# Validation Register

Canonical executed-evidence register for Lightroom AI Exposure Assist.

LAST_RECONCILED: 2026-08-31

Only evidence that was actually executed or directly observed is recorded here.
A Work Order statement without enough execution detail may document intent or
implementation, but it does not silently promote capability maturity.

## Evidence levels

- **Automated** — focused/full pytest, compile, CLI smoke, static contracts.
- **Integrated** — multiple production components exercised together.
- **Live Lightroom** — real Lightroom Classic with real catalog/cache/runtime
  artifacts.
- **Live Catalog Apply** — real Develop mutation/observation through Lightroom.

Automated evidence cannot by itself prove Lightroom-hosted Lua/runtime behavior.

## Trusted historical baseline

### WO-024 — Reproducible CLI certification

| ID | Date | Evidence | Result | Commit / run |
|---|---|---|---|---|
| VLD-081 | 2026-07-29 | Full fixture/test suite | 181 passed, 2 skipped | `17a82dd` |
| VLD-082 | 2026-07-29 | `lr-ai-exposure --check-config` | exit 0 | `17a82dd` |
| VLD-083 | 2026-07-29 | ANALYZE_ONLY integration | 3 passed; apply unreachable | `17a82dd` |
| VLD-086 | 2026-07-29 | Windows Python 3.12 CI | success | runs `30382636338`, `30384086375` |
| VLD-087 | 2026-07-29 | Windows Python 3.13 CI | success | runs `30382636338`, `30384086375` |

### WO-025 — Transactional XMP apply pilot

| ID | Date | Evidence | Result | Commit |
|---|---|---|---|---|
| VLD-088 | 2026-07-29 | XMP transaction tests | backup, SHA-256, write verification and rollback paths passed | `a65b953` |
| VLD-089 | 2026-07-29 | two-key apply authorization tests | passed | `a65b953` |
| VLD-090 | 2026-07-29 | full suite | 185 passed | `a65b953` |

### WO-027 — Controlled batch expansion

| ID | Date | Evidence | Result | Commit |
|---|---|---|---|---|
| VLD-099 | 2026-07-29 | Stage A bounded batch | 5-image stage completed | `6061e2a` |
| VLD-103 | 2026-07-29 | checkpoint/resume isolation | settled images not repeated | `93eef731` |
| VLD-105 | 2026-07-29 | Stage C bounded batch/full suite | 50-image stage closed; 186 tests passed | `634d81a`, `8d95ca3` |

### WO-028 — Real Lightroom Analyze Only certification

| ID | Date | Evidence | Result | Commit |
|---|---|---|---|---|
| VLD-107 | 2026-07-29 | Real Lightroom selection → cache preview → decision import | `REAL_LIGHTROOM_SMOKE_PASS`; one decision; ANALYZE_ONLY; applied 0 | `243c405` |
| VLD-108 | 2026-07-29 | Full suite at closeout | 196 passed, 2 skipped | `243c405` |

WO-028 proved real Lightroom identity/cache/decision plumbing, not the later
whole-folder/session workflow.

## WO-029 — Prepared current-folder lifecycle

Automated branch evidence was recorded at head
`4fd50d6faeb3f4b1e3ad8184961ce1ca94bfc553`, Actions run `30413267495`.

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-109 | 2026-07-29 | Focused prepared-job tests, Windows 3.12 | success: lifecycle, skill bundle, hashes, saved-job CLI/apply, plug-in contracts |
| VLD-110 | 2026-07-29 | Focused prepared-job tests, Windows 3.13 | same scope, success |
| VLD-111 | 2026-07-29 | Full pytest, Windows 3.12/3.13 | success both jobs |
| VLD-112 | 2026-07-29 | CLI config smoke | success both jobs |
| VLD-113 | 2026-07-29 | Integration suite | success both jobs |
| VLD-114 | 2026-07-29 | `compileall` source/tests | success both jobs |
| VLD-115 | 2026-07-29 | `git diff --check` | success both jobs |
| VLD-116 | 2026-07-29 | clean-tree/private-artifact gate | success both jobs |
| VLD-117 | 2026-07-29 | immutable job integrity/tamper test | success both jobs |
| VLD-118 | 2026-08-30 | Owner-operated Lightroom legacy Prepare/Apply plug-in | commands loaded; Prepare returned zero eligible RAW; later whole-folder/session work superseded this blocker |

WO-029 remains historical/legacy evidence; its missing live gates are not
requirements that automatically reopen the canonical WO-037+ architecture.

## WO-030 — Target documentation / governance

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-119 | 2026-08-30 | project-read-first tests + live preflight self-test | 8 passed; `NON_BLOCKING`, exclusions recorded, READY; governance only |
| VLD-120 | 2026-08-30 | focused current-runtime regression guards | 18 passed; static/compatibility scope |
| VLD-121 | 2026-08-30 | compile + documentation diff hygiene | passed; no Lightroom runtime proof |

