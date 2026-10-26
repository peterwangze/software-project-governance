# FIX-447 CODE R0 独立审查报告

- **任务**：FIX-447 LRC 并发窗口间歇性看护——INVENTORY drift / load_timing 家族（EVD-1707 C4 残余）
- **Reviewer**：独立 Code Reviewer（R0；与 Developer 不同实例）
- **日期**：2026-10-26 · **基准**：工作树未提交 diff @ HEAD ad2e226
- **审查对象**：
  1. `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`（+243/−5，git diff 核实）
  2. Developer 报告 `.codex-sandbox/FIX-447/dev-report.md`
  3. scratch：`reproduce_concurrent_window.py`、`run_suite_under_load.py`、4 份输出 txt
- **结论**：**APPROVED_WITH_NOTES（unresolved_blockers=0）**；findings = P3×4，无 P0~P2。
- 立场声明：以下判断仅基于本 Reviewer 亲眼复跑与读到的代码；Developer/Coordinator 叙述均按待验证声明对待并逐项核验。

---

## R1 复现构造有效性 — PASS

**机制核实**（非听信叙述）：测试 2 通过 `patch.object(lrc, "enumerate_candidates", …)` 包裹模块级函数；扫描器内两个调用点均为模块全局查找——主扫描 `scan_loop_runtime_claims`（loop_runtime_claims.py:3309）与再校验 `_recheck_inventory`（:3264）。包裹器在第 2 次调用（= 初始枚举之后的 recheck 再枚举）先执行真实写入再委托原函数——写入**确定性**落在〔初始枚举, recheck〕窗口内。全程无线程、无 sleep、无竞态等待（diff 原文核读）。`assertEqual(2, calls["count"])` 钉死调用次数。

**四变异形状端到端**（本人复跑，非转述）：
- content-change / create / delete / bytes-only(BOM) 四形状 verdict=BLOCKED，codes 与测试 `expected_codes` 逐集合相等；
- finding 精确点名：content-change 的 `INVENTORY_CONTENT_CHANGED` 携带 `normalized_path=docs/history.md`；create/delete 的 `INVENTORY_PATH_SET_CHANGED` message 内嵌具体路径；
- BOM 形状钉板 digest-vs-bytes 区分：raw bytes/字节计数变化触发 `FILE_BYTES_CHANGED`+`RAW_BYTES_CHANGED`+`DIGEST_DRIFT`，而 canonical 内容 digest 相等 ⇒ `CONTENT_CHANGED` **不**触发——与扫描器 `_content_digest` 的 utf-8-sig 规范化语义一致；
- 归因纯度断言在场：`codes <= DRIFT_FAMILY` 且 `exemptions_applied == []`。

## R2 证伪严密性 — PASS

- **无写入 ⇒ 确定性**：本人复跑 `test_scanner_is_deterministic_without_external_writers`（1 test OK, exit 0）与复现器 B 段（3 次扫描 1 个身份、双 recheck 全等、initial==recheck，exit 0）。
- **结构性论证**（代码核读）：`candidates.sort(key=(root_role, normalized_path.encode))`（:1744）使枚举顺序与 scandir 顺序无关；`segment_cache` 为每次调用内新建局部 dict（:1696），无跨调用模块态；digest 全 sha256 确定性。⇒ INVENTORY_* finding 只能由**实际文件状态差异**触发（:3267-3283 的集合/计数/逐路径比较 + :3396-3397 的终态 digest 比较）。故「历史间歇 drift BLOCKED = 外部写入落入窗口 + 看护正确工作」的归因在逻辑上闭合，产品缺陷假设证伪成立。
- **假阳性向量排查**：枚举排序/缓存态/哈希确定性/casefold（:1733-1735，确定性）均排除；唯一不可排除向量 = 外部写入者本身（即归因对象）。快照边界引理（scandir→is_file 间隙消失的文件在两趟均不可见 ⇒ 不产生 finding）是**可观测性边界**而非假阳性源，Developer 如实披露、不改码——判定正确。
- 复现器证据产自**未被修改的扫描器**（产品零 diff，见 R4），证伪证据不受测试编辑污染。

## R3 稳定化的语义安全（最重维度） — PASS

审查对象：`test_real_repository_inventory_complete_and_within_budget`（test:935-979）双分支改造。

