# Code Review: FEAT-025-R0 — quick-scan Slice-1 检查段事实源注册表

- **Task**: FEAT-025（R0；FX-195 承接，`quickscan-evaluation-0.79.0.md` §6 Slice-1 / §250 验收要点 ①②③）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: R0（首次审查；无前轮报告。前一会话中断且零产出，本轮为干净重启）
- **审查对象**: commit `504cc8f`（`git show 504cc8f --numstat` = 2 files changed, **935 + 588 = 1523 insertions(+), 0 deletions**，两文件均新增）
  - `skills/software-project-governance/infra/quickscan_registry.py`（935 行 / 181 stmts）
  - `skills/software-project-governance/infra/tests/test_quickscan_registry.py`（588 行 / 60 tests）
  - 审查对象**字节级冻结**核验：`git hash-object` 两文件 = `c0f23bbc…` / `651edc0f…`，与 `git rev-parse 504cc8f:<path>` 逐字节相同（工作树 = 被审 commit 内容）。
- **设计基准**（逐项比对用）: `docs/requirements/quickscan-evaluation-0.79.0.md` §3.1（L134-136，C1/C2/C3 分类与判据）、§3.3（L144-151 full 兜底）、§2.4（L101-122 四态契约）、§6 Slice-1 行（**L250**，验收 ①②③）、§255（L255「Slice 载体禁写入巨石编排体」）、§4.3（L178-183 回退）；`docs/requirements/architecture-evolution-0.80.0.md` §3.6（**L214-222** `CheckSpec` 字段集）、§4.1 R5（L260「Check ID 唯一」）
- **审查方法**: 逐行读两新增文件**全文**（935 + 588 = 1523 行，非抽样）；再以仓内事实逐条交叉核对——引擎 `verify_workflow.py`（24,329 行）与 `checks/review_domain.py` 的目标符号/字面量/行号、`infra/contract_matrix/snapshots.json` 冻结面、`core/architecture-baseline.json` 棘轮锚、`.governance/evidence-log.md` EVD-995
- **审查边界（诚实声明）**: 本轮的交叉核对**需要执行只读命令**（任务书明确要求核对"排除集 vs 引擎实际常量""70 段解析 vs 引擎源码""C3 依据 vs input_deps"，并点名 `git show`）。因此本轮与 FEAT-021 R0 的"零命令"口径不同——我执行了**只读**核验命令（`git show/numstat/hash-object`、`python -B` 内省、`pytest`、`coverage`、`archguard-ratchet`），**未修改任何产品代码、未写入任何仓库文件**；覆盖率运行产生的 1 个仓内副本 `.coverage_reg`（我创建、28 秒龄）已即时删除，工作树已还原（`.gitignore` 未忽略 coverage 产物，故该风险点如实登记）。**未复跑 596.2s 全量回归**（见 §3.2 第 9 条与 §七遗留）。核查等级逐条标注：✅独立核实 / ⚠采信（给出静态论证）/ ❓无法核验。
- **环境披露**: 审查期间工作树内有**并发会话**产生的未跟踪文件（`infra/registry.py`、`infra/tests/test_registry.py`、`.it_assemble.txt`、`.it_registry.txt`），均不属本审查对象；被审两文件与 `504cc8f` blob 逐字节一致（见上），故不影响结论。

---

## 一、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P1×1 / P2×1 / P3×4）

**1.1 表本体与冻结面逐项核实（验收①的正面结论）。**
- 70 行逐段一行，`SEGMENTS`（quickscan_registry.py:228-610）id 序列与 FEAT-020 冻结快照**集合与顺序双双恒等**（独立复算：`tuple(registry_ids()) == snapshots.json faces.check_segments.ids` → True）；`reconcile_snapshot()` 实测 `registry=70 snapshot=70 missing=[] extra=[] ok=True`。
- 段清单解析走 `_run_full_engine_checks` 函数体段落注释（:756 `_SEGMENT_SECTION_RE` + :761-784），实测返回 **70** 段且集合与快照恒等 ⇒ 与 commit message 所称"banner 只打 69 段、30b 无 banner → 改用段落注释"的自洽性成立；全文件同款段落注释实测 75 处 > 函数体内 70 处，故"函数体内作用域是承重的"（test_quickscan_registry.py:145-153 的断言为真，非装饰）。
- **排除集三路交叉核实全部成立**：① 注册表 `excluded_ids()` 实测 25 段；② 与引擎源码文本解析（`discover_product_gate_ids()`）集合恒等；③ 与**实际 import 的** `verify_workflow._PLUGIN_PRODUCT_CHECK_IDS` 集合恒等；④ 与评估文档 §3.1 C1 行（L134）逐 id 相同（测试 :332-334 钉住）。`quick_face_ids()` 实测 45 段 = §3.1 C2 行（机器解析 41 段）+ C3 四段，并集/交集断言成立（:342-349）。
- 派生列与声明分布实测一致：`fact_source_root` = host 33 / plugin 27 / mixed 10；排除原因码 = `PLUGIN_PACKAGE_ASSET`×17 / `PLUGIN_TREE_SCAN`×5 / `PLUGIN_GIT_FACT_SOURCE`×2 / `PLUGIN_CLAIM_ATTESTATION`×1（合计 25）；`plugin_face_not_product_gated()` = `('18h','28','28j','28l')`；`dual_root_disclosures()` = `('24','31')` —— **与 commit message / EVD-995 的每一项声称逐字符吻合**。
- **正确性设计选择得当（非发现）**：`fact_source_root` 与 `exclusion_reason_code` 不落表、而是 `input_deps`/`modes` 的纯函数派生（:187-203），既满足 §6"事实源根 + 排除原因代码"的逐行可见性，又让行 schema 保持 `CheckSpec` 子集（否则两个派生列会破坏验收③）——"无第二份真相"的主张与实现一致。

**1.2 表内容的事实性独立佐证（部分核实，范围显式）。**
- 我对 70 行做了**机械扫描**：把每行的非 git 依赖 target 去掉 glob 后，在引擎与 `checks/*.py` 源码中做字面量检索 → **66/70 行的声明至少有一个 target 在引擎源码中逐字出现**；其余 4 行（7 / 15 / 25 / 28o）为 **git 命令或树根声明，本身不含路径字面量**（7/15 仅 `plugin:git:…`、25 仅 `host:git:ls-files…`、28o 仅 `plugin:tree:.`），属结构性无字面量，非缺证据。抽样确认 :18h 的 `core/templates/deterministic-scaffolds`、:30 的五条路径、:28s 的四条宿主热文件等均在引擎中真实出现。
- **残余限制（❓）**：模块 docstring:44-49 声称事实源根用"对真实引擎做一次性插桩运行（拦截 banner）产出 70 段实际读取路径清单"，该插桩**留痕未随交付入库**，我无法复现该实验；故 `input_deps` 的**逐行完备性**（是否有遗漏的输入依赖）属未核验面，仅"已声明项非臆造"与"C3 四段依据可核"两点被独立证实（§3.2）。

