"""Shared test fixtures for lr_ai_exposure."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lr_ai_exposure.config import load_config, ConfigError


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project layout in a temporary directory."""
    # config/
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)

    # src/lr_ai_exposure/
    pkg_dir = tmp_path / "src" / "lr_ai_exposure"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")

    # runtime/
    (tmp_path / "runtime").mkdir(parents=True)

    # Write a valid settings.json
    settings = {
        "catalog_path": str(Path.home() / "Pictures" / "LR" / "ToTo" / "ToTo.lrcat"),
        "preview_cache_path": str(Path.home() / "Pictures" / "LR" / "ToTo" / "ToDo Previews.lrdata"),
        "runtime_directory": "runtime",
        "export_root": str(Path.home() / "G_Drive"),
        "preview_size": 2048,
        "maximum_delta_ev": 1.0,
        "minimum_apply_confidence": 0.8,
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_model": "",
        "ai_endpoint": "",
    }
    (config_dir / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")

    return tmp_path


@pytest.fixture
def valid_settings_file(tmp_path: Path) -> Path:
    """Return path to a valid settings.json for direct loading tests."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    settings = {
        "catalog_path": str(Path.home() / "Pictures" / "LR" / "ToTo" / "ToTo.lrcat"),
        "preview_cache_path": str(Path.home() / "Pictures" / "LR" / "ToTo" / "ToDo Previews.lrdata"),
        "runtime_directory": "runtime",
        "export_root": str(Path.home() / "G_Drive"),
        "preview_size": 2048,
        "maximum_delta_ev": 1.0,
        "minimum_apply_confidence": 0.8,
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "ai_model": "",
        "ai_endpoint": "",
    }
    (config_dir / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return config_dir / "settings.json"


@pytest.fixture
def malformed_json_file(tmp_path: Path) -> Path:
    """Return path to a file with invalid JSON."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text("{ not valid json }", encoding="utf-8")
    return config_dir / "settings.json"
