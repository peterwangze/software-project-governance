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
# On Windows git bash, $1 may be empty for 'git commit -m'. Try multiple sources.
COMMIT_MSG=""
# Source 1: explicit file argument (works for 'git commit' with editor)
if [ -n "$1" ] && [ -f "$1" ]; then
    COMMIT_MSG=$(cat "$1" 2>/dev/null)
fi
# Source 2: git's commit message file (works for some git versions)
if [ -z "$COMMIT_MSG" ] && [ -f "$REPO_ROOT/.git/COMMIT_EDITMSG" ]; then
    COMMIT_MSG=$(cat "$REPO_ROOT/.git/COMMIT_EDITMSG" 2>/dev/null)
fi

# Extract task ID from first line of whatever we got
FIRST_LINE=$(echo "$COMMIT_MSG" | head -1)
TASK_ID=$(echo "$FIRST_LINE" | grep -oE '^[A-Z]+-[0-9]+' || true)

# If we still can't get the commit message, skip blocking (post-commit will catch)
if [ -z "$COMMIT_MSG" ]; then
    echo "⚠️  GOVERNANCE: Cannot read commit message. Skipping pre-commit check."
    echo "   post-commit hook will verify governance."
    exit 0
fi

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
        echo "   Commit allowed, but MUST add evidence this session."
        echo ""
    fi
fi

# --- Step 4.5: Task-to-task evidence chain (跨任务防护) ---
# When starting a NEW task, verify previous task's evidence is complete
if [ -f "$REPO_ROOT/.governance/evidence-log.md" ] && [ -f "$REPO_ROOT/.governance/plan-tracker.md" ]; then
    PREV_TASK=$(git log -1 --format=%s 2>/dev/null | grep -oE '^[A-Z]+-[0-9]+' || true)
    if [ -n "$PREV_TASK" ] && [ "$PREV_TASK" != "$TASK_ID" ]; then
        # This is a different task from the last commit — check if previous is clean
        if ! grep -qE "$PREV_TASK" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null; then
            echo ""
            echo "╔══════════════════════════════════════════════════════════════╗"
            echo "║  M7.4 DEBT: Previous task '$PREV_TASK' has NO evidence.    ║"
            echo "║                                                            ║"
            echo "║  You are starting '$TASK_ID' while '$PREV_TASK' is          ║"
            echo "║  incomplete. Each task MUST be fully closed before moving   ║"
            echo "║  to the next. Evidence → check-governance → audit.          ║"
            echo "║                                                            ║"
            echo "║  Commit allowed, but MUST fix '$PREV_TASK' evidence first.  ║"
            echo "╚══════════════════════════════════════════════════════════════╝"
            echo ""
        fi
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
