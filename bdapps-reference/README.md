# bdapps-reference (provided PHP — reference only)

These are the **original bdapps integration PHP files provided with the problem
set**. They are kept here as a reference for the request/response contracts of the
bdapps platform APIs. **Our application does not run these files** — our CaaS
integration is reimplemented in Python at
[`backend/app/bdapps/caas.py`](../backend/app/bdapps/caas.py) (sandbox mode).

> Per the hackathon rules, all application code is written during the event. This
> folder is vendor-provided reference material, clearly labelled as such.

## What each file does
| File | Purpose |
|------|---------|
| `sdk_file.php` | Core bdapps SDK: `SMSSender`, `UssdSender`, **`DirectDebitSender` (CaaS charging)**, `Subscription`, `WebApi` |
| `send_otp.php` | Request an OTP for a subscriber (`/subscription/otp/request`) |
| `verify_otp.php` | Verify an OTP (`/subscription/otp/verify`) |
| `check_subscription.php` | Query subscription status (`/subscription/getStatus`) |
| `unsubscribe.php` | Unsubscribe a subscriber (`/subscription/send`, action=0) |
| `subscription_listener.php` | Webhook: receives subscription notifications |
| `sms.php` | Mobile-originated SMS receiver + broadcast |
| `ussd.php` | USSD session handler (subscribe / unsubscribe menu) |

## Credentials
Every `applicationId` / `password` field in these files is **blank**. They come
from the bdapps provisioning console for a specific app (see
`../docs/bdapps-setup.md`). Do **not** commit real credentials — use `.env`.

## Key contract detail (for our Python CaaS)
`DirectDebitSender::cass()` posts:
```json
{
  "applicationId": "...", "password": "...",
  "externalTrxId": "...", "subscriberId": "tel:8801XXXXXXXXX",
  "paymentInstrumentName": "Mobile Account", "amount": "2.00"
}
```
Success is `statusCode == "S1000"`. Our `caas.charge()` mirrors this.
