// Visual season calendar (Tier-0 #4). Renders the dated plan grouped by month
// as a timeline, with a type icon per stage and the `because` reasoning that
// grounds each date.

const STAGE_TYPES = [
  { test: /harvest|retting/i, icon: "🌾", cls: "harvest", label: "Harvest" },
  { test: /pest|disease|checkpoint/i, icon: "🐛", cls: "pest", label: "Pest/disease" },
  { test: /fertiliz|urea|gypsum|top-dress|basal/i, icon: "🧪", cls: "fert", label: "Fertilizer" },
  { test: /irrigat|drain|\bwater/i, icon: "💧", cls: "irrig", label: "Irrigation" },
  { test: /weed|thin|mulch/i, icon: "🌿", cls: "weed", label: "Weeding" },
  { test: /sow|transplant|planting|\bplant\b|nursery/i, icon: "🌱", cls: "sow", label: "Sowing" },
  { test: /prep/i, icon: "🚜", cls: "prep", label: "Land prep" },
];

function classify(stage) {
  return (
    STAGE_TYPES.find((t) => t.test.test(stage)) || {
      icon: "🛠️",
      cls: "other",
      label: "Task",
    }
  );
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function fmtDay(iso) {
  const [, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1].slice(0, 3)} ${d}`;
}

function monthKey(iso) {
  const [y, m] = iso.split("-").map(Number);
  return { key: `${y}-${m}`, label: `${MONTHS[m - 1]} ${y}` };
}

export default function PlanView({ plan }) {
  if (!plan || plan.error) return null;

  // Group stages into consecutive month buckets (preserving order).
  const groups = [];
  for (const st of plan.stages || []) {
    const { key, label } = monthKey(st.date);
    let g = groups.find((x) => x.key === key);
    if (!g) {
      g = { key, label, stages: [] };
      groups.push(g);
    }
    g.stages.push(st);
  }

  return (
    <div className="card plan">
      <h2>📅 Season calendar · {plan.crop}</h2>
      <p className="sub">
        Sowing window {plan.sowing_window?.label} · sow{" "}
        <strong>{fmtDay(plan.anchor_date)}</strong> → harvest{" "}
        <strong>{fmtDay(plan.expected_harvest)}</strong> · {plan.duration_days} days
      </p>

      {plan.warnings?.map((w, i) => (
        <p key={i} className="warning">⚠ {w}</p>
      ))}

      <div className="cal">
        {groups.map((g) => (
          <div key={g.key} className="cal-month">
            <div className="cal-month-label">{g.label}</div>
            <ul className="cal-stages">
              {g.stages.map((st, i) => {
                const t = classify(st.stage);
                return (
                  <li key={i} className={`cal-stage ${t.cls}`}>
                    <span className="cal-icon" title={t.label}>{t.icon}</span>
                    <span className="cal-date">{fmtDay(st.date)}</span>
                    <div className="cal-body">
                      <div className="cal-stage-name">{st.stage}</div>
                      <div className="cal-action">{st.action}</div>
                      {st.because && <div className="cal-because">{st.because}</div>}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {plan.source && <p className="assumptions">Calendar source: {plan.source}</p>}
    </div>
  );
}
