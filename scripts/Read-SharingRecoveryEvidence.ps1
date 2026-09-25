<#
Finite, read-only native metadata collection using Microsoft's existing SSO.
Run in a dedicated PowerShell process: the watchdog exits this process if an
authenticated request exceeds its deadline. No protected content links are read.
OfflineDirectory replays synthetic envelopes and can never produce native evidence.
OutputFile must be new. A failed read produces no successful evidence artifact.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$OutputFile,
    [string]$OfflineDirectory,
    [ValidateSet('Stage','Prod')][string]$PermissionProfile,
    [string]$PrincipalObjectId
)
$ErrorActionPreference = 'Stop'
$WarningPreference = 'SilentlyContinue'
$VerbosePreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$InformationPreference = 'SilentlyContinue'
$tenantId = '9f5c0ace-0780-4b48-8c24-b08bb5149210'
$environment = 'Default-9f5c0ace-0780-4b48-8c24-b08bb5149210'
$flowId = '04d6229f-5ab8-f111-aaac-7ced8d6f317c'
$runId = '08584113137259107903122568693CU13'
$flowRoute = 'https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/' + $environment + '/flows/' + $flowId + '/runs/' + $runId
$phase = 'validate-arguments'
$failureCode = 'COLLECTION_FAILED'
$httpStatus = $null
$requestCount = 0
$syntheticElapsed = 0
$timer = $null
$restModule = $null
$temporaryOutput = $null

function Refuse([string]$Code) {
    $script:failureCode = $Code
    throw 'SHARING_EVIDENCE_REFUSED'
}

function Read-Token($Value, [bool]$Required = $false) {
    if ($null -eq $Value -or $Value -eq '') {
        if ($Required) { Refuse 'MISSING_IDENTIFIER' }
        return $null
    }
    if ($Value -isnot [string] -or $Value -cnotmatch '^[A-Za-z0-9_.-]{1,128}$') { Refuse 'INVALID_IDENTIFIER' }
    return $Value
}

function Read-Guid($Value) {
    if ($Value -isnot [string] -or $Value -notmatch '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') { Refuse 'INVALID_IDENTITY' }
    return $Value.ToLowerInvariant()
}

function Read-Time($Value, [bool]$Required = $false) {
    if ($null -eq $Value -or $Value -eq '') {
        if ($Required) { Refuse 'MISSING_TIMESTAMP' }
        return $null
    }
    if ($Value -isnot [string] -or $Value -notmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|[+-]\d{2}:\d{2})$') { Refuse 'INVALID_TIMESTAMP' }
    try { return ([DateTimeOffset]::Parse($Value, [Globalization.CultureInfo]::InvariantCulture)).ToUniversalTime().ToString('o') }
    catch { Refuse 'INVALID_TIMESTAMP' }
}

function Read-Status($Value) {
    if ($Value -isnot [string] -or $Value -cnotin @('Succeeded','Failed','Running','Waiting','Skipped','TimedOut','Cancelled','Canceled','Aborted','Suspended')) { Refuse 'UNKNOWN_STATUS' }
    return $Value
}

function Read-IdentifierPath($Value) {
    if ($null -eq $Value -or $Value -eq '') { return $null }
    if ($Value -isnot [string] -or $Value -notmatch '^/[A-Za-z0-9_./-]{1,512}$' -or $Value.Contains('..')) { Refuse 'INVALID_RESOURCE_IDENTIFIER' }
    return $Value
}

function Read-Query([uri]$Uri) {
    $query = @{}
    foreach ($part in $Uri.Query.TrimStart('?').Split('&')) {
        if ($part -eq '') { continue }
        $pair = $part.Split([char[]]'=', 2)
        if ($pair.Count -ne 2) { Refuse 'INVALID_CONTINUATION' }
        $key = [Uri]::UnescapeDataString($pair[0])
        $value = [Uri]::UnescapeDataString($pair[1].Replace('+',' '))
        if ($query.ContainsKey($key) -or $key -cnotin @('api-version', '$filter', '$skiptoken', 'skiptokenSourceIndex', '$skip', '$top', '$expand')) { Refuse 'INVALID_CONTINUATION' }
        $query[$key] = $value
    }
    return $query
}

