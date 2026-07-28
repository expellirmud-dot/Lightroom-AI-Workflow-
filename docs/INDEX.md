# Documentation Index

This file is the canonical index of maintained project documentation.

Its purpose is to tell coding agents and maintainers:

- Which documents are authoritative
- What each document governs
- When each document must be read
- What changes require that document to be reviewed
- Which documents are historical or superseded

## Authority Order

1. Active Work Order
2. `AGENTS.md`
3. Safety contracts
4. Architecture and data contracts
5. Architecture decisions
6. Tests and implementation
7. User-facing documentation

When two documents at the same authority level conflict, stop and report
the conflict rather than choosing silently.

## Required Read Set

Every coding task must read:

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. The active Work Order
5. Documents marked as required by the active Work Order
6. Documents in the table below whose review triggers match the task

## Maintained Documents

| Document | Authority / Purpose | Read When | Review or Update When |
|---|---|---|---|
| `AGENTS.md` | Repository-wide execution, safety, validation, and closeout rules | Every task | Governance, workflow, authority, or completion rules change |
| `README.md` | User-facing project purpose, setup, commands, and current capabilities | Setup or user workflow tasks | Installation, commands, capabilities, or usage changes |
| `docs/ARCHITECTURE.md` | System boundaries, components, ownership, and canonical data flow | Architecture or integration work | Modules, boundaries, data flow, IPC, or responsibilities change |
| `docs/XMP_SAFETY.md` | XMP mutation boundary and safe-write contract | Any XMP-related task | Editable properties, backup, parsing, validation, or write behavior changes |
| `docs/AI_JUDGE_CONTRACT.md` | Vision AI input, output, validation, and exposure objective | AI analysis tasks | Prompt contract, schema, batching, confidence, or decision rules change |
| `docs/DECISIONS.md` | Accepted architecture decisions and rationale | Design decisions or disputed approaches | A material decision is accepted, replaced, or superseded |
| `docs/INDEX.md` | This file — canonical documentation index | Every task | Any document added or removed from this index |
| `.agents/skills/project-read-first/SKILL.md` | Repository preflight skill: resolve Git root, verify Serena/CodeGraph, read authority docs, produce bounded decision | Every implementation or debugging task | Preflight protocol, document read policy, or decision values change |
| `Work-Order/CURRENT_WORK_ORDER.md` | Pointer to the only authorized current Work Order | Every task | Work starts, completes, blocks, or transitions |
| `Work-Order/WO-*.md` | Bounded implementation authority and completion evidence | Its own task | Scope, acceptance criteria, status, evidence, or closeout changes |

## Documentation Placement Rules

Store information in the narrowest canonical location:

- Repository-wide execution rules → `AGENTS.md`
- User setup and usage → `README.md`
- Components and system flow → `docs/ARCHITECTURE.md`
- XMP invariants and write safety → `docs/XMP_SAFETY.md`
- AI request/response behavior → `docs/AI_JUDGE_CONTRACT.md`
- Durable design decisions and rationale → `docs/DECISIONS.md`
- Task-specific scope and evidence → active Work Order

Do not create duplicate status summaries when an existing canonical file
can be updated.

## Documentation Lifecycle

Documents must be classified as one of:

- `ACTIVE` — current authority
- `HISTORICAL` — retained as evidence but not current authority
- `SUPERSEDED` — replaced by another named document
- `DRAFT` — not authoritative

A superseded document must identify its replacement.
Historical and draft documents must not be used as current implementation
authority.

## New Canonical Documents (registered by WO-003)

| Document | Authority / Purpose | Read When | Update Trigger |
|---|---|---|---|
| `docs/PROJECT_STATUS.md` | Current project phase, risks, and next seam | Setup or integration tasks | Phase change, risks updated, or next seam changes |
| `docs/CAPABILITY_MATRIX.md` | Capability maturity register and status model | Architecture or capability work | Capability status changes |
| `docs/VALIDATION_REGISTER.md` | Executed evidence and validation scope | Validation or closeout tasks | New validation executed |

## Closeout Checklist

Before closing every Work Order:

- [ ] Review `README.md`
- [ ] Review every affected document in this index
- [ ] Update architecture or contracts when repository truth changed
- [ ] Record material decisions in `docs/DECISIONS.md`
- [ ] Record limitations and remaining risks
- [ ] Update the active Work Order with truthful validation evidence
- [ ] Reconcile `Work-Order/CURRENT_WORK_ORDER.md`
- [ ] Confirm this index still lists all canonical documents
- [ ] Confirm no duplicate or contradictory authority was introduced
