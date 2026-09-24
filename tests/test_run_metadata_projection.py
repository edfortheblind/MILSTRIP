"""The readback helper must never expose action content or signed content links."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


SHELL = shutil.which("powershell") or shutil.which("pwsh")
ROOT = Path(__file__).resolve().parents[1]
RUN_IDS = ("08584113190102759476565110458CU01", "08584113190214236444505960035CU02")


@pytest.mark.skipif(SHELL is None, reason="PowerShell is required for the host helper")
def test_native_metadata_projection_excludes_content_links_and_identity(tmp_path):
    sentinel = "NEVER_EXPORT_PRIVATE_ACTION_CONTENT"
    capture = {"value": [{"name": "Invoker_profile", "properties": {
        "status": "Succeeded", "code": "OK", "startTime": "2026-09-24T22:11:04Z",
        "endTime": "2026-09-24T22:11:05Z", "inputs": {"secret": sentinel},
        "outputs": {"body": {"displayName": sentinel}},
        "inputsLink": {"uri": "https://example.invalid/?sig=" + sentinel,
                       "secureData": {"properties": ["inputs"]}},
        "outputsLink": {"uri": "https://example.invalid/?sig=" + sentinel,
                        "secureData": {"properties": ["outputs"]}},
        "runtimeConfiguration": {"secureData": {"properties": ["inputs", "outputs"]}},
    }}]}
    for run_id in RUN_IDS:
        (tmp_path / (run_id + ".json")).write_text(json.dumps(capture), encoding="utf-8")
    output = tmp_path / "summary.json"
    result = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File",
        str(ROOT / "scripts/Read-StageBrokerRunMetadata.ps1"),
        "-OfflineActionsDirectory", str(tmp_path), "-OutputFile", str(output)],
        text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    text = output.read_text(encoding="utf-8-sig")
    assert sentinel not in text + result.stdout + result.stderr
    assert "https://" not in text and "displayName" not in text
    evidence = json.loads(text)
    assert evidence["source"] == "offline-metadata-projection"
    assert evidence["includes_person_or_operation_payload"] is False
    assert [run["run_id"] for run in evidence["runs"]] == list(RUN_IDS)
    for run in evidence["runs"]:
        row = run["actions"][0]
        assert row["name"] == "Invoker_profile" and row["status"] == "Succeeded"
        assert row["input_protection"] == ["inputs"]
        assert row["output_protection"] == ["outputs"]
        assert row["configuration_protection"] == ["inputs", "outputs"]


@pytest.mark.skipif(SHELL is None, reason="PowerShell is required for the host helper")
@pytest.mark.parametrize("bad_time", [False, True])
def test_failure_diagnostics_identify_phase_without_disclosing_response_or_content(tmp_path, bad_time):
    sentinel = "PRIVATE_DIAGNOSTIC_BODY_DO_NOT_PRINT"
    capture = ({"value": [{"name": "Invoker_profile", "properties": {"startTime": sentinel}}]}
               if bad_time else {"StatusCode": 403, "Error": {"Message": sentinel},
                                 "Message": sentinel, "Headers": {"Authorization": sentinel}})
    (tmp_path / (RUN_IDS[0] + ".json")).write_text(json.dumps(capture), encoding="utf-8")
    output = tmp_path / "summary.json"
    completed = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File",
        str(ROOT / "scripts/Read-StageBrokerRunMetadata.ps1"),
        "-OfflineActionsDirectory", str(tmp_path), "-OutputFile", str(output)],
        text=True, capture_output=True, timeout=30)
    assert completed.returncode == 1 and not output.exists()
    assert sentinel not in completed.stdout + completed.stderr
    diagnostic = json.loads(completed.stderr)
    assert diagnostic["error"] == "STAGE_METADATA_READBACK_FAILED"
    assert diagnostic["phase"] == ("project-action-metadata" if bad_time else "read-action-metadata")
    assert diagnostic["category"] and diagnostic["exception_type"]
    assert diagnostic["http_status"] == (None if bad_time else 403)


@pytest.mark.skipif(SHELL is None, reason="PowerShell is required for the host helper")
def test_installed_invokeapi_pagination_uses_the_safe_nonthrowing_branch_offline(tmp_path):
    # Load only the installed command's source. All authentication and HTTP
    # functions are replaced in a fresh local copy; no tenant call is possible.
    probe = tmp_path / "pagination-probe.ps1"
    probe.write_text(r'''
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -ListAvailable Microsoft.PowerApps.PowerShell)) { exit 77 }
Import-Module Microsoft.PowerApps.PowerShell -DisableNameChecking -WarningAction SilentlyContinue
$definition = (Get-Command InvokeApi).Definition
if ($definition -notmatch '\$nextLinkuri') { exit 78 }
function Test-PowerAppsAccount {}
function ReplaceMacro {
    param([Parameter(ValueFromPipeline=$true)][string]$InputObject, [string]$Macro, [AllowNull()][string]$Value)
    process { $InputObject.Replace($Macro, $Value) }
}
function Invoke-Request {
    param([Parameter(Mandatory=$true)][string]$Uri, [string]$Method, $Body, [switch]$ParseContent, [switch]$ThrowOnFailure)
    if ($Uri -notlike 'https://unit.invalid/*') { throw 'Unexpected test URI' }
    $script:calls++
    if ($script:calls -eq 1) { return [PSCustomObject]@{ value=@('first'); nextLink='https://unit.invalid/second' } }
    return [PSCustomObject]@{ value=@('second') }
}
Set-Item Function:\InvokeApi -Value ([ScriptBlock]::Create($definition))
$script:calls = 0
$failed = $false
try { InvokeApi -Method GET -Route 'https://unit.invalid/first' -ThrowOnFailure | Out-Null }
catch { $failed = $true }
if (-not $failed -or $script:calls -ne 1) { throw 'Expected installed throwing-pagination defect' }
$script:calls = 0
$result = InvokeApi -Method GET -Route 'https://unit.invalid/first'
if ($script:calls -ne 2 -or $result.value.Count -ne 2) { throw 'Normal pagination did not preserve both pages' }
Write-Output 'Offline pagination regression passed.'
''', encoding="utf-8")
    completed = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File", str(probe)],
                               text=True, capture_output=True, timeout=30)
    if completed.returncode in {77, 78}:
        pytest.skip("This regression targets the installed Power Apps 1.0.45 pagination defect")
    assert completed.returncode == 0, completed.stderr
    source = (ROOT / "scripts/Read-StageBrokerRunMetadata.ps1").read_text()
    actual_call = next(line for line in source.splitlines() if "$metadata = InvokeApi" in line)
    assert "-ThrowOnFailure" not in actual_call
