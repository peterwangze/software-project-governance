# FIX-348 R0 代码审查报告（Code Reviewer · round 0）

| 项 | 值 |
|---|---|
| 任务 | FIX-348 — Check 10 M5 record-doc 白名单扩展 `docs/requirements` |
| 审查轮次 | R0（首次审查） |
| 审查对象 | 未提交工作树 diff：`.governance/diff-FIX-348-R0.patch`（2 文件，+96/-23，96 插入 / 23 删除，净 +73——逐 hunk 复算与任务头一致） |
| 修改文件 | `skills/software-project-governance/infra/verify_workflow.py`；`skills/software-project-governance/infra/tests/test_verify_workflow.py` |
| 审查规范 | `skills/code-review/SKILL.md`（经 skill 机制加载并全程遵循）。注：调度模板给出的路径 `skills/software-project-governance/skills/code-review/SKILL.md` 不存在（Read 报 not found），实际规范位于仓库根 `skills/code-review/`——不影响审查执行，见 §8 流程注记 |
| 审查日期 | 2026-09-17 |
| 审查方式 | 纯静态只读审查（patch 逐行 + 工作树全文相关区段 + 先例注释块 + base scan 实现 + 消费面 grep）。Reviewer 无命令权限（Bash 禁止），运行时结论依据 Developer 申报并如实标注（§7） |

---

## 1. 审查输入与方法（事实源清单）

1. **patch 全文**：`.governance/diff-FIX-348-R0.patch`（209 行，逐行读取）；与工作树 `+` 侧逐段比对一致（注释块 L14532-14566、白名单 L14568、wrapper docstring L14591-14598、gate 注释 L15014-15019、测试类 L11290-11534 均与 patch `+` 侧逐字吻合）。
2. **先例与契约**：`verify_workflow.py` L14515-14616（FIX-295 注释块 + `M5_RECORD_DOC_DIRS` + `_is_m5_record_doc_path` + `check_m5_compliance_with_record_scope`）、L15013-15059（Check 10 gate 调用点与 `[EXEMPT]` 打印）。
3. **base scan 字节不变性核对**：`checks/review_domain.py` L128-345——patch 无该文件 hunk；`check_m5_compliance()`（scan 列表 L168、FIX-054 plugin-scope filter L184-189、Check 1b 启发式 L241-269）全部未触碰。
4. **live 实例**：`docs/requirements/dsh-compat-design-0.81.0.md:292`（读取实文，见 §2 正确性）。
5. **消费面扫描**：grep `M5_RECORD_DOC_DIRS` / `check_m5_compliance_with_record_scope` 全仓 `.py`——仅 verify_workflow.py（定义+调用点）、`registry.py:364`（Check 10 声明面，早已指向 wrapper，本次无需变更）、测试文件。
6. **版本冻结文档核查**：`docs/requirements/data-inventory-0.80.0.md:214` 记录 `M5_RECORD_DOC_DIRS`（`tuple[2]`、行锚 L14580-L14582）——该文档是 0.80.0 基线 commit（`213fbba0`）的冻结快照（文档头与 §「对象」行实证），不构成对本次 diff 的同步义务，判定为历史记录而非陈旧文档。

## 2. 五维度审查结论

### 2.1 正确性 — PASS（0 阻塞）

