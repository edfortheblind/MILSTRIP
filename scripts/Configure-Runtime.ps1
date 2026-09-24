param([string]$ConfigFile, [string]$ControlFile = $env:MILSTRIP_CONTROL_FILE, [switch]$ValidateOnly)
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
$env:MILSTRIP_CONTROL_FILE = if ($ControlFile) { [IO.Path]::GetFullPath($ControlFile) } else { Join-Path $repoRoot '.cred/control.json' }
& (Join-Path $repoRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'runtime_host.py') check-legacy-editor
if ($LASTEXITCODE -ne 0) { throw 'Host configuration is closed or unavailable. Use Database configuration in the MILSTRIP app after control activation.' }
if ($ValidateOnly) { return }
$privateDirectory = Split-Path -Parent $resolvedConfig
& (Join-Path $PSScriptRoot 'Protect-LocalApiDirectory.ps1') -Directory $privateDirectory
& (Join-Path $repoRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'configure_runtime.py')
if ($LASTEXITCODE -ne 0) { throw 'The configuration screen could not start. No runtime changes were activated.' }
