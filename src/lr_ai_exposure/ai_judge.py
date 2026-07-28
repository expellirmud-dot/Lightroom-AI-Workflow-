from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lr_ai_exposure.job import Manifest

class Verdict(str, Enum):
    KEEP = "KEEP"
    REVIEW = "REVIEW"
    SKIP = "SKIP"

class SinglePassError(ValueError):
    """Raised when single-pass AI decision contract is violated."""

class SinglePassDecision(BaseModel):
    """One AI decision for a single image combining triage and exposure."""
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    image_id: str = Field(..., description="The Lightroom id_local of the image")
    relevance_verdict: Verdict
    quality_verdict: Verdict
    delta_ev: float = Field(..., allow_inf_nan=False, description="Exposure adjustment in EV.")
    confidence: float = Field(..., ge=0.0, le=1.0, allow_inf_nan=False)
    highlight_risk: bool
    shadow_risk: bool
    subject_rationale: str
    scene_rationale: str
    batch_consistency_group: str
    reason: str


import json

def validate_single_pass_decision(raw: Mapping[str, Any], max_delta_ev: float = 3.0, min_confidence: float = 0.8) -> SinglePassDecision:
    """Validate raw decision dictionary against the strict single-pass contract."""
    try:
        # Pydantic strict mode requires JSON validation to coerce strings to Enums
        decision = SinglePassDecision.model_validate_json(json.dumps(raw))
        
        # Reject out-of-range delta_ev; do not clamp
        if not (-max_delta_ev <= decision.delta_ev <= max_delta_ev):
            raise ValueError(f"delta_ev {decision.delta_ev} is out of bounds [{-max_delta_ev}, {max_delta_ev}]")
            
        # Low confidence downgrades based on threshold
        if decision.confidence < min_confidence:
            if decision.relevance_verdict == Verdict.KEEP:
                decision.relevance_verdict = Verdict.REVIEW
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = f"Downgraded to REVIEW due to low confidence. {decision.reason}".strip()
            
        # Force REVIEW on highlight_risk or shadow_risk
        if decision.highlight_risk or decision.shadow_risk:
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = f"Downgraded to REVIEW due to risk flags. {decision.reason}".strip()
            
        return decision
    except Exception as e:
        raise SinglePassError(f"Validation failed: {str(e)}") from e


def analyze_job_single_pass(manifest: Manifest) -> list[SinglePassDecision]:
    """Generate deterministic mock decisions for a single-pass workflow.
    Ensures exactly one analysis pass per preview.
    """
    raise NotImplementedError("Vision provider integration explicitly NOT_IMPLEMENTED until a real image-capable provider is wired.")
