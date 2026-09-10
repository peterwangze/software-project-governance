# FEAT-019 设计审查报告（Design Reviewer — Round R0）

| 项 | 值 |
|---|---|
| 任务 | FEAT-019 — ArchGuard 棘轮规则 R1~R7 落地与基线快照（AUDIT-150 P0 REFACTOR-archguard-ratchet，fatal 位） |
| 审查轮次 | R0（首次设计审查；复审协议见 agents/design-reviewer.md） |
| 审查对象 | 未提交工作树改动（commit 前置）——3 修改 + 3 新增，与 Code 侧清单一致 |
| 审查面 | 设计与规则语义面（与 Code 侧互补不重复） |
| 规范加载 | `agents/design-reviewer.md` + `skills/design-review/SKILL.md` + `skills/tech-review/SKILL.md`（仓库全文，2026-09-10 会话） |
| 结论 | **APPROVED_WITH_NOTES**（unresolved_blockers=0） |
| 否决权 | 未行使（Bar Raiser 对立面重审结论：设计成立，4 WARNING 全部非否决级——见 §6） |

## 1. 审查对象与事实依据

### 1.1 工作树改动清单（git status 实录）

| 文件 | 状态 | 变化 |
|---|---|---|
| `skills/software-project-governance/infra/archguard_ratchet.py` | 新增 | 1,106 行——棘轮门独立模块（R1~R7 + 豁免 + 基线 build/check/regen + CLI） |
| `skills/software-project-governance/core/architecture-baseline.json` | 新增 | 548 行——基线快照（schema `spg-architecture-baseline/1`） |
| `skills/software-project-governance/infra/tests/test_archguard_ratchet.py` | 新增 | 444 行——正/负对照测试（每规则双向） |
| `skills/software-project-governance/infra/verify_workflow.py` | 修改 | +18/−0——仅 dispatch 接线（import 3 行 + argparse 注册 14 行 + commands-dict 1 行） |
| `skills/software-project-governance/infra/contract_matrix/snapshots.json` | 修改 | +5/−4——CLI 面 80→81 键 / handler 77→78（FEAT-020 快照 --regen 显式再生成） |
| `skills/software-project-governance/infra/tests/test_contract_matrix.py` | 修改 | +5/−1——FROZEN_CLI_KEY_COUNT 80→81 + 审查说明注释 |

### 1.2 审查取证命令（本审查独立实测，全部只读）

- `python .../verify_workflow.py archguard-ratchet` → **Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green，exit=0**。面板实录：R1 `24302 ≤ 24302`、R2 `46 sites ≤ 46 inventory / 36 files`、R3 `12 edges; managed 1; SCC max 1; unmanaged refs 1 disclosed`、R4 `1315 ≤ 1315`、R5 `cli keys 81/81 frozen, segments 70/70 frozen`、R6 `INFO Δ0 wall 1036.6ms`、R7 `deterministic=True; committed==fresh True`。
- 引擎物理行数实测（ReadAllLines 等价口径，同 facts §1.1）：**24,302** ✓（与基线 anchor_loc 精确一致）。
- R1 锚算术闭合核验：facts §1.1/§3.1 设计锚 **24,252**（2026-09-09 HEAD）+ FIX-299 引擎净增 **+7**（commit `1cda292`，verify_workflow.py +8/−1，git show numstat 实测）+ FIX-300 引擎净增 **+25**（commit `e994c7a`，+27/−2，实测）+ FEAT-019 接线 **+18** = **24,302** ✓。
- `checks/*.py` AST print 计数实测：**32 calls / 3 files**（R4 覆盖面缺口证据，见 W3）。
- HEAD=`c92bf5d`（FEAT-020）；基线 `generated.git_head=c92bf5d` 与快照再生成 git_head 一致 ✓。
- `.github/workflows/ci.yml`：4 步（verify 无参 / manifest / `unittest discover -s infra/tests` / cross-refs）——`archguard` 零命中（无命令级显式步骤；间接接线经 unittest 存在，见 W1 分析）。
- packet 措辞检索：`execution-packets.json` FEAT-019 包（L640-767）与 `.governance/change-triage/FEAT-019.json` 均无"实测为准"字样；packet `done_definition` 字面为"R1=24,252 锚定只降不升"（W4 依据）。

