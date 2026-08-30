from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from lr_ai_exposure.config import ConfigError
from lr_ai_exposure.main import main


def test_diagnostic_cli_writes_authoritative_bridge_result(tmp_path: Path) -> None:
    request_path = tmp_path / "diagnostic-input.json"
    bridge_path = tmp_path / "diagnostic-bridge.json"
    request_path.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "operation": "DIAGNOSE_CURRENT_FOLDER",
                "diagnostic_id": "diagnostic-cli",
                "plugin": {"version": "1.1.0", "build": 3},
                "catalog_path": "D:/catalog/Test.lrcat",
                "active_sources": [],
                "active_folder_count": 0,
                "active_folder_path": None,
                "direct_photo_count": 0,
                "enumeration_status": "SKIPPED_DEPENDENCY",
                "observed_file_formats": [],
                "counts": {"eligible_raw": 0},
                "samples": {},
                "eligible_photos": [],
            }
        ),
        encoding="utf-8",
    )
    settings = {
        "preview_cache_path": str(tmp_path / "missing.lrdata"),
        "runtime_directory": str(tmp_path / "runtime"),
    }

    with mock.patch("lr_ai_exposure.main.load_config", return_value=settings):
        rc = main(
            [
                "--diagnose-current-folder",
                "--diagnostic-input",
                str(request_path),
                "--bridge-result",
                str(bridge_path),
            ]
        )

    assert rc == 0
    result = json.loads(bridge_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert result["mode"] == "DIAGNOSE_CURRENT_FOLDER"
    assert result["job_id"] == "diagnostic-cli"
    assert result["diagnostic_completed"] is True
    assert Path(result["preflight_json"]).is_file()
    assert Path(result["diagnostic_txt"]).is_file()
    assert result["overall_readiness"] != "READY_FOR_SESSION"


def test_diagnostic_cli_rejects_missing_input_without_apply(tmp_path: Path) -> None:
    bridge_path = tmp_path / "diagnostic-bridge.json"
    settings = {
        "preview_cache_path": str(tmp_path / "missing.lrdata"),
        "runtime_directory": str(tmp_path / "runtime"),
    }

    with mock.patch("lr_ai_exposure.main.load_config", return_value=settings):
        with mock.patch("lr_ai_exposure.main._run_apply") as apply:
            rc = main(
                [
                    "--diagnose-current-folder",
                    "--diagnostic-input",
                    str(tmp_path / "absent.json"),
                    "--bridge-result",
                    str(bridge_path),
                ]
            )

    assert rc == 1
    assert not apply.called
    result = json.loads(bridge_path.read_text(encoding="utf-8"))
    assert result["status"] == "error"
    assert result["mode"] == "DIAGNOSE_CURRENT_FOLDER"


def test_diagnostic_cli_reports_invalid_config_instead_of_failing_early(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "diagnostic-input.json"
    bridge_path = tmp_path / "diagnostic-bridge.json"
    request_path.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "operation": "DIAGNOSE_CURRENT_FOLDER",
                "diagnostic_id": "diagnostic-bad-config",
                "active_sources": [],
                "active_folder_count": 0,
                "direct_photo_count": 0,
                "enumeration_status": "SKIPPED_DEPENDENCY",
                "observed_file_formats": [],
                "counts": {"eligible_raw": 0},
                "samples": {},
                "eligible_photos": [],
            }
        ),
        encoding="utf-8",
    )

    with mock.patch(
        "lr_ai_exposure.main.load_config",
        side_effect=ConfigError("Missing required setting: 'preview_cache_path'"),
    ):
        rc = main(
            [
                "--diagnose-current-folder",
                "--diagnostic-input",
                str(request_path),
                "--bridge-result",
                str(bridge_path),
            ]
        )

    assert rc == 0
    result = json.loads(bridge_path.read_text(encoding="utf-8"))
    report = json.loads(Path(result["preflight_json"]).read_text(encoding="utf-8"))
    cli_stage = next(stage for stage in report["stages"] if stage["stage"] == "cli_config")
    assert cli_stage["status"] == "FAIL"
    assert "CONFIG_INVALID" in cli_stage["reason_codes"]
    assert any(issue["code"] == "CONFIG_INVALID" for issue in report["issues"])
