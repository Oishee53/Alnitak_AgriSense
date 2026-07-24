"""Build the RAG index from data/knowledge_base/.

Usage:
    cd backend
    python scripts/ingest_kb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain script (add backend/ to path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.ingest import ingest  # noqa: E402


def main() -> None:
    count = ingest()
    print(f"[ingest_kb] Indexed {count} chunks.")


if __name__ == "__main__":
    main()
