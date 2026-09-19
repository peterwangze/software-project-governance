# Review Report — FIX-360 CODE R0

- **Task**: FIX-360（P2，triage 机录 `.governance/change-triage/FIX-360.json`）— sessions[].cwd 双源语义 CALIBRATION 披露行 + 契约钉（review-FIX-356-CODE-R0 F-1 残留）
- **Round**: R0（首次审查）
- **Reviewer**: Code Reviewer Agent（独立审查，未采信 Developer 申报）
- **审查对象**: 工作树未提交 diff，限定 FIX-360 两文件
  - `skills/software-project-governance/infra/governance_cost.py`（numstat **+6/-0**：CALIBRATION 新增 `sessions_cwd` 键，L763-768）
  - `skills/software-project-governance/infra/tests/test_governance_cost.py`（numstat **+8/-0**：新增 `test_calibration_discloses_sessions_cwd_dual_source`，L763-769）
- **结论**: **APPROVED_WITH_NOTES** — `unresolved_blockers=0`
- **日期**: 2026-09-19

---

## 0. 范围与并发说明（事实陈述）

- 工作树同时承载 **FIX-357 在途修改**（`checks/review_domain.py` +71/-4、`tests/test_review_closure_legacy.py` +204/-0），且审查进行中 `tests/test_pre_commit_review_evidence.py`（+40/-2）新出现——同一工作树有其他 Developer 在途写文件。以上均属其他任务文件面，**不在本审查范围**（任务书明确限定 FIX-360 两文件；triage `files` 数组与此一致）。
- 申报偏差备案：任务书写 governance_cost.py「+5」，numstat 实测 **+6/-0**（1 行键名 + 5 行字符串续行）。属申报口径偏差，非范围违规（triage `files` 面精确匹配，两文件均纯新增无顺带改）。

---

## 1. 五维度审查结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | **PASS** | 披露行三态语义与代码逐点核对一致（见 §2）；测试逻辑正确（模块级 dict 断言，无 fixture 依赖） |
| 安全性 | **PASS** | 纯披露字符串 + 测试断言；无输入处理/密钥/注入面变化；真实环境操作仅 1 条只读复跑（R1(c) 授权链，零写操作，见 §5） |
| 可维护性 | **PASS（带备注）** | 键名 `sessions_cwd` 与报告 `sessions[].cwd` 字段名精确对应；行文风格与同 dict 既有条目一致。备注 F-1/F-2 |
| 性能 | **PASS** | +1 dict 条目、+1 O(1) 断言——零运行时影响（真实复跑 scan duration_ms=5016 正常量级） |
| 测试覆盖 | **PASS（带备注）** | 新钉覆盖键存在/类型/非空；语义子串未钉（F-1）。套件 59 passed |

## 2. 披露措辞语义准确性核对（审查重点 1）——逐点比对

披露文本（governance_cost.py L763-768）：

> "dual-source: the session event's ``cwd`` wins when present; when it is absent this field carries a token unwrapped from the encoded ancestor directory name (--<id>--), empty when no encoded ancestor exists — a --workspace substring filter token, NOT a filesystem path."

| # | 披露声明 | 代码事实 | 判定 |
|---|---------|---------|------|
| 1 | "the session event's ``cwd`` wins when present" | `parse_session` L394-396：`etype == "session"` 事件取首个非空 `data.get("cwd")`；`scan_sessions` L680-685 仅在 falsy 时回退 | ✅ 一致 |
| 2 | "a token unwrapped from the encoded ancestor directory name (--<id>--)" | `_cwd_fallback_from_session_path` L647-650：`name[2:-2]` 剥离 `--...--` 包裹 | ✅ 一致 |
| 3 | "empty when no encoded ancestor exists"（第三态） | L651：`return ""` | ✅ 一致 |
| 4 | "a --workspace substring filter token" | L686：`if workspace is not None and workspace not in cwd: continue`——子串过滤语义 | ✅ 一致 |
| 5 | "NOT a filesystem path" 声明 | docstring L638-639 同款声明；实现确实从不重组为可遍历路径（仅对 rel_path 的祖先**目录名**做字符串操作） | ✅ 一致，无幻觉 |

三态（事件 cwd / 推导 token / 空串）全部覆盖，无语义偏差、无幻觉声明。

