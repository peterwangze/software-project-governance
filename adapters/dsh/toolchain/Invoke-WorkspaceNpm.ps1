param(
    [Parameter(Mandatory)][string]$Workspace,
    [Parameter(Mandatory)][string]$ProjectRoot,
    [Parameter(Mandatory)][string]$PythonExecutable,
    [Parameter(Mandatory)][string[]]$NpmArguments
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This workspace transport requires Windows PowerShell 7.' }

$workspacePath = (Resolve-Path -LiteralPath $Workspace).ProviderPath
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).ProviderPath
$relativeProject = [System.IO.Path]::GetRelativePath($workspacePath, $projectPath)
if ([System.IO.Path]::IsPathRooted($relativeProject) -or $relativeProject -eq '..' -or $relativeProject.StartsWith('..\')) {
    throw 'The npm project must be inside the selected workspace.'
}
$preload = (Join-Path $PSScriptRoot 'esbuild-stdio.cjs').Replace('\', '/')
$npm = Get-Command npm.cmd -CommandType Application -ErrorAction Stop
$names = 'NODE_OPTIONS', 'SPG_WORKSPACE_NPM_ROOT', 'SPG_WORKSPACE_NPM_WORKSPACE', 'SPG_WORKSPACE_NPM_PYTHON'
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

Push-Location -LiteralPath $projectPath
try {
    $env:SPG_WORKSPACE_NPM_ROOT = $projectPath
    $env:SPG_WORKSPACE_NPM_WORKSPACE = $workspacePath
    $env:SPG_WORKSPACE_NPM_PYTHON = $pythonPath
    $env:NODE_OPTIONS = ('{0} --require="{1}"' -f $previous['NODE_OPTIONS'], $preload).Trim()
    & $npm.Source @NpmArguments
    $result = $LASTEXITCODE
} finally {
    Pop-Location
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
exit $result
