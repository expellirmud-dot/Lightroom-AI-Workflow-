"""Tests for main CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from lr_ai_exposure.main import main


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_no_args(mock_config, capsys):
    mock_config.return_value = {"dry_run": True, "maximum_delta_ev": 2.0, "minimum_apply_confidence": 0.8, "preview_size": 2048, "runtime_directory": "scratch"}
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_check_config(mock_config, capsys):
    mock_config.return_value = {"dry_run": True, "maximum_delta_ev": 2.0, "minimum_apply_confidence": 0.8, "preview_size": 2048, "runtime_directory": "scratch"}
    assert main(["--check-config"]) == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    
    assert data["status"] == "ok"
    assert data["dry_run"] is True
    assert data["maximum_delta_ev"] == 2.0


@mock.patch("lr_ai_exposure.main.load_config")
def test_main_missing_selection(mock_config, capsys):
    mock_config.return_value = {"dry_run": True, "maximum_delta_ev": 2.0, "minimum_apply_confidence": 0.8, "preview_size": 2048, "runtime_directory": "scratch"}
    assert main(["--selection", "does-not-exist.json", "--lrdata", "some-dir"]) == 1
    captured = capsys.readouterr()
    assert "ERROR: Selection file not found" in captured.err


@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
@mock.patch("lr_ai_exposure.main.apply_exposure_deltas")
def test_main_e2e_flow(mock_apply, mock_analyze, mock_read_manifest, mock_handoff, mock_config, tmp_path):
    mock_config.return_value = {"dry_run": True, "maximum_delta_ev": 2.0, "minimum_apply_confidence": 0.8, "preview_size": 2048, "runtime_directory": str(tmp_path / "scratch/runtime")}
    
    (tmp_path / "scratch/runtime/jobs/job1").mkdir(parents=True)
    
    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}")
    
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()
    
    # Mock return values
    from lr_ai_exposure.job import Manifest
    mock_handoff.return_value = "job1"
    mock_read_manifest.return_value = Manifest("job1", [])
    mock_analyze.return_value = []
    mock_apply.return_value = {"applied": 1, "skipped": 0, "errors": 0, "details": []}
    
    assert main(["--selection", str(selection_path), "--lrdata", str(lrdata_path)]) == 0
    
    assert mock_handoff.called
    assert mock_analyze.called
    assert mock_apply.called
