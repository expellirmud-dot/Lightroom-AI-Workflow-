from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "lightroom-plugin" / "AIExposureAssist.lrplugin"


def _read(name: str) -> str:
    return (PLUGIN / name).read_text(encoding="utf-8")


def test_production_selection_preserves_recursive_folder_photo_count() -> None:
    support = _read("SessionPackageSupport.lua")
    start = support.index("function Support.buildProductionSelectionPayload")
    end = support.index("function Support.writeProductionSelectionSnapshot", start)
    production_block = support[start:end]
    assert "folder_photo_count = exclusions.folderPhotoCount" in production_block
    assert "#(exclusions or {})" not in production_block


def test_prepare_production_job_shell_is_one_job_non_mutating_and_not_pass_based() -> None:
    src = _read("PrepareProductionJob.lua")
    assert "Support.writeProductionSelectionSnapshot" in src
    assert "--prepare-production-job" in src
    assert "Support.loadPreviewCachePath()" in src
    assert "--selection" in src
    assert "--lrdata" in src
    assert "--bridge-result" in src
    assert "result.job_dir" in src
    assert "result.workflow_state" in src
    assert "applyDevelopSettings" not in src
    assert "withWriteAccessDo" not in src
    assert "--start-session" not in src
    assert "--prepare-session-pass" not in src
    assert "pass_number" not in src
    assert "runtime\\\\sessions" not in src


def test_prepare_production_job_shell_can_be_delegated_synchronously() -> None:
    src = _read("PrepareProductionJob.lua")
    assert "function PrepareProductionJob.run()" in src
    assert "if not Support.deferAutoStart then" in src
    assert "LrTasks.startAsyncTask" in src


def test_normal_continue_routes_minimal_production_without_legacy_fallback() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    assert "--production-workflow-status" in router
    assert 'runLowLevel("PrepareProductionJob.lua", nil)' in router
    assert "CatalogApplyBarrier.applyCatalogPlan" in router
    assert "--confirm-production-apply" in router
    assert "--measure-production-fresh-previews" in router
    assert "--verify-production-renders" in router
    assert "--confirm-production-residual-apply" in router
    assert "--verify-production-residual-renders" in router
    for state in ("READY", "ANALYZING", "READY_TO_APPLY", "VERIFYING", "COMPLETE", "NEEDS_ATTENTION"):
        assert f'state == "{state}"' in router
    assert "--apply-session-pass" not in router
    assert "--prepare-session-pass" not in router


def test_production_continue_requires_owner_confirmation_for_initial_and_residual_catalog_mutation() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    assert '"AI Exposure Assist - READY_TO_APPLY"' in router
    assert '"AI Exposure Assist - FINE_TUNE_RESIDUAL"' in router
    assert '"Fine-Tune Exposure"' in router
    assert "Residual apply requires explicit Owner confirmation" in router


def test_production_continue_does_not_immediately_verify_after_catalog_apply() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    ready_start = router.index('if state == "READY_TO_APPLY" then')
    verifying_start = router.index('if state == "VERIFYING" then', ready_start)
    ready_block = router[ready_start:verifying_start]
    assert "confirmInitialApply(jobId, applyResultPath)" in ready_block
    assert "runVerifyStep" not in ready_block
    assert "showPostApplyRefreshMessage(jobId, confirmed.verified_count)" in ready_block
    assert "Run Continue Exposure Workflow again after Lightroom has refreshed previews" in router


def test_production_ready_to_apply_dialog_displays_exact_plan_counts() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    assert "Will adjust:" in router
    assert "No change:" in router
    assert "Unresolved:" in router
    assert "Total:" in router


def test_production_continue_disambiguates_initial_vs_residual_verification_from_durable_internal_state() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    assert 'internalState == "VERIFYING_RENDERS"' in router
    assert 'return "VERIFY_ADJUSTED_RENDERS"' in router
    assert 'internalState == "VERIFYING_RESIDUAL"' in router
    assert 'return "VERIFY_RESIDUAL_RENDER"' in router
    assert 'internalState == "APPLYING_CATALOG"' in router
    assert 'internalState == "APPLYING_RESIDUAL"' in router
    assert "refusing render verification until apply evidence is recovered" in router


def test_production_complete_dialog_recovers_persisted_final_accounting_on_later_continue() -> None:
    router = _read("ContinueExposureWorkflow.lua")
    assert 'LrPathUtils.child(jobDir, "final-results.json")' in router
    assert "counts.input_count" in router
    assert "counts.adjusted" in router
    assert "counts.no_change" in router
    assert "counts.unresolved" in router
    assert "counts.invariant_verified" in router


def test_prepare_production_job_prewarms_standard_preview_cache_without_catalog_mutation() -> None:
    src = _read("PrepareProductionJob.lua")
    assert "photo:requestJpegThumbnail" in src
    assert "ensureProductionPreviews(photos, 1440)" in src
    assert "PREVIEW_WARM_TIMEOUT" in src
    assert "PREVIEW_WARM_FAILED" in src
    assert "applyDevelopSettings" not in src
    assert "withWriteAccessDo" not in src