**1.3 发现（正确性）**：
- **F-1（P1）** 模块级 I/O 机判的扫描面被截断，"表声明纯声明"的断言未覆盖表本体（详见 §四）。
- **F-2（P2）** product-gate 解析为文本/正则且结果无 fail-closed 校验；证据记录却记为"AST 源码解析"（详见 §四）。
- **F-4（P3）** `not-quick:<CODE>` 属 §3.6 `modes` 示例文法之外的新 token 家族。
- **F-5（P3）** `CompletenessReport.fallback_mode` 恒为 `"full"`，字段名与语义（回退**目标**）易被误读。
- **F-8（P3）** `discover_engine_segment_ids()` 返回引擎**源码序**，与快照/注册表位序不同（两套顺序并存）。
- **F-9（P3）** 证据记录行数 929 与实际 935 不符。

### 维度 2：安全性 — 通过（无发现）

- **零写操作 / 零提权面**：`quickscan_registry.py` 全文件无 `write_text`/`open(`/`eval(`/`exec(`/`subprocess`/`os.system`/`shell=True`/网络调用/`time.sleep`/`random`（机判：这些模式在两文件内的命中**全部落在测试文件**，且测试的 `write_text` 只写 `tempfile.TemporaryDirectory()` 内路径——已逐处核实 :63-84/:522-540）⇒ 数据安全 P7（不损坏用户数据）无暴露面。
- **import 期零副作用**：模块级语句 = 常量/`SegmentSpec` 类/`SEGMENTS` 表/`_BY_ID=_index()`/一条重复 id 的 `raise`（:695-699），无 I/O、无 `__main__`、无 `print`（实测 print=0、`__main__`=False、`noqa`=0、`type: ignore`=0）⇒ 符合 R4 print 纪律与"纯声明模块"定位。
- **输入校验与 fail-closed**：未知排除原因码 `_excluded()` 抛 `KeyError`（:222-223）；未知段查询 `segment()` / `exclusion_reason_code()` 抛 `KeyError`（:710-712/:736）；快照加载校验 `count == len(ids)`（:804-805）；引擎缺入口/缺锚点抛 `ValueError`（:776-777/:792-793）——四处失败面均有负对照测试（:499-503/:509-511/:522-540）。
- **注入与 ReDoS 面**：三条自产 pattern（:756/:757/:758）均为固定形态、无嵌套量词、作用于仓内文件文本；无用户可控字符串拼接进正则或命令。
- **编码纪律**：所有读取路径显式 `encoding="utf-8"`（:770/:790/:801），符合 FIX-278 G4/F UTF-8 纪律；测试写 fixture 亦显式 UTF-8。
- **无敏感数据**：全文件零密钥/token/凭据；无权限或越权面（纯只读数据模块）。

### 维度 3：可维护性 — 通过（含 P2×1 / P3×3）

- **命名与文档**：`_derive_*`/`discover_*`/`guard_*`/`reconcile_*`/`dual_root_disclosures` 表意清晰；模块 docstring 分节（设计事实源清单 → 行 schema → 派生列 → 证据方法 → 已知披露 4 条），且**每条披露都带事实源与代码锚点**（:51-72）——本仓"事实依据"文化的正向范例。
- **职责单一 / 函数长度**：935 行中约 395 行是 70 行的数据表；函数全部短小（最长 `guard_completeness` ≈35 行，`discover_engine_segment_ids` 24 行），无超 50 行函数；无重复逻辑（`_excluded()` 统一了排除行构造，:220-224）。
- **纪律边界清晰**：模块 docstring:5-6 显式禁止在本切片登记 CLI/argparse（Slice-2 职责），并有测试机判（:451-461，且该测试正确地把 docstring 排除在扫描面外——`split('"""',2)[-1]` 取代码体，docstring 里"为禁而提及 argparse"不误报）。
- **可维护性风险**：F-1（假绿的机判）、F-6（`SEGMENTS` 未入 `__all__`）、F-7（`+5` 魔数）。
- **已核实可接受的设计固有约束（非发现）**：`SegmentSpec` 字段注解为裸 `tuple`（:184-185）而非 §3.6 的 `tuple[str, ...]`，因 `from __future__ import annotations`（:75）下仅作形态声明、无运行时影响；`excluded_from_quick` 属性与 `MODE_QUICK not in self.modes` 的两处表达（:194/:740/:744）语义一致，不构成漂移。

### 维度 4：性能 — 通过（无发现）

- **import 成本实测 11.6 ms**（`python -B`，含 70 行表构造与索引构建），仅 stdlib 依赖（`json`/`re`/`dataclasses`/`pathlib`）；且**引擎零引用本模块**（§二）⇒ 对 R6 启动预算贡献为 0（独立复跑 `archguard-ratchet` 的 R6 实测冷导入 196 模块、Δ0）。
- **运行时成本实测**：`guard_completeness()`（读整份 24,329 行引擎 + 正则 + 集合差）= **8.2 ms**；`plugin_face_not_product_gated()` + `dual_root_disclosures()` 合计 **7.7 ms**。相对 FX-195 §4.2 的 47s 全量基线与"每会话一次"消费节律（evaluation L68-70），成本可忽略——**不改变 §4.2 的量级估算**。
- **数据结构与复杂度**：`_BY_ID` dict 为 O(1) 查询（:691-695）；差集/交集均 O(n)（n ≤ 70）；`_derive_fact_source_root` 为 O(deps) 集合构造；无 O(n²) 以上算法、无循环内 I/O（一次 `read_text` 后在内存正则）。
- **懒加载**：引擎文本与快照 JSON 只在函数调用时读取（:748-753 仅造路径，:770/:790/:801 才读），import 期零文件访问 ⇒ 符合"import 期不做事"预算方向。

### 维度 5：测试覆盖 — 通过（含 P1×1 / P3×2）

