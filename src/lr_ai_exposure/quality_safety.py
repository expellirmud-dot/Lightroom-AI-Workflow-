"""Visual quality safety rules.

Implements WO-010.2: Assess technical usability and enforce safety outcomes.
"""

from __future__ import annotations

from typing import Sequence

from lr_ai_exposure.image_triage import QualityAction, TriageDecision


def apply_quality_safety_rules(decision: TriageDecision) -> TriageDecision:
    """Enforce visual quality safety rules on a triage decision.
    
    Downgrades the action to REVIEW or SKIP if severe technical flaws exist.
    """
    flags = set(f.lower() for f in decision.quality_flags)
    
    # Severe flaws that make it unsafe to modify or meaningless to keep
    skip_flags = {
        "irreversibly_clipped",
        "severe_blur",
        "severe_obstruction",
        "focus_failure",
        "unusable",
    }
    
    review_flags = {
        "clipped_highlights",
        "motion_blur",
        "conflicting_evidence",
    }
    
    new_action = decision.quality_action
    reason = decision.reason
    
    if flags.intersection(skip_flags):
        if new_action != QualityAction.SKIP:
            new_action = QualityAction.SKIP
            reason = f"Downgraded to SKIP due to severe quality flags: {flags.intersection(skip_flags)}. {reason}".strip()
    elif flags.intersection(review_flags):
        if new_action == QualityAction.APPLY:
            new_action = QualityAction.REVIEW
            reason = f"Downgraded to REVIEW due to quality flags: {flags.intersection(review_flags)}. {reason}".strip()
            
    if new_action == decision.quality_action:
        return decision
        
    # Return a new instance with the updated action and reason
    from dataclasses import replace
    return replace(decision, quality_action=new_action, reason=reason)
