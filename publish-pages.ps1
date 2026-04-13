# Publish DSI Awareness Pulse to GitHub Pages
# Run this once to create the repo and enable Pages.
# After that, just run .\update-pages.ps1 to push new data.

param([switch]$Update)

$PulseDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $Update) {
    Write-Host ""
    Write-Host "  Publishing DSI Awareness Pulse to GitHub Pages..." -ForegroundColor Cyan
    Write-Host ""

    # Check gh auth
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  GitHub CLI not authenticated. Running login..." -ForegroundColor Yellow
        gh auth login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Authentication failed. Run 'gh auth login' manually." -ForegroundColor Red
            exit 1
        }
    }

    # Create private repo
    Write-Host "  Creating private GitHub repo..." -ForegroundColor DarkGray
    Push-Location $PulseDir
    gh repo create dsi-awareness-pulse --private --source=. --push
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Repo creation failed. It may already exist." -ForegroundColor Yellow
        git remote add origin (gh repo view --json url -q .url) 2>$null
        git push -u origin master 2>&1
    }

    # Enable GitHub Pages on main/master branch
    Write-Host "  Enabling GitHub Pages..." -ForegroundColor DarkGray
    gh api repos/{owner}/{repo}/pages -X POST -f "source[branch]=master" -f "source[path]=/" 2>&1

    $repoUrl = gh repo view --json url -q .url 2>$null
    $pagesUrl = $repoUrl -replace "github.com", "github.io" -replace "https://github.io/", "https://"
    # Construct pages URL
    $owner = gh api user -q .login 2>$null
    $pagesUrl = "https://$owner.github.io/dsi-awareness-pulse/"

    Pop-Location

    Write-Host ""
    Write-Host "  Done! Your dashboard will be live at:" -ForegroundColor Green
    Write-Host "  $pagesUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  (Pages can take 1-2 minutes to deploy on first push)" -ForegroundColor DarkGray
    Write-Host "  To update after a refresh: .\publish-pages.ps1 -Update" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "  Updating GitHub Pages..." -ForegroundColor Cyan

    Push-Location $PulseDir

    # Regenerate dashboard
    $Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (-not (Test-Path $Python)) { $Python = "python" }
    & $Python collector.py

    # Copy latest pulse.html to index.html
    Copy-Item pulse.html index.html -Force

    git add index.html pulse.html dashboard_data.json
    git commit -m "Weekly pulse update $(Get-Date -Format 'yyyy-MM-dd')"
    git push

    Pop-Location

    Write-Host ""
    Write-Host "  Pushed! Dashboard will update in ~1 minute." -ForegroundColor Green
}
