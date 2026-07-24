"""Embedding function for the RAG store.

Default: ChromaDB's built-in embedding (all-MiniLM via onnx) so the skeleton runs
with zero extra keys. Swap to a hosted embedding (Anthropic/OpenAI/Cohere) here
if you want higher quality — nothing else in the RAG layer needs to change.
"""
from __future__ import annotations


def get_embedding_function():
    """Return a Chroma-compatible embedding function.

    TODO (optional): replace with a hosted embedder. For now, returning None
    lets Chroma use its default (local, keyless) embedding function.
    """
    return None
