#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TARGETS=(
  ".venv"
  ".pytest_cache"
  ".ruff_cache"
  ".mypy_cache"
  ".pdm-build"
  "dist"
  "build"
  "electron-ui/node_modules"
  "electron-ui/out"
  "electron-ui/dist"
)

for target in "${TARGETS[@]}"; do
  path="$REPO_ROOT/$target"
  if [ -e "$path" ]; then
    rm -rf "$path"
    echo "Removed: $target"
  fi
done

echo "Cleanup complete."
