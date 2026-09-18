<!-- machine-suggested-next-round: none (terminal pass) | round: R0 | reviewer: Code Reviewer (subagent) | verdict: APPROVED_WITH_NOTES -->

# Code Review 报告 — FEAT-038-CODE-R0

| 项 | 值 |
|---|---|
| 任务 | FEAT-038 — Scenario 按需加载（命令入口只留决策树+当前场景投影，AUDIT-154 切片 A-7） |
| 审查轮次 | R0（独立代码审查；Reviewer 与 Developer 分离，本 Reviewer 未参与实现） |
| 审查对象 | 工作树未提交变更集：路由层 1 + 按需文档 9 + manifest/投影 + 引擎归属改指 + 守护测试 + 双面镜像 |
| 审查规范 | `skills/code-review/SKILL.md`（已加载）+ `agents/code-reviewer.md`（全文已读） |
| 审查方式 | 只读（Read/Grep/Glob）；审查者禁 Bash/pwsh——测试与校验器**未独立复跑**（见 §9 验证边界） |

---

## 1. 审查对象与事实基础

**A. 路由层与按需文档（10 文件，全部逐行读）**

| 文件 | 实测 | 关键结构（行号） |
|---|---|---|
| `commands/governance.md` | 110 行 | L5 路由层声明（含"拆出文件不在默认注入面"）；L25 边界表短版；L56-74 决策树 + `scenario_hint` A~F 分支；L78-98 六摘要表 + 路由契约（MUST）+ 跨场景注记；L100-111 命令路由 / 错误码按需指针 |
| `commands/governance/scenario-a.md` | 28 行 | H1 + 搬移 H2（L6）+ 7 步 + 参数面板 + 自动衔接 F（L17） |
| `commands/governance/scenario-b.md` | 108 行 | B1~B8 七个 `### Step` 全在（L12/27/47/67/76/93/97） |
| `commands/governance/scenario-c.md` | 45 行 | 5 步 + ask 摘要（L17）+ 写序列 A~E（L23-38）；**用户未响应前零写操作**（L10）+ FEAT-035 归属；深检衔接 M5.5 条 3（L12） |
| `commands/governance/scenario-d.md` | 62 行 | D1~D4 + 新鲜度三档表 + FEAT-034 时序重排（L10） |
| `commands/governance/scenario-e.md` | 79 行 | E1~E4 + P0 3 项 / P1 6 项 + FEAT-034 时序（L10） |
| `commands/governance/scenario-f.md` | 124 行 | 双契约（L18-23）+ ≤8 字段默认视图合约（L38-50）+ 20 字段 CLI / 4 字段 pack 契约（L56-75）+ 引导情况 A~D（L84-122） |
| `commands/governance/bootstrap.md` | 42 行 | 入口引导 FIX-238.1~238.4 + GOV-ERR-001~006 条件-动作表（L35-42） |
| `commands/governance/snapshot-schema.md` | 49 行 | snapshot 字段代码块 + `推荐快照引用` / RECO- 契约（L44-45） |
| `commands/governance/overview.md` | 149 行 | 三方分工 / Web console 边界 / 自动化分级 A+B 级（L40-48）/ 文件变更清单 / 边界表 / 9 条路由表 / 调度 / 交互规则 / 旧命令路由表 |

**B. 同步面（逐处核实）**
1. `adapters/dsh/skill-shims/governance.md`（17 行）——frontmatter 保留 + 新增 L15「分层加载（FEAT-038）」段。
2. `skills/software-project-governance/SKILL.md` L127——B 级声明已更新为"`commands/governance.md`（FEAT-038 起为**路由层**……按需 Read `commands/governance/`）"。
3. `core/manifest.json`——L7-34 `projection_ids` 实测 **25 条**（含 9 条 `fixture-command-governance-*`）；L654-688 `product.entries` 登记 9 个新文件；L721 `product.glob_patterns` 增 `commands/governance/*.md`；L53-74 `PROJECTION_SYNC_PATTERNS.required_members` **恰 12 条**（L72 为新增项）、`min_entries=12`。
4. `core/version-projections.json` L133-185——9 条 `byte_copy` 投影 source/target 一一对应（target 9 文件实测存在）。
5. fixture 镜像——`project/e2e-test-project/commands/governance.md` 实测为**新路由层**（L5/L78 命中），`project/e2e-test-project/commands/governance/{scenario-a..f,bootstrap,snapshot-schema,overview}.md` 9 文件实测存在（合 10 文件）。
6. `infra/verify_workflow.py` 归属改指（实测 5 处）：L2664-2682（`GOVERNANCE_PACK_STATUS_DOC_PATHS` 增 scenario-f 双面）、L8809-8824（`check_governance_context` docs 列表）、L18393-18407（target fixture 检查：路由层降为 3 needle + scenario-f 承接 26 needle）、L18436-18461（e2e contract check：路由器 needle 改为指向 scenario-f.md + 新增 scenario-f 条目）、L18837-18873（`_validate_e2e_governance_proxy` 契约文件与路由指针双断言）。
7. `test_completion_recommendation.py` L253-263——既有测试已同步改指 `snapshot-schema.md` + 断言路由指针（属披露外的同步面，见 §2-⑧）。
8. `core/architecture-baseline.json`——L17 `anchor_loc: 24769`；L541 `r4.total: 1304`；L553 `r6.import_count: 199`。

