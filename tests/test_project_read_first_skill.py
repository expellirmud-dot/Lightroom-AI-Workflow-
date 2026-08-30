import os
import subprocess
import sys
from pathlib import Path

def test_skill_files_exist() -> None:
    """Required skill files must exist at the canonical path."""
    root = _repo_root()
    skill_dir = root / ".agents" / "skills" / "project-read-first"

    required = [
        skill_dir / "SKILL.md",
        skill_dir / "scripts" / "preflight.ps1",
        skill_dir / "references" / "DOCUMENT_READ_POLICY.md",
        skill_dir / "references" / "SERENA_CODEGRAPH_PROTOCOL.md",
        skill_dir / "references" / "PREFLIGHT_OUTPUT_CONTRACT.md",
    ]

    for path in required:
        assert path.is_file(), f"Missing skill file: {path}"


def test_skill_frontmatter_valid() -> None:
    """SKILL.md must contain valid YAML frontmatter and the correct name."""
    root = _repo_root()
    skill_file = root / ".agents" / "skills" / "project-read-first" / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")

    assert content.startswith("---"), "SKILL.md must start with YAML frontmatter delimiter"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "SKILL.md must have closing frontmatter delimiter"

    frontmatter = parts[1]
    assert "name: project-read-first" in frontmatter, "SKILL.md frontmatter must declare name"
    assert "description:" in frontmatter, "SKILL.md frontmatter must declare description"


def test_preflight_script_no_mutation_commands() -> None:
    """The PowerShell script must not contain destructive Git commands."""
    root = _repo_root()
    script = root / ".agents" / "skills" / "project-read-first" / "scripts" / "preflight.ps1"
    content = script.read_text(encoding="utf-8")

    dangerous = ["git add", "git commit", "git reset", "git clean", "git stash", "git push"]
    for cmd in dangerous:
        assert cmd not in content, f"Script must not contain '{cmd}'"


def test_preflight_script_deterministic_output() -> None:
    """The PowerShell script must contain the expected output contract fields."""
    root = _repo_root()
    script = root / ".agents" / "skills" / "project-read-first" / "scripts" / "preflight.ps1"
    content = script.read_text(encoding="utf-8")

    required_fields = [
        "REPOSITORY_ROOT",
        "PREFLIGHT_DECISION",
        "GIT_READY",
        "BLOCKED_DIRTY_WORKTREE",
        "BLOCKED_PROJECT_MISMATCH",
        "BLOCKED_MISSING_AUTHORITY",
        "BLOCKED_SCOPE_CONFLICT",
        "BLOCKED_OWNER_DECISION",
    ]

    for field in required_fields:
        assert field in content, f"Script must reference '{field}'"


def test_mandatory_authority_files_in_skill() -> None:
    """The skill must reference the four mandatory authority documents."""
    root = _repo_root()
    skill_file = root / ".agents" / "skills" / "project-read-first" / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")

    mandatory = [
        "AGENTS.md",
        "docs/INDEX.md",
        "Work-Order/CURRENT_WORK_ORDER.md",
    ]
    for doc in mandatory:
        assert doc in content, f"Skill must reference mandatory document '{doc}'"


def test_all_terminal_decisions_documented() -> None:
    """All eight terminal preflight decisions must be documented."""
    root = _repo_root()
    contract = root / ".agents" / "skills" / "project-read-first" / "references" / "PREFLIGHT_OUTPUT_CONTRACT.md"
    content = contract.read_text(encoding="utf-8")

    decisions = [
        "READY",
        "BLOCKED_DIRTY_WORKTREE",
        "BLOCKED_PROJECT_MISMATCH",
        "BLOCKED_SERENA",
        "BLOCKED_CODEGRAPH",
        "BLOCKED_MISSING_AUTHORITY",
        "BLOCKED_SCOPE_CONFLICT",
        "BLOCKED_OWNER_DECISION",
    ]
    for d in decisions:
        assert d in content, f"Decision '{d}' must be documented in output contract"


