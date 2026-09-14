结论：**APPROVED_WITH_NOTES** ｜ `unresolved_blockers=0` ｜ round=1 ｜ prev_report=`docs/reviews/review-REL-077-RELEASE-R0.md` ｜ 机录 round 建议 = `REVIEW-REL-077-R4`

# Review — REVIEW-REL-077-RELEASE-R1（0.81.0 发布候选 · M-3 发布半面**复审** round 1）

- **round**：R1（发布面第 2 轮；release 面自编号 = 1）
- **prev_report**：`docs/reviews/review-REL-077-RELEASE-R0.md`（**已全文通读**，结论 `NEEDS_CHANGE` / blocking = F-01）
- **机录映射**：`.governance/review-REL-077-R3.md`（机器 stub）的 `next_round = REVIEW-REL-077-R4`、`prev_report` 指向 R0 报告 ⇒ 本轮即该 `R4` 轮；release 面报告自编号 = `R1`（两者为同一轮，勿按 R0/R1 字面回填轮次）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（无未解决 BLOCKING finding）——R0 的 **F-01 阻塞项已由 FIX-334 闭环**并被我独立复跑证实；F-02~F-08 全部落地；F-09 部分复现；本轮新裁决 FIX-335 / incident / FIX-336 三项，另出 **5 条 P3 备注**（不阻塞）
- **返回 Coordinator 的结论与本首行同一**：`APPROVED_WITH_NOTES`，`unresolved_blockers=0`

---

## 0. 审查对象、送审版本与审查期边界

### 0.1 送审版本（**审查期内产物发生变动，已记录**）

| 项 | 值 |
|---|---|
| 基线 | HEAD `22cf185982f949839776811d096e70d48beb884f` |
| 送审改动面 | **已 staged 7 文件 / +478 −16**（`git diff --cached --stat`）：`test_dsh_doctor.py`(+66/−1) · `test_archguard_ratchet.py`(+44/−2) · `release-checklist-0.81.0.md`(+48/−6) · `rollback-plan-0.81.0.md`(+31/−7) · `CHANGELOG.md`(+2) · `README.md`(+4) · 新增 `docs/reviews/review-REL-077-RELEASE-R0.md`(+299) |
| 审查期内变动 | **`docs/release/release-checklist-0.81.0.md` 工作树副本于 19:32:21（我审查进行中）被再次改动**（未 staged，`git status` = `MM`），新增「取数快照声明（REVIEW-FIX-334-CODE-R0 **P2-1**）」段并修订归因分级 2/3；另出现未跟踪 `docs/reviews/review-FIX-334-CODE-R0.md`(19:31:50) |
| 我的处置 | 已**读入并纳入本轮裁决**（该改动方向 = 增加披露，与我复核一致）；据此出 **F-R1-03**（残留措辞 + 送审版本需显式冻结）。**我的判定同时覆盖 staged 版本与工作树副本** |

### 0.2 审查期并发事实（非我写入）

- 我全程**只读**：唯一写入 = 本报告文件。所有测试命令 `DSH_HOME` 重定向至 `%TEMP%` 新建目录并逐条上报（§7）。
- `check-release` 运行**未**改动任何文件；`git status` 在我全部命令前后一致（除上述并发编辑与 peer 报告）。

---

## 1. R0 findings 逐条比对（M7.4 step 4.6）

