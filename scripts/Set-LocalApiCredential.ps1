$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$privateDirectory = Join-Path $repoRoot '.cred'
& (Join-Path $PSScriptRoot 'Protect-LocalApiDirectory.ps1') -Directory $privateDirectory
# Use the ignored, access-restricted project credential folder.
$env:MILSTRIP_API_CREDENTIAL_FILE = Join-Path $privateDirectory 'api-credential.json'
& (Join-Path $repoRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'configure_local_api.py')
if ($LASTEXITCODE -ne 0) { Write-Host 'Credential setup was not completed. Run this script again; no API password was saved.'; exit 1 }
