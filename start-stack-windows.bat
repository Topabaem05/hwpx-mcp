@echo off
setlocal

set "REPO_ROOT=%~dp0"

set "HWPX_MCP_START_BACKEND=%HWPX_MCP_START_BACKEND%"
if not defined HWPX_MCP_START_BACKEND set "HWPX_MCP_START_BACKEND=1"

set "HWPX_MCP_BACKEND_EXE=%HWPX_MCP_BACKEND_EXE%"

set "HWPX_MCP_BACKEND_COMMAND=%HWPX_MCP_BACKEND_COMMAND%"
set "HWPX_ELECTRON_PKG_MANAGER=%HWPX_ELECTRON_PKG_MANAGER%"
set "UI_INSTALL_COMMAND="

if defined HWPX_MCP_BACKEND_EXE (
  if not exist "%HWPX_MCP_BACKEND_EXE%" (
    if not exist "%REPO_ROOT%%HWPX_MCP_BACKEND_EXE%" (
      echo Could not find backend executable from HWPX_MCP_BACKEND_EXE=%HWPX_MCP_BACKEND_EXE%.
      echo Set HWPX_MCP_BACKEND_EXE to an existing executable path.
      exit /b 1
    )
    set "HWPX_MCP_BACKEND_EXE=%REPO_ROOT%%HWPX_MCP_BACKEND_EXE%"
  )

  set "HWPX_MCP_BACKEND_COMMAND=\"%HWPX_MCP_BACKEND_EXE%\""
) else (
  if not defined HWPX_MCP_BACKEND_COMMAND set "HWPX_MCP_BACKEND_COMMAND=uv run hwpx-mcp"
)

if /I "%HWPX_MCP_START_BACKEND%"=="0" (
  echo Skipping backend startup because HWPX_MCP_START_BACKEND=0.
) else (
  if not defined HWPX_MCP_BACKEND_EXE (
    where uv >nul 2>nul
    if errorlevel 1 (
      where python3 >nul 2>nul
      if errorlevel 1 (
        where python >nul 2>nul
        if errorlevel 1 (
          echo Could not find uv, python3, or python in PATH.
          echo Install uv or Python, or set HWPX_MCP_BACKEND_COMMAND to an executable command.
          exit /b 1
        ) else (
          set "HWPX_MCP_BACKEND_COMMAND=python -m hwpx_mcp.server"
        )
      ) else (
        set "HWPX_MCP_BACKEND_COMMAND=python3 -m hwpx_mcp.server"
      )
    )
  )
)

if not exist "%REPO_ROOT%electron-ui\package.json" (
  echo Could not find electron-ui directory. Run this script from the repository root.
  exit /b 1
)

if not exist "%REPO_ROOT%electron-ui\node_modules" (
  echo Installing Electron UI dependencies...

  if defined HWPX_ELECTRON_PKG_MANAGER (
    if /I "%HWPX_ELECTRON_PKG_MANAGER%"=="npm" (
      set "UI_INSTALL_COMMAND=npm install"
    ) else if /I "%HWPX_ELECTRON_PKG_MANAGER%"=="bunx" (
      set "UI_INSTALL_COMMAND=bunx npm install"
    ) else (
      echo Invalid HWPX_ELECTRON_PKG_MANAGER=%HWPX_ELECTRON_PKG_MANAGER%. Use npm or bunx.
      exit /b 1
    )
  )

  if not defined UI_INSTALL_COMMAND (
    where npm >nul 2>nul
    if not errorlevel 1 set "UI_INSTALL_COMMAND=npm install"
  )

  if not defined UI_INSTALL_COMMAND (
    where bunx >nul 2>nul
    if not errorlevel 1 set "UI_INSTALL_COMMAND=bunx npm install"
  )

  if not defined UI_INSTALL_COMMAND (
    echo Could not find npm or bunx. Install Node.js/npm or Bun and retry.
    exit /b 1
  )

  pushd "%REPO_ROOT%electron-ui"
  call %UI_INSTALL_COMMAND%
  popd
)

if /I "%HWPX_MCP_START_BACKEND%"=="0" (
  echo HWPX_MCP_START_BACKEND is set. Backend will not be started.
) else (
  start "hwpx-mcp (streamable-http)" cmd /k "cd /d \"%REPO_ROOT%\" && set MCP_TRANSPORT=streamable-http && set MCP_HOST=127.0.0.1 && set MCP_PORT=8000 && set MCP_PATH=/mcp && set HWPX_MCP_BACKEND_COMMAND=%HWPX_MCP_BACKEND_COMMAND% && call %HWPX_MCP_BACKEND_COMMAND%"
)
start "hwpx-mcp-electron-ui" cmd /k "cd /d \"%REPO_ROOT%electron-ui\" && set OPEN_WEBUI_URL=http://localhost:3000 && set HWPX_MCP_HTTP_URL=http://127.0.0.1:8000/mcp && npm start"

if /I "%~1"=="agent" (
  start "hwpx-mcp-agentic-gateway" cmd /k "cd /d \"%REPO_ROOT%\" && set MCP_TRANSPORT=stdio && hwpx-mcp-gateway"
)
