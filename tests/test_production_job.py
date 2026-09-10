from __future__ import annotations

import json
from pathlib import Path

import pytest


def _api():
    import lr_ai_exposure.production_job as api

    return api


def _semantics(job_id: str = "job-1") -> dict:
    return {
        "protocol_version": "2.0",
        "job_id": job_id,
        "groups": [
            {
                "group_id": "g-1",
                "status": "REFERENCE_SELECTED",
                "reference_image_id": "1",
                "members": [
                    {"image_id": "1", "verdict": "AUTO"},
                    {"image_id": "2", "verdict": "AUTO"},
                    {
                        "image_id": "3",
                        "verdict": "UNRESOLVED",
                        "reason": "VISUAL_AMBIGUITY",
                    },
                ],
            }
        ],
        "unassigned": [
            {"image_id": "4", "reason": "NO_CLEAR_CONTEXT"},
        ],
    }


def test_visual_semantics_accepts_minimal_provider_neutral_contract() -> None:
    api = _api()
    result = api.validate_visual_semantics(
        _semantics(), job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
    )

    assert result["job_id"] == "job-1"
    assert result["covered_image_ids"] == ["1", "2", "3", "4"]
    assert result["mutation_authority"] == "NONE"
    assert result["numeric_exposure_authority"] == "NONE"


def test_visual_semantics_rejects_any_numeric_exposure_or_unknown_field() -> None:
    api = _api()
    payload = _semantics()
    payload["groups"][0]["members"][1]["delta_ev"] = 0.25

    with pytest.raises(api.ProductionJobError, match="unexpected field|numeric|delta_ev"):
        api.validate_visual_semantics(
            payload, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )


def test_visual_semantics_rejects_missing_duplicate_foreign_and_bad_reference() -> None:
    api = _api()

    missing = _semantics()
    missing["unassigned"] = []
    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.validate_visual_semantics(
            missing, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )

    duplicate = _semantics()
    duplicate["unassigned"].append({"image_id": "2", "reason": "NO_CLEAR_CONTEXT"})
    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.validate_visual_semantics(
            duplicate, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )

    foreign = _semantics()
    foreign["unassigned"][0]["image_id"] = "999"
    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.validate_visual_semantics(
            foreign, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )

    bad_reference = _semantics()
    bad_reference["groups"][0]["reference_image_id"] = "4"
    with pytest.raises(api.ProductionJobError, match="reference"):
        api.validate_visual_semantics(
            bad_reference, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )


def test_visual_semantics_rejects_wrong_job_or_reference_on_declined_group() -> None:
    api = _api()
    wrong_job = _semantics(job_id="other")
    with pytest.raises(api.ProductionJobError, match="job_id"):
        api.validate_visual_semantics(
            wrong_job, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )

    declined = _semantics()
    declined["groups"][0]["status"] = "NO_CLEAR_REFERENCE"
    with pytest.raises(api.ProductionJobError, match="reference_image_id"):
        api.validate_visual_semantics(
            declined, job_id="job-1", ordered_image_ids=("1", "2", "3", "4")
        )


def test_production_job_state_is_durable_and_resumes_by_source_folder(tmp_path: Path) -> None:
    api = _api()
    runtime = tmp_path / "runtime"
    job_dir = runtime / "jobs" / "job-1"
    job_dir.mkdir(parents=True)

    created = api.create_production_job_state(
        job_dir,
        job_id="job-1",
        source_folder="D:/Album",
        ordered_image_ids=("1", "2"),
        policy={"quantum_ev": 0.05, "maximum_delta_ev": 1.0},
    )
    assert created["state"] == api.WAITING_FOR_SEMANTICS
    assert (job_dir / "job.json").is_file()

    loaded = api.load_production_job_state(job_dir)
    assert loaded == created

    route = api.resolve_production_workflow_state(runtime, "d:\\album\\")
    assert route["owner_state"] == "ANALYZING"
    assert route["job_id"] == "job-1"
    assert route["next_action"] == "CHECK_STATUS"

    (job_dir / "exposure-plan.json").write_text(
        json.dumps({"protocol_version": "2.0", "job_id": "job-1"}),
        encoding="utf-8",
    )
    api.update_production_job_state(job_dir, api.PLAN_READY)
    route = api.resolve_production_workflow_state(runtime, "D:/ALBUM")
    assert route["owner_state"] == "READY_TO_APPLY"
    assert route["next_action"] == "APPLY_EXPOSURE"


