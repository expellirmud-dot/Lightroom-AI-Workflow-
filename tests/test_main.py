"""Tests for main CLI.

These tests cover the canonical CLI surface: configuration check,
argument handling, and the default ANALYZE_ONLY execution path.
End-to-end artifact verification lives in ``test_main_integration.py``;
mode-selection verification lives in ``test_cli_modes.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from lr_ai_exposure.main import main


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_no_args(mock_config, capsys):
    mock_config.return_value = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": "scratch",
    }
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_check_config(mock_config, capsys):
    mock_config.return_value = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": "scratch",
    }
    assert main(["--check-config"]) == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["status"] == "ok"
    assert data["dry_run"] is True
    assert data["maximum_delta_ev"] == 2.0


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_missing_selection(mock_config, capsys):
    mock_config.return_value = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": "scratch",
    }
    assert main(["--selection", "does-not-exist.json", "--lrdata", "some-dir"]) == 1
    captured = capsys.readouterr()
    assert "ERROR: Selection file not found" in captured.err


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_conflicting_modes_rejected(mock_config, capsys):
    """--analyze-only and --apply are mutually exclusive."""
    mock_config.return_value = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": "scratch",
    }
    rc = main(["--analyze-only", "--apply", "--selection", "x.json", "--lrdata", "d"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Conflicting modes" in captured.err


@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_main_default_does_not_apply(
    mock_analyze, mock_read_manifest, mock_handoff, mock_config, tmp_path
):
    """Default mode is ANALYZE_ONLY and the apply layer is never imported."""
    mock_config.return_value = {
        "dry_run": True,
        "maximum_delta_ev": 2.0,
        "minimum_apply_confidence": 0.8,
        "preview_size": 2048,
        "runtime_directory": str(tmp_path / "runtime"),
        "ai_provider": "google",
        "ai_model": "gemini-2.5-pro",
    }

    (tmp_path / "runtime/jobs/job1").mkdir(parents=True)

    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")

    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    from lr_ai_exposure.job import Manifest

    mock_handoff.return_value = "job1"
    mock_read_manifest.return_value = Manifest("job1", [])
    mock_analyze.return_value = []

    with mock.patch("builtins.__import__", wraps=__import__) as mock_import:
        assert (
            main(["--selection", str(selection_path), "--lrdata", str(lrdata_path)])
            == 0
        )
        # The apply module must never be imported under the default mode.
        imported_names = [c.args[0] for c in mock_import.call_args_list]
        assert not any("lr_ai_exposure.apply" == n for n in imported_names), (
            "ANALYZE_ONLY imported the apply layer"
        )

    assert mock_handoff.called
    assert mock_analyze.called
