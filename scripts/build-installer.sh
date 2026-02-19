#!/usr/bin/env bash
# Unified installer build pipeline for HWPX-MCP.
#
# This script runs the full pipeline:
#   1. Build Python backend binary (PyInstaller)
#   2. Install Electron UI dependencies
#   3. Build Electron installer (electron-builder)
#
# Usage:
#   ./scripts/build-installer.sh              # build for current platform
#   ./scripts/build-installer.sh --skip-backend  # skip PyInstaller step
#
# Prerequisites:
#   - Python 3.10+ with pip/uv
#   - Node.js 18+ with npm
#   - PyInstaller (auto-installed if missing)
#
# Output:
#   dist/hwpx-mcp-backend/          Backend binary directory
#   dist/electron-installer/        Electron installer files

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ELECTRON_UI_DIR="$REPO_ROOT/electron-ui"
DIST_DIR="$REPO_ROOT/dist"
SKIP_BACKEND=false

for arg in "$@"; do
  case "$arg" in
    --skip-backend) SKIP_BACKEND=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

echo "=============================================="
echo " HWPX-MCP Installer Build Pipeline"
echo "=============================================="
echo "Repository:  $REPO_ROOT"
echo "Platform:    $(uname -s) $(uname -m)"
echo "Skip backend: $SKIP_BACKEND"
echo ""

# Step 1: Backend
if [ "$SKIP_BACKEND" = false ]; then
  echo "--- Step 1: Building backend binary ---"
  bash "$REPO_ROOT/scripts/build-backend.sh"
  echo ""
else
  echo "--- Step 1: Skipping backend build ---"
  if [ ! -d "$DIST_DIR/hwpx-mcp-backend" ]; then
    echo "WARNING: dist/hwpx-mcp-backend/ not found."
    echo "Electron installer will be built without bundled backend."
    echo "Users will need Python runtime to run the backend."
  fi
  echo ""
fi

# Step 2: Electron UI dependencies
echo "--- Step 2: Installing Electron UI dependencies ---"
if [ ! -d "$ELECTRON_UI_DIR/node_modules" ]; then
  if command -v npm >/dev/null 2>&1; then
    (cd "$ELECTRON_UI_DIR" && npm install)
  elif command -v bunx >/dev/null 2>&1; then
    (cd "$ELECTRON_UI_DIR" && bunx npm install)
  else
    echo "ERROR: npm or bunx required for Electron dependency install."
    exit 1
  fi
else
  echo "node_modules already present, skipping install."
fi
echo ""

# Step 3: Electron installer
echo "--- Step 3: Building Electron installer ---"
PLATFORM="$(uname -s)"
case "$PLATFORM" in
  Darwin)
    echo "Building for macOS..."
    (cd "$ELECTRON_UI_DIR" && npm run build:mac)
    ;;
  Linux)
    echo "Building for Linux..."
    (cd "$ELECTRON_UI_DIR" && npm run build:linux)
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "Building for Windows..."
    (cd "$ELECTRON_UI_DIR" && npm run build:win)
    ;;
  *)
    echo "Unknown platform: $PLATFORM"
    echo "Attempting generic directory build..."
    (cd "$ELECTRON_UI_DIR" && npm run build:dir)
    ;;
esac
echo ""

# Summary
echo "=============================================="
echo " Build Complete"
echo "=============================================="
echo ""

if [ -d "$DIST_DIR/hwpx-mcp-backend" ]; then
  echo "Backend binary:  $DIST_DIR/hwpx-mcp-backend/"
fi

INSTALLER_DIR="$DIST_DIR/electron-installer"
if [ -d "$INSTALLER_DIR" ]; then
  echo "Installer output: $INSTALLER_DIR/"
  echo ""
  echo "Files:"
  ls -lh "$INSTALLER_DIR/" 2>/dev/null | tail -n +2 || true
fi
