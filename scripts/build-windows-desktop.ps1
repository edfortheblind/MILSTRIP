[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "..\src\Milstrip.Desktop\Milstrip.Desktop.csproj"
$parityProject = Join-Path $PSScriptRoot "..\tools\Milstrip.Core.ParityTests\Milstrip.Core.ParityTests.csproj"

dotnet run --project $parityProject --configuration $Configuration
if ($LASTEXITCODE -ne 0) {
    throw "MILSTRIP parity tests failed with exit code $LASTEXITCODE."
}

if ($Publish) {
    dotnet publish $project --configuration $Configuration --runtime win-x64 --self-contained true
} else {
    dotnet build $project --configuration $Configuration
}

if ($LASTEXITCODE -ne 0) {
    throw "MILSTRIP desktop build failed with exit code $LASTEXITCODE."
}
