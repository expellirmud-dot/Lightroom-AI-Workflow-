"""Batch consistency grouping and reference selection.

Implements WO-010.1: Deterministic grouping and exposure jump detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from lr_ai_exposure.exposure_judgment import ExposureDecision


@dataclass(frozen=True)
class BatchConsistencyResult:
    """Result of batch consistency review for an image."""

    image_id: str
    original_decision: ExposureDecision
    final_action: str
    flagged_jump: bool
    consistency_reason: str


def group_decisions(decisions: Sequence[ExposureDecision]) -> dict[str, list[ExposureDecision]]:
    """Group decisions deterministically by scene intent and background exposure.

    In a real implementation, this would use visual features, but for the mock/contract,
    we group by explicitly classified fields.
    """
    groups: dict[str, list[ExposureDecision]] = {}
    for d in decisions:
        groups.setdefault(d.group_id, []).append(d)

    return groups


def select_reference_frame(group: Sequence[ExposureDecision]) -> ExposureDecision | None:
    """Select the best reference frame for a group deterministically.

    Prefers BALANCED subject exposure with LOW highlight risk.
    Ties are broken by highest confidence, then by first image_id alphabetically.
    """
    if not group:
        return None

    def _score(d: ExposureDecision) -> tuple[int, int, float, str]:
        # Subject exposure score (BALANCED is best)
        subj_score = 1 if d.subject_exposure.value == "BALANCED" else 0

        # Highlight risk score (LOW is best)
        hl_score = 1 if d.highlight_risk.value == "low" else 0

        # We negate image_id so that smaller alphabetical comes first in max()
        # but string negation isn't a thing. We'll return negative score and use min(),
        # or we sort.
        return (-subj_score, -hl_score, -d.confidence, d.image_id)

    return sorted(group, key=_score)[0]


def review_batch_consistency(
    decisions: Sequence[ExposureDecision],
    max_adjacent_jump_ev: float = 0.5,
) -> list[BatchConsistencyResult]:
    """Review a sequence of decisions for consistency and adjacent jumps."""
    results = []

    for i, current in enumerate(decisions):
        jump = False
        action = current.action.value
        reason = current.reason

        if i > 0:
            prev = decisions[i - 1]
            diff = abs(current.recommended_delta_ev - prev.recommended_delta_ev)

            # Check adjacent jump only if they are in the same group
            if current.group_id == prev.group_id and diff > max_adjacent_jump_ev:
                jump = True
                if action == "APPLY":
                    action = "REVIEW"
                    reason = f"Flagged adjacent jump of {diff:.2f} EV. {reason}".strip()

        results.append(
            BatchConsistencyResult(
                image_id=current.image_id,
                original_decision=current,
                final_action=action,
                flagged_jump=jump,
                consistency_reason=reason,
            )
        )

    return results
