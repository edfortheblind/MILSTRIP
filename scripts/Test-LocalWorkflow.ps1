$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
# A generated short-lived identity avoids reading the owner's plaintext password.
& (Join-Path $PSScriptRoot 'Protect-LocalApiDirectory.ps1') -Directory (Join-Path $repoRoot '.cred')
& (Join-Path $repoRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_local_api_http.py') --workflow
if ($LASTEXITCODE -ne 0) { throw 'Standalone workflow verification failed; see the sanitized failure above.' }
