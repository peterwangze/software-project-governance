# REVIEW-FIX-432-CODE-R1 — F-1 修复验证（QuoteSyncGuardTests）+ 守卫零改动声明验证 + 前轮 findings 处置比对

**Round: R1（复审）** | Reviewer: Code Reviewer（独立实读复审，唯一写入=本报告文件）| 日期：2026-10-05
**前轮报告（已实读全文）**：`docs/reviews/review-FIX-432-CODE-R0.md`（R0：APPROVED_WITH_NOTES，unresolved_blockers=0，findings P0=0/P1=1/P2=1/P3=6，机录 REVIEW-FIX-432-R0）
R1 增量对象：commit `c68cbbd`——Coordinator 调度声明：唯一变更文件 `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+150 行，QuoteSyncGuardTests 5 case）；守卫本体（9a28e4d）零改动。Reviewer 无命令通道（角色契约：Bash 禁止），以仓库当前文件态实读为审查面，commit 元数据依调度声明（见未验证项①）。

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**（无 BLOCKING finding）
R1 新 findings 计数：P0=0 · P1=0 · P2=1 · P3=2。

- **F-1（R0 唯一 P1）修复验证：通过（大部分修复，残余降级 P2）**——QuoteSyncGuardTests 已 committed（5 case + 6 helper，实读 L24723-24870），覆盖守卫 6 个 issue 分支中的 4 个（含 R0 建议负向三态中的两态，SKILL 漂移 reword+delete 双 flavor、标记移除 manifest+normsrc 双 flavor），断言精确（恰 1 条 + 目标指向 + 反向排除），隔离形态合规（真实仓零触碰）；R0 建议明列的第三态「bp 锚行改写」（守卫 L12043-12047 分支）无专属 case → 残余缺口 R1-1（P2，随下一张 infra 测试票）。
- **守卫本体零改动声明：验证通过**——R0 引用的全部 quote_sync 面代码形态锚点与当前文件态逐字对合（详见 §2）。
- **F-2（P2）处置路径确认**：bp L855 原样未改，与「随下一张 behavior-protocol 票」的既定处置一致，不要求本票修。
- **F-7（P3）确认可闭**：Coordinator 已按 R0 建议复跑 `git show --stat` 15 文件对号（调度声明 + session-snapshot 健康位佐证）。
- 其余 P3（F-3/F-4/F-5/F-6/F-8）维持开放并逐条标注归属（§4 比对表），均不阻塞。
- **无新引入问题**：增量仅为测试文件新增类，产品面（verify_workflow.py / bp / SKILL.md / 六 manifest）零变更（§2 验证）。

## 1. QuoteSyncGuardTests 实读核验（审查面 1）— 通过

实读 L24723-24870：类 docstring（契约声明四态：正向基线 / F-4 改写·删除双态 / F-A2 单 manifest 丢标记 / 规范源丢标记 fail-closed）+ 常量（BP_REL/SKILL_REL/_ANCHOR_RE）+ 6 helper（_materialize_surfaces/_run_guard/_read/_write/_real_citation/_trigger_line_index）+ 5 test 方法。类位于 module level、文件尾 `unittest.main()`（L24873-24874）自动发现，无显式 suite 清单需注册。

- **(a) 隔离形态 — 属实**：`_materialize_surfaces` 以 `shutil.copyfile(vw.ROOT / rel, dst)` 只读复制 8 规范面（bp + SKILL + `tuple(vw.QUOTE_SYNC_ADAPTER_MANIFESTS)` 运行时引用六元组）至临时 ROOT；全部变异经 `_write(root, rel, …)` 只写临时副本——**真实仓文件零写入**（逐行实读，无一处 `_write` 指向 `vw.ROOT`）。临时目录用 `_governance_temp_dir`（**既有** helper，L94-101，FIX-403/404 家族：`@contextlib.contextmanager` + `finally: shutil.rmtree(ignore_errors=True)`——清理失败降级 no-op 不崩套件；L80-91 实证注释说明其为本 sandbox 下 TemporaryDirectory 0o700 写入受限的对策，非本票新造 fixture——A11 轻量载体精神）。`_run_guard` 用 `patch.object(vw, "ROOT", Path(root))`——镜像既有 patch 模式（R0 BM-4 引 L1094/L1109 同款）。
- **(b) 变异锚点运行时提取 — 稳健性成立**：`_real_citation()` 用 `_ANCHOR_RE`（守卫 L12040 锚正则的逐字拷贝）从**真实** bp 提取 M10.4 引文 span，`assertIsNotNone` 自检（真实锚失配 → 显式 FAIL，fail-visible 而非静默错位变异）；`_trigger_line_index` 断言 citation 在 SKILL.md 行级**唯一**命中（`len(hit)==1`——grep 实证当前全文件恰 1 处 L364），变异定位防错位、删除态的「span 全文消失」前提由此锁定。未来 bp/SKILL 协同改写时引文自动跟随，无夹具硬编码过期面；残余漂移轴见蓝军 BM-R1-1/R1-2。
- **(c) 断言精确性 — 属实（非宽断言凑绿）**：四个负向 case 全部 `assertEqual(len(issues), 1, issues)`（**恰 1 条**精确计数）+ 目标文案 `assertIn`（与守卫 issue 文案逐字对合：reword/delete → "M10.4 citation no longer verbatim in SKILL.md"〔L12050-12051〕；manifest → rel 路径 + "lost canonical marker" + 标记字面量〔L12072-12073〕；normsrc → "canonical consult-draw marker" + "behavior-protocol.md M10.3" + "fail-closed"〔L12057-12059〕）+ 反向排除 `assertNotIn("adapter-manifest.json")`（验证 F-4 面 issue 不串入 manifest 面、normsrc 断裂时 manifest sweep 确实被 else 分支跳过——「无 per-manifest 噪声」契约有断言看护）。
- **(d) 正向零误报基线在位**：`test_no_drift_yields_zero_issues`——忠实复制的规范面集 `assertEqual(issues, [])`（零误报校准）✓。
- **(e) AI 专项 5 项**：①mock 残留=无（`patch.object(vw, "ROOT")` 为标准隔离手法，断言路径无 mock 数据混入，守卫读真实文件副本）；②硬编码返回值=无（改写文案「改写后的触发行」是变异注入输入；全部断言基于守卫真实返回构造）；③幻觉 API=无（shutil.copyfile/json.loads/json.dumps/re.search/Path/patch.object 均标准库，模块级 import 实证：json L18/re L20/shutil L21/Path L29/patch L32，零新增 import）；④TODO/FIXME/XXX=无（L24723-24870 实读）；⑤过度实现=无（约 148 行承载 5 case + 隔离基建；R0 估 30-40 行为「patch read_text 内联」轻量形态，实现选择「临时目录+真实文件复制」更重但换来两点收益：测的是守卫真实文件 I/O 路径（read_text 而非 mock 文本）+ 真实仓零触碰——量级权衡合理，非投机面）。
- **结构性优点**：`json.dumps(ensure_ascii=False, indent=2)` 回写 manifest 变异——守卫只 `json.loads` 解析、不比对字节，回写格式无关紧要，合法；`_trigger_line_index` 的唯一性断言同时保护 reword 与 delete 两 flavor 的变异前提。

## 2. 守卫本体零改动声明验证（审查面 2）— 通过

R0 报告引用的 quote_sync 面代码形态锚点 vs 当前文件态（本轮逐处实读/grep）：

| R0 引用锚点 | 当前态 | 对合 |
|---|---|---|
| verify_workflow.py L12002-12017 注释头 + `QUOTE_SYNC_ADAPTER_MANIFESTS` 六元组 | L12002-12017 实读：注释五行 + 六路径（claude/codex/gemini/opencode/chrys/dsh 顺序）逐字一致 | ✓ |
| L12018 `CONSULT_DRAW_MARKER = "生成≠咨询"` | L12018 逐字一致 | ✓ |
| L12021-12075 `_check_quote_sync_issues` 全函数（L12029-12036 双 OSError fail-closed / L12039-12042 锚正则 / L12043-12047 失配 issue / L12048-12052 span 漂移 issue / L12055-12060 规范源标记 / L12062-12074 manifest 循环） | L12000-12089 实读：函数体 55 行形态逐字一致，行号零漂移 | ✓ |
| L12349-12356 结果装配（`quote_sync` 键 + dangling/deprecated/cycles 旧键不动） | L12340-12364 实读一致 | ✓ |
| 三消费点 L7500-7513（release 面 `.get`）/ L16230-16274（panel 面，本轮实读 L16258-16273）/ L22112-22162（CLI 面 FAIL→`sys.exit(1)`，本轮实读 L22148-22162） | 三处实读：注释（含 F-8 所指「.get for backward compatibility」原句）、`.get("quote_sync", [])`、计数/打印/exit 形态逐字一致，行号对合 | ✓ |
| 规范面：bp L855（F-A5 注记）/ L865·L868（标记）/ L872（M10.4 锚行）；SKILL.md L364 触发行 | bp L848-875 实读：注记原文（含 F-2 所指括号短语原样）、标记两处、锚行与守卫正则逐字对合；SKILL.md grep「新任务/事务分解后」恰 1 命中 L364（docstring "L364 at fix time" 属实） | ✓ |

**结论：零改动声明在 R0 引用锚点覆盖范围内逐字验证通过**——quote_sync 守卫、三消费点、结果装配、规范面锚全部与 R0 审查时态一致；本轮增量未触及任何产品面文件。

## 3. 测试覆盖充分性（审查面 3）

守卫 issue 分支全景（6 分支）与 committed 覆盖盘点：

| # | 守卫分支 | 位置 | committed case | 状态 |
|---|---|---|---|---|
| ① | bp 不可读（OSError fail-closed） | L12031-12032 | — | 未覆盖（R0 建议未明列） |
| ② | SKILL 不可读（OSError fail-closed） | L12034-12036 | — | 未覆盖（同上） |
| ③ | **bp 锚行改写/缺失（正则失配）** | L12043-12047 | — | **未覆盖（R0 F-1 建议负向三态之一）→ R1-1** |
| ④ | 引文 span 单侧漂移 | L12048-12052 | reword + delete 双 flavor | ✓ 恰 1 条 + 文案断言 |
| ⑤ | 规范源丢标记（fail-closed，跳过 manifest sweep） | L12055-12060 | normsrc case | ✓ 含 sweep 跳过断言 |
| ⑥ | manifest 丢标记（丢标记 flavor） | L12070-12074 | dsh 单 manifest case | ✓；⑥b（manifest 不可读/坏 JSON，L12067-12068）未覆盖（R0 建议未明列） |

- **R0 F-1 要求的负向三态 committed 化**：态②（SKILL 漂移）✓、态③（标记移除，manifest+normsrc 双 flavor）✓、**态①（bp 锚行改写）✗**——三缺一，残余定级 R1-1（P2）。缓解面：锚失配非静默——真实锚失配时 `_real_citation` 的 `assertIsNotNone` 与 baseline 测试（复制的 bp 副本锚失配 → 守卫报 issue → `assertEqual(issues, [])` 失败）均会变红，「锚在位」有正向看护；缺的是「锚失配 → 恰 1 条 + anchor 文案」的负向专属断言。
- **manifest 全丢 vs 单丢覆盖边界（按任务规范评估，非必须扩）**：单丢已覆盖；全丢 = 同一循环分支六次触发（`len==6` 聚合形态），per-manifest 检测逻辑同构，扩测仅增维护面无新增检测语义——评估为**不必扩**。

## 4. 前轮 findings 逐条比对表（审查面 4）

| R0 # | 级别 | 本轮处置状态 | 事实依据 | 处置归属 |
|---|---|---|---|---|
| F-1 | P1 | **已修复（大部分）**：QuoteSyncGuardTests 5 case committed，4/6 守卫分支覆盖、断言精确、隔离合规 | §1 实读；残余=分支③无专属 case | 本票（c68cbbd）；残余 → R1-1 随下一张 infra 测试票 |
| F-2 | P2 | **未修复（按既定路径）**：bp L855 注记原样（含括号短语原文） | bp L848-855 实读 | 下一张 behavior-protocol 票（R0 建议 + Reviewer 原建议一致；不要求本票修） |
| F-3 | P3 | 未修复：标记检查仍文件级（L12055），文案仍称 M10.3 | §2 实读 | 后续演进票（可选：span 收窄或文案改文件级表述） |
| F-4 | P3 | 未修复：嵌套引号约束注释未加（L12038-12042 无标注） | §2 实读 | 后续演进票（可选；当前引文无嵌套，纯理论面） |
| F-5 | P3 | 未修复：位置语义仍不校验（R0 已裁定可接受现状） | §2 实读 | 可选强化或永久接受现状 |
| F-6 | P3 | 未修复（测试侧部分缓解）：守卫六元组仍硬编码；本轮 `_materialize_surfaces` 运行时引用 `vw.QUOTE_SYNC_ADAPTER_MANIFESTS`——新增第 7 平台若已入元组，测试复制面自动跟随（不放大 F-6 盲区也不缩小） | §1(a) 实读 | 后续票 / adapters 文档标注（R0 建议） |
| F-7 | P3 | **已闭合（Coordinator 复跑）**：`git show --stat` 15 文件对号完成 | Coordinator 调度声明 + session-snapshot L26 健康位（write-guard PASS/三 hooks 在位/locks active 空） | 闭环 |
| F-8 | P3 | 未修复：三处 `.get` 注释原句未动（L7505-7506/L16262-16263/L22149-22150） | §2 实读（三消费点原样） | 并入 R1-1 下票顺手处理（一句话注释改写） |

**新引入检查**：增量仅为测试类新增（L24722 类间距后至 L24870，前置 FIX-397 类结尾 L24710-24721 完整未动）——无产品面变更、无既有测试改动、无新引入缺陷。

## 蓝军挑战（3 条独立 ID，已执行）

- **BM-R1-1 快照漂移面（任务规范①）**：8 规范面复制即当前形态快照，三漂移轴推演——(i) 新增第 7 平台：测试运行时引用元组自动纳入复制面，但守卫元组与 adapters 目录的同步仍靠手工（F-6 未修），测试不设防也不放大该盲区；(ii) bp/SKILL 引文协同改写：`_real_citation` 运行时提取自动跟随 ✓；(iii) 锚行**前缀措辞**协同改写（守卫正则与锚行同票改）：测试 `_ANCHOR_RE` 为正则字面量拷贝、未随守卫内联正则联动 → `_real_citation` 提取失败 → `assertIsNotNone` 显式 FAIL——fail-visible 维护信号，非静默假绿；但 docstring 称 "with the guard's own anchor regex" 措辞失准（实为逐字拷贝非动态引用），可能误导后来者忽略同步义务 → R1-2。
- **BM-R1-2 「恰 1 条」断言脆性（任务规范②）**：守卫未来新增独立检查面（如 F-3 修复将标记检查拆分、⑥b 坏 JSON 分支叠加报出）→ 负向 case 可能产生 >1 issue → `len==1` 误红需同步维护。方向分析：**过严不过松**——只会在合法演进时误报维护，绝不会宽断言假绿；「恰 1 条 + 目标指向」正是 R0 F-1 对防凑绿的精确性要求。评估：可控，不要求改。
- **BM-R1-3 「未跑即信」面**：本轮 5 case 全绿无 evidence-log 机检佐证（grep FIX-432 仅见 EVD-1316 的 1047 OK——R0 时点、5 case 尚未存在；R1 修复无新 EVD）；Reviewer 无命令通道未复跑。缓解：5 case 断言与守卫 issue 文案逐字对合、逻辑推演全部自洽（§1(c)）；类结构完整可自动发现（§1）。残余交 Coordinator 收口时一条命令闭合（跑 QuoteSyncGuardTests 或全套件，预期 1047+5=1052 OK）。

## 新 findings 清单（R1）

| # | 级别 | 位置 | 问题 | 修复建议 |
|---|------|------|------|---------|
| R1-1 | **P2** | test_verify_workflow.py QuoteSyncGuardTests（缺失面；守卫分支 verify_workflow.py L12043-12047） | R0 F-1 建议的负向三态之一「bp 锚行改写」（锚正则失配分支）无专属 committed case——守卫 6 issue 分支已覆盖 4，锚失配分支仅有间接正向看护（baseline 变红），无「恰 1 条 + "anchor line missing or reworded" 文案」断言。 | 随下一张 infra 测试票补 1 case：临时副本中改写 bp 锚行前缀 → 断言恰 1 条 + L12045-12046 文案 + `assertNotIn("adapter-manifest.json")`；可顺手补 ①② unreadable 与 ⑥b 坏 JSON flavor（各约 8-10 行）+ F-8 三处注释一句话改写。 |
| R1-2 | **P3** | test_verify_workflow.py L24751-24753 / L24775-24777 | `_ANCHOR_RE` 为守卫内联正则（L12040）的逐字拷贝，`_real_citation` docstring 称 "with the guard's own anchor regex"——实为拷贝非动态引用（守卫正则内联于函数体，无法 import）；措辞可能掩盖「两份正则 MUST 同票同步」义务。漂移方向 fail-visible（不同步 → assertIsNotNone FAIL），无假绿风险。 | 注释明示：「verbatim copy of the guard's inline regex（verify_workflow.py `_check_quote_sync_issues`）— MUST update together」；纯注释级。 |
| R1-3 | **P3** | test_verify_workflow.py L24836（`rel = "adapters/dsh/adapter-manifest.json"`） | 单 manifest case 硬编码 dsh 平台：dsh manifest 未来移除/改名时该 case 失败（fail-visible）；与 R0 F-6 六元组硬编码同族的演进备注。 | 可选：从 `vw.QUOTE_SYNC_ADAPTER_MANIFESTS` 取末元素替代字面量，或将该备注并入 F-6 的后续票一并处置。 |

## 硬门槛自检

- **P0 阻塞问题数 = 0** ✓（findings 表实证）
- **5 维度全覆盖** ✓——正确性（§1 断言-文案逐字对合、§3 分支盘点、§2 零改动验证）；安全性（测试零写入真实仓、无注入/密钥面、临时目录经既有防护 helper）；可维护性（复用既有 `_governance_temp_dir`/patch 模式不重造 fixture、命名表意、R1-2 注释措辞）；性能（5 case 各复制 8 个小文件 + 守卫单次调用，相对全套件可忽略）；测试覆盖（§3 全景盘点 + 缺口如实计级）。
- **每条发现标注级别 = 100%** ✓（R1-1~R1-3 均带 P 级；前轮 8 条逐条标注处置状态）
- **复审义务履行** ✓——前轮报告全文实读；8 findings 逐条比对（已修复/未修复/新引入三态标注 + 处置归属）；守卫本体以 R0 引用锚点逐字复核（未跳过直接 APPROVED）。
- **AI 代码专项 5 项检查全部完成** ✓（§1(e) 逐项结论）

## 事实依据与未验证项声明

**已验证（本审查实读）**：test_verify_workflow.py L14-41（imports）/L80-101（`_governance_temp_dir` 及其沙箱注释）/L24710-24874（QuoteSyncGuardTests 全文 + 前置类边界 + `unittest.main()`）；verify_workflow.py L7500-7517/L12000-12089/L12340-12364/L16258-16273/L22148-22163（守卫全块 + 结果装配 + 三消费点）；behavior-protocol.md L848-875（L855 F-A5 注记 / L865·L868 标记 / L872 锚行）；SKILL.md L364（grep「新任务/事务分解后」全文件恰 1 命中）；.governance（grep FIX-432：evidence-log L1996/L2009/L2010/L2012、plan-tracker L84/L207、session-snapshot L5-L28、decision-log DEC-314/315）；R0 报告全文（docs/reviews/review-FIX-432-CODE-R0.md）。

**未验证（不作通过依据，如实标注）**：
1. commit `c68cbbd` 元数据（唯一变更文件、+150 行、与 9a28e4d 的边界）——Reviewer 无命令通道，依 Coordinator 调度声明；当前文件态实读（新增类约 148 行净增、前置类完整、产品面锚点与 R0 时态逐字一致）与该声明相容但非独立复核。
2. QuoteSyncGuardTests 5 case 实际执行全绿——未复跑（角色契约 Bash 禁止）；无 R1 修复的 evidence-log 机检记录；依据=断言与守卫文案逐字对合的推演自洽（§1(c)）+ BM-R1-3 缓解，建议 Coordinator 收口时一条命令闭合（预期全套件 1052 OK）。
3. F-7 的 `git show --stat` 复跑输出——依 Coordinator 调度声明闭合（R0 F-7 的处置主体本就是 Coordinator）。