- **清点与复跑**：`def test_` 逐类清点 = Acceptance1 7 + Acceptance2 6 + Acceptance3 5 + Acceptance4 5 + Acceptance5 7 + QuickFacePolicy 9 + DiscoveryDisclosure 3 + CarrierDiscipline 5 + DesignTraceability 3 + FailClosedBranch 6 + FixtureDrivenGuard 4 = **60**，与声称一致；**独立复跑 60 passed**（pytest 9.0.3 / Python 3.14.3，0.25s）。
- **覆盖率独立复跑逐数字吻合**：181 stmts / 1 miss / 99%，`Missing = 699` —— 与 EVD-995 声称的"181 stmts/1 miss=99%（miss=L699 导入期不变式守卫）"完全一致，且 L699 确为 `raise ValueError("quickscan registry declares duplicate CheckID rows")`（导入期重复 id 守卫，:698-699）⇒ 缺席属**不可达守卫**而非业务分支，如实披露得当。
- **五类覆盖齐备**：合法路径（表遍历断言 :221-227/:245-253）、非法路径（负对照 :499-503/:509-540）、边界（空 deps→unknown :518-520；排除行无原因 token→None :513-516）、不可变（frozen :236-239）、**交叉核对（真读仓内文件，非空断言）**：真读 `snapshots.json`（:103-143）、真读架构文档 §3.6 提取 `CheckSpec` 字段并与 `CHECKSPEC_FIELDS` 逐项相等（:211-219）、真读评估文档 C3 行（:493-497）、真读引擎源码做 product-gate 双路比对（:329-340）。
- **负对照有牙**（本仓"守卫必须能被负对照打穿"的标准）：合成引擎新增段 41 → `undeclared=('41',)`/`fail_closed=True`/`fallback_mode='full'`/告警含 `UNDECLARED_SEGMENT`（:167-182/:546-556）；stale 段 20 → 仅告警不熔断（:184-191）；删表一行（29）→ 仍 fail-closed（:193-198）；缺锚点/缺入口/count 不匹配 → 各抛错（:522-540）。
- **覆盖缺口**：F-1（`test_registry_declares_no_module_level_file_io` 的扫描面截断，未覆盖它声称保护的模块级语句）；F-10（C3 依据机判只做 target 子串包含，无法发现 basis 中被引函数名写错）；F-3（重复段号无负对照）。
- **测试卫生（正面）**：零 `unittest.mock`/`MagicMock`/`patch`（负对照全用真实 tempfile 引擎样本文本，强于打桩）；测试写操作只落 tempdir；`sys.path.insert` 与同目录 46/50 个既有测试文件的仓内约定一致（无 conftest.py，属既有模式而非本切片新引入）。

---

## 二、设计一致性逐项比对（§6 Slice-1 L250 ①②③ / §3.1 / §255 / §4.3 / evolution §3.6）

| 设计条目 | 实现位置 | 判定 |
|---|---|---|
| §250 ① 70/70 覆盖（对 FEAT-020 ids 机判） | :228-610 表 + :864-872 `reconcile_snapshot` + :103-128 测试 | ✅ 一致（集合**与顺序**双向恒等，独立复算） |
| §250 ② 完整性守卫：新段未入表 → 告警 + fail-closed 回退 full | :875-909 `guard_completeness` + :156-201/:543-576 测试 | ✅ 一致（含 fixture 端到端负对照） |
| §250 ③ 表 schema ⊂ `CheckSpec` 字段集 | :168-175 `CHECKSPEC_FIELDS` 从 §3.6 文档**机器解析**并断言相等 + :178-215 行 schema + :204-234 测试 | ✅ 一致（见下方口径注） |
| §3.6 `CheckSpec` 字段（check_id/domain/loader/input_deps/severity_floor/modes，L214-222） | `SEGMENT_SPEC_FIELDS` = {check_id, domain, input_deps, modes} ⊂ 6 字段集 | ✅ 子集成立（缺 `loader`/`severity_floor` 属 Slice-1 范围内取舍，§6 行未要求） |
| §3.6 `modes: tuple[str, ...]  # ("full","quick","domain:<name>")`（L221） | :33-35/:224 `("full","quick")` / `("full","not-quick:<CODE>")` | ⚠ 取值词汇为**扩展**（F-4）；字段名与容器类型一致 |
| §3.1 C1 25 段（L134，含"代码验证 L14669-L14698"） | :144-157 原因码表 + 25 行 `_excluded(...)` | ✅ 逐 id 恒等（三路交叉核实，§一 1.1） |
| §3.1 C2 41 段 / C3 4 段默认保留 quick（L136 fail-safe） | `_RETAIN` 45 行 + `C3_ADJUDICATION`（:612-682） | ✅ 一致（quick 45 = C2∪C3，机判成立） |
| §3.1 判据="事实源根 = 插件包本体" vs 排除集"≡ FIX-270" | 排除政策取 FIX-270（:22-24/:70-72 docstring），4 条插件面未 gated 段经 `plugin_face_not_product_gated()` 披露 | ✅ 与 §3.1 的**双重表述**自洽（§3.1 的 25 段清单本身即 FIX-270 清单）；披露义务已履行（非静默） |
| §255 载体禁写入巨石编排体 | 零引擎改动（numstat 仅 2 新增文件）+ 引擎源码 `quickscan` 命中 0 + :439-442 机判 | ✅ 一致（且强于"仅接线"——本切片连接线都不需要） |
| §4.3 回退项 3（删模块即回现状） | 无引擎接线 ⇒ 删除本模块即完全回退；R1 棘轮不受冲击（锚 24,329 = 引擎实际 24,329） | ✅ 一致 |
| §2.4 四态契约（Slice-1 只声明） | `MODE_FULL_FALLBACK`（:126-127）、`REASON_UNDECLARED_SEGMENT`/`REASON_UNKNOWN_INPUT`（:160-165）**只声明不实现**，编排属 Slice-2 | ✅ 范围一致（无越界实现，见 §3.1"过度实现"） |
| §4.1 R5「Check ID 唯一」（evolution L260） | 注册表侧有导入期机判（:698-699）；**观察侧（引擎 census）无唯一性校验** | ⚠ 半覆盖（F-3） |
| §7.2 QR-5（quick 排除面与 FIX-270 product-gate 正交） | 排除集 ≡ `_PLUGIN_PRODUCT_CHECK_IDS`（双路机判） | ✅ 一致（正交性有机器证据） |
| §7.2 QR-1（注册表漂移：新段未入表 → 静默漏检） | 守卫 fail-closed + 告警（`UNDECLARED_SEGMENT`） | ✅ 一致（唯一缺口 = 重复段号，F-3） |

