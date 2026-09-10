"""Minimal one-job production contracts for Lightroom AI Exposure Assist.

This module is deliberately small. It does not call a vision provider, calculate
photographic semantics, read/write Lightroom Catalog databases, or mutate image
files. It owns only the provider-neutral semantic contract, durable one-job state,
owner-facing state resolution, and exact terminal accounting introduced by
WO-053.

Numeric Exposure authority remains in deterministic Python measurement/planning
primitives. Actual Catalog mutation remains exclusively in Lightroom through
``CatalogApplyBarrier.lua``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence


PROTOCOL_VERSION = "2.0"
JOB_STATE_FILENAME = "job.json"

WAITING_FOR_SEMANTICS = "WAITING_FOR_SEMANTICS"
PLAN_READY = "PLAN_READY"
APPLYING_CATALOG = "APPLYING_CATALOG"
VERIFYING_RENDERS = "VERIFYING_RENDERS"
RESIDUAL_PLAN_READY = "RESIDUAL_PLAN_READY"
APPLYING_RESIDUAL = "APPLYING_RESIDUAL"
VERIFYING_RESIDUAL = "VERIFYING_RESIDUAL"
COMPLETE = "COMPLETE"
NEEDS_ATTENTION = "NEEDS_ATTENTION"
ABORTED = "ABORTED"

_INTERNAL_STATES = frozenset(
    {
        WAITING_FOR_SEMANTICS,
        PLAN_READY,
        APPLYING_CATALOG,
        VERIFYING_RENDERS,
        RESIDUAL_PLAN_READY,
        APPLYING_RESIDUAL,
        VERIFYING_RESIDUAL,
        COMPLETE,
        NEEDS_ATTENTION,
        ABORTED,
    }
)
_TERMINAL_STATES = frozenset({COMPLETE, ABORTED})

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    WAITING_FOR_SEMANTICS: frozenset({PLAN_READY, NEEDS_ATTENTION, ABORTED}),
    PLAN_READY: frozenset({APPLYING_CATALOG, COMPLETE, NEEDS_ATTENTION, ABORTED}),
    APPLYING_CATALOG: frozenset({VERIFYING_RENDERS, NEEDS_ATTENTION}),
    VERIFYING_RENDERS: frozenset({RESIDUAL_PLAN_READY, COMPLETE, NEEDS_ATTENTION}),
    RESIDUAL_PLAN_READY: frozenset({APPLYING_RESIDUAL, COMPLETE, NEEDS_ATTENTION}),
    APPLYING_RESIDUAL: frozenset({VERIFYING_RESIDUAL, NEEDS_ATTENTION}),
    VERIFYING_RESIDUAL: frozenset({COMPLETE, NEEDS_ATTENTION}),
    NEEDS_ATTENTION: frozenset({ABORTED}),
    COMPLETE: frozenset(),
    ABORTED: frozenset(),
}

_GROUP_STATUSES = frozenset(
    {"REFERENCE_SELECTED", "TARGETS_SELECTED", "NO_CLEAR_REFERENCE", "MIXED_LIGHTING", "UNCERTAIN"}
)
_MEMBER_VERDICTS = frozenset({"AUTO", "UNRESOLVED"})
_TERMINAL_IMAGE_STATUSES = frozenset({"ADJUSTED", "NO_CHANGE", "UNRESOLVED"})
_REASON_CLASSES = frozenset({"PHOTOGRAPHIC", "TECHNICAL", "SAFETY"})


class ProductionJobError(ValueError):
    """Raised when one-job production identity/state/contracts are invalid."""


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)
    return path


def normalize_source_folder(value: str | Path) -> str:
    """Normalize source identity without requiring the source to exist locally."""

    text = str(value or "").strip().replace("/", "\\")
    while len(text) > 3 and text.endswith("\\"):
        text = text[:-1]
    return text.lower()


def _ordered_ids(values: Sequence[str]) -> tuple[str, ...]:
    ordered = tuple(str(value) for value in values)
    if not ordered or any(not value for value in ordered) or len(set(ordered)) != len(ordered):
        raise ProductionJobError("ordered image IDs must be non-empty and unique")
    return ordered


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionJobError(f"{label} must be an object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    optional = optional or set()
    keys = set(value)
    missing = sorted(required - keys)
    unexpected = sorted(keys - required - optional)
    if missing:
        raise ProductionJobError(f"{label} missing required field(s): {missing}")
    if unexpected:
        raise ProductionJobError(f"{label} has unexpected field(s): {unexpected}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductionJobError(f"{label} must be a non-empty string")
    return value.strip()


def validate_visual_semantics(
    payload: Mapping[str, Any],
    *,
    job_id: str,
    ordered_image_ids: Sequence[str],
) -> dict[str, Any]:
    """Validate the exact provider-neutral visual-semantics boundary.

    The input contract intentionally contains no numeric Exposure fields. Unknown
    fields are rejected at every level, so a provider cannot smuggle ``delta_ev``,
    target Exposure, brightness targets, or mutation instructions into the
    deterministic planning boundary.
    """

    root = _require_object(payload, "visual semantics")
    _require_exact_keys(
        root,
        required={"protocol_version", "job_id", "groups", "unassigned"},
        label="visual semantics",
    )
    if root.get("protocol_version") != PROTOCOL_VERSION:
        raise ProductionJobError("unsupported visual semantics protocol_version")
    expected_job = _require_nonempty_string(job_id, "job_id")
    if root.get("job_id") != expected_job:
        raise ProductionJobError("visual semantics job_id does not match the production job")

    ordered = _ordered_ids(ordered_image_ids)
    groups = root.get("groups")
    unassigned = root.get("unassigned")
    if not isinstance(groups, list):
        raise ProductionJobError("visual semantics groups must be an array")
    if not isinstance(unassigned, list):
        raise ProductionJobError("visual semantics unassigned must be an array")

    normalized_groups: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    group_ids: set[str] = set()

    for group_index, raw_group in enumerate(groups):
        group = _require_object(raw_group, f"groups[{group_index}]")
        _require_exact_keys(
            group,
            required={"group_id", "status", "reference_image_id", "members"},
            label=f"groups[{group_index}]",
        )
        group_id_value = _require_nonempty_string(
            group.get("group_id"), f"groups[{group_index}].group_id"
        )
        if group_id_value in group_ids:
            raise ProductionJobError("visual semantics group_id values must be unique")
        group_ids.add(group_id_value)

        status = group.get("status")
        if status not in _GROUP_STATUSES:
            raise ProductionJobError(
                f"groups[{group_index}].status must be one of {sorted(_GROUP_STATUSES)}"
            )
        reference = group.get("reference_image_id")
        if reference is not None and (not isinstance(reference, str) or not reference):
            raise ProductionJobError(
                f"groups[{group_index}].reference_image_id must be a string or null"
            )
        if status == "REFERENCE_SELECTED" and reference is None:
            raise ProductionJobError("REFERENCE_SELECTED requires reference_image_id")
        if status != "REFERENCE_SELECTED" and reference is not None:
            raise ProductionJobError(
                "reference_image_id must be null when a group declines/uncertains the reference"
            )

        members = group.get("members")
        if not isinstance(members, list) or not members:
            raise ProductionJobError(f"groups[{group_index}].members must be a non-empty array")
        normalized_members: list[dict[str, Any]] = []
        member_ids: list[str] = []
        for member_index, raw_member in enumerate(members):
            member = _require_object(
                raw_member, f"groups[{group_index}].members[{member_index}]"
            )
            _require_exact_keys(
                member,
                required={"image_id", "verdict"},
                optional={"reason", "target_candidate_id", "acceptable_candidate_ids"},
                label=f"groups[{group_index}].members[{member_index}]",
            )
            image_id = _require_nonempty_string(
                member.get("image_id"),
                f"groups[{group_index}].members[{member_index}].image_id",
            )
            verdict = member.get("verdict")
            if verdict not in _MEMBER_VERDICTS:
                raise ProductionJobError(
                    f"groups[{group_index}].members[{member_index}].verdict is invalid"
                )
            reason = member.get("reason")
            if verdict == "UNRESOLVED":
                reason = _require_nonempty_string(
                    reason,
                    f"groups[{group_index}].members[{member_index}].reason",
                )
            elif reason is not None:
                raise ProductionJobError(
                    "reason is allowed only when member verdict is UNRESOLVED"
                )
            target_candidate_id = member.get("target_candidate_id")
            acceptable_candidate_ids = member.get("acceptable_candidate_ids")
            if target_candidate_id is not None:
                target_candidate_id = _require_nonempty_string(
                    target_candidate_id,
                    f"groups[{group_index}].members[{member_index}].target_candidate_id",
                )
            if acceptable_candidate_ids is not None:
                if (
                    not isinstance(acceptable_candidate_ids, list)
                    or not acceptable_candidate_ids
                    or any(not isinstance(value, str) or not value.strip() for value in acceptable_candidate_ids)
                    or len(set(acceptable_candidate_ids)) != len(acceptable_candidate_ids)
                ):
                    raise ProductionJobError(
                        f"groups[{group_index}].members[{member_index}].acceptable_candidate_ids must be a non-empty unique string array"
                    )
                acceptable_candidate_ids = [value.strip() for value in acceptable_candidate_ids]
                if target_candidate_id is not None and target_candidate_id not in acceptable_candidate_ids:
                    raise ProductionJobError("target_candidate_id must belong to acceptable_candidate_ids")
            if status == "TARGETS_SELECTED" and verdict == "AUTO" and target_candidate_id is None:
                raise ProductionJobError("TARGETS_SELECTED AUTO members require target_candidate_id")
            if verdict == "UNRESOLVED" and (target_candidate_id is not None or acceptable_candidate_ids is not None):
                raise ProductionJobError("UNRESOLVED members cannot carry target candidate choices")

            normalized_member = {"image_id": image_id, "verdict": str(verdict)}
            if reason is not None:
                normalized_member["reason"] = reason
            if target_candidate_id is not None:
                normalized_member["target_candidate_id"] = target_candidate_id
            if acceptable_candidate_ids is not None:
                normalized_member["acceptable_candidate_ids"] = acceptable_candidate_ids
            normalized_members.append(normalized_member)
            member_ids.append(image_id)
            observed_ids.append(image_id)

        if len(set(member_ids)) != len(member_ids):
            raise ProductionJobError("visual semantics must exactly cover every image once")
        if reference is not None and reference not in member_ids:
            raise ProductionJobError("selected reference_image_id must belong to the same group")

        normalized_groups.append(
            {
                "group_id": group_id_value,
                "status": str(status),
                "reference_image_id": reference,
                "members": normalized_members,
            }
        )

    normalized_unassigned: list[dict[str, str]] = []
    for index, raw_item in enumerate(unassigned):
        item = _require_object(raw_item, f"unassigned[{index}]")
        _require_exact_keys(
            item,
            required={"image_id", "reason"},
            label=f"unassigned[{index}]",
        )
        image_id = _require_nonempty_string(item.get("image_id"), f"unassigned[{index}].image_id")
        reason = _require_nonempty_string(item.get("reason"), f"unassigned[{index}].reason")
        normalized_unassigned.append({"image_id": image_id, "reason": reason})
        observed_ids.append(image_id)

    if (
        len(observed_ids) != len(ordered)
        or len(set(observed_ids)) != len(observed_ids)
        or set(observed_ids) != set(ordered)
    ):
        missing = sorted(set(ordered) - set(observed_ids))
        foreign = sorted(set(observed_ids) - set(ordered))
        raise ProductionJobError(
            "visual semantics must exactly cover every input image once "
            f"(missing={missing}, foreign={foreign}, observed={len(observed_ids)}, expected={len(ordered)})"
        )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": expected_job,
        "groups": normalized_groups,
        "unassigned": normalized_unassigned,
        "covered_image_ids": list(ordered),
        "numeric_exposure_authority": "NONE",
        "mutation_authority": "NONE",
    }


def create_production_job_state(
    job_dir: Path | str,
    *,
    job_id: str,
    source_folder: Path | str,
    ordered_image_ids: Sequence[str],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the durable state record for one already-captured production job."""

    directory = Path(job_dir)
    if directory.name != job_id:
        raise ProductionJobError(
            f"production job directory/name mismatch: directory={directory.name!r} job_id={job_id!r}"
        )
    state_path = directory / JOB_STATE_FILENAME
    if state_path.exists():
        raise ProductionJobError(f"production job state already exists: {state_path}")
    ordered = _ordered_ids(ordered_image_ids)
    source = _require_nonempty_string(str(source_folder), "source_folder")
    if not isinstance(policy, Mapping):
        raise ProductionJobError("policy must be an object")

    payload: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "MINIMAL_PRODUCTION_JOB_STATE",
        "job_id": _require_nonempty_string(job_id, "job_id"),
        "source_folder": source,
        "source_folder_key": normalize_source_folder(source),
        "ordered_image_ids": list(ordered),
        "input_count": len(ordered),
        "state": WAITING_FOR_SEMANTICS,
        "policy": dict(policy),
        "residual_retry_budget": 1,
        "visual_semantics_runs": 0,
        "whole_album_pass_count": 0,
    }
    _atomic_write_json(state_path, payload)
    return payload


