# Review Report — FIX-289 Code Review R0

- **Task**: FIX-289（FIX-281⑤⑥，0.78.1 入槽，DEC-173① 方案 A 缺陷面）
- **基线**: HEAD `afb959d`，工作树未提交 diff（git 层面未独立复核——Reviewer 无命令权限，以逐文件全文阅读 + Developer 自报 EVD-910 交叉核验）
- **被审查范围（严格 3 文件）**:
  1. `skills/software-project-governance/infra/review_record.py`（已全文阅读，451 行）
  2. `skills/software-project-governance/infra/tests/test_review_record.py`（已全文阅读，401 行）
  3. `skills/software-project-governance/references/evidence-id-prefix-conventions.md`（已全文阅读，38 行）
- **Reviewer**: Code Reviewer（Coordinator spawn，只读约束生效：未调用任何写/命令/用户交互工具）
- **Date**: 2026-08-28

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

（P0=0；1 条 P1 以遗留项记录、附关闭节点；不阻塞合并）

## 发现计数

| 级别 | 数量 |
|------|------|
| P0 阻塞 | 0 |
| P1 关键 | 1 |
| P2 建议 | 1 |
| P3 讨论 | 3 |

## 五维度逐项结论

| 维度 | 结论 | 事实依据 |
|------|------|---------|
| 正确性 | ✅ 通过 | 守卫 fail-closed 顺序正确：输入校验（L333-347）→ 目的地解析 → 存在性守卫（L362-391）→ 写记录（L397-400）→ 追加 evidence 行（L405-409）。默认路径在守卫处 return error dict，位于一切写操作之前——不覆盖文件、不追加行；`evidence_dir.mkdir`（L355）虽在守卫前，但守卫触发以 `review_file.exists()` 为前提，目录必然已存在，`exist_ok=True` 为 no-op，无副作用。keyword-only `force=False`（L281-296）保证既有调用零变化。 |
| 安全性 | ✅ 通过 | `task_id` 经 `_TASK_ID_RE = ^[A-Z]+-\d+$`（L74、L333）校验，阻断路径注入；备份名仅由已校验组件 + 固定格式微秒时间戳构成（L383-385）；force 路径不绕过任何输入校验（校验先于守卫）；无敏感数据、无注入面。 |
| 可维护性 | ✅ 通过（含 1 条 P3） | 守卫块注释完整（L362-367，REL-073 佐证引用属实）；docstring 行为契约同步更新（L23-30、L317-324、L218-222）；错误信息可操作（含记录路径 + force 出路指引，L371-376）。P3：`write_review_record` 函数体已约 160 行，本次 +30 行守卫后继续增长应考虑拆分。 |
| 性能 | ✅ 通过 | 纯文件 I/O，无循环嵌套；仅 force 路径多一次读 + 一次写；时间戳生成 O(1)。无 N+1/O(n²) 风险。 |
| 测试覆盖 | ✅ 通过（含 1 条 P2） | `ReviewRecordOverwriteGuardTests` 6 用例覆盖：默认拒绝核心路径（字节级不变断言 + evidence 行计数断言）、错误信息内容、force 备份字节保真 + 标记 + summary 字段、连续 force 链代际保真、fresh 记录 force=普通写（边界）、CLI 端到端 exit 2（错误路径）。断言实质性（字节比较/计数/返回码），无 mock 残留。P2：备份 OSError 分支（L377-390）无测试。 |

## 发现列表

**[P1] evidence-id-prefix-conventions.md:9 — 机器解析方出处误引「Check 28」，实为 Check 13**
- 事实依据：文档 L9 写「verify_workflow.py（**Check 28** 编号缺口检测、…）」。仓内事实：EVD- 编号缺口检测属 **Check 13 Sequential ID Checking**（verify_workflow.py:14345 头部打印；`_print_sequential_id_check` L11408 docstring 自证；EVD-ID gaps 打印于 L11417-11421；`evd_gaps` 产出自 L11390-11392）。而 Check 28 主项是 Governance Review Fallback Policy（L14874），28b~28s 子项均为其余 Guard，无一做编号缺口检测。本文档自我定位为「约定事实源」（L3）且规则 5 要求跨仓申报引用本文档——出处误引会传播其本要消除的歧义。
- 影响：无行为/数据影响（规则 1~4 非机器强制，L38 边界说明如实）；损害事实源文档的引用精确性。
- 建议：一词修正——「Check 28 编号缺口检测」→「Check 13 编号缺口检测」。
- 处置：**遗留项 L-1**，关闭节点 = 0.78.1 M-1 候选打包前（REL-073 里程碑链，plan-tracker L263）。

