# REVIEW-FIX-381-CODE-R0 — 切分器 backport 政策制度化（代码审查）

> **Task**: FIX-381（P2，v0.88.0 阶段 A7——arch 2026-09-23 Q4 定案 ⑨ 制度化：声明快照 + 受控 backport 非单源化）
> **Round**: R0（无前轮）
> **审查对象**: 工作树未 commit diff，3 文件 +362/−12（`git diff --stat` 实测吻合）
> **Reviewer**: Code Reviewer Agent（只读审查；唯一输出本报告）
> **审查方法**: 逐行读 diff 与三文件全文 + 全部申报数字独立实测复现（测试套件/verify/守卫活体/探针判别力内存模拟/分歧行四口径实测/commit 与 EVD 记录比对）——实测优先，未验证项显式标注

---

## 1. 目标锚定

- plan-tracker L105：FIX-381 行存在，验收 =「五制度件落地 + 忽略快照可再生验证 + 守卫语义复核结论」，deps=[FIX-378]（已闭环），状态与本次派发一致。
- agent-locks.json：`docs/reviews/review-FIX-381-CODE-R0.md` 锁定于 FIX-381（post-hoc Code Reviewer dispatch）。
- version-plan-0.88.0.md L13/L30：A7 =「切分器 backport 政策制度化（⑨ 定案——arch Q4）：制度五件套——触发器/快照清单/补丁台账/双运行契约样例/隐性耦合检查与可再生性」——与本 diff 的 policy 块五节逐一对应 ✓。

## 2. MUST 重点审查逐项结论

### 2.1 五件套结构完备性与机读性 — ✅ 通过

`version-projections.json` 新顶层块 `legacy_snapshot_backport_policy` 实测 9 键：`policy_id / decision_basis / snapshot_inventory / trigger / ledger / dual_run_contract / coupling_check / replay_path / guard_semantics_review`（python json.load 实证，文件合法 UTF-8 JSON）。

- **trigger**：`evaluate_when` + `criteria_all` 三判据（same-origin region / live region / real effect，列表机读）+ `dispositions` 两出口（backport / not-applicable——后者援引 FIX-380 note 3 先例，四理由与 FIX-380 commit c349f8e 记录逐字一致）+ `default`（"silence is not a disposition"）。
- **snapshot_inventory**：引用非复制——`location` 指向 `declared_legacy_snapshots + declared_legacy_snapshot_scope`（两键实存于同文件，实测确认），note 明示 "one list, one truth"。与任务契约「引用非复制」一致，且避免与 10 个 declared 条目形成第二事实源。
- **ledger**：`location` 指向 per-entry `approved_backports`；`required_fields` 8 字段；`location_rationale` 说明骑既有 `check_legacy_snapshots` 可证伪机制（零新 manifest 面）；`anchor_convention` 说明 anchor_symbol（函数名，防行号腐化——援引 FIX-388 重锚先例）+ marker（补丁自带 provenance 文本）双锚定。
- **dual_run_contract**：requirement + canonical_leg + snapshot_leg + `parity`（"both legs must agree… the probe must FAIL on the pre-fix state — a probe that cannot fail proves nothing"——可证伪语义强）+ sample（FIX-378 实例）。
- **coupling_check**：`when` + 四清单（fixture-own 测试对 / registry 机器键面 / 第三副本数据漂移——援引 FIX-379 task_priority 词表先例 / 跨文件契约）+ `record`（`coupling_reviewed` 字段落点）。
- **replay_path**：rule（再生非受支持写）+ 4 步（收敛红不消音 → 按 anchor 重放并恢复 marker → 重跑 dual_run → 更新台账再收敛）+ `canonical_regenerated_case`（字节全等则 promote-and-retire）。
- fixture-engine 条目首条 `approved_backports` 8 字段齐备（见 §2.3）。

### 2.2 守卫精化实现（projection.py）与向后兼容 — ✅ 通过

守卫实体确认：`check_legacy_snapshots` 位于 `infra/release/projection.py` L266-458。**triage 勘误成立**：`infra/checks/projection.py` 实测 202 行（python 逐行计数），`git diff` 零修改——Developer 勘误有据（审查初测 Measure-Object 177 行系忽略空行，已复核更正）。

逐项（行号为 projection.py 现行）：

