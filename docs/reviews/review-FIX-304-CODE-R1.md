# Code Review R1: FIX-304-CODE-R1 — G-1 微补增量复审

- **Task**: FIX-304（复审 round 1）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户直接交互）
- **Round**: **R1**。**前轮引用**：`docs/reviews/review-FIX-304-CODE-R0.md`（本人 R0：APPROVED_WITH_NOTES / unresolved_blockers=0 / P0=0·P1=0·P2=1（G-1）·P3=5（G-2~G-6）），机录于 `.governance/evidence-log.md`:1957（`REVIEW-FIX-304-R0`）。复审的**本质是验证修复**——本报告逐条标注前轮发现的"**已修复 / 未修复 / 新引入**"状态（M7.4 复审协议），并对本批增量做全量独立核验。
- **复审对象（工作树，非 commit）**: G-1 微补增量，基线 = **本人 R0 冻结的 ODB blob**：
  - `git diff 4c34b0012cc6af5cdab42e23c470df3141ce878b -- …/quickscan_registry.py` → **+50 / −17**（实测吻合）
  - `git diff 527d77549d3464f3f9d721f6cdcf0a1eb86c2cd9 -- …/tests/test_quickscan_registry.py` → **+35 / −0**（实测吻合）
- **新冻结锚核验（审查开始 + 落盘前各复算一次，均一致）**：
  | 文件 | 工作树 blob（派发锚） | 实测 | 行数 | 前轮（R0）blob |
  |---|---|---|---|---|
  | `quickscan_registry.py` | `1381d815414eeccc050bda2fed14ce03ec0c7732` | ✅ 相同 | **1029**（996+50−17 ✅） | `4c34b001…` |
  | `test_quickscan_registry.py` | `4c75858e99ae25669b1c6f71653f53a9f50c9773` | ✅ 相同 | **938**（903+35−0 ✅） | `527d7754…` |
  两 R0 blob 仍在仓中可解析（`git rev-parse` 成功）⇒ 增量基线未丢失，前轮结论可逐字节对照。
- **执行过的只读命令**: `git hash-object / rev-parse / show / diff(--numstat / -U0 / -U10)`；`python -B` 内存内省（**含把 R0 blob 编译进内存作为 "PRE-FIX" 模块做实弹对照**）；`pytest -B -p no:cacheprovider`（目标 82 例 + 消费者 77 例）；`coverage`（`COVERAGE_FILE` → `%TEMP%`，仓外）；`verify_workflow.py archguard-ratchet`（默认只读路径）。
- **边界声明**: 未修改任何被审文件（两 blob 前后一致）；除本报告外未写入任何仓库文件（`-B` + `-p no:cacheprovider` + `COVERAGE_FILE` 重定向后仓内零新增产物）。**并发环境披露**：工作树现有 **6 个 `M`**——4 个 FIX-303 在飞（`core/architecture-baseline.json`/`archguard_ratchet.py`/`contracts.py`/`tests/test_contracts.py`）+ `infra/registry.py`/`tests/test_registry.py`（并发任务扩面，见 §五门禁第 5 条）；另有 `?? docs/reviews/review-FIX-303-CODE-R0.md`。**本批审查面恒为两 quickscan 文件**，全部结论路径限定于此。

---

## 一、复审要点逐条裁决（任务书 5 条）

### (1) G-1 修复有效性 — ✅ **成立（4/4 路径）**

我把 R0 冻结 blob（`4c34b001`）编译进内存作为 **PRE-FIX 实测对照**，对同四个入参施加同一重复输入（`snapshot + ("29",)`），PRE/POST 逐字段对照：

