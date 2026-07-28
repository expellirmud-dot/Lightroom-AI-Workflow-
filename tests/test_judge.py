"""Tests for WO-009 mock judge and decision validation."""

from __future__ import annotations

import pytest

from lr_ai_exposure.job import Manifest, ManifestEntry
from lr_ai_exposure.judge import (
    DecisionError,
    clamp_ev,
    parse_and_validate_decision,
    process_mock_decisions,
    validate_decision_batch,
)


def _manifest(entries: int = 2) -> Manifest:
    return Manifest(
        job_id="test",
        entries=[
            ManifestEntry(
                image_id=f"IMG_{i}",
                raw_path=f"previews/IMG_{i}.NEF",
                xmp_path=f"xmp/IMG_{i}.xmp",
                preview_path=f"previews/IMG_{i}.jpg",
                seq=i,
            )
            for i in range(1, entries + 1)
        ],
    )


def test_clamp_ev():
    assert clamp_ev(1.5, 2.0) == 1.5
    assert clamp_ev(2.5, 2.0) == 2.0
    assert clamp_ev(-2.5, 2.0) == -2.0
    assert clamp_ev(0.0, 2.0) == 0.0

    with pytest.raises(ValueError):
        clamp_ev(1.0, 0.0)
    with pytest.raises(ValueError):
        clamp_ev(1.0, -1.0)


def test_parse_and_validate_decision_valid():
    raw = {"image_id": "IMG_1", "delta_ev": 1.5, "confidence": 0.9}
    dec = parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)
    assert dec.image_id == "IMG_1"
    assert dec.delta_ev == 1.5
    assert dec.confidence == 0.9
    assert dec.reject is False


def test_parse_and_validate_decision_missing_fields():
    with pytest.raises(DecisionError, match="Missing required field"):
        parse_and_validate_decision({"image_id": "IMG_1", "delta_ev": 1.5}, "IMG_1", 2.0, 0.8)


def test_parse_and_validate_decision_id_mismatch():
    raw = {"image_id": "IMG_2", "delta_ev": 1.5, "confidence": 0.9}
    with pytest.raises(DecisionError, match="Image ID mismatch"):
        parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)


def test_parse_and_validate_decision_non_numeric():
    raw = {"image_id": "IMG_1", "delta_ev": "abc", "confidence": 0.9}
    with pytest.raises(DecisionError, match="must be numeric"):
        parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)


def test_parse_and_validate_decision_invalid_confidence():
    raw = {"image_id": "IMG_1", "delta_ev": 1.5, "confidence": 1.5}
    with pytest.raises(DecisionError, match="must be in"):
        parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)


def test_parse_and_validate_decision_auto_reject():
    raw = {"image_id": "IMG_1", "delta_ev": 1.5, "confidence": 0.7}
    dec = parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)
    assert dec.reject is True
    assert "below minimum" in dec.reason


def test_parse_and_validate_decision_clamping():
    raw = {"image_id": "IMG_1", "delta_ev": 3.0, "confidence": 0.9}
    dec = parse_and_validate_decision(raw, "IMG_1", 2.0, 0.8)
    assert dec.delta_ev == 2.0
    assert "Clamped delta_ev" in dec.reason


def test_process_mock_decisions():
    m = _manifest(2)
    decisions = process_mock_decisions(m)
    assert len(decisions) == 2
    assert decisions[0].image_id == "IMG_1"
    assert decisions[0].delta_ev == 0.0
    assert decisions[0].confidence == 0.99
    assert decisions[0].reject is False
    assert decisions[1].image_id == "IMG_2"


def test_validate_decision_batch_success():
    m = _manifest(2)
    raw = [
        {"image_id": "IMG_2", "delta_ev": 1.0, "confidence": 0.9},
        {"image_id": "IMG_1", "delta_ev": -1.0, "confidence": 0.9},
    ]
    # Should re-order based on manifest
    validated = validate_decision_batch(raw, m, 2.0, 0.8)
    assert len(validated) == 2
    assert validated[0].image_id == "IMG_1"
    assert validated[0].delta_ev == -1.0
    assert validated[1].image_id == "IMG_2"
    assert validated[1].delta_ev == 1.0


def test_validate_decision_batch_count_mismatch():
    m = _manifest(2)
    raw = [
        {"image_id": "IMG_1", "delta_ev": 1.0, "confidence": 0.9},
    ]
    with pytest.raises(DecisionError, match="Decision count mismatch"):
        validate_decision_batch(raw, m, 2.0, 0.8)


def test_validate_decision_batch_duplicates():
    m = _manifest(2)
    raw = [
        {"image_id": "IMG_1", "delta_ev": 1.0, "confidence": 0.9},
        {"image_id": "IMG_1", "delta_ev": 2.0, "confidence": 0.9},
    ]
    with pytest.raises(DecisionError, match="Duplicate decision"):
        validate_decision_batch(raw, m, 2.0, 0.8)


def test_validate_decision_batch_unknown_id():
    m = _manifest(1)
    raw = [
        {"image_id": "IMG_X", "delta_ev": 1.0, "confidence": 0.9},
    ]
    with pytest.raises(DecisionError, match="Missing decision for manifest"):
        validate_decision_batch(raw, m, 2.0, 0.8)


def test_validate_decision_batch_not_list():
    m = _manifest(1)
    with pytest.raises(DecisionError, match="must be a list"):
        validate_decision_batch({"image_id": "IMG_1"}, m, 2.0, 0.8)


def test_validate_decision_batch_not_dict_items():
    m = _manifest(1)
    with pytest.raises(DecisionError, match="must contain dictionary"):
        validate_decision_batch(["IMG_1"], m, 2.0, 0.8)
