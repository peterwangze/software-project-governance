# FIX-390 后置代码审查（R0）— Check 18/18b 结构化状态判据（DEC-241 例外×4 消解票）

- **Round**: R0（首轮独立审查）
- **审查者**: Code Reviewer Agent（只读审查；唯一写入 = 本报告）
- **审查对象**: 仓库根 staged diff（`git diff --cached`，numstat 精确值：verify_workflow.py +109/−23、checks/evidence_domain.py +52/−5、tests/test_fix390_structured_status_judgment.py +607/−0；合计 +768/−28）
- **审查方法**: 逐行通读 staged diff 两个产品文件 + 对照 FIX-393 谓词源（`_status_is_writer_committed_cell`）、DEC-168 机录行契约（`governance_store._build_evidence_row`）、FIX-368 列布局注释、write-guard face-5 凭证扫描粒度 + 硬门槛命令亲跑 + HEAD 对照（detached worktree / 全仓拷贝注入 HEAD 代码 / 受控 A/B dogfood 拷贝 / 全量套件失败节点三重归因）。
- **边界声明**: 未修改产品代码 / staged 区 / `.governance/`；辅助对照工件全部位于 `%TEMP%\fix390_*`（审查结束即清理，含 `git worktree remove`）。
- **数据移动性披露**: 审查进行中（2026-09-26 12:57:52）父会话写入了 `.governance/plan-tracker.md` 与 `evidence-log.md`——live 数据为移动靶，所有 census 绝对数以「受控同数据 A/B」与「带时点探针输出」为准。

---

## 1. 硬门槛实跑记录（亲跑摘要）

| # | 门槛 | 命令 | 结果 |
|---|------|------|------|
| 1 | 新测试套件 | `python -m pytest …/tests/test_fix390_structured_status_judgment.py -v` | **18/18 passed**（0.21s，含 9 subtests） |
| 2 | 红性验证（套件绑定新实现） | 同套件 × HEAD 代码（拷贝注入 HEAD 版本） | **16 failed / 4 passed**——HEAD 上仍绿的 4 个恰为零回归守恒测试（`test_hand_row_without_json_still_fails_18b`、`test_legacy_empty_basis_row_still_fails_check18`、`test_description_fact_takes_precedence_over_basis_column` 等），证明套件非自证 |
| 3 | census | `verify_workflow.py check-governance --summary-only`（仓库根，staged） | **75 issues / exit 0**；FAIL 席位 = Check 16×4（REQ-092 EVD-476/473/423 + FIX-388 EVD-1146）+ Check 17×1（REQ-092 EVD-476）；**无任何 18/18b FAIL** |
| 4 | write-guard | `verify_workflow.py governance-write-guard` | **PASS / exit 0 / 0 issues**（五面全净，含 face-5 受管行族对账） |
| 5 | 受控 A/B census（本审查增设） | staged 代码拷贝 vs HEAD 代码拷贝（byte-hash 校验注入），各自以自身根为 CWD（dogfood 全检查） | **summary 输出逐字节相同、issue 总数相等** → staged diff 对 census 零增量（§4-P2-1） |
| 6 | Check 30/30c 零变化亲验 | 两拷贝 in-process 探针 `check_review_closure()` / `check_review_machine_provenance()` | **逐字段恒等**：Check 30 = WARN / 422 tasks / 0 violations / 30 warnings；Check 30c = WARN / rows_scanned 594 / rows_judged 308 / rows_machine 306 / files_judged 296 / warnings 2 |
| 7 | 全量测试套件 | `python -m pytest skills/.../infra/tests -q`（staged，仓库根） | **7 failed / 4176 passed / 1 skipped**（1406s）。构成归因见 §4-P1/§3-⑦ |
| 8 | manifest / cross-refs / version-consistency | census 全量面板亲见 | Check 11 / 12 / 24 均 [PASS] |

环境勘误（测量纪律）：①temp 目录直跑会因 `HOST_PROJECT_ROOT`（CWD 推导，:144-160）≠ `PLUGIN_ROOT`（脚本位置推导，:130-141）落入 host mode，28c 等 plugin 门控检查休眠（实测 52 vs 75）——HEAD 对照一律以受控 A/B 为准；②`.governance/` 不入 git → worktree/拷贝缺数据文件，数据型测试在拷贝侧的失败原因被环境扭曲（如 FIX-300 #7 两侧失败原因不同），故 §3-⑦ 归因采用「机制隔离 + 稳定性 + numstat 零重叠」判据而非单纯红绿对照。

---

## 2. 五维度审查结论（逐维度）

