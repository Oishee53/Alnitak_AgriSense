// Fertilizer & irrigation scheduler (Tier 1). Shows exactly how many kg of each
// input go on which date, what it costs, the organic alternative, and — most
// importantly — any urea top-dress the live forecast says to delay.

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function fmtDay(iso) {
  if (!iso) return "";
  const [, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}

const bdt = (n) => (n == null ? "—" : `${Math.round(n).toLocaleString()} BDT`);

export default function FertilizerView({ schedule }) {
  if (!schedule || schedule.error) return null;
  const s = schedule;

  const noDoses = s.doses_available === false;

  return (
    <div className="card fert-view">
      <h2>🧪 Fertilizer &amp; irrigation · {s.crop}</h2>
      <p className="sub">
        {s.farm_size_acres} acre · {s.soil_type} soil · anchored on sowing{" "}
        <strong>{fmtDay(s.sowing_anchor)}</strong>
        {!noDoses && (
          <>
            {" "}
            · total fertilizer bill <strong>{bdt(s.total_fertilizer_cost_bdt)}</strong>
          </>
        )}
      </p>

      {noDoses && (
        <p className="warning">⚠ {s.quantities_note}</p>
      )}

      {s.adjustments_applied?.map((a, i) => (
        <p key={i} className="adjust-note">⚙ {a}</p>
      ))}

      <h3>Application schedule</h3>
      <ul className="fert-stages">
        {s.fertilizer_schedule?.map((st, i) => (
          <li key={i} className={st.weather_alert ? "fert-stage alert" : "fert-stage"}>
            <div className="fert-head">
              <span className="fert-date">{fmtDay(st.date)}</span>
              <span className="fert-das">{st.das >= 0 ? `+${st.das}` : st.das}d</span>
              <span className="fert-stage-name">{st.stage}</span>
              <span className="fert-cost">{bdt(st.stage_cost_bdt)}</span>
            </div>
            <div className="fert-inputs">
              {st.inputs?.map((it, j) => (
                <span key={j} className="fert-chip">
                  {it.input} <strong>{it.kg} kg</strong>
                </span>
              ))}
            </div>
            {st.because && <div className="cal-because">{st.because}</div>}
            {st.weather_alert && (
              <div className="weather-alert">⛈ {st.weather_alert}</div>
            )}
          </li>
        ))}
      </ul>

      {s.irrigation_schedule?.length > 0 && (
        <>
          <h3>Irrigation</h3>
          <ul className="irrig-list">
            {s.irrigation_schedule.map((ir, i) => (
              <li key={i}>
                <span className="fert-date">{fmtDay(ir.date)}</span>
                <div className="cal-body">
                  <div className="cal-stage-name">
                    {ir.event}
                    {ir.condition !== "always" && (
                      <span className="cond-tag"> · {ir.condition}</span>
                    )}
                  </div>
                  <div className="cal-action">{ir.action}</div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {s.cost_breakdown?.length > 0 && (
        <>
      <h3>Season total by input</h3>
      <table>
        <thead>
          <tr>
            <th>Input</th>
            <th>kg/acre</th>
            <th>kg total</th>
            <th>BDT/kg</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {s.cost_breakdown?.map((c, i) => (
            <tr key={i}>
              <td>{c.input}</td>
              <td>{c.kg_per_acre}</td>
              <td>{c.kg_total}</td>
              <td>{c.price_bdt_per_kg}</td>
              <td>{Math.round(c.cost_bdt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
        </>
      )}

      {s.organic_alternatives?.length > 0 && (
        <div className="organic-box">
          <h3>🌿 Organic alternative</h3>
          {s.organic_alternatives.map((o, i) => (
            <p key={i}>
              <strong>{o.input}</strong> — {o.qty_kg_total.toLocaleString()} kg total (
              {o.qty_kg_per_acre.toLocaleString()} kg/acre), replaces {o.replaces}.
              <br />
              <span className="cal-because">{o.because}</span>
            </p>
          ))}
        </div>
      )}

      {s.weather_rules?.length > 0 && (
        <details className="rules">
          <summary>Weather rules for fertilizer timing (from the knowledge base)</summary>
          <ol>
            {s.weather_rules.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </details>
      )}

      <p className="assumptions">
        Doses: {s.source}. {s.price_note}
      </p>
    </div>
  );
}