function Confirm-Route([string]$Value, [string]$FirstRoute) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value.Length -gt 16384 -or $Value -match '[\x00-\x20\\]') { Refuse 'INVALID_CONTINUATION' }
    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri)) { Refuse 'INVALID_CONTINUATION' }
    if ($Value.Split('?')[0] -match '(?i)%2f|%5c|%2e') { Refuse 'INVALID_CONTINUATION' }
    $first = [uri]$FirstRoute
    if ($uri.Scheme -cne 'https' -or $uri.Host -cne $first.Host -or $uri.Port -ne 443 -or $uri.UserInfo -or $uri.Fragment -or $uri.AbsolutePath -cne $first.AbsolutePath) { Refuse 'INVALID_CONTINUATION' }
    # Reject path dot-segment normalization before comparing canonical paths.
    if ($Value -match '/\.{1,2}(/|\?)') { Refuse 'INVALID_CONTINUATION' }
    $query = Read-Query $uri
    $original = Read-Query $first
    if ($query['api-version'] -cne $original['api-version']) { Refuse 'INVALID_CONTINUATION' }
    if ($original.ContainsKey('$filter')) {
        if ($query['$filter'] -cne $original['$filter']) { Refuse 'INVALID_CONTINUATION' }
    } elseif ($query.ContainsKey('$filter')) { Refuse 'INVALID_CONTINUATION' }
    if ($original.ContainsKey('$expand')) {
        if ($first.AbsolutePath -cne ([uri]$flowRoute).AbsolutePath -or $original['$expand'] -cne 'properties/flow' -or $query['$expand'] -cne 'properties/flow') { Refuse 'INVALID_CONTINUATION' }
    } elseif ($query.ContainsKey('$expand')) { Refuse 'INVALID_CONTINUATION' }
    if ($query.ContainsKey('skiptokenSourceIndex') -and $first.AbsolutePath -cne ([uri]($flowRoute + '/actions')).AbsolutePath) { Refuse 'INVALID_CONTINUATION' }
    foreach ($numberKey in @('$top','$skip','skiptokenSourceIndex')) {
        if ($query.ContainsKey($numberKey) -and $query[$numberKey] -notmatch '^\d{1,9}$') { Refuse 'INVALID_CONTINUATION' }
    }
    if ($query.ContainsKey('$skiptoken') -and [string]::IsNullOrWhiteSpace($query['$skiptoken'])) { Refuse 'INVALID_CONTINUATION' }
    return $uri.AbsoluteUri
}

function Read-Continuation($Body) {
    $plain = $Body.nextLink
    $odata = $Body.'@odata.nextLink'
    foreach ($value in @($plain,$odata)) {
        if ($null -ne $value -and $value -isnot [string]) { Refuse 'INVALID_CONTINUATION' }
    }
    if ($plain -and $odata -and $plain -cne $odata) { Refuse 'CONFLICTING_CONTINUATION' }
    if ($plain) { return $plain }
    if ($odata) { return $odata }
    return $null
}

function Arm-Deadline([int]$Milliseconds) {
    if (-not $OfflineDirectory) { [MilstripSharingReadDeadline]::Arm($Milliseconds) }
}

function Test-FreshMicrosoftSession([string]$Audience) {
    # Read expiry/identity metadata only. The Microsoft module retains tokens.
    # A missing or near-expiry audience must authenticate before the request
    # watchdog starts, so its internal Get-JwtToken cannot open a new sign-in
    # while preserving stale session identity within our bounded read.
    if (-not $global:currentSession -or $global:currentSession.loggedIn -ne $true -or
        $global:currentSession.endpoint -cne 'prod' -or $global:currentSession.tenantId -ne $tenantId) { return $false }
    try {
        $expiry = $global:currentSession.resourceTokens[$Audience].expiresOn
        return ($null -ne $expiry -and [DateTimeOffset]$expiry -gt [DateTimeOffset]::UtcNow.AddMinutes(3))
    } catch { return $false }
}

