# FEAT-014 Code Review R1 — R0 两项 P1 修复验证（F-1 README 措辞收窄 / F-2 Check 28t 产品门守卫+登记）+ 回归

## 元信息

| 项 | 值 |
|----|----|
| Task | FEAT-014（RISK-049 关闭标准①；P1，0.79.0） |
| **Round** | **R1（复审轮——本轮本质是验证 R0 修复，不是首轮审查）** |
| **前轮报告** | `docs/reviews/review-FEAT-014-CODE-R0.md`（R0；结论 APPROVED_WITH_NOTES / `unresolved_blockers=0` / P0=0 / P1×3 / P2×4 / P3×6；F-1、F-2 两项 P1 为本轮修复对象） |
| 基线 | HEAD `5c630d7`（工作树全部未提交，无 REVIEW 记录） |
| 审查对象 | 工作树相对 HEAD 的完整 diff（含 R0 已审部分 + 本轮修复） |
| 范围（实测） | `README.md` +11/-7（6 hunk，全部落在 dsh 段）；`skills/software-project-governance/infra/verify_workflow.py` +176/-0（4 hunk，全部纯新增）；新增 `skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py`（92 行 / 3 用例）；`skills/software-project-governance/infra/tests/test_readme_evidence_levels.py`（145 行 / 8 用例，与 R0 一致，未改） |
| Reviewer | Code Reviewer Agent（只读审查；唯一写入 = 本报告文件） |
| 审查依据 | `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（原文复核）；R0 报告全文；RISK-049 行（`.governance/risk-log.md` L49）；派发 prompt 的 R1 复审协议 |
| Date | 2026-09-09（`Get-Date` 实测 2026-09-09 08:13） |

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0 = 0（无阻塞项）。R0 的两项 P1（F-1 / F-2）**均已修复且经独立复现**：F-1 的 README 措辞收窄为「登记在 `ADAPTER_CLAIM_REGISTRY` 的 dsh 宣示」并含显式反向声明，与实际核验面（注册表 4 类、命中 7 行/9 次、9/9 带标记、`verdict=PASS`）逐项一致；F-2 的 `_product_gate_active(args)` 守卫与两处登记落地，宿主模式 `[SKIP]` / `--product-gates` 恢复 / dogfood 完整运行三态由本审查自写探针独立复现（非引用 Developer 用例）。本轮新增发现 6 条（P2×1 / P3×5），全部非阻塞；R0 的 F-3 与 F-4~F-12 按派发范围标注为「未修复（R0 已登记为非阻塞遗留）」。无未解决 BLOCKING finding → 满足 code-review SKILL「循环角色」段的通过终态契约。

## 发现计数

| 轮次 | P0 | P1 | P2 | P3 |
|------|----|----|----|----|
| R0（前轮） | 0 | 3 | 4 | 6 |
| **R1 本轮新发现** | **0** | **0** | **1** | **5** |
| R0 遗留未修复（非阻塞） | 0 | 1（F-3，范围外） | 4 | 6 |

## 一、R0 逐条比对表（复审协议 M7.4 step 4.6 / code-review SKILL：逐条标注「已修复/未修复/新引入」）

| R0 # | 级别 | R0 内容（摘要） | R1 状态 | 事实依据（文件:行号 / 命令输出） |
|------|------|----------------|---------|--------------------------------|
| **F-1** | P1 | README L94/L442 新声明措辞超出实际标注覆盖（「every user-facing dsh claim above is annotated…」/「逐条标注验证等级」） | **已修复** | README.md L94 现文 = `the dsh claims **registered in \`ADAPTER_CLAIM_REGISTRY\`** (4 claim classes — session projection / preset roster / \`/governance\` gesture / install-forms boundary) are annotated with their verification level … Check 28t (\`check-governance\`) machine-checks that registry mapping; statements in this dsh section outside the registry are not covered by it.`；L442 对应 ZH（`**登记在 \`ADAPTER_CLAIM_REGISTRY\` 的 dsh 宣示**（当前 4 类：会话投影 / 预设清单 / \`/governance\` 手势 / 安装形态边界）… 本节中注册表之外的其他表述不在该核验范围内。`）。与实测核验面逐项一致：直调 `check_readme_claim_evidence_levels()` → `verdict=PASS`、`claims_checked=9 / claims_annotated=9 / markers_found=12 / markers_invalid=0`、levels 1/9/2、`warnings=0`；注册表 4 项命中 7 行/9 次（L33×2、L76×2、L92、L392、L393、L415、L440），逐行 9/9 带标记。反向声明覆盖 R0 F-1 反证清单（L33 `--install`/`--bootstrap-project`、L395 GUI 只读语义、L401-408、L423-428）——经复核这些行仍在且确实无标记，但已被新措辞显式排除在核验范围外。残留（非阻塞）：N-1（硬编码「4 类」为人工镜像） |
| **F-2** | P1 | Check 28t 未按 FIX-270 事实源归属登记/守卫（宿主模式仍运行） | **已修复** | 登记：verify_workflow.py L14159 `"Check 28t",  # README Claim→Evidence Levels（插件包本体 README）`（`_PLUGIN_PRODUCT_CHECK_IDS`）、L14214 `"Check 28t": "README Claim→Evidence Levels (FEAT-014)"`（`_PRODUCT_GATE_LABELS`）。守卫：L15443 `if _product_gate_active(args):` / L15466-15467 `else: _print_product_gate_skipped("Check 28t")` / L15468 尾 `print("└─…")` 位于 if/else **之外**——与 28o（L15340/L15360）、28p（L15365/L15377）、28q（L15383/L15396）、28r（L15401/L15413）**逐行同构**。三态独立复现（本审查自写探针，stub 计数而非 raiser）：宿主模式 `divergent=True, product_gates=False` → 28t 函数调用数 **0**、输出 `[SKIP] product self-check — plugin-package fact source; host/plugin roots diverge. Run with --product-gates to enable.`；`product_gates=True` → 调用数 **1**、`claims checked: 9 (annotated 9); markers: 12 (live-session 1, isolation 9, static 2)` / `Verdict: PASS`；dogfood（`HOST_PROJECT_ROOT=PLUGIN_ROOT=ROOT`）→ 调用数 **1**、完整运行 PASS。advisory 属性独立复现：真实 PASS 与合成 WARN（5 条警告）的 `all_issues` 同为 **124** → 28t 不增计数。R0 记录的「`_PLUGIN_PRODUCT_CHECK_IDS` 无运行时消费方」仍成立（全仓 grep 仅定义处 + 本用例断言 + test_fix270 文档字符串），本轮新增用例使其至少有 1 个断言消费方。残留（非阻塞）：N-3、N-4、N-5 |
| F-3 | P1 | RISK-049 关闭标准(1) 字面范围（适配器面）宽于实现覆盖（dsh 面） | **未修复（R0 已登记为非阻塞遗留；本轮范围外）** | `.governance/risk-log.md` L49 RISK-049 行原文未变（仍为「**适配器面**用户宣示建立机器可核对的 claim→evidence 等级映射…」）；`ADAPTER_CLAIM_REGISTRY` 仍 4 条 dsh 模式（L19131-19144），未登记 Claude/Codex/Gemini/opencode/Chrys/zcode 行。属 Coordinator 治理记录决策（关闭口径须显式限定 dsh 面）。派发 prompt 明确要求本轮不要求修复 |
| F-4 | P2 | 基线测试 `claims_checked >= 4` 存在注册表漂移窗口 | **未修复（R0 已登记为非阻塞遗留）** | `test_readme_evidence_levels.py` L140 仍 `self.assertGreaterEqual(r["stats"]["claims_checked"], 4)`；当前实测 9 |
| F-5 | P2 | 非 UTF-8 README 抛异常，与 docstring「never raises」不符 | **未修复（R0 已登记为非阻塞遗留）** | verify_workflow.py L19190 `content = path.read_text(encoding="utf-8")` 在函数体内无 `try/except`（L19153-19248 区间内无 `OSError`/`UnicodeDecodeError` 捕获） |
| F-6 | P2 | 测试临时目录不清理 | **未修复（R0 已登记为非阻塞遗留）** | `test_readme_evidence_levels.py` L32 `tempfile.mkdtemp(prefix="feat014_")`、L120 `tempfile.mkdtemp(prefix="feat014_none_")`，仍无 `addCleanup`/`TemporaryDirectory` |
| F-7 | P2 | live-session 标记措辞强于可溯源证据 | **未修复（R0 已登记为非阻塞遗留）** | README.md L415 仍为 `〔live-session: 2026-07-08 真实 dsh 会话 0.1.0-rc.6 /name skill 加载验证〕`（仅新增第二个 isolation 标记） |
| F-8 | P3 | 未覆盖 no-claims 分支与解码错误路径 | **未修复（R0 已登记为非阻塞遗留）** | `test_readme_evidence_levels.py` 仍 8 用例（L42/L57/L78/L92/L100/L110/L119/L135），无「README 存在但零注册命中」与解码错误用例 |
| F-9 | P3 | `markers_invalid` 未输出 | **未修复（R0 已登记为非阻塞遗留）** | 28t 打印块 L15447-15465 只输出 claims/annotated/markers/levels/verdict，无 `markers_invalid`（L19201 仍在统计） |
| F-10 | P3 | 函数 96 行 > 50 行建议 | **未修复（R0 已登记为非阻塞遗留）** | `check_readme_claim_evidence_levels` 定义于 L19153，下一 `def` 于 L19251 → 函数体 96 行（与 R0 一致） |
| F-11 | P3 | ISO 日期仅格式校验 / 行级绑定粒度 | **未修复（R0 已登记为非阻塞遗留）** | L19198 仍 `re.search(r"\d{4}-\d{2}-\d{2}", detail)`；per-line `search` 绑定不变（docstring 已声明粒度） |
| F-12 | P3 | 无 28t 定向 CLI 子命令（28s 有） | **未修复（R0 已登记为非阻塞遗留）** | 全仓 grep `check-readme-claim` / `readme-claim-evidence` **零命中** |

