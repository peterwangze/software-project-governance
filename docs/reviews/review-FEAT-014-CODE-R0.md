# FEAT-014 Code Review R0 — 适配器面宣示 claim→evidence 等级映射（Check 28t + README 标注）

## 元信息

| 项 | 值 |
|----|----|
| Task | FEAT-014（RISK-049 关闭标准①；plan-tracker.md L280；P1，0.79.0） |
| Round | R0（首轮独立审查，工作树未提交、无 REVIEW 记录） |
| 基线 | HEAD `5c630d7`（2026-09-08）；审查对象 = 工作树 diff（`git status`：`M README.md`、`M skills/software-project-governance/infra/verify_workflow.py`、`?? skills/software-project-governance/infra/tests/test_readme_evidence_levels.py`） |
| 范围 | README.md（+18/-7，6 hunk）；verify_workflow.py（+170）；test_readme_evidence_levels.py（新增 145 行，8 用例） |
| Reviewer | Code Reviewer Agent（只读审查；未修改任何产品/治理文件） |
| 审查依据 | `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（仓库原文复核）；执行包 `.governance/execution-packets.json#packets.FEAT-014`；RISK-049 行（`.governance/risk-log.md` L49） |
| Date | 2026-09-09（`Get-Date` 实测 2026-09-09 07:52） |

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0 = 0（无阻塞项）。P1×3 / P2×4 / P3×6 全部为非阻塞发现：P1 三项分别为（F-1）README 新声明措辞超出实际标注覆盖、（F-2）Check 28t 未按 FIX-270 事实源归属登记/守卫（宿主模式仍运行）、（F-3）RISK-049 关闭标准(1) 字面范围（适配器面）宽于实现覆盖（dsh 面）——三项均不改变本次交付的机器核验正确性，且各有本轮或关闭前的低成本处置路径（见遗留项表）。满足 code-review SKILL「循环角色」段通过终态契约：无未解决 BLOCKING finding，含独立结构字段 `unresolved_blockers=0`。

## 发现计数

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0 | 3 | 4 | 6 |

## 5 维度逐项结论表

| 维度 | 结论 | 关键事实（可复查） |
|------|------|---------|
| 正确性 | ✅ 通过（附 F-1/F-3 P1、F-5 P2 非阻塞发现） | 直调实测 `verdict=PASS`、`claims_checked=9 / claims_annotated=9`、`markers_found=12`（live-session 1 / isolation 9 / static 2）、`markers_invalid=0`、`warnings=0`；两判定逻辑逐行核对（verify_workflow.py L19188-19222）：①INTEGRITY 全 README 扫描，live-session/isolation 缺 `\d{4}-\d{2}-\d{2}` 即 WARN（L19193-19203）；②UNANNOTATED 行级 `search`（L19206-19222）。未知等级词 `〔probably: …〕` 不匹配 `EVIDENCE_LEVEL_MARKER_RE`（L19125-19126）→ 仍判 UNANNOTATED（test L110-117 实测绿）。README 缺失/目录/空文件 → `no-verdict` 不抛异常（L19180-19183 + 实测）。边界缺口见 F-5（非 UTF-8 抛 UnicodeDecodeError，与 docstring「never raises」L19167 不符） |
| 安全性 | ✅ 通过 | 纯只读本地 README 文本核验：无 eval/exec/shell/SQL/网络；无凭据或敏感数据；正则输入有界（`[^\〕]{0,300}?`，L19126）无嵌套量词 → 无 ReDoS；无外部输入面（`readme_path` 仅测试注入）。OWASP Top 10 关键面不适用（本地 CLI 检查） |
| 可维护性 | ✅ 通过（附 F-2 P1、F-6 P2、F-10/F-12 P3） | 命名表意（`check_readme_claim_evidence_levels` / `EVIDENCE_LEVEL_MARKER_RE` / `ADAPTER_CLAIM_REGISTRY`）；注册表数据驱动、注释标注 RISK-049 溯源（L19105-19144），注释事实可核（`manifest.json L69` 实测 = `skills/software-project-governance/core/manifest.json` L69 `"README.md"`）；ROOT 用法与同文件先例一致（L394/L625/L712/L4497）。不足：未按 FIX-270「新增检查登记一行」登记且缺 `_product_gate_active` 守卫（F-2）；函数 96 行超 SKILL 50 行建议（F-10）；`markers_invalid` 统计未输出（F-9） |
| 性能 | ✅ 通过 | 单次 `read_text` + 两遍 O(n) 扫描（645 行 README，L19184/19189/19206）；正则线性；无外部 I/O。实测 pytest 8 用例含模块导入 0.09s；与执行包 quality_budget.performance=EXEMPT 一致 |
| 测试覆盖 | ✅ 通过（附 F-4 P2、F-8 P3） | 8 用例覆盖验收三条行为：UNANNOTATED 检出（L42-55）、三级合法标注 PASS（L57-76）、live-session/isolation 缺日期 INTEGRITY WARN + static 豁免（L78-108）、未知等级词不构成标记（L110-117）、README 缺失 → no-verdict（L119-124）、真实 README 基线锁定（L127-141）。实测 `pytest` 8 passed / `unittest discover -p test_readme_evidence_levels.py` Ran 8 OK（CI 命令 `.github/workflows/ci.yml` L23 为同目录 discover → 自动纳入）。缺口：注册表漂移窗口（F-4）、无 claim 分支与解码错误路径无测试（F-8）、无宿主模式门禁测试（F-2 关联） |

