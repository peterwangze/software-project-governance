# Feature Flags — 0.86.0（REL-082 M-1R / REL-083）

> **起草说明**：本版 feature-flags 面随 M-1R 四件套一次成形（对照 feature-flags-0.85.0 最小形态先例——0.85.0 期由修复回合补授，0.86.0 起四件套为 M-1R 标准面）。本版两项行为变更（B-3/B-4）均**无 flag 级降级通道**，本文档即该事实的登记面 + 既有灰度开关边界重申 + write-guard WARN 姿态登记。起草于 2026-09-20（REL-083），随候选提交入索引。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.86.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.86.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.86.0 为内部治理效率版；do not claim 1.0.0 production-ready。

## 1. 本版 flag 面总览

| 项 | 值 |
|---|---|
| 本版行为变更 | **B-3**（治理行写入路径收敛 + write-guard WARN 姿态，FEAT-051/046/057）/ **B-4**（CLI 步超时分类学 step_unknown，FEAT-056）——CHANGELOG 0.86.0 段行为变更节原文口径 |
| flag 级通道 | **无**——两项变更均「版本级回滚」为唯一回退路径；发布形态即最终形态，不存在灰度放量开关、运行时 kill switch 或 opt-out 数据面 |
| 非破坏性说明 | B-3 为**执法姿态 WARN**（非门禁硬化）——无凭证手写行 WARN 响亮披露但 exit 0 不阻断，既有手工路径仍可用；Breaking changes = 无（CHANGELOG semver 论证段同口径） |
| 既有灰度开关 | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy`（0.84.0 FEAT-040 交付，本版零改动）——见 §4 边界 |

## 2. B-3 治理行写入路径收敛 + write-guard WARN 姿态（FEAT-051/046/057；DEC-222/224）

- **变更**：受管行族（EVD/DEC/REVIEW/任务状态列/ops 台账）的变更**机录优先**——经 governance-store/task-row-update 等 CLI 写入并留机器凭证（`〔op-…〕` 锚 / receipt operation_id / governance-store 标记）；write-guard 面 5 对无凭证手写行 **WARN 响亮披露（exit 0 不阻断）**——非破坏性执法，commit 面板可见。
- **用户视角**：获得 = 治理行变更首次拥有可对账的机器写入路径（凭证 join 锚）；感知 = commit 面板 WARN 计数披露行；体验 = 正向（手工路径不破坏——机录优先非机录强制）。
- **BLOCK 升级边界（未发布面）**：WARN→BLOCK 升级**不在本版**——DEC-224 双约束（不得 WARN-once-then-absorb + hook 窗口消费权台账化）随升级一并落地，留 0.87（CHANGELOG 披露⑤ / rollback-plan §8 移交清单 #2）。
- **回退通道**：**版本级回滚唯一路径**（CHANGELOG 0.86.0 段 B-3 声明原文）——无 flag 级降级；回退后行族对账执法面消失，手工直写回到无守卫 0.85.0 态（8 次手工事故防护代价评估见 rollback-plan-0.86.0 §7）。已按机录路径写入的治理行回滚后合法保留（0.85.0 引擎忽略面读取）。

## 3. B-4 CLI 步超时分类学 step_unknown（FEAT-056；DEC-224(c)）

- **变更**：closure-chain CLI 步超时从笼统失败改为 **step_unknown** 执行态——恢复由 effect-based resume 的世界核验门控处置（互斥双腿：landed=reconcile / NOT-landed=重执行 + replay 兜底；DEC-224(c) 与 external 步分类学对齐——review-FEAT-056-R0 P2-1 + review-FEAT-057-R0 P1-1 承接）。
- **边界**：链内部语义，**不改变任何既有 CLI 的对外退出码契约**；用户可感知面 = 恢复路径可靠性（kill/超时后单命令 resume 零重复追加零人工修复——本版 M-2 量测 C 组实测 + 混沌 35 passed 门）。
- **回退通道**：**版本级回滚唯一路径**（CHANGELOG 0.86.0 段 B-4 声明原文）——回退后 CLI 步超时回退笼统失败，恢复可靠性弱化（如实披露，rollback-plan §1 B-4 行）。程序与验证表见 rollback-plan-0.86.0 §2/§4。

## 4. 既有灰度开关边界（非本版新增——边界重申）

`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级 env，优先级高）> plan-tracker `behavior_profile: legacy`（项目级）> 默认 `modern`（非法值不猜——`governance-bootstrap` behavior.invalid 显式报告）：只回退**性能/编排行为**（快路径→六段读取 / 首次交互前置→深检先行 / ≤8 字段默认视图→完整快照契约 / Scenario 按需→预加载，共 4 项）；**安全语义不回退**（六不变量——升级确认门 / 异常不隐藏 / fail-closed〔`resolved_root_ok == false` 即停〕/ 真实环境防护〔三选一〕/ 复审必达 / 升级确认门前零写操作）——边界表权威源 = `skills/software-project-governance/SKILL.md`「行为灰度开关」节。本版未改动该通道与 LEGACY_REVERTS 约束（仅 performance 类可入回退表；任何把安全语义塞入回退表的改动会被守护测试翻红——`behavior_profile.revert_contract_issues()` 机检）。

**B-3/B-4 与灰度开关的正交性**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载** B-3 执法面与 B-4 恢复语义的回退——两变更属治理行为而非性能/编排行为，不在 LEGACY_REVERTS 白名单；不存在「legacy 模式下关闭 write-guard/closure-chain」的中间态。

## 5. 未发布面 N/A

- **write-guard BLOCK 升级**：留 0.87（DEC-224 双约束随升级落地）——本版 WARN 姿态即最终形态，无渐进放量面；
- **flag 清理计划**：不适用（本版无 flag 出货，无 flag 债务）；0.86.0 flag 编号序列止于 B-4；
- **kill switch 验证**：不适用（B-3 WARN 姿态本身即非阻断设计无需 kill switch；B-4 无运行时关闭数据面——其「触发—生效」路径即版本级回滚，程序与验证表见 rollback-plan-0.86.0 §2/§4）。

## 6. 硬门槛自检（本文件）

| 门槛项 | 判定 |
|---|---|
| 版本串在场 | PASS（0.86.0 多处） |
| 保守边界 5 token 在场 | PASS——五项 boundary token 齐备于「保守边界声明」节，逐项均携带 No…claim 行首 + 未被主张 的否定形态 |
| 禁用正向主张（overclaim） | PASS——全文按「未被主张/无/不适用」记录性措辞，无可索引的 loop-runtime 活体声明 |
| 与 CHANGELOG/rollback-plan 口径一致 | PASS——B-3/B-4 回退口径逐字对齐 CHANGELOG 0.86.0 段行为变更节与 rollback-plan §1/§5/§7 |
| 表行管道符转义（FIX-365 ragged 教训） | PASS——表 cell 内零裸管道符，全行单层管道分隔 |

---
*REL-083 M-1R 起草冻结（2026-09-20，REL-083，Governance Developer Agent 起草）。事实基线：B-3/B-4 回退口径取自 CHANGELOG 0.86.0 段（`44831b8` 冻结版）行为变更节原文；灰度开关边界取自 SKILL.md「行为灰度开关」节实读；BLOCK 升级双约束取自 DEC-224 实读；write-guard WARN 姿态与首活体实证取自 EVD-1117/1118；混沌门与量测数据取自本票 M-2 实测记录。*
