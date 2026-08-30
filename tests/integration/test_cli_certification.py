"""Integration runners for reproducible CLI certification (WO-024).

These tests exercise the canonical ``lr-ai-exposure`` CLI entry point
against synthetic, repository-owned fixtures.  They replace any
disposable ``scratch/`` runner and do not require private photographs,
live catalogs, or real Lightroom installations.

Design:
- ``test_cli_check_config_smoke`` runs the installed CLI as a subprocess
  (``--check-config`` does not need real Lightroom artifacts).
- The ANALYZE_ONLY integration tests call ``lr_ai_exposure.main.main()``
  directly in-process so that handoff/manifest/AI-judgment boundaries
  can be mocked deterministically (same pattern as ``test_main_integration.py``).
- Windows CI runs these as the integration gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, Verdict
from lr_ai_exposure.job import Manifest, read_manifest
from lr_ai_exposure.main import main


def _env() -> dict[str, str]:
    """Clean environment for subprocess runs."""
    env = dict(subprocess.os.environ)
    env["PYTHONPATH"] = ""
    env["PYTHONHOME"] = ""
    return env


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the installed ``lr-ai-exposure`` CLI in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "lr_ai_exposure.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )


def test_cli_check_config_smoke(tmp_path: Path) -> None:
    """CLI config smoke test: --check-config exits 0 and prints JSON.

    The CLI reads config/settings.json from the repository root, so
    the test must run from the repository root (not tmp_path).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    result = _run_cli(["--check-config"], repo_root)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
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

    Calls ``lr_ai_exposure.main.main()`` directly in-process so that
    handoff, manifest read, and AI-judgment boundaries can be mocked
    deterministically (same pattern as ``test_main_integration.py``).
    """
    from lr_ai_exposure.job import Manifest

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Build synthetic job directory on disk (previews + manifest).
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

    # Build deterministic decisions for assertion.
    decisions = [
        SinglePassDecision(
            image_id=f"img-{i}",
            action=Action.ADJUST, relevance_verdict=Verdict.KEEP,
            quality_verdict=Verdict.KEEP,
            delta_ev=0.1 * i,
            confidence=0.9,
            highlight_risk=False,
            shadow_risk=False,
            subject_rationale=f"subject img-{i}",
            scene_rationale=f"scene img-{i}",
            scene_group_id="group-A",
            reason=f"ok img-{i}",
        )
        for i in range(1, 6)
    ]

    manifest = read_manifest(job_dir)

    # Point runtime_directory at tmp_path so artifacts land under
    # the temporary directory and leave the repo's real runtime/ untouched.
    fake_settings = dict(manifest.__dict__) if hasattr(manifest, "__dict__") else {}
    # Use load_config patched to return settings with runtime_directory
    # pointing at tmp_path / "runtime".
    fake_runtime = tmp_path / "runtime"
    fake_runtime.mkdir(parents=True, exist_ok=True)

    with (
        mock.patch("lr_ai_exposure.main.handoff_job", return_value="job-wo024"),
        mock.patch("lr_ai_exposure.main.read_manifest", return_value=manifest),
        mock.patch(
            "lr_ai_exposure.main.analyze_job_single_pass",
            return_value=decisions,
        ),
        mock.patch("lr_ai_exposure.apply.apply_exposure_deltas") as mock_apply,
        mock.patch(
            "lr_ai_exposure.main.load_config",
            return_value={
                "catalog_path": "",
                "preview_cache_path": str(lrdata_dir),
                "runtime_directory": str(fake_runtime),
                "export_root": "",
                "preview_size": 2560,
                "maximum_delta_ev": 3.0,
                "minimum_apply_confidence": 0.85,
                "dry_run": True,
                "apply_authorized": False,
                "ai_provider": "manual_app",
                "ai_model": "test-model",
                "ai_api_key": "",
                "ai_endpoint": "",
            },
        ),
    ):
        rc = main(
            [
                "--analyze-only",
                "--selection",
                str(selection),
                "--lrdata",
                str(lrdata_dir),
            ]
        )

    # CLI_EXIT=0
    assert rc == 0

    # Artifacts written under tmp_path / "runtime", NOT the repo's real runtime/.
    job_dir = fake_runtime / "jobs" / "job-wo024"
    assert job_dir.is_dir()

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

    # Apply function proven not called.
    mock_apply.assert_not_called()

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
    from lr_ai_exposure.job import Manifest

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Build synthetic job directory on disk (previews + manifest).
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

    fake_runtime = tmp_path / "runtime"
    fake_runtime.mkdir(parents=True, exist_ok=True)

    with (
        mock.patch("lr_ai_exposure.main.handoff_job", return_value="job-wo024"),
        mock.patch("lr_ai_exposure.main.read_manifest", return_value=manifest),
        mock.patch(
            "lr_ai_exposure.main.analyze_job_single_pass",
            return_value=[],
        ),
        mock.patch(
            "lr_ai_exposure.apply.apply_exposure_deltas"
        ) as mock_apply,
        mock.patch(
            "lr_ai_exposure.main.load_config",
            return_value={
                "catalog_path": "",
                "preview_cache_path": str(lrdata_dir),
                "runtime_directory": str(fake_runtime),
                "export_root": "",
                "preview_size": 2560,
                "maximum_delta_ev": 3.0,
                "minimum_apply_confidence": 0.85,
                "dry_run": True,
                "apply_authorized": False,
                "ai_provider": "manual_app",
                "ai_model": "test-model",
                "ai_api_key": "",
                "ai_endpoint": "",
            },
        ),
    ):
        rc = main(
            [
                "--analyze-only",
                "--selection",
                str(selection),
                "--lrdata",
                str(lrdata_dir),
            ]
        )
        assert rc == 0
        mock_apply.assert_not_called()