# DSH 宿主兼容性体系设计（0.81.0）

| 项 | 值 |
|---|---|
| Task | **FEAT-028**（P1）——本文件是**设计规格**（主体），配套决策记录见 `docs/architecture/ADR-018-dsh-host-compatibility-contract.md` |
| 目标版本 | 0.81.0 |
| 生成日期 | 2026-09-13 |
| 作者 | Architect（设计），Design Reviewer（后置审查） |
| 唯一事实输入 | `docs/requirements/dsh-host-dependency-inventory-0.81.0.md`（**AUDIT-153**，801 行，HEAD `d87ead8`，2026-09-13） |
| 用户诉求 | 2026-09-13 指令：dsh 升级适配后出现大量兼容性问题，需系统性分析设计与实现；四条硬要求 = REQ-146（最小化宿主依赖）/ REQ-147（必要依赖单点契约）/ REQ-148（严格校验看护）/ REQ-149（依赖边界可调测） |
| 性质 | **只设计，不实现**——本文件与 ADR-018 是本任务唯一写入面；不含任何产品代码变更 |
| 关联 | RISK-050（dsh 上游内部面耦合）、DEC-187 I-1/I-2/I-3、DEC-188 ②、FIX-311 / FIX-313 / FIX-315 / FIX-316（本设计承接其修复设计）、`docs/release/release-checklist-0.80.0.md` §出槽登记第 12 条（`dsh_compat.py` 归属未裁决） |

## 0. 阅读指引与事实纪律

### 0.1 引用约定

- 本文所有技术断言分三级标注：
  - **【实测】** = AUDIT-153 已执行的探针/命令证据（引用其 `文件:行号` 或命令输出），或本设计期我直接读取的仓库源码（引用 `文件:行号`，凡我本人读取的均在 §0.2 列明）。
  - **【实测·AUDIT】** = 我未直接读取、引用 AUDIT-153 报告中的实测证据（保留其出处，不升级为我的观察）。
  - **【假设】** = 无证据的推断，一律进 §9 未验证假设表，**不得**被下游当事实使用。
- **C-25 纪律**：AUDIT-153 §7 的 R-01~R-19 未被当作事实使用；凡涉及处均标注「未验证（Rn）」并给验证计划。本设计主动识别出**两处 R 项影响判据**（R-13「first root wins」、R-15「无 Config ⇒ 原样透传」），并因此**改变**了两条设计判据（见 §2.4 与 §4.4.1）。
- **R0 修订纪律**：本文件已按 `docs/reviews/review-FEAT-028-DESIGN-R0.md`（NEEDS_CHANGE：3 P1 + 5 P2 + 10 P3/NOTE + 4 条新增蓝军）修订；**逐条处置索引见 §11**（供 R1 复审逐条验证）。凡因修订而改变的事实口径，均在原处标 `R0 F-n` / `R0 BT-R-nn` 并给出新旧差异，不做静默改写。
- 本文不重复 AUDIT-153 的 100 条依赖点清单与覆盖矩阵（那是事实输入）；本文只给出**处置裁决**与**目标状态**。

### 0.2 本设计期直接核实的代码事实（不依赖 AUDIT-153 转述）

| # | 文件 | 核实内容 |
|---|---|---|
| E-1 | `lib/index.js`（全 249 行） | `resolveDshHome` 内联 + `trim`（`:101-111`）；零依赖自述（`:92-97`）；`packageVersion` 经 URL 读 `../package.json`（`:130`）；`leftovers` 只查已知 token（`:161`）；`\r\n→\n`（`:154`）；catch 清理用 `dirname(outcome.dir \|\| '.')`（`:231-234`）；`apply` 只调 `ensurePreset`（`:247-249`） |
| E-2 | `adapters/dsh/launch.py`（1-240 / 280-609 行） | `dsh_home()` 无空白判定（`:114-118`）；`render_composition` 无 `errors=`（`:146`）、token 兜底（`:153`）；`_custom_skill_dir_entries` 的 `<=`（`:459`）；`_resolve_skill_entry` 的 `urllib` 分支（`:468-496`）；`_validate_composition_rows` 传 `schema_checked = verdict != "NOT_RUN"`（`:566`）；`verify_preset_loading` 无 `errors=`（`:598`）；witness 纳入 `settings.yaml` 的 size+mtime_ns（`:438-439`）；逃逸守卫（`:298-303`） |
| E-3 | `skills/software-project-governance/infra/dsh_compat.py`（全 1224 行） | 三态常量（`:112-114`）；`NOT_RUN` 政策（`:75-77`）；`FINDING_KINDS` 6 类（`:117-124`）；锚点/oracle/env 常量（`:134-156`）；平面发现（`:542-576`）；`NO_SCHEMA` 分支不计 `checked`（`:371-377`）；group 分支只做形态检查并提前求值 `disabled`（`:297-314`）；裁决不看 `rows_checked`（`:1000-1026`）；`emit_check_section` 的 PASS 分支只打印含 `"NOT verified"` 的 detail（`:1088-1092`）；`run_cli` NOT_RUN 退出 0（`:1139-1144`） |
| E-4 | `infra/registry.py` | `LOADER_WHITELIST` 闭集 15 项，含 `dsh_compat`（`:182-198`）；`_COMMANDS` 注释「82 keys」（`:229`）、`check-dsh-preset-compat/smoke` 两键（`:251-253`）；`_SEGMENT_LOADERS` 70 条、`28u`/`28v`（`:405-406`）、Segment 40 退役记录（`:428-431`） |
| E-5 | `infra/verify_workflow.py` | `PROJECTION_SYNC_PATTERNS` 11 条（`:6581-6593`）；`_projection_source_files` 定义（`:6676-6688`，**本次核查未发现调用点**）；28u 本体（`:6802-6866`）；`[SMOKE]` 正则（`:6797-6799`）；`DSH_UPGRADE_REGRESSION_LABEL`（`:6892`）；`cmd_check_dsh_preset_*` 薄包装（`:21096-21129`）；命令分发表（`:24153-24154`） |
| E-6 | `infra/checks/projection.py` | `_normalized_hash` 只归 `\r\n`（`:13-14`）；`check_projection_sync` 无参时走 `check_projections`（`:78-85`）→ 活跃投影 = `version-projections.json` 的 15 条 |
| E-7 | `infra/cleanup.py` | `PLUGIN_SCOPE_DIRS` 硬编码 11 元集（`:46-63`）；`cleanup_scope.directories` 必须是其子集否则 exit 4（`:75-114`）；**dir 条目递归展开为 canonical**（`:204-214`）——见 §2.9 的口径修正 |
| E-8 | `core/manifest.json` | `skills/software-project-governance/core/` 为 dir 条目（`:87-88`）；`infra/` 为 dir 条目（`:139`）；`adapters/`、`lib/`、`agent-presets/` 为 dir 条目（`:235-257`）；`canonical_product_artifacts`（`:655+`）；`cleanup_scope.directories` 11 元（`:818-822`） |
| E-9 | `package.json` | `type/main/exports`（`:19-27`）；`files` 11 项含 `adapters/dsh/`（`:28-40`）；`dsh.bundle.patch`（`:41-45`） |
| E-10 | `agent-presets/governance/agent.cordis.yml.template`（全 272 行） | **逐行复算（R0 F-1/F-8 后修正）**：① **平台无关行全集 = 29**（顶层 16：`:45` persona、`:89` agent-instructions、`:98` tool-bash、`:102` tool-pwsh、`:108` tool-fs、`:111` tool-fs-search、`:118` tool-jobs、`:131` skill-filesystem、`:138` tool-skill、`:143` tool-goal、`:148` planning(group)、`:172` compaction(group)、`:197` delegation(group)、`:258` tool-ask-user、`:261` tool-todo、`:268` tool-web；嵌套 13：`:154` plan-mode、`:179` compaction-basic、`:182` command-compact、`:185` tool-result-pruner、`:203` tool-subagent-control、`:206` tool-subagent-list-agents、`:209` tool-subagent(spawn)、`:216` tool-subagent-fork、`:224` tool-subagent-codex、`:233` tool-subagent-claude-code、`:242` workflow-worker-thread、`:247` tool-workflow、`:250` tool-ralph）——**R0 修正点**：旧表述记为 28 行，漏了平台条件行 `tool-bash`；② 其中 group 行 3、`disabled: true` 行 2（`tool-subagent-codex`、`tool-subagent-claude-code`）、**平台条件行 2**（`tool-bash` `:100` / `tool-pwsh` `:104`，恰一被短路）⇒ **任一平台上的 enabled 行 = 29 − 3 − 2 − 1 = 23**，与 AUDIT-153 `rows_enabled: 23` 一致；③ **含 `config:` 的行 = 17**（非 group 14 + group 3，group 的 `config` 是子行列表）——旧表述记为 18 属**误推**；④ `rows_checked: 18` / `rows_enabled: 23` 是**探针事实**（有 `Config` 导出的 enabled 行 = 23 − 5 零 schema 行：`plan-mode`/`command-compact`/`tool-subagent-control`/`tool-subagent-list-agents`/`tool-ask-user`），**不可由模板推导**（模板只能推出行集与 config 键，推不出 `schema_export`）|
| E-11 | `infra/version-projections.json` | 15 条投影，dsh 面 2 条（`:25-26`） |
| E-12 | `adapters/dsh/adapter-manifest.json` | `verified_on: 2026-07-08` + 证据串 `0.1.0-rc.6`（`:75-76`）；`native_entry.note` 描述加载模型（`:36`） |
| E-13 | `infra/tests/test_dsh_compat.py` | `:365 test_no_schema_rows_are_disclosed_not_failed`（断言 `checked=0` + `NO_SCHEMA` → PASS / issues 空）；`:399 test_zero_enabled_rows_degrades_to_not_run`；`:681` group 递归；`:754 test_throwing_group_disabled_expression_is_a_finding`（断言 group 抛错→finding）；`:742/:753` live-gated |
| E-14 | `infra/hooks/pre-commit:68-77` | `find_spg_home` 用纯 shell 拼 `${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance` + `skill-root.txt`，**无 JSON 解析能力** |
| E-15 | `core/protocol/plugin-contract.md:248-266` | DEC-187 I-1/I-2/I-3 承诺 + DEC-188 ② 机检判据 + 五条导出禁令 |
| E-16 | `docs/release/release-checklist-0.80.0.md:137` | 「`dsh_compat.py` 归属（core `infra/` → `adapters/dsh/`，core→dsh 耦合）**未裁决**」 |
| E-17 | `infra/registry.py:620-633, 658` | `CHECK_SPECS = _build_check_specs()` **在导入期执行**；其中 `:627-633` 用 `declared = set(_segments.registry_ids())` 与 `_SEGMENT_LOADERS` 求集合并 `raise RegistryError` ⇒ **新增段 MUST 同时声明在 `quickscan_registry.py`**（R0 F-2） |
| E-18 | `infra/quickscan_registry.py:234-611, 745` | `SEGMENTS` 表元素形态 = `SegmentSpec(segment_id, domain, input_tokens, disposition)`（最近邻：`28u` `:538-541`、`28v` `:542-546`）；`registry_ids()`（`:745`）是导入期 join 的另一侧 |
| E-19 | `infra/tests/test_registry.py:73-74, 277-279, 311-317, 334-344, 864-874` | 冻结面：`FROZEN_CLI_KEYS = 82` / `FROZEN_SEGMENTS = 70`；`migrated` 为**精确 4 项列表**（`archguard-ratchet`/`check-capability-registry`/`check-manifest-consistency`/`check-review-debt`）；`test_matches_the_live_engine_face` 要求 declared == observed（⇒ 新段必须在引擎内有真实 section） |
| E-20 | `infra/contract_matrix/{snapshots.json,generator.py}`、`core/architecture-baseline.json:6,16-20,542-543` | 契约矩阵快照冻结 CLI/段面（`generator.py --regen`）；棘轮基线 `r1_mainfile_budget.anchor_loc = 24204`（`:17`）、`r6_startup_budget.import_count = 196`（`:543`），且 `:6` 的 **R1 豁免 `rule: "R1"` / `expire_version: "0.81.0"` 恰在本版到期** |
| E-21 | `infra/tests/test_dsh_adapter.py:1138-1156` | parity 测试**直接调用** `renderComposition(template, pkgRoot)`（`:1139`/`:1142`）并断言 `leftovers == []`（`:1152`）⇒ 契约 token 必须在 `renderComposition` 内可得（R0 F-3） |
| E-22 | `adapters/dsh/launch.py:652-658`、`package.json:41-45`、`package.json:31` | skill shim frontmatter 契约（`---` + `name: <文件名>` + 非空 `description:`）；`dsh.bundle.patch` 键名；`files` 含 `skills/` ⇒ 放在 `skills/**` 下的提交式 fixture 会随包发布（R0 F-12） |

### 0.3 判定口径（本文自用，避免与 AUDIT-153 的口径串味）

| 口径 | 定义 |
|---|---|
| **必要性** | 沿用 AUDIT-153 §2 的三分类：`可消除` / `可弱化` / `必要`（+ 历史/有意不可消除） |
| **覆盖强度** | `强` = 有正反相用例且能判负漂移；`中` = 有守卫但无完整反相；`弱` = 守卫抓不住该漂移；`无` = 无守卫（沿用 AUDIT-153 §4 定义） |
| **目标强度** | 本设计为每个契约条目声明的**要求达到的**强度（机检：声明强度必须有 fixture/守卫佐证，见 §4.1） |
| **可信面 ≤ 校验面** | 结论强度不得超过实际被校验的依赖子集；零校验路径不得进入 PASS（C-6） |
| **三态** | `PASS` / `FAIL` / `NOT_RUN`，语义与 `dsh_compat.py:75-77` 一致：`NOT_RUN` 只披露未验证事实，不计 gate issue，且**绝不等价于 PASS**（C-7） |

---

## 1. 需求到设计的映射

| 需求 | 用户原话 | 设计域 | 本文件章节 | 交付形态 |
|---|---|---|---|---|
| **REQ-146** | 「尽可能减少对 DSH 宿主的依赖」 | (B) 依赖最小化 | §3 | 逐条处置裁决表 + 收窄判据 |
| **REQ-147** | 「必须的接口和字段依赖，尽量将依赖逻辑解耦，单独维护」 | (A) 依赖契约层 | §2 | 单点机器可读契约 + 消费方迁移 + 机器校验 |
| **REQ-148** | 「对依赖的代码进行严格的依赖性校验和看护」 | (C) 校验看护体系 | §4 | 覆盖强度阶梯 + 零校验不得 PASS + 7 个缺口修复设计 |
| **REQ-149** | 「依赖边界的代码增加可调测性设计，后续有问题能第一时间发现并保证低代价适配」 | (D) 可调测性 | §5 | 单一诊断入口 S0-S7 + fixture 策略 + 升级演练 |
| — | （可实施性） | (E)(F)(G) | §6/§7/§8 | 垂直切片 + 机检验收 + 非目标与风险 |

---

## 2. (A) 依赖契约层 —— REQ-147 的解

### 2.1 契约的边界：什么进契约，什么不进

契约**只承载**「本插件消费的、由宿主或本包约定决定的事实」两大类：

| 命名空间 | 承载内容 | 为什么需要 | 反面（不进契约） |
|---|---|---|---|
| `host.*` | 宿主侧事实：安装锚点与平面布局、`DSH_HOME` 语义（写入侧 / 探测侧）、用户预设根与组合文件名、行契约（字段名/内建前缀/group 语义/`!!js` 方言）、**29 行（平台无关全集）× 包名 × config 键**、skill frontmatter 契约、上游 API 锚点、CLI 调用形态 | 这些是 dsh 单方面决定的事实；散落硬编码即 §4 盲区 B-1/B-3/B-7/B-10 | 任何"我们的策略"（如交付路径选择、warn-only 政策）不进 `host.*` |
| `own.*` | 本包约定：包身份与入口声明、`cordis.patch.yml` 形态不变量、预设 id/载荷路径/标记文件名、渲染 token 契约、关键路径 | 跨消费者 parity 契约（JS×Python×模板×hooks），必须与宿主事实区分开，否则"宿主改了"与"我们改了"无法分辨 | 治理规则文本、技能内容、版本号（版本走投影，见 §2.9） |
| `evidence.*` | 版本证据与兼容区间：审计锚点、记录时间、平面来源、oracle 包版本、`compat_range`、`verified_on` + TTL | C-20「版本/时效类声明 MUST 可机器刷新或校验」；G-11/G-12 的失真面 | **不得**被 `version-projections.json` 投影（它是宿主事实，不是我们的版本派生，见 §2.9） |
| `coverage.*` | 逐条目的目标覆盖强度 + 守卫引用 + 反相 fixture 引用 | §4.1「可信面 ≤ 校验面」需要可机检的声明 | 不承载测试实现细节 |
| `elimination.*` | AUDIT-153 §3.1/§3.2 的逐条处置与切片归属 | REQ-146 的验收信号「前后依赖点计数下降且可机器复查」需要机器可读的基线 | 不承载"日记式"说明 |

**契约外判定**：契约不是"文件清单"。凡是**消费代码里出现的、契约已声明字段的等价字面量**（包名、行 id、config 键、路径、环境变量名、API 符号名），除非在契约内声明为 `allowlist` 并给理由，一律判为**契约外硬编码 → FAIL**（这就是 REQ-147 验收信号的机检形式，见 §2.8）。**allowlist 本身受约束（R0 BT-R-01）**：每条 MUST 含 `literal` + `reason` + `since_slice`，条数受棘轮预算约束（K-11，只降不升）——豁免通道不得成为自我认证的出口。

### 2.2 载体形态：候选与裁决

| 方案 | 形态 | 优点 | 缺点 | 裁决 |
|---|---|---|---|---|
| **F-JSON（推荐）** | 单文件 JSON（`adapters/dsh/host-contract.json`） | ① Python 侧 `json` 为 stdlib；② JS 侧 `JSON.parse` + `readFileSync`（`lib/index.js:130` 已有同款用法）；③ shell hooks 无需解析器（改用静态校验，见 §2.5）；④ 不是 Python 模块 ⇒ **不进入 `LOADER_WHITELIST` 闭集**（C-12 零改动）；⑤ 数据与代码分离，评审 diff 可读 | 无注释（改用 `_note` 字段与 `docs` 指针）；类型不自证（用 `schema_version` + 校验器补足） | **采用** |
| F-PY | Python 常量模块（`infra/dsh_contract.py` 内嵌数据） | 类型/注释友好 | **JS 消费者无法读** ⇒ 必然产生第二事实源（`lib/index.js` 只能继续内联），直接违背 REQ-147 的"单一事实源" | 排除 |
| F-YAML | YAML 文件 | 可注释 | Python 侧无保证可用的解析器（PyYAML 在测试中被门控，非硬依赖）；JS 侧 `js-yaml` 属**宿主平面**包，作为消费者依赖即引入依赖 | 排除 |
| F-MD | Markdown + 内嵌 fenced JSON | 人读友好 | 需要解析围栏（正则提取），双格式易漂移；校验成本高于收益 | 排除（人读面用 `docs/` 表格替代） |

### 2.3 放置位置：候选与裁决（含 C-8 / C-9 / C-10 / C-12 影响面）

**推荐：`adapters/dsh/host-contract.json`**（适配层）。理由与结构性影响：

| # | 论据 | 证据 |
|---|---|---|
| P-1 | **语义归属**：契约内容 100% 是宿主接口事实，属适配层资产；把宿主事实放进 `core` 会让"宿主依赖最小化"（REQ-146）在结构上反向恶化 | §2.1 命名空间表；`skills/software-project-governance/core/` 是"工作流合约/模板/生命周期/Gate/Profile"面（E-8） |
| P-2 | **结构性成本为零（C-8/C-9/C-12）**：`adapters/` 已在 `cleanup_scope.directories` 与 `PLUGIN_SCOPE_DIRS` 的同一 11 元集内（集合相等不变）；`adapters/dsh/` 已在 `package.json:34` 的 `files` 白名单内（D-06 不变）；JSON **不是** loader 模块 ⇒ `LOADER_WHITELIST` 不变（C-12 零改动） | E-7 / E-8 / E-9 / E-4 |
| P-3 | **不进技能树/投影面**：`skills/software-project-governance/` 是 `customSkillDirs` 注册的技能根，且 `infra/**/*.py`、`core/**/*.json` 出现在 `PROJECTION_SYNC_PATTERNS` 申报清单内；把宿主事实表放进技能树会让宿主事实出现在"会被镜像/会被投影"的资产面 | E-5（`:6585`）、E-22（`files` 含 `skills/`） |
| P-4 | **可逆性**：迁移到 `core/` 的成本 = 1 个路径常量（`dsh_contract.py`）+ 1 个 JS URL + 1 个 hooks 校验常量 ⇒ **可逆决策**，可以现在定，等 `dsh_compat.py` 归属 DEC 一并复审 | §2.9.4；ADR-018 D-2 可逆性标注 |

**必须如实登记的成本（不隐藏）**：core `infra/` 读取 `adapters/dsh/` 形成一条 **core→adapter 数据边**，与 E-16 已登记的既有偏差（`dsh_compat.py` 归属未裁决）**同类**。本设计的处理不是掩盖而是三件事：(a) 把这条边收窄为"一个访问器 + 一个数据文件"（今天 = 3 个模块约 30 处硬编码字面量）；(b) 在 ADR-018 与契约 `own.notes` 中显式登记；(c) 提供近零成本迁移路径，使该边可在 `dsh_compat.py` 归属 DEC 中一并裁决（§9 U-6）。

| 被排除候选 | 排除理由 |
|---|---|
| 放 `skills/software-project-governance/core/` | P-1（语义归属错位）+ P-3（进入投影申报面与技能根）；并且会与待裁决的 `dsh_compat.py` 归属相互锁定，提高迁移成本 |
| 放包根 `dsh-host-contract.json` | 包根文件需逐个进 `files` 白名单、`root_entries` 与 manifest 声明（三处同步），且包根没有分层归属；包根今天唯一的 dsh 面文件 `cordis.patch.yml` 是 dsh 约定的强制位置（D-01） |
| 放 `skills/software-project-governance/infra/` | 与 `dsh_compat.py` 同属待裁决的 core 面，把宿主事实表固化进 core；且 `infra/` 是被投影清单覆盖的目录 |

### 2.4 契约字段表（逐字段：取值来源 / 消费方 / 判据）