| ID | R0 级别 | R0 诉求 | **本轮裁决** | 事实依据（我的独立复核） |
|---|---|---|---|---|
| **F-01** | **P1 blocking** | `test_dsh_doctor.py:632` 渲染 sha256 硬钉腐朽（候选树必失败 + 钉死检出路径） | **已修复（充分，非弱化）** | ① 修法 = 派生（`checks.version.extract_skill_version` 读 `SKILL.md` frontmatter，DEC-096 权威源）+ parity（新解释器同树再渲染一次，`assertEqual` 逐字节）+ 「渲染非空」守卫；**全文已无 ≥64 位 hex 字面量**（grep 零命中）⇒ 版本轴与路径轴双双不再腐朽。② `python -m unittest …test_dsh_doctor`（`$tmpHome` 隔离）= **Ran 86 tests OK**，两次独立复跑 39.165s / 41.127s ⇒ 文档「实测 86，此前所载 70 为陈旧计数」**成立**（R0 建议里的「应 70 OK」系旧计数）。③ **反相红绿（内存探针，零落盘，我亲自构造）**：候选渲染 = `6caf90fec1f2773eaa0128f0fa5c7a7795b512c8a36d603f5cd6e939ff48e55d`（**16796 bytes**，与 Gate 11 逐字节相符）；模板版本行变异 ⇒ 派生断言 `assertIn("（v0.81.0）")` **红**；契约 token 变异（`own.render.tokens` 去掉 skills token）⇒ 渲染 `""` ⇒ `assertTrue(rendered)` **红**；复原 ⇒ **绿**。④ 旧钉值 `00e0d330…3723` ≠ 现渲染 ⇒ **修前该断言在本树必然红**（缺陷成立）。⑤ 路径轴代码实证：`launch.py:467-473` 把 `__GOVERNANCE_REPO_ROOT__` 代入 `ROOT.resolve()`、`:1711-1718` 同源 ⇒ 副本搬迁即改哈希 |
| **F-02** | P2 | 「重取全量原始失败清单逐条贴出」被标已履行但清单不存在 | **已修复（清单存在且可复核）** | ① 新增「**Gate 10 明细 —— 全量失败清单**」段：候选 38 块（36 failures + 2 errors）**逐条列出 13 行**，我核行内块数合计 = 22+2+5+1+1+1+1+1+1+1+1 = **38** ✓；pristine 37 = 共有 29 + 特有 8（7 ERROR + 1 FAIL）✓ 自洽。② **逐块独立复核（隔离复跑，最重两行）**：`test_pre_commit_review_evidence` = Ran 11 / FAILED(failures=**24**)，按用例分布 = 9 例各 2 块（其中 2 例各 4 块）= **22 块**（= 行 #1 逐字相符）+ `test_replay_real_evidence_log_fix260` **2 块**（= 行 #2 逐字相符）⇒ **22 + 2 = 24 全等**。③ 归因方向**已更正**：「原稿方向写反」→ 明写 `test_the_python_render_is_the_launchers_own_output` **候选树同路径必失败**，只有「pristine + 原检出路径」可满足 ✓ 与 §F-01⑤ 的代码事实一致 |
| **F-03** | P2 | 窗口计数「31+1」实测应为 33/34 | **已修复（发布文档面）；残留 1 处治理记录面 → F-R1-01** | ① 措辞改为**不写死**：`rollback-plan` 写「计数不写死，M-5 现场取 `git rev-list --count`」+ 写作时点实测 34(tip)/33(候选点)；checklist Gate 14 同口径。② 我实测 `git rev-list --count d87ead8..a89341e` = **33**、`d87ead8..22cf185` = **34** ⇒ 与文档**完全一致** ✓（分解 31 + `5e6d8c7` + `a89341e`(+`22cf185`) 亦相符）。③ **残留**：`.governance/evidence-log.md:2087`（EVD-1034）`gates."14_rollback_plan"` 仍为 `"区间 = d87ead8..候选打包提交，31 commits + 本提交"`（并发编辑后我**再次**确认未变）——正是 R0 F-03 三站点中的第 3 处 |
| **F-04** | P2 | 回滚终点是候选提交而非发布 tip，且无演练记录 | **已修复（记录存在 + 结构强佐证；复跑受本轮只读边界限制，见备注）** | ① 区间已改 `d87ead8..<发布 tip>` 并写明终点理由 ✓。② 新增 §4.1「revert 干跑记录」：两次（候选点 exit 0 / 0 冲突 / **80 路径**；tip exit 1 / **3 冲突** / 35 路径 = 5 D + 27 M + 3 UU）✓ 记录存在。③ **我逐项验证该记录的数字可从树结构精确导出**：`git diff --name-status d87ead8..a89341e` = **80 路径 = 39 A + 41 M** ⇔ 干跑 A 的「39 D + 41 M」（revert 后 A→D、M→M）✓；`git show --name-status a89341e` = **35 文件 = 5 A + 30 M** ⇔ 干跑 B 的「5 D + 27 M + 3 UU」（5 个新增→D；30 个修改中恰 3 个变 UU）✓；`git show --name-only 22cf185` = **正是报告所列的 3 件套** ✓ 且三件套在区间内**先新增**（`af2b58c` #18 / `c15f6df` #19 / `9e80c6a` #20）**后被 `a89341e` 修改**（M）⇒ 与区间外修改形成真「双改」冲突 ⇒ porcelain `UU` 为**正确编码** ✓。④ 主工作树零 revert 残留（`git status` 无任何 revert/冲突痕迹）✓ 与「主工作树零试跑」自洽 |
| **F-05** | P2 | CHANGELOG 缺显式 breaking 块；README 未同步 B-2 | **已修复（另出 2 条 P3 精度建议 → F-R1-04）** | ① `CHANGELOG.md:37` 已含 `**Breaking changes：无**（VERSIONING.md L11 口径：无接口删除/重命名、无默认行为破坏、无 Gate 语义或治理字段格式变更）` + `**行为变更（升级须知，2 项）** B-1/B-2` ✓，与既有范式同形（`:118` 0.79.0、`:212`、`:269`、`:331` 均以 `**Breaking changes：无**` 收尾）。② `VERSIONING.md:11` 实测 = 「删除/重命名 MUST 规则、改变 Gate 行为语义、改变 governance 文件字段格式」⇒ **「无 breaking」判定成立** ✓；`:83`（1.0.0 前 Minor 有限 Breaking 必须显式标注）由该显式结论行满足 ✓。③ README **中英两处**限定已加，且与代码逐条相符：`write_side_refusal`（`launch.py:851-911`）拒 unset（:878）/ blank（:882）/ 落入或包含真实 home（:907）；`--install` 与 `--sync` **同一 dest**（:1749-1755）⇒ 两者同守卫；`--uninstall`（:779）同守卫；`--dry-run` **在守卫之前 return 0**（:635-648 / :759）⇒ 放行 ✓；拒绝码 = `exit 2`（`SMOKE_EXIT_REFUSED=2`，`_refuse_write` :913-918）✓ |
| **F-06** | P2 | Gate 6/7 仍是 V8 在制品预检值 + 残留 ⟦⟧ 占位 | **已修复（回填值经我独立复跑逐项成立）** | ① Gate 6 回填值：我实跑 `verify_workflow.py archguard-ratchet` = **R1 PASS 24412 ≤ anchor 24412 · R2 47 ≤ 47 · R3 12 edges · R4 1299 ≤ 1299 · R5 84/84 + 71/71 · R6 196 Δ0 · R7 deterministic=True; committed==fresh True · Result: PASS (0 violations)** ⇒ 与文档**逐字相符** ✓。② **锚点变更成因复核**：`anchor_loc` = `24412` @ `5e6d8c7`/`3074120`/`a89341e`/`22cf185`（`d87ead8` = `24204`）；`git log -S'"anchor_loc": 24412'` = **`3074120`（V8）** ✓；`git diff 3074120..a89341e` 对该 JSON **只改 `generated.git_head`（210b200→5e6d8c7）**、未改 `anchor_loc` ✓ ⇒ 文档「预检 24405 取自 V8 在制品工作树、冻结态自 3074120 起即 24412」**成立**；我还独立**数出 `verify_workflow.py` 物理行数 = 24412** ✓（R1 的 loc 侧同源）。③ Gate 7 回填值：我实跑 `check-dsh-boundary` = `[PASS] K-2: outside-contract host literals: 0 (**11** declared consumer(s) scanned)`、`[PASS] K-8: … every guard reference resolves (**55** test file(s), 71 segment(s), 84 command key(s))`、`Result: PASS — 0 failing criterion(a)` ⇒ **K-2 11 / K-8 55 成立** ✓（K2_CONSUMERS 元组我数得 11 项；V8 提交信息自述「K-2 扫 11 消费者」佐证）。④ 占位：`docs/release/` 全量 ⟦⟧ = **2 处**，仅 `:133`（真机回贴面，允许）+ `:153`（冻结纪律引文，允许）✓ Gate 6/7 占位已清除 ✓ |
| **F-07** | P3 | 180s 超时被说成「时序噪声」不准确 | **已修复** | 代码事实逐条相符：`_RELEASE_GATE_TIMEOUT_DEFAULT = 180`（`verify_workflow.py:5946`）、`_RELEASE_GATE_TIMEOUT_ENV = "SPG_RELEASE_GATE_TIMEOUT"`（:5947）、「unit tests」面**只跑单模块** `test_verify_workflow.py`（:6024）✓。我的 `check-release` 复跑原样打印 `unit tests: … timed out after 180 seconds（exit=None）` ✓ ⇒ 属**确定性预算/口径不匹配**，措辞已改正 ✓ |
| **F-08** | P3 | checklist M-1 结语与 M-2 表矛盾 | **已修复** | `release-checklist` 尾注改为「M-2 门禁实测**已回填**（Gate 6/7 由 FIX-334 期在候选树复跑回填、Gate 10 含逐条失败清单与 pristine 对照），**真机三项回贴仍为待办**」✓ 不再自相矛盾 |
| **F-09** | P3 | Gate 13 归因未复现 | **部分复现（结论不变）→ 归因拆分见下** | ① **已复现**：`governance health` 96 issues、`unit tests` 180s 超时、`loop runtime claim gate` semantic **BLOCKED**（`AUTHORITY_SOURCE_OCCURRENCE: .governance/decision-log.md found 0` + `AMBIGUOUS_SUBJECT_RELATION` + 3×`UNSUPPORTED_AFFIRMATIVE`）、`dsh upgrade regression` PASS、`loop fuse block` PASS、`Result: FAILED - 7 issue(s)`（= 新增段所述 7 ✓）。② **被 flag 文本的来源已复现**：`AMBIGUOUS_SUBJECT_RELATION` 所引即 `release-checklist` **Gate 13 开头行**，且该行确由 **`22cf185`** 写入（`git show 22cf185 -- …checklist` 显示该 `+| 13 | … **已完成（候选提交 a89341e 之后复跑…）**` 行）✓ ⇒ 「非本次修复作者」成立。③ **未复现**：该「类+文件」组合「在 pristine `5e6d8c7` golden 清单中同样存在」（需 pristine 树扫描，超出本轮只读边界）⇒ 维持文档级。④ **补充不一致**：候选侧三例定向重跑我实测 `Ran 3 tests → FAILED (failures=1, errors=2)`（`#9 fixture_identity…=ERROR`、`#10 identity_host_source_drift…=FAIL`、`#11 claim_command…=ERROR`），与文档所记 pristine `failures=2, errors=1` 在 **F/E 分类计数上不同**（三例「均红」一致）。建议 M-4 以**同一条命令并列两侧原始输出**，不要用「同结果」的逐字表述 |

