"""One-shot CLI for Lightroom AI Exposure Assist MVP scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lr_ai_exposure.config import load_config, ConfigError
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.preview import validate_previews
from lr_ai_exposure.judge import process_mock_decisions
from lr_ai_exposure.quality_safety import apply_quality_safety_rules
from lr_ai_exposure.image_triage import validate_triage_decision, TriageDecision
from lr_ai_exposure.xmp import write_exposure_2012, XmpError


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
        "--job",
        type=Path,
        help="Path to the job directory",
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

    if not args.job:
        parser.print_help()
        return 0
        
    job_dir = args.job.resolve()
    manifest_path = job_dir / "manifest.json"
    
    if not manifest_path.exists():
        print(f"ERROR: Job manifest not found at {manifest_path}", file=sys.stderr)
        return 1
        
    try:
        manifest = read_manifest(job_dir)
    except Exception as exc:
        print(f"ERROR: Failed to load manifest: {exc}", file=sys.stderr)
        return 1
        
    val_results = validate_previews(manifest, job_dir)
    valid_ids = {r.entry.image_id for r in val_results if r.valid}
    invalid_results = [r for r in val_results if not r.valid]
    
    # Run mock judge on whole manifest
    raw_decisions_list = process_mock_decisions(manifest)
    raw_decisions = {d.image_id: d for d in raw_decisions_list}
    
    results = {
        "applied": [],
        "skipped": [],
        "reviewed": [],
        "errors": []
    }
    
    # Track decisions for output
    final_decisions = {}
    
    # Process decisions
    for entry in manifest.entries:
        image_id = entry.image_id
        xmp_path = job_dir / entry.xmp_path
        backup_dir = job_dir / "xmp-backup"
        
        if image_id not in valid_ids:
            # handled later in errors
            continue
            
        if image_id not in raw_decisions:
            results["errors"].append({"id": image_id, "reason": "No decision returned"})
            continue
            
        exp_decision = raw_decisions[image_id]
        
        # mock triage
        triage_dict = {
            "image_id": image_id,
            "relevance_class": "KEEP_PRIMARY",
            "quality_action": "APPLY",
            "event_relation": "same_event",
            "test_shot_likelihood": "none",
            "accidental_likelihood": "none",
            "quality_flags": [],
            "duplicate_of": "",
            "confidence": exp_decision.confidence,
            "reason": "Mock triage for dry run"
        }
        
        try:
            triage_decision = validate_triage_decision(triage_dict)
            safe_triage = apply_quality_safety_rules(triage_decision)
        except Exception as exc:
            results["errors"].append({"id": image_id, "reason": f"Validation failed: {exc}"})
            continue
            
        final_decisions[image_id] = {
            "delta_ev": exp_decision.delta_ev,
            "confidence": exp_decision.confidence,
            "reason": exp_decision.reason
        }
        
        if safe_triage.quality_action.value == "SKIP":
            results["skipped"].append({"id": image_id, "reason": "Triage skip"})
            continue
            
        if safe_triage.quality_action.value == "REVIEW" or exp_decision.confidence < settings["minimum_apply_confidence"]:
            results["reviewed"].append({"id": image_id, "reason": "Low confidence or review required"})
            continue
            
        # Write XMP
        try:
            if xmp_path.exists():
                msg = write_exposure_2012(xmp_path, exp_decision.delta_ev, backup_dir, dry_run=settings["dry_run"])
                results["applied"].append({"id": image_id, "msg": msg})
            else:
                results["errors"].append({"id": image_id, "reason": f"XMP not found at {xmp_path}"})
        except XmpError as exc:
            results["errors"].append({"id": image_id, "reason": str(exc)})
            
    for item in invalid_results:
        results["errors"].append({"id": item.entry.image_id, "reason": f"Invalid preview: {item.error}"})
        
    # Write ai-decisions.json
    (job_dir / "ai-decisions.json").write_text(json.dumps(final_decisions, indent=2))
    
    # Write result.json
    (job_dir / "result.json").write_text(json.dumps(results, indent=2))
    
    # Write run.log
    log_content = f"Job processed: {job_dir.name}\n"
    log_content += f"Applied: {len(results['applied'])}\n"
    log_content += f"Skipped: {len(results['skipped'])}\n"
    log_content += f"Reviewed: {len(results['reviewed'])}\n"
    log_content += f"Errors: {len(results['errors'])}\n"
    (job_dir / "run.log").write_text(log_content)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
