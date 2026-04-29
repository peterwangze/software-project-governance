#!/bin/bash
# prepare-commit-msg governance hook
# Saves the commit message so pre-commit can read it (Windows git bash workaround)
# On Windows, git commit -m doesn't pass $1 to pre-commit.

COMMIT_MSG_FILE="$1"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

if [ -n "$COMMIT_MSG_FILE" ] && [ -f "$COMMIT_MSG_FILE" ]; then
    # Save a copy that pre-commit can read
    cp "$COMMIT_MSG_FILE" "$REPO_ROOT/.git/GOV_COMMIT_MSG" 2>/dev/null
fi

exit 0
