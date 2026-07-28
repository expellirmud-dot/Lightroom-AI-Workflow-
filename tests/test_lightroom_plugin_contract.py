"""Static contract tests for the WO-006 Lightroom plug-in skeleton.

These tests validate the plug-in files without a Lightroom runtime:
- Info.lua parses as valid Lua (when a Lua interpreter is available).
- Required files exist.
- PluginInit.lua registers the `AI Exposure Assist` command.
- RunExposureAssist.lua defines a `run` entry point.
- No catalog write, subprocess, network, preview export, or file mutation
  appears in the skeleton.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "lightroom-plugin"
    / "AIExposureAssist.lrplugin"
)

REQUIRED_FILES = ["Info.lua", "PluginInit.lua", "RunExposureAssist.lua"]


def _read(name: str) -> str:
    path = PLUGIN_DIR / name
    assert path.is_file(), f"Missing plugin file: {path}"
    return path.read_text(encoding="utf-8")


def test_required_plugin_files_exist() -> None:
    """All three skeleton files must be present."""
    for name in REQUIRED_FILES:
        assert (PLUGIN_DIR / name).is_file(), f"Missing {name}"


def test_info_lua_parses() -> None:
    """Info.lua must parse as valid Lua if a Lua interpreter is available."""
    lua = shutil.which("lua") or shutil.which("luac")
    if lua is None:
        pytest.skip("Lua interpreter not available on this host")
    result = subprocess.run(
        [lua, "-e", "dofile('" + str(PLUGIN_DIR / "Info.lua") + "')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Info.lua failed to parse: {result.stderr}"


def test_plugininit_registers_command() -> None:
    """PluginInit.lua must register `AI Exposure Assist` under Plug-in Extras."""
    src = _read("PluginInit.lua")
    assert "AI Exposure Assist" in src, "Command label missing"
    assert "bindToPluginExtras" in src, "Must bind to Plug-in Extras"
    assert "LrPlugin" in src, "Must use LrPlugin SDK import"


def test_runexposureassist_has_run_entry() -> None:
    """RunExposureAssist.lua must expose a `run` function."""
    src = _read("RunExposureAssist.lua")
    assert re.search(r"function\s+RunExposureAssist\.run", src), "run() missing"
    assert "return RunExposureAssist" in src, "Module must return itself"


def test_skeleton_has_no_side_effects() -> None:
    """The WO-006 skeleton (Info.lua, PluginInit.lua) must not write, spawn, or export.

    RunExposureAssist.lua is owned by WO-007 and legitimately uses
    LrExportSession; its contract is covered by test_preview_export_handoff.py.
    """
    forbidden = [
        "LrTasks.execute",
        "io.open",
        "os.execute",
        "LrExportSession",
        "LrHttp",
        "writeFile",
        "xmp_path",
        "preview_path",
    ]
    # Strip Lua comments so safety wording inside comments does not trip.
    wo006_files = ["Info.lua", "PluginInit.lua"]
    for name in wo006_files:
        raw = _read(name)
        code_lines = [
            ln for ln in raw.splitlines()
            if not ln.lstrip().startswith("--") and "--[[" not in ln
        ]
        src = "\n".join(code_lines).lower()
        for token in forbidden:
            assert token.lower() not in src, f"{name} must not contain {token!r}"


def test_info_metadata_valid() -> None:
    """Info.lua must declare plug-in metadata fields."""
    src = _read("Info.lua")
    assert "LrPluginInfo" in src
    assert "VERSION" in src
