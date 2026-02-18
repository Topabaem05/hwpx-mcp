[CmdletBinding()]
param()

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$targets = @(
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pdm-build",
    "dist",
    "build",
    "electron-ui/node_modules",
    "electron-ui/out",
    "electron-ui/dist"
)

foreach ($target in $targets) {
    $path = Join-Path $repoRoot $target
    if (Test-Path $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "Removed: $target"
    }
}

Write-Host "Cleanup complete."
