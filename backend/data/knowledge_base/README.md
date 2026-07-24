# Knowledge base (RAG source documents)

Drop **public agronomic reference documents** here as `.md` or `.txt`. These are
collected from publicly available sources and indexed by `scripts/ingest_kb.py`
into a local Chroma store. The agent's crop, fertilizer, and season-plan advice
must be **grounded in what it retrieves from these files**, not model recall.

## What to collect (Bangladesh-relevant)
- **Crop calendars** — sowing/harvest windows and growth-stage days-after-sowing
  (e.g. BRRI rice calendars, DAE crop calendars).
- **Fertilizer guides** — N-P-K / urea-TSP-MoP dose tables per crop and soil
  (e.g. BARC Fertilizer Recommendation Guide).
- **Soil & yield references** — soil-type suitability, typical yields per acre.
- **Pest & disease guides** — common pests by crop + growth stage, treatments.

## Format tips
- One topic per file; keep tables as plain text/markdown so chunks stay readable.
- Put a clear title line at the top of each file — it becomes the citation source
  shown in the agent trace.
- Record where each document came from in `docs/data-sources.md` (for the
  README's real-vs-mock disclosure).

## Suggested starter files
```
brri_boro_rice_calendar.md
barc_fertilizer_guide_rice.md
maize_crop_calendar.md
potato_crop_calendar.md
soil_suitability_reference.md
common_pests_rice_maize.md
```
> This folder is intentionally near-empty in the skeleton. Populate it during the
> build, then run `python scripts/ingest_kb.py`.
