import json
from pathlib import Path

from lr_ai_exposure.main import main


def _install_legacy_cli_stubs(tmp_path, monkeypatch, *, apply_authorized: bool):
    import lr_ai_exposure.main as main_module

    runtime_dir = tmp_path / "runtime"
    lrdata = tmp_path / "lrdata"
    lrdata.mkdir()
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        '{"job_id": "test-job-123", "photos": []}',
        encoding="utf-8",
    )

    class MockManifest:
        job_id = "test-job-123"
        entries = []

    def mock_handoff(*args, **kwargs):
        job_dir = runtime_dir / "jobs" / "test-job-123"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir, MockManifest()

    monkeypatch.setattr(main_module, "_run_handoff", mock_handoff)
    monkeypatch.setattr(
        main_module,
        "load_config",
        lambda root: {
            "runtime_directory": str(runtime_dir),
            "apply_authorized": apply_authorized,
            "dry_run": False,
            "maximum_delta_ev": 3.0,
            "minimum_apply_confidence": 0.8,
            "preview_size": 1024,
        },
    )
    monkeypatch.setattr(main_module, "_run_analysis", lambda *args: [])
    monkeypatch.setattr(
        main_module,
        "_write_artifacts",
        lambda *args: (Path("decisions.json"), Path("evidence.json")),
    )
    return selection_path, lrdata


def test_missing_two_key_authorization_forces_analyze_only(
    tmp_path, monkeypatch, capsys
):
    selection_path, lrdata = _install_legacy_cli_stubs(
        tmp_path,
        monkeypatch,
        apply_authorized=False,
    )

    exit_code = main(
        [
            "--apply",
            "--selection",
            str(selection_path),
            "--lrdata",
            str(lrdata),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert (
        "WARNING: Missing legacy two-key authorization. "
        "Forcing ANALYZE_ONLY mode."
    ) in captured.err
    assert json.loads(captured.out)["mode"] == "ANALYZE_ONLY"


def test_successful_two_key_authorization(tmp_path, monkeypatch, capsys):
    import lr_ai_exposure.main as main_module

    selection_path, lrdata = _install_legacy_cli_stubs(
        tmp_path,
        monkeypatch,
        apply_authorized=True,
    )
    monkeypatch.setattr(
        main_module,
        "_run_apply",
        lambda *args: {
            "applied": 0,
            "proposed": 0,
            "skipped": 0,
            "errors": 0,
            "details": [],
        },
    )

    exit_code = main(
        [
            "--apply",
            "--authorize-apply",
            "test-job-123",
            "--selection",
            str(selection_path),
            "--lrdata",
            str(lrdata),
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "WARNING: Missing legacy two-key authorization" not in captured.err
    assert json.loads(captured.out)["mode"] == "APPLY"