| 入参路径 | **PRE-FIX**（R0 blob 实弹） | **POST-FIX**（`1381d815` 实弹） |
|---|---|---|
| `guard_completeness(observed_ids=dup)` | **NO RAISE**｜`ok=True`｜`declared=70 observed=71`｜`warnings=0` | `ValueError`｜`duplicate`✅｜`§4.1 R5`✅｜context = `guard_completeness(observed_ids)` |
| `guard_completeness(declared_ids=dup)` | **NO RAISE**｜`ok=True`｜`declared=71 observed=70`｜`warnings=0` | `ValueError`｜`duplicate`✅｜`§4.1 R5`✅｜context = `guard_completeness(declared_ids)` |
| `reconcile_snapshot(actual_ids=dup)` | **NO RAISE**｜`ok=True`｜`expected=70 actual=71` | `ValueError`｜`duplicate`✅｜`§4.1 R5`✅｜context = `reconcile_snapshot(actual_ids)` |
| `reconcile_snapshot(snapshot_ids=dup)` | **NO RAISE**｜`ok=True`｜`expected=71 actual=70` | `ValueError`｜`duplicate`✅｜`§4.1 R5`✅｜context = `reconcile_snapshot(snapshot_ids)` |
| 发现路径（R0 已守，回归对照） | `ValueError`（R0 实测） | `ValueError`｜两 token 齐备｜context = `<fixture path>`（与 PRE 的前缀同构） |

**结论**：R0 G-1 所报的"第二入参路径静默 `ok=True` + `len()` 失真"已在**全部公开入参**上消除；报错文案**四种路径逐一含 `duplicate` 与 `§4.1 R5` 锚**，且 `context` 标签**逐一可辨识出是哪个入参**（诊断可用）。R0 docstring 的绝对措辞（"本守卫**永不**把重复输入报成 `ok`"）现在**与实现相符**——因为 `observed` 与 `declared` 两侧均已落检（实测：通行路径 `guard_completeness()` = `ok=True/observed=70/declared=70`，无重复输入时行为不变）。

### (2) 家族补齐裁决 — **接受（不需回退）**

Developer 在本人指示的 2 条（`observed_ids`/`actual_ids`）之外，另守了 `declared_ids`/`snapshot_ids` 两条并补 2 测试。**裁决 = 接受为完成态**，依据（全部为可复查事实）：

1. **同一不变量的真实成员，而非投机镀金**：PRE-FIX 实弹显示两条"额外"路径与 G-1 两条**呈现同构缺陷签名**——`ok=True`、零告警、`len()` 失真（`declared=71` / `expected=71`）。即它们**不是**预防性猜测，而是既有缺陷的实例（与 R0 G-1 描述的伤害机制"`len()` 被 71/70 混淆时会传递到消费面"逐字对应）。
2. **半闭合本身是缺陷**：若只守 2/4，则**相邻公开入参**仍返回静默 `ok=True`——这正是 R0 G-1 命名的病理（守卫只挂在一部分入口上）。R0 在 F-3 判定中已确立"注册表侧与观察侧同构"的标准，家族内不对称会直接违背该标准。
3. **披露完整**：新 helper 的 docstring **逐点枚举**了覆盖集（5 个点：discovery census / guard observed / guard declared / reconcile actual / reconcile expected）；2 条新测试在 docstring 中显式自述 "Family completion" 并给出理由；任务上下文已如实上报"超出指示的 2 条"。**无隐藏扩面**。
4. **成本与可逆性**：模块净增 +33 行（+50/−17），**未新增状态语义**（不新增异常类型、不新增 reason code、不新增四态 token）、未碰 schema/契约/引擎/CLI、**no-dup 路径行为逐项等价**（见 (3)），两条调用点彼此独立 ⇒ 回退成本确实 ~1 分钟。
5. **判"越界"的边界在哪里（本批未触碰）**：若改动换用新异常型/新 reason code/四态词汇、改写 product-gate 或 AST 机判、或触碰 70 行表本体与行 schema，才算越界。**实测 diff 的 5 个 hunk 全部落在唯一性守卫家族内**（`@@ -711,0 +712,19 @@` 新 helper / `@@ -818,7 +837 @@` discovery 委托 / `@@ -924,4 +937,16 @@` reconcile / `@@ -939,3 +964,5 @@` 与 `@@ -943,3 +970,9 @@` guard docstring + 双侧守卫）⇒ 无越界成分。

**因此：家族补齐 = 同一不变量在同一公开参数家族上的最小闭合形式，接受并视为 G-1 的完成态。**

### (3) 去重实现单一化 + 无回归 — ✅ **成立**

