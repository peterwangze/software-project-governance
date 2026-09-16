结论：**APPROVED_WITH_NOTES** ｜ round=1 ｜ unresolved_blockers=0 ｜ 机录 round 建议 = 无（通过终态，复审链关闭——R0 首行同位域的「机录 round 建议」仅对 NEEDS_CHANGE 分支有义；Coordinator 指令模板中的 `REVIEW-FIX-314-R2` 仅在 NEEDS_CHANGE 时适用，本复审未触发，据实填写）

# Review — REVIEW-FIX-314-CODE-R1（R0 P1-1 退回修复核验）

- **round/R1 声明**：本报告为 round 1 复审，前轮引用 = `docs/reviews/review-FIX-314-CODE-R0.md`（NEEDS_CHANGE，unresolved_blockers=1，P1-1 唯一阻塞）。逐条比对结论：**P1-1 已修复；P2-1 已转承 FIX-344（plan-tracker L107 在案）；P2-2/P3-1~5 按遗留计划保留；无新引入阻塞**。
- **基线**：HEAD 仍为 `7bb102b`（与 R0 完全一致），工作树改动仍仅 2 文件：`infra/review_record.py`（HEAD→工作树 +119/−23）、`infra/tests/test_verify_workflow.py`（+437/**−0**）；`verify_workflow.py`/`hooks/`/`checks/review_domain.py` 经 `git status --porcelain` + `git diff HEAD --stat` 独立确认**零接触**。
- **审查者**：Code Reviewer（R0 同一审查方，复审 = 验证修复；独立复现优先，不转抄 Developer 声明）。
- **方法**：R0 锚点位移核算 + 当前文件 547 行全读 + 逐 hunk diff 审查 + 三面 GBK 活体探针（%TEMP% 隔离，`--project-root` 指向临时目录，全程未触真实 `.governance/` 写面）+ 三定向套件 + 全量 841 套件独立复现（仓库根）+ archguard-ratchet 独立复跑。

---

## 一、R1 重点逐项裁决

### 1. P1-1 三面复验（独立活体探针，%TEMP%）

GBK canonical fixture（`review-FIX-314-R5.md`，GBK 字节含 `- reviewer: Design Reviewer`，触发 `0xc9` 解码失败）+ 既有 evidence-log（seed 字节基线）：

| 探针 | 路径 | 结果 |
|---|---|---|
| A | **CLI 主路径**（`review-record --project-root <temp>` + 带 reviewer 写入） | **rc=2** + JSON error dict（`cannot read existing review record to resolve the (task, round, reviewer) key: 'utf-8' codec can't decode byte 0xc9...`）+ stderr 零 Traceback + **零写入**（canonical 字节不变 / evidence-log 字节不变 / 零 namespaced 文件 / `.governance` 目录集合不变） |
| B | **force 备份读**（库内 `write_review_record(force=True)`，reviewer-less → 越过 owner 探针直达备份读） | error dict（`cannot read existing review record for backup: ...`）+ **零写入**（无 `.pre-*.md` 备份、canonical 不动、evidence-log 不动） |
| C | **带 reviewer + force=True**（owner 探针先于 force 分支） | 与 A 同 error dict + 零写入——GBK canonical 使 force 自救同落结构化 fail-closed（R0 P1-1 第 3 点的场景，现为结构化拒绝而非裸 traceback） |

三条新用例独立复现 **16/16 OK**（`test_gbk_canonical_owner_probe_fails_closed_to_error_dict` / `test_gbk_canonical_force_backup_read_fails_closed_to_error_dict` / `test_cli_gbk_canonical_yields_exit2_error_dict_not_traceback`），断言面与我的探针一一吻合（canonical 字节等同 + 零 namespaced + 零 evidence 行 + rc=2 + JSON + `assertNotIn("Traceback")`）。RED（1F+2E）系历史状态不可复验，采信声明（R0 同先例）——GREEN 断言面已覆盖声明所列三场景。

### 2. 修复不引入新面

- **catch 面恰宽**：两处均 `except (OSError, UnicodeDecodeError)`——`UnicodeDecodeError` 是 `ValueError` 子类，该 tuple 不吞其他 `ValueError`/`Exception`；无过宽。全文件 catch 面枚举（全读核实）：L394 `(TypeError, ValueError)`（输入校验，既有）、L434/L471（本次修复）、L484/L494/L503 `OSError`（备份写/记录写/证据行写，既有）、L250/L517 `Exception`（wiring/bridge best-effort，既有）——**除 2 处加宽外无任何 catch 变化**。
- **error dict 消费方兼容**：CLI 唯一消费方 `cmd_review_record`（verify_workflow.py L22117-22119）仅判 `summary.get("error")` 真值 → JSON 输出 + `sys.exit(2)`——**文本无关，形状兼容**，任何 error dict 文本均兼容。force 路径消息经 diff 上下文行证实与 HEAD **逐字节一致**（`cannot read existing review record for backup: {0}`）；owner 探针路径消息文本无法对 R0 态字节复核（修复前状态未入 git、不可重建），但返回块行数守恒（锚点核算，见下节）、形状与全模块 error dict 一致、且消费方文本无关——兼容性成立。
- **逐 hunk 核算（「除 2 处外无其他改动」）**：R0 报告锚点位移——L120（`_read_record_reviewer.read_text`）→ 现 L120 **零位移**；L387（"Never raises" 契约行）→ 现 L387 **零位移**；L434（owner 探针 except）→ 现 L434 **同位置原位加宽**；L442 owner 匹配位移 +4 = 恰好 4 行修复注释；force 块位移 +3 = 恰好 3 行修复注释；总行数 547 = R0 态 540 + 7。**修复增量 = 2 处 catch tuple 原位加宽 + 7 行注释，无其他行面改动**。测试文件 +437/**−0 零删除** → 13 条既有用例零改动，+71 行 = 3 新用例 + GBK helper + 分节注释。
  - **勘误（本审查方 R0 报告）**：R0 基线行所记 review_record.py「+89/−22」的 ins 数字系误记（按 HEAD 451 行 + R0 态 540 行 −22 删反推应为 +111）；−22 与现 diff 恰合（新增的唯一删除面 = force catch 行）。该误记不涉及 R0 任何发现/结论，锚点位移核算已闭合此差异。

### 3. CLI 零改动依据裁决：**依据成立**

- `verify_workflow.py` 零 diff（24453 行整）+ archguard R1 锚 24453 ≤ 24453 **实测 PASS**——改 CLI 必增行破锚，属实。
- thin entry 事实核（L22094-22119 全读）：`cmd_review_record` **零捕获**委托 `write_review_record`，error dict → JSON + exit 2；库兑现 L387「Never raises」后（两处数据面读失败均已结构化，探针 A/B/C 实证），委托模式成立。
- 「同型 entries 零捕获先例」核实：`cmd_next_candidates`（L22122+）同构零捕获委托，先例属实。
- 收益/成本裁决：CLI 加捕获 = 零功能收益（库已返回 error dict，探针 A 端到端已得 JSON+exit 2）+ 破 R1 锚需重锚。**裁决：CLI 零改动正确。**

### 4. P2-1 隔离核实：**成立**

`checks/review_domain.py` 零接触（git status/diffstat 双确认）；plan-tracker L107 **FIX-344 已登记**（R0 P2-1 转承，2026-09-16，含三点盲区修法 + V8 假 WARN 后果 + 验收基线「既有 838 套件不回归」+ 目标版本 0.82.0 或后续 + 「WARN→FAIL 升级激活前必须修复」闸门条件）——转承要件齐全。

### 5. 套件红基线身份独立复现（仓库根）：**逐一重合**

`python -m unittest discover -s skills/software-project-governance/infra/tests -p test_verify_workflow.py` → **Ran 841 tests in 245.310s**（838+3 ✓），恰 3 红，身份与 R0 记载逐一重合：

1. `ERROR: FIX300DualCaliberAgreementTests.test_fixture_identity_mode_agrees_with_engine_on_present_sources`
2. `FAIL: FIX300DualCaliberAgreementTests.test_identity_host_source_drift_reproduces_divergence_shape`
3. `ERROR: LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`

三红均与本改动无依赖关系（FIX-300 双口径 / Loop runtime claim 适配，HEAD 既有，R0 已实证基线同型）。定向套件：ReviewRecordReviewerKeyTests **16/16** + test_review_record **21/21** + closure-legacy **36/36** 全绿。archguard-ratchet 独立复跑 **PASS（0 violations；R1 零增行 / R5 84/84 frozen / R7 deterministic）**。

## 二、发现列表（P0=0 ｜ P1=0 ｜ P2=1（遗留）｜ P3=6）

- **P2-2（R0 遗留，非阻塞）**：Check 30 merge 口径（任务级最 terminal 胜）+ commit-msg gate 任务级 OR 粒度——既有语义，FIX-344 描述中已并列「建议同批 DEC 一并收口」，保留至该批。
- **P3-1~P3-5（R0 遗留，全部维持原级）**：CLI 无 `--force` 旗标（force 仅库内可达——本次探针 B 亦因此走库内路径，现状与 R0 判定一致）；owner 匹配大小写敏感；reviewer 原文入证据 cell 未消毒；字面 `--reviewer unknown` 可认领无主记录；canonical 缺失 + namespaced 孤儿。均既有面/病态输入，不阻塞。
- **P3-6（新观察，非阻塞，非本次引入）**：`write_review_record` 的 `evidence_dir.mkdir(parents=True, exist_ok=True)`（L412）无异常捕获——`.governance` 不可创建时 OSError 仍可逃逸（L387「Never raises」对环境错误面不字面成立）。属 FIX-236.1 既有面、环境依赖型、触发面远窄于 P1-1 的数据面，且不在本次修复范围；CLI thin-entry 模式下同落裸 traceback。建议随 FIX-344 批或后续小修一并收口（catch OSError → error dict 即可，模式与本次完全同型）。

## 三、五维度 + AI 专项裁决

| 维度 | 裁决 | 依据 |
|---|---|---|
| 正确性 | **✓（P1-1 关闭）** | 两处读失败面 fail-closed 实证（探针 A/B/C）；键面/守卫/备份/行 ID 推导维持 R0 已核验状态（锚点零位移） |
| 安全性 | ✓ | 无新增注入/敏感数据/权限面；catch 恰宽不吞异常；零写入面逐字节实证 |
| 可维护性 | ✓ | 修复注释精确引用 R0 P1-1 与 GBK 现实风险源（AUDIT-147 D6 / AUDIT-148 §4.3）；docstring「Read errors propagate: the caller fails closed」与实现现自洽 |
| 性能 | ✓ | 零新增运行时开销（仅异常路径 catch 面加宽） |
| 测试覆盖 | ✓（R0 缺口①已闭合） | P1-1 三面各有专属用例；R0 缺口②（双半面 × 30c 交互）已随 FIX-344 转承，不阻塞本修复 |

**AI 专项 5 项**：mock 残留 无｜硬编码返回 无｜幻觉 API 无（841 套件独立复现佐证）｜未实现 TODO 无｜过度实现 无（修复收敛于 2 处 catch + 7 行注释 + 3 用例，声明与事实一致）。

## 四、结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0；P0=0，P1=0）。P1-1 修复面与声明完全一致且三面独立实证通过；CLI 零改动依据成立；P2-1 转承在案；红基线身份逐一重合；无新引入问题。遗留项 = P2-2/P3-1~6（均非阻塞，各有归属批次）。
