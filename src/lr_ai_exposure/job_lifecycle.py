"""Prepared-folder job lifecycle for external vision agents.

The Lightroom plug-in prepares a complete, immutable job bundle once. Any
file-capable vision agent may then inspect the exported previews and write one
validated JSON decision per FOUND manifest entry. The apply stage re-opens the
same job and never re-reads the Lightroom preview cache.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict, Action
from lr_ai_exposure.job import Manifest, ManifestError, read_manifest


class JobLifecycleError(ValueError):
    """Raised when a prepared job is missing, unsafe, or internally inconsistent."""


JOB_STATE_PREPARED = "PREPARED"
JOB_STATE_DECISIONS_VALIDATED = "DECISIONS_VALIDATED"
JOB_STATE_APPLY_COMPLETED = "APPLY_COMPLETED"
JOB_STATE_APPLY_COMPLETED_WITH_SKIPS = "APPLY_COMPLETED_WITH_SKIPS"
JOB_STATE_APPLY_FAILED = "APPLY_FAILED"

_EXTERNAL_AI_SKILLS = (
    "exposure-judgment",
    "batch-consistency-review",
    "image-relevance-triage",
    "visual-quality-safety",
)
_SKILL_FILE_SUFFIXES = {".md", ".json"}
_IMMUTABLE_JOB_ARTIFACTS = (
    "selection.json",
    "manifest.json",
    "AI_TASK.md",
    "AI_SKILLS.md",
    "decision-schema.json",
)


def _atomic_write_json(path: Path, payload: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)
    return path


def _atomic_write_text(path: Path, content: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)
    return path


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise JobLifecycleError(f"Cannot hash prepared-job artifact {path}: {exc}") from exc


def _single_source_root(manifest: Manifest) -> Path:
    parents = {Path(entry.raw_path).resolve().parent for entry in manifest.entries}
    if len(parents) != 1:
        raise JobLifecycleError(
            "A prepared folder job must contain photos from exactly one source "
            f"folder; found {len(parents)} source folders."
        )
    return next(iter(parents))


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_ai_skill_bundle(project_root: Path) -> str:
    """Bundle all canonical visual-skill Markdown/JSON files deterministically."""
    project_root = Path(project_root).resolve()
    skills_root = project_root / ".agents" / "skills"
    sections: list[str] = [
        "# Lightroom AI Exposure — Bundled Visual Skills",
        "",
        "This immutable job artifact contains the repository's four canonical ",
        "visual skills. Apply every rule below to the actual preview images. ",
        "AI_TASK.md and decision-schema.json are authoritative for output fields.",
        "",
    ]

    for skill_name in _EXTERNAL_AI_SKILLS:
        skill_root = skills_root / skill_name
        entrypoint = skill_root / "SKILL.md"
        if not entrypoint.is_file():
            raise JobLifecycleError(
                f"Canonical AI skill entrypoint not found: {entrypoint}"
            )

        files = sorted(
            path
            for path in skill_root.rglob("*")
            if path.is_file() and path.suffix.lower() in _SKILL_FILE_SUFFIXES
        )
        if entrypoint not in files:
            raise JobLifecycleError(
                f"Canonical AI skill entrypoint was not included: {entrypoint}"
            )

        sections.extend([f"# Skill: {skill_name}", ""])
        for path in files:
            relative = path.relative_to(project_root).as_posix()
            try:
                content = path.read_text(encoding="utf-8").rstrip()
            except OSError as exc:
                raise JobLifecycleError(
                    f"Cannot read canonical AI skill file {path}: {exc}"
                ) from exc
            sections.extend([f"## Source: `{relative}`", "", content, ""])

    return "\n".join(sections).rstrip() + "\n"


def _task_markdown(job_dir: Path, manifest: Manifest, skills_path: Path) -> str:
    found = [entry for entry in manifest.entries if entry.extraction_status == "FOUND"]
    return f"""# External AI Exposure Task

## Job

- Job ID: `{manifest.job_id}`
- Manifest: `{job_dir / 'manifest.json'}`
- Preview directory: `{job_dir / 'previews'}`
- Decision directory: `{job_dir / 'decisions'}`
- Decision schema: `{job_dir / 'decision-schema.json'}`
- Bundled visual skills: `{skills_path}`
- FOUND previews requiring decisions: **{len(found)}**

## Required operating model

