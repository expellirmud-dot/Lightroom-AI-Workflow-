"""Seed deterministic manual decisions for a bounded Lightroom workflow test.

This utility does NOT call an AI provider and does NOT touch Lightroom. It only
writes manual_app decision JSON files into the currently prepared pass so the
WO-035 Prepare -> WAITING_FOR_AI -> Resume mechanics can be exercised.

Default mode is PASS for every FOUND preview. Use --mode one-adjust to request
one small Exposure2012 adjustment on the first FOUND image while all other
images PASS. Existing/frozen/applied passes fail closed unless explicitly
re-seeding raw decision files with --force.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class LiveTestSeedError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LiveTestSeedError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LiveTestSeedError(f"Expected a JSON object at {path}")
    return value


def _decision(image_id: str, *, adjust: bool, delta_ev: float) -> dict[str, Any]:
    action = "ADJUST" if adjust else "PASS"
    return {
        "image_id": image_id,
        "action": action,
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": delta_ev if adjust else 0.0,
        "confidence": 0.99,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": "WO-036 deterministic workflow-mechanics fixture",
        "scene_rationale": "No scene judgment performed; AI quality testing is deferred",
        "scene_group_id": "live-test-fixture",
        "reason": "Synthetic manual_app decision for bounded Lightroom workflow validation",
    }


def seed_decisions(
    pointer_path: Path,
    *,
    mode: str = "pass-all",
    delta_ev: float = 0.10,
    force: bool = False,
) -> dict[str, Any]:
    if mode not in {"pass-all", "one-adjust"}:
        raise LiveTestSeedError(f"Unsupported mode: {mode}")
    if not 0.0 < abs(delta_ev) <= 0.25:
        raise LiveTestSeedError("delta_ev must be non-zero and no larger than 0.25 EV")

    pointer = _read_json(pointer_path)
    pass_dir_raw = pointer.get("pass_dir")
    if not isinstance(pass_dir_raw, str) or not pass_dir_raw:
        raise LiveTestSeedError("latest-session pointer has no valid pass_dir")
    pass_dir = Path(pass_dir_raw)

    frozen_path = pass_dir / "ai-decisions.json"
    applied_path = pass_dir / "catalog-apply-evidence.json"
    if frozen_path.exists():
        raise LiveTestSeedError(f"Pass already has frozen AI decisions: {frozen_path}")
    if applied_path.exists():
        raise LiveTestSeedError(f"Pass already has Catalog apply evidence: {applied_path}")

    manifest = _read_json(pass_dir / "manifest.json")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise LiveTestSeedError("manifest.json has no entries list")

    found_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("extraction_status") == "FOUND":
            image_id = str(entry.get("image_id") or "")
            if not image_id:
                raise LiveTestSeedError("FOUND manifest entry has no image_id")
            found_ids.append(image_id)

    if not found_ids:
        raise LiveTestSeedError("Prepared pass contains no FOUND previews")
    if len(set(found_ids)) != len(found_ids):
        raise LiveTestSeedError("Prepared manifest contains duplicate FOUND image_id values")

    decisions_dir = pass_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    existing = [decisions_dir / f"{image_id}.json" for image_id in found_ids]
    existing = [path for path in existing if path.exists()]
    if existing and not force:
        raise LiveTestSeedError(
            "Decision files already exist; refusing to overwrite without --force: "
            + ", ".join(str(p.name) for p in existing[:5])
        )

    adjusted_id: str | None = found_ids[0] if mode == "one-adjust" else None
    for image_id in found_ids:
        payload = _decision(
            image_id,
            adjust=image_id == adjusted_id,
            delta_ev=float(delta_ev),
        )
        path = decisions_dir / f"{image_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "session_id": pointer.get("session_id"),
        "pass_number": pointer.get("pass_number"),
        "pass_dir": str(pass_dir),
        "mode": mode,
        "decision_count": len(found_ids),
        "adjusted_image_id": adjusted_id,
        "delta_ev": float(delta_ev) if adjusted_id else 0.0,
    }


def _default_pointer(repo_root: Path) -> Path:
    return repo_root / "runtime" / "staging" / "latest-session.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--pointer", type=Path, default=None)
    parser.add_argument("--mode", choices=["pass-all", "one-adjust"], default="pass-all")
    parser.add_argument("--delta-ev", type=float, default=0.10)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    pointer = args.pointer or _default_pointer(args.repo_root)
    try:
        result = seed_decisions(
            pointer,
            mode=args.mode,
            delta_ev=args.delta_ev,
            force=args.force,
        )
    except LiveTestSeedError as exc:
        print(f"LIVE_TEST_SEED_BLOCKED: {exc}")
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
