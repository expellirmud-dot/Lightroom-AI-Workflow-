"""Regression contracts for the Lightroom SDK boundary.

These tests are intentionally static: CI cannot host Lightroom Classic, so they
protect integration mistakes that otherwise fail only inside Lightroom. A real
owner run remains the final LIVE gate.
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
        "PrepareAIPackage.lua": "return PrepareAIPackage",
        "ImportApplyAIResults.lua": "return ImportApplyAIResults",
        "PrepareNextAIPackage.lua": "return PrepareNextAIPackage",
        "SessionPackageSupport.lua": "return Support",
        # Retained compatibility surfaces.
        "RunExposureAssist.lua": "return RunExposureAssist",
        "ApplyPreparedJob.lua": "return ApplyPreparedJob",
        "IterativeSession.lua": "return IterativeSession",
        "ResumeIterativeSession.lua": "return ResumeIterativeSession",
    }
    for name, return_token in expected.items():
        src = _read(name)
        assert len(src) > 200, f"Suspiciously small plugin module: {name}"
        assert return_token in src, f"{name} missing module return contract"


def test_info_registers_canonical_and_legacy_single_pass_entrypoints() -> None:
    info = _read("Info.lua")
    for name in (
        "DiagnoseCurrentFolder.lua",
        "PrepareAIPackage.lua",
        "ImportApplyAIResults.lua",
        "PrepareNextAIPackage.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
    ):
        assert f'file = "{name}"' in info
    assert 'file = "IterativeSession.lua"' not in info
    assert 'file = "ResumeIterativeSession.lua"' not in info


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


def test_canonical_commands_route_folder_identity_through_shared_support() -> None:
    support = _read("SessionPackageSupport.lua")
    assert 'require "ActiveFolderResolver"' in support
    assert "ActiveFolderResolver.resolveActiveFolder(catalog)" in support
    assert "activeFolder:getPhotos(true)" in support

    for name in (
        "PrepareAIPackage.lua",
        "ImportApplyAIResults.lua",
        "PrepareNextAIPackage.lua",
    ):
        src = _read(name)
        assert 'require "SessionPackageSupport"' in src, name
        assert "Support.getActiveFolderPhotos(catalog)" in src, name


def test_retained_legacy_folder_entrypoints_keep_shared_resolver_contract() -> None:
    for name in (
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "IterativeSession.lua",
        "ResumeIterativeSession.lua",
    ):
        src = _read(name)
        assert 'require "ActiveFolderResolver"' in src, name
        assert "ActiveFolderResolver.resolveActiveFolder(catalog)" in src, name


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
        "PrepareAIPackage.lua",
        "ImportApplyAIResults.lua",
        "PrepareNextAIPackage.lua",
        "SessionPackageSupport.lua",
        "RunExposureAssist.lua",
        "ApplyPreparedJob.lua",
        "IterativeSession.lua",
        "ResumeIterativeSession.lua",
    ):
        src = _read(name)
        for call in sdk_calls:
            pattern = rf"(?<!LrTasks\.)pcall\(function\(\).*?{call}\s*\("
            assert not re.search(pattern, src, flags=re.S), (
                f"{name} wraps Lightroom SDK call {call} in standard Lua pcall; "
                "use LrTasks.pcall or execute directly inside an LrTasks async/protected task"
            )


def test_canonical_iterative_apply_uses_catalog_exposure_only() -> None:
    support = _read("SessionPackageSupport.lua")
    importer = _read("ImportApplyAIResults.lua")

    assert "photo:getDevelopSettings()" in support
    assert "catalog_exposure2012" in support
    assert "photo:applyDevelopSettings({ Exposure2012 = target })" in support
    assert 'catalog:withWriteAccessDo("AI Exposure Assist — Exposure2012"' in support
    assert "expected_before_exposure2012" in support
    assert "observed_after_exposure2012" in support
    assert "CATALOG_DRIFT" in support
    assert "APPLIED_VERIFIED" in support
    assert "readMetadata" not in support
    assert "crs:Exposure2012=" not in support
    assert "writeXmp" not in support

    assert "--analyze-session-pass" in importer
    assert "--apply-session-pass" in importer
    assert "lr_ai_exposure.catalog_confirm" in importer
    assert "--prepare-session-pass" not in importer


def test_decoupled_package_workflow_contract() -> None:
    prepare = _read("PrepareAIPackage.lua")
    importer = _read("ImportApplyAIResults.lua")
    next_package = _read("PrepareNextAIPackage.lua")

    assert "PACKAGE_READY" in prepare
    assert "--start-session" in prepare
    assert "--analyze-session-pass" not in prepare
    assert "--apply-session-pass" not in prepare
    assert "No AI provider will be called" in prepare

    assert "AI_RESULTS_NOT_READY" in importer
    assert "RERENDER_REQUIRED" in importer
    assert "--analyze-session-pass" in importer
    assert "--apply-session-pass" in importer
    assert "--prepare-session-pass" not in importer

    assert "catalog-apply-evidence.json" in next_package
    assert "--prepare-session-pass" in next_package
    assert "--analyze-session-pass" not in next_package
    assert "--apply-session-pass" not in next_package

    combined = "\n".join((prepare, importer, next_package))
    assert "WAITING_FOR_AI" not in combined
    assert "while true" not in combined.lower()
    assert "LrTasks.sleep" not in combined


def test_legacy_pause_resume_files_are_retained_but_not_canonical_menu() -> None:
    start = _read("IterativeSession.lua")
    resume = _read("ResumeIterativeSession.lua")
    info = _read("Info.lua")

    assert "WAITING_FOR_AI" in start
    assert "WAITING_FOR_AI" in resume
    assert "--prepare-session-pass" in resume
    assert 'file = "IterativeSession.lua"' not in info
    assert 'file = "ResumeIterativeSession.lua"' not in info


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
