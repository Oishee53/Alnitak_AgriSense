import { useState } from "react";

// The conversation with the farmer. Intake follow-ups appear here as assistant
// messages; the agent asks only for the fields it is missing.
export default function ChatPanel({ messages, busy, onSend }) {
  const [text, setText] = useState("");

  function submit(e) {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  }

  return (
    <div className="card chat">
      <h2>Conversation</h2>
      <div className="messages">
        {messages.length === 0 && (
          <p className="hint">
            Try: “I have some land near Rangpur and want to plant something this
            season.”
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy && <div className="msg assistant thinking">thinking…</div>}
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Message AgriSense…"
        />
        <button disabled={busy}>Send</button>
      </form>
    </div>
  );
}