- **唯一实现（机判）**：`_duplicate_ids` 全文出现 2 次 = 定义（:697）+ **唯一调用**（:722，位于新 helper `_reject_duplicate_check_ids` 内）；全模块**唯一 raise 站点** = :725（`duplicate CheckID(s)`）；旧的 **inline raise 文案 `duplicate engine segment section(s)` 在模块内已 0 命中**（机判）⇒ 不存在两份实现/两处文案。
- **no-dup 行为逐项等价（PRE vs POST 内存实弹对照，全部 True）**：`guard.lines()` 相等｜`reconcile` 的 `expected`/`actual`/`lines()` 相等｜`discover_engine_segment_ids()` 相等｜`discover_product_gate_ids()` 相等｜`plugin_face_not_product_gated()` 相等｜`dual_root_disclosures()` 相等｜`registry_ids()` 相等｜`quick_face_ids()`/`excluded_ids()` 相等。
- **既有负对照链路保持**：重复 fixture（`extra_segments=("29",)`）→ 发现路径 `ValueError`；新段 fixture（`extra_segments=("41",)`）→ `undeclared=('41',)` / `fail_closed=True` / `observed=71` / `fallback_target='full'`（与 R0 一致）。
- **类型保持**：`guard_completeness(observed_ids=list(...)).observed` 与 `declared_ids=list(...).declared` 仍为 `tuple`；`reconcile_snapshot(actual_ids=list(...))` 仍 `ok=True`（入参宽容性未被守卫破坏）。
- **净行数实测（供记录口径澄清，见 R1-N3）**：discovery 委托 hunk `@@ -818,7 +837 @@` = **7 removed / 1 added（净 −6）**；模块整体 **+50/−17（净 +33）**。任务书所述"发现路径改调用**净 −10 行**"与该 hunk 的实测不符（见 R1-N3，不影响本项裁决）。

### (4) 报错文案变更 — ✅ **语义等价（附一处诊断取舍）**

- **新旧文案**：`f"{path}: duplicate engine segment section(s) {…} — Check ID uniqueness is zero-tolerance (§4.1 R5)"` → `f"{context}: duplicate CheckID(s) {…} — Check ID uniqueness is zero-tolerance (§4.1 R5)"`。
- **机器可判语义保留**：两个 token（`duplicate`、`§4.1 R5`）在**全部 5 个覆盖点**实测齐备（§一 (1) 表 + discovery 路径）；旧测试 `assertRaisesRegex(ValueError, "duplicate")`（:702）继续通过（82 passed 机证）。
- **前缀语义等价**：发现路径的 `context = str(path)` ⇒ 前缀与原 `f"{path}: "` **逐字符相同**，仅描述词由"engine segment section(s)"变为通用"CheckID(s)"。
- **无消费方依赖旧文案**：全仓检索 `duplicate engine segment section` 仅命中**本人 R0 报告**（`:31`）——无代码/测试/文档依赖该措辞 ⇒ 变更无破坏面。
- **取舍（可接受）**：损失"engine **segment section**"这一针对 census 病因的诊断特异性，换取"**哪个入口**带入重复"的 context 标签。四条新路径下 context 明显更有用；发现路径仍带 `path`（可定位到 fixture/引擎文件）。判定：语义等价、诊断等价或更优，**无需修改**。若要两全，可在 discovery 的 context 加一词（如 `f"{path} (engine census)"`）——可选，不阻塞。

### (5) 增量测试有牙 — ✅ **成立（RED 反事实 + GREEN 机证）**

- **RED 反事实（本人独立复原）**：G-1 的两条新测试（`observed_ids`/`actual_ids`）在 PRE-FIX 上必然以 `AssertionError: ValueError not raised` 失败——因为 PRE-FIX 实弹显示这两条路径**返回 `ok=True` 而非抛错**（§一 (1) 表）⇒ 任务书所述 "RED 2 failed: ValueError not raised" 与事实一致。另 2 条家族测试是**随修复同批加入**（其 RED 状态出现在修复实施前无意义，故不构成额外 RED 计数）——该口径自洽。
- **GREEN 机证**：`pytest`（`-B -p no:cacheprovider`）= **82 passed / 0.43s**（独立复跑，可重复）。
- **测试清点（重命名级差异）**：R0 78 → R1 **82**；`removed = []`、`added = 4`、`kept = 78` ⇒ 78+4=82 ✅（无静默改名/删除）。新增 4 条全部位于 `CensusIntegrityTests`（6→10），全部使用 `assertRaisesRegex` 并**逐一钉住 context 标签**（`:721 "observed_ids"` / `:727 "actual_ids"` / `:738 "declared_ids"` / `:744 "snapshot_ids"`）——比"只断言抛 ValueError"更强（能区分是哪条路径失守）。
- **限制（R1-N2，P3）**：4 条新测试**未**断言 `duplicate` / `§4.1 R5` 两个文案 token（仅 `:702` 的旧测试断言 `duplicate`）⇒ 若将来文案退化（丢掉 R5 锚），测试不会失败。建议一行增强（见 §五）。