- **(a) 真实回归不可能被掩盖**：首个断言要求 `findings ⊆ {INVENTORY_*, PATH_SAFETY_ERROR}`。扫描器 verdict 仅 PASS/BLOCKED 两态（:3406，`not report.findings` 为 PASS 硬条件）；语义/policy/budget/classification 全部代码（SCAN_MODE_INVALID、PARSE_ERROR、*_BUDGET_EXCEEDED、UNSUPPORTED_AFFIRMATIVE 等分类态、PATH_ROOT_ESCAPE、PATH_CASE_COLLISION、CONTENT_NORMALIZATION_ERROR、ROOT_RESOLUTION_ERROR、ACCOUNTING_* 等）均不在容忍集 ⇒ 任何一个出现即红。**空 findings 的 BLOCKED 也红**（else 分支 `assertTrue(transient)`）——parsed_candidates 回归（无 finding 的静默计数不匹配）同样失败。两条掩盖路径均封死。
- **(b) PASS 分支保留全严格原断言**：0 findings（含瞬态族）、candidate_count==parsed_candidates、inventory_sha256==final_inventory_sha256——与原断言集等强；原 256MB 内存峰值断言保留在循环之前（diff 核读）。memory_report 同一容差逻辑，无额外放宽面。
- **(c) 容忍清单封闭性**：`startswith("INVENTORY_")` 前缀在**当前扫描器全集**下恰好等于 6 码闭集（grep 全文件核实：PATH_SET/COUNT/RAW_BYTES/CONTENT/FILE_BYTES_CHANGED @ :3271/3275/3277/3281/3283 + DIGEST_DRIFT @ :3397，与测试 `DRIFT_FAMILY` frozenset 逐字一致）；`PATH_SAFETY_ERROR` 为精确匹配（枚举读失败 :1700/:1705/:1731/:1660/:1668——Windows 共享冲突类外部瞬态，fail-closed 到 BLOCKED）。无模式匹配过宽问题（见 F1 前瞻性备注）。
- **BLOCKED 分支加固**：要求 digest 实际漂移（`assertNotEqual`）——PATH_SAFETY_ERROR 早退路径（:3315-3316）下 final 为空值与真实 digest 不等，语义一致。fail-closed 产品语义零削弱（扫描器零 diff，git status 核实仅测试文件 M）。

## R4 D4 纯粹性 — PASS

- diff 仅 1 文件 +243/−5（git diff --stat 本人核实）；−5 行 = 常量字面量单一源化（27.8→FIX401_CPU_BUDGET_SECONDS，数值逐位相同）+ 原三条严格断言被双分支超集替代（PASS 分支等强，BLOCKED 分支新增归因约束——覆盖面严格扩大而非缩小）。
- 扫描器零改动是**证据支撑的结论**（R1/R2 的确定性与类型化看护论证），不是规避：间歇源为外部并发写入者，产品已有正确 fail-closed 看护，改产品反而是错面。

## R5 数字可信性（独立复跑，全部本人执行） — PASS

| # | 命令 | 结果 | exit |
|---|------|------|------|
| 1 | `python -B -m unittest discover -s …/tests -p test_loop_runtime_claims.py`（串行全量） | **Ran 72 tests in 150.426s · OK** | 0 |
| 2 | 同上 `-k FIX447 -v` ×2（含 4-spinner 负载测试） | **4/4 OK ×2**（21.107s / 18.803s） | 0, 0 |
| 3 | `python -B .codex-sandbox/FIX-447/reproduce_concurrent_window.py` | 四形状 BLOCKED + B 段证伪 + C 段窗口定界全输出 | 0 |
| 4 | `-k test_scanner_is_deterministic_without_external_writers` | 1 test OK（0.039s，微型 fixture 合理） | 0 |
| 5 | `-p test_verify_workflow.py -k LoopRuntimeClaimAdapter`（相邻面） | 4 tests OK（14.539s） | 0 |
| 6 | `-p test_loop_runtime_claim_attestation.py`（相邻面） | 21 tests OK（18.959s） | 0 |

与 Developer 报告数字（72/129.716s 串行、负载 151.566s 等）一致量级（本机复跑时后台有会话负载，150s vs 130s 属正常浮动，全绿不受影响）。

## R6 残留风险披露充分性 — PASS

Developer 披露四项（CPU 包络不穷尽负载形状/快照边界引理/账本同族 adapter 面留候选池/:index git 锁理论瞬态）均如实且与我的独立分析一致。本审查未发现未披露的产品风险；F1/F2/F3 为测试工艺前瞻备注（见下），非缺陷。注：`test_claim_command_emits_complete_pass_report` 仍属 load_timing 候选池的说法为「未改动声明」，与本票零交集，不影响判定。

## Findings

| # | 级别 | 内容 | 处置建议 |
|---|------|------|---------|
| F1 | P3 | live-tree 容忍用 `startswith("INVENTORY_")` 前缀而非复用 `DRIFT_FAMILY` frozenset——当前全集封闭（已核），但未来新增 INVENTORY_* 语义码（如预算类）会被静默容忍 | 后续小票：改为 frozenset 成员判定 |
| F2 | P3 | PATH_SAFETY_ERROR 若以**持久**形态只出现在真实树形状（fixture 不可复现），live-tree 测试存在窄掩盖窗；现被测试 1 的 fixture 严格 PASS 与 46-unit 语料面交叉覆盖 | 记录即可；若未来出现真实树专属路径错误再收紧 |
| F3 | P3 | 测试 4 负载包络（4 spinner，27.8s 共享预算）锚定本机级；CI 风险与既有 FIX-401 median 测试（同 subject 同预算、更严的 median 形式，CI 已绿多版）同界，无新增向量 | 维持 DEC-262 重锚纪律 |
| F4 | P3 | `FIX401_CPU_BUDGET_SECONDS = 27.8` 注释算式 18.547×1.5=27.8205 与常量 27.8 存在 0.02s 舍入差——历史字面量原值，语义零变化 | 无需动作 |

## 报告完整性

- 本报告 sha256 由 Coordinator review-record 机录时计算绑定（report_sha256 字段）。
- 复跑命令 6 条全部带 exit code；关键输出行已摘录于对应维度段。
