# 工作流工具目录

本文件是工作流第三层"基础工具/脚本层"的统一索引。所有工具独立于阶段，可被多个子工作流共用，也可被用户直接调用。

## 工具总览

| 工具 ID | 名称 | 类型 | 位置 | 触发场景 | 所属子工作流 | 可独立使用 |
|---------|------|------|------|---------|------------|----------|
| TOOL-001 | 需求澄清 checklist | checklist | `skills/requirement-clarification/SKILL.md` | 需求模糊需要结构化澄清时 | 立项（initiation） | 是 |
| TOOL-002 | 技术评审 checklist | checklist | `skills/tech-review/SKILL.md` | 架构/技术方案需要评审时 | 架构设计（architecture） | 是 |
| TOOL-003 | Code Review 规范 | standard | `skills/code-review/SKILL.md` | 代码变更需要审查时 | 开发（development） | 是 |
| TOOL-004 | 发布 checklist | checklist | `skills/release-checklist/SKILL.md` | 版本发布前做最终检查时 | 版本发布（release） | 是 |
| TOOL-005 | 回顾会议模板 | template | `skills/retro-meeting/SKILL.md` | 阶段结束或项目复盘时 | 维护（maintenance） | 是 |
| TOOL-006 | 校验脚本 | script | `infra/verify_workflow.py` | 验证工作流资产完整性时 | 全部阶段 | 是 |
| TOOL-007 | governance-update 命令 | command | `commands/governance-update.md` | 更新 平台原生入口文件 bootstrap 到最新版本（不触碰 .governance/） | 维护（maintenance） | 是 |
| TOOL-008 | 发布就绪检查 | script | `infra/verify_workflow.py check-release` | 版本发布前聚合门禁检查时 | 发布（release） | 是 |
| TOOL-009 | 主流 agent adapter 检查 | script | `infra/verify_workflow.py check-agent-adapters [--runtime]` | 验证 Claude/Codex/Gemini/opencode adapter 状态与 runtime probe 时 | 架构/发布/维护 | 是 |
| TOOL-010 | 治理归档工具 | script | `infra/archive.py` | 治理数据膨胀、版本发布后持续归档、归档迁移时 | 维护/发布 | 是 |
| TOOL-011 | 清理工具 | script | `infra/cleanup.py` | 插件升级后清理过期文件，或做 cleanup dry-run 时 | 维护 | 是 |
| TOOL-012 | Git hooks 防护网 | hook | `infra/hooks/` | commit 前后执行治理门禁、证据检查、锁清理时 | 全部阶段 | 否（由 Git 自动触发） |
| TOOL-013 | 交叉引用检查 | script | `infra/verify_workflow.py check-cross-references` | 路径迁移、文档/skill/agent 引用变更后 | 架构/维护 | 是 |
| TOOL-014 | 真实 agent runtime E2E harness | script | `infra/verify_workflow.py agent-runtime-e2e` | Claude/Codex/Gemini/opencode 真实运行环境入口验证时 | 测试/发布/维护 | 是 |
| TOOL-015 | AI execution packet 生成与检查 | script | `infra/verify_workflow.py execution-packet` + `check-governance` Check 18c | 活跃 P0/P1 任务开始前生成短上下文执行包，提交前验证短包存在且字段有效 | 全部阶段 | 是 |
| TOOL-016 | Projection sync guard | script | `infra/verify_workflow.py check-projection-sync` + `check-governance` Check 28b | workflow source、target fixture、native entry、plugin manifest 变更后 | 测试/发布/维护 | 是 |
| TOOL-017 | Hot fact-source consistency guard | script | `infra/verify_workflow.py check-hot-fact-source` + `check-governance` Check 28c | plan-tracker 热区项目配置、总览、活跃事项、路线图、依赖链和需求矩阵变更后 | 发布/维护 | 是 |
| TOOL-018 | Product Success Contract guard | script | `infra/verify_workflow.py check-product-success-contracts` + `check-governance` Check 18d | P0/P1 任务启动和关闭前检查产品成功契约 | 开发/测试/发布/维护 | 是 |
| TOOL-019 | Executable Acceptance Contract guard | script | `infra/verify_workflow.py check-acceptance-contracts` + `check-governance` Check 18e | P0/P1 任务启动和关闭前检查可运行验收契约 | 开发/测试/发布/维护 | 是 |
| TOOL-020 | Quality Budget Gate | script | `infra/verify_workflow.py check-quality-budget` + `check-governance` Check 18f | P0/P1 任务启动和关闭前检查六维质量预算 | 开发/测试/CI/CD/发布/维护 | 是 |
| TOOL-021 | Vertical Slice Delivery Packet guard | script | `infra/verify_workflow.py check-vertical-slices` + `check-governance` Check 18g | P0/P1 任务启动和关闭前检查用户可见切片、demo、scope guard 和 rollback | 开发/测试/发布/维护 | 是 |
| TOOL-022 | Weak-LLM Deterministic Scaffold generator/check | script + template | `infra/verify_workflow.py generate-deterministic-scaffold` + `check-deterministic-scaffolds` + `check-governance` Check 18h | 弱 LLM 或新项目启动时生成 PRD-lite、验收、质量预算、垂直切片和 demo checklist 脚手架 | 立项/开发/测试/发布/维护 | 是 |
| TOOL-023 | User Interruption Policy v2 guard | script + template | `infra/verify_workflow.py check-interruption-policy` + `check-governance` Check 18i | P0/P1 任务启动和关闭前检查 critical-only 打断边界、assumption record 和打断预算 | 立项/开发/测试/发布/维护 | 是 |
| TOOL-024 | Runtime Readiness Matrix guard | script + doc | `infra/verify_workflow.py check-runtime-readiness-matrix` + `check-governance` Check 28d | adapter runtime facts、公开 readiness matrix 或 release gate 变更后 | 测试/发布/维护 | 是 |
| TOOL-025 | First-Session Measurement guard | script + doc | `infra/verify_workflow.py check-first-session-measurement` + `check-governance` Check 28e | local demo / external pilot 证据或 release note boundary 变更后 | 测试/发布/维护 | 是 |
| TOOL-026 | Governance Pack Registry guard | script + registry | `infra/verify_workflow.py check-governance-packs` + `check-governance` Check 28f | composable governance pack registry、pack 文件/检查归属或 no-overclaim boundary 变更后 | 架构/测试/发布/维护 | 是 |
| TOOL-027 | Governance Context Discovery | script + command contract | `infra/verify_workflow.py governance-context` + `check-governance` Check 28g | `/governance`/status 恢复已有项目、跨会话继续工作或 context-aware resume 验收时 | 立项/测试/发布/运营/维护 | 是 |
| TOOL-028 | README Pack Guidance guard | script + README contract | `infra/verify_workflow.py check-readme-pack-guidance` + `check-governance` Check 28h | README first-run pack guidance、pack registry 或 no-overclaim boundary 变更后 | 立项/测试/发布/维护 | 是 |
| TOOL-029 | Manifest Product Artifact guard | manifest + cleanup integration | `core/manifest.json` + `infra/cleanup.py` + `infra/verify_workflow.py check-manifest-consistency` | canonical product artifact、cleanup scope 或 pack registry shipping boundary 变更后 | 测试/发布/维护 | 是 |
| TOOL-030 | Governance Pack Status Boundary guard | script + command contract + release detail | `infra/verify_workflow.py check-governance-pack-status` + `check-governance` Check 28i + `check-release` governance pack status detail | `/governance`/status Delivery Trust Snapshot pack summary、default/enabled pack wording 或 release pack no-overclaim boundary 变更后 | 测试/发布/维护 | 是 |
| TOOL-031 | Capability Context Selection Trace | script + command contract | `infra/verify_workflow.py capability-context` + `check-governance` Check 28j | 0.45.0 capability context/selection trace、受限环境能力选择诊断或 release gate 前 | 调研/架构/开发/测试/发布/维护 | 是 |
| TOOL-032 | Capability Registry guard | script + registry | `infra/verify_workflow.py check-capability-registry` + `check-governance` Check 28k | external capability registry、plugin/skill/tool/MCP/browser/sub-agent/script/fallback catalog 或 no-overclaim boundary 变更后 | 调研/架构/测试/发布/维护 | 是 |
| TOOL-033 | Host Capability Context benchmark | script + benchmark/diagnostic | `infra/verify_workflow.py check-host-capability-context` + `check-governance` Check 28l | FIX-117 restricted-environment fixtures、no network/no plugin install/no MCP/no browser/no sub-agent/local skill only、simulated Codex CLI blocked/Gemini auth blocked 诊断或 release gate 前 | 调研/架构/测试/发布/维护 | 是 |
| TOOL-034 | Official Submission Ecosystem guard | script + submission docs contract | `infra/verify_workflow.py check-official-submission-ecosystem` + `check-governance` Check 28m + `check-release --version 0.46.0` release docs detail | 0.46.0 official submission docs、ecosystem positioning、comparison、migration guide、examples 或 no-overclaim boundary 变更后 | 调研/发布/维护 | 是 |
| TOOL-035 | Mainstream Agent Loading guard | script + README/adapter docs contract | `infra/verify_workflow.py check-mainstream-agent-loading` + `check-governance` Check 28n | 0.47.0 README mainstream loading matrix、Tier 1 adapter loading guide、Tier 2 compatibility/research rows 或 no-overclaim boundary 变更后 | 调研/测试/发布/维护 | 是 |
| TOOL-036 | External Project Validation harness | script + temporary workspace | `infra/verify_workflow.py external-project-validation --target <path> --fail-on-issues` | 1.0.0 前外部项目验证、VAL-001 复跑、真实外部 target 的完整 workflow surface 验证 | 测试/发布/维护 | 是 |
| TOOL-037 | Dynamic Lifecycle Registry guard | script + registry | `infra/verify_workflow.py check-lifecycle-registry` + `core/lifecycle-registry.json` | 0.51.0 lifecycle registry、classic-phase-gate 兼容 preset、flow unit schema 或 schema-only/no-overclaim 边界变更后 | 架构/测试/发布/维护 | 是 |
| TOOL-038 | Flow Unit Runtime hot-state guard | script + optional hot state | `infra/verify_workflow.py check-flow-unit-runtime [--fixture <path>] --fail-on-issues` + optional `.governance/flow-unit-runtime.json` | 0.52.0 flow-unit runtime visibility、active lanes、per-unit gate state、loop counters、blocked downstream units 或 rollup status 变更后 | 架构/测试/发布/维护 | 是 |
| TOOL-039 | Project-Type Gate Presets guard | script + registry presets | `infra/verify_workflow.py check-lifecycle-registry --fail-on-issues` + `core/lifecycle-registry.json` `project_type_gate_presets` | 0.53.0 project type gate presets、profile/project-type 正交边界、默认 packs、质量预算、验收模板、release checks、gate policy 或 gate standards 变更后 | 架构/测试/发布/维护 | 是 |
| TOOL-040 | Classic Gate Execution Registry guard | script + registry execution metadata | `infra/verify_workflow.py check-lifecycle-registry --fail-on-issues` + `infra/verify_workflow.py gate-check <G1-G11>` + `core/lifecycle-registry.json` `gate_execution_registry` | 0.54.0 classic G1-G11 registry execution、gate checks、evidence query、automation metadata、human-confirmation policy、severity 或 project-type overrides 变更后 | 架构/测试/发布/维护 | 是 |
| TOOL-041 | Dynamic Lifecycle Migration dry-run preview | script + migration guide | `infra/verify_workflow.py dynamic-lifecycle-migration --target <path> --dry-run` + `docs/migration/dynamic-flow-gate-migration-0.55.0.md` | 0.55.0 classic-phase-gate 到 dynamic-flow-gate 的只读迁移预览、plan/evidence 保留检查、blocked checks 和 no-overclaim boundary 验证后 | 架构/测试/发布/维护 | 是 |
| TOOL-043 | ArchGuard Architecture Health | CLI check (advisory) | `infra/verify_workflow.py check-architecture-health` + `core/architecture-health.json` | 0.58.0 模块/函数/模块常量大小阈值 + 重复常量检测（3 级 PASS/WARN/ERROR，advisory 不阻断 release） | 架构/维护 | 是 |
| TOOL-044 | ArchGuard Duplicate Code | CLI check (advisory) | `infra/verify_workflow.py check-duplicate-code` | 0.58.0 source/projection 语义重复检测（normalize 换行符 + 忽略空白，避免 CRLF/LF 误判） | 架构/维护 | 是 |
| TOOL-045 | ArchGuard Technical Debt | CLI check (advisory) | `infra/verify_workflow.py check-technical-debt` + `core/technical-debt-ledger.md` | 0.58.0 根目录游离脚本/历史 release 文档/hooks 内容漂移/技术债登记交叉验证 | 维护 | 是 |
| TOOL-046 | ArchGuard Complexity | CLI check (advisory) | `infra/verify_workflow.py check-complexity` | 0.58.0 圈复杂度（line-based proxy，AST 留 0.59.0+），advisory | 架构/维护 | 是 |
| TOOL-047 | Declarative Release Ledger | schema + CLI | `core/releases/` + `infra/verify_workflow.py release-ledger` | 候选/发布 commit、tag、remote、historical trust 与 artifact ledger 验证 | 发布/维护 | 是 |
| TOOL-048 | Artifact Projection Generator | registry + CLI | `core/version-projections.json` + `infra/verify_workflow.py release-projection [--write]` | SKILL frontmatter 版本投影检查与原子写入 | 发布/维护 | 是 |
| TOOL-049 | Optional Quality Tool Probe | CLI probe | `infra/verify_workflow.py quality-tools` | Ruff/mypy 可用性与版本探测，结构化 PASS/NOT_RUN/FAIL | 开发/测试/发布/维护 | 是 |
| TOOL-052 | DSH Preset Schema Compat Guard | CLI check（可独立运行） | `infra/dsh_compat.py` + `infra/verify_workflow.py check-dsh-preset-compat`（`check-governance` Check 28v） | 用**解析态** dsh 插件集的 loader YAML 方言 + loader `evaluate` + cordis `resolveConfig` 逐行校验每个 preset 组合（含 `group` 递归、`disabled` 祖先继承语义），行级报告 row id + 模块名 + schema 原文消息；无 node / 无可解析插件集 → NOT_RUN（可选工具政策，不计 issues） | 开发/测试/发布/维护 | 是 |
| TOOL-053 | 治理成本埋点报告 | CLI report（只读扫描） | `infra/governance_cost.py` + `infra/verify_workflow.py governance-cost-report --sessions-root <dir> [--workspace <str>] --format json\|text` | 0.84.0 治理成本可观测（FEAT-032/AUDIT-154 切片 A-1）：解析 DSH 会话轨迹（session.v3.jsonl.zstd），机读输出每轮 TTFA（用户消息→首次 ask_user_question）、进入实质工作时间（首次 ask→首个非治理工具调用或轮结束）、token 分项（in/cache/out 累计请求量）、工具时长分布、LLM vs 工具时间占比；`--sessions-root` 缺省取 `DSH_SESSIONS_ROOT` 环境变量，两者皆缺 → fail-closed（exit 2）；zstandard 缺失 → 清晰报错不静默降级；对用户会话目录仅只读 | 架构/开发/测试/维护 | 是 |
| TOOL-054 | 只读 bootstrap 聚合命令 | CLI aggregate（只读） | `infra/bootstrap_aggregate.py` + `infra/verify_workflow.py governance-bootstrap [--budget-ms N] [--format json\|text] [--profile lite\|standard\|strict]` | 0.84.0 bootstrap 聚合快路径（FEAT-033/AUDIT-154 切片 A-2）：单次输出 resolve envelope（复用 resolve_entry）+ 状态投影（项目配置/Gate 摘要/任务统计/活跃风险/最近活动）+ 候选（复用 task-priority 轻量路径，空推荐带结构化空原因）+ migration 版本比较标志（仅标志不执行）+ health（v1 恒 `deferred`——未做健康检查，指向 check-governance）+ next_actions；`--budget-ms`（默认 3000）超时 fail-safe 返回已完成部分 + `deferred` 明示未完成范围；零 .governance 写入、零 git 写入、零子进程；JSON ≤8KB 投影，text ≤40 行 | 立项/架构/开发/测试/发布/运营/维护 | 是 |
| TOOL-055 | 注入面体积预算门禁 | CLI check（可独立运行） | `infra/verify_workflow.py check-injection-budget [--budget-tokens N] [--profile lightweight\|standard\|strict] [--format text\|json]`（`check-governance` Check 33 内联同报） | 0.84.0 治理自身资源预算门禁（FEAT-039/AUDIT-154 切片 A-8）：对**实际加载集合**（多文件求和，非单文件——拆分文件不能绕过预算）定价并裁决；分项输出每面 bytes/chars/CJK/token（预算价 + DSH host 价）；口径 = CJK 1 tok/char、ASCII ceil(chars/4)、其他 ceil(chars*2/5)，**不引外部 tokenizer 依赖**（假设在 `--format json` 的 `tokenizer` 字段与 help 中文档化）；resident 层（persona + 所选 profile 入口模板 + 双入口薄指针 + agent-instructions）默认预算 6000 tok（**hard 硬门**，FEAT-050/DEC-211③ 翻 hard；arch 目标 4K），超限即显式 issue + FAIL（EVD-1104 瘦身后三 profile 4,216/5,694/5,966 全达标，当前树零超预算；未来增长 fail-closed）；skill 层独立预算 **16,000 tok**（FEAT-052：实测基线 14,456——FEAT-041 progressive disclosure 明细迁移的设计性增长；姿态保持 report-only 数据字段化——不翻硬门，翻硬为 0.86.0+ 候选经 FEAT-047 BaselineMetadata 承载）；command 层按需加载单独计量（report-only，实测 3,466 tok 远低于 resident 线，无独立数值需求）；任一 canonical 源解析失败 → 显式 issue + fail-closed；tool-return 面登记 FEAT-033 `MAX_JSON_BYTES=8192`（引用断言，不重实现） | 架构/开发/测试/发布/维护 | 是 |
| TOOL-056 | 行为灰度开关 / legacy 回退通道 | 模块 + CLI 面（只读） | `infra/behavior_profile.py` + `infra/verify_workflow.py governance-bootstrap` 的 `behavior` 面 | 0.84.0 切片 A 行为变更回退通道（FEAT-040/AUDIT-154 切片 A-9）：`GOVERNANCE_LEGACY_BEHAVIOR=1` 或 plan-tracker `behavior_profile: legacy` → 只回退性能/编排行为（快路径/首次交互前置/≤8 字段视图/Scenario 按需）；**安全语义不回退**（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达）——边界为机检契约（`revert_contract_issues`）非注释 | 全部阶段 | 是 |
| TOOL-057 | Governance Write Guard（直写路径守卫 + 行族对账 + 违规持久状态机） | CLI check（5 面） | `infra/verify_workflow.py governance-write-guard`（`check_governance_write_shapes`；状态机实体 `infra/write_guard_state.py`） | Coordinator 直写 `.governance/` 后一次性复跑：面 1 plan-tracker 任务行形状（M1 签名）/面 2 evidence-log 机器行族列数+ID（DEC-168）/面 3 agent-locks schema（Check 26）/面 4 execution-packets 结构（Check 18c）/面 5 **受管行族对账**（FEAT-057：EVD/DEC/REVIEW 行 + 任务状态列 + `*.ops.jsonl` receipt 台账的行级变更凭 `机器写入：governance-store` 标记、task_row_update `〔op-…〕` 锚、receipt `operation_id` 对账——无机器凭证 → WARN 响亮披露 `unattributed row change — use governance_store/task_row_update`，BLOCK 升级留 0.87）。首跑建立 `.governance/.write-guard-state.json` 状态基线（amnesty——存量行不追溯，零 WARN）；状态文件为守卫自身工件非修复（治理记录零写入零改写语义不变）；对账基线仅在 CLI 路径落盘，probe 调用（contract-matrix/测试）零写入。**FEAT-060（0.88.0 B1）**：CLI 路径检测的违规额外持久化进 `.governance/.write-guard-violations.json` 违规状态机（12 规范字段 + 六规则 + 消费权台账 + ops 可恢复消费事务；消费权闭集 = guard CLI，hook 经 CLI 消费；健康宿主零足迹）——WARN 输出字节不变，详见工具详情 TOOL-057 节 | 全部阶段（每次直写后） | 是 |

