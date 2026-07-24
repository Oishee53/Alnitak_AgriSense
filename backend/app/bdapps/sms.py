"""bdapps SMS Send module (BDApps API Guide v1.1.3 §3.1).

Delivers the paid weather/pest alert to the farmer's phone after a successful
CaaS charge — the "SMS alerts" line in the premium basket is a real deliverable,
not a label. Contract:

    POST https://developer.bdapps.com/sms/send
    { "applicationId", "password", "message",
      "destinationAddresses": ["tel:8801XXXXXXXXX"] }

Success is statusCode == "S1000". Sandbox mode simulates the send so demos
never depend on the network; live mode requires the app's whitelisted test
number (bdapps only delivers to whitelisted numbers until the app is approved).
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

# bdapps splits longer messages itself, but one SMS segment keeps the demo
# (and the operator charge) predictable.
MAX_SMS_CHARS = 320


async def send_sms(subscriber_id: str, message: str) -> dict[str, Any]:
    """Send one SMS to a subscriber. Returns {status_code, status_detail, preview}."""
    text = message[:MAX_SMS_CHARS]
    payload = {
        "applicationId": settings.bdapps_app_id,
        "password": settings.bdapps_app_password,
        "message": text,
        "destinationAddresses": [subscriber_id],
    }

    if settings.bdapps_sandbox:
        status_code, status_detail = "S1000", "SMS sent (sandbox simulation)"
    else:
        # Like CaaS, SMS Send is IP-gated; route via the relay on the
        # whitelisted host when configured, else call bdapps directly.
        if settings.bdapps_sms_relay_url:
            url = settings.bdapps_sms_relay_url
            body = {
                "secret": settings.bdapps_relay_secret,
                "destinationAddresses": [subscriber_id],
                "message": text,
            }
        else:
            url, body = settings.bdapps_sms_url, payload
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                r = await client.post(url, json=body)
                data = r.json()
            status_code = str(data.get("statusCode", "E0000"))
            status_detail = str(data.get("statusDetail", "no statusDetail"))
        except httpx.HTTPError as e:
            status_code, status_detail = "E1500", f"bdapps SMS request failed: {e}"
        except Exception as e:  # noqa: BLE001 - SMS failure must not kill checkout
            status_code, status_detail = "E1500", f"unexpected SMS error: {e}"

    return {
        "status_code": status_code,
        "status_detail": status_detail,
        "to": subscriber_id,
        "preview": text,
        "mode": "sandbox" if settings.bdapps_sandbox else "live",
    }


def compose_alert_sms(artifacts: dict[str, Any] | None) -> str:
    """Build the farmer's first paid alert from the session's artifacts.

    Preference order: the most severe weather alert, then a high pest risk,
    then a welcome that states what they will receive. Kept short and concrete
    — dates and actions, no fluff.
    """
    arts = artifacts or {}

    alerts = ((arts.get("weather_alerts") or {}).get("alerts")) or []
    if alerts:
        top = alerts[0]
        date = top.get("date") or ""
        rec = top.get("recommendation") or top.get("summary") or ""
        return f"AgriSense alert {date}: {rec}"

    risks = ((arts.get("pest_risk") or {}).get("active_risks")) or []
    high = [r for r in risks if str(r.get("risk_level", "")).lower() == "high"]
    if high:
        r = high[0]
        return (
            f"AgriSense pest alert: {r.get('pest')} risk is HIGH. "
            f"{(r.get('prevention') or [''])[0]}"
        )

    crop = ((arts.get("season_plan") or {}).get("crop")) or "your crop"
    return (
        f"AgriSense Premium active for {crop}. You will now receive dated "
        "weather and pest alerts for your season on this number."
    )
