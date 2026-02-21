const { spawnSync } = require("node:child_process");

const checkBinary = (name) => {
  const checker = process.platform === "win32" ? "where" : "which";
  return spawnSync(checker, [name], { stdio: "ignore" }).status === 0;
};

const run = (command, args) =>
  spawnSync(command, args, {
    stdio: "inherit",
  });

if (process.platform !== "linux") {
  process.exit(0);
}

if (checkBinary("wine")) {
  process.exit(0);
}

if (!checkBinary("apt-get")) {
  console.error("wine is required for Linux Windows packaging, but apt-get is unavailable.");
  process.exit(1);
}

if (!checkBinary("sudo")) {
  console.error("wine is required for Linux Windows packaging, but sudo is unavailable.");
  process.exit(1);
}

console.log("wine not found. Installing wine64...");

const updateResult = run("sudo", ["apt-get", "update"]);
if (updateResult.status !== 0) {
  process.exit(updateResult.status ?? 1);
}

const installResult = run("sudo", ["apt-get", "install", "-y", "wine64"]);
if (installResult.status !== 0) {
  process.exit(installResult.status ?? 1);
}

if (!checkBinary("wine")) {
  console.error("wine installation completed, but wine command is still unavailable.");
  process.exit(1);
}

console.log("wine installation complete.");
