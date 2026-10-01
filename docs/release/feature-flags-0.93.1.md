# Feature Flags — 0.93.1

- **日期**: 2026-10-01（准备态——tag 未打） · **原则**: 本版为**纯修复补丁批，零新增特性开关**（六件载荷 FIX-414~419 全数为根因修复/测试对齐/重构拆分/阈值重校准——无新特性面，无可配置旗标语义）；所有既有旗标出厂姿态沿 0.93.0 不变，翻转留独立授权票（B-12/B-13 纪律）

## 旗标面清单（本版零新增——既有旗标沿用 0.93.0 态）

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` | env（会话级）/ plan-tracker（项目级） | 未设置 = `modern` | 行为灰度开关（FEAT-040，0.84.0 交付——本版零改动）：`=1` 只回退性能行为，**安全语义不回退**（权威源 `skills/software-project-governance/SKILL.md`「行为灰度开关」节） | 不适用（运维开关，非执法翻转面）；LEGACY_REVERTS 白名单约束不变 |
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement（FEAT-069，0.90.0 交付——本版零改动；RB2 demo 契约 WARN 为设计内负例夹具，见对账台账 §三） | **独立授权票**（B-12/B-13 族） |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受控行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上 + 真实迁移授权票 |

## 本版行为变更非旗标面（不可配置、无条件启用；每项含回滚）

| # | 行为变更 | 语义 | 回滚 |
|---|---|---|---|
| B-21 | **`archive.py migrate --auto` 默认 ALL row-family**（FIX-416，授权 DEC：migrate --auto 默认 ALL 口径）：CLI 默认口径与 Check 27 判定口径对齐 + ALL 守卫修正 + 完整分解消息 | 归档触发判定一致性修复（消归档永续红）——非执法强度变化 | git revert `2fa1ebd`（rider 随主提交同序）；行为面=CLI 默认参数回退 |
| B-22 | **release_docs 阈值重校准 80→100**（FIX-419，arch D4 政策口径）+ 21 周实测速率依据 + TOOLS.md 同步 | 检测阈值政策重校准（预警线重定位，非检查项增删） | git revert `bdc037e`；阈值回 80 |

**零机制激活翻转、零测试外产品行为逻辑变化（产品文件触碰限 checks/version.py pin 登记数据重锚——FIX-418-R0 ②核实）**：FIX-414/415/418 为测试面对齐与隔离性根治（FIX-418 经 DEC-080/FIX-187 判定 11F 全数为测试隔离面，零产品缺陷）；FIX-417 为等价重构拆分（CLI 字节等价验证）；B-12/B-13/RB2 出厂姿态与 0.93.0 完全一致。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 已按用户 2026-09-30 裁定关闭〔前提移除式：官方提交暂缓，恢复提交时重开〕；1.0.0 外部验证前置族暂缓——用户声明存在大量未登记需求待登记）。
