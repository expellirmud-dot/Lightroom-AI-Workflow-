from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
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


class SceneExposureVerdict(str, Enum):
    TOO_DARK = "TOO_DARK"
    BALANCED = "BALANCED"
    TOO_BRIGHT = "TOO_BRIGHT"
    REVIEW = "REVIEW"


class SinglePassError(ValueError):
    """Raised when the single-pass AI decision contract is violated."""


class SinglePassDecision(BaseModel):
    """One evaluated exposure decision for a single image.

    PASS is a completed no-change judgment. ADJUST is the only mutating proposal.
    REVIEW is unresolved photographic evidence and remains non-mutating.

    The scene fields are duplicated per image intentionally so deterministic
    validation can prove that every member assigned to one scene_group_id shares
    the same explicit absolute scene conclusion without giving Python
    photographic judgment authority.
    """

    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    image_id: str = Field(..., description="The Lightroom id_local of the image")
    action: Action = Field(default=Action.REVIEW, description="PASS, ADJUST, or REVIEW")
    relevance_verdict: Verdict
    quality_verdict: Verdict
    delta_ev: float = Field(..., allow_inf_nan=False, description="Per-image Exposure2012 adjustment in EV.")
    confidence: float = Field(..., ge=0.0, le=1.0, allow_inf_nan=False)
    highlight_risk: bool
    shadow_risk: bool
    subject_rationale: str
    scene_rationale: str
    scene_group_id: str = Field(default="group-1", description="Stable exposure-context label")
    scene_exposure_verdict: SceneExposureVerdict = Field(
        default=SceneExposureVerdict.REVIEW,
        description="Absolute exposure conclusion for the whole scene context.",
    )
    scene_delta_ev: float = Field(
        default=0.0,
        allow_inf_nan=False,
        description="Approximate shared scene-level correction signal; not mutation authority.",
    )
    is_reference: bool = Field(default=False, description="Is this image a useful visual reference for the scene?")
    reason: str


def _validate_scene_signal(decision: SinglePassDecision, max_delta_ev: float) -> None:
    if not (-max_delta_ev <= decision.scene_delta_ev <= max_delta_ev):
        raise ValueError(
            f"scene_delta_ev {decision.scene_delta_ev} is out of bounds "
            f"[{-max_delta_ev}, {max_delta_ev}]"
        )
    epsilon = 1e-9
    if decision.scene_exposure_verdict == SceneExposureVerdict.TOO_DARK and decision.scene_delta_ev <= epsilon:
        raise ValueError("TOO_DARK scene_exposure_verdict requires positive scene_delta_ev")
    if decision.scene_exposure_verdict == SceneExposureVerdict.TOO_BRIGHT and decision.scene_delta_ev >= -epsilon:
        raise ValueError("TOO_BRIGHT scene_exposure_verdict requires negative scene_delta_ev")
    if decision.scene_exposure_verdict in {SceneExposureVerdict.BALANCED, SceneExposureVerdict.REVIEW} and abs(decision.scene_delta_ev) > epsilon:
        raise ValueError(
            f"{decision.scene_exposure_verdict.value} scene_exposure_verdict requires scene_delta_ev=0"
        )


