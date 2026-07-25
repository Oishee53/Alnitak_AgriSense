"""Plant disease detection from a photo (Tier 2).

POST /api/diagnose  — a farmer uploads a crop photo; a vision model identifies
the disease/pest and we ground the treatment in the KB where possible. The
result is stored as the session's `disease` artifact (so it survives reload) and
returned for the UI to render.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import trace as trace_mod
from app.memory import store
from app.tools import disease

router = APIRouter(prefix="/api", tags=["diagnose"])


class DiagnoseRequest(BaseModel):
    session_id: str
    image: str = Field(..., description="data: URL, e.g. data:image/jpeg;base64,…")
    crop: Optional[str] = None
    lang: Optional[str] = None  # 'bn' → vision free-text in Bengali


@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest) -> dict[str, Any]:
    """Diagnose a crop photo and store the result on the session."""
    if not req.image.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="image must be a data:image/ URL")

    state = store.get_or_create_session(req.session_id)
    try:
        result = await disease.detect_disease(req.image, crop=req.crop, lang=req.lang)
    except RuntimeError as e:  # missing OPENAI_API_KEY
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    steps: list[dict[str, Any]] = []
    if "error" not in result and result.get("is_plant") is not False:
        state.artifacts["disease"] = result
        store.persist_artifacts(state)
        # Surface the diagnosis in the visible agent trace.
        summary = (
            f"{result.get('crop') or 'crop'}: {result.get('diagnosis')} "
            f"({result.get('confidence')} confidence"
            + (", KB-grounded" if result.get("kb_grounded") else "")
            + ")"
        )
        trace_mod.record(
            req.session_id,
            "tool_result",
            tool="detect_disease",
            result={k: v for k, v in result.items() if k != "because"},
            summary=summary,
        )
        steps = [{"step": 1, "kind": "tool_result", "tool": "detect_disease", "summary": summary}]

    return {"diagnosis": result, "trace": steps}
