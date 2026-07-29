from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest import mock

from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest
from lr_ai_exposure.job_lifecycle import prepare_external_ai_job
from lr_ai_exposure.main import _build_parser, _select_operation, main


def test_parser_exposes_prepared_job_lifecycle() -> None:
    actions = {action.dest for action in _build_parser()._actions}
    assert {"prepare_job", "process_job", "apply_job"}.issubset(actions)


def test_prepare_operation_is_distinct_from_analysis() -> None:
    args = _build_parser().parse_args(["--prepare-job"])
    assert _select_operation(args) == "PREPARE"


def test_process_saved_job_operation() -> None:
    args = _build_parser().parse_args(["--process-job", "job-1"])
    assert _select_operation(args) == "PROCESS_SAVED"


def test_apply_saved_job_operation() -> None:
    args = _build_parser().parse_args(["--apply-job", "job-1"])
    assert _select_operation(args) == "APPLY_SAVED"


def _build_saved_job(tmp_path: Path) -> tuple[Path, Path]:
    runtime = tmp_path / "runtime"
    job_dir = runtime / "jobs" / "job-1"
    for name in ("previews", "xmp_backups", "results", "logs"):
        (job_dir / name).mkdir(parents=True, exist_ok=True)

    source = tmp_path / "photos"
    source.mkdir()
    raw_path = source / "A.NEF"
    raw_path.touch()
    xmp_path = source / "A.xmp"
    xmp_path.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n',
        encoding="utf-8",
    )
    preview_bytes = b"prepared-preview"
    preview_path = job_dir / "previews" / "000001__A.jpg"
    preview_path.write_bytes(preview_bytes)

    manifest = Manifest(
        job_id="job-1",
        total_selected=1,
        total_found=1,
        entries=[
            ManifestEntry(
                image_id="1",
                raw_path=str(raw_path.resolve()),
                source_xmp_path=str(xmp_path.resolve()),
                backup_relative_path="xmp_backups/A.xmp",
                preview_path="previews/000001__A.jpg",
                seq=1,
                extraction_status="FOUND",
                uuid="uuid-1",
                preview_bytes=len(preview_bytes),
                preview_sha256=hashlib.sha256(preview_bytes).hexdigest(),
            )
        ],
    )
    write_manifest(job_dir, manifest)
    (job_dir / "selection.json").write_text(
        json.dumps(
            {
                "job_id": "job-1",
                "photos": [
                    {
                        "id_local": "1",
                        "path": str(raw_path.resolve()),
                        "uuid": "uuid-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    prepare_external_ai_job(job_dir, manifest, runtime)
    (job_dir / "decisions" / "1.json").write_text(
        json.dumps(
            {
                "image_id": "1",
                "relevance_verdict": "KEEP",
                "quality_verdict": "KEEP",
                "delta_ev": 0.25,
                "confidence": 0.95,
                "highlight_risk": False,
                "shadow_risk": False,
                "subject_rationale": "subject is slightly dark",
                "scene_rationale": "scene supports a modest lift",
                "batch_consistency_group": "group-1",
                "reason": "matches the reference exposure",
            }
        ),
        encoding="utf-8",
    )
    return runtime, xmp_path


def _settings(runtime: Path) -> dict:
    return {
        "runtime_directory": str(runtime),
        "dry_run": True,
        "apply_authorized": False,
        "approved_image_ids": [],
        "approved_pilot_root": "",
        "maximum_delta_ev": 3.0,
        "minimum_apply_confidence": 0.85,
        "preview_size": 2560,
        "ai_provider": "manual_app",
        "ai_model": "external-file-agent",
        "external_agent_name": "Test Vision Agent",
    }


def test_process_and_apply_reopen_same_job_without_handoff(tmp_path: Path) -> None:
    runtime, xmp_path = _build_saved_job(tmp_path)

    with (
        mock.patch("lr_ai_exposure.main.load_config", return_value=_settings(runtime)),
        mock.patch("lr_ai_exposure.main.handoff_job") as handoff,
    ):
        assert main(["--process-job", "job-1"]) == 0
        handoff.assert_not_called()
        assert (runtime / "jobs" / "job-1" / "ai-decisions.json").is_file()

        assert (
            main(
                [
                    "--apply-job",
                    "job-1",
                    "--authorize-apply",
                    "job-1",
                ]
            )
            == 0
        )
        handoff.assert_not_called()

    assert 'crs:Exposure2012="+0.25"' in xmp_path.read_text(encoding="utf-8")
    evidence = json.loads(
        (runtime / "jobs" / "job-1" / "apply-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["results"][0]["status"] == "APPLIED_VERIFIED"
    assert evidence["results"][0]["backup_path"]
