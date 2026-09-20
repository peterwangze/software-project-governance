# version-plan-0.86.0 —— 确定性核心架构演进（第一版：写入器时代）

> REL-082 工作产物 · 状态: Release 半面 R0=NEEDS_CHANGE 修订版（设计半面已 R1 通过）· 落位注记: 本文件在 docs/planning/（先例多在 docs/release/——因 REL-082 锁面在此且属规划双文档族，不迁位，注记披露）
> 依据: 0.86.0-architecture-evolution.md（设计）· boundary-audit.md（盘点）· arch-consult-round1/round2-external/round3-external.md（顾问三轮）· review-REL-082-DESIGN-R0/R1 + RELEASE-R0（审查链）
> 日期: 2026-09-19 · 上游: 0.85.0（REL-081，发布中——**M-1 版本 bump MUST 排他在 0.85.0 M-8 归档完成后**〔共享冻结面 13 文件活跃中，RISK-054 同族先例〕）

## 0. semver bump 论证与版本占用（Release R0 R-F1 补全）

- **bump 裁定：0.85.0 → 0.86.0 MINOR**。依据：载荷=四类新写入器 CLI（task-row-update/governance_store 双 append/locks-extend/amend）+ contracts.py 契约 MUST 规则扩展 + write-guard 行族全覆盖上线路由——新增受治理能力面，无 breaking（既有 CLI/记录格式零破坏；write-guard 为 WARN 姿态上线路由非门禁硬化→L11 无触发面）。
- **占用/跳号核查**（Release Reviewer R0 V5 代验，本计划引用）：无 0.86.0 roadmap 行占用；tag 序至 v0.84.0；0.85.0 在途未 tag→顺延不跳号；CHANGELOG 最新段 0.84.0、0.85.0 段未入（在途）→顺序承载无冲突。
- **roadmap 0.86.0 行提案文本**（M-1 时 Coordinator 写入 plan-tracker 版本规划节）：
  `| 0.86.0 | 确定性核心架构演进第一版：写入器时代 | 批 0 契约冻结（FEAT-049）→ 批 1 原子写入器三票 → 批 2 closure 纵切+混沌发布门；受管状态变更零人工直写+全部可对账（0.87.0+ 存储分离/链铺开） | REL-082 |`

## 1. 版本主题与范围

**主题**：四类可靠原子写入器 + 一条可恢复标准闭环 + 接管范围内零手写（DEC-220 公理首次落地）。

**In scope（M0~M3 各一纵切）**：
- M0 契约冻结：状态语义/版本协议/operation_id/错误码/schema 版本（L0 contracts.py 承载）
- M1 原子状态件：`task-row-update`（转移合法性表+锚定+凭证 join）· `locks-extend/amend`
- M2 追加写入器：`evidence-append`（骨架+类型化 --refs）· `decision-append` · write-guard 行族全覆盖
- M3 闭环纵切：一条标准 closure-chain（effect-based resume/UNKNOWN 态/独立事件日志/混沌测试）
- 伴随纪律：BaselineMetadata provenance schema+存量数值门登记 · W-4 扫描器禁入语义区入审查项 · 全部新 CLI 过 §4 DoD 九条
- 搭车（纯复用窗口允许时）：B-6 snapshot-render

**Out of scope（0.87.0+）**：closure 铺开（取消/重开/异常接管）· 存储分离 JSON 化（首表 decision-log）· B-7 index-rebuild · 大表迁移 · 发版管线自举。

**范围变更控制**：M0~M3 任一项受阻不得静默砍——按回退树升级用户。

## 2. 批次划分（R0 修订版——批 0 阻塞依赖 + 文件面冻结）

