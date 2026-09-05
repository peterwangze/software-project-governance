# FIX-282 Code Review R0 — DEC-171 commit-msg Step 3 匹配缺陷修复（正则容忍加粗任务行）

- **Task ID**: FIX-282（P2，0.78.1；DEC-171 + DEC-173① + REL-073）
- **审查者**: Code Reviewer Agent（Role: `agents/code-reviewer.md`；SKILL: `skills/code-review/SKILL.md`）
- **轮次**: **R0**（首审；无前轮）
- **审查日期**: 2026-08-28（Reviewer 无时钟访问，以最近治理记录日期为参考；Coordinator 可补记）
- **被审查变更**（工作树未提交改动，审查对象 3 文件）：
  1. `skills/software-project-governance/infra/hooks/commit-msg`（+30/-1：新增 `task_in_plan_tracker()` + Step 3 调用替换；改动区域 = L71-93 注释+函数、L257-268 Step 3）
  2. `skills/software-project-governance/infra/tests/test_hooks.py`（新建，292 行：12 语义用例 + 3 bash parity 用例 + 提取/等子集守卫机制）
  3. `.git/hooks/commit-msg`（重装目标，声称与源 SHA256 一致）
- **诚实披露**: 本审查者按角色约束未运行 Bash/git（read/grep/glob 只读）。git 级 diff 未跑——diff 以任务书注入 + 工作树逐行 Read 核实（hook 全文 535 行确认仅上述两个改动区域，其余为既有代码）；Developer 自报测试结果（pytest 15 passed + 11 subtests、真实 plan-tracker 三态实测、verify/xref/manifest PASS、全量 26 failed 均既有 bash/WSL 基线）未复跑，标为自述。

---

## 0. 审查结论

> **Review 结论：APPROVED_WITH_NOTES**
> **结构字段：`unresolved_blockers=0`**（无未解决 BLOCKING finding；P0=0、P1=0、P2=4、P3=6，见 §4）

**总评**：修复方向与 DEC-171 ②（容忍加粗，正则 `\| \*\*P\d\*\* \| \*\*REL-071\*\*` 形态）一致，且实现为方向内的一般化（优先级列/ID 列均可粗可素）；注入面经 Step 1 提取形态核实为零；`[|]/[*]/[0-9]` 等子集构造在 grep-ERE / POSIX ERE / Python-re 三引擎语义已知等价；测试绑定机制（从 hook 源提取字面量）在提取失败路径是 fail-closed（raise → 测试 ERROR），非静默跳过；Step 3 集成钉住（新调用存在 + 旧字面量禁回归）；`.git/hooks/commit-msg` 与源经全量 Read 逐行比对一致（SHA256 未独立计算，见 §7）。阻塞级问题零。四项 P2 均为「语义收紧披露/布局假设文档化/测试韧性/跨 hook 同型登记」类，不阻塞本任务合并，但建议 Coordinator 对 P2-1/P2-2 作显式裁定入 DEC。

---

## 1. 5 维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | 逐 token 推演 ERE（hook L92）对 8 类行形态：加粗 P+加粗 ID（`\| \*\*P1\*\* \| \*\*REL-071\*\* \|`，plan-tracker L258 实测形态）、加粗 P+素 ID（L264 FIX-282 形态）、全素（L265 FIX-283 形态）、缺行 MISS（`FIX-9999` 无行）、描述列提及 MISS、第三列裸 ID MISS、非任务表行（G1）MISS、部分 ID（`FIX-2822`）MISS——尾随 `[*]{0,2} *[|]` 保证 ID 后仅允许星号/空白/管道，无子串误放行；CRLF 行尾 `\r` 不影响 `*[|]`；LC_ALL=C 字节模式下 CJK 字节与 ` `（0x20）/`[|]`（0x7C）不重叠。函数在 `set -e` 下经 `if !` 调用，退出码传导正确 |
| 安全性 | ✅ 通过 | 注入面关闭：TASK_ID 源（hook L239）`grep -oE '^[A-Z]+-[0-9]+'` 输出仅 `[A-Z]+-[0-9]+`，ERE 元字符零（`-` 在类外为字面量，三引擎一致）；`${task_id}` 拼入 ERE 无注入面；`[ -f ]` 与 grep 的 plan_file 路径均有引号；`2>/dev/null` 不回显文件内容；无真实环境写操作 |
| 可维护性 | ✅ 通过（P3×3 观察） | 函数单一职责、5 行；注释 17 行且事实引证逐条准确（DEC-171/afb959d/M7.5 均已核实——见 §3-6）；测试文件分层清晰（提取/守卫/语义/parity/replay）。⚠️ 观察项见 P3-A/B/D |
| 性能 | ✅ 通过 | 每 commit 一次线性单行 grep（253KB 文件），与旧字面量同量级，无 N+1、无二次扫描 |
| 测试覆盖 | ✅ 通过（含 P2-3 韧性观察） | 15 用例 + 11 subtests（12 语义 + 3 bash parity；subtests = mixed 3 + replay 6 + parity 2，与 Developer 自报计数结构一致）；覆盖 HIT 三形态/MISS 四类型/集成钉住/等子集守卫/双引擎 parity。⚠️ live replay 对未来数据变迁脆弱——见 P2-3 |

