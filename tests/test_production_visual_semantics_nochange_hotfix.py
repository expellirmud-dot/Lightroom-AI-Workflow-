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


def test_visual_semantics_schema_and_task_forbid_direct_no_change() -> None:
    """Schema and generated task must forbid direct visual NO_CHANGE verdict."""
    schema = production.visual_semantics_json_schema()
    member_schema = schema["properties"]["groups"]["items"]["properties"]["members"]["items"]
    allowed_verdicts = member_schema["properties"]["verdict"]["enum"]

    # Visual Judge must only be allowed to supply AUTO or UNRESOLVED
    assert "NO_CHANGE" not in allowed_verdicts, "NO_CHANGE must not be an allowed visual member verdict"
    assert allowed_verdicts == ["AUTO", "UNRESOLVED"]

    # Task text must guide the AI to use AUTO for assignable members and must not instruct NO_CHANGE
    task_text = production._production_task_text(job_id="job-1", source_folder="D:/album", image_count=2)
    assert "NO_CHANGE" not in task_text, "AI_TASK.md must not instruct or permit NO_CHANGE verdict"
    assert "mark assignable group members `AUTO`" in task_text or "mark assignable group members AUTO" in task_text


def test_validate_visual_semantics_rejects_direct_visual_no_change() -> None:
    """Validator must reject any visual semantics payload containing verdict NO_CHANGE."""
    semantics_with_no_change = {
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
    with pytest.raises(production.ProductionJobError, match="verdict is invalid"):
        production.validate_visual_semantics(
            semantics_with_no_change,
            job_id="job-1",
            ordered_image_ids=("1", "2"),
        )


def test_visual_no_change_cannot_bypass_actionable_deterministic_exposure(tmp_path: Path) -> None:
    """A member image must not be able to bypass deterministic measurement via visual NO_CHANGE.

    Under the repaired model:
    - Member images use 'AUTO' to declare eligibility for deterministic comparison.
    - An image requiring adjustment (e.g. measurement 0.25 vs ref 0.50 -> +1.0 EV delta)
      becomes WILL_ADJUST.
    - Python is the sole authority that resolves delta == 0.0 to NO_CHANGE
      (reason: DETERMINISTIC_ZERO_DELTA).
    - Any attempt to import or evaluate visual NO_CHANGE fails closed.
    """
    ids = ("1", "2")
    job_dir = _make_job(tmp_path, "job-actionable", ids)

    # 1. Verify that a payload with direct NO_CHANGE cannot be imported
    bad_semantics = {
        "protocol_version": "2.0",
        "job_id": "job-actionable",
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "AUTO"},
                    {"image_id": "2", "verdict": "NO_CHANGE"},  # bypass attempt!
                ],
            }
        ],
        "unassigned": [],
    }
    bad_sem_path = tmp_path / "bad_semantics.json"
    bad_sem_path.write_text(json.dumps(bad_semantics), encoding="utf-8")

    with pytest.raises(production.ProductionJobError, match="verdict is invalid"):
        production.import_visual_semantics(job_dir, bad_sem_path)

    # 2. Verify that with AUTO semantics, Python deterministically evaluates Exposure
    valid_semantics = {
        "protocol_version": "2.0",
        "job_id": "job-actionable",
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "AUTO"},
                    {"image_id": "2", "verdict": "AUTO"},
                ],
            }
        ],
        "unassigned": [],
    }
    valid_sem_path = tmp_path / "valid_semantics.json"
    valid_sem_path.write_text(json.dumps(valid_semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, valid_sem_path)

    measurements = [
        {"image_id": "1", "status": "MEASURED", "measurement": 0.50, "preview_sha256": "sha-1"},
        {"image_id": "2", "status": "MEASURED", "measurement": 0.25, "preview_sha256": "sha-2"},
    ]

    plan = production.build_production_plan(job_dir, measurements)
    by_id = {item["image_id"]: item for item in plan["items"]}

    # Image 1 is the reference: delta is 0.0 -> Python sets DETERMINISTIC_ZERO_DELTA
    assert by_id["1"]["pre_apply_status"] == "NO_CHANGE"
    assert by_id["1"]["reason_code"] == "DETERMINISTIC_ZERO_DELTA"
    assert by_id["1"]["validated_delta_ev"] == 0.0

    # Image 2 is darker than reference (0.25 vs 0.50): requires +1.0 EV adjustment!
    # Direct visual NO_CHANGE could have bypassed this. With AUTO, it MUST be WILL_ADJUST.
    assert by_id["2"]["pre_apply_status"] == "WILL_ADJUST"
    assert by_id["2"]["validated_delta_ev"] == 1.0
    assert by_id["2"]["target_exposure2012"] == 1.0
    assert by_id["2"]["reason_code"] == "DETERMINISTIC_REFERENCE_MATCH"

    # Plan counts check
    assert plan["counts"] == {
        "input_count": 2,
        "will_adjust": 1,
        "no_change": 1,
        "unresolved": 0,
    }
    assert plan["catalog_plan"]["planned_count"] == 1


def test_build_production_plan_rejects_member_no_change(tmp_path: Path) -> None:
    """build_production_plan must refuse to evaluate any visual NO_CHANGE verdict."""
    ids = ("1", "2")
    job_dir = _make_job(tmp_path, "job-legacy-bypass", ids)
    tampered = {
        "protocol_version": "2.0",
        "job_id": "job-legacy-bypass",
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "AUTO"},
                    {"image_id": "2", "verdict": "NO_CHANGE"},
                ],
            }
        ],
        "unassigned": [],
    }
    (job_dir / "visual-semantics.json").write_text(json.dumps(tampered), encoding="utf-8")
    production.update_production_job_state(
        job_dir,
        production.WAITING_FOR_SEMANTICS,
        visual_semantics_runs=1,
    )
    measurements = [
        {"image_id": "1", "status": "MEASURED", "measurement": 0.50, "preview_sha256": "sha-1"},
        {"image_id": "2", "status": "MEASURED", "measurement": 0.25, "preview_sha256": "sha-2"},
    ]
    with pytest.raises(production.ProductionJobError, match="unsupported member verdict|invalid"):
        production.build_production_plan(job_dir, measurements)

