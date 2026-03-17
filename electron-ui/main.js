const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require("electron");
const { autoUpdater } = require("electron-updater");
const { join, resolve, dirname } = require("path");
const { spawn, spawnSync } = require("child_process");
const { existsSync, appendFileSync, mkdirSync } = require("fs");
const { ensureAsync, resolveManagedBackend } = require("./scripts/runtime-manager");

const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = process.env.MCP_PORT || "8000";
const MCP_PATH = process.env.MCP_PATH || "/mcp";
const BACKEND_URL = `http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}`;
const REPO_ROOT = resolve(__dirname, "..");

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
const DEFAULT_AGENT_PROVIDER = (process.env.HWPX_AGENT_PROVIDER || "openrouter").trim();
const DEFAULT_AGENT_MODEL = (process.env.HWPX_AGENT_MODEL || "openai/gpt-oss-120b").trim();
const DEFAULT_CODEX_PROXY_URL = (
  process.env.HWPX_CODEX_PROXY_URL || "http://127.0.0.1:2455/v1/chat/completions"
).trim();
const DEFAULT_CODEX_PROXY_START = process.env.HWPX_CODEX_PROXY_START !== "0";
const DEFAULT_CODEX_PROXY_COMMAND = (process.env.HWPX_CODEX_PROXY_COMMAND || "").trim();
const DEFAULT_LOCAL_MODEL_ID = (process.env.HWPX_LOCAL_MODEL_ID || "Qwen/Qwen3.5-4B").trim();

const localModelBaseDir = () => {
  const localAppData = (process.env.LOCALAPPDATA || "").trim();
  if (localAppData) {
    return join(localAppData, "HWPX MCP");
  }
  return join(app.getPath("userData"), "local-model");
};

const defaultLocalModelHome = () => join(localModelBaseDir(), "models");
const defaultHfHome = () => join(localModelBaseDir(), "hf");

const readUrlField = (value) => {
  if (typeof value !== "string") {
    return "";
  }
  const trimmed = value.trim();
  return trimmed || "";
};

const resolveOpenAiVerificationUrls = (payload) => {
  const verificationUrlComplete =
    readUrlField(payload?.verification_uri_complete) ||
    readUrlField(payload?.verification_url_complete);

  const verificationUrl =
    readUrlField(payload?.verification_uri) ||
    readUrlField(payload?.verification_url) ||
    OPENAI_OAUTH_DEVICE_URL;

  return {
    verificationUrl,
    verificationUrlComplete,
    openUrl: verificationUrlComplete || verificationUrl || OPENAI_OAUTH_DEVICE_URL,
  };
};

let backendProcess = null;
let codexProxyProcess = null;
let backendLog = [];
let mainWindow = null;
let backendEnvOverrides = {};
let backendLogFilePath = null;
let backendFileLogFailed = false;
let appUpdateStatus = {
  state: "idle",
  message: "Automatic updates are available in installed builds.",
};

const emitAppUpdateStatus = (payload) => {
  appUpdateStatus = {
    ...appUpdateStatus,
    ...payload,
    updatedAt: new Date().toISOString(),
  };

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("app:update-status", appUpdateStatus);
  }
};

const resolveBackendLogFilePath = () => {
  if (backendLogFilePath) {
    return backendLogFilePath;
  }

  try {
    const logDir = join(app.getPath("userData"), "logs");
    mkdirSync(logDir, { recursive: true });
    backendLogFilePath = join(logDir, "backend-startup.log");
  } catch {
    backendLogFilePath = join(process.cwd(), "backend-startup.log");
  }

  return backendLogFilePath;
};

