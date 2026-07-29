# Architecture — Lightroom AI Exposure Assist

## Canonical flow

```text
Lightroom selected folder photos
→ PREPARE_JOB
→ read-only Lightroom preview-cache snapshot
→ extracted JPEG previews + ordered manifest
→ durable prepared job folder
→ external file-capable vision AI
→ job-scoped decision JSON files
→ PROCESS_SAVED_JOB validation
→ explicit APPLY_SAVED_JOB authorization
→ guarded per-image XMP transactions
→ Lightroom metadata refresh
```

The canonical runtime is asynchronous and file-based. Lightroom prepares a job
once and stops. AI analysis happens outside Lightroom. Apply reopens the same
job and never extracts previews again.

## Operations

| Operation | Inputs | Output | XMP mutation |
|---|---|---|---|
| `--prepare-job` | Lightroom `selection.json`, `.lrdata` path | durable job, previews, manifest, AI task | never |
| `--process-job JOB_ID` | saved job decisions | validated analysis artifacts | never |
| `--apply-job JOB_ID --authorize-apply JOB_ID` | same saved job | apply evidence and result | guarded |
| legacy `--analyze-only` / `--apply` | one-shot compatibility | legacy artifacts | legacy rules |

## Component ownership

| Component | Responsibility |
|---|---|
| Lightroom plug-in | selection identity, prepare invocation, explicit apply invocation, metadata refresh |
| `handoff.py` / cache extractor | read-only DB snapshots, preview extraction, manifest creation |
| `job_lifecycle.py` | prepared-job state, AI task/schema, saved-job resolution, job-scoped provider settings |
| external AI | inspect previews and write decision JSON only |
| `manual_app` provider | exact-set decision import and preview identity verification |
| `apply.py` | identity gates, per-image policy, checkpoint/resume |
| `apply_transaction.py` / `xmp.py` | backup, atomic Exposure2012 write, verification, rollback |

## Key boundaries

- The preview cache may be read only through SQLite snapshots. It is never
  modified.
- Lightroom catalog files are never opened or modified.
- External AI never receives authority to write XMP.
- Decision files are scoped to `runtime/jobs/<job-id>/decisions/`; no global
  response directory is canonical.
- Apply uses the prepared job's exact source folder as the containment root.
- Only `crs:Exposure2012` may be changed.
- Every XMP mutation is sequential, backed up, verified, and checkpointed.

## Rationale

- Prepare-once avoids repeated cache extraction and duplicate jobs.
- External file handoff allows any vision AI app without API coupling.
- Job-scoped decisions prevent stale or unrelated responses from contaminating
  a new batch.
- Saved-job apply preserves identity from preview through XMP.
- No resident server or file watcher is required.
