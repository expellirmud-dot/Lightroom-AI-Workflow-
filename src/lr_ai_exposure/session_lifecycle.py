from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lr_ai_exposure.ai_judge import SinglePassDecision, Action, analyze_job_single_pass
from lr_ai_exposure.analysis_result import (
    serialize_decisions,
    serialize_evidence,
    write_ai_decisions,
    write_analysis_evidence,
)
from lr_ai_exposure.apply import apply_exposure_deltas
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch
from lr_ai_exposure.convergence import evaluate_pass_convergence
from lr_ai_exposure.job import (
    Manifest,
    ManifestEntry,
    write_manifest,
    read_manifest,
)
from lr_ai_exposure.job_lifecycle import (
    JobLifecycleError,
    _atomic_write_json,
    _atomic_write_text,
    _build_ai_skill_bundle,
    _default_project_root,
    _sha256_file,
    _single_source_root,
    _IMMUTABLE_JOB_ARTIFACTS,
    configure_external_file_provider,
    eligible_apply_ids,
)
from lr_ai_exposure.render_barrier import validate_render_barrier
from lr_ai_exposure.session import (
    SessionError,
    SessionState,
    create_session,
    load_session,
    resolve_session_dir,
    write_session_state,
)


def _format_pass_id(pass_number: int) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"pass-{pass_number:04d}-{timestamp}"


def _get_pass_dir(session_dir: Path, pass_number: int, pass_id: str) -> Path:
    return session_dir / "passes" / f"{pass_number:04d}-{pass_id}"


def _task_markdown_for_pass(
    pass_dir: Path,
    manifest: Manifest,
    skills_path: Path,
    session_id: str,
    pass_number: int,
) -> str:
    found = [entry for entry in manifest.entries if entry.extraction_status == "FOUND"]
    return f"""# External AI Exposure Task — Session Pass

## Session & Pass
- Session ID: `{session_id}`
- Pass Number: `{pass_number}`
- Pass ID: `{manifest.pass_id}`
- Parent Pass ID: `{manifest.parent_pass_id or 'none (initial pass)'}`
- Manifest: `{pass_dir / 'manifest.json'}`
- Preview directory: `{pass_dir / 'previews'}`
- Decision directory: `{pass_dir / 'decisions'}`
- Decision schema: `{pass_dir / 'decision-schema.json'}`
- Bundled visual skills: `{skills_path}`
- FOUND previews requiring decisions: **{len(found)}**

## Required operating model
1. Read `AI_SKILLS.md` completely before judging any image.
2. Read `manifest.json` in manifest order.
3. Inspect every preview whose `extraction_status` is `FOUND`.
4. Group materially similar images by `scene_group_id` and pick consistent `is_reference` frames.
5. Return grounded `action` (`PASS`, `ADJUST`, or `REVIEW`) per image.
6. Write exactly one UTF-8 JSON file per FOUND image to `decisions/<image_id>.json`.

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
"""


