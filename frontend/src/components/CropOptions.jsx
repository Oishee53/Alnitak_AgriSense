// Ranked crop options (Tier-0 #3). Feasible crops ranked by suitability +
// risk-adjusted profit, with a farmer-facing PRIORITY selector (balanced /
// most profit / lowest risk), plain-language method summary, the `because`
// reasoning, KB citations, and the crops ruled out and why.
const RISK_COLOR = { low: "#4caf50", medium: "#e0a458", high: "#e05858" };

const PRIORITIES = [
  { key: "balanced", label: "⚖️ Balanced" },
  { key: "profit", label: "💰 Most profit" },
  { key: "safe", label: "🛡️ Lowest risk" },
];

function bdt(n) {
  return n == null ? "—" : `${Math.round(n).toLocaleString()} BDT`;
}

export default function CropOptions({ data, busy, onPick, onPriority }) {
  if (!data?.options?.length && !data?.excluded?.length) return null;
  const active = data.inputs_used?.priority || "balanced";

  return (
    <div className="card crops">
      <h2>Crop options</h2>

      <p className="rank-summary">
        Crops that don't fit your season, water, or budget were removed, then the
        rest ranked by how well they suit your farm and their profit after risk.
      </p>

      {onPriority && (
        <div className="priority-picker">
          <span className="priority-label">Rank for:</span>
          {PRIORITIES.map((p) => (
            <button
              key={p.key}
              className={active === p.key ? "active" : ""}
              disabled={busy}
              onClick={() => active !== p.key && onPriority(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      <div className="crop-list">
        {data.options.map((o, i) => (
          <div key={o.crop} className={`crop-opt ${i === 0 ? "best" : ""}`}>
            <div className="crop-head">
              <span className="crop-rank">#{i + 1}</span>
              <span className="crop-name">{o.crop}</span>
              <span className="crop-suit">suitability {Math.round(o.suitability * 100)}%</span>
              {!o.in_season && <span className="crop-off">off-season</span>}
            </div>
            <div className="crop-meta">
              <span>💧 {o.water_need}</span>
              <span style={{ color: RISK_COLOR[o.risk] || "inherit" }}>
                ⚠ risk: {o.risk}
              </span>
              <span>📅 {o.sowing_window}</span>
            </div>
            <div className="crop-profit">
              <span className="profit-main">≈ {bdt(o.risk_adjusted_profit_bdt_per_acre)}/acre profit</span>
              {o.expected_profit_bdt_per_acre != null &&
                o.expected_profit_bdt_per_acre !== o.risk_adjusted_profit_bdt_per_acre && (
                  <span className="profit-sub">
                    ({bdt(o.expected_profit_bdt_per_acre)} before risk discount)
                  </span>
                )}
            </div>
            {o.affordable_acres != null &&
              o.affordable_acres < (data.inputs_used?.farm_size_acres ?? Infinity) && (
                <p className="crop-afford">
                  💡 Budget covers about {o.affordable_acres} acre of this crop —
                  consider a smaller area.
                </p>
              )}
            <p className="crop-because">{o.because}</p>
            {onPick && (
              <button className="crop-pick" disabled={busy} onClick={() => onPick(o.crop)}>
                {busy ? "Working…" : "Plan this crop"}
              </button>
            )}
          </div>
        ))}
      </div>

      {data.excluded?.length > 0 && (
        <details className="excluded">
          <summary>Ruled out ({data.excluded.length}) — why these don't fit</summary>
          <ul>
            {data.excluded.map((e) => (
              <li key={e.crop}>
                <strong>{e.crop}</strong> — {e.reasons.join("; ")}
              </li>
            ))}
          </ul>
        </details>
      )}

      {data.ranking_method && (
        <details className="method">
          <summary>ⓘ How these are ranked</summary>
          <p>{data.ranking_method}</p>
        </details>
      )}

      {data.weather_note && <p className="warning">ℹ {data.weather_note}</p>}
      {data.kb_references?.length > 0 && (
        <p className="kb-refs">
          KB sources:{" "}
          {[...new Set(data.kb_references.map((r) => r.source))].join(", ")}
        </p>
      )}
      {data.note && <p className="assumptions">{data.note}</p>}
    </div>
  );
}
