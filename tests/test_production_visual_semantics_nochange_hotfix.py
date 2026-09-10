from __future__ import annotations

import json
from pathlib import Path

import pytest

from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest
import lr_ai_exposure.production_job as production


def _policy() -> dict[str, float]:
    return {
        "quantum_ev": 0.05,
        "maximum_delta_ev": 3.0,
        "minimum_exposure2012": -5.0,
        "maximum_exposure2012": 5.0,
    }


def _selection(job_id: str, source: str, ids: tuple[str, ...]) -> dict:
    return {
        "protocol_version": "2.0",
        "job_id": job_id,
        "selected_count": len(ids),
        "source_folder": source,
        "photos": [
            {
                "id_local": image_id,
                "path": f"D:/album/{image_id}.NEF",
                "uuid": f"uuid-{image_id}",
                "catalog_exposure2012": 0.0,
            }
            for image_id in ids
        ],
    }


def _manifest(job_dir: Path, job_id: str, ids: tuple[str, ...]) -> Manifest:
    entries = [
        ManifestEntry(
            image_id=image_id,
            raw_path=f"D:/album/{image_id}.NEF",
            source_xmp_path=f"D:/album/{image_id}.xmp",
            backup_relative_path=f"xmp_backups/{image_id}.xmp",
            preview_path=f"previews/{index:06d}__{image_id}.jpg",
            seq=index,
            extraction_status="FOUND",
            uuid=f"uuid-{image_id}",
            preview_bytes=100,
            preview_sha256=f"sha-{image_id}",
            preview_orientation="AB",
            source_preview_sha256=f"source-sha-{image_id}",
            source_preview_tier=1440,
        )
        for index, image_id in enumerate(ids, 1)
    ]
    manifest = Manifest(
        job_id=job_id,
        entries=entries,
        total_selected=len(ids),
        total_found=len(ids),
        total_missing=0,
        total_ambiguous=0,
        total_failed=0,
    )
    write_manifest(job_dir, manifest)
    return manifest


def _make_job(tmp_path: Path, job_id: str, ids: tuple[str, ...]) -> Path:
    job_dir = tmp_path / "runtime" / "jobs" / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "selection.json").write_text(
        json.dumps(_selection(job_id, "D:/album", ids)), encoding="utf-8"
    )
    _manifest(job_dir, job_id, ids)
    production.create_production_job_state(
        job_dir,
        job_id=job_id,
        source_folder="D:/album",
        ordered_image_ids=ids,
        policy=_policy(),
    )
    return job_dir


def test_visual_semantics_schema_matches_product_goal() -> None:
    schema = production.visual_semantics_json_schema()
    member_schema = schema["properties"]["groups"]["items"]["properties"]["members"]["items"]
    allowed_verdicts = member_schema["properties"]["verdict"]["enum"]
    assert allowed_verdicts == ["AUTO", "NO_CHANGE", "UNRESOLVED"]

    task_text = production._production_task_text(job_id="job-1", source_folder="D:/album", image_count=2)
    assert "reference_image_id" in task_text
    assert "NO_CHANGE" in task_text
    assert "AUTO" in task_text
    assert "numeric EV" in task_text
    assert "reference-free-brackets" not in task_text
    assert "target_candidate_id" not in task_text


def test_validate_visual_semantics_accepts_visual_no_change() -> None:
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-1",
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "NO_CHANGE"},
                    {"image_id": "2", "verdict": "AUTO"},
                ],
            }
        ],
        "unassigned": [],
    }
    validated = production.validate_visual_semantics(
        semantics,
        job_id="job-1",
        ordered_image_ids=("1", "2"),
    )
    assert validated["groups"][0]["members"][0]["verdict"] == "NO_CHANGE"


def test_visual_no_change_is_accounted_without_numeric_ai_authority(tmp_path: Path) -> None:
    ids = ("1", "2")
    job_dir = _make_job(tmp_path, "job-product-goal", ids)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-product-goal",
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "NO_CHANGE"},
                    {"image_id": "2", "verdict": "AUTO"},
                ],
            }
        ],
        "unassigned": [],
    }
    semantics_path = tmp_path / "semantics.json"
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    imported = production.import_visual_semantics(job_dir, semantics_path)
    assert imported["numeric_exposure_authority"] == "NONE"
    assert imported["mutation_authority"] == "NONE"

    measurements = [
        {"image_id": "1", "status": "MEASURED", "measurement": 0.50, "preview_sha256": "sha-1"},
        {"image_id": "2", "status": "MEASURED", "measurement": 0.25, "preview_sha256": "sha-2"},
    ]
    plan = production.build_production_plan(job_dir, measurements)
    by_id = {item["image_id"]: item for item in plan["items"]}

    assert by_id["1"]["pre_apply_status"] == "NO_CHANGE"
    assert by_id["1"]["validated_delta_ev"] == 0.0
    assert by_id["1"]["target_exposure2012"] == 0.0
    assert by_id["1"]["reason_code"] == "VISUAL_NO_CHANGE"

    assert by_id["2"]["pre_apply_status"] == "WILL_ADJUST"
    assert by_id["2"]["validated_delta_ev"] == 1.0
    assert by_id["2"]["target_exposure2012"] == 1.0
    assert plan["counts"] == {
        "input_count": 2,
        "will_adjust": 1,
        "no_change": 1,
        "unresolved": 0,
    }
    assert plan["numeric_exposure_authority"] == "DETERMINISTIC_PYTHON"
    assert plan["mutation_authority"] == "NONE"
