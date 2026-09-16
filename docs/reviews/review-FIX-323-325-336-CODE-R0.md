# FIX-323 + FIX-325 + FIX-336 合并代码审查报告（Code Review R0 — 机录 round 建议：REVIEW-FIX-323-R1 / REVIEW-FIX-325-R1 / REVIEW-FIX-336-R1）

- **任务**：FIX-323（REVIEW-FIX-311 F-01/F-02/F-03）+ FIX-325（REVIEW-FIX-313 F1/F2/F3 fixture + F4/F5 登记）+ FIX-336（discover preamble + FX-BASEURL-01 归属更正，FIX-326② 连带）——一报告三 task
- **Round**：R0（三 task 均首次审查；无前轮 findings 需比对）
- **基线**：HEAD `2466a80`（实测一致）；工作树恰 **5 文件** modified / **0 untracked**（审查前后各核一次，零漂移）
- **实测规模**（`git diff --numstat HEAD`）：`dsh_compat.py` **+50/−13**（任务书 +45/−11 不精确，以实测为准）· `test_dsh_compat.py` **+145/−0** · `test_dsh_adapter.py` **+293/−34** · `lib/index.js` **+20/−5** · `dsh_fixtures.py` **+4/−2**
- **Reviewer**：Code Reviewer Agent（只读；除本报告外仓库写入 0；全部变异/反相/基线重建在 `%TEMP%\cr-fx323-325-336-r0\**`，无任何 git 写子命令）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0 / P1=0 / P2=0 / P3=4）

## 1. 独立复现结论（硬门槛全项）

| # | 复现项 | 结果 |
|---|---|---|
| R-1 | **FIX-323 RED**（copyA = 当前树 + HEAD `dsh_compat.py`；新 6 测试） | **3 ERROR + 2 FAIL + 1 ok**：`ValueError: row kind(s) in no declared table …'SOME_FUTURE_PROBE_KIND'` 从 `run_cli`/`_print_human` **裸逃逸**（两渲染面 ERROR，即 F-01 形态）✓；`'info' != 'unknown'`（F-02）✓；ghost 行 `verdict: 'PASS'`、`[None] no kind at all` 落 `[INFO]` 面（ghost PASS）✓。group 豁免测试在旧码上也绿——钉的是**保持性**属性，RED 子集 = 5/6，符合设计 |
| R-2 | **FIX-323 GREEN**（当前树定向） | **6/6 OK**（0 skip，0.002s）✓ |
| R-3 | **FIX-325 变异 M1**（copyB：catch 复原 adopt-and-destroy `rmSync`+递归 mkdir） | **①② 2/2 FAIL**，`collidingSurvived=False`：① 载荷实录 `before=['governance.staging-1700000000000-i'] → after=['governance']`（同名目录被毁并被采纳 = 审查 S4 形态精确复现）；② 赢得重试摧毁 0.1 碰撞目录（`…-3lllll`）。③ 不受扰 ✓ |
| R-4 | **FIX-325 变异 M2**（copyC：else 分支复原 CWD 前缀扫描） | **③ 1/1 FAIL**，`decoySurvived=False`；warns 实录 `nothing was removed (Error: injected: homedir unavailable)` ⇒ **load-hook 注入真触发**、`outcome.dir=''`、走 `dirname('.')` 受审路径——非测试自证 ✓。①② 保持绿 ✓ |
| R-5 | **FIX-325 GREEN**（当前树定向 3 测试） | **3/3 OK**（0 skip；CWD 测试 0.327s 真子进程；Node **v24.13.1** registerHooks 真跑）✓；全模块 **52 OK**（13.0s）✓ |
| R-6 | **discover 口径**（TestLoader 计数，不执行） | 当前树 **3193** ✓；全 HEAD 基线 copyD **3066** ✓（compat=0 + 1 失败导入占位）；仅加 FIX-336 preamble 的 copyE **3185** ✓。链路 3066−1(占位消失)+120(compat 可发现)+6(compat 新增)+2(adapter 净：−1 自证 +3 新增) = **3193** 算术闭合 ✓ |
| R-7 | **四套件 + doctor**（仓库根实跑） | `test_dsh_compat` **126 OK**（9.0s）/ `test_dsh_adapter` **52 OK**（13.0s）/ `test_dsh_boundary` **136 OK**（2.7s）/ `test_dsh_contract` **120 OK**（3.5s）/ `test_dsh_doctor` **86 OK**（37.3s）——声明「126/86/136」三数与 compat/doctor/boundary 模块计数逐项吻合 ✓ |
| R-8 | **live smoke**（standalone CLI，`DSH_HOME` 重定向 %TEMP%） | **`verdict: PASS` + enabled 23 / checked 18 / NOT verified 5（NO_SCHEMA=5）+ exit 0**——REVIEW-FIX-311 R-8 锚逐项一致（行为保持）✓；隔离 home 收尾文件数 **0** ✓ |
| R-9 | **archguard-ratchet** | **[R1] PASS 24453 ≤ 24453（only-down）**；R2~R7 全 PASS，`Result: PASS (0 violations)` ✓；`verify_workflow.py` 不在 5 文件 diff 中 ✓ |
| R-10 | **lib/index.js 纯注释核实** | 3 个 hunk 全部为 ` *`/`//` 注释行（F4 孤儿 staging 权衡 15 行登记 + F5 `created`→`stagingCreated` 两处注释改名）；`node --check` exit 0 ✓ |
| R-11 | **G-18 fail-loud 未动** | `_informational_details` 本体零改动（diff 无该函数 hunk）；`test_the_report_level_self_check_raises_on_an_undeclared_kind`（test_dsh_compat L1134）存续且随 126 套件绿 ✓；import 期 `_assert_kind_tables()` 未动 ✓ |
| R-12 | **真实环境隔离审计** | 全程 `~/.dsh` mtime 恒 `2026/9/16 10:01:20`（≥8 次采样含 smoke 前后）；变异/基线/路标 5 个副本均在 `%TEMP%`；**未执行任何 `git add/commit/checkout/restore/stash/reset`**；仓库收尾 `git status` = 恰 5 M / 0 untracked ✓ |