| 守卫面 | 实现位置 | 实测 |
|---|---|---|
| policy 非对象红 | L351-352 | ✓ 测试钉 `test_policy_block_non_object_fails` |
| policy 五节空洞红 | L355-361（`BACKPORT_POLICY_REQUIRED_SECTIONS` L41-42，空洞=`not policy.get(section)` 含缺失与假值） | ✓ 测试钉 `test_hollow_policy_block_fails` |
| 台账非列表/空列表红 | L406-409 | ✓ 测试钉 `test_non_list_ledger_fails` |
| 台账条目八字段空洞红 | L420-428（`BACKPORT_LEDGER_REQUIRED_FIELDS` L34-36，逐字段 `str(... or "").strip()` 判空） | ✓ 测试钉 `test_ledger_entry_missing_fields_fails` |
| anchor+marker 对副本文本机检 | L411（每条目单次 read_text）+ L429-444（双子串独立红：anchor `no longer resolves` / marker `not found`） | ✓ 测试钉 `test_stale_anchor_fails` / `test_missing_marker_fails`（两用例正交设计——锚改名保 marker、删 marker 保锚，各红一通道） |
| stale-ledger 红 | 上两项合成（"a stale ledger is a failure, not a memory"） | ✓ |
| 收敛消息 ledger-aware 精化 | L390-402：带台账 → 两合法出口（replay-then-redeclare / promote-and-retire-含台账退役）；无台账 → 原消息逐字保留 | ✓ 测试钉 `test_converged_backport_bearing_snapshot_names_replay_disposition` |
| 返回面新增 `backport_ledger` | L457 + 早退路径 L334-341/L340-342 均携带（"zeroed when unreadable" 契约成立）；`release-projection` 命令实测渲染 `policy_declared: true, ledger_entries: 1, anchors_resolved: 1` | ✓ |

**向后兼容（additive）实测成立**：policy 校验仅当块存在（L350 `if policy is not None`）；台账校验仅当字段存在（L404-405 `is not None`）；收敛红触发判据 L388 **一字未改**（全文件字节等价）；`check_projections`（L565-566）只消费 `issues`/`declared`，形状无破坏；全仓 `check_legacy_snapshots` 调用面仅 `check_projections` + 本测试文件（git grep 实证）；16 个原有用例全绿即 policy-absent 旧路径零义务的直接测试证明（`LegacySnapshotDeclarationTests` 的临时目录用例均不带 policy 块）。

**活体**：`check_legacy_snapshots(仓库根)` 实跑 = `pass: true, issues: [], checked: 10, converged: [], missing: [], backport_ledger: {policy_declared: true, ledger_entries: 1, anchors_resolved: 1}`；census 披露面完好（inventory 297 / divergent 37 / declared 10 / undeclared_out_of_scope 27）。「局部 backport 不误发收敛红」由此活体直接证明（fixture-engine 带台账且分歧 → 绿）。

### 2.3 FIX-378 台账条目事实一致性 — ✅ 通过（逐点实读实证）

| 台账字段声明 | 独立核实 |
|---|---|
| `anchor_symbol: "_split_governance_table_row"` | 副本 L6854 `def _split_governance_table_row(line):` 实读 ✓ |
| `marker: "FIX-378 (backport"` | 副本 L6857 docstring `FIX-378 (backport of the FIX-373 fix into this declared legacy snapshot):` 实读 ✓ |
| reason 中 guard 位置 L6887 | 副本 L6887 `if ch == '"' and not in_code_span:` 实读 ✓（与主仓 L12346 同型——FIX-378 commit 44cb534 记录吻合） |
| reason「EVD-248 shape, 10 data cells -> 5」 | EVD-1134（FIX-373：10 格折叠 4 格）+ EVD-1136（LIVE 红态 raw_parts=6/data_cells=5）记录吻合 ✓ |
| `approved`「review-FIX-378-CODE-R0 APPROVED_WITH_NOTES/0 (recorded in the FIX-378 commit)」 | commit 44cb534 message verbatim 含「REVIEW-FIX-378-CODE-R0 APPROVED_WITH_NOTES/0 机录」✓ |
| `dual_run`「LIVE 6/5->12/10 recorded verbatim in the FIX-378 commit」 | commit 44cb534 verbatim 含「冒烟红绿 LIVE 6/5→12/10」（→/-> 排印归一，数字与结构逐字）✓；EVD-1136 补充 SYnth 红态 5/4 与审查内存模拟实测一致（§2.5） |
| `coupling_reviewed` 四项 | ①fixture-test pair：`fixture-test-verify-workflow` 条目实存且 reason 明示 "Declared together with fixture-engine; promoting one without the other breaks the pair" ✓ ②未动声明路径/PROJECTION_SYNC_PATTERNS 成员：diff 无路径移动 + projection-sync PASSED ✓ ③splitter-pin not-applicable 四理由（N-2 裁定/FIX-381 制度承载/锁面/守卫已防护）：与 FIX-380 commit c349f8e note 3 逐字一致，review-FIX-378-CODE-R0 L77 N-2 实读吻合 ✓ ④无第三副本：本审查文件系统级 grep（project/ 全树）实测切分器仅 1 处副本（即声明条目），tracked 面 grep 仅 canonical L12349/L12409 + 测试 docstring 引用 ✓ |
| 「exactly one intentional backport」口径 | 与 FIX-380 注记及 review-FIX-378 E-1 一致（EVD-1150 已核）✓ |