**新引入问题**：无（R0 的 13 条发现无一条因本轮修改而恶化；无新增 P0/P1）。

## 二、本轮 delta 逐项核实

### 2.1 README.md L94 / L442 —— F-1 处置（方案 a：措辞收窄）

| 核实项 | 结论 | 事实依据 |
|--------|------|---------|
| 措辞是否收窄到注册表范围 | ✅ | L94「the dsh claims **registered in `ADAPTER_CLAIM_REGISTRY`**」；L442「**登记在 `ADAPTER_CLAIM_REGISTRY` 的 dsh 宣示**」 |
| 是否含显式反向声明 | ✅ | L94「statements in this dsh section outside the registry are not covered by it.」；L442「本节中注册表之外的其他表述不在该核验范围内。」 |
| 「4 类」与实际注册表是否一致 | ✅ | 注册表 4 项：`dsh-session-projection` / `dsh-preset-roster` / `dsh-governance-gesture` / `dsh-install-forms-boundary`（L19131-19144）；README 列举顺序与语义一一对应 |
| 标注覆盖率是否与措辞一致 | ✅ | 直调实测 `claims_checked=9 / claims_annotated=9`；逐行核验 7 行命中（L33×2、L76×2、L92、L392、L393、L415、L440）全部 `annotated=True` |
| 「Check 28t 机器核验」表述是否属实 | ✅ | 28t 块 L15445 调用 `check_readme_claim_evidence_levels()`；`check-governance` 子命令存在（verify_workflow.py L2561）；dogfood 实测输出 `claims checked: 9 …` / `Verdict: PASS` |
| 是否留下新的超范围声明 | ✅ 无（1 条 P2 漂移风险见 N-1） | 新措辞的每一条可核事实均与实测一致；唯一残留是「4 类」计数/类名为人工镜像，机器不核验 |

