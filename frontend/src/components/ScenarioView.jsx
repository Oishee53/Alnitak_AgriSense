// Scenario simulation (Tier 1). Baseline vs what-if side by side, with every
// number recomputed by the finance engine — the deltas are the whole point, so
// changed rows are highlighted and unchanged ones stay quiet.
// In Bangla mode labels come from the static dictionary and the templated
// verdict/reasoning strings go through lib/bn.js (translate, not generate).
import { t } from "../lib/i18n.js";
import { localize, tk, cropName, d as bd } from "../lib/bn.js";

const fmt = (v, unit, lang) => {
  if (v == null) return "—";
  if (unit === "ratio") return `${bd((v * 100).toFixed(1), lang)}%`;
  if (typeof v !== "number") return bd(String(v), lang);
  return bd(v.toLocaleString(undefined, { maximumFractionDigits: 2 }), lang);
};

function Delta({ row, lang }) {
  const changed = row.change != null && row.change !== 0;
  const good = changed && row.change > 0;
  const isCost = /cost|break-even/i.test(row.metric);
  // For costs and break-even, up is bad; for profit/revenue/yield, up is good.
  const positive = isCost ? !good : good;

  return (
    <tr className={changed ? "delta-row changed" : "delta-row"}>
      <td>{localize(row.metric, lang)}</td>
      <td>{fmt(row.before, row.unit, lang)}</td>
      <td>
        <strong>{fmt(row.after, row.unit, lang)}</strong>
      </td>
      <td className={changed ? (positive ? "delta-up" : "delta-down") : ""}>
        {changed ? (
          <>
            {row.change > 0 ? "+" : ""}
            {fmt(row.change, row.unit, lang)}
            {row.change_pct != null && (
              <span className="delta-pct">
                {" "}
                ({row.change_pct > 0 ? "+" : ""}
                {bd(row.change_pct, lang)}%)
              </span>
            )}
          </>
        ) : (
          <span className="delta-none">{t(lang, "scen.noChange")}</span>
        )}
      </td>
    </tr>
  );
}

const LABEL_KEYS = {
  rainfall_pct: "scen.rainfall",
  budget_pct: "scen.budget",
  new_budget_bdt: "scen.newBudget",
  price_pct: "scen.price",
  yield_pct: "scen.yield",
  cost_pct: "scen.inputCosts",
};

export default function ScenarioView({ scenario, lang = "en" }) {
  if (!scenario || scenario.error) return null;
  const s = scenario;
  const applied = s.scenario_applied || {};
  const worse = (s.net_profit_change_bdt ?? 0) < 0;

  return (
    <div className="card scenario-view">
      <h2>{t(lang, "scen.title")} · {cropName(s.crop, lang)}</h2>

      <div className="scenario-chips">
        {Object.entries(applied).map(([k, v]) => (
          <span key={k} className="scenario-chip">
            {LABEL_KEYS[k] ? t(lang, LABEL_KEYS[k]) : k}{" "}
            <strong>
              {k === "new_budget_bdt"
                ? `${bd(Number(v).toLocaleString(), lang)} BDT`
                : `${v > 0 ? "+" : ""}${bd(v, lang)}%`}
            </strong>
          </span>
        ))}
      </div>

      <p className={worse ? "verdict verdict-bad" : "verdict verdict-good"}>
        {localize(s.verdict, lang)}
      </p>

      {s.acreage_reduced && (
        <p className="warning">
          {t(lang, "scen.resized1")}
          {bd(s.scenario?.farm_size_acres, lang)}
          {t(lang, "scen.resized2")}
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>{t(lang, "scen.metric")}</th>
            <th>{t(lang, "scen.baseline")}</th>
            <th>{t(lang, "scen.scenario")}</th>
            <th>{t(lang, "scen.change")}</th>
          </tr>
        </thead>
        <tbody>
          {s.deltas?.map((row, i) => (
            <Delta key={i} row={row} lang={lang} />
          ))}
        </tbody>
      </table>

      {s.reasoning?.length > 0 && (
        <div className="pest-block">
          <strong>{t(lang, "scen.how")}</strong>
          <ul>
            {s.reasoning.map((r, i) => (
              <li key={i} className="cal-because">
                {localize(r, lang)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {s.alternatives_under_new_constraint?.length > 0 && (
        <div className="alt-box">
          <h3>{t(lang, "scen.better")}</h3>
          <ul className="alt-list">
            {s.alternatives_under_new_constraint.map((a, i) => (
              <li key={i}>
                <div className="alt-head">
                  <strong>{cropName(a.crop, lang)}</strong>
                  <span className="pest-type">
                    {tk(a.risk, lang)} {t(lang, "scen.risk")}
                  </span>
                  <span className="alt-profit">
                    ≈ {bd(Math.round(a.risk_adjusted_profit_bdt_per_acre).toLocaleString(), lang)}{" "}
                    BDT{t(lang, "crops.acreProfit")}
                  </span>
                </div>
                <div className="cal-because">{localize(a.because, lang)}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {s.note && <p className="assumptions">{localize(s.note, lang)}</p>}
    </div>
  );
}
