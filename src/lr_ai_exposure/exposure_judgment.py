"""Exposure judgment models and deterministic validation.

Implements WO-010.1: Subject-aware exposure judgment and contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ExposureClass(str, Enum):
    SEVERELY_UNDEREXPOSED = "SEVERELY_UNDEREXPOSED"
    UNDEREXPOSED = "UNDEREXPOSED"
    SLIGHTLY_UNDEREXPOSED = "SLIGHTLY_UNDEREXPOSED"
    BALANCED = "BALANCED"
    SLIGHTLY_OVEREXPOSED = "SLIGHTLY_OVEREXPOSED"
    OVEREXPOSED = "OVEREXPOSED"
    CLIPPED = "CLIPPED"


class SceneIntent(str, Enum):
    INDOOR_EVENT = "indoor_event"
    OUTDOOR_DAYLIGHT = "outdoor_daylight"
    STAGE_OR_SPOTLIGHT = "stage_or_spotlight"
    BACKLIT_PERSON = "backlit_person"
    NIGHT_OR_LOW_LIGHT = "night_or_low_light"
    DOCUMENTARY_CANDID = "documentary_candid"
    DETAIL_OR_OBJECT = "detail_or_object"
    UNKNOWN = "unknown"


class HighlightRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Action(str, Enum):
    APPLY = "APPLY"
    REVIEW = "REVIEW"
    SKIP = "SKIP"


class ExposureJudgmentError(ValueError):
    """Raised when exposure judgment contract is violated."""


@dataclass(frozen=True)
class ExposureDecision:
    """Structured decision contract for WO-010.1."""

    image_id: str
    subject_type: str
    subject_exposure: ExposureClass
    background_exposure: ExposureClass
    scene_intent: SceneIntent
    highlight_risk: HighlightRisk
    group_id: str
    reference_image_id: str
    recommended_delta_ev: float
    action: Action
    confidence: float
    reason: str


def validate_exposure_decision(raw: Mapping[str, Any], max_delta_ev: float = 3.0) -> ExposureDecision:
    """Validate raw decision dictionary against the strict contract."""

    if not isinstance(raw, dict):
        raise ExposureJudgmentError("Decision must be a dictionary")

    required = {
        "image_id", "subject_type", "subject_exposure", "background_exposure",
        "scene_intent", "highlight_risk", "group_id", "reference_image_id",
        "recommended_delta_ev", "action", "confidence", "reason"
    }

    missing = required - set(raw.keys())
    if missing:
        raise ExposureJudgmentError(f"Missing required fields: {sorted(missing)}")

    try:
        subject_exposure = ExposureClass(raw["subject_exposure"])
        background_exposure = ExposureClass(raw["background_exposure"])
        scene_intent = SceneIntent(raw["scene_intent"])
        highlight_risk = HighlightRisk(raw["highlight_risk"])
        action = Action(raw["action"])
    except ValueError as e:
        raise ExposureJudgmentError(f"Invalid enum value: {e}") from e

    try:
        delta_ev = float(raw["recommended_delta_ev"])
        confidence = float(raw["confidence"])
    except (TypeError, ValueError) as e:
        raise ExposureJudgmentError(f"Numeric fields must be valid numbers: {e}") from e

    if not math.isfinite(delta_ev) or not math.isfinite(confidence):
        raise ExposureJudgmentError("Numeric fields must be finite")

    if not (0.0 <= confidence <= 1.0):
        raise ExposureJudgmentError(f"Confidence must be in [0, 1], got {confidence}")

    if abs(delta_ev) > max_delta_ev:
        # Instead of silent clamp like before, WO-010.1 contract might require it or we clamp it.
        # "All recommendations must still obey configured maximum_delta_ev."
        delta_ev = max(-max_delta_ev, min(max_delta_ev, delta_ev))

    # Highlight risk downgrade logic (as required in test: "Highlight-risk downgrade to REVIEW")
    # Actually, we shouldn't change the action if the caller already provided it,
    # but the instructions say "Low confidence or conflicting evidence must produce REVIEW."
    final_action = action
    reason = str(raw["reason"])

    if confidence < 0.8 and final_action == Action.APPLY:
        final_action = Action.REVIEW
        reason = f"Downgraded to REVIEW due to low confidence. {reason}".strip()

    if highlight_risk == HighlightRisk.HIGH and final_action == Action.APPLY and delta_ev > 0:
        final_action = Action.REVIEW
        reason = f"Downgraded to REVIEW due to high highlight risk. {reason}".strip()

    return ExposureDecision(
        image_id=str(raw["image_id"]),
        subject_type=str(raw["subject_type"]),
        subject_exposure=subject_exposure,
        background_exposure=background_exposure,
        scene_intent=scene_intent,
        highlight_risk=highlight_risk,
        group_id=str(raw["group_id"]),
        reference_image_id=str(raw["reference_image_id"]),
        recommended_delta_ev=delta_ev,
        action=final_action,
        confidence=confidence,
        reason=reason,
    )
