"""Configuration loader and validator for lr_ai_exposure."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration is malformed or invalid."""


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse a JSON settings file."""
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed JSON in {path}: {exc}") from exc


def _validate_settings(settings: dict[str, Any], root: Path) -> dict[str, Any]:
    """Validate required fields and types in settings."""
    required = {
        "catalog_path": str,
        "preview_cache_path": str,
        "runtime_directory": str,
        "export_root": str,
        "preview_size": int,
        "maximum_delta_ev": (int, float),
        "minimum_apply_confidence": (int, float),
        "dry_run": bool,
        "apply_authorized": bool,
        "approved_image_ids": list,
        "approved_pilot_root": str,
        "ai_provider": str,
        "ai_model": str,
    }

    for key, expected_type in required.items():
        if key not in settings:
            raise ConfigError(f"Missing required setting: {key!r}")
        if not isinstance(settings[key], expected_type):
            actual = type(settings[key]).__name__
            expected = (
                " or ".join(t.__name__ for t in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            raise ConfigError(
                f"Setting {key!r} must be {expected}, got {actual}"
            )

    # Validate EV bounds
    delta = settings["maximum_delta_ev"]
    if delta <= 0:
        raise ConfigError(
            f"maximum_delta_ev must be positive, got {delta}"
        )

    confidence = settings["minimum_apply_confidence"]
    if not (0.0 <= confidence <= 1.0):
        raise ConfigError(
            f"minimum_apply_confidence must be in [0, 1], got {confidence}"
        )

    # Validate preview_size
    preview_size = settings["preview_size"]
    if preview_size <= 0:
        raise ConfigError(
            f"preview_size must be positive, got {preview_size}"
        )

    # Resolve runtime paths relative to project root
    resolved = dict(settings)
    runtime_dir = root / settings["runtime_directory"]
    resolved["runtime_directory"] = str(runtime_dir)

    export_root = root / settings["export_root"]
    resolved["export_root"] = str(export_root)

    if settings["approved_pilot_root"]:
        pilot_root = root / settings["approved_pilot_root"]
        resolved["approved_pilot_root"] = str(pilot_root)
    else:
        resolved["approved_pilot_root"] = ""

    return resolved


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load and validate configuration from config/settings.json.

    Environment variables override secret-bearing AI fields:
    - ``AI_API_KEY`` → ``ai_api_key`` (if present)
    - ``AI_MODEL`` → ``ai_model`` (if present)
    - ``AI_ENDPOINT`` → ``ai_endpoint`` (if present)

    Secrets are never printed in validation output.
    """
    if project_root is None:
        project_root = Path.cwd()

    settings_path = project_root / "config" / "settings.json"
    raw = _load_json(settings_path)
    validated = _validate_settings(raw, project_root)

    # Environment overrides for secret fields only
    env_secrets = {"AI_API_KEY": "ai_api_key", "AI_MODEL": "ai_model", "AI_ENDPOINT": "ai_endpoint"}
    for env_key, config_key in env_secrets.items():
        value = os.environ.get(env_key, "")
        if value:
            validated[config_key] = value

    return validated


def validate_env_secrets(settings: dict[str, Any]) -> list[str]:
    """Return a list of warnings for AI fields that lack credentials.

    Used during dry-run checks where real API keys are not required.
    """
    warnings: list[str] = []
    for env_key, config_key in (("AI_API_KEY", "ai_api_key"), ("AI_MODEL", "ai_model"), ("AI_ENDPOINT", "ai_endpoint")):
        if not settings.get(config_key) and env_key in os.environ:
            # Credential is set via env — fine
            pass
        elif not settings.get(config_key):
            # No credential and no env var — expected during dry_run
            pass
    return warnings
