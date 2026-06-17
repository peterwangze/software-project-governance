# /governance — 确定性快速入口

`/governance` 是用户手动进入治理面板的统一入口。默认路径必须先走脚本、低 token、确定性：先运行一个只读 CLI，展示紧凑状态，再只基于记录事实继续推进。

## Fast-Start Contract

1. 解析 `WORKFLOW_HOME`，不得让 LLM 在长文档中搜索入口路径：
   - 优先 `SOFTWARE_PROJECT_GOVERNANCE_HOME`
   - 其次 `SPG_HOME`
   - 其次使用宿主暴露的已安装 plugin/runtime metadata
   - 最后回退到项目内 `skills/software-project-governance`
2. 运行：

```bash
python "$WORKFLOW_HOME/infra/verify_workflow.py" governance-fast-start --json
```

3. 解析 JSON envelope。字段包括 `scenario`、`trigger_mode`、`permission_mode`、`workflow_version`、`current_stage`、`gate_status`、`open_risk_count`、`carry_over_count`、`unfinished_work`、`source_facts`、`blocker_state`、`auto_continue`、`interrupt_boundary`、`hook_state`、`next_action`、`workflow_home`、`skill_entry_path`、`full_skill_load_required`、`full_skill_load_reason`、`no_overclaim_boundary`。
4. 默认 Scenario F/status/resume 路径不得读取或搜索 `skills/software-project-governance/SKILL.md`。`skill_entry_path` 只是后续升级路径事实，不是默认要加载的文件。
5. 只有 `full_skill_load_required=true`，或用户明确要求初始化、升级、诊断、深度路由细节、角色 Agent 分发规则时，才加载 `skill_entry_path` 或长场景参考。

## 默认 Scenario F 输出

当 envelope 显示已有治理状态时，输出紧凑状态面板 `Delivery Trust Snapshot`，至少包含：

- Resume state: `Existing governance state detected`
- Carry-over
- Open risks
- Unfinished work
- Source facts
- Blocker state
- Auto-continue
- Interrupt boundary
- Hooks
- Goal 或当前阶段
- Stage
- Gate/setup status
- Risk
- Evidence
- Next action
- Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work
- Question budget: no more than 3 non-critical questions before snapshot; deferred non-critical fields become assumptions
- Verification signal
- No-overclaim boundary

`Unfinished work` 必须来自 `Source facts`。没有事实时输出 `not found` 和 `do not invent`；不得从假设中创造新事项。

## 升级与打断规则

- `full_skill_load_required=true`：加载 `skill_entry_path`，进入完整 Coordinator 规则。
- `scenario` 为 `A_NEW_PROJECT_INIT` 或 `B_EXISTING_PROJECT_ONBOARDING`：路由到 `/governance-init`。
- hooks 缺失或 envelope 显示 blocker：在 `interrupt_boundary` 指定的位置使用 AskUserQuestion。
- `auto_continue=true`：自动继续记录中的任务，直到关键决策、阻塞、独立审查、发布边界或用户打断出现。

## 按需升级参考

工作流升级路径仍归 `/governance-init` 与完整 `SKILL.md` 处理；默认 fast-start 不展开细节。若进入升级路径，仍需覆盖持续归档触发检测与执行：先运行 `python "$WORKFLOW_HOME/infra/archive.py" migrate --auto --dry-run`，需要归档时运行 `python "$WORKFLOW_HOME/infra/archive.py" migrate --auto`，随后运行 `python "$WORKFLOW_HOME/infra/verify_workflow.py" check-archive-integrity`。归档完整性失败时，发布/版本 bump 收尾场景 MUST 阻断完成；无可归档数据时跳过归档。

## Coordinator 边界

Coordinator 仍负责用户交互、治理记录、任务闭环和 Agent Team 路由。产品代码修改仍需 Developer/Governance Developer 执行，并由独立 Reviewer 审查。完整路由细节不在本入口重复；完整路由表（19 行）位于 `skills/software-project-governance/SKILL.md`，仅在升级路径加载。

## Pack 与过度声明边界

Pack summary: Packs are capability modules; profiles are governance intensity presets.

Default packs: lite -> `governance-core`; standard -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`; strict -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise`.

Enabled packs: 从 profile/default pack summary 或 registry facts 得出；缺少事实时显示 unknown/not configured。

Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, quality gates, release gates, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready proof.

No-overclaim boundary: `/governance` fast-start 只是本地 hot-state routing signal；first-run demo/local-only 检查不需要 external credentials；no official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, universal/full runtime support, RISK closure, or 1.0.0 production-ready claim.

## Verification

本地验收信号：

```bash
python "$WORKFLOW_HOME/infra/verify_workflow.py" governance-fast-start --json
python "$WORKFLOW_HOME/infra/verify_workflow.py" governance-context --fail-on-issues
python "$WORKFLOW_HOME/infra/verify_workflow.py" first-run-demo --assert-snapshot
```