### 2.4 10 用例判别力 — ✅ 通过（4 项 P3 补强建议见发现清单）

`BackportPolicyTests` 10 用例全数实跑通过（`pytest -v`：**26 passed, 6 subtests**——与 Developer 申报逐字一致；16 原有用例零回归）。

- **ship 态活体 ×2**：`test_shipped_policy_and_ledger_are_live`（真注册表：policy_declared + entries≥1 + anchors 全解析）与 `test_shipped_ledger_entry_resolves_in_the_real_copy`（真副本文本逐条 anchor/marker 断言）——机构「活体而非装饰」的直接证明 ✓。
- 各红面：policy 空洞 / policy 非对象 / 台账字段空洞 / 台账非列表 / stale anchor / missing marker / converged 两出口消息——7 红面各有独立用例，红因断言到具体消息片段（非仅 assertFalse）✓。
- 绿路径：`test_valid_ledger_passes`（含 face 计数断言）✓。
- 判别力设计亮点：stale-anchor 与 missing-marker 两用例正交（各自只红一通道），证明双锚定互不遮蔽。

### 2.5 9/9 重放验证可信度 — ✅ 通过（本审查独立复现关键面；沙箱内 9 场景无法逐场重跑，见范围声明）

可仓库侧验证的承重面全部独立复现：

1. **探针判别力（内存模拟，零文件触碰）**：对副本现行切分器提取函数体、内存中回退守卫（模拟 pre-fix），跑真实 EVD-905 形态行（单无闭引号，与 canonical 已提交测试 test_verify_workflow.py L12167 逐字同型）：**pre-fix 5 parts/4 data cells → post-fix 12 parts/10 data cells == canonical 引擎 10 cells 逐格相等**。红态数字与 EVD-1136 记录「红态 5/4（cells[-1] 吞格实证）」逐字吻合，与 EVD-1134（FIX-373：10 格折叠 4 格）吻合——**dual_run 两腿 parity 与「探针必须能红」语义由本审查独立证实**。
2. **探针换型披露核实（意外获得）**：审查首轮模拟误用成对引号探针，pre-fix 12/10 不折叠（引号自愈开合）——即 Developer 披露的「探针第一版（成对引号）无判别力」的独立复现。单无闭引号才将 in_string 钉到行尾形成折叠。披露属实且机制可解释 ✓。
3. **fresh-generation 模拟披露**：副本 git 忽略实锤（`git check-ignore` → .gitignore L31）——无历史可复原， Developer 以现副本回退守卫模拟 pre-fix 是唯一可行路径，披露诚实 ✓。
4. **converged 红两场景**：不误发 = §2.2 活体（带台账分歧快照 pass）；正确命中 = 单测 `test_converged_backport_bearing_snapshot_names_replay_disposition` 绿（converged+台账 → replay 出口文本）+ 原有 `test_converged_declaration_fails` 绿（收敛即红保持）。
5. **E2 边缘 / marker 机制**：守卫对 marker 缺失必红（L439-444）+ replay_path 步骤 2 要求恢复 marker + anchor_convention 明文——未来 backport 不带 provenance 即红，fail-closed 制度化成立 ✓。

范围声明：9/9 为 Developer 隔离沙箱实跑申报，本审查复现其中全部仓库侧可复核的承重面（上述 5 项）；沙箱内 fixture-cwd 腿等场景以 EVD-1136/commit 44cb534 机录数字交叉印证。

### 2.6 「收敛即红」守卫语义复核结论 — ✅ 逻辑严密（数字口径见 P3-2）

