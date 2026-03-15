const {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} = require("node:fs");
const { createHash } = require("node:crypto");
const { homedir } = require("node:os");
const { isAbsolute, join, resolve } = require("node:path");
const { spawnSync } = require("node:child_process");

const SCRIPT_DIR = __dirname;
const REPO_ROOT = resolve(SCRIPT_DIR, "..", "..");
const LOCAL_RUNTIME_DIR = join(SCRIPT_DIR, "runtime");
const REPO_RUNTIME_DIR = join(REPO_ROOT, "scripts", "runtime");

const resolveRuntimeFile = (name) => {
  const localCandidate = join(LOCAL_RUNTIME_DIR, name);
  if (existsSync(localCandidate)) {
    return localCandidate;
  }

  return join(REPO_RUNTIME_DIR, name);
};

const PYTHON_VERSION_FILE = resolveRuntimeFile("python-version.txt");
const UV_BOOTSTRAP_FILE = resolveRuntimeFile("uv-bootstrap.json");

const APP_RUNTIME_DIR = "hwpx-mcp";
const DEFAULT_BACKEND_COMMAND = "uv run hwpx-mcp";
const DEFAULT_FETCH_TIMEOUT_MS = 120_000;

class RuntimeManagerError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "RuntimeManagerError";
    this.reason = options.reason || "runtime-manager-error";
    this.exitCode = Number.isInteger(options.exitCode) ? options.exitCode : 1;
  }
}

const normalizePath = (value) => {
  if (typeof value !== "string") {
    return "";
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  return isAbsolute(trimmed) ? trimmed : resolve(process.cwd(), trimmed);
};

const quoteIfNeeded = (value) => {
  if (typeof value !== "string") {
    return "";
  }

  if (value.includes(" ")) {
    return `"${value}"`;
  }

  return value;
};

const parseCliArgs = (argv = process.argv.slice(2)) => {
  const command = argv[0] || "doctor";
  let json = false;
  let platformOverride = "";
  let skipSync = false;

  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--json") {
      json = true;
      continue;
    }

    if (token === "--skip-sync") {
      skipSync = true;
      continue;
    }

    if (token === "--platform") {
      const next = argv[index + 1];
      if (!next || next.startsWith("--")) {
        throw new RuntimeManagerError("Missing value for --platform.", {
          reason: "invalid-arguments",
        });
      }
      platformOverride = next.trim();
      index += 1;
      continue;
    }

    if (token.startsWith("--platform=")) {
      platformOverride = token.slice("--platform=".length).trim();
      continue;
    }

    throw new RuntimeManagerError(`Unknown argument: ${token}`, {
      reason: "invalid-arguments",
    });
  }

  return {
    command,
    json,
    platformOverride,
    skipSync,
  };
};

const readJsonFile = (filePath) => {
  const content = readFileSync(filePath, "utf8");
  return JSON.parse(content);
};

const readPinnedVersion = () => {
  if (!existsSync(PYTHON_VERSION_FILE)) {
    throw new RuntimeManagerError(
      `Missing managed Python pin file: ${PYTHON_VERSION_FILE}`,
      { reason: "missing-python-pin" }
    );
  }

  const pinnedVersion = readFileSync(PYTHON_VERSION_FILE, "utf8").trim();
  if (!pinnedVersion) {
    throw new RuntimeManagerError(
      `Managed Python pin file is empty: ${PYTHON_VERSION_FILE}`,
      { reason: "invalid-python-pin" }
    );
  }

  return pinnedVersion;
};

const readUvBootstrapMeta = () => {
  if (!existsSync(UV_BOOTSTRAP_FILE)) {
    throw new RuntimeManagerError(
      `Missing uv bootstrap metadata file: ${UV_BOOTSTRAP_FILE}`,
      { reason: "missing-uv-bootstrap" }
    );
  }

  try {
    return readJsonFile(UV_BOOTSTRAP_FILE);
  } catch (error) {
    throw new RuntimeManagerError(
      `Invalid uv bootstrap metadata file: ${error.message}`,
      { reason: "invalid-uv-bootstrap" }
    );
  }
};

const sha256ForFile = (filePath) => {
  const digest = createHash("sha256");
  digest.update(readFileSync(filePath));
  return digest.digest("hex");
};

const ensureDir = (dirPath) => {
  mkdirSync(dirPath, { recursive: true });
};