**观察（F-4，P3，无需行动）**：披露未说明多个编码祖先嵌套时取哪一层（实现取最深一层——`Path.parents` 迭代序首个命中）。docstring 同样未指定，两者一致，不构成披露失真；如未来出现嵌套编码目录场景可在同任务面补一句。

## 3. Findings 清单

### F-1（P2 建议——可遗留）契约钉断言强度：钉了键，未钉语义

- **位置**: `test_governance_cost.py` L763-769
- **描述**: 断言仅覆盖 键存在 / `isinstance(str)` / `.strip()` 非空。若未来重构将披露文本替换为语义不完整甚至误导的文案（例如丢掉 "dual-source" 或 "NOT a filesystem path" 声明），该钉仍然通过——而 F-1 残留的修复初衷恰恰是披露完整性。同文件姊妹钉 `test_calibration_notes_discloses_overlap_semantics`（L750-761）有语义子串断言（"cumulative"/"residual"），本钉弱于本文件自身惯例。
- **缓解事实**: triage reason 原文即「测试断言键在场（现无契约钉）」——实现与 triage 范围精确一致，加强断言属超出最小面的增强诉求，非实现缺陷。
- **建议**: 后续（可并入 0.85.0 面或遗留）补 1~2 个语义锚断言，如 `assertIn("dual-source", ...)` 与 `assertIn("NOT a filesystem path", ...)`，使钉真正看护披露内容而非仅键名。
- **处置**: 不阻塞合并；建议 Developer 采纳或登记遗留。

### F-2（P3 讨论——无需行动）契约钉置于 `_require_zstandard` 守护类内引入 skip 面

- **位置**: `test_governance_cost.py` L713-717（`TestCLIOutput.setUp` → `_require_zstandard`）+ L763（新钉）
- **描述**: 新钉是纯模块级 dict 断言，不依赖 zstandard、不建 fixture；但置于 `TestCLIOutput` 类内后，在无 zstandard 环境会随类级守护被 skip——守护对该测试是不必要的。
- **缓解事实（重要性评估）**: ① 无 zstandard 环境下 `governance_cost` 报告生成整体 fail-closed（`GovernanceCostError`），calibration 面在该环境下本就无消费者，钉的保护价值趋零；② 同类姊妹校准测试确实需要 zstandard fixture，类级守护对它们合法；③ 本仓 dev/CI 环境有 zstandard（0.25.0 实测），重构风险实际发生在有 zstandard 的环境。故 skip 风险技术上存在、实质影响可忽略。
- **建议**: 不要求本轮改动。未来新增无 fixture 依赖的披露钉时，可放独立无守护类（或模块级断言），消除环境耦合。

### F-3（P3 建议——登记候选）空串 cwd + `--workspace` 过滤静默跳过无计数面

- **位置**: `governance_cost.py` L686-687（过滤点）+ L718-726（scan 面）
- **描述**: 空串 cwd 的会话在 `--workspace` 过滤下必然 `workspace not in ""` → 静默 `continue`；scan 面有 files_found/parsed/failed 但无「被过滤跳过 / 空 cwd」计数——用户无法区分「0 会话命中」与「N 会话因空 cwd 被跳过」。Developer「超出最小面不实施」的处置**恰当**：triage 范围=披露行+钉；scan 面加计数器改动 report schema 面（scan dict 为下游消费面），属独立变更，符合 D4 修改纯粹性。且披露行已诚实文档化空串第三态，消费者已获警告。
- **建议**: 登记 0.85.0+ 候选任务（如「scan 面增加 filter-skip/empty-cwd 计数器」），勿并入 FIX-360。

### F-4（P3 观察——无需行动）多重编码祖先未指定取层

- 见 §2 观察项。披露与 docstring 一致地未指定，非失真。

## 4. 范围纪律 / 向后兼容 / AI 专项（审查重点 3/4/5）

