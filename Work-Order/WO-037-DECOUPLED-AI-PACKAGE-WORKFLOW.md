# WO-037 — Decoupled AI Package Workflow

STATUS: COMPLETE_CI_CERTIFIED

## Goal
Decouple Lightroom plug-in execution from external AI execution so every Lightroom action is short-lived and repairable independently.

The plug-in prepares a durable, self-contained AI package on disk and exits. External AI runs later and writes decisions to that package. A separate Lightroom command imports/validates/applies those results. Preparing the next pass is another explicit Lightroom command after rerender.

## Owner decision
Approved architecture:

```text
Lightroom Plugin — Prepare
→ capture active-folder identity + Catalog Exposure2012
→ hand selection to Python
→ Python snapshots Previews.lrdata read-only and extracts Lightroom-rendered JPEG previews
→ write durable pass package
→ PACKAGE_READY
→ plug-in exits

External AI Runner — later / separate process
→ read package + skills + previews
→ write decisions only
→ exit

Lightroom Plugin — Import / Apply Results
→ validate decisions and exact session/pass identity
→ build guarded Exposure2012-only Catalog apply plan
→ apply and verify in Lightroom
→ RERENDER_REQUIRED or SESSION_COMPLETE
→ plug-in exits

Lightroom Plugin — Prepare Next AI Package
→ only after previous pass is confirmed and Lightroom has rerendered
→ capture a new immutable preview pass
→ PACKAGE_READY
→ plug-in exits
```

There is no resident listener, polling loop, live AI connection, or `WAITING_FOR_AI` ownership in the canonical Lightroom plug-in commands.

## Why this change
WO-035/036 already persisted pass artifacts, but their user-facing `WAITING_FOR_AI` / multipurpose `Resume Pending Iterative Session` semantics mixed four responsibilities: checking decisions, applying results, waiting for rerender, and preparing the next pass.

WO-037 makes component ownership explicit:

- Lightroom plug-in = identity capture, explicit prepare, explicit apply, explicit next-pass capture.
- Python = preview-cache snapshot/extraction, package/session engine, decision validation and deterministic planning.
- External AI = visual judgment only.
- Session/pass directory = durable IPC contract.

## Scope

### A. Canonical Prepare command
- Add `Prepare AI Package` as the user-facing Pass 1 command.
- Keep Lightroom as identity source (`id_local`, UUID, active folder, Catalog Exposure2012).
- Keep Python as the `.lrdata` read-only cache extractor.
- Persist package artifacts under the existing session/pass directory.
- Report `PACKAGE_READY` after Python returns a complete package.
- Show package/task/decision paths and exit.
- Do not call AI, poll, or mutate Lightroom.

### B. Canonical Import / Apply Results command
- Add `Import / Apply AI Results` as a separate command.
- Reuse the existing exact decision readiness/freeze, deterministic planning, Catalog drift check, Exposure2012-only apply, and Lightroom-observed confirmation logic.
- Missing decisions are `AI_RESULTS_NOT_READY`, not a wait/listener state.
- A pass with existing apply evidence is not re-applied and does not auto-create another pass.
- End at `RERENDER_REQUIRED` when another pass is needed.

### C. Canonical Prepare Next command
- Add `Prepare Next AI Package` as a separate command.
- Require a valid latest session, confirmed prior pass, non-converged session, same active Lightroom source folder, and remaining pass budget.
- Re-read current Catalog Exposure2012 identities.
- Invoke the existing Python `--prepare-session-pass` path.
- Let Python enforce the existing render freshness barrier and read-only cache extraction.
- End at `PACKAGE_READY` and exit.

### D. Shared plug-in support
- Extract duplicated Lightroom identity, selection, path, decision-readiness and Catalog Exposure2012-only helper logic into one plug-in support module.
- The support module must not query SQLite, open Catalog database files, write `.lrdata`, invoke AI, or mutate any Develop property other than Exposure2012.

### E. Compatibility boundary
- Keep `IterativeSession.lua` and `ResumeIterativeSession.lua` as legacy compatibility surfaces for now, but remove them from the canonical plug-in menu.
- Keep WO-029 single-pass commands available and label them Legacy.
- Do not delete proven legacy code in this Work Order.

