# Documentation Index

This is the canonical index of maintained project authority.

## Authority order

1. Active Work Order
2. `AGENTS.md`
3. Safety contracts
4. Canonical workflow and architecture
5. AI/data contracts and accepted decisions
6. Tests and implementation
7. User documentation

## Required read set

Every repository-changing task completes or validly reuses a read-first
preflight for `AGENTS.md`, this index, `Work-Order/CURRENT_WORK_ORDER.md`, the
active Work Order, and every document whose trigger matches the task. Use delta
preflight while repository-truth fingerprints remain unchanged.

## Maintained documents

| Document | Purpose | Read/update trigger |
|---|---|---|
| `AGENTS.md` | repository-wide governance and runtime invariants | every task; governance or workflow change |
| `docs/FOLDER_JOB_WORKFLOW.md` | approved Exposure Session/pass target lifecycle and current-runtime boundary | workflow, plugin, session, pass, AI handoff, render loop, or apply change |
| `docs/ARCHITECTURE.md` | components, ownership, data flow, IPC | architecture or integration change |
| `docs/DIAGNOSTIC_PREFLIGHT.md` | diagnostic-first Lightroom folder readiness contract | diagnostics, eligibility, cache, CLI, bridge, or metadata-readiness change |
| `docs/XMP_SAFETY.md` | allowed mutation and transaction contract | any XMP-related change |
| `docs/AI_JUDGE_CONTRACT.md` | external AI inputs, decision schema, validation | AI, schema, skill, batching, or confidence change |
| `docs/DECISIONS.md` | accepted durable design decisions | material design accepted or superseded |
| `docs/CAPABILITY_MATRIX.md` | capability maturity truth | capability status change |
| `docs/VALIDATION_REGISTER.md` | executed validation evidence | new validation |
| `docs/PROJECT_STATUS.md` | current phase, risks, next gate | phase or risk change |
| `README.md` | user setup and operation | user workflow or command change |
| `Work-Order/CURRENT_WORK_ORDER.md` | pointer to the only active Work Order | task transition |
| `Work-Order/WO-*.md` | bounded implementation authority and evidence | its own task |
| `.agents/skills/exposure-judgment/SKILL.md` | subject-aware exposure judgment | exposure rules change |
| `.agents/skills/batch-consistency-review/SKILL.md` | grouping and reference consistency | batch consistency change |
| `.agents/skills/image-relevance-triage/SKILL.md` | relevance/test-shot/accidental triage | relevance rules change |
| `.agents/skills/visual-quality-safety/SKILL.md` | blur/focus/highlight safety | quality rules change |
| `.agents/skills/project-read-first/SKILL.md` | repository preflight, reuse, delta checks, and dirty classification | every repository-changing task; preflight protocol change |

## Placement rules

- Runtime/session workflow → `docs/FOLDER_JOB_WORKFLOW.md`
- Component boundaries → `docs/ARCHITECTURE.md`
- Diagnostic readiness → `docs/DIAGNOSTIC_PREFLIGHT.md`
- XMP safety → `docs/XMP_SAFETY.md`
- AI schema and judgment → `docs/AI_JUDGE_CONTRACT.md`
- Durable rationale → `docs/DECISIONS.md`
- Task scope/evidence → active Work Order

Do not create duplicate status or authority documents.

## Closeout checklist

- Review `README.md` and all affected documents in this index.
- Record executed evidence only after commands actually pass.
- Reconcile capability status, project status, Work Order, and current pointer.
- Confirm no conflicting authority remains.
- Confirm runtime artifacts and backups are not tracked.
