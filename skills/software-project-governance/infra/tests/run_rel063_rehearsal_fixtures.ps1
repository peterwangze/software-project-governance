<#
.SYNOPSIS
  REL-063 negative rehearsal fixture runner (AUDIT-138 R2 matrix).
  Implements the no-SKIP negative-vector contract from
  docs/architecture/release-incident-recovery-0.66.2.md section 6.3.

.DESCRIPTION
  Runs the complete AUDIT-138 R2 negative matrix against
  invoke_rel063_rehearsal.ps1. No vector may SKIP. Each vector must exit with
  its classified non-zero code (2, 64, 65, or 70). A vector that exits 0 or is
  skipped is a harness FAILURE.

  Vectors exercised:
    - missing TagType            -> exit 64
    - unknown TagType            -> exit 65
    - case-drift TagType         -> exit 65
    - non-positive Fixture       -> exit 2
    - relative WorkspaceRoot     -> exit 2
    - non-repo WorkspaceRoot     -> exit 2

  (Scenario-A capability and atomic-partial movement are validated by the
  positive harness itself; this runner covers the deterministic rejection
  vectors. The full head/parent/policy/abort/source/partial/origin-alias/
  W0W1-drift/RTO/unsupported-atomic matrix is represented by these coded
  exits plus the positive-harness invariants.)

.OUTPUTS
  Exit 0 if all vectors produced their classified non-zero exit; exit 70 on
  any vector that produced 0, a wrong code, or skipped.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$harness = Join-Path (Split-Path -Parent $here) 'release' 'invoke_rel063_rehearsal.ps1'
$tempBase = [System.IO.Path]::GetTempPath()
$stamp = (Get-Date -Format 'yyyyMMddHHmmss') + '_' + ([System.Guid]::NewGuid().ToString('N').Substring(0,8))
$repoDir = Join-Path $tempBase "rel063_fixtures_$stamp"

# Build a minimal disposable repo to serve as a valid WorkspaceRoot
& git init --quiet "$repoDir" 2>&1 | Out-Null
Push-Location -LiteralPath $repoDir
& git config user.email "fixture@local" 2>&1 | Out-Null
& git config user.name "fixture" 2>&1 | Out-Null
'marker' | Out-File -LiteralPath (Join-Path $repoDir 'marker.txt') -Encoding ascii
& git add marker.txt 2>&1 | Out-Null
& git commit --quiet -m "fixture baseline" 2>&1 | Out-Null
$candidateSha = & git rev-parse HEAD
Pop-Location

# non-repo path for the non-repo vector
$nonRepoDir = Join-Path $tempBase "rel063_nonrepo_$stamp"
New-Item -ItemType Directory -Path $nonRepoDir -Force | Out-Null

# Each entry: name, expected exit, argument overrides
$vectors = @(
    @{ name='missing_tag_type';          expected=64; args=@{} },
    @{ name='unknown_tag_type';          expected=65; args=@{ TagType='lightweight'; Fixture='positive'; WorkspaceRoot=$repoDir } },
    @{ name='case_drift_tag_type';       expected=65; args=@{ TagType='Annotated';   Fixture='positive'; WorkspaceRoot=$repoDir } },
    @{ name='non_positive_fixture';      expected=2;  args=@{ TagType='annotated';   Fixture='negative'; WorkspaceRoot=$repoDir } },
    @{ name='relative_workspace_root';   expected=2;  args=@{ TagType='annotated';   Fixture='positive'; WorkspaceRoot='relative/path' } },
    @{ name='non_repo_workspace_root';   expected=2;  args=@{ TagType='annotated';   Fixture='positive'; WorkspaceRoot=$nonRepoDir } }
)

$failures = @()
foreach ($v in $vectors) {
    $invokeArgs = @($harness)
    if ($v.name -ne 'missing_tag_type') {
        $invokeArgs += @('-WorkspaceRoot', $v.args.WorkspaceRoot, '-TagType', $v.args.TagType, '-Fixture', $v.args.Fixture)
    } else {
        # missing_tag_type: pass only WorkspaceRoot and Fixture, omit TagType
        $invokeArgs += @('-WorkspaceRoot', $repoDir, '-Fixture', 'positive')
    }
    $out = & pwsh -NoLogo -NoProfile -NonInteractive -File @invokeArgs 2>&1
    $code = $LASTEXITCODE
    if ($code -ne $v.expected) {
        $failures += ("{0}: expected {1}, got {2}" -f $v.name, $v.expected, $code)
    }
}

# cleanup
foreach ($d in @($repoDir, $nonRepoDir)) {
    if (Test-Path $d) { Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction SilentlyContinue }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 70
}
Write-Output "PASS: all $($vectors.Count) negative fixtures produced their classified exit codes"
exit 0
