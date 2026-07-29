"""Canonical analysis-artifact writers.

Analysis artifacts are always written before any optional XMP apply stage.
They therefore record validated AI decisions and identity evidence, never an
XMP mutation claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lr_ai_exposure.ai_judge import SinglePassDecision


def _atomic_write_json(path: Path, payload: Any) -> Path:
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
    return {
        "job_id": job_id,
        "mode": mode,
        "provider": provider,
        "model": model,
        "apply_authorized": apply_authorized,
        "xmp_mutation": xmp_mutation,
        "decision_count": len(decisions),
        "decisions": [decision.model_dump(mode="json") for decision in decisions],
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
    markers: list[str] = [
        "CANONICAL_CLI",
        f"DECISIONS_{len(decisions)}",
        "FULL_DECISION_SCHEMA_WRITTEN",
        "ANALYSIS_STAGE_NO_XMP_MUTATION",
    ]
    if mode in {"ANALYZE_ONLY", "ANALYZE_SAVED_JOB"}:
        markers.extend(["APPLY_FUNCTION_NOT_CALLED", "NO_XMP_MUTATION"])
    if mode == "ANALYZE_ONLY":
        markers.append("ANALYZE_ONLY_DEFAULT")
    if mode == "ANALYZE_SAVED_JOB":
        markers.append("SAVED_JOB_DECISIONS_VALIDATED")
    if mode.startswith("APPLY"):
        markers.append("APPLY_STAGE_FOLLOWS_ANALYSIS_ARTIFACT")
    if extra_markers:
        markers.extend(extra_markers)

    return {
        "job_id": job_id,
        "mode": mode,
        "provider": provider,
        "model": model,
        "maximum_delta_ev": settings.get("maximum_delta_ev"),
        "minimum_apply_confidence": settings.get("minimum_apply_confidence"),
        "apply_authorized": bool(settings.get("apply_authorized", False))
        and mode.startswith("APPLY"),
        "xmp_mutation": False,
        "identity_chain": [
            {
                "image_id": decision.image_id,
                "relevance_verdict": decision.relevance_verdict.value
                if hasattr(decision.relevance_verdict, "value")
                else decision.relevance_verdict,
                "quality_verdict": decision.quality_verdict.value
                if hasattr(decision.quality_verdict, "value")
                else decision.quality_verdict,
                "delta_ev": decision.delta_ev,
                "confidence": decision.confidence,
            }
            for decision in decisions
        ],
        "markers": markers,
    }


def write_ai_decisions(job_dir: Path, payload: dict[str, Any]) -> Path:
    return _atomic_write_json(Path(job_dir) / "ai-decisions.json", payload)


def write_analysis_evidence(job_dir: Path, payload: dict[str, Any]) -> Path:
    return _atomic_write_json(Path(job_dir) / "analysis-evidence.json", payload)
