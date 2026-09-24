<#
Read-only action metadata for the two Stage acceptance runs from 2026-09-24.
Uses Microsoft's installed Power Apps PowerShell module and its existing SSO
session. Never follows input/output content links or returns their URIs/bodies.
OfflineActionsDirectory accepts saved metadata solely for projection testing.
#>
[CmdletBinding()]
param(
    [string]$OutputFile = (Join-Path $PSScriptRoot '..\.cred\stage-run-action-summary.json'),
    [string]$OfflineActionsDirectory
)
$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$flowId = '04d6229f-5ab8-f111-aaac-7ced8d6f317c'
$environmentName = 'Default-9f5c0ace-0780-4b48-8c24-b08bb5149210'
$runIds = @('08584113190102759476565110458CU01', '08584113190214236444505960035CU02')
$failurePhase = 'module-import'
$safeHttpStatus = $null

function Read-ProtectionFlags($link) {
    @($link.secureData.properties | Where-Object { $_ -in @('inputs', 'outputs') })
}

function Read-SafeToken($value) {
    if ($value -is [string] -and $value -match '^[A-Za-z0-9_.-]{1,128}$') { return $value }
    return $null
}

function Read-SafeTime($value) {
    if ([string]::IsNullOrWhiteSpace([string]$value)) { return $null }
    return ([DateTimeOffset]::Parse([string]$value)).ToUniversalTime().ToString('o')
}

try {
    if (-not $OfflineActionsDirectory) {
        Import-Module Microsoft.PowerApps.PowerShell -DisableNameChecking -WarningAction SilentlyContinue
    }
    $summaries = foreach ($runId in $runIds) {
        $failurePhase = 'read-action-metadata'
        $safeHttpStatus = $null
        if ($OfflineActionsDirectory) {
            $metadata = Get-Content -LiteralPath (Join-Path $OfflineActionsDirectory ($runId + '.json')) -Raw | ConvertFrom-Json
        }
        else {
            # Same Microsoft.ProcessSimple API family used by Get-FlowRun.
            # Only this fixed GET route is requested; content links are ignored.
            $route = 'https://{flowEndpoint}/providers/Microsoft.ProcessSimple/environments/' +
                $environmentName + '/flows/' + $flowId + '/runs/' + $runId + '/actions?api-version={apiVersion}'
            # Installed module 1.0.45 has an undefined $nextLinkuri in its
            # ThrowOnFailure pagination branch. The normal branch uses the
            # correct continuation URL. Validate its returned error explicitly.
            $metadata = InvokeApi -Method GET -Route $route -ApiVersion '2016-11-01' -Verbose:$false
        }
        if ($metadata.StatusCode -and [int]$metadata.StatusCode -ge 100 -and [int]$metadata.StatusCode -le 599) {
            $safeHttpStatus = [int]$metadata.StatusCode
        }
        if ($null -eq $metadata.value -or $metadata.error -or ($safeHttpStatus -and $safeHttpStatus -ge 400)) {
            throw 'Action metadata unavailable'
        }
        $failurePhase = 'project-action-metadata'
        $actions = foreach ($item in $metadata.value) {
            $properties = $item.properties
            [ordered]@{
                name = Read-SafeToken $item.name
                status = Read-SafeToken $properties.status
                code = Read-SafeToken $properties.code
                start_time = Read-SafeTime $properties.startTime
                end_time = Read-SafeTime $properties.endTime
                input_protection = @(Read-ProtectionFlags $properties.inputsLink)
                output_protection = @(Read-ProtectionFlags $properties.outputsLink)
                configuration_protection = @(Read-ProtectionFlags $properties.runtimeConfiguration)
            }
        }
        [ordered]@{ run_id = $runId; actions = @($actions) }
    }
    $result = [ordered]@{
        flow_id = $flowId
        environment = $environmentName
        source = $(if ($OfflineActionsDirectory) { 'offline-metadata-projection' } else { 'native-action-metadata' })
        verified_at = [DateTimeOffset]::UtcNow.ToString('o')
        includes_person_or_operation_payload = $false
        runs = @($summaries)
    }
    $failurePhase = 'save-metadata-summary'
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
    Write-Output ('Saved metadata-only summary for ' + $summaries.Count + ' fixed Stage runs.')
}
catch {
    # Fixed phase, enum category, CLR type and numeric HTTP status are safe.
    # Exception messages, stack traces and response bodies/links are not emitted.
    $diagnostic = [ordered]@{
        error = 'STAGE_METADATA_READBACK_FAILED'
        phase = $failurePhase
        category = [string]$_.CategoryInfo.Category
        exception_type = $_.Exception.GetType().FullName
        http_status = $safeHttpStatus
    }
    [Console]::Error.WriteLine(($diagnostic | ConvertTo-Json -Compress))
    exit 1
}
