"""RCV002: test production planner behavior with a numeric calibration guard.

Monkeypatch only the in-process test function; no production source edits.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

import lr_ai_exposure.production_job as production
from lr_ai_exposure.hybrid_exposure import (
    RendererResponseUncertain,
    estimate_renderer_calibrated_delta_ev as original_estimator,
)
from renderer_calibration_support import CalibrationOutOfSupport, estimate_if_supported
from test_reference_free_target_planning import _manifest, _selection, _policy


@pytest.mark.parametrize(
    ("baseline", "target", "expected"),
    [(0.30, 0.38, "UNRESOLVED"), (0.60, 0.65, "WILL_ADJUST"), (0.95, 0.85, "UNRESOLVED")],
)
def test_real_planner_guarded_injection(tmp_path, monkeypatch, baseline, target, expected):
    job = tmp_path / "job-rf"
    job.mkdir()
    manifest = _manifest(job, ("1",))
    _selection(job, ("1",))
    production.create_production_job_state(
        job, job_id="job-rf", source_folder="D:/album",
        ordered_image_ids=("1",), policy=_policy(),
    )
    production.build_reference_free_target_package(job, manifest)
    semantics = {
        "protocol_version": "2.0",
        "job_id": "job-rf",
        "groups": [{
            "group_id": "g-1", "status": "TARGETS_SELECTED",
            "reference_image_id": None,
            "members": [{"image_id": "1", "verdict": "AUTO", "target_candidate_id": "c05"}],
        }],
        "unassigned": [],
    }
    sem_path = tmp_path / "semantics.json"
    sem_path.write_text(json.dumps(semantics), encoding="utf-8")
    production.import_visual_semantics(job, sem_path)
    monkeypatch.setattr(production, "_reference_free_target_measurement",
                        lambda directory, image_id, candidate_id: target)

    def checked_estimator(**kwargs):
        try:
            return estimate_if_supported(original_estimator, **kwargs)
        except CalibrationOutOfSupport as exc:
            raise RendererResponseUncertain(str(exc)) from exc

    monkeypatch.setattr(production, "estimate_renderer_calibrated_delta_ev", checked_estimator)
    measurements = [{
        "image_id": "1", "status": "MEASURED", "measurement": baseline,
        "preview_sha256": manifest.entries[0].preview_sha256,
    }]
    plan = production.build_production_plan(job, measurements)
    item = plan["items"][0]
    assert item["pre_apply_status"] == expected
    if expected == "UNRESOLVED":
        assert item["reason_code"] == "RENDER_RESPONSE_UNCERTAIN"
        assert item["validated_delta_ev"] is None
        assert plan["catalog_plan"]["planned_count"] == 0
    else:
        assert item["validated_delta_ev"] > 0
        assert plan["catalog_plan"]["planned_count"] == 1
