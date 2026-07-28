import sqlite3
import os

def find_preview_uuid(previews_db_path: str, id_local: int | float) -> str | None:
    """
    Find the preview UUID for a given Lightroom id_local using ImageCacheEntry.
    Connects in read-only mode to prevent locking or mutation.
    """
    # SQLite uri=True allows mode=ro
    db = sqlite3.connect(f"file:{previews_db_path}?mode=ro", uri=True)
    try:
        cursor = db.execute("SELECT uuid FROM ImageCacheEntry WHERE imageId = ?;", (id_local,))
        row = cursor.fetchone()
        return row[0] if row else None
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
    uuid = find_preview_uuid(previews_db, id_local)
    if not uuid:
        return {"status": "MISSING_CACHE_ENTRY", "id_local": id_local}
        
    success = extract_root_pixel_jpeg(root_db, uuid, out_jpg)
    if not success:
        return {"status": "MISSING_JPEG_DATA", "id_local": id_local, "uuid": uuid}
        
    return {"status": "FOUND", "id_local": id_local, "uuid": uuid, "output": out_jpg}
