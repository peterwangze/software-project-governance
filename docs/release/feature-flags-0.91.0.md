# Feature Flags — 0.91.0

- **日期**: 2026-09-28 · **原则**: 本版**零新增旗标**（M-3 CODE 亲证：窗口 diff CLI 面 `add_argument`/`def cmd_`/`sys.argv` 变更行 = **0**——载荷为 agent 行为契约呈现面 + 解析器判据修复，非 flag 面）；所有执法面出厂姿态沿 0.90 不变，翻转留独立授权票（B-12/B-13 纪律）

## 旗标面清单（本版零新增——既有旗标沿用 0.90.0 态）

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` | env（会话级）/ plan-tracker（项目级） | 未设置 = `modern` | 行为灰度开关（FEAT-040，0.84.0 交付——本版零改动）：`=1` 只回退 4 项性能/编排行为，**安全语义不回退**（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达——权威源 `skills/software-project-governance/SKILL.md`「行为灰度开关」节） | 不适用（运维开关，非执法翻转面）；LEGACY_REVERTS 白名单约束不变 |
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement：False=判据可观测 WARN 不拦截；True=BLOCK 真拦截（FEAT-069，0.90.0 交付——本版零改动） | **独立授权票**（B-12/B-13 族）：RISK-059 关闭为前置——本版不翻转（DEC-268(1)：窗口 diff 守卫 token 零命中实锤、五前置未齐备） |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受控行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上 + 真实迁移授权票 |

## 本版新增非旗标面（不可配置、行为固定——非 flag 面）

- **FEAT-072 三要素推荐卡契约**：M7.4 6b/6c agent 行为契约 prose 重写 + 注入锚 existence-only 机检——**契约呈现面，非 flag 面**（M-3 RELEASE 放行条件④确认口径同构；无配置开关、无条件启用、无机器消费方解析卡正文〔M-3 CODE §5.2 亲证〕）
- **FIX-399 Check 28c 判据修复**：解析器对装饰日期单元格召回向放宽 + 末日期（发布日）语义——无条件启用（纯格式旧行为不变，回退=版本级回滚，rollback-plan-0.91.0 §发布后回滚）

## 无声明变更

本版不声明 official approval、marketplace approval、universal runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）；行为级终态验收未完成（DEC-263 版本定义边界不变）。

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
