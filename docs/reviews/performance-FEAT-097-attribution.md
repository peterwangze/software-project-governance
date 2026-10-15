# FEAT-097 性能红灯同窗归因报告（只读版本对比——不改限额）

- **Task**: FEAT-097（验收期单一时间错误 → CPU 守卫 RED 的归因材料）
- **性质**: 只读归因报告；限额/断言/生产代码/测试/快照零修改；不构成再锚定决定（裁决权在用户/Coordinator）
- **作者**: Governance Developer Agent（原始测量与报告）；Coordinator复算并修正单位成本、余量与推论措辞（未重做测量，修改不替代独立审查；未commit）
- **窗口**: 2026-10-11 02:41~02:57 UTC（本机同一天内三个子窗口，见 §3）
- **唯一写面**: 本文件（§1~§8保留当时未修复的历史测量；当前处置与验证结果见新增§9）
- **当前结果**: 用户DEC-333选择原门限修复，关联FIX-443已修复三处闭包引用环；FIX-443 R0及FEAT-097 R6独立AWN/0机录。原CPU27.8/CLI36守卫通过，修后完整引擎1115/612.826s OK；最终健康与commit前用户交付审查尚未执行，不能据此声称会话已完成。

---

## 1. 触发事实（前置，全部一手）

1. 稳定无并行窗口完整 engine：Ran 1115 / 801.783s，1114 通过，唯一 error =
   `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`
   subprocess timeout 36s（wall 域）。
2. Coordinator 原测试/原 36s/原断言隔离复跑 3 次：36.043 / 36.075 / 36.077 全 TimeoutExpired。
3. 本 Developer 同指令 3 次完整 CLI 测量（§3.1）：wall 39.439 / 37.400 / 39.122（中位 39.122），
   全部 RC=0、verdict=PASS——36s wall 预算在含 WIP 的 live 树上**这三个已观察样本都不够**；不能由三样本推断所有环境窗口。
4. 原 CPU 守卫（`test_loop_runtime_claims.py:1086-1173`，断言 `median < 27.8`，FIX-401 锚定
   2026-09-28 HEAD `f06a2bf` p50=18.547×1.5）：观察器复跑 **RED**——读数
   31.766 / 34.953 / 36.281，中位 **34.953 ≥ 27.8**（:index 树 = HEAD `bf6942d`，
   身份 PASS 恒定：1128 candidates / 332,948 units / sha `fb1b0cbf…`）。
5. 预算面未破坏：semantic_units 332,948/434,339 = 76.7%；live candidate_bytes
   27,393,799/33,554,432 = 81.6%；skipped/truncated = 0。

## 2. 方法（同窗交替、版本对称）

- **不可变物化树**：经 `materialize_loop_runtime_git_root`（scanner 自有获取代码，
  commit 经 `^{commit}`→`^{tree}` 精确解析）物化两个精确对象到仓库外隔离 temp：
  - `hist-tree` = `f06a2bf78146b251464acf1050556a5a91b0fc9e`（CPU 锚定会话的 HEAD）
  - `head-tree` = `bf6942dd9b961a7f707db295171b1f2c8bc3c21c`（当前 HEAD；Coordinator 已验
    `git diff --cached` 空、`:index` == HEAD）
- **版本对称**：每个扫描子进程从**自己树内** `skills/software-project-governance/infra`
  加载 `checks.loop_runtime_claims`（旧版 scanner 正常导入运行，无不兼容；新旧模块互不
  污染——每扫描一个 fresh 子进程）。
- **同窗交替**：单命令窗口内顺序 H1,C1,H2,C2,H3,C3（H=hist 树×hist scanner，
  C=head 树×head scanner），交替顺序缩短两侧环境窗口间隔。
  **未采集调度/热/IO 指标，不能声称环境影响完全抵消**；差分包含版本、语料与剩余环境波动。
- **计时区**：子进程内 `time.process_time()` + `time.perf_counter()` 严格只包
  `scan_loop_runtime_claims(context)`；git 物化、import、上下文构建全部在计时区外
  （FIX-401 时钟域纪律）。上下文 = `ClaimScanContext(tree, tree/skills/software-project-governance,
  tree, "product_release")`（与守卫测试同形）。
- **隔离**：每命令先建仓库外专用 short temp 并重定向 DSH_HOME/HOME/USERPROFILE/TEMP/TMP
  五变量（PowerShell `$tmpHome` 承载，未触碰 `$HOME` 自动变量）；cwd=仓库根；
  仓库零写入；无 sandbox_permissions。

