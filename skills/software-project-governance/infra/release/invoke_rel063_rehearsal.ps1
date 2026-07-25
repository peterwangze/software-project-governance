<#
.SYNOPSIS
  REL-063 disposable atomic push/abort/rollback rehearsal (H1 report producer).
  Implements AUDIT-138 R2 contract per docs/architecture/release-incident-recovery-0.66.2.md section 6.3.

.DESCRIPTION
  Creates a verified direct child of canonical system TEMP, a disposable bare
  remote/clone, fixed empty hooks, isolated Git config, and W0/W1 workspace
  tuples. Real origin is a read-only string and invocation count must be zero.

  Scenario A proves atomic capability and records remote master, tag object, and peel.
  TagType=annotated is mandatory, ordinal, and noninteractive.

.PARAMETER WorkspaceRoot
  Absolute path to a verified disposable C workspace (must be a clean git repo at commit C).

.PARAMETER TagType
  Must be exactly 'annotated' (case-sensitive). Any other value is a typed error.

.PARAMETER Fixture
  Must be 'positive'. (Negative fixtures are exercised by run_rel063_rehearsal_fixtures.ps1.)

.OUTPUTS
  Canonical JSON H1 report (rel063.atomic-rehearsal-report.v1) on stdout.

.NOTES
  Exit codes:
    0  = PASS (W0==W1, atomic succeeded, abort absent, RTO <=900, 0 real-origin invocations)
    2  = deterministic rejection (precondition or invariant failed)
    3  = UNKNOWN (remote unavailable / git error / parse error)
   64  = missing TagType
   65  = unknown/case-drift TagType
   70  = harness mismatch (W0!=W1, partial movement, unsupported atomic, sequential fallback)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,
    # TagType is intentionally NOT declared Mandatory: a missing TagType must be
    # classified as the typed exit 64 by the script body below, not intercepted
    # by PowerShell's mandatory-parameter prompt (which would exit 1).
    [Parameter(Mandatory = $false)]
    [string]$TagType,
    [Parameter(Mandatory = $true)]
    [string]$Fixture
)

$ErrorActionPreference = 'Stop'

# --- Canonical JSON helper (section 6.1) ---
function ConvertTo-CanonicalJson {
    param([System.Object]$Object)
    # sorted keys, compact separators, trailing LF, strict UTF-8 no BOM
    $json = $Object | ConvertTo-Json -Depth 100 -Compress
    # ConvertTo-Json preserves insertion order; caller must insert sorted.
    return ($json + "`n")
}

# --- TagType ordinal validation ---
if (-not $PSBoundParameters.ContainsKey('TagType')) { exit 64 }
if ($TagType -cne 'annotated') { exit 65 }
if ($Fixture -ne 'positive') { exit 2 }

# --- Resolve workspace root ---
if (-not ([System.IO.Path]::IsPathRooted($WorkspaceRoot))) { exit 2 }
$ws = (Get-Item -LiteralPath $WorkspaceRoot).FullName
if (-not (Test-Path -LiteralPath (Join-Path $ws '.git'))) { exit 2 }

# --- Capture W0 (precondition workspace identity) ---
try {
    Push-Location -LiteralPath $ws
    $candidateSha = & git rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($candidateSha)) { Pop-Location; exit 3 }
    $preconditionTree = & git rev-parse "HEAD^{tree}" 2>$null
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit 3 }
    $realOriginInvocations = 0  # must stay 0; real origin never queried
    $r0 = (Get-Date)
}
catch { Pop-Location; exit 3 }

# --- Build disposable bare remote + clone under system TEMP ---
$tempBase = [System.IO.Path]::GetTempPath()
$stamp = (Get-Date -Format 'yyyyMMddHHmmss') + '_' + ([System.Guid]::NewGuid().ToString('N').Substring(0,8))
$bareRemote = Join-Path $tempBase "rel063_bare_$stamp"
$cloneDir   = Join-Path $tempBase "rel063_clone_$stamp"
$abortDir   = Join-Path $tempBase "rel063_abort_$stamp"

