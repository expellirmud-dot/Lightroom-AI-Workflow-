# Relevance Reasoning Classes

Use these as internal reasoning labels, then map them to the strict
`relevance_verdict` field required by `decision-schema.json`.

## Map to KEEP

- KEEP_PRIMARY
- KEEP_SUPPORTING
- KEEP_CANDID

## Map to REVIEW

- REVIEW
- any uncertain test-shot, accidental, irrelevant, duplicate, or unusable case

## Map to SKIP

- SUGGEST_REJECT_TEST_SHOT, when evidence is strong
- SUGGEST_REJECT_ACCIDENTAL, when evidence is strong
- SUGGEST_REJECT_IRRELEVANT, when evidence is strong
- SUGGEST_REJECT_DUPLICATE, when the frame has no independent value
- SUGGEST_REJECT_UNUSABLE, when exposure correction cannot make it useful

SKIP is an exposure-processing decision only. It must never delete, reject, or
mutate the photograph.
