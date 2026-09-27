# REVIEW-REL-094-M1R-R0 — M-1R 基线再生独立审查报告

| 项 | 值 |
|---|---|
| 任务 | REL-094 M-1R 基线再生（0.91.0 发布窗 M-2 后续处置，先审后提交） |
| 审查者 | Code Reviewer Agent（独立，未参与开发） |
| 轮次 | R0 |
| 审查对象 | 工作区未提交 diff，3 文件，+30/−17（numstat 实测：baseline +2/−2、manifest +19/−8、test +9/−7；任务书申报 manifest 拆分 +20/−7 与实测差 1 行，总数一致） |
| 审查基点 | HEAD = bc3f05276318b94f97d2f17aaa26c2bb644e90f1（REL-094 M-1 提交） |
| **verdict** | **APPROVED_WITH_NOTES** |
| **unresolved_blockers=0** | （结构字段：无未解决 BLOCKING finding） |
| 发现统计 | P0=0 · P1=0 · P2=0 · P3=3（全部非阻塞） |
| 日期 | 2026-09-28 |

---

## 0. 审查结论（先行）

**APPROVED_WITH_NOTES**（通过终态，`unresolved_blockers=0`）。六项审查清单全部 PASS，全部验证命令由本审查者亲跑并留痕（§3）。授权链三引用实体均核实存在；prior 块与已提交旧值逐字节一致；新钉哈希双路验证（本审查者独立 sha256 重导 4/4 + 机器测试重导）全绿；regen 字节级幂等；loop_runtime_claims 本次亲跑 PASS，Developer「不可复现+机本地敏感」归因与独立观测一致，未发现任何掩盖痕迹。三条 P3 均为注记/命名类观察，不要求修改。

---

## 1. 审查清单逐项裁决

### 清单 1 — 零功能源码：**PASS**

证据：`git diff` 全量逐行读取（留档 `$env:TEMP\rel094_m1r_diff_before.txt`）+ `git status --porcelain`（仅 3 个 M 文件，无未跟踪文件）。

| 文件 | 变更定性 |
|---|---|
| `core/architecture-baseline.json` | 纯数据：`generated.git_head` e61e2678→bc3f0527、`r1_mainfile_budget.anchor_loc` 26358→26385。其余 561 行未动（全文比对） |
| `infra/fixtures/m0/manifest.json` | 纯数据：pin_revision.sources 双源重钉（section 描述、line_span、content_sha256、file_sha256）+ 新增 rebaseline 溯源块。fixtures/frozen_revision/consumers/change_rule 均未动 |
| `infra/tests/test_archguard_ratchet.py` | 纯数据面：冻结字面量 `assertEqual(..., 26358)`→`26385` + 注释块改写。无任何断言逻辑、控制流、辅助函数改动 |

任何功能语义改动：**无**。git_head 实测等于当前 `git rev-parse HEAD`（bc3f0527…）✓。+27 增量算术自洽（26385−26358=27）✓。

### 清单 2 — regen 正确性：**PASS**

亲跑记录（本审查者执行，cwd=仓库根）：

1. **幂等性**：`python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet --regen`
   - exit code 0，输出 `Result: REGENERATED`，R1 anchor loc 26385 / R4 print total 1318 / git head bc3f0527 / exemptions carried 1
   - 再生前后 `architecture-baseline.json` SHA256 逐字节相等（`885A0FDB…5E20B87` == `885A0FDB…5E20B87`，IDEMPOTENT: True）
   - `git status --porcelain` 再生后仍只有原 3 文件——REGENERATED 未引入任何新差异
2. **R1/R7/CliGate 定向**：`python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_archguard_ratchet.py" -v`
   - **Ran 38 tests in 138.328s — OK**（全模块，R1/R7/CliGate 为其子集）
   - R1MainfileBudgetTests（含 test_r1_passes_on_current_tree / 负对照×2）：绿
   - R7ReproducibilityTests 4/4 逐条 `... ok`（含 test_r7_double_build_byte_identical、test_r7_committed_baseline_matches_fresh_regen、双篡改负例）
   - CliGateTests 4/4 逐条 `... ok`（green_on_current_tree / red_on_tampered / fail_closed_on_missing / regen_writes_idempotent_bytes）
   - 部分测试名行因 stdout 交错「... ok」显示不齐，以末尾 `Ran 38 / OK` 汇总为准（unittest 无失败即 OK）

### 清单 3 — M0 重钉自证：**PASS**

