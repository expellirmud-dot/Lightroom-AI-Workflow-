# WO-037 — Decoupled AI Package Workflow

STATUS: ACTIVE

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
- Update canonical workflow, architecture, decisions, status, capability and user instructions to describe the file-based separation.
- Reconcile pre-existing plug-in contract tests that encode the superseded WO-035 menu/state contract.
- Add regression tests proving:
  - canonical menu exposes Prepare / Import-Apply / Prepare Next commands;
  - canonical command files contain no `WAITING_FOR_AI` state;
  - Prepare never validates/applies AI results;
  - Import / Apply never invokes `--prepare-session-pass`;
  - Prepare Next is the only canonical later-pass command that invokes `--prepare-session-pass`;
  - canonical commands contain no resident polling loop;
  - shared Catalog mutation is Exposure2012-only.

## Allowed files
- `Work-Order/WO-037-DECOUPLED-AI-PACKAGE-WORKFLOW.md`
- `Work-Order/WO-036-LIGHTROOM-LIVE-TEST-HARNESS.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `AGENTS.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `README.md`
- `lightroom-plugin/AIExposureAssist.lrplugin/Info.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareAIPackage.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/ImportApplyAIResults.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareNextAIPackage.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/SessionPackageSupport.lua`
- `tests/test_decoupled_package_workflow.py`
- `tests/test_lightroom_plugin_contract.py`
- `tests/test_lightroom_sdk_live_boundary.py`

## Reviewed but intentionally unchanged unless validation requires otherwise
- `AGENTS.md` — existing provider-neutral filesystem boundary and thin Lightroom ownership are compatible.
- `src/lr_ai_exposure/session_lifecycle.py` — existing start/prepare paths already create self-contained pass packages and do not call an AI provider during preparation.
- existing cache extractor / render barrier — reused without redesign.
- legacy `IterativeSession.lua` / `ResumeIterativeSession.lua` — retained but unregistered from the canonical menu.
- `DiagnoseCurrentFolder.lua` — diagnostic payload remains plug-in version 1.2.0; WO-037 keeps the metadata version at 1.2.0 because this Work Order changes workflow routing rather than the diagnostic protocol/build contract.

## Forbidden files / boundaries
- `.serena/project.yml`
- Lightroom `.lrcat`, `.lrcat-wal`, `.lrcat-shm`
- any `.lrdata` write path
- RAW/NEF/JPEG originals
- runtime session/package artifacts
- provider credentials/API keys
- any Develop property other than `Exposure2012`
- AI model/provider quality redesign (deferred)
- scene/reference redesign (separate future work)

## Acceptance criteria
1. Pass 1 preparation finishes at visible `PACKAGE_READY` and the canonical plug-in command exits.
2. No canonical iterative plug-in UI/state claims it is waiting or listening for AI.
3. The prepared package is self-contained enough for external AI to run later with Lightroom closed.
4. Import / Apply Results refuses incomplete decisions without mutation.
5. Import / Apply Results never prepares a subsequent pass automatically.
6. A separate Prepare Next AI Package command owns later-pass capture.
7. Later-pass preparation still uses the existing render barrier and read-only `.lrdata` snapshot/extraction path.
8. Catalog apply remains drift-checked and modifies only `Exposure2012`.
9. Automated CI passes on Windows Python 3.12 and 3.13.
10. No AI provider/model is called or tested by this Work Order.

## Required validation
- focused `pytest tests/test_decoupled_package_workflow.py`
- full `pytest tests`
- integration test suite used by repository CI
- `python -m compileall -q src`
- `git diff --check`
- repository CI on Windows Python 3.12 and 3.13
- diff review proving no `.lrdata` writes, no Catalog-file access, no provider invocation in canonical prepare commands, and no non-Exposure2012 Develop mutation

## Documentation impact
- `docs/FOLDER_JOB_WORKFLOW.md`: explicit Prepare Package → external AI → Import/Apply → Prepare Next Package sequence.
- `docs/ARCHITECTURE.md`: session folder as IPC boundary; no resident AI/listener.
- `docs/DECISIONS.md`: durable decision accepting decoupled command ownership.
- `README.md`: user-facing command sequence and current evidence boundary.
- `docs/PROJECT_STATUS.md`, `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`: reconcile after executed evidence.
- `AGENTS.md`: REVIEWED_NO_CHANGE unless implementation uncovers a conflict.

## Commit / PR authority
Owner explicitly requested: plan the change, add a Work Order, implement it, test it, and report when ready. This Work Order authorizes bounded commits, branch push, PR creation, and merge only after required CI passes and the diff remains within this scope.

## Stop conditions
- Lightroom SDK behavior required by the change cannot be established from current implementation/tests and would require speculative mutation.
- Existing render-barrier or Catalog Exposure2012 safety contract would need weakening.
- Any path would require writing `.lrdata` or direct Catalog database access.
- CI exposes an unrelated repository failure that cannot be safely separated from this Work Order.
