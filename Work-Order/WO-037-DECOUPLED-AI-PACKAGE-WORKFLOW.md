# WO-037 — Decoupled AI Package Workflow

STATUS: ACTIVE

## Goal
Decouple Lightroom plug-in execution from external AI execution so every Lightroom action is short-lived and repairable independently.

The plug-in must prepare a durable, self-contained AI package on disk and exit. External AI runs later and writes decisions to that package. A separate Lightroom command imports/validates/applies those results. Preparing the next pass is another explicit Lightroom command after rerender.

## Owner decision
Approved architecture:

```text
Lightroom Plugin — Prepare
→ capture active-folder identity + Catalog Exposure2012
→ hand manifest to Python
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
→ RERENDER_REQUIRED
→ plug-in exits

Lightroom Plugin — Prepare Next AI Package
→ only after previous pass is confirmed and Lightroom has rerendered
→ capture a new immutable preview pass
→ PACKAGE_READY
→ plug-in exits
```

There is no resident listener, polling loop, live AI connection, or `WAITING_FOR_AI` ownership in the Lightroom plug-in.

## Why this change
The current WO-035/036 runtime already stops after preparation, but its state names and multipurpose `Resume Pending Iterative Session` command imply a coupled listener/resume workflow. The same Resume command also validates decisions, applies changes, waits for rerender, and prepares the next pass. That obscures component ownership and increases the blast radius of a plug-in failure.

WO-037 makes the separation explicit:

- Lightroom plug-in = identity capture, explicit prepare, explicit apply, explicit next-pass capture.
- Python = preview-cache snapshot/extraction, package/session engine, decision validation and deterministic planning.
- External AI = visual judgment only.
- Session/pass directory = durable IPC contract.

## Scope

### A. Prepare command
- Rename user-facing iterative prepare command to `Prepare AI Package` terminology.
- Keep Lightroom as identity source (`id_local`, UUID, active folder, Catalog Exposure2012).
- Keep Python as the `.lrdata` read-only cache extractor.
- Persist package artifacts under the session/pass directory.
- Persist package lifecycle state as `PACKAGE_READY`.
- Show the package path and finish. Do not say the plug-in is waiting/listening.

### B. Import / Apply Results command
- Reuse the existing safe decision-readiness, freeze, plan, Catalog drift check, Exposure2012-only apply, and confirmation logic.
- Rename the user-facing command to `Import / Apply AI Results`.
- Missing decisions are `AI_RESULTS_NOT_READY`, not a wait state.
- If the current pass is already confirmed, do not auto-create the next pass.
- End at `RERENDER_REQUIRED` when another pass is needed.

### C. Explicit next-pass command
- Add `Prepare Next AI Package` as a separate Lightroom menu command.
- Require a valid latest session, a confirmed prior pass, a non-converged session, and the same active Lightroom source folder.
- Re-read current Catalog Exposure2012 identities for the next pass.
- Invoke the existing Python `--prepare-session-pass` path.
- Let Python enforce render freshness and read-only cache extraction.
- End at `PACKAGE_READY` and exit.

### D. Python package state
- `prepare_session_pass()` records `lifecycle_state: "PACKAGE_READY"` in `pass-state.json` and its returned bridge payload.
- No Python prepare path invokes an AI provider.
- Existing external-file decision validation remains reusable by the import/apply command.

### E. Documentation and regression protection
- Update canonical workflow/architecture/decisions/user instructions to describe file-based decoupling.
- Add regression tests proving:
  - prepared pass advertises `PACKAGE_READY`;
  - iterative Lightroom entrypoints contain no `WAITING_FOR_AI` user state;
  - Import / Apply Results does not prepare a next pass;
  - Prepare Next AI Package is the only iterative plug-in command that invokes `--prepare-session-pass` after pass 1;
  - no plug-in command invokes an AI provider or performs polling.

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
- `lightroom-plugin/AIExposureAssist.lrplugin/IterativeSession.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/ResumeIterativeSession.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareNextIterativePass.lua`
- `src/lr_ai_exposure/session_lifecycle.py`
- `tests/test_session_lifecycle.py`
- `tests/test_decoupled_package_workflow.py`

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
1. Pass 1 preparation finishes at durable `PACKAGE_READY` and the plug-in exits.
2. No iterative plug-in UI/state claims it is waiting or listening for AI.
3. External AI can be run later with Lightroom closed because the package is self-contained.
4. Import / Apply Results refuses incomplete decisions without mutation.
5. Import / Apply Results never prepares a subsequent pass automatically.
6. A separate Prepare Next AI Package command owns later-pass capture.
7. Later-pass preparation still enforces the existing render barrier and read-only `.lrdata` snapshot/extraction.
8. Catalog apply remains drift-checked and modifies only `Exposure2012`.
9. Automated CI passes on Windows Python 3.12 and 3.13.
10. No AI provider/model is called or tested by this Work Order.

## Required validation
- focused pytest for session lifecycle and decoupled workflow regression
- full `pytest tests`
- integration test suite used by repository CI
- `python -m compileall -q src`
- Lua/static workflow contract checks in tests
- `git diff --check`
- repository CI on Windows Python 3.12 and 3.13
- diff review proving no `.lrdata` writes, no Catalog-file access, and no non-Exposure2012 Develop mutation

## Documentation impact
- `AGENTS.md`: canonical target lifecycle and runtime ownership terminology.
- `docs/FOLDER_JOB_WORKFLOW.md`: explicit Prepare Package → external AI → Import/Apply → Prepare Next Package sequence.
- `docs/ARCHITECTURE.md`: disk package as IPC boundary; no resident AI/listener.
- `docs/DECISIONS.md`: durable decision accepting the decoupled package architecture.
- `README.md`: user-facing command sequence.
- `docs/PROJECT_STATUS.md`, `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`: reconcile after executed evidence.

## Commit / PR authority
Owner explicitly requested: plan the change, add a Work Order, implement it, test it, and report when ready. This Work Order authorizes bounded commits, branch push, PR creation, and merge only after required CI passes and the diff remains within this scope.

## Stop conditions
- Lightroom SDK behavior required by the change cannot be established from current implementation/tests and would require speculative mutation.
- Existing render-barrier or Catalog Exposure2012 safety contract would need weakening.
- Any path would require writing `.lrdata` or direct Catalog database access.
- CI exposes an unrelated repository failure that cannot be safely separated from this Work Order.
