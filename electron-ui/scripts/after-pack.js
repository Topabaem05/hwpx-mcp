const { join } = require("node:path");
const { chmodSync, existsSync } = require("node:fs");

exports.default = async function afterPack(context) {
  if (process.platform === "win32") {
    return;
  }

  const backendDir = join(context.appOutDir, "resources", "backend");
  const binaryPath = join(backendDir, "hwpx-mcp-backend");

  if (existsSync(binaryPath)) {
    chmodSync(binaryPath, 0o755);
    console.log(`Set executable permission on ${binaryPath}`);
  }
};
