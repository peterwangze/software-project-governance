# Feature Flags — 0.95.0

**状态：N/A（本版本无 Feature Flag 面）**

## 依据（release-checklist-0.95.0.md §F 同口径）

1. **M10 主动生态探索协议是行为协议层，非运行时机制**——EXP-01~05 为 Coordinator/角色 Agent 的行为规范（behavior-protocol.md 唯一规范源），无运行时开关、无配置面、无 kill-switch 语义；「关闭」等价于协议不遵守（流程违规），不存在技术回退面。
2. **六平台 `exploration_channels` manifest 声明为静态能力标注**（additive 键，FEAT-086 R0 §3 诚实性核验通过）——非可切换功能。
3. **quote_sync 引文同步守卫为检查器扩展**（check-cross-references 新维度）——检查面可经既有排除机制豁免，不构成产品功能 flag。
4. **行为变更披露路径**：用户视角的行为变化（新任务探索判断义务）已在 CHANGELOG 0.95.0 段「行为变更（非旗标面）」显式披露——不依赖旗标承载灰度。

## Kill Switch 验证

N/A——无旗标即无 Kill Switch 面；行为协议的「回退」= 版本回退（rollback-plan-0.95.0.md 承载：git revert 发布 commit 序列 + tag 回退）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 已按用户 2026-09-30 裁定关闭〔前提移除式：官方提交暂缓，恢复提交时重开〕；1.0.0 外部验证前置族暂缓——用户声明存在大量未登记需求待登记）。0.95.0 交付面为仓内治理工作流本体（dogfood 实证：1052 unittest、双审 AWN/0×2、13 处版本声明一致）；M10 行为协议的前瞻样本验收为仓内行为面验证（5 样本三类，docs/research/feat-086-prospective-samples-2026-10-04.md），不构成外部运行时支持声明。
