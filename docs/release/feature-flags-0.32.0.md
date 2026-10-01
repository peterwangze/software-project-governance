# Feature Flag 状态 — 0.32.0

**版本**: 0.32.0
**检查日期**: 2026-05-08
**检查者**: Release Agent (老发)

---

## 当前 Feature Flag 清单

**无**。0.32.0 不涉及 feature flag 变更。

本版本全部为系统级防护机制增强：
- FIX-056 (P0): Agent 意外并发防护——锁机制 + post-commit 锁清理 + Check 25 + check-locks 子命令
- FIX-057 (P1): 项目清洁度治理——未跟踪文件分类归档 + .gitignore + Check 24 + pre-commit Step 10

以上变更均为基础设施/系统级防护，不涉及面向用户的功能入口，不需 feature flag 控制。

## 灰度策略

**不适用**。本版本无新功能入口，无需灰度发布。

Agent 并发防护（agent-locks.json + Coordinator 铁律）是协议级变更——Coordinator 加载 SKILL.md 后即时生效。无需渐进式放量。

## Kill Switch 验证

**不适用**。本版本无功能开关。

紧急关闭方式（如锁机制导致 Coordinator 无法正常工作）：
1. 删除 `.governance/agent-locks.json` 文件（清除所有锁状态）
2. Coordinator 检测到锁文件缺失 → 降级为非锁模式（恢复到 0.31.0 行为）
3. 此降级行为已在 SKILL.md 铁律中定义

## 备注

- 0.32.0 的两个交付均为系统级可靠性增强，不改变用户交互流程
- 如 `agent-locks.json` 格式损坏，`check-locks` 子命令会在 `check-governance` 中检测并告警
- pre-commit Step 10 未跟踪检测可在 `.governance/` 中添加白名单文件列表进行局部豁免
