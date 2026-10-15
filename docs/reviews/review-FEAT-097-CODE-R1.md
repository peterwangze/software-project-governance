# FEAT-097 Code Review R1 — goal 与预算桥接（R0 NEEDS_CHANGE 强制复审）

- **轮次**: R1（复审）
- **前轮引用**: `docs/reviews/review-FEAT-097-CODE-R0.md`（R0 结论 NEEDS_CHANGE：P1×1 + P2×4 + P3×6）；机器记录 `.governance/review-FEAT-097-R0.md`（next_round=REVIEW-FEAT-097-R1）
- **审查方**: Code Reviewer Agent（只读审查；唯一写面 = 本报告；未修改产品代码、未触碰 `.governance/`、未 commit）
- **复审范围**: 聚焦复审——逐条核验 R0 P1-1 / P2-1~P2-4 在当前工作区的修复事实（按任务约束不重复 R0 已独立验证的全量面：全模块 1115 套件、check-injection-budget、check-architecture-health 未重跑，见 §6 说明）
- **审查对象**: 工作区未 commit 变更（HEAD `bf6942d`；`git status --porcelain` = 12 M + 3 ??，其中 ?? = R0 报告 / goal_bridge.py / test_goal_bridge.py；R0 期残留 `_tmp_suite097.log` 已消失——P3-1 已修复）
- **结论**: **NEEDS_CHANGE**（P0=0；P1×1 新引入——守护套件 RED；P2×5：R0 四项修复的测试半边缺失 + P2-4 整项未动）

---

## 0. 结论与理由

**NEEDS_CHANGE ｜ P0=0 ｜ P1×1（新引入·本轮必须修复） ｜ P2×5 ｜ P3×2**

**任务前提修正（重要事实）**：任务上下文称「当前实现尚未返工」——与当前事实不符。工作区 `goal_bridge.py` 已从 R0 期的 916 行增至 1040 行，**包含 R0 全部四项生产面修复**（P1-1 锁 / P2-1 对称授权 / P2-2 版本披露 / P2-3 真键）。前次会话实际完成了生产代码返工但**未同步测试面**（`test_goal_bridge.py` 与 R0 引用行号逐一吻合、仍为 26 测试，未新增任何用例），且复审链在 R1 记录前中断。本报告基于当前事实逐条判定。

**生产面四项修复全部实证成立**（详见 §1）：三变更函数跨进程锁争用探针三入口全拒（lock_contention/retryable）、CHECKPOINTED 无授权 resume 拒绝+留痕、record 路径 rules_version 响亮披露、账本面五键全为 authority_ledger.status 真键。R0 核心竞态（用户裁决被旧快照写回复活）在生产面已被 per-goal `_TargetLock` 关闭。

**但返工是半程的**：① `test_resume_with_different_rules_version_is_loud`（test_goal_bridge.py:257-270）仍以无授权 `continue` 调用 ruling 并断言成功——与 P2-1 修复后的生产代码直接矛盾，**实跑 FAILED（26 测试 1 失败，exit 1）**，守护套件 RED，违反 reliability 预算「全套件回归零退化」；② R0 §7 返工提示中与四项修复配对的回归用例（并发/对称红测/跨版本 record/真键断言/边界×2）**一条都未落地**——修复处于无测试看护状态。故 NEEDS_CHANGE（R1 < 3，未触熔断）。

---

## 1. R0 findings 逐条比对（已修复 / 部分修复 / 未修复 / 新引入）

