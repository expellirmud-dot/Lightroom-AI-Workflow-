"""AI Decision Contract and Mock Judge for lr_ai_exposure.

Implements WO-009: Validates exposure decisions and provides a deterministic
mock judge for offline and dry-run execution.
"""

from __future__ import annotations

from typing import Any, Mapping

from lr_ai_exposure.job import Manifest
from lr_ai_exposure.models import ImageDecision


class DecisionError(ValueError):
    """Raised when an AI decision violates the schema or limits."""


def clamp_ev(delta_ev: float, maximum_delta_ev: float) -> float:
    """Clamp delta_ev to [-maximum_delta_ev, maximum_delta_ev]."""
    if maximum_delta_ev <= 0:
        raise ValueError("maximum_delta_ev must be positive")
    return max(-maximum_delta_ev, min(maximum_delta_ev, float(delta_ev)))


def parse_and_validate_decision(
    raw: Mapping[str, Any],
    expected_image_id: str,
    maximum_delta_ev: float,
    minimum_apply_confidence: float,
) -> ImageDecision:
    """Parse a raw decision dict and validate against limits.

    Raises DecisionError if the decision is malformed, missing required fields,
    or belongs to the wrong image ID.
    """
    if not isinstance(raw, dict):
        raise DecisionError("Decision must be a dictionary")

    # Required fields
    for field in ("image_id", "delta_ev", "confidence"):
        if field not in raw:
            raise DecisionError(f"Missing required field: {field!r}")

    image_id = raw["image_id"]
    if image_id != expected_image_id:
        raise DecisionError(
            f"Image ID mismatch: expected {expected_image_id!r}, got {image_id!r}"
        )

    try:
        delta_ev = float(raw["delta_ev"])
    except (TypeError, ValueError) as exc:
        raise DecisionError(f"delta_ev must be numeric: {exc}") from exc

    try:
        confidence = float(raw["confidence"])
    except (TypeError, ValueError) as exc:
        raise DecisionError(f"confidence must be numeric: {exc}") from exc

    if not (0.0 <= confidence <= 1.0):
        raise DecisionError(f"confidence must be in [0.0, 1.0], got {confidence}")

    reject = bool(raw.get("reject", False))
    reason = str(raw.get("reason", ""))

    # Auto-reject if confidence is too low and not already rejected
    if not reject and confidence < minimum_apply_confidence:
        reject = True
        reason = f"Confidence {confidence:.2f} below minimum {minimum_apply_confidence:.2f}. {reason}".strip()

    # Clamp EV
    clamped_ev = clamp_ev(delta_ev, maximum_delta_ev)
    if clamped_ev != delta_ev:
        reason = f"Clamped delta_ev from {delta_ev:.2f} to {clamped_ev:.2f}. {reason}".strip()

    return ImageDecision(
        image_id=image_id,
        delta_ev=clamped_ev,
        confidence=confidence,
        reject=reject,
        reason=reason,
    )


def process_mock_decisions(
    manifest: Manifest,
) -> list[ImageDecision]:
    """Generate deterministic mock decisions for a manifest.

    Returns zero-EV, high-confidence decisions for every entry in order.
    """
    decisions = []
    for entry in manifest.entries:
        decisions.append(
            ImageDecision(
                image_id=entry.image_id,
                delta_ev=0.0,
                confidence=0.99,
                reject=False,
                reason="Mock deterministic decision",
            )
        )
    return decisions


def validate_decision_batch(
    raw_decisions: list[Mapping[str, Any]],
    manifest: Manifest,
    maximum_delta_ev: float,
    minimum_apply_confidence: float,
) -> list[ImageDecision]:
    """Validate a batch of raw decisions against the manifest order.

    Ensures exactly one decision per manifest image, matches image IDs,
    rejects duplicates, missing, or unknown IDs, and preserves manifest order.
    """
    if not isinstance(raw_decisions, list):
        raise DecisionError("Batch must be a list of decisions")

    if len(raw_decisions) != len(manifest.entries):
        raise DecisionError(
            f"Decision count mismatch: expected {len(manifest.entries)}, got {len(raw_decisions)}"
        )

    raw_by_id = {}
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            raise DecisionError("Batch must contain dictionary decisions")
        img_id = raw.get("image_id")
        if not img_id:
            raise DecisionError("Decision missing image_id")
        if img_id in raw_by_id:
            raise DecisionError(f"Duplicate decision for image_id: {img_id!r}")
        raw_by_id[img_id] = raw

    validated = []
    for entry in manifest.entries:
        if entry.image_id not in raw_by_id:
            raise DecisionError(f"Missing decision for manifest image_id: {entry.image_id!r}")

        validated.append(
            parse_and_validate_decision(
                raw_by_id[entry.image_id],
                entry.image_id,
                maximum_delta_ev,
                minimum_apply_confidence,
            )
        )

    return validated

__all__ = ["DecisionError", "clamp_ev", "parse_and_validate_decision", "process_mock_decisions", "validate_decision_batch"]
