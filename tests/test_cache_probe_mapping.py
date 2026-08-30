"""Tests for caching identity mapping."""

import sqlite3
import pytest
from pathlib import Path

from lr_ai_exposure.cache_probe import find_preview_uuid


def test_find_preview_uuid_cardinality(tmp_path: Path):
    db_path = tmp_path / "previews.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT)")

    # Missing
    assert find_preview_uuid(str(db_path), 123)["status"] == "MISSING"

    # Found exactly 1 (integer passed)
    conn.execute("INSERT INTO ImageCacheEntry VALUES ('123', 'uuid1')")
    conn.commit()
    res = find_preview_uuid(str(db_path), 123)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "uuid1"

    # Found exactly 1 (float passed)
    res = find_preview_uuid(str(db_path), 123.0)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "uuid1"

    # Found exactly 1 (string passed)
    res = find_preview_uuid(str(db_path), "123")
    assert res["status"] == "FOUND"

    # Multiple distinct UUIDs = AMBIGUOUS
    conn.execute("INSERT INTO ImageCacheEntry VALUES ('123', 'uuid2')")
    conn.commit()
    res = find_preview_uuid(str(db_path), 123)
    assert res["status"] == "AMBIGUOUS"

    # Multiple same UUIDs = FOUND (because SELECT DISTINCT)
    conn.execute("DELETE FROM ImageCacheEntry")
    conn.execute("INSERT INTO ImageCacheEntry VALUES ('999', 'uuid999')")
    conn.execute("INSERT INTO ImageCacheEntry VALUES ('999', 'uuid999')")
    conn.commit()
    res = find_preview_uuid(str(db_path), 999)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "uuid999"

    conn.close()

def test_find_preview_uuid_db_error():
    res = find_preview_uuid("/does/not/exist.db", 123)
    assert res["status"] == "DB_ERROR"
