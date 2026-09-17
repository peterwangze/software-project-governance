# Review Report — FIX-350 CODE R0（ArchGuard 判定面校准 + ratchet 重锚）

- **Task ID**: FIX-350（0.83.0 链；Developer 已交付，未 commit——工作区即待审变更集）
- **Round**: R0（首轮）
- **Reviewer**: Code Reviewer Agent（只读审查；未修改被审代码；未执行命令；未与用户交互）
- **审查对象**: 7 文件，+203/−26
- **审查依据**: diff 两份（fix350-main.diff / fix350-tests.diff）+ 被审文件工作区现状逐行核对 + 关联实现静态读取（verify_workflow.py / gate_domain.py / TOOLS.md / 投影树）
- **结论**: **APPROVED_WITH_NOTES**
- **unresolved_blockers**: **0**
- **发现计数**: **P0=0, P1=0, P2=1, P3=3**

---

## 0. 事实红线声明（未验证项汇总）

本审查为纯静态审查（角色约束：不执行命令）。以下 Developer 验收声明为**运行时实测值，本审查未复跑、不为其背书**，仅在机制层面做静态佐证：

| 申报项 | 本审查状态 |
|---|---|
| 28o fixture/.governance 条目清零（ERROR 8→4，残余为产品源真实 advisory） | **未验证**（运行值）；方向经静态核实支持：`project/**` 与 `.governance/**` 豁免在 gate 扩展后确会消除这两棵树的全部四面 findings（verify_workflow.py:19532,19535,19544） |
| 28p 0 ERROR/0 WARN + 3 [EXEMPT]（pairs=5） | **部分静态佐证**：投影树确为 5 文件（`__init__/cleanup/archive/verify_workflow/resolve_entry`，glob 实测），3 条豁免精确命中其中 3 个 source 相对路径，其余 2 对（archive.py、verify_workflow.py）保持受检；"0/0 WARN" 数值为运行值 **未验证** |
| ratchet 38/38；architecture_health 23/23；test_verify_workflow 857+89 subtests 零 FAIL | **未验证**（运行值，未复跑） |
| 裸引擎 PASSED / cross-refs / manifest（723 canonical） | **未验证**（运行值，未复跑） |
| +130 = FIX-348/349 预存 +85 + 本任务 +45 | **算术闭合但 +85 分账未独立验证**：+45 经逐 hunk 净和静态复核成立（见 §6.5）；+85 为前任务申报值，本审查无前任务 diff，未验证 |
| 3 个 HEAD 干净树预存环境红（quickscan/fix270）非本任务引入 | **未验证**；本任务 diff 未触及 quickscan/fix270 相关面（静态范围核对），"HEAD 复现" 陈述无法在只读约束下复跑 |
| baseline `generated.git_head: bf7e25af…` 与实际 HEAD 的对应 | **未验证**（不可运行 git） |

---

## 1. Developer 申报逐条核实矩阵

