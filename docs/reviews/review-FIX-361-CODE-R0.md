# Review Report — FIX-361 独立代码审查（Round 0）— 静态版本钉机检面

- **任务**: FIX-361 — DEC-213③ M-1 口径盲区规则化：`scan_static_version_pins()` WARN-only 子检查
- **审查轮次**: R0（首轮）
- **Reviewer**: Code Reviewer Agent（独立，未参与开发）
- **审查对象（恰 2 文件）**:
  - `skills/software-project-governance/infra/checks/version.py`（git diff 实测 **+165/-0**，纯追加，与申报一致）
  - `skills/software-project-governance/infra/tests/test_static_version_pins.py`（新建，实测 **25 个测试方法**：3+1+2+7+5+4+3=25）
- **范围纪律核对**: `git status --porcelain` 显示工作树另有 review_domain.py / test_review_closure_legacy.py / manifest.json / version-projections.json / e2e governance-status.md 修改——按任务书均属并行任务，本次未审查、未触碰。本任务改动面与申报一致，无越界写（`.governance/` 零修改）。
- **日期**: 2026-09-24（审查执行日）

---

## 总结论

## **APPROVED_WITH_NOTES** — `unresolved_blockers=0`

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **0** |
| P3 讨论/建议 | **6**（F-01~F-06，全部不阻塞） |

**判定理由**: 检测语义边界健壮（逐项验证见下）、豁免注册表防腐闭环成立（token 锚定 + 负例控制 12 命中与 ledger 逐行对齐）、WARN-only 姿态经 4 消费点源码核验向后兼容、正例 verbatim 缺陷行经 `7a865b7^` 逐字符溯源为真、2 项 pre-existing FAIL 在 HEAD 基线独立复现归因成立。6 条 P3 均为边缘盲区记录与措辞改进，不影响合并。

---

## 审查重点逐项结论

### ① 检测语义边界（AST docstring / lookaround）

**结论：通过（附 F-01 边缘记录）**

- **lookaround 正则** `(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])`（version.py:175）逐 case 验证：
  - `"10.83.0"` → 整体匹配为 `10.83.0`（lookbehind 挡住 `0.83.0` 尾部粘连）✓
  - `"0.830.0"` / `"0.83.05"` → 整体匹配为异版 token，不等于 active → 不误报 ✓（测试 `test_token_boundaries` 实证）
  - `"v0.83.0"` → 前缀 `v` 非 `[\d.]` → 命中 ✓（测试实证 line 4 hit）
  - 前缀防误报（`0.83.00` 不产生 `0.83.0` 假命中）由 lookahead 保证 ✓
- **AST docstring 判定**（`_annotation_string_lines`, version.py:204-228）健壮性推演：
  - 仅 Module/ClassDef/FunctionDef/AsyncFunctionDef 的 `body[0]` 裸字符串常量记为 docstring——符合 CPython"首语句才是 docstring"语义；`if` 分支体内的裸字符串、body[0] 之后的裸字符串均为可执行表达式 → **照扫**（保守方向，宁多勿漏）✓
  - 隐式拼接 docstring 含 f-string（JoinedStr）时不被识别为 docstring → 照扫：产生**假阳性方向**的偏差（多扫不漏扫），对 WARN-only 咨询面无害
  - 多行字符串 inner 行（`lineno+1..end`）标记与 docstring 集合独立：docstring 内 `#` 内容行被 docstring 面跳过（注释=注记，正确）；非 docstring 多行字符串的 `#` 内容行**不被注释规则吞掉**（fixture markdown 照扫）——`test_multiline_string_hash_line_is_scanned` 实证 line 3/5 双命中 ✓
- **降级路径**: parse 失败 → WARN + 跳过该文件行扫（fail-open 咨询面，`test_unparsable_file_warns_and_scan_continues` 实证不阻断同批其它文件）✓

### ② 豁免注册表防腐化机制

**结论：通过（附 F-02/F-03/F-04 记录）**

- 12 条 `(line, token, reason)` 行全部锚定真实树核对（116/120/121/122/212/216/217 为 fixture task-table；319/322/326/331/336 为 migration_flag 版本对输入/回显断言）——逐行 token 在位 ✓
- **抑制精确性**: 负例控制 `exemptions={}` 复现恰好 12 命中且行号与 ledger 完全一致；默认注册表下 0 pins / 0 stale / 0 other → 抑制面既不缺口也不过宽 ✓
- **token 锚定闭环**: 行内容漂移/删除 → stale 告警（`test_drifted_line_surfaces_as_stale_exemption` / `test_removed_token_...` / `test_missing_file_...` 三态实证）；未来 bump 后旧行休眠（不抑制、暂不告警），一旦行内容更新即触发 stale 重审——闭环成立，不会腐化为 blanket-allow ✓
- `RealTreeContractTests.test_ledger_rows_are_live_on_current_tree` 把 ledger 活性固化为回归测试（reason 非空 + 行号 token 在位双断言）✓

