# 架构演进与重构路线图 0.80.0（AUDIT-150 Phase 3 Design Doc / ADR）

> **Version**: 0.80.0-proposed（设计文档；版本承载以 Design Reviewer 审查通过 + DEC-183 入账为准）
> **Status**: Proposed → R0 notes closed（2026-09-09，REVIEW-AUDIT-150-R0 APPROVED_WITH_NOTES/0）
> **Triggering decisions / inputs**: 用户 2026-09-09 授权指令（最高约束：架构腐化系统性梳理 + 重构规划；零功能/性能回退、零问题回归）→ AUDIT-150 Phase 1 事实基线（`architecture-audit-facts-0.80.0.md`，下称 **facts**）→ Phase 2 架构顾问咨询（2026-09-09 arch 路由，下称**顾问**，逐项表态见各节 + 附录 A）
> **Risk addressed**: RISK-039（架构腐化看护缺口，打开）、RISK-044（summary-only 墙钟，缓解中——承接 0.79.0 复评结论）、RISK-048（测试环境敏感，打开——方法论承接）
> **History**: DEC-083（拆分路线图）→ DEC-088（ROI 修正：净收益 ~260 行实证）→ DEC-090/091（降级 SoD）→ DEC-145（重启=新任务新版本号）→ 本设计（0.80.0 重构线，遵守 DEC-145 原则启用新版本槽）
> **Scope**: 分析与设计文档 + 可执行任务清单 ONLY。本轮不修改任何产品代码、不修改 .governance/。重构执行任务逐项另行 triage（ID 由 Coordinator 侧 change-triage 机器分配——本文用语义化占位名 `REFACTOR-*`）。
> **事实基线时点**: 2026-09-09 HEAD（facts 附录快照）。本文所有度量数字仅引用 facts 节号，不重复度量。

---

## 0. ADR 字段映射（硬门槛自检入口）

| ADR 必备字段 | 承载章节 | 完备性 |
|---|---|---|
| 标题 | 文档标题 + §3.1 决策命题 | ✅ |
| 日期 | 2026-09-09（度量基线）+ 2026-09-09（本文撰写） | ✅ |
| 背景 | §1 + §2（facts 索引） | ✅ |
| 决策 | §3（目标架构）+ §4~§9（机制设计）+ §13（DEC-183 候选） | ✅ |
| 备选方案 | §12（ALT-A~D，≥2 满足：4 个） | ✅ |
| 排除理由 | §12 逐项（引用 facts 编号论证） | ✅ |
| 影响 | §13 DEC-183「影响」列 + §11 | ✅ |
| 后续动作 | §10 可执行任务清单 + §13「后续」列 | ✅ |
| 可逆性标注 | §3.8（逐决策可逆性） | ✅ |
| 蓝军挑战 ≥3 | §11.2（BC-1~BC-4，独立 ID + 缓解） | ✅ |
| 模块无循环依赖 | §3.3（目标依赖图 DAG 声明 + 机器判定规则 R3） | ✅ |
| 候选方案 ≥2 | §12（4 个） | ✅ |
| 非功能需求逐项措施 | §9.6 覆盖矩阵 | ✅ |
| 数据缺口 7 项处理 | §2.3 | ✅ |

---

## 1. 目标与非目标

### 1.1 用户目标映射（2026-09-09 指令原文归纳）

| # | 用户目标 | 本设计承接 | 主承载章节 |
|---|---|---|---|
| G1 | 架构演进规划——面向未来设计、高性能、可扩展、可维护 | 目标架构（分层 + 依赖方向 + 契约核心）+ 性能策略 | §3、§9 |
| G2 | 实现整理——清冗余、重构不合理逻辑、业务逻辑与公共基础设施分层解耦、底层逻辑归一聚合 | `_vw()` 反向耦合消除 + 层间解耦 + 单源资产（投影/夹具/索引）+ 数据表归宿 | §3.4、§5、§6、§7 |
| G3 | 好设计简化实现、去重防膨胀 | 缩容守门棘轮（防再膨胀）+ 高收益去重切片 + 渲染抽取 | §4、§10 |
| B1 | 零功能回退、零问题回归 | 契约矩阵 + 差分测试 + 测试基线修正前置 | §8 |
| B2 | 零性能回退 | 性能测量协议 + 成对比较 + 容差门禁 | §9 |

**总目标一句话**：不是"把 24,252 行压到某个数字"（顾问决策摘要，采纳），而是**稳定 CLI 契约、消除反向依赖、建立新功能无法继续污染旧入口的结构约束（棘轮），并让投影、归档、性能具有可验证的演进路径**。

### 1.2 非目标（本轮重构线"不做什么"——过度工程化防线）

每条非目标附"为什么不做的当前理由"（stage-architecture 过度工程化防线：每个设计决策必须有当前需要的原因）：

| # | 非目标 | 理由（事实依据） |
|---|---|---|
| NG-1 | 不做大爆炸重写 | facts §9 消费方矩阵（post-commit hook + CI 4 步 + 6 平台适配器）在无契约护栏下重写无法证明零回归（B1 义务不可达）；EVD-632 实证 ~16,000 行业务逻辑是 74 命令 × 治理规则的真实产物，重写引入新缺陷面而非消除复杂度 |
| NG-2 | 不预设全仓净减行数承诺 | DEC-088 链实证：拆分 ROI 曾被高估 ~1,100 行、实测 ~260 行（EVD-632）；顾问 Q2 采纳——追踪"产品逻辑体积"与"胶水体积"分开，不承诺净减总数 |
| NG-3 | 不引入第三方依赖/后台服务/动态插件机制 | facts §9.4：生产代码零第三方（stdlib-only 是既定运行面约束）；顾问 Q7 采纳——受控 loader 白名单即可 |
| NG-4 | 不做 70 套 Check 注册样板（一项≠一个文件） | EVD-632"32/53 段独特逻辑无法泛化"证明拆文件本身不减复杂度；顾问 Q1 采纳（详见 §3.5 表态） |
| NG-5 | 不把独特治理规则塞通用 DSL/表驱动引擎 | AUDIT-124 结论 + 顾问 Q3 判断标准（§5.1）；表驱动只用于已证可泛化的边界 |
| NG-6 | 不在本轮修改产品代码 / 治理记录 | AUDIT-150 任务边界：本轮仅设计 + 任务清单；DEC-183 以 proposed 文本附于 §13 由 Coordinator 写回 |
| NG-7 | 不覆盖 0.79.0 已入槽范围 | DEC-177 已裁决 0.79.0 范围（含 quick-scan 前移评估、FIX-292 等）；本设计只承接其结论作输入，不重排其范围；与 0.79.0 收尾可并行项在 §10 单独标注 |
| NG-8 | 不为缩行制造解释器/通用 DSL | 顾问决策摘要采纳 + DEC-088"业务逻辑 ~16000 行是合理复杂度"（facts §8.10）——保留真实复杂度，消灭偶然复杂度 |
| NG-9 | 不引入 SQLite/JSONL 权威日志作为初期交付 | 顾问 Q5 采纳（派生 JSON 索引初期推荐；SQLite 证据驱动后置——§7.4） |

---

## 2. 现状诊断索引（只引用 facts 节号，不重复度量）

### 2.1 Top 问题按影响排序

排序依据 = 对 G1~G3/B1~B2 目标的阻碍面 × 触及的消费者面（facts §9）。

| 排序 | 问题 | facts 出处 | 影响一句话 |
|---|---|---|---|
| **P-1** | 巨石 + 反向耦合：verify_workflow.py 24,252 行 / 504 def / 74 cmd_* / 80 dispatch 键 / 70 Check 段；19 个内部 import 源 + checks 子模块经 `_vw()` 延迟回访主文件共享全局（review_domain 59 符号最大耦合面） | §3.1、§3.2、§3.3、§4.1（L285 耦合方向事实） | 任何新增检查/命令都被迫触碰巨石多区段（§9.7 触碰面样本：FEAT-016 单组件 5 类文件、FEAT-011 单命令 3 区段+2 外部文件）；分层解耦（G2）被反向依赖锁死 |
| **P-2** | 防腐化看护失效：tag 曲线锯齿形——两次拆分窗口（v0.58→0.60 -616；v0.65→0.70 -1,631）均被更大斜率覆盖（+1,410/+2,766/+1,303），v0.70.0→HEAD 净增 4,069 行超历史峰值 11.3%；RISK-039 原文"全部在零告警下发生" | §4.3、§8.1（RISK-039 行） | 无结构性棘轮 ⇒ 拆分成果必然回吐（G3 防膨胀不可达）；这是历史两轮拆分失败的根因，优先级高于拆分本身 |
| **P-3** | 测试基线不可信：2,201 `def test_` vs 最近采信 788 ran（单文件）/ 全量采信记录多时点漂移（1,768→1,976→788）；1 fail 既有定性；环境敏感失败族（bash/WSL ×24、loop-runtime 抖动、median<8s 超阈） | §7.1、§7.2、§10-缺口1、§8.1（RISK-048） | 零回归义务（B1）当前**不可证明**——重构切片的每步验收门都依赖它；必须前置修正 |
| **P-4** | 重复与投影面失控：15 投影 + 8 标记面 + 6 版本钉手工协同；e2e 91 同名文件（60 SAMELOC / 31 DIFF 快照落后 ~10k 行）；28p by-design dup 3 对 | §5.1、§5.3、§5.4 | 单源缺失（G2 清冗余）：同一逻辑最多存在 3+ 份副本；发布投影靠纪律非靠生成器闭环 |
| **P-5** | 治理数据生命周期断裂：热文件 plan-tracker 344.1KB / evidence-log 1,419.5KB（28s 双 ERROR advisory）；归档器"触发器满足但无可归档数据"（识别失效） | §6.1、§6.2、§6.3 | agent 上下文预算被热文件吃穿（256KB 单读限制，FIX-160 note）；归档语义失效 ⇒ 数据只增不缩 |
| **P-6** | 已知缺陷悬置：cmd_check_release F-1 恒 exit 1（HEAD L20568 本会话抽查复核仍在，无守卫无注释）；Check 31 身份子相位口径差未定位；hook 接线缺口（FIX-297 L37 承接为后续候选） | §8.3、§8.4、§8.7 | 零问题回归（B2 前提）要求先区分"既有缺陷经批准纠正"与"行为保持"（顾问决策摘要采纳）——悬置缺陷污染差分基线 |
| **P-7** | 编排/渲染耦合：1,315 处 print；`_run_full_engine_checks` ~1,695 行承载 70 段逐段编排；三段以上同构 `print(标题)→调 check→遍历 issues→打印` 模板 | §3.1、§3.3、§3.5 | 渲染不可独立演进/测试；cmd_check_governance 历史实测 1,126 行中 437 行 print（EVD-630） |

### 2.2 历史拆分链结论承接（DEC-083 → DEC-088 → DEC-145）

本设计**不推翻** DEC-088 的"拆分整体 ROI 有限"结论（顾问决策摘要同见）——它证明的是：**业务逻辑难以靠位置搬运/表驱动显著压缩**，不证明依赖治理（P-1）、棘轮看护（P-2）、发布去重（P-4）、数据生命周期（P-5）没有价值。历史结论原文锚点（facts §8.10）：

