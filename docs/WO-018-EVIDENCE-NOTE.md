# WO-018 Evidence Note: Single-Pass AI Triage and Exposure Judgment

## Objective
Use each cached preview exactly once for relevance, quality triage, and exposure judgment. Ensure all outputs are deterministic under a fixed model/configuration, missing previews are skipped safely, and low-confidence decisions route to `REVIEW`.

## Process and Evidence

1. **Unified AI Judgment Contract (`src/lr_ai_exposure/ai_judge.py`):**
   - Implemented `SinglePassDecision` combining WO-010.1 (Exposure) and WO-010.2 (Triage) into a single deterministic step per image.
   - Requires exactly one `ManifestEntry` per preview, eliminating double-generation loops.
   - Required fields: `relevance_verdict`, `quality_verdict`, `delta_ev`, `confidence`, `highlight_risk`, `shadow_risk`, `subject_rationale`, `scene_rationale`, `batch_consistency_group`, and `reason`.

2. **Validation and Clamping:**
   - Evaluated inputs via `validate_single_pass_decision()`.
   - `delta_ev` is strictly clamped to `[-max_delta_ev, max_delta_ev]`.
   - `confidence < 0.8` automatically downgrades `KEEP` verdicts to `REVIEW` with an explicit reason code prepended.
   - Verifies inputs match finite criteria and `Verdict` enum bounds (`KEEP`, `REVIEW`, `SKIP`).

3. **Deterministic Batch Mocking:**
   - Implemented `analyze_job_single_pass(manifest)`.
   - Bypasses missing entries safely (`extraction_status != "FOUND"` yields a `SKIP`).
   - Mock decisions reliably generate a positive test case for each `FOUND` image.

## Validation Results
- Pytest `tests/test_ai_judge.py` passes 4 specific regression tests covering: valid inputs, confidence downgrades, EV clamping, and full manifest batch evaluation.
- `compileall -q src` confirms clean syntax.

## Conclusion
WO-018 is complete. The system unifies evaluation, safely consuming cache previews in one pass and producing rigorous, deterministic exposure logic ready for XMP generation.
