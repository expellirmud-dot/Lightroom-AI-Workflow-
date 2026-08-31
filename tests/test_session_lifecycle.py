from __future__ import annotations

import json
import io
import sqlite3
from pathlib import Path

from PIL import Image

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.session import load_session
from lr_ai_exposure.session_lifecycle import (
    prepare_session_pass,
    analyze_session_pass,
    apply_session_pass,
    confirm_session_apply,
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


def _jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 213), color).save(output, format="JPEG", quality=85)
    return output.getvalue()


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
    default_jpeg = _jpeg_bytes((64, 128, 192))
    for _, uuid_val, custom_jpeg in items:
        cur_r.execute(
            "INSERT OR REPLACE INTO RootPixels (uuid, jpegData) VALUES (?, ?)",
            (uuid_val, custom_jpeg if custom_jpeg is not None else default_jpeg),
        )
    conn_r.commit()
    conn_r.close()


def _decision(image_id: str, action: Action, delta: float, reference: bool = False) -> SinglePassDecision:
    return SinglePassDecision(
        image_id=image_id,
        action=action,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=delta,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="grounded",
        scene_rationale="grounded",
        scene_group_id="group-A",
        is_reference=reference,
        reason="test",
    )


def test_session_lifecycle_catalog_apply_and_frozen_decisions(tmp_path: Path) -> None:
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
    _write_dummy_xmp(xmp1, -1.0)
    _write_dummy_xmp(xmp2, -1.0)

    uuid1 = "uuid-1111"
    uuid2 = "uuid-2222"
    jpeg_initial_1 = _jpeg_bytes((16, 32, 64))
    jpeg_initial_2 = _jpeg_bytes((32, 64, 128))
    _make_dummy_preview_db(lrdata_dir, [(1, uuid1, jpeg_initial_1), (2, uuid2, jpeg_initial_2)])

    selection = {
        "protocol_version": "1.1",
        "session_id": "sess-test-01",
        "source_folder": str(source_dir),
        "photos": [
            {"id_local": "1", "uuid": uuid1, "path": str(raw_path1), "catalog_exposure2012": 0.25},
            {"id_local": "2", "uuid": uuid2, "path": str(raw_path2), "catalog_exposure2012": 0.70},
        ],
    }
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")

    pass1_info = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-test-01",
        pass_number=1,
    )
    pass1_dir = Path(pass1_info["pass_dir"])
    decisions_dir = pass1_dir / "decisions"
    (decisions_dir / "1.json").write_text(_decision("1", Action.PASS, 0.0, True).model_dump_json(indent=2), encoding="utf-8")
    (decisions_dir / "2.json").write_text(_decision("2", Action.ADJUST, 0.126).model_dump_json(indent=2), encoding="utf-8")

    settings = {
        "dry_run": False,
        "ai_provider": "manual_app",
        "ai_model": "manual-test",
        "minimum_apply_confidence": 0.8,
        "maximum_delta_ev": 1.0,
    }
    analyzed = analyze_session_pass(runtime_dir, "sess-test-01", 1, settings)
    assert analyzed["decision_count"] == 2
    frozen_before = Path(analyzed["ai_decisions"]).read_text(encoding="utf-8")

    # Mutate the raw manual response after Analyze. Planning must still consume
    # the frozen ai-decisions.json rather than invoke/read the provider again.
    (decisions_dir / "2.json").write_text(_decision("2", Action.ADJUST, -0.9).model_dump_json(indent=2), encoding="utf-8")

    plan_info = apply_session_pass(
        runtime_directory=runtime_dir,
        session_id="sess-test-01",
        pass_number=1,
        authorize_apply="sess-test-01",
        settings=settings,
    )
    assert plan_info["planned_count"] == 1
    assert Path(analyzed["ai_decisions"]).read_text(encoding="utf-8") == frozen_before

    plan = json.loads(Path(plan_info["catalog_apply_plan"]).read_text(encoding="utf-8"))
    item = plan["items"][0]
    assert item["image_id"] == "2"
    assert item["expected_before_exposure2012"] == 0.70
    assert item["delta_ev"] == 0.15
    assert item["target_exposure2012"] == 0.85

    state_before_confirm = load_session(runtime_dir / "sessions" / "sess-test-01")
    assert state_before_confirm.images["2"].expected_exposure2012 == 0.70
    assert state_before_confirm.images["2"].history == []
    assert read_exposure_2012(xmp2) == -1.0

    apply_result = {
        "protocol_version": "1.1",
        "session_id": "sess-test-01",
        "pass_id": pass1_info["pass_id"],
        "pass_number": 1,
        "results": [
            {
                "image_id": "2",
                "status": "APPLIED_VERIFIED",
                "observed_before_exposure2012": 0.70,
                "observed_after_exposure2012": 0.85,
            }
        ],
    }
    result_path = tmp_path / "catalog-apply-result.json"
    result_path.write_text(json.dumps(apply_result), encoding="utf-8")
    confirmed = confirm_session_apply(runtime_dir, "sess-test-01", 1, result_path)
    assert confirmed["applied_count"] == 1
    assert confirmed["next_pass_number"] == 2

    state = load_session(runtime_dir / "sessions" / "sess-test-01")
    assert state.images["2"].expected_exposure2012 == 0.85
    assert state.images["2"].cumulative_delta_ev == 0.15
    assert len(state.images["2"].history) == 1
    assert read_exposure_2012(xmp2) == -1.0

    jpeg_rerender_2 = _jpeg_bytes((128, 64, 32))
    _make_dummy_preview_db(lrdata_dir, [(1, uuid1, jpeg_initial_1), (2, uuid2, jpeg_rerender_2)])
    selection["photos"][1]["catalog_exposure2012"] = 0.85
    selection_path.write_text(json.dumps(selection), encoding="utf-8")

    pass2_info = prepare_session_pass(
        runtime_directory=runtime_dir,
        lrdata_dir=lrdata_dir,
        selection_json_path=selection_path,
        session_id="sess-test-01",
        pass_number=2,
        parent_pass_id=pass1_info["pass_id"],
    )
    assert pass2_info["render_barrier"].get("2") == "FRESH"

    pass2_dir = Path(pass2_info["pass_dir"])
    (pass2_dir / "decisions" / "1.json").write_text(_decision("1", Action.PASS, 0.0, True).model_dump_json(indent=2), encoding="utf-8")
    (pass2_dir / "decisions" / "2.json").write_text(_decision("2", Action.PASS, 0.0).model_dump_json(indent=2), encoding="utf-8")
    analyze_session_pass(runtime_dir, "sess-test-01", 2, settings)
    plan2 = apply_session_pass(runtime_dir, "sess-test-01", 2, "sess-test-01", settings)
    assert plan2["planned_count"] == 0

    empty_result = {
        "protocol_version": "1.1",
        "session_id": "sess-test-01",
        "pass_id": pass2_info["pass_id"],
        "pass_number": 2,
        "results": [],
    }
    result2_path = tmp_path / "catalog-apply-result-2.json"
    result2_path.write_text(json.dumps(empty_result), encoding="utf-8")
    final = confirm_session_apply(runtime_dir, "sess-test-01", 2, result2_path)
    assert final["is_converged"] is True
    assert final["next_pass_number"] is None
    assert load_session(runtime_dir / "sessions" / "sess-test-01").images["2"].status == "PASS"
