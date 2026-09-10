# REVIEW-FEAT-019-CODE-R0 — ArchGuard 棘轮 R1~R7（工作树 diff，commit 前置）

- **Round**: R0（首轮）
- **Reviewer**: Code Reviewer Agent（`agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行）
- **对象**: 未提交工作树改动（`git diff HEAD` + 3 新文件）
- **方法**: 只读审查——git 只读 + 逐行读全文 + 独立交叉印证（行数/行号/提交史/grep 消费点）；测试结果采信 Developer 声称并标注边界（§9）
- **日期**: 2026-09-10

## 0. 变更面清单（git status 实测）

| 文件 | 状态 | 面积 |
|---|---|---|
| `skills/software-project-governance/infra/archguard_ratchet.py` | 新增 | 1,106 行（实测全文读取，行数吻合） |
| `skills/software-project-governance/core/architecture-baseline.json` | 新增 | 548 行 |
| `skills/software-project-governance/infra/tests/test_archguard_ratchet.py` | 新增 | 444 行 |
| `skills/software-project-governance/infra/verify_workflow.py` | 修改 | +18/−0 |
| `skills/software-project-governance/infra/contract_matrix/snapshots.json` | 修改 | +5/−4 |
| `skills/software-project-governance/infra/tests/test_contract_matrix.py` | 修改 | +6/−1 |

## 1. R1~R7 判定实现正确性（逐项）

### R1 物理行锚 — 核实通过
- `physical_line_count`（archguard_ratchet.py:136-149）显式钉死 ReadAllLines 口径：仅拆 CRLF/LF/CR、尾换行不产幻影行、空文本=0——避开 `str.splitlines` 对 `\x0b/\x0c/\u2028` 的额外拆分。口径正确。
- **独立印证**：本审查用 .NET `ReadAllLines` 同口径实测引擎 = **24,302 行**，与 baseline `anchor_loc`（architecture-baseline.json:17）一致；文件末行 `main()` 恰在第 24,302 行。
- 负对照测试真实：+1 行→FAIL（excess_lines==1，test:54-68）；手改锚 −1→FAIL（test:70-74，only-down 双向切割）。

### R2 反向依赖三 kind — 核实通过
- 扫描面（archguard_ratchet.py:231-274）：`ast.Import`（`import verify_workflow` 含 `as` 别名）+ `ast.ImportFrom`（`from verify_workflow import`，含相对导入）计 `import_vw`；`def _vw` 计 `vw_def`；`Call(Name("_vw"))` 计 `vw_call`。函数内 deferred import 同样被 `ast.walk` 捕获（manifest.py:41 的 `# noqa: WPS433` deferred import 即实证）。
- **fail-closed 设计正确**：不可解析文件计 `parse_error` kind（:256-258），无预算即违规——不可扫描文件无法藏匿导入。
- 判定语义（:277-315）：按 `(path, kind)` 计数预算制，**只比对 count、容忍行号漂移**（lines 仅记录展示）——与 evolution §4.3"基线清单长度单调不增"一致；新文件零容忍（预算缺省 0）。
- **46 站点独立核算**：inventory 36 条 count 之和 = 6+3+3+3+6+3+3+3+4+1+3+3+4+1 = **46** ✓。
- **行号抽查 14/14 全中**：`checks/manifest.py`（33/41/47/51/55/323）、`loop_health.py`（38/47/59/370）、`checks/review_domain.py`（61/69/113）、`loop_migration.py:1195`（`from verify_workflow import (` 形式——ImportFrom 正确计入 import_vw）。committed baseline 与当前树一致的强佐证。
- 过期 fuse 语义（:287-297）：inventory 条目到期即无条件违规（催促清理+regen 落账）——与 R7"任何引擎变更后必须 regen"形成闭环，无假阳性/假阴性缺口。