1. **溯源块完整性**：`pin_revision.rebaseline.last` 含 `at: 2026-09-28`（=本日，实测 `Get-Date`）、`task`（REL-094 M-1R）、`authorization`、`prior[2]`（双源旧 span + 旧 content/file sha256）。
2. **prior 块逐字节比对**：程序化比对 `git show HEAD:…manifest.json` 的旧 pin 值 vs worktree prior 块——`behavior-protocol.md [512,556]` 与 `SKILL.md [223,230]` 两源的 span/content_sha256/file_sha256 全部 `== HEAD old: True`。旧值未被转写或截断。
3. **授权链引用核实**：
   - `DEC-266`：`.governance/decision-log.md` L208 存在（FEAT-072 契约设计裁决，2026-09-27）✓
   - `REVIEW-FEAT-072-R0`：`docs/reviews/review-FEAT-072-DESIGN-R0.md` 存在（git log bc3f052 收编记录一致）✓
   - `REVIEW-FIX-399-R0`：`docs/reviews/review-FIX-399-R0.md` 即 `review-FIX-399-CODE-R0.md` 存在 ✓
4. **新钉哈希双路验证**：
   - 独立重导（本审查者按 manifest `span_hash_recipe` 自行实现 sha256）：behavior-protocol.md span[522,566] content 与 file 两哈希、SKILL.md span[225,232] content 与 file 两哈希——**4/4 match: True**
   - 机器重导：`M0FixtureManifestTests.test_pin_revision_hashes_still_resolve` … ok（该测试按同 recipe 重导全部钉哈希）
5. **亲跑 M0FixtureManifestTests 全类**：`python -m unittest discover -s …/infra/tests -p "test_contracts.py" -k M0FixtureManifestTests -v` → **Ran 5 tests — OK**（含 fixture 冻结面、pin wellformed、hash resolve、consumers 声明）

重钉理由合规性：钉的目的是拦截**未授权**漂移；FEAT-072（DEC-266 链）与 FIX-399 均为授权修改，随链重钉并留 prior 存档，符合 DEC-262② sanctioned regen 策略与 0.90 先例（archguard 两轮 regen）。与 0.90 的 M0-pin 披露式处理区分正确：本批无未授权漂移掺入。

### 清单 4 — loop_runtime 归因可信性：**PASS（本次亲跑 PASS）**

亲跑：`python -m unittest discover -s …/infra/tests -p "test_loop_runtime_claims.py" -k LoopRuntimeClaimTests -v` → **Ran 24 tests in 131.837s — OK**，含 `test_real_repository_inventory_complete_and_within_budget ... ok`。

按清单约定：本次定向 PASS → Developer「两次 PASS 不可复现 + host `.governance` 机本地热文件敏感性（FIX-240 已注记）」的归因与独立观测**一致成立**。本审查者在干净时序下单次即 PASS，表明该 claim 存在环境敏感性而非稳定 FAIL——与 Developer 申报的方向吻合；无掩盖迹象（FIX-240 注记在案、未重写 claim 语义、未放宽断言）。不构成停止条件⑥。如实留痕：本报告仅记录单次运行结果，不做通过率外推。

### 清单 5 — 冻结字面量同步：**PASS**

- test 文件 diff = 字面量 `26358`→`26385`（1 处 assertEqual）+ 注释块改写；`self.assertEqual` 精确相等语义未弱化（等强度替换，非放宽为区间/regex）
- 残留扫描（grep 26358|26385 全 skill 树）：`26358` 仅存于 L486 历史谱系注记「prior 26358 at the 0.89.0 release-gate regen」——正确语境；无陈旧断言残留
- 注记内容与实况对账：26385 ✓（baseline L17 + regen 实测）、+27 ✓、git_head bc3f0527 ✓、「R4 print census unchanged at 1318」✓（baseline `r4_print_orchestration.total=1318` + 测试常量 `FACTS_PRINT_TOTAL = 1318` 一致；design_anchor_note 中「1,311」为 0.80 时代历史注记，非当前值，无冲突）
- test_metadata_contract（含该字面量的测试）在全模块跑中绿

### 清单 6 — check-governance：**PASS**

亲跑：`python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only`

```
Governance: 20 issues
[FAIL] 28s: Governance Data Size (FIX-160): .governance/evidence-log.md 1741479 bytes (1700.7 KB)
[WARN] 2:  Risk Staleness: 3 stale risk(s)
[WARN] 14: Structural Validity: 450 structural issue(s) (0 blocking)
[WARN] 15: Commit Scope Verification: 2 scope discipline issue(s)
[WARN] 24: Version Consistency: plan-tracker workflow version=0.90.0, expected=0.91.0
```