1. Read `AI_SKILLS.md` completely before judging any image.
2. Read `manifest.json` in manifest order.
3. Inspect every preview whose `extraction_status` is `FOUND`.
4. Apply all four bundled skills:
   - `exposure-judgment`
   - `batch-consistency-review`
   - `image-relevance-triage`
   - `visual-quality-safety`
5. Write exactly one UTF-8 JSON file per FOUND image to `decisions/`.
6. The filename should be `<image_id>.json`; the declared `image_id` inside
   the JSON is authoritative and must exactly match the manifest.
7. Do not create responses for MISSING, AMBIGUOUS, INVALID_JPEG, or failed
   manifest entries.
8. Do not modify RAW, XMP, Lightroom catalog, preview cache, manifest,
   `AI_TASK.md`, `AI_SKILLS.md`, schema, or preview files.

## What the AI must judge

- Intended subject and whether a person is the primary subject.
- Subject exposure, background exposure, and scene intent.
- Highlight and shadow safety.
- Focus, blur, obstruction, accidental/test-shot evidence, and technical use.
- Event/narrative relevance and duplicate/supporting value.
- Visual grouping, reference-frame choice, and exposure consistency across
  materially similar images.
- A bounded `delta_ev`; use `0.0` when no exposure change is justified.
- `KEEP`, `REVIEW`, or `SKIP` verdicts with grounded rationales.

## Required JSON fields
```json
{{
  "image_id": "<manifest image_id>",
  "action": "PASS | ADJUST | REVIEW",
  "relevance_verdict": "KEEP | REVIEW | SKIP",
  "quality_verdict": "KEEP | REVIEW | SKIP",
  "delta_ev": 0.0,
  "confidence": 0.0,
  "highlight_risk": false,
  "shadow_risk": false,
  "subject_rationale": "grounded subject observation",
  "scene_rationale": "grounded scene and exposure observation",
  "scene_group_id": "stable visual group",
  "is_reference": false,
  "reason": "concise final rationale"
}}
```

`AI_TASK.md` and `decision-schema.json` override any conceptual labels in the
skill references. Extra JSON fields are rejected. The application validates
all files before any XMP mutation; missing, unknown, duplicate, malformed, or
identity-mismatched responses reject the analysis stage without partial apply.
"""


def prepare_external_ai_job(
    job_dir: Path,
    manifest: Manifest,
    runtime_directory: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Finalize a cache-extracted job for an external file-capable AI agent."""
    job_dir = Path(job_dir).resolve()
    runtime_directory = Path(runtime_directory).resolve()
    project_root = _default_project_root() if project_root is None else Path(project_root).resolve()

    selection_path = job_dir / "selection.json"
    manifest_path = job_dir / "manifest.json"
    if not selection_path.is_file() or not manifest_path.is_file():
        raise JobLifecycleError(
            "Prepared-job handoff requires existing selection.json and manifest.json"
        )

    source_root = _single_source_root(manifest)
    skill_bundle = _build_ai_skill_bundle(project_root)

    decisions_dir = job_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    if any(decisions_dir.glob("*.json")):
        raise JobLifecycleError(
            f"Newly prepared job decision directory is not empty: {decisions_dir}"
        )

    schema_path = _atomic_write_json(
        job_dir / "decision-schema.json", SinglePassDecision.model_json_schema()
    )
    skills_path = _atomic_write_text(job_dir / "AI_SKILLS.md", skill_bundle)
    task_path = _atomic_write_text(
        job_dir / "AI_TASK.md", _task_markdown(job_dir, manifest, skills_path)
    )

    artifact_sha256 = {
        name: _sha256_file(job_dir / name) for name in _IMMUTABLE_JOB_ARTIFACTS
    }
    state = {
        "protocol_version": "1.0",
        "job_id": manifest.job_id,
        "state": JOB_STATE_PREPARED,
        "source_root": str(source_root),
        "manifest_path": str(manifest_path),
        "selection_path": str(selection_path),
        "preview_directory": str(job_dir / "previews"),
        "decision_directory": str(decisions_dir),
        "decision_schema": str(schema_path),
        "ai_task": str(task_path),
        "ai_skills": str(skills_path),
        "artifact_sha256": artifact_sha256,
        "total_selected": manifest.total_selected,
        "total_found": manifest.total_found,
        "total_missing": manifest.total_missing,
        "total_ambiguous": manifest.total_ambiguous,
        "total_failed": manifest.total_failed,
    }
    state_path = _atomic_write_json(job_dir / "job-state.json", state)

    pointer = {
        "protocol_version": "1.0",
        "job_id": manifest.job_id,
        "job_dir": str(job_dir),
        "state_path": str(state_path),
    }
    pointer_path = _atomic_write_json(
        runtime_directory / "staging" / "latest-prepared-job.json", pointer
    )
    state["latest_pointer"] = str(pointer_path)
    return state


