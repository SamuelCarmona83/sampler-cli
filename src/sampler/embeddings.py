"""Embeddings adapter layer.

Explicitly requested: EmbeddingProvider + BGE as default + support for multiple (Ollama etc in segunda etapa) + config-driven + offline hash/TF-IDF fallback.

ponytail: only BGE+Hash implemented (second-stage providers raise clear message). Single file. Reuses embedder hash logic. No registry, no extra base classes, no future scaffolding.

Config example:
  embeddings:
    provider: "bge-small"
    # provider: "hash"  # for no-internet
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sampler.config import EmbeddingsConfig

from sampler.indexer.embedder import DEFAULT_HASH_BITS, _hash_fingerprint_vector


def _missing_dep_error(provider: str, pip_extra: str, offline_hint: str = "") -> RuntimeError:
    msg = (
        f"{provider} requires optional deps.\n"
        f"Install: pip install 'sampler-cli[{pip_extra}]'\n"
        "If pip says extra is missing, upgrade sampler-cli first (>=0.4.0).\n"
    )
    if offline_hint:
        msg += f"Offline fallback: {offline_hint}\n"
    msg += "Use provider: hash (or TF-IDF via [semantic])."
    return RuntimeError(msg)


class EmbeddingProvider(ABC):
    """Requested adapter. embed(text, *, for_query=False) -> list[float] etc."""

    @abstractmethod
    def embed(self, text: str, *, for_query: bool = False) -> list[float]: ...

    def embed_batch(self, texts: list[str], *, for_query: bool = False) -> list[list[float]]:
        return [self.embed(t, for_query=for_query) for t in texts]

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...


class HashProvider(EmbeddingProvider):
    """Offline fallback. Reuses embedder._hash_fingerprint_vector (no dupe)."""

    def __init__(self, hash_bits: int = DEFAULT_HASH_BITS) -> None:
        self._hash_bits = hash_bits

    @property
    def name(self) -> str: return "hash"
    @property
    def dimension(self) -> int: return self._hash_bits
    @property
    def model_id(self) -> str: return f"hash-fingerprint-v1-{self._hash_bits}"

    def embed(self, text: str, *, for_query: bool = False) -> list[float]:
        return _hash_fingerprint_vector(text, self._hash_bits).tolist()

    def hash_fingerprint_vector(self, text: str):
        return _hash_fingerprint_vector(text, self._hash_bits)


class BGEProvider(EmbeddingProvider):
    """Default (BGE Small v1.5). Uses fastembed + passage/query prefixes."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or "BAAI/bge-small-en-v1.5"
        self._model_obj = None

    @property
    def name(self) -> str: return "bge-small"
    @property
    def dimension(self) -> int: return 384
    @property
    def model_id(self) -> str: return self._model

    def _ensure(self):
        if self._model_obj is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise _missing_dep_error("BGE", "embeddings", "provider: hash") from exc
            self._model_obj = TextEmbedding(model_name=self._model)
        return self._model_obj

    def embed(self, text: str, *, for_query: bool = False) -> list[float]:
        m = self._ensure()
        prefix = ("query: " if for_query else "passage: ")
        vecs = list(m.embed([prefix + text]))
        v = vecs[0]
        return v.tolist() if hasattr(v, "tolist") else list(v)

    def embed_batch(self, texts: list[str], *, for_query: bool = False) -> list[list[float]]:
        if not texts: return []
        m = self._ensure()
        prefix = ("query: " if for_query else "passage: ")
        vecs = list(m.embed([prefix + t for t in texts]))
        return [(v.tolist() if hasattr(v, "tolist") else list(v)) for v in vecs]


def get_embedding_provider(cfg: "EmbeddingsConfig | None" = None) -> EmbeddingProvider:
    if cfg is None:
        from sampler.config import ConfigManager
        cfg = ConfigManager().load().embeddings

    key = (cfg.provider or "bge-small").strip().lower()

    if key in ("hash", "hash-fingerprint"):
        return HashProvider()
    if key in ("bge-small", "bge"):
        return BGEProvider(model=cfg.model)

    # Explicit: ollama/nomic/openai/fastembed are segunda etapa (as requested)
    raise RuntimeError(
        f"Provider '{cfg.provider}' is second stage (Ollama/Docker Model etc.).\n"
        "For now use 'bge-small' (default) or 'hash' (offline).\n"
        "See TODO.md. Interface already designed to add without changing Embedder/Semantic/CLI."
    )