> 下表是契约的**规格**（不是最终 JSON 全文）；每个字段给出「取值来源」「消费方」「机检判据」。字段名以 `$` 表示层级。

#### `evidence.*`（版本证据；C-20 的载体）

| 字段 | 取值来源 | 消费方 | 判据 |
|---|---|---|---|
| `$evidence.audit.{id,path,head,date}` | AUDIT-153 头表 | `dsh-doctor`（报告溯源）、`check-dsh-boundary` | 路径存在 + 文本含该 head/date；缺失 → FAIL（证据链断裂） |
| `$evidence.recorded_on` / `$evidence.verified_on` | **机器写入**（`dsh-doctor --record-evidence`，需真实平面运行） | `check-dsh-boundary`（TTL）、`adapters/dsh/adapter-manifest.json` 一致性判据 | `now - verified_on > ttl_days` → FAIL（声明过期，C-20）；**不得**在被读取时自动刷新 |
| `$evidence.verified_on_ttl_days` | 人工设定（默认 180） | 同上 | 必须是正整数 |
| `$evidence.plane.{source,node_modules}` | 记录时实测 | `dsh-doctor --stage S3` | 与当次实测平面比对；不一致 → `[EVIDENCE-STALE]` 披露 + remediation |
| `$evidence.dsh_cli_version` | 记录时实测（当前实测为 `0.1.5-rc.1`） | S3 报告、`adapter-manifest.json` 一致性判据、G-11/G-12 修复 | 与当次实测不一致 → `[EVIDENCE-STALE]`；**该字段绝不参与版本投影**（§2.9.3） |
| `$evidence.oracle_packages`（4 包版本） | 记录时实测 | S3 报告、`[SKEW]` 判据 | 与当次实测逐包比对 |
| `$evidence.compat_range` | 人工裁定 | S3、`dsh-doctor` 顶层 verdict | 实测 dsh 版本落在区间外 → **FAIL**（这是 D-05「无版本闸门」的替代实现）；区间内但证据过期 → `NOT_RUN` 级披露 |

#### `host.*`（宿主事实）

| 字段 | 取值来源 | 消费方（今天 → 改造后） | 判据 |
|---|---|---|---|
| `$host.install.scope`=`@deepseek-ai`、`cli_package`=`dsh`、`anchor_rel` | AUDIT-153 D-69 实测 | `dsh_compat.py:134-136` → 读契约 | 与消费代码逐字相等；契约外出现 `@deepseek-ai/dsh` 形态字面量 → FAIL（除非 allowlist：`@deepseek-ai/cordis*` 属 oracle） |
| `$host.install.env_overrides`（`DSH_INSTALL_DIR` / `DSH_HARNESS_NODE_MODULES`） | D-69 同源 | `dsh_compat.py:126-129` → 契约 | 同上 |
| `$host.install.profiles_dir_name`=`profiles`、`plane_layout`（2 形态） | D-72 实测 | `dsh_compat.py:542-576` → 契约 | 平面发现结果非空时其形态必须属于 `plane_layout`；否则 FAIL |
| `$host.env.home_var`=`DSH_HOME`（**R0 F-6：写入侧与探测侧必须拆分**）<br>`$host.env.write_side.{blank_policy,trim_policy,fallback,tilde_expansion}`（**写入侧三实现 `lib/index.js` / `launch.py` / doctor 的记录路径必须一致**）<br>`$host.env.probe_side.{require_explicit,no_fallback}`（**探测侧保持 fail-closed**：`require_explicit=true`、`no_fallback=true`） | 写入侧 = AUDIT-153 G-06 逐 case 实测（**不是**注释推断）；探测侧 = `dsh_compat.py:553-563` 既有安全属性（只认显式 `DSH_HOME`，从不猜 `~/.dsh`） | 写入侧：`lib/index.js:101-111`、`launch.py:114-118`；探测侧：`dsh_compat.py:155,560-563`（**不改**） | 写入侧：§4.4.4 的三方差分 gate（全部 case 一致）；探测侧：`$host.env.probe_side` 与 `dsh_compat.py` 行为逐字对齐，且**反相断言**"未设 `DSH_HOME` 时不得读 `~/.dsh`"（既有 `test_dsh_compat.py:245` 固化）。**差分 gate 不适用于探测侧**（否则会改掉 guard 的安全属性） |
| `$host.home.user_preset_dir`=`.agent-presets`、`composition_file`=`agent.cordis.yml`、`composition_globs`（2 条） | D-18/D-73 实测（上游 `USER_PRESET_DIR`/`COMPOSITION_FILE`） | `lib/index.js:192`、`launch.py:122`、`dsh_compat.py:160-168`、`adapter-manifest.json:63`、hooks（静态校验） | 五处字面量必须等于契约值；hooks 由 §2.8 静态等式判据守护 |
| `$host.row_contract.*`：`id_field`/`name_field`/`config_field`/`group_field`/`disabled_field`/`builtin_prefix`=`cordis:`/`builtin_group_name`=`cordis:group`/`js_dialect_tag`=`!!js`/`loader_scope`=`[baseUrl,process,console]`/**`loader_scope_baseurl_shape`=`"file-url"`（R0 F-10：固定 `baseUrl` 取值形态 = 组合文件的 `file://` URL，`dsh_compat.py:433` `pathToFileURL(file.path).href`）**/`group_self_disabled_shortcircuit`=true/`ancestor_disabled_inherited`=true | loader 源码实测（AUDIT-153 §4 D-38/D-39/D-75 + G-02/G-03 引用的 `Entry._disabled` 首行与祖先走查）；`baseUrl` 形态 = E-3（探针实现） | `dsh_compat.py` `PROBE_SCRIPT`（`:283-331`）→ 契约（脚本由 Python 注入常量，见 §2.5） | 每个语义位必须有**反相 fixture**：`group name` 不可解析 / group 自身抛错但无子行 / 祖先 disabled 继承 / `process` 不在 scope / **`baseUrl` 非 file-url 形态（`FX-BASEURL-01`）** |
| `$host.rows[]`（**平台无关行全集 = 29**，每条含 `row_id` / `package` / `disabled_expr` / `platform_conditional`（2 行）/ `enabled_on` / `config_keys[]` / `config_declared` / `group`；**平台无关**是关键字面） | 行集 = E-10 逐行复算（29 行；与 AUDIT-153 `rows_enabled: 23` 的换算关系见 E-10②） | `dsh_compat.py`（不动其 oracle 机制）、Check 28w、`dsh-doctor --stage S2`、模板 | **双向一致**：模板逐行 ↔ 契约 `host.rows[]`（**全集 29 比对**，含平台条件行与 `disabled:true` 行）；模板多一行 / 契约多一条 / 包名或 config 键不一致 → FAIL（这是"契约被消费"的最强判据） |
| `$host.rows[].{schema_export, required_keys[], accepted_keys[], probe_result}`（**记录式子块**，字段级 `"source": "recorded"`） | **R0 F-5：仅 `dsh-doctor --record-evidence` 在真实平面记录**（AUDIT-153 只实测了 `dsh-persona.prefix` 必填一条，**不足以誊抄 29 行**） | V8 的 `host-facts` 冻结 + S2 的 `coverage` | **V1 阶段这些字段可以为空且 MUST 标 `"source": "recorded"` + `"recorded": false`**；K-1 只要求字段存在，不得要求非空；未记录时 S2/演练输出 `NOT_RUN(no-recorded-schema-shape)`。**禁止人工誊抄**（那会把契约退化为第二事实源，违 REQ-147） |
| `$host.skill_frontmatter.{name_equals_filename: true, description_required: true, fence: "---"}`（**R0 F-4**：D-62/D-63/D-64 的单点表达） | `launch.py:652-658` 既有校验 + D-62/D-63 | `launch.py`（S6 校验）、`adapters/dsh/skill-shims/*`、Check 28w | 9 个 shim 的 frontmatter 逐文件按此判据校验（缺 `name:` 或 `description:` → FAIL）；shim 文件名 ↔ `name:` 同名（`governance.md` ↔ `name: governance`）。**guard 归属（R1 N-4）** = `test_dsh_adapter.py::test_skill_shim_frontmatter_contract`（`:633-648`，≥9 shim 逐文件断言 fence / `name:<stem>` / 非空 `description`）——该既有可解析 guard 的引用 MUST 进入 `coverage.entries[].guard[]`（K-8 解析目标） |
| `$host.apis.{package: {exports[], role}}`（4 个 oracle 包 + 导出符号） | D-74 实测（`entryListSchema`/`evaluate`/`isJsExpr`/`resolveConfig` + `js-yaml`） | `dsh_compat.py:146-151, 211-227`（`PROBE_SCRIPT`）→ 契约注入 | 符号存在性由探针实测；符号名来自契约，探针脚本不再内嵌字面量 |
| `$host.cli.{version_command, dump_config_command, plugin_command, probe_invocation}` | D-57/D-12/D-81 | `adapter-manifest.json`、`dsh-doctor` S3/S5、`dsh_compat.py:775-785` | `dump_config_command` 只允许在**授权模式**下执行（§5.2 S5） |

#### `own.*`（本包约定）

| 字段 | 取值来源 | 消费方 | 判据 |
|---|---|---|---|
| `$own.package.{name,type,main,exports,files,engines_node,dsh_bundle_patch_key}`（**R0 F-4**：`dsh_bundle_patch_key` = `"dsh.bundle.patch"`，D-01 的单点表达，同时给 K-2 的"config 键名"类别提供命中目标） | `package.json:3,19-27,28-40,41-45` | `check-dsh-boundary`、`launch.py`、`lib/index.js` | 与 `package.json` 逐字相等；**D-08 三方一致**（包名 = `cordis.patch.yml:43` = profile 声明）由判据机检；`files` 必须覆盖契约自身与预设载荷；`dsh.bundle.patch` 键存在且其值指向 `$own.patch.file` |
| `$own.patch.{file,shape_invariants[]}`（`exactly-one-insert-row` / `no-id-update` / `no-trust` / `no-!!js`） | DEC-187 I-1/I-2 + D-10 实测 | Check 28w、`dsh-doctor --stage S1` | 4 条不变量逐条机检（今天已有测试覆盖其中 2 条，见 §4.2） |
| `$own.preset.{id, payload_dir, template, metadata, version_marker, skill_root_marker}` | FIX-310 交付形态 | 两个渲染器、hooks、`verify_workflow`、`adapter-manifest.json` | 五个消费方的字面量必须等于契约值 |
| `$own.render.tokens`（3 token → 相对路径） | `lib/index.js:83-87` × `launch.py:100-107` | 两个渲染器、模板、Check 28w | **双向集合相等**：模板出现的 token 集合 == 契约 token 集合（"拼错 token"因此变红，见 §4.4.5）；**未知 token 扫描** = `__[A-Za-z0-9_]+__`（渲染后命中即失败） |
| `$own.render.{newline_policy:"lf", leftover_scan, custom_skill_dirs_shape}` | D-66 / G-05 实测 | 两个渲染器、`_custom_skill_dir_entries`、`checks/projection.py` | §4.4.3（同缩进形）与 §4.4.6（行尾）的判据 |
| `$own.paths.*`（host_row / launcher / guard / accessor / doctor / manifest / hooks / skill_shims_dir） | 仓库结构 | 全部消费者 | 路径存在性 + 声明与实际一致 |
| `$own.checks.{smoke_section_title, compat_section_title, upgrade_regression_label, exit_codes}`（**R0 F-4**：`exit_codes = {"smoke": {"PASS": 0, "FAIL": 1, "REFUSED": 2}, "doctor": {"NONE": 0, "FAIL": 1, "REFUSED": 2}}`，D-53 的单点表达） | `verify_workflow.py:6892`、`dsh_compat.py:1035`、`launch.py:352-354`（`SMOKE_EXIT_*`） | `verify_workflow.py` 引擎、`dsh-doctor`、`launch.py` | 退出码表与三处实现逐项相等；`dsh-doctor` 的退出码语义 MUST 与该表一致（§5.1）；改成结构化字段后，S6 不再依赖 `[SMOKE]` 文本正则（D-84）。**guard 归属（R1 N-4）** = 既有退出码/隔离用例 `test_dsh_adapter.py:782`/`:806`/`:819`/`:832`（REFUSED 与隔离路径）+ `:1066`（28u 临时 home 清理）+ **K-12**（doctor ↔ boundary 裁决一致）——同样 MUST 进入 `coverage.entries[].guard[]` |

#### `coverage.*` / `elimination.*`

**`coverage.entries[]` 采用双键（R0 F-14：否则「62 条必要依赖各有声明」不可判定）**：

| 键 | 形态 | 作用 |
|---|---|---|
| `subject` | 契约内 JSON path（如 `host.rows[persona].config_keys`、`host.home.user_preset_dir`、`own.render.tokens`） | 指向**被声明强度**的那个契约字段——K-8 的解析目标 |
| `audit_ids[]` | AUDIT-153 的 `D-nn` 编号（如 `["D-24","D-25"]`） | 指向**依赖来源**——K-9 的覆盖目标；`audit_ids` 的并集 MUST ⊇ `elimination.audit_baseline.necessary_ids`（62 条必要依赖） |
| `target` / `guard[]` / `negative_fixtures[]` / `requires[]` / `gap_note` | 见 §4.1 阶梯表 | 强度声明与佐证 |

**判定规则**：同一 `subject` 可承载多个 `audit_ids`（AUDIT-153 的多条依赖属同一聚类）；**一个 `audit_id` 允许出现在多个 `subject`**（例：`D-34/D-35` 同时属"18 行"与"`customSkillDirs` 通道"两个聚类——AUDIT-153 §3.3 已如此聚类）。因此 K-9 的判据是**覆盖（⊇）+ 无空 `audit_ids`**，不是"一一映射"；重复声明只在 `subject` 完全相同时判为重复（→ FAIL）。

`elimination.*` 见 §3：`{audit_baseline:{total, necessary:[D-nn...], weakenable:[...], eliminable:[...]}, dispositions:[{id, class, decision, slice, evidence, removed_at?, weakened_at?}]}`。

### 2.5 消费方改造表（每个消费方如何改为从契约读取）

| # | 消费方 | 今天读什么（证据） | 改造后 | 失败语义 | 必须保持的不变量 |
|---|---|---|---|---|---|
| C-1 | `lib/index.js`（宿主行） | 内联 `TOKEN_PATHS`（`:83-87`）、`.agent-presets`（`:192`）、`.dsh`（`:105`）、`trim` 逻辑（`:103`）、marker 名（`:70,80`） | `JSON.parse(readFileSync(new URL('../adapters/dsh/host-contract.json', import.meta.url)))`，经**模块级 memoized `contractTokens()`** 读取；两个函数内读取点 = `ensurePreset()` 与 `renderComposition()`；**顶层零 I/O**（R0 F-3） | 读/解析失败 → `ctx?.logger?.warn(...)` + 返回 `{synced:false, contract:'unreadable'}`；`renderComposition` 回退为空 token 表 ⇒ `leftovers` 非空（**不抛**）；**永不抛** | **C-1 不变量**：零运行时依赖 / warn-only / 永不抛 / 导出面不变 / 无内联回退副本（详见 §2.6） |
| C-2 | `adapters/dsh/launch.py` | `dsh_home()`（`:114-118`）、`TOKEN_PATHS`（`:100-107`）、`PRESET_ID`/marker（`:109-111`）、手写缩进扫描（`:447-465`） | `from dsh_contract import load_contract`（`sys.path` 注入 `INFRA_DIR` 已有先例 `:543-545`）；渲染 token、预设路径、`custom_skill_dirs_shape` 全读契约 | 契约缺失/损坏 → 打印可行动错误 + 返回非 0（**不静默使用内置副本**） | 渲染 parity（三路径 sha256 全等）；`--dry-run` 零写入；`--uninstall` 逃逸守卫 |
| C-3 | `infra/dsh_compat.py`（护栏） | `DSH_SCOPE`/`DSH_PACKAGE`/`INSTALL_ANCHOR_REL`（`:134-136`）、`ORACLE_PACKAGES`（`:146-151`）、`DSH_HOME_ENV`/`PROFILES_DIR_NAME`（`:155-156`）、`COMPOSITION_FILENAMES`/`GLOBS`（`:160-168`）、`PROBE_SCRIPT` 内的 API 名与 scope（`:211-227, 234-270, 433`） | 常量改由 `dsh_contract` 提供；`PROBE_SCRIPT` 内 API 名/scope/tag 由 Python 侧以 JSON 注入 request（脚本内只保留结构） | 契约不可读 → `NOT_RUN`（**绝不 PASS**），reason 指向契约路径 | NOT_RUN 政策（`:75-77`）；不复制任何 schema（oracle 仍是安装态导出） |
| C-4 | `verify_workflow.py`（引擎） | `[SMOKE]` 输出正则（`:6797-6799`）、label 常量（`:6892`）、28u 的 subprocess 管道（`:6823-6846`） | 结构化：`dsh_doctor.run_isolated_smoke()` 返回 dict；`check_dsh_preset_smoke` 委托之（保持其既有返回形状与 CLI 输出）；section 标题/label 读契约 | 委托失败 → FAIL（fail-safe 方向不变） | 引擎 print 预算（C-15：输出归 render 层）；28u 退出码语义与 CLI 文本不变 |
| C-5 | `infra/hooks/{pre-commit,commit-msg,post-commit}` | 硬编码 `${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance`（E-14） | **运行时零改动**（shell 无 JSON 解析能力，加解析即引入新耦合）；改为**静态等式判据**：Check 28w 断言 hook 文本中的路径表达式 == 由契约拼出的同一表达式 | 契约漂移 → CI FAIL | hooks 零运行时依赖；用户仓副本不受影响（见 §8.2 R-7） |
| C-6 | `agent-presets/governance/agent.cordis.yml.template` | 3 token + **29 行（平台无关全集）** | 文本不改；由 Check 28w 断言"模板行集（全集 29）↔ 契约 `host.rows[]` 双向一致"、"模板 token 集 ↔ 契约 token 集双向一致" | 任一侧多/少/拼错 → FAIL | 单源模板（FIX-310）；渲染输出不变 |
| C-7 | `adapters/dsh/adapter-manifest.json` | `verified_on`/证据串（E-12）、路径描述（`:32,63`） | 版本证据改由契约 `evidence.*` 提供；manifest 保留"指向契约"的表述 | 与契约不一致 / TTL 过期 → FAIL | `print_manifest` 消费的字段名不变（D-60），仅加存在性校验 |

#### 2.5.1 访问器接口契约（R0 F-7）

```python
# skills/software-project-governance/infra/dsh_contract.py
CONTRACT_REL: str = "adapters/dsh/host-contract.json"
SUPPORTED_SCHEMA_VERSIONS: tuple[int, ...] = (1,)

def load_contract(root: Path | None = None, *, raw: str | None = None) -> dict:
    """Load + minimally validate the host contract. Never guesses, never falls back."""

def contract_path(root: Path | None = None) -> Path: ...
def get(path: str, contract: dict | None = None) -> Any: ...   # 点/方括号路径取值，缺失 raise
def reset_cache() -> None: ...                                  # 仅测试用
```

| 异常 | 触发条件 | 消费方语义（逐消费方约定） |
|---|---|---|
| `ContractUnreadable` | 文件不存在 / 读失败（`OSError`） | `lib/index.js` → warn + 跳过同步；`launch.py` → 可行动错误 + 非 0；`dsh_compat.py` → `NOT_RUN`；`check-dsh-boundary` → **FAIL**（K-1） |
| `ContractMalformed` | JSON 解析失败 / 顶层非对象 / 必填字段缺失 | 同上，但**不得**被降级为 `NOT_RUN`：`dsh_compat.py` 仍取 `NOT_RUN`（无法校验是本意），而 `check-dsh-boundary` MUST FAIL（畸形 = 产品缺陷，不是环境缺失） |
| `ContractSchemaUnknown` | `schema_version` 不在 `SUPPORTED_SCHEMA_VERSIONS` | 四个消费方一律 **fail-closed**：JS warn+跳过、Python 非 0 / `NOT_RUN`、检查 FAIL；**禁止**按旧版本猜测解析 |

**契约与判据的一致性**：K-1 直接引用本表的三个异常类名与"必填字段清单"（同一分类，不另立词汇）；错误消息 MUST 含 `契约路径 + 异常类 + 具体字段/偏移`（可行动）。

### 2.6 JS 侧（`lib/index.js`）的边界 —— 保护 C-1 不变量

**不变量清单（改造 MUST 全部保持）**：

| ID | 不变量 | 证据 | 本设计的保护手段 |
|---|---|---|---|
| J-1 | **零运行时依赖**：不 import 任何非 `node:` 模块 | `:58-61` 仅 `node:fs/os/path/url`；`:92-97` 明示"deliberately inlined instead of imported … a module-load failure can never take down the host's boot" | 契约经**包内文件读**（`readFileSync` + `new URL`，与 `:130` 读 `package.json` 同款），不引入任何包依赖 |
| J-2 | **warn-only / `apply()` 永不抛** | `:227-238`；`:184-187` 注释；`test_dsh_adapter.py:1213` | 契约读取放在 `ensurePreset()` 的 `try` 内（`:191` 起）——**与 CODE R0 F2 的修复位置一致** |
| J-3 | **顶层零 I/O**（R0 F-3 修正：不是"只在 `ensurePreset` 内读"） | 今天顶层只做常量与函数定义（`:83-87` 的 `TOKEN_PATHS` 是模块级常量） | 顶层**零 I/O、零 `import` 新增**（`readFileSync` 不出现在模块顶层）；契约读取收敛到**模块级 memoized `contractTokens()`**，由**两个函数内读取点**调用：`ensurePreset()`（`:180` 起）与 `renderComposition()`（`:149` 起，因为 `test_dsh_adapter.py:1138-1156` **直接调用**它并断言 `leftovers == []`）。memoize 保证一次进程内只读一次；两者都在 `try` 内调用或自行 try/catch ⇒ 契约不可读时 `renderComposition` 返回空 token 表 + `leftovers` 覆盖全部模板 token（非空），**不抛**。**硬约束仍是"顶层同步读会把『包内少一个文件』升级为『宿主行 import 失败』"** |
| J-4 | **无内联回退副本** | — | 契约不可读时**跳过同步**（warn）而不是回退到内置常量：保留副本即产生第二事实源，直接违背 REQ-147。代价 = 契约损坏时预设不交付；由 §5 的 S1 阶段给可行动 remediation，并由 CI（28u/28v）在发布前拦住 |
| J-5 | **导出面不变** | `['apply','ensurePreset','name','renderComposition']`（D-13 实测） | 不新增导出；`renderComposition` 签名不变（新增行为只在其内部） |
| J-6 | **渲染 parity 不变** | 三路径同 sha256（AUDIT-153 §2.7 实测） | 契约只把常量搬走，不改变取值；parity 测试 `test_dsh_adapter.py:1127` 为回归闸门 |
| J-7 | **幂等语义不变** | `.dsh-bundle-version`（D-19 实测） | marker 名从契约读，语义不变 |

