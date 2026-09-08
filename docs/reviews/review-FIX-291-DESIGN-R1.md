# Design Review — FIX-291 R1 复审（判定面批）

- **审查轮次**: R1（复审——前轮 R0 结论 NEEDS_CHANGE/unresolved_blockers=1，返工后强制复审 M7.4 step 4.6 T1）
- **前轮报告**: `docs/reviews/review-FIX-291-DESIGN-R0.md`（findings 基准——本轮逐项比对）
- **Reviewer**: Design Reviewer Agent（判定语义面；代码正确性由并行 Code Reviewer 负责）
- **日期**: 2026-09-09
- **审查对象**: 当前工作树未提交 diff（较 R0 时点 +1168/-23——返工增量 ~490 行）
- **复审纪律**: 逐条比对 R0 findings（已修复/未修复/新引入）；R1 不得为通过而通过

---

## 0. 复审方法与事实依据

| 事实源 | 核验方式 |
|---|---|
| 返工增量代码 | R0 后 diff 全量重读（P1-1 regex/解析器、P2-1 行分类、P2-2 索引豁免、P2-3 断言化四修复点逐行） |
| 语义推演 | provably-zero 12 形状探针（含 FIX-254 live 形状/spaced 计数/歧义值/ASCII 附着/CJK 附着）；W-7 断言 10 形状探针（含 REL-069/R0-P2-3 形状/CODE-R0 四叙事形状/护栏） |
| live 复核（只读） | Check 30 全量输出（viol/warn 逐条）；Check 30c 全量输出 + REL-070 豁免存活验证；completed 集合 R0-旧谓词 vs R1-新谓词全量 flip 扫描；`_status_is_completed_cell` 四消费者面核查（review_domain L2478 / parse_recent_completed_tasks L10452 / _status_next_steps L10661 / _status_task_stats L10701） |
| 测试 | `test_review_closure_legacy.py + test_review_machine_provenance.py`（62 passed）+ `test_verify_workflow.py` 全量（757 passed / 89 subtests） |

---

## 1. R0 findings 逐项比对（已修复 / 未修复 / 新引入）

| R0 ID | R0 要求 | R1 处置 | 验证证据 | 裁决 |
|---|---|---|---|---|
| **P1-1**（阻塞） | provably-zero 需证附着细目无 P0/P1 nonzero 计数；FIX-254 形状作红 fixture | 双负向前瞻：`(?!\s*[0-9A-Za-z])` token 边界 + `(?!.*P[01]\s*[=×xX]\s*[1-9])` nonzero 细目拒绝（review_domain.py L1691-1694）；**附带实质收紧**：解析器 malformed-value 分支改全行余量捕获（L1748-1753）——否则 `=0，P0 = 2` 带空格计数以截断值逃出证明窗口（合理且必要，采纳） | 探针 12/12：FIX-254 live 形状 `=0，P0=0/P1×1/P2×3/P3×5，共` 拒绝 ✓、`P0=1`/`P1×1`/spaced `P0 = 2` 拒绝 ✓、全零+`P2×1`/`P2=3/P3=5` 保持降级 ✓、`02，`/`10，`/`0abc`/`0 x` 拒绝 ✓、`0件` CJK 附着保持 ✓；红测试 ×5（含 FIX-254 同型 ×2 + 解析器级 ×3）+ 绿测试 ×1；live FIX-254 保持 FAIL ✓ | ✅ **已修复**（含超出建议的必要收紧；新逃逸面推演见 P3-R1-a） |
| **P2-1** | evidence 行通道按机器 marker 赋 source_format，使现行机器行破坏 historical 分类 | 行入口按 `REVIEW_MACHINE_ROW_MARKER` 命中赋 "machine"（L2550-2559）——rank 2 真实破坏分类 | 红测试 `test_machine_row_contribution_breaks_historical_classification`（同轮「机录行 + historical 文件」中缝缺口恒 FAIL）；merge-rank docstring 契约（L1926-1930）现对两通道均成立 | ✅ **已修复**（残余：现行**手写**行仍不破坏分类——降级登记 P3-R1-d） |
| **P2-2** | V8 豁免增加日期序 + 有效性校验 | `known_rounds` 索引化 {(task,round)→date+valid}（L2756-2811）；豁免 = `_next_round_discharged`：valid ∧ date ≥ base（L2767-2773，行/文件两豁免点同步 L2847/L2916） | 红测试 ×3（older/UNKNOWN/文件级日期序）+ 绿 `test_dated_valid_next_round_still_discharges_v8`；live REL-070 豁免存活（30c 仍 2 WARN，无 V8）✓ | ✅ **已修复**（归并边角见 P3-R1-b） |
| **P2-3** | W-7 版本上下文残余误判（「进行中——0.78.1 已发布」）收紧或登记 | 断言化收紧 `_w7_terminal_assertion_positions`（verify_workflow.py L10237-10268）：终态词须为转移段状态词（段首 = 格首/→/——后，允许 ✅/已 前缀）且紧随日期括注或格尾 | 探针 10/10：R0-P2-3 形状 `🔄 进行中 (…)——0.78.1 已发布` 现保持 ACTIVE ✓；CODE-R0 四叙事形状（方案A已撤回/令牌失效/窗口取消/已撤回，改推）+ 段首版本前缀 `——0.78.1 已发布` + 无日期护栏全 ACTIVE ✓；REL-069 形状保持 completed ✓；红测试 ×6 + 绿 ×4 | ✅ **已修复**（但收紧引入新回归——见 **P1-R1**） |
| P3-1 | 歧义值边界测试 | `test_parser_ambiguous_values_not_provably_zero`（10，/02，）+ `test_parser_ascii_letter_attachment_not_provably_zero`（0abc） | 测试清单实见 | ✅ 已交付 |
| P3-2 | live 计数面注记 | 随附 | ——但净计数声明掩盖了 per-task 双向 flip（见 P1-R1 披露要求） | ⚠ 部分（P1-R1 连带） |