唯一 FAIL = **28s**（evidence-log 超限，既有、与本 diff 无因果）；WARN 2/14/15/24 均为既有 advisory（24 系本窗口 plan-tracker 尚未 bump 至 0.91.0 的已知态，随发布收尾处理）。**无新增 FAIL** ✓。

---

## 2. 发现列表（全部非阻塞）

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| N1 | P3 | `test_archguard_ratchet.py` L488-489 附近 | 注释改写换行残留孤行「# instead: the」独立成行，阅读略断（编辑机制的排版残留，非语义问题） | 随下次触碰该块的授权变更顺手重排，不单独开票 |
| N2 | P3 | `test_archguard_ratchet.py` L9（diff 外，既有） | 模块 docstring 仍写「R4 total print calls must equal 1,315 (facts §3.1)」，而权威常量 `FACTS_PRINT_TOTAL = 1318`（其下演化链注释已完整追溯 1315→1318） | 既有陈旧 docstring，不在本批范围；登记为下次触碰时的低优先整理项即可 |
| N3 | P3 | `manifest.json` rebaseline.authorization | 引用写作「REVIEW-FEAT-072-R0」，落盘工件名为 `review-FEAT-072-DESIGN-R0.md`（git log 收编记录可消歧，无实际歧义） | 后续 manifest 引用建议写全文件名，减少检索成本 |

---

## 3. 亲跑命令与结果汇总

| # | 命令 | 结果 |
|---|------|------|
| 1 | `git diff`（全量留档）+ `git status --porcelain` | 3 文件 +30/−17，纯数据面；无未跟踪文件 |
| 2 | `git rev-parse HEAD` | bc3f05276318b94f97d2f17aaa26c2bb644e90f1（= baseline git_head） |
| 3 | `verify_workflow.py archguard-ratchet --regen` | exit 0；REGENERATED；前后 SHA256 逐字节相等；git status 不变 → **幂等** |
| 4 | `unittest discover -p "test_archguard_ratchet.py" -v` | **38 tests OK**（R1/R7/CliGate/R4/R2/R3/R5/R6/Exemption/BaselineArtifact 全绿） |
| 5 | `unittest discover -p "test_contracts.py" -k M0FixtureManifestTests -v` | **5 tests OK** |
| 6 | `unittest discover -p "test_loop_runtime_claims.py" -k LoopRuntimeClaimTests -v` | **24 tests OK（131.8s）**——含 real_repository_inventory |
| 7 | 独立 sha256 重导（span recipe 双源 × content/file） | **4/4 match: True** |
| 8 | prior 块 vs `git show HEAD:` 程序化逐字节比对 | **2/2 True**（span/content/file 全等） |
| 9 | `verify_workflow.py check-governance --summary-only` | 唯一 FAIL=28s（既有）；无新增 |
| 10 | grep 26358/26385 残留扫描 | 26358 仅存历史注记；无陈旧断言 |
| 11 | 授权链实体核查（DEC-266 / 两份 R0 报告） | 全部存在且指向正确 |

---

## 4. 代码审查硬门槛裁决（code-review SKILL）

| 门槛项 | 裁决 |
|---|---|
| P0 阻塞 = 0 | ✓（P0=0，P1=0） |
| 5 维度全覆盖 | ✓ 正确性：PASS（数据面与实况双路对账+38 测试绿）；安全性：PASS（无密钥/注入/权限面变更，纯声明数据）；可维护性：PASS（注记完整、溯源链可检索，P3×3 注记级）；性能：PASS/N-A（无运行时逻辑，测试耗时 131.8s 属 loop-claims 测试族既有水位）；测试覆盖：PASS（正/负对照全绿，冻结字面量由 test_metadata_contract 精确钉住） |
| 每条发现标注级别 | ✓（N1-N3 均 P3） |
| 设计一致性 | ✓ 与 DEC-262② sanctioned regen 策略、DEC-266 授权链、0.90 archguard regen 先例一致；重钉语义（授权变更随链重钉 vs 未授权漂移披露）与 Developer 申报及 manifest change_rule 吻合 |
| AI 代码专项 5 项 | ✓ mock 残留：无（diff 无 mock）；硬编码返回值：无（字面量即冻结真值契约，设计使然）；幻觉 API：无（未引入任何调用）；未实现 TODO：无新增；过度实现：无（纯数据登记） |

## 5. 终态声明

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`。本报告为唯一产出；审查过程中除 regen 幂等性验证（输出与既有工作区状态字节一致）外未产生任何写操作，未修改产品文件与 `.governance/**`。本结论不替代测试审查与发布审查。
