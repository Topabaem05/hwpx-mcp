const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require("electron");
const { join, resolve } = require("path");
const { spawn, spawnSync } = require("child_process");
const { existsSync } = require("fs");

const REPO_ROOT = resolve(__dirname, "..");
const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = process.env.MCP_PORT || "8000";
const MCP_PATH = process.env.MCP_PATH || "/mcp";
const BACKEND_URL = `http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}`;

let backendProcess = null;

const isCmd = (cmd) => {
  const check = process.platform === "win32" ? "where" : "which";
  return spawnSync(check, [cmd], { stdio: "ignore" }).status === 0;
};

const findBackendCommand = () => {
  const binName = process.platform === "win32" ? "hwpx-mcp-backend.exe" : "hwpx-mcp-backend";
  const batName = "hwpx-mcp-backend.bat";

  const candidates = [
    join(process.resourcesPath || "", "backend", binName),
    join(process.resourcesPath || "", "backend-win", batName),
    join(__dirname, "resources", "backend", binName),
    join(__dirname, "resources", "backend-win", batName),
    join(REPO_ROOT, "dist", "hwpx-mcp-backend", binName),
    join(REPO_ROOT, "dist", "hwpx-mcp-backend-win", batName),
  ];

  for (const c of candidates) {
    if (existsSync(c)) return c;
  }

  if (isCmd("uv")) return "uv run hwpx-mcp";
  if (isCmd("python3")) return "python3 -m hwpx_mcp.server";
  if (isCmd("python")) return "python -m hwpx_mcp.server";
  return null;
};

const startBackend = () => {
  if (process.env.HWPX_MCP_START_BACKEND === "0") return;

  const cmd = findBackendCommand();
  if (!cmd) {
    console.error("No backend command found. MCP backend will not start.");
    return;
  }

  console.log(`Starting backend: ${cmd}`);
  backendProcess = spawn(cmd, [], {
    cwd: REPO_ROOT,
    shell: true,
    env: {
      ...process.env,
      MCP_TRANSPORT: "streamable-http",
      MCP_HOST,
      MCP_PORT,
      MCP_PATH,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProcess.stdout?.on("data", (d) => process.stdout.write(`[backend] ${d}`));
  backendProcess.stderr?.on("data", (d) => process.stderr.write(`[backend] ${d}`));
  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
};

const stopBackend = () => {
  if (!backendProcess || backendProcess.killed) return;
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], { stdio: "ignore" });
  } else {
    backendProcess.kill("SIGTERM");
  }
  backendProcess = null;
};

const createWindow = () => {
  const mainWindow = new BrowserWindow({
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
  url: BACKEND_URL,
}));

ipcMain.handle("backend:restart", () => {
  stopBackend();
  startBackend();
  return { restarted: true, url: BACKEND_URL };
});

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
