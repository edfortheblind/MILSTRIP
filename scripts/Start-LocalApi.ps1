$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
$credential = Join-Path $repoRoot '.cred/api-credential.json'
if (-not (Test-Path -LiteralPath $credential)) {
    throw 'Run scripts/Set-LocalApiCredential.ps1 privately first.'
}
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8000 is occupied. Stop the identified prior development API before restarting; no process was terminated.'
}
$env:MILSTRIP_API_CREDENTIAL_FILE = $credential
if (-not $env:MILSTRIP_DATABASE_URL) {
    $env:MILSTRIP_DATABASE_URL = 'postgresql://TabAdmin@localhost:5432/trav3pl-psqldb-stage'
}
Push-Location $repoRoot
try {
    & $python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'Local API stopped with an error.' }
} finally { Pop-Location }
