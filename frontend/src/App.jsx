import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import TracePanel from "./components/TracePanel.jsx";
import ProfileCard from "./components/ProfileCard.jsx";
import CropOptions from "./components/CropOptions.jsx";
import PlanView from "./components/PlanView.jsx";
import FinanceTable from "./components/FinanceTable.jsx";
import FertilizerView from "./components/FertilizerView.jsx";
import PestRiskView from "./components/PestRiskView.jsx";
import ScenarioView from "./components/ScenarioView.jsx";
import WeatherAlerts from "./components/WeatherAlerts.jsx";
import MarketView from "./components/MarketView.jsx";
import SupplierView from "./components/SupplierView.jsx";
import DiseaseView from "./components/DiseaseView.jsx";
import PaymentPanel from "./components/PaymentPanel.jsx";
import SessionList from "./components/SessionList.jsx";
import { sendChat, getSession, getTrace, listSessions, diagnose } from "./lib/api.js";
import { t } from "./lib/i18n.js";

const LS_KEY = "agrisense_session_id";

// Demo layout: conversation + tabbed output on the left, agent TRACE on the
// right, and an optional session-history sidebar. Tabs keep each deliverable
// one click away instead of buried in a long scroll.
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
  const [fertilizer, setFertilizer] = useState(null);
  const [pestRisk, setPestRisk] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [alerts, setAlerts] = useState(null); // weather_advisory artifact (Tier 1)
  const [market, setMarket] = useState(null); // Tier 2
  const [suppliers, setSuppliers] = useState(null); // Tier 2
  const [disease, setDisease] = useState(null); // Tier 2 (photo diagnosis)
  const [diseaseImg, setDiseaseImg] = useState(null); // uploaded photo (ephemeral)
  const [busy, setBusy] = useState(false);
  // 'crops' | 'calendar' | 'finance' | 'fertilizer' | 'pests' | 'scenario' | 'weather'
  const [tab, setTab] = useState(null);
  const [sessions, setSessions] = useState([]); // session history (sidebar)
  const [showSessions, setShowSessions] = useState(false);
  // Reply language: 'en' or 'bn' (Bengali). Persisted so it survives reloads.
  const [lang, setLang] = useState(() => localStorage.getItem("agrisense_lang") || "en");

  async function refreshSessions() {
    try {
      const res = await listSessions();
      setSessions(res.sessions || []);
    } catch {
      /* sidebar is best-effort */
    }
  }

  // Rehydrate a session: profile, chat history, artifacts AND persisted trace.
  async function loadSession(id) {
    try {
      const snap = await getSession(id);
      setSessionId(id);
      localStorage.setItem(LS_KEY, id);
      setMessages(snap.history || []);
      setFarm(snap.farm);
      setCrops(snap.crop_options);
      setPlan(snap.season_plan);
      setFinancials(snap.financials);
      setFertilizer(snap.fertilizer_schedule);
      setPestRisk(snap.pest_risk);
      setScenario(snap.scenario);
      setAlerts(snap.weather_alerts);
      setMarket(snap.market);
      setSuppliers(snap.suppliers);
      setDisease(snap.disease);
      setDiseaseImg(null); // uploaded photo is ephemeral; diagnosis persists
      if (snap.season_plan) setTab("calendar");
      else if (snap.crop_options) setTab("crops");
      else setTab(null);
      const t = await getTrace(id);
      setTrace(t.trace || []);
      return true;
    } catch {
      return false;
    }
  }

  // On load: rehydrate the last session (persistent memory) + session list.
  useEffect(() => {
    refreshSessions();
    if (!sessionId) return;
    (async () => {
      const ok = await loadSession(sessionId);
      if (!ok) {
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
    if (res.fertilizer_schedule) setFertilizer(res.fertilizer_schedule);
    if (res.pest_risk) setPestRisk(res.pest_risk);
    if (res.scenario) setScenario(res.scenario);
    if (res.weather_alerts) setAlerts(res.weather_alerts);
    if (res.market) setMarket(res.market);
    if (res.suppliers) setSuppliers(res.suppliers);
    if (res.disease) setDisease(res.disease);
    if (res.trace?.length) setTrace((t) => [...t, ...res.trace]);
    // Auto-focus the newest artifact so the user never has to hunt for it.
    // The freshest answer is what the farmer just asked for, so it wins focus.
    if (res.market) setTab("market");
    else if (res.suppliers) setTab("suppliers");
    else if (res.scenario) setTab("scenario");
    else if (res.pest_risk) setTab("pests");
    else if (res.fertilizer_schedule) setTab("fertilizer");
    else if (res.weather_alerts) setTab("weather");
    else if (res.season_plan) setTab("calendar");
    else if (res.crop_options) setTab("crops");
  }

  async function handleSend(text) {
    if (busy) return; // one in-flight request per session — no double-fires
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await sendChat(sessionId, text, lang);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      applyResponse(res);
      refreshSessions(); // keep the sidebar labels/counts current
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `⚠️ ${e.message}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  // Farmer uploaded a crop photo → run AI disease diagnosis (Tier 2).
  async function handleImage(dataUrl) {
    if (busy) return;
    setDiseaseImg(dataUrl);
    setMessages((m) => [...m, { role: "user", content: "📷 (uploaded a crop photo)" }]);
    setBusy(true);
    try {
      const crop = plan?.crop || financials?.crop || crops?.options?.[0]?.crop;
      const res = await diagnose(sessionId, dataUrl, crop, lang);
      const d = res.diagnosis || {};
      setDisease(d);
      setTab("disease");
      const line = d.is_plant === false
        ? d.message
        : d.error
        ? d.error
        : `Diagnosis: ${d.diagnosis} (${d.confidence} confidence). See the Diagnosis tab.`;
      setMessages((m) => [...m, { role: "assistant", content: line }]);
      if (res.trace?.length) {
        setTrace((t) => [
          ...t,
          ...res.trace.map((s, i) => ({ ...s, step: t.length + i + 1 })),
        ]);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${e.message}` }]);
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
    setFertilizer(null);
    setPestRisk(null);
    setScenario(null);
    setAlerts(null);
    setMarket(null);
    setSuppliers(null);
    setDisease(null);
    setDiseaseImg(null);
    setTab(null);
  }

  // Which output panel to show: the selected tab if it still has data,
  // otherwise the most advanced artifact available. Order here is the
  // fallback priority.
  const TABS = [
    { key: "crops", label: t(lang, "tab.crops"), data: crops },
    { key: "calendar", label: t(lang, "tab.calendar"), data: plan },
    { key: "finance", label: t(lang, "tab.finance"), data: financials },
    { key: "fertilizer", label: t(lang, "tab.fertilizer"), data: fertilizer },
    { key: "pests", label: t(lang, "tab.pests"), data: pestRisk },
    { key: "scenario", label: t(lang, "tab.scenario"), data: scenario },
    { key: "weather", label: t(lang, "tab.weather"), data: alerts },
    { key: "market", label: t(lang, "tab.market"), data: market },
    { key: "suppliers", label: t(lang, "tab.suppliers"), data: suppliers },
    { key: "disease", label: t(lang, "tab.disease"), data: disease },
    // Payment is always reachable so judges can find the bdapps checkout;
    // the panel itself asks for a first message if there's no session yet.
    { key: "payment", label: t(lang, "tab.payment"), data: { always: true } },
  ];
  const available = TABS.filter((t) => !!t.data);
  const fallbackOrder = [
    "disease",
    "market",
    "suppliers",
    "scenario",
    "pests",
    "fertilizer",
    "weather",
    "calendar",
    "crops",
    "finance",
    "payment",
  ];
  const effectiveTab =
    available.find((t) => t.key === tab)?.key ??
    fallbackOrder.find((k) => available.some((t) => t.key === k)) ??
    null;

  return (
    <div className="app">
      {busy && <div className="loadbar" aria-hidden="true" />}

      <header className="topbar">
        <h1 aria-label="AgriSense AI">
          <span className="w" aria-hidden="true">🌾</span>{" "}
          <span className="w" aria-hidden="true">AgriSense</span>{" "}
          <span className="w accent" aria-hidden="true">AI</span>
        </h1>
        <span className="team">Team Alnitak · Bdapps Agentic AI Hackathon</span>
        <div className="lang-toggle" role="group" aria-label="Reply language">
          {[
            ["en", "EN"],
            ["bn", "বাংলা"],
          ].map(([code, label]) => (
            <button
              key={code}
              className={lang === code ? "active" : ""}
              onClick={() => {
                setLang(code);
                localStorage.setItem("agrisense_lang", code);
              }}
              title={code === "bn" ? "Reply in Bengali" : "Reply in English"}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          className={`toggle-sessions ${showSessions ? "active" : ""}`}
          onClick={() => setShowSessions((v) => !v)}
        >
          {t(lang, "top.sessions")}{sessions.length ? ` (${sessions.length})` : ""}
        </button>
        <button className="new-session" onClick={newSession}>
          {t(lang, "top.new")}
        </button>
      </header>

      <main className={`grid ${showSessions ? "with-sidebar" : ""}`}>
        {showSessions && (
          <aside className="sidebar">
            <SessionList
              sessions={sessions}
              currentId={sessionId}
              busy={busy}
              onSelect={loadSession}
              onNew={newSession}
              lang={lang}
            />
          </aside>
        )}
        <section className="left">
          <ChatPanel
            messages={messages}
            busy={busy}
            onSend={handleSend}
            onImage={handleImage}
            lang={lang}
          />
          <ProfileCard farm={farm} lang={lang} />

          {effectiveTab && (
            <div className="tab-bar">
              {available.map((t) => (
                <button
                  key={t.key}
                  className={effectiveTab === t.key ? "active" : ""}
                  onClick={() => setTab(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}

          {busy && !effectiveTab && <OutputSkeleton />}

          {effectiveTab === "crops" && (
            <CropOptions
              data={crops}
              busy={busy}
              lang={lang}
              onPick={(crop) => {
                // Rebuild for the new crop every panel already on screen, so
                // nothing is left showing the previous crop. Only mention the
                // panels that currently exist.
                const also = [
                  fertilizer && "fertilizer schedule",
                  pestRisk && "pest risk",
                  alerts && "weather alerts",
                  market && "market price",
                  suppliers && "supplier comparison",
                ].filter(Boolean);
                const extra = also.length
                  ? `, and also update the ${also.join(", ")} for it`
                  : "";
                handleSend(
                  `Let's go with ${crop}. Build the season plan and financials${extra}.`
                );
              }}
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
          {effectiveTab === "calendar" && <PlanView plan={plan} lang={lang} />}
          {effectiveTab === "finance" && <FinanceTable financials={financials} lang={lang} />}
          {effectiveTab === "fertilizer" && <FertilizerView schedule={fertilizer} lang={lang} />}
          {effectiveTab === "pests" && <PestRiskView risk={pestRisk} lang={lang} />}
          {effectiveTab === "scenario" && <ScenarioView scenario={scenario} lang={lang} />}
          {effectiveTab === "weather" && <WeatherAlerts data={alerts} lang={lang} />}
          {effectiveTab === "market" && <MarketView market={market} lang={lang} />}
          {effectiveTab === "suppliers" && <SupplierView suppliers={suppliers} lang={lang} />}
          {effectiveTab === "disease" && <DiseaseView disease={disease} image={diseaseImg} lang={lang} />}
          {effectiveTab === "payment" && (
            <PaymentPanel
              sessionId={sessionId}
              crop={plan?.crop || financials?.crop || crops?.options?.[0]?.crop}
              onCharged={(steps) =>
                setTrace((t) => [
                  ...t,
                  ...steps.map((s, i) => ({ ...s, step: t.length + i + 1 })),
                ])
              }
            />
          )}
        </section>

        <aside className="right">
          <TracePanel trace={trace} />
        </aside>
      </main>
    </div>
  );
}

// Shimmering placeholder that mirrors the shape of the oncoming output card
// (title → chips → ranked tiles) so the layout doesn't jump when data lands.
function OutputSkeleton() {
  return (
    <div className="card" aria-hidden="true">
      <div className="skeleton">
        <div className="sk sk-title" />
        <div className="sk-grid">
          <div className="sk sk-chip" />
          <div className="sk sk-chip" />
          <div className="sk sk-chip" />
        </div>
        <div className="sk sk-tall" />
        <div className="sk sk-tall" />
        <div className="sk sk-row" style={{ width: "70%" }} />
      </div>
    </div>
  );
}