## 2. 审查重点逐项裁决

### ① F-01 修复语义——fail-soft 不削弱 G-18（裁决：通过）

**守卫跳闸 ⟺ verdict 已 FAIL，同源代码级证明**：`_assert_report_kinds_declared`（dsh_compat.py:316-320）以 `_classify_row(row) == CATEGORY_UNKNOWN` 收集违例；verdict 层对**同一谓词**（:1614-1624）`failures.append`，而 `_resolve_verdict` 首分支即 `failures → VERDICT_FAIL`（:1667-1668）。故 fail-soft 包装触发的每一瞬间，报告的 verdict 已经 FAIL 且 issues 已含 undeclared-kind 条目——降级行是同一事实的**第三份披露**（verdict 行 + issue 清单 + 逐行 `[FAIL]`），**不是替代**。不存在「真 kind 声明缺陷被吞为一条 finding 而判定不变」的路径。机器层 fail-loud 完整保留：`_informational_details` 本体未动、仍 raise（R-11），包装仅存在于两个 RENDER 面（其职责是呈现已判定的事实，docstring 明示该契约）。**finding 计入 verdict FAIL？**——计入，且计入发生在包装之外（机器层，先于渲染）。RED 实测反证：旧码同一报告上 verdict 已 FAIL，逃逸的只是渲染。

**exit 映射后移时序**：新序 = 逐行 `[FAIL]` → verdict 三分支（FAIL/NOT_RUN/PASS+disclosures）→ `[INFO]` 面（fail-soft）→ `if fail_on_issues and verdict==FAIL: return 1` → 尾空行 → `return 0`。与旧码**退出码等价**（旧：FAIL 分支内 `return 1`，同样跳过尾空行），差异仅在输出顺序——可行动内容（verdict+issues）从「[INFO] 之后」提前到「[INFO] 之前」，且 `return 1` 不再截断任何报告面。main()（:2159）的独立 `--fail-on-issues` 映射同样在渲染完成后判定。时序正确。

### ② `_classify_row` UNKNOWN 化（裁决：通过，无合法行误伤）

- **group 豁免面**：`_is_group_record`（:224-231，`kind=="BUILTIN" and builtin=="group"`）仍是 `_classify_row` 首分支；group 记录（kind=BUILTIN，不在 FINDING_KINDS）在旧渲染面也不会打 `[FAIL]`，单源化前后 group 记录输出**逐字节等价**；`GROUP_NAME_UNRESOLVED` 行 kind≠BUILTIN，与 `_is_group_record` 形态互斥，不受影响。新测试 `test_render_faces_still_route_a_group_record_to_info` 两面钉住（该测试在旧码上也绿 = 保持性钉）。
- **合法无 kind 行**：探针 12 处 `entry.rows.push` 全部显式带 kind（FIX-311 R-6 已核，本片未触碰探针）——UNKNOWN 化只影响**畸形记录**，且方向 fail-closed（verdict FAIL + issue）。RED 实测旧码 ghost → `verdict PASS`/issues=[] 的假绿被消除。
- **渲染面单源化回归面**：逐类枚举——declared kind（两法等价）/ undeclared·missing kind（旧 0 行 [FAIL] → 新有，与 verdict 对齐 = F-03 目标）/ group 记录（等价）。无第四类。两渲染面（:2042、:2105）同改，无漂移。