## 3. 测量数据（原始）

### 3.1 前轮：3 次 live 树 CLI（完整 JSON 已存隔离目录）

命令（逐字同测试指令，默认 product_release）：
`python <repo>/skills/software-project-governance/infra/verify_workflow.py check-loop-runtime-claims --product-root <repo> --project-root <repo>`

| # | wall s | 子进程 CPU s | RC | verdict | candidates | bytes | 身份 sha |
|---|--------|-------------|----|---------|-----------|-------|----------|
| 1 | 39.439 | 34.828 | 0 | PASS | 1222 | 27,393,799 | `f9e9fa8b…` |
| 2 | 37.400 | 33.047 | 0 | PASS | 1222 | 27,393,799 | `f9e9fa8b…` |
| 3 | 39.122 | 35.578 | 0 | PASS | 1222 | 27,393,799 | `f9e9fa8b…` |

中位 wall **39.122**；parsed==candidates==1222、skipped=0、truncated=0、stderr 空。
stdout JSON：`C:/Users/peter/AppData/Local/Temp/feat097-calib-e864a629/run1-stdout.json`、`C:/Users/peter/AppData/Local/Temp/feat097-calib-5d9a9949/run2-stdout.json`、`C:/Users/peter/AppData/Local/Temp/feat097-calib-27781ce6/run3-stdout.json`。路径为测量实际位置，未用重定向后的 TEMP 推导。

> 注：CLI 子进程 CPU 含解释器启动/import/JSON 输出，与 §3.3 纯扫描区不可直接互比（如实披露）。

### 3.2 前轮：CPU 守卫原断言（RED 窗口 02:45:39~02:47:45Z）

`python -m unittest … -k three_run_performance_identity_and_median`（原 27.8、原系数）
+ 观察器（只拦截 `statistics.median` 记录取数、包装 `scan_loop_runtime_claims` 记录身份；
零语义修改、不重复扫描；脚本 `%TEMP%\feat097-cputrip-2106342e\observer.py`）：

- **RED**：`AssertionError: 34.953125 not less than 27.8`；CPU 31.766 / 34.953 / 36.281。
- 身份三连恒定 PASS：1128 candidates / 332,948 units / sha `fb1b0cbf…`（:index == HEAD）。

### 3.3 本轮：同窗交替 6 扫描（窗口 02:53:57~02:56:41Z）

| label | 树×scanner | CPU s | wall s | candidates | bytes | units | sha |
|-------|-----------|-------|--------|-----------|-------|-------|-----|
| H1 | f06a2bf | 22.203 | 25.148 | 980 | 21,752,751 | 301,452 | `258e1204…` |
| C1 | bf6942d | 22.844 | 25.817 | 1128 | 24,679,503 | 332,948 | `fb1b0cbf…` |
| H2 | f06a2bf | 23.234 | 26.291 | 980 | 21,752,751 | 301,452 | `258e1204…` |
| C2 | bf6942d | 26.594 | 29.385 | 1128 | 24,679,503 | 332,948 | `fb1b0cbf…` |
| H3 | f06a2bf | 20.469 | 22.097 | 980 | 21,752,751 | 301,452 | `258e1204…` |
| C3 | bf6942d | 25.172 | 27.965 | 1128 | 24,679,503 | 332,948 | `fb1b0cbf…` |

中位：**H CPU 22.203 / wall 25.148；C CPU 25.172 / wall 27.965**。逐侧身份恒定 PASS。

### 3.4 派生效率（版本差分的核心证据）

| 指标 | H（f06a2bf） | C（bf6942d） | C/H |
|------|-------------|--------------|-----|
| 每字节 CPU 成本（µs/B） | 22.203×10⁶/21,752,751 ≈ 1.0207 | 25.172×10⁶/24,679,503 ≈ 1.0200 | **−0.073%（近似持平）** |
| 每语义单位 CPU（µs/unit） | 73.68 | 75.61 | **+2.6%** |
| candidates | 980 | 1128 | +15.1% |
| candidate_bytes | 21,752,751 | 24,679,503 | +13.5% |
| semantic_units | 301,452 | 332,948 | +10.4% |
| CPU 中位 | 22.203 | 25.172 | **+13.4%** |

锚定会话参照（同 f06a2bf 树，2026-09-28 窗口）：p50 18.547 → 每单位 61.53 µs。

## 4. 归因结论（三源分解；明示可排除/不可排除）