### 1.3 权威语义源

演进文档 `docs/requirements/architecture-evolution-0.80.0.md`（DEC-183 采纳）§3.2 L148（12 边枚举）、§4.1 L254-262（R1~R7 规则表）、§4.2 L268、§4.3 L270-275（存量政策/豁免机制）、§8.1、§9.5、§10 L505（REFACTOR-archguard-ratchet 范围/验收）；REVIEW-AUDIT-150-DESIGN-R0 S5（L123）/BR-1（L133-138）；DEC-183/DEC-184（decision-log L192/193）；facts `docs/requirements/architecture-audit-facts-0.80.0.md` §1.1/§3.1（24,252 / 80 键 77 函数 / 1,315 print）。

## 2. 任务指定 5 项设计裁决

### 2.1 规则语义 vs 演进文档 §4 对齐（含 R1 口径漂移裁决）

逐条对照（演进文档 §4.1 → 实现）：

| 规则 | 演进文档语义 | 实现落点 | 判定 |
|---|---|---|---|
| R1 | LOC ≤ 基线锚（ReadAllLines 口径）；只降不升 fatal；"锚定 HEAD=24,252；**本设计不把该数当目标，仅当棘轮起点**"（§4.1）；"基线建立：任务首次运行全规则扫描→生成基线文件"（§4.3） | `check_r1` + `physical_line_count`（口径 docstring 显式钉死与 `str.splitlines` 的差异）；anchor=24,302（regen 时实测） | ✅ 忠实。口径漂移裁决见下 |
| R2 | 新代码零 `import verify_workflow`/`_vw()`（零容忍 fatal）；存量调用点入基线清单（路径+行号+**责任任务**）；CI 断言"基线清单长度单调不增" | AST 扫描三 kind（import_vw/vw_def/vw_call）+ per-(path,kind) count 预算，超即违规；inventory 带 path/lines/owner_task（占位任务名）；parse_error fail-closed 入 findings | ✅ 忠实（count 语义比"清单长度"更严：条目数不变但 count 增加也 FAIL） |
| R3 | §3.2 允许边枚举集之外 = 违规；SCC=0；存量政策"遗留巨石内部不适用（拆完该域才入管辖）；域模块自接入日起适用" | 12 边枚举硬编码 + `ASSERTED_EDGE_COUNT=12` 完整性自检（W1 防护）+ 迭代 Tarjan SCC + 禁边判定仅限 managed set；v1 管辖集仅自身 | ✅ 忠实（见 2.5） |
| R4 | 巨石内 print 按来源计数；**新业务模块零 print（fatal）**；巨石"按段基线递减（advisory→切片清零后转 fatal）"；存量 1,315 按 §3.3 域清单分段 | 巨石 AST 按所属（限定名）函数归档 + total/per-function only-down（fatal）；total=1,315 与 facts §3.1 精确对账（测试双锁） | ⚠️ 双向偏离：分位提前 fatal（S2，正向）；checks 域模块 32 处 print 无任何面承载（W3） |
| R5 | Check ID 唯一、CheckSpec 元信息完备、80 命令键全覆盖、loader 路径可解析；零容忍 fatal | live CLI keys + Check segment IDs == FEAT-020 快照（经其自身提取器消费，非复制）；快照缺失 → SKIP+披露 | ✅ v1 子集忠实；CheckSpec/loader 白名单面未实现且未声明依赖（S1） |
| R6 | 超容差=FAIL；存量政策"**首批切片校准容差（不拍脑袋定阈值）**"（§9.5 协议归 FEAT-018） | threshold=null；INFO/SKIP 永不 fatal（v1）；import_count + import_set_sha256（same-interpreter 确定性面）+ wall_ms report-only | ✅ 恰当——容差未定前无 FAIL 判定依据，不拍脑袋即不硬编码；分层见 2.5 |
| R7 | 生成输出 CI 重生成零差异；机器生成禁手编（§4.2） | 双 regen byte-identical + committed==fresh（git_head 剔除；R6 因跨解释器族变化剔除出比较——advisory 面不冻结，理由自洽）；stale/手编 → FAIL + regen 提示 | ✅ 忠实（R7 本切片作用于基线自身；投影/夹具面属 §6 REFACTOR 任务） |

