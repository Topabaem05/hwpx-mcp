const { copyFileSync, createWriteStream, existsSync, mkdirSync, renameSync, rmSync, statSync } = require("node:fs");
const { get } = require("node:https");
const { dirname, resolve } = require("node:path");

const VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe";
const OUTPUT_PATH = resolve(__dirname, "../../dist/windows-prereqs/vc_redist.x64.exe");
const INSTALLER_HELPER_SOURCE = resolve(__dirname, "install-local-model.py");
const INSTALLER_HELPER_DEST = resolve(__dirname, "../../dist/windows-prereqs/install-local-model.py");

function download(url, destination) {
  return new Promise((resolvePromise, rejectPromise) => {
    const request = get(url, (response) => {
      const statusCode = response.statusCode ?? 0;
      if (statusCode >= 300 && statusCode < 400 && response.headers.location) {
        response.resume();
        download(response.headers.location, destination).then(resolvePromise, rejectPromise);
        return;
      }

      if (statusCode !== 200) {
        response.resume();
        rejectPromise(new Error(`Failed to download VC++ redistributable: HTTP ${statusCode}`));
        return;
      }

      const tempPath = `${destination}.tmp`;
      const fileStream = createWriteStream(tempPath);
      response.pipe(fileStream);

      fileStream.on("finish", () => {
        fileStream.close(() => {
          renameSync(tempPath, destination);
          resolvePromise();
        });
      });

      fileStream.on("error", (error) => {
        response.resume();
        fileStream.close(() => {
          rmSync(tempPath, { force: true });
          rejectPromise(error);
        });
      });
    });

    request.on("error", rejectPromise);
  });
}

async function main() {
  mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
  copyFileSync(INSTALLER_HELPER_SOURCE, INSTALLER_HELPER_DEST);

  if (existsSync(OUTPUT_PATH) && statSync(OUTPUT_PATH).size > 0) {
    console.log(`Using existing VC++ redistributable at ${OUTPUT_PATH}`);
    console.log(`Copied installer model helper to ${INSTALLER_HELPER_DEST}`);
    return;
  }

  console.log(`Downloading VC++ redistributable from ${VC_REDIST_URL}`);
  await download(VC_REDIST_URL, OUTPUT_PATH);
  console.log(`Saved VC++ redistributable to ${OUTPUT_PATH}`);
  console.log(`Copied installer model helper to ${INSTALLER_HELPER_DEST}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