def validate_single_pass_decision(
    raw: Mapping[str, Any],
    max_delta_ev: float = 3.0,
    min_confidence: float = 0.8,
) -> SinglePassDecision:
    """Validate a raw decision dictionary against the strict contract.

    This validator deliberately distinguishes *evaluation coverage* from
    mutation. PASS/REVIEW must be zero-delta; ADJUST must be non-zero before any
    safety downgrade. Low-confidence/risk downgrades always clear delta_ev.
    """
    try:
        decision = SinglePassDecision.model_validate_json(json.dumps(raw))

        if not (-max_delta_ev <= decision.delta_ev <= max_delta_ev):
            raise ValueError(
                f"delta_ev {decision.delta_ev} is out of bounds "
                f"[{-max_delta_ev}, {max_delta_ev}]"
            )

        epsilon = 1e-9
        if decision.action in {Action.PASS, Action.REVIEW} and abs(decision.delta_ev) > epsilon:
            raise ValueError(f"{decision.action.value} requires delta_ev=0")
        if decision.action == Action.ADJUST and abs(decision.delta_ev) <= epsilon:
            raise ValueError("ADJUST requires a non-zero delta_ev")

        if not decision.scene_group_id.strip():
            raise ValueError("scene_group_id must not be empty")
        _validate_scene_signal(decision, max_delta_ev)

        if decision.confidence < min_confidence:
            decision.action = Action.REVIEW
            decision.delta_ev = 0.0
            if decision.relevance_verdict == Verdict.KEEP:
                decision.relevance_verdict = Verdict.REVIEW
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = (
                "Downgraded to REVIEW due to low confidence. "
                f"{decision.reason}"
            ).strip()

        if decision.highlight_risk or decision.shadow_risk:
            decision.action = Action.REVIEW
            decision.delta_ev = 0.0
            if decision.quality_verdict == Verdict.KEEP:
                decision.quality_verdict = Verdict.REVIEW
            decision.reason = (
                "Downgraded to REVIEW due to risk flags. "
                f"{decision.reason}"
            ).strip()

        return decision
    except Exception as exc:
        raise SinglePassError(f"Validation failed: {exc}") from exc


def validate_scene_decision_set(
    decisions: list[SinglePassDecision],
    *,
    require_explicit_scene_fields: bool = False,
    scene_delta_tolerance: float = 0.05,
) -> None:
    """Validate structural scene consistency without judging photography.

    Every decision assigned to the same scene_group_id must carry one consistent
    absolute scene verdict and approximately the same scene-level correction
    signal. Per-image delta_ev remains free to differ and may be zero for a
    genuinely correct PASS image.
    """
    groups: dict[str, list[SinglePassDecision]] = {}
    for decision in decisions:
        if require_explicit_scene_fields:
            required = {"scene_exposure_verdict", "scene_delta_ev"}
            missing = sorted(required - set(decision.model_fields_set))
            if missing:
                raise SinglePassError(
                    f"Decision {decision.image_id} is missing explicit scene outcome fields: {missing}"
                )
        groups.setdefault(decision.scene_group_id, []).append(decision)

    for group_id, members in groups.items():
        baseline = members[0]
        for member in members[1:]:
            if member.scene_exposure_verdict != baseline.scene_exposure_verdict:
                raise SinglePassError(
                    "Contradictory scene_exposure_verdict values in "
                    f"scene_group_id {group_id!r}: "
                    f"{baseline.scene_exposure_verdict.value} vs {member.scene_exposure_verdict.value}"
                )
            if abs(member.scene_delta_ev - baseline.scene_delta_ev) > scene_delta_tolerance:
                raise SinglePassError(
                    "Contradictory scene_delta_ev values in "
                    f"scene_group_id {group_id!r}: "
                    f"{baseline.scene_delta_ev} vs {member.scene_delta_ev}"
                )


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
        response_map = resolve_manual_response_map(manifest, Path(response_directory))

    decisions: list[SinglePassDecision] = []
    records = []

    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue

        preview_full_path = job_dir / entry.preview_path
        try:
            preview_full_path.resolve().relative_to(job_dir.resolve())
        except ValueError:
            raise SinglePassError(f"Preview path escapes job directory: {preview_full_path}")

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
            raise SinglePassError(f"Failed to analyze {entry.image_id}: {exc}") from exc

        from lr_ai_exposure.analysis_artifacts import AnalysisRecord

        token_usage = metadata.get("usage") or None
        records.append(
            AnalysisRecord(
                decision=decision,
                provider=metadata.get("provider", provider_name),
                model=metadata.get("model", model_name),
                mode=metadata.get("mode", "ANALYZE_ONLY"),
                preview_bytes=int(metadata.get("preview_bytes", entry.preview_bytes or 0)),
                preview_sha256=str(metadata.get("preview_sha256", entry.preview_sha256 or "")),
                response_reference=str(metadata.get("response_file", provider_name)),
                token_usage=token_usage,
            )
        )

    if records:
        from lr_ai_exposure.analysis_artifacts import write_analysis_records
        write_analysis_records(job_dir, manifest.job_id, records)

    return decisions