**明确的负面清单（JS 侧禁止）**：不 import `@deepseek-ai/*`；不读 `~/.dsh` 之外的路径；不做网络调用；不在 `apply()` 外产生副作用；不因契约缺失而抛；**不在模块顶层做 I/O**。

**J-3 的取舍已写进不变量本身**（R0 F-3）：直调 `renderComposition` 时也需要 token ⇒ 读取点是**两个函数**而非一个；代价是"函数内读"而非"模块级读"，收益是顶层仍无 I/O。该取舍的反相 fixture = `FX-JS-03`（契约缺失时 `renderComposition` 不抛、`leftovers` 覆盖全部 token；`ensurePreset` 跳过同步且 `outcome.contract == 'unreadable'`），见 §5.6。

### 2.7 契约保鲜与证据刷新（C-20 / C-22）

| 机制 | 形式 | 判据 |
|---|---|---|
| **证据写入 = 单点** | `dsh-doctor --record-evidence [--out <path>]`：在**隔离 DSH_HOME**下探测真实平面 → 写 `evidence.{recorded_on, plane, dsh_cli_version, oracle_packages, verified_on}` | 只有该命令写 `evidence.*`；`git diff` 可审 |
| **不得自动刷新** | 读取方（护栏/检查）**只读**，不写回 | 代码评审 + 反相测试（读取路径不得修改契约文件 mtime） |
| **TTL 判据** | `now - verified_on > ttl_days` → FAIL（"声明过期"） | `check-dsh-boundary` |
| **新鲜度纪律** | 每次 dsh 升级后 MUST 重录证据（写入 0.81.0 的升级 SOP，见 §5.5） | `dsh-doctor` 在 S3 输出 `[EVIDENCE-STALE]` + remediation 命令 |
| **清单保鲜** | `host.rows[]` / `own.*` 双向一致判据（C-22：避免本设计退化为一次性文档） | Check 28w（模板 ↔ 契约） |

### 2.8 契约的机器校验（Check 28w `check-dsh-boundary` 判据清单）

> 说明：Check 28w 是本设计的**新增 gate 判据**，落地于切片 V8（§6）。以下每一条都是可机检的。**例外（R0 BT-R-01）**：**K-2 提前到 V2 落地**（见 §6.1 V2），其余 K 判据随 V8。

| # | 判据 | 落地 | 失败信息形态 |
|---|---|---|---|
| K-1 | 契约 JSON 可解析 + `schema_version` 已知 + 必填字段齐全（字段表 §2.4 全覆盖，**含 `source: recorded` 子块的"存在但可为空"语义**）；失败按 §2.5.1 的三异常类分类 | V8（引用 §2.5.1 分类） | `ContractMalformed: missing host.env.probe_side.no_fallback` + 契约路径 |
| K-2 | **契约外硬编码扫描**（**V2 落地**，R0 BT-R-01）：在声明的消费者集合（`lib/index.js`、`launch.py`、`dsh_compat.py`、模板、hooks、`adapter-manifest.json`、`package.json`、`cordis.patch.yml`）中，凡出现契约已声明类别的字面量（`@deepseek-ai/dsh-*` 包名、`cordis:` 前缀、config 键名、`.agent-presets`、`agent.cordis.yml`、`DSH_HOME`、4 个 API 符号名、**拼接后的 hook 路径表达式见 K-5**），必须能在契约中命中；未命中且不在 allowlist → FAIL，输出 `file:line + literal`。**V2 形态 = 纯正则/文本扫描**（不依赖 `checks.dsh_boundary` 模块，成本极低），V8 升级为带 allowlist 校验的版本 | **V2**（文本扫描）/ V8（完整） | `outside-contract host literal: adapters/dsh/launch.py:122 ".agent-presets"` |
| K-3 | **模板 ↔ 契约 `host.rows[]` 双向一致（全集 29 行比对）**：行 id / 包名 / config 键集合 / `disabled` 形态（`disabled_expr`、`platform_conditional`）；**平台条件行与 `disabled:true` 行必须出现在契约里**（否则任一侧的单边新增不可见） | V8（V1 有单元级等价判据） | `template row not in contract: tool-bash` / `contract row absent from template: tool-fs-search` |
| K-4 | **token 集双向一致**：模板出现的 `__…__` 集合 == 契约 token 集合；且渲染后不得残留任何 `__[A-Za-z0-9_]+__` | V8（V1 单元级） | `unknown token in template: __GOVERNANCE_SKILLS_ROOTS__` |
| K-5 | **hooks 路径表达式等式**：hook 文本中的 `${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance` 必须等于由契约 `host.env.*` + `host.home.*` + `own.preset.id` 拼出的表达式 | V8 | `hook path drift: pre-commit:70` |
| K-6 | **patch 形态不变量**：恰一行 `insert`、零 `- id: <host row>` UPDATE、零 `trust:`、零 `!!js` | V8（既有测试已覆盖 2 条） | 逐条命中即 FAIL |
| K-7 | **版本证据一致性**：`adapter-manifest.json` 的 `runtime_e2e` 证据版本 / `verified_on` 与契约 `evidence.*` 一致且未过 TTL；`cordis.patch.yml` 与 `lib/index.js` 内不得再出现 dsh 版本字面量。**该判据的结论 MUST 被 `dsh-doctor` S3/S7 直接消费（不得重算）**（R0 BT-R-02） | V8 | `manifest evidence drift: 0.1.0-rc.6 vs contract 0.1.5-rc.1` |
| K-8 | **覆盖强度声明可证**（§4.1）：每个 `coverage.entries[]` 的 `guard` 引用必须解析到现存测试 id 或已注册 check id；`target == "strong"` 必须至少有 1 个 `negative_fixtures` 引用；`subject` 必须是契约内存在的 JSON path。**解析动作发生在 `checks/dsh_boundary` 内**（R0 F-15：`dsh_contract` 不得 import registry，否则成环） | V8 | `coverage claim unbacked: subject=host.rows[persona].config_keys` |
| K-9 | **归并处置完整性**（§3 + §2.4 双键）：`elimination.dispositions[]` 覆盖 `audit_baseline` 全部 ID 且无重复；`removed_at` 项有对应切片；**且 `coverage.entries[].audit_ids` 的并集 ⊇ `audit_baseline.necessary_ids`（62 条）**（R0 F-14） | V8 | `disposition missing for D-97` / `necessary dependency without coverage claim: D-62` |
| K-10 | **结构不变量**：契约文件在 `files` 白名单覆盖范围内；`canonical_product_artifacts` 含契约条目与 `host-facts` fixture 条目；`cleanup_scope.directories` 与 `PLUGIN_SCOPE_DIRS` 集合相等（既有守卫复用） | V8 | `contract not declared in canonical_product_artifacts` |
| **K-11** | **allowlist 受约束（R0 BT-R-01）**：`contract.allowlist[]` 每条 MUST 含 `literal` + `reason` + `since_slice`；条目数受**棘轮**约束（`allowlist_budget` 只降不升，超限 FAIL） | V8 | `allowlist entry without reason: "@deepseek-ai/cordis"` / `allowlist grew: 3 → 4 (budget 3)` |
| **K-12** | **同一事实单一裁决（R0 BT-R-02）**：同一仓库态下，`dsh-doctor --json` 的顶层 `verdict` 与 `check-dsh-boundary --fail-on-issues` 的退出码 MUST 一致（不一致 → doctor 自身 FAIL）；`coverage` 块**只允许一个生成点**（`check_dsh_preset_compat()`），doctor 只投影不重算 | V8 | `doctor/boundary verdict disagreement: doctor=PASS boundary=FAIL(K-7)` |
| **K-13** | **演练基线受约束（R0 BT-R-03）**：`host-facts-<v>.json` 的 `captured_at` 参与 TTL 判据；`--rehearse <new> --against <baseline>` 在 `new.dsh_version == baseline.dsh_version` 时 **FAIL（no-op rehearsal 不得绿）**；`new.captured_at` MUST **严格大于** `baseline.captured_at`；报告逐条带 `synthetic: true/false` | V8 | `rehearsal no-op: baseline and candidate are both 0.1.5-rc.1` |

### 2.9 迁移与回滚

#### 2.9.1 `core/manifest.json`（C-9）

- 新增 1 条 `canonical_product_artifacts.entries`：`{id: "dsh-host-contract", path: "adapters/dsh/host-contract.json", artifact_role: "host-dependency-contract", validation_commands: [...check-dsh-boundary...]}`。
- **口径修正（相对 AUDIT-153 §8.3 C-9）**：AUDIT-153 记「否则 `cleanup.py` 会把它们当残留」。本设计核实 `cleanup.py:204-214` 对 **dir 条目递归展开为 canonical**，而 `manifest.json:235` 已把 `adapters/` 声明为 dir 条目 ⇒ 新增文件**不会**被 cleanup 判为残留。因此 manifest 登记是**显式声明面**（可被 check 消费、可被读者审计），**不是**防删除的必要条件。【实测 E-7/E-8】

#### 2.9.2 `PLUGIN_SCOPE_DIRS` / `cleanup_scope.directories`（C-8）

- **零改动**：`adapters` 已在两侧 11 元集内（E-7/E-8），集合相等不变量保持。设计**刻意不引入新顶层目录**（记录式 fixture 放 `adapters/dsh/fixtures/` 下——`adapters/` 已是 dir 条目且已在 `files` 内，见 §5.4），从而避免同时改两处并触发 `checks/manifest.py` 的相等判据。

#### 2.9.3 版本投影（C-10）

- **新增投影 = 0 条**：契约不含本包版本串；`evidence.dsh_cli_version` 是**宿主版本事实**，MUST NOT 进 `version-projections.json`（否则 `check-projection-sync` 会试图把它改写成我们的版本 = 事实污染）。
- 既有 2 条 dsh 投影（`dsh-persona-version` / `dsh-agents-bootstrap-version`）不变（E-11）。
- **B-9 缺口不本版修**（`PROJECTION_SYNC_PATTERNS` 内 dsh 相关 0 条）：本设计的 §7 给出可机检的替代守护（K-3/K-7 已覆盖 persona 版本串与 bootstrap 版本串的存在性与 TTL），把「主 check 覆盖缺失」从"无守卫"降到"由 28w 覆盖"，**不改变** `PROJECTION_SYNC_PATTERNS` 清单（避免触发 `validation_inventories.min_entries=11` 与 `required_members` 的 exact 匹配面）。

#### 2.9.4 接线面（C-12 / C-14 / C-15）—— R0 F-2 后补全

> **R0 F-2 的根因**：新增段 28w + 新命令 `dsh-doctor` 触发**导入期与冻结面守卫**，仅改 `registry.py` 不足以让 V8 可执行。E-17~E-20 是实证依据。

| 面 | 改动 | 理由 / 步骤 |
|---|---|---|
| `infra/registry.py` | `LOADER_WHITELIST` **+2**（`checks.dsh_boundary`、`dsh_doctor`）；`_SEGMENT_LOADERS` **+1**（`("28w", "checks.dsh_boundary.check_dsh_boundary")`，70 → 71）；`_COMMANDS` **+1**（`("dsh-doctor", "dsh_doctor.cmd_dsh_doctor")`，82 → 83） | C-12 闭集显式登记；C-14 一一对应 |
| `infra/quickscan_registry.py` | `SEGMENTS` **+1** `SegmentSpec("28w", "distribution", ("plugin:asset:adapters/dsh/host-contract.json", "plugin:asset:agent-presets/**", "plugin:asset:lib/index.js", "plugin:asset:cordis.patch.yml", "plugin:asset:adapters/dsh/launch.py", "plugin:asset:skills/software-project-governance/infra/dsh_compat.py"), _excluded("PLUGIN_PACKAGE_ASSET"))`（input token 形态对齐 `28v` `:542-546`；**实现期以实际输入面为准**） | **导入期硬约束（E-17）**：`registry.py:658 CHECK_SPECS = _build_check_specs()` 在 `:627-633` 用 `registry_ids()` 与 `_SEGMENT_LOADERS` 求集合，缺一即 `raise RegistryError` ⇒ 只加 `_SEGMENT_LOADERS` 会导致 **import registry 直接失败** |
| `infra/verify_workflow.py` | ① `cmd_dsh_doctor` 薄包装 + 分发表项；② `_run_full_engine_checks` 内加 **28w section**（否则 `test_matches_the_live_engine_face`（E-19）的 observed ≠ declared）；③ 28u 委托 `dsh_doctor.run_isolated_smoke()`（D-84 弱化） | E-19 `:864-874` 要求 declared == observed；C-15：新 section MUST 走 render 层（输出归 `checks/dsh_boundary`），不增长 monolith 的 print 面 |
| **引擎侧 import 纪律（R6）** | `verify_workflow.py` 内对 `dsh_doctor` MUST **函数内惰性 import**（与 `cmd_check_dsh_preset_compat` 的 `from dsh_compat import run_cli` 同款），`r6_startup_budget.import_count` 保持 **196**（E-20） | 顶层 import 会触发 `test_engine_baseline_is_the_frozen_196_module_caliber` 与棘轮 R6 双红（E-19/E-20） |
| `infra/tests/test_registry.py` | `FROZEN_CLI_KEYS` 82 → **83**；`FROZEN_SEGMENTS` 70 → **71**；`:311-317` 的 `migrated` 精确列表 **+`"dsh-doctor"`**（因 `dsh_doctor` 非 `engine` 模块） | E-19 逐条冻结面；`migrated` 是**精确集合断言**，不同步即红 |
| `infra/contract_matrix/snapshots.json` | 由 `python skills/software-project-governance/infra/contract_matrix/generator.py --regen` 重生成（CLI 面 82→83、段面 70→71；`test_registry.py` 通过该快照做 `_frozen_faces()` 对账） | E-19/E-20；先例：FEAT-022/FIX-304 的契约变更路径 |
| `core/architecture-baseline.json` | `python …/verify_workflow.py archguard-ratchet --regen` 重生成（引擎 `anchor_loc` 24204 → 实测值、`r6_startup_budget.import_count` 保持 196、`r2_reverse_dependency` 面按实测） | E-20：基线陈旧即 FATAL（R7 已提交==fresh）；**只降不升**语义不变 |
| **R1 豁免到期处置（E-20 `:6`）** | `exemptions[0]`：`rule: "R1"` / `scope: "mainfile"` / `allowance_lines: 0` / `expire_version: "0.81.0"`。**本版到期** ⇒ 本设计给出两个选项并建议 **(a)**：<br>(a) **续期到 0.82.0 并在 DEC 中重述理由**（`--regen` 后 anchor 已含本次 wiring 行，allowance 仍为 0）；<br>(b) **退役该豁免条目**（删除 `exemptions[0]`，`--regen` 后 anchor 成为一个普通基线，任何后续增长即 FATAL）。<br>无论选哪个，MUST 由 DEC 显式登记（见 §10 O-8），**不得**静默留在 `0.81.0` 过期状态（棘轮会对过期豁免报错） | E-20 `:3-10`；`archguard_ratchet.py:38-42` 的自述 |
| `adapters/dsh/adapter-manifest.json` | 声明 `dsh-doctor` 为 dsh 面的诊断入口（`native_entry.note` 或 `validation` 段），使其与 `check-dsh-*` 并列可见 | D-93/D-90 的文档漂移面（本版不扩面，只加一行） |

> 备注（不作为论据，仅如实登记）：【实测·AUDIT】`registry.py:342` 的注释写「83 dispatch keys」（AUDIT-153 G-08b；我本次直接读取的是 `:229` 的「82 keys」与 `:405-406` 的段注册），本设计落地后**数值上**恰好变对；本设计**不改该注释**（属 G-08b 的独立修复面，登记不修）。

#### 2.9.5 回滚路径

| 回滚单位 | 手段 | 影响 |
|---|---|---|
| 契约层（V1+V2） | `git revert` V2 切片 → 消费方恢复内联常量（V1 的契约文件与测试保留为死数据，可再 revert 掉） | 无用户可见行为变化（V2 是行为保持重构） |
| 单一缺口修复（V3~V7） | 各切片独立 `git revert` | 逐缺口回退；`test_dsh_compat.py` 的改写随之回退（C-23 已声明） |
| 诊断入口（V8） | reject 前无产品代码依赖（新命令），直接 revert | 无回归面 |
| 整体 | 0.80.0 → 0.81.0 的回滚 = 回退到 0.80.0 tag；本设计不引入数据迁移、不改用户文件格式（预设文件内容不变） | 低 |

**为什么把契约落地切成 V1/V2 两片**：契约一旦被消费，回滚就跨文件。分成"数据层（新文件）"与"消费迁移（行为保持重构）"两片，使回滚可以只回退迁移而不动数据，反之亦然（D4：一次提交一个关注点）。

---

## 3. (B) 依赖最小化 —— REQ-146 的解

### 3.1 口径修正：AUDIT-153 §3.2 的计数与枚举不一致（如实标注）

- AUDIT-153 §3.2 标题声明「可弱化（**26** 条）」，但其表体逐行枚举为 **25 行**，展开后为 **36 个 ID**（`D-69~D-75` 一行含 7 个 ID；`D-30/D-31`、`D-66/D-100`、`D-67/D-68`、`D-90/D-93`、`D-58/D-59` 各含 2 个）。§2.11 的「可弱化 26」与 §2 表体的 `可弱化` 标记数（我逐段清点 = **21**）亦不一致。
- **本设计的处理**：以 AUDIT-153 §3.2 的**表体行**为分组单位，做**逐 ID 全覆盖**裁决（36 个 ID），并在契约 `elimination.dispositions[]` 里显式登记每个 ID。计数口径差异作为**审计口径问题**登记（不修改 AUDIT-153——它是已完成任务的事实输入）。REQ-146 的验收信号（"消除项在 0.81.0 中实际消失"）因此以**逐 ID 的 `removed_at`/`weakened_at` 字段**为准，而不是以"总数下降"为准。

### 3.2 §3.1「可消除」4 条处置裁决

| ID | AUDIT 判定 | **本设计裁决** | 理由（含反面证据） | 影响面 | 验收判据 | 切片 |
|---|---|---|---|---|---|---|
| **D-02** | 可消除（`dsh.profile` 键不存在） | **消除（确认不存在）+ 契约登记为"非本包声明"** | 实测 `package.json` 无该键；真实声明在 profile 侧，属 dsh 安装机制（AUDIT-153 §3.1）。契约 `host.notes.profile_declaration = "host-install-mechanism-not-ours"` 防止未来回流 | 无行为影响 | K-1/K-2（契约外不得出现 `dsh.profile` 写入） | V1 |
| **D-50** | 可消除（`!!js … new URL(…, baseUrl)` 死分支） | **消除（删除分支与 URL 数学）+ 保留一行显式诊断** | 渲染产物实测不含带 `baseUrl` 的 `!!js`；`test_dsh_adapter.py:227` 已断言产物无 `baseUrl`。**删除后**若真遇到该形态 entry：报显式 issue（不是静默解析），保持"不可静默"原则 | `launch.py:468-496`；`--smoke`/`verify_preset_loading` 路径 | `test_dsh_adapter.py` 全绿 + 新反相：注入 `!!js` entry → 明确 issue（非静默 PASS） | V5 |
| **D-56** | 可消除（`urllib` 2 个 import） | **消除（随 D-50 同片）** | 同 D-50；删除后 `import urllib.request` / `urljoin`/`urlparse` 无引用 | `launch.py:78,80` | 静态检查（无未用 import）+ 全量测试绿 | V5 |
| **D-05** | 「可消除 → 但 REQ-147 要求补齐」（缺 `peerDependencies`） | **弱化：不加依赖声明，改为机器校验的版本闸门**（`evidence.compat_range` + S3 判据） | ① AUDIT-153 §3.1 反面证据：把 `@deepseek-ai/dsh-home-paths` 变为真依赖会违反 `lib/index.js:94-97` 的宿主安全不变量；② `peerDependencies` 的**安装时语义**（npm 7+/pnpm 是否自动安装 peer）在 dsh/pnpm 语境下**未验证**（§9 U-1）——贸然补齐可能引入实质运行依赖边，与 C-1 直接冲突；③ "无版本闸门"的真实痛点是"升级后无人提示"，用契约 + 机检可以完全覆盖该痛点 | `package.json`（新增 peer 面）暂不动；`evidence.compat_range` 新增 | ① S3 在实测版本越界时 FAIL；② 契约外仍无 `dependencies`/`peerDependencies`（K-1/K-2）；③ 若 M-0 要求补齐声明，走 §9 U-1 验证后以 `peerDependenciesMeta.optional` 落地 | V1（闸门）/ U-1（声明） |

**反面证据执行声明**：本设计**不采纳**任何"把重复实现改为真依赖"的消除方向（`@deepseek-ai/dsh-home-paths` 不得成为真依赖）——D-16/D-47 一律走"契约化 + 三方差分校验"（§4.4.4）。

### 3.3 §3.2「可弱化」36 个 ID 处置裁决

> 裁决列：`弱化` = 按 AUDIT 方向落地；`保留原状` = 有证据说明现状已是该方向的合法形态；`登记不修` = 本版不做，进 §8.1 非目标。所有"弱化"都必须给出机检判据与切片。