---

## 2. 新发现（R1 引入）

### P1-R1（阻塞）—— W-7 断言化收紧回归了既有 completed 分类（live 实例 AUDIT-143，P0 任务）

**事实链（全部可复查）**：

1. live 状态格（plan-tracker AUDIT-143 行）：`⏳ 审计中 (2026-08-17) → ✅ 分析完成+规划落地 (2026-08-17)——DEC-143；REQ-107~114 入需求跟踪矩阵；修复链立项待 REQ-112/110 triage`
2. **pre-FIX-291 基线谓词 → completed**（✅ 分支命中：无 未完成/待完成/进行中/待执行 措辞——"审计中"不在排除集）；该分类自 FIX-278 F-1（「✅ 完成 (date) 状态格必须标记 completed」）起稳定成立。
3. **R0 代码 → completed**（R0 trailing-terminal 规则：✅ 本身是终态 marker，位置在 ⏳ 之后 → True）——R0 flip 扫描仅 REL-069 一例，无回归。
4. **R1 代码 → NOT completed**（实测）：✅ 分支被前导 ⏳ 排除（R0 起 ⏳/🔄 入排除集）→ 断言规则：`✅` 其后是「分析完成+规划落地」非日期 → ✅ 不构成断言；「分析完成」不在 W-7 终态词表（词表为 已发布/已关闭/已终止/已撤回/失效/不可信/取消/废弃——无通用完成措辞，完成措辞由 ✅ 分支 + `完成(` 兜底承载）；`完成\s*[（(]` 兜底不命中「完成+」→ **False**。
5. **影响面**（`_status_is_completed_cell` 四消费者）：① Check 30 completed 集——live 输出恰好无差（AUDIT-143 链无 completed-gated 规则交互，实测 viol/warn 逐条不变）；② **`_status_task_stats` p0_pending +1**（AUDIT-143 优先级 **P0** 实测——已完成 P0 任务在 cmd_status 快照中误报「待办」）；③ `parse_recent_completed_tasks` 最近完成列表失真；④ `_status_next_steps` 推荐候选可能混入已完结任务（advisory）。②—④ 为 advisory/展示面（无 FAIL 门禁消费者），① 为潜在未来危害（AUDIT-143 若长出需 L-A/L-B 降级的链将错误 FAIL）。

**定性**：方向为 fail-safe（向 ACTIVE 收紧，不破「ACTIVE/真实 nonzero 恒 FAIL」锁）；但违背 W-7 契约范围——queue-triage §2.1 #10 与 version-plan §2.2 将 W-7/BC-7 界定为「**保守漏降级修正**」（补漏的 completed 识别），不包括移除既有 completed 分类；且返工声明未披露（live 计数「149→149」类净计数声明〔本审查可测面 184→184 净零〕**掩盖了两个方向相反的 per-task flip**：REL-069 进 + AUDIT-143 出）。

**修复方向**（窄面）：✅ 是无歧义的状态字形（非叙事词——R1 收紧针对的是「方案A已撤回」类主语前置叙事形态，均不含 ✅），恢复其断言地位不需要重开叙事豁口。两候选：(a) ✅ 段首即断言，若同段（下一转移边界前）含日期括注；(b) ✅ 直接按位置比较（R0 语义）而词表 marker 维持 R1 严格断言规则。红 fixture = AUDIT-143 live 格（现行测试组无该形状——回归正因此漏网）。

### P3 级新观察（非阻塞）

