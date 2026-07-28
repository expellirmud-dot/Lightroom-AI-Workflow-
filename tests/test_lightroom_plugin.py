"""Static contract tests for the Lightroom AI Exposure plugin."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "lightroom-plugin"
    / "AIExposureAssist.lrplugin"
)


def _read(name: str) -> str:
    path = PLUGIN_DIR / name
    assert path.is_file(), f"Missing plugin file: {path}"
    return path.read_text(encoding="utf-8")


def test_runexposureassist_has_required_entries() -> None:
    """RunExposureAssist.lua must expose run."""
    src = _read("RunExposureAssist.lua")
    assert re.search(r"function\s+RunExposureAssist\.run", src), "run() missing"
    assert "return RunExposureAssist" in src, "Module must return itself"


def test_manifest_schema_fields_present() -> None:
    """Selection handoff entries must carry required identity fields."""
    src = _read("RunExposureAssist.lua")
    for field in ("id_local", "path", "uuid"):
        assert field in src, f"Selection entry missing field {field!r}"


def test_uses_secure_json() -> None:
    """Must use local Json module for serialization (WO-028)."""
    src = _read("RunExposureAssist.lua")
    assert "Json.encode" in src, "Must use local Json"


def test_no_ai_or_xmp_write_or_http() -> None:
    """Plugin must not implement AI, XMP writes, HTTP, watchers, or catalog mutation."""
    forbidden = [
        "LrHttp",
        "io.open",
        "os.execute",
        "crs:Exposure2012",
        "xmp:Update",
        "writeXmp",
        "LrSocket",
        "LrFTP",
    ]
    raw = _read("RunExposureAssist.lua")
    code_lines = [
        ln for ln in raw.splitlines()
        if not ln.lstrip().startswith("--") and "--[[" not in ln
    ]
    src = "\n".join(code_lines).lower()
    for token in forbidden:
        assert token.lower() not in src, f"RunExposureAssist.lua must not contain {token!r}"


def test_plugininit_invokes_run() -> None:
    """PluginInit.lua must still bind the command."""
    src = _read("PluginInit.lua")
    assert "AI Exposure Assist" in src
    assert "bindToPluginExtras" in src
