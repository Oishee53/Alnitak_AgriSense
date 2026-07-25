// Proactive weather-triggered advice (Tier 1). Renders the weather_advisory
// artifact: the live forecast window, upcoming plan actions, and dated alerts
// (delay urea before heavy rain, skip a rain-covered irrigation, …) each with
// the triggering forecast numbers and the `because` reasoning.

import { t } from "../lib/i18n.js";
import { localize, cropName, placeName, d } from "../lib/bn.js";

const SEV = {
  high: { icon: "🔴", cls: "sev-high", labelKey: "wa.actNow" },
  warning: { icon: "🟠", cls: "sev-warn", labelKey: "wa.watch" },
  advice: { icon: "🟢", cls: "sev-advice", labelKey: "wa.tip" },
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

import { MONTHS_SHORT } from "../lib/i18n.js";

function fmtDay(iso, lang) {
  if (!iso) return "";
  const [, m, day] = iso.split("-").map(Number);
  return `${(MONTHS_SHORT[lang] || MONTHS_SHORT.en)[m - 1]} ${d(day, lang)}`;
}

export default function WeatherAlerts({ data, lang = "en" }) {
  if (!data || data.error) return null;
  const fw = data.forecast_window || {};
  const alerts = data.alerts || [];
  const actions = data.plan_actions_in_window || [];

  return (
    <div className="card weather-alerts">
      <h2>{t(lang, "wa.title")} · {cropName(data.crop, lang)}</h2>
      <p className="sub">
        {lang === "bn" ? (
          <>
            {placeName(data.location, lang)}-এর {d(fw.days, lang)} দিনের লাইভ পূর্বাভাস:{" "}
            <strong>{d(fw.total_rain_mm, lang)} মিমি</strong> মোট বৃষ্টি, সর্বোচ্চ{" "}
            <strong>{d(fw.max_daily_rain_mm, lang)} মিমি</strong>/দিন, গড় সর্বোচ্চ{" "}
            <strong>{d(fw.avg_t_max, lang)}°C</strong> ({fw.source})
          </>
        ) : (
          <>
            Live {fw.days}-day forecast for {data.location}:{" "}
            <strong>{fw.total_rain_mm} mm</strong> total rain, max{" "}
            <strong>{fw.max_daily_rain_mm} mm</strong>/day, avg high{" "}
            <strong>{fw.avg_t_max}°C</strong> ({fw.source})
          </>
        )}
      </p>

      {alerts.length === 0 ? (
        <p className="alert-clear">{t(lang, "wa.clear")}</p>
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
                  <span className="alert-date">{fmtDay(a.date, lang)}</span>
                  {a.stage && <span className="alert-stage">{localize(a.stage, lang)}</span>}
                  <span className={`alert-sev ${sev.cls}`}>
                    {sev.icon} {t(lang, sev.labelKey)}
                  </span>
                </div>
                <div className="alert-rec">{localize(a.recommendation, lang)}</div>
                <div className="alert-trigger">
                  {t(lang, "wa.forecast")} {localize(a.trigger, lang)}
                </div>
                {a.because && <div className="alert-because">{localize(a.because, lang)}</div>}
              </li>
            );
          })}
        </ul>
      )}

      {actions.length > 0 && (
        <details className="upcoming-actions">
          <summary>
            {t(lang, "wa.planActions1")}{actions.length}{t(lang, "wa.planActions2")}
          </summary>
          <ul>
            {actions.map((a, i) => (
              <li key={i}>
                <strong>{fmtDay(a.date, lang)}</strong> — {localize(a.stage, lang)}:{" "}
                {localize(a.action, lang)}
              </li>
            ))}
          </ul>
        </details>
      )}

      {data.kb_references?.length > 0 && (
        <p className="kb-refs">
          {t(lang, "crops.kb")}{" "}
          {[...new Set(data.kb_references.map((r) => r.source))].join(", ")}
        </p>
      )}
      {data.source && (
        <p className="assumptions">
          {lang === "bn" ? "ভিত্তি: " : "Grounding: "}{data.source}
        </p>
      )}
    </div>
  );
}
