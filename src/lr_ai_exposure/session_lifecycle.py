from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lr_ai_exposure.ai_judge import (
    SinglePassDecision,
    analyze_job_single_pass,
    validate_scene_decision_set,
)
from lr_ai_exposure.analysis_result import (
    serialize_decisions,
    serialize_evidence,
    write_ai_decisions,
    write_analysis_evidence,
)
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch
from lr_ai_exposure.contact_sheets import (
    CONTACT_SHEET_INDEX_NAME,
    ContactSheetError,
    build_contact_sheets,
    validate_contact_sheet_package,
    validate_extracted_previews,
)
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


def _session_decision_schema() -> dict[str, Any]:
    """Return the canonical session schema with explicit scene outcome fields required."""
    schema = SinglePassDecision.model_json_schema()
    required = list(schema.get("required", []))
    for field_name in ("scene_group_id", "scene_exposure_verdict", "scene_delta_ev", "is_reference"):
        if field_name not in required:
            required.append(field_name)
        prop = schema.get("properties", {}).get(field_name)
        if isinstance(prop, dict):
            prop.pop("default", None)
    schema["required"] = required
    return schema


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
- Contact-sheet directory: `{pass_dir / 'contact_sheets'}`
- Contact-sheet index: `{pass_dir / CONTACT_SHEET_INDEX_NAME}`
- Decision directory: `{pass_dir / 'decisions'}`
- Decision schema: `{pass_dir / 'decision-schema.json'}`
- Bundled visual skills: `{skills_path}`
- FOUND previews requiring evaluation: **{len(found)}**

## Outcome contract

The goal is a photographically appropriate Exposure2012 result across the whole job, with materially similar images in the same lighting/intent scene remaining visually coherent. You may choose your own efficient visual reasoning method; the package does not prescribe a step-by-step thought process.

The following outcomes are mandatory:

- **Evaluate every FOUND image.** Coverage means every image was genuinely judged; it does **not** mean every image must change.
- **PASS is successful no-change.** Use `PASS` with `delta_ev: 0.0` when the image is already appropriately exposed and consistent with its scene. Never adjust merely to demonstrate coverage.
- **State the absolute scene conclusion.** Every decision must include `scene_exposure_verdict` (`TOO_DARK`, `BALANCED`, `TOO_BRIGHT`, or `REVIEW`) and `scene_delta_ev`, an approximate shared correction signal for that scene. All members assigned to one `scene_group_id` must agree on those two scene-level values.
- **Consistency alone is not enough.** A scene where every image is similarly too bright or too dark is not BALANCED merely because the images match each other.
- **Do not ignore outliers.** Before completing the pass, ensure there is no unexplained exposure outlier inside a materially similar scene. Legitimate lighting/composition differences may be separated into different scene groups.
- **Per-image freedom remains.** `delta_ev` is the image-specific proposal. It may differ from `scene_delta_ev`, and a genuinely correct image may remain PASS even when nearby images need adjustment.
- **Exposure only.** Do not judge blur, focus, sharpness, damaged frames, duplicates, relevance, or keep/cull quality from these previews. Set `relevance_verdict` and `quality_verdict` to `KEEP`; use `action: REVIEW` only for unresolved exposure evidence.
- External AI has decision authority only. It must not modify Lightroom, Catalog/cache data, originals, manifest, task, skills, schema, or session state.

Inspect the prepared contact sheets for batch/scene context and open individual FOUND previews whenever useful. The required result is the outcome above, not a prescribed inspection sequence.

## Required JSON fields
```json
{{
  "image_id": "<manifest image_id>",
  "action": "PASS | ADJUST | REVIEW",
  "relevance_verdict": "KEEP",
  "quality_verdict": "KEEP",
  "delta_ev": 0.0,
  "confidence": 0.0,
  "highlight_risk": false,
  "shadow_risk": false,
  "subject_rationale": "grounded subject observation",
  "scene_rationale": "grounded scene/exposure observation",
  "scene_group_id": "stable context label",
  "scene_exposure_verdict": "TOO_DARK | BALANCED | TOO_BRIGHT | REVIEW",
  "scene_delta_ev": 0.0,
  "is_reference": false,
  "reason": "concise final rationale"
}}
```