def load_production_job_state(job_dir: Path | str) -> dict[str, Any]:
    path = Path(job_dir) / JOB_STATE_FILENAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionJobError(f"production job state is unreadable: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProductionJobError("production job state must be an object")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise ProductionJobError("unsupported production job state protocol_version")
    if payload.get("result_kind") != "MINIMAL_PRODUCTION_JOB_STATE":
        raise ProductionJobError("production job state kind is invalid")
    if payload.get("job_id") != Path(job_dir).name:
        raise ProductionJobError("production job state identity does not match its directory")
    ordered = _ordered_ids(payload.get("ordered_image_ids", []))
    if payload.get("input_count") != len(ordered):
        raise ProductionJobError("production job input_count does not match ordered image IDs")
    state = payload.get("state")
    if state not in _INTERNAL_STATES:
        raise ProductionJobError(f"unknown production job state: {state!r}")
    source = payload.get("source_folder")
    if not isinstance(source, str) or not source:
        raise ProductionJobError("production job source_folder is missing")
    if payload.get("source_folder_key") != normalize_source_folder(source):
        raise ProductionJobError("production job source-folder identity is inconsistent")
    if payload.get("residual_retry_budget") != 1:
        raise ProductionJobError("production job residual retry budget must remain exactly one")
    if payload.get("whole_album_pass_count") != 0:
        raise ProductionJobError("minimal production job must not own a whole-album pass loop")
    return payload


def update_production_job_state(
    job_dir: Path | str,
    state: str,
    **updates: Any,
) -> dict[str, Any]:
    payload = load_production_job_state(job_dir)
    current = str(payload["state"])
    if state not in _INTERNAL_STATES:
        raise ProductionJobError(f"unknown production job state: {state!r}")
    if state != current and state not in _ALLOWED_TRANSITIONS[current]:
        raise ProductionJobError(f"invalid production state transition: {current} -> {state}")
    protected = {
        "protocol_version",
        "result_kind",
        "job_id",
        "source_folder",
        "source_folder_key",
        "ordered_image_ids",
        "input_count",
        "residual_retry_budget",
        "whole_album_pass_count",
    }
    overlap = sorted(protected.intersection(updates))
    if overlap:
        raise ProductionJobError(f"cannot overwrite immutable production job field(s): {overlap}")
    payload["state"] = state
    payload.update(updates)
    _atomic_write_json(Path(job_dir) / JOB_STATE_FILENAME, payload)
    return payload


def _owner_route_for(job_dir: Path, job: Mapping[str, Any]) -> dict[str, Any]:
    state = str(job["state"])
    common = {"job_id": str(job["job_id"]), "job_dir": str(job_dir)}
    if state == WAITING_FOR_SEMANTICS:
        return {"owner_state": "ANALYZING", "next_action": "CHECK_STATUS", **common}
    if state == PLAN_READY:
        plan_path = job_dir / "exposure-plan.json"
        if not plan_path.is_file():
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "MISSING_EXPOSURE_PLAN",
                **common,
            }
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "INVALID_EXPOSURE_PLAN",
                **common,
            }
        if not isinstance(plan, dict) or plan.get("job_id") != job.get("job_id"):
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "INVALID_EXPOSURE_PLAN",
                **common,
            }
        return {"owner_state": "READY_TO_APPLY", "next_action": "APPLY_EXPOSURE", **common}
    if state == RESIDUAL_PLAN_READY:
        residual_path = job_dir / "residual-plan.json"
        if not residual_path.is_file():
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "MISSING_RESIDUAL_PLAN",
                **common,
            }
        try:
            residual = json.loads(residual_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            residual = None
        if not isinstance(residual, dict) or residual.get("job_id") != job.get("job_id"):
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "INVALID_RESIDUAL_PLAN",
                **common,
            }
        return {"owner_state": "VERIFYING", "next_action": "FINE_TUNE_RESIDUAL", **common}
    if state in {
        APPLYING_CATALOG,
        VERIFYING_RENDERS,
        APPLYING_RESIDUAL,
        VERIFYING_RESIDUAL,
    }:
        return {"owner_state": "VERIFYING", "next_action": "CHECK_STATUS", **common}
    if state == COMPLETE:
        final_path = job_dir / "final-results.json"
        if not final_path.is_file():
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "MISSING_FINAL_RESULTS",
                **common,
            }
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            final = None
        counts = final.get("counts") if isinstance(final, dict) else None
        valid_final = (
            isinstance(final, dict)
            and final.get("result_kind") == "PRODUCTION_FINAL_ACCOUNTING"
            and final.get("job_id") == job.get("job_id")
            and final.get("ordered_image_ids") == job.get("ordered_image_ids")
            and isinstance(counts, dict)
            and counts.get("invariant_verified") is True
            and counts.get("input_count") == job.get("input_count")
            and isinstance(counts.get("adjusted"), int)
            and isinstance(counts.get("no_change"), int)
            and isinstance(counts.get("unresolved"), int)
            and counts.get("input_count")
            == counts.get("adjusted") + counts.get("no_change") + counts.get("unresolved")
        )
        if not valid_final:
            return {
                "owner_state": "NEEDS_ATTENTION",
                "next_action": None,
                "error": "INVALID_FINAL_RESULTS",
                **common,
            }
        return {"owner_state": "COMPLETE", "next_action": None, **common}
    return {
        "owner_state": "NEEDS_ATTENTION",
        "next_action": None,
        "error": str(job.get("error") or state),
        **common,
    }


