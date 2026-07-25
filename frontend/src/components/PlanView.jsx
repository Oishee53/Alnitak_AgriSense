// Season calendar (Tier-0 #4). Two ways to read the same dated plan:
//   • Timeline — stages grouped by month as a vertical list (default).
//   • Calendar — a real month grid with each stage in its day box.
// Either can be popped into a full-screen modal for a focused view.
// UI labels + month names are translated in Bangla mode; stage DATA stays
// English (it is the trace-checkable grounding).
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import CalendarView from "./CalendarView.jsx";
import { t, MONTHS_FULL, MONTHS_SHORT } from "../lib/i18n.js";
import { localize, cropName, d as bd } from "../lib/bn.js";

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

function fmtDay(iso, lang) {
  const [, m, day] = iso.split("-").map(Number);
  return `${(MONTHS_SHORT[lang] || MONTHS_SHORT.en)[m - 1]} ${bd(day, lang)}`;
}

function monthKey(iso, lang) {
  const [y, m] = iso.split("-").map(Number);
  return {
    key: `${y}-${m}`,
    label: `${(MONTHS_FULL[lang] || MONTHS_FULL.en)[m - 1]} ${bd(y, lang)}`,
  };
}

function Timeline({ plan, lang }) {
  const groups = [];
  for (const st of plan.stages || []) {
    const { key, label } = monthKey(st.date, lang);
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
              const ty = classify(st.stage);
              return (
                <li key={i} className={`cal-stage ${ty.cls}`}>
                  <span className="cal-icon" title={ty.label}>{ty.icon}</span>
                  <span className="cal-date">{fmtDay(st.date, lang)}</span>
                  <div className="cal-body">
                    <div className="cal-stage-name">{localize(st.stage, lang)}</div>
                    <div className="cal-action">{localize(st.action, lang)}</div>
                    {st.because && (
                      <div className="cal-because">{localize(st.because, lang)}</div>
                    )}
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

  // Portal straight to <body> so the fixed-position backdrop is always
  // anchored to the real viewport, never trapped by an ancestor card's
  // stacking/containing-block context (animations, transforms, etc.).
  return createPortal(
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
    </div>,
    document.body
  );
}

export default function PlanView({ plan, lang = "en" }) {
  const [view, setView] = useState("timeline"); // 'timeline' | 'calendar'
  const [expanded, setExpanded] = useState(false);
  if (!plan || plan.error) return null;

  const subLine = (
    <p className="sub">
      {t(lang, "plan.window")} {localize(plan.sowing_window?.label, lang)} ·{" "}
      {t(lang, "plan.sow")}{" "}
      <strong>{fmtDay(plan.anchor_date, lang)}</strong> → {t(lang, "plan.harvest")}{" "}
      <strong>{fmtDay(plan.expected_harvest, lang)}</strong> · {bd(plan.duration_days, lang)}{" "}
      {t(lang, "plan.days")}
    </p>
  );

  return (
    <div className="card plan">
      <div className="plan-head">
        <h2>{t(lang, "plan.title")} · {cropName(plan.crop, lang)}</h2>
        <div className="plan-tools">
          <div className="view-toggle" role="tablist" aria-label="Plan view">
            <button
              role="tab"
              aria-selected={view === "timeline"}
              className={view === "timeline" ? "active" : ""}
              onClick={() => setView("timeline")}
            >
              {t(lang, "plan.timeline")}
            </button>
            <button
              role="tab"
              aria-selected={view === "calendar"}
              className={view === "calendar" ? "active" : ""}
              onClick={() => setView("calendar")}
            >
              {t(lang, "plan.calendar")}
            </button>
          </div>
          <button
            className="expand-btn"
            onClick={() => setExpanded(true)}
            title={t(lang, "plan.expand")}
          >
            {t(lang, "plan.expand")}
          </button>
        </div>
      </div>

      {subLine}

      {plan.warnings?.map((w, i) => (
        <p key={i} className="warning">⚠ {localize(w, lang)}</p>
      ))}

      {view === "timeline" ? (
        <Timeline plan={plan} lang={lang} />
      ) : (
        <CalendarView plan={plan} lang={lang} />
      )}

      {plan.source && (
        <p className="assumptions">
          {t(lang, "plan.source")} {plan.source}
        </p>
      )}

      {expanded && (
        <Modal
          title={`${t(lang, "plan.title")} · ${cropName(plan.crop, lang)}`}
          onClose={() => setExpanded(false)}
        >
          {subLine}
          <CalendarView plan={plan} large lang={lang} />
        </Modal>
      )}
    </div>
  );
}