**口径注（验收③的读法）**：§250 ③ 原文写作"表 schema ⊂ CheckSpec.**input_deps**字段集"。按字面（⊂ 单字段 `input_deps`）读则本表必不合格（表含 `check_id`/`domain`/`modes`），按设计意图（Phase-2 平移性声明）应读作"⊂ **CheckSpec 的字段集**"。实现取了后者，并把 §3.6 的字段清单**从文档正则解析后断言 `tuple(CHECKSPEC_FIELDS) == tuple(fields)`**（测试 :211-219），使该声明不可被静默改写。**本审查采纳后一读法并判 PASS**，同时建议 Coordinator 在 §250 的验收措辞上收紧为"⊂ CheckSpec 字段集"以免后续复审歧义。

**结论：§6 Slice-1 的三条验收要点全部落地，且每条都有机器可判的固定物**（要求 ①→快照恒等断言；②→fixture 端到端负对照；③→文档解析断言）。偏离面仅两处：`modes` 取值词汇扩展（F-4，Phase-2 需映射口径）与 R5 唯一性在观察侧半覆盖（F-3）。

---

## 三、AI 专项 5 项 + 声称 vs 代码事实交叉核对

### 3.1 AI 专项 5 项（逐项结论）

| 项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | **无** | 两文件零 `unittest.mock`/`MagicMock`/`patch`（机判命中 0）。负对照用的是**真实** tempfile 引擎样本文本与真实快照 fixture（test:63-84/:546-584），非打桩——强于常见做法 |
| 硬编码返回值 | **无欺骗性硬编码** | `discover_*`/`guard_*`/`reconcile_*` 全部返回**真实解析结果**（真读引擎与 snapshot）；文件内字面量仅三类：① 70 行事实源声明（本切片交付物本身）；② §3.6 派生的 `CHECKSPEC_FIELDS`（文档解析断言相等）；③ 原因码常量表（4+2 码，逐条带语义说明 :144-165）。测试侧硬编码清单（`EVAL_C1_EXCLUDED` :52-56、`EVAL_C3_SEGMENTS` :57）是**独立的第二事实源**（用于交叉核对实现，不是复制实现输出），属正当用法 |
| 幻觉 API | **无** | 全部符号真实且经执行验证：`dataclasses.dataclass/fields`（`fields as dataclass_fields` 为真实 API 别名 :79）、`re.compile/findall`、`Path.read_text/resolve/parent`、`json.loads`。**被审文件引用的引擎侧符号逐项核实存在**（见 §3.2 第 5 条）——无一处臆造 |
| 未实现 TODO | **无** | 两文件零 `TODO`/`FIXME`/`XXX`/`HACK`/`NotImplementedError`/`noqa`/`type: ignore`（机判命中 0）；`MODE_FULL_FALLBACK`/守卫回退码确为"Slice-1 只声明、Slice-2 消费"（:126-127 显式标明），属**经声明的范围边界**而非遗留桩 |
| 过度实现 | **无实质过度** | 本切片未实现编排器/`--quick` 旗标/四态输出/缓存（§255 要求的边界守住了）；CLI 面有负向机判（test:451-461）；`dual_root_disclosures`/`plugin_face_not_product_gated` 两个披露函数超出 §6 字面要求，但它们是**因果必要**的：排除集取 FIX-270 后出现了双根排除（24/31）与插件面未 gated（18h/28/28j/28l）两类反例，不披露即静默（QR-1/QR-2 同族病理）⇒ 属正当延伸，且均被测试消费（test:403-433） |

### 3.2 Developer 声称 vs 代码事实（逐条交叉核对）

| # | 声称 | 核查结果 | 依据 |
|---|---|---|---|
| 1 | 恰 2 个新文件，+1523 行 | ✅ **独立核实** | `git show 504cc8f --numstat` = 935 + 588 = 1523 insertions、0 deletions、均 A 状态 |
| 2 | `verify_workflow.py` 零修改、引擎零 `quickscan` 引用 | ✅ **独立核实** | numstat 无该文件；引擎全源 `quickscan` 命中 **0**；引擎物理行数 24,329 = `architecture-baseline.json` `r1_mainfile_budget.anchor_loc` = 24,329 ⇒ 声明"R1 24329 不变"成立 |
| 3 | `reconcile_snapshot()`：70/70、missing=[] extra=[] ok=True | ✅ **独立核实（复跑）** | 实跑输出 `registry=70 snapshot=70 missing=[] extra=[] ok=True`；另验 id **顺序**亦与快照相同 |
| 4 | 排除集 ≡ FIX-270（双路）、modes 45/25、根 33/27/10、原因码 2/17/5/1 | ✅ **独立核实（复跑）** | 四路交叉：注册表排除集 = 源码文本解析 = 实际 import 常量 = §3.1 C1 行；分布计数逐项吻合（§一 1.1） |
| 5 | C3 四段全保留 quick，依据可核、与 `input_deps` 互证 | ✅ **独立核实（逐符号对源码）** | 28g：`check_governance_context`(引擎 L8808)→`discover_governance_context`(L8718)、`_context_file`(L7728)、`_parse_plan_context_tasks`(L8425)、`_parse_snapshot_context_tasks`(L8498)、`_parse_evidence_context_tasks`(L8741)、`_parse_context_open_risks`(L8743)、`_run_context_git`(L8638)+`git status --short --untracked-files=all`(L8666-8667)、`_parse_recent_commit_context_facts`(L8694)+`git log --oneline -5`(L7743)、`discover_flow_unit_runtime_context`(L3875)+`FLOW_UNIT_RUNTIME_STATE_REL`(L2352)、插件面 `commands/governance.md`/`governance-status.md`(L429/L2613)——**全部属实**；28j：`_capability_cli_registration_fact`(L7784) 确用 `ast.parse`(L7789)、`_capability_host_id`(L7848)、`discover_capability_context`(L7864)；28l：`discover_host_capability_context`(L8126)/`check_host_capability_context`(L8294)；29：`check_m5_runtime_triggers`(`checks/review_domain.py`:1342)、`EVIDENCE_PATH = SAMPLE_PATH.parent/"evidence-log.md"`(L9462)、`SAMPLE_PATH = HOST_PROJECT_ROOT/".governance"/"plan-tracker.md"`(L7545)、"语料为空降级 no-verdict 不 FAIL"(review_domain:1349-1351)、FIX-178 显式排除 session-snapshot(L1353/L1389)——**全部属实** |
| 6 | 完整性守卫 fixture 负对照（合成段 41 → fail-closed/告警；stale 仅告警） | ✅ **独立核实（复跑）** | 测试复跑通过；我另用自造引擎样本复验该分支行为一致 |
| 7 | 覆盖率 181 stmts / 1 miss = 99%（miss=L699） | ✅ **独立核实（复跑）** | `pytest --cov=quickscan_registry --cov-report=term-missing` → `Stmts 181 / Miss 1 / 99% / Missing=699`，逐数字吻合；L699 = 导入期重复 id 守卫 |
| 8 | 60 测试全绿 | ✅ **独立核实（复跑）** | 60 passed（0.25s），11 类逐类清点 = 60 |
| 9 | 全量复跑 Ran 2481 / 32F+1E+1S，A/B 移出对照新增失败 = 0 | ⚠ **采信（未复跑 596.2s）＋静态论证** | 静态论证比复跑更强且不受并发会话污染：本 commit **零修改既有文件**（numstat 仅 2 个 A），仓库内**无任何产品代码引用 `quickscan_registry`**（全仓检索命中仅两个被审文件本身）⇒ 新增回归面在结构上 = 仅 pytest 收集 +60 例；两文件与 504cc8f blob 逐字节相同，故 EVD-995 的失败集分类（7 项非基线失败全存量）与 FEAT-021 R0 采信的 EVD-979/994 口径一致 |
| 10 | archguard-ratchet PASS（R1 24329/R2 46/R4 1310/R5 82 键+70 段/R7 deterministic） | ✅ **独立核实（复跑）** | 实跑 `archguard-ratchet`（默认只读，写盘仅在 `regen_baseline` 的 `--regen` 路径内）：`R1 PASS 24329≤24329` / `R2 PASS 46≤46` / `R3 PASS` / `R4 PASS 1310≤1310` / `R5 PASS cli keys 82/82 frozen, segments 70/70 frozen` / `R7 PASS deterministic=True; committed==fresh True`；`Result: PASS (0 violations)`，exit 0 |
| 11 | 披露三项：双根 24/31、插件面未 gated 18h/28/28j/28l、28o 只声明 `plugin:tree` | ✅ **独立核实（复跑）** | `dual_root_disclosures()` = `('24','31')`；`plugin_face_not_product_gated()` = `('18h','28','28j','28l')`；`fact_source_root('28o') == plugin` 且其 `input_deps == ('plugin:tree:.',)` |
| 12 | lint NOT_RUN（pyproject 口径，ruff/mypy 未安装） | ⚠ **采信（未验证安装状态）** | 本次审查未安装/未调用 lint；等价静态自检（无 noqa/type: ignore、纯 stdlib、执行通过）不否定该声明，但 lint 面仍属**未验证** |

