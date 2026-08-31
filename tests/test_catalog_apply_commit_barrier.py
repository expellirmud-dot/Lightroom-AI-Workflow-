from __future__ import annotations

import json
from pathlib import Path

import pytest

from lr_ai_exposure.catalog_confirm import (
    _recover_prior_failed_confirmation,
    _validate_catalog_result_ready,
)
from lr_ai_exposure.session import (
    SessionError,
    create_session,
    load_session,
    write_session_state,
)


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "lightroom-plugin" / "AIExposureAssist.lrplugin"


def _make_recovery_session(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    runtime_dir = tmp_path / "runtime"
    source_dir = tmp_path / "photos"
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_path = source_dir / "photo1.NEF"
    raw_path.write_bytes(b"RAW")

    session_id = "sess-recovery"
    session_dir = runtime_dir / "sessions" / session_id
    create_session(
        session_dir=session_dir,
        session_id=session_id,
        source_folder=str(source_dir),
        selection=[
            {
                "id_local": "1",
                "uuid": "uuid-1",
                "path": str(raw_path),
                "catalog_exposure2012": 0.0,
            }
        ],
    )

    pass_id = "pass-0001-test"
    state = load_session(session_dir)
    state.passes = [pass_id]
    state.images["1"].status = "REVIEW"
    state.is_converged = True
    write_session_state(session_dir, state)

    pass_dir = session_dir / "passes" / f"0001-{pass_id}"
    pass_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "protocol_version": "1.1",
        "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY",
        "session_id": session_id,
        "pass_id": pass_id,
        "pass_number": 1,
        "catalog_exposure_tolerance": 0.01,
        "planned_count": 1,
        "items": [
            {
                "image_id": "1",
                "expected_before_exposure2012": 0.0,
                "target_exposure2012": -0.75,
                "delta_ev": -0.75,
                "decision_action": "ADJUST",
            }
        ],
    }
    (pass_dir / "catalog-apply-plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )
    return runtime_dir, session_dir, pass_dir, session_id


def _write_result(path: Path, session_id: str, pass_id: str, status: str, observed: float) -> None:
    path.write_text(
        json.dumps(
            {
                "protocol_version": "1.1",
                "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT",
                "session_id": session_id,
                "pass_id": pass_id,
                "pass_number": 1,
                "results": [
                    {
                        "image_id": "1",
                        "status": status,
                        "observed_before_exposure2012": 0.0,
                        "target_exposure2012": -0.75,
                        "observed_after_exposure2012": observed,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_unverified_catalog_result_fails_closed_before_session_commit(tmp_path: Path) -> None:
    runtime_dir, session_dir, _, session_id = _make_recovery_session(tmp_path)
    result_path = tmp_path / "result.json"
    _write_result(result_path, session_id, "pass-0001-test", "CATALOG_VERIFY_TIMEOUT", 0.0)

    with pytest.raises(SessionError, match="session state was not changed"):
        _validate_catalog_result_ready(runtime_dir, session_id, 1, result_path)

    state = load_session(session_dir)
    assert state.images["1"].status == "REVIEW"
    assert state.is_converged is True


def test_verified_absolute_target_is_ready_for_confirmation(tmp_path: Path) -> None:
    runtime_dir, _, _, session_id = _make_recovery_session(tmp_path)
    result_path = tmp_path / "result.json"
    _write_result(result_path, session_id, "pass-0001-test", "APPLIED_VERIFIED", -0.75)

    result = _validate_catalog_result_ready(runtime_dir, session_id, 1, result_path)
    assert result["results"][0]["status"] == "APPLIED_VERIFIED"


def test_prior_technical_failure_evidence_recovers_only_recorded_review_ids(tmp_path: Path) -> None:
    runtime_dir, session_dir, pass_dir, session_id = _make_recovery_session(tmp_path)
    evidence = {
        "protocol_version": "1.1",
        "session_id": session_id,
        "pass_id": "pass-0001-test",
        "pass_number": 1,
        "failed_image_ids": ["1"],
    }
    (pass_dir / "catalog-apply-evidence.json").write_text(
        json.dumps(evidence), encoding="utf-8"
    )

    recovered = _recover_prior_failed_confirmation(runtime_dir, session_id, 1)
    assert recovered == ["1"]

    state = load_session(session_dir)
    assert state.images["1"].status == "PENDING"
    assert state.is_converged is False


def test_canonical_plugin_uses_post_commit_bounded_verification_and_retry_safe_targets() -> None:
    barrier = (PLUGIN / "CatalogApplyBarrier.lua").read_text(encoding="utf-8")
    command = (PLUGIN / "ImportApplyAIResults.lua").read_text(encoding="utf-8")
    confirm = (ROOT / "src" / "lr_ai_exposure" / "catalog_confirm.py").read_text(encoding="utf-8")

    assert 'photo:applyDevelopSettings({ Exposure2012 = target })' in barrier
    assert 'result.status = "APPLY_REQUESTED"' in barrier
    assert 'result.status = "CATALOG_VERIFY_TIMEOUT"' in barrier
    assert 'result.verification_mode = "TARGET_ALREADY_PRESENT"' in barrier
    assert "for attempt = 1, maxVerifyAttempts do" in barrier
    assert "LrTasks.sleep(verifySleepSeconds)" in barrier
    assert "while true" not in barrier.lower()
    assert barrier.index("catalog:withWriteAccessDo") < barrier.index("local maxVerifyAttempts")

    assert 'local CatalogApplyBarrier = require "CatalogApplyBarrier"' in command
    assert "CatalogApplyBarrier.evidenceHasFailures" in command
    assert "CatalogApplyBarrier.applyCatalogPlan(Support, catalog, photoMap, plan, resultPath)" in command
    assert "if not Support.fileExists(resultPath) then" not in command

    main_block = confirm[confirm.index("def main(") :]
    assert main_block.index("_validate_catalog_result_ready(") < main_block.index(
        "_recover_prior_failed_confirmation("
    )
    assert main_block.index("_recover_prior_failed_confirmation(") < main_block.index(
        "confirm_session_apply("
    )
