# Feature Flags — 0.94.0

- **日期**: 2026-10-03（准备态——tag 未打） · **原则**: 本版**零新增特性开关**（十票载荷全数为元机制执法面接线、指标呈现、等价重构、根因修复与口径钉死——新增检测面一律 WARN 姿态起步，无可配置旗标语义）；所有既有旗标出厂姿态沿 0.93.1 不变，翻转留独立授权票（B-12/B-13 纪律）

## 旗标面清单（本版零新增——既有旗标沿用 0.93.1 态）

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` | env（会话级）/ plan-tracker（项目级） | 未设置 = `modern` | 行为灰度开关（FEAT-040，0.84.0 交付）：`=1` 只回退性能行为，**安全语义不回退**；0.94.0 FEAT-084 追加 LEGACY_REVERTS 第 5 项（performance 类——quick-scan 接线回退面），既有白名单约束不变 | 不适用（运维开关，非执法翻转面） |
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement（FEAT-069，0.90.0 交付——本版零改动；RB2 demo 契约 WARN 为设计内负例夹具） | **独立授权票**（B-12/B-13 族） |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受控行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上 + 真实迁移授权票 |

## 本版行为变更非旗标面（不可配置、无条件启用；每项含回滚）

| # | 行为变更 | 语义 | 回滚 |
|---|---|---|---|
| B-23 | **M2 词集检测 face-5 接线（FEAT-081，DEC-301 承载）**：loop_gate_processor 词集+双向否定语境窗口判定「登记待以后」类表述，deferred_registration **WARN 姿态**起步 + SKIP 分态 + 三键台账追加（既有 append-only 面） | M2 元机制执法面新增检测（ADR-021 B4）——WARN 起步非 BLOCK，无强制阻断；DEC-288 M2 生效判据获真实信号路径 | git revert `2aa2377`（rider 随主提交同序）；台账既有行不受影响 |
| B-24 | **governance-bootstrap behavior 面新增 session_closure 嵌套子面（FEAT-082，DEC-302 键位裁定）**：10 叶键（session_closure_rate/deferred_detections/…）+ 判定口径单源导入 | 指标呈现面新增（新增键 only，既有键零变更；bootstrap 投影面预算内 5377B≤8192） | git revert `5de8548`；依赖 B-23（判定面）——见 rollback-plan 闭链依赖警告 |
| B-25 | **会话健康摘要 `--scope quick｜full` 显式契约（FEAT-084，DEC-303 形态 B）**：会话协议消费 quick（墙钟 62-70s→≤15s）+ 深检/发布门固定 full + **缺省 full 字节等价 BYTE-IDENTICAL** + legacy 第 5 项 performance 回退 | CLI 新增旗标 + 会话协议消费面变化；缺省行为零变化（无 scope 字节等价实证）；quick N 与 full N 口径并存披露义务（RISK-064） | git revert `0377b78`（缺省面无需迁移；RISK-064/065 随票回收评估） |
| B-26 | **Check 28c 版本表状态列解析放宽（FIX-421）**：`FIX_105_SNAPSHOT_RELEASE_VERSION_RE` 状态列=已发布前缀+装饰尾巴 | 检查器信号修复（0.93.x 行漏识致 latest_release 回退 0.92.0 假信号清零）——识别面放宽非判定语义变化 | git revert `8568b1b`（三强制 rider 随票） |
| B-27 | **bootstrap 风险面三口径 fail-safe（FIX-422，DEC-304 固化）**：deadline 纯 ISO 日期前置门 + committed 终态渲染 ✅ 完成标记+refresh-suffix 重渲染 + 关闭态词表扩展（已缓解/已收窄/降级注记） | 治理信号可信度修复（fabricated overdue/假 FAIL 族治本）——读取链向后兼容，存量裸 committed 行可 refresh 重渲染 | git revert `768021b`（回退后假信号族复现——不建议单独回退本票） |

**零机制激活翻转、零破坏性变更**：FIX-423 为防护网 pin/快照面（测试资产口径，非运行时行为——DEC-305）；FEAT-083 为等价重构（CLI 零变化、投影语义不变、接口等价测试守护）；FIX-424/425 为纯 docstring（零行为面）；FIX-426 为纯测试新增（零生产码变更）；B-12/B-13/RB2 出厂姿态与 0.93.1 完全一致。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 已按用户 2026-09-30 裁定关闭〔前提移除式：官方提交暂缓，恢复提交时重开〕；1.0.0 外部验证前置族暂缓——用户声明存在大量未登记需求待登记）。
