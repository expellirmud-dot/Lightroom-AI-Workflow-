"""Tests for WO-010.1 exposure judgment."""

from __future__ import annotations

import pytest

from lr_ai_exposure.exposure_judgment import (
    Action,
    ExposureClass,
    ExposureJudgmentError,
    HighlightRisk,
    SceneIntent,
    validate_exposure_decision,
)


def _base_raw() -> dict[str, object]:
    return {
        "image_id": "IMG_1",
        "subject_type": "person",
        "subject_exposure": "SLIGHTLY_UNDEREXPOSED",
        "background_exposure": "BALANCED",
        "scene_intent": "outdoor_daylight",
        "highlight_risk": "low",
        "group_id": "group1",
        "reference_image_id": "IMG_1",
        "recommended_delta_ev": 0.25,
        "action": "APPLY",
        "confidence": 0.9,
        "reason": "Needs slight boost.",
    }


def test_validate_success() -> None:
    raw = _base_raw()
    dec = validate_exposure_decision(raw)
    assert dec.image_id == "IMG_1"
    assert dec.subject_exposure == ExposureClass.SLIGHTLY_UNDEREXPOSED
    assert dec.scene_intent == SceneIntent.OUTDOOR_DAYLIGHT
    assert dec.action == Action.APPLY
    assert dec.recommended_delta_ev == 0.25


def test_validate_missing_field() -> None:
    raw = _base_raw()
    del raw["scene_intent"]
    with pytest.raises(ExposureJudgmentError, match="Missing required field"):
        validate_exposure_decision(raw)


def test_validate_invalid_enum() -> None:
    raw = _base_raw()
    raw["highlight_risk"] = "super_high"
    with pytest.raises(ExposureJudgmentError, match="Invalid enum value"):
        validate_exposure_decision(raw)


def test_validate_non_numeric() -> None:
    raw = _base_raw()
    raw["confidence"] = "high"
    with pytest.raises(ExposureJudgmentError, match="must be valid numbers"):
        validate_exposure_decision(raw)


def test_validate_non_finite() -> None:
    raw = _base_raw()
    raw["recommended_delta_ev"] = float("inf")
    with pytest.raises(ExposureJudgmentError, match="must be finite"):
        validate_exposure_decision(raw)


def test_validate_confidence_bounds() -> None:
    raw = _base_raw()
    raw["confidence"] = 1.1
    with pytest.raises(ExposureJudgmentError, match="Confidence must be in"):
        validate_exposure_decision(raw)


def test_highlight_risk_downgrade() -> None:
    """Highlight-risk downgrade to REVIEW."""
    raw = _base_raw()
    raw["highlight_risk"] = "high"
    raw["recommended_delta_ev"] = 0.5
    raw["action"] = "APPLY"
    
    dec = validate_exposure_decision(raw)
    assert dec.action == Action.REVIEW
    assert "high highlight risk" in dec.reason


def test_low_confidence_downgrade() -> None:
    """Low-confidence decisions downgrade to REVIEW."""
    raw = _base_raw()
    raw["confidence"] = 0.7
    raw["action"] = "APPLY"
    
    dec = validate_exposure_decision(raw)
    assert dec.action == Action.REVIEW
    assert "low confidence" in dec.reason


def test_delta_ev_clamp() -> None:
    """Delta EV bands and maximum clamp."""
    raw = _base_raw()
    raw["recommended_delta_ev"] = 4.0
    
    dec = validate_exposure_decision(raw, max_delta_ev=3.0)
    assert dec.recommended_delta_ev == 3.0


def test_person_priority() -> None:
    """Person priority over average frame brightness. (Implicit in values)"""
    raw = _base_raw()
    raw["subject_exposure"] = "UNDEREXPOSED"
    raw["background_exposure"] = "BALANCED"
    raw["recommended_delta_ev"] = 0.5
    
    dec = validate_exposure_decision(raw)
    assert dec.recommended_delta_ev == 0.5
    assert dec.action == Action.APPLY


def test_dark_background_intent() -> None:
    """Balanced person with intentionally dark background."""
    raw = _base_raw()
    raw["subject_exposure"] = "BALANCED"
    raw["background_exposure"] = "UNDEREXPOSED"
    raw["scene_intent"] = "night_or_low_light"
    raw["recommended_delta_ev"] = 0.0
    
    dec = validate_exposure_decision(raw)
    assert dec.recommended_delta_ev == 0.0
    assert dec.action == Action.APPLY