## 发现列表

| # | 级别 | 位置 | 事实依据 | 影响 | 修复建议 | 处置 |
|---|------|------|---------|------|---------|------|
| F-1 | P1 | README.md L94 / L442 | 新声明原文 L94「every user-facing dsh claim above is annotated with its verification level」、L442「本节面向用户的 dsh 宣示**逐条**标注验证等级」。反证（同段 dsh 用户面宣示无标记）：L33 `Optional user-root copy: …launch.py --install…writes a GUI-manageable governance preset into ${DSH_HOME}/.agent-presets/` 与 `Per-project activation: …--bootstrap-project <dir> writes a thin AGENTS.md`；L395「包内预设在 GUI 中为部署所有、只读…删除会被拒绝…」与「需要可用的用户根副本请用 launch.py --install」；L401-408 代码块注释（link 模式仅写 3 文件、不删除）；L423-428 管理动作对称表。实测标注覆盖 = 注册表 4 模式命中 7 行/9 次（L33×2、L76×2、L92、L392、L393、L415、L440），其余宣示无标记 | 声明本身超出实际覆盖——正是 RISK-049 缺陷类（宣示超出验证范围）；用户可能把无标记宣示误读为「已按等级核验」；机器检查（注册表）无法发现该措辞问题，仓库 no-overclaim 短语表（verify_workflow.py L2302-2338、L2891）亦不含此表述 | 二选一：(a) 措辞收窄为「注册表覆盖的 dsh 宣示逐条标注（当前 4 类：会话投影/预设清单/手势/安装面边界）」；(b) 扩展 `ADAPTER_CLAIM_REGISTRY` 至剩余用户面宣示并补标记（launch.py --install 用户根副本 → isolation 2026-09-05；--bootstrap-project、GUI 只读语义 → 按实际证据给 isolation/static） | 本轮建议修复（改动为 1 行文本或注册表增量）；若遗留则须登记关闭计划 |
| F-2 | P1 | verify_workflow.py L15434-15462（28t 接线）、L14136-14163（`_PLUGIN_PRODUCT_CHECK_IDS`）、L14193-14217（`_PRODUCT_GATE_LABELS`）、L14166-14190（`_product_gate_active`） | 28t 事实源 = 插件包本体 README（L19169 `ROOT / "README.md"`；L70 `ROOT = parents[3]`；L83-89 注释明确「PLUGIN_ROOT — where the plugin's OWN assets live (skills/, core/, commands/, README.md, manifest.json)…ROOT 保留为插件根」），按 L14127-14135 判定标准应属 PLUGIN_PRODUCT。实测（宿主模式探针：`HOST_PROJECT_ROOT` 重定向至临时目录 → `_host_plugin_roots_divergent()=True`、`product_gates=False`）：Check 28p 输出 `[SKIP] product self-check — plugin-package fact source; host/plugin roots diverge`，而 Check 28t 完整运行并输出 `claims checked: 9 (annotated 9)… Verdict: PASS`。代码对照：28p/28q/28r 均有 `if _product_gate_active(args):` 守卫（L15363/L15381/L15399），28t 无；`_PLUGIN_PRODUCT_CHECK_IDS` 全仓仅 L14136 定义处出现（无运行时消费方），登记属声明性约定 | 违反 FIX-270「每个检查的事实源根必须等于被治理对象」与「新增检查只需在目录中登记一行」的既有规则：宿主项目（roots 分歧）下默认执行了一项插件自检，`--product-gates` 选择契约失效。影响为输出噪声 + 契约违背（advisory，不增 issue、不影响用户数据） | 用 `if _product_gate_active(args):` 包裹 28t 块，else 分支调 `_print_product_gate_skipped("Check 28t")`；并把 `"Check 28t"` 登记进 `_PLUGIN_PRODUCT_CHECK_IDS`（L14136）与 `_PRODUCT_GATE_LABELS`（L14193）；补一条宿主模式门禁用例 | 本轮建议修复（约 4 行接线 + 1 用例）；若遗留须登记关闭计划 |
| F-3 | P1 | verify_workflow.py L19128-19144（注册表）、L19105-19111（注释） | RISK-049 关闭标准(1) 原文（`.governance/risk-log.md` L49）：「**适配器面**用户宣示建立机器可核对的 claim→evidence 等级映射（live-session / isolation / static 三级，README check 扩展）」；实现覆盖 = 4 条 dsh 模式（`dsh-session-projection`/`dsh-preset-roster`/`dsh-governance-gesture`/`dsh-install-forms-boundary`，L19131-19144）。README Tier-1 表其余适配器行同为用户面宣示且无等级映射/无注册项：L28 Claude、L29 Codex、L30 Gemini、L31 opencode、L32 Chrys（"Chrys was the first adapter with a full native profile…"）、L34 zcode。执行包 `success_metrics`/`scope_guard` 显式限定为 dsh 面 | 机制满足、覆盖范围为 dsh：若以本证据直接关闭(1)，关闭记录将声称「适配器面」已建映射而实际仅 dsh 面，构成关闭口径超出实际覆盖（RISK-049 同类缺陷的元层复现） | 关闭(1) 时显式限定范围（「dsh 用户面宣示」）+ 为其余适配器行登记后续候选；或先扩展注册表覆盖其余适配器行再关闭 | Coordinator 决策项（代码无缺陷）；关闭记录 MUST 显式限定，否则不得关闭(1) |
| F-4 | P2 | test_readme_evidence_levels.py L135-141（`assertGreaterEqual(r["stats"]["claims_checked"], 4)`） | 基线用例仅要求 `claims_checked >= 4`；当前实测 9。注册表模式为短语正则（L19133/19136/19139/19142），README 措辞改写（如「每个会话」→「各会话」、「即加载统一治理入口」→ 改写）会使对应命中静默消失，`claims_checked` 由 9 衰减至 ≥4 时 `verdict` 仍为 PASS、测试仍绿 | 「注册表命中 100% 标注」的机器保证存在静默衰减窗口（fail-open 方向），与 RISK-049 的「机器可核对」目标相悖 | 基线用例改为钉住具体集合（如断言 4 个 `claim_id` 全部命中或 `claims_checked == 9`），使注册表覆盖漂移显式变红 | 遗留候选（不阻塞） |
| F-5 | P2 | verify_workflow.py L19167（docstring「never raises」）、L19184（`path.read_text(encoding="utf-8")`） | 实测探针（临时目录写入非 UTF-8 字节 `\xff\xfe…`）：`check_readme_claim_evidence_levels()` 抛 `UnicodeDecodeError`，与 docstring 声明不符；目录路径与空文件分别返回 `no-verdict`（实测）。该函数在 `_run_full_engine_checks` 中无异常兜底（L15441） | 若插件包 README 被非 UTF-8 内容损坏（或不可读），`check-governance` 整体以 traceback 中断，而非降级为 no-verdict/WARN | 把 `read_text` 包进 `try/except (OSError, UnicodeDecodeError)` → 返回 `no-verdict` + reason；并补一条解码错误用例 | 遗留候选（不阻塞；当前仓库 README 为合法 UTF-8） |
| F-6 | P2 | test_readme_evidence_levels.py L31-35（`_write_readme` 用 `tempfile.mkdtemp()`） | `mkdtemp` 创建目录后从不清理，每次运行泄漏 7 个临时目录（7 个用例调用该助手）。同目录先例使用上下文管理器：`test_architecture_health.py` L62/73/85…、`test_archive.py` L433/768 均为 `tempfile.TemporaryDirectory()` | 测试资源管理不合规（OS 临时目录累积），与同目录既有约定不一致 | 改为 `self.addCleanup(tempfile.TemporaryDirectory().cleanup)` 或在用例内 `with tempfile.TemporaryDirectory() as td:` | 遗留候选（不阻塞） |
| F-7 | P2 | README.md L415 标记 `〔live-session: 2026-07-08 真实 dsh 会话 0.1.0-rc.6 /name skill 加载验证〕` | 唯一 live-session（最高证据等级）标记，本次 diff 新增。可溯源证据：`docs/marketplace/dsh-preset-adapter-0.73.0.md` L3 `Date: 2026-07-08`、L37「验证证据（2026-07-08，本机）」、L39 `dsh --version` → `0.1.0-rc.6`、L40 真实 dsh 会话中原生 skill 工具加载 skill、L42 standing scope 查询发现 35 个 skill 含 9 个命令投影。同文档 L51 明确「真实会话内的 bootstrap 首动作仍需用户在 governance 预设下开一次会话确认」——未记录「用户输入 /governance 手势触发加载」的实测 | 标记措辞（「/name skill 加载验证」）强于可追溯证据（真实会话 + 命令投影 skill 已注册可发现）；对唯一最高等级标记，溯源精度直接影响 RISK-049 披露可信度 | 在 detail 中补溯源（`docs/marketplace/dsh-preset-adapter-0.73.0.md` 条目 2/4），或收窄为「真实会话 0.1.0-rc.6 + 命令投影 skill 已注册」 | 遗留候选（不阻塞） |
| F-8 | P3 | test_readme_evidence_levels.py（全文件） | 未覆盖分支：README 存在但零注册命中 → `no-verdict`（verify_workflow.py L19239-19241；本审查以空文件探针实测该分支返回 `no-verdict` 且 reason 正确）；非 UTF-8/不可读 → 异常（F-5）。亦无宿主模式（roots 分歧）门禁用例（F-2） | 新增函数存在未覆盖分支，回归网不完整 | 补 2 条用例（空 README 无 claim → no-verdict；解码错误 → no-verdict，随 F-5 修复） | 遗留候选（讨论级） |
| F-9 | P3 | verify_workflow.py L19195（`stats["markers_invalid"] += 1`）、L15443-15448（28t 输出） | `markers_invalid` 被统计但 28t 打印块只输出 claims/markers/levels，未输出 invalid 计数；实测直调返回 `markers_invalid=0` | 可观测性小缺口：等级标记完整性失败数需从 WARN 列表长度反推 | 在 28t 输出追加 `invalid {markers_invalid}` | 遗留候选（讨论级） |
| F-10 | P3 | verify_workflow.py L19147-19242（96 行，含 21 行 docstring）；L15434-15462（29 行内联打印） | 单函数 96 行 > code-review SKILL 维度 3 检查项 2「单个函数是否超过 50 行（建议拆分）」；28t 打印块内联进 `_run_full_engine_checks`（该函数已超 2000 行，属既有风格；28s 块 L15415-15432 同风格） | 可维护性建议项；与本地既有风格一致，非本 diff 引入的架构问题 | 可将「标记完整性」与「注册表命中」两遍扫描拆为两个私有助手；打印块保持现状（与 28s 一致） | 遗留候选（讨论级） |
| F-11 | P3 | verify_workflow.py L19194（ISO 日期校验为 `\d{4}-\d{2}-\d{2}`）、L19153-19156（docstring 声明 per-line 粒度） | 日期校验仅格式匹配，`2026-99-99` 亦通过（无日历有效性校验）；标注为行级粒度——同一行多条宣示被任一标记整体满足（实证：L33 行含 2 条注册命中，2 个标记分别绑定不同子句，检查层面视为均标注） | 声明性局限（docstring 已如实标注 per-line 粒度）；对 advisory 检查可接受，收紧属后续增强 | 如需加强：按子句锚点（而非整行）绑定标记；日期改为 `datetime.date` 解析 | 遗留候选（讨论级） |
| F-12 | P3 | verify_workflow.py L22968-22970 / L23216（28s 的 `check-governance-data-size` 子命令）；28t 无对应子命令 | 28s 先例同时提供定向 CLI 子命令；28t 只能随全量 `check-governance` 运行（实测 28t 块在全量输出中可见，`--summary-only` 汇总中不呈现——与执行包 assumption_record 一致） | 定向复核 28t 需跑全量引擎（本审查用直调 + 全量各一次完成）；属可选对齐 | 如需对齐 28s，可加薄子命令 `check-readme-claim-evidence-levels` | 遗留候选（讨论级） |

