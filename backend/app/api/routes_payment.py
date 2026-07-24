"""bdapps CaaS checkout endpoints (Tier 2, 10 pts).

Showcases a complete checkout -> operator balance deduction -> receipt flow
in sandbox/simulator mode. See app/bdapps/caas.py.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import CheckoutRequest, CheckoutResponse
from app.bdapps import caas

router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest) -> CheckoutResponse:
    """Charge the farmer's operator balance for their input basket.

    TODO: build the itemized basket total, call caas.charge(), persist the
    receipt to memory, and surface the request/response in the agent trace.
    """
    return await caas.charge(
        subscriber_id=req.subscriber_id,
        amount_bdt=req.amount_bdt,
        items=req.items,
        session_id=req.session_id,
    )
