[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$distDir = Join-Path $repoRoot "dist"
$winBackendDir = Join-Path $distDir "hwpx-mcp-backend-win"
$wheelDir = Join-Path $distDir "_win_backend_wheels"
$extractDir = Join-Path $distDir "_win_backend_extract"
$pythonVersionFile = Join-Path $repoRoot "scripts/runtime/python-version.txt"

if (-not (Test-Path $pythonVersionFile)) {
    Write-Error "Missing Python version pin: $pythonVersionFile"
    exit 1
}

$pythonVersion = (Get-Content -Path $pythonVersionFile -Raw).Trim()
if (-not $pythonVersion) {
    Write-Error "Python version pin is empty: $pythonVersionFile"
    exit 1
}

$parts = $pythonVersion.Split('.')
if ($parts.Count -lt 2) {
    Write-Error "Python version pin must use major.minor.patch format: $pythonVersion"
    exit 1
}
$pythonMinorVersion = "$($parts[0]).$($parts[1])"
$pythonEmbedUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$pythonEmbedZip = Join-Path $distDir "python-$pythonVersion-embed-amd64.zip"
$deps = @(
    "pyhwpx",
    "pywin32>=305",
    "mcp>=1.0.0",
    "fastmcp>=0.2.0",
    "pyhwp>=0.1a",
    "pandas>=2.0.0",
    "matplotlib>=3.7.0",
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
    "python-hwpx>=1.9",
    "lxml>=5.0.0",
    "defusedxml>=0.7.0",
    "xmlschema>=3.0.0",
    "pydantic-xml>=2.0.0",
    "xmldiff>=2.0.0",
    "uvicorn>=0.30.0",
    "fastapi>=0.110.0",
    "starlette>=0.38.0",
    "httpx>=0.28.0",
    "langgraph>=0.2.0",
    "torch>=2.5.0",
    "transformers>=4.49.0",
    "accelerate>=1.2.0",
    "safetensors>=0.5.0",
    "huggingface_hub>=0.28.0"
)

function Invoke-PipDownload {
    param(
        [string[]]$Arguments
    )

    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()
    try {
        $process = Start-Process -FilePath "python" -ArgumentList @("-m", "pip") + $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
        return $process.ExitCode -eq 0
    }
    finally {
        if (Test-Path $stdoutFile) { Remove-Item $stdoutFile -Force }
        if (Test-Path $stderrFile) { Remove-Item $stderrFile -Force }
    }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is required to build the Windows backend bundle."
    exit 1
}

Write-Host "=============================================="
Write-Host " Windows Self-Contained Backend Builder"
Write-Host "=============================================="
Write-Host "Python version:  $pythonVersion"
Write-Host "Version source:  $pythonVersionFile"
Write-Host "Output:          $winBackendDir"
Write-Host ""

if (Test-Path $winBackendDir) { Remove-Item $winBackendDir -Recurse -Force }
if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }

New-Item -ItemType Directory -Force -Path (Join-Path $winBackendDir "python") | Out-Null
New-Item -ItemType Directory -Force -Path $wheelDir | Out-Null

Write-Host "--- Step 1: Downloading Python embeddable ---"
if (-not (Test-Path $pythonEmbedZip)) {
    Invoke-WebRequest -Uri $pythonEmbedUrl -OutFile $pythonEmbedZip
}
Expand-Archive -Path $pythonEmbedZip -DestinationPath (Join-Path $winBackendDir "python") -Force

$pthFile = Get-ChildItem (Join-Path $winBackendDir "python") -Filter "python*._pth" | Select-Object -First 1
if ($pthFile) {
    $lines = Get-Content $pthFile.FullName
    $lines = $lines | ForEach-Object {
        if ($_ -eq "#import site") { "import site" } else { $_ }
    }
    if ($lines -notcontains "..\Lib\site-packages") { $lines += "..\Lib\site-packages" }
    if ($lines -notcontains "..") { $lines += ".." }
    Set-Content -Path $pthFile.FullName -Value $lines -Encoding ASCII
}

Write-Host "--- Step 2: Downloading Windows wheels ---"
foreach ($dep in $deps) {
    Write-Host "  Downloading: $dep"
    $downloaded = Invoke-PipDownload -Arguments @(
        "download",
        "--dest", $wheelDir,
        "--platform", "win_amd64",
        "--python-version", $pythonMinorVersion,
        "--only-binary=:all:",
        $dep
    )

    if (-not $downloaded) {
        $downloaded = Invoke-PipDownload -Arguments @(
            "download",
            "--dest", $wheelDir,
            "--no-deps",
            "--platform", "any",
            "--python-version", $pythonMinorVersion,
            $dep
        )
    }

    if (-not $downloaded) {
        $downloaded = Invoke-PipDownload -Arguments @(
            "download",
            "--dest", $wheelDir,
            $dep
        )
    }

    if (-not $downloaded) {
        Write-Warning "Could not download $dep (may need source build on Windows)."
    }
}

