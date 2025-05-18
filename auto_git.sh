#!/bin/bash

COMMIT_MSG=${1:-"Auto-commit on $(date '+%Y-%m-%d %H:%M:%S')"}

git add .
git commit -m "$COMMIT_MSG"
git push --set-upstream origin main