### 批 0（串行先行——批 1 的显式阻塞依赖；arch 顾问第三轮 P1-1 裁决）
| 票 | 内容 | 文件面（冻结） | 验收入口 |
|---|---|---|---|
| FEAT-049 | **M0 契约冻结与验收基座**：**扩展既有 `contracts.py`**（FEAT-021〔906b209〕交付的 L0 最小契约层 466 行 + FIX-303〔4fcc354〕——非新建；**约束：不破坏既有 frozen 形状，87 存量契约测试零回归**）——新增：operation_id 产生/作用域/重试复用/同 ID 异载荷处置；状态与合法迁移——含执行态 UNKNOWN 与评估态 NOT_EVALUABLE 区分；错误码及重试/人工分类；schema 版本字段/兼容规则/未知版本处理；写入器最小 I/O 与效果判定契约。交付物另含：版本化契约 fixtures + 可运行契约测试 + 三张批 1 票的契约引用与变更规则 + **量测协议工件（benchmarks/closure/protocol.md+固定用例组三路径）** + **M0 契约源 pin revision 记录**（behavior-protocol.md 转移表/SKILL.md 相关段的内容摘要锚——记入 fixtures manifest 供批 2.0 复跑对照） | `skills/software-project-governance/infra/contracts.py`（扩展既有）+ `infra/tests/test_contracts.py`（扩展既有）+ fixtures + `benchmarks/closure/protocol.md`（新） | 契约测试通过 = 冻结 revision；批 2.0 复跑 = 兼容性回归（非补做验收）；**关闭证据四项**：谁交付/产物在哪/验收命令/哪些票被阻塞 |

依赖图：批 0 → 契约测试通过冻结 revision → 批 1（各票消费同一冻结 revision；M0 产物为共享只读依赖——修改触发契约变更流程：提变更→更新 M0 基线→识别受影响票→重跑验收，实现票不得直接改共享语义）→ 批 2.0（复跑 M0 契约测试+跨票集成验收）→ closure/混沌发布门。

### 批 1（并行 ≤3，文件面不相交——**宣告可并行前冻结**〔arch P2-c〕）
| 票 | 内容 | 文件面（冻结裁定） |
|---|---|---|
| FEAT-042R | task-row-update CLI（B-1 根）：M7.4 转移合法性表可执行化 + task_id 锚定 + 翻转凭证结构 join（WARN 姿态） | `infra/task_row_update.py`（新）+ `infra/tests/test_task_row_update.py`（新）——消费 contracts.py 只读 |
| FEAT-046 | locks-extend/amend + evidence-append/decision-append（同管道族） | **裁定：`infra/governance_store.py` 新建独立文件**（不并入既有——owner=FEAT-046 串行集成；与 FEAT-042R 文件面不相交）+ `infra/tests/test_governance_store.py`（新） |
| FEAT-047 | BaselineMetadata provenance schema + 存量数值门登记（Q-4 纪律票） | `infra/baseline_metadata.py`（新）+ `infra/tests/test_baseline_metadata.py`（新）+ 既有数值门只读接入 |

**批 2（串行，依赖批 1 原子件）**：
| 步 | 内容 |
|---|---|
| 2.0 | **closure-chain 依赖盘点实测**（批 1 产物接口冻结确认——M0 验收复跑） |
| 2.1 | closure-chain 纵切（FEAT-048）：一条标准链 + effect-based resume + UNKNOWN 态 + 独立事件日志 |
| 2.2 | **混沌测试**（发布门）：commit 失败/push 凭据失败/push 超时 UNKNOWN 三边界各 kill 一次 → resume 零人工修复 |
| 2.3 | write-guard 行族全覆盖 + 接管范围「零手写」硬门禁上线路由（WARN 姿态——BLOCK 升级留 0.87） |

**M-1~M-8 标准发布链**照旧（候选打包/门禁实测/双半面审查/transition/tag v0.86.0/push/归档）；M-2 门禁实测 MUST 含混沌测试复演。

## 3. 验收口径（R0 修订版——三维拆分，arch 第三轮 P1-2 裁决）

> 撤回先前「对照 0.85.0 实测 ≥5 段降至 ≤2」表述——该基线无 provenance（EVD-1101 记 4 段/boundary-audit 记 5-8 步，互不一致且无测量口径）。三方历史陈述列为**待核实**，不得合并为单一数字。

| 维度 | 口径 | 判定 |
|---|---|---|
| ① 历史相对改善 | 旧版→新版确定性环节 LLM 往返减少量 | **NOT_EVALUABLE**（无可信基线时不得宣传达成；按下方量测协议建基线后可转可评估） |
| ② 新版绝对目标 | **标准 closure 路径 LLM 逻辑往返 ≤2**（明确限定：一次逻辑模型请求响应计一次，流式分片不另计，工具结果后再响应另计，传输层重试单列；不含规划/评审/返工环节——那些非写入器可控变量） | M3 落地后按协议实测判定 |
| ③ 机制正确性 | 原子性/幂等/恢复/门禁按功能与故障测试验收（混沌测试 3 边界 kill+resume 零人工修复） | 独立可验证，不受旧基线缺失影响 |