### ③ CWD 守卫构造有效性（裁决：通过——真故障注入，非自证）

- **受审路径真触发**：M2 warns 实录注入错误串、`outcome.dir=''`、decoy 被扫——证明 `resolveDshHome` 抛错确实进入 V10 catch 的「无已证明 staging」分支（lib/index.js:475/491 try 内调用 → :563-568 else）。DSH_HOME **unset** 是必要的（设置则 `homedir()` 永不被咨询，`_run_cwd_fault_probe` docstring 明示此点）。
- **替换目标逐字命中**：load-hook 替换串 `import { homedir } from 'node:os'` ≡ lib/index.js:74 原文；`url === target` 用 `pathToFileURL` 同源构造。
- **钉值充分性**：碰撞名公式 probe ≡ 产品码（lib:510 `${userDir}.staging-${Date.now()}-${Math.random().toString(36).slice(2,8)}`）；实测真实碰撞发生（种子名 `…-i`、`…-3lllll` 与行内派生名逐字相等，EEXIST 路径可达），M1 下熔断/重试两分支都被真实到达。`Math.random` 序列封顶策略（`Math.min(randCalls++, len-1)`）对 8 次循环正确（[0.5] 恒撞；[0.1,0.9] 第 2 次即成）。
- **自监控性（鲁棒加分）**：若 lib 格式化漂移致替换静默失效，homedir 正常解析 → `HOME/USERPROFILE` 已重定向 → 同步落临时 home → `synced=true` → 断言红——注入失效**自身会变红**，无静默绿。真实 home 双保险（hook 注入 + 环境重定向）成立。
- **版本闸政策**：`_node_version_tuple` 解析 v-prefixed 三元组、`>= (22, 15, 0)` 元组比较正确；本机 v24.13.1 真跑 0 skip。旧运行时 skip（NOT_RUN）而非 fail——与仓声明 engines ≥20 的关系见裁决⑥②。

### ④ discover 口径（裁决：通过）

三路标全部独立复现（R-6）：**3066 → 3185 → 3193**；+127 = compat 新可发现 126 − 消失的失败导入占位 1 + adapter 净 +2。FX-BASEURL-01 归属更正的契约面自洽：设计 dsh-compat-design-0.81.0.md:1023 明文 N-6(b)「**留 V8（按 Coordinator 指令）**」；review-FEAT-031-CODE-R1 F-11 记「未修复（FIX-326）」——本片正是该连带更正落地；新 reason 文本与设计 §2.4（`pathToFileURL(file.path).href` 守卫自注入，组合侧无法提供非 file-url 形态）及实证载体 `test_dsh_boundary.BaseUrlShapeTests`（**恰 4 条**：L694/698/703/715）逐项一致；host-contract.json:1051 的 negative-fixture 词表登记不变。

### ⑤ 测试质量 + 范围纪律 + AI 专项（裁决：通过）

- **红→绿**：三 task RED 全复现（R-1/R-3/R-4 + discover 占位），GREEN 全复现（R-2/R-5/R-7）。
- **非自证**：FIX-325 三守卫端到端执行**真实 lib/index.js blob**（包级拷贝 + 子进程 + 故障注入），且两条变异各自精确打在受审分支上；被删除的 F2 自证式用例（不加载产品的三步形状重放）确认已移除（diff 中整段删除）。
- **隔离**：全部 node 子进程 `HOME/USERPROFILE` 重定向；碰撞/CWD 探针的 dsh_home 均为临时目录；CWD 探针 `DSH_HOME` unset 但 homedir 已故障 + home 变量重定向双保险。
- **范围**：恰 5 文件、0 untracked（收尾复核）；`lib/index.js` 纯注释逐行核实（R-10）；`dsh_fixtures.py` 恰 2 行 slice 更正；`dsh_compat.py` 改动面 = F-01/F-02/F-03 三处 + 注释，无夹带。
- **AI 专项 5 项**：mock 残留 **0**（产品码零 mock；测试内 `mock.patch` 注入报告生产者为合法面测试手法，与 FIX-311 既有模式一致）· 硬编码返回值 **0** · 幻觉 API **0**（`module.registerHooks` 为 Node ≥22.15 真实 API 且有版本闸；其余 API 均经套件实跑验证）· 未实现 TODO **0** · 过度实现 **无**（`_node_version_tuple`/`_node_register_hooks_available` 为声明政策所必需）。

### ⑥ 遗留裁决项核实（供 Coordinator 写回时定夺）

