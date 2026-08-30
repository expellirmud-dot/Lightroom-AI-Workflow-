"""Regression contracts for the Lightroom SDK boundary.

These tests are intentionally static: CI cannot host Lightroom Classic, so they
protect the exact integration mistakes that previously passed Python tests but
failed only inside Lightroom. A real owner run remains the final LIVE gate.
"""

from __future__ import annotations

import re
from pathlib import Path

PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "lightroom-plugin"
    / "AIExposureAssist.lrplugin"
)


def _read(name: str) -> str:
    path = PLUGIN_DIR / name
    assert path.is_file(), f"Missing plugin file: {path}"
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"Plugin file is empty: {path}"
    return content


def test_critical_plugin_modules_exist_and_are_nonempty() -> None:
    expected = {
        "ActiveFolderResolver.lua": "return ActiveFolderResolver",
        "DiagnoseCurrentFolder.lua": "return DiagnoseCurrentFolder",
        "RunExposureAssist.lua": "return RunExposureAssist",
        "ApplyPreparedJob.lua": "return ApplyPreparedJob",
        "IterativeSession.lua": "return IterativeSession",
    }
    for name, return_token in expected.items():
        src = _read(name)
        assert len(src) > 200, f"Suspiciously small plugin module: {name}"
        assert return_token in src, f"{name} missing module return contract"


def test_info_registers_every_runtime_entrypoint() -> None:
    info = _read("Info.lua")
    for name in (
        "DiagnoseCurrentFolder.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "IterativeSession.lua",
    ):
        assert f'file = "{name}"' in info


def test_active_folder_resolver_treats_lightroom_type_as_authoritative() -> None:
    src = _read("ActiveFolderResolver.lua")
    assert 'sourceType == "LrFolder"' in src
    assert "info.is_folder = true" in src
    assert "source_type_status" in src
    assert "get_path_status" in src
    assert "get_path_error" in src
    assert "Do not demote a real" in src


def test_active_folder_resolver_routes_sdk_calls_through_yield_safe_wrapper() -> None:
    src = _read("ActiveFolderResolver.lua")
    assert 'import "LrTasks"' in src
    assert "LrTasks.pcall(func)" in src
    for call in (
        "catalog:getActiveSources()",
        "source:getName()",
        "source:getPath()",
        "source:type()",
    ):
        assert re.search(
            rf"sdkCall\(function\(\).*?{re.escape(call)}.*?end\)",
            src,
            flags=re.S,
        ), f"SDK call is not routed through sdkCall: {call}"


def test_diagnostic_enumeration_uses_lrtasks_pcall_not_lua_pcall() -> None:
    src = _read("DiagnoseCurrentFolder.lua")
    assert "local ok, value = LrTasks.pcall(func)" in src
    assert re.search(
        r"LrTasks\.pcall\(function\(\)\s*return activeFolder:getPhotos\(false\)",
        src,
        flags=re.S,
    )
    assert re.search(
        r"LrTasks\.pcall\(function\(\)\s*return activeFolder:getPhotos\(true\)",
        src,
        flags=re.S,
    )
    assert not re.search(
        r"(?<!LrTasks\.)pcall\(function\(\)\s*return activeFolder:getPhotos",
        src,
        flags=re.S,
    )


def test_diagnostic_child_and_metadata_probes_share_yield_safe_wrapper() -> None:
    src = _read("DiagnoseCurrentFolder.lua")
    assert "local kids = safeCall({}, function() return f:getChildren() or {} end)" in src
    assert "return photo:getRawMetadata(key)" in src
    safe_call = re.search(
        r"local function safeCall\(defaultValue, func\)(.*?)end\n\nlocal function safeMetadata",
        src,
        flags=re.S,
    )
    assert safe_call, "safeCall implementation not found"
    assert "LrTasks.pcall(func)" in safe_call.group(1)
    assert "pcall(func)" not in safe_call.group(1).replace("LrTasks.pcall(func)", "")


def test_diagnostic_preserves_exact_folder_resolution_evidence() -> None:
    src = _read("DiagnoseCurrentFolder.lua")
    for field in (
        "source_type",
        "source_type_status",
        "source_type_error",
        "get_path_status",
        "get_path_error",
        "enumeration_error",
    ):
        assert field in src
    assert "getPhotos(true) failed:" in src
    assert "getPhotos(false) failed:" in src


def test_diagnostic_version_matches_current_plugin_metadata() -> None:
    info = _read("Info.lua")
    diagnose = _read("DiagnoseCurrentFolder.lua")
    assert re.search(r"major\s*=\s*1", info)
    assert re.search(r"minor\s*=\s*2", info)
    assert re.search(r"revision\s*=\s*0", info)
    assert re.search(r"build\s*=\s*1", info)
    assert 'payload.plugin = { version = "1.2.0", build = 1 }' in diagnose


def test_all_folder_entrypoints_use_the_shared_resolver() -> None:
    for name in (
        "DiagnoseCurrentFolder.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "IterativeSession.lua",
    ):
        src = _read(name)
        assert 'require "ActiveFolderResolver"' in src, name
        assert "ActiveFolderResolver.resolveActiveFolder(catalog)" in src, name


def test_whole_folder_entrypoints_are_recursive() -> None:
    for name in ("DiagnoseCurrentFolder.lua", "RunExposureAssist.lua", "IterativeSession.lua"):
        src = _read(name)
        assert "getPhotos(true)" in src, name


def test_operational_plugins_do_not_wrap_known_sdk_calls_in_plain_pcall() -> None:
    """Catch the nested Lua-pcall regression that only failed in Lightroom."""
    sdk_calls = (
        "getActiveSources",
        "getPath",
        "getChildren",
        "getPhotos",
        "getRawMetadata",
        "readMetadata",
        "getDevelopSettings",
        "applyDevelopSettings",
    )
    for name in (
        "DiagnoseCurrentFolder.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "IterativeSession.lua",
    ):
        src = _read(name)
        for call in sdk_calls:
            pattern = rf"(?<!LrTasks\.)pcall\(function\(\).*?{call}\s*\("
            assert not re.search(pattern, src, flags=re.S), (
                f"{name} wraps Lightroom SDK call {call} in standard Lua pcall; "
                "use LrTasks.pcall or execute directly inside an LrTasks async/protected task"
            )


def test_iterative_session_uses_catalog_exposure_only() -> None:
    src = _read("IterativeSession.lua")
    assert "photo:getDevelopSettings()" in src
    assert "catalog_exposure2012" in src
    assert "photo:applyDevelopSettings({ Exposure2012 = target })" in src
    assert 'catalog:withWriteAccessDo("AI Exposure Assist — Exposure2012"' in src
    assert "expected_before_exposure2012" in src
    assert "observed_after_exposure2012" in src
    assert "CATALOG_DRIFT" in src
    assert "APPLIED_VERIFIED" in src
    assert "lr_ai_exposure.catalog_confirm" in src
    assert "readMetadata" not in src
    assert "crs:Exposure2012=" not in src
    assert "writeXmp" not in src


def test_diagnostic_remains_read_only_while_probing_live_boundaries() -> None:
    src = _read("DiagnoseCurrentFolder.lua")
    for forbidden in (
        "--apply",
        "writeMetadata",
        "readMetadata",
        "crs:Exposure2012=",
        "writeXmp",
    ):
        assert forbidden.lower() not in src.lower()
