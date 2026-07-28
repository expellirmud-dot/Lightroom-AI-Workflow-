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
    
    mock_response = mock.Mock()
    mock_response.text = '{"image_id": "img1", "relevance_verdict": "KEEP", "quality_verdict": "KEEP", "delta_ev": 1.2, "confidence": 0.9, "highlight_risk": false, "shadow_risk": false, "subject_rationale": "r1", "scene_rationale": "r2", "batch_consistency_group": "g1", "reason": "good"}'
    
    mock_client = mock.Mock()
    mock_client.models.generate_content.return_value = mock_response
    
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        with mock.patch("google.genai.Client", return_value=mock_client):
            decisions = analyze_job_single_pass(manifest, tmp_path)
            
    assert len(decisions) == 1
    assert decisions[0].image_id == "img1"
    assert decisions[0].delta_ev == 1.2

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
def test_analyze_job_single_pass_integration(tmp_path: Path):
    import shutil
    
    real_jpg = Path("scratch/extracted_preview.jpg")
    if not real_jpg.exists():
        pytest.skip("scratch/extracted_preview.jpg not found")
        
    entries = [
        ManifestEntry("img_real", "raw1", "src1", "bk1", "previews/img1.jpg", 1, extraction_status="FOUND"),
    ]
    manifest = Manifest(job_id="job_real", entries=entries)
    
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()
    shutil.copy2(real_jpg, previews_dir / "img1.jpg")
    
    try:
        decisions = analyze_job_single_pass(manifest, tmp_path)
    except SinglePassError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            pytest.skip(f"Skipping due to Gemini API rate limit: {e}")
        raise
        
    assert len(decisions) == 1
    assert decisions[0].image_id == "img_real"
    assert hasattr(decisions[0], "delta_ev")
    assert isinstance(decisions[0].delta_ev, float)