**C. 守护测试**：`test_verify_workflow.py` L20437-20570 `FEAT038GovernanceOnDemandSplitTests`——**实测 10 个测试方法**（申报/验收记录称 9，见 P2-3）。

**D. 治理面事实**：`.governance/execution-packets.json` L993-1069（FEAT-038 packet：success_metrics / acceptance_contract / quality_budget 六维）；`.governance/plan-tracker.md` L89（FEAT-038 状态 **⏳ 待执行**，符合"审查中未收口"）。

---

## 2. Developer 申报 7 项逐项核实（不采信自报）

| # | 申报 | 核实结果 | 事实依据 |
|---|------|---------|---------|
| ① | 零语义丢失（A24/24·B104/104·C41/41·D58/58·E75/75·F120/120 逐行对照 + 2 处披露改写） | **结构性核实成立；逐行计数采信申报**。① 子标题面：B 的 B1~B8 七个 `### Step`、D 的 D1~D4、E 的 E1~E4、F 的 `### 状态展示后的引导（MUST）` 全部在场且序号连续；② 关键 token 抽验（建议面 C+F）**全部在场**：C「用户未响应前零写操作」「AskUserQuestion 呈现升级摘要」「插件残留清理删除面」「M5.5 条 3」「dry-run 先行」；F「默认交互视图合约」「≤8 字段」「20 字段 CLI snapshot 契约」「4 字段 pack doc-surface 契约」「deferred→待检查」；③ F 的 20 字段名清点为**恰 20 个**（与 `governance-status.md` L60 逐字一致），pack 4 字段 + 边界 token 齐备；④ 披露的 2 处改写可核实：snapshot 节 H2→文件 H1（snapshot-schema.md L1）、overview 文件变更清单首行改指路由层（overview.md L55）；⑤ A/B 无独立 FEAT-034 段落，但路由层 L60/L95 的跨场景注记统一承担（口径一致，非丢失）。**逐行对照表本身无法独立复算（禁 Bash）**——见 §9。 | 读 10 文件全文；grep FEAT-034/035/036 token 24 处命中 |
| ② | 路由层完整性（决策树 + 六摘要 + 路由指令无歧义） | **成立**。L64 先声明"读取 `scenario_hint`（A..F）并按对应 Scenario 分支"，随后 L67-72 给 A~F 的字母→场景映射；表 L84-91 每行携带"触发条件/关键步骤/执行规程文件"三要素且全部命名 `commands/governance/scenario-x.md`；L80 路由契约为 MUST 且明示"摘要只用于识别与分流，不是执行依据"。缺陷/边界语义同时在场：L66 fail-closed、L74 判定逻辑下沉 `detect_scenario()`。唯一措辞不齐见 P3-5（不影响可路由性）。 | 路由层 L56-98 |
| ③ | 注入面纪律（拆出文件不在默认注入面） | **结论成立，但守护用例的判定面与命名不符（P2-2）**。事实面：a) 新文件位于 `commands/governance/`，9 处均自述"不在默认注入面"；b) FEAT-039 同树的机器事实源 `checks/injection_budget.py` L144-154 以 `command-doc` 项登记**仅** `commands/governance.md`，并在 note 明写"the scenario/overview documents it defers to are NOT part of the default surface"；c) 宿主侧 DSH 手势目标为 `commands/governance.md`（`adapters/dsh/launch.py` L818 `SMOKE_GESTURE_TARGET`）。而 FEAT-038 自己的守护用例（L20511-20516）以 `assertNotIn(rel, vw.INJECTION_CONTRACT_ANCHORS)` 判定，该 dict（verify_workflow.py L6678-6706）**只有 3 个键**且全部在 `agent-presets/`、`skills/`、`adapters/`，`commands/**` 从不是键——该断言近乎恒真。 | 读 test 用例 + `INJECTION_CONTRACT_ANCHORS` + FEAT-039 surface 表 |
| ④ | manifest 登记正确性（16→25 与投影清单精确一致 / 12 条） | **逐项成立**。`manifest.projection_ids` 实测 25 条 == `version-projections.json` 的 `projections` 实测 25 条（27 个 `"id"` 命中 − 2 个 validation_inventories = 25），9 条新增 id 名、`kind: byte_copy`、source/target 与仓库实存文件一一吻合；`required_members` 恰 12 条（`member_match: exact` + `min_entries: 12`），与引擎 `PROJECTION_SYNC_PATTERNS`（L6639-6657，含 L6655 新增项及其 FEAT-038 说明注释）**完全等集**。fixture 侧 manifest 为 0.37.0 遗留快照（非镜像物），无同步义务。 | 三文件逐条比对 |
| ⑤ | REQUIRED_SNIPPETS 补修（死组合删除 · 指纹恒等 · 正则依赖字面量） | **机制成立，且"净 0 行"获树内旁证**。a) 引擎 L730-733 为 4 行说明注释（"F-2 items open"），L734 起为唯一字面量；b) `checks/version.py:89` 正则 `REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest`（`re.S`）的落点经实测仍成立：L1059 `}` → L1060/1061 空行 → L1062 `# ── Manifest domain`（恰满足 `\n\}\n{2,}#`），且 L734 是全文首个 `REQUIRED_SNIPPETS = {`，body 捕获不再被前置 `= {}` 污染；c) **删/加行数对账**：fixture 引擎 `project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py` L444-447 保留修复前原形（`REQUIRED_SNIPPETS = {}` + 两行 `.update(...)` + 空行 = 4 行），与新增 4 行注释**等量** ⇒ "净 0 行"成立；d) 归属：该删除是 `data-inventory-0.80.0.md` L331 的 F-2 遗留项（L87/L89 同族标注），**非** FEAT-038 语义所需——跨任务夹带见 P3-3。**"sha256 5b4d7df0… 指纹恒等"无法离线复算**，采信申报（见 §9）。 | 引擎 L730-734/L1059-1062、fixture 引擎 L444-448、data-inventory L331/L335 |
| ⑥ | 并发耦合披露（与 FEAT-039 同树互覆，最终 24,769/1304/199） | **数值与树一致；但"committed==fresh"的判定语义需辨明（P2-4/P3-2 相关）**。a) `verify_workflow.py` 实测 **24,769 行**，与 `architecture-baseline.json` L17 `anchor_loc` 相等；b) R7 的 committed 比较经 `_strip_volatile()` 剥离 `generated.git_head` 与 `r6_startup_budget`（`archguard_ratchet.py` L884-931），故工作树未提交本身不构成 R7 失败——该项按"树内自洽"评估为一致；c) **但 FEAT-039 的实现实体确在同一工作树**（`checks/injection_budget.py` 733 行、`registry.py` L194/L293、引擎 L6852-6904/24059-24067/24713、测试 20430 段），而 plan-tracker L87 仍记 FEAT-039"⏳ 待执行"——两任务变更在同一树/同一基线文件上互相吸收，**无法从审查视角做逐任务归因**（见 P2-4）。 | 引擎行数（read 实测）+ baseline L17/L541/L553 + R7 源码 + plan-tracker L87 |
| ⑦ | 35 既有失败归因（test_registry 88-key 属 FEAT-039 面 + replay 类 RISK-056） | **归因类别存在性抽验成立；"未补"表述已与当前树不符（P3-2）**。a) `test_registry.py` L93 `FROZEN_CLI_KEYS = 88`、L110 `FROZEN_ENGINE_IMPORT_COUNT = 199`、L346-366 迁移 handler 清单含 `check-injection-budget`——**88-key 面在树内已补**，申报"未补（FEAT-039 面）"为过时口径；b) RISK-056（replay 类既有失败）在 plan-tracker L84 有登记痕迹（FEAT-035 行"RISK-056 既有测试失败登记"）；c) **35 项清单未独立复现**（禁 Bash），FEAT-038 自身"零新增失败"因此**未经本审查证实**，仅证"其守护面断言在当前树状态下自洽"（见 §9）。 | test_registry L93/L110/L346-366；plan-tracker L84 |
| ⑧ | （披露外）测试同步面 | **存在且方向正确**：`test_completion_recommendation.py` L253-263 已由 `commands/governance.md` 改指 `snapshot-schema.md` + 路由指针；`test_verify_workflow.py` L3878-3882（fixture contract 写入 scenario-f.md）、L8725-8734（e2e 双写路由层+scenario-f）、L18393-18407/L18837-18873 均已同步。该面未列入 Developer 申报，属**申报完整性的正向缺口**（有利于变更，非缺陷）。 | 上述 4 处逐段读 |

