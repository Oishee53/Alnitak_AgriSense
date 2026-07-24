"""bdapps CaaS payment tests (Tier 2).

Covers the pieces where a bug would either charge the wrong amount, mis-address
the subscriber, or silently lose a receipt: number normalization, the
server-authoritative basket total, the sandbox charge contract, and the full
HTTP checkout -> receipt -> history round-trip.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.bdapps.caas import charge, normalize_subscriber_id
from app.api.routes_payment import _basket_total
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _force_sandbox(monkeypatch):
    """Keep payment tests deterministic and offline no matter what mode the
    developer's .env is in (e.g. BDAPPS_SANDBOX=false for a live phone test)."""
    from app.config import settings

    monkeypatch.setattr(settings, "bdapps_sandbox", True)


# ---- subscriber normalization -------------------------------------------
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("01712345678", "tel:8801712345678"),
        ("8801712345678", "tel:8801712345678"),
        ("+8801712345678", "tel:8801712345678"),
        ("tel:8801712345678", "tel:8801712345678"),
        ("01712-345 678", "tel:8801712345678"),
    ],
)
def test_subscriber_normalization_valid(raw, expected):
    norm, err = normalize_subscriber_id(raw)
    assert err is None
    assert norm == expected


@pytest.mark.parametrize("raw", ["", "017", "abc", "0171234567", "018123456789"])
def test_subscriber_normalization_invalid(raw):
    norm, err = normalize_subscriber_id(raw)
    assert norm is None and err


# ---- basket total (server-authoritative) --------------------------------
def test_basket_total_sums_priced_lines():
    items = [
        {"name": "Premium", "qty": 1, "unit_price_bdt": 50},
        {"name": "SMS pack", "qty": 2, "unit_price_bdt": 30},
    ]
    assert _basket_total(items) == 110.0


def test_basket_total_none_when_unpriced():
    assert _basket_total([{"name": "x", "qty": 1}]) is None
    assert _basket_total([]) is None


# ---- sandbox charge contract --------------------------------------------
@pytest.mark.asyncio
async def test_sandbox_charge_returns_s1000_and_masks_password(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "bdapps_app_password", "supersecret")
    monkeypatch.setattr(settings, "bdapps_sandbox", True)
    resp = await charge(
        subscriber_id="tel:8801712345678",
        amount_bdt=80,
        items=[{"name": "Premium", "qty": 1, "unit_price_bdt": 80}],
        session_id="unit-test",
    )
    assert resp.success and resp.status_code == "S1000"
    assert resp.external_trx_id.startswith("AGRI-")
    req = resp.receipt["request"]
    # The mobile-account contract fields the SDK sends, password never exposed.
    assert req["paymentInstrumentName"] == "Mobile Account"
    assert req["amount"] == "80.00"
    assert req["subscriberId"] == "tel:8801712345678"
    assert "supersecret" not in str(resp.receipt)


# ---- full HTTP round-trip -----------------------------------------------
def test_checkout_sums_basket_and_persists_receipt():
    sid = f"test-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/payment/checkout",
        json={
            "session_id": sid,
            "subscriber_id": "01712-345678",  # messy input, must normalize
            "items": [
                {"name": "AgriSense Premium", "qty": 1, "unit_price_bdt": 50},
                {"name": "SMS alerts", "qty": 1, "unit_price_bdt": 30},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["status_code"] == "S1000"
    assert body["amount_bdt"] == 80.0  # server summed the basket
    assert body["receipt"]["subscriber_id"] == "tel:8801712345678"
    # Trace: the charge (call + result) and the paid alert SMS delivery.
    tools = [s["tool"] for s in body["trace"]]
    assert tools == [
        "bdapps_caas_charge",
        "bdapps_caas_charge",
        "bdapps_sms_send",
    ]
    # The paid deliverable: an alert SMS to the charged number.
    assert body["receipt"]["sms"]["status_code"] == "S1000"
    assert body["receipt"]["sms"]["to"] == "tel:8801712345678"
    assert body["receipt"]["sms"]["preview"]

    # Receipt persisted and retrievable.
    hist = client.get(f"/api/payment/receipts/{sid}").json()["receipts"]
    assert len(hist) == 1
    assert hist[0]["external_trx_id"] == body["external_trx_id"]
    assert hist[0]["amount_bdt"] == 80.0


# ---- alert SMS composition ----------------------------------------------
def test_sms_composed_from_weather_alert_first():
    from app.bdapps.sms import compose_alert_sms

    arts = {
        "weather_alerts": {
            "alerts": [
                {
                    "date": "2026-08-06",
                    "recommendation": "Delay the urea top-dress 2 days; 21.8 mm rain.",
                }
            ]
        },
        "season_plan": {"crop": "T. Aman Rice"},
    }
    msg = compose_alert_sms(arts)
    assert "2026-08-06" in msg and "urea" in msg.lower()


def test_sms_welcome_when_no_alerts():
    from app.bdapps.sms import compose_alert_sms

    msg = compose_alert_sms({"season_plan": {"crop": "T. Aman Rice"}})
    assert "T. Aman Rice" in msg
    assert "alert" in msg.lower()


@pytest.mark.asyncio
async def test_relay_mode_posts_txn_and_secret_not_credentials(monkeypatch):
    """In relay mode the backend sends the txn + shared secret to the relay
    URL (never the app password), and passes the relay's bdapps response back."""
    from app.bdapps import caas
    from app.config import settings

    monkeypatch.setattr(settings, "bdapps_sandbox", False)
    monkeypatch.setattr(settings, "bdapps_relay_url", "https://relay.test/charge.php")
    monkeypatch.setattr(settings, "bdapps_relay_secret", "s3cr3t")
    monkeypatch.setattr(settings, "bdapps_app_password", "SHOULD_NOT_BE_SENT")

    captured = {}

    class _Resp:
        def json(self):
            return {
                "statusCode": "S1000",
                "statusDetail": "Success",
                "internalTrxId": "INT123",
                "referenceId": "88887777",
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["body"] = json
            return _Resp()

    monkeypatch.setattr(caas.httpx, "AsyncClient", _Client)

    resp = await caas.charge("tel:8801816213837", 1.0, [], "sess")

    assert captured["url"] == "https://relay.test/charge.php"
    assert captured["body"]["secret"] == "s3cr3t"
    assert captured["body"]["subscriberId"] == "tel:8801816213837"
    # The app password must NOT travel to the relay (it lives on the host).
    assert "password" not in captured["body"]
    assert "SHOULD_NOT_BE_SENT" not in str(captured["body"])
    # The relay's bdapps ids flow back into the receipt.
    assert resp.success is True
    assert resp.receipt["internal_trx_id"] == "INT123"
    assert resp.receipt["reference_id"] == "88887777"
    assert "via relay" in resp.receipt["endpoint"]


def test_checkout_rejects_bad_number():
    r = client.post(
        "/api/payment/checkout",
        json={"session_id": "x", "subscriber_id": "017",
              "items": [{"name": "a", "qty": 1, "unit_price_bdt": 50}]},
    )
    assert r.status_code == 400


def test_checkout_rejects_nonpositive_amount():
    r = client.post(
        "/api/payment/checkout",
        json={"session_id": "x", "subscriber_id": "01712345678",
              "amount_bdt": 0, "items": []},
    )
    assert r.status_code == 400