const appendBackendFileLog = (line) => {
  try {
    appendFileSync(resolveBackendLogFilePath(), `${new Date().toISOString()} ${line}\n`, "utf8");
  } catch (error) {
    if (!backendFileLogFailed) {
      backendFileLogFailed = true;
      const fallbackLine = `[main] Backend file logging disabled: ${error.message}`;
      backendLog.push(fallbackLine);
      if (backendLog.length > 200) backendLog.shift();
      console.warn(fallbackLine);
    }
  }
};

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

  const provider = typeof opts.provider === "string" && opts.provider.trim() ? opts.provider.trim() : DEFAULT_AGENT_PROVIDER;
  const model = typeof opts.model === "string" && opts.model.trim() ? opts.model.trim() : DEFAULT_AGENT_MODEL;
  const localModelId =
    typeof opts.localModelId === "string" && opts.localModelId.trim()
      ? opts.localModelId.trim()
      : provider === "local"
      ? model
      : effectiveEnv("HWPX_LOCAL_MODEL_ID", DEFAULT_LOCAL_MODEL_ID);

  setOptionalEnv("HWPX_AGENT_PROVIDER", provider);
  setOptionalEnv("HWPX_AGENT_MODEL", model);
  setOptionalEnv("HWPX_LOCAL_MODEL_ID", localModelId);
  setOptionalEnv(
    "HWPX_CODEX_PROXY_URL",
    provider === "codex-proxy" ? opts.codexProxyUrl || DEFAULT_CODEX_PROXY_URL : ""
  );
  setOptionalEnv(
    "HWPX_CODEX_PROXY_ACCESS_TOKEN",
    provider === "codex-proxy" ? opts.codexProxyAccessToken : ""
  );
  setOptionalEnv("OPENROUTER_API_KEY", provider === "openrouter" ? opts.openrouterApiKey : "");
  setOptionalEnv("OPENAI_API_KEY", provider === "openai" ? opts.openaiApiKey : "");
  setOptionalEnv("OPENAI_OAUTH_TOKEN", provider === "openai" ? opts.gptOauthToken : "");
  setOptionalEnv("CODEX_OAUTH_TOKEN", provider === "openai" ? opts.gptOauthToken : "");
};

const effectiveEnv = (name, fallback = "") => {
  if (typeof backendEnvOverrides[name] === "string" && backendEnvOverrides[name].trim()) {
    return backendEnvOverrides[name].trim();
  }
  const raw = process.env[name];
  return typeof raw === "string" && raw.trim() ? raw.trim() : fallback;
};

const currentAgentProvider = () => effectiveEnv("HWPX_AGENT_PROVIDER", DEFAULT_AGENT_PROVIDER);

const normalizeCodexProxyUrl = (value) => {
  const trimmed = typeof value === "string" ? value.trim() : "";
  const base = trimmed || DEFAULT_CODEX_PROXY_URL;
  const normalized = base.replace(/\/+$/, "");
  if (/\/chat\/completions$/i.test(normalized)) {
    return normalized;
  }
  if (/\/v1$/i.test(normalized)) {
    return `${normalized}/chat/completions`;
  }
  return `${normalized}/chat/completions`;
};

const currentCodexProxyUrl = () =>
  normalizeCodexProxyUrl(effectiveEnv("HWPX_CODEX_PROXY_URL", DEFAULT_CODEX_PROXY_URL));

const isCodexProxyAutoStartEnabled = () => {
  const raw = effectiveEnv(
    "HWPX_CODEX_PROXY_START",
    DEFAULT_CODEX_PROXY_START ? "1" : "0"
  );
  return raw !== "0";
};

const isCodexProxyProviderActive = () => currentAgentProvider() === "codex-proxy";

const isLocalUrl = (value) => {
  try {
    const parsed = new URL(value);
    return ["127.0.0.1", "localhost", "::1"].includes(parsed.hostname);
  } catch {
    return false;
  }
};

const codexProxyProbeUrls = (chatUrl) => {
  try {
    const parsed = new URL(chatUrl);
    return [
      `${parsed.origin}/health`,
      `${parsed.origin}/v1/models`,
    ];
  } catch {
    return [];
  }
};

const log = (msg) => {
  const line = `[main] ${msg}`;
  console.log(line);
  backendLog.push(line);
  if (backendLog.length > 200) backendLog.shift();
  appendBackendFileLog(line);
};

