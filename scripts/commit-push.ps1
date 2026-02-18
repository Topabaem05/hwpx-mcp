[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CommitMessage,
    [string]$Remote = "origin",
    [string]$Branch = ""
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not $Branch) {
    $Branch = git rev-parse --abbrev-ref HEAD
}

git add -A
git commit -m $CommitMessage
git push $Remote $Branch
