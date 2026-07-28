import json
from pathlib import Path
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.xmp import read_exposure_2012, write_exposure_2012

def apply_exposure_deltas(job_dir: Path, selection_json_path: Path, decisions: list[SinglePassDecision], dry_run: bool = True) -> dict:
    """
    Applies approved AI exposure deltas to original XMP files based on decisions.
    Requires selection.json to locate original XMP files.
    """
    manifest = read_manifest(job_dir)
    
    with open(selection_json_path, "r", encoding="utf-8") as f:
        selection = json.load(f)
        
    identities = selection.get("photos", [])
    id_to_original_path = {str(item["id_local"]): item.get("path") for item in identities}
    
    results = {
        "applied": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }
    
    for decision in decisions:
        if decision.relevance_verdict != Verdict.KEEP or decision.quality_verdict != Verdict.KEEP:
            results["skipped"] += 1
            results["details"].append(f"Skipped {decision.image_id}: Not KEEP ({decision.relevance_verdict}, {decision.quality_verdict})")
            continue
            
        original_raw = id_to_original_path.get(decision.image_id)
        if not original_raw:
            results["errors"] += 1
            results["details"].append(f"Error {decision.image_id}: Could not find original path in selection.json")
            continue
            
        raw_path = Path(original_raw)
        xmp_path = raw_path.with_suffix(".xmp")
        
        if not xmp_path.exists():
            results["errors"] += 1
            results["details"].append(f"Error {decision.image_id}: Source XMP not found {xmp_path}")
            continue
            
        backup_dir = job_dir / "xmp_backups"
        
        try:
            old_exposure = read_exposure_2012(xmp_path)
            new_exposure = old_exposure + decision.delta_ev
            
            msg = write_exposure_2012(xmp_path, new_exposure, backup_dir, dry_run=dry_run)
            results["applied"] += 1
            results["details"].append(f"Applied {decision.image_id}: {msg}")
            
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Error {decision.image_id}: {e}")
            
    return results
