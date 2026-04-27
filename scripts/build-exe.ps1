param(
    [string]$AppName = "DataCasketShred",
    [switch]$NoWindowed,
    [switch]$NoOneFile
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Missing .venv python at: $venvPython. Run .\scripts\bootstrap.ps1 first."
}

$pyInstallerCheck = & $venvPython -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if ($LASTEXITCODE -ne 0) {
    & $venvPython -m pip install pyinstaller
}

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--name", $AppName,
    "--add-data", "src/app/i18n/locales;app/i18n/locales",
    "src/app/main.py"
)

if (-not $NoWindowed) {
    $pyInstallerArgs += "--windowed"
}
if (-not $NoOneFile) {
    $pyInstallerArgs += "--onefile"
}

& $venvPython @pyInstallerArgs

Write-Host ""
Write-Host "Build complete."
Write-Host "Output folder: $projectRoot\dist"
