# RAW/JPEG Photo Processing — Verified Foundations (Research Phase 1)

**Research date:** 2026-10-27  
**Status:** PHASE 1 — documented technical findings; **not** a completed production-engine design or a benchmark  
**Source priority:** official manuals, official standards and primary product documentation  
**Repository purpose:** research alongside the Lightroom AI Exposure project, not a change to its authorized runtime

## Executive findings

1. RAW files are not finished photographs. Each RAW developer converts sensor samples into a rendered image through black-level handling, demosaicing, color interpretation, tonal processing and an output transform. An in-camera JPEG has already undergone its own processing and may contain clipped or compressed output values. **Rendering and photography are separate from mere file conversion.** [S1, S2, S3]
2. **Renderer identity matters:** Lightroom uses Camera Raw technology and a Process Version; Capture One uses its own camera ICC profile plus base tone curve; Darktable exposes a configurable ordered pixelpipe; RawTherapee has its own input profiles, processing profiles, tone mapping and RAW processing. Identical slider numbers do not promise identical pictures. [S6, S7, S9, S10, S11]
3. A Lightroom **Standard Preview** is already produced by Adobe's Camera Raw engine. An embedded/minimal JPEG preview is made by the camera and might represent a different look. This distinction is central to studying a preset-applied contact sheet. [S5]
4. **Exposure EV is not directly CIELAB L\*** or gamma-encoded JPEG brightness. Physical linear-light scaling, nonlinear tone mapping and per-program processing change the final lightness relationship. A pixel-domain JPEG exposure simulation cannot serve as proof of an equivalent Lightroom/Darktable RAW adjustment. [S12, S13, S19]
5. Darktable has an **area exposure mapping** tool explicitly intended for matching exposure between photos of a series, but its manual warns that a moving face under changing illumination is an unreliable sampling patch. This is an unusually direct counterpart to the earlier subject-aware exposure experiments, **not** proof that the entire photographic task is solved. [S13]
6. Noise processing and optical corrections are frequently **camera/ISO/lens dependent**. Darktable's profiled denoise derives a camera/ISO noise profile; its optical correction may depend on lens, focal length, aperture and sometimes focus distance. Those operations must be tested on actual sample RAWs, not inferred from a global preset number. [S17, S18]

## 1. What a RAW developer actually does

A practical conceptual model is:

```text
RAW sensor samples + metadata
  -> raw black/white levels and sensor-specific calibration
  -> mosaiced color data correction / highlight repair (where supported)
  -> demosaic, yielding image pixels
  -> white balance / chromatic adaptation and input camera profile
  -> scene-linear exposure and other tonal/color operations
  -> optical and geometric corrections, noise/sharpness where applicable
  -> tone mapping / display transform and output color profile
  -> file encoding (for example, JPEG or TIFF)
```

**Important:** this is a conceptual teaching diagram, **not a universal exact module order**. Some steps operate before demosaic, some after; darktable explicitly specifies its pixelpipe ordering and warns against arbitrary reordering. Its newest documented workflow has different order presets for RAW and JPEG. Verify installed version, enabled modules, image-specific history and execution order before attempting exact replication. [S11, S12]

The sensor's RAW values must be interpreted with a camera-specific profile before they become useful colorimetric RGB values. RawTherapee's documentation describes camera-to-working-space conversion with matrices or DCP/ICC profiles; a profile can itself introduce tone and creative characteristics. This is one reason the camera's original JPEG, a Lightroom render and a Capture One render can look different despite sharing a single RAW source. [S1, S2]

### 1.1 Black points, demosaic and clipping

With mosaiced RAW capture, neighboring sensor samples commonly observe different color filters. Demosaicing estimates full-color RGB pixels from this sampled array. Black level offsets and sensor saturation matter. True clipped sensor-channel information cannot simply be restored by turning exposure down. Reconstruction may infer missing regions from other un-clipped channels or neighbors, but results are estimates with failure modes. RawTherapee explicitly distinguishes **highlight reconstruction of RAW clipping** from **highlight compression of values rendered too bright by later exposure processing**. [S3]

### 1.2 Camera profile and tonal baseline

A camera input profile is more than a brand-name look. It transforms camera color measurements into a meaningful working color representation. DCP/ICC-based profiles may be tailored to different illuminants; some include tone curves or appearance information. The resulting baseline can profoundly affect perceived brightness, skin hues, saturated greens/blues and contrast. [S2]

In Capture One, the **Base Characteristics** panel selects a default camera ICC profile plus film/tone curve after demosaicing. Its own support documentation identifies the base curve as an important part of the rendering pipeline. A linear/less-contrasty curve and a film-style curve produce different starting pictures before ordinary Exposure adjustments. [S9, S10]