def test_output_contract_has_all_fields() -> None:
    """The output contract must contain every required field."""
    root = _repo_root()
    contract = root / ".agents" / "skills" / "project-read-first" / "references" / "PREFLIGHT_OUTPUT_CONTRACT.md"
    content = contract.read_text(encoding="utf-8")

    required = [
        "REPOSITORY_ROOT", "CURRENT_DIRECTORY", "BRANCH", "HEAD",
        "UPSTREAM", "ORIGIN", "GIT_STATUS", "ACTIVE_WORK_ORDER",
        "WORK_ORDER_STATUS", "CAPABILITY_IDS", "ALLOWED_FILES",
        "FORBIDDEN_FILES", "SERENA_PROJECT", "SERENA_STATUS",
        "CODEGRAPH_PROJECT", "CODEGRAPH_STATUS", "CODEGRAPH_SYNC",
        "FULL_DOCUMENTS_READ", "TARGETED_DOCUMENTS_READ",
        "SOURCE_SYMBOLS_INSPECTED", "EXPECTED_CHANGE",
        "REQUIRED_VALIDATION", "DOCUMENTATION_IMPACT",
        "COMMIT_AUTHORIZATION", "PREFLIGHT_DECISION", "BLOCK_REASON",
    ]
    for field in required:
        assert field in content, f"Output contract must contain field '{field}'"


def test_serena_and_codegraph_are_on_demand_policy_aids() -> None:
    """Regression: generic implementation must not require either MCP tool."""
    root = _repo_root()
    skill_dir = root / ".agents" / "skills" / "project-read-first"
    skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    protocol = (skill_dir / "references" / "SERENA_CODEGRAPH_PROTOCOL.md").read_text(
        encoding="utf-8"
    )
    document_policy = (skill_dir / "references" / "DOCUMENT_READ_POLICY.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([skill, protocol, document_policy])
    normalized = " ".join(combined.split())

    assert "Serena = `ON_DEMAND`" in combined
    assert "CodeGraph = `ON_DEMAND`" in combined
    assert "ordinary bounded implementation" in normalized
    assert "documentation-only" in normalized.lower()
    assert "Serena and CodeGraph must be verified before source implementation" not in combined


def test_preflight_accepts_not_required_mcp_statuses() -> None:
    """Regression: unused MCP capabilities must be reported without blocking."""
    root = _repo_root()
    skill_dir = root / ".agents" / "skills" / "project-read-first"
    contract = (skill_dir / "references" / "PREFLIGHT_OUTPUT_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    script = (skill_dir / "scripts" / "preflight.ps1").read_text(encoding="utf-8")

    assert "SERENA_STATUS=NOT_REQUIRED" in script
    assert "CODEGRAPH_STATUS=NOT_REQUIRED" in script
    assert "NOT_REQUIRED" in contract
    assert "REQUIRED_BUT_UNAVAILABLE" in contract


def test_mcp_blocking_decisions_are_conditional() -> None:
    """Regression: MCP absence blocks only a genuinely MCP-dependent task."""
    root = _repo_root()
    protocol = (
        root
        / ".agents"
        / "skills"
        / "project-read-first"
        / "references"
        / "SERENA_CODEGRAPH_PROTOCOL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(protocol.split())

    assert "concrete task genuinely requires" in normalized
    assert "smaller authoritative method" in normalized
    assert "materially risk correctness" in normalized
    assert "`BLOCKED_SERENA`" in protocol
    assert "`BLOCKED_CODEGRAPH`" in protocol


def test_policy_requires_smallest_sufficient_nonduplicative_retrieval() -> None:
    """Regression: unchanged source must not be fetched repeatedly across tools."""
    root = _repo_root()
    skill_dir = root / ".agents" / "skills" / "project-read-first"
    skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    document_policy = (skill_dir / "references" / "DOCUMENT_READ_POLICY.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([skill, document_policy])

    assert "smallest sufficient tool" in combined
    assert "Never retrieve the same unchanged source body through multiple mechanisms" in combined
    assert "delta preflight" in combined.lower()


def test_repository_paths_not_hardcoded() -> None:
    """Skill and script must not hard-code the example repository path."""
    root = _repo_root()
    skill_dir = root / ".agents" / "skills" / "project-read-first"

    for file_path in skill_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in {".md", ".ps1", ".py", ".txt"}:
            content = file_path.read_text(encoding="utf-8")
            assert (
                "D:\\ai-tools\\lightroom-ai-exposure" not in content
            ), f"Hard-coded repo path found in {file_path}"


def _repo_root() -> Path:
    """Resolve the Git repository root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())