## 工具详情

### TOOL-001：需求澄清 checklist

- **文件**：`skills/requirement-clarification/SKILL.md`
- **子命令**：通过 Claude Code slash command `/requirement-clarification` 调用，或直接在上下文中加载
- **输入**：用户对需求的原始描述
- **输出**：经过 5 问法 + IN/OUT 边界分析后的结构化需求文档
- **触发条件**：用户表述模糊、需求边界不清、缺乏量化验收标准
- **依赖**：无
- **被以下子工作流使用**：立项（initiation）

### TOOL-002：技术评审 checklist

- **文件**：`skills/tech-review/SKILL.md`
- **子命令**：通过 Claude Code slash command `/tech-review-checklist` 调用，或直接在上下文中加载
- **输入**：待评审的技术方案或架构设计文档
- **输出**：结构化的评审结论（通过/有条件通过/需修改）+ 具体评审意见
- **触发条件**：架构设计完成、技术选型确定、重大技术决策做出后
- **依赖**：无
- **被以下子工作流使用**：架构设计（architecture）、技术选型（selection）

### TOOL-003：Code Review 规范

- **文件**：`skills/code-review/SKILL.md`
- **子命令**：通过 Claude Code slash command `/code-review-standard` 调用，或直接在上下文中加载
- **输入**：待审查的代码变更（diff 或 PR）
- **输出**：分级审查结论（P0 阻塞 / P1 关键 / P2 建议）+ 逐条审查意见
- **触发条件**：代码变更提交 Review、合并前检查
- **依赖**：无
- **被以下子工作流使用**：开发（development）

### TOOL-004：发布 checklist

- **文件**：`skills/release-checklist/SKILL.md`
- **子命令**：通过 Claude Code slash command `/release-checklist` 调用，或直接在上下文中加载
- **输入**：当前版本的变更清单和测试报告
- **输出**：逐项检查结论（通过/未通过/不适用）+ 发布建议
- **触发条件**：版本发布前
- **依赖**：测试报告（子工作流 testing）
- **被以下子工作流使用**：版本发布（release）

### TOOL-005：回顾会议模板

- **文件**：`skills/retro-meeting/SKILL.md`
- **子命令**：通过 Claude Code slash command `/retro-meeting` 调用，或直接在上下文中加载
- **输入**：本阶段/本轮的产出物和治理记录
- **输出**：结构化的回顾结论（目标回顾、结果评估、根因分析、改进计划）
- **触发条件**：阶段完成、项目里程碑、定期回顾
- **依赖**：本阶段的 evidence-log、decision-log、risk-log
- **被以下子工作流使用**：维护（maintenance），也可被任意阶段结束时调用

### TOOL-006：校验脚本

- **文件**：`infra/verify_workflow.py`
- **子命令**：`verify`（全量校验）、`status`（治理状态摘要）、`gate <G1-G11>`（Gate 详情）、`gate-check <G1-G11>`（registry-backed Gate 自动判定）、`gates`（全部 Gate 状态）、`stage <stage-id>`（阶段状态）、`stages`（全部阶段状态）、`check-governance --fail-on-issues`（治理健康检查）、`e2e-check`（E2E proxy + fixture 分层检查）、`external-project-validation --target <path> --fail-on-issues`（外部项目临时验证 workspace）、`check-version-consistency`、`check-manifest-consistency`、`check-governance-packs`、`check-capability-registry`、`check-lifecycle-registry`、`check-host-capability-context`、`check-official-submission-ecosystem`、`check-readme-pack-guidance`、`check-governance-pack-status`、`capability-context`、`check-deterministic-scaffolds`、`check-interruption-policy`、`generate-deterministic-scaffold`、`check-locks`、`check-archive-integrity`
- **输入**：无（自动读取项目文件）
- **输出**：校验结果（PASSED/FAILED）+ 治理状态摘要
- **触发条件**：工作流资产变更后、Gate 检查时、定期巡检
- **依赖**：项目需已完成 `governance-init`
- **被以下子工作流使用**：全部阶段

### TOOL-007：governance-update 命令

