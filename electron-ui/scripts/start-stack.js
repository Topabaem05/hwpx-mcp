const { spawn, spawnSync } = require("node:child_process");
const { join, resolve } = require("node:path");
const { existsSync } = require("node:fs");

const ELECTRON_UI_DIR = resolve(__dirname, "..");
const REPO_ROOT = resolve(ELECTRON_UI_DIR, "..");
const RUNTIME_MANAGER_SCRIPT = join(__dirname, "runtime-manager.js");

const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = process.env.MCP_PORT || "8000";
const MCP_PATH = process.env.MCP_PATH || "/mcp";
const requestedTransport = (process.env.MCP_TRANSPORT || "streamable-http").trim().toLowerCase();
const MCP_TRANSPORT = "streamable-http";
const disableSandbox = process.env.HWPX_ELECTRON_NO_SANDBOX === "1";
const autoInstallUiDeps = process.env.HWPX_ELECTRON_AUTO_INSTALL !== "0";
const argv = process.argv.slice(2);
const hasFlag = (name) => argv.includes(name);
const isEnvToggleEnabled = (value) => typeof value === "string" && value.trim() === "1";
const dryRunMode = hasFlag("--dry-run") || isEnvToggleEnabled(process.env.HWPX_RUNTIME_DRY_RUN);
const jsonOutput = hasFlag("--json") || isEnvToggleEnabled(process.env.HWPX_RUNTIME_JSON);
const printInfo = (message) => {
  if (!jsonOutput) {
    console.log(message);
  }
};
const backendUrl =
  process.env.HWPX_MCP_HTTP_URL || `http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}`;

const explicitBackendExecutable = (process.env.HWPX_MCP_BACKEND_EXE || "").trim();
const hasExplicitBackendCommand = Object.prototype.hasOwnProperty.call(
  process.env,
  "HWPX_MCP_BACKEND_COMMAND"
);
const requestedBackendCommand = hasExplicitBackendCommand
  ? process.env.HWPX_MCP_BACKEND_COMMAND
  : "";
const openWebUiUrl = process.env.OPEN_WEBUI_URL || "http://localhost:3000";
const runWithBackend = process.env.HWPX_MCP_START_BACKEND !== "0";
const uiPackageManager = (process.env.HWPX_ELECTRON_PKG_MANAGER || "").trim().toLowerCase();

const shell = process.platform === "win32";

const BUNDLED_BACKEND_BINARY_NAME =
  process.platform === "win32" ? "hwpx-mcp-backend.exe" : "hwpx-mcp-backend";

const BUNDLED_BACKEND_BAT_NAME = "hwpx-mcp-backend.bat";