| # | R0 finding | 判定 | 证据（一手） |
|---|-----------|------|------|
| **P1-1** | 三变更函数 RMW 无锁（丢失更新竞态） | **部分修复——生产面✓已修复，回归用例✗未补** | 生产面：`goal_bridge.py:510-522`（record_execution）/`:624-636`（write_checkpoint）/`:704-716`（record_ruling）均 `from governance_store import StoreError, _TargetLock`（函数内导入）+ `with _TargetLock(path, timeout_seconds)` 包裹全部 load→mutate→save；`StoreError`→`CODE_LOCK_CONTENTION`（disposition retryable，:517-522/631-636/711-716）。锁原语核验：`governance_store.py:511-585` `_TargetLock` = per-target O_EXCL lockfile（`<parent>/.locks/<name>.lock`）+ 进程内互斥 + 600s stale 接管；`StoreError.payload` 存在（:282-287），`exc.payload.get("detail")` 用法成立。**跨进程探针实证**（隔离临时目录 `%TEMP%\feat097-r1-*.py`）：外部进程持锁时 record/checkpoint/ruling 三入口均返回 `{"error": true, "code": "lock_contention", "disposition": "retryable"}`；crash 遗留孤锁同样 lock_contention（600s stale 接管为文档化恢复路径——`governance_store.py:518-531`）。锁路径无嵌套获取（`authority_ledger.status` 只读不取锁）——无死锁面。26 测试中 25 绿证明正常 acquire/release 循环无破坏。**缺口**：`test_goal_bridge.py` grep `lock|contention|concurren|thread|race|_TargetLock` 零命中（18 处匹配全为 "blocked" 子串噪声）——R0 §7① 要求的并发回归用例未落地（→ 新 P2-R1-A） |
| **P2-1** | CHECKPOINTED 恢复面与 BLOCKED 授权标准不对称 | **部分修复——生产面✓已修复（精确按 R0 建议），测试面✗未同步且既有测试被打破（→ 新 P1-R1）** | 生产面：`goal_bridge.py:731-746` CHECKPOINTED 分支新增 `if (decision != "abort" and not str(authorized_by or "").strip())` → 拒绝（CODE_UNAUTHORIZED_RESUME）+ `unauthorized_attempts` 留痕（kind=resume）；abort 豁免（安全方向）——与 R0 建议「continue/extend-budget/reduce-scope 要求 authorized_by 非空；abort 可豁免」逐字吻合。BLOCKED 面（:780-793）保持原对称语义。**但**：对称红测未新增；且 `test_goal_bridge.py:262-264` 既有测试以 `ruling(decision="continue", rules_version="999.0.0-future")`（无 authorized_by）断言 `assertFalse(result.get("error"))` —— 实跑 FAILED：`AssertionError: True is not false : {'error': True, 'code': 'unauthorized_resume', ...}`（即 :741-746 拒绝文案，GBK mojibake 为 pwsh 解码显示问题、非产品缺陷） |
| **P2-2** | record_execution 不比对 rules_version | **部分修复——生产面✓已修复，用例✗未补** | 生产面：`goal_bridge.py:451-471` 新增 `_rules_version_disclosure`（比对 `_default_rules_version()` vs `artifact["rules_version"]`，mismatch 追加 `rules_version_changed` history 行 + re-pin，披露不阻断——DEC-330 语义）+ `:532` 在 `_record_execution_locked` 内 load 后调用（record 路径每变必走）。缺口：唯一跨版本测试（:257-270）只走 ruling 路径（且当前红），record 路径跨版本用例未新增（→ P2-R1-C） |
| **P2-3** | `_ledger_summary` 读幻觉键 `events_total` 恒 null | **部分修复——生产面✓已修复，断言✗未补** | 生产面：`goal_bridge.py:269-300` 现读 `integrity.lines`/`integrity.last_seq`/`integrity.ok`/`open_recheck_obligations`/`open_recheck_obligation_keys`——与 `authority_ledger.py:1503-1523` `status()` 实际返回键逐一比对**全为真键**（integrity 面 :1509-1512、义务面 :1514-1521）；`events_total` 已不存在于模块（全文读确认）。缺口：`test_goal_bridge.py:226` 仍只断言 `available ∈ (True, False)`，真键非 null 断言未补（→ P2-R1-D） |
| **P2-4** | 危险区边界等号 + 多维同时 danger 零测试 | **未修复（纯测试缺口，原样存在）** | `test_goal_bridge.py:107-133` 仍只有四维**独立**注入（80%/80%/1.58×/1.8×）+ warning-alone（65%）；无 `rounds=42`（恰 0.70×60 边界等号）用例、无多维同时 danger 用例。生产 `share >= danger_ratio`（`goal_bridge.py:330`）R0 已裁定语义正确——该项本就只是测试缺口 |
| **P3-1** | `_tmp_suite097.log` 未申报残留 | **已修复** | `Test-Path _tmp_suite097.log` → ABSENT；`git status --porcelain` 无此文件（untracked 第 15 位由 R0 报告本身取代） |

R0 其余 P3-2~P3-6 为讨论级遗留（R0 已裁定可遗留），本轮不重复核验、维持遗留状态。

---

## 2. R1 新发现

### P1-R1（关键·新引入·本轮必须修复）守护套件 RED——返工只改生产代码未同步既有测试

