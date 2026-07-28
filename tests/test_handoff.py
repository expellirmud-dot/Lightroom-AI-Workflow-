import os
import json
import pytest
from pathlib import Path
from lr_ai_exposure.handoff import handoff_job
from tests.test_cache_extractor import dummy_lrdata # Use the fixture from earlier

def test_handoff_job(dummy_lrdata, tmp_path):
    runtime_root = tmp_path / "runtime"
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    p1 = photos_dir / "IMG_01.CR2"
    p2 = photos_dir / "IMG_02.CR2"
    p3 = photos_dir / "IMG_03.CR2"
    p1.write_text("")
    p2.write_text("")
    p3.write_text("")
    
    selection = {
        "job_id": "test_job_123",
        "photos": [
            {"id_local": 101.0, "path": str(p1.resolve())},
            {"id_local": 102.0, "path": str(p2.resolve())}, # missing root-pixel
            {"id_local": 103.0, "path": str(p3.resolve())},
        ]
    }
    selection_path = tmp_path / "selection.json"
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump(selection, f)
        
    job_id = handoff_job(str(runtime_root), dummy_lrdata, str(selection_path))
    
    job_dir = runtime_root / "jobs" / job_id
    assert job_dir.exists()
    
    manifest_path = job_dir / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["job_id"] == "test_job_123"
    assert len(manifest["entries"]) == 3
    
    e1 = manifest["entries"][0]
    assert e1["image_id"] == "101.0"
    assert e1["extraction_status"] == "FOUND"
    assert e1["preview_bytes"] > 0
    assert (job_dir / e1["preview_path"]).exists()
    
    e2 = manifest["entries"][1]
    assert e2["extraction_status"] == "MISSING"
    assert e2["preview_bytes"] == 0
    
    e3 = manifest["entries"][2]
    assert e3["extraction_status"] == "FOUND"
    assert (job_dir / e3["preview_path"]).exists()
