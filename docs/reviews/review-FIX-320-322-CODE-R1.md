<!-- machine-suggested-next-round: 无（通过终态，复审链关闭） | round: R1 | reviewer: Code Reviewer (subagent, 同 R0 审查方) | verdict: APPROVED_WITH_NOTES | unresolved_blockers: 0 -->

# FIX-320 + FIX-322 合并代码审查 R1 复审（REVIEW-FIX-320-322-CODE-R0 退回修复核验）

- **round: R1**（复审轮）；前轮引用：`docs/reviews/review-FIX-320-322-CODE-R0.md`（NEEDS_CHANGE，P0=0，P1=1〔F-1〕，P2=1〔F-2〕，P3=4〔F-3~F-6〕，unresolved_blockers=1）。
- 审查对象：R0 同批 6 文件工作树未提交改动的 R1 增量（git status 实测与 R0 完全同集：5 M〔`infra/checks/dsh_boundary.py`、`infra/checks/loop_runtime_claims.py`、`infra/tests/test_dsh_boundary.py`、`infra/tests/test_dsh_contract.py`、`infra/tests/test_loop_runtime_claims.py`〕+ 1 untracked〔`core/loop-runtime-claim-exemptions.json`〕+ R0 报告自身 untracked）；R0 后并行批 A（FIX-342/344）已入库为 HEAD `f73bef7`（不含 dsh_boundary 面，与 R0 的批间隔离假设一致）。
- 审查者：Code Reviewer（R0 同一审查方）。只读 + 唯一写入本报告；红相反相在 %TEMP% 镜像（789 文件 = 788 git 跟踪 + 账本，真实仓库零改动、零 commit、零 stash）。
- **结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**。F-1（P1）处置充分、F-2（P2）修复经三面独立复现成立、无新引入、无回归。保留备注均为 P3 级披露/闭环时落账项，无未解决阻塞。

---

## 1. R0 findings 逐条比对（已修复/未修复/新引入）

| R0 ID | R0 级别 | R1 状态 | 事实依据 |
|-------|---------|---------|----------|
| F-1 | P1 | **已修复（处置充分，阻塞解除）** | plan-tracker L109 **FIX-346 行存在且要件齐**（裁决见 §3）；完成口径修正承诺（「verdict/identity 自愈；性能断言待定标」）由 Coordinator 闭环落账 |
| F-2 | P2 | **已修复（三面复现成立）** | `checks/dsh_boundary.py` L541 规则 `rest.startswith(("/", "@"))` + L532-537 注释显式记录双定界符语义并引 F-2/R0 + 2 新测试（L277 负相 / L298 守卫）；复现见 §2#1-3 |
| F-3 | P3 | 处置计划核验通过 | EVD 口径注记（「37 处 @literal」盘点口径）随 Coordinator 闭环落账——EVD 尚未写，与 FIX-320/322 行仍 ⏳ 的状态自洽；闭环时核对，非阻塞 |
| F-4 | P3 | 处置计划核验通过 | 同上（「8 测试」方法数口径注记） |
| F-5 | P3 | 维持披露 | 账本 artifact_role 显式登记仍为可选改进（`core/` 整目录声明覆盖、cleanup clean 未变），无功能风险 |
| F-6 | P3 讨论 | 维持披露 | 同五元组重复豁免理论面，现景不可达 + 逐条披露自足，仅记录 |
| 新引入 | — | **无** | git status 同集无新增文件；R1 增量面 = dsh_boundary.py（规则行 L541 1 处替换 + 注释 L534-537 扩写引 F-2）+ test_dsh_boundary.py（+2 方法，134→136）。注：R0 态无 git 快照，字节级 ±2/−2 不可复算，「+2/−2」申报在观测精度内一致（口径如实注明）；test_dsh_contract 仍 120（256−136），loop/archguard 失败身份逐字段未变 |

## 2. 独立复现记录（全部当场执行）

