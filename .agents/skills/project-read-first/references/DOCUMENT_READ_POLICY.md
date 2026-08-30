# Document Read Policy

This reference document defines how the project-read-first skill
selects and reads documents during preflight.

## Mandatory Full Reads or Valid Same-Thread Reuse

The skill must require complete reads of:

1. `AGENTS.md` — repository-wide execution, safety, and closeout rules
2. `docs/INDEX.md` — canonical documentation index determining document authority
3. `Work-Order/CURRENT_WORK_ORDER.md` — pointer to the active Work Order
4. The active Work Order file itself (as pointed to by step 3)

These four files define authority and scope and must not be replaced by
summaries. Their completed full reads may be reused in the same thread when
HEAD, the active Work Order pointer, relevant-file status/hash, task context,
and available conversation context remain unchanged.

Before every subsequent implementation step, use delta preflight. Repeat a
full read only when its file or authority fingerprint changed, context is no
longer available, or repository policy explicitly requires it.

## Targeted Read Policy

The skill must avoid unnecessary broad reads. Use targeted section
reads (offset/limit around the relevant section) as the default.

### Default Targeted Behavior

| Document | Sections to Read |
|---|---|
| `docs/PROJECT_STATUS.md` | Status header, current objective, risks, and next seam |
| `docs/CAPABILITY_MATRIX.md` | Status definitions plus rows for capability IDs named by the active Work Order |
| `docs/VALIDATION_REGISTER.md` | Schema/header and the latest entries relevant to the active capabilities |
| `README.md` | Only sections affected by installation, configuration, commands, usage, or supported behavior |
| Source code | Use the smallest sufficient tool: targeted search, bounded line reads, ordinary symbol lookup when useful, Serena for material semantic navigation, then CodeGraph for material dependency reasoning |

### Escalation Rules

Escalate to a full read when:

1. A safety contract governs the task (e.g., XMP safety, AI judge contract).
2. The active Work Order requires it.
3. Definitions are distributed across the file.
4. Targeted sections conflict or remain ambiguous.
5. Closeout requires confirming the complete document remains accurate.
6. `docs/INDEX.md` does not identify authority for a material project area.

### Forbidden Escalations

- Do not escalate to a full read of user-photo data, RAW files, Lightroom catalogs, or XMP sidecars containing real photography data.
- Do not escalate reads beyond what the active Work Order's Required Read Order allows.

## On-Demand Tool Selection and Anti-Duplication

Serena = `ON_DEMAND` for concrete semantic symbol/source/navigation questions.
CodeGraph = `ON_DEMAND` for concrete dependency, caller/callee, or impact
questions. Documentation-only work and ordinary bounded implementation proceed
without either MCP when targeted search and bounded reads are sufficient.

Never retrieve the same unchanged source body through multiple mechanisms
without a concrete reason. Do not repeat orientation, Serena activation or
configuration reads, broad graph exploration, or full-file reads merely because
another implementation step began. Reread only after a material file/truth
change, incomplete prior output, or a new concrete question.

## Priority Rules

When two documents at the same authority level (per `docs/INDEX.md`) conflict:

1. The active Work Order takes priority.
2. If both are Work Orders at equal level, the more recent commit wins.
3. If still conflicting, stop and report the conflict rather than choosing silently.

## Read Verification

After completing reads, the skill must confirm:

- Each file in the mandatory full-read list was successfully opened and non-empty.
- Reused reads identify the prior completed preflight and confirm unchanged
  fingerprints.
- Any targeted reads were scoped to the correct section (no unrelated sections absorbed).
- No forbidden documents (real photos, catalogs, preview caches) were read.