def test_no_production_job_routes_owner_to_ready(tmp_path: Path) -> None:
    api = _api()
    result = api.resolve_production_workflow_state(tmp_path / "runtime", "D:/album")
    assert result == {
        "owner_state": "READY",
        "next_action": "START_ANALYSIS",
        "job_id": None,
        "job_dir": None,
    }


def test_aborted_job_routes_ready(tmp_path: Path) -> None:
    api = _api()
    runtime = tmp_path / "runtime"
    d = runtime / "jobs" / "job-aborted"
    d.mkdir(parents=True)
    api.create_production_job_state(d, job_id="job-aborted", source_folder="D:/album", ordered_image_ids=("1",), policy={})
    api.update_production_job_state(d, api.ABORTED, error="SUPERSEDED")
    r = api.resolve_production_workflow_state(runtime, "D:/album")
    assert r["owner_state"] == "READY"
    assert r["next_action"] == "START_ANALYSIS"
    assert r["job_id"] is None


def test_multiple_active_jobs_for_same_source_fail_closed(tmp_path: Path) -> None:
    api = _api()
    runtime = tmp_path / "runtime"
    for index in (1, 2):
        job_dir = runtime / "jobs" / f"job-{index}"
        job_dir.mkdir(parents=True)
        api.create_production_job_state(
            job_dir,
            job_id=f"job-{index}",
            source_folder="D:/album",
            ordered_image_ids=(str(index),),
            policy={},
        )

    result = api.resolve_production_workflow_state(runtime, "D:/album")
    assert result["owner_state"] == "NEEDS_ATTENTION"
    assert result["next_action"] is None
    assert result["error"] == "MULTIPLE_ACTIVE_PRODUCTION_JOBS"


def _terminal_items() -> list[dict]:
    return [
        {
            "image_id": "1",
            "final_status": "ADJUSTED",
            "baseline_exposure2012": -0.20,
            "final_exposure2012": 0.00,
            "total_delta_ev": 0.20,
            "residual_attempts": 0,
            "reason_class": "PHOTOGRAPHIC",
            "reason_code": "SETTLED",
        },
        {
            "image_id": "2",
            "final_status": "NO_CHANGE",
            "baseline_exposure2012": 0.10,
            "final_exposure2012": 0.10,
            "total_delta_ev": 0.0,
            "residual_attempts": 0,
            "reason_class": "PHOTOGRAPHIC",
            "reason_code": "NO_CHANGE",
        },
        {
            "image_id": "3",
            "final_status": "UNRESOLVED",
            "baseline_exposure2012": 0.0,
            "final_exposure2012": 0.0,
            "total_delta_ev": 0.0,
            "residual_attempts": 1,
            "reason_class": "TECHNICAL",
            "reason_code": "RENDER_STALE",
        },
    ]


def test_terminal_accounting_is_exact_exhaustive_and_persistable(tmp_path: Path) -> None:
    api = _api()
    output = tmp_path / "final-results.json"
    result = api.finalize_production_accounting(
        job_id="job-1",
        source_folder="D:/album",
        ordered_image_ids=("1", "2", "3"),
        items=_terminal_items(),
        output_path=output,
    )

    assert result["counts"] == {
        "input_count": 3,
        "adjusted": 1,
        "no_change": 1,
        "unresolved": 1,
        "invariant_verified": True,
    }
    assert [item["image_id"] for item in result["items"]] == ["1", "2", "3"]
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_terminal_accounting_rejects_missing_duplicate_foreign_or_nonterminal() -> None:
    api = _api()
    base = _terminal_items()

    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.finalize_production_accounting(
            job_id="job-1",
            source_folder="D:/album",
            ordered_image_ids=("1", "2", "3"),
            items=base[:2],
        )

    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.finalize_production_accounting(
            job_id="job-1",
            source_folder="D:/album",
            ordered_image_ids=("1", "2", "3"),
            items=[base[0], base[0], base[2]],
        )

    foreign = [dict(item) for item in base]
    foreign[2]["image_id"] = "999"
    with pytest.raises(api.ProductionJobError, match="exactly cover"):
        api.finalize_production_accounting(
            job_id="job-1",
            source_folder="D:/album",
            ordered_image_ids=("1", "2", "3"),
            items=foreign,
        )

    invalid = [dict(item) for item in base]
    invalid[0]["final_status"] = "WILL_ADJUST"
    with pytest.raises(api.ProductionJobError, match="terminal"):
        api.finalize_production_accounting(
            job_id="job-1",
            source_folder="D:/album",
            ordered_image_ids=("1", "2", "3"),
            items=invalid,
        )
