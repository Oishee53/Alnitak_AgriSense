<?php
/**
 * AgriSense — bdapps SMS Send relay.
 *
 * Companion to charge.php. Deploy on the whitelisted bdapps host so the paid
 * weather/pest alert SMS is sent from the allowed IP (SMS Send is IP-gated too).
 *
 * Request (JSON, from our backend):
 *   { "secret": "...", "destinationAddresses": ["tel:8801..."], "message": "..." }
 * Response: bdapps JSON verbatim (statusCode / statusDetail).
 *
 * Contract: BDApps API Guide v1.1.3 §3.1 (https://developer.bdapps.com/sms/send)
 */

// ----- CONFIG: fill these in on the server (do NOT commit real values) -------
$APP_ID        = 'APP_139290';
$API_KEY       = 'PUT_YOUR_32_CHAR_API_KEY_HERE';
$SHARED_SECRET = 'PUT_A_LONG_RANDOM_SECRET_HERE';  // must match BDAPPS_RELAY_SECRET
$SMS_URL       = 'https://developer.bdapps.com/sms/send';
// -----------------------------------------------------------------------------

header('Content-Type: application/json');

function fail($code, $detail, $http = 200) {
    http_response_code($http);
    echo json_encode(array('statusCode' => $code, 'statusDetail' => $detail));
    exit;
}

$in = json_decode(file_get_contents('php://input'), true);
if (!is_array($in)) {
    fail('E-RELAY', 'relay: invalid JSON body', 400);
}
if (!isset($in['secret']) || !hash_equals($SHARED_SECRET, (string)$in['secret'])) {
    fail('E-RELAY-AUTH', 'relay: bad or missing shared secret', 401);
}

$addresses = isset($in['destinationAddresses']) ? $in['destinationAddresses'] : array();
$message   = isset($in['message']) ? $in['message'] : '';
if (empty($addresses) || $message === '') {
    fail('E-RELAY', 'relay: destinationAddresses and message are required', 400);
}

$payload = array(
    'applicationId'        => $APP_ID,
    'password'             => $API_KEY,
    'message'              => $message,
    'destinationAddresses' => $addresses,
);

$ch = curl_init($SMS_URL);
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

$data = json_decode($res, true);
if (!is_array($data)) {
    fail('E1500', 'relay: unparseable bdapps response: ' . substr($res, 0, 200));
}
echo json_encode($data);