---

## 二、前轮发现逐条状态（已修复 / 未修复 / 新引入）

| 前轮项 | 级别 | R1 状态 | 依据 |
|---|---|---|---|
| **G-1**（显式入参路径无唯一性守卫；docstring 绝对措辞） | **P2** | ✅ **已修复** | 4/4 路径 PRE→POST 实弹对照（§一 (1)）；docstring 措辞现与实现相符；no-dup 行为逐项等价（§一 (3)）；新增 4 条针对性负对照测试（§一 (5)） |
| **G-2**（F-1 AST 机判对间接 I/O 无牙） | P3 | ⏸ **未修复（不在本批指示范围）** | 本批为 G-1 微补：模块无新增 hunk 触及 AST 相关面，测试侧新增 4 条全部为重复入参用例（`added=4` 已逐名核验）⇒ 维持 R0 的 P3 加强建议状态 |
| **G-3**（F-2 只守"零命中"） | P3 | ⏸ **未修复（不在本批指示范围）** | `discover_product_gate_ids` 无任何 hunk（hunk 头实测仅 711/818/924/939/943）⇒ 维持 P3 |
| **G-4**（EVD-998 清点式算术 79≠78） | P3 | ✅ **已修复（Coordinator 侧）** | `.governance/evidence-log.md`:1953 现为"测试面 60→78（**59 保留**〔5 条 F-5 改名同步〕+ **19 新增**〔含 F-1 改写 1 条〕——**G-4 更正**）"；与本人 R0 重命名级清点（kept 59 / added 19 / 78）逐数字一致 |
| **G-5**（F-1 in-situ 未以测试形态入库） | P3 | ⏸ **未修复（不在本批指示范围）** | 新增 4 条测试均为重复入参用例，无 in-situ 注入用例 ⇒ 维持 P3 |
| **G-6**（F-7 注释普适性） | P3 | ➖ **未修复/不需动作（讨论项）** | 讨论级，无动作要求 |
| — | — | **本批无"未修复的 BLOCKING"、无"新引入 BLOCKING"** | 见 §五（本轮新发现全部 P3） |

**汇总：R0 的 P2×1 已闭环；P3 中 G-4 已由 Coordinator 更正；G-2/G-3/G-5/G-6 保持 R0 登记的 P3（本批未指示其处置）。**

---

## 三、5 个评审维度（聚焦增量）

| 维度 | 结论 | 增量相关依据 |
|---|---|---|
| **正确性** | 通过 | PRE/POST 实弹四点对照（§一 (1)）；no-dup 等价矩阵全 True（§一 (3)）；类型保持；`_reject_duplicate_check_ids` 返回入参（**返回原序列**使调用点可内联，未改变语义）；两侧守卫均在 `tuple(...)` 归一后进行（列表入参亦被覆盖） |
| **安全性** | 通过 | 不新增 I/O（新增代码为纯集合运算）；AST 模块体机判对 1029 行新版本仍 `offenses == []`（R0 机判同款，模块级语句未变：新增 helper 为函数定义）；不新增敏感面/注入面；`ValueError` 分支为 fail-closed（拒绝回答）方向 |
| **可维护性** | 通过（附 R1-N1） | **消重方向**：一份实现 + 一份文案（机判：定义 1 + 调用 1 + raise 站点 1）；docstring 逐点枚举覆盖面（可审计）；`context` 标签使报错自描述；函数短小（`_reject_duplicate_check_ids` 11 行代码体）。**唯** R1-N1：helper docstring **首句**的"每个取得 id 序列的公开入口"是普遍断言，比紧随其后的枚举更宽（见 §五） |
| **性能** | 通过 | `_duplicate_ids` O(n) 在 5 个覆盖点各执行一次，n ≤ 70；`reconcile`/`guard` 未新增 I/O；import 期无变化（R6 Δ0，ratchet 复跑）——无 O(n²)、无循环内 I/O |
| **测试覆盖** | 通过（附 R1-N2） | 82 passed（机证）；78→82 清点 `+4/−0`（无改名/删除）；4 条新用例**逐路径钉 context 标签**（强于只断言异常型）；覆盖率 198 stmts/1 miss=99%（miss = L739 导入期守卫，由 R0 的 L720 位移 +19 行，与新增 helper 的插入位置一致）；**限制** R1-N2（未钉文案 token） |