---

## 2. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | hook 零 mock；测试用真实 subprocess（`bash -s`）+ tempfile，无 `unittest.mock` 导入；`_BASH=None` 仅为 skip 信号非 mock 替身 |
| 2 | 硬编码返回值 | ✅ 无问题 | 测试断言全部由 hook 源提取的真实字面量模式驱动（`_pattern_for` ← `_extract_pattern(_extract_function(...))`，test_hooks.py:49-69）；fixture 行（:191-211）为按真实形态构造的数据，非返回值 |
| 3 | 幻觉 API | ✅ 无 | 仅标准库 re/shutil/subprocess/tempfile/unittest/pathlib；`_find_bash` 候选路径为常见 git 安装路径（:118-122）；无虚构 API 调用 |
| 4 | 未实现 TODO | ✅ 无 | test_hooks.py 全文逐行读，零 TODO/FIXME/pass 占位；docstring 完整（:1-30） |
| 5 | 过度实现 | ✅ 无（P3 观察） | 292 行测试 + 17 行注释对 5 行函数属重比例，但绑定要求（从 hook 源提取字面量——FIX-282 任务书绑定要求）+ 等子集守卫 + 双引擎 parity = 分层防护网设计，且本项目 P4 原则（测试看护）背书；无可删冗余抽象。若后续成本敏感，可裁剪层为 parity/replay（P3-B/F 相关），非本任务义务 |

---

## 3. 重点审查项 1-8 逐项核实

### 3.1 语义收紧边界 — ⚠️ 方向内收紧成立，但有副作用未披露（P2-1）
- **(a) 漏匹配核查**：任务表当前全部行均为「首列 P{n}（可加粗）+ 第二列 ID」形态——实测：L76 表头 `| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |`；L230-271 活动行 40+ 行逐行为 `| **P{n}** | ID | ...`（P0-P2，ID 列粗/素混合：L258 `**REL-071**` 加粗、L254/264/265/270 素）；L273-283 最近完成段同形态；L287-301 归档指针段为 `| — | FIX-082 | ...`（首列 `—`，见下）。
- **发现（P2-1 主体）**：plan-tracker 中存在两类合法携带任务 ID 但首列非 P{n} 的表行：(1) 需求跟踪矩阵（L531-622）：`| REQ-002 | ... | P0 | ... |` 首列 REQ-id——**旧字面量 `| REQ-002 |` 命中（首列即为 ID），新 matcher MISS**；(2) 归档指针行（L294-301）：`| — | FIX-082 | ... |`——旧字面量命中，新 matcher MISS。语义影响：**引用需求矩阵行首列 ID（REQ-*）或归档指针 ID 的 commit，Step 3 由「放行」变「阻止」**。这是「防误放行 vs 误拒」权衡中**方向正确的收紧**（内容列/裸单元格不再算任务存在；test_mention_in_description_cell_misses / test_id_in_third_column_misses / test_non_task_table_row_misses 明确钉住该意图），且对当前本仓工作流零影响（FIX-282~289/REL-073 全部 P-first 行，实测 HIT 形态成立）。
- **(b) 方向判定**：DEC-171 ②原文「匹配改为容忍加粗（正则 `\| \*\*P\d\*\* \| \*\*REL-071\*\*` 或去 markdown 加粗后匹配）」——实现为该正则的一般化（P 列/ID 列均可粗可素、容空白），属**方向内**；锚定首两列为任务行结构亦与 M7.5 任务条目形态（behavior-protocol.md L599-602：条目须含 ID + 优先级级别）一致。收紧本身不构成违反，但**REQ-*/指针行从「通过」变「阻止」的副作用在评审上下文与 hook 注释中均未显式披露**——建议 Coordinator 裁定并以 DEC 落档「Step 3 存在性 = 任务表 P-first 行」，另补 REQ 行/指针行 MISS 锚点测试钉住边界（防未来静默回退成字面量）。
- **级别**: P2-1（非阻塞；方向正确，披露/测试钉界缺失）。

