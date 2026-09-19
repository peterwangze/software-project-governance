# review-FIX-357-CODE-R0 — 独立代码审查报告（round 0）

- **Task**: FIX-357（P1，target 0.85.0）— C-01 豁免行因果断言措辞按来源分流
- **Reviewer**: Code Reviewer Agent（独立审查，未参与实现）
- **日期**: 2026-09-19
- **审查范围（恰 2 文件，工作树未提交 diff）**:
  - `skills/software-project-governance/infra/checks/review_domain.py`（stat 75 = +71/−4）
  - `skills/software-project-governance/infra/tests/test_review_closure_legacy.py`（+204/−0）
- **前像 blob 锚（git diff index 行实证）**: `index e681bfa..f98d547`（review_domain.py）、`index 610c2ef..1c8fc99`（test 文件）——与 Developer 申报开工锚 e681bfa/610c2ef **一致** → review-FIX-355 binding note 5 的重跑条款未触发，V-1~V-16 无需重跑（此项由 Reviewer 从 diff index 行独立核对，非转述申报）。
- **会话状态披露（如实）**: 本审查会话在动态复验阶段被中断。静态审查（diff 逐行审读 + 消费面核查 + 不变量验证）**已全部完成**；动态复验（pytest / 红相影子树 / check-governance A/B）**未及执行**，按 Coordinator 收尾指令逐项标注「未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）」并给出静态论证基础。Coordinator 保留最终裁决权。

---

## 1. 修复语义核对（对照 review-FIX-355-CODE-R0 C-01 与 DEC-214②）

- C-01 原判定：4 个终态豁免门（V2 L-A 前导缺口 / V2 historical-shape / V5 legacy-key / V5 historical-shape）均以 `task_id in closed` 触发，但 `closed` 合并两类因果来源（DEC-214②：`closed = completed ∪ (archived − live_active)` 的归档依据 vs EVD-892 活体行终态恢复），共用同一措辞模板 → 披露失真（源判 P1）。
- 本 diff 交付：来源判别函数 `_terminal_exemption_source`（review_domain.py L2059-2071，判据 `task_id in closed and task_id not in completed` → "archive"，否则 "live"）+ 模板映射 `_terminal_exemption_cause_clause`（L2074-2082，字典 `_TERMINAL_EXEMPTION_SOURCE_CLAUSE` L2049-2056）+ 4 门各注入 `cause = _terminal_exemption_cause_clause(task_id, closed, completed)` 并把 reason 尾部 `; downgraded` 改为 `; {cause}; downgraded`（L2239/2246、L2265/2273、L2437/2446、L2467/2478）。
- 判定逻辑零改动核验：见 §3.3。与 DEC-214② 判定语义一致性：见 §3.1。

## 2. 独立复验结果表

### 2.1 已真实执行（Reviewer 本会话，exit code 0）

