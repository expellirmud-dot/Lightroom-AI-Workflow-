"""Static contract tests for the WO-007 preview export and manifest handoff.

These tests validate the plug-in Lua without a Lightroom runtime:
- RunExposureAssist.lua defines `run`, `previewName`, and `buildExportSettings`.
- Preview naming follows the WO-007 contract: `{seq:06d}__{raw_stem}.jpg`.
- Export settings use JPEG format with specific-folder destination.
- Manifest entries carry the WO-005 schema fields (image_id, raw_path,
  xmp_path, preview_path, seq).
- No AI, XMP write, HTTP server, watcher, or catalog mutation appears.
"""

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
    """RunExposureAssist.lua must expose run, previewName, buildExportSettings."""
    src = _read("RunExposureAssist.lua")
    assert re.search(r"function\s+RunExposureAssist\.run", src), "run() missing"
    assert re.search(r"function\s+RunExposureAssist\.previewName", src), "previewName() missing"
    assert re.search(r"function\s+RunExposureAssist\.buildExportSettings", src), "buildExportSettings() missing"
    assert "return RunExposureAssist" in src, "Module must return itself"


def test_preview_naming_schema() -> None:
    """Preview naming must be `{seq:06d}__{raw_stem}.jpg` (WO-007 contract)."""
    src = _read("RunExposureAssist.lua")
    assert "%06d__%s.jpg" in src, "previewName must use {seq:06d}__{raw_stem}.jpg"
    assert "jpg" in src.lower()


def test_export_settings_use_jpeg() -> None:
    """Export settings must select JPEG format and a specific folder."""
    src = _read("RunExposureAssist.lua")
    assert "LR_format" in src and '"JPEG"' in src, "Must export JPEG"
    assert "specificFolder" in src, "Must target a specific folder"
    assert "LrExportSession" in src, "Must use LrExportSession SDK"


def test_manifest_schema_fields_present() -> None:
    """Manifest handoff entries must carry WO-005 schema fields."""
    src = _read("RunExposureAssist.lua")
    for field in ("image_id", "raw_path", "xmp_path", "preview_path", "seq"):
        assert field in src, f"Manifest entry missing field {field!r}"


def test_no_ai_or_xmp_write_or_http() -> None:
    """WO-007 must not implement AI, XMP writes, HTTP, watchers, or catalog mutation."""
    forbidden = [
        "LrHttp",
        "LrTasks.execute",
        "io.open",
        "os.execute",
        "crs:Exposure2012",
        "xmp:Update",
        "writeXmp",
        "LrSocket",
        "LrFTP",
    ]
    # Strip Lua block/line comments before scanning for forbidden tokens,
    # so safety wording inside comments does not trip the contract.
    raw = _read("RunExposureAssist.lua")
    code_lines = [
        ln for ln in raw.splitlines()
        if not ln.lstrip().startswith("--") and "--[[" not in ln
    ]
    src = "\n".join(code_lines).lower()
    for token in forbidden:
        assert token.lower() not in src, f"RunExposureAssist.lua must not contain {token!r}"


def test_plugininit_invokes_run() -> None:
    """PluginInit.lua must still bind the command (no side-effect regression)."""
    src = _read("PluginInit.lua")
    assert "AI Exposure Assist" in src
    assert "bindToPluginExtras" in src