Lightroom Classic uses **Adobe Camera Raw process versions**. This affects which Develop processing behavior/settings apply; it cannot be assumed to implement the same transform as another application's exposure module or HSL/color controls. Its raw and creative profiles are different in applicability, and Adobe's **As Shot** white balance uses camera-derived WB data when available, whereas Lightroom's **Auto** option calculates WB from image data. Camera Auto WB and Lightroom Auto WB must therefore not be conflated. [S6, S7]

### 1.3 Scene-referred vs display-referred

In scene-referred editing, working pixel values preserve relationships to the underlying light and can exceed the display's output gamut/range until they are mapped toward display-referred values. Darktable promotes scene-referred processing and uses a nonlinear display transform near the end of its scene-referred pixelpipe. This processing order matters for clipping, saturation, contrast and correction behavior. [S11, S12]

A **linear-light exposure multiplication** is conceptually:

```text
linear_output = linear_input × 2^(EV_delta)
```

This is not an assertion that a Lightroom slider performs precisely that operation at every intermediate stage; modern RAW developers may use additional tonal, profile and highlight logic. The sRGB channel values stored in a normal display JPEG are **nonlinear-encoded**. W3C publishes the transfer function for converting sRGB values to linear-light values. Multiplying encoded JPEG values directly is not equivalent to linear-light scaling; even correctly decoding and scaling an already-rendered JPEG does not reconstruct the original RAW rendering pipeline. [S12, S19]

### 1.4 Noise, detail and optics

Sensor noise varies by camera, ISO, image signal and channel. Darktable's **denoise (profiled)** uses camera model/ISO metadata and corresponding camera sensor noise statistics; manual documentation explains ISO interpolation and different luma/chroma denoising methods. The intended strength should be assessed against retention of hair, eye detail, skin texture and textile edges in real 1:1 exports. [S18]

Distortion, transverse chromatic aberration and vignetting correction may use embedded RAW metadata or Lensfun. Darktable records that focal length, aperture and possibly focus distance influence corrections; some combinations have missing or partial calibration profiles. A universal static correction for images captured at different focal lengths cannot be assumed to represent the actual optics. [S17]

## 2. Why RAW and JPEG respond differently to edits

| Question | RAW development | JPEG correction |
|---|---|---|
| Where does image interpretation happen? | Developer interprets sensor data, camera color, WB, tone and output transform | Camera or upstream developer has already made many interpretation choices |
| Exposure correction | Can happen in a scene-linear/raw-derived processing chain | Operates on previously processed, tone-mapped data, sometimes after transforming encoded values to linear |
| White balance | Camera as-shot metadata can guide RAW chromatic adaptation; settings can be changed with more freedom | Existing WB/color and camera profile are baked into encoded channels; rebalancing is more constrained |
| Highlights | Raw-channel data may remain even where rendered JPEG is white; reconstruction is still imperfect | Output clipping/compression may have permanently discarded distinctions |
| Bit depth and compression | Source varies by format/camera; often higher effective precision and richer range | Ordinary JPEG is commonly 8-bit per RGB channel and uses lossy compression |
| Cross-app matching | Requires profile, processing pipeline and output reference alignment | May be easier to compare files pixel-for-pixel, but source tonal information is already lost |

The JPEG limitation is **not** that every JPEG edit is invalid: display-domain JPEG adjustments are useful for preview, ranking and approximate appearance tests. The limitation is **equivalence**. A `+0.5 EV` applied to a JPEG approximation cannot be treated as ground truth for `+0.5` on the Lightroom RAW Exposure slider, especially in highlights, saturated colors or shadow noise. [S3, S12, S19]

The color metric **CIELAB L\*** is a perceptual lightness coordinate, not an exposure stop. Comparing `L\*` across portraits can be useful evidence but must not compel all faces, different skin reflectances, lighting angles or scenes to converge to one brightness target. Reference patches under genuinely comparable illumination are safer than arbitrary skin pixels. Darktable's area exposure mapping documentation warns explicitly about faces changing from light to shade as they turn. [S13]

## 3. Application-by-application findings

| Software | Developer baseline and color | Repeatable workflows | Implication for study |
|---|---|---|---|
| **Lightroom Classic / Camera Raw** | Camera Raw rendering, Process Versions, Adobe/Camera Matching profiles, camera as-shot WB | Preset-based Develop state, Catalog; optional proprietary-RAW XMP sidecars; Standard/1:1 previews rendered with Camera Raw | A Standard Preview following preset application is a meaningful *visual baseline*. Record exact process/profile/WB/Develop state and not just the preset filename. |
| **Darktable** | Ordered pixelpipe; linear scene-referred processing and later display transform; multiple color modules | Native `.dtstyle` XML, `darktable-cli`, app-managed sidecar/history | More open control of processing; copying Adobe XMP slider fields is not a style conversion. Actual render comparison is necessary. |
| **RawTherapee** | Camera input profiles, auto-matched camera-JPEG curve, tone/exposure tools | `.pp3` processing profiles, `rawtherapee-cli`, optional per-image sidecars | Worth studying as a second open-source RAW renderer with a documented method to approach the camera-JPEG look; verify against Lightroom look separately. |
| **Capture One** | Camera ICC + film/base curve; versioned processing engine | Catalog/Session editing and profiles, exports | Demonstrates how early tone and color defaults establish a camera-specific look. Treat matching look across engines as empirical, not numerical, equivalence. |

