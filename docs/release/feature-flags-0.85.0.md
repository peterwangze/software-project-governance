# Feature Flags — 0.85.0（REL-081 / FEAT-054 M-1R）

> **补授说明**：M-3 前 Coordinator 裁决（checklist 披露 ② 差距处置选项 (a)）——本版 feature-flags 面以**最小形态**补授：本版两项行为变更均**无 flag 级降级通道**，本文档即该事实的登记面。起草于 2026-09-20（FEAT-054 修复回合），随候选提交入索引。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.85.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.85.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.85.0 为内部治理效率版；do not claim 1.0.0 production-ready。

## 1. 本版 flag 面总览（空集声明）

| 项 | 值 |
|---|---|
| 本版行为变更 | **B-1**（入口模板契约 v2，FEAT-041）/ **B-2**（resident 预算 hard gate，FEAT-050）——CHANGELOG 0.85.0 段行为变更节原文口径 |
| flag 级通道 | **无**——两项变更均「无 flag 级降级，版本级回滚」为唯一回退路径；发布形态即最终形态，不存在灰度放量开关、运行时 kill switch 或 opt-out 数据面 |
| 既有灰度开关 | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy`（0.84.0 FEAT-040 交付，本版零改动）——见 §4 边界 |

## 2. B-1 入口模板契约 v2（FEAT-041；DEC-218/219）

- **变更**：会话注入的 bootstrap 模板从自包含全文改为「触发器行内 + 明细按需」——行为规程明细按需加载 `skills/software-project-governance/SKILL.md`「Bootstrap 规程明细」§B0~B5；resident 注入 standard 10,718→5,694 / strict 10,918→5,966（砍半）。
- **升级路径兼容**：旧安装 `/plugin update` 整段替换零残留（「详细规则」H2 恢复 = 边界集超集已验证）；单入口工作区行为约束以主入口 `CLAUDE.md` 为准不变。
- **回退通道**：**版本级回滚唯一路径**（CHANGELOG 0.85.0 段 B-1 声明原文）——无 flag 级降级；回滚程序与影响面见 rollback-plan-0.85.0 §1（入口模板契约面行）与 §5（不可回滚项 3：瘦身收益与硬门防护均为版本级整体，不存在部分回滚中间态）。

## 3. B-2 注入预算 resident hard gate（FEAT-050；DEC-211③）

- **变更**：`check-injection-budget` 的 resident 层（standard/strict）从 ADVISORY 翻为 **FAIL**——注入面超 6,000 tok 直接判 FAIL（fail-closed）；skill/command 层维持 report-only。达标基线 4,216/5,694/5,966（EVD-1104）。
- **回退通道**：**版本级回滚唯一路径**（CHANGELOG 0.85.0 段 B-2 声明原文）——回退后 standard/strict 回降 ADVISORY，预算回弹防护弱化（如实披露，见 checklist 披露 ⑥）；`GOVERNANCE_LEGACY_BEHAVIOR` 无法兜底该面。回滚程序与误阻触发条件见 rollback-plan-0.85.0 §1（注入预算门禁面行）与 §6（触发条件 2）。

## 4. 既有灰度开关边界（非本版新增——边界重申）

`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级 env）> plan-tracker `behavior_profile: legacy`（项目级）> 默认 `modern`：只回退**性能/编排行为**（快路径→六段读取 / 首次交互前置→深检先行 / snapshot 渲染契约→完整视图 / Scenario 按需→预加载，共 4 项）；**安全语义不回退**（升级确认门 / 异常不隐藏 / fail-closed / 真实环境防护 / 复审必达，5 不变量）——边界表权威源 = `skills/software-project-governance/SKILL.md`「行为灰度开关」节。本版未改动该通道与 LEGACY_REVERTS 约束（仅 performance 类可入回退表）。

## 5. 未发布面 N/A

- **B-6 snapshot-render 等记号**：全仓零登记（grep 实证，2026-09-20）——规划草案口头记号，未随本版出货，**N/A**；本版 flag 编号序列止于 B-2。
- **flag 清理计划**：不适用（无 flag 出货，无 flag 债务）。
- **kill switch 验证**：不适用（B-2 硬门无运行时关闭数据面；其「触发—生效」路径即版本级回滚，程序与验证表见 rollback-plan-0.85.0 §2/§4）。

## 6. 硬门槛自检（本文件）

| 门槛项 | 判定 |
|---|---|
| 版本串在场 | PASS（0.85.0 多处） |
| 保守边界 5 token 在场 | PASS——五项 boundary token 齐备于「保守边界声明」节，逐项均携带 No…claim 行首 + 未被主张 的否定形态 |
| 禁用正向主张（overclaim） | PASS——全文按「未被主张/无/不适用」记录性措辞，无可索引的 loop-runtime 活体声明 |
| 与 CHANGELOG/rollback-plan 口径一致 | PASS——B-1/B-2 回退口径逐字对齐 CHANGELOG 0.85.0 段行为变更节与 rollback-plan §1/§5 |

---
*FEAT-054 修复回合补授（2026-09-20，Governance Developer Agent 起草，Coordinator 裁决边缘①选 (a) 承载）。事实基线：B-1/B-2 回退口径取自 CHANGELOG 0.85.0 段（`a91d6b4` 冻结版）行为变更节原文；灰度开关边界取自 SKILL.md「行为灰度开关」节实读；达标基线取自 2026-09-20 check-injection-budget 实测；「snapshot-render」零登记取自 git grep 实证。*
