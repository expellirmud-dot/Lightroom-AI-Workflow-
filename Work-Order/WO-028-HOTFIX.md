# WO-028-HOTFIX: Replace LrJson with local Json module

## Objective
Proceed with WO-028 hotfix to remove LrJson dependency which causes runtime failures.

## Confirmed runtime failure source
`lightroom-plugin/AIExposureAssist.lrplugin/RunExposureAssist.lua`

References:
- line 12: `local LrJson = import "LrJson"`
- line 100: `LrJson.encode(jobData)`
- line 155: `LrJson.decode(evidenceContent)`

## Required implementation

1. Remove:
   `local LrJson = import "LrJson"`

2. Add a repository-owned JSON module inside:
   `lightroom-plugin/AIExposureAssist.lrplugin/`
   Preferred file: `Json.lua`

3. Import it locally using the plugin path mechanism supported by the existing plugin structure.

4. Replace:
   `LrJson.encode(jobData)`
with:
   `Json.encode(jobData)`

5. Replace:
   `LrJson.decode(evidenceContent)`
with:
   `Json.decode(evidenceContent)`

6. Remove the fallback branch:
   "LrJson not found. Cannot encode JSON securely."

7. The local codec must support:
   - object, array, string, number, boolean, null
   - UTF-8/Thai text
   - Windows backslashes
   - escaped quotes
   - malformed JSON rejection

8. Preserve exact selection order and the existing bridge protocol.

9. Do not alter:
   - Python analysis logic
   - XMP apply logic
   - RAW files
   - Lightroom catalog
   - preview-cache databases

## Validation

1. Add tests for:
   - encode selection payload
   - decode evidence payload
   - Thai filename
   - Windows path
   - quotes/backslashes
   - malformed JSON
   - ordered identities

2. After implementation run:
   ```powershell
   Get-ChildItem lightroom-plugin -Recurse -File | Select-String -Pattern "LrJson"
   ```
   Expected result: no matches

3. Reload the plugin in Lightroom and perform real smoke:
   - select one disposable photo
   - invoke AI Exposure Assist
   - confirm no namespace error
   - confirm selection.json is created
   - report its exact path

4. Then run:
   ```powershell
   uv run python -m lr_ai_exposure.main `
     --analyze-only `
     --selection "<REAL_SELECTION_JSON_PATH>" `
     --lrdata "C:\Users\Expellirmud\Pictures\LR\ToTo\ToTo Previews.lrdata"
   ```
   Required result: mode = ANALYZE_ONLY, applied = 0

## Closeout Requirements
- Commit once.
- Do not push.
- Produce required markers in the final report.

## Closeout Record

- **Date**: 2026-07-29
- **Status**: COMPLETED
- **Notes**: Real Lightroom smoke pass. Manual app import passed, status OK, mode ANALYZE_ONLY. 1 decision imported and 0 applied.
