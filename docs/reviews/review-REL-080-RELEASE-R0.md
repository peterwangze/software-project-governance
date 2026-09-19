# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R0

**结论：NEEDS_CHANGE ｜ round=0 ｜ unresolved_blockers=6**

- **审查方**：Release Reviewer Agent（独立审查；只读——本报告除本文件外零写盘，复跑后 `git status --porcelain` 仍 = 28 项，与审查前逐行一致）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **28 个 staged 文件**（复核一致）+ `docs/release/{release-checklist,feature-flags,rollback-plan}-0.84.0.md` + `project/CHANGELOG.md` [0.84.0] 段 + `skills/software-project-governance/core/releases/0.84.0.json`（candidate）
- **审查日期**：2026-09-19 ｜ **前轮**：无（REL-080 发布半面首轮；审查轮次与 0.83.0 的 REL-079 链完全隔离——`REL-080-RELEASE-R0` 无前轮引用）
- **证据基线**：4 维 SKILL 口径 + 7 维任务口径全覆盖；9 项门禁独立复跑；`DEC-204~212` / `RISK-052~058` / `EVD-1073~1081` / 九任务机录审查记录逐项核对
- **硬门槛裁决**：**未满足**（`check-release` = exit 1 / 3 issue(s)；回滚方案未经演练；版本 bump 平面存在未申报缺口）→ 见 §6

---

## 0. 独立复跑证据（只读 —— 与 Release Agent 申报逐项对照）

| # | 命令（只读） | 我的复跑结果 | 与 checklist 申报对照 |
|---|---|---|---|
| V-1 | `check-version-consistency` | **PASSED exit 0**；13 文件 + marker 面全一致；WARN ×1 = plan-tracker `工作流版本` 0.83.0 | 与 #1 一致 ✓ |
| V-2 | `check-projection-sync --fail-on-issues` | **PASSED exit 0**；入口双根 + DSH 方言互认（3,634B/59L） | 与 #2 一致 ✓ |
| V-3 | `check-entry-bootstrap-sync` | **PASSED exit 0**；`CLAUDE.md=23835B/full`、`AGENTS.md=2988B/thin`（双根同值） | 与 #3 一致 ✓ |
| V-4 | `check-injection-contract` | **PASSED exit 0**；3 文件 / 23 anchors | 与 #4 一致 ✓（逐值） |
| V-5 | `check-injection-budget` | **PASSED exit 0**；resident **4,957 / 6,000**（余量 1,043 = 17.4%）；分项 persona 1,673 / entry-template 1,361 / secondary 875 / agent-instructions 1,048；entry-skill 9,387 **report-only** | 与 #5 一致 ✓（逐值） |
| V-6 | `check-cross-references` | **PASS exit 0**；0 dangling / 0 deprecated / 0 circular | 与 #6 一致 ✓ |
| V-7 | `check-manifest-consistency` | **PASS exit 0**；canonical **768** / actual **869** | #7 申报 767/865 → **时点漂移**（见 F-11） |
| V-8 | `release-projection`（check 态） | **PASS exit 0**；`source_version=0.84.0`、`projections_checked=26`、`declared_legacy_snapshots=10`（converged 0 / missing 0） | 与 #9 一致 ✓（逐值） |
| V-9 | `check-archive-integrity` | **PASS exit 0**；hot 85 / archived 93 / index 1221 / 合计 178 | 与 #16 一致 ✓（逐值） |
| V-10 | `check-governance --summary-only --level strict` | **`Governance: 29 issues` exit 0**；FAIL 构成与 WARN 构成见 §4.2 | 与 #13 总数一致 ✓；WARN 逐项枚举不完整（F-07） |
| V-11 | `pytest test_entry_projection.py test_bootstrap_aggregate.py`（FIX-353 两文件，`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`） | **74 passed exit 0**（32 + 42，0.97s） | #17「两文件复验 exit 0」成立 ✓（计数口径见 F-10） |
| V-12 | `git rev-list --count 2a15e59..b537976` / `git rev-list -n1 v0.83.0` | **10**；`v0.83.0` = annotated tag，peel = **`296f4f5`** | 与 Change Inventory / 回滚区间锚定一致 ✓（逐值） |
| V-13 | `git status --short` + index 面抽验（§2） | 28 staged 一致；**零未暂存改动**；审查后行数不变 | 与 §8 申报 28 文件一致 ✓ |

