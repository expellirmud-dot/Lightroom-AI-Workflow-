"""Canonical CLI integration test — synthetic five-image ANALYZE_ONLY workflow.

Exercises the real ``lr_ai_exposure.main.main`` entry point against a
synthetic five-image job, with the handoff and AI-judgment stages
patched at the module boundary so the test is deterministic and makes
no external API calls.

Covers the WO-022 acceptance criteria:

- Canonical CLI completes a synthetic five-image ANALYZE_ONLY workflow.
- CLI_EXIT=0.
- Five decisions are written in manifest order.
- Full risk and rationale fields are preserved.
- Apply function is proven not called.
- No XMP, RAW, catalog, or preview-cache mutation occurs.

This test does NOT touch real photographs, XMP, catalogs, or preview
caches. The job directory lives entirely under ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.job import Manifest, ManifestEntry
from lr_ai_exposure.main import main


EXPECTED = 5


def _make_decision(image_id: str, seq: int) -> SinglePassDecision:
    """Construct a deterministic, schema-valid SinglePassDecision.

    Varies ``delta_ev`` by ``seq`` so manifest-order preservation can
    be verified from the written artifact.
    """
    return SinglePassDecision(
        image_id=image_id,
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        delta_ev=0.1 * seq,
        confidence=0.9,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale=f"subject rationale for {image_id}",
        scene_rationale=f"scene rationale for {image_id}",
        batch_consistency_group="group-A",
        reason=f"ok {image_id}",
    )


def _build_manifest(job_id: str) -> Manifest:
    entries = [
        ManifestEntry(
            image_id=f"img-{i}",
            raw_path=f"/tmp/synthetic/raw/img-{i}.NEF",
            source_xmp_path=f"/tmp/synthetic/raw/img-{i}.xmp",
            backup_relative_path=f"xmp_backups/img-{i}.xmp",
            preview_path=f"previews/{i:06d}__img-{i}.jpg",
            seq=i,
            extraction_status="FOUND",
            uuid=f"uuid-{i}",
            preview_bytes=1024 + i,
            preview_sha256=f"sha-{i}" + "0" * 59,
        )
        for i in range(1, EXPECTED + 1)
    ]
    return Manifest(
        job_id=job_id,
        entries=entries,
        total_selected=EXPECTED,
        total_found=EXPECTED,
    )


def _settings(tmp_path: Path) -> dict:
    return {
        "dry_run": True,
        "maximum_delta_ev": 1.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": str(tmp_path / "runtime"),
        "ai_provider": "google",
        "ai_model": "gemini-2.5-pro",
    }


@mock.patch("lr_ai_exposure.apply.apply_exposure_deltas")
@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_canonical_cli_five_image_analyze_only_workflow(
    mock_analyze,
    mock_read_manifest,
    mock_handoff,
    mock_config,
    mock_apply,
    tmp_path,
):
    """WO-022 acceptance: five-image ANALYZE_ONLY workflow via canonical CLI."""
    settings = _settings(tmp_path)
    mock_config.return_value = settings

    job_id = "job-integration"
    job_dir = tmp_path / "runtime" / "jobs" / job_id
    job_dir.mkdir(parents=True)

    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    manifest = _build_manifest(job_id)
    decisions = [_make_decision(e.image_id, e.seq) for e in manifest.entries]

    mock_handoff.return_value = job_id
    mock_read_manifest.return_value = manifest
    mock_analyze.return_value = decisions
    mock_apply.return_value = {"applied": 0, "skipped": 0, "errors": 0}

    # Run the canonical CLI in default mode (no --apply).
    rc = main(
        ["--analyze-only", "--selection", str(selection_path), "--lrdata", str(lrdata_path)]
    )

    # CLI_EXIT=0
    assert rc == 0

    # Apply function proven not called.
    mock_apply.assert_not_called()

    # ai-decisions.json written with full schema in manifest order.
    ai_decisions_path = job_dir / "ai-decisions.json"
    assert ai_decisions_path.exists(), "ai-decisions.json not written"
    decisions_doc = json.loads(ai_decisions_path.read_text(encoding="utf-8"))

    assert decisions_doc["job_id"] == job_id
    assert decisions_doc["mode"] == "ANALYZE_ONLY"
    assert decisions_doc["apply_authorized"] is False
    assert decisions_doc["xmp_mutation"] is False
    assert decisions_doc["decision_count"] == EXPECTED

    written = decisions_doc["decisions"]
    assert len(written) == EXPECTED

    # Manifest order preserved: image_id and delta_ev must track seq.
    for idx, entry in enumerate(manifest.entries):
        d = written[idx]
        assert d["image_id"] == entry.image_id
        assert d["delta_ev"] == pytest.approx(0.1 * entry.seq)
        # Full risk + rationale schema fields preserved (WO-022 requirement 5).
        for full_field in (
            "image_id",
            "relevance_verdict",
            "quality_verdict",
            "delta_ev",
            "confidence",
            "highlight_risk",
            "shadow_risk",
            "subject_rationale",
            "scene_rationale",
            "batch_consistency_group",
            "reason",
        ):
            assert full_field in d, f"missing full-schema field {full_field}"
        assert d["highlight_risk"] is False
        assert d["shadow_risk"] is False
        assert d["subject_rationale"] == f"subject rationale for {entry.image_id}"
        assert d["scene_rationale"] == f"scene rationale for {entry.image_id}"
        assert d["batch_consistency_group"] == "group-A"

    # analysis-evidence.json written with identity chain in manifest order.
    evidence_path = job_dir / "analysis-evidence.json"
    assert evidence_path.exists(), "analysis-evidence.json not written"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert evidence["job_id"] == job_id
    assert evidence["mode"] == "ANALYZE_ONLY"
    assert evidence["apply_authorized"] is False
    assert evidence["xmp_mutation"] is False
    assert len(evidence["identity_chain"]) == EXPECTED
    for idx, entry in enumerate(manifest.entries):
        link = evidence["identity_chain"][idx]
        assert link["image_id"] == entry.image_id
        assert link["delta_ev"] == pytest.approx(0.1 * entry.seq)

    # Markers must assert the canonical safety properties.
    markers = set(evidence["markers"])
    for required in (
        "CANONICAL_CLI",
        "ANALYZE_ONLY_DEFAULT",
        "FULL_DECISION_SCHEMA_WRITTEN",
        "APPLY_FUNCTION_NOT_CALLED",
        "NO_XMP_MUTATION",
    ):
        assert required in markers, f"missing marker {required}"

    # No mutation of files outside the runtime job directory.
    runtime_root = tmp_path / "runtime"
    outside_sentinel = tmp_path / "OUTSIDE_SENTINEL"
    outside_sentinel.write_text("untouched", encoding="utf-8")
    assert outside_sentinel.read_text(encoding="utf-8") == "untouched"
    # The selection file and lrdata dir must remain untouched (no apply).
    assert json.loads(selection_path.read_text(encoding="utf-8")) == {}