### R3 十二边矩阵 + Tarjan SCC + 管辖集 — 核实通过
- 枚举实测：L6→{L5,L4,L3,L2,L0}(5) + L5→{L4,L0}(2) + L4→{L3,L2,L0}(3) + L3→L0(1) + L2→L0(1) = **12** ✓；`ASSERTED_EDGE_COUNT=12` 的派生断言（W1 guard，:329-335）在引擎与测试双侧生效（test:147-159 还断言了 C(6,2)=15 误读会错误放行的 forbidden trio L5→L3/L5→L2/L3→L2 不在矩阵中）。
- **迭代 Tarjan 逐行核实正确**（:407-456）：迭代器栈推进/回溯、子节点完成后 `lowlink[parent] = min(lowlink[parent], lowlink[node])` 传播、`on_stack` 判定、根条件弹栈成 SCC——标准算法的无递归实现，2-cycle 负对照（test:168-183）断言 `max_scc_size==2` 且同时抓 forbidden edge。
- 管辖集 v1 仅自身（DEFAULT_MANAGED_MODULES 1 条，接入日政策）与 baseline `legacy_note` 一致；非管辖目标的 import 披露为 `unmanaged_target_refs`（archguard_ratchet 对 contract_matrix.generator 的 lazy edge 即被诚实披露，test:166 断言披露非空）。
- 边界处理：未知 layer → 违规（:355-361）；自环跳过（:391-392）；stdlib 判定用 `sys.stdlib_module_names`（3.10+，与项目 Python 族钉 3.11/3.14 相容）。

### R4 print 归属双粒度 — 核实通过
- 归属算法（:481-505）：递归 descent，FunctionDef/AsyncFunctionDef 换 owner，嵌套函数得限定名（`cmd_check_sequential_ids._report` 在 baseline 中实际出现，证明嵌套归属生效）；`<module>` 级保留零计数条目、其余零计数函数过滤——新函数默认预算 0，新增 print 必违规。
- 判定（:508-531）：total 与 per-function 双单调不增，双负对照（test:210-221）。
- **facts 校准**：AUDIT-150 §3.1 census 1,315 由测试断言（test:197-203）且与 baseline total 一致——计数口径经第三方事实源钉死。
- 语义边界（归属保守方向）：lambda 体/装饰器/默认参数中的 print 归外围函数——计数偏紧不偏松，棘轮安全侧。

### R5 消费 FEAT-020 快照 — 核实通过
- 消费方式合规：经 `cmg.extract_cli_dispatch()` / `cmg.extract_check_segments()`（generator.py:95/160 实存，返回 `keys`/`ids` 字段形状匹配）——零复制提取器逻辑，符合 packet 契约。
- SKIP+披露（:558-564）：快照缺失→`status=SKIP`+中英披露、零 violations 不误报——与 packet"缺失时 SKIP+披露，不误报"一致，有测试（test:239-247）。
- 双向判定：frozen−live（移除=契约破坏）与 live−frozen（新增=须走 regen 契约路径）均违规；check_segments 漂移同理。
- 快照损坏/结构异常→json 解析崩溃→exit 1（fail-closed 方向）。

### R6 冷导入采集 — 核实通过
- 隔离子进程 `[sys.executable, "-I", "-B", "-c", probe]`（:624-627）：-I 隔离 PYTHONPATH/user-site，-B 不写 pyc；路径经 `{path!r}` repr 注入（转义安全，无注入面）。
- `threshold=null` 持久化于 baseline:543；`wall_ms` **不持久化**（build_baseline 仅存 import_count/sha256）——R7 确定性免疫计时噪声，run_check 的 R6 面 status 仅 INFO/SKIP，永不产生 violations（test:293-297 断言 never-fatal）。
- 确定性：`sorted(sys.modules)` + sha256；`lru_cache(4)` 使 double-regen 稳定；120s 超时→None→SKIP 披露。

### R7 可再生成 — 核实通过，**剔除面不引入假阴性**
- 双 regen 字节相等（`_canonical_json_bytes` sort_keys+indent2 统一序列化）；`_strip_volatile`（:858-871）仅剔除 `generated.git_head`（逐 commit 变化）与整个 `r6_startup_budget`（跨解释器族变化，且本就是 advisory 面）。
- **"基线与引擎真实不一致"检出能力独立验证**：手改锚 +10（test:313-319）与 −5（test:321-327）均触发 `baseline-stale`——因为 fresh regen 的 R1/R2/R4 面全部来自**当前树实测**（build_baseline 的 `existing` 参数只携带 authored zone，不携带任何测量值），committed 与 fresh 的测量面差异不可能被剔除面掩盖。R2 inventory 手改 count 同理由实测对账失配。
- authored zone（exemptions/managed_modules）被 regen 原样携带→committed 恒等——**by design**（治理区，见 P3-2 披露）；extraction zone 手编必败（"机器生成禁手编" enforcement 生效）。
- `snapshot_present_at_regen` 入基线：regen 时无快照而 check 时有（或反之）→ stale 失配→催促 regen ✓。