## WO-031 — Diagnose Current Folder

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-122 | 2026-08-30 | focused diagnostic/plug-in/CLI/prepared-job/XMP tests | 61 passed, 1 optional Lua-parser skip |
| VLD-123 | 2026-08-30 | full pytest suite | 218 passed, 2 skipped |
| VLD-124 | 2026-08-30 | config smoke, compileall, diagnostics, diff/scope inspection | passed; integration evidence only |

## WO-033 — On-Demand Repository Intelligence Governance

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-125 | 2026-08-30 | TDD RED governance run | four expected policy-contract failures |
| VLD-126 | 2026-08-30 | focused governance + preflight | 12 passed; Serena/CodeGraph correctly `NOT_REQUIRED`; READY |
| VLD-127 | 2026-08-30 | full pytest | 243 passed, 2 skipped, 2 environment/dependency warnings |
| VLD-128 | 2026-08-30 | compileall + `git diff --check` | passed |

## WO-038 — Contact-sheet package pipeline

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-129 | 2026-08-31 | TDD RED then focused contact-sheet/session/CLI/plug-in regressions | expected RED; GREEN 10 tests passed |
| VLD-130 | 2026-08-31 | full pytest, compileall, config smoke, diff check | all commands exited 0; local automated/integration proof only |

WO-038 supports `INTEGRATED` contact-sheet creation/integrity, not model quality.

## Reconciled missing current evidence

The following executed evidence existed in accepted Work Orders but was missing
from this canonical register. It is added here without changing its scope.

### WO-034 — Catalog Exposure runtime hardening

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-131 | 2026-08-30 | GitHub Actions `33326239821`, Windows Python 3.12/3.13 | PASS: focused/full, config, integration, compile, diff and clean-tree gates; Catalog-authoritative iterative implementation, no live Lightroom proof |

### WO-035 — Durable AI handoff workflow

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-132 | 2026-08-30 | GitHub Actions `33328089473`, Windows Python 3.12/3.13 | PASS: canonical session/handoff automation; no provider quality/live mutation claim |

### WO-036 — Lightroom live-test harness

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-133 | 2026-08-30 | post-merge GitHub Actions run #80 | success; deterministic pass-all/one-adjust test seeder certified; does not replace Lightroom live proof |

### WO-037 — Decoupled AI package workflow

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-134 | 2026-08-30 | PR certification run #85 (`33340357782`), Windows Python 3.12/3.13 | PASS: explicit Prepare / Import-Apply / Prepare Next architecture, full regression/certification; CI not Lightroom host |

### WO-039 — Catalog apply commit barrier

| ID | Date | Evidence | Result / scope |
|---|---|---|---|
| VLD-135 | 2026-08-31 | GitHub Actions run #91, Windows Python 3.12/3.13 | PASS: post-commit bounded verification, absolute-target/idempotent retry, fail-closed confirmation and legacy technical-state recovery; fixed path not yet live-rechecked |
| VLD-136 | 2026-08-31 | Live Lightroom session `sess-1788136092` before WO-039 fix | 324-image session reached apply; 21 requested absolute targets were later observed present in Develop, while same-callback verification recorded stale values and produced `PASS=303 / REVIEW=21 / verified applies=0`; this is defect-discovery evidence, not proof of the corrected barrier |

VLD-136 supersedes the interpretation that the project is still blocked at the
old zero-eligible whole-folder stage. It proves real whole-folder/session/apply
progress, but it must not be re-labeled as a successful WO-039 verification.

## Current live acceptance still pending

Current owner-operated proof must establish:

1. re-run `Import / Apply AI Results` on the affected session;
2. recognize all 21 already-present targets without a second delta;
3. recover only the recorded technical failure IDs;
4. produce `Verified Catalog applies: 21`, `PASS: 303`, `REVIEW: 0` and
   `RERENDER_REQUIRED`;
5. after Lightroom rerender, run `Prepare Next AI Package` and prove a fresh
   generation is accepted.

Only after those observations may the corresponding post-commit/iterative-loop
capabilities be promoted to complete `LIVE_VERIFIED` status.

## Known evidence gaps / deferred proof

- WO-032 states that whole-folder traversal and iterative schema changes were
  implemented/tested, but this register does not invent a missing exact command,
  run ID or test count. Later live session evidence independently supersedes the
  earlier whole-folder blocker.
- GitHub CI statically/automatically exercises Lua contracts but cannot replace
  Lightroom-hosted runtime proof.
- AI model/provider photographic quality and photographer calibration are
  intentionally deferred beyond the current technical closure gate.
- Legacy XMP/metadata synchronization evidence remains historical and is not a
  prerequisite for the canonical Catalog-authoritative iterative route.
