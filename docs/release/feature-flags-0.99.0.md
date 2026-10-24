# Feature Flags — 0.99.0

> 延续 0.98.0 实义旗标面口径：环境变量控制的行为切换面如实声明；0.99.0 新增面仅 FIX-448 迁移授权门禁（内部执行旗标，非用户行为开关）。

| 旗标 | 状态 | 语义与边界 |
|---|---|---|
| `GOVERNANCE_ENFORCEMENT` | 延续 0.98.0 面（FEAT-095） | 默认 off（零漂移 advisory 基线）；on=enforcement-check 分层执法+机录。0.99.0 无语义变更 |
| `GOVERNANCE_LEGACY_BEHAVIOR` | 延续既有面（0.85.0 引入） | =1 只回退性能行为；安全语义不回退（FEAT-040 不变量清单） |
| `SPG_WEB_INSTALL_TIMEOUT` | 延续既有面（FIX-238.4） | web-console --install 超时参数化（默认 120s） |
| `FIX448_EVD_M2_EXECUTE` | **0.99.0 新增（内部授权门禁）** | FIX-448 D1 热表迁移执行旗：≠1 时 `evidence_migration.py --execute` 确定性 refusal（execute_not_authorized，无旁路）。**非用户行为开关**——一次性迁移授权边界（DEC-368④ 审查链后显式设置），迁移完成即失义；dry-run 面无旗标需求 |
| kill-switch / 灰度滚动 | 无 | 本版无 kill-switch 控制的 rollout 面 |

## 行为变更面（非旗标——用户可感知）

1. **DSH 预设原生派生**（FEAT-102/DEC-364）：governance 预设从宿主公开组合树 declaration 派生，不再复制工具行/不写 $DSH_HOME；0.1.x 静态组合退役（DEC-366②口径）；R3-B1 取消窗口为已登记已知边界。
2. **治理热表迁移工具**（FIX-448 D1）：新增 `evidence_migration.py`（Eligibility canonical 单源/RawRowPlan/EVDTransfer I4 阶段机）；本仓热表已执行安全子集迁移（120 实例/207,338B，hot 2157KB→1950KB）——下游零影响（热表 gitignored 不随插件分发）。
3. **审查链与状态机零变更**：FEAT-103/448 载荷零 task-row 状态机 schema 变更；复审必达/CAS 语义 byte-compat 保持。

## 边界

pack enabled/审查链/发布门均不受旗标影响；`FIX448_EVD_M2_EXECUTE` 只控制迁移执行可达性，不构成质量门证明；0.99.0 相对 0.98.0 的用户可见行为变更仅上述非旗标面。

## 边界声明（保守口径——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；旗标面为本地环境变量控制，无远端配置/多宿主同步声明；非 Windows 未验证；本声明件不构成任何发布门/质量门证明。
