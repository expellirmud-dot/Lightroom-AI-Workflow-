import hashlib
from pathlib import Path

from lr_ai_exposure.xmp import backup_xmp, rollback_xmp, write_exposure_2012, read_exposure_2012

class ApplyTransactionError(Exception):
    pass

class RollbackFatalError(Exception):
    pass

def execute_apply_transaction(
    xmp_path: Path,
    new_exposure: float,
    backup_dir: Path,
    dry_run: bool
) -> dict:
    """
    Executes the apply transaction for a single XMP file.
    Returns a dict with evidence.
    """
    evidence = {
        "xmp_path": str(xmp_path),
        "status": "PROPOSED",
        "dry_run": dry_run,
        "original_sha256": None,
        "backup_sha256": None,
        "final_sha256": None,
        "rollback_sha256": None,
        "message": ""
    }
    
    if not xmp_path.exists():
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = "Source XMP not found"
        return evidence
        
    try:
        original_bytes = xmp_path.read_bytes()
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        evidence["original_sha256"] = original_sha256
    except OSError as e:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Failed to read original XMP: {e}"
        return evidence
        
    if dry_run:
        try:
            msg = write_exposure_2012(xmp_path, new_exposure, backup_dir, dry_run=True)
            evidence["message"] = msg
            evidence["status"] = "PROPOSED"
        except Exception as e:
            evidence["status"] = "FAILED_BEFORE_REPLACE"
            evidence["message"] = str(e)
        return evidence
        
    # Real write - Transaction boundary starts
    try:
        backup_path, backup_sha256 = backup_xmp(xmp_path, backup_dir, dry_run=False)
        evidence["backup_sha256"] = backup_sha256
    except Exception as e:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Backup failed: {e}"
        return evidence
        
    if backup_sha256 != original_sha256:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = "Backup SHA-256 does not match original SHA-256"
        return evidence

    try:
        msg = write_exposure_2012(xmp_path, new_exposure, backup_dir, dry_run=False, skip_backup=True)
    except Exception as e:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Write failed before replace: {e}"
        # verify it's still original
        current_sha = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
        evidence["final_sha256"] = current_sha
        return evidence

    # Post-replace validation
    try:
        post_val = read_exposure_2012(xmp_path)
        if abs(post_val - new_exposure) > 0.001:
            raise ValueError(f"Post-replace mismatch: expected {new_exposure}, got {post_val}")
            
        evidence["final_sha256"] = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
        evidence["status"] = "APPLIED_VERIFIED"
        evidence["message"] = msg
        return evidence
        
    except Exception as e:
        # Automatic rollback
        try:
            rollback_xmp(xmp_path, backup_path, backup_sha256)
            evidence["rollback_sha256"] = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
            evidence["status"] = "FAILED_AFTER_REPLACE_ROLLED_BACK"
            evidence["message"] = f"Post-replace validation failed: {e}. Rolled back successfully."
            return evidence
        except Exception as rb_e:
            evidence["status"] = "ROLLBACK_FAILED_FATAL"
            evidence["message"] = f"Rollback failed after post-replace validation error ({e}): {rb_e}"
            raise RollbackFatalError(evidence["message"])