## 2. fatal 语义真实性 — 全覆盖核实

| 违规路径 | exit 码 | 证据 |
|---|---|---|
| 基线缺失（R0） | 1 | :1046-1049 + test:425-429 子进程实测 |
| R1/R2/R3/R4/R5/R7 任一违规 | 1 | :1102-1104 `sys.exit(1)`；test:413-423 篡改基线子进程实测 returncode==1 |
| R2 parse_error（不可扫描文件） | 1 | 无预算→违规→exit 1（:256-258/:303-314） |
| R2 inventory 过期 | 1 | :287-297 无条件违规 |
| 豁免超额（OVER-ALLOWANCE）/ 豁免过期 | 1 | :717-719/:697-701 保留违规 |
| 基线 JSON 结构异常 | 1（崩溃退出） | KeyError/ValueError 未捕获→traceback 退出非 0（fail-closed 方向） |
| `--regen` | 0 | :1028-1043 显式 return |
| R5 SKIP / R6 INFO-SKIP | 0 | 设计内非致命（packet 口径） |

`sys.exit(1)` 传播链核实：引擎 dispatch 为 `commands[cmd](args)` 直调（verify_workflow.py:24298），无 try/except 包裹 SystemExit——**fatal 位真实**。

## 3. R5 lazy import 防循环 — 正确

- `archguard_ratchet.py` 顶层 imports 全 stdlib（:62-72）+ `from __future__`——引擎启动 `from archguard_ratchet import cmd_archguard_ratchet`（verify_workflow.py:69）不连带 contract_matrix。
- `contract_matrix.generator` 仅在 `r5_live_faces`（:544-546）函数体内 lazy import；R6 冷导入 probe（`import verify_workflow`）同样不触发 generator。
- 循环闭环防护：若未来本模块顶层加 `import verify_workflow`，R2 扫描即计 `import_vw`（本模块在扫描范围内，docstring :58-59 明示）→ 预算 0 → fatal。防护自洽。
- 附带核实：generator.py:51 顶层 `import verify_workflow as vw` 正是 R2 inventory 中 `contract_matrix/generator.py import_vw@51` 条目的来源——扫描口径与事实互证。

## 4. 耦合面裁决（审查重点④）

**裁决：FEAT-020 快照 80→81 + `FROZEN_CLI_KEY_COUNT` 计数更新是唯一必要耦合，无更小面。**

依据：
1. packet 验收命令（acceptance_contract.command）明确要求顶层子命令 `verify_workflow.py archguard-ratchet`——顶层 CLI key 必然 +1（80→81），handler 必然 +1（77→78）；若并入现有 Check 以避免快照变化，将违反 packet 验收口径。
2. snapshots.json 的 5 处变化（handler_count/key_count/keys 插入 archguard-ratchet 按字母序/git_head/timestamp）全部为 `generator.py --regen` 的机械产物，无一可免。
3. 消费点 grep 全仓实证：`FROZEN_CLI_KEY_COUNT` 仅 test_contract_matrix.py:40 定义、:142 消费；handler_count 无独立冻结断言（:145-146 为随 stored 值的推导校验）——**耦合恰好一行常量 + 注释，无遗漏也无冗余**。
4. test_contract_matrix.py:36-39 注释显式援引"documented contract-change path"并注明 review 覆盖——契约变更路径文档化合规。

## 5. 主文件 +18 行纯接线 — 核实

git diff 全量仅 3 hunks：(a) import +2 注释 +1 import（:66-69）；(b) argparse 子命令注册 +2 注释 +12 代码（:23903-23916）；(c) dispatch 表 +1（:24269）。合计 **3+14+1=18 行**，零逻辑、零其他改动。R1 锚生成于接线之后（锚 24,302 含此 18 行）——"gate born green"自举时点成立。

## 6. 测试 38 例真实性 + 存量失败归属

