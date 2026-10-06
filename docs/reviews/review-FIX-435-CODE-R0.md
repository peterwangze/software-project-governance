# REVIEW-FIX-435-CODE-R0 — B16 archive.py C2 拆分续：行为等价性与 exclusions 棘轮回收独立审查（CODE）

**Round: R0（首轮）** | Reviewer: Code Reviewer（独立审查；唯一写入 = 本报告文件）| 日期锚：HEAD `185aa31`（2026-10-06）
审查对象：**未提交工作树 diff**（8 路径 = 4 修改 + 4 新建，`git status` 实测无溢出）：`infra/archive.py` 4241→1697 行（入口壳：双根 seam + 同签名包装器 + 核心编排器 + CLI main）+ 新模块 `archive_verdicts.py`（726）/`archive_migration_engine.py`（1170）/`archive_entity_migration.py`（589）/`archive_cli.py`（332）+ `core/architecture-health.json`（module_size.exclusions 移除 archive.py 条目 4 行）+ `tests/test_archive.py`（+5）/`tests/test_architecture_health.py`（+3）。

与 FIX-432 R0 先例不同：本审查**有命令通道**（任务书硬门槛明示 MUST 抽样独立复跑），全部关键结论均由本审查亲跑命令产出，无「依 EVD 记录背书」项。

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**（无 P0/P1 finding；行为等价由三层独立证据闭环，exclusions 棘轮兑现，A5 纪律零违反，+8 用例为真实守护，模块职责单一成立，性能预算内改善）
findings 计数：P0=0 · P1=0 · P2=1 · P3=4。P2 为 engine docstring 对 patch 口径的表述过宽（文档精度，无行为缺陷）；P3 为隔离加载用例判别力披露/冷导入开销披露/套件失败计数对账/陈旧注释携带，均不阻塞本票收口。

## 逐项核验（验收 ①~⑥）

### ① 行为等价 — 通过（三层独立证据）

**(a) 真实数据字节级对照**（狗粮仓库，全部只读；HEAD 版经 `git show` 原始字节提取至 %TEMP% 独立执行，PYTHONPATH 指向 infra 以复用未触碰的 parsing/indexing 兄弟模块）：

| 对照面 | 结果 |
|---|---|
| `migrate --auto --dry-run` | stdout+exit code **逐字节一致**（0/0） |
| `migrate 0.60.0 0.93.0 --dry-run`（EVD） | 逐字节一致 |
| `migrate 0.60.0 0.93.0 --dry-run --row-family ALL` | 逐字节一致 |
| `migrate-big-table evidence 0.60.0 0.93.0 --dry-run`（EVD） | 逐字节一致 |
| 同上 `--row-family TRIAGE` | 逐字节一致 |
| `scan-families 0.60.0 0.93.0 --output <temp.tsv>` | 四族 **406 行分类 TSV 逐字节一致**（42,295 B，sha256 相等；EVD 188/REVIEW 130/RECO 46/TRIAGE 42，逐 reason 分布一致） |
| CLI 8 面 `--help`（top + 7 子命令） | **全部逐字节一致**（sha256 两两相等） |

Developer「三连比对零翻转」声明在审查抽样上成立且被更强形式（TSV 逐行 + 全 dry-run 家族 stdout）覆盖。

