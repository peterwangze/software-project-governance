# FIX-444 Code Review R0 — commit-msg 事实门否定句误报修复（独立审查）

- **轮次**: R0（初审）
- **审查方**: Code Reviewer Agent（只读；唯一写面 = 本报告；未改产品/测试/治理，未 commit）
- **审查对象绑定**: HEAD `bf6942dd…`（staged 空，实际 git 确认）；工作区 `infra/hooks/commit-msg` blob **`4ddad50→f54403ee`**（20+/1−）+ `infra/tests/test_hooks.py` blob **`b681b13→838942cb`**（110+/2−）——hash-object 由本 Reviewer 计算；triage 允许面恰两文件、第三文件未触碰
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "unresolved_blockers": 1}
```

---

## 0. 结论

设计的方向正确且大部分已验证成立：helper 的出现局部否定剥离（24 否定词 + 9 可选填充闭合表 + 编造|幻觉）在 10 行测试阴阳例、我的 9 例对抗复核、7/8 条**真实 EVD 行**上语义正确；Step12 推测模式逐字保留；`_find_bash` rider 的 WSL 根因诊断链完整（#5/#6 探针证明 which→System32 WSL、`test -d 'C:/'` FAIL vs Git-bash OK；#4 排除环境重定向致因）；模块 36 测最终全绿（4.262s）。

**但验收标准「正常用户合规提交通过」在当前真实输入上不成立**：我用 hook 真实抽取路径（awk `task_evidence_lines` 源绑定）+ 真实 Step12 条件对**当前 evidence-log.md 的 FIX-444 全部 8 行**隔离复放——**`STEP12=BLOCK(fabrication)`**。逐行归因：**EVD-1463 携带 4 处剥离后裸词**，属两类技术引用语境：①逐字保全的 `OLD_PATTERN='…编造｜幻觉'` 模式引用（Coordinator 于派发中预判的类）；②逐字保全的旧重放阳性夹具串 `check "我编造了测试结果"` / `check "本次幻觉结果已通过"`。即：**本票自己的证据行无法通过本票修复后的 hook**——与旧缺陷同类（引用型行被无语境拒绝），修一半。`unresolved_blockers=1`（§3）。

按派发要求：不覆盖/不删除机录旧行（EVD-1463 是逐字事实来源，正是不可改的那种）、不绕 hook、不伪造闭环——NC + 具体重放 + 最小语义面建议（§4）。

## 1. 变更设计核验（已成立部分）

| # | 项 | 判定 | 证据 |
|---|----|------|------|
| 1 | helper 语义/极性 | **PASS** | 源 :103-117：sed 三元组局部移除后 `grep -Eq "编造\|幻觉"` 命中=BLOCK（fail-closed 极性正确）；否定词/填充词均为闭合表；byte-literal 无多字节类（FIX-239 纪律注明）；sed 行内匹配不跨行 |
| 2 | Step12 原门保留 | **PASS** | :455-456 推测模式两个析取支逐字保留（我 diff 对照 + 测试静态断言三重绑定：helper 接线在场/推测 regex verbatim/旧合并尾不在）；仅编造\|幻觉 移交新扫描 |
| 3 | 混合句不白名单 | **PASS** | 「否定词在行内≠白名单行」——测试 3 混合例 + 我的对抗例（多行混合/`不产生幻觉但这次幻觉…`）全 BLOCK |
| 4 | 测试真咬合 | **PASS** | `FabricationNegationScanTests` 双引擎真 bash（提取 shipped 函数 + heredoc 执行）；无 bash 时 **raise 非静默 skip**（`_run_negation_scan` AssertionError）；RED 11 subfails（旧 hook 无 helper——同源 RED）→ GREEN 3/3 |
| 5 | `_find_bash` rider | **PASS** | win32 探针 `test -d 'C:/'`（非 win 保留 `:` 原行为）；根因链：#6 WHICH_BASH=system32 WSL + C_PATH_FAIL / Git-bash C_PATH_OK；#5 Git-bash fixture DIR_OK/FILE_OK/GREP_HIT；#4 无重定向复跑同 7 fails 排除环境致因——误筛只影响 win32 候选、真实文件测试由 MISS 转实跑，非静默 PASS |
| 6 | 模块回归 | **PASS** | 首跑 36 中 7 fails（预存装置缺陷，当场定位当场修——非跳过非淡化）→ 终跑 **36/36 OK 4.262s**（module_final_raw.log） |

## 2. 我的独立复核（对抗负例 + 真实输入重放）

**对抗 9 例**（源绑定 shipped 函数，Git-bash 实跑，隔离 `fix444-r0-adv-e8603693`，12:40:21Z→12:40:23Z exit 0）：

| 输入 | 判定 | 评注 |
|------|------|------|
| 不允许不编造 | PASS | **边界**：内层 不+编造 被剥→双否定逃逸（该语形实际语义为"必须编造"，但自然语料中不存在；披露为已知限制） |
| 不允许编造 | **BLOCK** | 残余误报（保守方向）：允许 不在否定表、非填充词 |
| 无法编造 | **BLOCK** | 残余误报（保守方向）：无法 不在表 |
| 并非编造了结果 | PASS | 正确安全否定 |
| 韩国编造了数据 | **BLOCK** | 正确肯定拒绝（国 非否定词——子串不误剥） |
| 杜绝一切幻觉 | PASS | 正确三元组 |
| 不编造时戳⏎我编造了结果 | **BLOCK** | 多行混合：行 2 裸词 |
| \`不编造\`时戳（markdown） | PASS | 相邻三元组不受反引号干扰 |
| 禁止编造；本次编造了数据 | **BLOCK** | 混合 sanity |

**真实输入重放**（决定性，隔离 `fix444-r0-evd-4d5dfdc9`，12:41:57Z）：真实 evidence-log.md 副本 + 源绑定 awk 抽取（8 行）+ 源绑定 Step12 条件 → **`STEP12=BLOCK(fabrication)`**（speculation 支未触发；fabrication 支触发）。逐行 python 归因（awk/sed 语义等价，12:42:40Z）：EVD-1462 CLEAN / **EVD-1463 BARE×4** / EVD-1464~1469 CLEAN。fixture sanity：无依据肯定行（`事实依据: 我编造了测试结果`）在我首次脚本中因 bash 语法缺陷（exit 2，见 §5 偏差）未跑完，但该形态 BLOCK 已由对抗例「韩国编造了数据」与测试 5 阳性例覆盖——门仍咬合。

## 3. Finding B1（P1·阻塞）真实证据行 EVD-1463 的技术引用串仍被误拒——本票自身提交无法通过修复后的 hook

- **位置**: `infra/hooks/commit-msg:115-117`（helper 无引用语境类）对照 `.governance/evidence-log.md:2186`（EVD-1463 行）
- **事实**: 4 处剥离后裸词=①`OLD_PATTERN='…\|编造｜幻觉'` 模式引用内 2 处（编造、幻觉 各一，前接 `)\|`/`)｜` 非否定词）②重放夹具引用内 `check \"我编造了测试结果\"`、`check \"本次幻觉结果已通过\"` 2 处（前接 `\"` 非否定词）。这些是**逐字保全的命令/模式事实来源**（EVD-1463 明示 exactliteral 以 command-records JSON 为准），非宣称虚构结果——与 EVD-1450 同属合规行，但语境是"引用"而非"否定"，当前扫描只有否定一个安全类。
- **影响**: 验收①（正常提交通过）失败于真实输入；且未来任何引用该模式/重放夹具的证据行同样误拒——类未闭合。
- **处置边界**: 不得改机录行、不得绕 hook、不得以 3 个 helper 测试替代真实输入通过。

