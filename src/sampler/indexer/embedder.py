from __future__ import annotations

import os
from typing import Callable

from sampler.db import Database

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BATCH_SIZE = 32


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
    """Generates symbol embeddings using a local sentence-transformers model.

    An `encode_fn` may be injected (e.g. in tests) to bypass loading the real
    model; it must accept a list[str] and return an (N, dim) numpy array.

    Set `offline=True` (or env vars HF_HUB_OFFLINE=1 / TRANSFORMERS_OFFLINE=1)
    when there's no network access to HuggingFace or any other provider — the
    model must already be cached locally, or `model_name` must point to a
    local model directory.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        encode_fn: Callable | None = None,
        offline: bool = False,
    ) -> None:
        self.model_name = model_name
        self.offline = offline or os.environ.get("HF_HUB_OFFLINE") == "1"
        self._encode_fn = encode_fn
        self._model = None

    def _load_model(self):
        if self._model is None:
            if self.offline:
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Semantic search requires the 'semantic' extra. "
                    "Install with: pip install 'sampler-cli[semantic]'"
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name, local_files_only=self.offline)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not load model '{self.model_name}'"
                    + (
                        " in offline mode (not found in local cache)."
                        if self.offline
                        else " — no network access to HuggingFace or any other provider?"
                    )
                    + " Download the model once with internet access (it gets cached locally), "
                    "or point --model at a local model directory, then retry with --offline."
                ) from exc
        return self._model

    def embed_texts(self, texts: list[str]):
        if self._encode_fn is not None:
            return self._encode_fn(texts)
        model = self._load_model()
        return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

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

        dim: int | None = None
        for start in range(0, total, batch_size):
            batch = rows[start : start + batch_size]
            texts = [build_embedding_text(dict(row), row["file_path"]) for row in batch]
            vectors = self.embed_texts(texts)
            if dim is None:
                dim = int(vectors.shape[1])

            for row, vector in zip(batch, vectors):
                db.upsert_embedding(
                    symbol_id=row["id"],
                    model=self.model_name,
                    dim=dim,
                    vector=vector.astype("float32").tobytes(),
                )

            if on_progress is not None:
                on_progress(min(start + batch_size, total), total)

        return total
