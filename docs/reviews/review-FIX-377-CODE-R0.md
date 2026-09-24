# review-FIX-377-CODE-R0 — 调查报告结论核验（代码审查 · R0——调查票轻量审查）

> **Round 声明**：R0（首轮审查；FIX-377 无前轮 REVIEW 报告）。审查对象 = Developer 调查报告（EVD-1144 机录 + 会话申报）的**结论可复现性与归属正确性**——Part 1（FACTS_PRINT_TOTAL 1306→1316 +10 归属）与 Part 2（28 失败 + 2 subtests 四类归类）+ 前提修正 + 修复候选 5 项。
>
> **审查方式**：轻量复现抽查（不重跑 979s 全量）——独立 census walk、a6d3bfb diff 逐行核验、决定性污染组合复跑、LRC/archguard/static-pin 定点单跑、git 祖先关系核验。审查全程零产品代码修改、零 `.governance/` 写入；本文件为唯一输出。审查者探针存放 `%TEMP%\fix377_review_probe\`（仓外）。控制台中文偶发 GBK 渲染 mojibake（FIX-278 已知面，仅显示层，locator/code 字段均 ASCII 精确）。
>
> Governance: always-on × maximum-autonomy | stage: 维护与演进（第 11 阶段），G11 passed | 4 risks（父会话热数据，本席为子审查席不重复展开）

---

## 0. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **0** |
| P3 讨论 | **3**（F-1 / F-2 / F-3） |

调查报告的全部可抽查结论在轻量复现口径下**逐项复现成立**：Part 1 归属（+10 全归 a6d3bfb，10/10 行号精确）、Part 2 四类归类（③ 决定性 3F+1P 复现；② archguard +72/LRC 触发文档轮换复现；④ stale 豁免+未豁免 pin 复现；① 时间敏感证伪复现）、前提修正（008efa6 ∈ 0.87.0 窗口 + 四致因 commit 全部 post-tag）、归属完整性（census 跳变唯一落点 + 零残余）、调查票边界（工作树干净、零 FIX-377 commit）。两条推翻性结论（FIX-339 假设证伪 / 前提修正）均经独立实验复核成立。P3×3 为证据完备性备注，不影响任何结论方向。

---

## 1. 审查证据基线

| 输入 | 说明 |
|------|------|
| 被审申报 | EVD-1144（evidence-log L2616，治理存储机器写入 op-b9784aa384314a36bc6ddb16853f8fc7）+ 任务简报全文申报 |
| Developer 工件（旁证，均独立复验） | `%TEMP%\fix377\`：full_suite.txt（**30 failed, 3839 passed, 2 skipped, 512 subtests passed in 979.22s**）、file_alone.txt（test_verify_workflow 单文件 **3 failed, 926 passed**）、census_walk.py 等探针 |
| 前轮审查旁证 | review-FIX-376-CODE-R0.md L129-130（12674 pin WARN + 12550 pin + stale-12375 实测）、L157（28 基线失败「未深挖」移交 + `[] == []` 探针样例）；review-REL-086-RELEASE-R2.md（532 文件零 ragged 冻结时点自证） |
| 审查者独立复现 | 下表 §2 全部命令为本席独立执行（非采信申报） |

---

## 2. 抽查结果逐项记录（命令 + 输出摘要 + 判定）

### 2.1 Part 1 — FACTS_PRINT_TOTAL 1306→1316 +10 归属 ✅ 成立

**① 独立 census walk**（`count_print_calls` AST 口径，archguard_ratchet.py L497-521；blob 经 `git show <sha>:<engine>` 落 %TEMP% 后计数）：

```
6e25753: total=1306   (0.86.0)
5e56021: total=1306   aa72c37: total=1306   dd4537b: total=1306
a6d3bfb: total=1316   ← 唯一跳变点 +10
80d71b5: total=1316   008efa6: total=1316   602f8f3: total=1316
3d31c49: total=1316   d6dd300: total=1316   WORKTREE: total=1316
```

与申报 census walk **逐点全等**；+10 跳变唯一落点 = a6d3bfb。引擎触达 commit 全集（6e25753..HEAD 共 9 个）已被上述锚点全覆盖（008efa6 未触引擎——regen 只改基线文件，与 `git log 6e25753..HEAD -- verify_workflow.py` 枚举一致），中间无未采样缝隙。

**② a6d3bfb diff -U0 逐行核验**（`git show a6d3bfb --unified=0 -- .../verify_workflow.py` + hunk 行号映射）：新增 print **恰 10 处**，与申报 10/10 行号**逐一精确命中**：

| 申报行号 | diff 实测新行 | 内容（均为 Check 16/17 豁免披露输出） |
|---|---|---|
| _run_full_engine_checks L15514/15516/15518 | L15514/15516/15518 | `Historical exempted (FIX-371/DEC-227 ✅-terminal, skipped): {ga_exempted}` + task_id 行 + `... and N more` |
| _run_full_engine_checks L15548/15550/15552 | L15548/15550/15552 | 同族（ui_exempted） |
| cmd_check_goal_alignment L21464/21466 | L21464/21466 | 同族（exempted） |
| cmd_check_user_impact L21502/21504 | L21502/21504 | 同族（exempted） |

**③ HEAD 基线钉零漂移**：test_archguard_ratchet.py:87 `FACTS_PRINT_TOTAL = 1316` ✓；RUN7 棘轮活体输出 `[R4] PASS print total 1316 ⇔ baseline 1316 (per-function ratchet)` ✓。**判定：归属成立，10/10 无残余。**

### 2.2 Part 2③ — 测试基础设施缺陷（污染）✅ 决定性复现成立

机制代码面核验：污染者 test_governance_store.py:1461-1469 进程内 `vw.main(["--project-root", str(self.tmp), ...])`；被重绑面 verify_workflow.py:234-272（`global HOST_PROJECT_ROOT/GOVERNANCE_DIR/EXECUTION_PACKET_PATH/SAMPLE_PATH/SESSION_SNAPSHOT_PATH/EVIDENCE_PATH/RISK_PATH/ARCHIVE_*/REQUIRED_FILES` 全局写、**无恢复**）；该测试 setUp/tearDown（L1452-1459）仅管理 tmp 目录、不快照全局。与申报逐位一致。

复现实验（pytest，单进程按参顺序执行，`-p no:cacheprovider`）：

| RUN | 组合 | 结果 | 判定 |
|---|---|---|---|
| RUN1 | 污染者单跑 | **1 passed** in 0.13s | 污染者自身健康 ✓ |
| RUN2 | 3 受害者单跑（HotFact ×2 + ExternalProject sentinel） | **3 passed** in 0.15s | 非固有损坏、非时间敏感 ✓ |
| RUN3 | 污染者→3 受害者同进程 | **3 failed, 1 passed** in 1.37s | **与申报 3F+1P 逐位一致** ✓ |

RUN3 失败签名：受害者 issues 列表为空（引擎全局被重绑至已删除 tmp 的 .governance → 热事实扫描静默空转）；ExternalProject 失败 `AssertionError: [] == []` @ test_verify_workflow.py:10798——与 review-FIX-376 L157 留存探针样例**同型**（该轮「FIX-339 时间敏感」线索实为此污染，见 §2.5①）。

**③ 面算术闭合**：file_alone 对照（Developer 工件，本席复核 FAILED 行）test_verify_workflow 单文件仅 3F（FIX300 ×2 + LoopRuntimeClaimAdapter ×1，均为 ② LRC 家族真实树数据耦合）→ 全量同文件 20F，差 17 = 16 HotFact + ExternalProject；**quickscan 单跑 1 passed（0.11s）** → quickscan 亦为纯污染受害者。③ = 16 HotFact + ExternalProject + quickscan = **18 节点** ✓；28 = ②8 + ③18 + ④2 ✓。

### 2.3 Part 2② — 环境语义 8+2 ✅ 成立（LRC 轮换 + archguard +72 均 reproducer）

**① archguard**（RUN7，3 tests 单跑 → **3 failed**，CliGate 失败消息内嵌真实 CLI 全量输出）：

```
[R1] FAIL  mainfile loc 25534 ⇔ anchor 25462 (only-down)      → +72
[R4] PASS  print total 1316 ⇔ baseline 1316                    → 1316 对齐未被破坏
[R7] FAIL  regen deterministic=True; committed==fresh False    → 未 regen
[VIOLATION] R1 ... LOC 25534 > anchor 25462 (+72)
[VIOLATION] R7 baseline-stale ... engine changed without regen
Result: FAIL (2 violation(s)) — fatal ratchet gate（CliGate exit 1 != 0）
```

逐 commit 净 LOC 拆分核验（`git show <sha> --shortstat -- verify_workflow.py`）：FIX-373 +9/−2=**+7**、FIX-374 +42/−5=**+37**、FIX-375 +21/−2=**+19**、FIX-376 +32/−23=**+9**，合计 **+72** = R1 锚差，与申报拆分**逐位精确**。

**② LRC 家族真实树 fail-closed**（RUN8：test_loop_runtime_claims L938 单跑 77.67s → **failed**）：

```
assertEqual("PASS", report.verdict) → 'PASS' != 'BLOCKED'
findings（恰 2 条）:
  1. ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row
     @ docs/reviews/review-REL-086-RELEASE-R2.md            （0233f49 提交）
  2. UNKNOWN_STATE_PREDICATE
     @ docs/reviews/review-FIX-376-CODE-R0.md, locator=accounting:29:1（3d31c49 提交）
