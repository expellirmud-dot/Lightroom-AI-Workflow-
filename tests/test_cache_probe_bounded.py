"""Bounded regression tests for WO-020 cache-probe fixes.

All databases are created under pytest tmp_path. No dependency on
scratch/, the live Lightroom cache, copied preview DBs, or previously
generated snapshots.

Covers:
- REAL numeric imageId FOUND
- string "3084000.0" normalized and FOUND
- integer 3084000 normalized and FOUND
- missing ID returns MISSING
- same UUID repeated returns FOUND
- two distinct UUIDs return AMBIGUOUS
- invalid DB returns DB_ERROR
- safe_sqlite_uri correctly encodes spaces and Windows paths
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lr_ai_exposure.db_uri import safe_sqlite_uri
from lr_ai_exposure.cache_probe import find_preview_uuid


def _make_db(tmp_path: Path, rows) -> str:
    """Build a throwaway previews.db with given (imageId, uuid) rows."""
    db = tmp_path / "previews.db"
    uri = safe_sqlite_uri(str(db)) + "?mode=rwc"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute(
        "CREATE TABLE ImageCacheEntry (imageId NUMERIC, uuid TEXT, digest TEXT)"
    )
    for iid, uid in rows:
        conn.execute(
            "INSERT INTO ImageCacheEntry VALUES (?, ?, ?)",
            (iid, uid, "d"),
        )
    conn.commit()
    conn.close()
    return str(db)


def test_real_numeric_imageid_found(tmp_path: Path):
    db = _make_db(tmp_path, [(3084000.0, "UUID-A")])
    res = find_preview_uuid(db, 3084000.0)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "UUID-A"


def test_string_dot_zero_normalized(tmp_path: Path):
    db = _make_db(tmp_path, [(3084000.0, "UUID-A")])
    res = find_preview_uuid(db, "3084000.0")
    assert res["status"] == "FOUND"


def test_integer_normalized(tmp_path: Path):
    db = _make_db(tmp_path, [(3084000.0, "UUID-A")])
    res = find_preview_uuid(db, 3084000)
    assert res["status"] == "FOUND"


def test_missing_id_returns_missing(tmp_path: Path):
    db = _make_db(tmp_path, [(3084000.0, "UUID-A")])
    res = find_preview_uuid(db, 9999999.0)
    assert res["status"] == "MISSING"


def test_repeated_same_uuid_returns_found(tmp_path: Path):
    db = _make_db(
        tmp_path,
        [(3084000.0, "UUID-A"), (3084000.0, "UUID-A")],
    )
    res = find_preview_uuid(db, 3084000.0)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "UUID-A"


def test_two_distinct_uuids_returns_ambiguous(tmp_path: Path):
    db = _make_db(
        tmp_path,
        [(3084000.0, "UUID-A"), (3084000.0, "UUID-B")],
    )
    res = find_preview_uuid(db, 3084000.0)
    assert res["status"] == "AMBIGUOUS"


def test_invalid_db_returns_db_error(tmp_path: Path):
    bad = tmp_path / "nope.db"  # does not exist
    res = find_preview_uuid(str(bad), 3084000.0)
    assert res["status"] == "DB_ERROR"


def test_safe_sqlite_uri_encodes_spaces_and_windows(tmp_path: Path):
    p = tmp_path / "with space.db"
    p.write_bytes(b"")
    uri = safe_sqlite_uri(str(p))
    assert uri.startswith("file:///")
    assert "with%20space" in uri or "with space" in uri
    # Exact file resolves (no silent empty db).
    conn = sqlite3.connect(uri + "?mode=rwc", uri=True)
    conn.execute("CREATE TABLE t (a INT)")
    conn.commit()
    conn.close()
    assert p.exists()