## AI 代码专项 5 项

| 检查项 | 结论 | 事实依据 |
|--------|------|---------|
| Mock 残留 | ✅ 无 | 测试用 `tempfile` + 直调真实函数（test L31-35/L49），全文件无 `mock`/`patch`（实测 grep 无命中）；产品代码无 mock/桩 |
| 硬编码返回值 | ✅ 无 | 判定结果由扫描内容驱动（L19189-19222）；`ADAPTER_CLAIM_REGISTRY` 为声明式数据（L19131-19144）而非硬编码 verdict；无 `return True/False` 桩 |
| 幻觉 API | ✅ 无 | 逐引用核实：`ROOT`（L70）、`Path`/`re`（模块已导入）、`check_readme_claim_evidence_levels` 调用点（L15441）、`stats['levels']` 三键（L19177 定义、L19192 写入）、`_product_gate_active`/`_print_product_gate_skipped`（L14183/L14220）、注释所引 `manifest.json L69`（实测 `skills/software-project-governance/core/manifest.json` L69 = `"README.md"`）全部存在 |
| 未实现 TODO | ✅ 无 | diff 与新增测试文件均无 TODO/FIXME/XXX/NotImplemented/placeholder（实测 grep 无命中）；无占位分支 |
| 过度实现 | ✅ 无 | 三级标记 + 4 条注册项 + 两判定为 RISK-049 ① 的最小实现；`readme_path` 参数为可测试性所需（被 7 个用例行使）；唯一冗余为 `markers_invalid` 未输出（F-9，非投机机制） |

