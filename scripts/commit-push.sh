#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/commit-push.sh \"your commit message\" [remote] [branch]"
  echo "Example: ./scripts/commit-push.sh \"feat: add workflow helpers\""
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMMIT_MESSAGE="$1"
REMOTE="${2:-origin}"
BRANCH="${3:-$(git rev-parse --abbrev-ref HEAD)}"

git add -A
git commit -m "$COMMIT_MESSAGE"
git push "$REMOTE" "$BRANCH"