---

## 3. 五维度逐项结论

### 3.1 正确性 — 通过（带 2 条 P2）
- **逻辑正确**：拆分是"搬移+指针"，无逻辑改写；路由层保留 fail-closed（L58/L66）、判定树、六分支映射，语义链完整。
- **跨面一致性（本任务的核心正确性面）**：所有"内容已迁出"的机器消费面均**同时**改指 owning document，且被改指的文件**确实含所需 token**——逐项验证：`scenario-f.md` 含 `Unfinished work`/`Source facts`/`Blocker state`/`Auto-continue`/`Interrupt boundary`（L63）、`Existing governance state detected`（L26/42）、`not found`/`do not invent`/`governance-context`（L27/79）、`lite is the recommended first-run default`（L70）⇒ `check_governance_context`（L8815-8824）、pack-status 四字段 + 边界 token、e2e contract check（L18450-18459）、proxy 契约（L18852-18872）**四项均不会因迁出而翻红**。
- **边界条件**：`_documented_route_table_count()` 仍读路由层（L1465-1469）——路由层 L31 保留"完整路由表（19 行）"句，且 SKILL.md L191-209 实表**恰 19 行**（逐行点数）⇒ architecture fact source 的 count 比对成立；`core/onboarding.md` 之类 skill-root-relative 引用经 `resolve_ref()`（L11494-11503）正确落到 `skills/software-project-governance/core/onboarding.md`（实存）。
- **资源/并发**：纯文档 + 常量表改动，无共享状态；FEAT-039 同树并发写入属流程耦合（P2-4），非代码并发缺陷。
- 遗留缺口：快照规范首句重复（P2-1）；fixture 引擎 4 处归属未随改（P2-4，潜性）。