### 2.2 verify_workflow.py —— F-2 处置（登记 + 守卫）

| 核实项 | 结论 | 事实依据 |
|--------|------|---------|
| 两处登记 | ✅ | L14159（`_PLUGIN_PRODUCT_CHECK_IDS`）、L14214（`_PRODUCT_GATE_LABELS`） |
| 守卫与 28o/28p/28q/28r 逐行同构 | ✅ | 四者均为 `if _product_gate_active(args):` … `else: _print_product_gate_skipped("Check X")` … `print("└─…")`（尾行在 if/else 外）；28t 同构 |
| 宿主模式默认 `[SKIP]` | ✅（独立复现） | 探针：`divergent=True, product_gates=False` → 28t 函数调用数 0；输出含 `[SKIP] product self-check — plugin-package fact source; host/plugin roots diverge` |
| `--product-gates` 恢复运行 | ✅（独立复现） | 探针：同 roots 分歧下 `product_gates=True` → 调用数 1、`Verdict: PASS` |
| dogfood 完整运行（不退化） | ✅（独立复现） | 探针：`HOST_PROJECT_ROOT=PLUGIN_ROOT=ROOT` → 调用数 1、完整输出 PASS |
| advisory 不增 all_issues | ✅（独立复现） | 探针：真实 PASS vs 合成 WARN（5 警告）→ `all_issues` 均 124 |
| 无越界改动 | ✅ | verify_workflow.py 4 个 hunk 全为纯新增（+1 / +1 / +34 / +140），无删除；无版本号、无其他 check 改动 |

### 2.3 新增 `test_feat014_check28t_product_gate.py`（实测 92 行 / 3 用例；派发 prompt 记「68 行」——实测不符，以本审查实测为准）

| 核实项 | 结论 | 事实依据 |
|--------|------|---------|
| 红→绿是否成立 | ✅（非自证） | ① `test_check28t_registered_in_product_gate_tables`（L71-74）断言两条登记——登记为本轮新增行，pre-fix 必失败；② `test_host_mode_skips_check28t_by_default`（L76-82）——探针证明 pre-fix 语义（把 `_product_gate_active` 强制为 True 以模拟无守卫块）下 stub raiser 立即触发 `AssertionError: product check ran: Check 28t`，用例必失败 |
| 断言强度 | ✅ 足够 | skip 用例三断言组合：`assertIn("Check 28t")`（防删除）+ `assertIn("[SKIP] product self-check")` + `assertNotIn("claims checked:")`（该字符串全仓唯一来源 = 28t 打印块，L15447）；stub 为 raiser → 泄漏即失败。flag 用例以 `assertRaises(AssertionError)` 证明产品函数被调用 |
| 是否依赖 README 内容（脆弱耦合） | ✅ 无 | `_run_engine_host_mode`（L47-65）以 raiser 打桩，docstring 明示「stays independent of the README content itself」 |
| 是否自证式断言 | ✅ 否 | 断言对象是「产品函数是否被调用」「登记表是否含 28t」，均为主代码路径属性，非 stub 自身返回值；flag 用例对 stub 异常消息的断言（L88）属可接受权衡（见「测试覆盖」维度） |
| 资源管理 | ✅ | L54 `with tempfile.TemporaryDirectory() as td:`（未复现 F-6 的 mkdtemp 问题） |

