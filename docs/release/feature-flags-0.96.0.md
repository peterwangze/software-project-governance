# Feature Flags — 0.96.0

**状态：N/A（本版本无 Feature Flag 面）**

## 依据（release-checklist-0.96.0.md §F 同口径）

1. **新增守护均为入口期/检查器守卫，非运行时机制**——bootstrap H2-singleton 写前守护（FIX-439）为写入路径前置校验（违规 ⇒ exit 1 拒绝写入），无运行时开关、无配置面、无 kill-switch 语义；「关闭」等价于守护不生效（缺陷复发——incident-20261006 第 2 次复发环），不存在合法的技术回退诉求。
2. **evidence/decision-append 校验前置（FIX-439③）为 fail-closed 承诺兑现**——拒绝 ⇒ 零持久化零台账；该行为自 FIX-228 起即为文档化承诺，本版为缺陷修复（承诺原未成立）非新机制。
3. **dry-run 预演 guard（FIX-440 F-3）为既有 dry-run 通道的预演扩展**——不构成产品功能 flag。
4. **行为变更披露路径**：用户视角的行为变化（bootstrap 写入守护/拒绝零落盘）已在 CHANGELOG 0.96.0 段「行为变更（非旗标面）」显式披露——不依赖旗标承载灰度。

## Kill Switch 验证

N/A——无旗标即无 Kill Switch 面；守护行为的「回退」= 版本回退（rollback-plan-0.96.0.md 承载：git revert 发布 commit 序列 + tag 回退；发布前 ahead 8 全部本地——回退免远端操作）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；0.96.0 交付面为仓内治理工作流本体（dogfood 实证：1061 unittest〔f=2 预存披露集——M-2 定谳〕、七票审查链 AWN/0、13 处版本声明一致 @0.96.0）；宿主 incident 根治（FIX-439/440）以「云视TV」实测三缺陷族为界（incident-20261006-dsh-bootstrap-splice-repeat.md），不构成全部外部宿主形态验证声明。