**未独立复跑（如实标注，不得写成通过）**：`archguard-ratchet`（#8）、`e2e-check`（#11）、`verify`（#12）、`check-release`（#14）、`release-ledger`（#15）——前两项含 regen/写入面 vs 已 staged 候选的工作树污染风险，后三项为长时/全量执行；其申报值**未被本次独立复核**，按事实依据红线标「未独立验证」（对应 M-8 复跑义务，见 §7）。

---

## 1. 维度一：版本 bump 完整性（含盲区披露）

**结论：不通过（存在未申报缺口 F-05）**

staged 28 文件平面与申报一致；**index 面**（非工作树）逐项抽验通过：

| 平面 | 载体（index 实测值） | 判定 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter `0.84.0` | ✓ |
| JSON 声明面 ×7 | `.claude-plugin/plugin.json` / `marketplace.json`（`/plugins/0/version`）/ `.codex-plugin` / `.zcode-plugin` / `.chrys-plugin` / `package.json` = **0.84.0**；`core/manifest.json` `0.84.0` | ✓ 7/7 |
| hook 版本行 ×4 | `infra/hooks/{pre-commit,commit-msg,post-commit,prepare-commit-msg}` `@version: 0.84.0`；staged diff 各 **1 加 1 删**（仅版本行） | ✓ 4/4 |
| canonical 模板标记 ×4 | `commands/governance-init.md` = **4 × `@bootstrap-version: 0.84.0`**（full×3 + secondary-thin×1）；diff = 4 行替换 | ✓ 4/4 |
| DSH 方言面 ×2 | `adapters/dsh/AGENTS.md.template` `@bootstrap-version: 0.84.0`；`agent-presets/governance/agent.cordis.yml.template` persona `v0.84.0` | ✓ 2/2 |
| 入口投影（tracked 面 ×3） | repo-root `AGENTS.md`（0.83.0→0.84.0）+ fixture `CLAUDE.md` / `AGENTS.md` = 0.84.0 | ✓ |
| 入口投影（未跟踪面 ×1） | repo-root `CLAUDE.md` = 0.84.0 但 **`.gitignore:3` 忽略**（`git ls-files` 不匹配）→ 不进发布面；回滚方案 §1 载体行**已显式披露**此点 | ✓ 披露充分 |
| `REQUIRED_SNIPPETS` 版本钉 ×6 | `verify_workflow.py` staged diff = 6 处 `0.83.0 → 0.84.0` | ✓ 6/6 |
| fixture 面 | fixture `skills/.../SKILL.md` 0.84.0 + fixture `.governance/plan-tracker.md` `工作流版本: 0.84.0` | ✓ 2/2 |
| **fixture 命令面** | `project/e2e-test-project/commands/governance-init.md`（**tracked**）= **4 × `@bootstrap-version: 0.83.0`**，**不在 staged 集**，**不在任何门禁覆盖面** | ✗ **F-05** |
| CHANGELOG / ledger | `## [0.84.0]` 首段；`core/releases/0.84.0.json` = `lifecycle_state: candidate` | ✓ |

- `check-version-consistency`（13 面）+ `check-projection-sync`（26 面）+ `check-entry-bootstrap-sync` **三门全 PASS 却不覆盖 F-05 载体** ⇒ 该缺口为**真实口径盲区**（非仅披露遗漏）。
- FIX-353 两处测试版本钉（`test_entry_projection.py` / `test_bootstrap_aggregate.py`）**已修复且复验绿**（V-11）——评审确认其修复方式为动态派生 + 令牌化 + fail-closed（丢令牌即 `RuntimeError`），**无 vacuous compare 降级**（`_bootstrap_template_version()` 头部不可读即 raise；`_pin_active_version()` 无令牌即 raise；`PLAN_TRACKER_UPGRADED` 静默 no-op 即 raise）⇒ **修复质量合格**（裁决见 §5.3）。

## 2. 维度二：CHANGELOG 可追溯性

**结论：PASS（抽验 5 条逐项闭合）**

