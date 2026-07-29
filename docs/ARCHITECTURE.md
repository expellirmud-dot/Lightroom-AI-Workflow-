# Architecture — Lightroom AI Exposure Assist

## Canonical flow

```text
current Lightroom folder
→ enumerate every eligible proprietary-RAW master
→ PREPARE_JOB
→ read-only Lightroom preview-cache snapshot
→ extracted JPEG previews + ordered manifest
→ durable self-contained job folder
→ external file-capable vision AI reads AI_TASK.md + AI_SKILLS.md
→ job-scoped decision JSON files
→ PROCESS_SAVED_JOB validation
→ explicit APPLY_SAVED_JOB authorization
→ guarded per-image XMP transactions
→ Lightroom metadata refresh
```

The canonical runtime is asynchronous and file-based. Lightroom prepares one
complete active-folder job and stops. AI analysis happens outside Lightroom.
Apply reopens the same job and never extracts previews or invokes AI again.

## Operations

| Operation | Inputs | Output | XMP mutation |
|---|---|---|---|
| `--prepare-job` | folder-derived `selection.json`, `.lrdata` path | durable job, previews, manifest, AI task, bundled skills, schema | never |
| `--process-job JOB_ID` | saved job decisions | validated analysis artifacts | never |
| `--apply-job JOB_ID --authorize-apply JOB_ID` | same saved job | apply evidence and result | guarded |
| legacy `--analyze-only` / `--apply` | one-shot compatibility | legacy artifacts | legacy rules |

## Component ownership

| Component | Responsibility |
|---|---|
| Lightroom plug-in | active-folder enumeration, identity capture, prepare invocation, source-folder apply confirmation, metadata refresh |
| `handoff.py` / cache extractor | read-only DB snapshots, preview extraction, manifest creation |
| `job_lifecycle.py` | prepared-job state, bundled skills, AI task/schema, saved-job resolution, job-scoped provider settings |
| external AI | inspect the self-contained job and write decision JSON only |
| `manual_app` provider | exact-set decision import and preview identity verification |
| `apply.py` | identity gates, per-image policy, checkpoint/resume |
| `apply_transaction.py` / `xmp.py` | backup, atomic Exposure2012 write, verification, rollback |

## Prepared-job boundary

A prepared job is a durable local handoff package. It contains:

- the exact selection/manifest identity chain;
- extracted previews and preview hashes;
- `AI_TASK.md`;
- `AI_SKILLS.md`, generated deterministically from all Markdown/JSON content in
  the four canonical visual skill directories;
- strict decision schema;
- job-scoped decision, evidence, backup, and log locations.

Missing task, skill bundle, or schema invalidates saved-job processing. This
makes the handoff usable by an AI application that has access only to the job
folder and not to the repository.

## Key boundaries

- The preview cache may be read only through SQLite snapshots. It is never
  modified.
- Lightroom catalog files are never opened or modified.
- Only proprietary-RAW master photos are prepared; formats whose metadata is
  normally embedded in the source image are excluded from this sidecar-only
  workflow.
- External AI never receives authority to write XMP.
- Decision files are scoped to `runtime/jobs/<job-id>/decisions/`; no global
  response directory is canonical.
- Apply requires the same Lightroom source folder to be active and uses the
  prepared job's exact source folder as the containment root.
- Only `crs:Exposure2012` may be changed.
- Every XMP mutation is sequential, backed up, verified, and checkpointed.

## Rationale

- Active-folder enumeration avoids manual Ctrl+A selection and accidental
  partial jobs.
- Prepare-once avoids repeated cache extraction and duplicate jobs.
- A bundled skill contract prevents external AI tools from silently omitting
  the project's visual judgment rules.
- External file handoff allows any vision AI app without API coupling.
- Job-scoped decisions prevent stale or unrelated responses from contaminating
  a new batch.
- Saved-job apply preserves identity from preview through XMP.
- No resident server or file watcher is required.
