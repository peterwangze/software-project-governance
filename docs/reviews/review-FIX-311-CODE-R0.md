# FIX-311 代码审查报告（Code Review R0，V4 切片）

- **任务**：FIX-311（0.81.0 切片 **V4**：group 语义与 loader 对齐 G-02/G-03 + 分类自检 G-18 + F-R1-03 白名单化）
- **Round**：R0（首次审查；无前轮 findings）
- **审查对象**：工作树内 2 个修改文件 —— `skills/software-project-governance/infra/dsh_compat.py`（实测 **+421/−50**；1757 → **2128** 行）、`skills/software-project-governance/infra/tests/test_dsh_compat.py`（**+348/−4**；→ **1806** 行）；基线 HEAD = `3c37342`
- **权威来源（已读）**：AUDIT-153 §5（G-02/G-03/G-18）；设计 §4.4.2 / §4.3 / §4.6 / §6.1 V4 / §5.6；**loader 真实语义** = `@deepseek-ai/cordis-plugin-loader/lib/index.js:363-369` `_disabled()`
- **Reviewer**：Code Reviewer Agent（只读；仓库零写入已实证——收尾 `git status` 恰 4 行 modified / 0 untracked）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0 / P1=0 / P2=2 / P3=1）

## 0. 判据前置：权威语义逐条核对（§4.4.2 G02-a/b、G03-a/b/c、§4.5 G-18、§6.1 V4 共 8 条）

全部 ✅：group 必留记录（`kind: BUILTIN` + `builtin:'group'` + 子行计数）；`name` 必为已声明内建 `cordis:group`（契约 `host.row_contract.builtin_group_name`）；group **自身** `disabled` 不求值；`disabled` 仅在继承时求值、抛错须披露子行（`DISABLED_INHERITED_UNKNOWN` + `rows_inherited_unverified`）；childless group + 抛错**不是** finding；G-18 断言「每个 kind 恰属一类」（实现采四类，与既有 `kind == "PASS"` 独立分支一致，**非偏离**）。

**契约事实实测**：`cordis:group` / `group_self_disabled_shortcircuit=True` / `ancestor_disabled_inherited=True` —— 与 loader 「自身短路 + 祖先走查不带短路」**逐项一致**。

## 1. 独立复现结论