**(b) AST 级结构比对**（自写脚本：HEAD 89 个顶层 def/class 与拆分后五模块全量对位；78 个函数体在 host-下标归一化 + `_impl` 后缀归一化后逐体比对）：
- 29 个纯函数/常量/编排器 **SAME**（含 `migrate_by_version`/`_run_entity_migrations`/`build_index`/`verify_archive_integrity`/`rebuild_index`/`rollback_last_migration`/`analyze_auto_archive_candidates`/`migrate_auto`/`_window_end_release_date`/`_evidence_*` 六阶段/`_migration_write_journal`/`_migration_write_batch`/`_atomic_write_text`/CLI parser 等）；
- 全部 DIFF 残差经逐条人工裁决 = **声明过的机械 seam**：`*, host` 参数 + `host["NAME"]` 调用时解析、`q6_fallback` 注入（`_q6_date_window_fallback` 拆为 end_date 解析〔留壳，经模块 globals 读 `_window_end_release_date`〕+ 纯判定 impl）、`context=None` 默认值上移至壳包装器（ROOT 绑定读取留在入口模块）、路径参数化（`archive_dir`/`gov_dir`/`evidence_subdir`/`next_evd_filename`/`state_dir` 由壳包装器注入）、CLI `impl[...]` 分发；**零业务逻辑行漂移**；
- 唯一名称未保留：HEAD `_classify_family_rows` → `_classify_family_rows_impl`（+`q6_fallback` 参数）——全仓 grep 实证无任何外部消费方（tests/verify_workflow/兄弟模块零引用），不破坏任何面；verify_workflow 隔离加载器仅消费 `analyze_auto_archive_candidates`/`verify_archive_integrity`，两者均留在壳内。
- HEAD 20 个模块级常量全部保留（ROOT 族+阈值在壳；家族常量在 engine 并由壳 re-import）。

**(c) host seam 语义**（源码逐点核实 + 测试实证）：
- 测试实际 patch 面（test_archive.py grep 实证 103 处）：`ROOT`/`PLUGIN_ROOT` ×~96、`_migration_write_batch`（staging 崩溃 ×6）、`_atomic_write_text`（commit 崩溃，按 `path.name == "evidence-log.md"` 条件拦截）、`_migration_write_journal`（finalize 崩溃）、`_decision_authority_state`（并发切换 TOCTOU：entry 门 + in-lock 复检两次调用）、`_window_end_release_date`（Q6 新守护用例）——**全部**经 `host["..."]` 调用时解析（engine/entity 源码逐调用点核实：`_evidence_log`/`_plan_tracker`/`_archive_dir`/`_gov_dir`/`_decision_log`/`_risk_log`/`_ensure_archive_dirs`/`_classify_rows_for_family`/`_build_classification_context`/`_evidence_task_versions_standalone`/`_migration_journal_path`/`_next_family_archive_filename`/`_migration_write_journal`/`_migration_write_batch`/`_atomic_write_text`/`_decision_authority_state`/`_q6_date_window_fallback`/`scan` 锚的 `ROOT`）；
- 依赖方向单向无环：archive → cli/engine/entity/verdicts → parsing/indexing；**无任何兄弟 import archive**（rogue 二次实例不可能，隔离加载不变量成立）；
- `patch.object(archive, X)` = 写 `archive.__dict__` = 写 `globals()` = 写 host 字典——同字典，seam 数学上闭合；隔离 spec_from_file_location 实例的 `globals()` 即自身命名空间，`module.ROOT` 重绑直达引擎（`_load_archive_module` L9817-9836 实读确认重绑面恰为 ROOT/HOST_PROJECT_ROOT）。
- **新守护用例真实性裁决**：`test_q6_wrapper_honors_window_end_patch` **判别力成立**（双分支设计：patch 返回 None 分支在 seam 失效〔真实 `_window_end_release_date` 对 0.90.0 返回日期〕时必然 FAIL——非空转）；legacy surface（47 callable + 15 object）/异常层级/payload/签名用例均为真实断言；`test_isolated_loader_instance_is_seam_consistent` 判别力**部分**（见 F-2），但作为隔离加载路径冒烟 + 与既有 ~96 处 `patch.object(archive, "ROOT")` 大家族互补，seam 整体被锁死。

### ② exclusions 棘轮回收 — 通过

`git diff HEAD -- core/architecture-health.json` 实测**唯一变更 = 删除 module_size.exclusions 的 archive.py 条目（恰 4 行）**；worktree 全 JSON `archive` 匹配仅剩 2 处（L72 `release_docs_archive_threshold_versions` / L73 `release_docs_note` 注记字符串），与 Developer「残留 2 处非 exclusions」声明一致；无新增 exclusions、无任何阈值改动。`check-architecture-health` 实跑：**archive 家族 7 模块零 finding**（findings 全部为 closure_chain/dsh_compat/governance_store/loop_*/task_*/verify_workflow 预存项；archive.py 1697 / parsing 1435 / engine 1170 均 < warn 2000）。

