# Work Order 032: Whole-Folder Batch Processing & Iterative Schema

## Context
The prior work order stopped at diagnostic reporting. The owner requested to implement the full continuous section until the system supports whole-folder analysis (recursive photo collection) and incorporates the Action enum, scene_group_id, is_reference, and other iterative-pass schema fields.

## Objectives
- [x] Recursive photo collection via Lightroom Lua (ctiveFolder:getPhotos(true)).
- [x] Upgrade data model (SinglePassDecision) with Action (PASS, ADJUST, REVIEW) instead of relying solely on Verdict.
- [x] Replace atch_consistency_group with scene_group_id and introduce is_reference.
- [x] Update JSON schema generation and AI task prompt (AI_TASK.md).
- [x] Update job lifecycle filtering (ligible_apply_ids) to use Action.ADJUST.
- [x] Pass all automated tests without regression.

## Status
IMPLEMENTED and TESTED. Committed locally as requested.

## Next Steps
The owner can now deploy to Lightroom and test a real whole-folder workflow, observing the new decision structure and recursive traversal.
