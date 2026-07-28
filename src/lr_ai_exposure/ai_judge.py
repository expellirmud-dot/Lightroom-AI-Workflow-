from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, Field, model_validator

from lr_ai_exposure.job import Manifest

class Verdict(str, Enum):
    KEEP = "KEEP"
    REVIEW = "REVIEW"
    SKIP = "SKIP"

class SinglePassError(ValueError):
    """Raised when single-pass AI decision contract is violated."""

class SinglePassDecision(BaseModel):
    """One AI decision for a single image combining triage and exposure."""
    image_id: str = Field(..., description="The Lightroom id_local of the image")
    relevance_verdict: Verdict
    quality_verdict: Verdict
    delta_ev: float = Field(..., description="Exposure adjustment in EV. Clamped to [-3.0, 3.0]")
    confidence: float = Field(..., ge=0.0, le=1.0)
    highlight_risk: bool
    shadow_risk: bool
    subject_rationale: str
    scene_rationale: str
    batch_consistency_group: str
    reason: str

    @model_validator(mode="after")
    def clamp_and_downgrade(self) -> SinglePassDecision:
        # Clamp delta_ev
        self.delta_ev = max(-3.0, min(3.0, self.delta_ev))
        
        # Low confidence downgrades
        if self.confidence < 0.8:
            if self.relevance_verdict == Verdict.KEEP:
                self.relevance_verdict = Verdict.REVIEW
            if self.quality_verdict == Verdict.KEEP:
                self.quality_verdict = Verdict.REVIEW
            self.reason = f"Downgraded to REVIEW due to low confidence. {self.reason}".strip()
            
        return self


def validate_single_pass_decision(raw: Mapping[str, Any], max_delta_ev: float = 3.0) -> SinglePassDecision:
    """Validate raw decision dictionary against the strict single-pass contract."""
    try:
        decision = SinglePassDecision.model_validate(raw)
        # Apply max_delta_ev config if needed since model clamped to 3.0 by default
        decision.delta_ev = max(-max_delta_ev, min(max_delta_ev, decision.delta_ev))
        return decision
    except Exception as e:
        raise SinglePassError(f"Validation failed: {str(e)}") from e


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
