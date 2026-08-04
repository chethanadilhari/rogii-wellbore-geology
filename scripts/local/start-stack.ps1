#Requires -Version 5.1
<#
.SYNOPSIS
  Open two new PowerShell windows: API (8000) + frontend (5173).
#>
[CmdletBinding()]
param(
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ApiScript = Join-Path $PSScriptRoot "start-api.ps1"
$FrontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

$ApiArgs = "-NoExit -ExecutionPolicy Bypass -File `"$ApiScript`""
if ($Reload) {
    $ApiArgs += " -Reload"
}

Write-Host "Launching API window..."
Start-Process powershell -ArgumentList $ApiArgs -WorkingDirectory $ProjectRoot

Start-Sleep -Seconds 1

Write-Host "Launching frontend window..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $FrontendScript
) -WorkingDirectory $ProjectRoot

Write-Host ""
Write-Host "Started local stack windows."
Write-Host "  API:       http://127.0.0.1:8000"
Write-Host "  Docs:      http://127.0.0.1:8000/docs"
Write-Host "  Frontend:  http://127.0.0.1:5173"
Write-Host ""
Write-Host "After both are up, run:  .\scripts\local\health-check.ps1"
