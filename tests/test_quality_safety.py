"""Tests for WO-010.2 quality safety rules."""

from __future__ import annotations

from lr_ai_exposure.image_triage import validate_triage_decision, QualityAction
from lr_ai_exposure.quality_safety import apply_quality_safety_rules


def _make_dec(action: str, flags: list[str]) -> dict[str, object]:
    raw = {
        "image_id": "IMG_1",
        "relevance_class": "KEEP_PRIMARY",
        "quality_action": action,
        "event_relation": "same",
        "test_shot_likelihood": "none",
        "accidental_likelihood": "none",
        "quality_flags": flags,
        "duplicate_of": "",
        "confidence": 0.9,
        "reason": "mock",
    }
    return validate_triage_decision(raw)


def test_safety_skip():
    """Obstruction and severe blur safety outcomes -> SKIP."""
    dec = _make_dec("APPLY", ["severe_blur"])
    safe_dec = apply_quality_safety_rules(dec)
    
    assert safe_dec.quality_action == QualityAction.SKIP
    assert "severe_blur" in safe_dec.reason


def test_safety_review():
    """Motion blur or clipped highlights -> REVIEW."""
    dec = _make_dec("APPLY", ["clipped_highlights"])
    safe_dec = apply_quality_safety_rules(dec)
    
    assert safe_dec.quality_action == QualityAction.REVIEW
    assert "clipped_highlights" in safe_dec.reason


def test_safety_pass():
    """No severe flags -> APPLY."""
    dec = _make_dec("APPLY", ["minor_noise"])
    safe_dec = apply_quality_safety_rules(dec)
    
    assert safe_dec.quality_action == QualityAction.APPLY


def test_safety_already_skip():
    """If already SKIP, keep it SKIP."""
    dec = _make_dec("SKIP", ["clipped_highlights"])
    safe_dec = apply_quality_safety_rules(dec)
    
    assert safe_dec.quality_action == QualityAction.SKIP
