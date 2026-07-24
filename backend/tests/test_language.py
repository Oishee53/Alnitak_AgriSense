"""Language directive tests (Tier 2 — Bengali support).

The system prompt must switch the reply language while keeping tool arguments in
English, so the deterministic tools keep matching crop/soil/season names.
"""
from __future__ import annotations

from app.agent.prompts import build_system_prompt


def test_bengali_directive_present_when_bn():
    p = build_system_prompt({}, [], lang="bn")
    assert "Bengali" in p or "বাংলা" in p
    # tool arguments must stay English
    assert "tool arguments" in p.lower() and "english" in p.lower()


def test_default_is_english():
    for lang in (None, "en", "xx"):
        p = build_system_prompt({}, [], lang=lang)
        assert "clear, simple English" in p


def test_profile_and_missing_still_rendered():
    p = build_system_prompt(
        {"location": "Rangpur", "soil_type": "loam"}, ["budget_bdt"], lang="bn"
    )
    assert "Rangpur" in p and "budget_bdt" in p
