[CmdletBinding()]
param(
    [switch]$RunAgent
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronUiDir = Join-Path $repoRoot "electron-ui"
$electronNodeModules = Join-Path $electronUiDir "node_modules"
$startBackend = $env:HWPX_MCP_START_BACKEND -ne "0"
$packageManager = $env:HWPX_ELECTRON_PKG_MANAGER

$resolveInstallCommand = {
    param([string]$managerPreference)

    if ($managerPreference) {
        switch ($managerPreference.ToLowerInvariant()) {
            "npm" {
                if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
                    Write-Error "HWPX_ELECTRON_PKG_MANAGER is set to npm, but npm command is not available."
                    return $null
                }

                return @("npm", "install")
            }
            "bunx" {
                if (-not (Get-Command bunx -ErrorAction SilentlyContinue)) {
                    Write-Error "HWPX_ELECTRON_PKG_MANAGER is set to bunx, but bunx command is not available."
                    return $null
                }

                return @("bunx", "npm", "install")
            }
            default {
                Write-Error "Unsupported HWPX_ELECTRON_PKG_MANAGER='$managerPreference'. Use npm or bunx."
                return $null
            }
        }
    }

    if (Get-Command npm -ErrorAction SilentlyContinue) {
        return @("npm", "install")
    }

    if (Get-Command bunx -ErrorAction SilentlyContinue) {
        return @("bunx", "npm", "install")
    }

    Write-Error "Could not find npm or bunx for Electron UI dependency install. Install Node.js or Bun."
    return $null
}

$backendExecutable = $env:HWPX_MCP_BACKEND_EXE
$backendCommand = if ($env:HWPX_MCP_BACKEND_COMMAND) {
    $env:HWPX_MCP_BACKEND_COMMAND
} else {
    "uv run hwpx-mcp"
}

$backendExecutableCommand = if ($backendExecutable) {
    $resolvedExecutable = if ([System.IO.Path]::IsPathRooted($backendExecutable)) {
        $backendExecutable
    } else {
        Join-Path $repoRoot $backendExecutable
    }

    if (-not (Test-Path $resolvedExecutable)) {
        Write-Error "Could not find backend executable from HWPX_MCP_BACKEND_EXE=$backendExecutable."
        Write-Error "Set HWPX_MCP_BACKEND_EXE to an existing executable path."
        exit 1
    }

    "\"$resolvedExecutable\""
} else {
    $false
}

if ($backendExecutableCommand) {
    $backendCommand = $backendExecutableCommand
}

if ($startBackend -and -not $backendExecutableCommand -and $backendCommand -match '^uv\s+run\s+') {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        if (Get-Command python3 -ErrorAction SilentlyContinue) {
            $backendCommand = "python3 -m hwpx_mcp.server"
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            $backendCommand = "python -m hwpx_mcp.server"
        } else {
            Write-Error "Could not find uv, python3, or python in PATH. Install one of them or set HWPX_MCP_BACKEND_COMMAND to an executable command."
            exit 1
        }
    }
}

if (-not $startBackend) {
    Write-Host "Skipping backend startup because HWPX_MCP_START_BACKEND=0."
}

if (-not (Test-Path (Join-Path $electronUiDir "package.json"))) {
    Write-Error "Could not find electron-ui directory. Run this script from the repository root."
    exit 1
}

if (-not (Test-Path $electronNodeModules)) {
    Write-Host "Installing Electron UI dependencies..."
    $installCommand = & $resolveInstallCommand $packageManager

    if (-not $installCommand) {
        exit 1
    }

    Push-Location $electronUiDir
    & $installCommand[0] $installCommand[1..($installCommand.Length - 1)]

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Electron UI dependency install command failed. Install with npm or bunx directly and retry."
        exit 1
    }

    Pop-Location
}

if ($startBackend) {
    $serverCommand = @"
Set-Location "$repoRoot"
`$env:MCP_TRANSPORT = "streamable-http"
`$env:MCP_HOST = "127.0.0.1"
`$env:MCP_PORT = "8000"
`$env:MCP_PATH = "/mcp"
`$env:HWPX_MCP_BACKEND_COMMAND = "$backendCommand"
& cmd /c `"$backendCommand`"
"@
}

$uiCommand = @"
Set-Location "$electronUiDir"
`$env:OPEN_WEBUI_URL = "http://localhost:3000"
`$env:HWPX_MCP_HTTP_URL = "http://127.0.0.1:8000/mcp"
npm start
"@

if ($startBackend) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $serverCommand
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", $uiCommand

if ($RunAgent) {
    $gatewayCommand = @"
Set-Location "$repoRoot"
`$env:MCP_TRANSPORT = "stdio"
hwpx-mcp-gateway
"@

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $gatewayCommand
}
