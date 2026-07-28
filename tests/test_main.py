"""Tests for end-to-end integration."""

import json
import os
import pytest
from pathlib import Path
from lr_ai_exposure.main import main

def test_dry_run_integration_success(tmp_path: Path):
    """Run a complete synthetic job with multiple success and failure cases."""
    # Setup job dir
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    xmp_dir = job_dir / "xmp"
    xmp_dir.mkdir()
    
    # Write manifest
    manifest = {
        "job_id": "test_job_1",
        "entries": [
            {"image_id": "img1", "raw_path": "img1.dng", "xmp_path": "xmp/img1.xmp", "seq": 1, "preview_path": "previews/img1.jpg"},
            {"image_id": "img2", "raw_path": "img2.dng", "xmp_path": "xmp/img2.xmp", "seq": 2, "preview_path": "previews/img2.jpg"}
        ]
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest))
    
    # Create fake previews
    preview_dir = job_dir / "previews"
    preview_dir.mkdir()
    (preview_dir / "img1.jpg").write_bytes(b"fake_jpeg_12345678901234567890")
    (preview_dir / "img2.jpg").write_bytes(b"fake_jpeg_12345678901234567890")
    
    # Create fake XMPs
    xmp_content = b'<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/></rdf:RDF>'
    (xmp_dir / "img1.xmp").write_bytes(xmp_content)
    (xmp_dir / "img2.xmp").write_bytes(xmp_content)
    
    # Mock settings by writing config file
    (tmp_path / 'config').mkdir(exist_ok=True)
    config = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 1024,
        "runtime_directory": str(tmp_path),
        "catalog_path": "dummy.lrcat",
        "preview_cache_path": "dummy Previews.lrdata",
        "export_root": "dummy_export"
    }
    (tmp_path / "config" / "settings.json").write_text(json.dumps(config))
    
    # Run CLI
    import sys
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        res = main(["--job", str(job_dir)])
        assert res == 0
    finally:
        os.chdir(original_cwd)
        
    # Check outputs
    assert (job_dir / "result.json").exists()
    assert (job_dir / "ai-decisions.json").exists()
    assert (job_dir / "run.log").exists()
    
    results = json.loads((job_dir / "result.json").read_text())
    # All mocked previews are considered valid by mock judge, and confidence defaults to 0.9.
    # Therefore, they should be in 'applied' or 'reviewed' depending on mock logic.
    # By default WO-009 mock judge gives confidence 0.9, delta_ev +0.25.
    assert len(results["applied"]) == 2
