from __future__ import annotations

import json
from pathlib import Path

import pytest

from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest
from lr_ai_exposure.job_lifecycle import (
    JOB_STATE_PREPARED,
    JobLifecycleError,
    configure_external_file_provider,
    eligible_apply_ids,
    prepare_external_ai_job,
    resolve_saved_job,
)


def _prepared_manifest(tmp_path: Path) -> tuple[Path, Path, Manifest]:
    runtime = tmp_path / "runtime"
    job_dir = runtime / "jobs" / "job-folder"
    (job_dir / "previews").mkdir(parents=True)
    (job_dir / "xmp_backups").mkdir()
    (job_dir / "results").mkdir()
    (job_dir / "logs").mkdir()

    source = tmp_path / "photos"
    source.mkdir()
    preview = job_dir / "previews" / "000001__A.jpg"
    preview.write_bytes(b"jpeg")
    manifest = Manifest(
        job_id="job-folder",
        total_selected=1,
        total_found=1,
        entries=[
            ManifestEntry(
                image_id="1",
                raw_path=str((source / "A.NEF").resolve()),
                source_xmp_path=str((source / "A.xmp").resolve()),
                backup_relative_path="xmp_backups/A.xmp",
                preview_path="previews/000001__A.jpg",
                seq=1,
                extraction_status="FOUND",
                uuid="uuid-1",
                preview_bytes=4,
                preview_sha256="hash",
            )
        ],
    )
    write_manifest(job_dir, manifest)
    (job_dir / "selection.json").write_text(
        json.dumps(
            {
                "job_id": "job-folder",
                "photos": [
                    {
                        "id_local": "1",
                        "path": str((source / "A.NEF").resolve()),
                        "uuid": "uuid-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return runtime, job_dir, manifest


def test_prepare_job_writes_durable_external_ai_bundle(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)

    state = prepare_external_ai_job(job_dir, manifest, runtime)

    assert state["state"] == JOB_STATE_PREPARED
    assert (job_dir / "AI_TASK.md").is_file()
    assert (job_dir / "decision-schema.json").is_file()
    assert (job_dir / "decisions").is_dir()
    assert (job_dir / "job-state.json").is_file()
    assert (runtime / "staging" / "latest-prepared-job.json").is_file()
    task = (job_dir / "AI_TASK.md").read_text(encoding="utf-8")
    assert "exposure-judgment" in task
    assert "batch-consistency-review" in task
    assert "image-relevance-triage" in task
    assert "visual-quality-safety" in task


def test_resolve_saved_job_never_requires_lrdata(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)
    prepare_external_ai_job(job_dir, manifest, runtime)

    resolved_dir, resolved_manifest, selection = resolve_saved_job(
        runtime, "job-folder"
    )

    assert resolved_dir == job_dir.resolve()
    assert resolved_manifest.job_id == "job-folder"
    assert selection == job_dir / "selection.json"


def test_saved_job_id_path_escape_is_rejected(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    with pytest.raises(JobLifecycleError):
        resolve_saved_job(runtime, "../escape")


def test_external_provider_is_job_scoped(tmp_path: Path) -> None:
    settings = {"ai_provider": "google", "ai_model": "old"}
    configured = configure_external_file_provider(settings, tmp_path / "job")
    assert configured["ai_provider"] == "manual_app"
    assert configured["manual_response_directory"] == str(tmp_path / "job" / "decisions")
    assert configured["ai_model"] == "old"
    assert settings["ai_provider"] == "google"


def test_eligible_apply_ids_are_safe_and_non_zero() -> None:
    base = dict(
        relevance_verdict=Verdict.KEEP,
        quality_verdict=Verdict.KEEP,
        confidence=0.9,
        highlight_risk=False,
        shadow_risk=False,
        subject_rationale="subject",
        scene_rationale="scene",
        batch_consistency_group="g",
        reason="ok",
    )
    decisions = [
        SinglePassDecision(image_id="apply", delta_ev=0.25, **base),
        SinglePassDecision(image_id="no-change", delta_ev=0.0, **base),
        SinglePassDecision(
            image_id="review",
            delta_ev=0.25,
            **{**base, "relevance_verdict": Verdict.REVIEW},
        ),
    ]
    assert eligible_apply_ids(decisions, 0.85) == ["apply"]
