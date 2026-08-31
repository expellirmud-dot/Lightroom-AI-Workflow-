---
name: image-relevance-triage
description: Preserved relevance-triage guidance; dormant for the current exposure-only small-preview task unless AI_TASK.md explicitly activates relevance assessment.
---

# Image Relevance Triage

`AI_TASK.md` and `decision-schema.json` are authoritative.

## Current MVP mode — dormant

The current contact-sheet/small-preview Exposure Session task does **not**
authorize relevance, duplicate, accidental/test-shot or keep/reject judgment.
This skill is bundled for compatibility/progressive evolution but must not
silently activate those features.

For the current MVP:

- set `relevance_verdict=KEEP` for every in-scope decision;
- do not classify relevance, documentary value, duplicates, accidental frames
  or test shots;
- do not use `SKIP`/relevance `REVIEW` to settle an exposure problem;
- unresolved exposure evidence belongs in `action=REVIEW` under the exposure
  contract;
- do not infer keep/reject value from filename or small preview limitations.

## Future activation boundary

Broader relevance triage may be used only when a future `AI_TASK.md` explicitly
activates it and the generated schema/preview evidence supports that task.
Until then, historical relevance examples/references are non-authoritative for
current decision output.
