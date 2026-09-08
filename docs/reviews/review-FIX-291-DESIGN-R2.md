# Design Review — FIX-291 R2 复审（判定面批·熔断判定轮）

- **审查轮次**: R2（T1 链第 2 次复审——R1 结论 NEEDS_CHANGE/unresolved_blockers=1〔P1-R1〕返工后）
- **前轮报告**: `docs/reviews/review-FIX-291-DESIGN-R1.md`（P1-R1 节 + §5 预期终态——本轮按其指定锚点验证）
- **Reviewer**: Design Reviewer Agent（判定语义面）
- **日期**: 2026-09-09
- **审查对象**: 当前工作树未提交 diff（R2 窄修增量：`_w7_terminal_assertion_positions` ✅ 字形分支 + known_rounds 逐记录索引〔Code R1 P3-5〕+ 测试）
- **复审纪律**: R0/R1 全部 findings 修复保持性 + 边界八条终态推演 + 新发现照报；不为通过而通过

---

## 0. R2 验证方法（全部只读实测）

| 锚点（R1 §5 指定） | 方法 | 结果 |
|---|---|---|
| 1. AUDIT-143 恢复 completed | live 格逐字探针 + 套件红 fixture `test_audit143_live_cell_completed` | ✅ True（恢复） |
| 2. 叙事护栏全保持 | R1 六形态 + R2 新护栏（✅ 无日期段 / ✅ 非段首 / ✅ 断言后 active 段）探针 13/13 + 套件红测试 ×6 | ✅ 全 ACTIVE |
| 3. flip 集 = 恰 1 换入 / 0 换出 | 独立重建 HEAD 谓词（与 diff 删除行 `if "✅" in text and not any(m in text for m in ("未完成","待完成","进行中","待执行")):` 逐字一致——Developer 方法学可信）全量扫描 | ✅ IN=['REL-069'] / OUT=[] |
| 4. live | Check 30 / 30c / p0_pending | ✅ FAIL/7/24 逐条一致；30c=2；p0_pending=0 |
| 5. 全量测试 | `pytest infra/tests/` 全量 | ✅ 26 failed / 2104 passed / 226 subtests——失败全部归属三类既有环境基线（cleanup ×1 + loop_runtime_claims ×1〔RISK-048〕+ pre_commit_review_evidence ×24〔WSL 基线〕），零新增失败类 |

---

## 1. P1-R1 修复裁决（阻塞项）

**✅ 已修复，达到 R1 §5 预期终态。**

R2 实现（verify_workflow.py L10249-10286）：✅ 字形维持断言地位但放宽至**段规则**——✅ 处转移边界后段首 + 同段内（至下一 →/— 边界或格尾）含日期括注 `[（(]\s*\d{4}-\d{2}-\d{2}` 即断言；词表 marker（已发布/已关闭/…）**维持 R1 严格断言不变**（日期紧随/格尾）；docstring 同步。

**语义推演（逃逸面判定——Coordinator 提问「✅ 段内叙事提及日期但非终态？」）**：
- ✅ 是无歧义状态字形（非叙事词——R1 收紧针对的主语前置叙事形态均不含段首 ✅）。「✅ + 段内日期」的断言语义 = dogfood 惯例本身（FIX-278 F-1：✅ = delivered endpoint）——对该形状族的判定与 pre-FIX-291 基线 ✅ 分支**等价**（无 active 措辞时基线同判 True），不构成新增放宽面。
- 段内 active 词防护：`_status_is_completed_cell` 的位置比较覆盖段内后续 active（「✅ 交付 (d) 后续进行中」→ 进行中 位置在后 → ACTIVE，探针验证）✓。
- 段边界早截断（段内日期区间破折号等）只会丢失断言 → ACTIVE 方向（保守）✓。
- 唯一比基线更严的形状族：「✅ 段无任何日期 + 排除触发仅为 ⏳/🔄 emoji」→ R2 ACTIVE vs 基线 completed——**live 实测 OUT=[]（零实例）**；作为理论形态登记（P3-R2-a）。
- 护栏覆盖充分性判定：**充分**——✅ 无日期段 / ✅ 非段首 / active 后段胜出三护栏均有探针 + 套件红测试锚定（`test_check_glyph_without_date_in_segment_stays_active` / `test_check_glyph_mid_prose_not_at_segment_start_stays_active` / `test_active_after_check_glyph_segment_stays_active`）。

## 2. 随附处置验证

| 项 | 验证 | 裁决 |
|---|---|---|
| Code R1 P3-5（≡ 我 R1 P3-R1-b）：known_rounds 逐记录索引 | 实读 L2747-2775：`(task,round) → [record{date,valid},…]` + `_next_round_discharged` = exists-one（单记录 valid ∧ dated ≥ base）——max-date+OR-valid 归并边角（valid-但-旧记录 + 新-UNKNOWN 合并出无单记录依据的豁免）消除；红 fixture `test_composite_valid_old_plus_unknown_new_not_discharged` + 绿 `test_single_valid_dated_record_still_discharges` | ✅ 修复正确（我的 P3-R1-b 超预期闭合） |
| Developer 如实报告护栏初稿撞 P3-R1-c（pre-existing `完成(` 兜底） | 该路径新旧谓词同判 True（R1 已核），非 R2 引入；已登记维持 | ✅ 处置诚实合规 |

