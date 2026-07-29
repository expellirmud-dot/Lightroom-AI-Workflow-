"""Guarded batch application of validated exposure decisions."""

from __future__ import annotations

import json
from pathlib import Path

from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.apply_transaction import execute_apply_transaction, RollbackFatalError
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.xmp import read_exposure_2012


def _atomic_checkpoint(path: Path, payload: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def apply_exposure_deltas(
    job_dir: Path,
    selection_json_path: Path,
    decisions: list[SinglePassDecision],
    config: dict,
) -> dict:
    """Apply safe decisions to the exact XMP targets recorded by a saved job.

    Manifest and selection identity are reconciled across the whole selected
    folder. Decisions are required only for ``FOUND`` preview entries; entries
    whose previews could not be extracted receive explicit terminal skip
    records instead of blocking unrelated images.
    """
    job_dir = Path(job_dir)
    manifest = read_manifest(job_dir)

    with open(selection_json_path, "r", encoding="utf-8") as handle:
        selection = json.load(handle)

    if manifest.job_id != selection.get("job_id"):
        raise ValueError(
            f"Job ID mismatch: manifest {manifest.job_id} != selection {selection.get('job_id')}"
        )

    identities = selection.get("photos", [])
    selection_map = {str(item["id_local"]): item for item in identities}
    all_manifest_map = {str(entry.image_id): entry for entry in manifest.entries}
    found_manifest_map = {
        str(entry.image_id): entry
        for entry in manifest.entries
        if entry.extraction_status == "FOUND"
    }

    all_manifest_ids = set(all_manifest_map)
    selection_ids = set(selection_map)
    decision_ids = {str(decision.image_id) for decision in decisions}

    if len(selection_map) != len(identities):
        raise ValueError("Selection contains duplicate id_local values")
    if len(decision_ids) != len(decisions):
        raise ValueError("Decisions contain duplicate image_ids")
    if all_manifest_ids != selection_ids:
        raise ValueError(
            "Exact ID set reconciliation failed between full manifest and selection"
        )
    if set(found_manifest_map) != decision_ids:
        raise ValueError(
            "Exact ID set reconciliation failed between FOUND manifest entries and decisions"
        )

    results = {
        "applied": 0,
        "proposed": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    dry_run = bool(config.get("dry_run", True))
    apply_authorized = bool(config.get("apply_authorized", False))
    approved_ids = {str(value) for value in config.get("approved_image_ids", [])}
    approved_root = str(config.get("approved_pilot_root", ""))
    max_ev = float(config.get("maximum_delta_ev", 3.0))
    min_conf = float(config.get("minimum_apply_confidence", 0.8))

    if not dry_run and not apply_authorized:
        results["details"].append(
            "DRY_RUN_ENFORCED: apply_authorized is false. Forcing dry_run=True."
        )
        dry_run = True

    pilot_root_path: Path | None = None
    if not dry_run:
        if not approved_root:
            raise ValueError("approved_pilot_root is empty. Failing closed.")
        pilot_root_path = Path(approved_root).resolve()

    transaction_evidences: list[dict] = []
    settled_ids: set[str] = set()
    evidence_file = job_dir / "apply-evidence.json"

    if evidence_file.exists():
        try:
            previous = json.loads(evidence_file.read_text(encoding="utf-8"))
            for evidence in previous.get("results", []):
                if not isinstance(evidence, dict):
                    raise ValueError("checkpoint result is not an object")
                transaction_evidences.append(evidence)
                image_id = evidence.get("image_id")
                if image_id is not None:
                    settled_ids.add(str(image_id))
                status = str(evidence.get("status", ""))
                if status == "APPLIED_VERIFIED":
                    results["applied"] += 1
                elif status == "PROPOSED":
                    results["proposed"] += 1
                elif status.startswith("SKIPPED"):
                    results["skipped"] += 1
                elif status.startswith("FAILED_") or status == "ROLLBACK_FAILED_FATAL":
                    results["errors"] += 1
        except Exception as exc:
            raise ValueError(f"Corrupted checkpoint: {exc}") from exc

    def checkpoint() -> None:
        _atomic_checkpoint(
            evidence_file,
            {"job_id": manifest.job_id, "results": transaction_evidences},
        )

    def record_skip(image_id: str, message: str, status: str = "SKIPPED") -> None:
        results["skipped"] += 1
        results["details"].append(f"Skipped {image_id}: {message}")
        transaction_evidences.append(
            {"image_id": image_id, "status": status, "message": message}
        )
        checkpoint()

    def record_error(
        image_id: str,
        message: str,
        status: str = "FAILED_BEFORE_REPLACE",
    ) -> None:
        results["errors"] += 1
        results["details"].append(f"Error {image_id}: {message}")
        transaction_evidences.append(
            {"image_id": image_id, "status": status, "message": message}
        )
        checkpoint()

    for entry in manifest.entries:
        image_id = str(entry.image_id)
        if image_id in settled_ids or entry.extraction_status == "FOUND":
            continue
        record_skip(
            image_id,
            f"Preview extraction status is {entry.extraction_status}",
            "SKIPPED_PREVIEW_UNAVAILABLE",
        )
        settled_ids.add(image_id)

    for decision in decisions:
        image_id = str(decision.image_id)
        if image_id in settled_ids:
            continue

        selection_item = selection_map[image_id]
        manifest_entry = found_manifest_map[image_id]

        if selection_item.get("uuid") != manifest_entry.uuid:
            record_error(image_id, "Cache UUID mismatch")
            settled_ids.add(image_id)
            continue

        raw_path = Path(selection_item["path"]).resolve()
        xmp_path = raw_path.with_suffix(".xmp").resolve()
        manifest_raw_path = Path(manifest_entry.raw_path).resolve()
        manifest_xmp_path = Path(manifest_entry.source_xmp_path).resolve()

        if raw_path != manifest_raw_path:
            record_error(image_id, "canonical raw_path mismatch")
            settled_ids.add(image_id)
            continue
        if xmp_path != manifest_xmp_path:
            record_error(image_id, "canonical source_xmp_path mismatch")
            settled_ids.add(image_id)
            continue
        if manifest_entry.backup_relative_path != f"xmp_backups/{xmp_path.name}":
            record_error(image_id, "backup_relative_path mismatch")
            settled_ids.add(image_id)
            continue

        if not dry_run:
            if image_id not in approved_ids:
                record_skip(image_id, "Not in approved_image_ids allowlist")
                settled_ids.add(image_id)
                continue
            assert pilot_root_path is not None
            try:
                raw_path.relative_to(pilot_root_path)
                xmp_path.relative_to(pilot_root_path)
            except ValueError:
                record_error(image_id, "Path escapes approved_pilot_root")
                settled_ids.add(image_id)
                continue

        if (
            decision.relevance_verdict != Verdict.KEEP
            or decision.quality_verdict != Verdict.KEEP
        ):
            record_skip(
                image_id,
                f"Not KEEP ({decision.relevance_verdict}, {decision.quality_verdict})",
            )
            settled_ids.add(image_id)
            continue
        if decision.confidence < min_conf:
            record_skip(
                image_id,
                f"Confidence {decision.confidence} below {min_conf}",
            )
            settled_ids.add(image_id)
            continue
        if decision.highlight_risk or decision.shadow_risk:
            record_skip(image_id, "Risk flags present")
            settled_ids.add(image_id)
            continue
        if not (-max_ev <= decision.delta_ev <= max_ev):
            record_error(image_id, f"delta_ev {decision.delta_ev} out of bounds")
            settled_ids.add(image_id)
            continue
        if abs(decision.delta_ev) < 1e-9:
            record_skip(
                image_id,
                "Validated delta_ev is 0.0; XMP left byte-identical",
                "SKIPPED_NO_CHANGE",
            )
            settled_ids.add(image_id)
            continue
        if not xmp_path.exists():
            record_error(image_id, f"Source XMP not found {xmp_path}")
            settled_ids.add(image_id)
            continue

        backup_dir = job_dir / "xmp_backups"
        try:
            old_exposure = read_exposure_2012(xmp_path)
            new_exposure = old_exposure + decision.delta_ev
            if not (-5.0 <= new_exposure <= 5.0):
                raise ValueError(
                    f"Absolute exposure {new_exposure} is outside [-5, 5]"
                )

            evidence = execute_apply_transaction(
                xmp_path,
                new_exposure,
                backup_dir,
                dry_run=dry_run,
            )
            evidence.update(
                {
                    "image_id": image_id,
                    "old_exposure": old_exposure,
                    "delta_ev": decision.delta_ev,
                    "new_exposure": new_exposure,
                }
            )
            transaction_evidences.append(evidence)

            status = str(evidence["status"])
            if status == "PROPOSED":
                results["proposed"] += 1
                results["details"].append(
                    f"Proposed {image_id}: {evidence['message']}"
                )
            elif status == "APPLIED_VERIFIED":
                results["applied"] += 1
                results["details"].append(
                    f"Applied {image_id}: {evidence['message']}"
                )
            else:
                results["errors"] += 1
                results["details"].append(
                    f"Error {image_id}: {status} - {evidence['message']}"
                )
            checkpoint()
            settled_ids.add(image_id)

        except RollbackFatalError as exc:
            transaction_evidences.append(
                {
                    "image_id": image_id,
                    "status": "ROLLBACK_FAILED_FATAL",
                    "message": str(exc),
                }
            )
            results["errors"] += 1
            results["details"].append(f"FATAL {image_id}: {exc}")
            checkpoint()
            raise
        except Exception as exc:
            record_error(image_id, str(exc))
            settled_ids.add(image_id)

    return results
