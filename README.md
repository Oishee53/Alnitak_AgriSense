# Alnitak_AgriSense

> **AgriSense AI** — an autonomous agricultural advisor that takes a smallholder
> farmer from an empty field to a costed, weather-aware season plan, and keeps
> advising through harvest.
>
> Built for the **Bdapps Agentic AI Hackathon** — IUT 12th ICT Fest (powered by Codex).

AgriSense is an **agent, not a chatbot**. From a short conversation it gathers the
farm's specifics, pulls live weather data, retrieves grounded agronomic knowledge,
runs the financial arithmetic, and produces a dated, explained, costed season plan —
exposing every tool call in a visible trace so a judge can confirm each number came
from a real call, not model imagination.

---

## Table of contents
- [Architecture](#architecture)
- [Feature → Tier map](#feature--tier-map)
- [Real vs mock data](#real-vs-mock-data)
- [Repository layout](#repository-layout)
- [Setup](#setup)
- [Tools & APIs used](#tools--apis-used)
- [Team](#team)

---

## Architecture

```
        ┌─────────────────────────────────────────────────────────┐
        │                     Frontend (React/Vite)                │
        │   Chat panel  │  Season plan / finance view  │  TRACE    │
        └───────────────┬─────────────────────────────┬───────────┘
                        │  REST / SSE                  │ (live trace)
        ┌───────────────▼──────────────────────────────────────────┐
        │                  Backend (FastAPI, Python)                 │
        │                                                            │
        │   ┌────────────────────────────────────────────────────┐  │
        │   │           Agent orchestrator (tool-calling loop)     │  │
        │   │   plan → decide tool → call → observe → repeat       │  │
        │   │   + missing-info detection  + trace recorder         │  │
        │   └───┬───────────┬───────────┬──────────┬───────────────┘  │
        │       │           │           │          │                  │
        │   ┌───▼───┐   ┌───▼───┐   ┌───▼────┐  ┌──▼─────┐            │
        │   │Weather│   │  RAG  │   │Finance │  │ Crops/ │  ... tools │
        │   │(live) │   │(Chroma│   │ (math) │  │ season │            │
        │   └───────┘   │  KB)  │   └────────┘  └────────┘            │
        │               └───────┘                                    │
        │                                                            │
        │   Memory (SQLite): farms, sessions, messages, plans        │
        │   bdapps CaaS module (sandbox checkout / charging flow)     │
        └────────────────────────────────────────────────────────────┘
```

The **agent orchestrator** owns the loop. On each turn it inspects what it knows
about the farm, asks targeted follow-ups for missing fields, and chains the tools
in dependent order (weather → crop ranking → season plan → finance). Every step is
written to a **trace** that the frontend renders live.

## Feature → Tier map

| Tier | Feature | Where | Status |
|------|---------|-------|--------|
| **0** | Conversational intake (location, size, soil, water, budget, season) | `agent/orchestrator.py`, `agent/prompts.py` | done |
| **0** | Live weather grounding | `tools/weather.py` (Open-Meteo) | done |
| **0** | Crop recommendation (≥3 ranked) | `tools/crops.py` | done |
| **0** | Season plan (dated calendar) | `tools/season_plan.py` | done |
| **0** | Financial projection (cost, yield, revenue, ROI, break-even) | `tools/finance.py` | done |
| **0** | Explained reasoning | prompts + tool outputs carry `because` fields | done |
| **0** | Knowledge base + RAG | `rag/`, `data/knowledge_base/` | done |
| **0** | Visible agent trace | `agent/trace.py`, frontend `TracePanel` | done |
| **1** | Persistent memory (cross-session) | `memory/` (+ session-history sidebar, persisted agent trace) | done (SQLite; survives restarts) |
| **1** | Proactive weather-triggered advice | `tools/advisory.py` + `WeatherAlerts` panel; `tools/fertilizer.py` also flags rain-delayed urea | done (live forecast × dated plan → alerts, e.g. "delay urea before heavy rain") |
| **1** | Fertilizer / irrigation scheduler | `tools/fertilizer.py` + `FertilizerView` | done (kg + cost per stage, organic option, FRG-2018 doses) |
| **1** | Pest & disease risk | `tools/pests.py` + `PestRiskView` | done (stage × live-weather gated, IPM-first, costed) |
| **1** | Scenario simulation (what-if) | `tools/scenario.py` + `ScenarioView` | done (re-runs the finance engine, diffs every figure) |
| **2** | bdapps CaaS payment + SMS delivery | `bdapps/caas.py`, `bdapps/sms.py`, `api/routes_payment.py`, `PaymentPanel` | done (freemium: 1 BDT Direct Debit unlocks the full season calendar and sends the farmer's alert by SMS; receipt persisted, charge + SMS shown in trace; sandbox or live via provisioned app) |
| **2** | Market price intelligence | `tools/market.py` | stub |
| **2** | Bengali / voice | frontend + prompts | future |

> Scope discipline: **Tier 0 must run end to end before any Tier 1/2 work.**

### Tier 1 detail

**Fertilizer & irrigation scheduler** (`build_fertilizer_schedule`) — returns the
exact kg of each input per application with real dates, the cost of every line,
and a dated irrigation plan. Doses are the BARC FRG-2018 tables; urea/TSP/MoP are
priced at the government-fixed dealer rates. It applies the KB's own adjustment
rules: sandy soil gets +25% MoP and more urea splits; the organic option adds
2 t/acre cowdung and cuts urea and TSP by 20%.

**Proactive, weather-triggered advice** — the same tool cross-references each
urea top-dressing against the live Open-Meteo daily forecast and raises an alert
when >20 mm rain falls within 48 hours, because the KB puts nitrogen runoff loss
at 30–40%. That is a real "delay the nitrogen" recommendation, computed rather
than narrated.

**Pest & disease risk** (`assess_pest_risk`) — a pest is only reported as active
when the crop is inside its days-after-sowing window, and only escalated to
*high* when the live forecast satisfies a weather trigger the KB actually states
(cool+humid → blight and aphids, storm → BLB, standing water → BPH and bacterial
wilt). Each risk carries its symptom, scouting threshold, IPM-first prevention,
treatment, and cost scaled to the farm.

**Scenario simulation** (`simulate_scenario`) — re-runs the real finance engine
with perturbed inputs and diffs every figure. Rainfall shocks are converted to
yield loss through the crop's KB water-need class and then damped by the farm's
irrigation access, so a tubewell farmer and a rainfed farmer get different
answers to the same question. A budget cut resizes the planted area rather than
merely re-pricing it, and the tool returns re-ranked alternative crops under the
new constraint.

**Dose coverage and its two provenance classes** — twelve of the nineteen ranked
crops now carry kg/acre dose tables, from two sources, declared per crop:

- *kb-transcribed* (7 crops: T. Aman rice, Boro rice, maize, potato, wheat,
  mustard, jute) — copied from `fertilizer_guide.md`, which already states doses
  as kg/acre of product.
- *frg-derived* (5 crops: brinjal, tomato, onion, garlic, chili) — read off each
  crop's own table in **BARC FRG-2018** (`data/sources/FRG-2018.pdf`, cited to the
  page). FRG states *nutrient* kg/ha by soil-analysis class, so these are
  converted to product kg/acre using the official nutrient percentages in
  FRG-2018 Appendix-2 (urea 46% N, TSP 20% P, MoP 50% K, gypsum 18% S, zinc
  sulphate monohydrate 36% Zn, boric acid 17% B) and 1 ha = 2.4711 acre.

Every frg-derived crop stores the exact FRG nutrient row it came from in
`frg_nutrient_recommendation_kg_per_ha`, so a judge can reproduce each figure
rather than trust it — and
`test_every_frg_derived_dose_reconciles_with_its_source_row` re-derives all of
them on every test run.

We use the **Medium** soil-fertility row throughout, because `fertilizer_guide.md`
is also stated "for medium-fertility soil", putting both classes on one basis.
This is also what resolved a discrepancy we hit while sourcing: secondary
literature quotes brinjal at 78 kg N/ha and tomato at 253 kg N/ha, a 3× gap that
looked like bad data. FRG-2018 shows tomato's Medium row is 41–80 kg N/ha — the
253 figure was an old BARI-2004 recommendation, over 4× current guidance. We
declined to publish anything until the primary document settled it.

The seven still-uncovered crops (pulses, groundnut, sweet potato, sugarcane) fall
back to a **timing-only** schedule: real dates and split ratios from that crop's
calendar, with no kg and no BDT, and an explicit note that the quantities are not
in our sources. `test_crop_without_a_dose_table_gives_timing_but_never_invents_kg`
enforces that the fallback never invents a quantity.

**Grounding guarantee** — weather parameters are deliberately *not* advertised in
the tool schemas. During development the model was observed inventing a
plausible-looking forecast and passing it in; now the orchestrator discards
anything the model supplies for those fields and injects the real `get_weather`
result, recording the substitution in the trace. Tests in
`tests/test_tier1.py` lock this behaviour in.

## Real vs mock data

The hackathon README **must** state what is real vs mock. Keep this table honest.

| Data / service | Real or mock | Source |
|----------------|--------------|--------|
| Weather (rainfall, temperature, forecast) | **REAL** | Open-Meteo API (keyless) |
| Agronomic knowledge base (crop calendars, fertilizer guides, soil/yield refs) | **REAL (collected)** | Public extension manuals — see `docs/data-sources.md` |
| Crop/soil suitability rules | REAL-derived | Grounded in retrieved KB |
| Fertilizer doses — rice, maize, potato, wheat, mustard, jute | **REAL (collected)** | DAE/BARC figures in `data/knowledge_base/fertilizer_guide.md`, transcribed to `data/seed/fertilizer_reference.json` |
| Fertilizer doses — brinjal, tomato, onion, garlic, chili | **REAL (primary source)** | BARC FRG-2018 (`data/sources/FRG-2018.pdf`), cited per page; nutrient kg/ha → product kg/acre via FRG Appendix-2 percentages, derivation stored and unit-tested |
| Urea / TSP / DAP / MoP prices | **REAL** | Government-fixed dealer prices (MoA notification, Apr-2023) |
| Gypsum, zinc, boron, cowdung prices | MOCK / estimated | market estimates — flagged per line in the tool output |
| Pest & disease profiles (symptom, threshold, IPM, treatment) | **REAL (collected)** | DAE IPM leaflets, BRRI/BARI plant-protection guides → `data/seed/pest_reference.json` |
| Pest treatment costs | MIXED | KB-stated where the source gives a figure; otherwise estimated — each entry declares which in `cost_basis` |
| Market prices | **MOCK / seeded** | `data/seed/market_prices.json` (until a real feed is wired) |
| Supplier catalog | **MOCK / seeded** | `data/seed/suppliers.json` |
| bdapps CaaS charging | **SANDBOX / simulated** | `bdapps/caas.py` (mirrors bdapps CaaS request/response) |
| LLM reasoning | REAL | OpenAI (gpt-4o-mini default, configurable) |

## Repository layout

```
Alnitak-AgriSense/
├── backend/            FastAPI agent server (Python)
│   ├── app/
│   │   ├── api/        HTTP routes + Pydantic schemas
│   │   ├── agent/      orchestrator, prompts, tool registry, trace, LLM client
│   │   ├── tools/      weather, crops, season_plan, finance, fertilizer, pests, ...
│   │   ├── rag/        ingest + retrieve over the knowledge base
│   │   ├── memory/     SQLite models + store (farms, sessions, messages)
│   │   └── bdapps/     CaaS sandbox checkout/charging module
│   ├── data/           knowledge_base/ (RAG docs) + seed/ (mock data)
│   ├── scripts/        one-off scripts (KB ingest)
│   └── tests/
├── frontend/           Vite + React chat UI with live trace panel
├── bdapps-reference/   ORIGINAL provided bdapps PHP (reference only — not run by us)
└── docs/               architecture, tier checklist, data sources
```

## Setup

### Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# bash:                source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in OPENAI_API_KEY etc.
python scripts/ingest_kb.py # build the RAG index from data/knowledge_base
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env        # point VITE_API_BASE at the backend
npm run dev
```

Backend docs (Swagger) at `http://localhost:8000/docs`.

## Tools & APIs used
- **LLM:** OpenAI (`OPENAI_API_KEY`, default `gpt-4o-mini`) — provider abstraction in `agent/llm.py`.
- **Weather:** [Open-Meteo](https://open-meteo.com/) — free, keyless, real forecast + historical.
- **Vector store / RAG:** ChromaDB (local, persistent).
- **Memory:** SQLite via SQLAlchemy.
- **bdapps CaaS:** sandbox simulation of the Charging-as-a-Service flow (per
  [bdapps tap API docs](https://dev.bdapps.com/API_Documentation/bdapps_tap_api.html)).

## Team
**Alnitak** — IUT 12th ICT Fest, Bdapps Agentic AI Hackathon (Final Round).

## License
See [LICENSE](LICENSE).