- **范围纪律**: ✅ FIX-360 两文件 numstat `+6/-0`、`+8/-0` 纯新增，零删改、零顺带改；triage `files` 数组逐字匹配。工作树其余 3 个修改文件属 FIX-357 在途（§0，出范围）。
- **向后兼容**: ✅ CALIBRATION 仅两处消费（L727 报告嵌入 + 测试）；`sessions_cwd` 全仓 grep 仅命中本任务两文件——无其他消费者/文档/schema 需同步。契约矩阵快照（`contract_matrix/snapshots.json`，12,387 字节）不含 `calibration`/`governance_cost`/`sessions_cwd` 任何钉，且 `generator.py --check` 实测 **zero drift**——**无需 regen**。加键为 JSON 面纯增量，既有消费者（`test_json_output_has_schema_and_metrics` 断言 `assertIn("calibration", report)`、姊妹校准测试 join values）不受影响。
- **AI 专项 5 项**:
  1. mock 残留：无（新测试零 mock）✅
  2. 硬编码返回值：无（静态披露文本即交付物本体）✅
  3. 幻觉 API/语义：无——披露声明经 §2 五点逐一对照真实代码路径验证 ✅
  4. 未实现 TODO：无（diff 内零 TODO；scan 计数器为显式披露的遗留建议，非隐藏未实现）✅
  5. 过度实现：无——+14 行恰好=最小面（一行披露+一条断言），零范围蔓生 ✅

## 5. 独立复验结果表

| # | 命令（workdir=仓库根） | exit code | 输出摘要 |
|---|----------------------|-----------|---------|
| 1 | `python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q` | 0 | **59 passed in 0.18s**（=58 基线 + 1 新增，0 skip；zstandard 0.25.0 在场）——与 Developer 申报①一致 |
| 2 | `python skills/software-project-governance/infra/verify_workflow.py governance-cost-report --sessions-root C:/Users/peter/.dsh/sessions --workspace project_management_workflow --format json` | 0 | schema `governance-cost-report/1`；scan `files_found=355, files_parsed=355, files_failed=0, duration_ms=5016`；calibration 面 8 键含新 `sessions_cwd`，披露文本与源码逐字一致——与 Developer 申报③一致（353→355 为会话根实时增长，非偏差） |
| 3 | `python skills/software-project-governance/infra/contract_matrix/generator.py --check` | 0 | `contract matrix: current implementation matches snapshot (4 faces, zero drift)`——确认加键不需要快照 regen |

注：Developer 申报②「verify_workflow.py 全部子命令 PASSED」未逐项独立复跑（复验预算 1~3 项；全套结果同时受 FIX-357 在途修改混淆，归因不洁）——本审查以第 1/2/3 项针对性复验覆盖本变更的直接验收面。

### 真实环境命令逐条上报表（R4）

| 命令 | 环境性质 | 写操作 | 授权链 | 结果 |
|------|---------|--------|--------|------|
| 复验表 #2（governance-cost-report 真实只读复跑） | 用户真实会话根 `C:/Users/peter/.dsh/sessions` | **零写**（纯读，stdout 内存解析，未落盘任何文件） | R1(c)：用户 2026-09-19 授权该命令族（任务书沿用） | exit 0，见复验表 |

除上表外本审查未执行任何触及用户 HOME 配置目录/`$DSH_HOME` 的操作；破坏性红线不适用（无安装/验收/配置写场景）。

## 6. 硬门槛裁决

| 门槛 | 判定 |
|------|------|
| P0 阻塞问题数 = 0 | ✅（P0=0，P1=0） |
| 5 维度全覆盖 | ✅（§1 逐维有结论） |
| 每条发现标注级别 | ✅（F-1~F-4 均 P2/P3，无阻塞级） |
| 设计一致性 | ✅（与 review-FIX-356-CODE-R0 F-1 修复语义、triage 范围、RISK-050/FIX-356 既有语义一致） |
| AI 专项 5 项 | ✅（§4 逐项有结论） |
| 独立复验真实执行 | ✅（§5 三命令，exit code + 摘要在案） |

## 7. 总结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

修复以最小面（+6/+8 纯新增）正确闭环 review-FIX-356-CODE-R0 F-1：披露行三态语义与代码逐点一致、无幻觉；契约钉在场；范围纪律与向后兼容均实证无虞。F-1（钉强度）/F-2（钉放置）为非阻塞增强建议，F-3 建议登记 0.85.0+ 候选，F-4 仅观察。无阻塞项，可合并。

---

*Reviewer 独立声明：本报告全部结论基于本仓工作树文件现状（行号以审查时点为准）与 §5 实测命令输出；未采信 Developer 申报作为通过依据（申报仅作交叉对照）。未修改任何代码文件；唯一写入=本报告。*
