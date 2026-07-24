# bdapps setup (provisioning + CaaS)

Condensed from the provided bdapps how-to decks. Needed only for the Tier-2
payment-gateway feature.

## 1. Account + app
1. Create an account at **user.bdapps.com** → Login.
2. Open **Provisioning** → **Create New App** (choose **Pro**).
3. **Details** → Application Name, Description, **Allowed Host Address(es)**.
4. **Services** → tick the APIs you use — for us: **CaaS** (+ Subscription if you
   gate access). SMS/USSD/Downloadable are optional.
5. **Settings** → configure each selected API, then **Submit**.

## 2. Use bdapps' provided server (optional shortcut)
If you don't host your own backend, bdapps offers a shared dev server. In the
app config use:
- **Allowed Host Address:** `103.108.140.219`
- **SMS receiving URL:** `https://103.108.140.219/api/listener/sms_listener`
- **USSD connection URL:** `https://103.108.140.219/api/listener/ussd_listener`
- **Subscription notification URL:** `https://103.108.140.219/api/listener/sub_listener`
- **Hosting profile:** `http://103.108.140.219`
  (hosting tutorial: https://youtu.be/qItOzLA7dqM?t=321)

> For AgriSense we run our **own** FastAPI backend, so point the listener/host
> fields at wherever the backend is deployed.

## 3. Credentials → .env
From the provisioning console, copy the app's `applicationId` and `password` into
`backend/.env`:
```
BDAPPS_APP_ID=APP_0xxxxx
BDAPPS_APP_PASSWORD=xxxxxxxx
BDAPPS_SANDBOX=false   # true = local simulator, no network
```
Never commit real credentials.

## 4. CaaS flow we implement
`backend/app/bdapps/caas.py::charge()` mirrors the reference
`DirectDebitSender::cass()` (see `bdapps-reference/sdk_file.php`):
checkout → charge request → operator balance deduction → receipt. Success =
`statusCode == "S1000"`.

Official docs: https://dev.bdapps.com/API_Documentation/bdapps_tap_api.html