**[P2] test_review_record.py — force 路径的 OSError 分支（review_record.py:377-390）无回归测试**
- 事实依据：6 新用例未覆盖「备份读失败/备份写失败 → error dict 且原记录不动」的回滚性质。该性质经代码阅读核实正确（备份写失败发生在对 `review_file` 任何突变之前，L386-390 先于 L398 的覆盖写），但无测试看护，后续重构可能无声破坏。
- 建议：以 `mock.patch.object(Path, "write_text", side_effect=OSError)` 定向注入备份写失败，断言 error dict + 原记录字节不变 + 无 `.pre-` 残留。可遗留。

**[P3] review_record.py:366-367 — docstring「repeated forces never collide」为轻微过强表述**
- 事实依据：微秒时间戳（`%Y%m%dT%H%M%S%f`，L385）使同进程顺序调用实际不可能碰撞；但同微秒并发 force（跨进程）会以截断方式覆盖同代备份。命名格式定长零填充，字典序=时间序，`sorted()` 代际断言（测试 L356-359）成立。
- 建议：不改代码；后续如触及可改为「microsecond timestamps make collisions practically impossible」级措辞，或写入时用 `O_EXCL` 语义。

**[P3] review_record.py:397-400 — 备份成功后记录写失败时，error 信息未提示备份位置**
- 事实依据：该失败路径下原文件可能截断，但数据已在 `.pre-<ts>` 备份中；返回的 error 文案（"cannot write review file"）不指明恢复点。与修复前相同的固有失败模式类（非本次回归），evidence 行不会追加（正确）。
- 建议：error 文案追加「previous record preserved at {backup}」。

**[P3]（备注，非缺陷）force 覆盖产生同 REVIEW-ID 双 evidence 行**
- 事实依据：已由 RISK-047（risk-log L47，2026-08-28 登记）显式承载：「append-only 不破坏数据；Check 30 first-match 扫描落首行，无 FAIL 向量」，后续动作（evidence 行替换语义 / CLI --force 旗标）已入 DEC-174 后续候选。本审查不重复立项，仅确认该已知行为与登记一致。

## AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 新增 `ReviewRecordOverwriteGuardTests`（L270-397）零 mock；既有 mock 用法（vw 属性 patch、process_gate_result side_effect）均属正当用途 |
| 2 | 硬编码返回值 | ✅ 无 | 守卫逻辑为真实存在性检查 + 真实文件 I/O；备份名动态生成 |
| 3 | 幻觉 API/引用 | ⚠️ 1 处引用失准（即 P1） | 所用 Python API 全部真实；REL-073（plan-tracker L263）、EVD-910（evidence-log L1621）、RISK-047（risk-log L47）、DEC-174（decision-log L183）、REQ-107（review_domain L2492）、Check 30c（review_domain L2508）均实证存在；唯一失准 = 文档 L9 的「Check 28」应为「Check 13」 |
| 4 | 未实现 TODO | ✅ 无 | 三个文件无遗留 TODO；后续动作均走 DEC-174/RISK-047 正式登记，非裸 TODO |
| 5 | 过度实现 | ✅ 无 | force 严格限定 DEC-174 范围（库级 keyword-only，CLI 参数面零变化，argparse L22661-22680 实证无 --force）；⑥ 文档恰为申报的映射说明，5 条规则与申报一一对应 |

## 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞 = 0 | ✅ 通过 |
| 5 维度全覆盖 | ✅ 通过 |
| 每条发现标注级别 | ✅ 通过 |
| 设计一致性 | ✅ 通过——与 FIX-281⑤ 申报（plan-tracker L262「⑤review_record.py:335 无存在性检查直接覆盖，P7 数据破坏风险」）精确闭合；与 DEC-174（decision-log L183：库级 force 而非 CLI 旗标，CLI 零改动走既有 exit-2）完全一致；⑥ 与 FIX-281⑥ 申报「EV-/EVD- 前缀差异无映射说明」闭合 |
| AI 专项 5 项 | ✅ 全部完成 |

## 遗留项列表

| # | 级别 | 内容 | 关闭节点 |
|---|------|------|---------|
| L-1 | P1 | evidence-id-prefix-conventions.md:9「Check 28 编号缺口检测」→「Check 13 编号缺口检测」（一词修正） | 0.78.1 M-1 候选打包前 |
| L-2 | P2 | 补 force 路径 OSError 分支回归测试（备份写失败→原记录不动） | 0.78.1 后续修正批次 |

## 重点审查项 1-8 逐项核实结果

