from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import pytest

import lr_ai_exposure.production_job as production
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest


def _jpeg(value: int = 110) -> bytes:
    image = Image.new("RGB", (80, 60), (value, value, value))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _policy() -> dict[str, float]:
    return {
        "quantum_ev": 0.05,
        "maximum_delta_ev": 3.0,
        "minimum_exposure2012": -5.0,
        "maximum_exposure2012": 5.0,
    }


def _manifest(job_dir: Path, ids: tuple[str, ...]) -> Manifest:
    preview_dir = job_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for index, image_id in enumerate(ids, 1):
        payload = _jpeg(100 + index * 10)
        rel = f"previews/{index:06d}__{image_id}.jpg"
        (job_dir / rel).write_bytes(payload)
        import hashlib
        digest = hashlib.sha256(payload).hexdigest()
        entries.append(
            ManifestEntry(
                image_id=image_id,
                raw_path=f"D:/album/{image_id}.NEF",
                source_xmp_path=f"D:/album/{image_id}.xmp",
                backup_relative_path=f"xmp_backups/{image_id}.xmp",
                preview_path=rel,
                seq=index,
                extraction_status="FOUND",
                uuid=f"uuid-{image_id}",
                preview_bytes=len(payload),
                preview_sha256=digest,
                preview_orientation="AB",
                source_preview_sha256=digest,
                source_preview_tier=1440,
            )
        )
    manifest = Manifest(
        job_id="job-rf",
        entries=entries,
        total_selected=len(ids),
        total_found=len(ids),
        total_missing=0,
        total_ambiguous=0,
        total_failed=0,
    )
    write_manifest(job_dir, manifest)
    return manifest