---

## 四、AI 专项 5 项（增量）

| 项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | 无 | 增量两文件机判 `unittest.mock|MagicMock|patch(` = 0；4 条新测试用真实注册表快照数据（`_snapshot_ids()`） |
| 硬编码返回值 | 无欺骗性硬编码 | 新测试期望 = `assertRaisesRegex(...)` 对**真实行为**的断言（PRE-FIX 反事实已证其可失败）；无"抄实现输出为期望值" |
| 幻觉 API | 无 | 增量仅用 `frozenset`/`tuple`/`set`/`assertRaisesRegex`；`_reject_duplicate_check_ids` 无新 import |
| 未实现 TODO | 无 | 增量零 `TODO/FIXME/NotImplementedError/type: ignore` |
| 过度实现 | **无（但需裁决，已裁决为接受）** | 家族补齐全 §一 (2)：同一不变量的同族闭合，非新功能；未新增异常型/reason code/四态词汇/schema/CLI；已完整披露 + 可逆 |

---

## 五、门禁声称 vs 独立核实

| # | 声称 | 核查结果 | 依据 |
|---|---|---|---|
| 1 | 82 passed | ✅ **独立复现** | `pytest -B -p no:cacheprovider` → `82 passed in 0.43s`；清点 78→82（+4/−0） |
| 2 | 覆盖率 198 stmts / 1 miss = 99%（miss L739 位移守卫） | ✅ **独立复现** | `--cov=quickscan_registry` → `Stmts 198 / Miss 1 / 99% / Missing = 739`；实测 L738-739 = `if len(_BY_ID) != len(_IDS): raise ValueError("quickscan registry declares duplicate CheckID rows")` ⇒ "位移守卫"属实（R0 记 L720，因新 helper 19 行插入而上移 19 行，位移量与插入位置自洽） |
| 3 | ratchet PASS | ✅ **复跑通过**（含污染披露） | `R1 PASS 24329≤24329`／`R2 PASS 46≤46`／`R3 PASS`／`R4 PASS 1310≤1310`／`R5 PASS cli 82/82 + segments 70/70`／`R6 INFO 196 Δ0`／`R7 PASS deterministic; committed==fresh` → `Result: PASS (0 violations)`, exit 0。**披露**：`archguard_ratchet.py` + `architecture-baseline.json` 仍为 FIX-303 在飞 ⇒ 结果为混合树；**静态论证该门禁不消费本批**（零 `import quickscan_registry/registry`；R5 走 FEAT-020 extractors + 冻结快照；R1 只计 `verify_workflow.py` LOC） |
| 4 | 全量 2584 = 2580 + 4，F/E/S 恒等 | ⚠ **采信（未复跑）+ 算术独立证实** | **"−4 增量"部分已独立证实**：目标测试文件 78→82（`added=4 / removed=0 / kept=78`）；"2580+4=2584" 算术成立。未复跑原因：工作树现有 **6 个 `M`**（FIX-303 四文件 + `registry.py`/`test_registry.py` 并发扩面），全量结果**当前不可归属本批**。替代证据（结构性）：全仓消费面仅 `registry.py` + 两测试文件，且两测试文件均绿（82 + 77，见下） |
| 5 | 消费者 71 OK（改名/守卫零影响） | ⚠ **口径漂移（不属本批）＋结构面零影响已证实** | 当前树 `pytest test_registry.py` = **77 passed / 21.15s**（**非 71**）——因 `registry.py`(+77/−7) 与 `test_registry.py`(+131/−2) 正被**并发任务扩面**（R0 时二者为 commit `36f2040` 状态：71 例，本人 R0 已核实 71 passed）。**结构面核实（决定性）**：消费者两文件对本次改动涉及的全部符号——`fallback_mode`/`fallback_target`/`CompletenessReport`/`guard_completeness`/`_reject_duplicate*`/`_duplicate_ids`/`reconcile_snapshot`/`discover_engine_segment_ids`——**机判 0 命中**；仅使用 `_segments.registry_ids()`（registry.py:622）、`_segments.segment(...)`（:632）、`qr.registry_ids()`/`qr.segment()`/`qr.SEGMENT_SPEC_FIELDS` ⇒ **本增量对消费者结构性零影响**，且该结论与树内并发改动无关 |