**新引入（regression）**：**未发现**——本轮改动面无产品运行时行为变化（2 个测试文件 + 4 份文档），且 `check-release` 静态面在我复跑中**全 PASS**（`release docs` / `changelog` / `release lineage` / `archive integrity` 均 PASS）⇒ FIX-334/335 的文档改动**未引入门禁回归** ✓。

---

## 2. 本轮新增事实裁决（非 R0 退回项）

### 2.1 FIX-335 —— 同族第 4 例版本钉腐朽（决策 ①②③）

| 问 | 裁决 | 依据 |
|---|---|---|
| ① 缺陷是否成立 | **成立（同一腐朽族，R0 未列出）** | 机制实证：`_entry_expired` 判 `current ≥ expire_version`，`apply_exemptions` 的版本取自 `SKILL.md` frontmatter（`archguard_ratchet.py:185-202 / 689`）；fixture 钉 `expire_version:"0.81.0"` 而本版版本 = `0.81.0` ⇒ 降级为 `EXPIRED:0.81.0` ⇒ `assertEqual(effective, [])` 必失败 ⇒ **候选侧必红 / pristine(0.80.0) 侧可满足**。我用**内存版本覆盖探针**复现：真实 0.81.0 下 fuse `0.81.0` ⇒ **不抑制（红）**，fuse `0.81.1` ⇒ 抑制（绿） |
| ② 修法是否未弱化断言语义 | **未弱化** | 与该模块 HEAD 版逐字比对：**断言本体完全未动**（`assertEqual(effective, [])` + `assertTrue(disclosures)`；`assertEqual(len(effective), 1)` + `assertIn("OVER-ALLOWANCE", …)`），**只改 fixture 的 fuse 取值**；派生值 = `extract_skill_version(SKILL.md)` 的 `patch+1` 并 `assertGreater(derived, current)`；版本不可解析 ⇒ `assertRegex` **fail-closed 报错**（不静默）。**到期路径覆盖未丢**：模块内仍有 `test_expired_exemption_no_longer_suppresses`（历史值 `0.78.1`，断言 `EXPIRED`）⇒ EXPIRED 语义仍有独立用例（我实跑 `ExemptionMechanismTests` = **Ran 4 OK**，含该例） |
| ③ 反相证据是否足以证明断言非恒真 | **充分（我已独立复现，非仅采信报告）** | 内存探针（`read_skill_version` 覆写为 0.82.0，模拟副本 bump，零落盘）：fuse `0.81.0` ⇒ **红**；fuse `0.81.1`（冻结旧 fuse）⇒ **红**；fuse `0.83.0`（交付派生 fuse）⇒ **绿**；且在**所有**状态下「超额度仍 FAIL」恒成立（over-allowance 断言 = 1 条有效违例）⇒ 断言确为**真测试**、fuse 确为**载荷件**（非恒真、非恒假）。整模块复跑 = **Ran 38 OK**（125.196s）✓ 与 EVD-1037 的 `Ran 4 OK / Ran 38 OK` 相符 |
| 残留（P3，不阻断） | 见下 | ① `:159` 的 `expire_version="0.78.1"` **自带显式 `version=(0,78,1)` 实参**（自洽、不会腐朽），但行内注释 `# == current skill version` 已成陈旧散文；② `:457` 的 `0.81.0` 不参与任何到期判定（`build_baseline` carryover 探针，断言仅计数）⇒ 惰性、不腐朽；③ `:425` 的 `0.78.1` 属**历史到期值**，单调安全 ✓（与 EVD-1037 的「历史到期值一律保留」裁决一致）。另：peer 的 P3-1（:457 未来若引入到期剪枝会复活）我同意为**潜在**风险，可并入 FIX-336/337 批次登记 |

