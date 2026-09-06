from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from lr_ai_exposure.ai_judge import (
    Action,
    SceneExposureVerdict,
    SinglePassDecision,
    SinglePassError,
    Verdict,
    validate_scene_decision_set,
    validate_single_pass_decision,
)
from lr_ai_exposure.convergence import evaluate_pass_convergence
from lr_ai_exposure.session import SessionError, create_session, load_session
from lr_ai_exposure.session_lifecycle import (
    analyze_session_pass,
    apply_session_pass,
    confirm_session_apply,
    prepare_session_pass,
)
from lr_ai_exposure.job import read_manifest


def _jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (320, 213), color).save(out, format="JPEG", quality=85)
    return out.getvalue()


def _write_preview_db(lrdata: Path, rows: list[tuple[int, str, bytes]]) -> None:
    lrdata.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(lrdata / "previews.db") as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS ImageCacheEntry "
            "(id INTEGER PRIMARY KEY, imageId INTEGER, uuid TEXT UNIQUE, digest TEXT, orientation TEXT)"
        )
        db.execute("DELETE FROM ImageCacheEntry")
        for image_id, uuid, _ in rows:
            db.execute(
                "INSERT INTO ImageCacheEntry (imageId, uuid, digest, orientation) VALUES (?, ?, ?, 'AB')",
                (image_id, uuid, f"digest-{image_id}"),
            )
    with sqlite3.connect(lrdata / "root-pixels.db") as db:
        db.execute("CREATE TABLE IF NOT EXISTS RootPixels (uuid TEXT PRIMARY KEY, jpegData BLOB)")
        db.execute("DELETE FROM RootPixels")
        for _, uuid, jpeg in rows:
            db.execute("INSERT INTO RootPixels (uuid, jpegData) VALUES (?, ?)", (uuid, jpeg))


def _decision(
    image_id: str,
    action: Action,
    delta: float,
    *,
    scene: str = "scene-A",
    scene_verdict: SceneExposureVerdict = SceneExposureVerdict.BALANCED,
    scene_delta: float = 0.0,
    reference: bool = False,
) -> SinglePassDecision:
    return SinglePassDecision(
        image_id=image_id,
        action=action,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=delta,
        confidence=0.95,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="evaluated subject exposure",
        scene_rationale="evaluated whole-scene exposure",
        scene_group_id=scene,
        scene_exposure_verdict=scene_verdict,
        scene_delta_ev=scene_delta,
        is_reference=reference,
        reason="evaluated",
    )


def _raw(decision: SinglePassDecision) -> dict:
    return json.loads(decision.model_dump_json())


def test_coverage_does_not_require_adjustment_and_scene_outcomes_are_consistent() -> None:
    passed = validate_single_pass_decision(_raw(_decision("1", Action.PASS, 0.0)))
    assert passed.action == Action.PASS
    assert passed.delta_ev == 0.0

    bad_pass = _raw(_decision("1", Action.PASS, 0.0))
    bad_pass["delta_ev"] = 0.2
    with pytest.raises(SinglePassError, match="PASS requires delta_ev=0"):
        validate_single_pass_decision(bad_pass)

    bad_adjust = _raw(_decision("1", Action.ADJUST, 0.2))
    bad_adjust["delta_ev"] = 0.0
    with pytest.raises(SinglePassError, match="ADJUST requires a non-zero"):
        validate_single_pass_decision(bad_adjust)

    decisions = [
        _decision(
            "1", Action.PASS, 0.0,
            scene_verdict=SceneExposureVerdict.TOO_BRIGHT,
            scene_delta=-0.6,
        ),
        _decision(
            "2", Action.ADJUST, -0.45,
            scene_verdict=SceneExposureVerdict.TOO_BRIGHT,
            scene_delta=-0.6,
        ),
    ]
    validate_scene_decision_set(decisions, require_explicit_scene_fields=True)

    contradictory = [
        decisions[0],
        _decision(
            "2", Action.ADJUST, 0.4,
            scene_verdict=SceneExposureVerdict.TOO_DARK,
            scene_delta=0.6,
        ),
    ]
    with pytest.raises(SinglePassError, match="Contradictory scene_exposure_verdict"):
        validate_scene_decision_set(contradictory, require_explicit_scene_fields=True)


