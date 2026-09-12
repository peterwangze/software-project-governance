# verify_workflow.py 内嵌数据块全量归宿清单（0.80.0）— DOC-003

| 项 | 值 |
|---|---|
| 任务 | DOC-003（P2）——192 数据块全量归宿清单（§5.2 五类分类 + 消费方） |
| 输入 | `docs/requirements/architecture-audit-facts-0.80.0.md` §3.1/§3.4；`docs/requirements/architecture-evolution-0.80.0.md` §5.1/§5.2 |
| 对象 | `skills/software-project-governance/infra/verify_workflow.py` @ 当前 HEAD（LOC 24,302 = facts 基线 commit `213fbba0` 的 24,252 之后 3 个 commit 净 +50：`1cda292c`/`e994c7ad`/`c4437577`，块数不变） |
| 方法 | 一次性 AST 提取（Python 3.14.3，脚本见附录 A，不入库）+ facts 正则口径复算 + git 历史对账 + 消费方程序化扫描（AST Load 使用点 + 仓内 `.py` 全扫分类）。零产品代码修改；未动 `.governance/`。 |
| 消费方列图例 | **内部**=verify_workflow.py 内 AST Load 使用点；**dyn**=`"NAME" in globals()` 动态探测；**外部产品**=checks/*_domain.py 等经 `_SHARED_NAMES`/`_vw()` 回取；**测试**=`import verify_workflow as vw` 消费；**源扫描/fixture**=字符串形态引用（重命名/搬移会破坏的消费面——迁移风险点）；**同名副本**=其他文件同名定义（分叉风险，F-4） |

---

## 1. 口径定义与总量摘要

**三层口径**（互相可对账）：

| 层 | 口径 | 站点数 | 说明 |
|---|---|---|---|
| L0 | 模块级赋值站点全集（AST：Assign/AnnAssign，单 Name 目标，top-level） | **253** | 含路径/标量等非数据块 |
| L1 | **数据块清单（本交付）** = L0 中 list/dict/set/tuple 字面量站点（144，主表 §3）+ 非字面量数据站点（58，表 §4：facts 口径命中但非字面量 49 + AST 增补 9） | **202** | 合计 2,441 行（块跨度口径） |
| L2 | 范围外站点 = 路径/根解析常量、标量配置（int/str/env/退出码）、别名赋值 | 51 | 附录 B 逐条列出（不属"数据块"，列出以证覆盖 100%） |

**facts §3.1 正则口径**（`^([A-Z][A-Z0-9_]{3,})\s*=\s*[\[\{\("r]`）本次实测复现 **184 块 / 2,323 行**（详见 §2 对账——文档声称的 192/2,048 不可复现）。

**五类归宿分布**（§5.2 框架；按站点数/块跨度行数）：

| 归宿类 | 站点 | 行数 | 判定规则（本清单执行版） |
|---|---|---|---|
| A. JSON registry | **13**（12 名，REQUIRED_SNIPPETS 占 2 站点） | 823 | §5.2 点名锚点 5 名 + 跨平台/跨域声明式矩阵（跨 ≥2 检查域消费、或投影/平台契约语义、或外部产品/测试消费） |
| B. 域内 data.py | **136** | 1,247 | 单检查域消费的 token/枚举/小映射/文本；含消费方已迁至 checks/*_domain.py 的 `_SHARED_NAMES` 回取块 |
| C. Python 常量模块 | **44** | 342 | 含 re.compile 编译对象（38 站点）或 frozenset/set/tuple()/join 等 Python 特有结构（DEC-088） |
| D. 项目级配置 | **0** | 0 | 无实例（W-3 裁决维持：不建，YAGNI） |
| E. 构建期生成 | **9** | 28 | 可由权威源推导：lifecycle-registry.json（3）、SKILL.md 版本钉（5）、投影标记契约（1） |

**迁移优先级分布**（按清单行 201 行计）：**P1 × 8**（全部 A 类锚点/大块）、**P2 × 48**（A 小块 4 + B 大块〔span≥20〕+ C 家族聚合 + E 全部）、**保持 × 145**（B 小块随宿主检查随迁、C 散点编译对象、死数据候选待裁决）。

---

## 2. 与 facts §3.1 对账（192/2,048 复现性 + 漂移）

### 2.1 192 块不可复现（证据链）

在 facts 基线 commit `213fbba0`（2026-09-09，LOC 24,252 与 facts §3.1 精确一致）上复算：

| 口径变体 | 基线 213fbba0 | 当前 HEAD | 备注 |
|---|---|---|---|
| 文档化正则（锚定 `^`） | **184 块 / 2,323 行** | 184 块 / 2,323 行 | 块跨度口径=定义行→下一 top-level 语句前 |
| 同上，值跨度（AST end_lineno） | 184 块 / 2,165 行 | — | 2,048 与两种行口径均不符 |
| +f/+b 前缀、名字长度 {1,}/{2,} | 184 | 184 | 无变化 |
| 任意 RHS（`^NAME\s*=`） | 216 | 216 | 含注解赋值等 |
| 允许缩进（`^\s*`） | 188 | 188 | 多出 4 个函数内列首块 |
| 去锚点（任意位置匹配） | 218 = 184 top-level + **8 函数内缩进** + 26 行内中段匹配 | — | **差值 8 恰为 192−184** |

- **git 历史对账**：最近 30 个触及该文件的 commit（2026-08-23 ~ 09-10）块数区间 176~184，**192 从未出现**于任何已提交版本。
- **最可能机制（假设，无法完全证伪）**：facts 测量脚本统计时混入了 8 个函数内缩进大写赋值块（184+8=192）；"2,048 行"与所有可复现行口径（2,323/2,165）均不符，无法归因。
- **处置**：本清单以实测 **184** 为 facts 口径基线，登记勘误建议（F-3）。

### 2.2 AST 口径 ↔ facts 口径差异构成

| 集合 | 站点 | 构成 |
|---|---|---|
| 交集（大写字面量块） | 135 | list/dict/set/tuple 字面量、名字匹配 facts 正则 |
| facts 独有（→ 表 §4） | 49 | call:compile 30、const:str 13、call:join 3、binop 2、listcomp 1 |
| AST 独有（→ 主表 + 表 §4 尾部） | 9+9 | 字面量但下划线私有名 9（`_W7_*` 等，facts 正则 `^[A-Z]` 排除）；非字面量且 facts 未命中 9（私有 `_*_RE` 编译对象 7、frozenset 1、date 构造 1） |

即：**本清单 202 站点 = facts 口径复现 184 + AST 增补 18**，两层口径全部覆盖、无一遗漏（L0=253 全数入册）。

### 2.3 facts §3.4 点名表漂移（基线→当前 HEAD）

- 24/26 张点名表定义行 **+3**（213fbba0 后插入行所致，块体不变）；
- **改名 2 张**：`GATE_EXECUTION_REGISTRY_ALLOWED_FUNCTIONS` → `GATE_EXECUTION_ALLOWED_FUNCTIONS`（L2528）；`EXTERNAL_PROJECT_VALIDATION_NATIVE_ENTRY_FILES` → `EXTERNAL_PROJECT_NATIVE_ENTRY_FILES`（L19127）；
- `REQUIRED_SNIPPETS` 实体 325 → **337 行**（+12，键数 45）。

---

## 3. 主清单——模块级 list/dict/set/tuple 字面量块（144 站点 / 143 行）

行数=块跨度（定义行至下一 top-level 语句前一行，与 facts §3.4 同口径）。`REQUIRED_SNIPPETS` 两个赋值站点（L710 占位 + L714 实体）合并为一行。归类/优先级规则见 §1；判定依据演进文档 §5.2 锚点优先，其余按消费方实证判定。

| 块名 | 定义块（行） | 行数 | 类型 | 归宿 | 理由 | 消费方（grep 实证） | 优先级 |
|---|---|---|---|---|---|---|---|
| PLUGIN_SCOPE_DIRS | L273-L285 | 13 | set[9] | B | 单域 token/枚举/映射（_is_plugin_path）——域内 data.py | 内部：_is_plugin_path L299；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:611 等8处；同名副本：skills/software-project-governance/infra/cleanup.py:46 等3处 | 保持 |
| PLATFORM_ENTRY_FILES | L356-L363 | 8 | set[4] | A | 平台入口文件清单，跨 2 域消费（context + untracked） | 内部：_is_context_product_file L8661；check_untracked_files L17339 | P2 |
| BLOCKING_LOCK_ISSUE_TYPES | L364-L378 | 15 | set[11] | B | 单域 token/枚举/映射（lock_issue_is_blocking）——域内 data.py | 内部：lock_issue_is_blocking L383 | 保持 |
| REQUIRED_FILES | L396-L457 | 62 | dict[59] | A | §5.2 A 锚点：全仓文件契约 + manifest.json 重复副本（EVD-630，兼具 E 特征） | 内部：_apply_project_root_override L243；_check_all_required_files_exist L16612；check_files L1248；dyn globals() L242 | P1 |
| OPTIONAL_PROJECTION_FILES | L458-L488 | 31 | dict[27] | A | §5.2 A 锚点：投影文件清单（27 项可选契约） | 内部：check_files L1249 | P1 |
| PROJECTION_SNIPPETS | L489-L626 | 138 | dict[21] | A | §5.2 A 锚点：投影占位符契约；唯一运行时消费为 L712 死组合（F-2） | 内部：<module> L712；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:649 | P1 |
| WORKFLOW_SNIPPETS | L627-L709 | 83 | dict[11] | A | §5.2 A 锚点：工作流占位符契约；唯一运行时消费为 L711 死组合（F-2） | 内部：<module> L711 | P1 |
| REQUIRED_SNIPPETS | L710 占位+L714-L1050 | 1+337 | dict[45] | A | §5.2 A 锚点：45 文件 snippet 契约实体（含内嵌版本串，version.py 源扫描消费） | 内部：<module> L711/L712；check_snippets L1271；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:616 等2处；源扫描/fixture：skills/software-project-governance/infra/tests/test_release_ledger.py:664 等3处；另 module 级 L711-712 死组合（F-2） | P1 |
| LOOP_ROLE_SKILL_CONTRACTS | L1289-L1319 | 31 | dict[7] | B | 单域 token/枚举/映射（check_loop_role_skill_consistency）——域内 data.py | 内部：check_loop_role_skill_consistency L1366/L1404；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:16716 | P2 |
| LOOP_ROLE_SHARED_SEMANTIC_TOKENS | L1320-L1341 | 22 | tuple[18] | B | 单域 token/枚举/映射（check_loop_role_skill_consistency）——域内 data.py | 内部：check_loop_role_skill_consistency L1394 | P2 |
| ACTIVE_AGENT_ROLES | L1452-L1468 | 17 | list[14] | B | 单域 token/枚举/映射（check_architecture_fact_source）——域内 data.py | 内部：check_architecture_fact_source L7496；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:1038 | 保持 |
| NAMED_REVIEWER_ROLES | L1469-L1477 | 9 | list[6] | B | 单域 token/枚举/映射（check_architecture_fact_source）——域内 data.py | 内部：check_architecture_fact_source L7499 | 保持 |
| GOVERNANCE_DEVELOPER_REQUIRED_SKILLS | L1478-L1483 | 6 | list[3] | B | 单域 token/枚举/映射（check_architecture_fact_source）——域内 data.py | 内部：check_architecture_fact_source L7478 | 保持 |
| FIX_069_RELEASE_BLOCKERS | L1484-L1492 | 9 | list[6] | B | 单域 token/枚举/映射（check_release_readiness_fact_source）——域内 data.py | 内部：check_release_readiness_fact_source L1778/L1802 | 保持 |
| REQ_059_RELEASE_BLOCKERS | L1493-L1500 | 8 | list[6] | B | 单域 token/枚举/映射（check_release_readiness_fact_source）——域内 data.py | 内部：check_release_readiness_fact_source L1802 | 保持 |
| MAINSTREAM_AGENT_ADAPTERS | L1503-L1503 | 1 | list[6] | A | 平台适配矩阵，跨 2 检查域消费（adapter-contract + runtime-matrix） | 内部：check_agent_adapter_contract L5804；check_runtime_readiness_matrix L2986；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:547 | P2 |
| ADAPTER_REQUIRED_KEYS | L1504-L1521 | 18 | list[14] | B | 单域 token/枚举/映射（check_agent_adapter_contract）——域内 data.py | 内部：check_agent_adapter_contract L5817 | 保持 |
| FIX_087_ACTIVE_TASKS | L1851-L1851 | 1 | list[7] | B | 单域 token/枚举/映射（check_hot_fact_source_consistency）——域内 data.py | 内部：check_hot_fact_source_consistency L2054 | 保持 |
| FIX_087_ACTIVE_FIXES | L1852-L1852 | 1 | list[6] | B | 单域 token/枚举/映射（check_hot_fact_source_consistency）——域内 data.py | 内部：check_hot_fact_source_consistency L2076 | 保持 |
| FIX_087_REQ_TASKS | L1853-L1860 | 8 | dict[5] | B | 单域 token/枚举/映射（check_hot_fact_source_consistency）——域内 data.py | 内部：check_hot_fact_source_consistency L2102 | 保持 |
| FIX_105_READINESS_RELEASE_BLOCKERS | L1865-L1867 | 3 | list[2] | B | 单域 token/枚举/映射（check_hot_fact_source_consistency）——域内 data.py | 内部：check_hot_fact_source_consistency L2066 | 保持 |
| RUNTIME_MATRIX_AGENT_IDS | L2159-L2159 | 1 | list[8] | B | 单域 token/枚举/映射（check_runtime_readiness_matrix）——域内 data.py | 内部：check_runtime_readiness_matrix L2979/L2982；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:548 | 保持 |
| RUNTIME_MATRIX_RESEARCH_ONLY_IDS | L2160-L2160 | 1 | list[2] | B | 单域 token/枚举/映射（check_runtime_readiness_matrix）——域内 data.py | 内部：check_runtime_readiness_matrix L3020 | 保持 |
| MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS | L2162-L2171 | 10 | list[8] | B | 单域 token/枚举/映射（check_mainstream_agent_loading）——域内 data.py | 内部：check_mainstream_agent_loading L4798；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:550 等2处 | 保持 |
| MAINSTREAM_AGENT_LOADING_TIER1 | L2172-L2179 | 8 | list[6] | B | 单域 token/枚举/映射（check_mainstream_agent_loading）——域内 data.py | 内部：check_mainstream_agent_loading L4816/L4849；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:551 | 保持 |
| MAINSTREAM_AGENT_LOADING_TIER2 | L2180-L2186 | 7 | list[5] | B | 单域 token/枚举/映射（_append_mainstream_loading_overclaim_issues、check_mainstream_agent_loading）——域内 data.py | 内部：_append_mainstream_loading_overclaim_issues L4751；check_mainstream_agent_loading L4816/L4857 | 保持 |
| MAINSTREAM_AGENT_LOADING_ADAPTERS | L2187-L2276 | 90 | dict[6] | A | 6 平台×token 声明式矩阵（90 行），多平台 README 投影参与 | 内部：check_mainstream_agent_loading L4872；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:552 等2处 | P1 |
| MAINSTREAM_AGENT_LOADING_README_TOKENS | L2277-L2283 | 7 | list[5] | B | 单域 token/枚举/映射（check_mainstream_agent_loading）——域内 data.py | 内部：check_mainstream_agent_loading L4813 | 保持 |
| MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS | L2284-L2292 | 9 | list[7] | B | 单域 token/枚举/映射（check_mainstream_agent_loading）——域内 data.py | 内部：check_mainstream_agent_loading L4834 | 保持 |
| MAINSTREAM_AGENT_LOADING_BOUNDARY_TOKENS | L2293-L2299 | 7 | list[5] | B | 零消费（内部+外部 grep 均无）——死数据候选 F-1，裁决前保持 | （零消费——F-1） | 保持 |
| MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS | L2300-L2308 | 9 | list[7] | B | 单域 token/枚举/映射（_append_mainstream_loading_overclaim_issues、_mainstream_loading_line_has_safe_negation 等3函数）——域内 data.py | 内部：_append_mainstream_loading_overclaim_issues L4732；_mainstream_loading_line_has_safe_negation L4703；list_negation_covers_phrase L4626/L4647 | 保持 |
| MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS | L2309-L2345 | 37 | list[35] | B | 单域 token/枚举/映射（_append_mainstream_loading_overclaim_issues、_mainstream_loading_line_has_safe_negation 等3函数）——域内 data.py | 内部：_append_mainstream_loading_overclaim_issues L4744；_mainstream_loading_line_has_safe_negation L4704；list_negation_covers_phrase L4628/L4649 | P2 |
| FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES | L2347-L2347 | 1 | set[3] | B | 单域 token/枚举/映射（check_first_session_measurement）——域内 data.py | 内部：check_first_session_measurement L3076/L3079 | 保持 |
| DYNAMIC_LIFECYCLE_MIGRATION_BOUNDARY_TOKENS | L2354-L2363 | 10 | list[8] | B | 单域 token/枚举/映射（_migration_guide_issues、check_dynamic_lifecycle_migration_preview）——域内 data.py | 内部：_migration_guide_issues L4044；check_dynamic_lifecycle_migration_preview L4361 | 保持 |
| DYNAMIC_LIFECYCLE_MIGRATION_FORBIDDEN_OVERCLAIMS | L2364-L2378 | 15 | list[13] | C | 含 re.compile 编译对象成员——DEC-088 loader 例外 | 内部：_dynamic_migration_forbidden_text_issues L4060 | 保持 |
| LIFECYCLE_REGISTRY_STAGE_IDS | L2380-L2392 | 13 | list[11] | E | 可由 core/lifecycle-registry.json（stage 全集，值域重复） 推导——构建期生成 | 内部：check_lifecycle_registry L3454/L3480 | P2 |
| LIFECYCLE_REGISTRY_REQUIRED_FLOW_FIELDS | L2393-L2409 | 17 | list[15] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3580/L3787 | 保持 |
| LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES | L2410-L2418 | 9 | set[7] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3596/L3604；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:4189 | 保持 |
| LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS | L2419-L2427 | 9 | set[7] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3642 | 保持 |
| LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS | L2428-L2434 | 7 | set[5] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3674 | 保持 |
| LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS | L2435-L2441 | 7 | set[5] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3726 | 保持 |
| LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS | L2442-L2447 | 6 | set[4] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3732 | 保持 |
| LIFECYCLE_REGISTRY_BOUNDARY_TOKENS | L2448-L2458 | 11 | list[9] | B | 单域 token/枚举/映射（check_lifecycle_registry）——域内 data.py | 内部：check_lifecycle_registry L3429 | 保持 |
| LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS | L2459-L2484 | 26 | list[6] | C | 含 re.compile 编译对象成员——DEC-088 loader 例外 | 内部：check_lifecycle_registry L3826 | 保持 |
| LIFECYCLE_REGISTRY_RUNTIME_ACTIVATION_EXPECTED | L2485-L2491 | 7 | dict[5] | E | 可由 core/lifecycle-registry.json runtime_activation 段镜像 推导——构建期生成 | 内部：check_lifecycle_registry L3417 | P2 |
| GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS | L2492-L2501 | 10 | set[8] | B | 单域 token/枚举/映射（_check_gate_execution_registry）——域内 data.py | 内部：_check_gate_execution_registry L3258 | 保持 |
| GATE_EXECUTION_REQUIRED_FIELDS | L2502-L2511 | 10 | set[8] | B | 单域 token/枚举/映射（_check_gate_execution_registry）——域内 data.py | 内部：_check_gate_execution_registry L3289 | 保持 |
| GATE_EXECUTION_CHECK_REQUIRED_FIELDS | L2512-L2517 | 6 | set[4] | B | 单域 token/枚举/映射（_gate_execution_check_definition_issues）——域内 data.py | 内部：_gate_execution_check_definition_issues L3220 | 保持 |
| GATE_EXECUTION_ALLOWED_SEVERITIES | L2518-L2518 | 1 | set[4] | B | 单域 token/枚举/映射（_check_gate_execution_registry、_gate_execution_check_definition_issues）——域内 data.py | 内部：_check_gate_execution_registry L3317/L3368；_gate_execution_check_definition_issues L3230/L3231 | 保持 |
| GATE_EXECUTION_ALLOWED_EXECUTORS | L2519-L2527 | 9 | set[7] | B | 单域 token/枚举/映射（_gate_execution_check_definition_issues）——域内 data.py | 内部：_gate_execution_check_definition_issues L3228 | 保持 |
| GATE_EXECUTION_ALLOWED_FUNCTIONS | L2528-L2543 | 16 | set[14] | B | 单域 token/枚举/映射（_gate_execution_check_definition_issues）——域内 data.py | 内部：_gate_execution_check_definition_issues L3232 | 保持 |
| GOVERNANCE_PACK_IDS | L2544-L2550 | 7 | list[5] | B | 单域 token/枚举/映射（check_governance_packs、check_readme_pack_guidance）——域内 data.py | 内部：check_governance_packs L4417/L4489；check_readme_pack_guidance L4515；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:3019 等2处 | 保持 |
| GOVERNANCE_PACK_REQUIRED_FIELDS | L2551-L2562 | 12 | list[10] | B | 单域 token/枚举/映射（check_governance_packs）——域内 data.py | 内部：check_governance_packs L4433 | 保持 |
| GOVERNANCE_PACK_PROFILE_IDS | L2563-L2563 | 1 | set[3] | B | 单域 token/枚举/映射（check_governance_packs）——域内 data.py | 内部：check_governance_packs L4448 | 保持 |
| GOVERNANCE_PACK_KNOWN_CHECKS | L2564-L2611 | 48 | set[46] | B | 单域 token/枚举/映射（check_governance_packs）——域内 data.py | 内部：check_governance_packs L4471 | P2 |
| GOVERNANCE_PACK_STATUS_DOC_PATHS | L2612-L2617 | 6 | list[4] | B | 单域 token/枚举/映射（check_governance_pack_status）——域内 data.py | 内部：check_governance_pack_status L5145；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:3361 等2处 | 保持 |
| GOVERNANCE_PACK_STATUS_REQUIRED_TOKENS | L2618-L2629 | 12 | list[10] | B | 单域 token/枚举/映射（check_governance_pack_status）——域内 data.py | 内部：check_governance_pack_status L5152 | 保持 |
| GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS | L2630-L2641 | 12 | list[10] | B | 单域 token/枚举/映射（_append_missing_status_boundary_issues）——域内 data.py | 内部：_append_missing_status_boundary_issues L5133 | 保持 |
| GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS | L2643-L2654 | 12 | list[10] | B | 单域 token/枚举/映射（check_governance_pack_status）——域内 data.py | 内部：check_governance_pack_status L5164 | 保持 |
| GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS | L2655-L2677 | 23 | list[21] | B | 单域 token/枚举/映射（_append_pack_overclaim_issues）——域内 data.py | 内部：_append_pack_overclaim_issues L5102 | P2 |
| GOVERNANCE_CONTEXT_REQUIRED_FIELDS | L2678-L2686 | 9 | list[7] | B | 单域 token/枚举/映射（check_governance_context）——域内 data.py | 内部：check_governance_context L8813 | 保持 |
| GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS | L2687-L2696 | 10 | set[8] | B | 单域 token/枚举/映射（_parse_snapshot_context_tasks）——域内 data.py | 内部：_parse_snapshot_context_tasks L8512 | 保持 |
| GOVERNANCE_CONTEXT_BLOCKED_MARKERS | L2697-L2697 | 1 | tuple[5] | B | 单域 token/枚举/映射（discover_governance_context）——域内 data.py | 内部：discover_governance_context L8765 | 保持 |
| CAPABILITY_CONTEXT_REQUIRED_FIELDS | L2698-L2710 | 13 | list[11] | B | 单域 token/枚举/映射（check_capability_context）——域内 data.py | 内部：check_capability_context L8861 | 保持 |
| CAPABILITY_CONTEXT_ALLOWED_STATUSES | L2711-L2718 | 8 | set[6] | B | 单域 token/枚举/映射（check_capability_context）——域内 data.py | 内部：check_capability_context L8874/L8927 | 保持 |
| CAPABILITY_CONTEXT_DEGRADED_STATUSES | L2719-L2719 | 1 | set[4] | B | 单域 token/枚举/映射（check_capability_context）——域内 data.py | 内部：check_capability_context L8894/L8935 | 保持 |
| CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS | L2722-L2730 | 9 | list[4] | B | 单域 token/枚举/映射（check_capability_context）——域内 data.py | 内部：check_capability_context L8939 | 保持 |
| HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS | L2731-L2741 | 11 | list[9] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8299 | 保持 |
| HOST_CAPABILITY_CONTEXT_SCENARIOS | L2742-L2751 | 10 | set[8] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8343；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:5654 | 保持 |
| HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS | L2752-L2761 | 10 | list[8] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8320 | 保持 |
| HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES | L2762-L2770 | 9 | set[7] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8324 | 保持 |
| HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES | L2771-L2777 | 7 | set[5] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8326/L8330 | 保持 |
| HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS | L2778-L2786 | 9 | list[7] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8348 | 保持 |
| HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS | L2787-L2808 | 22 | list[20] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8367 | P2 |
| HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS | L2809-L2812 | 4 | dict[2] | B | 单域 token/枚举/映射（check_host_capability_context）——域内 data.py | 内部：check_host_capability_context L8339/L8362 | 保持 |
| OFFICIAL_SUBMISSION_DOC_PATHS | L2813-L2819 | 7 | list[5] | B | 单域 token/枚举/映射（check_official_submission_ecosystem）——域内 data.py | 内部：check_official_submission_ecosystem L6163；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:7051 | 保持 |
| OFFICIAL_SUBMISSION_RELEASE_DOC_PATHS | L2820-L2824 | 5 | list[3] | B | 单域 token/枚举/映射（check_official_submission_ecosystem）——域内 data.py | 内部：check_official_submission_ecosystem L6163；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:7052 | 保持 |
| OFFICIAL_SUBMISSION_REQUIRED_TOKENS | L2825-L2849 | 25 | list[23] | B | 单域 token/枚举/映射（check_official_submission_ecosystem）——域内 data.py | 内部：check_official_submission_ecosystem L6214 | P2 |
| OFFICIAL_SUBMISSION_FORBIDDEN_OVERCLAIMS | L2850-L2880 | 31 | list[27] | B | 单域 token/枚举/映射（check_official_submission_ecosystem）——域内 data.py | 内部：check_official_submission_ecosystem L6187 | P2 |
| GOVERNANCE_PACK_BOUNDARY_TOKENS | L2892-L2897 | 6 | list[4] | B | 单域 token/枚举/映射（check_governance_packs）——域内 data.py | 内部：check_governance_packs L4412 | 保持 |
| GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS | L2898-L2908 | 11 | list[9] | B | 单域 token/枚举/映射（check_governance_packs）——域内 data.py | 内部：check_governance_packs L4494 | 保持 |
| README_PACK_GUIDANCE_REQUIRED_TOKENS | L2909-L2933 | 25 | list[21] | B | 单域 token/枚举/映射（check_readme_pack_guidance）——域内 data.py | 内部：check_readme_pack_guidance L4511 | P2 |
| RUNTIME_CAPABILITY_KEYS | L5199-L5207 | 9 | tuple[6] | B | 单域 token/枚举/映射（_validate_runtime_capabilities）——域内 data.py | 内部：_validate_runtime_capabilities L5272/L5305 | 保持 |
| RUNTIME_CAPABILITY_STATUSES | L5208-L5209 | 2 | set[3] | B | 单域 token/枚举/映射（_validate_runtime_capabilities）——域内 data.py | 内部：_validate_runtime_capabilities L5278/L5280 | 保持 |
| ADAPTER_RUNTIME_CAPABILITY_POLICY | L5210-L5261 | 52 | dict[6] | C | §5.2 C 锚点：嵌套 set 值（JSON 无 set 语义）——DEC-088 | 内部：_validate_runtime_capabilities L5271；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:549 | 保持 |
| GEMINI_API_KEY_ENV_VARS | L5402-L5406 | 5 | tuple[2] | B | 单域 token/枚举/映射（_detect_gemini_env_auth_sources）——域内 data.py | 内部：_detect_gemini_env_auth_sources L5484 | 保持 |
| GEMINI_VERTEX_CONFIG_ENV_VARS | L5407-L5412 | 6 | tuple[3] | B | 零消费（内部+外部 grep 均无）——死数据候选 F-1，裁决前保持 | （零消费——F-1） | 保持 |
| GEMINI_VERTEX_CREDENTIAL_ENV_VARS | L5413-L5418 | 6 | tuple[3] | B | 单域 token/枚举/映射（_detect_gemini_env_auth_sources）——域内 data.py | 内部：_detect_gemini_env_auth_sources L5492 | 保持 |
| GEMINI_GCA_CONFIG_ENV_VARS | L5419-L5422 | 4 | tuple[1] | B | 零消费（内部+外部 grep 均无）——死数据候选 F-1，裁决前保持 | （零消费——F-1） | 保持 |
| GEMINI_GCA_CREDENTIAL_ENV_VARS | L5423-L5426 | 4 | tuple[1] | B | 单域 token/枚举/映射（_detect_gemini_env_auth_sources）——域内 data.py | 内部：_detect_gemini_env_auth_sources L5505 | 保持 |
| OPENCODE_LEGAL_DEEPSEEK_MODELS | L5606-L5607 | 2 | tuple[2] | B | 单域 token/枚举/映射（_opencode_model_scan、_validate_opencode_provider_model_preflight_claim）——域内 data.py | 内部：_opencode_model_scan L5669；_validate_opencode_provider_model_preflight_claim L5777/L5793 | 保持 |
| PROJECTION_SYNC_PATTERNS | L6574-L6604 | 31 | tuple[11] | A | 投影同步模式表（11 源），§6 投影单源策略的直接数据面 | 内部：_projection_source_files L6672；源扫描/fixture：skills/software-project-governance/infra/tests/test_release_ledger.py:666 等2处 | P1 |
| INJECTION_CONTRACT_ANCHORS | L6607-L6638 | 32 | dict[4] | A | dsh 投影注入契约锚点（4 锚×字段），外部测试 4 处消费 | 内部：check_injection_contract L6754/L6774；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:663 等4处 | P1 |
| ~~DSH_SKILLS_DISK_PATTERNS~~ | ~~L6784-L6792~~ | ~~9~~ | ~~tuple[2]~~ | — | **已退役（0.80.0 FIX-310）**——`dsh.skills` 经全量核实 dsh 核心从不读取，字段与 `check_dsh_skills_manifest` 及其数据面一并移除；候选实现中该符号出现次数 = 0，本行原引行号已为空行/无关行（DESIGN R0 F5 更正） | —— | 已退役 |
| ~~_REJECT_SECURITY_DETAIL~~ | ~~L6796-L6801~~ | ~~6~~ | ~~dict[2]~~ | — | **已退役（0.80.0 FIX-310）**——同上，随 `check_dsh_skills_manifest` 移除；候选实现中 0 次出现（DESIGN R0 F5 更正） | —— | 已退役 |
| STAGE_ORDER | L7567-L7572 | 6 | list[11] | B | 单域 token/枚举/映射（list_available_stages）——域内 data.py | 内部：list_available_stages L9444/L9451 | 保持 |
| STAGE_SKILL_ALIASES | L7573-L7579 | 7 | dict[4] | B | 单域 token/枚举/映射（normalize_stage_name）——域内 data.py | 内部：normalize_stage_name L9415 | 保持 |
| STAGE_SKILL_DIR_NAMES | L7580-L7584 | 5 | dict[2] | B | 单域 token/枚举/映射（_stage_name_from_skill_dir、stage_skill_dir_name）——域内 data.py | 内部：_stage_name_from_skill_dir L9431；stage_skill_dir_name L9421 | 保持 |
| STATUS_ICONS | L7585-L7592 | 8 | dict[4] | B | 单域 token/枚举/映射（cmd_gate、cmd_gate_check 等4函数）——域内 data.py | 内部：cmd_gate L11291；cmd_gate_check L17201；cmd_gates L11385（共4函数/4点） | 保持 |
| GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS | L8566-L8580 | 15 | tuple[12] | B | 内部零消费，消费方在域模块（_SHARED_NAMES 回取，F-5） | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:66 | 保持 |
| GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS | L8581-L8591 | 11 | tuple[8] | B | 内部零消费，消费方在域模块（_SHARED_NAMES 回取，F-5） | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:65 | 保持 |
| GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS | L8592-L8599 | 8 | tuple[5] | B | 内部零消费，消费方在域模块（_SHARED_NAMES 回取，F-5） | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:67 | 保持 |
| GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS | L8600-L8610 | 11 | tuple[7] | B | 内部零消费，消费方在域模块（_SHARED_NAMES 回取，F-5） | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:64 | 保持 |
| FIRST_RUN_DEMO_REQUIRED_FIELDS | L9248-L9269 | 22 | list[19] | B | 单域 token/枚举/映射（assert_first_run_demo_snapshot、cmd_first_run_demo）——域内 data.py | 内部：assert_first_run_demo_snapshot L9357；cmd_first_run_demo L11245 | P2 |
| FIRST_RUN_DEMO_REQUIRED_MARKERS | L9270-L9300 | 31 | list[27] | B | 单域 token/枚举/映射（assert_first_run_demo_snapshot）——域内 data.py | 内部：assert_first_run_demo_snapshot L9358 | P2 |
| _W7_TERMINAL_MARKERS | L10427-L10429 | 3 | tuple[9] | B | 单域 token/枚举/映射（_w7_terminal_assertion_positions）——域内 data.py | 内部：_w7_terminal_assertion_positions L10467 | 保持 |
| _W7_ACTIVE_MARKERS | L10430-L10430 | 1 | tuple[5] | B | 单域 token/枚举/映射（_status_is_completed_cell）——域内 data.py | 内部：_status_is_completed_cell L10538 | 保持 |
| PRODUCT_CODE_PATTERNS | L12115-L12121 | 7 | list[9] | A | 产品代码边界定义，跨 3 内部域 + review_domain 产品消费（另有局部同名遮蔽 F-4） | 内部：_is_context_product_file L8663；_is_product_code_location L12163；check_agent_activation L14102；源扫描/fixture：skills/software-project-governance/infra/tests/test_architecture_health.py:92；同名副本：skills/software-project-governance/infra/checks/review_domain.py:510 等3处 | P2 |
| _NONACTIVE_SUBSECTION_MARKERS | L12284-L12286 | 3 | tuple[4] | B | 单域 token/枚举/映射（_is_nonactive_subsection）——域内 data.py | 内部：_is_nonactive_subsection L12289 | 保持 |
| EXECUTION_PACKET_REQUIRED_FIELDS | L12789-L12798 | 10 | dict[6] | B | 单域 token/枚举/映射（_execution_packet_field_issues）——域内 data.py | 内部：_execution_packet_field_issues L12826 | 保持 |
| PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS | L12860-L12868 | 9 | dict[6] | B | 单域 token/枚举/映射（_validate_product_success_contract）——域内 data.py | 内部：_validate_product_success_contract L12913 | 保持 |
| ACCEPTANCE_CONTRACT_REQUIRED_FIELDS | L12972-L12979 | 8 | dict[5] | B | 单域 token/枚举/映射（_validate_acceptance_contract）——域内 data.py | 内部：_validate_acceptance_contract L13005 | 保持 |
| ACCEPTANCE_PASS_STATUSES | L12986-L12986 | 1 | set[5] | B | 单域 token/枚举/映射（_validate_acceptance_contract）——域内 data.py | 内部：_validate_acceptance_contract L13027 | 保持 |
| ACCEPTANCE_NOT_RUN_STATUSES | L12987-L12989 | 3 | set[6] | B | 单域 token/枚举/映射（_validate_acceptance_contract）——域内 data.py | 内部：_validate_acceptance_contract L13023 | 保持 |
| QUALITY_BUDGET_DIMENSIONS | L13070-L13077 | 8 | tuple[6] | B | 单域 token/枚举/映射（<module>、_validate_quality_budget 等3函数）——域内 data.py | 内部：<module> L13366；_validate_quality_budget L13170/L13197；build_execution_packet L13857；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:12273 等2处 | 保持 |
| QUALITY_BUDGET_PASS_STATUSES | L13078-L13078 | 1 | set[5] | B | 单域 token/枚举/映射（_validate_quality_budget）——域内 data.py | 内部：_validate_quality_budget L13194 | 保持 |
| QUALITY_BUDGET_PENDING_STATUSES | L13079-L13079 | 1 | set[6] | B | 单域 token/枚举/映射（_validate_quality_budget）——域内 data.py | 内部：_validate_quality_budget L13192 | 保持 |
| QUALITY_BUDGET_EXEMPT_STATUSES | L13080-L13080 | 1 | set[7] | B | 单域 token/枚举/映射（_validate_quality_budget）——域内 data.py | 内部：_validate_quality_budget L13188 | 保持 |
| VERTICAL_SLICE_REQUIRED_FIELDS | L13236-L13243 | 8 | tuple[6] | B | 单域 token/枚举/映射（_validate_vertical_slice）——域内 data.py | 内部：_validate_vertical_slice L13289 | 保持 |
| VERTICAL_SLICE_PASS_STATUSES | L13244-L13244 | 1 | set[5] | B | 单域 token/枚举/映射（_validate_vertical_slice）——域内 data.py | 内部：_validate_vertical_slice L13316 | 保持 |
| VERTICAL_SLICE_PENDING_STATUSES | L13245-L13245 | 1 | set[6] | B | 单域 token/枚举/映射（_validate_vertical_slice）——域内 data.py | 内部：_validate_vertical_slice L13314 | 保持 |
| DETERMINISTIC_SCAFFOLD_TYPES | L13356-L13356 | 1 | tuple[3] | B | 单域 token/枚举/映射（check_deterministic_scaffolds、main 等3函数）——域内 data.py | 内部：check_deterministic_scaffolds L13478/L13502；main L24089；render_deterministic_scaffold L13429/L13430；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:12696 等2处 | 保持 |
| DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS | L13357-L13365 | 9 | tuple[7] | B | 单域 token/枚举/映射（_validate_deterministic_scaffold_text）——域内 data.py | 内部：_validate_deterministic_scaffold_text L13450 | 保持 |
| DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS | L13387-L13418 | 32 | dict[7] | C | 含 tuple() 组合调用——Python 特有结构 | 内部：_validate_deterministic_scaffold_text L13458 | 保持 |
| INTERRUPTION_POLICY_REQUIRED_PHRASES | L13517-L13526 | 10 | tuple[7] | B | 单域 token/枚举/映射（check_interruption_policy）——域内 data.py | 内部：check_interruption_policy L13767 | 保持 |
| INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES | L13527-L13534 | 8 | tuple[5] | B | 单域 token/枚举/映射（check_interruption_policy）——域内 data.py | 内部：check_interruption_policy L13775 | 保持 |
| INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS | L13535-L13541 | 7 | tuple[5] | B | 单域 token/枚举/映射（_validate_assumption_record）——域内 data.py | 内部：_validate_assumption_record L13662 | 保持 |
| INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS | L13547-L13555 | 9 | tuple[7] | B | 单域 token/枚举/映射（_validate_interruption_policy_examples、classify_user_interruption）——域内 data.py | 内部：_validate_interruption_policy_examples L13687/L13701；classify_user_interruption L13645 | 保持 |
| INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS | L13556-L13565 | 10 | tuple[7] | B | 单域 token/枚举/映射（_validate_packet_interruption_policy）——域内 data.py | 内部：_validate_packet_interruption_policy L13729 | 保持 |
| INTERRUPTION_POLICY_DEFAULT_EXAMPLES | L13566-L13640 | 75 | list[12] | B | 单域 token/枚举/映射（check_interruption_policy）——域内 data.py | 内部：check_interruption_policy L13779；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:12901 | P2 |
| _PROFILE_GATE_COUNT | L14171-L14175 | 5 | dict[3] | B | 单域 token/枚举/映射（check_profile_consistency）——域内 data.py | 内部：check_profile_consistency L14237/L14243 | 保持 |
| _PROFILE_TASK_COLUMNS | L14176-L14185 | 10 | dict[3] | B | 单域 token/枚举/映射（_hot_task_status_index、check_profile_consistency）——域内 data.py | 内部：_hot_task_status_index L9568；check_profile_consistency L14244 | 保持 |
| M5_RECORD_DOC_DIRS | L14580-L14582 | 3 | tuple[2] | B | 单域 token/枚举/映射（_is_m5_record_doc_path、check_m5_compliance_with_record_scope）——域内 data.py | 内部：_is_m5_record_doc_path L14594；check_m5_compliance_with_record_scope L14626；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:11092；同名副本：skills/software-project-governance/infra/tests/test_verify_workflow.py:10911 | 保持 |
| _PRODUCT_GATE_LABELS | L14728-L14756 | 29 | dict[25] | B | 单域 token/枚举/映射（_print_product_gate_skipped）——域内 data.py | 内部：_print_product_gate_skipped L14759；测试：skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py:74；源扫描/fixture：skills/software-project-governance/infra/contract_matrix/generator.py:150 | P2 |
| AGENT_RUNTIME_E2E_PLATFORMS | L18244-L18246 | 3 | tuple[4] | A | e2e 平台矩阵，4 函数跨命令消费 + 测试消费 | 内部：_agent_runtime_e2e_command_matrix L18262；_is_valid_agent_runtime_workflow_agent L18772；cmd_agent_runtime_e2e L19008（共4函数/4点）；测试：skills/software-project-governance/infra/tests/test_dsh_adapter.py:558 | P2 |
| _KNOWN_VERIFY_FAILURE_SIGNATURES | L18500-L18507 | 8 | set[4] | B | 单域 token/枚举/映射（_validate_e2e_verify_known_failure）——域内 data.py | 内部：_validate_e2e_verify_known_failure L18533/L18539 | 保持 |
| EXTERNAL_PROJECT_VALIDATION_COMMANDS | L19113-L19119 | 7 | list[4] | B | 单域 token/枚举/映射（run_external_project_validation）——域内 data.py | 内部：run_external_project_validation L20252；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:10106 | 保持 |
| EXTERNAL_PROJECT_NATIVE_ENTRY_FILES | L19127-L19135 | 9 | tuple[6] | B | 单域 token/枚举/映射（_external_validation_native_entry_paths）——域内 data.py | 内部：_external_validation_native_entry_paths L19216 | 保持 |
| EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS | L19136-L19153 | 18 | tuple[3] | C | 含 re.compile 编译对象成员——DEC-088 loader 例外 | 内部：_external_validation_native_entry_diagnostics L19242 | 保持 |
| EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS | L19154-L19156 | 3 | tuple[3] | B | 单域 token/枚举/映射（_external_validation_hook_diagnostics）——域内 data.py | 内部：_external_validation_hook_diagnostics L19942；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:10225 | 保持 |
| ARCHGUARD_DEFAULT_ROOT_RESIDUE | L19294-L19296 | 3 | tuple[4] | B | 单域 token/枚举/映射（check_technical_debt）——域内 data.py | 内部：check_technical_debt L19547 | 保持 |
| ADAPTER_CLAIM_REGISTRY | L19724-L19739 | 16 | tuple[4] | C | 含 re.compile 编译对象成员——DEC-088 loader 例外 | 内部：check_readme_claim_evidence_levels L19800 | 保持 |
| _EVIDENCE_MACHINE_ROW_FAMILIES | L22227-L22228 | 2 | tuple[2] | B | 单域 token/枚举/映射（_evidence_machine_row_issues）——域内 data.py | 内部：_evidence_machine_row_issues L22330 | 保持 |

---

## 4. 补充清单——非字面量数据站点（58 站点：facts 口径 49 + AST 增补 9）

含字符串常量块、re.compile 编译对象、join/listcomp 组合表达式。这些站点属 facts"数据表"口径的组成部分（或 AST 口径增补），归宿判定同样适用 §5.2 五类——其中 30 个编译对象站点全部为 **C 类（DEC-088）**。

| 块名 | 定义行 | 行数 | 类型 | 归宿 | 理由 | 消费方（grep 实证） | 优先级 |
|---|---|---|---|---|---|---|---|
| IDENTITY_ATTESTATION_PENDING | L62-L64 | 3 | const:str | B | 单域 token/枚举/映射（_run_identity_attestation_fixture_only）——域内 data.py | 内部：_run_identity_attestation_fixture_only L20460/L20496；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:98；源扫描/fixture：skills/software-project-governance/infra/tests/test_loop_runtime_claims.py:285 等3处；同名副本：skills/software-project-governance/infra/checks/loop_runtime_claims.py:25 等2处 | 保持 |
| FIX_069_RELEASE_VERSION | L1501 | 1 | binop | E | 可由 SKILL.md frontmatter/版本投影钉扎 推导——构建期生成 | 内部：check_release_readiness_fact_source L1778/L1797 | P2 |
| FIX_069_READINESS_VERSION | L1502 | 1 | binop | E | 可由 SKILL.md frontmatter/版本投影钉扎 推导——构建期生成 | 内部：check_release_readiness_fact_source L1774/L1800 | P2 |
| FIX_087_ACTIVE_VERSION | L1848 | 1 | call:join | E | 可由 SKILL.md frontmatter/版本投影钉扎 推导——构建期生成 | 内部：check_hot_fact_source_consistency L2028/L2120 | P2 |
| FIX_087_PREVIOUS_VERSION | L1849 | 1 | call:join | E | 可由 SKILL.md frontmatter/版本投影钉扎 推导——构建期生成 | 内部：check_hot_fact_source_consistency L2029/L2042 | P2 |
| FIX_087_READINESS_VERSION | L1850 | 1 | call:join | E | 可由 SKILL.md frontmatter/版本投影钉扎 推导——构建期生成 | 内部：check_hot_fact_source_consistency L2030/L2074 | P2 |
| FIX_105_SNAPSHOT_RELEASE_VERSION_RE | L1861 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_latest_published_release_fact L1917 | P2 |
| FIX_105_PLAN_WORKFLOW_VERSION_RE | L1862 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_snapshot_fact_source_issues L1928 | P2 |
| FIX_105_SNAPSHOT_VERSION_RE | L1863 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_snapshot_fact_source_issues L1940 | P2 |
| FIX_105_SNAPSHOT_DATE_RE | L1864 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_snapshot_fact_source_issues L1947；测试：skills/software-project-governance/infra/tests/test_snapshot_freshness.py:315 等3处；源扫描/fixture：skills/software-project-governance/infra/checks/snapshot_domain.py:61 | P2 |
| LIFECYCLE_REGISTRY_ACTIVE_MODE | L2350 | 1 | const:str | B | 单域 token/枚举/映射（_parse_plan_workflow_model、build_dynamic_lifecycle_migration_preview 等4函数）——域内 data.py | 内部：_parse_plan_workflow_model L4012/L4022；build_dynamic_lifecycle_migration_preview L4208/L4251；check_dynamic_lifecycle_migration_preview L4349（共4函数/16点） | 保持 |
| LIFECYCLE_REGISTRY_DYNAMIC_MODE | L2351 | 1 | const:str | B | 单域 token/枚举/映射（_parse_plan_workflow_model、build_dynamic_lifecycle_migration_preview 等4函数）——域内 data.py | 内部：_parse_plan_workflow_model L4014/L4015；build_dynamic_lifecycle_migration_preview L4207/L4257；check_dynamic_lifecycle_migration_preview L4351（共4函数/6点） | 保持 |
| LIFECYCLE_REGISTRY_GATES | L2379 | 1 | listcomp | E | 可由 Gate 序列权威定义（现为表达式生成） 推导——构建期生成 | 内部：_check_gate_execution_registry L3279；check_lifecycle_registry L3456/L3513；测试：skills/software-project-governance/infra/tests/test_verify_workflow.py:4207 | P2 |
| GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH | L2642 | 1 | const:str | B | 单域 token/枚举/映射（check_governance_pack_status）——域内 data.py | 内部：check_governance_pack_status L5158 | 保持 |
| GEMINI_AUTH_REMEDIATION | L5427-L5435 | 9 | const:str | B | 单域 token/枚举/映射（_gemini_auth_preflight）——域内 data.py | 内部：_gemini_auth_preflight L5523 | 保持 |
| OPENCODE_PROVIDER_MODEL_REMEDIATION | L5608-L5615 | 8 | const:str | B | 单域 token/枚举/映射（_opencode_provider_model_preflight）——域内 data.py | 内部：_opencode_provider_model_preflight L5697 | 保持 |
| VERSION_LINE_ANCHOR | L6605-L6606 | 2 | const:str | E | 可由 投影生成器 @version-line 标记契约（§6 投影面） 推导——构建期生成 | 内部：<module> L6634；check_injection_contract L6762/L6765 | P2 |
| DSH_SMOKE_REAL_HOME_WRITES_RE | L6940-L6941 | 2 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：check_dsh_preset_smoke L6994 | 保持 |
| DSH_SMOKE_RESULT_PASS_RE | L6942-L6944 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：check_dsh_preset_smoke L6998 | 保持 |
| DSH_UPGRADE_REGRESSION_LABEL | L7035-L7037 | 3 | const:str | B | 单域 token/枚举/映射（run_dsh_upgrade_regression_gates）——域内 data.py | 内部：run_dsh_upgrade_regression_gates L7059/L7063 | 保持 |
| GIT_REMOTE_NAME_RE | L7355-L7357 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validated_git_remote_name L7383 | 保持 |
| FACT_BASIS_RE | L12642-L12645 | 4 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:62 | 保持 |
| UNGROUNDED_CLAIM_RE | L12646-L12649 | 4 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 外部产品：skills/software-project-governance/infra/checks/evidence_domain.py:63 | 保持 |
| SECRET_FIELD_RE | L12650 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_contains_secret_like L12724 | P2 |
| SECRET_ASSIGNMENT_RE | L12651-L12656 | 6 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_contains_secret_like L12733 | P2 |
| PRODUCT_SUCCESS_PLACEHOLDER_RE | L12869-L12872 | 4 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_is_meaningful_product_success_text L12891；_validate_acceptance_contract L13027；_validate_quality_budget L13185（共4函数/4点） | P2 |
| PRODUCT_SUCCESS_PROCESS_ONLY_RE | L12873-L12877 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_is_process_only_product_success_metric L12904 | P2 |
| PRODUCT_SUCCESS_USER_OUTCOME_RE | L12878-L12882 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_product_success_contract L12931 | P2 |
| PRODUCT_SUCCESS_RUNNABLE_RE | L12883-L12889 | 7 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_product_success_contract L12933 | P2 |
| ACCEPTANCE_RUNNABLE_COMMAND_RE | L12980-L12985 | 6 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_acceptance_contract L13015 | 保持 |
| QUALITY_BUDGET_VALIDATION_SIGNAL_RE | L13081-L13089 | 9 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_has_quality_validation_signal L13147 | P2 |
| QUALITY_BUDGET_WEAK_PROSE_RE | L13090-L13099 | 10 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_is_weak_quality_prose L13151 | P2 |
| VERTICAL_SLICE_DEMO_SIGNAL_RE | L13246-L13253 | 8 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13304 | P2 |
| VERTICAL_SLICE_USER_SIGNAL_RE | L13254-L13257 | 4 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13298 | P2 |
| VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE | L13258-L13262 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13300 | P2 |
| VERTICAL_SLICE_TECH_LAYER_RE | L13263-L13267 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13300 | P2 |
| VERTICAL_SLICE_BROAD_SCOPE_RE | L13268-L13271 | 4 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13308 | P2 |
| VERTICAL_SLICE_WEAK_PROSE_RE | L13272-L13277 | 6 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_vertical_slice L13294 | P2 |
| DETERMINISTIC_SCAFFOLD_COMMAND_RE | L13367-L13371 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_deterministic_scaffold_text L13461 | P2 |
| DETERMINISTIC_SCAFFOLD_SIGNAL_RE | L13372-L13376 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_deterministic_scaffold_text L13463 | P2 |
| DETERMINISTIC_SCAFFOLD_WEAK_RE | L13377-L13381 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_deterministic_scaffold_text L13448 | P2 |
| DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE | L13382-L13386 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_deterministic_scaffold_text L13469 | P2 |
| INTERRUPTION_POLICY_PLACEHOLDER_RE | L13542-L13546 | 5 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：_validate_assumption_record L13666 | 保持 |
| EXTERNAL_PROJECT_VALIDATION_BOUNDARY | L19120-L19126 | 7 | const:str | B | 单域 token/枚举/映射（run_external_project_validation）——域内 data.py | 内部：run_external_project_validation L20220/L20269 | 保持 |
| ARCHGUARD_SCHEMA_REL | L19291 | 1 | const:str | B | 单域 token/枚举/映射（_archguard_load_schema）——域内 data.py | 内部：_archguard_load_schema L19300 | 保持 |
| ARCHGUARD_LEDGER_REL | L19292 | 1 | const:str | B | 单域 token/枚举/映射（check_technical_debt）——域内 data.py | 内部：check_technical_debt L19610 | 保持 |
| ARCHGUARD_HOOKS_REL | L19293 | 1 | const:str | B | 单域 token/枚举/映射（check_technical_debt）——域内 data.py | 内部：check_technical_debt L19576 | 保持 |
| EVIDENCE_LEVEL_MARKER_RE | L19718-L19723 | 6 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化 | 内部：check_readme_claim_evidence_levels L19782/L19804 | 保持 |
| RECO_ROW_MARKER | L21770 | 1 | const:str | B | 单域 token/枚举/映射（_recommendation_snapshot_row_text、check_completion_recommendation）——域内 data.py | 内部：_recommendation_snapshot_row_text L21800；check_completion_recommendation L21900 | 保持 |
| _W7_TERMINAL_DATE_RE | L10431-L10433 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：_w7_terminal_assertion_positions L10497 | 保持 |
| _STATUS_ID_TOKEN_RE | L10859-L10861 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：_status_raw_dependency_ids L10877 | 保持 |
| _TASK_ID_CELL_RE | L12240-L12242 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：_plan_tracker_task_row_issues L22272；parse_current_active_tasks L12326 | 保持 |
| _ARCHIVE_FAMILY_RANGE_RE | L14385 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：_resolve_archive_task_refs L14444 | 保持 |
| _PLUGIN_PRODUCT_CHECK_IDS | L14669-L14700 | 32 | call:frozenset | C | frozenset 构造——Python 特有集合结构（DEC-088）（AST 增补：facts 正则口径未命中） | 测试：skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py:73；源扫描/fixture：skills/software-project-governance/infra/contract_matrix/generator.py:150 | 保持 |
| REQ108_RECOMMENDATION_DATE | L21766-L21769 | 4 | call:date | B | 单域 token/枚举/映射（check_completion_recommendation）——域内 data.py（AST 增补：facts 正则口径未命中） | 内部：check_completion_recommendation L21932/L21995 | 保持 |
| _RECO_TASK_ID_RE | L21772 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：_write_recommendation_snapshot L21817 | 保持 |
| _SNAPSHOT_REF_RE | L21773 | 1 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：check_completion_recommendation L21961 | 保持 |
| _TASK_ID_IN_REF_RE | L21774-L21776 | 3 | call:compile | C | re.compile 编译对象——DEC-088 loader 例外，禁裸 JSON 化（AST 增补：facts 正则口径未命中） | 内部：check_completion_recommendation L21909/L21935；源扫描/fixture：skills/software-project-governance/infra/checks/risk_domain.py:65 | 保持 |

---

## 5. DEC-088 loader 复杂度例外（C 类精确边界）

C 类共 44 站点，构成：**编译对象 38**（顶层 `= re.compile(...)` 37 + 嵌于字面量内 1 组 4 块，见下）+ **Python 特有结构 6**（frozenset 1、嵌套 set 值 1、tuple() 组合 1、join 3 归 E 前的 C 特征已注明）。

**任务点名的 FORBIDDEN_OVERCLAIMS 族边界实证**（DEC-088：含 regex 编译对象者禁裸表驱动）：

| 块 | 形态 | 归宿 |
|---|---|---|
| DYNAMIC_LIFECYCLE_MIGRATION_FORBIDDEN_OVERCLAIMS（L2364，15 行） | list 含 re.compile 成员 | **C** |
| LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS（L2459，26 行） | list 含 re.compile 成员 | **C** |
| ADAPTER_CLAIM_REGISTRY（L19724，16 行，FEAT-014） | tuple×(标签, re.compile, 提示) | **C**（registry 先例成立，但迁移需专用 loader：registry 存 pattern 字符串 + 加载期编译，loader 属 L2 端口而非数据） |
| EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS（L19136，18 行） | tuple 含 re.compile 成员 | **C** |
| 其余 FORBIDDEN_OVERCLAIMS 族（GOVERNANCE_PACK_STATUS/GOVERNANCE_PACK/OFFICIAL_SUBMISSION/HOST_CAPABILITY_CONTEXT/MAINSTREAM_AGENT_LOADING，共 5 块 138 行） | 纯字符串成员 | **B**（§5.1"简单 token 约束"——可表驱动，域内 data.py） |

---

## 6. A 类 registry 候选（12 名）——命名建议与 schema 要点

沿 `core/lifecycle-registry.json`（2,441 行）先例，建议 4 个 registry（schema_version 必备；未知字段拒绝；重复键检测；引用一致性校验；版本兼容规则）：

| 建议 registry | 纳入块（优先级） | schema 要点 |
|---|---|---|
| `core/required-artifacts.registry.json` | REQUIRED_FILES、OPTIONAL_PROJECTION_FILES、REQUIRED_SNIPPETS+WORKFLOW_SNIPPETS+PROJECTION_SNIPPETS（三表按 F-2 合并单源）（P1） | `entries[]: {path, category: required\|optional_projection\|snippet, tokens: [{token, version_pin?}]}`；校验：与 manifest.json 交叉一致（消除 EVD-630 fallback 副本）、路径存在性、重复 path、snippet 内嵌版本钉改由构建期注入（呼应 E 类） |
| `core/platform-matrix.registry.json` | MAINSTREAM_AGENT_ADAPTERS、MAINSTREAM_AGENT_LOADING_ADAPTERS、PLATFORM_ENTRY_FILES、AGENT_RUNTIME_E2E_PLATFORMS（P1/P2） | `platforms{}: {display, entry_files, readme_tokens, adapters}`；校验：4 表 platform 键集一致性（claude/codex/gemini/opencode/…对齐）、token 引用的路径存在 |
| `core/projection-contract.registry.json` | PROJECTION_SYNC_PATTERNS、INJECTION_CONTRACT_ANCHORS（P1） | `sources[]: {id, pattern/glob}` + `anchors{}: {anchor, fields[]}`；与 §6.3 CI 重生成验证挂钩；VERSION_LINE_ANCHOR（E 类）由生成器产出 |
| `core/product-scope.registry.json` | PRODUCT_CODE_PATTERNS（P2） | `patterns[]: glob`；消费方（review/context/activation 三域）统一从 registry 读，消除 review_domain.py:510 局部同名遮蔽（F-4） |

**loader 边界（DEC-088 纪律）**：凡需 `re.compile` 的成员不入 registry 数据——registry 存 pattern 字符串，编译发生在 L2 loader 端口（代码），保证 registry 保持纯声明式。§5.2 纪律原文采纳：移到 JSON ≠ 减维护 ≠ 提性能；每块迁移附消费方清单（本清单即基线）；L0 只定义 registry 形状，**不建"所有常量中心"**。

---

## 7. 遗留发现（F-1 ~ F-6，均为待裁决项，本任务零代码修改）

| ID | 发现 | 证据 | 建议 |
|---|---|---|---|
| F-1 | **死数据候选 3 块**：MAINSTREAM_AGENT_LOADING_BOUNDARY_TOKENS（L2293）、GEMINI_VERTEX_CONFIG_ENV_VARS（L5407）、GEMINI_GCA_CONFIG_ENV_VARS（L5419）——内部 AST Load、外部产品/测试、字符串引用全为零（e2e 全量拷贝除外） | §3 表"（零消费——F-1）" | 独立清理任务裁决（删除需 Developer+Reviewer 流程，不在本清单内动） |
| F-2 | **REQUIRED_SNIPPETS 死组合 + 三表漂移**：L710 占位 → L711-712 `update(WORKFLOW/PROJECTION_SNIPPETS)` → **L714 字面量整体覆盖**（组合结果被丢弃）。实体 45 键中 **5 个重复键**（去重后 40）；与 WORKFLOW 11/11 全重叠、与 PROJECTION 仅 12/21 重叠（**9 个 projection 键运行时失效**）；实体另有 17 键不在两源表中 | 附录 A 脚本输出 `[F-2]` 行；L707-714 源码 | A 类迁移时三表合并单一 registry + 构建校验（重复键/源覆盖 diff）；9 个失效键需裁决去留 |
| F-3 | facts §3.1 "192 块/2,048 行"不可复现 | §2.1 证据链 | facts 勘误为 184 块/2,323 行（块跨度口径） |
| F-4 | **同名分叉副本**：cleanup.py:46 `PLUGIN_SCOPE_DIRS`（模块级，注释自认"Keep in sync with manifest.json"——手工同步负担）；checks/loop_runtime_claims.py:25 `IDENTITY_ATTESTATION_PENDING`（模块级）；checks/review_domain.py:510 `PRODUCT_CODE_PATTERNS`（函数内局部遮蔽，与 `_SHARED_NAMES` 回取并存） | §3/§4 表"同名副本"列 | 迁移对应块时以单一权威源收编（A 类 registry / 域 data.py），消除手工同步 |
| F-5 | **_SHARED_NAMES 反向耦合面**：FACT_BASIS_RE、UNGROUNDED_CLAIM_RE、GOVERNANCE_CONTEXT_EVIDENCE_*×4 共 6 块消费方全在 evidence_domain.py（getattr 回取）；另有 8 个域模块同样模式 | §3/§4 表"外部产品"列；evidence_domain.py L59-96 | 相关块迁入对应域模块时反向耦合自然消除（演进文档 §3.4 `_vw()` 消除方案的数据面输入） |
| F-6 | **源文本扫描消费方**（迁移重命名即破坏）：checks/version.py:89 以正则扫描 `REQUIRED_SNIPPETS = {…}` 源码段做版本一致性检查；contract_matrix/generator.py:150 扫描 _PRODUCT_GATE_LABELS/_PLUGIN_PRODUCT_CHECK_IDS；tests 多处以字符串写 fixture | §3/§4 表"源扫描/fixture"列 | A/C 类迁移设计必须同步改造这 3 类消费方（读 registry 而非扫源码） |

---

## 8. 验收对照

| 验收项 | 结果 |
|---|---|
| ① 清单覆盖实测 100% + 可复现命令附录 | ✅ L0 全部 253 站点入册（主表 144 + 表 §4 58 + 附录 B 51）；附录 A 含提取/复算/对账脚本全文 |
| ② 每块六字段齐 | ✅ 名称/起止行/行数/类型/归宿类/理由 + 消费方 + 优先级（201 数据块行全覆盖） |
| ③ 消费方 grep 实证 ≥20 块列行号 | ✅ 超额：全部 201 行均带使用点行号（内部 AST Load 行号 + 外部 file:line），零消费块如实标注 F-1 |
| ④ 与 facts §3.1 对账 + 差异解释 | ✅ §2：184 复现、192 不可复现（机制假设+git 历史证据）、点名表 +3 漂移与 2 处改名 |
| ⑤ A 类候选 registry 命名与 schema 要点 | ✅ §6：4 个 registry + schema 字段/校验/loader 边界 |
| ⑥ 零产品代码修改 | ✅ 仓库内唯一写入 = 本文档；脚本仅存 %TEMP%（附录 A 收录全文） |
| ⑦ 健康零新增 | ✅ 未动产品代码/测试/治理文件，无新增风险项 |

---

## 附录 A：可复现命令与提取脚本（一次性，不入库；本附录为权威副本）

```powershell
# 0) 提取 + facts 口径复算 + 使用点分析（输出 %TEMP%\doc003_blocks.json）
python $env:TEMP\doc003_extract.py
# 1) 192/2048 复现性变体实验（基线 commit 213fbba0 与 HEAD）
python $env:TEMP\doc003_verify_192.py
# 2) git 历史块数对账（最近 30 commit 的块数曲线与增删名 delta）
python $env:TEMP\doc003_git_recon.py
# 3) 单块消费方抽查（示例：任一块名）
rg -n "\bREQUIRED_SNIPPETS\b" --type py .
```

**A.1 提取脚本全文**（`doc003_extract.py`；facts 正则、块跨度口径与 facts §1.2/§3.4 逐字一致）：

```python
import ast, json, re, sys
from pathlib import Path
ROOT = Path(r"D:\AI\agent\claude\coding\project_management_workflow")
VW = ROOT / "skills/software-project-governance/infra/verify_workflow.py"
OUT = Path(r"C:\Users\peter\AppData\Local\Temp") / "doc003_blocks.json"
src = VW.read_text(encoding="utf-8"); lines = src.splitlines(); nlines = len(lines)
tree = ast.parse(src)
FACTS = re.compile(r'^([A-Z][A-Z0-9_]{3,})\s*=\s*[\[\{\("r]')
facts_hits = [(m.group(1), i+1) for i, ln in enumerate(lines) if (m := FACTS.match(ln))]
TMAP = [(ast.List,"list"),(ast.Dict,"dict"),(ast.Set,"set"),(ast.Tuple,"tuple")]
def vtype(v):
    for t,n in TMAP:
        if isinstance(v,t): return n
    if isinstance(v, ast.Constant): return "const:"+type(v.value).__name__
    if isinstance(v, ast.Call):
        return "call:"+(getattr(v.func,"attr",None) or getattr(v.func,"id",None) or "?")
    if isinstance(v, ast.BinOp): return "binop"
    if isinstance(v, ast.DictComp): return "dictcomp"
    if isinstance(v, ast.ListComp): return "listcomp"
    return type(v).__name__
def nelem(v):
    if isinstance(v,(ast.List,ast.Tuple,ast.Set)): return len(v.elts)
    if isinstance(v,ast.Dict): return len(v.keys)
    return None
blocks=[]; top=tree.body
for idx,node in enumerate(top):
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        name,value = node.targets[0].id,node.value
    elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.value is not None:
        name,value = node.target.id,node.value
    else: continue
    nxt = top[idx+1].lineno-1 if idx+1<len(top) else nlines
    calls = sorted({(c.func.attr if isinstance(c.func,ast.Attribute) else getattr(c.func,"id","?"))
                    for c in ast.walk(value) if isinstance(c,ast.Call)})
    m = FACTS.match(lines[node.lineno-1])
    blocks.append(dict(name=name,start=node.lineno,block_end=nxt,span=nxt-node.lineno+1,
        vtype=vtype(value),nelem=nelem(value),calls=calls,
        upper=bool(re.fullmatch(r"[A-Z][A-Z0-9_]{3,}",name)),
        facts=bool(m and m.group(1)==name)))
usage={b["name"]:[] for b in blocks}
class V(ast.NodeVisitor):
    def __init__(self): self.stack=[]
    def _f(self,node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
    visit_FunctionDef=_f; visit_AsyncFunctionDef=_f
    def visit_Name(self,node):
        if node.id in usage and isinstance(node.ctx,ast.Load):
            usage[node.id].append((node.lineno,self.stack[-1] if self.stack else "<module>"))
        self.generic_visit(node)
V().visit(tree)
for b in blocks:
    b["usage"]=usage[b["name"]]
    b["consumer_funcs"]=sorted({f for _,f in usage[b["name"]]})
OUT.write_text(json.dumps(blocks,ensure_ascii=False,indent=1),encoding="utf-8")
```

**A.2 分类规则**（确定性，可由 blocks.json 复算）：E 集（9 名，§1 表）→ C（vtype==call:compile 或 calls 含 compile/frozenset/tuple/join，§5.2 C 锚点 ADAPTER_RUNTIME_CAPABILITY_POLICY 显式列入）→ A（§5.2 锚点 5 名 + A_EXTRA 7 名，理由逐名见 §3 表）→ 其余 B。优先级：A 锚点或 span≥25→P1；A 小块→P2；E→P2；C 家族正则（FIX_105/SECRET/VERTICAL_SLICE/PRODUCT_SUCCESS/DETERMINISTIC_SCAFFOLD/QUALITY_BUDGET _RE 族）→P2；B span≥20→P2；死数据（F-1 三名）与其余→保持。

**A.3 外部消费方分类**：仓内全部 `.py`（排除 verify_workflow.py 自身、`__pycache__`、`project/e2e-test-project/` 全量拷贝夹具）逐行匹配 `\b块名\b`，按行内容归类：`alias.NAME`→测试；`_vw().NAME` 或 `_SHARED_NAMES` 字符串成员或 `from verify_workflow import`→外部产品；带引号→源扫描/fixture；行首 `NAME =`→同名副本。

---

## 附录 B：范围外站点（51）——路径/标量/别名，非聚合数据块

| 块名 | 定义行 | 行数 | 类型 | 说明 |
|---|---|---|---|---|
| ROOT | L73 | 1 | Subscript | 路径/根解析常量 |
| INTERACTION_BOUNDARY_PATH | L74 | 1 | binop | 路径/根解析常量 |
| USER_INTERRUPTION_POLICY_TEMPLATE_PATH | L75-L101 | 27 | binop | 路径/根解析常量 |
| PLUGIN_ROOT | L135 | 1 | call:_resolve_plugin_root | 路径/根解析常量 |
| HOST_PROJECT_ROOT | L136-L138 | 3 | call:_resolve_host_root | 路径/根解析常量 |
| GOVERNANCE_DIR | L139 | 1 | binop | 路径/根解析常量 |
| EXECUTION_PACKET_PATH | L140-L142 | 3 | binop | 路径/根解析常量 |
| RUNTIME_READINESS_MATRIX_PATH | L2158 | 1 | binop | 路径/根解析常量 |
| MAINSTREAM_AGENT_LOADING_DOC_PATH | L2161 | 1 | binop | 路径/根解析常量 |
| FIRST_SESSION_MEASUREMENT_PATH | L2346 | 1 | binop | 路径/根解析常量 |
| GOVERNANCE_PACKS_PATH | L2348 | 1 | binop | 路径/根解析常量 |
| LIFECYCLE_REGISTRY_PATH | L2349 | 1 | binop | 路径/根解析常量 |
| FLOW_UNIT_RUNTIME_STATE_REL | L2352 | 1 | call:Path | 路径/根解析常量 |
| DYNAMIC_LIFECYCLE_MIGRATION_GUIDE_REL | L2353 | 1 | call:Path | 路径/根解析常量 |
| CAPABILITY_CONTEXT_DOC_PATH | L2720 | 1 | call:Path | 路径/根解析常量 |
| CAPABILITY_CONTEXT_TOOLS_PATH | L2721 | 1 | call:Path | 路径/根解析常量 |
| _RELEASE_GATE_TIMEOUT_DEFAULT | L5939 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RELEASE_GATE_TIMEOUT_ENV | L5940-L5942 | 3 | const:str | 标量配置（int/str/env/退出码） |
| _REJECT_REASON_TRAVERSAL | L6793 | 1 | const:str | 标量配置（int/str/env/退出码） |
| _REJECT_REASON_ABSOLUTE | L6794-L6795 | 2 | const:str | 标量配置（int/str/env/退出码） |
| GIT_LINEAGE_TIMEOUT_SECONDS | L7354 | 1 | const:int | 标量配置（int/str/env/退出码） |
| SAMPLE_PATH | L7545 | 1 | binop | 路径/根解析常量 |
| SESSION_SNAPSHOT_PATH | L7546-L7548 | 3 | binop | 路径/根解析常量 |
| GATES_PATH | L7563 | 1 | binop | 路径/根解析常量 |
| LIFECYCLE_PATH | L7564 | 1 | binop | 路径/根解析常量 |
| STAGE_SKILLS_ROOT | L7565-L7566 | 2 | binop | 路径/根解析常量 |
| EVIDENCE_PATH | L9462 | 1 | binop | 路径/根解析常量 |
| RISK_PATH | L9463 | 1 | binop | 路径/根解析常量 |
| ARCHIVE_INDEX_PATH | L9464 | 1 | binop | 路径/根解析常量 |
| ARCHIVE_TASKS_DIR | L9465 | 1 | binop | 路径/根解析常量 |
| ARCHIVE_EVIDENCE_DIR | L9466 | 1 | binop | 路径/根解析常量 |
| ARCHIVE_DECISIONS_DIR | L9467 | 1 | binop | 路径/根解析常量 |
| ARCHIVE_RISKS_DIR | L9468-L9470 | 3 | binop | 路径/根解析常量 |
| DETERMINISTIC_SCAFFOLD_DIR | L13355 | 1 | binop | 路径/根解析常量 |
| DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS | L13366 | 1 | Name | 别名赋值（指向主表块 QUALITY_BUDGET_DIMENSIONS） |
| _LEGACY_TASK_STATUS_COLUMN | L14186-L14188 | 3 | const:int | 标量配置（int/str/env/退出码） |
| _ARCHIVE_RANGE_SPAN_CAP | L14386 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _ARCHIVE_RESOLVED_STATUS | L14387-L14389 | 3 | const:str | 标量配置（int/str/env/退出码） |
| _LEGACY_SNAPSHOT_MARKER | L21771 | 1 | const:str | 标量配置（int/str/env/退出码） |
| _PLAN_TRACKER_ROW_EXPECTED_SHAPE | L22229-L22234 | 6 | const:str | 标量配置（int/str/env/退出码） |
| _WEB_INSTALL_TIMEOUT_DEFAULT | L23010 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _WEB_INSTALL_TIMEOUT_ENV | L23011-L23013 | 3 | const:str | 标量配置（int/str/env/退出码） |
| _RESOLVE_TIMEOUT_DEFAULT | L23312 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RESOLVE_TIMEOUT_ENV | L23313 | 1 | const:str | 标量配置（int/str/env/退出码） |
| _RESOLVE_ENTRY_REL | L23314 | 1 | const:str | 标量配置（int/str/env/退出码） |
| _RESOLVE_ENTRY_CANONICAL_MARKER | L23315 | 1 | const:str | 标量配置（int/str/env/退出码） |
| _RESOLVE_EXIT_OTHER | L23316 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RESOLVE_EXIT_PYTHON_MISSING | L23317 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RESOLVE_EXIT_FILE_NOT_FOUND | L23318 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RESOLVE_EXIT_TIMEOUT | L23319 | 1 | const:int | 标量配置（int/str/env/退出码） |
| _RESOLVE_EXIT_STORE_STUB | L23320-L23322 | 3 | const:int | 标量配置（int/str/env/退出码） |

*— DOC-003 交付完毕。生成：Analyst Agent（程序化提取 + 逐块实证；零产品代码修改）。*
