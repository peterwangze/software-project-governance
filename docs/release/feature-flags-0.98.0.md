# Feature Flags — 0.98.0

> 本版为**实义旗标面**版本（0.97.0 为 N/A 声明件先例；0.98.0 引入环境变量控制的行为切换面，如实声明）。

| 旗标 | 状态 | 语义与边界 |
|---|---|---|
| `GOVERNANCE_ENFORCEMENT` | **默认 off（零漂移 advisory 基线）** | FEAT-095 动作级执法总开关。off=六边界仅 advisory 提示+机录（与 0.97.0 行为零漂移——DEC-357 口径钉死）；on=enforcement-check 出口码 0/2/3/4 分层执法（硬阻断/限流升级/提示重建）+ `ENFORCEMENT-ACTION` jsonl 机录含 remedy。**commit 前不设卡**（WIP checkpoint 始终允许）。执法层级=协议级+CLI 级（六平台无宿主级拦截——M-0 §3 调研判定如实降级，DSH 原语完备未接线） |
| `GOVERNANCE_LEGACY_BEHAVIOR` | 延续既有面（0.85.0 引入） | =1 只回退性能行为（M7.8.3 FEAT-034 fallback 面）；**安全语义不回退**（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达——FEAT-040 不变量清单） |
| `SPG_WEB_INSTALL_TIMEOUT` | 延续既有面（FIX-238.4） | web-console --install 超时参数化（默认 120s，非法回退默认） |
| kill-switch / 灰度滚动 | 无 | 本版无 kill-switch 控制的 rollout 面；载荷为静态 CLI/契约文本新增 |

## 行为变更面（非旗标——用户可感知）

1. **goal 危险区收口**（FEAT-097）：多维权预算任一入危险区即收口（70% 轮量必要不充分）；blocked 后未授权续跑被拒并落 unauthorized_attempts（goal_bridge CLI 面）。
2. **审查可信链执法**（FEAT-093/094）：同 ID 双语义写入被拒（task-row-update CAS）；报告/机录冲突判 CONFLICT；R2 义务随 NEEDS_CHANGE 自动登记——复审必达语义零变化（byte-compat 钉）。
3. **归档不覆写保护**（FIX-446）：异物/字节不匹配目标明确拒绝；合法路径零变化。

## 边界

pack enabled/审查链/发布门均不受旗标影响（旗标只控制执法强度面，不构成 quality gate 证明——Pack boundary 口径延续）；`GOVERNANCE_ENFORCEMENT=on` 为 opt-in：默认关闭下 0.98.0 与 0.97.0 行为零漂移（除上述非旗标行为变更面）。

## 边界声明（保守口径——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；旗标面为本地环境变量控制，无远端配置/多宿主同步声明；非 Windows 未验证；本声明件不构成任何发布门/质量门证明。