| # | 命令 / 操作 | 结果摘要 |
|---|-------------|---------|
| V1 | `git status --porcelain` | 工作树共 5 个修改文件：本任务 2 文件 + `infra/checks/version.py`、`infra/tests/test_hooks.py`、`infra/tests/test_pre_commit_review_evidence.py`（并行任务范围，出本审查范围）——**范围纪律事实基线** |
| V2 | `git diff --stat`（限定 2 文件） | `review_domain.py | 75 ++++…`、`test_review_closure_legacy.py | 204 ++++…`；合计 `2 files changed, 275 insertions(+), 4 deletions(-)`——与申报规模一致（review_domain 实为 +71/−4，stat 计数 75 = ins+del；4 处删除均为 reason 尾行 `; downgraded` 改写） |
| V3 | `git diff`（两文件全文 hunks 逐行审读） | index 前像 = e681bfa/610c2ef（锚核对）；全部新增/修改面 = 模块注释块 + 2 函数 + 1 字典 + 4 门 cause 注入；4 处删除均为措辞尾行 |
| V4 | `read` review_domain.py L2084-2203（函数签名 + closed/completed 派生块） | 派生路径全貌取证（§3.1/§3.2 依据） |
| V5 | `grep 'closed'`（review_domain.py） | `in closed` 恰 4 处门触发（L2235/L2260/L2434/L2459）+ 派生处（L2120/L2156/L2158/L2163）；无其他消费者 |
| V6 | `grep 'closure basis'`（全插件） | 仅新增代码与新增测试命中——无既有消费者 |
| V7 | `grep 'downgraded\|reason'`（infra/hooks + infra/*.py 消费模式） | commit-msg hook 零匹配（唯一命中为无关迁移指南文案）；Check 30 豁免行 reason 的下游消费均为透传打印（verify_workflow.py L16220/16224/16251），无前缀/子串解析 |
| V8 | `read` verify_workflow.py L161-235（FIX300DualCaliberAgreementTests） | 该类走 Check 31 identity attestation / loop-runtime-claims 双口径（`vw._run_identity_attestation_fixture_only` / `vw.cmd_check_loop_runtime_claims`）——与 Check 30 豁免措辞面零代码路径交集（§2.2 第 4 行论证基础） |

### 2.2 未独立复验（按 Coordinator 收尾指令标注；各附静态论证基础）

| # | Developer 申报项 | 复核方式与结论 |
|---|------------------|----------------|
| D1 | pytest test_review_closure_legacy.py → 54 passed（44 既有 + 10 新增） | **未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）**。静态佐证：10 用例调用的 `rd._terminal_exemption_source` / `rd._terminal_exemption_cause_clause` 与 `closure basis` 断言面均只依赖本 diff 新增面（§3.4 红相结构论证）；测试文件导入机制 `__file__` 相对自包含（L38-44），无跨树依赖 |
| D2 | verify_workflow 全子命令 PASSED；cross-refs/manifest PASS（784/884） | **未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）**。本 diff 为 Check 30 豁免行纯文案分支，不触 cross-refs/manifest 计数面（V6/V7 消费面核查佐证） |
| D3 | check-governance 冻结 A/B：31=31 输出逐字节一致 → 零新增 issue | **未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）**。静态佐证：`closed`/`completed` 派生、门 if 条件、violations/warnings 集合构成零改动（§3.3）→ issue 集合在构造上不可能新增；变更仅在既有豁免 WARN 行 reason 文本内插入分句 |
| D4 | 分流前后对照：仅 FIX-246/REL-078 两行 V2 豁免行新增来源分句，其余 28 行逐字节一致 | **未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）**。静态佐证同 D3：仅 2 个 live 数据中的 V2 L-A 豁免行（归档来源）+0 个 live 来源行在现网数据触发；措辞注入只影响触发豁免门的行 |
| D5 | FIX300DualCaliber 3 failed 与本 diff 无关 | **未独立复验（依据：Developer A/B 同输出佐证 + 构造无交集论证）**——本项静态论证最强：(a) `test_verify_workflow.py` 不在本 diff 两文件内（V1 实证）；(b) 失败类走 Check 31 identity/loop-runtime-claims 面（V8 实证），与 Check 30 `check_review_closure` 无调用关系；(c) diff 面为 Check 30 reason 常量模板注入，不触 identity sub-phase / HOST_PROJECT_ROOT 解析；(d) 该类 docstring 自述对 host-root 解析与真实 Git index 敏感（环境敏感型用例，L181-183）——失败更可能与运行环境 cwd 相关 |

## 3. 审查重点逐项结论

### 3.1 来源判别正确性 — **通过**

- **判据与 DEC-214② 合并语义一致性**：live 路径唯一合并点 L2158 `closed = completed | (_archived_completed_task_ids() - live_active)` ⇒ `closed − completed ⊆ archived − live_active`，即任何「在 closed 不在 completed」的 id **必然**经归档侧进入 → "archive" 归因恒真。反向：id ∈ completed ⇒ 活体行在场且断言终态 → "live" 归因恒真（即使该 id 同时在归档索引中，声称活体行依据仍属实——不构成假披露）。
- **fail-safe 方向安全（fail-closed 而非 fail-open）**：三条回退路径全部 `closed = completed`——fixture 路径（L2117-2120，completed 为调用方显式参数，注释明示永不并入归档数据）、tracker 不可读（L2152-2156，live_active is None）、异常路径（L2160-2163）。回退后 closed == completed ⇒ 分类器对所有 id 返回 "live" ⇒ **无归档贡献即不可能声称归档依据**，方向正确。
- **completed/closed 在 4 门作用域可得性**：二者均在 `check_review_closure` 函数体前部定义（fixture L2117/L2120；live L2123 + L2156-2163），4 门（L2235/L2260/L2434/L2459）同处其后的 `for task_id, seq in sorted(sequences.items())` 循环内 → 作用域成立，无 NameError 风险。

### 3.2 措辞注入的输出面影响 — **通过**

- 注入位置：`…pattern); {cause}; downgraded`——在既有分号分Clause序列中插入，格式与既有多分句风格一致；模板常量以 `; ` 结尾衔接。
- 下游消费者核查（V6/V7 实证）：`closure basis` 子串全插件仅新增代码/测试持有；commit-msg hook 无对这些行的任何匹配；Check 30c（`check_review_machine_provenance`，FIX-260）直读证据行判机器来源，不消费 Check 30 豁免行 reason；verify_workflow 对 Check 30 warnings 为透传打印，无前缀/子串解析 → **注入对下游解析面安全**。
- `DEC-214②` 模板含带圈数字 ②：既有 reason 已含中文/Unicode 字符，无新增编码类别。

### 3.3 判定逻辑零改动核验 — **通过**

4 门 if 条件在 diff 中均为上下文行（未改动），逐字比对：
- L2233-2235 `if _missing_rounds_are_leading(missing_rounds, rounds) and task_id in closed:` — 未变
- L2260-2262 `if task_id in closed and all((rounds[r].get("source_format") == "historical") for r in rounds):` — 未变
- L2429-2434 V5 legacy-key 门（`blocker_status == "missing" and legacy_keys and not legacy_nonzero and not legacy_unparsed and task_id in closed`）— 未变
- L2459-2463 V5 historical-shape 门（`task_id in closed and … (blocker_status == "missing" or _blocker_evidence_provably_zero(blocker_evidence))`）— 未变

4 处删除行均为 reason 尾行措辞（`; downgraded` → `; {cause}; downgraded`）；`closed` 派生（L2147-2163）、V1 破链面（仍消费活体 `completed`，L2701 注释在案）、豁免资格集合构成零改动。`in closed` 全文件恰 4 门（V5 实证），与 DEC-214②「closed 只作用终态豁免门」口径一致。FIX-358 范围（L2514/L2559 谓词面）不在任何 diff hunk 中 → 只读未改，实证确认。

### 3.4 测试质量 — **通过（附未独立复验标注）**

- **红相存在性（结构论证）**：用例 1-5 调用 `rd._terminal_exemption_source`/`_terminal_exemption_cause_clause`——修复前函数不存在 → AttributeError FAIL；用例 6-10 断言 `assertIn("closure basis: …")`——修复前 reason 无任何 closure basis 分句 → assertIn FAIL。10 用例在分流前**必然全红**，红相存在性在构造上成立；经验复跑未执行（见 D1 标注）。
- **行为正例装置保真度（静态评估）**：`_live_run` 走 temp `.governance` 真实 I/O + `mock.patch.object(vw, SAMPLE_PATH/EVIDENCE_PATH/GOVERNANCE_DIR)`，与 FIX-355 既有用例同构；归档来源用例 plan_rows=[] + archive index 真实行形态（「完成 (date)」终态断言）；活体来源用例 tracker「✅ 完成」行——两类正例的数据面保真。
- **覆盖结构**：分类器 4（含合并集合混存、域外 fail-safe 缺省）+ 模板互异 1 + 行为正例 4（V2 L-A 与 V5 legacy-key 两门 × 两来源）+ fixture 边界 1。V2 historical / V5 historical 两门无专属行为正例——见 P3-1。

### 3.5 范围纪律 + 待验证项复核 — **通过**

- 恰 2 文件（V1/V2 实证）；其余 3 个工作树修改文件属并行任务，未纳入本审查。
- D5 无关性复核：见 §2.2 第 4 行——静态论证完整（四点），经验 A/B 复跑未执行，如实标注。

## 4. 五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | §3.1 判别语义与 fail-safe 方向；§3.3 零改动 |
| 安全性 | ✅ 通过 | 无外部输入/路径构造/注入面；模板为常量；§3.2 下游安全 |
| 可维护性 | ✅ 通过 | 分流集中单一可单测函数；「判定无措辞、措辞无判定」分离有文档（L2074-2081 docstring）；模块注释解释因果类型 |
| 性能 | ✅ 通过 | 每豁免行 O(1) 字典查找；无新增扫描 |
| 测试覆盖 | ✅ 通过（P3 备注） | 10 用例红相结构成立、正例装置保真；4 门中 2 门行为正例抽样（P3-1） |

## 5. AI 代码专项 5 项

| 检查项 | 结论 |
|--------|------|
| mock 残留 | ✅ 无——产品代码零 mock；测试 mock 为既有 fixture 隔离模式（与文件内 FIX-355 用例一致） |
| 硬编码返回值 | ✅ 无——返回值为常量模板文本，属修复本体 |
| 幻觉 API 调用 | ✅ 无——仅 set 运算 + 字典查找，无新外部调用 |
| 未实现 TODO | ✅ 无 |
| 过度实现 | ✅ 无——1 字典 + 2 微函数 + 4 处注入，最小交付面 |

## 6. Findings

| 级别 | 位置 | 描述 | 建议 |
|------|------|------|------|
| P0 | — | 无 | — |
| P1 | — | 无 | — |
| P2 | — | 无 | — |
| P3-1 | test_review_closure_legacy.py | 行为正例仅抽样 V2 L-A / V5 legacy-key 两门；V2 historical / V5 historical 两门的新分句仅由共享 mapper 单测间接看护（f-string 注入点 L2273/L2478 的内容无端到端断言；崩溃类错误会被既有 FIX-291/EV-066 用例捕获） | 后续（可并入 FIX-358 同文件串行）补 2 个行为正例 |
| P3-2 | review_domain.py L2158 | 分类器正确性依赖不变量 `closed ⊇ completed`，当前由派生代码结构保证但无断言/交叉引用看护——未来若有人改动派生使 closed 收窄，措辞会静默误归因 | 在 L2158 合并点加一行交叉引用注释（指向 `_terminal_exemption_source` docstring 的不变量声明），或加防御断言 |

## 7. 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✅（P0 = 0） |
| 5 维度全覆盖 = 100% | ✅（§4） |
| 每条发现标注级别 = 100% | ✅（§6，含「无 P0/P1/P2」显式记录） |
| 设计一致性检查 | ✅（§1/§3.1——与 DEC-214② 合并语义、review-FIX-355 C-01 修复语义、binding note 5 锚条款一致） |
| AI 专项 5 项 | ✅（§5） |
| 独立复验命令真实执行（exit code + 摘要入报告） | ✅ 部分达成并如实披露——V1~V8 已执行入表；D1~D5 动态项未及执行，按 Coordinator 指令以规定措辞标注并附静态论证（§2.2）。此项披露不构成代码级 BLOCKING finding |
| 报告落盘 docs/reviews/（唯一写入面） | ✅（本文件） |

## 8. 总结论

## **APPROVED_WITH_NOTES** — unresolved_blockers = **0**

零 P0/P1/P2 findings；修复语义与 DEC-214② 判定语义一致，fail-safe 方向安全（fail-closed：无归档贡献不声称归档依据），判定逻辑零改动经 diff 逐字核验，下游解析面安全经全插件消费面核查。Notes = §2.2 五项动态复验未独立复验的如实披露 + 两条 P3 建议。APPROVED 仅表示本代码审查硬门槛通过，不替代测试/发布审查；D1~D5 的经验复验缺口由 Coordinator 决定是否补跑或在 evidence-log 如实记录后接受。

## 9. 边缘问题（呈 Coordinator，不阻塞）

1. **D1~D5 经验复验缺口**：建议 evidence-log 记录时如实保留「Reviewer 未独立复验」标注；若后续环境允许，Coordinator 可补一次只读复跑（pytest 该文件 + `check-governance --summary-only` + `-k FIX300DualCaliber`）闭环。
2. **FIX300DualCaliber 3 failed 长期滞留**：与本 diff 无关的静态论证虽成立，该失败面（Check 31 双口径 identity/host-root 解析，环境敏感）建议入账独立任务跟进，避免带失败基线进入 0.85.0。
3. **P3-2 不变量看护**：可随 FIX-358（同文件串行）顺带处理，避免单独开票。
4. 本审查会话曾创建临时文件 `docs/reviews/.fix357-packet-tmp.json`（packet 提取用），已随本报告落盘清理删除；docs/reviews/ 最终仅含本报告。

— review-FIX-357-CODE-R0 完 —
