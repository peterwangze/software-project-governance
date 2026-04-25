# governance-verify — 治理健康检查

对当前项目执行治理健康检查，发现证据缺口、Gate 不一致和风险过期等问题。

## Input Parameters

此命令不接受任何输入参数。

## Execution Flow

### Step 1: 检查是否已初始化
- **IF** `.governance/` 目录不存在 OR `.governance/plan-tracker.md` 不存在 → 返回错误 `VERIFY-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 文件完整性检查（Category A）
- **IF** `.governance/plan-tracker.md` 存在 → PASS
- **IF** `.governance/evidence-log.md` 存在 → PASS
- **IF** `.governance/decision-log.md` 存在 → PASS
- **IF** `.governance/risk-log.md` 存在 → PASS
- 任一缺失 → 记录为 `missing_file` 错误

### Step 3: 证据完整性检查（Category B）
对 plan-tracker 中每条状态为"已完成"的任务逐项检查：
- 在 evidence-log 中搜索对应的任务 ID
- **IF** 找到至少 1 条证据 → PASS
- **IF** 未找到任何证据 → 记录为 `missing_evidence`，任务 ID 列入缺口清单

### Step 4: Gate 一致性检查（Category C）
- 遍历 plan-tracker Gate 状态跟踪表
- **IF** Gate 状态为 passed / passed-on-entry / passed-with-conditions → 检查 evidence-log 中是否存在关联该 Gate 的证据条目
  - **IF** 存在 → PASS
  - **IF** 不存在 → 记录为 `gate_evidence_gap`
- **IF** Gate 状态为 pending → 不检查（尚未执行）

### Step 5: 风险过期检查（Category D）
- 读取 risk-log 中状态为"活跃"的风险条目
- **IF** 最后更新日期距今 > 7 天 → 记录为 `stale_risk`
- **IF** 最后更新日期距今 ≤ 7 天 → PASS

### Step 6: workflow 仓库专属检查（Category E — 仅当适用时）
- **IF** 项目根目录存在 `scripts/verify_workflow.py` → 执行 `python scripts/verify_workflow.py`，捕获输出和退出码
  - **IF** 退出码 = 0 → PASS
  - **ELSE** → 记录为 `workflow_verify_failed`，附带脚本输出
- **IF** 不存在 → 跳过此检查

### Step 7: 汇总并输出健康报告

## Output Format

### Required Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| overall_result | enum | 总体结果 | PASSED / FAILED |
| total_checks | number | 检查类别数 | 4 或 5 |
| passed_checks | number | 通过的检查类别数 | 4 |
| files_present | list | 存在的治理文件 | [plan-tracker, evidence-log, decision-log, risk-log] |
| missing_files | list | 缺失的治理文件 | [] |
| missing_evidence_count | number | 缺失证据的任务数 | 0 |
| missing_evidence_tasks | list | 缺失证据的任务 ID 列表 | [] |
| gate_evidence_gaps | list | Gate-证据不一致的 Gate 列表 | [] |
| stale_risks_count | number | 过期风险数 | 0 |
| stale_risks | list | 过期风险 ID 列表 | [] |
| workflow_verify_result | string | verify_workflow.py 结果（如有） | "PASSED" / "SKIPPED" / "FAILED: <details>" |

### Output Template

```
Governance Health Check for "{project_name}"

Category A — File Integrity:              {PASSED/FAILED}
  {for each file}  ✅ / ❌ {filename}
Category B — Evidence Completeness:        {PASSED/FAILED}
  {if failed}  ❌ Missing evidence for: {task_ids}
Category C — Gate Consistency:            {PASSED/FAILED}
  {if failed}  ❌ Gates with missing evidence: {gate_ids}
Category D — Risk Freshness:              {PASSED/FAILED}
  {if failed}  ❌ Stale risks (>7 days): {risk_ids}
{Category E — Workflow Script Verify:      PASSED/FAILED/SKIPPED}
  {if applicable}  Output: {script_output_summary}

Overall: {PASSED/FAILED} — {passed}/{total} checks passed

{if FAILED}
Action required:
  {actionable_list_of_gaps}
```

## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|-------------|
| VERIFY-ERR-001 | `.governance/` 或 `.governance/plan-tracker.md` 不存在 | "Project has not been initialized yet. Run `/governance-init` to set up governance tracking first." | 停止执行，不做任何检查 |

## Self-Validation

After execution, agent MUST verify:
- [ ] overall_result is either "PASSED" or "FAILED" (not "maybe" or "mostly")
- [ ] Every "已完成" task was actually checked against evidence-log
- [ ] Every active risk's last_updated date was compared to today
- [ ] Gate consistency check covered all non-pending gates
- [ ] Missing items are listed with specific task/risk/gate IDs (not vague descriptions)
- [ ] If verify_workflow.py was run, the actual output is   included
- [ ] Action required section lists concrete, addressable gaps (not advice)