### 3.2 安全性 — 通过
- **fail-closed 无削减**：`resolved_root_ok == false → STOP` 在路由层 L58/L66 与 bootstrap.md L18（脚本兜底不可用 → STOP）双处保留；deferred 诚实语义（"待检查"≠通过）在路由层 L62 与四个 Scenario 文件重复声明。
- **写操作门禁无放宽**：FEAT-035 语义随 C 搬移且强化（L10/L17/L20-21/L27-29：确认前零写、写清单显式列目标文件、回滚方式、dry-run 先行）；snapshot 写入门禁（RECO- 引用契约）随 snapshot-schema.md 保留（L44）。
- **注入/敏感数据**：纯 Markdown；无密钥、无 token、无外部调用；`<plugin_home>` 占位符纪律保留（未回退到 `$WORKFLOW_HOME`）。
- **权限面**：变更集全部位于产品代码路径（SKILL.md L89-101 明确 `commands/**` = 产品代码），未走 Coordinator 直写 —— 流程面合规。

### 3.3 可维护性 — 通过（带 P2/P3）
- **命名/分层清晰**：路由层=识别与分流，Scenario=执行规程，bootstrap=错误路径，snapshot-schema=字段契约，overview=描述性说明——单一职责，无重复定义（同一内容仅一处权威 + 指针）。
- **重复代码**：一处引入型重复（P2-1 快照规范首句 ×2）；一处结构性重复标题（P3-1）。
- **注释质量**：引擎侧两侧改点均有 FEAT-038 出处注释（L2675-2678、L6650-6654、L18452-18454、L18839-18841），可追溯性好。
- **文档结构**：overview.md 存在 H2/H3 同题对（L70/L74、L135/L140）与孤立 H3（L40），见 P3-1。

### 3.4 性能 — 通过（本任务即性能任务）
- 默认载荷从 49,889B（申报）降到路由层 110 行；`/governance` 常规场景的注入面 = 路由层（+ 命中场景一个文件），未命中场景不进上下文——与 AUDIT-154 诉点方向一致。
- 成本上界有硬守护：`test_router_layer_within_injection_budget` 以 `st_size ≤ 12288` 断言（ratchet 语义）。按 FEAT-039 校准口径（CJK=1 tok/字）粗估路由层量级 ≈2~3K tok，与验收"命令总注入 ≤4K tok"方向一致；**精确字节/令牌未独立测量**（§9）。
- 无算法/复杂度面（无循环、无 I/O）。

### 3.5 测试覆盖 — 通过（带 1 条 P2）
- 10 用例覆盖八面：体积硬上限 / 决策树+六摘要行 / MUST-Read 路由指令 / 文件存在非空（>512B） / manifest 登记（entries + glob） / 不在注入面 / 子标题零丢失（B/D/E/F 逐 heading 断言） / FEAT-034-035-036 零回退（C: 4 token；D: FEAT-034；F: 5 token） / 支持文档契约（bootstrap 4 token、snapshot 3 token、overview 3 token） / fixture 镜像 10 文件全等。
- **缺陷路径覆盖**：子标题丢失、文件缺失/空壳、manifest 漏登、fixture 漂移都能红——正向有效。
- **缺牙/弱牙**：`test_scenario_documents_are_not_in_the_default_injection_surface` 的判定面与命名不符（P2-2）；C/F 的 heading 断言为**空清单**（`"c": []`）——即 A/C 两文件无子标题级守护（两者本无 `###` 子标题，属如实，但意味着 C 的 5 步子结构只靠 token 在场守护）；用例计数与验收记录不一致（P2-3）。
- 既有测试同步面无回退（§2-⑧）。

---

## 4. 特别审查点逐项结论

