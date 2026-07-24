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
| **1** | Proactive weather-triggered advice | `tools/advisory.py` + `WeatherAlerts` panel | done (live forecast × dated plan → alerts, e.g. "delay urea before heavy rain") |
| **1** | Fertilizer / irrigation scheduler | `tools/fertilizer.py` | stub |
| **1** | Pest & disease risk | `tools/pests.py` | stub |
| **1** | Scenario simulation (what-if) | `tools/scenario.py` | stub |
| **2** | bdapps CaaS payment (sandbox) | `bdapps/caas.py`, `api/routes_payment.py` | working (sandbox sim) |
| **2** | Market price intelligence | `tools/market.py` | stub |
| **2** | Bengali / voice | frontend + prompts | future |

> Scope discipline: **Tier 0 must run end to end before any Tier 1/2 work.**

## Real vs mock data

The hackathon README **must** state what is real vs mock. Keep this table honest.

| Data / service | Real or mock | Source |
|----------------|--------------|--------|
| Weather (rainfall, temperature, forecast) | **REAL** | Open-Meteo API (keyless) |
| Agronomic knowledge base (crop calendars, fertilizer guides, soil/yield refs) | **REAL (collected)** | Public extension manuals — see `docs/data-sources.md` |
| Crop/soil suitability rules | REAL-derived | Grounded in retrieved KB |
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
