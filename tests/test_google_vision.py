import os
import pytest
from pathlib import Path
from unittest import mock
import hashlib
import json

from lr_ai_exposure.job import ManifestEntry
from lr_ai_exposure.ai_judge import SinglePassError
from lr_ai_exposure.providers.google_vision import analyze_single_image_google, ProviderQuotaError

def test_analyze_single_image_google_mocked(tmp_path: Path):
    preview_bytes = b"dummy_jpeg" # Not a real JPEG, but we mock the verify step
    sha256 = hashlib.sha256(preview_bytes).hexdigest()
    
    entry = ManifestEntry(
        image_id="img1", raw_path="raw1", source_xmp_path="xmp1",
        backup_relative_path="bk1", preview_path="previews/img1.jpg",
        seq=1, extraction_status="FOUND", uuid="dummy-uuid",
        preview_bytes=len(preview_bytes), preview_sha256=sha256
    )
    
    img_path = tmp_path / "img1.jpg"
    img_path.write_bytes(preview_bytes)
    
    mock_response = mock.Mock()
    mock_response.text = json.dumps({
        "relevance_verdict": "KEEP", "quality_verdict": "KEEP", 
        "delta_ev": 1.2, "confidence": 0.9, 
        "highlight_risk": False, "shadow_risk": False, 
        "subject_rationale": "r1", "scene_rationale": "r2", 
        "batch_consistency_group": "g1", "reason": "good"
    })
    
    mock_client = mock.Mock()
    mock_client.models.generate_content.return_value = mock_response
    
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}):
        with mock.patch("google.genai.Client", return_value=mock_client):
            mock_img = mock.Mock()
            mock_img.format = "JPEG"
            mock_img_context = mock.Mock()
            mock_img_context.__enter__ = mock.Mock(return_value=mock_img)
            mock_img_context.__exit__ = mock.Mock()
            
            with mock.patch("PIL.Image.open", return_value=mock_img_context):
                decision, metadata = analyze_single_image_google(entry, img_path)
                
    assert decision.image_id == "img1"
    assert decision.delta_ev == 1.2
    assert metadata["provider"] == "google"
