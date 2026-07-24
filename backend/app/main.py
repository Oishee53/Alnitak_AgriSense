"""FastAPI entry point for AgriSense AI.

Run:  uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import routes_chat, routes_diagnose, routes_payment, routes_trace
from app.memory.db import init_db


def _ensure_kb() -> None:
    """Build the RAG index at startup if it does not exist yet, so a fresh
    machine can never silently run without the knowledge base (Tier-0 #7).
    Note: the very first build downloads Chroma's embedding model (~79 MB) —
    do this once with internet before the demo."""
    import chromadb

    from app.rag.ingest import COLLECTION, ingest

    try:
        chromadb.PersistentClient(path=settings.chroma_dir).get_collection(COLLECTION)
        return  # index already built
    except Exception:
        pass
    print("[startup] RAG index not found — ingesting knowledge base ...")
    try:
        n = ingest()
        print(f"[startup] Knowledge base ready ({n} chunks).")
    except Exception as e:
        print(
            f"[startup] WARNING: KB ingest failed ({e}). RAG will be unavailable "
            "until `python scripts/ingest_kb.py` succeeds."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, make sure the RAG index exists.
    init_db()
    _ensure_kb()
    yield
    # Shutdown: close resources if needed.


app = FastAPI(
    title="AgriSense AI",
    description="Autonomous agricultural advisor — Bdapps Agentic AI Hackathon.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_chat.router)
app.include_router(routes_trace.router)
app.include_router(routes_payment.router)
app.include_router(routes_diagnose.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "agrisense", "env": settings.app_env}
