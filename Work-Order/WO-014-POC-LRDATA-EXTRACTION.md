# WO-014: Proof of Concept - Extract LRDATA Preview

## Objective
Extract a single image from the Lightroom preview cache (`.lrdata`) as a Proof of Concept (POC) for future system development.

## Special Authorization
This Work Order explicitly overrides the `AGENTS.md` Non-Negotiable Boundary regarding `.lrdata` access. The AI agent is authorized to read and extract data from the Lightroom preview cache (`.lrdata` or `.lrcat-data`) for the purpose of this isolated POC only.

## Scope
- Allowed Files: `C:\Users\Expellirmud\Pictures\LR\ToTo\ToTo Previews.lrdata`, `C:\Users\Expellirmud\Pictures\LR\ToTo\ToTo.lrcat-data`, Python scratch scripts for extraction.
- Excluded: No modifications to the Lightroom Catalog (`.lrcat`). Read-only operations on the cache.

## Acceptance Criteria
- A script successfully extracts at least one JPEG preview from the Lightroom cache.
- The extracted image is saved to a verifiable output directory.

## Status
ACTIVE
