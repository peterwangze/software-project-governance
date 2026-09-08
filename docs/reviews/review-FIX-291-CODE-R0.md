# 审查报告：FIX-291 — 判定面批代码审查（Code Reviewer · R0）

- **Task ID**: FIX-291
- **Reviewer**: Code Reviewer Agent（独立复审，非 Developer 自审）
- **Round**: R0
- **审查对象**: 工作树未提交 diff（`git diff` + `git status --short`，5 文件，+686/-20）
- **审查日期**: 2026-09-09
- **判定语义面**: 由并行 Design Reviewer 负责（`docs/reviews/review-FIX-291-DESIGN-R0.md`）；本报告聚焦代码正确性

---

## 一、结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

核心逻辑正确、边界锁定测试真实有效、Developer 验证数字经独立抽样复核全部成立（1 项 pre 状态无法在不触碰工作树的前提下忠实复算，已标注并给出等效佐证）。发现 2 项 P2（非阻塞，建议遗留跟踪）+ 4 项 P3（讨论/记录）。无 P0/P1。

---

## 二、审查对象与实现落点（焦点 6）

| 文件 | 变更 | 落点正当性 |
|---|---|---|
| `infra/checks/review_domain.py` | +206/-8 | ✅ Check 30（`check_review_closure` / `_build_review_sequence` / `_collect_live_review_sequences` / `_parse_unresolved_blockers_fields`）与 Check 30c（`check_review_machine_provenance`）的实现体均在本文件（grep 核实：L2040-2396、L2613-2885）——0.71.0 薄入口化后 checks/ 子包即实现落点，扩展正当 |
| `infra/verify_workflow.py` | +55/-2 | ✅ W-7 谓词 `_status_is_completed_cell`（L10223）的定义位置；经 `_SHARED_NAMES` 桥（review_domain.py L98 `_status_is_completed_cell`）每次调用回灌 review_domain 的 completed 集——耦合路径成立，两处必须同变更集 |
| `infra/tests/test_review_closure_legacy.py` | +227 | 新增 `HistoricalFileShapeTests`（8 测试，live 通道 tempdir + mock.patch 路径） |
| `infra/tests/test_review_machine_provenance.py` | +140 | 新增 `MachineRowClassificationTests`（7 测试） |
| `infra/tests/test_verify_workflow.py` | +78 | 新增 `StatusCellMixedTerminalMarkerTests`（9 测试） |

---

## 三、逐焦点结论（checklist）

### 焦点 1 — diff 正确性逐行 ✅

