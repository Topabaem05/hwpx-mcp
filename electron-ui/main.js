const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require("electron");
const { join, resolve, dirname } = require("path");
const { spawn, spawnSync } = require("child_process");
const { existsSync } = require("fs");

const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = process.env.MCP_PORT || "8000";
const MCP_PATH = process.env.MCP_PATH || "/mcp";
const BACKEND_URL = `http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}`;

let backendProcess = null;
let backendLog = [];
let mainWindow = null;

const log = (msg) => {
  const line = `[main] ${msg}`;
  console.log(line);
  backendLog.push(line);
  if (backendLog.length > 200) backendLog.shift();
};

const isCmd = (cmd) => {
  const check = process.platform === "win32" ? "where" : "which";
  return spawnSync(check, [cmd], { stdio: "ignore" }).status === 0;
};

const findBackendCommand = () => {
  const isWin = process.platform === "win32";
  const binName = isWin ? "hwpx-mcp-backend.exe" : "hwpx-mcp-backend";
  const batName = "hwpx-mcp-backend.bat";

  const resPath = typeof process.resourcesPath === "string" && process.resourcesPath
    ? process.resourcesPath
    : null;

  const appDir = __dirname;
  const repoRoot = resolve(appDir, "..");

  const candidates = [];

  if (resPath) {
    if (isWin) candidates.push({ path: join(resPath, "backend-win", batName), type: "bat" });
    candidates.push({ path: join(resPath, "backend", binName), type: "bin" });
  }

  if (isWin) candidates.push({ path: join(appDir, "resources", "backend-win", batName), type: "bat" });
  candidates.push({ path: join(appDir, "resources", "backend", binName), type: "bin" });

  if (isWin) candidates.push({ path: join(repoRoot, "dist", "hwpx-mcp-backend-win", batName), type: "bat" });
  candidates.push({ path: join(repoRoot, "dist", "hwpx-mcp-backend", binName), type: "bin" });

  for (const c of candidates) {
    log(`Checking: ${c.path} → ${existsSync(c.path) ? "FOUND" : "not found"}`);
    if (existsSync(c.path)) {
      return { cmd: c.path, type: c.type, cwd: dirname(c.path) };
    }
  }

  if (isCmd("uv")) {
    log("Fallback: uv run hwpx-mcp");
    return { cmd: "uv run hwpx-mcp", type: "shell", cwd: repoRoot };
  }
  const py = isCmd("python3") ? "python3" : isCmd("python") ? "python" : null;
  if (py) {
    log(`Fallback: ${py} -m hwpx_mcp.server`);
    return { cmd: `${py} -m hwpx_mcp.server`, type: "shell", cwd: repoRoot };
  }

  log("No backend command found.");
  return null;
};

const startBackend = () => {
  if (process.env.HWPX_MCP_START_BACKEND === "0") {
    log("Backend start skipped (HWPX_MCP_START_BACKEND=0)");
    return;
  }

  const found = findBackendCommand();
  if (!found) {
    log("ERROR: No backend command available.");
    return;
  }

  const { cmd, type, cwd } = found;

  const isWin = process.platform === "win32";
  let spawnCmd, spawnArgs;

  if (type === "bat") {
    spawnCmd = "cmd.exe";
    spawnArgs = ["/c", `"${cmd}"`];
  } else if (type === "bin") {
    spawnCmd = cmd;
    spawnArgs = [];
  } else {
    spawnCmd = cmd;
    spawnArgs = [];
  }

  log(`Starting backend: ${spawnCmd} ${spawnArgs.join(" ")}`);
  log(`  cwd: ${cwd}`);
  log(`  type: ${type}`);

  try {
    backendProcess = spawn(spawnCmd, spawnArgs, {
      cwd,
      shell: type !== "bin",
      windowsVerbatimArguments: isWin && type === "bat",
      env: {
        ...process.env,
        MCP_TRANSPORT: "streamable-http",
        MCP_HOST,
        MCP_PORT,
        MCP_PATH,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });

    backendProcess.stdout?.on("data", (d) => {
      const s = d.toString();
      process.stdout.write(`[backend] ${s}`);
      backendLog.push(`[out] ${s.trim()}`);
    });
    backendProcess.stderr?.on("data", (d) => {
      const s = d.toString();
      process.stderr.write(`[backend] ${s}`);
      backendLog.push(`[err] ${s.trim()}`);
    });
    backendProcess.on("error", (e) => {
      log(`Backend spawn error: ${e.message}`);
      backendProcess = null;
    });
    backendProcess.on("exit", (code, signal) => {
      log(`Backend exited: code=${code} signal=${signal}`);
      backendProcess = null;
    });

    log(`Backend process started (pid=${backendProcess.pid})`);
  } catch (e) {
    log(`Backend spawn failed: ${e.message}`);
    backendProcess = null;
  }
};

const stopBackend = () => {
  if (!backendProcess || backendProcess.killed) return;
  log("Stopping backend...");
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch (e) {
    log(`Stop error: ${e.message}`);
  }
  backendProcess = null;
};

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 640,
    show: false,
    backgroundColor: "#090b14",
    webPreferences: {
      preload: join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(join(__dirname, "src", "index.html"));
  mainWindow.once("ready-to-show", () => mainWindow.show());

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
};

// IPC Handlers
ipcMain.handle("dialog:saveFile", async (_, opts) => {
  const result = await dialog.showSaveDialog(BrowserWindow.getFocusedWindow(), {
    title: opts?.title || "Save file",
    defaultPath: opts?.defaultPath || "output.hwpx",
    filters: opts?.filters || [
      { name: "HWPX Documents", extensions: ["hwpx"] },
      { name: "HWP Documents", extensions: ["hwp"] },
      { name: "PDF", extensions: ["pdf"] },
      { name: "All Files", extensions: ["*"] },
    ],
  });
  return result.canceled ? null : result.filePath;
});

ipcMain.handle("dialog:openFile", async (_, opts) => {
  const result = await dialog.showOpenDialog(BrowserWindow.getFocusedWindow(), {
    title: opts?.title || "Open file",
    filters: opts?.filters || [
      { name: "HWP Documents", extensions: ["hwp", "hwpx"] },
      { name: "All Files", extensions: ["*"] },
    ],
    properties: ["openFile"],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("dialog:selectFolder", async (_, opts) => {
  const result = await dialog.showOpenDialog(BrowserWindow.getFocusedWindow(), {
    title: opts?.title || "Select folder",
    properties: ["openDirectory", "createDirectory"],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("backend:status", () => ({
  running: backendProcess !== null && !backendProcess.killed,
  pid: backendProcess?.pid ?? null,
  url: BACKEND_URL,
  log: backendLog.slice(-30),
}));

ipcMain.handle("backend:restart", () => {
  stopBackend();
  startBackend();
  return { restarted: true, url: BACKEND_URL, pid: backendProcess?.pid ?? null };
});

// App lifecycle
app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", stopBackend);
