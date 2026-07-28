"""Tests for lr_ai_exposure configuration loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lr_ai_exposure.config import load_config, ConfigError


def test_valid_default_config(project_root: Path) -> None:
    """A valid settings.json loads and validates without errors."""
    settings = load_config(project_root)
    assert settings["dry_run"] is True
    assert settings["maximum_delta_ev"] == 1.0
    assert settings["preview_size"] == 2048
    assert settings["minimum_apply_confidence"] == 0.8


def test_missing_required_setting(tmp_path: Path) -> None:
    """A settings.json missing a required field raises ConfigError."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    partial = {
        "catalog_path": str(Path.home()),
        # missing preview_cache_path, runtime_directory, etc.
        "dry_run": True,
    }
    (config_dir / "settings.json").write_text(json.dumps(partial), encoding="utf-8")

    with pytest.raises(ConfigError, match="Missing required setting"):
        load_config(tmp_path)


def test_malformed_json(tmp_path: Path) -> None:
    """A settings.json with invalid JSON raises ConfigError."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text("this is not json", encoding="utf-8")

    with pytest.raises(ConfigError, match="Malformed JSON"):
        load_config(tmp_path)


def test_maximum_delta_ev_zero_rejected(tmp_path: Path) -> None:
    """maximum_delta_ev set to 0 raises ConfigError."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    settings = {
        "catalog_path": str(Path.home()),
        "preview_cache_path": str(Path.home()),
        "runtime_directory": "runtime",
        "export_root": str(Path.home()),
        "preview_size": 2048,
        "maximum_delta_ev": 0,
        "minimum_apply_confidence": 0.8,
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_model": "gemini-2.5-pro",
        "ai_provider": "google",
    }
    (config_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    with pytest.raises(ConfigError, match="maximum_delta_ev must be positive"):
        load_config(tmp_path)


def test_minimum_apply_confidence_out_of_range(tmp_path: Path) -> None:
    """minimum_apply_confidence outside [0, 1] raises ConfigError."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    settings = {
        "catalog_path": str(Path.home()),
        "preview_cache_path": str(Path.home()),
        "runtime_directory": "runtime",
        "export_root": str(Path.home()),
        "preview_size": 2048,
        "maximum_delta_ev": 1.0,
        "minimum_apply_confidence": 1.5,
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_model": "gemini-2.5-pro",
        "ai_provider": "google",
    }
    (config_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    with pytest.raises(ConfigError, match="minimum_apply_confidence must be in"):
        load_config(tmp_path)


def test_invalid_preview_size(tmp_path: Path) -> None:
    """preview_size set to 0 or negative raises ConfigError."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    settings = {
        "catalog_path": str(Path.home()),
        "preview_cache_path": str(Path.home()),
        "runtime_directory": "runtime",
        "export_root": str(Path.home()),
        "preview_size": 0,
        "maximum_delta_ev": 1.0,
        "minimum_apply_confidence": 0.8,
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_model": "gemini-2.5-pro",
        "ai_provider": "google",
    }
    (config_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    with pytest.raises(ConfigError, match="preview_size must be positive"):
        load_config(tmp_path)


def test_runtime_directory_resolved_to_absolute(project_root: Path) -> None:
    """runtime_directory is resolved to an absolute path."""
    settings = load_config(project_root)
    resolved = Path(settings["runtime_directory"])
    assert resolved.is_absolute()


def test_export_root_resolved_to_absolute(project_root: Path) -> None:
    """export_root is resolved to an absolute path."""
    settings = load_config(project_root)
    resolved = Path(settings["export_root"])
    assert resolved.is_absolute()


def test_dry_run_default_true(project_root: Path) -> None:
    """dry_run defaults to True in the checked-in configuration."""
    settings = load_config(project_root)
    assert settings["dry_run"] is True


def test_check_config_exits_zero(project_root: Path, capsys: pytest.CaptureFixture) -> None:
    """--check-config prints a summary and exits 0 for valid config."""
    import sys
    from lr_ai_exposure.main import main

    # Change cwd so load_config finds the temp project root
    import os

    old_cwd = os.getcwd()
    os.chdir(project_root)
    try:
        rc = main(["--check-config"])
        assert rc == 0
        captured = capsys.readouterr()
        summary = json.loads(captured.out)
        assert summary["dry_run"] is True
        assert summary["maximum_delta_ev"] == 1.0
    finally:
        os.chdir(old_cwd)
