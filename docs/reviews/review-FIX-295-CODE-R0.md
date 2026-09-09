# REVIEW-FIX-295-CODE-R0 — 独立代码审查报告（round 0）

| 项 | 值 |
|---|---|
| Task | FIX-295 — AUDIT-149 N6：Check 10 M5 扫描面收窄（docs/release + docs/reviews 记录类豁免+披露） |
| 审查对象 | 未提交工作树相对 HEAD `76f67bd` 的两文件变更（`git status --porcelain` 实测恰 2 文件，+321/−1） |
| 变更文件 | `skills/software-project-governance/infra/verify_workflow.py`（+104/−1）；`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+218） |
| Reviewer | code-reviewer（独立 Reviewer，非实现者） |
| 审查日期 | 2026-09-09 |
| 结论 | **APPROVED_WITH_NOTES**（unresolved_blockers=0；遗留 P3×3，均不阻塞） |

---

## 0. 硬门槛裁决

| 门槛 | 裁定 | 依据 |
|---|---|---|
| P0 阻塞问题数 = 0 | **通过（0）** | 发现清单（§3）：P0×0 / P1×0 / P2×0 / P3×3 |
| 5 维度全覆盖 | **通过（5/5）** | §2 逐维度结论 |
| 每条发现带级别与事实依据 | **通过** | §3 每条含 文件:行号 / commit / 命令输出 |
| 设计一致性检查 | **通过** | §1.1 与 FIX-294 wrapper 先例、FIX-178 收窄先例、DEC-151 口径、AUDIT-149 N6 诉求逐条比对 |
| AI 代码专项 5 项 | **通过（5/5，无命中）** | §4 |
| 事实依据红线 | **遵守** | 全部结论可复查；唯一未逐项复跑项（三 hook 实跑）已显式标注（§5.6） |

---

## 1. 第一焦点裁定：wrapper 架构 vs base 直改

### 1.1 裁定：wrapper 架构**恰当**（采纳，P3-0 级正面确认）

事实链：

1. Check 10 扫描逻辑本体在 `checks/review_domain.py::check_m5_compliance()`（L128-345），**不在本任务 triage 文件范围内**（`.governance/change-triage/FIX-295.json` files 恰为 verify_workflow.py + 测试两文件）。直改 base = 范围外修改，违反「修改纯粹性」（D4/P-v1）。
2. `git status --porcelain` 实测：工作树仅 2 文件改动，**`checks/review_domain.py` 零改动成立**（diff 范围 = `git diff HEAD --stat` 输出恰两行）。
3. FIX-294 先例（commit `76f67bd` = HEAD，commit message「两遍注入式 wrapper……审查通过终态」）对同类「base 在 checks/ 域文件、任务范围仅 verify_workflow.py」局面采用了完全相同的解法：base 字节不动 + verify_workflow.py 侧 wrapper（`check_risk_mitigation_closure_with_archive`，L14348-14419）。新代码恰置于该 wrapper 之后（L14422 起），形态对照一致：豁免披露字段（`archived_exemptions` ↔ `record_scope_exempted`）、不计入计数、fail-closed 边界文档化。
4. base 契约由 `test_base_scan_still_flags_record_doc_option_lists`（test_verify_workflow.py L10321-10352）**永久锁定**：两活体形状记录行仍必须从裸 `check_m5_compliance()` 返回 BLOCKING——若未来有人改 base 收窄扫描面，该测试立即红。架构前提被测试钉死，这是比注释更强的锁定。
5. 与 FIX-294 的合理差异：FIX-294 需两遍（注入增广后重跑判定），本问题形状只需单次 base 调用 + 结果分区（L14496-14507）——更简单且足够，无过度设计。

**结论**：架构决策成立。范围纪律、先例一致性、契约锁定三方面均无缺陷。

### 1.2 豁免边界正确性（验收标准 2）

`_is_m5_record_doc_path()`（L14463-14476）为**目录组件白名单谓词**：`rp == record_dir or rp.startswith(record_dir + "/")`，反斜杠归一。

- 前缀陷阱：`docs/release-notes.md` 不豁免（`docs/release` + `/` ≠ `docs/release-`）——单测用例显式覆盖（L10471 `"docs/release-notes.md": False`）+ 端到端负路径测试（`test_gate_wrapper_still_blocks_same_text_outside_whitelist`，同文本在 `docs/release-notes.md` 仍 BLOCKING，L10386-10409）。
- 非直接子目录陷阱：`docs/other/release/x.md` 不豁免（单测 L10473）。
- 白名单外保留扫描三路抽验：① `docs/requirements/spec-a.md` 同文本仍 BLOCKING；② `docs/release-notes.md` 同上；③ `CLAUDE.md` 内联提问指令仍 BLOCKING（`test_gate_wrapper_keeps_inline_question_face_on_entry_files`，L10411-10427）。`AGENTS.md` / `.governance/CLAUDE.md` 由谓词单测（→ False，L10474-10476）+ base 扫描列表零改动（`review_domain.py` L168 实读 + base 锁测试）共同保障。
- fail-closed：白名单外一切路径（含空串）保留扫描；`issue.get("file","")` 缺字段时归入 kept 而非豁免（L14500-14501）。

### 1.3 豁免 ≠ 静默（验收标准 3，DEC-151 口径）

- 披露块 L14917-14925：`[EXEMPT] N record-doc M5 issue(s) — FIX-295 path whitelist …(disclosed, not counted)`，逐条列 file:line:text（截 70 字符，>8 条折叠计数）。
- 不计数实证：`all_issues += len(blocking) + len(errors)`（L14898）作用于豁免后的 `m5_result["issues"]`（kept 列表）——豁免项结构上不可能进入计数。
- **不掩盖真实 FAIL**：活体复跑（B 侧）Check 10 = `[PASS]` + `[EXEMPT] 2`；若白名单外出现真违规仍走 `[BLOCKING]` 分支（负路径测试证明该分支存活）。与 Check 36 的 `[EXEMPT] 46 archived-ref exemption(s) — DEC-151 disclosure` 输出形态同族。

---

## 2. 五维度逐项结论

### 维度 1：正确性 — **通过**

- wrapper 分区逻辑（L14496-14507）：单次 base 调用 → 按 `_is_m5_record_doc_path` 二分 → kept/豁免列表；base dict 为每次调用新建，原地改写 `base["issues"]` 无共享状态风险。
- 边界：空 issues（passthrough 测试）、缺 `file` 键（`.get` 默认 `""` → kept，fail-closed）、反斜杠路径（归一 + 单测）、`rp == record_dir` 精确等值（单测 `"docs/release": True`）。
- 门调用点唯一性：grep 实测 `check_m5_compliance` 在 verify_workflow.py 中仅 3 处引用——L1223 导入、L14496（wrapper 内部）、L14892（门，已换 wrapper）。strict/lightweight 档共用 `_run_full_engine_checks` 单一调用点，**无旁路**。
- 无并发面（单线程 CLI 检查）、无资源管理面（纯计算 + 只读扫描）。

### 维度 2：安全性 — **通过**

- 无新增输入解析面：谓词仅处理引擎内部生成的 repo 相对路径（来自 `md_file.relative_to(ROOT)`）。
- 无注入/敏感数据/权限面变更。白名单是路径分类不是内容启发——不可被文件内容操纵（与 FIX-280 当年「往文档里加 AskUserQuestion 字样来消报」的内容面路径相反，本修复不依赖文档内容）。

### 维度 3：可维护性 — **通过**

- 命名表意（`M5_RECORD_DOC_DIRS` / `_is_m5_record_doc_path` / `check_m5_compliance_with_record_scope` / `record_scope_exempted`），与 FIX-294 命名族（`archived_exemptions`）对齐。
- 模块级 30 行注释块（L14422-14451）完整记载：动机、两活体实例、先例勘误（含「AUDIT-149 cites this precedent family as the "FIX-280 先例"」的显式更正）、实现选型、三条 fail-closed 边界——注释与代码一致（逐条核过）。
- wrapper 12 行主体 + 谓词 11 行，职责单一；无重复逻辑。

### 维度 4：性能 — **通过**

- base 扫描字节不变（O(files×lines) 不变）；wrapper 增量 = O(issues) 单次分区，issues 量为个位~十位级，可忽略。无重复 base 调用（对比 FIX-294 两遍属问题需要，此处不需要）。活体 check-governance 运行无感知差异（两侧均正常完成）。

### 维度 5：测试覆盖 — **通过**

- 7 用例（`Fix295Check10RecordDocScopeTests`，L10287-10498）覆盖：base 架构锁（红侧捕获）、豁免+披露（绿侧）、负路径三路（docs/requirements + 前缀陷阱 + CLAUDE.md 内联面）、结构检查保留、无豁免透传恒等、谓词 13 例边界单测（含空串/反斜杠/精确等值/两级陷阱）。
- 复跑：定向 7/7 OK（0.070s）。TDD 红态独立复现：HEAD worktree 注入新测试 → `Ran 7, FAILED (errors=6)`，6 ERROR 均为 `AttributeError: no attribute check_m5_compliance_with_record_scope / _is_m5_record_doc_path`，1 PASS = base 锁用例——与 Developer「红 6 ERROR+1 PASS」逐项一致。
- 覆盖率口径：本仓无逐文件覆盖率门禁；就变更面而言核心路径（豁免/保留/透传/边界）100% 有测试。AUDIT-149 N6 要求的「两处现报消失且指令面样例仍命中」由活体 + 负路径测试双向满足。

---

## 3. 发现清单

| # | 级别 | 位置 | 发现 | 处置建议 |
|---|---|---|---|---|
| F-1 | **P3** | `.governance/change-triage/FIX-295.json` L4（title）；`docs/release/audit-149-health-noise-0.79.0.md` §3 域 6 / §4 N6 / §6 | 「FIX-280 先例」称谓误植：git 实证 session-snapshot 收窄先例 = **FIX-178**（`2b2a5d1`「Check 29 auto-discovery excludes session-snapshot」）；**FIX-280**（`a7fd5b3`）实为 docs 内容面修复（version-plan 两文档加 AskUserQuestion 引用消报）。Developer 已在代码注释与任务书中勘误，但 triage title 与 AUDIT-149 原文未改 | 非本任务范围（治理记录/已入账文档）；建议后续触碰这些文件时附一行勘误注记（快速通道可承载），防止未来考古再引用错先例 |
| F-2 | **P3** | verify_workflow.py L14922-14925 | `[EXEMPT]` 披露逐条上限 8 条，超出仅计数。当前活体 2 条远低于阈值；若未来记录类豁免批量增长（如 FIX-294 后 Check 36 曾到 46 条），明细需翻查源文件 | 观察项，无需改动；若增长可仿 Check 36 披露加来源溯源字段 |
| F-3 | **P3** | `project/e2e-test-project/`（e2e 镜像，本任务未触碰） | e2e 镜像中的 verify_workflow.py 副本未随本改动同步（strict 档 function_size WARN 引用的仍是镜像旧副本）——与 FIX-294 同样不触碰镜像，镜像同步属发布期任务 | 发布（0.79.0）收尾批次随版本同步，无需本任务处理 |

无 P0 / P1 / P2 发现。

---

## 4. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 生产代码零 mock/patch；测试用 `patch.object(vw, "ROOT", …)` 全部在 `with` 上下文内自动还原（7 用例逐一核过）；tempdir 全部 `with tempfile.TemporaryDirectory()` 自清理 |
| 2 | 硬编码返回值 | **无** | wrapper 结果完全派生自 base 实跑结果（L14496-14507）；无伪造 issue 列表/常量返回 |
| 3 | 幻觉 API 调用 | **无** | 仅调用实存符号：`check_m5_compliance`（L1223 已导入，review_domain.py L128 定义）、dict/list 原生操作；7/7 测试 + 全量 795 套件通过证明无未定义引用 |
| 4 | 未实现 TODO | **无** | diff 内无 TODO/FIXME/占位符/NotImplemented |
| 5 | 过度实现 | **无** | 最小面：1 常量 + 1 谓词（11 行）+ 1 wrapper（12 行主体）+ 1 调用点替换 + 1 披露块；无多余配置面/参数化/未来预留（白名单仅 2 目录 = 活体所需，未预防性扩展 audit 归档族——fail-closed 方向正确） |

---

## 5. 事实依据汇总（审查者独立复跑记录）

命令均从仓库根执行，只读或 effect-safe（临时 worktree 验证后已清理：`git worktree list` 仅余主树）。

### 5.1 base 零改动（验收 1）
`git status --porcelain` → 恰 ` M skills/.../tests/test_verify_workflow.py` + ` M skills/.../verify_workflow.py` 两行；`git diff HEAD --stat` → 2 files changed, +321/−1。`checks/review_domain.py` 不在改动集。

### 5.2 事实修正核验（验收 4）
- `git show --stat 2b2a5d1` → 「FIX-178: Check 29 auto-discovery excludes session-snapshot (false-positive fix)」，改动 = verify_workflow.py(+32/−9) + tests(+73)——**收窄先例确为 FIX-178**。
- `git show --stat a7fd5b3` → 「FIX-280: M5 基线小修——version-plan 裁决表样式 m5_option_list_no_auq 豁免注记（两文档 §5.1 加 AskUserQuestion 引用……）」，改动 = `docs/release/version-plan-0.77.0.md` + `0.78.0.md`——**docs 内容面修复**，Developer 勘误属实（见 F-1）。
- `review_domain.py` L168 实读：扫描面 = `["AGENTS.md", "CLAUDE.md", ".governance/CLAUDE.md", "docs/**/*.md"]`；L180-189 实读：FIX-054 过滤器经 `_is_plugin_path` 排除 skills/** + archive + e2e——**skills/** 自 FIX-054 起在扫描面外的陈述属实**，故负路径锁定改用仍扫面（docs/requirements、docs/release-notes.md、CLAUDE.md）的设计正确。

### 5.3 回归事实复核（验收 6）
- **39 → 37 精确 −2**：A 侧（HEAD worktree + `.governance` 副本）`check-governance` → `[BLOCKING] 2 M5 anti-pattern(s)` + `Result: ISSUES FOUND — 39 issue(s)`；B 侧（工作树）→ `[PASS]` + `[EXEMPT] 2 record-doc M5 issue(s) — … docs/release, docs/reviews …`（两活体 file:line 披露与 AUDIT-149 §3 域 6 定位一致）+ `Result: ISSUES FOUND — 37 issue(s)`。
- **unittest A/B**：A 侧 `Ran 788 tests … FAILED (failures=1)`；B 侧 `Ran 795 tests … FAILED (failures=1)`；两侧唯一失败同为 `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`（既有定性环境敏感例，subprocess 超时类）——**失败集逐项相同，+7 = 新测试数**。
- **strict 档**：`check-governance --level strict` → `Result: ISSUES FOUND — 37 issue(s)`；Check 10 PASS + [EXEMPT] 2；输出中与本改动相关的仅既有 advisory（e2e 镜像 function_size WARN、Check 29 既有 1 条 M5.4b WARN）——**无新增 FAIL/WARN 指向本改动**。
- **TDD 红**：§2 维度 5 所述 `Ran 7, FAILED (errors=6)` 复现。

### 5.4 三 gate（Developer 报告项）
`.git/hooks/` 实测 `pre-commit` / `commit-msg` / `post-commit` 三脚本在位（机制存在性已核）。**未逐 hook 实跑**（需真实 commit 上下文）——标「未验证（机制在位 + 引擎级等价检查 37 无新增已独立复跑）」。

### 5.5 规格符合性
- AUDIT-149 §4 N6 诉求：两处现报消失 ✓（37 + PASS）、指令面样例仍命中 ✓（负路径测试 + CLAUDE.md 面测试）、保留 docs/requirements 等指导类子目录 ✓（白名单仅 release/reviews 两目录，比 N6 甲案标题「限定为 agent 指令面」更保守——取 N6 风险缓解条款的 fail-closed 方向，豁免面最小化，正确取舍）。
- DEC-151 口径：豁免 + 披露 + 不计入 ✓（§1.3）。
- FIX-294 先例：wrapper + 披露字段 + fail-closed 注释 ✓（§1.1）。

### 5.6 与先例审报告交叉
`docs/reviews/review-FIX-294-CODE-R0.md` 存在于 HEAD（该 commit stat 第 4 行）——「审查通过终态」先例陈述属实。

---

## 6. 结论

**APPROVED_WITH_NOTES**

- 硬门槛全部通过（§0）；P0 = 0。
- 架构裁定：wrapper vs base——**wrapper 恰当**（范围纪律 + FIX-294 先例一致 + base 契约测试锁定）。
- 遗留：F-1/F-2/F-3（P3×3，均有处置去向，不阻塞合并）。

**unresolved_blockers=0**
