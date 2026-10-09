# Feature Flags — 0.97.0

**状态：N/A（本版本无 Feature Flag 面）**

## 依据（release-checklist-0.97.0.md §F 同口径）

1. **本版载荷均为行为契约文本与 CLI 参数扩展，非运行时开关机制**——M7.8 协调开销纪律三契约（FEAT-090）为 Coordinator 行为契约（MUST 语义，违反=流程违规），无运行时配置面、无开关；「关闭」等价于契约不生效（回到待优化行为），不存在合法的技术回退诉求。
2. **delta 复审 --scope/--delta-base（FEAT-091）与 execution-packet --budget（FEAT-092）为 CLI 可选参数**——缺省值向后兼容（scope 缺省 full / budget 缺省不写），参数本身就是「开关」（不传=旧行为），无需独立 flag 面。
3. **Check 30c WARN→FAIL 执法激活（FEAT-089，PROVENANCE_FAIL_ESCALATION_VERSION=0.97.0）为单向棘轮**——设计上不可经 flag 回退（DEC-146 升级路径原文语义：执法升级是本版承诺本身）；合法回退=版本回退（rollback-plan 承载）。
4. **行为变更披露路径**：用户视角行为变化（契约 7~9 注入/30c 执法/预算护栏 advisory）已在 CHANGELOG 0.97.0 段「行为变更（非旗标面）」显式披露——不依赖旗标承载灰度。
5. **GOVERNANCE_LEGACY_BEHAVIOR=1 灰度开关（FEAT-040）延续既有面**——仅 M7.8.3 的 FEAT-034 fallback 性能面可回退（M7.8.1/.2 为新增契约无旧路径），非本版新增 flag。

## Kill Switch 验证

N/A——无旗标即无 Kill Switch 面；行为「回退」= 版本回退（rollback-plan-0.97.0.md 承载：git revert 版本面提交 + tag 回退；发布前全部本地——回退免远端操作）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；0.97.0 交付面为仓内治理工作流本体（dogfood 实证：全量 4758 unittest 0 failed〔M-2 复跑 EVD-1353〕、四票审查链 AWN/0、13 处版本声明一致 @0.97.0、注入预算三 profile 4416/5899/6172）；治理开销优化收益数字（~2.9h/会话、审查链 31%→~15%）为单宿主会话实测基线（session-f3f46901，EVD-1350）推算的目标值，**非多宿主验证声明**——升级后首个宿主会话回测为准（执行包 success_metrics 口径）。
