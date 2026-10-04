# 「做薄·开放·主动探索」演进——现状盘点报告（v1）

> 调研日期：2026-10-04 · 作者：Coordinator · 状态：待架构顾问首轮讨论
> 需求源：用户点名（2026-10-04 演进指令）· 目标：做薄、做轻量、开放、主动兼容先进工具/资源/方法论
> 八大核心能力愿景：意图识别 / 事务分解 / 路径规划 / 落盘契约 / 循环演进 / 过程看护 / 主动探索 / 兼容开放

## 1. 用户指令核心解读

1. **痛点**：历史上提出的「主动探测开源社区资源/SOTA 工具」优化（即 DEC-077，2026-06-07）从未在真实任务中触发过一次主动探测行为。
2. **判断**：「一个人/一个工具流打包完成所有事情基本以失败告终」——单体育论已被证伪，必须借力生态。
3. **方向**：把自己做薄做轻量；清理无限叠加责任产生的冗余治理逻辑；提升主动探测使用开源社区代码/工具/资源的能力与兼容性。
4. **硬约束**：本演进所有决策必须与「架构与疑难问题顾问」共同完成；顾问缺席时重试或阻塞等待。

## 2. 规模与结构事实（量化证据）

采集命令：`Get-ChildItem -Recurse -File` + `Measure-Object -Line`（2026-10-04，0.94.0 已发布态）。

| 层/对象 | 规模 | 信号 |
|---|---|---|
| `infra/verify_workflow.py` | **24,805 行**单文件；`def check_/cmd_` 函数 **146 个**；argparse 子命令 **95 个** | 上帝模块（D3 违约实证） |
| `infra/tests/` | 262 文件 **229,422 行**（占 infra 61%） | 测试随生产面同步膨胀 |
| `infra/`（除 tests/__pycache__） | ~110K 行源码（checks 25,742 + release 6,711 + hooks 1,287 + 顶层脚本约 66K） | 治理引擎本体过重 |
| `core/` | 88 文件 7,802 行（lifecycle-registry.json 单文件 2,441 行） | 注册表承载过多行为语义 |
| `references/` | 12 文件 2,218 行（behavior-protocol.md **641**、agent-communication-protocol.md 307、interaction-boundary.md 225） | 协议文本膨胀 |
| 入口注入面 | SKILL.md 367 行 + persona/CLAUDE.md/AGENTS.md bootstrap 段 | 每会话注入协议成本高 |
| skill 库 | 26 个顶层 skill；agents/ 15 个角色文件 | 能力层宽广 |
| `project/e2e-test-project/` | 完整物理复制插件本体（verify_workflow.py 12,533 + test 6,020 行副本） | 物理重复（违反单源） |
| `docs/` | 732 文件 105,035 行 | 文档体量 ≈ 产品的 27% |
| lifecycle 模型 | 三态并存：`active-compatibility-preset` / `schema-only-inactive` / `active-classic-compatibility`（lifecycle-registry.json :34/:70/:1750） | DEC-097 loop 重构迁移未收口，新旧模型叠加 |

## 3. 「主动探索」缺口根因分析（用户最痛点）

**历史交付物盘点**（DEC-077 → 0.45.0 FIX-115/116/117 + 0.46.0 FIX-118，证据：archive/decisions/decisions-v0.1.0-0.59.0.md:79、EVD-449/EVD-463）：

- `core/capability-registry.json`：仅 **8 条宿主能力条目**（codex.desktop.plugin-manifest / skill-entry / capability-context-tool / host.mcp.connectors / browser.in-app-or-chrome-control / agent-team.governance-developer / script.verify-workflow / fallback.local-diagnostic-readonly）——**面向「受限环境宿主能力发现→降级→边界」的防御性静态清单**。
- `capability-context` 命令：诊断宿主缺什么能力，输出 DEGRADED/BLOCKED trace。
- FIX-118 生态定位材料：纯文档（ecosystem-positioning 等），无运行时行为。

**四条根因**（为什么从未触发过一次主动探测）：

| # | 根因 | 证据 |
|---|---|---|
| R1 | 方向错位：DEC-077 把「能力发现」实现成**静态 catalog + 降级诊断**（宿主缺什么），而非**主动搜索行为**（任务需要什么外部资源、社区有什么最优解） | capability-registry.json 全部 8 条目均为宿主侧能力声明 |
| R2 | 行为协议零触发器：behavior-protocol.md（M0-M9，641 行）、SKILL.md 路由表、methodology-routing.md（仅 39 行）中**没有任何一条规则要求在事务分解后/方法论路由时先探测外部生态资源** | methodology-routing.md 39 行仅映射内部 skill |
| R3 | 选择证据面过重：selection trace 契约为受限环境审计设计（source facts/validation command/no-overclaim），日常任务中引用一个开源库/工具**没有低成本落盘通道** | capability-registry 条目 schema 要求 side_effect_boundary/validation_command 等重字段 |
| R4 | 宿主现成借力通道未被协议化：DSH 平台已提供 `web_search`（生态调研）、`route_agent`（多模型专业 agent 路由）等现成能力，治理协议未把「使用它们」定义为任何事务的标准步骤 | SKILL.md 全文无 web_search/route_agent 触发要求 |