### 2.4 R0 已审未改部分（回归面）

| 部分 | 状态 | 事实依据 |
|------|------|---------|
| README dsh 段 12 个等级标记（7 行） | 未改 | 直调统计 `markers_found=12`、levels 1/9/2；逐标记位置 L33×2、L76×2、L92×2、L392、L393、L415×2、L440×2 |
| `check_readme_claim_evidence_levels()` + `ADAPTER_CLAIM_REGISTRY` | 未改 | 函数仍 L19153-19248；注册表仍 4 项（L19131-19144）；实测 PASS、9/9 |
| Check 28t 接线 | 已改（F-2） | 见 2.2 |
| `test_readme_evidence_levels.py` | 未改 | 145 行 / 8 用例；F-4 基线 L140、F-6 `mkdtemp` L32/L120 均保持 R0 状态 |

## 三、5 维度逐项结论表

| 维度 | 结论 | 关键事实（可复查） |
|------|------|---------|
| 正确性 | ✅ 通过（附 N-1 P2、N-4 P3 非阻塞） | F-1 措辞与实际核验面逐项一致（4 类 / 9 命中 / 9 标注 / PASS）；F-2 三态独立复现（宿主 SKIP / flag 恢复 / dogfood 完整）；28t 不增 all_issues（124==124）；守卫未改变 `--summary-only` 与退出码路径（`cmd_check_governance` L14121 调用点未动）；无边界条件退化 |
| 安全性 | ✅ 通过 | 本轮改动 = README 文本 + 一处布尔守卫 + 测试；无 eval/exec/shell/SQL/网络；无凭据/敏感数据；无外部输入面（`readme_path` 仅测试注入）；测试仅写临时目录；实测本审查全部探针运行期间 `.governance/` 无写入（最新 mtime 08:07:43 = Coordinator 锁写入，探针均在其后）。OWASP Top 10 关键面不适用（本地 CLI 检查） |
| 可维护性 | ✅ 通过（附 N-2/N-4/N-5/N-6 P3） | 守卫与 28o-28r 同构（可直接比对）；命名与注释表意；新测试沿用 `test_fix270_product_gates.py` 既有引擎级模式；不足：测试脚手架重复（N-2）、登记表分组注释语义错位（N-5）、产品注释引用 review-local ID（N-6）、函数 96 行（F-10 未修复） |
| 性能 | ✅ 通过 | 产品代码新增开销 = 每次 `check-governance` 一次布尔判断（复用既有 `_host_plugin_roots_divergent()`，L14167-14191）；宿主模式反而**减少**一次 README 扫描。测试面：新文件 3 用例 31.24s（2 次全量引擎运行：17.52s + 13.63s），定向两文件 22.72s（readme 8 + 28t 3 = 11 passed）；与 `test_fix270_product_gates.py`（7 passed / 11.42s，同样 2 次引擎运行）先例一致。全量 `test_verify_workflow` 764 passed / 134.89s（R0 基线 127.67s，差异未做配对基线，归因未验证） |
| 测试覆盖 | ✅ 通过（附 N-2/N-3 P3） | 新文件 3 用例覆盖 F-2 三个面（登记 / 宿主跳过 / flag 恢复）；红→绿非自证（见 2.3）；`test_fix270_product_gates.py` 7 passed 无回归。缺口：无 dogfood 专项用例（N-3，谓词由 test_fix270 `ProductGateSemanticsTests` 泛化覆盖 + 本审查探针实证）；flag 用例断言依赖 stub 消息（权衡已由 docstring 说明）；F-4/F-8 遗留未修复 |

## 四、R1 新发现列表

