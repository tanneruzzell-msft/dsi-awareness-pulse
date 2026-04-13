# DSI Awareness Pulse - Refresh Script
# Run manually or schedule via Task Scheduler for weekly automation.
#
# Usage:
#   .\refresh-pulse.ps1              # Full collection + open dashboard
#   .\refresh-pulse.ps1 -SkipOpen    # Collect only, don't open browser
#   .\refresh-pulse.ps1 -Schedule    # Register a weekly scheduled task

param(
    [switch]$SkipOpen,
    [switch]$Schedule
)

$PulseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Python) {
        Write-Error "Python not found. Install Python 3.12+ first."
        exit 1
    }
}

if ($Schedule) {
    Write-Host "Registering weekly scheduled task..." -ForegroundColor Cyan

    $Action = New-ScheduledTaskAction -Execute $Python -Argument ('"' + $PulseDir + '\collector.py"') -WorkingDirectory $PulseDir
    $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "8:00AM"
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

    Register-ScheduledTask -TaskName "DSI-Awareness-Pulse" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly DSI awareness data collection" -Force

    Write-Host "Scheduled task registered (every Monday 8 AM)." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "  DSI Awareness Pulse - Refreshing..." -ForegroundColor Cyan
Write-Host ""

Push-Location $PulseDir
& $Python collector.py
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "  Refresh complete!" -ForegroundColor Green

    if (-not $SkipOpen) {
        $DashboardPath = Join-Path $PulseDir "pulse.html"
        Write-Host "  Opening dashboard..." -ForegroundColor DarkGray
        Start-Process $DashboardPath
    }
} else {
    Write-Host ""
    Write-Host ("  Collection failed (exit code " + $exitCode + ")") -ForegroundColor Red
}