Sources: Adobe [S5–S8]; darktable [S11–S16]; RawTherapee [S1–S4]; Capture One [S9–S10].

### 3.1 Lightroom preview and XMP are not the same thing

Adobe distinguishes:
- **Minimal/Embedded previews**: camera-generated JPEGs, potentially different from applied Develop settings.
- **Standard/1:1 previews**: processed using Camera Raw; Standard is used for Library Grid/Filmstrip/other views. A contact sheet extracted from a verified fresh Standard Preview is evidence of the processed appearance at preview resolution, not of raw sensor values. [S5]
- **Catalog settings vs XMP**: Lightroom records edits in its Catalog, optionally also writing XMP. For proprietary RAW files, sidecars avoid modifying the RAW. Current Adobe documentation notes additional ACR sidecar behavior beginning with Lightroom Classic 15.0, so software version must be recorded rather than assuming one timeless sidecar rule. [S8]

**Warning for experiments:** an Adobe `.xmp` preset, an Adobe RAW `.xmp` sidecar and a darktable history `.xmp` file are distinct artifacts/contracts. The extension alone does not prove interoperation. A Darktable native style is an XML `.dtstyle` file, maintained in Darktable's environment. [S8, S15, S16]

### 3.2 Darktable has an existing exposure-region technique worth investigating

Darktable's exposure module documents **area exposure mapping**:
1. Select a consistent sample on a reference image and measure or designate its target brightness.
2. Select the corresponding patch on another image; the tool derives exposure compensation to approach that target.
3. Repeat when the sampled subject and illumination remain comparable.

This is **not** automated semantic selection of the correct subject, and the manual warns against using moving or variably illuminated portions of a person's face as a universal reference. That warning helps explain why older face-skin lightness matching could be technically repeatable but photographically wrong. [S13]

Darktable also offers area color mapping in the color-calibration module; its manual cautions that equal measured sample chromaticity need not produce equal *perceived* image color because surrounding lightness and color contrast change perception. This is relevant when evaluating skin color after applying a preset. [S14]

### 3.3 Command-line batch capabilities are documented, not yet benchmarked here

- **Darktable CLI** supports image export, named `--style`, sidecar input, output format/ICC options and configuration directory handling. Its documentation warns that disabling custom presets/styles to run multiple instances prevents use of `--style`; concurrency therefore needs a controlled benchmark and configuration strategy. [S15]
- **RawTherapee CLI** can process input images/folders via `-c`, layered `-p` processing profiles and per-image `-s` PP3 sidecars; profile precedence is documented. [S4]
- **Capture One** and **Lightroom** are commercial RAW editors; this report does not assume a fully equivalent supported headless CLI merely because they have export or scripting functions.

No comparative speed claim is justified until the same original RAWs, output dimensions, settings, hardware and warm/cold cache conditions have been tested.

## 4. Findings vs assumptions

| Classification | Statement |
|---|---|
| **FACT** | Lightroom Standard Previews are rendered by Camera Raw, unlike embedded camera JPEGs. [S5] |
| **FACT** | Darktable's module order changes processing behavior, and it offers scene-referred operations. [S11, S12] |
| **FACT** | Darktable provides area exposure mapping while warning about variably illuminated faces. [S13] |
| **FACT** | RawTherapee's Auto-Matched Curve can use the embedded camera JPEG as a tonal reference for initial raw interpretation. [S1] |
| **FACT** | Camera-as-shot WB is conceptually separate from Lightroom's image-derived Auto WB. [S6] |
| **INFERENCE** | The same preset's subjective look will usually need deliberate per-renderer color/tone work rather than 1:1 slider values. Supported by differences in documented pipelines, but any specific rendition must be tested. |
| **EXPERIMENT REQUIRED** | Which Darktable module combination most closely matches the actual Lightroom `zp` look on the same Nikon NEFs. |
| **EXPERIMENT REQUIRED** | Whether semantic AI can reliably predict individual Exposure corrections better/faster than region matching or other deterministic methods on the intended event photos. |
| **EXPERIMENT REQUIRED** | Which camera/ISO noise profile and lens profile work for each intended Nikon NEF/lens and Darktable version. |
| **EXPERIMENT REQUIRED** | Whether a no-GUI RAW batch workflow is faster *end to end* once human/AI inspection and required rerenders are included. |

