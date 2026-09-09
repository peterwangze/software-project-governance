# Code Review — FEAT-011 (R0)

| 项 | 值 |
|---|---|
| Task | FEAT-011 — G3 扩展：写时结构看护引擎扩展至 Coordinator 直写路径 |
| Round | R0（首次代码审查；按 FIX-291/292 双审交错占轮先例，本报告对应 review-record `--round 1`） |
| Reviewer | Code Reviewer Agent（独立派发，只读审查） |
| 日期 | 2026-09-09 |
| 审查对象 | 工作树未提交变更相对 HEAD `1d3d973`：`skills/software-project-governance/infra/verify_workflow.py`（+399/-2）、`skills/software-project-governance/infra/tests/test_triage_write_guard.py`（+314，15 新用例）；`change_triage.py` 未改（恰当性独立判定，见 §6.4） |
| 规格源 | plan-tracker L279（FEAT-011 行）；`.governance/change-triage/FEAT-011.json`；`docs/release/version-plan-0.79.0.md` §5 #1（G3 扩展）；`docs/release/audit-149-health-noise-0.79.0.md` §4 M1；DEC-168 / DEC-172② / DEC-177① |
| **结论** | **APPROVED_WITH_NOTES**（P0=0；1×P1 + 2×P2 + 3×P3 见 §4；`unresolved_blockers=0`） |

---

## 1. 审查方法与边界

- 逐行通读全部 diff（verify_workflow.py 508 行 diff 上下文、测试 344 行 diff）及守卫依赖的全部既有权威源函数（`_governance_table_cells` L12129、`_normalize_priority` L12064、`_split_markdown_table_row` L328、`check_agent_locks_format` L16934、`_load_execution_packets` L12685、`EXECUTION_PACKET_REQUIRED_FIELDS`、`change_triage._TASK_ID_RE` L108、既有 G3 守卫 `_triage_write_structure_guard` L21654-21752）。
- 对照 HEAD（`git show HEAD:…`）核验两处去重的原实现，判定行为恒等性。
- 独立复跑全部验证命令（§2）；对「行为恒等」「SKIP 语义」「M1 边界」执行 6 组探针（只读仓库、临时目录写入，探针脚本未触碰仓库文件）。
- 只读审查：未修改任何产品代码与 `.governance/` 记录；本报告为唯一写入产物。

## 2. 回归事实独立复核（全部自跑，非转述）

| # | 事实（Developer/Coordinator 声明） | 独立复核结果 | 证据 |
|---|---|---|---|
| 1 | `governance-write-guard` exit 1，FAIL 恰为 M1 四行 7 issues | ✅ 一致：exit 1；L188 FIX-222×2 / L189 FIX-223×2 / L190 FIX-224×2 / L257 FIX-279×1（每条含行号+期望列形）；面 2/3/4 PASS；remediation 明示「守卫只检不改」 | 本机复跑输出（2026-09-09） |
| 2 | pytest test_triage_write_guard.py 30 passed | ✅ `30 passed in 0.31s`（15 既有 FIX-278 + 15 新增，方法计数核对=30） | 本机复跑 |
| 3 | test_change_triage + test_task_priority 193/193 | ✅ `193 passed in 16.13s`（change-triage 既有守卫行为零变化） | 本机复跑 |
| 4 | check-manifest-consistency / check-cross-references / check-locks PASS | ✅ 三项 exit 0（check-locks：3 文件锁在位） | 本机复跑 |
| 5 | check-governance --summary-only = 87 零新增 | ✅ `共 87 issues`（与 0.79.0 基线一致；新守卫未接入 check-governance 主链——grep 证实 `check_governance_write_shapes` 仅有 CLI 一个消费点） | 本机复跑 |
| 6 | unittest test_verify_workflow 774/775，1 失败为既有 | ✅ `Ran 775 tests … FAILED (failures=1)`；失败者 `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`（subprocess 型，`AssertionError: 0 != 1`、stderr 空）。**既有定性独立验证**：`git archive HEAD` 干净快照（临时目录，不触碰工作树）上同测试同样失败（`Ran 1 test … FAILED (failures=1)`）；工作树孤立复跑亦失败（13.0s，贴近 15s subprocess 预算）——与本任务变更无关成立 | 本机复跑 ×3 |
| — | 「TDD 红 15 failed」 | 过程性声明无工件可复核，标**未验证**；但构造性成立：15 个新用例引用 HEAD 不存在的 `check_governance_write_shapes` / `cmd_governance_write_guard`，在 HEAD 上必然全红 | 静态判定 |
| — | Developer 报告称 1 失败为「error」 | 实为 `failures=1`（AssertionError），非 error（异常）——标签差异，不影响 774/775 与既有定性 | 本机复跑摘要 |