### 4.1 循环引用风险 — 无环（静态核验通过）
逐点构造引用图（含 `check_cross_references` 的 `commands/` **rglob** 扫描面，verify_workflow.py L11391-11402）：
- 出边：路由层 → {scenario-a..f, bootstrap, snapshot-schema, overview} + `commands/governance-init.md` 等旧命令；scenario-a → governance-init.md；scenario-b → `core/onboarding.md`（解析为 `skills/…/core/onboarding.md`）；scenario-c → governance-update.md；scenario-d → {`.governance/session-snapshot.md`（`is_external_or_runtime_generated_ref` 豁免）}；scenario-f → governance-status.md；overview → {SKILL.md, core/onboarding.md, agent-dispatch-template.md, governance-{init,status,verify,update}.md}。
- 回边：全库对 `commands/governance.md` 的引用**只有 2 处**——路由层 L82 自引（自环 `[A,A]` 被 L11644 的 `len==2 and cycle[0]==cycle[1]` 过滤）与 `SKILL.md` L127（SKILL.md == `entry_source`，作为 edge source 被 L11596 排除）。**无 X ↔ 路由层的双向边**，故 10 文件子图无环。
- 悬空面：新文件内的路径引用逐条解析命中（`skills/…/SKILL.md`、`commands/governance-*.md`、`core/onboarding.md`、`references/agent-dispatch-template.md`、`project/CHANGELOG.md`），`<plugin_home>/infra/*.py` 类因含 `<` 走 placeholder 豁免（L11472/L11484-11485）。
⇒ "零悬空零循环"**静态结论成立**；「695 引用 PASS」的运行时数字未独立复跑（§9）。

### 4.2 DSH shim 兼容 — 契约不破
`adapters/dsh/skill-shims/governance.md`：`---` 围栏（L1）、`name: governance`（L2，== 文件名）、非空 `description`（L3）、`commands/governance.md` 指针（L12）、"薄投影"自述（L8）全部保留 ⇒ `test_dsh_adapter.py` L873-888 与 `test_dsh_contract.py` L925-936 的 shim 契约断言**结构上仍满足**。新增 L15 只做分层加载说明，未复制 workflow 规则（薄指针纪律保持：无规则正文、无第二事实源）。"分层加载"文本无任何测试引用（grep 全库唯一命中）——属说明性增量，无守护也无不一致风险。

### 4.3 与 FEAT-039 并发耦合与 R1 重锚 — 树内自洽，归因不可分离
- `architecture-baseline.json`：R1 `anchor_loc 24769` == 引擎实测行数（read 报 24,769 lines）；R4 `total 1304`；R6 `import_count 199`（与 `test_registry.FROZEN_ENGINE_IMPORT_COUNT=199` 一致）。
- R7 语义：`_strip_volatile()` 剥 `git_head`/`r6_startup_budget`（L884-897），committed 与 fresh **都在当前工作树计算** ⇒ "未提交"不影响 R7 判定；只要 baseline 与引擎同步 regen，R7 保持 PASS。
- 残余问题不在数值而**在归因**：FEAT-039 的实体（`checks/injection_budget.py` 等）与 FEAT-038 同树且在基线文件上互覆（两次 regen），而 plan-tracker L87 仍标 FEAT-039"待执行"。任一任务单独测算 R1 增量都不可行 ⇒ 见 P2-4（本条属披露与记账面，非代码缺陷）。

### 4.4 零语义丢失（建议抽验面 C+F）— 抽验通过
C：`scenario-c.md` 5 步与写序列 A/B/C/C-2/D/E 齐全，FEAT-035 三处关键约束（确认前零写、写清单显式、dry-run 先行）+ DEC-207② 深检衔接在场；F：双契约数字面**自洽**（默认视图 8 行字段、20 字段名恰 20、pack 4 字段 + 三行固定语义行），且与 `governance-status.md` L60/L63/L99 的字段清单**逐字一致**（无第二口径）。token 面抽验见 §2-①。

### 4.5 是否过度拆分（bootstrap.md / snapshot-schema.md 是否本可内联）— 判定为**合理，非过度实现**
- `snapshot-schema.md`（49 行）有 ≥2 个消费点（Scenario D 恢复前校验 + 会话收尾写入），且被既有测试直接锚定（`test_completion_recommendation.py` L258-263 断言该文件 + 路由指针）——独立文件避免"同一契约两处书写"。
- `bootstrap.md`（42 行）聚合的是**错误路径**（解析失败/超时/陈旧/错误码表），正常路径零成本；内联回路由层会把 586B 的剩余预算吃掉约 80%（4,590B >> 余量），直接违背本任务目标。
- 结论：拆分层级 = 按"触发条件"而非"体积"划分，符合单一职责；未发现投机性抽象或空壳文件（9 文件全部 >512B 且内容实质）。

---

