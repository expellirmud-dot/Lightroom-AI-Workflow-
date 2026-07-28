# WO-006 — Lightroom Plugin Skeleton

STATUS: PLANNED

## Objective

Create a minimal Lightroom Classic plug-in shell with a visible command and no Python execution, preview export, AI logic, catalog mutation, or XMP writes.

## Read-First Level

`IMPACT`

Run the `project-read-first` skill before editing.

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Lightroom plug-in loading | NOT_STARTED | TESTED |
| Menu command registration | NOT_STARTED | TESTED |

## Allowed Files

- `lightroom-plugin/AIExposureAssist.lrplugin/Info.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PluginInit.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/RunExposureAssist.lua`
- `tests/test_lightroom_plugin_contract.py`
- `README.md`
- Traceability and active Work Order documents

## Requirements

- Use valid Lightroom SDK plug-in metadata.
- Register `AI Exposure Assist` under Plug-in Extras.
- The command may report selection count or a clear not-yet-implemented message.
- No catalog write access, subprocess, network, preview export, or file mutation.
- Add static contract tests that run without Lightroom.

## Validation

Run focused tests, full pytest, compileall for Python sources, diff check, and Git status review.

## Closeout

Commit exactly once after passing gates. Do not push and do not begin WO-007.
