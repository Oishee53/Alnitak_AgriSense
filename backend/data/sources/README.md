# Primary source documents

Original PDFs that `data/knowledge_base/*.md` and `data/seed/*_reference.json`
are derived from. Nothing here is read at runtime — the agent reads the
knowledge base and the seed JSON. This folder exists so a reviewer can trace any
number back to the document it came from.

The PDFs themselves are **not committed** (the FRG guide alone is ~43 MB). Fetch
them with the links below if you need to re-check a figure.

## FRG-2018.pdf — BARC *Fertilizer Recommendation Guide 2018* (223 pp, English)

Source for the fertilizer doses of **brinjal, tomato, onion, garlic and chili**
in `data/seed/fertilizer_reference.json` (those entries are marked
`"provenance": "frg-derived"` and cite their page).

Download from whichever responds — these hosts block non-Bangladesh traffic:

- https://moa.portal.gov.bd/sites/default/files/files/moa.portal.gov.bd/page/9d1b92d4_1793_43af_9425_0ed49f27b8d0/FRG-2018%20(English).pdf
- https://barc.portal.gov.bd/sites/default/files/files/barc.portal.gov.bd/page/4adead4d_6e17_4d74_b5bd_e86e46c059ad/88c1738fe0618daef286ef3d27c95423.pdf
- https://www.bfa-fertilizer.org/fertilizer-recommendation-guide/ (links to English + Bangla)

Save as `FRG-2018.pdf` in this folder.

### Pages used

| Page | Table |
|------|-------|
| 101 | Tomato (Winter) |
| 102 | Brinjal |
| 109 | Onion |
| 110 | Garlic |
| 112 | Chilli |
| 196 | Appendix-2 — nutrient compositions of fertilizers (the conversion factors) |

The guide is a scanned PDF with no text layer, so pages were rendered to images
and read manually rather than parsed.

### How to re-check a number

FRG states **nutrient** kg/ha by soil-analysis class; our tables store **product**
kg/acre. Each derived crop keeps its source row in
`frg_nutrient_recommendation_kg_per_ha`, and the conversion is:

```
product_kg_per_acre = (nutrient_kg_per_ha / nutrient_fraction) / 2.4711
```

using the Appendix-2 percentages recorded in `_derivation.nutrient_composition_pct`
(urea 46% N, TSP 20% P, MoP 50% K, gypsum 18% S, zinc sulphate monohydrate 36% Zn,
boric acid 17% B). We use the **Medium** soil-fertility row throughout, matching
`fertilizer_guide.md`, which is also stated for medium-fertility soil.

`tests/test_tier1.py::test_every_frg_derived_dose_reconciles_with_its_source_row`
re-derives every figure from those stored rows on each test run.

### Still to transcribe

Aus rice, lentil, chickpea, mungbean, groundnut, sugarcane and sweet potato have
no dose table yet — the scheduler returns timing only for them. Their FRG tables
are at: pulses p86, oilseeds p89, root and tuber crops p93.