| # | ID | AUDIT 弱化方向 | **裁决** | 落地形态 | 验收判据 | 切片 |
|---|---|---|---|---|---|---|
| 1 | D-07 | `engines.node` 硬约束 → 能力探测 | 弱化 | 契约登记 `own.package.engines_node`；`dsh-doctor` 报告实测 `node_version` 并与声明比对（不一致 → 建议级披露，不 FAIL） | doctor JSON 含 `host.node_version` + `node_engines_ok` | V1/V8 |
| 2 | D-11 | 版本引用动态读取 | 弱化 | 删除 `cordis.patch.yml:30` 的 dsh 版本字面量，改指契约 `evidence.dsh_cli_version` | 全仓 grep 无失真版本字面量（K-7） | V7 |
| 3 | D-14 | `ctx.logger` 可选化 | 保留原状 | 已用可选链（`:198,210-212,226,237`），属最低限度；契约登记 `host.row_contract.ctx_logger = "optional"` 使"可选"成为声明 | 契约字段 + J-2 不变量测试（无 ctx 调用不抛） | V1 |
| 4 | D-15 | 上游镜像版本引用去版本化 | 弱化 | 删除 `lib/index.js:92-93` 的 `installed dsh 0.1.5-rc.2`，改为"镜像对象与差异校验见契约 §evidence + `dsh-doctor --stage S3`" | K-7 + 注释不再含版本字面量 | V7 |
| 5 | D-16 | 内联 `DSH_HOME` 解析 → 契约化 + 差分校验 | 弱化 | §4.4.4（三方差分 gate；语义进契约；**不改为真依赖**） | 8 例 case 表全一致 | V6 |
| 6 | D-22 | staging+rename 声明化 | 弱化 | 契约 `own.preset.write_policy = "staging+rename, no-lock, best-effort"`（如实声明并发窗口，G-15 不在本版修） | 契约字段存在 + 与两份实现一致 | V1 |
| 7 | D-30/D-31 | `!!js process.platform` → 声明式能力探测 | 弱化（声明 + 反相，**不改模板**） | 契约 `host.row_contract.loader_scope`（= `[baseUrl,process,console]`）+ **平台条件行的唯一载体 = `host.rows[].{platform_conditional, enabled_on, disabled_expr}`**（2 行：`tool-bash` / `tool-pwsh`，见 §2.4 `$host.rows[]`）。**R1 N-1 修正**：删除原表述的 `platform_expr_rows[]`（该字段**不在** §2.4 字段表中；同一事实两个字段名违反"每字段单一含义"）——**不设**该派生字段，平台条件行一律由 `host.rows[]` 表达，禁止任何形式的第二来源；下游按 §2.4 实现即可 | 反相 fixture 变红可抓 | V4/V5 |
| 8 | D-45 | 宿主平面分工 → 机器可读契约 | 弱化（**带未验证标注**） | 契约 `host.host_plane_registries = {shell_env, subagents, web}`，字段备注 `verification: unverified (R-09)`；S5 恒为 `NOT_RUN`（除非授权） | 契约字段存在 + S5 输出 NOT_RUN + R-09 验证计划在案 | V1/V8 |
| 9 | D-47 | `launch.py` `DSH_HOME` 收敛 | 弱化 | §4.4.4 | 同 D-16 | V6 |
| 10 | D-49 | 手写扫描 → 复用真实 YAML | 弱化（结构化优先 + 差分 + 声明式 shape） | §4.4.3 | 同缩进形命中 2 条（与探针一致） | V5 |
| 11 | D-54 | witness 范围收窄 | 弱化 | `top_level` 只比**名字**（去掉 size/mtime_ns）；**采样定义（R0 F-13）**：采样对象 = `launch.py:409-444` 的 `_real_home_witness()` 两个分量（`top_level` 与 `write_surface`），采样时刻 = smoke 前 1 次、后**连续 2 次**（间隔 0）；比较式 = `top_level` 取前 1 次 vs 后第 1 次的**名字集合**差集（任一侧变化即"疑似写"），疑似的两个分量 MUST 在后第 2 次采样中**复现同样变化**才判 FAIL（仅出现一次 = 宿主竞态 → advisory 披露，不 FAIL）；`write_surface` 保持前 1 次 vs 后第 1 次逐项比较（`.agent-presets` 是我们的唯一写面，不容忍竞态） | 新反相：触碰 `settings.yaml`（改 size/mtime）→ **不** FAIL；真写入 `.agent-presets` → FAIL | V5 |
| 12 | D-57 | `verified_on`/证据由机器刷新 | 弱化 | §2.7（`--record-evidence` + TTL + K-7） | manifest↔契约一致 + 过期 FAIL | V7 |
| 13 | D-61 | 文案契约 → 语义契约断言 | 弱化 | 把 dsh 字面存在性断言改为"字面量来自契约"（检查断言词表由契约驱动） | 断言词表可追溯到契约字段 | V8 |
| 14 | D-66/D-100 | 行尾归一化显式统一 | 弱化 | 两个渲染器显式统一为"先归一 CRLF → LF，再归一孤立 CR → LF"（JS 侧正则扩展；Python 侧 `newline` 与显式替换）；`checks/projection.py:14` 的归一化同步补孤立 CR | 新反相：注入 1 个孤立 `\r` → 两渲染器输出 sha256 全等；投影哈希一致 | V5 |
| 15 | D-67/D-68 | node-gated skip → 显式 NOT_RUN 披露 | 弱化 | 契约 `coverage.entries[].requires`（如 `["node"]`）；`dsh-doctor --stage S6` 输出"因环境缺失而未验证的面"清单 | doctor 输出 `unverified_due_to_env[]` 且非空时不得给绿 | V1/V8 |
| 16 | D-69~D-75 | 护栏锚点/API 硬编码 → 单点契约 + 启动期能力探测 | 弱化 | §2.5 C-3（常量入契约 + 探针保留存在性检查与 NOT_RUN 降级） | K-1/K-2 + 既有 `test_oracle_failure_is_not_run_not_fail` 仍绿 | V1/V2 |
| 17 | D-79 | 临时目录清理可审计 | 弱化（advisory） | `dsh-doctor --stage S3` **只读**列出 `%TEMP%/spg-dsh-compat-*` 残留计数（不删除、不触碰用户目录） | 残留计数出现在报告；超阈值 → advisory 披露（不计 gate issue） | V8 |
| 18 | D-81 | Node CLI 调用契约声明化 | 弱化 | 契约 `host.cli.probe_invocation`（`node --input-type=module --eval` + stdin JSON 协议） | 契约字段 + 探针调用点读契约 | V1/V2 |
| 19 | D-82 | 渲染层契约声明化 | 弱化 | 契约 `own.checks.*_section_title` + 快照测试 | 快照一致；R4 print 预算不增（C-15） | V1/V8 |
| 20 | D-84 | launcher→checker 输出正则 → 结构化 | 弱化 | §2.5 C-4（`run_isolated_smoke()` 结构化；28u 委托） | 28u CLI 文本与退出码不变；doctor S6 用结构化字段 | V8 |
| 21 | D-90/D-93 | 文档/claim 矩阵漂移治理 | 登记不修 | 4 条 dsh claim 与适配器矩阵本版不动；由 §8.1 非目标承接 | — | — |
| 22 | D-99 | git hooks 路径发现契约化 | 弱化 | K-5 静态等式（不改 hooks 运行时） | hook 文本漂移 → FAIL | V8 |
| 23 | D-60 | manifest 字段带回退读取 | 弱化 | 契约登记 manifest 必读字段清单；`print_manifest` 前加存在性校验（缺字段 → 可行动错误而非 `KeyError`） | 反相：删一个字段 → 明确报错（不抛栈） | V1/V8 |
| 24 | D-58/D-59 | manifest 描述与实现一致性校验 | 弱化 | K-2/K-5 覆盖（预设根路径、加载模型路径字面量） | 不一致 → FAIL | V8 |
| 25 | D-76（形式） | 「有无 schema」判据扩大为显式列出零校验行 | 弱化 | §4.4.1（`UNVERIFIED_KINDS` + `coverage` 块 + 上屏） | §4.3 三层不变式 | V3 |

### 3.4 依赖面收窄的机检判据

| 判据 | 命令 | 期望 |
|---|---|---|
| 契约外硬编码字面量归零 | `check-dsh-boundary`（**待实现**，V8；其文本扫描部分 **V2 即落地**） | `PASSED — outside-contract host literals: 0 (allowlist 3/3 — @deepseek-ai/cordis* oracle names)` |
| allowlist 未膨胀（R0 BT-R-01） | 同上（K-11） | `allowlist 3/3 (budget 3, 只降不升)`；新增条目缺 `reason`/`since_slice` → FAIL |
| 消除项确实消失 | 同上（读 `elimination.dispositions[]`） | `eliminated: 3/3 executable (D-02/D-50/D-56); D-05 deferred to U-1` |
| 今天即可跑（无新命令） | `pwsh -Command "(Select-String -Path lib/index.js,adapters/dsh/launch.py,skills/software-project-governance/infra/dsh_compat.py -Pattern '@deepseek-ai/dsh-' -AllMatches).Matches.Count"` | 改造前 = **≥20**（今天散落的包名/config 键字面量）；改造后 = 契约内 + allowlist 之外 0（该 grep 计数下降但**不归零**——契约文件本身仍含包名，属正常） |

---

## 4. (C) 校验看护体系 —— REQ-148 的解

### 4.1 覆盖强度阶梯与「可信面 ≤ 校验面」的机检形式

**阶梯（与 AUDIT-153 §4 定义一致，用于声明）**：

| 强度 | 定义 | 机器可证的条件（K-8 判据） |
|---|---|---|
| `strong` | 能抓住该依赖点的漂移并判负 | ≥1 个守卫引用（check id / test id）+ **≥1 个反相 fixture 引用** |
| `medium` | 有守卫，缺完整反相 | ≥1 个守卫引用（无反相要求） |
| `weak` | 有守卫但抓不住该漂移 | ≥1 个守卫引用 + `gap_note`（说明抓不住什么） |
| `none` | 无守卫 | 仅允许 `necessity != "necessary"` 的条目；`necessary` 条目出现 `none` → FAIL |

**「可信面 ≤ 校验面」的机检形式（四条同时成立才放行）**：

1. **声明完整性**：每个契约条目（`host.*` 的 62 条必要依赖 + `own.*` 的 parity 契约）在 `coverage.entries[]` 中**有且仅有一条**声明。**唯一性规则的判定单位 = `subject`**（**同一 `subject` 不得重复声明**；R1 N-7：原句"61 条 / 62 条"重复表述已删除，计数口径统一为 **62**，与 K-9 / §10 O-9 一致），缺声明 → FAIL。**判定键 = §2.4 定义的双键**（R0 F-14）：`subject`（契约 JSON path）+ `audit_ids[]`（`D-nn`）；**62 条必要依赖按 `audit_ids` 的并集覆盖判定**——允许一个 `audit_id` 出现在多个 `subject`（AUDIT-153 §3.3 的聚类本身重叠）**且不因此判为重复**；`subject` 必须解析到契约内存在的路径。
2. **佐证存在性**：`guard` 引用的 check id 必须在 `registry.py` 注册表中存在；test id 必须在 `infra/tests/` 中存在（K-8）。**解析动作在 `checks/dsh_boundary` 内完成**（R0 F-15）——`dsh_contract` 只做数据加载与结构校验，**不得** import registry，否则形成 `registry → checks.dsh_boundary → dsh_contract → registry` 环，ADR §8 的"0 环"结论失效。
3. **强度不越级**：`target == "strong"` 必须有反相 fixture 引用；`target == "none"` 只允许非必要条目。**因此"声明强于佐证"在结构上不可表达** —— 这就是"可信面 MUST NOT 大于校验面"的机检形式（C-6）。
4. **豁免受约束**（R0 BT-R-01）：`contract.allowlist[]` 不参与 `coverage` 判定，但受 K-11 的 `reason`/`since_slice`/棘轮约束——**"契约外硬编码"的唯一豁免通道有护栏**。

> 与 C-21 的关系：C-21 要求该不变量**可机检**且**不产生第二事实源**。本设计的做法是把强度声明放进**契约这一个文件**（而不是让它出现在 REVIEW 记录或独立台账），检查器只读契约与测试/注册表，不写任何权威数据。

### 4.2 逐依赖聚类 → 目标覆盖强度（含当前强度与差距）

> 聚类取自 AUDIT-153 §3.3；「当前」按 §4 覆盖矩阵取值（最保守口径）；「目标」是本设计对 0.81.0 结束后状态的要求。

| # | 依赖聚类（代表 ID） | 当前 | **目标** | 达到目标的手段（切片） | 反相 fixture |
|---|---|---|---|---|---|
| 1 | 包身份与入口契约（D-01/03/04/06/08） | 弱/无 | `strong` | K-2（契约外扫描）+ K-10（files/manifest）+ 包名三方一致判据（V8） | FX-PKG-01/02（`dsh.bundle.patch` 改名；`exports` 断裂） |
| 2 | 补丁层 insert 语义（D-09/D-10） | 弱/强 | `strong` | K-6（4 条不变量）+ `dsh-doctor` S1（V8） | FX-PATCH-01（注入 `- id: <host row>` UPDATE） |
| 3 | 预设交付路径与文件名（D-18/20/35/59） | 中 | `strong` | K-5（hooks 等式）+ S1（渲染/标记）+ 路径存在性 | FX-PATH-01（`.agent-presets` 改名） |
| 4 | 有 schema 的 18 行（D-24~D-29…） | 强 | `strong`（保持） | 既有 28v + 既有反相（`text`→拒绝） | 既有（`test_dsh_compat.py:612` 等）+ FX-ROW-KEY-01 |
| 5 | `customSkillDirs` 通道（D-34/35） | 强 | `strong` | §4.4.3 差分 gate（V5） | FX-CSD-01（同缩进）/ 02（相对路径）/ 03（拼错 token） |
| 6 | `cordis:` 内建前缀与 group 语义（D-38/39） | 弱 | `strong` | §4.4.2（V4） | FX-GROUP-01/02/03 |
| 7 | 护栏的上游 API 面（D-74/75/77） | 强 | `strong`（保持） | 契约化符号名 + 既有 NOT_RUN 降级 | 既有（`:441`）+ FX-API-01（符号缺失 → NOT_RUN） |
| 8 | `DSH_HOME` 语义（D-17/18/71/72） | 弱 | `strong` | §4.4.4 三方差分（V6） | FX-HOME-01（`"   "`）/ 02（尾空格）/ 03（`""`） |
| 9 | warn-only / 永不抛契约（D-23） | 强 | `strong`（保持 + 扩展） | J-1~J-3 不变量测试（契约不可读、契约畸形） | FX-JS-01（契约缺失）/ 02（契约非法 JSON） |
| 10 | 隔离与逃逸守卫（D-53/55/80） | 强 | `strong`（保持） | 既有 28u + `--uninstall` 守卫 | 既有 4 例 |
| 11 | 渲染 token 契约（D-21/48/65） | 强 | `strong` | K-4/K-5 + §4.4.5 未知名扫描 | FX-TOKEN-01（拼错 token）/ 02（未知 token） |
| 12 | 版本投影与清理范围（D-94~D-98） | 中 | `medium` | K-7/K-10（主 check 覆盖缺失 <!> B-9 不在本版修，如实保留 `medium`） | FX-VER-01（persona 版本串漂移） |
| 13 | 看护接线（D-83~D-88/91） | 中 | `strong`（28w/doctor 加入后） | 注册表一一对应（C-14）+ 快照 + **K-11/K-12/K-13**（allowlist 棘轮 / 单一裁决 / 演练基线约束） | FX-WIRE-01（删一段注册 → FAIL）/ FX-ALLOW-01 / FX-VERDICT-01 / FX-REHEARSE-05 |

**多消费者裁决一致性（R0 BT-R-02 的落点）**：`coverage` 块、`dsh_cli_version`、`manifest verified_on` 三个事实在**多个入口可见**（28v / 28u / K-7 / doctor S1~S3），因此新增判据 **K-12** 要求"同一仓库态下 doctor 与 boundary 的裁决必须一致"，并把 `coverage` 的生成点唯一化（`check_dsh_preset_compat()`）；doctor 只**投影**这些结果，不重新推导。

**零校验行（5 行）的目标**：**不是**"变成 `strong`"（我们拿不到它们的 schema），而是"**必须上屏 + 必须使结论降级**"——即 §4.4.1 的目标（`rows_checked==0` → `NOT_RUN`；混合结论必须携带 `coverage` 块并以 `[NOT_RUN]` 行披露）。这是 C-6 的正解：**不能把不可校验的面伪装成已验证**。

### 4.3 「零校验 MUST NOT PASS」的机检形式（C-6 / C-21）

**三层不变式（每层一个独立测试，任一失败即阻断）**：

| 层 | 不变式 | 机检形式 | 落地 |
|---|---|---|---|
| L1 报告级 | 不存在 `rows_checked == 0 ∧ verdict == PASS` 的报告 | 对裁决函数做**组合矩阵测试**：`(compositions, rows_enabled, rows_checked, failures)` 的笛卡尔子集逐点断言 `checked==0 ⇒ verdict ∈ {FAIL, NOT_RUN}` | V3 |
| L2 渲染级 | `emit_check_section()` 在 L1 的不变量成立时**不得**输出 `[PASS]` 行 | **stdout 捕获测试**：构造 `checked==0` 报告 → 捕获输出 → 断言不含 `[PASS]` 且含 `[NOT_RUN]` | V3 |
| L3 披露级 | 混合结论（部分行无 schema）必须把未校验行**上屏** | stdout 捕获测试：构造 `checked==2` + 2 行 `NO_SCHEMA` → 断言输出含 2 行 `[NOT_RUN]` 披露（判据按 `kind` 而非字符串 `"NOT verified"`） | V3 |

**根因修复（G-01④ 的机制面）**：把 `emit_check_section` 的"是否上屏"判据从字符串匹配 `if "NOT verified" in detail`（`dsh_compat.py:1090`）改为**结构化 `kind` 判定**（`kind ∈ UNVERIFIED_KINDS`）。字符串耦合正是"屏幕上看不见 NO_SCHEMA"的机制原因。

### 4.4 缺口修复设计

> 每个缺口：① 根因证据；② 目标判据（**与 loader 真实语义对齐——判据来源逐条标注**）；③ 影响的既有测试与 C-23 处置；④ 新增反相 fixture；⑤ 验收命令。

#### 4.4.1 G-01：`NO_SCHEMA` 行零校验却报 PASS（FIX-315）

**① 根因【实测 E-3】**：`dsh_compat.py:371-376`（无 `Config` ⇒ `NO_SCHEMA` + `continue`，不计 `checked`）→ `:377`（仅此处 `checked += 1`）→ `:1000-1025` 裁决只看 `failures` 与 `rows_enabled`，不看 `rows_checked`；`:1088-1092` PASS 分支只打印含 `"NOT verified"` 的 detail，而 `NO_SCHEMA` 的 message 不含该串 ⇒ 屏幕上完全不可见。

**② 目标判据**：

| 判据 | 内容 | 判据来源 |
|---|---|---|
| G01-a | `rows_checked == 0` ⇒ verdict = `NOT_RUN`（**永不 PASS**） | C-7 三态政策（`dsh_compat.py:75-77` 实测） |
| G01-b | 报告新增结构化 `coverage = {rows_enabled, rows_verified, rows_unverified, unverified_reasons{kind: n}}` | C-6「可信面 ≤ 校验面」的可见化 |
| G01-c | PASS 分支必须逐行打印未校验行（按 `kind` 判定，不按字符串） | G-01④ 实测缺陷 |
| G01-d | PASS reason 措辞必须声明分母：`"verified X of Y enabled row(s) ..."`（不得只说 `"X enabled row(s) validated"`） | G-01③ 实测（`checked: 1` 却 reason 说 "1 enabled row(s) validated"，与 `enabled: 2` 不一致） |
| G01-e | `NO_SCHEMA` 的 detail 文案 MUST NOT 断言"loader 会把 config 原样透传" | **R-15 未验证**（§9 U-2）：改为"this guard cannot validate this row's config (the module exports no Config schema)"——**去掉对 loader 行为的未经证实的断言** |

**③ 既有测试与 C-23 处置**：`test_dsh_compat.py:365 test_no_schema_rows_are_disclosed_not_failed`（E-13）**必须改写**（属 C-23 声明的"预期变红"）。改写为两条：
- `test_no_schema_rows_only_degrades_to_not_run`：`checked=0` + `NO_SCHEMA` → 断言 `verdict == "NOT_RUN"`、`issues == []`、details 含披露行；
- `test_mixed_rows_pass_discloses_the_unverified_ones`：`checked=1` + `PASS` 行 + `NO_SCHEMA` 行 → 断言 `verdict == "PASS"` **且** `coverage.rows_unverified == 1` **且** 屏幕输出含 `[NOT_RUN]` 披露。
**处置裁决**：**改测试**（不是保留双行为）——理由：现行行为正是审计认定的"inventing a green one"，与项目自身的 NOT_RUN 政策（`:75-77`）逻辑冲突（AUDIT-153 §5 G-01「交互」条）；保留双行为等于把缺陷制度化。

**④ 新增反相 fixture**：`FX-NO-SCHEMA-01`（仅一行 `NO_SCHEMA` + `config:{totallyBogusKeyThatMustBeRejected:12345}` → 期望 `NOT_RUN`，**不是** PASS）；`FX-NO-SCHEMA-02`（混合形 → 期望 PASS + 披露行上屏）。fixture 形态：**生成式**（在 temp 目录构造组合文件，见 §5.4），不提交仓库文件。

**⑤ 验收（R0 F-11：命令必须自包含可复现）**：
```
python …/infra/tests/dsh_fixtures.py --emit-fixture FX-NO-SCHEMA-01 --out <tmpdir>     # 待实现（V1 支撑模块）
python …/infra/dsh_compat.py --json <tmpdir>/FX-NO-SCHEMA-01.cordis.yml               # 既有命令
# 期望：verdict=NOT_RUN、rows_checked=0、issues=[]、reason 含 "NOT verified"
python …/verify_workflow.py check-dsh-preset-compat                                   # 既有命令
# 期望：仓库真实组合 PASS 且屏幕出现 5 行 [NOT_RUN] 披露，不出现 "[PASS] … 0"
```
`--emit-fixture` 是本设计对 §5.4"生成式 fixture"的**可复现入口**（同一 ID 在任何机器上生成同一字节），使 V3/V4/V5 的验收命令不再依赖人工构造。

#### 4.4.2 G-02 / G-03：group 行语义双向缺陷（FIX-311）

