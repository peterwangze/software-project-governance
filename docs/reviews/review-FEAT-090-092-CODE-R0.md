# CODE REVIEW — 治理开销优化批（FEAT-090/091/092）独立审查报告（R0）

- **Reviewer**: Code Reviewer（独立，round 0，批量审查——FEAT-091 新派发协议首用：2~4 相关产物合并单 Reviewer，逐票结论）
- **日期**: 2026-10-09
- **审查对象**: 工作区未提交变更（git status 17 M + 2 ??，+285/-40 与声称一致）
- **验收标准出处注记**: 任务指令称源自 change-triage JSON 的 acceptance 字段——三份 JSON 实无该字段；实际验收文本在 plan-tracker.md L81-83（内容一致，仅出处引用需更正）

════════ FEAT-090 — verdict: APPROVED_WITH_NOTES，unresolved_blockers = 0 ════════

验收逐项：
① M7.8 三契约 ✓ — behavior-protocol.md:767-775。M7.8.1 并行派发+禁睡眠（含运行时通知驱动语义）、M7.8.2 三触发器事件化（含「不取消 M7.4 step 2/M8 自检」范围句）、M7.8.3 热路径单源（write-guard 同级措辞显式落文）。风格与 M7.7 R 条款一致（MUST/违规/出处引用）。
② SKILL 契约 7~9 ✓ — SKILL.md 关键行为契约段（intro 六条→九条，test_dsh_adapter 断言「九条与铁律同级」通过）。
③ governance-init 模板同步 ✓ — 两处 profile 模板插入 + e2e 副本同步（blob hash 相同）；ENTRY_TEMPLATE_CANONICAL_BYTES 三 profile 各 +365B；check-injection-budget 三 profile 全 PASS（自跑复核：lightweight 4416 / standard 5899 / strict 6172，与声称完全一致）。
④ governance-verify 事件化口径 ✓ — 三触发器节 + 范围注记 + 「用户显式调用不受限」豁免。
⑤ 零退化 ✓ — 见横切第 4 条。

Findings：
- [P2] strict 注入余量仅 28 tok（6172/6200，hard gate）。证据：`verify_workflow.py check-injection-budget --profile strict` → PASSED 6172 ≤ 6200。护栏存在（canonical bytes pin + hard gate 使任何增行必先 re-price），但余量数字应入 evidence/票面台账，后续任何 resident 面（persona/agent-instructions/模板）增长都会触发 gate。
- [P3] behavior-protocol.md:769 M7.8 引言「性能行为可按行为灰度开关 legacy 回退」略欠逐条映射：M7.8.1/.2 无 LEGACY_REVERTS 条目（behavior_profile.py 未改），实际可回退的只有 M7.8.3 的 FEAT-034 fallback（已在回退表内）。句子自洽（安全面排除清单点名派发/验证），但可更精确。
- [P3] 本地狗粮 CLAUDE.md（gitignored）已被手工同步新契约行，先于 /plugin update 升级流。不分发、无害，但偏离 canonical 升级路径（FIX-011 纪律的边缘操作）。

════════ FEAT-091 — verdict: APPROVED_WITH_NOTES，unresolved_blockers = 0 ════════

验收逐项：
① M7.4 T1 R2 注入面 ✓ — behavior-protocol.md:565：复审必达/round+1/同人不变显式保留（「变的是注入范围」）；注入面=diff+前轮报告路径+验收标准；结构性变更 Reviewer 全量裁定权 + 「复审结论注明『要求全量』即视为行使」行权机制。
② governance-review 批量审查 ✓ — commands/governance-review.md:47-51：2~4 产物合并派发、逐份结论、Developer≠Reviewer 独立性不变。
③ review-record --scope/--delta-base ✓ — review_record.py:410-422 校验先于任何落盘（fail-closed）；缺省 full 向后兼容；新增 `- scope:`/`- delta_base:` 行对 Check 30/30c 解析器惰性已核实（REVIEW_FILE_DATE_RE/REVIEW_NEXT_ROUND_FIELD_RE 均锚定自身字段行，review_domain.py:3205/3225）；CLI choices=argparse 拒绝非法值。
④ 摘要化回注 ✓ — governance-review.md（verdict+blockers+全文路径、禁全文注入）+ SKILL 契约第 1 条 delta 句。
⑤ 零退化 ✓。

Findings：
- [P2] 陈旧实测数字：test_review_machine_provenance.py docstring 与 DEC-327 均记「段实测 3621B / 余量 475B」，实际按测试自身方法测量 = 3686B / 余量 410B（65B 漂移，疑为 FEAT-091 delta 句在测量后加长）。断言 ≤4096 本身正确且通过；但按本仓事实纪律，docstring 与 DEC-327 的实测数应更正（docstring 改数 + DEC 勘误行，DEC 修正走 Coordinator）。
- [P3] `--scope delta` 不带 `--delta-base` 被接受（无锚点记录）。M7.4 未强制锚点；建议后续要求或 WARN。
- [P3] API 直调时 scope="" 静默归一为 full（`str(scope or "full")`）；CLI argparse 已挡，仅 API 误用面。

════════ FEAT-092 — verdict: APPROVED_WITH_NOTES，unresolved_blockers = 0 ════════

