// Plant disease detection from a photo (Tier 2). Shows the farmer's uploaded
// image, the AI diagnosis with a confidence badge, visible symptoms, and the
// treatment — KB-grounded (IPM-first, costed) where the condition matches our
// reference, model-suggested otherwise. Always carries the "confirm with an
// extension officer" disclaimer.

import { t } from "../lib/i18n.js";
import { localize, cropName, tk, unit } from "../lib/bn.js";

const money = (v) => (v == null ? "—" : Number(v).toLocaleString());

function confClass(c) {
  return `conf-${(c || "low").toLowerCase()}`;
}

export default function DiseaseView({ disease, image, lang = "en" }) {
  if (!disease) return null;
  const d = disease;

  if (d.is_plant === false) {
    return (
      <div className="card disease-view">
        <h2>{t(lang, "dz.title")}</h2>
        <p className="warning">⚠ {localize(d.message, lang)}</p>
      </div>
    );
  }
  if (d.error) {
    return (
      <div className="card disease-view">
        <h2>{t(lang, "dz.title")}</h2>
        <p className="pay-error">⚠️ {localize(d.error, lang)}</p>
      </div>
    );
  }

  const healthy = d.condition === "healthy";

  return (
    <div className="card disease-view">
      <h2>{t(lang, "dz.title")}{d.crop ? ` · ${cropName(d.crop, lang)}` : ""}</h2>

      <div className="disease-top">
        {image && <img className="disease-img" src={image} alt="uploaded crop" />}
        <div className="disease-head">
          <div className={`disease-dx ${healthy ? "healthy" : ""}`}>
            {localize(disease.diagnosis, lang)}
          </div>
          <div className="disease-badges">
            <span className={`badge ${confClass(disease.confidence)}`}>
              {tk(disease.confidence, lang)} {t(lang, "dz.confidence")}
            </span>
            {disease.severity && (
              <span className="badge sev">{tk(disease.severity, lang)}</span>
            )}
            <span className={`badge ${d.kb_grounded ? "kb-yes" : "kb-no"}`}>
              {d.kb_grounded ? t(lang, "dz.kb") : t(lang, "dz.ai")}
            </span>
          </div>
          {d.because && <p className="cal-because">{localize(d.because, lang)}</p>}
        </div>
      </div>

      {d.visible_symptoms?.length > 0 && (
        <div className="pest-block">
          <strong>{t(lang, "dz.symptoms")}</strong>
          <ul>
            {d.visible_symptoms.map((s, i) => (
              <li key={i}>{localize(s, lang)}</li>
            ))}
          </ul>
        </div>
      )}

      {!healthy && d.treatment && (
        <div className={`market-rec ${d.kb_grounded ? "rec-store" : "rec-mixed"}`}>
          <div className="market-rec-call">{t(lang, "dz.treatment")}</div>
          <div className="market-rec-because">{localize(d.treatment, lang)}</div>
        </div>
      )}

      {d.prevention?.length > 0 && (
        <div className="pest-block">
          <strong>{t(lang, "dz.prevention")}</strong>
          <ul>
            {d.prevention.map((p, i) => (
              <li key={i}>{localize(p, lang)}</li>
            ))}
          </ul>
        </div>
      )}

      <dl className="metrics">
        {d.threshold && (
          <div>
            <dt>{t(lang, "dz.threshold")}</dt>
            <dd>{localize(d.threshold, lang)}</dd>
          </div>
        )}
        {Array.isArray(d.cost_bdt_per_acre) && (
          <div>
            <dt>{t(lang, "dz.costAcre")}</dt>
            <dd>
              {d.cost_bdt_per_acre[0] === 0 && d.cost_bdt_per_acre[1] === 0
                ? lang === "bn"
                  ? "শুধু ব্যবস্থাপনা"
                  : "management only"
                : `${money(d.cost_bdt_per_acre[0])}–${money(d.cost_bdt_per_acre[1])} ${unit("BDT", lang)}`}
            </dd>
          </div>
        )}
      </dl>

      {d.kb_source && (
        <p className="assumptions">{t(lang, "dz.kbSource")} {d.kb_source}</p>
      )}
      <p className="assumptions">{localize(d.disclaimer, lang)}</p>
    </div>
  );
}