def test_review_is_re_evaluable_and_only_all_pass_converges(tmp_path: Path) -> None:
    state = create_session(
        tmp_path / "session",
        "sess-review",
        str(tmp_path),
        [
            {"id_local": "1", "uuid": "u1", "path": str(tmp_path / "1.NEF"), "catalog_exposure2012": 0.0},
            {"id_local": "2", "uuid": "u2", "path": str(tmp_path / "2.NEF"), "catalog_exposure2012": 0.0},
        ],
    )
    state.passes.append("pass-1")
    first = evaluate_pass_convergence(
        state,
        [_decision("1", Action.PASS, 0.0), _decision("2", Action.REVIEW, 0.0)],
        "pass-1",
    )
    assert first["is_converged"] is False
    assert state.images["2"].status == "REVIEW"

    state.passes.append("pass-2")
    second = evaluate_pass_convergence(
        state,
        [_decision("1", Action.PASS, 0.0), _decision("2", Action.PASS, 0.0)],
        "pass-2",
    )
    assert second["is_converged"] is True
    assert state.images["2"].status == "PASS"


def _make_three_photo_fixture(tmp_path: Path):
    runtime = tmp_path / "runtime"
    lrdata = tmp_path / "catalog Previews.lrdata"
    photos = tmp_path / "photos"
    photos.mkdir()
    rows = []
    selection_photos = []
    for idx, color in enumerate([(40, 40, 40), (90, 90, 90), (150, 150, 150)], start=1):
        raw = photos / f"p{idx}.NEF"
        raw.write_bytes(f"RAW{idx}".encode())
        uuid = f"uuid-{idx}"
        rows.append((idx, uuid, _jpeg_bytes(color)))
        selection_photos.append(
            {"id_local": str(idx), "uuid": uuid, "path": str(raw), "catalog_exposure2012": 0.0}
        )
    _write_preview_db(lrdata, rows)
    selection = {
        "protocol_version": "1.1",
        "session_id": "sess-complete",
        "source_folder": str(photos),
        "photos": selection_photos,
    }
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    settings = {
        "dry_run": False,
        "ai_provider": "manual_app",
        "ai_model": "test-agent",
        "minimum_apply_confidence": 0.8,
        "maximum_delta_ev": 1.0,
    }
    return runtime, lrdata, selection, selection_path, settings, rows


