import json
import hashlib
from pathlib import Path
import pytest

from lr_ai_exposure.job import ManifestEntry
from lr_ai_exposure.ai_judge import SinglePassError
from lr_ai_exposure.providers.manual_app import analyze_single_image_manual_app

@pytest.fixture
def dummy_image_file(tmp_path: Path) -> Path:
    img = tmp_path / "test.jpg"
    img.write_bytes(b"dummy")
    return img

@pytest.fixture
def dummy_response_file(tmp_path: Path) -> Path:
    resp = tmp_path / "resp.json"
    resp.write_text(json.dumps({
        "image_id": "123.0",
        "action": "ADJUST", "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 0.5,
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "ok",
        "scene_rationale": "ok",
        "scene_group_id": "group1",
        "reason": "ok"
    }))
    return resp

@pytest.fixture
def dummy_entry() -> ManifestEntry:
    return ManifestEntry(
        image_id="123.0",
        raw_path="a.cr2",
        source_xmp_path="a.xmp",
        backup_relative_path="bk_a.xmp",
        preview_path="test.jpg",
        seq=1,
        extraction_status="FOUND",
        uuid="uuid-1",
        preview_bytes=5,
        preview_sha256=hashlib.sha256(b"dummy").hexdigest()
    )

def test_manual_app_missing_preview(dummy_entry, tmp_path, dummy_response_file):
    with pytest.raises(SinglePassError, match="Preview not found"):
        analyze_single_image_manual_app(dummy_entry, tmp_path / "nope.jpg", dummy_response_file)

import dataclasses

def test_manual_app_byte_mismatch(dummy_entry, dummy_image_file, dummy_response_file):
    dummy_entry = dataclasses.replace(dummy_entry, preview_bytes=10)
    with pytest.raises(SinglePassError, match="Byte size mismatch"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, dummy_response_file)

def test_manual_app_sha_mismatch(dummy_entry, dummy_image_file, dummy_response_file):
    dummy_entry = dataclasses.replace(dummy_entry, preview_sha256="nope")
    with pytest.raises(SinglePassError, match="SHA-256 mismatch"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, dummy_response_file)

def test_manual_app_missing_response_file(dummy_entry, dummy_image_file, tmp_path):
    with pytest.raises(SinglePassError, match="Manual response file not found"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, tmp_path / "nope.json")

def test_manual_app_malformed_json(dummy_entry, dummy_image_file, tmp_path):
    resp = tmp_path / "bad.json"
    resp.write_text("{bad")
    with pytest.raises(SinglePassError, match="Failed to parse manual response file"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, resp)

def test_manual_app_wrong_image_id(dummy_entry, dummy_image_file, tmp_path):
    resp = tmp_path / "bad_id.json"
    resp.write_text(json.dumps({"image_id": "456.0"}))
    with pytest.raises(SinglePassError, match="image_id mismatch"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, resp)

def test_manual_app_missing_required_fields(dummy_entry, dummy_image_file, tmp_path):
    resp = tmp_path / "missing.json"
    resp.write_text(json.dumps({"image_id": "123.0"})) # missing all other fields
    with pytest.raises(SinglePassError, match="validation error"):
        analyze_single_image_manual_app(dummy_entry, dummy_image_file, resp)

def test_manual_app_valid(dummy_entry, dummy_image_file, dummy_response_file):
    decision, metadata = analyze_single_image_manual_app(dummy_entry, dummy_image_file, dummy_response_file)
    assert decision.image_id == "123.0"
    assert decision.delta_ev == 0.5
    assert metadata["provider"] == "manual_app"
    assert "JPEG_IDENTITY_VERIFIED" in metadata["markers"]
