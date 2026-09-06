import os
import sqlite3
from typing import Any

from lr_ai_exposure.db_uri import safe_sqlite_uri


def _identity_candidates(id_local: int | float | str) -> tuple[list[Any], list[str]]:
    """Return robust numeric/text candidates for Lightroom ImageCacheEntry.imageId."""
    id_local_str = str(id_local).strip()
    if id_local_str.endswith(".0"):
        id_local_str = id_local_str[:-2]

    numeric_cands: list[Any] = []
    try:
        if "." in id_local_str:
            numeric_cands.append(float(id_local_str))
        else:
            numeric_cands.append(int(id_local_str))
    except (TypeError, ValueError):
        pass
    text_cands = [id_local_str, id_local_str + ".0", str(id_local).strip()]
    return numeric_cands, text_cands


def _dedupe_rows(rows: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[tuple[Any, ...]] = []
    for row in rows:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def find_preview_uuid(previews_db_path: str, id_local: int | float | str) -> dict:
    """
    Find the preview UUID for a given Lightroom id_local using ImageCacheEntry.
    Enforces exact UUID cardinality while preserving compatibility with cache
    schemas that do not expose orientation.
    """
    try:
        db = sqlite3.connect(safe_sqlite_uri(previews_db_path) + "?mode=ro&immutable=1", uri=True, timeout=30.0)
    except Exception:
        return {"status": "DB_ERROR", "uuid": None}

    try:
        numeric_cands, text_cands = _identity_candidates(id_local)
        rows: list[tuple[Any, ...]] = []
        for cand in numeric_cands + text_cands:
            rows.extend(
                db.execute(
                    "SELECT DISTINCT uuid FROM ImageCacheEntry WHERE imageId = ?;",
                    (cand,),
                ).fetchall()
            )
        rows = _dedupe_rows(rows)
        if len(rows) == 0:
            return {"status": "MISSING", "uuid": None}
        if len(rows) == 1:
            return {"status": "FOUND", "uuid": rows[0][0]}
        return {"status": "AMBIGUOUS", "uuid": None}
    except Exception:
        return {"status": "DB_ERROR", "uuid": None}
    finally:
        db.close()


def find_preview_record(previews_db_path: str, id_local: int | float | str) -> dict:
    """Resolve exactly one preview UUID plus Lightroom orientation code.

    Canonical package extraction needs the orientation carried by the same
    ImageCacheEntry record as the UUID. A missing orientation column or
    conflicting UUID/orientation rows fails closed instead of guessing.
    """
    try:
        db = sqlite3.connect(safe_sqlite_uri(previews_db_path) + "?mode=ro&immutable=1", uri=True, timeout=30.0)
    except Exception:
        return {"status": "DB_ERROR", "uuid": None, "orientation": None}

    try:
        columns = {
            str(row[1]) for row in db.execute('PRAGMA table_info("ImageCacheEntry")')
        }
        if "orientation" not in columns:
            return {
                "status": "DB_ERROR",
                "uuid": None,
                "orientation": None,
                "error": "ORIENTATION_COLUMN_MISSING",
            }

        numeric_cands, text_cands = _identity_candidates(id_local)
        rows: list[tuple[Any, ...]] = []
        for cand in numeric_cands + text_cands:
            rows.extend(
                db.execute(
                    "SELECT DISTINCT uuid, orientation FROM ImageCacheEntry WHERE imageId = ?;",
                    (cand,),
                ).fetchall()
            )
        rows = _dedupe_rows(rows)
        if len(rows) == 0:
            return {"status": "MISSING", "uuid": None, "orientation": None}
        if len(rows) == 1:
            return {
                "status": "FOUND",
                "uuid": rows[0][0],
                "orientation": rows[0][1],
            }
        return {"status": "AMBIGUOUS", "uuid": None, "orientation": None}
    except Exception:
        return {"status": "DB_ERROR", "uuid": None, "orientation": None}
    finally:
        db.close()


def extract_root_pixel_jpeg(root_pixels_db_path: str, preview_uuid: str, output_path: str) -> bool:
    """Extract the jpegData for a given preview UUID from RootPixels."""
    db = sqlite3.connect(safe_sqlite_uri(root_pixels_db_path) + "?mode=ro&immutable=1", uri=True, timeout=30.0)
    try:
        cursor = db.execute("SELECT jpegData FROM RootPixels WHERE uuid = ?;", (preview_uuid,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as file:
            file.write(row[0])
        return True
    finally:
        db.close()


def run_mapping_probe(previews_db: str, root_db: str, id_local: int | float, out_jpg: str) -> dict:
    """End-to-end mapping from Lightroom id_local to extracted JPEG."""
    res = find_preview_uuid(previews_db, id_local)
    if res["status"] != "FOUND":
        return {"status": res["status"], "id_local": id_local, "uuid": None}

    uuid = res["uuid"]
    success = extract_root_pixel_jpeg(root_db, uuid, out_jpg)
    if not success:
        return {"status": "MISSING_JPEG_DATA", "id_local": id_local, "uuid": uuid}

    return {"status": "FOUND", "id_local": id_local, "uuid": uuid, "output": out_jpg}
