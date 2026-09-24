param(
    [Parameter(Mandatory=$true)][ValidateSet('stage','prod')][string]$Environment,
    [switch]$ProvisionApplicationSchema,
    [string]$ConfirmTarget
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$arguments = @((Join-Path $PSScriptRoot 'initialize_application_database.py'), '--environment', $Environment)
if ($ProvisionApplicationSchema) { $arguments += '--provision-application-schema' }
if ($ConfirmTarget) { $arguments += @('--confirm-target', $ConfirmTarget) }
& (Join-Path $repoRoot '.venv/Scripts/python.exe') @arguments
if ($LASTEXITCODE -ne 0) { throw 'Application database initialization did not complete.' }
