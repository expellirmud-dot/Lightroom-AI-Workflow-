"""Canonical analysis-artifact writers for the ANALYZE_ONLY CLI flow.

This module is the single owner of the on-disk shape of the two
artifacts produced by every canonical ``lr-ai-exposure`` run:

- ``ai-decisions.json``      — the full, schema-validated
  ``SinglePassDecision`` payload, written in manifest order.
- ``analysis-evidence.json`` — the analysis-evidence record (mode,
  provider, model, job identity, identity chain, markers).

Design invariants:

- Decisions are written in **manifest order**. Never sorted, never
  deduplicated, never reordered.
- Each decision is serialized with ``SinglePassDecision.model_dump(
  mode="json")`` so the full risk and rationale fields are preserved
  and the payload is byte-stable across runs.
- The apply layer is never reached from this module. ANALYZE_ONLY
  artifact writing is strictly separate from XMP mutation.
- Writes are atomic (temp file + ``replace``) so a failed write leaves
  any existing artifact intact.

No XMP, RAW, catalog, or preview-cache mutation occurs here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lr_ai_exposure.ai_judge import SinglePassDecision


def _atomic_write_json(path: Path, payload: Any) -> Path:
    """Write ``payload`` as UTF-8 JSON via a temp file + atomic replace.

    Returns the final path. A failure mid-write leaves any existing
    file at ``path`` intact because the temp file is replaced only
    after the full JSON has been encoded.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def serialize_decisions(
    job_id: str,
    decisions: list[SinglePassDecision],
    provider: str,
    model: str,
    *,
    mode: str = "ANALYZE_ONLY",
    apply_authorized: bool = False,
    xmp_mutation: bool = False,
) -> dict[str, Any]:
    """Build the canonical ``ai-decisions.json`` payload.

    Decisions are serialized in manifest order. Each decision uses
    ``model_dump(mode="json")`` so the full schema (including
    ``highlight_risk``, ``shadow_risk``, ``subject_rationale``,
    ``scene_rationale``, ``batch_consistency_group`` and ``reason``)
    is preserved.
    """
    return {
        "job_id": job_id,
        "mode": mode,
        "provider": provider,
        "model": model,
        "apply_authorized": apply_authorized,
        "xmp_mutation": xmp_mutation,
        "decision_count": len(decisions),
        "decisions": [d.model_dump(mode="json") for d in decisions],
    }


def serialize_evidence(
    job_id: str,
    decisions: list[SinglePassDecision],
    provider: str,
    model: str,
    settings: dict[str, Any],
    *,
    mode: str = "ANALYZE_ONLY",
    extra_markers: list[str] | None = None,
) -> dict[str, Any]:
    """Build the canonical ``analysis-evidence.json`` payload.

    Captures the mode, provider/model, identity chain (one entry per
    decision in manifest order), and validation markers. Carries no
    secrets — only non-secret ``settings`` fields are referenced.
    """
    markers: list[str] = [
        "CANONICAL_CLI",
        "ANALYZE_ONLY_DEFAULT",
        f"DECISIONS_{len(decisions)}",
        "FULL_DECISION_SCHEMA_WRITTEN",
        "APPLY_FUNCTION_NOT_CALLED",
        "NO_XMP_MUTATION",
    ]
    if extra_markers:
        markers.extend(extra_markers)

    return {
        "job_id": job_id,
        "mode": mode,
        "provider": provider,
        "model": model,
        "maximum_delta_ev": settings.get("maximum_delta_ev"),
        "minimum_apply_confidence": settings.get("minimum_apply_confidence"),
        "apply_authorized": False,
        "xmp_mutation": False,
        "identity_chain": [
            {
                "image_id": d.image_id,
                "relevance_verdict": d.relevance_verdict.value
                if hasattr(d.relevance_verdict, "value")
                else d.relevance_verdict,
                "quality_verdict": d.quality_verdict.value
                if hasattr(d.quality_verdict, "value")
                else d.quality_verdict,
                "delta_ev": d.delta_ev,
                "confidence": d.confidence,
            }
            for d in decisions
        ],
        "markers": markers,
    }


def write_ai_decisions(
    job_dir: Path,
    payload: dict[str, Any],
) -> Path:
    """Write ``ai-decisions.json`` atomically into ``job_dir``."""
    return _atomic_write_json(Path(job_dir) / "ai-decisions.json", payload)


def write_analysis_evidence(
    job_dir: Path,
    payload: dict[str, Any],
) -> Path:
    """Write ``analysis-evidence.json`` atomically into ``job_dir``."""
    return _atomic_write_json(Path(job_dir) / "analysis-evidence.json", payload)
