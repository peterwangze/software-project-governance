# Review Report — REL-079 CODE R0（0.83.0 候选 M-1 增量 + 集成面）

- **Task ID**: REL-079（DEC-200 预授权发布链 M-3 CODE 半面；0.83.0 候选）
- **Round**: R0（初审）
- **Reviewer**: Code Reviewer Agent（只读审查；未修改被审文件；未执行命令；未与用户交互）
- **审查对象**: 候选全量 delta vs v0.82.0 = 34 文件 +1421/−81，其中已审批两批次 `bf7e25a`(FIX-349, APPROVED_WITH_NOTES/0) + `589e99f`(FIX-350, APPROVED_WITH_NOTES/0) 之外，本审重点为 M-1 未提交增量（版本声明面 bump + 0.83.0.json candidate manifest + 投影文件 + plan-tracker 数据面）及三批次集成共存
- **审查方法**: 纯静态审查（Read/Grep/Glob）。角色协议禁止执行命令——全部机器门禁申报按「申报核实表」（§10）标注**未验证**，不写成已通过
- **Diff 证据口径声明**: `m1-full-delta.diff`（209 行 / 16 文件）覆盖面**不完整**——工作区实测另有个别版本面成员已变更但不在 diff 内（详见 F-4）：根 CLAUDE.md、verify_workflow.py（REQUIRED_SNIPPETS×6）、fixture SKILL.md、fixture plan-tracker。本审查以**工作区文件现状**为权威逐点对账，不以 diff 缺席判定缺失，也不以申报判定存在

---

## 1. 版本面声明点核对矩阵（遗漏/多余检测）

权威源 = SKILL.md frontmatter（version-projections.json `authority`）。下表为全量实测：

| # | 声明点 | 实测 | 证据 |
|---|--------|------|------|
| 1 | SKILL.md frontmatter `version` | **0.83.0** ✅ | 工作区 Read :3 |
| 2 | package.json | **0.83.0** ✅ | diff hunk + REQUIRED_SNIPPETS 钉住（:1040-1042）|
| 3 | core/manifest.json | **0.83.0** ✅ | 工作区 Read :4 |
| 4 | .claude-plugin/plugin.json | **0.83.0** ✅ | diff hunk + 钉住（:1028-1030）|
| 5 | .claude-plugin/marketplace.json | **0.83.0** ✅ | diff hunk + 钉住（:1031-1033）|
| 6 | .codex-plugin/plugin.json | **0.83.0** ✅ | diff hunk + 钉住（:1034-1036）|
| 7 | .zcode-plugin/plugin.json | **0.83.0** ✅ | diff hunk + 钉住（:1037-1039）|
| 8 | .chrys-plugin/plugin.json | **0.83.0** ✅ | diff hunk |
| 9 | AGENTS.md @bootstrap-version | **0.83.0** ✅ | 工作区 Grep :5 |
| 10 | CLAUDE.md @bootstrap-version | **0.83.0** ✅ | 工作区 Read :5（**不在 diff 内**）|
| 11-14 | hooks ×4 @version（pre-commit/commit-msg/post-commit/prepare-commit-msg）| **0.83.0** ×4 ✅ | diff 4 hunks |
| 15-20 | verify_workflow.py REQUIRED_SNIPPETS ×6 版本字面量 | **0.83.0** ×6 ✅ | Grep 恰 6 处（:1029/1032/1035/1038/1041/1044）；文件内 **0 处 0.82.0 残留**（Grep 零命中）（**不在 diff 内**）|
| 21-23 | commands/governance-init.md 模板标记 ×3（lightweight :197 / standard :262 / strict :533）| **0.83.0** ×3 ✅ | 工作区 Grep——`> @bootstrap-version: 0.83.0` 恰 3 处，无第 4 处旧标记 |
| 24 | agent-presets/governance/agent.cordis.yml.template（dsh-persona-version）| **v0.83.0** ✅ | Grep :51 `治理工作流（v0.83.0）` |
| 25 | adapters/dsh/AGENTS.md.template（dsh-agents-bootstrap-version）| **0.83.0** ✅ | Grep :3 |
| 26 | .governance/plan-tracker.md 数据面 `工作流版本` | **0.83.0** ✅ | Grep :11（M-1 候选打包中——未发布，口径正确）|
| 27 | 投影：fixture SKILL.md（fixture-skill）| **0.83.0** ✅ | 工作区 Read :3 |
| 28 | 投影：fixture plan-tracker `工作流版本`（fixture-plan，count=1）| **0.83.0**，恰 1 处 ✅ | Grep :9 |
| 29 | fixture CLAUDE.md @bootstrap-version | **0.82.0** ❌ | 见 F-2（P2）|
| 30 | fixture verify_workflow.py / fixture core/manifest.json | 无版本锚 / **0.37.0** | 见 F-3（P3，预存 lag 族）|

