# Architecture

## One-line
A hand-written **tool-calling agent loop** (FastAPI backend) that gathers the
farm profile, grounds every fact in real tools (weather API + RAG knowledge
base) and pure-Python math, and streams a **visible trace** to a React UI.

## Request lifecycle (one farmer turn)
1. `POST /api/chat` → `routes_chat.chat`
2. `store.get_or_create_session` loads farm profile + history (persistent memory)
3. `Orchestrator.run`:
   - build system prompt, injecting **missing intake fields** as targeted asks
   - loop up to `MAX_STEPS`:
     - LLM decides: ask a follow-up, or call tool(s)
     - each tool call + raw result is written to `trace`
     - results fed back to the LLM
   - stop when the LLM returns prose with no tool call
4. `store.save_turn` persists messages, updated profile, and any plan/financials
5. Frontend renders reply + `PlanView`/`FinanceTable`; `TracePanel` shows the trace
   (`GET /api/trace/{id}` snapshot, or `/stream` for live SSE)

## Why a hand-written loop (not a framework)
The trace is a scored deliverable — a judge must confirm each number came from a
real call. Owning the loop means we capture every param sent and value returned,
in exactly the shape the UI needs. Frameworks hide this.

## Grounding rules (how we avoid hallucinated numbers)
| Fact type | Source of truth |
|-----------|-----------------|
| Weather (rain, temp) | `tools/weather.py` → Open-Meteo (real) |
| Crop / fertilizer / calendar facts | `rag/retriever.py` → Chroma KB (real, cited) |
| All money | `tools/finance.py` → pure arithmetic (deterministic, tested) |
| Prices / suppliers | `data/seed/*.json` (mock, disclosed) |
| Payment | `bdapps/caas.py` (sandbox) |

## Component map
- `app/agent/` — orchestrator, prompts, tool registry, trace, llm client
- `app/tools/` — one module per capability (weather, crops, season_plan, finance, …)
- `app/rag/` — ingest + retrieve over `data/knowledge_base/`
- `app/memory/` — SQLAlchemy models + store (Farm / Session / Message)
- `app/bdapps/` — CaaS sandbox charging
- `app/api/` — HTTP routes + Pydantic schemas

## Build order (recommended)
1. `llm.py` (OpenAI wiring — done) → `orchestrator.py` loop runs
2. `weather.py` is already real → first grounded tool
3. KB: add docs → `ingest.py` + `retriever.py` → RAG works
4. `crops.py` → `season_plan.py` → `finance.py` (+ pass `tests/test_finance.py`)
5. `memory/store.py` → sessions persist
6. Frontend trace panel end-to-end
7. Only then: Tier 1 (fertilizer, pests, scenario, proactive) and Tier 2 (CaaS, market)
