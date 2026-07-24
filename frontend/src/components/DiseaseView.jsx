// Plant disease detection from a photo (Tier 2). Shows the farmer's uploaded
// image, the AI diagnosis with a confidence badge, visible symptoms, and the
// treatment — KB-grounded (IPM-first, costed) where the condition matches our
// reference, model-suggested otherwise. Always carries the "confirm with an
// extension officer" disclaimer.

const money = (v) => (v == null ? "—" : Number(v).toLocaleString());

function confClass(c) {
  return `conf-${(c || "low").toLowerCase()}`;
}

export default function DiseaseView({ disease, image }) {
  if (!disease) return null;
  const d = disease;

  if (d.is_plant === false) {
    return (
      <div className="card disease-view">
        <h2>🔬 Photo diagnosis</h2>
        <p className="warning">⚠ {d.message}</p>
      </div>
    );
  }
  if (d.error) {
    return (
      <div className="card disease-view">
        <h2>🔬 Photo diagnosis</h2>
        <p className="pay-error">⚠️ {d.error}</p>
      </div>
    );
  }

  const healthy = d.condition === "healthy";

  return (
    <div className="card disease-view">
      <h2>🔬 Photo diagnosis{d.crop ? ` · ${d.crop}` : ""}</h2>

      <div className="disease-top">
        {image && <img className="disease-img" src={image} alt="uploaded crop" />}
        <div className="disease-head">
          <div className={`disease-dx ${healthy ? "healthy" : ""}`}>
            {d.diagnosis}
          </div>
          <div className="disease-badges">
            <span className={`badge ${confClass(d.confidence)}`}>
              {d.confidence} confidence
            </span>
            {d.severity && <span className="badge sev">{d.severity}</span>}
            <span className={`badge ${d.kb_grounded ? "kb-yes" : "kb-no"}`}>
              {d.kb_grounded ? "KB-grounded" : "AI estimate"}
            </span>
          </div>
          {d.because && <p className="cal-because">{d.because}</p>}
        </div>
      </div>

      {d.visible_symptoms?.length > 0 && (
        <div className="pest-block">
          <strong>Visible symptoms</strong>
          <ul>
            {d.visible_symptoms.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {!healthy && d.treatment && (
        <div className={`market-rec ${d.kb_grounded ? "rec-store" : "rec-mixed"}`}>
          <div className="market-rec-call">Treatment</div>
          <div className="market-rec-because">{d.treatment}</div>
        </div>
      )}

      {d.prevention?.length > 0 && (
        <div className="pest-block">
          <strong>Prevention (IPM-first)</strong>
          <ul>
            {d.prevention.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      <dl className="metrics">
        {d.threshold && (
          <div>
            <dt>Action threshold</dt>
            <dd>{d.threshold}</dd>
          </div>
        )}
        {Array.isArray(d.cost_bdt_per_acre) && (
          <div>
            <dt>Est. cost/acre</dt>
            <dd>
              {d.cost_bdt_per_acre[0] === 0 && d.cost_bdt_per_acre[1] === 0
                ? "management only"
                : `${money(d.cost_bdt_per_acre[0])}–${money(d.cost_bdt_per_acre[1])} BDT`}
            </dd>
          </div>
        )}
      </dl>

      {d.kb_source && <p className="assumptions">KB source: {d.kb_source}</p>}
      <p className="assumptions">{d.disclaimer}</p>
    </div>
  );
}
