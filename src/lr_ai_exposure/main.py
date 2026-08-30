"""Canonical CLI for Lightroom AI Exposure Assist.

Canonical production workflows:
1. Prepared-folder workflow (WO-029 backward compatibility):
   - --prepare-job
   - --process-job
   - --apply-job

2. Iterative Whole-Folder Exposure Session workflow:
   - --start-session (prepares session & Pass 1)
   - --prepare-session-pass (prepares Pass N with render freshness check)
   - --analyze-session-pass (validates/runs AI decisions for Pass N)
   - --apply-session-pass (applies Exposure2012 for Pass N and checks convergence)
   - --session-status (retrieves session state summary)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lr_ai_exposure.config import load_config, ConfigError
from lr_ai_exposure.diagnostics import run_diagnostic
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.handoff import handoff_job
from lr_ai_exposure.ai_judge import analyze_job_single_pass
from lr_ai_exposure.analysis_result import (
    serialize_decisions,
    serialize_evidence,
    write_ai_decisions,
    write_analysis_evidence,
)
from lr_ai_exposure.job_lifecycle import (
    JOB_STATE_APPLY_COMPLETED,
    JOB_STATE_APPLY_COMPLETED_WITH_SKIPS,
    JOB_STATE_APPLY_FAILED,
    JOB_STATE_DECISIONS_VALIDATED,
    configure_external_file_provider,
    eligible_apply_ids,
    load_job_state,
    prepare_external_ai_job,
    resolve_saved_job,
    update_job_state,
)
from lr_ai_exposure.session import load_session, resolve_session_dir, SessionError
from lr_ai_exposure.session_lifecycle import (
    prepare_session_pass,
    analyze_session_pass,
    apply_session_pass,
)


def _write_bridge_result(out_path: Path | None, payload: dict[str, Any]) -> None:
    if not out_path:
        return
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(out_path)
    except Exception as exc:
        print(f"ERROR writing bridge result: {exc}", file=sys.stderr)


def _diagnostic_settings_fallback(root: Path, error: ConfigError) -> dict[str, Any]:
    """Recover only non-secret diagnostic paths when canonical config is invalid."""
    runtime_directory = root / "runtime"
    preview_cache_path = ""
    try:
        raw = json.loads((root / "config" / "settings.json").read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            runtime_value = raw.get("runtime_directory")
            if isinstance(runtime_value, str) and runtime_value:
                runtime_candidate = Path(runtime_value)
                runtime_directory = (
                    runtime_candidate
                    if runtime_candidate.is_absolute()
                    else root / runtime_candidate
                )
            preview_value = raw.get("preview_cache_path")
            if isinstance(preview_value, str):
                preview_cache_path = preview_value
    except (OSError, ValueError, TypeError):
        pass
    return {
        "runtime_directory": str(runtime_directory),
        "preview_cache_path": preview_cache_path,
        "_diagnostic_config_error": str(error),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lr-ai-exposure",
        description="Lightroom AI Exposure Assist",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration and print a summary",
    )
    parser.add_argument(
        "--prepare-job",
        action="store_true",
        help="Extract selected previews once and create an external-AI job bundle.",
    )
    parser.add_argument(
        "--diagnose-current-folder",
        action="store_true",
        help="Aggregate read-only Lightroom folder, cache, CLI, bridge, and XMP readiness.",
    )
    parser.add_argument(
        "--diagnostic-input",
        type=Path,
        help="Path to the diagnostic request JSON written by the Lightroom plug-in.",
    )
    parser.add_argument(
        "--process-job",
        metavar="JOB_ID",
        help="Validate external AI decisions for an existing prepared job.",
    )
    parser.add_argument(
        "--apply-job",
        metavar="JOB_ID",
        help="Validate and apply an existing prepared job without re-reading cache.",
    )
    parser.add_argument(
        "--analyze-only",
        dest="analyze_only",
        action="store_true",
        help="Legacy one-shot analysis route (default when no operation is supplied).",
    )
    parser.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Legacy one-shot apply route.",
    )
    parser.add_argument(
        "--authorize-apply",
        type=str,
        help="Second-key authorization. Must exactly equal the target job_id or session_id.",
    )
    parser.add_argument(
        "--bridge-result",
        type=Path,
        help="Path to write the authoritative bridge result JSON.",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        help="Path to selection.json from Lightroom (prepare/legacy/session routes).",
    )
    parser.add_argument(
        "--lrdata",
        type=Path,
        help="Path to Lightroom Previews.lrdata directory (prepare/legacy/session routes).",
    )

    # Iterative Exposure Session routes
    parser.add_argument(
        "--start-session",
        action="store_true",
        help="Initialize an iterative exposure session and prepare Pass 1.",
    )
    parser.add_argument(
        "--prepare-session-pass",
        action="store_true",
        help="Prepare Pass N for an existing session with render freshness barrier check.",
    )
    parser.add_argument(
        "--analyze-session-pass",
        action="store_true",
        help="Validate/execute AI exposure decisions for Pass N of a session.",
    )
    parser.add_argument(
        "--apply-session-pass",
        action="store_true",
        help="Apply Exposure2012 adjustments for Pass N and evaluate convergence.",
    )
    parser.add_argument(
        "--session-status",
        action="store_true",
        help="Inspect current state and convergence progress of an exposure session.",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Identifier of the iterative exposure session.",
    )
    parser.add_argument(
        "--pass-number",
        type=int,
        default=1,
        help="Pass number for iterative session operations (default: 1).",
    )
    parser.add_argument(
        "--parent-pass-id",
        type=str,
        help="Parent pass ID for session pass lineage.",
    )

    return parser


def _select_mode(args: argparse.Namespace) -> str:
    if args.apply and args.analyze_only:
        raise ConfigError(
            "Conflicting modes: --analyze-only and --apply are mutually exclusive"
        )
    if args.apply:
        return "APPLY"
    return "ANALYZE_ONLY"


def _select_operation(args: argparse.Namespace) -> str:
    session_ops = [
        bool(args.start_session),
        bool(args.prepare_session_pass),
        bool(args.analyze_session_pass),
        bool(args.apply_session_pass),
        bool(args.session_status),
    ]
    prepared_ops = [
        bool(args.diagnose_current_folder),
        bool(args.prepare_job),
        bool(args.process_job),
        bool(args.apply_job),
    ]
    if sum(session_ops) + sum(prepared_ops) > 1:
        raise ConfigError("Requested operations are mutually exclusive")
    if (any(session_ops) or any(prepared_ops)) and (args.analyze_only or args.apply):
        raise ConfigError("Structured operations cannot be combined with legacy --analyze-only/--apply")

    if args.start_session:
        return "START_SESSION"
    if args.prepare_session_pass:
        return "PREPARE_SESSION_PASS"
    if args.analyze_session_pass:
        return "ANALYZE_SESSION_PASS"
    if args.apply_session_pass:
        return "APPLY_SESSION_PASS"
    if args.session_status:
        return "SESSION_STATUS"
    if args.diagnose_current_folder:
        return "DIAGNOSE_CURRENT_FOLDER"
    if args.prepare_job:
        return "PREPARE"
    if args.process_job:
        return "PROCESS_SAVED"
    if args.apply_job:
        return "APPLY_SAVED"
    return _select_mode(args)


def _run_handoff(
    settings: dict[str, Any],
    root: Path,
    selection_path: Path,
    lrdata_path: Path,
) -> tuple[Path, object]:
    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    job_id = handoff_job(
        str(runtime_dir),
        str(lrdata_path),
        str(selection_path),
    )
    job_dir = runtime_dir / "jobs" / job_id
    manifest = read_manifest(job_dir)
    return job_dir, manifest


def _run_analysis(
    manifest: object,
    job_dir: Path,
    settings: dict[str, Any],
) -> list:
    return analyze_job_single_pass(manifest, job_dir, settings)


def _write_artifacts(
    job_dir: Path,
    manifest: object,
    decisions: list,
    settings: dict[str, Any],
    mode: str,
) -> tuple[Path, Path]:
    provider = settings.get("ai_provider", "unknown")
    model = settings.get("ai_model", "unknown")
    apply_authorized = bool(settings.get("apply_authorized", False)) and mode.startswith(
        "APPLY"
    )

    decisions_payload = serialize_decisions(
        job_id=manifest.job_id,
        decisions=decisions,
        provider=provider,
        model=model,
        mode=mode,
        apply_authorized=apply_authorized,
        xmp_mutation=False,
    )
    evidence_payload = serialize_evidence(
        job_id=manifest.job_id,
        decisions=decisions,
        provider=provider,
        model=model,
        settings=settings,
        mode=mode,
    )
    return (
        write_ai_decisions(job_dir, decisions_payload),
        write_analysis_evidence(job_dir, evidence_payload),
    )


def _run_apply(
    job_dir: Path,
    selection_path: Path,
    decisions: list,
    settings: dict[str, Any],
) -> dict:
    from lr_ai_exposure.apply import apply_exposure_deltas

    return apply_exposure_deltas(job_dir, selection_path, decisions, settings)


def _validate_prepare_inputs(args: argparse.Namespace) -> tuple[Path, Path]:
    if not args.selection or not args.lrdata:
        raise ConfigError("Operation requires --selection and --lrdata")
    selection_path = args.selection.resolve()
    lrdata_path = args.lrdata.resolve()
    if not selection_path.is_file():
        raise ConfigError(f"Selection file not found at {selection_path}")
    if not lrdata_path.is_dir():
        raise ConfigError(f"lrdata directory not found at {lrdata_path}")
    return selection_path, lrdata_path


def _write_run_log(
    job_dir: Path,
    mode: str,
    decision_count: int,
    applied: int,
    skipped: int,
    errors: int,
) -> None:
    content = (
        f"Job processed: {job_dir.name}\n"
        f"Mode: {mode}\n"
        f"Decisions: {decision_count}\n"
        f"Applied: {applied}\n"
        f"Skipped: {skipped}\n"
        f"Errors: {errors}\n"
    )
    (job_dir / "run.log").write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    job_id = "unknown"
    job_dir: Path | None = None
    mode = "UNKNOWN"
    decisions_path = ""
    evidence_path = ""
    apply_evidence: str | None = None
    decision_count = 0
    applied_count = 0
    skipped_count = 0
    error_count = 0
    if args.diagnose_current_folder:
        mode = "DIAGNOSE_CURRENT_FOLDER"

    def _result_payload(status: str, error: str | None = None, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "protocol_version": "1.0",
            "status": status,
            "job_id": job_id,
            "mode": mode,
            "decision_count": decision_count,
            "applied": applied_count,
            "skipped": skipped_count,
            "errors": error_count,
            "job_dir": str(job_dir) if job_dir else "",
            "ai_decisions": decisions_path,
            "analysis_evidence": evidence_path,
            "apply_evidence": apply_evidence,
            "error": error,
        }
        payload.update(extra)
        return payload

    def _fail(msg: str) -> int:
        print(f"ERROR: {msg}", file=sys.stderr)
        _write_bridge_result(args.bridge_result, _result_payload("error", msg))
        return 1

    try:
        operation = _select_operation(args)
    except ConfigError as exc:
        return _fail(str(exc))

    root = Path.cwd()
    try:
        settings = load_config(root)
    except ConfigError as exc:
        if operation != "DIAGNOSE_CURRENT_FOLDER":
            return _fail(str(exc))
        settings = _diagnostic_settings_fallback(root, exc)

    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    if args.check_config:
        summary = {
            "status": "ok",
            "dry_run": settings["dry_run"],
            "maximum_delta_ev": settings["maximum_delta_ev"],
            "minimum_apply_confidence": settings["minimum_apply_confidence"],
            "preview_size": settings["preview_size"],
            "runtime_directory": settings["runtime_directory"],
            "canonical_provider": settings.get("ai_provider"),
        }
        print(json.dumps(summary, indent=2))
        return 0

    if operation == "DIAGNOSE_CURRENT_FOLDER":
        mode = operation
        if not args.diagnostic_input:
            return _fail("--diagnostic-input is required for current-folder diagnostics")
        try:
            diagnostic_input = args.diagnostic_input.resolve()
            if not diagnostic_input.is_file():
                raise FileNotFoundError(
                    f"Diagnostic input file not found at {diagnostic_input}"
                )
            request = json.loads(diagnostic_input.read_text(encoding="utf-8"))
            if not isinstance(request, dict):
                raise ValueError("Diagnostic input must contain one JSON object")
            request_id = request.get("diagnostic_id")
            if isinstance(request_id, str) and request_id:
                job_id = request_id
            report = run_diagnostic(request, settings, root)
        except Exception as exc:
            return _fail(f"Current-folder diagnostic failed: {exc}")

        result = _result_payload(
            "ok",
            diagnostic_completed=True,
            overall_readiness=report["overall_readiness"],
            issue_count=len(report["issues"]),
            preflight_json=report["artifacts"]["preflight_json"],
            diagnostic_txt=report["artifacts"]["diagnostic_txt"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    # Iterative Exposure Session operations
    if operation == "START_SESSION":
        mode = "START_SESSION"
        try:
            selection_path, lrdata_path = _validate_prepare_inputs(args)
            session_info = prepare_session_pass(
                runtime_directory=runtime_dir,
                lrdata_dir=lrdata_path,
                selection_json_path=selection_path,
                session_id=args.session_id,
                pass_number=1,
                project_root=root,
            )
            job_id = session_info["session_id"]
        except Exception as exc:
            return _fail(f"Start Session failed: {exc}")

        result = _result_payload(
            "ok",
            session_id=session_info["session_id"],
            pass_id=session_info["pass_id"],
            pass_number=1,
            session_dir=session_info["session_dir"],
            pass_dir=session_info["pass_dir"],
            manifest=session_info["manifest_path"],
            preview_directory=session_info["preview_directory"],
            decision_directory=session_info["decision_directory"],
            decision_schema=session_info["decision_schema"],
            ai_task=session_info["ai_task"],
            total_selected=session_info["total_selected"],
            total_found=session_info["total_found"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "PREPARE_SESSION_PASS":
        mode = f"PREPARE_SESSION_PASS_{args.pass_number}"
        if not args.session_id:
            return _fail("--session-id is required for prepare-session-pass")
        try:
            selection_path, lrdata_path = _validate_prepare_inputs(args)
            session_info = prepare_session_pass(
                runtime_directory=runtime_dir,
                lrdata_dir=lrdata_path,
                selection_json_path=selection_path,
                session_id=args.session_id,
                pass_number=args.pass_number,
                parent_pass_id=args.parent_pass_id,
                project_root=root,
            )
            job_id = session_info["session_id"]
        except Exception as exc:
            return _fail(f"Prepare Session Pass failed: {exc}")

        result = _result_payload(
            "ok",
            session_id=session_info["session_id"],
            pass_id=session_info["pass_id"],
            pass_number=session_info["pass_number"],
            session_dir=session_info["session_dir"],
            pass_dir=session_info["pass_dir"],
            manifest=session_info["manifest_path"],
            preview_directory=session_info["preview_directory"],
            decision_directory=session_info["decision_directory"],
            render_barrier=session_info.get("render_barrier", {}),
            total_selected=session_info["total_selected"],
            total_found=session_info["total_found"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "ANALYZE_SESSION_PASS":
        mode = f"ANALYZE_SESSION_PASS_{args.pass_number}"
        if not args.session_id:
            return _fail("--session-id is required for analyze-session-pass")
        try:
            analysis_info = analyze_session_pass(
                runtime_directory=runtime_dir,
                session_id=args.session_id,
                pass_number=args.pass_number,
                settings=settings,
            )
            job_id = args.session_id
            decision_count = analysis_info["decision_count"]
            decisions_path = analysis_info["ai_decisions"]
            evidence_path = analysis_info["analysis_evidence"]
        except Exception as exc:
            return _fail(f"Analyze Session Pass failed: {exc}")

        result = _result_payload(
            "ok",
            session_id=analysis_info["session_id"],
            pass_number=analysis_info["pass_number"],
            pass_id=analysis_info["pass_id"],
            decision_count=decision_count,
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "APPLY_SESSION_PASS":
        mode = f"APPLY_SESSION_PASS_{args.pass_number}"
        if not args.session_id:
            return _fail("--session-id is required for apply-session-pass")
        if args.authorize_apply != args.session_id:
            return _fail("Apply Session Pass requires --authorize-apply equal to the exact session_id")
        try:
            apply_info = apply_session_pass(
                runtime_directory=runtime_dir,
                session_id=args.session_id,
                pass_number=args.pass_number,
                authorize_apply=args.authorize_apply,
                settings=settings,
            )
            job_id = args.session_id
            applied_count = apply_info["applied_count"]
            apply_evidence = apply_info["apply_evidence"]
        except Exception as exc:
            return _fail(f"Apply Session Pass failed: {exc}")

        result = _result_payload(
            "ok",
            session_id=apply_info["session_id"],
            pass_number=apply_info["pass_number"],
            pass_id=apply_info["pass_id"],
            applied=apply_info["applied_count"],
            pass_count=apply_info["pass_count"],
            review_count=apply_info["review_count"],
            is_converged=apply_info["is_converged"],
            applied_image_ids=apply_info["applied_image_ids"],
            next_pass_number=apply_info["next_pass_number"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "SESSION_STATUS":
        mode = "SESSION_STATUS"
        if not args.session_id:
            return _fail("--session-id is required for session-status")
        try:
            session_dir = resolve_session_dir(runtime_dir, args.session_id)
            state = load_session(session_dir)
            job_id = state.session_id
        except Exception as exc:
            return _fail(f"Session Status failed: {exc}")

        pass_count = sum(1 for img in state.images.values() if img.status == "PASS")
        adjust_count = sum(1 for img in state.images.values() if img.status == "ADJUST")
        review_count = sum(1 for img in state.images.values() if img.status == "REVIEW")
        pending_count = sum(1 for img in state.images.values() if img.status == "PENDING")

        result = _result_payload(
            "ok",
            session_id=state.session_id,
            source_folder=state.source_folder,
            total_images=len(state.images),
            passes=state.passes,
            is_converged=state.is_converged,
            pass_count=pass_count,
            adjust_count=adjust_count,
            review_count=review_count,
            pending_count=pending_count,
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    # Legacy Prepared-job operations
    if operation == "PREPARE":
        mode = "PREPARE"
        try:
            selection_path, lrdata_path = _validate_prepare_inputs(args)
            job_dir, manifest = _run_handoff(
                settings, root, selection_path, lrdata_path
            )
            job_id = manifest.job_id
            state = prepare_external_ai_job(
                job_dir,
                manifest,
                Path(settings["runtime_directory"]),
            )
            _write_run_log(job_dir, mode, 0, 0, 0, 0)
        except Exception as exc:
            return _fail(f"Prepare job failed: {exc}")

        result = _result_payload(
            "ok",
            job_state=state["state"],
            manifest=state["manifest_path"],
            preview_directory=state["preview_directory"],
            decision_directory=state["decision_directory"],
            decision_schema=state["decision_schema"],
            ai_task=state["ai_task"],
            total_selected=state["total_selected"],
            total_found=state["total_found"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation in {"PROCESS_SAVED", "APPLY_SAVED"}:
        job_id = str(args.process_job or args.apply_job)
        mode = "ANALYZE_SAVED_JOB" if operation == "PROCESS_SAVED" else "APPLY_SAVED_JOB"
        try:
            job_dir, manifest, selection_path = resolve_saved_job(
                Path(settings["runtime_directory"]), job_id
            )
            state = load_job_state(job_dir)
            external_settings = configure_external_file_provider(settings, job_dir)
            decisions = _run_analysis(manifest, job_dir, external_settings)
            decision_count = len(decisions)
            dp, ep = _write_artifacts(
                job_dir, manifest, decisions, external_settings, mode
            )
            decisions_path = str(dp)
            evidence_path = str(ep)
        except Exception as exc:
            return _fail(f"Saved-job analysis failed: {exc}")

        if operation == "PROCESS_SAVED":
            update_job_state(
                job_dir,
                JOB_STATE_DECISIONS_VALIDATED,
                decision_count=decision_count,
                ai_decisions=decisions_path,
                analysis_evidence=evidence_path,
            )
            _write_run_log(job_dir, mode, decision_count, 0, 0, 0)
            result = _result_payload(
                "ok",
                job_state=JOB_STATE_DECISIONS_VALIDATED,
                decision_directory=state["decision_directory"],
            )
            _write_bridge_result(args.bridge_result, result)
            print(json.dumps(result, indent=2))
            return 0

        if args.authorize_apply != job_id:
            return _fail(
                "Apply Prepared Job requires --authorize-apply equal to the exact job_id"
            )

        source_root = state.get("source_root")
        if not source_root:
            return _fail("Prepared job is missing its authorized source_root")

        approved_ids = eligible_apply_ids(
            decisions,
            float(settings["minimum_apply_confidence"]),
        )
        apply_settings = dict(external_settings)
        apply_settings.update(
            {
                "dry_run": False,
                "apply_authorized": True,
                "approved_image_ids": approved_ids,
                "approved_pilot_root": source_root,
            }
        )

        try:
            results = _run_apply(
                job_dir,
                selection_path,
                decisions,
                apply_settings,
            )
            applied_count = int(results.get("applied", 0))
            skipped_count = int(results.get("skipped", 0))
            error_count = int(results.get("errors", 0))
            apply_evidence = str(job_dir / "apply-evidence.json")
        except Exception as exc:
            update_job_state(
                job_dir,
                JOB_STATE_APPLY_FAILED,
                error=str(exc),
                ai_decisions=decisions_path,
                analysis_evidence=evidence_path,
            )
            return _fail(f"Apply Prepared Job failed: {exc}")

        final_state = (
            JOB_STATE_APPLY_COMPLETED
            if skipped_count == 0 and error_count == 0
            else JOB_STATE_APPLY_COMPLETED_WITH_SKIPS
        )
        update_job_state(
            job_dir,
            final_state,
            decision_count=decision_count,
            applied=applied_count,
            skipped=skipped_count,
            errors=error_count,
            approved_image_ids=approved_ids,
            ai_decisions=decisions_path,
            analysis_evidence=evidence_path,
            apply_evidence=apply_evidence,
        )
        _write_run_log(
            job_dir,
            mode,
            decision_count,
            applied_count,
            skipped_count,
            error_count,
        )
        result = _result_payload(
            "ok",
            job_state=final_state,
            approved_image_ids=approved_ids,
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    mode = operation
    if not args.selection or not args.lrdata:
        parser.print_help()
        return 0

    selection_path = args.selection.resolve()
    lrdata_path = args.lrdata.resolve()
    if not selection_path.exists():
        return _fail(f"Selection file not found at {selection_path}")
    if not lrdata_path.exists():
        return _fail(f"lrdata dir not found at {lrdata_path}")

    try:
        job_dir, manifest = _run_handoff(
            settings, root, selection_path, lrdata_path
        )
        job_id = manifest.job_id
    except Exception as exc:
        return _fail(f"Handoff failed: {exc}")

    apply_authorized = settings.get("apply_authorized", False)
    cli_authorized = args.authorize_apply == manifest.job_id
    if mode == "APPLY" and (not apply_authorized or not cli_authorized):
        print(
            "WARNING: Missing legacy two-key authorization. Forcing ANALYZE_ONLY mode.",
            file=sys.stderr,
        )
        mode = "ANALYZE_ONLY"
        settings["apply_authorized"] = False

    try:
        decisions = _run_analysis(manifest, job_dir, settings)
        decision_count = len(decisions)
    except Exception as exc:
        return _fail(f"AI Judgment failed: {exc}")

    try:
        dp, ep = _write_artifacts(job_dir, manifest, decisions, settings, mode)
        decisions_path = str(dp)
        evidence_path = str(ep)
    except Exception as exc:
        return _fail(f"Artifact write failed: {exc}")

    if mode == "APPLY":
        try:
            results = _run_apply(job_dir, selection_path, decisions, settings)
            applied_count = int(results.get("applied", 0))
            skipped_count = int(results.get("skipped", 0))
            error_count = int(results.get("errors", 0))
            apply_evidence = str(job_dir / "apply-evidence.json")
        except Exception as exc:
            return _fail(f"Apply failed: {exc}")

    _write_run_log(
        job_dir,
        mode,
        decision_count,
        applied_count,
        skipped_count,
        error_count,
    )
    result = _result_payload("ok")
    _write_bridge_result(args.bridge_result, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
