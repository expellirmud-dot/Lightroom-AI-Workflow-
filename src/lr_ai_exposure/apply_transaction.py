"""Transactional XMP apply with backup, verification, and rollback evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from lr_ai_exposure.xmp import (
    backup_xmp,
    read_exposure_2012,
    rollback_xmp,
    write_exposure_2012,
)


class ApplyTransactionError(Exception):
    pass


class RollbackFatalError(Exception):
    pass


def execute_apply_transaction(
    xmp_path: Path,
    new_exposure: float,
    backup_dir: Path,
    dry_run: bool,
) -> dict:
    """Execute one XMP transaction and return durable verification evidence."""
    evidence = {
        "xmp_path": str(xmp_path),
        "backup_path": None,
        "status": "PROPOSED",
        "dry_run": dry_run,
        "original_sha256": None,
        "backup_sha256": None,
        "final_sha256": None,
        "rollback_sha256": None,
        "message": "",
    }

    if not xmp_path.exists():
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = "Source XMP not found"
        return evidence

    try:
        original_bytes = xmp_path.read_bytes()
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        evidence["original_sha256"] = original_sha256
    except OSError as exc:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Failed to read original XMP: {exc}"
        return evidence

    if dry_run:
        try:
            evidence["message"] = write_exposure_2012(
                xmp_path,
                new_exposure,
                backup_dir,
                dry_run=True,
            )
            evidence["status"] = "PROPOSED"
        except Exception as exc:
            evidence["status"] = "FAILED_BEFORE_REPLACE"
            evidence["message"] = str(exc)
        return evidence

    try:
        backup_path, backup_sha256 = backup_xmp(
            xmp_path,
            backup_dir,
            dry_run=False,
        )
        evidence["backup_path"] = str(backup_path)
        evidence["backup_sha256"] = backup_sha256
    except Exception as exc:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Backup failed: {exc}"
        return evidence

    if backup_sha256 != original_sha256:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = "Backup SHA-256 does not match original SHA-256"
        return evidence

    try:
        message = write_exposure_2012(
            xmp_path,
            new_exposure,
            backup_dir,
            dry_run=False,
            skip_backup=True,
        )
    except Exception as exc:
        evidence["status"] = "FAILED_BEFORE_REPLACE"
        evidence["message"] = f"Write failed before replace: {exc}"
        evidence["final_sha256"] = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
        return evidence

    try:
        post_value = read_exposure_2012(xmp_path)
        if abs(post_value - new_exposure) > 0.001:
            raise ValueError(
                f"Post-replace mismatch: expected {new_exposure}, got {post_value}"
            )
        evidence["final_sha256"] = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
        evidence["status"] = "APPLIED_VERIFIED"
        evidence["message"] = message
        return evidence
    except Exception as exc:
        try:
            rollback_xmp(xmp_path, backup_path, backup_sha256)
            evidence["rollback_sha256"] = hashlib.sha256(
                xmp_path.read_bytes()
            ).hexdigest()
            evidence["status"] = "FAILED_AFTER_REPLACE_ROLLED_BACK"
            evidence["message"] = (
                f"Post-replace validation failed: {exc}. "
                "Rolled back successfully."
            )
            return evidence
        except Exception as rollback_exc:
            evidence["status"] = "ROLLBACK_FAILED_FATAL"
            evidence["message"] = (
                "Rollback failed after post-replace validation error "
                f"({exc}): {rollback_exc}"
            )
            raise RollbackFatalError(evidence["message"])