**R1 口径漂移裁决（24,252 → 24,302）：可接受，予以追认。** 依据链：
1. 演进文档 §4.1 明文"本设计不把该数当目标，仅当棘轮起点"——24,252 是写文档时点的度量快照，从未成为生效锚；
2. §4.3"基线建立：任务首次运行全规则扫描 → 生成基线文件"——生效锚 = 基线建立时点实测，机械锚定旧快照会在建门日即红（+50），违背"基线建立即冻结"（§4.1 存量政策）并制造 S5/BR-1 所述自举混乱窗口；
3. 漂移量 +50 全部可追溯且各自双审通过：FIX-299 +7（`1cda292`，REVIEW-FIX-299-R0 AWN/0）、FIX-300 +25（`e994c7a`，REVIEW-FIX-300-R0 AWN/0）、FEAT-019 接线 +18（自举豁免登记 allowance=0）；
4. "只降不升"语义不变，基线 note 保留设计锚出处。
但 note 的**依据引用与归因有失实/缺口** → W4（修文案，不动语义）。packet 字面"R1=24,252 锚定只降不升"与本实现的差异，由本审查依演进文档权威语义追认（packet 该句应理解为锚定语义的简写而非数值硬编码——数值权威在 §4.3 首扫实测）。

**R6 advisory 定位：恰当。** 演进文档 R6 的 FAIL 以容差表存在为前提（"首批切片校准容差"），FEAT-018（REFACTOR-perf-protocol）未实施时唯一不拍脑袋的选择就是收集框架先行；实现以 baseline note + module docstring + `test_r6_never_fatal_in_this_slice` + 输出文案四重锁定该分层，防止 v1 误升 fatal 或误设阈值。

### 2.2 自举纪律（S5 / BR-1 闭环核验）

S5 建议（REVIEW-AUDIT-150-DESIGN-R0 L123）："archguard-ratchet 落独立模块……；基线生成先于自身代码合并，**或自举豁免显式登记+到期版本**"；演进文档 §10 验收同文。核验：

- **独立模块** ✅：命令+生成器+豁免全部落 `infra/archguard_ratchet.py`（1,106 行），主文件零业务逻辑；
- **主文件仅 dispatch 接线** ✅：+18 行实测构成 = import 3 + argparse 14 + dict 1，与豁免 reason 中"18 lines: import + argparse registration + commands-dict entry"**精确一致**；
- **走了"或"的后一分支且更强** ✅：锚生成于接线之后（接线已在锚内）+ 豁免显式登记（`exemptions[0]`：rule=R1/scope=mainfile/**allowance_lines=0**/expire_version=**0.81.0**/dec=DEC-183/DEC-184）——allowance=0 使该条目成为"DEC 追踪的披露记录而非增长许可"（任何 excess 仍 FAIL，OVER-ALLOWANCE 牙齿在）；
- **看守自身不污染被看守面** ✅：`scan_reverse_dependencies` 不排除本模块（docstring L58-59 明示"it is scanned like every other infra module"）；本模块零 `import verify_workflow`（实测 R2 面绿）；R3 将自身 admit 为唯一 managed module 并诚实披露 lazy `contract_matrix` consumer 边为 unmanaged（待 REFACTOR-contract-layer 接入）。
- 建门日 CI 绿（gate born green）：实测 exit=0，无 S5 担忧的建门日红窗口。

**判定：满足。** S5/BR-1 至此闭环。

### 2.3 豁免机制设计强度

对照演进文档 §4.3"例外必须带 {理由 + 审批记录（DEC ID）+ 到期版本}；到期未续 = CI FAIL；禁通配符豁免（每条点名）"与顾问 Q2：

