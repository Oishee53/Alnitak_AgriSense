// Ranked crop options (Tier-0 #3). Feasible crops ranked by suitability +
// risk-adjusted profit, with a farmer-facing PRIORITY selector (balanced /
// most profit / lowest risk), plain-language method summary, the `because`
// reasoning, KB citations, and the crops ruled out and why.
// In Bangla mode BOTH the labels (static dictionary) and the templated DATA
// strings (deterministic pattern translation in lib/bn.js — translate, not
// generate) are rendered in Bangla. Numbers stay Western so they match the
// trace; unrecognized free text falls back to English rather than garbling.
import { t } from "../lib/i18n.js";
import { localize, tk, cropName, d } from "../lib/bn.js";

const RISK_COLOR = { low: "#4caf50", medium: "#e0a458", high: "#e05858" };

const PRIORITIES = [
  { key: "balanced", labelKey: "crops.balanced" },
  { key: "profit", labelKey: "crops.profit" },
  { key: "safe", labelKey: "crops.safe" },
];

function bdt(n, lang) {
  return n == null ? "—" : `${d(Math.round(n).toLocaleString(), lang)} BDT`;
}

export default function CropOptions({ data, busy, onPick, onPriority, lang = "en" }) {
  if (!data?.options?.length && !data?.excluded?.length) return null;
  const active = data.inputs_used?.priority || "balanced";

  return (
    <div className="card crops">
      <h2>{t(lang, "crops.title")}</h2>

      <p className="rank-summary">{t(lang, "crops.summary")}</p>

      {onPriority && (
        <div className="priority-picker">
          <span className="priority-label">{t(lang, "crops.rankFor")}</span>
          {PRIORITIES.map((p) => (
            <button
              key={p.key}
              className={active === p.key ? "active" : ""}
              disabled={busy}
              onClick={() => active !== p.key && onPriority(p.key)}
            >
              {t(lang, p.labelKey)}
            </button>
          ))}
        </div>
      )}

      <div className="crop-list">
        {data.options.map((o, i) => (
          <div key={o.crop} className={`crop-opt ${i === 0 ? "best" : ""}`}>
            <div className="crop-head">
              <span className="crop-rank">#{d(i + 1, lang)}</span>
              <span className="crop-name">{cropName(o.crop, lang)}</span>
              <span className="crop-suit">
                {t(lang, "crops.suitability")} {d(Math.round(o.suitability * 100), lang)}%
              </span>
              {!o.in_season && (
                <span className="crop-off">{t(lang, "crops.offseason")}</span>
              )}
            </div>
            <div className="crop-meta">
              <span>💧 {tk(o.water_need, lang)}</span>
              <span style={{ color: RISK_COLOR[o.risk] || "inherit" }}>
                ⚠ {t(lang, "crops.risk")} {tk(o.risk, lang)}
              </span>
              <span>📅 {localize(o.sowing_window, lang)}</span>
            </div>
            <div className="crop-profit">
              <span className="profit-main">
                ≈ {bdt(o.risk_adjusted_profit_bdt_per_acre, lang)}
                {t(lang, "crops.acreProfit")}
              </span>
              {o.expected_profit_bdt_per_acre != null &&
                o.expected_profit_bdt_per_acre !== o.risk_adjusted_profit_bdt_per_acre && (
                  <span className="profit-sub">
                    ({bdt(o.expected_profit_bdt_per_acre, lang)}{" "}
                    {t(lang, "crops.beforeDiscount")})
                  </span>
                )}
            </div>
            {o.affordable_acres != null &&
              o.affordable_acres < (data.inputs_used?.farm_size_acres ?? Infinity) && (
                <p className="crop-afford">
                  {t(lang, "crops.afford1")}
                  {d(o.affordable_acres, lang)}
                  {t(lang, "crops.afford2")}
                </p>
              )}
            <p className="crop-because">{localize(o.because, lang)}</p>
            {onPick && (
              <button className="crop-pick" disabled={busy} onClick={() => onPick(o.crop)}>
                {busy ? t(lang, "crops.working") : t(lang, "crops.pick")}
              </button>
            )}
          </div>
        ))}
      </div>

      {data.excluded?.length > 0 && (
        <details className="excluded">
          <summary>
            {t(lang, "crops.ruledOut1")}
            {data.excluded.length}
            {t(lang, "crops.ruledOut2")}
          </summary>
          <ul>
            {data.excluded.map((e) => (
              <li key={e.crop}>
                <strong>{cropName(e.crop, lang)}</strong> —{" "}
                {e.reasons.map((r) => localize(r, lang)).join("; ")}
              </li>
            ))}
          </ul>
        </details>
      )}

      {data.ranking_method && (
        <details className="method">
          <summary>{t(lang, "crops.how")}</summary>
          <p>{data.ranking_method}</p>
        </details>
      )}

      {data.weather_note && (
        <p className="warning">ℹ {localize(data.weather_note, lang)}</p>
      )}
      {data.kb_references?.length > 0 && (
        <p className="kb-refs">
          {t(lang, "crops.kb")}{" "}
          {[...new Set(data.kb_references.map((r) => r.source))].join(", ")}
        </p>
      )}
      {data.note && <p className="assumptions">{localize(data.note, lang)}</p>}
    </div>
  );
}