## 3. 五维度逐项结论

### 3.1 正确性 — 通过（带 F-1 遗留）

- **M1 签名判定正确**（验收标准 1 逐项）：
  - *重复优先级列*：`prio_cells = [c for c in cells[:task_idx] if _normalize_priority(c)]`（L21812-21813）。优先级单元格界定 = 既有权威 `_normalize_priority`（strip + strip("*") 后恰为 `P0|P1|P2`）——探针实证 `**P0**`/`P1`/`**P2**` 归一化命中，`P3`/`P0/P1`/`-P1-` 不命中。>1 个即报，**每行每类型恰一条**；优先级 token 出现在任务 ID 之后不计（探针：prio-after-id → 0 issue）；3 个重复仍只报一条。与 M1 语义（重复列使任务相对列右移）吻合。
  - *行尾空单元格*：依赖既有 `_governance_table_cells` **恰丢一个**首/尾空单元格的语义——正常行 `…| ✅ 完成 |` 的结构性尾空被丢弃 → `cells[-1]` 非空 → 不报；M1 行 `…| ✅ 完成 | |` 存活一个空单元格 → `cells[-1]==""` → 报。边界答案（验收标准问）：**1 个与多个行尾空单元格均命中，每行至多报一条**（探针：one-empty→1、two-empty→1，不重复计数）。「状态列被解析为空 → 判活跃」前提成立：同一 cells 函数为 `parse_current_active_tasks` 所用，`_is_incomplete_task_status("")` 返回 True（fail-closed，L12162-12164）。
  - *扫描范围*：全文件扫描含任务 ID 单元格的表行（M1 行位于完成区 L188-190——docstring 明示且活体命中）；`---` 分隔行与无任务 ID 行跳过；表头行因无任务 ID 单元格自然跳过。活体零误报：L255（FIX-277 规范行）等未命中。
- **四面编排与 SKIP 语义**：面 1/2/4 以 `is_file()` 门控，产物缺席 → SKIPPED（非缺陷）——测试 `test_execution_packets_absent_skipped_not_failed` 覆盖面 4。**例外**：面 3 无 is_file 门控，agent-locks.json 缺席时经复用的 Check 26 语义返回 `missing` issue → FAIL 而非 SKIPPED（探针实证），与 docstring 契约「Absent files SKIP their face」及 CLI 文案「SKIPPED = 产物缺席，非缺陷」不一致 → F-2（P2）。
- **exit code 契约**：0 = 全部受检面 PASS；1 = 任一面 FAIL（`failed |= face["status"] == "FAIL"`——SKIPPED 永不置位）；活体 exit 1 复现；`test_cmd_exits_one_on_issues` / `test_cmd_clean_exits_zero` 双向覆盖。✅
- **F-1（P1）边界回归**：`_validate_execution_packet` 委托后丢失非 dict 早退（详见 §4）。

### 3.2 安全性 — 通过

- 新代码零 `eval/exec/subprocess/网络`；输入为仓库内固定治理路径（`SAMPLE_PATH`/`GOVERNANCE_DIR` 派生）；输出仅 stdout + exit code。
- 无敏感数据、无凭据；issue 消息以 `.format` 拼接解析出的单元格文本（如优先级单元格列表）——仅控制台展示，无注入面。
- OWASP 关键项（输入校验/注入/敏感数据/权限）逐项扫描：新代码面无适用违规。

### 3.3 可维护性 — 通过

