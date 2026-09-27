# Feature Flags — 0.90.0

- **日期**: 2026-09-27 · **原则**: 本版**无新激活旗标**；所有新执法面出厂 WARN-only，翻转留独立授权票（B-12/B-13 先例纪律）

## 旗标面清单

| 旗标 | 位置 | 出厂值 | 语义 | 翻转条件 |
|---|---|---|---|---|
| `RB2_SENSITIVE_BLOCK_ENFORCED` | `infra/checks/evidence_domain.py` | `False` | 敏感动作阻断 enforcement：False=判据可观测 WARN 不拦截；True=BLOCK 真拦截 | **独立授权票**（B-12/B-13 族）：RISK-059 关闭+翻转 checklist（渲染分文案 N-1+敏感词表审查 N-5——REVIEW-FEAT-069-R0 遗留已登记） |
| B-12 分族 BLOCK（write-guard） | 既有 | 未激活 | 受管行族 BLOCK 姿态（0.86 交付） | 同上（独立授权票） |
| B-13 storage 切换 | 既有 | 未激活 | 治理记录存储切换（FEAT-061 协议层） | 同上+真实迁移授权票 |

## 本版新增非旗标面（不可配置、行为固定）

- RB-2 **宿主激活前置判据**（check_goal_layer_contract_readiness）：模板默认值契约宿主→WARN 六字段明细（判据面，非阻断面）
- 迁移链自愈重入（FIX-398）：中断态检测+补偿，无条件启用（P7 纯减法，回退=--rollback）
- 结构派生影子（FEAT-071 `--shadow-derive`）：显式调用才运行，零副作用（只读）

## 无声明变更

本版不声明 official approval / marketplace approval / universal runtime support（RISK-036 边界维持）；行为级终态验收未完成（DEC-263 版本定义）。
