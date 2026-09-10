from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import lr_ai_exposure.production_job as production


def _setup_verified_job(tmp_path: Path) -> Path:
    job_dir = tmp_path / "runtime" / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
    production.create_production_job_state(
        job_dir,
        job_id="job-1",
        source_folder="D:/album",
        ordered_image_ids=("1", "2", "3", "4"),
        policy={
            "quantum_ev": 0.05,
            "maximum_delta_ev": 3.0,
            "minimum_exposure2012": -5.0,
            "maximum_exposure2012": 5.0,
            "residual_tolerance_ev": 0.10,
        },
    )
    production.update_production_job_state(
        job_dir,
        production.PLAN_READY,
        visual_semantics_runs=1,
        exposure_plan="exposure-plan.json",
        plan_counts={"input_count": 4, "will_adjust": 2, "no_change": 1, "unresolved": 1},
    )
    plan = {
        "protocol_version": "2.0",
        "result_kind": "MINIMAL_PRODUCTION_EXPOSURE_PLAN",
        "job_id": "job-1",
        "source_folder": "D:/album",
        "ordered_image_ids": ["1", "2", "3", "4"],
        "counts": {"input_count": 4, "will_adjust": 2, "no_change": 1, "unresolved": 1},
        "items": [
            {
                "image_id": "1",
                "pre_apply_status": "WILL_ADJUST",
                "baseline_exposure2012": 0.0,
                "validated_delta_ev": 0.20,
                "target_exposure2012": 0.20,
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "DETERMINISTIC_REFERENCE_MATCH",
                "reference_image_id": "2",
                "target_measurement": 0.50,
                "baseline_measurement": 0.435,
                "baseline_source_preview_sha256": "base-source-1",
            },
            {
                "image_id": "2",
                "pre_apply_status": "NO_CHANGE",
                "baseline_exposure2012": 0.0,
                "validated_delta_ev": 0.0,
                "target_exposure2012": 0.0,
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "VISUAL_NO_CHANGE",
                "baseline_source_preview_sha256": "base-source-2",
            },
            {
                "image_id": "3",
                "pre_apply_status": "UNRESOLVED",
                "baseline_exposure2012": -0.10,
                "validated_delta_ev": None,
                "target_exposure2012": None,
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "MIXED_LIGHTING",
                "baseline_source_preview_sha256": "base-source-3",
            },
            {
                "image_id": "4",
                "pre_apply_status": "WILL_ADJUST",
                "baseline_exposure2012": -0.10,
                "validated_delta_ev": 0.30,
                "target_exposure2012": 0.20,
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "DETERMINISTIC_REFERENCE_MATCH",
                "reference_image_id": "2",
                "target_measurement": 0.50,
                "baseline_measurement": 0.406,
                "baseline_source_preview_sha256": "base-source-4",
            },
        ],
        "catalog_plan": {
            "protocol_version": "2.0",
            "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_PLAN",
            "job_id": "job-1",
            "catalog_exposure_tolerance": 0.01,
            "planned_count": 2,
            "items": [
                {"image_id": "1", "expected_before_exposure2012": 0.0, "target_exposure2012": 0.20, "delta_ev": 0.20},
                {"image_id": "4", "expected_before_exposure2012": -0.10, "target_exposure2012": 0.20, "delta_ev": 0.30},
            ],
        },
        "numeric_exposure_authority": "DETERMINISTIC_PYTHON",
        "mutation_authority": "NONE",
    }
    (job_dir / "exposure-plan.json").write_text(json.dumps(plan), encoding="utf-8")
    production.update_production_job_state(job_dir, production.APPLYING_CATALOG)
    production.update_production_job_state(
        job_dir,
        production.VERIFYING_RENDERS,
        applied_verified_count=2,
        applied_verified_image_ids=["1", "4"],
    )
    return job_dir


def _fresh(image_id: str, sha: str, measurement: float) -> dict:
    return {
        "image_id": image_id,
        "measurement_kind": "CANONICAL_FIXED_ROI",
        "source_preview_sha256": sha,
        "observed_measurement": measurement,
    }


