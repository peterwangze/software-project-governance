#!/bin/bash
# pre-commit governance hook — installed by software-project-governance
# Runs BEFORE every git commit. BLOCKS commits that don't meet governance criteria.
# Design assumption: agent WILL NOT follow rules voluntarily. System MUST enforce.

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

# --- Check if governance is initialized ---
if [ ! -f "$REPO_ROOT/.governance/plan-tracker.md" ]; then
    # Not initialized — allow commit without governance checks
    exit 0
fi

# --- Step 1: Extract task ID from commit message ---
COMMIT_MSG_FILE="$1"
if [ -z "$COMMIT_MSG_FILE" ]; then
    # No commit message file (e.g., commit -m used, message is in stdin)
    COMMIT_MSG=$(cat)
else
    COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")
fi

# Extract task ID: first line, word before ":" that matches UPPERCASE-NUMBERS
FIRST_LINE=$(echo "$COMMIT_MSG" | head -1)
TASK_ID=$(echo "$FIRST_LINE" | sed -n 's/^\([A-Z][A-Z]*-[0-9][0-9]*\):.*/\1/p')

# --- Step 2: Task ID must be present ---
if [ -z "$TASK_ID" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  GOVERNANCE BLOCKED: Commit message has NO task ID.         ║"
    echo "║                                                            ║"
    echo "║  Every commit MUST reference a plan-tracker task.           ║"
    echo "║  Format: 'AUDIT-XXX: description' or 'FIX-XXX: description' ║"
    echo "║                                                            ║"
    echo "║  Action: Add task to plan-tracker, then use its ID.         ║"
    echo "║  Emergency bypass: git commit --no-verify                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi

# --- Step 3: Task MUST exist in plan-tracker ---
if ! grep -q "| $TASK_ID |" "$REPO_ROOT/.governance/plan-tracker.md" 2>/dev/null; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  GOVERNANCE BLOCKED: Task '$TASK_ID' not in plan-tracker.  ║"
    echo "║                                                            ║"
    echo "║  You are committing work that was never planned.            ║"
    echo "║  This violates M7.5: Pre-Task Protocol.                     ║"
    echo "║                                                            ║"
    echo "║  Action: Add '$TASK_ID' to .governance/plan-tracker.md      ║"
    echo "║          THEN retry the commit.                             ║"
    echo "║  Emergency bypass: git commit --no-verify                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi

# --- Step 4: Check evidence exists (WARN only — don't block) ---
if [ -f "$REPO_ROOT/.governance/evidence-log.md" ]; then
    if ! grep -qE "$TASK_ID" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null; then
        echo ""
        echo "⚠️  GOVERNANCE: Task '$TASK_ID' has no evidence yet."
        echo "   Commit allowed, but MUST add evidence to .governance/evidence-log.md"
        echo "   in the same session. post-commit hook will remind you."
        echo ""
    fi
fi

# --- Step 5: Check if commit message references work in progress ---
if grep -qiE "wip|work in progress|临时|tmp|temp" <<< "$COMMIT_MSG"; then
    echo ""
    echo "⚠️  GOVERNANCE: Commit message indicates WIP/TEMP work."
    echo "   This is fine for local branches but should be squashed before merge."
    echo ""
fi

# All checks passed
exit 0
