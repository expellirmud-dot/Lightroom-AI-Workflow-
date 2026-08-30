from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from lr_ai_exposure.job import ManifestEntry
from lr_ai_exposure.ai_judge import SinglePassDecision, SinglePassError, validate_single_pass_decision

class ProviderQuotaError(SinglePassError):
    """Raised when the provider rate limits or exhausts quota."""

def analyze_single_image_google(
    entry: ManifestEntry, 
    preview_full_path: Path, 
    model_name: str = "gemini-2.5-pro",
    max_output_tokens: int = 512
) -> tuple[SinglePassDecision, dict[str, Any]]:
    """Analyze exactly one JPEG using Google GenAI provider."""
    
    if not os.environ.get("GEMINI_API_KEY"):
        raise SinglePassError("GEMINI_API_KEY environment variable is required")
        
    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError
    except ImportError:
        raise SinglePassError("google-genai package is required but not installed")
        
    client = genai.Client()
    
    # Verification
    if not preview_full_path.exists():
        raise SinglePassError(f"Preview not found for {entry.image_id}: {preview_full_path}")
        
    try:
        image_bytes = preview_full_path.read_bytes()
    except Exception as e:
        raise SinglePassError(f"Failed to read image bytes: {e}")
        
    if len(image_bytes) != entry.preview_bytes:
        raise SinglePassError(f"Byte size mismatch: expected {entry.preview_bytes}, got {len(image_bytes)}")
        
    import hashlib
    actual_sha256 = hashlib.sha256(image_bytes).hexdigest()
    if actual_sha256 != entry.preview_sha256:
        raise SinglePassError(f"SHA-256 mismatch: expected {entry.preview_sha256}, got {actual_sha256}")
        
    # Verify JPEG format using PIL
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.format != "JPEG":
                raise SinglePassError(f"Expected JPEG format, got {img.format}")
            img.verify()
    except Exception as e:
        if isinstance(e, SinglePassError):
            raise
        raise SinglePassError(f"Failed to decode JPEG: {e}")

    prompt = (
        "You are an expert AI photo editor acting as a strict single-pass judge for a photo.\n"
        "Analyze the provided image and output a SinglePassDecision JSON object.\n\n"
        "Guidelines:\n"
        "1. Assess relevance (KEEP, REVIEW, SKIP). Is the subject clear and intended?\n"
        "2. Assess quality (KEEP, REVIEW, SKIP). Is it sharply in focus? Downgrade if blurry.\n"
        "3. Evaluate exposure (delta_ev). Provide the EV adjustment needed to perfectly expose the subject (-3.0 to +3.0).\n"
        "4. Flag highlight_risk (true/false) if there are blown-out skies or bright spots that cannot be recovered.\n"
        "5. Flag shadow_risk (true/false) if important shadows are completely crushed.\n"
        "6. Provide a short reason and rationale for subject and scene.\n"
        "7. Provide a scene_group_id string (e.g. 'indoor-warm', 'outdoor-overcast').\n"
        "8. Set action to PASS if no adjustment is needed, ADJUST if delta_ev should be applied, REVIEW if unsure.\n"
        "9. Set is_reference to true if this image is the best reference for the scene group.\n"
        "10. Output valid JSON matching the exact schema. Do NOT include image_id, confidence is optional."
    )
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "enum": ["PASS", "ADJUST", "REVIEW"]},
            "relevance_verdict": {"type": "STRING", "enum": ["KEEP", "REVIEW", "SKIP"]},
            "quality_verdict": {"type": "STRING", "enum": ["KEEP", "REVIEW", "SKIP"]},
            "delta_ev": {"type": "NUMBER"},
            "confidence": {"type": "NUMBER"},
            "highlight_risk": {"type": "BOOLEAN"},
            "shadow_risk": {"type": "BOOLEAN"},
            "subject_rationale": {"type": "STRING"},
            "scene_rationale": {"type": "STRING"},
            "scene_group_id": {"type": "STRING"},
            "is_reference": {"type": "BOOLEAN"},
            "reason": {"type": "STRING"}
        },
        "required": [
            "action", "relevance_verdict", "quality_verdict", "delta_ev", 
            "confidence", "highlight_risk", "shadow_risk", "subject_rationale",
            "scene_rationale", "scene_group_id", "is_reference", "reason"
        ]
    }
    
    _QUOTA_KEYWORDS = ("quota", "exhausted", "per day", "daily", "billing")
    _RATE_LIMIT_KEYWORDS = ("rate", "per minute", "retry")
    
    def _is_quota_exhausted(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(k in msg for k in _QUOTA_KEYWORDS)
    
    for attempt in range(1, 3):  # Maximum two attempts (one bounded retry for RATE_LIMITED only)
        try:
            response = client.models.generate_content(
                model=model_name,
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
                    max_output_tokens=max_output_tokens,
                ),
            )
            break  # Success
        except APIError as e:
            if e.code == 429:
                if _is_quota_exhausted(e):
                    # QUOTA_EXHAUSTED — never retry; stop immediately
                    raise ProviderQuotaError(f"QUOTA_EXHAUSTED: {e}") from e
                # RATE_LIMITED — one bounded retry with Retry-After or fixed delay
                if attempt >= 2:
                    raise ProviderQuotaError(f"RATE_LIMITED: {e}") from e
                import time, re
                retry_delay = 32  # safe default
                m = re.search(r"retryDelay.*?(\d+)s", str(e))
                if m:
                    retry_delay = min(int(m.group(1)) + 2, 60)  # cap at 60s
                time.sleep(retry_delay)
                continue
            raise SinglePassError(f"Provider API error ({e.code}): {e}") from e
        except Exception as e:
            raise SinglePassError(f"Provider request failed: {e}") from e

    try:
        raw_dict = json.loads(response.text)
    except Exception as e:
        raise SinglePassError(f"Failed to parse JSON response: {e}")
        
    # Explicitly system-bind image_id (no silent overwrite, just insert since we asked model not to provide it)
    if "image_id" in raw_dict:
        if raw_dict["image_id"] != str(entry.image_id):
            raise SinglePassError(f"Model returned incorrect image_id {raw_dict['image_id']}, expected {entry.image_id}")
    else:
        raw_dict["image_id"] = str(entry.image_id)
        
    # Do not provide default confidence; if absent, schema validation fails.
    decision = validate_single_pass_decision(raw_dict)
    
    usage = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = {
            "prompt_token_count": getattr(response.usage_metadata, "prompt_token_count", 0),
            "candidates_token_count": getattr(response.usage_metadata, "candidates_token_count", 0),
            "total_token_count": getattr(response.usage_metadata, "total_token_count", 0),
        }
        
    metadata = {
        "provider": "google",
        "model": model_name,
        "mode": "ANALYZE_ONLY",
        "usage": usage
    }
        
    return decision, metadata