**结论**：现有 Capability Discovery 是「防御性能力清单」，用户要的是「进攻性生态借力」——两者方向相反。需要的是**行为层设计**（什么时机、谁、探测什么、如何记录、如何采用），而非更多静态工件。

## 4. 越界责任/自研轮子清单（做薄候选）

工作流自研了以下本可借力外部/宿主/平台机制的能力（每项均为长期维护责任）：

| # | 自研轮子 | 规模 | 可借力方向（待顾问评审） |
|---|---|---|---|
| W1 | 归档/迁移系统（archive.py 3,663 行 + loop_migration.py 2,995 行） | ~6.7K 行 | 数据生命周期可由轻量规则+宿主 git 历史承担 |
| W2 | write-guard/锁/状态机（governance_store.py 2,405 行 + closure_chain.py 3,383 行 + .write-guard-state.json 2,628 行运行态） | ~8.4K 行 | 声明式 schema 校验可换轻量 linter/JSON Schema 工具链 |
| W3 | 发布链系统（release/ 28 文件 6,711 行，M-1~M-7 发布链） | ~6.7K 行 | git tag + conventional commits + 现成 release 工具（release-please/semantic-release 模式） |
| W4 | 自检引擎 146 checks / 95 子命令 | 24.8K 行 | 大多数 check 是历史问题修补的叠加（如 Check 34 R3 引用改形、Check 36/42 口径），可分层为核心不变量（少数）+ 历史观测（归档/降频） |
| W5 | e2e fixture 物理复制插件本体 | ~18.5K 行 | 应为符号链接/安装投影/子模块，不应物理复制 |
| W6 | 治理数据格式自研（plan-tracker.md 表格解析 + 多个 JSON 运行态） | 解析器分散在 verify_workflow.py | 数据面可收敛为单一 schema + 通用解析 |
| W7 | 上下文注入协议三入口（CLAUDE.md/AGENTS.md/SKILL.md 手工同步 + @bootstrap-version 对齐） | 每会话 ~1.5K+ 行注入 | 注入面应最小化为指针+不变量，明细按需加载（FEAT-041 已开头，未完成） |

## 5. 与八大能力愿景的差距映射

| 核心能力 | 现状 | 差距 |
|---|---|---|
| 1 意图识别 | governance-bootstrap 场景检测（A~F） | 有基础；需对齐「用户原始意图」而非「治理场景」 |
| 2 事务分解 | Agent 分发路由表 + task 表 | 有基础；分解后无生态探测步骤（R2） |
| 3 路径规划 | 版本规划/依赖链/loop 模型（三态并存） | loop 重构未收口，legacy 与新模型叠加 |
| 4 落盘契约 | evidence/decision/risk log + execution packet | 成熟但**过重**（证据 schema 成本高） |
| 5 循环演进 | DEC-097 loop-engineering（schema-only-inactive 部分） | 中环/外环未激活，迁移未收口 |
| 6 过程看护 | 146 checks + 11 Gates + hooks | **过度看护**：check 叠加无退出机制，噪音/成本高 |
| 7 主动探索 | capability-registry（防御性）| **核心缺口**：无行为触发器、无低成本选择证据、无外部资源采用面（§3 四根因） |
| 8 兼容开放 | 7 平台 adapter + DEC-012 三层模型 | adapter 面成熟；但对**外部工具/资源生态**的开放（消费侧）缺失 |

## 6. 待与架构顾问讨论的决策点（首轮议程）

- D-A 本职边界定义：治理核心 = 意图对齐 + 契约看护 + 循环闭环？哪些自研轮子（W1~W7）该卸载/替换/降级为宿主能力？
- D-B 做薄路径：verify_workflow.py 上帝模块拆解策略；146 checks 分层标准（核心不变量 vs 历史观测）；「check 退出机制」设计（什么样的 check 可以退休）。
- D-C 主动探索行为设计：生态探测插入点（事务分解后？方法论路由时？）；探测产物形态（轻量 selection trace？research note?）；如何避免重蹈「重证据 schema」覆辙（R3）。
- D-D 兼容开放接口：外部资源采用的协议面（扩展现有 registry or 新建任务级 research artifact or 直接协议化宿主通道 web_search/route_agent）。
- D-E 演进节奏：如何在不破坏当前 11 Gate 全过、0 FAIL 健康态的前提下分阶段做薄（先立后破 vs 冻结增量只做减法）。

## 7. 证据索引

- 规模统计：本报告 §2 表格（2026-10-04 实测命令输出，Coordinator 会话记录）
- DEC-077 原文：`.governance/archive/decisions/decisions-v0.1.0-0.59.0.md` L79
- capability-registry 现状：`skills/software-project-governance/core/capability-registry.json`（8 条目实测）
- lifecycle 三态：`core/lifecycle-registry.json` L34/L70/L1750
- 深检基线：`check-governance --summary-only` → `Governance: [PASS]`（2026-10-04）
