# FEAT-035-DESIGN-R0 — 迁移退出启动关键路径 · 独立设计审查报告

- **Round**: R0（首轮）
- **审查人**: Design Reviewer Agent（只读审查；本报告为唯一写入产物）
- **日期**: 2026-09-18
- **审查对象**: FEAT-035 变更集（工作树未提交）——governance.md Scenario C 重写 / governance-init.md standard+strict 模板升级块+lightweight 归档确认门 / SKILL.md 衔接句 / test_verify_workflow.py 新增 4 测试 / governance-cleanup.md + e2e fixture 三文件镜像 / CLAUDE.md 活体投影
- **审查依据**: agents/design-reviewer.md + skills/design-review/SKILL.md + DEC-207②（decision-log L148）+ plan-tracker L84 任务申报

## 结论：NEEDS_CHANGE（P0=0/P1=1/P2=3/P3=3）

> Coordinator 动作：按 behavior-protocol M7.4 退回修复后重 spawn 本 Reviewer 复审（R1 必达）。核心 P1 为升级 ask 写操作清单完整性缺口——修复面小（协议文本 2 处 + 清单一行），不动架构。

---

## 1. 申报逐项核实（7 项）

### 申报 1 — 写操作清单完整性：**不完整（P1-D1）**

A~E 步骤逐项对照（以 bootstrap 模板序列 A~E 为权威，governance-init.md L378-412 / L654-689）：

