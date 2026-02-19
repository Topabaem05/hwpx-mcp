# Build the hwpx-mcp Python backend into a standalone binary using PyInstaller.
#
# Usage:
#   ./scripts/build-backend.ps1
#
# Output:
#   dist\hwpx-mcp-backend\   (directory with binary + dependencies)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$specFile = Join-Path $repoRoot "hwpx-mcp-backend.spec"
$distDir = Join-Path $repoRoot "dist"

if (-not (Test-Path $specFile)) {
    Write-Error "Spec file not found at $specFile"
    exit 1
}

function Install-PyInstaller {
    if (Get-Command pyinstaller -ErrorAction SilentlyContinue) {
        return
    }

    Write-Host "PyInstaller not found. Installing..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv pip install "pyinstaller>=6.0.0"
    } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
        pip3 install "pyinstaller>=6.0.0"
    } elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        pip install "pyinstaller>=6.0.0"
    } else {
        Write-Error "No pip/uv found to install PyInstaller."
        exit 1
    }
}

function Install-Dependencies {
    Write-Host "Ensuring backend Python dependencies are installed..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv pip install -e $repoRoot
    } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
        pip3 install -e $repoRoot
    } elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        pip install -e $repoRoot
    } else {
        Write-Error "No pip/uv found to install dependencies."
        exit 1
    }
}

Write-Host "=== HWPX-MCP Backend Build ==="
Write-Host "Repository root: $repoRoot"

Install-Dependencies
Install-PyInstaller

Write-Host "Running PyInstaller..."
Set-Location $repoRoot
pyinstaller $specFile --noconfirm --distpath $distDir --workpath (Join-Path $repoRoot "build")

$backendDir = Join-Path $distDir "hwpx-mcp-backend"
if (Test-Path $backendDir) {
    Write-Host ""
    Write-Host "Build successful!"
    Write-Host "Output: $backendDir"
    Write-Host ""
    Write-Host "Test the binary:"
    Write-Host "  `$env:MCP_TRANSPORT = 'stdio'; & '$backendDir\hwpx-mcp-backend.exe'"
} else {
    Write-Error "Build output not found at $backendDir"
    exit 1
}
