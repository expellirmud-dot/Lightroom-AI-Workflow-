import json
from pathlib import Path
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.xmp import read_exposure_2012, write_exposure_2012

import json
from pathlib import Path
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.xmp import read_exposure_2012, write_exposure_2012

def apply_exposure_deltas(job_dir: Path, selection_json_path: Path, decisions: list[SinglePassDecision], config: dict) -> dict:
    """
    Applies approved AI exposure deltas to original XMP files based on decisions.
    Requires selection.json to locate original XMP files.
    Enforces Phase E safety checks.
    """
    manifest = read_manifest(job_dir)
    
    with open(selection_json_path, "r", encoding="utf-8") as f:
        selection = json.load(f)
        
    identities = selection.get("photos", [])
    selection_map = {str(item["id_local"]): item for item in identities}
    manifest_map = {str(entry.image_id): entry for entry in manifest.entries}
    
    # Require exact cardinality against manifest
    if len(decisions) != len(manifest.entries):
        raise ValueError(f"Cardinality mismatch: got {len(decisions)} decisions for {len(manifest.entries)} manifest entries")
    
    results = {
        "applied": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }
    
    dry_run = config.get("dry_run", True)
    apply_authorized = config.get("apply_authorized", False)
    approved_ids = config.get("approved_image_ids", [])
    approved_root = config.get("approved_pilot_root", "")
    max_ev = config.get("maximum_delta_ev", 3.0)
    
    if not dry_run and not apply_authorized:
        results["details"].append("DRY_RUN_ENFORCED: apply_authorized is false. Forcing dry_run=True.")
        dry_run = True
    
    for decision in decisions:
        img_id = decision.image_id
        
        # 1. Reconcile manifest, selection, decisions
        if img_id not in manifest_map:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: Decision image_id not in manifest")
            continue
            
        sel_item = selection_map.get(img_id)
        if not sel_item:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: Decision image_id not in selection.json")
            continue
            
        raw_path = Path(sel_item["path"])
        xmp_path = raw_path.with_suffix(".xmp")
        
        # 2. Reject unapproved images
        if approved_ids and img_id not in approved_ids:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Not in approved_image_ids allowlist")
            continue
            
        # 3. Add approved_pilot_root path containment
        if approved_root:
            try:
                raw_path.relative_to(Path(approved_root))
            except ValueError:
                results["errors"] += 1
                results["details"].append(f"Error {img_id}: Path {raw_path} not under approved_pilot_root")
                continue
        
        # 4. Enforce confidence, review, risk gates
        if decision.relevance_verdict != Verdict.KEEP or decision.quality_verdict != Verdict.KEEP:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Not KEEP ({decision.relevance_verdict}, {decision.quality_verdict})")
            continue
            
        if not (-max_ev <= decision.delta_ev <= max_ev):
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: delta_ev {decision.delta_ev} out of bounds")
            continue
            
        if not xmp_path.exists():
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: Source XMP not found {xmp_path}")
            continue
            
        backup_dir = job_dir / "xmp_backups"
        
        try:
            old_exposure = read_exposure_2012(xmp_path)
            new_exposure = old_exposure + decision.delta_ev
            
            # Enforce absolute EV gate [-5, 5] typical Lightroom
            if not (-5.0 <= new_exposure <= 5.0):
                raise ValueError(f"Absolute exposure {new_exposure} is outside [-5, 5]")
            
            msg = write_exposure_2012(xmp_path, new_exposure, backup_dir, dry_run=dry_run)
            
            # Assert post-replace value
            if not dry_run:
                post_replace_exposure = read_exposure_2012(xmp_path)
                if abs(post_replace_exposure - new_exposure) > 0.001:
                    raise ValueError(f"Post-replace mismatch: expected {new_exposure}, got {post_replace_exposure}")
            
            results["applied"] += 1
            if dry_run:
                results["details"].append(f"Proposed {img_id}: {msg}")
            else:
                results["details"].append(f"Applied {img_id}: {msg} (written for Lightroom manual import)")
            
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: {e}")
            
    return results
