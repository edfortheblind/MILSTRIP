param([string]$ConfigFile)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if ($ConfigFile) {
    $resolvedConfig = [IO.Path]::GetFullPath($ConfigFile)
} elseif ($env:MILSTRIP_RUNTIME_CONFIG_FILE) {
    $resolvedConfig = [IO.Path]::GetFullPath($env:MILSTRIP_RUNTIME_CONFIG_FILE)
} else {
    $resolvedConfig = Join-Path $repoRoot '.cred/runtime.json'
}
if ((Split-Path -Leaf (Split-Path -Parent $resolvedConfig)) -ne '.cred' -or
    [IO.Path]::GetExtension($resolvedConfig) -ne '.json') {
    throw 'Configuration must be a JSON file directly inside a .cred directory.'
}
$env:MILSTRIP_RUNTIME_CONFIG_FILE = $resolvedConfig
$privateDirectory = Split-Path -Parent $resolvedConfig
& (Join-Path $PSScriptRoot 'Protect-LocalApiDirectory.ps1') -Directory $privateDirectory
& (Join-Path $repoRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'configure_runtime.py')
if ($LASTEXITCODE -ne 0) { throw 'The configuration screen could not start. No runtime changes were activated.' }