const updaterLogger = {
  info: (msg) => log(`[updater] ${msg}`),
  warn: (msg) => log(`[updater][warn] ${msg}`),
  error: (msg) => log(`[updater][error] ${msg}`),
  debug: (msg) => log(`[updater][debug] ${msg}`),
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const formatUpdateVersion = (value) => {
  if (typeof value !== "string") {
    return app.getVersion();
  }

  const trimmed = value.trim();
  return trimmed || app.getVersion();
};

const setupAutoUpdater = () => {
  if (!app.isPackaged) {
    emitAppUpdateStatus({
      state: "disabled-dev",
      message: "Automatic updates are disabled in development builds.",
    });
    return;
  }

  autoUpdater.logger = updaterLogger;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("checking-for-update", () => {
    emitAppUpdateStatus({
      state: "checking",
      message: "Checking for app updates...",
    });
  });

  autoUpdater.on("update-available", (info) => {
    emitAppUpdateStatus({
      state: "available",
      version: formatUpdateVersion(info?.version),
      message: `Update ${formatUpdateVersion(info?.version)} found. Downloading now...`,
    });
  });

  autoUpdater.on("update-not-available", (info) => {
    emitAppUpdateStatus({
      state: "not-available",
      version: formatUpdateVersion(info?.version),
      message: `App is up to date (${formatUpdateVersion(info?.version)}).`,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    const percent = Number.isFinite(progress?.percent) ? progress.percent : 0;
    emitAppUpdateStatus({
      state: "downloading",
      percent,
      message: `Downloading app update... ${percent.toFixed(1)}%`,
    });
  });

  autoUpdater.on("update-downloaded", async (info) => {
    emitAppUpdateStatus({
      state: "downloaded",
      version: formatUpdateVersion(info?.version),
      message: `Update ${formatUpdateVersion(info?.version)} is ready. Restart to install.`,
    });

    const targetWindow = mainWindow && !mainWindow.isDestroyed() ? mainWindow : null;
    const choice = await dialog.showMessageBox(targetWindow, {
      type: "info",
      buttons: ["Restart now", "Later"],
      defaultId: 0,
      cancelId: 1,
      title: "Update ready",
      message: `HWPX MCP ${formatUpdateVersion(info?.version)} has been downloaded.`,
      detail: "The update will be installed after the app restarts.",
    });

    if (choice.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on("error", (error) => {
    const message = error instanceof Error ? error.message : String(error);
    emitAppUpdateStatus({
      state: "error",
      message: `Automatic update failed: ${message}`,
    });
  });

  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((error) => {
      const message = error instanceof Error ? error.message : String(error);
      emitAppUpdateStatus({
        state: "error",
        message: `Automatic update failed: ${message}`,
      });
    });
  }, 12000);
};

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
  const rawInterval = payload?.interval;
  const intervalSeconds = Math.max(
    3,
    typeof rawInterval === "number"
      ? Math.floor(rawInterval)
      : Number.parseInt(typeof rawInterval === "string" ? rawInterval : "5", 10) || 5
  );

  const verification = resolveOpenAiVerificationUrls(payload);

  if (!deviceAuthId || !userCode) {
    throw new Error("Invalid deviceauth response from OpenAI issuer");
  }

  return {
    deviceAuthId,
    userCode,
    intervalSeconds,
    ...verification,
  };
};

const pollOpenAiDeviceCode = async ({ deviceAuthId, userCode, intervalSeconds }) => {
  const startedAt = Date.now();
  let currentIntervalSeconds = intervalSeconds;

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

    if (response.status === 429) {
      currentIntervalSeconds = Math.min(currentIntervalSeconds + 5, 30);
      await sleep(currentIntervalSeconds * 1000);
      continue;
    }

    if (response.status === 403 || response.status === 404) {
      await sleep(currentIntervalSeconds * 1000);
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

const runOpenAiOauthLogin = async (emitProgress) => {
  const device = await requestOpenAiDeviceCode();
  emitProgress?.({
    stage: "code_issued",
    userCode: device.userCode,
    verificationUrl: device.verificationUrl,
    verificationUrlComplete: device.verificationUrlComplete,
    openUrl: device.openUrl,
    manualCodeRequired: !device.verificationUrlComplete,
  });

  await shell.openExternal(device.openUrl || OPENAI_OAUTH_DEVICE_URL);
  emitProgress?.({ stage: "browser_opened" });

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

  emitProgress?.({ stage: "token_ready" });

  return {
    accessToken,
    userCode: device.userCode,
    verificationUrl: device.verificationUrl,
    verificationUrlComplete: device.verificationUrlComplete,
    openUrl: device.openUrl,
    manualCodeRequired: !device.verificationUrlComplete,
  };
};

const waitForProcessExit = (proc, timeoutMs = 2500) =>
  new Promise((resolveWait) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolveWait();
    };

    try {
      proc.once("exit", finish);
      proc.once("error", finish);
    } catch {
      finish();
      return;
    }

    setTimeout(finish, timeoutMs);
  });

const waitForUrl = async (probeUrls, { attempts = 15, delayMs = 1000 } = {}) => {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    for (const probeUrl of probeUrls) {
      try {
        const response = await fetch(probeUrl, {
          method: "GET",
          headers: { accept: "application/json" },
        });
        if (response.ok) {
          return true;
        }
      } catch {
      }
    }

    if (attempt + 1 < attempts) {
      await sleep(delayMs);
    }
  }

  return false;
};

const defaultProxyWorkingDir = () => {
  try {
    return app.getPath("userData");
  } catch {
    return process.cwd();
  }
};

const isCmd = (cmd) => {
  const check = process.platform === "win32" ? "where" : "which";
  return spawnSync(check, [cmd], { stdio: "ignore" }).status === 0;
};

const getPrimaryCommandToken = (command) => {
  const match = String(command || "").match(/^\s*(?:"([^"]+)"|(\S+))/);
  if (!match) {
    return "";
  }
  return match[1] || match[2] || "";
};

const resolveBackendExecutable = (executablePath) => {
  if (!executablePath) {
    return "";
  }

  if (existsSync(executablePath)) {
    return executablePath;
  }

  const resolvedPath = resolve(REPO_ROOT, executablePath);
  if (existsSync(resolvedPath)) {
    return resolvedPath;
  }

  return "";
};

const isCodexProxyReachable = async (chatUrl) => {
  const probeUrls = codexProxyProbeUrls(chatUrl);
  if (probeUrls.length === 0) {
    return false;
  }
  return waitForUrl(probeUrls, { attempts: 1, delayMs: 0 });
};

const findCodexProxyCommand = () => {
  const isWin = process.platform === "win32";
  const binaryName = isWin ? "codex-proxy-server.exe" : "codex-proxy-server";
  const batName = "codex-proxy.bat";
  const resPath = typeof process.resourcesPath === "string" && process.resourcesPath
    ? process.resourcesPath
    : null;
  const appDir = __dirname;
  const repoRoot = resolve(appDir, "..");

  if (DEFAULT_CODEX_PROXY_COMMAND) {
    log(`[proxy] Using configured command: ${DEFAULT_CODEX_PROXY_COMMAND}`);
    return {
      cmd: DEFAULT_CODEX_PROXY_COMMAND,
      type: "shell",
      cwd: defaultProxyWorkingDir(),
    };
  }

  const candidates = [];

  if (resPath) {
    if (isWin) candidates.push({ path: join(resPath, "codex-proxy-win", batName), type: "bat" });
    candidates.push({ path: join(resPath, "codex-proxy-win", binaryName), type: "bin" });
    candidates.push({ path: join(resPath, "codex-proxy", binaryName), type: "bin" });
  }

  if (isWin) candidates.push({ path: join(appDir, "resources", "codex-proxy-win", batName), type: "bat" });
  candidates.push({ path: join(appDir, "resources", "codex-proxy-win", binaryName), type: "bin" });
  candidates.push({ path: join(appDir, "resources", "codex-proxy", binaryName), type: "bin" });
  if (isWin) candidates.push({ path: join(repoRoot, "dist", "codex-proxy-win", batName), type: "bat" });
  candidates.push({ path: join(repoRoot, "dist", "codex-proxy-win", binaryName), type: "bin" });
  candidates.push({ path: join(repoRoot, "dist", "codex-proxy", binaryName), type: "bin" });

  for (const candidate of candidates) {
    log(`[proxy] Checking: ${candidate.path} → ${existsSync(candidate.path) ? "FOUND" : "not found"}`);
    if (existsSync(candidate.path)) {
      return {
        cmd: candidate.path,
        type: candidate.type,
        cwd: dirname(candidate.path),
      };
    }
  }

  if (isCmd("codex-lb")) {
    log("[proxy] Fallback: codex-lb");
    return { cmd: "codex-lb", type: "shell", cwd: defaultProxyWorkingDir() };
  }

  if (isCmd("uvx")) {
    log("[proxy] Fallback: uvx codex-lb");
    return { cmd: "uvx codex-lb", type: "shell", cwd: defaultProxyWorkingDir() };
  }

  if (isCmd("uv")) {
    log("[proxy] Fallback: uv tool run codex-lb");
    return { cmd: "uv tool run codex-lb", type: "shell", cwd: defaultProxyWorkingDir() };
  }

  log("[proxy] No Codex proxy command found.");
  return null;
};

const startCodexProxy = async () => {
  if (!isCodexProxyAutoStartEnabled()) {
    log("[proxy] Auto-start skipped (HWPX_CODEX_PROXY_START=0)");
    return { started: false, skipped: true, reason: "disabled" };
  }

  if (!isCodexProxyProviderActive()) {
    return { started: false, skipped: true, reason: "provider_not_codex_proxy" };
  }

  const proxyUrl = currentCodexProxyUrl();
  if (!isLocalUrl(proxyUrl)) {
    log(`[proxy] Auto-start skipped for non-local proxy URL: ${proxyUrl}`);
    return { started: false, skipped: true, reason: "non_local_url", url: proxyUrl };
  }

  if (await isCodexProxyReachable(proxyUrl)) {
    log(`[proxy] Proxy already reachable at ${proxyUrl}`);
    return { started: false, reachable: true, url: proxyUrl };
  }

  if (codexProxyProcess && !codexProxyProcess.killed) {
    const ready = await waitForUrl(codexProxyProbeUrls(proxyUrl), {
      attempts: 6,
      delayMs: 500,
    });
    if (ready) {
      return { started: false, reachable: true, url: proxyUrl, pid: codexProxyProcess.pid };
    }
  }

  const found = findCodexProxyCommand();
  if (!found) {
    log(
      "[proxy] Unable to auto-start Codex proxy. Provide HWPX_CODEX_PROXY_COMMAND or bundle codex-proxy-win."
    );
    return { started: false, url: proxyUrl, error: "command_not_found" };
  }

  const { cmd, type, cwd } = found;
  const isWin = process.platform === "win32";
  let spawnCmd = cmd;
  let spawnArgs = [];

  if (type === "bat") {
    spawnCmd = "cmd.exe";
    spawnArgs = ["/c", `"${cmd}"`];
  }

  log(`[proxy] Starting Codex proxy: ${spawnCmd}`);
  log(`[proxy]   cwd: ${cwd}`);
  log(`[proxy]   type: ${type}`);

  try {
    codexProxyProcess = spawn(spawnCmd, spawnArgs, {
      cwd,
      shell: type !== "bin",
      windowsVerbatimArguments: isWin && type === "bat",
      env: {
        ...process.env,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });

    codexProxyProcess.stdout?.on("data", (d) => {
      const s = d.toString();
      process.stdout.write(`[proxy] ${s}`);
      const line = `[proxy/out] ${s.trim()}`;
      backendLog.push(line);
      appendBackendFileLog(line);
    });
    codexProxyProcess.stderr?.on("data", (d) => {
      const s = d.toString();
      process.stderr.write(`[proxy] ${s}`);
      const line = `[proxy/err] ${s.trim()}`;
      backendLog.push(line);
      appendBackendFileLog(line);
    });
    codexProxyProcess.on("error", (e) => {
      log(`[proxy] Spawn error: ${e.message}`);
      codexProxyProcess = null;
    });
    codexProxyProcess.on("exit", (code, signal) => {
      log(`[proxy] Exited: code=${code} signal=${signal}`);
      codexProxyProcess = null;
    });

    log(`[proxy] Process started (pid=${codexProxyProcess.pid})`);
  } catch (e) {
    log(`[proxy] Spawn failed: ${e.message}`);
    codexProxyProcess = null;
    return { started: false, url: proxyUrl, error: "spawn_failed" };
  }

  const ready = await waitForUrl(codexProxyProbeUrls(proxyUrl), {
    attempts: 20,
    delayMs: 1000,
  });
  if (ready) {
    log(`[proxy] Ready at ${proxyUrl}`);
  } else {
    log(`[proxy] Startup did not expose a healthy endpoint at ${proxyUrl}`);
  }

  return {
    started: codexProxyProcess !== null,
    ready,
    pid: codexProxyProcess?.pid ?? null,
    url: proxyUrl,
  };
};

const stopCodexProxy = async ({ waitForExit = false } = {}) => {
  if (!codexProxyProcess || codexProxyProcess.killed) return;
  const proc = codexProxyProcess;
  log("[proxy] Stopping Codex proxy...");
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      proc.kill("SIGTERM");
    }
  } catch (e) {
    log(`[proxy] Stop error: ${e.message}`);
  }

  if (waitForExit) {
    await waitForProcessExit(proc);
  }

  codexProxyProcess = null;
};

const syncCodexProxyLifecycle = async () => {
  if (!isCodexProxyProviderActive()) {
    await stopCodexProxy({ waitForExit: true });
    return { started: false, skipped: true, reason: "provider_not_codex_proxy" };
  }

  if (!isCodexProxyAutoStartEnabled()) {
    await stopCodexProxy({ waitForExit: true });
    return { started: false, skipped: true, reason: "disabled" };
  }

  if (!isLocalUrl(currentCodexProxyUrl())) {
    await stopCodexProxy({ waitForExit: true });
    return { started: false, skipped: true, reason: "non_local_url", url: currentCodexProxyUrl() };
  }

  return startCodexProxy();
};

const findBackendCommand = async () => {
  const explicitBackendExecutable = (process.env.HWPX_MCP_BACKEND_EXE || "").trim();
  if (explicitBackendExecutable) {
    const resolvedBackendExe = resolveBackendExecutable(explicitBackendExecutable);
    if (!resolvedBackendExe) {
      log(`Configured HWPX_MCP_BACKEND_EXE not found: ${explicitBackendExecutable}`);
      return null;
    }

    return {
      cmd: resolvedBackendExe,
      type: "bin",
      cwd: dirname(resolvedBackendExe),
      source: "explicit-executable",
    };
  }

  const hasExplicitBackendCommand = Object.prototype.hasOwnProperty.call(
    process.env,
    "HWPX_MCP_BACKEND_COMMAND"
  );
  if (hasExplicitBackendCommand) {
    return {
      cmd: String(process.env.HWPX_MCP_BACKEND_COMMAND || "").trim(),
      type: "shell",
      cwd: REPO_ROOT,
      source: "explicit-command",
    };
  }

  const isWin = process.platform === "win32";
  const binName = isWin ? "hwpx-mcp-backend.exe" : "hwpx-mcp-backend";
  const batName = "hwpx-mcp-backend.bat";
  const resPath = typeof process.resourcesPath === "string" && process.resourcesPath
    ? process.resourcesPath
    : null;
  const appDir = __dirname;

  const candidates = [];

  if (resPath) {
    if (isWin) candidates.push({ path: join(resPath, "backend-win", batName), type: "bat" });
    candidates.push({ path: join(resPath, "backend", binName), type: "bin" });
  }

  if (isWin) candidates.push({ path: join(appDir, "resources", "backend-win", batName), type: "bat" });
  candidates.push({ path: join(appDir, "resources", "backend", binName), type: "bin" });

  if (isWin) candidates.push({ path: join(REPO_ROOT, "dist", "hwpx-mcp-backend-win", batName), type: "bat" });
  candidates.push({ path: join(REPO_ROOT, "dist", "hwpx-mcp-backend", binName), type: "bin" });

  for (const c of candidates) {
    log(`Checking: ${c.path} → ${existsSync(c.path) ? "FOUND" : "not found"}`);
    if (existsSync(c.path)) {
      return {
        cmd: c.path,
        type: c.type,
        cwd: dirname(c.path),
        source: "bundled-backend",
      };
    }
  }

  try {
    const runtimeEnsure = await ensureAsync({ env: process.env });
    const managed = resolveManagedBackend(runtimeEnsure.pythonPath, process.env);
    const managedExecutable = getPrimaryCommandToken(managed.backendCommand);

    if (!managedExecutable || !existsSync(managedExecutable)) {
      log(
        `Managed runtime backend executable does not exist: ${managedExecutable || "<empty>"}`
      );
      return null;
    }

    return {
      cmd: managed.backendCommand,
      type: "shell",
      cwd: REPO_ROOT,
      source: "managed-runtime",
    };
  } catch (error) {
    log(`Managed runtime resolution failed: ${error.message}`);
  }

  log("No backend command found.");
  return null;
};

const isBackendManaged = () => process.env.HWPX_MCP_START_BACKEND !== "0";

const startBackend = async () => {
  if (!isBackendManaged()) {
    log("Backend start skipped (HWPX_MCP_START_BACKEND=0)");
    return;
  }

  const found = await findBackendCommand();
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

  const launchEnv = {
    ...process.env,
    ...backendEnvOverrides,
    MCP_TRANSPORT: "streamable-http",
    MCP_HOST,
    MCP_PORT,
    MCP_PATH,
    HWPX_LOCAL_MODEL_ID: effectiveEnv("HWPX_LOCAL_MODEL_ID", DEFAULT_LOCAL_MODEL_ID),
    HWPX_LOCAL_MODEL_HOME: effectiveEnv("HWPX_LOCAL_MODEL_HOME", defaultLocalModelHome()),
    HF_HOME: effectiveEnv("HF_HOME", defaultHfHome()),
  };

  if (found.source === "managed-runtime" || found.source === "bundled-backend") {
    delete launchEnv.PYTHONHOME;
    delete launchEnv.PYTHONPATH;
  }

  try {
    backendProcess = spawn(spawnCmd, spawnArgs, {
      cwd,
      shell: type !== "bin",
      windowsVerbatimArguments: isWin && type === "bat",
      env: launchEnv,
      stdio: ["ignore", "pipe", "pipe"],
    });

    backendProcess.stdout?.on("data", (d) => {
      const s = d.toString();
      process.stdout.write(`[backend] ${s}`);
      const line = `[out] ${s.trim()}`;
      backendLog.push(line);
      appendBackendFileLog(line);
    });
    backendProcess.stderr?.on("data", (d) => {
      const s = d.toString();
      process.stderr.write(`[backend] ${s}`);
      const line = `[err] ${s.trim()}`;
      backendLog.push(line);
      appendBackendFileLog(line);
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

const stopBackend = async ({ waitForExit = false } = {}) => {
  if (!backendProcess || backendProcess.killed) return;
  const proc = backendProcess;
  log("Stopping backend...");
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      proc.kill("SIGTERM");
    }
  } catch (e) {
    log(`Stop error: ${e.message}`);
  }

  if (waitForExit) {
    await waitForProcessExit(proc);
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
  mainWindow.webContents.on("did-finish-load", () => {
    emitAppUpdateStatus(appUpdateStatus);
  });

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
  managed: isBackendManaged(),
  running: backendProcess !== null && !backendProcess.killed,
  pid: backendProcess?.pid ?? null,
  url: BACKEND_URL,
   proxy: {
    managed: isCodexProxyAutoStartEnabled() && isCodexProxyProviderActive(),
    running: codexProxyProcess !== null && !codexProxyProcess.killed,
    pid: codexProxyProcess?.pid ?? null,
    url: currentCodexProxyUrl(),
  },
  logPath: resolveBackendLogFilePath(),
  log: backendLog.slice(-30),
}));

ipcMain.handle("app:update-status", () => appUpdateStatus);

ipcMain.handle("backend:restart", async (_, opts) => {
  setBackendCredentials(opts);
  const proxyStatus = await syncCodexProxyLifecycle();
  if (!isBackendManaged()) {
    log("Backend restart skipped because backend management is disabled.");
    return {
      restarted: false,
      managed: false,
      url: BACKEND_URL,
      pid: null,
      proxy: proxyStatus,
      message: "backend_management_disabled",
    };
  }

  await stopBackend({ waitForExit: true });
  if (process.platform === "win32") {
    await sleep(450);
  }
  await startBackend();
  return {
    restarted: backendProcess !== null,
    managed: true,
    url: BACKEND_URL,
    pid: backendProcess?.pid ?? null,
    proxy: proxyStatus,
    message: backendProcess !== null ? "backend_restarted" : "backend_start_failed",
  };
});

ipcMain.handle("auth:openai-oauth-login", async () => {
  const emitProgress = (payload) => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      return;
    }
    mainWindow.webContents.send("auth:openai-oauth-progress", payload);
  };

  try {
    emitProgress({ stage: "starting" });
    const login = await runOpenAiOauthLogin(emitProgress);
    setOptionalEnv("OPENAI_OAUTH_TOKEN", login.accessToken);
    setOptionalEnv("CODEX_OAUTH_TOKEN", login.accessToken);
    emitProgress({ stage: "completed", ...login });
    return { success: true, ...login };
  } catch (error) {
    emitProgress({
      stage: "failed",
      error: error instanceof Error ? error.message : String(error),
    });
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
});

// App lifecycle
app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  await syncCodexProxyLifecycle();
  await startBackend();
  createWindow();
  setupAutoUpdater();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  stopCodexProxy();
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopCodexProxy();
  stopBackend();
});
