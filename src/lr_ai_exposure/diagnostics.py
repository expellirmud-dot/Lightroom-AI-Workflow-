"""Read-only aggregated diagnostics for the active Lightroom folder."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
from importlib import metadata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lr_ai_exposure.cache_probe import find_preview_uuid
from lr_ai_exposure.db_uri import safe_sqlite_uri
from lr_ai_exposure.xmp import XmpError, read_exposure_2012


DIAGNOSTIC_PROTOCOL_VERSION = "1.0"
SAMPLE_LIMIT = 5
STAGE_STATUSES = {"PASS", "WARN", "FAIL", "SKIPPED_DEPENDENCY"}


def _bounded_samples(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {}
    bounded: dict[str, list[dict[str, Any]]] = {}
    for category, samples in value.items():
        if isinstance(category, str) and isinstance(samples, list):
            bounded[category] = [item for item in samples if isinstance(item, dict)][
                :SAMPLE_LIMIT
            ]
    return bounded


def _issue(
    issues: list[dict[str, Any]],
    *,
    stage: str,
    severity: str,
    code: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {
        "stage": stage,
        "severity": severity,
        "code": code,
        "message": message,
    }
    if evidence:
        item["evidence"] = evidence
    issues.append(item)


def _stage(
    stages: list[dict[str, Any]],
    name: str,
    status: str,
    reason_codes: list[str],
    evidence: dict[str, Any],
) -> None:
    if status not in STAGE_STATUSES:
        raise ValueError(f"Invalid diagnostic stage status: {status}")
    stages.append(
        {
            "stage": name,
            "status": status,
            "reason_codes": reason_codes,
            "evidence": evidence,
        }
    )


def _read_only_database_probe(
    path: Path,
    required_table: str,
    required_columns: set[str],
) -> tuple[dict[str, Any], list[str]]:
    evidence: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "readable": False,
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "modified_ns": path.stat().st_mtime_ns if path.is_file() else None,
        "quick_check": None,
        "required_table": required_table,
        "required_columns": sorted(required_columns),
        "observed_columns": [],
    }
    reason_codes: list[str] = []
    if not path.is_file():
        reason_codes.append(f"{required_table.upper().replace('-', '_')}_DB_MISSING")
        return evidence, reason_codes

    try:
        db = sqlite3.connect(safe_sqlite_uri(str(path)) + "?mode=ro", uri=True)
        try:
            evidence["quick_check"] = db.execute("PRAGMA quick_check(1)").fetchone()[0]
            table = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (required_table,),
            ).fetchone()
            if table is None:
                reason_codes.append(f"{required_table.upper()}_TABLE_MISSING")
            else:
                columns = {
                    str(row[1])
                    for row in db.execute(f'PRAGMA table_info("{required_table}")')
                }
                evidence["observed_columns"] = sorted(columns)
                missing = sorted(required_columns - columns)
                if missing:
                    evidence["missing_columns"] = missing
                    reason_codes.append(f"{required_table.upper()}_COLUMNS_MISSING")
            evidence["readable"] = True
            if evidence["quick_check"] != "ok":
                reason_codes.append(f"{required_table.upper()}_QUICK_CHECK_FAILED")
        finally:
            db.close()
    except Exception as exc:
        evidence["error"] = str(exc)
        reason_codes.append(f"{required_table.upper()}_DB_READ_FAILED")
    return evidence, reason_codes


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath(
            [os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(root))]
        ) == os.path.normcase(os.path.abspath(root))
    except (OSError, ValueError):
        return False


def _probe_xmp(
    eligible: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    if not eligible:
        return (
            "SKIPPED_DEPENDENCY",
            ["NO_ELIGIBLE_RAW"],
            {"checked": 0, "exists": 0, "parse_ready": 0, "missing": 0, "invalid": 0, "samples": []},
        )

    evidence: dict[str, Any] = {
        "checked": 0,
        "exists": 0,
        "parse_ready": 0,
        "missing": 0,
        "invalid": 0,
        "samples": [],
    }
    reasons: set[str] = set()
    for photo in eligible:
        raw_path = Path(str(photo.get("path", "")))
        xmp_path = raw_path.with_suffix(".xmp")
        evidence["checked"] += 1
        sample: dict[str, Any] = {
            "id_local": photo.get("id_local"),
            "filename": photo.get("filename") or raw_path.name,
            "xmp_path": str(xmp_path),
            "exists": xmp_path.is_file(),
        }
        if not xmp_path.is_file():
            evidence["missing"] += 1
            reasons.add("XMP_MISSING")
            _issue(
                issues,
                stage="xmp_readiness",
                severity="FAIL",
                code="XMP_MISSING",
                message="Eligible RAW has no readable XMP sidecar.",
                evidence={"id_local": photo.get("id_local"), "xmp_path": str(xmp_path)},
            )
        else:
            evidence["exists"] += 1
            try:
                sample["exposure_2012"] = read_exposure_2012(xmp_path)
                sample["parse_ready"] = True
                evidence["parse_ready"] += 1
            except (XmpError, OSError) as exc:
                sample["parse_ready"] = False
                sample["error"] = str(exc)
                evidence["invalid"] += 1
                reasons.add("XMP_EXPOSURE_UNREADABLE")
                _issue(
                    issues,
                    stage="xmp_readiness",
                    severity="FAIL",
                    code="XMP_EXPOSURE_UNREADABLE",
                    message="Exposure2012 is missing, malformed, ambiguous, or non-finite.",
                    evidence={"id_local": photo.get("id_local"), "error": str(exc)},
                )
        if len(evidence["samples"]) < SAMPLE_LIMIT:
            evidence["samples"].append(sample)
    status = "PASS" if not reasons else "FAIL"
    return status, sorted(reasons) or ["XMP_READINESS_PROVEN"], evidence


def _probe_preview_mapping(
    eligible: list[dict[str, Any]],
    previews_db: Path,
    root_db: Path,
    cache_ready: bool,
    issues: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    counts = {
        "FOUND": 0,
        "MISSING": 0,
        "AMBIGUOUS": 0,
        "DB_ERROR": 0,
        "ROOT_PIXEL_MISSING": 0,
        "INVALID_JPEG": 0,
    }
    evidence: dict[str, Any] = {"counts": counts, "samples": []}
    if not eligible:
        return "SKIPPED_DEPENDENCY", ["NO_ELIGIBLE_RAW"], evidence
    if not cache_ready:
        return "SKIPPED_DEPENDENCY", ["PREVIEW_CACHE_NOT_READY"], evidence

    root_connection = sqlite3.connect(safe_sqlite_uri(str(root_db)) + "?mode=ro", uri=True)
    try:
        for photo in eligible:
            id_local = photo.get("id_local")
            if isinstance(id_local, (int, float, str)):
                result = find_preview_uuid(str(previews_db), id_local)
            else:
                result = {"status": "DB_ERROR", "uuid": None}
            status = str(result.get("status", "DB_ERROR"))
            if status not in counts:
                status = "DB_ERROR"
            counts[status] += 1
            sample: dict[str, Any] = {
                "id_local": photo.get("id_local"),
                "filename": photo.get("filename"),
                "status": status,
                "preview_uuid": result.get("uuid"),
            }
            if status == "FOUND" and len(evidence["samples"]) < SAMPLE_LIMIT:
                jpeg = root_connection.execute(
                    "SELECT length(jpegData), hex(substr(jpegData, 1, 2)) "
                    "FROM RootPixels WHERE uuid = ?",
                    (result.get("uuid"),),
                ).fetchall()
                sample["root_pixel_row_count"] = len(jpeg)
                if len(jpeg) == 1:
                    sample["jpeg_byte_count"] = jpeg[0][0]
                    sample["jpeg_soi_hex"] = jpeg[0][1]
                    sample["jpeg_valid"] = jpeg[0][0] is not None and jpeg[0][0] >= 100 and jpeg[0][1] == "FFD8"
                    if not sample["jpeg_valid"]:
                        counts["INVALID_JPEG"] += 1
                else:
                    counts["ROOT_PIXEL_MISSING"] += 1
            if len(evidence["samples"]) < SAMPLE_LIMIT:
                evidence["samples"].append(sample)
    finally:
        root_connection.close()

    reasons = [name for name, count in counts.items() if name != "FOUND" and count]
    if counts["ROOT_PIXEL_MISSING"] or counts["INVALID_JPEG"]:
        _issue(
            issues,
            stage="preview_identity_mapping",
            severity="FAIL",
            code="PREVIEW_BYTES_UNREADABLE",
            message="A mapped preview has missing or invalid root-pixel JPEG bytes.",
            evidence={"counts": counts},
        )
    if counts["FOUND"] != len(eligible):
        reasons.append("INCOMPLETE_PREVIEW_IDENTITY_MAPPING")
        _issue(
            issues,
            stage="preview_identity_mapping",
            severity="FAIL",
            code="INCOMPLETE_PREVIEW_IDENTITY_MAPPING",
            message="Not every eligible RAW identity maps to exactly one preview.",
            evidence={"counts": counts},
        )
    return ("PASS" if not reasons else "FAIL"), (reasons or ["ALL_IDENTITIES_FOUND"]), evidence


def _write_text_atomic(path: Path, content: str) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def _summary_text(report: dict[str, Any]) -> str:
    counts = report["summary"]
    lines = [
        "AI Exposure Assist - Current Folder Diagnostic",
        f"Diagnostic ID: {report['diagnostic_id']}",
        f"Overall readiness: {report['overall_readiness']}",
        f"Active folder: {report['lightroom'].get('active_folder_path') or '<none>'}",
        f"Direct photos: {counts['direct_photo_count']}",
        f"Child folders: {counts['child_folder_count']}",
        f"Recursive photos: {counts['recursive_photo_count']}",
        f"Eligible proprietary RAW masters: {counts['eligible_raw_count']}",
        "",
        "Stages:",
    ]
    for stage in report["stages"]:
        reasons = ", ".join(stage["reason_codes"])
        lines.append(f"- {stage['stage']}: {stage['status']} ({reasons})")
    lines.extend(["", f"Issues: {len(report['issues'])}"])
    for issue in report["issues"]:
        lines.append(f"- [{issue['severity']}] {issue['code']}: {issue['message']}")
    return "\n".join(lines) + "\n"


def run_diagnostic(
    request: dict[str, Any],
    settings: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Aggregate all independent current-folder checks and write two reports."""
    if request.get("protocol_version") != DIAGNOSTIC_PROTOCOL_VERSION:
        raise ValueError("Unsupported diagnostic protocol version")
    if request.get("operation") != "DIAGNOSE_CURRENT_FOLDER":
        raise ValueError("Diagnostic request operation mismatch")
    diagnostic_id = request.get("diagnostic_id")
    if not isinstance(diagnostic_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", diagnostic_id):
        raise ValueError("diagnostic_id must contain only letters, digits, dot, underscore, or hyphen")

    runtime_dir = Path(str(settings["runtime_directory"])).resolve()
    report_dir = runtime_dir / "diagnostics" / diagnostic_id
    report_dir.mkdir(parents=True, exist_ok=True)
    issues: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []

    active_folder_count = int(request.get("active_folder_count", 0))
    enumeration_status = request.get("enumeration_status")
    context_reasons: list[str] = []
    if active_folder_count != 1:
        context_reasons.append("ACTIVE_FOLDER_CARDINALITY")
        _issue(
            issues,
            stage="lightroom_context",
            severity="FAIL",
            code="ACTIVE_FOLDER_CARDINALITY",
            message="Exactly one active Lightroom folder is required.",
            evidence={"active_folder_count": active_folder_count},
        )
    if enumeration_status != "PASS":
        context_reasons.append("LIGHTROOM_ENUMERATION_FAILED")
        _issue(
            issues,
            stage="lightroom_context",
            severity="FAIL",
            code="LIGHTROOM_ENUMERATION_FAILED",
            message="Lightroom could not enumerate direct photos from the active folder.",
            evidence={"error": request.get("enumeration_error")},
        )
    _stage(
        stages,
        "lightroom_context",
        "PASS" if not context_reasons else "FAIL",
        context_reasons or ["ACTIVE_FOLDER_ENUMERATED"],
        {
            "catalog_path": request.get("catalog_path"),
            "active_sources": request.get("active_sources", []),
            "active_folder_count": active_folder_count,
            "active_folder_path": request.get("active_folder_path"),
            "direct_photo_count": int(request.get("direct_photo_count", 0)),
            "child_folder_count": int(request.get("child_folder_count", 0)),
            "recursive_photo_count": int(request.get("recursive_photo_count", 0)),
        },
    )

    raw_counts = request.get("counts")
    counts: dict[str, Any] = raw_counts if isinstance(raw_counts, dict) else {}
    eligible_count = int(counts.get("eligible_raw", 0))
    eligibility_reasons = ["ELIGIBLE_RAW_FOUND"]
    eligibility_status = "PASS"
    if eligible_count == 0:
        eligibility_status = "WARN"
        eligibility_reasons = ["NO_ELIGIBLE_RAW"]
        _issue(
            issues,
            stage="eligibility",
            severity="FAIL",
            code="NO_ELIGIBLE_RAW",
            message="The active folder contains no eligible proprietary-RAW master photos.",
        )
    _stage(
        stages,
        "eligibility",
        eligibility_status,
        eligibility_reasons,
        {"counts": counts, "observed_file_formats": request.get("observed_file_formats", [])},
    )

    eligible = [item for item in request.get("eligible_photos", []) if isinstance(item, dict)]
    if eligible_count != len(eligible):
        _issue(
            issues,
            stage="eligibility",
            severity="FAIL",
            code="ELIGIBLE_IDENTITY_COUNT_MISMATCH",
            message="Eligible RAW count does not match the supplied identity set.",
            evidence={"reported_count": eligible_count, "identity_count": len(eligible)},
        )
    observed_formats = request.get("observed_file_formats", [])
    if isinstance(observed_formats, list):
        observed_total = sum(
            int(item.get("count", 0))
            for item in observed_formats
            if isinstance(item, dict) and isinstance(item.get("count", 0), int)
        )
        recursive_count = int(request.get("recursive_photo_count", 0))
        if observed_total != recursive_count:
            _issue(
                issues,
                stage="eligibility",
                severity="FAIL",
                code="FILE_FORMAT_HISTOGRAM_MISMATCH",
                message="Observed fileFormat histogram does not cover every recursive photo.",
                evidence={"histogram_count": observed_total, "recursive_photo_count": recursive_count},
            )
    source_root_value = request.get("active_folder_path")
    if isinstance(source_root_value, str) and source_root_value:
        source_root = Path(source_root_value)
        for photo in eligible:
            photo_path = Path(str(photo.get("path", "")))
            if not _path_is_within(photo_path, source_root):
                _issue(
                    issues,
                    stage="eligibility",
                    severity="FAIL",
                    code="SOURCE_CONTAINMENT_MISMATCH",
                    message="Eligible RAW path is outside the active source folder.",
                    evidence={"id_local": photo.get("id_local"), "path": str(photo_path)},
                )

    runtime_evidence = {
        "project_root": str(project_root.resolve()),
        "runtime_directory": str(runtime_dir),
        "diagnostic_directory": str(report_dir),
        "directory_exists": report_dir.is_dir(),
        "directory_writable": os.access(report_dir, os.W_OK),
    }
    runtime_ready = runtime_evidence["directory_exists"] and runtime_evidence["directory_writable"]
    _stage(stages, "runtime", "PASS" if runtime_ready else "FAIL", ["RUNTIME_READY" if runtime_ready else "RUNTIME_NOT_WRITABLE"], runtime_evidence)
    if not runtime_ready:
        _issue(issues, stage="runtime", severity="FAIL", code="RUNTIME_NOT_WRITABLE", message="Authorized diagnostic runtime directory is not writable.")

    uv_path = shutil.which("uv")
    try:
        cli_version = metadata.version("lightroom-ai-exposure")
    except metadata.PackageNotFoundError:
        cli_version = "unknown"
    config_error = settings.get("_diagnostic_config_error")
    cli_evidence = {
        "python_executable": sys.executable,
        "uv_path": uv_path,
        "cli_version": cli_version,
        "config_loaded": config_error is None,
        "config_error": config_error,
        "configured_preview_cache_path": settings.get("preview_cache_path"),
        "secrets_printed": False,
    }
    cli_reasons: list[str] = []
    if config_error:
        cli_reasons.append("CONFIG_INVALID")
        _issue(
            issues,
            stage="cli_config",
            severity="FAIL",
            code="CONFIG_INVALID",
            message="Canonical configuration is invalid; only diagnostic path fallback was used.",
            evidence={"error": str(config_error)},
        )
    if not uv_path:
        cli_reasons.append("UV_NOT_RESOLVED")
    cli_status = "FAIL" if config_error else ("PASS" if uv_path else "WARN")
    _stage(stages, "cli_config", cli_status, cli_reasons or ["CLI_READY"], cli_evidence)
    if not uv_path:
        _issue(issues, stage="cli_config", severity="WARN", code="UV_NOT_RESOLVED", message="uv is not resolvable from the diagnostic process PATH.")

    _stage(
        stages,
        "bridge",
        "PASS",
        ["BRIDGE_REQUEST_VALID"],
        {
            "protocol_version": request.get("protocol_version"),
            "operation": request.get("operation"),
            "diagnostic_id": diagnostic_id,
            "utf8_json_request": True,
        },
    )

    _stage(
        stages,
        "metadata_sync",
        "FAIL",
        ["METADATA_SYNC_UNPROVEN"],
        {
            "sync_safety": "UNPROVEN",
            "owner_save_metadata_required": False,
            "reason": "No supported Lightroom SDK evidence in this diagnostic proves catalog/sidecar synchronization.",
        },
    )
    _issue(
        issues,
        stage="metadata_sync",
        severity="FAIL",
        code="METADATA_SYNC_UNPROVEN",
        message="Metadata synchronization safety is unknown; later mutation must fail closed without requiring an unsupported owner action.",
    )

    configured_cache = settings.get("preview_cache_path")
    if isinstance(configured_cache, str) and configured_cache:
        cache_path_configured = True
        cache_path = Path(configured_cache)
    else:
        cache_path_configured = False
        cache_path = project_root / "__missing_preview_cache__"
    if not cache_path_configured:
        _issue(
            issues,
            stage="preview_cache",
            severity="FAIL",
            code="PREVIEW_CACHE_PATH_MISSING",
            message="Configuration does not contain a usable preview_cache_path.",
        )
    catalog_value = request.get("catalog_path")
    expected_cache_path: Path | None = None
    if isinstance(catalog_value, str) and catalog_value:
        catalog_path = Path(catalog_value)
        expected_cache_path = catalog_path.with_name(catalog_path.stem + " Previews.lrdata")
    cache_matches_catalog = (
        expected_cache_path is not None
        and os.path.normcase(os.path.abspath(cache_path))
        == os.path.normcase(os.path.abspath(expected_cache_path))
    )
    if expected_cache_path is not None and not cache_matches_catalog:
        _issue(
            issues,
            stage="preview_cache",
            severity="WARN",
            code="PREVIEW_CACHE_CATALOG_MISMATCH",
            message="Configured preview cache path does not match the active catalog name/location convention.",
            evidence={"configured": str(cache_path), "expected": str(expected_cache_path)},
        )
    previews_db = cache_path / "previews.db"
    root_db = cache_path / "root-pixels.db"
    previews_evidence, previews_reasons = _read_only_database_probe(
        previews_db, "ImageCacheEntry", {"imageId", "uuid"}
    )
    root_evidence, root_reasons = _read_only_database_probe(
        root_db, "RootPixels", {"uuid", "jpegData"}
    )
    cache_reasons = previews_reasons + root_reasons
    for code in cache_reasons:
        normalized = code
        if code == "IMAGECACHEENTRY_DB_MISSING":
            normalized = "PREVIEWS_DB_MISSING"
        elif code == "ROOTPIXELS_DB_MISSING":
            normalized = "ROOT_PIXELS_DB_MISSING"
        _issue(
            issues,
            stage="preview_cache",
            severity="FAIL",
            code=normalized,
            message="Preview cache database readiness check failed.",
        )
    cache_ready = not cache_reasons
    _stage(
        stages,
        "preview_cache",
        "PASS" if cache_ready else "FAIL",
        cache_reasons or ["CACHE_DATABASES_READ_ONLY_READY"],
        {
            "configured_path": str(cache_path),
            "expected_from_catalog": str(expected_cache_path) if expected_cache_path else None,
            "matches_catalog": cache_matches_catalog,
            "previews_db": previews_evidence,
            "root_pixels_db": root_evidence,
        },
    )

    mapping_status, mapping_reasons, mapping_evidence = _probe_preview_mapping(
        eligible, previews_db, root_db, cache_ready, issues
    )
    _stage(stages, "preview_identity_mapping", mapping_status, mapping_reasons, mapping_evidence)

    xmp_status, xmp_reasons, xmp_evidence = _probe_xmp(eligible, issues)
    _stage(stages, "xmp_readiness", xmp_status, xmp_reasons, xmp_evidence)

    fail_codes = {issue["code"] for issue in issues if issue["severity"] == "FAIL"}
    safety_codes = {
        "SOURCE_CONTAINMENT_MISMATCH",
        "ELIGIBLE_IDENTITY_COUNT_MISMATCH",
        "FILE_FORMAT_HISTOGRAM_MISMATCH",
        "XMP_EXPOSURE_UNREADABLE",
        "INCOMPLETE_PREVIEW_IDENTITY_MAPPING",
        "PREVIEW_BYTES_UNREADABLE",
        "METADATA_SYNC_UNPROVEN",
    }
    if fail_codes & safety_codes:
        overall = "SAFETY_BLOCKED"
    elif "NO_ELIGIBLE_RAW" in fail_codes:
        overall = "NOT_READY_UNSUPPORTED"
    elif fail_codes:
        overall = "NOT_READY_FIXABLE"
    else:
        overall = "READY_FOR_SESSION"

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_version": DIAGNOSTIC_PROTOCOL_VERSION,
        "operation": "DIAGNOSE_CURRENT_FOLDER",
        "diagnostic_id": diagnostic_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_readiness": overall,
        "diagnostic_completed": True,
        "mutation_authorized": False,
        "plugin": request.get("plugin", {}),
        "lightroom": {
            "catalog_path": request.get("catalog_path"),
            "active_sources": request.get("active_sources", []),
            "active_folder_path": request.get("active_folder_path"),
            "observed_file_formats": request.get("observed_file_formats", []),
            "samples": _bounded_samples(request.get("samples")),
        },
        "summary": {
            "direct_photo_count": int(request.get("direct_photo_count", 0)),
            "child_folder_count": int(request.get("child_folder_count", 0)),
            "recursive_photo_count": int(request.get("recursive_photo_count", 0)),
            "eligible_raw_count": eligible_count,
            "counts": counts,
            "stage_counts": {
                status: sum(stage["status"] == status for stage in stages)
                for status in sorted(STAGE_STATUSES)
            },
            "issue_count": len(issues),
        },
        "stages": stages,
        "issues": sorted(
            issues,
            key=lambda item: ({"FAIL": 0, "WARN": 1}.get(item["severity"], 2), item["stage"], item["code"]),
        ),
        "artifacts": {
            "preflight_json": str(report_dir / "preflight.json"),
            "diagnostic_txt": str(report_dir / "diagnostic.txt"),
        },
    }
    _write_text_atomic(
        Path(report["artifacts"]["preflight_json"]),
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
    )
    _write_text_atomic(
        Path(report["artifacts"]["diagnostic_txt"]),
        _summary_text(report),
    )
    return report
