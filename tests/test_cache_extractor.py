import os
import sqlite3
import pytest
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch

@pytest.fixture
def dummy_lrdata(tmp_path):
    lrdata = tmp_path / "Dummy.lrdata"
    lrdata.mkdir()
    
    # previews.db
    pdb_path = lrdata / "previews.db"
    pdb = sqlite3.connect(str(pdb_path))
    pdb.execute("CREATE TABLE ImageCacheEntry (imageId REAL, uuid TEXT, digest TEXT, orientation TEXT)")
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (101.0, 'UUID-101', 'digest', 'A')")
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (102.0, 'UUID-102', 'digest', 'A')")
    pdb.execute("INSERT INTO ImageCacheEntry VALUES (103.0, 'UUID-103', 'digest', 'A')")
    pdb.commit()
    pdb.close()
    
    # root-pixels.db
    rdb_path = lrdata / "root-pixels.db"
    rdb = sqlite3.connect(str(rdb_path))
    rdb.execute("CREATE TABLE RootPixels (uuid TEXT, digest TEXT, colorProfile TEXT, croppedWidth REAL, croppedHeight REAL, quality REAL, jpegData BLOB)")
    rdb.execute("INSERT INTO RootPixels VALUES ('UUID-101', 'digest', 'prof', 600, 400, 0.8, x'FFD8FFE0')")
    # UUID-102 missing root pixel
    rdb.execute("INSERT INTO RootPixels VALUES ('UUID-103', 'digest', 'prof', 600, 400, 0.8, x'FFD8FFE1')")
    rdb.commit()
    rdb.close()
    
    return str(lrdata)

def test_snapshot_cache_dbs(dummy_lrdata, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    previews_dst, root_dst = snapshot_cache_dbs(dummy_lrdata, str(snapshot_dir))
    
    assert os.path.exists(previews_dst)
    assert os.path.exists(root_dst)
    assert os.path.dirname(previews_dst) == str(snapshot_dir)

def test_extract_batch(dummy_lrdata, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_cache_dbs(dummy_lrdata, str(snapshot_dir))
    
    out_dir = str(tmp_path / "out")
    
    identities = [
        {"id_local": 101.0, "path": "C:/photos/IMG_01.CR2"},
        {"id_local": 102.0, "path": "C:/photos/IMG_02.CR2"}, # Missing jpeg
        {"id_local": 999.0, "path": "C:/photos/IMG_99.CR2"}, # Missing cache
        {"id_local": 103.0, "path": "C:/photos/IMG_03.CR2"},
        {"id_local": None, "path": "C:/photos/IMG_ERR.CR2"}, # Error
    ]
    
    results = extract_batch(identities, str(snapshot_dir), out_dir)
    assert len(results) == 5
    
    assert results[0]["status"] == "FOUND"
    assert results[0]["output"].endswith("000001__IMG_01.jpg")
    assert os.path.exists(results[0]["output"])
    
    assert results[1]["status"] == "MISSING"
    assert results[1]["output"] is None
    
    assert results[2]["status"] == "MISSING"
    
    assert results[3]["status"] == "FOUND"
    assert results[3]["output"].endswith("000004__IMG_03.jpg")
    assert os.path.exists(results[3]["output"])
    
    assert results[4]["status"] == "ERROR"
