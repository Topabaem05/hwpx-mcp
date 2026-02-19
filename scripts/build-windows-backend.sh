#!/usr/bin/env bash
# Build a self-contained Windows backend bundle from Linux.
#
# PyInstaller cannot cross-compile, so this script uses:
#   1. Python embeddable distribution (official python.org zip for Windows)
#   2. pip download --platform win_amd64 to fetch Windows wheels
#   3. A launcher .bat that starts the MCP server
#
# Usage:
#   ./scripts/build-windows-backend.sh
#
# Output:
#   dist/hwpx-mcp-backend-win/
#     python/            Embeddable Python runtime
#     Lib/site-packages/ Installed dependencies
#     hwpx_mcp/          Project source
#     templates/          Template assets
#     security_module/    Security DLL
#     hwpx-mcp-backend.bat  Launcher script
#
# Prerequisites:
#   - Python 3 (host, for pip download)
#   - wget or curl
#   - unzip

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
WIN_BACKEND_DIR="$DIST_DIR/hwpx-mcp-backend-win"
WHEEL_DIR="$DIST_DIR/_win_wheels"

PYTHON_VERSION="3.11.9"
PYTHON_EMBED_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_ZIP="$DIST_DIR/python-${PYTHON_VERSION}-embed-amd64.zip"

echo "=============================================="
echo " Windows Self-Contained Backend Builder"
echo "=============================================="
echo "Python version:  $PYTHON_VERSION"
echo "Output:          $WIN_BACKEND_DIR"
echo ""

rm -rf "$WIN_BACKEND_DIR" "$WHEEL_DIR"
mkdir -p "$WIN_BACKEND_DIR/python" "$WHEEL_DIR"

# Step 1: Download Python embeddable
echo "--- Step 1: Downloading Python ${PYTHON_VERSION} embeddable for Windows ---"
if [ ! -f "$PYTHON_EMBED_ZIP" ]; then
  if command -v wget >/dev/null 2>&1; then
    wget -q -O "$PYTHON_EMBED_ZIP" "$PYTHON_EMBED_URL"
  elif command -v curl >/dev/null 2>&1; then
    curl -sL -o "$PYTHON_EMBED_ZIP" "$PYTHON_EMBED_URL"
  else
    echo "ERROR: wget or curl required."
    exit 1
  fi
fi
(cd "$WIN_BACKEND_DIR/python" && unzip -qo "$PYTHON_EMBED_ZIP")
echo "Extracted Python embeddable."

# Enable site-packages in embedded Python
PTH_FILE=$(ls "$WIN_BACKEND_DIR/python"/python*._pth 2>/dev/null | head -1)
if [ -n "$PTH_FILE" ]; then
  sed -i 's/^#import site/import site/' "$PTH_FILE"
  echo "../Lib/site-packages" >> "$PTH_FILE"
  echo "../../" >> "$PTH_FILE"
  echo "Enabled site-packages in $PTH_FILE"
fi
echo ""

# Step 2: Download Windows wheels for all dependencies
echo "--- Step 2: Downloading Windows wheels ---"
PY_MINOR="${PYTHON_VERSION%.*}"

DEPS=(
  "mcp>=1.0.0"
  "fastmcp>=0.2.0"
  "pyhwp>=0.1a"
  "pandas>=2.0.0"
  "matplotlib>=3.7.0"
  "pydantic>=2.5.0"
  "python-dotenv>=1.0.0"
  "python-hwpx>=1.9"
  "lxml>=5.0.0"
  "defusedxml>=0.7.0"
  "xmlschema>=3.0.0"
  "pydantic-xml>=2.0.0"
  "xmldiff>=2.0.0"
  "uvicorn>=0.30.0"
  "starlette>=0.38.0"
)

for dep in "${DEPS[@]}"; do
  echo "  Downloading: $dep"
  pip3 download \
    --dest "$WHEEL_DIR" \
    --platform win_amd64 \
    --python-version "$PY_MINOR" \
    --only-binary=:all: \
    "$dep" 2>/dev/null || \
  pip3 download \
    --dest "$WHEEL_DIR" \
    --no-deps \
    --platform any \
    --python-version "$PY_MINOR" \
    "$dep" 2>/dev/null || \
  pip3 download \
    --dest "$WHEEL_DIR" \
    "$dep" 2>/dev/null || \
  echo "    WARNING: Could not download $dep (may need source build on Windows)"
done
echo ""

# Step 3: Extract wheels into Lib/site-packages
echo "--- Step 3: Installing wheels into bundle ---"
SITE_PKG="$WIN_BACKEND_DIR/Lib/site-packages"
mkdir -p "$SITE_PKG"

