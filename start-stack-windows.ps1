[CmdletBinding()]
param(
    [switch]$RunAgent
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronUiDir = Join-Path $repoRoot "electron-ui"
$startStackScript = Join-Path $electronUiDir "scripts\start-stack.js"
$runtimeManagerScript = Join-Path $electronUiDir "scripts\runtime-manager.js"

if (-not (Test-Path (Join-Path $electronUiDir "package.json"))) {
    Write-Error "Could not find electron-ui directory. Run this script from the repository root."
    exit 1
}

if (-not (Test-Path $startStackScript)) {
    Write-Error "Could not find Electron launcher script: $startStackScript"
    exit 1
}

if (-not (Test-Path $runtimeManagerScript)) {
    Write-Error "Could not find runtime manager script: $runtimeManagerScript"
    exit 1
}

if (-not $env:HWPX_MCP_START_BACKEND) {
    $env:HWPX_MCP_START_BACKEND = "1"
}

$stackCommand = @"
Set-Location "$repoRoot"
`$env:MCP_TRANSPORT = "streamable-http"
`$env:MCP_HOST = "127.0.0.1"
`$env:MCP_PORT = "8000"
`$env:MCP_PATH = "/mcp"
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
`$startStackArgs = @()
if (`$env:HWPX_RUNTIME_DRY_RUN -eq "1") { `$startStackArgs += "--dry-run" }
if (`$env:HWPX_RUNTIME_JSON -eq "1") { `$startStackArgs += "--json" }
& node "$startStackScript" @startStackArgs
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $stackCommand

if ($RunAgent) {
    $gatewayCommand = @"
Set-Location "$repoRoot"
`$env:MCP_TRANSPORT = "stdio"
hwpx-mcp-gateway
"@

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $gatewayCommand
}
