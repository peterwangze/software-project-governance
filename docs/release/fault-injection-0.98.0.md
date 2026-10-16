# 0.98.0 故障注入六项验证报告（DEC-330 发布底线）

- **版本**: 0.98.0 · **验证时点**: 2026-10-15（M-3 RELEASE 半面定向实跑）+ 2026-10-16（M-8 落盘收口） · **性质**: DEC-330 联合裁定之发布验证底线——六项不可豁免
- **执行**: 独立 Release Reviewer 子代理定向实跑承载测试（`pytest -k` 六项承载选择器）——**8 passed, 1243 deselected, 1.29s**（REVIEW-REL-102-R2 §②-5，报告 sha256=d7f2ba5e…，ledger seq60）

## 六项 × 机器承载 × 实测结果

| # | DEC-330 验收项 | 机器承载（文件:行） | 实测 |
|---|---|---|---|
| 1 | 错修订审查拒收 | test_enforcement_hard_block_revision_mismatch_on_review_dispatch（test_verify_workflow.py:26975）+ task-row-update 状态级/内容级双 CAS（test_task_row_update.py:261/275） | ✅ passed |
| 2 | 报告机录冲突拒收 | test_acceptance3_conflict_refused_nothing_written（test_verify_workflow.py:26140）——CONFLICT 判定禁乐观者胜出、零写入 | ✅ passed |
| 3 | R2 不漏建 | test_needs_change_row_without_next_round_record_still_fails_v8（test_review_machine_provenance.py:394）+ V8 族六测——NEEDS_CHANGE 无 next_round 机录即 FAIL | ✅ passed |
| 4 | 代理死亡可恢复 | test_acceptance5_aborted_does_not_discharge_obligation（test_verify_workflow.py:26318）+ supervisor escalation states（:26164）——ABORTED/UNKNOWN 终态不解除义务 | ✅ passed |
| 5 | blocked 后无未授权执行 | test_blocked_execution_fault_injection_zero_unauthorized（test_goal_bridge.py:444）+ unauthorized_attempts 审计四测——BLOCKED 无用户裁定 refuse+落账 | ✅ passed |
| 6 | 无关任务不被全局冻结 | test_enforcement_allowlist_channels_not_frozen_and_goal_resume_throttled（test_verify_workflow.py:27060）——scoped 白名单（fix/re-review/forensics）外通道不冻结+goal 续走限流 | ✅ passed |

## 保障层级声明（如实降级——M-0 §3 调研判定）

六项承载均为 **CLI 级+协议级**执法（六平台无宿主级拦截——DSH 原语 guard/toolFilter/fs-sandbox 完备但插件未接线，U1 PoC 为后续候选票）；goal 机械 floor（blocked 轮数/resume 需直接人类轮）为唯一 harness 真执法部分。该降级口径与 FEAT-095 交付物披露一致（SKILL「动作级执法」段+feature-flags-0.98.0.md），不构成宿主级声明。

## 复跑

`python -m pytest skills/software-project-governance/infra/tests -k "revision_mismatch or conflict_refused or next_round_record or aborted or unauthorized or not_frozen" -v`（承载子集）；全量承载面随 test_verify_workflow/test_goal_bridge/test_review_machine_provenance/test_task_row_update 全套件（M-2 unit gate exit=0，EVD-1707/1708）。