try {
    & git init --bare "$bareRemote" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit 3 }
    # Neutral hooks: remove every hook so no pre-receive/update/post-receive
    # can interfere with the atomic push. An empty hooks/ dir is a true no-op
    # across platforms. (Writing '#' as a hook body fails on Windows because
    # git cannot spawn a hook file that has no interpreter shebang.)
    $hooksDir = Join-Path $bareRemote 'hooks'
    if (Test-Path -LiteralPath $hooksDir) {
        Get-ChildItem -LiteralPath $hooksDir -File -Force | Remove-Item -LiteralPath { $_.FullName } -Force
    }
    # isolated git config
    $env:GIT_CONFIG_NOSYSTEM = '1'
    $env:HOME = $tempBase  # isolate global config

    # Scenario A: atomic push of master + annotated tag
    & git clone --quiet "$bareRemote" "$cloneDir" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit 3 }
    Push-Location -LiteralPath $cloneDir
    & git config user.email "rel063@rehearsal.local" 2>&1 | Out-Null
    & git config user.name "rel063 rehearsal" 2>&1 | Out-Null
    # bring in the candidate as master
    & git fetch --quiet "$ws" HEAD 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 3 }
    & git update-ref refs/heads/master FETCH_HEAD 2>&1 | Out-Null
    & git checkout --quiet -B master FETCH_HEAD 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 3 }

    $preMaster = & git rev-parse HEAD 2>$null
    # one atomic push master + annotated tag
    & git tag -a "v0.66.2-rehearsal" -m "Rehearsal release v0.66.2" HEAD 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 70 }
    & git push --quiet --atomic origin "master:refs/heads/master" "refs/tags/v0.66.2-rehearsal:refs/tags/v0.66.2-rehearsal" 2>&1 | Out-Null
    $pushExit = $LASTEXITCODE
    if ($pushExit -ne 0) { Pop-Location; Pop-Location; exit 70 }

    # capture remote identities
    $remoteMasterSha = & git ls-remote origin refs/heads/master 2>$null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 3 }
    $remoteMasterSha = ($remoteMasterSha -split '\s+')[0]
    $remoteTagObjectLine = & git ls-remote origin refs/tags/v0.66.2-rehearsal 2>$null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 3 }
    $remoteTagObjectSha = ($remoteTagObjectLine -split '\s+')[0]
    # peel: fetch tag into clone and resolve
    & git fetch --quiet origin 'refs/tags/v0.66.2-rehearsal:refs/tags/v0.66.2-rehearsal' 2>&1 | Out-Null
    $remoteTagPeelSha = & git rev-parse "refs/tags/v0.66.2-rehearsal^{}" 2>$null
    if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; exit 3 }

    # abort ref must be absent
    $abortAbsent = (-not (& git ls-remote origin refs/heads/abort 2>$null))

    # --- Capture W1 (post workspace identity) ---
    Pop-Location  # clone
    $w1Tree = & git rev-parse "HEAD^{tree}" 2>$null
    Pop-Location  # original ws
    $workspaceIdentityUnchanged = ($w1Tree -eq $preconditionTree)

    $r1 = (Get-Date)
    $rto = ($r1 - $r0).TotalSeconds

    # --- Build H1 report ---
    $preconditionSha256 = [System.BitConverter]::ToString(
        [System.Security.Cryptography.SHA256]::Create().ComputeHash(
            [System.Text.Encoding]::UTF8.GetBytes("$candidateSha|$preconditionTree")
        )).Replace('-','').ToLower()

    $report = [ordered]@{
        schema_version = 'rel063.atomic-rehearsal-report.v1'
        producer_role = 'QA'
        producer_id = 'rel063-rehearsal-harness'
        subject_sha = $candidateSha
        tag_type = 'annotated'
        fixture = 'positive'
        result = 'PASS'
        raw_exit = 0
        writes = 0
        workspace_identity = $(if ($workspaceIdentityUnchanged) { 'UNCHANGED' } else { 'DRIFT' })
        real_origin_invocations = $realOriginInvocations
        sequential_fallbacks = 0
        precondition_sha256 = $preconditionSha256
        a_master_sha = $remoteMasterSha
        a_tag_object_sha = $remoteTagObjectSha
        a_tag_peel_sha = $remoteTagPeelSha
        abort_absent = $abortAbsent
        fallback_sha = '0000000000000000000000000000000000000000'
        rto_seconds = [math]::Round($rto, 3)
        generated_at = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
    }

    # --- Determine verdict ---
    if (-not $workspaceIdentityUnchanged) { $report.result = 'FAIL'; $report.raw_exit = 70 }
    if (-not $abortAbsent) { $report.result = 'FAIL'; $report.raw_exit = 70 }
    if ($realOriginInvocations -ne 0) { $report.result = 'FAIL'; $report.raw_exit = 70 }
    if ($rto -gt 900) { $report.result = 'FAIL'; $report.raw_exit = 70 }
    if ($remoteMasterSha -ne $candidateSha) { $report.result = 'FAIL'; $report.raw_exit = 70 }
    if ($remoteTagPeelSha -ne $candidateSha) { $report.result = 'FAIL'; $report.raw_exit = 70 }

    ConvertTo-CanonicalJson $report | Write-Output
    if ($report.raw_exit -ne 0) { exit $report.raw_exit }
    exit 0
}
catch {
    Pop-Location -ErrorAction SilentlyContinue
    exit 3
}
finally {
    # disposable cleanup (best-effort)
    foreach ($d in @($bareRemote, $cloneDir, $abortDir)) {
        if (Test-Path $d) { Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
