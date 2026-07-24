"""bdapps CaaS (Charging-as-a-Service) module — Tier 2 (10 pts).

Showcases a complete checkout -> operator balance deduction -> receipt flow.
Mirrors the request/response shape of the bdapps CaaS `cass` call (see the
provided reference SDK in bdapps-reference/sdk_file.php -> DirectDebitSender).

Two modes (BDAPPS_SANDBOX):
  - sandbox=true  -> local simulator: deterministic S1000 success + receipt,
                     no network. Perfect for a reliable live demo.
  - sandbox=false -> POST to the real bdapps sandbox endpoint using the
                     configured applicationId/password.

Docs: https://dev.bdapps.com/API_Documentation/bdapps_tap_api.html
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.api.schemas import CheckoutResponse
from app.config import settings


def _external_trx_id() -> str:
    return "AGRI-" + uuid.uuid4().hex[:16].upper()


async def charge(
    subscriber_id: str,
    amount_bdt: float,
    items: list[dict[str, Any]],
    session_id: str,
) -> CheckoutResponse:
    """Charge a subscriber's operator balance and return a receipt.

    Request fields mirror bdapps DirectDebit/CaaS:
        applicationId, password, externalTrxId, subscriberId,
        paymentInstrumentName="Mobile Account", amount
    Success is statusCode == "S1000".
    """
    external_trx_id = _external_trx_id()
    payload = {
        "applicationId": settings.bdapps_app_id,
        "password": settings.bdapps_app_password,
        "externalTrxId": external_trx_id,
        "subscriberId": subscriber_id,
        "paymentInstrumentName": "Mobile Account",
        "amount": f"{amount_bdt:.2f}",
    }

    if settings.bdapps_sandbox:
        status_code, status_detail = "S1000", "Success (sandbox simulation)"
    else:
        status_code, status_detail = await _post_real(payload)

    success = status_code == "S1000"
    receipt = {
        "external_trx_id": external_trx_id,
        "subscriber_id": subscriber_id,
        "amount_bdt": amount_bdt,
        "items": items,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "mode": "sandbox" if settings.bdapps_sandbox else "live-sandbox",
        "session_id": session_id,
    }
    return CheckoutResponse(
        success=success,
        external_trx_id=external_trx_id,
        status_code=status_code,
        status_detail=status_detail,
        amount_bdt=amount_bdt,
        receipt=receipt,
    )


async def _post_real(payload: dict[str, Any]) -> tuple[str, str]:
    """POST to the real bdapps CaaS endpoint; return (statusCode, statusDetail).

    TODO: verify the exact endpoint/field names against the bdapps tap API docs
    for your app; handle non-S1000 status codes.
    """
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        r = await client.post(settings.bdapps_caas_url, json=payload)
        data = r.json()
    return str(data.get("statusCode", "")), str(data.get("statusDetail", ""))
