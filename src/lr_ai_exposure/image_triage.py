"""Image relevance triage models and validation.

Implements WO-010.2: Classify image relevance, test shots, accidents, duplicates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class RelevanceClass(str, Enum):
    KEEP_PRIMARY = "KEEP_PRIMARY"
    KEEP_SUPPORTING = "KEEP_SUPPORTING"
    KEEP_CANDID = "KEEP_CANDID"
    REVIEW = "REVIEW"
    SUGGEST_REJECT_TEST_SHOT = "SUGGEST_REJECT_TEST_SHOT"
    SUGGEST_REJECT_ACCIDENTAL = "SUGGEST_REJECT_ACCIDENTAL"
    SUGGEST_REJECT_IRRELEVANT = "SUGGEST_REJECT_IRRELEVANT"
    SUGGEST_REJECT_DUPLICATE = "SUGGEST_REJECT_DUPLICATE"
    SUGGEST_REJECT_UNUSABLE = "SUGGEST_REJECT_UNUSABLE"


class QualityAction(str, Enum):
    APPLY = "APPLY"
    REVIEW = "REVIEW"
    SKIP = "SKIP"


class Likelihood(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TriageError(ValueError):
    """Raised when triage decision contract is violated."""


@dataclass(frozen=True)
class TriageDecision:
    """Structured decision contract for WO-010.2."""
    
    image_id: str
    relevance_class: RelevanceClass
    quality_action: QualityAction
    event_relation: str
    test_shot_likelihood: Likelihood
    accidental_likelihood: Likelihood
    quality_flags: list[str] = field(default_factory=list)
    duplicate_of: str = ""
    confidence: float = 1.0
    reason: str = ""


def validate_triage_decision(raw: Mapping[str, Any]) -> TriageDecision:
    """Validate raw triage decision dictionary against the strict contract."""
    
    if not isinstance(raw, dict):
        raise TriageError("Decision must be a dictionary")
        
    required = {
        "image_id", "relevance_class", "quality_action", "event_relation",
        "test_shot_likelihood", "accidental_likelihood", "quality_flags",
        "duplicate_of", "confidence", "reason"
    }
    
    missing = required - set(raw.keys())
    if missing:
        raise TriageError(f"Missing required fields: {sorted(missing)}")
        
    try:
        relevance_class = RelevanceClass(raw["relevance_class"])
        quality_action = QualityAction(raw["quality_action"])
        test_shot_likelihood = Likelihood(raw["test_shot_likelihood"])
        accidental_likelihood = Likelihood(raw["accidental_likelihood"])
    except ValueError as e:
        raise TriageError(f"Invalid enum value: {e}") from e

    try:
        confidence = float(raw["confidence"])
    except (TypeError, ValueError) as e:
        raise TriageError(f"Numeric fields must be valid numbers: {e}") from e

    if not math.isfinite(confidence):
        raise TriageError("Confidence must be finite")

    if not (0.0 <= confidence <= 1.0):
        raise TriageError(f"Confidence must be in [0, 1], got {confidence}")
        
    if not isinstance(raw["quality_flags"], list):
        raise TriageError("quality_flags must be a list of strings")

    final_relevance = relevance_class
    final_action = quality_action
    reason = str(raw["reason"])
    
    # Low-confidence or conflicting cases must produce REVIEW.
    if confidence < 0.8:
        if final_relevance != RelevanceClass.REVIEW:
            final_relevance = RelevanceClass.REVIEW
            reason = f"Downgraded to REVIEW due to low confidence. {reason}".strip()
        if final_action == QualityAction.APPLY:
            final_action = QualityAction.REVIEW
            
    # Ambiguous test shots (e.g., low or medium likelihood but suggested reject)
    if final_relevance == RelevanceClass.SUGGEST_REJECT_TEST_SHOT and test_shot_likelihood in (Likelihood.LOW, Likelihood.NONE):
        final_relevance = RelevanceClass.REVIEW
        reason = f"Downgraded to REVIEW due to ambiguous test shot evidence. {reason}".strip()

    return TriageDecision(
        image_id=str(raw["image_id"]),
        relevance_class=final_relevance,
        quality_action=final_action,
        event_relation=str(raw["event_relation"]),
        test_shot_likelihood=test_shot_likelihood,
        accidental_likelihood=accidental_likelihood,
        quality_flags=[str(x) for x in raw["quality_flags"]],
        duplicate_of=str(raw["duplicate_of"]),
        confidence=confidence,
        reason=reason,
    )
