// Market price intelligence (Tier 2). Current price, a small history sparkbar,
// the trend, and the SELL-NOW / STORE / WAIT call with its reasoning. Prices are
// seeded/mock — disclosed at the bottom. Bangla mode: labels from the static
// dictionary, the call + reasoning + disclosure via deterministic lib/bn.js.
import { t } from "../lib/i18n.js";
import { localize, tk, cropName, d, unit } from "../lib/bn.js";

const money = (v, lang) => (v == null ? "—" : d(Number(v).toLocaleString(), lang));

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

export default function MarketView({ market, lang = "en" }) {
  if (!market || market.error) return null;
  const m = market;
  const tr = m.trend || {};
  const arrow = tr.direction === "rising" ? "▲" : tr.direction === "falling" ? "▼" : "▬";
  const rev = m.revenue_estimate;

  return (
    <div className="card market-view">
      <h2>{t(lang, "market.title")} · {cropName(m.crop, lang)}</h2>

      <div className="market-top">
        <div className="market-price">
          <div className="market-now">
            {money(m.current_price_bdt, lang)}{" "}
            <span className="market-unit">
              {t(lang, "market.bdtPer")}{tk(m.unit, lang)}
            </span>
          </div>
          <div className={`market-trend trend-${tr.direction}`}>
            {arrow} {tk(tr.direction, lang)} {tr.change_pct_recent > 0 ? "+" : ""}
            {d(tr.change_pct_recent, lang)}% {t(lang, "market.vsLast")}
          </div>
        </div>
        <SparkBars history={m.history} current={m.current_price_bdt} />
      </div>

      <div className={`market-rec ${callClass(m.recommendation)}`}>
        <div className="market-rec-call">{localize(m.recommendation, lang)}</div>
        <div className="market-rec-because">{localize(m.because, lang)}</div>
      </div>

      {rev && (
        <dl className="metrics market-rev">
          <div>
            <dt>{t(lang, "market.estHarvest")}</dt>
            <dd>
              {money(rev.total_units, lang)} {tk(rev.unit, lang)}
            </dd>
          </div>
          <div>
            <dt>{t(lang, "market.gross")}</dt>
            <dd>{money(rev.gross_revenue_bdt, lang)} {unit("BDT", lang)}</dd>
          </div>
        </dl>
      )}
      {rev && <p className="cal-because">{localize(rev.because, lang)}</p>}

      {m.proxy_note && <p className="warning">⚠ {localize(m.proxy_note, lang)}</p>}
      <p className="assumptions">{localize(m.price_source, lang)}</p>
    </div>
  );
}