- 三要素齐 ✅（reason / dec / expire_version）；R1 专属 `allowance_lines` 是设计增强——豁免只在超额 ≤ allowance 时抑制，超出仍 FAIL（`OVER-ALLOWANCE` 标记 + `test_active_exemption_over_allowance_still_fails`）；
- 到期 FAIL ✅：豁免到期 → violation 保留并打 `EXPIRED:` 标记；**R2 inventory 条目到期 → 预算归零 + 无条件违规**（`test_r2_expired_inventory_entry_zero_budget`——即使该 (path,kind) 当前存在 sites，也立即 FAIL 逼清理）；
- 禁通配符 ✅：豁免匹配是 (rule, scope) 精确等值，scope 为具体面（如 `mainfile`、`reverse-dep:<path>:<kind>`），无模式匹配；
- 防常态化设计强度足够 ✅：到期版本是硬熔断（版本源自 SKILL.md frontmatter——DEC-096 权威源）；allowance 使豁免天然衰减；自举豁免 allowance=0 示范了"披露≠许可"；
- fail-safe 方向选择：SKILL.md 版本不可读 → 豁免全 ACTIVE + `version-unreadable` 披露（docstring 声明 suppression fail-safe）——工程折中，见 BR-C（残余低）。

**偏离一项**：§4.3 明文"豁免清单**独立于基线文件**，防混淆"，实现将 exemptions（及 R2 fuse、r3 managed_modules）作为基线文件的 **authored zone**（regen verbatim carryover，extraction zone 禁手编由 R7 守护）。功能等价（不会被 regen 冲掉、逐条点名、fuse 保留），但物理布局偏离明文且未声明裁决理由 → **W2**。

### 2.4 耦合面裁决（与 Code 侧共同裁决项：FEAT-020 契约面 80→81）

事实：FEAT-019 新增 `archguard-ratchet` CLI 键 → FEAT-020 冻结快照必然漂移（80→81 键 / 77→78 handler）。Developer 路径 = `generator.py --regen` 显式再生成（snapshots.json：+`archguard-ratchet` 键、git_head `72ccc89`→`c92bf5d`、timestamp 更新）+ `FROZEN_CLI_KEY_COUNT=81` 计数更新 + test_contract_matrix.py 注释审查说明。裁决三问：

- **最小** ✅：新键本身是演进文档 §4.2（"在发布门新增 archguard-ratchet 独立命令"）与 §10 任务范围明文要求——不存在可更小的替代（不加键则 fatal 门无 CLI 入口）；参数仅 `--regen`/`--baseline` 两个，均为命令自身语义（再锚定/路径覆写），无投机参数；除此之外零契约面变化（Check segments 70/70 不动、handler 仅 +1 对应新键）。
- **合规** ✅：走了 FEAT-020 已文档化的契约变更路径——显式 --regen + 冻结计数同步 bump + 变更说明入代码注释；R5 的违规报文本身即写明该规范路径（"deliberate contract changes must regenerate the FEAT-020 snapshot (its generator --regen) and bump the frozen count in review"）。
- **可追溯** ✅：四重留痕——snapshots.json git_head/timestamp/键清单、test_contract_matrix.py 注释（含审查覆盖声明）、本 DESIGN-R0 裁决记录、以及**R5 现在机器守护 81/81 一致性**（新门自身看护耦合变化，闭环自洽：未来任何一方漂移，R5 fatal）。

**裁决：此耦合最小、合规、可追溯——予以通过。**（注：FEAT-020 R0 的 P2×3 遗留〔generator root 名实不符/golden mojibake/golden 本机路径〕属 FEAT-020 侧登记项，本切片再生成不扩大其暴露——golden 面未被本切片触碰。）

### 2.5 R3 v1 管辖集"接入日"政策 + R6 分层