- **38 例逐类清点**：R1×3 + R2×6 + R3×4 + R4×4 + R5×5 + R6×2 + R7×4 + Exemption×4 + BaselineArtifact×2 + CliGate×4 = **38** ✓。
- 质量结构：每规则正/负对照双向；负对照全部 temp-dir fixture 或内存扰动（真实引擎/基线/快照零修改——`with tempfile.TemporaryDirectory()` 模式核实）；CLI 两态经真实 dispatch 路径子进程实测（含 returncode 断言）；regen 幂等以字节相等断言（test:431-440）；facts 1,315 校准锚定计数口径。
- R5 mock 使用（test:255-261 `patch.object(ar, "r5_live_faces", ...)`）为 patch 上下文内的合法 fixture 注入，非产品 mock 残留。
- 存量失败（全量 2,278/30F+1E+1S、健康 31 stash 前后恒等）：**采信**（见 §9 边界）；数字与 AUDIT-151 基线（2,194/26F）的增量演化方向合理，且本 slice 新增 38 例若引入新失败会违反"恒等"声称——与 38 例断言当前树全绿的测试内容（如 test_r7_committed_baseline_matches_fresh_regen、test_cli_green_on_current_tree）自洽。

## 7. AI 专项 5 项检查

| # | 项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **通过** | 产品代码（archguard_ratchet.py 全文）零 mock；测试内 patch 限于上下文管理器 |
| 2 | 硬编码返回值 | **通过** | 全部判定来自实测（AST/子进程/文件计数）；R1 note 中 24,252 为叙述性历史锚，判定输入是 `anchor_loc` 实测字段 |
| 3 | 幻觉 API | **通过** | `cmg.extract_cli_dispatch/extract_check_segments` 实存且形状匹配（generator.py:95/160 已读）；`sys.stdlib_module_names`/`stdout.reconfigure` 均真实 API 且版本相容 |
| 4 | 未实现 TODO | **通过** | 全文无 TODO/FIXME/pass-placeholder；R6 `threshold=null` 是有 note 的 FEAT-018 接点，非残缺 |
| 5 | 过度实现 | **通过** | Tarjan 对 v1 单模块超前但有负对照与接入日政策支撑；`_OWNER_TASK_MAP` 6 条/managed 1 条，克制；R6 wall_ms 采集仅报告不入基线 |

## 8. 审查维度结论（5/5 覆盖）

| 维度 | 结论 | 要点 |
|---|---|---|
| 正确性 | **通过** | R1~R7 判定逻辑逐行核实；边界（空文本/BOM/行漂移/parse_error/自环/超时）全覆盖；Tarjan 算法正确 |
| 安全性 | **通过** | 无硬编码密钥；subprocess 参数列表式（无 shell 注入）；probe repr 转义；CLI 输入仅路径/开关；OWASP 面无命中 |
| 可维护性 | **通过（附 P2-1/P3-7）** | 模块自包含、docstring 详尽、判定/豁免/生成三区分离清晰；`check_r3` ~155 行偏长（P3） |
| 性能 | **通过（附 P2-1）** | AST 单遍；R7 double-regen 经 lru_cache 免重复子进程；R5 触发引擎 double-load（P2-1，既有模式继承） |
| 测试覆盖 | **通过（附 P2-2）** | 38 例双向 + facts 校准 + CLI 两态 + 幂等字节；动态导入逃逸面无负对照（P2-2 关联披露项） |

## 9. 采信边界声明（事实依据红线）

以下声称**采信 Developer 报告、未独立复跑**（只读审查约束）：全量测试 2,278/30F+1E+1S 与改前恒等；check-governance 健康 31 stash 前后恒等；38/38 通过。采信基础：本审查独立复算的全部锚点（引擎 24,302 行、R2 46 站点、14/14 行号、HEAD=c92bf5d 与两处 git_head 同源、facts 1,315 测试断言在案）均与声称一致，无一处证伪。commit 时点 Coordinator 宜以 EVD 行核对上述命令输出留痕。

## 10. 发现列表

### P0（阻塞）— 无

### P1（关键）— 无

### P2（建议）