- **单一事实源达成度高**（FEAT-011 核心主张）：面 1 复用 `_governance_table_cells`+`_normalize_priority`+`_TASK_ID_CELL_RE`；面 2 复用 `_split_markdown_table_row` + `change_triage._TASK_ID_RE`（惰性 import）；面 3 整体复用 `check_agent_locks_format`（Check 26，无第二 schema）；面 4 复用 `EXECUTION_PACKET_REQUIRED_FIELDS` 表。注释显式引用 FIX-292 双源教训。**守卫确无第二套形状定义** ✅（唯一偏差是 F-1 的委托分支行为，属复用实现瑕疵而非双源）。
- 函数职责单一：三个纯函数（face 1/2 均 docstring 声明 Pure: no I/O）+ 一个编排函数 + 薄 CLI 入口（RISK-039 thin-entry 纪律，argparse glue + printing only）。
- 函数长度：`check_governance_write_shapes` 约 130 行但为四面顺序编排、每面独立成块，可读性良好；face 函数均 <65 行。
- F-4（P3）：测试文件 docstring 将面 4 权威源表述为「Check 18c `_validate_execution_packet`」，实际消费的是共享 helper `_execution_packet_field_issues`（语义正确——字段表单源；措辞宜指向 helper）。F-5（P3）：face 2 col-mismatch issue 的 `task_id` 字段用 `split("|")[1]` 提取，与 row_id 提取（切片法）是同一单元格的两条解析路径（行为等价，风格瑕疵）。

### 3.4 性能 — 通过

- 面 1/2 为 O(行数) / O(行数×2族) 线性扫描；`family_standard` 字典缓存行族标准，无重复全文件扫描。
- 守卫为独立子命令，未接入 check-governance 主链（§2 #5 证据：87 零新增、墙钟无感知变化）；`from change_triage import _TASK_ID_RE` 惰性导入仅在面 2 执行时发生。
- 无 N+1 / O(n²) 以上算法；无循环内 I/O（每文件恰一次 read_text）。

### 3.5 测试覆盖 — 通过（带 F-3 补强建议）

- 15 新用例覆盖：面 1（3 合成 + 1 活体金丝雀——金丝雀用 `issubset(_KNOWN_M1_IDS)` + 非空双断言，同时防误报扩散与漏报）、面 2（4：合法/列破坏/ID 破坏/EVD 手工混合不误报）、面 3/4（4：合法/锁字段缺失/包字段缺失/缺席 SKIP）、CLI（2：exit 1 / exit 0）、非破坏性（1：`test_guard_writes_nothing`）。
- **`test_guard_writes_nothing` 断言强度充分**（验收标准 3）：对治理目录**全部文件**做 `name→bytes` 字典前后相等断言——同时覆盖内容改写（字节不同）、新增文件（after 多键）、删除文件（after 少键）三类写入；被测函数为 `check_governance_write_shapes`（全部面的载体）。守卫只检不改在活体亦间接验证（本审查多次复跑后 `git status` 仍仅原有 2 个 M 文件）。
- F-3（P2）补强缺口：RECO 族列数破坏无用例（仅 TRIAGE 有）；面 3 缺席→FAIL 分支无用例（正因缺测试，F-2 未被开发期发现）；面 1/2 unreadable 分支无用例；exit-0 测试中四产物齐全，SKIPPED 面经 CLI 不影响 exit 0 的路径未单独走通。

## 4. 发现清单

