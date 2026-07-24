// Proactive weather-triggered advice (Tier 1). Renders the weather_advisory
// artifact: the live forecast window, upcoming plan actions, and dated alerts
// (delay urea before heavy rain, skip a rain-covered irrigation, …) each with
// the triggering forecast numbers and the `because` reasoning.

const SEV = {
  high: { icon: "🔴", cls: "sev-high", label: "act now" },
  warning: { icon: "🟠", cls: "sev-warn", label: "watch" },
  advice: { icon: "🟢", cls: "sev-advice", label: "tip" },
};

const KIND_ICON = {
  "nitrogen-timing": "🧪",
  irrigation: "💧",
  "spray-window": "🐛",
  harvest: "🌾",
  establishment: "🌱",
  "heavy-rain": "🌧️",
  "dry-spell": "☀️",
};

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmtDay(iso) {
  if (!iso) return "";
  const [, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}

export default function WeatherAlerts({ data }) {
  if (!data || data.error) return null;
  const fw = data.forecast_window || {};
  const alerts = data.alerts || [];
  const actions = data.plan_actions_in_window || [];

  return (
    <div className="card weather-alerts">
      <h2>🌦️ Weather alerts · {data.crop}</h2>
      <p className="sub">
        Live {fw.days}-day forecast for {data.location}:{" "}
        <strong>{fw.total_rain_mm} mm</strong> total rain, max{" "}
        <strong>{fw.max_daily_rain_mm} mm</strong>/day, avg high{" "}
        <strong>{fw.avg_t_max}°C</strong> ({fw.source})
      </p>

      {alerts.length === 0 ? (
        <p className="alert-clear">
          ✅ No weather conflicts — the forecast is clear for the upcoming plan
          actions.
        </p>
      ) : (
        <ul className="alert-list">
          {alerts.map((a, i) => {
            const sev = SEV[a.severity] || SEV.advice;
            return (
              <li key={i} className={`alert ${sev.cls}`}>
                <div className="alert-head">
                  <span className="alert-icon" title={a.kind}>
                    {KIND_ICON[a.kind] || "⚠️"}
                  </span>
                  <span className="alert-date">{fmtDay(a.date)}</span>
                  {a.stage && <span className="alert-stage">{a.stage}</span>}
                  <span className={`alert-sev ${sev.cls}`}>
                    {sev.icon} {sev.label}
                  </span>
                </div>
                <div className="alert-rec">{a.recommendation}</div>
                <div className="alert-trigger">Forecast: {a.trigger}</div>
                {a.because && <div className="alert-because">{a.because}</div>}
              </li>
            );
          })}
        </ul>
      )}

      {actions.length > 0 && (
        <details className="upcoming-actions">
          <summary>
            Plan actions inside the forecast window ({actions.length})
          </summary>
          <ul>
            {actions.map((a, i) => (
              <li key={i}>
                <strong>{fmtDay(a.date)}</strong> — {a.stage}: {a.action}
              </li>
            ))}
          </ul>
        </details>
      )}

      {data.kb_references?.length > 0 && (
        <p className="kb-refs">
          KB sources:{" "}
          {[...new Set(data.kb_references.map((r) => r.source))].join(", ")}
        </p>
      )}
      {data.source && <p className="assumptions">Grounding: {data.source}</p>}
    </div>
  );
}
