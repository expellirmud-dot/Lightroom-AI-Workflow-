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
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "batch_consistency_group": "g1",
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
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.5,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "batch_consistency_group": "g1",
        "reason": "uncertain"
    }
    decision = validate_single_pass_decision(raw)
    assert decision.relevance_verdict == Verdict.REVIEW
    assert decision.quality_verdict == Verdict.REVIEW
    assert "Downgraded to REVIEW due to low confidence" in decision.reason

def test_validate_single_pass_rejects_out_of_bounds_ev():
    raw = {
        "image_id": "img1",
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 5.0, # Will be rejected
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "batch_consistency_group": "g1",
        "reason": "looks good"
    }
    with pytest.raises(SinglePassError, match="out of bounds"):
        validate_single_pass_decision(raw, max_delta_ev=3.0)

def test_validate_single_pass_force_review_on_risk():
    raw = {
        "image_id": "img1",
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 1.5,
        "confidence": 0.9,
        "highlight_risk": True,
        "shadow_risk": False,
        "subject_rationale": "person",
        "scene_rationale": "daylight",
        "batch_consistency_group": "g1",
        "reason": "risk"
    }
    decision = validate_single_pass_decision(raw)
    assert decision.quality_verdict == Verdict.REVIEW
    assert "Downgraded to REVIEW due to risk flags" in decision.reason

def test_analyze_job_single_pass():
    entries = [
        ManifestEntry("img1", "raw1", "src1", "bk1", "prev1", 1, extraction_status="FOUND"),
        ManifestEntry("img2", "raw2", "src2", "bk2", "prev2", 2, extraction_status="MISSING"),
    ]
    manifest = Manifest(job_id="job1", entries=entries)
    
    with pytest.raises(NotImplementedError, match="Vision provider integration explicitly NOT_IMPLEMENTED"):
        analyze_job_single_pass(manifest)
