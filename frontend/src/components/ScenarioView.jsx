// Scenario simulation (Tier 1). Baseline vs what-if side by side, with every
// number recomputed by the finance engine — the deltas are the whole point, so
// changed rows are highlighted and unchanged ones stay quiet.

const fmt = (v, unit) => {
  if (v == null) return "—";
  if (unit === "ratio") return `${(v * 100).toFixed(1)}%`;
  if (typeof v !== "number") return String(v);
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

function Delta({ d }) {
  const changed = d.change != null && d.change !== 0;
  const good = changed && d.change > 0;
  const isCost = /cost|break-even/i.test(d.metric);
  // For costs and break-even, up is bad; for profit/revenue/yield, up is good.
  const positive = isCost ? !good : good;

  return (
    <tr className={changed ? "delta-row changed" : "delta-row"}>
      <td>{d.metric}</td>
      <td>{fmt(d.before, d.unit)}</td>
      <td>
        <strong>{fmt(d.after, d.unit)}</strong>
      </td>
      <td className={changed ? (positive ? "delta-up" : "delta-down") : ""}>
        {changed ? (
          <>
            {d.change > 0 ? "+" : ""}
            {fmt(d.change, d.unit)}
            {d.change_pct != null && (
              <span className="delta-pct">
                {" "}
                ({d.change_pct > 0 ? "+" : ""}
                {d.change_pct}%)
              </span>
            )}
          </>
        ) : (
          <span className="delta-none">no change</span>
        )}
      </td>
    </tr>
  );
}

const LABELS = {
  rainfall_pct: "Rainfall",
  budget_pct: "Budget",
  new_budget_bdt: "New budget",
  price_pct: "Price",
  yield_pct: "Yield",
  cost_pct: "Input costs",
};

export default function ScenarioView({ scenario }) {
  if (!scenario || scenario.error) return null;
  const s = scenario;
  const applied = s.scenario_applied || {};
  const worse = (s.net_profit_change_bdt ?? 0) < 0;

  return (
    <div className="card scenario-view">
      <h2>🔮 What-if · {s.crop}</h2>

      <div className="scenario-chips">
        {Object.entries(applied).map(([k, v]) => (
          <span key={k} className="scenario-chip">
            {LABELS[k] || k}{" "}
            <strong>
              {k === "new_budget_bdt"
                ? `${Number(v).toLocaleString()} BDT`
                : `${v > 0 ? "+" : ""}${v}%`}
            </strong>
          </span>
        ))}
      </div>

      <p className={worse ? "verdict verdict-bad" : "verdict verdict-good"}>
        {s.verdict}
      </p>

      {s.acreage_reduced && (
        <p className="warning">
          ⚠ The budget no longer funds the full area — the plan is resized to{" "}
          {s.scenario?.farm_size_acres} acre.
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Baseline</th>
            <th>Scenario</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {s.deltas?.map((d, i) => (
            <Delta key={i} d={d} />
          ))}
        </tbody>
      </table>

      {s.reasoning?.length > 0 && (
        <div className="pest-block">
          <strong>How this was calculated</strong>
          <ul>
            {s.reasoning.map((r, i) => (
              <li key={i} className="cal-because">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {s.alternatives_under_new_constraint?.length > 0 && (
        <div className="alt-box">
          <h3>Better options under this constraint</h3>
          <ul className="alt-list">
            {s.alternatives_under_new_constraint.map((a, i) => (
              <li key={i}>
                <div className="alt-head">
                  <strong>{a.crop}</strong>
                  <span className="pest-type">{a.risk} risk</span>
                  <span className="alt-profit">
                    ≈ {Math.round(a.risk_adjusted_profit_bdt_per_acre).toLocaleString()}{" "}
                    BDT/acre
                  </span>
                </div>
                <div className="cal-because">{a.because}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {s.note && <p className="assumptions">{s.note}</p>}
    </div>
  );
}