## 5. AI 生成代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 新增测试零 mock 引入（`json`/`unittest`/pathlib 真实文件断言）；被改的既有测试同样使用真实仓库/临时树 |
| 2 | 硬编码返回值 | ✅ 无 | 路由层/Scenario 为规范文本；20/4/8 字段清单是**契约常量**（与 `governance-status.md` 逐字一致，属双面契约要求的固定语义行），非"假数据返回" |
| 3 | 幻觉 API / 命令 | ✅ 无 | 抽验全部实存：`first-run-demo --assert-snapshot`、`web-console --summary-link`、`check-governance-pack-status`、`governance-bootstrap --format json`、`archive.py migrate --auto --dry-run`、`cleanup.py --dry-run`、`resolve_entry.py --json`（registry.py L281/L341 + 引擎 L23901-23919/24421-24423/24742/24713） |
| 4 | 未实现 TODO | ✅ 无 | `commands/governance/**` grep TODO/FIXME/XXX/占位 → 命中仅为正文语义（"占位证据条目""消除占位符歧义"），非未完成标记 |
| 5 | 过度实现 | ✅ 无 | 10 文件职责单一、无重复定义；拆分粒度按触发条件（见 §4.5）；无"顺手重构"（引擎侧仅归属改指 + 已披露的 F-2 删除） |

---

## 6. 发现列表（P0=0，P1=0；P2×4 / P3×5）

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| **P2-1** | P2 | `commands/governance/snapshot-schema.md` L6 与 L8 | **引入型重复句**：`` `session-snapshot.md` 必须包含以下字段以确保 Scenario D 可无缝恢复： `` 连写两遍（L6、L8），已随镜像进入 fixture（同文件 L6/L8）。属"节标题转文件标题"改写时的复制残留，无信息丢失但为交付面噪声（重复内容维度） | 删除 L6（保留 L8 作为正文首句），同步 fixture 镜像并复跑镜像等值用例 |
| **P2-2** | P2 | `test_verify_workflow.py` L20511-20516 | **守护断言面与命名不符（false assurance）**：用例名/注释声明"not in the default injection surface"，判定却是 `assertNotIn(rel, vw.INJECTION_CONTRACT_ANCHORS)`——该 dict 仅 3 个键（`agent-presets/*`、`SKILL.md`、`adapters/dsh/AGENTS.md.template`，引擎 L6678-6706），`commands/**` 永不是键，断言近乎恒真；真正的注入面事实源是 FEAT-039 `INJECTION_BUDGET_SURFACES` 的 `command-doc` 项（`checks/injection_budget.py` L144-154，tier=command，note 明示 scenario/overview 不在默认面）与 `commands/*.md` 扁平发现面。当前无失败后果，但断言不能证伪 | 改为直连事实源：断言"无任何 injection surface 路径落在 `commands/governance/` 下"（读 `INJECTION_BUDGET_SURFACES` 计算），或断言路由层为唯一 `command` tier 面。若刻意保留弱断言，请在用例注释中如实声明其弱语义 |
| **P2-3** | P2 | `.governance/execution-packets.json` L1005/L1017/L1023 + 本报告 §1-C | **验收证据计数与产物不符**：packet 的 `expected_output` 与 demo_evidence 均记"**9 passed** / 9 用例 / FEAT038GovernanceOnDemandSplitTests 9 用例"，但类内实测 **10 个测试方法**（L20459/20468/20485/20490/20499/20511/20519/20538/20551/20565）——`pytest -k FEAT038` 必输出 10 passed，记录值不可能由当前树产生 ⇒ 或该轮 run 早于第 10 个用例（`test_support_documents_keep_their_contracts` 未被那次 run 覆盖），或计数误记。二者都使"守护测试全绿"证据不可复现（非反向夸大：产物强于申报） | 重跑 `pytest -k FEAT038` 并按实测回填 packet 的 `expected_output`/`demo_evidence`（9→10）与 success_metrics 文案；若确有用例为后补，追加一条 run 记录 |
| **P2-4** | P2 | `project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py` L3897-3902、L12476-12499、L12085/L12092 | **fixture 引擎未随归属改指**（潜性不一致）：fixture 的 `commands/governance.md` 已更新为新路由层（L5/L78 命中），但 fixture 自带的引擎副本仍要求**路由层**含 `Unfinished work`/`Source facts` 等已迁出 token（L3897-3902 的 doc 列表、L12476-12499 的 `_validate_e2e_governance_proxy` 契约文本、L12085/L12092 的 e2e 契约路径）。当前矩阵不执行该路径（`_e2e_target_cwd_command_matrix` 只跑 status/gate/cleanup，L18269-18304；`_validate_e2e_target_status` 只读 stdout，L18679-18716；`verify-e2e.sh` 只做文件存在/grep），故**当前无失败**；但任何人从 fixture cwd 跑 `governance-context`/`e2e-check` 即 FAIL。fixture 镜像是已登记的"预期投影/双写债"（FIX-350 / RISK-039） | 二选一并留痕：(a) 把 canonical 引擎的 4 处归属改指同步进 fixture 引擎（推荐，成本低）；(b) 明确把 fixture 引擎降级声明为"legacy 快照、不追平"，并把该偏离写入 RISK-039/FEAT-040（四平台回归）的范围，避免"镜像"语义继续隐含追平义务 |
| **P3-1** | P3 | 六份 `scenario-*.md` L1/L6 等；`overview.md` L70/L74、L135/L140、L40 | **标题重复与层级跳变**：Wrapper H1（`# Scenario X: …`，守护用例 L20534 强制要求）紧随搬移的 H2 同题标题；overview.md 出现 `## 产品代码 vs 治理记录边界（完整表）` + `### 产品代码 vs 治理记录边界`、`## 现有命令路由（完整表）` + `## 现有命令路由` 同题对，且 `### 自动化能力分级声明` 前无母 H2（`---` 后直接 H3）。属可读性/目录生成面的结构噪声，无语义风险 | 保留 H1（守护需要），把搬移 H2 改为不重复表述的正文引导句或降为 H3；overview 的重复 H2 合并为一个标题 |
| **P3-2** | P3 | 申报 ⑦（及 packet 同期文案）vs `test_registry.py` L93/L110/L346-366 | **披露过时**：申报"test_registry 88-key 未补（FEAT-039 面）"与当前树不符——88 键、199 import 面与 `check-injection-budget` 迁移项均已在场。此类"既有失败清单"若按旧口径入账，会污染 35 项归因 | 刷新失败清单口径（按当前树重跑或明确标注"某时点快照"） |
| **P3-3** | P3 | `verify_workflow.py` L730-734；`docs/requirements/data-inventory-0.80.0.md` L331 | **跨任务夹带（F-2 遗留项）**：死组合删除属 data-inventory F-2 的独立遗留项（`REL-078 CODE R0 L121` 建议），随 FEAT-038 一同入账——违反"一个 commit 承载一个问题"的纯粹性口径（D4），但与 FEAT-038 同因（同树 F-2 项）且已披露，判断为**可接受**；风险在账目面：F-2 项在 data-inventory 中仍标 open（注释写"F-2 items open"） | 在 evidence/packet 中显式记该行为"F-2 部分交付"并从 F-2 余项中扣除，避免与 FEAT-039 批次双计或漏计 |
| **P3-4** | P3 | 验收措辞"子目录结构与扁平命令发现机制隔离"（packet L1063；`fill_feat038_packet.ps1` L78） | **声明而非机检**：仓内可核的是 glob/清单面（`commands/*.md` 不下降、DSH 手势目标为 `commands/governance.md`、manifest 未登记为命令），但**宿主命令发现是否递归 `commands/**`** 无仓内证据（SKILL.md L96 的分类表用 `commands/**` = "用户斜杠命令"，语义是"产品代码"轴，非发现轴）。若宿主递归发现，将多出 9 个可调用入口（不破坏 ≤12KB 预算，但属用户可见面变化） | FEAT-040（多平台回归）把"实际暴露的命令列表"纳入验收：四平台实测仅 `/governance` 系列 9 条旧命令 + 路由层命令，不含 scenario/bootstrap/overview |
| **P3-5** | P3 | `commands/governance.md` L86-91 | 六摘要表"触发条件"列 A/B/C 写 `scenario_hint == "X"`，D/E/F 改写状态描述（如"一切正常——…"）；与 L64 的字母映射靠组合推理。无歧义，但措辞不齐 | D/E/F 行统一为 `scenario_hint == "D"（session-snapshot 新鲜…）` 格式 |

