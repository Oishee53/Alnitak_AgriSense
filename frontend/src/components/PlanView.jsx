// Season calendar (Tier-0 #4). Two ways to read the same dated plan:
//   • Timeline — stages grouped by month as a vertical list (default).
//   • Calendar — a real month grid with each stage in its day box.
// Either can be popped into a full-screen modal for a focused view.
import { useEffect, useState } from "react";
import CalendarView from "./CalendarView.jsx";

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

function Timeline({ plan }) {
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
  );
}

// Lightweight accessible modal — backdrop blur, Esc / click-away to close.
function Modal({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export default function PlanView({ plan }) {
  const [view, setView] = useState("timeline"); // 'timeline' | 'calendar'
  const [expanded, setExpanded] = useState(false);
  if (!plan || plan.error) return null;

  return (
    <div className="card plan">
      <div className="plan-head">
        <h2>Season calendar · {plan.crop}</h2>
        <div className="plan-tools">
          <div className="view-toggle" role="tablist" aria-label="Plan view">
            <button
              role="tab"
              aria-selected={view === "timeline"}
              className={view === "timeline" ? "active" : ""}
              onClick={() => setView("timeline")}
            >
              📋 Timeline
            </button>
            <button
              role="tab"
              aria-selected={view === "calendar"}
              className={view === "calendar" ? "active" : ""}
              onClick={() => setView("calendar")}
            >
              🗓️ Calendar
            </button>
          </div>
          <button className="expand-btn" onClick={() => setExpanded(true)} title="Open full calendar">
            ⤢ Expand
          </button>
        </div>
      </div>

      <p className="sub">
        Sowing window {plan.sowing_window?.label} · sow{" "}
        <strong>{fmtDay(plan.anchor_date)}</strong> → harvest{" "}
        <strong>{fmtDay(plan.expected_harvest)}</strong> · {plan.duration_days} days
      </p>

      {plan.warnings?.map((w, i) => (
        <p key={i} className="warning">⚠ {w}</p>
      ))}

      {view === "timeline" ? <Timeline plan={plan} /> : <CalendarView plan={plan} />}

      {plan.source && <p className="assumptions">Calendar source: {plan.source}</p>}

      {expanded && (
        <Modal title={`Season calendar · ${plan.crop}`} onClose={() => setExpanded(false)}>
          <p className="sub">
            Sowing window {plan.sowing_window?.label} · sow{" "}
            <strong>{fmtDay(plan.anchor_date)}</strong> → harvest{" "}
            <strong>{fmtDay(plan.expected_harvest)}</strong> · {plan.duration_days} days
          </p>
          <CalendarView plan={plan} large />
        </Modal>
      )}
    </div>
  );
}
