# WO-006 — Lightroom Plugin Skeleton

STATUS: DONE

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

## Closeout Evidence

- **Implementation**: `lightroom-plugin/AIExposureAssist.lrplugin/` with `Info.lua` (valid SDK metadata), `PluginInit.lua` (binds `AI Exposure Assist` under Plug-in Extras), `RunExposureAssist.lua` (no-op `run` entry). No Python execution, preview export, AI, catalog mutation, or XMP writes.
- **Tests**: `tests/test_lightroom_plugin_contract.py` — 6 tests (1 Lua-parse skip when interpreter absent). Validates file presence, metadata, command registration, `run` entry, no-side-effects contract, and Info.lua structure.
- **Validation**: `pytest -q` → 41 passed (1 skip), 0 failed. `compileall -q src` → pass. `git diff --check` → pass (CRLF warning only).
- **Capability impact**: CAP-016 (plug-in loading) → TESTED. CAP-017 (menu command registration) → TESTED.
- **Scope**: Only allowed files changed (3 Lua files, test, README, traceability docs, CURRENT_WORK_ORDER.md, this work order).
- **Stop conditions respected**: no Lightroom runtime required for tests; not pushed; WO-007 not started within this commit.