```

与申报「触发文档轮换至 REL-086-R2 ragged row + FIX-376 L29」**逐位一致**（locator 29:1 即申报 L29）。轮换叙事自洽：R2 报告冻结时点自证 532 文件零 ragged（L17/L45），0233f49 把 R2 报告自身入库后成为新触发文档。RUN11：FIX300 ×2 单跑 **2 failed**（`'PASS' != 'BLOCKED'`）→ ② 成员坐实（单跑即败，非污染受害者）。

### 2.4 Part 2④ — 账本过期 2 ✅ 成立

- checks/version.py:205 `STATIC_PIN_EXEMPTIONS` 定义；**:281 `(12375, "0.87.0", _REASON_FIXTURE_ROW_TEXT)` stale 条目存在** ✓
- test_verify_workflow.py:12550 `... | fixture task | - | 0.87.0 | ...` 与 :12674 `"| ✅ 已交付 | EVD-997 / 0.87.0 |"` 两字面量在位 ✓（12375→12550 漂移 = FIX-373 测试插入；12674 = FIX-376 新增——漂移归因与两 commit 触达面一致，且 review-FIX-376 L129-130 已独立实测同面 WARN）
- RUN6：2 tests → **2 failed**，消息精确：`stale ledger row .../test_verify_workflow.py:12375 (token 0.87.0) → re-audit` + `[WARN] static-version-pin: ...:12550 pins the active version "0.87.0" literally → derive it instead ... or register a reasoned (line, token, reason) exemption in checks/version.py STATIC_PIN_EXEMPTIONS` ✓

### 2.5 两个推翻性结论复核（MUST #2）✅ 均成立

**① FIX-339 时间敏感假设证伪**：RUN4 HotFactSourceConsistencyTests 整类隔离单跑 **22 passed / 0.23s**（覆盖全量连败的 16 节点），运行时钟时点与 Developer 复跑（13:53+）及全量失败跑（11:39）均不同 → 通过/失败与时钟无关、与污染者存在性严格相关（RUN2/RUN3 对照）。review-FIX-376 L157 的时间敏感猜想（探针样例 `[] == []` @ test:10798）经 RUN3 证实为污染受害者签名——**假设证伪成立**，推翻方向正确。

**② 前提修正（28 败全形成于 0.88 窗口，0.87 发布面干净）**：
- `git cat-file -t 008efa6` = commit；= **REL-084 M-2**（2026-09-21 13:23 +0800），message 自载 `pytest 3847P/0F` + `archguard regen+FACTS 1316 对齐`；EVD-1131 = M-2 门禁实测机录在案 ✓
- 祖先关系：`merge-base --is-ancestor 008efa6 602f8f3` = 0（M-2 ∈ v0.87.0，peel=602f8f3f90b6…与申报一致）✓；四致因 commit 04b7a42/3c3218d/0233f49/3d31c49 `is-ancestor 602f8f3 →` 均 exit 0（**全部 post-tag**）✓
- 008efa6 diff：`FACTS_PRINT_TOTAL = 1306 → 1316`（M-2 regen）+「census truth re-alignment / +10 ATTRIBUTED TO PRE-EXISTING … registered as FIX-377 (0.88) for bisect」注记（test_archguard_ratchet.py L80-87）——**0.87.0 regen 的「pre-existing 漂移」定性正是被本调查翻转的错误归属**，翻转证据（census walk + diff 10/10）已闭环 ✓
- 拦截缺口申报：EVD-1128 记 FIX-371 验证面 =「54P 复绿+主运行面实跑」——**未含 archguard 棘轮**；a6d3bfb 自身未 regen 基线（基线对齐延至 008efa6 且归属错注）→ 缺口叙事与机录一致 ✓
- 注：3847P/0F 未在本席独立复跑（979s 超出轻量口径）——见 F-2。

### 2.6 归属清单完整性（MUST #1/#6）✅ 10/10 无残余

census 跳变唯一落点 a6d3bfb（§2.1①）+ diff 新增 print 恰 10 处且行号全中（§2.1②）+ HEAD census = 1316 = 基线钉 = R4 PASS（§2.1③）→ **+10 全量归属、零未归属残余、零多归属**。每一归属均有 commit/命令双重证据。

### 2.7 调查票边界（MUST #4）✅ 属实

`git status --porcelain` = 空（审查前基线与终态两次核验）；`git log --all --grep FIX-377` 仅 FIX-376 message 引用（**零 FIX-377 commit**）；EVD-1144 自载「verify_workflow.py 零修改」；本次全部复现实验为只读 + %TEMP% 仓外探针，pytest 产物（.pytest_cache/__pycache__）均 git-ignored。**零产品代码修改声明属实。**

---

## 3. MUST 关注四项逐项裁决

| # | 关注项 | 裁决 |
|---|--------|------|
| 1 | 证据链是否支撑 | ✅ 每个归属有 commit+命令双证据；申报数字（1306/1316/10/8+2/18/2/72/7/37/19/9/3847P）全部对上机录或本席复现 |
| 2 | 两条推翻性结论复核 | ✅ 均独立复核成立（§2.5）；方向正确、影响面陈述准确（直接影响后续票：FIX-A 候选因此升为唯一 0F 门禁阻断项） |
| 3 | FIX-A P1 定级合理性 | ✅ **合理**（§4 论证） |
| 4 | 调查票边界 | ✅ 工作树干净、零 FIX-377 commit、实验全仓外（§2.7） |

---

## 4. 修复候选 5 项复核（可追溯性 + 定级）

| 候选 | 定级 | 可追溯证据（本席复现） | 复核意见 |
|------|------|------------------------|---------|
| FIX-A 测试隔离 | P1 | RUN1/2/3 决定性 3F+1P + 18 节点阻断面（§2.2）+ 重绑无恢复代码面（L234-272 / L1452-1459） | **P1 定级合理**：(a) 18 节点每次全量跑确定性破坏；(b) 唯一阻断 0.88.0 M-2「pytest 0F」门禁的 bucket（② 为合法数据演化的 fail-closed 面、④ 仅 2 行账本）；(c) 修复面小且纯测试侧（setUp 快照/tearDown 恢复，或 subprocess 化——同类 test_engine_subprocess_* 兄弟用例已是现成形态），不触引擎重绑 API；(d) 不足 P0：无产品代码缺陷、失败已披露入账非静默。落地时建议顺带补 F-3 具名 |
| FIX-B 账本卫生 | P2 | RUN6 双失败消息 + version.py:281 stale 条目 | 与 version-plan-0.88.0.md L75 已登记的 M-1 输入（12550 派生化 + 12375 stale 复核 F-12）同面——落地时对齐既有登记，避免双入账 |
| FIX-C 棘轮 regen | P2 | RUN7 R1+72/R7 stale（净拆分 7/37/19/9 精确） | +72 全部来自 0.88 合法交付（TDD 红绿记录在案），regen 属「合法交付后基线跟进」非违规吸收；时点由 Coordinator 裁决申报合理；regen 遵守 all-changes-first（FEAT-055 先例）+ lineage 注记纪律（FACTS 注记先例已在案） |
| FIX-D 文档清账 | P2 | RUN8 双触发文档 finding（R2 ragged row + FIX-376 L29） | 补充设计线索：FIX-376 触发点是审查报告 **code fence 内引用引擎实现代码**（L29-38 ```python 块）被 claim 扫描器当作文档命题命中——FIX-D 可在「改写文档措辞」与「扫描器 fence 感知」间裁量，后者语义面更大需独立评审 |
| 流程改进 | P3 | EVD-1128（54P 未含棘轮）+ 008efa6 错注归属 | 拦截缺口真实：FIX-371 交付面未含棘轮 + M-2 regen 时以未验证的「pre-existing」定性吸收 +10。建议方向：写器交付票的验证套件清单纳入 archguard-ratchet（与 96 键快照同级的机判面），regen 时 census 归属必须带 census walk 证据 |

