# WO-009 — AI Decision Contract and Mock Judge

STATUS: PLANNED

## Objective

Implement the validated exposure-decision contract and a deterministic offline mock judge. No external AI call is authorized.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| AI decision schema | NOT_STARTED | TESTED |
| Deterministic mock judge | NOT_STARTED | TESTED |
| Exposure delta limiting | NOT_STARTED | TESTED |

## Scope

- Define exactly one decision per manifest image.
- Preserve image identity and order.
- Validate numeric signed-decimal `delta_ev`, confidence, reject flag, and reason.
- Clamp delta to configured limits.
- Reject unknown IDs, duplicates, missing decisions, malformed values, and low-confidence automatic application.
- In dry-run/mock mode, return deterministic zero-EV decisions.
- No network, credentials, real model, XMP, or Lightroom mutation.

## Validation

Run focused schema and boundary tests, full pytest, compileall, diff check, and Git status review.

## Closeout

Update contracts and traceability documents, commit once, do not push, and do not begin WO-010.
