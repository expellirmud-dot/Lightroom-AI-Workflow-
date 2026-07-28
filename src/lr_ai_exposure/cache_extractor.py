import os
import shutil
from typing import List, Dict, Any
from lr_ai_exposure.cache_probe import find_preview_uuid, extract_root_pixel_jpeg

def snapshot_cache_dbs(lrdata_dir: str, snapshot_dir: str) -> tuple[str, str]:
    """
    Creates a snapshot directory and copies previews.db and root-pixels.db into it.
    Returns the paths to the snapshotted databases.
    """
    os.makedirs(snapshot_dir, exist_ok=True)
    previews_src = os.path.join(lrdata_dir, "previews.db")
    root_src = os.path.join(lrdata_dir, "root-pixels.db")
    
    previews_dst = os.path.join(snapshot_dir, "previews.db")
    root_dst = os.path.join(snapshot_dir, "root-pixels.db")
    
    if os.path.exists(previews_src):
        shutil.copy2(previews_src, previews_dst)
    else:
        raise FileNotFoundError(f"previews.db not found in {lrdata_dir}")
        
    if os.path.exists(root_src):
        shutil.copy2(root_src, root_dst)
    else:
        raise FileNotFoundError(f"root-pixels.db not found in {lrdata_dir}")
        
    return previews_dst, root_dst

def extract_batch(identities: List[Dict[str, Any]], snapshot_dir: str, out_dir: str) -> List[Dict[str, Any]]:
    """
    Given a list of identity dicts (with 'id_local' and 'path'), extract their JPEGs.
    Preserves selection order and names outputs atomically as 000001__<stem>.jpg.
    Returns structured results.
    """
    previews_db = os.path.join(snapshot_dir, "previews.db")
    root_db = os.path.join(snapshot_dir, "root-pixels.db")
    
    if not os.path.exists(previews_db) or not os.path.exists(root_db):
        raise FileNotFoundError("Snapshotted databases missing in snapshot_dir")
        
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
                "status": "ERROR", 
                "id_local": id_local, 
                "path": src_path, 
                "error": str(e)
            })
            
    return results
