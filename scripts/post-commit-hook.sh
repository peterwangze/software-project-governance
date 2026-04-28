#!/bin/bash
# post-commit governance hook — installed by software-project-governance
# Fires after every git commit. Forces governance visibility at each commit point.

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

# --- Step 1: Extract task ID from commit message ---
COMMIT_MSG=$(git log -1 --format=%B)
TASK_ID=$(echo "$COMMIT_MSG" | grep -oE '[A-Z]+-[0-9]+' | head -1)

# --- Step 2: Check task traceability ---
if [ -z "$TASK_ID" ]; then
    echo ""
    echo "⚠️  GOVERNANCE: Commit message has NO task ID reference."
    echo "   Expected format: 'AUDIT-XXX: description' or 'FIX-XXX: description'"
    echo "   This commit is NOT traceable to plan-tracker tasks."
    echo "   Action: Update plan-tracker or amend commit message."
    echo ""
else
    # Check if evidence exists for this task (handles comma-separated and range IDs)
    if [ -f "$REPO_ROOT/.governance/evidence-log.md" ]; then
        if grep -qE "$TASK_ID" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null; then
            echo ""
            echo "✅ GOVERNANCE: Commit '$TASK_ID' — evidence found in evidence-log."
            echo ""
        else
            echo ""
            echo "⚠️  GOVERNANCE: Commit '$TASK_ID' has NO evidence entry yet."
            echo "   Action: Add evidence to .governance/evidence-log.md"
            echo ""
        fi
    fi
fi

# --- Step 3: Check if plan-tracker knows about this task ---
if [ -n "$TASK_ID" ] && [ -f "$REPO_ROOT/.governance/plan-tracker.md" ]; then
    if ! grep -q "| $TASK_ID |" "$REPO_ROOT/.governance/plan-tracker.md" 2>/dev/null; then
        echo "⚠️  GOVERNANCE: Task '$TASK_ID' not found in plan-tracker."
        echo "   This task was NOT recorded before work started."
        echo "   Action: Add task to plan-tracker or use correct task ID."
        echo ""
    fi
fi

# --- Step 4: Quick governance summary ---
if [ -f "$REPO_ROOT/scripts/verify_workflow.py" ]; then
    echo "--- Governance Quick Check ---"
    python "$REPO_ROOT/scripts/verify_workflow.py" check-governance 2>/dev/null | \
        grep -E "(Check [0-9]|PASS|WARN|issued)" | head -12
    echo "-------------------------------"
fi
