[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$distDir = Join-Path $repoRoot "dist"
$winProxyDir = Join-Path $distDir "codex-proxy-win"
$wheelDir = Join-Path $distDir "_win_codex_proxy_wheels"
$pipBootstrapDir = Join-Path $distDir "_win_codex_proxy_pip"
$pythonVersionFile = Join-Path $repoRoot "scripts/runtime/python-version.txt"
$codexPythonVersionFile = Join-Path $repoRoot "scripts/runtime/codex-proxy-python-version.txt"

if (-not (Test-Path $pythonVersionFile)) {
    Write-Error "Missing backend Python version pin: $pythonVersionFile"
    exit 1
}
$backendPythonVersion = (Get-Content -Path $pythonVersionFile -Raw).Trim()
if (-not $backendPythonVersion) {
    Write-Error "Backend Python version pin is empty: $pythonVersionFile"
    exit 1
}

if (-not (Test-Path $codexPythonVersionFile)) {
    Write-Error "Missing codex proxy Python version pin: $codexPythonVersionFile"
    exit 1
}
$pythonVersion = (Get-Content -Path $codexPythonVersionFile -Raw).Trim()
if (-not $pythonVersion) {
    Write-Error "Codex proxy Python version pin is empty: $codexPythonVersionFile"
    exit 1
}

$pythonEmbedUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$pythonEmbedZip = Join-Path $distDir "python-$pythonVersion-embed-amd64.zip"
$codexLbVersion = "1.1.1"
$deps = @(
    "aiohttp>=3.13.3",
    "aiohttp-retry>=2.9.1",
    "aiosqlite>=0.22.1",
    "alembic>=1.16.5",
    "asyncpg>=0.30.0",
    "bcrypt>=4.3.0",
    "brotli>=1.2.0",
    "codex-lb==$codexLbVersion",
    "cryptography>=46.0.3",
    "email-validator>=2.0.0",
    "fastapi>=0.128.0",
    "greenlet>=3.3.0",
    "jinja2>=3.1.5",
    "psycopg[binary]>=3.2.12",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.12.0",
    "pyotp>=2.9.0",
    "python-dotenv>=1.2.1",
    "python-multipart>=0.0.21",
    "segno>=1.6.6",
    "sqlalchemy>=2.0.45",
    "uvicorn>=0.41.0",
    "zstandard>=0.25.0"
)

Write-Host "=============================================="
Write-Host " Windows Codex Proxy Bundle Builder"
Write-Host "=============================================="
Write-Host "Python version:   $pythonVersion (explicit codex-proxy exception from $codexPythonVersionFile)"
Write-Host "Backend pin:      $backendPythonVersion (from $pythonVersionFile)"
Write-Host "codex-lb version: $codexLbVersion"
Write-Host "Output:           $winProxyDir"
Write-Host ""

if (Test-Path $winProxyDir) { Remove-Item $winProxyDir -Recurse -Force }
if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
if (Test-Path $pipBootstrapDir) { Remove-Item $pipBootstrapDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $winProxyDir "python") | Out-Null
New-Item -ItemType Directory -Force -Path $wheelDir | Out-Null

Write-Host "--- Step 1: Downloading Python embeddable ---"
if (-not (Test-Path $pythonEmbedZip)) {
    Invoke-WebRequest -Uri $pythonEmbedUrl -OutFile $pythonEmbedZip
}
Expand-Archive -Path $pythonEmbedZip -DestinationPath (Join-Path $winProxyDir "python") -Force

$pthFile = Get-ChildItem (Join-Path $winProxyDir "python") -Filter "python*._pth" | Select-Object -First 1
if ($pthFile) {
    $lines = Get-Content $pthFile.FullName
    $lines = $lines | ForEach-Object {
        if ($_ -eq "#import site") { "import site" } else { $_ }
    }
    if ($lines -notcontains "..\Lib\site-packages") { $lines += "..\Lib\site-packages" }
    if ($lines -notcontains "..") { $lines += ".." }
    Set-Content -Path $pthFile.FullName -Value $lines -Encoding ASCII
}

Write-Host "--- Step 2: Downloading codex-lb wheels ---"
python -m pip install --quiet --target $pipBootstrapDir "pip<24.1"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$downloadScriptPath = Join-Path $distDir "_win_codex_proxy_download.py"
$downloadScript = @'
import sys

bootstrap_dir, wheel_dir, codex_lb_version = sys.argv[1:4]
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
    f'codex-lb=={codex_lb_version}',
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
    code = pip_main(args)
    if code != 0:
        raise SystemExit(code)
'@
Set-Content -Path $downloadScriptPath -Value $downloadScript -Encoding ASCII
try {
    python $downloadScriptPath $pipBootstrapDir $wheelDir $codexLbVersion
}
finally {
    if (Test-Path $downloadScriptPath) { Remove-Item $downloadScriptPath -Force }
}
Remove-Item Env:PIP_DISABLE_PIP_VERSION_CHECK -ErrorAction SilentlyContinue

Write-Host "--- Step 3: Extracting wheels ---"
$sitePackages = Join-Path $winProxyDir "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
Get-ChildItem $wheelDir -Filter *.whl | ForEach-Object {
    Expand-Archive -Path $_.FullName -DestinationPath $sitePackages -Force
}

Write-Host "--- Step 4: Creating launchers ---"
$bat = @'
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PATH=%SCRIPT_DIR%python;%PATH%"

if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=2455"

echo Starting bundled codex-lb proxy on http://%HOST%:%PORT% ...
if defined CODEX_PROXY_LOG_PATH (
  "%SCRIPT_DIR%python\python.exe" -m app.cli --host %HOST% --port %PORT% %* < NUL >> "%CODEX_PROXY_LOG_PATH%" 2>&1
) else (
  "%SCRIPT_DIR%python\python.exe" -m app.cli --host %HOST% --port %PORT% %* < NUL > NUL 2>&1
)
'@
Set-Content -Path (Join-Path $winProxyDir "codex-proxy.bat") -Value $bat -Encoding ASCII

$ps = @'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null
$env:PATH = "$(Join-Path $scriptDir 'python');$env:PATH"

if (-not $env:HOST) { $env:HOST = "127.0.0.1" }
if (-not $env:PORT) { $env:PORT = "2455" }

Write-Host "Starting bundled codex-lb proxy on http://$($env:HOST):$($env:PORT) ..."
$pythonExe = Join-Path $scriptDir "python\python.exe"
if ($env:CODEX_PROXY_LOG_PATH) {
    & $pythonExe -m app.cli --host $env:HOST --port $env:PORT @args *>> $env:CODEX_PROXY_LOG_PATH
} else {
    & $pythonExe -m app.cli --host $env:HOST --port $env:PORT @args *> $null
}
'@
Set-Content -Path (Join-Path $winProxyDir "codex-proxy.ps1") -Value $ps -Encoding UTF8

Write-Host "--- Step 5: Summary ---"
Write-Host "Output: $winProxyDir"
Get-ChildItem $winProxyDir | Format-Table Name, Length, LastWriteTime -AutoSize

if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
if (Test-Path $pipBootstrapDir) { Remove-Item $pipBootstrapDir -Recurse -Force }