**交叉核对小结**：12 条声称中 **9 条独立复现为真**（含全部关键数字）、2 条采信（全量回归、lint）、**1 条与代码事实不符**（见 F-2 的机制描述与 F-9 的行数），无一条声称被证伪为"未交付/未实现"。

---

## 四、发现汇总（P0~P3 + 位置 + 事实依据 + 建议）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据 | 修复建议 |
|---|------|------------------|------------|----------|----------|
| **F-1** | **P1** | `tests/test_quickscan_registry.py`:470-475 | `test_registry_declares_no_module_level_file_io` 声称"Importing the table alone must be pure declaration (no reads, no drift)"，但它用 `source.split("\ndef ", 1)[0]`（:473）截取源码，扫描面**止于 L219**，而真正的模块级语句在**其后**：`SEGMENTS` 表本体（:228-610，即"the table"）、`C3_ADJUDICATION`（:612-682）、`_BY_ID = _index()`（:695）、导入期重复 id 守卫（:698-699）。实测 `module_level` 覆盖 1..219 / 936 行，三处断言目标均不在扫描面内 ⇒ **假绿**：后续切片在表区或索引区引入模块级 I/O（`read_text(`/`open(`/`json.load(`）不会被该守卫拦住，而测试名与 docstring 会让人以为已受保护（与 QR-1"注册漂移静默"同族病理） | ① :473 截断表达式；② 实测边界"covers lines 1..219 of 936"、`"SEGMENTS = (" in cut == False`、`"duplicate CheckID" in cut == False`、`"_BY_ID = _index()" in cut == False`；③ 仓内已有正确先例：`tests/test_contracts.py` 的 `ZeroIoZeroDependencyTests` 以 **AST 模块体节点白名单**机判 | 改为 AST 机判：`tree = ast.parse(source)` 后对 `tree.body` 做节点白名单（`Import`/`Assign`/`ClassDef`/`FunctionDef`/`Expr(Str)` 之外即失败），或断言"所有 `ast.Call` 节点均不存在于模块级语句中"。**注意**：该测试不在六条验收标准的判定链上（验收⑤由 ①numstat 零引擎改动 ②引擎零 `quickscan` 引用 ③注册表不 import 引擎 ④无 CLI 面 四项独立证实），故本项不影响验收裁决，但属"守卫有洞"应在本轮或紧随补丁轮修 |
| **F-2** | P2 | `quickscan_registry.py`:787-795；对照 :798-806；`.governance/evidence-log.md`:1939（EVD-995） | ① **机制描述与实现不符**：EVD-995 与本轮任务书记载排除集"双路验证：**AST 源码解析** vs 实际 import 常量"，但实现是**文本解析**——`source.split(anchor,1)[1].split("})",1)[0]` + `re.findall(r'"Check ([A-Za-z0-9]+)"')`（:791-795），全程无 `ast`。② **解析结果无 fail-closed 校验**：只有"锚点缺失即抛 `ValueError`"（:792-793），若锚点在而条目形态变化（如条目改用单引号、`frozenset({...})` 改写成多行拼接），`findall` 返回 **`()`** 而非报错——对比同类兄弟 `load_frozen_snapshot_ids` 有 `count == len(ids)` 校验（:804-805），此函数缺少等价的结果校验。影响：证据记录对方法**鲁棒性的表述被高估**；解析退化时 `plugin_face_not_product_gated()` 会把 27 个插件面段全量误报为"未受 product-gate 管辖"（方向为**过度披露**，不损失覆盖，故非 P0/P1） | ① :787-795 实现（无 `ast`）；② :798-806 兄弟函数的 count 校验对比；③ EVD-995 原文"双路验证：AST 源码解析 vs 实际 import 常量"；④ 兜底存在但不完整：`test_engine_product_gate_parse_matches_the_live_constant`（:329-340）在与实际 import 比对时会因 25≠0 而 FAIL，但该兜底只在**测试进程**内生效，函数被单独调用时仍静默返回 `()` | 二选一：(a) 措辞更正为"源码**文本**解析"并保留现实现；(b) 若确需 AST 语义，改用 `ast.parse` + `ast.literal_eval` 取 frozenset。**无论哪条**，MUST 补一条结果非空/数量断言（如 `if not ids: raise ValueError(...)`），使解析退化 fail-closed 而非静默空集 |
| **F-3** | P2 | `quickscan_registry.py`:761-784（census）+ :886-887（集合差）；设计 `architecture-evolution-0.80.0.md` §4.1 R5（L260） | 观察侧（引擎段清单）**无唯一性机判**：`discover_engine_segment_ids` 用 `findall` 返回含重复项的 tuple、不去重不校验；`guard_completeness` 只做 `set(observed) - set(declared)` / 反向差（:886-887），**重复段号对守卫不可见**。已构造反例复现：在合成引擎正文中把 `# ── 29. ` 段落注释重复一次 → `len(observed)=71, unique=70, ok=True, undeclared=(), stale=(), fail_closed=False`。§4.1 R5 明文要求"Check ID 唯一"，注册表侧已机判（:698-699 导入期 `ValueError`），但**观察侧半覆盖**。影响：机器看护有洞（方向 fail-safe——不损失覆盖、不误排除），且 `len(observed)` 已被测试用作断言（:556 `assertEqual(len(report.observed), 71)`），长度被 71/70 混淆时会传递到消费面 | ① :784 `findall` 直接返回；② :886-887 集合差；③ 复现输出 `len(observed)=71 unique=70 ok=True fail_closed=False`；④ §4.1 R5 原文"Check ID 唯一…零容忍（fatal）"；⑤ 对比注册表侧 :698-699 的唯一性守卫 | 在 `discover_engine_segment_ids` 返回前加唯一性校验（重复 id 即 `ValueError`，与注册表侧 :698-699 同构），或让 `guard_completeness` 把"观察侧重复"并入 `undeclared` 语义（fail-closed）+ 补一条重复段号负对照 |
| **F-4** | P3 | `quickscan_registry.py`:33-35、:224；设计 `architecture-evolution-0.80.0.md` §3.6 L221 | 模式政策面 token `not-quick:<REASON_CODE>` 是 §3.6 示例文法 `modes: tuple[str, ...]  # ("full","quick","domain:<name>")` **之外的新 token 家族**；模块 docstring 自述"标签化 token **沿用** §3.6 modes 既有 `domain:<name>` 文法"——严格说只"沿用了形态约定"，词汇本身是扩展。字段名子集成立（验收③ PASS），但 commit message 的"Phase-2 平移**零语义分叉**"因此缺一条映射口径：Phase-2 的 `CheckSpec.modes` 要如何表达"排除 + 原因码"尚未定义 | ① :33-35/:224 token 构造；② §3.6 L221 示例仅列 `domain:<name>`；③ §9.3（evolution L458）只规定"选择机制 = …模式政策"，未定义 token 词汇 | 在 docstring 显式标注"`not-quick:<CODE>` 为 Slice-1 引入的扩展词汇，Phase-2 平移口径 = `<见 REFACTOR-light-registry / quickscan-orchestration 的定义>`"，避免后续把该 token 读作 §3.6 既定词汇 |
| **F-5** | P3 | `quickscan_registry.py`:126-127、:851、:908；测试 :165/:190/:552 | `CompletenessReport.fallback_mode` **恒为 `"full"`**（:908 无条件赋值），与是否 fail-closed 无关——`guard_completeness()` 在完全覆盖时也返回 `fallback_mode == "full"`（测试 :165 把该常量钉住，:190/:552 同样）。docstring :126-127 把它定义为"完整性守卫 fail-closed 回退**目标**"，但字段名读作"本次回退**后的**模式"。影响：Slice-2 编排器若单看该字段判定"是否已回退 full"，会永远判为已回退（方向 fail-safe，不损失覆盖），但会产出误导性披露措辞（把 quick 正常执行报成 fell back to full） | ① :908 无条件赋值；② :126-127 docstring 措辞；③ :800-809 `fail_closed` 才是判别字段；④ 三处测试钉住常量 | 二选一：字段改名 `fallback_target`（表"目标"语义），或未熔断时置 `None`；并在 Slice-2 消费处写明"是否回退以 `fail_closed` 为准，`fallback_mode` 仅为回退目标" |
| **F-6** | P3 | `quickscan_registry.py`:82-119（`__all__`）vs :228（`SEGMENTS`） | 70 行注册表**本体** `SEGMENTS` 未列入 `__all__`，而同模块其余 30 余个公开符号齐备。机判：`set(vars(module)) - set(__all__)` 的公开名恰为 `{'SEGMENTS'}`。影响：`from quickscan_registry import *` 与基于 `__all__` 的文档/工具索引会漏掉本切片的**唯一事实源本体**（`all_segments()` 仍在，故非功能缺陷） | ① :82-119 清单（含 `SEGMENT_SPEC_FIELDS`/`SegmentSpec`/`all_segments`，独缺 `SEGMENTS`）；② 实测差集 = `{'SEGMENTS'}` | 把 `"SEGMENTS"` 加入 `__all__`（保持字母序位置），或在 docstring 注明"表本体经 `all_segments()` 暴露，不导出" |
| **F-7** | P3 | `quickscan_registry.py`:779 | `for index in range(start + 5, len(lines)):` 中的偏置 `+ 5` 为**无注释魔数**。实测 `start+5` = 引擎 L14771，仍落在 `_run_full_engine_checks` 的 docstring 内（引擎 L14768-14773：L14767 为 `def`，L14768 `"""Run all governance…`，L14769-14772 续行，L14773 `"""`）——该偏置对"跳过函数自身 def"并无必要（顶层 `def ` 不可能出现在 docstring 行，嵌套 def 带缩进故不匹配 `startswith("def ")`） | ① :779 表达式；② 引擎 L14767-14773 逐行内容；③ :780 判定 `lines[index].startswith("def ")` | 加一行注释说明意图（如"skip the def line and any decorator/blank lines"），或径直改为 `range(start + 1, len(lines))` 并补一条"函数体紧邻下一个 def"的边界用例固定行为 |
| **F-8** | P3 | `quickscan_registry.py`:761-784（返回序）+ :870-871/:886-887（消费面） | `discover_engine_segment_ids()` 返回的是**引擎源码段落顺序**，与 FEAT-020 快照顺序**不同**（实测 engine[50:70] 中 `28u` 落在 `40` 之后、`30c` 先于 `30b`；快照[50:70] 为 `28u` 在 `29` 之前、`30b` 在 `30c` 之前；首个错位下标 = 55）。当前**全部消费面走集合运算**（:870-871 差集、:886-887 差集、`quick_face_ids`/`excluded_ids` 按表序），故无功能影响；但"注册表行序 = 快照序"（测试 :107-110 钉住）与"census 序 = 源码序"两套顺序并存，Slice-2 若按位 zip 二者即静默错配 | ① :784 直接返回 `findall` 结果（源码序）；② 实测 engine[50:70] vs snapshot[50:70] 差异；③ 消费面 :870-871/:886-887 用 `set`；④ 测试 :107-110 断言注册表序 = 快照序 | 在函数 docstring 明写"返回顺序 = 引擎源码顺序，**与快照/注册表位序无关**；消费面 MUST 用集合运算或显式排序"，避免 Slice-2 误用位序 |
| **F-9** | P3 | commit `504cc8f` message；`.governance/evidence-log.md`:1939（EVD-995） | 记录中的行数**与产物不符**：commit message 与 EVD-995 均写 `infra/quickscan_registry.py（929 行…）`，而实际为 **935 行**。影响：治理记录的事实精度（本仓以"事实依据"为准绳，证据行数字应可复算）；无功能影响。另：commit message 的 `929 行` 与同 message 内 `--numstat` 的 935 自相矛盾 | ① `git show 504cc8f --numstat` = `935 0 skills/.../quickscan_registry.py`；② blob 换行字节计数 = 935；③ 工作树 `(Get-Content).Count` = 935；④ EVD-995 原文"（929 行/181 stmts）"；⑤ 同文件的 test 588 行记数**正确** | 更正 EVD-995 的行数为 935（不改动其他已核实的数字），后续证据行行数建议以 `git show --numstat` 为准 |
| **F-10** | P3 | `tests/test_quickscan_registry.py`:293-300 | C3"依据可核"的机判强度有限：`test_c3_verdicts_carry_code_level_evidence_backing_the_declared_deps` 只对每条 dep 的 **target 子串**做 `assertIn(target, joined)`（:298-300），**不校验 basis 中被引的函数名/符号名**。故若 basis 把引擎函数名写错（例如把 `_parse_context_open_risks` 写成不存在的 `_parse_open_risks`），该测试仍会通过——"依据可核"实际由人工/本轮逐符号核对兜底（本轮已逐符号核实**全部属实**，见 §3.2 第 5 条，故当前无虚假依据，属机制性弱断言） | ① :293-300 断言体仅 target 子串；② 本轮逐符号核对结论（§3.2#5）证实 basis 无幻觉符号；③ 对照 :245-253 对 dep 语法的强机判（三段式 + root/kind 域校验） | 追加一条"basis 中出现的 `_` 开头标识符必须能在引擎/`checks/*.py` 中检索到"的机判（或把 C3 basis 的符号引用抽为结构化字段 `evidence_symbols`，与源码机判对账） |