- **文件**：`commands/governance-update.md`
- **子命令**：`/governance update`
- **输入**：当前仓库中的平台原生入口文件和工作流版本
- **输出**：升级后的 bootstrap 段落和升级摘要
- **触发条件**：插件更新后、bootstrap 模板变化后、用户显式要求更新入口文件
- **依赖**：`commands/governance-init.md` 中的 canonical bootstrap 模板
- **被以下子工作流使用**：维护（maintenance）

### TOOL-008：发布就绪检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-release [--version X.Y.Z] [--require-changelog] [--runtime-adapters] [--skip-execution-gates] [--lineage-mode candidate|released] [--release-commit COMMIT] [--lineage-remote REMOTE]`
- **输入**：可选版本号；可选要求 CHANGELOG 已包含该版本；可选本机 agent runtime probe；默认执行发布门禁命令。`candidate` 是提交/tag 创建前的兼容模式；`released` 要求显式 release commit，并验证本地 tag、tag 指向和 remote tag 状态。
- **输出**：发布就绪检查结果（PASSED/FAILED）+ 版本一致性、release fact source、release lineage、agent adapter、交叉引用、归档完整性、`verify`、`check-governance --fail-on-issues`、`e2e-check`、unittest 分项结果
- **触发条件**：`stage-release` 执行发布 checklist 时；0.35.0 及后续版本发布前
- **依赖**：`check_version_consistency()`、`check_release_readiness_fact_source()`、`check_agent_adapter_contract()`、`check_cross_references()`、`check_archive_integrity()`、`verify_workflow.py verify`、`check-governance --fail-on-issues`、`e2e-check`、`python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- **降级口径**：`--skip-execution-gates` 仅用于诊断静态聚合，不作为正式发布 checklist 通过证据；`candidate` 通过也不证明 tag 已创建或推送，发布完成后必须以 `--lineage-mode released --release-commit <commit>` 复验。
- **被以下子工作流使用**：版本发布（release）

### TOOL-009：主流 agent adapter 检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-agent-adapters [--runtime]`
- **输入**：adapter manifest/README/launcher；`--runtime` 时读取本机 PATH 中的 agent CLI
- **输出**：Claude/Codex/Gemini/opencode 的 STATIC/PASS/UNSUPPORTED/FAIL 状态
- **触发条件**：适配层变更后、发布前检查、主流 agent runtime 证据刷新时
- **依赖**：`adapters/{claude,codex,gemini,opencode}/adapter-manifest.json`
- **被以下子工作流使用**：架构设计（architecture）、版本发布（release）、维护（maintenance）

### TOOL-010：治理归档工具

- **文件**：`infra/archive.py`
- **子命令**：`migrate --auto [--dry-run]`
- **输入**：`.governance/plan-tracker.md`、`.governance/evidence-log.md`、`.governance/archive/index.md`
- **输出**：归档迁移摘要、归档后的 task/evidence 文件、索引更新
- **触发条件**：插件升级归档迁移、版本发布后持续归档、plan-tracker 膨胀到阈值时
- **依赖**：`verify_workflow.py check-archive-integrity`
- **被以下子工作流使用**：版本发布（release）、维护（maintenance）

### TOOL-011：清理工具

- **文件**：`infra/cleanup.py`
- **子命令**：`--dry-run --json`；升级流程中可执行实际清理
- **输入**：`manifest.json` canonical 文件集合与当前工作区文件
- **输出**：清理候选或已清理文件摘要
- **触发条件**：插件升级后、manifest 变化后、需要检查过期文件残留时
- **依赖**：`skills/software-project-governance/core/manifest.json`
- **被以下子工作流使用**：维护（maintenance）

### TOOL-012：Git hooks 防护网

- **文件**：`infra/hooks/prepare-commit-msg`、`infra/hooks/pre-commit`、`infra/hooks/commit-msg`、`infra/hooks/post-commit`
- **触发方式**：Git 自动触发
- **输入**：staged diff、commit message、治理记录、agent locks
- **输出**：阻断型错误或允许型治理提醒；post-commit 锁清理
- **触发条件**：每次 commit
- **依赖**：`.governance/evidence-log.md`、`.governance/plan-tracker.md`、`.governance/agent-locks.json`
- **被以下子工作流使用**：全部阶段

### TOOL-013：交叉引用检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-cross-references [--fail-on-issues]`
- **输入**：`skills/software-project-governance/`、`commands/`、`agents/` 下的 Markdown/Python 引用
- **输出**：dangling reference、deprecated path、circular reference 检查结果
- **触发条件**：路径迁移、文档重构、skill/agent/command 引用变更后
- **依赖**：无外部依赖
- **被以下子工作流使用**：架构设计（architecture）、维护（maintenance）

### TOOL-014：真实 agent runtime E2E harness

- **文件**：`infra/verify_workflow.py`
- **子命令**：`agent-runtime-e2e [--target PATH] [--timeout SECONDS] [--agent claude|codex|gemini|opencode]`
- **输入**：`project/e2e-test-project` 或指定 target cwd；本机 PATH 中的 Claude/Codex/Gemini/opencode CLI
- **输出**：每个平台的 `PASS` / `BLOCKED` / `FAIL` 状态、执行命令、cwd、blocked_reason 和截断日志摘要
- **触发条件**：主流 agent 适配状态刷新、发布前真实 runtime 验证、外部环境诊断
- **依赖**：`project/e2e-test-project` 四平台 native entry fixture；对应 agent CLI 与本机认证/模型配置
- **PASS schema**：真实 agent 输出必须包含 `E2E_PLATFORM=<platform>; E2E_AGENT=<workflow role>; E2E_STAGE=<current stage>; E2E_MODE=<trigger x permission>`；platform 必须匹配当前 CLI，workflow role/stage 不得为占位，mode 必须是合法触发模式 × 权限模式
- **判定口径**：`BLOCKED` 表示环境或 agent runtime 配置阻塞，不等于 harness 失败；`FAIL` 表示未分类失败或结构化 PASS schema 不完整，需要修复 harness 或入口适配
- **被以下子工作流使用**：测试（testing）、版本发布（release）、维护（maintenance）

### TOOL-015：AI execution packet 生成与检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`execution-packet [--write] [--task TASK_ID]`
- **输入**：`.governance/plan-tracker.md` 的 `## 当前活跃事项`
- **输出**：`.governance/execution-packets.json`，包含每个活跃 P0/P1 任务的 `goal`、`allowed_change_scope`、`required_evidence`、`next_commands`、`done_definition`
- **触发条件**：每个 P0/P1 任务启动前；`check-governance` Check 18c 发现缺包或短包无效时
- **依赖**：`check-governance`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：全部阶段，尤其是维护、开发、发布

