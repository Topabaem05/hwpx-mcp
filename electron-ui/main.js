const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require("electron");
const { join, resolve, dirname } = require("path");
const { spawn, spawnSync } = require("child_process");
const { existsSync } = require("fs");

const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = process.env.MCP_PORT || "8000";
const MCP_PATH = process.env.MCP_PATH || "/mcp";
const BACKEND_URL = `http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}`;

const OPENAI_OAUTH_ISSUER = (process.env.OPENAI_OAUTH_ISSUER || "https://auth.openai.com")
  .trim()
  .replace(/\/+$/, "");
const OPENAI_OAUTH_CLIENT_ID = (
  process.env.OPENAI_OAUTH_CLIENT_ID || "app_EMoamEEZ73f0CkXaXp7hrann"
)
  .trim();
const OPENAI_OAUTH_TIMEOUT_MS = Number.parseInt(
  process.env.OPENAI_OAUTH_TIMEOUT_MS || "900000",
  10
);
const OPENAI_OAUTH_API_BASE = `${OPENAI_OAUTH_ISSUER}/api/accounts`;
const OPENAI_OAUTH_DEVICE_URL = `${OPENAI_OAUTH_ISSUER}/codex/device`;

let backendProcess = null;
let backendLog = [];
let mainWindow = null;
let backendEnvOverrides = {};

const setOptionalEnv = (envName, value) => {
  const normalized = typeof value === "string" ? value.trim() : "";
  if (normalized) {
    backendEnvOverrides = { ...backendEnvOverrides, [envName]: normalized };
    return;
  }

  if (backendEnvOverrides[envName]) {
    const { [envName]: _removed, ...rest } = backendEnvOverrides;
    backendEnvOverrides = rest;
  }
};

const setBackendCredentials = (opts) => {
  if (!opts || typeof opts !== "object") {
    return;
  }

  setOptionalEnv("OPENAI_API_KEY", opts.openaiApiKey);
  setOptionalEnv("OPENAI_OAUTH_TOKEN", opts.gptOauthToken);
};

const log = (msg) => {
  const line = `[main] ${msg}`;
  console.log(line);
  backendLog.push(line);
  if (backendLog.length > 200) backendLog.shift();
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const requestOpenAiDeviceCode = async () => {
  if (!OPENAI_OAUTH_CLIENT_ID) {
    throw new Error("OPENAI_OAUTH_CLIENT_ID is not configured");
  }

  const response = await fetch(`${OPENAI_OAUTH_API_BASE}/deviceauth/usercode`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ client_id: OPENAI_OAUTH_CLIENT_ID }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`deviceauth usercode failed (${response.status}): ${body.slice(0, 200)}`);
  }

  const payload = await response.json();
  const deviceAuthId =
    typeof payload?.device_auth_id === "string" ? payload.device_auth_id.trim() : "";
  const userCode = typeof payload?.user_code === "string" ? payload.user_code.trim() : "";
  const rawInterval = typeof payload?.interval === "string" ? payload.interval : "5";
  const intervalSeconds = Math.max(3, Number.parseInt(rawInterval, 10) || 5);

  if (!deviceAuthId || !userCode) {
    throw new Error("Invalid deviceauth response from OpenAI issuer");
  }

  return {
    deviceAuthId,
    userCode,
    intervalSeconds,
  };
};

const pollOpenAiDeviceCode = async ({ deviceAuthId, userCode, intervalSeconds }) => {
  const startedAt = Date.now();

  while (Date.now() - startedAt < OPENAI_OAUTH_TIMEOUT_MS) {
    const response = await fetch(`${OPENAI_OAUTH_API_BASE}/deviceauth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        device_auth_id: deviceAuthId,
        user_code: userCode,
      }),
    });

    if (response.ok) {
      return response.json();
    }

    if (response.status === 403 || response.status === 404) {
      await sleep(intervalSeconds * 1000);
      continue;
    }

    const body = await response.text();
    throw new Error(`deviceauth token failed (${response.status}): ${body.slice(0, 200)}`);
  }

  throw new Error("OpenAI OAuth device login timed out after 15 minutes");
};

const exchangeOpenAiAuthorizationCode = async ({ authorizationCode, codeVerifier }) => {
  const redirectUri = `${OPENAI_OAUTH_ISSUER}/deviceauth/callback`;
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: authorizationCode,
    redirect_uri: redirectUri,
    client_id: OPENAI_OAUTH_CLIENT_ID,
    code_verifier: codeVerifier,
  });

  const response = await fetch(`${OPENAI_OAUTH_ISSUER}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(`oauth token exchange failed (${response.status}): ${payload.slice(0, 200)}`);
  }

  const tokenPayload = await response.json();
  const accessToken =
    typeof tokenPayload?.access_token === "string" ? tokenPayload.access_token.trim() : "";
  if (!accessToken) {
    throw new Error("OpenAI OAuth token response missing access_token");
  }

  return accessToken;
};

const runOpenAiOauthLogin = async () => {
  const device = await requestOpenAiDeviceCode();
  await shell.openExternal(OPENAI_OAUTH_DEVICE_URL);

  const codePayload = await pollOpenAiDeviceCode(device);
  const authorizationCode =
    typeof codePayload?.authorization_code === "string"
      ? codePayload.authorization_code.trim()
      : "";
  const codeVerifier =
    typeof codePayload?.code_verifier === "string" ? codePayload.code_verifier.trim() : "";

  if (!authorizationCode || !codeVerifier) {
    throw new Error("OpenAI OAuth device flow did not return authorization code details");
  }

  const accessToken = await exchangeOpenAiAuthorizationCode({
    authorizationCode,
    codeVerifier,
  });

  return {
    accessToken,
    userCode: device.userCode,
    verificationUrl: OPENAI_OAUTH_DEVICE_URL,
  };
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
        ...backendEnvOverrides,
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
    backgroundColor: "#f2f4f6",
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

ipcMain.handle("backend:restart", (_, opts) => {
  setBackendCredentials(opts);
  stopBackend();
  startBackend();
  return { restarted: true, url: BACKEND_URL, pid: backendProcess?.pid ?? null };
});

ipcMain.handle("auth:openai-oauth-login", async () => {
  try {
    const login = await runOpenAiOauthLogin();
    setOptionalEnv("OPENAI_OAUTH_TOKEN", login.accessToken);
    return { success: true, ...login };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
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
