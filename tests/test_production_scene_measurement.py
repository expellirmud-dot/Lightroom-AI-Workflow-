from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest
import lr_ai_exposure.production_job as production


def _jpeg(gray: int) -> bytes:
    image = Image.new("RGB", (320, 240), (gray, gray, gray))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=94)
    return out.getvalue()


def _ready_two_image_job(tmp_path: Path) -> Path:
    job_dir = tmp_path / "runtime" / "jobs" / "job-scene"
    preview_dir = job_dir / "previews"
    preview_dir.mkdir(parents=True)
    payloads = {"1": _jpeg(120), "2": _jpeg(150)}
    photos = []
    entries = []
    for seq, image_id in enumerate(("1", "2"), start=1):
        preview = preview_dir / f"{seq:06d}__{image_id}.jpg"
        preview.write_bytes(payloads[image_id])
        sha = hashlib.sha256(payloads[image_id]).hexdigest()
        photos.append({
            "id_local": image_id,
            "path": f"D:/album/{image_id}.NEF",
            "uuid": f"uuid-{image_id}",
            "catalog_exposure2012": 0.0,
        })
        entries.append(ManifestEntry(
            image_id=image_id,
            raw_path=f"D:/album/{image_id}.NEF",
            source_xmp_path=f"D:/album/{image_id}.xmp",
            backup_relative_path=f"xmp_backups/{image_id}.xmp",
            preview_path=f"previews/{seq:06d}__{image_id}.jpg",
            seq=seq,
            extraction_status="FOUND",
            uuid=f"uuid-{image_id}",
            preview_bytes=len(payloads[image_id]),
            preview_sha256=sha,
            preview_orientation="AB",
            source_preview_sha256=sha,
            source_preview_tier=1440,
        ))
    (job_dir / "selection.json").write_text(json.dumps({
        "protocol_version": "2.0",
        "job_id": "job-scene",
        "selected_count": 2,
        "source_folder": "D:/album",
        "photos": photos,
    }), encoding="utf-8")
    write_manifest(job_dir, Manifest(
        job_id="job-scene",
        entries=entries,
        total_selected=2,
        total_found=2,
    ))
    production.create_production_job_state(
        job_dir,
        job_id="job-scene",
        source_folder="D:/album",
        ordered_image_ids=("1", "2"),
        policy={
            "quantum_ev": 0.05,
            "maximum_delta_ev": 3.0,
            "minimum_exposure2012": -5.0,
            "maximum_exposure2012": 5.0,
        },
    )
    semantics = tmp_path / "semantics.json"
    semantics.write_text(json.dumps({
        "protocol_version": "2.0",
        "job_id": "job-scene",
        "groups": [{
            "group_id": "g1",
            "status": "REFERENCE_SELECTED",
            "reference_image_id": "2",
            "members": [
                {"image_id": "1", "verdict": "AUTO"},
                {"image_id": "2", "verdict": "AUTO"},
            ],
        }],
        "unassigned": [],
    }), encoding="utf-8")
    production.import_visual_semantics(job_dir, semantics)
    return job_dir


def test_no_face_scene_measurement_drives_reference_plan_and_fresh_verification(tmp_path: Path) -> None:
    job_dir = _ready_two_image_job(tmp_path)

    measurements = production.build_production_baseline_measurements(job_dir, meter=None)
    assert [item["status"] for item in measurements["items"]] == ["MEASURED", "MEASURED"]
    assert measurements["items"][0]["measurement"] < measurements["items"][1]["measurement"]

    evidence = json.loads((job_dir / "measurement-rois.json").read_text(encoding="utf-8"))
    assert [item["measurement_strategy"] for item in evidence["items"]] == [
        "ROBUST_SCENE_LUMINANCE",
        "ROBUST_SCENE_LUMINANCE",
    ]
    assert all("face_rois" not in item for item in evidence["items"])

    plan = production.build_production_plan(job_dir, measurements["items"])
    by_id = {item["image_id"]: item for item in plan["items"]}
    assert by_id["1"]["pre_apply_status"] == "WILL_ADJUST"
    assert by_id["1"]["validated_delta_ev"] > 0
    assert by_id["1"]["reason_code"] == "DETERMINISTIC_SCENE_REFERENCE_MATCH"
    assert by_id["2"]["pre_apply_status"] == "NO_CHANGE"

    fresh = tmp_path / "fresh.jpg"
    fresh.write_bytes(_jpeg(135))
    result = production.measure_production_fresh_previews(
        job_dir,
        preview_paths={"1": fresh},
        expected_image_ids=("1",),
    )
    assert result[0]["measurement_kind"] == "ROBUST_SCENE_LUMINANCE"
    assert result[0]["observed_measurement"] > measurements["items"][0]["measurement"]
