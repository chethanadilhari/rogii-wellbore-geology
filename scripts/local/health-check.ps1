#Requires -Version 5.1
<#
.SYNOPSIS
  Local health check for API (+ optional frontend).
.DESCRIPTION
  Exits 0 only when /health reports healthy with model_loaded=true.
  Optionally checks /models/current and the Vite frontend URL.
#>
[CmdletBinding()]
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:5173",
    [switch]$SkipFrontend,
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = "Stop"
$failed = $false

function Write-Check([string]$Name, [bool]$Ok, [string]$Detail = "") {
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    if ($Detail) {
        Write-Host ("[{0}] {1}: {2}" -f $mark, $Name, $Detail)
    } else {
        Write-Host ("[{0}] {1}" -f $mark, $Name)
    }
    if (-not $Ok) { $script:failed = $true }
}

Write-Host "Local health check"
Write-Host "  API:      $ApiBaseUrl"
if (-not $SkipFrontend) {
    Write-Host "  Frontend: $FrontendUrl"
}
Write-Host ""

# --- /health ---
try {
    $health = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -TimeoutSec $TimeoutSec
    $ok = ($health.status -eq "healthy") -and ($health.model_loaded -eq $true)
    Write-Check "GET /health" $ok (
        "status=$($health.status) model_loaded=$($health.model_loaded) " +
        "version=$($health.model_version) recipe=$($health.selected_model)"
    )
} catch {
    Write-Check "GET /health" $false $_.Exception.Message
}

# --- /models/current ---
try {
    $model = Invoke-RestMethod -Uri "$ApiBaseUrl/models/current" -TimeoutSec $TimeoutSec
    $ok = [bool]$model.model_version
    Write-Check "GET /models/current" $ok (
        "version=$($model.model_version) selected=$($model.selected_model)"
    )
} catch {
    Write-Check "GET /models/current" $false $_.Exception.Message
}

# --- frontend ---
if (-not $SkipFrontend) {
    try {
        $resp = Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec $TimeoutSec
        Write-Check "GET frontend" ($resp.StatusCode -eq 200) "HTTP $($resp.StatusCode)"
    } catch {
        Write-Check "GET frontend" $false $_.Exception.Message
    }
}

Write-Host ""
if ($failed) {
    Write-Host "Health check FAILED."
    exit 1
}
Write-Host "Health check OK."
exit 0