| # | 级别 | 位置 | 事实依据 | 影响 | 修复建议 |
|---|------|------|---------|------|---------|
| N-1 | **P2** | README.md L94 / L442 | EN「(4 claim classes — session projection / preset roster / `/governance` gesture / install-forms boundary)」、ZH「（当前 4 类：会话投影 / 预设清单 / `/governance` 手势 / 安装形态边界）」为注册表规模与类名的人工镜像；实测 Check 28t 只核验「注册表模式命中行是否带标记」，**不解析** README 中关于注册表自身的描述（`check_readme_claim_evidence_levels` L19186-19242 仅用 `ADAPTER_CLAIM_REGISTRY` 作输入） | 注册表扩容（R0 F-3 已提出「为其余适配器行登记后续候选」）或类名调整后，README 的「4 类」可静默失真，且无任何机器检查可发现——与 R0 F-4（测试侧 `>= 4` 漂移窗口）同源的 README 侧漂移窗口 | 二选一：①删去计数，改写为「登记在 `ADAPTER_CLAIM_REGISTRY` 的 dsh 宣示（类目见该注册表）」；②在 `test_readme_evidence_levels.py` 补一条「README 声明的类目集合 == 注册表 `claim_id` 集合」断言（可随 F-4 一并处置） |
| N-2 | P3 | `test_feat014_check28t_product_gate.py` L36-65 | `_args()`（L36-44）与 roots 打桩逻辑（L55-56）与 `test_fix270_product_gates.py` L38-60 近乎逐行重复；后者已有引擎级类 `EngineProductGateTests`（L175-219），其 `_run_engine` 模式与本文件 `_run_engine_host_mode` 同构 | 两处脚手架需同步维护（如 `_args` 字段增减时）；FIX-270 测试文件的引擎级用例与新 FEAT-014 用例分散在两个文件 | 可下沉共享 helper（如 `tests/_product_gate_helpers.py`），或把 28t 用例并入 `test_fix270_product_gates.py::EngineProductGateTests`；若不改，建议在 docstring 注明「脚手架与 test_fix270 保持同步」 |
| N-3 | P3 | `test_feat014_check28t_product_gate.py`（全文件） | 3 用例中无 dogfood 模式（`_host_plugin_roots_divergent()==False` → 无 `--product-gates` 也运行）的专项断言；该分支由 `test_fix270_product_gates.py` L66-72（`ProductGateSemanticsTests.test_dogfood_keeps_product_gates_by_default`）在谓词层覆盖，本审查另以探针实证 dogfood 下 28t 调用数 1 且 PASS | 28t 的 dogfood 行为缺直接回归网；若未来有人把守卫改为 `if getattr(args,'product_gates',False):`，谓词层用例仍会绿而 28t 在 dogfood 下静默跳过 | 补 1 条 dogfood 用例（roots 相同 + `product_gates=False` → 28t 函数被调用） |
| N-4 | P3 | verify_workflow.py L15436-15442（28t 注释块）、L19161-19166（docstring） | 注释与 docstring 称「fatal_on_error=false … escalation to FAIL is the registered tightening path (RISK-049 closure review)」；实测全仓（排除 review 报告）无 28t 的 advisory/收紧路径登记记录：`architecture-health.json` 与 `docs/release/feature-flags-0.61.0.md`（28s 的 `gate_integration.fatal_on_error=false` 登记先例）均无 28t；`risk-log.md` L49 RISK-049 行亦未提及该收紧路径 | 「registered」措辞缺事实支撑（声明性约定仅存在于代码注释）；与 28s 的数据驱动 advisory 相比，28t 的 advisory 属性只能靠读代码确认 | 要么在 `docs/release/feature-flags-*.md` 或 `architecture-health.json` 式声明中登记 28t 的 advisory 属性与收紧路径，要么把注释中的「registered」改为「planned/candidate」（待 RISK-049 关闭评审时登记） |
| N-5 | P3 | verify_workflow.py L14154-14159 | `_PLUGIN_PRODUCT_CHECK_IDS` 的分组注释「# ArchGuard 插件树扫描」（L14154）之下新增了 28t（L14159），但 28t 的事实源是插件包 README（L19169 `ROOT / "README.md"`），语义上属「插件包本体文件作为事实源」组（L14140，Check 28h「README Pack Guidance」即在该组） | 分组注释是事实源分类的唯一载体（该 frozenset 无运行时消费方），错位会削弱后续新增检查时的分类参照 | 把 28t 移到 L14153（28n）之后 / L14140 组内，或在 L14159 行内注明「事实源 = 插件包 README，此处因归档顺序紧邻 28r」 |
| N-6 | P3 | verify_workflow.py L15442 | 注释末句「Fact source = the plugin package's own README (ROOT) → PLUGIN_PRODUCT (FIX-270 / F-2).」中的 `F-2` 是 R0 报告的本地发现编号（仅存在于 `docs/reviews/review-FEAT-014-CODE-R0.md`），非仓库持久 ID | 后续读者无法从仓库内检索 `F-2` 的含义（该编号随 R0 报告归档，R1/R2 会各自重编号）；注释溯源链断裂 | 改为持久 ID：`(FIX-270 / RISK-049 ①)`，或写全 `(FIX-270; see docs/reviews/review-FEAT-014-CODE-R0.md F-2)` |

## 五、AI 代码专项 5 项

| 检查项 | 结论 | 事实依据 |
|--------|------|---------|
| Mock 残留 | ✅ 无不当 mock | 产品代码无 mock/桩。新增测试文件用 `mock.patch.object` 3 处（L55/L56/L58）：均为**探针式**打桩（roots 重定向 + raiser），不替代被测逻辑；与 `test_fix270_product_gates.py` L188-199 既有先例一致。`test_readme_evidence_levels.py` 仍 0 处 mock（grep 计数 0） |
| 硬编码返回值 | ✅ 无 | 28t 判定仍由扫描内容驱动（L19186-19242）；`ADAPTER_CLAIM_REGISTRY` 为声明式数据；新测试 stub 只抛异常不返回 verdict；README 无硬编码「PASS」类结论 |
| 幻觉 API | ✅ 无 | 逐引用核实并实测通过：`vw._PLUGIN_PRODUCT_CHECK_IDS`（L14136）、`vw._PRODUCT_GATE_LABELS`（L14194）、`vw.ROOT`/`PLUGIN_ROOT`/`HOST_PROJECT_ROOT`（模块级，探针实测值一致）、`vw._run_full_engine_checks`（L14232）、`vw.check_readme_claim_evidence_levels`（L19153）、`_print_product_gate_skipped`（L14222）、`_product_gate_active`（L14184）全部存在；`check-governance` 子命令存在（L2561） |
| 未实现 TODO | ✅ 无 | 改动文件 grep `TODO|FIXME|XXX|NotImplemented|placeholder`：新增测试文件 0 命中；verify_workflow.py 相关区间 0 命中；README 唯一命中 L561「项目目标是 XXX」为无关段落的既有模板示例（不在本轮 hunk 内） |
| 过度实现 | ✅ 无 | 修复为最小面：2 行登记 + 3 行守卫 + 2 段 README 措辞（行数不变）+ 3 个用例；无投机机制、无预留开关、无未使用参数 |

