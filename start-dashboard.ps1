# DSI Awareness Pulse — Start Dashboard
# Launches the interactive dashboard server.
#
# Usage:
#   .\start-dashboard.ps1           # Start on http://localhost:5100
#   .\start-dashboard.ps1 -Port 8080  # Custom port

param([int]$Port = 5100)

$PulseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Python) {
        Write-Error "Python not found."
        exit 1
    }
}

Write-Host ""
Write-Host "  DSI Awareness Pulse" -ForegroundColor Cyan
Write-Host "  Starting dashboard at http://localhost:$Port" -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""

Start-Process "http://localhost:$Port"
& $Python "$PulseDir\server.py" --port $Port