**量测协议**（M0 批 0 内冻结）：测量起止点定义/标准与异常路径分类/人工干预与失败样本记录法/模型与提示模板与工具配置与代码 revision 记录/原始 trace 保留。固定用例组（标准成功/冲突/恢复三路径）旧新同协议测量。工件落 `benchmarks/closure/{protocol.md, cases/, runs/<run-id>/{manifest.json, results.jsonl, summary.md}}`（标准库生成；敏感脱敏；测量工件 JSON ≠ 业务存储 JSON 化前移）。无 trace 且旧版可运行=旧版重演基线（明确非"历史实测"）；无法恢复等价环境=相对指标维持 NOT_EVALUABLE 记原因。**不得测得新版 3 次后为过门改门槛**——改目标=有理由有版本记录的需求变更。

**「零手写」验收定义**（R0 修订——arch P2-d）：更名「**受管状态变更零人工直写，且全部变更可与合法写入操作对账**」。三指标：未对账变更数=0（受管文件变更均有合法操作解释）/对账覆盖率=100%（列明覆盖文件字段范围）/人工恢复干预次数（标准路径=0，故障路径单列不隐藏）。验收方法=验收窗口起止快照差异 vs 操作记录比对（hook 拦截计数仅辅助——绕过 hook 不被计数）。证明的是"验收范围内没有未记录直写"，非"维护者从未打开编辑器"。

**机制验收补充**：verify_workflow 全子命令 PASSED · archguard R1 基线不升 · R6 启动预算不超 · 全部新 CLI 过 DoD 九条 · BT-8 绕行分层检测（冻结受管清单/操作记录/release 对账/五类异常检查——边界声明：不抗同权限伪造攻击者，真防恶意写者需仓库权限或受保护 CI）· BT-9 混沌 kill 语义（子进程+父控制器+命名故障点；Popen.kill 跨平台终止；硬终止与抛异常两类分开；kill≠掉电持久性保证；注入接口仅内部测试入口）。

## 4. 回退决策树（R0 修订版——交付裁决与运行处置两层分离，arch P1-3 裁决）

### 第一层：交付裁决（三选一，互斥）
| 分支 | 定义 | 交付结果 |
|---|---|---|
| **A 完整交付** | 修复后通过原 DoD（必要时顺延整个发布） | 本版目标完整完成 |
| **B 明确延期** | 本次不交付该面，承诺迁入**确定的后续里程碑** | 范围调整——不得宣称原范围完整完成 |
| **C 撤回规划** | 撤销本次实施承诺，回 planning 重判必要性与方案 | 无确定交付承诺 |

**硬规则**：DoD 不得静默降低。原范围未完成时只能整体顺延或通过显式范围变更批准延期/撤回；**部分发布不得标记原计划完整完成**。「其余照发」必须证明该面可隔离且其余能力不依赖其未满足契约——M0/核心写入器/effect-based resume 基础不变量不得因其他票完成而被绕过发布。

### 第二层：运行处置（可与任一分支组合）
禁用该能力 / 只读 / 使用已验证旧路径 / 启用**预先定义且单独验收**的降级 profile（behavior_profile 非豁免标签——须提前规定可用禁止操作/必须满足的安全一致性不变量/明确失败方式/进入退出条件/恢复测试）/ 无法安全隔离则阻止发布。**不能故障后临时发明 profile 把原目标改称已完成**；撤销功能≠撤销历史副作用（已发生动作按前向恢复收尾）。

### 状态语义三分（DoD/完成态不得混淆）
实现状态（BLOCKED/...）· 交付裁决（deferred/withdrawn/...）· 运行姿态（disabled/read_only/validated_fallback/...）

### 触发与升级
- **R1（某写入器/链不可达验收）**→ 第一层三选一（用户裁决——DEC-221 保留边界）+ 第二层组合
- **R2（混沌测试不过且短期不可修）**→ closure-chain 选 B（迁 0.87.0 确定里程碑）；原子 CLI 照发（批 0/1 独立价值保全）——用户确认
- **R3（M0 契约与既有机录冲突不可调和）**→ 暂停 0.86.0 全链，C 撤回 planning，用户架构裁决

