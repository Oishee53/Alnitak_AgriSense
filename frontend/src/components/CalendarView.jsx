// Real month-grid calendar for the season plan. Renders each month that holds a
// plan stage as a 7-column calendar; stages sit in their actual day boxes. The
// sowing window is tinted, and HOVERING (or focusing) a day pops up its full
// stage detail as a floating tooltip anchored to that day — instead of a panel
// at the bottom of the list. Month/weekday names + legend labels follow the
// language toggle; stage DATA (names, actions, because) stays English — the
// trace-checkable grounding.
import { useState } from "react";
import { createPortal } from "react-dom";
import { t, MONTHS_FULL, WEEKDAYS } from "../lib/i18n.js";
import { localize, d as bd } from "../lib/bn.js";

const STAGE_TYPES = [
  { test: /harvest|retting/i, icon: "🌾", cls: "harvest", label: "Harvest", bn: "ফসল কাটা" },
  { test: /pest|disease|checkpoint/i, icon: "🐛", cls: "pest", label: "Pest / disease", bn: "পোকা / রোগ" },
  { test: /fertiliz|urea|gypsum|top-dress|basal/i, icon: "🧪", cls: "fert", label: "Fertilizer", bn: "সার" },
  { test: /irrigat|drain|\bwater/i, icon: "💧", cls: "irrig", label: "Irrigation", bn: "সেচ" },
  { test: /weed|thin|mulch/i, icon: "🌿", cls: "weed", label: "Weeding", bn: "নিড়ানি" },
  { test: /sow|transplant|planting|\bplant\b|nursery/i, icon: "🌱", cls: "sow", label: "Sowing", bn: "বপন" },
  { test: /prep/i, icon: "🚜", cls: "prep", label: "Land prep", bn: "জমি তৈরি" },
];
const OTHER = { icon: "🛠️", cls: "other", label: "Task", bn: "কাজ" };
const classify = (stage) => STAGE_TYPES.find((t) => t.test.test(stage)) || OTHER;
const typeLabel = (ty, lang) => (lang === "bn" ? ty.bn : ty.label);

const iso = (y, m, d) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return { y, m, d }; };

