from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from lr_ai_exposure.job import Manifest

class Verdict(str, Enum):
    KEEP = "KEEP"
    REVIEW = "REVIEW"
    SKIP = "SKIP"

class SinglePassError(ValueError):
    """Raised when single-pass AI decision contract is violated."""

@dataclass(frozen=True)
class SinglePassDecision:
    """One AI decision for a single image combining triage and exposure."""
    image_id: str
    relevance_verdict: Verdict
    quality_verdict: Verdict
    delta_ev: float
    confidence: float
    highlight_risk: bool
    shadow_risk: bool
    subject_rationale: str
    scene_rationale: str
    batch_consistency_group: str
    reason: str


def validate_single_pass_decision(raw: Mapping[str, Any], max_delta_ev: float = 3.0) -> SinglePassDecision:
    """Validate raw decision dictionary against the strict single-pass contract."""
    if not isinstance(raw, dict):
        raise SinglePassError("Decision must be a dictionary")
        
    required = {
        "image_id", "relevance_verdict", "quality_verdict",
        "delta_ev", "confidence", "highlight_risk", "shadow_risk",
        "subject_rationale", "scene_rationale", "batch_consistency_group", "reason"
    }
    
    missing = required - set(raw.keys())
    if missing:
        raise SinglePassError(f"Missing required fields: {sorted(missing)}")
        
    try:
        relevance_verdict = Verdict(raw["relevance_verdict"])
        quality_verdict = Verdict(raw["quality_verdict"])
    except ValueError as e:
        raise SinglePassError(f"Invalid enum value: {e}") from e
        
    try:
        delta_ev = float(raw["delta_ev"])
        confidence = float(raw["confidence"])
    except (TypeError, ValueError) as e:
        raise SinglePassError(f"Numeric fields must be valid numbers: {e}") from e

    if not math.isfinite(delta_ev) or not math.isfinite(confidence):
        raise SinglePassError("Numeric fields must be finite")

    if not (0.0 <= confidence <= 1.0):
        raise SinglePassError(f"Confidence must be in [0, 1], got {confidence}")

    clamped_ev = max(-max_delta_ev, min(max_delta_ev, delta_ev))
    
    # Low-confidence images are routed to REVIEW
    final_relevance = relevance_verdict
    final_quality = quality_verdict
    reason = str(raw["reason"])
    
    if confidence < 0.8:
        if final_relevance == Verdict.KEEP:
            final_relevance = Verdict.REVIEW
        if final_quality == Verdict.KEEP:
            final_quality = Verdict.REVIEW
        reason = f"Downgraded to REVIEW due to low confidence. {reason}".strip()

    return SinglePassDecision(
        image_id=str(raw["image_id"]),
        relevance_verdict=final_relevance,
        quality_verdict=final_quality,
        delta_ev=clamped_ev,
        confidence=confidence,
        highlight_risk=bool(raw["highlight_risk"]),
        shadow_risk=bool(raw["shadow_risk"]),
        subject_rationale=str(raw["subject_rationale"]),
        scene_rationale=str(raw["scene_rationale"]),
        batch_consistency_group=str(raw["batch_consistency_group"]),
        reason=reason,
    )

def analyze_job_single_pass(manifest: Manifest) -> list[SinglePassDecision]:
    """Generate deterministic mock decisions for a single-pass workflow.
    Ensures exactly one analysis pass per preview.
    """
    decisions = []
    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            decisions.append(
                SinglePassDecision(
                    image_id=entry.image_id,
                    relevance_verdict=Verdict.SKIP,
                    quality_verdict=Verdict.SKIP,
                    delta_ev=0.0,
                    confidence=1.0,
                    highlight_risk=False,
                    shadow_risk=False,
                    subject_rationale="",
                    scene_rationale="",
                    batch_consistency_group="",
                    reason=f"Skipped because extraction status is {entry.extraction_status}"
                )
            )
            continue
            
        decisions.append(
            SinglePassDecision(
                image_id=entry.image_id,
                relevance_verdict=Verdict.KEEP,
                quality_verdict=Verdict.KEEP,
                delta_ev=0.5,
                confidence=0.95,
                highlight_risk=False,
                shadow_risk=False,
                subject_rationale="Mock indoor portrait",
                scene_rationale="Mock indoor event",
                batch_consistency_group="event_1",
                reason="Mock deterministic decision"
            )
        )
    return decisions
