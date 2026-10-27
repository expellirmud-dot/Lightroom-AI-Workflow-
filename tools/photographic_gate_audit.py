#!/usr/bin/env python3
"""Read-only audit of exposure-review evidence; never writes Lightroom or XMP.

This validates review coverage/conflicts. It DOES NOT judge photographs,
calculate exposure EV, or certify photographic quality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class EvidenceError(ValueError):
    pass


_EXPECTED = {
    "REVIEW_TOO_BRIGHT_POSSIBLE": "DARKEN",
    "REVIEW_TOO_DARK_POSSIBLE": "BRIGHTEN",
}


def audit_exposure_evidence(run: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(run, dict) or not isinstance(review, dict):
        raise EvidenceError("Both evidence documents must be JSON objects.")
    sample_count = run.get("sample_photos")
    counts = run.get("worker_verdict_counts")
    flags = run.get("nexus_review_flags")
    items = review.get("items")
    if type(sample_count) is not int or sample_count <= 0:
        raise EvidenceError("sample_photos must be a positive integer.")
    if not isinstance(counts, dict) or not counts:
        raise EvidenceError("worker_verdict_counts is missing.")
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise EvidenceError("Worker verdict counts must be non-negative integers.")
    if sum(counts.values()) != sample_count:
        raise EvidenceError("Worker verdict coverage does not match sample count.")
    if not isinstance(flags, list) or not isinstance(items, list):
        raise EvidenceError("Review flags and independent review items must be arrays.")

    reviews_by_number: dict[int, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or type(item.get("n")) is not int:
            raise EvidenceError("Invalid independent review item.")
        n = item["n"]
        if n in reviews_by_number:
            raise EvidenceError("Duplicate independent review number.")
        reviews_by_number[n] = item

    checked: list[dict[str, Any]] = []
    seen_flags: set[int] = set()
    for flag in flags:
        if not isinstance(flag, dict) or type(flag.get("n")) is not int:
            raise EvidenceError("Invalid review flag.")
        n = flag["n"]
        if n in seen_flags:
            raise EvidenceError("Duplicate review flag.")
        seen_flags.add(n)
        expected = _EXPECTED.get(flag.get("verdict"))
        if expected is None:
            continue  # Unrecognized flags never generate positive truth.
        review_item = reviews_by_number.get(n)
        if review_item is None:
            raise EvidenceError(f"Strong review flag {n} lacks independent full-size review.")
        if str(review_item.get("photo")) != str(flag.get("stem")):
            raise EvidenceError(f"Review identity mismatch for item {n}.")
        if review_item.get("direction_gate") != expected:
            raise EvidenceError(f"Review direction mismatch for item {n}.")
        checked.append({"n": n, "photo": str(flag["stem"]), "direction": expected})

    all_keep = counts.get("KEEP", 0) == sample_count
    reasons: list[str] = []
    if all_keep and checked:
        reasons.append("ALL_KEEP_CONTRADICTS_INDEPENDENT_REVIEW")
    owner_truth = (
        run.get("fresh_photographer_truth_for_sample") is True
        and review.get("owner_photographic_acceptance") is True
    )
    if not owner_truth:
        reasons.append("PHOTOGRAPHER_ACCEPTANCE_MISSING")

    # This is an advisory gate, never a mutation authorization or PASS for imagery.
    return {
        "status": "BLOCKED_PHOTOGRAPHIC_PROMOTION" if reasons else "NO_CONFLICT_FOUND_OWNER_EVIDENCE_RECORDED",
        "sample_count": sample_count,
        "worker_keep_count": counts.get("KEEP", 0),
        "independent_fullsize_reviewed": len(items),
        "confirmed_review_conflicts": checked,
        "reasons": reasons,
        "numeric_ev_authority": "NONE",
        "catalog_xmp_mutation_authority": "NONE",
        "photographic_quality_certified_by_script": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Frozen run final-result.json")
    parser.add_argument("--review", required=True, type=Path, help="Frozen fullsize-review-progress.json")
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        review = json.loads(args.review.read_text(encoding="utf-8"))
        result = audit_exposure_evidence(run, review)
    except (EvidenceError, OSError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_EVIDENCE", "reason": str(exc)}))
        return 3
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if result["reasons"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
