<!-- review-record: task=FIX-333 type=CODE round=R1 verdict=APPROVED_WITH_NOTES next_round=无（复审链关闭） unresolved_blockers=0 blocking_findings=none nonblocking_findings=P2:F-3(Coordinator提交边界),P3:F-4,P3:F-5,P3:F-6 -->

# Code Review — FIX-333-CODE-R1：R0 退回修复核验 + F-H 随批微核（round 1，复审链关闭）

| 项 | 值 |
|---|---|
| Task ID | FIX-333 |
| 审查 round | **R1**（复审轮；前轮引用：`docs/reviews/review-FIX-333-CODE-R0.md`——F-1 P1 阻塞 / F-2 P2 / F-3 P2 / F-4~F-6 P3） |
| 审查对象 | 工作树未提交改动（基线 HEAD `0a13b21`）：`skills/software-project-governance/infra/verify_workflow.py`（vs HEAD 10+/10−，本轮恰 3 处等行替换）+ `infra/tests/test_triage_write_guard.py`（vs HEAD +155 = R0 +87 + 本轮 +68）+ `references/agent-dispatch-template.md`（vs HEAD +16/−0，F-H 单句改写位于其中） |
| 审查类型 | Code Review 复审（`agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行） |
| Reviewer | Code Reviewer sub-agent（R0 同一审查方，独立于 Developer） |
| 日期 | 2026-09-17 |
| 审查约束 | **只读**：Read/Grep/Glob + 只读命令（`git diff/show/status`、`pytest`、`archguard-ratchet`、`check-governance`）；GBK 反相一律在 `%TEMP%\fix333_r1_review\`（`git show HEAD` 字节级基线副本 + `tempfile.TemporaryDirectory`）；**唯一写入 = 本报告**；仓库 `.governance/` 零触碰（套件运行后 `git status --porcelain -- .governance/` 输出为空实证） |

---

## 一、终态结论（硬门槛裁决）

**APPROVED_WITH_NOTES —— `unresolved_blockers=0`（复审链关闭）**

- **P0 = 0，P1 = 0。** R0 唯一阻塞项 **F-1（P1）已修复**且经本 Reviewer 自建探针 + %TEMP% 干净 HEAD 基线独立复现闭环（§三）；**F-2（P2）已修复**同闭环；**F-H（Design R0 P2 随批）已按 Design R0 建议改写**且 4 处出现语义自洽（§四）。
- 修复声明与实测**逐项相符**，无一虚报； except 精确面变体（`UnicodeDecodeError`，非 R0 建议的 `+ValueError` 宽面变体）**裁决成立且更优**（§五）。
- 遗留均为非阻塞项：F-3（P2，Coordinator 提交边界指令）、F-4/F-5/F-6（P3，维持披露）+ 新增观察 N-1（既有日期炸弹，非本改动引入，§三.4）。

## 二、R0 findings 逐条比对（已修复 / 未修复 / 新引入）

| Finding | R0 级别 | R1 裁决 | 证据 |
|---|---|---|---|
| **F-1** `_triage_write_structure_guard` 写后校验同型缺口 | **P1（阻塞）** | **已修复** | L22191 `except OSError` → `except (OSError, UnicodeDecodeError)`，`"triage record unreadable after write"` 消息逐字保持；L22197 `except (IOError, OSError)` → `+ UnicodeDecodeError`，`"evidence-log unreadable after write"` 保持；`except json.JSONDecodeError` 分支（L22193）不动。新增 2 条反相用例 `test_write_guard_non_utf8_record_*` / `test_write_guard_non_utf8_evidence_*`（`WriteStructureGuardUnitTests`，hunk +46 行）。独立复现：§三.1 探针面 A/B 基线 ESCAPED → 工作树 STRUCTURED |
| **F-2** `check_agent_lock_consistency` 一致性路径 | P2 | **已修复** | L17574 `except (json.JSONDecodeError, IOError)` → `+ UnicodeDecodeError`；skipped `"agent-locks.json is unparseable — lock consistency check skipped."` 消息逐字保持。新增 1 条反相用例 `test_lock_consistency_non_utf8_skips_without_raise`（断言 skipped 含 `unparseable` + format 投影含 `invalid_json`，验证面3收口与一致性路径的协作）。独立复现：§三.1 探针面 C。注：修复声明写「L17571」为行锚微偏（L17571 是空文件 skipped 行），实际改动行 = R0 指认的 L17574，位置正确 |
| **F-3** 工作树混入 8 个非本任务文件 | P2 | **维持（未修复，非代码面）** | `git status --porcelain` 仍含 lib/index.js、test_dsh_adapter.py、test_loop_runtime_claims.py、test_verify_workflow.py、env_failure_classification.json、docs/requirements ×2 共 8 个修改 + 2 个未跟踪审查报告。提交边界责任在 Coordinator（§七指令） |
| **F-4** 插件元数据探测捕获面 | P3 | **维持披露（未修复）** | L17284 / L17298 仍为 `except (json.JSONDecodeError, KeyError, IOError)`，本轮零触碰（diff 无该区域 hunk） |
| **F-5** 面3 测试断言精度 | P3 | **维持披露（未修复）** | `test_non_utf8_locks_and_packets_fail_closed_not_raise` 锁面仍仅断言 `FAIL + issues 非空`，未断言投影 type（本轮 F-2 用例的 `invalid_json` 断言属 Check26 路径，非该用例） |
| **F-6** 捕获面风格不统一 | P3 | **维持披露（未修复）** | 面1/2 仍为宽面 `+ValueError`（L22456/L22480），本轮新面用精确 `UnicodeDecodeError`——风格差异仍在，可选清理项 |
| **F-H**（Design R0 P2 随批）模板「唯一豁免出现」失实句 | P2（Design） | **已修复** | L149 单句改写为「本节负相示例为该字面串在本模板中的唯一**代码示例赋值形态**出现（其余出现均为行文引用或 ❌ 清单条目，非可执行赋值语句）」——恰为 Design R0 建议变体。微核见 §四.3 |
| 新引入面 | — | **无** | §四.4 |

## 三、独立复现核验（Reviewer 自建，不重用开发者测试代码）

### 1. 三面 GBK 探针（`%TEMP%\fix333_r1_review\probe_r1.py`，自建载荷）

| 面 | 载荷 | 干净 HEAD 基线副本 | 工作树（修复后） |
|---|---|---|---|
| A = F-1 record 面 | GBK 编码 triage record JSON（中文载荷 `ensure_ascii=False`）+ UTF-8 evidence | **ESCAPED `UnicodeDecodeError`: `'utf-8' codec can't decode byte 0xb7 in position 53`** | **STRUCTURED**：`triage record unreadable after write: 'utf-8' codec can't decode byte 0xb7 in position 53`（消息前缀保持 + codec 细节内插） |
| B = F-1 evidence 面 | GBK 编码 evidence-log（TRIAGE 行族）+ UTF-8 record | **ESCAPED `UnicodeDecodeError`: `byte 0xb1 in position 49`** | **STRUCTURED**：`evidence-log unreadable after write: 'utf-8' codec can't decode byte 0xb1 in position 49` |
| C = F-2 Check26 一致性路径 | GBK 编码 `.governance/agent-locks.json`（`GOVERNANCE_DIR` mock 重定向至 %TEMP%） | **ESCAPED `UnicodeDecodeError`: `byte 0xb4 in position 159`** | **STRUCTURED**：`skipped='agent-locks.json is unparseable — lock consistency check skipped.'` + 1 条 format issue（`invalid_json` 投影） |

