from __future__ import annotations

import hashlib
import io
import sqlite3
from pathlib import Path

from PIL import Image

from lr_ai_exposure.cache_extractor import extract_batch
from lr_ai_exposure.cache_probe import find_preview_record


def _jpeg_bytes(width: int = 12, height: int = 8) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    for x in range(width // 2):
        for y in range(height):
            image.putpixel((x, y), (220, 20, 20))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def _write_snapshot(snapshot_dir: Path, rows: list[tuple[str, str, str]], jpeg_by_uuid: dict[str, bytes]) -> None:
    snapshot_dir.mkdir(parents=True)
    with sqlite3.connect(snapshot_dir / "previews.db") as db:
        db.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT, orientation TEXT)")
        db.executemany("INSERT INTO ImageCacheEntry VALUES (?, ?, ?)", rows)
    with sqlite3.connect(snapshot_dir / "root-pixels.db") as db:
        db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.executemany("INSERT INTO RootPixels VALUES (?, ?)", list(jpeg_by_uuid.items()))


def test_preview_record_carries_orientation_and_conflicts_fail_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "previews.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT, orientation TEXT)")
        db.execute("INSERT INTO ImageCacheEntry VALUES ('1', 'uuid-1', 'DA')")

    found = find_preview_record(str(db_path), "1")
    assert found == {"status": "FOUND", "uuid": "uuid-1", "orientation": "DA"}

    with sqlite3.connect(db_path) as db:
        db.execute("INSERT INTO ImageCacheEntry VALUES ('1', 'uuid-1', 'AB')")

    ambiguous = find_preview_record(str(db_path), "1")
    assert ambiguous["status"] == "AMBIGUOUS"
    assert ambiguous["uuid"] is None
    assert ambiguous["orientation"] is None


def test_preview_record_requires_orientation_column(tmp_path: Path) -> None:
    db_path = tmp_path / "previews.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT)")
        db.execute("INSERT INTO ImageCacheEntry VALUES ('1', 'uuid-1')")

    result = find_preview_record(str(db_path), "1")
    assert result["status"] == "DB_ERROR"
    assert result["error"] == "ORIENTATION_COLUMN_MISSING"


def test_extract_batch_normalizes_rotations_and_preserves_raw_fingerprint(tmp_path: Path) -> None:
    raw_jpeg = _jpeg_bytes()
    raw_sha = hashlib.sha256(raw_jpeg).hexdigest()
    snapshot_dir = tmp_path / "snapshot"
    rows = [
        ("1", "uuid-ab", "AB"),
        ("2", "uuid-bc", "BC"),
        ("3", "uuid-cd", "CD"),
        ("4", "uuid-da", "DA"),
    ]
    _write_snapshot(snapshot_dir, rows, {uuid: raw_jpeg for _, uuid, _ in rows})

    results = extract_batch(
        [{"id_local": str(i), "path": f"D:/photos/{i}.NEF"} for i in range(1, 5)],
        str(snapshot_dir),
        str(tmp_path / "out"),
    )

    assert [item["status"] for item in results] == ["FOUND"] * 4
    assert [item["orientation"] for item in results] == ["AB", "BC", "CD", "DA"]
    assert all(item["source_preview_sha256"] == raw_sha for item in results)

    outputs = [Path(item["output"]) for item in results]
    assert outputs[0].read_bytes() == raw_jpeg
    with Image.open(outputs[0]) as image:
        assert image.size == (12, 8)
    with Image.open(outputs[1]) as image:
        assert image.size == (8, 12)
    with Image.open(outputs[2]) as image:
        assert image.size == (12, 8)
    with Image.open(outputs[3]) as image:
        assert image.size == (8, 12)


def test_extract_batch_rejects_mirrored_or_unknown_orientation(tmp_path: Path) -> None:
    raw_jpeg = _jpeg_bytes()
    snapshot_dir = tmp_path / "snapshot"
    _write_snapshot(
        snapshot_dir,
        [("1", "uuid-ba", "BA"), ("2", "uuid-x", "XX")],
        {"uuid-ba": raw_jpeg, "uuid-x": raw_jpeg},
    )

    results = extract_batch(
        [
            {"id_local": "1", "path": "D:/photos/1.NEF"},
            {"id_local": "2", "path": "D:/photos/2.NEF"},
        ],
        str(snapshot_dir),
        str(tmp_path / "out"),
    )

    assert [item["status"] for item in results] == ["UNSUPPORTED_ORIENTATION", "UNSUPPORTED_ORIENTATION"]
    assert all(item["output"] is None for item in results)