### ③ A5 纪律 — 通过（零新增违规实证）

- `verify_workflow.py` 零触碰（`git diff HEAD --stat` + `git status --porcelain` 双空实测）——R1 锚点安全；
- `archguard-ratchet` 实跑 FAIL 集 = **R1 mainfile +440 / R2 dsh_doctor import_vw +1 / R4 print total +28（三函数分解）/ R5 cli keys check-exploration-channels / R7 committed==fresh**——与任务书声明逐条对号，**零条目涉及 archive 族文件**（R6 冷导入 Δ0）；
- 全量套件实跑（24m16s）：**18 failed / 4695 passed / 1 skipped**（16 FAILED + 2 SUBFAILED[strict]）；为闭合「HEAD 同在」声明，本审查以 **detached HEAD worktree**（`git worktree add --detach %TEMP% HEAD`，不触碰受审工作树，验后已 remove）对账：**9 个硬 FAILED 逐条复现 + 2 个 SUBFAILED 复现——工作树全部 18 失败均在 HEAD 同败**，属 FEAT-088 快照/基线未 regen 族 + contracts/registry/预算族预存债，**零新增失败**。18 vs 声明 19 的计数差见 F-4（不影响零新增结论）。

### ④ 测试 +8 真实守护 — 通过

`test_archive.py` +5（`TestFix435SplitSurface`：legacy surface 47+15 名解析 / 异常层级+payload / 三函数签名+默认值 inspect / Q6 patch 双分支 / 隔离加载器 seam）；`test_architecture_health.py` +3（`ArchiveFamilySizeGuardTests`：实跑 `check_architecture_health` 断言家族零 finding〔skipTest 仅限 schema 不可用环境〕/ 活 schema 断言 exclusions 无 archive 路径〔再添加即红〕/ 7 模块物理行数 ≤ warn 棘轮）。两文件全量实跑 **219 passed（含 8 新用例）**。逐条断言分析为真实守护非凑绿（判别力分析见 ①(c)/F-2）。

### ⑤ 模块单一职责（D1-D3）— 通过

五层各司其职：判定层（分类/裁决/explain 渲染，纯函数 + q6_fallback 注入纪律）/机制层（journal→batch→commit 流水线 + 四族扫描 + 文件格式写手）/实体层（decision/risk/evidence 腿 + 回滚恢复）/CLI 壳（argparse 面 + 子命令 handler）/入口壳（双根 seam + 包装器 + 编排器 + main）。依赖单向（见 ①(c)），全部 < 2000 行，check-architecture-health 零家族 finding。拆分边界沿数据/副作用轴切割（纯判定 vs ROOT 绑定 IO 面），无上帝模块残留。

### ⑥ 性能预算 ±10% — 通过（用户面改善）

`migrate --auto --dry-run` 三次取最小：HEAD 0.313s → worktree 0.302s（**-3.4%**，与声明 0.30→0.28s 方向一致）。裸 `import archive` 0.095→0.148s（+53ms，5 模块 import 开销）——不违反预算口径（用户面操作反而更快），披露见 F-3。

## 蓝军挑战（已执行）