**结论：三面「Never raises / 结构化而非逸出」契约在修复后成立；基线三面全逸出证明缺陷真实、修复非自证。** 探针全程 %TEMP% + mock 常量重定向，仓库 `.governance/` 零访问。

### 2. 测试套件 RED→GREEN（%TEMP% 基线副本 = `git show HEAD:` 字节重定向 + 工作树测试文件 + infra 依赖副本）

| 运行 | 结果 | 裁决 |
|---|---|---|
| 基线（HEAD，三面未修）`pytest -k "non_utf8 or lock_consistency"` | **6 failed**（R0 3 条 + R1 新 3 条全 RED；失败机制 = `<frozen codecs>` UnicodeDecodeError 逸出），32 deselected | ✅ 新增用例为真守卫 |
| 工作树全量 `test_triage_write_guard.py -q` | **38 passed in 0.26s**（35 → 38 与声明一致） | ✅ GREEN |
| `test_change_triage.py -q`（工作树） | **92 passed, 1 failed**——唯一 FAIL = `test_cli_success_expected_new_and_warn_disclosure` | ✅ 与声明一致 |

### 3. 唯一 FAIL 的日期炸弹定性（独立实证，非本改动引入）

- 机制：`_triage_record_for_lock` 默认 `created_at="2026-09-10"`（test_change_triage.py L1179 硬编码）+ `cross_check_triage_files`「同期=当日 only」语义（L1211-1217 注释自证：created another day → None → silent）⇒ 运行日 ≠ 2026-09-10 时 WARN 披露永不触发 ⇒ L1515 `assertIn("WARN", done.stderr)` 必炸。
- HEAD 基线复现：干净基线上同一用例 **同位置 L1515 AssertionError 失败**——HEAD 无任何 FIX-333 改动仍炸 ⇒ 既有失败，与本轮 except 扩面（UnicodeDecodeError 路径，UTF-8 CLI 流不可触达）零交集。
- 处置：登记为观察 N-1（§七），属 change-triage 测试域自有维护项，不在 FIX-333 范围。

