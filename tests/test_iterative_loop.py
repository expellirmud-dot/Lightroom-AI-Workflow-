from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from lr_ai_exposure.ai_judge import Verdict, SinglePassDecision, Action
from lr_ai_exposure.session import create_session
from lr_ai_exposure.convergence import evaluate_pass_convergence
from lr_ai_exposure.render_barrier import validate_render_barrier
from lr_ai_exposure.job import Manifest, ManifestEntry


def test_iterative_loop_end_to_end(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_123"
    session_id = "sess-123"
    selection = [
        {
            "id_local": "100",
            "uuid": str(uuid.uuid4()),
            "path": "D:/Photos/1.CR2",
            "catalog_exposure2012": 0.25,
        },
        {
            "id_local": "101",
            "uuid": str(uuid.uuid4()),
            "path": "D:/Photos/2.CR2",
            "catalog_exposure2012": 0.70,
        },
    ]
    state = create_session(session_dir, session_id, "D:/Photos", selection)
    assert state.images["101"].baseline_exposure2012 == 0.70
    assert state.images["101"].expected_exposure2012 == 0.70

    state.passes.append("pass-01")
    decisions = [
        SinglePassDecision(
            image_id="100",
            action=Action.PASS,
            scene_group_id="G1",
            is_reference=True,
            delta_ev=0.0,
            relevance_verdict=Verdict.KEEP,
            quality_verdict=Verdict.KEEP,
            confidence=0.9,
            highlight_risk=False,
            shadow_risk=False,
            subject_rationale="ok",
            scene_rationale="ok",
            reason="ok",
        ),
        SinglePassDecision(
            image_id="101",
            action=Action.ADJUST,
            scene_group_id="G1",
            is_reference=False,
            delta_ev=0.123,
            relevance_verdict=Verdict.KEEP,
            quality_verdict=Verdict.KEEP,
            confidence=0.9,
            highlight_risk=False,
            shadow_risk=False,
            subject_rationale="ok",
            scene_rationale="ok",
            reason="ok",
        ),
    ]

    results = evaluate_pass_convergence(state, decisions, "pass-01")
    assert results["pass_number"] == 1
    assert results["quantized_deltas"]["101"] == 0.10
    assert state.images["101"].cumulative_delta_ev == 0.10
    assert state.images["101"].expected_exposure2012 == 0.80
    assert not state.is_converged

    manifest = Manifest(
        job_id="sess-123",
        pass_number=2,
        pass_id="pass-02",
        parent_pass_id="pass-01",
        entries=[
            ManifestEntry(
                image_id="100",
                raw_path="",
                source_xmp_path="",
                backup_relative_path="",
                preview_path="",
                seq=1,
                preview_bytes=2048,
                preview_sha256="hash1",
            ),
            ManifestEntry(
                image_id="101",
                raw_path="",
                source_xmp_path="",
                backup_relative_path="",
                preview_path="",
                seq=2,
                preview_bytes=2048,
                preview_sha256="hash2_new",
            ),
        ],
    )
    state.images["101"].last_preview_sha256 = "hash2_old"
    freshness = validate_render_barrier(state, manifest, {"101": 0.80})
    assert freshness["101"] == "FRESH"

    mismatch_state = create_session(
        tmp_path / "mismatch",
        "sess-mismatch",
        "D:/Photos",
        [
            {
                "id_local": "1",
                "uuid": str(uuid.uuid4()),
                "path": "D:/Photos/m.CR2",
                "catalog_exposure2012": 0.0,
            }
        ],
    )
    mismatch_state.images["1"].status = "ADJUST"
    mismatch_state.images["1"].expected_exposure2012 = 1.0
    mismatch_state.images["1"].last_preview_sha256 = "old"
    mismatch_manifest = Manifest(
        job_id="sess-mismatch",
        entries=[
            ManifestEntry(
                image_id="1",
                raw_path="",
                source_xmp_path="",
                backup_relative_path="",
                preview_path="",
                seq=1,
                preview_bytes=100,
                preview_sha256="new",
            )
        ],
    )
    mismatch = validate_render_barrier(mismatch_state, mismatch_manifest, {"1": 0.5})
    assert mismatch["1"].startswith("REVIEW_RENDER_UNPROVEN_CATALOG_MISMATCH")
    assert mismatch_state.images["1"].status == "REVIEW"
