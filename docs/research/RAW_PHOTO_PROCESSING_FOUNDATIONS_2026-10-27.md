# Research intake — RAW photo processing foundations before engine design

- Created: 2026-10-27
- Status: **RESEARCH_IN_PROGRESS — research brief only, not a completed research report**
- Type: Non-authoritative research note; **NOT** an accepted product decision, implementation Work Order, or validation evidence
- Parent repository: `Lightroom-AI-Workflow-`
- Source of scope: Owner's request to learn how photo-processing applications work before designing any new processing engine

> This public repository must contain no private photos, raw files, Lightroom Catalog data, personal absolute paths, credentials, runtime package artifacts, or unpublished photo samples.

## Research method and order of work

**Do Phase 1 first.** Do not design the engine by assuming a Lightroom slider, Darktable module, Pillow/JPEG transform, or exposure EV value is interchangeable. Separate supported technical facts, version-dependent behavior, expert guidance, and hypotheses requiring experiments. Prefer official software manuals, developer documentation, color-science literature and reproducible research over unsourced claims.

### Phase 1 — Understand real photographic processing (priority)

1. **RAW fundamentals:** photon-to-sensor values, camera ADC/bit depth, black/white levels, clipping and saturation, CFA/demosaicing, white balance, camera profiles, camera metadata, linear-light operations and noise characteristics.
2. **Typical RAW development pipeline:** lens profile correction, exposure adjustment, highlight reconstruction, noise reduction, sharpening, tone/color manipulation, scene-referred vs display-referred processing, input/working/output color spaces, ICC/DCP profiles, gamut mapping, export and compression. For each application, verify its **actual module ordering** instead of asserting one universal ordering.
3. **RAW vs JPEG adjustment:** what is baked into camera-created JPEGs, white balance/profile/curve/contrast differences, limited highlight recovery and quantization/gamut constraints, gamma/nonlinearity; why a nominal exposure adjustment on JPEG pixels is not guaranteed to match Lightroom's `Exposure2012` result from a NEF. Differentiate image appearance from slider units.
4. **Program-by-program review:**
   - Adobe Lightroom Classic / Adobe Camera Raw: process version, preset XMP, parametric rendering, Develop Catalog state and preview lifecycle;
   - Darktable: scene-referred editing, color pipeline, module order, `.dtstyle`, CLI batch export;
   - RawTherapee: RAW pipeline, processing profiles and CLI;
   - Capture One: RAW rendering, profiles and adjustment architecture;
   - Other tools only where evidence provides genuine additional insight.
5. **Photography-specific methods:** skin/orange/yellow/green HSL work, tonal highlight roll-off, appropriate face exposure vs scene atmosphere, noise vs texture/detail, adaptive lens corrections, white-balance constraints, image-to-image and sequence consistency.
6. **Evidence:** compare official documentation and observed behavior; record exact product version, official URL, publication/update date if available, uncertainty and unresolved differences.

### Phase 2 — Derive an engine proposal from the verified principles

Only after Phase 1, evaluate designs for **Nikon NEF → technically correct, aesthetically consistent JPEG**. The original Lightroom workflow remains an important reference, **not** proof that another renderer can reproduce it by copying XMP slider values.

The existing Lightroom assistant is a separate, bounded `Exposure2012`-only product. Do not silently expand it. Study possible future approaches as **research**, including:

- Baseline RAW rendering using an approved style/preset, with white balance **left at the camera/current value for now**;
- Estimating useful image-specific exposure without enforcing uniform image brightness;
- Grouping adjacent wedding/event shots by time, camera/exposure metadata, visual semantics and lighting, accounting for CLIP/embedding misgrouping;
- Subjects, faces/skin, backlight, bright dresses/shirts, night/atmosphere, intentional low-key scenes and clipped highlights;
- Comparing photographic AI judgment, deterministic metering, scene-aware grouping, human review, exposure calibration in renderer output and renderer-in-the-loop optimization;
- Lightroom-rendered Standard Previews/contact sheets and render-freshness barriers vs a separate Darktable CLI renderer;
- Reproducing a *look* (not directly translating XMP numeric sliders) with native Darktable `.dtstyle`, targeted hue/saturation/luminance controls, tone/filmic controls and adaptive ISO-dependent noise processing;
- Making batch output resumable, with exactly-once identities, source-file preservation, explicit PASS/REVIEW/UNRESOLVED accounting and measurable latency;
- Making a small, documented test set (e.g. 4–20 selected NEF images) and comparing visual consistency with verified Lightroom-produced reference JPEGs of **the same** NEF inputs.

## Research report expected outputs

1. A **fundamentals tutorial** grounded in reputable technical references.
2. A **program comparison table**, explicitly distinguishing feature availability from implementation/processing order.
3. A **RAW vs JPEG explanation** with concrete examples and mathematical caveats.
4. A **verified findings vs assumptions** register, including source URLs.
5. A **candidate engine design comparison** only after the fundamentals, including quality, speed, complexity and failure modes.
6. A **minimal reproducible validation plan**: file identity, visual/photometric quality, scene consistency, skin/hues/highlights, processing time and safe error recovery.
7. A list of **decisions reserved for the Owner**, without turning untested research ideas into existing project requirements.

## Current project boundary and non-goals

- The repository's active authority remains `Work-Order/WO-041-SCENE-COMPLETE-EXPOSURE-ITERATION.md`; it is awaiting Owner-operated Lightroom validation as recorded in current documentation.
- No change here to `AGENTS.md`, `docs/DECISIONS.md`, product roadmap, capability/evidence status, existing session contracts or running code.
- Do not modify original NEF/JPEG files, sidecars, Lightroom Catalog or preview caches.
- Do not enable automated white-balance changes or automatically apply non-Exposure Develop settings.
- Do not claim the separate Darktable style experiments are calibrated to the Lightroom target until a like-for-like test confirms them.
- Do not call this note a final Deep Research result: the requested source-backed report is pending and must be brought into this repository explicitly after it exists.

## Handoff / documentation workflow

Once the complete source-backed Deep Research report is available:

1. Save an **unaltered primary report** in this research directory (Markdown or a verified linked artifact), preserving references and retrieval date.
2. Build a clearly marked **synthesis** with `FACT / INFERENCE / EXPERIMENT_REQUIRED` labels.
3. Keep engine proposals under research, separate from the canonical Exposure-only product.
4. Review with Owner before creating an implementation Work Order or merging any design decision to `main`.

Research work is documentation-only at this stage; **no code, app behavior, RAW file or catalog was changed**.