- DEC-083（2026-06-24）：渐进按 check 域拆分、终态 <500 行薄入口——**方向保留，机制修正**（本设计 §8 绞杀者 + §4 棘轮取代"每版拆 1~2 域"的纯人工纪律）。
- DEC-088 / EVD-632（2026-06-27）：re-export 搬运不降行数；体量大头在数据表与 print 编排；~16,000 行业务逻辑是合理复杂度；净收益 ~260 行——**采纳为边界条件**：重构收益重定位到 P-1/P-2/P-4/P-5（结构性收益），行数只作棘轮观测值不作目标。
- DEC-103：禁止以 re-export 伪装 God module 拆分——**采纳**：切片验收必须含"旧入口调用行净减 + 豁免缩减"，纯搬运不算切片完成（§8.4 验收门）。
- DEC-145（2026-08-22）：重启=新任务新版本号——**遵守**：本设计即 0.80.0 新重构线基线（DEC-183），不复用停滞的 FIX-155/156/REL-047 行。

### 2.3 facts 数据缺口 7 项对应处理（设计不依赖缺口数据，或显式标注假设）

| facts 缺口 # | 内容 | 本设计处理 |
|---|---|---|
| 1 | 无 2026-09-09 当日全量测试数字 | **设计不依赖**：§8.1 将"全量基线建立"本身列为 P0 前置任务（REFACTOR-test-baseline-audit）；在此之前一切切片验收门以"当轮全量 + 契约差分"为准，不引用历史漂移数字 |
| 2 | 健康摘要 26 vs 27 差 1 未归因 | **设计不依赖**：面板计数不作门禁输入；棘轮门（§4）使用独立机器基线文件 |
| 3 | status 墙钟无可比基线（0.49~0.56s vs 4.04s 跨时点） | **显式假设**：性能门禁只认 §9.5 协议下的成对相对比较；绝对值仅作观测范围（顾问 P0-⑤ 同款） |
| 4 | e2e 31 DIFF 文件逐 hunk 差异未展开 | **设计不依赖 hunk 内容**：五分类处置（§6.3）按"快照时点 + 是否被 check-projection-sync 守护"判定，与 hunk 内容无关 |
| 5 | loop_runtime_claim_attestation.py 两口径行数 | **不依赖**：模块归宿决策与行数口径无关 |
| 6 | 非 dsh 适配器 claim→evidence 等级映射无实现面 | **不依赖**：DEC-179/180 已限定为后续候选未 triage；本设计适配器面只涉及"投影单源覆盖 5 平台 JSON + package.json"（facts §5.1），不涉及等级映射 |
| 7 | v0.58.0 之前 tag 曲线未测 | **不依赖**：棘轮基线锚定 HEAD（2026-09-09），历史曲线仅作形态证据 |

---

## 3. 目标架构

### 3.1 决策命题（一句话）

**采纳"薄入口 + 契约核心 + 应用编排 + 领域检查插件 + 基础设施端口 + 渲染/CLI + 组合根"的六层单向架构，以绞杀者切片从 verify_workflow.py 巨石渐进迁移，棘轮守门保证只进不退。**

### 3.2 分层图（文字版）与各层职责（≤3 句）

依赖方向：**只允许上层 import 下层（编号小者）；任何反向 import = 违规（R2/R3 机器判定）**。

```
L6 组合根（composition root：按命令装配实现、提供执行上下文）
   │ 唯一允许 import 全部具体实现的层
L5 渲染与 CLI 兼容层（renderers + 80 键兼容入口）
   │ 消费 L4 的聚合结果，产出 stdout/stderr/exit code
L4 应用编排层（命令用例、检查选择 full/quick、依赖排序、结果聚合）
   │ 只经 L0 端口与 L2 打交道
L3 领域检查插件（checks/<domain>/：review / projection / archive / identity / …）
   │ 只依赖 L0 契约 + 自带数据；禁止互相 import
L2 基础设施实现（Markdown 解析、Git、文件、索引、原子写入、时钟）
   │ 实现 L0 端口；不含治理业务政策
L1 数据资产层（权威 Markdown 治理原文 / JSON registry / 派生索引与热视图〔可重建〕）
   │ 被读写的数据本身，非代码
L0 核心契约（Check ID / Finding / Result / 执行上下文 / 端口接口 / 插件元信息）
   │ 零依赖（仅 stdlib 类型）；任何层都可依赖它

〔横切〕ArchGuard 棘轮门（§4）+ 契约差分（§8.2）+ 全量测试 + 性能门禁（§9）+ 数据恢复验证（§7.5）
〔构建链〕规范源 + 平台模板 + 版本源 → 确定性生成器 → 投影 / 发布产物 / 集成夹具（§6）
〔遗留〕verify_workflow.py = 旧入口薄兼容壳（终态：L5 的一个兼容 facade + L6 装配，行数只降不升）
```

各层职责（≤3 句/层，顾问 Q1 表格采纳为基底）：

| 层 | 职责（≤3 句） | 明确禁止 |
|---|---|---|
| L0 核心契约 | 定义 Check ID、Finding、Result、执行上下文与端口接口、插件/命令注册元信息的纯类型与协议。全部为 stdlib 类型/dataclass，零 I/O。任何层可依赖，自身不依赖任何层。 | 文件读写、CLI 输出、import 任何具体检查/实现 |
| L1 数据资产 | 权威治理原文（Markdown）+ 版本化 JSON registry + 可重建的派生索引/热视图。单一权威源原则：每个事实只有一个权威位置（§6/§7）。 | —（数据层无代码职责） |
| L2 基础设施实现 | 实现 L0 端口：文件/Git/Markdown 解析、索引构建、原子写入（沿 release/projection.py journal 先例，facts §5.1）、时钟。 | 决定治理合规与否的业务政策 |
| L3 领域检查插件 | 每域一个包（checks/review/、checks/projection/…），承载独特治理规则、事实解释、Finding 产生。共域短小检查可共文件（§3.5）。 | print/终端输出、CLI dispatch、`_vw()` 回访、检查间互相 import、隐式全局 |
| L4 应用编排 | 命令用例编排、检查选择（full/quick/域选择，§9.3）、执行排序、结果聚合为 Result。 | Markdown 解析细节、终端排版 |
| L5 渲染与 CLI | 参数解析（80 键兼容）、输出格式（文本/JSON/兼容输出）、退出码映射。 | 执行业务判断、直接扫描治理数据 |
| L6 组合根 | 按命令装配 L2 实现 + L3 插件 + L4 用例，创建命令范围执行上下文（含共享快照缓存，§9.2）。 | 承载业务逻辑、import 时实例化全部服务（§9.1 懒加载） |

**DAG 声明（硬门槛：模块无循环依赖）**：L0→{L2,L3,L4,L5,L6} 之外，允许的依赖边仅 {L6→L5,L4,L3,L2,L0；L5→L4,L0；L4→L3,L2,L0；L3→L0；L2→L0}，共 12 条有向边、无环（枚举集为唯一权威事实源，计数为派生校验值；15 = C(6,2) 完全 DAG，会放行 L5→L3、L5→L2、L3→L2 三条违规层依赖边，与上表层级职责冲突，不采）。机器判定 = AST import 图 + 允许矩阵 + 强连通分量（SCC=0）检查（§4 规则 R3）。遗留容忍环仅存在于治理数据面（AUDIT-146→FEAT-010→AUDIT-146，facts §4.1 / FIX-237.2 cycle tolerance）——属任务依赖数据，不在代码 DAG 内，由 REFACTOR-governance-record-model（§7.2）在记录模型中显式化。

### 3.3 与既有 checks/*_domain.py 的关系（渐进绞杀，非推倒）

facts §4.1 实测已有 15 个 checks 子模块 + 4 个 release 子模块被 verify_workflow import——**这些是绞杀者的第一批骨架**，但当前形态违规：经 `_vw()` 反向回访（L3→遗留巨石）。演进方式：每个域模块按 §3.4 规则逐步解除 `_vw()`（常量/纯函数下沉 L0/L3、I/O 改端口注入），不是重写。archive.py / task_priority.py / change_triage.py / review_record.py / loop_*.py 等独立 CLI 模块（不被 import，facts §4.1）已天然接近目标形态，仅需接入 L0 契约与 L6 组合根。

### 3.4 `_vw()` 反向耦合消除方案（按类处理，不做 Services 大对象改名）

facts §4.1：`_vw()` 是 checks 子模块对 verify_workflow 共享全局的延迟 accessor（review_domain L52/L61/L113 本会话抽查复核）。消除按符号类别分流（顾问 Q1 采纳，逐类落点）：

| `_vw()` 访问的符号类别 | 归宿 | 迁移机制 |
|---|---|---|
| 常量/类型（数据表、正则编译对象） | L0 契约层或所属域 `data.py`/常量模块 | §5 归宿表分类搬迁（含 registry loader） |
| 纯计算函数（解析/判定，无 I/O） | 所属域领域函数（L3）或 L2 工具 | 下沉 + 单测随迁 |
| 文件/Git 读取 | L2 窄接口注入（L0 端口定义形状） | 构造参数/执行上下文注入，禁模块级全局 |
| 命令政策/渲染（print、exit 语义） | 从检查中**移除**——归 L4/L5 | 随渲染抽取切片（§10 REFACTOR-render-extract） |
| 隐式共享状态/缓存 | L6 组合根创建的命令范围显式上下文 | 每命令一次快照（§9.2），切片传递 |

**消除纪律**：新代码零 `_vw()`（R2 硬禁令）；存量 `_vw()` 调用点进基线清单，逐切片消除、CI 禁新增禁回升（§4）。不允许以"Services 大对象注入"整体改名替代（顾问 Q1 原文采纳——那是把隐式全局换成显式上帝对象）。

### 3.5 Check / 命令组织粒度决策（含对顾问"一项=一个注册项"的表态）

**表态：采纳顾问 Q1——"一项可独立调度的 Check = 一个注册项，不强制一项=一个文件"。**

理由（本仓事实为准）：EVD-632 实测 53 段（现 70 段，facts §3.3）中 32 段独特逻辑无法泛化——按"一项一文件"会制造 70 个小文件 + 70 套注册样板，复杂度守恒且违背 DEC-088 教训。粒度规则：

1. **先映射稳定 Check ID**：70 段编号（Check 1~40 + 子相位 18b~18i / 28b~28u / 30c + 汇总，facts §3.3 全清单）冻结为稳定 ID（含子相位 ID 化，如 `check-28p`），注册表记录 {ID → 领域、loader、输入依赖、执行等级、结果依赖}。
2. **再按领域组织文件**：`checks/<domain>/checks.py + rules.py + data.py`；短小共域检查共文件；单段 ≥ 数百行或需要独立测试边界（如 loop_runtime_claims 3,148 行、review_domain 3,087 行，facts §2.2）才独立模块。
3. **命令同理**：80 dispatch 键（77 函数 + 3 别名组，facts §3.1）冻结；新命令 = 注册项（键→handler 模块路径），不强制新文件。

### 3.6 核心契约定义（L0 首批形状——实现留待 REFACTOR-contract-layer）

以伪代码声明形状（字段与类型完整；实现为 Developer 任务）：

