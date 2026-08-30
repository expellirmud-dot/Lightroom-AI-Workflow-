import pytest
from lr_ai_exposure.ai_judge import (
    Verdict,
    SinglePassError,
    validate_single_pass_decision,
    analyze_job_single_pass,
)
from lr_ai_exposure.job import Manifest, ManifestEntry

def test_validate_single_pass_valid():
    raw = {
        "image_id": "img1",
        "action": "ADJUST", "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "scene_group_id": "g1",
        "reason": "looks good"
    }
    decision = validate_single_pass_decision(raw)
    assert decision.image_id == "img1"
    assert decision.relevance_verdict == Verdict.KEEP
    assert decision.delta_ev == 1.5
    assert decision.confidence == 0.9

def test_validate_single_pass_low_confidence_downgrades_to_review():
    raw = {
        "image_id": "img1",
        "action": "ADJUST", "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.5,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "scene_group_id": "g1",
        "reason": "uncertain"
    }
    decision = validate_single_pass_decision(raw)
    assert decision.relevance_verdict == Verdict.REVIEW
    assert decision.quality_verdict == Verdict.REVIEW
    assert "Downgraded to REVIEW due to low confidence" in decision.reason

def test_validate_single_pass_rejects_out_of_bounds_ev():
    raw = {
        "image_id": "img1",
        "action": "ADJUST", "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 5.0, # Will be rejected
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "scene_group_id": "g1",
        "reason": "looks good"
    }
    with pytest.raises(SinglePassError, match="out of bounds"):
        validate_single_pass_decision(raw, max_delta_ev=3.0)

def test_validate_single_pass_force_review_on_risk():
    raw = {
        "image_id": "img1",
        "action": "ADJUST", "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.9,
        "highlight_risk": True,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "scene_group_id": "g1",
        "reason": "risk"
    }
    decision = validate_single_pass_decision(raw)
    assert decision.quality_verdict == Verdict.REVIEW
    assert "Downgraded to REVIEW due to risk flags" in decision.reason

import os
from unittest import mock
from pathlib import Path

def test_analyze_job_single_pass_mocked(tmp_path: Path):
    entries = [
        ManifestEntry("img1", "raw1", "src1", "bk1", "previews/img1.jpg", 1, extraction_status="FOUND"),
        ManifestEntry("img2", "raw2", "src2", "bk2", "previews/img2.jpg", 2, extraction_status="MISSING"),
    ]
    manifest = Manifest(job_id="job1", entries=entries)

    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()
    (previews_dir / "img1.jpg").write_bytes(b"dummy_jpeg_bytes")

    from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
    decision = SinglePassDecision(
        image_id="img1", action=Action.ADJUST, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP,
        delta_ev=1.2, confidence=0.9, highlight_risk=False, shadow_risk=False,
        subject_rationale="r1", scene_rationale="r2", scene_group_id="g1", reason="good"
    )

    with mock.patch("lr_ai_exposure.providers.google_vision.analyze_single_image_google", return_value=(decision, {"provider": "google"})):
        decisions = analyze_job_single_pass(manifest, tmp_path, {"ai_provider": "google", "ai_model": "gemini-2.5-pro"})

    assert len(decisions) == 1
    assert decisions[0].image_id == "img1"
    assert decisions[0].delta_ev == 1.2

@pytest.mark.skip(reason="Integration test moved to test_google_vision.py")
def test_analyze_job_single_pass_integration(tmp_path: Path):
    pass
