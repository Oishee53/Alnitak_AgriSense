"""Build the RAG knowledge base from data/knowledge_base/*.

Reads the collected agronomic documents (extension manuals, fertilizer guides,
crop calendars, soil/yield references), splits them into heading-aware chunks,
embeds them with Chroma's default local embedding function, and persists to a
local Chroma collection. Run via scripts/ingest_kb.py.
"""
from __future__ import annotations

import glob
import os
import re

from app.config import settings

COLLECTION = "agrisense_kb"

_MAX_CHUNK = 1400  # chars; sections beyond this get sub-split


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown doc into (heading, body) sections on '## ' headings.

    The document title (first '# ' line) is prefixed to every chunk so each
    chunk stays self-describing after retrieval.
    """
    lines = text.splitlines()
    title = ""
    for ln in lines:
        if ln.startswith("# "):
            title = ln[2:].strip()
            break

    sections: list[tuple[str, str]] = []
    current_head, current_body = "Overview", []
    for ln in lines:
        if ln.startswith("## "):
            if current_body:
                sections.append((current_head, "\n".join(current_body).strip()))
            current_head, current_body = ln[3:].strip(), []
        else:
            current_body.append(ln)
    if current_body:
        sections.append((current_head, "\n".join(current_body).strip()))

    out: list[tuple[str, str]] = []
    for head, body in sections:
        if not body:
            continue
        chunk = f"{title} — {head}\n{body}" if title else f"{head}\n{body}"
        if len(chunk) <= _MAX_CHUNK:
            out.append((head, chunk))
        else:  # sub-split long sections on sentence boundaries
            parts, buf = [], ""
            for sent in re.split(r"(?<=[.!?])\s+", chunk):
                if len(buf) + len(sent) > _MAX_CHUNK and buf:
                    parts.append(buf)
                    buf = sent
                else:
                    buf = f"{buf} {sent}".strip()
            if buf:
                parts.append(buf)
            out.extend((head, p) for p in parts)
    return out


def ingest() -> int:
    """Ingest every .md/.txt under KB_DIR into Chroma. Returns #chunks indexed."""
    import chromadb

    files = sorted(
        f
        for f in glob.glob(os.path.join(settings.kb_dir, "**", "*"), recursive=True)
        if f.lower().endswith((".md", ".txt"))
        and os.path.basename(f).lower() != "readme.md"
    )
    if not files:
        print(f"[ingest] No .md/.txt files in {settings.kb_dir}. Add KB docs first.")
        return 0

    client = chromadb.PersistentClient(path=settings.chroma_dir)
    # Rebuild from scratch so re-ingest never leaves stale chunks behind.
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    for path in files:
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        for i, (head, chunk) in enumerate(_split_sections(text)):
            ids.append(f"{fname}::{i}")
            docs.append(chunk)
            metas.append({"source": fname, "section": head})
        print(f"[ingest] {fname}: ok")

    collection.add(ids=ids, documents=docs, metadatas=metas)
    print(f"[ingest] Indexed {len(ids)} chunks from {len(files)} files.")
    return len(ids)
