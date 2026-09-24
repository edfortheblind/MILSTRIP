[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Claude Furry','Mike Thompson')]
    [string]$Owner,
    [string]$ControlFile
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$acceptScript = Join-Path $PSScriptRoot 'accept_bootstrap_owner.py'
$captureArguments = @($acceptScript, '--owner', $Owner, '--capture-spec')
if ($ControlFile) { $captureArguments += @('--control-file', $ControlFile) }
$specJson = & $pythonPath @captureArguments
if ($LASTEXITCODE -ne 0) { throw 'Protected Owner capture specification was refused.' }
$spec = $specJson | ConvertFrom-Json

# These commands only read the two existing apps and two broker flows. They do
# not grant sharing, change roles, start flows, or activate application access.
Import-Module Microsoft.PowerApps.PowerShell -WarningAction SilentlyContinue
Add-PowerAppsAccount -Endpoint prod | Out-Null
$appEvidence = @()
$flowEvidence = @()
$flowReads = 0
foreach ($profile in @('stage','prod')) {
    $resource = $spec.resources.$profile
    $roles = @(Get-PowerAppRoleAssignment -AppName $resource.app_id -EnvironmentName $spec.environment_name)
    $matches = @($roles | Where-Object { $_.Internal.properties.principal.id -eq $spec.object_id })
    if ($matches.Count -ne 1) { throw 'Expected one native app permission for the selected protected Owner.' }
    $native = $matches[0].Internal
    $properties = $native.properties
    if ($properties.roleName -ne 'CanView' -or $properties.principal.type -ne 'User' -or $properties.principal.tenantId -ne $spec.tenant_id) {
        throw 'The protected Owner requires ordinary CanView app access in the verified tenant.'
    }
    $appEvidence += [PSCustomObject]@{
        app_id=$resource.app_id; environment_name=$spec.environment_name; verified_at=[DateTime]::UtcNow.ToString('o')
        assignment=[PSCustomObject]@{
            id=$native.id; name=$native.name; type=$native.type
            properties=[PSCustomObject]@{
                roleName=$properties.roleName
                principal=[PSCustomObject]@{ id=$properties.principal.id; type=$properties.principal.type; tenantId=$properties.principal.tenantId }
            }
        }
    }
    if ($flowReads -gt 0) { Start-Sleep -Seconds 13 }
    $route = 'https://{flowEndpoint}/providers/Microsoft.ProcessSimple/environments/' + $spec.environment_name + '/flows/' + $resource.flow_id + '/users?api-version={apiVersion}'
    $reply = InvokeApi -Method GET -Route $route -ApiVersion '2016-11-01'
    $flowReads++
    if ($reply.error -or $reply.nextLink -or $reply.'@odata.nextLink' -or @($reply.value).Count -ge 1000) {
        throw 'Flow run-only permission readback failed or was incomplete.'
    }
    $users = @($reply.value | Where-Object { $_.properties.principal.id -eq $spec.object_id })
    if ($users.Count -ne 1) { throw 'Expected one native run-only entry for the selected protected Owner.' }
    $user = $users[0]
    $flowEvidence += [PSCustomObject]@{
        flow_id=$resource.flow_id; environment_name=$spec.environment_name; verified_at=[DateTime]::UtcNow.ToString('o'); next_link=$null
        users=@([PSCustomObject]@{
            id=$user.id; name=$user.name; type=$user.type
            properties=[PSCustomObject]@{
                permissionType=$user.properties.permissionType
                principal=[PSCustomObject]@{ id=$user.properties.principal.id; type=$user.properties.principal.type; tenantId=$user.properties.principal.tenantId }
            }
        })
    }
}
[IO.File]::WriteAllText($spec.app_capture, ($appEvidence | ConvertTo-Json -Depth 10))
[IO.File]::WriteAllText($spec.flow_capture, ($flowEvidence | ConvertTo-Json -Depth 10))
Write-Output ('Captured four native permission records for ' + $Owner + '. Application membership remains unchanged.')