def test_later_pass_reaudits_complete_set_and_stale_render_waits_without_review(tmp_path: Path) -> None:
    runtime, lrdata, selection, selection_path, settings, rows = _make_three_photo_fixture(tmp_path)
    p1 = prepare_session_pass(runtime, lrdata, selection_path, session_id="sess-complete", pass_number=1)
    p1dir = Path(p1["pass_dir"])
    schema = json.loads((p1dir / "decision-schema.json").read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert {"scene_group_id", "scene_exposure_verdict", "scene_delta_ev", "is_reference"} <= required
    decisions = [
        _decision("1", Action.PASS, 0.0, reference=False, scene_verdict=SceneExposureVerdict.TOO_BRIGHT, scene_delta=-0.4),
        _decision(
            "2", Action.ADJUST, -0.4,
            scene_verdict=SceneExposureVerdict.TOO_BRIGHT,
            scene_delta=-0.4,
        ),
        _decision("3", Action.REVIEW, 0.0, scene_verdict=SceneExposureVerdict.REVIEW, scene_delta=0.0, scene="scene-B"),
    ]
    for d in decisions:
        (p1dir / "decisions" / f"{d.image_id}.json").write_text(d.model_dump_json(indent=2), encoding="utf-8")
    analyze_session_pass(runtime, "sess-complete", 1, settings)
    plan = apply_session_pass(runtime, "sess-complete", 1, "sess-complete", settings)
    assert plan["planned_count"] == 1
    assert plan["requires_rerender"] is True

    apply_result = {
        "protocol_version": "1.1",
        "session_id": "sess-complete",
        "pass_id": p1["pass_id"],
        "pass_number": 1,
        "results": [
            {
                "image_id": "2",
                "status": "APPLIED_VERIFIED",
                "observed_before_exposure2012": 0.0,
                "observed_after_exposure2012": -0.4,
            }
        ],
    }
    result_path = tmp_path / "apply-result.json"
    result_path.write_text(json.dumps(apply_result), encoding="utf-8")
    confirmed = confirm_session_apply(runtime, "sess-complete", 1, result_path)
    assert confirmed["is_converged"] is False
    assert confirmed["requires_rerender"] is True

    # Catalog target is current, but preview bytes are intentionally unchanged.
    selection["photos"][1]["catalog_exposure2012"] = -0.4
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    with pytest.raises(SessionError, match="WAITING_FOR_RERENDER"):
        prepare_session_pass(
            runtime, lrdata, selection_path,
            session_id="sess-complete", pass_number=2, parent_pass_id=p1["pass_id"],
        )
    state_after_wait = load_session(runtime / "sessions" / "sess-complete")
    assert state_after_wait.images["2"].status == "ADJUST"
    assert state_after_wait.images["3"].status == "REVIEW"
    assert len(state_after_wait.passes) == 1

    # Lightroom rerender becomes fresh for the one adjusted image.
    rerendered = list(rows)
    rerendered[1] = (2, "uuid-2", _jpeg_bytes((30, 30, 30)))
    _write_preview_db(lrdata, rerendered)
    p2 = prepare_session_pass(
        runtime, lrdata, selection_path,
        session_id="sess-complete", pass_number=2, parent_pass_id=p1["pass_id"],
    )
    assert p2["total_selected"] == 3
    manifest = read_manifest(Path(p2["pass_dir"]))
    assert [entry.image_id for entry in manifest.entries] == ["1", "2", "3"]
    assert p2["render_barrier"]["2"] == "FRESH"
    assert p2["render_barrier"]["1"] == "SKIPPED_NOT_ADJUSTED"
    assert p2["render_barrier"]["3"] == "SKIPPED_NOT_ADJUSTED"


def test_scope_change_requires_new_session(tmp_path: Path) -> None:
    runtime, lrdata, selection, selection_path, _settings, _rows = _make_three_photo_fixture(tmp_path)
    p1 = prepare_session_pass(runtime, lrdata, selection_path, session_id="sess-complete", pass_number=1)
    extra = tmp_path / "photos" / "p4.NEF"
    extra.write_bytes(b"RAW4")
    selection["photos"].append(
        {"id_local": "4", "uuid": "uuid-4", "path": str(extra), "catalog_exposure2012": 0.0}
    )
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    with pytest.raises(SessionError, match="SESSION_SCOPE_CHANGED"):
        prepare_session_pass(
            runtime, lrdata, selection_path,
            session_id="sess-complete", pass_number=2, parent_pass_id=p1["pass_id"],
        )


def test_no_adjust_with_review_needs_recheck_not_rerender(tmp_path: Path) -> None:
    runtime, lrdata, _selection, selection_path, settings, _rows = _make_three_photo_fixture(tmp_path)
    p1 = prepare_session_pass(runtime, lrdata, selection_path, session_id="sess-complete", pass_number=1)
    p1dir = Path(p1["pass_dir"])
    for d in [
        _decision("1", Action.PASS, 0.0),
        _decision("2", Action.PASS, 0.0),
        _decision("3", Action.REVIEW, 0.0, scene="scene-B", scene_verdict=SceneExposureVerdict.REVIEW),
    ]:
        (p1dir / "decisions" / f"{d.image_id}.json").write_text(d.model_dump_json(indent=2), encoding="utf-8")
    analyze_session_pass(runtime, "sess-complete", 1, settings)
    planned = apply_session_pass(runtime, "sess-complete", 1, "sess-complete", settings)
    assert planned["planned_count"] == 0
    assert planned["requires_rerender"] is False

    empty = tmp_path / "empty-result.json"
    empty.write_text(
        json.dumps(
            {
                "protocol_version": "1.1",
                "session_id": "sess-complete",
                "pass_id": p1["pass_id"],
                "pass_number": 1,
                "results": [],
            }
        ),
        encoding="utf-8",
    )
    confirmed = confirm_session_apply(runtime, "sess-complete", 1, empty)
    assert confirmed["is_converged"] is False
    assert confirmed["requires_rerender"] is False
    assert confirmed["review_count"] == 1
    assert confirmed["next_pass_number"] == 2
