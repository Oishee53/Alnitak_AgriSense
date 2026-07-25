// Fertilizer & irrigation scheduler (Tier 1). Shows exactly how many kg of each
// input go on which date, what it costs, the organic alternative, and — most
// importantly — any urea top-dress the live forecast says to delay.
// Bangla mode: labels via the static dictionary, data strings via lib/bn.js.
import { t, MONTHS_SHORT } from "../lib/i18n.js";
import { localize, tk, cropName, d } from "../lib/bn.js";

function fmtDay(iso, lang) {
  if (!iso) return "";
  const [, m, day] = iso.split("-").map(Number);
  return `${(MONTHS_SHORT[lang] || MONTHS_SHORT.en)[m - 1]} ${d(day, lang)}`;
}

const bdt = (n, lang) => (n == null ? "—" : `${d(Math.round(n).toLocaleString(), lang)} BDT`);

export default function FertilizerView({ schedule, lang = "en" }) {
  if (!schedule || schedule.error) return null;
  const s = schedule;

  const noDoses = s.doses_available === false;

  return (
    <div className="card fert-view">
      <h2>{t(lang, "fert.title")} · {cropName(s.crop, lang)}</h2>
      <p className="sub">
        {d(s.farm_size_acres, lang)} {tk("acre", lang)} · {tk(s.soil_type, lang)}{" "}
        {lang === "bn" ? "মাটি" : "soil"} ·{" "}
        {lang === "bn" ? "বপন" : "anchored on sowing"}{" "}
        <strong>{fmtDay(s.sowing_anchor, lang)}</strong>
        {!noDoses && (
          <>
            {" · "}
            {lang === "bn" ? "মোট সারের খরচ" : "total fertilizer bill"}{" "}
            <strong>{bdt(s.total_fertilizer_cost_bdt, lang)}</strong>
          </>
        )}
      </p>

      {noDoses && (
        <p className="warning">⚠ {localize(s.quantities_note, lang)}</p>
      )}

      {s.adjustments_applied?.map((a, i) => (
        <p key={i} className="adjust-note">⚙ {localize(a, lang)}</p>
      ))}

      <h3>{t(lang, "fert.schedule")}</h3>
      <ul className="fert-stages">
        {s.fertilizer_schedule?.map((st, i) => (
          <li key={i} className={st.weather_alert ? "fert-stage alert" : "fert-stage"}>
            <div className="fert-head">
              <span className="fert-date">{fmtDay(st.date, lang)}</span>
              <span className="fert-das">{d(st.das >= 0 ? `+${st.das}` : st.das, lang)}d</span>
              <span className="fert-stage-name">{localize(st.stage, lang)}</span>
              <span className="fert-cost">{bdt(st.stage_cost_bdt, lang)}</span>
            </div>
            <div className="fert-inputs">
              {st.inputs?.map((it, j) => (
                <span key={j} className="fert-chip">
                  {it.input} <strong>{d(it.kg, lang)} kg</strong>
                </span>
              ))}
            </div>
            {st.because && <div className="cal-because">{localize(st.because, lang)}</div>}
            {st.weather_alert && (
              <div className="weather-alert">⛈ {localize(st.weather_alert, lang)}</div>
            )}
          </li>
        ))}
      </ul>

      {s.irrigation_schedule?.length > 0 && (
        <>
          <h3>{t(lang, "fert.irrigation")}</h3>
          <ul className="irrig-list">
            {s.irrigation_schedule.map((ir, i) => (
              <li key={i}>
                <span className="fert-date">{fmtDay(ir.date, lang)}</span>
                <div className="cal-body">
                  <div className="cal-stage-name">
                    {localize(ir.event, lang)}
                    {ir.condition !== "always" && (
                      <span className="cond-tag"> · {localize(ir.condition, lang)}</span>
                    )}
                  </div>
                  <div className="cal-action">{localize(ir.action, lang)}</div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {s.cost_breakdown?.length > 0 && (
        <>
      <h3>{t(lang, "fert.seasonTotal")}</h3>
      <table>
        <thead>
          <tr>
            <th>{t(lang, "fert.input")}</th>
            <th>{t(lang, "fert.kgPerAcre")}</th>
            <th>{t(lang, "fert.kgTotal")}</th>
            <th>{t(lang, "fert.bdtPerKg")}</th>
            <th>{t(lang, "fert.cost")}</th>
          </tr>
        </thead>
        <tbody>
          {s.cost_breakdown?.map((c, i) => (
            <tr key={i}>
              <td>{c.input}</td>
              <td>{d(c.kg_per_acre, lang)}</td>
              <td>{d(c.kg_total, lang)}</td>
              <td>{d(c.price_bdt_per_kg, lang)}</td>
              <td>{d(Math.round(c.cost_bdt).toLocaleString(), lang)}</td>
            </tr>
          ))}
        </tbody>
      </table>
        </>
      )}

      {s.organic_alternatives?.length > 0 && (
        <div className="organic-box">
          <h3>{t(lang, "fert.organic")}</h3>
          {s.organic_alternatives.map((o, i) => (
            <p key={i}>
              <strong>{o.input}</strong> — {d(o.qty_kg_total.toLocaleString(), lang)} kg
              {lang === "bn" ? " মোট (" : " total ("}
              {d(o.qty_kg_per_acre.toLocaleString(), lang)} kg/{tk("acre", lang)}
              {lang === "bn" ? "), বদলে দেয় " : "), replaces "}{o.replaces}.
              <br />
              <span className="cal-because">{localize(o.because, lang)}</span>
            </p>
          ))}
        </div>
      )}

      {s.weather_rules?.length > 0 && (
        <details className="rules">
          <summary>{t(lang, "fert.rules")}</summary>
          <ol>
            {s.weather_rules.map((r, i) => (
              <li key={i}>{localize(r, lang)}</li>
            ))}
          </ol>
        </details>
      )}

      <p className="assumptions">
        {lang === "bn" ? "মাত্রা: " : "Doses: "}{s.source}. {localize(s.price_note, lang)}
      </p>
    </div>
  );
}