**① 根因【实测 E-3】**：G-02 = `dsh_compat.py:297` 的 `if (row.group)` 分支只做 `Array.isArray(row.config)` 形态检查后立即递归（`:311-313`），**从不解析/校验 group 自身的 `name`**（group 行也不进 `rows[]`，屏幕上完全无记录）；G-03 = 同分支**先**无条件 `disabledOf(row, ctx)`（`:303-310`），抛错即成 finding 并 `continue` ⇒ 子行永不进入 `walk`（既不报 PASS 也不报 FAIL），而 loader 的 `Entry._disabled` 首行 `if (options.group) return false` 使 **group 自身的 disabled 从不被求值**。

**② 目标判据（与 loader 语义对齐，逐条给来源）**：

| 判据 | 内容 | 判据来源（**不凭注释推断**） |
|---|---|---|
| G02-a | group 行 MUST 在报告中留下记录（`kind: BUILTIN` + `builtin: "group"` + 子行计数） | AUDIT-153 §5 G-02 实测（`planning` 行零记录） |
| G02-b | group 的 `name` MUST 是**已知内建**`cordis:group`；其他值（含 `cordis:` 前缀的其他名、普通包名）→ 新 finding kind `GROUP_NAME_UNRESOLVED`（fail-closed） | loader 对 group 行的解析行为在 AUDIT-153 **仅实测了 `cordis:group`**；其他形态未验证 ⇒ 判据取"不可验证即判负"，并在契约 `host.row_contract.builtin_group_name` 固定 |
| G03-a | group **自身**的 `disabled` MUST NOT 在 group 行处求值（对齐 `Entry._disabled` 首行短路） | AUDIT-153 §5 G-03 引用的 loader 源码行（实测证据） |
| G03-b | group 的 `disabled` 仅在**被子行继承**时求值；抛错 → finding（真实致命：loader 的祖先走查会抛）+ **子行必须全部被披露**（`DISABLED_INHERITED_UNKNOWN`，计 `rows_inherited_unverified`） | 同上（祖先走查不带短路） |
| G03-c | 一个**没有子行**的 group 携带抛错 `disabled` → **不是** finding（没有子行会继承 ⇒ loader 不会因它失败） | G03-a 的推论 + AUDIT-153 G-03「假阳性」判定的精确化 |

**③ 既有测试与 C-23 处置**：`test_dsh_compat.py:754 test_throwing_group_disabled_expression_is_a_finding`（E-13）**必须改写**：其构造含 1 个子行 ⇒ 新行为下**仍是 finding**，但**归因**与**披露**改变（不得再把它写成"group disabled expression threw"了事，必须断言子行被披露 + `rows_inherited_unverified ≥ 1`）。新增 `test_throwing_group_disabled_without_children_is_not_a_finding`（G03-c）。
**处置裁决**：**改测试（归因与披露断言）+ 新增一条**——不是保留双行为；理由：`:755-756` 的注释声称"`disabledOf` is called unguarded by the loader's ancestor walk"，该断言对**祖先**成立、对 **group 自身**不成立（AUDIT-153 G-03 已实测反驳）。

**④ 反相 fixture**：`FX-GROUP-01`（group name 不可解析 `cordis:gruop` → FAIL）；`FX-GROUP-02`（无子行 group + 抛错 disabled → **不 FAIL**）；`FX-GROUP-03`（有子行 group + 抛错 disabled → FAIL + 子行披露）。

**⑤ 验收**：`test_dsh_compat.py` 新用例绿；构造 `FX-GROUP-01` 时 `--json` 的 `issues[0]` 含 `GROUP_NAME_UNRESOLVED`。

#### 4.4.3 G-05：`launch.py` 手写 `customSkillDirs` 扫描对合法 YAML 漏项（FIX-316）

**① 根因【实测 E-2】**：`launch.py:459` 用 `if len(line) - len(line.lstrip()) <= block_indent: break` 作为块结束判据；YAML 允许列表项与键同缩进 ⇒ `<=` 提前 `break` ⇒ 命中 0 条。

**② 目标判据（三层，来自两种不同强度的证据）**：

| 判据 | 内容 | 来源 |
|---|---|---|
| G05-a | 块结束判据改为 `> block_indent` 之外**只在缩进 `< block_indent` 时结束**（即 `<=` → `<`） | YAML block sequence 规范 + AUDIT-153 G-05 的实测反例（同缩进命中 0 条） |
| G05-b | **声明式 shape**：契约 `own.render.custom_skill_dirs_shape`（键缩进、列表风格、条目数 2、条目形态 = 绝对路径或 token）成为**模板侧断言**：模板的该块必须匹配声明的 shape | 把"手写解析器"从"唯一事实源"降级为"shape 的实现" |
| G05-c | **差分 gate**：当探针可用时，探针（用 loader 自己的 `entryListSchema` 解析）报告的 `customSkillDirs` 条目 MUST 等于扫描器结果；不一致 → FAIL | loader 自己的解析器是权威（`dsh-skill-filesystem` 消费的是它） |
| G05-d | 探针不可用（无 node/无安装）时，`verify_preset_loading` 必须把"`customSkillDirs` 由手写扫描器给出"标为**未验证面**（`NOT_RUN` 级披露），且 smoke 的 PASS 必须携带该披露 | C-7 NOT_RUN 政策（不得让手写解析器的结论冒充已验证） |

**③ 既有测试与 C-23**：`test_dsh_adapter.py:368`/`:397`/`:901` 覆盖当前缩进形态，不冲突（保持绿）。新增反相：`FX-CSD-01`（同缩进列表项 → 扫描器命中 2 且与探针一致）。

**④ 验收**：`python -m unittest ... -p "test_dsh_adapter.py"` 全绿；新增 `test_same_indent_custom_skill_dirs_are_found` 在改前**红**、改后**绿**（红绿实证）。

#### 4.4.4 G-06：`DSH_HOME` 空白处理的**三方分歧**（FIX-316）

**① 根因【实测 E-2/§5 G-06】**：`lib/index.js:103` `trim()`；`launch.py:115-118` 只判 `if env:`（`"   "` 为真 → 落字面空白路径）；上游 `dsh-home-paths` 行为见 case 表（三者已实测分歧）。

**② 目标判据（不硬编码"我们的策略"，而以**差分一致性**为不变式）**：

| 判据 | 内容 | 来源 |
|---|---|---|
| G06-a | **写入侧**语义进契约：`host.env.write_side.blank_policy = "trimmed-empty-means-unset"`、`...trim_policy = "verbatim-then-platform-resolve"`、`...fallback = "<home>/.dsh"`、`...tilde_expansion = ["~","~/","~\\"]` | AUDIT-153 G-06 **实测 case 表**（`""` / `"   "` / `"\t"` → 上游回落默认；`"C:/tmp/x "` → 上游保留尾空格；`"~"`/`"~/x"` 三者一致） |
| G06-b | **写入侧三实现**（`lib/index.js`、`launch.py`、`dsh_doctor` 的记录路径）在同一 case 表上 MUST 与**上游实现的实测值**一致 | 差分 gate 的权威 = 安装态 `@deepseek-ai/dsh-home-paths`（不复制其代码，只比对结果）。**R0 F-6：不得把 `dsh_compat` 的读取方纳入此 gate** |
| G06-b' | **探测侧保持既有安全属性（R0 F-6）**：契约 `host.env.probe_side = {require_explicit: true, no_fallback: true}` 与 `dsh_compat.py:553-563` 逐字对齐；`DSH_HOME` 未显式设置时 MUST **不读** `~/.dsh`（`_profile_planes` 返回 `[]`） | `dsh_compat.py:553-563` 自述 + `test_dsh_compat.py:245`「未设不猜」既有固化；**差分 gate 的"与上游一致"不适用于探测侧**（上游回落默认，guard 刻意不回落）——否则会改掉 guard 的安全属性并扩大真实环境探测面，与 ADR §7 安全行、C-19/M7.7 冲突 |
| G06-c | 硬禁止：`DSH_HOME` 为纯空白时，任何实现**不得**产出含字面空白的路径（`launch.py` 今天会产出 `"   \.agent-presets\governance"`） | 实测缺陷（AUDIT-153 G-06 逐 case） |
| G06-d | 差分 gate 在无 node/无安装时 → `NOT_RUN`（绝不 PASS），并在 doctor S3 输出 `NOT_RUN(no-upstream-impl)` | C-7 |

**③ 既有测试与 C-23**：`test_dsh_compat.py:245`（未设不猜 `~/.dsh`）与 `test_dsh_adapter.py:782/806`（decoy/isolated home）**保持绿，并被强化为反相断言**（探测侧：未设 `DSH_HOME` ⇒ 不得读 `~/.dsh`，G06-b'）；新增 live-gated **写入侧**差分测试 + 离线 case 表测试（对三分支的**期望值表**来自 G-06 实测）。

**④ 验收**：写入侧 8 例 case 表全一致（含上游对拍）；探测侧反相测试绿；`launch.py` 不再产出字面空白路径。

#### 4.4.5 G-07：`leftovers` 守卫对拼错 token 无效（FIX-316）

**① 根因【实测 E-1/E-2】**：`lib/index.js:161` 与 `launch.py:153` 都只在**已知 3 个 token** 集合里检查残留。

**② 目标判据**：

| 判据 | 内容 | 来源 |
|---|---|---|
| G07-a | 渲染后扫描 `__[A-Za-z0-9_]+__`（覆盖混合大小写），**任何**命中即视为未解析残留学 | AUDIT-153 G-07 实测（`__Governance_Repo_Root__` 绕过 `[A-Z0-9_]+` 正则） |
| G07-b | 模板侧（编辑期）判据：模板出现的 `__…__` 集合 == 契约 token 集合（K-4）——把"拼错"前移到模板编辑时 | REQ-147 单一事实源 |
| G07-c | JS 侧行为保持 warn-only：命中 → `leftovers` 非空 → `ensurePreset` 已有的"跳过 + warn"逻辑生效（`:209-213`） | J-2 |
| G07-d | Python 侧：`render_composition()` 返回 `""`（既有契约）并把未解析串加入诊断 | E-2 `:153` |

**③ 既有测试与 C-23**：`test_dsh_adapter.py:170 test_template_uses_only_known_tokens` 保持绿（它已覆盖全大写形态），新增混合大小写与未知 token 反相。

**④ 验收**：`FX-TOKEN-01`（`__GOVERNANCE_SKILLS_ROOTS__`）/ `FX-TOKEN-02`（`__Governance_Repo_Root__`）→ 两渲染器都报非空 leftovers，且 `ensurePreset` 跳过（不写坏预设）。

#### 4.4.6 G-10：`UnicodeDecodeError` 穿出公共入口（FIX-316）

**① 根因【实测 E-2】**：`launch.py:598`（读组合）与 `:146`（读模板）无 `errors=` 兜底；同文件 `:652`/`:819` 有 ⇒ 同文件口径不一致；非 UTF-8 输入使 `UnicodeDecodeError` 未捕获穿出 `main()`（exit 1 + 栈）。

**② 目标判据**：

| 判据 | 内容 | 来源 |
|---|---|---|
| G10-a | 读**会被当作内容消费**的文件（模板、组合）不得用 `errors="replace"`（会把 mojibake 写进预设/结论），而 MUST 捕获 `UnicodeDecodeError` → 结构化失败 | P-7（避免损坏用户数据）+ 同文件口径统一的证据 |
| G10-b | 公共入口（`main()` / CLI）不得泄漏栈：失败必须是"可行动诊断 + 稳定退出码" | AUDIT-153 G-10 实测（今天 exit 1 + 未捕获栈） |
| G10-c | `verify_preset_loading` 对非法 UTF-8 组合 → `verdict: FAIL` + 明确 issue（该文件无法被验证）；**不得**静默跳过为 PASS | C-6 |
| G10-d | 上游调用点（`verify_workflow.py` 28u）不得因该异常中断 `check-governance` 引擎 | CODE R0 F8（release-checklist:119） |

**③ 既有测试与 C-23**：新增 `test_non_utf8_composition_is_a_structured_failure`（三入口：`render_composition` / `verify_preset_loading` / `main(["--install"])`）——断言无栈、退出码稳定、消息含文件名与偏移量。
**切片提示**：G10-d 属"引擎不中断"面，与 §4.5 的 `check-governance` 集成验证同片（V8）。

#### 4.4.7 G-11 / G-12：注释版本引用失真与 `verified_on` 失真（C-20）

**① 根因【实测 E-12/§5 G-11/G-12】**：`cordis.patch.yml:30` 与 `lib/index.js:92-93` 引用 `installed dsh 0.1.5-rc.2`（实测为 `0.1.5-rc.1`）；`adapter-manifest.json:75-76` 的 `verified_on: 2026-07-08` + `0.1.0-rc.6` 已过期 67 天。

**② 目标判据**：

| 判据 | 内容 |
|---|---|
| G11-a | 代码/注释中的 dsh 版本字面量**归零**；引用改为"见契约 `evidence.*`"（文字引用不算事实源时也必须指向唯一事实源） |
| G12-a | `adapter-manifest.json` 的 `runtime_e2e.verified_on` 与证据版本 MUST 与契约 `evidence.*` 一致（K-7） |
| G12-b | `now - verified_on > ttl_days` → FAIL（"runtime-verified 声明过期"，C-20） |
| G12-c | 刷新只能由 `dsh-doctor --record-evidence` 在**真实平面**上执行（可审计的 `git diff`） |

**③ C-23**：无既有测试固化该行为（`test_dsh_adapter.py` 未断言版本字面量）⇒ 纯新增。
**④ 验收**：K-7 判据 + 全仓 grep 无 `0.1.5-rc.2` / `0.1.0-rc.6` 失真字面量。

### 4.5 未纳入 0.81.0 的缺口（如实列出，不做隐瞒）

| 缺口 | 处置 | 理由 |
|---|---|---|
| **G-04**（`lib/index.js` catch 清理可退化为进程 CWD） | **列为候选切片 V10**（1 行级修复：清理目标改为显式 staging 变量，对齐 `launch.py:261-266`）+ 反相 fixture | 涉及潜在**文件系统副作用**（误删 CWD 下同名目录），机制已实测存在、触发条件未复现（AUDIT-153 判"部分证实"）；是否纳入 0.81.0 交 M-0 裁决——本设计给出最小方案与判据，不擅自扩范围 |
| **G-09**（`spg-dsh-compat-*` 临时目录残留） | 弱化：S3 stage 只读计数披露（D-79），**不修清理逻辑** | 当前不可复现（陈旧版本残留）；强杀兜底需要独立设计（进程外清理） |
| **G-13**（NO_SCHEMA 行在上游侧其实可校验） | 不修，转 §9 U-2 验证计划 | 属"上游约定"面；R-15 未验证，不能据此设计 |
| **G-14 / R-05 / R-12**（`[SKEW]` 告警有效性） | 不修；由 S3 stage 输出 `other_planes` 供将来验证 | 本机单平面，分支未被执行（不可验证） |
| **G-15**（`ensurePreset` 无并发保护） | 声明化（D-22）；不修 | 加锁需要跨进程机制，超本版范围；风险如实登记（§8.2） |
| **G-16**（`--smoke` 忽略 `--dry-run`） | 文档化（S6 remediation 说明）；不修 | 设计取舍，AUDIT-153 判"仅记录" |
| **G-17**（witness 假 FAIL） | 弱化（D-54：去 size/mtime + 双采样） | 见 §3.3 第 11 行 |
| **G-18**（`FINDING_KINDS` 无守卫） | **纳入 V4 的邻近判据**：新增 `UNVERIFIED_KINDS` 常量 + 一个断言"每个 kind 恰好属于 {FINDING, UNVERIFIED, DISCLOSURE} 之一"的自检 | 成本极低且直接服务 K-8/L3 |
| `dsh_compat.py` 归属迁移 | **不修，需独立 DEC**（E-16） | 见 §9 U-6 |

### 4.6 三态语义一致性（C-7）

| 结论 | 语义 | 退出码 / gate 计分 | 屏幕表现 |
|---|---|---|---|
| `FAIL` | 已证实被拒绝/不可用 | `--fail-on-issues` → 1；引擎计入 issues | `[FAIL]` + 逐条 finding |
| `NOT_RUN` | **未验证**（无 node / 无安装 / 文件不可读 / 全部行无 schema / 契约不可读 / 环境缺失导致的门控跳过） | **退出 0，不计 gate issue**（`dsh_compat.py:1139-1144` 既有政策） | `[NOT_RUN]` + 原因 + remediation |
| `PASS` | 至少 1 条 enabled 行被真实校验，且未校验面**已披露** | 0 | `[PASS]` + `coverage` 分母 + 未校验行的 `[NOT_RUN]` 披露行 |

**新增要求**：node-gated 测试的 skip（B-8：9 处 `skipTest`）MUST 按同一政策披露——落点 = 契约 `coverage.entries[].requires` + `dsh-doctor --stage S6` 的 `unverified_due_to_env[]`（§3.3 第 15 行）。

---

## 5. (D) 依赖边界可调测性 —— REQ-149 的解

### 5.1 单一诊断入口规格（C-16）

**命令**：`python skills/software-project-governance/infra/verify_workflow.py dsh-doctor [options]`（**待实现**，切片 V8；注册为 registry 命令键 `dsh-doctor`）。

| 选项 | 作用 |
|---|---|
| `--json` | 机器可读报告（默认可读文本） |
| `--stage S0..S7`（可重复） | 只跑指定阶段 |
| `--offline` | 禁止一切子进程/宿主探测（全部相关阶段 → `NOT_RUN`，**不 FAIL**） |
| `--record-evidence` | 唯一契约证据写入路径（需真实平面；隔离 DSH_HOME） |
| `--rehearse <host-facts.json> [--against <baseline.json>]` | 离线升级演练（§5.5） |
| `--allow-host-probe` | 允许 S5 执行宿主组合探测（**要求先满足 R1 三选一**：隔离/备份+校验/用户授权），否则拒绝（exit 2） |

**命令名候选与排除**：

| 候选 | 优点 | 排除理由 |
|---|---|---|
| **`dsh-doctor`（采用）** | 与既有 `check-dsh-*`（gate 判据）区分：doctor 是**诊断入口**，语义"分阶段体检 + 可行动建议"；命令名短、可预测 | — |
| 扩展 `check-dsh-preset-compat` | 无新命令 | 把 gate 判据与诊断编排混成一个入口 ⇒ 退出码语义冲突（gate 的 0/1 与诊断的 0/1/2 REFUSED 无法共存）；且它今天不含阶段分层（AUDIT-153 §6.2） |
| 新建 `check-dsh` 大命令 | 名字统一 | 与既有 28u/28v 的注册面冲突（C-14 一一对应），且"check"命名会诱导用户把它当 gate 用 |

**输出契约（每阶段一条，固定字段）**：

```json
{
  "schema_version": 1,
  "command": "dsh-doctor",
  "generated_at": "<ISO8601>",
  "host": {"dsh_version": "...", "plane": "...", "node_version": "..."},
  "verdict": "PASS | FAIL | NOT_RUN",
  "exit_code": 0,
  "stages": [
    {"stage": "S2", "title": "row/config schema",
     "verdict": "PASS",
     "credible_face": {"rows_enabled": 23, "rows_verified": 18, "rows_unverified": 5,
                       "unverified_reasons": {"NO_SCHEMA": 5}},
     "evidence": [{"kind": "check|file|probe|test", "ref": "...", "detail": "..."}],
     "remediation": [{"action": "...", "command": "...", "expected": "..."}]}
  ]
}
```

**退出码**：`0` = 无 FAIL（含全 `NOT_RUN`）；`1` = 至少一个阶段 FAIL；`2` = 拒绝执行（隔离守卫/用法错误/未授权宿主探测）。与 `launch.py` 的 `SMOKE_EXIT_{PASS,FAIL,REFUSED}=0,1,2` 语义一致（D-53）。

**降级设计（诊断入口自身失败，BT-2 的落地）**：
- 每个阶段**独立 try/except**；阶段内异常 → 该阶段 `verdict: "NOT_RUN"`, `reason: "stage crashed: <TypeError: msg>"`, `stage_error: true`；**其余阶段继续**；报告始终含 8 条阶段记录。
- doctor 本体不得 import `verify_workflow`（避免循环依赖，§8.3）；对 `dsh_compat` / `launch.py` 一律**惰性 import + 子进程隔离**，使"护栏/渲染器已损坏"这一最需要诊断的场景仍可运行。**反向同理**：`verify_workflow.py` 对 `dsh_doctor` MUST 函数内惰性 import（R6 `import_count` 保持 196，E-20）。
- `--selftest`（V8 交付）：用合成输入逐阶段注入异常，断言"任一阶段崩溃不影响其余阶段输出 + 顶层 verdict 不因崩溃变绿"，作为 doctor 自身的反相 gate。

**单一裁决纪律（R0 BT-R-02 的落地）**：
- doctor 的 **S3/S7 MUST 消费 K-7 的结果**（`check-dsh-boundary` 的版本证据判据）而非自行重算 `dsh_cli_version` / `manifest verified_on` / TTL；`evidence[]` 里记 `kind: "check", ref: "28w/K-7"`。
- **`coverage` 块只有一个生成点**（`check_dsh_preset_compat()`）；doctor S2 只**投影**它（`kind: "check", ref: "28v"`），不重算、不改写。
- **K-12**：同一仓库态下 `dsh-doctor --json` 顶层 `verdict` 与 `check-dsh-boundary --fail-on-issues` 退出码 MUST 一致；不一致 → doctor 自身 FAIL（含反相 fixture `FX-VERDICT-01`）。

### 5.2 阶段规格（S0→S7，对齐 AUDIT-153 §6.1 的定界链）

