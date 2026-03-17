@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "START_STACK_SCRIPT=%REPO_ROOT%electron-ui\scripts\start-stack.js"
set "RUNTIME_MANAGER_SCRIPT=%REPO_ROOT%electron-ui\scripts\runtime-manager.js"
set "STACK_ARGS="

set "HWPX_MCP_START_BACKEND=%HWPX_MCP_START_BACKEND%"
if not defined HWPX_MCP_START_BACKEND set "HWPX_MCP_START_BACKEND=1"

set "HWPX_ELECTRON_PKG_MANAGER=%HWPX_ELECTRON_PKG_MANAGER%"

if not exist "%REPO_ROOT%electron-ui\package.json" (
  echo Could not find electron-ui directory. Run this script from the repository root.
  exit /b 1
)

if not exist "%START_STACK_SCRIPT%" (
  echo Could not find Electron launcher script: %START_STACK_SCRIPT%
  exit /b 1
)

if not exist "%RUNTIME_MANAGER_SCRIPT%" (
  echo Could not find runtime manager script: %RUNTIME_MANAGER_SCRIPT%
  exit /b 1
)

if "%HWPX_RUNTIME_DRY_RUN%"=="1" set "STACK_ARGS=%STACK_ARGS% --dry-run"
if "%HWPX_RUNTIME_JSON%"=="1" set "STACK_ARGS=%STACK_ARGS% --json"

if /I "%~1"=="agent" (
  start "hwpx-mcp-agentic-gateway" cmd /k "cd /d \"%REPO_ROOT%\" && set MCP_TRANSPORT=stdio && hwpx-mcp-gateway"
)

start "hwpx-mcp-stack" cmd /k "cd /d \"%REPO_ROOT%\" && set MCP_TRANSPORT=streamable-http && set MCP_HOST=127.0.0.1 && set MCP_PORT=8000 && set MCP_PATH=/mcp && set PYTHONHOME= && set PYTHONPATH= && node \"%START_STACK_SCRIPT%\"%STACK_ARGS%"
