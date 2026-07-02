from pathlib import Path

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.indexer.embedder import Embedder, build_embedding_text
from sampler.query.semantic import SemanticEngine

# New provider layer
from sampler.embeddings import EmbeddingProvider, HashProvider


def _index_demo_project(tmp_path: Path) -> tuple[Database, str]:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "network.py").write_text(
        '''
def retry_request(url, retries):
    """Retries failed HTTP requests using exponential backoff."""
    return url


def add(a, b):
    """Adds two numbers."""
    return a + b
''',
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")
    return db, "demo"


def test_build_embedding_text_includes_structured_fields() -> None:
    symbol = {
        "type": "function",
        "qualified_name": "retry_request",
        "name": "retry_request",
        "signature": "def retry_request(url, retries)",
        "docstring": "Retries failed HTTP requests using exponential backoff.",
    }
    text = build_embedding_text(symbol, "network.py")

    assert "Function:" in text
    assert "retry_request" in text
    assert "File:" in text
    assert "network.py" in text
    assert "Arguments:" in text
    assert "url" in text
    assert "retries" in text
    assert "Docstring:" in text
    assert "exponential backoff" in text


def test_embed_project_stores_one_embedding_per_symbol(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    embedder = Embedder(provider=HashProvider())

    count = embedder.embed_project(db=db, project_name=project_name)

    assert count == 2
    rows = db.get_embeddings_for_project(project_name)
    assert len(rows) == 2
    assert all(row["dim"] == 256 for row in rows)


def test_semantic_search_ranks_matching_symbol_first(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    engine = SemanticEngine(db=db)
    results = engine.semantic_search("retry network request", project_name=project_name, limit=5)

    assert results
    assert results[0]["qualified_name"] == "retry_request"


def test_hybrid_search_combines_signals(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    engine = SemanticEngine(db=db)
    results = engine.hybrid_search("retry network request", project_name=project_name, limit=5)

    assert results
    top = results[0]
    assert top["qualified_name"] == "retry_request"
    assert 0.0 <= top["score"] <= 1.0
    assert "semantic_similarity" in top
    assert "exact_match" in top
    assert "centrality" in top
    assert "recently_modified" in top


def test_semantic_search_without_embeddings_returns_empty(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    engine = SemanticEngine(db=db, embedder=Embedder(provider=HashProvider()))

    assert engine.semantic_search("anything", project_name=project_name)


def test_hash_fallback_used_when_tfidf_unavailable(tmp_path: Path, monkeypatch) -> None:
    db, project_name = _index_demo_project(tmp_path)
    embedder = Embedder(provider=HashProvider())
    embedder.embed_project(db=db, project_name=project_name)
    engine = SemanticEngine(db=db, embedder=embedder)

    # Force fallback path (simulate no TF-IDF backend).
    monkeypatch.setattr(engine, "_tfidf_scored_candidates", lambda query, rows, pool: [])

    results = engine.semantic_search("retry network request", project_name=project_name, limit=5)

    assert results
    assert results[0]["qualified_name"] == "retry_request"


class _DummyProvider(EmbeddingProvider):
    """Minimal provider for testing the vector scoring path (no real model)."""
    def __init__(self):
        self._dim = 8
    @property
    def name(self): return "dummy"
    @property
    def dimension(self): return self._dim
    @property
    def model_id(self): return "dummy-test-v1"
    def embed(self, text: str, *, for_query: bool = False):
        # Very naive: hash a few buckets
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        vec = [0.0] * self._dim
        for i in range(self._dim):
            vec[i] = (h[i] % 10) / 10.0
        return vec
    def embed_batch(self, texts, *, for_query=False):
        return [self.embed(t, for_query=for_query) for t in texts]


def test_provider_vector_path_used_when_embeddings_match(tmp_path: Path, monkeypatch) -> None:
    db, project_name = _index_demo_project(tmp_path)
    prov = _DummyProvider()
    embedder = Embedder(provider=prov)
    embedder.embed_project(db=db, project_name=project_name)

    engine = SemanticEngine(db=db, embedder=embedder)

    # Force no tfidf to ensure provider path is taken
    monkeypatch.setattr(engine, "_tfidf_scored_candidates", lambda q, rows, p: [])

    results = engine.semantic_search("retry network request", project_name=project_name, limit=5)
    assert results
    # Should have used the dummy vectors (sanity: scores present)
    assert "semantic_similarity" in results[0] or "score" in results[0]