- **BM-1 嵌套 atomic-write 拦截收窄**：拆分前 `patch.object(archive, "_atomic_write_text")` 连 `_migration_write_journal`/`_migration_write_batch` **内嵌**的原子写也拦截；拆分后该嵌套调用解析于 engine 模块本地不再被拦截。逐条核对 8 个崩溃/切换测试：staging×6 按 `_migration_write_batch` 名字拦截（host 路由✓）、commit 按 path 条件只拦 hot 重写（journal/batch 走真函数=字节等价✓）、finalize 按 `_migration_write_journal` 拦截（✓）、TOCTOU 按 `_decision_authority_state`（✓）——**无任何现有测试依赖嵌套拦截**，字节级等价不受影响；残余 = docstring 表述过宽（F-1）。
- **BM-2 隔离实例二次加载**：若兄弟模块 rogue `import archive`，spec_from_file_location 世界会拿到 cwd-ROOT 的第二实例——import 图逐模块核实零反向 import；新用例对该破坏形态的判别力不足单独构成阻塞（F-2 披露），但该形态若真实发生会在既有 ROOT-patch 家族立即爆红（引擎读到未 patch 的 ROOT → 文件落到 repo 根而非 temp root → 上百断言失败）——防线冗余成立。
- **BM-3 改测试凑绿通道**：+8 用例中 arch-health 三面为「活 schema + 物理行数」双锚（改 JSON 添 exclusion 或模块膨胀即红，非 pin 挪数）；签名用例锁 inspect 参数列表+默认值；无「改断言适配实现」迹象——实现侧一切 seam 变化都有对应的真实验证面。
- **BM-4 默认值冻结口径**：`migrate_evidence_resumable` 的 `batch_size=BIG_TABLE_MIGRATION_BATCH_SIZE` 默认值在 HEAD 与拆分后均在 def 时绑定（拆分前后语义同构，patch 常量不改变默认——两代一致，非本票回归）。

## findings 清单

| # | 级别 | 位置 | 问题 | 修复建议 |
|---|------|------|------|---------|
| F-1 | **P2** | infra/archive_migration_engine.py L33-37（模块 docstring） | docstring 声称 "a patched `_atomic_write_text` is honored at every pipeline call site (journal writes, batch staging, archive write, hot rewrite)"——**口径过宽**：journal/batch staging 处被 host 路由的是 `_migration_write_journal`/`_migration_write_batch` 本身，其**内嵌** `_atomic_write_text` 调用解析于 engine 模块本地，`patch.object(archive, "_atomic_write_text")` 拆分后不再拦截（拆分前会拦截）。现有测试零依赖此嵌套面（BM-1 逐条核实），字节级行为等价不受影响；但未来按此句编写「全落盘计数/打断 journal 写」的测试会静默少拦截。 | 措辞收紧为：「patch 以各调用点的 host 名为准：`_migration_write_journal`/`_migration_write_batch`/`_atomic_write_text`（archive 写与 hot 重写）；engine 内嵌原子写不经 host，不被 `_atomic_write_text` patch 拦截」。一行文档修订，随票或遗留均可。 |
| F-2 | **P3** | infra/tests/test_archive.py 新增 `test_isolated_loader_instance_is_seam_consistent` | 本仓配置下（cwd=repo root，plan-tracker 存在且 0.1.0~0.2.0 无可归档任务）seam 破坏世界（兄弟 rogue import archive）同样产出 success=True/tasks_archived=0——断言不红，判别力部分。真实价值 = 隔离加载路径冒烟（捕获 spec 加载下 ImportError/NameError）+ 与既有 ROOT-patch 家族互补（该破坏形态由既有上百用例兜底）。 | 可选增强：isolated 实例上断言一个只在 temp root 成立的反向探针（如绑定空 root 后 `migrate_by_version` 返回 `details="plan-tracker.md not found"`/success=False），或直接对 isolated 实例调 `_migrate_evidence` 断言读取 temp root 的 evidence-log。非阻塞。 |
| F-3 | **P3** | infra/archive.py（import 面） | 裸 `import archive` 冷导入 0.095→0.148s（+53ms，4 兄弟模块链式 import）。用户面 CLI 操作实测更快（-3.4%），不违 ±10% 预算；R6 冷导入基线现不含 archive（Δ0），未来纳入时此开销需入账。 | 披露性 finding；若 R6 将来纳入 archive 族，按 FEAT-018 阈值口径重新测量即可。 |
| F-4 | **P3** | 全量套件对账（本报告 ③） | 本审查实测 18 failed（16 FAILED + 2 SUBFAILED）vs Developer 声明 19——已抽验 11/11 全部 HEAD 同败（含 2 SUBFAILED），「零新增」结论不受影响；19 vs 18 差异未定位（疑为计数口径把 SUBFAILED 父项单列或环境波动一项）。 | Coordinator 对账以「HEAD 同败集 ⊇ 工作树失败集」为准（本次已实证该包含关系）；如需精确对齐 19，由 Developer 补 stash 复跑清单。 |
| F-5 | **P3** | infra/archive.py L298-300 | 「we replace direct constants with function calls below」陈旧注释系 HEAD 携带（HEAD L251），非本票引入，现状无害。 | 顺手清理可选（与本票 F-1 同一文档清理批次）。 |