const runProcess = ({ command, args, env, reasonOnFailure }) => {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    env,
  });

  if (result.error) {
    throw new RuntimeManagerError(
      `Failed to launch ${command}: ${result.error.message}`,
      {
        reason: reasonOnFailure,
      }
    );
  }

  if (result.status !== 0) {
    const stderr = (result.stderr || "").trim();
    const stdout = (result.stdout || "").trim();
    const details = stderr || stdout || "command failed";
    throw new RuntimeManagerError(`Command failed: ${command} ${args.join(" ")} (${details})`, {
      reason: reasonOnFailure,
    });
  }

  return result;
};

const sanitizedRuntimeEnv = (env = process.env) => {
  const nextEnv = { ...env };
  delete nextEnv.PYTHONHOME;
  delete nextEnv.PYTHONPATH;
  delete nextEnv.VIRTUAL_ENV;

  for (const certVar of ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "PIP_CERT"]) {
    const value = (nextEnv[certVar] || "").trim();
    if (value && !existsSync(value)) {
      delete nextEnv[certVar];
    }
  }

  return nextEnv;
};

const downloadToFile = async (url, destinationPath) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_FETCH_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new RuntimeManagerError(
        `Failed to download ${url}: HTTP ${response.status}`,
        { reason: "download-failed" }
      );
    }

    const fileBuffer = Buffer.from(await response.arrayBuffer());
    writeFileSync(destinationPath, fileBuffer);
  } catch (error) {
    if (error instanceof RuntimeManagerError) {
      throw error;
    }

    const message = error && error.name === "AbortError"
      ? `Timed out downloading ${url}`
      : `Failed to download ${url}: ${error.message}`;
    throw new RuntimeManagerError(message, { reason: "download-failed" });
  } finally {
    clearTimeout(timeout);
  }
};

const detectPlatformId = (platform = process.platform, arch = process.arch) => {
  const normalizedArch = arch === "x64" || arch === "arm64" ? arch : "";
  if (!normalizedArch) {
    return `${platform}-${arch}`;
  }
  return `${platform}-${normalizedArch}`;
};

const isSupportedPlatform = (platformId, uvBootstrapMeta) => {
  return Boolean(uvBootstrapMeta && Object.prototype.hasOwnProperty.call(uvBootstrapMeta, platformId));
};

const getPlatformToken = (platformId) => {
  if (typeof platformId !== "string") {
    return "";
  }
  const parts = platformId.split("-");
  return parts[0] || "";
};

const defaultRuntimeHomeForPlatform = (platformId, env = process.env) => {
  const platformToken = getPlatformToken(platformId);
  const userHome = homedir();

  if (platformToken === "win32") {
    const localAppData = normalizePath(env.LOCALAPPDATA) || join(userHome, "AppData", "Local");
    return join(localAppData, APP_RUNTIME_DIR, "runtime");
  }

  if (platformToken === "darwin") {
    return join(userHome, "Library", "Application Support", APP_RUNTIME_DIR, "runtime");
  }

  const xdgDataHome = normalizePath(env.XDG_DATA_HOME) || join(userHome, ".local", "share");
  return join(xdgDataHome, APP_RUNTIME_DIR, "runtime");
};

const resolveRuntimeHome = (platformId, env = process.env) => {
  const overrideRuntimeHome = normalizePath(env.HWPX_RUNTIME_HOME || "");
  if (overrideRuntimeHome) {
    return {
      runtimeHome: overrideRuntimeHome,
      runtimeHomeOverrideUsed: true,
    };
  }

  return {
    runtimeHome: defaultRuntimeHomeForPlatform(platformId, env),
    runtimeHomeOverrideUsed: false,
  };
};

const resolveRuntimePaths = (runtimeHome, pinnedVersion, platformId) => {
  const platformToken = getPlatformToken(platformId);
  const windows = platformToken === "win32";

  const uvPath = windows
    ? join(runtimeHome, "uv", "uv.exe")
    : join(runtimeHome, "uv", "uv");

  const pythonPath = windows
    ? join(runtimeHome, "python", pinnedVersion, "python.exe")
    : join(runtimeHome, "python", pinnedVersion, "bin", "python3");

  const lockPath = join(runtimeHome, "runtime-manager.lock");
  const downloadsDir = join(runtimeHome, "downloads");
  const pythonRoot = join(runtimeHome, "python");
  const uvRoot = join(runtimeHome, "uv");
  const venvRoot = join(runtimeHome, "venv");
  const venvPath = join(venvRoot, pinnedVersion);

  return {
    uvPath,
    pythonPath,
    venvPath,
    lockPath,
    downloadsDir,
    pythonRoot,
    uvRoot,
    venvRoot,
  };
};