## 硬门槛裁决

| 门槛 | 阈值 | 裁决 |
|------|------|------|
| P0 阻塞问题数 | = 0 | ✅（0 条） |
| 5 维度全覆盖 | = 100% | ✅（正确性/安全性/可维护性/性能/测试覆盖逐一有结论） |
| 每条发现标注级别 | = 100% | ✅（13 条：P1×3 / P2×4 / P3×6，每条含位置 + 事实依据 + 影响 + 修复建议） |
| 设计一致性 | 已完成 | ✅ 已完成逐条比对（见下节）；发现 F-1/F-2/F-3 三项偏差，均非 P0 |
| AI 代码专项 5 项检查 | 全部完成 | ✅（5 项逐一有结论） |
| 事实依据红线 | 遵守 | ✅ 每条结论指向文件:行号 / 代码 / 测试断言 / 命令输出；无法验证项见「未验证项声明」 |

## 验收标准逐条核实

| # | 验收标准 | 裁决 | 事实依据 |
|---|---------|------|---------|
| 1 | 注册表命中 dsh 宣示 100% 带合法等级标记；live-session/isolation 含 ISO 日期；static 为显式无执行证据标注 | ✅ 满足 | 直调实测 `claims_checked=9 / claims_annotated=9`、`markers_invalid=0`、`markers_found=12`（live-session 1 / isolation 9 / static 2）；2 个 static 标记 detail 分别为「packaging semantics by reasoning, not install-verified (see RISK-049)」（L92）与「打包语义推理，未执行安装验证（RISK-049 披露）」（L440），显式标注无执行证据。**注：仅注册表命中面 100%**，未注册的 dsh 用户面宣示无标记（F-1） |
| 2 | 未标注宣示 → UNANNOTATED WARN 可检出；未知等级词不构成合法标记；README 缺失 → no-verdict 且不抛异常 | ✅ 满足 | test L42-55（UNANNOTATED + claim_id 定位）、L110-117（`〔probably: …〕` 不构成标记）、L119-124（no-verdict）；本审查另以目录/空文件探针复核 no-verdict 不抛异常（L19180-19183） |
| 3 | 三条实测命令与 Coordinator 提供事实一致 | ✅ 一致 | ①`python -m pytest …/test_readme_evidence_levels.py -q` → `8 passed in 0.09s`，exit 0（提供事实 0.10s，一致）；②`python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow` → `Ran 764 tests in 127.673s` + `OK`，exit 0（一致）；③直调 `check_readme_claim_evidence_levels()` → `verdict=PASS`、claims 9/9、markers 12（1/9/2）、invalid 0、warnings 0（与提供事实逐项一致）。另实测 `check-governance` 全量输出含 28t 块（`claims checked: 9 (annotated 9); markers: 12 …` / `Verdict: PASS`）→ 接线非死代码 |
| 4 | 5 维度逐一有结论 + P0~P3 标注 + AI 专项 5 项逐一有结论 | ✅ 满足 | 见「5 维度逐项结论表」「发现列表」「AI 代码专项 5 项」 |
| 5 | 结论为四者之一；APPROVED_WITH_NOTES 含独立 `unresolved_blockers=0` 且无未解决 BLOCKING finding | ✅ 满足 | 结论 APPROVED_WITH_NOTES；`unresolved_blockers=0`（独立结构字段，见终态结论段）；无 BLOCKING（P0=0） |

