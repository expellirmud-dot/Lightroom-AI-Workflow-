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


IMMUTABLE_ARTIFACTS = {
    "selection.json",
    "manifest.json",
    "AI_TASK.md",
    "AI_SKILLS.md",
    "decision-schema.json",
}


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


def test_prepare_job_writes_self_contained_external_ai_bundle(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)

    state = prepare_external_ai_job(job_dir, manifest, runtime)

    assert state["state"] == JOB_STATE_PREPARED
    assert (job_dir / "AI_TASK.md").is_file()
    assert (job_dir / "AI_SKILLS.md").is_file()
    assert (job_dir / "decision-schema.json").is_file()
    assert (job_dir / "decisions").is_dir()
    assert (job_dir / "job-state.json").is_file()
    assert (runtime / "staging" / "latest-prepared-job.json").is_file()
    assert state["ai_skills"] == str(job_dir.resolve() / "AI_SKILLS.md")
    assert set(state["artifact_sha256"]) == IMMUTABLE_ARTIFACTS
    assert all(len(value) == 64 for value in state["artifact_sha256"].values())

    persisted_state = json.loads(
        (job_dir / "job-state.json").read_text(encoding="utf-8")
    )
    assert persisted_state["artifact_sha256"] == state["artifact_sha256"]

    task = (job_dir / "AI_TASK.md").read_text(encoding="utf-8")
    assert "Read `AI_SKILLS.md` completely" in task
    for skill_name in (
        "exposure-judgment",
        "batch-consistency-review",
        "image-relevance-triage",
        "visual-quality-safety",
    ):
        assert skill_name in task

    skills = (job_dir / "AI_SKILLS.md").read_text(encoding="utf-8")
    assert "# Skill: exposure-judgment" in skills
    assert "# Skill: batch-consistency-review" in skills
    assert "# Skill: image-relevance-triage" in skills
    assert "# Skill: visual-quality-safety" in skills
    assert "DELTA_EV_GUIDE.md" in skills
    assert "GROUPING_RULES.md" in skills


def test_prepare_job_fails_closed_when_skill_source_is_missing(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)
    empty_project = tmp_path / "empty-project"
    empty_project.mkdir()

    with pytest.raises(JobLifecycleError, match="skill entrypoint not found"):
        prepare_external_ai_job(
            job_dir,
            manifest,
            runtime,
            project_root=empty_project,
        )


def test_resolve_saved_job_never_requires_lrdata(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)
    prepare_external_ai_job(job_dir, manifest, runtime)

    resolved_dir, resolved_manifest, selection = resolve_saved_job(
        runtime, "job-folder"
    )

    assert resolved_dir == job_dir.resolve()
    assert resolved_manifest.job_id == "job-folder"
    assert selection == job_dir / "selection.json"


def test_resolve_saved_job_rejects_missing_skill_bundle(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)
    prepare_external_ai_job(job_dir, manifest, runtime)
    (job_dir / "AI_SKILLS.md").unlink()

    with pytest.raises(JobLifecycleError, match="Prepared job artifact not found"):
        resolve_saved_job(runtime, "job-folder")


def test_resolve_saved_job_rejects_modified_immutable_artifact(tmp_path: Path) -> None:
    runtime, job_dir, manifest = _prepared_manifest(tmp_path)
    prepare_external_ai_job(job_dir, manifest, runtime)
    skills_path = job_dir / "AI_SKILLS.md"
    skills_path.write_text(
        skills_path.read_text(encoding="utf-8") + "\nunauthorized edit\n",
        encoding="utf-8",
    )

    with pytest.raises(JobLifecycleError, match="artifact integrity mismatch"):
        resolve_saved_job(runtime, "job-folder")


def test_saved_job_id_path_escape_is_rejected(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    with pytest.raises(JobLifecycleError):
        resolve_saved_job(runtime, "../escape")


def test_external_provider_is_job_scoped(tmp_path: Path) -> None:
    settings = {"ai_provider": "google", "ai_model": "old"}
    configured = configure_external_file_provider(settings, tmp_path / "job")
    assert configured["ai_provider"] == "manual_app"
    assert configured["manual_response_directory"] == str(
        tmp_path / "job" / "decisions"
    )
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
