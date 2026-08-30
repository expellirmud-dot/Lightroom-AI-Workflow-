from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from lr_ai_exposure.job import Manifest


class Verdict(str, Enum):
    KEEP = "KEEP"
    REVIEW = "REVIEW"
    SKIP = "SKIP"


class Action(str, Enum):
    PASS = "PASS"
    ADJUST = "ADJUST"
    REVIEW = "REVIEW"


class SinglePassError(ValueError):
    """Raised when the single-pass AI decision contract is violated."""


class SinglePassDecision(BaseModel):
    """One AI decision for a single image combining triage and exposure."""

    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    image_id: str = Field(..., description="The Lightroom id_local of the image")
    action: Action = Field(default=Action.REVIEW, description="PASS, ADJUST, or REVIEW")
    relevance_verdict: Verdict
    quality_verdict: Verdict
    delta_ev: float = Field(
        ...,
        allow_inf_nan=False,
        description="Exposure adjustment in EV.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, allow_inf_nan=False)
    highlight_risk: bool
    shadow_risk: bool
    subject_rationale: str
    scene_rationale: str
    scene_group_id: str = Field(default="group-1", description="Scene group ID for iterative passes")
    is_reference: bool = Field(default=False, description="Is this image the reference for the scene group?")
    reason: str


import json


def validate_single_pass_decision(
    raw: Mapping[str, Any],
    max_delta_ev: float = 3.0,
    min_confidence: float = 0.8,
) -> SinglePassDecision:
    """Validate a raw decision dictionary against the strict contract."""
    try:
        decision = SinglePassDecision.model_validate_json(json.dumps(raw))

        if not (-max_delta_ev <= decision.delta_ev <= max_delta_ev):
            raise ValueError(
                f"delta_ev {decision.delta_ev} is out of bounds "
                f"[{-max_delta_ev}, {max_delta_ev}]"
            )

        if decision.confidence < min_confidence:
            if decision.action != Action.REVIEW:
                decision.action = Action.REVIEW
            if decision.relevance_verdict == Verdict.KEEP:
                decision.relevance_verdict = Verdict.REVIEW
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = (
                "Downgraded to REVIEW due to low confidence. "
                f"{decision.reason}"
            ).strip()

        if decision.highlight_risk or decision.shadow_risk:
            if decision.action != Action.REVIEW:
                decision.action = Action.REVIEW
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = (
                "Downgraded to REVIEW due to risk flags. "
                f"{decision.reason}"
            ).strip()

        return decision
    except Exception as exc:
        raise SinglePassError(f"Validation failed: {exc}") from exc


from pathlib import Path


def analyze_job_single_pass(
    manifest: Manifest,
    job_dir: Path,
    config: dict[str, Any],
) -> list[SinglePassDecision]:
    """Analyze or import one decision per FOUND preview in manifest order.

    ``google`` performs a network call. ``manual_app`` imports decision files
    from the configured directory and is the canonical prepared-job provider.
    """
    provider_name = config.get("ai_provider", "google")
    model_name = config.get("ai_model", "gemini-2.5-pro")

    if provider_name == "google":
        from lr_ai_exposure.providers.google_vision import analyze_single_image_google
    elif provider_name == "manual_app":
        from lr_ai_exposure.providers.manual_app import (
            analyze_single_image_manual_app,
            resolve_manual_response_map,
        )
    else:
        raise SinglePassError(f"Unknown ai_provider: {provider_name}")

    response_map: dict[str, Path] = {}
    if provider_name == "manual_app":
        response_directory = config.get("manual_response_directory")
        if not response_directory:
            raise SinglePassError(
                "manual_app provider requires 'manual_response_directory' in config"
            )
        response_map = resolve_manual_response_map(
            manifest,
            Path(response_directory),
        )

    decisions: list[SinglePassDecision] = []
    records = []

    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue

        preview_full_path = job_dir / entry.preview_path
        try:
            preview_full_path.resolve().relative_to(job_dir.resolve())
        except ValueError:
            raise SinglePassError(
                f"Preview path escapes job directory: {preview_full_path}"
            )

        try:
            if provider_name == "google":
                decision, metadata = analyze_single_image_google(
                    entry=entry,
                    preview_full_path=preview_full_path,
                    model_name=model_name,
                )
            else:
                decision, metadata = analyze_single_image_manual_app(
                    entry=entry,
                    preview_full_path=preview_full_path,
                    response_file=response_map[str(entry.image_id)],
                    model_name=str(model_name),
                )
            decisions.append(decision)
        except Exception as exc:
            raise SinglePassError(
                f"Failed to analyze {entry.image_id}: {exc}"
            ) from exc

        from lr_ai_exposure.analysis_artifacts import AnalysisRecord

        token_usage = metadata.get("usage") or None
        records.append(
            AnalysisRecord(
                decision=decision,
                provider=metadata.get("provider", provider_name),
                model=metadata.get("model", model_name),
                mode=metadata.get("mode", "ANALYZE_ONLY"),
                preview_bytes=int(
                    metadata.get("preview_bytes", entry.preview_bytes or 0)
                ),
                preview_sha256=str(
                    metadata.get("preview_sha256", entry.preview_sha256 or "")
                ),
                response_reference=str(
                    metadata.get("response_file", provider_name)
                ),
                token_usage=token_usage,
            )
        )

    if records:
        from lr_ai_exposure.analysis_artifacts import write_analysis_records

        write_analysis_records(job_dir, manifest.job_id, records)

    return decisions
