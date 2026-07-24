// Market price intelligence (Tier 2). Current price, a small history sparkbar,
// the trend, and the SELL-NOW / STORE / WAIT call with its reasoning. Prices are
// seeded/mock — disclosed at the bottom.

const money = (v) => (v == null ? "—" : Number(v).toLocaleString());

// Recommendation → colour class. "SELL" calls are urgent (clay), STORE/WAIT is
// a hold (green), mixed is neutral (amber).
function callClass(rec) {
  const r = (rec || "").toUpperCase();
  if (r.startsWith("STORE") || r.includes("WAIT")) return "rec-store";
  if (r.includes("OR STORE")) return "rec-mixed";
  return "rec-sell";
}

function SparkBars({ history, current }) {
  const series = [...(history || [])];
  if (series[series.length - 1] !== current) series.push(current);
  if (series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  return (
    <div className="spark" aria-hidden="true">
      {series.map((v, i) => {
        const h = 12 + ((v - min) / span) * 40; // 12–52px
        const last = i === series.length - 1;
        return (
          <span
            key={i}
            className={`spark-bar ${last ? "now" : ""}`}
            style={{ height: `${h}px` }}
            title={`${money(v)}`}
          />
        );
      })}
    </div>
  );
}

export default function MarketView({ market }) {
  if (!market || market.error) return null;
  const m = market;
  const t = m.trend || {};
  const arrow = t.direction === "rising" ? "▲" : t.direction === "falling" ? "▼" : "▬";
  const rev = m.revenue_estimate;

  return (
    <div className="card market-view">
      <h2>💹 Market price · {m.crop}</h2>

      <div className="market-top">
        <div className="market-price">
          <div className="market-now">
            {money(m.current_price_bdt)} <span className="market-unit">BDT / {m.unit}</span>
          </div>
          <div className={`market-trend trend-${t.direction}`}>
            {arrow} {t.direction} {t.change_pct_recent > 0 ? "+" : ""}
            {t.change_pct_recent}% vs last period
          </div>
        </div>
        <SparkBars history={m.history} current={m.current_price_bdt} />
      </div>

      <div className={`market-rec ${callClass(m.recommendation)}`}>
        <div className="market-rec-call">{m.recommendation}</div>
        <div className="market-rec-because">{m.because}</div>
      </div>

      {rev && (
        <dl className="metrics market-rev">
          <div>
            <dt>Est. harvest</dt>
            <dd>
              {money(rev.total_units)} {rev.unit}
            </dd>
          </div>
          <div>
            <dt>Gross at today's price</dt>
            <dd>{money(rev.gross_revenue_bdt)} BDT</dd>
          </div>
        </dl>
      )}
      {rev && <p className="cal-because">{rev.because}</p>}

      {m.proxy_note && <p className="warning">⚠ {m.proxy_note}</p>}
      <p className="assumptions">{m.price_source}</p>
    </div>
  );
}
