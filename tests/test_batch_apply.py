import json
import pytest
from pathlib import Path
from unittest import mock
from lr_ai_exposure.apply import apply_exposure_deltas
from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.job import Manifest, ManifestEntry

def test_apply_checkpoint_resume_and_isolation(tmp_path: Path):
    job_dir = tmp_path / "job-123"
    job_dir.mkdir()

    # Create 3 images: img1, img2, img3
    entries = []
    photos = []
    decisions = []

    pilot_root = tmp_path / "pilot"
    pilot_root.mkdir()
    xmp_backups = job_dir / "xmp_backups"
    xmp_backups.mkdir()

    for i in range(1, 4):
        img_id = f"img{i}"
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
        job_id="job-123",
        entries=entries
    )
    from lr_ai_exposure.job import write_manifest
    write_manifest(job_dir, manifest)

    selection_path = job_dir / "selection.json"
    selection = {
        "job_id": "job-123",
        "photos": photos
    }
    with open(selection_path, "w") as f:
        json.dump(selection, f)

    config = {
        "dry_run": False,
        "apply_authorized": True,
        "approved_image_ids": ["img1", "img2", "img3"],
        "approved_pilot_root": str(pilot_root),
        "maximum_delta_ev": 3.0,
        "minimum_apply_confidence": 0.8
    }

    # Run 1: img2 fails non-fatally before replace
    with mock.patch("lr_ai_exposure.apply.execute_apply_transaction") as mock_execute:
        # img1 succeeds, img2 fails, img3 succeeds
        def side_effect(xmp, ev, bdir, dry_run):
            if xmp.name == "img2.xmp":
                return {"status": "FAILED_BEFORE_REPLACE", "message": "injected failure"}
            return {"status": "APPLIED_VERIFIED", "message": "ok"}
        mock_execute.side_effect = side_effect

        results1 = apply_exposure_deltas(job_dir, selection_path, decisions, config)

    assert results1["applied"] == 2
    assert results1["errors"] == 1
    assert mock_execute.call_count == 3

    # Verify checkpoint
    evidence_file = job_dir / "apply-evidence.json"
    assert evidence_file.exists()
    ev1 = json.loads(evidence_file.read_text())
    assert len(ev1["results"]) == 3

    # Run 2: Resume, should not call execute_apply_transaction at all
    with mock.patch("lr_ai_exposure.apply.execute_apply_transaction") as mock_execute2:
        results2 = apply_exposure_deltas(job_dir, selection_path, decisions, config)

    assert results2["applied"] == 2
    assert results2["errors"] == 1
    assert mock_execute2.call_count == 0  # No repeated processing!
