# WO-031 - Diagnose Current Lightroom Folder

## Status

COMPLETED - AUTOMATED VALIDATION GREEN; OWNER LIGHTROOM TEST PENDING

## Owner decision

Implement the first approved seam from WO-030: `DIAGNOSE_CURRENT_FOLDER`.
This Work Order exists to replace one-error-at-a-time Lightroom debugging with
one bounded, read-only diagnostic run that gathers as much independent evidence
as possible before any Exposure Session/pass or real XMP implementation.

The existing local `.serena/project.yml` modification is owner-owned and
`NON_BLOCKING`. Do not edit, restore, stash, stage, commit, or otherwise use it
as a reason to stop this Work Order.

## Context reuse

WO-030 completed the architecture/governance read and documentation
reconciliation. In the same continuous Work thread, reuse that completed
read-first context and perform delta preflight only while HEAD, this Work Order,
and relevant files remain unchanged. Do not repeat a repository-wide audit or
full canonical reread merely because implementation is starting.

## Objective

Implement an end-to-end read-only `DIAGNOSE_CURRENT_FOLDER` path that reports
Lightroom folder eligibility and all independently testable cache/runtime/CLI/
bridge readiness in one run, including when eligible RAW count is zero.

The first real owner test after this Work Order should produce enough evidence
to diagnose the current Lightroom error without another fail-fast cycle.

## Required behavior

The diagnostic run must aggregate stages using `PASS`, `WARN`, `FAIL`, or
`SKIPPED_DEPENDENCY` and continue independent checks after non-fatal failures.
In particular, `eligible RAW = 0` must not terminate the diagnostic run.

Capture, when available:

- active Lightroom source/folder identity, source type/name/path;
- direct photo count from the active folder;
- observed `fileFormat` values, including nil/unknown values and observed type;
- eligible proprietary-RAW count;
- virtual-copy, video, unsupported-format, empty-path, offline/missing-path,
  and duplicate counts;
- bounded samples for each useful category with filename, Lightroom identity,
  path, and relevant metadata values;
- configured preview-cache path;
- `previews.db` and `root-pixels.db` existence/readability and required-table
  readiness where independently testable;
- runtime directory readiness;
- CLI/config readiness;
- bridge request/result protocol readiness where independently testable;
- XMP-sidecar existence and Exposure2012 parse-readiness only when safe and
  read-only;
- plugin/build/protocol identifiers needed to correlate owner evidence.

Produce both:

- machine-readable `preflight.json`;
- concise human-readable diagnostic summary suitable for the Lightroom owner.

## Safety / forbidden behavior

- Read-only diagnostics only.
- No XMP mutation, apply authorization, backup creation, or rollback path.
- No RAW/JPEG/catalog/preview-cache writes.
- No Exposure Session/pass implementation.
- No AI/provider redesign or paid API requirement.
- No change to existing transactional XMP apply behavior except wiring that is
  strictly necessary to keep diagnostics isolated from apply.
- Do not modify `.serena/project.yml`.
- Do not hide or convert independent failures into an early terminal error.

## Allowed implementation scope

Only files required for this seam may change, expected within:

- `lightroom-plugin/AIExposureAssist.lrplugin/`
- `src/lr_ai_exposure/`
- focused tests under `tests/`
- `docs/DIAGNOSTIC_PREFLIGHT.md` only if implementation evidence requires a
  contract clarification;
- `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`,
  `docs/PROJECT_STATUS.md` for truthful evidence/status at closeout;
- `Work-Order/CURRENT_WORK_ORDER.md` and this Work Order.

Do not broaden scope into session/pass, AI-provider cleanup, dependency cleanup,
or iterative apply.

## Implementation sequence

Maintain a concise TODO/checkpoint and work through it without repeating the
WO-030 audit:

1. delta preflight and relevant-file inspection;
2. implement diagnostic data collection and aggregation;
3. expose the Lightroom/plugin trigger and deterministic CLI/bridge path;
4. add focused automated tests for zero-eligible and multi-issue aggregation;
5. run regression guards proving existing Prepare/Apply behavior is unchanged;
6. reconcile evidence/status docs and close only when automated gates pass;
7. stop for one owner Lightroom run. Do not begin the next architecture seam.

## Required automated validation

At minimum, execute focused tests proving:

- zero eligible RAW still yields a complete diagnostic artifact;
- multiple independent failures appear in the same report;
- observed `fileFormat` values and bounded samples are preserved;
- cache checks can run or report `SKIPPED_DEPENDENCY` independently;
- diagnostics perform no XMP mutation;
- existing prepared-job/apply regression guards remain green.

Also run repository-required compile/diff/scope checks relevant to changed
source and tests.

## Completion gate

Close WO-031 only after automated evidence is green and the owner receives one
exact Lightroom test step. Real Lightroom evidence is not required to finish
implementation, but the next action after closeout must be the bounded owner
`DIAGNOSE_CURRENT_FOLDER` run rather than further implementation.

## Owner test expected after closeout

The owner should need to sync `main`, reload the Lightroom plug-in if required,
open the same problem folder, run exactly one diagnostic command/menu action,
and return the generated summary/artifact. No real Apply is authorized by this
Work Order.

## Implemented behavior

- Added plug-in version 1.1.0 build 3 menu command **AI Exposure Assist -
  Diagnose Current Folder** without changing Prepare or Apply behavior.
- Added bounded Lightroom evidence collection for active sources, direct
  photos, observed `fileFormat` values/types, exclusions, eligible identities,
  and category samples. Zero eligible RAW does not terminate collection.
- Added `--diagnose-current-folder` plus `--diagnostic-input` CLI handling and
  authoritative bridge-result validation.
- Added deterministic stage aggregation and `preflight.json` plus
  `diagnostic.txt` artifacts under the authorized runtime diagnostics path.
- Added read-only SQLite cache/table/identity/JPEG evidence and strict read-only
  XMP Exposure2012 readiness. Metadata sync remains explicitly `UNPROVEN` and
  fails closed without requiring an unsupported Save Metadata action.
- No session/pass, AI/provider, metadata refresh, XMP apply, backup, rollback,
  RAW, catalog, or preview-cache mutation path was added.

## Executed automated evidence

- Focused diagnostic, plug-in, CLI, Prepare/Apply, XMP, and transaction suite:
  `61 passed, 1 skipped`. The skip is the optional Lua parser because no Lua
  interpreter is installed on this host.
- Full suite: `218 passed, 2 skipped`. The second skip is the pre-existing
  legacy integration marker.
- Python source diagnostics for the new module: no findings.
- Compile, diff, and final scope evidence are recorded in
  `docs/VALIDATION_REGISTER.md` after execution.

## Documentation impact

- `UPDATED`: `docs/DIAGNOSTIC_PREFLIGHT.md`, `docs/CAPABILITY_MATRIX.md`,
  `docs/VALIDATION_REGISTER.md`, `docs/PROJECT_STATUS.md`, this Work Order, and
  `Work-Order/CURRENT_WORK_ORDER.md`.
- `REVIEWED_NO_CHANGE`: `README.md`, `docs/FOLDER_JOB_WORKFLOW.md`,
  `docs/ARCHITECTURE.md`, `docs/XMP_SAFETY.md`, `docs/AI_JUDGE_CONTRACT.md`, and
  `docs/DECISIONS.md`.
- `NOT_APPLICABLE`: visual AI skill documents because WO-031 invokes no AI.