1. **守卫 fail-closed 语义** — ✅ 核实通过。默认路径 return 位于 review_record.py:369-376，先于记录写（L398）与 evidence 追加（L405-409），无文件写入无行追加（测试 L318-323 字节不变 + 行计数=1 断言）。error dict 调用方处置全量枚举（grep 16 处）：唯一生产调用方 = verify_workflow.py `cmd_review_record`（L21023-21035），`summary.get("error")` → `sys.exit(2)` ✅；其余调用方均为测试且显式处理 error。
2. **force 三重留痕** — ✅ 核实通过（含 2 条 P3 备注）。读失败（L378-382）/备份写失败（L386-390）均先于对原记录的任何突变 return error——回滚正确；连续 force 链各保前代（每次备份当前文件后再覆盖，测试 L348-361 双代际断言）；微秒时间戳定长格式防碰撞成立（同微秒跨进程并发为理论残留，P3）。
3. **备份文件名惰性** — ✅ 核实通过。正则定义实位于 `infra/checks/review_domain.py`：`_LEGACY_REVIEW_FILE_RE = ^review-([A-Z]+-\d+)-v\d+\.md$`（L1531）与 `_REVIEW_FILE_NAME_RE = ^review-([A-Z]+-\d+)(?:-R(\d+))?\.md$`（L2502-2503），verify_workflow.py:1184 re-export。双正则均双端锚定，`review-FIX-236-R0.pre-<ts>.md` 因 `.pre-` 段无法匹配。Check 30 文件扫描（review_domain L2451-2460）与 Check 30c（L2565、L2603-2611）对备份文件分别 skip / 计入 `files_unmatched` 不判定；`_lookup_review_file`（L2580-2597）仅按精确候选名查找，永不命中备份。惰性声明成立。
4. **`- force_overwrite:` 标记行惰性** — ✅ 核实通过。日期锚 `REVIEW_FILE_DATE_RE = ^- date: (\d{4}-\d{2}-\d{2})\s*$`（L2505，multiline）不匹配标记行；结论提取 `_extract_review_conclusion_from_text`（L1595-1610）锚定「审查结论/评审结论/CONCLUSION + 冒号 + 状态词」，标记行无此类锚；next_round 锚 `REVIEW_NEXT_ROUND_FIELD_RE = next_round:\s*REVIEW-`（L2501）不匹配；blocker 字段扫描无 token 可捕获。标记行插入位置（`- wiring:` 之后、结论块之前）对全部顺序无关解析器无影响。
5. **向后兼容** — ✅ 核实通过。`force` 为 keyword-only 且默认 False（L282、L295）；全仓调用点 grep 实证：CLI 入口（verify_workflow.py:21023）与 test_review_machine_provenance.py:158 均不传 force；argparse 无 `--force`（L22661-22680）——既有调用零行为变化，与 DEC-174 及 EVD-910「CLI 零改动」自报一致。
6. **测试质量** — ✅ 通过（含 1 条 P2）。6 用例覆盖核心/边界/错误路径，断言实质（字节比较、计数、exit code、summary 结构字段），无 mock 残留；缺口仅 OSError 防御分支（P2）。Developer 自报 RED→GREEN（未修复 3 failures+3 errors → 21/21）与守卫语义、CLI exit 2 断言（测试 L372-397）逐条对应，可证性成立；测试执行本身未独立复跑（无命令权限，标「未验证」）。
7. **⑥ 文档事实准确性** — ⚠️ 1 处失准（P1），其余全部实证一致：`router EV-066（2026-08-23）/EV-071/073（2026-08-27）`（plan-tracker L262 原文吻合）；REL-073 设计审查引用 EV-066/071/073 与 EV-038/EVO-004（docs/reviews/review-REL-073-DESIGN-R0.md:46）；audit-148 报告含 EVO-004（该文件 L99）；行模板源 `core/templates/evidence-log.md` 存在；Check 34 快照锚（`_SNAPSHOT_REF_RE` verify_workflow.py:20725）与 REQ-108/M7.4 step 6 RECO-/EVD- 锚要求（behavior-protocol.md:565 原文吻合）；`| EVD-` 迁移扫描（archive.py:1044/1499/2116）；evidence_domain.py 存在且解析 EVD- 行；`gate_state.evidence_refs` 契约（loop-runtime-contract.json:94/118）、v2 仅校验 list 类型（flow_unit_runtime_v2.py:368-370）、append 语义（loop_gate_processor.py:746-754）三条链全部属实；check-cross-references 悬空引用检测语义属实（verify_workflow.py:11001-11008 docstring 自证）。文档引用的全部仓内路径均逐一验证存在，无新悬空路径引用；check-cross-references 657 refs PASS 为 Developer 自报（未独立复跑）。
8. **范围纪律** — ⚠️ 未独立复核。无 git 权限，无法 diff 工作树。佐证：EVD-910 证据行 artifacts 列恰为本次 3 文件（evidence-log L1621）；review_record.py 修改区域均带 FIX-289⑤ 标记、CLI/argparse 段与「零改动」自报一致；本审查未读取 FIX-288 的 6 个文件（未以其发任何 finding）。工作树是否存在其余本任务改动无法凭只读排除——如实标注。

## 审查结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）——FIX-289⑤⑥ 达成申报语义，P7 数据破坏风险闭合，⑥ 文档一处 P1 引用失准以遗留项 L-1 登记（关闭节点 M-1 前），不阻塞合并。
