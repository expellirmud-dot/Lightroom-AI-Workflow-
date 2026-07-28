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

def analyze_job_single_pass(manifest: Manifest, job_dir: Path) -> list[SinglePassDecision]:
    """Analyze a batch of extracted previews using a real vision API.
    Ensures exactly one analysis pass per preview.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise SinglePassError("GEMINI_API_KEY environment variable is required")
        
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise SinglePassError("google-genai package is required but not installed")
        
    client = genai.Client()
    decisions = []
    
    prompt = (
        "You are an expert AI photo editor acting as a strict single-pass judge for a batch of photos.\n"
        "Analyze the provided image and output a SinglePassDecision JSON object.\n\n"
        "Guidelines:\n"
        "1. Assess relevance (KEEP, REVIEW, SKIP). Is the subject clear and intended?\n"
        "2. Assess quality (KEEP, REVIEW, SKIP). Is it sharply in focus? Downgrade if blurry.\n"
        "3. Evaluate exposure (delta_ev). Provide the EV adjustment needed to perfectly expose the subject (-3.0 to +3.0).\n"
        "4. Flag highlight_risk (true/false) if there are blown-out skies or bright spots that cannot be recovered.\n"
        "5. Flag shadow_risk (true/false) if important shadows are completely crushed.\n"
        "6. Provide a short reason and rationale for subject and scene.\n"
        "7. Provide a batch_consistency_group string (e.g. 'indoor-warm', 'outdoor-overcast').\n"
        "8. Output valid JSON matching the exact schema."
    )
    
    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue
            
        preview_full_path = job_dir / entry.preview_path
        if not preview_full_path.exists():
            raise SinglePassError(f"Preview not found for {entry.image_id}: {preview_full_path}")
            
        try:
            image_bytes = preview_full_path.read_bytes()
            schema = {
                "type": "OBJECT",
                "properties": {
                    "image_id": {"type": "STRING"},
                    "relevance_verdict": {"type": "STRING", "enum": ["KEEP", "REVIEW", "SKIP"]},
                    "quality_verdict": {"type": "STRING", "enum": ["KEEP", "REVIEW", "SKIP"]},
                    "delta_ev": {"type": "NUMBER"},
                    "confidence": {"type": "NUMBER"},
                    "highlight_risk": {"type": "BOOLEAN"},
                    "shadow_risk": {"type": "BOOLEAN"},
                    "subject_rationale": {"type": "STRING"},
                    "scene_rationale": {"type": "STRING"},
                    "batch_consistency_group": {"type": "STRING"},
                    "reason": {"type": "STRING"}
                },
                "required": [
                    "image_id", "relevance_verdict", "quality_verdict", "delta_ev", 
                    "confidence", "highlight_risk", "shadow_risk", "subject_rationale",
                    "scene_rationale", "batch_consistency_group", "reason"
                ]
            }
            
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type='image/jpeg',
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1,
                ),
            )
            
            raw_dict = json.loads(response.text)
            # Ensure image_id matches the requested one exactly
            raw_dict["image_id"] = str(entry.image_id)
            
            # Default confidence if model misses it
            if "confidence" not in raw_dict:
                raw_dict["confidence"] = 0.95
                
            decision = validate_single_pass_decision(raw_dict)
            decisions.append(decision)
            
        except Exception as e:
            raise SinglePassError(f"Failed to analyze {entry.image_id}: {e}") from e
            
    return decisions
