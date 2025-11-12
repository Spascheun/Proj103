#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <local-target-branch> <remote-name> <remote-branch> [--push]"
  exit 2
fi

TARGET="$1"
REMOTE="$2"
REMOTE_BRANCH="$3"
PUSH=false
if [ "${4:-}" = "--push" ]; then
  PUSH=true
fi

# Ensure we're inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository (run this inside your repo)."
  exit 1
fi

echo "Fetching from remote '$REMOTE'..."
git fetch "$REMOTE" --prune

echo "Stashing local changes (if any)..."
git stash push -u -m "pre-merge-stash-$(date +%s)" || true

echo "Checking out target branch '$TARGET'..."
git checkout "$TARGET"

echo "Updating target branch from its remote (if exists)..."
if git show-ref --verify --quiet "refs/remotes/$REMOTE/$TARGET"; then
  git pull --rebase "$REMOTE" "$TARGET"
else
  echo "No remote tracking branch $REMOTE/$TARGET found; skipping pull."
fi

echo "Merging remote branch '$REMOTE/$REMOTE_BRANCH' into '$TARGET'..."
# Use --no-ff to keep merge commit explicit
git merge --no-ff "$REMOTE/$REMOTE_BRANCH" || {
  echo "Merge reported conflicts. Resolve them in VS Code, then run:"
  echo "  git add <resolved-files>"
  echo "  git commit    # or git merge --continue if using rebase/merge tooling"
  echo "After resolving, you can run this script again or continue manually."
  echo "Stash is saved and can be popped with 'git stash pop' when ready."
  exit 0
}

if [ "$PUSH" = true ]; then
  echo "Pushing merged '$TARGET' to $REMOTE..."
  git push "$REMOTE" "$TARGET"
fi

echo "Attempting to pop previous stash (if any)..."
# attempt to pop stash created by this script; be careful if stash is empty
if git stash list | grep -q "pre-merge-stash"; then
  git stash pop || echo "Failed to pop stash automatically; resolve or pop manually."
else
  echo "No pre-merge stash found."
fi

echo "Merge completed successfully."
