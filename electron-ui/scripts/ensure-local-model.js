const { existsSync, mkdirSync, renameSync, rmSync, statSync } = require("node:fs");
const { resolve } = require("node:path");
const { spawnSync } = require("node:child_process");

const MODEL_ID = (process.env.HWPX_LOCAL_MODEL_ID || "Qwen/Qwen3.5-4B-Instruct").trim();
const OUTPUT_ROOT = resolve(__dirname, "../../dist/local-models");
const OUTPUT_DIR = resolve(OUTPUT_ROOT, MODEL_ID.replaceAll("/", "__"));

function resolvePythonBin() {
  const candidates = [];
  const override = (process.env.HWPX_PYTHON_BIN || "").trim();
  if (override) {
    candidates.push(override);
  }
  candidates.push("python", "python3");

  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["-c", "import sys; print(sys.executable)"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    if (result.status === 0) {
      return candidate;
    }
  }

  throw new Error("Python interpreter not found. Set HWPX_PYTHON_BIN or install python/python3.");
}

function ensureDirectory(dirPath) {
  mkdirSync(dirPath, { recursive: true });
}

function hasSnapshot(dirPath) {
  const configPath = resolve(dirPath, "config.json");
  const tokenizerConfigPath = resolve(dirPath, "tokenizer_config.json");
  return existsSync(configPath) && existsSync(tokenizerConfigPath);
}

function hasWeights(dirPath) {
  const candidateFiles = [
    "model.safetensors",
    "model.safetensors.index.json",
    "pytorch_model.bin",
    "pytorch_model.bin.index.json",
  ];
  return candidateFiles.some((fileName) => existsSync(resolve(dirPath, fileName)));
}

function hasTokenizerAssets(dirPath) {
  const candidateFiles = [
    "tokenizer.json",
    "vocab.json",
    "tokenizer.model",
  ];
  return candidateFiles.some((fileName) => existsSync(resolve(dirPath, fileName)));
}

function validateSnapshot(dirPath) {
  return hasSnapshot(dirPath) && hasWeights(dirPath) && hasTokenizerAssets(dirPath);
}

function runPythonDownload(outputDir) {
  const pythonBin = resolvePythonBin();
  const script = [
    "from huggingface_hub import snapshot_download",
    "import os",
    "repo_id = os.environ['HWPX_LOCAL_MODEL_ID']",
    "output_dir = os.environ['HWPX_LOCAL_MODEL_OUTPUT']",
    "snapshot_download(",
    "    repo_id=repo_id,",
    "    local_dir=output_dir,",
    ")",
  ].join("\n");

  const result = spawnSync(pythonBin, ["-c", script], {
    stdio: "inherit",
    env: {
      ...process.env,
      HWPX_LOCAL_MODEL_ID: MODEL_ID,
      HWPX_LOCAL_MODEL_OUTPUT: outputDir,
    },
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`Python snapshot download failed with exit code ${result.status}`);
  }
}

function main() {
  ensureDirectory(OUTPUT_ROOT);

  if (validateSnapshot(OUTPUT_DIR)) {
    const sizeMb = Math.round(statSync(resolve(OUTPUT_DIR, "config.json")).size / 1024);
    console.log(`Using existing bundled local model at ${OUTPUT_DIR} (config ${sizeMb} KiB)`);
    return;
  }

  const stagingDir = `${OUTPUT_DIR}.tmp`;
  rmSync(stagingDir, { recursive: true, force: true });
  ensureDirectory(stagingDir);

  console.log(`Downloading local model snapshot ${MODEL_ID} to ${OUTPUT_DIR}`);
  runPythonDownload(stagingDir);

  if (!validateSnapshot(stagingDir)) {
    throw new Error(`Local model snapshot incomplete at ${OUTPUT_DIR}`);
  }

  rmSync(OUTPUT_DIR, { recursive: true, force: true });
  renameSync(stagingDir, OUTPUT_DIR);

  console.log(`Bundled local model snapshot is ready at ${OUTPUT_DIR}`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