| 阶段 | 名称 | 今天的状态（§6.1） | 本设计的判定输入 | verdict 判据 | 典型 remediation |
|---|---|---|---|---|---|
| **S0** | 现象/输入面 | 纯手工 | 传入的用户现象描述（可选）、`DSH_HOME` 解析结果、`node`/`dsh` 存在性、包根与版本 | 恒 `NOT_RUN`-by-design（记录输入事实）；若 `DSH_HOME` 无法解析 → FAIL | 设置 `DSH_HOME` 或检查 `~/.dsh` |
| **S1** | 交付面（预设是否渲染） | 纯手工 | 预设目录存在性、`.dsh-bundle-version` 内容 vs 包版本、`skill-root.txt` 内容、两渲染器输出哈希（**隔离 home 渲染**，不读真实 home 内容） | 目录缺失 / 版本标记不等 → FAIL；标记等 → PASS | `python adapters/dsh/launch.py --sync` |
| **S2** | 行/schema 面 | 自动化（28v） | `check_dsh_preset_compat()` + `coverage` 块 | FAIL / NOT_RUN / PASS（§4.6） | 按 finding 改行 config；`NO_SCHEMA` → 手工核对上游插件文档 |
| **S3** | 平面/安装面 | 自动化（披露） | **消费 28w 的 K-7 结果**（证据版本/TTL 一致性，不重算）+ 平面发现、oracle 版本、`other_planes`、`compat_range`、临时残留计数（**只读**） | 版本越界 → FAIL；证据过期/多平面偏斜 → 披露；无法发现平面 → NOT_RUN | `dsh-doctor --record-evidence`；检查 `DSH_HOME` |
| **S4** | 渲染/parity 面 | 部分自动化 | 模板→渲染（JS 与 Python 两实现）sha256 比对、leftover 扫描、`customSkillDirs` 扫描器 ↔ 探针差分、行尾归一化 | 任一不一致 → FAIL | 修模板/契约；`git pull` 后 `--sync` |
| **S5** | 宿主 entry 面 | **今天无路径** | 默认 `NOT_RUN(requires --allow-host-probe)`；授权后：`dsh --profile <p> --dump-config` 前后 diff（DEC-188 ② 机检判据） | 未授权 = NOT_RUN；授权后 entry 列表变化超"恰多一行" → FAIL | 用户授权；或按 §5.3 T-2 处置 |
| **S6** | skill 目录/手势面 | 自动化（smoke） | `run_isolated_smoke()`（结构化）：catalog root、gesture shim、frontmatter 契约、`customSkillDirs` 可解析性；`unverified_due_to_env[]` | smoke FAIL → FAIL；环境缺失导致未验证 → NOT_RUN + 清单 | `--sync` + 重启 dsh；检查 `skill-shims/` |
| **S7** | hook/自升级面 | 纯手工 | `.git/hooks/*` 版本行 vs 源 hooks 版本、`skill-root.txt` 可达性、投影一致性（`dsh-persona-version`/`dsh-agents-bootstrap-version`）、**28w/K-7 + K-5 的结果投影**（不重算） | hooks 陈旧/缺失 → WARN（advisory）；hook 路径表达式漂移 → FAIL | 复制 hooks（一次性命令） |

**关键性质**：S1/S3/S5/S7 是 AUDIT-153 判定的"今天手工"三段（S0→S1、S4、S5、S7）中可自动化的部分；**S4 今天无路径**（"PASS 但用户仍失败"=无法定界）由 S4 的 parity/差分判据补上；**S5 仍不可离线**（T-2），以"授权门 + NOT_RUN 披露"落地（R1 三选一）。

### 5.3 离线/CI 可复现性：T-1~T-10 逐条处置（C-17）

| # | AUDIT-153 的"必须有真机"面 | **处置** | 具体形式 | 判据 |
|---|---|---|---|---|
| T-1 | `dsh plugin add/remove` 写 profile `bundles` | **显式 NOT_RUN + 授权可选项 + fixture 冻结** | 默认 S5 = `NOT_RUN(requires --allow-host-probe)`；授权运行时把"前后 `bundles` 列表"记录为 fixture（含哈希），供后续 diff | 记录存在且含 before/after；未授权时输出 NOT_RUN 且不计 gate issue |
| T-2 | 组合后 entry 列表与安装前等价（DEC-187 I-1 机检） | **显式 NOT_RUN + 授权可选项**（本设计不承诺离线化） | 同 T-1；授权后 diff 判据 = DEC-188 ②（`profile-contract.md:256`）：既有行零变化 + 恰多一行且只命名本包 | 同上；未验证面在 S5 输出 NOT_RUN 原文 |
| T-3 | 设置页 roster（`dsh-preset-roster` claim） | **显式 NOT_RUN 披露** | S1 只证"预设目录与文件已写入"；报表明确"设置页 UI 未验证" | S1 PASS 文本必须带"UI 未验证"限定（措辞纪律） |
| T-4 | 会话内 skill 目录真的被注册 | **离线代理 + NOT_RUN 披露** | S6 的 catalog 解析（今天已有）+ 明确"resolution-level only" | S6 PASS 文本含限定语 |
| T-5 | `/governance` 手势真的可触发 | 同 T-4 | S6 的 gesture shim frontmatter 校验 | 同上 |
| T-6 | `{{model}}`/`{{cwd}}` 真被宿主插值 | **离线代理 + NOT_RUN 披露** | S4 断言"渲染产物含未替换的 `{{model}}`/`{{cwd}}` 占位符"（**离线可证**）；插值行为未验证 | S4 输出 `interpolation: unverified (R-08)` |
| T-7 | 宿主平面注册表（`shell-env`/`subagents`/`web`） | **显式 NOT_RUN + 契约带未验证标注** | 契约 `host.host_plane_registries`（`verification: unverified (R-09)`）；S5 授权后读宿主组合 | 未验证标注必须出现在契约与 doctor 报告中 |
| T-8 | npm registry 安装形态 | **离线化（新增 `npm pack` 面检查）** | 新增判据：在**临时目录**执行 `npm pack --dry-run --json`，断言打包清单 ⊇ 契约声明的必发集合（`lib/`、`agent-presets/`、契约文件、`adapters/dsh/`、`cordis.patch.yml`） | 清单缺项 → FAIL；命令不可用（无 npm）→ NOT_RUN（C-7）。**假设**：`--dry-run` 不在仓库与用户目录产生写入（§9 U-3） |
| T-9 | 宿主在窗口内写 `settings.yaml` → witness 假 FAIL | **离线化（去 size/mtime + 双采样）** | §3.3 第 11 行（D-54） | 反相：触碰 `settings.yaml` → 不 FAIL |
| T-10 | `dsh-agent-router` 等持续写入影响 witness | **已离线化的保持** | 既有设计已排除宿主自有子树（`launch.py:421-427` 自述） | 反相：宿主子树变化 → 不 FAIL（既有 `:1000` 用例扩展） |

### 5.4 fixture 策略

| 类型 | 形式 | 位置 | 理由 |
|---|---|---|---|
| **生成式 fixture（默认，占多数）** | 测试期在 temp 目录构造组合文本（在既有的 `_scratch()` 模式上扩展），用"基础组合 + 具名突变"生成；并暴露 **`python infra/tests/dsh_fixtures.py --emit-fixture <ID> --out <dir>`**（R0 F-11：同一 ID 在任何机器生成同一字节 ⇒ 验收命令自包含可复现） | 无提交文件（新增支撑模块 `infra/tests/dsh_fixtures.py`） | ① 提交式 fixture 会持续累积；② 突变可复用为 doctor 的 `--selftest` 输入；③ D4（不做冗余修改） |
| **记录式 fixture（少量）** | `host-facts-<dsh-version>.json`：宿主事实快照（见 §5.5），含 `captured_at` / `dsh_version` / `synthetic`（bool）/ `provenance`（记录命令 + 平面） | **`adapters/dsh/fixtures/`**（R0 F-12 修正：不再放 `skills/**`） | ① `adapters/` 已是 `manifest.json` 的 dir 条目（canonical 自动覆盖，E-8）且已在 `files` 白名单内；② **发布面如实声明**：该 fixture **随 npm 包发布**——这是**有意**的（用户无需装 dsh 即可跑 `--rehearse` 离线演练），代价用**体积预算 ≤64 KiB/文件、≤3 个版本文件**约束，由 K-10 的 manifest 条目 + 体积断言守护；③ 与 `host.*` 宿主事实语义同层（R0 F-12 的建议选项） |
| **schema 冻结** | `host-facts` 内嵌 per-row `{module, resolved, config_export, accepted_keys[], required_keys[], probe_result}` | 同上 | 把"某版本接受什么"冻结成可 diff 的事实；**不复制 schema 代码**（只记录键集与接受/拒绝结果）；**只能由 `--record-evidence` 写**（§2.4 的记录式子块，禁止人工誊抄） |
| **"真实升级前后" fixture 对** | `host-facts-<v_before>.json` + `host-facts-<v_after>.json`；两者 MUST 满足 `captured_at` 严格递增、`dsh_version` 不同（K-13）；无法获得真实 after 时只能使用 **`synthetic: true`** 的突变 fixture | 同上 | 见 §5.5；**诚实边界**：v_before 无法追溯制造，只能由 V8 落地时在**当时**的平面上首次记录；合成突变必须在报告里带 `synthetic: true` 标记，**不得**与真实记录混同（R0 BT-R-03） |

**fixture 生命周期约束（R0 BT-R-03）**：每个 `host-facts-*.json` 的 `captured_at` 参与 TTL 判据（与 `evidence.verified_on` 同阈值），过期 → S3 输出 `[EVIDENCE-STALE]` 并给 remediation；`--rehearse` 的 no-op（同版本）与时间倒序一律 **FAIL**（K-13）。

### 5.5 升级演练（upgrade rehearsal）机制设计

**目标**（用户要求 ④ 的机制面）：下一次 dsh 升级的影响，能在**我方 CI** 里先看到。

```
[A] 记录：dsh-doctor --record-evidence --out adapters/dsh/fixtures/host-facts-<v>.json
      ├─ 在隔离 DSH_HOME 下探测真实平面（不读真实 home 内容；M7.7 (a) 隔离）
      ├─ 内容 = {dsh_version, plane, oracle_packages, rows[]: {module, resolved, config_export,
      │           accepted_keys, required_keys, probe_result}, api_symbols[], captured_at,
      │           synthetic: false, provenance: "<命令 + 平面>"}
      └─ 同时写契约 evidence.*（唯一写入路径）

[B] 差分（CI，离线）：dsh-doctor --rehearse <new>.json --against <baseline>.json
      ├─ 前置守卫（K-13，R0 BT-R-03）：
      │   ├─ new.dsh_version == baseline.dsh_version     → FAIL("rehearsal no-op")
      │   ├─ new.captured_at <= baseline.captured_at     → FAIL("baseline/candidate time order")
      │   └─ 任一 fixture captured_at 超 TTL             → [EVIDENCE-STALE]（并按阈值 FAIL/advisory）
      ├─ 契约面漂移：包缺失 / 模块不可解析 / API 符号缺失 → FAIL(演练)
      ├─ 行为面漂移：我方 config 由 accept → reject；required_keys 新增 → FAIL(演练)
      ├─ 声明面漂移：evidence.verified_on / dsh_version 与 fixture 不一致 → [EVIDENCE-STALE]
      ├─ 条目级 synthetic 标记：synthetic: true 的条目在报告里逐条标注，且**不得**用于判定"升级安全"
      └─ 输出"我方将面临什么"清单 + remediation

[C] 合成突变自检（离线，证明演练有效）：用 dsh_fixtures 生成的突变 fixture 跑 [B]
      ├─ 删除一个包 / 移除一个 API 符号 / 给某行加一个 required key / 把某行 probe 改 reject
      ├─ 同版本 no-op（FX-REHEARSE-05）/ 时间倒序（FX-BASE-01）→ 必须 FAIL
      └─ 每个突变 MUST 触发对应的演练 FAIL —— 这是"演练机制自身"的反相 gate
```

**诚实边界（必须写清）**：
1. 演练回放的是**记录态事实**，不是真实 schema ⇒ 能抓**契约面/接口面漂移**（RISK-050 的主要成因面：包名、API 符号、config 键接受性），**不能**替代真机安装（T-1/T-2）。
2. "下一次升级在 CI 先看到"的**前提**是有人在有新版 dsh 的机器上跑一次 `[A]`（真实环境，需按 R1 隔离重定向 `DSH_HOME`；这正是 `--record-evidence` 的内建隔离）。**没有这一步就没有 before/after 对**——设计不声称自动化该前提。
3. fixture 陈旧（长期未重录）会制造虚假安全感 ⇒ 由 `[B]` 的 TTL 判据 + `[EVIDENCE-STALE]` + S3 的 remediation 对抗（BT-5/R-5）。
4. **no-op 演练不得绿（R0 BT-R-03）**：同版本 + 时间倒序一律 FAIL（K-13）；`synthetic: true` 的条目在报告里逐条标注，且**不得**用于判定"升级安全"——它只能证明"演练机制有效"，不能证明"宿主升级无影响"。

### 5.6 负相 fixture 清单（对齐 AUDIT-153 §6.4 缺口表）

| Fixture ID | 对齐缺口 | 突变 | 期望 |
|---|---|---|---|
| FX-NO-SCHEMA-01 | §6.4「无 NO_SCHEMA 负相」/ G-01 | 仅一行 `NO_SCHEMA` + 非法 config | `NOT_RUN`（**不是** PASS），`rows_checked: 0` |
| FX-NO-SCHEMA-02 | 同上 | 1 行 PASS + 1 行 `NO_SCHEMA` | `PASS` + `coverage.rows_unverified: 1` + 屏幕 `[NOT_RUN]` 披露行 |
| FX-GROUP-01 | §6.4「无 group name 不可解析负相」/ G-02 | group `name: cordis:gruop` | `FAIL` + `GROUP_NAME_UNRESOLVED` |
| FX-GROUP-02 | G-03 精确化 | 无子行 group + 抛错 `disabled` | **不 FAIL**（无继承者） |
| FX-GROUP-03 | G-03 | 有子行 group + 抛错 `disabled` | `FAIL` + 子行披露（`rows_inherited_unverified ≥ 1`） |
| FX-CR-01 | §6.4「无 `\r` 注入」/ D-66 | 模板注入 1 个孤立 `\r` | 两渲染器 sha256 全等；不等则 FAIL |
| FX-TOKEN-01/02 | §6.4「无拼错 token」/ G-07 | `__GOVERNANCE_SKILLS_ROOTS__` / `__Governance_Repo_Root__` | 两渲染器 leftovers 非空；`ensurePreset` 跳过 |
| FX-CSD-01 | §6.4「无同缩进 customSkillDirs」/ G-05 | 列表项与键同缩进 | 扫描器命中 2 且与探针一致 |
| FX-CSD-02 | 同上邻域 | 相对路径 entry | 明确 issue（FIX-290 类） |
| FX-UTF8-01 | §6.4「无非 UTF-8」/ G-10 | 组合含 `0xFF` | 结构化失败（无栈）+ 稳定退出码 |
| FX-HOME-01/02/03 | §6.4「无 `DSH_HOME` 空白/尾空格」/ G-06 | `"   "` / `"C:/tmp/x "` / `""` | 三方一致（含上游） |
| FX-JS-01/02/03 | 新（契约面） | 契约缺失 / 契约非法 JSON / 契约缺失下的 `renderComposition` 直调（R0 F-3） | JS：warn + 跳过同步 + 不抛（`renderComposition` 返回 `leftovers` 覆盖全部 token）；Python：结构化错误（`ContractUnreadable`/`ContractMalformed`）+ 非 0 |
| FX-BASEURL-01 | 新（R0 F-10） | `!!js` 表达式的 `baseUrl` 非 file-url 形态 | 明确 finding（`baseUrl` 形态语义固定为 `$host.row_contract.loader_scope_baseurl_shape`） |
| FX-PATCH-01 | §6.4 邻域 / D-10 | patch 注入 `- id: <host row>` UPDATE | FAIL（K-6） |
| FX-ALLOW-01 | 新（R0 BT-R-01 / K-11） | allowlist 新增一条无 `reason` 的条目；或条数超预算 | FAIL（`allowlist entry without reason` / `allowlist grew`） |
| FX-VERDICT-01 | 新（R0 BT-R-02 / K-12） | 人为令 doctor 与 boundary 对同一事实结论不同（测试内注入） | doctor 自身 FAIL（`verdict disagreement`） |
| FX-REHEARSE-01..04 | §5.5 [C] | 删包 / 删 API 符号 / 加 required key / probe→reject | 演练逐项 FAIL |
| FX-REHEARSE-05 | 新（R0 BT-R-03 / K-13） | `new.dsh_version == baseline.dsh_version`（no-op 演练） | **FAIL**（"rehearsal no-op"），不得输出"无漂移 = 升级安全" |
| FX-BASE-01 | 新（R0 BT-R-03 / K-13） | `new.captured_at <= baseline.captured_at`；或 baseline 超 TTL | FAIL（时间序）/ `[EVIDENCE-STALE]`（TTL） |
| FX-WITNESS-01 | §6.4「无 settings.yaml 竞态负相」/ G-17 | 触碰 `settings.yaml` | **不** FAIL（D-54 弱化后） |
| FX-RESIDUE-01 | §6.4「无探针强杀负相」/ G-09 | 预置一个 `spg-dsh-compat-*` | S3 只读计数披露（advisory，不删） |

---

## 6. (E) 实施切片计划（供 M-0 版本范围裁决）

### 6.1 切片清单

> 每片 = 可独立审查的垂直切片。**「依赖前序」**列已包含文件冲突导致的**串行约束**（DSH 无 `isolation: worktree`，同文件并发修改 MUST 串行化）。

| 片 | 目标（一句话） | 触碰文件 | 依赖前序 | 验收判据 | 建议审查者 | 承接 |
|---|---|---|---|---|---|---|
| **V1** | 契约数据层落地：新增契约文件（**只含可核静态事实**）+ 访问器 + 自校验单元测试 + fixture 生成入口 + manifest 声明 | **新增** `adapters/dsh/host-contract.json`、`skills/software-project-governance/infra/dsh_contract.py`、`infra/tests/test_dsh_contract.py`、`infra/tests/dsh_fixtures.py`（含 `--emit-fixture`）；改 `core/manifest.json`（`canonical_product_artifacts` +1 条） | 无 | ① `test_dsh_contract.py` 绿（含 K-1/K-3/K-4/K-9 的单元级判据）；② **R0 F-5**：`host.rows[].{schema_export,required_keys,accepted_keys}` 在 V1 允许为空且标 `source: recorded` + `recorded: false`，K-1 只要求字段存在、不要求非空（**禁止人工誊抄**）；③ `check-manifest-consistency --fail-on-issues` PASSED；④ `cleanup.py --dry-run` 干净；⑤ 反相：模板加一行未登记 → 自校验 FAIL；⑥ `dsh_fixtures.py --emit-fixture FX-NO-SCHEMA-01 --out <tmp>` 两次输出字节相同 | Design Reviewer（契约 schema）+ Code Reviewer | REQ-147 |
| **V2** | 消费方改为从契约读取（**行为保持重构**）+ **K-2 文本扫描前置落地** | 改 `adapters/dsh/launch.py`、`infra/dsh_compat.py`、`lib/index.js`（JS 侧 = 模块级 memoized `contractTokens()`，两个函数内读取点，**顶层零 I/O**，R0 F-3）；**不改** hooks 与模板；新增 K-2 的**纯文本/正则扫描**（可作为 `test_dsh_contract.py` 的一个用例，不依赖新模块） | V1 | ① `test_dsh_adapter.py` + `test_dsh_compat.py` **Ran 89, OK**；② 三路径渲染 sha256 不变（`00e0d330…`）——**该验收只证"输出等价"，不证"单一事实源"**（R0 BT-R-04 的措辞澄清）；③ `check-dsh-preset-compat` PASSED、`check-dsh-preset-smoke` PASSED；④ **per-field 突变矩阵**（R0 BT-R-04）：至少对 `own.render.tokens` / `own.preset.id` / `own.preset.version_marker` / `host.rows[]` 四项各一条突变，断言消费者输出随之改变；⑤ **不可从输出观测的字段**（`own.package.engines_node`、`own.patch.shape_invariants`、`coverage.*`）由 K-2/K-10 覆盖，明确**不**纳入突变矩阵；⑥ K-2 文本扫描绿（无契约外字面量）；⑦ `FX-JS-03`（契约缺失时 `renderComposition` 不抛 + `leftovers` 非空）绿 | Code Reviewer（宿主行 + parity 为本版最高风险面）+ Design Reviewer | REQ-147 |
| **V3** | 零校验不得 PASS（G-01 / **FIX-315**） | 改 `infra/dsh_compat.py`（裁决 + `coverage` + 上屏判据）、`infra/tests/test_dsh_compat.py`（改写 `:365`） | V2 | ① L1/L2/L3 三条不变式测试绿；② `:365` 改写后绿（**变红属预期**，写进 commit 信息）；③ `dsh_compat.py --json <FX-NO-SCHEMA-01>` → `NOT_RUN` | Test Reviewer + Code Reviewer | REQ-148 / FIX-315 |
| **V4** | group 语义与 loader 对齐（G-02/G-03 / **FIX-311**）+ `FINDING/UNVERIFIED` 分类自检（G-18） | 改 `infra/dsh_compat.py`（`PROBE_SCRIPT` 的 `walk`）、`infra/tests/test_dsh_compat.py`（改写 `:754`） | V3（同文件串行） | ① FX-GROUP-01/02/03 行为符合判据表；② `:754` 改写后绿（**归因与披露断言**）；③ 分类自检断言每个 kind 恰属一类 | Code Reviewer + Test Reviewer | REQ-148 / FIX-311 |
| **V5** | 渲染与解码面守卫（G-05/G-07/G-10/D-66/D-49/D-50/D-54/D-56） | 改 `adapters/dsh/launch.py`、`lib/index.js`、`infra/dsh_compat.py`（探针输出 `customSkillDirs`）、`infra/checks/projection.py`（归一化）、**`infra/tests/dsh_fixtures.py`（扩展本片所需的反相 fixture 常量；**R1 N-5**：该文件由 V1 创建、**V5** 使用，矩阵已对齐）**；新增测试用例（**经 `dsh_fixtures.py --emit-fixture` 生成**） | V2（同文件串行） | ① FX-CR-01/FX-TOKEN-01/02/FX-CSD-01/FX-UTF8-01 全绿（改前红、改后绿，红绿实证）；② `test_dsh_adapter.py` 全绿；③ `check-projection-sync` PASSED；④ 无未用 import（D-56）；⑤ **D-54 采样判据按 §3.3 第 11 行写死的"对象/时刻/比较式"实现**，`FX-WITNESS-01` 可机检（R0 F-13） | Code Reviewer + Test Reviewer | REQ-148 / FIX-313(a) / FIX-316 |
| **V6** | `DSH_HOME` 三方收敛（G-06 / D-16 / D-47） | 改 `lib/index.js`、`adapters/dsh/launch.py`、`infra/dsh_compat.py`（读取方语义） | V5（同文件串行） | ① FX-HOME-01/02/03 三方一致；② live-gated 差分测试与上游一致（无安装 → `NOT_RUN`，不计 issue）；③ `launch.py` 不再产出字面空白路径 | Code Reviewer | REQ-148 / FIX-316 |
| **V7** | 版本与证据看护（G-11/G-12 / D-11/D-15/D-57） | 改 `cordis.patch.yml`（去版本字面量）、`lib/index.js`（注释）、`adapters/dsh/adapter-manifest.json`（指向契约） | V2（`lib/index.js` 串行） | ① 全仓无 `0.1.5-rc.2` / `0.1.0-rc.6` 字面量；② manifest↔契约一致性判据 PASS；③ TTL 过期 → FAIL（用合成过期 fixture 验证） | Release Reviewer（声明真实性）+ Code Reviewer | REQ-148 / C-20 |
| **V8** | 契约边界门禁（Check 28w，K-1/K-3~K-13）+ 单一诊断入口 + 升级演练 | **新增** `infra/dsh_doctor.py`、`infra/checks/dsh_boundary.py`、`infra/tests/test_dsh_doctor.py`、`adapters/dsh/fixtures/host-facts-<v>.json`；改 **`infra/registry.py`**（`LOADER_WHITELIST` +2 / `_SEGMENT_LOADERS` +1 / `_COMMANDS` +1）、**`infra/quickscan_registry.py`**（`SEGMENTS` +1 `28w`，否则导入期 `RegistryError`）、**`infra/tests/test_registry.py`**（`FROZEN_*` 与 `migrated`）、**`infra/contract_matrix/snapshots.json`**（`generator.py --regen`）、**`core/architecture-baseline.json`**（`archguard-ratchet --regen` + R1 豁免到期处置）、**`infra/verify_workflow.py`**（薄 cmd + 28w section + 28u 委托，**函数内惰性 import**）、**`adapters/dsh/adapter-manifest.json`**（登记诊断入口） | V1..V7 | ① `check-dsh-boundary --fail-on-issues` PASSED（K-1/K-3~K-13；K-2 已在 V2 落地）；② `dsh-doctor --json` 输出 8 阶段 + 退出码 0/1/2；③ `--offline` 全 NOT_RUN 且退出 0；④ `--selftest` 通过（阶段崩溃隔离）；⑤ `--rehearse` 的 4 个合成突变逐项 FAIL + `FX-REHEARSE-05`/`FX-BASE-01` 按 K-13 FAIL；⑥ `FX-VERDICT-01` 按 K-12 判 doctor 自身 FAIL；⑦ 28u CLI 文本与退出码不变；⑧ `import registry` 成功且 `test_registry.py` 全绿（`FROZEN_CLI_KEYS=83`/`FROZEN_SEGMENTS=71`/`migrated` 5 项）；⑨ `archguard-ratchet`（R7 已提交==fresh）PASS 且 **R1 豁免按 O-8 的裁决**（续期或退役）登记；⑩ `test_engine_baseline_is_the_frozen_196_module_caliber` 仍绿（惰性 import） | Design Reviewer（入口与阶段契约）+ Code Reviewer + Release Reviewer（冻结面/棘轮/R1 豁免） | REQ-149 / C-16 |
| **V9** | 发布面收尾（文档/版本投影核对/迁移说明） | 改 `project/CHANGELOG.md`、release docs、`core/releases/0.81.0.json`、版本投影（**非**契约内版本） | V1..V8 | ① `check-version-consistency` PASSED；② `check-projection-sync --fail-on-issues` PASSED；③ CHANGELOG 与切片一一对应 | Release Reviewer | — |
| **V10（候选，M-0 裁决）** | `lib/index.js` catch 清理退化修复（G-04 / **FIX-313(b)**）：清理目标改用显式 staging 变量 | 改 `lib/index.js`（1-3 行）+ 新反相 fixture | V2 | ① 反相：`resolveDshHome()` 抛错路径下 CWD 的 `governance.staging-*` 不被删除；② 正常路径 staging 清理行为不变；③ J-1~J-7 不变量测试全绿 | Code Reviewer | 安全面（P7） |

