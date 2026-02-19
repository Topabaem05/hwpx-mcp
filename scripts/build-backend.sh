#!/usr/bin/env bash
# Build the hwpx-mcp Python backend into a standalone binary using PyInstaller.
#
# Usage:
#   ./scripts/build-backend.sh
#
# Output:
#   dist/hwpx-mcp-backend/   (directory with binary + dependencies)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE="$REPO_ROOT/hwpx-mcp-backend.spec"
DIST_DIR="$REPO_ROOT/dist"

if [ ! -f "$SPEC_FILE" ]; then
  echo "ERROR: Spec file not found at $SPEC_FILE"
  exit 1
fi

install_pyinstaller() {
  if command -v pyinstaller >/dev/null 2>&1; then
    return 0
  fi

  echo "PyInstaller not found. Installing..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install "pyinstaller>=6.0.0"
  elif command -v pip3 >/dev/null 2>&1; then
    pip3 install "pyinstaller>=6.0.0"
  elif command -v pip >/dev/null 2>&1; then
    pip install "pyinstaller>=6.0.0"
  else
    echo "ERROR: No pip/uv found to install PyInstaller."
    exit 1
  fi
}

install_deps() {
  echo "Ensuring backend Python dependencies are installed..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install -e "$REPO_ROOT"
  elif command -v pip3 >/dev/null 2>&1; then
    pip3 install -e "$REPO_ROOT"
  elif command -v pip >/dev/null 2>&1; then
    pip install -e "$REPO_ROOT"
  else
    echo "ERROR: No pip/uv found to install dependencies."
    exit 1
  fi
}

echo "=== HWPX-MCP Backend Build ==="
echo "Repository root: $REPO_ROOT"

install_deps
install_pyinstaller

echo "Running PyInstaller..."
cd "$REPO_ROOT"
pyinstaller "$SPEC_FILE" --noconfirm --distpath "$DIST_DIR" --workpath "$REPO_ROOT/build"

BACKEND_DIR="$DIST_DIR/hwpx-mcp-backend"
if [ -d "$BACKEND_DIR" ]; then
  echo ""
  echo "Build successful!"
  echo "Output: $BACKEND_DIR"
  echo ""
  echo "Test the binary:"
  echo "  MCP_TRANSPORT=stdio $BACKEND_DIR/hwpx-mcp-backend"
else
  echo "ERROR: Build output not found at $BACKEND_DIR"
  exit 1
fi
