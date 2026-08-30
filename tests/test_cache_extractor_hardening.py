"""Tests for Phase B cache extractor hardening."""

import os
import sqlite3
import pytest
from pathlib import Path

from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch


def test_snapshot_cache_dbs(tmp_path: Path):
    lrdata = tmp_path / "lrdata"
    lrdata.mkdir()

    # Create valid mock DBs
    p_db = lrdata / "previews.db"
    r_db = lrdata / "root-pixels.db"

    for db_path in [p_db, r_db]:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE Test (id INTEGER)")
        conn.commit()
        conn.close()

    snap_dir = tmp_path / "snapshot"
    snapshot_cache_dbs(str(lrdata), str(snap_dir))

    assert (snap_dir / "previews.db").exists()
    assert (snap_dir / "root-pixels.db").exists()


def test_extract_batch_invalid_jpeg(tmp_path: Path):
    snap_dir = tmp_path / "snapshot"
    snap_dir.mkdir()

    # Create mock DBs
    p_db = snap_dir / "previews.db"
    r_db = snap_dir / "root-pixels.db"

    conn1 = sqlite3.connect(p_db)
    conn1.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT)")
    conn1.execute("INSERT INTO ImageCacheEntry VALUES ('123', 'uuid1')")
    conn1.commit()
    conn1.close()

    conn2 = sqlite3.connect(r_db)
    conn2.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
    conn2.execute("INSERT INTO RootPixels VALUES ('uuid1', x'00000000')") # Invalid JPEG
    conn2.commit()
    conn2.close()

    out_dir = tmp_path / "out"
    identities = [{"id_local": "123", "path": "test.cr2"}]

    results = extract_batch(identities, str(snap_dir), str(out_dir))
    assert results[0]["status"] == "INVALID_JPEG"


def test_extract_batch_valid_jpeg(tmp_path: Path):
    snap_dir = tmp_path / "snapshot"
    snap_dir.mkdir()

    p_db = snap_dir / "previews.db"
    r_db = snap_dir / "root-pixels.db"

    conn1 = sqlite3.connect(p_db)
    conn1.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT)")
    conn1.execute("INSERT INTO ImageCacheEntry VALUES ('456', 'uuid2')")
    conn1.commit()
    conn1.close()

    # 100+ bytes fake JPEG
    fake_jpeg = b"\xff\xd8" + b"\x00" * 100
    conn2 = sqlite3.connect(r_db)
    conn2.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
    conn2.execute("INSERT INTO RootPixels VALUES ('uuid2', ?)", (fake_jpeg,))
    conn2.commit()
    conn2.close()

    out_dir = tmp_path / "out"
    identities = [{"id_local": "456", "path": "test2.cr2"}]

    results = extract_batch(identities, str(snap_dir), str(out_dir))
    assert results[0]["status"] == "FOUND"
    assert "test2.jpg" in results[0]["output"]
