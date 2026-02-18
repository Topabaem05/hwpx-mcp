#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ELECTRON_UI_DIR="$REPO_ROOT/electron-ui"

if ! command -v bunx >/dev/null 2>&1; then
  echo "bunx is required for this launcher but was not found in PATH."
  echo "Install Bun first: https://bun.sh/"
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  echo "Installing Python package dependencies with uv..."
  uv pip install -e "$REPO_ROOT"
elif command -v python3 >/dev/null 2>&1; then
  echo "Installing Python package dependencies with python3..."
  python3 -m pip install -e "$REPO_ROOT"
elif command -v python >/dev/null 2>&1; then
  echo "Installing Python package dependencies with python..."
  python -m pip install -e "$REPO_ROOT"
else
  echo "Could not find uv, python3, or python in PATH."
  echo "Install one of them and retry."
  exit 1
fi

if [ ! -d "$ELECTRON_UI_DIR/node_modules" ]; then
  echo "Installing Electron UI dependencies with bunx npm install..."
  (cd "$ELECTRON_UI_DIR" && bunx npm install)
fi

export HWPX_ELECTRON_PKG_MANAGER=bunx
export HWPX_MCP_START_BACKEND="${HWPX_MCP_START_BACKEND:-1}"

if [ -z "${HWPX_MCP_BACKEND_COMMAND:-}" ]; then
  if command -v uv >/dev/null 2>&1; then
    export HWPX_MCP_BACKEND_COMMAND="uv run hwpx-mcp"
  elif command -v python3 >/dev/null 2>&1; then
    export HWPX_MCP_BACKEND_COMMAND="python3 -m hwpx_mcp.server"
  elif command -v python >/dev/null 2>&1; then
    export HWPX_MCP_BACKEND_COMMAND="python -m hwpx_mcp.server"
  fi
fi

(cd "$ELECTRON_UI_DIR" && bunx npm run start-stack)
