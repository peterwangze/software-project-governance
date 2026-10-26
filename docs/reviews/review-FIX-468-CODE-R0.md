# FIX-468 CODE R0 — 独立代码审查报告

- **审查人**：独立 Code Reviewer（FIX-468 CODE R0）
- **日期**：2026-10-26（Asia/Shanghai）
- **审查对象**：工作树未提交 diff `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`（+99/−27，`git diff --stat` 亲核）；Developer 报告 `.codex-sandbox/FIX-468/dev-report.md`；背景证据 CI run 40271229818 / 40276699568（FAIL）/ 40279190706（ok）、EVD-2168、前序 `docs/reviews/review-FIX-447-CODE-R0.md`（F3 预言本缺陷）。
- **verdict：APPROVED_WITH_NOTES（unresolved_blockers = 0）**

## R1 机器无关性 — PASS

- 断言面（亲读 diff）：负载门 `assertLess(elapsed, baseline * FIX468_LOAD_ENVELOPE)`；空载门 `assertLess(baseline, FIX401_CPU_BUDGET_SECONDS)`。两个参照系均不含 16 核锚定常数——baseline 为**同机同轮实测**，27.8 施加于空载基线（CI 历史恒绿面：serial/budget 测试三 run 全过），1.75 为无量纲相对包络。
- 1.75 推导核验：注释「worst observed ≤~1.4× + ~25% 余量」——1.4 × 1.25 = 1.75，算术自洽；注释在案且写明 DEC-262 重锚纪律（禁静默放宽）。常量紧邻 `FIX401_CPU_BUDGET_SECONDS=27.8` 单源放置。

## R2 负例语义（最重） — PASS

- 包络门为 `assertLess`（严格小于）：确定性钉板测试实证**边界值即红**（`gate(2.0, 2.0×1.75)` → `assertRaises(AssertionError)` 亲跑绿；边界内侧 `−1e-9` 绿——3.5 与 3.5−1e-9 在 binary64 均精确可比，判定确定性成立）。
- 绝对锚 27.8 原样保留（施加于空载基线，每台机器仍过 FIX-346 纪律）。
- 全 diff 无 skip、无 sleep、无重跑到绿、无永真断言（门为算术比较）。
- spinner 终止纪律原样保留于 `_scan_cpu_seconds_under_spinners` 的 finally（terminate → wait → TimeoutExpired 时 kill → wait）；异常路径下未赋值的 `elapsed` 不产生掩蔽（异常直接传播，无 return 达成）。
- **语义映射披露（设计变更，验收明定，非缺陷）**：旧门「负载运行 < 27.8 绝对」→ 新门「负载运行 < 同机基线 × 1.75 + 空载基线 < 27.8」。RISK-048 看护语义（外部负载不得无界通胀 CPU 成本）以机器无关形式保留；高基线机器上负载绝对值可高于 27.8 而过新门——这是验收要求的参照系变换，如实记录。

## R3 缩放正确性 — PASS

- `_spinners_for_cores = max(1, min(4, cores−1))`：亲算 cpu=1→1、2→1、4→3、16→4、None→1（`cores or 2`→1）——与钉板断言（2→1/4→3/16→4）一致；cpu=1 形状由公式覆盖（未单钉，可接受）。
- 小核真实路径：新测试在本机实跑 `workers=1`（2-core CI 形状）的完整负载扫描并过同一相对包络——路径有效（是在本机跑 1-spinner 形状而非模拟降核，注释措辞准确无 overclaim）。

## R4 D4 纯粹性 — PASS

- `git status --porcelain -uno` 亲核：仅 `test_loop_runtime_claims.py` 一文件 M；扫描器 `loop_runtime_claims.py` 零改动。
- Developer 跳过 adapter 子集的理由（绑定的是扫描器行为、未触碰）成立；**本审查人自行补跑该子集**：`-k LoopRuntimeClaimAdapter` → **Ran 4 tests in 13.344s · OK · exit 0**。

## R5 独立复跑（全部本人前台实跑） — PASS

| # | 命令 | 结果 |
|---|---|---|
| 1 | `python -B -m unittest discover … -p test_loop_runtime_claims.py -v` | **Ran 73 tests in 202.104s · OK · exit 0**（FIX447 类 5/5 绿，含新钉板与重构负载测） |
| 2 | `… -k FIX447 -v` | **Ran 5 tests in 47.826s · OK · exit 0** |
| 3 | 负例演示：`…test_cpu_envelope_gate_fires_on_breach_and_small_core_path_stays_green -v` | **Ran 1 test in 24.118s · OK · exit 0**（含 assertRaises 边界红 + 缩放钉板 + 1-spinner 路径） |
| 4 | `test_verify_workflow.py -k LoopRuntimeClaimAdapter`（R4 补跑） | **Ran 4 tests in 13.344s · OK · exit 0** |

（全量 202.1s vs Developer 257.9s：其披露的 ~+90s 会话并发噪声方向一致，类级口径 47.8s ≈ 其 48.5s 自洽。）

## R6 残留披露 — PASS（一项 NOT_RUN 为收口前置门）

1. **CI 首验 NOT_RUN（收口前置门，非本审查可闭合）**：1.75 包络对 CI 的充分性依赖「CI 历史失败隐含通胀 ≥ 27.8/CI基线 ≤ ~1.4×」的估算——CI 空载基线无直接测量，若其 < ~15.9s 则历史隐含通胀可 >1.75。Developer 已如实披露（residual #1）且注明 DEC-262 归因重锚纪律。**裁定：AWP 通过的前提 = 任务收口（committed 终态确认）必须以 CI 复跑绿为准**；若 CI 再抖，按 DEC-262 归因（包络 vs 真回归）后重锚，禁静默放宽。
2. 套件成本 +~36s（类级，两负载测各 2 次扫描）——披露充分；CI 步历史 450~635s，预算无虞。
3. 全量与类级差值噪声拆分——披露自洽。

## Findings 汇总

| Id | 级别 | 内容 | 处置 |
|---|---|---|---|
| F1 | P3 | CI 包络充分性 NOT_RUN——收口必须以 CI 复跑绿为终态门；再抖则 DEC-262 归因重锚 | 交任务收口协议承载（推送后验证） |
| F2 | P3 | 语义映射（负载绝对门→相对门+空载绝对门）为验收明定的参照系变换，报告中已如实记录 | 无需动作（记录在案） |
| F3 | P3 | 套件 +~36s 类级成本；后续可做类级共享物化树小票（本票不做，测试独立性优先） | 0.100 候选池备忘 |

## 红线声明

本审查未修改任何产品代码/测试、未 commit/stage、未写 `.governance/**`、未接触用户；唯一写面 = 本报告。`test_conflict_does_not_mutate` 单次 ERROR（run 40271229818，1/3）属 FIX-468 票内披露的观察项，不在本审查对象范围内，维持不并案。
