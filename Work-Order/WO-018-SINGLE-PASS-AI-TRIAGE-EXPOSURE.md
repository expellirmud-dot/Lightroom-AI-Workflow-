# WO-018: Single-Pass AI Triage and Exposure Judgment

## Objective
Use each cached preview exactly once for relevance, quality triage, and exposure judgment.

## Preconditions
- WO-017 produces valid cache-preview jobs.

## Scope
- Run one AI analysis pass per preview.
- Produce:
  - relevance verdict
  - quality/technical verdict
  - exposure recommendation
  - confidence
  - reason codes
- Do not generate a second 2048-pixel review preview.
- Low-confidence cases become `REVIEW`.

## Required Verdicts
- `KEEP`
- `REVIEW`
- `SKIP`

## Required Exposure Output
- `delta_ev`
- confidence
- highlight/shadow risk flags
- subject/scene rationale
- batch consistency group or reference

## Acceptance Criteria
- One cached preview is consumed once per image.
- No second preview generation occurs.
- Outputs are deterministic under a fixed model/configuration.
- Low-confidence images are routed to `REVIEW`.
- Batch exposure recommendations stay within configured safety bounds.

## Stop Conditions
- Preview resolution is insufficient for the required judgment.
- Model output cannot be validated against schema.
- Exposure recommendations exceed configured bounds.
- AI attempts to write XMP directly.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Status
CLOSED