---

## 六、R1 发现汇总（全部非阻塞）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据 | 建议 |
|---|------|------------------|------------|----------|------|
| **R1-N1** | P3 | 模块 `quickscan_registry.py`:713-715（helper docstring 首句） | **措辞比实现宽**（新文本）：首句称"**每个取得 id 序列的公开入口**见重复即拒绝回答"，但紧随其后的枚举（同 docstring）只列 5 个覆盖点；实测仍有 2 个**公开** id-序列产出口未落检：① `load_frozen_snapshot_ids()`——count==len 但含重复时直接返回 `('1','1','2')`（其兄弟校验是 count-vs-len，非唯一性）；② `discover_product_gate_ids()`——重复条目返回 `('7','7')`。**影响评估**：①的推举消费路径 `reconcile_snapshot` **已守 expected 侧**（实测 `reconcile_snapshot(snapshot_path=dup-file)` → `ValueError`），仅**直接调用**该 loader 的外部消费方（如 Slice-2）会看到含重复的 tuple；②的模块内消费方 `plugin_face_not_product_gated()` 走 `set()`，`len()` 失真不进入任何裁决，且 live 25 唯一由测试钉住。⇒ 无当前位置的裁决失真，属**措辞/对称性**问题（与 R0 F-2、G-1 同族：绝对措辞超出实现）。 | ① 实测 `load_frozen_snapshot_ids(count=3, ids=["1","1","2"])` → `('1','1','2')`；② 实测 `discover_product_gate_ids(dup-fixture)` → `('7','7')`；③ 对照实测 `reconcile(snapshot_path=dup)` → `ValueError`（消费侧已守）；④ docstring 枚举 5 点经逐点核对**准确**（discovery / guard observed / guard declared / reconcile actual / reconcile expected） | 二选一（≤2 行）：**(a) 收窄首句**为"下列 5 个公开入口…"（与枚举一致，最省）；**(b) 对称落检**——让两处 `return` 前各过 `_reject_duplicate_check_ids(...)`（`load_frozen_snapshot_ids` 的 context 可用 `f"{path}"`，product-gate 用 `str(path)`），使普遍断言成真。**非阻塞**（当前无裁决失真；方向 fail-safe） |
| **R1-N2** | P3 | 测试 `test_quickscan_registry.py`:721/727/738/744 | 4 条新负对照只断言 **context 标签**（`observed_ids`/`actual_ids`/`declared_ids`/`snapshot_ids`），**未断言文案的 `duplicate` 与 `§4.1 R5` 锚**（仅旧测试 :702 断言 `duplicate`）⇒ 未来若文案退化（丢 R5 锚/丢 duplicate 词），测试不会失败，而该锚是"零容忍策略出处"的可追溯证据。 | ① 4 条新测试的 `assertRaisesRegex` 模式逐条核验（仅 context token）；② 实现文案含双 token（实测 5/5 覆盖点）；③ `:702` 旧测试断言 `duplicate` | 一行增强，例如把模式改为 `r"observed_ids.*duplicate CheckID\(s\).*§4\.1 R5"`（`assertRaisesRegex` 用 `re.search`，无需全串匹配）。可选，不阻塞 |
| **R1-N3** | P3 | `.governance/evidence-log.md`（待写入的 R1 证据行）/ 本批交接描述 | **记录口径待澄清**：交接所述"去重实现单一化（…+发现路径改调用**净 −10 行**）"无法从 diff 复算——实测 discovery 委托 hunk `@@ -818,7 +837 @@` = **7 removed / 1 added（净 −6）**；模块整体 = **+50/−17（净 +33）**；两种量法均非 −10。若原意是"避免在 5 处内联重复逻辑的**推算节省**"（5×7 行内联 ≈ 35 行 vs 实际 19+5 = 24 行 ⇒ 约 −11），则该指标应改标为推算口径而非 diff 口径。**不影响**"单一实现"结论（该结论已由机判独立证实：定义 1 次 + 调用 1 次 + raise 站点 1 处）。 | ① `git diff -U0` 逐 hunk 计数（5 个 hunk：+19 / 7−1 / +12 / +2 / +6）；② `--numstat` = 50/17（+33 净）与行数 996→1029 自洽 | 在 R1 证据行按 diff 口径记录（"+50/−17；discovery 委托 hunk 净 −6；去重收益为推算口径 ≈ −11 行"），避免后续复审复算不一致（与 R0 G-4 同族；G-4 已由 Coordinator 更正，本案宜同步口径） |

