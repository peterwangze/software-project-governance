# Feature Flags — 0.84.0（REL-080）

> **M-0/M-1 草案（REL-080 prep，2026-09-19）**——Release Agent 起草、Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/feature-flags-0.83.0.md` 先例结构。M-3 Release Reviewer 审查与 M-2 门禁实测前，本文件不构成发布声明。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.84.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.84.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版引擎/判定面改动全部在仓库内测试与隔离 `DSH_HOME`（环境变量重定向至临时目录）下验收，隔离验收不等于真实外部首会话验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；0.84.0 为内部治理效率版；do not claim 1.0.0 production-ready。
- **性能收益口径边界**：AUDIT-154 的冷启动/注入数值为**实测基线**，本版主张的是「机制落地 + 可机检」（首次交互前置 / 聚合命令 / 按需加载 / 薄指针 / 预算门禁），**不主张**冷启动已达成 p50≤25s——FEAT-034 数值验收尾巴已结构化转 RISK-055（DEC-207①），TTFA 复验框架 `--ttfa-acceptance` 本版提供，采样结论待 REL-080 后续切片。
- **ArchGuard advisory 边界**：Check 28n/28o/28p 维持 `fatal_on_error=false` 既有边界——本版不声称 ArchGuard advisory fatal 化；28o 残余为产品源真实 advisory（God-module 族，RISK-039），如实披露。

## 1. 新增/变更的开关

| # | 开关 | 类型 | 默认 | 说明 |
|---|---|---|---|---|
| **F-1** | `GOVERNANCE_LEGACY_BEHAVIOR` | **env，会话级** | 未设置 = `modern`（新协议） | `=1`（或任意非空真值）→ 回退**性能/编排**行为 4 项（见 §2 B-6），安全语义不回退。优先于 F-2（env > plan-tracker > 默认） |
| **F-2** | `behavior_profile`（plan-tracker `## 项目配置` 行） | **项目级配置项** | 缺省 = `modern` | `legacy` → 同 F-1 回退面（项目级生效）；取值非法 → **不猜**：按下一优先级执行并在 `governance-bootstrap` 的 `behavior.invalid` 显式报告（FEAT-040 R0 P1-2 修复点） |
| **F-3** | `--profile` / `--format` 等既有开关 | 既有 | 不变 | 0.83.0 既有开关全部保留，语义未变（见 §5） |
| **F-4** | `check-injection-budget` 预算档位 | **检查器判定姿态（非运行时开关）** | lightweight = 硬门禁；standard/strict = **ADVISORY** | 出货姿态 = DEC-210（advisory，选项 a）；回弹风险 = RISK-057；翻 hard 时点 = 模板瘦身后（DEC-210 ④） |

**生效形态可见性（FEAT-040）**：`governance-bootstrap` 的 `behavior` 面**必然**携带 `profile` / `source`（`env` / `plan-tracker` / `default`）/ `reverted`（4 项）/ `invariants`（安全不变量）/ `invalid`（非法取值上报）——开关状态不是"文档承诺"，而是单命令可读的机器事实。

### 1.1 安全不变量（不可被开关回退 —— 硬边界）

| # | 不变量 | 机检形态（FEAT-040 三层机检） |
|---|---|---|
| I-1 | **升级确认门（FEAT-035）** | FEAT-035 所属变更**不得**出现在 `LEGACY_REVERTS`（回退表只允许 `performance` 类）；测试锁定 |
| I-2 | **异常不隐藏** | 回退不改变异常/失败可见性（非干扰契约双臂逐面相等） |
| I-3 | **fail-closed** | `resolved_root_ok == false` → MUST STOP，legacy 模式照常生效 |
| I-4 | **真实环境防护** | 涉及用户真实环境的操作三选一防护（隔离/备份/逐项授权）不回退 |
| I-5 | **复审必达** | NEEDS_CHANGE 复审义务不回退（round<3 强制复审） |

### 1.2 非开关项（如实登记）

- `governance-bootstrap`（FEAT-033）/ `governance-cost-report`（FEAT-032）/ `check-injection-budget`（FEAT-039）为**加性 CLI 能力**——随版本默认启用，无 opt-in 开关；
- FEAT-036 快照默认视图（8 字段）为**协议默认行为**（非开关）——完整契约仍在 artifact 面（24 token），risk/FAIL/证据缺口不隐藏；
- FEAT-037 薄指针 / FEAT-038 按需加载为**投影与文档结构形态**（非开关）——由 `check-projection-sync` / `check-entry-bootstrap-sync` 机检权威化。

## 2. 行为变更（用户可感知 —— MUST 写入 CHANGELOG 与升级说明）

