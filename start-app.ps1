#Requires -Version 5.1
<#
.SYNOPSIS
  Start the Staples Image Generation POC (FastAPI + uvicorn).

.DESCRIPTION
  - Moves to the project root
  - Uses .venv Python/uvicorn
  - Stops any existing listener on the chosen port
  - Starts uvicorn with --reload
  - Optionally opens the UI in the default browser

.PARAMETER Port
  Override APP_PORT from .env (default 8000).

.PARAMETER HostAddress
  Bind address (default 127.0.0.1).

.PARAMETER NoBrowser
  Do not open the browser automatically.

.EXAMPLE
  .\start-app.ps1

.EXAMPLE
  .\start-app.ps1 -Port 8001
#>
[CmdletBinding()]
param(
    [int]$Port = 0,
    [string]$HostAddress = "127.0.0.1",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Info([string]$Message) {
    Write-Host "[staples] $Message" -ForegroundColor Cyan
}

function Write-Warn([string]$Message) {
    Write-Host "[staples] $Message" -ForegroundColor Yellow
}

function Get-EnvValue([string]$Key, [string]$Default = "") {
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) { return $Default }
    $line = Get-Content $envFile | Where-Object { $_ -match ("^\s*" + [regex]::Escape($Key) + "\s*=") } | Select-Object -First 1
    if (-not $line) { return $Default }
    $value = ($line -split "=", 2)[1].Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Test-PortFree([int]$TestPort) {
    $inUse = Get-NetTCPConnection -LocalPort $TestPort -State Listen -ErrorAction SilentlyContinue
    return -not $inUse
}

function Stop-PortListener([int]$TargetPort) {
    $conns = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $procId = $c.OwningProcess
        if ($procId -and $procId -ne 0) {
            try {
                $p = Get-Process -Id $procId -ErrorAction Stop
                Write-Info ("Stopping existing process on port {0} (PID {1} - {2})" -f $TargetPort, $procId, $p.ProcessName)
                Stop-Process -Id $procId -Force -ErrorAction Stop
            } catch {
                Write-Warn ("Could not stop PID {0}: {1}" -f $procId, $_.Exception.Message)
            }
        }
    }
    Start-Sleep -Seconds 1
}

# --- Resolve Python / venv ---------------------------------------------------
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$venvUvicorn = Join-Path $ProjectRoot ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found at .venv. Create it with: python -m venv .venv ; .\.venv\Scripts\pip.exe install -r requirements-local.txt"
}

if (-not (Test-Path $venvUvicorn)) {
    Write-Warn "uvicorn not found in .venv - installing requirements..."
    & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements-local.txt")
}

# --- Resolve host / port -----------------------------------------------------
if ($Port -le 0) {
    $Port = [int](Get-EnvValue "APP_PORT" "8000")
}
$hostFromEnv = Get-EnvValue "APP_HOST" ""
if ($hostFromEnv) { $HostAddress = $hostFromEnv }

$mockMode = Get-EnvValue "MOCK_MODE" "true"
Write-Info "Project : $ProjectRoot"
Write-Info "MOCK_MODE=$mockMode"
Write-Info "Binding : http://${HostAddress}:${Port}"

# Prefer requested port; if still blocked after kill, fall back
$candidatePorts = @($Port, 8001, 8080, 8765) | Select-Object -Unique
$selectedPort = $null
foreach ($p in $candidatePorts) {
    Stop-PortListener -TargetPort $p
    if (Test-PortFree -TestPort $p) {
        $selectedPort = $p
        break
    }
    Write-Warn "Port $p still in use after stop attempt."
}

if (-not $selectedPort) {
    throw "No free port among $($candidatePorts -join ', '). Pass -Port <n> or free a port."
}

if ($selectedPort -ne $Port) {
    Write-Warn "Port $Port unavailable - using $selectedPort instead."
}
$Port = $selectedPort

$url = "http://${HostAddress}:${Port}"

# Also stop stray uvicorn processes for this app
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -like "*uvicorn*") -and
        ($_.CommandLine -like "*app.main:app*")
    } |
    ForEach-Object {
        Write-Info ("Stopping leftover uvicorn PID {0}" -f $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Start-Sleep -Milliseconds 500

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($OpenUrl)
        Start-Sleep -Seconds 3
        Start-Process $OpenUrl
    } -ArgumentList $url | Out-Null
}

Write-Info "Starting uvicorn (Ctrl+C to stop)..."
Write-Info "Open: $url"
Write-Host ""

& $venvUvicorn "app.main:app" --reload --host $HostAddress --port $Port