### 2.2 incident（FIX-335 隔离变量名冲突 → `DSH_HOME` 指向 `C:\Users\peter`）

- **裁决：发布文档无需披露**（与 Coordinator 判断一致），**但附 3 项条件**：
  1. 事件属**派发纪律事项**（pwsh 保留只读 `$HOME` 与 `$home =` 写法静默冲突 ⇒ 重定向失效），已机录 incidents + 登记 FIX-337 ⇒ 处置面正确 ✓；
  2. 「零影响」论证我**独立抽查成立**：`archguard_ratchet.py` 对 `DSH_HOME` / `.dsh` / `USERPROFILE` / `HOME` **零命中**；受影响命令 = `ExemptionMechanismTests`（**4 例 / 0.001s，纯进程内，无子进程**）⇒ 确无 DSH 代码路径被执行、无读写发生 ✓；
  3. **但**：凡发布证据中声明「隔离 DSH_HOME」的条目必须**真的**重定向过 —— 本事件的可核查边界仅限该次命令；**若同类事件落在门禁/验收命令上（例如 28u 冒烟的 `real-home writes: 0` 声明），则必须披露**（级别建议 P2：它会直接否定一条隔离声明），纯派发纪律类不入发布文档。FIX-337 落地前，派发 prompt 的隔离命令统一 `$tmpHome` 且执行当下逐条上报（peer T-6 同）

### 2.3 FIX-336（`test_dsh_compat` 在 `discover -s …/tests -t .` 下整模块不可载入）

- **裁决：「全量基线口径非全量」不损害 Gate 10 结论的诚实性**（缺口事实已披露；但我要求**就地补限定语**，见 F-R1-02）。
- 三条我实测的事实：
  1. **已披露**：Gate 10 明细段行 #12 逐字写明「该模块的 120 用例在本模式下整体未被收集（"Ran 2983" 不含它们…）」，归因分级第 3 条 ② 复述；
  2. **缺口不隐藏失败面**：该模块在窗口内**被修改**（`git diff --name-status d87ead8..a89341e -- …test_dsh_compat.py` = `M`），但我以「顶层 = tests 目录」口径复跑 = **Ran 120 tests OK**（10.431s）⇒ 被排除的 120 例是**绿的**；
  3. **缺陷成立且双侧同现**：`discover -s …/tests -t . -p test_dsh_compat.py` ⇒ `ModuleNotFoundError: No module named 'dsh_fixtures'`（Ran 1 / errors=1，exit 1）✓。
- **要求（P3，非阻塞）**：把限定语写进 Gate 10 **行的标题/结论句**（例：`全量测试基线（本口径不含题 #12 的 test_dsh_compat 120 用例，见明细段）`）——现状只在同格明细段出现，只读结论句的读者会得到「2983 = 全量」的印象。

---

## 3. 本轮新增 findings（全部 P3，不阻塞）

