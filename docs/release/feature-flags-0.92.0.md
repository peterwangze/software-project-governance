# Feature Flags — 0.92.0

- **日期**: 2026-09-29 · **原则**: 本版**零新增旗标**（例外标注机制=**输出标注面非 flag 面**——annotation-only 不改原始结果/字节/退出码；M-3 RELEASE RL-F3/放行条件① 同口径）；所有执法面出厂姿态沿 0.91.0 不变，翻转留独立授权票（B-12/B-13 纪律）

## 旗标面清单（本版零新增——既有旗标沿用 0.91.0 态）

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` | env（会话级）/ plan-tracker（项目级） | 未设置 = `modern` | 行为灰度开关（FEAT-040，0.84.0 交付——本版零改动）：`=1` 只回退性能行为，**安全语义不回退**（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达——权威源 `skills/software-project-governance/SKILL.md`「行为灰度开关」节） | 不适用（运维开关，非执法翻转面）；LEGACY_REVERTS 白名单约束不变 |
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement：False=判据可观测 WARN 不拦截；True=BLOCK 真拦截（FEAT-069，0.90.0 交付——本版零改动） | **独立授权票**（B-12/B-13 族）：RISK-059 关闭为前置——本版不翻转 |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受控行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上 + 真实迁移授权票 |

## 本版行为变更非旗标面（B-1~B-7——不可配置、无条件启用；每项含回滚）

| # | 行为变更 | 来源 | 效果 | 回滚 |
|---|---|---|---|---|
| **B-1** | strict persona 单源化+薄指针压缩 | FEAT-073 `e65b317` | strict 档会话更轻；strict 注入余量 **9→391 tok**（三档实测 lightweight **3859**/standard **5337**/strict **5609**，/6000 全 PASS） | `git revert e65b317`（persona 恢复多源注入——strict 回 5991/6000 口径）；**无 breaking**，回退即恢复 0.91 行为 |
| **B-2** | release-gate 超时预算 **180→2333s** | FIX-400 `a7bcd5f`+`f06a2bf`（=ceil(1554.78×1.5)——DEC-262 先例同式） | 门禁信号恢复可信（墙钟预算与实测时长匹配，假超时消除） | `git revert f06a2bf a7bcd5f`（恢复 180s——假红面回归，不建议单独执行） |
| **B-3** | loop 计时断言**墙钟→process_time** | FIX-401 `136d65e` | 并行负载假红消除（RISK-048 收窄——预算 27.0→27.8） | `git revert 136d65e`（环境敏感面恢复——风险 reopen，不建议） |
| **B-4** | 发布聚合层**例外标注机制 exception_registry** | FEAT-075 `16a5157`+`484dd77` | EXC-001 两层同屏（原始 ERROR 真实字节+exception accepted 同行）；**annotation-only 不改原始结果/字节/退出码**；dry-run 零写入代码级强制（`Scan REFUSED` exit 1） | `git revert 484dd77 16a5157`（机制面）；EXC-001 条目=`.governance/exceptions.json` 治理数据面，随 DEC 处置撤销（非 revert 面） |
| **B-5** | **LRC 豁免账本第 5 条** LRC-EXEMPT-FIX401R0-79-1 | `df26f7e`（DEC-283 题 2 一次性授权） | 发布门禁 BLOCKED→PASS **逐条披露**（五元组 UNSUPPORTED_AFFIRMATIVE／product_root／`docs/reviews/review-FIX-401-R0.md`／accounting:79:1／LRC-ACTIVE-RUNTIME；九键实测+双锚 re-pin digest 4f8a6cc8→d47f5d16+正负因果测试） | **`git revert df26f7e` 单提交自洽**（锚与账本同提交——无悬挂；回退后 LRC 如实恢复 BLOCKED 判定） |
| **B-6** | 数据面：**有界迁移 18 EVD 出热**（2 任务+18 EVD） | DEC-284 扩展授权（`.governance` 数据面——EVD-1233） | 验收 5/6：18/18 精确／守恒 2921+522／幂等 0/0；消费者经 **`archive/index.md`** 读取（bootstrap 协议既有——读取契约不变） | 迁移面序①：**journal 逐 ID 复原+archive.py rollback**（EVD-1233 隔离副本实弹演练已证可达基线——rollback-plan-0.92.0 §回滚三序） |
| **B-7** | archguard R1 锚**两次 sanctioned regen**（26385→26413→26478） | `f06a2bf`（FIX-400）+`484dd77`（FEAT-075）——DEC-260 分离提交纪律 | 载荷增长受控入锚（fatal gate 全绿 @26478；R6 advisory 205 模块 Δ0；regen deterministic） | 锚随对应功能票 revert **对称回退**（分离提交同序——DEC-260 纪律对称；regen 确定性保证可复现） |

## 无声明变更

本版不声明 official approval、marketplace approval、universal runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）；**容量问题未技术消除**（EXC-001/002 限期例外控制——2026-10-12 硬到期，见 rollback-plan-0.92.0 §EXC 到期处置）；行为级终态验收与权威翻转不在本版（DEC-282 C-1 边界）。

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