```python
# L0/contract.py —— 全部 stdlib，零 I/O
CheckID        = str            # 冻结清单：70 段稳定 ID（§3.5），别名如 "check-28p"
CommandKey     = str            # 冻结清单：80 dispatch 键（facts §3.1）

@dataclass(frozen=True)
class Finding:
    severity: str               # "BLOCKING" | "WARN" | "INFO"（沿用现语义，facts §3.5 样本 A）
    check: CheckID
    message: str
    file: str | None = None     # 相对仓库根路径
    line: int | None = None
    extra: dict = field(default_factory=dict)   # 检查特有细节（原样保留，兼容现输出）

@dataclass
class CheckResult:              # 内部强类型；经适配器以 dict 暴露（§3.7）
    check: CheckID
    passed: bool
    findings: list[Finding]
    skipped: str | None = None  # [SKIP] 披露沿用（FIX-270 机制，facts §9.6）
    details: dict = field(default_factory=dict)

# 端口（L2 实现之；L3/L4 只见接口）
class GovernanceStore(Protocol):      # 读：plan-tracker/evidence/decision/risk + 归档
    def read_records(self, scope: RecordScope) -> Iterable[LogicalRecord]: ...
class FilesystemPort(Protocol):       # 读树/读文件（UTF-8 强制，FIX-278 G4/F）
    ...
class GitPort(Protocol):              # status/show/tag/rev-parse
    ...
class ClockPort(Protocol):            # 可注入时钟（测试确定性）
    ...

@dataclass(frozen=True)
class CheckSpec:                # 注册项元信息（轻量，禁 import 时执行检查体）
    check_id: CheckID
    domain: str
    loader: str                # 模块路径字符串（受控白名单加载，§9.1）
    input_deps: tuple[str, ...]   # 声明输入依赖（quick-scan 选择闭包用，§9.3）
    severity_floor: str
    modes: tuple[str, ...]     # ("full", "quick", "domain:<name>")
```

**类型语法与版本基线过渡说明**：上伪代码 `str | None` 为 PEP 604 语法（3.10+ 运行时）。目标层新代码按 CI 版本 3.11+ 书写，并在待确认 Q1（§11.4）裁决落地时统一 pyproject 工具钉（py39→3.11）与契约类型语法口径；裁决前 L0 落地以 `from __future__ import annotations` 或 `typing.Optional` 过渡，保 3.9 解析兼容。

### 3.7 Result dict 兼容策略（关键兼容决策）

facts §9.6：现行接口形状 = Result dict（键 `pass`/`issues`/`details`），消费方（post-commit hook exit code、CI 4 步、`result["details"]["loop_runtime_claim_gate"]` 等内嵌读取）。策略：

1. **dict 表面长期保留为兼容契约**：键名 `pass`（含保留字拼写）/`issues`/`details` 不改、不改大小写、不加必填键。
2. **内部强类型渐进**：CheckResult（§3.6）经 `to_legacy_dict()` 适配器产出旧形状；类型与构造校验辅助（必填键/类型断言）先落地，供新代码使用。
3. **差分冻结**：契约矩阵（§8.2 类 3）冻结典型 Result dict 的序列化字节（含空值/缺省键差异——顾问 Q6 提示的类型/缺省值/空值差异逐项入黄金样例）。

### 3.8 关键决策可逆性标注（stage-architecture ADR 要求）

| 决策 | 可逆性 | 说明 |
|---|---|---|
| 六层单向架构 + 依赖矩阵（§3.2） | **可逆（结构重组类）**——层边界可再划分，只要 DAG 保持 | 70% 信息下推进（Amazon 可逆决策原则） |
| Check ID / 80 命令键冻结（§3.5/§8.2） | **半可逆**——ID 是对外契约，一经发布难回收；冻结前须 Phase 4 审查确认清单完整性 | 不可逆面 = 对外文档/脚本引用 |
| Result dict 兼容面（§3.7） | 不可逆（对外契约）——只能扩不能改 | 与上同 |
| 棘轮基线锚定 HEAD（§4.3） | 可逆——基线文件可重算，但只允许降不允许升 | 单向棘轮本身即机制 |
| 归档语义修复优先（§7.1） | 可逆（只读诊断先行） | 修复实施前不移动任何数据 |
| 投影生成器接管 15 投影（§6） | 半可逆——生成器错误可污染多平台，故配 CI 重生成零差异 + 人工黄金样例双护栏（BC-1） | |
| 派生 JSON 索引选型（§7.4） | 可逆——索引可删除可重建；升 SQLite 不受锁死 | 证据驱动后置 |

---

## 4. 缩容守门机制（棘轮规则集）

### 4.1 规则集（每条机器可判定）

设计原则（顾问 Q2 采纳）：**存量债务棘轮 + 增量零容忍 + 发布级趋势预算**联合守门。ArchGuard 用 stdlib `ast`/`tokenize` 实现即可（facts §9.4 stdlib-only 约束）；静态分析不识别所有动态导入 ⇒ **禁止未批准动态加载入口**（loader 白名单，§9.1）并测试装配路径。

| 规则 ID | 规则 | 机器判定方式 | 增量政策 | 存量政策 |
|---|---|---|---|---|
| **R1 主文件体积预算** | verify_workflow.py 精确 LOC（ReadAllLines 口径，facts §1.1）≤ 基线值（锚定 HEAD=24,252；本设计不把该数当目标，仅当棘轮起点） | CI 运行计数脚本 vs `core/architecture-baseline.json` 快照 | 每切片合并只降不升；任何上升 = FAIL（fatal，区别于 28 系 advisory——BC-2） | 基线建立即冻结；豁免见 §4.3 |
| **R2 反向依赖禁令** | 新代码（checks/release/新模块树）零 `import verify_workflow`、零 `_vw()` 定义/调用 | AST import 图 + 调用点扫描；输出违规 (path, line, rule) 三元组 | 零容忍（fatal） | 存量调用点入基线清单（路径+行号+责任任务）；逐切片消除，CI 断言"基线清单长度单调不增" |
| **R3 层间依赖矩阵** | §3.2 允许边集合之外的一切内部 import = 违规；全图 SCC=0 | AST import 图 + 允许矩阵 diff + `tarjan` SCC（stdlib 实现） | 零容忍 | 遗留巨石内部不适用（拆完该域才入管辖）；域模块自接入日起适用 |
| **R4 print 递减** | L3 领域模块禁 `print`（渲染归 L5）；巨石内 print 按来源（cmd_* / Check 段）计数 | `ast.walk` 统计 Call(print) 按所属函数归档 | 新业务模块零 print（fatal）；巨石按段基线递减（advisory→切片清零后转 fatal） | 1,315 处（facts §3.1）按 §3.3 域清单分段建基线 |
| **R5 注册完整性** | Check ID 唯一、CheckSpec 元信息完备、80 命令键全覆盖、loader 路径可解析（白名单内） | 注册表加载 + 断言（ID 唯一/必填字段/键集合 == 冻结清单/路径 importable） | 零容忍（fatal）——防"注册漂移"（RISK-046 同类根因） | 建立时与 facts §3.2/§3.3 清单对账 |
| **R6 启动成本预算** | 按命令 import 集合计数 + 冷启动墙钟（`python -X importtime`）进入命令级预算表 | CI 采样（交错新/旧，§9.5 协议）vs 预算表容差 | 超容差 = FAIL（性能门禁，§9.5） | 首批切片校准容差（不拍脑袋定阈值） |
| **R7 生成输出可重现** | 投影/夹具生成输出在 CI 临时目录重生成零差异；夹具复制显式分类标记 | 生成器 --check 模式 + diff | 零容忍（fatal） | §6 迁移期旧夹具按五分类标记 |

配套度量（advisory，沿用 Check 28 系机制先例，facts §5.2）：产品逻辑体积 vs 胶水体积分开追踪（脚本按文件归属层分类求和）——回应 NG-2"不承诺净减"但保持趋势可见。

### 4.2 与既有 ArchGuard 面（Check 28 族 / architecture-health.json）的关系

facts §5.2/§8.2：现有 28 系多为 advisory + 事后度量（RISK-039 批评"全是结构/事后/自觉型约束"）。本机制**不复用 advisory 位**而是在发布门新增 `archguard-ratchet` 独立命令（fatal_on_error=true），消费 `core/architecture-baseline.json`（新文件，机器生成禁手编）。28s（体积告警）保留为数据面护栏（§7）。

### 4.3 存量违规基线建立与豁免到期机制

- **基线建立**：REFACTOR-archguard-ratchet 任务首次运行全规则扫描 → 生成基线文件（每条违规 = 路径 + 行号 + 规则 ID + **责任任务占位名**）→ 提交入库。禁通配符豁免（每条点名）。
- **棘轮动作**：切片合并 → 重跑扫描 → 基线自动缩减（且仅缩减）；CI 断言基线 diff 方向。
- **豁免机制**：例外必须带 {理由 + 审批记录（DEC ID）+ 到期版本}；到期未续 = CI FAIL。豁免清单独立于基线文件，防混淆。
- **旧入口终态**：verify_workflow.py = 薄兼容壳（DEC-083 终态 <500 行方向保留但不承诺期限数字；以"豁免清零 + R1 基线收敛至壳层"为完成判据）。

---

## 5. 数据与逻辑配比

### 5.1 表驱动边界判定规则（顾问 Q3 采纳 + 本仓实例校准）

**判断标准（停止扩展通用引擎、回到 Python 插件的信号）**：配置开始需要 **条件分支、循环、执行顺序、副作用、自定义表达式** 之一时。

| 适合表驱动 | 本仓实例（facts §3.4 点名表） |
|---|---|
| 文件存在性 | REQUIRED_FILES（60 行）——且 EVD-630 已证与 manifest.json 300 条目重复（fallback 副本） |
| 固定字段/集合成员 | ADAPTER_REQUIRED_KEYS、GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS、REQUIRED_* tokens 族 |
| 简单 token 约束 | *_FORBIDDEN_OVERCLAIMS 族（纯字符串成员；**例外**：含 regex 编译对象者不可裸表驱动——DEC-088 详勘实证，需专用 loader） |
| 版本映射/投影占位符 | REQUIRED_SNIPPETS（325 行）+ PROJECTION_SNIPPETS（133 行）——本应外部化（DEC-088 Step A 原案，复杂度被低估处按新分类重估） |
| 语义同参数异 | 各平台 README tokens |

| 不适合（保持 Python 插件） | 依据 |
|---|---|
| 多阶段身份状态判断 | Check 31 身份子相位（facts §8.4 口径差本身即多阶段复杂度证据） |
| 跨文件证据链 | review 域（59 符号耦合面，facts §4.1） |
| 归档资格判定 | §7.1——归档识别失效证明其非平凡 |
| 历史兼容复杂例外 | e2e 31 DIFF 快照 |
| 已证难泛化的独特检查 | EVD-632：原型 Z 28 段 / AUDIT-124：32/53 独特 |

### 5.2 192 块数据表分类归宿表

facts §3.4 实测 192 块 / 2,048 行（含点名表 30+ 块全清单）。归宿按类判定（全量逐块清单由 REFACTOR-data-inventory 任务产出并入基线——本设计给出判定规则与点名表归类，不虚构未逐块核对的数字）：