**分解式**：CPU 总量 = 语料单位数 × 每单位成本（窗口函数）。

1. **语料增长（实证，可量化）**：锚定期→HEAD 提交树 units +10.4% / bytes +13.5% /
   candidates +15.1%（0.90→0.98 批次累积，与本票单票无关——本票 WIP 尚未提交，
   :index 不含）。同窗 C/H CPU 差 +13.4% 与 bytes 差 +13.5% 近乎线性重合。
2. **算法/代码（本样本未显示显著单位成本增加）**：两侧每字节成本相差 −0.073%、每单位
   成本 +2.65%。这三组交替样本不足以严格排除算法回归或量化统计噪声，只支持单位成本
   接近的观察。按派发“最多一次”授权未执行 cProfile；不是已证明追加剖析没有信息。
3. **窗口差异（实证存在，具体因果未观测）**：历史树锚定窗口 18.547 → 本轮历史树
   22.203（+19.9%），该跨会话数据还含 Python/系统等未控差异。相同 HEAD 树本轮两个窗口
   的中位为 25.172 与 34.953125；每单位分别 75.60 与 **104.98 µs**，后者高 **38.86%**。
   这说明绝对耗时随窗口变化；未观测频控、调度、IO、残留进程，不能指定机载根因，
   也不能把相对旧锚总增长 +88.5% 直接当成环境单因素或宣称已验证旧包络。
   **（形态混淆修正，见 §8：上述 25.172 来自 fresh 子进程形态、34.953125 来自原测试
   in-process 形态——该对比混合了测量形态变量，不能作为纯窗口差异证据；§8 同窗判别
   实测同树同码两形态中位差 +21.4%。）**

**合成边界**：原CPU预算27.8不变。后续同窗当前树p50=25.172（原预算余量9.45%），
前窗p50=34.953125（超预算25.73%）；两次语义身份恒定PASS。Git索引等于HEAD，本票
未stage的新代码不在该CPU扫描树内；因此该次红灯不是本票未提交代码直接进入被测树
所致。语料+13.45%与窗口差异均已观测，不能由这些数据唯一分解算法/环境因果。
CLI的36秒上限低于三次完整wall样本37.400~39.439；不能独归因于纯语料或称为安静窗。
可按已记录的FIX-346/DEC-262公式提出wall再校准，但不因此放宽CPU或生产扫描限额。

## 5. 命令留痕（全部 UTC；root=`D:\AI\agent\claude\coding\project_management_workflow`；仓库零写入）

| # | 命令（要点） | UTC start→end | exit | 隔离目录/影响 |
|---|-------------|---------------|------|----------------|
| 1 | 3×CLI 测量（§3.1，.NET Process 取 wall+CPU，stdout 落盘） | R1 02:41:59→02:42:38 / R2 02:43:25→02:44:02 / R3 02:44:09→02:44:48 | 0/0/0 | `feat097-calib-e864a629`、`-5d9a9949`、`-27781ce6`（各含 runN-stdout.json） |
| 2 | 观察器 v1（unittest.main 路径加载失败——我方工具缺陷） | 02:45:20→02:45:20 | 1 | `feat097-cputrip-d40e76e3`（无测量产出） |
| 3 | 观察器 v2 = CPU 守卫原断言 + 读数/身份观察（§3.2 RED） | 02:45:39→02:47:45 | 1（断言 RED，即测量目的） | `feat097-cputrip-2106342e`（observer.py；测试自带 temp 在隔离 TEMP 内） |
| 4 | 同窗交替（§3.3）：setup 物化两树 + H1..C3 六子进程 | 02:53:57→02:56:41 | 0（setup 与 6 扫描全 0） | `feat097-attrib-d78b8f7f`（hist-tree/ head-tree/ setup.py/ scan_once.py；逐扫描起始 UTC：H1 02:53:59、C1 02:54:25、H2 02:54:52、C2 02:55:19、H3 02:55:49、C3 02:56:12——**逐扫描 end 未单独打戳**（由次序+总窗推算，如实标注），扫描内 CPU/wall 由子进程自记） |

工具缺陷披露：#4 中一条 pwsh `WriteAllText` 首次调用括号笔误（stderr MethodException），
同命令内已纠正写入 setup.py（SETUP_EXIT=0 证明）；不影响任何测量。
#2 的 unknown：无（失败即全部输出）；#1/#3/#4 时间戳完整如上。
保护：全程五变量重定向至各命令专用仓库外 temp；未触碰用户 HOME/DSH_HOME 真实目录；
对用户环境写仅限隔离 temp 与其中的脚本/JSON（追加式）；未 commit/push、未写 `.governance/`、
未用 sandbox_permissions；原测试/index/git stage 零写。