### 维度 1：正确性 — **通过**（附 P3 观察）

- **三态判据身份复用真实性（复核重点 1）— 证实**：`_hot_status_completion_state`（verify_workflow.py:12392）同模块直接调用 `_status_is_writer_committed_cell`（:10587）——同一函数对象同源消费，非第四份镜像；后者经模块级别名 `_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN`（:10583）绑定真实写入器链对象。本次 diff 未新增任何链副本（逐 hunk 核对：仅消费）。测试 `test_writer_identity_binding_real_writer_product_exempts` 用 `tru.build_candidate_row` 真实产品行绑定 + 剥锚回 guarded。
- **未知不猜分支完备性 — 证实**：空串 / 无锚手写 committed / triaged 带锚 / dev 带锚 / 混合链（🔄→✅）/ 未知 token 六形态全 `""`（GUARDED_SHAPES 矩阵逐一断言）。链序核对 `_STATE_MARKER_CHAIN`（task_row_update.py:287-295）：dev（🔄|进行中）先于 committed → 并存形态保守 guarded；triaged 带锚首命中 triaged → guarded。锚正则 `〔op-[0-9a-f]{32}〕`：31/33 位 hex 因定长 + `\b` 不匹配（畸形不认）。
- **FIX-376 F-3 保守分叉保留 — 证实**：混合链「🔄 … → ✅ 完成」无 ops 锚 → 非 committed、非 ✅ 领头 → guarded（测试 + live FIX-375 实格）；✅ 领头 reopened 链按 FIX-371 语义豁免（既有残余逐字保留）。
- **Check 18 basis 回退列位（复核重点 2）— 正确**：`parts[5]` 与 writer `_build_evidence_row` 的 `cells=[evd_id, task_id, evd_type, description, basis_cell, refs_cell, …]`（governance_store.py:1033-1034）精确对应；与 FIX-368 列布局注释一致（:12714-12719）。description 优先序保持（仅 desc 无匹配才回退，测试覆盖）。`fact_basis` 落 entries（非豁免）列表 → `_current_release_impact_entries` → evidence_domain 数据通路完整。
- **Check 18b 凭证接纳强度（复核重点 3）— 达标**：JSON desc→basis 优先序正确；`machine_attested` 仅在无任何 JSON 时计算；JSON 存在但载荷违规 → 凭证不开脱（测试覆盖）；畸形 op（短/非 hex）/异写器 marker 不认（测试覆盖）。推断词双面扫描（desc+basis，不误放行，测试覆盖）。
- **附加键不改既有消费方语义**：引擎消费面（:15766-15803）只读既有键；`fact_source`/`machine_attested` 为纯附加披露键。

### 维度 2：安全性 — **通过**

- 凭证正则消费 write-guard 权威常量 `re.escape(_GOVERNANCE_STORE_MARKER_PREFIX)` 不重述（FIX-292 单源落实，`_SHARED_NAMES` 身份解析）；op 形态与 `new_operation_id() = "op-" + uuid4().hex`（contracts.py:690-696）精确对应。
- 漂移绑定测试：`_EVIDENCE_MACHINE_CREDENTIAL_RE` 对 `gs._build_evidence_row` 真实产物断言命中——writer marker 漂移即测试红。
- 行级搜索伪造面评估见 P3-2（与 face-5 同粒度且更严；真实性权威按声名归 write-guard faces 2/5）。
- fail-closed 全程保持（未知 → guarded / 无凭证 → 严格 FAIL）；无密钥、无注入面新增。

### 维度 3：可维护性 — **通过**

- 注释与实现一致（三态语义、DEC-241 背景、FIX-292/DEC-168 引用、F-3 分叉保留）；`_SHARED_NAMES` 延迟解析沿用 ADR-016 模式；职责单一；无重复实现。观察 P3-1（clean-step 措辞精度）。

### 维度 4：性能 — **通过**

- 豁免判定 O(n) 集合推导；预编译 regex；无循环内 I/O / N+1；print 标签改动无测试文本锚定（grep 证实）。

### 维度 5：测试覆盖 — **通过**

- 形态矩阵（5 exempted + 6 guarded）+ S_new ⊇ S_old 不变量 + 真实写入器绑定 + 活体定位 + 凭证畸形/异写器拒绝 + JSON 优先与不开脱 + 推断词双面 + 零回归守恒；live 数据面另做穷举差分亲验（§3）。

## AI 代码专项 5 项检查（全项完成）

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | 无（测试内 patch 为合法隔离；产品代码无 mock） |
| 2 | 硬编码返回值 | 无 |
| 3 | 幻觉 API 调用 | 无（所引符号全部实存且实跑通过） |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 无（改动收敛于 DEC-241 消解面） |