- **逻辑正确**：白名单扩展是纯数据变更（元组 +1 目录）+ 既有 wrapper 机制消费。`_is_m5_record_doc_path()`（L14571-14585）未被改动：仍是目录组件匹配（`rp == record_dir or rp.startswith(record_dir + "/")`）、反斜杠归一化、fail-closed（未枚举即扫描）。
- **live 实例验证**（静态推演，逐条件核对）：`dsh-compat-design-0.81.0.md:292` 为单物理行表格行，同行含 `(a)`/`(b)` 选项标记 + "选项" 上下文词、无 "AskUserQuestion"——满足 `review_domain.py` L252-268 的 `m5_option_list_no_auq` 触发三条件，severity=BLOCKING（L266）。base scan 扫描面含 `docs/**/*.md`（L168）且该路径不在 plugin-scope/archive/e2e 排除集（L184-189）→ base 确实 FLAG；路径 `docs/requirements/...` 现匹配白名单组件 → wrapper 移入 `record_scope_exempted` → gate `[EXEMPT]` 披露打印（L15047-15055）、不计入 `all_issues`。验收目标（该行 BLOCKING→[EXEMPT]）在机制上成立。
- **fail-closed 不弱化**（负例逐一核对）：`docs/other/spec-a.md`（非白名单 docs 子树）、`docs/release-notes.md`（裸前缀 trap）、`docs/requirements-notes.md`（新增 FIX-348 lookalike trap）、`docs/other/requirements/x.md`（"requirements" 非该处白名单前导目录）——四者仍 BLOCKING，负例期望列表的 sorted 序（`docs/other/r…` < `docs/other/s…` < `docs/release…` < `docs/requirements…`）经字符序复核正确。
- **边界条件**：`""`、精确目录名（`"docs/requirements"`）、嵌套（`sub/dir/x.md`）、反斜杠（`docs\\requirements`）形态已由组件边界单测覆盖（L11508-11525，新增 3 行用例）。
- **并发/资源**：无新共享状态、无新 I/O——不适用。

### 2.2 安全性 — PASS（0 阻塞）

- 注入面：无（纯路径字符串分类，无 shell/SQL/HTML 拼接）。
- 输入校验：路径归一化保留既有实现（`replace("\\", "/")`），fail-closed 默认（白名单外一律扫描）是本变更的安全属性核心——扩展未触碰该默认方向。
- 敏感数据：无新增密钥/token/密码。
- 权限检查：不适用（静态检查器）。OWASP 关键项扫描无命中面。

### 2.3 可维护性 — PASS（2 条 P3 建议）

- 命名一致：扩展沿用 `M5_RECORD_DOC_DIRS` 数据契约，未引入新名字。
- 注释同步完整：4 处消费点（模块注释块 FIX-348 段、fail-closed 边界 bullet、wrapper docstring、gate 调用点注释）+ 测试类 docstring + 冻结断言全部同步，无遗漏点（grep 全仓确认无残留二元组枚举）。
- 注释块结构遵循先例：FIX-295 原段逐字保留（L14516-14530），FIX-348 作为扩展段追加（L14532-14542）——与调度要求「追加 FIX-348 段」一致。
- 发现 F-1 / F-2（见 §3）。

### 2.4 性能 — PASS（0 阻塞）

- 白名单元组 +1：`_is_m5_record_doc_path` 每次 O(3) 前缀比较，非热路径（每 CLI 调用一次），无影响。
- wrapper 既有 O(n) 单遍 issue 分拣，未改动。无新循环/无批量 I/O 变化。

### 2.5 测试覆盖 — PASS（0 阻塞）

- 新增 green 侧正例 `test_gate_wrapper_exempts_requirements_design_doc_issues`（L11423-11450）：base FLAG → wrapper 豁免披露双向锁定，且断言 `type`/`severity` 精确值。
- 负例扩展：原 `docs/requirements/spec-a.md` 负例因语义失效被替换为 `docs/other/spec-a.md`（正确处置——它已入白名单），并新增 `docs/requirements-notes.md`（前缀 trap）与 `docs/other/requirements/x.md`（非白名单前导目录）。
- 组件边界单测表 +3 行（含 `docs/requirements` 精确目录、design 文件、两个 trap），冻结断言同步三目录（L11532-11534）。
- 架构锁测试（base scan 仍 FLAG record 行）保留——wrapper 前提变化时该测试先红，防护有效。
- inline-question 面与 structural 面回归（既有 4 测试）未动，覆盖 wrapper 语义"只豁免白名单路径 issue"的其余两 face。
- Fix295 类静态清点 8 个 test 方法，与 Developer 申报「Fix295 类 8 passed」一致。

## 3. 发现列表（每条已标注级别）

