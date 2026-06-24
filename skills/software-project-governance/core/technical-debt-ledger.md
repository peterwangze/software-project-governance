# 技术债登记表（Technical Debt Ledger）

> **建立版本**: 0.57.0（AUDIT-121 / DEC-083）
> **用途**: 系统性登记架构/实现腐化项，为 ArchGuard（0.58.0+）和重构版本提供可跟踪的事实源
> **维护规则**: 每个 AUDIT 发现的腐化项必须在此登记；重构完成项标记 RESOLVED 并关联证据；ArchGuard 0.58.0 落地后将从此表读取已知债项并持续守护

---

## 登记项

| 债务 ID | 登记日期 | 来源 AUDIT | 描述 | 严重度 | 影响范围 | 承载版本 | 状态 | 关联证据/决策 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TD-001 | 2026-06-24 | AUDIT-121 | verify_workflow.py God Module——20,294 行/439 def+class/54 CLI 子命令/40+ 全局常量集中单文件 | P0 | 认知负担、测试耦合、AI 可维护性、演进摩擦 | 0.59.0~0.64.0 渐进式拆分 | OPEN | F1, DEC-083, RISK-039 |
| TD-002 | 2026-06-24 | AUDIT-121 | 缺失现代 Python 工程基础设施——无 src/ layout、无 lint（ruff/flake8）、无 formatter、无 type checker（mypy）、无 PEP 517/518 打包元数据 | P0 | 代码风格漂移、类型错误仅 runtime 暴露、无静态分析、新贡献者无 onboarding | 0.64.0 | OPEN | F2, DEC-083 |
| TD-003 | 2026-06-24 | AUDIT-121 | source/projection 双写——verify_workflow.py source(20294) vs projection(14166) 差异 6128 行需 check-projection-sync 人工盯防；archive/cleanup/test 同样双写 | P1 | 双重维护成本、projection 漂移风险、fixture 体积膨胀 | 0.64.0（改为生成时投影） | OPEN | F3, DEC-083 |
| TD-004 | 2026-06-24 | AUDIT-121 | 命令面冗余——commands/ 下 8 文件 2232 行，7 个是 /governance 重复入口 | P2 | 文档维护冗余（已知平台能力缺口，非本项目可独立解决） | 等待上游能力补齐（AUDIT-120/DEC-082） | DEFERRED | F4, AUDIT-120, DEC-082 |
| TD-005 | 2026-06-24 | AUDIT-121 | 自演进遗留物堆积——根目录游离脚本、Windows 误创建文件、docs/release 累积 105 文件无归档机制 | P1 | 仓库根污染、历史发布文档无归档、清理看护盲区 | 0.57.0（部分闭环） | PARTIAL | F5；nul + _fix_030_reconstruct.py 已清理；docs/release 归档待 ArchGuard check-technical-debt |
| TD-006 | 2026-06-24 | AUDIT-121 | 架构腐化看护缺口——28 check 全是结构/事后/自觉型，0 个 check 守护模块大小/重复/复杂度/技术债；verify_workflow.py 膨胀到 2 万行触发零告警 | P0 | 工作流无法看护自身及宿主项目工程健康；1.0.0 可信度根部裂痕 | 0.58.0（ArchGuard 独立能力） | IN_PROGRESS | F6, DEC-083, RISK-039；0.58.0 ArchGuard 设计已启动（REQ-101，docs/requirements/archguard-design-0.58.0.md） |
| TD-007 | 2026-06-25 | AUDIT-121(发现)/REQ-101(纳入) | hooks 内容漂移检测缺口——bootstrap 只检测 .git/hooks 是否存在，不检测内容与源一致性；实测 4 个已安装 hooks 全部漂移（post-commit 停在 0.32.0，缺 self-upgrade 机制） | P1 | 已安装 hooks 静默落后于源，治理约束实际未生效而不告警 | 0.58.0（ArchGuard check-technical-debt 含 hooks drift 检测） | OPEN | AUDIT-121 hooks 漂移修复记录；archguard-design-0.58.0.md §2.3 |
| TD-008 | 2026-06-25 | REQ-101 | PRODUCT_CODE_PATTERNS 重复定义——verify_workflow.py:11666 与 :14064 各定义一次，潜在可变状态冲突 | P2 | 同名常量二次赋值，后定义覆盖前定义，维护易出错 | 0.59.0（manifest 域拆分时合并） | OPEN | archguard-design-0.58.0.md §2.1 重复定义检测 |
| TD-009 | 2026-06-25 | REQ-101 | evidence-log 列规范不统一——表无显式 schema 表头，各 EVD 条目列数不一（EVD-618 10列、EVD-619 12列、REVIEW-REL-043 10列），check-governance 标为非 blocking WARN | P2 | 结构不一致影响机器解析，长期累积可读性下降 | 待评估（ArchGuard check-structural-validity 可扩展） | OPEN | check-governance Check 28 structural WARN |
| TD-010 | 2026-06-25 | REQ-101 | governance-context 启发式误报——把 0.54.2 已撤回版本路线图行（含 FIX-143/REL-037/AUDIT-115 token）误识别为 unfinished work，实为 RISK-038 已关闭的历史失败链 | P2 | 恢复路径误报待办任务，干扰 Scenario D 会话恢复判断 | 待评估（governance-context 检测器需排除"已撤回/失效"版本） | OPEN | governance-context 输出；RISK-038 已关闭 |

---

## 维护纪律

1. **发现即登记**：任何 AUDIT/审视发现的架构/实现腐化项必须在表中新增行，分配 TD-NNN
2. **状态流转**：OPEN → IN_PROGRESS（启动承载版本时）→ RESOLVED（重构完成且有证据）或 DEFERRED（明确延期理由）
3. **证据绑定**：RESOLVED 项必须关联 EVD/REVIEW 证据；DEFERRED 项必须关联 DEC 决策
4. **ArchGuard 消费**：0.58.0 `check-technical-debt` 将读取本表，校验 OPEN/IN_PROGRESS 项是否在对应版本路线图中
5. **不隐瞒**：本表是公开技术债事实源，不得为"显得健康"而删除 OPEN 项

---

## 0.57.0 闭环记录

- **TD-005 PARTIAL 闭环**：已清理 `nul`（Windows 设备名误创建，未跟踪，无引用）+ `_fix_030_reconstruct.py`（FIX-030 一次性重构脚本残留，未跟踪，FIX-030 已于 2026-05 月完成）。剩余 `docs/release` 105 文件归档机制留待 0.58.0 ArchGuard `check-technical-debt` 实现后闭环。