Write-Host "--- Step 3: Installing wheels into bundle ---"
$sitePackages = Join-Path $winBackendDir "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

$extractScriptPath = Join-Path $distDir "_win_backend_extract.py"
$extractScript = @'
import pathlib
import shutil
import sys
import tarfile
import zipfile

wheel_dir = pathlib.Path(sys.argv[1])
site_packages = pathlib.Path(sys.argv[2])
extract_dir = pathlib.Path(sys.argv[3])

for wheel in wheel_dir.glob("*.whl"):
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(site_packages)

for source_archive in wheel_dir.glob("*.tar.gz"):
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_archive, "r:gz") as tf:
        tf.extractall(extract_dir)
    candidates = [
        path for path in extract_dir.rglob("*")
        if path.is_dir() and path.name not in {"__pycache__"} and not path.name.endswith(".egg-info")
    ]
    roots = [path for path in candidates if path.parent == extract_dir or path.parent.parent == extract_dir]
    for root in roots:
        marker = root / "__init__.py"
        if marker.exists() or any(root.glob("*.py")):
            shutil.copytree(root, site_packages / root.name, dirs_exist_ok=True)
'@
Set-Content -Path $extractScriptPath -Value $extractScript -Encoding ASCII
try {
    python $extractScriptPath $wheelDir $sitePackages $extractDir
}
finally {
    if (Test-Path $extractScriptPath) { Remove-Item $extractScriptPath -Force }
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
}

Write-Host "--- Step 4: Copying project source ---"
Copy-Item -Path (Join-Path $repoRoot "hwpx_mcp") -Destination $winBackendDir -Recurse -Force
if (Test-Path (Join-Path $repoRoot "templates")) {
    Copy-Item -Path (Join-Path $repoRoot "templates") -Destination $winBackendDir -Recurse -Force
}
if (Test-Path (Join-Path $repoRoot "security_module")) {
    Copy-Item -Path (Join-Path $repoRoot "security_module") -Destination $winBackendDir -Recurse -Force
}

Write-Host "--- Step 5: Creating launcher scripts ---"
$bat = @'
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PATH=%SCRIPT_DIR%python;%PATH%"

if not defined MCP_TRANSPORT set "MCP_TRANSPORT=streamable-http"
if not defined MCP_HOST set "MCP_HOST=127.0.0.1"
if not defined MCP_PORT set "MCP_PORT=8000"
if not defined MCP_PATH set "MCP_PATH=/mcp"

echo Starting HWPX-MCP Backend Server...
echo Transport: %MCP_TRANSPORT%
echo Endpoint:  http://%MCP_HOST%:%MCP_PORT%%MCP_PATH%

"%SCRIPT_DIR%python\python.exe" -m hwpx_mcp.server %*
'@
Set-Content -Path (Join-Path $winBackendDir "hwpx-mcp-backend.bat") -Value $bat -Encoding ASCII

$ps = @'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null
$env:PATH = "$(Join-Path $scriptDir 'python');$env:PATH"

if (-not $env:MCP_TRANSPORT) { $env:MCP_TRANSPORT = "streamable-http" }
if (-not $env:MCP_HOST) { $env:MCP_HOST = "127.0.0.1" }
if (-not $env:MCP_PORT) { $env:MCP_PORT = "8000" }
if (-not $env:MCP_PATH) { $env:MCP_PATH = "/mcp" }

Write-Host "Starting HWPX-MCP Backend Server..."
Write-Host "Transport: $($env:MCP_TRANSPORT)"
Write-Host "Endpoint:  http://$($env:MCP_HOST):$($env:MCP_PORT)$($env:MCP_PATH)"

& (Join-Path $scriptDir "python\python.exe") -m hwpx_mcp.server @args
'@
Set-Content -Path (Join-Path $winBackendDir "hwpx-mcp-backend.ps1") -Value $ps -Encoding UTF8

Write-Host "=============================================="
Write-Host " Build Complete"
Write-Host "=============================================="
Write-Host "Output:   $winBackendDir"
Get-ChildItem $winBackendDir | Format-Table Name, Length, LastWriteTime -AutoSize

if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
