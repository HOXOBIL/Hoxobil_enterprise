#!/bin/bash

# Exit on errors
set -e

while true
do
  COMMIT_MSG="Auto-commit on $(date '+%Y-%m-%d %H:%M:%S')"

  git add .

  # Only commit if there are changes
  if git diff-index --quiet HEAD --; then
    echo "⏳ No changes to commit..."
  else
    echo "📦 Committing: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG"
  fi

  # Push to upstream (auto-set if not defined)
  if git rev-parse --abbrev-ref --symbolic-full-name @{u} &>/dev/null; then
    git push
  else
    git push --set-upstream origin main
  fi

  echo "✅ Synced! Waiting 5 seconds..."
  sleep 5
done
