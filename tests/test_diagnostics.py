from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from lr_ai_exposure.diagnostics import run_diagnostic


def _request(*, photos: list[dict], counts: dict | None = None) -> dict:
    return {
        "protocol_version": "1.0",
        "operation": "DIAGNOSE_CURRENT_FOLDER",
        "diagnostic_id": "diagnostic-test",
        "plugin": {"version": "1.1.0", "build": 3},
        "catalog_path": "D:/catalog/Test.lrcat",
        "active_sources": [
            {"type": "LrFolder", "name": "Event", "path": "D:/photos/Event"}
        ],
        "active_folder_count": 1,
        "active_folder_path": "D:/photos/Event",
        "direct_photo_count": len(photos),
        "enumeration_status": "PASS",
        "observed_file_formats": [
            {"value": "JPG", "value_type": "string", "count": len(photos)}
        ],
        "counts": counts
        or {
            "eligible_raw": 0,
            "virtual_copies": 0,
            "videos": 0,
            "unsupported_formats": len(photos),
            "empty_paths": 0,
            "offline_paths": 0,
            "duplicate_paths": 0,
        },
        "samples": {"unsupported_formats": photos[:5]},
        "eligible_photos": [],
    }


def _settings(tmp_path: Path, cache: Path) -> dict:
    return {
        "preview_cache_path": str(cache),
        "runtime_directory": str(tmp_path / "runtime"),
    }


def _stage(report: dict, name: str) -> dict:
    return next(stage for stage in report["stages"] if stage["stage"] == name)


def test_zero_eligible_raw_still_writes_complete_artifacts(tmp_path: Path) -> None:
    cache = tmp_path / "Missing Previews.lrdata"
    request = _request(
        photos=[
            {
                "filename": "frame.jpg",
                "id_local": "101",
                "uuid": "uuid-101",
                "path": "D:/photos/Event/frame.jpg",
                "file_format": "JPG",
                "file_format_type": "string",
            }
        ]
    )

    report = run_diagnostic(request, _settings(tmp_path, cache), tmp_path)

    assert report["summary"]["eligible_raw_count"] == 0
    assert "NO_ELIGIBLE_RAW" in _stage(report, "eligibility")["reason_codes"]
    assert _stage(report, "preview_cache")["status"] == "FAIL"
    assert _stage(report, "preview_identity_mapping")["status"] == "SKIPPED_DEPENDENCY"
    preflight = Path(report["artifacts"]["preflight_json"])
    summary = Path(report["artifacts"]["diagnostic_txt"])
    assert json.loads(preflight.read_text(encoding="utf-8"))["diagnostic_id"] == "diagnostic-test"
    assert "Eligible proprietary RAW masters: 0" in summary.read_text(encoding="utf-8")


def test_multiple_independent_failures_are_aggregated(tmp_path: Path) -> None:
    cache = tmp_path / "Broken Previews.lrdata"
    cache.mkdir()
    raw = tmp_path / "photos" / "missing.nef"
    request = _request(
        photos=[],
        counts={
            "eligible_raw": 1,
            "virtual_copies": 1,
            "videos": 1,
            "unsupported_formats": 1,
            "empty_paths": 1,
            "offline_paths": 1,
            "duplicate_paths": 1,
        },
    )
    request["eligible_photos"] = [
        {
            "filename": "missing.nef",
            "id_local": "202",
            "uuid": "uuid-202",
            "path": str(raw),
            "file_format": "RAW",
            "file_format_type": "string",
        }
    ]

    report = run_diagnostic(request, _settings(tmp_path, cache), tmp_path)

    codes = {issue["code"] for issue in report["issues"]}
    assert {"PREVIEWS_DB_MISSING", "ROOT_PIXELS_DB_MISSING", "XMP_MISSING"} <= codes
    assert len(report["issues"]) >= 3
    assert _stage(report, "runtime")["status"] == "PASS"
    assert _stage(report, "bridge")["status"] == "PASS"


def test_file_format_values_and_bounded_samples_are_preserved(tmp_path: Path) -> None:
    request = _request(photos=[])
    request["observed_file_formats"] = [
        {"value": "RAW", "value_type": "string", "count": 7},
        {"value": None, "value_type": "nil", "count": 2},
    ]
    request["samples"] = {
        "unknown_formats": [
            {
                "filename": f"sample-{index}.nef",
                "id_local": str(index),
                "file_format": None,
                "file_format_type": "nil",
            }
            for index in range(8)
        ]
    }

    report = run_diagnostic(
        request,
        _settings(tmp_path, tmp_path / "none.lrdata"),
        tmp_path,
    )

    assert report["lightroom"]["observed_file_formats"] == request["observed_file_formats"]
    assert len(report["lightroom"]["samples"]["unknown_formats"]) == 5
    assert report["lightroom"]["samples"]["unknown_formats"][0]["file_format_type"] == "nil"


def test_cache_readiness_and_xmp_probe_are_read_only(tmp_path: Path) -> None:
    cache = tmp_path / "Catalog Previews.lrdata"
    cache.mkdir()
    previews_db = cache / "previews.db"
    root_db = cache / "root-pixels.db"
    with sqlite3.connect(previews_db) as db:
        db.execute("CREATE TABLE ImageCacheEntry (imageId NUMERIC, uuid TEXT)")
        db.execute("INSERT INTO ImageCacheEntry VALUES (303, 'preview-303')")
    with sqlite3.connect(root_db) as db:
        db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.execute("INSERT INTO RootPixels VALUES ('preview-303', ?)", (b"\xff\xd8" + b"x" * 128,))

    raw = tmp_path / "photos" / "frame.nef"
    raw.parent.mkdir()
    raw.write_bytes(b"raw-bytes")
    xmp = raw.with_suffix(".xmp")
    xmp.write_text(
        '<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/">'
        '<rdf:RDF><rdf:Description crs:Exposure2012="+0.35" />'
        "</rdf:RDF></x:xmpmeta>",
        encoding="utf-8",
    )
    before = xmp.read_bytes()
    request = _request(photos=[])
    request["counts"]["eligible_raw"] = 1
    request["eligible_photos"] = [
        {
            "filename": raw.name,
            "id_local": "303",
            "uuid": "uuid-303",
            "path": str(raw),
            "file_format": "RAW",
            "file_format_type": "string",
        }
    ]

    report = run_diagnostic(request, _settings(tmp_path, cache), tmp_path)

    assert _stage(report, "preview_cache")["status"] == "PASS"
    assert _stage(report, "preview_identity_mapping")["evidence"]["counts"]["FOUND"] == 1
    assert _stage(report, "xmp_readiness")["evidence"]["parse_ready"] == 1
    assert xmp.read_bytes() == before
    assert not list(raw.parent.glob("*.bak"))
    assert not list(raw.parent.glob("*.tmp"))