**汇总：P0 = 0（无阻塞项）。P1×1 / P2×2 / P3×7。** 全部为非阻塞发现：F-1 为**测试守卫有洞**（假绿风险，不在六条验收判定链上，修复成本 ≤15 行 AST 改写）；F-2/F-3 为解析侧 fail-closed 缺口与证据措辞准确性（当前无产品消费方，Slice-2 前修即可）；F-4~F-10 为文档/命名/记录精度与机判强度建议。

---

## 五、验收标准逐条裁决

| # | 验收标准 | 裁决 | 事实依据 |
|---|---|---|---|
| 1 | 70/70 覆盖（对 FEAT-020 冻结 ids 机判恒等） | **PASS** | 注册表 id 元组与 `snapshots.json faces.check_segments.ids` **集合与顺序双恒等**；`count == len(ids) == 70`；`reconcile_snapshot()` 实跑 `missing=[] extra=[] ok=True`；引擎 census 70 段集合恒等；测试 :103-143/:463-468 机判 |
| 2 | 完整性守卫：新段未入表 → 告警 + fail-closed 回退 full | **PASS** | fixture 端到端负对照（合成段 41 → `undeclared=('41',)`/`fail_closed=True`/`fallback_mode='full'`/告警含 `UNDECLARED_SEGMENT`；stale 段 20 → 仅告警）实测通过；`guard_completeness()` 在真树实跑 `ok=True undeclared=() stale=()`；`lines()` 给出可读告警文本（:857-861）。**唯一缺口**（重复段号不可见）记于 F-3，不改变本项判定 |
| 3 | 表 schema ⊂ CheckSpec 字段集（Phase-2 平移性） | **PASS** | `SEGMENT_SPEC_FIELDS` = {check_id, domain, input_deps, modes} ⊂ `CHECKSPEC_FIELDS`；后者从 §3.6 文档正则解析并与文档字段元组**逐项相等**断言（测试 :211-219）；每条行 `as_dict()` 键集与字段集恒等（:221-227）。口径按 §二"口径注"采"⊂ CheckSpec 字段集"读法；`not-quick:<CODE>` 取值词汇扩展记于 F-4（备注，不阻断） |
| 4 | C3 四段逐段裁决落表且依据可核 | **PASS** | `C3_ADJUDICATED_SEGMENTS == ('28g','28j','28l','29')` 与 §3.1 L136 逐 id 相同；四段 verdict 全 `retain-quick` 且均在 quick 面（无排除码）；根判定 28g=mixed / 28j=plugin / 28l=plugin / 29=host 与 `input_deps` 逐条互证；**依据字符串引用的全部引擎符号/字面量/行号经本审查逐项对源码核实为真**（§3.2#5），无幻觉符号 |
| 5 | 载体纪律：`verify_workflow.py` 零修改、引擎零引用 | **PASS** | numstat 仅 2 个新增文件（引擎不出现）；引擎源码 `quickscan` 命中 0；引擎物理行数 24,329 = R1 锚 24,329；独立复跑 `archguard-ratchet` = PASS（0 violations，exit 0）；两被审文件与 504cc8f blob 逐字节相同 |
| 6 | AI 专项 5 项逐一有结论 | **PASS** | mock 残留 / 硬编码返回值 / 幻觉 API / 未实现 TODO / 过度实现 —— 5 项逐项结论见 §3.1，均有可复查事实（机判命中数、逐符号核实、范围边界对照） |