### ③ WARN-only 姿态与 4 消费点向后兼容

**结论：通过**

4 个消费点源码逐一核验，全部以 `startswith("[WARN]")` 分离、WARN 不进入失败通道：

| # | 消费点 | 位置（verify_workflow.py） | 分离方式 |
|---|--------|---------------------------|----------|
| 1 | check-release 聚合 | L7078-7085 | `version_failures = [i for i in ... if not startswith("[WARN]")]`，WARN 入 `details.warnings` |
| 2 | cmd_verify | L10325-10340 | `fail_items` / `warn_items` 双列表 |
| 3 | check-governance Check 24 | L15707-15720 | `vc_fail` 计数、`vc_warn` 以 `[INFO]` 打印 |
| 4 | cmd_check_version_consistency | L21421-21440 | 仅 `fail_items` 触发 `sys.exit(1)`；WARN 仅打印 → exit 0 |

- 结构兼容：diff 为纯追加（+165/-0），`check_version_consistency` 既有 FAIL 语义零改动；`scan_static_version_pins` 输出恒为 `[WARN]` 前缀（`test_all_findings_are_warn_prefixed` + `test_check_version_consistency_appends_static_pin_face` 双实证）✓
- 附：`test_check_version_consistency_appends_static_pin_face` 断言只覆盖 static-pin 行的 WARN 前缀，不断言整个 issues 列表全 WARN——正确边界（其它 face 本就有 FAIL）✓

### ④ 正例 verbatim 缺陷行复现价值

**结论：通过——溯源为真，复现价值成立**

`git show 7a865b7^` 逐字符核对：

| 测试常量 | 申报出处 | 溯源结果 |
|----------|----------|----------|
| `_FIX352_LINE` = `self.assertIn("@bootstrap-version: 0.83.0", updated)` | 7a865b7^ test_entry_projection.py:450 | **逐字符一致** ✓ |
| `_FIX353_HEAD` = `- **工作流版本**: 0.83.0` | 7a865b7^ test_bootstrap_aggregate.py:54 | **逐字符一致** ✓ |
| `_FIX353_ASSERT` = `self.assertEqual(project["workflow_version"], "0.83.0")` | 7a865b7^ test_bootstrap_aggregate.py:333 | **逐字符一致** ✓ |

注入 `active="0.83.0"`（bump 时代）使正例保真且测试文件**自身在自扫描下恒净**（全文件无可执行/数据行携带 0.84.0；实测真实树扫描 0 命中佐证）——测试不会在下一次 bump 时自噬 ✓

### ⑤ 8 项 pre-existing FAIL 归因抽查（抽 2 项 HEAD 基线复跑）

**结论：通过（归因成立）**

方法：`git archive HEAD` 抽取至 `%TEMP%\fix361-head-baseline`（889 tracked 文件；基线 version.py 中 `scan_static_version_pins` 出现 0 次 = 确认 pre-fix 代码），**复制当前 `.governance` 进基线保持数据面一致**（`.governance` 未被 git 跟踪——此步为可比性关键）。

| 抽查项 | HEAD 基线 | 当前树 | 归因裁决 |
|--------|-----------|--------|----------|
| check-release | exit=1，**Traceback `KeyError: 'source_version'`**（与申报"check-release 基线 KeyError"精确吻合） | exit=1，失败签名结构化（hot fact-source / execution gates / governance health / unit tests / loop runtime claim gate），KeyError 0 次 | **FAIL 状态 pre-existing** ✓。签名差异（KeyError 消失）归因并行任务对 manifest.json/version-projections.json 的工作树修改——出范围，且与 FIX-361 无关（见下方归因加强论证） |
| check-loop-runtime-claims | exit=1，`verdict: BLOCKED` | exit=1，`verdict: BLOCKED`（签名一致） | **pre-existing** ✓——与全量 5F"loop-runtime-claims 簇"申报同族互证 |