验收逐项：
① --budget ✓ — verify_workflow.py:15346-15357：守卫位于唯一写点（15358 `if args.write`）之前，非法值 exit 2 且零落盘（测试断言文件不存在）；argparse type=int 拒绝非 int（exit 2）；--write 与只读 preview 都携带 stamp；缺省不写（测试覆盖）。
② 结构校验 ✓ — _execution_packet_field_issues（14096）budget 形状校验（精确键集/非 bool/int/正数），接线于 14209（加载面）与 25265（Check 18c）。
③ SKILL 分发路由 advisory 注记 ✓ — 「子代理预算传递」段，advisory 语义显式（不是硬门禁）。
④ 新测试覆盖 ✓ — test_execution_packet_budget.py 12 用例（写/preview/缺省/CLI 子进程 exit 0-2-2/非法值零写/形状校验/手工 enrich 保留）。
⑤ 零退化 ✓。

Findings：
- [P3] 裸 `--budget N --write`（无 --task）会 stamp 全部再生产包——语义合理但 SKILL/help 只示例 `--task {id} --budget {N}` 形态，建议补一句说明。
- [P3] 校验器测试缺 `{"max_steps": True}`（bool）用例（校验器已挡 bool，CLI type=int 产不出，仅手改 JSON 面）。
- [P3] test_cli_parser_accepts_budget_flag 对真实 .governance 跑只读 preview（NOSUCH task → 空选）——无副作用，轻微环境耦合。

════════ 横切发现 ════════

1. 注入预算：三 profile 数字与声称逐一相符（自跑复核）。strict 余量 28tok 属「可用但极薄」——gate 设计使增长必先自觉 re-price，可接受，但需入台账（见 FEAT-090 P2）。
2. regen 合法性：成立。anchor 27895→27934（+39）== verify_workflow.py 恰好 39 行纯插入（物理行口径，含注释行）；FACTS_PRINT_TOTAL 1375→1376（+1）== 唯一新 [ERROR] print（census cmd_execution_packet 2→3 一致）；baseline JSON 仅动 git_head/anchor_loc/census/total 四键，R2/R3/R5/R6 零漂移；git_head af8fba0 == 当前 HEAD。无夹带。
3. M0 重定基：成立。官方 recipe（"\n".join(lines[span])）复算两 content_sha256 均匹配，file_sha256 匹配；prior 链保留（新增 2 条 = 上一轮 last）；authorization 记三票 triage + 「R0 裁定回退则 pin 随票 revert」回退联动语义成立。
4. 回归声称核实：自跑 1596 passed + 172 subtests / 0 failed（batch1: review_record+execution_packet_budget+review_machine_provenance+archguard_ratchet+contracts = 272；batch2: dsh_adapter+verify_workflow+bootstrap_aggregate = 1184+142st；batch3: entry_projection+behavior_profile+governance_cost = 140+30st）。全套件 4757 passed + 1 flaky 未整体复跑（2h），但全部 diff 触碰模块 + 关键守护均已定向验证。flaky 判定可接受：test_bootstrap_aggregate 为 subprocess+timeout 型负载敏感测试，diff 零触碰该模块（git status 证实），本次复跑通过。
5. 越界结论：17 个修改文件全部在三票范围 + 声明 regen/fixture 副本内；e2e 非入口面副本（governance-verify/review.md、AGENTS.md）不同步是正确的（冻结 fixture/薄指针语义，守护测试通过佐证）。两个注意点：(a) [P2] 未跟踪文件 docs/requirements/analysis-governance-overhead-session-f3f46901-0.96.0.md 是本批需求源证据（DEC-327 引为 EVD-1350）但不在任何票 files[] —— commit 时必须显式纳入（补 files 或 commit message 注明），否则 EVD-1350 悬挂；(b) [P3] 「.governance/ 零触碰（git status 证实）」方法论不成立——.governance 在 .gitignore 内（git status 天然不可见）；但现存治理记录（triage JSON/DEC-327 governance-store 机写 op）均为 Coordinator 归因，与「Developer 不写 .governance」角色边界一致。
6. DEC-327：已入 decision-log（L194），先例链 DEC-144→162→295(2)→本票、回退语义（回退 7~9 条则预算上限随票回落 3072）完整；测试断言 3072→4096 与 docstring 先例链引用如实。唯一瑕疵 = 上述 P2 陈旧实测数。

总评：三票实现质量高——fail-closed 语义（校验先于写）、向后兼容（缺省 full/缺省不写/enrich 保留）、安全语义不回退声明、成本归因留痕均到位。无 P0/P1；4×P2（strict 余量台账、陈旧实测数 docstring+DEC、未声明证据文档纳入 commit）均为低成本收口项，不阻塞通过。建议：本轮顺手改 docstring 数字；Coordinator 补 DEC-327 勘误行 + commit 时纳入分析文档。

---
*处置跟踪（Coordinator 机录）：P2-docstring 数字更正 → Developer 单行闭环（进行中）；P2-DEC 勘误 → DEC-328 已入；P2-分析文档纳入 commit → 收口 commit 处理；strict 余量 28tok → evidence 台账记录；P3×6 → session-snapshot 观察池。*