| 抽样条目 | commit | EVD | DEC / RISK | 判定 |
|---|---|---|---|---|
| FEAT-032 成本埋点 | `564b7da` ✓（窗口内） | EVD-1073 ✓（evidence-log L2241） | DEC-205 ✓ / RISK-052 ✓ | ✓ |
| FEAT-033 聚合命令 | `a5d678f` ✓ | EVD-1075 ✓（L2249） | RISK-054 ✓ | ✓（R0 NEEDS_CHANGE→R1 机录可查） |
| FEAT-035 迁移确认门 | `df9e7db` ✓ | EVD-1078 ✓（L2262） | DEC-209 ✓ / RISK-056 ✓ | ✓ |
| FEAT-039 预算门禁 | `512fd51` ✓ | EVD-1080 ✓（L2270） | DEC-210 / DEC-211 ✓ / RISK-057 ✓ | ✓ |
| FEAT-040 灰度开关 | `b537976` ✓ | EVD-1081 ✓（L2275） | DEC-212 ✓ / RISK-055 / RISK-058 ✓ | ✓ |

- **载荷窗口**：`2a15e59..b537976` = **10 commits**（V-12），与 Change Inventory「10 个载荷提交」逐 hash 一致（`c3e1da0/564b7da/457a756/a5d678f/469fb57/38ff7d7/df9e7db/697689d/512fd51/b537976`）✓。
- **B-1~B-6 行为变更**：CHANGELOG 0.84.0 段逐条收录（六条）✓，与 checklist「行为变更」表、feature-flags §2 三处**同集同序** ✓；B-6 明确列出 4 项回退面 + 5 项安全不变量，回退指引可执行（env / plan-tracker 双臂）✓。
- **Breaking changes = 无**：与 diff 面一致（无 MUST 规则删除/重命名、无 Gate 语义破坏、无字段格式变更）✓；semver MINOR 论证引 `core/VERSIONING.md` L12/L37 ✓ 且**非** PATCH/MAJOR 的反证齐备 ✓。
- **灰度/回退说明完整性**：feature-flags §1（F-1~F-4）/§1.1（I-1~I-5）/§4（D-1~D-5）/Kill-switch 声明齐备；**唯一高风险面（交互语义变更）有 F-1/F-2 一键回退**，安全面不回退有 `behavior_profile.py` 三层机检承载 ✓。

## 3. 维度三：发布文档三件套

**结论：checklist 基本合格（含 F-07/F-08/F-09/F-10/F-11/F-14 精度缺陷）；feature-flags 合格；rollback-plan 步骤可执行但**未经演练**（F-03）**

- **checklist**：Gate 表 1~19 逐项有当场值 + FAIL 逐项归属（检查号 + 载体 + 处置人）；no-overclaim 边界 7 条（含隔离环境措辞「环境变量重定向至临时目录」，无无限定语「真实安装」表述）✓；RISK 复评提案 8 行 ✓；披露清单 ①~⑥ ✓；M-2 执行序 / M-8 收尾义务清单齐备 ✓。**精度缺陷**见 §5.1。
- **feature-flags**：开关表 / 安全不变量机检形态 / 非开关项登记 / 无删除项 / 与 0.83.0 对照 / Kill-switch 需求声明 —— 结构完整、无夸大 ✓。
- **rollback-plan**：区间锚定（`2a15e59` 起点 + `<发布 tip>` 占位不预填）✓ 与实测一致；**先例教训注记**（0.81.0 F-01/F-04、0.82.0 勘误）显式内嵌 ✓；§1 回滚影响分类含**唯一安全面**（B-2 弱化）显式列出 ✓；§2 程序分插件侧/用户侧 + §2.3 发布前中止三态 ✓；§3 数据安全（`.governance/` 零触碰）✓；§4 回滚后验证 10 项 ✓；§5 不可回滚项 6 条 ✓；§6 触发条件 6 条含「未授权写操作发生 → 最高优先回滚」✓。**步骤可执行性**：命令形式与仓库实测一致（`check-version-consistency` 可跑、`sync_entry_projection.py` 存在、`<plugin_root>` 占位语义清楚）✓。**缺陷**：§4 #10 回滚演练 = 「M-5 期义务/未执行」，无演练记录 ⇒ 硬门槛「回滚方案存在且**已验证**」不满足（F-03）。

