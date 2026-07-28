"""Canonical CLI for the Lightroom AI Exposure Assist MVP.

Execution modes:

- ``--analyze-only`` (default): render previews, run the single-pass
  AI judgment, write the full ``SinglePassDecision`` schema to
  ``ai-decisions.json`` and ``analysis-evidence.json``. The apply
  layer is never imported or called.
- ``--apply``: additionally apply approved exposure deltas via the
  guarded XMP apply layer. Requires explicit user opt-in.

When neither mode is supplied, ANALYZE_ONLY is selected. The apply
function cannot be reached from the default execution path.

No XMP, RAW, catalog, or preview-cache mutation occurs in
ANALYZE_ONLY mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lr_ai_exposure.config import load_config, ConfigError
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.handoff import handoff_job
from lr_ai_exposure.ai_judge import analyze_job_single_pass
from lr_ai_exposure.analysis_result import (
    serialize_decisions,
    serialize_evidence,
    write_ai_decisions,
    write_analysis_evidence,
)

def _write_bridge_result(out_path: Path | None, payload: dict) -> None:
    if not out_path:
        return
    try:
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(out_path)
    except Exception as exc:
        print(f"ERROR writing bridge result: {exc}", file=sys.stderr)



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lr-ai-exposure",
        description="Lightroom AI Exposure Assist (MVP scaffold)",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration and print a summary",
    )
    parser.add_argument(
        "--analyze-only",
        dest="analyze_only",
        action="store_true",
        help="Run analysis and write decision artifacts without applying (default).",
    )
    parser.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Apply approved exposure deltas after analysis. Requires explicit opt-in.",
    )
    parser.add_argument(
        "--authorize-apply",
        type=str,
        help="Explicitly authorize real XMP mutation for the given job_id. Requires --apply mode.",
    )
    parser.add_argument(
        "--bridge-result",
        type=Path,
        help="Path to write the authoritative bridge result JSON.",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        help="Path to selection.json from Lightroom",
    )
    parser.add_argument(
        "--lrdata",
        type=Path,
        help="Path to Lightroom Previews.lrdata directory",
    )
    return parser


def _select_mode(args: argparse.Namespace) -> str:
    """Resolve the execution mode and reject ambiguous combinations.

    Returns ``"ANALYZE_ONLY"`` or ``"APPLY"``. When neither flag is
    supplied, ANALYZE_ONLY is selected as the default.
    """
    if args.apply and args.analyze_only:
        raise ConfigError(
            "Conflicting modes: --analyze-only and --apply are mutually exclusive"
        )
    if args.apply:
        return "APPLY"
    return "ANALYZE_ONLY"


def _run_handoff(
    settings: dict[str, Any], root: Path, selection_path: Path, lrdata_path: Path
) -> tuple[Path, "object"]:
    """Execute the handoff stage and read the canonical manifest.

    Returns ``(job_dir, manifest)``. Raises on failure.
    """
    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    job_id = handoff_job(
        str(runtime_dir), str(lrdata_path), str(selection_path)
    )
    job_dir = runtime_dir / "jobs" / job_id
    manifest = read_manifest(job_dir)
    return job_dir, manifest


def _run_analysis(
    manifest: "object",
    job_dir: Path,
    settings: dict[str, Any],
) -> list:
    """Run the single-pass AI judgment and return validated decisions.

    Passes the validated ``settings`` object through the analysis
    boundary — never a partial slice.
    """
    return analyze_job_single_pass(manifest, job_dir, settings)


def _write_artifacts(
    job_dir: Path,
    manifest: "object",
    decisions: list,
    settings: dict[str, Any],
    mode: str,
) -> tuple[Path, Path]:
    """Write the canonical analysis artifacts.

    Returns ``(ai_decisions_path, analysis_evidence_path)``.
    """
    provider = settings.get("ai_provider", "unknown")
    model = settings.get("ai_model", "unknown")
    apply_authorized = bool(settings.get("apply_authorized", False)) and mode == "APPLY"
    xmp_mutation = False

    decisions_payload = serialize_decisions(
        job_id=manifest.job_id,
        decisions=decisions,
        provider=provider,
        model=model,
        mode=mode,
        apply_authorized=apply_authorized,
        xmp_mutation=xmp_mutation,
    )
    evidence_payload = serialize_evidence(
        job_id=manifest.job_id,
        decisions=decisions,
        provider=provider,
        model=model,
        settings=settings,
        mode=mode,
    )
    decisions_path = write_ai_decisions(job_dir, decisions_payload)
    evidence_path = write_analysis_evidence(job_dir, evidence_payload)
    return decisions_path, evidence_path


def _run_apply(
    job_dir: Path,
    selection_path: Path,
    decisions: list,
    settings: dict[str, Any],
) -> dict:
    """Invoke the guarded apply layer.

    The apply module is imported lazily so the ANALYZE_ONLY path can
    never reach it.
    """
    from lr_ai_exposure.apply import apply_exposure_deltas

    return apply_exposure_deltas(job_dir, selection_path, decisions, settings)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the lr-ai-exposure CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    job_id = "unknown"
    mode = "ANALYZE_ONLY"
    decisions_path = ""
    evidence_path = ""
    apply_evidence = None
    decision_count = 0
    applied_count = 0

    def _fail(msg: str) -> int:
        print(f"ERROR: {msg}", file=sys.stderr)
        _write_bridge_result(args.bridge_result, {
            "protocol_version": "1.0",
            "status": "error",
            "job_id": job_id,
            "mode": mode,
            "decision_count": decision_count,
            "applied": applied_count,
            "ai_decisions": str(decisions_path) if decisions_path else "",
            "analysis_evidence": str(evidence_path) if evidence_path else "",
            "apply_evidence": str(apply_evidence) if apply_evidence else None,
            "error": msg,
        })
        return 1

    root = Path.cwd()
    try:
        settings = load_config(root)
    except ConfigError as exc:
        return _fail(str(exc))

    if args.check_config:
        summary = {
            "status": "ok",
            "dry_run": settings["dry_run"],
            "maximum_delta_ev": settings["maximum_delta_ev"],
            "minimum_apply_confidence": settings["minimum_apply_confidence"],
            "preview_size": settings["preview_size"],
            "runtime_directory": settings["runtime_directory"],
        }
        print(json.dumps(summary, indent=2))
        return 0

    try:
        mode = _select_mode(args)
    except ConfigError as exc:
        return _fail(str(exc))

    if not args.selection or not args.lrdata:
        parser.print_help()
        return 0

    selection_path = args.selection.resolve()
    lrdata_path = args.lrdata.resolve()

    if not selection_path.exists():
        return _fail(f"Selection file not found at {selection_path}")

    if not lrdata_path.exists():
        return _fail(f"lrdata dir not found at {lrdata_path}")

    # 1. Handoff
    try:
        job_dir, manifest = _run_handoff(settings, root, selection_path, lrdata_path)
        job_id = manifest.job_id
    except Exception as exc:
        return _fail(f"Handoff failed: {exc}")

    # Check two-key authorization contract
    apply_authorized = settings.get("apply_authorized", False)
    cli_authorized = args.authorize_apply == manifest.job_id

    if mode == "APPLY":
        if not apply_authorized or not cli_authorized:
            print("WARNING: Missing two-key authorization. Forcing ANALYZE_ONLY mode.", file=sys.stderr)
            mode = "ANALYZE_ONLY"
            settings["apply_authorized"] = False

    # 2. AI Judgment (Single-Pass) — validated settings flow through.
    try:
        decisions = _run_analysis(manifest, job_dir, settings)
        decision_count = len(decisions)
    except Exception as exc:
        return _fail(f"AI Judgment failed: {exc}")

    # 3. Canonical analysis artifacts (always written).
    try:
        dp, ep = _write_artifacts(
            job_dir, manifest, decisions, settings, mode
        )
        decisions_path = str(dp)
        evidence_path = str(ep)
    except Exception as exc:
        return _fail(f"Artifact write failed: {exc}")

    # 4. Apply — only reachable in --apply mode. The apply layer is
    #    imported lazily; ANALYZE_ONLY cannot reach this code path.
    results: dict | None = None
    if mode == "APPLY":
        try:
            results = _run_apply(job_dir, selection_path, decisions, settings)
            applied_count = results.get("applied", 0)
            apply_evidence = str(job_dir / "apply-evidence.json")
        except Exception as exc:
            return _fail(f"Apply failed: {exc}")

    # 5. Result recording.
    log_content = (
        f"Job processed: {job_dir.name}\n"
        f"Mode: {mode}\n"
        f"Decisions: {decision_count}\n"
        f"Applied: {applied_count}\n"
        f"Skipped: {results['skipped'] if results else 0}\n"
        f"Errors: {results['errors'] if results else 0}\n"
    )
    (job_dir / "run.log").write_text(log_content, encoding="utf-8")

    res = {
        "protocol_version": "1.0",
        "status": "ok",
        "job_id": job_id,
        "mode": mode,
        "decision_count": decision_count,
        "applied": applied_count,
        "ai_decisions": str(decisions_path),
        "analysis_evidence": str(evidence_path),
        "apply_evidence": str(apply_evidence) if apply_evidence else None,
        "error": None,
    }
    _write_bridge_result(args.bridge_result, res)

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