**归因加强论证（覆盖全部 FAIL，不止抽查 2 项）**: 本树默认注册表下 `scan_static_version_pins(root)` 返回恰好 `[]`（0 pins / 0 stale）→ `check_version_consistency` 输出与 pre-FIX-361 **逐字节一致** → 4 消费点收到的输入零变化 → 任何子命令 FAIL 在构造上不可能由本变更引入或修复。Review-father 独立巡检 69 只读子命令：59 ok + 6 真实 FAIL（check-sequential-ids / check-structural-validity / dsh-doctor / check-loop-runtime-claims / check-release / release-ledger）+ 4 个无效命令名 usage error——与申报 71→63+8 的集合不必逐项一致（命令清单不同），方向一致：FAIL 均为环境/.governance 数据/并行任务面，与 M-1 机检面无关。

### ⑥ 范围纪律 + AI 专项

**范围纪律**: 通过——version.py 纯追加 +165/-0；新测试文件 1 个；`.governance/` 零写；无冻结文件（test_verify_workflow.py）触碰；报告写入 docs/reviews/ 符合任务授权。

**AI 专项 5 项（全部通过）**:

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | 无 | 测试用 tempfile 真实文件系统 + 真实模块函数，全文件无 mock/patch |
| 2 | 硬编码返回值 | 无 | 产品侧无硬编码判定结果；测试侧 `0.83.0` 字面量为**有据注入**（历史 verbatim + 文档化理由），非偷懒硬编码 |
| 3 | 幻觉 API | 无 | WARN 指引引用的 `resolve_entry.read_active_version()` 真实存在（resolve_entry.py:82）；`@@ACTIVE_VERSION@@` token 为 test_bootstrap_aggregate.py:62 实际动态化模式 |
| 4 | 未实现 TODO | 无 | 全文件无 TODO/FIXME/占位实现 |
| 5 | 过度实现 | 无 | `tests_dir`/`exemptions` 参数均有测试消费；无投机抽象；扫描器保持单函数最小语义 |

---

## 五维度逐项结论（硬门槛）

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | **通过** | 正则边界逐 case 验证；AST 判定语义与 CPython docstring 规则一致；降级/缺目录/无版本三 fail-open 面均有测试；ledger 抑制与 stale 审计逻辑闭环 |
| 安全性 | **通过** | 无注入面（仅读取仓库自身 tests 目录，无 subprocess/eval）；异常捕获窄化（OSError/UnicodeError/SyntaxError）；显式 UTF-8 读取；无密钥 |
| 可维护性 | **通过（附 F-05/F-06）** | 扫描逻辑独立成函数（未继续膨胀 `check_version_consistency` 主干，但该函数长度趋势延续 review-FIX-285 F-01 的 P2 记录，现约 65 行）；注释块把判定语义/姿态/豁免机制写成可审计规范 |
| 性能 | **通过** | 单遍 rglob + 每文件一次 ast.parse；新测试套件全量 1.58s（含真实树扫描）；无 N+1 |
| 测试覆盖 | **通过** | 25 测试覆盖：双正例缺陷形、派生负例、注释/docstring/模块 docstring/多行 `#` 内容、token 边界、行内注释、豁免抑制/错 token/漂移/删除/缺文件、姿态 4 态、真实树 3 契约——核心路径+边界+错误路径全覆盖 |

**硬门槛裁决**: P0=0 ✓｜5 维度全覆盖 ✓｜每条发现有级别标注 ✓｜设计一致性（与 DEC-213③ 决策原文比对：本实现即决策中"新增机检面"候选的落地，WARN-only 与"0.85.0+ 候选"保守姿态一致）✓｜AI 专项 5 项 ✓

---

## Findings 清单（全部非阻塞）

### F-01【P3】正则对非标准形态 semver 的召回盲区
`_SEMVER_TOKEN_RE` 对 4 段式（`0.84.0.1`）与尾点式（`0.84.0.`）不产生 token → 不告警。二者均非合法 semver 且从未在本仓缺陷史出现；lookaround 以牺牲该边缘召回换取零误报，对 WARN-only 咨询面可接受。**建议**: 维持现状；若未来出现 4 段版本方案再扩展。

### F-02【P3】豁免 ledger 的版本漂移休眠行无显式清理机制
bump 后旧行（token=旧 active）休眠：不抑制、不告警、无清理义务，ledger 单调增长。token 锚定保证其无害（内容一变即触发 stale 重审），但缺一个"bump 后 ledger 巡检"的显式提醒面。**建议**: 可在版本 bump 流程文档中加一句"review STATIC_PIN_EXEMPTIONS"，或在 stale 审计中对 `token != active_version` 的休眠行给 advisory 计数（不阻塞）。