for whl in "$WHEEL_DIR"/*.whl; do
  [ -f "$whl" ] || continue
  unzip -qo "$whl" -d "$SITE_PKG" 2>/dev/null || true
done

for targz in "$WHEEL_DIR"/*.tar.gz; do
  [ -f "$targz" ] || continue
  TMPEXT="$WHEEL_DIR/_extract"
  mkdir -p "$TMPEXT"
  tar xzf "$targz" -C "$TMPEXT" 2>/dev/null || continue
  PKG_DIR=$(find "$TMPEXT" -name "setup.py" -o -name "pyproject.toml" | head -1 | xargs dirname 2>/dev/null)
  if [ -n "$PKG_DIR" ]; then
    SRC_DIR=$(find "$PKG_DIR" -maxdepth 1 -type d ! -name "*.egg-info" ! -name "__pycache__" | tail -n +2 | head -1)
    if [ -n "$SRC_DIR" ]; then
      cp -r "$SRC_DIR" "$SITE_PKG/" 2>/dev/null || true
    fi
  fi
  rm -rf "$TMPEXT"
done

echo "Installed $(find "$SITE_PKG" -maxdepth 1 -type d | wc -l) packages."
echo ""

# Step 4: Copy project source
echo "--- Step 4: Copying project source ---"
cp -r "$REPO_ROOT/hwpx_mcp" "$WIN_BACKEND_DIR/"
[ -d "$REPO_ROOT/templates" ] && cp -r "$REPO_ROOT/templates" "$WIN_BACKEND_DIR/"
[ -d "$REPO_ROOT/security_module" ] && cp -r "$REPO_ROOT/security_module" "$WIN_BACKEND_DIR/"
echo "Copied hwpx_mcp, templates, security_module."
echo ""

# Step 5: Create launcher scripts
echo "--- Step 5: Creating launcher scripts ---"

cat > "$WIN_BACKEND_DIR/hwpx-mcp-backend.bat" << 'BATCH_EOF'
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONHOME=%SCRIPT_DIR%python"
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%Lib\site-packages"
set "PATH=%SCRIPT_DIR%python;%PATH%"

if not defined MCP_TRANSPORT set "MCP_TRANSPORT=streamable-http"
if not defined MCP_HOST set "MCP_HOST=127.0.0.1"
if not defined MCP_PORT set "MCP_PORT=8000"
if not defined MCP_PATH set "MCP_PATH=/mcp"

echo Starting HWPX-MCP Backend Server...
echo Transport: %MCP_TRANSPORT%
echo Endpoint:  http://%MCP_HOST%:%MCP_PORT%%MCP_PATH%

"%SCRIPT_DIR%python\python.exe" -m hwpx_mcp.server %*
BATCH_EOF

cat > "$WIN_BACKEND_DIR/hwpx-mcp-backend.ps1" << 'PS_EOF'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHOME = Join-Path $scriptDir "python"
$env:PYTHONPATH = "$scriptDir;$(Join-Path $scriptDir 'Lib\site-packages')"
$env:PATH = "$(Join-Path $scriptDir 'python');$env:PATH"

if (-not $env:MCP_TRANSPORT) { $env:MCP_TRANSPORT = "streamable-http" }
if (-not $env:MCP_HOST)      { $env:MCP_HOST = "127.0.0.1" }
if (-not $env:MCP_PORT)      { $env:MCP_PORT = "8000" }
if (-not $env:MCP_PATH)      { $env:MCP_PATH = "/mcp" }

Write-Host "Starting HWPX-MCP Backend Server..."
Write-Host "Transport: $($env:MCP_TRANSPORT)"
Write-Host "Endpoint:  http://$($env:MCP_HOST):$($env:MCP_PORT)$($env:MCP_PATH)"

& (Join-Path $scriptDir "python\python.exe") -m hwpx_mcp.server @args
PS_EOF

echo "Created hwpx-mcp-backend.bat and hwpx-mcp-backend.ps1"
echo ""

# Step 6: Summary
echo "=============================================="
echo " Build Complete"
echo "=============================================="
TOTAL_SIZE=$(du -sh "$WIN_BACKEND_DIR" | cut -f1)
echo "Output:   $WIN_BACKEND_DIR"
echo "Size:     $TOTAL_SIZE"
echo ""
echo "Contents:"
ls -1 "$WIN_BACKEND_DIR/"
echo ""
echo "To test on Windows:"
echo "  hwpx-mcp-backend.bat"

rm -rf "$WHEEL_DIR"
