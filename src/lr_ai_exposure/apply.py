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
        
    if manifest.job_id != selection.get("job_id"):
        raise ValueError(f"Job ID mismatch: manifest {manifest.job_id} != selection {selection.get('job_id')}")
        
    identities = selection.get("photos", [])
    selection_map = {str(item["id_local"]): item for item in identities}
    manifest_map = {str(entry.image_id): entry for entry in manifest.entries}
    
    manifest_ids = set(manifest_map.keys())
    selection_ids = set(selection_map.keys())
    decision_ids = {str(d.image_id) for d in decisions}
    
    if len(decision_ids) != len(decisions):
        raise ValueError("Decisions contain duplicate image_ids")
        
    if manifest_ids != selection_ids or manifest_ids != decision_ids:
        raise ValueError("Exact ID set reconciliation failed between manifest, selection, and decisions")
    
    results = {
        "applied": 0,
        "proposed": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }
    
    dry_run = config.get("dry_run", True)
    apply_authorized = config.get("apply_authorized", False)
    approved_ids = config.get("approved_image_ids", [])
    approved_root = config.get("approved_pilot_root", "")
    max_ev = config.get("maximum_delta_ev", 3.0)
    min_conf = config.get("minimum_apply_confidence", 0.8)
    
    if not approved_ids:
        raise ValueError("approved_image_ids is empty. Failing closed.")
        
    if not approved_root:
        raise ValueError("approved_pilot_root is empty. Failing closed.")
        
    if not dry_run and not apply_authorized:
        results["details"].append("DRY_RUN_ENFORCED: apply_authorized is false. Forcing dry_run=True.")
        dry_run = True
    
    pilot_root_path = Path(approved_root).resolve()
    
    for decision in decisions:
        img_id = decision.image_id
        
        sel_item = selection_map[img_id]
        manifest_entry = manifest_map[img_id]
        
        if sel_item.get("uuid") != manifest_entry.uuid:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: Cache UUID mismatch")
            continue
            
        raw_path = Path(sel_item["path"]).resolve()
        xmp_path = raw_path.with_suffix(".xmp").resolve()
        
        if raw_path.name != manifest_entry.raw_path:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: raw_path mismatch")
            continue
            
        if manifest_entry.xmp_path != f"xmp_backups/{xmp_path.name}":
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: xmp_path mismatch")
            continue
        
        # 2. Reject unapproved images
        if img_id not in approved_ids:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Not in approved_image_ids allowlist")
            continue
            
        # 3. Strict path containment
        try:
            raw_path.relative_to(pilot_root_path)
            xmp_path.relative_to(pilot_root_path)
        except ValueError:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: Path escapes approved_pilot_root")
            continue
        
        # 4. Enforce confidence, review, risk gates
        if decision.relevance_verdict != Verdict.KEEP or decision.quality_verdict != Verdict.KEEP:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Not KEEP ({decision.relevance_verdict}, {decision.quality_verdict})")
            continue
            
        if decision.confidence < min_conf:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Confidence {decision.confidence} below {min_conf}")
            continue
            
        if decision.highlight_risk or decision.shadow_risk:
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: Risk flags present")
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
            
            if dry_run:
                results["proposed"] += 1
                results["details"].append(f"Proposed {img_id}: {msg}")
            else:
                results["applied"] += 1
                results["details"].append(f"Applied {img_id}: {msg} (written for Lightroom manual import)")
            
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: {e}")
            
    return results