Scene signal rules: `TOO_DARK` uses positive `scene_delta_ev`; `TOO_BRIGHT` uses negative `scene_delta_ev`; `BALANCED` and `REVIEW` use `0.0`. `scene_delta_ev` is context/evidence, not mutation authority. Only per-image `action: ADJUST` + validated `delta_ev` can enter Catalog planning.
"""


def _normalize_path(value: str) -> str:
    return os.path.normcase(os.path.abspath(value))


def _validate_frozen_session_scope(
    session_state: Any,
    photos: list[dict[str, Any]],
    source_folder: str,
) -> None:
    """Fail closed if a later Lightroom capture no longer matches the frozen session set."""
    if _normalize_path(str(source_folder)) != _normalize_path(session_state.source_folder):
        raise SessionError(
            "SESSION_SCOPE_CHANGED: active source folder differs from the frozen session. "
            "Start a new session for the changed folder scope."
        )

    current: dict[str, dict[str, Any]] = {}
    for photo in photos:
        image_id = str(photo.get("id_local", ""))
        if not image_id or image_id in current:
            raise SessionError("SESSION_SCOPE_CHANGED: current Lightroom image identities are missing or duplicated")
        current[image_id] = photo

    expected_ids = set(session_state.images)
    current_ids = set(current)
    if current_ids != expected_ids:
        added = sorted(current_ids - expected_ids)
        removed = sorted(expected_ids - current_ids)
        raise SessionError(
            "SESSION_SCOPE_CHANGED: Lightroom image set no longer matches the frozen session "
            f"(added={len(added)}, removed={len(removed)}). Start a new session."
        )

    for image_id in sorted(expected_ids):
        frozen = session_state.images[image_id]
        photo = current[image_id]
        current_path = str(photo.get("path", ""))
        if not current_path or _normalize_path(current_path) != _normalize_path(frozen.raw_path):
            raise SessionError(
                f"SESSION_SCOPE_CHANGED: image {image_id} path differs from the frozen session. Start a new session."
            )
        current_uuid = str(photo.get("uuid", "") or "")
        if frozen.uuid and current_uuid and current_uuid != frozen.uuid:
            raise SessionError(
                f"SESSION_SCOPE_CHANGED: image {image_id} UUID differs from the frozen session. Start a new session."
            )


def _validate_next_pass_lineage(
    session_state: Any,
    pass_number: int,
    parent_pass_id: str | None,
) -> None:
    expected_pass = len(session_state.passes) + 1
    if pass_number != expected_pass:
        raise SessionError(
            f"Pass number {pass_number} is invalid for current lineage; expected {expected_pass}"
        )
    expected_parent = session_state.passes[-1] if session_state.passes else None
    if parent_pass_id != expected_parent:
        raise SessionError(
            f"Parent pass mismatch: expected {expected_parent!r}, found {parent_pass_id!r}"
        )


def _catalog_exposure_map(photos: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in photos:
        image_id = str(item.get("id_local", ""))
        raw = item.get("catalog_exposure2012")
        if not image_id or isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        values[image_id] = float(raw)
    return values


def _validate_immutable_pass_package(pass_dir: Path, manifest: Manifest) -> None:
    """Refuse external decisions when a captured package artifact was changed."""
    state_path = pass_dir / "pass-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"Prepared pass state is unreadable: {exc}") from exc
    expected_hashes = state.get("artifact_sha256")
    if not isinstance(expected_hashes, dict):
        raise SessionError("Prepared pass state is missing artifact_sha256")
    for name in _IMMUTABLE_JOB_ARTIFACTS:
        path = pass_dir / name
        expected = expected_hashes.get(name)
        if not path.is_file() or not isinstance(expected, str) or _sha256_file(path) != expected:
            raise SessionError(f"Prepared pass immutable artifact mismatch: {name}")
    index_path = pass_dir / CONTACT_SHEET_INDEX_NAME
    expected_index_hash = state.get("contact_sheet_index_sha256")
    if (
        not index_path.is_file()
        or not isinstance(expected_index_hash, str)
        or _sha256_file(index_path) != expected_index_hash
    ):
        raise SessionError("Prepared pass immutable artifact mismatch: contact-sheet-index.json")
    if (pass_dir / "cache_snapshots").exists():
        raise SessionError("Prepared pass still contains temporary cache snapshots")
    try:
        validate_contact_sheet_package(pass_dir, manifest)
    except ContactSheetError as exc:
        raise SessionError(f"Contact-sheet package validation failed: {exc}") from exc


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
        _validate_next_pass_lineage(session_state, pass_number, parent_pass_id)
        _validate_frozen_session_scope(session_state, photos, source_folder)

    pass_id = _format_pass_id(pass_number)
    pass_dir = _get_pass_dir(session_dir, pass_number, pass_id)
    pass_dir.mkdir(parents=True, exist_ok=True)
    (pass_dir / "decisions").mkdir(parents=True, exist_ok=True)

    # Later passes re-audit the complete frozen session image set.
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
                preview_orientation=res.get("orientation"),
                source_preview_sha256=res.get("source_preview_sha256"),
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
    try:
        validated_previews = validate_extracted_previews(pass_dir, manifest)
        contact_sheet_index_path = build_contact_sheets(pass_dir, validated_previews)
    except ContactSheetError as exc:
        raise SessionError(f"Contact-sheet preparation failed: {exc}") from exc

    manifest_path = write_manifest(pass_dir, manifest)

    render_barrier_results: dict[str, str] = {}
    if pass_number > 1:
        render_barrier_results = validate_render_barrier(
            session_state,
            manifest,
            _catalog_exposure_map(in_scope_photos),
            tolerance=float(session_state.policy.get("catalog_exposure_tolerance", 0.01)),
        )
        waiting_ids = sorted(
            image_id
            for image_id, result in render_barrier_results.items()
            if result.startswith("WAITING_FOR_RERENDER")
        )
        blocked = {
            image_id: result
            for image_id, result in render_barrier_results.items()
            if result.startswith("BLOCKED_RENDER")
        }
        if waiting_ids or blocked:
            # This pass has not crossed the admission barrier and is not durable lineage.
            shutil.rmtree(pass_dir, ignore_errors=True)
            if waiting_ids and not blocked:
                examples = ", ".join(waiting_ids[:8])
                raise SessionError(
                    "WAITING_FOR_RERENDER: Lightroom previews are not fresh for "
                    f"{len(waiting_ids)} adjusted image(s). Example IDs: {examples}. "
                    "No image was converted to REVIEW and no new pass was admitted; wait for Lightroom and retry."
                )
            examples = ", ".join(f"{k}={v}" for k, v in list(sorted(blocked.items()))[:8])
            raise SessionError(
                "RENDER_BARRIER_BLOCKED: render freshness cannot be proven. "
                f"{examples}. No new pass was admitted."
            )

    skill_bundle = _build_ai_skill_bundle(project_root)
    skills_path = _atomic_write_text(pass_dir / "AI_SKILLS.md", skill_bundle)
    schema_path = _atomic_write_json(
        pass_dir / "decision-schema.json", _session_decision_schema()
    )
    task_path = _atomic_write_text(
        pass_dir / "AI_TASK.md",
        _task_markdown_for_pass(pass_dir, manifest, skills_path, actual_session_id, pass_number),
    )

    try:
        contact_sheet_index = validate_contact_sheet_package(pass_dir, manifest)
    except ContactSheetError as exc:
        raise SessionError(f"Contact-sheet package validation failed: {exc}") from exc

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
        "contact_sheet_directory": str(pass_dir / "contact_sheets"),
        "contact_sheet_index": str(contact_sheet_index_path),
        "contact_sheet_count": len(contact_sheet_index["sheets"]),
        "contact_sheet_index_sha256": _sha256_file(contact_sheet_index_path),
        "artifact_sha256": artifact_sha256,
        "total_selected": manifest.total_selected,
        "total_found": manifest.total_found,
        "render_barrier": render_barrier_results,
        "mutation_mode": "LIGHTROOM_CATALOG_EXPOSURE2012",
    }
    _atomic_write_json(pass_dir / "pass-state.json", pass_state)

    shutil.rmtree(snapshot_dir)

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
        "contact_sheet_directory": str(pass_dir / "contact_sheets"),
        "contact_sheet_index": str(contact_sheet_index_path),
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
    _validate_immutable_pass_package(pass_dir, manifest)

    configured_settings = configure_external_file_provider(settings, pass_dir)
    decisions = analyze_job_single_pass(manifest, pass_dir, configured_settings)
    validate_scene_decision_set(decisions, require_explicit_scene_fields=True)

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
        "requires_rerender": bool(items),
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
                session_state.images[image_id].last_preview_sha256 = (
                    entry.source_preview_sha256 or entry.preview_sha256
                )
            applied_image_ids.append(image_id)
        else:
            session_state.images[image_id] = copy.deepcopy(original_state.images[image_id])
            session_state.images[image_id].status = "REVIEW"
            failed_image_ids.append(image_id)
            convergence_summary["results"][image_id] = "REVIEW_CATALOG_APPLY_UNVERIFIED"

    session_state.is_converged = bool(session_state.images) and all(
        img.status == "PASS" for img in session_state.images.values()
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
    max_passes = int(session_state.policy.get("maximum_passes", 4))
    next_pass = (
        None
        if session_state.is_converged or pass_number >= max_passes
        else pass_number + 1
    )
    return {
        "session_id": session_id,
        "pass_number": pass_number,
        "pass_id": pass_id,
        "applied_count": len(applied_image_ids),
        "pass_count": pass_count,
        "review_count": review_count,
        "is_converged": session_state.is_converged,
        "requires_rerender": bool(applied_image_ids),
        "applied_image_ids": applied_image_ids,
        "failed_image_ids": failed_image_ids,
        "next_pass_number": next_pass,
        "apply_evidence": str(evidence_path),
    }