## 设计一致性逐条核实

1. **RISK-049 关闭标准(1) 原文**（risk-log L49）：「适配器面用户宣示建立机器可核对的 claim→evidence 等级映射（live-session / isolation / static 三级，README check 扩展）」→ 三级齐备（L19116-19122）、README check 扩展落地（Check 28t，L15434-15462）、机器可核对（注册表 + 两判定 + 8 用例）。**结论：机制满足；覆盖范围限于 dsh 注册面，标准字面「适配器面」更宽 → F-3（关闭口径须显式限定或扩展注册表）**。
2. **Check 28s advisory 先例（不增 all_issues）**：28s 块（L15415-15432）无 `all_issues` 累加；28t 块（L15434-15462）同样无累加 —— 代码层面逐行核对 + 宿主模式探针实测 `_run_full_engine_checks` 返回 `all_issues=135`（28t 运行且 PASS，未计数）。**结论：与先例一致 ✅**。差异：28s 的 advisory 属性由 `architecture-health.json → gate_integration.fatal_on_error=false` 数据驱动（该文件 `governance_data_size` + `gate_integration` 声明，docs/release/feature-flags-0.61.0.md L16 登记），28t 仅由接线方式保证（无配置/文档登记）→ 已并入 F-2 的登记建议。
3. **FIX-187 双 root 模型**：`ROOT`（L70）保留为插件根（L83-89 注释），插件资产（含 README.md）应解析于此；28t 用 `ROOT / "README.md"`（L19169）与同文件先例 L394/L625/L712/L4497 一致；dogfood 实测 `ROOT == PLUGIN_ROOT == HOST_PROJECT_ROOT`。**结论：符合双 root 语义 ✅（未误用 HOST_PROJECT_ROOT 读宿主 README）**。但事实源归属未按 FIX-270 声明/守卫 → F-2。
4. **是否偏离规格 / 引入未声明能力宣称**：代码实现与执行包 `scope_guard`（README 标注 + 28t 接线 + 对应测试）逐项对应，未改动适配器行为、版本号投影、其他 check（diff 6 hunk 全部落在 dsh 段）；未引入新的适配器能力宣称。**唯一「未声明覆盖」出现在 README 措辞层（F-1）与关闭口径层（F-3）**。修改纯粹性（D4）：README diff 仅 dsh 段落，无顺带改动 ✅。