function Read-SinglePage([string]$Route, [string]$FirstRoute, [string]$FixtureName) {
    # A new request has no HTTP status until it returns. An earlier page's 200
    # must never be reported for a later transport/authentication exception.
    $script:httpStatus = $null
    $confirmed = Confirm-Route $Route $FirstRoute
    $elapsed = if ($OfflineDirectory) { $script:syntheticElapsed } else { $timer.ElapsedMilliseconds }
    $remaining = 120000 - $elapsed
    if ($remaining -le 0) { Refuse 'OVERALL_DEADLINE' }
    $script:requestCount++
    $requestLimit = [int][Math]::Min(30000, $remaining)
    Arm-Deadline $requestLimit
    if ($OfflineDirectory) {
        $envelope = Get-Content -LiteralPath (Join-Path $OfflineDirectory $FixtureName) -Raw | ConvertFrom-Json
        if ($envelope.elapsed_ms -isnot [int] -and $envelope.elapsed_ms -isnot [long]) { Refuse 'INVALID_FIXTURE' }
        if ($envelope.elapsed_ms -lt 0) { Refuse 'INVALID_FIXTURE' }
        if ($envelope.elapsed_ms -ge $requestLimit) { Refuse 'REQUEST_DEADLINE' }
        $script:syntheticElapsed += $envelope.elapsed_ms
        $script:httpStatus = $envelope.http_status
        if ($envelope.http_status -ne 200) { Refuse 'HTTP_READ_FAILED' }
        $body = $envelope.body
    } else {
        # Invoke-Request is the module's single HTTP request primitive. Its
        # authentication stays inside Microsoft code; we never copy a token.
        $response = & $restModule {
            param([string]$FixedRoute, [int]$TimeoutSeconds)
            $PSDefaultParameterValues = @{'Invoke-WebRequest:TimeoutSec'=$TimeoutSeconds; 'Invoke-WebRequest:MaximumRedirection'=0}
            Invoke-Request -Uri $FixedRoute -Method GET -ThrowOnFailure -Verbose:$false
        } $confirmed ([int][Math]::Max(1,[Math]::Floor($requestLimit / 1000)))
        $script:httpStatus = [int]$response.StatusCode
        if ($response.StatusCode -ne 200) { Refuse 'HTTP_READ_FAILED' }
        if ($response.Content -isnot [string] -or $response.Content.Length -gt 2097152) { Refuse 'RESPONSE_SIZE_OR_SHAPE' }
        $body = $response.Content | ConvertFrom-Json
    }
    $elapsed = if ($OfflineDirectory) { $script:syntheticElapsed } else { $timer.ElapsedMilliseconds }
    if ($elapsed -ge 120000) { Refuse 'OVERALL_DEADLINE' }
    Arm-Deadline ([int](120000 - $elapsed))
    if ($null -eq $body -or $body -isnot [pscustomobject] -or $body.error) { Refuse 'MALFORMED_RESPONSE' }
    return $body
}

function Project-Action($Row) {
    if ($Row -isnot [pscustomobject] -or $Row.properties -isnot [pscustomobject]) { Refuse 'MALFORMED_ACTION' }
    $start = Read-Time $Row.properties.startTime
    $end = Read-Time $Row.properties.endTime
    if ($start -and $end -and [DateTimeOffset]$start -gt [DateTimeOffset]$end) { Refuse 'INVALID_TIMESTAMP_ORDER' }
    return [ordered]@{name=Read-Token $Row.name $true; status=Read-Status $Row.properties.status; code=Read-Token $Row.properties.code; start_time=$start; end_time=$end}
}

