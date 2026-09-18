# FEAT-035-DESIGN-R1 — 迁移退出启动关键路径 · 独立设计复审报告（R0 findings 修复验证）

- **Round**: R1（复审轮——复审纪律：逐条比对前轮 findings，标注已修复/未修复/新引入）
- **前轮引用**: `docs/reviews/review-FEAT-035-DESIGN-R0.md`（结论 NEEDS_CHANGE，P0=0/P1=1/P2=3/P3=3；§8 复审锚 5 项）
- **审查人**: Design Reviewer Agent（只读审查；本报告为唯一写入产物）
- **日期**: 2026-09-18
- **审查对象**: FEAT-035 R1 修复集——governance.md Scenario C ask 清单+确认后序列 C-2 / governance-init.md standard+strict 模板 C-2 改写+Step 1 时序句 / governance-update.md 确认门改写 / governance-cleanup.md L3/L13 措辞同步 / ADR-007 状态行追加 / test_verify_workflow.py 新增 2 测试+既有测试增强 / CLAUDE.md 活体 + e2e fixture 镜像同步
- **审查依据**: agents/design-reviewer.md + skills/design-review/SKILL.md + 前轮 R0 报告 §8 复审锚

## 结论：APPROVED_WITH_NOTES（unresolved_blockers=0）

> P0=0 / P1=0 / P2=0 / P3=0（BLOCKING=0）。R0 全部 5 项可修复 findings（D1/D2/D3/D4/D7）逐条核实**已修复**；D5/D6 按申报维持不修且未恶化。6 条非阻塞备注见 §5（含校验数值申报值边界与 evidence-log 补录义务）。本结论为通过终态——按 design-review SKILL，`APPROVED_WITH_NOTES` 仅用于无未解决 BLOCKING finding 的审查，本报告不含任何未解决 BLOCKING finding。

---

## 1. R0 findings 逐条比对（复审锚 §8 逐项）

### D1（R0 P1）升级 ask 写清单缺 cleanup 删除面 + 双入口序列不对齐 —— **已修复 ✅**

逐项对照 R0 修复建议 (a)~(d)：

