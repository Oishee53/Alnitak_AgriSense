"""Shared loader for the seed reference data (crop profiles + economics).

Loaded once and cached. Paths resolve relative to the backend/ working dir
(same convention as settings.kb_dir).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


@lru_cache
def crop_profiles() -> dict[str, Any]:
    with open(_SEED_DIR / "crop_profiles.json", encoding="utf-8") as fh:
        return json.load(fh)["crops"]


@lru_cache
def crop_economics() -> dict[str, Any]:
    with open(_SEED_DIR / "crop_economics.json", encoding="utf-8") as fh:
        return json.load(fh)["crops"]


@lru_cache
def market_prices() -> dict[str, Any]:
    with open(_SEED_DIR / "market_prices.json", encoding="utf-8") as fh:
        return json.load(fh)["prices"]


def normalize_season(season: str | None) -> str | None:
    """Map free-text season names to canonical: kharif-1, kharif-2, rabi."""
    if not season:
        return None
    s = season.strip().lower()
    if any(k in s for k in ("aman", "kharif-2", "kharif 2", "monsoon", "july", "august")):
        return "kharif-2"
    if any(k in s for k in ("boro", "rabi", "winter", "dry season")):
        return "rabi"
    if any(k in s for k in ("aus", "kharif-1", "kharif 1", "summer", "pre-monsoon", "spring")):
        return "kharif-1"
    if "kharif" in s:  # bare "kharif" — monsoon season is the common meaning
        return "kharif-2"
    return s


# Rice-specific season names. When a farmer names one of these they are naming a
# specific rice crop they intend to grow, not just a calendar window. We keep
# normalize_season() mapping them to the shared calendar season (so other
# same-window crops stay available as alternatives) but recover the rice intent
# separately here, so an explicit "Boro"/"Aman"/"Aus" request is never silently
# swapped for a different, higher-profit crop that shares the season.
_SEASON_RICE_CROP = {
    "aman": "T. Aman Rice",
    "boro": "Boro Rice",
    "aus": "Aus Rice",
}


def season_rice_crop(season: str | None) -> str | None:
    """The specific rice crop a rice-season name implies (Aman/Boro/Aus), else None."""
    if not season:
        return None
    s = season.strip().lower()
    for key, crop in _SEASON_RICE_CROP.items():
        if key in s:
            return crop
    return None


def normalize_soil(soil: str | None) -> str:
    """Map free-text soil descriptions onto our four texture keys."""
    s = (soil or "").strip().lower()
    if "sand" in s:
        return "sandy"
    if "clay" in s:
        return "clay"
    if "silt" in s:
        return "silt"
    return "loam"  # loam / unknown default (most forgiving texture)


def match_crop_name(crop: str) -> str | None:
    """Fuzzy-match a user/LLM crop name to a seed-data key."""
    c = crop.strip().lower()
    profiles = crop_profiles()
    for name in profiles:
        if name.lower() == c:
            return name
    for name in profiles:
        if c in name.lower() or name.lower() in c:
            return name
    aliases = {
        "aus": "Aus Rice",
        "aman": "T. Aman Rice",
        "aman rice": "T. Aman Rice",
        "paddy": "T. Aman Rice",
        "boro": "Boro Rice",
        "rice": "T. Aman Rice",
        "dhan": "T. Aman Rice",
        "maize": "Maize (Kharif)",
        "corn": "Maize (Kharif)",
        "bhutta": "Maize (Kharif)",
        "sweet potato": "Sweet Potato",
        "mishti alu": "Sweet Potato",
        "potato": "Potato",
        "alu": "Potato",
        "sarisha": "Mustard",
        "mustard": "Mustard",
        "pat": "Jute",
        "jute": "Jute",
        "masur": "Lentil",
        "lentil": "Lentil",
        "dal": "Lentil",
        "chola": "Chickpea",
        "gram": "Chickpea",
        "chickpea": "Chickpea",
        "mug": "Mungbean",
        "moog": "Mungbean",
        "mung": "Mungbean",
        "peyaj": "Onion",
        "piyaj": "Onion",
        "onion": "Onion",
        "rosun": "Garlic",
        "garlic": "Garlic",
        "morich": "Chili",
        "chilli": "Chili",
        "chili": "Chili",
        "pepper": "Chili",
        "tomato": "Tomato",
        "tomato ": "Tomato",
        "begun": "Brinjal",
        "brinjal": "Brinjal",
        "eggplant": "Brinjal",
        "aubergine": "Brinjal",
        "badam": "Groundnut",
        "chinabadam": "Groundnut",
        "groundnut": "Groundnut",
        "peanut": "Groundnut",
        "aakh": "Sugarcane",
        "akh": "Sugarcane",
        "sugarcane": "Sugarcane",
        "cane": "Sugarcane",
    }
    for key, name in aliases.items():
        if key in c:
            return name
    return None