**裁决**: 申报的版本声明面（14 文件级 + REQUIRED_SNIPPETS×6 + 模板×3）**全部 0.83.0，无遗漏、无多余**；投影合同 15 项目标中 14 项已逐点实测/静态钉住为 0.83.0。唯一版本面外的陈旧点 = fixture 原生入口镜像（F-2/F-3），均为投影合同未登记目标，非本次申报义务内遗漏。

---

## 2. 0.83.0.json candidate manifest 结构核对

对照 0.82.0.json（released）逐键核对：

| 键 | 0.82.0（released）| 0.83.0（candidate）| 裁决 |
|---|---|---|---|
| artifacts | changelog + release_docs×3(0.82.0) + review_evidence | 同构，release_docs×3 指向 0.83.0 三文件 | ✅ 同构 |
| effective_state | lifecycle_state=released, amendments=[], withdrawn=false | lifecycle_state=**candidate**，余同 | ✅ 预期差异 |
| events | 1×candidate_to_released | **[]** | ✅ 预期差异 |
| lifecycle_state（顶层）| released | **candidate** | ✅ 预期差异 |
| trust | candidate_commit.derivation=git_commit_adding_path | **完全同形，无额外键** | ✅（此前 schema 违规已修，未复发）|
| provenance / schema_version / version | native / 1 / 0.82.0 | native / 1 / 0.83.0 | ✅ |

**结构差异恰为 lifecycle/events/trust 三处，无第 4 处差异、无额外键。** 单行紧凑 JSON、键名字母序——与 ledger `parse_canonical_manifest_bytes` 的 canonical 形态要求（NFC、排序键、紧凑分隔符、单一尾 LF，ledger.py:142-149）一致。