### F-R1-01（P3）R0 F-03 的第 3 站点未随修：EVD-1034 `14_rollback_plan` 仍是旧口径
- **位置**：`.governance/evidence-log.md:2087`（EVD-1034）`gates."14_rollback_plan"` = `"已交付且可执行（区间 = d87ead8..候选打包提交，31 commits + 本提交）"`
- **依据**：并发编辑后我**再次**核读，该字段未变；发布文档面（checklist Gate 14 / rollback-plan §2.1 + 尾注）已改为 33/34 且不写死 ✓
- **影响**：低（EVD-1036 已记录更正后的 33/34；发布文档亦不再引用该字段）——但机器可读字段与冻结产物口径相反，未来跨行核对会复现同类争议
- **建议**：在 EVD-1034 或新增一行 EVD 内加一句 supersede 声明（`F-03 更正：终值见 EVD-1036 / rollback-plan §2.1`）

### F-R1-02（P3）三处计数口径漂移（均已在文内披露成因，但未就地收口）
- **① Gate 10 两次取数未对帐**：行首 `failures=38, errors=2`（2026-09-13）vs 明细段 `failures=36, errors=2`（2026-09-14）。**我给出对帐**：差额 = **2** = ①`test_triage_write_guard…test_live_plan_tracker_flags_only_known_m1_rows`（FIX-328/330 修复）+ ⑬`test_dsh_doctor` 渲染硬钉（FIX-334 修复）——两者均在同行点名，故 **38 − 2 = 36 自洽**；建议补一句并标注「两次取数**非块对块可比**」（活体 `.governance/` 数据面在窗口内变动，见行 #2/#3；`governance health` 88→96 同源）。
- **② Gate 13 并存 6 / 7 issue 计数**：行首结论 = `FAILED — 6 issue(s)`，FIX-334 段 = `FAILED - 7 issue(s)`。我实测**当前 = 7**，新增项 = `AMBIGUOUS_SUBJECT_RELATION`（本 checklist 自身 Gate 13 开头行，`22cf185` 文本）✓ 与披露相符；建议 headline 改用最新值并保留 6 作历史。
- **③ `静态面 13/13 PASS` 标签与实测项数不符**：我实跑打印 **17 项 PASS**（静态组 14 项 + `changelog` + `dsh upgrade regression` + `loop fuse block`），文档括注亦列 17 个名称 ⇒ **结论（全 PASS）无误、标签计数陈旧**。
- **性质**：均属「历史值/现值并存」，方向是**低估或中性**（无 FAIL→PASS 包装）；且 FIX-334 段已写「**M-4 以当场复跑值为准**」⇒ 非阻塞。
- **建议**：M-4 复跑时**整体刷新一次**为单一口径（一行一句话把三处旧值标为「写作时点」，现值就地更新）。

### F-R1-03（P3）审查期内产物变动 + 并发编辑残留措辞
- **事实**：`docs/release/release-checklist-0.81.0.md` 于 **19:32:21**（我审查进行中）被改（`git status` = `MM`；mtime 对比 peer 报告 `review-FIX-334-CODE-R0.md` 19:31:50）——承接该 peer 审查的 **P2-1**（Gate 10 明细 #4/#5 未反映 FIX-335 已修）。
- **内容评价**：方向 = **增加披露**（新增「取数快照声明」+ 归因分级第 2 条改「本版已修 2 项」+ 第 3 条注明原表述作废）⇒ 与我的复核一致（FIX-335 后 `Ran 38 OK`），**不改变本轮结论**。
- **缺陷**：第 3 条 ① 修订后仍以「…**建议登记独立 FIX**；」收尾，与前句「原『需另立 FIX』的表述**作废**」**自相矛盾**（编辑残留）。
- **建议**：M-5 前删去该尾句；并在送审/机录时**显式声明送审版本 = working tree（含该未 staged 改动）**，以免「冻结产物」语义再被质疑。

### F-R1-04（P3）两处措辞精度（R0 F-05 的可选项）
- **①** `CHANGELOG:37` 括注含「无**默认行为破坏**」，与紧邻「**行为变更（升级须知，2 项）**」张力（B-2 改的正是**文档化的默认路径**：README 手工安装）。建议改为「无 MUST 规则/Gate 语义破坏；下述 2 项为用户可感知行为变更」。
- **②** README 中英限定只覆盖「`~/.dsh` 及其子目录」，而 `launch.py:907` **同时拒绝「包含真实 home（父目录）」**（如 `DSH_HOME=C:\Users\<u>`）——保守方向、拒绝消息可行动，但建议把两种形态都写出，避免用户按字面理解后撞 `exit 2`。

### F-R1-05（P3）F-09 残留：候选/pristine 定向重跑的 F/E 分类计数不同
- 见 §1 F-09④：候选侧我实测 `Ran 3 → failures=1, errors=2`，文档记 pristine `failures=2, errors=1`；三例「均红」一致，但「同结果」不宜逐字使用。建议 M-4 同命令并列两侧原始输出。

---

## 4. 五维度结论