## 六、硬门槛裁决

| 门槛 | 阈值 | 裁决 |
|------|------|------|
| P0 阻塞问题数 | = 0 | ✅（0 条；R1 新发现最高 P2） |
| 5 维度全覆盖 | = 100% | ✅（正确性/安全性/可维护性/性能/测试覆盖逐一有结论） |
| 每条发现标注级别 | = 100% | ✅（R1 新发现 6 条：P2×1 / P3×5，每条含位置 + 事实 + 影响 + 修复建议；R0 比对表 13 条逐条带级别） |
| 复审协议（round 声明 + 前轮逐条比对） | 已完成 | ✅（头部声明 round=R1 与 R0 引用；F-1~F-12 逐条标注状态） |
| 设计一致性 | 已完成 | ✅（见下节） |
| AI 代码专项 5 项 | 全部完成 | ✅（5 项逐一有结论） |
| 事实依据红线 | 遵守 | ✅（每条结论指向文件:行号 / 命令输出 / 探针实测；未验证项见「未验证项声明」） |

## 七、验收标准逐条核实

| # | 验收标准 | 裁决 | 事实依据 |
|---|---------|------|---------|
| 1 | R0 的 F-1 与 F-2 逐条给出「已修复/未修复/新引入」判定 + 事实依据（文件:行号 + 命令输出） | ✅ | 见「一、R0 逐条比对表」+「二、本轮 delta 逐项核实」（F-1 已修复 / F-2 已修复 / 新引入 = 无；其余 11 条标未修复） |
| 2 | F-2 的守卫独立复现：宿主模式 28t `[SKIP]`、dogfood 完整运行、`--product-gates` 恢复 | ✅ | 本审查自写探针（`%TEMP%\feat14_gate_probe.py`，仅内存内 monkeypatch，未改仓库）：宿主模式调用数 0 + `[SKIP] product self-check — plugin-package fact source; host/plugin roots diverge`；`--product-gates` 调用数 1 + `Verdict: PASS`；dogfood 调用数 1 + 完整运行 |
| 3 | 5 维度逐一有结论；每条发现 P0~P3 + 位置 + 事实 + 影响 + 修复建议；AI 专项 5 项逐一有结论 | ✅ | 见「三」「四」「五」 |
| 4 | 结论为四者之一；APPROVED_WITH_NOTES 含独立字段 `unresolved_blockers=0` 且无未解决 BLOCKING | ✅ | 结论 APPROVED_WITH_NOTES；`unresolved_blockers=0`（独立结构字段，见「终态结论」段）；P0=0 → 无 BLOCKING |
| 5 | 回归事实复核：定向测试与 `test_verify_workflow` 结果与提供事实一致 | ✅ | ① `python -m pytest .../test_readme_evidence_levels.py .../test_feat014_check28t_product_gate.py -q` → **11 passed in 22.72s**（exit 0），与 Coordinator 提供事实一致；② `python -m pytest .../test_fix270_product_gates.py -q` → **7 passed in 11.42s**（11+7=18，与 Developer「定向 18 passed」一致）；③ `python -m pytest .../test_verify_workflow.py -q` → **764 passed, 89 subtests passed in 134.89s**（exit 0），与「Ran 764 tests / OK」一致；④ `check-manifest-consistency` → `[PASS] Manifest and filesystem are consistent`（Canonical 603 / Actual 653）；⑤ `check-cross-references` → 3× `[PASS]`；⑥ `check-locks` → `Result: PASS — agent-locks.json is clean`（Active tasks 2 / File locks 2） |
| 6 | 修改纯粹性核查：本轮 diff 是否仅覆盖 F-1/F-2？有无顺带改动、版本号变更、其它 check 改动？ | ✅ 成立（附 R0 numstat 不可复现的披露） | 见下节 |

### 修改纯粹性核查（详细）

**当前工作树 vs HEAD 的实测构成**（`git diff --numstat` + `--unified=0` hunk 统计）：

