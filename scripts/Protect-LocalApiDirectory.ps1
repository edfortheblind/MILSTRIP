param([Parameter(Mandatory=$true)][string]$Directory)
$ErrorActionPreference = 'Stop'
[void](New-Item -ItemType Directory -Force -Path $Directory)
if ((Get-Item -LiteralPath $Directory).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    # OneDrive cloud placeholders are reparse points without redirecting paths.
    # Allow only CLOUD/CLOUD_1..F tags; reject junctions, symlinks and unknown tags.
    $reparseInfo = & fsutil.exe reparsepoint query $Directory 2>$null
    $tagMatch = [regex]::Match(($reparseInfo -join "`n"), '0x([0-9a-fA-F]{8})')
    if ($LASTEXITCODE -ne 0 -or -not $tagMatch.Success) { throw 'Cannot verify private folder reparse type.' }
    $tag = [Convert]::ToUInt32($tagMatch.Groups[1].Value, 16)
    if (($tag -band [Convert]::ToUInt32('FFFF0FFF', 16)) -ne [Convert]::ToUInt32('9000001A', 16)) {
        throw 'Private credential storage must not be a link or junction.'
    }
}
$ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
# Change only the DACL. Reapplying a fresh security descriptor through Set-Acl
# can request SeSecurityPrivilege; owner/SACL changes are unnecessary here.
& icacls.exe $Directory /inheritance:r /grant:r "*$($ownerSid):(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict private credential directory access.' }
$acl = Get-Acl -LiteralPath $Directory
$rules = @($acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
if (-not $acl.AreAccessRulesProtected -or $rules.Count -ne 1 -or
    $rules[0].IdentityReference.Value -ne $ownerSid -or
    $rules[0].AccessControlType -ne 'Allow' -or
    $rules[0].FileSystemRights -ne 'FullControl') {
    throw 'Private directory has unexpected explicit permissions; no credential will be written.'
}
