# Documentation Index

This is the canonical index of maintained project authority.

## Authority order

1. Active Work Order
2. `AGENTS.md`
3. Safety contracts
4. Canonical workflow and architecture
5. AI/data contracts and accepted decisions
6. Roadmap, capability/status and executed-evidence registers
7. Tests and implementation
8. User documentation

`docs/ROADMAP.md` is the only current Project Roadmap. Files under
`Work-Order/` whose names contain `ROADMAP` are historical execution artifacts
unless `Work-Order/CURRENT_WORK_ORDER.md` explicitly activates them.

`docs/ROADMAP.md` controls project direction and phase gates; it does not
override an active Work Order or implementation/safety truth.

## Required read set

Every repository-changing task completes or validly reuses a read-first
preflight for `AGENTS.md`, this index, `Work-Order/CURRENT_WORK_ORDER.md`, the
active Work Order, and every document whose trigger matches the task. Use delta
preflight while repository-truth fingerprints remain unchanged.

For planning/next-work decisions, also read `docs/ROADMAP.md`,
`docs/PROJECT_STATUS.md` and the relevant capability/evidence rows before
creating another Work Order.

## Maintained documents

| Document | Purpose | Read/update trigger |
|---|---|---|
| `AGENTS.md` | repository-wide governance, runtime invariants and anti-loop execution rules | every task; governance or workflow change |
| `docs/ROADMAP.md` | current project phase, exit gates, post-MVP backlog and Work Order activation policy | planning, phase transition, new Work Order |
| `docs/FOLDER_JOB_WORKFLOW.md` | canonical Exposure Session/pass lifecycle | workflow, plug-in, session, pass, AI handoff, render loop or apply change |
| `docs/ARCHITECTURE.md` | components, ownership, data flow and IPC | architecture or integration change |
| `docs/DIAGNOSTIC_PREFLIGHT.md` | diagnostic-first Lightroom folder readiness contract | diagnostics, eligibility, cache, CLI or bridge readiness change |
| `docs/XMP_SAFETY.md` | canonical Catalog mutation safety plus preserved legacy XMP safety | any mutation-boundary or XMP-related change |
| `docs/AI_JUDGE_CONTRACT.md` | current external AI task/schema semantics and validation boundary | AI, schema, skill, batching or confidence change |
| `docs/DECISIONS.md` | accepted durable design/governance decisions | material design accepted or superseded |
| `docs/CAPABILITY_MATRIX.md` | capability maturity truth | capability status/evidence boundary change |
| `docs/VALIDATION_REGISTER.md` | actually executed validation evidence | new validation or evidence reconciliation |
| `docs/PROJECT_STATUS.md` | current phase, active gate, risks and next proof | phase, gate or risk change |
| `README.md` | user setup and current canonical operation | user workflow or command change |
| `Work-Order/CURRENT_WORK_ORDER.md` | pointer to the only active Work Order | task transition |
| `Work-Order/WO-*.md` | bounded implementation authority and historical evidence | its own task |
| `.agents/skills/exposure-judgment/SKILL.md` | current exposure judgment guidance | exposure rules/schema change |
| `.agents/skills/batch-consistency-review/SKILL.md` | current exposure grouping/reference guidance | batch consistency/schema change |
| `.agents/skills/image-relevance-triage/SKILL.md` | dormant compatibility guidance unless task explicitly activates relevance | explicit post-MVP relevance scope change |
| `.agents/skills/visual-quality-safety/SKILL.md` | exposure-risk guidance; broader quality triage dormant unless task activates it | exposure-risk or explicit post-MVP quality scope change |
| `.agents/skills/project-read-first/SKILL.md` | preflight, reuse, delta checks and dirty classification | every repository-changing task; preflight protocol change |

## Placement rules

- Project direction / phase / next gate → `docs/ROADMAP.md`
- Current snapshot / blockers → `docs/PROJECT_STATUS.md`
- Capability maturity → `docs/CAPABILITY_MATRIX.md`
- Executed proof → `docs/VALIDATION_REGISTER.md`
- Runtime/session workflow → `docs/FOLDER_JOB_WORKFLOW.md`
- Component boundaries → `docs/ARCHITECTURE.md`
- Diagnostic readiness → `docs/DIAGNOSTIC_PREFLIGHT.md`
- Mutation/XMP safety → `docs/XMP_SAFETY.md`
- AI schema and judgment → `docs/AI_JUDGE_CONTRACT.md`
- Durable rationale → `docs/DECISIONS.md`
- Task scope/evidence → active Work Order

Do not create duplicate status, roadmap, evidence or authority documents.

## Work Order anti-loop check

Before creating a new Work Order, classify the trigger:

- defect inside the active acceptance gate → current Work Order remediation;
- documentation/instruction mismatch → current Work Order closeout
  reconciliation;
- new capability/boundary/product requirement → candidate new Work Order;
- future enhancement → roadmap backlog.

A new Work Order must identify the roadmap gate it advances and an explicit
terminal evidence condition.

## Closeout checklist

- Review `README.md` and every affected maintained document above.
- Record executed evidence only after commands or live checks actually occur.
- Reconcile capability status, project status, roadmap phase, Work Order and
  current pointer.
- Confirm no conflicting current authority remains.
- Confirm historical Work Orders/roadmaps are not being treated as active.
- Confirm runtime artifacts, user photographs, backups and credentials are not
  tracked.