1. **Gate 10/M-2 基线数字 2983→3193**：新计数 **3193 已两次独立实测**（R-6），且 3066/3185 中间路标同测——数字准确，可写回。建议写回时一并记录口径说明：3193 = TestLoader discover 计数（含 1 个可选依赖 skipUnless 模块的正常计入，不含执行）。
2. **CWD 守卫 Node ≥22.15 发布注记建议**：建议发布/CHANGELOG 对 FIX-325 记——「G-04 CWD 退化反相守卫依赖 Node ≥22.15 的同步 `module.registerHooks`；仓声明 engines ≥20，在 <22.15 运行时该守卫按 skip/NOT_RUN 政策跳过而非失败。**发布文档不得声称验收①在全部支持引擎上有测试守卫**」。此为 FIX-313 R0 F1 警示（「不得声称有守卫」）在补齐 fixture 后的**降档重述**：现在可以说「有守卫，但受引擎版本限定」。

## 3. Findings（均非阻塞）

| ID | 级别 | task | 位置 | 事实（已复现） | 影响 | 建议 |
|---|---|---|---|---|---|---|
| N-1 | P3 | FIX-323 | `dsh_compat.py:1498-1516` | fail-soft 降级行仅渲染、不入 `report["issues"]` | 无（§2①同源证明：触发瞬间 issues 已含同事实条目，判定不受影响） | 无需修改；如需穷尽可在 docstring 补一句「该行是渲染面补充披露，非 issues 成员」 |
| N-2 | P3 | FIX-325 | `test_dsh_adapter.py`（`_CWD_FAULT_PROBE` 替换串） | load-hook 依赖 lib:74 import 行逐字匹配 | 无静默风险（注入失效 → synced 断言红，测试自监控，R-5 验证） | 无需修改；lib 该行重构时同步改探针即可（同文件注释已可发现） |
| N-3 | P3 | FIX-323 | 任务书口径 | 任务书 diff 数字 +45/−11 vs 实测 +50/−13 | 记账精度 | 以本报告实测 numstat 入账 |
| N-4 | P3 | FIX-336 | discover 叙事 | 「3185（120）→ 3193（126）」的 +8 中含 adapter 净 +2（−1+3），括号注只跟踪 compat | 叙事精度 | 写回治理记录时按 R-6 算式记账 |

## 4. 五维度结论

- **正确性 ✅**：F-01 降级路径同源证明无判定吞没（§2①）；exit 映射等价且时序改进；UNKNOWN 化方向 fail-closed 且无合法行误伤（§2②）；FIX-325 三守卫与 V10 修复语义一一对应，碰撞/重试/熔断/CWD 四分支全部机器可达（M1/M2 反相证明）。
- **安全性 ✅**：探针全部落 %TEMP% + home 变量重定向 + 双保险自监控；无网络/无密钥/无枚举式删除引入；`~/.dsh` 全程零写入实测；fail-closed 方向一致。
- **可维护性 ✅**：fail-soft 包装 docstring 完整记载契约与 G-18 关系；两渲染面单源化消除双表漂移；lib 注释登记 F4 权衡（F5 变量名漂移同步更正）；测试 helper 复用既有模式（`_complete_package_copy` 与 `_catching_package_copy` 职责分离注释清晰）。
- **性能 ✅**：包装仅 try/except 零开销；单源化同为 O(rows)；新测试有界（8 次熔断上限；52 测试 13.0s；126 测试 9.0s；版本闸探测一次 30s 超时封顶）。
- **测试覆盖 ✅**：6+3 新测试全绿且经 3 组反相（RED×2 + 占位）证明捕获力；G-18 fail-loud、group 豁免等保持性属性有钉；126/52/136/120/86 五套件全绿。

## 5. 真实环境命令上报表（R4）

全部命令只读或落 `%TEMP%\cr-fx323-325-336-r0\**`（base + 5 变体副本，各 2801 文件）：`git` 只读子命令（log/status/diff/show）· `robocopy`/`shutil.copytree` 到 %TEMP% · `python -m unittest`（当前树五套件 + copyA/copyB/copyC 变体定向）· `TestLoader.discover` 计数（不执行）· `python dsh_compat.py --root .`（`DSH_HOME` 重定向 smoke，两次）· `node --check` · `node` 子进程经测试件（内部隔离）。**真实 `~/.dsh` 写入 0**（mtime `2026/9/16 10:01:20` 全程恒定）；smoke 隔离 home 收尾文件数 0；**仓库写入 = 本报告 1 文件**（受审 5 blob 分毫未动，收尾 `git status` 恰 5 M / 0 untracked）；**未执行任何 git 写子命令**。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。一句话摘要：三任务的修复语义、守卫构造与计数口径全部经独立反相复现证实为真守卫（含 G-18 fail-loud 与 verdict 同源证明），恰 5 文件零夹带，零阻塞项，4 条 P3 记录与两项遗留裁决核实随报告交付。*
