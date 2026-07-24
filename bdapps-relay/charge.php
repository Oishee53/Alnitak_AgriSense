<?php
/**
 * AgriSense — bdapps CaaS Direct Debit relay.
 *
 * Deploy this ON the bdapps hosting whose IP is whitelisted for the app
 * (e.g. 103.108.140.219). Our Python backend POSTs the transaction here; this
 * script makes the real bdapps Direct Debit call from the allowed IP, so the
 * charge is not rejected with E1303 (originating IP not provisioned).
 *
 * Request (JSON, from our backend):
 *   { "secret": "...", "externalTrxId": "...", "subscriberId": "tel:8801...",
 *     "amount": "1.00", "currency": "BDT", "accountId": "8801...",
 *     "paymentInstrumentName": "Mobile Account" }
 * Response: the bdapps JSON verbatim (statusCode / statusDetail / internalTrxId
 *   / referenceId), so the backend can show the real ids in the receipt.
 *
 * Contract: BDApps API Guide v1.1.3 §5.3 (https://developer.bdapps.com/caas/direct/debit)
 */

// ----- CONFIG: fill these in on the server (do NOT commit real values) -------
$APP_ID       = 'APP_139290';
$API_KEY      = 'PUT_YOUR_32_CHAR_API_KEY_HERE';   // the App Password / API Key
$SHARED_SECRET = 'PUT_A_LONG_RANDOM_SECRET_HERE';  // must match BDAPPS_RELAY_SECRET
$CAAS_URL     = 'https://developer.bdapps.com/caas/direct/debit';
// -----------------------------------------------------------------------------

header('Content-Type: application/json');

function fail($code, $detail, $http = 200) {
    http_response_code($http);
    echo json_encode(array('statusCode' => $code, 'statusDetail' => $detail));
    exit;
}

$raw = file_get_contents('php://input');
$in  = json_decode($raw, true);
if (!is_array($in)) {
    fail('E-RELAY', 'relay: invalid JSON body', 400);
}

// Shared-secret gate — this endpoint moves real money, so reject anyone else.
if (!isset($in['secret']) || !hash_equals($SHARED_SECRET, (string)$in['secret'])) {
    fail('E-RELAY-AUTH', 'relay: bad or missing shared secret', 401);
}

$subscriberId = isset($in['subscriberId']) ? $in['subscriberId'] : '';
$amount       = isset($in['amount']) ? $in['amount'] : '';
$externalTrxId = isset($in['externalTrxId']) ? $in['externalTrxId'] : ('AGRI-' . uniqid());
if ($subscriberId === '' || $amount === '') {
    fail('E-RELAY', 'relay: subscriberId and amount are required', 400);
}

// Build the exact bdapps Direct Debit payload (§5.3.1 comprehensive sample).
$payload = array(
    'applicationId'         => $APP_ID,
    'password'              => $API_KEY,
    'externalTrxId'         => $externalTrxId,
    'subscriberId'          => $subscriberId,
    'paymentInstrumentName' => isset($in['paymentInstrumentName']) ? $in['paymentInstrumentName'] : 'Mobile Account',
    'amount'               => $amount,
    'currency'             => isset($in['currency']) ? $in['currency'] : 'BDT',
);
if (!empty($in['accountId'])) {
    $payload['accountId'] = $in['accountId'];
}

// Same transport as the provided reference SDK (Core::sendRequest).
$ch = curl_init($CAAS_URL);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);
$res = curl_exec($ch);
if ($res === false) {
    fail('E1500', 'relay: curl error: ' . curl_error($ch));
}
curl_close($ch);

// Pass the bdapps response straight back to our backend.
$data = json_decode($res, true);
if (!is_array($data)) {
    fail('E1500', 'relay: unparseable bdapps response: ' . substr($res, 0, 200));
}
echo json_encode($data);
