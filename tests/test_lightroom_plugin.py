"""Static contract tests for the prepared-folder Lightroom plug-in."""

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
    return path.read_text(encoding="utf-8")


def test_prepare_command_exports_active_folder_once() -> None:
    src = _read("RunExposureAssist.lua")
    assert re.search(r"function\s+RunExposureAssist\.run", src)
    assert "catalog:getActiveSources()" in src
    assert "activeFolder:getPhotos(false)" in src
    assert 'sourceType == "LrFolder"' in src
    assert 'getRawMetadata("isVirtualCopy")' in src
    assert 'getRawMetadata("isVideo")' in src
    assert 'getRawMetadata("fileFormat")' in src
    assert 'fileFormat ~= "RAW"' in src
    assert "catalog:getTargetPhotos()" not in src
    assert "--prepare-job" in src
    assert 'requested_mode = "PREPARE"' in src
    assert "--apply" not in src
    assert "--analyze-only" not in src


def test_prepare_handoff_carries_folder_and_identity_fields() -> None:
    src = _read("RunExposureAssist.lua")
    for field in ("source_folder", "id_local", "path", "uuid"):
        assert field in src
    assert "Json.encode" in src
    assert "preview_cache_path" in src
    assert "skipped_virtual_copies" in src
    assert "skipped_videos" in src
    assert "skipped_unsupported_formats" in src


def test_apply_command_reopens_saved_job_for_matching_active_folder() -> None:
    src = _read("ApplyPreparedJob.lua")
    assert "--apply-job" in src
    assert "--authorize-apply" in src
    assert "latest-prepared-job.json" in src
    assert "pointer.state_path" in src
    assert "state.source_root" in src
    assert "catalog:getActiveSources()" in src
    assert "activeFolder:getPhotos(false)" in src
    assert "catalog:getTargetPhotos()" not in src
    assert "--lrdata" not in src
    assert "--selection" not in src
    assert "APPLIED_VERIFIED" in src
    assert "readMetadata" in src


def test_plugin_never_implements_ai_or_xmp_writes() -> None:
    combined = _read("RunExposureAssist.lua") + _read("ApplyPreparedJob.lua")
    for token in (
        "LrHttp",
        "os.execute",
        "crs:Exposure2012=",
        "writeXmp",
        "LrSocket",
        "LrFTP",
    ):
        assert token.lower() not in combined.lower()


def test_info_registers_prepare_and_apply_menu_items_without_selection_gate() -> None:
    src = _read("Info.lua")
    assert "Diagnose Current Folder" in src
    assert "Prepare Current Folder" in src
    assert "Apply Prepared Job" in src
    assert "RunExposureAssist.lua" in src
    assert "ApplyPreparedJob.lua" in src
    assert "enabledWhen" not in src


def test_diagnostic_command_aggregates_without_xmp_or_apply() -> None:
    src = _read("DiagnoseCurrentFolder.lua")
    assert re.search(r"function\s+DiagnoseCurrentFolder\.run", src)
    assert "catalog:getActiveSources()" in src
    assert "activeFolder:getPhotos(false)" in src
    assert 'safeMetadata(photo, "fileFormat")' in src
    assert 'type(metadata.fileFormat)' in src
    assert "observed_file_formats" in src
    assert "eligible_photos" in src
    assert "offline_paths" in src
    assert "duplicate_paths" in src
    assert "--diagnose-current-folder" in src
    assert "--diagnostic-input" in src
    assert "preflight_json" in src
    assert "diagnostic_txt" in src
    assert "--apply" not in src
    assert "writeMetadata" not in src
    assert "readMetadata" not in src
    assert "Exposure2012" not in src
