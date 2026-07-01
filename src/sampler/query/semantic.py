from __future__ import annotations

from datetime import datetime

from sampler.db import Database
from sampler.indexer.embedder import Embedder


class SemanticEngine:
    def __init__(self, db: Database, embedder: Embedder | None = None) -> None:
        self.db = db
        self.embedder = embedder or Embedder()

    def _scored_candidates(self, query: str, project_name: str | None, pool: int):
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires the 'semantic' extra. "
                "Install with: pip install 'sampler-cli[semantic]'"
            ) from exc

        rows = self.db.get_embeddings_for_project(project_name) if project_name else []
        if not rows:
            return []

        query_vec = self.embedder.embed_texts([query])[0]
        query_vec = np.asarray(query_vec, dtype="float32")

        scored = []
        for row in rows:
            vec = np.frombuffer(row["vector"], dtype="float32")
            sim = float(np.dot(query_vec, vec))
            scored.append((sim, row))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:pool]

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
            callers = self.db.get_callers(row["symbol_id"])
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