def _selection(job_dir: Path, ids: tuple[str, ...]) -> None:
    (job_dir / "selection.json").write_text(
        json.dumps(
            {
                "protocol_version": "2.0",
                "job_id": "job-rf",
                "selected_count": len(ids),
                "source_folder": "D:/album",
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
        ),
        encoding="utf-8",
    )


def test_reference_free_bracket_package_uses_opaque_candidate_ids(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    manifest = _manifest(job_dir, ("1", "2"))

    result = production.build_reference_free_target_package(job_dir, manifest)

    assert result["result_kind"] == "REFERENCE_FREE_TARGET_CANDIDATES"
    assert [item["image_id"] for item in result["items"]] == ["1", "2"]
    first = result["items"][0]
    assert len(first["candidates"]) >= 7
    assert all(candidate["candidate_id"].startswith("c") for candidate in first["candidates"])
    assert any(candidate["is_baseline"] for candidate in first["candidates"])
    assert Path(job_dir / first["sheet_path"]).is_file()


def test_reference_free_semantics_can_select_target_without_reference(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1", "2")
    manifest = _manifest(job_dir, ids)
    production.build_reference_free_target_package(job_dir, manifest)

    payload = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [
            {
                "group_id": "g-1",
                "status": "TARGETS_SELECTED",
                "reference_image_id": None,
                "members": [
                    {"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c04"},
                    {"image_id": "2", "verdict": "AUTO", "target_candidate_id": "c02"},
                ],
            }
        ],
        "unassigned": [],
    }
    validated = production.validate_visual_semantics(payload, job_id="job-rf", ordered_image_ids=ids)
    assert validated["groups"][0]["members"][0]["target_candidate_id"] == "c04"


def test_reference_free_planner_uses_per_image_target_not_group_reference(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1", "2")
    manifest = _manifest(job_dir, ids)
    _selection(job_dir, ids)
    production.create_production_job_state(
        job_dir,
        job_id="job-rf",
        source_folder="D:/album",
        ordered_image_ids=ids,
        policy=_policy(),
    )
    production.build_reference_free_target_package(job_dir, manifest)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [
            {
                "group_id": "g-1",
                "status": "TARGETS_SELECTED",
                "reference_image_id": None,
                "members": [
                    {"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c05"},
                    {"image_id": "2", "verdict": "AUTO", "target_candidate_id": "c03"},
                ],
            }
        ],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, sem_path)

    # Planning consumes deterministic baseline measurements.  Target measurements
    # are supplied by the frozen target-candidate seam in this unit test.
    measurements = [
        {"image_id": "1", "status": "MEASURED", "measurement": 0.45, "preview_sha256": manifest.entries[0].preview_sha256},
        {"image_id": "2", "status": "MEASURED", "measurement": 0.70, "preview_sha256": manifest.entries[1].preview_sha256},
    ]
    monkeypatch.setattr(
        production,
        "_reference_free_target_measurement",
        lambda directory, image_id, candidate_id: 0.60,
    )
    monkeypatch.setattr(
        production,
        "estimate_renderer_calibrated_delta_ev",
        lambda **kwargs: +0.50 if kwargs["baseline_measurement"] < 0.60 else -0.50,
    )

    plan = production.build_production_plan(job_dir, measurements)
    by_id = {item["image_id"]: item for item in plan["items"]}
    assert by_id["1"]["validated_delta_ev"] == +0.50
    assert by_id["2"]["validated_delta_ev"] == -0.50
    assert plan["catalog_plan"]["planned_count"] == 2


def test_reference_free_import_rejects_unknown_candidate_id(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1",)
    manifest = _manifest(job_dir, ids)
    production.create_production_job_state(
        job_dir,
        job_id="job-rf",
        source_folder="D:/album",
        ordered_image_ids=ids,
        policy=_policy(),
    )
    production.build_reference_free_target_package(job_dir, manifest)
    payload = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [
            {
                "group_id": "g-1",
                "status": "TARGETS_SELECTED",
                "reference_image_id": None,
                "members": [
                    {"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c99"}
                ],
            }
        ],
        "unassigned": [],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(production.ProductionJobError, match="unknown target candidate"):
        production.import_visual_semantics(job_dir, path)


def test_reference_free_target_with_new_highlight_clipping_fails_closed(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1",)
    manifest = _manifest(job_dir, ids)
    _selection(job_dir, ids)
    production.create_production_job_state(
        job_dir,
        job_id="job-rf",
        source_folder="D:/album",
        ordered_image_ids=ids,
        policy=_policy(),
    )
    package = production.build_reference_free_target_package(job_dir, manifest)
    # Force one candidate to represent an unsafe visual choice while preserving
    # opaque candidate identity; planner must reject it before numeric mutation.
    package["items"][0]["candidates"][0]["new_highlight_clip_fraction"] = 0.10
    (job_dir / "reference-free-target-candidates.json").write_text(
        json.dumps(package), encoding="utf-8"
    )
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [
            {
                "group_id": "g-1",
                "status": "TARGETS_SELECTED",
                "reference_image_id": None,
                "members": [
                    {"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c00"}
                ],
            }
        ],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, sem_path)
    measurements = [
        {
            "image_id": "1",
            "status": "MEASURED",
            "measurement": 0.45,
            "preview_sha256": manifest.entries[0].preview_sha256,
        }
    ]
    plan = production.build_production_plan(job_dir, measurements)
    assert plan["catalog_plan"]["planned_count"] == 0
    assert plan["items"][0]["pre_apply_status"] == "UNRESOLVED"
    assert plan["items"][0]["reason_code"] == "UNSAFE_TARGET_HIGHLIGHTS"


def test_reference_free_large_unvalidated_delta_fails_closed(monkeypatch, tmp_path: Path) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1",)
    manifest = _manifest(job_dir, ids)
    _selection(job_dir, ids)
    production.create_production_job_state(
        job_dir,
        job_id="job-rf",
        source_folder="D:/album",
        ordered_image_ids=ids,
        policy=_policy(),
    )
    production.build_reference_free_target_package(job_dir, manifest)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [{
            "group_id": "g-1",
            "status": "TARGETS_SELECTED",
            "reference_image_id": None,
            "members": [{"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c05"}],
        }],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, sem_path)
    measurements = [{
        "image_id": "1",
        "status": "MEASURED",
        "measurement": 0.45,
        "preview_sha256": manifest.entries[0].preview_sha256,
    }]
    monkeypatch.setattr(production, "_reference_free_target_measurement", lambda *args, **kwargs: 0.70)
    monkeypatch.setattr(production, "estimate_renderer_calibrated_delta_ev", lambda **kwargs: 1.20)
    plan = production.build_production_plan(job_dir, measurements)
    assert plan["catalog_plan"]["planned_count"] == 0
    assert plan["items"][0]["pre_apply_status"] == "UNRESOLVED"
    assert plan["items"][0]["reason_code"] == "RENDER_RESPONSE_UNCERTAIN"


def test_reference_free_acceptable_interval_uses_robust_midpoint_target(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1",)
    manifest = _manifest(job_dir, ids)
    _selection(job_dir, ids)
    production.create_production_job_state(
        job_dir, job_id="job-rf", source_folder="D:/album", ordered_image_ids=ids, policy=_policy()
    )
    production.build_reference_free_target_package(job_dir, manifest)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [{
            "group_id": "g-1", "status": "TARGETS_SELECTED", "reference_image_id": None,
            "members": [{
                "image_id": "1", "verdict": "AUTO", "target_candidate_id": "c04",
                "acceptable_candidate_ids": ["c03", "c04"],
            }],
        }],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, sem_path)
    measurements = [{
        "image_id": "1", "status": "MEASURED", "measurement": 0.45,
        "preview_sha256": manifest.entries[0].preview_sha256,
    }]
    monkeypatch.setattr(
        production, "_reference_free_target_measurement",
        lambda directory, image_id, candidate_id: {"c03": 0.50, "c04": 0.60}[candidate_id],
    )
    observed = {}
    def fake_estimator(**kwargs):
        observed.update(kwargs)
        return 0.25
    monkeypatch.setattr(production, "estimate_renderer_calibrated_delta_ev", fake_estimator)
    plan = production.build_production_plan(job_dir, measurements)
    assert observed["target_measurement"] == pytest.approx(0.55)
    assert plan["items"][0]["acceptable_candidate_ids"] == ["c03", "c04"]
    assert plan["catalog_plan"]["planned_count"] == 1


def test_new_reference_free_job_rejects_legacy_reference_authority(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1", "2")
    manifest = _manifest(job_dir, ids)
    production.create_production_job_state(
        job_dir, job_id="job-rf", source_folder="D:/album", ordered_image_ids=ids, policy=_policy()
    )
    production.build_reference_free_target_package(job_dir, manifest)
    payload = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [{
            "group_id": "legacy",
            "status": "REFERENCE_SELECTED",
            "reference_image_id": "1",
            "members": [
                {"image_id": "1", "verdict": "AUTO"},
                {"image_id": "2", "verdict": "AUTO"},
            ],
        }],
        "unassigned": [],
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(production.ProductionJobError, match="forbid REFERENCE_SELECTED"):
        production.import_visual_semantics(job_dir, path)


def test_reference_free_target_up_to_one_ev_is_staged_in_half_ev_step(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "job-rf"
    job_dir.mkdir()
    ids = ("1",)
    manifest = _manifest(job_dir, ids)
    _selection(job_dir, ids)
    production.create_production_job_state(
        job_dir, job_id="job-rf", source_folder="D:/album", ordered_image_ids=ids, policy=_policy()
    )
    production.build_reference_free_target_package(job_dir, manifest)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [{
            "group_id": "g-1", "status": "TARGETS_SELECTED", "reference_image_id": None,
            "members": [{"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c05"}],
        }],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job_dir, sem_path)
    measurements = [{
        "image_id": "1", "status": "MEASURED", "measurement": 0.45,
        "preview_sha256": manifest.entries[0].preview_sha256,
    }]
    monkeypatch.setattr(production, "_reference_free_target_measurement", lambda *args, **kwargs: 0.70)
    monkeypatch.setattr(production, "estimate_renderer_calibrated_delta_ev", lambda **kwargs: 0.80)
    plan = production.build_production_plan(job_dir, measurements)
    assert plan["catalog_plan"]["planned_count"] == 1
    item = plan["items"][0]
    assert item["pre_apply_status"] == "WILL_ADJUST"
    assert item["validated_delta_ev"] == pytest.approx(0.50)
    assert item["desired_total_delta_ev"] == pytest.approx(0.80)
    assert plan["catalog_plan"]["items"][0]["delta_ev"] == pytest.approx(0.50)