---

## 3. 申报独立核验（逐条，含亲跑证据）

| # | 申报 | 核验结果 |
|---|------|---------|
| ① | 三态判据 + 按身份复用 FIX-393 谓词 | ✅ 证实（§2-1） |
| ② | legacy ✅ 前缀语义逐字节保留 | ⚠️ 谓词级有 clean-step 微差（P3-1）；**live 数据零差异**（旧 74 个豁免任务逐一保持） |
| ③ | 豁免差分 S 30→47、drops=∅、expansion=17 全 writer-committed、含窗移第三实例 EVD-1166 | ✅ **穷举差分亲验**：EVD 级 S_old=30 → S_new=47，drops=EMPTY，expansion=17 逐行 state=committed（含 EVD-1166/REL-089、EVD-1164/REL-087）；task 级 74→91 drops=∅ |
| ④ | REQ-092 / EVD-1146 / 混合链保持 guarded | ✅ 亲验：REQ-092 hot cell state=''、EVD-1146（FIX-388）与 EVD-476/473/423 均在 strict entry set；FIX-375 混合链 guarded |
| ⑤ | 16/17 FAIL 席位逐字保持 | ✅ 亲跑：staged/HEAD 对照 5 条 FAIL 线逐字相同 |
| ⑥ | Check 30 恒等（组合②前置） | ✅ 亲验：Check 30/30c 探针逐字段恒等（§1-#6） |
| ⑦ | **「1198P+149S/3F=HEAD 既有（stash 实证）」** | ❌ **不可复现（P1）**：staged 全量实测 **7F/4176P/1S**（1406s）——套件总规模已非申报时点状态（4364 vs 1350 量级）。构成：**archguard 三连（R1/R7/CLI-gate）为 staged 恶化项**（R1：引擎 26318 LOC vs 提交锚 26193，超 +125；HEAD 侧 = 26318−86 = 26232，已超 +39——即 FIX-393/394 集成遗留未 regen，本票 +86 使其恶化，numstat 亲证）；**loop-claims quartet（inventory/adapter/FIX-300×2）**：与 staged diff 零代码路径重叠（grep 证），失败跨数据写入稳定复现，归为既有/数据域（HEAD 侧无法在不触树前提下取得同数据对照——worktree 缺 `.governance`、拷贝缺 `.git`，均已实证扭曲判据，如实记入局限） |
| ⑧ | **「census 75→73（18/18b 1×2 FAIL→0 含窗移 EVD-1166）」** | ❌ **不可复现（P2-1）**：staged 实测 75；受控 A/B 零增量；live Check 18/18b 入集 = **0**（探针：`release task ids: ['DEC-190','EVD-1038',…,'REL-077','RISK-050']`、`window-filtered: 0`）——`_current_release_task_ids` 全表扫「进行中」取到 0.77 时代 token 集（P3-4 既有缺陷），0.89.0 窗口未激活 → 「18/18b 1×2 FAIL→0」在 fixture 面真实成立（HEAD 16F → staged 18P），**不是 live census 事实** |
| ⑨ | 「红 19F→绿 18P+11S」 | ⚠️ 实测 HEAD 16F/4P → staged 18P（各含 9 subtests）；计数口径出入（runner 对 subTest 计数差异），实质（红→绿 + 守恒）成立 |
| ⑩ | diff 规模「verify +104 净 / evidence_domain +57 净」 | ⚠️ numstat 精确值：+109/−23（净 +86）/+52/−5（净 +47）；总 +768/−28 正确 |
| ⑪ | write-guard / cross-refs / manifest / version-consistency 全 exit 0 | ✅ write-guard 亲跑 exit 0；Check 11/12/24 [PASS] 亲见 |

---

## 4. 发现列表（级别/位置/事实/建议）

