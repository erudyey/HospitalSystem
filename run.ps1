<#
.SYNOPSIS
    Task runner script for HospitalSystem development, testing, and packaging.
.EXAMPLE
    .\run.ps1 dev
    .\run.ps1 desktop
    .\run.ps1 test
    .\run.ps1 format
    .\run.ps1 package
#>
param (
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("dev", "desktop", "test", "format", "package", "setup", "test-package")]
    [string]$Command,

    [Parameter(Mandatory = $false)]
    [switch]$Quick,

    [Parameter(Mandatory = $false)]
    [switch]$Demo
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvPytest = Join-Path $RepoRoot ".venv\Scripts\pytest.exe"
$VenvRuff = Join-Path $RepoRoot ".venv\Scripts\ruff.exe"

switch ($Command) {
    "setup" {
        Write-Host "Setting up project dependencies..." -ForegroundColor Cyan
        if (-not (Test-Path $VenvPython)) {
            uv venv .venv
        }
        uv pip install --python $VenvPython django waitress pywebview whitenoise pytest pytest-django ruff django-stubs pyinstaller basedpyright
        Push-Location "$RepoRoot\frontend"
        try {
            deno install
        } finally {
            Pop-Location
        }
        Write-Host "Setup complete!" -ForegroundColor Green
    }

    "dev" {
        Write-Host "Starting development servers (Vite + Django)..." -ForegroundColor Cyan
        $env:DJANGO_SETTINGS_MODULE = "backend.config.settings"
        $env:DEBUG = "True"
        
        # Migrate local dev DB
        & $VenvPython "$RepoRoot\backend\manage.py" migrate

        # Run Vite and Django concurrently
        $frontendJob = Start-Job -ScriptBlock {
            param($path)
            Set-Location $path
            deno task dev
        } -ArgumentList "$RepoRoot\frontend"

        try {
            & $VenvPython "$RepoRoot\backend\manage.py" runserver 127.0.0.1:8000
        } finally {
            Stop-Job $frontendJob
            Remove-Job $frontendJob
        }
    }

    "desktop" {
        Write-Host "Launching HospitalSystem Desktop..." -ForegroundColor Cyan
        # Ensure frontend is built if dist does not exist
        if (-not (Test-Path "$RepoRoot\frontend\dist\index.html")) {
            Write-Host "Building frontend first..." -ForegroundColor Yellow
            Push-Location "$RepoRoot\frontend"
            try {
                deno task build
            } finally {
                Pop-Location
            }
        }
        $desktopArgs = @()
        if ($Demo) {
            $desktopArgs += "--demo"
        }
        & $VenvPython "$RepoRoot\desktop\launcher.py" @desktopArgs
    }

    "test" {
        if (-not $Quick) {
            Write-Host "Running basedpyright strict type checks..." -ForegroundColor Cyan
            & $VenvPython -m basedpyright
            Write-Host ""
        }
        Write-Host "Running backend automated test suite..." -ForegroundColor Cyan
        $env:TESTING = "True"
        & $VenvPytest "$RepoRoot\backend\tests"
    }

    "test-package" {
        Write-Host "Running automated standalone bundle verification..." -ForegroundColor Cyan
        & $VenvPython "$RepoRoot\desktop\verify_bundle.py"
    }

    "format" {
        Write-Host "Running Ruff linter and formatter..." -ForegroundColor Cyan
        & $VenvRuff check --fix "$RepoRoot\backend" "$RepoRoot\desktop"
        & $VenvRuff format "$RepoRoot\backend" "$RepoRoot\desktop"
        Push-Location "$RepoRoot\frontend"
        try {
            deno fmt
        } finally {
            Pop-Location
        }
    }

    "package" {
        Write-Host "Packaging HospitalSystem as Windows .exe..." -ForegroundColor Cyan
        $packageArgs = @()
        if ($Quick) {
            $packageArgs += "--quick"
        }
        & $VenvPython "$RepoRoot\package.py" @packageArgs
        Write-Host "`nRunning automated standalone verification..." -ForegroundColor Cyan
        & $VenvPython "$RepoRoot\desktop\verify_bundle.py"
    }
}