- **source_format 分类**（review_domain.py:2553-2572）：marker in 内容 → `machine`；无 marker 且无 `- date:` 字段 → `historical`；有 date 无 marker → `machine_format`。三分支完备，IOError → `unknown`（保守）。live 实测分类：machine=58 / historical=29 / machine_format=0。
- **rank 合并**（L1955-1959）：`machine(2)=machine_format(2) > historical(1) > unknown(0)`，仅高 rank 覆盖——单调，无降级回退。⚠ 存在 rank 倒置豁免面（见 P2-2）。
- **provably-zero 正则**（L1682 `^unresolved_blockers=0(?!\d)`）：与解析器语义精确咬合——实测 `0，P0=0/…` → True（全角逗号 U+FF0C 不在值终止符类 `[^\s,;|`*]` 内，故整段附着值以单个 invalid token 进 `invalid_tokens`，review_domain.py:1729-1737 逐行核实）；`02，`/`10，` → False（fail-closed 成立）。`_blocker_evidence_provably_zero`（L1687-1704）要求 status=invalid 且全部 values=0 且全部 invalid token 可证零——nonzero/conflict/missing 均不触发。
- **V2 历史形状门**（L2143-2155）：置于 L-A 之后、violation 之前；`all rounds historical` + completed → WARN；ACTIVE / 任一轮 machine·machine_format·unknown → FAIL 保持。与 L-A（仅前导）、FIX-173 命名豁免的顺序与优先级正确。
- **V5 历史形状门**（L2335-2353）：`terminal round historical` + completed + 非 legacy_nonzero/unparsed +（missing 或 provably-zero）→ WARN；valid nonzero、conflict、ambiguous invalid 均落入原 violation 分支（L2354）。与 FIX-233 日期豁免、L-B legacy 豁免不冲突（三者输入正交：日期 / legacy 键拼写 / 文件形状）。
- **30c ID 列锚定**（L2794-2803）：`parts[1].strip("*` ")` 剥离粗体/反引号修饰后 finditer——粗体锚定有测试（`test_row_id_cell_bold_markdown_still_anchors`）；EVD-/RECO- 提及行入 `rows_non_review` 计数不入判。
- **V8 溯源豁免**（L2774-2786 文件级 / L2842-2847 行级）：`known_rounds`（L2727-2741）= 新格式文件名 + ID 列行解析的 (task, round) 对；豁免 `continue` 位于 `for cid in ids:` 内层——不跳过外层任何逻辑（核实 L2828-2860 循环结构）。
- **W-7 谓词**（verify_workflow.py:10240-10258）：规则顺序 未完成/待完成 → 已完成 → ✅无 active → **trailing-terminal** → 完成( 兜底；`_last_marker_pos` 用 rfind 取最右位置。「推进中」入 trailing ACTIVE 集但不在 ✅ 排除集——版本上下文格（0.78.0 已发布，0.79.0 推进中）保持 ACTIVE 有测试锁定。

### 焦点 2 — 边界锁定回归测试质量 ✅（真实断言，非形式化）

边界用例在红相（HEAD 代码）下即通过、绿相下仍通过——锁定的是既有 fail-closed 行为而非新逻辑的空转：

| 边界 | 用例 | 红相 | 绿相 |
|---|---|---|---|
| ACTIVE 恒 FAIL | `test_historical_file_gap_on_active_task_stays_fail`（ARCH-105 ⏳） | PASS | PASS |
| 历史 nonzero 恒 FAIL | `test_historical_file_v5_nonzero_stays_fail`（ARCH-106 =2） | PASS | PASS |
| 现行机器格式不放宽 | `test_machine_file_gap_stays_fail`（ARCH-107 marker+date，中缝缺轮） | PASS | PASS |
| 无 R+1 记录恒 WARN | `test_needs_change_row_without_next_round_record_still_warns_v8`（FIX-314） | PASS | PASS |
| 现行手写行恒 V7 | `test_handwritten_review_row_still_warns_v7`（FIX-300） | PASS | PASS |
| active 收尾保守 | `test_active_trailing_after_terminal_stays_active`（reopened） | **FAIL**（旧谓词误判 completed——本修复的目标缺口之一） | PASS |

### 焦点 3 — 测试诚实性 ✅（全部独立复核）

| Developer 声明 | 独立复核方法 | 结果 |
|---|---|---|
| 红相 14 failed | HEAD 代码沙箱（`git archive` → %TEMP%，不触碰工作树）+ 新测试文件叠加 | **精确 14**：closure 5 + provenance 4 + W-7 5（另 4 个 InjectionAnchor 失败为沙箱缺 references/ 文件的伪影，非本变更测试） |
| 绿相 24/24 | 工作树运行三个新测试类 | 8+7+9 = 24 全过 ✓ |
| 三文件 60/60 | 全量运行两个 review 域文件 + W-7 类 | 29+22+9 = 60 全过 ✓（60 = 两文件全部 + test_verify_workflow 新类，口径成立） |
| live Check 30 不变 | HEAD 沙箱（补 references/ 修复路由表伪影后）vs 工作树，同 live 数据 | **精确一致**：FAIL / 7 viol / 24 warn，warning 集合 set-diff 为空（首轮沙箱缺 references 出现的 SYSGAP-030 V1 漂移已定位为伪影并消除） |
| 30c 35 WARN→2 | 同上 A/B | HEAD 35（V7:33, V8:2）→ post 2（V7:2）✓ |
| rows_non_review 164 | live stats | 164 ✓ |
| historical 29 files | live 文件分类复算 | 29 ✓（review-ADR-006/007、review-FIX-041 等） |
| 全量 pre 26/2050 → post 26/2074 零新增 | post 全量×2 + pre 全量沙箱×1 | post run2 = **26/2074 精确一致**（run1 = 25/2075，差异为 `test_three_run_performance_identity_and_median` 计时敏感抖动）；pre 沙箱 = 27/2049 = 同三类存量 + 1 个 git 缺失伪影（release_ledger 0.6.6.1 测试）+ 同一抖动测试；**post 失败集 ⊆ pre 失败集，零新增成立**；存量三类（cleanup manifest / loop_runtime 计时 / pre_commit WSL hook）成员逐一相同 ✓ |
| 26 vs 27 基线漂移披露 | 见上 | 如实——本审查独立复现同一漂移（25↔26↔27 随计时浮动），漂移源为单一性能测试，与被审代码无关 |
| check-governance 149→149 | post 直跑 = 149 ✓；pre 无法忠实复算（stash 类对照需触碰工作树，沙箱缺 .git 产生 971 伪影、混合补丁法不可靠） | post ✓ / pre **未验证**——由「Check 30 逐条不变 + 30c WARN 单调下降 33 条 + 全量零新增」等效佐证方向，不构成阻塞 |

### 焦点 4 — 安全/回归风险 ⚠ 两项 P2（非阻塞）

见 findings P2-1（W-7 词表散文误伤面）、P2-2（rank 倒置豁免面）。两者 live 影响均为零（W-7 live 翻转恰 1 例 = REL-069 预期目标，196 行逐一比对；rank 倒置需「机录行 + 同号文件被手写覆盖」复合形态）。

### 焦点 5 — 工程卫生 ✅

- 零 mock 残留（diff 中 mock 仅出现在测试文件的路径 patch——合法测试基建）
- 零硬编码（REL-070/FIX-260/EV-066/ARCH-002 全部仅存在于注释/文档串，grep 逐行核实）
- 零 TODO/FIXME/XXX
- `py_compile` 五文件全过
- quality-tools NOT_RUN 如实（无 lint/type 工具调用声明，无伪造通过记录）

---

## 四、五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | 焦点 1 逐行 + 边界探针（rank 合并、provably-zero 四例、W-7 四例全部实测） |
| 安全性 | ✅ 通过（无新增面） | 纯本地判定逻辑，无外部输入执行/注入面；词表仅用于字符串位置比较 |
| 可维护性 | ✅ 通过 | 分类/门规则带出处注释（FIX 编号 + router 证据编号可追溯）；命名表意；`rows_non_review` stats 字段用 `.get(...,0)` 兼容旧结果 |
| 性能 | ✅ 通过 | `known_rounds` set O(1) 查询；`_last_marker_pos` 9×rfind 有限词表；live 全量 30c 扫描 356 行/270 文件无感 |
| 测试覆盖 | ✅ 通过 | 24 新测试覆盖 3 正向形态 + 5 边界锁定 + 3 回归保持；红→绿证据链完整且经独立复现 |

## 五、AI 代码专项 5 项

| # | 检查 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无（测试基建 patch 除外，合法） |
| 2 | 硬编码返回值 | 无 |
| 3 | 幻觉 API 调用 | 无——全部调用既有函数（`_parse_unresolved_blockers_fields`、`_REVIEW_FILE_NAME_RE` 等）均经 read 核实存在 |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 无——三个子项均对应 router 实证缺陷形态（EV-066 V2×9/V5×2、WARN 10→13、REL-069），live 数字逐一兑现 |

---

## 六、Findings

### P0（阻塞）：无
### P1（关键）：无

### P2-1 W-7 trailing-terminal 规则作用域宽于文档声明——散文误伤面（fail-open 方向）
- **位置**: `skills/software-project-governance/infra/verify_workflow.py:10252-10257`
- **事实**: 规则对**所有**状态格无条件生效（docstring 框定为 mixed transition chains）。实测（探针，2026-09-09）：`"🔄 进行中——方案A已撤回，改推方案B（等待排期）"`、`"⏳ 待执行 (v0.78.0 已发布后启动)"`、`"🔄 进行中——依赖令牌失效，等待更换"`、`"⏳ 待执行——原定时窗口取消，重新排队"` → 全部判 completed=True。终态词（已撤回/失效/取消/废弃/已发布…）出现在 active 词之后的**任意散文位置**即翻转。
- **影响**: 活跃任务被误判终态 → 从 P0 活跃检测（verify_workflow.py:10652）、status_map（L10612）、done 列表（L10403）消失，且使 Check 30 L-A WARN 降级门槛（completed）被误满足——掩盖方向。**本仓 live 影响今日为零**（196 任务行新旧谓词逐行 diff，翻转恰 1 例 = REL-069 预期目标），但本插件发布至用户仓库，散文形态不可枚举。
- **建议**: 遗留跟踪——将 trailing 规则限定于转移边界（终态 marker 前邻 `→`/行首/✅，或终态段为独立状态即后邻日期/行尾），或对 active 词与终态词同现的格维持保守 ACTIVE（仅信任 `→` 分隔的显式转移链）。

### P2-2 source_format rank 合并对「现行格式 evidence 行」不设防——与文档声明相悖的豁免面
- **位置**: `skills/software-project-governance/infra/checks/review_domain.py:1955-1959`（rank 合并）、`2528-2534`（行入口无 source_format）；文档声明 `1884-1901`（"a current-format contribution to a round always breaks the provably-historical classification"）
- **事实**: live evidence 行入口不携带 `source_format` → 缺省 `unknown`（rank 0）→ **低于** historical（1）。实测：同轮「机录行（unknown）+ 历史手写文件（historical）」合并后 round = `historical`。即现行格式的**行**贡献无法击穿历史分类，只有文件贡献（machine=2）可以——文档声明在行贡献上不成立。
- **影响**: 需复合形态触发（review-record 机录行 + 同号文件被手写历史形状覆盖），触发后 all-historical 链误判 → V2/V5 FAIL 误降 WARN（fail-open）。live 今日无实例。
- **建议**: 遗留跟踪——`_collect_live_sequences` 行入口按 `REVIEW_MACHINE_ROW_MARKER` 分类（marker 在行内 → `source_format="machine"`），使行贡献同样 rank 2。

### P3-1 provably-zero 边界接受 `0`+ASCII 字母附着
- **位置**: `review_domain.py:1682`。实测 `unresolved_blockers=0abc` → True。`0件`/`0个` 类 CJK 附着合理；`0x…` 类十六进制暗示虽极端牵强仍属可辩区间。建议后续收紧为「0 后随非 ASCII 字母数字」。不阻塞。

### P3-2 30c 锚定后 REVIEW id 仅存在于关联ID列（parts[2]）的行不再受判
- **位置**: `review_domain.py:2794-2803`。旧全行 finditer 会判、新 ID 列锚定不判。live 164 条此类行全部为 EVD-/RECO- 交叉引用（分类正确）；Check 30 行入口（L2517-2521）仍匹配 parts[1]∪parts[2]——两检查口径自此有意分叉。现行机录约定 id 在 ID 列，可接受；如未来出现关列记录形态需 revisit。

### P3-3 known_rounds 不校验日期/时序
- **位置**: `review_domain.py:2727-2741, 2846`。无日期行、早于 NEEDS_CHANGE 写入的 R+1 记录均可豁免 V8。合作语料假设 + FIX-260 已登记不可伪造侧记录升级路径，记录备查。

### P3-4 复合测试的失败归因
- `test_historical_file_leading_gap_on_mixed_terminal_status_warns` 同时耦合 W-7 与历史形状两修复（这是其目的——router V2×9 复合形态等效）；单独回归定位时需读测试注释。可接受。

---

## 七、验证证据（复核命令与输出摘要）

1. `py_compile` 五文件 → OK
2. `pytest tests/test_review_closure_legacy.py tests/test_review_machine_provenance.py` → 51 passed；`-k StatusCellMixedTerminalMarkerTests` → 9 passed
3. live 探针：Check30 post FAIL/7 viol/24 warn；30c post WARN/2（stats rows_non_review=164, rows_machine=68, files_judged=58）；文件分类 machine=58/historical=29/machine_format=0
4. HEAD 沙箱（%TEMP%\fix291_red，git archive HEAD infra+references + 新测试）→ 红相 14 failed（5+4+5）；HEAD live Check30 = FAIL/7/24（与 post 集合 diff 为空）；HEAD 30c = 35（V7:33/V8:2）
5. W-7 谓词 A/B（parse_task_dependencies 196 行，旧谓词按 diff 删除行忠实重建）→ 翻转 1 例：REL-069（old=False→new=True）
6. 全量 A/B：post（工作树）run1 25 failed/2075 passed、run2 26/2074（差异 = test_loop_runtime_claims 计时抖动）；pre（%TEMP%\fix291_head_full = git archive HEAD 全树 + .governance 副本）27/2049 = post 三类存量全含 + release_ledger git 伪影 + 同抖动；**post-only 失败 = 0**
7. check-governance：post = 149 issue(s) ✓；pre 忠实复算不可行（需 stash 触碰工作树），未验证（不阻塞，等效佐证见焦点 3）
8. 边界探针：rank 合并 row(unknown)+file(historical)→historical；provably-zero 四例；W-7 散文四例（结果见 P2-1/P2-2/P3-1）

## 八、硬门槛自检

- [x] P0 阻塞问题数 = 0
- [x] 5 维度全覆盖（§四）
- [x] 每条发现标注级别（P2×2 + P3×4）
- [x] 设计一致性检查完成（与 review-FIX-291-DESIGN-R0 判定面分工正交；与 FIX-278 L-A/L-B、FIX-233 日期豁免、FIX-174 命名豁免的优先级/输入正交性核实）
- [x] AI 代码专项 5 项逐一有结论（§五）
- [x] 只读审查——除本报告外零仓库写入（沙箱/探针均在 %TEMP%；测试运行 `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1`）
- [x] 每条 finding 引用文件+行号；Developer 声明抽样复核（§三表）

## 九、终态

**APPROVED_WITH_NOTES — unresolved_blockers=0**

- P2×2 建议遗留跟踪（W-7 词表收边、行入口 source_format 分类），不阻塞本变更合并
- 后续动作归 Coordinator：commit 安排 / review-record 机录 / 遗留项入账