| ID | 级别 | 位置 | 发现（事实依据） | 建议 |
|---|---|---|---|---|
| F-1 | P3 | `verify_workflow.py:15049` | `[EXEMPT]` 运行时披露标签仍写 `FIX-295 path whitelist`——白名单现在同时承载 FIX-348 的 `docs/requirements` 扩展；上方注释（L15014）已更新为「FIX-295 / FIX-348」，标签未跟上 | 非阻塞。后续顺手把标签改为 `FIX-295/FIX-348 path whitelist`（披露溯源精确性） |
| F-2 | P3 | `verify_workflow.py:14533` | FIX-348 注释段括注写 `delivered design documents (docs/requirements/*-design-*.md)`，但白名单粒度是整目录——`docs/requirements/**` 下任意文件（不限 design 命名）均豁免。括注可能让读者低估豁免面（后文 fail-closed bullet 已如实写「moved docs/requirements/** INTO the whitelist」，部分缓解） | 非阻塞。可补半句"the whitelist stays directory-granular"消歧 |
| F-3 | P3 | `verify_workflow.py:14605-14616`（记录性发现，非本次引入） | 整目录豁免按 path 分类覆盖**所有 issue 类型**：未来若 `docs/requirements/**` 下出现 `m5_inline_question_cn` 级 BLOCKING，也将披露不计。与 `docs/release`/`docs/reviews` 既有语义完全同款（FIX-295 先例），且任务验收基准已显式接受该目录入白名单；缓解：`[EXEMPT]` 披露可见、entry 文件与 structural 面不受影响、目录粒度是 FIX-295 PATH-CLASSIFICATION 契约所强制（文件级白名单反而漂移契约） | 非阻塞。无需本次修改；登记为已接受边界，供后续 audit 引用 |

**分布：P0=0，P1=0，P2=0，P3=3（全部非阻塞建议/记录）。**

## 4. AI 代码专项 5 项检查（逐一结论）

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | 无 | diff 无 mock 代码；测试中 `patch.object(vw, "ROOT", root)` 为既有合法隔离手段（tempdir 根替换），非残留 |
| 2 | 硬编码返回值 | 无 | `M5_RECORD_DOC_DIRS` 三元组是声明的数据契约（含冻结断言看守），非 stub 返回；`_FIX348_REQUIREMENTS_ROW` 是测试 fixture（复刻 live 行 :292 的启发式触发形态：同行 `(a)`+“选项”+无 AskUserQuestion），用途明确 |
| 3 | 幻觉 API 调用 | 无 | 未新增任何 API/函数调用；引用的 `record_scope_exempted` / `record_scope_dirs` / `_is_m5_record_doc_path` 均为既有真实实现面（L14600-14615、L14571） |
| 4 | 未实现 TODO | 无 | diff 无 TODO/FIXME/占位 |
| 5 | 过度实现 | 无 | +96 行全部落在白名单元组、注释同步、测试同步三个义务面；无顺带重构、无新抽象、无配置面扩张 |

## 5. 设计一致性比对（FIX-295 wrapper 契约逐点）

| # | 契约点 | 判定 | 事实 |
|---|---|---|---|
| 1 | base `check_m5_compliance()` 字节不变 | ✓ | patch 无 `checks/review_domain.py` hunk；scan 列表（L168）与 FIX-054 plugin-scope filter（L184-189）未触碰；架构锁测试保留 |
| 2 | 路径分类语义未漂移 | ✓ | `_is_m5_record_doc_path` 未改动——目录组件匹配（exact dir 或 dir+"/"）、永不裸前缀（`docs/requirements-notes.md` trap 负例新增）、永不内容启发式、反斜杠归一化、fail-closed |
| 3 | 豁免必披露 | ✓ | wrapper `record_scope_exempted` 机制未改动；gate `[EXEMPT]` 打印沿用（L15047-15055），`record_scope_dirs` 三元组随披露输出 |
| 4 | 注释如实更新 | ✓ | 原「every docs/ subtree OUTSIDE the whitelist (e.g. docs/requirements/**)」如实改写为「FIX-348 moved docs/requirements/** INTO the whitelist … every other docs/ subtree — e.g. docs/other/** — stays scanned, and lookalike … never match」——与调度要求逐字对应 |
| 5 | 其他检查事实源不受影响 | ✓ | grep 证明 `M5_RECORD_DOC_DIRS` 仅被 wrapper 与测试消费；Checks 1x/2x 直读 `docs/requirements` 路径、不经 M5 白名单；`registry.py:364` 的 Check 10 声明面早已指向 wrapper，无需变更（projection/manifest/cross-refs 无新差异源） |
| 6 | 版本冻结文档 | ✓ | `data-inventory-0.80.0.md` 的 `tuple[2]`/行锚是 0.80.0 基线快照事实（版本化命名 + 基线 commit 锚），非活文档，不构成同步义务 |

## 6. 硬门槛裁决

| # | 门槛 | 裁决 | 依据 |
|---|---|---|---|
| 1 | P0 阻塞 = 0 | **通过** | §3 分布 P0=0 |
| 2 | 5 维度逐一有结论 | **通过** | §2.1-2.5 全部 PASS |
| 3 | 每条发现标注 P0~P3 | **通过** | §3 三条发现均带级别 |
| 4 | 设计一致性（FIX-295 契约逐点） | **通过** | §5 六点全 ✓ |
| 5 | AI 专项 5 项 | **通过** | §4 逐一结论 |
| 6 | 范围纪律 | **通过** | patch 恰 2 文件；无顺带重构；无 `.governance/` 治理记录改动（patch 文件本身系 Coordinator 生成的审查输入）；+96/-23 与任务头一致 |

## 7. 运行时结论的依据限制（如实标注）

Reviewer 无命令权限（Bash 禁止），以下为 **Developer 申报、本轮未独立复跑**的运行时结论：check-governance summary 34→33（delta=Check 10 BLOCKING 1 条消除）、`-k record` 30 passed、check-projection-sync / check-manifest-consistency / check-cross-references PASS。静态佐证与静态保留意见：

- 静态佐证：live 行 :292 满足启发式触发形态且路径入白名单 → 「BLOCKING→[EXEMPT]、0 anti-pattern BLOCKING」在机制上必然成立（§2.1）；Fix295 类 8 个 test 方法静态清点与申报一致。
- 静态保留：`-k record` 的 30 计数依赖运行时选择集（本文件内名字含 "record" 的测试静态清点为 15，其余应来自同套件其他测试模块），静态无法精确复核，按申报处理。
- evidence-log 现状：仅有 `TRIAGE-FIX-348` 机器行（L2177）；实现侧运行时证据行尚未机录。**请 Coordinator 在收到本结论后按 M7.4 以 review-record 机制机录本审查结论，并补 DEV 侧运行时证据行**——否则 Check 30 复审链与证据完整性检查将缺实现侧事实源。

## 8. 流程注记（供 Coordinator，非代码发现）

1. 调度模板引用的审查规范路径 `skills/software-project-governance/skills/code-review/SKILL.md` 不存在；实际规范位于 `skills/code-review/SKILL.md`（已加载并遵循）。后续调度模板建议修正路径。
2. 报告目录先例核实：`docs/reviews/` 下存在 `review-FIX-295-CODE-R0.md` 等既有报告，本报告命名遵循同一先例。

## 9. 审查结论

**APPROVED** — 硬门槛全部通过，零 BLOCKING 问题，可以合并。

- `unresolved_blockers=0`
- 发现分布：P0=0 / P1=0 / P2=0 / P3=3（F-1、F-2、F-3，全部非阻塞建议或记录性发现，不要求本轮修改）
- APPROVED 仅表示本审查硬门槛通过，不替代测试执行与发布审查（运行时结论依据见 §7 的申报标注）。
- 本结论为 R0 通过终态；若 diff 在合并前发生任何变更，须重新发起审查。
