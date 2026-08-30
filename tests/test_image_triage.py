"""Tests for WO-010.2 image relevance triage."""

from __future__ import annotations

import pytest

from lr_ai_exposure.image_triage import (
    Likelihood,
    QualityAction,
    RelevanceClass,
    TriageError,
    validate_triage_decision,
)


def _base_raw() -> dict[str, object]:
    return {
        "image_id": "IMG_1",
        "relevance_class": "KEEP_PRIMARY",
        "quality_action": "APPLY",
        "event_relation": "same_event",
        "test_shot_likelihood": "none",
        "accidental_likelihood": "none",
        "quality_flags": [],
        "duplicate_of": "",
        "confidence": 0.9,
        "reason": "Primary subject clear.",
    }


def test_validate_success() -> None:
    raw = _base_raw()
    dec = validate_triage_decision(raw)
    assert dec.image_id == "IMG_1"
    assert dec.relevance_class == RelevanceClass.KEEP_PRIMARY
    assert dec.quality_action == QualityAction.APPLY


def test_validate_missing_field() -> None:
    raw = _base_raw()
    del raw["test_shot_likelihood"]
    with pytest.raises(TriageError, match="Missing required field"):
        validate_triage_decision(raw)


def test_validate_invalid_enum() -> None:
    raw = _base_raw()
    raw["relevance_class"] = "DELETE_NOW"
    with pytest.raises(TriageError, match="Invalid enum value"):
        validate_triage_decision(raw)


def test_low_confidence_downgrade() -> None:
    """Low-confidence downgrade to REVIEW."""
    raw = _base_raw()
    raw["confidence"] = 0.6

    dec = validate_triage_decision(raw)
    assert dec.relevance_class == RelevanceClass.REVIEW
    assert dec.quality_action == QualityAction.REVIEW
    assert "low confidence" in dec.reason


def test_ambiguous_test_shot() -> None:
    """Test-shot evidence requiring multiple indicators (downgrade to REVIEW if ambiguous)."""
    raw = _base_raw()
    raw["relevance_class"] = "SUGGEST_REJECT_TEST_SHOT"
    raw["test_shot_likelihood"] = "low"  # ambiguous evidence

    dec = validate_triage_decision(raw)
    assert dec.relevance_class == RelevanceClass.REVIEW
    assert "ambiguous test shot evidence" in dec.reason


def test_supporting_detail_image() -> None:
    """Supporting and detail image classification."""
    raw = _base_raw()
    raw["relevance_class"] = "KEEP_SUPPORTING"

    dec = validate_triage_decision(raw)
    assert dec.relevance_class == RelevanceClass.KEEP_SUPPORTING


def test_candid_vs_accidental() -> None:
    """Relevant candid versus accidental image distinction."""
    raw1 = _base_raw()
    raw1["relevance_class"] = "KEEP_CANDID"
    raw1["accidental_likelihood"] = "low"

    dec1 = validate_triage_decision(raw1)
    assert dec1.relevance_class == RelevanceClass.KEEP_CANDID

    raw2 = _base_raw()
    raw2["relevance_class"] = "SUGGEST_REJECT_ACCIDENTAL"
    raw2["accidental_likelihood"] = "high"

    dec2 = validate_triage_decision(raw2)
    assert dec2.relevance_class == RelevanceClass.SUGGEST_REJECT_ACCIDENTAL


def test_irrelevant_image() -> None:
    """Irrelevant-image classification with batch context."""
    raw = _base_raw()
    raw["relevance_class"] = "SUGGEST_REJECT_IRRELEVANT"
    raw["event_relation"] = "unrelated_scene"

    dec = validate_triage_decision(raw)
    assert dec.relevance_class == RelevanceClass.SUGGEST_REJECT_IRRELEVANT


def test_duplicate_suggestion() -> None:
    """Duplicate suggestion without deletion behavior."""
    raw = _base_raw()
    raw["relevance_class"] = "SUGGEST_REJECT_DUPLICATE"
    raw["duplicate_of"] = "IMG_0"

    dec = validate_triage_decision(raw)
    assert dec.relevance_class == RelevanceClass.SUGGEST_REJECT_DUPLICATE
    assert dec.duplicate_of == "IMG_0"
