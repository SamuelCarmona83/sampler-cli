from __future__ import annotations

import hashlib
import re
from typing import Callable

from sampler.db import Database

DEFAULT_BATCH_SIZE = 32
DEFAULT_HASH_BITS = 256
DEFAULT_EMBEDDING_BACKEND = "hash-fingerprint-v1"


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
    """Generates deterministic local embeddings with hash fingerprints.

    No LLM model dependency, no provider/network dependency.

    An `encode_fn` may be injected (e.g. tests/custom backend) to bypass the
    built-in fingerprinting logic; it must accept list[str] and return an
    (N, dim) numpy-like array.
    """

    def __init__(
        self,
        encode_fn: Callable | None = None,
        hash_bits: int = DEFAULT_HASH_BITS,
    ) -> None:
        self.backend = DEFAULT_EMBEDDING_BACKEND
        self._encode_fn = encode_fn
        self.hash_bits = hash_bits

    def _tokens(self, text: str) -> list[str]:
        return tokenize_text(text)

    def hash_fingerprint_vector(self, text: str):
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
            ) from exc

        vec = np.zeros(self.hash_bits, dtype="float32")
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.hash_bits
            vec[idx] = 1.0

        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec

    def hash_fingerprint_bytes(self, text: str) -> bytes:
        return self.hash_fingerprint_vector(text).astype("float32").tobytes()

    def embed_texts(self, texts: list[str]):
        if self._encode_fn is not None:
            return self._encode_fn(texts)
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Semantic search requires numpy. Install with: pip install 'sampler-cli[semantic]'"
            ) from exc
        return np.stack([self.hash_fingerprint_vector(t) for t in texts])

    def embed_project(
        self,
        db: Database,
        project_name: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> int:
        """Generate and store embeddings for every symbol in a project. Returns the count embedded.

        Processes in batches so `on_progress(done, total)` can drive a progress bar
        (e.g. rich.progress) without waiting for the whole project to finish.
        """
        rows = db.list_symbols(project_name=project_name)
        total = len(rows)
        if total == 0:
            return 0

        dim = self.hash_bits
        for start in range(0, total, batch_size):
            batch = rows[start : start + batch_size]
            texts = [build_embedding_text(dict(row), row["file_path"]) for row in batch]
            for row, text in zip(batch, texts):
                db.upsert_embedding(
                    symbol_id=row["id"],
                    model=self.backend,
                    dim=dim,
                    vector=self.hash_fingerprint_bytes(text),
                )

            if on_progress is not None:
                on_progress(min(start + batch_size, total), total)

        return total
