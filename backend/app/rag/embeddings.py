"""Embedding function for the RAG store.

Default: ChromaDB's built-in embedding (all-MiniLM via onnx) so the skeleton runs
with zero extra keys. Swap to a hosted embedding (Anthropic/OpenAI/Cohere) here
if you want higher quality — nothing else in the RAG layer needs to change.
"""
from __future__ import annotations

from pathlib import Path


def use_local_model_cache() -> None:
    """Keep ChromaDB's ONNX embedding model on the project drive.

    By default Chroma downloads the all-MiniLM model to ``~/.cache/chroma``
    (i.e. the C: user profile). We repoint that at ``backend/data/onnx_models``
    so nothing about *running* this project writes outside the repo. Same model,
    same vectors — only the download location changes, so no re-indexing is
    needed. Call this before opening any Chroma client. Best-effort: if Chroma's
    internals change, ingest/retrieve still work (falling back to the default
    path) rather than crashing.
    """
    try:
        from app.config import settings
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import (
            ONNXMiniLM_L6_V2,
        )

        root = Path(settings.chroma_dir).parent / "onnx_models"
        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = root / ONNXMiniLM_L6_V2.MODEL_NAME
    except Exception:
        pass


def get_embedding_function():
    """Return a Chroma-compatible embedding function.

    TODO (optional): replace with a hosted embedder. For now, returning None
    lets Chroma use its default (local, keyless) embedding function.
    """
    return None