## 4. 维度四：门禁状态裁决

### 4.1 11 项 exit 0 面
9 项独立复跑全 exit 0 且与申报一致（V-1~V-9）；`archguard-ratchet`/`e2e-check`/`verify` 未独立复跑（§0 说明），其值按「未独立验证」入账，不作通过声明。

### 4.2 `check-governance` 29 issues（我的复跑原始构成）
- **FAIL 10**：`18c ×1` / `18d ×2` / `18f ×2` / `18i ×1` = **REL-080 missing execution packet ×6**（§5.1 F-01）；`28c ×1` = snapshot missing parseable `session_date`（F-02）；`28s ×1` = evidence-log 1,571,227 B（1534.4 KB，advisory）；`Check 30 ×2 closure violations`（F-12）。
- **WARN**：`24 ×1`（plan-tracker 0.83.0）、`2 ×1`（4 stale risk）、`14 ×1`（424 structural / 0 blocking）、`28n ×8`（module 3 / function 5）、`28q ×4`（hooks_drift）、`30c ×1`（2 machine-provenance）、**`35 ×1`（snapshot freshness —— 与 28c 同源）**、**`36 ×1`（risk mitigation closure ×16）**。

### 4.3 三项 `check-release` FAIL 逐项裁决（**这 3 项是否构成发布阻断**）

| FAIL 项 | 事实（我的复核） | 裁决 |
|---|---|---|
| ① `hot fact source` | **未收口**：28c 仍 FAIL（谓词 = 快照缺 `**session_date**: YYYY-MM-DD`，实测正则 `FIX_105_SNAPSHOT_DATE_RE` 不匹配「> 生成: 2026-09-18」）+ 35 同源 WARN；且清单声明的收口物「本文件提供 proposed 全文」**不存在**（F-02） | **构成阻断**（本版**新增**项、可确定性修复；且收口路径无物可依） |
| ② `execution gates → governance health` | 阻断构成 = **REL-080 packet ×6（本版新增、可直接修复）** + hot fact source ×1 + **Check 30 V2 ×2（历史项）**。其中 30 V2 有据：`RISK-051`（2026-09-17 登记 ×2：FIX-246 缺 R0 / REL-078 链首即 R1）+ `DEC-199`（如实保留、不改写历史），且**两项记录均先于 0.84.0 窗口**（staged 集与 10 提交窗口内均无相关审查记录改动） | **部分构成阻断**：packet ×6 + hot fact ×1 构成阻断；**Check 30 V2 ×2 不构成阻断**（已接受历史缺口，须如实保留、不得「通过化」） |
| ③ `execution gates → unit tests` | `-m unittest .../test_verify_workflow.py -v` 180s 闸门超时（FIX-234 默认）；清单申报「独立复跑 273.4s / exit 0 全绿」——**该复跑的原始证据不在发布包内**，我亦**未**独立复跑（全量套件 ≈19 分钟且存在对已 staged 候选工作树的污染风险）。性质上属**闸门预算 < 本机套件时长**（0.81.0 Gate 13 已登记同类 180s 预算 vs ~240s+ 现象） | **不构成产品阻断（非用例失败）**；但**其收口证据缺失构成阻断**——未验证项不得写成通过，MUST 以 `SPG_RELEASE_GATE_TIMEOUT` 覆盖后复跑并把 exit 0 结果落入发布记录 |

## 5. 维度五：审查链完备性 + FIX-352/353 归属裁决

### 5.1 九任务终态（机录 —— 逐条核对）
`.governance/review-FEAT-03x-R*.md` 全部存在，头部均为 `# Review Record (machine-written by review-record)`（含 task/round/date/reviewer/report 五字段 + 结论行），**终态全部 `APPROVED_WITH_NOTES` 且携带 `unresolved_blockers=0`**；四例 NEEDS_CHANGE 均含 `## 复审必达` + `next_round` 指针（FEAT-033 / FEAT-035 / FEAT-036 / FEAT-039 / FEAT-040）⇒ **九任务 = 9/9 通过终态，机录可查**，与 plan-tracker / CHANGELOG 申报一致 ✓。