| ID | 观察 | 依据 |
|---|---|---|
| P3-R1-a | provably-zero 细目分隔符覆盖：corpus 外写法 `P0：1`（全角冒号）/`P0*2` / 前导零 `P0=01` 逃逸细目拒绝（`[=×xX]` 类未含 ：/*/；`[1-9]` 不匹配 01 的 0）。本仓 corpus 惯例（=/×）已覆盖，live 无实例——登记观察 | L1691-1694 regex 推演 |
| P3-R1-b | known_rounds 同 (task,round) 多记录归并 date=max/valid=any 的混合归因边角：undated-valid 文件 + dated-UNKNOWN 行合并出 valid∧dated 条目可豁免（各记录自身均不满足）。需同轮双源畸形记录，极窄 | L2758-2765 `_index_record` |
| P3-R1-c | `完成(` 兜底绕过 trailing-active 比较：「✅ 完成 (d) → 🔄 reopened (d)」仍判 completed——**pre-existing 行为**（本 diff 未改变该路径，新旧谓词同判 True），如实登记供后续收紧 | verify_workflow.py L10307 兜底路径 |
| P3-R1-d | 现行**手写** REVIEW- 行（无 marker → unknown rank 0）并入 historical 文件轮不破坏 historical 分类（机器行已修复）。该行自身被 V7 WARN（可见性保留）；收紧候选 = 日期 ≥ FIX-174 的行一律破坏分类 | L2556-2558 + rank L1955-1960 |

---

## 3. 边界锁定复核（R0 §2.4 八条重推演——修复后）

| 组合路径 | R1 后状态 | 判定 |
|---|---|---|
| A × ACTIVE 任务 | 不变（completed 前置保持；红测试保持） | ✅ |
| A × 现行格式记录 | **增强**：文件 + 机录行两通道均破坏 historical 分类（P2-1 修复）；手写行残余 P3-R1-d | ✅ |
| A × 真实 nonzero（valid） | 不变 | ✅ |
| A × 真实 nonzero（prose 附着） | **修复收窄**：FIX-254 形状/P0=1/spaced 计数全拒绝（P1-1 修复）；分隔符残余 P3-R1-a | ✅（较 R0 更严） |
| A × 歧义值 | 不变 + 显式测试锚定（P3-1 交付） | ✅ |
| C 单独（W-7 误判） | 残余形态收紧（断言化）；**新回归 P1-R1（反方向：completed→ACTIVE）**——不破锁但破 scope/正确性 | ⚠ P1-R1 |
| B × A / B × C | 不变（无 completed/source_format 消费） | ✅ |
| A(V2) × A(V5) 同链 / 三子项叠加 | 不变（单裁决 continue 语义保持；live 实测零叠加放宽） | ✅ |

**结论**：三子项组合路径无任何新增放宽；唯一新面为 P1-R1 的收紧方向回归。

---

## 4. live 复核（只读实测，2026-09-09）

| 验证门槛 | 实测 | 判定 |
|---|---|---|
| Check 30 逐条不变 | FAIL / violations 7 条逐条一致（V1 FIX-213 + V5 FIX-253/254/255/256/258/REL-068）/ warnings 24 条同分布（V1×20 V2×2 V5×1 V3×1） | ✅ |
| FIX-254 保持 FAIL | ✓（V5 violations 内；且其 prose 形状现被 regex 直接拒绝——若未来成为 historical 文件形状亦不降级） | ✅ |
| 30c / REL-070 豁免存活 | 30c WARN/2（V7 FIX-256 + FIX-258 现行手写行）；REL-070 V8 ×0（dated-valid R+1 豁免在日期序收紧下存活） | ✅ |
| REL-069 flip 保持 | ✓（断言「✅ 已发布 (date)」命中，completed=True；其链 machine/valid-0 与 V5 无门交互） | ✅ |
| **全量 flip 扫描** | R0-旧谓词 vs R1-新谓词：**2 例**——REL-069（进，预期）+ **AUDIT-143（出，P0——未披露回归 → P1-R1）**；净计数 184→184（净零掩盖双向 flip） | ❌ P1-R1 |
| 测试 | 62 + 757 passed / 89 subtests 全绿 | ✅ |

---

## 5. 终态结论

**NEEDS_CHANGE**

- **unresolved_blockers = 1**（P1-R1）。
- R0 全部 findings（P1-1 / P2-1 / P2-2 / P2-3 / P3×2）**均已有效修复**，修复质量高于建议面（P1-1 的解析器全行捕获、P2-2 的有效性门均为必要收紧，采纳）。
- 阻塞项为 R1 收紧**新引入**的 per-task 回归：AUDIT-143（P0 任务）completed→ACTIVE——违背 W-7「保守漏降级修正」范围（只应补漏、不应移除既有 completed 分类），产生 p0_pending 误 +1（cmd_status 展示面）等四消费者影响，且未被返工声明披露（净计数声明掩盖双向 flip）。
- 修复面窄且方向明确（✅ 字形断言地位恢复 / 位置比较恢复，词表 marker 维持严格断言规则；红 fixture = AUDIT-143 live 格）。修复后预期 R2 复审仅验证：AUDIT-143 恢复 completed + 叙事形状护栏全保持 + flip 集回到恰 1 例（REL-069）。
- P3×4（R1-a/b/c/d）为观察项，不阻塞（P3-R1-c 为 pre-existing 行为登记）。

---

*本报告为 FIX-291 判定语义面 R1 复审。审查过程零产品文件写入（唯一写入 = 本报告）；全部验证命令只读。*