| 归宿类 | 判定条件 | 点名表实例（facts §3.4） | 迁移形态 |
|---|---|---|---|
| A. JSON registry（多平台共享/可审计声明式） | ≥2 消费方或跨平台投影参与 | REQUIRED_FILES（与 manifest 重复，EVD-630）、REQUIRED_SNIPPETS、PROJECTION_SNIPPETS、WORKFLOW_SNIPPETS | 带 schema_version 的 JSON registry（沿 lifecycle-registry.json 2,441 行先例，facts §2.2），配套校验：类型/重复键/未知字段/引用一致性/版本兼容 |
| B. 域内 data.py（单检查独有 token/枚举/小映射） | 单一域消费 | LOOP_ROLE_* 两表、GOVERNANCE_PACK_* 族、README_PACK_GUIDANCE_*、HOST_CAPABILITY_* | checks/<domain>/data.py 常量模块 |
| C. Python 常量模块（regex/组合表达式） | 含编译对象或 Python 特有结构 | FIX_105_*/SECRET_* 正则族（~40 个 re.compile）、ADAPTER_RUNTIME_CAPABILITY_POLICY | Python 模块（禁 JSON 化——DEC-088 实证 loader 复杂度） |
| D. 项目级配置 | 用户项目政策 | （现无实例——预留类，NG-1 防线：无当前需要不建） | 不建（显式非目标，YAGNI） |
| E. 构建期生成（可从权威源推导） | 存在单一权威源 | 版本钉 6 处、标记面 8 行（§6 投影面） | 生成器产物禁人工维护 |

**纪律**（顾问 Q3 原文采纳）：移到 JSON ≠ 减维护 ≠ 提性能；每块迁移须附消费方清单；契约层（L0）只定义 registry 形状，**不建"所有常量中心"**。

### 5.3 对 AUDIT-124 "32/53 独特逻辑"结论的承接

- 32 段独特逻辑（原型 C 4 + Z 28，EVD-632）→ **保留 Python 插件形态**，按 §3.5 归入领域包；唯一动作是解除 `_vw()` 与渲染抽取（结构收益，非缩行收益）。
- 可压缩段（原型 A 12 + B 5 + D 4 = 21 段）→ **压缩的是编排/渲染面而非业务逻辑**：注册表 + 共享渲染器（§10 REFACTOR-orchestration-dedup）替代逐段 print 模板（facts §3.5 三样本同构证据）。
- 70 段 vs 53 段差（28u/30c/31~40 新增，facts §3.3）→ 新增段按新规则直接入注册表；其中已表驱动边界内者（如 28t ADAPTER_CLAIM_REGISTRY，FEAT-014）验证了 registry 先例。

---

## 6. 投影与夹具单源策略

### 6.1 15 投影逐项来源映射原则（facts §5.1 清单）

单一权威源链：**规范内容（core/manifest.json，source_of_truth=true）+ 版本源（SKILL.md frontmatter active_version，DEC-096 权威）+ 平台能力差异 + 平台模板 → 确定性生成器 → 投影文件 + 8 标记面行 + 6 版本钉**。

| 投影 kind | 条目 | 来源映射原则 |
|---|---|---|
| byte_copy ×1 | SKILL.md → e2e/SKILL.md | 权威源字节复制；CI 校验逐字节一致（FIX-270 门禁沿用） |
| structured_json ×7 | manifest/plugin/marketplace/package JSON 族 | 版本号 JSON-pointer 注入；schema 字段集冻结 |
| transformed_text ×7 | e2e plan-tracker、4 hooks、2 dsh 模板 | 模板 + 变量（版本/路径）；模板即源，目标禁手编 |

逐项 15 条来源映射表（source → generator 参数 → target → 校验锚）由 REFACTOR-projection-single-source 任务产出为生成器输入清单；本设计不重复罗列 15 行明细（facts §5.1 已有权威清单，避免第三份拷贝——单源原则自身适用）。

**生成器确定性要求**（顾问 Q4 采纳）：固定 UTF-8 + 换行风格（LF/CRLF 按平台模板钉死）+ 集合排序键；**禁时间戳/绝对路径/随机性入产物**；构建/维护阶段生成（不在 CLI 启动时生成）；生成结果可提交 Git；CI 在临时目录重生成要求**零差异**。平台特有内容保留受控模板差异，不折最低公分母。

**与既有实现关系**：release/projection.py（313 行，三类写入 + journal 回滚，facts §5.1）**扩展而非重建**——它已实现写入引擎；新增的是"来源声明模型 + 确定性生成入口 + CI --check 模式"。

### 6.2 e2e 91 文件五分类处置（顾问 Q4 采纳）

facts §5.3：91 同名文件 = 60 SAMELOC + 31 DIFF。分类处置：

| 类 | 判定 | 处置 | 预期量级（依据 facts §5.3/§5.4） |
|---|---|---|---|
| ① 无意重复副本 | SAMELOC 且来源可由构建产物装配（__init__.py、resolve_entry.py、SKILL.md、governance-init.md 等） | 测试时从构建产物装配，删除手工副本 | 60 SAMELOC 中的投影/by-design 对（含 28p 三对） |
| ② 故意损坏副本 | 为 mutation/负对照测试存在（如 GBK936 负对照，FIX-278） | 显式标记 + patch 脚本生成，禁同步 | 少量（现存于测试内嵌，非独立文件为主） |
| ③ 历史兼容样本 | 31 DIFF（快照落后，如 verify_workflow.py 14,166 vs 24,252） | **冻结禁自动同步**；标记快照时点（tag） | 31 文件 |
| ④ 领域检查夹具 | 某域检查的最小输入样本 | 只留必要；归 checks/<domain>/fixtures/ | 按域清点 |
| ⑤ 真实 e2e | 完整链路覆盖（agent-runtime-e2e 等命令消费，facts §3.2） | 保留少量完整链路 | ~少量目录 |

护栏：六平台独立契约断言；生成器测试不得只验"自产自洽"（BC-1）；保留人工审阅黄金样例；**避免符号链接瘦身**（Windows-first 兼容性，facts §9.3）。

### 6.3 CI 重生成验证

`check-projection-sync`（现有，facts §9.5）扩展为：CI 步骤 = 临时目录重生成 → diff 全投影 + 夹具类① → 零差异 PASS。纳入 R7 规则。

---

## 7. 治理数据生命周期

### 7.1 第一步：归档识别修复（优先于一切数据移动）

facts §6.3：归档器输出"触发器满足（release_forced）但无可归档数据"而热文件双 ERROR（§6.1）——**体积触发 ≠ 存在可归档记录**（FIX-158 已修过一次 early-return 死代码，此次是识别面失效）。修复要求（顾问 Q5 采纳）：

- 归档器 dry-run 输出**可审计解释**：扫描数 / 解析成败 / 逐条保留原因（不满足哪个业务条件）/ 满足条件数 / 未知结构数。
- 修复后仍不能归档 ⇒ **缩热视图而非强删**（数据安全 P7）。
- 只读诊断先行（REFACTOR-archive-recognition-fix 任务 P0），修复实施前**零数据移动**；实施配完整备份 + 操作后一致性校验（check-archive-integrity）。

### 7.2 第二步：记录模型统一

现状：plan-tracker/evidence/decision/risk 四热文件 + archive + change-triage JSON + incidents 各自格式（facts §6）。统一为**版本化逻辑记录模型**：稳定 ID / 状态 / 时间 / 关系（含已知容忍环 AUDIT-146↔FEAT-010，facts §4.1——在关系字段显式化而非隐式容忍）/ 源位置（文件+行）。**保留 Markdown 原文为权威**（NG 采纳顾问假设：Markdown 权威 + 派生）；迁移只加解析器兼容既有格式，不改写原文。

### 7.3 第三步：冷热分层

- **冷层**：不可变归档原文（archive/ 54 文件既有机制延续）。
- **热层**：未完成事项 + 近期事件（窗口可配）。
- **导航层**：清单 + ID→位置映射 + 摘要（即 §7.4 派生索引）。
- **append-only 边界显式化**：逻辑历史不可变；物理归档 = 受控事务移动（journal 先例）；若政策禁物理移动则保留原日志、另生成热视图（二选一在 REFACTOR-governance-hotview 设计时定，默认后者——更保守）。

### 7.4 派生索引选型（顾问 Q5 逐项表态）

| 选项 | 表态 | 理由 |
|---|---|---|
| 无索引修解析（第一阶段） | **采纳** | §7.1/§7.2 本身即是；索引建在坏解析上无意义 |
| 派生 JSON 索引（可检查/可重建） | **采纳（初期推荐）** | 含 schema + 源指纹；mtime 相同 ≠ 内容未变（顾问提醒采纳——用内容指纹）；可删除可重建 |
| JSONL 权威日志 | **拒绝** | 双写一致性问题（顾问同款理由）；Markdown 权威已定（§7.2），再引入第二权威源违反单源原则 |
| SQLite | **拒绝（现在）/ 证据驱动后置** | 当前总量 1.76MB（口径：双 ERROR 热文件之和 = plan-tracker 344.1KB + evidence-log 1,419.5KB；四热文件合计 ~2.0MB，facts §6.1）不需数据库；stdlib-only 下 sqlite3 可用但引入查询面维护成本；P2 profiling 显示解析成本显著时重议（REFACTOR-perf-evidence-driven） |

### 7.5 LLM agent 上下文预算视图

- agent 面新增按主题/ID/状态查询 + **预算上下文视图**（给定 token 预算 → 裁剪视图）；裁剪必须标注"省略了什么、去哪取原文"（顾问 Q5 采纳；AUDIT-147 D6 乱码教训同域——UTF-8 强制沿 FIX-278）。
- 配套**恢复流程验证**：热视图/索引损坏 → 删除重建 → 与原文对账（数据恢复演练入横切门，§3.2）。
- Check 28s 阈值保留为护栏（RISK-039 独立守护，facts §6.2 note）；热视图解决根因而非调阈值。

---

## 8. 零回归迁移路径

### 8.0 测试基线修正（前置中的前置）

facts §7.1/§7.2 + 缺口 1：2,201 `def test_` vs 采信 788 ran（单文件）/ 全量多时点漂移（1,768→1,976→788），1 fail 既有定性。**在基线可信前，任何结构切片不得启动**（切片验收门依赖全量绿）。

修正动作（REFACTOR-test-baseline-audit + REFACTOR-test-env-characterization，均 P0）：

1. **收集关系调查（不猜测——顾问 P0-③ 采纳）**：固化收集清单（unittest discover 范围 vs 全函数计数）、runner、命令、**预期收集数**。显式假设（待该任务验证）：CI `python -m unittest discover -s infra/tests`（facts §9.1）不覆盖 e2e/ 与根 tests/；788 为单文件运行数字。假设错误则以实测为准，设计不依赖具体数值。
2. **失败定性分类学**：环境失败（bash/WSL ×24、loop-runtime 抖动——FIX-278 基线）/ 已知缺陷（F-1、Check 31）/ 真实回归 三分；各挂标记与豁免。
3. **单文件绿 ≠ 全仓过**（FEAT-016 R0 采信先例教训，facts §7.2）写入任务验收模板。
4. **全量超时调查**：查原因不放大大 timeout 掩盖退化（顾问 Q6 采纳）。
5. **提交分离**：重构切片 / 缺陷修复 / 规则变化分开提交验收（D4 修改纯粹性）。

**既有缺陷先行显式修复**（顾问 Q6 采纳："先写正确预期测试，再单独显式修复，不混入等价搬迁"）：cmd_check_release F-1（HEAD L20568 本会话复核仍在）、Check 31 口径差、hook 接线缺口——均 P0 独立任务（§10），在契约矩阵冻结**之前**完成或显式标记为"经批准纠正项"入基线。