**附**：0.83.0.json 引用的三份 release docs（release-checklist / feature-flags / rollback-plan-0.83.0.md）**已存在于 docs/release/**（Glob 实测 3 文件）——无 dangling 引用。

---

## 3. 0.82.0.json released 事件 integrity 截重盖专项（发现 F-1）

**事实链**（全部静态可证）：
1. diff 显示 0.82.0.json 唯一变化 = `events[0].integrity`：`sha256:5c9e8fb9…` → `sha256:34d779ab…`；event 其余字段（id=rel078-transition / type / recorded_at / claims 三键）**逐字节未变**。
2. ledger.py:157-159：`event_integrity` = sha256(canonical_json_bytes(event 去 integrity 键) 去尾 LF)——对固定 payload **确定性**。
3. ledger.py:231-232：校验要求 `declared_integrity == event_integrity(event)`，不等即报 `integrity hash mismatch`。
4. release/ledger.py **不在本次 M-1 变更集内**（不在 diff 16 文件中，亦非 FIX-349/350 已审范围）→ 同一 payload、同一算法下两个哈希不可能同时有效：旧截 5c9e8fb9 在当前算法下**必然已失效**（或为发布时错算，或为算法后变更遗留），新截 34d779ab 是使 :231 通过的唯一形态。

**裁决**: 重盖在机械上必需（否则 release-ledger 永久 FAIL），event 历史内容零变化，且 Coordinator 申报 release-ledger = NATIVE_CANDIDATE PASS 与新截自洽。**但这是对已发布版本完整性戳的改写，未列入本任务披露项**——trust layer 的审计链语义要求此类改写显式入账。→ **P2**，不阻断，处置要求见 F-1。

---

## 4. 投影完整性抽查（release-projection 产物非手改）

按任务要求抽查 ≥2，实际完成 4 项 projection-registry 目标 + 2 项投影外镜像：

| 目标 | 结果 |
|---|---|
| fixture-skill（fixture SKILL.md）| 0.83.0 ✅ 与源逐字段同构 |
| fixture-plan（fixture plan-tracker，`工作流版本` count=1）| 0.83.0，恰 1 处 ✅ 与 transformed_text 契约（count=1）吻合 |
| dsh-persona-version（agent.cordis.yml.template）| v0.83.0 ✅ |
| dsh-agents-bootstrap-version（adapters/dsh/AGENTS.md.template）| 0.83.0 ✅ |

四个非 diff 文件的 projection 目标全部就位——「4 个投影文件」申报与上述 4 项 registry 目标为最高吻合解释（申报未列名，见 F-5）。投影外镜像的陈旧状态见 F-2/F-3。

---

## 5. BOM 事故残留专项

| 检查面 | 方法 | 结果 |
|---|---|---|
| m1-full-delta.diff 全文 | Grep `\x{FEFF}` | **0 命中** ✅ 无 BOM 引入 |
| 全仓 *.json（含 6 个 bump JSON）| Grep `\x{FEFF}` | **0 命中** ✅ |
| 全仓 *.md | Grep `\x{FEFF}` | **0 命中** ✅ |
| hooks 目录 4 文件 | Grep `\x{FEFF}` | **0 命中** ✅ |
| JSON 可读性 | .claude-plugin/plugin.json / manifest.json / package.json / marketplace.json / 0.83.0.json 逐一 Read/Grep | 全部可读、结构完好、无异常首字节 ✅ |

此前 16 文件 BOM 剥离无残留、本次 M-1 无 BOM 新增引入。

---

## 6. 集成面：FIX-349 + FIX-350 两批次共存核对

- **共存实证（工作区静态）**：FIX-349 产物 U+000C 分隔符条目在 verify_workflow.py:11783（`("U+000C", "\x0c")`）；FIX-350 产物 `_archguard_exclusion_match` 在 :19453（定义）/ :19485（薄包装）/ :19660（dup 消费点）。两批次产物在同一文件内共存、行号连续无交叠冲突。
- **ratchet 锚静态吻合**：verify_workflow.py 实际总行数 = **24583**（Read 分页元数据实测）= architecture-baseline.json `anchor_loc`（FIX-350 R0 §1 #5 已核 24583）——锚值与工作区现状一致，与申报 committed==fresh PASS 方向互证（复跑未执行，见 §10）。
- **REQUIRED_SNIPPETS bump 与 SKILL frontmatter 一致**：×6 字面量 = 0.83.0 = frontmatter version（§1 #1/#15-20）✅。
- **前轮 findings 闭合核对**：FIX-349 R0 的 F-1（U+000C）已由 FIX-350 交付闭合（:11783 + docstring + 负例，FIX-350 R0 §3.6 已核）；FIX-349 R0 其余 P2/P3（F-2 双面语义已闭合、F-3~F-7 备案级）无未决阻塞项残留——与两份前轮报告的 APPROVED_WITH_NOTES/0 终态一致，无复审链未闭环事项。

---

## 7. 五维度审查结论

### 维度 1：正确性 — PASS（附 P2×2、P3×3）
版本声明面 25+ 申报点全部 0.83.0 无遗漏无多余（§1）；0.83.0.json 结构恰三处预期差异、无额外键（§2）；integrity 重盖机制自洽但披露缺失（§3/F-1）；fixture 镜像陈旧（F-2/F-3）。边界条件：governance-init.md 模板恰 3 处无第 4 处旧标记；fixture-plan count=1 与契约一致；verify_workflow.py 无 0.82.0 残留。

### 维度 2：安全性 — PASS（零发现）
diff 全部内容为版本字符串、bootstrap 标记注释行与一个数据 JSON；无密钥/token；hooks 仅注释行版本变化；0.83.0.json 为仓库内受控数据文件，非外部输入，无注入面；canonical 形态受 ledger 解析器校验。

### 维度 3：可维护性 — PASS（附 F-2/F-3/F-4）
投影合同（version-projections.json 15 项）覆盖了 bump 的全部常规面且机器可校验——本次 14 项 registry 目标全部就位即其收益实证。缺口：fixture 原生入口镜像（CLAUDE.md/AGENTS.md/GEMINI.md）与 fixture core/manifest.json 不在合同内，无机器同步路径，依赖人工记忆（F-2 实证上版同步、本版遗漏）。diff 证据生成不完整（F-4）降低可复查性。

### 维度 4：性能 — PASS（零发现）
配置/数据面变更；REQUIRED_SNIPPETS ×6 为字面量包含检查，成本可忽略；无新增 I/O、无循环嵌套、无 N+1。

### 维度 5：测试覆盖 — PASS（附 coverage gap 备注）
机器门禁 7 项由 Coordinator 独立复跑申报 PASS（本审查未复跑，§10）；其中 3 项获静态佐证：projection 4 目标实测就位（§4）、REQUIRED_SNIPPETS 钉住存在（§1）、文件 LOC = ratchet 锚（§6）。Coverage gap：fixture 镜像陈旧态无任何机器检查看护（与 F-2 同根）——check-version-consistency 与 check-projection-sync 双双 PASS 的同时 fixture CLAUDE.md 停留在 0.82.0，证明两检查的覆盖边界均不含该镜像。

---

## 8. 发现列表

> **P0 = 0，P1 = 0**。以下 5 条均不阻塞合并。

### F-1（P2）已发布 0.82.0.json 事件 integrity 截被重盖，未列入披露项
- **位置**: `skills/software-project-governance/core/releases/0.82.0.json:1`；机制 `infra/release/ledger.py:157-159, :231-232`
- **事实**: §3 全链——event 内容零变化而 integrity 由 5c9e8fb9… 改写为 34d779ab…；ledger 算法确定性 + :231 精确匹配要求 ⇒ 旧截在当前算法下必已失效，重盖机械必需；release-ledger NATIVE_CANDIDATE PASS（Coordinator 复跑申报）与新截自洽。任务申报的已知披露项（unittest 30 失败族、governance health 21 issues）**不含此项**。
- **影响**: 内容与验证均无损；但 trust layer 对已发布历史戳的静默改写若不入账，审计链「hash 即历史」的语义被削弱——未来追溯 0.82.0 过渡事件时无法从在库工单看出截曾被重盖及原因。
- **建议**: 发布证据（evidence-log / REL-079 release checklist）补一条：记录重盖所用的机器命令/工具输出与成因定性（发布时错算 vs canonical 算法后变更）。无需代码修改。

### F-2（P2）fixture CLAUDE.md bootstrap 标记停留在 0.82.0——投影合同外的版本面成员
- **位置**: `project/e2e-test-project/CLAUDE.md:5`（`> @bootstrap-version: 0.82.0`）
- **事实**: fixture SKILL.md 已投影至 0.83.0（§4），按 FIX-238.2 口径（bootstrap 头 < fixture 内 SKILL frontmatter active_version 即陈旧）该镜像**现为陈旧态**。version-projections.json 15 项 projection 不含 fixture 原生入口（CLAUDE.md/AGENTS.md/GEMINI.md 均无登记）；该文件 0.82.0 的存在证明上一发布周期它曾被（人工）同步——即它是**事实上的版本面成员，但无机器同步路径**。本次 M-1 申报的「AGENTS.md+CLAUDE.md bootstrap 标记」指根目录两文件（均已 0.83.0 ✅），fixture 镜像不在申报义务内——属投影合同覆盖缺口，非执行遗漏。
- **影响**: e2e fixture 内部版本自洽性破裂（SKILL 0.83.0 vs CLAUDE.md 0.82.0）；若 e2e 检查未来覆盖 bootstrap 新鲜度（REQ-065 fixture 跟随当前版本的要求面），将产生预期差。
- **建议**: 并入 0.83.0 发布收尾 fixture regen 清单（FIX-349 F-7 政策的天然覆盖对象）；中期把 fixture 原生入口登记为 projection（如 transformed_text 指向 CLAUDE.md 标记行），消灭人工同步依赖。

### F-3（P3）fixture 树预存 lag 延续实证：verify_workflow.py 副本无版本锚、core/manifest.json 副本=0.37.0
- **位置**: `project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py`（Grep `0\.8[0-9]\.0` 零命中）；`.../core/manifest.json:4`（`"version": "0.37.0"`）
- **事实**: FIX-349 R0 F-7 已披露 fixture verify_workflow.py 预存 lag 并确立「发布收尾统一 regen」政策；本次实测扩展该事实：副本连 REQUIRED_SNIPPETS 版本锚都没有（早于该机制引入），fixture core/manifest.json 更陈旧（0.37.0）。两者均非投影合同目标，与 F-2 同根。
- **建议**: regen 清单按「整个 fixture 树」而非逐文件点名执行，或明确豁免边界写入投影合同注释；备案即可，不阻塞。

### F-4（P3）m1-full-delta.diff 覆盖面不完整（16 文件 vs 实测 ≥20 变更文件）
- **位置**: `C:\Users\peter\AppData\Local\Temp\m1-full-delta.diff`（审查输入证据）
- **事实**: 工作区实测 4 个已变更的版本面成员不在 diff 内：根 CLAUDE.md（0.83.0 ✅ 已直接读取补证）、verify_workflow.py REQUIRED_SNIPPETS×6（0.83.0 ✅ Grep 补证）、fixture SKILL.md 与 fixture plan-tracker（0.83.0 ✅ 补证）。任务侧已知「投影生成文件 git status 不可得」，但 CLAUDE.md 与 verify_workflow.py 属可 diff 的已跟踪面，缺席原因未在申报中说明。
- **影响**: 本轮无实质影响（已按工作区现状全量对账补齐）；削弱 diff 作为审查证据的完备性，若后续轮沿用同一 diff 会得出「缺 CLAUDE.md/verify_workflow 变更」的误判。
- **建议**: 后续轮 diff 生成需覆盖全部版本面成员；备案。

### F-5（P3）「4 个投影文件」申报未逐项列名
- **位置**: 任务申报文本（非仓库文件）
- **事实**: 实测 projection-registry 中恰好 4 个目标在本周期发生版本变化且不在 diff 内：fixture-skill / fixture-plan / dsh-persona-version / dsh-agents-bootstrap-version——全部 0.83.0 ✅（§4），为该申报的最高吻合解释；但申报未列名，无法确证即此 4 项。
- **建议**: 后续任务申报对投影面逐项列名（id 级），便于对账；备案。

---

## 9. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | M-1 diff 为配置/数据/文档面：无代码逻辑、无测试、无桩；hooks hunks 仅注释行版本号 |
| 2 | 硬编码返回值 | ✅ 无 | 无可执行逻辑变更；0.83.0.json 为声明式数据（candidate 形态），非运行时返回 |
| 3 | 幻觉 API 调用 | ✅ 无 | 无新增代码路径；REQUIRED_SNIPPETS ×6 为字面量钉住（Read 实证 :1028-1045），非调用 |
| 4 | 未实现 TODO | ✅ 无 | diff 与新文件无 TODO/FIXME/pass 桩；0.83.0.json 三份 release docs 引用目标已存在（Glob 实证），非悬空承诺 |
| 5 | 过度实现 | ✅ 无 | 0.83.0.json 恰为 schema 最小 candidate 形态（§2 无额外键）；版本面变更逐点对应申报；超出纯 bump 的唯一变更 = integrity 重盖（已单列为 F-1，非夹带代码）|

---

## 10. Developer/Coordinator 申报核实表（事实红线）

| # | 申报 | 裁决 | 依据 |
|---|------|------|------|
| ① | M-1 版本面 bump（SKILL/package/manifest/marketplace/4×plugin.json/4×hooks/AGENTS+CLAUDE 标记/REQUIRED_SNIPPETS×6/init 模板×3）| ✅ 已验证 | §1 矩阵逐点 Read/Grep，全部 0.83.0，无遗漏无多余 |
| ② | check-version-consistency PASS | ⚠️ **未验证**（申报值，Coordinator 复跑）；静态佐证：§1 全点实测一致；同时实测表明其覆盖边界不含 fixture 原生入口（F-2 同轮 PASS 与陈旧共存） | — |
| ③ | check-projection-sync PASS（15 mirrors）| ⚠️ **未验证**（申报值）；静态佐证：4 个本周期 projection 目标实测 0.83.0（§4）；15 项中其余为结构化 JSON /version 指针，已由 §1 对应点实测覆盖 | — |
| ④ | check-manifest-consistency PASS（809）| ⚠️ **未验证**（申报值）；静态佐证：manifest.json 0.83.0、canonical 形态未见破坏 | — |
| ⑤ | check-injection-contract PASS / archguard-ratchet fatal green（24583 锚）| ⚠️ **未验证**（申报值）；静态佐证：文件 LOC=24583 与锚一致、FIX-349/350 产物共存无交叠（§6） | — |
| ⑥ | release-ledger NATIVE_CANDIDATE | ⚠️ **未验证**（申报值）；静态佐证：0.83.0.json 结构合规、0.82.0.json 新截与当前算法自洽（§2/§3） | — |
| ⑦ | EntryBootstrapTemplateTests 绿（模板标记 ×3 bump 后）| ⚠️ **未验证**（申报值）；静态佐证：governance-init.md 恰 3 处 0.83.0 标记、无旧标记残留（§1 #21-23） | — |
| ⑧ | 全量 unittest 3211 tests failures=30（WSL 无发行版族 + hooks replay 漂移族；0.82.0 同型披露先例）| ⚠️ **未验证**（运行值，未复跑）；本审查范围内无新增红因证据，按披露先例接受为发布审查输入 | — |
| ⑨ | governance health 21 issues 披露基线 | ⚠️ **未验证**（运行值）；同上 | — |
| ⑩ | BOM 16 文件已剥离、无残留 | ✅ 已验证 | §5 四面 Grep 零命中 + JSON 可读性实测 |

---

## 11. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | 0 | ✅ PASS |
| 5 维度逐一结论 | 100% | 5/5（§7）| ✅ PASS |
| 每条发现 P0~P3 + 位置 + 事实依据 | 100% | 5/5（§8）| ✅ PASS |
| 设计一致性 | 已完成 | 与 DEC-200 M-3 CODE 半面范围一致；FIX-238.2 标记纪律全面执行；release-ledger schema 无违规复发（§2 trust 无额外键）；两前轮审查终态核对无未闭环事项（§6）| ✅ PASS |
| AI 专项 5 项 | 全部完成 | 5/5（§9）| ✅ PASS |

---

## 12. 审查结论

```yaml
verdict: APPROVED_WITH_NOTES
unresolved_blockers: 0
findings:
  P0: 0
  P1: 0
  P2: 2   # F-1 0.82.0 integrity 重盖披露缺失 / F-2 fixture CLAUDE.md 陈旧（投影合同缺口）
  P3: 3   # F-3 fixture 树 lag 延续 / F-4 diff 证据不完整 / F-5 投影申报未列名
blocking: false
notes: |
  版本声明面 25+ 申报点全部实测 0.83.0，无遗漏无多余；0.83.0.json candidate
  manifest 结构恰 lifecycle/events/trust 三处预期差异、无额外键（此前 schema
  违规未复发）；投影 4 目标实测就位；BOM 零残留；FIX-349/350 共存与 ratchet
  锚静态吻合，两前轮 APPROVED_WITH_NOTES/0 终态无未闭环事项。
  两项 P2 均为披露/看护缺口而非缺陷：F-1 要求把已发布事件 integrity 重盖
  （内容零变化、机械必需）入账发布证据；F-2 要求 fixture CLAUDE.md 并入发布
  收尾 regen 或登记 projection。全部机器门禁为 Coordinator 复跑申报值，本
  审查按红线标注未验证，其中 3 项获静态佐证。P0=0，不阻断 M-3 CODE 半面通过。
```

*Reviewer: Code Reviewer Agent · REL-079 CODE R0 · 只读静态审查（Read/Grep/Glob），未执行命令、未修改被审文件；本文件为本次任务唯一写入产物。*
