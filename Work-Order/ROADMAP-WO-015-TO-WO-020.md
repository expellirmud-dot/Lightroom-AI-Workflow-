# HISTORICAL ROADMAP — WO-015 to WO-020

STATUS: COMPLETED_SUPERSEDED
CURRENT_ROADMAP: `docs/ROADMAP.md`

This file preserves the historical cache-workflow sequence only. It is **not**
the current Project Roadmap and must not be used to activate new Work Orders.
For current phase, next gate and Work Order activation rules, read
`docs/ROADMAP.md`, `docs/PROJECT_STATUS.md` and
`Work-Order/CURRENT_WORK_ORDER.md`.

## Historical goal

Replace Lightroom-rendered AI preview exports with read-only extraction from the
Lightroom preview cache while preserving deterministic mapping, safety,
traceability and guarded exposure updates.

## Historical sequence

1. **WO-015 — Lightroom Preview Cache Identity Mapping**
2. **WO-016 — Read-Only Lightroom Cache Preview Extractor**
3. **WO-017 — Cache Preview Job Manifest Handoff**
4. **WO-018 — Single-Pass AI Triage and Exposure Judgment**
5. **WO-019 — Guarded XMP Exposure Apply Pilot**
6. **WO-020 — End-to-End Cache-to-Lightroom Pilot**

These Work Orders are historical evidence. Later accepted decisions replaced the
XMP-centered target with the canonical Catalog-authoritative Exposure Session
and explicit package workflow.

## Preserved historical safety boundaries

- never modify `.lrcat` directly;
- never write `.lrdata`;
- never modify RAW files;
- generated cache snapshots/previews/runtime artifacts are not committed;
- final delivery export remains user-controlled.

Historical XMP-specific requirements apply only when an explicitly active legacy
sidecar path uses them. They do not override the current canonical Catalog route.