def test_adjusted_only_verification_closes_when_all_settle(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    result = production.verify_production_adjusted_renders(
        job_dir,
        [
            _fresh("1", "fresh-1", 0.49),
            _fresh("4", "fresh-4", 0.48),
        ],
    )

    assert result["residual_planned_count"] == 0
    assert result["owner_state"] == "COMPLETE"
    assert result["final_accounting"]["counts"] == {
        "input_count": 4,
        "adjusted": 2,
        "no_change": 1,
        "unresolved": 1,
        "invariant_verified": True,
    }
    assert production.load_production_job_state(job_dir)["state"] == production.COMPLETE
    assert not (job_dir / "residual-plan.json").exists()


def test_verification_creates_one_targeted_residual_plan_only_for_unsettled(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    # Image 1 is within 0.10 EV; image 4 remains ~0.32 EV dark versus target.
    result = production.verify_production_adjusted_renders(
        job_dir,
        [
            _fresh("1", "fresh-1", 0.49),
            _fresh("4", "fresh-4", 0.40),
        ],
    )

    assert result["residual_planned_count"] == 1
    assert result["residual_image_ids"] == ["4"]
    residual = json.loads((job_dir / "residual-plan.json").read_text(encoding="utf-8"))
    assert residual["planned_count"] == 1
    assert residual["items"][0]["image_id"] == "4"
    assert residual["items"][0]["expected_before_exposure2012"] == pytest.approx(0.20)
    assert residual["items"][0]["delta_ev"] == pytest.approx(0.30)
    assert residual["items"][0]["target_exposure2012"] == pytest.approx(0.50)
    assert production.load_production_job_state(job_dir)["state"] == production.RESIDUAL_PLAN_READY
    assert not (job_dir / "passes").exists()


def test_stale_render_fails_closed_without_residual_retry(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    result = production.verify_production_adjusted_renders(
        job_dir,
        [
            _fresh("1", "base-source-1", 0.40),
            _fresh("4", "fresh-4", 0.50),
        ],
    )

    assert result["residual_planned_count"] == 0
    final = result["final_accounting"]
    by_id = {item["image_id"]: item for item in final["items"]}
    assert by_id["1"]["final_status"] == "UNRESOLVED"
    assert by_id["1"]["reason_class"] == "TECHNICAL"
    assert by_id["1"]["reason_code"] == "RENDER_STALE"
    assert by_id["4"]["final_status"] == "ADJUSTED"
    assert production.load_production_job_state(job_dir)["state"] == production.COMPLETE


def test_fresh_verification_requires_exact_adjusted_subset_and_fixed_roi_kind(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    with pytest.raises(production.ProductionJobError, match="exactly cover"):
        production.verify_production_adjusted_renders(job_dir, [_fresh("1", "fresh-1", 0.49)])

    job_dir = _setup_verified_job(tmp_path / "kind")
    bad = _fresh("1", "fresh-1", 0.49)
    bad["measurement_kind"] = "HSV_RECLASSIFIED"
    with pytest.raises(production.ProductionJobError, match="CANONICAL_FIXED_ROI"):
        production.verify_production_adjusted_renders(
            job_dir,
            [bad, _fresh("4", "fresh-4", 0.49)],
        )


def _residual_evidence(job_dir: Path) -> dict:
    residual = json.loads((job_dir / "residual-plan.json").read_text(encoding="utf-8"))
    item = residual["items"][0]
    return {
        "protocol_version": "1.1",
        "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT",
        "job_id": "job-1",
        "results": [
            {
                "image_id": item["image_id"],
                "expected_before_exposure2012": item["expected_before_exposure2012"],
                "target_exposure2012": item["target_exposure2012"],
                "observed_before_exposure2012": item["expected_before_exposure2012"],
                "observed_after_exposure2012": item["target_exposure2012"],
                "status": "APPLIED_VERIFIED",
            }
        ],
    }


def test_residual_apply_and_second_verify_closes_without_any_second_retry(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    production.verify_production_adjusted_renders(
        job_dir,
        [_fresh("1", "fresh-1", 0.49), _fresh("4", "fresh-4", 0.40)],
    )
    evidence_path = tmp_path / "residual-apply.json"
    evidence_path.write_text(json.dumps(_residual_evidence(job_dir)), encoding="utf-8")

    confirmed = production.confirm_production_residual_apply(job_dir, evidence_path)
    assert confirmed["verified_count"] == 1
    assert production.load_production_job_state(job_dir)["state"] == production.VERIFYING_RESIDUAL

    final = production.verify_production_residual_renders(
        job_dir,
        [_fresh("4", "fresh-4-second", 0.46)],  # about +0.12 EV residual: not settled
    )
    by_id = {item["image_id"]: item for item in final["final_accounting"]["items"]}
    assert by_id["1"]["final_status"] == "ADJUSTED"
    assert by_id["4"]["final_status"] == "UNRESOLVED"
    assert by_id["4"]["reason_code"] == "RESIDUAL_NOT_SETTLED"
    assert by_id["4"]["residual_attempts"] == 1
    assert production.load_production_job_state(job_dir)["state"] == production.COMPLETE
    assert not (job_dir / "residual-2-plan.json").exists()


def test_residual_apply_accepts_explicit_target_already_present_retry(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    production.verify_production_adjusted_renders(
        job_dir,
        [_fresh("1", "fresh-1", 0.49), _fresh("4", "fresh-4", 0.40)],
    )
    evidence = _residual_evidence(job_dir)
    evidence["results"][0]["observed_before_exposure2012"] = evidence["results"][0][
        "target_exposure2012"
    ]
    evidence["results"][0]["verification_mode"] = "TARGET_ALREADY_PRESENT"
    evidence_path = tmp_path / "residual-apply.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    confirmed = production.confirm_production_residual_apply(job_dir, evidence_path)

    assert confirmed["verified_count"] == 1
    assert production.load_production_job_state(job_dir)["state"] == production.VERIFYING_RESIDUAL


def test_residual_second_render_must_be_new_generation(tmp_path: Path) -> None:
    job_dir = _setup_verified_job(tmp_path)
    production.verify_production_adjusted_renders(
        job_dir,
        [_fresh("1", "fresh-1", 0.49), _fresh("4", "fresh-4", 0.40)],
    )
    evidence_path = tmp_path / "residual-apply.json"
    evidence_path.write_text(json.dumps(_residual_evidence(job_dir)), encoding="utf-8")
    production.confirm_production_residual_apply(job_dir, evidence_path)

    final = production.verify_production_residual_renders(
        job_dir,
        [_fresh("4", "fresh-4", 0.50)],
    )
    item = next(item for item in final["final_accounting"]["items"] if item["image_id"] == "4")
    assert item["final_status"] == "UNRESOLVED"
    assert item["reason_code"] == "RENDER_STALE"
    assert item["residual_attempts"] == 1


def test_reference_free_residual_path_uses_renderer_calibration_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir = _setup_verified_job(tmp_path)
    plan_path = job_dir / "exposure-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    first = next(item for item in plan["items"] if item["image_id"] == "1")
    first["reason_code"] = "REFERENCE_FREE_VISUAL_TARGET"
    first["target_candidate_id"] = "c05"
    first["acceptable_candidate_ids"] = ["c05"]
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    def calibrated(**kwargs):
        observed = float(kwargs["baseline_measurement"])
        if observed <= 0.41:
            return 0.25
        return 0.05

    monkeypatch.setattr(production, "estimate_renderer_calibrated_delta_ev", calibrated)

    def forbidden_legacy(*args, **kwargs):
        raise AssertionError("reference-free residual must not call legacy log-ratio EV helper")

    monkeypatch.setattr(production, "compute_per_image_delta_ev", forbidden_legacy)

    first_verify = production.verify_production_adjusted_renders(
        job_dir,
        [_fresh("1", "fresh-1", 0.40), _fresh("4", "fresh-4", 0.50)],
    )
    assert first_verify["residual_image_ids"] == ["1"]
    residual = json.loads((job_dir / "residual-plan.json").read_text(encoding="utf-8"))
    assert residual["items"][0]["delta_ev"] == pytest.approx(0.25)
    assert residual["items"][0]["target_exposure2012"] == pytest.approx(0.45)

    evidence = {
        "protocol_version": "1.1",
        "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT",
        "job_id": "job-1",
        "results": [{
            "image_id": "1",
            "expected_before_exposure2012": 0.20,
            "target_exposure2012": 0.45,
            "observed_before_exposure2012": 0.20,
            "observed_after_exposure2012": 0.45,
            "status": "APPLIED_VERIFIED",
        }],
    }
    evidence_path = tmp_path / "residual-reference-free-apply.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    production.confirm_production_residual_apply(job_dir, evidence_path)
    final = production.verify_production_residual_renders(
        job_dir, [_fresh("1", "fresh-1-second", 0.47)]
    )
    by_id = {item["image_id"]: item for item in final["final_accounting"]["items"]}
    assert by_id["1"]["final_status"] == "ADJUSTED"
    assert by_id["1"]["reason_code"] == "SETTLED_AFTER_RESIDUAL"

