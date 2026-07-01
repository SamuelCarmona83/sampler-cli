from pathlib import Path

import numpy as np

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.indexer.embedder import Embedder, build_embedding_text
from sampler.query.semantic import SemanticEngine


def _fake_encode(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words style embedding: dimension per known keyword, unit-normalized."""
    vocab = ["retry", "request", "network", "add", "calculator", "total", "helper"]
    vectors = []
    for text in texts:
        lowered = text.lower()
        vec = np.array([1.0 if word in lowered else 0.0 for word in vocab], dtype="float32")
        norm = np.linalg.norm(vec)
        vectors.append(vec / norm if norm else vec)
    return np.stack(vectors)


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
    embedder = Embedder(encode_fn=_fake_encode)

    count = embedder.embed_project(db=db, project_name=project_name)

    assert count == 2
    rows = db.get_embeddings_for_project(project_name)
    assert len(rows) == 2
    assert all(row["dim"] == 7 for row in rows)


def test_semantic_search_ranks_matching_symbol_first(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    embedder = Embedder(encode_fn=_fake_encode)
    embedder.embed_project(db=db, project_name=project_name)

    engine = SemanticEngine(db=db, embedder=embedder)
    results = engine.semantic_search("retry network request", project_name=project_name, limit=5)

    assert results
    assert results[0]["qualified_name"] == "retry_request"


def test_hybrid_search_combines_signals(tmp_path: Path) -> None:
    db, project_name = _index_demo_project(tmp_path)
    embedder = Embedder(encode_fn=_fake_encode)
    embedder.embed_project(db=db, project_name=project_name)

    engine = SemanticEngine(db=db, embedder=embedder)
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
    engine = SemanticEngine(db=db, embedder=Embedder(encode_fn=_fake_encode))

    assert engine.semantic_search("anything", project_name=project_name) == []
