"""Validate workflow commands in an isolated copy of the product surface."""

from datetime import date
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import external_project_diagnostics as diagnostics


def plan_tracker(version):
    return f"""# External Validation Temporary Project

## 项目配置

- **项目目标**: Validate software-project-governance in a temporary external-project workspace without mutating the source target.
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: maximum-autonomy
- **工作流版本**: {version}
- **当前阶段**: 立项与目标定义（第 1 阶段）

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | → 调研 | pending | | |
| G2 | → 技术选型 | pending | | |
| G3 | → 环境搭建 | pending | | |
| G4 | → 架构设计 | pending | | |
| G5 | → 开发实现 | pending | | |
| G6 | → 测试 | pending | | |
| G7 | → 防护网与CI/CD | pending | | |
| G8 | → 版本发布 | pending | | |
| G9 | → 运营 | pending | | |
| G10 | → 维护 | pending | | |
| G11 | → 下一轮 | pending | | |

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| External validation temporary project | 立项 | 0 | 0 | 0 | 0 | G1 pending | {date.today().isoformat()} |

## 当前活跃事项

No active P0/P1/P2 tasks. This temporary workspace validates install surface and command execution only.

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |
|------|------|---------|---------|---------------|-----------|

### 版本 Gate（V-Gate）

| 检查项 | 判定标准 |
|--------|---------|
| 版本范围完成率 | ≥90% |
| Breaking Change 文档化 | VERSIONING + CHANGELOG |
| 版本号一致性 | verify PASSED |
| 未完成项处置 | 降级/移版本 |
| 用户文档更新 | README/CHANGELOG |

## 需求跟踪矩阵

| 需求ID | 描述 | 来源 | 优先级 | 关联任务 | 状态 | 验证方式 |
|--------|------|------|--------|---------|------|---------|

## 变更控制（临时任务纳入机制）

### 标准路径（FIX-228 实质化）
变更提出 → **依赖分析**（运行 `task-priority-analysis`，检查新任务是否阻塞/被阻塞） → **优先级判定**（P0/P1/P2，结合当前 in-flight 任务和版本依赖链） → **冲突检查**（是否与 in-flight 任务修改相同文件） → **版本适配**（确定目标版本） → 创建 task → 执行

### 快速通道（仅限治理记录范畴——.governance/ 文件修改）
最小入账（plan-tracker 加行） → 立即执行 → 事后补齐（evidence-log + check-governance） → Gate 审计

> **FIX-228 规则**：快速通道仅适用于 `.governance/` 治理记录修改（不涉及产品代码）。任何涉及产品代码（skills/**）的新任务 MUST 走标准路径——依赖分析 + 优先级判定 + 冲突检查不得跳过。
"""


