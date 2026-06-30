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
| TD-011 | 2026-06-25 | REQ-101 | 发布流程遗漏"更新路线图状态"——0.57.0 发布后 plan-tracker 版本路线图 0.57.0 行仍标记"规划"，导致 check 28c hot-fact-source 一致性告警（_latest_published_release_fact 正则匹配"已发布"状态，0.57.0 未匹配使 0.56.1 被误判为最新发布）。release-checklist 未明确列"发布后更新 plan-tracker 路线图状态为已发布"步骤 | P2 | 发布流程依赖人工记忆更新路线图状态，易遗漏；check 28c 能事后捕获但属被动告警 | 待评估（release-checklist 模板 + verify_workflow check-release 应增加"路线图状态一致性"前置检查） | OPEN | check 28c FIX-105_SNAPSHOT_RELEASE_VERSION_RE；0.57.0 发布后 check-governance 1 issue 已修复 |
| TD-012 | 2026-06-25 | FIX-152 | ArchGuard check_duplicate_code 用"归一化行集合对称差"而非设计 §2.2/§6 的"行计数 diff"计算 duplicate_pct——重复样板行被去重，duplicate_pct 偏高于 diff 校准基线（设计按 diff -w 校准 32.5%，集合法在 verify_workflow.py 实测 64.7%）。阈值 WARN60/ERROR80 是按 diff 指标校准的，集合法数值不可直接对比。事后 Explore Code Review Finding #4 | P3 | 集合法与 diff 法数值不可比，阈值校准与实测口径不一致；advvisory 不阻断 gate 故非紧急，但影响 duplicate_pct 的可解释性 | 0.59.0+ | IN_PROGRESS | 事后 Explore Code Review（DEC-085），EVD-622；ArchGuard check_duplicate_code verify_workflow.py:_archguard 计算段 |
| TD-013 | 2026-06-25 | FIX-152 | check-architecture-health 全仓库扫描含 project/e2e-test-project/ projection 副本，导致每个 infra 文件 module_size/function_size 被报告两次（source 一次 + projection 一次），发现计数虚高。事后 Explore Code Review Finding #5 | P3 | 发现计数虚高影响信号清晰度；projection 是生成副本非源模块；RealCodebaseIntegrationTest 已用 "e2e-test-project" not in path 临时规避 | 0.59.0+ | IN_PROGRESS | 事后 Explore Code Review（DEC-085），EVD-622；_archguard_iter_code_files 应排除 repo_only 分类的 project/ 路径 |
| TD-014 | 2026-06-28 | FIX-158 | archive.py decision-log/risk-log 迁移逻辑未实现。`_decision_log()`(archive.py:52)/`_risk_log()`(archive.py:56) path getter 已定义、`archive/decisions`+`archive/risks` 目录已创建、`build_index`(archive.py:920-952)+`verify_archive_integrity`(archive.py:1050) 已能读取这两个目录，但 `migrate_by_version`(archive.py:548-776) 只有 task+evidence 两个迁移分支，无 decision/risk 迁移代码。FIX-158 计划第(5)项跳过。事后 Explore Code Review Finding P2 #1 | P2 | decision-log.md(138KB)/risk-log.md(42KB) 持续膨胀但永不归档；build_index 的 Decision/Risk 索引段永远为空。不阻塞 task/evidence 核心归档职能（已完成），但治理数据膨胀的 decision/risk 维度无覆盖。AUDIT-125 根因 3"覆盖盲区"的残留 | 0.62.0+ | RESOLVED | **2026-06-30 FIX-162 兑现**（EVD-640）：新增 `_migrate_decisions`/`_migrate_risks`/`_entry_version_for_archive`，dry-run 29 decisions + 11 risks 可迁出。审查发现的 P0（FIX-162/163 耦合回归）+ P2-1（decision 保真）当场修复 |
| TD-015 | 2026-06-28 | FIX-158 | verify_archive_integrity Check 3（archive.py:1145-1162）只统计 total_in_files 与 total_in_index 两个独立计数，从不比较二者差异、从不向 issues 追加。即使文件有条目但索引漏了（或反之），result["pass"] 仍为 True。事后 Explore Code Review Finding P2 #2（历史意见，本次未修） | P2 | 归档完整性检查存在盲区——"文件数 vs 索引数"漂移无法被自动发现。当前恰好相等（355=355）掩盖了检查缺失。FIX-157 时期审查员首次提出，FIX-158 未修 | 0.62.0+ | RESOLVED | **2026-06-30 FIX-163 兑现**（EVD-641）：Check 3 改 per-category 对称计数（tasks/evidence/decisions/risks 各自比对），+2 测试（drift 检测 + coupling guard）。修复了 FIX-162 耦合回归（审查员 P0） |

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