## 6. 最小后续方案（供独立审查，不自行接受风险）

- **最小方案：只校准CLI墙钟超时，CPU守卫不变。** 既有test_verify_workflow.py
  109~126的FIX-346/DEC-262规程为三次同指令p50×1.5；本轮ceil(39.122×1.5)=59秒。
  半额29.5秒小于三样本最小37.400秒，仍有可复算的反向约束。改面限定为该测试的
  subprocess timeout与来源注记，保留RC=0/PASS/parsed一致/skipped0/truncated0全部断言；
  CPU测试median<27.8、semantic_units434339、32MiB、所有生产fail-closed逻辑不变。
  原CPU测试须原样复验通过；若复验仍红灯，就保留阻断，不用wall校准越过CPU失败。
- **边界：** 调整CPU预算、改为交替差分性能断言、接受失败验收或绕过门禁均超出上述
  最小方案，必须由Coordinator依据behavior-protocol M5.3呈现具体风险/范围并取得用户
  明示裁决。当前不实施这些动作、不通过登记未来事项跳过当场失败。
- **交付证据：** 保全稳定1115的1114通过/1时间错误；后续只复验受改时间用例及关联类、
  原CPU性能守卫与FEAT-097接线，不将组合验收写成修复后整套单次全绿。
  独立Reviewer核验后才进入治理关键交付物审查（commit前）。

## 7. 边界与未做事项（§1~§6 归因阶段）

限额/断言/生产/测试/快照零修改；未执行第四轮校准、未重跑 1115、未跑 cProfile（§4.2
理由）；未写治理记录、未 commit；R5 后置审查由 Coordinator 独立派发。归因中「窗口机载
差异」未观测——明示为未闭合项，不伪称已闭环。

---

## 8. 同窗测试形态判别（原CPU二次RED后追加；实际6诊断扫描+2剖析预热+1剖析扫描，预热超出原6+1上限）

- **目的**：§4.3 遗留的形态混淆——原测试（单进程连跑 3 扫描，in-process）与归因轮
  C 侧（每扫描 fresh 子进程）同树同码读数差 ~35%，需同窗判别是测量形态还是机载窗口。
- **受控设计**：两形态共用**同一**物化 `:index`==HEAD 树（setup_facts.json：
  scanner 树内/仓库 live 双侧 SHA256 相等 `42925298ab120faca6ab0fa2af027394651a8d5e378d40b67df9bee99c0014e3`，关闭路径混用）；两形态 scanner 均从树内路径加载、
  同一 ClaimScanContext 构形；计时区仅 `scan_loop_runtime_claims`；**不操纵 gc**
  （只观测）；观察点（计时区外）记录 gc_enabled/gc_count/gc_collections/gc_threshold/
  modules/sys.gettrace。`traced:false`字段只证明`sys.gettrace()`为空，**不是**
  `tracemalloc.is_tracing()`实测。`PYTHONTRACEMALLOC=ABSENT`为03:20:06Z会话状态，
  不能回溯证明各扫描子进程启动状态；脚本没有显式开启tracemalloc，原测试只在另一个
  :930方法中显式start/stop，但没有逐扫描is_tracing记录，故内存追踪混淆未被实测完整排除。
- **结果（同窗 03:13:28→03:16:50Z，恰 6 扫）**：

| 形态 | CPU s（3 次） | 中位 | 身份 |
|------|---------------|------|------|
| in-process（复刻测试体） | 29.203 / 31.516 / 36.250（**进程内单调上升**） | **31.516** | 恒定 PASS 1128/24,679,503/332,948/`fb1b0cbf…` |
| fresh（每扫新进程） | 28.188 / 24.734 / 25.953 | **25.953** | 同上恒定 |

  中位差 **+21.43%**；本次两批样本出现fresh中位<27.8<in-process中位的判定差异。
  运行次序为同进程批次后fresh批次，未随机交错，窗口随时间变化仍是混淆；不能由一次
  六扫描实验唯一证明进程形态是差异原因。gc collections为进程启动以来累计计数：
  1→188→318→459，三个扫描增量187/130/141。累计计数自然增加，**不证明保留对象
  增多或GC压力逐轮上升**。阈值观测(2000,10,0)、gc enabled、modules122不变；
  还没有对象保留数量、GC耗时或GC因果干预证据。