function Project-Permission($Row) {
    if ($Row -isnot [pscustomobject] -or $Row.properties -isnot [pscustomobject] -or $Row.properties.principal -isnot [pscustomobject]) { Refuse 'MALFORMED_PERMISSION' }
    $principal = $Row.properties.principal
    $principalType = Read-Token $principal.type $true
    $role = Read-Token $Row.properties.roleName $true
    if ($principalType -cnotin @('User','Group','Tenant') -or $role -cnotin @('CanView','CanEdit','Owner')) { Refuse 'UNKNOWN_PERMISSION_SHAPE' }
    $assignmentId = Read-IdentifierPath $Row.id
    if (-not $assignmentId) { Refuse 'MISSING_IDENTIFIER' }
    $assignmentName = Read-Token $Row.name $true
    $expectedAssignmentId = '/providers/Microsoft.PowerApps/apps/' + $appId + '/permissions/' + $assignmentName
    if ($assignmentId -cne $expectedAssignmentId) { Refuse 'PERMISSION_RESOURCE_MISMATCH' }
    return [ordered]@{id=$assignmentId; name=$assignmentName; role=$role; principal_id=Read-Guid $principal.id; principal_type=$principalType; tenant_id=Read-Guid $principal.tenantId}
}

function Walk-DefinitionActions($Actions, [string[]]$Ancestors, [string[]]$Branches, [int]$Depth,
    [System.Collections.Generic.List[object]]$Inventory, [System.Collections.Generic.HashSet[string]]$SeenNames) {
    if ($Depth -gt 30) { Refuse 'DEFINITION_DEPTH_LIMIT' }
    if ($null -eq $Actions) { return }
    if ($Actions -isnot [pscustomobject]) { Refuse 'MALFORMED_DEFINITION_ACTIONS' }
    foreach ($entry in @($Actions.PSObject.Properties | Sort-Object Name)) {
        $name = Read-Token $entry.Name $true
        if (-not $SeenNames.Add($name)) { Refuse 'DUPLICATE_DEFINITION_ACTION' }
        if ($Inventory.Count -ge 999) { Refuse 'DEFINITION_ROW_LIMIT' }
        $action = $entry.Value
        if ($action -isnot [pscustomobject]) { Refuse 'MALFORMED_DEFINITION_ACTION' }
        $type = Read-Token $action.type $true
        $hostMetadata = $action.inputs.host
        $connection = Read-Token $hostMetadata.connectionName
        if ($null -ne $hostMetadata.connectionReferenceName) { $connection = Read-Token $hostMetadata.connectionReferenceName }
        $operation = Read-Token $hostMetadata.operationId
        $apiName = $null
        if ($hostMetadata.apiId) {
            if ($hostMetadata.apiId -isnot [string] -or $hostMetadata.apiId -cnotmatch '^/providers/Microsoft.PowerApps/apis/([A-Za-z0-9_.-]{1,128})$') { Refuse 'INVALID_DEFINITION_API' }
            $apiName = $Matches[1]
        }
        $brokerOperation = $null
        if ($connection -ceq 'broker' -and $operation -ceq 'InvokeBroker') {
            # Only this reviewed literal classification is read from the
            # definition. No payload_json, actor, parameter value, expression,
            # connection configuration or protected runtime payload is exported.
            $candidate = $action.inputs.parameters.'body/operation'
            if ($candidate -is [string] -and $candidate -cin @('SaveUserAccess','AcquireSharingLease','RecordSharingResult','ReserveManagementCall','RecordManagementCall')) {
                $brokerOperation = $candidate
            }
        }
        $Inventory.Add([ordered]@{name=$name;type=$type;connection=$connection;operation=$operation;
            broker_operation=$brokerOperation;api_name=$apiName;ancestors=@($Ancestors);ancestor_branches=@($Branches)})
        $parents = @($Ancestors) + @($name)
        Walk-DefinitionActions $action.actions $parents (@($Branches)+@($name+':actions')) ($Depth+1) $Inventory $SeenNames
        Walk-DefinitionActions $action.else.actions $parents (@($Branches)+@($name+':else')) ($Depth+1) $Inventory $SeenNames
        if ($null -ne $action.cases -and $action.cases -isnot [pscustomobject]) { Refuse 'MALFORMED_DEFINITION_BRANCH' }
        foreach ($caseEntry in @($action.cases.PSObject.Properties | Sort-Object Name)) {
            if ($null -ne $caseEntry) {
                $caseName = Read-Token $caseEntry.Name $true
                Walk-DefinitionActions $caseEntry.Value.actions $parents (@($Branches)+@($name+':case:'+ $caseName)) ($Depth+1) $Inventory $SeenNames
            }
        }
        Walk-DefinitionActions $action.default.actions $parents (@($Branches)+@($name+':default')) ($Depth+1) $Inventory $SeenNames
    }
}

