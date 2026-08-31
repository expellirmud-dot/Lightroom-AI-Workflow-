from __future__ import annotations

import json
import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from lr_ai_exposure.main import main
from lr_ai_exposure.catalog_confirm import main as catalog_confirm_main
from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict


def _write_dummy_xmp(path: Path, exposure: float = 0.0) -> None:
    content = f"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:Exposure2012="{exposure:+.2f}"/>
 </rdf:RDF>
</x:xmpmeta>
"""
    path.write_text(content, encoding="utf-8")


def _jpeg_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 213), (64, 128, 192)).save(output, format="JPEG", quality=85)
    return output.getvalue()


def _make_dummy_preview_db(lrdata_dir: Path, uuid_val: str) -> None:
    lrdata_dir.mkdir(parents=True, exist_ok=True)
    db_path = lrdata_dir / "previews.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS ImageCacheEntry (id INTEGER PRIMARY KEY, imageId INTEGER, uuid TEXT UNIQUE, digest TEXT)"
    )
    cur.execute(
        "INSERT OR REPLACE INTO ImageCacheEntry (imageId, uuid, digest) VALUES (1, ?, 'digest_1')",
        (uuid_val,),
    )
    conn.commit()
    conn.close()

    root_db = lrdata_dir / "root-pixels.db"
    conn_r = sqlite3.connect(root_db)
    cur_r = conn_r.cursor()
    cur_r.execute("CREATE TABLE IF NOT EXISTS RootPixels (uuid TEXT PRIMARY KEY, jpegData BLOB)")
    default_jpeg = _jpeg_bytes()
    cur_r.execute(
        "INSERT OR REPLACE INTO RootPixels (uuid, jpegData) VALUES (?, ?)",
        (uuid_val, default_jpeg),
    )
    conn_r.commit()
    conn_r.close()


def test_session_cli_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_dir = tmp_path / "runtime"
    lrdata_dir = tmp_path / "catalog.lrdata"
    source_dir = tmp_path / "photos"
    source_dir.mkdir(parents=True, exist_ok=True)

    dummy_catalog = tmp_path / "catalog.lrcat"
    dummy_catalog.write_text("DUMMY_CATALOG", encoding="utf-8")
    dummy_exports = tmp_path / "exports"
    dummy_exports.mkdir(parents=True, exist_ok=True)

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = {
        "catalog_path": str(dummy_catalog),
        "export_root": str(dummy_exports),
        "runtime_directory": str(runtime_dir),
        "preview_cache_path": str(lrdata_dir),
        "dry_run": False,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_provider": "manual_app",
        "ai_model": "manual-agent",
        "minimum_apply_confidence": 0.8,
        "maximum_delta_ev": 1.0,
        "preview_size": 2560,
    }
    (config_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    raw1 = source_dir / "img1.NEF"
    raw1.write_bytes(b"RAW1")
    _write_dummy_xmp(source_dir / "img1.xmp", -0.5)
    uuid1 = "uuid-cli-1"
    _make_dummy_preview_db(lrdata_dir, uuid1)

    selection = {
        "protocol_version": "1.1",
        "session_id": "sess-cli-01",
        "source_folder": str(source_dir),
        "photos": [
            {
                "id_local": "1",
                "uuid": uuid1,
                "path": str(raw1),
                "catalog_exposure2012": 0.35,
            }
        ],
    }
    selection_file = tmp_path / "selection.json"
    selection_file.write_text(json.dumps(selection), encoding="utf-8")
    bridge_file = tmp_path / "bridge-result.json"
    monkeypatch.chdir(tmp_path)

    ret = main(
        [
            "--start-session",
            "--session-id",
            "sess-cli-01",
            "--selection",
            str(selection_file),
            "--lrdata",
            str(lrdata_dir),
            "--bridge-result",
            str(bridge_file),
        ]
    )
    assert ret == 0
    res = json.loads(bridge_file.read_text(encoding="utf-8"))
    assert res["status"] == "ok"
    assert res["pass_number"] == 1

    pass1_dir = Path(res["pass_dir"])
    dec = SinglePassDecision(
        image_id="1",
        action=Action.PASS,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.0,
        confidence=0.9,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="Good",
        scene_rationale="Good",
        scene_group_id="G1",
        is_reference=True,
        reason="Good",
    )
    (pass1_dir / "decisions" / "1.json").write_text(dec.model_dump_json(indent=2), encoding="utf-8")

    ret_analyze = main(
        [
            "--analyze-session-pass",
            "--session-id",
            "sess-cli-01",
            "--pass-number",
            "1",
            "--bridge-result",
            str(bridge_file),
        ]
    )
    assert ret_analyze == 0

    ret_plan = main(
        [
            "--apply-session-pass",
            "--session-id",
            "sess-cli-01",
            "--pass-number",
            "1",
            "--authorize-apply",
            "sess-cli-01",
            "--bridge-result",
            str(bridge_file),
        ]
    )
    assert ret_plan == 0
    plan_bridge = json.loads(bridge_file.read_text(encoding="utf-8"))
    assert plan_bridge["status"] == "ok"
    assert plan_bridge["applied"] == 0
    plan = json.loads(Path(plan_bridge["apply_evidence"]).read_text(encoding="utf-8"))
    assert plan["planned_count"] == 0

    result_file = tmp_path / "catalog-result.json"
    result_file.write_text(
        json.dumps(
            {
                "protocol_version": "1.1",
                "session_id": "sess-cli-01",
                "pass_id": plan["pass_id"],
                "pass_number": 1,
                "results": [],
            }
        ),
        encoding="utf-8",
    )
    ret_confirm = catalog_confirm_main(
        [
            "--session-id",
            "sess-cli-01",
            "--pass-number",
            "1",
            "--apply-result",
            str(result_file),
            "--bridge-result",
            str(bridge_file),
        ]
    )
    assert ret_confirm == 0
    confirmed = json.loads(bridge_file.read_text(encoding="utf-8"))
    assert confirmed["status"] == "ok"
    assert confirmed["is_converged"] is True
    assert confirmed["pass_count"] == 1

    ret_status = main(
        [
            "--session-status",
            "--session-id",
            "sess-cli-01",
            "--bridge-result",
            str(bridge_file),
        ]
    )
    assert ret_status == 0
    res_status = json.loads(bridge_file.read_text(encoding="utf-8"))
    assert res_status["status"] == "ok"
    assert res_status["is_converged"] is True
    assert res_status["pass_count"] == 1