### 4. archguard + 行恒等 + check-governance

| 项 | 命令/方法 | 结果 |
|---|---|---|
| archguard | `verify_workflow.py archguard-ratchet` | **PASS（0 violations）**：R1 mainfile loc **24453 ≤ 24453**（only-down）；R2 47/47；R4 print 1299 ≤ 1299；R5 cli 84/84 frozen；R6 cold import 196 Δ0；R7 regen deterministic=True、committed==fresh True（**无需 --regen**，与声明一致） |
| 行中性（文件粒度） | HEAD 副本 vs 工作树 `(Get-Content).Count` | **24453 == 24453 恒等**；numstat：verify_workflow.py 10+/10− = R0 7/7 + 本轮 **3 处等行替换**（1/1、1/1、2/2）；测试 +155 = R0 +87 + 本轮 +68；模板 +16/−0（F-H 净行变化 0 = 单句原位改写） |
| check-governance | `verify_workflow.py check-governance` | PASS（0 failing criterion），67 issues——与修复声明 endpoint 一致（+1 为 R0 报告自身 ragged-table accounting 项，属报告产物非改动面，知悉不改） |

## 四、行中性 / F-H 微核 / 无新引入面

1. **diff 形态**：vs HEAD 共 7 hunk / 10 等行替换——R0 已审 5 hunk（12700/17423/22435/22453/22477）逐字保持原样；本轮新增恰 3 hunk（17571→17574、22188-22197×2），全部等行替换，无行为外改动。
2. **消息面兼容**：三面既有消息字符串逐字保持（record/evidence/skipped-unparseable）；`UnicodeDecodeError` 的 str 仅含 codec 与字节位置、不含路径 ⇒ detail 内插无新增泄露面。
3. **F-H 微核**：字面串 `$home =`（大小写不敏感）在模板实存 **4 处**——L146×1（fenced code 内 ❌ 负相示例 = 唯一代码示例赋值形态）、L149×2（规则行文 inline code）、L200×1（❌ 清单条目）——与 L149 改写句声明完全自洽，且与 Design R0 的计数（L146 + L149×2 + L200）一致。改写范围 = L149 单句（Design R0 finding 原文「唯一豁免出现」vs 现文对照实证）；vs HEAD 模板仅 FIX-337 批次 2 hunk（+16/−0），F-H 净行变化 0。如实注记：该 section 整体未提交，无 F-H 改写前的已提交基线可做句级 diff——「前后文零改动」在现有可证粒度（Design R0 原文对照 + vs HEAD hunk 边界）下成立。
4. **无新引入面**：3 条新增 except 仅把解码失败转入既有结构化 FAIL/skipped 通道（fail-closed 方向，无静默 PASS 通道）；try 块内容零改动；F-4 维持面（L17284/L17298）确认未触碰；全仓同型残留面集合与 R0 扫描结论一致（无第五处新遗漏进入本轮 diff 范围）。

## 五、except 精确面变体裁决（R1 指定重点）

开发者选择精确 `UnicodeDecodeError`，而非 R0 修复建议中并列给出的 `+ValueError` 宽面变体。**裁决：成立且更优。**

