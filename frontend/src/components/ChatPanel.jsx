import { useEffect, useRef, useState } from "react";
import { t } from "../lib/i18n.js";

// The conversation with the farmer. Intake follow-ups appear here as assistant
// messages; the agent asks only for the fields it is missing. Two accessibility
// affordances for low-literacy farmers (Tier 2): a 📷 camera button for AI
// disease diagnosis from a photo, and a 🎤 mic button for voice input (Web
// Speech API), which listens in Bengali or English per the language toggle.

// Web Speech API — available in Chrome/Edge under a prefix.
const SpeechRecognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function ChatPanel({ messages, busy, onSend, onImage, lang = "en" }) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const fileRef = useRef(null);
  const recogRef = useRef(null);

  function submit(e) {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  }

  function pickImage(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file || busy) return;
    const reader = new FileReader();
    reader.onload = () => onImage?.(reader.result); // data: URL
    reader.readAsDataURL(file);
  }

  // Stop any active recognition when the component unmounts.
  useEffect(() => () => recogRef.current?.abort?.(), []);

  function toggleMic() {
    if (!SpeechRecognition || busy) return;
    if (listening) {
      recogRef.current?.stop();
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = lang === "bn" ? "bn-BD" : "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    let finalText = "";
    rec.onresult = (ev) => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const chunk = ev.results[i][0].transcript;
        if (ev.results[i].isFinal) finalText += chunk;
        else interim += chunk;
      }
      setText((finalText + interim).trim());
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recogRef.current = rec;
    setListening(true);
    rec.start();
  }

  return (
    <div className="card chat">
      <h2>{t(lang, "chat.title")}</h2>
      <div className="messages">
        {messages.length === 0 && (
          <p className="hint">{t(lang, "chat.hint")}</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy && (
          <div className="msg assistant thinking">{t(lang, "chat.thinking")}</div>
        )}
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={pickImage}
          style={{ display: "none" }}
        />
        <button
          type="button"
          className="icon-btn"
          disabled={busy}
          title={t(lang, "chat.photoTitle")}
          onClick={() => fileRef.current?.click()}
        >
          📷
        </button>
        {SpeechRecognition && (
          <button
            type="button"
            className={`icon-btn mic ${listening ? "listening" : ""}`}
            disabled={busy}
            title={listening ? t(lang, "chat.micStop") : t(lang, "chat.micTitle")}
            onClick={toggleMic}
          >
            🎤
          </button>
        )}
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            listening ? t(lang, "chat.listening") : t(lang, "chat.placeholder")
          }
        />
        <button disabled={busy}>{t(lang, "chat.send")}</button>
      </form>
    </div>
  );
}