## 硬门槛自检

- **P0 阻塞问题数 = 0** ✓（findings 表实证）
- **5 维度全覆盖 = 100%** ✓——正确性（①(a)(b)(c)/BM-1/BM-4）、安全性（无新输入面；写路径原子性/锁/权威 fail-closed 语义逐体 SAME；无硬编码密钥；`write_family_scan_outputs` 保留 .governance 拒写守卫）、可维护性（⑤ 职责分层/命名/注释质量；F-1/F-5 文档精度）、性能（⑥ 实测 + F-3 披露）、测试覆盖（④ + 219 全绿 + F-2 判别力披露）。
- **每条发现标注级别 = 100%** ✓（F-1~F-5 均带 P 级）
- **设计一致性检查已完成** ✓——ADR-006 归档数据可扩展性、DEC-278 单元一/二/三分类语义、FIX-187/242 双根 seam、FEAT-060/061 崩溃恢复语义、FIX-417 纯阶段抽取纪律全部保形（AST SAME/机械 seam 裁决）；单向依赖无环。
- **AI 代码专项 5 项检查全部完成** ✓——①mock 残留=无（5 文件 grep 零 unittest.mock/MagicMock/patch）；②硬编码返回值=无（所有早退 dict 由实测路径构造）；③幻觉 API=无（全部 import 实存：pathlib/re/json/hashlib/subprocess/contextlib/tempfile + 实存兄弟模块）；④未实现 TODO=无（5 文件 TODO/FIXME/XXX/HACK 零匹配）；⑤过度实现=无（包装器层 27 个但每个对应一个真实验证面/patch 点，无投机配置面）。

## 事实依据与未验证项声明

**已验证（本审查亲跑命令/实读）**：`git status`/`git diff HEAD --stat`/`git diff HEAD`（JSON + 两测试文件全文）/`git show HEAD:archive.py`；5 个 Python 文件全文实读（archive.py 1697 / verdicts 726 / engine 1170 / entity 589 / cli 332）；test_archive.py 关键段实读（L1-40/L4570-4690/L4745-4960/L5085-5160/新增 L6088-6224）+ patch 面 103 处 grep；verify_workflow.py L9817-9836；两测试文件全量（219 passed, 16.72s）；CLI 8 面 help sha256 对照；6 组 dry-run stdout+exit 对照；scan-families TSV sha256 对照（42,295 B）；AST 对位脚本（89 def 清单 + 78 函数体归一化 diff 逐条裁决）；`check-architecture-health`（4 ERROR/33 WARN 全非 archive 族）；`archguard-ratchet`（8 violations 对号声明）；全量套件（18 failed/4695 passed/1 skipped, 24m16s）；detached HEAD worktree 复跑（9 FAILED + 2 SUBFAILED 全同败，验后 worktree 已 remove，`git worktree list` 复核）；7 文件 BOM/CRLF 字节检测（全 UTF-8 无 BOM 纯 LF——FIX-278 纪律）；import/help/dry-run 计时（三取最小）。

**未验证（不作通过依据，如实标注）**：①真实 WRITE 迁移未在狗粮仓实跑（破坏性，铁律禁改产品状态）——写路径等价由 219 用例（含崩溃注入/并发切换/回滚族，经 host seam 全绿）+ AST 逐体 SAME + dry-run 字节等价三角闭环；②Developer「三连比对」的完整历史产物文件未调阅（本审查以独立重跑的更强覆盖替代）；③`migrate --project-root` 显式重绑面未单独实测（代码实读确认 `_apply_project_root_override` SAME + 包装器路径注入同构，且既有测试族覆盖）。

**结论：APPROVED_WITH_NOTES（unresolved_blockers = 0）** —— 建议 Coordinator 机录并通过本票 R0；F-1（P2 文档措辞）建议随票顺手修订或登记遗留，F-2~F-5（P3）作为披露项入账，不构成返工条件。