### 8.1 契约矩阵（等价证明义务 + 差分测试设计）

| 契约类 | 冻结内容 | 等价证明义务 | 差分测试设计 |
|---|---|---|---|
| 1. 80 CLI 键 | 键集（77 函数 + 3 别名组，facts §3.1）、参数、help、退出码、stdout/stderr、文件副作用 | 新旧实现在冻结输入上逐键等价 | 特征测试（characterization）：冻结输入仓库快照 → 交错运行旧/新 → 比较 exit code + stdout/stderr 字节 + 文件树 diff。**仓内消费方事实**（facts §9.1）：post-commit hook `2>/dev/null` 只消费 exit code；CI 4 步消费 exit code；CLAUDE/AGENTS.md 引用命令不解析 stdout 格式 ⇒ 仓内机器契约 = exit code + 文件副作用；stdout 格式按"人类可读 + 会话采信面板（--summary-only）"冻结为软契约；仓外脚本解析面无法穷举（顾问 P0-②）→ 待确认项 Q2（§11.4） |
| 2. 70 Check | Check ID、触发条件、结果顺序、severity、issue 计数细节 | 每段在冻结仓库快照上产出等价 findings（顺序与数量） | 逐 Check 黄金输出文件（fixture 快照 + 预期 Result dict 序列化）；子相位 ID 化后逐一映射 |
| 3. Result dict | 键集/类型/缺省值/空值差异/序列化（§3.7） | to_legacy_dict 适配器输出与旧构造逐键等价 | schema 快照 + 边界用例（空 issues/None details/SKIP 披露）黄金样例 |
| 4. 运行环境 | Windows 路径/编码（FIX-278 UTF-8 纪律）/PowerShell/hooks/CI（ubuntu+Py3.11） | 双环境（Windows 本机 + CI ubuntu）等价 | 差分 harness 双平台运行；编码负对照沿用 test_utf8_read_guard 先例 |
| 5. 治理数据 | 旧格式解析/归档前后完整性 | 新解析器对既有全量语料（1.76MB 热文件 + archive 54 文件）产出相同逻辑记录集 | 语料快照 → 旧/新解析 → 逻辑记录集 diff = 空 |
| 6. 性能 | §9.5 协议 | 同环境成对比较无实质退化 | 交错采样 + 容差判定 |

### 8.2 绞杀者切片序列（P0/P1/P2）+ 验收门 + 回滚

通用切片流程（顾问 Q6 采纳）：旧入口保留 → 新契约 + 兼容 Result 边界 → 选定域垂直切片 → 冻结输入上新旧差分 → 路由切换 → 删旧实现与对应豁免 → 按域重复。**写操作不在同一工作树双跑**（隔离副本比较文件树差异）。

| 阶段 | 切片内容 | 验收门（全过才算切片完成） | 回滚策略 |
|---|---|---|---|
| **P0 可信基线** | 测试基线修正（§8.0）+ 契约矩阵冻结（§8.1）+ 依赖债务快照（R1~R7 基线文件）+ 归档只读诊断 + 数据备份 | 全量测试绿（含定性分类）；契约快照入库；棘轮基线生成且 CI 生效 | 纯只读 + 快照文件，git revert 即回 |
| **P0 独立纠错** | F-1 / Check 31 / hook 接线（既有缺陷显式修复，与 0.79.0 收尾可并行——§10 标注） | 每项：正确预期测试先行（红→绿）+ 单独 commit + 全量无新失败 | 独立 commit revert |
| **P1 结构试点** | 最小契约层（L0）+ 轻注册 + 按需导入；**一简单一复杂两个垂直切片**（复杂切片选依赖共享状态者，暴露 `_vw()` 消除全链路）；随切片抽渲染（不改版式） | 目标域测试 + 全量 + 契约差分（类 1/2/3）过；架构债务降（R2 基线缩减、无新增违规）；性能无实质退化（R6）；无未批准行为差异；**回滚演练过** | 路由开关回旧路径（切片保留双实现至验收后删除）；旧路径设删除期限（防永久双实现） |
| **P1 高收益去重/生命周期** | 投影单源生成 + 夹具五分类 + 归档识别修复实施 + 编排同构段去重（原型 A/B/D 21 段）+ 记录模型/热视图 | CI 重生成零差异（R7）；28p by-design 对清零；归档 dry-run 输出可审计解释且移动有完整性校验；渲染差分逐字节（不改版式） | 生成器产物 git revert + journal 回滚（projection.py 先例）；归档移动配备份恢复演练 |
| **P2 规模化迁移** | 按域迁移剩余检查与命令（review → projection/archive/identity → 其余）+ 减旧编排（_run_full_engine_checks 拆域）+ quick-scan 依赖选择落地 + 删兼容债务与到期豁免 | 每域同 P1 验收门；R1 主文件基线显著收敛；豁免清单趋零 | 同 P1；数据格式迁移的代码回退 ≠ 数据可回退——单独设计（§11.1 RSK-6） |
| **P2 证据驱动优化** | profiling 决定持久缓存 / SQLite 索引重议 / 更细模块边界 | 有 profiling 数据支撑才立项（NG 防） | — |

---

## 9. 性能策略

### 9.1 静态轻注册 + 按命令加载（顾问 Q7 采纳）

- 注册表只含轻量元数据（命令键→handler 模块路径字符串；CheckID→loader/领域/输入依赖/执行等级/结果依赖——§3.6 CheckSpec）。
- 启动链：轻入口识别命令 → import 所选 handler → 选择所需 Check → 加载插件与数据 → 创建命令范围缓存 → 输出退出。
- **禁止**：目录扫描/pkgutil 全量发现、入口 import 全部命令、import 时读文件/Git、import 时实例化全部服务（L6 禁令 §3.2）。
- **不引入第三方动态插件机制**：受控 loader 白名单（R5 校验路径可解析性 + 装配路径测试——静态分析盲区补偿，§4.1）。

### 9.2 单次执行共享快照

命令范围执行上下文（L6 创建）持有：文件树快照、Git 状态、治理语料解析缓存。同命令内多 Check 复用（消除 70 段各自重复解析——facts §3.5 编排现状的隐性成本）；跨进程不共享（初期）。快照不可变（测试确定性 + quick-scan 缓存键基础）。

### 9.3 quick-scan 子集选择——位置在应用编排层（L4）

**表态：采纳顾问 Q7——quick-scan 不是简化检查逻辑，而是同一批检查的选择策略。** 承接 0.79.0 立项评估（DEC-177 ②，RISK-044 缓解分支）结论作为输入；目标架构落位：

- 选择机制 = 变更事实 + CheckSpec.input_deps 声明 + 模式政策 → 受影响检查闭包 → **原有实现**（不改检查体）。
- 支持 full/quick/域选择；增量考虑：文件增删改名、共享 registry 变化、全局不变量、未提交文件、未知输入（未知回退 full）。
- quick 输出区分：通过 / 未执行 / 缓存复用 / 无法判断（禁把"没查"报成"通过"）。
- hooks 可消费经验证 quick；CI/发布 full 兜底；**先 shadow 比较再改 hook 政策**。
- 初期只做子集选择；跨进程缓存后置（缓存键 = 引擎/规则版本 + 配置 + 输入指纹）。

### 9.4 不虚承诺数量级提速

facts §7.3：解释器启动主导场景（status 含启动 0.49~4.04s 跨时点漂移）；顾问 Q7 采纳——接受单进程下限，不虚承诺；提速收益主要来自按需导入（缩短 import 集合）与共享快照（消除重复解析），量级由 R6 预算表量化。

### 9.5 性能测量协议（R6/契约类 6 的判定基础）

1. stdlib 分段测量：`python -X importtime`（import 集合）+ 命令级墙钟。
2. 同机、同 Python、同工作树，**交错**运行新旧（A/B/A/B ≥5 轮）。
3. 冷/暖启动分开报告（冷 = 新进程首跑；暖 = 同进程重复或系统缓存后）。
4. 指标 = **median + P95 + 环境信息**（Python 版本/OS/负载标注——RISK-048 教训：并行治理 agent 负载会污染单次样本）。
5. 容差预先约定（REFACTOR-perf-protocol 首批切片校准：建议初值 median 相对差 ≤10%、P95 ≤25%，作为假设标注待校准）；超容差 = 切片验收 FAIL。
6. 不凭单次 0.5s/4s 下结论（facts §7.3 两值并列教训）。

### 9.6 非功能需求覆盖矩阵（tech-review 第三步映射）

| 非功能需求 | 设计措施 | 承载章节 |
|---|---|---|
| 性能 | 按命令加载（§9.1）+ 共享快照（§9.2）+ quick-scan 选择（§9.3）+ 测量协议与容差门禁（§9.5/R6） | §9 |
| 安全（数据安全 P7） | 数据移动零强删（§7.1 缩视图不删）+ 备份 + 一致性校验 + 恢复演练（§7.5）+ 写操作禁同工作树双跑（§8.2）+ journal 回滚先例（§6.1）+ UTF-8 纪律（FIX-278 沿用） | §6/§7/§8 |
| 可用性（agent/用户面） | 80 键 CLI 兼容（§8.1 类 1）+ exit code 语义冻结 + 预算上下文视图（§7.5）+ quick 输出四态披露（§9.3）+ [SKIP] 披露沿用 | §7/§8/§9 |
| 可维护性 | 六层单向依赖 + R1~R7 棘轮 + 豁免到期机制（§4）+ 单源资产（§6）+ 记录模型统一（§7.2）+ 注册完整性（R5） | §3/§4/§6/§7 |
| 可扩展性 | CheckSpec 注册项扩展（新检查零触碰巨石）+ 域包自治（§3.5）+ 端口注入（§3.4）+ 平台模板受控差异（§6.1） | §3 |
| 可测试性 | 契约差分 harness（§8.1）+ 黄金样例 + 端口 mock（ClockPort 等）+ 命令范围快照不可变（§9.2）+ 快照/装饰夹具分层（§6.2） | §6/§8 |
| 兼容性（Windows-first） | 差分双平台（§8.1 类 4）+ 编码纪律 + 禁符号链接（§6.2）+ stdlib-only（NG-3） | §8/§9 |

---

## 10. 可执行任务清单（核心交付）

**消费说明**：ID 为语义化占位名（`REFACTOR-*`）；正式 ID 由 Coordinator 侧 change-triage 机器分配。规模：S ≤ 0.5 天 / M ≤ 2 天 / L ≥ 3 天（含测试与证据）。版本槽"0.79.0∥"= 可与 0.79.0 收尾并行（只读或独立小修，不触碰 0.79.0 范围内核增需 DEC）。

### P0 — 可信基线与独立纠错（切片前置门槛）

