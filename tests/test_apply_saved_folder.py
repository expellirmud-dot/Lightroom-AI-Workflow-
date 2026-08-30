from __future__ import annotations

import json
from pathlib import Path

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.apply import apply_exposure_deltas
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest


def _xmp() -> str:
    return (
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )


def test_non_found_preview_and_zero_delta_settle_without_mutation(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    source.mkdir()
    (source / "A.NEF").touch()
    (source / "B.NEF").touch()
    xmp = source / "A.xmp"
    xmp.write_text(_xmp(), encoding="utf-8")
    before = xmp.read_bytes()

    job_dir = tmp_path / "runtime" / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
    manifest = Manifest(
        job_id="job-1",
        total_selected=2,
        total_found=1,
        total_missing=1,
        entries=[
            ManifestEntry(
                "1", str((source / "A.NEF").resolve()), str(xmp.resolve()),
                "xmp_backups/A.xmp", "previews/A.jpg", 1, "FOUND", "uuid-1", 1, "h1"
            ),
            ManifestEntry(
                "2", str((source / "B.NEF").resolve()), str((source / "B.xmp").resolve()),
                "xmp_backups/B.xmp", "previews/B.jpg", 2, "MISSING", "uuid-2", 0, None
            ),
        ],
    )
    write_manifest(job_dir, manifest)
    selection = {
        "job_id": "job-1",
        "photos": [
            {"id_local": "1", "path": str((source / "A.NEF").resolve()), "uuid": "uuid-1"},
            {"id_local": "2", "path": str((source / "B.NEF").resolve()), "uuid": "uuid-2"},
        ],
    }
    selection_path = job_dir / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    decision = SinglePassDecision(
        image_id="1",
        action=Action.ADJUST, relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="subject",
        scene_rationale="scene",
        scene_group_id="g",
        reason="no change",
    )

    results = apply_exposure_deltas(
        job_dir,
        selection_path,
        [decision],
        {
            "dry_run": False,
            "apply_authorized": True,
            "approved_image_ids": ["1"],
            "approved_pilot_root": str(source),
            "maximum_delta_ev": 3.0,
            "minimum_apply_confidence": 0.85,
        },
    )

    assert results["applied"] == 0
    assert results["skipped"] == 2
    assert results["errors"] == 0
    assert xmp.read_bytes() == before
    evidence = json.loads((job_dir / "apply-evidence.json").read_text(encoding="utf-8"))
    statuses = {item["image_id"]: item["status"] for item in evidence["results"]}
    assert statuses == {
        "1": "SKIPPED_NO_CHANGE",
        "2": "SKIPPED_PREVIEW_UNAVAILABLE",
    }
