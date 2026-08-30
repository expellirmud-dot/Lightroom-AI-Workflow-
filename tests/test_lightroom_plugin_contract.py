"""Static contract tests for the Lightroom Classic plug-in.

These tests validate the plug-in files without a Lightroom runtime:
- Info.lua parses as valid Lua when a Lua interpreter is available.
- Required files exist.
- Info.lua declares the SDK, identity, two menu commands, and version fields.
- Prepare and Apply modules define implementation entry points.
- Metadata/bootstrap files contain no runtime side effects.
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

REQUIRED_FILES = [
    "Info.lua",
    "PluginInit.lua",
    "DiagnoseCurrentFolder.lua",
    "RunExposureAssist.lua",
    "ApplyPreparedJob.lua",
]


def _read(name: str) -> str:
    path = PLUGIN_DIR / name
    assert path.is_file(), f"Missing plugin file: {path}"
    return path.read_text(encoding="utf-8")


def test_required_plugin_files_exist() -> None:
    for name in REQUIRED_FILES:
        assert (PLUGIN_DIR / name).is_file(), f"Missing {name}"


def test_info_lua_parses() -> None:
    lua = shutil.which("lua") or shutil.which("luac")
    if lua is None:
        pytest.skip("Lua interpreter not available on this host")
    result = subprocess.run(
        [lua, "-e", "dofile('" + str(PLUGIN_DIR / "Info.lua") + "')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Info.lua failed to parse: {result.stderr}"


def test_info_metadata_valid() -> None:
    src = _read("Info.lua")
    required_tokens = [
        "LrSdkVersion",
        "LrSdkMinimumVersion",
        "LrToolkitIdentifier",
        "LrPluginName",
        "LrLibraryMenuItems",
        "DiagnoseCurrentFolder.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "VERSION",
    ]
    for token in required_tokens:
        assert token in src, f"Info.lua missing required field {token}"

    assert re.search(r"LrSdkVersion\s*=\s*\d+(?:\.\d+)?", src)
    assert re.search(r"LrSdkMinimumVersion\s*=\s*\d+(?:\.\d+)?", src)
    assert "LrPluginInfo =" not in src
    assert "LrPluginInit =" not in src


def test_info_declares_folder_prepare_and_saved_apply_commands() -> None:
    src = _read("Info.lua")
    assert "Diagnose Current Folder" in src
    assert "Prepare Current Folder" in src
    assert "Apply Prepared Job" in src
    assert 'file = "RunExposureAssist.lua"' in src
    assert 'file = "DiagnoseCurrentFolder.lua"' in src
    assert 'file = "ApplyPreparedJob.lua"' in src
    assert "enabledWhen" not in src


def test_runtime_modules_have_run_entries() -> None:
    diagnose = _read("DiagnoseCurrentFolder.lua")
    prepare = _read("RunExposureAssist.lua")
    apply = _read("ApplyPreparedJob.lua")
    assert re.search(r"function\s+DiagnoseCurrentFolder\.run", diagnose)
    assert "return DiagnoseCurrentFolder" in diagnose
    assert re.search(r"function\s+RunExposureAssist\.run", prepare)
    assert "return RunExposureAssist" in prepare
    assert re.search(r"function\s+ApplyPreparedJob\.run", apply)
    assert "return ApplyPreparedJob" in apply


def test_metadata_and_bootstrap_have_no_side_effects() -> None:
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
    for name in ["Info.lua", "PluginInit.lua"]:
        raw = _read(name)
        code_lines = [
            line
            for line in raw.splitlines()
            if not line.lstrip().startswith("--") and "--[[" not in line
        ]
        src = "\n".join(code_lines).lower()
        for token in forbidden:
            assert token.lower() not in src, f"{name} must not contain {token!r}"