| # | 复现项 | 结果 |
|---|---|---|
| R-1 | **G-02 红→绿**（AST 提取 OLD `PROBE_SCRIPT` + 独立重实现 walk 对照） | OLD 版 **完全不含** `GROUP_NAME_UNRESOLVED`/`builtin:'group'`/`inherited_unverified`/`DISABLED_INHERITED_UNKNOWN`（4/4）；`cordis:gruop`+子行：**OLD=PASS（enabled=1）→ NEW=FAIL** ✅ |
| R-2 | **G-03① 红→绿**（真实平面 FX-GROUP-02） | **NEW=`NOT_RUN`/`issues=[]`/group 留 1 条记录**；OLD=`DISABLED_EXPR_ERROR` ⇒ `FAIL`（**假阳**）✅ |
| R-3 | **G-03②（核心）子行仍被校验**（真实平面 FX-GROUP-03） | **NEW=`rows_checked=1` + `DISABLED_INHERITED_UNKNOWN` + `rows_inherited_unverified=1` + 4 条 row 记录**；OLD=记录 1 条/enabled 0/**子行完全消失**（连带假阴）✅ |
| R-4 | **祖先走查不回归** | 单层：子行 `DISABLED_INHERITED`、`issues=[]`、group 自身无 `BUILTIN` 记录（正确）；**嵌套场景另发现 OLD 的第二处假阳**（内层 group 的 `disabled` 被错误求值）✅ |
| R-5 | **G-18 fail-loud** | 未声明 kind ⇒ `verdict=FAIL` + `issues=1`（含 `undeclared row kind`）；`_informational_details` **raise ValueError**（不落 `[INFO]`）✅ |
| R-6 | 12-kind 分类穷尽/互斥表与代码一致 | 探针可发射 12 种 kind，与 4 表**恰好一一对应、无重复**（7+3+1+1，unique=12）✅ |
| R-7 | **G-01 成果不回退** | `coverage` 结构齐备且未动；`emit_disclosures()` 仍被两分支调用；`_resolve_verdict` **首分支仍为 FINDING 优先**；`rows_checked==0 ⇒ NOT_RUN` 分支逐字节未动 ✅ |
| R-8 | **28v + exit** | `enabled 23 / checked 18 / NOT verified 5 / inherited-disabled 0 / unresolvable-inheritance 0`、`writes: 0`、PASSED、**exit 0** ⇒ 口径不变 ✅ |
| R-9 | 三套测试 | **`test_dsh_compat` 71 OK（0 skip，live 平面真跑）** / `test_dsh_contract` 120 OK / `test_dsh_adapter` 46 OK ✅ |
| R-10 | **真实环境零写入** | 隔离机制：`DSH_HOME` 重定向 + **该 temp 目录运行后条目数 = 0**；`~/.dsh` mtime `2026/9/12 20:06:00` 未变（`~/.dsh/profiles` 仅只读扫描，既有行为）✅ |
| R-11 | 引擎面 fail-loud | 注入未声明 kind 后 `emit_check_section()` 返回 issue 数 1 并正常打印 `[FAIL]`（不经过会抛错的 `_informational_details`）✅ |
| R-12 | **变异实证** | 5 个变异 **5/5 被抓回**（`_assert_report_kinds_declared`→no-op、`_classify_row_kind`→恒 INFO、`INFO_KINDS`→空、`FINDING_KINDS` 去 `GROUP_NAME_UNRESOLVED`、`_is_group_record`→恒 False）✅ |
| R-13 | 范围纪律 | 恰 4 行 modified / 0 untracked；未改契约/掩盖面 ✅ |

## 2. 三处请裁决项 —— 逐条判定

### ① group 记录走 `[INFO]` 而非 `[NOT_RUN]` —— **背书**

1. **语义正确**：`UNVERIFIED_KINDS` 的定义是「**enabled** 行的 config 未被 schema 校验」；group 行**没有 config 可校验**（内建 `cordis:group` 选择子行而非模块）。
2. **口径后果实证**：若并入，`NOT verified` 将从 **5 → 8** 而 `rows_enabled` 仍 **23** ⇒ 分子分母自相矛盾，破坏 §4.3 L1/L3 与 release-checklist #9 的机检锚点。
3. **不掩盖事实**：group 记录是**新增披露**，`[INFO]` 面在 `run_cli` / `_print_human` 均已打印（实测 FX-GROUP-02 上屏）⇒ 信息未被隐藏，只是**未被谎报为「未验证」**。

### ② 抛错 group 的子行同时产生「披露 + 校验」两条记录 —— **保留**

1. 两条记录陈述**两个都为真**的事实：「无法判定是否启动」（G03-b 披露义务）与「config 与安装态 schema 不符」（本片要消除的连带假阴）。
2. **不产生假阳/假阴**：`issues=2` 皆为真实缺陷；若子行 config 合法则记 `PASS` 且不产生 issue（实测路径存在）。
3. 披露类 **不**计入 `failures`，评分口径干净。压合会重新引入旧版两类错误之一。

### ③ F4 分支拆分 + 两条夹具同步 —— **属必要范围**

1. 旧文案在有第二个成因（**根本不存在任何 plugin 行**）时是**无测量支撑的事实主张**（对一行都没有的组合声称「每一行都是 disabled」）；而 childless group 正是该成因的**新来源**（G02-a 之前 group 零记录）⇒ **属 G-02 的直接后果**。
2. 两分支都可达且都有测试（`test_zero_enabled_rows_degrades_to_not_run` 走 disabled 行；新增 `test_no_plugin_row_at_all_does_not_claim_disabled_rows` 走空行）。
3. `_matrix_entry` 的 `inherited_unverified` 派生是**新计数器的必要配套**（否则矩阵夹具与探针口径不一致），非范围蔓延。

## 3. Findings（均非阻塞）

| # | 级别 | 位置 | 事实（已独立复现） | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-01** | **P2** | `dsh_compat.py:1477` + `:2020`/`:2081` | `run_cli()`/`_print_human()` 在 FAIL 分支**之前**无条件调 `_informational_details()`，其首行 `_assert_report_kinds_declared()` 对未声明 kind **raise**。实测：CLI **抛 `ValueError` 逃逸**、stdout 停在逐 composition 头、**未打印 `Result: FAILED` + issues 清单**；对照 `emit_check_section()` 正常返回 issue 数 1 | **无错误判定**（FAIL 已定，非 0 退出 ⇒ fail-safe），但 standalone CLI **丢失完整可行动报告**并留未处理栈 —— 与设计 §4.4.6 G10-b「公共入口不得泄漏栈」/§2.5.1「a verdict, not a crash」取向不一致 | 三选一（推荐①）：①调用点后移到 FAIL 分支之后且仅对非 UNKNOWN 报告调用；②报告构造期先做守卫并把失败降级为 finding；③调用点捕获 `ValueError` 并渲染为额外 issue |
| **F-02** | **P2** | `dsh_compat.py:262-268` | `_classify_row` 对 `row.get("kind") is None` 返回 `CATEGORY_INFO`，**绕过** `_classify_row_kind` ⇒ 与同函数 docstring「whitelist, not a residual」及 F-R1-03 意图不一致。实测：注入无 `kind` 行 ⇒ `verdict=NOT_RUN`、`issues=[]`、`[INFO] ghost … [None]` 上屏且**不抛** | 未来探针若**省略** `kind`（而非发错 kind），其行静默落 `[INFO]` 且不改变判定 —— F-R1-03 残差形态的另一种输入形状。**P2 而非 P1**：探针为同仓固定源码，12 处 `entry.rows.push` **全部显式带 `kind`**（R-6 已核对），触发需先引入探针缺陷 | 与 `CATEGORY_UNKNOWN` 同待遇（无 `kind` ⇒ UNKNOWN）；或**显式写入 docstring 并用测试钉住**（现有 6 条新测试**均不覆盖无 `kind` 行**） |
| **F-03** | **P3** | `dsh_compat.py:2017`、`:2071` | 两处渲染面仍用 `row.get("kind") in FINDING_KINDS` 成员判定（未走 `_classify_row`）⇒ 未声明 kind 时渲染的 `[FAIL]` 行数 = **0**（finding 只在 `issues` 清单出现） | 显示面歧义，与「单一分类源」略有差距；**不改变判定** | 两处改走 `_classify_row(row) == CATEGORY_FINDING`，或对 `CATEGORY_UNKNOWN` 行也渲染 `[FAIL]` |

**建议处置次序（可同批或紧随）**：F-02（约 3 行 + 1 测试）→ F-03（2 行 + 1 断言）→ F-01（结构调整）。

## 4. 五维度结论

- **正确性 ✅**：三处判据与 loader 真实语义逐条对齐；计数口径自洽（`rows_inherited_unverified` 与 `rows_inherited_disabled` 分离，前者进 unverified 通道、后者不进 enabled 分母）；`_resolve_verdict` 分支顺序契约未变；G-18 的 `CATEGORY_UNKNOWN ⇒ failures.append` **填上了** F-R1-03 的兜底缺口。
- **安全性 ✅**：`_render_probe_script()` 单趟 `re.sub` + 兜底替换（消除二次重写风险）+ 类型校验 + leftover 兜底 ⇒ 无注入/无静默半渲染；新增行无密钥/版本字面量；失效方向 = fail-closed。
- **可维护性 ✅**（附 F-03）：单一分类源设计清晰、注释与机制一致、无死代码；`dsh_compat.py` 已 2128 行（既有单体趋势，本片未引入上帝类）。
- **性能 ✅**：新披露循环 O(children)；`_assert_report_kinds_declared` 为 O(rows) 二次遍历（23 行，可忽略）；import 期表校验一次；28v 全量 4.99s 同量级。
- **测试覆盖 ✅**：新增 `RowKindClassificationTests` 6 方法 + 4 条 live 用例 + C-23 预期改写落地；**5/5 变异抓回**；**live 平面真跑 0 skip**。

## 5. AI 代码专项 5 项

mock 残留 **0**（真实 `check_dsh_preset_compat` + 真实夹具；注入探针产物属既有既定手法）· 硬编码返回值 **0**（契约事实经 `_fact()` 读取）· 幻觉 API **0** · 未实现 TODO **0** · 过度实现 **无阻塞项**（唯二超字面改动 = F-02/F-03，已定级并说明理由）。

## 6. 事实更正（Coordinator 侧记账）

1. 实测规模：`dsh_compat.py` **+421/−50 / 2128 行**、`test_dsh_compat.py` **+348/−4 / 1806 行**（任务书派出时的估算 +471/−x / 2118 行不精确）。
2. `review-FIX-319-CODE-R0.md:97` 记「`**a****b**` → PASS」与 HEAD 实测（FAIL）不符 ⇒ 该格**勘误**。
3. 当前 `check-governance --summary-only` = **87 issues**（FIX-319 期记 86，差 1，与本两片无因果）；Check 18c 唯一 FAIL 仍是 `REL-077 missing execution packet`。

## 7. 真实环境命令上报表（R4）

全部写操作限于 `%TEMP%\cr-321-311\**`（probe/sim 脚本、`headsrc`、夹具、隔离 home）；**仓库路径写入 0**；`~/.dsh` 写入 0（mtime 未变，经环境变量重定向）。**未执行任何 `git add/commit/checkout/restore/stash/reset`**（★ 尤其未用 `git stash`）。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
