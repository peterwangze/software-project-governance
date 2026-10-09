# REVIEW-REL-101-M3a-CODE-R0 — M-1 版本面 CODE 审查报告（Code Reviewer，2026-10-09）

- **Reviewer**: Code Reviewer（M-3a 半面，独立复跑）
- **Verdict**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**——以全量 pytest 绿为准（EVD-1353 已录 4758P/1S/563st 0F exit 0）
- **审查对象**: 未 commit 工作区 23 文件 65+/31- + untracked docs/release/m-0-assembly-0.97.0.md（全 diff 逐文件过审，非抽样）

## 一、bump 完整性与一致性 — PASS
- check-version-consistency PASSED exit=0（13 faces + bootstrap markers）；义务面全部核到（REQUIRED_SNIPPETS 六锚 L1058~1073 等长 12 行/governance-init 三标记×2/AGENTS.md.template/persona L51/双根 entry sync ×4/e2e fixture 五文件/.git/hooks 四文件 @version=0.97.0——28q 漂移归零）
- 等长替换核查：23 文件全部为 0.96.0→0.97.0 等长替换，**零意外内容变更**（100% 全量过审）

## 二、CHANGELOG 0.97.0 段（L5~L37）— PASS
- diff numstat 34+/0- 纯插入；0.96.0 段零触碰
- 五要素齐备：版本主题（EVD-1350 四数字全对）/四票载荷/DEC-327 披露/升级路径与回退面/回滚引用
- **30c FAIL 执法披露三处落位足够显著**（L10/L21 加粗/L29）；PROVENANCE_FAIL_ESCALATION_VERSION="0.97.0" 硬编码于 review_domain.py:3188
- 数字全对账：EVD-1350/1351/1352、DEC-326/327/328、review_exemptions_30c.json（canonical sha256 独立复算=53615bc6… 逐字符相等）、载荷 6 commits、v0.96.0 tag peel 325289f
- 准备态注记与 0.96.0 FIX-349 口径同构

## 三、风险状态改形判定（RISK-039/050/066）
**判定：成立——「状态语义对齐先例」，非伪造非关闭非日期造假；具门禁决定性，需 DEC 收口（P2-1）。**
- 登记日期未动（10-01/10-01/10-04）；复评窗 2026-10-31 维持；改形注自证触发源与先例（047/062）；巡检证据真实（archguard 0viol/dsh exit 0）；EVD-1353 已披露
- 机制核验：is_risk_status_open 精确匹配（risk_domain.py L95-97）；改形后 check_risk_staleness() total_open 0/stale[]；check-governance exit 0
- 影响澄清：用户可见 risk_count 不变（FIX-397④ 前缀口径）；Check 36 内容维仍覆盖；净损失=Check 2/8 不再计入（与缓解中/降级同待遇，047/062/064/065 先例在先）
- **P2-1（M-7 前闭环）**：改形语义无 decision-log 入账 + m-0 §5#2 预期未显式勘误 → 处置二选一：补 DEC 或回退受 2 stale 基线

## 四、测试与门禁声称核实（全自跑）
check-version-consistency PASSED / test_static_version_pins 25 passed / injection-budget 4416/5899/6172 全 PASS（strict 冻结线 ACTIVE 28tok）/ test_review_machine_provenance 41 passed / check-governance exit 0
- **事实修正（P3-3）**：M-2 candidate 实际=FAILED-3（release-docs×3=M-4 时序态）+其余 22 面 PASS（四执行门 exit 0）——整体「PASSED」措辞不准确

## 五、越界检查 — PASS
diff 仅版本面+CHANGELOG+m-0 报告；core/releases 零触碰；旧段零删改

## Findings
- **P2-1** 风险改形缺 DEC 入账+m-0 §5#2 未勘误（→ 处置：M-7 前补 DEC 或回退）
- P3-1 回归基线口径：4757P（交付时点）vs 4758P（M-2 复跑）均绿；M-7 终账以最新全量为准
- P3-2 Check 2/8 解析盲区（RISK-052~059 行布局语义左移从未计入——EVD-1196 已记录同根因；后续卫生票候选）
- P3-3 M-2 verdict 措辞修正（见四）
- P3-4 Check 31 inventory-drift 瞬态 FAIL ×4（evidence-log 追加所致非门禁；M-7 消费前需重钉）
- P3-5 rollback-plan 前向引用（已披露可接受）
- P3-6 e2e plan-tracker 版本行尾 `**` 既有格式瑕疵（两侧同形保留）

## 联动失效条款
以全量 pytest 绿为准（EVD-1353：4758 passed+1 skipped+563 subtests 0 failed exit 0）；tag 前任何复跑红（含 flaky 复发）→ 本结论失效回 NEEDS_CHANGE 复审。