- **位置**: `skills/software-project-governance/infra/tests/test_goal_bridge.py:257-270`（`test_resume_with_different_rules_version_is_loud`）对照 `infra/goal_bridge.py:731-746`（P2-1 修复）。
- **事实**（一手）: 实跑 `python -m unittest skills/software-project-governance/infra/tests/test_goal_bridge.py -v` → **`Ran 26 tests in 0.697s — FAILED (failures=1)`**（exit 1）。失败点：测试以 `decision="continue"` 无 `authorized_by` 调用 ruling 并断言无错误；P2-1 修复后的生产代码按设计拒绝（unauthorized_resume）。生产行为正确（精确实现 R0 §7③ 建议），**过时的是测试**。
- **影响评估**: 违反 quality_budget.reliability「全套件回归零退化」与 done_definition「全套件回归零退化」；模块守护面处于 RED 状态，任何 CI/收口命令跑该模块即失败。修复为一行量级（见 §8-F1），无设计争议。
- **修复建议**: 该测试调用补 `authorized_by="user"`——授权 continue 路径同样经过 `:764-773` 的 rules_changed 披露逻辑，原断言（`rules_version_changed` 为真 + `mixed==1`）在修复后全部保持成立（已对照代码路径核验）。

### P2-R1-A（建议·原则上本轮修）P1-1 修复缺并发回归用例——核心竞态修复处于无看护状态

- **事实**: R0 §7① 明示「补并发回归用例（两真子进程或 monkeypatch 旧快照注入——探针可直接转正为用例）」；当前测试文件零并发/锁用例（grep 证实，§1 P1-1 行）。未来重构若静默移除 `with _TargetLock(...)` 无任何测试会红——R0 级竞态将无防护网回归。
- **建议**: 本轮探针可直接转正：①外部持锁（子进程 `_TargetLock.__enter__` + sleep）时三入口断言 `code == "lock_contention"`；②串行化语义用例——ruling(abort) 落盘后，基于旧快照的 racing refuse 不再能抹除裁决（锁使 load→save 原子化）。

### P2-R1-B（建议·原则上本轮修）P2-1 修复缺对称红测

- **事实**: R0 §7③ 要求「对称性红测」；当前无用例断言「CHECKPOINTED 无授权 continue/extend-budget/reduce-scope 被拒 + 留痕、abort 无授权仍放行」。
- **建议**: `ResumeAuthorizationTests` 补：无授权 `continue` → `assertRefused(CODE_UNAUTHORIZED_RESUME)` + `unauthorized_attempts` 有 kind=resume 行；无授权 `abort` → 无错误进 BLOCKED。

### P2-R1-C（建议·原则上本轮修）P2-2 修复缺跨版本 record 路径用例

- **事实**: R0 §7④ 要求「补一条跨版本 record 用例」；`_rules_version_disclosure`（:451-471）当前无任何测试触达（唯一跨版本测试走 ruling 路径）。
- **建议**: monkeypatch `gb._default_rules_version` 返回新版本后 `record` → 断言 history 出现 `rules_version_changed` 行且 `rules_version` re-pin。

### P2-R1-D（建议·原则上本轮修）P2-3 修复缺真键非 null 断言

- **事实**: R0 §7② 要求「测试补断言非 null（修复后）」；`test_schema_carries_all_five_faces`（:224-226）仍只断言 `available ∈ (True, False)`。
- **建议**: ledger available=True 时断言 `events_lines`/`last_seq` 非 None（真键读真值）。

### P2-R1-E（=R0 P2-4 原样）边界等号与多维交叉用例仍缺

- **事实**: 见 §1 P2-4 行——`rounds=42`（恰 70%×60，`share >= danger_ratio` 等号位）与 rounds+tokens 双 danger（`danger_dimensions` 多维列表）两用例均缺。
- **建议**: `BudgetDangerZoneTests` 补两条：`judge_budget(rounds=42, …)` → `zones["rounds"]["zone"]=="danger"`；`rounds=48 + tokens=1_600_000` → 两维同 danger。

### P3-R1-1（讨论）票面验收命令不覆盖 goal_bridge 模块守护套件

- **事实**: execution-packet `acceptance_contract.command` = `python -m unittest …/test_verify_workflow.py -v && … check-governance --summary-only`——只跑 test_verify_workflow.py（1115 面，含 5 条接线测），**不含 test_goal_bridge.py 的 26 条模块测**；`demo_path` 的 `-k goal_bridge` 同样只命中接线测。P1-R1 的 RED 在票面验收命令下不可见。
- **建议**: 收口时把 `…/test_goal_bridge.py` 追加进验收命令（或 EVD 行以两条 unittest 命令分别落证据）。

### P3-R1-2（讨论）pwsh 裸跑 unittest 输出中文 detail 呈 mojibake