| 维度 | 结论 | 依据摘要 |
|---|---|---|
| **1. 发布就绪** | **通过** | 静态面全 PASS（含 `release docs` / `changelog` / `release lineage` / `archive integrity`，我复跑）✓；RISK-050 打开（不声明关闭）✓ / RISK-036 打开 ✓；真机三项**未回贴**且全库无「通过」声明（`:133` ⟦待用户回贴⟧）✓ |
| **2. 质量门禁** | **通过（既有失败已实测归因）** | 执行面 3 项 FAIL 全部复现且可归因：`governance health` 96 issues（活体治理记录面）/ `unit tests` **180s 预算 < 单模块墙钟**（确定性口径，非 flake，`:5946/:6024` 代码实证）/ `loop runtime claim gate` BLOCKED（新增项 = 本 checklist 的 Gate 13 行）；`dsh upgrade regression`（隔离 smoke）与 `loop fuse block` PASS ✓。**本版改动面零运行时行为变化** |
| **3. 回滚能力** | **通过（记录可复核；未由我复跑）** | §4.1 两次干跑记录存在，其**每一数字可从树结构精确导出**（80 = 39A+41M；35 = 5A+30M，3 UU = `22cf185` 改的同一三件套）✓；主工作树零残留 ✓；`git revert <range>` 形式在 `git 2.52.0.windows.1` 可用（R0 已核）；**复跑受本轮只读边界限制**（见 §6/§8） |
| **4. 用户影响** | **通过** | Breaking 显式声明 + B-1/B-2 作为升级须知列出（CHANGELOG + feature-flags §2 + README 中英）✓；拒绝消息自含可行动指引（把 `DSH_HOME` 指向临时目录）✓；数据面无不可逆改动（预设为可再生渲染产物）✓ |
| **5. 版本号合规 + no-overclaim** | **通过** | `version consistency` PASS（声明面全 0.81.0）✓；MINOR 论证与 L11 口径一致 ✓（新增能力面 + 无 Major 级破坏）；`core/releases/0.81.0.json` 仍为 candidate 态、`candidate_commit a89341e` ✓；无「真机通过」overclaim ✓ |

---

## 5. 硬门槛逐条裁决（`agents/release-reviewer.md`）

| 门槛项 | 阈值 | 本轮裁决 |
|---|---|---|
| 发布检查清单全部 PASS / 逐项有可复核证据 | = 100% | **满足**：14 项全部有可复核证据——Gate 6/7 由我复跑原值 ✓、Gate 10 含 38 块逐条清单（最重两行逐块相符）✓、Gate 13 静态 13/13（实打印 17 项全 PASS）✓、Gate 14 区间/计数与实测同源 ✓ |
| 回滚方案存在且已验证 | = 已验证 | **满足**：§4.1 有命令/退出码/冲突面/路径数记录，且签名与树结构逐项吻合；**复跑**受本轮只读边界限制（未执行 revert/worktree），建议 M-4/M-5 由具写权限者再跑一次并留证（不改变本判定） |
| CHANGELOG 用户视角完整 | 关键段全部覆盖 | **满足** |
| breaking changes 已标注 | = 100% | **满足**：`BREAKING：无` 显式结论行 + 2 项行为变更升级须知（另见 F-R1-04① 措辞建议） |
| Feature Flag 关闭验证 | 全部通过 | **满足**：新增 opt-in 开关 = 0；B-1/B-2 回退路径 = 版本回滚（已写明）；开关缺口登记 FIX-324（本批未触碰开关面） |

**⇒ 硬门槛 5/5 通过；无未解决 BLOCKING finding ⇒ `APPROVED_WITH_NOTES` / `unresolved_blockers=0`。**

---

## 6. 独立复现声明（我亲自复核的数字/文件）

**亲自执行（命令结果，非文档采信）**：

