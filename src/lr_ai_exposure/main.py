"""One-shot CLI for Lightroom AI Exposure Assist MVP scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lr_ai_exposure.config import load_config, ConfigError
from lr_ai_exposure.job import read_manifest, write_manifest
from lr_ai_exposure.handoff import handoff_job
from lr_ai_exposure.ai_judge import analyze_job_single_pass
from lr_ai_exposure.apply import apply_exposure_deltas


def main(argv: list[str] | None = None) -> int:
    """Entry point for the lr-ai-exposure CLI."""
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
        "--selection",
        type=Path,
        help="Path to selection.json from Lightroom",
    )
    parser.add_argument(
        "--lrdata",
        type=Path,
        help="Path to Lightroom Previews.lrdata directory",
    )
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

    if not args.selection or not args.lrdata:
        parser.print_help()
        return 0
        
    selection_path = args.selection.resolve()
    lrdata_path = args.lrdata.resolve()
    
    if not selection_path.exists():
        print(f"ERROR: Selection file not found at {selection_path}", file=sys.stderr)
        return 1
        
    if not lrdata_path.exists():
        print(f"ERROR: lrdata dir not found at {lrdata_path}", file=sys.stderr)
        return 1
        
    # 1. Handoff
    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir
        
    try:
        job_id = handoff_job(str(runtime_dir), str(lrdata_path), str(selection_path))
        job_dir = runtime_dir / "jobs" / job_id
        manifest = read_manifest(job_dir)
    except Exception as exc:
        print(f"ERROR: Handoff failed: {exc}", file=sys.stderr)
        return 1

        
    # 2. AI Judgment (Single-Pass)
    try:
        decisions = analyze_job_single_pass(manifest)
        
        # Write ai-decisions.json
        decisions_dict = {
            d.image_id: {
                "relevance_verdict": d.relevance_verdict,
                "quality_verdict": d.quality_verdict,
                "delta_ev": d.delta_ev,
                "confidence": d.confidence,
                "reason": d.reason
            } for d in decisions
        }
        (job_dir / "ai-decisions.json").write_text(json.dumps(decisions_dict, indent=2))
    except Exception as exc:
        print(f"ERROR: AI Judgment failed: {exc}", file=sys.stderr)
        return 1
        
    # 3. Apply Exposure Deltas
    try:
        results = apply_exposure_deltas(
            job_dir, 
            selection_path, 
            decisions, 
            dry_run=settings.get("dry_run", True),
            apply_authorized=settings.get("apply_authorized", False)
        )
    except Exception as exc:
        print(f"ERROR: Apply failed: {exc}", file=sys.stderr)
        return 1
        
    # 4. Result Recording
    (job_dir / "result.json").write_text(json.dumps(results, indent=2))
    
    log_content = f"Job processed: {job_dir.name}\n"
    log_content += f"Applied: {results['applied']}\n"
    log_content += f"Skipped: {results['skipped']}\n"
    log_content += f"Errors: {results['errors']}\n"
    (job_dir / "run.log").write_text(log_content)
    
    print(log_content)
    return 0

if __name__ == "__main__":
    sys.exit(main())