const findBundledBackend = () => {
  const binaryCandidates = [
    join(ELECTRON_UI_DIR, "resources", "backend", BUNDLED_BACKEND_BINARY_NAME),
    join(REPO_ROOT, "dist", "hwpx-mcp-backend", BUNDLED_BACKEND_BINARY_NAME),
  ];

  const batCandidates = process.platform === "win32" ? [
    join(ELECTRON_UI_DIR, "resources", "backend-win", BUNDLED_BACKEND_BAT_NAME),
    join(REPO_ROOT, "dist", "hwpx-mcp-backend-win", BUNDLED_BACKEND_BAT_NAME),
  ] : [];

  try {
    const { app } = require("electron");
    if (app) {
      const resPath = process.resourcesPath || "";
      binaryCandidates.unshift(join(resPath, "backend", BUNDLED_BACKEND_BINARY_NAME));
      if (process.platform === "win32") {
        batCandidates.unshift(join(resPath, "backend-win", BUNDLED_BACKEND_BAT_NAME));
      }
    }
  } catch {
    // Not running inside Electron context; skip resourcesPath probe.
  }

  for (const candidate of binaryCandidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  for (const candidate of batCandidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
};

const isCommandAvailable = (command) => {
  const check = shell ? "where" : "which";
  return spawnSync(check, [command], { stdio: "ignore" }).status === 0;
};

const getPrimaryCommandToken = (command) => {
  const match = command.match(/^\s*(?:"([^"]+)"|(\S+))/);

  if (!match) {
    return "";
  }

  return match[1] || match[2] || "";
};

const isExecutableAvailable = (command) => {
  const executable = getPrimaryCommandToken(command);

  if (!executable) {
    return false;
  }

  if (existsSync(executable)) {
    return true;
  }

  return isCommandAvailable(executable);
};

const resolveUiPackageManager = () => {
  if (uiPackageManager && uiPackageManager !== "npm" && uiPackageManager !== "bunx") {
    throw new Error(
      `Unsupported HWPX_ELECTRON_PKG_MANAGER=${uiPackageManager}. ` +
        "Use only npm or bunx."
    );
  }

  const candidates = [];

  if (isCommandAvailable("npm")) {
    candidates.push({ command: "npm", args: ["install"] });
  }

  if (isCommandAvailable("bunx")) {
    candidates.push({ command: "bunx", args: ["npm", "install"] });
  }

  if (uiPackageManager) {
    const selected = candidates.find((candidate) => candidate.command === uiPackageManager);

    if (!selected) {
      throw new Error(
        `Could not find ${uiPackageManager} in PATH for HWPX_ELECTRON_PKG_MANAGER. ` +
          "Install npm or bunx before running npm/bunx-based install."
      );
    }

    return selected;
  }

  if (candidates.length > 0) {
    return candidates[0];
  }

  throw new Error(
    "Could not find npm or bunx for Electron UI dependency install. " +
      "Install Node.js (npm) or Bun (bunx) and retry."
  );
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

const resolveBackendSelection = () => {
  if (explicitBackendExecutable) {
    const resolvedBackendExe = resolveBackendExecutable(explicitBackendExecutable);

    if (!resolvedBackendExe) {
      throw new Error(
        `Could not find backend executable from HWPX_MCP_BACKEND_EXE=${explicitBackendExecutable}. ` +
          "Set HWPX_MCP_BACKEND_EXE to an existing binary path."
      );
    }

    return {
      backendCommand: resolvedBackendExe.includes(" ") ? `"${resolvedBackendExe}"` : resolvedBackendExe,
      source: "explicit-executable",
      overrideUsed: true,
    };
  }

  if (hasExplicitBackendCommand) {
    const normalizedCommand = String(requestedBackendCommand || "").trim();

    if (normalizedCommand && !isExecutableAvailable(normalizedCommand)) {
      throw new Error(
        `Backend command is not runnable: ${normalizedCommand}. ` +
          "Set HWPX_MCP_BACKEND_COMMAND to a valid executable on PATH or a full path command."
      );
    }

    return {
      backendCommand: normalizedCommand,
      source: "explicit-command",
      overrideUsed: true,
    };
  }

  const bundled = findBundledBackend();
  if (bundled) {
    printInfo(`Found bundled backend binary: ${bundled}`);
    return {
      backendCommand: bundled.includes(" ") ? `"${bundled}"` : bundled,
      source: "bundled-backend",
      overrideUsed: false,
    };
  }

  const runtimeEnsureResult = spawnSync(
    process.execPath,
    [RUNTIME_MANAGER_SCRIPT, "ensure", "--json"],
    {
      cwd: REPO_ROOT,
      env: process.env,
      encoding: "utf8",
    }
  );

  if (runtimeEnsureResult.status !== 0) {
    const raw = (runtimeEnsureResult.stdout || runtimeEnsureResult.stderr || "").trim();
    let message = "Managed runtime ensure failed.";

    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        message = parsed.message || parsed.error || raw;
      } catch {
        message = raw;
      }
    }

    throw new Error(message);
  }

  let managed;
  try {
    managed = JSON.parse(runtimeEnsureResult.stdout || "{}");
  } catch {
    throw new Error("Managed runtime ensure returned invalid JSON output.");
  }

  const managedExecutable = getPrimaryCommandToken(managed.backendCommand || "");
  if (!managedExecutable || !existsSync(managedExecutable)) {
    throw new Error(
      `Managed runtime backend executable does not exist: ${managedExecutable || "<empty>"}`
    );
  }

  return {
    backendCommand: managed.backendCommand,
    source: "managed-runtime",
    overrideUsed: Boolean(managed.overrideUsed),
  };
};

const sharedEnv = {
  ...process.env,
  MCP_TRANSPORT,
  MCP_HOST,
  MCP_PORT,
  MCP_PATH,
  HWPX_MCP_BACKEND_COMMAND: requestedBackendCommand,
  HWPX_MCP_HTTP_URL: backendUrl,
  OPEN_WEBUI_URL: openWebUiUrl,
};

const backendSelection = resolveBackendSelection();
const backendCommand = backendSelection.backendCommand;
sharedEnv.HWPX_MCP_BACKEND_COMMAND = backendCommand;

const stopProcess = (child) => {
  if (!child || child.killed) {
    return;
  }

  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(child.pid), "/f", "/t"], {
      stdio: "ignore",
    });
    return;
  }

  child.kill("SIGTERM");
};

if (requestedTransport !== MCP_TRANSPORT) {
  printInfo(
    `Overriding MCP_TRANSPORT=${requestedTransport} for Electron bootstrap; using ${MCP_TRANSPORT} instead.`
  );
}

if (!MCP_PATH.startsWith("/")) {
  throw new Error(`Invalid MCP_PATH=${MCP_PATH}. Expected an absolute path like /mcp.`);
}

let backendFailure = null;
let isBackendReady = false;

const waitForEndpoint = async () => {
  const probeUrls = [
    backendUrl,
    backendUrl.endsWith("/") ? backendUrl.slice(0, -1) : `${backendUrl}/`,
  ].filter((value, index, all) => value && all.indexOf(value) === index);

  let lastError = "not ready yet";

  for (let attempt = 1; attempt <= 30; attempt += 1) {
    if (backendFailure) {
      throw backendFailure;
    }

    for (const probeUrl of probeUrls) {
      try {
        const response = await fetch(probeUrl, {
          method: "GET",
          headers: {
            accept: "application/json, text/event-stream",
          },
        });

      if (response.status < 500) {
        printInfo(`Backend is ready after ${attempt} polling attempt(s).`);
        return;
      }

        lastError = `non-fatal HTTP status ${response.status} from ${probeUrl}`;
      } catch {
        lastError = `request failed for ${probeUrl}`;
      }

      await new Promise((resolve) => setTimeout(resolve, 750));
    }
  }

  throw new Error(`Backend did not become available at ${backendUrl}: ${lastError}`);
};