### 5.2 发布期修复（FIX-352 / FIX-353）现状
- 两文件改动**已 staged**（`test_entry_projection.py` +36 / `test_bootstrap_aggregate.py` +75）——注意 checklist line 180 仍写「未 staged」（F-14）。
- **零入账**：全 `.governance/{*.md,*.json}` 对 `FIX-35[23]` **零命中**（无 task 行、无 change-triage、无 EVD、无 DEC/RISK）；清单「口径缺口本身入账」在账本中**无对应记录**（grep `13 面|口径缺口|版本钉` 亦零命中）。

### 5.3 裁决：测试夹具修复是否需补审，或可并入本次发布审查
**裁决 = 可并入本次发布审查（无需另开补审轮次），但 MUST 先补入账（F-06 为本轮阻断项之一）**，理由均为可复查事实：
1. **影响面**：改动仅落 `skills/.../infra/tests/**`（测试面），生产行为面零变化（引擎改动仅 `REQUIRED_SNIPPETS` 版本钉 6 处）；无公开接口/协议/数据结构变更。
2. **验证状态**：本次发布审查**已独立复跑**两文件 = **74 passed / exit 0**（V-11），且逐行审阅 diff 确认无断言弱化、无 vacuous compare、双重 fail-closed 守卫在案 ⇒ 质量由本次审查承载（等效 Code 面复核）。
3. **但**：产品代码改动**随发布提交入库**却无 task ID / triage / EVD / 独立审查记录，违反「不在计划跟踪表里就先入账」与「产品代码产出必须有验证证据和独立审查」；因此**入账 + 折叠裁决（DEC）为提交前强制项**，而非可选备注。
   > 注：本项属「账目完整性」阻断，**不指向缺陷**——修复本身合格（与 F-05 的性质不同，勿混同处置）。

## 6. 维度六：DEC-204 预授权范围符合性

**结论：PASS（范围无越权）**

- `DEC-204` 全文核对：范围 = FEAT-032~040 九任务 + **REL-080 发布 0.84.0**；授权形态 = 预授权（覆盖 transition + tag + push github-https）；**边界明文 = 预授权不免除门禁**（M-2 门禁实测 + M-3 审查 MUST 满足，任一发布门禁 FAIL → 停止并升级用户）；不关闭 RISK-036/039/050/051；1.0.0 预留不动 ✓。
- **28 staged 文件 = 声明平面内**：版本/投影面 20 + 发布文档三件套 3 + CHANGELOG 1 + candidate manifest 1 + `REQUIRED_SNIPPETS` 6 钉（同文件）+ **FIX-353 测试文件 2**（唯一非声明平面项 → F-06 裁决）。
- **无夹带**：无切片 B/C 内容、无 RISK 关闭声明、无 1.0.0 面改动、无 0.83.0 既有开关删除；fixture `plan-tracker` 版本行 bump 属发布平面 ✓（与任务口径一致）。
- **门禁不放弃**：清单与 CHANGELOG 均未以「预授权」免除任何 FAIL（3 项 FAIL 全部保留披露）✓ —— 与本轮 NEEDS_CHANGE 结论方向一致。

## 7. 维度七：归档 / 快照 / 路线图收尾路径

| 项 | 事实 | 判定 |
|---|---|---|
| M-6 归档检测 | `migrate --auto --dry-run` = 无可归档数据 / 零写操作；`check-archive-integrity` **PASS**（85/93/1221/178，我复跑逐值一致） | **跳过合理** ✓ |
| M-7 快照 | 现场快照**仍缺** `**session_date**`（28c FAIL + 35 WARN）；且**「proposed 全文」在发布包中不存在**（三件套全文检索无快照内容、无 `**session_date**` 行）；快照自述「补记 0.81.0 发布行——修复 28c」与实测不符，且仍写 REL-079（F-13） | **不通过**（F-02 阻断；收口需**新写**而非复制） |
| M-8 收尾清单 | 9 项义务齐备（commit/快照/plan-tracker/packet/FIX-353 入暂存/全量 pytest/check-release 复跑/hooks 提示/归档）——**但含 1 处过期表述**（line 180「未 staged」，F-14）；`execution-packet --write`、`SPG_RELEASE_GATE_TIMEOUT` 复跑、plan-tracker 版本行三条**收口动作明确可执行** | **基本完备**（需补 F-06 入账项 + 回滚演练项） |
| 路线图/版本行 | plan-tracker `工作流版本` = 0.83.0（WARN 24）→ M-8 收口；REL-080 行 ⏳ 进行中 → 待 ✅ | 已披露 ✓ |
| ledger | `0.84.0.json` = candidate；`release-ledger --no-remote` 预提交态 FAIL（candidate_commit 尚不可由 git 派生）——**M-1 后/commit 前的正确观测值，不包装为 PASS** ✓；M-5 commit 后 MUST 复跑（`--remote` 于 push 后） | 处置正确 ✓ |