function Project-RunDefinition($Flow) {
    if ($Flow -isnot [pscustomobject] -or $Flow.properties -isnot [pscustomobject]) { Refuse 'MISSING_RUN_ATTACHED_DEFINITION' }
    $snapshotId = Read-Guid $Flow.name
    if ($snapshotId -cne '4e2df4b9-e7fd-e446-63fa-678b9612ca1f') { Refuse 'HISTORICAL_SNAPSHOT_MISMATCH' }
    $expectedPath = '/providers/Microsoft.ProcessSimple/environments/' + $environment + '/flows/' + $snapshotId
    if ($Flow.id -cne $expectedPath) { Refuse 'SNAPSHOT_PATH_MISMATCH' }
    $logical = Read-Guid $Flow.properties.workflowEntityId
    $definition = $Flow.properties.definition
    if ($definition -isnot [pscustomobject] -or $definition.actions -isnot [pscustomobject]) { Refuse 'MISSING_RUN_ATTACHED_DEFINITION' }
    $metadataLogical = Read-Guid $definition.metadata.workflowEntityId
    if ($logical -cne $flowId -or $metadataLogical -cne $flowId) { Refuse 'SNAPSHOT_LOGICAL_FLOW_MISMATCH' }
    # Hash the complete native definition in memory, then discard its body.
    # This serialization is fixed for review and preview/apply comparison.
    $serialized = $definition | ConvertTo-Json -Depth 100 -Compress
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $digest = ([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($serialized)))).Replace('-','').ToLowerInvariant() }
    finally { $hasher.Dispose() }
    $inventory = New-Object 'System.Collections.Generic.List[object]'
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    Walk-DefinitionActions $definition.actions @() @() 0 $inventory $seen
    return [ordered]@{
        attached_flow_name=$snapshotId;attached_flow_id=$expectedPath;snapshot_identity_source='run.properties.flow.name'
        sha256=$digest;hash_serialization='powershell-converttojson-depth100-compress-utf8-no-bom'
        logical_flow_id=$logical;metadata_logical_flow_id=$metadataLogical;content_version=Read-Token $definition.contentVersion
        actions=@($inventory.ToArray())
    }
}

function Read-Collection([string]$FirstRoute, [string]$FixturePrefix, [string]$Kind) {
    $rows = New-Object 'System.Collections.Generic.List[object]'
    $seenRoutes = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $seenIds = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $seenPages = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $route = $FirstRoute
    for ($page = 1; $page -le 20; $page++) {
        $route = Confirm-Route $route $FirstRoute
        if (-not $seenRoutes.Add($route)) { Refuse 'CONTINUATION_LOOP' }
        $reply = Read-SinglePage $route $FirstRoute ($FixturePrefix + '-' + $page.ToString('000') + '.json')
        if ($reply.value -isnot [Array]) { Refuse 'MALFORMED_COLLECTION' }
        if ($rows.Count + $reply.value.Count -ge 1000) { Refuse 'ROW_LIMIT' }
        $pageIds = New-Object 'System.Collections.Generic.List[string]'
        foreach ($row in $reply.value) {
            $projected = if ($Kind -eq 'action') { Project-Action $row } else { Project-Permission $row }
            $identity = if ($Kind -eq 'action') { $projected.name } else { $projected.id }
            if (-not $seenIds.Add($identity)) { Refuse 'DUPLICATE_RESOURCE' }
            $pageIds.Add($identity)
            $rows.Add($projected)
        }
        # An empty page may advance once; repeated page content still fails
        # closed even when its continuation cursor changes.
        $pageIdentity = (@($pageIds | Sort-Object) -join '|')
        if (-not $seenPages.Add($pageIdentity)) { Refuse 'REPEATED_PAGE' }
        $next = Read-Continuation $reply
        if (-not $next) { return $rows.ToArray() }
        $route = Confirm-Route $next $FirstRoute
    }
    Refuse 'PAGE_LIMIT'
}