### F-03【P3】stale 审计对扫描目录外的不可读 registry 目标静默跳过
`except (OSError, UnicodeError): continue` 的注释声称"已由上方扫描覆盖"，但该覆盖仅对 scan dir 内文件成立；registry key 若指向目录外文件且不可读则完全静默。当前 12 行全部在 scan dir 内 = 纯潜在缺口。**建议**: registry key 约定已隐含约束；可加一行注释明确前提。

### F-04【P3】`_REASON_MIGRATION_PAIR` 措辞对 326 行字面不精确
理由文本"neither operand is the real active version"对 `migration_flag("0.84.0", "0.84.0")`（两操作数数值上均等于当前 active）字面为假；真实意图（合成场景数据、相对比较语义）清楚。**建议**: 改为"operands are synthetic scenario data, not references to the release"类措辞，避免未来审计误读。

### F-05【P3】`cmd_check_version_consistency` 披露串未提及新扫描面
打印串"Files checked: 13 ... + bootstrap markers"（L21425）未列入 static-pin face——披露完整性小缺口（WARN 输出本身会打印命中，无功能影响）。**建议**: 顺手补一句"+ static pin scan (infra/tests)"。

### F-06【P3】测试 harness tempfile 无清理
`_scan` 每次 `tempfile.mkdtemp` 不清理，单次运行遗留 ~20 个临时目录。业界常态、无断言影响。**建议**: 可用 `addClassCleanup` 收口，非必需。

---

## 独立复验记录（3 项）

| # | 复验项 | 命令 | 申报 | 实测 | 裁决 |
|---|--------|------|------|------|------|
| 1 | 新测试套件 | `python -m pytest .../test_static_version_pins.py -q` | 25 passed | **25 passed in 1.58s** | ✓ 一致 |
| 2 | 接线 + 负例控制 | `verify_workflow.py check-version-consistency`；`scan_static_version_pins(root)` 默认 vs `exemptions={}` | exit 0；负例复现 12 命中 | **exit=0 / PASSED**；默认 0 pins + 0 stale；负例**恰好 12 命中且行号与 ledger 逐行对齐** | ✓ 一致 |
| 3 | pre-existing 归因抽查 | `git archive HEAD` → 临时基线（+.governance 数据对齐）→ check-release / check-loop-runtime-claims 双树复跑 | 8 FAIL 全部 HEAD 复现，含 check-release KeyError | 抽查 2 项 **均 HEAD exit=1 复现**（check-release 含 `KeyError: 'source_version'`；loop-runtime-claims BLOCKED） | ✓ 归因成立 |

未独立复跑项（如实披露）: 全量测试套件 3489P/5F 未重跑（3 项复验预算已用满）；以 loop-runtime-claims 命令级 BLOCKED@HEAD + 零输出面论证（F 无关性）作佐证。申报"71 只读子命令 63+8"未逐项复制（Reviewer 巡检为 69 命令自选清单，得 59 ok + 6 真实 FAIL + 4 无效名），方向一致。

---

## 边缘问题（移交 Coordinator 参考）

1. **check-release 失败签名漂移**: 当前树 KeyError 消失、失败结构化——归因并行任务（manifest.json / version-projections.json 工作树修改），建议 Coordinator 在并行任务审查链中覆盖，勿遗漏。
2. **基线可比性前提**: `.governance` 未被 git 跟踪，任何 HEAD worktree 复现都必须显式复制 `.governance` 才能与开发环境同口径——Developer 申报的"worktree 复现"方法学成立与否取决于此；本次 Review 已按此方法独立构建基线并复现。
3. **下一次 bump 的预期行为**: 0.84.0→0.85.0 时，fixture 表若仍为 `0.84.0` 字面量则无告警（休眠）；若被开发者更新为 `0.85.0` 字面量则立即 WARN + 旧 ledger 行 stale 告警——双重信号是设计预期，发布清单可提前写明，避免发布期误判为新增缺陷。

---

## 审查依据（事实源清单）

- `git diff` version.py（+165/-0 实测）；`git status --porcelain`（范围纪律）
- `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（已加载，按其执行协议）
- version.py:139-303（新增段全文逐行读）；test_static_version_pins.py:1-349（全文逐行读）
- verify_workflow.py L7078/10325/15707/21421（4 消费点）、L21440（exit 语义）
- `7a865b7^` 三处 verbatim 溯源；decision-log DEC-213③（L154）语义对齐
- 复验命令输出（pytest 25P / exit 0 / 12 命中负例 / HEAD 基线双命令复现）
- 前轮相关审查: docs/reviews/review-FIX-285-CODE-R0.md（F-01 函数长度趋势引用）