---

## 8. 发现清单（P0=0）

**P0：0 项。P1：5 项（全部阻断）。P2：2 项。P3：6 项。**

| ID | 级别 | 维度 | 问题（事实） | 处置 |
|---|---|---|---|---|
| **F-01** | **P1** | 门禁 | `check-release` FAIL② 主构成之一：**REL-080 execution packet 缺失 ×6**（我复跑：18c `1` + 18d `2` + 18f `2` + 18i `1`）。根因 = 任务 ID 由 REL-079 更正为 REL-080 后 packet 未随行（`.governance/execution-packets.json` 现有 9 包全为 `FEAT-03x`，无 `REL-*` 键） | `python … verify_workflow.py execution-packet --write`（REL-080）→ 复跑 check-governance 验证 6 FAIL 归零 |
| **F-02** | **P1** | 门禁/文档 | `check-release` FAIL① `hot fact source` 未收口：快照缺 `**session_date**: YYYY-MM-DD`（28c FAIL + 35 WARN，同源）。**且 checklist 两处声称「本文件提供 proposed 全文」——该内容在发布包中不存在**（三件套全文无快照文本）⇒ 收口无物可依，MUST 新写 | Coordinator 写 `.governance/session-snapshot.md`（补可解析 `session_date`，顺带修正 0.81.0/0.84.0 发布行与 REL-079→REL-080 措辞）→ 复跑 28c/35 归零 |
| **F-03** | **P1** | 回滚 | 回滚演练（rollback-plan §4 #10）= 「M-5 期义务 / 未执行」，**无演练记录** ⇒ 角色硬门槛「回滚方案存在且**已验证**」不满足（0.83.0 先例为 M-1 冻结后即完成 revert 干跑 exit 0/零冲突/36 paths） | 隔离副本执行 §2.1(a) `revert --no-commit 2a15e59..<发布 tip>` 干跑，记录 exit 码/冲突数/paths 数并落入 checklist #18 |
| **F-04** | **P1**（证据类） | 门禁 | `check-release` FAIL③ `unit tests`：180s 闸门预算超时；申报的「独立复跑 273.4s / exit 0 全绿」**无原始证据在包内**，本次审查**未独立复跑**（理由见 §0）⇒ 该 FAIL 的收口证据缺失 | 按清单 M-2 执行序 #4：`SPG_RELEASE_GATE_TIMEOUT=600 python … check-release --version 0.84.0 --require-changelog --lineage-mode candidate` 复跑并把输出/exit 码贴入 checklist；全量 `pytest`（≈19min）复跑确认 0 新增失败 |
| **F-05** | **P1** | 版本平面 | **版本 bump 平面存在未申报缺口**：`project/e2e-test-project/commands/governance-init.md`（**tracked**）携带 **4 × `@bootstrap-version: 0.83.0`**，**未 staged、未 bump、不在 `check-version-consistency`(13 面)/`check-projection-sync`(26 面)/`check-entry-bootstrap-sync` 任一覆盖面**，也不在 `declared_legacy_snapshots`（10 条 = engine/tools-doc/archive/cleanup/4 hooks/2 tests，无命令面）。前序版本（REL-073/075/076/077）该面均在 M-1 批内 bump，本版漏项；而 checklist「fixture 面 ×12 … 10 个 fixture 命令面 = 0.84.0」与「版本 bump 平面清单（零遗漏核对面）」**与事实不符**（盘上 fixture 命令面仅 8 个文件、仅 1 个带版本标记且为 0.83.0） | 二选一并留痕：① bump 该面 4 处标记至 0.84.0（与 canonical 4 × 0.84.0 对齐）并纳入 staged 集；**或** ② 显式将该面声明为平面外（登记 `declared_legacy_snapshots` 或等价 DEC），同时**修正 checklist 的平面声明**。二者皆须补入 §5.1 披露（本缺口属「M-1 口径盲区」同类，本版第二次暴露） |
| **F-06** | **P1**（账目类） | 审查链/范围 | FIX-352/353 属**产品代码**改动（`infra/tests/**`）且**随发布提交入库**，但：无 task 行、无 change-triage、无 EVD、无独立审查记录（`.governance` 对 `FIX-35[23]` 零命中）；清单「口径缺口本身入账」在账本无对应记录 | 提交前补：task_ID + `change-triage` 机录 + EVD 行；并以 DEC 记「折叠进 REL-080-RELEASE-R0 + 本次独立复跑 74 passed/exit 0」的裁决（§5.3）。**修复本身合格，无需另开补审轮次** |
| **F-07** | P2 | 文档披露 | checklist §Gate 10 声称「`check-governance` 的 FAIL/WARN/ERROR 均逐项列明归属」，但 #13 的 WARN 枚举**遗漏 Check 35**（snapshot freshness，与 28c 同源）与 **Check 36**（risk mitigation closure ×16）；总数 29 与实测一致（非计数错误，属枚举不完整） | 补枚举两行（含处置人）；或收窄「均逐项列明」的表述口径 |
| **F-08** | P2 | 文档披露 | #13 把 6 项 packet FAIL 统一写作「**Check 18c ×6**」，实测实跨 **18c×1 / 18d×2 / 18f×2 / 18i×1** 四检查面 | 按实测检查号改写（#14② 的「packet ×6」口径正确，保留） |
| **F-09** | P3 | 文档精度 | B-4 / Change Inventory 的「`AGENTS.md` 16,011B→**2,699B**（-83%）」为 **FEAT-037 时点值**；shipped 实测 = **2,988B**（-81.3%，≤3072B 预算仍满足），且与同一文件 #3 行「AGENTS.md=2988B/thin」自相矛盾 | 统一为 shipped 值并保留时点注记 |
| **F-10** | P3 | 文档精度 | #17「两文件复验 exit 0（**42 tests OK**）」计数不精确——实测 = `test_bootstrap_aggregate.py` **42** + `test_entry_projection.py` **32** = **74 passed** | 按 74（32+42）改写 |
| **F-11** | P3 | 文档精度 | #7 `check-manifest-consistency` 申报 767/865，当场实测 = **768/869**（+4 = 三件套 3 + candidate manifest 1）⇒ 该行数值为 M-1 prep 前时点值；门禁仍 PASS | 刷新为当场值 |
| **F-12** | P3 | 文档精度 | 「Check 30 V2 ×2 …**0.83.0 发布时已存在，本版不新增**」的佐证不完整：0.83.0 checklist 记 **×1 = FIX-246**（L111）；REL-078 项的 ×2 归属见 `RISK-051`（2026-09-17 登记）。两项记录均先于 0.84.0 窗口（我复核：staged 集与 10 提交窗口无相关记录改动）⇒ 实质结论成立，**但引用应指向 RISK-051 而非 0.83.0 门禁行** | 改引 `RISK-051` + `DEC-199` |
| **F-13** | P3 | 文档精度 | `.governance/session-snapshot.md` 自述「本快照补记 0.81.0 发布行——修复 28c」与实测不符（28c 判定谓词为 `**session_date**` 字段，仍 FAIL）；快照仍写「REL-079（0.84.0 发布）」（ID 已更正为 REL-080） | 随 F-02 收口时一并修正 |
| **F-14** | P3 | 文档精度 | checklist M-8 义务 line 180「当前为工作树修改、**未 staged**」与当前状态不符（两文件**已在 stage 区**） | 随 R1 更新为已 staged |