| # | 验证项 | 手段 | 实测结果 |
|---|--------|------|----------|
| 1 | **F-2 红相**（HEAD/R0 态复现 `0 != 1`） | %TEMP% 镜像 789 文件 + 镜像内规则退回 `startswith("/")`，`unittest tests.test_dsh_boundary.K2OutsideContractTests -k version_suffix` | `test_negative_a_version_suffixed_undeclared_package_is_caught` **FAIL: `AssertionError: 0 != 1 : []`**（旧规则漏检 `@…@^1.2` 形态）；守卫 `test_positive_a_declared_package_with_a_version_suffix_is_accepted` 绿（该守卫在双态下均绿，锁的是零误报向）——exit 1 |
| 2 | **F-2 绿相** | 镜像恢复工作树版（新规则），同命令重跑 | 2 tests **OK**，exit 0——红→绿成立，全程真实仓库零写入 |
| 3 | boundary+contract 全套（真实树） | `python -m unittest tests.test_dsh_boundary tests.test_dsh_contract`（infra cwd） | **256 tests OK**（boundary=136〔134+2 与申报一致〕，contract=120 不变） |
| 4 | K-2 实树 | `verify_workflow.py check-dsh-boundary` | `[PASS] K-2: outside-contract host literals: 0 (11 declared consumer(s) scanned)` 逐字吻合；全判据 PASS 0 failing，exit 0 |
| 5 | loop 套件（真实树） | `python -m unittest tests.test_loop_runtime_claims` | **59 tests / 恰 2 FAIL，与 R0 基线身份逐字段一致**：① `test_real_repository_inventory_complete_and_within_budget` = 2×AUTHORITY_SOURCE_OCCURRENCE（decision-log + plan-tracker "found 0"，FIX-345 域既有红）；② `test_three_run_performance_identity_and_median` L1082 verdict BLOCKED（严态 4 classify findings = 账本未跟踪时既有红，即 F-1 记录的 commit 后自愈面）。无新失败 |
| 6 | archguard | `verify_workflow.py archguard-ratchet` | PASS（0 violations；regen deterministic=True），exit 0 |
| 7 | `@` 规则边界（内存态，实际模块语义） | 导入 `checks.dsh_boundary` 对 12 个边界字面量实测 `_PACKAGE_RE.match` + rest 判定 | 见 §4 裁决表 |

## 3. F-1 处置充分性裁决（P1 阻塞解除的依据）

F-1 的阻塞实质是「完成声明自愈范围过宽 + 性能预算缺口无任务承接」（R0 已明示非代码返工面）。处置两腿均成立：

1. **登记腿（可验证，已落地）**：plan-tracker L109 FIX-346 行要件齐全——P3 定级；合并范围①（`test_three_run_performance_identity_and_median` L1083 `median<8.0s` 硬编码，实测 13.3~17.0s 超支 66%~113%，parallel 负载协变量已考虑——与 R0 §2#15 独立实测同源）+ ②（adapter 15s 超时 vs 全仓扫描 ~50s+，EVD-1030）= R0 遗留③ 合并，与 R0 §6.1 建议（可与 adapter 15s 合并一个独立小任务）一致；修法方向 = 预算重定标非放宽断言语义；来源可追溯（REVIEW-FIX-320-322-CODE-R0 F-1 P1/遗留③ + EVD-1030）；目标 0.82.0 与 R0 建议一致；归属（测试面 Developer → Reviewer）与验收（空闲环境三轮复测定标 + 断言更新 + **反相（预算减半仍红）**）可测；状态 ⏳ R0 转承登记。
2. **口径腿（承诺，闭环时落账）**：完成口径将修正为「verdict/identity 自愈；性能断言待定标」——与 R0 F-1 要求的措辞一致；当前 FIX-320/322 行仍 ⏳（闭环未发生），无残留的过宽完成声明在册。

**裁决：充分**。两腿合计覆盖 F-1 的返工面；登记腿为硬事实、口径腿有明确落账时点（闭环），且 loop 套件复跑（§2#5）证明性能红的存在形态与 FIX-346 描述完全一致。

## 4. `@` 规则边界裁决（以实现语义为准）

内存态实测（真实模块 `_PACKAGE_RE` + rest 判定，12 形态）：

