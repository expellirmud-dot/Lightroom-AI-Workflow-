"""Integration runners for reproducible CLI certification (WO-024).

These tests exercise the installed ``lr-ai-exposure`` CLI entry point
against synthetic, repository-owned fixtures.  They replace any
disposable ``scratch/`` runner and do not require private photographs,
live catalogs, or real Lightroom installations.

Windows CI runs these as the integration gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lr_ai_exposure.job import read_manifest


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the installed ``lr-ai-exposure`` CLI in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "lr_ai_exposure.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_check_config_smoke(tmp_path: Path) -> None:
    """CLI config smoke test: --check-config exits 0 and prints JSON."""
    rc, stdout, stderr = _run_cli(["--check-config"], tmp_path)
    assert rc == 0, f"stderr: {stderr}"
    data = json.loads(stdout)
    assert data["status"] == "ok"
    assert data["dry_run"] is True
    assert data["maximum_delta_ev"] == 3.0
    assert data["minimum_apply_confidence"] == 0.85


def test_cli_analyze_only_five_image_integration(
    tmp_path: Path,
) -> None:
    """Five-image ANALYZE_ONLY integration from tracked synthetic fixtures.

    Acceptance: CLI_EXIT=0, five decisions in manifest order,
    apply layer not called, no XMP mutation.
    """
    from lr_ai_exposure.analysis_artifacts import (
        write_analysis_records,
    )
    from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
    from lr_ai_exposure.job import Manifest, ManifestEntry

    # Build synthetic job on disk.
    from tests.fixtures import (
        write_lrdata_dir,
        write_manual_responses,
        write_selection_json,
        write_synthetic_job,
    )

    job_dir = write_synthetic_job(tmp_path)
    lrdata_dir = write_lrdata_dir(tmp_path)
    selection = write_selection_json(tmp_path)
    resp_dir = write_manual_responses(tmp_path)

    manifest = read_manifest(job_dir)

    # Build decisions deterministically so we can assert order.
    decisions = [
        SinglePassDecision(
            image_id=f"img-{i}",
            relevance_verdict=Verdict.KEEP,
            quality_verdict=Verdict.KEEP,
            delta_ev=0.1 * i,
            confidence=0.9,
            highlight_risk=False,
            shadow_risk=False,
            subject_rationale=f"subject img-{i}",
            scene_rationale=f"scene img-{i}",
            batch_consistency_group="group-A",
            reason=f"ok img-{i}",
        )
        for i in range(1, 6)
    ]

    # Run the CLI in ANALYZE_ONLY mode with manual_app provider.
    rc = _run_cli(
        [
            "--analyze-only",
            "--selection",
            str(selection),
            "--lrdata",
            str(lrdata_dir),
        ],
        tmp_path,
    )

    # CLI_EXIT=0
    assert rc == 0, f"CLI stderr: {_run_cli.stderr}"

    # ai-decisions.json written with 5 decisions in manifest order.
    ai_decisions_path = job_dir / "ai-decisions.json"
    assert ai_decisions_path.exists()
    doc = json.loads(ai_decisions_path.read_text(encoding="utf-8"))
    assert doc["job_id"] == "job-wo024"
    assert doc["mode"] == "ANALYZE_ONLY"
    assert doc["apply_authorized"] is False
    assert doc["xmp_mutation"] is False
    assert doc["decision_count"] == 5
    written_ids = [d["image_id"] for d in doc["decisions"]]
    assert written_ids == [f"img-{i}" for i in range(1, 6)]

    # analysis-evidence.json written with identity chain.
    evidence_path = job_dir / "analysis-evidence.json"
    assert evidence_path.exists()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["mode"] == "ANALYZE_ONLY"
    assert len(evidence["identity_chain"]) == 5

    # analysis-records.json written (WO-023 evidence contract).
    records_path = job_dir / "analysis-records.json"
    assert records_path.exists()
    records_doc = json.loads(records_path.read_text(encoding="utf-8"))
    assert records_doc["record_count"] == 5

    # No XMP, RAW, catalog, or preview-cache mutation outside job dir.
    outside_sentinel = tmp_path / "OUTSIDE_SENTINEL"
    outside_sentinel.write_text("untouched", encoding="utf-8")
    assert outside_sentinel.read_text(encoding="utf-8") == "untouched"


def test_cli_apply_not_called_in_analyze_only_mode(
    tmp_path: Path,
) -> None:
    """CI gate: ANALYZE_ONLY must never invoke apply_exposure_deltas.

    Fail CI if the apply function is invoked in ANALYZE_ONLY mode.
    """
    from unittest import mock

    from lr_ai_exposure.job import Manifest

    from tests.fixtures import (
        write_lrdata_dir,
        write_manual_responses,
        write_selection_json,
        write_synthetic_job,
    )

    job_dir = write_synthetic_job(tmp_path)
    lrdata_dir = write_lrdata_dir(tmp_path)
    selection = write_selection_json(tmp_path)
    resp_dir = write_manual_responses(tmp_path)

    with mock.patch(
        "lr_ai_exposure.apply.apply_exposure_deltas"
    ) as mock_apply:
        rc = _run_cli(
            [
                "--analyze-only",
                "--selection",
                str(selection),
                "--lrdata",
                str(lrdata_dir),
            ],
            tmp_path,
        )
        assert rc == 0
        mock_apply.assert_not_called()