### P1-1（archguard R1 棘轮恶化未 regen + 「3F=HEAD 既有」申报失实）
- **位置**: 仓库级质量门（`tests/test_archguard_ratchet.py` R1/R7/CLI-gate 三连）+ 任务申报/evidence 记录面。
- **事实**: ①R1 失败消息亲录：`main-file LOC 26318 > anchor 26193 (+125) —— ratchet is only-down; shrink the engine or regen after a sanctioned shrink`；②numstat 亲证本票对引擎净 +86 行；③HEAD 侧引擎 = 26318−86 = 26232（超锚 +39，FIX-393/394 集成遗留——HEAD 本已违反 only-down 棘轮且未 regen）；④全量套件实测 7F 而非申报 3F，且申报「=HEAD 既有」与「archguard 三连恶化 +39→+125」矛盾；⑤census 的 28o 面为 advisory（function_size WARN / `fatal_on_error=false`），LOC 棘轮由 pytest 套件执法——即 M-2「pytest 全绿」口径当前不成立。
- **影响**: 带病扩写主文件：本票在已违规棘轮上再加 +86 行且无 sanctioned regen，违反项目自设的 only-down 棘轮纪律（P-v1 原则 6）。
- **建议（合并前处置，二选一）**: ①Coordinator 授权 archguard baseline regen（0.88.0 M-2「archguard regen 26193」先例流程）并复跑 archguard 三连至绿；②或本票批内收窄引擎增量/把 607 行测试增量保留在独立测试文件（已满足）并显式授权遗留。**申报「3F=HEAD 既有」必须勘正为实测 7F 及上述构成**。

### P2-1（census 申报口径失实——证据勘正义务，非代码缺陷）
- **位置**: 任务申报/evidence 记录面（「census 75→73」「18/18b 1×2 FAIL→0 含窗移第三实例」）。
- **事实**: ①staged census 实测 75 issues（exit 0）；②受控 A/B（唯一变量=代码版本）summary 逐字节相同、总数相等 → census 零增量；③live Check 18/18b 入集=0（探针输出存档）；④审查期间 `.governance/plan-tracker.md`、`evidence-log.md` 被 12:57:52 写入——live 数据移动靶，绝对数随时点漂移，更须以可复现命令+时点口径入账。
- **影响**: 证据账若按原申报入账将携带不可复现数字（违反 P-v1 原则 1）。代码本身**零回归**（A/B 恒等 + 18/18 绿 + 红性绑定实证）。
- **建议**: 勘正为实测口径：「机制消解在 fixture 面实证（HEAD 16F→staged 18P）；live census 零增量（75→75）；18/18b live 入集=0（P3-4 窗口键控既有缺陷所致，0.89.0 窗口激活后首次可见，届时复测）」。另将 diff 规模申报勘正为 numstat 精确值。

### P3-1（legacy 分支 clean-step 微扩张——理论性、方向安全）
- **位置**: verify_workflow.py:12402。**事实**: HEAD 旧谓词对未清洗 cell 直接 startswith(✅)；新实现先剥 backtick/`**` 再匹配 → `` `✅ …` `` 形态理论上新增豁免。方向安全（仅扩张无 drop，⊇ 不受损）；live 136 hot status 零此类形态（expansion=17 全 committed 实证）。**建议**: 措辞修正为「live 行为等价、谓词级含装饰剥离微差」。

### P3-2（Check 18b 行级凭证搜索的伪造面——设计边界内，建议后续加固）
- **位置**: evidence_domain.py:417（对 `raw_line` 全行搜索）。**事实**: 手写行在 description 列内嵌字面 marker 即可被 machine_attested。缓解：face-5 同为行级 substring（:23248）且 Check 18b 更严（op 锚形态）；faces 2/5 台账对账可交叉核验伪造 op id。**建议**: 后续票将搜索 scope 到 basis 列（parts[5]）或消费 face-2 op-receipt 存在性。

### P3-3（fact_len ≥20 可被 marker 尾巴满足——残余风险有限）
- **位置**: evidence_domain.py:348-362 + FACT_BASIS_RE（:13015-13017，捕获至行尾）。**事实**: basis 供事实时 fact_text 含「（机器写入：…）」尾巴，实文近空的行理论上可借尾巴过 ≥20 门槛。缓解：writer 拒空 basis（governance_store.py:1060-1065）。**建议**: 后续票在 `fact_source="basis-column"` 时剔 marker 尾再计长。

### P3-4（`_current_release_task_ids` 窗口键控缺陷——既有，非本票引入；掩盖本票 live 效果）
- **位置**: verify_workflow.py:12412-12425。**事实**: 对任何含「进行中」的 `| ` 表行全表扫取 task token；live 实测返回 0.77 时代 token 集 → Check 18/18b live 入集=0 → 两个严格检查 live 面空转。本 diff 未触碰该函数。**建议**: 立后续票：窗口行锚定（版本规划段 + 状态列）；0.89.0 窗口真实激活时本票 live 效果首次可见，届时复测。

### P3-5（live census 存在 20 条既有 Check-28c FAIL——与本票无关）
- **事实**: 仓库根 staged census 含 20 条 `[FAIL] hot fact-source consistency`（0.88.0 roadmap 行 missing active task REL-091/FIX-373..389 等）。归因：28c 代码路径与本 diff 零交集（`_hot_task_is_delivered`→`_status_cell_is_delivered` 未触碰；受控 A/B 两侧恒等）。**建议**: FIX-395 域承载；申报中「verify 全 exit 0」与「check-governance 零 FAIL」是两回事，避免混读。