| 步骤 | 写面 | ask 清单披露（governance.md L305-306） | 判定 |
|------|------|------|------|
| A 入口 bootstrap 段替换 | 平台入口文件 bootstrap 段 | ✅「平台原生入口文件 bootstrap 段」 | 覆盖 |
| B plan-tracker 结构补全 | plan-tracker.md 结构节 | ✅「.governance/plan-tracker.md（结构补全）」 | 覆盖 |
| C-1 hooks 检测 | 无写（提示安装命令，不代写） | ✅「.git/hooks/*（提示安装命令，不代写）」 | 覆盖 |
| C-2 cleanup.py 残留清理 | **删除**插件安装目录不在 manifest 中的文件 | ❌ 清单无此项 | **缺口（D1）** |
| D 工作流版本字段 | plan-tracker.md 字段 | ✅（含在 plan-tracker 项） | 覆盖 |
| E 归档迁移 | archive/ 目录 + index + plan-tracker 瘦身 | ⚠️ 未在清单列写面，但 L306 回滚行声明「归档迁移执行前 dry-run 报告先行呈现并留存」+ 二次 AskUserQuestion 门（L319） | 经二次确认门闭合，可接受 |

**两面不对齐（D1 伴生缺陷）**：governance.md Scenario C 确认后序列（L308-322）无 cleanup 步骤，而 bootstrap 模板 C 步骤（governance-init.md L397/L673）含「运行 cleanup.py——自动删除」。同一次版本升级：走 /governance 入口不清理残留，走 bootstrap 入口清理——写序列不一致，违反 P-v5 泛化性原则（单点修改未对齐镜像面）。

**矛盾加重项**：bootstrap 模板 C 步骤的「自动删除」措辞与 governance-cleanup.md 自身安全保证（L109「**dry-run 先展示**：所有清理前必须通过 --dry-run 展示待删列表，用户确认后才执行」）直接矛盾。FEAT-035 将归档步骤 E 确认门化时未对 C-2 的删除写面做同等处理——知情同意链在删除面断裂。

### 申报 2 — DEC-207② P2-1 衔接句（三文件落点）：**成立 ✅**

逐字核实，三处全部在场且语义完整：
- governance.md L297：Scenario C 深检衔接段——「版本升级写序列属推进类动作……MUST 先满足 M5.5 条 3 的深检前置……**不得以"已获得升级确认"替代深检**」（末句直接封死"确认豁免深检"误读）
- governance-init.md L387（standard）/ L663（strict）：模板块内「深检前置（MUST——DEC-207② P2-1 / M5.5 条 3）」双份
- SKILL.md L39：「版本升级写序列属推进类动作（FEAT-035 / DEC-207② P2-1）……执行前 MUST 补齐 M5.5 条 3 深检」
- 引用锚有效：M5.5 条 3 实际存在（behavior-protocol.md L407「深检后置 ≠ 深检可选」），非悬空引用
- 测试锁定：`test_upgrade_write_sequence_deep_check_linkage`（test_verify_workflow.py L9733-9744）三文件断言

**歧义消除效果判定：有效**。衔接句同时锚定 (a) 写序列的推进类属性 (b) 深检前置 (c) 确认不免除深检——DEC-207② 指出的"两种执行解读"在该三点上被显式裁决。义务兑现 ✅。

### 申报 3 —「用户未响应前零写操作」语义：**成立 ✅**

- governance.md L295「写序列不前置于首次交互，**用户未响应前零写操作**（FEAT-035——读入口与写迁移解耦：展示状态不拥有修改项目的隐含授权）」+ L302 步骤 3「确认前不执行任何写操作」
- 模板 L374/L650 头部 + L414/L691 尾部承诺句 + CLAUDE.md 活体 L115-117 同步
- A 步骤显式「并入升级确认 AskUserQuestion——确认前零写操作」（L378/L654）——呈现摘要本身零写 ✅
- dry-run 为只读（`--dry-run` flag）、CHANGELOG 提取/清单构造均为读操作 ✅
- 语义边界（协议可执行性）：「零写操作」在所有协议面一致，无例外通道 ✅

### 申报 4 — 默认选项设计权衡：**合理 ✅（非 BLOCKING）**

- 「执行升级（推荐）」保留自动精神（一次确认后 A~E 全自动），同时把否决权交还用户——升级写面属治理基础设施（非用户数据），归类为推进类动作（关键决策，永远必问）正确，与 M5.3 关键决策清单一致
- 拒绝路径：governance.md L329 幂等性段「用户拒绝升级时同样路由到 Scenario F（migration 待处理状态经 FEAT-033 migration 标志在状态行持续可见）」——无静默版本差，且**不重复弹 ask**（拒绝态持续可见但不再打断）✅
- 回滚方式披露（L306：入口段 git/备份恢复、版本字段回退、归档 dry-run 报告留存）✅
- 权衡正当：知情同意优先于完全无感，符合「关键决策必问 + 非关键不打断」框架；蓝军挑战见 §6

### 申报 5 — 守护测试强度：**基本成立——反断言面有一处实证遗漏（P2-D3）**

4 个新增测试方法实际落位于 `GovernanceStatusContractTests` 类内（test_verify_workflow.py L9695-9744；**非申报的"UpgradeWriteConfirmationTests"类名——申报偏差记 P3-D7**）：

| 测试 | 断言面 |
|------|------|
| test_scenario_c_upgrade_writes_are_ask_confirmed（L9695） | 6 标记在场 + 反断言「自动升级序列/已自动升级」 |
| test_scenario_c_archive_migration_dry_run_confirmed（L9713） | 归档 dry-run 确认门标记 |
| test_init_templates_present_pending_upgrade_and_zero_write（L9720） | 计数断言 4/4/4/2（防部分修复）+ 反断言「零用户行动/零用户操作/一切自动完成/自动序列/已自动升级」 |
| test_upgrade_write_sequence_deep_check_linkage（L9733） | DEC-207② 三文件衔接句 |

计数断言已对照实际文本核实：governance-init.md「呈现升级待处理」×4（L376/414/652/691，尾部以子串「呈现升级待处理摘要」命中）、「用户未响应前零写操作」×4、「执行升级（推荐）」×4、「版本升级写序列属推进类动作」×2——**测试与文本一致，可绿**。

反断言清单完备性评估：**不完整**。反断言只扫 governance.md 与 governance-init.md；governance-update.md（活体命令）的旧静默措辞（D3）不在任何守护面内——这正是"还有哪些静默自动措辞残留可能溜过"的实证答案。其余面：README 无残留（全仓库 grep 核实）；CHANGELOG 历史条目正确豁免（发布记录须保留历史真实性，反断言不扫 CHANGELOG 是正确设计）。

### 申报 6 — @bootstrap-version 保持 0.83.0 传播路径：**闭合 ✅**

- 当前一致性：SKILL.md frontmatter `version: 0.83.0`（L3）== 模板头 0.83.0 ×4（governance-init.md L197 lightweight/L264 standard/L540 strict/L838 secondary-thin）== AGENTS.md 薄指针头 0.83.0 == CLAUDE.md 活体头 0.83.0 ✅
- 测试锁点：`test_bootstrap_version_marker_injected_into_all_profiles`（L15399-15416）——FIX-256 动态断言，从 SKILL frontmatter 提取版本后断言 `> @bootstrap-version: {version}` 精确 ×4。**v0.84.0 发布 bump frontmatter 而模板头未同步 → 此测试立即 FAIL**（无手工测试字面量同步负担）
- 陈旧链推送：check-version-consistency（VersionConsistencyBootstrapMarkerTests L909-1038 锁定行为）——AGENTS.md（tracked）陈旧 = FAIL、CLAUDE.md（untracked）陈旧 = WARN + FIX-238.2 fail-closed 升级链 → FEAT-035 新确认流程承接
- FEAT-035 新增的升级确认段位于各模板 @bootstrap-version 头下方，随段整体替换传播 ✅

### 申报 7 — 既有失败归属（30 个 test_hooks/test_pre_commit_review_evidence）：**读取面零交集声明成立 ✅（文件级核实）**

- test_pre_commit_review_evidence.py 读取面：`infra/hooks/` 源文件（L27 `_HOOKS_DIR`）+ `.governance/evidence-log.md` 活数据（L32 `_EVIDENCE`、L222 live evidence-log）+ 临时 fixture（L96-98）
- FEAT-035 变更集：governance.md / governance-init.md / SKILL.md / governance-cleanup.md / fixture 三文件 / test_verify_workflow.py 新增段 / CLAUDE.md——与上述读取面**零交集** ✅（变更集不含 hooks 文件、不含 .governance/ 任何文件）
- test_verify_workflow.py 内 hook 类测试（CommitMsgFactGroundingHookTests L13795 等）经 import 复用同一 helper（L19466），读取面相同——零交集 ✅
- FEAT-035 新增 4 测试方法为类内自包含方法（L9695-9744 全量读过），无模块级副作用
- **边界声明**：本审查 Bash 禁止，无法 diff 工作树核实 test_verify_workflow.py 除新增段外无其它改动，亦未复跑测试——「30 个失败」为申报值未独立复验；零交集结论限定于"所读新增段"与"所核读取面"

---

## 2. 特别审查点裁决（4 项）

### SP-1 与 FEAT-034 协议族一致性（升级 ask vs 首次 ask 时序）：**跨入口歧义残留（P2-D2）**

- /governance 路径：**明确合并**——governance.md L295「版本差距 + CHANGELOG delta 摘要随快路径首次 ask 一并呈现征询确认」
- bootstrap 主路径（governance-init.md 模板 Step 1 / CLAUDE.md 同构段）：首次交互前置段（呈现恢复/下一步选项）与版本升级段是两个独立段落，**无合并句也无独立句**——按段落顺序推导 = 先首次交互 ask、后独立升级确认 ask，但这是推导不是规范；behavior-protocol M5.5 条 1 仅把「版本升级序列」列为后置项，未定义其 ask 相对首次 ask 的位置
- 后果：同一版本差在两条入口产生不同的 ask 结构（合并一问 vs 先后两问）——AI 执行者行为分叉。写安全不受影响（「确认前零写」在两种读法下均守住），但这正是 DEC-207② 要消除的「两种执行解读」同族问题，只是从深检维度转移到了 ask 时序维度
- 修复建议：bootstrap 模板版本升级段补一句显式时序（推荐：「升级待处理摘要并入首次交互 AskUserQuestion 呈现（与 /governance Scenario C 时序一致）；用户未响应前零写操作」），或在 M5.5 条 1 补升级 ask 定位句

### SP-2 circular 依赖检查：**无新环 ✅**

引用方向核实（governance-cleanup.md 改写后）：governance-cleanup.md L3/L13 →（单向指向）Scenario C / bootstrap 升级序列；governance.md/governance-init.md 引用的是 cleanup.py **脚本**而非 cleanup 命令文档；cleanup.md 头部「推荐使用 /governance」单向。命令文档间无环、模板↔命令文档无环。与 check-cross-references 申报 PASS 一致（本审查经引用方向文件级核实，未复跑工具——Bash 禁止）。

### SP-3 零用户行动承诺变更的用户传播面（82 版本用户 → 0.84.0）：**引导充分 ✅**

- 升级摘要四要素（版本跨度/CHANGELOG 要点/写清单/回滚）信息面完整；默认推荐降低决策摩擦；拒绝路径 migration 标志持续可见、不阻断会话其余功能、不重复弹 ask（L307 选项 2 + L329 幂等性）——迁移摩擦可控
- 次要平台入口（Codex）：AGENTS.md 薄指针无升级段，但「完整规则：加载 SKILL.md（或读主入口）」（AGENTS.md L12）→ SKILL.md L39 衔接句覆盖升级确认语义——传播面经 SKILL.md 间接闭合 ✅
- 行为变化登记：maximum-autonomy 用户从「完全无感升级」变为「每版本一次确认」——设计意图（知情同意优先），蓝军挑战 §6-C 已评估，接受

### SP-4 AI 专项（协议文本可执行性）：**主体可执行，三处缺口**

可执行性良好面：升级 ask 呈现内容与选项结构步骤化、确认后序列 A~E 编号明确、E 步骤 dry-run→确认→执行→完整性检查链条完整、幂等路径明确。缺口：D1（清单不含实际将发生的删除）、D2（跨入口 ask 时序两读）、D3（governance-update.md 矛盾指令）——AI 按文本执行会在三处产生与 FEAT-035 意图不符的行为。

---

## 3. 发现清单

### P1（1 项）

**D1 — 升级 ask 写操作清单缺 cleanup.py 删除写面 + Scenario C 序列与 bootstrap 模板 C 步骤不对齐**
- 证据：governance.md L305-306（清单四类，无 cleanup 删除）；governance.md L308-322（步骤 4 无 cleanup 步骤）vs governance-init.md L397/L673（模板 C 步骤含「自动清理升级残留……自动删除」）；governance-cleanup.md L109（自身安全保证要求 dry-run 先展示+确认后执行，与模板「自动删除」矛盾）
- 影响：用户按清单确认升级，实际写面超出清单（插件目录文件删除）——直接削弱 FEAT-035 验收标准「升级场景显示升级待处理」的知情同意完整性；/governance 与 bootstrap 两入口写序列分叉（P-v5 单点修改未对齐镜像）
- 修复建议：(a) governance.md Scenario C 步骤 4 补 cleanup 步骤，与模板 A~E 对齐；(b) ask 清单显式列「插件残留清理（删除不在 canonical manifest 中的文件，manifest/exclude 双保护）」；(c) 模板 C 步骤 cleanup 措辞改为「dry-run 报告先行呈现 + AskUserQuestion 确认后执行」（与 governance-cleanup.md 安全保证及归档步骤 E 确认门化模式一致）；(d) 新增测试反断言/断言锁定对齐后的两面

### P2（3 项）

**D2 — 升级确认 ask 与首次交互 ask 的合并/独立时序在 bootstrap 主路径未定义**（证据与修复建议见 SP-1）

**D3 — governance-update.md 活体命令行为模型与 FEAT-035 矛盾，且在反断言守护面之外**
- 证据：governance-update.md L7「bootstrap 在每次会话开始时会**自动检测版本变化并自升级**——用户不需要手动运行此命令。仅在**自动升级失败**……时使用」（旧静默语义描述）；L41-48 Step 5/6 直接替换 bootstrap 段 + 写 plan-tracker 版本字段，无确认步骤；文件头 L3 路由到 Scenario C 但正文保留完整无确认独立流程——文件内自相矛盾
- 影响：AI 检索到手动回退命令时按 Step 3~8 执行 = 零确认写序列；「自动升级」行为描述教 AI 错误的心智模型
- 修复建议：L7 行为描述改为「提示 + 确认后执行（FEAT-035）」；Step 5 前加确认门或显式声明「本命令的用户显式调用即升级确认，仍须先呈现将执行的写操作」；将其纳入反断言扫描面（`test_scenario_c_upgrade_writes_are_ask_confirmed` 扩展或新增文件级断言）

**D4 — ADR-007 与现行协议矛盾且无 supersede 指针**
- 证据：docs/architecture/ADR-007-governance-upgrade-migration.md 状态行「提案（已修复 B1+B2——待重新审查）」（L4）；9 处「零用户操作」规范表述（L37/72/85/94/102/118/128/427/551），其中 L427 为内嵌模板级文本「**E. 归档迁移检测与执行**（用户更新插件后自动触发——零用户操作）」
- 影响：FEAT-035 推翻了该 ADR 的核心交互模型（零用户操作 → ask 确认），但 ADR 头部无任何取代指针；维护者/AI 检索归档迁移设计会得到与落地协议相反的指令，L427 内嵌模板文本极易被误当作现行规范复制回协议
- 修复建议：ADR-007 状态行追加「部分取代——Step E 交互模型经 FEAT-035 / DEC-207② 改为 ask-确认前置（2026-09-18），见 docs/reviews/review-FEAT-035-DESIGN-R0.md」（docs/ 为 Coordinator 可写治理记录，一次编辑完成）

### P3（3 项）

**D5 — adr-canonical-manifest-cleanup.md L299「CLAUDE.md bootstrap 自动升级序列中执行」**——历史 ADR 内旧措辞残留，非执行面；随下次该 ADR 修订顺带更新即可

**D6 — 初始化 vs 升级的 hooks 写权限语义不一致（既有张力，非本变更面引入）**——governance.md Scenario A L167「安装 git hooks」/B8「Hooks 已安装」（agent 代写）vs 升级场景「提示一次性命令（agent 不能自动写 .git/hooks/——安全问题）」（模板 L395-396/L671-672）。初始化经 init 命令显式调用可辩为用户授权，但两面语义宜统一登记为后续候选项

**D7 — 申报偏差 + fixture 锁定缺口**——(a) 测试类名申报为「UpgradeWriteConfirmationTests」，实际落位 `GovernanceStatusContractTests`（L9225 起）内 4 个方法；(b) fixture 镜像（project/e2e-test-project/ 五文件）的 FEAT-035 标记经本审查逐一核实在场（CLAUDE.md L115-155 / governance.md L277-311 / governance-init.md L221-683 / governance-cleanup.md L13 / SKILL.md L39），但 `test_e2e_fixture_mirrors_bootstrap_script_and_markers`（L15436-15442）只断言 bootstrap.sh/cmd/@bootstrap-version，**不断言 FEAT-035 标记**——未来 canonical 变更 fixture 漂移不会被测试抓到。建议扩展现有 fixture 镜像测试断言「用户未响应前零写操作」标记

---

## 4. 维度覆盖裁决（硬门槛）

| 维度 | 裁决 | 依据 |
|------|------|------|
| 设计一致性 | **未通过（P1-D1 / P2-D2）** | Scenario C 与 bootstrap 模板序列不对齐；跨入口 ask 时序两读 |
| 安全性 | **通过（核心）** | 「确认前零写操作」语义全协议面一致；hooks 不代写；归档二次确认门；回滚披露；fail-closed 链未削减。cleanup 删除披露缺口已记 P1 |
| 向后兼容 | **通过** | 拒绝路径不阻断 + migration 标志持续可见；幂等；82 版本用户迁移引导充分（SP-3） |
| 测试守护 | **未通过（P2-D3）** | 4 测试+计数断言+反断言强度良好，但反断言扫描面遗漏 governance-update.md；fixture 无 FEAT-035 标记锁定（P3-D7） |
| 传播路径 | **通过** | 版本链动态断言（L15399-15416）+ check-version-consistency 陈旧链 + FIX-238.2 fail-closed 闭合（申报 6） |

**P0 = 0** ✅（无协议级致命缺陷：零写语义、fail-closed、深检前置三大安全支柱全部成立且有测试锁定）

## 5. 蓝军挑战记录（4 条，≥3 达标）

- **C-1**「ask-确认前置会不会把升级永久卡死？」→ 拒绝路径 migration 标志持续可见且不重复打断（L307/L329），会话其余功能不受影响；版本差长期存在由状态行可见性缓解。残余风险（协议-插件能力漂移）可接受。**缓解有效**
- **C-2**「默认推荐『执行升级』是否构成暗模式？」→ 写面均为治理基础设施（无用户数据），归档有二次门；但 D1 修复前，cleanup 删除面未披露削弱此辩护——**D1 修复后可接受**
- **C-3**「双重确认（升级 ask + 归档 dry-run ask）是否过度打断？」→ 归档动治理数据结构（task 迁移 + plan-tracker 瘦身），独立门正当；且多数升级 dry-run 无可归档 → 跳过，零额外打断。**设计合理**
- **C-4**「字符串标记测试能否防语义回归？」→ 协议类变更的可守护面即文本层 + Check 行为抽查；反断言封死已知旧措辞复活路径；新型静默措辞靠审查流程守护（本审查即该层）。**天花板已知且可接受**

## 6. 依赖图分析

```
governance-init.md 模板（bootstrap 权威/canonical）
        ↓ 应为完整镜像                    ↓ 引用脚本（非文档）
governance.md Scenario C（手动入口镜像）──→ cleanup.py   ←──✗ D1：镜像不完整（缺 C-2 cleanup 步骤）
        ↓ 引用锚                                              ↓ 自身安全保证（dry-run 先展示）
SKILL.md 衔接句 → behavior-protocol.md M5.5 条 3 ✅ 单向有效        governance-cleanup.md ←──⚠ 模板「自动删除」与其矛盾（D1c）
governance-cleanup.md → Scenario C/bootstrap 序列 ✅ 单向无环
fixture 五文件 → canonical ✅ 单向（缺测试锁定，P3-D7b）
governance-update.md → 路由头指 Scenario C + 正文自留无确认流程 ✗ 文件内自相矛盾（D3）
ADR-007 → 已落地 Step E ✗ 无 supersede 指针（D4）
```

无循环依赖；两处镜像断裂（D1/D3）+ 一处文档脱节（D4）。

## 7. 硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 = 0 | ✅ |
| 维度覆盖 5/5 逐项裁决 | ✅（2 未通过 → NEEDS_CHANGE） |
| 每条发现 P0~P3 分级 + 证据 | ✅（7 条：1×P1、3×P2、3×P3） |
| 蓝军挑战 ≥3 且各配缓解 | ✅（4 条） |
| 循环依赖 = 0 | ✅ |
| 结论 | **NEEDS_CHANGE**——修复 D1（必须）+ 建议 D2/D3/D4 一并返工后重 spawn 本 Reviewer 复审（R1） |

## 8. 复审锚（R1 MUST 逐条比对）

1. D1：Scenario C 步骤 4 含 cleanup 步骤且与模板 A~E 对齐；ask 清单含删除面披露；模板 C 步骤措辞与 governance-cleanup.md 安全保证一致
2. D2：bootstrap 模板版本升级段含显式 ask 时序句（或 M5.5 补条目）
3. D3：governance-update.md 行为描述同步 FEAT-035 + 纳入反断言扫描面
4. D4：ADR-007 状态行含 supersede 指针
5. 既有通过面不得回退：申报 2/3/6/7 与 SP-2/SP-3 的全部 ✅ 项

---

*事实依据声明：本报告全部结论引用文件路径+行号，可复查。Bash 禁止导致的三项边界已声明：工作树未 diff（申报 7 边界）、check-cross-references 未复跑（SP-2 经引用方向核实）、测试未复跑（「30 个失败」为申报值）。*
