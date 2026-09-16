[CmdletBinding()]
param(
    [switch]$Continuous,
    [switch]$PlanActive
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$config = Join-Path $projectRoot 'config.local.json'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing: $python"
}
if (-not (Test-Path -LiteralPath $config)) {
    throw "Local configuration is missing: $config"
}

$env:HA_URL = Read-Host 'Home Assistant URL (for example, http://homeassistant.local:8123)'
if ([string]::IsNullOrWhiteSpace($env:HA_URL)) {
    throw 'No Home Assistant URL was supplied.'
}
$env:HA_TOKEN = Read-Host 'Paste Home Assistant token, then press Enter' -MaskInput
if ([string]::IsNullOrWhiteSpace($env:HA_TOKEN)) {
    throw 'No Home Assistant token was supplied.'
}

Write-Host 'Starting read-only shadow controller. It will not write to Nest.' -ForegroundColor Cyan
$arguments = @('-m', 'solar_ac', '--config', $config)
if ($PlanActive) {
    $arguments += '--plan-active'
}
if (-not $Continuous) {
    $arguments += '--once'
}
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