| 占位 ID | 任务标题 | 范围 | 依赖 | 验收标准（可运行命令/门禁） | 切片 | 版本槽 | 规模 |
|---|---|---|---|---|---|---|---|
| REFACTOR-test-baseline-audit | 测试收集关系调查与全量基线建立 | 固化收集清单/runner/命令/预期收集数；输出 2,201 vs 788 关系结论；建立当日全量运行基线（只读+运行测试，不改产品代码） | — | 交付基线报告（收集数/失败分类学/超时原因）；`python -m unittest discover -s infra/tests` 全量绿或定性清单入库 | P0 | 0.79.0∥（只读）→ 0.80.0 首槽 | M |
| REFACTOR-test-env-characterization | 环境敏感失败定性标记 | 按 RISK-048 因果证伪链方法对 bash/WSL ×24、loop-runtime 抖动、median<8s 超阈逐族定性；失败分类标记机制（环境/已知缺陷/真实回归） | REFACTOR-test-baseline-audit | 分类标记覆盖全部既有失败；新增回归不被环境标记掩盖（抽查 diff） | P0 | 0.79.0∥（分析产物 + 测试代码小修——不改产品代码） | S |
| REFACTOR-fix-release-f1 | cmd_check_release 恒 exit 1 显式修复 | verify_workflow.py L20568 无条件 pass=False 改为依据 claim_gate issues 判定；修 F-2（测试断言归因强度） | — | 正确预期测试先行（红→绿：healthy 输入 exit 0 / claim issues 输入 exit 1 两态都可达）；全量无新失败；单独 commit | P0 | 0.79.0∥（若核增获批）否则 0.80.0 | S |
| REFACTOR-check31-caliber | Check 31 身份子相位口径差定位修复 | 定位独立运行 PASS vs 引擎内 identity_verdict=FAIL 分歧根因并修复（facts §8.4 登记候选） | — | 两口径同一输入产出一致 verdict；差分用例入库；根因写入任务记录 | P0 | 0.79.0∥ / 0.80.0 | M |
| REFACTOR-hook-wiring | hook 接线缺口交付 | FEAT-011 遗留：write-guard 触发链 hook 接线（FIX-297 L37 承接的后续候选） | REFACTOR-fix-release-f1（同文件域避让） | 接线后 post-commit 面板显示 write-guard 结果；回滚方案（FIX-297 方案 2 规则保留为回退） | P0 | 0.80.0（0.79.0 已收窄出槽） | M |
| REFACTOR-perf-protocol | 性能测量协议脚本与容差校准 | 交错采样脚本（-X importtime + 命令墙钟 median/P95）；首批切片校准容差（§9.5 初值假设验证） | REFACTOR-test-baseline-audit | 协议脚本入库；对 status/check-governance 产出双基线报告；容差表入库供 R6 消费 | P0 | 0.79.0∥（测量产物——不改产品代码，新增协议脚本/容差表文件） | M |
| REFACTOR-archguard-ratchet | 棘轮规则 R1~R7 落地与基线快照 | 新增 archguard-ratchet 命令（fatal）+ core/architecture-baseline.json 生成器 + 豁免登记机制 + CI 接线 | REFACTOR-test-baseline-audit（对账用清单） | 基线文件生成（R1=24,252 锚定、R2 `_vw()` 清单、R4 print 分段计数）；CI 违规上升即 FAIL 的负对照测试；棘轮命令/基线生成器自身代码落独立模块（不落 verify_workflow.py），基线生成先于自身代码合并或自举豁免显式登记 + 到期版本 | P0→P1 | 0.80.0 | L |
| REFACTOR-data-inventory | 192 数据块全量归宿清单 | 逐块归属 §5.2 五类；产出 registry 迁移清单（含消费方清单） | — | 清单覆盖 192/192 块（对账 facts §3.1 计数）；每块带消费方与归宿类；DEC-088 loader 复杂度例外标注 | P0 | 0.79.0∥（分析产物——不改产品代码，新增归宿清单文档） | M |
| REFACTOR-archive-recognition-fix | 归档识别修复（只读诊断→实施） | 归档器输出可审计解释（扫描数/解析成败/保留原因/未知结构）；诊断后修复识别面；实施配备份+完整性校验 | REFACTOR-test-baseline-audit | dry-run 解释输出可审计；修复后能归档者真实归档且 check-archive-integrity PASS；不能归档者输出业务原因（不强删） | P0→P1 | 0.80.0 | M |
| REFACTOR-contract-matrix-freeze | 契约矩阵冻结与特征测试 | 80 CLI 键/70 Check ID/Result dict 三类快照 + 特征测试 + 差分 harness 骨架（双平台） | REFACTOR-fix-release-f1, REFACTOR-check31-caliber, REFACTOR-hook-wiring（§8.0 三件套前置显式编码） | 快照文件入库；差分 harness 对当前实现自校验 PASS（旧 vs 旧 = 零差异）；黄金样例人工审阅记录；差分 harness 双端（Windows 本机 + CI ubuntu）Python major.minor 版本钉一致（黄金样例生成与比对同解释器族）；冻结时点断言：0.79.0 已 released 或残余波次清单显式入基线记录 | P0 | 0.80.0 | L |

**P0 统计：10 项（S×2 / M×6 / L×2）；其中 6 项可 0.79.0∥ 并行（test-baseline-audit / test-env-characterization / fix-release-f1 / check31-caliber / perf-protocol / data-inventory）。**

### P1 — 结构试点与高收益去重

| 占位 ID | 任务标题 | 范围 | 依赖 | 验收标准 | 切片 | 版本槽 | 规模 |
|---|---|---|---|---|---|---|---|
| REFACTOR-contract-layer | 最小契约层 L0 落地 | §3.6 契约形状实现（CheckID/Finding/CheckResult/端口 Protocol/CheckSpec）+ to_legacy_dict 适配器 + 构造校验 | REFACTOR-contract-matrix-freeze | 契约层零 I/O 零内部依赖（R3 判定）；Result dict 差分零差异（§8.1 类 3） | P1 | 0.80.0 | M |
| REFACTOR-light-registry | 轻量注册与按命令加载 | 命令键→handler 路径 + CheckID→CheckSpec 注册表 + 受控 loader 白名单 + L6 组合根雏形 | REFACTOR-contract-layer | R5 注册完整性 PASS；启动 import 集合不增（-X importtime 对照）；装配路径测试 | P1 | 0.80.0 | M |
| REFACTOR-slice-pilot-simple | 简单域垂直切片 | 选低耦合域（候选 ci_domain 492 行 1 符号 / snapshot_domain 439 行 1 符号，facts §4.1）完整走绞杀者流程（含移除对应 `_vw()` 与渲染抽取不改版式） | REFACTOR-light-registry, REFACTOR-archguard-ratchet | §8.2 P1 验收门全过（含回滚演练）；R2 基线缩减；差分类 1/2/3 零差异 | P1 | 0.80.0 | M |
| REFACTOR-slice-pilot-complex | 复杂域垂直切片（共享状态） | 选高耦合域（review_domain 59 符号面分批先迁 1 子域）暴露 `_vw()` 消除全链路 | REFACTOR-slice-pilot-simple | 同上；59 符号耦合面基线下降且不回升；性能 R6 容差内 | P1 | 0.80.0~0.81.0 | L |
| REFACTOR-orchestration-dedup | 编排同构段去重（原型 A/B/D 21 段） | 70 段中可压缩 21 段（AUDIT-124 清单）改注册表+共享渲染；渲染器入 L5 | REFACTOR-slice-pilot-simple | 渲染差分逐字节（不改版式）；R4 print 分段基线下降；32 独特段零触碰 | P1 | 0.81.0 | M |
| REFACTOR-projection-single-source | 投影单源生成器 | 15 投影来源声明模型 + 确定性生成 + CI --check 零差异（扩展 release/projection.py） | REFACTOR-data-inventory | CI 临时目录重生成 15/15 零差异（R7）；标记面 8 行 + 6 版本钉由生成器接管 | P1 | 0.81.0 | L |
| REFACTOR-e2e-fixture-classification | e2e 夹具五分类瘦身 | 91 文件按 §6.2 分类：类①装配化 / 类③冻结标记 / 类④归域 / 类⑤保留 | REFACTOR-projection-single-source | 分类标记全覆盖 91/91；28p by-design 对清零；e2e 命令全绿；类③ 31 份清单附消解计划（随对应域迁移切片替换为差分 harness 或删除，绑定 P2 migrate-* 任务） | P1 | 0.81.0 | M |
| REFACTOR-governance-record-model | 治理记录模型统一 | 逻辑记录模型（稳定 ID/状态/时间/关系/源位置）+ 兼容解析器 + 关系字段显式化（容忍环入册） | REFACTOR-archive-recognition-fix | 全量语料逻辑记录集新旧 diff=空（§8.1 类 5）；解析器对 1.76MB 热文件+archive 54 文件 PASS | P1 | 0.81.0 | M |
| REFACTOR-governance-hotview | 治理热视图与派生索引 | 冷热分层 + 派生 JSON 索引（schema+源指纹）+ 恢复演练 + 预算视图 v1 | REFACTOR-governance-record-model | 索引可删除重建且对账一致；28s ERROR 面（双热文件）降为 WARN 以下或输出业务原因；恢复演练记录 | P1→P2 | 0.81.0 | M |
| REFACTOR-quickscan-orchestration | quick-scan 编排层落地 | L4 选择策略（input_deps 闭包）+ shadow 比较 + hooks 政策评估 | 0.79.0 quick-scan 前移评估结论（DEC-177 ②）；REFACTOR-light-registry | shadow 全量对照报告（quick 命中集 vs full 差异=预期未执行集）；quick 四态输出（§9.3） | P1→P2 | 0.81.0~0.82.0 | L |

**P1 统计：10 项（M×7 / L×3）。**

### P2 — 规模化迁移与证据驱动优化

| 占位 ID | 任务标题 | 范围 | 依赖 | 验收标准 | 切片 | 版本槽 | 规模 |
|---|---|---|---|---|---|---|---|
| REFACTOR-migrate-review-domain | review 域全量迁移 | review_domain 59 符号面剩余部分 + 相关 cmd_* 入域包 | REFACTOR-slice-pilot-complex | 域差分零差异；R2 该域 `_vw()` 清零 | P2 | 0.82.0 | L |
| REFACTOR-migrate-domains-batch1 | projection/archive/identity 域迁移批 | 按域清单（facts §4.1 剩余列）逐域绞杀 | REFACTOR-slice-pilot-complex | 同域验收门；豁免清单随域缩减 | P2 | 0.82.0~0.83.0 | L |
| REFACTOR-migrate-remaining | 剩余检查与命令迁移 | 70 Check/80 键剩余项 + loop 族接入组合根 | REFACTOR-migrate-domains-batch1 | 注册表覆盖 70/70 + 80/80（R5）；巨石仅剩兼容壳 | P2 | 0.83.0+ | L |
| REFACTOR-legacy-orchestration-shrink | 旧编排收缩 | `_run_full_engine_checks` ~1,695 行按域拆解至 L4；70 段编排迁注册驱动 | REFACTOR-orchestration-dedup + 域迁移 | R1 主文件基线显著收敛（不预设数字）；编排差分零差异 | P2 | 0.82.0~0.83.0 | L |
| REFACTOR-agent-context-view | agent 上下文预算视图完善 | 主题/ID/状态查询 + 预算裁剪（标注省略与原文出处） | REFACTOR-governance-hotview | 预算视图在真实会话场景验证（AUDIT-147 D6 乱码负对照回归） | P2 | 0.83.0+ | M |
| REFACTOR-main-thin-entry | 旧入口终态薄壳 | verify_workflow.py 收敛为兼容 facade + 组合根装配；豁免清零 | 全部域迁移 | R1 基线收敛至壳层量级；80 键差分零差异；R2 豁免清单空 | P2 | 0.83.0+ | M |
| REFACTOR-perf-evidence-driven | 证据驱动性能优化 | profiling 决定：跨进程缓存 / SQLite 重议 / 更细边界 | REFACTOR-quickscan-orchestration | 有 profiling 报告才立项（NG 防）；每优化走 R6 门禁 | P2 | 0.83.0+ | M |

