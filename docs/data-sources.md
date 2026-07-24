# Data sources (real vs mock disclosure)

Keep this file honest — it backs the real-vs-mock table in the root README, which
the hackathon submission explicitly requires.

## Real / live
- **Weather** — [Open-Meteo](https://open-meteo.com/) forecast + geocoding APIs.
  Keyless. Returns real rainfall, temperature, precipitation probability.

## Real / collected (RAG knowledge base)
14 documents in `backend/data/knowledge_base/` → 118 chunks in Chroma, covering
**19 crops**. Content is **compiled/authored by the team following public
Bangladesh extension knowledge** (not scraped from the original PDFs) — disclose
this honestly; it satisfies "collected from publicly available sources."

| Document | Topic | Underlying public sources |
|----------|-------|---------------------------|
| aman_rice_guide.md / boro_rice_guide.md / aus_rice_guide.md | rice by season | BRRI Adhunik Dhaner Chash, DAE |
| maize_guide.md | maize (Kharif/Rabi) | DAE maize guide, BARC FRG-2018 |
| potato_guide.md | potato | BARI potato guide, DAE |
| wheat_mustard_jute_guide.md | wheat, mustard, jute | BWMRI, BARI, BJRI, DAE |
| pulses_guide.md | lentil, chickpea, mungbean | BARI pulse guides, DAE |
| spices_guide.md | onion, garlic, chili | BARI spice research, DAE |
| vegetables_guide.md | tomato, brinjal | BARI vegetable guides, DAE IPM |
| other_crops_guide.md | groundnut, sugarcane, sweet potato | BARI, BSRI, DAE |
| fertilizer_guide.md | N-P-K doses per crop | BARC Fertilizer Recommendation Guide 2018 |
| soil_water_suitability.md | soil × crop, water need, rainfall | SRDI, BARC, FAO |
| pest_disease_reference.md | pests/diseases by crop+stage | DAE IPM leaflets, BRRI/BARI |
| crop_calendar_overview.md | month-by-month planting | DAE national crop calendar |

> Public sources referenced: BRRI, BARI, BARC (FRG-2018), BWMRI, BJRI, BSRI,
> SRDI, DAE (Department of Agricultural Extension), and FAO crop guides.

## Structured reference data (drives the numbers)
The hard figures used in ranking and financial math come from structured seed
files, compiled from the same public extension figures:
- `backend/data/seed/crop_profiles.json` — per-crop seasons, sowing windows,
  soil suitability, water need, risk, and dated growth stages (19 crops).
- `backend/data/seed/crop_economics.json` — per-acre costs, yields, prices.
> Design note: RAG grounds the *narrative + citations*; these JSON files ground
> the *computed numbers*. Be ready to explain that split.

## Mock / seeded (disclosed)
- **Market prices** — `backend/data/seed/market_prices.json` (placeholder BDT
  values). Replace with a real price board feed if one is wired.
- **Supplier catalog** — `backend/data/seed/suppliers.json` (mock; a seeded
  catalog is explicitly permitted by the brief).

## Sandbox / simulated
- **bdapps CaaS charging** — `backend/app/bdapps/caas.py` simulates the
  charge → deduction → receipt flow. Set `BDAPPS_SANDBOX=false` with real
  credentials to hit the actual bdapps sandbox endpoint.
