# DSI Awareness Pulse — Start Dashboard
# Launches the interactive dashboard server.
#
# Usage:
#   .\start-dashboard.ps1              # Local only (http://localhost:5100)
#   .\start-dashboard.ps1 -Share       # Share with team on your network
#   .\start-dashboard.ps1 -Port 8080   # Custom port

param(
    [int]$Port = 5100,
    [switch]$Share
)

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

if ($Share) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169" } | Select-Object -First 1).IPAddress
    Write-Host "  Share this with your team:" -ForegroundColor DarkGray
    Write-Host "  http://${ip}:${Port}" -ForegroundColor Green
    Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
    Write-Host ""
    Start-Process "http://localhost:$Port"
    & $Python "$PulseDir\server.py" --port $Port --share
} else {
    Write-Host "  http://localhost:$Port" -ForegroundColor DarkGray
    Write-Host "  Tip: use -Share to let teammates access" -ForegroundColor DarkGray
    Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
    Write-Host ""
    Start-Process "http://localhost:$Port"
    & $Python "$PulseDir\server.py" --port $Port
}