def load_job_state(job_dir: Path) -> dict[str, Any]:
    path = Path(job_dir) / "job-state.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JobLifecycleError(f"Invalid job state at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise JobLifecycleError(f"Job state must be a JSON object: {path}")
    return raw


def _verify_immutable_job_artifacts(job_dir: Path, state: dict[str, Any]) -> None:
    expected_hashes = state.get("artifact_sha256")
    if not isinstance(expected_hashes, dict):
        raise JobLifecycleError("Prepared job state is missing artifact_sha256")

    for name in _IMMUTABLE_JOB_ARTIFACTS:
        path = job_dir / name
        if not path.is_file():
            raise JobLifecycleError(f"Prepared job artifact not found: {path}")
        expected = expected_hashes.get(name)
        if not isinstance(expected, str) or not expected:
            raise JobLifecycleError(f"Prepared job hash missing for {name}")
        actual = _sha256_file(path)
        if actual != expected:
            raise JobLifecycleError(
                f"Prepared job artifact integrity mismatch for {name}: "
                f"expected {expected}, got {actual}"
            )


def resolve_saved_job(runtime_directory: Path, job_id: str) -> tuple[Path, Manifest, Path]:
    """Resolve and verify an existing job without touching the Lightroom cache."""
    if not job_id or job_id in {".", ".."} or "/" in job_id or "\\" in job_id:
        raise JobLifecycleError(f"Invalid job_id: {job_id!r}")

    jobs_root = (Path(runtime_directory) / "jobs").resolve()
    job_dir = (jobs_root / job_id).resolve()
    try:
        job_dir.relative_to(jobs_root)
    except ValueError as exc:
        raise JobLifecycleError(f"Job path escapes runtime jobs root: {job_id}") from exc
    if not job_dir.is_dir():
        raise JobLifecycleError(f"Prepared job directory not found: {job_dir}")

    state = load_job_state(job_dir)
    if state.get("job_id") != job_id:
        raise JobLifecycleError(
            f"Saved job state identity mismatch: directory={job_id} state={state.get('job_id')}"
        )
    _verify_immutable_job_artifacts(job_dir, state)

    try:
        manifest = read_manifest(job_dir)
    except ManifestError as exc:
        raise JobLifecycleError(str(exc)) from exc
    if manifest.job_id != job_id:
        raise JobLifecycleError(
            f"Saved job identity mismatch: directory={job_id} manifest={manifest.job_id}"
        )

    decisions_dir = job_dir / "decisions"
    if not decisions_dir.is_dir():
        raise JobLifecycleError(f"Prepared decision directory not found: {decisions_dir}")
    return job_dir, manifest, job_dir / "selection.json"


def update_job_state(job_dir: Path, state: str, **updates: Any) -> dict[str, Any]:
    payload = load_job_state(job_dir)
    payload["state"] = state
    payload.update(updates)
    _atomic_write_json(Path(job_dir) / "job-state.json", payload)
    return payload


def configure_external_file_provider(
    settings: dict[str, Any], job_dir: Path
) -> dict[str, Any]:
    configured = dict(settings)
    configured["ai_provider"] = "manual_app"
    configured["manual_response_directory"] = str(Path(job_dir) / "decisions")
    configured["ai_model"] = str(
        settings.get("external_agent_name")
        or settings.get("ai_model")
        or "external-file-agent"
    )
    return configured


def eligible_apply_ids(
    decisions: Iterable[SinglePassDecision], minimum_confidence: float
) -> list[str]:
    result: list[str] = []
    for decision in decisions:
        if decision.action != Action.ADJUST:
            continue
        if decision.confidence < minimum_confidence:
            continue
        if decision.highlight_risk or decision.shadow_risk:
            continue
        if abs(decision.delta_ev) < 1e-9:
            continue
        result.append(str(decision.image_id))
    return result
