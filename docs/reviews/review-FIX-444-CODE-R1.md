# FIX-444 Code Review R1 — 引用判别类复审（同一 Reviewer 必达轮）

- **轮次**: R1（复审；R0 结论 NEEDS_CHANGE，unresolved_blockers=1，txn 95beb3b7…/seq19）
- **前轮引用**: `docs/reviews/review-FIX-444-CODE-R0.md`（hash `ff181a54…`——未改）
- **审查方**: Code Reviewer Agent（与 R0 同一实例；只读；唯一写面 = 本报告）
- **审查对象绑定**: HEAD `bf6942dd…` staged 空（实测）；`hooks/commit-msg` blob **`8eb148fa02759def9dd40644ba89bfe696c9e786`**（35+/1−）+ `tests/test_hooks.py` blob **`2e09c8cea93a5a7129cf5e86464d621272b1e658`**（256+/2−）=291+/3−，与派发精确一致（实测 hash-object）
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "unresolved_blockers": 3}
```

---

## 0. 结论

**R0 B1（真实输入误拒）已解决**：干净退出（exit 0）的真 bash 端到端复放（源绑定 awk 抽取 + 实际 Step-12 条件，bash -n 先行）对**当前窗口**（EVD 副本 749,509 bytes，含 EVD-1486~1494）三任务全量真实行——**FEAT-097 72 行 / FIX-443 24 行 / FIX-444 31 行全部 PASS**；R0 双否定升级要求亦满足（`不允许不编造`/`禁止不编造` 非引号形经 `\5` 保裸词 **BLOCK**）。V2 拒绝集五项全对；V4 原门保持（推测模式 verbatim/事实依据门实测拒/审查门无 diff 触碰）；V5 模块 **42/42 OK**（30.274s，独立复跑）。

**但引用判别类过宽，五个攻击 shape 实证逃逸**（V3，实际输出非推演）：`PASS｜我编造了测试结果;…` 与 `BLOCK｜…` 同形 → PASS；`我要求你"不允许不编造"并把数据当真实结果` → PASS；`check "我编造了测试结果"` → PASS；`check-quoted 我编造了;…` → PASS。三类机制（无界 span 清空 / 仅凭弯引号授引地位 / check 形可仿写包裹）均违反验收「裸肯定/混合/双否定仍拒」与「引号本身不免、无 span 豁免」——**NEEDS_CHANGE，`unresolved_blockers=3`**（§2 B1~B3）。round 1 < 3 → Developer 必要修复后同 Reviewer R2 必达。

## 1. V 矩阵结果（全部一手实跑；命令记录 §5）

| # | 项 | 结果 | 证据 |
|---|----|------|------|
| V1 | 三任务真实行端到端（真 bash clean exit） | **PASS** | 窗口冻结副本 749,509B；FEAT-097 72/FIX-443 24/FIX-444 31 行全 PASS，零 BARE_ROW；exit 0 |
| V2 | 拒绝集 | **PASS** | affirmative/mixed/double-neg-unquoted/stacked-禁止不 → 全 BLOCK；missing-basis（事实依据门）→ BLOCK |
| V3 | 引用边界攻击 | **FAIL** | 五攻击全 PASS（逃逸，§2）；三合法引用 ctl 全 PASS（引用类本身有效但无差别） |
| V4 | 原门保持 | **PASS** | 推测模式两支 verbatim（diff+前轮静态断言）；事实依据门实测拒；审查/review 门零 diff 触碰 |
| V5 | 模块独立快跑 | **PASS** | **Ran 42 tests in 30.274s — OK**（exit 0） |
| V6 | blob 绑定 | **PASS** | 8eb148fa…/2e09c8ce… 实测一致；staged 空 |

## 2. Findings（本轮阻塞项）

### B1（P1·阻塞）`(PASS\|BLOCK)｜[^;]*` 与 `check-quoted [^;)]*` 无界 span 清空其后任意文本——span 内裸肯定逃逸

- **位置**: `hooks/commit-msg` helper 表达式 E1（`(PASS|BLOCK)｜[^;]*`）与 E8（`check-quoted [^;)]*`）
- **实证输出**: `V3_atk-passspan-affirm=PASS`、`V3_atk-blockspan-affirm=PASS`、`V3_atk-checkquoted-span=PASS`——输入 `事实依据: PASS｜我编造了测试结果; 后续复测通过` 等三形，span 剥离连肯定句一起清掉 → 整行 PASS。`[^;]*` 无 `;` 时贪到行尾：**裸 report 标记后的任何肯定声明都被豁免**（正是派发预警形态）。
- **要求（R2）**: span 剥离不得清除裸肯定子句——或收紧 span 边界至封闭引用载荷形，或对 span 内含第一人称肯定标记（我/本次/结果已…闭合表）时拒绝该 span 豁免（unknown 保守拒）。

### B2（P1·阻塞）仅凭弯引号即授「发现名引用」地位——引号内叠否定的命令式肯定逃逸

- **位置**: helper E2（`"（neg)(允许)?(neg)(filler)?(term)"` 整段剥除）
- **实证输出**: `V3_atk-quoted-dneg-imperative=PASS`——输入 `我要求你"不允许不编造"并把数据当真实结果`：引号段被剥，剩余 `我要求你并把数据当真实结果` 无裸词 → PASS。语义为**强制编造的命令**，非引用。ctl（`R0 发现"不允许不编造"为边界`）PASS 正确——但引号本身不区分二者。
- **要求（R2）**: 引号形仅在前置引用语境标记（闭合表：发现/边界/命名/引用 等）或等价封闭条件时按引用剥除；否则引号内叠否定走 E3 路径强制 BLOCK；unknown 保守拒。

### B3（P1·阻塞）`check "…"`/`check \"…\"` span 可仿写包裹任意肯定——形仿即免检