### 8.1 非阻断项（如实保留 —— 不得写成通过）
- **Check 30 V2 ×2**：`RISK-051` + `DEC-199`（如实保留、不改写历史、不机器补造）；发布文档须继续按「既有基线披露」承载，**不得归类为通过**。
- **Check 28s**（evidence-log 1534.4 KB）：advisory `fatal_on_error=false`，维持 DEC-140/FIX-171 披露口径。
- **Check 28n ×8 / 28o 残余 / 30c ×2 / 14 结构 424(0 blocking) / 2 stale risk ×4 / 28q hooks_drift ×4**：advisory 或用户一次性动作（hooks 版本行差异经我复核 = 各 1 加 1 删，行为语义零变化）。
- **WARN 24**（plan-tracker 0.83.0）：M-8 收口。
- **未独立复跑项**（archguard-ratchet / e2e-check / verify / check-release / release-ledger）：标注「未独立验证」，由 M-8 复跑义务承接。

---

## 9. 硬门槛逐项裁决

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | 100% | Gate 表含 **3 项 FAIL**（#14 exit 1）+ 多项未执行义务（#18） | ✗ **未满足** |
| 回滚方案存在且已验证 | = 已验证 | 方案存在且步骤可执行，**演练未执行**（F-03） | ✗ **未满足** |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | Added/Changed/Fixed/B-1~B-6/披露/breaking 全覆盖，5 条抽样可追溯闭合 | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING L11 逐项反证 | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂回退面 + I-1~I-5 三层机检 + `behavior_profile.py` 守护测试在案 | ✓（回退"已验证"由测试面承载） |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 九任务全 ✅（机录终态 9/9 APPROVED_WITH_NOTES/0） | ✓ |
| 版本 bump 完整性 | 全平面 | **存在未申报缺口**（F-05） | ✗ **未满足** |