1. `test_dsh_doctor`：**Ran 86 tests OK**（两次；39.165s / 41.127s），`$tmpHome` 隔离 ⇒ F-01 修复有效、文档「70 系陈旧计数」更正成立。
2. `test_archguard_ratchet`：**Ran 38 OK**（125.196s）；`ExemptionMechanismTests` = **4 OK**（含 `test_expired_exemption_no_longer_suppresses`）⇒ FIX-335 有效且到期路径覆盖未丢。
3. **渲染反相探针（内存，零落盘）**：`16796 bytes` / `6caf90fe…e55d`；模板版本行变异 ⇒ 派生断言红；契约 token 变异 ⇒ 渲染 `""` ⇒ `assertTrue(rendered)` 红；复原 ⇒ 绿；旧钉值 `00e0d330…3723` ∉ 现渲染。
4. **fuse 反相探针（内存，零落盘）**：真实 0.81.0 {`0.81.0` 红 / `0.81.1` 绿}；副本 0.82.0 {`0.81.0` 红 / `0.81.1` 红 / `0.83.0` 绿}；over-allowance 恒 FAIL。
5. `archguard-ratchet`：R1 **24412** / R2 47 / R3 12 / R4 1299 / R5 84-84 + 71-71 / R6 196 Δ0 / R7 deterministic + committed==fresh / PASS 0 violations（**Gate 6 逐项复现**）；另独立数出 `verify_workflow.py` **物理行数 24412**。
6. `check-dsh-boundary`：PASS 0 failing；**K-2 = 11 consumers**、**K-8 = 55 test files / 71 segments / 84 keys**、K-7 NOT_RUN（**Gate 7 逐项复现**）。
7. `check-release --version 0.81.0 --require-changelog --lineage-mode candidate`：**静态面全 PASS**（14 项打印）+ `changelog` PASS + `dsh upgrade regression`（隔离）PASS + `loop fuse block` PASS；执行面 FAIL = `governance health`(96) / `unit tests`(180s 超时) / `loop runtime claim gate`(BLOCKED)；`Result: FAILED - 7 issue(s)`；**exit 1**。
8. `test_pre_commit_review_evidence`：Ran 11 / failures=**24**；逐用例块数 = 9 例各 2 块（2 例各 4 块）= **22** + `test_replay_real_evidence_log_fix260` **2** ⇒ 与 Gate 10 行 #1/#2 **逐块相符**；失败原因 = Windows `bash`→`wsl.exe`（原始 mojibake 输出可见）。
9. 定向三例 `test_verify_workflow`（既有基线族）：`Ran 3 → failures=1, errors=2`；`#9 ERROR` / `#10 FAIL` / `#11 ERROR`。
10. `test_dsh_compat`：`discover -t .` ⇒ `ModuleNotFoundError: dsh_fixtures`（1 error）；`-t <tests 目录>` ⇒ **Ran 120 OK** ⇒ FIX-336 缺口为纯收集面、**无隐藏失败**。
11. git 计数与结构：`rev-list --count d87ead8..a89341e`=**33** / `..22cf185`=**34**；`diff --name-status d87ead8..a89341e` = **80（39 A + 41 M）**；`show --name-status a89341e` = **35（5 A + 30 M）**；`show --name-only 22cf185` = **3 件套**；三件套新增提交 `af2b58c`/`c15f6df`/`9e80c6a`（区间内 #18/#19/#20）。
12. 锚点链：`anchor_loc` = 24204@`d87ead8` → **24412**@`5e6d8c7`/`3074120`/`a89341e`/`22cf185`；`log -S` 归属 = `3074120`；`3074120..a89341e` 仅改 `generated.git_head`。
13. 文档面：`docs/release/` ⟦⟧ = **2 处**（真机面 + 纪律引文）；`test_dsh_doctor.py` **无 ≥64 位 hex 字面量**；`VERSIONING.md:11/83`；`CHANGELOG:37` 及 0.79.0/0.78.1/0.78.0 范式行；`launch.py:635-648 / 655-657 / 759 / 779 / 851-911 / 913-918 / 1749-1755`；`verify_workflow.py:5946/5947/6024`；`K2_CONSUMERS`（11 项）。
14. `.governance`：EVD-1034 / EVD-1036 / EVD-1037 全文、incident 文件、`review-REL-077-R3.md`（机录 stub，`next_round=REVIEW-REL-077-R4`）。
15. 无副作用核查：全部命令前后 `git status --porcelain` 一致（除 §0.1 的并发编辑与 peer 报告）；`__pycache__` 未见为跟踪面变化。

**我未能独立复现（标注为文档级 / 边界外，且不作为本轮 blocking 依据）**：

- 全量 `discover`（2983 例两树原始输出）——按指令**未跑**（≈13 分钟）；以行级/块级复跑替代（§6.8/6.9/6.10）；
- `revert` 干跑本身（需在隔离 worktree 执行写操作，超出本轮只读边界）——以其**结构签名可精确导出**替代；
- pristine `5e6d8c7` 树上的任何实测（需建 worktree）：pristine 侧 37 块构成、pristine 三例 F/E 分类、`AMBIGUOUS_SUBJECT_RELATION` 组合在 pristine golden 清单中的存在性；
- `check-archive-integrity` 精确计数（Hot 89 / Archived 91 / Index 1119 / Total 180）——`archive integrity` 项在 `check-release` 中 **PASS** 已复现，精确计数未复核。

---

## 7. 命令上报（全部只读；唯一写入 = 本报告）

