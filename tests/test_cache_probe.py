import os
import sqlite3
import pytest
from lr_ai_exposure.cache_probe import find_preview_uuid, extract_root_pixel_jpeg, run_mapping_probe

@pytest.fixture
def mock_dbs(tmp_path):
    previews_db = tmp_path / "previews.db"
    root_db = tmp_path / "root-pixels.db"
    
    pdb = sqlite3.connect(previews_db)
    pdb.execute("CREATE TABLE ImageCacheEntry (imageId REAL, uuid TEXT, digest TEXT, orientation TEXT)")
    # Exactly one
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (1001.0, 'UUID-1001', 'digest', 'A')")
    # Multiple (Ambiguous)
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (1002.0, 'UUID-1002A', 'digest', 'A')")
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (1002.0, 'UUID-1002B', 'digest', 'A')")
    pdb.commit()
    pdb.close()
    
    rdb = sqlite3.connect(root_db)
    rdb.execute("CREATE TABLE RootPixels (uuid TEXT, digest TEXT, colorProfile TEXT, croppedWidth REAL, croppedHeight REAL, quality REAL, jpegData BLOB)")
    rdb.execute("INSERT INTO RootPixels VALUES ('UUID-1001', 'digest', 'prof', 600, 400, 0.8, x'FFD8FFE0')")
    rdb.commit()
    rdb.close()
    
    return str(previews_db), str(root_db)

def test_find_preview_uuid_cardinality(mock_dbs):
    previews_db, _ = mock_dbs
    
    # Exactly one
    res1 = find_preview_uuid(previews_db, 1001.0)
    assert res1["status"] == "FOUND"
    assert res1["uuid"] == "UUID-1001"
    
    # Multiple (Ambiguous)
    res2 = find_preview_uuid(previews_db, 1002.0)
    assert res2["status"] == "AMBIGUOUS"
    assert res2["uuid"] is None
    
    # Zero (Missing)
    res3 = find_preview_uuid(previews_db, 9999.0)
    assert res3["status"] == "MISSING"
    assert res3["uuid"] is None

def test_extract_root_pixel_jpeg(mock_dbs, tmp_path):
    _, root_db = mock_dbs
    out_path = tmp_path / "out.jpg"
    
    # Valid extraction
    success = extract_root_pixel_jpeg(root_db, "UUID-1001", str(out_path))
    assert success is True
    assert out_path.exists()
    assert out_path.read_bytes() == b'\xff\xd8\xff\xe0'
    
    # Missing JPEG
    missing = extract_root_pixel_jpeg(root_db, "NON-EXISTENT", str(tmp_path / "missing.jpg"))
    assert missing is False

def test_run_mapping_probe(mock_dbs, tmp_path):
    previews_db, root_db = mock_dbs
    out_jpg = str(tmp_path / "extracted.jpg")
    
    # Valid
    res = run_mapping_probe(previews_db, root_db, 1001.0, out_jpg)
    assert res["status"] == "FOUND"
    assert res["uuid"] == "UUID-1001"
    assert os.path.exists(res["output"])
    
    # Missing cache entry
    res_miss = run_mapping_probe(previews_db, root_db, 9999.0, out_jpg)
    assert res_miss["status"] == "MISSING"
    
    # Ambiguous
    res_ambig = run_mapping_probe(previews_db, root_db, 1002.0, out_jpg)
    assert res_ambig["status"] == "AMBIGUOUS"
    
    # Found entry but missing RootPixels JPEG
    # Let's insert a cache entry without root pixel
    pdb = sqlite3.connect(previews_db)
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (1003.0, 'UUID-NO-JPEG', 'digest', 'A')")
    pdb.commit()
    pdb.close()
    
    res_no_jpeg = run_mapping_probe(previews_db, root_db, 1003.0, out_jpg)
    assert res_no_jpeg["status"] == "MISSING_JPEG_DATA"
    assert res_no_jpeg["uuid"] == "UUID-NO-JPEG"