| R0 要求 | R1 实证 | 判定 |
|---------|---------|------|
| (a) Scenario C 步骤 4 补 cleanup 步骤，与模板 A~E 对齐 | governance.md L312 新增 `C-2. 插件残留清理删除面（与模板 C-2 同序同措辞——dry-run 先行 + 确认后执行）`：dry-run 呈现待删报告 → AskUserQuestion 确认 → 执行 → 不确认则跳过且不影响其余步骤 | ✅ |
| (a') C-2 位置正确性（Hook 检测后、版本字段更新前） | governance.md：C. Hook 存活检测（L311）→ C-2（L312）→ D. 更新 `工作流版本`（L313）；模板：hooks 提示（init L395-396）→ C-2（L397）→ **D. 更新 plan-tracker `工作流版本`**（L399）；活体 CLAUDE.md L136-140 同构 | ✅ |
| (b) ask 清单显式列删除面 | governance.md L305 清单第 4 类：「插件残留清理删除面（cleanup.py——dry-run 先行 + 确认后执行；删除插件安装目录中不在 canonical manifest 中的文件，`.governance/`/`.git/` 不触碰）」 | ✅ |
| (c) 模板 C 步骤措辞与 governance-cleanup.md 安全保证一致 | init L397/L673（standard+strict 双模板）改为 dry-run 先行 + AskUserQuestion 确认链，与 cleanup.md L109「dry-run 先展示……用户确认后才执行」零矛盾；「自动删除」措辞已从全部协议面退役（grep 核实：governance.md / governance-init.md / governance-cleanup.md / CLAUDE.md / AGENTS.md / fixture 全树均无命中） | ✅ |
| (d) 测试锁定对齐后的两面 | 新增 `test_upgrade_cleanup_deletion_surface_dual_entry_aligned`（test_verify_workflow.py L9756-9783）：双文件 needle + `init.count("插件残留清理删除面")==2` + 「自动删除」双文件反断言 + cleanup.md 措辞断言 + **双入口位置断言**（governance 序列 Hook 存活检测 < 删除面 < 版本字段；init 块 hooks 提示 < 删除面 < D 步骤）——断言逐一对照实际文本核实，全部可满足 | ✅ |

**ask 清单五类 vs 确认后序列 A~E 全覆盖对照（复审要点 1）**：A 入口段→清单项 1 ✅；B 结构补全+D 版本字段→清单项 2（plan-tracker 合并披露）✅；C hooks 提示→清单项 3（明示「不代写」）✅；C-2 删除面→清单项 4 ✅（R0 缺口本点）；E 归档→清单项 5（其它治理文件）+ L306 回滚行 dry-run 报告留存 + L314/L320 二次确认门（R0 已判定可接受，未回退）✅。**全覆盖，无未披露写面**（governance-update.md 的 decision-log 披露 nit 见 §5-N2，非 Scenario C 面）。

### D2（R0 P2/SP-1）跨入口 ask 时序两读 —— **已修复 ✅**

- 时序句落位：governance-init.md standard 模板 L346 / strict 模板 L622（两模板 Step 1 首次交互前置段末尾，FEAT-034 段内——落点正确），逐字为「升级 ask 时序（FEAT-035）：若快路径检测到版本差距，升级待处理确认随本次首次交互 ask 一并呈现征询——与 /governance Scenario C 时序同口径，不拆分为先后两次弹窗；确认前不执行升级写序列。」
- 活体投影：根 CLAUDE.md L87 逐字一致；fixture CLAUDE.md L87 镜像一致
- 测试锁定：`init.count("升级待处理确认随本次首次交互 ask 一并呈现")==2`（L9739，防单模板漏改）
- **与 M5.5/FEAT-034 一致性（复审要点 2）**：M5.5 条 1（behavior-protocol.md L405）的「后置」对象是深检与写序列**执行**，本句合并的是 ask **呈现**——两文各司其职无冲突；「同口径/不拆分/确认前不执行升级写序列」三段式显式裁决了 R0 指出的两种读法，与 /governance Scenario C L295 完全同口径。**无新歧义**。R0 给出的「模板补句 或 M5.5 补条目」二选一，实际采用模板补句（推荐项），M5.5 未动——符合最小修改。

### D3（R0 P2）governance-update.md 静默语义 + 守护面外 —— **已修复 ✅**

- L3 路由头：「已弃用——使用 `/governance`……（ask-确认前置——FEAT-035）」
- L7 行为描述：旧「自动检测版本变化并自升级/自动升级失败」心智模型已替换为「呈现升级待处理摘要并经 AskUserQuestion 确认（FEAT-035 ask-确认前置；用户未响应前零写操作）」+ 手动回退定位（仅在确认流程受阻或用户想立即升级时使用）+ 「本命令只覆盖升级写序列的入口段子集——完整升级序列仍以 `/governance` Scenario C 为准」（申报的「最小改法=正文补确认门非整段路由」兑现）
- L38 Step 4 模板描述含「bootstrap 升级（提示 + 确认后执行——FEAT-035）」
- Step 5（L41-45）确认门：写前 AskUserQuestion 呈现写清单（入口段+版本字段）+ 回滚方式，「用户确认前不执行任何写操作」；Step 6 标题（L47）「确认后更新 plan-tracker 工作流版本」
- **文件内自洽（复审要点 3）**：L3 路由（首选 /governance）与 L7 手动回退定位不矛盾——回退命令自身同样走确认门，两条路径的交互模型一致；Step 5 确认清单与 Step 5/6 实际写面一致
- **纳入守护网**：新增 `test_governance_update_command_ask_confirmed_no_silent_semantics`（L9785-9802）——5 个旧措辞反断言（含「自动删除」）+ 6 个确认门 needle 断言；逐一对照文件文本核实全部可满足。R0 指出的「活体命令在反断言扫描面之外」缺口闭合

### D4（R0 P2）ADR-007 无 supersede 指针 —— **已修复 ✅**

- L4 状态行：原文「提案（已修复 B1+B2——待重新审查）」**完整保留**，纯追加「；**部分取代**——Step E 交互模型经 FEAT-035 / DEC-207② 改为 ask-确认前置（2026-09-18），见 docs/reviews/review-FEAT-035-DESIGN-R0.md」——与 R0 建议文本逐字一致
- **正文零改写佐证（复审要点 4）**：R0 列举的 9 处「零用户操作」（L37/72/85/94/102/118/128/427/551）grep 核实**全部原样在场**（含 L427 内嵌模板级文本）——历史不改写纪律守住；指针指向 R0 报告路径有效（本审查即从该路径加载前轮）

### D7（R0 P3）申报偏差 + fixture 锁定缺口 —— **已修复 ✅**

- (a) 落位注明：`test_scenario_c_upgrade_writes_are_ask_confirmed` docstring（L9700-9702）「R1 D7 erratum: this FEAT-035 test family lives inside GovernanceStatusContractTests; the declared standalone class name "UpgradeWriteConfirmationTests" was never created.」——申报偏差入档。**落点说明**：注明位于 FEAT-035 首测试方法 docstring 而非类 docstring（类 docstring L9226 仍为 FIX-064 原文）——语义达成（可检索、可澄清），记录为落点备注非缺陷
- (b) fixture 镜像锁定：`test_e2e_fixture_mirrors_bootstrap_script_and_markers` 新增断言 `assertIn("用户未响应前零写操作", init)`（L15501-15504，含 R1 D7b 注释）——fixture 漂移防护缺口闭合

### D5 / D6（R0 P3，申报不修）—— **状态确认，未恶化 ✅**

- D5：adr-canonical-manifest-cleanup.md L373/L387「自动删除」旧措辞仍在场（历史 ADR，转跟踪）——与申报一致；全仓库 grep 确认其仅为协议面外残留（另见 §5-N6 精确化）
- D6：hooks 写权限语义张力（初始化代写 vs 升级提示）未被本轮触碰——既有状态维持

## 2. 通过面不回退核验（R0 申报 2/3/4/6/7、SP-1~SP-3）

| R0 通过项 | R1 核验 | 判定 |
|-----------|---------|------|
| 申报 2 深检衔接句三文件 | governance.md L297 / init L387+L663 / SKILL.md L39 全部在场；`test_upgrade_write_sequence_deep_check_linkage`（L9743-9754）未回退 | ✅ |
| 申报 3 零写语义 | governance.md L295/L302、init L374/L414/L650/L691（×4）、CLAUDE.md L115/L117/L155、fixture 同步——全协议面一致 | ✅ |
| 申报 4 默认选项+拒绝路径 | L307 三选项 + L330 幂等性/migration 标志持续可见未动 | ✅ |
| 申报 6 版本链 0.83.0 | SKILL frontmatter（L3）== 模板头 ×4（init L197/L264/L540/L838）== AGENTS.md（L5）== 根 CLAUDE.md（L5）== fixture 五文件全套 0.83.0 | ✅ |
| 申报 7 / SP-2 引用方向 | cleanup.md L3/L13 单向指向 Scenario C；governance.md 引用 cleanup.py 脚本非命令文档——无环维持 | ✅ |
| SP-3 次要入口传播 | AGENTS.md L13 → SKILL.md L39 衔接句（含 FEAT-035 升级确认语义）——间接闭合维持 | ✅ |
| R0 既有测试 4 件 | L9695-9754 全部在场；`test_scenario_c_upgrade_writes_are_ask_confirmed` 增强（required 增「插件残留清理删除面」L9713，反断言增「自动删除」L9716）——增强非回退 | ✅ |

## 3. 复审要点 5/6 裁决

**测试断言强度（要点 5）**：新增 2 测试覆盖面充分——D1 测试为 R0 建议的 (a)(b)(c)(d) 全四项（含位置断言防"同页不同序"的部分修复）；D3 测试补上守护网最后一块盲区（活体命令文件级扫描）。计数断言（×2/×4）+ 反断言 + 位置断言三层防部分修复。通过面不回退：申报的 R0 2/3/6 与 SP-2/SP-3 全部复核无回退（§2）。

**新引入检查 + AI 专项（要点 6）**：无 BLOCKING 新引入。R0 SP-4 的三处 AI 可执行性缺口（D1/D2/D3）全部闭合：Scenario C 序列编号 A/B/C/C-2/D/E 明确且 C-2 含具体命令与跳过路径；跨入口 ask 时序一句话裁决；governance-update.md 单一行为模型文件内自洽。残余两条非阻塞观察（§5-N1/N2）。

## 4. 维度覆盖裁决 + 硬门槛

| 维度 | R1 裁决 | 依据 |
|------|---------|------|
| 设计一致性 | **通过** | 双入口序列对齐且测试位置断言锁定；ask 时序跨入口同口径 |
| 安全性 | **通过** | 知情同意链在删除面闭合（清单披露+dry-run+确认+可跳过）；零写语义未变；hooks 不代写；fail-closed 链未削减 |
| 向后兼容 | **通过** | 拒绝路径/幂等/migration 标志未动；回滚披露覆盖 cleanup 面 |
| 测试守护 | **通过** | 新增 2 测试 + 既有 4 测试增强；D7b fixture 标记锁定；计数断言文本基线逐一核实（4/4/4/2/2 全吻合） |
| 传播路径 | **通过** | 模板×2 + 活体 CLAUDE.md + fixture 五文件全同步；版本链 0.83.0 全绿 |

| 硬门槛 | 结果 |
|--------|------|
| P0 = 0 | ✅ |
| 蓝军挑战 ≥3 且各配缓解 | ✅（继承 R0 §5 四条——C-2「暗模式」质疑随 D1 修复解除前提，缓解成立；无新增架构面） |
| 循环依赖 = 0 | ✅（cleanup.md→Scenario C 单向维持；governance-update.md→Scenario C 路由单向） |
| 前轮 findings 逐条比对 | ✅（7 条：5 修复 + 2 申报不修且未恶化；新引入 0 BLOCKING） |
| 结论 | **APPROVED_WITH_NOTES（unresolved_blockers=0）** |

## 5. 非阻塞备注（6 条——跟踪项，不阻断通过）

- **N1（校验数值边界）**：申报的「五项校验 exit=0 + 受影响测试 7/7 + 四整类 31/31 + 投影幂等 [WROTE]→[SKIP] + fixture SHA256 IDENTICAL + 干净 HEAD 复跑 17 failures」均为**申报值，未独立复验**（Bash 禁止——design-reviewer 工具硬约束，同 R0 边界）。但全部测试断言的**文本前提**（needle 在场性/计数/位置序/反断言真空面）已由本审查逐一独立核实为真，测试可绿性高置信。数值结论以申报值为准记录。
- **N2（evidence-log 补录义务）**：evidence-log 中 FEAT-035 现仅 2 条记录（TRIAGE-FEAT-035 L2228、REVIEW-FEAT-035-R0 L2258）——R1 执行证据（校验/测试/SHA256/worktree 复跑）尚未机录。Coordinator 于 M7.4 任务收尾时 MUST 补录，否则 Check 证据完整性面存在缺口。
- **N3（cosmetic）**：governance.md L312 C-2 行列表缩进多一空格（4 空格 vs 兄弟行 3 空格）——markdown 同级渲染不受影响，下次触碰该文件时顺带对齐即可。
- **N4（披露 nit）**：governance-update.md Step 5 确认清单（L42）未列 Step 7 的 decision-log 写入。decision-log 属治理记录（非关键决策类，可自动执行），不削弱知情同意实质；下次修订顺带补全清单。
- **N5（失败归属细节）**：「既有 17 failures 归属 fixture 硬编码 0.82.0 vs 活数据 0.83.0」——tracked e2e fixture 树 grep 核实**零 0.82.0**（全套 0.83.0）；「0.82.0」硬编码实际位于 hook 测试内联 fixture 行（test_verify_workflow.py L19444/L19465/L19484）。归属方法（干净 HEAD worktree 复跑原样复现）本身健全且结论（归属既有）不受影响，仅诊断描述应修正指向。
- **N6（「自动删除」残留面精确化）**：全仓库 grep 11 处命中 = D5 历史 ADR（L373/L387）+ R0 审查报告自身 4 处（L30/32/122/176——审查记录引用缺陷原文，历史文档豁免）+ 测试 needle/docstring 5 处。协议面零残留，与申报一致。

## 6. 边界声明（事实依据红线）

本审查 Bash/pwsh 禁止（角色硬约束），四项边界：①五项校验与测试未复跑（数值为申报值，文本前提已独立核实）；②工作树未 git diff（以 R0→R1 文本对照与行号位移一致性佐证——新增测试致 L15399→L15494 区段 +58 行位移，与新增量吻合，未见删除痕迹）；③fixture SHA256 未独立计算（以五文件关键面逐字比对佐证：D2 句/C-2/衔接句/cleanup L3/版本头全部镜像一致）；④ADR-007 正文零改写以「零用户操作」9 处原样在场佐证，非 diff 级证明。全部结论引用文件路径+行号，可复查。
