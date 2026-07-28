param(
    [string]$StartPath = "."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Decision {
    param(
        [string]$Decision,
        [string]$Reason = ""
    )
    Write-Output "PREFLIGHT_DECISION=$Decision"
    if ($Reason) {
        Write-Output "BLOCK_REASON=$Reason"
    }
}

function Resolve-CanonicalRoot {
    param([string]$Path)
    $resolved = git -C $Path rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $resolved) {
        return $null
    }
    return $resolved
}

$root = Resolve-CanonicalRoot -Path $StartPath
if (-not $root) {
    Write-Decision -Decision "BLOCKED_MISSING_AUTHORITY" -Reason "Not a Git repository or no git in PATH"
    exit 1
}

# Valid preflight decision values (all eight, as documented in PREFLIGHT_OUTPUT_CONTRACT.md)
$validDecisions = @(
    "READY",
    "BLOCKED_DIRTY_WORKTREE",
    "BLOCKED_PROJECT_MISMATCH",
    "BLOCKED_SERENA",
    "BLOCKED_CODEGRAPH",
    "BLOCKED_MISSING_AUTHORITY",
    "BLOCKED_SCOPE_CONFLICT",
    "BLOCKED_OWNER_DECISION"
)

$currentDir = (Get-Location).Path
try {
    Set-Location -Path $root -ErrorAction Stop
} catch {
    Write-Decision -Decision "BLOCKED_MISSING_AUTHORITY" -Reason "Cannot change to repository root"
    exit 1
}

$branch = try { git branch --show-current 2>$null } catch { "" }
$head = try { git rev-parse HEAD 2>$null } catch { "" }
$upstream = try { git rev-parse --abbrev-ref HEAD@{upstream} 2>$null } catch { "" }
$origin = try { git remote get-url origin 2>$null } catch { "" }
$gitStatus = try { git status --short 2>$null } catch { "" }

# Check mandatory authority files exist
$mandatoryFiles = @(
    "AGENTS.md",
    "docs/INDEX.md",
    "Work-Order/CURRENT_WORK_ORDER.md"
)
$missingFiles = @()
foreach ($f in $mandatoryFiles) {
    if (-not (Test-Path -Path (Join-Path $root $f) -PathType Leaf)) {
        $missingFiles += $f
    }
}

$hasDirty = $false
if ($gitStatus -and $gitStatus.Trim()) {
    $hasDirty = $true
}

if ($missingFiles.Count -gt 0) {
    Write-Decision -Decision "BLOCKED_MISSING_AUTHORITY" -Reason "Missing mandatory files: $($missingFiles -join ', ')"
    exit 1
}

if ($hasDirty) {
    Write-Decision -Decision "BLOCKED_DIRTY_WORKTREE" -Reason "Working tree has uncommitted changes"
    exit 1
}

Write-Output "READ_FIRST_PREFLIGHT"
Write-Output ""
Write-Output "REPOSITORY_ROOT=$root"
Write-Output "CURRENT_DIRECTORY=$currentDir"
Write-Output "BRANCH=$branch"
Write-Output "HEAD=$head"
Write-Output "UPSTREAM=$upstream"
Write-Output "ORIGIN=$origin"
Write-Output "GIT_STATUS=$gitStatus"
Write-Output ""

# Serena verification
$serenaProject = "NOT_VERIFIED"
$serenaStatus = "NOT_VERIFIED"
if (Get-Command "serena" -ErrorAction SilentlyContinue) {
    $serenaProject = $root
    $serenaStatus = "AVAILABLE"
}

# CodeGraph verification
$codegraphProject = "NOT_VERIFIED"
$codegraphStatus = "NOT_VERIFIED"
$codegraphSync = "UNKNOWN"
if (Test-Path (Join-Path $root ".codegraph")) {
    $codegraphProject = $root
    $codegraphStatus = "AVAILABLE"
    $codegraphSync = "yes"
}

# Work Order read status (placeholder until active Work Order is identified)
$activeWorkOrder = "PENDING_READ"
$workOrderStatus = "PENDING_READ"
$capabilityIds = "PENDING_READ"
$allowedFiles = "PENDING_READ"
$forbiddenFiles = "PENDING_READ"

# Read status from Work Order pointer in CURRENT_WORK_ORDER.md
$currentWoPath = Join-Path $root "Work-Order" "CURRENT_WORK_ORDER.md"
if (Test-Path $currentWoPath) {
    $woContent = Get-Content -Path $currentWoPath -Raw -ErrorAction SilentlyContinue
    if ($woContent -match 'WORK_ORDER:\s*`(.+?)`') {
        $activeWorkOrder = $Matches[1]
    }
    if ($woContent -match 'STATUS:\s*(\w+)') {
        $workOrderStatus = $Matches[1]
    }
    if ($woContent -match 'CAPABILITY_IDS') {
        $capabilityIds = "IN_WORK_ORDER"
    }
}

# Documentation impact (placeholder)
$documentationImpact = "PENDING_WORK_ORDER"
$commitAuthorization = "PENDING_WORK_ORDER"

# Expected change and validation (placeholder)
$expectedChange = "PENDING_TASK_DEFINITION"
$requiredValidation = "PENDING_WORK_ORDER"

# Serena project info
$serenaProjectOut = $serenaProject
if ($serenaProject -eq "NOT_VERIFIED") {
    $serenaStatus = "NOT_VERIFIED"
} else {
    $serenaStatus = "AVAILABLE"
}

# CodeGraph sync status
if ($codegraphSync -eq "UNKNOWN") {
    $codegraphSync = "not_checked"
}

# Emit output contract
Write-Output "READ_FIRST_PREFLIGHT"
Write-Output ""
Write-Output "REPOSITORY_ROOT=$root"
Write-Output "CURRENT_DIRECTORY=$currentDir"
Write-Output "BRANCH=$branch"
Write-Output "HEAD=$head"
Write-Output "UPSTREAM=$upstream"
Write-Output "ORIGIN=$origin"
Write-Output "GIT_STATUS=$gitStatus"
Write-Output ""
Write-Output "ACTIVE_WORK_ORDER=$activeWorkOrder"
Write-Output "WORK_ORDER_STATUS=$workOrderStatus"
Write-Output "CAPABILITY_IDS=$capabilityIds"
Write-Output "ALLOWED_FILES=$allowedFiles"
Write-Output "FORBIDDEN_FILES=$forbiddenFiles"
Write-Output ""
Write-Output "SERENA_PROJECT=$serenaProjectOut"
Write-Output "SERENA_STATUS=$serenaStatus"
Write-Output "CODEGRAPH_PROJECT=$codegraphProject"
Write-Output "CODEGRAPH_STATUS=$codegraphStatus"
Write-Output "CODEGRAPH_SYNC=$codegraphSync"
Write-Output ""
Write-Output "FULL_DOCUMENTS_READ=AGENTS.md,docs/INDEX.md,Work-Order/CURRENT_WORK_ORDER.md,ACTIVE_WORK_ORDER"
Write-Output "TARGETED_DOCUMENTS_READ=PENDING_WORK_ORDER_SCOPE"
Write-Output "SOURCE_SYMBOLS_INSPECTED=PENDING_TASK"
Write-Output ""
Write-Output "EXPECTED_CHANGE=$expectedChange"
Write-Output "REQUIRED_VALIDATION=$requiredValidation"
Write-Output "DOCUMENTATION_IMPACT=$documentationImpact"
Write-Output "COMMIT_AUTHORIZATION=$commitAuthorization"
Write-Output ""
Write-Decision -Decision "GIT_READY"