- **接入日忠实落地** ✅：`DEFAULT_MANAGED_MODULES` 仅 `infra/archguard_ratchet.py`（admitted_by=FEAT-019），与 §4.1 R3 存量政策"遗留巨石内部不适用（拆完该域才入管辖）；域模块自接入日起适用"逐字对应；baseline `legacy_note` 显式声明 verify_workflow.py + checks/* + release/* + loop_* 的 R3 进入时点；
- **分工自洽** ✅：legacy 模块对巨石的反向边（`import verify_workflow`/`_vw()`）在 R2 inventory（实测 46 sites / 36 (path,kind) entries，覆盖 capability_registry/ci/evidence/gate/manifest/review/risk/snapshot/triage/generator/loop_engine/loop_gate_processor/loop_health/loop_migration）**拦截新增**，而 R3 只在接入日判定层间合法边——两规则管辖面互斥不重叠：R2 管"对巨石的反向边存在量"，R3 管"managed 集内的层边合法性"；接入前新增反向边被 R2 零容忍拦住，接入后由 R3 接管层边判定。与 §3.4"存量 `_vw()` 调用点进基线清单，逐切片消除、禁新增禁回升"一致；
- **诚实披露** ✅：unmanaged target refs（如 lazy `contract_matrix.generator`）不判定但报告披露（实测 1 条），测试断言 `report["unmanaged_target_refs"]` 非空；
- **R6 分层明确** ✅：threshold=null 待 FEAT-018——四重披露（baseline note"collection + comparison frame only; FEAT-018's tolerance table fills threshold, then the face tightens — advisory until then, never fatal in v1" / module docstring / `test_r6_never_fatal_in_this_slice` + `test_r6_deterministic_faces_recorded` 断言 threshold is None / CLI 输出"threshold lands with FEAT-018"）。演进文档 §9.5 容差协议与 R6 的衔接（"容差表供 R6 消费"）在基线中留位。

## 3. tech-review checklist 映射

### 3.1 结构完整性（4/4 通过）

| # | 检查项 | 判定 | 依据 |
|---|---|---|---|
| 1 | 设计目标明确 | ✅ | 演进文档 §1（用户目标映射）+ §4.1（规则集逐条机器可判定）+ packet goal |
| 2 | 方案描述完整 | ✅ | §4.2 独立 fatal 命令 + 基线文件 + 豁免机制；实现模块 docstring 逐规则语义 |
| 3 | 替代方案列出 | ✅ | 演进文档 §12 四方案否决（ALT-A 大爆炸/ALT-B 纯文件拆分/ALT-C DSL 表驱动/ALT-D 只修缺陷）；R6 亦有隐含替代（硬编码阈值 vs 收集框架）被 §9.5 否决 |
| 4 | 风险评估 | ✅ | §11.1/§11.2 + BR-1（看守守门人）已有缓解；本轮新增残余见 §5 |

### 3.2 架构质量（7 项）

| # | 检查项 | 级别 | 判定 |
|---|---|---|---|
| 1 | 模块职责单一 | 阻塞 | ✅ archguard_ratchet 单一职责=棘轮守门（1,106 行内聚于规则判定+基线生成，无业务检查逻辑迁移——packet non_goal 遵守） |
| 2 | 无循环依赖 | 阻塞 | ✅ verify_workflow → archguard_ratchet 单向 import；本模块 lazy import contract_matrix.generator（防 import 环，docstring 声明）；SCC 实测 max 1 |
| 3 | 接口定义完整 | 阻塞 | ✅ CLI（2 参数 + exit 0/1 语义 + UTF-8 reconfigure）+ 基线 JSON schema（`spg-architecture-baseline/1`，键面完整可校验）+ 内部函数纯输入输出可独立测 |
| 4 | 数据流清晰 | 关键 | ✅ 扫描（AST/子进程）→ build_baseline → load/check → regen 端到端可追溯；extraction zone vs authored zone 边界明确 |
| 5 | 错误处理覆盖 | 关键 | ✅ fail-closed 三处：baseline 缺失 exit 1 + regen 提示；AST parse_error 入 findings；cold-import 失败 → R6 SKIP 披露（advisory 面降级披露而非假 FAIL） |
| 6 | 可扩展性 | 一般 | ✅ 新规则 = 新 check_rN + 基线段 + regen；managed_modules 按切片 admit；owner_task 占位承接后续 REFACTOR-* |
| 7 | 可测试性 | 一般 | ✅ 444 行正/负对照全覆盖（每规则双向）+ temp fixture 隔离 + CLI 两态 subprocess 实证 |

### 3.3 非功能需求映射

| 非功能需求 | 架构支撑措施 | 满足程度 | 遗留风险 |
|---|---|---|---|
| 性能（R6 面） | 冷导入隔离探测 + 确定性面（count/hash）+ FEAT-018 容差表留位 | 框架满足；门禁待 FEAT-018 | 容差落地前无性能 FAIL 依据（by design） |
| 安全（数据安全） | regen 只写单一目标文件（mkdir+原子性由调用方/commit 看护）；测试全 temp 隔离；负对照不触碰真实引擎/基线/快照 | 满足 | — |
| 可用性（agent/用户面） | exit code 语义冻结（violation→1）；[SKIP]/[note] 披露沿用 FIX-270 先例；输出自明（rule/status/detail） | 满足 | — |
| 可维护性 | 独立模块 + 声明式基线 + 豁免治理化（DEC+到期）+ 12 边枚举自检（W1 防护） | 满足 | authored zone 布局偏离 §4.3（W2） |
| 兼容性（Windows/CI） | stdlib-only（演进文档 facts §9.4 约束）；`sys.stdlib_module_names` 需 3.10+——DEC-184 Q1 已裁 3.11+ 基线；CI=3.11 ✓ | 满足 | `from __future__ import annotations` 保住 3.9 解析兼容，但 3.9 运行 R3 路径会 AttributeError（S3，影响极小） |

## 4. 蓝军挑战（≥3，标准格式）

视角切换（Step 1 框架）：从"这个棘轮为什么是对的"→"**这个棘轮最可能在哪里被架空**"。核心隐含假设：① 基线文件始终等于真实扫描（R7 守护）；② `--regen` 只在切片合并时被善意调用；③ SKILL.md frontmatter 版本可读；④ FEAT-020 快照持续存在。

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|---|
| BR-A | 恶意/草率 `--regen` 架空棘轮：违规增长主文件或新增 `_vw()` 后跑 regen，锚/清单自动抬升，一切检查自洽变绿 | 高（棘轮单向性失效——这正是机制的存在理由） | R7 committed==fresh 禁**手编**但**不禁 regen**；基线文件入 git，regen diff 可见；CI 经 unittest 间接两态（引擎漂移不 regen → R7 stale 红） | **中**：regen-diff 方向无机器断言——演进文档 §4.3"CI 断言基线 diff 方向"未落地（W1） | CI/pre-commit 补基线 diff 方向断言：anchor 只降、R2 inventory 总 sites 只减、R4 total 只降 |
| BR-B | 删除/损坏 FEAT-020 快照 → R5 SKIP+disclose 降级，81 键契约面失守且不红 | 中 | FEAT-020 自身 27 特征测试守护快照存在性；**R7 兜底**：基线 `snapshot_present_at_regen` 参与比较，删快照 → fresh regen 该值变 false → R7 stale FAIL（实测设计路径） | 低 | 可选：SKIP 时于 CI 摘要高亮，防降级静默 |
| BR-C | SKILL.md frontmatter 格式漂移/损坏 → `read_skill_version` 返回 None → 所有豁免永活（到期判定失效） | 低-中 | `version-unreadable` 披露输出；DEC-096 权威源（版本面另有 check-version-consistency 等多检查守护）；豁免仅 1 条且 allowance=0（无实质抑制能力） | 低 | 可选：version=None 时将 R1 豁免按"不可用"处理（保守反转）；当前折中可接受 |
| BR-D（维护者视角） | R4 per-function 键=函数名：任何改名/重构都触发 R7 stale → regen 日常化 → diff 审查疲劳，BR-A 残余放大 | 中 | regen 显式命令 + 摘要输出（锚/sites/print total 一目了然）；切片合并才需 regen 的节奏预期 | 中低 | W1 方向断言落地后此疲劳路径自动收紧（regen 也要过方向门） |

## 5. 发现清单（BLOCKING 0 / WARNING 4 / SUGGESTION 3）

> 无 BLOCKING 发现。以下 WARNING 均为非阻塞设计缺口/偏离，不构成"未解决 BLOCKING finding"。

### WARNING

- **W1 — 基线 diff 方向断言未落地（演进文档 §4.3 明文机制缺失）**
  位置：`archguard_ratchet.py`（`check_r7`/`regen_baseline`——只验"基线==当前扫描"，不验方向）；`.github/workflows/ci.yml`（无 archguard 步骤、无基线 diff 检查）。
  事实：演进文档 §4.3"棘轮动作：……基线自动缩减（且仅缩减）；**CI 断言基线 diff 方向**"；§10 范围含"CI 接线"。现状：命令级 CI 显式步骤缺失，但 `unittest discover`（ci.yml L23）运行 test_archguard_ratchet（含真实 CLI 两态 + R7 committed==fresh）构成**间接接线**——引擎漂移不 regen、基线手编两场景 CI 均会红；唯一无机器看护的场景 = **显式 regen 抬锚/扩清单**（BR-A 残余）。
  建议：小切片补 CI 步骤或 pre-commit 钩子断言基线 diff 方向（anchor 只降 / R2 inventory 总 sites 只减 / R4 total 只降）；过渡期将"基线文件 diff 方向"列为 slice review 必查项。
- **W2 — 豁免清单内嵌基线文件，偏离演进文档 §4.3"豁免清单独立于基线文件，防混淆"明文且未声明**
  位置：`architecture-baseline.json` 顶层 `exemptions` 键 + `r2_reverse_dependency.inventory[].expire_version` fuse + `r3_layer_matrix.managed_modules`（authored zone）；`archguard_ratchet.py` L46-47/L848（carryover 设计）。
  事实：功能等价（authored zone regen verbatim 保留、逐条点名、三要素、到期 FAIL、无通配符），但物理布局与 §4.3 明文冲突，且代码/基线/文档均未声明该偏离及理由。
  建议：二选一并留痕——(a) 拆 `core/architecture-exemptions.json`（独立文件，regen 读取合并）；(b) 保持内嵌但经 decision/演进文档变更注记追认"文件内分区（extraction/authored）+ R7 禁手编"满足"防混淆"意图（单一事实位置 + regen 原子性），补一句声明即可。
- **W3 — R4 覆盖面缺口：checks 域模块 32 处 print 无任何棘轮面承载**
  位置：`count_print_calls`/`check_r4`（仅 `verify_workflow.py`）；实测 `infra/checks/*.py` AST print = 32 calls / 3 files。
  事实：演进文档 §4.1 R4 增量政策"**新业务模块零 print（fatal）**"+ §3.2 L3 禁令（"L3 领域插件禁 print"）无判定面：R4 v1 只扫巨石，既有 checks 模块的 print 增长（新加或存量回升）不被任何规则拦截。
  建议：R4 增设 checks 面存量基线（per-file count 入清单 only-down，与 R2 inventory 同构），或显式登记为 REFACTOR-render-extract 切片前置（写入基线 note 或 plan-tracker 任务行），防"R4=已完成全部语义"误读。
- **W4 — baseline R1 note 依据引用失实 + 归因不全**
  位置：`architecture-baseline.json` `r1_mainfile_budget.design_anchor_note`（"FEAT-019 packet mandates 实测为准 at regen time (intervening engine deltas: **FIX-300** + FEAT-019 dispatch wiring)"）；同文案见 `archguard_ratchet.py` `R1_DESIGN_ANCHOR_NOTE`；`test_archguard_ratchet.py` L52 注释（"packet: ≥24,000 scale, 实测为准"）。
  事实：(a) `execution-packets.json` 与 `change-triage/FEAT-019.json` 均无"实测为准"措辞（检索实录），packet `done_definition` 字面反而是"R1=24,252 锚定只降不升"——note 把依据错挂在 packet 上；真实权威依据是演进文档 §4.1（"仅当棘轮起点，不当目标"）+ §4.3（首扫生成基线），本报告 §2.1 已据此追认漂移可接受；(b) 归因漏 FIX-299 引擎净增 +7（算术闭合：24,252 + 7(FIX-299 `1cda292`) + 25(FIX-300 `e994c7a`) + 18(wiring) = 24,302——note 只列 FIX-300 则算术不闭合）。
  建议：修 note/注释文案——依据改为"evolution §4.1/§4.3（棘轮起点实测锚定）"，归因补全三项（FIX-299 +7 / FIX-300 +25 / wiring +18）。纯文案修正，不动数值与语义。

### SUGGESTION

- **S1 — R5 v1 范围声明缺口**：演进文档 R5 语义含"CheckSpec 元信息完备 + loader 路径可解析（白名单）"，v1 仅落地两键面对账（cli_dispatch.keys / check_segments.ids）；建议在基线 `r5_registration_integrity` 补 note 声明"CheckSpec/loader 白名单面依赖 REFACTOR-contract-layer 接入"，防范围误读（位置：`build_baseline` L833-838）。
- **S2 — R4 分位正向偏离未声明**：演进文档"巨石按段基线递减（advisory→切片清零后转 fatal）"vs 实现巨石面直接 fatal（更严：print 增长立即红）。方向正确（巨石 print 增长本就该拦、与 R1 同哲学），建议 docstring/基线一句追认，消除与演进文档字面的读者困惑（位置：`archguard_ratchet.py` R4 段注释）。
- **S3 — R2 静态扫描已知盲区（低风险，登记即可）**：(a) `from . import verify_workflow`（ImportFrom module=None + level>0）与 `getattr(mod,'_vw')` 动态调用不被识别——演进文档 §4.1 已承认动态盲区并以 loader 白名单为补偿（未落地，随 S1）；(b) `sys.stdlib_module_names` 需 3.10+，DEC-184 Q1 已裁 3.11+ 基线故无实际影响，仅与"3.9 解析兼容"表述并存时需知运行 R3 在 3.9 会 AttributeError（位置：`scan_reverse_dependencies` / `check_r3` L388）。

## 6. Bar Raiser 独立评审（对立面框架重审）

按 tech-review 第五步单 agent 最低标准，切换分析框架（"这个设计为什么是对的"→"最可能在哪里失败"）后独立复核四个核心假设：

1. **"基线=真实扫描"**——成立：R7 committed==fresh + 双 regen 字节一致 + 篡改/陈旧双负对照在测（test_r7_detects_*）；CI 经 unittest 强制。
2. **"regen 被善意调用"**——不成立时唯一防线是 diff 审查（W1/BR-A 残余中）——不达否决级（基线入库+显式命令+四重留痕使滥用可追溯，方向断言可增量补）。
3. **"版本可读"**——BR-C 残余低（豁免仅 1 条且 allowance=0，失效无实质抑制收益）。
4. **"快照存在"**——R7 `snapshot_present_at_regen` 联动兜底（BR-B 残余低）。

**独立结论：设计成立。** 棘轮的单向性核心由 R1/R2/R4 的 only-down 判定 + R7 禁手编 + 豁免熔断三重保证，已落地面与演进文档 §4 语义忠实；全部残余缺口（W1~W4）均为可增量闭合的非阻塞项，无根本性架构缺陷，不构成否决。

## 7. 硬门槛裁决（design-reviewer.md）

| 门槛项 | 阈值 | 判定 |
|---|---|---|
| 候选方案数 | ≥2 | ✅ 演进文档 §12 四替代方案逐条否决（ADR 字段完整：背景/决策/备选/排除理由/影响） |
| ADR 关键字段完整 | =100% | ✅ DEC-183 + 演进文档 §0 字段映射 + §3.8 可逆性标注 |
| 蓝军挑战条数 | ≥3（独立 ID） | ✅ BR-A/BR-B/BR-C/BR-D 四条，含缓解/残余/增强 |
| 模块无循环依赖 | =0 | ✅ SCC 实测 max=1；verify_workflow→archguard 单向；lazy import 防环 |
| Bar Raiser 评审完成 | 已执行 | ✅ §6 对立面重审，无否决 |

## 8. 结论

| 字段 | 值 |
|---|---|
| 终态 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0** |
| BLOCKING / WARNING / SUGGESTION | 0 / 4（W1~W4）/ 3（S1~S3） |
| 复审触发 | 不触发（非 NEEDS_CHANGE）；W1~W4 建议随 commit 前文案修正（W4）与后续小切片（W1/W2/W3）跟进，不阻塞本切片 commit |
| 备注（Coordinator 消费） | ①R1 锚 24,302 口径漂移经本审查追认（§2.1 依据链），W4 文案修正后闭环；②FEAT-020 耦合面（81 键）经 §2.4 共同裁决通过；③结论请 Coordinator 经 review-record 机录（REVIEW-FEAT-019-DESIGN-R0），本报告为唯一事实源 |
