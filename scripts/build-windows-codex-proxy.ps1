[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$distDir = Join-Path $repoRoot "dist"
$winProxyDir = Join-Path $distDir "codex-proxy-win"
$wheelDir = Join-Path $distDir "_win_codex_proxy_wheels"
$pipBootstrapDir = Join-Path $distDir "_win_codex_proxy_pip"

$pythonVersion = "3.13.1"
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
Write-Host "Python version:   $pythonVersion"
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
    if ($lines -notcontains "../Lib/site-packages") { $lines += "../Lib/site-packages" }
    if ($lines -notcontains "..") { $lines += ".." }
    Set-Content -Path $pthFile.FullName -Value $lines -Encoding UTF8
}

Write-Host "--- Step 2: Downloading codex-lb wheels ---"
python -m pip install --quiet --target $pipBootstrapDir "pip<24.1"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
python - <<PY
import sys
sys.path.insert(0, r"$pipBootstrapDir")
from pip._internal.cli.main import main as pip_main
deps = [
    r"aiohttp>=3.13.3",
    r"aiohttp-retry>=2.9.1",
    r"aiosqlite>=0.22.1",
    r"alembic>=1.16.5",
    r"asyncpg>=0.30.0",
    r"bcrypt>=4.3.0",
    r"brotli>=1.2.0",
    r"codex-lb==$codexLbVersion",
    r"cryptography>=46.0.3",
    r"email-validator>=2.0.0",
    r"fastapi>=0.128.0",
    r"greenlet>=3.3.0",
    r"jinja2>=3.1.5",
    r"psycopg[binary]>=3.2.12",
    r"pydantic>=2.12.5",
    r"pydantic-settings>=2.12.0",
    r"pyotp>=2.9.0",
    r"python-dotenv>=1.2.1",
    r"python-multipart>=0.0.21",
    r"segno>=1.6.6",
    r"sqlalchemy>=2.0.45",
    r"uvicorn>=0.41.0",
    r"zstandard>=0.25.0",
]
for dep in deps:
    args = [
        'download',
        '--dest', r'$wheelDir',
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
PY
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
set "PYTHONHOME=%SCRIPT_DIR%python"
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%Lib\site-packages"
set "PATH=%SCRIPT_DIR%python;%PATH%"

if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=2455"

echo Starting bundled codex-lb proxy on http://%HOST%:%PORT% ...
"%SCRIPT_DIR%python\python.exe" -m app.cli --host %HOST% --port %PORT% %* < NUL > NUL 2>&1
'@
Set-Content -Path (Join-Path $winProxyDir "codex-proxy.bat") -Value $bat -Encoding ASCII

$ps = @'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHOME = Join-Path $scriptDir "python"
$env:PYTHONPATH = "$scriptDir;$(Join-Path $scriptDir 'Lib\site-packages')"
$env:PATH = "$(Join-Path $scriptDir 'python');$env:PATH"

if (-not $env:HOST) { $env:HOST = "127.0.0.1" }
if (-not $env:PORT) { $env:PORT = "2455" }

Write-Host "Starting bundled codex-lb proxy on http://$($env:HOST):$($env:PORT) ..."
& (Join-Path $scriptDir "python\python.exe") -m app.cli --host $env:HOST --port $env:PORT @args *> $null
'@
Set-Content -Path (Join-Path $winProxyDir "codex-proxy.ps1") -Value $ps -Encoding UTF8

Write-Host "--- Step 5: Summary ---"
Write-Host "Output: $winProxyDir"
Get-ChildItem $winProxyDir | Format-Table Name, Length, LastWriteTime -AutoSize

if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
if (Test-Path $pipBootstrapDir) { Remove-Item $pipBootstrapDir -Recurse -Force }
