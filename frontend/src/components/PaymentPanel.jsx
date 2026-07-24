import { useEffect, useMemo, useState } from "react";
import { checkout, listReceipts, getPaymentMode } from "../lib/api.js";

// Tier 2 — bdapps CaaS checkout. The farmer unlocks premium advisory by
// charging their mobile-operator balance (Charging-as-a-Service). Line items
// are priced, so the backend sums the basket itself; we never send a total the
// server would have to trust. On success we push the bdapps request/response
// into the live agent trace so a judge can see the real call.
// Test price: 1 BDT, matching the charge configured on the provisioned bdapps
// app (APP_139265). One purchase unlocks the full season calendar and sends
// the farmer's first weather/pest alert by SMS.
function defaultItems(crop) {
  const plan = crop ? `${crop} season pack` : "season pack";
  return [
    {
      name: `AgriSense Premium — ${plan} (full calendar + SMS alerts)`,
      qty: 1,
      unit_price_bdt: 1,
    },
  ];
}

export default function PaymentPanel({ sessionId, crop, onCharged, onPaid }) {
  const [subscriber, setSubscriber] = useState("01712345678");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [history, setHistory] = useState([]);
  const [sandbox, setSandbox] = useState(null); // null until we learn the mode

  useEffect(() => {
    getPaymentMode()
      .then((m) => setSandbox(m.sandbox))
      .catch(() => setSandbox(null));
  }, []);

  const items = useMemo(() => defaultItems(crop), [crop]);
  const total = items.reduce((s, i) => s + i.qty * i.unit_price_bdt, 0);

  async function refreshHistory() {
    if (!sessionId) return;
    try {
      const res = await listReceipts(sessionId);
      setHistory(res.receipts || []);
    } catch {
      /* history is best-effort */
    }
  }

  useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  async function pay() {
    if (busy || !sessionId) return;
    setBusy(true);
    setError(null);
    try {
      // No amount passed — the server sums the priced basket (authoritative).
      const res = await checkout(sessionId, subscriber, items);
      // Carry the charge status into the receipt so the card is honest even
      // when a live charge is declined (wrong key, non-whitelisted number…).
      setReceipt({
        ...res.receipt,
        success: res.success,
        status_code: res.status_code,
        status_detail: res.status_detail,
      });
      if (res.trace?.length) onCharged?.(res.trace);
      if (res.success) onPaid?.();
      refreshHistory();
    } catch (e) {
      setError(e.message || "payment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card payment">
      <h2>
        Premium advisory · bdapps CaaS
        {sandbox === false ? (
          <span className="badge live">LIVE</span>
        ) : sandbox === true ? (
          <span className="badge sandbox">SANDBOX</span>
        ) : null}
      </h2>
      <p className="hint">
        Pay from your mobile balance to unlock the full season plan and
        season-long weather &amp; pest SMS alerts — no card or bank needed.
      </p>

      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i}>
              <td>{it.name}</td>
              <td>{it.qty}</td>
              <td>{it.unit_price_bdt} BDT</td>
              <td>{it.qty * it.unit_price_bdt} BDT</td>
            </tr>
          ))}
          <tr className="total-row">
            <td colSpan={3}>Total</td>
            <td>{total} BDT</td>
          </tr>
        </tbody>
      </table>

      <label className="pay-field">
        <span>Mobile number</span>
        <input
          value={subscriber}
          onChange={(e) => setSubscriber(e.target.value)}
          placeholder="01712345678"
          disabled={busy}
        />
      </label>

      <button className="pay-btn" onClick={pay} disabled={busy || !sessionId}>
        {busy ? "Charging…" : `Pay ${total} BDT via mobile balance`}
      </button>
      {!sessionId && (
        <p className="hint">Start a conversation first so the receipt is linked to your farm.</p>
      )}
      {error && <p className="pay-error">⚠️ {error}</p>}

      {receipt && (
        <div className={`receipt ${receipt.success === false ? "declined" : "ok"}`}>
          <div className="receipt-head">
            <span className="tick">{receipt.success === false ? "✕" : "✓"}</span>
            <div>
              <strong>
                {receipt.success === false ? "Payment declined" : "Payment successful"}
              </strong>
              <div className="hint">
                {receipt.success === false
                  ? receipt.status_detail || "charge was declined by bdapps"
                  : `Mobile-operator balance charged${
                      receipt.mode === "live" ? " (live)" : " (sandbox)"
                    }`}
              </div>
            </div>
            <span className="amt">{receipt.amount_bdt} BDT</span>
          </div>
          <dl className="metrics">
            <div><dt>Transaction</dt><dd>{receipt.external_trx_id}</dd></div>
            <div>
              <dt>Status</dt>
              <dd>
                {receipt.status_code || "S1000"} ·{" "}
                {receipt.success === false ? "declined" : "success"}
              </dd>
            </div>
            <div><dt>Subscriber</dt><dd>{receipt.subscriber_id}</dd></div>
            <div><dt>Instrument</dt><dd>Mobile Account</dd></div>
            {receipt.reference_id && (
              <div><dt>Reference</dt><dd>{receipt.reference_id}</dd></div>
            )}
          </dl>
          {receipt.sms && (
            <div className={`sms-status ${receipt.sms.status_code === "S1000" ? "ok" : "fail"}`}>
              <strong>
                📩 Alert SMS {receipt.sms.status_code === "S1000" ? "sent" : "failed"}
                {receipt.sms.mode === "live" ? " (live)" : " (sandbox)"}
              </strong>{" "}
              to {receipt.sms.to}
              <div className="sms-preview">“{receipt.sms.preview}”</div>
            </div>
          )}
          <p className="assumptions">
            bdapps CaaS Direct Debit contract · endpoint {receipt.endpoint} ·{" "}
            {receipt.mode === "live"
              ? "LIVE — real charge against the operator balance."
              : "sandbox simulation (no real money moves)."}
          </p>
        </div>
      )}

      {history.length > 0 && (
        <>
          <h3>Payment history</h3>
          <table className="history">
            <thead>
              <tr>
                <th>When</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Transaction</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => (
                <tr key={r.external_trx_id}>
                  <td>{r.paid_at ? new Date(r.paid_at).toLocaleString() : "—"}</td>
                  <td>{r.amount_bdt} BDT</td>
                  <td className={r.success ? "ok-text" : "declined-text"}>
                    {r.status_code}
                  </td>
                  <td className="mono">{r.external_trx_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