- **事实**: 本轮失败断言的 detail 字段在 pwsh 管道下显示 GBK mojibake（FIX-278 同型面；产品 JSON 本身 UTF-8 正确、`_configure_stdio` 已做 reconfigure——问题仅在捕获管道编码）。
- **建议**: Developer 复现时以 `[Console]::OutputEncoding=[Text.Encoding]::UTF8` 前置或直接读 JSON；不影响产品，登记讨论即可。

---

## 3. 五维度结论（硬门槛 ②；聚焦复审——R0 全量结论继承，本节记增量）

| 维度 | 结论 | 增量依据（一手） |
|------|------|------|
| **正确性** | **PASS（带 P1-R1/P2-R1-E）** | R0 四项正确性缺陷的生产面修复全部实证（§1）；锁集成未破坏状态机行为（25/26 绿 + 接线 5/5 绿）；新缺陷=测试-生产矛盾（P1-R1）与边界用例缺（P2-R1-E），非生产行为错误 |
| **安全性** | **PASS（增强）** | P2-1 修复使 CHECKPOINTED 恢复面与 BLOCKED 面授权标准对称——SKILL 第 10 条「禁静默续跑」协议门从「仅呈现契约」升级为「模块门强制」；P1-1 修复消除用户裁决+审计被抹路径（RPG 流氓并行 actor 威胁模型关闭） |
| **可维护性** | **PASS（带 P2-R1-A~D）** | 锁手法与 FEAT-096 R1 协议先例同型（函数内导入 + per-goal 锁 + retryable 错误码）；三函数公共/锁体拆分（`_*_locked`）结构清晰；缺口=修复无测试看护（§2） |
| **性能** | **PASS** | 锁为 per-goal 无争用（单 Coordinator 顺序路径零等待）；judge ≤10ms 守护用例绿（:386-398）；锁超时 10s 默认 + retryable disposition 不阻塞轮间毫秒级预算 |
| **测试覆盖** | **FAIL→NEEDS_CHANGE 依据** | 26 测试 1 失败（P1-R1）——套件 RED；R0 §7 要求的 5 组新用例零落地（P2-R1-A~E）；接线 5/5 绿 |

---

## 4. AI 代码专项 5 项（硬门槛 ⑤；对返工增量）

| 项 | 结论 | 依据 |
|----|------|------|
| mock 残留 | **无** | goal_bridge.py 全文读：无 mock/Mock/pdb/breakpoint；测试侧 `unittest.mock`/`mock_env` 为正当工具 |
| 硬编码返回值 | **无** | 新增代码无业务硬编码；timeout/阈值均为配置面常量 |
| 幻觉 API 调用 | **无（R0 P2-3 已修复）** | `_TargetLock`/`StoreError`/`authority_ledger.status` 五键全部经实读核验为真实 API 与真实返回键（governance_store.py:282-287/511-585；authority_ledger.py:1503-1523） |
| 未实现 TODO | **无** | 全文读零 TODO/FIXME |
| 过度实现 | **无** | 返工增量 = 恰好四项 R0 findings 的最小修复面 + 错误码/文档注释；无越面功能 |

---

## 5. 设计一致性（硬门槛 ④；聚焦复审）

- **non_goals×3**: 返工未触碰——锁为工件写入内部协议（不涉 harness goal 重造）；`_rules_version_disclosure` 强化 DEC-330（披露不阻断、仍无 mid-session 热升级）；对称授权仍在 095 边界内的协议+CLI 门（authorized_by=调用方断言）。**符合**。
- **quality_budget**: reliability 当前**不达标**（套件 RED，P1-R1）——这是本轮 NEEDS_CHANGE 的直接预算依据；security 增强（§3）；其余维度的 R0 验证继承（本轮未重跑的 face 见 §6 说明）。
- **allowed_change_scope**: 返工增量限于 `goal_bridge.py`（票面文件）；测试文件未改（正是缺口本身）。

---

## 6. 验证命令与输出（审查者独立实跑）

