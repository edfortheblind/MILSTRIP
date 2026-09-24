param(
    [string]$ConfigFile = $env:MILSTRIP_RUNTIME_CONFIG_FILE,
    [string]$ControlFile = $env:MILSTRIP_CONTROL_FILE,
    [switch]$ValidateOnly
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
$runtimeConfig = if ($ConfigFile) { [System.IO.Path]::GetFullPath($ConfigFile) } else { Join-Path $repoRoot '.cred/runtime.json' }
$controlConfig = if ($ControlFile) { [System.IO.Path]::GetFullPath($ControlFile) } else { Join-Path $repoRoot '.cred/control.json' }
$env:MILSTRIP_RUNTIME_CONFIG_FILE = $runtimeConfig
$env:MILSTRIP_CONTROL_FILE = $controlConfig
Push-Location $repoRoot
try {
    & $python (Join-Path $PSScriptRoot 'runtime_host.py') check-startup
    if ($LASTEXITCODE -ne 0) { throw 'The selected runtime authority could not be validated.' }
    if ($ValidateOnly) { return }
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 8000 is occupied. Stop the identified prior development API before restarting; no process was terminated.'
    }
    & $python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'Local API stopped with an error.' }
} finally { Pop-Location }
