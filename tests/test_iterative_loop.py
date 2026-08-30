from lr_ai_exposure.ai_judge import Verdict
import pytest
from pathlib import Path
from typing import Any
import uuid

from lr_ai_exposure.session import SessionState, SessionImageState, create_session
from lr_ai_exposure.ai_judge import SinglePassDecision, Action
from lr_ai_exposure.convergence import evaluate_pass_convergence
from lr_ai_exposure.render_barrier import validate_render_barrier
from lr_ai_exposure.job import Manifest, ManifestEntry

def test_iterative_loop_end_to_end(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_123"
    session_id = "sess-123"
    
    # 1. Create Session
    selection = [
        {"id_local": "100", "uuid": str(uuid.uuid4()), "path": "D:/Photos/1.CR2", "xmp_path": "D:/Photos/1.xmp"},
        {"id_local": "101", "uuid": str(uuid.uuid4()), "path": "D:/Photos/2.CR2", "xmp_path": "D:/Photos/2.xmp"},
    ]
    state = create_session(session_dir, session_id, "D:/Photos", selection)
    
    # 2. Pass 1
    state.passes.append("pass-01")
    decisions = [
        SinglePassDecision(image_id="100", action=Action.PASS, scene_group_id="G1", is_reference=True, delta_ev=0.0, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP, confidence=0.9, highlight_risk=False, shadow_risk=False, subject_rationale="ok", scene_rationale="ok", reason="ok"),
        SinglePassDecision(image_id="101", action=Action.ADJUST, scene_group_id="G1", is_reference=False, delta_ev=0.5, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP, confidence=0.9, highlight_risk=False, shadow_risk=False, subject_rationale="ok", scene_rationale="ok", reason="ok"),
    ]
    
    results = evaluate_pass_convergence(state, decisions, "pass-01")
    assert results["applied"] == 1
    assert results["pass"] == 1
    assert state.images["100"].status == "PASS"
    assert state.images["101"].status == "ADJUST"
    assert state.images["101"].cumulative_delta_ev == 0.5
    assert not state.is_converged
    
    # 3. Render Barrier (simulate fresh preview)
    manifest = Manifest(
        job_id="sess-123", pass_number=2, pass_id="pass-02", parent_pass_id="pass-01",
        entries=[
            ManifestEntry(image_id="100", raw_path="", source_xmp_path="", backup_relative_path="", preview_path="", seq=1, preview_sha256="hash1"),
            ManifestEntry(image_id="101", raw_path="", source_xmp_path="", backup_relative_path="", preview_path="", seq=2, preview_sha256="hash2_new"),
        ]
    )
    # Set the previous hash for 101 to something different
    state.images["101"].last_preview_sha256 = "hash2_old"
    
    freshness = validate_render_barrier(state, manifest)
    assert freshness["101"] == "FRESH"
    assert state.images["101"].status == "ADJUST"
    
    # 4. Pass 2 (Oscillation simulation)
    state.passes.append("pass-02")
    decisions2 = [
        SinglePassDecision(image_id="101", action=Action.ADJUST, scene_group_id="G1", is_reference=False, delta_ev=-0.6, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP, confidence=0.9, highlight_risk=False, shadow_risk=False, subject_rationale="ok", scene_rationale="ok", reason="ok"), # Reverse sign!
    ]
    results2 = evaluate_pass_convergence(state, decisions2, "pass-02")
    assert state.images["101"].oscillations == 1
    
    # 5. Render Barrier (simulate another fresh preview)
    manifest3 = Manifest(
        job_id="sess-123", pass_number=3, pass_id="pass-03", parent_pass_id="pass-02",
        entries=[
            ManifestEntry(image_id="101", raw_path="", source_xmp_path="", backup_relative_path="", preview_path="", seq=2, preview_sha256="hash3_new"),
        ]
    )
    state.images["101"].last_preview_sha256 = "hash2_new"
    validate_render_barrier(state, manifest3)
    
    # 6. Pass 3 (Oscillation continues -> REVIEW)
    state.passes.append("pass-03")
    decisions3 = [
        SinglePassDecision(image_id="101", action=Action.ADJUST, scene_group_id="G1", is_reference=False, delta_ev=0.4, relevance_verdict=Verdict.KEEP, quality_verdict=Verdict.KEEP, confidence=0.9, highlight_risk=False, shadow_risk=False, subject_rationale="ok", scene_rationale="ok", reason="ok"), # Reverse sign again!
    ]
    results3 = evaluate_pass_convergence(state, decisions3, "pass-03")
    assert state.images["101"].oscillations == 2
    assert state.images["101"].status == "REVIEW"  # Should be REVIEW due to oscillation
    assert state.is_converged
