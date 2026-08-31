"""Lightroom-facing confirmation CLI for iterative Catalog Exposure2012 applies."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from lr_ai_exposure.config import load_config
from lr_ai_exposure.session import (
    SessionError,
    load_session,
    resolve_session_dir,
    write_session_state,
)
from lr_ai_exposure.session_lifecycle import confirm_session_apply


def _pass_dir_for(session_dir: Path, pass_number: int, pass_id: str) -> Path:
    return session_dir / "passes" / f"{pass_number:04d}-{pass_id}"


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise SessionError(f"{label} not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise SessionError(f"{label} must be a JSON object")
    return value


def _validate_catalog_result_ready(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
    apply_result_path: Path | str,
) -> dict[str, Any]:
    """Fail closed unless every planned Catalog mutation is observed at target.

    This gate runs before ``confirm_session_apply`` so a Lightroom timing or
    technical failure cannot be reclassified as a photographic REVIEW and
    cannot accidentally converge the session.
    """
    runtime_path = Path(runtime_directory).resolve()
    session_dir = resolve_session_dir(runtime_path, session_id)
    session_state = load_session(session_dir)
    if pass_number < 1 or pass_number > len(session_state.passes):
        raise SessionError(f"Pass number {pass_number} not found in session {session_id}")

    pass_id = session_state.passes[pass_number - 1]
    pass_dir = _pass_dir_for(session_dir, pass_number, pass_id)
    plan = _read_json_object(pass_dir / "catalog-apply-plan.json", "Catalog apply plan")
    result = _read_json_object(Path(apply_result_path).resolve(), "Catalog apply result")

    if (
        plan.get("session_id") != session_id
        or plan.get("pass_id") != pass_id
        or int(plan.get("pass_number", -1)) != pass_number
    ):
        raise SessionError("Catalog apply plan lineage mismatch")
    if (
        result.get("session_id") != session_id
        or result.get("pass_id") != pass_id
        or int(result.get("pass_number", -1)) != pass_number
    ):
        raise SessionError("Catalog apply result lineage mismatch")

    planned_items = plan.get("items", [])
    result_items = result.get("results", [])
    if not isinstance(planned_items, list) or not isinstance(result_items, list):
        raise SessionError("Catalog apply plan/result items must be arrays")

    planned: dict[str, dict[str, Any]] = {}
    for item in planned_items:
        if not isinstance(item, dict):
            raise SessionError("Catalog apply plan contains a non-object item")
        image_id = str(item.get("image_id", ""))
        if not image_id or image_id in planned:
            raise SessionError("Catalog apply plan has missing or duplicate image IDs")
        planned[image_id] = item

    observed: dict[str, dict[str, Any]] = {}
    for item in result_items:
        if not isinstance(item, dict):
            raise SessionError("Catalog apply result contains a non-object item")
        image_id = str(item.get("image_id", ""))
        if not image_id or image_id in observed:
            raise SessionError("Catalog apply result has missing or duplicate image IDs")
        observed[image_id] = item

    if set(observed) != set(planned):
        raise SessionError("Catalog apply result image set does not exactly match apply plan")

    tolerance = float(plan.get("catalog_exposure_tolerance", 0.01))
    failures: list[tuple[str, str]] = []
    for image_id, planned_item in planned.items():
        result_item = observed[image_id]
        status = str(result_item.get("status", "MISSING_STATUS"))
        target = planned_item.get("target_exposure2012")
        observed_after = result_item.get("observed_after_exposure2012")
        target_ok = (
            isinstance(target, (int, float))
            and not isinstance(target, bool)
            and isinstance(observed_after, (int, float))
            and not isinstance(observed_after, bool)
            and abs(float(observed_after) - float(target)) <= tolerance
        )
        if status != "APPLIED_VERIFIED" or not target_ok:
            failures.append((image_id, status))

    if failures:
        counts = Counter(status for _, status in failures)
        summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
        examples = ", ".join(image_id for image_id, _ in failures[:8])
        raise SessionError(
            "Catalog apply is not fully verified; session state was not changed. "
            f"Failures: {summary}. Example image IDs: {examples}. "
            "Run Import / Apply AI Results again; the Catalog apply is absolute-target "
            "and retry-safe."
        )
    return result


def _recover_prior_failed_confirmation(
    runtime_directory: Path | str,
    session_id: str,
    pass_number: int,
) -> list[str]:
    """Repair state written by the pre-WO-039 confirmation bug.

    Older confirmation code converted technical Catalog verification failures to
    photographic REVIEW and could mark the session converged. Recovery is
    permitted only for IDs explicitly recorded in that pass's
    ``failed_image_ids`` evidence and only when no history entry for the same
    pass was committed.
    """
    runtime_path = Path(runtime_directory).resolve()
    session_dir = resolve_session_dir(runtime_path, session_id)
    session_state = load_session(session_dir)
    if pass_number < 1 or pass_number > len(session_state.passes):
        raise SessionError(f"Pass number {pass_number} not found in session {session_id}")

    pass_id = session_state.passes[pass_number - 1]
    pass_dir = _pass_dir_for(session_dir, pass_number, pass_id)
    evidence_path = pass_dir / "catalog-apply-evidence.json"
    if not evidence_path.is_file():
        return []

    evidence = _read_json_object(evidence_path, "Catalog apply evidence")
    if (
        evidence.get("session_id") != session_id
        or evidence.get("pass_id") != pass_id
        or int(evidence.get("pass_number", -1)) != pass_number
    ):
        raise SessionError("Existing Catalog apply evidence lineage mismatch")

    failed_ids = evidence.get("failed_image_ids", [])
    if not isinstance(failed_ids, list) or not failed_ids:
        return []

    recovered: list[str] = []
    for raw_id in failed_ids:
        image_id = str(raw_id)
        image = session_state.images.get(image_id)
        if image is None:
            raise SessionError(f"Failed Catalog apply evidence references unknown image {image_id}")
        if any(history.pass_id == pass_id for history in image.history):
            continue
        if image.status == "REVIEW":
            image.status = "PENDING"
            recovered.append(image_id)

    if recovered:
        session_state.is_converged = False
        write_session_state(session_dir, session_state)
    return recovered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lr-ai-exposure-catalog-confirm")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--apply-result", type=Path, required=True)
    parser.add_argument("--bridge-result", type=Path, required=True)
    args = parser.parse_args(argv)

    root = Path.cwd()
    settings = load_config(root)
    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    try:
        _validate_catalog_result_ready(
            runtime_directory=runtime_dir,
            session_id=args.session_id,
            pass_number=args.pass_number,
            apply_result_path=args.apply_result,
        )
        recovered_ids = _recover_prior_failed_confirmation(
            runtime_directory=runtime_dir,
            session_id=args.session_id,
            pass_number=args.pass_number,
        )
        result = confirm_session_apply(
            runtime_directory=runtime_dir,
            session_id=args.session_id,
            pass_number=args.pass_number,
            apply_result_path=args.apply_result,
        )
        payload = {
            "protocol_version": "1.1",
            "status": "ok",
            "recovered_failed_confirmation_ids": recovered_ids,
            **result,
        }
        exit_code = 0
    except Exception as exc:
        payload = {
            "protocol_version": "1.1",
            "status": "error",
            "session_id": args.session_id,
            "pass_number": args.pass_number,
            "error": str(exc),
        }
        exit_code = 1

    args.bridge_result.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.bridge_result.with_suffix(args.bridge_result.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(args.bridge_result)
    print(json.dumps(payload, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
