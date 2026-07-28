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

    root = Path.cwd()
    try:
        settings = load_config(root)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

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
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not args.selection or not args.lrdata:
        parser.print_help()
        return 0

    selection_path = args.selection.resolve()
    lrdata_path = args.lrdata.resolve()

    if not selection_path.exists():
        print(
            f"ERROR: Selection file not found at {selection_path}",
            file=sys.stderr,
        )
        return 1

    if not lrdata_path.exists():
        print(f"ERROR: lrdata dir not found at {lrdata_path}", file=sys.stderr)
        return 1

    # 1. Handoff
    try:
        job_dir, manifest = _run_handoff(settings, root, selection_path, lrdata_path)
    except Exception as exc:
        print(f"ERROR: Handoff failed: {exc}", file=sys.stderr)
        return 1

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
    except Exception as exc:
        print(f"ERROR: AI Judgment failed: {exc}", file=sys.stderr)
        return 1

    # 3. Canonical analysis artifacts (always written).
    try:
        decisions_path, evidence_path = _write_artifacts(
            job_dir, manifest, decisions, settings, mode
        )
    except Exception as exc:
        print(f"ERROR: Artifact write failed: {exc}", file=sys.stderr)
        return 1

    # 4. Apply — only reachable in --apply mode. The apply layer is
    #    imported lazily; ANALYZE_ONLY cannot reach this code path.
    results: dict | None = None
    if mode == "APPLY":
        try:
            results = _run_apply(job_dir, selection_path, decisions, settings)
        except Exception as exc:
            print(f"ERROR: Apply failed: {exc}", file=sys.stderr)
            return 1

    # 5. Result recording.
    log_content = (
        f"Job processed: {job_dir.name}\n"
        f"Mode: {mode}\n"
        f"Decisions: {len(decisions)}\n"
        f"Applied: {results['applied'] if results else 0}\n"
        f"Skipped: {results['skipped'] if results else 0}\n"
        f"Errors: {results['errors'] if results else 0}\n"
    )
    (job_dir / "run.log").write_text(log_content, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "job_id": manifest.job_id,
                "mode": mode,
                "decision_count": len(decisions),
                "ai_decisions": str(decisions_path),
                "analysis_evidence": str(evidence_path),
                "applied": results["applied"] if results else 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