**裁决汇总：6/6 PASS。** 无验收标准未通过；F-3 与 F-1 分别是"守卫覆盖面"与"测试自身覆盖面"的加强项，均不改判本表。

---

## 六、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅ 0（10 条发现中无 P0） |
| 5 维度全覆盖 = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐项有结论（§一） |
| 每条发现标注级别 = 100% | ✅ F-1~F-10 全部标注 P1/P2/P3 + file:line + 事实依据 + 修复建议 |
| 设计一致性检查已完成 | ✅ 对照 §250 ①②③、§3.1 C1/C2/C3、§255、§4.3、§2.4、evolution §3.6、§4.1 R5、§7.2 QR-1/QR-5 —— 13 项逐项比对（§二） |
| AI 代码专项 5 项检查全部完成 | ✅ mock 残留/硬编码/幻觉 API/未实现 TODO/过度实现 逐项有结论（§3.1） |
| 逐行读两文件全文 | ✅ 935 + 588 = 1523 行全文逐行（非抽样）；并逐符号核对引擎与 `checks/` 的对侧事实 |
| 声称与代码事实交叉核对（任务书硬门槛 4） | ✅ 12 条声称逐条给出核查等级（§3.2）：9 条独立复现、2 条采信（附静态论证）、1 条不符并登记为 F-2/F-9 |

