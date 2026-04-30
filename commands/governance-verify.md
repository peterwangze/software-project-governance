# governance-verify — 治理健康检查

> **推荐使用 `/software-project-governance`**——自动检测异常并触发 Scenario E 诊断+修复。本命令保留为快捷方式。

对当前项目执行治理健康检查，发现证据缺口、Gate 不一致和风险过期等问题。

## 输入参数

此命令不接受任何输入参数。

## 执行流程

### Step 1: 检查是否已初始化
- **IF** `.governance/` 目录不存在 OR `.governance/plan-tracker.md` 不存在 → 返回错误 `VERIFY-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 文件完整性检查（类别 A）
- **IF** `.governance/plan-tracker.md` 存在 → PASS
- **IF** `.governance/evidence-log.md` 存在 → PASS
- **IF** `.governance/decision-log.md` 存在 → PASS
- **IF** `.governance/risk-log.md` 存在 → PASS
- 任一缺失 → 记录为 `missing_file` 错误

### Step 3: 证据完整性检查（类别 B）
对 plan-tracker 中每条状态为"已完成"的任务逐项检查：
- 在 evidence-log 中搜索对应的任务 ID
- **IF** 找到至少 1 条证据 → PASS
- **IF** 未找到任何证据 → 记录为 `missing_evidence`，任务 ID 列入缺口清单

### Step 4: Gate 一致性检查（类别 C）
- 遍历 plan-tracker Gate 状态跟踪表
- **IF** Gate 状态为 passed / passed-on-entry / passed-with-conditions → 检查 evidence-log 中是否存在关联该 Gate 的证据条目
  - **IF** 存在 → PASS
  - **IF** 不存在 → 记录为 `gate_evidence_gap`
- **IF** Gate 状态为 pending → 不检查（尚未执行）

### Step 5: 风险过期检查（类别 D）
- 读取 risk-log 中状态为"活跃"的风险条目
- **IF** 最后更新日期距今 > 7 天 → 记录为 `stale_risk`
- **IF** 最后更新日期距今 ≤ 7 天 → PASS

### Step 6: workflow 仓库专属检查（类别 E — 仅当适用时）
- **IF** 项目根目录存在 `scripts/verify_workflow.py` → 执行 `python scripts/verify_workflow.py`，捕获输出和退出码
  - **IF** 退出码 = 0 → PASS
  - **ELSE** → 记录为 `workflow_verify_failed`，附带脚本输出
- **IF** 不存在 → 跳过此检查

### Step 7: 汇总并输出健康报告

## 输出格式

### 必要字段
| 字段 | 类型 | 说明 | 示例 |
|-------|------|-------------|---------|
| overall_result | 枚举 | 总体结果 | PASSED / FAILED |
| total_checks | 数字 | 检查类别数 | 4 或 5 |
| passed_checks | 数字 | 通过的检查类别数 | 4 |
| files_present | 列表 | 存在的治理文件 | [plan-tracker, evidence-log, decision-log, risk-log] |
| missing_files | 列表 | 缺失的治理文件 | [] |
| missing_evidence_count | 数字 | 缺失证据的任务数 | 0 |
| missing_evidence_tasks | 列表 | 缺失证据的任务 ID 列表 | [] |
| gate_evidence_gaps | 列表 | Gate-证据不一致的 Gate 列表 | [] |
| stale_risks_count | 数字 | 过期风险数 | 0 |
| stale_risks | 列表 | 过期风险 ID 列表 | [] |
| workflow_verify_result | 字符串 | verify_workflow.py 结果（如有） | "PASSED" / "SKIPPED" / "FAILED: <详情>" |

### 输出模板

```
"{project_name}" 的治理健康检查

类别 A — 文件完整性:                   {通过/失败}
  {逐文件}  ✅ / ❌ {文件名}
类别 B — 证据完整性:                   {通过/失败}
  {若失败}  ❌ 缺失证据的任务: {task_ids}
类别 C — Gate 一致性:                  {通过/失败}
  {若失败}  ❌ 缺失证据的 Gate: {gate_ids}
类别 D — 风险新鲜度:                   {通过/失败}
  {若失败}  ❌ 过期风险（>7天）: {risk_ids}
{类别 E — 工作流脚本校验:               通过/失败/已跳过}
  {若适用}  输出: {脚本输出摘要}

总体: {通过/失败} — {passed}/{total} 项检查通过

{if FAILED}
需要处理的事项:
  {可操作的缺口清单}
```

## 错误码

| 代码 | 条件 | 用户消息 | Agent 动作 |
|------|-----------|-------------|-------------|
| VERIFY-ERR-001 | `.governance/` 或 `.governance/plan-tracker.md` 不存在 | "项目尚未初始化。运行 `/governance-init` 为此项目设置治理跟踪。" | 停止执行，不做任何检查 |

## 自校验

执行后，agent MUST 验证：
- [ ] overall_result 为 "PASSED" 或 "FAILED"（非 "maybe" 或 "mostly"）
- [ ] 每个"已完成"任务均已实际与 evidence-log 对照检查
- [ ] 每个活跃风险的最后更新日期均已与今天比较
- [ ] Gate 一致性检查覆盖了所有非 pending Gate
- [ ] 缺失项以具体任务/风险/Gate ID 列出（非模糊描述）
- [ ] 若运行了 verify_workflow.py，实际输出已包含在内
- [ ] "需要处理的事项"部分列出了具体可处理的缺口（非建议性文字）
