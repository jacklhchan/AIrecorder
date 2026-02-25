param(
    [switch]$Clean,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$venvPath = Join-Path $projectRoot ".venv-windows"
$pythonExe = Join-Path $venvPath "Scripts\\python.exe"
$specPath = Join-Path $projectRoot "packaging\\AIrecorder.spec"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ from python.org first."
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath"
    py -3.11 -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment python not found at $pythonExe"
}

if (-not (Test-Path $specPath)) {
    throw "PyInstaller spec file not found at $specPath"
}

if (-not $SkipDependencyInstall) {
    Write-Host "Installing Python dependencies"
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt")
    & $pythonExe -m pip install pyinstaller
}

$pyinstallerArgs = @("-m", "PyInstaller", "--noconfirm")
if ($Clean) {
    $pyinstallerArgs += "--clean"
}
$pyinstallerArgs += $specPath

Write-Host "Running PyInstaller build"
& $pythonExe @pyinstallerArgs

$exePath = Join-Path $projectRoot "dist\\AIrecorder\\AIrecorder.exe"
if (Test-Path $exePath) {
    Write-Host "Build complete: $exePath"
} else {
    throw "Build did not produce expected executable at $exePath"
}
