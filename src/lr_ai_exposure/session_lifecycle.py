from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lr_ai_exposure.ai_judge import SinglePassDecision, analyze_job_single_pass
from lr_ai_exposure.analysis_result import (
    serialize_decisions,
    serialize_evidence,
    write_ai_decisions,
    write_analysis_evidence,
)
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch
from lr_ai_exposure.convergence import evaluate_pass_convergence
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest, read_manifest
from lr_ai_exposure.job_lifecycle import (
    _atomic_write_json,
    _atomic_write_text,
    _build_ai_skill_bundle,
    _default_project_root,
    _sha256_file,
    _IMMUTABLE_JOB_ARTIFACTS,
    configure_external_file_provider,
)
from lr_ai_exposure.render_barrier import validate_render_barrier
from lr_ai_exposure.session import (
    SessionError,
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
1. Read `AI_SKILLS.md` before judging images.
2. Read `manifest.json` in manifest order.
3. Inspect every FOUND preview in scope for this pass.
4. Return grounded `action` (`PASS`, `ADJUST`, or `REVIEW`) per image.
5. Write exactly one UTF-8 JSON file per FOUND image to `decisions/<image_id>.json`.
6. Scene/group fields are contextual hints only; they do not authorize mutation.

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
  "scene_rationale": "grounded context and exposure observation",
  "scene_group_id": "context label",
  "is_reference": false,
  "reason": "concise final rationale"
}}
```
"""


def _catalog_exposure_map(photos: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in photos:
        image_id = str(item.get("id_local", ""))
        raw = item.get("catalog_exposure2012")
        if not image_id or isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        values[image_id] = float(raw)
    return values


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

    selection_data = json.loads(selection_path.read_text(encoding="utf-8"))
    photos = selection_data.get("photos", [])
    if not isinstance(photos, list) or not photos:
        raise SessionError("Selection must contain at least one photo")

    source_folder = selection_data.get("source_folder", "") or str(Path(photos[0]["path"]).parent)

    if pass_number == 1 or session_id is None:
        actual_session_id = session_id or f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        session_dir = runtime_path / "sessions" / actual_session_id
        session_state = create_session(session_dir, actual_session_id, source_folder, photos)
        _atomic_write_json(session_dir / "selection.json", selection_data)
    else:
        actual_session_id = session_id
        session_dir = resolve_session_dir(runtime_path, actual_session_id)
        session_state = load_session(session_dir)

    pass_id = _format_pass_id(pass_number)
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    pass_dir.mkdir(parents=True, exist_ok=True)
    (pass_dir / "decisions").mkdir(parents=True, exist_ok=True)

    if pass_number == 1:
        in_scope_photos = photos
    else:
        adjust_ids = {image_id for image_id, img in session_state.images.items() if img.status == "ADJUST"}
        ref_ids = {
            image_id
            for image_id, img in session_state.images.items()
            if img.is_reference and img.status == "PASS"
        }
        target_ids = adjust_ids | ref_ids
        in_scope_photos = [p for p in photos if str(p.get("id_local")) in target_ids]
        if not in_scope_photos and not session_state.is_converged:
            in_scope_photos = photos

    pass_selection_payload = dict(selection_data)
    pass_selection_payload["job_id"] = actual_session_id
    pass_selection_payload["pass_id"] = pass_id
    pass_selection_payload["pass_number"] = pass_number
    pass_selection_payload["photos"] = in_scope_photos
    _atomic_write_json(pass_dir / "selection.json", pass_selection_payload)

    snapshot_dir = pass_dir / "cache_snapshots"
    snapshot_cache_dbs(str(lrdata_path), str(snapshot_dir))

    previews_out_dir = pass_dir / "previews"
    extract_results = extract_batch(in_scope_photos, str(snapshot_dir), str(previews_out_dir))

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
        preview_rel = f"previews/{i + 1:06d}__{stem}.jpg"

        status = res["status"]
        preview_bytes = 0
        preview_sha256 = None
        if status == "FOUND" and res.get("output") and os.path.exists(res.get("output", "")):
            out_path = res["output"]
            preview_bytes = os.path.getsize(out_path)
            preview_sha256 = hashlib.sha256(Path(out_path).read_bytes()).hexdigest()
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
                backup_relative_path=f"xmp_backups/{stem}.xmp",
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

    render_barrier_results: dict[str, str] = {}
    if pass_number > 1:
        render_barrier_results = validate_render_barrier(
            session_state,
            manifest,
            _catalog_exposure_map(in_scope_photos),
            tolerance=float(session_state.policy.get("catalog_exposure_tolerance", 0.01)),
        )
        write_session_state(session_dir, session_state)

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
        name: _sha256_file(pass_dir / name)
        for name in _IMMUTABLE_JOB_ARTIFACTS
        if (pass_dir / name).is_file()
    }
    pass_state = {
        "protocol_version": "1.1",
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
        "mutation_mode": "LIGHTROOM_CATALOG_EXPOSURE2012",
    }
    _atomic_write_json(pass_dir / "pass-state.json", pass_state)

    session_state.passes.append(pass_id)
    write_session_state(session_dir, session_state)

    pointer = {
        "protocol_version": "1.1",
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
            job_id=manifest.job_id,
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
            extra_markers=["ITERATIVE_DECISIONS_FROZEN_FOR_APPLY"],
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


def _load_frozen_decisions(pass_dir: Path, manifest: Manifest) -> list[SinglePassDecision]:
    path = pass_dir / "ai-decisions.json"
    if not path.is_file():
        raise SessionError(
            "Frozen ai-decisions.json is missing. Run analyze-session-pass before apply planning."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"Frozen AI decision artifact is unreadable: {exc}") from exc

    if payload.get("job_id") != manifest.job_id:
        raise SessionError("Frozen AI decision job_id does not match manifest")
    raw_decisions = payload.get("decisions")
    if not isinstance(raw_decisions, list):
        raise SessionError("Frozen AI decision artifact has no decisions list")

    try:
        decisions = [
            SinglePassDecision.model_validate_json(json.dumps(item))
            for item in raw_decisions
        ]
    except Exception as exc:
        raise SessionError(f"Frozen AI decision schema validation failed: {exc}") from exc

    expected_ids = [str(e.image_id) for e in manifest.entries if e.extraction_status == "FOUND"]
    actual_ids = [str(d.image_id) for d in decisions]
    if len(actual_ids) != len(set(actual_ids)):
        raise SessionError("Frozen AI decision artifact contains duplicate image IDs")
    if set(actual_ids) != set(expected_ids):
        raise SessionError(
            "Frozen AI decision image set does not exactly match FOUND manifest images"
        )
    return decisions


def apply_session_pass(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
    authorize_apply: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Plan an iterative Catalog apply without mutating Lightroom or session state."""
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
    decisions = _load_frozen_decisions(pass_dir, manifest)

    proposed_state = copy.deepcopy(session_state)
    convergence_summary = evaluate_pass_convergence(proposed_state, decisions, pass_id)
    by_id = {str(d.image_id): d for d in decisions}

    items: list[dict[str, Any]] = []
    for image_id, result in convergence_summary["results"].items():
        if result != "ADJUST":
            continue
        before_img = session_state.images[image_id]
        after_img = proposed_state.images[image_id]
        expected_before = (
            before_img.expected_exposure2012
            if before_img.expected_exposure2012 is not None
            else before_img.baseline_exposure2012
        )
        target = after_img.expected_exposure2012
        if target is None:
            raise SessionError(f"Planned image {image_id} has no target Exposure2012")
        items.append(
            {
                "image_id": image_id,
                "expected_before_exposure2012": round(float(expected_before), 4),
                "target_exposure2012": round(float(target), 4),
                "delta_ev": convergence_summary["quantized_deltas"][image_id],
                "decision_action": by_id[image_id].action.value,
            }
        )

    plan = {
        "protocol_version": "1.1",
        "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY",
        "session_id": session_id,
        "pass_id": pass_id,
        "pass_number": pass_number,
        "catalog_exposure_tolerance": float(
            session_state.policy.get("catalog_exposure_tolerance", 0.01)
        ),
        "planned_count": len(items),
        "items": items,
        "decision_results": convergence_summary["results"],
    }
    plan_path = _atomic_write_json(pass_dir / "catalog-apply-plan.json", plan)
    planned_ids = [str(item["image_id"]) for item in items]
    next_pass = None if proposed_state.is_converged else pass_number + 1

    # Canonical main.py historically labels these fields as applied/apply_evidence.
    # In the iterative Catalog route they deliberately mean "planned" until
    # Lightroom verifies the mutation and catalog_confirm commits session state.
    return {
        "session_id": session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "planned_count": len(items),
        "catalog_apply_plan": str(plan_path),
        "requires_catalog_apply": bool(items),
        "applied_count": len(items),
        "applied_image_ids": planned_ids,
        "apply_evidence": str(plan_path),
        "pass_count": convergence_summary["pass"],
        "review_count": convergence_summary["review"],
        "is_converged": proposed_state.is_converged,
        "next_pass_number": next_pass,
    }


def confirm_session_apply(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
    apply_result_path: Path | str,
) -> dict[str, Any]:
    """Commit iterative session state only from Lightroom-verified Catalog results."""
    runtime_path = Path(runtime_directory).resolve()
    session_dir = resolve_session_dir(runtime_path, session_id)
    session_state = load_session(session_dir)
    if pass_number > len(session_state.passes):
        raise SessionError(f"Pass number {pass_number} not found in session {session_id}")

    pass_id = session_state.passes[pass_number - 1]
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    manifest = read_manifest(pass_dir)
    decisions = _load_frozen_decisions(pass_dir, manifest)

    plan_path = pass_dir / "catalog-apply-plan.json"
    if not plan_path.is_file():
        raise SessionError("catalog-apply-plan.json is missing")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("session_id") != session_id or plan.get("pass_id") != pass_id:
        raise SessionError("Catalog apply plan lineage mismatch")

    result_path = Path(apply_result_path).resolve()
    if not result_path.is_file():
        raise SessionError(f"Catalog apply result not found: {result_path}")
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    if result_payload.get("session_id") != session_id or result_payload.get("pass_id") != pass_id:
        raise SessionError("Catalog apply result lineage mismatch")

    planned_items = {str(item["image_id"]): item for item in plan.get("items", [])}
    result_items = result_payload.get("results", [])
    if not isinstance(result_items, list):
        raise SessionError("Catalog apply result must contain a results list")
    result_map: dict[str, dict[str, Any]] = {}
    for item in result_items:
        image_id = str(item.get("image_id", ""))
        if not image_id or image_id in result_map:
            raise SessionError("Catalog apply result has missing or duplicate image IDs")
        result_map[image_id] = item
    if set(result_map) != set(planned_items):
        raise SessionError("Catalog apply result image set does not exactly match apply plan")

    original_state = copy.deepcopy(session_state)
    convergence_summary = evaluate_pass_convergence(session_state, decisions, pass_id)
    tolerance = float(session_state.policy.get("catalog_exposure_tolerance", 0.01))
    manifest_by_id = {str(entry.image_id): entry for entry in manifest.entries}
    applied_image_ids: list[str] = []
    failed_image_ids: list[str] = []

    for image_id, planned in planned_items.items():
        item = result_map[image_id]
        planned_target = float(planned["target_exposure2012"])
        computed_target = session_state.images[image_id].expected_exposure2012
        if computed_target is None or abs(computed_target - planned_target) > tolerance:
            raise SessionError(f"Catalog plan target drift detected for image {image_id}")

        observed_after = item.get("observed_after_exposure2012")
        verified = (
            item.get("status") == "APPLIED_VERIFIED"
            and isinstance(observed_after, (int, float))
            and not isinstance(observed_after, bool)
            and abs(float(observed_after) - planned_target) <= tolerance
        )
        if verified:
            entry = manifest_by_id.get(image_id)
            if entry and entry.preview_sha256:
                session_state.images[image_id].last_preview_sha256 = entry.preview_sha256
            applied_image_ids.append(image_id)
        else:
            session_state.images[image_id] = copy.deepcopy(original_state.images[image_id])
            session_state.images[image_id].status = "REVIEW"
            failed_image_ids.append(image_id)
            convergence_summary["results"][image_id] = "REVIEW_CATALOG_APPLY_UNVERIFIED"

    session_state.is_converged = all(
        img.status in {"PASS", "REVIEW"} for img in session_state.images.values()
    )
    write_session_state(session_dir, session_state)

    evidence_payload = {
        "protocol_version": "1.1",
        "session_id": session_id,
        "pass_id": pass_id,
        "pass_number": pass_number,
        "mutation_mode": "LIGHTROOM_CATALOG_EXPOSURE2012",
        "plan": plan,
        "lightroom_result": result_payload,
        "applied_image_ids": applied_image_ids,
        "failed_image_ids": failed_image_ids,
        "decision_results": convergence_summary["results"],
    }
    evidence_path = _atomic_write_json(pass_dir / "catalog-apply-evidence.json", evidence_payload)

    groups_payload = {
        "session_id": session_id,
        "pass_number": pass_number,
        "groups": {
            img.scene_group_id: [
                image_id
                for image_id, other in session_state.images.items()
                if other.scene_group_id == img.scene_group_id
            ]
            for img in session_state.images.values()
        },
    }
    _atomic_write_json(session_dir / "groups.json", groups_payload)

    pass_count = sum(1 for img in session_state.images.values() if img.status == "PASS")
    review_count = sum(1 for img in session_state.images.values() if img.status == "REVIEW")
    next_pass = None if session_state.is_converged else pass_number + 1
    return {
        "session_id": session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "applied_count": len(applied_image_ids),
        "pass_count": pass_count,
        "review_count": review_count,
        "is_converged": session_state.is_converged,
        "applied_image_ids": applied_image_ids,
        "failed_image_ids": failed_image_ids,
        "next_pass_number": next_pass,
        "apply_evidence": str(evidence_path),
    }