**观察项（非 finding）**
- 静态引用图无环/无悬空（§4.1）；`SKILL.md` L127 与路由层 L31 的双向指称不构成环（前者为 edge-source 排除）。
- `checks/version.py:89` 正则锚点在修复后仍精确命中 L1059→L1062，且成为**唯一** `REQUIRED_SNIPPETS = {` 起点。
- 路由表 19 行在 SKILL.md L191-209 实测恰 19 行 ⇒ architecture fact source 的"documented vs actual"比对不受拆分影响。
- `project/e2e-test-project/skills/.../core/manifest.json` 为 0.37.0 遗留快照（非镜像义务物）——与 canonical manifest 的 25 投影无一致性要求。
- 变更集全部落在 `commands/**`（产品代码）⇒ 走了 Developer + Code Reviewer 通道，未发生 Coordinator 直写。

---

## 7. 设计一致性裁决（triage acceptance 对照）

| 验收口径（plan-tracker L89 / packet L1002-1017） | 裁决 | 依据 |
|---|---|---|
| 主文件 ≤12KB（12,288B） | ✅ **结构性满足** | 硬断言用例 `test_router_layer_within_injection_budget`（`st_size ≤ 12288`）+ 申报 11,702B/余量 586B；**字节未独立测量**（§9） |
| 六 Scenario 就位 + 按需 Read（命中场景读对应文件） | ✅ 满足 | 9 文件实存非空（>512B）；路由表 6 行各带 `scenario-{a..f}.md` + MUST-Read 契约（L80）；"摘要是索引不是执行依据"显式声明 |
| Scenario D/F 会话不加载 A/B/C 全文；命令总注入 ≤4K tok | ✅ **结构性成立** | 默认载荷 = 路由层；A/B/C 仅在命中时 Read（L80 契约）；令牌为校准口径推演（≈2~3K 量级），未独立计值 |
| 校验 PASS（cross-references / projection-sync / manifest / injection-contract / verify / e2e-check 全 exit 0） | ⚠️ **未独立复跑**；静态面一致 | 静态：引用图无环无悬空（§4.1）、投影 25==25（§2-④）、token 面全部在场（§3.1）。运行时 exit code 采信申报（§9） |
| 零语义丢失（搬移非删减），FEAT-034/035/036 零回退 | ✅ 抽验通过 | §2-① 关键 token + 子标题 + 20/4/8 字段契约逐项在场；逐行对照表采信申报 |
| 守护测试（体积/六摘要/路由指令/零丢失/零回退/镜像） | ✅ 存在且有效，**计数记录不符** | 10 用例断言逐个读源核实为真断言（除 P2-2 弱断言）；P2-3 记录面修正 |
| 依赖 FEAT-034 / 不动 FEAT-039 预算面 | ✅ | FEAT-034 已完成（plan-tracker L82）；路由层跨场景注记消费其语义；FEAT-039 预算面未被修改（仅同树共存，P2-4） |

