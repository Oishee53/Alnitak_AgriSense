import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import TracePanel from "./components/TracePanel.jsx";
import ProfileCard from "./components/ProfileCard.jsx";
import CropOptions from "./components/CropOptions.jsx";
import PlanView from "./components/PlanView.jsx";
import FinanceTable from "./components/FinanceTable.jsx";
import { sendChat, getSession, getTrace } from "./lib/api.js";

const LS_KEY = "agrisense_session_id";

// Demo layout: conversation + tabbed output (crops / calendar / finance) on the
// left, agent TRACE on the right. Tabs keep each deliverable one click away
// instead of buried in a long scroll.
export default function App() {
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(LS_KEY) || null
  );
  const [messages, setMessages] = useState([]);
  const [trace, setTrace] = useState([]);
  const [farm, setFarm] = useState(null);
  const [crops, setCrops] = useState(null);
  const [plan, setPlan] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState(null); // 'crops' | 'calendar' | 'finance'

  // Rehydrate a prior session on load (persistent memory across refreshes).
  useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const snap = await getSession(sessionId);
        setMessages(snap.history || []);
        setFarm(snap.farm);
        setCrops(snap.crop_options);
        setPlan(snap.season_plan);
        setFinancials(snap.financials);
        if (snap.season_plan) setTab("calendar");
        else if (snap.crop_options) setTab("crops");
        const t = await getTrace(sessionId);
        setTrace(t.trace || []);
      } catch {
        localStorage.removeItem(LS_KEY); // stale id — start fresh
        setSessionId(null);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyResponse(res) {
    setSessionId(res.session_id);
    localStorage.setItem(LS_KEY, res.session_id);
    setFarm(res.farm);
    if (res.crop_options) setCrops(res.crop_options);
    if (res.season_plan) setPlan(res.season_plan);
    if (res.financials) setFinancials(res.financials);
    if (res.trace?.length) setTrace((t) => [...t, ...res.trace]);
    // Auto-focus the newest artifact so the user never has to hunt for it.
    if (res.season_plan) setTab("calendar");
    else if (res.crop_options) setTab("crops");
  }

  async function handleSend(text) {
    if (busy) return; // one in-flight request per session — no double-fires
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await sendChat(sessionId, text);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      applyResponse(res);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `⚠️ ${e.message}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function newSession() {
    localStorage.removeItem(LS_KEY);
    setSessionId(null);
    setMessages([]);
    setTrace([]);
    setFarm(null);
    setCrops(null);
    setPlan(null);
    setFinancials(null);
    setTab(null);
  }

  // Which output panel to show: the selected tab if it still has data,
  // otherwise the most advanced artifact available.
  const has = { crops: !!crops, calendar: !!plan, finance: !!financials };
  const effectiveTab =
    tab && has[tab]
      ? tab
      : has.calendar
      ? "calendar"
      : has.crops
      ? "crops"
      : has.finance
      ? "finance"
      : null;

  return (
    <div className="app">
      <header className="topbar">
        <h1>🌾 AgriSense AI</h1>
        <span className="team">Team Alnitak · Bdapps Agentic AI Hackathon</span>
        <button className="new-session" onClick={newSession}>
          ↻ New session
        </button>
      </header>

      <main className="grid">
        <section className="left">
          <ChatPanel messages={messages} busy={busy} onSend={handleSend} />
          <ProfileCard farm={farm} />

          {effectiveTab && (
            <div className="tab-bar">
              {has.crops && (
                <button
                  className={effectiveTab === "crops" ? "active" : ""}
                  onClick={() => setTab("crops")}
                >
                  🌱 Crop options
                </button>
              )}
              {has.calendar && (
                <button
                  className={effectiveTab === "calendar" ? "active" : ""}
                  onClick={() => setTab("calendar")}
                >
                  📅 Season calendar
                </button>
              )}
              {has.finance && (
                <button
                  className={effectiveTab === "finance" ? "active" : ""}
                  onClick={() => setTab("finance")}
                >
                  💰 Finance
                </button>
              )}
            </div>
          )}

          {effectiveTab === "crops" && (
            <CropOptions
              data={crops}
              busy={busy}
              onPick={(crop) =>
                handleSend(
                  `Let's go with ${crop}. Build the season plan and financials.`
                )
              }
              onPriority={(p) => {
                const label = {
                  balanced: "a balanced view of fit and profit",
                  profit: "the most profitable crops",
                  safe: "the safest, lowest-risk crops",
                }[p];
                handleSend(`Re-rank the crop options to prioritise ${label}.`);
              }}
            />
          )}
          {effectiveTab === "calendar" && <PlanView plan={plan} />}
          {effectiveTab === "finance" && <FinanceTable financials={financials} />}
        </section>

        <aside className="right">
          <TracePanel trace={trace} />
        </aside>
      </main>
    </div>
  );
}