## 4. 最小语义面建议（供 Developer R1；Reviewer 不改码）

在 helper 的移除面追加**第二个闭合安全语境类：技术引用语境**（与否定表同纪律——byte-literal、闭合、逐出现、unknown 默认拒）：

1. **模式对引用**：剥离字面对 `编造|幻觉` / `编造｜幻觉`（半角/全角竖线两形）。自然散文不会以竖线连接二词；markdown 表格行内半角竖线本就不可能存在（会破表）。风险≈0，披露即可。
2. **重放夹具调用引用**：剥离 `check "` 开引号至闭引号内的出现（ERE：`check "?\"[^"]*\"` 形 span，ASCII 否定类合规 FIX-239）。该 `check "` 标记是本仓重放装置的闭合调用形；真实证据散文不用此形。风险：作者在 check 串内写真实宣称会逃逸——但该语境即测试夹具引用，属可接受披露面。
3. **配套红测**（防泛化）：EVD-1463 形行（模式引用+check 夹具）PASS；散文肯定 `我编造了测试结果`（无 check 语境）仍 BLOCK；混合 `check "x"；我编造了y` 仍 BLOCK；修复后以**当前真实 8 行**经真实抽取路径复验全 PASS（复用本轮重放脚本思路，含 per-row CLEAN 断言）。

