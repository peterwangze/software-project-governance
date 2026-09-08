# 审查报告：FIX-291 — 判定面批代码审查（Code Reviewer · R1 增量复审）

- **Task ID**: FIX-291
- **Reviewer**: Code Reviewer Agent（同一 Reviewer 复审，M7.4 step 4.6）
- **Round**: R1（前轮引用：`docs/reviews/review-FIX-291-CODE-R0.md` — APPROVED_WITH_NOTES/0）
- **审查对象**: 返工增量（当前工作树 diff 相对 R0 审查时点；累计 5 文件 +1168/-23，R1 增量约 +482/-3）
- **审查日期**: 2026-09-09
- **返工驱动**: Design R0 findings + 本 Reviewer R0 P2×2/P3 同源项

---

## 一、结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

R0 全部 findings 处置到位（P2×2 真实修复且有红→绿测试锁证；P3-1/P3-3 修复；P3-2 按约登记处置）。返工声明的全部数字经独立复现精确成立（红相 14 failed/7 passed、全量 2095 passed、live 计数零漂移）。新发现 1 项 P2（未披露的 live 谓词翻转 AUDIT-143——保守方向、治理检查零 delta，但属合法终态措辞的漏判且回工摘要未披露）+ 2 项 P3。无 P0/P1。

---

## 二、前轮 findings 处置验证（R0 → R1）

| R0 finding | 声明处置 | 独立验证 | 结果 |
|---|---|---|---|
| **P2-1** W-7 散文误伤面（4 形态判 completed） | `_w7_terminal_assertion_positions` 断言收紧（段首边界 + 终态日期括注双条件） | 4 形态 live 探针 + `W7TerminalSegmentScopeTests` 全绿；红相 6 failed 精确复现（对 R0 沙箱）；`verify_workflow.py:10237-10266` 逐行核对：主语前置（head 不以 →/—/✅/已 收尾即拒）+ 非日期续写（rest 不匹配 `^[（(]\s*\d{4}-\d{2}-\d{2}` 即拒）双重排除 | **已修复** ✅ |
| **P2-2** 行入口 source_format 缺省 unknown(0) 无法击穿 historical | 行通道按 `REVIEW_MACHINE_ROW_MARKER` 分类为 machine(2)（`review_domain.py:2547-2557`） | `test_machine_row_contribution_breaks_historical_classification` 红相 fail（R0 沙箱实证）/绿相 pass；live 复算 60 轮机录分类、Check 30 数字与 R0 完全一致（live 无受影响复合形态）；docstring 声明「两通道均成立」现已如实 | **已修复** ✅ |
| P3-1 `0abc` 边界接受 | token 边界负向前瞻 `(?!\s*[0-9A-Za-z])` | `test_parser_ascii_letter_attachment_not_provably_zero`（0abc 拒 / 0件、0，P0=0 收）绿相过、红相 fail | **已修复** ✅ |
| P3-2 parts[2]-only REVIEW id 不受判 | 维持（登记处置） | 本轮 diff 无相关变更——与 Coordinator 指令一致 | **按约登记** ✅ |
| P3-3 known_rounds 无日期/时序校验 | `_index_record`/`_next_round_discharged`（valid + date ≥ base，行/文件两豁免点） | `ReworkR1DischargeScopeTests` 3 红（older/unknown/file-level）+ 1 绿守卫（dated-valid）精确复现；`review_domain.py:2747-2812` 逐行核对 | **已修复** ✅（残留下界见 P3-5） |
| P3-4 复合测试归因 | 记录 | — | 记录维持 |

---

## 三、返工增量逐项验证（Developer 声明 6 项）

### 1. `_PROVABLY_ZERO_TOKEN_RE` 双负向前瞻 ✅
`review_domain.py:1690-1693`：`^unresolved_blockers=0(?!\s*[0-9A-Za-z])(?!.*P[01]\s*[=×xX]\s*[1-9])`。逐案验证：
- 边界：`10，`/`02，`（字面不匹配）、`0abc`/`0 x`（ASCII 字母数字前瞻拒）、`0件`/`0，`（CJK/全角逗号放行）——语义正确
- 细目：`P1×1`/`P0=1`/`P0 = 2`（空格容忍）拒绝；`P2=3`/`P3=5`（非阻塞级）不拒绝——与 L-B「可证为空」标准精确对齐；`P1=0` 零值不拒绝 ✓
- live 自相矛盾形状（FIX-254）：`unresolved_blockers=0，P0=0/P1×1/P2×3/P3×5` → provably_zero=**False**（探针实证）——Design P1-1 blocker 修复兑现
- 词法细节：前瞻 2 扫描 `^` 锚定的 token 全体（= 附着细目窗口），`P[01]` 不误触 `P10=2`（`0` 非 `[=×xX]`）

