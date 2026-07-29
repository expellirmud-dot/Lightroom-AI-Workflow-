# Validation Register

Canonical executed-evidence register for Lightroom AI Exposure Assist.

This register records only evidence that was actually executed and whose scope
is understood. Historical rows containing `pending`, `THIS_COMMIT`, or claims
that contradicted later repository/runtime truth were removed during WO-029.
Git history remains available for forensic detail.

## Evidence levels

- **Automated** — focused/full pytest, compile, CLI smoke, static contracts.
- **Integrated** — multiple production components exercised together.
- **Live Lightroom** — real Lightroom Classic, real catalog selection/cache,
  and representative runtime artifacts.
- **Live XMP Apply** — real prepared job, real sidecar transaction, Lightroom
  metadata read-back.

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

WO-028 proved the real Lightroom identity/cache/decision path. It did not prove
the new WO-029 full-folder Prepare/Apply commands.

## WO-029 — Prepared current-folder lifecycle

Automated evidence applies to branch `wo-029-folder-job-lifecycle` at head
`451011ff08dbe540b0dc20fffc7c9b22ee6d4664`, GitHub Actions run
`30412526981`.

| ID | Date | Evidence | Result | Scope |
|---|---|---|---|---|
| VLD-109 | 2026-07-29 | Focused prepared-job tests on Windows Python 3.12 | success | lifecycle, self-contained skill bundle, saved-job CLI/apply, plug-in contracts |
| VLD-110 | 2026-07-29 | Focused prepared-job tests on Windows Python 3.13 | success | same scope |
| VLD-111 | 2026-07-29 | Full pytest suite on Windows Python 3.12 and 3.13 | success on both matrix jobs | all tracked tests |
| VLD-112 | 2026-07-29 | CLI config smoke on Windows Python 3.12 and 3.13 | success | canonical `manual_app` external-file configuration |
| VLD-113 | 2026-07-29 | Integration suite on Windows Python 3.12 and 3.13 | success | cross-component Python workflow |
| VLD-114 | 2026-07-29 | `compileall` for `src` and `tests` | success on both matrix jobs | Python syntax/import surface |
| VLD-115 | 2026-07-29 | `git diff --check` | success on both matrix jobs | tracked diff hygiene |
| VLD-116 | 2026-07-29 | clean working-tree check | success on both matrix jobs | no runtime/private artifacts created by CI |

Both run-40 matrix jobs concluded `success`. Focused, full, config, integration,
compile, diff, and clean-tree steps all concluded `success`.

## WO-029 live gates still required

- Open exactly one real Lightroom folder and run **Prepare Current Folder**.
- Confirm the plug-in enumerates all eligible proprietary-RAW masters without
  manual photo selection.
- Confirm one cache handoff produces `manifest.json`, all available previews,
  `AI_TASK.md`, `AI_SKILLS.md`, schema, state, and job-scoped decisions folder.
- Give only that prepared job folder to an external vision AI and produce the
  exact decision set.
- Run **Apply Prepared Job** against the matching active folder.
- Confirm backup paths/hashes, old/delta/new exposure, terminal settlement for
  every eligible image, rollback safety, and Lightroom metadata refresh.

Until those live gates pass, WO-029 remains ACTIVE and its new Lightroom folder
commands are not `LIVE_VERIFIED`.

## Current limitations

- CI statically inspects Lua contracts; the GitHub runner does not prove the
  Lightroom-hosted Lua runtime.
- Real apply requires an existing XMP sidecar containing one unambiguous finite
  `crs:Exposure2012` value.
- DNG/JPEG/TIFF/PSD/video/virtual-copy inputs are intentionally excluded from
  the sidecar-only writable target set.
- The legacy Google API provider remains compatibility code, but it is not the
  canonical production route and its quota is not a WO-029 blocker.
