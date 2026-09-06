"""Hardened read-only Lightroom preview-cache extractor."""

import hashlib
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, JpegImagePlugin

from lr_ai_exposure.cache_probe import extract_root_pixel_jpeg, find_preview_record
from lr_ai_exposure.db_uri import safe_sqlite_uri


SUPPORTED_ROTATION_ORIENTATIONS = frozenset({"AB", "BC", "CD", "DA"})


def _validate_sqlite_db(path: str) -> bool:
    """Run PRAGMA quick_check."""
    uri = safe_sqlite_uri(path) + "?mode=ro&immutable=1"
    try:
        db = sqlite3.connect(uri, uri=True, timeout=30.0)
        cursor = db.execute("PRAGMA quick_check;")
        result = cursor.fetchone()
        db.close()
        return bool(result and result[0] == "ok")
    except Exception:
        return False


def snapshot_cache_dbs(lrdata_dir: str, snapshot_dir: str) -> tuple[str, str]:
    """Create validated read-only SQLite backups of the two preview databases."""
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
        src_conn = sqlite3.connect(safe_sqlite_uri(previews_src) + "?mode=ro&immutable=1", uri=True, timeout=30.0)
        dst_conn = sqlite3.connect(previews_temp, timeout=30.0)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()

        src_conn = sqlite3.connect(safe_sqlite_uri(root_src) + "?mode=ro&immutable=1", uri=True, timeout=30.0)
        dst_conn = sqlite3.connect(root_temp, timeout=30.0)
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
    """Validate the JPEG signature and a non-trivial byte length."""
    try:
        with open(path, "rb") as file:
            content = file.read()
        return len(content) >= 100 and content.startswith(b"\xff\xd8")
    except Exception:
        return False


def _normalize_preview_orientation(path: str, orientation: str) -> None:
    """Rotate an extracted package JPEG to Lightroom display orientation.

    Lightroom cache rotation codes supported here are the non-mirrored forms:
    AB=0 degrees, BC=90 CW, CD=180, DA=270 CW. Mirrored codes deliberately
    fail closed until their semantics are explicitly required and tested.
    """
    if orientation not in SUPPORTED_ROTATION_ORIENTATIONS:
        raise ValueError(f"unsupported Lightroom preview orientation: {orientation!r}")
    if orientation == "AB":
        return

    transpose = {
        "BC": Image.Transpose.ROTATE_270,  # 90 degrees clockwise
        "CD": Image.Transpose.ROTATE_180,
        "DA": Image.Transpose.ROTATE_90,   # 270 degrees clockwise
    }[orientation]
    source_path = Path(path)
    normalized_path = source_path.with_suffix(source_path.suffix + ".oriented.tmp")
    try:
        with Image.open(source_path) as image:
            if image.format != "JPEG":
                raise ValueError("extracted preview is not JPEG")
            image.load()
            transformed = image.transpose(transpose)
            save_kwargs: dict[str, Any] = {"format": "JPEG", "optimize": False}
            quantization = getattr(image, "quantization", None)
            if quantization:
                save_kwargs["qtables"] = quantization
                try:
                    save_kwargs["subsampling"] = JpegImagePlugin.get_sampling(image)
                except (AttributeError, ValueError):
                    pass
            else:
                save_kwargs["quality"] = 95
            if image.info.get("icc_profile"):
                save_kwargs["icc_profile"] = image.info["icc_profile"]
            transformed.save(normalized_path, **save_kwargs)
        os.replace(normalized_path, source_path)
    finally:
        if normalized_path.exists():
            normalized_path.unlink(missing_ok=True)


def extract_batch(
    identities: List[Dict[str, Any]], snapshot_dir: str, out_dir: str
) -> List[Dict[str, Any]]:
    """Extract orientation-correct package JPEGs from read-only cache snapshots."""
    previews_db = os.path.join(snapshot_dir, "previews.db")
    root_db = os.path.join(snapshot_dir, "root-pixels.db")
    if not os.path.exists(previews_db) or not os.path.exists(root_db):
        raise FileNotFoundError("DB_OPEN_ERROR: Snapshotted databases missing")

    os.makedirs(out_dir, exist_ok=True)
    results: list[dict[str, Any]] = []
    for index, ident in enumerate(identities):
        seq = index + 1
        id_local = ident.get("id_local")
        src_path = ident.get("path")
        if id_local is None or src_path is None:
            results.append(
                {
                    "status": "ERROR",
                    "id_local": id_local,
                    "path": src_path,
                    "error": "Missing identity fields",
                }
            )
            continue

        stem = os.path.splitext(os.path.basename(src_path))[0]
        out_name = f"{seq:06d}__{stem}.jpg"
        out_path = os.path.join(out_dir, out_name)

        res = find_preview_record(previews_db, id_local)
        if res["status"] != "FOUND":
            results.append(
                {
                    "status": res["status"],
                    "id_local": id_local,
                    "path": src_path,
                    "uuid": None,
                    "orientation": None,
                    "output": None,
                    **({"error": res["error"]} if res.get("error") else {}),
                }
            )
            continue

        uuid = res["uuid"]
        orientation = res.get("orientation")
        if orientation not in SUPPORTED_ROTATION_ORIENTATIONS:
            results.append(
                {
                    "status": "UNSUPPORTED_ORIENTATION",
                    "id_local": id_local,
                    "path": src_path,
                    "uuid": uuid,
                    "orientation": orientation,
                    "output": None,
                }
            )
            continue

        temp_path = out_path + ".tmp"
        try:
            success = extract_root_pixel_jpeg(root_db, uuid, temp_path)
            if not success:
                results.append(
                    {
                        "status": "MISSING",
                        "id_local": id_local,
                        "path": src_path,
                        "uuid": uuid,
                        "orientation": orientation,
                        "output": None,
                    }
                )
                continue
            if not _validate_jpeg(temp_path):
                os.remove(temp_path)
                results.append(
                    {
                        "status": "INVALID_JPEG",
                        "id_local": id_local,
                        "path": src_path,
                        "uuid": uuid,
                        "orientation": orientation,
                        "output": None,
                    }
                )
                continue

            source_preview_sha256 = hashlib.sha256(Path(temp_path).read_bytes()).hexdigest()
            try:
                _normalize_preview_orientation(temp_path, orientation)
            except (OSError, ValueError) as exc:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                results.append(
                    {
                        "status": "ORIENTATION_NORMALIZE_ERROR",
                        "id_local": id_local,
                        "path": src_path,
                        "uuid": uuid,
                        "orientation": orientation,
                        "output": None,
                        "error": str(exc),
                    }
                )
                continue

            os.replace(temp_path, out_path)
            results.append(
                {
                    "status": "FOUND",
                    "id_local": id_local,
                    "path": src_path,
                    "uuid": uuid,
                    "orientation": orientation,
                    "source_preview_sha256": source_preview_sha256,
                    "output": out_path,
                }
            )
        except Exception as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            results.append(
                {
                    "status": "OUTPUT_WRITE_ERROR",
                    "id_local": id_local,
                    "path": src_path,
                    "uuid": uuid,
                    "orientation": orientation,
                    "output": None,
                    "error": str(exc),
                }
            )

    return results