- R0 原文即「二选一与仓内风格对齐即可」——两变体均为预授权选项，不构成偏离。
- 覆盖充分性：三个 try 块均为常量 `encoding="utf-8"` 的读取（open+read / read_text），现实异常域 = OSError/IOError（原已捕获）∪ UnicodeDecodeError（本轮补捕）；不存在现实的第三类 ValueError 源（假想的非常量 encoding 属编程错误，本就不应吞）。
- 方向一致性：与面3/4 的精确风格对齐，恰是 R0 F-6 期望的统一方向；面1/2 的历史宽面维持披露不变。
- fail-closed 保持：三面均转结构化 issue/skipped，无静默 PASS 通道（§四.4）。

## 六、五维度逐项结论 + AI 专项（本轮 3 hunk + 3 用例 + 1 句）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | §三 三面探针双态对照 + §三.2 RED→GREEN + 消息逐字保持 |
| 安全性 | ✅ 通过 | 结构化通道无注入面；detail 无路径泄露；fail-closed 无静默 PASS |
| 可维护性 | ✅ 通过 | 与面3/4 风格统一（§五）；docstring/用例 docstring 与实现一致；F-6 残差为既有披露 |
| 性能 | ✅ 通过 | 仅异常路径扩面，零热路径影响；archguard R6 Δ0 |
| 测试覆盖 | ✅ 通过 | 契约面覆盖：4 面（R0）+ 3 面（R1）= 7 面 GBK 反相全绿；断言含消息前缀 + codec 细节 + skipped/投影类型 |

**AI 专项 5 项**：① mock 残留：无（`mock.patch.object` 仅重定向模块常量至 %TEMP%，合法隔离手法）；② 硬编码返回值：无；③ 幻觉 API：无（`UnicodeDecodeError` 为真实内置异常）；④ 未实现 TODO：无；⑤ 过度实现：无（最小 except 扩面 + 聚焦用例）。

## 七、遗留项（非阻塞）与 Coordinator 指令

| 项 | 级别 | 处置 |
|---|---|---|
| F-3 提交边界 | P2 | **Coordinator MUST**：FIX-333 commit 精确 `git add skills/software-project-governance/infra/verify_workflow.py skills/software-project-governance/infra/tests/test_triage_write_guard.py`；其余 8 个修改文件由各自任务（FIX-346 / FIX-337-Design 批等）走各自 commit/审查边界。注意：`agent-dispatch-template.md` 整体属未提交的 FIX-337 Design 批（F-H 单句位于其中，无法单独提交一句）⇒ 该文件随 Design 批入库与否由 Coordinator 按 Design R0 处置决策执行 |
| F-4 | P3 | 维持披露（插件元数据探测，触发面窄，可后续批收口） |
| F-5 | P3 | 维持披露（面3 锁面断言精度，可选） |
| F-6 | P3 | 维持披露（面1/2 宽面风格统一，可选） |
| N-1（新观察） | P3（域外） | `test_change_triage` 日期炸弹（`created_at="2026-09-10"` 硬编码 × 同期=当日 only ⇒ 2026-09-10 之外的任何运行日必炸，HEAD 同位置复现）——属 change-triage 测试域自有维护项，建议由该域任务刷新测试日期基准或改相对日期，不入 FIX-333 范围 |

## 八、审查过程披露（证据完整性）

R1 前期一次基线构建事故：全量拷贝 infra `*.py` 时工作树（已修复）`verify_workflow.py` 覆盖了先前的 HEAD 基线副本，导致一轮「基线」探针/pytest 实际运行了修复后代码（6 passed 假象）。**已发现、已废弃该轮结果，并以 `git show HEAD:` 字节级重建基线 + 删除 `__pycache__` + Select-String 反向验证（无 FIXED-LEAK 行）后全部重跑**——本报告 §三/§四 全部数据来自干净基线复跑。事故未触碰仓库任何文件（全程 %TEMP%）。

---

**结论：APPROVED_WITH_NOTES（unresolved_blockers=0，复审链关闭）。** F-1/F-2 修复精确、消息语义逐字保持、独立复现双态闭环；F-H 按建议改写且语义自洽；行中性三重实证（24453 恒等 + numstat + archguard only-down）；无新引入面。遗留 F-3/F-4/F-5/F-6 + N-1 均非阻塞，处置指令见 §七。