def prepare_session_pass(
    runtime_directory: Path | str,
    lrdata_dir: Path | str,
    selection_json_path: Path | str,
    session_id: str | None = None,
    pass_number: int = 1,
    parent_pass_id: str | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    runtime_path = Path(runtime_directory).resolve()
    lrdata_path = Path(lrdata_dir).resolve()
    selection_path = Path(selection_json_path).resolve()
    if project_root is None or not (Path(project_root) / ".agents" / "skills").is_dir():
        project_root = _default_project_root()
    else:
        project_root = Path(project_root).resolve()

    if not selection_path.is_file():
        raise SessionError(f"Selection file not found: {selection_path}")
    if not lrdata_path.is_dir():
        raise SessionError(f"Preview cache directory not found: {lrdata_path}")

    with open(selection_path, "r", encoding="utf-8") as f:
        selection_data = json.load(f)

    photos = selection_data.get("photos", [])
    if not photos:
        raise SessionError("Selection must contain at least one photo")

    source_folder = selection_data.get("source_folder", "")
    if not source_folder:
        source_folder = str(Path(photos[0]["path"]).parent)

    # Initialize or load session
    if pass_number == 1 or session_id is None:
        actual_session_id = session_id or f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        session_dir = runtime_path / "sessions" / actual_session_id
        session_state = create_session(session_dir, actual_session_id, source_folder, photos)
        # Copy frozen selection.json to session root
        _atomic_write_json(session_dir / "selection.json", selection_data)
    else:
        actual_session_id = session_id
        session_dir = resolve_session_dir(runtime_path, actual_session_id)
        session_state = load_session(session_dir)

    pass_id = _format_pass_id(pass_number)
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    pass_dir.mkdir(parents=True, exist_ok=True)
    (pass_dir / "decisions").mkdir(parents=True, exist_ok=True)
    (session_dir / "xmp_backups").mkdir(parents=True, exist_ok=True)

    # Determine in-scope photos for this pass
    if pass_number == 1:
        in_scope_photos = photos
    else:
        # Include photos that were marked ADJUST in previous pass + stable group references
        adjust_ids = {img_id for img_id, img in session_state.images.items() if img.status == "ADJUST"}
        ref_ids = {img_id for img_id, img in session_state.images.items() if img.is_reference and img.status == "PASS"}
        target_ids = adjust_ids | ref_ids
        in_scope_photos = [p for p in photos if str(p.get("id_local")) in target_ids]
        if not in_scope_photos:
            in_scope_photos = photos

    # Copy pass selection
    pass_selection_payload = dict(selection_data)
    pass_selection_payload["job_id"] = actual_session_id
    pass_selection_payload["pass_id"] = pass_id
    pass_selection_payload["pass_number"] = pass_number
    pass_selection_payload["photos"] = in_scope_photos
    _atomic_write_json(pass_dir / "selection.json", pass_selection_payload)

    # Snapshot cache into pass dir
    snapshot_dir = pass_dir / "cache_snapshots"
    snapshot_cache_dbs(str(lrdata_path), str(snapshot_dir))

    # Extract previews
    previews_out_dir = pass_dir / "previews"
    extract_results = extract_batch(in_scope_photos, str(snapshot_dir), str(previews_out_dir))

    # Build manifest entries
    entries: list[ManifestEntry] = []
    total_found = 0
    total_missing = 0
    total_ambiguous = 0
    total_failed = 0

    for i, res in enumerate(extract_results):
        src_path = in_scope_photos[i].get("path", "")
        stem = Path(src_path).stem
        raw_path_canon = str(Path(src_path).resolve())
        source_xmp_path = str(Path(src_path).with_suffix(".xmp").resolve())
        backup_rel = f"xmp_backups/{stem}.xmp"
        preview_rel = f"previews/{i+1:06d}__{stem}.jpg"

        status = res["status"]
        preview_bytes = 0
        preview_sha256 = None

        if status == "FOUND" and res.get("output") and os.path.exists(res.get("output", "")):
            out_path = res["output"]
            preview_bytes = os.path.getsize(out_path)
            with open(out_path, "rb") as f:
                preview_sha256 = hashlib.sha256(f.read()).hexdigest()
            total_found += 1
        elif status == "MISSING":
            total_missing += 1
        elif status == "AMBIGUOUS":
            total_ambiguous += 1
        else:
            total_failed += 1

        entries.append(
            ManifestEntry(
                image_id=str(in_scope_photos[i].get("id_local", "")),
                raw_path=raw_path_canon,
                source_xmp_path=source_xmp_path,
                backup_relative_path=backup_rel,
                preview_path=preview_rel,
                seq=i + 1,
                extraction_status=status,
                uuid=res.get("uuid"),
                preview_bytes=preview_bytes,
                preview_sha256=preview_sha256,
            )
        )

    manifest = Manifest(
        job_id=actual_session_id,
        pass_number=pass_number,
        pass_id=pass_id,
        parent_pass_id=parent_pass_id,
        entries=entries,
        total_selected=len(in_scope_photos),
        total_found=total_found,
        total_missing=total_missing,
        total_ambiguous=total_ambiguous,
        total_failed=total_failed,
    )
    manifest_path = write_manifest(pass_dir, manifest)

    # If pass > 1, validate render barrier freshness
    render_barrier_results = {}
    if pass_number > 1:
        render_barrier_results = validate_render_barrier(session_state, manifest)

    # Bundle skills and write task
    skill_bundle = _build_ai_skill_bundle(project_root)
    skills_path = _atomic_write_text(pass_dir / "AI_SKILLS.md", skill_bundle)
    schema_path = _atomic_write_json(
        pass_dir / "decision-schema.json", SinglePassDecision.model_json_schema()
    )
    task_path = _atomic_write_text(
        pass_dir / "AI_TASK.md",
        _task_markdown_for_pass(pass_dir, manifest, skills_path, actual_session_id, pass_number),
    )

    artifact_sha256 = {
        name: _sha256_file(pass_dir / name) for name in _IMMUTABLE_JOB_ARTIFACTS
    }

    pass_state = {
        "protocol_version": "1.0",
        "session_id": actual_session_id,
        "pass_id": pass_id,
        "pass_number": pass_number,
        "parent_pass_id": parent_pass_id,
        "source_root": str(source_folder),
        "manifest_path": str(manifest_path),
        "preview_directory": str(previews_out_dir),
        "decision_directory": str(pass_dir / "decisions"),
        "decision_schema": str(schema_path),
        "ai_task": str(task_path),
        "ai_skills": str(skills_path),
        "artifact_sha256": artifact_sha256,
        "total_selected": manifest.total_selected,
        "total_found": manifest.total_found,
        "render_barrier": render_barrier_results,
    }
    pass_state_path = _atomic_write_json(pass_dir / "pass-state.json", pass_state)

    session_state.passes.append(pass_id)
    write_session_state(session_dir, session_state)

    # Write latest session pointer
    pointer = {
        "protocol_version": "1.0",
        "session_id": actual_session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "session_dir": str(session_dir),
        "pass_dir": str(pass_dir),
    }
    _atomic_write_json(runtime_path / "staging" / "latest-session.json", pointer)

    return {
        "session_id": actual_session_id,
        "pass_id": pass_id,
        "pass_number": pass_number,
        "session_dir": str(session_dir),
        "pass_dir": str(pass_dir),
        "manifest_path": str(manifest_path),
        "preview_directory": str(previews_out_dir),
        "decision_directory": str(pass_dir / "decisions"),
        "decision_schema": str(schema_path),
        "ai_task": str(task_path),
        "total_selected": manifest.total_selected,
        "total_found": manifest.total_found,
        "render_barrier": render_barrier_results,
    }


def analyze_session_pass(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
    settings: dict[str, Any],
) -> dict[str, Any]:
    runtime_path = Path(runtime_directory).resolve()
    session_dir = resolve_session_dir(runtime_path, session_id)
    session_state = load_session(session_dir)

    if pass_number > len(session_state.passes):
        raise SessionError(f"Pass number {pass_number} not found in session {session_id}")

    pass_id = session_state.passes[pass_number - 1]
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    manifest = read_manifest(pass_dir)

    configured_settings = configure_external_file_provider(settings, pass_dir)
    decisions = analyze_job_single_pass(manifest, pass_dir, configured_settings)

    mode = f"SESSION_PASS_{pass_number}"
    dp = write_ai_decisions(
        pass_dir,
        serialize_decisions(
            job_id=actual_job_id if (actual_job_id := getattr(manifest, "job_id", session_id)) else session_id,
            decisions=decisions,
            provider=configured_settings.get("ai_provider", "unknown"),
            model=configured_settings.get("ai_model", "unknown"),
            mode=mode,
            apply_authorized=False,
            xmp_mutation=False,
        ),
    )
    ep = write_analysis_evidence(
        pass_dir,
        serialize_evidence(
            job_id=session_id,
            decisions=decisions,
            provider=configured_settings.get("ai_provider", "unknown"),
            model=configured_settings.get("ai_model", "unknown"),
            settings=configured_settings,
            mode=mode,
        ),
    )

    return {
        "session_id": session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "decision_count": len(decisions),
        "ai_decisions": str(dp),
        "analysis_evidence": str(ep),
    }


def apply_session_pass(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
    authorize_apply: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    if authorize_apply != session_id:
        raise SessionError("authorize_apply must exactly equal the session_id")

    runtime_path = Path(runtime_directory).resolve()
    session_dir = resolve_session_dir(runtime_path, session_id)
    session_state = load_session(session_dir)

    if pass_number > len(session_state.passes):
        raise SessionError(f"Pass number {pass_number} not found in session {session_id}")

    pass_id = session_state.passes[pass_number - 1]
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    manifest = read_manifest(pass_dir)

    configured_settings = configure_external_file_provider(settings, pass_dir)
    decisions = analyze_job_single_pass(manifest, pass_dir, configured_settings)

    # Evaluate convergence & bounds & oscillation
    convergence_summary = evaluate_pass_convergence(session_state, decisions, pass_id)

    # Approved IDs for apply are those marked ADJUST
    approved_ids = [
        str(d.image_id)
        for d in decisions
        if convergence_summary["results"].get(str(d.image_id)) == "ADJUST"
    ]

    apply_config = dict(configured_settings)
    apply_config.update(
        {
            "dry_run": False,
            "apply_authorized": True,
            "approved_image_ids": approved_ids,
            "approved_pilot_root": session_state.source_folder,
        }
    )

    selection_path = pass_dir / "selection.json"
    apply_results = apply_exposure_deltas(pass_dir, selection_path, decisions, apply_config)

    # Update session state with applied hash and values
    applied_image_ids: list[str] = []
    evidence_file = pass_dir / "apply-evidence.json"
    if evidence_file.exists():
        evidence_data = json.loads(evidence_file.read_text(encoding="utf-8"))
        for item in evidence_data.get("results", []):
            if item.get("status") == "APPLIED_VERIFIED":
                applied_image_ids.append(str(item["image_id"]))

    write_session_state(session_dir, session_state)

    # Write groups ledger snapshot
    groups_payload = {
        "session_id": session_id,
        "pass_number": pass_number,
        "groups": {
            img.scene_group_id: [
                i_id for i_id, i in session_state.images.items() if i.scene_group_id == img.scene_group_id
            ]
            for img in session_state.images.values()
        },
    }
    _atomic_write_json(session_dir / "groups.json", groups_payload)

    next_pass = None if session_state.is_converged else pass_number + 1

    return {
        "session_id": session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "applied_count": len(applied_image_ids),
        "pass_count": convergence_summary["pass"],
        "review_count": convergence_summary["review"],
        "is_converged": session_state.is_converged,
        "applied_image_ids": applied_image_ids,
        "next_pass_number": next_pass,
        "apply_evidence": str(evidence_file),
    }