### 2. 解析器 malformed-value 分支完整余量捕获 ✅（重点审查项）
`review_domain.py:1745-1753`：invalid token 从截断值 `f"unresolved_blockers={raw_value}"` 改为 `field[key_match.start():].strip()`（与 no-value 分支同约定）。**下游消费方封闭性核实**（grep 全量 25 处）：
- `_blocker_evidence_provably_zero`（唯一行为消费方——本变更的目的窗口，`=0，P0 = 2` 带空格计数入证）
- `_merge_missing_with_valid` / `_merge_unresolved_blocker_evidence`：以 invalid_tokens 重建 fields 再解析——重解析对全余量 token 幂等（key 锚定重现同一余量），实测路径稳定
- V5 violation detail 串只用 status/values；`legacy_invalid_tokens` 走独立 legacy 键路径不受影响
- 无其他消费方（无展示/持久化代码读 canonical invalid_tokens）
结论：影响面封闭，无未审计消费方。

### 3. 行入口 source_format="machine" ✅ —— 见 §二 P2-2 行。

### 4. known_rounds 索引化 + `_next_round_discharged` ✅（附残留下界 P3-5）
文件级（`review_domain.py:2852-2853`）与行级（L2913-2916）两豁免点同步收紧；base_date 在两处均非 None（未 dated 记录在到达豁免点前已 continue）——无 None 比较陷阱。

### 5. W-7 断言收紧 ✅ —— 见 §二 P2-1 行。live 探针：R0 规则→R1 谓词翻转仅 1 例（AUDIT-143，见 P2-3）；R0 实测 4 误伤形态全部回落 ACTIVE。

### 6. 新增 21 测试 ✅
- 绿相：`ReworkR1BoundaryTests` 7 + `ReworkR1DischargeScopeTests` 4 + `W7TerminalSegmentScopeTests` 10 = 21 全过（两 review 文件累计 62 passed；test_verify_workflow 两 W-7 类 19 passed）
- **红相（对 R0 代码沙箱——当前文件结构化回退 7 处 R1 区域，py_compile 过，红绿分布行为验证重建保真）**：Boundary 5 failed/2 passed + Discharge 3/1 + W7 6/4 = **14 failed / 7 passed——与声明精确一致**；红相通过项恰为绿字面守卫（P2-nonzero WARN 保持 / 歧义值保持拒 / dated-valid 豁免保持 / 3 个转移终态保持 + reopened 保持）——非形式化，锁定方向正确

---

## 四、Developer 声明数字独立复核

| 声明 | 复核 | 结果 |
|---|---|---|
| 红相 14 failed/7 passed | R0 沙箱（%TEMP% 结构化回退）分文件运行 | **14/7 精确一致**（5+2 / 3+1 / 6+4）✓ |
| 全量 2095 passed = 2074+21 | 工作树全量 | **26 failed / 2095 passed** ✓；失败集 = R0 同三类存量（cleanup manifest / loop_runtime 计时抖动本轮 failed / pre_commit WSL hook），零新增 |
| live 计数（未逐项声明，R0 基线对照） | Check 30 = FAIL/7 viol/24 warn（task 集与 R0 完全一致）；30c = WARN/2（V7:2）；rows_non_review=164；check-governance = **149**（R0 亦 149） | 全部与 R0-post 一致 ✓ |
| 5 文件 +1168/-23 | git diff --stat | ✓（R0 时 +686/-20，增量 +482/-3） |
| py_compile | 五文件 | OK ✓ |
| 工程卫生 | diff 扫描 | 零 TODO/mock 残留（测试基建 patch 除外）/硬编码（REL-070 等仅注释）✓ |

---

## 五、Findings（R1 新发现）

### P0 / P1：无

