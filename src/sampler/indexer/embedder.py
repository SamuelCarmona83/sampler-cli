from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Callable

from sampler.db import Database
from sampler.viz.events import EmbeddingGenerated

if TYPE_CHECKING:
    from sampler.viz.bus import EventBus, NullEventBus

# --- Public constants kept for backward compat ---
DEFAULT_BATCH_SIZE = 32
DEFAULT_HASH_BITS = 256
DEFAULT_EMBEDDING_BACKEND = "hash-fingerprint-v1"

# New provider layer (lazy to avoid hard dep on embeddings package for pure-hash users)
try:
    from sampler.embeddings import EmbeddingProvider, get_embedding_provider
except Exception:  # during early import or missing pieces
    EmbeddingProvider = None  # type: ignore
    get_embedding_provider = None  # type: ignore


def _hash_fingerprint_vector(text: str, hash_bits: int = DEFAULT_HASH_BITS):
    """ponytail: extracted for reuse by HashProvider (avoid dupe of the vector math)."""
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
        ) from exc

    # tokenize is already top level in this file
    tokens = tokenize_text(text)
    vec = np.zeros(hash_bits, dtype="float32")
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % hash_bits
        vec[idx] = 1.0

    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def tokenize_text(text: str) -> list[str]:
    """Tokenize identifiers and prose with light normalization.

    - keeps original token
    - splits snake_case/camel-ish chunks via separators
    - adds naive singular form for trailing 's' words
    """
    base = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    out: list[str] = []
    for tok in base:
        out.append(tok)
        parts = [p for p in re.split(r"[_\-./]", tok) if p]
        out.extend(parts)
        if tok.endswith("s") and len(tok) > 3:
            out.append(tok[:-1])
        for part in parts:
            if part.endswith("s") and len(part) > 3:
                out.append(part[:-1])
    return out


def build_embedding_text(symbol: dict, file_path: str) -> str:
    """Build a structured, doc-like text for a symbol (embeds better than raw code).

    Produces something like:
        Function:
        retry_request

        File:
        network.py

        Arguments:
        url
        retries

        Docstring:
        Retries failed HTTP requests using exponential backoff.
    """
    label = (symbol.get("type") or "symbol").replace("async ", "").capitalize()
    parts = [f"{label}:", symbol.get("qualified_name") or symbol.get("name") or ""]

    parts += ["", "File:", file_path]

    args = _extract_arguments(symbol.get("signature"))
    if args:
        parts += ["", "Arguments:", *args]

    docstring = symbol.get("docstring")
    if docstring:
        parts += ["", "Docstring:", docstring.strip()]

    return "\n".join(parts)


def _extract_arguments(signature: str | None) -> list[str]:
    if not signature or "(" not in signature or ")" not in signature:
        return []
    inner = signature.split("(", 1)[1].rsplit(")", 1)[0]
    names = [a.strip().split(":")[0].split("=")[0].strip() for a in inner.split(",")]
    return [n for n in names if n and n not in ("self", "cls")]


class Embedder:
    """High-level embedding orchestrator.

    Now uses the pluggable EmbeddingProvider adapter by default (reads from
    global config). Fully backward compatible:

    - Embedder()  -> uses config (bge-small by default, or hash if set / no deps)
    - Embedder(encode_fn=...) or explicit hash_bits -> legacy hash path preserved
      for tests and advanced injection.

    The provider layer allows BGE / Ollama / OpenAI etc. without changing
    callers of embed_project or the semantic engine.
    """

    def __init__(
        self,
        encode_fn: Callable | None = None,
        hash_bits: int = DEFAULT_HASH_BITS,
        provider: "EmbeddingProvider | None" = None,
    ) -> None:
        self._encode_fn = encode_fn
        self.hash_bits = hash_bits  # only used in pure legacy hash path

        if provider is not None:
            self.provider = provider
        elif encode_fn is not None or hash_bits != DEFAULT_HASH_BITS:
            # Legacy explicit hash mode requested
            from sampler.embeddings import HashProvider

            self.provider = HashProvider(hash_bits=hash_bits)
        else:
            # Preferred: config-driven provider (bge-small by default)
            if get_embedding_provider is not None:
                try:
                    self.provider = get_embedding_provider()
                except Exception:
                    # Fall back gracefully to hash (e.g. config load issues in tests)
                    from sampler.embeddings import HashProvider

                    self.provider = HashProvider(hash_bits=hash_bits)
            else:
                from sampler.embeddings import HashProvider

                self.provider = HashProvider(hash_bits=hash_bits)

        # backend string for compat (used in old messages / some tests)
        self.backend = getattr(self.provider, "model_id", DEFAULT_EMBEDDING_BACKEND)

    # --- Legacy hash surface (delegates when using HashProvider; used by SemanticEngine fallback) ---

    def _tokens(self, text: str) -> list[str]:
        return tokenize_text(text)

    def hash_fingerprint_vector(self, text: str):
        # Prefer provider if it exposes the method (HashProvider does)
        if hasattr(self.provider, "hash_fingerprint_vector"):
            return self.provider.hash_fingerprint_vector(text)
        # Otherwise synthesize via embed (less efficient but correct for any provider)
        vec_list = self.provider.embed(text)
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
            ) from exc
        return np.array(vec_list, dtype="float32")

    def hash_fingerprint_bytes(self, text: str) -> bytes:
        return self.hash_fingerprint_vector(text).astype("float32").tobytes()

    def embed_texts(self, texts: list[str]):
        """Legacy path used by some custom encode_fn injection."""
        if self._encode_fn is not None:
            try:
                import numpy as np
            except ImportError as exc:
                raise RuntimeError(
                    "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
                ) from exc
            return np.stack(self._encode_fn(texts)) if not isinstance(self._encode_fn(texts)[0], (list, tuple)) else np.stack([np.array(v) for v in self._encode_fn(texts)])
        # Delegate to provider batch
        vecs = self.provider.embed_batch(texts)
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
            ) from exc
        return np.stack([np.array(v, dtype="float32") for v in vecs])

    # --- Main API (now provider-aware) ---

    def embed_project(
        self,
        db: Database,
        project_name: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_progress: Callable[[int, int], None] | None = None,
        event_bus: EventBus | NullEventBus | None = None,
    ) -> int:
        """Generate and store embeddings for every symbol in a project using the active provider.

        Returns the count embedded.
        """
        rows = db.list_symbols(project_name=project_name)
        total = len(rows)
        if total == 0:
            return 0

        provider = self.provider
        dim = provider.dimension
        model = provider.model_id

        for start in range(0, total, batch_size):
            batch = rows[start : start + batch_size]
            texts = [build_embedding_text(dict(row), row["file_path"]) for row in batch]
            # Use provider batch (supports for_query=False for document storage)
            vectors = provider.embed_batch(texts, for_query=False)

            done_before = start
            for row, vec in zip(batch, vectors):
                try:
                    import numpy as np
                except ImportError as exc:
                    raise RuntimeError(
                        "Embeddings require numpy. Install with: pip install 'sampler-cli[semantic]' or 'sampler-cli[embeddings]'"
                    ) from exc
                vec_bytes = np.array(vec, dtype="float32").tobytes()
                db.upsert_embedding(
                    symbol_id=row["id"],
                    model=model,
                    dim=dim,
                    vector=vec_bytes,
                )
                done_before += 1
                if event_bus is not None:
                    name = row["qualified_name"] or row["name"]
                    event_bus.emit(
                        EmbeddingGenerated(name=name, index=done_before, total=total)
                    )

            if on_progress is not None:
                on_progress(min(start + batch_size, total), total)

        return total