### 边缘问题 5 项定级判定（汇总）

| # | 边缘问题 | 定级 | 一句话判定 |
|---|---------|------|-----------|
| 1 | legacy clean-step 微扩张 | P3 | 理论性、方向安全（⊇）、live 零实例——记录即可 |
| 2 | 18b 行级凭证伪造面 | P3 | 与 face-5 同粒度且更严、权威边界已声名——后续加固票 |
| 3 | fact_len 含 marker 尾巴 | P3 | writer 拒空 basis 缓解——后续票剔尾计长 |
| 4 | 窗口键控全表扫「进行中」 | P3 | 既有缺陷、掩盖 18/18b live 面——立票修复 |
| 5 | 28c 20 条既有 FAIL | P3 | 数据态既有、与本票零因果——FIX-395 域承载 |

---

## 5. 硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 = 100% | ✅ |
| 每条发现标注级别 = 100% | ✅（P1×1 + P2×1 + P3×5，全部含位置/事实/建议） |
| 设计一致性（DEC-241/DEC-227/FIX-376 F-3/DEC-168/FIX-292） | ✅ 完成（消费不重述、F-3 分叉保留、S_new⊇S_old、fail-closed 全部成立） |
| AI 五项检查 | ✅ 全部完成 |
| 本任务指定硬门槛（新套件 / check-governance / write-guard 亲跑） | ✅ 全部通过（§1-#1/3/4） |

## 6. 结论

## **APPROVED_WITH_NOTES**（`unresolved_blockers=0`；有条件合并——遗留义务必须入跟踪表）

- **计数**: **P0=0，P1=1，P2=1，P3=5**。
- **裁决理由**: 本票代码（三态判据/basis 列/凭证接纳/豁免面）逐行核验与实跑全部证实，零缺陷、零回归（受控 A/B census 恒等；新套件 18/18 绿且红性绑定实证；write-guard exit 0；Check 30/30c 恒等）。任务指定的三项硬门槛全过，无 P0。P1-1（archguard R1 棘轮 +125 无 sanctioned regen；其中 +39 为 HEAD 既有、+86 为本票净增）属仓库级质量门遗留而非本票代码缺陷，按「P0=0 且 P1>0（有遗留计划）→ 有条件合并」处理。
- **合并附带义务（必须逐条入跟踪表/证据勘正）**:
  1. **（P1-1）** Coordinator 授权 archguard baseline regen（0.88.0 M-2 先例流程）或批内收窄引擎增量，复跑 archguard 三连至绿；`tests/test_archguard_ratchet.py` 当前红 = M-2「pytest 全绿」口径未满足，不得带入 0.89.0 M-2 门。
  2. **（P1-1/P2-1）** 申报勘正：①「3F=HEAD 既有」→ 实测 7F/4176P/1S 及构成（archguard 三连恶化 + loop-claims quartet 既有/数据域）；②「census 75→73 / 18-18b 1×2 FAIL→0」→ 实测 75→75、A/B 零增量、live 入集=0；③diff 规模 numstat 精确值。
  3. **（P3-4）** 窗口键控立票；0.89.0 窗口激活后复测 18/18b live 面。
  4. 审查辅助工件清理（`git worktree remove` + `%TEMP%\fix390_*` 拷贝删除）。
- **复审条款**: 本票为 R0；若 Developer/Coordinator 对 P1-1/P2-1 的处置产生代码变更（如 shrink），按 M7.4 发起 R1 并引用本报告逐条比对。本结论为通过终态，`unresolved_blockers=0`。

## 亲跑命令清单（可复查）

```
python -m pytest skills/software-project-governance/infra/tests/test_fix390_structured_status_judgment.py -v   # 18 passed
python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only             # 75 issues, exit 0
python skills/software-project-governance/infra/verify_workflow.py governance-write-guard                      # PASS, exit 0
python -m pytest skills/software-project-governance/infra/tests -q                                             # 7F/4176P/1S (1406s)
python -m pytest …test_archguard_ratchet.py::R1MainfileBudgetTests::test_r1_passes_on_current_tree -q          # LOC 26318 > 26193 (+125)
git diff --cached --numstat                                                                                    # 109/23, 52/5, 607/0
# 受控 A/B：robocopy×2 → HEAD 代码 byte-hash 注入 → 各自根为 CWD → check-governance --summary-only → 逐字节 diff = 空
```