| 字面量形态 | match？ | rest | 触发？ | 裁决 |
|------------|---------|------|--------|------|
| `@scope/pkg` | ✓ | 空 | ✓（基线负相威力保持） | 与 R0 一致 |
| `@scope/pkg@^1.2` | ✓ | `@^1.2` | ✓（**F-2 修复目标形态**） | 修复生效 |
| `@scope/pkg@`（裸尾 @） | ✓ | `@` | ✓ | 简并形态仍为包引导引用；触发方向保守（漏检比误报危害大，且上报 token 为包名、K-2 输出可见可豁免）——**可接受** |
| `@scope/pkg@/sub`、`@scope/pkg@1.0/sub` | ✓ | `@/…`、`@1.0/…` | ✓ | 包引导连续体，同上可接受 |
| `a@b` / `user@host` / `peter@example.com` | ✗ | — | ✗ | `_PACKAGE_RE` 要求字面量以 `@scope/name` **开头**，非包形态 `@` 字面量结构性免疫——**新规则零新增误报面** |
| `@scope@name/pkg` | ✗ | — | ✗ | scope 字符类不含 `@`，畸形形态不入判定 |
| `@scope/pkg/other@thing` | ✓ | `/other@thing` | ✓ | 经 `/` 分支，与 R0 一致 |
| `see @scope/pkg here`（句子） | ✗ | — | ✗ | 整串判定锚定起点，prose 不触发（FIX-322 核心语义保持） |

**裁决：不需追加注记**。注释「`@`-prefixed rest is a version tag of the same package」的措辞略窄于实际触发集（裸 `@`、`@/…` 亦触发），但行为是保守并集（rest 以包延续定界符开头即归属），方向安全、两新测试+守卫已锁主形态、实树 0 触发无观测反例。仅作本节记录，不设 finding。

## 5. 五维度 + AI 专项 + 硬门槛（针对 R1 增量面）

**五维度**：正确性 PASS（规则行 + 注释 + 测试三者语义一致；红→绿双态实测；`@` 边界 12 形态实测）；安全性 PASS（增量无输入面/副作用变化；镜像反相零仓库写入）；可维护性 PASS（注释引 F-2/R0 可追溯，docstring 如实；无重复）；性能 PASS（规则为常量定界符检查，O(1) 增量，无扫描面扩大）；测试覆盖 PASS（负相红→绿 + 零误报守卫 + 实树 0 + 边界形态实测）。

**AI 专项 5 项**（增量面 = 1 规则行 + 注释 + 2 测试）：mock 残留 无；硬编码返回值 无；幻觉 API 无（`scan_outside_contract_literals`/`_PACKAGE_RE` 均经运行验证）；未实现 TODO 无；过度实现 无（最小增量，无顺手改）。

**硬门槛**：P0=0；P1=0（F-1 解除）；5 维度 100% 覆盖；每条发现已标级；设计一致性 = FIX-346 与 R0 §6.1 处置建议一致、F-2 修复与 R0 建议选项双落地（注释 + 守卫测试）、上报 literal 保持包名 token（L543 `group(0)`）与 K-2 语义一致；AI 专项 5 项完成。

## 6. 保留备注（非阻塞，P3）

1. F-3/F-4：EVD 口径注记由 Coordinator 闭环时落账（EVD 尚未写）——闭环时核对注记确实含 R0 §4 指明的两种口径。
2. F-5/F-6：维持 R0 披露，无动作要求。
3. §4 裁决记录：注释措辞略窄于触发集（保守方向），已记录不设 finding。
4. loop 套件 2 既有红与 archguard/K-2 的 PASS 态不构成回归：失败身份与 R0 §2#5 逐字段一致，且分别由 FIX-345/FIX-346 承接。

---
*审查证据全部来自本会话当场命令输出；红相反相在 %TEMP% 镜像执行（真实仓库零改动），其余为只读命令与内存态探针。报告生成：R1，基线 HEAD `f73bef7` + 6 文件工作树批。复审链：R0 NEEDS_CHANGE/1 → **R1 APPROVED_WITH_NOTES/0，复审链关闭**。*