**本轮新增：P0 = 0；P1 = 0；P2 = 0；P3 = 3（R1-N1~N3，全部非阻塞）。**
**前轮残余（保持登记）**：P3×4（G-2/G-3/G-5/G-6，均不在本批指示范围）。

---

## 七、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| 新冻结锚核对（漂移即中止） | ✅ `1381d815…` / `4c75858e…` 一致（审查开始 + 落盘前各一次）；行数 1029/938 与 +50/−17、+35/−0 自洽；R0 blob 仍可解析（基线未丢） |
| 逐行读增量 diff（+85/−17 全量） | ✅ 模块 5 个 hunk（`-U10` 通读 + `-U0` 逐 hunk 计数）+ 测试 1 个 hunk（4 条新用例 + 插入点上下文）全量通读，非抽样 |
| 5 维度逐一结论 | ✅ §三 |
| 前轮 findings 逐条"已修复/未修复/新引入"标注 | ✅ §二（G-1 已修复 / G-4 已修复（Coordinator）/ G-2·G-3·G-5 未修复（不在指示范围）/ G-6 讨论项 / 本轮无新引入 BLOCKING） |
| 每条发现级别 + file:line + 事实依据 | ✅ R1-N1~N3 |
| AI 专项 5 项 | ✅ §四（含"过度实现"裁决 = 接受） |
| 复审要点 5 条逐条裁决 | ✅ §一（修复有效性 / 家族补齐=接受 / 去重单一实现+无回归 / 文案等价 / 测试有牙） |
| 结论（含 `unresolved_blockers` 独立行） | ✅ §八 |

---

## 八、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：R0 唯一 P2（**G-1**）已被**完整闭环**——以 R0 冻结 blob 在内存中实弹重建 PRE-FIX 后对照，四条公开入参路径（`observed_ids`/`declared_ids`/`actual_ids`/`snapshot_ids`）在修复**前**全部呈现静默 `ok=True` + `len()` 失真（`declared=71`/`expected=71`/`observed=71`/`actual=71`、`warnings=0`），修复**后**全部抛 `ValueError`，且**逐一**携带 `duplicate` 与 `§4.1 R5` 锚及可辨识的 context 标签；no-dup 路径的 `guard`/`reconcile` 输出（含 `lines()`、`expected`/`actual`、`registry_ids`/`quick`/`excluded`/`census`/`product-gate`/披露函数）与 PRE-FIX **逐项等价**，既有 fixture 负对照链路（新段 41 → fail-closed；重复段 29 → 抛错）保持，零回归；去重达成"单一实现 + 单一文案"（机判：定义 1 / 调用 1 / raise 站点 1，旧 inline 文案 0 命中）；文案变更保留两个机器可判 token 且无消费方依赖旧文案 ⇒ 语义等价。**家族补齐裁决 = 接受**：被额外守护的 `declared_ids`/`snapshot_ids` 经 PRE-FIX 实弹证实与 G-1 两条路径**同构同病**（非投机镀金），只守 2/4 会留下相邻公开入参的同一病理；披露完整（docstring 逐点枚举 + 测试自述 "Family completion"）、成本极小（+33 行净增、不新增异常型/reason code/四态词汇/schema/CLI）、可逆 ⇒ 属同一不变量的最小闭合形式，**不要求回退**。增量测试有牙（RED 反事实成立：两条 G-1 用例在 PRE-FIX 必以 `ValueError not raised` 失败；GREEN 82 passed 机证可复跑）；门禁 3 条独立复现（82 passed / 198·1·99%·L739 / ratchet PASS·exit 0）、1 条采信并算术证实（2584 = 2580+4，`+4/−0` 清点独立复核）、1 条口径漂移已辨明并不属本批（消费者实测 77 passed 系并发扩面，结构面对本批改动符号**零引用**⇒ 零影响）。**P0 = 0 且无任何未修复的 BLOCKING finding** ⇒ 满足 code-review SKILL「循环角色」段的通过终态契约，以 `APPROVED_WITH_NOTES` 结项（3 条 P3 备注 + 4 条前轮残余 P3）。

