"""Plant disease / pest detection from a photo (Tier 2).

A farmer uploads a photo of an affected leaf or plant. A vision LLM identifies
the crop and the most likely disease/pest/deficiency with visible symptoms and
its confidence. We then GROUND the treatment: if the identified condition
matches an entry in our KB pest/disease reference (data/seed/pest_reference.json,
from DAE IPM leaflets / BRRI-BARI guides), we return that entry's IPM-first
prevention, treatment and per-acre cost — not the model's free-text guess.

The photo diagnosis itself is a real vision-model call (not mock); the treatment
is KB-grounded where a match exists, model-suggested otherwise (flagged).
"""
from __future__ import annotations

import difflib
from typing import Any

from app.agent.llm import LLMClient
from app.tools.seed_data import match_crop_name

_VISION_SYSTEM = (
    "You are an experienced Bangladeshi plant pathologist and agricultural "
    "extension officer. Look at the photo of a crop plant/leaf and identify the "
    "problem. Be honest about uncertainty. Respond ONLY as JSON with keys:\n"
    '  "is_plant" (bool),\n'
    '  "crop" (string, best guess of the crop, or ""),\n'
    '  "condition" ("healthy" | "disease" | "pest" | "deficiency" | "unknown"),\n'
    '  "name" (the specific disease/pest/deficiency, or "" if healthy/unknown),\n'
    '  "confidence" ("high" | "medium" | "low"),\n'
    '  "visible_symptoms" (array of short strings you actually see),\n'
    '  "severity" ("mild" | "moderate" | "severe" | ""),\n'
    '  "reasoning" (one sentence citing the visual evidence),\n'
    '  "advice" (one or two sentences of first-response guidance).\n'
    "Never invent a pesticide dose. If the image is not a plant, set is_plant "
    "false and condition unknown."
)

# Photo analysis is free-form (no fixed template to translate), so for Bengali
# we ask the model to write the free-text fields in Bangla directly, while
# keeping the structured enums + the English disease name (so KB matching and
# the deterministic frontend tokens still work).
_VISION_BN = (
    "\nIMPORTANT: write visible_symptoms, reasoning and advice in BENGALI "
    "(Bangla script), simple words a smallholder farmer understands. Keep "
    "is_plant, condition, confidence, severity and name in ENGLISH exactly as "
    "the enums above (name = the disease/pest common English name)."
)


def _vision_system(lang: str | None) -> str:
    return _VISION_SYSTEM + (_VISION_BN if (lang or "en").lower() == "bn" else "")


def _kb_match(crop_name: str | None, disease_name: str) -> dict[str, Any] | None:
    """Find the closest KB pest/disease entry for the identified condition.

    Searches the crop's entries first (if we recognise the crop), then all
    crops. Uses a fuzzy name match so 'late blight' ↔ 'Late blight (P. infestans)'
    still lines up.
    """
    from app.tools.pests import _pest_reference  # reuse the pests loader

    ref = _pest_reference().get("crops", {})
    target = disease_name.strip().lower()
    if not target:
        return None

    def best_in(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
        names = [e.get("name", "") for e in entries]
        lowered = [n.lower() for n in names]
        # direct substring either way
        for e, low in zip(entries, lowered):
            if low and (low in target or target in low):
                return e
        # fuzzy
        hit = difflib.get_close_matches(target, lowered, n=1, cutoff=0.6)
        if hit:
            return entries[lowered.index(hit[0])]
        return None

    if crop_name and crop_name in ref:
        m = best_in(ref[crop_name])
        if m:
            return m
    for entries in ref.values():
        m = best_in(entries)
        if m:
            return m
    return None


async def detect_disease(
    image_data_url: str,
    crop: str | None = None,
    llm: LLMClient | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    """Diagnose a crop photo and attach KB-grounded treatment where possible."""
    client = llm or LLMClient()
    hint = f" The farmer says this is {crop}." if crop else ""
    vision = await client.vision_json(
        _vision_system(lang),
        "Diagnose this crop photo." + hint,
        image_data_url,
    )
    if not vision:
        return {"error": "could not analyse the image — please try a clearer, "
                "well-lit close-up of the affected leaf"}

    if vision.get("is_plant") is False:
        return {
            "is_plant": False,
            "message": "That doesn't look like a crop plant — please upload a "
            "close-up photo of the affected leaf or plant.",
        }

    identified_crop = match_crop_name(vision.get("crop", "") or (crop or "")) or (
        vision.get("crop") or crop
    )
    condition = vision.get("condition", "unknown")
    name = (vision.get("name") or "").strip()

    result: dict[str, Any] = {
        "crop": identified_crop,
        "condition": condition,
        "diagnosis": name or ("Healthy" if condition == "healthy" else "Unclear"),
        "confidence": vision.get("confidence", "low"),
        "visible_symptoms": vision.get("visible_symptoms", []),
        "severity": vision.get("severity", ""),
        "because": vision.get("reasoning", ""),
        "source": "AI vision diagnosis (OpenAI vision model)",
        "disclaimer": "AI photo estimate — confirm with a local agriculture "
        "extension officer before applying any chemical.",
    }

    # Ground the treatment in the KB where the condition matches a known entry.
    kb = _kb_match(identified_crop, name) if condition in ("disease", "pest") else None
    if kb:
        result["kb_grounded"] = True
        result["treatment"] = kb.get("treatment")
        result["prevention"] = kb.get("prevention", [])
        result["threshold"] = kb.get("threshold")
        result["cost_bdt_per_acre"] = kb.get("cost_bdt_per_acre")
        result["kb_source"] = kb.get("source")
        result["kb_name"] = kb.get("name")
    else:
        result["kb_grounded"] = False
        result["treatment"] = vision.get("advice", "")
        result["prevention"] = []

    return result
