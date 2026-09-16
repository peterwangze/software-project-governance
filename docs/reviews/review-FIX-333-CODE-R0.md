<!-- review-record: task=FIX-333 type=CODE round=R0 verdict=NEEDS_CHANGE next_round=R1 unresolved_blockers=1 blocking_findings=P1:F-1 nonblocking_findings=P2:F-2,P2:F-3,P3:F-4,P3:F-5,P3:F-6 -->

# Code Review — FIX-333-CODE-R0：write-guard 非 UTF-8 边界四面收口的独立代码审查（round 0）

| 项 | 值 |
|---|---|
| Task ID | FIX-333 |
| 审查 round | **R0**（首轮；机录 round 建议：**返工后 R1**——F-1 为 P1 阻塞，返工范围见 §六） |
| 审查对象 | 工作树未提交改动（基线 HEAD `0a13b21`）——`skills/software-project-governance/infra/verify_workflow.py`（+7/−7，5 hunk，行中性）+ `skills/software-project-governance/infra/tests/test_triage_write_guard.py`（+87，3 条 GBK 反相用例） |
| 审查类型 | Code Review（`agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行） |
| Reviewer | Code Reviewer sub-agent（独立于 Developer） |
| 日期 | 2026-09-17 |
| 审查约束 | **只读**：Read/Grep/Glob + 只读命令（`git diff/show/status`、`pytest`、`archguard-ratchet`）；GBK 反相一律在 `%TEMP%`（`%TEMP%\fix333_review\` 基线副本 + `tempfile.TemporaryDirectory`）；**未修改任何产品/测试代码**，未触碰仓库 `.governance/`；唯一产物 = 本报告（Reviewer 报告写入职责由 Coordinator 任务指派） |

---

## 一、终态结论（硬门槛裁决）

**NEEDS_CHANGE —— `unresolved_blockers=1`**

- **P0 = 0**；**P1 × 1**（F-1，`_triage_write_structure_guard` 同型缺口未收口——阻塞）；**P2 × 2**（F-2/F-3）；**P3 × 3**（F-4/F-5/F-6）。
- 被审查的四面修复本身**全部正确**且独立复现通过（§二、§四）；阻塞点不在已修四面，而在**同一 write-guard 域内遗留的第 5/6 同型面**（§六 F-1/F-2）——与本任务「泛化收口，不做单点修复」的声明直接冲突（新测试 docstring 自述"泛化收口"，实际收口范围止于四面）。
- 返工预期极小：两处 `except` 扩面 + 1~2 条同型反相测试（约 +4~10 行；archguard R1 行锚为 only-down，增行后按 ratchet 流程 `--regen` 即可，属既有流程非额外风险）。

## 二、硬门槛复现核验（全部从仓库根 `D:\AI\agent\claude\coding\project_management_workflow` 运行）

| # | 门槛 | 命令 | 结果 | 裁决 |
|---|---|---|---|---|
| 1 | RED 可复现 | `%TEMP%\fix333_review\baseline_infra`（HEAD `verify_workflow.py` 副本）+ 工作树测试文件：`python -m pytest ...\tests\test_triage_write_guard.py -q -k non_utf8` | **3 failed**（`<frozen codecs>:325: UnicodeDecodeError` 逸出），32 deselected | ✅ RED 真实 |
| 2 | GREEN | `python -m pytest skills/software-project-governance/infra/tests/test_triage_write_guard.py -q` | **35 passed in 0.24s**（32 旧 + 3 新） | ✅ |
| 3 | 四面 GBK 独立探针 | Reviewer 自建 `%TEMP%\fix333_review\probe.py`（不重用开发者测试代码）：GBK 副本 ×4 面 + `mock.patch` 常量 → `check_governance_write_shapes()` | 工作树：`plan_tracker=FAIL(plan_tracker_unreadable)` / `evidence_log=FAIL(evidence_log_unreadable)` / `agent_locks=FAIL(agent_locks_invalid_json)` / `execution_packets=FAIL(execution_packets_structure, detail 含 "invalid JSON: 'utf-8' codec can't decode…")`，**零异常逸出**；基线副本同探针：**`ESCAPED UnicodeDecodeError`** | ✅ Never raises 契约四面成立，缺陷非自证 |
| 4 | archguard 行锚恒等 | `python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet` | **R1 PASS mainfile loc 24453 ≤ anchor 24453**；R2~R7 全 PASS（print 1299 ≤ 1299、cli 84/84 frozen、regen deterministic=True）；exit 0 | ✅ 行中性实证 |
| 5 | 反相隔离 | 全部 GBK 副本位于 `%TEMP%\fix333_review\` 与 `tempfile.TemporaryDirectory`；仓库 `.governance/` 零写入 | ✅ | ✅ 符合破坏性红线 |

探针勘误记录：首版探针面4 显示 PASS——根因是探针自身载荷 `{"packets": {}}` 全 ASCII（GBK↔ASCII 字节重合，UTF-8 可解码），**非被修代码缺陷**；载荷注入中文后重跑，面4 正确 FAIL。此过程同时反向证实了捕获面的判定边界正确（可解码内容不误报）。

## 三、审查重点逐项裁决

### 重点 1：四面之外的独立扫描（grep `read_text`/`json.loads` 全文件 170/21 处）

**发现同型缺口——详见 §六 F-1（P1）/F-2（P2）/F-4（P3）**：

| 位置 | 函数 | 现状 | 与被修面的关系 | 定级 |
|---|---|---|---|---|
| L22189-22190 | `_triage_write_structure_guard` | `read_text+json.loads` 只捕 `OSError` / `json.JSONDecodeError`；docstring **L22185 明文 "Never raises"** | record JSON ≅ 面4 同型；**这就是 change-triage write guard 写后校验本体** | **P1** |
| L22196 | 同上 | evidence-log `read_text` 只捕 `(IOError, OSError)` | **与面2 读同一个 evidence-log.md 文件** | （并入 F-1） |
| L17574 | `check_agent_lock_consistency`（L17526） | `except (json.JSONDecodeError, IOError)` → skipped | **与面3 读同一个 agent-locks.json** | P2 |
| L17284/L17298 | 插件元数据 best-effort 探测 | `except (json.JSONDecodeError, KeyError, IOError)` | 插件自有资产（版本控制内），触发面窄 | P3 |

外部印证：AUDIT-147 D6 / AUDIT-148 §4.3 已实证 Windows ANSI/GBK 工具误写治理文件是**真实发生**的风险——这正是 FIX-333 的立项前提，因此上述 `.governance/` 读取面不属于纯理论缺口。

### 重点 2：捕获面恰当性

- **面1/2 `+ValueError`（宽）**：try 块仅 `read_text(encoding="utf-8")` 一行（L22455/L22479），`encoding` 为常量 ⇒ try 块内 ValueError 实际来源 ≈ UnicodeDecodeError（`UnicodeDecodeError ⊂ UnicodeError ⊂ ValueError`）；不存在被吞的"其他 ValueError 子类"现实路径。且 fail-closed 语义下即使未来出现意外 ValueError，后果是转结构化 FAIL 而非静默 PASS——无安全方向风险。仓内有同风格先例（L14404 `(IOError, OSError, UnicodeDecodeError, ValueError)`，且该处两异常并列属冗余但无害）。**裁决：可接受**（F-6 P3：与面3/4 的精确 `UnicodeDecodeError` 风格不一致，属可选统一项，不要求本轮改）。
- **面3/4 复用既有分支**：面3 归入 `invalid_json`（write-guard 投影 `agent_locks_invalid_json`，探针实证）、面4 归入 `load_error` 结构（投影 `execution_packets_structure`）。语义上"编码错误 ≠ JSON 语法错误"略有含混，但 detail 内插 `{e}` 携带 codec 信息可分辨，且维持行中性约束下改动最小。**裁决：可接受**。

### 重点 3：Never raises 契约

四面在非 UTF-8 输入下均返回结构化 issue——§二#3 独立探针实证（Reviewer 自建载荷，非重用开发者测试）。**就 `check_governance_write_shapes()` 而言契约成立**；但同文件 `_triage_write_structure_guard`（同为 write-guard 域、同明文契约）不成立 → F-1。

### 重点 4：行中性 + 消息面兼容

- 5 hunk 全部等行替换（2/2、1/1、2/2、1/1、1/1），无行为外改动；archguard R1 loc 24453 ≤ 24453 PASS、R4 print 1299 ≤ 1299 PASS、R5 cli 84/84 frozen PASS——恒等三重实证。
- `exc.msg` → `exc`：`str(JSONDecodeError)` = msg + 位置后缀（超集）；全仓 grep 确认**无任何对 `invalid JSON: {exc.msg}` 形状的精确断言**（唯一 `exc.msg` 残留在 `checks/evidence_domain.py:384`，属该模块自有消息，与本面无关）；`"invalid JSON: "` 前缀保持，消费方均为子串匹配（`test_triage_write_guard.py:792` 等）。`evidence_domain.py:384` 不消费本消息。**裁决：兼容**。

### 重点 5：测试质量 + 范围纪律 + AI 专项

- **RED 可复现**：✅（§二#1，基线副本独立复现）；**非自证**：✅（Reviewer 自建探针双版对照）；**隔离**：✅（%TEMP% + `mock.patch.object` 常量重定向，零 `.governance/` 触碰；GBK 载荷全部为 GBK 可编码的中文+ASCII，规避了 emoji 不可编码坑）。
- 断言精度：面3 用例对锁面仅断言 `FAIL + issues 非空`，未断言投影 type → F-5（P3）。
- **范围纪律**：两个声明文件内改动纯粹（5 hunk + 3 用例全在声明范围）；但工作树另有 **8 个非本任务文件的未提交修改**（`lib/index.js` +24、`test_dsh_adapter.py` +69、`test_loop_runtime_claims.py` +18、`test_verify_workflow.py` +12〔FIX-346 超时预算再校准〕、`agent-dispatch-template.md` +16、`docs/requirements/` ×2、`env_failure_classification.json` +6）→ F-3（P2，提交边界责任在 Coordinator：FIX-333 commit MUST 精确 `git add` 两个声明文件，遵守 P-v1 D4 单 commit 单问题）。
- **AI 专项 5 项**：① mock 残留：无——`mock.patch` 仅用于模块常量重定向到 %TEMP% 隔离副本，合法测试手法；② 硬编码返回值：无；③ 幻觉 API：无——`UnicodeDecodeError`/`json.JSONDecodeError`/`ValueError` 均为真实内置异常层级；④ 未实现 TODO：无残留，docstring FIX-333 标注与实现一致；⑤ 过度实现：无——最小捕获面扩展。

## 四、五维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过（四面） | §二#3/#4 独立复现 + 消息超集兼容核实；但同文件同域遗留面未收口（F-1，阻塞） |
| 安全性 | ✅ 通过 | detail 内插 `exc` 无新增泄露面（UnicodeDecodeError/JSONDecodeError 的 str 不含路径；OSError 分支原本就内插）；结构化 dict 无注入面；fail-closed 方向无静默 PASS 通道 |
| 可维护性 | ✅ 通过 | 复用既有判定分支（Check 26 / load_error）、docstring 与实现一致；F-6 风格统一为可选清理 |
| 性能 | ✅ 通过 | 仅异常路径扩展，零热路径影响；archguard R6 cold import 196 modules Δ0 |
| 测试覆盖 | ✅ 通过（四面） | 3 条反相用例 RED→GREEN 独立复现；契约面覆盖 4/4；F-5 断言精度备注 |

## 五、设计一致性

- 与 docstring 契约（L22443 "Never returns structured issues … Never raises"）四面一致成立；FIX-330 §8-④ 实证边界按声面修复。
- 与「扩展而非重写」声明一致：change-triage 写时守卫行为零变化（diff 无该路径改动——但正因如此，写后校验路径 `_triage_write_structure_guard` 的同型缺口成为收口声明与实际的差距 → F-1）。

## 六、Findings 清单（阻塞项含位置/事实/影响/修复建议）

### F-1（**P1，阻塞**）`_triage_write_structure_guard` 写后校验同型缺口未收口
- **位置**：`skills/software-project-governance/infra/verify_workflow.py` L22189-22190、L22196（函数 L22152）
- **事实**：docstring L22185 明文 `Never raises`；L22189-22190 `Path(record_path).read_text(encoding="utf-8") + json.loads(...)` 仅捕 `OSError` / `json.JSONDecodeError`；L22196 `Path(evidence_path).read_text(encoding="utf-8")` 仅捕 `(IOError, OSError)`。`UnicodeDecodeError ⊂ ValueError`，两者均不接 → 非 UTF-8 输入下异常从 change-triage 写后校验逸出（guard 契约：失败应转退出码 2 的结构化结论，而非 traceback）。
- **同型性实证**：与面2 读**同一个 evidence-log.md**；record JSON 与面4 同为 UTF-8 JSON 读取；该函数即 change-triage write guard 写后校验本体——本任务主题域正中心。
- **影响**：AUDIT-147/148 实证的 GBK 误写场景下，FIX-333 声称的「Never raises 泛化收口」在该面不成立；`change-triage` 进程 crash 而非 fail-closed 退出。
- **修复建议**：L22191 `except OSError` → `except (OSError, UnicodeDecodeError)`（record 面，JSONDecodeError 分支同补或并入）、L22197 `except (IOError, OSError)` → `except (IOError, OSError, UnicodeDecodeError)`（或按面1/2 风格 `+ValueError`，二选一与仓内风格对齐即可）；补 1~2 条 %TEMP% GBK 反相用例（结构对齐既有 `non_utf8` 用例族）。增行走 archguard `--regen` 既有流程。

### F-2（P2）`check_agent_lock_consistency` 一致性路径同文件缺口
- **位置**：L17574（函数 L17526）
- **事实**：与面3 读**同一个 agent-locks.json**，`except (json.JSONDecodeError, IOError)` 缺 `UnicodeDecodeError`——面3 已修的同一文件在此路径仍会异常逸出（本应 skipped）。
- **建议**：与 F-1 同批补 `+UnicodeDecodeError`（一行）。

### F-3（P2）工作树混入 8 个非本任务文件的未提交修改
- **事实**：`git status --porcelain` 共 10 个修改文件；除 2 个声明对象外，其余 8 个属 FIX-346 等其他任务（`test_verify_workflow.py` diff 注释自证 FIX-346）。
- **建议**：FIX-333 commit 时精确 `git add skills/software-project-governance/infra/verify_workflow.py skills/software-project-governance/infra/tests/test_triage_write_guard.py`（返工后加 F-1/F-2 触及的文件），其余变更由各自任务走各自的 commit/审查边界。

### F-4（P3）插件元数据 best-effort 探测捕获面（L17284/L17298）
- `installed_plugins.json`/`marketplace.json` 非 UTF-8 时异常逸出与 UNKNOWN 兜底设计不符；文件为版本控制内插件资产，触发面窄。可随 F-1 批次顺带收口或明确遗留。

### F-5（P3）面3 测试断言精度
- `test_non_utf8_locks_and_packets_fail_closed_not_raise` 锁面仅断言 `FAIL + issues 非空`，未断言投影 type `agent_locks_invalid_json`（探针已证实投影正确）。建议下轮补精确断言。

### F-6（P3）捕获面风格不统一
- 面1/2 宽（`+ValueError`）vs 面3/4 精确（`+UnicodeDecodeError`）vs L14404 冗余并列。语义均正确；统一风格属可选清理，不要求本轮。

## 七、复审指引（R1 必查）

1. 逐条比对本轮 F-1~F-6：F-1/F-2 必须闭环（修复 + 反相测试 + %TEMP% 复现）；F-3 由 Coordinator 提交边界证实；F-4/F-5/F-6 逐条标注已修复/遗留。
2. 增行后 archguard 锚按 ratchet 流程 regen 并验证 R1 only-down 语义仍成立。
3. 四面既有验证（§二#2/#3/#4）在返工后回归：35+新增 用例全绿、archguard PASS、`test_triage_write_guard` 全量通过。

---

**结论：NEEDS_CHANGE（unresolved_blockers=1，F-1）。** 四面修复质量高、独立复现全通过；阻塞点为同一 write-guard 域、同一「Never raises」契约下的写后校验路径（`_triage_write_structure_guard`）及同文件一致性路径未随泛化收口，返工面小（两处 except + 反相测试），建议返工后进入 R1 复审。
