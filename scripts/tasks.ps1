param(
    [ValidateSet("setup", "test", "run", "bootstrap", "build-exe", "help")]
    [string]$Task = "help",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs = @()
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$bootstrapScript = Join-Path $projectRoot "scripts\bootstrap.ps1"
$buildExeScript = Join-Path $projectRoot "scripts\build-exe.ps1"

function Ensure-Bootstrap {
    if (-not (Test-Path $venvPython)) {
        Write-Host "No .venv found. Running bootstrap..."
        & $bootstrapScript
    }
}

function Show-Usage {
    Write-Host "DataCasketShred task runner"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\tasks.ps1 -Task <task> [options] [-- <app-args>]"
    Write-Host ""
    Write-Host "Available tasks:"
    Write-Host "  bootstrap  Create .venv and install dependencies"
    Write-Host "  setup      Ensure bootstrap and (re)install dependencies"
    Write-Host "  test       Ensure bootstrap and run pytest"
    Write-Host "  run        Ensure bootstrap and start the app"
    Write-Host "  build-exe  Build standalone executable with PyInstaller"
    Write-Host "  help       Show this help"
    Write-Host ""
    Write-Host "Run options:"
    Write-Host "  -- <app-args>    Forward arbitrary args to app.main"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\tasks.ps1 -Task run -- --checkshred"
    Write-Host "  .\scripts\tasks.ps1 -Task run -- --cli D:\Vault\backup.7z D:\tmp\a.json"
}

switch ($Task) {
    "setup" {
        Ensure-Bootstrap
        & $venvPython -m pip install -e ".[dev]"
    }
    "bootstrap" {
        & $bootstrapScript
    }
    "test" {
        Ensure-Bootstrap
        & $venvPython -m pytest -q
    }
    "run" {
        Ensure-Bootstrap
        $runArgs = @("-m", "app.main")
        if ($AppArgs.Count -gt 0) {
            $runArgs += $AppArgs
        }
        & $venvPython @runArgs
    }
    "build-exe" {
        Ensure-Bootstrap
        & $buildExeScript @AppArgs
    }
    "help" {
        Show-Usage
    }
}
