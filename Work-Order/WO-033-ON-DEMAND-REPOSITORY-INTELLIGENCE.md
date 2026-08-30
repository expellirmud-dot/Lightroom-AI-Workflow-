# Work Order 033: On-Demand Repository Intelligence Governance

## Status

COMPLETED

## Authority

Owner task attached on 2026-08-30. The attachment defines the acceptance
criteria, safety boundary, validation, commit, and push authority for this Work
Order.

## Goal

Keep Serena and CodeGraph available while removing mandatory activation,
verification, broad orientation, duplicate source retrieval, and default
blocking from project preflight. Unused capabilities report `NOT_REQUIRED`.

## Scope and Risk

- Classification: governance behavior and regression tests.
- Risk: low runtime risk; medium project-policy risk.
- Runtime mode: documentation/static-governance only; no Lightroom or XMP access.
- Capability IDs: governance only; no runtime capability maturity promotion.

## Allowed Files

- `AGENTS.md`
- `.agents/skills/project-read-first/**`
- `tests/test_project_read_first_skill.py`
- `tests/__init__.py` (adjacent full-suite import collision found during validation)
- `docs/VALIDATION_REGISTER.md`
- `Work-Order/WO-033-ON-DEMAND-REPOSITORY-INTELLIGENCE.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden Files and Actions

- Do not modify, stage, or commit `.serena/project.yml`.
- Do not modify Lightroom runtime, session, exposure, cache, photo, RAW, XMP,
  catalog, or preview-cache content.
- Do not uninstall or globally disable Serena or CodeGraph.
- Do not change user-global Codex configuration.
- Do not force-push, reset destructively, or include unrelated owner changes.

## Acceptance Criteria

1. Serena and CodeGraph are explicitly `ON_DEMAND` and remain available.
2. Documentation-only and ordinary bounded implementation need neither MCP.
3. Default MCP status is `NOT_REQUIRED`.
4. MCP-specific blocking is conditional on a genuinely required capability
   that has no smaller safe authoritative substitute.
5. Same-thread delta preflight remains supported.
6. Smallest-sufficient retrieval and anti-duplication rules are explicit.
7. Governance regression tests, full relevant tests, and diff/scope checks pass.
8. `.serena/project.yml` is excluded from the commit.
9. Local `tests.*` imports resolve to this repository rather than an unrelated
   site-packages package.

## Required Validation

- `python -m pytest tests/test_project_read_first_skill.py -q`
- execute the preflight script and verify default MCP statuses
- `python -m pytest -q`
- `python -m compileall -q src tests`
- `git diff --check`
- inspect final Git status/diff and staged scope

## Documentation Impact

- `AGENTS.md`: `UPDATED`
- `.agents/skills/project-read-first/**`: `UPDATED`
- `docs/VALIDATION_REGISTER.md`: update only after evidence executes
- `docs/INDEX.md`: `REVIEWED_NO_CHANGE`
- runtime/safety/architecture/AI/user documents: `NOT_APPLICABLE`

## Delivery Authority

After all validation passes, commit the bounded governance change and push
`main` to `origin/main` only when safely fast-forwardable. Never force-push.

## Executed Evidence

- TDD RED: 4 expected governance-contract failures.
- Focused GREEN: 12 passed.
- Preflight script: Serena and CodeGraph `NOT_REQUIRED`; decision `READY`.
- Adjacent import regression: `tests/test_handoff.py` passed after the local
  package marker prevented collision with site-packages `tests`.
- Full suite: 243 passed, 2 skipped, 2 environment/dependency warnings.
- Python compileall and `git diff --check`: passed.
- `.serena/project.yml`: unchanged and excluded.

## Remaining Risks

- Automated governance tests do not prove either MCP runtime, by design;
  availability is checked only when a concrete task requires the capability.
- Pytest reports a non-fatal Windows temp cleanup `PermissionError` after its
  successful summary, plus two pre-existing dependency/deprecation warnings.