- **判据无需改**：触发器为全文件字节等价（L388 `path.read_bytes() == canon.read_bytes()`），本审查以**结构性证明**坐实「局部 backport 不可能满足」：副本 579,195 字节 vs canonical 1,124,769 字节（545KB 差），行数 14,174 vs 25,534——字节等价在任何局部 backport 下均不可达，与 ~34.7k 具体数字无关。
- **~34.7k 分歧行核实**：四口径实测——git diff 全输出 **34,226 行**（≈34.7k，±1.5% 内，漂移方向与 canonical 持续演进一致）；numstat ±合计 32,392；difflib opcodes 16,048；ndiff 全输出 28,205。数字量级可信（历史同源：FEAT-040 reason、本测试文件 L11 docstring、EVD-1136 均载），但「differing lines」未注明度量口径（见 P3-2）。
- **两出口处置文本**：replay-then-redeclare 与 promote-and-retire（含台账退役）——与 replay_path 的 rule/canonical_regenerated_case 内部一致，实现与测试双落 ✓。`guard_semantics_review.change_landed`「仅收敛消息精化、零触发逻辑变更」与代码实况逐行吻合 ✓。

### 2.7 验证复现 — ✅ 全数复现

| Developer 申报 | 本审查实测 | 结果 |
|---|---|---|
| 26P+6sub（原 16 零回归） | `pytest test_projection_legacy_snapshots.py -v`：26 passed, 6 subtests（16 原有 + 10 新） | ✓ 逐字 |
| verify 全量 PASSED | `python verify_workflow.py`：**== Verification Result: PASSED ==**（exit 0） | ✓ |
| cross-refs/manifest 868/997 | `check-manifest-consistency`：Canonical 868 / Actual 997 **PASS**；`check-cross-references`：无废弃路径/无循环引用 PASS | ✓ 逐字 |
| projection-sync PASS | `check-projection-sync`：Result: PASSED | ✓ |
| release-projection 渲染面 | `release-projection` 输出含 `backport_ledger: {policy_declared: true, ledger_entries: 1, anchors_resolved: 1}` | ✓ |

## 3. 五维度逐项结论

| 维度 | 结论 | 要点 |
|---|---|---|
| 正确性 | ✅ | 逐行读守卫：分支顺序正确（收敛红先于台账校验并 continue；条目非 dict 不计入 ledger_entries 但必红）；早退路径返回面齐备；`errors="replace"` 读取防御性成立；8 字段判空对 None/空串/空白一致 |
| 安全性 | ✅ | 仓库内 CLI 面无外部输入；路径经既有 `_safe_repo_path`（遍历/符号链接防护）；无新增正则（无 ReDoS 面）；无密钥；issues 为纯字符串进 dict/JSON，无注入面 |
| 可维护性 | ✅（P3-3/P3-4/P3-5） | 常量模块级带 docstring；消息自解释；唯一输出文件契约遵守。注意点：required_fields 双处声明无机器互检（P2-1）；`check_legacy_snapshots` 增至 ~193 行（P3-4） |
| 性能 | ✅ | 每带台账条目单次 579KB read_text + O(n) 子串检索；policy 空洞检查 O(5)；无 N+1/O(n²)；对 10 条目规模无感知开销 |
| 测试覆盖 | ✅（P3-6） | 核心路径/边界/错误路径均有；红因断言到消息片段；4 项补强建议见下 |

## 4. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | diff 机械扫描 mock/Mock/patch 零命中；测试用真实临时目录 + 真实 shipped 注册表 |
| 2 | 硬编码返回值 | ✅ 无 | 守卫全部由文件文本计算；测试常量（FIX-999 等）为合法 fixture 而非桩 |
| 3 | 幻觉 API 调用 | ✅ 无 | 所调 API（json/pathlib/tempfile/str 方法/既有 `_safe_repo_path`/`_legacy_census`）均实存；引用的外部记录（commit 44cb534/EVD-1136/review-FIX-378 N-2）全部实读吻合 |
| 4 | 未实现 TODO | ✅ 无 | diff 扫描 TODO/FIXME/XXX/NotImplemented 零命中 |
| 5 | 过度实现 | ✅ 无 | additive 最小面；informative 键（decision_basis/snapshot_inventory/guard_semantics_review）不强制有明示理由；无投机泛化 |

## 5. 发现清单