function MonthGrid({ y, m, byDay, winStart, winEnd, anchor, onHover, onLeave, lang }) {
  const months = MONTHS_FULL[lang] || MONTHS_FULL.en;
  const weekdays = WEEKDAYS[lang] || WEEKDAYS.en;
  const firstWd = new Date(y, m - 1, 1).getDay();
  const days = new Date(y, m, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstWd; i++) cells.push(null);
  for (let d = 1; d <= days; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <div className="cal-grid-card">
      <div className="cal-grid-title">{months[m - 1]} {bd(y, lang)}</div>
      <div className="cal-grid">
        {weekdays.map((w) => (
          <div key={w} className="cal-wd">{w}</div>
        ))}
        {cells.map((d, i) => {
          if (d == null) return <div key={i} className="cal-cell empty" aria-hidden="true" />;
          const dk = iso(y, m, d);
          const events = byDay.get(dk) || [];
          const inWindow = winStart && winEnd && dk >= winStart && dk <= winEnd;
          const isAnchor = dk === anchor;
          const isToday = dk === todayIso;
          const cls = [
            "cal-cell",
            events.length ? "has-event" : "",
            inWindow ? "in-window" : "",
            isAnchor ? "anchor" : "",
            isToday ? "today" : "",
          ].join(" ").trim();
          const cell = (
            <div className="cal-cell-date">{bd(d, lang)}</div>
          );
          if (!events.length) {
            return <div key={i} className={cls}>{cell}</div>;
          }
          const show = (e) => onHover(dk, events, e.currentTarget.getBoundingClientRect());
          return (
            <button
              key={i}
              className={cls}
              onMouseEnter={show}
              onMouseLeave={onLeave}
              onFocus={show}
              onBlur={onLeave}
              aria-label={`${months[m - 1]} ${d}: ${events.map((e) => e.stage).join(", ")}`}
            >
              {cell}
              <div className="cal-cell-events">
                {events.map((e, j) => {
                  const ty = classify(e.stage);
                  return (
                    <span key={j} className={`cal-ev ${ty.cls}`} title={localize(e.stage, lang)}>
                      <span className="cal-ev-icon">{ty.icon}</span>
                      <span className="cal-ev-name">{localize(e.stage, lang)}</span>
                    </span>
                  );
                })}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Floating tooltip anchored to a hovered/focused day cell. Portaled to <body>
// with position:fixed so the day cells' `overflow:hidden` can't clip it, and a
// z-index above the modal backdrop so it works in the expanded view too. It
// flips above/below the cell depending on room, and stays clear of the pointer
// (pointer-events:none) so it never flickers.
function DayPopover({ detail, lang }) {
  const { rect, date, events } = detail;
  const { y, m, d } = parse(date);
  const months = MONTHS_FULL[lang] || MONTHS_FULL.en;
  const above = rect.top > 260; // enough room overhead → show above the cell
  const HALF = 165; // half of max-width, for viewport clamping
  const style = {
    position: "fixed",
    left: Math.min(Math.max(rect.left + rect.width / 2, HALF + 8), window.innerWidth - HALF - 8),
    top: above ? rect.top - 10 : rect.bottom + 10,
    transform: above ? "translate(-50%, -100%)" : "translate(-50%, 0)",
  };
  return createPortal(
    <div className={`day-pop ${above ? "above" : "below"}`} style={style} role="tooltip">
      <div className="day-detail-date">
        {months[m - 1]} {bd(d, lang)}, {bd(y, lang)}
      </div>
      {events.map((e, i) => {
        const ty = classify(e.stage);
        return (
          <div key={i} className={`day-detail-item ${ty.cls}`}>
            <div className="day-detail-stage">
              <span>{ty.icon}</span> {localize(e.stage, lang)}
            </div>
            <div className="day-detail-action">{localize(e.action, lang)}</div>
            {e.because && (
              <div className="cal-because">{localize(e.because, lang)}</div>
            )}
          </div>
        );
      })}
    </div>,
    document.body
  );
}

export default function CalendarView({ plan, large = false, lang = "en" }) {
  const [hover, setHover] = useState(null); // { date, events, rect }
  if (!plan || plan.error) return null;

  const byDay = new Map();
  const monthsMap = new Map();
  for (const st of plan.stages || []) {
    const { y, m } = parse(st.date);
    monthsMap.set(`${y}-${m}`, { y, m });
    if (!byDay.has(st.date)) byDay.set(st.date, []);
    byDay.get(st.date).push(st);
  }
  const monthList = [...monthsMap.values()].sort((a, b) => a.y - b.y || a.m - b.m);

  const winStart = plan.sowing_window?.start;
  const winEnd = plan.sowing_window?.end;

  // Legend: only the stage types actually present.
  const present = new Map();
  for (const st of plan.stages || []) {
    const ty = classify(st.stage);
    present.set(ty.cls, ty);
  }

  const onHover = (date, events, rect) => setHover({ date, events, rect });
  const onLeave = () => setHover(null);

  return (
    <div className={`calv ${large ? "calv-large" : ""}`}>
      <div className="calv-grids">
        {monthList.map(({ y, m }) => (
          <MonthGrid
            key={`${y}-${m}`}
            y={y}
            m={m}
            byDay={byDay}
            winStart={winStart}
            winEnd={winEnd}
            anchor={plan.anchor_date}
            onHover={onHover}
            onLeave={onLeave}
            lang={lang}
          />
        ))}
      </div>

      <div className="calv-side">
        <div className="calv-legend">
          {[...present.values()].map((ty) => (
            <span key={ty.cls} className={`legend-item ${ty.cls}`}>
              <span className="legend-dot" /> {typeLabel(ty, lang)}
            </span>
          ))}
          <span className="legend-item in-window">
            <span className="legend-dot" /> {t(lang, "plan.legendWindow")}
          </span>
        </div>
        <p className="calv-hint">{t(lang, "plan.hoverHint")}</p>
      </div>

      {hover && <DayPopover detail={hover} lang={lang} />}
    </div>
  );
}
