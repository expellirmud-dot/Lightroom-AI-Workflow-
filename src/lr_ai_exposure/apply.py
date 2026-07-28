import json
from pathlib import Path
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.xmp import read_exposure_2012, write_exposure_2012
from lr_ai_exposure.apply_transaction import execute_apply_transaction, RollbackFatalError

import json
from pathlib import Path
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.xmp import read_exposure_2012, write_exposure_2012
from lr_ai_exposure.apply_transaction import execute_apply_transaction, RollbackFatalError

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
    transaction_evidences = []
    settled_ids = set()
    
    evidence_file = job_dir / "apply-evidence.json"
    if evidence_file.exists():
        try:
            with open(evidence_file, "r", encoding="utf-8") as f:
                prev_ev = json.load(f)
                for res in prev_ev.get("results", []):
                    transaction_evidences.append(res)
                    settled_ids.add(res.get("image_id"))
                    
                    # Update results counts
                    st = res.get("status")
                    if st == "APPLIED_VERIFIED":
                        results["applied"] += 1
                    elif st == "PROPOSED":
                        results["proposed"] += 1
                    elif st == "SKIPPED":
                        results["skipped"] += 1
                    elif st.startswith("FAILED_") or st == "ROLLBACK_FAILED_FATAL":
                        results["errors"] += 1
        except Exception as e:
            raise ValueError(f"Corrupted checkpoint: {e}")
            
    def _checkpoint():
        evidence_payload = {
            "job_id": manifest.job_id,
            "results": transaction_evidences
        }
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_payload, f, indent=2)

    for decision in decisions:
        img_id = decision.image_id
        
        if img_id in settled_ids:
            continue
            
        def _record_skip(msg: str):
            results["skipped"] += 1
            results["details"].append(f"Skipped {img_id}: {msg}")
            transaction_evidences.append({"image_id": img_id, "status": "SKIPPED", "message": msg})
            _checkpoint()
            
        def _record_error(msg: str, status: str = "FAILED_BEFORE_REPLACE"):
            results["errors"] += 1
            results["details"].append(f"Error {img_id}: {msg}")
            transaction_evidences.append({"image_id": img_id, "status": status, "message": msg})
            _checkpoint()

        if not dry_run and img_id not in approved_ids:
            _record_skip("Not in approved_image_ids allowlist")
            continue
        
        sel_item = selection_map[img_id]
        manifest_entry = manifest_map[img_id]
        
        if sel_item.get("uuid") != manifest_entry.uuid:
            _record_error("Cache UUID mismatch")
            continue
            
        raw_path = Path(sel_item["path"]).resolve()
        xmp_path = raw_path.with_suffix(".xmp").resolve()
        
        if raw_path.name != manifest_entry.raw_path.split("/")[-1] and raw_path.name != Path(manifest_entry.raw_path).name:
            _record_error("canonical raw_path mismatch")
            continue
            
        if xmp_path.name != manifest_entry.source_xmp_path.split("/")[-1] and xmp_path.name != Path(manifest_entry.source_xmp_path).name:
            _record_error("canonical source_xmp_path mismatch")
            continue
            
        if manifest_entry.backup_relative_path != f"xmp_backups/{xmp_path.name}":
            _record_error("backup_relative_path mismatch")
            continue
        
        # 3. Strict path containment
        try:
            raw_path.relative_to(pilot_root_path)
            xmp_path.relative_to(pilot_root_path)
        except ValueError:
            _record_error("Path escapes approved_pilot_root")
            continue
        
        # 4. Enforce confidence, review, risk gates
        if decision.relevance_verdict != Verdict.KEEP or decision.quality_verdict != Verdict.KEEP:
            _record_skip(f"Not KEEP ({decision.relevance_verdict}, {decision.quality_verdict})")
            continue
            
        if decision.confidence < min_conf:
            _record_skip(f"Confidence {decision.confidence} below {min_conf}")
            continue
            
        if decision.highlight_risk or decision.shadow_risk:
            _record_skip("Risk flags present")
            continue
            
        if not (-max_ev <= decision.delta_ev <= max_ev):
            _record_error(f"delta_ev {decision.delta_ev} out of bounds")
            continue
            
        if not xmp_path.exists():
            _record_error(f"Source XMP not found {xmp_path}")
            continue
            
        backup_dir = job_dir / "xmp_backups"
        
        try:
            old_exposure = read_exposure_2012(xmp_path)
            new_exposure = old_exposure + decision.delta_ev
            
            # Enforce absolute EV gate [-5, 5] typical Lightroom
            if not (-5.0 <= new_exposure <= 5.0):
                raise ValueError(f"Absolute exposure {new_exposure} is outside [-5, 5]")
            
            evidence = execute_apply_transaction(xmp_path, new_exposure, backup_dir, dry_run=dry_run)
            evidence["image_id"] = img_id
            transaction_evidences.append(evidence)
            
            status = evidence["status"]
            if status == "PROPOSED":
                results["proposed"] += 1
                results["details"].append(f"Proposed {img_id}: {evidence['message']}")
            elif status == "APPLIED_VERIFIED":
                results["applied"] += 1
                results["details"].append(f"Applied {img_id}: {evidence['message']} (written for Lightroom manual import)")
            else:
                results["errors"] += 1
                results["details"].append(f"Error {img_id}: {status} - {evidence['message']}")
            
            _checkpoint()
            
        except RollbackFatalError as e:
            results["errors"] += 1
            results["details"].append(f"FATAL {img_id}: {e}")
            transaction_evidences.append({"image_id": img_id, "status": "ROLLBACK_FAILED_FATAL", "message": str(e)})
            _checkpoint()
            raise # Stop the batch
        except Exception as e:
            _record_error(str(e))

    return results
