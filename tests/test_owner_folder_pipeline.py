"""Whole-folder diagnostic scenarios modeled after the real Lightroom owner workflow.

The goal is to catch the next likely integration failures before another owner
round-trip: parent-folder enumeration, recursive identity coverage, preview DB
mapping, root-pixel availability, and XMP readiness.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from lr_ai_exposure.diagnostics import run_diagnostic


def _write_xmp(path: Path, exposure: float = 0.0) -> None:
    path.write_text(
        '<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/">'
        f'<rdf:RDF><rdf:Description crs:Exposure2012="{exposure:+.2f}" />'
        '</rdf:RDF></x:xmpmeta>',
        encoding="utf-8",
    )


def _make_cache(cache: Path, rows: list[tuple[int, str]], *, root_uuids: set[str] | None = None) -> None:
    cache.mkdir(parents=True)
    with sqlite3.connect(cache / "previews.db") as db:
        db.execute("CREATE TABLE ImageCacheEntry (imageId NUMERIC, uuid TEXT)")
        db.executemany("INSERT INTO ImageCacheEntry VALUES (?, ?)", rows)
    roots = root_uuids if root_uuids is not None else {uuid for _, uuid in rows}
    with sqlite3.connect(cache / "root-pixels.db") as db:
        db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.executemany(
            "INSERT INTO RootPixels VALUES (?, ?)",
            [(uuid, b"\xff\xd8" + b"x" * 256) for uuid in roots],
        )


def _photo(image_id: int, raw: Path) -> dict:
    return {
        "filename": raw.name,
        "id_local": str(image_id),
        "uuid": f"catalog-{image_id}",
        "path": str(raw),
        "file_format": "RAW",
        "file_format_display": "RAW",
        "file_format_type": "string",
        "is_virtual_copy": False,
        "is_video": False,
        "path_exists": True,
    }


def _request(root: Path, photos: list[dict], *, direct: int = 0, child_folders: int = 2) -> dict:
    return {
        "protocol_version": "1.0",
        "operation": "DIAGNOSE_CURRENT_FOLDER",
        "diagnostic_id": "owner-folder-test",
        "plugin": {"version": "1.2.0", "build": 1},
        "catalog_path": str(root.parent / "Owner.lrcat"),
        "active_sources": [
            {
                "type": "getPath,getChildren,getPhotos,getParent,type=LrFolder",
                "source_type": "LrFolder",
                "source_type_status": "PASS",
                "name": root.name,
                "path": str(root),
                "get_path_status": "PASS",
            }
        ],
        "active_folder_count": 1,
        "active_folder_path": str(root),
        "direct_photo_count": direct,
        "child_folder_count": child_folders,
        "recursive_photo_count": len(photos),
        "enumeration_status": "PASS",
        "enumeration_error": None,
        "observed_file_formats": [
            {"value": "RAW", "value_display": "RAW", "value_type": "string", "count": len(photos)}
        ],
        "counts": {
            "eligible_raw": len(photos),
            "virtual_copies": 0,
            "videos": 0,
            "unsupported_formats": 0,
            "empty_paths": 0,
            "offline_paths": 0,
            "duplicate_paths": 0,
        },
        "samples": {"eligible_raw": photos[:5]},
        "eligible_photos": photos,
    }


def _stage(report: dict, name: str) -> dict:
    return next(stage for stage in report["stages"] if stage["stage"] == name)


def _settings(tmp_path: Path, cache: Path) -> dict:
    return {
        "preview_cache_path": str(cache),
        "runtime_directory": str(tmp_path / "runtime"),
    }


def test_parent_folder_with_only_child_raws_passes_all_read_only_content_gates(tmp_path: Path) -> None:
    """Exact structural case: parent has zero direct photos; RAWs live in two children."""
    root = tmp_path / "2569-08-02"
    child_a = root / "193ND750"
    child_b = root / "194ND750"
    child_a.mkdir(parents=True)
    child_b.mkdir(parents=True)
    raw_a = child_a / "A001.NEF"
    raw_b = child_b / "B001.NEF"
    raw_a.write_bytes(b"raw-a")
    raw_b.write_bytes(b"raw-b")
    _write_xmp(raw_a.with_suffix(".xmp"), 0.0)
    _write_xmp(raw_b.with_suffix(".xmp"), 0.25)

    photos = [_photo(101, raw_a), _photo(202, raw_b)]
    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(101, "preview-101"), (202, "preview-202")])

    report = run_diagnostic(_request(root, photos), _settings(tmp_path, cache), tmp_path)

    assert _stage(report, "lightroom_context")["status"] == "PASS"
    assert _stage(report, "eligibility")["status"] == "PASS"
    assert _stage(report, "preview_cache")["status"] == "PASS"
    assert _stage(report, "preview_identity_mapping")["status"] == "PASS"
    assert _stage(report, "xmp_readiness")["status"] == "PASS"
    assert report["summary"]["direct_photo_count"] == 0
    assert report["summary"]["child_folder_count"] == 2
    assert report["summary"]["recursive_photo_count"] == 2
    assert report["summary"]["eligible_raw_count"] == 2

    # Metadata-sync mutation safety is intentionally a separate gate; a healthy
    # read-only folder/cache/XMP diagnostic must not be mislabeled as an
    # enumeration or preview failure because that later mutation proof is absent.
    issue_codes = {issue["code"] for issue in report["issues"]}
    assert "LIGHTROOM_ENUMERATION_FAILED" not in issue_codes
    assert "NO_ELIGIBLE_RAW" not in issue_codes
    assert "INCOMPLETE_PREVIEW_IDENTITY_MAPPING" not in issue_codes
    assert "XMP_MISSING" not in issue_codes


def test_incomplete_preview_mapping_fails_before_analysis(tmp_path: Path) -> None:
    root = tmp_path / "Event"
    child = root / "Camera"
    child.mkdir(parents=True)
    raw_a = child / "A.NEF"
    raw_b = child / "B.NEF"
    raw_a.write_bytes(b"a")
    raw_b.write_bytes(b"b")
    _write_xmp(raw_a.with_suffix(".xmp"))
    _write_xmp(raw_b.with_suffix(".xmp"))
    photos = [_photo(1, raw_a), _photo(2, raw_b)]

    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(1, "preview-1")])
    report = run_diagnostic(
        _request(root, photos, child_folders=1),
        _settings(tmp_path, cache),
        tmp_path,
    )

    assert _stage(report, "preview_identity_mapping")["status"] == "FAIL"
    codes = {issue["code"] for issue in report["issues"]}
    assert "INCOMPLETE_PREVIEW_IDENTITY_MAPPING" in codes


def test_ambiguous_preview_identity_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "Event"
    child = root / "Camera"
    child.mkdir(parents=True)
    raw = child / "A.NEF"
    raw.write_bytes(b"a")
    _write_xmp(raw.with_suffix(".xmp"))
    photos = [_photo(7, raw)]

    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(7, "preview-a"), (7, "preview-b")])
    report = run_diagnostic(
        _request(root, photos, child_folders=1),
        _settings(tmp_path, cache),
        tmp_path,
    )

    mapping = _stage(report, "preview_identity_mapping")
    assert mapping["status"] == "FAIL"
    assert mapping["evidence"]["counts"]["AMBIGUOUS"] == 1


def test_missing_root_pixel_jpeg_fails_before_ai(tmp_path: Path) -> None:
    root = tmp_path / "Event"
    child = root / "Camera"
    child.mkdir(parents=True)
    raw = child / "A.NEF"
    raw.write_bytes(b"a")
    _write_xmp(raw.with_suffix(".xmp"))
    photos = [_photo(9, raw)]

    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(9, "preview-9")], root_uuids=set())
    report = run_diagnostic(
        _request(root, photos, child_folders=1),
        _settings(tmp_path, cache),
        tmp_path,
    )

    mapping = _stage(report, "preview_identity_mapping")
    assert mapping["status"] == "FAIL"
    assert mapping["evidence"]["counts"]["ROOT_PIXEL_MISSING"] == 1
    assert "PREVIEW_BYTES_UNREADABLE" in {issue["code"] for issue in report["issues"]}


def test_missing_xmp_is_reported_without_touching_raw(tmp_path: Path) -> None:
    root = tmp_path / "Event"
    child = root / "Camera"
    child.mkdir(parents=True)
    raw = child / "A.NEF"
    original = b"owner-raw-must-not-change"
    raw.write_bytes(original)
    photos = [_photo(11, raw)]

    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(11, "preview-11")])
    report = run_diagnostic(
        _request(root, photos, child_folders=1),
        _settings(tmp_path, cache),
        tmp_path,
    )

    xmp = _stage(report, "xmp_readiness")
    assert xmp["status"] == "FAIL"
    assert "XMP_MISSING" in {issue["code"] for issue in report["issues"]}
    assert raw.read_bytes() == original
    assert not raw.with_suffix(".xmp").exists()


def test_recursive_file_format_histogram_must_cover_every_photo(tmp_path: Path) -> None:
    root = tmp_path / "Event"
    root.mkdir()
    raw = root / "A.NEF"
    raw.write_bytes(b"a")
    _write_xmp(raw.with_suffix(".xmp"))
    photos = [_photo(21, raw)]
    request = _request(root, photos, direct=1, child_folders=0)
    request["recursive_photo_count"] = 2  # deliberately contradictory live evidence

    cache = tmp_path / "Owner Previews.lrdata"
    _make_cache(cache, [(21, "preview-21")])
    report = run_diagnostic(request, _settings(tmp_path, cache), tmp_path)

    assert "FILE_FORMAT_HISTOGRAM_MISMATCH" in {
        issue["code"] for issue in report["issues"]
    }
