import json
import pytest
from pathlib import Path
from unittest import mock
from lr_ai_exposure.apply import apply_exposure_deltas
from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest

def run_stage_test(tmp_path: Path, count: int, test_name: str, inject_failure: bool = False):
    job_dir = tmp_path / f"job-{test_name}"
    job_dir.mkdir()
    
    entries = []
    photos = []
    decisions = []
    approved_ids = []
    
    pilot_root = tmp_path / f"pilot-{test_name}"
    pilot_root.mkdir()
    xmp_backups = job_dir / "xmp_backups"
    xmp_backups.mkdir()
    
    for i in range(1, count + 1):
        img_id = f"img{i}"
        approved_ids.append(img_id)
        raw_path = pilot_root / f"{img_id}.raw"
        xmp_path = pilot_root / f"{img_id}.xmp"
        raw_path.touch()
        xmp_path.write_text('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><crs:Exposure2012>0.0</crs:Exposure2012></rdf:Description></rdf:RDF></x:xmpmeta>')
        
        entries.append(ManifestEntry(
            image_id=img_id,
            uuid=f"uuid-{i}",
            source_xmp_path=str(xmp_path),
            raw_path=str(raw_path),
            backup_relative_path=f"xmp_backups/{xmp_path.name}",
            preview_path=f"previews/{img_id}.jpg",
            seq=i
        ))
        
        photos.append({
            "id_local": img_id,
            "uuid": f"uuid-{i}",
            "path": str(raw_path)
        })
        
        decisions.append(SinglePassDecision(
            image_id=img_id,
            confidence=0.9,
            action=Action.ADJUST, relevance_verdict=Verdict.KEEP,
            quality_verdict=Verdict.KEEP,
            highlight_risk=False,
            shadow_risk=False,
            delta_ev=0.5,
            subject_rationale="",
            scene_rationale="",
            scene_group_id="",
            reason=""
        ))
        
    manifest = Manifest(
        job_id=f"job-{test_name}",
        entries=entries
    )
    write_manifest(job_dir, manifest)
        
    selection_path = job_dir / "selection.json"
    selection = {
        "job_id": f"job-{test_name}",
        "photos": photos
    }
    with open(selection_path, "w") as f:
        json.dump(selection, f)
        
    config = {
        "dry_run": False,
        "apply_authorized": True,
        "approved_image_ids": approved_ids,
        "approved_pilot_root": str(pilot_root),
        "maximum_delta_ev": 3.0,
        "minimum_apply_confidence": 0.8
    }
    
    with mock.patch("lr_ai_exposure.apply.execute_apply_transaction") as mock_execute:
        def side_effect(xmp, ev, bdir, dry_run):
            if inject_failure and xmp.name == "img2.xmp":
                return {"status": "FAILED_BEFORE_REPLACE", "message": "injected failure"}
            return {"status": "APPLIED_VERIFIED", "message": "ok"}
        mock_execute.side_effect = side_effect
        
        results = apply_exposure_deltas(job_dir, selection_path, decisions, config)
        
    evidence_file = job_dir / "apply-evidence.json"
    ev_data = json.loads(evidence_file.read_text())
    
    return results, ev_data, mock_execute

def test_stage_a(tmp_path: Path):
    results, ev_data, mock_execute = run_stage_test(tmp_path, 5, "stage-a", inject_failure=False)
    assert results["applied"] == 5
    assert results["errors"] == 0
    assert len(ev_data["results"]) == 5
    assert mock_execute.call_count == 5

def test_stage_b(tmp_path: Path):
    # Pass 1
    results1, ev_data1, mock_execute1 = run_stage_test(tmp_path, 20, "stage-b", inject_failure=True)
    assert results1["applied"] == 19
    assert results1["errors"] == 1
    assert len(ev_data1["results"]) == 20
    assert mock_execute1.call_count == 20
    
    # Pass 2 - Resume
    job_dir = tmp_path / "job-stage-b"
    selection_path = job_dir / "selection.json"
    manifest = Manifest(job_id="job-stage-b", entries=[]) # doesn't matter for resume mock
    decisions = []
    for i in range(1, 21):
        decisions.append(SinglePassDecision(
            image_id=f"img{i}", confidence=0.9, action=Action.ADJUST, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP,
            highlight_risk=False, shadow_risk=False, delta_ev=0.5,
            subject_rationale="", scene_rationale="", scene_group_id="", reason=""
        ))
    config = {
        "dry_run": False, "apply_authorized": True,
        "approved_image_ids": [f"img{i}" for i in range(1, 21)],
        "approved_pilot_root": str(tmp_path / "pilot-stage-b"),
        "maximum_delta_ev": 3.0, "minimum_apply_confidence": 0.8
    }
    
    with mock.patch("lr_ai_exposure.apply.execute_apply_transaction") as mock_execute2:
        results2 = apply_exposure_deltas(job_dir, selection_path, decisions, config)
        
    assert results2["applied"] == 19
    assert results2["errors"] == 1
    assert mock_execute2.call_count == 0

def test_stage_c(tmp_path: Path):
    results, ev_data, mock_execute = run_stage_test(tmp_path, 50, "stage-c", inject_failure=False)
    assert results["applied"] == 50
    assert results["errors"] == 0
    assert len(ev_data["results"]) == 50
    assert mock_execute.call_count == 50
