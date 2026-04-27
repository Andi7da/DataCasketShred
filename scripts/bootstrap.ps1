param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$venvPath = Join-Path $projectRoot ".venv"

if (-not (Test-Path $venvPath)) {
    python -m venv ".venv"
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found at $venvPython"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e ".[dev]"

$envFile = Join-Path $projectRoot ".env"
$envExampleFile = Join-Path $projectRoot ".env.example"
if ((-not (Test-Path $envFile)) -and (Test-Path $envExampleFile)) {
    Copy-Item $envExampleFile $envFile
}

if ($RunTests) {
    & $venvPython -m pytest -q
}

Write-Host "Bootstrap complete."
Write-Host "Use .\.venv\Scripts\Activate.ps1 to activate the environment."
