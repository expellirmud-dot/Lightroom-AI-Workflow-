# WO-030 - Exposure Session Documentation Reconciliation

## Status

COMPLETED - DOCUMENTATION AND GOVERNANCE ONLY

## Owner decision

The accepted target architecture is a provider-agnostic Exposure Session made
of immutable iterative passes. Lightroom remains the authoritative renderer,
external vision AI owns scene/group/outlier judgment, deterministic Python
owns validation/convergence/XMP safety, and the Lightroom plug-in remains a
thin coordinator.

The pre-existing local modification to `.serena/project.yml` is owner-owned,
unrelated to this Work Order, and classified
`NON_BLOCKING_PREEXISTING_OWNER_CHANGE`. It must not be edited, restored,
stashed, staged, or committed by this Work Order.

## Objective

Reconcile canonical documentation and repository governance before any
runtime implementation. Define the target session/pass lifecycle,
diagnostic-first preflight, provider-neutral file contract, render freshness,
convergence, oscillation, safe stop behavior, and the boundaries preserved
from the existing cache and XMP safety implementation.

## Allowed files

- `AGENTS.md`
- `README.md`
- `.agents/skills/project-read-first/`
- canonical Markdown files under `docs/`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `Work-Order/WO-029-FOLDER-JOB-LIFECYCLE.md`
- this Work Order

## Forbidden changes

- No files under `src/` or `tests/`.
- No Lightroom plug-in behavior or metadata changes.
- No configuration, dependency, workflow, or CI changes.
- No RAW, JPEG, XMP, catalog, preview-cache, or runtime artifact access.
- No real XMP apply.
- No modification, restore, stash, stage, or commit of
  `.serena/project.yml`.
- No commit or push.

## Required documentation outcomes

- Replace the canonical one-shot prepared-folder lifecycle with the approved
  Exposure Session and immutable-pass target architecture while labeling the
  current runtime truth accurately.
- Use `parent_pass_id` for pass lineage.
- Label `0.10 EV`, `+/-1.0 EV/pass`, `+/-2.0 EV cumulative`, and
  `maximum_passes = 4` as pilot defaults, not production constants.
- Require render freshness to reconcile expected `Exposure2012`, a new
  pass/generation identity, and refreshed preview evidence/hash.
- Persist scene groups across passes by default, with safe REVIEW or split
  behavior when evidence conflicts.
- Make `DIAGNOSE_CURRENT_FOLDER` the first implementation seam.
- Make metadata synchronization fail closed only when safety cannot be
  proven; do not require owner metadata writes without evidence.
- Preserve read-only preview-cache extraction and transactional XMP safety.
- Separate optional provider/API adapters from the canonical file workflow.
- Reconcile WO-029, merged PR #1, `main`, capability status, validation truth,
  and README guidance.
- Classify dirty state as `NON_BLOCKING`, `BLOCKING`, or `CRITICAL`, permit
  same-thread read-first reuse, and require delta preflight when repository
  truth is unchanged.

## Validation

```powershell
uv run pytest -q tests/test_project_read_first_skill.py
uv run pytest -q tests/test_lightroom_plugin.py tests/test_job_lifecycle.py tests/test_saved_job_cli.py
python -m compileall -q src
python -m compileall -q tests
git diff --check
git status --short
```

Runtime tests are regression guards only. This Work Order does not claim that
the target session/pass architecture is implemented.

## Closeout policy

Close only after documentation consistency, focused regression validation,
diff hygiene, allowed-file scope, and preservation of the owner-owned Serena
change are verified. Leave no active implementation Work Order; implementation
requires separate owner authorization.

## Closeout evidence

- `uv run pytest -q tests/test_project_read_first_skill.py`: 8 passed.
- `uv run pytest -q tests/test_lightroom_plugin.py tests/test_job_lifecycle.py tests/test_saved_job_cli.py`: 18 passed.
- `python -m compileall -q src`: passed.
- `python -m compileall -q tests`: passed.
- `git diff --check`: passed; Git reported line-ending normalization warnings
  only.
- Direct preflight script self-test: correct `origin/main`, one output block,
  explicit `NON_BLOCKING` exclusions, terminal `READY`.
- `.serena/project.yml` remained owner-owned, modified, unstaged, and outside
  this Work Order's changes.
- No runtime/source/plugin/config/test files, photographs, XMP, catalog, live
  preview cache, or runtime artifacts were changed by this Work Order.

## Documentation impact classification

- `UPDATED`: governance/read-first policy, canonical workflow, architecture,
  diagnostic contract, AI contract, XMP safety, accepted decisions, project
  status, capability matrix, validation register, README, WO-029 outcome, and
  current Work Order pointer.
- `REVIEWED_NO_CHANGE`: four runtime-bundled visual skills because changing
  them before target schema implementation would alter current AI behavior.
- `NOT_APPLICABLE`: source, plug-in, configuration, dependency, CI, and runtime
  implementation.
- `BLOCKED`: none for documentation closeout; implementation awaits a separate
  owner-authorized Work Order.
