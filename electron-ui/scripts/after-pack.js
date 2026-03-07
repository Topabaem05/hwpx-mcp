const { join } = require("node:path");
const { chmodSync, existsSync } = require("node:fs");

exports.default = async function afterPack(context) {
  if (process.platform === "win32") {
    return;
  }

  const backendDir = join(context.appOutDir, "resources", "backend");
  const binaryPath = join(backendDir, "hwpx-mcp-backend");
  const codexProxyDir = join(context.appOutDir, "resources", "codex-proxy");
  const codexProxyBinaryPath = join(codexProxyDir, "codex-proxy-server");

  if (existsSync(binaryPath)) {
    chmodSync(binaryPath, 0o755);
    console.log(`Set executable permission on ${binaryPath}`);
  }

  if (existsSync(codexProxyBinaryPath)) {
    chmodSync(codexProxyBinaryPath, 0o755);
    console.log(`Set executable permission on ${codexProxyBinaryPath}`);
  }
};
