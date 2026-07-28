import os
import sqlite3
import pytest
from lr_ai_exposure.cache_probe import find_preview_uuid, extract_root_pixel_jpeg, run_mapping_probe

@pytest.fixture
def mock_dbs(tmp_path):
    previews_db = tmp_path / "previews.db"
    root_db = tmp_path / "root-pixels.db"
    
    # Create mock previews.db
    pdb = sqlite3.connect(previews_db)
    pdb.execute("CREATE TABLE ImageCacheEntry (imageId REAL, uuid TEXT, digest TEXT, orientation TEXT)")
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (1234.0, 'UUID-123', 'digest', 'A')")
    pdb.commit()
    pdb.close()
    
    # Create mock root-pixels.db
    rdb = sqlite3.connect(root_db)
    rdb.execute("CREATE TABLE RootPixels (uuid TEXT, digest TEXT, colorProfile TEXT, croppedWidth REAL, croppedHeight REAL, quality REAL, jpegData BLOB)")
    rdb.execute("INSERT INTO RootPixels VALUES ('UUID-123', 'digest', 'prof', 600, 400, 0.8, x'FFD8FFE0')")
    rdb.commit()
    rdb.close()
    
    return str(previews_db), str(root_db)

def test_find_preview_uuid(mock_dbs):
    previews_db, _ = mock_dbs
    
    uuid = find_preview_uuid(previews_db, 1234.0)
    assert uuid == "UUID-123"
    
    missing = find_preview_uuid(previews_db, 9999)
    assert missing is None

def test_extract_root_pixel_jpeg(mock_dbs, tmp_path):
    _, root_db = mock_dbs
    out_path = tmp_path / "out.jpg"
    
    success = extract_root_pixel_jpeg(root_db, "UUID-123", str(out_path))
    assert success is True
    assert out_path.exists()
    assert out_path.read_bytes() == b'\xff\xd8\xff\xe0'
    
    missing = extract_root_pixel_jpeg(root_db, "NON-EXISTENT", str(tmp_path / "missing.jpg"))
    assert missing is False

def test_run_mapping_probe(mock_dbs, tmp_path):
    previews_db, root_db = mock_dbs
    out_jpg = str(tmp_path / "extracted.jpg")
    
    res = run_mapping_probe(previews_db, root_db, 1234.0, out_jpg)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "UUID-123"
    assert os.path.exists(res["output"])
    
    res_miss = run_mapping_probe(previews_db, root_db, 999, out_jpg)
    assert res_miss["status"] == "MISSING_CACHE_ENTRY"
