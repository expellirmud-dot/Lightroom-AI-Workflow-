from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "lightroom-plugin" / "AIExposureAssist.lrplugin"


def _read(name: str) -> str:
    return (PLUGIN / name).read_text(encoding="utf-8")


def _assert_no_resident_listener(text: str) -> None:
    lowered = text.lower()
    assert "waiting_for_ai" not in lowered
    assert "while true" not in lowered
    assert "lrtasks.sleep" not in lowered
    assert "settimeout" not in lowered


def test_menu_exposes_decoupled_commands_not_resume_command():
    info = _read("Info.lua")
    assert 'title = "AI Exposure Assist — Prepare AI Package"' in info
    assert 'file = "PrepareAIPackage.lua"' in info
    assert 'title = "AI Exposure Assist — Import / Apply AI Results"' in info
    assert 'file = "ImportApplyAIResults.lua"' in info
    assert 'title = "AI Exposure Assist — Prepare Next AI Package"' in info
    assert 'file = "PrepareNextAIPackage.lua"' in info
    assert 'file = "ResumeIterativeSession.lua"' not in info


def test_prepare_package_is_short_lived_and_never_calls_ai_provider():
    text = _read("PrepareAIPackage.lua")
    assert "PACKAGE_READY" in text
    assert "--start-session" in text
    assert "--analyze-session-pass" not in text
    assert "--apply-session-pass" not in text
    _assert_no_resident_listener(text)


def test_import_apply_never_prepares_next_pass_or_waits_for_ai():
    text = _read("ImportApplyAIResults.lua")
    assert "AI_RESULTS_NOT_READY" in text
    assert "RERENDER_REQUIRED" in text
    assert "--analyze-session-pass" in text
    assert "--apply-session-pass" in text
    assert "--prepare-session-pass" not in text
    _assert_no_resident_listener(text)


def test_next_package_command_owns_later_pass_preparation_only():
    text = _read("PrepareNextAIPackage.lua")
    assert "PACKAGE_READY" in text
    assert "--prepare-session-pass" in text
    assert "catalog-apply-evidence.json" in text
    assert "--analyze-session-pass" not in text
    assert "--apply-session-pass" not in text
    assert "applyDevelopSettings" not in text
    _assert_no_resident_listener(text)


def test_shared_support_keeps_exposure2012_only_catalog_mutation():
    text = _read("SessionPackageSupport.lua")
    assert "photo:applyDevelopSettings({ Exposure2012 = target })" in text
    forbidden = [
        "WhiteBalance",
        "Contrast2012",
        "Highlights2012",
        "Shadows2012",
        "Whites2012",
        "Blacks2012",
        "Clarity2012",
        "Texture",
        "Vibrance",
        "Saturation",
    ]
    for name in forbidden:
        assert name not in text


def test_canonical_iterative_commands_do_not_access_catalog_database_or_write_lrdata():
    names = [
        "PrepareAIPackage.lua",
        "ImportApplyAIResults.lua",
        "PrepareNextAIPackage.lua",
        "SessionPackageSupport.lua",
    ]
    combined = "\n".join(_read(name) for name in names)
    assert ".lrcat" not in combined.lower()
    assert ".lrcat-wal" not in combined.lower()
    assert ".lrcat-shm" not in combined.lower()
    assert "sqlite" not in combined.lower()
    assert "previews.lrdata" not in combined.lower() or "read-only" in combined.lower()
