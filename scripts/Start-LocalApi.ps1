param([string]$ConfigFile = $env:MILSTRIP_RUNTIME_CONFIG_FILE)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
$runtimeConfig = if ($ConfigFile) { [System.IO.Path]::GetFullPath($ConfigFile) } else { Join-Path $repoRoot '.cred/runtime.json' }
if (-not (Test-Path -LiteralPath $runtimeConfig)) {
    throw 'Run scripts/Configure-Runtime.ps1 first. Configure and test the database profiles.'
}
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8000 is occupied. Stop the identified prior development API before restarting; no process was terminated.'
}
$env:MILSTRIP_RUNTIME_CONFIG_FILE = $runtimeConfig
Push-Location $repoRoot
try {
    & $python -c "from api.runtime import load_runtime; load_runtime(); print('Runtime profiles loaded.')"
    if ($LASTEXITCODE -ne 0) { throw 'Runtime configuration or API credentials are invalid.' }
    & $python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'Local API stopped with an error.' }
} finally { Pop-Location }