---

## 5. 发现清单

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-1 | P3 | EVD-1144 / full_suite.txt | ② 的「+2 failed subtests」未在留存工件中逐项定位：full_suite.txt 短摘要仅含计数算术（30 failed = 28 条 FAILED 汇总行 + 2 个失败 subtest），且本席单跑复现的 ② 全部 8 个测试成员均无 subtest 失败计数——2 个 subtest 的测试级归属为申报推断（算术成立、方向合理） | 后续票（FIX-B/FIX-D）处置时以 `-rA`/subtest 明细补一次定位入账 |
| F-2 | P3 | EVD-1131 / 008efa6 | 前提修正中「008efa6 实测 3847P/0F」未在本审查独立复跑（979s 超出轻量口径）——采信机录（EVD-1131 + commit message）+ 结构性论证（M-2 ∈ v0.87.0、四致因 commit 全部 post-tag、census 008efa6=1316） | 0.88.0 M-2 全量跑将自然复验此前提；无需独立动作 |
| F-3 | P3 | EVD-1144 | 决定性复现组合（污染者+三受害者 3F+1P）未具名 4 个 node id——本席以推导 trio（2 HotFact + 1 ExternalProject）复现成功且 quickscan 判别吻合，机制与数字全对上；缺具名属可复现性完备性而非真实性缺陷 | 调查票收口时把组合 4 个 node id 补入 EVD-1144 或报告正文 |

