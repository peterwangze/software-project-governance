# FIX-449 活动版本针代码审查 R0

- 日期：2026-10-16
- 结论：NEEDS_CHANGE
- unresolved_blockers=1
- 审查基准 HEAD：`a00105717935079c54ec30ed6e6c790e8bd97290`
- 待审对象：`skills/software-project-governance/infra/tests/test_verify_workflow.py` 的 FIX-449 差异及 `docs/diagnostics/fix-449-version-pins.md`。
- 被审测试文件字节 SHA-256：`652480e44320352325c1762c38aa473fed9d15ec51285a69f853d7df8d8abcd5`
- 测试文件 diff SHA-256：`b97b6b6f38678fbc2276fd367cba8b77cb503953bbe56069e56fea06e6c72fde`

## 结论依据与发现

**R0-F1 / P1 / BLOCKING：共享 PLAN 的既有消费者遗漏渲染，真实版本被 token 写入迁移账本。**

- 变更位置：`test_verify_workflow.py:25468` 起将四条共享 PLAN 的版本改成 token；受影响消费者 `FEAT093AuthorityLedgerReworkR0Tests._migrated_gov()` 在 **L25753** 仍直接写 `fixture.PLAN`，没有调用新的 `_gov()` 渲染路径。
- 事实：独立在 `resolve_entry.read_active_version` 分别返回 `0.98.0`、`0.99.0`、`1.0.0` 时调用该 helper，三次均 `plan_contains_tokens=True`；每次 `LedgerWriter(gov).state['tasks']` 的 FEAT-093、FEAT-094、FIX-442 的 `target_version` 均为字面值 `@@ACTIVE_VERSION@@`。
- 影响：`test_p3_3_dry_run_remigration_predicts_live_counts` 经过此路径，原来合法的版本数据现已变成未渲染模板。18 项及三版本运行仍绿，只证明计数断言不检查该失真；不能据此证明所有共享 fixture 消费路径都随权威版本派生。
- 建议：让 `_migrated_gov()` 复用统一渲染的 `_gov()`，或提取一个两处共用的 fixture 构造函数；补此消费者的无 token、三活动行版本相等、冲突版本不同回归。修复后复跑两个 class 并独立复审。

除 R0-F1 外未发现新增阻塞。主 `_gov()` 的替换顺序正确，冲突行从同 major 的下一 minor 派生并保持不同；缺锚负向 fixture 保持空事项、不改变拒收断言；性能数据仍为 31 行且没有放宽 2s/50ms 门。

## 五维度

| 维度 | 结论及事实 |
| --- | --- |
| 正确性 | 需修改：主路径三个活动版本、下一 minor 冲突版本及负向 fixture 的派生正确；共享 PLAN 的第二构造路径遗留 token，见 R0-F1。 |
| 安全性 | 本次差异通过：仅测试输入派生，无新增产品权限、输入执行或真实用户数据操作；真实 migration 都在隔离临时 fixture 中。 |
| 可维护性 | 需修改：一个共享模板有两个构造入口，但只有一处渲染，现有 helper 未统一；该遗漏是 R0-F1 同一问题。 |
| 性能 | 通过：每次 fixture 两次线性替换，低量级；原 31-task rebuild/单事务预算断言保持且真实运行通过。 |
| 测试覆盖 | 现有目标回归通过，但不足以批准：三次完整 class 均为 18 tests / OK；新增无 token 断言仅验证主 `_gov()`，没有验证 `_migrated_gov()`。 |

## 设计一致性与 AI 专项

设计对照：DEC-213③（`.governance/archive/decisions/decisions-v0.1.0-0.91.0.md:107`）要求测试版本从被测渲染源派生；主路径符合，第二消费者漏渲染尚未完整符合。未修改产品版本或新增 exemption。FEAT-093 的历史冲突披露、零丢失、幂等及坏行 fail-closed 断言没有被删除或放宽。

| AI 检查项 | 结论 |
| --- | --- |
| mock 残留 | 版本 mock 只用于输入边界测试，不模拟 migration 成功；真实 ledger API 执行。 |
| 硬编码返回值 | 无新增伪造成功返回；但模板 token 从第二消费者泄漏到真实账本输入，已列 R0-F1。 |
| 幻觉 API | `read_active_version`、`migrate` 和 `LedgerWriter` 均为现有真实 API，已运行。 |
| 未实现 TODO | 未发现本 diff 新增未实现占位逻辑。 |
| 过度实现 | 差异集中于测试输入与回归，不涉及无关产品功能。 |

## 独立真实验证

Windows Python 3.14.3；没有重复全套 suite。

1. 完整运行 `FEAT093AuthorityLedgerProjectionTests` 与 `FEAT093AuthorityLedgerReworkR0Tests`，在外层 mock 权威版本为 `0.98.0` / `0.99.0` / `1.0.0`：每轮 **18 tests / 0 failures / 0 errors / OK**，合计 54 tests；耗时分别 1.312s、1.306s、1.321s。
2. 对 `_migrated_gov()` 独立三版本探针：每轮 plan 残留 token、三条 registered task 的 `target_version` 都是 `@@ACTIVE_VERSION@@`，复现 R0-F1；临时 fixture 随上下文清理。
3. `checks.version.scan_static_version_pins(Path.cwd())`：本次观察输出 `[]`。目标文件零 WARN；整树结果受并行 FIX-453 exemption 修复影响，不能全部归因本票。诊断文档记录的原始 1 WARN 与当时静态测试失败没有被包装为通过。
4. `git diff --check -- skills/software-project-governance/infra/tests/test_verify_workflow.py`：exit 0。

未验证 GitHub Python 3.11、全流水线、版本收尾或发布；上述目标通过不替代这些验收。

## 硬门槛与后续

P0=0，P1=1（未解决），P2=0，P3=0；五维度、分级、设计一致性及 AI 五项检查完成。R0-F1 关闭并复审前不批准 A 单元提交。B 的 marker 单元与 C 的 CI 依赖单元有独立报告，结论不受此 finding 影响。

Reviewer 仅写本报告及 B/C 两份指定报告；未修改产品、CI、治理记录或 index，未修改暂停 WIP。
