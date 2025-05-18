#!/bin/bash

# Exit script if any command fails
set -e

# Get commit message or use timestamp
COMMIT_MSG=${1:-"Auto-commit on $(date '+%Y-%m-%d %H:%M:%S')"}

echo "Ì¥Ñ Adding changes..."
git add .

# Check if there are any changes to commit
if git diff-index --quiet HEAD --; then
  echo "‚úÖ No changes to commit."
else
  echo "Ì≥ù Committing with message: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"
fi

# Check if branch has upstream set
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)

if [ -z "$UPSTREAM" ]; then
  echo "Ìºê Setting upstream and pushing..."
  git push --set-upstream origin main
else
  echo "Ì∫Ä Pushing to $UPSTREAM"
  git push
fi

echo "‚úÖ Done!"