保守残余（非阻塞、随附披露）：`不允许编造`/`无法编造` 类仍保守拒（否定表闭合的代价，方向安全）；双否定逃逸边界（§2）。

## 5. 过程偏差披露（不追溯豁免）

1. Developer #4/#6 无 five-env（EVD-1462/1463 已自认，R1 纪律偏差；#4 仅自动清理 temp fixture+pycache、#6 零写——事实已核，但**不构成追溯隔离/风险接受**）。
2. #6 utc_start unknown、#3/#7 diff-stat 子退出码 unknown（记录如实）。
3. **本轮我方两处脚本缺陷**（如实）：EVD 重放脚本 per-row 诊断循环 bash 语法错误（exit 2——核心判定输出在错误前完成有效；逐行归因改由 python 等价实现完成）；对抗脚本首版无缺陷。两脚本均落隔离目录供查。

## 6. 五维度 + AI 专项

| 维度 | 结论 |
|------|------|
| 正确性 | **FAIL(B1)**——helper 对否定类正确，但真实输入存在第二安全类（引用）未覆盖；极性/混合/多行正确 |
| 安全性 | **PASS（带披露）**——fail-closed 方向保持（残余误报为保守向；双否定边界披露）；推测门/事实依据门原样 |
| 可维护性 | **PASS**——闭合表+byte-literal 纪律；建议面沿同纪律扩展 |
| 性能 | **PASS**——单行 sed+grep；模块 36 测 4.262s |
| 测试覆盖 | **FAIL(B1)**——双引擎真 bash 真咬合，但缺"当前真实 EVD 行"回归层（本轮重放即该层首跑即红——证明该层必要） |

AI 专项：mock 残留无（测试为真 bash 执行）；硬编码无（闭合表即契约常量）；幻觉 API 无（awk/sed/grep 均真实）；TODO 无；过度实现无（diff 恰两文件必要面；rider 为同票已发现装置缺陷的定向修复，测试内 win32 限定不触非 win 行为）。

## 7. 硬门槛自检

P0=0（阻塞为 P1×1，NEEDS_CHANGE 依据）✓｜5 维 100% ✓｜发现带级+位置+事实+建议 ✓｜设计一致性（triage non_goals：不放宽肯定/混合阻断、不绕 hook——除 B1 外符合；B1 即"不放宽"与"合规行通过"的未竟交集）✓｜AI 5 项 ✓｜事实红线（真实输入重放一手；unknown 如实；mojibake 仅为控制台显示）✓

## 8. 机录与后续

`review-record --task FIX-444 --round 0 --result NEEDS_CHANGE --report docs/reviews/review-FIX-444-CODE-R0.md --reviewer 'Code Reviewer'`——NC<3：Developer 按 §4 最小面返工 → **同一 Reviewer R1 必达**（注入本报告路径；R1 核验=§4 三项红测 + 当前真实 8 行经真实路径全 PASS + 无新引入）。unresolved_blockers=1。
