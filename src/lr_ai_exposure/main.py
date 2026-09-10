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
import hashlib
import json
import sys
from importlib import metadata as importlib_metadata
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
from lr_ai_exposure.session import (
    SessionError,
    build_session_policy,
    load_session,
    resolve_session_dir,
)
from lr_ai_exposure.session_lifecycle import (
    prepare_session_pass,
    analyze_session_pass,
    apply_session_pass,
)
from lr_ai_exposure.workflow_state import resolve_workflow_state
from lr_ai_exposure.session_retention import (
    build_production_job_retention_report,
    build_retention_report,
)
from lr_ai_exposure.hybrid_folder import load_hybrid_analysis
from lr_ai_exposure.hybrid_exposure import YoloHsvSkinMeter
from lr_ai_exposure.hybrid_session import freeze_hybrid_session_pass
from lr_ai_exposure.production_job import (
    build_production_baseline_measurements,
    build_production_plan,
    extract_and_measure_production_fresh_previews,
    confirm_production_catalog_apply,
    confirm_production_residual_apply,
    import_visual_semantics,
    prepare_production_package,
    resolve_production_workflow_state,
    verify_production_adjusted_renders,
    verify_production_residual_renders,
)

PRODUCTION_FACE_MODEL = Path("models/yolov8n-face.pt")
PRODUCTION_FACE_MODEL_SHA256 = "D17B38523A994B13EE604B67F02791CA0F43B9F446A32FD7BC44E17C56EAD077"
PRODUCTION_FACE_CONFIDENCE = 0.55
PRODUCTION_FACE_IOU = 0.45
PRODUCTION_FACE_IMAGE_SIZE = 1024
PRODUCTION_MIN_SKIN_PIXELS = 50


