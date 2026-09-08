# 审查报告：FIX-291 — 判定面批代码审查（Code Reviewer · R2 增量复审）

- **Task ID**: FIX-291
- **Reviewer**: Code Reviewer Agent（同一 Reviewer 复审，M7.4 step 4.6）
- **Round**: R2（前轮引用：`docs/reviews/review-FIX-291-CODE-R1.md` — APPROVED_WITH_NOTES/0）
- **审查对象**: R2 窄修增量（较 R1 时点：verify_workflow.py +27 / review_domain.py +2 / 两测试文件 +155；累计 5 文件 +1352/-23）
- **审查日期**: 2026-09-09
- **返工驱动**: Design R1 P1-R1 / P3-R1-b + 本 Reviewer R1 P2-3 / P3-5

---

## 一、结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

R1 两项 findings（P2-3 AUDIT-143 回归、P3-5 索引合并解耦）均真实修复且红→绿锁证；live 三代谓词 A/B 证实净行为面收敛至「相对 HEAD 恰 1 例预期翻转（REL-069）」。全量 26 failed/2104 passed 精确成立、零新增。新发现 2 项 P3（红相数字以修订前草稿口径披露；✅ 字形分支同段续写残面），均不阻塞。

---

## 二、前轮 findings 处置验证（R1 → R2）

| R1 finding | 声明处置 | 独立验证 | 结果 |
|---|---|---|---|
| **P2-3** AUDIT-143 completed→ACTIVE 回归（未披露 live 翻转） | ✅ 字形断言分支：✅ 处转移边界段首 + 同段（下一 →/— 前）内含日期括注即断言（不要求紧随）；词表 marker 维持 R1 严格断言 | 代码逐行（`verify_workflow.py` `_w7_terminal_assertion_positions` R2 段）；live 三代探针（196 行）：**HEAD→R2 翻转 = [REL-069] 唯一**——AUDIT-143 恢复 HEAD 判定（True），R1→R2 翻转恰 1 例 = AUDIT-143；`W7CheckGlyphAssertionTests` 7 测试全绿（含 R1 六叙事护栏逐形复验 + 版本上下文 + reopened + 段后 active 边界） | **已修复** ✅ |
| **P3-5** `_index_record` max-date + OR-valid 解耦 | 逐记录列表索引 + exists-one 精确判定（`review_domain is None → False` fail-closed 守卫） | `ReworkR2IndexSemanticsTests`：复合误放行形态（有效旧 + UNKNOWN 新）红相 fail（R1 沙箱实证）/绿相 pass；单条有效 dated 守卫保持；`review_domain.py` 逐行核对——`any(rec.valid ∧ rec.date ≥ base)` 为精确式，解耦面消除 | **已修复** ✅ |
| P3-6 非 marker 手写行维持 unknown | 登记维持 | 本轮 diff 无相关变更 | **按约登记** ✅ |

---

## 三、增量逐项验证

### 1. ✅ 字形断言分支 ✅（含相互作用审查）
- **段首前提继承**：✅ 分支位于既有 (a) head 检查之后——主语前置/版本前缀 ✅ 一律先被拒（`test_check_glyph_mid_prose_not_at_segment_start_stays_active` 锁证）。
- **同段日期任意位置**：segment = ✅ 起至下一 `→`/`—` 或格尾；AUDIT-143 的 `(2026-08-17)` 在复合措辞后 → 断言成立。segment 边界用单字符 `—` 搜索天然覆盖 `——`。
- **与词表分支无短路/优先级问题**：✅ 分支 `continue` 后词表 marker 仍独立遍历；两分支产出并入同一 positions 列表，`max(assertions) > active_pos` 守卫对两来源统一生效——reopened（✅ 断言后被 🔄）与段后 active（`test_active_after_check_glyph_segment_stays_active`）均保持 ACTIVE。
- **rule 3（✅ 无 active marker → True）优先级不变**：字形分支只影响混合链 rule-4 路径，无回归面。
- **护栏六形态 + 版本上下文不重新误伤**：逐形复验测试锁定（六形态均不含 ✅，与 ✅ 放宽正交）。

### 2. known_rounds 逐记录索引 ✅
R1 合并式（`{"date": 最新, "valid": 任一}`）→ R2 记录列表 + `any(valid ∧ dated ≥ base)`——语义精确化，两个豁免点（文件级/行级）调用面不变；`base_date is None → False` 显式 fail-closed。

### 3. 新增 9 测试 ✅
- 绿相：`W7CheckGlyphAssertionTests` 7 + `ReworkR2IndexSemanticsTests` 2 = 9 全过（累计 64+26 passed）
- **红相（R1 代码沙箱——当前文件回退 ✅ 分支 12 行 + 索引函数回退 R1 合并式，py_compile 过）实证：2 failed / 7 passed**——红项 = `test_audit143_live_cell_completed` + `test_composite_valid_old_plus_unknown_new_not_discharged`（恰为两项修复的锁证）；7 绿项全为护栏（R1/R2 同判）。声明"红相 3 failed/6 passed"的**第 3 红为护栏初稿**——初稿措辞撞 pre-existing `完成\s*[（(]` 兜底路径（新旧谓词同判 True，无法成红）后改措辞为「已交付」（docstring 内如实登记为 DESIGN-R1 P3-R1-c）。披露诚实；终版测试集红相实为 2/7（见 P3-7 口径注记）。

---

## 四、Developer 声明数字独立复核