| # | 申报 | 核实结果 | 事实依据 |
|---|---|---|---|
| 1 | `_archguard_exclusion_match()` 单一匹配实现；`_archguard_excluded` 薄包装；gate 扩展至 function_size/module_constants/duplicate_constant；无豁免 schema 行为不变 | ✅ **证实** | verify_workflow.py:19453-19480（唯一匹配实现，返回 entry/None）；:19483-19485（薄包装仅 `is not None`）；:19532（excluded 单点计算）、:19535（module_size 面）、:19544（`.py and not excluded` 一并 gate function_size/module_constants/duplicate_constant）。exclusions 为空列表时 `_archguard_exclusion_match` 对一切返回 None → 行为与旧版逐行等价（旧版同函数仅返回类型不同） |
| 2 | dup pair 豁免按 source 相对路径；豁免对计入 pairs_checked；exemptions 独立列表 + [EXEMPT] 双面披露；不进 findings | ✅ **证实** | verify_workflow.py:19654（`dc.get("exclusions", [])`）；:19659-19666（命中 → exemptions.append(path+reason) + continue，不读文件不产 finding）；:19691（`pairs_checked: len(pairs)` 在豁免 continue 之后按全量 pairs 计数 → 豁免对计入）；披露双面：28p 聚合段 :16006-16009、CLI :22874-22877（均 `.get("exemptions", [])` 防御 error-path 无键返回 :19644） |
| 3 | schema：module_size.exclusions + project/** + .governance/**；duplicate_code.exclusions 三条精确 source 路径（project/** 对 source 匹配无效）；阈值 30→80 + note；未移动 docs/release 任何文件 | ✅ **证实**（含一处 P2 措辞精度，见 F-1） | architecture-health.json:12-13（两条新豁免含 reason+RISK-039 链）；:33-35（三条精确路径，无通配）；:46-47（80 + note）。`project/**` 对 source 无效的论断**成立**：pair 的 rel 形态为 `py.relative_to(root)`（verify_workflow.py:19630），恒为 `skills/software-project-governance/infra/<name>.py`，源树无 `project` 段 → 永不命中（fnmatch 与 bare 段匹配均需段相等，"software-project-governance" ≠ "project"）。docs/release 目录 232 文件全部在位（glob 实测），无移动痕迹 |
| 4 | F-1 separators 补 U+000C + docstring 家族清单同步 + 负例测试；F-2 WARN/exit-1 双面语义（CLI sys.exit(1) 事实） | ✅ **证实** | F-1：verify_workflow.py:11783（U+000C 入表）；:11763-11765（docstring 家族清单补 FF——全仓库唯一枚举点，grep 实测无第二处漏同步）；负例 test_verify_workflow.py:11869-11884。F-2：docstring :11767-11771 双面语义陈述与事实一致——聚合面 `structural_issue_is_blocking`（:393-396）将 WARN 排除在 blocking 之外；CLI 面 `cmd_check_structural_validity`（:21104-21115）`if issues: … sys.exit(1)` 无 WARN 豁免——**`sys.exit(1)` 事实核实成立** |
| 5 | regen：R1 24453→24583；R4 1299→1301；R2 不变；七规则全 PASS | ✅ **证实**（锚值）；运行值「七规则全 PASS」未验证 | architecture-baseline.json:17（anchor_loc=24583）；:541（total=1301）；R2 inventory（:21-366）无新增条目——与机制一致：R2 扫描 infra/ 反向依赖且 scan_exclusions 排除 verify_workflow.py 自身（:367-374），本任务仅改该文件。「七规则全 PASS」为运行值，未验证 |
| 6 | 验收实测（见 §0 表） | 部分/未验证 | 见 §0 |
| 7 | 3 个预存环境红非本任务引入 | 未验证 | 见 §0 |

---

## 2. 五维度逐项结论

### 维度 1：正确性 — 通过

- **豁免 gate 扩展**（:19528-19544）：excluded 单点计算后同时约束 module_size 与 `.py` 专属三面；非 `.py` 文件的 module_size 豁免行为与旧版一致（旧版即全文件类型）。无豁免 schema 下 `exclusions=[]` → 全量扫描，与旧版逐行等价。逐条件核对无误。
- **dup 豁免通道**（:19659-19666）：豁免判断在文件读取之前（省 I/O）；`continue` 保证豁免对不进 findings；`pairs_checked=len(pairs)` 与豁免无关 → 计数语义正确（「检查了 5 对，其中 3 对豁免」的口径自洽）。
- **error-path 防御**：schema 损坏时返回 dict 无 `exemptions` 键（:19644-19645），两个打印面均 `.get(..., [])`（:16006, :22874）→ 无 KeyError 路径。
- **U+000C**（:11783, :11797-11810）：检出逻辑与既有分离符同构（find 全量扫描 + 行列计算），行号口径 `content.count("\n", 0, pos)+1` 与 FF 作为 splitlines 边界的语义一致。
- **阈值 re-arm**（:19725, :19734 `>=`）：74 版本现状下 30 恒 WARN、80 重新出槽——`>=` 语义与 note 中 "at 80 the advisory re-arms" 一致（74 < 80 时静默，第 80 个版本入位时触发）。
- 边界条件：`_archguard_exclusion_match` 对非 dict entry / 空 path 容错（:19464-19466）；`exclusions or []` 防 None。已核对。

### 维度 2：安全性 — 通过

- schema 为仓库内受控文件，非外部输入；fnmatch 匹配无注入面。
- 路径归一化：`str(rel_path).replace("\\", "/")`（:19462）——Windows 反斜杠形态在匹配前归一，豁免不会被 `\` 形态绕过。
- 无敏感数据硬编码；diff 无密钥/token。
- 权限面不适用（本地诊断工具，无鉴权语义）。

### 维度 3：可维护性 — 通过（带 1×P2、2×P3）

- **单一实现 + 薄包装**（:19453-19485）从结构上消灭了「豁免匹配双实现漂移」的可能——check_architecture_health 与 check_duplicate_code 现共享同一匹配函数，docstring 明确两 callers 的分工（boolean vs 披露）。这是本改动最核心的可维护性收益。
- docstring（:11763-11765, :11767-11771）与 TOOLS.md 三点（:516, :568/:571, :582）同步更新，注释-代码一致性核对无误。
- schema reason 字段均携带 RISK-039 / FIX-350 追溯链与长期修复方向，豁免不是裸条目。
- 瑕疵见 F-1（P2）/ F-2、F-3（P3）。

### 维度 4：性能 — 通过

- 豁免匹配复杂度 O(规则数 × 路径段数)，规则个位数，每文件一次；无新 I/O。
- dup 豁免对提前 continue，跳过双文件读取——净减 I/O。
- 无新循环嵌套、无 N+1。

### 维度 5：测试覆盖 — 通过

- **负例锁定真实**：`test_no_exclusions_fixture_still_scanned`（test_architecture_health.py:126-147 diff 行）在无 project/** 豁免的 schema 下断言 fixture 镜像在三面（function_size/module_constants/duplicate_constant）均产出 finding 且存在 ERROR——直接钉住「机制不弱化」。fixture 数值经阈值推演复核：601 行函数 ≥ error 500 → ERROR；200 常量 ∈ [150,300) → WARN；X_CONST 双定义 → ERROR。断言可达，非恒真。
- **正例锁定豁免**：`test_exclusion_gate_covers_function_and_constant_faces` 断言豁免后镜像零 findings（四面齐豁）。
- **dup 双向**：`test_without_exclusions_pair_still_flags`（pair 仍 flag + `exemptions == []` 零豁免披露）+ `test_pair_exemption_disclosed_and_excluded`（finding 消失 + `pairs_checked==1` + path/reason 披露内容断言）。
- **U+000C 负例真实**：真实临时文件 + `patch.object(vw, "GOVERNANCE_DIR")` 隔离（test_verify_workflow.py:11814-11816），断言精确到 file/line/label——这是真实扫描函数在真实文件上运行，非 mock 捷径。
- 覆盖缺口（非阻塞）：豁免匹配的路径变体（反斜杠字面 schema path、大小写差异、`**/` 前缀 pattern 形态）无直接单测——helper 匹配逻辑本身非本任务修改，见 F-4（P3）。

---

## 3. 审查重点专项核实

### 3.1 豁免机制不弱化判定面 — 通过
- 负例真实锁定（§2 维度 5），两面（architecture_health + duplicate_code）各有无豁免负例。
- 单一实现核实：`_archguard_excluded` 仅一行委托（:19485），全仓库 grep 无第二套豁免匹配逻辑；两个消费面均走 `_archguard_exclusion_match`。
- 路径变体绕过评估：反斜杠已归一（:19462）；`**` 段有 basename/整段双重 fallback（:19470-19475）；bare 段匹配（:19476-19479）方向是**过宽**（over-exempt）而非漏匹配（under-exempt）——弱化方向的偏差被 schema 精确路径（dup 面）与 RISK-039 登记的目录级豁免（module_size 面）约束，见 F-3。

### 3.2 dup 豁免口径 — 通过
- `project/**` 永不命中的论断**成立**（§1 #3：pair rel 恒为 source 相对路径，源树无 project 段）。
- 三条精确路径宽窄适中：命中投影树 5 对中的 `__init__.py`（100% 同一）、`resolve_entry.py`（100% 同一）、`cleanup.py`（89.2%，≥error_pct 80 原本产 ERROR）；`archive.py` 与 `verify_workflow.py` 两对保持受检——与申报「其余镜像对保持受检」一致。
- 豁免粒度为文件级精确路径，无通配，无 over-match。

### 3.3 [EXEMPT] 披露真实性（DEC-151） — 通过
- 数据面：exemptions 独立列表（:19692），不混入 findings。
- 披露面 1：28p 聚合段（:16006-16009，豁免行先于 findings 打印、不截断——豁免上限=pairs 数，当前 3，无溢出风险）。
- 披露面 2：CLI（:22874-22877）。两处均含 reason（空 reason 时退化为纯路径，仍披露）。
- 无静默豁免路径：除这两个打印面外无其他消费方丢弃 exemptions。

### 3.4 schema 校准合理性 — 通过（附 P2）
- 30→80 事实链静态核实：`check_technical_debt` 以 `release_docs_archive_threshold_versions` 对 docs/release 版本 token 计数触发 WARN（:19725-19739）；**docs/release 现状 74 个去重版本**（232 文件逐条清点），note 中「74」准确——30 阈值下为永久 WARN（告警疲劳），80 重新出槽，校准方向合理。
- check-release 对 docs/release 的依赖**方向成立**：`check_release_docs_coverage`（:6292-6303，经 check_release_readiness :7088 调用）要求目标版本三文件存在于 docs/release；verify_workflow.py 硬编码引用 docs/release/0.46.0 三文件（:2869-2871, :6243），移动将产生 dangling ref → `check_cross_references` FAIL → check-release FAIL（:7067-7077）。但「reads these files for released-version lineage」的机制表述与静态事实**部分错位**（release lineage 事实源实为 git 历史 :7288-7298 与 plan-tracker roadmap，gate_domain.py:608-649；docs/release 的机器依赖是「目标版本存在性 + 跨引用完整性」）——见 F-1（P2，措辞精度）。
- `.governance/**` 豁免与 `governance_data_size` 独立面**无冲突**：后者只读 schema `governance_data_size.files` 四个热文件（architecture-health.json:51-62），与 ArchGuard exclusions 无共享读取路径。

### 3.5 regen 形态 — 通过
- 机器生成形态：键名字母序排列、2 空格缩进一致、`generated.git_head` + `loc_caliber` 元数据在位（architecture-baseline.json:12-15）——无手写痕迹特征。
- 锚值核实：R1 anchor_loc=24583（:17）、R4 total=1301（:541）、R2 inventory 无新增（与本任务仅改 verify_workflow.py 自身且被 R2 scan_exclusions 排除的机制一致）。
- census 链注：test_archguard_ratchet.py:60-64 完整记载 +2 的两个打印点归因、R1/R4 双值、日期与任务标识——链注纪律满足。
- authored zone 原样携带：R1 self-bootstrap 豁免条目（DEC-183/184/190，allowance_lines=0，expire 0.82.0）完整在位（:2-11）。
- R4 per_function 分账自洽：+2 = `_run_full_engine_checks`（28p 段 1 处）+ `cmd_check_duplicate_code`（1 处），各 +1。

### 3.6 F-1/F-2 与 FIX-349 R0 发现的对应闭合 — 闭合
- F-1（U+000C 补扫）：检出实现 + docstring 家族清单 + 负例测试三件齐；全仓库唯一家族枚举点已同步（grep 核实）。
- F-2（双面语义注记）：docstring 新增段（:11767-11771）与两个消费点的事实在静态核对中逐字成立（§1 #4）——将「WARN 在聚合面非阻塞但在 CLI 面致命」的隐式行为显式化为运维警示，闭合 FIX-349 R0 对该语义模糊性的发现。

### 3.7 锁外两文件追认评估 — 建议追认
| 文件 | 必要性 | 最小性 | 追认建议 |
|---|---|---|---|
| test_architecture_health.py（+102） | 4 条测试全部直接钉住本任务核心行为申报 #1/#2（gate 扩展正反例 + dup 豁免正反例），是「豁免机制不弱化」声明的唯一机器看护 | 仅新增 helper + 2 测试类 + json import；未触碰既有测试 | ✅ 建议追认 |
| test_archguard_ratchet.py（+7/−2） | FACTS_PRINT_TOTAL 是 baseline R4 的强制配套事实（print census 实际 +2），不同步则 ratchet 必红；census 链注为 regen 纪律载体 | 单常量 + 注释块，无逻辑改动 | ✅ 建议追认 |

---

## 4. 发现列表（P0~P3）

> P0=0，P1=0。以下 4 条均不阻塞合并。

### F-1（P2）release_docs_note 理由链的机制表述与静态事实部分错位
- **位置**: `core/architecture-health.json:47`
- **事实**: note 称 "check-release reads these files for released-version lineage"。静态核实：①`check_release_docs_coverage` 仅校验**目标版本**三文件存在（:6299-6303），不读历史版本文件；②`check_release_lineage` 事实源是 git 历史（:7288-7298 委托 commit_checks），`released_history_version` 读 plan-tracker roadmap（checks/gate_domain.py:608-649）——均非 docs/release；③可证实的 docs/release 机器依赖是「目标版本 REL-021 存在性」+「verify_workflow.py:2869-2871/:6243 硬编码引用 0.46.0 三文件，移动即 dangling ref → cross-references FAIL」。
- **影响**: 策略结论（全历史保留 + 80 出槽）不受影响、方向正确；但 note 作为 schema 内持久化理由链，其机制表述经不起静态复核，未来按此表述做归档决策可能误判风险面。
- **建议**: 后续微调 note 措辞为可复核事实（如「check-release 经 REL-021 校验目标版本 docs 存在性且引擎硬编码引用部分历史文件，移动产生 dangling ref」），非本轮义务。

### F-2（P3）census 链注的函数归属命名近似
- **位置**: `infra/tests/test_archguard_ratchet.py:61-62`（diff 后行号）
- **事实**: 链注称打印点在 "28p check-governance segment (cmd_check_governance)"；实际该打印在 `_run_full_engine_checks` 的 28p 段（:16008），baseline R4 分账归 `_run_full_engine_checks: 580`（baseline :461）。账目（+2、两处各 +1）正确，仅叙述命名以入口命令代称所属函数。
- **建议**: 不要求修改；后续触碰该注释块时可顺手对齐为 `_run_full_engine_checks`。

### F-3（P3）新豁免条目依赖 bare 段级匹配的隐性宽语义
- **位置**: `core/architecture-health.json:12-13`；`verify_workflow.py:19476-19479`
- **事实**: `project/**` 经 bare 段匹配（`bare="project"`，任意路径段等于 "project" 即命中）实际语义 ≈ `**/project/**`，比 glob 直觉更宽；`.governance/**` 同理。当前源树无同名段（"software-project-governance" 为单一段，不命中），无实际 over-match。该语义为 pre-existing helper 行为，非本任务引入，但两条新 schema 条目首次依赖它。
- **建议**: 可选——在 schema reason 或 TOOLS.md 注记「豁免 glob 为段级匹配（任意层级同名段命中）」，防未来目录命名撞段。

### F-4（P3）fnmatch 大小写敏感性跨平台差异 + 豁免路径变体无直接单测
- **位置**: `verify_workflow.py:19468`（fnmatch.fnmatch 调用）；测试面缺口
- **事实**: `fnmatch.fnmatch` 在 Windows 经 normcase 大小写不敏感、POSIX 敏感——同一 schema 豁免在两平台匹配域不同。pre-existing 语义，非本任务引入；本任务新增的豁免消费面未附带路径变体（反斜杠字面、大小写、`**/` 前缀形态）单测。
- **建议**: 不阻塞；后续如做豁免语义加固可补变体参数化测试并在文档注明平台差异。

---

## 5. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | 测试用真实临时目录 + 真实扫描函数；`patch.object(vw, "GOVERNANCE_DIR")` 为隔离重定向（被测函数在真实文件上完整运行），非 mock 捷径；diff 无 MagicMock/patch 返回值伪造 |
| 2 | 硬编码返回值 | ✅ 无 | 引擎改动全部从 schema/文件系统推导；测试断言值经阈值推演可复核（§2 维度 5） |
| 3 | 幻觉 API 调用 | ✅ 无 | fnmatch/Path/ast/sys.exit/str.replace 均标准库实际存在且用法正确；逐行核对无捏造调用 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME/占位实现；「长期修复 = projection single-source」以 RISK-039 登记承接，非代码内悬空承诺 |
| 5 | 过度实现 | ✅ 无 | 改动范围与任务申报一一对应（豁免 gate + dup 豁免通道 + U+000C + 阈值 + 文档同步 + 测试），未夹带重构/新特性；diff 逐 hunk 核对无越界改动 |

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5 逐一有结论（§2） | ✅ |
| 每发现标注级别 | 100% | 4/4 标注 P2/P3（§4） | ✅ |
| 设计一致性 | 已完成 | DEC-151（豁免必披露——双面披露实现一致）、RISK-039（双写债登记——schema reason 引用一致）、G9（hooks helper 复用——未触碰）、advisory-only 边界（未改 fatal_on_error） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 有结论（§5） | ✅ |

---

## 7. 结论

**APPROVED_WITH_NOTES**（unresolved_blockers = 0）

- P0=0、P1=0；P2×1（F-1，schema note 措辞精度，可作为遗留项）、P3×3（F-2/F-3/F-4，记录备查级）。
- 核心机制（单一匹配实现 + gate 四面扩展 + dup 豁免通道 + 双面 EXEMPT 披露 + U+000C + ratchet 重锚）经逐行静态核实与申报一致；「机制不弱化」由真实负例测试双向锁定。
- 运行时验收数值（测试通过数、28o/28p 计数、七规则 PASS）本审查未复跑，维持 Developer 申报、待 Coordinator 侧验证链确认（§0）。
- 锁外两文件建议追认（§3.7）。

*Reviewer: Code Reviewer Agent · FIX-350 R0 · 只读审查，未修改被审代码，本报告为本次任务唯一写入文件。*