### 6.2 文件冲突矩阵与波次排程

| 文件 | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | V9 |
|---|---|---|---|---|---|---|---|---|---|
| `adapters/dsh/host-contract.json`（新） | ● | | | | | | | | |
| `infra/dsh_contract.py`（新） | ● | | | | | | | | |
| `infra/tests/test_dsh_contract.py`（新） | ● | ●（+K-2 用例） | | | | | | | |
| `infra/tests/dsh_fixtures.py`（新） | ● | | | | ● | | | | |
| `core/manifest.json` | ● | | | | | | | ●（host-facts 条目） | |
| `adapters/dsh/launch.py` | | ● | | | ● | ● | | | |
| `infra/dsh_compat.py` | | ● | ● | ● | ● | ● | | | |
| `lib/index.js` | | ● | | | ● | ● | ● | | |
| `infra/tests/test_dsh_compat.py` | | | ● | ● | | | | | |
| `infra/tests/test_dsh_adapter.py` | | | | | ● | ● | | | |
| `cordis.patch.yml` / `adapter-manifest.json` | | | | | | | ● | ●（登记入口行） | |
| `infra/dsh_doctor.py` / `checks/dsh_boundary.py`（新） | | | | | | | | ● | |
| `infra/registry.py` / `quickscan_registry.py` | | | | | | | | ● | |
| `infra/verify_workflow.py` | | | | | | | | ● | |
| `infra/tests/test_registry.py` / `contract_matrix/snapshots.json` / `core/architecture-baseline.json` | | | | | | | | ● | |
| `adapters/dsh/fixtures/host-facts-<v>.json`（新） | | | | | | | | ● | |

**波次（无同文件并发）**：

| 波次 | 并行切片 | 说明 |
|---|---|---|
| W1 | V1 | 新文件 + manifest；无冲突 |
| W2 | V2 | 三个消费方一次迁移（行为保持）；**必须独占**（宿主行 + parity） |
| W3 | **V3 ∥ V7** | V3 = `dsh_compat.py` + `test_dsh_compat.py`；V7 = `cordis.patch.yml` + `adapter-manifest.json` + `lib/index.js` 注释行 ⇒ 文件不相交 |
| W4 | V4 | `dsh_compat.py` 独占（与 V3 同文件，必须串行） |
| W5 | **V5 ∥ V8** | V5 = `launch.py`/`lib`/`dsh_compat`；V8 = 新模块 + `registry.py`/`verify_workflow.py` ⇒ 不相交 |
| W6 | V6 | `launch.py`/`lib`/`dsh_compat` 独占 |
| W7 | **V9 ∥ V10** | V9 = 文档/发布面；V10 = `lib/index.js` 的 1-3 行 ⇒ 不相交 |

**并行安全结论**：核心文件（`dsh_compat.py` / `launch.py` / `lib/index.js`）构成一条串行链，是 0.81.0 的关键路径；可并行的只有新文件型切片（V1/V8）与文档型切片（V9）。`V10` 与 `V9` 可并行，但若 M-0 不纳入 V10，则 W7 只剩 V9。

**W5 的复核（R0 F-2 后）**：V5 与 V8 仍不相交——V5 = `launch.py`/`lib/index.js`/`dsh_compat.py`/`test_dsh_adapter.py`/`dsh_fixtures.py`；V8 = 新模块 + `registry.py`/`quickscan_registry.py`/`verify_workflow.py`/`test_registry.py`/`snapshots.json`/`architecture-baseline.json`/`adapter-manifest.json`/`fixtures/`。**唯一新增的相交风险**是 `core/manifest.json`（V1 与 V8 各加一条）⇒ V8 必须在 V1 之后（已在依赖前序列约束）。

**冻结面/棘轮的独占纪律（R0 F-2）**：`test_registry.py`、`contract_matrix/snapshots.json`、`core/architecture-baseline.json` 三处**只允许 V8 触碰**（它们由 `--regen` 与冻结计数驱动，任何并发修改都会互相干扰）；V8 内部步骤顺序 MUST 为 **① registry/quickscan 声明 → ② 引擎 section + 薄 cmd → ③ `generator.py --regen` → ④ `archguard-ratchet --regen` → ⑤ `FROZEN_*`/`migrated` 更新 → ⑥ R1 豁免按 O-8 处置**，每步后跑一次 `python -m unittest … -p "test_registry.py"`。

### 6.3 切片与既有 task 的对应（供 Coordinator 复用编号）

| 切片 | 承接既有 task | 备注 |
|---|---|---|
| V3 | **FIX-315**（release-checklist:128） | P1，0.80.0 已登记不阻塞 |
| V4 | **FIX-311** 的 G-02/G-03 部分 | 另一部分（P2 遗留批）不在本设计范围 |
| V5/V6/V7 | **FIX-316**（release-checklist:129）+ **FIX-313(a)** | FIX-316 是"健壮性/死代码/口径遗留批" |
| V10 | **FIX-313(b)** | 候选，M-0 裁决 |

---

## 7. (F) 验收与机检判据：四件必须机器验证的事

> **纪律**：标注「**既有命令**」= 今天即可运行；标注「**待实现**」= 属本设计新增（V1..V9），不得当作已存在能力对外声明。

### 7.1 「依赖面收窄了」

| 判据 | 命令 | 期望输出 | 状态 |
|---|---|---|---|
| 契约外硬编码字面量归零 | `python skills/software-project-governance/infra/verify_workflow.py check-dsh-boundary --fail-on-issues` | `Result: PASSED — outside-contract host literals: 0 (allowlist 3/3 — @deepseek-ai/cordis* oracle names)`；exit 0 | **待实现**（V8；K-2 的文本扫描部分 **V2**） |
| allowlist 未膨胀（BT-R-01） | 同上（K-11） | `allowlist 3/3 (budget 3, 只降不升)` | **待实现**（V8） |
| 消除项确实消失 | 同上（读 `elimination.dispositions[]`） | `eliminated: D-02, D-50, D-56 (3/3 executable); D-05 → deferred (U-1)` | **待实现**（V8） |
| 原始依赖点计数方向 | `pwsh -Command "(Select-String -Path lib/index.js,adapters/dsh/launch.py,skills/software-project-governance/infra/dsh_compat.py -Pattern '@deepseek-ai/dsh-' -AllMatches).Matches.Count"` | 改造后计数 **低于** 0.81.0 前基线（包名字面量集中到契约）；**不要求归零**（契约文件本身含包名） | **既有命令**（须在 V2 前后各跑一次留档） |
| 结构不变量未被破坏 | `python …/verify_workflow.py check-manifest-consistency --fail-on-issues` | `PASSED`（含 `PLUGIN_SCOPE_DIRS` 相等判据） | **既有命令** |

### 7.2 「契约被消费了」

| 判据 | 命令 | 期望输出 | 状态 |
|---|---|---|---|
| 静态：逐消费方与契约一一对应 | `check-dsh-boundary`（K-2/K-3/K-4/K-5；**K-2 的文本扫描在 V2 即可跑**） | 无 `outside-contract host literal` / `template row not in contract` / `unknown token` / `hook path drift` | **待实现**（K-2 → V2；其余 → V8） |
| 行为（**输出等价**）：渲染输出不变 | `python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_dsh_adapter.py"` | `Ran 43 tests … OK`（含 `:1127` parity、`:1158` 幂等）。**该条只证输出等价，不证单一事实源**（R0 BT-R-04） | **既有命令** |
| 行为（**单一事实源**）：per-field 突变矩阵 + K-2 静态扫描 | 新测试 `test_consumers_read_the_contract_instead_of_shadow_constants`（4 项字段各一条突变）+ V2 的 K-2 文本扫描 | ① 合成 token/preset id/marker 名/行集出现在消费结果中（旧常量不再出现）；② 无可从输出观测的字段（`own.package.engines_node` 等）由 K-2/K-10 覆盖 | **待实现**（V2） |
| 契约自身可解析且字段齐全 | `python …/infra/dsh_contract.py --validate`（薄 CLI，或 `test_dsh_contract.py`） | `OK — schema_version 1; host.rows 29 (23 enabled/platform + 3 group + 2 disabled:true); own.render.tokens 3; coverage.entries N` | **待实现**（V1） |

### 7.3 「零校验不再 PASS」

| 判据 | 命令 | 期望输出 | 状态 |
|---|---|---|---|
| 生成 fixture（使下述命令自包含，R0 F-11） | `python …/infra/tests/dsh_fixtures.py --emit-fixture FX-NO-SCHEMA-01 --out <tmpdir>` | 生成 `<tmpdir>/FX-NO-SCHEMA-01.cordis.yml`（同 ID 任意机器字节相同） | **待实现**（V1） |
| 报告级 | `python skills/software-project-governance/infra/dsh_compat.py --json <tmpdir>/FX-NO-SCHEMA-01.cordis.yml` | `"verdict": "NOT_RUN"`、`"rows_checked": 0`、`"issues": []`、`"coverage".rows_unverified == 1` | **既有命令** + **待实现** fixture（V1） |
| 渲染级 | `python …/verify_workflow.py check-dsh-preset-compat` | 屏幕上对 5 个零 schema 行输出 `[NOT_RUN]` 披露行；且**不存在** `[PASS] … 0` 形态（0 校验不得 PASS） | **既有命令**（行为变更属 V3） |
| 仓库真实组合的结论诚实性 | 同上 | `[PASS] verified 18 of 23 enabled row(s) …`（分母可见）+ 5 行 `[NOT_RUN]`（23 = 平台无关 29 − 3 group − 2 disabled:true − 1 平台短路，见 E-10） | **既有命令**（期望输出属 V3 目标） |
| 不变式测试 | `python -m unittest … -p "test_dsh_compat.py" -k zero_checked` | 三条不变式测试全绿 | **待实现**（V3） |

### 7.4 「有单点诊断入口」

| 判据 | 命令 | 期望输出 | 状态 |
|---|---|---|---|
| 入口存在且输出分阶段 | `python …/verify_workflow.py dsh-doctor --json` | JSON 顶层含 `verdict` / `stages`（8 条，S0~S7 齐全，每条含 `credible_face` / `evidence` / `remediation`） | **待实现**（V8） |
| 退出码语义 | `dsh-doctor --json; echo $LASTEXITCODE` | 无 FAIL → `0`；有 FAIL → `1`；未授权宿主探测/用法错误 → `2` | **待实现**（V8） |
| 离线可用 | `dsh-doctor --offline --json`（无 dsh/无 node 机器） | 8 阶段全 `NOT_RUN` + 原因 + remediation；exit `0`（不误报 FAIL） | **待实现**（V8） |
| 入口自守护 | `dsh-doctor --selftest` | 逐阶段注入异常 → 其余阶段仍输出、顶层不因崩溃变绿 | **待实现**（V8） |
| 裁决一致性 | `dsh-doctor --json` 与 `check-dsh-boundary --fail-on-issues` 同一仓库态 | 两者结论一致（不一致 → doctor 自身 FAIL）；`coverage` 由 28v 单一生成点产出（K-12，R0 BT-R-02） | **待实现**（V8） |
| 升级演练有效 | `dsh-doctor --rehearse <FX-REHEARSE-01..04>` | 4 个合成突变逐项 FAIL 并给出"我方将面临什么" | **待实现**（V8） |
| 演练不得 no-op 绿 | `dsh-doctor --rehearse <FX-REHEARSE-05>`（同版本）/ `<FX-BASE-01>`（时间倒序） | 两者均 **FAIL**（K-13，R0 BT-R-03） | **待实现**（V8） |

---

## 8. (G) 非目标与已知风险

### 8.1 非目标（本版明确不做）

| # | 非目标 | 理由 |
|---|---|---|
| N-1 | **0.80.0 遗留的真机三项验收**（设置页「自定义」标签 / 删除 / 打开目录；非治理预设会话不含治理技能；治理会话技能目录完整性） | 需用户真实 dsh 环境与授权（T-3/T-4/T-5）；本设计只提供离线代理（S6 resolution-level）与 NOT_RUN 披露，不改验收口径（release-checklist §真机验收面）。**不得**以本设计冒充该验收完成 |
| N-2 | **FIX-312**（归档引擎决策归属误判） | 与 dsh 兼容性主题无关 |
| N-3 | **FIX-314**（`review_record.py` 键含 reviewer） | 与主题无关 |
| N-4 | **`dsh_compat.py` 归属迁移**（core `infra/` → `adapters/dsh/`） | 需独立 DEC（release-checklist:137）；本设计只做了"降低迁移成本 + 显式登记"（§2.3） |
| N-5 | **`peerDependencies` 补齐** | 安装时语义未验证（U-1）；D-05 以版本闸门替代（§3.2） |
| N-6 | **消除 23 行 schema 耦合**（RISK-050 的另一条腿） | 该耦合是本插件的交付目标本身（预设承载宿主工具行）；只能前移检测，不能消除 |
| N-7 | **其它 5 个适配器**（claude/codex/gemini/opencode/chrys）的 dsh 交互 | 不在范围（AUDIT-153 §1.4） |
| N-8 | **macOS/Linux 验证**（R-19） | 本设计期与 AUDIT-153 均仅在 Windows 验证；新增判据 MUST 在实现期至少在 Linux CI 跑一次（写入 V8 验收） |
| N-9 | **运行时自愈**（自动改预设 / 自动降级 schema / 自动改写用户配置） | 违反 DEC-187 I-2 与 warn-only 政策；诊断只**报告与建议** |
| N-10 | **G-13~G-18 中未纳入的具体项** | 见 §4.5 逐条理由 |

### 8.2 设计引入的新风险与缓解

| # | 风险 | 影响 | 缓解 | 残留 |
|---|---|---|---|---|
| R-1 | **契约层成为新的单点故障**（BT-1） | 契约缺失/畸形 ⇒ 预设不交付（JS 侧无回退副本，J-4） | ① K-1/K-10 门禁 + `files` 白名单覆盖；② V2 的突变测试；③ 发布前 28u/28v 必然渲染预设 ⇒ CI 拦住打包缺陷；④ S1 remediation 明确指向 `--sync` | 契约损坏仍会中断自动交付（但**不**影响宿主 boot：warn-only） |
| R-2 | **诊断入口自身失败**（BT-2） | 最需要诊断时不可用 | §5.1 降级设计（惰性 import / 子进程隔离 / 阶段级 try / 报告恒 8 条 / `--selftest`） | doctor 进程自身被杀/解释器不可用 ⇒ 只能靠 `launch.py --smoke`（既有） |
| R-3 | **JS/Python 双消费者对同一契约解释分歧**（BT-3） | 两条交付路径写出不同预设（D-65 类事故复发） | ① 契约字段单一含义 + K-3/K-4 机检；② 三路径 sha256 parity 测试为硬门禁；③ 新增"突变测试"证明无影子副本；④ V2 明确"行为保持"验收 | 契约 schema 演进时若新增字段未同步两侧 → 由 parity 测试在 CI 抓住 |
| R-4 | **覆盖强度声明通胀**（"声明强于佐证"） | 看护体系自我感觉良好 | K-8：`strong` 必须有反相 fixture 引用；`necessary` 条目不得 `none`；强度声明只在契约一个文件（无第二台账） | 反相 fixture 的**有效性**无法自动证明（只能由测试审查评估） |
| R-5 | **fixture 陈旧制造虚假安全感**（BT-5） | 演练绿但真机坏 | TTL 判据 + `[EVIDENCE-STALE]` + 每次升级后 MUST 重录（SOP 写入 V8 交付物） | 长期不升级 ⇒ 证据必然过期（这正是判据要暴露的） |
| R-6 | **core→adapter 数据边被固化**（BT-6） | 削弱待裁决的架构归属决策 | 收窄为"一个访问器 + 一个数据文件"；显式登记；迁移成本 ≤3 处（§2.3 P-4 / §9 U-6） | 若 DEC 判 core 不得读 adapters，则需一次迁移切片（成本已知且小） |
| R-7 | **hooks 静态校验只在本仓 CI 生效**（BT-7） | 用户仓 hooks 副本（一次性复制）不受任何守卫 | ① 现有 `hooks_drift` 检查已报"陈旧"（release-checklist:133）；② V9 在迁移说明中要求用户重装 hooks；③ 本设计**不**让 hooks 引入运行时契约依赖（避免新耦合） | 用户仓旧 hook 与新版契约并存（仅影响 hook 的 dsh 路径发现，退化路径已存在） |
| R-8 | **诊断输出被当作验收** | 用户把 `dsh-doctor PASS` 当成真机验收通过 | S1/S6 的 PASS 文本 MUST 携带限定语（"resolution-level only / UI 未验证"）；§8.1 N-1 明确非目标 | 措辞纪律依赖实现与审查（已列 V8 验收项） |
| **R-9**（R0 BT-R-01） | **半迁移期守卫缺位 + allowlist 自我豁免**：V1 落契约、V2 迁消费方，而唯一能判"仍在硬编码"的 K-2 原计划要到 V8 才存在；且 allowlist 无判据 ⇒ 可无限自我豁免 | 迁移期的"已完成"是**自述**而非机检；长期看契约面可被 allowlist 侵蚀 | ① **K-2 提前到 V2**（纯文本扫描，不依赖新模块）；② **K-11**：allowlist 条目须含 `reason` + `since_slice`，条数受棘轮（只降不升）+ 体积/条数预算；③ `FX-ALLOW-01` 反相 | 迁移完成后 allowlist 仍可被**有理由地**扩大（棘轮只约束数量，不约束理由质量——由评审把关） |
| **R-10**（R0 BT-R-02） | **同一事实两个 verdict**：doctor 与 28u/28v/K-7 可能对同一事实给出不同裁决（doctor 自算 vs 检查判负） | 用户看到"doctor PASS 但 gate FAIL"，诊断可信度崩塌 | ① doctor 的 S3/S7 **消费 K-7 结果**、S2 **投影** `coverage`（单生成点）；② **K-12**：同一仓库态下 doctor 顶层 verdict 与 `check-dsh-boundary` 退出码必须一致，不一致 → doctor 自身 FAIL；③ `FX-VERDICT-01` 反相 | 一致性判据覆盖 `verdict` 与 `coverage` 两个可观测面；`evidence[]` 内的自由文本仍可能措辞不同（不影响裁决） |
| **R-11**（R0 BT-R-03） | **演练基线的"沉默失效"**：`host-facts` 无 TTL/单调性/synthetic 标记 ⇒ 同版本重录或时间倒序时演练输出"无漂移"，被读成"升级安全" | 虚假安全感：CI 全绿而真机坏 | ① **K-13**：同版本 no-op **FAIL**、`captured_at` 严格递增、baseline 纳入 TTL；② 报告逐条 `synthetic: true/false`；③ `FX-REHEARSE-05` / `FX-BASE-01` 反相 | 真实 after 仍需一次真实平面记录（§5.5 诚实边界 2，不可自动化） |
| **R-12**（R0 BT-R-04） | **"行为保持"的可验证性边界**：三路径 sha256 不变只证**输出**等价，不证"无影子副本"；且部分契约字段不产生输出差异 ⇒ 突变测试天然不适用 | V2 的"迁移完成"可能被高估 | ① K-2 提前到 V2（静态守卫）；② V2 改为 **per-field 突变矩阵**（tokens / preset id / marker 名 / 行集各一条）；③ **不可从输出观测的字段**明确改由 K-2/K-10 覆盖；④ V2 验收文字显式写"parity 只证输出等价，不证单一事实源" | 突变矩阵覆盖 4 类关键字段；其余字段依赖静态扫描（K-2/K-10），存在"读契约但不影响输出且未被扫描"的理论缝隙（低） |