### F. Documentation and regression protection
- Update canonical workflow, architecture, decisions, status and user instructions to describe the file-based separation.
- Reconcile pre-existing plug-in contract tests that encode the superseded WO-035 menu/state contract.
- Add regression tests proving:
  - canonical menu exposes Prepare / Import-Apply / Prepare Next commands;
  - canonical command files contain no `WAITING_FOR_AI` state;
  - Prepare never validates/applies AI results;
  - Import / Apply never invokes `--prepare-session-pass`;
  - Prepare Next is the only canonical later-pass command that invokes `--prepare-session-pass`;
  - canonical commands contain no resident polling loop;
  - shared Catalog mutation is Exposure2012-only.

## Implemented files
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareAIPackage.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/ImportApplyAIResults.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareNextAIPackage.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/SessionPackageSupport.lua`
- updated `Info.lua` canonical menu routing
- `tests/test_decoupled_package_workflow.py`
- reconciled plug-in/SDK static contracts
- architecture/workflow/decision/status/README documentation

## Compatibility / reviewed unchanged
- `src/lr_ai_exposure/session_lifecycle.py` — existing start/prepare paths already create self-contained pass packages and do not call an AI provider during preparation.
- existing cache extractor / render barrier — reused without redesign.
- legacy `IterativeSession.lua` / `ResumeIterativeSession.lua` — retained but unregistered from the canonical menu.
- `DiagnoseCurrentFolder.lua` — diagnostic payload remains plug-in version 1.2.0; workflow routing does not change its diagnostic protocol/build contract.
- `AGENTS.md` — existing provider-neutral filesystem boundary and thin Lightroom ownership are compatible.

## Forbidden boundaries preserved
- no `.serena/project.yml` change
- no direct Lightroom `.lrcat`, `.lrcat-wal`, `.lrcat-shm` access
- no `.lrdata` write path
- no RAW/NEF/JPEG original mutation
- no provider credentials/API keys
- no Develop mutation other than `Exposure2012`
- no AI model/provider quality redesign
- no scene/reference redesign

## Acceptance results
1. Canonical Pass 1 command visibly ends at `PACKAGE_READY`: **PASS (static/automated contract)**.
2. Canonical iterative command files contain no `WAITING_FOR_AI` state: **PASS**.
3. Package is persisted before plug-in exit and external AI is filesystem-separated: **PASS (automated architecture contract; live use still pending)**.
4. Import / Apply refuses incomplete decisions without mutation: **PASS (static + existing decision readiness path)**.
5. Import / Apply never prepares a subsequent pass: **PASS**.
6. Separate Prepare Next AI Package command owns later-pass capture: **PASS**.
7. Later-pass preparation reuses the existing render barrier and read-only cache extraction: **PASS (code path + existing automated coverage)**.
8. Catalog apply remains drift-checked and Exposure2012-only: **PASS**.
9. Windows Python 3.12 and 3.13 certification: **PASS**.
10. No AI provider/model was called or tested: **PASS**.

## Executed validation evidence
GitHub Actions PR run #85, run id `33340357782`, head `d9aa38e4bd71f92196a71ee53aad16cf66aa481b`, completed `success` on 2026-08-30.

Both Windows Python 3.12 and 3.13 jobs passed:
- WO-029 focused prepared-job regressions
- full pytest suite
- CLI configuration smoke test
- integration suite
- source/test compile
- `git diff --check`
- clean working-tree/private-artifact check

The first PR run exposed only stale tests that still required the superseded Resume menu/version assumptions. Those tests were reconciled to the WO-037 canonical command contract, after which run #85 passed on both Windows matrix jobs.

## Remaining evidence boundary
WO-037 is CI-certified, not Lightroom-hosted `LIVE_VERIFIED`. The next manual gate is a bounded Lightroom Classic test of:

```text
Prepare AI Package
→ deterministic WO-036 no-AI decision seed
→ Import / Apply AI Results
→ Lightroom rerender
→ Prepare Next AI Package (only if the test requires another pass)
```

AI model/provider quality testing remains deferred.

## Merge authority
Owner explicitly authorized planning, Work Order creation, implementation, testing and completion. PR #5 may merge after the final branch CI for closeout-only documentation remains green.
