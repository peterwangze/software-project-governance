#!/bin/bash
# E2E Governance Verification — runs against e2e-test-project
# Simulates real user scenarios. Design assumption: if this breaks, users break.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
E2E_DIR="$SCRIPT_DIR/../e2e-test-project"
PASS=0
FAIL=0

green() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
red() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo "=== E2E Governance Verification ==="
echo "Target: $E2E_DIR"
echo ""

# --- Category A: Project structure (new user after governance-init) ---
echo "--- Category A: Project structure ---"

[ -f "$E2E_DIR/CLAUDE.md" ] && green "CLAUDE.md exists" || red "CLAUDE.md missing"
[ -d "$E2E_DIR/.governance" ] && green ".governance/ exists" || red ".governance/ missing"
[ -f "$E2E_DIR/.governance/plan-tracker.md" ] && green "plan-tracker.md exists" || red "plan-tracker.md missing"
[ -f "$E2E_DIR/.governance/evidence-log.md" ] && green "evidence-log.md exists" || red "evidence-log.md missing"
[ -f "$E2E_DIR/.governance/decision-log.md" ] && green "decision-log.md exists" || red "decision-log.md missing"
[ -f "$E2E_DIR/.governance/risk-log.md" ] && green "risk-log.md exists" || red "risk-log.md missing"

# --- Category B: Bootstrap content (user gets full governance from day 1) ---
echo ""
echo "--- Category B: Bootstrap content ---"

if [ -f "$E2E_DIR/CLAUDE.md" ]; then
    grep -q "SELF-CHECK" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: SELF-CHECK present" || red "Bootstrap: SELF-CHECK missing"
    grep -q "Governance Bootstrap" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: Governance Bootstrap section present" || red "Bootstrap: missing"
    grep -q "AskUserQuestion" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: AskUserQuestion rule present" || red "Bootstrap: AskUserQuestion missing"
    grep -q "阶段跳跃防护" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: stage jump protection present" || red "Bootstrap: stage jump missing"
    grep -q "收工前检查" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: session end checklist present" || red "Bootstrap: session end missing"
    grep -q "版本变化自动检测" "$E2E_DIR/CLAUDE.md" && green "Bootstrap: version change detection present" || red "Bootstrap: version detection missing"
fi

# --- Category C: Plan-tracker structure (user has complete governance toolkit) ---
echo ""
echo "--- Category C: Plan-tracker completeness ---"

if [ -f "$E2E_DIR/.governance/plan-tracker.md" ]; then
    grep -q "## 版本规划" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: version planning section" || red "Plan-tracker: version planning missing"
    grep -q "## 需求跟踪矩阵" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: requirement traceability" || red "Plan-tracker: requirement traceability missing"
    grep -q "## 变更控制" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: change control section" || red "Plan-tracker: change control missing"
    grep -q "快速通道" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: fast track defined" || red "Plan-tracker: fast track missing"
    grep -q "项目配置" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: project config section" || red "Plan-tracker: config missing"
    grep -q "工作流版本" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: workflow version field" || red "Plan-tracker: version field missing"
    grep -q "操作权限模式" "$E2E_DIR/.governance/plan-tracker.md" && green "Plan-tracker: permission mode field" || red "Plan-tracker: permission mode missing"
fi

# --- Category D: Hook integrity (system-level enforcement) ---
echo ""
echo "--- Category D: Hook integrity ---"

if [ -d "$E2E_DIR/.git" ]; then
    [ -f "$E2E_DIR/.git/hooks/pre-commit" ] && green "pre-commit hook installed" || red "pre-commit hook missing"
    [ -f "$E2E_DIR/.git/hooks/post-commit" ] && green "post-commit hook installed" || red "post-commit hook missing"
    # Verify hooks are executable
    [ -x "$E2E_DIR/.git/hooks/pre-commit" ] && green "pre-commit hook executable" || red "pre-commit hook not executable"
    [ -x "$E2E_DIR/.git/hooks/post-commit" ] && green "post-commit hook executable" || red "post-commit hook not executable"
else
    red "E2E project .git/ missing — re-init with: cd e2e-test-project && git init"
fi

# --- Summary ---
echo ""
echo "=== Result: $PASS passed, $FAIL failed ==="

if [ $FAIL -gt 0 ]; then
    echo "ACTION: Fix failures above. These represent real user-facing gaps."
    exit 1
else
    echo "All E2E checks passed. User experience intact."
    exit 0
fi