| # | 变更 | 旧行为（0.83.0） | 新行为（0.84.0） | 理由 | 影响面 |
|---|---|---|---|---|---|
| **B-1** | 首次交互前置（FEAT-034，`469fb57`） | 会话启动按 Step 1→2→3→4 顺序推进，深检（交叉验证）在首次交互**之前**；冷启动到首次 ask 实测 4m31.8s~7m08s | 快路径热数据（`governance-bootstrap`）就绪后**立即**进入首次交互（ask），深检**后置**；健康面未完成时状态行显示「待检查」而非绿色通过 | 阻塞事务实测：深检前置把用户挡在门外 4~7 分钟；热数据已足够支撑首次 ask | 会话启动协议（决策树 / SKILL / 模板 / M5.5 四处一致）；**深检后置 ≠ 可选**——推进类动作（发布/版本 bump/治理写回/遗留任务修改）前 MUST 补齐；fail-closed 不变 |
| **B-2** | 迁移写操作退出启动关键路径（FEAT-035，`df9e7db`） | 升级/归档/清理等迁移写操作随会话**自动执行**（静默写用户入口文件） | 全部改为**提示 + 确认后执行**：ask 清单五类（含 cleanup **删除面**）+ 步骤位置锁定 + `update.md` 确认门；用户未响应前**零写操作**，migration 标志持续提示不重复打断 | 展示状态不应拥有修改项目的隐含授权（AUDIT-154 arch 结论）；"零用户行动"以静默写为代价不可接受（DEC-209） | 升级/归档/清理路径；`/plugin update → 下次会话` 用户操作不变；拒绝/无响应时**不**降级为静默执行 |
| **B-3** | Snapshot 双契约（FEAT-036，`38ff7d7`） | 状态输出单口径（完整快照 18.4K tok 级输出进会话） | **默认交互视图 ≤8 字段**（推演 ≈260 tok ≤700）；完整 artifact 契约口径拆正并保留（20 字段 CLI snapshot 三载体 + 4 pack doc-surface = 24 token 零删减） | 输出体积本身即治理开销（AUDIT-154）；但信任面不能因瘦身而缺失 | 默认视图；**权限风险 / FAIL / 证据缺失项不隐藏**；完整契约不扩展进 `governance-bootstrap`（DEC-208：≤8KB 硬预算） |
| **B-4** | 次要入口薄指针（FEAT-037，`457a756`） | `AGENTS.md` 与 `CLAUDE.md` 各持一份完整 bootstrap 模板（双份 21.8KB×2 注入） | `commands/governance-init.md` Step 7 为**唯一** canonical 源；主入口投影完整模板、次要入口投影生成的薄指针（≤40 行 / ≤3072B；段 16,011B→2,699B，-83%） | 双入口去重是可机检的静态注入削减；生成幂等（双 apply 零 diff） | 双入口工作区；单入口工作区**不受影响**（仍为完整模板，向后兼容）；行为约束以主入口 `CLAUDE.md` 为准 |
| **B-5** | Scenario 按需加载（FEAT-038，`697689d`） | `/governance` 命令全文单文档 49,889B 全量进上下文 | 路由层 + 九个按需文件（入口 11,702B，-76.5%）——Scenario D/F 会话不再加载 A/B/C 全文 | 命令文档注入是固定会话成本；按需读取不牺牲可达性（零语义丢失逐行对照 A24~F120） | 命令注入面；`commands/governance/*.md` 新增，旧入口保留路由角色（无命令删除） |
| **B-6** | 行为灰度开关（FEAT-040，`b537976`；DEC-212） | 交互语义变更无回退通道 | `GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级）/ `behavior_profile: legacy`（项目级）一键回退 **4 项性能/编排行为**：① 快路径 → 六段热文件读取；② 首次交互前置 → 深检先行；③ 8 字段默认视图 → 完整视图；④ Scenario 按需 → 预加载。**安全语义不变量不回退**（§1.1 I-1~I-5） | 交互语义变更属高风险面，需要安全网（FEAT-040 立项理由）；但"撤销知情同意门"等于把安全语义变成可选（违 DEC-209）⇒ 回退面按机检白名单硬限制 | 协议编排面；回退范围由 `LEGACY_REVERTS` 白名单 + 三层机检锁定；legacy 模式下 fail-closed / 确认门 / 复审义务照常 |

> **升级提示（面向用户）**：B-1/B-5 是**会话成本与协议时序**变更、B-3/B-4 是**输出与入口形态**变更、B-2 是**写操作授权边界收紧**（防护增强）、B-6 是**新增回退通道**（默认关闭）。六项对既有治理数据零破坏，历史治理记录零改写。无 breaking change；无删除既有 CLI 命令/开关；无新文件格式。

## 3. 新增的检查面与命令（加性，默认启用）

| # | 项 | 形态 | 默认 | 说明 |
|---|---|---|---|---|
| 1 | `governance-bootstrap` | **新增 CLI 命令** | 启用 | 只读聚合（resolve + 状态投影 + 候选 + migration 标志 + next_actions）；≤8KB 硬预算 + 四阶段钳制（FEAT-033） |
| 2 | `governance-cost-report` | **新增 CLI 命令** | 启用 | 成本埋点（TTFA / 进入实质工作时间 / token 分项）；单命令 <5s（FEAT-032） |
| 3 | `check-injection-budget` | **新增检查子命令** | 启用（lightweight 硬门禁；standard/strict ADVISORY） | canonical 口径分项表 + `sha256_16` 漂移锚 + zstandard 显式断言（FEAT-039 / DEC-210/211） |
| 4 | RISK-055 复验框架 `--ttfa-acceptance` | **新增验收开关（采样框架）** | 启用 | TTFA/TTW 成对报告 + DEC-205 下界声明（FEAT-040） |
| 5 | 回退路径双平台机检（`behavior_profile`） | **新增测试/机检面** | 启用 | 安全边界三层机检（回退表分类 + 不变量不共享 + 双臂逐面相等） |

**无删除项**：本版未删除任何 CLI 命令、检查项或开关；`0.83.0` 既有 88 个 CLI keys / 71 segments 的棘轮基线随新增命令按 FEAT-020 快照机制更新（口径以 M-2 `archguard-ratchet` 当场值为准，本文件不预填）。

## 4. 建议的"降级/回退"开关（本版**未**提供，如实列出）

| # | 场景 | 本版处置 | 归属 |
|---|---|---|---|
| D-1 | 性能/编排协议不适用（旧宿主/旧习惯） | **提供**：F-1/F-2 一键回退 4 项性能行为（§2 B-6） | FEAT-040 / DEC-212 |
| D-2 | 回退后某项安全语义也想"退回旧行为"（例如免确认写） | **不提供**——安全不变量不在回退面（机检锁定 I-1~I-5） | DEC-209 / FEAT-040 三层机检 |
| D-3 | 注入预算在 standard/strict 档被触发但不希望阻断发布 | **已按 ADVISORY 出货**（DEC-210）；无运行时开关——如需收严 = 改姿态并走受审提交 | DEC-210 / RISK-057 |
| D-4 | 检查器判定面误报（`check-injection-budget` 等新面） | **无 flag 级降级**——回退通道 = 版本级回滚（`docs/release/rollback-plan-0.84.0.md`） | 版本级回滚通道 |
| D-5 | 按需加载/薄指针不想生效 | **不提供 flag**——薄指针与按需加载是投影形态（canonical 单源），如需回到旧形态 = 版本级回滚 | FEAT-037/038 + 版本级回滚 |

**Kill switch 需求声明**：本版**无 kill switch 需求**——唯一高风险面（交互语义变更）已由 F-1/F-2 一键回退覆盖，且回退面机检锁定只含性能类；紧急整体回退走版本级回滚（rollback-plan §2/§6）。

## 5. 与 0.83.0 的开关对照（无删除）

- 0.83.0 的既有开关**全部保留**、语义未变：`--quick` 影子通道、product-gate 跳过机制、`check-release --skip-execution-gates` / BR-4、`dsh-doctor` 四开关、loop-claims 豁免账本（`core/loop-runtime-claim-exemptions.json`——4 条豁免维持，digest 锚不变）等；
- 本版**未删除**任何开关、未删除任何豁免登记；
- 0.83.0 行为变更 B-1~B-4（Check 16 fan-out 口径 / Check 14 子检查 6 / ArchGuard 判定面校准 / Check 10 M5 白名单）**延续有效**；0.82.0 B-1~B-8、0.81.0 B-1/B-2 同样延续；
- ArchGuard advisory `fatal_on_error=false` 既有边界**延续不变**。

---

*M-0/M-1 草案冻结（2026-09-19，REL-080 prep）。事实基线：FEAT-032~040 终态取自 plan-tracker 任务行、DEC-204~212、EVD-1073~1081 与对应 REVIEW 报告（机录）；回退 4 项与安全不变量取自 DEC-212①/② 与 FEAT-040 `behavior_profile.py` 三层机检；预算口径取自 DEC-210/211。本文件为草案，M-2 门禁实测值不预填（以 `release-checklist-0.84.0.md` 当场值为准）。*