### 3.2 ERE 可移植性 — ✅ 静态论证通过（运行未验证）
- 构造分解：`^ *` / `[|]` / `[*]` / `[0-9]` / `*` / `+` / `{0,2}` / 字面量——全部落在 POSIX ERE 与 Python-re 的共同子集；`[*]{0,2}` = 字面星号类 + 区间量词，GNU grep -E（git-bash/WSL 主路径）与 BSD grep -E 均支持区间；无 `\` 转义、无 POSIX `[:class:]`、无 `\d`/`\s`（LC_ALL=C 环境亦无 Unicode 类需求——`[0-9]` 在 C 字节模式恒为 ASCII 数字，与 Python 语义一致）。
- `LC_ALL=C` 强制字节模式：pattern 内仅 ASCII，与 plan-tracker UTF-8/CJK 内容无字节碰撞（` `（0x20）、`|`（0x7C）、`*`（0x2A）、`P`（0x50）、数字——均不落在 CJK 高位字节区间），结果 locale 无关（对齐 FIX-239 既有结论）。
- 残余风险：BusyBox grep -E 的 `{m,n}` 支持**未验证**（hook 运行环境 = git-bash/WSL/native bash，均非 busybox 主路径；若部署到 busybox 嵌入式宿主需实测）；`[0-9]` 在非常规 locale 下与 Python 的 `re`（Unicode 数字）有理论差异——但 `[0-9]` 在 Python rel 中仅匹配 ASCII，一致。
- **级别**: 观察级（P3-E 部分），不阻塞。

### 3.3 注入安全 — ✅ 零注入面
- 核实：hook L239 `TASK_ID=$(echo "$FIRST_LINE" | grep -oE '^[A-Z]+-[0-9]+' || true)`——`-o` 仅输出匹配子串；锚定 `^` 且 `[A-Z]+-[0-9]+` 无元字符（`-` 类外字面量）。`${task_id}` 拼入 ERE 的字符集 = `[A-Z0-9-]`，安全。
- Step 2 空值门控（L242-255）在 Step 3 之前，`${task_id}` 不可能为空串变形。
- hook 注释 L82 的声明「so it contains no ERE metacharacters」与实现一致，非幻觉。
- **级别**: 通过。

### 3.4 测试绑定真实性 — ✅ 提取失败 fail-closed；跳过仅环境降级（P3-B 观察）
- 提取机制：`_extract_function`（:49-55）找不到函数体 → `raise AssertionError`（**测试 ERROR，非 skip**）；`_extract_pattern`（:58-64）找不到 `grep -Eq "..."` → 同样 raise；`_pattern_for`/`_run_pattern`（:67-99）驱动调用链任一步失败即失败——**提取失败 = fail-closed 成立**。
- 静默跳过仅两处，均非提取失败：`:265 @unittest.skipUnless(_BASH, ...)`（无功能 bash → BashParityTests 整体跳过——会话/CI 无 git-bash/WSL/native 时双引擎 parity 降级为单引擎 Python-re + 等子集守卫（:78-88 正是为此设的哨兵））；`:255-256 skipTest`（live `.governance/plan-tracker.md` 不可用——离线跑包场景）。两跳过的语义 = 环境降级而非防护网失效：核心语义断言（12 用例）不依赖 bash 始终运行。
- 双引擎 parity 实质断言强度：`test_bash_hits_bold_and_plain_rows`（:270-277）对同 fixture 同时断言 bash 函数结果与 Python-re 结果（双断言），`test_bash_misses_absent_task`（:279-283）双断言 MISS；`_run_bash_function`（:140-171）对非常规输出（WSL 无发行版 stub 等）**raise 而非静默 False**——parity 用例非口水断言。强度合理。
- **级别**: 通过（P3-B 观察：`_FN_RE`/`_PATTERN_RE` 对函数体格式敏感——首个 `grep -Eq`、`^}` 行首收括；未来 hook 编辑可能使提取静默改绑，建议后续固化为锚点注释或断言）。

### 3.5 安装面闭环 — ✅ 内容一致性成立（SHA256 未独立计算）
- 全量 Read 比对：`.git/hooks/commit-msg`（535 行）与源 `skills/.../hooks/commit-msg`（535 行）逐行一致——含 L92 新 matcher 行、L263 新调用行、L258-262 新注释；无遗漏/差异。
- 双重保障：hook Step 0 自升级（L203-210）在下次 commit 时 `cmp -s` 不一致即自抄源并重启——即使未来漂移亦自愈；但本审查断言「本次安装面闭合」以当前工作树 Read 内容为准。
- SHA256 声明未独立复核（角色禁 Bash；Read 级一致性为可复查事实）。
- **级别**: 通过。

### 3.6 范围纪律 — ✅ 严格限于改动区域（git 级未跑，静态核实）
- 工作树全文核实：hook 源 535 行中，新增内容 = L71-93（注释 17 行 + `task_in_plan_tracker()` 5 行）与 L257-262 注释 + L263 调用替换；其余 L1-70/L94-256/L264-535 为既有代码，零顺带修改。与注入 diff（+30/-1）算术吻合（23 行注释函数 + 7 行 Step 3 注释/调用 − 1 行旧调用）。
- 注释-代码一致性：L82「Task_ID comes from Step 1's extraction (^[A-Z]+-[0-9]+)」核实（L239）✅；L74-76「pre-FIX-282 literal never matched bold-ID rows… REL-071's M-5 transition commit (afb959d) had to bypass via --no-verify (DEC-171)」核实（decision-log L180 + plan-tracker L258 实测加粗行）✅；L79-81「M7.5 semantics preserved」核实（behavior-protocol.md L574-602 任务前协议 + test_absent_task_misses 行为）✅；L85-87 等子集声明与实现一致（pattern 全字符 ∈ `[0-9A-Za-z ^#${}\[\]|*,.+()?%_-]`）✅。零注释幻觉。
- **级别**: 通过。

### 3.7 AI 专项 — 见 §2（5/5 结论齐全；无 mock 残留/硬编码/幻觉 API/TODO；分层防护非过度实现）

### 3.8 post-commit L172 同型缺陷（边缘上报核实）— ⚠️ 陈述属实，级别建议 P2（仅登记建议）
- 核实：`skills/.../hooks/post-commit` L172：`if ! grep -q "| $TASK_ID |" ...`——与修复前 commit-msg 同字面量；其上下文（L171-177）为 **WARN-only**（`echo "⚠️ ..."` 后事件继续，无 `exit 1`）——**阻断面无影响，噪声面有影响**：加粗 ID 行（未来所有任务行均可能加粗）提交后将稳定产生「Task not found in plan-tracker」误 WARN；且描述列裸 ID 的漏报（该 WARN 形如「未登记」却未核对列位）仍依赖列位。
- 全仓 grep 确认：`| $TASK_ID |` 字面量现存于 post-commit L172 仅此一处（commit-msg L74/L258 为注释中引述）；pre-commit/prepare-commit-msg 无同型阻断检查（pre-commit 无任务存在性步骤——Step 3 唯一承载点 = commit-msg，修复面完整，无遗漏阻断路径）。
- **级别建议**: P2（登记 0.78.x 后续批次：post-commit Step 3 换用同一 tolerant matcher 或去粗归一匹配；WARN-only 不构成紧急同修必要性）。

---

## 4. 发现列表（P0=0 / P1=0 / P2=4 / P3=6，均非阻塞）

### P2-1 — 语义收紧副作用未披露：REQ-* 需求矩阵行与归档指针行不再满足 Step 3
- **位置**: hook L88-93（matcher 锚定）+ plan-tracker L531-622（需求矩阵首列 REQ-id）+ L294-301（归档指针首列 `—`）
- **事实**: 旧字面量 `| $TASK_ID |` 列位无关，REQ-002 / FIX-082 等首列/次列裸 ID 均命中；新 matcher 要求首列 `P{n}`——上述两表行全部 MISS。当前本仓活动任务（FIX-282~289/REL-073）均 P-first 行，零实际阻断；但该行为变化未在任何评审上下文/注释/测试中显式声明。
- **影响**: 引用 REQ-*（ADR-009 合法前缀，behavior-protocol L586）或已归档 ID 的 commit 将被 Step 3 阻止（fail-closed 方向，安全侧）；宿主项目中「需求先行 commit」习惯将被强制转变为「任务表注册后 commit」。
- **建议**: Coordinator 裁定并以 DEC 落档「Step 3 任务存在性 = 任务表 P-first 行」；补 REQ 行/指针行 MISS 锚点测试（与 test_non_task_table_row_misses 同型，防静默回退）；hook 注释补一句边界说明。

### P2-2 — 布局假设未文档化：matcher 仅支持「首列优先级」金规格任务表
- **位置**: hook L92 + `core/templates/plan-tracker.md` L51（`| 优先级 | ID | 任务项 | 依赖 | 目标版本 | 状态 |`）+ verify_workflow.py:13799-13803（lightweight=6/standard=20/strict=20 均优先级在前）+ archive.py:1309（legacy 10-col `| 任务ID | 描述 | 优先级 | ...`）/archive.py:2089（旧 21-col `| ID | 阶段 | ... | 优先级 | ...`）
- **事实**: 当前模板与三档 profile 的任务表均「优先级列在前 + ID 列第二」——matcher 假设成立（本仓实测 L76 表头一致）。但历史/旧宿主格式（10-col、21-col）为 **ID 首列**：旧字面量（列位无关）对它们可正常命中，新 matcher 对 ID-first 任务表行全体 MISS → 该类宿主升级后 Step 3 全阻断。
- **影响**: 仅影响未迁移旧布局的宿主；本仓零影响；方向与 DEC-171 指定锚定形态一致，但「旧布局宿主行为变化」未评估未披露。
- **建议**: 二选一——(a) 文档化「支持范围 = 当前模板布局（优先级首列）」并转 Record/发布审查确认；(b) 如需兼容旧布局，补 ID-first 分支（首列 ID + 次列任意/第三列 P）——扩界需 Coordinator 授权。默认推荐 (a)+处置说明记录。

### P2-3 — `test_replay_real_plan_tracker_hits` 耦合易变 live 数据，预期未来必红
- **位置**: test_hooks.py:251-262
- **事实**: 硬编码 ID 集（REL-071/REL-072/FIX-282/REL-073/FIX-283/FIX-288）断言实时 plan-tracker 命中；本仓 plan-tracker 253KB + archive index 存在且已发布版本 ≥2——下一次归档迁移（发布强制/数据量触发，bootstrap Step E）会把完成态任务行迁出热文件，届时这些 ID 行消失 → 该用例必 FAIL（当前通过依赖「任务行尚未归档」的临时状态）。
- **影响**: 场景化防护网随治理数据生命周期衰减（S3 转 S1 类），与本项目「防护网不因数据演化而失效」原则张力。
- **建议**: 改为动态提取（解析 real plan-tracker 任务表所有现存 ID → 各断言 HIT + FIX-9999 MISS），或收窄为「任一现存 P-first 行 ID HIT + 恒缺 ID MISS」；非阻塞。

### P2-4 — post-commit L172 同型字面量（登记建议，见 §3-8）
- **位置**: infra/hooks/post-commit:172
- **事实**: 同字面量（WARN-only）——加粗 ID 行将误报「Task not found」噪声；描述列裸 ID 漏报。
- **建议**: 登记 0.78.x 后续批次统一 tolerant matcher；本任务范围外不处理。

### P3-A — 注释篇幅（17 行对 5 行函数）
- **位置**: hook L71-87。事实内容逐条核实准确（§3-6），风格上属重注；建议未来维护时若有功能改动随批精简。观察级。

### P3-B — 提取正则对函数体格式敏感
- **位置**: test_hooks.py:45-46。`_FN_RE` 依赖 `^}` 行首收括、`_PATTERN_RE` 取首个 `grep -Eq "..."`——hook 函数体格式变化（缩进/新增 grep）可能使提取改绑或漂移；建议后续加锚点断言（如函数名+`LC_ALL=C` 同现断言已有 `assertIn("grep -Eq", fn)`，可再加 `assertIn("LC_ALL=C", fn)`）。

### P3-C — `_run_bash_function` 路径 repr 双反斜杠/cygpath fallback 无测试
- **位置**: test_hooks.py:152-161。Windows 路径 `{0!r}` 插入脚本后 REPO_ROOT 为双反斜杠字面量——git-bash 下经 CRT 归一化可行（Developer 自报 parity 通过佐证），WSL/native 无此问题；`cygpath -u` 回退分支未在任何测试路径被覆盖。可移植性观察，未独立执行验证。

### P3-D — 测试 fragment 表头与真实表头非逐字
- **位置**: test_hooks.py:104-109（`| 优先级 | 任务 ID | 任务描述 | 依赖 | 版本 |`）vs 真实 L76（`| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |`）。matcher 为结构匹配不依赖列名，语义等价；如需保真度可改用真实表头（非阻塞）。

### P3-E — 等子集守卫允许集过宽/过严边角
- **位置**: test_hooks.py:78。允许 `$`/`#`/`%`/`?`/`(`/`)` 等（ERE 语义与 Python 等价故无害），拒绝 `&`/`:`/`\t` 等合法字面（deny-based 过严，防 `[:class:]` 优先）——方向正确，观察级；注释已声明意图（:72-77）。

### P3-F — 三加粗形态（`***`）不支持
- **位置**: hook L92 `[*]{0,2}` 上限 2。bold+italic 三缀任务/优先级单元格将 MISS；当前数据无此形态（全部 `**` 两缀或素），观察级；若未来出现需扩为 `[*]{0,3}` 并同步等子集守卫测试。

---

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 结果 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 0 |
| 5 维度全覆盖 | 100% | ✅（§1 五维度逐一结论） |
| 每条发现标注级别 | 100% | ✅（§4 全 P0~P3 标签） |
| 设计一致性检查 | 完成 | ✅（DEC-171 ② 方向内 + M7.5 任务条目形态（behavior-protocol L599-602）+ Step 3 「存在性」语义保留（absent→FAIL）逐一比对，§3-1/§3-6） |
| AI 专项 5 项 | 全部完成 | ✅（§2 五格逐一结论） |

**裁决：通过 → APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0/P1=0；P2×4 非阻塞登记，其中 P2-1/P2-2 建议 Coordinator 裁定入 DEC，P2-3/P2-4 登记后续批次）。

## 6. 遗留项清单（非阻塞）

| 项 | 级别 | 关闭建议 | 截止 |
|----|------|---------|------|
| P2-1 语义收紧副作用披露（REQ-*/指针行） | P2 | Coordinator DEC 落档 + 补 REQ/指针行 MISS 锚点测试 | 本批次 |
| P2-2 布局假设文档化（旧 10-col/21-col 宿主） | P2 | 文档化支持范围 或 授权兼容分支 | Coordinator 裁定 |
| P2-3 replay 用例数据耦合 | P2 | 动态提取任务表 ID 或收窄断言 | 后续触碰 |
| P2-4 post-commit L172 同型 | P2 | 0.78.x 后续批次统一 matcher（WARN-only 不紧急） | 0.78.x 队列 |
| P3-A~F | P3 | 见 §4 各条 | 观察 |

## 7. 未验证项披露

1. Developer 自报全部测试/验证结果（pytest 15 passed + 11 subtests、真实 plan-tracker 三态实测、verify/xref/manifest PASS、全量 26 failed 既有基线）未由本审查者复跑（角色禁 Bash）——建议 Coordinator 以 pytest/verify 机器输出复核。
2. SHA256 一致性未独立计算（无 Bash `sha256sum`/`cmp`）——`.git/hooks/commit-msg` vs 源的一致性以全量 Read 逐行比对（535 行等同）为可复查事实。
3. git 级工作树 diff 未跑：两 hunk/+30-1 的精确性为注入 diff + 工作树全文 Read 静态佐证，非 git 独立复证。
4. ERE 在 BSD grep / BusyBox grep -E 的区间量词行为为静态论证（GNU 主路径未运行验证）；实际运行环境（git-bash/WSL）parity 由 Developer 自报通过。
5. 本报告不替代测试审查/发布审查；REVIEW 机器行持久化由 Coordinator 按 FIX-260 协议执行。
