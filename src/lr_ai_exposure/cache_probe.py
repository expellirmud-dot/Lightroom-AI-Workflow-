from __future__ import annotations

import os
import sqlite3
from pathlib import Path
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
    """Resolve exactly one Lightroom preview UUID for an image identity."""
    try:
        db = sqlite3.connect(
            safe_sqlite_uri(previews_db_path) + "?mode=ro&immutable=1",
            uri=True,
            timeout=30.0,
        )
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
    """Resolve one preview UUID, digest (when available), and orientation.

    Canonical Standard Preview reuse needs the digest from the same
    ImageCacheEntry row used for UUID/orientation. Older synthetic/legacy cache
    schemas without a digest column remain readable for root-pixel compatibility;
    those records simply cannot authorize Standard Preview tier lookup.
    """
    try:
        db = sqlite3.connect(
            safe_sqlite_uri(previews_db_path) + "?mode=ro&immutable=1",
            uri=True,
            timeout=30.0,
        )
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

        has_digest = "digest" in columns
        select_columns = "uuid, digest, orientation" if has_digest else "uuid, orientation"
        numeric_cands, text_cands = _identity_candidates(id_local)
        rows: list[tuple[Any, ...]] = []
        for cand in numeric_cands + text_cands:
            rows.extend(
                db.execute(
                    f"SELECT DISTINCT {select_columns} FROM ImageCacheEntry WHERE imageId = ?;",
                    (cand,),
                ).fetchall()
            )
        rows = _dedupe_rows(rows)
        if len(rows) == 0:
            return {"status": "MISSING", "uuid": None, "orientation": None}
        if len(rows) != 1:
            return {"status": "AMBIGUOUS", "uuid": None, "orientation": None}

        if has_digest:
            uuid, digest, orientation = rows[0]
            return {
                "status": "FOUND",
                "uuid": uuid,
                "digest": digest,
                "orientation": orientation,
            }
        uuid, orientation = rows[0]
        return {"status": "FOUND", "uuid": uuid, "orientation": orientation}
    except Exception:
        return {"status": "DB_ERROR", "uuid": None, "orientation": None}
    finally:
        db.close()


def find_cached_preview_tier(
    lrdata_dir: str | Path,
    preview_uuid: str,
    digest: str,
    target_size: int,
) -> dict[str, Any]:
    """Find an existing Lightroom-rendered preview tier without modifying cache.

    Lightroom stores extensionless JPEG files beneath a deterministic UUID bucket
    using names of the form ``<uuid>-<digest>_<tier>``. Exact target wins;
    otherwise the smallest existing larger tier is selected. Smaller tiers are
    never silently substituted.
    """
    if not isinstance(target_size, int) or isinstance(target_size, bool) or target_size <= 0:
        raise ValueError("target_size must be a positive integer")
    if not preview_uuid or not digest:
        return {
            "status": "PREVIEW_TIER_NOT_READY",
            "path": None,
            "tier": None,
            "available_tiers": [],
            "error": "PREVIEW_IDENTITY_DIGEST_MISSING",
        }
    if any(sep in preview_uuid or sep in digest for sep in ("/", "\\")):
        return {
            "status": "PREVIEW_TIER_NOT_READY",
            "path": None,
            "tier": None,
            "available_tiers": [],
            "error": "PREVIEW_IDENTITY_PATH_UNSAFE",
        }

    root = Path(lrdata_dir).resolve()
    bucket = root / preview_uuid[:1] / preview_uuid[:4]
    try:
        bucket.resolve().relative_to(root)
    except ValueError:
        return {
            "status": "PREVIEW_TIER_NOT_READY",
            "path": None,
            "tier": None,
            "available_tiers": [],
            "error": "PREVIEW_BUCKET_ESCAPES_CACHE",
        }

    prefix = f"{preview_uuid}-{digest}_"
    candidates: dict[int, Path] = {}
    if bucket.is_dir():
        for path in bucket.iterdir():
            if not path.is_file() or not path.name.startswith(prefix):
                continue
            suffix = path.name[len(prefix):]
            if not suffix.isdigit():
                continue
            tier = int(suffix)
            candidates.setdefault(tier, path)

    available = sorted(candidates)
    eligible = [tier for tier in available if tier >= target_size]
    if not eligible:
        return {
            "status": "PREVIEW_TIER_NOT_READY",
            "path": None,
            "tier": None,
            "available_tiers": available,
        }

    selected_tier = target_size if target_size in candidates else min(eligible)
    selected_path = candidates[selected_tier].resolve()
    try:
        selected_path.relative_to(root)
    except ValueError:
        return {
            "status": "PREVIEW_TIER_NOT_READY",
            "path": None,
            "tier": None,
            "available_tiers": available,
            "error": "PREVIEW_FILE_ESCAPES_CACHE",
        }
    return {
        "status": "FOUND",
        "path": str(selected_path),
        "tier": selected_tier,
        "available_tiers": available,
    }


def extract_root_pixel_jpeg(
    root_pixels_db_path: str, preview_uuid: str, output_path: str
) -> bool:
    """Extract RootPixels jpegData for legacy/read-only compatibility tooling."""
    db = sqlite3.connect(
        safe_sqlite_uri(root_pixels_db_path) + "?mode=ro&immutable=1",
        uri=True,
        timeout=30.0,
    )
    try:
        cursor = db.execute(
            "SELECT jpegData FROM RootPixels WHERE uuid = ?;", (preview_uuid,)
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as file:
            file.write(row[0])
        return True
    finally:
        db.close()


def run_mapping_probe(
    previews_db: str, root_db: str, id_local: int | float, out_jpg: str
) -> dict:
    """Legacy end-to-end mapping from Lightroom id_local to RootPixels JPEG."""
    res = find_preview_uuid(previews_db, id_local)
    if res["status"] != "FOUND":
        return {"status": res["status"], "id_local": id_local, "uuid": None}

    uuid = res["uuid"]
    success = extract_root_pixel_jpeg(root_db, uuid, out_jpg)
    if not success:
        return {
            "status": "MISSING_JPEG_DATA",
            "id_local": id_local,
            "uuid": uuid,
        }

    return {"status": "FOUND", "id_local": id_local, "uuid": uuid, "output": out_jpg}
