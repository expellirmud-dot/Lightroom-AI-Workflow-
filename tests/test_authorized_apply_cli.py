import pytest
import json
from pathlib import Path
from lr_ai_exposure.main import main

def test_missing_two_key_authorization_forces_analyze_only(tmp_path, monkeypatch, capsys):
    # Setup mock job and settings
    runtime_dir = tmp_path / "runtime"
    lrdata = tmp_path / "lrdata"
    lrdata.mkdir()
    selection_path = tmp_path / "selection.json"
    
    # We'll use mocked functions to avoid full handoff complexity
    import lr_ai_exposure.main as main_module
    
    class MockManifest:
        job_id = "test-job-123"
        entries = []
        
    def mock_handoff(*args, **kwargs):
        job_dir = runtime_dir / "jobs" / "test-job-123"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir, MockManifest()
        
    monkeypatch.setattr(main_module, "_run_handoff", mock_handoff)
    
    def mock_load_config(root):
        return {
            "runtime_directory": str(runtime_dir),
            "apply_authorized": False, # Missing config authorization
            "dry_run": False,
            "maximum_delta_ev": 3.0,
            "minimum_apply_confidence": 0.8,
            "preview_size": 1024
        }
    monkeypatch.setattr(main_module, "load_config", mock_load_config)
    
    def mock_run_analysis(*args):
        return []
        
    monkeypatch.setattr(main_module, "_run_analysis", mock_run_analysis)
    
    def mock_write_artifacts(*args):
        return Path("decisions.json"), Path("evidence.json")
        
    monkeypatch.setattr(main_module, "_write_artifacts", mock_write_artifacts)
    
    # Write a dummy selection
    selection_path.write_text('{"job_id": "test-job-123", "photos": []}')
    
    # Run CLI with --apply but without --authorize-apply
    argv = [
        "--apply",
        "--selection", str(selection_path),
        "--lrdata", str(lrdata)
    ]
    
    exit_code = main(argv)
    assert exit_code == 0
    
    captured = capsys.readouterr()
    assert "WARNING: Missing two-key authorization. Forcing ANALYZE_ONLY mode." in captured.err
    
    # Mode in output should be ANALYZE_ONLY
    output = json.loads(captured.out)
    assert output["mode"] == "ANALYZE_ONLY"

def test_successful_two_key_authorization(tmp_path, monkeypatch, capsys):
    runtime_dir = tmp_path / "runtime"
    lrdata = tmp_path / "lrdata"
    lrdata.mkdir()
    selection_path = tmp_path / "selection.json"
    
    import lr_ai_exposure.main as main_module
    
    class MockManifest:
        job_id = "test-job-123"
        entries = []
        
    def mock_handoff(*args, **kwargs):
        job_dir = runtime_dir / "jobs" / "test-job-123"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir, MockManifest()
        
    monkeypatch.setattr(main_module, "_run_handoff", mock_handoff)
    
    def mock_load_config(root):
        return {
            "runtime_directory": str(runtime_dir),
            "apply_authorized": True, # Has config authorization
            "dry_run": False,
            "maximum_delta_ev": 3.0,
            "minimum_apply_confidence": 0.8,
            "preview_size": 1024
        }
    monkeypatch.setattr(main_module, "load_config", mock_load_config)
    
    monkeypatch.setattr(main_module, "_run_analysis", lambda *args: [])
    monkeypatch.setattr(main_module, "_write_artifacts", lambda *args: (Path("a"), Path("b")))
    
    def mock_run_apply(*args):
        return {"applied": 0, "proposed": 0, "skipped": 0, "errors": 0, "details": []}
    monkeypatch.setattr(main_module, "_run_apply", mock_run_apply)
    
    selection_path.write_text('{"job_id": "test-job-123", "photos": []}')
    
    # Run CLI with both keys
    argv = [
        "--apply",
        "--authorize-apply", "test-job-123",
        "--selection", str(selection_path),
        "--lrdata", str(lrdata)
    ]
    
    exit_code = main(argv)
    assert exit_code == 0
    
    captured = capsys.readouterr()
    assert "WARNING: Missing two-key authorization" not in captured.err
    
    output = json.loads(captured.out)
    assert output["mode"] == "APPLY"
