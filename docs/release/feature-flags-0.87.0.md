# Feature Flags — 0.87.0（REL-084 M-1R / REL-085）

> **起草说明**：本版 feature-flags 面随 M-1R 四件套一次成形（对照 feature-flags-0.86.0 先例——0.86.0 起四件套为 M-1R 标准面）。本版三项行为变更（B-9/B-10/B-11）均**无 flag 级降级通道**，本文档即该事实的登记面 + 各自回退通道声明（版本级回退唯一路径）+ 既有灰度开关边界重申。起草于 2026-09-21（REL-085），随候选提交入索引。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.87.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.87.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.87.0 为治理健康收口版；do not claim 1.0.0 production-ready。

## 1. 本版 flag 面总览

| 项 | 值 |
|---|---|
| 本版行为变更 | **B-9**（Check 31 语义预算容量重定标，FIX-369）/ **B-10**（locks-release 释放语义，FIX-370）/ **B-11**（Check 16/17 历史豁免账本，FIX-371）——CHANGELOG 0.87.0 段行为变更节原文口径；另有 FIX-366 连带 CRLF 保真行为变化（非独立变更号，§5） |
| flag 级通道 | **无**——三项变更均「版本级回滚」为**唯一回退路径**；发布形态即最终形态，不存在灰度放量开关、运行时 kill switch 或 opt-out 数据面 |
| 非破坏性说明 | B-9 为基线机制设计内数值重定标非判定语义变更（VERSIONING L11 显式处置——Breaking changes = 无）；B-10 纯新增 CLI、shrink-locks 保留无删除面；B-11 活跃判定语义零弱化（历史行豁免 + 新增行零豁免全严检）——CHANGELOG semver 论证段同口径 |
| 既有灰度开关 | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy`（0.84.0 FEAT-040 交付，本版零改动）——见 §6 边界 |

## 2. B-9 Check 31 语义预算容量重定标（FIX-369）

- **变更**：`ScanLimits.max_semantic_units` **300,000 → 361,923 = ceil(301,602 × 1.2)**——measured_peak = 301,602 semantic_units（2026-09-20 +08:00 当日最高同门禁实测：300,701 晨 / 300,913 ~17:4x / 301,602 ~18:0x；working tree at commit `6e25753`；payload 15,385,341B < 32MiB payload 预算）；1.2 = 增长裕度因子（version-plan-0.87.0 §3.1 candidate A）。provenance 注释在 `checks/loop_runtime_claims.py` L225-242；基线经 FEAT-047 baseline-register 机制登记（gate check-31-semantic-units）。
- **用户视角**：获得 = `check-loop-runtime-claims` 在当前活数据体量（301,602+）下恢复可用（0.86.0 期 SEMANTIC_BUDGET_EXCEEDED fail-closed BLOCKED 解除）；感知 = 门禁从 BLOCKED 转有据 PASS；体验 = 正向（引擎 fail-closed 语义不变——超限即拒绝，绝不假装扫描通过）。
- **重定标非豁免（红线）**：门禁语义不弱化（BLOCKED→有据 PASS 仅因容量重推导）；公式钉值 + 反豁免 fail-closed 双测试（`FIX369SemanticBudgetRecalibrationTests`）钉死**再重定标必须走同公式**（ceil(实测峰值×1.2)）并经 baseline-register 登记——静默上调被守护测试翻红。
- **回退通道**：**版本级回退唯一路径**（CHANGELOG B-9 原文）——还原预算值（361,923→300,000 单行回退）+ 基线注销；数据级、可执行、双向自洽。⚠️ 回滚后 LRC **必然 BLOCKED 回归**（活数据已实测越线——0.86.0 已知态），如实预期；程序见 rollback-plan-0.87.0 §2.1 步骤 5 / §4 #11。

## 3. B-10 locks-release 释放语义（FIX-370）

- **变更**：governance_store 新增 `locks-release` 子命令——锁清理 governed 化：task 锚定**真删除**（active_tasks + file_locks + ops 台账登记）+ **先登记后删除**（ops 台账先行，删除动作携带 operation_id 审计痕迹）+ released_files 审计章 + 三态/幂等 fail-closed；CLI 分发面 95→**96 键**重定基线（FEAT-355 同型；archguard R5 消费面）。**shrink-locks 保留且语义不变**（TTL 收缩为最近 Governed 效果——0.86.0 披露② 的缺口由本命令补足非替换）。
- **用户视角**：获得 = 过期锁悬挂（Check 26 活体——REL-082 过期锁 4 blocking 实证）首次拥有可对账的释放路径；感知 = 释放动作在 ops 台账留 operation_id 痕迹 + released_files 审计章；体验 = 正向（已建立机录路径零事故基线延续——写入器时代自举）。
- **边界**：误删补偿 = acquire 幂等重取（锁条目可重建，不触任务数据）；**不可逆面 = 零**（真删除仅及锁条目自身，已释放事实由台账留痕）。
- **回退通道**：**版本级回退唯一路径**（代码回退承载）——locks-release 命令面移除、CLI 分发面回落 95 键（回滚后 MUST archguard regen 对齐冻结面）；已释放的锁不随回滚恢复（需要时 acquire 幂等重取）；shrink-locks 旧语义保持可用。程序与验证表见 rollback-plan-0.87.0 §2/§4。

## 4. B-11 Check 16/17 历史豁免账本（FIX-371；DEC-227/228）

- **变更**：Check 16/17 历史行豁免账本（DEC-227 路线 b）——✅ 终态历史行（2026-09-20 前存量）豁免入账本，**新增行零豁免全严检**；豁免在三消费方留痕不静默（Check 16 / Check 17 / Check 18 事实依据取数 wrapper——DEC-228①）；主运行面打印 historical_exempted 计数 + 有界清单（交付时点对账 26=8+18）。
- **用户视角**：获得 = Check 16/17 门禁信号从 31 FAIL 噪声态收敛到真实活跃义务态（交付时点真实面 31→5，勘正回填后 5→3）；感知 = 主运行面豁免计数与逐行清单可审计（三面留痕）；体验 = 正向——**REQ-092 blocked 保持 FAIL 未被豁免**（Desktop marketplace 外部依赖 + result matrix 在场——零豁免红线活体实证，0.79.0 先例姿态延续）。
- **红线（DEC-227）**：账本仅容纳 2026-09-20 前存量历史行；路线 a（数据补录）被否——补录 = 编造风险违反 P1；路线 c（披露基线）被否——M-2 门禁仍红；机录行不合格子字段登记时逐条披露。
- **回退通道**：**版本级回退唯一路径（机制级）**——账本机制为 verify_workflow.py 代码内实现（+144 行；非独立数据文件），回退 = 代码回退承载（Check 16/17 回到全严检、FAIL 计数回升至 0.86.0 已知形态——如实预期非回滚失败）。条目级增删（DEC-226 非-T2 裁定「账本可增删可回滚」）仅适用于机制在场时的数据级操作，不构成 flag 级降级通道。程序见 rollback-plan-0.87.0 §2/§4。

## 5. CRLF 保真行为变化（FIX-366 连带——非独立变更号）

- **变更**：projection transformed target 保留原生换行——`read_bytes().decode` 替代 `read_text` 隐式转换（CHANGELOG 披露④）；CRLF 护栏双断言测试在场。
- **用户视角**：获得 = 投影字节保真（Windows 原生 CRLF 文件经投影不再被静默归一化）；感知 = 投影 diff 面字节级变化（一次性）；体验 = 正向且无行为破坏面。
- **回退通道**：随 FIX-366 版本级回滚恢复旧隐式转换行为（护栏测试一并消失——防回归网同步失去，如实披露）；操作面后果见 rollback-plan-0.87.0 §7（两遍 plan 撤回 = 绕开手法复活专节）。

## 6. 既有灰度开关边界（非本版新增——边界重申）

`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级 env，优先级高）> plan-tracker `behavior_profile: legacy`（项目级）> 默认 `modern`（非法值不猜——`governance-bootstrap` behavior.invalid 显式报告）：只回退**性能/编排行为**（快路径→六段读取 / 首次交互前置→深检先行 / ≤8 字段默认视图→完整快照契约 / Scenario 按需→预加载，共 4 项）；**安全语义不回退**（六不变量——升级确认门 / 异常不隐藏 / fail-closed〔`resolved_root_ok == false` 即停〕/ 真实环境防护〔三选一〕/ 复审必达 / 升级确认门前零写操作）——边界表权威源 = `skills/software-project-governance/SKILL.md`「行为灰度开关」节。本版未改动该通道与 LEGACY_REVERTS 约束（仅 performance 类可入回退表；任何把安全语义塞入回退表的改动会被守护测试翻红——`behavior_profile.revert_contract_issues()` 机检）。