| # | 级别 | 位置 | 事实 | 影响 | 修复建议 |
|---|---|---|---|---|---|
| F-1 | **P1** | `verify_workflow.py` L12726-12728（`_validate_execution_packet`） | HEAD 原实现对非 dict 包早退 `return ["packet must be object"]`；新版委托 `_execution_packet_field_issues` 后**无条件**执行 `packet.get("task_id")`。探针实证：str/list/int 包 → `AttributeError: … object has no attribute 'get'`。可达路径：`check_execution_packets` L13832-13844（active P0/P1 任务的 packet 值为非 null 非对象）→ Check 18c（L14873，无 try/except 包裹）→ `check-governance` 整体 traceback 崩溃。face 4 守卫路径不受影响（直接调 helper，helper 自身处理非 dict，探针 PROBE1b = `['packet must be object']`） | 畸形 execution-packets.json 下 Check 18c 由「优雅 FAIL + 结构化 issue」退化为「命令崩溃」；「Check 18c 委托后输出字节恒等」声明在该分支**不成立**（dict 分支恒等，PROBE2 逐项一致）。崩溃为响亮失败（非静默误判），且当前仓库数据完好不可触发，故不定 P0 | 委托后恢复早退：`issues = _execution_packet_field_issues(packet)` 之后加 `if not isinstance(packet, dict): return issues`（一行，恢复 HEAD 恒等）；补一条非 dict 包的 Check 18c 回归用例 |
| F-2 | **P2** | `verify_workflow.py` L22000-22017（face 3）+ L21917-21919 docstring + L22225 CLI 文案 | 面 3 无 `is_file()` 门控；agent-locks.json 缺席时 `check_agent_locks_format()` 返回 `[{"type":"missing",…}]` → face 3 = **FAIL**（探针实证 `status=FAIL, issues=['.governance/agent-locks.json not found…']`）。docstring 契约「Absent files SKIP their face」与 CLI「SKIPPED = 产物缺席，非缺陷」对面 3 不成立；result 初始化的 `"agent_locks": {"status":"SKIPPED"}` 为不可达死值 | 未启用锁文件的宿主运行守卫将得到 exit 1，把「产物缺席」误呈现为「结构破坏」；四面 SKIP 语义不对称（1/2/4 SKIP、3 FAIL） | 二选一：(a) 面 3 加 `locks_path.is_file()` 门控与面 1/2/4 对齐（推荐——语义统一）；(b) 修订 docstring/CLI 文案与 expected 字段，明示「locks 缺席 = FAIL（治理初始化强制项）」为有意例外。 whichever 需补面 3 缺席分支用例 |
| F-3 | **P2** | `tests/test_triage_write_guard.py`（新增 4 类） | 覆盖缺口：RECO 族列数破坏、面 3 缺席分支、面 1/2 unreadable 分支、SKIPPED 面下的 CLI exit-0 均无用例（F-2 即因缺口未在开发期暴露） | 后续守卫演化时上述分支回归不可测 | 随 F-1/F-2 修复补 4 条用例；其余为可选补强 |
| F-4 | **P3** | `tests/test_triage_write_guard.py` L20-22 模块 docstring | 面面 4 复用权威表述为「Check 18c `_validate_execution_packet`」，实际消费 `_execution_packet_field_issues`（字段表层）——语义主张（不自建第二套字段定义）成立，指称不精确 | 文档误导后续维护者到含语义检查的外层函数 | docstring 改指 `_execution_packet_field_issues`（EXECUTION_PACKET_REQUIRED_FIELDS 单源） |
| F-5 | **P3** | `verify_workflow.py` L21827-21829（face 2 col-mismatch `task_id` 提取） | 同一行 ID 单元格存在两条解析路径：`split("|")[1].strip()`（col-mismatch 用）与切片法（ID 格式检查用）——行为等价 | 风格瑕疵；解析演进时两处需同步 | 统一为同一提取（如复用 row_id 变量） |
| F-6 | **P3** | `tests/test_triage_write_guard.py` `_clean_gov` | 直接实例化另一 TestCase 类（`GovernanceWriteGuardLocksAndPacketsTests()._result(…)`) 复用 helper | 测试间隐式耦合；helper 提升为模块级函数更稳 | 可选：提取模块级 `_make_clean_gov(td)` |

**P0 计数 = 0**；P1 = 1（F-1）；P2 = 2（F-2/F-3）；P3 = 3（F-4/F-5/F-6）。

## 5. 设计一致性核验（硬门槛 3）

