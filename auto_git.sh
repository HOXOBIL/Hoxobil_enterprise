#!/bin/bash

cd "$(dirname "$0")"  # Go to the directory of the script

while true; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    
    git add .
    git commit -m "Auto-commit at $TIMESTAMP"
    git push

    echo "[$TIMESTAMP] Changes pushed to GitHub."

    sleep 5
done
