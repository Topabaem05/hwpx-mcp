# Windows Release Actions

This document explains how the repository's Windows release GitHub Actions flow is configured and how to use it to publish the bundled Windows x64 installer.

## Workflow file

- Workflow: `.github/workflows/windows-x64-release.yml`
- Job name: `Windows x64 Release Build`
- Runner: `windows-latest`
- Main output: `HWPX.MCP-<version>-win-x64.exe`

## What the workflow does

The workflow builds a fully bundled Windows release and publishes the resulting assets to a GitHub release.

It runs these stages:

1. checks out the repository
2. installs Node.js and Python build dependencies
3. builds the bundled backend executable
4. builds the bundled Windows codex proxy payload
5. builds the Electron NSIS installer with `npm run build:win:bundle -- --x64`
6. verifies the backend and bundled codex proxy exist in `dist/electron-installer/win-unpacked/resources/`
7. smoke-tests the bundled codex proxy on `http://127.0.0.1:2455`
8. collects the installer, `latest.yml`, and `.blockmap`
9. uploads workflow artifacts
10. creates or updates the tagged GitHub release and uploads the release assets

## Required GitHub settings

Configure these repository settings before relying on the release workflow:

### 1. Actions permissions

The workflow uses `permissions: contents: write` and uploads release assets with `gh release upload`.

In the repository settings:

- open `Settings -> Actions -> General`
- set `Workflow permissions` to `Read and write permissions`

Without write permission, release creation and asset upload will fail even if the build succeeds.

### 2. Tag naming

Tag-triggered releases depend on tags matching `v*`.

Examples:

- `v4.0.0`
- `v4.1.0`

## Trigger modes

The workflow supports two ways to run.

### A. Push a release tag

Pushing a tag like `v4.0.0` automatically starts the release workflow and uses that tag for release upload.

Example:

```bash
git tag -a v4.0.0 -m "v4.0.0"
git push origin v4.0.0
```

### B. Manual `workflow_dispatch`

You can rerun the release build from any branch without moving the tag by dispatching the workflow manually and passing the existing release tag.

Example:

```bash
gh workflow run windows-x64-release.yml --repo Topabaem05/hwpx-mcp --ref wt/agent -f tag=v4.0.0
```

This is the preferred recovery path when the tag already exists and only the workflow or packaging logic changed.

## Local CLI authentication for manual dispatch

The workflow itself uses `${{ github.token }}` during the run, so no extra repository secret is required for normal release uploads.

However, if you trigger or inspect workflows from a local machine with `gh`, your local GitHub authentication must be able to:

- dispatch workflows
- view workflow runs
- create or inspect releases

Practical minimum for a classic PAT used with `gh`:

- `repo`
- `workflow`

If you use `gh auth login`, make sure the authenticated account has write access to the repository.

## Important implementation details

### Electron build publishing

The `Build bundled Windows x64 installer` step passes both of these environment variables:

- `GH_TOKEN: ${{ github.token }}`
- `GITHUB_TOKEN: ${{ github.token }}`

This is required because `electron-builder` needs a GitHub token when publishing release artifacts.

### Bundled codex proxy bootstrap

The Windows codex proxy bundle is created by:

- `scripts/build-windows-codex-proxy.ps1`
- `scripts/build-windows-codex-proxy.sh`

The current working setup depends on two important details:

1. the generated launcher clears inherited `PYTHONHOME` and `PYTHONPATH`
2. the PowerShell builder rewrites `python313._pth` as ASCII

These changes prevent the embedded Python runtime from failing during startup with `ModuleNotFoundError: encodings` on the Windows runner.

### Smoke test behavior

The smoke test in `.github/workflows/windows-x64-release.yml` validates:

- `/health` returns `status == "ok"`
- `/v1/models` contains a `data` field

It also captures proxy logs through `CODEX_PROXY_LOG_PATH` and prints the last log lines on failure.

## Expected outputs

Successful runs produce:

- installer: `dist/electron-installer/HWPX.MCP-<version>-win-x64.exe`
- updater metadata: `dist/electron-installer/latest.yml`
- updater blockmap: `dist/electron-installer/*.blockmap`

The release upload step publishes those files to the GitHub release for the selected tag.

## Recommended release procedure

1. confirm version metadata is updated
2. push the release branch changes
3. create and push the `v*` tag
4. watch the workflow run
5. if the tag run fails but the tag should stay fixed, patch the branch and rerun with `workflow_dispatch -f tag=<tag>`
6. verify the release page contains the installer, `latest.yml`, and `.blockmap`

## Useful commands

List recent release workflow runs:

```bash
gh run list --repo Topabaem05/hwpx-mcp --workflow windows-x64-release.yml --limit 5
```

Watch a run to completion:

```bash
gh run watch <run-id> --repo Topabaem05/hwpx-mcp --exit-status
```

Inspect the release assets:

```bash
gh release view v4.0.0 --repo Topabaem05/hwpx-mcp --json assets,url
```

## Troubleshooting

### `GitHub Personal Access Token is not set`

Check that the Electron build step still passes both `GH_TOKEN` and `GITHUB_TOKEN` from `${{ github.token }}`.

### Bundled codex proxy never becomes healthy

Check the printed proxy log from the smoke step first. The workflow already emits the last 200 lines from `CODEX_PROXY_LOG_PATH`.

### `encodings` import failure in the bundled proxy

Re-check the embedded Python bootstrap behavior in:

- `scripts/build-windows-codex-proxy.ps1`
- `scripts/build-windows-codex-proxy.sh`

The launcher must not inherit conflicting Python path variables, and the rewritten `python313._pth` must remain ASCII.

### Release assets missing even though the build succeeded

Check both of these:

- repository Actions permissions allow write access
- the run has a non-empty `RELEASE_TAG`

If you manually dispatch the workflow without a `tag` input, the workflow will build artifacts but skip release upload.