| 契约 | 核验结论 | 证据 |
|---|---|---|
| 与 FIX-278 G3 既有守卫的扩展关系（零行为变化） | ✅ diff 对 `_triage_write_structure_guard`（L21654-21752）**零行修改**，全部新增代码追加于其后；既有 15 个 FIX-278 用例全绿（30/30 的一部分）；face 2 与 write-guard 同用 `_split_markdown_table_row` 计数（「same counting」声明属实）；write-guard 的行族标准排除写入行、face 2 全文件扫描取首行——两者角色不同（写时 vs 库态）且声明如实（"whole-file extension"） | diff hunk 边界 + 测试复跑 |
| DEC-168（TRIAGE 行族列数权威） | ✅ face 2 采「行族首行确立标准」而非硬编码 10 列，与 DEC-168 裁定（行族自身为标准最自洽）及既有 write-guard 实现（首个非写入 TRIAGE 行）同构；活体 TRIAGE 62 行×10 列、RECO 40 行×10 列全均匀 → 面 2 PASS 零误报；EVD 手工混合明确排除列数强制（Check 14 WARN 域，测试覆盖） | 活体扫描 + DEC-168 原文 |
| Check 26 复用边界 | ✅ 面 3 整体复用 `check_agent_locks_format`，issue 以 `agent_locks_{type}` 前缀透传、expected 字段描述 schema——无第二 schema 定义。唯一张力即 F-2（缺席语义继承 Check 26 的 issue 而非 SKIP） | L22000-22017 |
| Check 18c 复用边界 | ✅ 面 4 复用 `_execution_packet_field_issues`（字段表单源）+ `_load_execution_packets`（JSON/root 形状）；语义检查（task_id 匹配/scope 广度/evidence 措辞）正确留在 Check 18c——「write guard judges STRUCTURE, not task semantics」边界如实。**例外**：F-1（委托分支行为回归） | L12726-12741 + L22044-22080 |
| FEAT-011 任务边界（不修数据——FIX-293 域） | ✅ 守卫零写路径、零自动修复；消息明示「修复动作留给写入者，本守卫只检不改」；M1 四行仍原样留存（待 FIX-293）；plan-tracker L278 FIX-293 行明确引用 FEAT-011 为「写时看护——防新增不治存量」 | 守卫活体输出 + plan-tracker L278 |
| 变更范围 vs triage 记录 | ✅ 实改文件 ⊆ `files` 声明（verify_workflow.py + 测试；change_triage.py 声明而未改——见 §6.4）；无目标外顺带修改（git status 仅 2 文件） | git diff --stat |

## 6. 验收标准逐项裁决

1. **守卫正确性** — ✅（§3.1）：M1 两签名判定边界逐项核验（优先级界定=`_normalize_priority` 权威、`**P0**`/`**P1**` 归一化命中、行尾空 1/多个均报且每行一条）；四面 SKIP 语义面 1/2/4 成立、面 3 见 F-2；exit 0/1/SKIPPED 契约成立。
2. **复用真实性** — ⚠️ 部分成立：`_TASK_ID_CELL_RE` 恒等 ✅（模式串与 HEAD 逐字节同、`re.match`→`compiled.match` 语义同）；`_execution_packet_field_issues` dict 分支恒等 ✅（PROBE2 issue 序列逐项同 HEAD）、**非 dict 分支不恒等**（F-1）；守卫无第二套形状定义 ✅。
3. **非破坏性** — ✅：零写路径（代码面 + `test_guard_writes_nothing` 字节级断言 + 活体复跑无新变更）。
4. **5 维度 + 发现分级 + AI 专项** — ✅（§3 / §4 / §7）。
5. **回归事实复核** — ✅ 全部独立复现（§2），含 774/775 既有失败的 HEAD 干净快照独立定性（git archive 法，独立于 Developer 的 stash 法）。
6. **结论** — APPROVED_WITH_NOTES（§8），含独立字段 `unresolved_blockers=0`。

### 6.4 `change_triage.py` 不改动的恰当性 — **恰当，独立判定成立**

- (a) FEAT-011 四面全部针对 **Coordinator 直写产物**；change_triage 自身写入路径已有 FIX-278 G3 write-guard（本次零触碰、15 既有用例全绿）——扩展而非重写的主张与实现一致。
- (b) TRIAGE 行 ID 格式权威 `_TASK_ID_RE`（L108，`^[A-Z]+-\d+$`）经惰性 import 复用（L21863），零第二定义——正因复用可用，无需改动 change_triage.py。
- (c) DEC-168 裁定列数权威 = **行族自身**（evidence-log 内首行），非写入器代码常量——在 change_triage.py 落列数常量反而违背 DEC-168。
- (d) RECO 行权威写入器 `_snapshot_evidence_row` 在 verify_workflow.py 自身（L21316-21365，`RECO-{task}` 10 列）——face 2 契约与写入器格式逐字一致（活体 40 行核验）。

