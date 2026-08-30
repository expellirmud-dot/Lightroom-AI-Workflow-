from __future__ import annotations

from typing import Any

from lr_ai_exposure.ai_judge import SinglePassDecision, Action
from lr_ai_exposure.session import SessionState, ExposureHistory


def _quantize_ev(delta: float, step: float) -> float:
    if step <= 0:
        return round(float(delta), 4)
    return round(round(float(delta) / step) * step, 4)


def _pass_number_for_id(state: SessionState, pass_id: str) -> int:
    try:
        return state.passes.index(pass_id) + 1
    except ValueError as exc:
        raise ValueError(f"Pass {pass_id!r} is not present in session lineage") from exc


def evaluate_pass_convergence(
    state: SessionState,
    decisions: list[SinglePassDecision],
    pass_id: str,
) -> dict[str, Any]:
    """Evaluate frozen decisions against policy and update a session-state instance.

    Callers that are only planning an apply should pass a deep copy of the
    authoritative state. Session history is committed only after Lightroom
    confirms the Catalog mutation.
    """
    tolerance = float(state.policy.get("tolerance", 0.10))
    quantization = float(state.policy.get("quantization", 0.05))
    max_auto_delta = float(state.policy.get("maximum_delta_ev", 1.0))
    max_cumulative = float(state.policy.get("cumulative_delta_ev", 2.0))
    max_passes = int(state.policy.get("maximum_passes", 4))

    current_pass_number = _pass_number_for_id(state, pass_id)

    applied_count = 0
    review_count = 0
    pass_count = 0
    results: dict[str, str] = {}
    quantized_deltas: dict[str, float] = {}

    for decision in decisions:
        image_id = str(decision.image_id)
        if image_id not in state.images:
            continue

        img = state.images[image_id]
        img.scene_group_id = decision.scene_group_id
        img.is_reference = decision.is_reference

        if img.status == "REVIEW":
            review_count += 1
            results[image_id] = "SKIPPED_ALREADY_REVIEW"
            continue

        if decision.action == Action.REVIEW:
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW"
            continue

        delta = _quantize_ev(decision.delta_ev, quantization)
        quantized_deltas[image_id] = delta

        if decision.action == Action.PASS or abs(delta) <= tolerance:
            img.status = "PASS"
            pass_count += 1
            results[image_id] = "PASS"
            continue

        if abs(delta) > max_auto_delta:
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW_BOUNDS_EXCEEDED"
            continue

        if abs(img.cumulative_delta_ev + delta) > max_cumulative:
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW_CUMULATIVE_EXCEEDED"
            continue

        # Oscillation is intentionally conservative: one meaningful sign flip is
        # recorded, but automatic authority is removed only after repeated
        # evidence or a revisit of a prior exposure state.
        if img.history:
            last_hist = img.history[-1]
            if abs(last_hist.delta_ev) > tolerance and abs(delta) > tolerance:
                if (last_hist.delta_ev > 0 and delta < 0) or (
                    last_hist.delta_ev < 0 and delta > 0
                ):
                    img.oscillations += 1

            current_expected = (
                img.expected_exposure2012
                if img.expected_exposure2012 is not None
                else img.baseline_exposure2012
            )
            proposed_exposure = current_expected + delta
            for prior in img.history:
                if abs(proposed_exposure - prior.expected_exposure2012) < (tolerance / 2.0):
                    img.oscillations += 1
                    break

        if img.oscillations >= 2:
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW_OSCILLATION"
            continue

        if current_pass_number >= max_passes:
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW_MAX_PASSES"
            continue

        img.status = "ADJUST"
        img.cumulative_delta_ev = round(img.cumulative_delta_ev + delta, 4)
        img.previous_pass_id = pass_id

        current_expected = (
            img.expected_exposure2012
            if img.expected_exposure2012 is not None
            else img.baseline_exposure2012
        )
        expected = round(current_expected + delta, 4)
        img.expected_exposure2012 = expected
        img.history.append(
            ExposureHistory(
                pass_id=pass_id,
                delta_ev=delta,
                expected_exposure2012=expected,
            )
        )

        applied_count += 1
        results[image_id] = "ADJUST"

    all_settled = all(img.status in {"PASS", "REVIEW"} for img in state.images.values())
    if current_pass_number >= max_passes or applied_count == 0 or all_settled:
        for img in state.images.values():
            if img.status == "ADJUST":
                img.status = "REVIEW"
                results[img.image_id] = "REVIEW_MAX_PASSES"
        state.is_converged = True
    else:
        state.is_converged = False

    return {
        "applied": applied_count,
        "review": review_count,
        "pass": pass_count,
        "results": results,
        "quantized_deltas": quantized_deltas,
        "is_converged": state.is_converged,
        "pass_number": current_pass_number,
    }