---

## 6. 硬门槛裁决

| 门槛项 | 要求 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞数 | = 0 | 0 | ✅ |
| 5 维度覆盖 | 100% | 正确性=结论逐项复现成立（§2）；安全性=零产品代码修改、实验全仓外只读、无敏感数据（§2.7）；可维护性=归属账本/lineage 注记纪律评估（§4 FIX-C）；性能=0.21s 决定性复现 + 979s 全量成本说明（§1/§2.2）；测试覆盖=拦截缺口核验（§2.5② EVD-1128） | ✅ |
| 每条发现有级别 | 100% | F-1/F-2/F-3 均 P3 | ✅ |
| 设计一致性 | 已完成 | 申报与 EVD-1144/version-plan-0.88.0 A3 登记/棘轮注记三方一致（§1/§2.5②） | ✅ |
| AI 代码专项 5 项 | 全部完成 | 审查对象为调查报告非代码变更；零产品代码 diff（git status 干净 + 零 FIX-377 commit）→ mock 残留/硬编码返回/幻觉 API/未实现 TODO/过度实现 **五项均 N/A（有据）** | ✅ |

**事实依据红线自查**：本报告每条结论均指向 §2 命令+输出；「3847P/0F」一处明确标注未独立复跑（F-2 采信机录），无任何未验证内容写成已通过。

---

## 7. 遗留项列表

| 遗留项 | 级别 | 关闭时点 |
|--------|------|---------|
| F-1 subtest 定位 | P3 | FIX-B/FIX-D 处置时顺带 |
| F-2 3847P/0F 独立复验 | P3 | 0.88.0 M-2 全量跑自然复验 |
| F-3 组合 node id 具名 | P3 | 调查票收口时补入 EVD-1144 |

---

*review-FIX-377-CODE-R0 冻结（2026-09-24，Code Reviewer Agent——调查票轻量审查）。审查基线：HEAD d6dd300（工作树干净）。证据：本席独立 census walk（11 点）/ a6d3bfb diff -U0 行号映射（10/10）/ pytest 定点复跑 RUN1~RUN8+RUN11（3F+1P 决定性组合在内）/ git 祖先关系核验 / EVD-1128·1131·1144 机录对读 / Developer 工件 %TEMP%\fix377\ 旁证复核。本报告为审查席独立结论；修复候选立项与调度权在 Coordinator。*