**P2 统计：7 项（M×3 / L×4）。**

### 清单覆盖对账（任务书必覆盖项 → 占位 ID）

测试基线修正→test-baseline-audit+env-characterization ｜ 契约矩阵冻结→contract-matrix-freeze ｜ ArchGuard 棘轮门→archguard-ratchet ｜ 最小契约层→contract-layer ｜ 垂直切片×2→slice-pilot-simple+complex ｜ 渲染抽取→render 部分并入两切片 + orchestration-dedup ｜ 投影单源生成→projection-single-source ｜ e2e 夹具分类瘦身→e2e-fixture-classification ｜ 归档识别修复→archive-recognition-fix ｜ 治理热视图/索引→governance-hotview(+record-model) ｜ cmd_check_release F-1→fix-release-f1 ｜ Check 31 口径差→check31-caliber ｜ hook 接线缺口→hook-wiring ｜ quick-scan 编排→quickscan-orchestration ｜ 按域迁移批→migrate-review-domain+domains-batch1+remaining ｜ 性能测量协议落地→perf-protocol ｜ **27/27 全覆盖，0 遗漏**。

---

## 11. 风险与回滚

### 11.1 一般风险（≥5 条含回滚）

| 风险 ID | 风险 | 概率×影响 | 缓解 | 回滚 |
|---|---|---|---|---|
| RSK-1 | 测试基线调查发现大规模潜伏失败（>50 真实回归级），切片门槛长期无法满足 | 中×高 | 失败分类学先行（环境/已知缺陷/真实回归三分）；分层基线（按域绿即可启动该域切片）；真实回归独立任务化不受重构线阻塞 | 基线报告版本化，回退到上一采信时点继续分类 |
| RSK-2 | 棘轮门误报阻断正常开发（如 R3 矩阵对测试代码误适用） | 中×中 | 规则作用域显式白名单（测试目录豁免沿 architecture-health.json 先例，facts §2.2）；负对照测试先行；豁免审批通道 | archguard-ratchet 命令降 advisory 一版（DEC 记录），修复后回升 fatal |
| RSK-3 | 生成器接管 15 投影后模板错误同时污染多平台发布面 | 低×高 | CI 重生成零差异（R7）+ 人工黄金样例 + journal 回滚（projection.py 先例）+ byte_copy 逐字节门禁（FIX-270）沿用 | git revert 生成器 commit + release journal 恢复 |
| RSK-4 | 归档修复实施时误移/漏移治理记录（数据安全 P7） | 低×高 | 只读诊断先行；移动前全备份 + check-archive-integrity + 恢复演练；默认热视图替代物理移动（§7.3 保守选项） | 备份恢复 + 归档事务 journal 回退 |
| RSK-5 | 重构线与 0.79.0 并行致版本槽/治理写冲突（agent-locks/plan-tracker 双写） | 中×中 | ∥ 项限定只读或独立小修；file_locks 由 Coordinator spawn 前置（AUDIT-150 模式延续）；版本槽分离（0.79.0 已定范围不核增） | ∥ 项出槽顺延 0.80.0，零代码冲突残留 |
| RSK-6 | 数据格式迁移的代码回退 ≠ 数据可回退（记录模型/热视图上线后） | 低×高 | 迁移设计包含反向兼容期（旧解析器保留 N 版）；逻辑记录集 diff 门禁（§8.1 类 5） | 代码 revert + 数据留在新格式由兼容解析器读（不物理回退数据） |

### 11.2 蓝军挑战（≥3 条，独立 ID + 缓解）

| ID | 挑战（"如果…会怎样"） | 回应/缓解 |
|---|---|---|
| **BC-1** | **如果切片差分测试与旧实现共享同一份被污染的解析/渲染基础设施，"新旧等价"是否循环自证？**（等价证明的地基问题） | 三重独立锚：① 契约快照在**任何新代码落地前**冻结（REFACTOR-contract-matrix-freeze 前置于 contract-layer，依赖已声明）；② 黄金样例人工审阅留痕（不信任自产自洽——顾问 Q4 同款）；③ 差分 harness 先做"旧 vs 旧"自校验（零差异才可信）再用于新旧对照。三者缺一该切片验收 FAIL |
| **BC-2** | **如果棘轮门重蹈"28 check 全事后/自觉型约束"覆辙（RISK-039 原文批评），只报不阻断怎么办？** | R1/R2/R5/R7 设 fatal_on_error=true 直接进发布门（§4.2 明确与 28 系 advisory 分位）；豁免必须带 DEC 审批 + 到期版本；基线文件机器生成禁手编；CI 有"违规上升即 FAIL"负对照测试。若 Reviewer 认为 fatal 面过宽，收窄面须逐规则 DEC 记录 |
| **BC-3** | **如果 70 段 Check ID 冻结清单本身有错（漏段/子相位编号不稳定/汇总段语义含混），冻结即固化错误契约怎么办？** | 冻结清单以 facts §3.3 行号实测清单为底稿（70 段全清单含行号）+ REFACTOR-contract-matrix-freeze 任务逐段与代码对账（print 头存在性机器验证）后才入快照；对账差异回写 facts 缺口清单而不是强拼；子相位 ID 化规则（`check-18b` 格式）经 Phase 4 Design Reviewer 审查确认 |
| **BC-4** | **如果重构线周期拉长（27 项跨 0.80.0~0.83.0+），中途优先级被新需求挤压，留下"半迁移"状态比现状更糟怎么办？** | 每切片自包含验收 + 回滚演练（切片完成即生产可用，不依赖后续切片）；旧路径删除期限机制防永久双实现（§8.2）；棘轮保证任何暂停点都是"已改善且锁住"的状态（R1 只降不升）——最坏情况=暂停在某切片边界，结构收益已锁定且无回吐 |

### 11.3 顾问识别 P0 待澄清事项——本仓可得答案 / 待确认

| 顾问 P0 项 | 本仓答案（facts 依据） | 状态 |
|---|---|---|
| ① Python 最低版本/分发方式/免构建 | CI = ubuntu-latest + Python 3.11（facts §9.1）；分发 = 源码仓 + 插件市场直装（6 平台 adapters，facts §9.2），无打包构建步骤；bootstrap.cmd/resolve_entry.py 直接 python 运行（免构建成立）。**最低版本声明现状**：无 `[project].requires-python`；但根 pyproject.toml 工具面钉 py39（`[tool.ruff] target-version="py39"` / `[tool.mypy] python_version="3.9"`），且主文件保持 3.9 语法姿态（无 future-import / PEP 604 注解） | 部分可答；**待确认 Q1**：是否冻结 "3.11+ 为支持基线"（建议值，须用户/审查裁决） |
| ② 哪些 stdout 被脚本解析/Markdown 锚点被外部引用 | 仓内消费方不解析 stdout 内容（post-commit `2>/dev/null` 只取 exit code；CI 取 exit code；入口 md 引用命令不解析格式——facts §9.1）⇒ 冻结为：exit code + 文件副作用 = 机器契约；stdout = 人类可读软契约（例外：--summary-only 面板被会话采信，作软契约冻结）。仓外（用户宿主项目脚本）不可穷举 | 部分可答；**待确认 Q2**：外部脚本/锚点引用面由用户自行确认无（或列出） |
| ③ 2,201 函数 vs 788 ran 收集关系 | 不能猜测（顾问同款立场）→ 任务化：REFACTOR-test-baseline-audit P0；显式假设已登记（§8.0.1） | 待任务验证（设计不依赖具体数值） |
| ④ hooks/CLI/agent 并发写治理文件/旧格式兼容 | 写方可枚举：change-triage / review-record / execution-packet --write / governance-write-guard / session-snapshot + agent-locks.json 锁机制既存（facts §6.1/§9.6）；RISK-046 邻域（派发锁漂移）打开。**设计假设**：热视图/索引生成必须可重入 + 原子写（journal 先例）+ 内容指纹（mtime 不可靠） | 已按保守假设设计（§7.4）；并发场景实测归 REFACTOR-governance-hotview 验收 |
| ⑤ 无统一硬件性能 SLA | 采纳：0.5~4s 仅作观测范围；门禁 = 同机交错相对容差（§9.5）；绝对值门禁仅保留已修订验收线（summary-only <60s，DEC-177 ②） | 已解决（协议层面） |

### 11.4 待确认事项（需用户/Coordinator 裁决的开放问题）

| # | 问题 | 建议默认值 | 影响面 |
|---|---|---|---|
| Q1 | Python 支持基线冻结为 3.11+？（顾问 P0-① 残余） | 是（与 CI 一致） | 契约类 4（运行环境）冻结范围 |
| Q2 | 仓外是否存在解析 stdout/引用 Markdown 锚点的脚本？（顾问 P0-② 残余） | 默认无（按软契约冻结） | 契约类 1 stdout 等级 |
| Q3 | 归档物理移动 vs 原日志保留+热视图（§7.3 二选一） | 后者（保守） | REFACTOR-governance-hotview 设计 |
| Q4 | P0 ∥ 项是否申请 0.79.0 范围核增（6 项，§10） | fix-release-f1/check31-caliper 建议核增（小修高值），其余留 0.80.0 | 0.79.0 收尾范围 |

---

## 12. 替代方案与否决理由（≥2；实际 4 个）

| 方案 | 内容概要 | 否决理由（事实引用） |
|---|---|---|
| **ALT-A 大爆炸重写** | 新建 verify_workflow_v2.py 按目标架构全量重实现，一次性切换 | ① 零回归义务不可证明：测试基线当前不可信（facts §7.1/§7.2：2,201 vs 788 采信漂移、1 fail 定性未闭环）——B1 前置失效；② 消费方面无契约护栏（facts §9.1：post-commit 唯一调用点 + CI 4 步 + 6 平台 + 80 键面）一次性切换爆炸半径最大；③ EVD-632 实证 ~16,000 行业务逻辑是合理复杂度——重写复制不了治理规则的演化历史（DEC-083~145 三轮治理结论沉淀在现有实现里），只会引入新缺陷面；④ DEC-099 先例已确立"新逻辑不碰 God Module"渐进路线的政治可行性 |
| **ALT-B 第三次纯文件拆分（DEC-088 路线原样重启）** | 继续"每版拆 1~2 域"的位置搬运算术（0.59/0.60 模式延续） | ① DEC-088 实证 re-export 搬运不降主文件行数、净收益 ~260 行（EVD-632）；② facts §4.3 锯齿曲线：两次拆分窗口（-616/-1,631）均被 +1,410/+2,766/+1,303 回吐——**无棘轮的拆分必然回吐**（P-2 根因未解）；③ DEC-103 明令禁止 re-export 伪装拆分；④ `_vw()` 反向耦合（facts §4.1）证明位置拆分不产生依赖解耦（G2 不可达） |
| **ALT-C 全面 DSL/表驱动** | 把 70 段 Check 全部改为数据表 + 通用解释器引擎 | ① EVD-632："原型 Z（custom）28 段是独特逻辑无法泛化"；AUDIT-124 32/53 独立复核（facts §8.10）；② DEC-088 Step A 详勘已证 token 外部化复杂度被低估（FORBIDDEN_OVERCLAIMS 含 regex 编译对象需专用 loader）；③ 顾问 Q3 判断标准：配置需要条件分支/循环/副作用时必须回 Python——70 段中至少 32 段立即越界；④ 制造解释器 = 制造第二个上帝模块 + 第二套测试面，违背 NG-8 |
| **ALT-D 冻结现状只修缺陷（不重构）** | 只做 P0 独立纠错（F-1/Check 31/hook），结构维持现状 | ① RISK-039 打开的原文即批评"全部在零告警下发生"——不建棘轮则第三轮膨胀必然复现（facts §4.3 曲线外推依据）；② 用户指令明确要求"架构演进规划 + 分层解耦 + 归一聚合"（G1/G2）——只修缺陷不满足授权范围；③ 治理数据生命周期断裂（P-5）与投影多副本（P-4）无缺陷修复路径可达；④ 但 ALT-D 的 P0 子集被**吸收**进本方案（§10 P0 独立纠错批） |

