# Code Review: FEAT-017 — post-commit write-guard 接线（R0，commit 前置工作树审查）

- **Task ID**: FEAT-017（R0；三件套之三——前置 FIX-299✅ / FIX-300✅）
- **Reviewer**: Code Reviewer Agent（只读审查）
- **审查对象**: 未提交工作树改动（`git diff HEAD`）——`skills/software-project-governance/infra/hooks/post-commit`（+109，单 hunk `@@ -192,6 +192,115 @@`，新行 L195-303 恰 109 行）+ `skills/software-project-governance/infra/tests/test_hooks.py`（+236）；两文件合计 **345 insertions / 0 deletions**
- **审查日期**: 2026-09（R0 首轮）
- **绑定规范**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（含 APPROVED_WITH_NOTES 需 `unresolved_blockers=0` 规则）
- **方法边界（采信声明）**: 只读审查——只读 git（diff HEAD / status / ls-files）+ 读文件/搜索 + .git/hooks 安装副本只读探测；**未运行测试、未运行 bash -n、未运行 guard**（Developer 声称的 31 passed / bash -n exit 0 / projection-sync PASSED / manifest PASS / 健康 29 / 真实 guard 两态+SKIP 实录均按采信处理，辅以源码与测试内容交叉印证，见 §7）；唯一产物 = 本报告。

---

## 0. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **通过（0）** | 发现列表（§8）零 P0 |
| 5 维度全覆盖 | = 100% | **通过** | §4 逐一有结论 |
| 每条发现标注级别 | = 100% | **通过** | F-1(P1)/F-2(P2)/F-3~F-6(P3×4) |
| 设计一致性检查 | 已完成 | **通过** | §5：验收 1-3 全落地；引用条款（M1.2/FIX-297 方案 2/FEAT-011/AUDIT-150 §10）全部实存；triage 声明与工作树一致（恰 2 文件） |
| AI 代码专项 5 项 | 全部完成 | **通过** | §6 逐一有结论 |

**终态：APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0、P1=1（F-1，文档面跟进项，不阻塞本代码合入）、P2=1、P3=4。

---

## 1. 变更摘要与修改纯粹性（diff 复核）

- `git status --porcelain`：恰 2 个修改文件、**零 untracked**——与派发预授权范围（hook + 测试）逐字一致 ✓。
- hook：单 hunk 纯新增——Step 4 `fi`（L193）与 Step 5 注释（L304）之间插入 Step 4b 块（L195-303），**既有 Step 0-5 零行改动**（0 deletions 证实）✓。
- test_hooks.py：模块 docstring 追加 FEAT-017 段（L31-40）、`import os`（L43）、`_POST_COMMIT`/`_WG_SECTION_RE`（L55/L58-60）、`_wg_section()`（L129-139）、`_WG_STUB` + `_find_python_for_bash` + 2 个测试类（L342-551）——均为既有结构内**纯追加**；`tempfile` 为既有 import（L47，diff 未动）✓。
- 声称"L195-303 纯新增 109 行"：hunk 数学吻合（115−6=109；L195..L303 含首尾=109 行）✓。

## 2. 裁决门契约核对（hook grep 串 vs guard 实际输出——逐字）

对照 `verify_workflow.py` `cmd_governance_write_guard`（L22612-22670）：