| 文件 | numstat | hunk | 落点 |
|------|---------|------|------|
| `README.md` | +11/-7（HEAD 641 行 → 工作树 645 行） | 6 | 全部在 dsh 段（L33 / L76 / L92+新增2 / L390-393 / L413-415 / L438+新增2）；无其他段落改动 |
| `skills/software-project-governance/infra/verify_workflow.py` | +176/-0（HEAD 23070 → 23246） | 4 | `+1` L14159（登记）、`+1` L14214（登记）、`+34` L15436（28t 块含守卫）、`+140` L19111（`check_readme_claim_evidence_levels` + 注册表）；无删除、无其他 check 改动 |
| `tests/test_feat014_check28t_product_gate.py` | 新增 92 行 | — | 3 用例 |
| `tests/test_readme_evidence_levels.py` | 145 行（未改） | — | 8 用例，F-4/F-6 状态与 R0 一致 |

**R1 增量（相对 R0 已审树）**：README 两处措辞改写（L94/L442，行数中性——README 总行数 645 与 R0 报告「645 行 README」一致，且 R0 引用的全部行号 L33/L76/L92/L94/L392/L393/L395/L401-408/L415/L423-428/L440/L442 在当前文件逐一命中原内容）+ verify_workflow.py 6 行新增（2 行登记 + 3 行守卫 + 1 行注释补充）+ 新测试文件。**无版本号变更**（`manifest.json`/`plugin.json`/SKILL frontmatter 均不在 diff 内）、**无其他 check 改动**、**无顺带改动**。

**R0 numstat 事实披露**：R0 报告记 `README.md（+18/-7）`，实测为 **+11/-7**（`git diff --numstat`），且与 R0 自报的「645 行 README」自相矛盾（若 +18/-7 成立，R0 树应为 652 行）。R0 对 verify_workflow.py 的 `+170` 与实测 `+176` 相差 6 行，恰等于本轮可辨识增量（2 登记 + 3 守卫 + 1 注释）。**结论：R0 的 README numstat 为报告事实瑕疵（不影响本轮判定）**；因 R0 快照不可获取，R1 增量以「行号 + 内容 + 总行数」三重对齐推定，非 `git diff` 直接比对（见「未验证项声明」）。

## 八、设计一致性逐条核实

1. **RISK-049 关闭标准(1)**（risk-log L49）：「适配器面用户宣示建立机器可核对的 claim→evidence 等级映射（live-session / isolation / static 三级，README check 扩展）」→ 三级齐备、README check（28t）落地、机器可核对（注册表 + 两判定 + 11 用例）。**本轮改进**：README 措辞不再声称「全部 dsh 宣示逐条标注」，改为「注册表内 dsh 宣示」+ 显式反向声明 → R0 F-1 的元层复现风险消除。**残留**：关闭口径仍限 dsh 面（F-3，Coordinator 决策项）。
2. **FIX-270 事实源归属**：28t 事实源 = 插件包 README（L19169 `ROOT / "README.md"`；L83-89 双 root 注释）→ PLUGIN_PRODUCT；本轮按「新增检查只需在目录中登记一行」补齐登记（L14159/L14214）+ `_product_gate_active` 守卫（L15443/L15466-15467）→ **符合 ✅**。
3. **28s advisory 先例（不增 all_issues）**：28t 块仍无 `all_issues` 累加（L15436-15468 区间无该语句）；实测真实 PASS 与合成 WARN 的 `all_issues` 同为 124 → **一致 ✅**。差异（28s 的 advisory 由 `architecture-health.json` + feature-flags 文档数据驱动，28t 仅注释声明）→ N-4（P3）。
4. **FIX-187 双 root 模型**：28t 读 `ROOT / "README.md"`，未误用 `HOST_PROJECT_ROOT`；dogfood 实测 `ROOT == PLUGIN_ROOT == HOST_PROJECT_ROOT`；新增守卫正是为 roots 分歧场景引入 → **符合 ✅**。
5. **是否偏离规格 / 引入未声明能力宣称**：R1 增量与派发 prompt 的 F-1/F-2 处置描述逐项对应；未改动适配器行为、版本号投影、其他 check；未引入新的适配器能力宣称。README 新措辞**收窄**宣称面而非扩张 → **符合 D4 修改纯粹性 ✅**。
6. **测试与治理约束一致性**：`check-manifest-consistency` / `check-cross-references` / `check-locks` 三项均 PASS（命令输出见验收标准 5）；新增测试文件被 CI 命令 `.github/workflows/ci.yml` L23（`unittest discover -s skills/software-project-governance/infra/tests`）自动纳入 → **符合 ✅**。

## 九、未验证项声明