- **cProfile（授权内 1 次；第 3 次 in-process 扫描；profile 使该轮膨胀至 70.5s，
  非校准样本）**：top tottime = `builtins.compile` 9.74s（181 次候选文件编译）、
  `_build_python_claim_provenance_index` 6.31s、`_python_parse_bundle` 6.05s（cum
  22.2s）、`isinstance` 4.86s（18.06M 次）、json `iterencode` 4.83s（357,788 次）——
  本轮热点为解析/索引/序列化等分布；没有历史相同profile作对照，不能证明算法没有
  回归、工作严格线性、GC是原因或不存在异常热点。profile3rd.py实际先做两个未计时
  扫描再剖析一次，共3扫描；两次预热超出了Coordinator原“六scan+最多一次profile”
  诊断上限，作为过程偏差披露，不把它们隐入六样本或用来改阈值。
- **结论（观察与因果边界）**：①观察到两批样本中位差21.43%、同进程三个读数上升；
  尚未证明进程形态或GC造成差异。②原CPU两次RED继续有效，fresh对照不替代原测试；
  原测试34.953/34.234与复刻31.516的残差包含unittest装载、批次时序和环境变化。
  ③没有原始机载或对象级证据可唯一分解原因。④历史/current单位成本接近及本轮剖析
  为后续修复的定位线索，不能严格排除算法回归。
- **验收状态**：CPU 守卫（原 in-process 形态）今日三窗全部 RED（02:45、03:05、
  03:13 复刻）→ **验收 BLOCKED 维持**；wall 36→59 **未执行**（前置门正确拦截）。
- **最小后续选项（均涉新产品文件/测试形态/阈值调整之一，scope/risk 待用户 M5.3
  裁决，本报告不选择）**：
  1. 测试形态重设计（性能断言改 fresh-进程形态或进程内扫间释放保留对象）——改的是
     测量形态，需论证不弱化 tripwire 语义；
  2. CPU 预算按 DEC-262 documented-load 路径受管再锚定（以本报告为归因记录）；
  3. scanner 侧降低跨扫保留/复用编译产物（产品优化，新范围）；
  4. 维持阻断交付现状。
- **原始产物（盘上，非transcript-only）**：`C:/Users/peter/AppData/Local/Temp/feat097-shapedisc-20958ea1/`：
  `setup_facts.json`、`shapeI.json`、`shapeF_run1.json`~`shapeF_run3.json`、
  `profile_cumulative.txt`、`profile_tottime.txt`、脚本 `setup.py`/`shapeI.py`/
  `shapeF.py`/`profile3rd.py`。
- **本节命令留痕**（全部五变量隔离、仓库零写入、cwd=仓库根）：

| # | 命令 | UTC start→end | exit | 说明 |
|---|------|---------------|------|------|
| 8.1 | 判别首轮（setup 物化+双侧哈希 + shapeI + 3×shapeF） | 03:13:02→03:13:04 | setup 0；扫描 4×1（**零扫描消耗**：observe() 在计时前 KeyError `'threshold'`——Python 3.14 gc.get_stats() 无该键，我方 wrapper API 缺陷，traceback 可复查） | 产出 setup_facts.json（哈希证据固化） |
| 8.2 | 修复 observe（get_thresholds）重跑 | 03:13:20→03:13:21 | 4×1（零扫描消耗；AttributeError：本机 API 为 `get_threshold` 单数） | 二次 API 修正证据 |
| 8.3 | 终版判别（get_threshold） | 03:13:28→03:16:50 | shapeI 0；shapeF×3 全 0 | 6 扫恰用尽授权；逐扫 CPU/wall/身份/观测落 shapeI.json + shapeF_run*.json |
| 8.4 | cProfile第3次in-process扫（实际另含2次未计时预热，属于超额） | 03:17:19.623Z→03:19:43.495Z | 0（verdict PASS findings0） | profile累计/tottime落盘；此命令3scan，全轮实际9scan |
| 8.5 | `PYTHONTRACEMALLOC`会话状态读（无python、非扫描） | 03:20:06.232Z | —（输出ABSENT） | 未采集历史子进程is_tracing，不算逐进程排除证据 |

- **§8 unknown（明示）**：原测试与复刻的装载、批次时序和窗口差异没有分解；保留对象
  与GC因果没有对象级证据；`traced`只检测sys.gettrace，未逐扫描测is_tracing；报告
  只能支持阻断仍在及后续有界修复的方向，不能声称诊断原因闭环。Coordinator已在独立
  审查前修正以上边界，Developer接受全部修正及两次额外预热的过程偏差。