| # | 命令/动作 | 结果 |
|---|-----------|------|
| 1 | `python …/verify_workflow.py execution-packet --task FEAT-097` | 短包读取成功（allowed_change_scope/quality_budget/scope_guard 与 R0 一致） |
| 2 | `git rev-parse HEAD` + `git status --porcelain` | HEAD `bf6942d`（与 R0 一致）；12 M + 3 ??；`_tmp_suite097.log` 不在列表 |
| 3 | `python -m unittest …/test_goal_bridge.py -v` | **Ran 26 tests in 0.697s — FAILED (failures=1)**（exit 1；失败=`test_resume_with_different_rules_version_is_loud`，unauthorized_resume）——P1-R1 证据 |
| 4 | `python -m unittest …/test_verify_workflow.py -k Feat097GoalBridgeWiring -v` | **Ran 5 tests in 0.051s — OK** |
| 5 | 跨进程锁争用探针（`%TEMP%\feat097-r1-lockprobe.py`，隔离临时目录） | 外部持锁：record/checkpoint/ruling 三入口均 `error=True code=lock_contention disposition=retryable`——P1-1 生产面修复实证 |
| 6 | 孤锁探针（`%TEMP%\feat097-r1b-probe.py`） | crash 遗留锁文件 → `lock_contention`（600s stale 接管为恢复路径，无数据损坏） |
| 7 | `Test-Path _tmp_suite097.log` | ABSENT——P3-1 已修复 |
| 8 | grep `lock|contention|concurren|thread|race|_TargetLock` 于 test_goal_bridge.py | 零相关命中——P2-R1-A 证据 |

**未重跑面（按任务约束聚焦复审）**: 全模块 1115 套件、check-injection-budget、check-architecture-health、check-governance——R0 已独立验证且返工增量限于 `goal_bridge.py`（infra 代码，非注入面/模板面）；`test_goal_bridge.py` 与 SKILL/模板文件相对 R0 引用行号逐一吻合（推断未被返工触碰，测试缺口本身即证据）。若 Coordinator 要求 R2 前全量回归，按票面验收命令执行即可。

---

## 7. 硬门槛自检（输出前）

| 门槛 | 判定 |
|------|------|
| P0 阻塞问题数 = 0 | ✓（P0=0；P1×1 显式声明「本轮必须修复」——NEEDS_CHANGE 依据） |
| 5 维度 100% 覆盖 | ✓（§3 逐项有结论） |
| 每条发现 P0~P3 + 文件:行号 + 事实 + 建议 | ✓（§1/§2 四要素齐备） |
| R0 findings 逐条 已修复/未修复/新引入 比对 | ✓（§1 六行判定表） |
| round 号 + 前轮引用声明 | ✓（报告头） |
| round ≥ 3 仍 BLOCKING → 建议 BLOCKED | 不适用（R1 < 3） |
| 设计一致性 + AI 专项 5 项 | ✓（§4/§5） |
| 事实依据红线 | ✓（每条判定指向行号/命令输出/探针输出；未重跑面如实标注 §6） |

---

## 8. 给 Governance Developer 的精确修复清单（R2 注入用）

按依赖顺序（F1 独立且一行量级；F2~F6 均为测试新增，互不依赖可并行）：

- **F1（P1-R1·必须）** `test_goal_bridge.py:262-263`：`self.ruling(decision="continue", rules_version="999.0.0-future")` → 补 `authorized_by="user"`。修复后原断言（无错误 / `rules_version_changed` 为真 / mixed==1）全部保持成立（已对照 `goal_bridge.py:747-778` 授权路径核验）。预期：26/26 绿。
- **F2（P2-R1-A）** 新增并发回归用例（可直接转正本轮探针）：①子进程持 `_TargetLock(artifact)` 时三入口断言 `code=="lock_contention"`；②ruling(abort) 落盘后 racing refuse 不得抹除裁决（串行化语义）。
- **F3（P2-R1-B）** 新增对称红测：CHECKPOINTED 无授权 `continue` → `assertRefused(CODE_UNAUTHORIZED_RESUME)` + kind=resume 留痕；无授权 `abort` → 放行进 BLOCKED。
- **F4（P2-R1-C）** 新增跨版本 record 用例：monkeypatch `_default_rules_version` → record 后断言 `rules_version_changed` history 行 + re-pin。
- **F5（P2-R1-D）** `test_schema_carries_all_five_faces` 补真键断言：available=True 时 `events_lines`/`last_seq` 非 None。
- **F6（P2-R1-E）** `BudgetDangerZoneTests` 补两条：`rounds=42` → danger（边界等号）；`rounds=48 + tokens=1_600_000` → 双维 danger。
- **F7（P3，收口时顺手）** 票面验收命令追加 `…/test_goal_bridge.py`（P3-R1-1）；EVD 行以当场命令输出为准。

修复后预期结论路径：**APPROVED**（若 F2~F6 全落地）或 **APPROVED_WITH_NOTES**（若 F2~F6 部分遗留——须 unresolved_blockers=0 且 P1-R1 已闭）。