const installUiDependencies = () => {
  if (!autoInstallUiDeps) {
    return false;
  }

  const { command, args } = resolveUiPackageManager();

  printInfo(`Electron binary not found. Running ${command} ${args.join(" ")} in electron-ui...`);

  const result = spawnSync(command, args, {
    cwd: ELECTRON_UI_DIR,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    throw new Error(
      `Electron UI install command failed in electron-ui: ${command} ${args.join(" ")}. ` +
        "Install dependencies manually before retry."
    );
  }

  return true;
};

const launchBackend = () => {
  if (!runWithBackend) {
    printInfo("Skipping backend startup because HWPX_MCP_START_BACKEND=0.");
    return null;
  }

  printInfo(`Starting backend with: ${backendCommand}`);

  const child = spawn(backendCommand, [], {
    cwd: REPO_ROOT,
    shell: true,
    env: sharedEnv,
    stdio: "inherit",
  });

  child.on("exit", (code, signal) => {
    if (isBackendReady) {
      return;
    }

    if (code !== null && code !== 0) {
      backendFailure = new Error(
        `Backend exited with code ${code} before MCP endpoint became ready.`
      );
      return;
    }

    if (signal) {
      backendFailure = new Error(
        `Backend was terminated by signal ${signal} before MCP endpoint became ready.`
      );
      return;
    }

    backendFailure = new Error("Backend exited before MCP endpoint became ready.");
  });

  return child;
};

const electronBinary = join(
  ELECTRON_UI_DIR,
  "node_modules",
  ".bin",
  shell ? "electron.cmd" : "electron"
);

const launchElectron = () => {
  if (!existsSync(electronBinary)) {
    const didInstall = installUiDependencies();

    if (didInstall && !existsSync(electronBinary)) {
      throw new Error(
        `Electron binary not found at ${electronBinary} after npm install. Check electron setup in electron-ui.`
      );
    }

    if (!didInstall) {
      throw new Error(
        `Electron binary not found at ${electronBinary}. Run 'npm install' in electron-ui first.`
      );
    }
  }

  const args = [ELECTRON_UI_DIR];
  if (disableSandbox) {
    args.push("--no-sandbox");
  }

  return spawn(electronBinary, args, {
    cwd: ELECTRON_UI_DIR,
    shell,
    env: sharedEnv,
    stdio: "inherit",
  });
};

const printBootstrapSummary = () => {
  printInfo("Starting HWPX MCP Electron stack");
  printInfo(`MCP_HOST: ${MCP_HOST}`);
  printInfo(`MCP_PORT: ${MCP_PORT}`);
  printInfo(`MCP_PATH: ${MCP_PATH}`);
  printInfo(`MCP transport: ${requestedTransport} -> ${MCP_TRANSPORT}`);
  printInfo(`Backend URL: ${backendUrl}`);
  printInfo(`Backend start command: ${backendCommand}`);
  printInfo(`Let Electron manage backend start: ${runWithBackend}`);
};

const dryRunPayload = () => ({
  mode: "dry-run",
  source: backendSelection.source,
  overrideUsed: backendSelection.overrideUsed,
  backendCommand,
  backendUrl,
  mcpTransport: MCP_TRANSPORT,
  requestedTransport,
  runWithBackend,
});

const printDryRun = () => {
  const payload = dryRunPayload();
  if (jsonOutput) {
    process.stdout.write(`${JSON.stringify(payload)}\n`);
    return;
  }

  printInfo("Dry-run mode enabled; skipping Electron launch.");
  printInfo(`Backend source: ${payload.source}`);
  printInfo(`Backend command: ${payload.backendCommand}`);
};

const printFatal = (error) => {
  if (jsonOutput) {
    process.stderr.write(
      `${JSON.stringify({
        mode: dryRunMode ? "dry-run" : "launch",
        error: error.message,
      })}\n`
    );
    return;
  }

  console.error(error.message);
};

let electronProcess = null;

const stopAll = () => {
  stopProcess(electronProcess);
};

(async () => {
  try {
    if (dryRunMode) {
      printDryRun();
      process.exit(0);
    }

    printBootstrapSummary();
    electronProcess = launchElectron();
  } catch (error) {
    stopAll();
    printFatal(error);
    process.exit(1);
  }

  const cleanup = () => {
    stopAll();
  };

  process.on("SIGINT", () => {
    cleanup();
    process.exit(0);
  });

  process.on("SIGTERM", () => {
    cleanup();
    process.exit(0);
  });

  process.on("beforeExit", cleanup);

  electronProcess.on("exit", (code) => {
    cleanup();
    process.exit(code ?? 0);
  });
})();
