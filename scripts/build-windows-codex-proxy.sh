#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
WIN_PROXY_DIR="$DIST_DIR/codex-proxy-win"
WHEEL_DIR="$DIST_DIR/_win_codex_proxy_wheels"
PIP_BOOTSTRAP_DIR="$DIST_DIR/_win_codex_proxy_pip"

PYTHON_VERSION="3.13.1"
PYTHON_EMBED_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_ZIP="$DIST_DIR/python-${PYTHON_VERSION}-embed-amd64.zip"
CODEX_LB_VERSION="1.1.1"
DEPS=(
  "aiohttp>=3.13.3"
  "aiohttp-retry>=2.9.1"
  "aiosqlite>=0.22.1"
  "alembic>=1.16.5"
  "asyncpg>=0.30.0"
  "bcrypt>=4.3.0"
  "brotli>=1.2.0"
  "codex-lb==${CODEX_LB_VERSION}"
  "cryptography>=46.0.3"
  "email-validator>=2.0.0"
  "fastapi>=0.128.0"
  "greenlet>=3.3.0"
  "jinja2>=3.1.5"
  "psycopg[binary]>=3.2.12"
  "pydantic>=2.12.5"
  "pydantic-settings>=2.12.0"
  "pyotp>=2.9.0"
  "python-dotenv>=1.2.1"
  "python-multipart>=0.0.21"
  "segno>=1.6.6"
  "sqlalchemy>=2.0.45"
  "uvicorn>=0.41.0"
  "zstandard>=0.25.0"
)

echo "=============================================="
echo " Windows Codex Proxy Bundle Builder"
echo "=============================================="
echo "Python version:    $PYTHON_VERSION"
echo "codex-lb version:  $CODEX_LB_VERSION"
echo "Output:            $WIN_PROXY_DIR"
echo ""

rm -rf "$WIN_PROXY_DIR" "$WHEEL_DIR" "$PIP_BOOTSTRAP_DIR"
mkdir -p "$WIN_PROXY_DIR/python" "$WHEEL_DIR"

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
(cd "$WIN_PROXY_DIR/python" && unzip -qo "$PYTHON_EMBED_ZIP")

PTH_FILE=$(ls "$WIN_PROXY_DIR/python"/python*._pth 2>/dev/null | head -1)
if [ -n "$PTH_FILE" ]; then
  python3 - "$PTH_FILE" <<'PY'
import pathlib
import sys

pth = pathlib.Path(sys.argv[1])
text = pth.read_text(encoding="utf-8")
text = text.replace("#import site", "import site")
lines = text.splitlines()
for extra in ("../Lib/site-packages", ".."):
    if extra not in lines:
        lines.append(extra)
pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi
echo ""

echo "--- Step 2: Downloading codex-lb Windows wheels ---"
python3 -m pip install --quiet --target "$PIP_BOOTSTRAP_DIR" "pip<24.1"
PIP_DISABLE_PIP_VERSION_CHECK=1 python3 - "$PIP_BOOTSTRAP_DIR" "$WHEEL_DIR" <<'PY'
import sys

bootstrap_dir, wheel_dir = sys.argv[1:3]
sys.path.insert(0, bootstrap_dir)

from pip._internal.cli.main import main as pip_main

deps = [
    'aiohttp>=3.13.3',
    'aiohttp-retry>=2.9.1',
    'aiosqlite>=0.22.1',
    'alembic>=1.16.5',
    'asyncpg>=0.30.0',
    'bcrypt>=4.3.0',
    'brotli>=1.2.0',
    'codex-lb==1.1.1',
    'cryptography>=46.0.3',
    'email-validator>=2.0.0',
    'fastapi>=0.128.0',
    'greenlet>=3.3.0',
    'jinja2>=3.1.5',
    'psycopg[binary]>=3.2.12',
    'pydantic>=2.12.5',
    'pydantic-settings>=2.12.0',
    'pyotp>=2.9.0',
    'python-dotenv>=1.2.1',
    'python-multipart>=0.0.21',
    'segno>=1.6.6',
    'sqlalchemy>=2.0.45',
    'uvicorn>=0.41.0',
    'zstandard>=0.25.0',
]

for dep in deps:
    args = [
        'download',
        '--dest', wheel_dir,
        '--platform', 'win_amd64',
        '--python-version', '3.13',
        '--only-binary=:all:',
        '--progress-bar', 'off',
    ]
    if dep.startswith('codex-lb=='):
        args.append('--no-deps')
    args.append(dep)
    result = pip_main(args)
    if result != 0:
        raise SystemExit(result)
PY
echo ""

echo "--- Step 3: Extracting wheels into bundle ---"
SITE_PKG="$WIN_PROXY_DIR/Lib/site-packages"
mkdir -p "$SITE_PKG"

for whl in "$WHEEL_DIR"/*.whl; do
  [ -f "$whl" ] || continue
  unzip -qo "$whl" -d "$SITE_PKG"
done
echo ""

echo "--- Step 4: Creating proxy launchers ---"
cat > "$WIN_PROXY_DIR/codex-proxy.bat" <<'BATCH_EOF'
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONHOME=%SCRIPT_DIR%python"
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%Lib\site-packages"
set "PATH=%SCRIPT_DIR%python;%PATH%"

if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=2455"

echo Starting bundled codex-lb proxy on http://%HOST%:%PORT% ...
"%SCRIPT_DIR%python\python.exe" -m app.cli --host %HOST% --port %PORT% %* < NUL > NUL 2>&1
BATCH_EOF

cat > "$WIN_PROXY_DIR/codex-proxy.ps1" <<'PS_EOF'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHOME = Join-Path $scriptDir "python"
$env:PYTHONPATH = "$scriptDir;$(Join-Path $scriptDir 'Lib\site-packages')"
$env:PATH = "$(Join-Path $scriptDir 'python');$env:PATH"

if (-not $env:HOST) { $env:HOST = "127.0.0.1" }
if (-not $env:PORT) { $env:PORT = "2455" }

Write-Host "Starting bundled codex-lb proxy on http://$($env:HOST):$($env:PORT) ..."
& (Join-Path $scriptDir "python\python.exe") -m app.cli --host $env:HOST --port $env:PORT @args *> $null
PS_EOF
echo ""

echo "--- Step 5: Summary ---"
TOTAL_SIZE=$(du -sh "$WIN_PROXY_DIR" | cut -f1)
echo "Output:   $WIN_PROXY_DIR"
echo "Size:     $TOTAL_SIZE"
echo "Contents:"
ls -1 "$WIN_PROXY_DIR/"

rm -rf "$WHEEL_DIR" "$PIP_BOOTSTRAP_DIR"