## 7. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无——新生产代码零 mock/测试桩（hygiene grep 空结果）；测试内 `mock.patch` 全部 with 作用域即撤 | grep + 逐行 |
| 2 | 硬编码返回值 | ✅ 无——全部判定来自解析结果/复用检查器输出；期望列形字符串是消息文本而非判定逻辑 | 逐行 |
| 3 | 幻觉 API 调用 | ✅ 无——新代码引用的 9 个符号全部定位存在（§1 列表，含行号）；subparser 注册（L23712）与命令表注册（L23809）双点核验，活体命令可执行 | grep + 活体运行 |
| 4 | 未实现 TODO | ✅ 无——新代码区（L21754-22068）TODO/FIXME/XXX/NotImplemented 零命中 | grep |
| 5 | 过度实现 | ✅ 无——四面均为规格所列（version-plan §5 #1 / audit-149 §4 M1 / DEC-168 / Check 26 / Check 18c 字段表）；无自动修复、无额外检查面、CLI 遵守薄入口纪律；数据修复正确留给 FIX-293 | 规格比对 |

## 8. 硬门槛裁决与结论

| 门槛 | 阈值 | 裁决 |
|---|---|---|
| P0 阻塞问题数 | = 0 | ✅ 0（F-1 为边界条件未处理，按 SKILL 分级属 P1——触发需畸形输入、失败模式为响亮崩溃非静默误判、守卫主路径不受影响） |
| 5 维度全覆盖 | 100% | ✅ §3.1-3.5 逐一有结论 |
| 每条发现标注级别 | 100% | ✅ §4 六条全部带 P 级 + 位置 + 事实 + 影响 + 修复建议 |
| 设计一致性检查 | 已完成 | ✅ §5 六项逐条比对 |
| AI 专项 5 项 | 全部完成 | ✅ §7 |

### 结论：**APPROVED_WITH_NOTES**

- `unresolved_blockers=0`
- 通过理由：四面守卫核心逻辑正确、活体零误报精确命中 M1 四行、复用主张（无第二形状定义）成立、非破坏性有字节级测试与活体双重证据、全部回归事实独立复现、`change_triage.py` 不改动恰当。
- MUST 处理的 notes（合并前或紧随其后，均不阻塞）：**F-1（P1）一行修复恢复非 dict 早退 + 补回归用例**（「行为恒等」声明在修复前对该分支不成立，Developer 报告中的恒等表述应随修复更正）；F-2（P2）面 3 缺席语义二选一收敛 + 补用例；F-3/F-4/F-5/F-6 为补强/整洁项。
- 本结论仅为代码审查门通过，不替代测试审查与发布审查（FEAT-011 闭环路径要求 Code + Design 双审）。

## 9. 事实依据索引

- diff：`git diff HEAD -U6`（verify_workflow.py 508 行 / test_triage_write_guard.py 344 行，落盘 `%TEMP%\feat011_{verify,test}.diff`）
- HEAD 对照：`git show HEAD:skills/software-project-governance/infra/verify_workflow.py`（`_validate_execution_packet` 原实现早退实证）
- 活体命令输出：`governance-write-guard`（exit 1 / 7 issues）、pytest 30/30、193/193、三 gate PASS、check-governance 87、unittest 775 ran failures=1
- HEAD 既有定性：`git archive HEAD` 临时快照单测复现 FAILED (failures=1)
- 行为探针：非 dict 包 ×3（AttributeError）/ helper 安全 / dict 包 issue 序列 / 面 3 缺席 FAIL / 行尾空 1-2 个边界 / 优先级归一化 ×6 / dup-priority 边界 ×2（探针脚本 `%TEMP%\feat011_probe.py`，未触碰仓库）
- 活体数据：TRIAGE 62 行×10 列、RECO 40 行×10 列（`Select-String` 列计数）；plan-tracker L188/189/190/257/255 原文
- 规格原文：plan-tracker L279 / FEAT-011.json / version-plan-0.79.0.md §5 #1 / audit-149 §4 M1 表 / DEC-168 / DEC-172② / DEC-177①
