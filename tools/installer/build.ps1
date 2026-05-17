#requires -version 5.1
<#
.SYNOPSIS
    Build the DroneResearch Windows installers (CLI + GCS).

.DESCRIPTION
    End-to-end build pipeline:

      1. Generate the RZ branding assets (icon + Inno wizard images).
      2. Run PyInstaller for the CLI bundle  → dist\DroneResearchCLI\
      3. Run PyInstaller for the GCS bundle  → dist\RZGCS\
      4. Compile both Inno Setup scripts     → tools\installer\out\

    Output:
      tools\installer\out\DroneResearch-CLI-Setup-0.2.0.exe
      tools\installer\out\RZ-GCS-Setup-0.2.0.exe

.PARAMETER Target
    Which installer(s) to build: 'cli', 'gcs', or 'all' (default).

.PARAMETER SkipBundle
    Skip PyInstaller steps and only re-compile the Inno installers.
    Useful when you only changed the .iss scripts or branding assets.

.PARAMETER InnoCompiler
    Full path to ISCC.exe. Defaults to the standard Inno Setup 6 location.

.EXAMPLE
    .\tools\installer\build.ps1
.EXAMPLE
    .\tools\installer\build.ps1 -Target gcs
.EXAMPLE
    .\tools\installer\build.ps1 -SkipBundle -Target cli
#>
[CmdletBinding()]
param(
    [ValidateSet('cli', 'gcs', 'all')]
    [string]$Target = 'all',

    [switch]$SkipBundle,

    [string]$InnoCompiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
)

$ErrorActionPreference = 'Stop'

# Repository root = grandparent of this script's directory.
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path

Set-Location $ProjectRoot
Write-Host "──────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host " RZ Solutions / DroneResearch Installer Builder" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host " Target:       $Target" -ForegroundColor Cyan
Write-Host " Skip bundle:  $SkipBundle" -ForegroundColor Cyan
Write-Host "──────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""

# ── Sanity checks ────────────────────────────────────────────────────
function Test-Tool($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Missing tool '$cmd'. $hint"
    }
}
Test-Tool 'python' 'Install Python 3.10+ and ensure it is on PATH.'

if (-not $SkipBundle) {
    Test-Tool 'pyinstaller' "Install build deps:`n    pip install -r tools\installer\requirements_build.txt"
}

if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup compiler not found at:`n    $InnoCompiler`n" +
          "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php " +
          "or pass -InnoCompiler <path>."
}

# ── Step 1: Branding assets ──────────────────────────────────────────
Write-Host "[1/4] Generating RZ branding assets..." -ForegroundColor Yellow
python tools\installer\icon\make_assets.py
if ($LASTEXITCODE -ne 0) { throw "Asset generation failed." }
Write-Host ""

# ── Step 2 & 3: PyInstaller bundles ──────────────────────────────────
function Invoke-PyInstaller($spec, $label) {
    Write-Host "[2/4] PyInstaller: $label" -ForegroundColor Yellow
    Write-Host "       spec = $spec" -ForegroundColor DarkGray
    pyinstaller --noconfirm --clean $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $label." }
    Write-Host ""
}

if (-not $SkipBundle) {
    if ($Target -in @('cli', 'all')) {
        Invoke-PyInstaller 'tools\installer\specs\droneresearch_cli.spec' 'CLI bundle'
    }
    if ($Target -in @('gcs', 'all')) {
        Invoke-PyInstaller 'tools\installer\specs\rz_gcs.spec' 'RZ GCS bundle'
    }
} else {
    Write-Host "[2/4] Skipping PyInstaller (-SkipBundle)" -ForegroundColor DarkGray
    Write-Host ""
}

# ── Step 4: Inno Setup ───────────────────────────────────────────────
function Invoke-Inno($iss, $label) {
    Write-Host "[4/4] Inno Setup: $label" -ForegroundColor Yellow
    & $InnoCompiler /Q $iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed for $label." }
    Write-Host ""
}

New-Item -ItemType Directory -Force -Path 'tools\installer\out' | Out-Null

if ($Target -in @('cli', 'all')) {
    Invoke-Inno 'tools\installer\inno\droneresearch_cli.iss' 'CLI installer'
}
if ($Target -in @('gcs', 'all')) {
    Invoke-Inno 'tools\installer\inno\rz_gcs.iss' 'RZ GCS installer'
}

# Summary
Write-Host 'Build complete' -ForegroundColor Green
Get-ChildItem 'tools\installer\out\*.exe' | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 1)
    Write-Host ($_.Name + ' ' + $sizeMB + ' MB') -ForegroundColor White
}
