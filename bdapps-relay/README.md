# bdapps live relay (satisfies the originating-IP allowlist)

bdapps only accepts CaaS (Direct Debit) and SMS Send requests **from a
whitelisted host IP** (for this app: `103.108.140.219`). A request from anywhere
else is rejected with **E1303** — *"IP address from which this request
originated is not provisioned"*. Approving the app + whitelisting a subscriber
number does **not** change this: the IP check is separate.

Our AgriSense backend is Python/FastAPI and (during the hackathon) runs on a
laptop, so its requests leave from the wrong IP. These two tiny PHP files run
**on the whitelisted host** and make the real bdapps call from the allowed IP.
Flow:

```
Python backend (anywhere)  --POST txn + secret-->  charge.php on 103.108.140.219
                                                        |
                                                        |  real bdapps call
                                                        v  (from allowed IP)
                                              bdapps CaaS  ->  S1000  ✅
```

## Files
- `charge.php` — CaaS Direct Debit relay (BDApps API Guide §5.3)
- `sms.php` — SMS Send relay (§3.1), for the paid alert SMS

## Deploy (once)
1. On the bdapps hosting for `103.108.140.219`, create a folder, e.g. `agri/`,
   and upload `charge.php` and `sms.php` into it. (Same hosting profile as the
   PPT "Create Hosting Profile" step.)
2. Edit both files and fill the three constants at the top:
   - `$APP_ID` = `APP_139290`
   - `$API_KEY` = your 32-char API Key (the App Password shown in the console)
   - `$SHARED_SECRET` = a long random string (generate one; keep it private)
3. Note the public URLs, e.g.
   - `https://103.108.140.219/agri/charge.php`
   - `https://103.108.140.219/agri/sms.php`

## Point the backend at the relay
In `backend/.env`:
```
BDAPPS_SANDBOX=false
BDAPPS_RELAY_URL=https://103.108.140.219/agri/charge.php
BDAPPS_SMS_RELAY_URL=https://103.108.140.219/agri/sms.php
BDAPPS_RELAY_SECRET=<the same $SHARED_SECRET you put in the PHP files>
```
Restart the backend. Now a 1 BDT checkout charges for real (from the allowed
IP) and the receipt shows the real `internalTrxId` / `referenceId`.

## Test the relay directly (optional)
```bash
curl -k -X POST https://103.108.140.219/agri/charge.php \
  -H "Content-Type: application/json" \
  -d '{"secret":"<secret>","externalTrxId":"AGRI-TEST1","subscriberId":"tel:8801816213837","amount":"1.00","currency":"BDT","accountId":"8801816213837","paymentInstrumentName":"Mobile Account"}'
```
Expect `{"statusCode":"S1000",...}` (charges 1 BDT to the whitelisted number).

## Security notes
- The `$SHARED_SECRET` is what stops the public internet from draining balances
  through your relay URL — keep it long and private, and never commit the
  filled-in PHP.
- The API Key lives **only** on the whitelisted host (in the PHP), not shipped
  around — the backend never needs it in relay mode.
- Serve the relay over HTTPS so the secret isn't sent in the clear.