const getVenvPythonPath = (venvPath, platformId) => {
  const windows = getPlatformToken(platformId) === "win32";
  return windows
    ? join(venvPath, "Scripts", "python.exe")
    : join(venvPath, "bin", "python");
};

const runProbe = ({ pythonPath, env, name, args }) => {
  const result = spawnSync(pythonPath, args, {
    encoding: "utf8",
    env,
  });

  if (result.error) {
    return {
      name,
      ok: false,
      details: result.error.message,
    };
  }

  if (result.status !== 0) {
    const stderr = (result.stderr || "").trim();
    const stdout = (result.stdout || "").trim();
    return {
      name,
      ok: false,
      details: stderr || stdout || "probe failed",
    };
  }

  return {
    name,
    ok: true,
    details: (result.stdout || "").trim() || "ok",
  };
};

const readPythonVersion = ({ pythonPath, env }) => {
  const result = runProbe({
    pythonPath,
    env,
    name: "pythonVersion",
    args: ["-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
  });

  return result.ok ? result.details : "";
};

const runHealthProbes = ({ uvPath, pythonPath, venvPath, platformId, env, pinnedVersion, requireUv = true }) => {
  if (requireUv && !existsSync(uvPath) && !existsSync(pythonPath)) {
    return {
      health: "missing",
      reason: "runtime-missing",
      pythonVersion: "",
      probes: {
        venv: { ok: false, details: "venv missing" },
        ssl: { ok: false, details: "python missing" },
        pip: { ok: false, details: "python missing" },
        fastapi: { ok: false, details: "python missing" },
        hwpx_mcp: { ok: false, details: "python missing" },
      },
    };
  }

  if (requireUv && !existsSync(uvPath)) {
    return {
      health: "missing",
      reason: "uv-missing",
      pythonVersion: "",
      probes: {
        venv: { ok: false, details: "venv missing" },
        ssl: { ok: false, details: "python missing" },
        pip: { ok: false, details: "python missing" },
        fastapi: { ok: false, details: "python missing" },
        hwpx_mcp: { ok: false, details: "python missing" },
      },
    };
  }

  if (!existsSync(pythonPath)) {
    return {
      health: "missing",
      reason: "python-missing",
      pythonVersion: "",
      probes: {
        venv: { ok: false, details: "venv missing" },
        ssl: { ok: false, details: "python missing" },
        pip: { ok: false, details: "python missing" },
        fastapi: { ok: false, details: "python missing" },
        hwpx_mcp: { ok: false, details: "python missing" },
      },
    };
  }

  const pythonVersion = readPythonVersion({ pythonPath, env });
  if (!pythonVersion) {
    return {
      health: "broken",
      reason: "python-version-probe-failed",
      pythonVersion: "",
      probes: {
        venv: { ok: false, details: "venv missing" },
        ssl: { ok: false, details: "python probe failed" },
        pip: { ok: false, details: "python probe failed" },
        fastapi: { ok: false, details: "python probe failed" },
        hwpx_mcp: { ok: false, details: "python probe failed" },
      },
    };
  }

  if (pythonVersion !== pinnedVersion) {
    return {
      health: "broken",
      reason: "python-version-mismatch",
      pythonVersion,
      probes: {
        venv: { ok: false, details: "venv missing" },
        ssl: { ok: false, details: `expected ${pinnedVersion}, got ${pythonVersion}` },
        pip: { ok: false, details: `expected ${pinnedVersion}, got ${pythonVersion}` },
        fastapi: { ok: false, details: `expected ${pinnedVersion}, got ${pythonVersion}` },
        hwpx_mcp: { ok: false, details: `expected ${pinnedVersion}, got ${pythonVersion}` },
      },
    };
  }

  const venvPythonPath = getVenvPythonPath(venvPath, platformId);
  if (!existsSync(venvPythonPath)) {
    return {
      health: "missing",
      reason: "venv-missing",
      pythonVersion,
      probes: {
        venv: { ok: false, details: "venv python missing" },
        ssl: { ok: false, details: "venv missing" },
        pip: { ok: false, details: "venv missing" },
        fastapi: { ok: false, details: "venv missing" },
        hwpx_mcp: { ok: false, details: "venv missing" },
      },
    };
  }

  const venvProbe = runProbe({
    pythonPath: venvPythonPath,
    env,
    name: "venv",
    args: [
      "-c",
      "import sys; raise SystemExit(0 if sys.prefix != getattr(sys,'base_prefix',sys.prefix) else 1)",
    ],
  });
  const sslProbe = runProbe({ pythonPath: venvPythonPath, env, name: "ssl", args: ["-c", "import ssl"] });
  const pipProbe = runProbe({ pythonPath: venvPythonPath, env, name: "pip", args: ["-c", "import pip"] });
  const fastapiProbe = runProbe({
    pythonPath: venvPythonPath,
    env,
    name: "fastapi",
    args: ["-c", "import fastapi"],
  });
  const hwpxProbe = runProbe({
    pythonPath: venvPythonPath,
    env,
    name: "hwpx_mcp",
    args: ["-c", "import hwpx_mcp"],
  });

  const probes = {
    venv: { ok: venvProbe.ok, details: venvProbe.details },
    ssl: { ok: sslProbe.ok, details: sslProbe.details },
    pip: { ok: pipProbe.ok, details: pipProbe.details },
    fastapi: { ok: fastapiProbe.ok, details: fastapiProbe.details },
    hwpx_mcp: { ok: hwpxProbe.ok, details: hwpxProbe.details },
  };

  const failingProbe = Object.entries(probes).find(([, probe]) => !probe.ok);
  if (failingProbe) {
    return {
      health: "broken",
      reason: `${failingProbe[0]}-probe-failed`,
      pythonVersion,
      probes,
    };
  }

  return {
    health: "ok",
    reason: "runtime-ready",
    pythonVersion,
    probes,
  };
};

const walkForExecutable = (rootDir, targetFileNames, depthLimit = 4, depth = 0) => {
  if (!existsSync(rootDir) || depth > depthLimit) {
    return "";
  }

  const targetSet = new Set(targetFileNames);

  const entries = readdirSync(rootDir, { withFileTypes: true });
  for (const entry of entries) {
    const absolutePath = join(rootDir, entry.name);
    if (entry.isFile() && targetSet.has(entry.name)) {
      return absolutePath;
    }
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    const absolutePath = join(rootDir, entry.name);
    const found = walkForExecutable(absolutePath, targetFileNames, depthLimit, depth + 1);
    if (found) {
      return found;
    }
  }

  return "";
};

const findInstalledPythonPath = ({ runtimeHome, pinnedVersion, platformId, fallbackPath }) => {
  const platformToken = getPlatformToken(platformId);
  const windows = platformToken === "win32";
  const pythonRoot = join(runtimeHome, "python");

  if (!existsSync(pythonRoot)) {
    return fallbackPath;
  }

  const targetNames = windows ? ["python.exe"] : ["python3", "python3.11", "python"];
  const discoveredPath = walkForExecutable(pythonRoot, targetNames, 5);
  if (!discoveredPath) {
    return fallbackPath;
  }

  if (discoveredPath.includes(pinnedVersion)) {
    return discoveredPath;
  }

  const alternateNames = windows ? ["python.exe"] : ["python", "python3", "python3.11"];
  const alternatePath = walkForExecutable(pythonRoot, alternateNames, 5);
  if (alternatePath && alternatePath.includes(pinnedVersion)) {
    return alternatePath;
  }

  return discoveredPath || fallbackPath;
};

const ensureUvBinary = async ({ runtimeHome, platformId, uvBootstrapMeta, env }) => {
  const platformMeta = uvBootstrapMeta[platformId];
  if (!platformMeta || !platformMeta.url || !platformMeta.sha256) {
    throw new RuntimeManagerError(`Missing uv metadata for platform: ${platformId}`, {
      reason: "invalid-uv-bootstrap",
    });
  }

  const platformToken = getPlatformToken(platformId);
  const windows = platformToken === "win32";
  const uvPath = windows
    ? join(runtimeHome, "uv", "uv.exe")
    : join(runtimeHome, "uv", "uv");

  if (existsSync(uvPath)) {
    return {
      uvPath,
      uvAction: "reuse",
    };
  }

  const downloadsDir = join(runtimeHome, "downloads");
  const archiveFileName = platformMeta.url.split("/").pop() || `uv-${platformId}`;
  const archivePath = join(downloadsDir, archiveFileName);
  const extractDir = join(runtimeHome, `uv-extract-${Date.now()}`);

  ensureDir(downloadsDir);
  ensureDir(extractDir);

  try {
    await downloadToFile(platformMeta.url, archivePath);

    const expectedChecksum = env.HWPX_RUNTIME_TEST_BAD_CHECKSUM === "1"
      ? `bad-${platformMeta.sha256}`
      : platformMeta.sha256;
    const actualChecksum = sha256ForFile(archivePath);
    if (actualChecksum !== expectedChecksum) {
      throw new RuntimeManagerError(
        `Checksum mismatch for ${archiveFileName}: expected ${expectedChecksum}, got ${actualChecksum}`,
        { reason: "checksum-mismatch" }
      );
    }

    if (archiveFileName.endsWith(".zip")) {
      if (windows) {
        runProcess({
          command: "powershell",
          args: [
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            `Expand-Archive -Path '${archivePath.replace(/'/g, "''")}' -DestinationPath '${extractDir.replace(/'/g, "''")}' -Force`,
          ],
          env,
          reasonOnFailure: "extract-failed",
        });
      } else {
        runProcess({
          command: "unzip",
          args: ["-o", archivePath, "-d", extractDir],
          env,
          reasonOnFailure: "extract-failed",
        });
      }
    } else {
      runProcess({
        command: "tar",
        args: ["-xzf", archivePath, "-C", extractDir],
        env,
        reasonOnFailure: "extract-failed",
      });
    }

    const extractedUv = walkForExecutable(extractDir, windows ? ["uv.exe"] : ["uv"], 6);
    if (!extractedUv) {
      throw new RuntimeManagerError("Downloaded uv archive did not contain uv executable.", {
        reason: "extract-failed",
      });
    }

    ensureDir(join(runtimeHome, "uv"));
    copyFileSync(extractedUv, uvPath);
    if (!windows) {
      chmodSync(uvPath, 0o755);
    }

    return {
      uvPath,
      uvAction: "install",
    };
  } finally {
    rmSync(extractDir, { recursive: true, force: true });
  }
};

const ensurePythonInstalled = ({ runtimeHome, platformId, pinnedVersion, uvPath, env, fallbackPythonPath }) => {
  const pythonPathBefore = findInstalledPythonPath({
    runtimeHome,
    pinnedVersion,
    platformId,
    fallbackPath: fallbackPythonPath,
  });

  if (existsSync(pythonPathBefore)) {
    return {
      pythonPath: pythonPathBefore,
      pythonAction: "reuse",
    };
  }

  ensureDir(join(runtimeHome, "python"));
  ensureDir(join(runtimeHome, "uv-cache"));

  const uvEnv = {
    ...env,
    UV_PYTHON_INSTALL_DIR: join(runtimeHome, "python"),
    UV_CACHE_DIR: join(runtimeHome, "uv-cache"),
    UV_PYTHON_INSTALL_BIN: "0",
  };

  runProcess({
    command: uvPath,
    args: ["python", "install", pinnedVersion],
    env: uvEnv,
    reasonOnFailure: "python-install-failed",
  });

  const pythonPathAfter = findInstalledPythonPath({
    runtimeHome,
    pinnedVersion,
    platformId,
    fallbackPath: fallbackPythonPath,
  });

  if (!existsSync(pythonPathAfter)) {
    throw new RuntimeManagerError(
      `uv installed Python ${pinnedVersion}, but executable was not found under ${join(runtimeHome, "python")}`,
      { reason: "python-install-missing" }
    );
  }

  return {
    pythonPath: pythonPathAfter,
    pythonAction: "install",
  };
};

const resolveManagedBackend = (pythonPath, env = process.env) => {
  const explicitBackendExecutable = (env.HWPX_MCP_BACKEND_EXE || "").trim();
  if (explicitBackendExecutable) {
    const resolvedExecutable = normalizePath(explicitBackendExecutable) || explicitBackendExecutable;
    return {
      backendCommand: quoteIfNeeded(resolvedExecutable),
      overrideUsed: true,
      overrideType: "backend-exe",
    };
  }

  const hasExplicitBackendCommand = typeof env.HWPX_MCP_BACKEND_COMMAND === "string";
  const requestedBackendCommand = hasExplicitBackendCommand
    ? env.HWPX_MCP_BACKEND_COMMAND.trim()
    : "";

  if (hasExplicitBackendCommand && requestedBackendCommand) {
    return {
      backendCommand: requestedBackendCommand,
      overrideUsed: true,
      overrideType: "backend-command",
    };
  }

  if (hasExplicitBackendCommand && !requestedBackendCommand) {
    return {
      backendCommand: DEFAULT_BACKEND_COMMAND,
      overrideUsed: true,
      overrideType: "backend-command-empty",
    };
  }

  return {
    backendCommand: `${quoteIfNeeded(pythonPath)} -m hwpx_mcp.server`,
    overrideUsed: false,
    overrideType: "none",
  };
};

const trySystemPython = ({ env, pinnedVersion, platformId, uvPath, venvPath }) => {
  if (env.HWPX_ALLOW_SYSTEM_PYTHON !== "1") {
    return {
      pythonPath: "",
      source: "managed",
    };
  }

  const candidates = getPlatformToken(platformId) === "win32"
    ? ["python", "py"]
    : ["python3", "python"];

  for (const command of candidates) {
    const args = command === "py"
      ? ["-3.11", "-c", "import sys; print(sys.executable)"]
      : ["-c", "import sys; print(sys.executable)"];
    const executableResult = spawnSync(command, args, {
      encoding: "utf8",
      env,
    });
    if (executableResult.error || executableResult.status !== 0) {
      continue;
    }

    const discoveredPath = (executableResult.stdout || "").trim();
    if (!discoveredPath || !existsSync(discoveredPath)) {
      continue;
    }

    const probe = runHealthProbes({
      uvPath,
      pythonPath: discoveredPath,
      venvPath,
      platformId,
      env,
      pinnedVersion,
      requireUv: false,
    });

    if (probe.health === "ok" && probe.pythonVersion === pinnedVersion) {
      return {
        pythonPath: discoveredPath,
        source: "system",
      };
    }
  }

  return {
    pythonPath: "",
    source: "managed",
  };
};

const prepareManagedVenv = ({ pythonPath, uvPath, venvPath, runtimeHome, pinnedVersion, env, platformId }) => {
  const stagingPath = `${venvPath}.staging-${Date.now()}`;
  const backupPath = `${venvPath}.backup-${Date.now()}`;
  const hadExistingVenv = existsSync(venvPath);
  const managedEnv = sanitizedRuntimeEnv(env);
  const uvEnv = {
    ...managedEnv,
    UV_CACHE_DIR: join(runtimeHome, "uv-cache"),
    UV_PYTHON_INSTALL_DIR: join(runtimeHome, "python"),
    UV_PYTHON_INSTALL_BIN: "0",
  };

  ensureDir(resolve(venvPath, ".."));
  ensureDir(join(runtimeHome, "uv-cache"));
  rmSync(stagingPath, { recursive: true, force: true });
  rmSync(backupPath, { recursive: true, force: true });

  runProcess({
    command: uvPath,
    args: ["venv", "--python", pythonPath, stagingPath],
    env: uvEnv,
    reasonOnFailure: "venv-create-failed",
  });

  const stagingPythonPath = getVenvPythonPath(stagingPath, platformId);
  runProcess({
    command: uvPath,
    args: ["pip", "install", "--python", stagingPythonPath, "--upgrade", "pip"],
    env: uvEnv,
    reasonOnFailure: "venv-sync-failed",
  });
  runProcess({
    command: uvPath,
    args: ["pip", "install", "--python", stagingPythonPath, "-e", REPO_ROOT],
    env: uvEnv,
    reasonOnFailure: "venv-sync-failed",
  });

  const versionProbe = readPythonVersion({
    pythonPath: stagingPythonPath,
    env: managedEnv,
  });
  if (versionProbe !== pinnedVersion) {
    rmSync(stagingPath, { recursive: true, force: true });
    throw new RuntimeManagerError(
      `Managed venv Python mismatch: expected ${pinnedVersion}, got ${versionProbe || "unknown"}`,
      { reason: "venv-version-mismatch" }
    );
  }

  try {
    if (hadExistingVenv) {
      renameSync(venvPath, backupPath);
    }
    renameSync(stagingPath, venvPath);
    if (hadExistingVenv) {
      rmSync(backupPath, { recursive: true, force: true });
    }
  } catch (error) {
    if (!existsSync(venvPath) && existsSync(backupPath)) {
      renameSync(backupPath, venvPath);
    }
    rmSync(stagingPath, { recursive: true, force: true });
    throw new RuntimeManagerError(`Failed to swap managed venv: ${error.message}`, {
      reason: "venv-swap-failed",
    });
  }

  return {
    venvPath,
    venvAction: hadExistingVenv ? "repair" : "install",
  };
};

const doctor = ({ platformOverride = "", env = process.env } = {}) => {
  const pinnedVersion = readPinnedVersion();
  const uvBootstrapMeta = readUvBootstrapMeta();
  const platformId = platformOverride || detectPlatformId();
  if (!isSupportedPlatform(platformId, uvBootstrapMeta)) {
    throw new RuntimeManagerError(`Unsupported platform: ${platformId}`, {
      reason: "unsupported-platform",
      exitCode: 1,
    });
  }

  const { runtimeHome, runtimeHomeOverrideUsed } = resolveRuntimeHome(platformId, env);
  const {
    lockPath,
    uvPath,
    pythonPath: fallbackPythonPath,
    venvPath,
  } = resolveRuntimePaths(runtimeHome, pinnedVersion, platformId);

  const managedPythonPath = findInstalledPythonPath({
    runtimeHome,
    pinnedVersion,
    platformId,
    fallbackPath: fallbackPythonPath,
  });

  const fallback = trySystemPython({
    env,
    pinnedVersion,
    platformId,
    uvPath,
    venvPath,
  });
  const pythonPath = existsSync(managedPythonPath) ? managedPythonPath : fallback.pythonPath || managedPythonPath;
  const runtimeSource = fallback.source === "system" && pythonPath === fallback.pythonPath ? "system" : "managed";

  const backend = resolveManagedBackend(pythonPath, env);
  const healthState = runHealthProbes({
    uvPath,
    pythonPath,
    venvPath,
    platformId,
    env,
    pinnedVersion,
    requireUv: runtimeSource !== "system",
  });

  return {
    command: "doctor",
    pinnedVersion,
    pythonVersion: healthState.pythonVersion,
    platform: platformId,
    runtimeHome,
    lockPath,
    uvPath,
    pythonPath,
    venvPath,
    backendCommand: backend.backendCommand,
    overrideUsed: backend.overrideUsed,
    overrideType: backend.overrideType,
    runtimeSource,
    runtimeHomeOverrideUsed,
    health: healthState.health,
    reason: healthState.reason,
    probes: healthState.probes,
  };
};

const ensure = ({ platformOverride = "", env = process.env, skipSync = false } = {}) => {
  return ensureAsync({ platformOverride, env, skipSync });
};

const ensureAsync = async ({ platformOverride = "", env = process.env, skipSync = false } = {}) => {
  const snapshot = doctor({ platformOverride, env });
  const uvBootstrapMeta = readUvBootstrapMeta();

  ensureDir(snapshot.runtimeHome);

  const uvResult = await ensureUvBinary({
    runtimeHome: snapshot.runtimeHome,
    platformId: snapshot.platform,
    uvBootstrapMeta,
    env,
  });

  const pythonResult = ensurePythonInstalled({
    runtimeHome: snapshot.runtimeHome,
    platformId: snapshot.platform,
    pinnedVersion: snapshot.pinnedVersion,
    uvPath: uvResult.uvPath,
    env,
    fallbackPythonPath: snapshot.pythonPath,
  });

  const managedPaths = resolveRuntimePaths(snapshot.runtimeHome, snapshot.pinnedVersion, snapshot.platform);
  const venvPythonPath = getVenvPythonPath(managedPaths.venvPath, snapshot.platform);
  let venvAction = existsSync(venvPythonPath) ? "reuse" : "install";

  if (!skipSync) {
    const preSyncHealth = runHealthProbes({
      uvPath: uvResult.uvPath,
      pythonPath: pythonResult.pythonPath,
      venvPath: managedPaths.venvPath,
      platformId: snapshot.platform,
      env,
      pinnedVersion: snapshot.pinnedVersion,
    });

    if (preSyncHealth.health !== "ok") {
      const venvResult = prepareManagedVenv({
        pythonPath: pythonResult.pythonPath,
        uvPath: uvResult.uvPath,
        venvPath: managedPaths.venvPath,
        runtimeHome: snapshot.runtimeHome,
        pinnedVersion: snapshot.pinnedVersion,
        env,
        platformId: snapshot.platform,
      });
      venvAction = venvResult.venvAction;
    }
  }

  const backend = resolveManagedBackend(pythonResult.pythonPath, env);
  const healthState = skipSync
    ? {
      health: existsSync(uvResult.uvPath) && existsSync(pythonResult.pythonPath) ? "ok" : "missing",
      reason: "sync-skipped",
      pythonVersion: readPythonVersion({ pythonPath: pythonResult.pythonPath, env }),
      probes: {
        venv: { ok: false, details: "sync skipped" },
        ssl: { ok: false, details: "sync skipped" },
        pip: { ok: false, details: "sync skipped" },
        fastapi: { ok: false, details: "sync skipped" },
        hwpx_mcp: { ok: false, details: "sync skipped" },
      },
    }
    : runHealthProbes({
      uvPath: uvResult.uvPath,
      pythonPath: pythonResult.pythonPath,
      venvPath: managedPaths.venvPath,
      platformId: snapshot.platform,
      env,
      pinnedVersion: snapshot.pinnedVersion,
    });

  const installedSomething = uvResult.uvAction === "install"
    || pythonResult.pythonAction === "install"
    || venvAction === "install"
    || venvAction === "repair";
  const action = installedSomething
    ? (venvAction === "repair" ? "repair" : "install")
    : snapshot.health === "ok" ? "noop" : "reuse";

  return {
    ...snapshot,
    command: "ensure",
    action,
    uvAction: uvResult.uvAction,
    pythonAction: pythonResult.pythonAction,
    venvAction,
    pythonVersion: healthState.pythonVersion || snapshot.pinnedVersion,
    uvPath: uvResult.uvPath,
    pythonPath: pythonResult.pythonPath,
    venvPath: managedPaths.venvPath,
    backendCommand: backend.backendCommand,
    overrideUsed: backend.overrideUsed,
    overrideType: backend.overrideType,
    health: healthState.health,
    reason: healthState.reason,
    probes: healthState.probes,
  };
};

const repair = async ({ platformOverride = "", env = process.env } = {}) => {
  const snapshot = doctor({ platformOverride, env });
  if (snapshot.health === "ok") {
    return {
      ...snapshot,
      command: "repair",
      action: "noop",
      reason: "runtime-ready",
    };
  }

  const ensured = await ensureAsync({
    platformOverride,
    env,
    skipSync: false,
  });

  const reinstallReasons = new Set([
    "runtime-missing",
    "uv-missing",
    "python-missing",
    "venv-missing",
  ]);
  const repairAction = reinstallReasons.has(snapshot.reason) ? "reinstall" : "repair";

  return {
    ...ensured,
    command: "repair",
    action: repairAction,
    reason: ensured.health === "ok" ? ensured.reason : snapshot.reason,
  };
};

const executeCommand = (command, options) => {
  if (command === "doctor") {
    return doctor(options);
  }
  if (command === "ensure") {
    return ensure(options);
  }
  if (command === "repair") {
    return repair(options);
  }

  throw new RuntimeManagerError(
    `Unsupported command: ${command}. Use doctor, ensure, or repair.`,
    { reason: "invalid-command" }
  );
};

const printResult = (result, json) => {
  if (json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return;
  }

  const lines = [
    `command: ${result.command}`,
    `platform: ${result.platform}`,
    `pinnedVersion: ${result.pinnedVersion}`,
    `runtimeHome: ${result.runtimeHome}`,
    `uvPath: ${result.uvPath}`,
    `pythonPath: ${result.pythonPath}`,
    `backendCommand: ${result.backendCommand}`,
    `overrideUsed: ${result.overrideUsed}`,
    `health: ${result.health}`,
    `reason: ${result.reason}`,
  ];

  process.stdout.write(`${lines.join("\n")}\n`);
};

const printError = (error, json) => {
  const status = {
    pinnedVersion: (() => {
      try {
        return readPinnedVersion();
      } catch {
        return "";
      }
    })(),
    runtimeHome: normalizePath(process.env.HWPX_RUNTIME_HOME || "") || "",
    lockPath: "",
    uvPath: "",
    pythonPath: "",
    backendCommand: "",
    overrideUsed: false,
    health: "error",
    reason: error.reason || "runtime-manager-error",
    message: error.message,
  };

  if (json) {
    process.stderr.write(`${JSON.stringify(status, null, 2)}\n`);
    return;
  }

  process.stderr.write(`${error.message}\n`);
};

const runCli = async (argv = process.argv.slice(2), env = process.env) => {
  const options = parseCliArgs(argv);
  const result = await executeCommand(options.command, {
    platformOverride: options.platformOverride,
    env,
    skipSync: options.skipSync,
  });
  printResult(result, options.json);
  return result;
};

if (require.main === module) {
  runCli().catch((error) => {
    if (error instanceof RuntimeManagerError) {
      const json = process.argv.includes("--json");
      printError(error, json);
      process.exit(error.exitCode);
    }

    const fallbackError = new RuntimeManagerError(error.message, {
      reason: "runtime-manager-crash",
    });
    const json = process.argv.includes("--json");
    printError(fallbackError, json);
    process.exit(fallbackError.exitCode);
  });
}

module.exports = {
  APP_RUNTIME_DIR,
  DEFAULT_BACKEND_COMMAND,
  PYTHON_VERSION_FILE,
  UV_BOOTSTRAP_FILE,
  RuntimeManagerError,
  detectPlatformId,
  doctor,
  ensure,
  ensureAsync,
  executeCommand,
  parseCliArgs,
  readPinnedVersion,
  readUvBootstrapMeta,
  repair,
  resolveManagedBackend,
  resolveRuntimeHome,
  resolveRuntimePaths,
  runCli,
};