## 5. Consequences for future engine research — not yet a design decision

These are derived research questions for Phase 2, not instructions to change the existing project:

1. Is the objective **matching existing Lightroom JPEGs**, **consistent event-documentary appearance**, or both? These are related but not identical loss functions.
2. Can an exposure decision be made from a verified preset-applied rendered preview while retaining a clear mapping to a subsequent *real RAW renderer* correction?
3. Can group-level judgment be separated from per-image exceptions, avoiding the failure of both “one global brightness target” and “100+ fragmented scenes”?
4. What is the smallest reliable closed-loop experiment: one representative scene, several source RAWs, a few exposure candidates rendered by the **actual** engine, visual choice, then measured validation?
5. Can the same-source, same-output-profile comparison avoid being confounded by different camera input profiles, WB interpretations, automatic style modules, highlight reconstruction, lens corrections and denoise?
6. What would a terminal pass require: one decision per image, exact image identity, applied-value verification, render freshness and a meaningful unresolved count?

**Phase 1 boundary:** No engine architecture has been approved; no source photos were changed; no Lightroom or Darktable processing was run as part of this literature review.

## Sources — verified primary documentation

- **[S1] RawPedia — Getting Started** (RAW interpretation, camera-embedded JPEG, auto-matched camera curve). https://rawpedia.rawtherapee.com/Getting_Started
- **[S2] RawPedia — Color Management** (camera input profiles, working RGB, DCP/ICC). https://rawpedia.rawtherapee.com/Color_Management
- **[S3] RawPedia — Exposure** (auto levels, highlight reconstruction vs compression, RAW exposure compensation). https://rawpedia.rawtherapee.com/Exposure
- **[S4] RawPedia — Command-Line Options** (`rawtherapee-cli` and PP3 profile order). https://rawpedia.rawtherapee.com/Command-Line_Options
- **[S5] Adobe — Optimize Lightroom performance** (embedded/standard/1:1 preview differences). https://helpx.adobe.com/lightroom-classic/desktop/technical-support/performance-guidelines/optimize-performance-lightroom.html
- **[S6] Adobe — Adjust image tone and color in Lightroom Classic** (profiles; As Shot and Auto WB). https://helpx.adobe.com/lightroom-classic/desktop/process-and-develop-photos/image-tone-color.html
- **[S7] Adobe — Develop module options** (Camera Raw Process Version). https://helpx.adobe.com/lightroom-classic/desktop/process-and-develop-photos/develop-module-options.html
- **[S8] Adobe — Metadata basics and actions** (Catalog, XMP/ACR sidecar behavior). https://helpx.adobe.com/lightroom-classic/desktop/organize-photos-in-lightroom-classic/metadata-basics-actions.html
- **[S9] Capture One — Base Characteristics panel** (camera ICC, film curve and engine). https://support.captureone.com/hc/en-us/articles/360002588917-The-Base-Characteristics-panel-overview
- **[S10] Capture One — Selecting an alternative tone curve**. https://support.captureone.com/hc/en-us/articles/360002593758-Selecting-an-alternative-tone-curve
- **[S11] darktable — Module order**. https://docs.darktable.org/usermanual/development/en/module-reference/utility-modules/darkroom/module-order/
- **[S12] darktable — Color pipeline**. https://docs.darktable.org/usermanual/development/en/special-topics/color-pipeline/
- **[S13] darktable — Exposure and area exposure mapping**. https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/exposure/
- **[S14] darktable — Color calibration and area color mapping**. https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/color-calibration/
- **[S15] darktable — darktable-cli**. https://docs.darktable.org/usermanual/development/en/special-topics/program-invocation/darktable-cli/
- **[S16] darktable — Styles and `.dtstyle`**. https://docs.darktable.org/usermanual/development/en/module-reference/utility-modules/shared/styles/
- **[S17] darktable — Lens correction**. https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/lens-correction/
- **[S18] darktable — Denoise (profiled)**. https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/denoise-profiled/
- **[S19] W3C — CSS Color 4 (2026-10-08 candidate draft): sRGB/linear-light transfer functions**. https://www.w3.org/TR/2026/CRD-css-color-4-20261008/

**Version caveat:** darktable manuals at `/development/` document the development manual, not an exact guarantee about every installed 5.6.x binary. Any module/default/CLI behavior used for production must be reconfirmed against the exact installed build. RawPedia sections may also reference specific earlier versions; treat those version-specific default values as historical unless validated.

**Review/approval status:** literature-based Phase 1 evidence recorded; Phase 2 engine design and actual benchmarks remain unapproved/unexecuted.
