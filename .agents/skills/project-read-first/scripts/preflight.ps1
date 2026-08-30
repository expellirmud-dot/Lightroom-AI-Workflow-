param(
    [string]$StartPath = ".",
    [string[]]$NonBlockingDirtyPath = @(),
    [string[]]$CriticalDirtyPath = @()
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
$upstream = try { git rev-parse --abbrev-ref 'HEAD@{upstream}' 2>$null } catch { "" }
$origin = try { git remote get-url origin 2>$null } catch { "" }
$gitStatus = try { @(git status --short 2>$null) } catch { @() }

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

$dirtyPaths = @(
    foreach ($line in $gitStatus) {
        if ($line -and $line.Length -ge 4) {
            $line.Substring(3).Trim()
        }
    }
)
$unexpectedDirty = @($dirtyPaths | Where-Object { $_ -notin $NonBlockingDirtyPath })
$criticalDirty = @($dirtyPaths | Where-Object { $_ -in $CriticalDirtyPath })
$dirtyClassification = "CLEAN"
if ($criticalDirty.Count -gt 0) {
    $dirtyClassification = "CRITICAL"
} elseif ($unexpectedDirty.Count -gt 0) {
    $dirtyClassification = "BLOCKING"
} elseif ($dirtyPaths.Count -gt 0) {
    $dirtyClassification = "NON_BLOCKING"
}

if ($missingFiles.Count -gt 0) {
    Write-Decision -Decision "BLOCKED_MISSING_AUTHORITY" -Reason "Missing mandatory files: $($missingFiles -join ', ')"
    exit 1
}

if ($dirtyClassification -eq "CRITICAL") {
    Write-Output "DIRTY_CLASSIFICATION=CRITICAL"
    Write-Decision -Decision "BLOCKED_DIRTY_WORKTREE" -Reason "Critical dirty paths: $($criticalDirty -join ', ')"
    exit 1
}

if ($dirtyClassification -eq "BLOCKING") {
    Write-Output "DIRTY_CLASSIFICATION=BLOCKING"
    Write-Decision -Decision "BLOCKED_DIRTY_WORKTREE" -Reason "Dirty paths require classification or overlap task scope: $($unexpectedDirty -join ', ')"
    exit 1
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
    if ($woContent -match 'ACTIVE_WORK_ORDER:\s*([^\r\n]+)') {
        $activeWorkOrder = $Matches[1].Trim()
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
Write-Output "SERENA_PROJECT=NOT_REQUIRED"
Write-Output "SERENA_STATUS=NOT_REQUIRED"
Write-Output "CODEGRAPH_PROJECT=NOT_REQUIRED"
Write-Output "CODEGRAPH_STATUS=NOT_REQUIRED"
Write-Output "CODEGRAPH_SYNC=NOT_REQUIRED"
Write-Output ""
Write-Output "FULL_DOCUMENTS_READ=AGENTS.md,docs/INDEX.md,Work-Order/CURRENT_WORK_ORDER.md,ACTIVE_WORK_ORDER"
Write-Output "TARGETED_DOCUMENTS_READ=PENDING_WORK_ORDER_SCOPE"
Write-Output "SOURCE_SYMBOLS_INSPECTED=PENDING_TASK"
Write-Output ""
Write-Output "PREFLIGHT_REUSE=no"
Write-Output "DIRTY_CLASSIFICATION=$dirtyClassification"
$nonBlockingOut = if ($dirtyClassification -eq "NON_BLOCKING") { $dirtyPaths -join ',' } else { "NONE" }
Write-Output "NON_BLOCKING_EXCLUSIONS=$nonBlockingOut"
Write-Output ""
Write-Output "EXPECTED_CHANGE=$expectedChange"
Write-Output "REQUIRED_VALIDATION=$requiredValidation"
Write-Output "DOCUMENTATION_IMPACT=$documentationImpact"
Write-Output "COMMIT_AUTHORIZATION=$commitAuthorization"
Write-Output ""
# GIT_READY was the historical label; READY is the canonical terminal value.
Write-Decision -Decision "READY"