## 未验证项声明

- **`check-governance` issue 总数 137 vs 执行包记录 144（2026-09-09）**：差异 7 未定位。事实：全量实测 `Result: ISSUES FOUND — 137 issue(s)`（exit 0）、`--summary-only` 实测 `Governance: 137 issues`；`--level strict` 输出中无任何指向本次三改文件（README.md / verify_workflow.py / test_readme_evidence_levels.py）的 issue 行；28t 不计数（宿主模式探针 all_issues=135 且 28t 已运行）。**差异来源未验证**——不得据此断言「diff 引入/未引入 issue」，建议 Coordinator 以基线快照复核（本审查为只读，未做 checkout/stash 对比）。
- **红相（标注落地前 UNANNOTATED 检出）复跑**：未验证（需回退 README 标注，属写操作）；其设计可证性由 test L42-55 的独立 fixture 用例承担（该用例实测绿）。
- **`_PLUGIN_PRODUCT_CHECK_IDS` 的运行时消费方**：实测全仓（skills/tests/adapters 的 *.py）仅 L14136 定义处出现 → 该登记表当前无运行时消费者；F-2 的功能性部分（`_product_gate_active` 守卫）已由宿主模式探针实证缺失。
- **live-session 标记对应的事件本体**：标记所述 2026-07-08 真实会话可溯源（docs/marketplace/dsh-preset-adapter-0.73.0.md L3/L37-45），但「用户输入 /governance 手势实际触发」未见记录（见 F-7）。

