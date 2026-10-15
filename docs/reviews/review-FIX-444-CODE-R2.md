# FIX-444 Code Review R2 — 双层引用判别复审（同一 Reviewer 必达轮）

- **轮次**: R2（复审；R1 结论 NEEDS_CHANGE，unresolved_blockers=3，txn de0711df…/seq22）
- **前轮引用**: `docs/reviews/review-FIX-444-CODE-R1.md`（hash `eec48eb8…`——未改）
- **审查方**: Code Reviewer Agent（与 R0/R1 同一实例；只读；唯一写面 = 本报告）
- **审查对象绑定**: HEAD `bf6942dd…` staged 空（实测）；`hooks/commit-msg` blob **`996cb79fc93a20f040d27786b0c1f969b4c18fb3`**（81+/1−）+ `tests/test_hooks.py` blob **`526cd5e77287a688a6d16e9e7848d477d7548084`**（391+/2−）=472+/3−——与派发精确一致（实测 hash-object）
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "unresolved_blockers": 3}
```

---

## 0. 结论

**R1 五攻击已全修复（必要条件达成）**：prose 层不再有任何 call/verdict/引用豁免——R1 五攻击 shape 实跑**全部 BLOCK**，三 ctl 合法引用仍 PASS；R1 双否定/叠否定拒绝保持；V1 当前冻结窗口（**802,343 bytes / SHA256 28640C1F…A2B29**，恰为 Coordinator 冻结态）三任务实数行集 **FEAT-097=72 / FIX-443=24 / FIX-444=54 全 PASS**（真实 Step-12 路径、真 bash、clean exit 0）；V2 拒绝集 4/4；P-1 可移植性落地（自包含 SyntheticEvdStep12ReplayTests 永久面 + 5 攻击红测入库 + 行数断言防零行自证；live probe 可见 skip+seen≥1=P-1 次选可接受形态）；模块独立快跑 44 测（§5）。

**但三个新 wrap 攻击实际逃逸（actual output，非推演）**：n1 `事实依据: {"result":"PASS｜我编造了测试结果;"}` → **PASS**；n8 `事实依据: {"r":"check-quoted 我编造了; x"}` → **PASS**；n7 `事实依据: 我发现"不允许不编造"是要求必须遵守并当真` → **PASS**。record 层豁免仅凭花括号+引号字节即授予（无 source provenance 绑定），prose 标记门可被句内背书滥用——正是 Coordinator 预声明**不接受**的 Developer 自曝残余类。按「任何 record 层 unsupported closure 实际 PASS 必须 NC、不算非阻塞」→ **NEEDS_CHANGE，`unresolved_blockers=3`**（§2）。round 2 < 3 → 同 Reviewer **R3 必达**。

## 1. 验证矩阵结果（全部真 bash 实跑；探针脚本/bash -n/全 literal 落隔离根）

| # | 项 | 结果 | 证据 |
|---|----|------|------|
| V1 | 三任务真实行端到端（fresh copy=冻结态） | **PASS** | 802,343B/SHA 28640C1F…；72/24/54 行全 PASS 零 BARE_ROW；clean exit 0 |
| V2 | 拒绝集 | **PASS** | affirm/mixed/dneg-unquoted/missing-basis 全 BLOCK |
| V3A | R1 五攻击+三 ctl | **PASS** | 五攻击全 BLOCK（prose 无豁免）；三 ctl 全 PASS |
| V3N | 新 record/wrap 攻击（9 shape） | **FAIL×3** | n1/n8/n7 PASS（逃逸，§2）；n2/n2b/n3/n4/n5/n6 BLOCK（含：任意 JSON 裸肯定/未闭合/花括号散文引语/多 occurrence 第二肯定均拒——划分器对这些保守正确） |
| P-1 | 可移植性 | **PASS（带 P3）** | Synthetic 类自包含/never skipped/行数断言（:669-737，5good+5attack 经真实 `_step12_replay`）；live 类可见 skip+seen≥1（:740-765）——次选形态可接受，首选移出记 P3-F2 |
| P-2 | bash 边界 | **PASS** | skipUnless(_BASH) 仅能力边界；本机 bash 实在全跑；无 bash 时 `_run_*` raise 非 PASS |
| V4 | 原门保持 | **PASS** | 推测模式 verbatim（diff）；事实依据门实测拒；review 门零触碰 |
| V5 | 模块独立快跑 | 见 §5（44 测） | raw Tee 落隔离 |
| V6 | blob 绑定 | **PASS** | 996cb79f…/526cd5e7… 实测一致 |

## 2. Findings（本轮阻塞项，全部 actual output）

### B1（P1·阻塞）record 层 `(PASS|BLOCK)｜[^;]*` 豁免无 provenance 绑定——任意 JSON 串内判定 span 包裹肯定即免

- **位置**: helper record 层 `-e "s/(PASS|BLOCK)｜[^;]*//g"`（:~145 区域）+ `json_region_mask` 仅按 `{}`+引号划分（无字段/类型校验）
- **实证**: `V3N_n1-json-passspan=PASS`——`事实依据: {"result":"PASS｜我编造了测试结果;"}`：`{"result":…}` 非任何来源记录结构，纯 wrap；判定 span 连肯定句整段剥除 → 逃逸。划分器把该串整体划 record → prose 层零豁免的正确设计被 record 层绕过。**花括号划 record 本身不保守——record 豁免面更大**（Coordinator 预判实证）。
- **要求（R3）**: record 层 call/verdict 豁免必须绑定**可追溯结构**（已知来源承载字段键如 `literal`/`raw`/`observed` 或等价记录签名），任意键 JSON 串不继承豁免。

### B2（P1·阻塞）record 层 `check-quoted [^;)]*` 同类无 provenance 豁免

- **位置**: record 层 `-e "s/check-quoted [^;)]*//g"`
- **实证**: `V3N_n8-json-checkquoted=PASS`——`事实依据: {"r":"check-quoted 我编造了; x"}` → span 剥除逃逸。（同族 check 裸/转义合成形 n2/n2b 实测 BLOCK——比 R1 收窄，但 check-quoted 形仍开；真实 EVD-1463 形 literal 经 V1 合法通过——类对真实行有效，问题同样在 provenance 不绑定。）
- **要求**: 同 B1 绑定可追溯结构；span 内含第一人称肯定起式时不豁免。

### B3（P1·阻塞）prose 标记门 `(双否定|发现|边界|命名|引用)+"叠否定"` 可被句内背书滥用

- **位置**: prose 层 `-e "s/(双否定|发现|边界|命名|引用)“(neg)(允许)?(neg)(filler)?(term)”//g"`
- **实证**: `V3N_n7-finding-prefix-endorse=PASS`——`事实依据: 我发现"不允许不编造"是要求必须遵守并当真`：标记 发现 满足门条件→引号段剥除→尾句（要求必须遵守并当真）无 token→逃逸。语义为**背书强制编造令**，非引用；ctl（`R0 发现"不允许不编造"为边界`）PASS 正确但字节层面同门不可分。
- **要求**: 标记门需附加封闭边界条件（如引号段后紧邻谓语限定为引用语法形——「为边界/已实证/是攻击」等闭合表——或引号段须为行内独立成分）；不满足即走叠否定保裸词路径 BLOCK；unknown 拒。

**三项共同 R3 验收线**：n1/n7/n8 全 BLOCK + ctl 三形仍 PASS + **真实 EVD-1463/1481 形 synthetic good rows 仍 PASS**（:687-698）+ 冻结窗口三任务实数行集端到端仍全 PASS + n2~n6 防线不回退 + 模块绿 + n1/n7/n8 入库红测。

## 3. R1 findings 复审对照

| R1 项 | R2 判定 |
|-------|---------|
| B1 无界 verdict span（prose） | **已修复**（prose 零豁免；五攻击实测 BLOCK） |
| B2 弯引号即引地位（prose） | **已修复（标记门化）**——但新 B3（标记门背书滥用）为其收紧后残余变体 |
| B3 check 形仿免检（prose） | **已修复（prose）**——record 层必要豁免的 provenance 缺失转为新 B1/B2 |

## 4. 披露

- **Developer 侧（不代填）**：其 R2-2 JSON literal 探针仍含 body placeholder（green_a.sh 原文件在）→ 首次 probe 假 pass 无效；其命令尾 gitstat/hash 子 exit 未逐独回显——以上按 Developer 自留缺口引用，本报告不补齐不采信其数字。
- **我方**：本轮探针脚本零缺陷（argv 参数化 + bash -n 先行 + clean exit 0）；R1 期 D1/D2/D3 已在历史保全 JSON 披露，未复演（无 false-empty：行数断言 72/24/54 为 awk 实数）。

## 5. 验证命令记录（five-env 全程；探针/module raw 与脚本落隔离根）

| id | command 要点 | start(UTC) | end(UTC) | exit | affected/protection |
|----|-------------|-----------|----------|------|---------------------|
| C1 | blob/HEAD/staged/numstat | 13:31:35.38Z | 13:31:35.74Z | 0 | 只读 |
| C2 | hook 全 diff -U12 只读 | unknown | unknown | 0 | 只读 |
| C3 | 综合探针（V1/V2/V3A/V3N，argv gen+bash -n+clean run） | 13:32:50.49Z | 13:32:56.13Z | **0** | 隔离 fix444r2-rev-3526c1b7（gen_r2.py/r2probe.sh/EVD 副本 802,343B） |
| C4 | 测试结构 grep+read（:669-768） | unknown | unknown | 0 | 只读 |
| C5 | 模块独立快跑（后台 job pwsh-19，raw Tee） | 13:34:09.64Z | 13:35:19.91Z | 0 | **Ran 44 tests in 63.098s — OK**；隔离 fix444r2-mod-970c4673 |

完整 literal/全精度戳/输出以同隔离根 `FIX-444-reviewer-R2-command-records.json`（随本报告一次性齐备落盘）为准。

## 6. 五维 + AI 专项

正确性 **FAIL(B1~B3)**（双层架构方向正确、prose 面正确、record/provenance 与标记门收口未竟）｜安全性 **FAIL(B1~B3)**（三个实际逃逸通道）｜可维护性 **PASS（带 P3-F1/F2）**（P3-F1：mask 无 provenance 的结构注记；P3-F2：live probe 首选移出通用模块）｜性能 PASS（awk 单遍+sed 链；模块 ~60s 级）｜测试覆盖 **PASS 带 FAIL 面**（synthetic 永久面+红测入库达成；n1/n7/n8 无红测=逃逸存活原因，R3 必补）。AI 专项：无 mock 残留/无业务硬编码/无幻觉 API/无 TODO/无过度实现。

## 7. 硬门槛自检

P0=0（阻塞=P1×3）✓｜5 维 100% ✓｜发现带级+位置+actual output ✓｜R1 findings 逐条对照（§3）✓｜round+前轮引用 ✓｜事实红线（逃逸=实跑输出；Developer 缺口不代填；窗口绑定 SHA/bytes/实数）✓｜「原五攻击修复必要不充分」口径一致 ✓

## 8. 机录与后续

`review-record --task FIX-444 --round 2 --result NEEDS_CHANGE --report docs/reviews/review-FIX-444-CODE-R2.md --reviewer 'Code Reviewer'`——round 2 < 3：Developer 按 §2 三要求必要修复 → 同一 Reviewer **R3 必达**（注入本报告；R3 验收线=§2 末共同线）。`unresolved_blockers=3`。