---

## 七、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：§6 Slice-1 的三条验收要点（70/70 对账、完整性守卫 fail-closed、schema ⊂ `CheckSpec`）**全部落地且各有机器可判的固定物**，六条验收标准逐条 PASS；70/70 覆盖经"集合 + 顺序 + 引擎 census + 快照 count"四重独立核实为恒等；排除集与 FIX-270 `_PLUGIN_PRODUCT_CHECK_IDS` 经"注册表 = 源码文本解析 = 实际 import 常量 = §3.1 C1 行"四路交叉为恒等（25 段），quick 面 45 段 = §3.1 C2（机器解析 41）+ C3 四段；C3 四段的"依据可核"经本审查**逐符号对引擎源码核实为真**（含 `check_m5_runtime_triggers`、FIX-178 排除、`EVIDENCE_PATH`/`SAMPLE_PATH` 派生），无一处幻觉符号；载体纪律成立（引擎零改动、零引用、R1 锚 24,329 不变、`archguard-ratchet` 独立复跑 PASS/exit 0）；测试 60/60 与覆盖率 181 stmts/1 miss=99%（miss=L699 导入期守卫）经独立复跑逐数字吻合；AI 专项 5 项无异常。P0 = 0 且六条验收全 PASS ⇒ 无未解决 BLOCKING finding，满足 code-review SKILL「循环角色」段的通过终态契约，并以独立结构字段声明 `unresolved_blockers=0`。

**发现计数（独立行，供机器记录）**：P0 = 0；P1 = 1；P2 = 2；P3 = 7。

**唯一 P1（F-1）的处置要求**（按 code-review SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」）：F-1 是**测试守卫的扫描面截断**，修复成本 ≤15 行（改 AST 模块体机判），**建议本轮或紧随补丁轮落地**；若本轮不修，**MUST 由 Coordinator 登记为遗留项并附关闭截止日期**——否则后续切片（尤其 Slice-2 在表旁新增模块级常量/求值）会在"零 I/O 已机判"的假绿下漂移。**F-1 不影响任何验收标准的裁决**（验收⑤由四项独立证据支撑，见 §五第 5 行）。

**P2 处置要求**：F-2（解析 fail-closed + 证据措辞）与 F-3（观察侧唯一性）应在 **Slice-2 消费注册表之前**修复——F-2 影响 EVD-995 的方法描述准确性与解析退化时的披露正确性；F-3 的 `len(observed)` 失真会被 Slice-2 的长度断言继承。两者均 ≤10 行改动。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**，以免与 FIX-291 的 provably-zero 探针（附着 `P0/P1` 非零计数即拒绝认证为零）冲突；P0/P1/P2/P3 计数写在独立行。

---

## 八、遗留项与建议处置

| 项 | 级别 | 建议处置 | 责任方 |
|---|---|---|---|
| F-1 | P1 | 本轮（或紧随补丁轮）把 `test_registry_declares_no_module_level_file_io` 改为 AST 模块体节点机判；否则登记遗留 + 关闭截止日期 | Developer / Coordinator |
| F-2、F-3 | P2 | **Slice-2 开工前**完成：F-2 更正措辞（"源码文本解析"）并补解析结果非空/数量 fail-closed 校验；F-3 补 census 唯一性校验 + 重复段号负对照 | Developer（下一轮） |
| F-4~F-8、F-10 | P3 | 记跟踪表：F-4 补 Phase-2 token 平移口径；F-5 字段改名/语义说明；F-6 补 `__all__`；F-7 注释或简化魔数；F-8 docstring 明写返回序；F-10 强化 C3 依据机判 | Developer / Coordinator |
| F-9 | P3 | 更正 EVD-995 的行数 929 → 935（其余已核实数字不动） | Coordinator（治理记录） |
| 残余未核验面 | — | ① 596.2s 全量回归未复跑（静态论证见 §3.2#9，如需机器证据建议由 Coordinator 在无并发会话时补跑）；② lint NOT_RUN 未验证工具安装状态；③ `input_deps` 逐行**完备性**（是否漏声明输入依赖）依赖 docstring:44-49 所述的插桩实验，该留痕未入库，建议作为 Slice-2 shadow（S-B）的输入项而非本轮阻断项 | Coordinator |

*审查边界声明：本轮为**只读审查**，但按任务书硬门槛 4 的要求执行了**只读核验命令**（`git show/numstat/hash-object`、`python -B` 内省与实测计时、`pytest` 60 例、`coverage` 单模块、`verify_workflow.py archguard-ratchet`）——**未修改任何产品代码、未写入任何仓库文件**（覆盖率运行产生的仓内副本 `.coverage_reg` 系我创建并已即时删除；`archguard-ratchet` 的写盘路径仅在 `regen_baseline`/`--regen` 内，本轮未触发）。被审两文件与 `504cc8f` blob 逐字节相同，审查期间并发的未跟踪文件（`infra/registry.py`、`infra/tests/test_registry.py`、`.it_*.txt`）不属审查对象且未被我改动。核查等级逐条标注于 §3.2：9 条独立核实、2 条采信（附静态论证）、1 条不符（已登记 F-2/F-9）；无法核验项已在 §八"残余未核验面"显式登记，未写成事实。*