| # | 级别 | 位置 | 描述与证据 | 建议 |
|---|---|---|---|---|
| P2-1 | **P2 建议** | `infra/release/projection.py` L30-36 vs `core/version-projections.json` `ledger.required_fields` | 八字段契约存在**双处文本声明**（Python 元组 + JSON 列表）且无机器互检；projection.py 注释「Mirrors the registry policy block's ledger.required_fields … (no second shape source)」表述过强——实际无任何机制阻止单侧漂移，若有人只改 JSON 的 required_fields，守卫仍按旧元组执行（声明机构与执行面静默分叉——恰是本 FIX 制度化要防的漂移类）。当前两处逐字一致（实测），ship 态活体测试钉住现行条目对现行元组，故非现行缺陷 | 加一条 shipped-registry 互检断言（读 JSON `ledger.required_fields` 与 `BACKPORT_LEDGER_REQUIRED_FIELDS` 比对），或在 `test_shipped_policy_and_ledger_are_live` 内并入；同时将注释措辞改为「mirrors — drift is not machine-checked」或落实互检后保留 |
| P3-1 | P3 | 同上两处 | 与 P2-1 同源的现状注记：JSON `required_fields` 目前是纯声明文本，守卫不读它 | （随 P2-1 一并处置） |
| P3-2 | P3 | `version-projections.json` `guard_semantics_review.conclusion`（"~34.7k divergent lines"）及既有 reason/测试 docstring L11 | 「~34.7k」未注明度量口径；现树复现：git diff 全输出 34,226 行（±1.5% 内吻合）/ numstat 32,392 / difflib opcodes 16,048 / ndiff 28,205。量级与结论（分歧行 ≫ 0）不受影响，且套件本以结构化 census 为准（`test_census_is_structural_not_a_disclosed_number` 有意不钉数字） | 文本加一个口径括注（如 "by git-diff output lines"）或将数字降为「tens of thousands」量级表述 |
| P3-3 | P3 | projection.py L429-444 | anchor/marker 机检为**全文件子串**存在性，未绑定到 anchor 函数体内——重构把 marker 移出函数（仍在文件内）不红。作为 stale tripwire 足够（docstring 亦如实写 "resolves in the copy text"），非缺陷 | 记录为未来收紧候选（如 AST 定位 anchor def 后限定区间），无本轮动作必要 |
| P3-4 | P3 | projection.py L266-458 | `check_legacy_snapshots` 约 193 行（本次 +134），持续超 50 行惯例；与仓库既有风格一致，非本次引入 | 后续再加面时考虑按 face 提取 helper |
| P3-5 | P3 | projection.py L355-356 | policy 五节空洞校验对「真值即可」——非空字符串（如 `"todo"`）也过；形状校验宽松（shipped 内容均为对象，风险低） | 可选：要求 dict 形态；非必须 |
| P3-6 | P3 | test_projection_legacy_snapshots.py（新用例面） | 4 处未钉分支：①台账列表含非 dict 项（L413-417 分支）②空列表 `[]`（L406 `not ledger` 半支）③早退路径 `backport_ledger` 键存在性（unreadable/非列表注册表）④converged **无**台账时旧消息文本（L398-402 else 支——红已被原 `test_converged_declaration_fails` 覆盖，文本未钉） | 补 4 个轻量用例（可选，不阻塞） |

## 6. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞 = 0 | ✅ 0 |
| 5 维度全覆盖 | ✅ §3 逐项 |
| 每条发现标注级别 | ✅ P2×1 / P3×6（含同源拆分注记），全部附位置+证据 |
| 设计一致性（ADR/契约比对） | ✅ version-plan-0.88.0 A7 五件套 + ⑨ 定案（arch Q4）+ P-v1 原则 5（制度化非单点）逐项吻合；声明快照非投影目标地位未变 |
| AI 专项 5 项 | ✅ §4 全过 |

## 7. 总结论

**APPROVED_WITH_NOTES**

`unresolved_blockers=0`

P0=0，P1=0；P2×1（required_fields 双声明无机器互检——建议本轮顺手加一条互检断言，不阻塞合并）、P3×6（记录性）。Developer 申报的全部可验证数字（26P+6sub / verify PASSED / 868/997 / projection-sync / 6/5→12/10 / L6887/L6857 / ~34.7k 量级 / 探针换型披露）经独立实测**零虚报**；「收敛即红」复核结论经结构性证明成立（字节等价判据 + 545KB 体量差使局部 backport 不可能误触发）。受控 backport 机构以可证伪机检落地，.marker 机制使未来 backport 强制自带 provenance——⑨ 定案制度化的验收（五制度件 + 可再生性 + 守卫语义复核）全部达成。

**范围声明**：本审查只读被审代码与 `.governance/`；全部模拟为内存级/只读命令，未修改任何被审文件与治理记录；9/9 沙箱重放中仓库侧不可直接重跑的场景已按 §2.5 范围声明以机录数字交叉印证并如实标注。