- **实际命令绑定**：隔离根`C:/Users/peter/AppData/Local/Temp/feat097-shapedisc-20958ea1`；
  `python <root>/setup.py D:/AI/agent/claude/coding/project_management_workflow <root>`；
  `python <root>/shapeI.py <root>/idx-tree <root>/shapeI.json`；
  `python <root>/shapeF.py <root>/idx-tree <root>/shapeF_runN.json runN`（N=1,2,3）；
  `python <root>/profile3rd.py <root>/idx-tree <root>/profile_cumulative.txt`。
  逐命令完整路径、实际UTC、退出码与原始产物由Coordinator保存在
  `.governance/incidents/FEAT-097-shape-command-records.json`及对应`.governance/incidents/FEAT-097-shape-*`副本。

## 9. 用户裁决后的原门限修复与真实验证（Coordinator补录）

- 用户选择“原门限修复”，机录DEC-333；机器TRIAGE-FIX-443，P1/user-named/0.98.0。实际生产改面为scanner与对应测试两个文件，183+/75−；原CPU27.8、CLI36、semantic434339/32MiB/1500与安全语义保持。没有采用§6/§8的校准或fresh替代方案。
- 源码与新回归确认三处递归闭包self-cell环：`_python_accounting.container_chain`捕获parents/container_cache，另两个JSON walk同型。AST祖先链改为等价迭代，JSON递归移至模块级并显式传参，释放局部循环引用。没有生产GC配置变更、跨扫缓存或扫描子集。新资源寿命回归旧码3subTest FAIL→新码PASS；只有json_units=9的旧环计数在截尾工具输出中保留，另外两案具体计数unknown。该机制是已证资源寿命缺陷，仍不把历史全部耗时增长归为唯一原因。
- Developer完整loop模块65/176.524s OK（含原CPU三扫守卫）、关联CLI/双口径/桥接接线12/111.469s OK。修后精确索引树单扫身份1128/24679503/332948/fb1b0cbf…一致；该四元组只证明所记录身份面，不能扩为全部输出字节证明。语义遍历等价由Reviewer逐行对照与回归支持；单扫15.125CPU秒不用于跨形态精确因果比例。
- 同一Reviewer独立FIX-443 R0 AWN/unresolved_blockers=0；FEAT-097 R6 delta/baseR5 AWN/0，明确原B1/B2消解。原CPU目标Ran1/56.314s OK；原CLI timeout36目标Ran1/20.874s OK；新资源回归独立PASS。原三扫具体CPU读数与median没有提取，保持unknown，验收依据是未改断言的实际通过。原日志已存incidents/FIX-443-reviewer-cpu-guard.log和-cli-guard.log。
- 两条review-record机器事务seq16/17，报告sha分别5126bc7ae159b5decd28fca24c623246a8d8aaf8f3ac5bd82181d3ccc363a4ba与68fbe4acd8c25a1bcaaf0bf2886026379b4be0aac60c8a3ffa5ca797dee148d4。G6映射无unit，wired=false/degraded=false，不宣称flow-unit绑定。R5为历史BLOCKED保持；其“NC3+”描述已由R6修正为仅R0/R1两次NC，重新接合依据是实际BLOCKED T4与用户DEC-333。
- Coordinator修后稳定窗口完整engine单跑：UTC12:09:33.6756615Z至12:19:46.8029185Z，exit0，Ran1115tests/612.826s OK，日志存incidents/FEAT-097-post-FIX-443-engine-regression.log（EVD-1460）。five-env外部sg-e1976bd8，期间无治理/产品写或并发扫描。
- 纯judge_budget按原九调用/参数/median<10ms实测0.00290000753ms（max0.26650000655ms）；公开record_execution含锁和持久I/O另观测median6.0586ms、首次40.2911ms，不冒充整个API的10ms保证（EVD-1450）。居民注入4441<=6200硬门通过，skill超45为report-only；架构尺寸4ERROR/33WARN为原advisory披露，增量ratchet0violations，未regen（EVD-1461）。
- Developer及Reviewer精确命令历史已入incidents/FIX-443-command-replay.json与FIX-443-reviewer-command-records.json；原unittest部分输出仅工具transcript，原细节缺失诚实保留。当前还有独立FIX-444处理正常提交hook否定句误报，以及最终健康/关键交付物用户审查/实际commit；不将验证通过提前写成全部交付完成。