| 声明 | 复核 | 结果 |
|---|---|---|
| 累计 5 文件 +1352/-23 | git diff --stat | ✓ |
| 全量 26 failed / 2104 passed（+9 零新增） | 工作树全量 | **26/2104 精确一致** ✓（2095+9=2104；失败集 = R0/R1 同三类存量：cleanup manifest / loop_runtime 计时（本轮 failed）/ pre_commit WSL hook；零新增） |
| 红相 3 failed/6 passed | R1 沙箱实证 | 终版集 **2/7**；第 3 红为修订前草稿（披露如实——P3-7） |
| live（未逐项声明） | Check 30 = FAIL/7 viol/24 warn（task 集与 R0/R1 一致）；30c = WARN/2（V7:2）；rows_non_review=164；check-governance = **149**（R0/R1 均 149）；completed 集 185 = HEAD 184 + REL-069（AUDIT-143 复位） | 全部一致 ✓ |
| py_compile / 卫生 | 五文件 OK；R2 增量零 TODO/mock/硬编码（AUDIT-143 仅现于 docstring 文档引用） | ✓ |

---

## 五、Findings（R2 新发现）

### P0 / P1 / P2：无

### P3-7 红相数字以修订前草稿口径披露
- 声明「红相 3 failed/6 passed」描述的是护栏措辞修订**前**的草稿状态；终版测试集红相 = 2/7（R1 沙箱实证）。撞 `完成 (` 兜底路径的初稿红项在改措辞后转为双判绿护栏，不再构成红证据——碰撞本身与 pre-existing 路径登记（DESIGN-R1 P3-R1-c）在指令与测试 docstring 中均已如实披露，无隐瞒；仅为数字口径精确性注记。建议后续红相数字以终版集口径报告。

### P3-8 ✅ 字形分支同段续写残面（前瞻）
- ✅ 段首 + 同段日期后，若**同段内**（无 →/— 分界）跟随非词表进行措辞（如「✅ 初版评审通过 (date)，二阶段规划中」——「规划中」不在 active 词表），位置守卫不触发 → 判 completed。护栏测试覆盖的是**段后**（——分界）active 措辞形态。live 零实例（三代翻转全集 = REL-069 + AUDIT-143）；dogfood 惯例 ✅+日期段即终态，风险前瞻性记录。如后续语料出现该形态，可收边为「✅ 与日期之间/之后的同段 active 类措辞检查」或扩充 active 词表。

---

## 六、五维度 + AI 专项（增量）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ | §三 1-2 逐行 + 沙箱红相实证 + live 三代 A/B |
| 安全性 | ✅ | 无新增输入执行面 |
| 可维护性 | ✅ | R2 分支带 Design-R1 出处注释 + live 实例引用；docstring 与实现同步（含 ✅ 分支差异说明） |
| 性能 | ✅ | 记录列表 any() 线性于同轮记录数（≤2）；✅ 段扫描有限 |
| 测试覆盖 | ✅ | 9 新测试 = 2 红锁证 + 7 护栏（含 R1 六形态复验——放宽不回退收紧） |

AI 专项 5 项：mock 残留无（测试 patch 除外）/硬编码无（AUDIT-143 为 docstring 文档引用）/幻觉 API 无（`_file_date`、`_normalize_review_conclusion`、`_extract_review_conclusion_from_text` 均存在且语义一致）/TODO 无/过度实现无（2 项窄修逐一对应 R1 findings，无范围蔓延）。

---

## 七、验证证据（R2）

1. `py_compile` 五文件 OK；closure+provenance 64 passed；三 W-7 类 26 passed（9+10+7）
2. live 三代谓词 A/B（196 行，HEAD/R1 规则/R2——HEAD 谓词按 diff 删除行重建、R1 规则在本探针内按 R1 语义复刻）：HEAD→R2 = [REL-069(False→True)] 唯一；R1→R2 = 1（AUDIT-143 False→True）；R2-completed=185
3. R1 红相沙箱（%TEMP%\fix291_r2red：当前 infra 副本 + 2 处 R2 区域回退，py_compile 过）：ReworkR2Index 1F/1P、W7CheckGlyph 1F/6P = **2F/7P**
4. 全量：26 failed / 2104 passed（= 2095+9 ✓，三类存量零新增）
5. live 检查：Check 30 FAIL/7/24（task 集一致）；30c WARN/2；check-governance 149；rows_non_review=164
6. 卫生扫描：R2 增量零 TODO/mock/硬编码残留

## 八、硬门槛自检

- [x] P0 = 0；[x] 5 维度覆盖；[x] 每条发现标注级别（P3×2）；[x] 设计一致性（Design R1 P1-R1/P3-R1-b 处置对应核实）；[x] AI 专项 5 项；[x] 只读审查（除本报告外零仓库写入；沙箱/探针 %TEMP% 已清理）；[x] 前轮 findings 逐条比对（§二）；[x] round 号与前轮引用声明（头部）

## 九、终态

**APPROVED_WITH_NOTES — unresolved_blockers=0**

- R1 P2-3 / P3-5 已修复且锁证；live 净行为面 = 相对 HEAD 恰 1 例预期翻转（REL-069）
- 新增 P3-7（红相口径）/ P3-8（✅ 同段续写残面）登记备查，不阻塞
- 后续归 Coordinator：review-record 机录（round 5）/ 本终态为通过态（无 T1 复审义务）/ 遗留入账（累计：P3-2 登记维持、P3-6 维持、P3-7、P3-8）/ commit 安排