**发现计数（独立行，供机器记录）**：本轮新增 P0 = 0；P1 = 0；P2 = 0；P3 = 3。前轮残余 P3 = 4（G-2/G-3/G-5/G-6）。

**机器记录口径提示**：`unresolved_blockers=0` 独占一行且无附着细目（沿用 FEAT-025 R0 与 FIX-304 R0 先例，避让 provably-zero 探针）；计数写在独立行。

**复审链状态**：R0（`REVIEW-FIX-304-R0`，evidence-log:1957）→ R1（本报告）→ **终态通过**（无 NEEDS_CHANGE，无需 round 2；不触及 M7.4 熔断）。建议 Coordinator 以 `review-record` 机录本轮结论（不得手写 REVIEW 行），并在 R1 证据行按 §五 R1-N3 的 diff 口径记录行数。

**非阻塞处置建议（给 Coordinator）**：
- **R1-N1（P3）**：helper docstring 首句的普遍断言 → 或收窄措辞（1 行），或让 `load_frozen_snapshot_ids`/`discover_product_gate_ids` 对称落检（各 1 行）。与 G-2/G-3 同批顺带处理即可（三者合计 ≤10 行 + 2 测试）。
- **R1-N2（P3）**：4 条新测试的 `assertRaisesRegex` 模式加 `duplicate CheckID\(s\).*§4\.1 R5`，把"零容忍策略出处"纳入机判。
- **R1-N3（P3）**：R1 证据行按 diff 口径填写（+50/−17；discovery 委托 hunk 净 −6；去重为推算收益 ≈ −11 行），避免与后续复审复算不一致。
- 前轮残余 G-2/G-3/G-5（P3）与 G-6（讨论）：维持 R0 登记，无新窗口要求。

---

## 九、审查边界与残余未核验面（如实声明）

- **只读边界**：未修改任何产品代码或 `.governance/`；除本报告外未写入任何仓库文件；被审两文件 blob 在审查前后复算一致（未漂移）。仓外写操作仅 `%TEMP%\cov_fix304_r1.dat`（coverage 数据文件，`COVERAGE_FILE` 显式重定向）+ 测试自身 `TemporaryDirectory()`。
- **PRE-FIX 对照的实现方式（方法披露）**：以 `git show 4c34b001…` 取 R0 blob 源码，`compile`/`exec` 进内存模块（注册入 `sys.modules` 以支持 `dataclass`）后调用其函数——**未落盘、未改动任何工作树文件**，故 PRE/POST 对照为同一进程内实弹，非推测。
- **⚠ 采信项**：全量回归（声称 2584 / F/E/S 恒等）**未复跑**——工作树含 6 个 `M`（FIX-303 四文件 + 本次两文件 + 并发 `registry.py`/`test_registry.py`），全量结果不可归属；替代证据 = `+4` 清点独立复核 + 消费面结构性论证（全仓仅 3 处消费者，两测试文件均绿）。
- **⚠ 污染披露**：`archguard-ratchet` 复跑为混合树结果（FIX-303 在飞 ratchet 实现 + 基线）；已附"该门禁不消费本批文件"的静态论证。
- **❓ 未核验面（不写成事实）**：① `load_frozen_snapshot_ids`/`discover_product_gate_ids` 的**外部**（仓外/Slice-2）消费方是否存在直接调用（R1-N1 的影响面；当前仓内无此类调用）；② lint（ruff/mypy）仍未运行，**lint 面属未验证**；③ 并发任务对 `registry.py`/`test_registry.py` 的改动内容不在本审查面，未做审查（仅记录其导致消费者用例数 71→77 的口径漂移）。

*审查边界声明：本报告全部结论指向可复查事实（git 命令输出、两文件行号、PRE/POST 内存实弹输出、pytest/coverage/ratchet 实跑输出）。采信与未核验项已在 §五、§九显式标注；无结论来自推测。*
