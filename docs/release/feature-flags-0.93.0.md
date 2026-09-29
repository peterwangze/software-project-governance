# Feature Flags — 0.93.0

- **日期**: 2026-09-29（准备态——tag 未打） · **原则**: 本版**零新增旗标**（M1 需求源执法/M2 发现即闭环为**引擎执法面**，经 DEC-290/291 授权链交付——非旗标可配置面；SD 完好性门/write-then-probe 为**检测与根修面**，无开关语义）；所有执法面出厂姿态沿 0.92.0 不变，翻转留独立授权票（B-12/B-13 纪律）

## 旗标面清单（本版零新增——既有旗标沿用 0.92.0 态）

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` | env（会话级）/ plan-tracker（项目级） | 未设置 = `modern` | 行为灰度开关（FEAT-040，0.84.0 交付——本版零改动）：`=1` 只回退性能行为，**安全语义不回退**（权威源 `skills/software-project-governance/SKILL.md`「行为灰度开关」节） | 不适用（运维开关，非执法翻转面）；LEGACY_REVERTS 白名单约束不变 |
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement（FEAT-069，0.90.0 交付——本版零改动） | **独立授权票**（B-12/B-13 族） |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受控行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上 + 真实迁移授权票 |

## 本版行为变更非旗标面（不可配置、无条件启用；每项含回滚）

| # | 行为变更 | 语义 | 回滚 |
|---|---|---|---|
| B-16 | **CLI `--demand-source` 必填**（FEAT-080 M1-B3）：task-priority-analysis 等入口缺需求源参数即拒绝（窗口关闭——空通道灭绝） | M1 执法：推荐/排序的需求源标注不再是可选项 | git revert `2f3ecd4`；行为面=参数校验移除 |
| B-17 | **Check 41/42 入 check-governance**（FEAT-080）：同优先级 user-named 未闭合时 machine-signal 不得排前（INV-1）+ 闭环率面（INV-X）——违规即 FAIL | M1 执法引擎面（DEC-290/291 授权链） | git revert；检查面从聚合器摘除 |
| B-18 | **发布门 provenance 子检查**（FEAT-080）：check-release 携带需求源完整面 | M1 执法发布门延伸 | git revert |
| B-19 | **SD 完好性门**（FIX-405/406）：release-ready 聚合扫描写受面 os.access(R_OK)，拒读即 FAIL+takeown/icacls 处置模板 | RISK-061 检测面（fail-closed） | git revert `d22a4f9`；检测面摘除（根修面独立） |
| B-20 | **投影 writer write-then-probe**（FIX-409）：写后拒读=显式 FAIL（不回滚字节） | RISK-061 根修+检测双保险 | git revert 终窗 `4f52c6b` writer 段；writer 回 mkdtemp 形态（不推荐） |

**零机制激活翻转**：B-12/B-13/RB2 出厂姿态与 0.92.0 完全一致；M1/M2（B-16~B-18）为引擎执法面交付（交付即生效的检查器/参数校验，无运行时翻转位——如需关闭走独立授权票+旗标化新票）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
