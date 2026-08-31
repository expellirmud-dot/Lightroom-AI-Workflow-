from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

from PIL import Image
import pytest

from lr_ai_exposure.ai_judge import Action, SinglePassDecision, Verdict
from lr_ai_exposure.session import SessionError
from lr_ai_exposure.session_lifecycle import prepare_session_pass


def _jpeg_bytes(index: int) -> bytes:
    image = Image.new("RGB", (320, 213), (index % 255, 80, 160))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue()


def _write_cache(lrdata_dir: Path, photos: list[dict[str, str]]) -> None:
    lrdata_dir.mkdir()
    with sqlite3.connect(lrdata_dir / "previews.db") as connection:
        connection.execute(
            "CREATE TABLE ImageCacheEntry (imageId INTEGER, uuid TEXT, digest TEXT)"
        )
        connection.executemany(
            "INSERT INTO ImageCacheEntry VALUES (?, ?, ?)",
            [(int(photo["id_local"]), photo["uuid"], "digest") for photo in photos],
        )
    with sqlite3.connect(lrdata_dir / "root-pixels.db") as connection:
        connection.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        connection.executemany(
            "INSERT INTO RootPixels VALUES (?, ?)",
            [(photo["uuid"], _jpeg_bytes(index)) for index, photo in enumerate(photos, 1)],
        )


def test_prepare_builds_ordered_contact_sheet_package_and_removes_snapshots(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    photos = []
    for index in range(1, 18):
        raw_path = source_dir / f"frame-{index:02d}.NEF"
        raw_path.write_bytes(b"raw")
        photos.append({"id_local": str(index), "uuid": f"uuid-{index}", "path": str(raw_path)})
    lrdata_dir = tmp_path / "Previews.lrdata"
    _write_cache(lrdata_dir, photos)
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        json.dumps({"source_folder": str(source_dir), "photos": photos}), encoding="utf-8"
    )

    prepared = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-contact-sheets",
    )

    pass_dir = Path(prepared["pass_dir"])
    index = json.loads((pass_dir / "contact-sheet-index.json").read_text(encoding="utf-8"))
    assert [sheet["image_ids"] for sheet in index["sheets"]] == [
        [str(item) for item in range(1, 17)],
        ["17"],
    ]
    assert [sheet["preview_paths"] for sheet in index["sheets"]] == [
        [f"previews/{item:06d}__frame-{item:02d}.jpg" for item in range(1, 17)],
        ["previews/000017__frame-17.jpg"],
    ]
    assert all((pass_dir / sheet["sheet_path"]).is_file() for sheet in index["sheets"])
    assert not (pass_dir / "cache_snapshots").exists()
    task = (pass_dir / "AI_TASK.md").read_text(encoding="utf-8")
    assert "contact sheets first" in task.lower()
    assert "must not judge blur, focus, sharpness" in task.lower()


def test_analyze_rejects_a_tampered_contact_sheet(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    raw_path = source_dir / "frame.NEF"
    raw_path.write_bytes(b"raw")
    photo = {"id_local": "1", "uuid": "uuid-1", "path": str(raw_path)}
    lrdata_dir = tmp_path / "Previews.lrdata"
    _write_cache(lrdata_dir, [photo])
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps({"source_folder": str(source_dir), "photos": [photo]}), encoding="utf-8")
    prepared = prepare_session_pass(runtime_dir, lrdata_dir, selection_path, session_id="sess-tampered")
    pass_dir = Path(prepared["pass_dir"])
    index = json.loads((pass_dir / "contact-sheet-index.json").read_text(encoding="utf-8"))
    (pass_dir / index["sheets"][0]["sheet_path"]).write_bytes(b"tampered")
    decision = SinglePassDecision(
        image_id="1",
        action=Action.PASS,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=1.0,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="exposure",
        scene_rationale="exposure",
        scene_group_id="group",
        is_reference=False,
        reason="pass",
    )
    (pass_dir / "decisions" / "1.json").write_text(decision.model_dump_json(), encoding="utf-8")

    from lr_ai_exposure.session_lifecycle import analyze_session_pass

    with pytest.raises(SessionError, match="Contact-sheet package validation failed"):
        analyze_session_pass(runtime_dir, "sess-tampered", 1, {"ai_model": "test"})
