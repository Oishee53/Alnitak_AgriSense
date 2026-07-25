// Thin client for the AgriSense backend.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function jsonOrThrow(res) {
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function sendChat(sessionId, message, lang) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, lang }),
  });
  return jsonOrThrow(res); // -> ChatResponse
}

export async function getSession(sessionId) {
  const res = await fetch(`${BASE}/api/session/${sessionId}`);
  return jsonOrThrow(res); // -> ChatResponse (with history)
}

export async function listSessions() {
  const res = await fetch(`${BASE}/api/sessions`);
  return jsonOrThrow(res); // -> {sessions: [{id,label,preview,created_at,message_count}]}
}

export async function getTrace(sessionId) {
  const res = await fetch(`${BASE}/api/trace/${sessionId}`);
  return jsonOrThrow(res);
}

// Live trace via Server-Sent Events. Returns the EventSource so callers can close it.
export function streamTrace(sessionId, onStep) {
  const es = new EventSource(`${BASE}/api/trace/${sessionId}/stream`);
  es.onmessage = (e) => {
    try {
      onStep(JSON.parse(e.data));
    } catch {
      /* ignore keep-alives */
    }
  };
  return es;
}

export async function checkout(sessionId, subscriberId, items, amountBdt) {
  const res = await fetch(`${BASE}/api/payment/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      subscriber_id: subscriberId,
      items,
      // Omitted when priced items are present — the server sums the basket.
      ...(amountBdt != null ? { amount_bdt: amountBdt } : {}),
    }),
  });
  return jsonOrThrow(res); // -> CheckoutResponse (with receipt + trace)
}

export async function listReceipts(sessionId) {
  const res = await fetch(`${BASE}/api/payment/receipts/${sessionId}`);
  return jsonOrThrow(res); // -> { receipts: [...] }
}

export async function getPaymentMode() {
  const res = await fetch(`${BASE}/api/payment/mode`);
  return jsonOrThrow(res); // -> { sandbox: bool, app_id }
}

export async function diagnose(sessionId, imageDataUrl, crop, lang) {
  const res = await fetch(`${BASE}/api/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, image: imageDataUrl, crop, lang }),
  });
  return jsonOrThrow(res); // -> { diagnosis, trace }
}
