from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

from PIL import Image, ImageChops

from lr_ai_exposure.session_lifecycle import prepare_session_pass


def _solid_jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 213), (20, 80, 180)).save(output, format="JPEG", quality=95)
    return output.getvalue()


def test_contact_sheet_tile_uses_orientation_normalized_preview(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    raw_path = source_dir / "portrait.NEF"
    raw_path.write_bytes(b"raw")

    lrdata_dir = tmp_path / "Previews.lrdata"
    lrdata_dir.mkdir()
    with sqlite3.connect(lrdata_dir / "previews.db") as db:
        db.execute(
            "CREATE TABLE ImageCacheEntry (imageId INTEGER, uuid TEXT, digest TEXT, orientation TEXT)"
        )
        db.execute(
            "INSERT INTO ImageCacheEntry VALUES (1, 'uuid-1', 'digest', 'DA')"
        )
    with sqlite3.connect(lrdata_dir / "root-pixels.db") as db:
        db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.execute("INSERT INTO RootPixels VALUES ('uuid-1', ?)", (_solid_jpeg(),))

    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "source_folder": str(source_dir),
                "photos": [
                    {"id_local": "1", "uuid": "uuid-1", "path": str(raw_path)}
                ],
            }
        ),
        encoding="utf-8",
    )

    prepared = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-orientation-contact-sheet",
    )
    pass_dir = Path(prepared["pass_dir"])

    with Image.open(pass_dir / "previews" / "000001__portrait.jpg") as preview:
        assert preview.size == (213, 320)

    index = json.loads(
        (pass_dir / "contact-sheet-index.json").read_text(encoding="utf-8")
    )
    sheet_path = pass_dir / index["sheets"][0]["sheet_path"]
    with Image.open(sheet_path) as sheet:
        image_area = sheet.crop((0, 0, 320, 216)).convert("RGB")
        white = Image.new("RGB", image_area.size, "white")
        bbox = ImageChops.difference(image_area, white).getbbox()

    assert bbox is not None
    left, top, right, bottom = bbox
    assert right - left < 200
    assert bottom - top > 200