| hook 侧 | guard 侧 | 结论 |
|---|---|---|
| `grep -q '^Result: PASS'`（L268） | `print("Result: PASS — 0 issue(s)（SKIPPED = 产物缺席，非缺陷）。…")`（L22669，stdout，行首） | **逐字吻合** ✓；该子命令 stdout 中无其他 `Result: ` 行首行（faces 行 L22652 为 `  [PASS] label — N issue(s)`，不冲突） |
| `grep -q '^Result: FAIL'`（L275） | `print("Result: FAIL — {0} issue(s)。…")`（L22665，stdout，`sys.exit(1)` 前） | **逐字吻合** ✓ |
| rc 契约 | exit 1 = 任一 face FAIL（L22668）；PASS 路径无 sys.exit → exit 0；SKIPPED face 永不 FAIL（L22625-22628 docstring） | 与 hook case 分派（0/1/124·137/*）一致 ✓ |
| issue 行抽取 `'^ *- '`（L276/L283） | `print("    - {0}: {1}")`（L22660，4 空格 + `- `）；`期望列形:` 行（L22662）与 faces 行均不匹配该模式 | COUNT = issue 总数 = guard 自报 total（L22665 `.format(total)`）**语义等值** ✓ |
| rc=0 无 PASS 行 → UNAVAILABLE（L271） | guard 正常 PASS 必打印 Result 行 → 该分支仅在输出形状漂移/异常截断时触达 | 诚实降级 ✓（有测试 pin，§3-E） |
| rc=1 无 FAIL 行 → UNAVAILABLE（L291） | python 未捕获异常同样 exit 1、traceback 走 stderr（被 `2>/dev/null` 丢弃）→ stdout 无 Result 行 | **裁决门核心语义成立**：崩溃不误报 FAIL ✓（行为测试 test_crash_rc1… 复现） |
| `--project-root "$REPO_ROOT"` 后置拼写 | `_extract_project_root_arg`（L140-166）从 argv **任意位置**剥离该 flag 后再交 subparser（L23392→L24189-24194）；subparser 本体（L24181-24187）未声明但预扫描兜底 | 拼写合法、面向 host 仓库（cwd 无关）✓ |

## 3. bash 正确性/健壮性（审查重点 1，逐项）

**A. `set -e` 交互（L6 全局 errexit）——通过**
- L260 `SPG_WG_OUT=$(spg_wg_invoke 2>/dev/null) || SPG_WG_RC=$?`：标准捕获 idiom——赋值失败时 RHS `SPG_WG_RC=$?` 持左值失败码；errexit 因 `||` 抑制 ✓。函数体处于 tested-context（errexit 抑制域），guard rc（0/1/124/137/*）**全路径透传**，无中途 abort ✓。
- L247 探测 `if timeout --version … | grep -q`：if 条件域内 rc 127（command not found）安全落入 else ✓。
- L268/L275 `printf | grep -q` 在 if 条件域内 ✓；L276 `grep -c … || true` 防 rc=1 中断（grep -c 无匹配时打印 `0` 并 rc=1 → COUNT=0 语义正确）✓；L283 管道以 sed 结尾（rc=0），`grep | head` 的 SIGPIPE 不影响管道 rc（hook 未设 pipefail，与既有步骤一致）✓。
- L258/261 `date +%s%N 2>/dev/null | tr -cd '0-9'`：pipeline rc = tr（几乎恒 0）；空值由 L263 `-n` 双检兜底 ✓。
- L264 算术展开位于字符串赋值内（非独立 `(( ))` 命令）→ 零值不影响 rc ✓。

**B. quoting——通过**：L223 `"$REPO_ROOT/.governance"`、L248-252 `"${SPG_WG_PY}" "$VERIFY_WORKFLOW" … --project-root "$REPO_ROOT"`、L287 rerun 提示内嵌 `\"${VERIFY_WORKFLOW}\"`/`\"${REPO_ROOT}\"`——全部引用闭合，含空格路径安全 ✓。

**C. `date +%s%N` 净化与 BSD 兼容——通过**：BSD/macOS 字面尾缀 `N` 经 `tr -cd '0-9'` 剥离（降级整秒精度，注释如实声明）；GNU ns 时间戳 ~1.7e18 < int64 上限 9.2e18，`-le`/`$(( ))` 无溢出；T0>T1（时钟跳变）→ elapsed 置空不显示 ✓。

**D. timeout 探测语义——通过**：仅当 `timeout --version` 首行含 `GNU coreutils` 才包裹；Windows System32 timeout.exe（pause 语义，`--version` 即时报错、stdout 空）→ banner 缺席 → 不包裹；busybox/macOS 缺席或非 GNU → 不包裹。GNU 默认 SIGTERM 超时自报 rc=124 → L294 分支 ✓。"拒绝误包裹、降级为不包裹"的保守取向正确（宁可无超时保护，不可吞掉 guard）。P3 保留项见 F-3（137 混叠）。

**E. 管道 rc / 输出捕获——通过**：guard 输出整体经命令置换捕获 stdout（stderr 丢弃——guard 修复指引走 stdout print，不丢失）；空输出时 `printf '%s\n' ""` → 单换行 → 两 grep 均不命中 → UNAVAILABLE，无误报 ✓。

## 4. 五维度结论

| 维度 | 结论 | 要点 |
|---|---|---|
| 1 正确性 | **通过** | §2 契约逐字吻合 + §3 set -e/quoting/净化/探测全项核实；三层 SKIP 门（L223/L226/L236）+ 四态分派（PASS/FAIL/UNAVAILABLE×3/SKIP×3）逻辑闭合；段内**无任何 exit 语句**（L195-302 逐行核实）→ 三态恒 exit 0、流继续 Step 5；变量域 SPG_WG_* 隔离，Step 5 零干扰 |
| 2 安全性 | **通过** | 无注入新增面（参数全引用，无 eval；guard 参数为固定子命令+路径）；无敏感数据；guard check-only 零 `.governance` 写入（docstring L22623-22628 明示且面板如实转述 L285）；不新增权限/网络面 |
| 3 可维护性 | **通过（带 F-1/F-4）** | 命名前缀隔离 + 自含性有测试 pin（test_section_self_contained）；注释覆盖设计动机/映射表/回滚路径且引用条款全部实存（§5）；ROLLBACK 可操作性见 §6.6；P3 外观（F-4）与 P1 文档漂移（F-1）为文档/外观面 |
| 4 性能 | **通过** | 每 commit 增量 = 1 次 guard 子进程（30s 上限）+ 1 次 `timeout --version` 探测 fork（ms 级）+ 2 次 date/tr；post-commit 非关键路径，可接受 |
| 5 测试覆盖 | **通过（带 F-2/F-5/F-6）** | 新增 14 = 9 静态 pin + 5 行为测试；静态 pin 逐条对照 hook 原文**全部成立**（本审查逐一复核：invocation contract/verdict gate/panel markers/timeout/`|| SPG_WG_RC=$?`/ROLLBACK/no-exit/self-containment——断言子串在 L248-249/L268/L275/L269/L224/L226/L236/L217-218 等逐字命中）；行为测试在 `set -e` 下执行**真实 shipped 段**（正则抽取 L195-303，非副本），marker 文件反证 SKIP 路径 guard 未被调用——用例设计强；skip 条件诚实（复用 FIX-282 `_find_bash` 排除 WSL stub + bash 内 python 可解析性双 precondition，无 bash/python 即显式 skip 而非假通过）；总数 31 = 既有 14+3 + 新 9+5 计数吻合 |

## 5. 设计一致性

- 验收 1（commit 时点可见性）：接线位于 Step 4 与 Step 5 之间，面板词汇表复用既有惯例（✅ 单行 ↔ L151；⚠️ 单行 ↔ L141/L173；╔═╗ box ↔ L155-165）✓。
- 验收 2（timeout 防护）：GNU 语义探测包裹 + 30s + 124/137 分支 ✓。
- 验收 3（回滚文档）：见 §6.6。
- 引用真实性：`behavior-protocol.md` M1.2 L75「直写后 MUST 复跑 governance-write-guard（FEAT-011 / FIX-297）」与「hook 接线为后续候选（FEAT-011 Design Review R0 F-1 方案 2）」**原文实存**——FEAT-017 即该"后续候选"的交付，FIX-297 方案 2 引用不虚；AUDIT-150 §10 P0 REFACTOR-hook-wiring 在 plan-tracker L297 入账原文实存；FEAT-011 子命令/CLI 注册（L22612/L24181-24187/L24276）实存——无幻觉 API。
- triage 声明一致：恰 2 文件、后者为派发预授权 ✓（§1）。
- **注意（→F-1）**：本交付使 SKILL.md L126 与 behavior-protocol.md L75 的现行陈述「无 hook/commit 时点接线」变为不实——分级结论（B 级检查器 + A 级协议触发；面板不阻断、强制时点仍由 M1.2 MUST 约束）依然成立，但"无接线"字面过时，需一行措辞跟进。

## 6. AI 专项 5 项 + 回滚文档

| # | 项 | 结论 | 依据 |
|---|---|---|---|
| 6.1 | mock 残留 | **无** | 生产 hook 零 mock；`_WG_STUB` 为测试 fixture 且注释显式声明 "test fixture, not a production mock — the shipped hook always resolves the real script"（test_hooks.py L414-417 域） |
| 6.2 | 硬编码返回值 | **无** | 面板结论全部由 guard 实际 stdout（Result 行 + issue 行）驱动，无预设返回值 |
| 6.3 | 幻觉 API | **无** | §2/§5：子命令、flag 拼法、rc 契约、输出形状全部对源核对实存 |
| 6.4 | 未实现 TODO | **无** | diff 内无 TODO/FIXME/占位符 |
| 6.5 | 过度实现 | **无** | 交付恰好覆盖验收 1-3；elapsed 时间显示属验收 2「计时净化」面板质量范畴，非镀金 |
| 6.6 | ROLLBACK 可操作性 | **可操作** | L217-222：删整段即恢复 FIX-297 方案 2 纯协议姿态；自含性实证——`SPG_WG_*`/`spg_wg_invoke` 全部引用局限于 L228-300（grep 核实零块外引用），Step 5 不读；静态 pin（test_rollback_documented + test_section_self_contained）双钉 |

## 7. 采信边界（未运行项）

1. **31 passed**：静态计数交叉印证（14 Matcher + 3 BashParity + 9 + 5 = 31 ✓），执行结果采信 Developer。
2. **bash -n exit 0**：采信；本审查以逐行目检替代（if/elif/else/fi、case/esac、函数定义、子 shell 全部闭合，未发现语法错误）。
3. **projection-sync PASSED / manifest PASS / 健康 29（+1 预期瞬态 hooks_drift + 2 条 FIX-300 review 文档既有项）**：采信；其中 **hooks_drift +1 已独立核实为真**——`.git/hooks/post-commit` 存在且无 Step 4b（只读探测），且 Step 0 自升级（L117-124）下次 commit 自愈，「预期瞬态」定性正确。
4. **真实 guard 两态 + SKIP + 本仓只读观察实录**：采信；行为测试以 stub 复现输出形状，且该形状已经本审查与真实 CLI 源码逐字核对一致（§2），采信风险低。
5. **timeout 路径（rc=124/137）**：仅静态 pin，无行为复现（→F-6）。

## 8. 发现列表

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | **P1** | `skills/software-project-governance/SKILL.md` L126；`skills/software-project-governance/references/behavior-protocol.md` L75 | 本交付合入后，两处 canonical 现行陈述「CLI 被调用即强制…但**无 hook/commit 时点接线**——…（hook 接线为后续候选）」字面变为不实（post-commit 已有 advisory 面板接线）。分级结论本身不受影响（面板不阻断、复跑 MUST 仍由 M1.2 约束、仍不得对外宣示为纯 B 级时点强制），但治理仓库对宣示准确性有自订纪律，热注入面（SKILL.md 每会话加载）出现与可观察行为矛盾的事实陈述应尽快消除。Developer 披露了 hooks_drift 但未覆盖此两条文档漂移 | 本轮补一行措辞更新（如「commit 时点已有 advisory 可见面板接线（FEAT-017）；强制复跑时点仍由 M1.2 协议 MUST 约束」）或立即入账跟进任务；**不阻塞本代码合入** |
| F-2 | **P2** | `infra/hooks/post-commit` L276/L283 ← 依赖 `verify_workflow.py` L22660/L22665/L22669 输出形状 | hook 的 COUNT/first-3 抽取依赖 guard issue 行 `    - ` 与 Result 行形状，但该形状**无 guard 侧契约测试钉住**（本次 14 个新测试全在 hook 侧）；guard 输出若漂移，FAIL 面板静默退化为 `0 issue(s)`/空列表（不崩溃、Result 行裁决门仍兜底，故仅降级不误报） | 归宿建议 FEAT-020（契约矩阵冻结——80 CLI 键/Result dict 快照）：将 `governance-write-guard` 的 Result 行与 issue 行形状纳入冻结面，一并消除本项 |
| F-3 | **P3** | `infra/hooks/post-commit` L294-295 | rc=137 一律释为 "timed out"；137 亦可能为 OOM SIGKILL（非超时），措辞小概率误标（罕见、无行为影响——两路径均为 UNAVAILABLE 不裁决） | 可在文案中加 "killed (timeout or OOM)" 类措辞；可不改 |
| F-4 | **P3** | `infra/hooks/post-commit` L278-288 | FAIL box 内容行不以 `║` 收边，与 Step 2 box（L156-164 收边）视觉惯例不一致（emoji+CJK 等宽本就因终端而异，纯外观） | 可选对齐；不改不影响功能 |
| F-5 | **P3** | `infra/tests/test_hooks.py` L401-406（test_section_never_blocks） | `assertNotIn("exit 1"/"exit 2")` 不覆盖 bare `exit` / `exit 0`（`exit 0` 会吞掉 Step 5——本次实测段内无任何 exit，本审查逐行核实，风险未兑现） | 建议后续收紧为 multiline regex pin（`^\s*exit\b`）；防回归强度提升 |
| F-6 | **P3** | `infra/tests/test_hooks.py`（PostCommitWriteGuardPanelTests 覆盖面） | timeout 分支（rc=124/137）无行为测试（需挂起 stub + GNU timeout，易 flaky 而省略——取舍合理，但真机超时路径未被行为验证，见 §7.5） | 可选：以 `sleep`-型 stub + 短 timeout（如 2s）在 GNU timeout 环境加一条带条件 skip 的行为用例；或维持现状并在 FEAT-020 契约面记录 |

## 9. 总结评价

交付质量高：核心设计（Result-line 裁决门 + rc 分派 + 三层 SKIP 门 + GNU 语义探测超时 + 计时净化 + 自含回滚）在 bash 陷阱面（set -e/quoting/管道 rc/BSD 兼容）全部处理正确，且每一项都有静态 pin 或行为测试锚定；测试采用"真实 shipped 段抽取执行"而非副本，marker 反证 SKIP 路径未调用 guard，是强设计。唯一实质跟进项是 F-1 文档措辞漂移（P1，非代码缺陷、不阻塞合入）与 F-2 契约钉住归属（P2，天然归宿 FEAT-020）。**建议合入**（F-1 本轮补或紧随入账）。

---

**审查结论：APPROVED_WITH_NOTES**
unresolved_blockers=0
发现计数：P0=0，P1=1（F-1），P2=1（F-2），P3=4（F-3/F-4/F-5/F-6）
