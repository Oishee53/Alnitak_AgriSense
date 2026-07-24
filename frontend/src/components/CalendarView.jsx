// Real month-grid calendar for the season plan. Renders each month that holds a
// plan stage as a 7-column calendar; stages sit in their actual day boxes. The
// sowing window is tinted, and clicking a day reveals its full stage detail.
import { useState } from "react";

const STAGE_TYPES = [
  { test: /harvest|retting/i, icon: "🌾", cls: "harvest", label: "Harvest" },
  { test: /pest|disease|checkpoint/i, icon: "🐛", cls: "pest", label: "Pest / disease" },
  { test: /fertiliz|urea|gypsum|top-dress|basal/i, icon: "🧪", cls: "fert", label: "Fertilizer" },
  { test: /irrigat|drain|\bwater/i, icon: "💧", cls: "irrig", label: "Irrigation" },
  { test: /weed|thin|mulch/i, icon: "🌿", cls: "weed", label: "Weeding" },
  { test: /sow|transplant|planting|\bplant\b|nursery/i, icon: "🌱", cls: "sow", label: "Sowing" },
  { test: /prep/i, icon: "🚜", cls: "prep", label: "Land prep" },
];
const OTHER = { icon: "🛠️", cls: "other", label: "Task" };
const classify = (stage) => STAGE_TYPES.find((t) => t.test.test(stage)) || OTHER;

const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const iso = (y, m, d) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return { y, m, d }; };

function MonthGrid({ y, m, byDay, winStart, winEnd, anchor, onPick, selected }) {
  const firstWd = new Date(y, m - 1, 1).getDay();
  const days = new Date(y, m, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstWd; i++) cells.push(null);
  for (let d = 1; d <= days; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <div className="cal-grid-card">
      <div className="cal-grid-title">{MONTHS[m - 1]} {y}</div>
      <div className="cal-grid">
        {WD.map((w) => (
          <div key={w} className="cal-wd">{w}</div>
        ))}
        {cells.map((d, i) => {
          if (d == null) return <div key={i} className="cal-cell empty" aria-hidden="true" />;
          const dk = iso(y, m, d);
          const events = byDay.get(dk) || [];
          const inWindow = winStart && winEnd && dk >= winStart && dk <= winEnd;
          const isAnchor = dk === anchor;
          const isToday = dk === todayIso;
          const isSel = dk === selected;
          const cls = [
            "cal-cell",
            events.length ? "has-event" : "",
            inWindow ? "in-window" : "",
            isAnchor ? "anchor" : "",
            isToday ? "today" : "",
            isSel ? "selected" : "",
          ].join(" ").trim();
          const cell = (
            <div className="cal-cell-date">{d}</div>
          );
          if (!events.length) {
            return <div key={i} className={cls}>{cell}</div>;
          }
          return (
            <button
              key={i}
              className={cls}
              onClick={() => onPick(dk, events)}
              aria-label={`${MONTHS[m - 1]} ${d}: ${events.map((e) => e.stage).join(", ")}`}
            >
              {cell}
              <div className="cal-cell-events">
                {events.map((e, j) => {
                  const t = classify(e.stage);
                  return (
                    <span key={j} className={`cal-ev ${t.cls}`} title={e.stage}>
                      <span className="cal-ev-icon">{t.icon}</span>
                      <span className="cal-ev-name">{e.stage}</span>
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

export default function CalendarView({ plan, large = false }) {
  const [sel, setSel] = useState(null); // { date, events }
  if (!plan || plan.error) return null;

  const byDay = new Map();
  const monthsMap = new Map();
  for (const st of plan.stages || []) {
    const { y, m } = parse(st.date);
    monthsMap.set(`${y}-${m}`, { y, m });
    if (!byDay.has(st.date)) byDay.set(st.date, []);
    byDay.get(st.date).push(st);
  }
  const months = [...monthsMap.values()].sort((a, b) => a.y - b.y || a.m - b.m);

  const winStart = plan.sowing_window?.start;
  const winEnd = plan.sowing_window?.end;

  // Legend: only the stage types actually present.
  const present = new Map();
  for (const st of plan.stages || []) {
    const t = classify(st.stage);
    present.set(t.cls, t);
  }

  const pick = (date, events) => setSel({ date, events });
  const detail = sel || {
    date: plan.anchor_date,
    events: byDay.get(plan.anchor_date) || [],
  };
  const detailDate = detail.date ? parse(detail.date) : null;

  return (
    <div className={`calv ${large ? "calv-large" : ""}`}>
      <div className="calv-grids">
        {months.map(({ y, m }) => (
          <MonthGrid
            key={`${y}-${m}`}
            y={y}
            m={m}
            byDay={byDay}
            winStart={winStart}
            winEnd={winEnd}
            anchor={plan.anchor_date}
            onPick={pick}
            selected={sel?.date}
          />
        ))}
      </div>

      <div className="calv-side">
        <div className="calv-legend">
          {[...present.values()].map((t) => (
            <span key={t.cls} className={`legend-item ${t.cls}`}>
              <span className="legend-dot" /> {t.label}
            </span>
          ))}
          <span className="legend-item in-window">
            <span className="legend-dot" /> Sowing window
          </span>
        </div>

        {detail.events.length > 0 && detailDate && (
          <div className="day-detail">
            <div className="day-detail-date">
              {MONTHS[detailDate.m - 1]} {detailDate.d}, {detailDate.y}
            </div>
            {detail.events.map((e, i) => {
              const t = classify(e.stage);
              return (
                <div key={i} className={`day-detail-item ${t.cls}`}>
                  <div className="day-detail-stage">
                    <span>{t.icon}</span> {e.stage}
                  </div>
                  <div className="day-detail-action">{e.action}</div>
                  {e.because && <div className="cal-because">{e.because}</div>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