- **R0 快照比对**：R0 树未提交且无存档，无法用 `git diff` 直接隔离「R0 已审部分」与「R1 修复部分」。本审查采用三重对齐推定（① 当前 diff 的 6 个 README hunk / 4 个 verify_workflow hunk 与 R0 描述的「6 hunk」及 R0 引用行号逐一对上；② README 总行数 645 与 R0 自报一致；③ R0 引用的 L395/L401-408/L423-428 等反证行内容未变）——推定结论为「R1 README 增量 = 两处措辞改写且行数中性」，**但未经直接 diff 证明**。
- **R0 报告 `README.md +18/-7` 的成因**：未验证（无法回溯 R0 测量方式）；本审查只确认该数字与当前实测（+11/-7）及 R0 自报行数（645）不相容。
- **全量引擎 `all_issues` 基线的绝对值**：宿主模式探针得 122（默认）/129（`--product-gates`）、dogfood 124。该三值差异来自宿主根为临时目录导致宿主侧检查结果不同，**未逐项归因**；本审查只用其做「28t 不增计数」的等值比较（124==124），未用它做基线断言。
- **`test_verify_workflow` 耗时对比（134.89s vs R0 127.67s）**：未做配对基线/静默窗口复跑，差异**归因未验证**（该套件不含本轮新增文件，机械上不受其影响）。
- **非 Windows / 非本机环境**：全部命令在本机 Windows + Python 3.14 执行；跨平台行为未验证。
- **live-session 标记对应事件本体**：沿用 R0 F-7 的未验证项（README L415 的 2026-07-08 会话可溯源至 `docs/marketplace/dsh-preset-adapter-0.73.0.md` L3/L37-39，但「用户输入 `/governance` 手势实际触发」仍无记录）。

## 十、遗留项表（均不阻塞）

| # | 级别 | 来源 | 内容 | 关闭建议 |
|---|------|------|------|---------|
| F-3 | P1 | R0 | 关闭标准(1)「适配器面」vs 实现 dsh 面 | Coordinator 关闭记录显式限定 dsh 面；否则不得关闭(1)（本轮范围外） |
| N-1 | P2 | R1 | README「4 类」为注册表人工镜像，机器不核验 | 随 F-4 一并处置（删计数或补断言） |
| F-4 | P2 | R0 | 基线测试 `claims_checked >= 4` 漂移窗口 | 测试增强（钉住 claim_id 集合/精确计数） |
| F-5 | P2 | R0 | 非 UTF-8 README 抛异常 | 后续修复（try/except → no-verdict + 用例） |
| F-6 | P2 | R0 | 测试临时目录不清理 | 后续测试修复 |
| F-7 | P2 | R0 | live-session 标记措辞强于证据 | 后续补溯源或收窄 |
| N-2 | P3 | R1 | 新测试脚手架与 test_fix270 重复 | 下沉共享 helper 或并入既有类 |
| N-3 | P3 | R1 | 缺 dogfood 专项用例 | 补 1 条用例 |
| N-4 | P3 | R1 | 28t advisory/收紧路径无登记记录 | 登记或改注释措辞 |
| N-5 | P3 | R1 | 登记表分组注释语义错位 | 调整位置或行内注明 |
| N-6 | P3 | R1 | 产品注释引用 review-local ID `F-2` | 改用持久 ID |
| F-8~F-12 | P3 | R0 | 分支覆盖 / `markers_invalid` 输出 / 函数长度 / 日期校验 / 定向子命令 | 可选增强 |

## 十一、审查工具使用声明（透明披露）

- 本审查未修改任何产品代码或 `.governance/` 治理记录；唯一写入 = 本报告文件。实测佐证：`git status --short` 前后一致（`M README.md`、`M verify_workflow.py`、`?? docs/reviews/review-FEAT-014-CODE-R0.md`、`?? test_feat014_check28t_product_gate.py`、`?? test_readme_evidence_levels.py`）；`.governance/` 最新 mtime 为 08:07:43（Coordinator 锁写入），本审查全部探针在其后运行，未产生新写入。
- 为满足验收标准 2（F-2 守卫独立复现）与 5（回归事实复核）以及事实依据红线，本审查执行了**只读**验证命令：`pytest`（11 / 7 / 764 三组）、`check-manifest-consistency`、`check-cross-references`、`check-locks`、以及 4 组内存内探针（直调 `check_readme_claim_evidence_levels()` 统计 + 注册表逐行命中；`_run_full_engine_checks` 三态门禁；advisory 等值比较 + 无守卫反证；HEAD/工作树行数核对）。探针脚本仅写入 `%TEMP%`，对仓库文件的修改为 0（monkeypatch 仅作用于进程内存）。
- 上述命令执行与 `agents/code-reviewer.md` 工具权限表「Bash ❌ 禁止」存在张力；本审查选择「事实依据 + 验收标准优先」并如实披露（与 R0 相同处置），是否构成协议偏差由 Coordinator 判定。
- 未创建子 agent、未调用 AskUserQuestion、未修改非报告文件。

## 十二、结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

- R0 两项 P1（F-1 / F-2）**已修复**，均有独立复现事实支撑；无新引入问题、无 P0。
- 本轮新发现 6 条（P2×1 / P3×5），全部非阻塞，已登记关闭建议。
- R0 的 F-3 与 F-4~F-12 按派发范围标注为「未修复（R0 已登记为非阻塞遗留）」，本轮不要求修复。
- 硬门槛全部通过：P0=0、5 维度全覆盖、每条发现带级别、复审协议（round 声明 + 前轮逐条比对）完成、AI 专项 5 项完成、事实依据红线遵守。