- **P2-1** R5 判定触发引擎 double-load：`python verify_workflow.py archguard-ratchet` 以 `__main__` 运行时，`check_r5 → from contract_matrix import generator`（archguard_ratchet.py:546）→ generator.py:51 顶层 `import verify_workflow as vw` → 引擎 24k 行被作为模块**二次加载**。无循环死锁（archguard_ratchet 已缓存）、无正确性错误，纯成本面；FEAT-020 既有模式继承（generator --regen 同样发生），非本 slice 引入。建议：归入 REFACTOR-contract-layer（generator 顶层 vw import lazy 化——`extract_cli_dispatch` 本身纯 AST，vw 仅服务 Face 3 live invocation）。
- **P2-2** R2/R4 静态分析固有逃逸面未在 docstring 声明：`importlib.import_module("verify_workflow")`、`exec`/`getattr` 动态形式、print 别名（`p = print`）不被三 kind 捕获。仓库无此类先例、实际风险低，但 R2 docstring 宜补一句边界声明（静态语法锚定口径），避免后续误信全覆盖。
- **P2-3** 治理完备性核对项：packet `vertical_slice.scope_guard` 字面列 3 文件（引擎/棘轮/基线），实际 diff 面 6 文件（+测试 444 行 + 快照 + FEAT-020 计数）。测试为 done_definition（"基线+负对照证据"）必需、快照为文档化契约路径必需，正当性成立（§4），但建议 Coordinator 在 evidence-log/commit message 中显式补记耦合面扩大说明，保持 triage 面 ↔ diff 面对账闭环。

### P3（讨论）

- **P3-1** R1_DESIGN_ANCHOR_NOTE（archguard_ratchet.py:735-740）"intervening engine deltas: FIX-300 + FEAT-019 dispatch wiring"枚举不完整：facts 锚（2be00ec）后引擎还吸收了 FIX-299（1cda292 改 L20568）等介入提交的行贡献（+50 中 18 为接线、约 32 为其他介入）。核心语义"实测为准"不受影响；建议后续 regen 时改为"commits since facts-0.80.0"或去枚举。
- **P3-2** R7 对 authored zone（exemptions/managed_modules）无结构校验：手塞一条无 DEC 依据的豁免会被 fresh regen 原样携带→committed==fresh 恒过。现行防护是流程性的（DEC 引用+到期熔断+双审）。建议后续 slice 给 exemptions 加最小结构校验（dec/rule/scope 非空）。
- **P3-3** R2 过期 inventory 违规 message（:292-295）只说 "clean them up"，宜同时提示 `--regen` 落账命令（清理后须 regen 条目才会从 inventory 消失）。
- **P3-4** 豁免过期与 inventory 过期的语义不对称（前者仅在有匹配违规时标 EXPIRED，后者无条件违规）——角色不同（许可 vs 债务），合理，记录讨论即可。
- **P3-5** R4 范围限引擎文件：print 迁出引擎到新 infra 模块即出棘轮范围（archguard_ratchet.py 自身 print 不计）。与演进方向一致（出引擎=改进），后续 slice 可扩至 infra/*.py 全域。
- **P3-6** R6 import_count=196 含 probe 自身引入的 `json` 模块噪声（恒定但口径含 probe）。FEAT-018 接 threshold 前宜冻结 probe 口径或剔除 probe 自身模块。
- **P3-7** `check_r3`（:321-475）约 155 行，可拆 scan/judge/scc 三段；当前结构清晰、注释充分，不阻塞。

## 11. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| 5 维度覆盖 | 5/5（§8） |
| 每条发现标注级别 | 100%（P2×3 + P3×7） |
| 设计一致性 | 已完成——与 AUDIT-150 §4/evolution §3.2/§4、FEAT-019 packet（allowed_change_scope/done_definition/acceptance_contract）逐项比对，偏差仅 P2-3 治理对账项与 P3-1 note 精度 |
| AI 专项 5 项 | 5/5 通过（§7） |

## 12. 终态

> **APPROVED_WITH_NOTES**
> unresolved_blockers = 0
> P0=0 / P1=0 / P2=3（double-load 优化归 REFACTOR-contract-layer、静态边界披露、耦合面对账补记）/ P3=7

通过与备注理由：R1~R7 判定实现经逐行+独立交叉印证全部成立（含 R7 剔除面不引入假阴性的检出能力验证）；fatal 位真实（全部违规路径 exit 非 0 实测/推演双证）；R5 防循环正确；+18 行纯接线核实；耦合面唯一且最小；测试 38 例双向对照真实；AI 专项零命中。P2 项均有明确承接路径且不阻塞合并。APPROVED_WITH_NOTES 不替代测试与发布审查。
