#Requires -Version 5.1
<#
.SYNOPSIS
  Start the FastAPI prediction backend on 127.0.0.1:8000.
.DESCRIPTION
  Uses the project .venv when present. Ensures a root .env exists (copied from
  .env.example). Pass -Reload for development auto-reload.
#>
[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
    Write-Warning "Project .venv not found; using '$Python' from PATH."
}

$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
    Write-Host "Created .env from .env.example"
}

$Artifacts = Join-Path $ProjectRoot "artifacts"
if (-not (Test-Path (Join-Path $Artifacts "current.json"))) {
    Write-Error "Missing artifacts/current.json. Train/export first: python scripts/train_export.py"
}

Write-Host "Starting FastAPI on http://${HostAddress}:${Port}"
Write-Host "OpenAPI docs: http://${HostAddress}:${Port}/docs"
Write-Host "Project root: $ProjectRoot"

$UvicornArgs = @(
    "-m", "uvicorn", "app.api.main:app",
    "--host", $HostAddress,
    "--port", "$Port"
)
if ($Reload) {
    $UvicornArgs += "--reload"
}

& $Python @UvicornArgs
exit $LASTEXITCODE
