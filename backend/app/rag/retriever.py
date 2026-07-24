"""Query the RAG knowledge base.

`search` is registered as an agent tool (search_knowledge_base) AND called
directly by the crop/season tools to ground their advice. Each hit carries its
source file + section so the citation shows up in the agent trace.
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.rag.ingest import COLLECTION

_collection = None


def _get_collection():
    """Lazily open the persistent Chroma collection."""
    global _collection
    if _collection is None:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_dir)
        _collection = client.get_collection(COLLECTION)
    return _collection


async def search(query: str, k: int = 4) -> list[dict[str, Any]]:
    """Return the top-k grounded snippets for a query.

    Shape: [{"text","source","section","score"}, ...] — score is cosine-ish
    relevance in [0,1] (1 = best). Raises a helpful error if the KB was never
    ingested (the agent surfaces it in the trace instead of inventing facts).
    """
    try:
        col = _get_collection()
    except Exception as e:  # collection missing / chroma unavailable
        return [
            {
                "error": f"knowledge base unavailable: {e}",
                "hint": "run `python scripts/ingest_kb.py` in backend/",
            }
        ]

    res = col.query(query_texts=[query], n_results=max(1, min(k, 10)))
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    hits: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        score = round(max(0.0, 1.0 - dist / 2), 3) if dist is not None else None
        hits.append(
            {
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "section": (meta or {}).get("section", ""),
                "score": score,
            }
        )
    return hits


async def search_compact(query: str, k: int = 3, max_chars: int = 500) -> list[dict[str, Any]]:
    """Like search() but with truncated text — used inside other tools to keep
    their outputs (and the trace) readable."""
    hits = await search(query, k)
    for h in hits:
        if "text" in h and len(h["text"]) > max_chars:
            h["text"] = h["text"][: max_chars].rsplit(" ", 1)[0] + " …"
    return hits