---

## 13. proposed DEC 条目（DEC-183 候选——Coordinator 写回 decision-log）

> **DEC-183** | 2026-09-09 | 0.80.0 重构线基线——采纳架构演进规划（分层绞杀 + 棘轮守门 + 单源资产 + 数据生命周期）
>
> **背景**：用户 2026-09-09 授权指令（架构腐化系统性梳理与重构规划；零功能/性能回退、零问题回归）。AUDIT-150 Phase 1 事实基线（architecture-audit-facts-0.80.0.md：巨石 24,252 行/504 def/74 cmd/80 键/70 Check 段；`_vw()` 反向耦合 19 模块；tag 曲线锯齿 v0.70→HEAD +4,069；测试 2,201 vs 788 采信缺口；15 投影 + e2e 91 文件 60/31 重复；治理热文件 1.76MB + 归档识别失效；RISK-039 打开）+ Phase 2 架构顾问咨询（分层契约/棘轮/插件为主/单源生成/Markdown 权威+派生索引/绞杀者切片/P0-P2 阶段门——已逐项表态：采纳为主、修正处标注、拒绝 JSONL 权威日志与 SQLite 即行，见演进文档附录 A）。
>
> **决策**：(1) 采纳 `docs/requirements/architecture-evolution-0.80.0.md` 为 0.80.0 重构线基线：六层单向架构（契约/基础设施/领域检查/编排/渲染 CLI/组合根，DAG 声明）+ 绞杀者切片（P0 可信基线与纠错 → P1 结构试点与高收益去重 → P2 规模化迁移）+ 棘轮守门 R1~R7（fatal 位，与 28 系 advisory 分位）+ 契约矩阵冻结（80 键/70 Check/Result dict/环境/治理数据/性能六类差分）+ 投影与夹具单源 + 治理数据生命周期（归档识别修复优先 → 记录模型 → 冷热分层 + 派生 JSON 索引）。(2) 重构执行任务以 §10 清单（27 项占位 ID）为 triage 输入，逐项机器入账（change-triage 分配正式 ID），遵守 DEC-145"新任务新版本号"。(3) 测试基线修正与既有缺陷显式修复（F-1/Check 31/hook 接线）为切片前置门槛；在此之前不启动结构切片。三件套前置义务经任务依赖图显式编码：REFACTOR-contract-matrix-freeze 依赖 {fix-release-f1, check31-caliber, hook-wiring}（§10），与 §8.0 声明一致。(4) 不承诺全仓净减行数（DEC-088 教训）；主文件行数仅作棘轮观测值（R1 只降不升）。
>
> **备选**：ALT-A 大爆炸重写 / ALT-B 第三次纯文件拆分 / ALT-C 全面 DSL 表驱动 / ALT-D 只修缺陷不重构——**均否决**（理由见演进文档 §12，逐条引用 facts 编号与 DEC-083/088/103/145 治理链）。
>
> **影响**：产品代码零变更（本 DEC 仅确立基线）；0.80.0+ 版本槽规划按 §10 版本列；RISK-039 获得结构性关闭路径（棘轮门 = "外部宿主验证 ArchGuard 面"关闭条件的仓内前置）；RISK-044/048 承接（quick-scan 落位编排层 + 性能协议容差）；与 0.79.0 收尾并行的 6 项 P0 ∥ 清单待范围裁决（Q4）。
>
> **证据**：facts 文档（AUDIT-150 Phase 1）+ 顾问咨询全文（Phase 2）+ 本演进文档（Phase 3）+ Phase 4 Design Reviewer 审查记录（待）。
>
> **决策者**：用户（2026-09-09 授权指令）+ Coordinator（落盘）/ Architect（设计）。
>
> **关联**：AUDIT-150, DEC-083/088/090/091/096/099/103/145/177, RISK-039/044/046/048, EVD-630/632/969。
>
> **后续**：Phase 4 Design Reviewer 审查本演进文档 → 通过后 §10 清单逐项 change-triage 机器入账 → 0.80.0 版本规划（REL 线）启动；待确认 Q1~Q4（演进文档 §11.4）随审查/用户裁决闭合。

---

## 附录 A：顾问建议逐项表态总表

| ID | 顾问条目（Q#/摘要） | 表态 | 理由/分歧点（本仓事实为准） |
|---|---|---|---|
| P1 | 决策摘要：目标不为缩行数字 | **采纳** | 与 DEC-088 教训一致（facts §8.10） |
| P2 | 决策摘要：~16,000 行真实检查逻辑保留归属 | **采纳** | EVD-632 同款结论 |
| P3 | 决策摘要：零回退须先建可复现基线 + 区分"保持行为"与"经批准纠正缺陷" | **采纳** | §8.0 前置门槛；F-1/Check 31 先修 |
| P4 | 假设：stdlib/单进程/Windows-first/无后台服务 | **采纳** | facts §9.3/§9.4 实证同款 |
| P5 | 假设：80 CLI 键为待冻结契约 | **采纳** | facts §3.1 dispatch 实测 80 键 |
| P6 | 假设：Markdown 暂保治理数据权威 | **采纳** | §7.2；派生索引可重建 |
| P7 | Q1 六层架构表 | **采纳（修正层名与既有模块映射）** | 与 checks/*_domain.py 既有骨架衔接（§3.3）——顾问未涉及既有 19 模块处置，本设计补全 |
| P8 | Q1 消除 `_vw()` 按类处理、不做 Services 大对象 | **采纳** | §3.4 逐类表 |
| P9 | Q1 检查粒度"一项=一个注册项非一个文件" | **采纳** | §3.5；EVD-632 32/53 独特逻辑实证 |
| P10 | Q2 棘轮联合指标 + ArchGuard stdlib 实现 + 禁未批准动态加载 | **采纳** | §4 R1~R7；静态分析盲区以白名单+装配测试补偿 |
| P11 | Q2 遗留违规精确基线/豁免到期/双体积追踪 | **采纳** | §4.3；不承诺净减（NG-2） |
| P12 | Q3 插件为主有限表驱动 + 五信号停止标准 | **采纳** | §5.1；DEC-088 loader 复杂度例外显式保留 |
| P13 | Q3 192 块五归宿 + "移 JSON≠减维护" | **采纳（修正：D 类项目级配置不建——YAGNI）** | §5.2 表 D 行；无当前实例 |
| P14 | Q4 投影单源 + 确定性生成 + CI 零差异 | **采纳** | §6.1；扩展 release/projection.py 非重建（本设计补充衔接） |
| P15 | Q4 夹具五分类 + 黄金样例 + 禁符号链接 | **采纳** | §6.2；Windows-first 补充（facts §9.3） |
| P16 | Q5 归档先修语义→记录模型→冷热分层 | **采纳** | §7 顺序完全一致 |
| P17 | Q5 索引选型：派生 JSON 索引（初期推荐） | **采纳** | §7.4 表 |
| P18 | Q5 索引选型：JSONL 权威日志 | **拒绝** | §7.4 表（双写一致性 + Markdown 单源原则） |
| P19 | Q5 索引选型：SQLite 即行 | **拒绝（后置）** | §7.4 表（证据驱动重议保留） |
| P20 | Q5 agent 预算视图 + 裁剪标注 | **采纳** | §7.5；FIX-278 编码纪律叠加 |
| P21 | Q6 不先全面重写 rendering；先基线→最小契约→垂直切片 | **采纳** | §8 顺序一致；1,315 print 中混流程控制的风险评估接受 |
| P22 | Q6 绞杀者切片流程 + 每切片验收门 + 删除期限 + 数据迁移单独设计 | **采纳** | §8.2 表；RSK-6 |
| P23 | Q7 轻注册/按命令加载/共享快照/quick-scan 属编排层选择策略 | **采纳** | §9.1~9.3；承接 0.79.0 评估结论（DEC-177 ②）——本设计补充该衔接 |
| P24 | Q7 性能协议 median+P95+容差+交错 | **采纳** | §9.5；RISK-048 教训叠加环境标注 |
| P25 | 总览三原则（保留真实复杂度/单权威源可重建/单向迁移机器棘轮） | **采纳** | 分别承载于 §5/§6-7/§4-8 |
| P26 | 总览 P0~P2 切片顺序：hook 接线升 P0 独立纠错 | **采纳（微调）** | §10；0.79.0 收窄事实（facts §8.7） |
| P27 | 总览 P0~P2 切片顺序：quick-scan 挂 0.79.0 评估依赖 | **采纳（微调）** | §10；0.79.0 收窄事实（facts §8.7） |
| P28 | 顾问 P0 待澄清 5 项 | **逐条回应** | §11.3（2 项部分可答、1 项任务化、2 项已按保守假设设计）——不计入采/修/拒三类统计 |

**表态统计（position 级，ID 可机检）：采纳 21 条（P1~P6、P8~P12、P14~P17、P20~P25）/ 修正 4 条（P7 Q1 层映射衔接、P13 Q3-D 类不建、P26/P27 总览微调）/ 拒绝 2 条（P18 JSONL 权威日志、P19 SQLite 即行——SQLite 为"拒绝现在"保留证据驱动重议）；P28 为逐条回应类，不计入三类。原"采纳 26 条"系混合行未拆 position 前的口径，经逐 position 化复算修正为 21（R0-S2）。无与本仓事实冲突处：顾问全部量化引用与 facts 一致；唯一事实性修正 = hook 接线状态（顾问咨询时点为"缺口"，FIX-297 已承接规则面但接线未交付——本设计按 facts §8.7 最新态处置）。**

## 附录 B：本轮自检声明（Architect）

- 唯一写入产物 = 本文档；未修改产品代码与 .governance/（DEC-183 为 proposed 文本）。
- 全部设计结论可追溯：facts §N / 顾问 QN / DEC-EVD-RISK ID（正文逐处标注）。
- 硬门槛：候选方案 4（≥2）✓；ADR 字段 100%（§0 映射表）✓；蓝军 4 条独立 ID+缓解（≥3）✓；DAG 声明 + R3 机器判定（无循环依赖）✓；任务清单 27 项含范围/依赖/验收/切片/版本槽/规模 ✓；NFR 逐项措施（§9.6）✓；数据缺口 7 项处理（§2.3）✓。
- 本会话只读抽查 2 项核验 facts（`_vw()` 模式 L52/L61/L113；F-1 缺陷 L20568）——均与 facts 一致。
- 独立评审（Bar Raiser）由 Phase 4 Design Reviewer 承担——本文 Status 保持 Proposed。