try {
    if (Test-Path -LiteralPath $OutputFile) { Refuse 'OUTPUT_EXISTS' }
    if ($PermissionProfile -and -not $PrincipalObjectId) { Refuse 'PRINCIPAL_REQUIRED' }
    if (-not $PermissionProfile -and $PrincipalObjectId) { Refuse 'UNEXPECTED_PRINCIPAL' }
    if ($PrincipalObjectId) { $PrincipalObjectId = Read-Guid $PrincipalObjectId }
    if ($OfflineDirectory) {
        $context = Get-Content -LiteralPath (Join-Path $OfflineDirectory 'context.json') -Raw | ConvertFrom-Json
        if ((Read-Guid $context.tenant_id) -ne $tenantId) { Refuse 'AUTH_TENANT_MISMATCH' }
        $actorId = Read-Guid $context.actor_object_id
    } else {
        $phase = 'interactive-authentication'
        Import-Module Microsoft.PowerApps.PowerShell -DisableNameChecking -WarningAction SilentlyContinue
        $audience = if ($PermissionProfile) { 'https://service.powerapps.com/' } else { 'https://service.flow.microsoft.com/' }
        if (-not (Test-FreshMicrosoftSession $audience)) {
            Add-PowerAppsAccount -Endpoint prod -Audience $audience -Verbose:$false | Out-Null
        }
        if ($global:currentSession.endpoint -cne 'prod') { Refuse 'AUTH_ENDPOINT_MISMATCH' }
        if ($global:currentSession.loggedIn -ne $true -or (Read-Guid $global:currentSession.tenantId) -ne $tenantId) { Refuse 'AUTH_TENANT_MISMATCH' }
        if (-not (Test-FreshMicrosoftSession $audience)) { Refuse 'AUTH_EXPIRY_TOO_SHORT' }
        $actorId = Read-Guid $global:currentSession.userId
        $restModule = Get-Module Microsoft.PowerApps.RestClientModule -All | Select-Object -First 1
        if (-not $restModule) { Refuse 'MODULE_SCOPE_UNAVAILABLE' }
        # A CLR timer fires independently of a blocked PowerShell pipeline.
        # Expiry prints a fixed diagnostic and kills only this worker process.
        Add-Type -TypeDefinition @'
using System;
using System.Threading;
public static class MilstripSharingReadDeadline {
    private static Timer timer;
    public static void Arm(int milliseconds) {
        if (timer == null) timer = new Timer(_ => {
            Console.Error.WriteLine("{\"error\":\"SHARING_EVIDENCE_READBACK_FAILED\",\"code\":\"WATCHDOG_DEADLINE\"}");
            Environment.Exit(1);
        }, null, milliseconds, Timeout.Infinite);
        else timer.Change(milliseconds, Timeout.Infinite);
    }
    public static void Stop() { if (timer != null) timer.Dispose(); }
}
'@
    }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    Arm-Deadline 120000
    $phase = 'metadata-read'
    $result = [ordered]@{
        source=$(if ($OfflineDirectory) {'offline-sharing-recovery-metadata'} else {'native-sharing-recovery-metadata'})
        schema_version=1; collected_at=$null; tenant_id=$tenantId; environment=$environment; actor_object_id=$actorId
    }
    if ($PermissionProfile) {
        $appId = if ($PermissionProfile -eq 'Stage') {'7f1b64d0-d51a-4ec8-84ad-2b18fe8c2f82'} else {'0aa02d8b-c7fa-42cc-87e8-6d287bd4c897'}
        $permissionsRoute = 'https://api.powerapps.com/providers/Microsoft.PowerApps/apps/' + $appId + '/permissions?api-version=2017-06-01&%24filter=' + [Uri]::EscapeDataString("environment eq '$environment'")
        $permissions = @(Read-Collection $permissionsRoute 'permissions' 'permission')
        $matches = @($permissions | Where-Object { $_.principal_id -eq $PrincipalObjectId -and $_.tenant_id -eq $tenantId -and $_.principal_type -ceq 'User' })
        if ($matches.Count -gt 1) { Refuse 'AMBIGUOUS_PERMISSION' }
        $result.source = if ($OfflineDirectory) {'offline-app-permission-metadata'} else {'native-app-permission-metadata'}
        $result.app_id=$appId
        $result.principal_object_id=$PrincipalObjectId
        $result.assignment_count=$permissions.Count
        $result.matches=$matches
        $result.complete=$true
        $result.can_view_verified=($matches.Count -eq 1 -and $matches[0].role -ceq 'CanView')
    } else {
        # The only permitted expansion is the definition attached to this
        # exact historical run; never substitute a current-flow definition.
        $runRoute = $flowRoute + '?api-version=2016-11-01&%24expand=properties%2Fflow'
        $run = Read-SinglePage $runRoute $runRoute 'run.json'
        if ($run.name -cne $runId -or $run.properties -isnot [pscustomobject] -or (Read-Continuation $run)) { Refuse 'RUN_BINDING_OR_COMPLETENESS' }
        if ($run.id -and $run.id -cne ([uri]$flowRoute).AbsolutePath) { Refuse 'RUN_BINDING_OR_COMPLETENESS' }
        $start = Read-Time $run.properties.startTime $true
        $end = Read-Time $run.properties.endTime
        if ($end -and [DateTimeOffset]$start -gt [DateTimeOffset]$end) { Refuse 'INVALID_TIMESTAMP_ORDER' }
        $result.flow_id=$flowId
        $result.run_id=$runId
        $result.run=[ordered]@{status=Read-Status $run.properties.status; start_time=$start; end_time=$end; workflow_id=Read-IdentifierPath $run.properties.workflow.id; workflow_name=Read-Token $run.properties.workflow.name; workflow_version=Read-Token $run.properties.workflow.version}
        $result.definition=Project-RunDefinition $run.properties.flow
        if (($result.run.workflow_id -and $result.run.workflow_id -cne $result.definition.attached_flow_id) -or
            ($result.run.workflow_name -and $result.run.workflow_name -cne $result.definition.attached_flow_name)) {
            Refuse 'RUN_WORKFLOW_REFERENCE_CONFLICT'
        }
        $result.run.workflow_id=$result.definition.attached_flow_id
        $result.run.workflow_name=$result.definition.attached_flow_name
        $result.actions=@(Read-Collection ($flowRoute + '/actions?api-version=2016-11-01') 'actions' 'action')
        $runtimeNames = @($result.actions | ForEach-Object { $_.name })
        $definitionNames = @($result.definition.actions | ForEach-Object { $_.name })
        if ($runtimeNames.Count -eq 0 -or $runtimeNames.Count -ne $definitionNames.Count -or
            @(Compare-Object $runtimeNames $definitionNames -CaseSensitive).Count -gt 0) { Refuse 'DEFINITION_ACTION_SET_MISMATCH' }
        $result.completeness=[ordered]@{run=$true; actions=$true; definition=$true}
        # The attached GUID is a native snapshot identity. It is never assigned
        # to workflow_version when that version field is absent in the API.
    }
    $result.collected_at=[DateTimeOffset]::UtcNow.ToString('o')
    $phase = 'save-evidence'
    $temporaryOutput = $OutputFile + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $temporaryOutput -Encoding UTF8
    [IO.File]::Move([IO.Path]::GetFullPath($temporaryOutput), [IO.Path]::GetFullPath($OutputFile))
    if (-not $OfflineDirectory) { [MilstripSharingReadDeadline]::Stop() }
    Write-Output 'Saved complete metadata projection; recovery eligibility requires separate validation.'
}
catch {
    $status = if ($httpStatus -is [int] -and $httpStatus -ge 100 -and $httpStatus -le 599) { $httpStatus } else { $null }
    [Console]::Error.WriteLine(([ordered]@{error='SHARING_EVIDENCE_READBACK_FAILED'; code=$failureCode; phase=$phase; http_status=$status; exception_type=$_.Exception.GetType().FullName; script_line=$_.InvocationInfo.ScriptLineNumber} | ConvertTo-Json -Compress))
    if ($temporaryOutput -and (Test-Path -LiteralPath $temporaryOutput)) { Remove-Item -LiteralPath $temporaryOutput -Force -ErrorAction SilentlyContinue }
    exit 1
}