def resolve_production_workflow_state(
    runtime_directory: Path | str,
    source_folder: Path | str,
) -> dict[str, Any]:
    """Resolve one owner-facing action from durable one-job state, read-only."""

    runtime = Path(runtime_directory)
    jobs_root = runtime / "jobs"
    source_key = normalize_source_folder(source_folder)
    if not jobs_root.is_dir():
        return {
            "owner_state": "READY",
            "next_action": "START_ANALYSIS",
            "job_id": None,
            "job_dir": None,
        }

    matching: list[tuple[int, Path, dict[str, Any]]] = []
    for job_dir in jobs_root.iterdir():
        if not job_dir.is_dir() or not (job_dir / JOB_STATE_FILENAME).is_file():
            continue
        try:
            job = load_production_job_state(job_dir)
        except ProductionJobError:
            # A state file that still identifies this source must not be ignored:
            # returning READY would permit a duplicate job over corrupt evidence.
            try:
                raw = json.loads((job_dir / JOB_STATE_FILENAME).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            raw_source = raw.get("source_folder") if isinstance(raw, dict) else None
            if isinstance(raw_source, str) and normalize_source_folder(raw_source) == source_key:
                return {
                    "owner_state": "NEEDS_ATTENTION",
                    "next_action": None,
                    "job_id": job_dir.name,
                    "job_dir": str(job_dir),
                    "error": "CORRUPT_PRODUCTION_JOB_STATE",
                }
            continue
        if job.get("source_folder_key") != source_key:
            continue
        try:
            mtime = (job_dir / JOB_STATE_FILENAME).stat().st_mtime_ns
        except OSError:
            mtime = 0
        matching.append((mtime, job_dir, job))

    if not matching:
        return {
            "owner_state": "READY",
            "next_action": "START_ANALYSIS",
            "job_id": None,
            "job_dir": None,
        }

    active = [record for record in matching if record[2]["state"] not in _TERMINAL_STATES]
    if len(active) > 1:
        return {
            "owner_state": "NEEDS_ATTENTION",
            "next_action": None,
            "job_id": None,
            "job_dir": None,
            "error": "MULTIPLE_ACTIVE_PRODUCTION_JOBS",
            "job_ids": sorted(str(record[2]["job_id"]) for record in active),
        }
    if active:
        _, job_dir, job = active[0]
        return _owner_route_for(job_dir, job)

    _, job_dir, job = max(matching, key=lambda item: (item[0], str(item[1])))
    return _owner_route_for(job_dir, job)


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProductionJobError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ProductionJobError(f"{label} must be a finite number")
    return result


def finalize_production_accounting(
    *,
    job_id: str,
    source_folder: str | Path,
    ordered_image_ids: Sequence[str],
    items: Sequence[Mapping[str, Any]],
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build the exact terminal ledger; every input image must appear once."""

    ordered = _ordered_ids(ordered_image_ids)
    frozen = tuple(items)
    item_ids: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(frozen):
        if not isinstance(raw, Mapping):
            raise ProductionJobError(f"terminal item {index} must be an object")
        image_id = _require_nonempty_string(raw.get("image_id"), f"terminal item {index}.image_id")
        item_ids.append(image_id)
        by_id[image_id] = raw
    if (
        len(item_ids) != len(ordered)
        or len(set(item_ids)) != len(item_ids)
        or set(item_ids) != set(ordered)
    ):
        missing = sorted(set(ordered) - set(item_ids))
        foreign = sorted(set(item_ids) - set(ordered))
        raise ProductionJobError(
            "terminal accounting must exactly cover every input image once "
            f"(missing={missing}, foreign={foreign}, observed={len(item_ids)}, expected={len(ordered)})"
        )

    normalized_items: list[dict[str, Any]] = []
    counts = {"ADJUSTED": 0, "NO_CHANGE": 0, "UNRESOLVED": 0}
    unresolved_breakdown: dict[str, int] = {}
    for image_id in ordered:
        raw = by_id[image_id]
        status = raw.get("final_status")
        if status not in _TERMINAL_IMAGE_STATUSES:
            raise ProductionJobError(
                f"image {image_id} has non-terminal final_status {status!r}; "
                f"expected one of {sorted(_TERMINAL_IMAGE_STATUSES)}"
            )
        reason_class = raw.get("reason_class")
        if reason_class not in _REASON_CLASSES:
            raise ProductionJobError(
                f"image {image_id} reason_class must be one of {sorted(_REASON_CLASSES)}"
            )
        reason_code = _require_nonempty_string(raw.get("reason_code"), f"image {image_id}.reason_code")
        baseline = _finite_number(raw.get("baseline_exposure2012"), f"image {image_id}.baseline_exposure2012")
        final = _finite_number(raw.get("final_exposure2012"), f"image {image_id}.final_exposure2012")
        total_delta = _finite_number(raw.get("total_delta_ev"), f"image {image_id}.total_delta_ev")
        residual_attempts = raw.get("residual_attempts")
        if isinstance(residual_attempts, bool) or not isinstance(residual_attempts, int) or residual_attempts not in {0, 1}:
            raise ProductionJobError(
                f"image {image_id}.residual_attempts must be 0 or 1"
            )
        if status == "NO_CHANGE" and abs(total_delta) > 1e-9:
            raise ProductionJobError(f"NO_CHANGE image {image_id} cannot carry a non-zero total_delta_ev")
        arithmetic_delta = final - baseline
        if abs(arithmetic_delta - total_delta) > 1e-9:
            raise ProductionJobError(
                f"image {image_id} exposure arithmetic does not match total_delta_ev "
                f"(final-baseline={arithmetic_delta}, total_delta_ev={total_delta})"
            )

        counts[str(status)] += 1
        if status == "UNRESOLVED":
            unresolved_breakdown[reason_code] = unresolved_breakdown.get(reason_code, 0) + 1
        normalized_items.append(
            {
                "image_id": image_id,
                "final_status": str(status),
                "baseline_exposure2012": baseline,
                "final_exposure2012": final,
                "total_delta_ev": total_delta,
                "residual_attempts": residual_attempts,
                "reason_class": str(reason_class),
                "reason_code": reason_code,
            }
        )

    input_count = len(ordered)
    total = counts["ADJUSTED"] + counts["NO_CHANGE"] + counts["UNRESOLVED"]
    if total != input_count:
        raise ProductionJobError("terminal accounting invariant failed")

    result: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "PRODUCTION_FINAL_ACCOUNTING",
        "job_id": _require_nonempty_string(job_id, "job_id"),
        "source_folder": _require_nonempty_string(str(source_folder), "source_folder"),
        "ordered_image_ids": list(ordered),
        "counts": {
            "input_count": input_count,
            "adjusted": counts["ADJUSTED"],
            "no_change": counts["NO_CHANGE"],
            "unresolved": counts["UNRESOLVED"],
            "invariant_verified": True,
        },
        "unresolved_breakdown": dict(sorted(unresolved_breakdown.items())),
        "items": normalized_items,
    }
    if output_path is not None:
        _atomic_write_json(Path(output_path), result)
    return result


__all__ = [
    "ABORTED",
    "APPLYING_CATALOG",
    "APPLYING_RESIDUAL",
    "COMPLETE",
    "NEEDS_ATTENTION",
    "PLAN_READY",
    "PROTOCOL_VERSION",
    "ProductionJobError",
    "RESIDUAL_PLAN_READY",
    "VERIFYING_RENDERS",
    "VERIFYING_RESIDUAL",
    "WAITING_FOR_SEMANTICS",
    "create_production_job_state",
    "extract_and_measure_production_fresh_previews",
    "finalize_production_accounting",
    "finalize_zero_mutation_plan",
    "load_production_job_state",
    "normalize_source_folder",
    "resolve_production_workflow_state",
    "update_production_job_state",
    "validate_visual_semantics",
]


# WO-053 Phase 2/3 composition imports. Kept here rather than duplicating the
# proven preview/contact-sheet and deterministic Exposure implementations.
from lr_ai_exposure.cache_extractor import extract_batch, snapshot_cache_dbs
from lr_ai_exposure.contact_sheets import (
    build_contact_sheets,
    validate_contact_sheet_package,
    validate_extracted_previews,
)
from lr_ai_exposure.handoff import handoff_job
from lr_ai_exposure.hybrid_exposure import (
    CanonicalFixedSkinRoi,
    InvalidMeasurement,
    UnresolvedExposureDecision,
    build_absolute_exposure_target,
    build_canonical_fixed_skin_roi,
    compute_per_image_delta_ev,
    estimate_renderer_calibrated_delta_ev,
    measure_canonical_fixed_skin_roi,
    RendererResponseUncertain,
)
from lr_ai_exposure.job import read_manifest
from lr_ai_exposure.scene_measurement import (
    InvalidSceneMeasurement,
    measure_robust_scene_luminance,
)
from lr_ai_exposure.reference_free_target import (
    build_reference_free_target_package,
    candidate_record,
    display_clip_metrics,
    load_reference_free_target_candidates,
    simulate_display_exposure_jpeg,
)
from lr_ai_exposure.session_retention import (
    assert_production_job_compaction_allowed,
    build_production_job_retention_report,
)



def visual_semantics_json_schema() -> dict[str, Any]:
    """Return the public semantic-only provider contract for one production job."""

    member = {
        "type": "object",
        "required": ["image_id", "verdict"],
        "properties": {
            "image_id": {"type": "string", "minLength": 1},
            "verdict": {"enum": sorted(_MEMBER_VERDICTS)},
            "reason": {"type": "string", "minLength": 1},
            "target_candidate_id": {"type": "string", "pattern": "^c[0-9]{2}$"},
            "acceptable_candidate_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "pattern": "^c[0-9]{2}$"},
            },
        },
        "additionalProperties": False,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "AI Exposure Assist Visual Semantics",
        "type": "object",
        "required": ["protocol_version", "job_id", "groups", "unassigned"],
        "properties": {
            "protocol_version": {"const": PROTOCOL_VERSION},
            "job_id": {"type": "string", "minLength": 1},
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["group_id", "status", "reference_image_id", "members"],
                    "properties": {
                        "group_id": {"type": "string", "minLength": 1},
                        "status": {"enum": sorted(_GROUP_STATUSES)},
                        "reference_image_id": {"type": ["string", "null"]},
                        "members": {"type": "array", "minItems": 1, "items": member},
                    },
                    "additionalProperties": False,
                },
            },
            "unassigned": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["image_id", "reason"],
                    "properties": {
                        "image_id": {"type": "string", "minLength": 1},
                        "reason": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
        "x-authority": {
            "numeric_exposure": "NONE",
            "mutation": "NONE",
            "exact_image_coverage_required": True,
        },
    }


def _production_task_text(*, job_id: str, source_folder: str, image_count: int) -> str:
    return f"""# AI Exposure Assist — Reference-Free Visual Targets

Job: `{job_id}`
Source folder: `{source_folder}`
Images: `{image_count}`

Your role is visual target selection only. Do not choose a master/reference exposure.
For every image, inspect its sheet under `reference-free-brackets/`. Each panel is
identified only by an opaque candidate ID such as `c00`, `c01`, ... . Select the
photographically best candidate for that image while preserving intentional high-key,
low-key, backlight/silhouette intent and avoiding unnecessary highlight loss.

Output rules:
- group images only for contextual consistency;
- use group status `TARGETS_SELECTED` with `reference_image_id: null`;
- mark assignable group members `AUTO` and provide `target_candidate_id` for each confident member;
- optionally provide `acceptable_candidate_ids` when multiple neighboring choices are acceptable;
- use `UNRESOLVED` with a short reason when photographic intent is genuinely ambiguous;
- every input image ID must appear exactly once.

Candidate IDs are opaque visual choices. Do **not** output numeric EV, Exposure2012,
brightness targets, deltas, or mutation instructions. Python owns candidate mapping,
renderer calibration, safety gates, and all Lightroom numeric authority. The AI has no
Lightroom/Catalog/XMP mutation authority.

Write output matching `visual-semantics-schema.json` to `visual-semantics-input.json`.
"""


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionJobError(f"{label} is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProductionJobError(f"{label} must be a JSON object")
    return value


def _load_production_selection(path: Path | str) -> dict[str, Any]:
    selection = _read_json_object(Path(path), "production selection")
    _require_exact_keys(
        selection,
        required={"protocol_version", "job_id", "selected_count", "source_folder", "photos"},
        optional={"folder_photo_count"},
        label="production selection",
    )
    if selection.get("protocol_version") != PROTOCOL_VERSION:
        raise ProductionJobError("production selection protocol_version must be 2.0")
    job_id = _require_nonempty_string(selection.get("job_id"), "production selection.job_id")
    source = _require_nonempty_string(selection.get("source_folder"), "production selection.source_folder")
    photos = selection.get("photos")
    if not isinstance(photos, list) or not photos:
        raise ProductionJobError("production selection.photos must be a non-empty array")
    if selection.get("selected_count") != len(photos):
        raise ProductionJobError("production selection selected_count does not match photos")
    ids: list[str] = []
    normalized_photos: list[dict[str, Any]] = []
    for index, raw in enumerate(photos):
        photo = _require_object(raw, f"production selection.photos[{index}]")
        _require_exact_keys(
            photo,
            required={"id_local", "path", "uuid", "catalog_exposure2012"},
            label=f"production selection.photos[{index}]",
        )
        image_id = _require_nonempty_string(photo.get("id_local"), f"photos[{index}].id_local")
        path_value = _require_nonempty_string(photo.get("path"), f"photos[{index}].path")
        uuid_value = _require_nonempty_string(photo.get("uuid"), f"photos[{index}].uuid")
        exposure = _finite_number(photo.get("catalog_exposure2012"), f"photos[{index}].catalog_exposure2012")
        ids.append(image_id)
        normalized_photos.append(
            {
                "id_local": image_id,
                "path": path_value,
                "uuid": uuid_value,
                "catalog_exposure2012": exposure,
            }
        )
    _ordered_ids(ids)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": job_id,
        "selected_count": len(ids),
        "source_folder": source,
        "folder_photo_count": selection.get("folder_photo_count"),
        "photos": normalized_photos,
        "ordered_image_ids": ids,
    }


def prepare_production_package(
    *,
    runtime_directory: Path | str,
    lrdata_dir: Path | str,
    selection_json_path: Path | str,
    preview_size: int,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose the proven job/cache/contact-sheet primitives exactly once."""

    if isinstance(preview_size, bool) or not isinstance(preview_size, int) or preview_size <= 0:
        raise ProductionJobError("preview_size must be a positive integer")
    selection = _load_production_selection(selection_json_path)
    runtime = Path(runtime_directory)
    existing = resolve_production_workflow_state(runtime, selection["source_folder"])
    if existing.get("owner_state") in {"ANALYZING", "READY_TO_APPLY", "VERIFYING"}:
        raise ProductionJobError(
            f"ACTIVE_PRODUCTION_JOB_EXISTS: {existing.get('job_id')}; continue that job instead"
        )
    if existing.get("owner_state") == "NEEDS_ATTENTION" and existing.get("job_id"):
        raise ProductionJobError(
            f"ACTIVE_PRODUCTION_JOB_NEEDS_ATTENTION: {existing.get('job_id')}"
        )

    returned_job_id = handoff_job(
        str(runtime),
        str(lrdata_dir),
        str(selection_json_path),
        preview_size,
        validated_protocol_version=PROTOCOL_VERSION,
    )
    if returned_job_id != selection["job_id"]:
        raise ProductionJobError(
            f"handoff job identity mismatch: expected {selection['job_id']}, got {returned_job_id}"
        )
    job_dir = runtime / "jobs" / returned_job_id
    manifest = read_manifest(job_dir)
    state = create_production_job_state(
        job_dir,
        job_id=returned_job_id,
        source_folder=selection["source_folder"],
        ordered_image_ids=selection["ordered_image_ids"],
        policy=policy,
    )

    if manifest.total_selected != selection["selected_count"] or manifest.total_found != selection["selected_count"]:
        update_production_job_state(
            job_dir,
            NEEDS_ATTENTION,
            error="PREVIEW_PACKAGE_INCOMPLETE",
            package_counts={
                "selected": manifest.total_selected,
                "found": manifest.total_found,
                "missing": manifest.total_missing,
                "ambiguous": manifest.total_ambiguous,
                "failed": manifest.total_failed,
            },
        )
        raise ProductionJobError("PREVIEW_PACKAGE_INCOMPLETE: every input image requires a usable preview")

    try:
        previews = validate_extracted_previews(job_dir, manifest)
        contact_index = build_contact_sheets(job_dir, previews)
        validate_contact_sheet_package(job_dir, manifest)
        reference_free_package = build_reference_free_target_package(job_dir, manifest)
    except Exception as exc:
        update_production_job_state(
            job_dir,
            NEEDS_ATTENTION,
            error=f"PACKAGE_VALIDATION_FAILED:{type(exc).__name__}",
        )
        raise ProductionJobError(f"production package validation failed: {exc}") from exc

    _atomic_write_json(job_dir / "visual-semantics-schema.json", visual_semantics_json_schema())
    (job_dir / "AI_TASK.md").write_text(
        _production_task_text(
            job_id=returned_job_id,
            source_folder=selection["source_folder"],
            image_count=selection["selected_count"],
        ),
        encoding="utf-8",
    )
    state = update_production_job_state(
        job_dir,
        WAITING_FOR_SEMANTICS,
        package_ready=True,
        manifest_path="manifest.json",
        contact_sheet_index=str(Path(contact_index).relative_to(job_dir)),
        visual_semantics_schema="visual-semantics-schema.json",
        reference_free_targets="reference-free-target-candidates.json",
        reference_free_target_count=len(reference_free_package["items"]),
        ai_task="AI_TASK.md",
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": returned_job_id,
        "job_dir": str(job_dir),
        "source_folder": selection["source_folder"],
        "total_images": selection["selected_count"],
        "state": state["state"],
        "owner_state": "ANALYZING",
        "next_action": "RUN_VISUAL_SEMANTICS",
        "mutation_authority": "NONE",
    }


def _validate_reference_free_candidate_choices(job_dir: Path, semantics: Mapping[str, Any]) -> None:
    candidate_path = job_dir / "reference-free-target-candidates.json"
    if candidate_path.is_file():
        if any(group.get("status") == "REFERENCE_SELECTED" for group in semantics.get("groups", [])):
            raise ProductionJobError(
                "reference-free production jobs forbid REFERENCE_SELECTED photographic authority"
            )
    uses_targets = any(
        member.get("target_candidate_id") is not None
        for group in semantics.get("groups", [])
        for member in group.get("members", [])
    )
    if not uses_targets:
        return
    if not candidate_path.is_file():
        raise ProductionJobError("reference-free target candidate manifest is required")
    try:
        manifest = load_reference_free_target_candidates(job_dir)
        for group in semantics.get("groups", []):
            for member in group.get("members", []):
                candidate_id = member.get("target_candidate_id")
                if candidate_id is None:
                    continue
                candidate_record(
                    manifest,
                    image_id=str(member["image_id"]),
                    candidate_id=str(candidate_id),
                )
                for acceptable in member.get("acceptable_candidate_ids", []):
                    candidate_record(
                        manifest,
                        image_id=str(member["image_id"]),
                        candidate_id=str(acceptable),
                    )
    except ValueError as exc:
        raise ProductionJobError(str(exc)) from exc


def import_visual_semantics(
    job_dir: Path | str,
    semantics_json_path: Path | str,
) -> dict[str, Any]:
    """Import one and only one visual-semantics result for the job."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != WAITING_FOR_SEMANTICS:
        raise ProductionJobError(
            f"visual semantics can be imported only while waiting; state={state['state']}"
        )
    if state.get("visual_semantics_runs") != 0 or (directory / "visual-semantics.json").exists():
        raise ProductionJobError("visual semantics must run/import exactly once per production job")
    payload = _read_json_object(Path(semantics_json_path), "visual semantics input")
    validated = validate_visual_semantics(
        payload,
        job_id=state["job_id"],
        ordered_image_ids=state["ordered_image_ids"],
    )
    _validate_reference_free_candidate_choices(directory, validated)
    _atomic_write_json(directory / "visual-semantics.json", validated)
    update_production_job_state(
        directory,
        WAITING_FOR_SEMANTICS,
        visual_semantics_runs=1,
        visual_semantics_path="visual-semantics.json",
    )
    return validated


def _normalize_measurement_results(
    job_dir: Path,
    ordered_image_ids: Sequence[str],
    measurements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest = read_manifest(job_dir)
    manifest_by_id = {str(entry.image_id): entry for entry in manifest.entries}
    if set(manifest_by_id) != set(ordered_image_ids):
        raise ProductionJobError("manifest identity does not exactly match production job inputs")

    observed_ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(measurements):
        if not isinstance(raw, Mapping):
            raise ProductionJobError(f"measurement item {index} must be an object")
        keys = set(raw)
        required = {"image_id", "status", "measurement", "preview_sha256"}
        if keys != required:
            unexpected = sorted(keys - required)
            missing = sorted(required - keys)
            raise ProductionJobError(
                f"measurement item {index} fields invalid (missing={missing}, unexpected={unexpected})"
            )
        image_id = _require_nonempty_string(raw.get("image_id"), f"measurement item {index}.image_id")
        observed_ids.append(image_id)
        status = raw.get("status")
        if status not in {"MEASURED", "UNUSABLE"}:
            raise ProductionJobError("measurement status must be MEASURED or UNUSABLE")
        preview_sha = _require_nonempty_string(raw.get("preview_sha256"), f"measurement {image_id}.preview_sha256")
        expected_entry = manifest_by_id.get(image_id)
        if expected_entry is None or preview_sha != expected_entry.preview_sha256:
            raise ProductionJobError(
                f"measurement preview_sha256 does not match immutable manifest for image {image_id}"
            )
        measurement_value = raw.get("measurement")
        if status == "MEASURED":
            measurement_value = _finite_number(measurement_value, f"measurement {image_id}.measurement")
            if measurement_value <= 0:
                raise ProductionJobError(f"measurement {image_id}.measurement must be positive")
        elif measurement_value is not None:
            raise ProductionJobError("UNUSABLE measurement must carry null measurement")
        by_id[image_id] = {
            "image_id": image_id,
            "status": status,
            "measurement": measurement_value,
            "preview_sha256": preview_sha,
        }

    ordered = _ordered_ids(ordered_image_ids)
    if (
        len(observed_ids) != len(ordered)
        or len(set(observed_ids)) != len(observed_ids)
        or set(observed_ids) != set(ordered)
    ):
        raise ProductionJobError("measurement results must exactly cover every input image once")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "DETERMINISTIC_MEASUREMENT_RESULTS",
        "job_id": job_dir.name,
        "measurement_authority": "DETERMINISTIC_PYTHON",
        "items": [by_id[image_id] for image_id in ordered],
    }


def _serialize_canonical_fixed_roi(roi: CanonicalFixedSkinRoi) -> dict[str, Any]:
    return {
        "canonical_long_edge": int(roi.canonical_long_edge),
        "canonical_width": int(roi.canonical_width),
        "canonical_height": int(roi.canonical_height),
        "box": [int(value) for value in roi.box],
        "mask_width": int(roi.mask_width),
        "mask_height": int(roi.mask_height),
        "packed_mask_base64": base64.b64encode(bytes(roi.packed_mask)).decode("ascii"),
        "skin_pixels": int(roi.skin_pixels),
    }


def _deserialize_canonical_fixed_roi(record: Mapping[str, Any]) -> CanonicalFixedSkinRoi:
    required = {
        "canonical_long_edge",
        "canonical_width",
        "canonical_height",
        "box",
        "mask_width",
        "mask_height",
        "packed_mask_base64",
        "skin_pixels",
    }
    if set(record) != required:
        raise ProductionJobError("canonical fixed ROI fields are invalid")
    box = record.get("box")
    if not isinstance(box, list) or len(box) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in box):
        raise ProductionJobError("canonical fixed ROI box must contain four integers")
    numeric_names = (
        "canonical_long_edge",
        "canonical_width",
        "canonical_height",
        "mask_width",
        "mask_height",
        "skin_pixels",
    )
    numeric: dict[str, int] = {}
    for name in numeric_names:
        value = record.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ProductionJobError(f"canonical fixed ROI {name} must be a positive integer")
        numeric[name] = value
    encoded = record.get("packed_mask_base64")
    if not isinstance(encoded, str) or not encoded:
        raise ProductionJobError("canonical fixed ROI packed mask is missing")
    try:
        packed = base64.b64decode(encoded.encode("ascii"), validate=True)
    except Exception as exc:
        raise ProductionJobError("canonical fixed ROI packed mask is invalid base64") from exc
    if not packed:
        raise ProductionJobError("canonical fixed ROI packed mask is empty")
    return CanonicalFixedSkinRoi(
        canonical_long_edge=numeric["canonical_long_edge"],
        canonical_width=numeric["canonical_width"],
        canonical_height=numeric["canonical_height"],
        box=tuple(box),
        mask_width=numeric["mask_width"],
        mask_height=numeric["mask_height"],
        packed_mask=packed,
        skin_pixels=numeric["skin_pixels"],
    )


def _coerce_measurement_provenance(provenance: Any) -> dict[str, Any] | None:
    if provenance is None:
        return None
    if not isinstance(provenance, Mapping):
        raise ProductionJobError("measurement_provenance must be an object")
    return {str(key): value for key, value in provenance.items()}


def build_production_baseline_measurements(
    job_dir: Path | str,
    *,
    meter: Any | None = None,
    canonical_long_edge: int = 1440,
    min_skin_pixels: int = 50,
    measurement_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure immutable baseline previews in one provider-neutral scene domain.

    Production numeric authority is robust scene luminance for every decodable
    JPEG.  A face/skin meter is optional and is used only as a compatibility
    fallback when synthetic/legacy test evidence is not a decodable JPEG.  This
    prevents face detection from becoming a production admission gate.
    """

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != WAITING_FOR_SEMANTICS or state.get("visual_semantics_runs") != 1:
        raise ProductionJobError("baseline measurement requires one frozen visual-semantics result")
    if (directory / "measurement-results.json").exists() or (directory / "measurement-rois.json").exists():
        raise ProductionJobError("baseline deterministic measurements already exist for this production job")
    if isinstance(canonical_long_edge, bool) or not isinstance(canonical_long_edge, int) or canonical_long_edge <= 0:
        raise ProductionJobError("canonical_long_edge must be a positive integer")
    if isinstance(min_skin_pixels, bool) or not isinstance(min_skin_pixels, int) or min_skin_pixels < 0:
        raise ProductionJobError("min_skin_pixels must be a non-negative integer")

    measure_fn = None if meter is None else getattr(meter, "measure_bytes", None)
    if meter is not None and not callable(measure_fn):
        raise ProductionJobError("measurement backend must expose measure_bytes(image_id=..., jpeg_bytes=...)")
    provenance = _coerce_measurement_provenance(
        measurement_provenance
        if measurement_provenance is not None
        else getattr(meter, "provenance", None) if meter is not None else None
    )

    manifest = read_manifest(directory)
    by_id = {str(entry.image_id): entry for entry in manifest.entries}
    measurement_items: list[dict[str, Any]] = []
    roi_items: list[dict[str, Any]] = []

    for image_id in state["ordered_image_ids"]:
        entry = by_id.get(image_id)
        if entry is None:
            raise ProductionJobError(f"manifest has no input image {image_id}")
        preview_path = directory / entry.preview_path
        try:
            jpeg_bytes = preview_path.read_bytes()
        except OSError as exc:
            raise ProductionJobError(f"baseline preview is unreadable for image {image_id}: {exc}") from exc
        observed_sha = hashlib.sha256(jpeg_bytes).hexdigest()
        if observed_sha != entry.preview_sha256:
            raise ProductionJobError(
                f"baseline preview_sha256 mismatch for image {image_id}: manifest={entry.preview_sha256} observed={observed_sha}"
            )

        try:
            scene = measure_robust_scene_luminance(jpeg_bytes)
        except InvalidSceneMeasurement:
            scene = None

        if scene is not None:
            measurement_items.append({
                "image_id": image_id,
                "status": "MEASURED",
                "measurement": float(scene.measurement),
                "preview_sha256": observed_sha,
            })
            roi_items.append({
                "image_id": image_id,
                "baseline_preview_sha256": observed_sha,
                "measurement_strategy": "ROBUST_SCENE_LUMINANCE",
                "highlight_clip_fraction": float(scene.highlight_clip_fraction),
                "scene_crop_fraction": float(scene.crop_fraction),
                "scene_trim_fraction": float(scene.trim_fraction),
            })
            continue

        # Compatibility fallback for non-JPEG unit fixtures and legacy evidence.
        if not callable(measure_fn):
            measurement_items.append({
                "image_id": image_id,
                "status": "UNUSABLE",
                "measurement": None,
                "preview_sha256": observed_sha,
            })
            continue
        try:
            frame = measure_fn(image_id=image_id, jpeg_bytes=jpeg_bytes)
        except Exception as exc:
            raise ProductionJobError(f"deterministic measurement backend failed for image {image_id}: {exc}") from exc
        faces = tuple(getattr(frame, "faces", ()) or ())
        usable = tuple(
            face for face in faces
            if bool(getattr(face, "valid_skin", False))
            and getattr(face, "measurement", None) is not None
        )
        if not usable:
            measurement_items.append({
                "image_id": image_id,
                "status": "UNUSABLE",
                "measurement": None,
                "preview_sha256": observed_sha,
            })
            continue

        face_roi_entries: list[dict[str, Any]] = []
        face_measurements: list[float] = []
        try:
            for face in usable:
                roi = build_canonical_fixed_skin_roi(
                    jpeg_bytes=jpeg_bytes,
                    box=tuple(int(v) for v in face.box),
                    canonical_long_edge=canonical_long_edge,
                    min_skin_pixels=min_skin_pixels,
                )
                measured_face = float(measure_canonical_fixed_skin_roi(jpeg_bytes=jpeg_bytes, roi=roi))
                if not math.isfinite(measured_face) or measured_face <= 0:
                    raise ProductionJobError(f"canonical fixed ROI measurement is invalid for image {image_id}")
                face_measurements.append(measured_face)
                face_roi_entries.append({
                    "face_id": str(getattr(face, "face_id", "")),
                    "roi": _serialize_canonical_fixed_roi(roi),
                })
        except ProductionJobError:
            raise
        except Exception as exc:
            raise ProductionJobError(f"canonical fixed ROI measurement failed for image {image_id}: {exc}") from exc

        measurement = float(statistics.median(face_measurements))
        measurement_items.append({
            "image_id": image_id,
            "status": "MEASURED",
            "measurement": measurement,
            "preview_sha256": observed_sha,
        })
        roi_item: dict[str, Any] = {
            "image_id": image_id,
            "baseline_preview_sha256": observed_sha,
            "measurement_strategy": "MEDIAN_USABLE_FACES",
            "face_rois": face_roi_entries,
        }
        if len(face_roi_entries) == 1:
            roi_item["face_id"] = face_roi_entries[0]["face_id"]
            roi_item["roi"] = face_roi_entries[0]["roi"]
        roi_items.append(roi_item)

    measurement_record = _normalize_measurement_results(
        directory, state["ordered_image_ids"], measurement_items
    )
    measurement_record["measurement_strategy"] = "ROBUST_SCENE_LUMINANCE_WITH_LEGACY_FACE_FALLBACK"
    if provenance is not None:
        measurement_record["measurement_provenance"] = provenance
    roi_record = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "PRODUCTION_CANONICAL_FIXED_ROIS",
        "job_id": state["job_id"],
        "measurement_kind": "SCENE_OR_CANONICAL_FIXED_ROI",
        "items": roi_items,
    }
    if provenance is not None:
        roi_record["measurement_provenance"] = provenance
    _atomic_write_json(directory / "measurement-results.json", measurement_record)
    _atomic_write_json(directory / "measurement-rois.json", roi_record)
    update_production_job_state(
        directory,
        WAITING_FOR_SEMANTICS,
        baseline_measurements="measurement-results.json",
        measurement_rois="measurement-rois.json",
    )
    return measurement_record


def extract_and_measure_production_fresh_previews(
    job_dir: Path | str,
    *,
    lrdata_dir: Path | str,
    expected_image_ids: Sequence[str],
    target_preview_size: int = 1440,
) -> dict[str, Any]:
    """Extract only confirmed adjusted previews and remeasure frozen ROIs.

    This is the non-mutating post-Catalog barrier: it snapshots Lightroom preview
    DBs read-only, extracts current rendered Standard Preview-class JPEGs for the
    exact adjusted subset, then feeds those files into fixed-ROI measurement.
    """

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    expected = [str(value) for value in expected_image_ids]
    if state["state"] == VERIFYING_RENDERS:
        authorized = [str(value) for value in state.get("applied_verified_image_ids", [])]
        result_kind = "PRODUCTION_FRESH_RENDER_MEASUREMENTS"
    elif state["state"] == VERIFYING_RESIDUAL:
        authorized = [str(value) for value in state.get("residual_verified_image_ids", [])]
        result_kind = "PRODUCTION_RESIDUAL_FRESH_RENDER_MEASUREMENTS"
    else:
        raise ProductionJobError(
            "fresh preview measurement requires VERIFYING_RENDERS or VERIFYING_RESIDUAL; "
            f"state={state['state']}"
        )
    if expected != authorized:
        raise ProductionJobError(
            "fresh preview measurement subset must match the exact confirmed adjusted order "
            f"(expected={authorized}, observed={expected})"
        )

    selection = _load_production_selection(directory / "selection.json")
    if selection["job_id"] != state["job_id"] or selection["ordered_image_ids"] != state["ordered_image_ids"]:
        raise ProductionJobError("selection identity does not match production job state")
    photos_by_id = {str(photo["id_local"]): photo for photo in selection["photos"]}
    missing = [image_id for image_id in expected if image_id not in photos_by_id]
    if missing:
        raise ProductionJobError(f"fresh preview subset is absent from selection: {missing}")
    identities = [photos_by_id[image_id] for image_id in expected]

    snapshot_dir = directory / "fresh-preview-cache-snapshot"
    out_dir = directory / "fresh-previews"
    snapshot_cache_dbs(str(lrdata_dir), str(snapshot_dir))
    extracted = extract_batch(
        identities,
        str(snapshot_dir),
        str(out_dir),
        lrdata_dir=str(lrdata_dir),
        target_preview_size=int(target_preview_size),
    )

    extract_results: list[dict[str, Any]] = []
    preview_paths: dict[str, Path] = {}
    for index, raw in enumerate(extracted):
        if not isinstance(raw, Mapping):
            raise ProductionJobError(f"fresh extraction result {index} must be an object")
        image_id = _require_nonempty_string(raw.get("id_local"), f"fresh extraction {index}.id_local")
        status = raw.get("status")
        tier = raw.get("source_preview_tier")
        output = raw.get("output")
        if status != "FOUND" or not output:
            raise ProductionJobError(
                f"fresh preview extraction failed for image {image_id}: {status}"
            )
        if not isinstance(tier, int) or tier < int(target_preview_size):
            raise ProductionJobError(
                f"fresh preview {image_id} is not Standard Preview-class: tier={tier}"
            )
        source_sha = _require_nonempty_string(
            raw.get("source_preview_sha256"),
            f"fresh extraction {image_id}.source_preview_sha256",
        )
        preview_paths[image_id] = Path(str(output))
        extract_results.append(
            {
                "image_id": image_id,
                "status": "FOUND",
                "source_preview_tier": tier,
                "source_preview_sha256": source_sha,
                "output": str(output),
                "orientation": raw.get("orientation"),
            }
        )
    if [item["image_id"] for item in extract_results] != expected:
        raise ProductionJobError("fresh extraction order does not match confirmed adjusted subset")

    items = measure_production_fresh_previews(
        directory,
        preview_paths=preview_paths,
        expected_image_ids=expected,
    )
    by_id = {item["image_id"]: item for item in extract_results}
    for measured in items:
        image_id = measured["image_id"]
        source_sha = str(measured["source_preview_sha256"])
        if source_sha != by_id[image_id]["source_preview_sha256"]:
            raise ProductionJobError(f"fresh measurement source SHA mismatch for image {image_id}")

    record = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": result_kind,
        "job_id": state["job_id"],
        "verification_scope": "ADJUSTED_ONLY" if state["state"] == VERIFYING_RENDERS else "RESIDUAL_ONLY",
        "ordered_image_ids": list(expected),
        "target_preview_size": int(target_preview_size),
        "extract_results": extract_results,
        "items": items,
        "mutation_authority": "NONE",
    }
    _atomic_write_json(directory / "fresh-measurements.json", record)
    return record


