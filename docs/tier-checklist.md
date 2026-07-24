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
- ✅ bdapps CaaS payment + SMS delivery — all in-app advice (incl. the full
  season calendar) is free; the Premium tab is an optional add-on: a 1 BDT
  Direct Debit (BDApps API Guide §5.3, `caas/direct/debit`) subscribes the
  farmer to season-long weather/pest alerts, delivered via SMS Send (§3.1,
  `sms/send`) to their phone. Subscriber number normalized to
  `tel:8801XXXXXXXXX`, basket summed server-side, password masked, receipt
  persisted (`receipts` table), charge + SMS shown in the agent trace. Sandbox
  simulator by default; flips to the real provisioned app (APP_139290,
  whitelisted test number) via `BDAPPS_SANDBOX=false` + API key, with a PHP
  relay (see `bdapps-relay/`) to satisfy bdapps' originating-IP allowlist.
- ✅ Market price intelligence (`get_market_prices`) — current price, recent
  history + trend, and a SELL-NOW / STORE / WAIT call with reasoning that
  accounts for whether the crop stores well; optional gross-revenue estimate at
  today's price. Prices seeded/mock (disclosed). `MarketView` panel; tested.
- ✅ Marketplace / supplier comparison (`compare_suppliers`) — sizes the farm's
  fertilizer basket from the crop's FRG dose table × acres (sandy-soil MoP
  bump), prices it at every supplier, ranks cheapest-first with BDT saved and
  delivery/rating tradeoffs. Catalog seeded/mock (disclosed). `SupplierView`
  panel; tested.
- ✅ Plant disease detection from images (`detect_disease` + `/api/diagnose`) —
  farmer uploads a leaf photo from the chat composer; a vision LLM identifies
  the crop + disease/pest with confidence and visible symptoms, then the
  treatment is KB-grounded (IPM-first, costed) where the condition matches
  `pest_reference.json`, model-suggested otherwise (flagged). `DiseaseView`
  panel with the photo, diagnosis and the "confirm with an extension officer"
  disclaimer. Tested with a mocked vision call.
- ✅ Bengali + voice interaction — EN/বাংলা toggle: the agent replies entirely
  in Bengali while tool arguments stay English (deterministic tools keep
  matching). 🎤 voice input via the Web Speech API (bn-BD / en-US per the
  toggle) transcribes speech into the composer for low-literacy farmers.

## Judging weights (for prioritisation)
Agentic behavior 20 · Accuracy & math 20 · Scope & execution 15 ·
Knowledge base 12 · bdapps payment 10 · Explainability 10 · Technical 8 ·
Innovation 5 → **Tier 0 alone covers ~85 of 100.**
