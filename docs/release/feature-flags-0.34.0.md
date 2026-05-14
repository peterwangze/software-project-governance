# Feature Flag 状态 — 0.34.0

**版本**: 0.34.0
**检查日期**: 2026-05-14
**检查者**: Release Agent (老发)

---

## 当前 Feature Flag 清单

**无**。0.34.0 不涉及 feature flag 变更。

本版本为审查驱动质量回收与治理数据标准化：
- AUDIT-099: 全项目质量审查闭环
- FMT-001: plan-tracker 热文件标准化
- FIX-059~067: 真实 E2E、review fallback、归档数据源、持续归档、治理信噪比、架构事实源、G10/G11 Gate 证据质量修复

以上变更均为工作流验证、防护网和发布质量增强，不新增需灰度的用户功能入口。

## 灰度策略

**不适用**。本版本无 feature flag，无需灰度发布。

0.34.0 的验证和防护逻辑随插件版本升级即时生效；发布前通过 `check-version-consistency`、`verify`、`check-governance --fail-on-issues` 和 `e2e-check` 验证。

## Kill Switch 验证

**不适用**。本版本无功能开关。

紧急关闭方式为回滚到 v0.33.0，详见 `docs/release/rollback-plan-0.34.0.md`。

## 备注

- 无新增环境变量
- 无新增外部服务依赖
- 无数据库或持久化 schema 迁移
- 无 breaking changes
