from __future__ import annotations

from lr_ai_exposure.main import _build_parser, _select_operation


def test_parser_exposes_prepared_job_lifecycle() -> None:
    actions = {action.dest for action in _build_parser()._actions}
    assert {"prepare_job", "process_job", "apply_job"}.issubset(actions)


def test_prepare_operation_is_distinct_from_analysis() -> None:
    args = _build_parser().parse_args(["--prepare-job"])
    assert _select_operation(args) == "PREPARE"


def test_process_saved_job_operation() -> None:
    args = _build_parser().parse_args(["--process-job", "job-1"])
    assert _select_operation(args) == "PROCESS_SAVED"


def test_apply_saved_job_operation() -> None:
    args = _build_parser().parse_args(["--apply-job", "job-1"])
    assert _select_operation(args) == "APPLY_SAVED"
