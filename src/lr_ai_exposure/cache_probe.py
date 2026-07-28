import sqlite3
import os

def find_preview_uuid(previews_db_path: str, id_local: int | float | str) -> dict:
    """
    Find the preview UUID for a given Lightroom id_local using ImageCacheEntry.
    Enforces exact cardinality.
    Returns: {"status": "FOUND"|"MISSING"|"AMBIGUOUS"|"DB_ERROR", "uuid": str|None}
    """
    try:
        db = sqlite3.connect(f"file:{previews_db_path}?mode=ro", uri=True)
    except Exception:
        return {"status": "DB_ERROR", "uuid": None}
        
    try:
        # Normalize id_local. SDK might pass float, int, or string.
        id_local_str = str(id_local).strip()
        if id_local_str.endswith('.0'):
            id_local_str = id_local_str[:-2]
            
        # Enforce exact cardinality with DISTINCT
        cursor = db.execute("SELECT DISTINCT uuid FROM ImageCacheEntry WHERE imageId = ?;", (id_local_str,))
        rows = cursor.fetchall()
        
        count = len(rows)
        if count == 0:
            return {"status": "MISSING", "uuid": None}
        elif count == 1:
            return {"status": "FOUND", "uuid": rows[0][0]}
        else:
            return {"status": "AMBIGUOUS", "uuid": None}
    except Exception:
        return {"status": "DB_ERROR", "uuid": None}
    finally:
        db.close()

def extract_root_pixel_jpeg(root_pixels_db_path: str, preview_uuid: str, output_path: str) -> bool:
    """
    Extract the jpegData for a given preview UUID from RootPixels.
    """
    db = sqlite3.connect(f"file:{root_pixels_db_path}?mode=ro", uri=True)
    try:
        cursor = db.execute("SELECT jpegData FROM RootPixels WHERE uuid = ?;", (preview_uuid,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return False
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(row[0])
        return True
    finally:
        db.close()

def run_mapping_probe(previews_db: str, root_db: str, id_local: int | float, out_jpg: str) -> dict:
    """
    End-to-end mapping from Lightroom id_local to extracted JPEG.
    """
    res = find_preview_uuid(previews_db, id_local)
    if res["status"] != "FOUND":
        return {"status": res["status"], "id_local": id_local, "uuid": None}
        
    uuid = res["uuid"]
    success = extract_root_pixel_jpeg(root_db, uuid, out_jpg)
    if not success:
        return {"status": "MISSING_JPEG_DATA", "id_local": id_local, "uuid": uuid}
        
    return {"status": "FOUND", "id_local": id_local, "uuid": uuid, "output": out_jpg}
