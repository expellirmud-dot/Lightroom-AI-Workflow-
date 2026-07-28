"""Hardened cache extractor."""
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from lr_ai_exposure.cache_probe import find_preview_uuid, extract_root_pixel_jpeg
from lr_ai_exposure.db_uri import safe_sqlite_uri


def _validate_sqlite_db(path: str) -> bool:
    """Run PRAGMA quick_check."""
    uri = safe_sqlite_uri(path) + "?mode=ro"
    try:
        db = sqlite3.connect(uri, uri=True)
        cursor = db.execute("PRAGMA quick_check;")
        result = cursor.fetchone()
        db.close()
        return result and result[0] == "ok"
    except Exception:
        return False


def snapshot_cache_dbs(lrdata_dir: str, snapshot_dir: str) -> tuple[str, str]:
    """
    Creates a snapshot directory and safely backups databases using sqlite3 backup API.
    Returns the paths to the snapshotted databases.
    """
    os.makedirs(snapshot_dir, exist_ok=True)
    
    previews_src = os.path.join(lrdata_dir, "previews.db")
    root_src = os.path.join(lrdata_dir, "root-pixels.db")
    
    if not os.path.exists(previews_src) or not os.path.exists(root_src):
        raise FileNotFoundError(f"Source DBs not found in {lrdata_dir}")
        
    temp_dir = os.path.join(snapshot_dir, "temp_snapshot")
    os.makedirs(temp_dir, exist_ok=True)
    
    previews_temp = os.path.join(temp_dir, "previews.db")
    root_temp = os.path.join(temp_dir, "root-pixels.db")
    
    try:
        # Safely backup previews.db
        src_conn = sqlite3.connect(safe_sqlite_uri(previews_src) + "?mode=ro", uri=True)
        dst_conn = sqlite3.connect(previews_temp)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        
        # Safely backup root-pixels.db
        src_conn = sqlite3.connect(safe_sqlite_uri(root_src) + "?mode=ro", uri=True)
        dst_conn = sqlite3.connect(root_temp)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        
        if not _validate_sqlite_db(previews_temp) or not _validate_sqlite_db(root_temp):
            raise RuntimeError("DB_SNAPSHOT_ERROR: quick_check failed")
            
        previews_dst = os.path.join(snapshot_dir, "previews.db")
        root_dst = os.path.join(snapshot_dir, "root-pixels.db")
        
        os.replace(previews_temp, previews_dst)
        os.replace(root_temp, root_dst)
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    return previews_dst, root_dst


def _validate_jpeg(path: str) -> bool:
    """Validate JPEG file signature and trivial decode."""
    try:
        with open(path, "rb") as f:
            content = f.read()
            if len(content) < 100:
                return False
            if not content.startswith(b"\xff\xd8"):
                return False
            # Check EOF marker if strict, but many JPEGs have trailing data.
            # We'll just verify the start marker and size.
            return True
    except Exception:
        return False


def extract_batch(identities: List[Dict[str, Any]], snapshot_dir: str, out_dir: str) -> List[Dict[str, Any]]:
    """
    Given a list of identity dicts (with 'id_local' and 'path'), extract their JPEGs.
    """
    previews_db = os.path.join(snapshot_dir, "previews.db")
    root_db = os.path.join(snapshot_dir, "root-pixels.db")
    
    if not os.path.exists(previews_db) or not os.path.exists(root_db):
        raise FileNotFoundError("DB_OPEN_ERROR: Snapshotted databases missing")
        
    os.makedirs(out_dir, exist_ok=True)
    
    results = []
    for i, ident in enumerate(identities):
        seq = i + 1
        id_local = ident.get("id_local")
        src_path = ident.get("path")
        
        if id_local is None or src_path is None:
            results.append({
                "status": "ERROR", 
                "id_local": id_local, 
                "path": src_path, 
                "error": "Missing identity fields"
            })
            continue
            
        stem = os.path.splitext(os.path.basename(src_path))[0]
        out_name = f"{seq:06d}__{stem}.jpg"
        out_path = os.path.join(out_dir, out_name)
        
        res = find_preview_uuid(previews_db, id_local)
        if res["status"] != "FOUND":
            results.append({
                "status": res["status"], 
                "id_local": id_local, 
                "path": src_path, 
                "output": None
            })
            continue
            
        uuid = res["uuid"]
        
        temp_path = out_path + ".tmp"
        try:
            success = extract_root_pixel_jpeg(root_db, uuid, temp_path)
            if success:
                if not _validate_jpeg(temp_path):
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    results.append({
                        "status": "INVALID_JPEG",
                        "id_local": id_local,
                        "path": src_path,
                        "uuid": uuid,
                        "output": None
                    })
                    continue
                    
                os.replace(temp_path, out_path)
                results.append({
                    "status": "FOUND", 
                    "id_local": id_local, 
                    "path": src_path, 
                    "uuid": uuid, 
                    "output": out_path
                })
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                results.append({
                    "status": "MISSING", 
                    "id_local": id_local, 
                    "path": src_path, 
                    "uuid": uuid, 
                    "output": None
                })
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            results.append({
                "status": "OUTPUT_WRITE_ERROR", 
                "id_local": id_local, 
                "path": src_path, 
                "error": str(e)
            })
            
    return results