def _package_version(package: str) -> str:
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def _production_measurement_provenance(
    *,
    model_path: Path,
    model_sha256: str,
    meter: Any,
) -> dict[str, Any]:
    meter_provenance = getattr(meter, "provenance", None)
    if not isinstance(meter_provenance, dict):
        meter_provenance = {}
    return {
        "backend": "YOLO_FACE_PLUS_HSV_SKIN",
        "model_path": PRODUCTION_FACE_MODEL.as_posix(),
        "model_sha256": model_sha256,
        "resolved_model_path": str(model_path),
        "confidence": PRODUCTION_FACE_CONFIDENCE,
        "iou": PRODUCTION_FACE_IOU,
        "image_size": PRODUCTION_FACE_IMAGE_SIZE,
        "min_skin_pixels": PRODUCTION_MIN_SKIN_PIXELS,
        "selected_device": str(meter_provenance.get("device", "UNKNOWN")),
        "dependency_versions": {
            "torch": _package_version("torch"),
            "ultralytics": _package_version("ultralytics"),
            "opencv-python": _package_version("opencv-python"),
            "opencv-python-headless": _package_version("opencv-python-headless"),
            "Pillow": _package_version("Pillow"),
        },
    }


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
    parser.add_argument(
        "--workflow-status",
        action="store_true",
        help="Resolve the read-only next workflow action for one Lightroom source folder.",
    )
    parser.add_argument(
        "--source-folder",
        type=Path,
        help="Active Lightroom source folder for workflow status operations.",
    )
    parser.add_argument(
        "--prepare-production-job",
        action="store_true",
        help="Prepare one Minimal Production job/package; no Catalog mutation.",
    )
    parser.add_argument(
        "--production-workflow-status",
        action="store_true",
        help="Resolve the owner-facing state for the Minimal Production one-job route.",
    )
    parser.add_argument(
        "--production-retention-report",
        action="store_true",
        help="Print a read-only dry-run runtime production-job retention report; never deletes files.",
    )
    parser.add_argument(
        "--import-production-semantics",
        metavar="JOB_ID",
        help="Import exactly one semantic-only visual result for a production job.",
    )
    parser.add_argument(
        "--visual-semantics",
        type=Path,
        help="Visual-semantics JSON for --import-production-semantics.",
    )
    parser.add_argument(
        "--build-production-plan",
        metavar="JOB_ID",
        help="Build the deterministic one-job Exposure plan from measurement results.",
    )
    parser.add_argument(
        "--measurements",
        type=Path,
        help="Deterministic measurement-results JSON for --build-production-plan.",
    )
    parser.add_argument(
        "--confirm-production-apply",
        metavar="JOB_ID",
        help="Confirm exact CatalogApplyBarrier evidence for the initial production apply.",
    )
    parser.add_argument(
        "--confirm-production-residual-apply",
        metavar="JOB_ID",
        help="Confirm exact CatalogApplyBarrier evidence for the one residual apply.",
    )
    parser.add_argument(
        "--catalog-apply-evidence",
        type=Path,
        help="CatalogApplyBarrier result JSON for production apply confirmation.",
    )
    parser.add_argument(
        "--measure-production-fresh-previews",
        metavar="JOB_ID",
        help="Extract and measure fresh Lightroom previews for the exact adjusted subset only.",
    )
    parser.add_argument(
        "--verify-production-renders",
        metavar="JOB_ID",
        help="Verify fresh renders for the initially adjusted subset only.",
    )
    parser.add_argument(
        "--verify-production-residual-renders",
        metavar="JOB_ID",
        help="Perform the final fresh-render verification for the residual subset only.",
    )
    parser.add_argument(
        "--fresh-measurements",
        type=Path,
        help="Canonical fixed-ROI fresh measurement JSON for production verification.",
    )
    parser.add_argument(
        "--session-retention-report",
        action="store_true",
        help="Print a read-only dry-run runtime session retention report; never deletes files.",
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
        "--import-hybrid-session-pass",
        action="store_true",
        help="Validate/freeze an exact WO-049 hybrid analysis into an existing session pass; no Lightroom mutation.",
    )
    parser.add_argument(
        "--hybrid-analysis",
        type=Path,
        help="Path to the durable hybrid-analysis JSON for --import-hybrid-session-pass.",
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
    production_ops = [
        bool(args.prepare_production_job),
        bool(args.production_workflow_status),
        bool(args.production_retention_report),
        bool(args.import_production_semantics),
        bool(args.build_production_plan),
        bool(args.measure_production_fresh_previews),
        bool(args.confirm_production_apply),
        bool(args.confirm_production_residual_apply),
        bool(args.verify_production_renders),
        bool(args.verify_production_residual_renders),
    ]
    session_ops = [
        bool(args.session_retention_report),
        bool(args.workflow_status),
        bool(args.start_session),
        bool(args.prepare_session_pass),
        bool(args.analyze_session_pass),
        bool(args.apply_session_pass),
        bool(args.session_status),
        bool(args.import_hybrid_session_pass),
    ]
    prepared_ops = [
        bool(args.diagnose_current_folder),
        bool(args.prepare_job),
        bool(args.process_job),
        bool(args.apply_job),
    ]
    if sum(production_ops) + sum(session_ops) + sum(prepared_ops) > 1:
        raise ConfigError("Requested operations are mutually exclusive")
    if (any(production_ops) or any(session_ops) or any(prepared_ops)) and (args.analyze_only or args.apply):
        raise ConfigError("Structured operations cannot be combined with legacy --analyze-only/--apply")

    if args.prepare_production_job:
        return "PREPARE_PRODUCTION_JOB"
    if args.production_workflow_status:
        return "PRODUCTION_WORKFLOW_STATUS"
    if args.production_retention_report:
        return "PRODUCTION_RETENTION_REPORT"
    if args.import_production_semantics:
        return "IMPORT_PRODUCTION_SEMANTICS"
    if args.build_production_plan:
        return "BUILD_PRODUCTION_PLAN"
    if args.measure_production_fresh_previews:
        return "MEASURE_PRODUCTION_FRESH_PREVIEWS"
    if args.confirm_production_apply:
        return "CONFIRM_PRODUCTION_APPLY"
    if args.verify_production_renders:
        return "VERIFY_PRODUCTION_RENDERS"
    if args.confirm_production_residual_apply:
        return "CONFIRM_PRODUCTION_RESIDUAL_APPLY"
    if args.verify_production_residual_renders:
        return "VERIFY_PRODUCTION_RESIDUAL_RENDERS"
    if args.session_retention_report:
        return "SESSION_RETENTION_REPORT"
    if args.workflow_status:
        return "WORKFLOW_STATUS"
    if args.start_session:
        return "START_SESSION"
    if args.prepare_session_pass:
        return "PREPARE_SESSION_PASS"
    if args.analyze_session_pass:
        return "ANALYZE_SESSION_PASS"
    if args.apply_session_pass:
        return "APPLY_SESSION_PASS"
    if args.import_hybrid_session_pass:
        return "IMPORT_HYBRID_SESSION_PASS"
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
        preview_size=int(settings["preview_size"]),
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


def _build_production_policy(settings: dict[str, Any]) -> dict[str, float]:
    # 0.05 EV quantum and Lightroom Exposure2012 -5/+5 bounds are already used
    # by the repository's Hybrid deterministic proof tests. The per-image maximum
    # remains the current owner configuration value rather than a worker-proposed limit.
    return {
        "quantum_ev": 0.05,
        "maximum_delta_ev": float(settings["maximum_delta_ev"]),
        "minimum_exposure2012": -5.0,
        "maximum_exposure2012": 5.0,
    }


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

    # WO-053 Minimal Production one-job routes. These are non-mutating until the
    # separate Lightroom Catalog apply command is explicitly introduced/proven.
    if operation == "PRODUCTION_WORKFLOW_STATUS":
        mode = operation
        if not args.source_folder:
            return _fail("--source-folder is required for --production-workflow-status")
        try:
            workflow = resolve_production_workflow_state(runtime_dir, args.source_folder)
            if workflow.get("job_id"):
                job_id = str(workflow["job_id"])
            if workflow.get("job_dir"):
                job_dir = Path(str(workflow["job_dir"]))
        except Exception as exc:
            return _fail(f"Production workflow status failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state=workflow.get("owner_state"),
            next_action=workflow.get("next_action"),
            workflow_error=workflow.get("error"),
            production_job_ids=workflow.get("job_ids", []),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "PRODUCTION_RETENTION_REPORT":
        mode = operation
        try:
            retention = build_production_job_retention_report(runtime_dir)
        except Exception as exc:
            return _fail(f"Production Retention Report failed: {exc}")
        result = _result_payload(
            "ok",
            production_retention_report=retention,
            job_count=retention["job_count"],
            eligible_count=retention["eligible_count"],
            protected_count=retention["protected_count"],
            total_bytes=retention["total_bytes"],
            eligible_bytes=retention["eligible_bytes"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "PREPARE_PRODUCTION_JOB":
        mode = operation
        try:
            selection_path, lrdata_path = _validate_prepare_inputs(args)
            prepared = prepare_production_package(
                runtime_directory=runtime_dir,
                lrdata_dir=lrdata_path,
                selection_json_path=selection_path,
                preview_size=int(settings["preview_size"]),
                policy=_build_production_policy(settings),
            )
            job_id = str(prepared["job_id"])
            job_dir = Path(str(prepared["job_dir"]))
        except Exception as exc:
            return _fail(f"Prepare production job failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state=prepared["owner_state"],
            internal_state=prepared["state"],
            next_action=prepared["next_action"],
            source_folder=prepared["source_folder"],
            total_images=prepared["total_images"],
            mutation_authority=prepared["mutation_authority"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "IMPORT_PRODUCTION_SEMANTICS":
        mode = operation
        job_id = str(args.import_production_semantics)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.visual_semantics:
            return _fail("--visual-semantics is required for --import-production-semantics")
        semantics_path = args.visual_semantics.resolve()
        if not semantics_path.is_file():
            return _fail(f"Visual semantics file not found: {semantics_path}")
        try:
            imported = import_visual_semantics(job_dir, semantics_path)
        except Exception as exc:
            return _fail(f"Import production semantics failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state="ANALYZING",
            next_action="BUILD_DETERMINISTIC_PLAN",
            covered_image_ids=imported["covered_image_ids"],
            mutation_authority=imported["mutation_authority"],
            numeric_exposure_authority=imported.get("numeric_exposure_authority", "NONE"),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "BUILD_PRODUCTION_PLAN":
        mode = operation
        job_id = str(args.build_production_plan)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        try:
            if args.measurements:
                measurement_payload = json.loads(args.measurements.resolve().read_text(encoding="utf-8"))
                if not isinstance(measurement_payload, dict) or not isinstance(measurement_payload.get("items"), list):
                    raise ValueError("measurement file must contain an items array")
            else:
                # Product numeric authority is provider-neutral robust scene luminance.
                # Face/skin detection is no longer a production admission dependency.
                measurement_payload = build_production_baseline_measurements(
                    job_dir,
                    meter=None,
                    canonical_long_edge=int(settings["preview_size"]),
                    min_skin_pixels=PRODUCTION_MIN_SKIN_PIXELS,
                    measurement_provenance={
                        "backend": "ROBUST_SCENE_LUMINANCE",
                        "crop_fraction": 0.10,
                        "trim_fraction": 0.05,
                        "highlight_clip_threshold": 245,
                    },
                )
            plan = build_production_plan(job_dir, measurement_payload["items"])
        except Exception as exc:
            return _fail(f"Build production plan failed: {exc}")
        extra: dict[str, Any] = {
            "workflow_state": plan.get("workflow_state", "READY_TO_APPLY"),
            "next_action": plan.get("next_action", "APPLY_EXPOSURE"),
            "input_count": plan["counts"]["input_count"],
            "will_adjust": plan["counts"]["will_adjust"],
            "no_change": plan["counts"]["no_change"],
            "unresolved": plan["counts"]["unresolved"],
            "planned_count": plan["catalog_plan"]["planned_count"],
            "exposure_plan": str(job_dir / "exposure-plan.json"),
            "mutation_authority": plan["mutation_authority"],
            "numeric_exposure_authority": plan.get(
                "numeric_exposure_authority", "DETERMINISTIC_PYTHON"
            ),
        }
        final = plan.get("final_accounting")
        if isinstance(final, dict) and isinstance(final.get("counts"), dict):
            final_counts = final["counts"]
            extra.update(
                adjusted=final_counts.get("adjusted"),
                no_change=final_counts.get("no_change"),
                unresolved=final_counts.get("unresolved"),
                invariant_verified=final_counts.get("invariant_verified"),
            )
        result = _result_payload("ok", **extra)
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "CONFIRM_PRODUCTION_APPLY":
        mode = operation
        job_id = str(args.confirm_production_apply)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.catalog_apply_evidence:
            return _fail("--catalog-apply-evidence is required for --confirm-production-apply")
        catalog_evidence_path = args.catalog_apply_evidence.resolve()
        try:
            confirmed = confirm_production_catalog_apply(job_dir, catalog_evidence_path)
        except Exception as exc:
            return _fail(f"Confirm production Catalog apply failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state="VERIFYING",
            next_action="VERIFY_ADJUSTED_RENDERS",
            verified_count=confirmed["verified_count"],
            verified_image_ids=confirmed["verified_image_ids"],
            mutation_authority=confirmed.get("mutation_authority", "NONE"),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "MEASURE_PRODUCTION_FRESH_PREVIEWS":
        mode = operation
        job_id = str(args.measure_production_fresh_previews)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.lrdata:
            return _fail("--lrdata is required for --measure-production-fresh-previews")
        try:
            from lr_ai_exposure.production_job import load_production_job_state, VERIFYING_RENDERS, VERIFYING_RESIDUAL

            job_state = load_production_job_state(job_dir)
            if job_state["state"] == VERIFYING_RENDERS:
                expected = [str(value) for value in job_state.get("applied_verified_image_ids", [])]
            elif job_state["state"] == VERIFYING_RESIDUAL:
                expected = [str(value) for value in job_state.get("residual_verified_image_ids", [])]
            else:
                expected = []
            measured = extract_and_measure_production_fresh_previews(
                job_dir,
                lrdata_dir=args.lrdata.resolve(),
                expected_image_ids=expected,
                target_preview_size=int(settings["preview_size"]),
            )
        except Exception as exc:
            return _fail(f"Measure production fresh previews failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state="VERIFYING",
            next_action="VERIFY_ADJUSTED_RENDERS"
            if measured.get("verification_scope") == "ADJUSTED_ONLY"
            else "VERIFY_RESIDUAL_RENDER",
            fresh_measurements=str(job_dir / "fresh-measurements.json"),
            measured_count=len(measured.get("items", [])),
            measured_image_ids=measured.get("ordered_image_ids", []),
            mutation_authority=measured.get("mutation_authority", "NONE"),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "VERIFY_PRODUCTION_RENDERS":
        mode = operation
        job_id = str(args.verify_production_renders)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.fresh_measurements:
            return _fail("--fresh-measurements is required for --verify-production-renders")
        try:
            payload = json.loads(args.fresh_measurements.resolve().read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                raise ValueError("fresh measurement file must contain an items array")
            verified = verify_production_adjusted_renders(job_dir, payload["items"])
        except Exception as exc:
            return _fail(f"Verify production adjusted renders failed: {exc}")
        extra = {
            "workflow_state": verified["owner_state"],
            "next_action": verified.get("next_action"),
            "residual_planned_count": verified.get("residual_planned_count", 0),
            "residual_image_ids": verified.get("residual_image_ids", []),
            "mutation_authority": verified.get("mutation_authority", "NONE"),
        }
        final = verified.get("final_accounting")
        if isinstance(final, dict) and isinstance(final.get("counts"), dict):
            counts = final["counts"]
            extra.update(
                input_count=counts.get("input_count"),
                adjusted=counts.get("adjusted"),
                no_change=counts.get("no_change"),
                unresolved=counts.get("unresolved"),
                invariant_verified=counts.get("invariant_verified"),
            )
        result = _result_payload("ok", **extra)
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "CONFIRM_PRODUCTION_RESIDUAL_APPLY":
        mode = operation
        job_id = str(args.confirm_production_residual_apply)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.catalog_apply_evidence:
            return _fail("--catalog-apply-evidence is required for --confirm-production-residual-apply")
        try:
            confirmed = confirm_production_residual_apply(
                job_dir, args.catalog_apply_evidence.resolve()
            )
        except Exception as exc:
            return _fail(f"Confirm production residual apply failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state="VERIFYING",
            next_action="VERIFY_RESIDUAL_RENDER",
            verified_count=confirmed["verified_count"],
            verified_image_ids=confirmed["verified_image_ids"],
            mutation_authority=confirmed.get("mutation_authority", "NONE"),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "VERIFY_PRODUCTION_RESIDUAL_RENDERS":
        mode = operation
        job_id = str(args.verify_production_residual_renders)
        job_dir = runtime_dir / "jobs" / job_id
        if not job_dir.is_dir():
            return _fail(f"Production job not found: {job_id}")
        if not args.fresh_measurements:
            return _fail("--fresh-measurements is required for --verify-production-residual-renders")
        try:
            payload = json.loads(args.fresh_measurements.resolve().read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                raise ValueError("fresh measurement file must contain an items array")
            verified = verify_production_residual_renders(job_dir, payload["items"])
        except Exception as exc:
            return _fail(f"Verify production residual renders failed: {exc}")
        counts = verified["final_accounting"]["counts"]
        result = _result_payload(
            "ok",
            workflow_state=verified["owner_state"],
            next_action=verified.get("next_action"),
            input_count=counts["input_count"],
            adjusted=counts["adjusted"],
            no_change=counts["no_change"],
            unresolved=counts["unresolved"],
            invariant_verified=counts["invariant_verified"],
            retry_budget_exhausted=verified.get("retry_budget_exhausted", True),
            mutation_authority=verified.get("mutation_authority", "NONE"),
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    if operation == "SESSION_RETENTION_REPORT":
        mode = "SESSION_RETENTION_REPORT"
        try:
            retention = build_retention_report(runtime_dir)
        except Exception as exc:
            return _fail(f"Session Retention Report failed: {exc}")
        result = _result_payload(
            "ok",
            retention_report=retention,
            session_count=retention["session_count"],
            eligible_count=retention["eligible_count"],
            protected_count=retention["protected_count"],
            total_bytes=retention["total_bytes"],
            eligible_bytes=retention["eligible_bytes"],
        )
        _write_bridge_result(args.bridge_result, result)
        print(json.dumps(result, indent=2))
        return 0

    # Read-only state-aware operator routing.
    if operation == "WORKFLOW_STATUS":
        mode = "WORKFLOW_STATUS"
        if not args.source_folder:
            return _fail("--source-folder is required for --workflow-status")
        try:
            workflow = resolve_workflow_state(runtime_dir, args.source_folder)
            pointer = workflow.get("pointer")
            if isinstance(pointer, dict) and pointer.get("session_id"):
                job_id = str(pointer["session_id"])
            elif workflow.get("session_id"):
                job_id = str(workflow["session_id"])
        except Exception as exc:
            return _fail(f"Workflow Status failed: {exc}")
        result = _result_payload(
            "ok",
            workflow_state=workflow.get("state"),
            next_action=workflow.get("next_action"),
            session_id=workflow.get("session_id"),
            pointer=workflow.get("pointer"),
            workflow_error=workflow.get("error"),
            session_ids=workflow.get("session_ids", []),
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
                target_preview_size=int(settings["preview_size"]),
                session_policy=build_session_policy(settings),
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
                target_preview_size=int(settings["preview_size"]),
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

    if operation == "IMPORT_HYBRID_SESSION_PASS":
        mode = f"IMPORT_HYBRID_SESSION_PASS_{args.pass_number}"
        if not args.session_id:
            return _fail("--session-id is required for --import-hybrid-session-pass")
        if not args.hybrid_analysis:
            return _fail("--hybrid-analysis is required for --import-hybrid-session-pass")
        try:
            session_dir = resolve_session_dir(runtime_dir, args.session_id)
            state = load_session(session_dir)
            if args.pass_number < 1 or args.pass_number > len(state.passes):
                raise SessionError(
                    f"Pass number {args.pass_number} not found in session {args.session_id}"
                )
            pass_id = state.passes[args.pass_number - 1]
            pass_dir = session_dir / "passes" / f"{args.pass_number:04d}-{pass_id}"
            manifest = read_manifest(pass_dir)
            analysis = load_hybrid_analysis(args.hybrid_analysis.resolve())
            frozen = freeze_hybrid_session_pass(pass_dir, manifest, state, analysis)
            job_id = args.session_id
            decision_count = int(frozen["decision_count"])
            decisions_path = str(frozen["ai_decisions"])
            evidence_path = str(frozen["hybrid_analysis"])
        except Exception as exc:
            return _fail(f"Import Hybrid Session Pass failed: {exc}")

        result = _result_payload(
            "ok",
            session_id=args.session_id,
            pass_number=args.pass_number,
            pass_id=pass_id,
            decision_count=decision_count,
            hybrid_analysis=evidence_path,
            ai_decisions=decisions_path,
            mutation_authority="NONE",
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