---

## 8. 硬门槛裁决

| 门槛 | 裁决 |
|------|------|
| P0 阻塞 = 0 | ✅（P0=0） |
| 5 维度 100% 覆盖 | ✅（§3 逐维结论） |
| 每条发现标注 P0~P3 | ✅（9 条，全部标注） |
| 设计一致性完成 | ✅（§7 逐条，含 2 项"未独立复跑"的显式披露） |
| AI 代码专项 5 项 | ✅（§5 逐项） |

---

## 9. 验证边界（诚实声明）

审查者角色禁 Bash/pwsh（`agents/code-reviewer.md` L96），以下**未独立复现**，均以静态事实替代并如实标注：
1. **测试与校验器未复跑**：`pytest -k FEAT038`、`check-cross-references`/`check-projection-sync`/`check-governance`/`e2e-check` 的 exit 0 采信申报；本报告用"断言逐个读源 + token 在场性 + 静态引用图 + 投影等集"四路交叉替代。
2. **字节数未测量**：11,702B/余量 586B 为申报值（有硬断言守护机制在场）；路由层实测 110 行、9 文件规模为行数级事实。
3. **逐行对照表（A24/24…F120/120）与 sha256 指纹恒等未复算**：以关键 token 抽验（C/F）+ 子标题连续性 + 结构等价替代。
4. **35 项既有失败未复现**：仅抽验归因类别的存在性（`test_registry` 88/199 面、RISK-056 登记）；"FEAT-038 零新增失败"因此**未获本审查证实**，仅证其守护面断言在当前树状态下自洽。
5. **R4 1304 / R6 199 未复算**：仅核对与 `test_registry` 冻结常量一致。
6. **git HEAD 对照不可得**：审查者无 git 权限，"与 HEAD 逐行复核"采信 Developer 申报；本报告的所有"零丢失"结论均基于**当前树内**在场性证据，非 HEAD diff。

以上不构成 finding，但为复核边界——建议 Coordinator 在收口前对 ①/④ 做一次独立复跑（`pytest -k FEAT038` + `check-governance --summary-only`），即可闭合 P2-3 与"零新增失败"两项证据面。

---

## 结论：APPROVED_WITH_NOTES（P0=0/P1=0/P2=4/P3=5）

unresolved_blockers=0

**通过终态说明（三态口径 = APPROVED：零阻塞，带备注）**：硬门槛 5/5 通过，无未解决 BLOCKING finding；P0=0 且 P1=0，四条 P2 均为**证据/守护/镜像口径**类（非功能缺陷、非反向夸大），五条 P3 为文档结构与记账精度类。分片设计的关键风险面——"内容迁出导致机器消费面翻红"——经逐处归属改指核实为**已闭环**（pack-status 四字段 / governance-context 8 token / e2e 契约 / proxy 契约四项消费面均落在确实含 token 的 owning document 上）；路由层可自主路由（决策树 + 六摘要 + MUST-Read 契约）；投影 25 条与 manifest 精确等集；DSH shim 契约不破；AI 专项 5 项无异常。

**建议处置顺序**：P2-1/P2-3（一行修复 + 一次复跑，即可同时闭合证据面）→ P2-2（断言接事实源）→ P2-4 与 P3-3/P3-4 建议随 **FEAT-040**（多平台回归，其验收依赖本任务的投影同步面与 fixture 面）一并处置；P3-1/P3-2/P3-5 可遗留。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中独占一行且无附着细目（沿用 FEAT-025/FIX-304 先例，避让 FIX-291 provably-zero 探针）；P0/P1/P2/P3 计数写在结论行，不与该行混排。本报告为 R0 通过终态，复审链无需开启（若 Coordinator 选择采纳 P2-1/P2-3 返工，则按 M7.4 step 4.6 发起 R1 复审）。

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。本次审查未修改任何文件（仅产出本报告）、未执行任何命令、对被审对象零写入。*