## 3. R0/R1 全部 findings 修复保持性（R2 不得引入回归）

| ID | R2 后状态 | 证据 |
|---|---|---|
| R0 P1-1（provably-zero） | ✅ 保持 | regex 未动；回归探针 5/5（FIX-254 形状/spaced/歧义值/P2-nonzero 绿）；live FIX-254 保持 FAIL |
| R0 P2-1（机录行分类） | ✅ 保持 | 行分类代码未动；live 30c rows_machine 分类不变 |
| R0 P2-2（V8 日期序+有效性） | ✅ 保持且增强 | R2 逐记录化收窄豁免面；live REL-070 豁免仍存活（30c=2 WARN、零 V8） |
| R0 P2-3（版本上下文残余） | ✅ 保持 | 词表断言规则未动；探针复验 ACTIVE |
| R0 P3-1/P3-2 | ✅ 保持 / ✅ 已随附 | 歧义值测试在套件；计数面注记 + 本轮双向披露（IN/OUT 清单与我的独立扫描一致） |
| R1 P1-R1（AUDIT-143 回归） | ✅ **修复** | §1 |
| R1 P3-R1-a（分隔符覆盖） | 维持观察 | corpus 惯例（=/×）覆盖；非阻塞 |
| R1 P3-R1-b（归并归因） | ✅ **闭合**（P3-5） | §2 |
| R1 P3-R1-c（`完成(` 兜底，pre-existing） | 维持登记 | Developer 撞见并如实报告；非本批范围 |
| R1 P3-R1-d（现行手写行不破坏 historical） | 维持观察 | V7 WARN 可见性保留；非阻塞 |

## 4. 边界锁定八条组合路径终态推演（R2 后）

| 路径 | 终态 |
|---|---|
| A × ACTIVE 恒 FAIL | ✅ 保持（completed 前置未动） |
| A × 现行格式（文件 + 机录行） | ✅ 两通道破坏 historical 分类保持（手写行残余 P3-R1-d 观察） |
| A × 真实 nonzero（valid / prose 附着） | ✅ 保持拒绝（R1 修复未回退；回归探针通过） |
| A × 歧义值 | ✅ fail-closed 保持 |
| C（W-7）单独 | ✅ 断言域 = 严格词表 + ✅ 段规则（基线等价 + 三护栏）；flip 恰 1 进 0 出 |
| B × A / B × C | ✅ 无交互（30c 不消费 completed/source_format） |
| A(V2) × A(V5) 同链 | ✅ 单裁决 continue 语义保持 |
| 三子项叠加 | ✅ live 实测 Check 30 输出逐条一致（FAIL/7/24） |

**终态结论：无任何组合放宽路径；三子项 + 三轮修复后的判定面满足「ACTIVE/真实 nonzero 恒 FAIL」锁定与「降级仅限历史形状/保守漏降级修正」范围。**

## 5. 新发现（R2）

仅观察项，无阻塞：

| ID | 观察 |
|---|---|
| P3-R2-a | 「✅ 段无日期 + 仅 emoji active（⏳/🔄）触发排除」形状族较 pre-FIX-291 基线更严（ACTIVE vs 基线 completed）——live 零实例（OUT=[]），理论形态登记；如未来出现该形状格可按 AUDIT-143 同型判例扩展段规则 |
| P3-R2-b（注记） | pre_commit_review_evidence SUBFAILED 计数 25→24（0.78.1 基线→本批）——同一既有 WSL 基线类内的数据依赖漂移（replay 真实 evidence log），非 FIX-291 代码失败；零新增失败类结论不受影响 |

## 6. 终态结论

**APPROVED_WITH_NOTES**

- **unresolved_blockers = 0**
- P1-R1 修复达到 R1 §5 预期终态全部锚点；R0/R1 全部 findings 修复保持、无 R2 回归；边界八条终态推演无放宽路径；随附 P3-5 超预期闭合 R1 P3-R1-b。
- 保留备注（非阻塞，跟踪不阻断）：P3-R1-a（分隔符覆盖）、P3-R1-c（pre-existing `完成(` 兜底）、P3-R1-d（手写行残余）、P3-R2-a（✅ 无日期理论形态）、P3-R2-b（基线漂移注记）。
- 设计面无进一步异议；发布决策（M-4）留给用户。

---

*本报告为 FIX-291 判定语义面 R2 复审（熔断判定轮——通过终态）。审查过程零产品文件写入（唯一写入 = 本报告）；全部验证命令只读。*