| # | 命令（摘要） | 退出码 | 结论摘要 |
|---|---|---|---|
| 1 | `git status --porcelain` / `log --oneline -3` / `diff --cached --stat` / `diff HEAD --stat` | 0 | HEAD `22cf185`；staged **7 文件 +478 −16**；与任务给定改动面一致 |
| 2 | `git rev-list --count d87ead8..{a89341e,22cf185,HEAD}` | 0 | **33 / 34 / 34** ✓ |
| 3 | `git diff --name-status d87ead8..a89341e` + 状态分组 | 0 | **80 = 39 A + 41 M**（⇔ 干跑 A） |
| 4 | `git show --name-status/--name-only {a89341e,22cf185}` | 0 | `a89341e` **35 = 5 A + 30 M**（含 3 件套 M）；`22cf185` **恰 3 件套** |
| 5 | `git log --diff-filter=A -- <三件套>` / `rev-list --count d87ead8..<新增提交>` | 0 | 新增于 `af2b58c`/`c15f6df`/`9e80c6a`（区间内 #18/#19/#20） |
| 6 | `git show <c>:…/architecture-baseline.json`（5 时点）+ `git log -S'"anchor_loc": 24412'` + `git diff 3074120..a89341e -- <json>` | 0 | 24204→**24412**（归属 `3074120`）；a89341e 仅改 `generated.git_head` |
| 7 | `python -c`（读 `verify_workflow.py` 物理行数） | 0 | **24412** |
| 8 | `python -m unittest skills.software-project-governance.infra.tests.test_dsh_doctor` ×2（`DSH_HOME=%TEMP%\spg-r1-doctor-*`） | 0 / 0 | **Ran 86 OK**（39.165s / 41.127s） |
| 9 | `python -m unittest …test_archguard_ratchet`；`….ExemptionMechanismTests -v`（`…spg-r1-arch-*`） | 0 / 0 | **Ran 38 OK**（125.196s）；**Ran 4 OK** |
| 10 | `python -m unittest …test_pre_commit_review_evidence`（×2） | 1 | Ran 11 / failures=**24**；块分布 22 + 2（#1/#2 相符）；`wsl.exe` 缺失原文 |
| 11 | `python -m unittest -v` 定向 3 例（`FIX300DualCaliber…` ×2 + `LoopRuntimeClaimAdapter…`） | 1 | Ran 3 → failures=1 / errors=2（#9 ERROR、#10 FAIL、#11 ERROR） |
| 12 | `python -m unittest discover -s …/tests -t . -p test_dsh_compat.py`；同 `-t <tests 目录>` | 1 / 0 | **ModuleNotFoundError**（1 error）；**Ran 120 OK** |
| 13 | `python verify_workflow.py archguard-ratchet`（`…spg-r1-gates-*`） | 0 | R1 **24412**≤24412 / R5 84-84+71-71 / R7 committed==fresh / **PASS 0 violations** |
| 14 | `python verify_workflow.py check-dsh-boundary`（`…spg-r1-gates2-*`） | 0 | K-2 **11** / K-8 **55**·71·84 / **PASS 0 failing** |
| 15 | `python verify_workflow.py check-release --version 0.81.0 --require-changelog --lineage-mode candidate`（`…spg-r1-rel-*`） | 1 | 静态/其余 PASS（17 项）；执行面 3 FAIL（96 / 180s / BLOCKED）；**FAILED - 7 issue(s)** |
| 16 | `python -c` 渲染反相探针（内存；`…spg-r1-rev-*`） | 0 | 16796B / `6caf90fe…e55d`；三态红-红-绿 |
| 17 | `python -c` fuse 反相探针（内存；`…spg-r1-rev2-*`） | 0 | 0.82.0 下 {0.81.0 红 / 0.81.1 红 / 0.83.0 绿} |
| 18 | `git cat-file -e d87ead8:…test_dsh_contract.py` / `…5e6d8c7:…` | 128 / 0 | 0.80.0 时**不存在**、`5e6d8c7` 存在 ✓（佐证 rollback-plan 第 6 行） |
| 19 | 只读 grep/读：⟦⟧ 扫描 · 64-hex 扫描 · 测试内版本字面量 · `DSH_HOME` 命中 · `K2_CONSUMERS` · write-op 扫描 · `launch.py`/`verify_workflow.py`/`VERSIONING.md`/`CHANGELOG` 定向读 | 0 | 见 §1/§2 各条（均为实测判定依据） |
| 20 | `Get-Content -Encoding UTF8` 只读治理文件（EVD-1034/1036/1037、incident、`review-REL-077-R3.md`）+ `Get-Item` mtime | 0 | 机录轮次映射；并发编辑时点（19:31:50 / 19:32:21） |

**未执行**：任何 `git add/commit/restore/reset/checkout/stash/revert`、任何 worktree 创建、任何全量 `discover`、任何仓库外或真实 home（`%USERPROFILE%\.dsh`）读写。每条测试命令均以 `$tmpHome`（非保留名）重定向 `DSH_HOME` 至 `%TEMP%` 新建目录并打印首行。

---

## 8. 发布就绪裁决

**裁决：可进入 M-4 / M-5（transition + annotated tag）**——R0 的唯一 blocking 项 F-01 已闭环并经我独立复跑证实；全部 5 项硬门槛通过；无未解决 BLOCKING finding。

**M-4/M-5 前的最小待办（全部 P3，不阻断；建议一次收口）**

| # | 动作 | 覆盖 | 判据 |
|---|---|---|---|
| 1 | M-4 复跑 `check-release` 与全量测试，并**以当场值为唯一口径**刷新 Gate 10（38/36）与 Gate 13（6/7）与「静态面 13/13」标签 | F-R1-02 / F-09④ | 三处旧值就地标注「写作时点」，现值唯一 |
| 2 | 补 EVD 行 supersede 声明：EVD-1034 `14_rollback_plan` 旧口径作废 | F-R1-01 | 机器记录与冻结产物同源 |
| 3 | 删去 checklist 归因分级第 3 条 ① 的「建议登记独立 FIX」尾句；确认送审版本 = working tree（含该未 staged 改动） | F-R1-03 | 行内无自相矛盾；送审版本显式 |
| 4 | （可选，措辞）CHANGELOG「无默认行为破坏」改为「无 MUST 规则/Gate 语义破坏」；README 补「包含真实 home 的父目录亦被拒」 | F-R1-04 | 与代码行为逐字一致 |
| 5 | （可选）目录级重跑一次隔离 `revert` 干跑并留证（由具写权限者执行；我受只读边界限制未跑） | F-04 复跑项 / peer T-2 | 演练记录从「结构可佐证」升为「本轮实测」 |
| 6 | FIX-336 收集面缺陷按独立任务修复时，同步把限定语写进 Gate 10 行标题/结论句 | 新增事实③ | 「全量」口径自知 |

**真机三项**仍由用户手动执行并回贴；**回贴前任何文档不得声明其通过**（本轮已核：现无此类声明）。M-5 打 tag 前 MUST 复跑一次门禁并以当场值为准。

---

*审查方：Release Reviewer Agent（只读；唯一写入 = 本报告）｜审查对象版本：0.81.0（REL-077）｜基线 `22cf185` + staged 7 文件（+478/−16）+ 审查期工作树改动（checklist「取数快照声明」）｜结论：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**｜机录建议：`review-record --task REL-077 --round 4 --result APPROVED_WITH_NOTES`（`unresolved_blockers=0`；报告 = `docs/reviews/review-REL-077-RELEASE-R1.md`；prev = `docs/reviews/review-REL-077-RELEASE-R0.md`）*
