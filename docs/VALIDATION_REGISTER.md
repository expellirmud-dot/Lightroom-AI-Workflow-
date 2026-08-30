# Validation Register

Canonical executed-evidence register for Lightroom AI Exposure Assist.

This register records only evidence that was actually executed and whose scope is understood. Historical rows containing `pending`, `THIS_COMMIT`, or claims that contradicted later repository/runtime truth were removed during WO-029. Git history remains available for forensic detail.

## Evidence levels

- **Automated** — focused/full pytest, compile, CLI smoke, static contracts.
- **Integrated** — multiple production components exercised together.
- **Live Lightroom** — real Lightroom Classic, real catalog selection/cache, and representative runtime artifacts.
- **Live XMP Apply** — real prepared job, real sidecar transaction, Lightroom metadata read-back.

Automated evidence cannot by itself prove Lightroom Lua runtime behavior.

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
| VLD-088 | 2026-07-29 | XMP transaction tests | backup, SHA-256, write verification, rollback paths passed | `a65b953` |
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
| VLD-107 | 2026-07-29 | Real Lightroom selection → cache preview → external decision import | `REAL_LIGHTROOM_SMOKE_PASS`; 1 decision; `ANALYZE_ONLY`; applied 0; no XMP mutation | `243c405` |
| VLD-108 | 2026-07-29 | Full suite at closeout | 196 passed, 2 skipped | `243c405` |

WO-028 proved the real Lightroom identity/cache/decision path. It did not prove the new WO-029 full-folder Prepare/Apply commands.

## WO-029 — Prepared current-folder lifecycle

Automated evidence applies to branch `wo-029-folder-job-lifecycle` at head `4fd50d6faeb3f4b1e3ad8184961ce1ca94bfc553`, GitHub Actions run `30413267495` (run 50).

| ID | Date | Evidence | Result | Scope |
|---|---|---|---|---|
| VLD-109 | 2026-07-29 | Focused prepared-job tests on Windows Python 3.12 | success | folder lifecycle, self-contained skill bundle, immutable artifact hashes, saved-job CLI/apply, plug-in contracts |
| VLD-110 | 2026-07-29 | Focused prepared-job tests on Windows Python 3.13 | success | same scope |
| VLD-111 | 2026-07-29 | Full pytest suite on Windows Python 3.12 and 3.13 | success on both matrix jobs | all tracked tests |
| VLD-112 | 2026-07-29 | CLI config smoke on Windows Python 3.12 and 3.13 | success | canonical `manual_app` external-file configuration |
| VLD-113 | 2026-07-29 | Integration suite on Windows Python 3.12 and 3.13 | success | cross-component Python workflow |
| VLD-114 | 2026-07-29 | `compileall` for `src` and `tests` | success on both matrix jobs | Python syntax/import surface |
| VLD-115 | 2026-07-29 | `git diff --check` | success on both matrix jobs | tracked diff hygiene |
| VLD-116 | 2026-07-29 | clean working-tree check | success on both matrix jobs | no runtime/private artifacts created by CI |
| VLD-117 | 2026-07-29 | Immutable prepared-job integrity test | success on both matrix jobs | altered task/skills/schema/manifest/selection inputs fail closed before decision import/apply |

Both Windows matrix jobs concluded `success`. Focused, full, config, integration, compile, diff, and clean-tree steps all concluded `success`.

### Post-merge real Lightroom observation

| ID | Date | Evidence | Result | Scope |
|---|---|---|---|---|
| VLD-118 | 2026-08-30 | Owner-operated Lightroom plug-in 1.1.0 build 2 | both Prepare/Apply menu commands loaded; Prepare stopped with `The active Lightroom folder contains no eligible proprietary-RAW master photos.` | proves menu availability and live eligibility failure only; Python/cache/CLI/apply not reached |

## WO-029 unresolved live gates at supersession

- Open exactly one real Lightroom folder and run **Prepare Current Folder**.
- Confirm the plug-in enumerates all eligible proprietary-RAW masters without manual photo selection.
- Confirm one cache handoff produces `manifest.json`, all available previews, `AI_TASK.md`, `AI_SKILLS.md`, schema, state, immutable artifact hashes, and the job-scoped decisions folder.
- Give only that prepared job folder to an external vision AI and produce the exact decision set.
- Run **Apply Prepared Job** against the matching active folder.
- Confirm backup paths/hashes, old/delta/new exposure, terminal settlement for every eligible image, rollback safety, and Lightroom metadata refresh.

These gates did not pass before PR #1 merged. WO-029 is now superseded rather
than active. Its missing proof must not be inherited by the target Exposure
Session architecture.

## WO-030 documentation evidence

WO-030 defines target documentation and governance only. No row in this section
claims session/pass, diagnostic, rerender, metadata-sync, or real XMP runtime
behavior.

| ID | Date | Evidence | Result | Scope |
|---|---|---|---|---|
| VLD-119 | 2026-08-30 | `tests/test_project_read_first_skill.py` and live preflight-script self-test | 8 passed; script returned `DIRTY_CLASSIFICATION=NON_BLOCKING`, explicit exclusions, correct `origin/main`, and `PREFLIGHT_DECISION=READY` | governance/read-first behavior only |
| VLD-120 | 2026-08-30 | focused current-runtime regression guards | 18 passed | static Lightroom plug-in, prepared-job lifecycle, saved-job CLI compatibility |
| VLD-121 | 2026-08-30 | source/test compile and documentation diff hygiene | compileall passed for source/tests; `git diff --check` passed with line-ending normalization warnings only | syntax and diff hygiene; no runtime execution |

## Current limitations

- CI statically inspects Lua contracts; the GitHub runner does not prove the Lightroom-hosted Lua runtime.
- Real apply requires an existing XMP sidecar containing one unambiguous finite `crs:Exposure2012` value.
- DNG/JPEG/TIFF/PSD/video/virtual-copy inputs are intentionally excluded from the sidecar-only writable target set.
- The legacy Google API provider remains compatibility code, but it is not the canonical production route and its quota is not a WO-029 blocker.
