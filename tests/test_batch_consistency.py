"""Tests for WO-010.1 batch consistency review."""

from __future__ import annotations

import pytest

from lr_ai_exposure.batch_consistency import group_decisions, review_batch_consistency, select_reference_frame
from lr_ai_exposure.exposure_judgment import validate_exposure_decision


def _make_dec(image_id: str, group_id: str, subj_exp: str, hl_risk: str, conf: float, delta: float) -> dict[str, object]:
    raw = {
        "image_id": image_id,
        "subject_type": "person",
        "subject_exposure": subj_exp,
        "background_exposure": "BALANCED",
        "scene_intent": "outdoor_daylight",
        "highlight_risk": hl_risk,
        "group_id": group_id,
        "reference_image_id": "dummy",
        "recommended_delta_ev": delta,
        "action": "APPLY",
        "confidence": conf,
        "reason": "mock",
    }
    return validate_exposure_decision(raw)


def test_group_decisions():
    """Separation of materially different lighting groups."""
    d1 = _make_dec("A", "g1", "BALANCED", "low", 0.9, 0.0)
    d2 = _make_dec("B", "g2", "BALANCED", "low", 0.9, 0.0)
    d3 = _make_dec("C", "g1", "BALANCED", "low", 0.9, 0.0)

    groups = group_decisions([d1, d2, d3])
    assert len(groups) == 2
    assert len(groups["g1"]) == 2
    assert len(groups["g2"]) == 1


def test_select_reference_frame():
    """Reference-frame selection is deterministic."""
    # d1: balanced, low risk, conf 0.9 -> best
    d1 = _make_dec("A", "g1", "BALANCED", "low", 0.9, 0.0)
    # d2: underexposed -> lower subj score
    d2 = _make_dec("B", "g1", "UNDEREXPOSED", "low", 0.9, 0.5)
    # d3: balanced but high risk
    d3 = _make_dec("C", "g1", "BALANCED", "high", 0.9, 0.0)
    # d4: balanced, low risk, but lower conf
    d4 = _make_dec("D", "g1", "BALANCED", "low", 0.8, 0.0)

    ref = select_reference_frame([d2, d3, d4, d1])
    assert ref is not None
    assert ref.image_id == "A"


def test_select_reference_frame_tie_breaker():
    """Ties broken by confidence then image_id alphabetically."""
    d1 = _make_dec("B", "g1", "BALANCED", "low", 0.9, 0.0)
    d2 = _make_dec("A", "g1", "BALANCED", "low", 0.9, 0.0)

    ref = select_reference_frame([d1, d2])
    assert ref is not None
    assert ref.image_id == "A"


def test_adjacent_exposure_jump_detection():
    """Flag large adjacent exposure jumps for review."""
    d1 = _make_dec("A", "g1", "BALANCED", "low", 0.9, 0.0)
    d2 = _make_dec("B", "g1", "BALANCED", "low", 0.9, 0.6)  # jump of 0.6
    d3 = _make_dec("C", "g2", "BALANCED", "low", 0.9, 1.5)  # jump of 0.9, but different group!

    results = review_batch_consistency([d1, d2, d3], max_adjacent_jump_ev=0.5)

    assert len(results) == 3
    assert not results[0].flagged_jump

    # B is in same group and jumps 0.6 > 0.5
    assert results[1].flagged_jump
    assert results[1].final_action == "REVIEW"
    assert "Flagged adjacent jump" in results[1].consistency_reason

    # C is in different group, so the jump from B to C is ignored
    assert not results[2].flagged_jump
    assert results[2].final_action == "APPLY"