## 10. 审查结论

**NEEDS_CHANGE**（round=0）**｜unresolved_blockers=6**

**阻断项 6 项**（按收口成本升序，全部为可确定性收口项，无一是产品缺陷）：
1. **F-01** REL-080 execution packet ×6 → `execution-packet --write`；
2. **F-02** 快照 `**session_date**`（28c/35）+ 〔「proposed 全文」缺失 ⇒ 需新写〕；
3. **F-04** `unit tests` 闸门收口证据（`SPG_RELEASE_GATE_TIMEOUT` 复跑 + 全量 pytest 复跑）；
4. **F-03** 回滚演练（§2.1(a) 干跑，exit 0 / 零冲突留痕）；
5. **F-05** fixture 命令面 4 × `0.83.0`（bump 或平面外声明 + 修正 checklist 声明）；
6. **F-06** FIX-352/353 入账（task ID + change-triage + EVD + 折叠 DEC）。

**通过面（本审查已复核成立，R1 无需重做工）**：28 staged 平面与申报一致；9 项门禁独立复跑 exit 0；CHANGELOG 5 条抽样可追溯闭合 + B-1~B-6 完整；feature-flags 完整；rollback-plan 结构与区间锚定正确（仅缺演练）；九任务机录终态 9/9；DEC-204 范围无越权；Check 30 V2 ×2 / 28s / 28n / 28o / 28q 等既有披露项归属正确且非阻断。

**R1 复审范围（重 spawn 同一 Release Reviewer，注入本报告路径）**：仅需验证 6 项阻断的收口实证 + F-07~F-14 的文档修正；**不得跳过前轮比对**（逐条标注「已修复 / 未修复 / 新引入」）。**R1 前不得推进 M-4/M-5**（tag / transition）；`core/releases/0.84.0.json` 在 R1 通过前保持 `candidate`。

**约束性备注（binding notes）**：
1. 若以「已披露」名义把 F-01/F-02 归类为通过并推进 M-5，本结论作废；清单 §Gate 10 已明文禁止该归类方式。
2. Check 30 V2 ×2 与 28s 属**已接受基线**，不因本结论而要求修复（`DEC-199` 口径）。
3. F-06 的折叠裁决成立的前提是 `.governance` 入账完成；未入账即提交 = 产品代码改动无审查覆盖入库，将构成新的流程违规而非文档瑕疵。
4. 本轮**未**独立复跑的 5 项门禁不得被引用为本审查的通过背书。

---

*审查方：Release Reviewer Agent（独立审查，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 28 staged 文件）｜结论：**NEEDS_CHANGE / unresolved_blockers=6**｜机录义务：Coordinator 以 `review-record` 持久化本结论（Reviewer 不写治理状态）*