- **位置**: helper E6/E7
- **实证输出**: `V3_atk-check-span-affirm=PASS`——`事实依据: check "我编造了测试结果"` 整段被剥 → PASS。该形是真实重放夹具引用（当前 31 行 FIX-444 行依赖其通过），但**任何作者把真实宣称写成该形即免检**（单点旧 EVD key 免检=派发明令禁止的接受面）。
- **要求（R2）**: check-span 豁免须绑定封闭载荷（如内容不含第一人称肯定起式的闭合约束，或引用必须携带可追溯前缀 raw/replay 标记），使仿写真实宣称不再逃逸；配合 B1/B2 同一"span 内肯定不豁免"原则。

**三项共同验收线（R2）**：五个攻击 shape 全 BLOCK + 三个 ctl 引用仍 PASS + **当前窗口三任务真实行（72/24/31）端到端仍全 PASS**（引用类收紧不得误伤现行 EVD 行）+ 模块全绿 + 新增攻击红测入库（本轮五 shape 必须成为红测——现套件 9 pass 无攻击例正是逃逸存活原因）。

## 3. R0 findings 复审对照

| R0 项 | R1 判定 |
|-------|---------|
| B1 真实 EVD-1463 技术引用误拒 | **已修复**（V1 三任务全 PASS，含引用形态行） |
| 双否定「不允许不编造」PASS（R0 披露边界→派发升级为阻断级） | **已修复**（非引号形 E3 强制 BLOCK 实证；但引号形转入本轮 B2——升级要求在引号语境未竟） |
| 保守残余（不允许编造/无法编造 仍拒） | 维持（保守方向，非阻塞，随附披露） |

## 4. 本轮我方装置缺陷披露（2 处，均已定位修复、不影响产品与最终结果）

1. 首版生成器占位符碰撞（`REPO` 撞 `REPO_ROOT` 且丢引号）——python gen 阶段 exit 1，**未进入 bash 执行**；
2. 生成脚本 3 行 plain-append 的 `%%s` 未渲染 → 首跑 V1 误标 FAIL(empty)（行数恒 0，Step-12 实未跑）——定位（dbg：awk 直跑 NEW=31/OLD=8 正常）后文件级补丁重跑，**clean exit 0**，V1 结果以补丁后跑为准。全部脚本/日志落隔离根。

## 5. 验证命令记录（five-env 全程；verbatim 脚本落隔离目录）

| id | command 要点 | start(UTC) | end(UTC) | exit | affected/protection |
|----|-------------|-----------|----------|------|---------------------|
| C1 | blob/HEAD/staged/numstat 实测 | 13:05:05.65Z | 13:05:06.02Z | 0 | 只读 |
| C2 | hook 全 diff -U10 只读 | unknown | unknown | 0 | 只读 |
| C3 | 综合脚本生成（首版）失败 | —（gen 阶段） | — | 1 | 缺陷①；未跑 bash |
| C4 | v1v2v3.sh 首跑（V1 假空/V2V3 有效） | 13:07:16.20Z | 13:07:18.00Z | 1 | 隔离 fix444r1-rev2-837b3b11；EVD 窗口副本 749,509B |
| C5 | dbg 双文件对比（NEW=31/OLD=8） | 13:08:03.65Z | 13:08:04.47Z | 0 | 只读+隔离写 |
| C6 | dbg2 函数直调（LINES_len=80282/31 行） | 13:08:48.49Z | 13:08:48.88Z | 0 | 同上 |
| C7 | 补丁后 **clean 重跑（V1V2V3 权威结果）** | 13:09:23.98Z | 13:09:26.06Z | **0** | 同上；verbatim=v1v2v3.sh+dbg.sh+dbg2.sh+gen_r1.py |
| C8 | V5 模块独立跑（raw Tee 落盘） | 13:09:50.60Z | 13:10:28.07Z | 0 | 隔离 fix444r1-mod-2fd7ea52 |

V3 输入串逐字见 §2/隔离脚本；Developer raw（incidents FIX-444-R1-*.log/occurrences.json 等）未逐件复读——V1/V2/V3/V5 以我方独立实跑为准，Developer 42 绿与本轮 C8 相互印证。

## 6. 五维 + AI 专项

正确性 **FAIL(B1~B3)**（引用类无差别豁免；否定/叠否定/混合/抽取路径正确）｜安全性 **FAIL(B1~B3)**（span/引号豁免通道=可绕事实门；fail-closed 缺口正在于此）｜可维护性 PASS（闭合表纪律延续；表达式间顺序依赖已注释锚定 R0/R1 因果）｜性能 PASS（单行 sed 链；模块 30.274s）｜测试覆盖 FAIL（9 pass 无攻击例——五逃逸无一有红测看护；R2 必须补）。AI 专项：无 mock 残留/无硬编码业务/无幻觉 API（sed/awk/grep 真实）/无 TODO/无过度实现（35+/256− 为必要面+测试）。

## 7. 硬门槛自检

P0=0（阻塞=P1×3，NC 依据）✓｜5 维 100% ✓｜发现带级+位置+实证输出 ✓｜R0 findings 逐条对照（§3）✓｜round+前轮引用 ✓｜事实红线（攻击=实际输出非推演；我方缺陷如实；未跑面标注）✓｜「自然语料无」论证未采用（派发禁令遵守）✓

## 8. 机录与后续

`review-record --task FIX-444 --round 1 --result NEEDS_CHANGE --report docs/reviews/review-FIX-444-CODE-R1.md --reviewer 'Code Reviewer'`——round 1 < 3：Developer 按 §2 三要求必要修复 → 同一 Reviewer **R2 必达**（注入本报告；R2 验收线=§2 末「三项共同验收线」）。`unresolved_blockers=3`。