**B-9/B-10/B-11 与灰度开关的正交性**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载**三项变更的回退——B-9 容量重定标属门禁基线（fail-closed 安全语义面：legacy 模式下预算值不变、SEMANTIC_BUDGET_EXCEEDED 照样拒绝）、B-10 释放语义与 B-11 豁免账本属治理行为而非性能/编排行为，均不在 LEGACY_REVERTS 白名单；不存在「legacy 模式下关闭 locks-release/豁免账本或还原预算值」的中间态。

## 7. 未发布面 N/A

- **write-guard WARN→BLOCK 升级**：留 0.88（DEC-224 双约束随升级落地；DEC-226 出槽清单登记）——本版无 write-guard 姿态变更；
- **flag 清理计划**：不适用（本版无 flag 出货，无 flag 债务）；0.87.0 行为变更编号序列止于 B-11；
- **kill switch 验证**：不适用（B-9 引擎 fail-closed 语义即安全兜底无需 kill switch；B-10 误删补偿 = acquire 幂等重取为内建恢复路径非独立开关；B-11 无运行时关闭数据面——其「触发—生效」路径即版本级回滚，程序与验证表见 rollback-plan-0.87.0 §2/§4）。

## 8. 硬门槛自检（本文件）

| 门槛项 | 判定 |
|---|---|
| 版本串在场 | PASS（0.87.0 多处） |
| 保守边界 5 token 在场 | PASS——五项 boundary token 齐备于「保守边界声明」节，逐项均携带 No…claim 行首 + 未被主张 的否定形态 |
| 禁用正向主张（overclaim） | PASS——全文按「未被主张/无/不适用」记录性措辞，无可索引的 loop-runtime 活体声明 |
| 与 CHANGELOG/rollback-plan 口径一致 | PASS——B-9/B-10/B-11 回退口径逐字对齐 CHANGELOG 0.87.0 段行为变更节与 rollback-plan §1/§4/§7；B-9 公式与 provenance 对齐 `loop_runtime_claims.py` L225-243 实读 |
| 表行管道符转义（FIX-365 ragged 教训） | PASS——表 cell 内零裸管道符，全行单层管道分隔 |

---
*REL-085 M-1R 起草冻结（2026-09-21，REL-085，Governance Developer Agent 起草）。事实基线：B-9/B-10/B-11 回退口径取自 CHANGELOG 0.87.0 段（`80d71b5` 冻结版）行为变更节原文；B-9 公式、measured_peak 与 provenance 取自 `checks/loop_runtime_claims.py` L225-243 实读（公式钉值/反豁免双测试 = `FIX369SemanticBudgetRecalibrationTests` 实读）；B-10 口径取自 FIX-370 交付记录（EVD-1127 / 活体验证 op-7c866828）；B-11 口径取自 DEC-227/228 与 EVD-1128（真实面 31→5→3、REQ-092 零豁免红线）；灰度开关边界取自 SKILL.md「行为灰度开关」节实读；CRLF 口径取自 CHANGELOG 披露④。*
