"""Basic contract tests for the embeddings provider adapter layer."""
from pathlib import Path

import pytest

from sampler.embeddings import EmbeddingProvider, get_embedding_provider, HashProvider
from sampler.config import ConfigManager, EmbeddingsConfig


def test_hash_provider_contract():
    p = HashProvider()
    assert isinstance(p, EmbeddingProvider)
    assert p.name == "hash"
    assert p.dimension > 0
    assert "hash" in p.model_id

    v = p.embed("def foo(): pass")
    assert isinstance(v, list)
    assert len(v) == p.dimension
    assert all(isinstance(x, float) for x in v)

    batch = p.embed_batch(["a", "b"])
    assert len(batch) == 2
    assert len(batch[0]) == p.dimension


def test_get_embedding_provider_hash_explicit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cm = ConfigManager()
    cm.update_embeddings(provider="hash")

    prov = get_embedding_provider()
    assert prov.name == "hash"


def test_get_embedding_provider_defaults_to_bge_small():
    # Even without installing [embeddings], the factory should not crash on "bge-small"
    # (it will raise only on first .embed if fastembed missing)
    cfg = EmbeddingsConfig(provider="bge-small")
    # This may raise if fastembed not present — that's expected and tested via error path elsewhere.
    # We just ensure the key is known in registry or handled.
    try:
        prov = get_embedding_provider(cfg)
        assert prov.name in ("bge-small", "fastembed")
    except RuntimeError as e:
        # Acceptable: missing optional dep message
        assert "embeddings" in str(e).lower() or "fastembed" in str(e).lower()


# (ponytail: dropped private _USE_PREFIX poke test; prefix is impl detail of BGE, covered by usage in embed/semantic)
