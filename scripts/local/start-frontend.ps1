#Requires -Version 5.1
<#
.SYNOPSIS
  Start the React/Vite frontend on 127.0.0.1:5173.
#>
[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$FrontendRoot = Join-Path $ProjectRoot "app\frontend"
Set-Location $FrontendRoot

if (-not (Test-Path (Join-Path $FrontendRoot "node_modules"))) {
    Write-Host "Installing frontend dependencies (npm install)..."
    npm install
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$EnvFile = Join-Path $FrontendRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $FrontendRoot ".env.example") $EnvFile
    Write-Host "Created app/frontend/.env from .env.example"
}

Write-Host "Starting frontend on http://${HostAddress}:${Port}"
Write-Host "Expects API at VITE_API_BASE_URL (default http://127.0.0.1:8000)"

npm run dev -- --host $HostAddress --port $Port
exit $LASTEXITCODE