---

## 9. 未验证假设与验证计划

> 纪律：以下均为**假设**（无实测证据）；**不得**被下游当事实使用（C-25 同源纪律）。凡本设计的判据依赖它们的，已在设计中标为"需先验证"或已改为"不依赖"。

| # | 假设 | 为什么未验证 | 对本设计的影响 | 验证计划（归属） |
|---|---|---|---|---|
| U-1 | `peerDependencies` 在 dsh 的 pnpm profile 平面中**不会**导致自动安装/解析新的依赖边 | AUDIT-153 未测 npm/pnpm peer 语义；本设计不得执行命令 | D-05 的"补齐声明"方向被推迟（§3.2） | 在隔离 `DSH_HOME` 的一次性 profile 上做 `dsh plugin add` 前后 diff（需授权，T-1 面） |
| U-2 | 「无 `Config` 导出 ⇒ loader 原样透传 config」 | AUDIT-153 **R-15 明确未验证** | G-01 的文案判据已改为**不断言 loader 行为**（§4.4.1 G01-e） | 读 `cordis-plugin-loader` 的 `resolveConfig` 调用点源码（只读，低成本） |
| U-3 | `npm pack --dry-run --json` 在仓库/用户目录零写入 | 未执行 | T-8 的离线化判据以此为前置 | 在**临时目录**执行并在执行前后比对仓库与 `%TEMP%` 之外的写入面（显式留痕） |
| U-4 | 「`$DSH_HOME/.agent-presets/` 是 `resolvedRoots` 的第一个（first root wins）」 | AUDIT-153 **R-13 未验证**（未逐行读数组字面量） | 本设计**未把该断言作为任何判据**；`lib/index.js:41-44` 的该表述属既有注释，V7 的"注释去版本化"不涉此句（不改写未验证断言） | 读 `dsh-agent-presets/lib/index.js:1300-1330`（只读） |
| U-5 | `{{model}}` / `{{cwd}}` 由宿主插值（T-6） | AUDIT-153 R-08 | T-6 只做"占位符存在"的离线代理 + 未验证披露 | live 会话读 persona 原文 |
| U-6 | 契约从 `adapters/dsh/` 迁移到 `core/` 的成本 ≤3 处、无逻辑变更 | 未实施 | 支撑 §2.3 P-4 的可逆性论证 | V1 落地后由 Code Reviewer 核对消费点清单（`dsh_contract.py` 路径常量 + JS URL + hooks 校验常量） |
| U-7 | group 行 `name` 非 `cordis:group` 时 loader 的行为（挂载/失败） | AUDIT-153 仅实测 `cordis:group` | G02-b 取"不可验证即判负"（fail-closed），**不**声称 loader 会失败 | 构造一次性隔离组合调用 loader（需 node + 安装态；只读探测） |
| U-8 | S5（宿主 entry 面）在授权后可稳定获得 `--dump-config` 输出 | AUDIT-153 §1.4 明确 `NOT_RUN` | S5 默认 NOT_RUN；授权模式的输出形状未验证 | 用户授权后一次性执行（T-2） |
| U-9 | `host-facts` 记录式 fixture 的字段集足以表达"哪些行会坏" | 设计期推断 | 演练判据的完备性依赖它（§5.5 诚实边界 1 已声明局限） | V8 首次记录后，用真实升级窗（或 4 个合成突变）校准字段集 |
| U-10 | K-13 的"同版本 no-op 一律 FAIL"不会误伤合法场景（例如同版本重录以刷新 TTL） | 设计期裁定，未实施 | 若误伤，合法用途会走 `--record-evidence`（刷新证据）而非 `--rehearse`；但**同版本重录后想演练**的场景会被拒 | V8 落地后收集使用反馈；若确有需要，可加显式 `--allow-same-version` 逃生门（需理由字段 + 报告标注）——本设计**不**预置该开关（避免重开"演练可绿"的漏洞） |
| U-11 | Check 28w 的 `SegmentSpec("28w", "distribution", …)` 输入 token 面可与 `28v` 对齐（§2.9.4 给出的是**建议形态**） | 设计期按 `28u`/`28v`（`:538-546`）的最近邻形态推断，未逐条核对 FEAT-025 的 disposition 规则 | 若实现期判定输入面不同，需按 C3 四段裁决重列 token 与 disposition | V8 实现首步：核对 `_excluded("PLUGIN_PACKAGE_ASSET")` 对本段是否适用（不适用则用 `_RETAIN`）并让 `test_segment_set_matches_the_quickscan_registry` 绿 |

---

## 10. 开放决策点（供 Design Review / M-0 裁决）

| # | 决策点 | 选项 | Architect 建议 |
|---|---|---|---|
| O-1 | 0.81.0 版本范围 | (a) 全量 V1~V9；(b) V1~V3 + V8（最小可用：契约 + 零校验门禁 + 诊断入口）；(c) V1~V8 不含 V9 | 建议 **(a)**，但若需要压缩关键路径，**(b)** 可独立成立（V4~V7 是缺口修复批，可下一版） |
| O-2 | 是否纳入 V10（G-04 / FIX-313(b)） | 纳入 / 不纳入 | 建议**纳入**：涉及潜在误删用户 CWD 目录，修复成本极低（1-3 行 + 1 fixture），风险等级高于"下一版再说"的收益 |
| O-3 | D-05 是否在 0.81.0 补齐 `peerDependencies` | 补齐 / 以版本闸门替代 / 延后 | 建议**以版本闸门替代**（H-1 未验证；C-1 风险面） |
| O-4 | 契约放置位置 | `adapters/dsh/`（建议）/ `core/`（若 DEC 判 core 不得读 adapters） | 建议 `adapters/dsh/`，并在 `dsh_compat.py` 归属 DEC 中一并复审 |
| O-5 | `dsh_compat.py` / `dsh_doctor.py` / `dsh_contract.py` 的层归属 | core infra（现状延续）/ 迁移适配层 | 建议**本版不迁移**，只登记"三者同属一个待裁决集合"，避免与 O-4 相互锁定 |
| O-6 | 覆盖强度 `strong` 的反相 fixture 门槛 | 1 个 / ≥2 个 | 建议 **1 个**（先建立机制，后续按缺口回填） |
| O-7 | S5 授权模式的默认开关 | 默认关闭 / 默认开启 | 建议**默认关闭**（R1 三选一未满足即禁止执行，无豁免） |
| **O-8** | **`core/architecture-baseline.json` 的 R1 豁免到期处置**（`rule: "R1"` / `expire_version: "0.81.0"`，E-20 `:6`） | (a) 续期到 0.82.0 并在 DEC 中重述理由；(b) 退役该条目（`--regen` 后成为普通基线，任何后续增长即 FATAL） | **必须由 DEC 显式裁决**，不得静默留在过期状态（棘轮会对过期豁免报错）。Architect 倾向 **(a)**：它与 §6.1 V8 的 wiring 行（本次新增的 28w section 与薄 cmd）同源，续期一次即可覆盖本版；若 M-0 选择 (b)，则本版 MUST 在 `--regen` 后确认 anchor 已吸收 wiring 行（避免下一版无心增长即红） |
| **O-9** | allowlist 预算初值（K-11） | `3`（本设计现状：`@deepseek-ai/cordis`、`@deepseek-ai/cordis-plugin-loader`、`@deepseek-ai/cordis-plugin-include` 的契约外引用）/ 其他 | 建议 **3**（即"零新增"），只降不升；新增必须走 DEC 级理由 |

---

## 附录 A：本文引用的 AUDIT-153 事实锚点索引

| 用途 | AUDIT-153 位置 |
|---|---|
| 依赖点全量清单与必要性分类 | §2.1~§2.11（D-01~D-100；`rows_enabled: 23` / `rows_checked: 18`） |
| 三类归并与反面证据 | §3.1（含 `@deepseek-ai/dsh-home-paths` 反面证据）、§3.2、§3.3 |
| 看护覆盖矩阵与盲区 B-1~B-10 | §4、§4.1 |
| 缺口 G-01~G-18 实测证据 | §5 |
| 可调测性现状（S0~S7 / T-1~T-10 / fixture 缺口） | §6.1~§6.5 |
| 事实/假设分离 | §7（R-01~R-19） |
| 下游约束 C-1~C-25 | §8.1~§8.5 |

## 附录 B：本文核实的仓库证据索引

见 §0.2（E-1~E-22，含 R0 F-2/F-3/F-12 后新增的 E-17~E-22）。所有"【实测】"标注的断言均可由该表逐条回到 `文件:行号`。

## 附录 C：术语表

| 术语 | 含义 |
|---|---|
| 契约（contract） | `adapters/dsh/host-contract.json` —— 本插件对 dsh 依赖的单一事实源 |
| 契约外硬编码 | 消费代码中出现契约已声明类别的字面量，但未在契约中登记（K-2 判据对象；豁免通道受 K-11 约束） |
| 平台无关行全集 | 模板中的全部行（29 行），含平台条件行与 `disabled: true` 行——K-3 的比对基准（R0 F-1） |
| 可信面 | 结论实际覆盖的依赖子集（例如"23 行中的 18 行"） |
| 校验面 | 声明声称覆盖的依赖子集 |
| `subject` / `audit_ids` | `coverage.entries[]` 的双键：前者指向契约内 JSON path，后者指向 AUDIT-153 的 `D-nn`（R0 F-14） |
| 探测侧 / 写入侧 | `host.env` 的两半：探测侧（`dsh_compat` 读取，fail-closed、不回落）与写入侧（三实现必须与上游一致）（R0 F-6） |
| host-facts | 记录式宿主事实快照 fixture（§5.5 [A]；含 `captured_at` / `synthetic`） |
| 演练（rehearsal） | 用记录态事实回放"宿主升级后我方将面临什么"（§5.5 [B]；同版本 no-op 必须 FAIL） |

---

## 11. R0 审查处置索引（供 R1 复审逐条验证）

> 来源：`docs/reviews/review-FEAT-028-DESIGN-R0.md`（NEEDS_CHANGE；3 P1 / 5 P2 / 10 P3+NOTE / 4 条新增蓝军）。下表给出每条发现的**处置位置**（本文件与 ADR-018 的行号以 R1 时实际为准）。

| 发现 | 级别 | 处置 | 位置 |
|---|---|---|---|
| F-1 `host.rows[]` 28 vs 模板 29 | P1 | 已修复：行集定义为**平台无关全集 29**（含 `tool-bash`），每条带 `disabled_expr`/`platform_conditional`/`enabled_on`；E-10 复算表 + K-3 全集比对 + §7.2 期望 `host.rows 29` | §0.2 E-10；§2.4 `$host.rows[]`；§2.8 K-3；§7.2 |
| F-2 V8 接线面不完备 | P1 | 已修复：V8 触碰文件补全（`quickscan_registry.py` / `test_registry.py` / `contract_matrix/snapshots.json` / `core/architecture-baseline.json`）+ 导入期 `RegistryError` 约束 + `--regen` 步骤 + **R1 豁免（0.81.0 到期）处置** + 引擎侧惰性 import（R6 196） | §0.2 E-17~E-20；§2.9.4；§6.1 V8；§6.2；§10 O-8 |
| F-3 JS 侧 J-3/J-5 与 V2 自相矛盾 | P1 | 已修复：J-3 改为"**顶层零 I/O** + 模块级 memoized `contractTokens()` + 两个函数内读取点（`ensurePreset` / `renderComposition`）"；补 `FX-JS-03`；C-1 行与 §2.6 负面清单同步 | §2.5 C-1；§2.6 J-3 + 取舍段；§5.6；§6.1 V2⑦ |
| F-4 三类必要依赖无表达 | P2 | 已修复：补 `own.package.dsh_bundle_patch_key`、`own.checks.exit_codes`、`host.skill_frontmatter.*` 三组字段 + 各自判据（K-2 命中目标 / K-5 / shim 校验） | §2.4 |
| F-5 `required_keys`/`schema_export` 无 V1 来源 | P2 | 已修复：拆为**记录式子块**（`source: recorded`，V1 允许为空且 `recorded: false`），只有 `--record-evidence` 可写；**禁止人工誊抄**；K-1 只要求存在不要求非空 | §2.4；§5.4；§6.1 V1② |
| F-6 `host.env` 写入/探测侧未拆 | P2 | 已修复：拆 `write_side` / `probe_side`；G06-b 仅适用写入侧，新增 G06-b'（探测侧 fail-closed 反相断言） | §2.4；§4.4.4 |
| F-7 `load_contract` 签名/异常缺失 | P2 | 已修复：§2.5.1 给出签名 + 三异常类（`ContractUnreadable`/`ContractMalformed`/`ContractSchemaUnknown`）+ 逐消费方语义；K-1 引用同一分类 | §2.5.1；§2.8 K-1 |
| F-8 E-10 的"18 行 config"误推 | P3 | 已修复：改为"含 `config:` 的行 = 17（14 非 group + 3 group）"；`rows_checked: 18` 标注为**探针事实、不可由模板推导** | §0.2 E-10③④ |
| F-9 ADR §3.1 候选 C 理由③ 与 I-3 相反 | P3 | 已修复：删除"与 I-3 方向相反"的表述，改写为"不采纳：以契约化 + 三方差分替代（理由见 C-1 与 AUDIT-153 §3.1 反面证据）" | ADR-018 §3.1 |
| F-10 `baseUrl` 语义未固定 | P3 | 已修复：契约增 `loader_scope_baseurl_shape = "file-url"` + 反相 fixture `FX-BASEURL-01` | §2.4；§5.6 |
| F-11 生成式 fixture 验收不可复现 | P3 | 已修复：`dsh_fixtures.py --emit-fixture <ID> --out <dir>`（同 ID 字节相同）；§4.4.1⑤ 与 §7.3 改为自包含命令 | §4.4.1⑤；§5.4；§6.1 V1⑥；§7.3 |
| F-12 fixture 会被 npm 发布 | P3 | 已修复：记录式 fixture 移至 `adapters/dsh/fixtures/`，**显式声明随包发布为有意设计**（用户可离线演练）+ 体积预算（≤64 KiB/文件、≤3 版本文件）+ K-10 守护 | §2.9.2；§5.4 |
| F-13 D-54 双采样未定义 | P3 | 已修复：写死采样对象（`top_level` / `write_surface` 两分量）、时刻（前 1 次 + 后连续 2 次、间隔 0）、比较式（名字集合差集 + 复现才 FAIL；`write_surface` 不容忍竞态） | §3.3 第 11 行；§6.1 V5⑤ |
| F-14 `coverage` 与 62 条必要依赖无映射 | P2 | 已修复：`coverage.entries[]` 双键（`subject` + `audit_ids[]`）+ 覆盖判定规则（⊇、允许一 ID 多 subject、同 subject 重复判 FAIL）+ K-8/K-9 引用 | §2.4 `coverage.*`；§4.1 条 1；§2.8 K-8/K-9 |
| F-15 K-8 解析位置未指明 | NOTE | 已修复：显式写"解析在 `checks/dsh_boundary` 内完成；`dsh_contract` 不得 import registry（否则成环）" | §4.1 条 2；§2.8 K-8；ADR §8 |
| **BT-R-01** 半迁移 + allowlist 侵蚀 | 新增 | 已纳入：K-2 **提前到 V2** + 新增 **K-11**（`reason`/`since_slice`/棘轮预算）+ `FX-ALLOW-01` + 新风险 R-9 | §2.1；§2.8 K-2/K-11；§6.1 V2；§8.2 R-9；§10 O-9；ADR §2 D-5 / §6 |
| **BT-R-02** 同一事实两个 verdict | 新增 | 已纳入：新增 **K-12**（doctor ↔ boundary 裁决一致 + `coverage` 单生成点）；§5.1 单一裁决纪律；S3/S7 改"消费 K-7"；`FX-VERDICT-01`；新风险 R-10 | §2.8 K-12；§5.1；§5.2；§5.6；§8.2 R-10；ADR §6 |
| **BT-R-03** baseline 无 TTL/单调性/synthetic | 新增 | 已纳入：新增 **K-13**（同版本 no-op FAIL、`captured_at` 严格递增、baseline 纳入 TTL、条目级 `synthetic` 标记）；§5.4/§5.5 更新；`FX-REHEARSE-05`/`FX-BASE-01`；新风险 R-11；U-10 | §2.8 K-13；§5.4；§5.5；§5.6；§8.2 R-11；§9 U-10；ADR §6 |
| **BT-R-04** "行为保持"只证输出等价 | 新增 | 已纳入：K-2 前置到 V2 + **per-field 突变矩阵**（4 类字段）+ 不可观测字段改由 K-2/K-10 覆盖 + V2 验收措辞澄清；新风险 R-12 | §6.1 V2②④⑤；§7.2；§8.2 R-12；ADR §6 |

**仍存疑 / 有意偏离（如实标注）**：
1. **§2.9.4 的 `SegmentSpec("28w", …)` 输入 token 面**：按 `28u`/`28v` 最近邻形态推断，disposition 规则（`_excluded("PLUGIN_PACKAGE_ASSET")` vs `_RETAIN`）**未核验** ⇒ 标为假设 U-11，实现首步核对。
2. **R1 豁免的处置**（O-8）：本设计给出 (a) 续期 / (b) 退役两个选项与倾向，**不代为裁决**——它涉及版本基线与 DEC，属 M-0。
3. **K-13 的 no-op 一律 FAIL**：可能拒绝"同版本重录后演练"这一合法用法（U-10）；设计**不预置**逃生开关（避免重开漏洞），如需再由 DEC 决定。
4. **S5（宿主 entry 面）** 仍为 `NOT_RUN`（T-2 未离线化）——这是**有意**保留的未验证面，不因本次修订而改变。

### 11.1 R1（`REVIEW-FEAT-028-R1`，APPROVED_WITH_NOTES / unresolved_blockers=0）非阻塞项处置

| 编号 | 级别 | 本批状态 | 处置 | 位置 |
|---|---|---|---|---|
| **N-1** 同一事实两个字段名（`platform_expr_rows[]`） | P3 | **本批闭合** | 删除该字段表述（**不设**派生字段、禁止第二来源）；平台条件行的唯一载体 = §2.4 `host.rows[].{platform_conditional, enabled_on, disabled_expr}`；同时把幻名 `js_scope` 更正为 §2.4 实有的 `host.row_contract.loader_scope` | §3.3 第 7 行 |
| **N-4** 两处新字段的判据无 guard 归属 | P3 | **本批闭合** | `host.skill_frontmatter.*` → `guard = test_dsh_adapter.py::test_skill_shim_frontmatter_contract`（`:633-648`）；`own.checks.exit_codes` → `guard = test_dsh_adapter.py:782/806/819/832` + `:1066` + **K-12**；两者引用 MUST 进 `coverage.entries[].guard[]`（K-8） | §2.4 两行判据列 |
| **N-5** §6.2 矩阵与 §6.1 切片清单不一致（`dsh_fixtures.py` 标 V4） | P3 | **本批闭合** | 矩阵改为 **V1 创建 + V5 使用**；§6.1 V5 触碰文件补列 `infra/tests/dsh_fixtures.py`（扩展反相 fixture 常量）⇒ 两处对齐 | §6.1 V5 行；§6.2 矩阵行 |
| **N-7** §4.1 条 1 "61 条 / 62 条"重复且唯一性口径含糊 | P3 | **本批闭合** | 删除"61 条"残句（计数统一 **62**，与 K-9/O-9 一致）；唯一性规则改写为"**同一 `subject` 不得重复声明**"，并显式声明"一个 `audit_id` 出现在多个 `subject` **不判为重复**" | §4.1 条 1 |
| N-2 K-11 `allowlist_budget` 锚点位置未定（P2） | P2 | **留 V8（按 Coordinator 指令）** | 需把 budget 锚定到契约之外（`FROZEN_*` 同族常量或 `architecture-baseline.json` 的只降不升机制）——V8 落地前强制项 | §2.8 K-11；§2.1；§7.1；§10 O-9 |
| N-3 K-12 与 `--offline` 适用域未划 | P2 | **留 V8（按 Coordinator 指令）** | K-12 比较限定"全阶段非 `--offline` 运行"；`--offline` 的"全 NOT_RUN / exit 0"限定为"文件级判据亦无 FAIL"的干净态 | §2.8 K-12；§5.1；§6.1 V8③ |
| N-6 突变矩阵进程隔离 / `FX-BASEURL-01` 构造 / baseline TTL 后果定型（含 §7.2 单跑 `Ran 43` ↔ 实测 46 的口径） | P3 | **留 V8（按 Coordinator 指令）** | (a) JS 突变一律独立进程、Python 用 `reset_cache()`；(b) `FX-BASEURL-01` 改为断言注入值形态或 `new URL(baseUrl)`/`fileURLToPath` 语义差异；(c) baseline 超 TTL 定型为 **FAIL** + `[EVIDENCE-STALE]` | §6.1 V2④；§5.6；§5.5；§7.2 |

> **R1 处置纪律**：N-1/N-4/N-5/N-7 于本批（文档级）闭合并就地标 `R1 N-n`；N-2/N-3/N-6 为 **V8 落地前义务**（Coordinator 在 V8 派发时注入为强制项），本文件**不**预置结论以免越权裁决。

---

*文档结束。本文件与 `docs/architecture/ADR-018-dsh-host-compatibility-contract.md` 是本任务（FEAT-028）唯一产物；本次未修改任何产品代码或治理记录。*
