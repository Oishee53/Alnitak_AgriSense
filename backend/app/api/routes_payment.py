"""bdapps CaaS checkout endpoints (Tier 2, 10 pts).

A complete checkout -> operator-balance charge -> receipt flow:
  1. normalize the subscriber number to bdapps `tel:8801XXXXXXXXX` form,
  2. compute the basket total server-side (client can't dictate a wrong total),
  3. call the CaaS charge (sandbox simulator or the real bdapps endpoint),
  4. persist the receipt + surface the request/response in the agent trace,
  5. return the receipt.

See app/bdapps/caas.py for the charge contract.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.schemas import CheckoutRequest, CheckoutResponse, TraceStep
from app.bdapps import caas, sms
from app.config import settings
from app.memory import store

router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.get("/mode")
async def mode() -> dict[str, Any]:
    """Report whether charges are simulated (sandbox) or hit the real bdapps API.

    Lets the UI label the checkout honestly instead of hard-coding "SANDBOX".
    """
    return {
        "sandbox": settings.bdapps_sandbox,
        "app_id": settings.bdapps_app_id or None,
    }


def _basket_total(items: list[dict[str, Any]]) -> float | None:
    """Sum priced lines (qty × unit_price_bdt). None if no line is priced."""
    total = 0.0
    priced = False
    for line in items:
        unit = line.get("unit_price_bdt")
        if unit is None:
            continue
        qty = line.get("qty", 1)
        try:
            total += float(qty) * float(unit)
            priced = True
        except (TypeError, ValueError):
            continue
    return round(total, 2) if priced else None


def _trace_steps(req_shown: dict[str, Any], resp: CheckoutResponse) -> list[dict[str, Any]]:
    """Build the two visible trace steps for the CaaS charge."""
    return [
        {
            "step": 1,
            "kind": "tool_call",
            "tool": "bdapps_caas_charge",
            "params": req_shown,
            "summary": f"Charging {resp.amount_bdt:.2f} BDT via bdapps CaaS",
        },
        {
            "step": 2,
            "kind": "tool_result",
            "tool": "bdapps_caas_charge",
            "result": {
                "statusCode": resp.status_code,
                "statusDetail": resp.status_detail,
                "externalTrxId": resp.external_trx_id,
                "success": resp.success,
            },
            "summary": (
                f"{resp.status_code}: "
                + ("charged" if resp.success else "declined")
                + f" ({resp.receipt.get('mode', 'sandbox')})"
            ),
        },
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest) -> CheckoutResponse:
    """Charge the farmer's operator balance for their basket and issue a receipt."""
    subscriber_id, err = caas.normalize_subscriber_id(req.subscriber_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Server-authoritative amount: prefer the summed basket; fall back to the
    # client amount only when no line carries a price.
    amount = _basket_total(req.items)
    if amount is None:
        amount = req.amount_bdt
    if amount is None or amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="amount must be greater than 0 (send amount_bdt or priced items)",
        )

    resp = await caas.charge(
        subscriber_id=subscriber_id,
        amount_bdt=amount,
        items=req.items,
        session_id=req.session_id,
    )

    steps = _trace_steps(resp.receipt.get("request", {}), resp)

    # Deliver the paid deliverable: the farmer's first weather/pest alert SMS
    # (BDApps SMS Send §3.1). An SMS failure is reported, never fatal.
    if resp.success:
        artifacts = store.get_or_create_session(req.session_id).artifacts
        sms_result = await sms.send_sms(
            subscriber_id, sms.compose_alert_sms(artifacts)
        )
        resp.receipt["sms"] = sms_result
        steps.append(
            {
                "step": len(steps) + 1,
                "kind": "tool_result",
                "tool": "bdapps_sms_send",
                "result": {
                    "statusCode": sms_result["status_code"],
                    "to": sms_result["to"],
                    "message": sms_result["preview"],
                },
                "summary": (
                    f"{sms_result['status_code']}: alert SMS "
                    + ("sent" if sms_result["status_code"] == "S1000" else "failed")
                    + f" ({sms_result['mode']})"
                ),
            }
        )
    resp.trace = [TraceStep(**s) for s in steps]  # for the live trace panel
    try:
        store.save_receipt(req.session_id, resp, steps)
    except Exception:
        # A persistence hiccup must not fail a completed charge; the receipt is
        # still returned to the caller.
        pass
    return resp


@router.get("/receipts/{session_id}")
async def receipts(session_id: str) -> dict[str, Any]:
    """Return the payment history for a session (newest first)."""
    return {"receipts": store.list_receipts(session_id)}