### P2-3 W-7 R1 收紧引入未披露的 live 谓词翻转——AUDIT-143（合法终态措辞漏判，保守方向）
- **位置**: `verify_workflow.py:10237-10266`（断言规则）+ `10298-10303`（完成( 兜底不命中复合措辞）
- **事实**: live 探针（196 行，R0 规则 vs R1 谓词）：翻转恰 1 例 = **AUDIT-143** `⏳ 审计中 (2026-08-17) → ✅ 分析完成+规划落地 (2026-08-17)——DEC-143；REQ-107~114 入需求`。HEAD 与 R0 均判 completed（HEAD ✅ 分支无 active 词命中；R0 trailing ✅ marker 位置胜）；R1 判 **ACTIVE**：✅ 非断言（rest=`分析完成+…` 非日期括注）、无词表终态词、`完成\s*[（(]` 兜底不命中（"完成+"非"完成（"）。completed 集 185→184（换出 AUDIT-143、换入 REL-069，净数恰平）。
- **影响**: 方向 = BC-7 fail-safe（漏降级而非误降级）；治理检查零 delta（Check 30/30c/check-governance 149 全不变——AUDIT-143 无 review 链且不触发任何活跃任务检查增量）。但：(a) 相对 HEAD 是真实行为回归（真终态任务重新判 ACTIVE）；(b) 返工摘要声明了「红 ×6/绿 ×4」却**未披露该 live 翻转**。
- **建议**: 遗留跟踪——覆盖 `✅ <复合措辞>…完成…(date)` 形态（如 ✅ 限定段内含「完成」且段尾带日期括注即视为终态断言），或明示接受该保守漏判并补披露/守卫测试（断言 AUDIT-143 形态的预期判定）。

### P3-5 `_index_record` 合并语义解耦（max-date + OR-valid）
- **位置**: `review_domain.py:2752-2762`。entry 取跨记录**最新日期**与**任一有效**——若某轮唯一有效记录 dated < base 而另一 UNKNOWN 记录 dated ≥ base，合并后 (date=最新, valid=True) 误放行豁免。逐记录判定（exists record: valid ∧ date ≥ base）为精确式。需轮号倒置 + 混合结论同号记录复合形态触发（R1 测试已封 older/unknown 单独形态）。不阻塞，建议后续把 `_index_record` 改存记录列表。

### P3-6 非 marker 现行手写行仍为 unknown(0)
- **位置**: `review_domain.py:2553-2557`。无 marker 的 REVIEW 行（dated ≥ 生效日的 V7 违规行本身）不击穿 historical 分类（rank 0）。设计取舍：仅 CLI 机录行可证 machine(2)。触发需「现行手写行 + 同轮历史文件」复合形态，且该行自身已被 30c V7 WARN 披露。记录备查。

---

## 六、五维度 + AI 专项（增量）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ | §三 1-5 逐行 + 双前瞻正则逐案 + 消费方封闭性 grep |
| 安全性 | ✅ | 无新增输入执行面；日期解析 `date.fromisoformat` 带 ValueError 捕获（`review_domain.py:2797-2800`） |
| 可维护性 | ✅ | 断言规则/豁免语义带 R0/R1 出处注释；`_next_round_discharged` 语义自文档 |
| 性能 | ✅ | known_rounds dict O(1)；断言扫描词表 × 文本有限 |
| 测试覆盖 | ✅ | 21 新测试 = 11 红相修复锁证 + 7 绿字面守卫 + 边界（reopened/无日期段首）；红绿分布独立复现 |

AI 专项 5 项：mock 残留无（测试 patch 除外）/硬编码无/幻觉 API 无（`_file_date`、`_normalize_review_conclusion`、`_extract_review_conclusion_from_text` 均经 read 核实存在且语义核对）/TODO 无/过度实现无（6 项增量逐一对应 R0/Design findings 与 live 实证形态）。

---

## 七、验证证据（R1）

1. `py_compile` 五文件 OK；两 review 测试文件 62 passed；W-7 两类 19 passed
2. live：Check 30 FAIL/7/24（= R0-post，task 集一致）；30c WARN/2（V7:2，stats rows_scanned 358/rows_judged 72/rows_machine 70/rows_non_review 164——较 R0 +2 行/文件为机录增量，非判定漂移）；check-governance 149；FIX-254 形状 provably_zero=False
3. W-7 三代谓词 A/B（196 行）：HEAD→R1 翻转 = [AUDIT-143(True→False), REL-069(False→True)]；R0 规则→R1 翻转 = 1（AUDIT-143）
4. R0 红相沙箱（%TEMP%\fix291_r1red：当前 infra 副本 + 7 处 R1 区域结构化回退至 R0 文本；py_compile 过）：ReworkR1Boundary 5F/2P、ReworkR1Discharge 3F/1P、W7SegmentScope 6F/4P = **14F/7P**
5. 全量：26 failed / 2095 passed（= 2074+21 ✓；失败集与 R0 三类存量一致，零新增）
6. invalid_tokens 消费方 grep（25 处）封闭性核实；diff 卫生扫描零残留

## 八、硬门槛自检

- [x] P0 = 0；[x] 5 维度覆盖；[x] 每条发现标注级别（P2×1 + P3×2）；[x] 设计一致性（与 Design R0 findings 处置对应核实）；[x] AI 专项 5 项；[x] 只读审查（除本报告外零仓库写入；沙箱/探针均在 %TEMP%）；[x] 前轮 findings 逐条比对（已修复/未修复/新引入——见 §二、§五）；[x] round 号与前轮引用声明（头部）

## 九、终态

**APPROVED_WITH_NOTES — unresolved_blockers=0**

- R0 P2×2 已修复且锁证；新增 P2-3（AUDIT-143 未披露 live 翻转，保守方向零检查 delta）建议遗留跟踪或补守卫测试
- 后续归 Coordinator：review-record 机录（round 3）/ T1 判定（本终态为通过态，无 NEEDS_CHANGE 复审义务）/ P2-3、P3-5、P3-6 遗留入账 / commit 安排
