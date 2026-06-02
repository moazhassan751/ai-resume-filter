#!/usr/bin/env bash
# purge_git_history.sh
# WARNING: This rewrites git history. Coordinate with collaborators and back up first.
# Requires python git-filter-repo (pip install git-filter-repo)

set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "git not found"
  exit 1
fi
if ! python -c "import git_filter_repo" >/dev/null 2>&1; then
  echo "git-filter-repo not installed. Install with: pip install git-filter-repo"
  exit 2
fi

# Backup branch
git branch backup-before-purge

echo "Create a file 'secrets-to-remove.txt' with each secret on its own line."
read -p "Press Enter when ready..."

# Build replace file for filter-repo
REPLACE_FILE="filter-repo-replace.txt"
> "$REPLACE_FILE"
while read -r secret; do
  if [ -n "$secret" ]; then
    echo "$secret==REDACTED" >> "$REPLACE_FILE"
  fi
done < secrets-to-remove.txt

# Run filter-repo
git filter-repo --replace-text "$REPLACE_FILE"

echo "Filter complete. You must force-push to update remote."
echo "git push --force --all && git push --force --tags"