def write_governance(workspace, target_facts, version, render_plan):
    gov = workspace / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(render_plan(version), encoding="utf-8")
    (gov / "decision-log.md").write_text("# Decision Log\n\n", encoding="utf-8")
    (gov / "evidence-log.md").write_text("# Evidence Log\n\n", encoding="utf-8")
    (gov / "risk-log.md").write_text("# Risk Log\n\n", encoding="utf-8")
    (gov / "session-snapshot.md").write_text(
        "# Session Snapshot\n\n"
        f"- session_date: {date.today().isoformat()}\n"
        "- purpose: external project validation temporary workspace\n"
        f"- source_target: {target_facts['target']}\n",
        encoding="utf-8",
    )
    (gov / "external-validation-target.json").write_text(
        json.dumps(target_facts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def copy_surface(workspace, source_root, tracked):
    if not tracked:
        raise RuntimeError("cannot discover source git-tracked files for external validation package")
    copied = []
    for rel in sorted(tracked):
        rel = rel.replace("\\", "/")
        if rel.startswith(".governance/") or rel.startswith(".git/"):
            continue
        src = source_root / rel
        if not src.is_file():
            continue
        dst = workspace / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def prepare_git(workspace):
    subprocess.run(["git", "init"], cwd=str(workspace), capture_output=True, text=True, timeout=20, check=True)
    subprocess.run(["git", "config", "user.email", "external-validation@example.invalid"],
                   cwd=str(workspace), capture_output=True, text=True, timeout=10, check=True)
    subprocess.run(["git", "config", "user.name", "External Validation Harness"],
                   cwd=str(workspace), capture_output=True, text=True, timeout=10, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"],
                   cwd=str(workspace), capture_output=True, text=True, timeout=10, check=True)
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "add", "-A"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--no-verify", "-m", "FIX-131 external validation baseline"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    hooks_src = workspace / "skills/software-project-governance/infra/hooks"
    hooks_dst = workspace / ".git/hooks"
    for hook_name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit"):
        hook_src = hooks_src / hook_name
        if hook_src.is_file():
            shutil.copy2(hook_src, hooks_dst / hook_name)


def run_command(workspace, args, timeout=120):
    verify_script = workspace / "skills/software-project-governance/infra/verify_workflow.py"
    try:
        result = subprocess.run(
            [sys.executable, str(verify_script)] + list(args),
            cwd=str(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "args": list(args),
            "exit_code": 124,
            "stdout_tail": "\n".join((exc.stdout or "").splitlines()[-20:]),
            "stderr_tail": f"command timed out after {timeout}s",
        }
    except OSError as exc:
        return {
            "args": list(args),
            "exit_code": 127,
            "stdout_tail": "",
            "stderr_tail": f"command failed to start: {exc}",
        }
    return {
        "args": list(args),
        "exit_code": result.returncode,
        "stdout_tail": "\n".join(result.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(result.stderr.splitlines()[-20:]),
    }


def validate_project(
    target, keep_workspace, workspace_parent, timeout, *, inspect_target,
    copy_surface, write_governance, prepare_git, run_command, commands, boundary,
):
    target_facts = diagnostics.target_facts(target)
    if not target_facts["exists"] or not target_facts["is_dir"] or target_facts["file_count"] <= 0:
        return {
            "pass": False,
            "workspace": None,
            "target": target_facts,
            "target_diagnostics": [],
            "surface_files": 0,
            "commands": [],
            "issues": ["target must be an existing directory with at least one non-generated file"],
            "no_overclaim_boundary": boundary,
        }

    target_path = Path(target).resolve()
    target_diagnostics = inspect_target(target_path)
    parent = Path(workspace_parent).resolve() if workspace_parent else None
    if parent and (parent == target_path or target_path in parent.parents):
        return {
            "pass": False,
            "workspace": None,
            "target": target_facts,
            "target_diagnostics": target_diagnostics,
            "surface_files": 0,
            "commands": [],
            "issues": ["workspace parent must not be the target directory or inside the target directory"],
            "no_overclaim_boundary": boundary,
        }
    workspace = Path(tempfile.mkdtemp(
        prefix="spg-external-validation-", dir=str(parent) if parent else None,
    ))
    try:
        copied = copy_surface(workspace)
        write_governance(workspace, target_facts)
        prepare_git(workspace)

        command_results = []
        issues = diagnostics.diagnostic_issues(target_diagnostics)
        for label, cmd_args in commands:
            result = run_command(workspace, cmd_args, timeout=timeout)
            result["label"] = label
            command_results.append(result)
            if result["exit_code"] != 0:
                issues.append(f"{label} exited {result['exit_code']}")

        return {
            "pass": len(issues) == 0,
            "workspace": str(workspace),
            "target": target_facts,
            "target_diagnostics": target_diagnostics,
            "surface_files": len(copied),
            "commands": command_results,
            "issues": issues,
            "no_overclaim_boundary": boundary,
        }
    finally:
        if not keep_workspace:
            # FIX-404: cleanup permission errors must not mask validation results.
            shutil.rmtree(workspace, ignore_errors=True)


def run_cli(args, validate):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    result = validate(
        args.target,
        keep_workspace=args.keep_workspace,
        workspace_parent=args.workspace_parent,
        timeout=args.timeout,
    )
    print()
    print("=== External Project Validation Harness ===")
    print(f"  Target:        {result['target']['target']}")
    print(f"  Target files:  {result['target']['file_count']}")
    print(f"  Surface files: {result['surface_files']}")
    if result.get("workspace"):
        print(f"  Workspace:     {result['workspace']}")
    if result.get("target_diagnostics"):
        print("  Target-native diagnostics:")
        for item in result["target_diagnostics"]:
            line = f":{item['line']}" if "line" in item else ""
            print(
                f"    [{item['status']}] {item['category']} "
                f"{item['path']}{line} - {item['message']}"
            )
    for command in result["commands"]:
        status = "PASS" if command["exit_code"] == 0 else "FAIL"
        print(f"  [{status}] {command['label']} (exit {command['exit_code']})")
        if command["exit_code"] != 0 and command.get("stderr_tail"):
            print(command["stderr_tail"])
    print(f"  Boundary:      {result['no_overclaim_boundary']}")
    print(f"  Result:        {'PASSED' if result['pass'] else 'FAILED'}")
    print()
    print("JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.fail_on_issues and not result["pass"]:
        sys.exit(1)
