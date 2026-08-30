from __future__ import annotations

from typing import Any
from lr_ai_exposure.session import SessionState, SessionImageState, ExposureHistory
from lr_ai_exposure.ai_judge import SinglePassDecision, Action

def evaluate_pass_convergence(
    state: SessionState,
    decisions: list[SinglePassDecision],
    pass_id: str
) -> dict[str, Any]:
    """Evaluate decisions against convergence policy and update session state."""
    
    tolerance = state.policy.get("tolerance", 0.10)
    max_auto_delta = state.policy.get("maximum_delta_ev", 1.0)
    max_cumulative = state.policy.get("cumulative_delta_ev", 2.0)
    max_passes = state.policy.get("maximum_passes", 4)
    
    current_pass_number = len(state.passes) + 1
    
    applied_count = 0
    review_count = 0
    pass_count = 0
    
    results = {}
    
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
            
        if decision.action == Action.PASS or abs(decision.delta_ev) <= tolerance:
            img.status = "PASS"
            pass_count += 1
            results[image_id] = "PASS"
            continue
            
        delta = decision.delta_ev
        
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
            
        # Oscillation check
        # Detect: meaningful delta reverses sign, or no progress
        if len(img.history) > 0:
            last_hist = img.history[-1]
            if abs(last_hist.delta_ev) > tolerance and abs(delta) > tolerance:
                if (last_hist.delta_ev > 0 and delta < 0) or (last_hist.delta_ev < 0 and delta > 0):
                    img.oscillations += 1
                    
        if img.oscillations >= 2: # 2 reversals = bouncing back and forth
            img.status = "REVIEW"
            review_count += 1
            results[image_id] = "REVIEW_OSCILLATION"
            continue
            
        img.status = "ADJUST"
        img.cumulative_delta_ev += delta
        img.previous_pass_id = pass_id
        
        # We assume the delta will be applied perfectly
        expected = (img.expected_exposure2012 or 0.0) + delta
        img.expected_exposure2012 = expected
        
        img.history.append(ExposureHistory(
            pass_id=pass_id,
            delta_ev=delta,
            expected_exposure2012=expected
        ))
        
        applied_count += 1
        results[image_id] = "ADJUST"

    if current_pass_number >= max_passes:
        for img in state.images.values():
            if img.status == "ADJUST":
                img.status = "REVIEW"
                results[img.image_id] = "REVIEW_MAX_PASSES"
        state.is_converged = True
    elif applied_count == 0:
        state.is_converged = True
        
    return {
        "applied": applied_count,
        "review": review_count,
        "pass": pass_count,
        "results": results,
        "is_converged": state.is_converged
    }
