<#
.SYNOPSIS
    IVERI AI Agent — Sovereign PowerShell Launcher
.DESCRIPTION
    Launches IVERI AI Agent in air-gapped sovereign mode with hardware VRAM
    assessment, local document intelligence, and cyberpunk dashboard.
.EXAMPLE
    .\iveri.ps1
    .\iveri.ps1 chat
    .\iveri.ps1 web
    .\iveri.ps1 doctor
    .\iveri.ps1 demo
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Enforce UTF-8 output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Sovereign Environment Setup
if (-not $env:IVERI_HOME) {
    $env:IVERI_HOME = "$env:LOCALAPPDATA\iveri"
}
$env:HERMES_HOME = $env:IVERI_HOME
$env:IVERI_SOVEREIGN = "1"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Probe for Python interpreter
$PythonCandidates = @(
    "$ScriptDir\.venv\Scripts\python.exe",
    "$ScriptDir\venv\Scripts\python.exe",
    "C:\Python314\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe"
)

$PythonExe = $null
foreach ($candidate in $PythonCandidates) {
    if (Test-Path $candidate) {
        $PythonExe = $candidate
        break
    }
}

if (-not $PythonExe) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) {
        $PythonExe = $found.Source
    }
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Python 3.11+ executable not found. Please install Python." -ForegroundColor Red
    exit 1
}

# Subcommand dispatch
$FirstArg = if ($Arguments -and $Arguments.Count -gt 0) { $Arguments[0].ToLower() } else { "" }

switch ($FirstArg) {
    "" {
        Write-Host "[IVERI] Starting Sovereign Interactive REPL..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --sovereign chat
    }
    "chat" {
        $remaining = $Arguments[1..($Arguments.Count - 1)]
        Write-Host "[IVERI] Starting Sovereign Interactive REPL..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --sovereign chat $remaining
    }
    "web" {
        Write-Host "[IVERI] Starting Sovereign Web Dashboard on http://127.0.0.1:9119 ..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --sovereign dashboard --host 127.0.0.1 --port 9119
    }
    "dashboard" {
        Write-Host "[IVERI] Starting Sovereign Web Dashboard on http://127.0.0.1:9119 ..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --sovereign dashboard --host 127.0.0.1 --port 9119
    }
    "doctor" {
        Write-Host "[IVERI] Running Sovereign System Diagnostics..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\scripts\iveri_doctor.py"
    }
    "demo" {
        Write-Host "[IVERI] Running Golden Demo on Repository Knowledge Books..." -ForegroundColor Cyan
        & $PythonExe "$ScriptDir\scripts\test_golden_demo_books.py"
    }
    "help" {
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --help
    }
    default {
        & $PythonExe "$ScriptDir\hermes_cli\main.py" --sovereign $Arguments
    }
}
