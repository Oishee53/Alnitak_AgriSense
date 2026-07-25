// Session history sidebar (Tier 1 — persistent memory). Lists prior sessions
// from the backend store; selecting one rehydrates its profile, chat, plan and
// trace. Collapsible so it stays out of the way during a demo.

function fmtWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

import { t } from "../lib/i18n.js";

export default function SessionList({ sessions, currentId, busy, onSelect, onNew, lang = "en" }) {
  return (
    <div className="card sessions">
      <div className="sessions-head">
        <h2>{t(lang, "sess.title")}</h2>
        <button className="sessions-new" disabled={busy} onClick={onNew}>
          {t(lang, "sess.new")}
        </button>
      </div>
      {(!sessions || sessions.length === 0) && (
        <p className="hint">{t(lang, "sess.hint")}</p>
      )}
      <ul className="session-list">
        {sessions?.map((s) => (
          <li key={s.id}>
            <button
              className={`session-item ${s.id === currentId ? "active" : ""}`}
              disabled={busy}
              onClick={() => s.id !== currentId && onSelect(s.id)}
              title={s.preview}
            >
              <span className="session-label">{s.label}</span>
              <span className="session-meta">
                {fmtWhen(s.created_at)} · {s.message_count} {t(lang, "sess.msg")}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
