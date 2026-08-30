from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pytest

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.session import load_session
from lr_ai_exposure.session_lifecycle import (
    prepare_session_pass,
    analyze_session_pass,
    apply_session_pass,
)
from lr_ai_exposure.xmp import read_exposure_2012


def _write_dummy_xmp(path: Path, exposure: float = 0.0) -> None:
    content = f"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:Exposure2012="{exposure:+.2f}"/>
 </rdf:RDF>
</x:xmpmeta>
"""
    path.write_text(content, encoding="utf-8")


def _make_dummy_preview_db(lrdata_dir: Path, items: list[tuple[int, str, bytes | None]]) -> None:
    lrdata_dir.mkdir(parents=True, exist_ok=True)
    db_path = lrdata_dir / "previews.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS ImageCacheEntry (id INTEGER PRIMARY KEY, imageId INTEGER, uuid TEXT UNIQUE, digest TEXT)"
    )
    for img_id, uuid_val, _ in items:
        cur.execute(
            "INSERT OR REPLACE INTO ImageCacheEntry (imageId, uuid, digest) VALUES (?, ?, ?)",
            (img_id, uuid_val, f"digest_{img_id}"),
        )
    conn.commit()
    conn.close()

    root_db = lrdata_dir / "root-pixels.db"
    conn_r = sqlite3.connect(root_db)
    cur_r = conn_r.cursor()
    cur_r.execute("CREATE TABLE IF NOT EXISTS RootPixels (uuid TEXT PRIMARY KEY, jpegData BLOB)")
    default_jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 200 + b"\xFF\xD9"
    for _, uuid_val, custom_jpeg in items:
        data = custom_jpeg if custom_jpeg is not None else default_jpeg
        cur_r.execute(
            "INSERT OR REPLACE INTO RootPixels (uuid, jpegData) VALUES (?, ?)",
            (uuid_val, data),
        )
    conn_r.commit()
    conn_r.close()


def test_session_lifecycle_multi_pass_flow(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    lrdata_dir = tmp_path / "catalog.lrdata"
    source_dir = tmp_path / "photos"
    source_dir.mkdir(parents=True, exist_ok=True)

    raw_path1 = source_dir / "photo1.NEF"
    raw_path2 = source_dir / "photo2.NEF"
    raw_path1.write_bytes(b"RAW_DATA_1")
    raw_path2.write_bytes(b"RAW_DATA_2")

    xmp1 = source_dir / "photo1.xmp"
    xmp2 = source_dir / "photo2.xmp"
    _write_dummy_xmp(xmp1, 0.0)
    _write_dummy_xmp(xmp2, 0.0)

    uuid1 = "uuid-1111"
    uuid2 = "uuid-2222"
    jpeg_initial_1 = b"\xFF\xD8\xFF\xE0" + b"INITIAL_1" + b"\x00" * 200 + b"\xFF\xD9"
    jpeg_initial_2 = b"\xFF\xD8\xFF\xE0" + b"INITIAL_2" + b"\x00" * 200 + b"\xFF\xD9"
    _make_dummy_preview_db(lrdata_dir, [(1, uuid1, jpeg_initial_1), (2, uuid2, jpeg_initial_2)])

    selection = {
        "protocol_version": "1.0",
        "session_id": "sess-test-01",
        "source_folder": str(source_dir),
        "photos": [
            {"id_local": "1", "uuid": uuid1, "path": str(raw_path1)},
            {"id_local": "2", "uuid": uuid2, "path": str(raw_path2)},
        ],
    }
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")

    # 1. Pass 1 Preparation
    pass1_info = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-test-01",
        pass_number=1,
    )
    assert pass1_info["session_id"] == "sess-test-01"
    assert pass1_info["pass_number"] == 1
    assert pass1_info["total_found"] == 2
    assert Path(pass1_info["manifest_path"]).is_file()

    # Create decisions for Pass 1: photo 1 is reference (PASS), photo 2 is ADJUST (+0.50 EV)
    pass1_dir = Path(pass1_info["pass_dir"])
    decisions_dir = pass1_dir / "decisions"
    dec_1 = SinglePassDecision(
        image_id="1",
        action=Action.PASS,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="Well balanced",
        scene_rationale="Consistent",
        scene_group_id="group-A",
        is_reference=True,
        reason="Good reference",
    )
    dec_2 = SinglePassDecision(
        image_id="2",
        action=Action.ADJUST,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.50,
        confidence=0.90,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="Under exposed",
        scene_rationale="Needs +0.50 EV",
        scene_group_id="group-A",
        is_reference=False,
        reason="Adjust to match group-A",
    )
    (decisions_dir / "1.json").write_text(dec_1.model_dump_json(indent=2), encoding="utf-8")
    (decisions_dir / "2.json").write_text(dec_2.model_dump_json(indent=2), encoding="utf-8")

    settings = {
        "dry_run": False,
        "ai_provider": "manual_app",
        "minimum_apply_confidence": 0.8,
        "maximum_delta_ev": 1.0,
    }

    # 2. Pass 1 Apply
    apply_info = apply_session_pass(
        runtime_directory=runtime_dir,
        session_id="sess-test-01",
        pass_number=1,
        authorize_apply="sess-test-01",
        settings=settings,
    )
    assert apply_info["applied_count"] == 1
    assert "2" in apply_info["applied_image_ids"]
    assert not apply_info["is_converged"]
    assert apply_info["next_pass_number"] == 2

    # Verify XMP was updated for photo 2
    assert read_exposure_2012(xmp2) == 0.50
    assert read_exposure_2012(xmp1) == 0.0

    # 3. Simulate Lightroom Rerender (new preview jpeg in database)
    jpeg_rerender_2 = b"\xFF\xD8\xFF\xE0" + b"RERENDERED_2" + b"\x00" * 200 + b"\xFF\xD9"
    _make_dummy_preview_db(lrdata_dir, [(1, uuid1, jpeg_initial_1), (2, uuid2, jpeg_rerender_2)])

    # 4. Pass 2 Preparation (Checks render barrier freshness!)
    pass2_info = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-test-01",
        pass_number=2,
        parent_pass_id=pass1_info["pass_id"],
    )
    assert pass2_info["pass_number"] == 2
    assert pass2_info["render_barrier"].get("2") == "FRESH"

    # Pass 2 Decisions: photo 2 is now evaluated against reference and found PASS
    pass2_dir = Path(pass2_info["pass_dir"])
    pass2_dec_dir = pass2_dir / "decisions"
    dec_2_pass2 = SinglePassDecision(
        image_id="2",
        action=Action.PASS,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="Now balanced with reference",
        scene_rationale="Good exposure",
        scene_group_id="group-A",
        is_reference=False,
        reason="Converged to group-A",
    )
    (pass2_dec_dir / "2.json").write_text(dec_2_pass2.model_dump_json(indent=2), encoding="utf-8")

    dec_1_pass2 = SinglePassDecision(
        image_id="1",
        action=Action.PASS,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="Reference photo",
        scene_rationale="Reference photo",
        scene_group_id="group-A",
        is_reference=True,
        reason="Reference",
    )
    (pass2_dec_dir / "1.json").write_text(dec_1_pass2.model_dump_json(indent=2), encoding="utf-8")

    # 5. Pass 2 Apply (Convergence reached!)
    apply2_info = apply_session_pass(
        runtime_directory=runtime_dir,
        session_id="sess-test-01",
        pass_number=2,
        authorize_apply="sess-test-01",
        settings=settings,
    )
    assert apply2_info["applied_count"] == 0
    assert apply2_info["is_converged"] is True
    assert apply2_info["next_pass_number"] is None

    session_state = load_session(runtime_dir / "sessions" / "sess-test-01")
    assert session_state.is_converged is True
    assert session_state.images["2"].status == "PASS"