### TOOL-016：Projection sync guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-projection-sync [--fail-on-issues]`
- **输入**：source `skills/**`、`commands/**`、`agents/**`；target fixture `project/e2e-test-project`；`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`、core manifest 和 target plan-tracker 版本声明
- **输出**：source 版本、镜像文件检查数量、版本声明检查结果、target fixture drift/missing file/native entry marker 缺失问题
- **触发条件**：修改 workflow source、target fixture、native entry、plugin manifest 后；发布前 release readiness 门禁
- **依赖**：`check-governance` Check 28b、`check-release` projection sync detail、`project/e2e-test-project`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-017：Hot fact-source consistency guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-hot-fact-source [--fail-on-issues]`
- **输入**：`.governance/plan-tracker.md` 热区：项目配置、项目总览、当前活跃事项、`1.0.0 依赖链`、版本规划、需求跟踪矩阵
- **输出**：版本阶段叙事、活跃 task 状态、依赖链 blocker、需求矩阵交付状态之间的不一致问题
- **触发条件**：更新当前版本任务状态、路线图、1.0.0 依赖链、需求矩阵或发布前事实源复核时
- **依赖**：`check-governance` Check 28c、`check-release` hot fact source detail
- **被以下子工作流使用**：发布（release）、维护（maintenance）

### TOOL-018：Product Success Contract guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-product-success-contracts [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `product_success_contract`
- **输出**：每个活跃任务的用户、JTBD、非目标、成功指标、竞争基线和完成定义完整性检查结果；拒绝占位草案和仅 governance/review/evidence 完成的流程型指标
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前产品成功门禁复核时
- **依赖**：`check-governance` Check 18d、`core/templates/product-success-contract.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-019：Executable Acceptance Contract guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-acceptance-contracts [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `acceptance_contract`
- **输出**：每个活跃任务的验收场景、可运行命令、预期输出、最近运行结果和 demo 证据检查结果；拒绝占位草案、不可运行命令和未 PASS 的最近运行结果
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前验收门禁复核时
- **依赖**：`check-governance` Check 18e、`core/templates/executable-acceptance-contract.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-020：Quality Budget Gate

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-quality-budget [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `quality_budget`
- **输出**：每个活跃任务的 performance、reliability、security、accessibility、ux、maintainability 六维质量预算检查结果；拒绝占位草案、缺维度、失败状态和无理由例外
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前质量门禁复核时
- **依赖**：`check-governance` Check 18f、`core/templates/quality-budget.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、CI/CD、发布（release）、维护（maintenance）

### TOOL-021：Vertical Slice Delivery Packet guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-vertical-slices [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `vertical_slice`
- **输出**：每个活跃任务的用户可见切片、demo 路径、范围边界、回滚方案、状态和证据检查结果；拒绝占位草案、纯技术层切片、不可演示路径、全仓范围和 review/prose-only 证据
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前垂直切片门禁复核时
- **依赖**：`check-governance` Check 18g、`core/templates/vertical-slice-delivery-packet.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-022：Weak-LLM Deterministic Scaffold generator/check

- **文件**：`infra/verify_workflow.py` + `core/templates/deterministic-scaffolds/`
- **子命令**：`generate-deterministic-scaffold --type web-app|cli-tool|workflow-plugin [--output PATH]`；`check-deterministic-scaffolds [--fail-on-issues]`
- **输入**：项目类型；scaffold 模板库中的 `index.md`、`web-app.md`、`cli-tool.md`、`workflow-plugin.md`
- **输出**：可直接放入目标项目的 PRD-lite / Product Success Contract / Executable Acceptance / Quality Budget / Vertical Slice / Demo Checklist / Tooling 脚手架；模板完整性检查结果
- **触发条件**：弱 LLM 执行新项目、常见项目类型启动、P0/P1 任务缺产品成功路径、发布前确认 0.39.0 产品成功门禁工具库完整性
- **依赖**：`check-governance` Check 18h、`core/templates/deterministic-scaffolds/index.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-023：User Interruption Policy v2 guard

- **文件**：`infra/verify_workflow.py` + `core/templates/user-interruption-policy.md` + `references/interaction-boundary.md`
- **子命令**：`check-interruption-policy [--fail-on-issues]`；alias `check-user-interruption-policy [--fail-on-issues]`
- **输入**：interaction boundary 规则、用户打断策略模板、`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `interruption_policy`
- **输出**：critical-only 策略完整性、产品意图/验收标准/不可逆决策分类 examples、assumption record 五字段和 interruption budget 检查结果
- **触发条件**：P0/P1 任务启动前、任务关闭前、用户反馈打断过多或关键处漏问、发布前 0.39.0 产品成功门禁复核时
- **依赖**：`check-governance` Check 18i、`core/templates/execution-packet.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-024：Runtime Readiness Matrix guard

- **文件**：`infra/verify_workflow.py` + `docs/requirements/runtime-readiness-matrix-0.43.0.md`
- **子命令**：`check-runtime-readiness-matrix [--fail-on-issues]`
- **输入**：`adapters/claude|codex|gemini|opencode/adapter-manifest.json`、公开 runtime/readiness matrix 文档
- **输出**：公开矩阵是否覆盖 Claude/Codex/Gemini/opencode/Cursor/Copilot，是否与 adapter manifest 的 PASS/BLOCKED/DEGRADED、version command、blocked reason、workflow closure 和 no-overclaim 边界一致
- **触发条件**：更新 adapter runtime facts、发布 readiness 文档、0.43.0 Cross-Harness E2E Closure 或 release gate 前
- **依赖**：`check-governance` Check 28d、`check-release` runtime readiness matrix detail、`check-agent-adapters --runtime`、`agent-runtime-e2e`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-025：First-Session Measurement guard

- **文件**：`infra/verify_workflow.py` + `docs/requirements/first-session-measurement-0.43.0.md`
- **子命令**：`check-first-session-measurement [--fail-on-issues]`
- **输入**：first-session measurement evidence 文档中的 `Measurement Status` 表、local demo 命令和 external pilot 状态
- **输出**：local_demo 是否只声明 LOCAL_DEMO_ONLY PASS，external_pilot 是否只使用 PASS/BLOCKED/NOT_MEASURED 且不把 `first-run-demo` local proof 包装成外部 pilot PASS，release note no-overclaim boundary 是否完整
- **触发条件**：更新 5-minute first-session 证据、发布 0.43.0 release notes、外部 pilot 测量状态变化或 release gate 前
- **依赖**：`check-governance` Check 28e、`check-release` first-session measurement detail、`first-run-demo --assert-snapshot`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-026：Governance Pack Registry guard

- **文件**：`infra/verify_workflow.py` + `core/governance-packs.json`
- **子命令**：`check-governance-packs [--fail-on-issues]`
- **输入**：canonical governance pack registry 中的 pack ID、profile、capability、file reference、check reference、validation command 和 no-overclaim boundary
- **输出**：`governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise` 是否完整；引用文件和引用检查是否存在；是否出现 official approval / marketplace approval / 1.0.0 production-ready 等过度声明
- **触发条件**：新增或调整 composable governance pack、改变文件/检查归属、发布 0.44.0 pack boundary 或 release gate 前
- **依赖**：`check-governance` Check 28f、`core/manifest.json`
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-027：Governance Context Discovery

- **文件**：`infra/verify_workflow.py` + `/governance` 与 `/governance-status` command contracts
- **子命令**：`governance-context [--fixture <project-root>] [--fail-on-issues]`
- **输入**：`.governance/plan-tracker.md` active rows/version roadmap、`.governance/session-snapshot.md` carry-over/next priorities、`.governance/risk-log.md` open risks、目标项目命令契约文档
- **输出**：fact-backed unfinished work handoff：detected item、source facts、blocker state、next action、auto-continue 和 interrupt boundary；无事实时明确 `not found` 且 `do not invent`
- **触发条件**：`/governance`/status 恢复已有项目、跨会话继续工作、0.44.0 context-aware resume 验收或 release gate 前
- **依赖**：`check-governance` Check 28g、Delivery Trust Snapshot、`first-run-demo --assert-snapshot`
- **被以下子工作流使用**：立项（initiation）、测试（testing）、发布（release）、运营（operations）、维护（maintenance）

### TOOL-028：README Pack Guidance guard

- **文件**：`infra/verify_workflow.py` + `README.md` + `core/governance-packs.json`
- **子命令**：`check-readme-pack-guidance [--fail-on-issues]`
- **输入**：README first-run preset guidance、0.44.0 pack ID、profile vs pack 边界和 no-overclaim wording
- **输出**：README 是否把 `lite`/`standard`/`strict` 映射到 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`，并明确 packs 不替代 profiles、pack enabled 不等于 evidence/review/quality/release/approval/runtime PASS
- **触发条件**：更新 README first-run 文案、调整 pack registry、发布 0.44.0 pack boundary 或 release gate 前
- **依赖**：`check-governance` Check 28h、`check-governance-packs`
- **被以下子工作流使用**：立项（initiation）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-029：Manifest Product Artifact guard

- **文件**：`core/manifest.json` + `infra/cleanup.py` + `infra/verify_workflow.py`
- **子命令**：`check-manifest-consistency [--fail-on-issues]`
- **输入**：`canonical_product_artifacts.entries`、`cleanup_scope.directories`、tracked git file set、product file entries
- **输出**：critical product artifact 是否显式声明为 product file、是否存在、是否由 git 跟踪、是否带验证命令；cleanup 扫描范围是否由 manifest 声明并与 verifier plugin scope 同步
- **触发条件**：新增或迁移 pack registry、改变 manifest product entries、调整 cleanup scope、发布 0.44.0 pack boundary 或 release gate 前
- **依赖**：`core/governance-packs.json`、`check-governance-packs`、`infra/cleanup.py`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-030：Governance Pack Status Boundary guard

- **文件**：`infra/verify_workflow.py` + source/fixture `/governance-status` and `/governance` command contracts + `docs/requirements/composable-governance-packs-0.44.0.md`
- **子命令**：`check-governance-pack-status [--fail-on-issues]`
- **输入**：Delivery Trust Snapshot pack summary/default packs/enabled packs/pack boundary contract，以及 0.44.0 release pack boundary/no-overclaim detail
- **输出**：status/release surfaces 是否说明 packs 是 capability modules、profiles 是 intensity presets；是否展示 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`；是否阻断 pack enabled/pack membership 被宣称为 evidence、review、quality gate、release gate、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready
- **触发条件**：修改 `/governance`、`/governance-status`、0.44.0 pack requirements、release readiness/check-release detail 或 pack boundary wording 后
- **依赖**：`check-governance` Check 28i、`check-release` governance pack status detail、`core/governance-packs.json`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-031：Capability Context Selection Trace

- **文件**：`infra/verify_workflow.py` + `docs/requirements/capability-discovery-orchestration-0.45.0.md`
- **子命令**：`capability-context [--fixture <project-root>] [--fail-on-issues]`
- **输入**：当前项目或 fixture 的 host/package/entry 文件事实、`verify_workflow.py` 命令注册事实、runtime readiness matrix、governance pack registry、Codex Desktop marketplace-management E2E 规划文档，以及未来 FIX-116 external capability registry 是否存在
- **输出**：`scenario`、`host_id`、`available_capabilities`、`selected_capability`、`source_facts`、`rejected_alternatives`、`degradation`、`side_effect_boundary`、`validation_command`、`review_requirement`、`no_overclaim_boundary`
- **触发条件**：0.45.0 FIX-115 capability context/selection trace 验收、受限环境能力选择诊断、后续 FIX-116/FIX-117/REL-022 release gate 前
- **依赖**：`check-governance` Check 28j、`check-runtime-readiness-matrix`、`check-governance-packs`
- **边界**：read-only diagnostic；不得声明 automatic global best-tool selection；不得把 catalog entry 当 runtime PASS；不得把 diagnostic selection trace 当 successful external execution；preferred capability 不可用时必须输出 `BLOCKED`、`DEGRADED`、`NOT_SUPPORTED` 或 `NOT_FOUND`
- **被以下子工作流使用**：调研（research）、架构设计（architecture）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-032：Capability Registry guard

- **文件**：`infra/verify_workflow.py` + `core/capability-registry.json`
- **子命令**：`check-capability-registry [--fail-on-issues]`
- **输入**：canonical capability registry 中的 plugin、skill、tool、MCP、browser、sub-agent、script、fallback 条目；每条的 `kind`、`host_surface`、`scenarios`、`status`、`source_facts`、`validation_command`、`side_effect_boundary`、`no_overclaim_boundary`
- **输出**：registry 是否 registry-first 且不做物理插件拆分；是否覆盖所需 kind；是否缺 source facts / validation command / side effect boundary；是否把 catalog entry 当 runtime PASS 或 external capability available；是否把 governance packs 混同为 external capability；是否出现 official/marketplace/universal/automatic best-tool/1.0.0 overclaim
- **触发条件**：新增或调整外部 capability catalog、引用 host tools / adapter manifests / plugin manifests / fallback 路径、发布 0.45.0 capability discovery 边界或 release gate 前
- **依赖**：`check-governance` Check 28k、`core/manifest.json`、TOOL-031
- **边界**：catalog membership is not runtime PASS；registry 是 capability fact source，不执行 plugin install、MCP call、browser action、sub-agent spawn、network call 或 external API；governance packs 保持 internal capability modules，不等同 external plugin/skill/tool availability
- **被以下子工作流使用**：调研（research）、架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-033：Host Capability Context benchmark

- **文件**：`infra/verify_workflow.py` + `docs/requirements/capability-discovery-orchestration-0.45.0.md`
- **子命令**：`check-host-capability-context [--fixture <project-root>] [--fail-on-issues]`
- **输入**：当前项目或测试 fixture 的 capability registry/catalog facts、local skill/script facts、runtime readiness facts，以及 no network、no plugin install、no MCP、no browser、no sub-agent、local skill only、simulated Codex CLI blocked、simulated Gemini auth blocked 等受限环境场景
- **输出**：restricted host capability context 是否覆盖 8 个场景；每个场景是否给出 `source_facts`、`selected_capability`、降级边界、`validation_command` 与 no-overclaim boundary；是否阻断 blocked/degraded/catalog fact 被包装成 runtime PASS/AVAILABLE、automatic best-tool selection 或 universal plugin availability
- **触发条件**：FIX-117 restricted-environment fixtures、capability discovery/orchestration release gate、受限宿主诊断或 no-overclaim boundary 变更后
- **依赖**：`check-governance` Check 28l、TOOL-031、TOOL-032、runtime readiness matrix
- **边界**：benchmark/diagnostic only；not external execution；not Desktop marketplace E2E PASS；不执行 network、plugin install、MCP call、browser action、sub-agent spawn、Codex CLI runtime 或 Gemini auth flow；blocked capability is not runtime PASS；catalog fact is not runtime PASS
- **被以下子工作流使用**：调研（research）、架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-034：Official Submission Ecosystem guard

- **文件**：`infra/verify_workflow.py` + `docs/marketplace/official-submission-0.46.0.md` + `docs/marketplace/ecosystem-positioning-0.46.0.md` + `docs/marketplace/comparison-0.46.0.md` + `docs/marketplace/migration-guide-0.46.0.md` + `docs/marketplace/examples-0.46.0.md`
- **子命令**：`check-official-submission-ecosystem [--fail-on-issues]`
- **输入**：0.46.0 official submission ecosystem docs、ecosystem comparison、migration guide、examples、official-submission release-surface boundary docs、0.45.0 capability-context evidence、capability registry、restricted-environment benchmark 和 Codex Desktop marketplace-management BLOCKED / NOT_RUN report
- **输出**：official submission materials 是否说明 workflow 是 governance trust layer、orchestrates external capabilities、complements Superpowers/Agent Skills/MCP/browser tools/host-native plugins；是否消费 FIX-115/FIX-116/FIX-117 与 0.45.0 Desktop BLOCKED/NOT_RUN 证据；是否阻断 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS、automatic best-tool selection、universal plugin/skill/tool availability、catalog entry runtime PASS、1.0.0 production-ready 和 replacement overclaim
- **触发条件**：0.46.0 official submission materials、ecosystem positioning、migration guide、examples、release docs 或 no-overclaim boundary 变更后
- **依赖**：`check-governance` Check 28m、`check-release --version 0.46.0` release docs detail、TOOL-031、TOOL-032、TOOL-033
- **边界**：documentation/release guard only；not official submission approval；not marketplace approval；not Desktop marketplace-management E2E PASS；not automatic best-tool selection；not universal plugin/skill/tool availability；not catalog entry runtime PASS；not 1.0.0 production-ready
- **被以下子工作流使用**：调研（research）、发布（release）、维护（maintenance）

### TOOL-035：Mainstream Agent Loading guard

- **文件**：`infra/verify_workflow.py` + `README.md` + `adapters/claude/README.md` + `adapters/codex/README.md` + `adapters/gemini/README.md` + `adapters/opencode/README.md` + `docs/requirements/mainstream-agent-loading-0.47.0.md`
- **子命令**：`check-mainstream-agent-loading [--fail-on-issues]`
- **输入**：0.47.0 mainstream agent loading requirements、README Tier 1/Tier 2 loading matrix、Claude/Codex/Gemini/opencode adapter loading guides、source citations、validation commands、runtime/readiness and no-overclaim boundary text
- **输出**：加载说明是否覆盖 Codex、Claude Code、Gemini CLI、opencode；compatibility/research rows 是否覆盖 Cursor、GitHub Copilot coding agent、Cline、Windsurf/Cascade、Kiro；requirements row 是否带 source URL；Tier 2 是否保持 RESEARCH_ONLY / NOT_RUNTIME_VERIFIED；是否阻断 official approval、marketplace approval、universal/full runtime support、Desktop marketplace-management E2E PASS、automatic best-tool selection、catalog runtime PASS、1.0.0 production-ready 等越界声明
- **触发条件**：0.47.0 loading/readme/adapter docs、mainstream agent compatibility matrix、validation commands 或 no-overclaim wording 变更后
- **依赖**：`check-governance` Check 28n、`check-agent-adapters`、TOOL-024、TOOL-034、RISK-036
- **边界**：documentation/adapter contract guard only；not official approval；not marketplace approval；not universal/full runtime support；not Codex Desktop marketplace-management E2E PASS；not automatic best-tool selection；not catalog entry runtime PASS；not 1.0.0 production-ready
- **被以下子工作流使用**：调研（research）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-036：External Project Validation harness

- **文件**：`infra/verify_workflow.py`
- **子命令**：`external-project-validation --target <path> [--workspace-parent <path>] [--keep-workspace] [--timeout N] [--fail-on-issues]`
- **输入**：真实外部项目目录、当前仓库 git-tracked workflow surface、生成的临时 `.governance/` 最小记录
- **输出**：临时 validation workspace、复制的 surface 文件数、`status`、`gate G1`、`governance-context --fail-on-issues`、`check-governance --fail-on-issues` 结果和 JSON 摘要
- **触发条件**：VAL-001 复跑、1.0.0 前外部验证、外部新项目 install-surface regression、release gate 前需要机器可复跑外部 target 证据
- **依赖**：当前 git-tracked source surface、`check-governance`、`governance-context`、`core/manifest.json`
- **边界**：temporary workspace only；不修改 `--target`；不是 official approval；不是 marketplace approval；不是 external validation full PASS；不是 Desktop lifecycle E2E PASS；不关闭 RISK-036；不是 1.0.0 production-ready
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-037：Dynamic Lifecycle Registry guard

- **文件**：`infra/verify_workflow.py` + `core/lifecycle-registry.json`
- **子命令**：`check-lifecycle-registry [--fail-on-issues]`
- **输入**：canonical lifecycle registry 中的 `active_lifecycle_mode`、`default_lifecycle_mode`、classic/dynamic lifecycle modes、stage/subphase vocabulary、loop policy、allowed transitions、gate references、project type hooks、flow unit schema，以及 `python_game_10_chapters` example data
- **输出**：active/default lifecycle mode 是否仍为 `classic-phase-gate`；dynamic-flow-gate 是否保持 schema-only inactive；flow unit schema 是否覆盖必需字段；python_game 10 章节是否以数据表达 chapter 1 released、chapter 2 testing、chapter 3 development、chapter 4-10 backlog；是否阻断 RISK-037 closure 或 1.0.0 readiness overclaim
- **触发条件**：新增或调整 lifecycle registry、flow-unit schema、project-type hooks、stage/subphase vocabulary、loop policy、allowed transitions、gate references 或 schema-only release boundary 后
- **依赖**：`core/manifest.json`、`check-manifest-consistency`、classic G1-G11 `core/stage-gates.md`
- **边界**：schema-only registry；不激活 flow-unit runtime；不迁移项目；不替代 classic G1-G11；不关闭 RISK-036/RISK-037；不是 1.0.0 production-ready
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-038：Flow Unit Runtime hot-state guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-flow-unit-runtime [--fixture <path>] [--fail-on-issues]`
- **输入**：可选热状态文件 `.governance/flow-unit-runtime.json`，包含 `workflow_model`、`flow_units`、`active_lanes`、per-unit `gate_state`、`loop_state.loop_count`、`blocked_downstream_units`、`rollup_status` 和 no-overclaim boundary；文件缺失时安全通过并报告 NOT_FOUND。
- **输出**：flow-unit runtime hot-state 检查结果，展示 workflow model、active lanes、rollup status、blocked downstream units 和 loop counters。
- **触发条件**：0.52.0 flow-unit runtime visibility、status/context output、python_game 多章节热状态、dependency blocking 或 loop counter 语义变更后。
- **依赖**：`check-lifecycle-registry`、classic G1-G11 vocabulary、optional hot project state。
- **边界**：runtime visibility only；不激活 declarative gate engine；不迁移项目；classic G1-G11 保持兼容；不关闭 RISK-036/RISK-037；不是 1.0.0 production-ready。
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-039：Project-Type Gate Presets guard

- **文件**：`infra/verify_workflow.py` + `core/lifecycle-registry.json`
- **子命令**：`check-lifecycle-registry [--fail-on-issues]`
- **输入**：canonical lifecycle registry 中的 `project_type_hooks` 与 `project_type_gate_presets`，覆盖 game、web-app、mobile-app、library、cli-tool、ai-agent-plugin、internal-script；每个 preset 的 profile 正交边界、默认 packs、质量预算、验收模板、release checks、gate policy 和 gate standards。
- **输出**：required project types 是否完整；preset 是否有 hook 对应项；default flow unit type 是否同时属于 preset/hook templates 和 `flow_unit_schema.allowed_unit_types`；profile/project-type 是否声明正交；game 是否覆盖 chapter/level/asset/narrative/playability gate standards；library 是否覆盖 api/semver/docs/downstream-tests gate standards；no-overclaim 文本是否阻断 declarative gate engine、项目迁移、dynamic default、RISK-036/RISK-037 closure 和 1.0.0 readiness。
- **触发条件**：0.53.0 project-type gate presets、项目类型默认 packs、质量预算、验收模板、release checks、gate policy、gate standards 或 profile/project-type 正交边界变更后。
- **依赖**：TOOL-037、`core/manifest.json`、classic G1-G11 `core/stage-gates.md`、`check-manifest-consistency`。
- **边界**：preset data contract only；classic-phase-gate 保持 active/default；dynamic-flow-gate 保持 inactive/schema-only；不激活 declarative gate engine；不迁移项目；不把 dynamic-flow-gate 设为默认；不关闭 RISK-036/RISK-037；不是 1.0.0 production-ready。
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-040：Classic Gate Execution Registry guard

- **文件**：`infra/verify_workflow.py` + `core/lifecycle-registry.json`
- **子命令**：`check-lifecycle-registry [--fail-on-issues]`；运行时检查使用 `gate-check <G1-G11>`
- **输入**：canonical lifecycle registry 中的 `gate_execution_registry`，覆盖 G1-G11 的 `required_artifacts`、`checks`、`evidence_query`、`automation_command`、`human_confirmation_policy`、`severity` 和 `project_type_overrides`。
- **输出**：`classic_registry_execution` 是否启用；G1-G11 是否按顺序完整声明；check executor/function/severity 是否可识别；project-type override 是否只引用已声明项目类型并 fail-closed；automation command 是否仅作为 metadata 且不由 gate judgment 执行。
- **触发条件**：0.54.0 classic G1-G11 registry execution、`auto_judge_gate` 判定路径、gate/check metadata 或 project-type override schema 变更后。
- **依赖**：TOOL-037、TOOL-039、`core/stage-gates.md`、`check-manifest-consistency`。
- **边界**：classic registry execution only；`runtime_activation.declarative_gate_engine` 保持 false；不激活 flow-unit runtime；不迁移项目；不把 dynamic-flow-gate 设为默认；不执行 registry 中声明的 automation command；不关闭 RISK-036/RISK-037；不是 1.0.0 production-ready。
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-041：Dynamic Lifecycle Migration dry-run preview

- **文件**：`infra/verify_workflow.py` + `docs/migration/dynamic-flow-gate-migration-0.55.0.md`
- **子命令**：`dynamic-lifecycle-migration --target <path> --dry-run [--fail-on-issues]`；别名 `dynamic-flow-gate-migration`
- **输入**：目标项目根或 fixture；读取 `.governance/plan-tracker.md`、`.governance/evidence-log.md`、可选 `.governance/flow-unit-runtime.json` 和 canonical lifecycle registry。
- **输出**：JSON migration preview，包含 `workflow_model`、`flow_units`、`evidence_preservation`、`blocked_checks`、`no_overclaim_boundaries` 和 read-only `migration_plan`。
- **触发条件**：0.55.0 migration/external validation 前，需要检查 classic 项目是否可保留 plan/evidence 并形成 dynamic-flow-gate opt-in 预览。
- **依赖**：TOOL-037、TOOL-038、TOOL-040、`check-manifest-consistency`。
- **边界**：dry-run only；必须显式传入 `--dry-run`；不修改 target；classic-phase-gate remains active/default；dynamic-flow-gate is opt-in；plan-tracker is preserved；evidence-log is preserved；不关闭 RISK-036/RISK-037；不声明 external validation full PASS、official approval、marketplace approval、Codex Desktop lifecycle PASS 或 1.0.0 production-ready。
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-042：Local Web Console launcher

- **文件**：`infra/verify_workflow.py` + repo-only `web/`
- **子命令**：`web-console --status`；`web-console --governance-entry`；`web-console --summary-link`；`web-console --start [--install] [--open] [--host 127.0.0.1] [--port 5173]`；`--install` 超时由 `SPG_WEB_INSTALL_TIMEOUT` 参数化（默认 120s，非法回退默认——FIX-238.4）
- **输入**：当前仓库中的 `web/package.json`、本机 `npm`、可选 `web/node_modules`
- **输出**：Web console 可用性、启动/复用结果、手动启动命令、本地 URL；`--governance-entry` 是手动 `/governance` 默认入口，启动或复用本地 Web UI；`--summary-link` 输出阶段/session 总结可追加的只读入口且不启动服务；`--start` 后台启动 Vite dev server 并写入 `web/web-dev.log` 与 `.spg-web-console.pid`；npm install 超时输出分类诊断（`timed out after Ns (SPG_WEB_INSTALL_TIMEOUT)`）不挂起，`--fail-on-issues` 时 exit 124
- **触发条件**：用户手动执行 `/governance`，或希望从 CLI/客户端打开可视化状态面板、查看本地配置、状态、证据/风险或高级维护入口时
- **依赖**：repo-only `web/` React/Vite console、`npm`、`check-manifest-consistency`
- **边界**：local companion dashboard only；主交互仍在 CLI/agent client；手动 `/governance` 默认启动或复用 Web console，便于后续 Web UI 交互；阶段/session 总结只追加 `--summary-link` 只读入口；缺少依赖时不静默安装，提示显式 `--install`；不自动执行 agent 任务；不是 Codex Desktop 内嵌 UI、marketplace lifecycle PASS、official approval 或 1.0.0 readiness 证据。
- **被以下子工作流使用**：立项（initiation）、测试（testing）、运营（operations）、维护（maintenance）

### TOOL-051：Entry bootstrap + resolve_entry 超时兜底

- **文件**：`infra/bootstrap.sh`、`infra/bootstrap.cmd`、`infra/verify_workflow.py`（`resolve-entry` 薄入口）
- **子命令**：`resolve-entry [--project-root <path>]`；POSIX 直调 `bash "<plugin_home>/infra/bootstrap.sh"`；Windows 直调 `& "<plugin_home>\infra\bootstrap.cmd"`
- **输入**：插件包内 `infra/resolve_entry.py`；宿主项目根（默认 cwd，或 `--project-root`）
- **输出**：resolve_entry JSON envelope（stdout）；分类诊断（`spg-bootstrap-error: <category>`）——file-not-found / timeout / python-missing / store-stub，exit 非 0（fail-closed，FIX-238.3）
- **退出码契约**：0 成功；1 其他失败；2 python 缺失；3 resolve_entry.py 缺失；4 超时；5 store stub（缺 FX-130 canonical marker）
- **触发条件**：宿主无 AGENTS.md/CLAUDE.md 时定位引导入口；`/governance` 第一动作；resolve_entry 卡住/缺失诊断（FIX-238）
- **依赖**：resolve_entry.py 本体零改动（DEC-096）；`SPG_RESOLVE_TIMEOUT`（默认 15s，非法回退默认）
- **边界**：不做路径考古、不无限 fallback、不修改 resolve_entry.py；超时/缺失时只输出诊断并停止；`@bootstrap-version` 升级链按入口引导命令文档的规则由 agent 执行
- **被以下子工作流使用**：维护（maintenance）、发布（release）、运营（operations）

### TOOL-043：ArchGuard Architecture Health check

- **文件**：`infra/verify_workflow.py`（`check_architecture_health`）+ `core/architecture-health.json`
- **子命令**：`check-architecture-health [--fail-on-issues]`
- **输入**：仓库下 `.py/.js/.ts` 文件 + `core/architecture-health.json` 声明式阈值预算
- **输出**：3 级（PASS/WARN/ERROR）发现清单——module_size（文件行数）、function_size（Python AST 函数行数）、module_constants（模块常量计数）、duplicate_constant（重复定义如 PRODUCT_CODE_PATTERNS）
- **触发条件**：大型项目持续演进中需要看模块/函数膨胀信号时；CI/本地一键扫描
- **依赖**：`core/architecture-health.json`（manifest 双重登记）、Python `ast`
- **边界**：0.58.0 advisory-only（`gate_integration.fatal_on_error=false`）——WARN/ERROR 告警但不阻断 release gate；schema `module_size.exclusions` 豁免（FIX-350 起同时 gate 全部四个扫描面：module_size/function_size/module_constants/duplicate_constant；无豁免 schema 行为与旧版一致）；`project/**`（e2e fixture 投影镜像）与 `.governance/**`（宿主治理运行时数据）已豁免；不重写代码，仅诊断。
- **被以下子工作流使用**：架构（architecture）、维护（maintenance）

### TOOL-047：Declarative Release Ledger

- **事实源**：`core/releases/<version>.json`，schema 为 `core/release-ledger.schema.json`
- **子命令**：`release-ledger [--version X.Y.Z] [--remote origin] [--no-remote]`
- **状态**：`PASS=0`、`FAIL=1`、`UNKNOWN=2`、`BLOCKED=3`
- **边界**：historical backfill 永不等价于 native PASS；缺失历史 tag 只记录 `missing_requires_decision`，不得自动创建
- **被以下子工作流使用**：发布（release）、维护（maintenance）

### TOOL-048：Artifact Projection Generator

- **事实源**：`skills/software-project-governance/SKILL.md` frontmatter version
- **检查**：`release-projection`，默认只读
- **写入**：`release-projection --write`，预生成并全量校验后原子替换；失败按 rollback journal 恢复
- **安全**：拒绝绝对路径、`..`、symlink traversal、重复 target、缺失 JSON pointer 和替换计数漂移
- **被以下子工作流使用**：发布（release）、维护（maintenance）

### TOOL-049：Optional Quality Tool Probe

- **子命令**：`quality-tools`
- **输出**：Ruff/mypy 各自 `PASS`、`NOT_RUN` 或 `FAIL`，以及 `runtime_dependency=false`
- **边界**：未安装必须为 `NOT_RUN`；不安装依赖，不把未运行写成 PASS
- **被以下子工作流使用**：开发、测试、发布、维护

### TOOL-052：DSH Preset Schema Compat Guard

- **文件**：`infra/dsh_compat.py`（独立可运行）、`infra/tests/test_dsh_compat.py`
- **子命令**：`check-dsh-preset-compat [--fail-on-issues]`；`check-governance` 内为 Check 28v（FIX-270 插件产品自检，宿主模式需 `--product-gates`）
- **输入**：包内每个 preset 组合（渲染源 `agent-presets/*/agent.cordis.yml.template`，外加任何 `agent.cordis.yml` 直接组合）+ **解析态** dsh 插件集的 `@deepseek-ai/cordis-plugin-include` `entryListSchema`、`@deepseek-ai/cordis-plugin-loader` `evaluate`/`isJsExpr`、`@deepseek-ai/cordis` `resolveConfig`；解析面优先级 = `DSH_INSTALL_DIR` / `DSH_HARNESS_NODE_MODULES` → `$DSH_HOME/profiles/<profile>/node_modules` 与 `profiles/node_modules`（**只读**，且仅在 `$DSH_HOME` 被显式导出时；绝不猜测 `~/.dsh`）→ PATH `dsh` 的 install anchor。输出中逐包报告解析出的绝对路径与版本；`@deepseek-ai/dsh` CLI 版本仅作参考（schema 权威是 oracle 包，不是 CLI 版本串）
- **输出**：逐行 `PASS / CONFIG_INVALID / MODULE_UNRESOLVED / IMPORT_ERROR / CONFIG_EXPR_ERROR / DISABLED_EXPR_ERROR / ROW_SHAPE / NO_SCHEMA / BUILTIN / DISABLED_INHERITED`，失败行携带 row id + 模块名 + schema 原文消息；整体 `PASS` / `FAIL` / `NOT_RUN`
- **安全边界**：只读静态分析 + 从解析面 import 模块（不调用 `apply`，不构造 Context）；子进程 `DSH_HOME` 重定向到临时空目录，`home_writes` = 该临时目录的条目数（构造时为空）⇒ **仅证明未写入该隔离 home**，不是全局零写入证明（模块 import 与 `$DSH_HOME/profiles` 只读探测都在其外），M7.7 (a) 先例
- **边界**：无 node / 无可解析插件集 → `NOT_RUN`（不计 issues，不写成 PASS）；schema 判定只来自解析面 `Config`，不复制任何 schema；`disabled` 语义按 loader 的 `Entry._disabled` 祖先链继承（group 自身恒为 enabled，但其 `disabled` 由子行继承 ⇒ 子行记 `DISABLED_INHERITED`，不出 finding）
- **被以下子工作流使用**：开发、测试、发布、维护

### TOOL-053：治理成本埋点报告（FEAT-032 / AUDIT-154 切片 A-1）

- **文件**：`infra/governance_cost.py`（正式模块，EVD-1071 研究脚本逻辑提升）、`infra/tests/test_governance_cost.py`；`project/research/dsh-trace-analysis/` 下脚本为 deprecated 指针
- **子命令**：`governance-cost-report --sessions-root <dir> [--workspace <str>] --format json|text [--ttfa-acceptance]`
- **输入**：`--sessions-root` 下 `**/session.v3.jsonl.zstd`（zstandard 解压；`--sessions-root` 缺省取 `DSH_SESSIONS_ROOT` 环境变量，两者皆缺 → exit 2 fail-closed，不硬编码用户路径）；`--workspace` 按 cwd 子串过滤后再聚合
- **输出**：机读 JSON（schema `governance-cost-report/1`）+ 人类可读 text：每轮 TTFA（用户消息→首次 ask_user_question）、进入实质工作时间（首次 ask→首个非治理工具调用或轮结束，含 endpoint 判别）、token 分项（in/cache/out，累计请求量口径）、工具时长分布（按名聚合 count/total/max/avg）、LLM vs 工具时间占比与 labeled residual、ask_user_question 挂起（用户等待）单列；报告内嵌 `calibration` 口径披露（审计报告 §4：原始时间戳差值不加工、LLM 窗口内 TTFT/解码不可分离、残差语义）
- **口径**：`user/message` 无 turn 字段按事件序归属当前 turn（EVD-1071/审计 §2）；治理工具按名分类仅 `ask_user_question`+`skill`（声明式常量，通用工具按名不可分类、计入实质工作候选——已在 calibration 披露）
- **安全边界**：对 sessions root 纯只读（rglob + 读字节）；zstandard 缺失 → 清晰报错 exit 1，不静默降级；模块 import 期 stdlib-only（引擎冷启动面 +1），zstandard 懒加载
- **依赖**：zstandard（可选运行时依赖，缺失 fail-closed——依赖登记由 Coordinator 决策，未修改 requirements/pyproject）
- **验收面（`--ttfa-acceptance`，FEAT-040 / RISK-055 一键复验路径）**：追加成对 TTFA+TTW 验收块——阈值常量在代码（`TTFA_ACCEPTANCE_P50_MS = 25000` / `TTFA_ACCEPTANCE_P95_MS = 45000` / `TTFA_ACCEPTANCE_MIN_TURNS = 3`），采样口径与 `totals.ttfa_ms` 同一全体（DEC-207① 要求的同快照口径，与 EVD-1073/RISK-052 基线可直接对比）；`TTW` 逐行配对（首次 ask → 首个非治理工具 | 轮结束），因为单看 TTFA 可以用"更早发问"买分。verdict ∈ `PASS` / `FAIL` / `PENDING`——样本 < 3 时 **PENDING 而非绿**：机制未跑就宣称达标正是 AUDIT-154 点名的度量诚实性问题。**一键命令**（在新会话跑过新协议后执行）：
  `python <plugin_home>/infra/verify_workflow.py governance-cost-report --sessions-root "$env:DSH_SESSIONS_ROOT" --workspace project_management_workflow --ttfa-acceptance --format text`
- **被以下子工作流使用**：架构、开发、测试、维护（FEAT-033/034/039 消费其指标；RISK-055 复验）

### TOOL-054：只读 bootstrap 聚合命令（FEAT-033 / AUDIT-154 切片 A-2）

- **文件**：`infra/bootstrap_aggregate.py`（核心模块，engine-free）、`infra/tests/test_bootstrap_aggregate.py`；引擎只接线 dispatch（`verify_workflow.py` import + subparser + commands dict，governance_cost 同款模式）
- **子命令**：`governance-bootstrap [--budget-ms N] [--format json|text] [--profile lite|standard|strict]`（`--project-root` 走引擎全局参数；缺省 cwd，fail-closed）
- **输入**：`.governance/` 活数据只读（plan-tracker.md / risk-log.md / decision-log.md，UTF-8 行级解析）+ `resolve_entry.resolve()` envelope（dual-root 权威，DEC-096）+ `task_priority` 轻量依赖分析（纯 stdlib 复用，非重新推导）
- **输出**：机读 JSON（schema `governance-bootstrap/1`，≤8KB 投影 / ≤2K token）或 ≤40 行 text 摘要。聚合面：`resolve`（envelope 子集）+ `migration`（active vs plan 版本比较**仅标志不执行**）+ `project`/`gates`（计数 + 首 pending gate）/`tasks`（tpa 口径统计：total/completed/unblocked/blocked/non_executable/p0_pending）/`risks`（open/overdue/soon + ≤3 overdue ids）/`recent`（≤3/5 决策，lite 档省略）/`candidates`（recommended_next ≤1/3/5，空推荐携带 `empty_reason`+`unblock_recommendation` 结构化原因——REQ-110，禁止机械枚举）+ `health`（**v1 恒 `deferred`**：`pending_checks` + 指向 `check-governance` 的 next_action——本命令未做健康检查，不得伪装已检查）+ `next_actions`（≤5 条派生指引）
- **预算契约**：`--budget-ms`（默认 3000）单调钟相位间检查；超时返回已完成部分 + `deferred: [{section, reason: budget_exhausted}]` 明示未完成范围（fail-safe 不猜测通过；health 的 deferred 是 v1 契约，与预算 deferred 是两回事）
- **只读红线**：零 `.governance` 写入、零 git 写入、零子进程派发、不调用 archive/迁移；连续两次运行输出一致（仅 `generated_at`/`duration_ms` 易变）——测试以 fixture 树哈希 + 双跑 payload 相等断言看护
- **边界**：不 import `verify_workflow`（ArchGuard R2 零新增反向边——状态投影为**已披露镜像**，与 resolve_entry 镜像引擎 regex 同一纪律）；`status` 仍是全量投影依赖（Delivery Trust Snapshot/Gate 全表以 status 为准）；协议重排（Scenario 顺序/交互时序）是 FEAT-034 边界，本命令只做数据面聚合
- **被以下子工作流使用**：立项/架构/开发/测试/发布/运营/维护（每会话 bootstrap 快路径；governance 命令文档的 Scenario F/D 数据源段与入口 SKILL 的 bootstrap 健康摘要段已接线指向）

### TOOL-055：注入面体积预算门禁（FEAT-039 / AUDIT-154 切片 A-8）

- **文件**：`infra/checks/injection_budget.py`（`check_injection_budget` / `load_injection_surface` / `estimate_surface_tokens` / `cmd_check_injection_budget`——handler 在 leaf，`infra/verify_workflow.py` 只做 dispatch 接线 + Check 33 内联同报；`check-injection-contract` 同块扩展）；`infra/tests/test_verify_workflow.py::Feat039InjectionBudgetTests`
- **子命令**：`check-injection-budget [--budget-tokens N] [--profile lightweight|standard|strict] [--format text|json] [--fail-on-issues]`
- **输入（实际加载集合，多文件求和——非单文件，拆分文件不能绕过预算）**：
  - `resident` 层：persona（`agent-presets/governance/agent.cordis.yml.template` 的 `prefix:` 块标量——注入的就是它，YAML 宿主配置与注释不计）+ 入口模板（`commands/governance-init.md` Step 7 按 `--profile` 选 canonical 模板）+ 次要入口薄指针（secondary-thin 模板，双入口工作区才在场）+ `agent-instructions`（`adapters/dsh/AGENTS.md.template` 整文件）；
  - `skill` / `command` 层（按需加载，单独计量，**不并入 resident**）：`skills/software-project-governance/SKILL.md`（**独立预算 16,000 tok**——FEAT-052，tier 聚合与 surface 行按各自预算线判定超限，实测基线 14,456）、`/governance` 命令入口默认载荷（FEAT-038 路由层——拆出的场景/说明文件不在默认注入面，故不计入）。
  - 口径说明：入口面按 **canonical 模板**定价（不是某个工作区的入口文件），因此改一份工作区的入口文件不会移动这个门禁；活体工作区入口由 `check-entry-bootstrap-sync` 守护。**块边界不在此处重实现**——切片直接委托 `sync_entry_projection`（生成平台入口文件的同一权威：标签 → 区块内**最后一个**裸围栏，嵌套围栏不截断），故定价数字与注入文本不会分叉（R1/FEAT-039：私有切片规则曾把薄指针模板后的规格说明文字计入，并保留 markdown 围栏标记）。
- **输出**：分项表（surface / tier / bytes / chars / CJK / 预算价 token / DSH host 价 token / 状态 / `sha256[:16]` 内容指纹——**漂移锚**：等长改写不改变 token 数，指纹可检）+ 三层 TOTAL + 全域诊断 TOTAL + tokenizer 口径 + "Tier budgets" 逐层预算线行（FEAT-052）+ "Over budget — gated / report-only" 两行口径 + tool-return 面登记行；`--format json` 输出机读 payload（含每面 `sha256_16`、`tokenizer` 口径字段与 `verdict`）
- **tokenizer 口径（文档化假设——不引外部 tokenizer 依赖）**：CJK 字符 = 1 token；ASCII = `ceil(chars/4)`（与 DSH host `@deepseek-ai/dsh-token-meter` 的 `CHARS_PER_TOKEN = 4` 同率）；其他字符 = `ceil(chars*2/5)`。`tokens_host` 一列同时给出纯 `ceil(chars/4)` 口径便于与宿主自身计数对照。Han 文本在真实 BPE 下 ≈1 token/字符，按宿主 4 字符/token 定价会低估 3-4 倍——这正是预算要覆盖的语料。
- **预算与裁决**：`--budget-tokens` 默认 6000（**resident hard 硬门**，FEAT-050/DEC-211③ 自切片 A 放宽档翻转；arch 最终目标 4K）。`BUDGET_TIER_POLICY` 逐层声明 gate 姿态与预算线：`resident` = hard（EVD-1104 瘦身后三 profile 4,216/5,694/5,966 全 ≤6,000——slice-A 放宽窗已关闭，超限即 issue + FAIL，未来增长 fail-closed）、`skill` = report-only + **独立预算线 16,000**（FEAT-052 数据字段化——policy 行显式 `budget_tokens` 字段，tier 聚合/surface 行/报告按该线判定与呈现，实测 14,456 在线内；姿态不翻硬门，翻硬为 0.86.0+ 候选经 FEAT-047 BaselineMetadata 承载）、`command` = report-only（无独立数值——实测 3,466 tok 远低于 resident 线，无实证需求；无 `budget_tokens` 字段的 tier 沿用 resident 线）。verdict ∈ `PASS` / `ADVISORY` / `FAIL`（当前策略表无 advisory 档，ADVISORY 分支为数据驱动保留臂）；**裁决只由 gated 档决定**——报告与 Check 33 显式分列 "gated over"（动裁决）与 "report-only over"（仅测量）+ "Tier budgets" 逐层预算线行（FEAT-052），不混称 over-budget（P2-1）；`BUDGET_TIER_POLICY` 缺 `resident` 行时输出显式 issue + FAIL，不是 `KeyError`（fail-closed）。任一 canonical 源解析失败（文件缺失/锚点损坏/切片越界/canonical 源不可解析）→ 显式 issue + `FAIL`（fail-closed，绝不静默记 0）。
- **tool-return 预算面（登记，不重实现）**：FEAT-033 的 `bootstrap_aggregate.MAX_JSON_BYTES = 8192` 由 `check_tool_return_budget` 断言（常量值 + `_enforce_projection_budget` 存在），预算被悄悄放宽会在本门禁报 issue。
- **CI 接线（不新建 CI 系统——复用既有 check 面）**：① 每次 commit/PR 走既有 `governance` hook 与 `check-governance` 聚合（Check 33 段内已内联体积分项与 ADVISORY 行）；② 需要在流水线里单独取退出码时用 `python skills/software-project-governance/infra/verify_workflow.py check-injection-budget --fail-on-issues`（FAIL → exit 1；ADVISORY → exit 0）；③ 机读断言用 `--format json` 的 `verdict` / `tiers` 字段。zstandard 依赖面：FEAT-032 的 zstd fixture 测试在依赖缺失时**显式 FAIL**（`test_governance_cost.py::Feat039ZstandardDependencyAssertionTests`，提示 `pip install zstandard`），不再静默 skip（DEC-205②）。
- **边界**：只测量与裁决，不修改任何被测量文件、不写 `.governance/`、不执行 git；不替代 `check-injection-contract`（锚点存在性）与 `check-entry-bootstrap-sync`（投影一致性）——三者互补：注入面**在不在** / **一致不一致** / **贵不贵**。
- **被以下子工作流使用**：架构、开发、测试、发布、维护

### TOOL-056：行为灰度开关 / legacy 回退通道（FEAT-040 / AUDIT-154 切片 A-9）

- **文件**：`infra/behavior_profile.py`（核心模块，stdlib-only leaf）、`infra/tests/test_behavior_profile.py`；引擎面零改动（`governance-bootstrap` 的 `behavior` 面由 `infra/bootstrap_aggregate.py` 承载——ArchGuard R1/R4/R5 不动）
- **调用形态**：无独立子命令。判定入口 = `governance-bootstrap --format json` 的 `behavior` 面（`profile`/`source`/`env_var`/`plan_tracker_key`/`reverted`/`invariants`/`invalid`）+ `--format text` 的 `behavior:` 行；legacy 生效时回退提示置于 `next_actions` **首位**（不可被 5 条上限挤掉）
- **输入（两臂 + 默认）**：会话级环境变量 `GOVERNANCE_LEGACY_BEHAVIOR`（`1/true/yes/on/legacy` → legacy；`0/false/no/off/modern` → modern）> 项目级 plan-tracker `## 项目配置` 的 `- **behavior_profile**: legacy|modern` > 默认 `modern`
- **回退范围（`LEGACY_REVERTS`，**只回退性能/编排行为**）**：FEAT-034 快路径→六段读取；FEAT-034 首次交互前置→深检先行；FEAT-036 ≤8 字段默认视图→完整快照契约；FEAT-038 Scenario 按需→预加载。每条带 `class` 字段，`ALLOWED_REVERT_CLASSES = {performance}`
- **安全硬边界（`SAFETY_INVARIANTS`，legacy 一律不回退）**：升级确认门（FEAT-035，确认前零写操作）/ 异常不隐藏 / fail-closed（`resolved_root_ok == false` 即停）/ 真实环境防护（M7.7 三选一）/ 复审必达（M7.4）
- **机检契约**：`revert_contract_issues()` 断言 (1) 回退表只允许 `performance` 类；(2) 回退表与安全不变量不得共享 FEAT（FEAT-035 只出现在不变量侧）；(3) 每个不变量带非空协议 marker；(4) 面/id 唯一。守护测试除「真实表干净」外**注入违规**验证 checker 真的会失败（净表断言无法证明 checker 有效）
- **非干扰契约（守护测试）**：同一宿主树下 modern/legacy 两次 `governance-bootstrap` payload 除 `behavior` 与回退 next_action 外**逐面相等**——`health` 仍为 `deferred`（不借绿），`resolve`（fail-closed 权威）不变，治理面无缺失
- **发布面**：六个注入面必须携带 `行为灰度开关` 标记（canonical Step 7 四个模板 + 路由层 + bootstrap 说明 + SKILL.md + DSH 模板 + persona），由 `test_behavior_profile.py::PublicationTests` 守护；薄指针上限（≤40 行/≤3KB）由 `check-entry-bootstrap-sync` 守护
- **边界**：只读纯函数（AST 守护：仅 `os`/`re` 导入、零写调用）；不 import `verify_workflow`（ArchGuard R2/R6）；不做用户提示、不写 `.governance/`
- **被以下子工作流使用**：全部阶段（每会话 bootstrap 生效面）；发布/维护（回退通道可用性验收）

### TOOL-057：Governance Write Guard（直写路径守卫 + 行族对账 + 违规持久状态机，FEAT-011 / FEAT-057 / FEAT-060）

- **文件**：`infra/verify_workflow.py`（`check_governance_write_shapes` + `cmd_governance_write_guard` + face 5 对账/判定函数）+ `infra/write_guard_state.py`（FEAT-060 违规持久状态机 + 消费权台账 + ops 可恢复消费事务——实现实体模块，引擎文件仅保留薄接线，RISK-039 thin-entry 纪律；FIX-381 triage 勘误惯例：锁面按实现实体扩展并披露）
- **子命令**：`governance-write-guard`（post-commit hook Step 4b 自动接线，30s 超时预算；亦可手动复跑）
- **检查面（5 面）**：面 1 plan-tracker 任务行形状（AUDIT-149 §4 M1 两签名）；面 2 evidence-log 机器行族 TRIAGE/RECO 列数 + ID 格式（DEC-168 行族权威）；面 3 agent-locks.json schema（复用 Check 26）；面 4 execution-packets.json 结构（复用 Check 18c 字段表）；面 5 **受管行族对账**（FEAT-057，WARN 姿态）
- **面 5 对账范围**：evidence-log EVD/REVIEW 行、decision-log DEC 行、plan-tracker 任务行（状态列 = 末单元格，写入器 schema）、`.governance/*.ops.jsonl` receipt 台账；凭证判据消费写入器自有形状——governance-store `机器写入：governance-store` 标记（evidence-append/decision-append）、`checks.review_domain.REVIEW_MACHINE_ROW_MARKER`（Check 30c V7 权威）、`task_row_update.STATUS_CELL_OP_SUFFIX_PATTERN`（`〔op-<32hex>〕` 状态锚，末单元格端锚定）、receipt 行 `operation_id`；guard 测试将判据绑定到写入器实建行（标记漂移测试先红）
- **状态基线（新增工件，非修复）**：`.governance/.write-guard-state.json`（schema_version=1；每受管面存 sha256 快路径 + 行级 digest 多重集）。首跑建立基线——存量手写行属历史事实不追溯（amnesty 零 WARN）；此后每轮对账「自上轮以来的行级差分」，改写/新增行无机器凭证 → `unattributed_row_change` WARN（响亮披露 + 写入器指引，退出码不变）；行删除不追溯（归档迁移合法机器面）；TRIAGE/RECO 不做标记判定（写入器先于标记纪律，列数契约已覆盖——Check 30c V7 分类先例）；`governance-store-ops.json`（JSON 文档账本）不做行 diff（BT-4 邻域，后切片）
- **违规持久状态机（FEAT-060，0.88.0 B1——DEC-224 双约束 + arch Q2）**：CLI 路径检测到的 `unattributed_row_change` 额外持久化进 `.governance/.write-guard-violations.json`（守卫自身工件，健康宿主零足迹）——12 规范字段（violation_id/family/object_id/before_hash/after_hash/workflow_run_id/hook_identity/first_seen/occurrence/status〔open/consumed/superseded〕/grant_id/consumption_event）+ 寻址字段（type/file/line/snapshot/session_id/last_seen/escalated/notes）；六规则（观测≠接受/WARN 不改基线〔机制面=基线写入对违规状态零权力；字面「WARN 不前移对账基线」属 FEAT-064 BLOCK 翻转〕/同会话二次独立触发升级〔`GOVERNANCE_SESSION_ID` 注入，未注入保守不升〕/跨会话保留/hook 消费权预授予+单次原子消费/台账损坏不吸收不前移）；消费权闭集注册表（`CONSUMER_REGISTRY`，当前唯一消费者 = guard CLI——post-commit hook 经 CLI 消费，hook 不直接消费）；**消费 + 基线更新走 ops 可恢复事务**（journal `pending_txn` + 世界判定 resume——崩溃仅留 journal 残留，无半状态；实现复用 governance_store `_TargetLock`/`_atomic_write_bytes` 单源；plain 推进与事务/恢复共用同一状态文件锁——P1-1 review-FEAT-060-R0：锁竞争让行披露 `row_family_state_lock_busy`，窗口保持开放复跑重推）。
- **WARN→BLOCK 升级**：留 0.87（version-plan §2 批 1 行声明；0.88 重新排布为 FEAT-064——分族 BLOCK 激活，违规状态机/消费权台账为其前置基座）；输出注释与 docstring 均声明升级边界
- **锁外披露先例**：本守卫不要求 file_lock/agent-locks 在场即可运行（锁缺席不 SKIP 不 FAIL）——对账面以状态基线差分为准，不依赖锁状态；hook ✅ 行后 WARN-gated 计数披露行（`write-guard: N WARN(s) —— run governance-write-guard for details`，N>0 才现——详情需复跑 guard 查看）
- **安全边界**：守卫只检不改——治理记录零写入零改写（faces 1-4 原契约不变）；唯一落盘工件是状态基线文件与违规台账（均为守卫自身工件，非修复），且仅在 CLI 路径（probe 调用——contract-matrix representative 提取/聚合读/测试——零写入、不消费对账窗口、不建台账）；SKIPPED 面 = 产物缺席非缺陷；faces 1-4 非 UTF-8 fail-closed（FIX-333），面 5 不可读面 WARN 披露后跳过
- **发版管线自举面（FIX-383，0.88.0 B2——rollback §8 #7 ⑩拆票之一）**：`write-guard-bootstrap` 子命令——版本切换期发布链（M-1~M-8）依赖的检查器自身状态工件的自举恢复。**converge 模式**（默认）= 一次 guard persist 路径运行（基线 regen/推进 + FEAT-060 三分支查世界事务 resume + 违规重检测/资格消费）+ 收敛后世界判定——只写守卫自身工件，治理记录零写入；未收敛 → 结构化 `manual_intervention` 拒绝 + exit 1（响亮阻断，不静默吸收）。**`--check-only` 模式** = 只读世界判定（五检查：`guard_state_current` 基线在场且 schema 当前 / `row_families_clean` probe 面零问题〔零写入零消费〕/ `violation_ledger_healthy` 台账健康〔R6 损坏不吸收〕/ `no_pending_txn` 待完成消费事务为空 / `ledger_no_drift` 无行号漂移 open 记录——账本行号漂移 = open 违规登记内容摘要不再命中其登记身份；不可判定面缺席记录按资格规则消费，其余 R1/R4 保持 open 响亮）——发布窗口 preflight/审计面 + closure-chain 自举链 `release-window-bootstrap` 的效果探针（FIX-383：查世界不信日志，中断后重入零人工修复）。退出码：0 收敛 / 1 未收敛
- **被以下子工作流使用**：全部阶段（Coordinator 直写后复跑）；CI/CD（post-commit hook 自动面板）；发布（M-1~M-8 版本切换期自举——closure-chain `release-window-bootstrap` 链承载）

### TOOL-050：Loop Runtime Claim Gate

- **文件**：`infra/checks/loop_runtime_claims.py`、`core/loop-runtime-claim-allowlist.json`、`core/loop-runtime-claim-authority.json`
- **子命令**：`check-loop-runtime-claims --product-root <path> --project-root <host> [--scan-mode product_release|installed_host]`
- **输入**：产品根下 `docs/`、`project/`、`skills/` 的全部 Markdown/Python/JSON 候选，以及显式 host root 的四个热治理文件
- **输出**：完整 inventory digest、解析/semantic-unit 数量、notice/fingerprint 计数、typed blocking findings、zero skip/truncate 计数
- **触发条件**：Loop capability wording、review SKILL、历史 0.65.0 解释、policy/authority、发布候选变化后；作为 `check-governance` Check 31 和 release gate 的阻断检查
- **依赖**：packaged policy/authority、AUDIT-133、EVD-707、DEC-104；stdlib-only scanner leaf
- **边界**：只证明 capability claim 与当前证据一致；不激活 Loop runtime、不修复 migration contract、不关闭 RISK-037/RISK-042；无 accept-current/refresh/auto-update
- **被以下子工作流使用**：架构、开发、测试、发布、维护

### TOOL-044：ArchGuard Duplicate Code check

- **文件**：`infra/verify_workflow.py`（`check_duplicate_code`）
- **子命令**：`check-duplicate-code [--fail-on-issues]`
- **输入**：source（`skills/software-project-governance/infra/*.py`）与 projection（`project/e2e-test-project/.../infra/*.py`）文件对
- **输出**：每对的重复率（duplicate_pct）+ 阈值分级（WARN≥60%/ERROR≥80%）；FIX-350 起豁免对（schema `duplicate_code.exclusions`，按 source 相对路径匹配）计入 pairs_checked 并以 `[EXEMPT]` 行披露（DEC-151：豁免必披露，不静默）
- **触发条件**：监控 source/projection 双写腐化、评估拆分收益时
- **依赖**：`core/architecture-health.json` 的 `duplicate_code` 段
- **边界**：**MUST normalize 换行符**（CRLF→LF）+ 忽略空白——否则 source(CRLF) vs projection(LF) 会误判 100% 差异；advisory-only；`__init__.py`/`resolve_entry.py`/`cleanup.py` 三个镜像对为预期同步（RISK-039 双写债），已按 source 路径豁免。
- **被以下子工作流使用**：架构（architecture）、维护（maintenance）

### TOOL-045：ArchGuard Technical Debt check

- **文件**：`infra/verify_workflow.py`（`check_technical_debt`，复用 `_external_validation_read_text`/`_external_validation_canonical_hook_text`）+ `core/technical-debt-ledger.md`
- **子命令**：`check-technical-debt [--fail-on-issues]`
- **输入**：根目录文件、`docs/release/` 版本数、`infra/hooks/*` vs `.git/hooks/*`、`core/technical-debt-ledger.md`
- **输出**：root_residue（游离脚本）、release_docs_versions（历史文档版本数）、hooks_drift（源 vs 已安装内容漂移）、ledger_no_carrying_version（OPEN/IN_PROGRESS 项无承载版本）
- **触发条件**：定期技术债巡检、发布前 hooks 一致性检查
- **依赖**：`core/technical-debt-ledger.md`（manifest 登记）、`core/architecture-health.json`
- **边界**：advisory-only；hooks 漂移检测复用既有 helper（G9 约束）不重复实现；不自动清理游离脚本；release_docs_versions 阈值经 FIX-350 校准为 80（docs/release 全历史保留是蓄意策略——release lineage 可复现性，check-release 依赖该目录；归档评估在阈值再次触及时出槽）。
- **被以下子工作流使用**：维护（maintenance）

### TOOL-046：ArchGuard Complexity check

- **文件**：`infra/verify_workflow.py`（`check_complexity`）
- **子命令**：`check-complexity [--fail-on-issues]`
- **输入**：`core/architecture-health.json` 的 `complexity` 段
- **输出**：0.58.0 `enabled=false` 时返回 line-based proxy 提示；启用时复用 architecture-health 函数行数数据作为圈复杂度代理
- **触发条件**：评估函数复杂度（0.59.0+ 启用 AST 圈复杂度后）
- **依赖**：`core/architecture-health.json`
- **边界**：0.58.0 line-based proxy（AST 圈复杂度留 0.59.0+）；advisory-only。
- **被以下子工作流使用**：架构（architecture）、维护（maintenance）

## 工具与子工作流的关系矩阵

| 工具 | 立项 | 调研 | 选型 | 环境 | 架构 | 开发 | 测试 | CI/CD | 发布 | 运营 | 维护 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 需求澄清 | ● | ○ | ○ | | | | | | | | |
| 技术评审 | | | ● | | ● | | | | | | |
| Code Review | | | | | | ● | | | | | |
| 发布检查 | | | | | | | | | ● | | |
| 发布就绪脚本 | | | | | | | | | ● | | ○ |
| Agent adapter 检查 | | | | | ● | | | | ● | | ● |
| 回顾模板 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● |
| 校验脚本 | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 治理归档 | | | | | | | | | ● | | ● |
| 清理工具 | | | | | | | | | | | ● |
| Git hooks | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 交叉引用检查 | | | | | ● | | | | | | ● |
| 真实 agent runtime E2E | | | | | ○ | | ● | | ● | | ● |
| AI execution packet | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Projection sync guard | | | | | ○ | | ● | | ● | | ● |
| Hot fact-source consistency guard | | | | | ○ | | | | ● | | ● |
| Product Success Contract guard | ● | | | | ○ | ● | ● | | ● | | ● |
| Executable Acceptance Contract guard | | | | | ○ | ● | ● | | ● | | ● |
| Quality Budget Gate | | | | | ○ | ● | ● | ● | ● | | ● |
| Vertical Slice Delivery Packet guard | | | | | ○ | ● | ● | | ● | | ● |
| Weak-LLM Deterministic Scaffold generator/check | ● | ○ | | | ○ | ● | ● | | ● | | ● |
| User Interruption Policy v2 guard | ● | ○ | | | ○ | ● | ● | | ● | | ● |
| Runtime Readiness Matrix guard | | | | | ○ | | ● | | ● | | ● |
| First-Session Measurement guard | | | | | ○ | | ● | | ● | | ● |
| Governance Context Discovery | ● | ○ | | | ○ | ○ | ● | | ● | ● | ● |
| README Pack Guidance guard | ● | | | | ○ | | ● | | ● | | ● |
| Manifest Product Artifact guard | | | | | ○ | | ● | | ● | | ● |
| Governance Pack Status Boundary guard | | | | | ○ | | ● | | ● | | ● |
| Host Capability Context benchmark | | ● | | | ○ | | ● | | ● | | ● |
| Capability Context Selection Trace | | ● | | | ● | ● | ● | | ● | | ● |
| Capability Registry guard | | ● | | | ● | | ● | | ● | | ● |
| Official Submission Ecosystem guard | | ● | | | ○ | | ● | | ● | | ● |
| Mainstream Agent Loading guard | | ● | | | ○ | | ● | | ● | | ● |
| External Project Validation harness | | | | | | | ● | | ● | | ● |
| Dynamic Lifecycle Registry guard | | | | | ● | | ● | | ● | | ● |
| Flow Unit Runtime hot-state guard | | | | | ● | | ● | | ● | | ● |
| Classic Gate Execution Registry guard | | | | | ● | | ● | ● | ● | | ● |
| Dynamic Lifecycle Migration dry-run preview | | | | | ● | | ● | | ● | | ● |
| Local Web Console launcher | ● | | | | | | ● | | | ● | ● |
| 入口引导 bootstrap（resolve_entry 超时兜底） | | | | ● | | | | | ● | ● | ● |
| Declarative Release Ledger | | | | | ● | | ● | | ● | | ● |
| Artifact Projection Generator | | | | | ● | ● | ● | | ● | | ● |
| Optional Quality Tool Probe | | | | | | ● | ● | | ● | | ● |
| 行为灰度开关（legacy 回退通道） | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Governance Write Guard（直写守卫+行族对账） | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |

> ● 主要使用者  ○ 可选用

## 添加新工具的约定

向本工作流添加新工具时：

1. **放置位置**：与阶段强绑定的放在对应 `skills/stage-*/SKILL.md` 或专项 `skills/*/SKILL.md`；跨阶段自动化脚本放在 `skills/software-project-governance/infra/`
2. **命名规范**：`<动词>-<对象>.md`（如 `requirement-clarification.md`）
3. **必须包含**：触发条件、输入输出、执行步骤、独立使用说明、子工作流映射
4. **更新本索引**：在本文件中新增工具条目和关系矩阵
5. **更新校验脚本**：在 `verify_workflow.py` 中补入新工具的存在性检查；若工具是发布/门禁相关行为，优先提供可复跑子命令
