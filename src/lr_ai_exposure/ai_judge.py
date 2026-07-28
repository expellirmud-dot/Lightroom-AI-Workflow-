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


import os
from pathlib import Path
from typing import Any

def analyze_job_single_pass(manifest: Manifest, job_dir: Path, config: dict[str, Any]) -> list[SinglePassDecision]:
    """Analyze a batch of extracted previews using a configurable vision API.
    Ensures exactly one analysis pass per preview. MAX_IN_FLIGHT=1.
    """
    provider_name = config.get("ai_provider", "google")
    model_name = config.get("ai_model", "gemini-2.5-pro")
    
    if provider_name == "google":
        from lr_ai_exposure.providers.google_vision import analyze_single_image_google
    else:
        raise SinglePassError(f"Unknown ai_provider: {provider_name}")
        
    decisions = []
    
    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue
            
        preview_full_path = job_dir / entry.preview_path
        
        # Verify job-root containment
        try:
            preview_full_path.resolve().relative_to(job_dir.resolve())
        except ValueError:
            raise SinglePassError(f"Preview path escapes job directory: {preview_full_path}")
            
        try:
            if provider_name == "google":
                decision, metadata = analyze_single_image_google(
                    entry=entry, 
                    preview_full_path=preview_full_path, 
                    model_name=model_name
                )
            decisions.append(decision)
        except Exception as e:
            raise SinglePassError(f"Failed to analyze {entry.image_id}: {e}") from e
            
    return decisions