## 5. 候选池衔接与跨版承接（Release R0 修订）

- FEAT-043（计划期试点前置纪律）→ 并入 FEAT-047（provenance 票）实施；**FEAT-044（回合心跳）/FEAT-045（并行段识别）→ 0.87.0 候选**（closure 铺开时一并——两文档口径统一）；既有 P3 残留池照旧独立裁决。
- **0.85.0 回退分支承接预声明（R-F6）**：0.85.0 回退树 R1~R3/选项 c/降级分支多处标注顺延 0.86.0（翻 hard+P3-3、①瘦身、⑧ entry-skill、FEAT-039 预算面族、RISK-057/058 复评窗）——**按 DEC-221 范围变更保留边界：任何承接均升请用户裁决后并入，不自动并入本计划范围**。若 0.85.0 出现顺延项，本计划范围重审（可能触发 R1 第一层交付裁决）。
- **B-延期分支版本号语义（R-F7）**：R2（closure 迁 0.87.0）情形下**默认缩范围发 v0.86.0**（批 0/批 1 独立价值保全）+ CHANGELOG 显式 `deferred` 披露——不采用顺延合并 0.87.0（与 DEC-221「tag v0.86.0」授权字面冲突需新裁决，无必要不触发）；若用户在 R2 裁决时另选顺延，按范围变更走 DEC-221 保留边界。

## 5.5 发布执行细则（Release R0 R-F4/R-F5/R-F9~F11 处置）

- **注入预算交互（R-F4）**：0.85.0 批 2.3 翻 hard 后 standard/strict 为 hard 门——0.86.0 全部新增文本面（contracts/fixtures/测试/文档）**承诺零注入面文本新增**（六面清单锚 `INJECTION_BUDGET_SURFACES`——不触 persona/entry/secondary/agent-instructions/SKILL 注入段；SKILL.md 若需新增仅限 report-only skill 层并逐项预算）。「strict 余量 34 tok」为 FEAT-041 Developer 申报值（EVD 未落）——**不作规划输入**；0.86.0 M-2 门禁实测以**批 2.2 canonical 重测当场值**为动态口径。
- **benchmarks/closure 入库策略（R-F5）**：仓库根 `benchmarks/closure/`——`protocol.md` + `cases/` 入库（版本化协议与用例是发布产物）；`runs/` 加入 .gitignore（本地保留原始 trace，敏感面不出仓库外但不入 git 历史）+ EVD 记 run-id 与摘要（可追溯不膨胀）。
- **M-2 混沌复演承载（R-F9）**：进 release checklist（release-checklist SKILL 面）gate 行「混沌三边界复演零人工修复（隔离 remote——不产生真实远端副作用〔Release R0 边缘②〕）」。
- **NOT_EVALUABLE 措辞规则（R-F10）**：CHANGELOG/roadmap 中维度①（历史相对改善）固定措辞「基线不可评估（无可信历史 trace）——未宣传达成」；发布不受阻（三维表口径）。
- **对账快照执行点（R-F11）**：起点=批 1 首票派发前快照；终点=批 2.3 完成时快照；M-2 执行比对（差异 vs 操作记录）；证据入 release checklist + EVD。

## 6. 交付物清单与审查链状态

本文件 + 0.86.0-architecture-evolution.md + boundary-audit.md + arch-consult-round1.md + arch-consult-round2-external.md + arch-consult-round3-external.md（顾问原文保全——DEC-221 义务③）。审查链：**设计半面 R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0（机录 REVIEW-REL-082-R0/R1）✅**；**发布半面 R0 NEEDS_CHANGE（R-F1~F12）→ 本修订版 → R1 定向复审（同 Reviewer，逐条比对 R-F1~F12）**；发布半面通过 → DEC-221 生效确认 EVD（设计打磨完成留痕——含第 6 次手工编辑事故佐证行〔R0-N2〕）→ 批 0 派发（FEAT-049）。**M-4 版本发布授权出处：DEC-221（用户预授权「授权发布对应版本」）**；M-0 用户裁定采纳已由 DEC-221 前置裁定承载（「完成整体的设计规划之后」=本计划打磨完成时点）。
