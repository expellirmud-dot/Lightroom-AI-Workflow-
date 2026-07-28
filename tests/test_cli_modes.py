"""CLI mode-selection tests for the canonical lr-ai-exposure entry point.

Covers WO-022 requirements 1, 2, and 4:

- ``--analyze-only`` and ``--apply`` are explicit CLI modes.
- ANALYZE_ONLY is the default when neither mode is supplied.
- ``apply_exposure_deltas`` is never called in ANALYZE_ONLY mode.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from lr_ai_exposure.main import _build_parser, _select_mode, main
from lr_ai_exposure.config import ConfigError


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


def test_parser_advertises_both_modes():
    """Both --analyze-only and --apply must be present as CLI options."""
    parser = _build_parser()
    actions = {a.dest for a in parser._actions}
    assert "analyze_only" in actions
    assert "apply" in actions


def test_select_mode_defaults_to_analyze_only():
    """No mode flags -> ANALYZE_ONLY."""
    parser = _build_parser()
    ns = parser.parse_args([])
    assert _select_mode(ns) == "ANALYZE_ONLY"


def test_select_mode_explicit_analyze_only():
    parser = _build_parser()
    ns = parser.parse_args(["--analyze-only"])
    assert _select_mode(ns) == "ANALYZE_ONLY"


def test_select_mode_explicit_apply():
    parser = _build_parser()
    ns = parser.parse_args(["--apply"])
    assert _select_mode(ns) == "APPLY"


def test_select_mode_rejects_both_flags():
    """Supplying both modes must raise ConfigError."""
    parser = _build_parser()
    ns = parser.parse_args(["--analyze-only", "--apply"])
    with pytest.raises(ConfigError):
        _select_mode(ns)


@mock.patch("lr_ai_exposure.apply.apply_exposure_deltas")
@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_analyze_only_mode_does_not_call_apply(
    mock_analyze,
    mock_read_manifest,
    mock_handoff,
    mock_config,
    mock_apply,
    tmp_path,
):
    """ANALYZE_ONLY must never invoke apply_exposure_deltas."""
    from lr_ai_exposure.job import Manifest

    mock_config.return_value = _settings(tmp_path)
    (tmp_path / "runtime/jobs/jobA").mkdir(parents=True)

    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    mock_handoff.return_value = "jobA"
    mock_read_manifest.return_value = Manifest("jobA", [])
    mock_analyze.return_value = []

    rc = main(
        ["--analyze-only", "--selection", str(selection_path), "--lrdata", str(lrdata_path)]
    )
    assert rc == 0
    mock_apply.assert_not_called()
    mock_analyze.assert_called_once()


@mock.patch("lr_ai_exposure.apply.apply_exposure_deltas")
@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_apply_mode_invokes_apply_with_settings(
    mock_analyze,
    mock_read_manifest,
    mock_handoff,
    mock_config,
    mock_apply,
    tmp_path,
):
    """--apply mode routes through apply_exposure_deltas with the settings object."""
    from lr_ai_exposure.job import Manifest

    settings = _settings(tmp_path)
    mock_config.return_value = settings
    (tmp_path / "runtime/jobs/jobB").mkdir(parents=True)

    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    mock_handoff.return_value = "jobB"
    mock_read_manifest.return_value = Manifest("jobB", [])
    mock_analyze.return_value = []
    mock_apply.return_value = {"applied": 0, "skipped": 0, "errors": 0}

    rc = main(
        ["--apply", "--selection", str(selection_path), "--lrdata", str(lrdata_path)]
    )
    assert rc == 0
    mock_apply.assert_called_once()
    # The settings object must be passed through as the fourth argument.
    passed_settings = mock_apply.call_args.args[3]
    assert passed_settings is settings


@mock.patch("lr_ai_exposure.apply.apply_exposure_deltas")
@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.handoff_job")
@mock.patch("lr_ai_exposure.main.read_manifest")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_default_mode_is_analyze_only_and_does_not_apply(
    mock_analyze,
    mock_read_manifest,
    mock_handoff,
    mock_config,
    mock_apply,
    tmp_path,
):
    """Supplying no mode flag defaults to ANALYZE_ONLY and skips apply."""
    from lr_ai_exposure.job import Manifest

    mock_config.return_value = _settings(tmp_path)
    (tmp_path / "runtime/jobs/jobC").mkdir(parents=True)

    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    mock_handoff.return_value = "jobC"
    mock_read_manifest.return_value = Manifest("jobC", [])
    mock_analyze.return_value = []

    rc = main(["--selection", str(selection_path), "--lrdata", str(lrdata_path)])
    assert rc == 0
    mock_apply.assert_not_called()


@mock.patch("lr_ai_exposure.main.load_config")
@mock.patch("lr_ai_exposure.main.analyze_job_single_pass")
def test_settings_passed_through_analysis_boundary(
    mock_analyze, mock_config, tmp_path
):
    """analyze_job_single_pass must receive the validated settings object."""
    mock_config.return_value = _settings(tmp_path)
    # Bypass handoff with a stubbed module-level function.
    job_dir = tmp_path / "runtime/jobs/jobD"
    job_dir.mkdir(parents=True)
    selection_path = tmp_path / "selection.json"
    selection_path.write_text("{}", encoding="utf-8")
    lrdata_path = tmp_path / "Previews.lrdata"
    lrdata_path.mkdir()

    from lr_ai_exposure.job import Manifest

    with (
        mock.patch("lr_ai_exposure.main.handoff_job", return_value="jobD"),
        mock.patch(
            "lr_ai_exposure.main.read_manifest", return_value=Manifest("jobD", [])
        ),
    ):
        rc = main(
            ["--analyze-only", "--selection", str(selection_path), "--lrdata", str(lrdata_path)]
        )
    assert rc == 0
    # analyze_job_single_pass(manifest, job_dir, settings)
    passed_settings = mock_analyze.call_args.args[2]
    assert passed_settings["maximum_delta_ev"] == 1.0
    assert passed_settings["ai_provider"] == "google"
