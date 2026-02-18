[CmdletBinding()]
param()

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$electronUiDir = Join-Path $repoRoot "electron-ui"

if (-not (Get-Command bunx -ErrorAction SilentlyContinue)) {
  Write-Error "bunx is required for this launcher but was not found in PATH."
  Write-Error "Install Bun first: https://bun.sh/"
  exit 1
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
  Write-Host "Installing Python package dependencies with uv..."
  uv pip install -e $repoRoot
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  Write-Host "Installing Python package dependencies with python3..."
  python3 -m pip install -e $repoRoot
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  Write-Host "Installing Python package dependencies with python..."
  python -m pip install -e $repoRoot
} else {
  Write-Error "Could not find uv, python3, or python in PATH."
  Write-Error "Install one of them and retry."
  exit 1
}

if (-not (Test-Path (Join-Path $electronUiDir "node_modules"))) {
  Write-Host "Installing Electron UI dependencies with bunx npm install..."
  Push-Location $electronUiDir
  bunx npm install
  Pop-Location
}

$env:HWPX_ELECTRON_PKG_MANAGER = "bunx"

if (-not $env:HWPX_MCP_START_BACKEND) {
  $env:HWPX_MCP_START_BACKEND = "1"
}

if (-not $env:HWPX_MCP_BACKEND_COMMAND) {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    $env:HWPX_MCP_BACKEND_COMMAND = "uv run hwpx-mcp"
  } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $env:HWPX_MCP_BACKEND_COMMAND = "python3 -m hwpx_mcp.server"
  } elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $env:HWPX_MCP_BACKEND_COMMAND = "python -m hwpx_mcp.server"
  }
}

Push-Location $electronUiDir
try {
  bunx npm run start-stack
} finally {
  Pop-Location
}
