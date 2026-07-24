# Tier checklist (track progress here)

Legend: ⬜ not started · 🟨 in progress · ✅ done

## Tier 0 — Core (REQUIRED, must run end to end)
- ✅ **1. Conversational intake** — collects location, size, soil, water, budget,
  season; asks targeted follow-ups only for missing fields
- ✅ **2. Live weather grounding** — Open-Meteo call returning real rain/temp,
  wired into the agent loop and crop ranking
- ✅ **3. Crop recommendation** — ≥3 ranked crops w/ suitability, water, risk, profit
- ✅ **4. Season plan** — dated calendar: prep → sowing → fertilizer → irrigation
  → weed/pest checkpoints → harvest
- ✅ **5. Financial projection** — itemized costs + yield, revenue, net, ROI,
  break-even; inspectable & internally consistent *(tests written)*
- ✅ **6. Explained reasoning** — every recommendation names inputs + retrieved data
- ✅ **7. Knowledge base + RAG** — public agronomic docs → Chroma → grounds advice
- ✅ **8. Visible agent trace** — every tool call + params + raw result,
  rendered in the UI trace panel per turn

## Tier 1 — Advanced (differentiators)
- ✅ Persistent memory (cross-session — SQLite; profile/history/plan survive
  restarts; session-history sidebar; agent trace persisted too)
- ✅ Proactive weather-triggered advice (`weather_advisory` tool: live forecast
  cross-checked against the dated plan → "delay urea before heavy rain" alerts,
  KB-grounded thresholds, rendered in a Weather alerts panel)
- ⬜ Fertilizer & irrigation scheduler
- ⬜ Pest & disease risk
- ⬜ Scenario simulation (what-if)

## Tier 2 — Ambitious (bonus, only after Tier 0 solid)
- ✅ bdapps CaaS payment + SMS delivery — honest freemium: the season calendar
  shows a 3-stage free preview; a 1 BDT Direct Debit (BDApps API Guide §5.3,
  `caas/direct/debit`) unlocks the full dated calendar AND sends the farmer's
  first weather/pest alert via SMS Send (§3.1, `sms/send`). Subscriber number
  normalized to `tel:8801XXXXXXXXX`, basket summed server-side, password
  masked, receipt persisted (`receipts` table), charge + SMS shown in the agent
  trace. Sandbox simulator by default; flips to the real provisioned app
  (APP_139265, whitelisted test number) via `BDAPPS_SANDBOX=false` + API key.
- ⬜ Market price intelligence (sell/store/wait)
- ⬜ Marketplace / supplier comparison
- ⬜ Plant disease detection from images
- ⬜ Bengali / voice interaction

## Judging weights (for prioritisation)
Agentic behavior 20 · Accuracy & math 20 · Scope & execution 15 ·
Knowledge base 12 · bdapps payment 10 · Explainability 10 · Technical 8 ·
Innovation 5 → **Tier 0 alone covers ~85 of 100.**
