from __future__ import annotations

from datetime import datetime

from sampler.db import Database
from sampler.indexer.embedder import Embedder, build_embedding_text, tokenize_text

# Provider layer (for vector scoring when precomputed embeddings match the active provider)
try:
    from sampler.embeddings import EmbeddingProvider
except Exception:
    EmbeddingProvider = None  # type: ignore


class SemanticEngine:
    def __init__(self, db: Database, embedder: Embedder | None = None) -> None:
        self.db = db
        # Embedder now carries the active EmbeddingProvider (config-driven by default)
        self.embedder = embedder or Embedder()

    def _project_rows(self, project_name: str | None) -> list[dict]:
        if not project_name:
            return []
        return self.db.list_symbols(project_name=project_name)

    def _tfidf_scored_candidates(self, query: str, rows: list[dict], pool: int):
        """Primary backend: TF-IDF cosine similarity over structured symbol docs."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return []

        if not rows:
            return []

        texts = [build_embedding_text(dict(r), r["file_path"]) for r in rows]
        vectorizer = TfidfVectorizer(tokenizer=tokenize_text, token_pattern=None, lowercase=True)
        doc_matrix = vectorizer.fit_transform(texts)
        query_vec = vectorizer.transform([query])

        sims = (doc_matrix @ query_vec.T).toarray().ravel()
        scored = [(float(sim), row) for sim, row in zip(sims, rows)]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:pool]

    def _provider_vector_scored_candidates(self, query: str, project_name: str | None, pool: int):
        """Preferred path when a real (non-hash) provider has precomputed embeddings.

        Uses provider.embed(..., for_query=True) for the query vector + cosine against
        stored vectors whose model matches the current provider's model_id.
        Falls back to [] (so caller can try TF-IDF/hash).
        """
        if not project_name:
            return []
        try:
            import numpy as np
        except ImportError:
            return []

        provider = getattr(self.embedder, "provider", None)
        if provider is None or provider.name == "hash":
            return []

        embeddings = self.db.get_embeddings_for_project(project_name)
        if not embeddings:
            return []

        target_model = provider.model_id
        matching = [e for e in embeddings if e["model"] == target_model]
        if not matching:
            # provider changed or not embedded yet for this provider -> fallback
            return []

        try:
            query_vec = np.array(provider.embed(query, for_query=True), dtype="float32")
        except Exception:
            return []

        scored = []
        for row in matching:
            try:
                vec = np.frombuffer(row["vector"], dtype="float32")
                if len(vec) != len(query_vec):
                    continue
                sim = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-12))
                scored.append((sim, row))
            except Exception:
                continue

        if not scored:
            return []
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:pool]

    def _hash_scored_candidates(self, query: str, rows: list[dict], project_name: str | None, pool: int):
        """Last-resort backend: deterministic hash fingerprints (no ML, always available)."""
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
            ) from exc

        embeddings = self.db.get_embeddings_for_project(project_name) if project_name else []
        query_vec = self.embedder.hash_fingerprint_vector(query)

        if embeddings:
            scored = []
            for row in embeddings:
                vec = np.frombuffer(row["vector"], dtype="float32")
                sim = float(np.dot(query_vec, vec))
                scored.append((sim, row))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            return scored[:pool]

        if not rows:
            return []

        scored = []
        for row in rows:
            text = build_embedding_text(dict(row), row["file_path"])
            vec = self.embedder.hash_fingerprint_vector(text)
            sim = float(np.dot(query_vec, vec))
            scored.append((sim, row))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:pool]

    def _scored_candidates(self, query: str, project_name: str | None, pool: int):
        rows = self._project_rows(project_name)

        # 1. Real provider vectors (BGE/Ollama/OpenAI etc.) if pre-embedded and model matches
        prov = self._provider_vector_scored_candidates(query, project_name, pool)
        if prov:
            return prov

        # 2. TF-IDF (fast, on-the-fly, lexical, no pre-embed needed, sklearn optional)
        tfidf = self._tfidf_scored_candidates(query, rows, pool)
        if tfidf:
            return tfidf

        # 3. Hash fingerprint (always works, deterministic local fallback)
        return self._hash_scored_candidates(query, rows, project_name, pool)

    def semantic_search(self, query: str, project_name: str | None = None, limit: int = 10) -> list[dict]:
        """Pure cosine-similarity search over stored symbol embeddings, no graph/text signals."""
        candidates = self._scored_candidates(query, project_name, pool=limit)
        return [{**dict(row), "score": sim, "semantic_similarity": sim} for sim, row in candidates]

    def hybrid_search(
        self,
        query: str,
        project_name: str | None = None,
        limit: int = 10,
        candidate_pool: int = 50,
    ) -> list[dict]:
        """Combine semantic similarity with exact-match, graph centrality, and recency signals.

        score = 0.5 * semantic_similarity + 0.2 * exact_match + 0.2 * centrality + 0.1 * recently_modified
        """
        candidates = self._scored_candidates(query, project_name, pool=candidate_pool)
        if not candidates:
            return []

        centralities = []
        for _, row in candidates:
            callers = self.db.get_callers(row["id"])
            centralities.append(len(callers))
        max_centrality = max(centralities) or 1

        timestamps = []
        for _, row in candidates:
            try:
                timestamps.append(datetime.fromisoformat(row["last_indexed"]))
            except (TypeError, ValueError):
                timestamps.append(None)
        known_ts = [t for t in timestamps if t is not None]
        min_ts = min(known_ts) if known_ts else None
        max_ts = max(known_ts) if known_ts else None
        ts_span = (max_ts - min_ts).total_seconds() if (min_ts and max_ts and max_ts != min_ts) else 0

        query_norm = query.strip().lower()

        results = []
        for (sim, row), centrality_count, ts in zip(candidates, centralities, timestamps):
            name = (row["qualified_name"] or row["name"] or "").lower()
            if name == query_norm:
                exact_match = 1.0
            elif query_norm and query_norm in name:
                exact_match = 0.5
            else:
                exact_match = 0.0

            centrality = centrality_count / max_centrality if max_centrality else 0.0

            if ts_span and ts is not None:
                recently_modified = (ts - min_ts).total_seconds() / ts_span
            else:
                recently_modified = 1.0 if ts is not None else 0.0

            score = 0.5 * sim + 0.2 * exact_match + 0.2 * centrality + 0.1 * recently_modified
            results.append(
                {
                    **dict(row),
                    "score": score,
                    "semantic_similarity": sim,
                    "exact_match": exact_match,
                    "centrality": centrality,
                    "recently_modified": recently_modified,
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]
