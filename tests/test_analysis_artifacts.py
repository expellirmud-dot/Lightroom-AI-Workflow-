"""Tests for the canonical AnalysisRecord evidence contract (WO-023)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.analysis_artifacts import (
    AnalysisRecord,
    serialize_analysis_records,
    write_analysis_records,
)


def _decision(image_id: str = "img-1", delta: float = 0.5) -> SinglePassDecision:
    return SinglePassDecision(
        image_id=image_id,
        action=Action.ADJUST, relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=delta,
        confidence=0.9,
        highlight_risk=False,
        shadow_risk=True,
        subject_rationale="subject",
        scene_rationale="scene",
        scene_group_id="group-A",
        reason="ok",
    )


def _record(image_id: str = "img-1", seq: int = 1) -> AnalysisRecord:
    return AnalysisRecord(
        decision=_decision(image_id, 0.1 * seq),
        provider="manual_app",
        model="Gemini 3.1 Pro High",
        mode="ANALYZE_ONLY",
        preview_bytes=1024 + seq,
        preview_sha256=f"sha-{seq}" + "0" * 59,
        response_reference=f"responses/{image_id}.json",
        token_usage=None,
    )


def test_record_preserves_full_decision_schema():
    payload = _record().model_dump(mode="json")
    decision = payload["decision"]
    for field in (
        "image_id",
        "relevance_verdict",
        "quality_verdict",
        "delta_ev",
        "confidence",
        "highlight_risk",
        "shadow_risk",
        "subject_rationale",
        "scene_rationale",
        "scene_group_id",
        "reason",
    ):
        assert field in decision, f"decision field dropped: {field}"
    # Risk flag values survive serialization untouched.
    assert decision["shadow_risk"] is True
    assert decision["highlight_risk"] is False


def test_record_preserves_provider_metadata():
    payload = _record(seq=3).model_dump(mode="json")
    assert payload["provider"] == "manual_app"
    assert payload["model"] == "Gemini 3.1 Pro High"
    assert payload["mode"] == "ANALYZE_ONLY"
    assert payload["preview_bytes"] == 1027
    assert payload["preview_sha256"].startswith("sha-3")
    assert payload["response_reference"] == "responses/img-1.json"
    assert payload["token_usage"] is None


def test_record_carries_token_usage_when_available():
    record = AnalysisRecord(
        decision=_decision(),
        provider="google",
        model="gemini-2.5-pro",
        mode="ANALYZE_ONLY",
        preview_bytes=10,
        preview_sha256="a" * 64,
        response_reference="google",
        token_usage={
            "prompt_token_count": 100,
            "candidates_token_count": 50,
            "total_token_count": 150,
        },
    )
    payload = record.model_dump(mode="json")
    assert payload["token_usage"]["total_token_count"] == 150


def test_record_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AnalysisRecord(
            decision=_decision(),
            provider="manual_app",
            model="m",
            mode="ANALYZE_ONLY",
            preview_bytes=1,
            preview_sha256="x",
            response_reference="r",
            unexpected_field="nope",
        )


def test_record_rejects_negative_preview_bytes():
    with pytest.raises(ValidationError):
        AnalysisRecord(
            decision=_decision(),
            provider="manual_app",
            model="m",
            mode="ANALYZE_ONLY",
            preview_bytes=-1,
            preview_sha256="x",
            response_reference="r",
        )


def test_serialize_records_deterministic_and_ordered():
    records = [_record(f"img-{i}", i) for i in range(1, 6)]
    payload_a = serialize_analysis_records("job-x", records)
    payload_b = serialize_analysis_records("job-x", records)

    # Deterministic serialization: byte-identical JSON.
    assert json.dumps(payload_a, sort_keys=False) == json.dumps(
        payload_b, sort_keys=False
    )
    assert payload_a["record_count"] == 5
    ids = [r["decision"]["image_id"] for r in payload_a["records"]]
    assert ids == [f"img-{i}" for i in range(1, 6)]


def test_write_analysis_records_atomic(tmp_path: Path):
    records = [_record(f"img-{i}", i) for i in range(1, 6)]
    out = write_analysis_records(tmp_path, "job-x", records)

    assert out == tmp_path / "analysis-records.json"
    assert out.exists()
    assert not (tmp_path / "analysis-records.json.tmp").exists()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["job_id"] == "job-x"
    assert doc["record_count"] == 5
    assert len(doc["records"]) == 5