def measure_production_fresh_previews(
    job_dir: Path | str,
    *,
    preview_paths: Mapping[str, Path | str],
    expected_image_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Remeasure an exact fresh subset in its frozen baseline measurement domain."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    expected = tuple(str(value) for value in expected_image_ids)
    if not expected or len(set(expected)) != len(expected):
        raise ProductionJobError("fresh measurement subset must be non-empty and unique")
    if any(image_id not in set(state["ordered_image_ids"]) for image_id in expected):
        raise ProductionJobError("fresh measurement subset contains image outside production inputs")
    if set(str(k) for k in preview_paths) != set(expected):
        raise ProductionJobError("fresh preview paths must exactly cover the expected subset")

    roi_record = _read_json_object(directory / "measurement-rois.json", "production fixed ROI evidence")
    if roi_record.get("protocol_version") != PROTOCOL_VERSION or roi_record.get("job_id") != state["job_id"]:
        raise ProductionJobError("production fixed ROI evidence identity mismatch")
    if roi_record.get("result_kind") != "PRODUCTION_CANONICAL_FIXED_ROIS":
        raise ProductionJobError("production fixed ROI evidence kind mismatch")
    items = roi_record.get("items")
    if not isinstance(items, list):
        raise ProductionJobError("production fixed ROI evidence items must be an array")
    roi_by_id: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ProductionJobError(f"production fixed ROI item {index} must be an object")
        image_id = _require_nonempty_string(item.get("image_id"), f"production fixed ROI item {index}.image_id")
        if image_id in roi_by_id:
            raise ProductionJobError(f"production fixed ROI evidence contains duplicate image_id {image_id}")
        roi_by_id[image_id] = item
    missing = [image_id for image_id in expected if image_id not in roi_by_id]
    if missing:
        raise ProductionJobError(f"fresh measurement has no frozen measurement evidence for image(s): {missing}")

    results: list[dict[str, Any]] = []
    for image_id in expected:
        path = Path(preview_paths[image_id])
        try:
            jpeg_bytes = path.read_bytes()
        except OSError as exc:
            raise ProductionJobError(f"fresh preview is unreadable for image {image_id}: {exc}") from exc
        source_sha = hashlib.sha256(jpeg_bytes).hexdigest()
        roi_item = roi_by_id[image_id]
        strategy = str(roi_item.get("measurement_strategy") or "")

        if strategy == "ROBUST_SCENE_LUMINANCE":
            try:
                scene = measure_robust_scene_luminance(jpeg_bytes)
            except InvalidSceneMeasurement as exc:
                raise ProductionJobError(f"fresh robust scene measurement failed for image {image_id}: {exc}") from exc
            results.append({
                "image_id": image_id,
                "measurement_kind": "ROBUST_SCENE_LUMINANCE",
                "source_preview_sha256": source_sha,
                "observed_measurement": float(scene.measurement),
            })
            continue

        frozen_rois: list[CanonicalFixedSkinRoi] = []
        measurement_kind = "CANONICAL_FIXED_ROI"
        face_rois_raw = roi_item.get("face_rois")
        if face_rois_raw is not None:
            if strategy != "MEDIAN_USABLE_FACES":
                raise ProductionJobError(f"unsupported multi-face measurement strategy for image {image_id}")
            if not isinstance(face_rois_raw, list) or not face_rois_raw:
                raise ProductionJobError(f"frozen multi-face ROI set is missing for image {image_id}")
            face_ids: list[str] = []
            for face_index, face_roi_raw in enumerate(face_rois_raw):
                if not isinstance(face_roi_raw, Mapping):
                    raise ProductionJobError(f"frozen face ROI {face_index} is invalid for image {image_id}")
                face_id = _require_nonempty_string(
                    face_roi_raw.get("face_id"), f"frozen face ROI {image_id}.{face_index}.face_id"
                )
                roi_raw = face_roi_raw.get("roi")
                if not isinstance(roi_raw, Mapping):
                    raise ProductionJobError(f"frozen face ROI {face_id} is missing for image {image_id}")
                face_ids.append(face_id)
                frozen_rois.append(_deserialize_canonical_fixed_roi(roi_raw))
            if len(set(face_ids)) != len(face_ids):
                raise ProductionJobError(f"frozen multi-face ROI set contains duplicate face IDs for image {image_id}")
            if len(frozen_rois) > 1:
                measurement_kind = "CANONICAL_FIXED_ROI_MEDIAN"
        else:
            roi_raw = roi_item.get("roi")
            if not isinstance(roi_raw, Mapping):
                raise ProductionJobError(f"frozen canonical ROI is missing for image {image_id}")
            frozen_rois.append(_deserialize_canonical_fixed_roi(roi_raw))

        observed_values: list[float] = []
        for roi in frozen_rois:
            try:
                observed_face = float(measure_canonical_fixed_skin_roi(jpeg_bytes=jpeg_bytes, roi=roi))
            except Exception as exc:
                raise ProductionJobError(f"fresh canonical fixed ROI measurement failed for image {image_id}: {exc}") from exc
            if not math.isfinite(observed_face) or observed_face <= 0:
                raise ProductionJobError(f"fresh canonical fixed ROI measurement is invalid for image {image_id}")
            observed_values.append(observed_face)
        results.append({
            "image_id": image_id,
            "measurement_kind": measurement_kind,
            "source_preview_sha256": source_sha,
            "observed_measurement": float(statistics.median(observed_values)),
        })
    return results


REFERENCE_FREE_MAX_AUTOMATIC_DELTA_EV = 0.50
REFERENCE_FREE_MAX_TOTAL_DELTA_EV = 1.00


VLD202_RENDERER_CALIBRATION_SAMPLES: tuple[tuple[float, float, float], ...] = (
    (0.5994784235954285, 0.6784195899963379, +0.35),
    (0.6082506179809570, 0.6757431626319885, +0.30),
    (0.6970835626125336, 0.7156122028827667, +0.10),
    (0.6490084528923035, 0.6909455060958862, +0.20),
    (0.5435690283775330, 0.49524158239364624, -0.20),
    (0.5512416362762451, 0.4736078679561615, -0.30),
    (0.5182951092720032, 0.4559866786003113, -0.25),
    (0.6879870593547821, 0.7183455228805542, +0.15),
    (0.7549521923065186, 0.7363607883453369, -0.10),
    (0.8322980403900146, 0.7935922145843506, -0.25),
)

VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES: tuple[tuple[float, float, float], ...] = (
    (0.698673784733, 0.717694163322, +0.10),
    (0.672862768173, 0.712134897709, +0.20),
    (0.671505093575, 0.682137250900, +0.05),
    (0.417326301336, 0.443690985441, +0.10),
    (0.421450197697, 0.446624308825, +0.10),
    (0.600026309490, 0.551611840725, -0.20),
    (0.523843169212, 0.546796083450, +0.10),
    (0.570598423481, 0.498909056187, -0.30),
    (0.465764731169, 0.403921544552, -0.25),
    (0.416451752186, 0.367541968822, -0.20),
    (0.638914525509, 0.649043977261, +0.05),
    (0.701274514198, 0.729284763336, +0.15),
    (0.728180408478, 0.719182729721, -0.05),
    (0.725388228893, 0.716351330280, -0.05),
    (0.763767838478, 0.747052550316, -0.10),
    (0.712113738060, 0.692241549492, -0.10),
    (0.709222018719, 0.689123153687, -0.10),
    (0.705233812332, 0.685193777084, -0.10),
    (0.781482338905, 0.773690164089, -0.05),
    (0.781635284424, 0.773443937302, -0.05),
    (0.630813360214, 0.642718493938, +0.05),
    (0.636346697807, 0.647328615189, +0.05),
    (0.711439251900, 0.721919238567, +0.05),
    (0.872949838638, 0.840959250927, -0.25),
    (0.702348232269, 0.693064391613, -0.05),
)
SCENE_REFERENCE_MAX_AUTOMATIC_DELTA_EV = 1.00


def _reference_free_target_measurement(
    directory: Path,
    image_id: str,
    candidate_id: str,
) -> float:
    target_manifest = load_reference_free_target_candidates(directory)
    candidate = candidate_record(target_manifest, image_id=image_id, candidate_id=candidate_id)
    if float(candidate.get("new_highlight_clip_fraction", 0.0)) > 0.005:
        raise ProductionJobError("REFERENCE_FREE_TARGET_UNSAFE_HIGHLIGHTS")

    manifest = read_manifest(directory)
    by_id = {str(entry.image_id): entry for entry in manifest.entries}
    entry = by_id.get(str(image_id))
    if entry is None:
        raise ProductionJobError(f"reference-free target image {image_id} is missing from manifest")
    baseline_bytes = (directory / entry.preview_path).read_bytes()
    simulated = simulate_display_exposure_jpeg(
        baseline_bytes,
        float(candidate["simulated_display_ev"]),
    )
    baseline_hi, _ = display_clip_metrics(baseline_bytes)
    selected_hi, _ = display_clip_metrics(simulated)
    if max(0.0, selected_hi - baseline_hi) > 0.005:
        raise ProductionJobError("REFERENCE_FREE_TARGET_UNSAFE_HIGHLIGHTS")

    roi_record = _read_json_object(directory / "measurement-rois.json", "measurement ROIs")
    roi_items = roi_record.get("items")
    if not isinstance(roi_items, list):
        raise ProductionJobError("measurement ROI items are invalid")
    roi_item = next((item for item in roi_items if isinstance(item, dict) and str(item.get("image_id")) == str(image_id)), None)
    if roi_item is None:
        raise ProductionJobError("NO_USABLE_MEASUREMENT")
    if roi_item.get("measurement_strategy") == "ROBUST_SCENE_LUMINANCE":
        try:
            return float(measure_robust_scene_luminance(simulated).measurement)
        except InvalidSceneMeasurement as exc:
            raise ProductionJobError(f"reference-free scene target measurement failed: {exc}") from exc
    frozen_rois: list[CanonicalFixedSkinRoi] = []
    face_rois = roi_item.get("face_rois")
    if isinstance(face_rois, list) and face_rois:
        for face_entry in face_rois:
            if not isinstance(face_entry, Mapping) or not isinstance(face_entry.get("roi"), Mapping):
                raise ProductionJobError("frozen target ROI evidence is invalid")
            frozen_rois.append(_deserialize_canonical_fixed_roi(face_entry["roi"]))
    elif isinstance(roi_item.get("roi"), Mapping):
        frozen_rois.append(_deserialize_canonical_fixed_roi(roi_item["roi"]))
    else:
        raise ProductionJobError("NO_USABLE_MEASUREMENT")
    values = [float(measure_canonical_fixed_skin_roi(jpeg_bytes=simulated, roi=roi)) for roi in frozen_rois]
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ProductionJobError("reference-free target measurement is invalid")
    return float(statistics.median(values))


def _validated_semantics_core(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "protocol_version": record.get("protocol_version"),
        "job_id": record.get("job_id"),
        "groups": record.get("groups"),
        "unassigned": record.get("unassigned"),
    }


def _reason_for_group_status(status: str) -> str:
    return {
        "NO_CLEAR_REFERENCE": "NO_CLEAR_REFERENCE",
        "MIXED_LIGHTING": "MIXED_LIGHTING",
        "UNCERTAIN": "SEMANTIC_UNCERTAIN",
    }.get(status, "NO_CLEAR_REFERENCE")


def build_production_plan(
    job_dir: Path | str,
    measurements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one exact deterministic plan from frozen semantics + measurements."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != WAITING_FOR_SEMANTICS or state.get("visual_semantics_runs") != 1:
        raise ProductionJobError("one validated visual-semantics result is required before planning")
    semantics_record = _read_json_object(directory / "visual-semantics.json", "validated visual semantics")
    semantics = validate_visual_semantics(
        _validated_semantics_core(semantics_record),
        job_id=state["job_id"],
        ordered_image_ids=state["ordered_image_ids"],
    )
    selection = _load_production_selection(directory / "selection.json")
    if selection["job_id"] != state["job_id"] or selection["ordered_image_ids"] != state["ordered_image_ids"]:
        raise ProductionJobError("selection identity does not match production job state")
    manifest = read_manifest(directory)
    manifest_by_id = {str(entry.image_id): entry for entry in manifest.entries}
    measurement_record = _normalize_measurement_results(
        directory, state["ordered_image_ids"], measurements
    )
    measurement_by_id = {item["image_id"]: item for item in measurement_record["items"]}
    baseline_by_id = {
        str(photo["id_local"]): float(photo["catalog_exposure2012"])
        for photo in selection["photos"]
    }

    policy = state.get("policy")
    if not isinstance(policy, dict):
        raise ProductionJobError("production job policy is invalid")
    required_policy = {
        "quantum_ev",
        "maximum_delta_ev",
        "minimum_exposure2012",
        "maximum_exposure2012",
    }
    missing_policy = sorted(required_policy - set(policy))
    if missing_policy:
        raise ProductionJobError(f"production job policy missing required value(s): {missing_policy}")
    quantum = _finite_number(policy["quantum_ev"], "policy.quantum_ev")
    max_delta = _finite_number(policy["maximum_delta_ev"], "policy.maximum_delta_ev")
    min_exposure = _finite_number(policy["minimum_exposure2012"], "policy.minimum_exposure2012")
    max_exposure = _finite_number(policy["maximum_exposure2012"], "policy.maximum_exposure2012")
    if quantum <= 0 or max_delta <= 0 or min_exposure > max_exposure:
        raise ProductionJobError("production numeric policy is invalid")

    semantic_by_id: dict[str, dict[str, Any]] = {}
    group_by_id: dict[str, dict[str, Any]] = {}
    for group in semantics["groups"]:
        for member in group["members"]:
            semantic_by_id[member["image_id"]] = member
            group_by_id[member["image_id"]] = group
    unassigned_by_id = {item["image_id"]: item for item in semantics["unassigned"]}

    measurement_strategy_by_id: dict[str, str] = {}
    roi_path = directory / "measurement-rois.json"
    if roi_path.exists():
        roi_record = _read_json_object(roi_path, "measurement strategy evidence")
        roi_entries = roi_record.get("items")
        if isinstance(roi_entries, list):
            for raw_roi in roi_entries:
                if isinstance(raw_roi, Mapping) and raw_roi.get("image_id") is not None:
                    measurement_strategy_by_id[str(raw_roi.get("image_id"))] = str(raw_roi.get("measurement_strategy") or "")

    items: list[dict[str, Any]] = []
    catalog_items: list[dict[str, Any]] = []
    counts = {"WILL_ADJUST": 0, "NO_CHANGE": 0, "UNRESOLVED": 0}

    for image_id in state["ordered_image_ids"]:
        baseline = baseline_by_id[image_id]
        entry = manifest_by_id[image_id]
        baseline_source_sha = entry.source_preview_sha256 or entry.preview_sha256
        common: dict[str, Any] = {
            "image_id": image_id,
            "baseline_exposure2012": baseline,
            "baseline_source_preview_sha256": baseline_source_sha,
            "validated_delta_ev": None,
            "target_exposure2012": None,
        }
        if image_id in unassigned_by_id:
            item = {
                **common,
                "pre_apply_status": "UNRESOLVED",
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": unassigned_by_id[image_id]["reason"],
            }
        else:
            member = semantic_by_id[image_id]
            group = group_by_id[image_id]
            verdict = member["verdict"]
            if verdict == "UNRESOLVED":
                item = {
                    **common,
                    "pre_apply_status": "UNRESOLVED",
                    "reason_class": "PHOTOGRAPHIC",
                    "reason_code": member["reason"],
                }
            elif verdict == "AUTO":
                target_candidate_id = member.get("target_candidate_id")
                if target_candidate_id is not None:
                    measured = measurement_by_id[image_id]
                    if measured["status"] != "MEASURED":
                        item = {
                            **common,
                            "pre_apply_status": "UNRESOLVED",
                            "reason_class": "PHOTOGRAPHIC",
                            "reason_code": "NO_USABLE_MEASUREMENT",
                        }
                    else:
                        try:
                            target_candidate_ids = member.get("acceptable_candidate_ids") or [
                                str(target_candidate_id)
                            ]
                            target_measurements = [
                                _reference_free_target_measurement(
                                    directory, image_id, str(candidate_id)
                                )
                                for candidate_id in target_candidate_ids
                            ]
                            target_measurement = float(statistics.median(target_measurements))
                            desired_total_delta = estimate_renderer_calibrated_delta_ev(
                                calibration_samples=(VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES if measurement_strategy_by_id.get(image_id) == "ROBUST_SCENE_LUMINANCE" else VLD202_RENDERER_CALIBRATION_SAMPLES),
                                baseline_measurement=float(measured["measurement"]),
                                target_measurement=target_measurement,
                                quantum_ev=quantum,
                                max_abs_ev=max_delta,
                            )
                            if abs(float(desired_total_delta)) > REFERENCE_FREE_MAX_TOTAL_DELTA_EV + 1e-12:
                                raise RendererResponseUncertain(
                                    "reference-free target exceeds validated total correction bound"
                                )
                            delta = max(
                                -REFERENCE_FREE_MAX_AUTOMATIC_DELTA_EV,
                                min(REFERENCE_FREE_MAX_AUTOMATIC_DELTA_EV, float(desired_total_delta)),
                            )
                            delta = round(delta / quantum) * quantum
                            delta = round(float(delta), 10)
                        except (ProductionJobError, RendererResponseUncertain, ValueError) as exc:
                            text = str(exc)
                            reason = (
                                "UNSAFE_TARGET_HIGHLIGHTS"
                                if "UNSAFE_HIGHLIGHTS" in text
                                else "RENDER_RESPONSE_UNCERTAIN"
                                if isinstance(exc, RendererResponseUncertain)
                                else "NO_USABLE_MEASUREMENT"
                            )
                            item = {
                                **common,
                                "pre_apply_status": "UNRESOLVED",
                                "reason_class": "SAFETY" if reason == "UNSAFE_TARGET_HIGHLIGHTS" else "PHOTOGRAPHIC",
                                "reason_code": reason,
                            }
                        else:
                            if abs(delta) <= 1e-12:
                                item = {
                                    **common,
                                    "pre_apply_status": "NO_CHANGE",
                                    "validated_delta_ev": 0.0,
                                    "target_exposure2012": baseline,
                                    "reason_class": "PHOTOGRAPHIC",
                                    "reason_code": "REFERENCE_FREE_TARGET_ZERO_DELTA",
                                }
                            else:
                                try:
                                    target = build_absolute_exposure_target(
                                        current_exposure2012=baseline,
                                        validated_delta_ev=delta,
                                        minimum_exposure2012=min_exposure,
                                        maximum_exposure2012=max_exposure,
                                    )
                                except UnresolvedExposureDecision:
                                    item = {
                                        **common,
                                        "pre_apply_status": "UNRESOLVED",
                                        "reason_class": "SAFETY",
                                        "reason_code": "TARGET_EXPOSURE_OUT_OF_BOUNDS",
                                    }
                                else:
                                    item = {
                                        **common,
                                        "pre_apply_status": "WILL_ADJUST",
                                        "validated_delta_ev": delta,
                                        "target_exposure2012": target.target_exposure2012,
                                        "reason_class": "PHOTOGRAPHIC",
                                        "reason_code": "REFERENCE_FREE_VISUAL_TARGET",
                                        "target_candidate_id": str(target_candidate_id),
                                        "acceptable_candidate_ids": [
                                            str(value) for value in target_candidate_ids
                                        ],
                                        "target_measurement": target_measurement,
                                        "desired_total_delta_ev": float(desired_total_delta),
                                    }
                                    catalog_items.append(
                                        {
                                            "image_id": image_id,
                                            "expected_before_exposure2012": baseline,
                                            "target_exposure2012": target.target_exposure2012,
                                            "delta_ev": float(delta),
                                        }
                                    )
                elif group["status"] != "REFERENCE_SELECTED":
                    item = {
                        **common,
                        "pre_apply_status": "UNRESOLVED",
                        "reason_class": "PHOTOGRAPHIC",
                        "reason_code": _reason_for_group_status(group["status"]),
                    }
                else:
                    reference_id = str(group["reference_image_id"])
                    measured = measurement_by_id[image_id]
                    reference = measurement_by_id[reference_id]
                    if measured["status"] != "MEASURED" or reference["status"] != "MEASURED":
                        item = {
                            **common,
                            "pre_apply_status": "UNRESOLVED",
                            "reason_class": "PHOTOGRAPHIC",
                            "reason_code": "NO_USABLE_MEASUREMENT",
                        }
                    else:
                        try:
                            scene_domain = (
                                measurement_strategy_by_id.get(image_id) == "ROBUST_SCENE_LUMINANCE"
                                and measurement_strategy_by_id.get(reference_id) == "ROBUST_SCENE_LUMINANCE"
                            )
                            if scene_domain:
                                delta = estimate_renderer_calibrated_delta_ev(
                                    calibration_samples=VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES,
                                    baseline_measurement=float(measured["measurement"]),
                                    target_measurement=float(reference["measurement"]),
                                    quantum_ev=quantum,
                                    max_abs_ev=max_delta,
                                )
                                if abs(float(delta)) > SCENE_REFERENCE_MAX_AUTOMATIC_DELTA_EV + 1e-12:
                                    raise RendererResponseUncertain(
                                        "scene-reference correction exceeds validated automatic bound"
                                    )
                            else:
                                delta = compute_per_image_delta_ev(
                                    float(reference["measurement"]),
                                    float(measured["measurement"]),
                                    quantum_ev=quantum,
                                    max_abs_ev=max_delta,
                                )
                        except (InvalidMeasurement, RendererResponseUncertain) as exc:
                            reason = (
                                "DELTA_OUT_OF_BOUNDS"
                                if isinstance(exc, RendererResponseUncertain) or "maximum bound" in str(exc)
                                else "NO_USABLE_MEASUREMENT"
                            )
                            item = {
                                **common,
                                "pre_apply_status": "UNRESOLVED",
                                "reason_class": "SAFETY" if reason == "DELTA_OUT_OF_BOUNDS" else "PHOTOGRAPHIC",
                                "reason_code": reason,
                            }
                        else:
                            if abs(delta) <= 1e-12:
                                item = {
                                    **common,
                                    "pre_apply_status": "NO_CHANGE",
                                    "validated_delta_ev": 0.0,
                                    "target_exposure2012": baseline,
                                    "reason_class": "PHOTOGRAPHIC",
                                    "reason_code": "DETERMINISTIC_ZERO_DELTA",
                                }
                            else:
                                try:
                                    target = build_absolute_exposure_target(
                                        current_exposure2012=baseline,
                                        validated_delta_ev=delta,
                                        minimum_exposure2012=min_exposure,
                                        maximum_exposure2012=max_exposure,
                                    )
                                except UnresolvedExposureDecision:
                                    item = {
                                        **common,
                                        "pre_apply_status": "UNRESOLVED",
                                        "reason_class": "SAFETY",
                                        "reason_code": "TARGET_OUT_OF_BOUNDS",
                                    }
                                else:
                                    item = {
                                        **common,
                                        "pre_apply_status": "WILL_ADJUST",
                                        "validated_delta_ev": float(delta),
                                        "target_exposure2012": target.target_exposure2012,
                                        "reason_class": "PHOTOGRAPHIC",
                                        "reason_code": ("DETERMINISTIC_SCENE_REFERENCE_MATCH" if scene_domain else "DETERMINISTIC_REFERENCE_MATCH"),
                                        "reference_image_id": reference_id,
                                        "target_measurement": float(reference["measurement"]),
                                        "baseline_measurement": float(measured["measurement"]),
                                    }
                                    catalog_items.append(
                                        {
                                            "image_id": image_id,
                                            "expected_before_exposure2012": baseline,
                                            "target_exposure2012": target.target_exposure2012,
                                            "delta_ev": float(delta),
                                        }
                                    )
            else:
                raise ProductionJobError(f"unsupported member verdict: {verdict}")
        counts[item["pre_apply_status"]] += 1
        items.append(item)

    if sum(counts.values()) != len(state["ordered_image_ids"]):
        raise ProductionJobError("pre-apply exact accounting invariant failed")
    catalog_plan = {
        "protocol_version": PROTOCOL_VERSION,
        "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_PLAN",
        "job_id": state["job_id"],
        "catalog_exposure_tolerance": 0.01,
        "planned_count": len(catalog_items),
        "items": catalog_items,
    }
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "MINIMAL_PRODUCTION_EXPOSURE_PLAN",
        "job_id": state["job_id"],
        "source_folder": state["source_folder"],
        "ordered_image_ids": list(state["ordered_image_ids"]),
        "counts": {
            "input_count": len(state["ordered_image_ids"]),
            "will_adjust": counts["WILL_ADJUST"],
            "no_change": counts["NO_CHANGE"],
            "unresolved": counts["UNRESOLVED"],
        },
        "items": items,
        "catalog_plan": catalog_plan,
        "numeric_exposure_authority": "DETERMINISTIC_PYTHON",
        "mutation_authority": "NONE",
    }
    _atomic_write_json(directory / "measurement-results.json", measurement_record)
    _atomic_write_json(directory / "exposure-plan.json", result)
    update_production_job_state(
        directory,
        PLAN_READY,
        measurement_results="measurement-results.json",
        exposure_plan="exposure-plan.json",
        plan_counts=result["counts"],
    )
    if not catalog_items:
        final = finalize_zero_mutation_plan(directory)
        result["workflow_state"] = "COMPLETE"
        result["next_action"] = None
        result["final_accounting"] = final
    else:
        result["workflow_state"] = "READY_TO_APPLY"
        result["next_action"] = "APPLY_EXPOSURE"
    return result


def finalize_zero_mutation_plan(job_dir: Path | str) -> dict[str, Any]:
    """Close a valid plan that contains no Catalog mutation items.

    This is both the normal zero-plan terminal path and a bounded recovery seam
    for an already-built PLAN_READY job. It writes final accounting only; it never
    invokes Lightroom, a Catalog writer, or render verification.
    """

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != PLAN_READY:
        raise ProductionJobError(
            f"zero-mutation finalization requires PLAN_READY; state={state['state']}"
        )
    plan = _read_json_object(directory / "exposure-plan.json", "production exposure plan")
    if plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("zero-mutation production plan job_id mismatch")
    if plan.get("ordered_image_ids") != state["ordered_image_ids"]:
        raise ProductionJobError("zero-mutation production plan input identity mismatch")

    catalog_plan = plan.get("catalog_plan")
    if not isinstance(catalog_plan, dict):
        raise ProductionJobError("zero-mutation production plan has no catalog_plan")
    catalog_items = catalog_plan.get("items")
    if catalog_plan.get("planned_count") != 0 or catalog_items != []:
        raise ProductionJobError("zero-mutation finalization requires an empty Catalog plan")

    plan_items = plan.get("items")
    if not isinstance(plan_items, list):
        raise ProductionJobError("zero-mutation production plan items must be an array")
    observed_ids = [
        str(item.get("image_id") or "")
        for item in plan_items
        if isinstance(item, Mapping)
    ]
    if observed_ids != list(state["ordered_image_ids"]) or len(observed_ids) != len(plan_items):
        raise ProductionJobError(
            "zero-mutation production plan must exactly preserve ordered input image IDs"
        )

    final_items: list[dict[str, Any]] = []
    for raw in plan_items:
        assert isinstance(raw, Mapping)
        image_id = _require_nonempty_string(raw.get("image_id"), "zero-mutation plan image_id")
        pre_apply_status = raw.get("pre_apply_status")
        if pre_apply_status not in {"NO_CHANGE", "UNRESOLVED"}:
            raise ProductionJobError(
                f"zero-mutation plan contains non-terminal pre-apply status for image {image_id}: {pre_apply_status!r}"
            )
        baseline = _finite_number(
            raw.get("baseline_exposure2012"),
            f"zero-mutation plan {image_id}.baseline_exposure2012",
        )
        final_items.append(
            {
                "image_id": image_id,
                "final_status": str(pre_apply_status),
                "baseline_exposure2012": baseline,
                "final_exposure2012": baseline,
                "total_delta_ev": 0.0,
                "residual_attempts": 0,
                "reason_class": str(raw.get("reason_class") or "PHOTOGRAPHIC"),
                "reason_code": _require_nonempty_string(
                    raw.get("reason_code"),
                    f"zero-mutation plan {image_id}.reason_code",
                ),
            }
        )

    final = finalize_production_accounting(
        job_id=state["job_id"],
        source_folder=state["source_folder"],
        ordered_image_ids=state["ordered_image_ids"],
        items=final_items,
        output_path=directory / "final-results.json",
    )
    update_production_job_state(
        directory,
        COMPLETE,
        final_results="final-results.json",
        final_counts=final["counts"],
        zero_mutation_terminal=True,
    )
    return final


def confirm_production_catalog_apply(
    job_dir: Path | str,
    evidence_json_path: Path | str,
) -> dict[str, Any]:
    """Confirm exact CatalogApplyBarrier evidence before render verification.

    This function never retries a Catalog write. Any mismatch or non-verified
    item moves the job to NEEDS_ATTENTION so partial/ambiguous mutation cannot be
    hidden as a photographic outcome.
    """

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != PLAN_READY:
        raise ProductionJobError(
            f"Catalog apply evidence can be confirmed only from PLAN_READY; state={state['state']}"
        )
    plan = _read_json_object(directory / "exposure-plan.json", "production exposure plan")
    if plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("production exposure plan job_id mismatch")
    if plan.get("ordered_image_ids") != state["ordered_image_ids"]:
        raise ProductionJobError("production exposure plan input identity mismatch")
    plan_items = plan.get("items")
    if not isinstance(plan_items, list):
        raise ProductionJobError("production exposure plan items must be an array")
    plan_item_ids = [str(item.get("image_id") or "") for item in plan_items if isinstance(item, Mapping)]
    if (
        len(plan_item_ids) != len(state["ordered_image_ids"])
        or len(set(plan_item_ids)) != len(plan_item_ids)
        or set(plan_item_ids) != set(state["ordered_image_ids"])
    ):
        raise ProductionJobError("production exposure plan items must exactly cover input image IDs")
    will_adjust_ids = [
        str(item["image_id"])
        for item in plan_items
        if isinstance(item, Mapping) and item.get("pre_apply_status") == "WILL_ADJUST"
    ]
    catalog_plan = plan.get("catalog_plan")
    if not isinstance(catalog_plan, dict):
        raise ProductionJobError("production exposure plan has no catalog_plan object")
    if catalog_plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("production catalog plan job_id mismatch")
    if catalog_plan.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_PLAN":
        raise ProductionJobError("production catalog plan operation mismatch")
    planned_items = catalog_plan.get("items")
    if not isinstance(planned_items, list):
        raise ProductionJobError("production catalog plan items must be an array")
    if catalog_plan.get("planned_count") != len(planned_items):
        raise ProductionJobError("production catalog plan planned_count mismatch")
    planned_by_id: dict[str, Mapping[str, Any]] = {}
    planned_ids: list[str] = []
    for item in planned_items:
        if not isinstance(item, Mapping):
            raise ProductionJobError("production catalog plan item must be an object")
        image_id = _require_nonempty_string(item.get("image_id"), "catalog plan image_id")
        if image_id in planned_by_id:
            raise ProductionJobError("production catalog plan contains duplicate image IDs")
        planned_by_id[image_id] = item
        planned_ids.append(image_id)
    if planned_ids != will_adjust_ids:
        raise ProductionJobError(
            "production catalog mutation subset must exactly match WILL_ADJUST image IDs"
        )

    evidence = _read_json_object(Path(evidence_json_path), "Catalog apply evidence")
    # Preserve the raw barrier result before deciding whether it is safe to
    # advance. This is recovery evidence, including failure/partial-write cases.
    _atomic_write_json(directory / "apply-result.json", evidence)
    update_production_job_state(
        directory,
        APPLYING_CATALOG,
        apply_result="apply-result.json",
    )

    errors: list[str] = []
    if evidence.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT":
        errors.append("operation mismatch")
    if evidence.get("job_id") != state["job_id"]:
        errors.append("job_id mismatch")
    results = evidence.get("results")
    if not isinstance(results, list):
        errors.append("results must be an array")
        results = []

    observed_ids: list[str] = []
    result_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(results):
        if not isinstance(raw, Mapping):
            errors.append(f"result {index} is not an object")
            continue
        image_id = str(raw.get("image_id") or "")
        observed_ids.append(image_id)
        if image_id in result_by_id:
            errors.append(f"duplicate result image_id {image_id}")
        result_by_id[image_id] = raw

    if (
        len(observed_ids) != len(planned_ids)
        or len(set(observed_ids)) != len(observed_ids)
        or set(observed_ids) != set(planned_ids)
    ):
        errors.append(
            "apply results must exactly cover the planned mutation subset "
            f"(planned={sorted(planned_ids)}, observed={sorted(observed_ids)})"
        )

    try:
        tolerance = _finite_number(
            catalog_plan.get("catalog_exposure_tolerance", 0.01),
            "catalog_plan.catalog_exposure_tolerance",
        )
    except ProductionJobError as exc:
        errors.append(str(exc))
        tolerance = 0.01
    if tolerance < 0:
        errors.append("catalog exposure tolerance must be non-negative")
        tolerance = 0.01
    verified_ids: list[str] = []
    for image_id in planned_ids:
        raw = result_by_id.get(image_id)
        if raw is None:
            continue
        planned = planned_by_id[image_id]
        try:
            result_expected = _finite_number(
                raw.get("expected_before_exposure2012"),
                f"image {image_id}.expected_before_exposure2012",
            )
            result_target = _finite_number(
                raw.get("target_exposure2012"),
                f"image {image_id}.target_exposure2012",
            )
            planned_expected = _finite_number(
                planned.get("expected_before_exposure2012"),
                f"plan {image_id}.expected_before_exposure2012",
            )
            planned_target = _finite_number(
                planned.get("target_exposure2012"),
                f"plan {image_id}.target_exposure2012",
            )
            observed_before = _finite_number(
                raw.get("observed_before_exposure2012"),
                f"image {image_id}.observed_before_exposure2012",
            )
            observed_after = _finite_number(
                raw.get("observed_after_exposure2012"),
                f"image {image_id}.observed_after_exposure2012",
            )
        except ProductionJobError as exc:
            errors.append(str(exc))
            continue
        if abs(result_expected - planned_expected) > 1e-12:
            errors.append(f"image {image_id} expected-before value mismatch")
        if abs(result_target - planned_target) > 1e-12:
            errors.append(f"image {image_id} target value mismatch")
        if abs(observed_before - planned_expected) > tolerance and not _is_target_already_present_result(
            raw,
            observed_before,
            observed_after,
            planned_target,
            tolerance,
        ):
            errors.append(f"image {image_id} observed-before drift exceeds tolerance")
        if raw.get("status") != "APPLIED_VERIFIED":
            errors.append(f"image {image_id} status is {raw.get('status')!r}, not APPLIED_VERIFIED")
            continue
        if abs(observed_after - planned_target) > tolerance:
            errors.append(f"image {image_id} observed-after value is outside target tolerance")
            continue
        verified_ids.append(image_id)

    if errors:
        update_production_job_state(
            directory,
            NEEDS_ATTENTION,
            error="CATALOG_APPLY_EVIDENCE_INVALID",
            apply_result="apply-result.json",
            apply_errors=errors,
        )
        raise ProductionJobError("Catalog apply evidence is not safely confirmable: " + "; ".join(errors))

    update_production_job_state(
        directory,
        VERIFYING_RENDERS,
        apply_result="apply-result.json",
        applied_verified_count=len(verified_ids),
        applied_verified_image_ids=verified_ids,
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": state["job_id"],
        "verified_count": len(verified_ids),
        "verified_image_ids": verified_ids,
        "next_state": VERIFYING_RENDERS,
        "mutation_authority": "NONE",
    }


def _is_target_already_present_result(
    raw: Mapping[str, Any],
    observed_before: float,
    observed_after: float,
    planned_target: float,
    tolerance: float,
) -> bool:
    return (
        raw.get("status") == "APPLIED_VERIFIED"
        and raw.get("verification_mode") == "TARGET_ALREADY_PRESENT"
        and abs(observed_before - planned_target) <= tolerance
        and abs(observed_after - planned_target) <= tolerance
    )


def _validate_fresh_measurement_subset(
    expected_ids: Sequence[str],
    measurements: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    ordered = tuple(str(value) for value in expected_ids)
    observed_ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    required = {
        "image_id",
        "measurement_kind",
        "source_preview_sha256",
        "observed_measurement",
    }
    for index, raw in enumerate(measurements):
        if not isinstance(raw, Mapping):
            raise ProductionJobError(f"fresh measurement {index} must be an object")
        if set(raw) != required:
            raise ProductionJobError(
                f"fresh measurement {index} fields are invalid; expected {sorted(required)}"
            )
        image_id = _require_nonempty_string(raw.get("image_id"), f"fresh measurement {index}.image_id")
        observed_ids.append(image_id)
        measurement_kind = raw.get("measurement_kind")
        if measurement_kind not in {
            "ROBUST_SCENE_LUMINANCE",
            "CANONICAL_FIXED_ROI",
            "CANONICAL_FIXED_ROI_MEDIAN",
        }:
            raise ProductionJobError(
                f"fresh measurement {image_id} must use ROBUST_SCENE_LUMINANCE, CANONICAL_FIXED_ROI, or CANONICAL_FIXED_ROI_MEDIAN; got {measurement_kind!r}"
            )
        source_sha = _require_nonempty_string(
            raw.get("source_preview_sha256"),
            f"fresh measurement {image_id}.source_preview_sha256",
        )
        observed = _finite_number(
            raw.get("observed_measurement"),
            f"fresh measurement {image_id}.observed_measurement",
        )
        if observed <= 0:
            raise ProductionJobError(
                f"fresh measurement {image_id}.observed_measurement must be positive"
            )
        by_id[image_id] = {
            "image_id": image_id,
            "measurement_kind": str(measurement_kind),
            "source_preview_sha256": source_sha,
            "observed_measurement": observed,
        }
    if (
        len(observed_ids) != len(ordered)
        or len(set(observed_ids)) != len(observed_ids)
        or set(observed_ids) != set(ordered)
    ):
        raise ProductionJobError(
            "fresh render measurements must exactly cover the adjusted subset once "
            f"(expected={sorted(ordered)}, observed={sorted(observed_ids)})"
        )
    return by_id


def _validate_render_verification_artifact(
    record: Mapping[str, Any],
    *,
    label: str,
    job_id: str,
    result_kind: str,
    verification_scope: str,
    expected_ids: Sequence[str],
    allowed_statuses: set[str],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(record, Mapping):
        raise ProductionJobError(f"{label} verification artifact must be an object")
    if record.get("protocol_version") != PROTOCOL_VERSION:
        raise ProductionJobError(f"{label} verification protocol_version mismatch")
    if record.get("result_kind") != result_kind:
        raise ProductionJobError(f"{label} verification result_kind mismatch")
    if record.get("job_id") != job_id:
        raise ProductionJobError(f"{label} verification job_id mismatch")
    if record.get("verification_scope") != verification_scope:
        raise ProductionJobError(f"{label} verification scope mismatch")
    items = record.get("items")
    if not isinstance(items, list):
        raise ProductionJobError(f"{label} verification items must be an array")
    expected = [str(value) for value in expected_ids]
    observed: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(items):
        if not isinstance(raw, Mapping):
            raise ProductionJobError(f"{label} verification item {index} must be an object")
        image_id = _require_nonempty_string(raw.get("image_id"), f"{label} verification item {index}.image_id")
        if image_id in by_id:
            raise ProductionJobError(f"{label} verification contains duplicate image_id {image_id}")
        status = raw.get("verification_status")
        if status not in allowed_statuses:
            raise ProductionJobError(f"{label} verification status is invalid for image {image_id}")
        observed.append(image_id)
        by_id[image_id] = raw
    if observed != expected:
        raise ProductionJobError(
            f"{label} verification must exactly cover the expected subset "
            f"(expected={expected}, observed={observed})"
        )
    return by_id


def _final_items_from_plan_and_verification(
    *,
    plan: Mapping[str, Any],
    first_verification: Mapping[str, Any],
    residual_plan: Mapping[str, Any] | None = None,
    residual_verification: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    job_id = _require_nonempty_string(plan.get("job_id"), "production plan.job_id")
    plan_items = plan.get("items")
    if not isinstance(plan_items, list):
        raise ProductionJobError("production plan items must be an array")
    adjusted_ids = [
        str(item.get("image_id") or "")
        for item in plan_items
        if isinstance(item, Mapping) and item.get("pre_apply_status") == "WILL_ADJUST"
    ]
    first_by_id = _validate_render_verification_artifact(
        first_verification,
        label="first render",
        job_id=job_id,
        result_kind="PRODUCTION_ADJUSTED_RENDER_VERIFICATION",
        verification_scope="ADJUSTED_ONLY",
        expected_ids=adjusted_ids,
        allowed_statuses={"SETTLED", "UNRESOLVED", "RESIDUAL_REQUIRED"},
    )
    residual_plan_by_id: dict[str, Mapping[str, Any]] = {}
    residual_by_id: dict[str, Mapping[str, Any]] = {}
    residual_required_ids = [
        image_id
        for image_id in adjusted_ids
        if first_by_id[image_id].get("verification_status") == "RESIDUAL_REQUIRED"
    ]
    if residual_plan is not None:
        if residual_plan.get("job_id") != job_id:
            raise ProductionJobError("residual plan job_id mismatch during final accounting")
        if residual_plan.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_RESIDUAL_PLAN":
            raise ProductionJobError("residual plan operation mismatch during final accounting")
        if residual_plan.get("retry_budget") != 1:
            raise ProductionJobError("residual plan retry budget must remain exactly one")
        residual_items = residual_plan.get("items")
        if not isinstance(residual_items, list) or residual_plan.get("planned_count") != len(residual_items):
            raise ProductionJobError("residual plan count/items are invalid during final accounting")
        residual_ids: list[str] = []
        for index, item in enumerate(residual_items):
            if not isinstance(item, Mapping):
                raise ProductionJobError(f"residual plan item {index} must be an object")
            image_id = _require_nonempty_string(item.get("image_id"), f"residual plan item {index}.image_id")
            if image_id in residual_plan_by_id:
                raise ProductionJobError(f"residual plan contains duplicate image_id {image_id}")
            residual_plan_by_id[image_id] = item
            residual_ids.append(image_id)
        if residual_ids != residual_required_ids:
            raise ProductionJobError(
                "residual plan must exactly match first-verification RESIDUAL_REQUIRED images"
            )
        if residual_verification is None:
            raise ProductionJobError("residual verification artifact is required for residual final accounting")
        residual_by_id = _validate_render_verification_artifact(
            residual_verification,
            label="residual render",
            job_id=job_id,
            result_kind="PRODUCTION_RESIDUAL_RENDER_VERIFICATION",
            verification_scope="RESIDUAL_SUBSET_ONLY",
            expected_ids=residual_ids,
            allowed_statuses={"SETTLED", "UNRESOLVED"},
        )
    elif residual_required_ids:
        raise ProductionJobError("first verification requires residual evidence but no residual plan was supplied")
    final_items: list[dict[str, Any]] = []
    for raw in plan.get("items", []):
        if not isinstance(raw, Mapping):
            raise ProductionJobError("production plan item must be an object")
        image_id = str(raw["image_id"])
        baseline = float(raw["baseline_exposure2012"])
        status = raw["pre_apply_status"]
        if status == "NO_CHANGE":
            final_items.append(
                {
                    "image_id": image_id,
                    "final_status": "NO_CHANGE",
                    "baseline_exposure2012": baseline,
                    "final_exposure2012": baseline,
                    "total_delta_ev": 0.0,
                    "residual_attempts": 0,
                    "reason_class": str(raw.get("reason_class") or "PHOTOGRAPHIC"),
                    "reason_code": str(raw.get("reason_code") or "NO_CHANGE"),
                }
            )
            continue
        if status == "UNRESOLVED":
            final_items.append(
                {
                    "image_id": image_id,
                    "final_status": "UNRESOLVED",
                    "baseline_exposure2012": baseline,
                    "final_exposure2012": baseline,
                    "total_delta_ev": 0.0,
                    "residual_attempts": 0,
                    "reason_class": str(raw.get("reason_class") or "PHOTOGRAPHIC"),
                    "reason_code": str(raw.get("reason_code") or "UNRESOLVED"),
                }
            )
            continue
        if status != "WILL_ADJUST":
            raise ProductionJobError(f"unsupported pre-apply status {status!r}")
        first = first_by_id.get(image_id)
        if first is None:
            raise ProductionJobError(f"missing first verification result for adjusted image {image_id}")
        initial_target = float(raw["target_exposure2012"])
        initial_delta = float(raw["validated_delta_ev"])
        first_status = first.get("verification_status")
        if first_status == "SETTLED":
            final_items.append(
                {
                    "image_id": image_id,
                    "final_status": "ADJUSTED",
                    "baseline_exposure2012": baseline,
                    "final_exposure2012": initial_target,
                    "total_delta_ev": initial_delta,
                    "residual_attempts": 0,
                    "reason_class": "PHOTOGRAPHIC",
                    "reason_code": "SETTLED",
                }
            )
            continue
        if first_status == "UNRESOLVED":
            final_items.append(
                {
                    "image_id": image_id,
                    "final_status": "UNRESOLVED",
                    "baseline_exposure2012": baseline,
                    "final_exposure2012": initial_target,
                    "total_delta_ev": initial_delta,
                    "residual_attempts": 0,
                    "reason_class": str(first.get("reason_class") or "TECHNICAL"),
                    "reason_code": str(first.get("reason_code") or "VERIFY_FAILED"),
                }
            )
            continue
        if first_status != "RESIDUAL_REQUIRED":
            raise ProductionJobError(f"unknown first verification status for image {image_id}")
        residual = residual_by_id.get(image_id)
        residual_plan_item = residual_plan_by_id.get(image_id)
        if residual is None or residual_plan_item is None:
            raise ProductionJobError(f"residual image {image_id} has no terminal residual evidence")
        target2 = float(residual_plan_item["target_exposure2012"])
        total_delta = target2 - baseline
        residual_status = residual.get("verification_status")
        final_items.append(
            {
                "image_id": image_id,
                "final_status": "ADJUSTED" if residual_status == "SETTLED" else "UNRESOLVED",
                "baseline_exposure2012": baseline,
                "final_exposure2012": target2,
                "total_delta_ev": total_delta,
                "residual_attempts": 1,
                "reason_class": (
                    "PHOTOGRAPHIC"
                    if residual_status == "SETTLED"
                    else str(residual.get("reason_class") or "PHOTOGRAPHIC")
                ),
                "reason_code": (
                    "SETTLED_AFTER_RESIDUAL"
                    if residual_status == "SETTLED"
                    else str(residual.get("reason_code") or "RESIDUAL_NOT_SETTLED")
                ),
            }
        )
    return final_items


def verify_production_adjusted_renders(
    job_dir: Path | str,
    fresh_measurements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify only initially adjusted images and build at most one residual plan."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != VERIFYING_RENDERS:
        raise ProductionJobError(
            f"initial render verification requires VERIFYING_RENDERS; state={state['state']}"
        )
    plan = _read_json_object(directory / "exposure-plan.json", "production exposure plan")
    if plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("production exposure plan job_id mismatch during render verification")
    adjusted_items = [
        item
        for item in plan.get("items", [])
        if isinstance(item, Mapping) and item.get("pre_apply_status") == "WILL_ADJUST"
    ]
    adjusted_ids = [str(item["image_id"]) for item in adjusted_items]
    if adjusted_ids != list(state.get("applied_verified_image_ids", adjusted_ids)):
        raise ProductionJobError("adjusted verification subset does not match confirmed Catalog apply")
    fresh_by_id = _validate_fresh_measurement_subset(adjusted_ids, fresh_measurements)
    policy = state.get("policy") or {}
    tolerance = _finite_number(policy.get("residual_tolerance_ev", 0.10), "policy.residual_tolerance_ev")
    quantum = _finite_number(policy.get("quantum_ev", 0.05), "policy.quantum_ev")
    maximum_delta = _finite_number(policy.get("maximum_delta_ev", 3.0), "policy.maximum_delta_ev")
    min_exposure = _finite_number(policy.get("minimum_exposure2012", -5.0), "policy.minimum_exposure2012")
    max_exposure = _finite_number(policy.get("maximum_exposure2012", 5.0), "policy.maximum_exposure2012")
    if tolerance < 0:
        raise ProductionJobError("residual_tolerance_ev must be non-negative")

    verification_items: list[dict[str, Any]] = []
    residual_items: list[dict[str, Any]] = []
    for planned in adjusted_items:
        image_id = str(planned["image_id"])
        fresh = fresh_by_id[image_id]
        baseline_sha = str(planned.get("baseline_source_preview_sha256") or "")
        current_target = float(planned["target_exposure2012"])
        target_measurement = _finite_number(
            planned.get("target_measurement"), f"plan {image_id}.target_measurement"
        )
        if fresh["source_preview_sha256"] == baseline_sha:
            verification_items.append(
                {
                    **fresh,
                    "verification_status": "UNRESOLVED",
                    "reason_class": "TECHNICAL",
                    "reason_code": "RENDER_STALE",
                    "target_measurement": target_measurement,
                    "residual_error_ev": None,
                }
            )
            continue
        observed = float(fresh["observed_measurement"])
        reference_free = (
            planned.get("reason_code") == "REFERENCE_FREE_VISUAL_TARGET"
            or planned.get("target_candidate_id") is not None
        )
        scene_domain = (
            fresh.get("measurement_kind") == "ROBUST_SCENE_LUMINANCE"
            or planned.get("reason_code") == "DETERMINISTIC_SCENE_REFERENCE_MATCH"
        )
        if reference_free or scene_domain:
            try:
                residual_error = estimate_renderer_calibrated_delta_ev(
                    calibration_samples=(
                        VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES
                        if scene_domain else VLD202_RENDERER_CALIBRATION_SAMPLES
                    ),
                    baseline_measurement=observed,
                    target_measurement=target_measurement,
                    quantum_ev=quantum,
                    max_abs_ev=maximum_delta,
                )
            except RendererResponseUncertain as exc:
                verification_items.append(
                    {
                        **fresh,
                        "verification_status": "UNRESOLVED",
                        "reason_class": "SAFETY",
                        "reason_code": "RENDER_RESPONSE_UNCERTAIN",
                        "target_measurement": target_measurement,
                        "residual_error_ev": None,
                        "detail": str(exc),
                    }
                )
                continue
        else:
            residual_error = math.log2(target_measurement / observed)
        if abs(residual_error) <= tolerance + 1e-12:
            verification_items.append(
                {
                    **fresh,
                    "verification_status": "SETTLED",
                    "reason_class": "PHOTOGRAPHIC",
                    "reason_code": "SETTLED",
                    "target_measurement": target_measurement,
                    "residual_error_ev": residual_error,
                }
            )
            continue
        try:
            if reference_free or scene_domain:
                residual_delta = float(residual_error)
                if abs(residual_delta) > REFERENCE_FREE_MAX_AUTOMATIC_DELTA_EV + 1e-12:
                    raise RendererResponseUncertain(
                        "calibrated residual exceeds validated automatic bound"
                    )
            else:
                residual_delta = compute_per_image_delta_ev(
                    target_measurement,
                    observed,
                    quantum_ev=quantum,
                    max_abs_ev=maximum_delta,
                )
            if abs(residual_delta) <= 1e-12:
                raise InvalidMeasurement("residual quantized to zero outside accepted tolerance")
            target2 = build_absolute_exposure_target(
                current_exposure2012=current_target,
                validated_delta_ev=residual_delta,
                minimum_exposure2012=min_exposure,
                maximum_exposure2012=max_exposure,
            )
        except (InvalidMeasurement, UnresolvedExposureDecision, RendererResponseUncertain) as exc:
            verification_items.append(
                {
                    **fresh,
                    "verification_status": "UNRESOLVED",
                    "reason_class": "SAFETY",
                    "reason_code": "RESIDUAL_OUT_OF_BOUNDS",
                    "target_measurement": target_measurement,
                    "residual_error_ev": residual_error,
                    "detail": str(exc),
                }
            )
            continue
        verification_items.append(
            {
                **fresh,
                "verification_status": "RESIDUAL_REQUIRED",
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "RESIDUAL_REQUIRES_FINE_TUNE",
                "target_measurement": target_measurement,
                "residual_error_ev": residual_error,
            }
        )
        residual_items.append(
            {
                "image_id": image_id,
                "expected_before_exposure2012": current_target,
                "target_exposure2012": target2.target_exposure2012,
                "delta_ev": float(residual_delta),
                "target_measurement": target_measurement,
                "prior_source_preview_sha256": fresh["source_preview_sha256"],
            }
        )

    verification = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "PRODUCTION_ADJUSTED_RENDER_VERIFICATION",
        "job_id": state["job_id"],
        "verification_scope": "ADJUSTED_ONLY",
        "residual_tolerance_ev": tolerance,
        "items": verification_items,
    }
    _atomic_write_json(directory / "verification-results.json", verification)

    if residual_items:
        residual_plan = {
            "protocol_version": PROTOCOL_VERSION,
            "operation": "LIGHTROOM_CATALOG_EXPOSURE2012_RESIDUAL_PLAN",
            "job_id": state["job_id"],
            "catalog_exposure_tolerance": 0.01,
            "retry_budget": 1,
            "planned_count": len(residual_items),
            "items": residual_items,
        }
        _atomic_write_json(directory / "residual-plan.json", residual_plan)
        update_production_job_state(
            directory,
            RESIDUAL_PLAN_READY,
            verification_results="verification-results.json",
            residual_plan="residual-plan.json",
            residual_retry_count=0,
            residual_image_ids=[item["image_id"] for item in residual_items],
        )
        return {
            "protocol_version": PROTOCOL_VERSION,
            "job_id": state["job_id"],
            "owner_state": "VERIFYING",
            "next_action": "FINE_TUNE_RESIDUAL",
            "residual_planned_count": len(residual_items),
            "residual_image_ids": [item["image_id"] for item in residual_items],
            "mutation_authority": "NONE",
        }

    final_items = _final_items_from_plan_and_verification(
        plan=plan,
        first_verification=verification,
    )
    final = finalize_production_accounting(
        job_id=state["job_id"],
        source_folder=state["source_folder"],
        ordered_image_ids=state["ordered_image_ids"],
        items=final_items,
        output_path=directory / "final-results.json",
    )
    update_production_job_state(
        directory,
        COMPLETE,
        verification_results="verification-results.json",
        final_results="final-results.json",
        final_counts=final["counts"],
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": state["job_id"],
        "owner_state": "COMPLETE",
        "next_action": None,
        "residual_planned_count": 0,
        "residual_image_ids": [],
        "final_accounting": final,
        "mutation_authority": "NONE",
    }


def confirm_production_residual_apply(
    job_dir: Path | str,
    evidence_json_path: Path | str,
) -> dict[str, Any]:
    """Confirm the one permitted targeted residual Catalog apply subset."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != RESIDUAL_PLAN_READY:
        raise ProductionJobError(
            f"residual Catalog apply evidence requires RESIDUAL_PLAN_READY; state={state['state']}"
        )
    if int(state.get("residual_retry_count", 0)) != 0:
        raise ProductionJobError("residual retry budget is already consumed")
    residual_plan = _read_json_object(directory / "residual-plan.json", "residual plan")
    if residual_plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("residual plan job_id mismatch")
    if residual_plan.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_RESIDUAL_PLAN":
        raise ProductionJobError("residual plan operation mismatch")
    if residual_plan.get("retry_budget") != 1:
        raise ProductionJobError("residual retry budget must remain exactly one")
    items = residual_plan.get("items")
    if not isinstance(items, list) or residual_plan.get("planned_count") != len(items):
        raise ProductionJobError("residual plan count/items are invalid")
    planned_by_id = {str(item["image_id"]): item for item in items if isinstance(item, Mapping)}
    planned_ids = [str(item["image_id"]) for item in items if isinstance(item, Mapping)]
    if len(planned_by_id) != len(planned_ids):
        raise ProductionJobError("residual plan contains duplicate image IDs")
    expected_residual_ids = [str(value) for value in state.get("residual_image_ids", [])]
    if planned_ids != expected_residual_ids:
        raise ProductionJobError(
            "residual plan subset must exactly match the verified residual image subset"
        )
    if any(image_id not in set(state["ordered_image_ids"]) for image_id in planned_ids):
        raise ProductionJobError("residual plan contains an image outside production inputs")

    evidence = _read_json_object(Path(evidence_json_path), "residual Catalog apply evidence")
    _atomic_write_json(directory / "residual-apply-result.json", evidence)
    update_production_job_state(
        directory,
        APPLYING_RESIDUAL,
        residual_apply_result="residual-apply-result.json",
        residual_retry_count=1,
    )
    errors: list[str] = []
    if evidence.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT":
        errors.append("operation mismatch")
    if evidence.get("job_id") != state["job_id"]:
        errors.append("job_id mismatch")
    results = evidence.get("results")
    if not isinstance(results, list):
        errors.append("results must be an array")
        results = []
    result_by_id: dict[str, Mapping[str, Any]] = {}
    observed_ids: list[str] = []
    for raw in results:
        if not isinstance(raw, Mapping):
            errors.append("result is not an object")
            continue
        image_id = str(raw.get("image_id") or "")
        observed_ids.append(image_id)
        if image_id in result_by_id:
            errors.append(f"duplicate result image_id {image_id}")
        result_by_id[image_id] = raw
    if (
        len(observed_ids) != len(planned_ids)
        or len(set(observed_ids)) != len(observed_ids)
        or set(observed_ids) != set(planned_ids)
    ):
        errors.append("residual apply results must exactly cover the residual planned subset")
    try:
        tolerance = _finite_number(
            residual_plan.get("catalog_exposure_tolerance", 0.01),
            "residual_plan.catalog_exposure_tolerance",
        )
    except ProductionJobError as exc:
        errors.append(str(exc))
        tolerance = 0.01
    if tolerance < 0:
        errors.append("residual catalog exposure tolerance must be non-negative")
        tolerance = 0.01
    verified: list[str] = []
    for image_id in planned_ids:
        raw = result_by_id.get(image_id)
        planned = planned_by_id[image_id]
        if raw is None:
            continue
        try:
            expected = _finite_number(
                raw.get("expected_before_exposure2012"),
                f"residual image {image_id}.expected_before_exposure2012",
            )
            target = _finite_number(
                raw.get("target_exposure2012"),
                f"residual image {image_id}.target_exposure2012",
            )
            planned_expected = _finite_number(
                planned.get("expected_before_exposure2012"),
                f"residual plan {image_id}.expected_before_exposure2012",
            )
            planned_target = _finite_number(
                planned.get("target_exposure2012"),
                f"residual plan {image_id}.target_exposure2012",
            )
            observed_before = _finite_number(
                raw.get("observed_before_exposure2012"),
                f"residual image {image_id}.observed_before_exposure2012",
            )
            observed_after = _finite_number(
                raw.get("observed_after_exposure2012"),
                f"residual image {image_id}.observed_after_exposure2012",
            )
        except ProductionJobError as exc:
            errors.append(str(exc))
            continue
        if abs(expected - planned_expected) > 1e-12:
            errors.append(f"image {image_id} expected-before mismatch")
        if abs(target - planned_target) > 1e-12:
            errors.append(f"image {image_id} target mismatch")
        if abs(observed_before - planned_expected) > tolerance and not _is_target_already_present_result(
            raw,
            observed_before,
            observed_after,
            planned_target,
            tolerance,
        ):
            errors.append(f"image {image_id} observed-before drift exceeds tolerance")
        if raw.get("status") != "APPLIED_VERIFIED":
            errors.append(f"image {image_id} is not APPLIED_VERIFIED")
            continue
        if abs(observed_after - planned_target) > tolerance:
            errors.append(f"image {image_id} observed-after is outside target tolerance")
            continue
        verified.append(image_id)
    if errors:
        update_production_job_state(
            directory,
            NEEDS_ATTENTION,
            error="RESIDUAL_CATALOG_APPLY_EVIDENCE_INVALID",
            residual_apply_errors=errors,
        )
        raise ProductionJobError(
            "Residual Catalog apply evidence is not safely confirmable: " + "; ".join(errors)
        )
    update_production_job_state(
        directory,
        VERIFYING_RESIDUAL,
        residual_verified_image_ids=verified,
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": state["job_id"],
        "verified_count": len(verified),
        "verified_image_ids": verified,
        "next_state": VERIFYING_RESIDUAL,
        "mutation_authority": "NONE",
    }


def verify_production_residual_renders(
    job_dir: Path | str,
    fresh_measurements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Second/final render verification. No additional retry can be created."""

    directory = Path(job_dir)
    state = load_production_job_state(directory)
    if state["state"] != VERIFYING_RESIDUAL:
        raise ProductionJobError(
            f"residual render verification requires VERIFYING_RESIDUAL; state={state['state']}"
        )
    if int(state.get("residual_retry_count", 0)) != 1:
        raise ProductionJobError("residual retry must be consumed exactly once before final verification")
    plan = _read_json_object(directory / "exposure-plan.json", "production exposure plan")
    first = _read_json_object(directory / "verification-results.json", "first render verification")
    residual_plan = _read_json_object(directory / "residual-plan.json", "residual plan")
    if plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("production exposure plan job_id mismatch during residual verification")
    if first.get("job_id") != state["job_id"]:
        raise ProductionJobError("first render verification job_id mismatch")
    if residual_plan.get("job_id") != state["job_id"]:
        raise ProductionJobError("residual plan job_id mismatch during residual verification")
    if residual_plan.get("operation") != "LIGHTROOM_CATALOG_EXPOSURE2012_RESIDUAL_PLAN":
        raise ProductionJobError("residual plan operation mismatch during residual verification")
    if residual_plan.get("retry_budget") != 1:
        raise ProductionJobError("residual retry budget must remain exactly one during residual verification")
    residual_items = residual_plan.get("items")
    if not isinstance(residual_items, list) or residual_plan.get("planned_count") != len(residual_items):
        raise ProductionJobError("residual plan count/items are invalid during residual verification")
    residual_ids: list[str] = []
    seen_residual_ids: set[str] = set()
    for index, item in enumerate(residual_items):
        if not isinstance(item, Mapping):
            raise ProductionJobError(f"residual plan item {index} must be an object")
        image_id = _require_nonempty_string(item.get("image_id"), f"residual plan item {index}.image_id")
        if image_id in seen_residual_ids:
            raise ProductionJobError(f"residual plan contains duplicate image_id {image_id}")
        seen_residual_ids.add(image_id)
        residual_ids.append(image_id)
        _require_nonempty_string(
            item.get("prior_source_preview_sha256"),
            f"residual plan {image_id}.prior_source_preview_sha256",
        )
    confirmed_ids = state.get("residual_verified_image_ids")
    if not isinstance(confirmed_ids, list):
        raise ProductionJobError("residual_verified_image_ids is required before final residual verification")
    if residual_ids != [str(value) for value in confirmed_ids]:
        raise ProductionJobError("final residual verification subset does not match confirmed residual apply")
    adjusted_ids = [
        str(item.get("image_id") or "")
        for item in plan.get("items", [])
        if isinstance(item, Mapping) and item.get("pre_apply_status") == "WILL_ADJUST"
    ]
    _validate_render_verification_artifact(
        first,
        label="first render",
        job_id=state["job_id"],
        result_kind="PRODUCTION_ADJUSTED_RENDER_VERIFICATION",
        verification_scope="ADJUSTED_ONLY",
        expected_ids=adjusted_ids,
        allowed_statuses={"SETTLED", "UNRESOLVED", "RESIDUAL_REQUIRED"},
    )
    fresh_by_id = _validate_fresh_measurement_subset(residual_ids, fresh_measurements)
    tolerance = _finite_number(
        (state.get("policy") or {}).get("residual_tolerance_ev", 0.10),
        "policy.residual_tolerance_ev",
    )
    original_plan_by_id = {
        str(item.get("image_id")): item
        for item in plan.get("items", [])
        if isinstance(item, Mapping)
    }
    quantum = _finite_number(
        (state.get("policy") or {}).get("quantum_ev", 0.05),
        "policy.quantum_ev",
    )
    maximum_delta = _finite_number(
        (state.get("policy") or {}).get("maximum_delta_ev", 3.0),
        "policy.maximum_delta_ev",
    )
    results: list[dict[str, Any]] = []
    for planned in residual_items:
        image_id = str(planned["image_id"])
        fresh = fresh_by_id[image_id]
        target_measurement = _finite_number(
            planned.get("target_measurement"), f"residual plan {image_id}.target_measurement"
        )
        if fresh["source_preview_sha256"] == str(planned.get("prior_source_preview_sha256") or ""):
            results.append(
                {
                    **fresh,
                    "verification_status": "UNRESOLVED",
                    "reason_class": "TECHNICAL",
                    "reason_code": "RENDER_STALE",
                    "target_measurement": target_measurement,
                    "residual_error_ev": None,
                }
            )
            continue
        original = original_plan_by_id.get(image_id, {})
        reference_free = (
            original.get("reason_code") == "REFERENCE_FREE_VISUAL_TARGET"
            or original.get("target_candidate_id") is not None
        )
        scene_domain = (
            fresh.get("measurement_kind") == "ROBUST_SCENE_LUMINANCE"
            or original.get("reason_code") == "DETERMINISTIC_SCENE_REFERENCE_MATCH"
        )
        if reference_free or scene_domain:
            try:
                residual_error = estimate_renderer_calibrated_delta_ev(
                    calibration_samples=(
                        VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES
                        if scene_domain else VLD202_RENDERER_CALIBRATION_SAMPLES
                    ),
                    baseline_measurement=float(fresh["observed_measurement"]),
                    target_measurement=target_measurement,
                    quantum_ev=quantum,
                    max_abs_ev=maximum_delta,
                )
            except RendererResponseUncertain as exc:
                results.append(
                    {
                        **fresh,
                        "verification_status": "UNRESOLVED",
                        "reason_class": "SAFETY",
                        "reason_code": "RENDER_RESPONSE_UNCERTAIN",
                        "target_measurement": target_measurement,
                        "residual_error_ev": None,
                        "detail": str(exc),
                    }
                )
                continue
        else:
            residual_error = math.log2(target_measurement / float(fresh["observed_measurement"]))
        settled = abs(residual_error) <= tolerance + 1e-12
        results.append(
            {
                **fresh,
                "verification_status": "SETTLED" if settled else "UNRESOLVED",
                "reason_class": "PHOTOGRAPHIC",
                "reason_code": "SETTLED" if settled else "RESIDUAL_NOT_SETTLED",
                "target_measurement": target_measurement,
                "residual_error_ev": residual_error,
            }
        )
    verification = {
        "protocol_version": PROTOCOL_VERSION,
        "result_kind": "PRODUCTION_RESIDUAL_RENDER_VERIFICATION",
        "job_id": state["job_id"],
        "verification_scope": "RESIDUAL_SUBSET_ONLY",
        "retry_budget_exhausted": True,
        "items": results,
    }
    _atomic_write_json(directory / "residual-verification-results.json", verification)
    final_items = _final_items_from_plan_and_verification(
        plan=plan,
        first_verification=first,
        residual_plan=residual_plan,
        residual_verification=verification,
    )
    final = finalize_production_accounting(
        job_id=state["job_id"],
        source_folder=state["source_folder"],
        ordered_image_ids=state["ordered_image_ids"],
        items=final_items,
        output_path=directory / "final-results.json",
    )
    update_production_job_state(
        directory,
        COMPLETE,
        residual_verification_results="residual-verification-results.json",
        final_results="final-results.json",
        final_counts=final["counts"],
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "job_id": state["job_id"],
        "owner_state": "COMPLETE",
        "next_action": None,
        "final_accounting": final,
        "retry_budget_exhausted": True,
        "mutation_authority": "NONE",
    }
