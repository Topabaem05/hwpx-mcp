# Unified installer build pipeline for HWPX-MCP (Windows).
#
# This script runs the full pipeline:
#   1. Build Python backend binary (PyInstaller)
#   2. Install Electron UI dependencies
#   3. Build Electron installer (electron-builder)
#
# Usage:
#   ./scripts/build-installer.ps1
#   ./scripts/build-installer.ps1 -SkipBackend
#
# Prerequisites:
#   - Python 3.10+ with pip/uv
#   - Node.js 18+ with npm
#   - PyInstaller (auto-installed if missing)
#
# Output:
#   dist\hwpx-mcp-backend\          Backend binary directory
#   dist\electron-installer\        Electron installer files

[CmdletBinding()]
param(
    [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$electronUiDir = Join-Path $repoRoot "electron-ui"
$distDir = Join-Path $repoRoot "dist"

Write-Host "=============================================="
Write-Host " HWPX-MCP Installer Build Pipeline"
Write-Host "=============================================="
Write-Host "Repository:   $repoRoot"
Write-Host "Platform:     Windows $([System.Environment]::Is64BitOperatingSystem ? 'x64' : 'x86')"
Write-Host "Skip backend: $SkipBackend"
Write-Host ""

# Step 1: Backend
if (-not $SkipBackend) {
    Write-Host "--- Step 1: Building backend binary ---"
    & (Join-Path $repoRoot "scripts" "build-backend.ps1")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Backend build failed."
        exit 1
    }
    Write-Host ""
} else {
    Write-Host "--- Step 1: Skipping backend build ---"
    $backendDir = Join-Path $distDir "hwpx-mcp-backend"
    if (-not (Test-Path $backendDir)) {
        Write-Warning "dist\hwpx-mcp-backend\ not found."
        Write-Warning "Electron installer will be built without bundled backend."
        Write-Warning "Users will need Python runtime to run the backend."
    }
    Write-Host ""
}

# Step 2: Electron UI dependencies
Write-Host "--- Step 2: Installing Electron UI dependencies ---"
$nodeModulesDir = Join-Path $electronUiDir "node_modules"
if (-not (Test-Path $nodeModulesDir)) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location $electronUiDir
        npm install
        Pop-Location
    } elseif (Get-Command bunx -ErrorAction SilentlyContinue) {
        Push-Location $electronUiDir
        bunx npm install
        Pop-Location
    } else {
        Write-Error "npm or bunx required for Electron dependency install."
        exit 1
    }
} else {
    Write-Host "node_modules already present, skipping install."
}
Write-Host ""

# Step 3: Electron installer
Write-Host "--- Step 3: Building Electron installer ---"
Write-Host "Building for Windows..."
Push-Location $electronUiDir
npm run build:win
if ($LASTEXITCODE -ne 0) {
    Write-Error "Electron build failed."
    Pop-Location
    exit 1
}
Pop-Location
Write-Host ""

# Summary
Write-Host "=============================================="
Write-Host " Build Complete"
Write-Host "=============================================="
Write-Host ""

$backendOutputDir = Join-Path $distDir "hwpx-mcp-backend"
if (Test-Path $backendOutputDir) {
    Write-Host "Backend binary:  $backendOutputDir"
}

$installerDir = Join-Path $distDir "electron-installer"
if (Test-Path $installerDir) {
    Write-Host "Installer output: $installerDir"
    Write-Host ""
    Write-Host "Files:"
    Get-ChildItem $installerDir | Format-Table Name, Length, LastWriteTime -AutoSize
}