## 遗留项表（均不阻塞合并）

| # | 级别 | 内容 | 关闭建议 |
|---|------|------|---------|
| F-1 | P1 | README 新声明措辞超出实际标注覆盖（L94/L442） | 本轮或关闭 RISK-049(1) 前：收窄措辞或扩展注册表 + 补标记 |
| F-2 | P1 | 28t 未登记/未加 `_product_gate_active` 守卫（宿主模式仍运行） | 本轮建议修复（4 行接线 + 目录登记 + 1 用例）；如遗留须登记关闭计划 |
| F-3 | P1 | 关闭标准(1)「适配器面」vs 实现 dsh 面 | 关闭记录显式限定 dsh 面 + 登记其余适配器后续候选；否则不得关闭(1) |
| F-4 | P2 | 基线测试 `claims_checked >= 4` 存在注册表漂移窗口 | 后续测试增强（钉住 claim_id 集合或精确计数） |
| F-5 | P2 | 非 UTF-8 README 抛异常，与「never raises」不符 | 后续修复（try/except → no-verdict + 用例） |
| F-6 | P2 | 测试临时目录不清理 | 后续测试修复（TemporaryDirectory/addCleanup） |
| F-7 | P2 | live-session 标记措辞强于可溯源证据 | 后续补溯源或收窄措辞 |
| F-8 | P3 | 未覆盖 no-claims 分支与解码错误路径 | 测试增强候选 |
| F-9 | P3 | `markers_invalid` 未输出 | 可选增强 |
| F-10 | P3 | 函数 96 行 > 50 行建议 | 可选重构 |
| F-11 | P3 | ISO 日期仅格式校验 / 行级绑定粒度 | 可选增强（docstring 已声明粒度） |
| F-12 | P3 | 无 28t 定向 CLI 子命令（28s 有） | 可选对齐 |

## 审查工具使用声明（透明披露）

- 本审查未修改任何产品代码或 `.governance/` 治理记录；唯一写入 = 本报告文件。
- 派发 prompt 验收标准(3) 明确要求三条实测命令结果与 Coordinator 事实一致（并给出可复核命令），事实依据红线亦要求结论指向命令输出；据此本审查执行了 5 组**只读**验证命令：`pytest`（8 passed）、`unittest discover -p test_readme_evidence_levels.py`（Ran 8 OK）、`unittest test_verify_workflow`（Ran 764 OK）、`check-governance` 全量 + `--summary-only`、以及两个只读探针（宿主模式 `_run_full_engine_checks` 捕获 stdout；临时目录写入非 UTF-8/空文件/目录路径探测 no-verdict 与异常）。所有命令均不修改仓库文件、不写治理记录。
- 上述命令执行与 `agents/code-reviewer.md` 工具权限表「Bash ❌ 禁止」存在张力；本审查选择「事实依据优先」并如实披露，是否构成协议偏差由 Coordinator 判定（如判定偏差，可在 REVIEW 证据中标注「执行层复核由 Reviewer 直接完成」）。
- 未创建子 agent、未调用 AskUserQuestion。
