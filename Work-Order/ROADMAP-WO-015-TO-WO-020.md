# Lightroom Cache Workflow Roadmap — WO-015 to WO-020

## Goal
Replace Lightroom-rendered AI preview exports with read-only extraction from the Lightroom preview cache, while preserving deterministic mapping, safety, traceability, and guarded XMP exposure updates.

## Sequence

1. **WO-015 — Lightroom Preview Cache Identity Mapping**  
   Prove selected photo → cache identity → exact JPEG.

2. **WO-016 — Read-Only Lightroom Cache Preview Extractor**  
   Turn the mapping into a deterministic batch extractor.

3. **WO-017 — Cache Preview Job Manifest Handoff**  
   Produce a complete validated job contract without Lightroom preview export.

4. **WO-018 — Single-Pass AI Triage and Exposure Judgment**  
   Use one cached preview for relevance, quality, and exposure.

5. **WO-019 — Guarded XMP Exposure Apply Pilot**  
   Apply only approved `crs:Exposure2012` changes to copied test photos.

6. **WO-020 — End-to-End Cache-to-Lightroom Pilot**  
   Validate the full bounded workflow on 5–25 copied test photos.

## Authority Rule
Only one Work Order may be active at a time. Future Work Orders remain blocked until the preceding Work Order is closed with evidence.

## Permanent Safety Boundaries
- Never modify `.lrcat`.
- Never modify `.lrdata`.
- Never modify RAW files.
- XMP mutation is limited to `crs:Exposure2012`.
- Cache access is read-only and must fail closed.
- Generated cache snapshots, extracted JPEGs, and runtime artifacts are not committed.
- No automatic second preview at 2048 pixels.
- Final delivery export remains a separate user-controlled Lightroom operation.
