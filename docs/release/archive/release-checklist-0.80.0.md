# Release Checklist — 0.80.0 (REL-076)

**Version**: 0.80.0 (MINOR — 用户 2026-09-12 指令「发布新版本承载这次修改」；plan-tracker 中 FIX-308/309/310 与 0.80.0 重构线 P1 首批的任务行版本归属即 0.80.0)
**Window**: `v0.79.0 (17eda48) .. <candidate commit>` — **21 commits 已合入 + 本候选 commit**（M-1 核定 2026-09-12，`git log v0.79.0..HEAD`）+ 本候选 commit（M-1 打包：版本投影〔子任务 A〕+ CHANGELOG/三件套/release manifest〔子任务 B〕）
**Status**: candidate（`release_authorized=false`；transition/tag/push 待 M-4 用户授权——DEC-143，唯一人工门）

## Release Scope

本版无 `version-plan-0.80.0.md`（0.80.0 尚无独立规划工件；权威来源 = plan-tracker 0.80.0 任务行 + DEC-183/184/186/187）。窗口含两条**互相独立**的主线：

| 分组 | 任务 | 版本归属 |
|---|---|---|
| 主线一：0.80.0 重构线 P1 首批（DEC-183/184 授权链；前一会话交付） | FEAT-021（最小契约层 L0）、FEAT-022（轻量注册与按命令加载）、FEAT-025（quick-scan Slice-1 检查段事实源注册表）、FEAT-026（quick-scan Slice-2 编排器 + 四态契约 + shadow 通道）、FIX-303/304/305（三者 R0 审查遗留批闭环）、8 个审查报告入库 commit | 0.80.0 |
| 主线二：dsh 适配层零侵入改造三连（用户 2026-09-11 反馈触发「dsh 升级版本之后安装会导致 dsh 异常／预设页崩毁／开不了新会话」） | FIX-307（0.1.5-rc.2 接入兼容性）、FIX-308（persona 行 config 键失效——真机致命项根因）、FIX-309（Check 28v 兼容性护栏）、FIX-310（零侵入架构改造，含审查报告入库 commit） | 0.80.0 |
| 上一版收尾 | REL-075 M-5 回填补提交（release-checklist-0.79.0 row 11 ledger 回填） | 0.79.0 遗留 |
| 治理记录面（gitignored 无产品 commit） | DEC-187 架构不变量入账、RISK-050 登记、EVD-1001/1003/1004/1005 证据入账、REL-076 本候选打包 | 0.80.0 周期 |
| 风险挂载 | **RISK-050**（dsh 上游内部面耦合——FIX-307/308 两次事故同源）本版交付**一条腿**的结构性根因消除（上游内部行 UPDATE 面 + `!!js` 自定位面退役）；**另一条腿未消除**——组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema，由 advisory Check 28v 前移护栏（**不声明关闭**）；RISK-045/046/047/048 状态不变 | 0.80.0 |

**不在本版**：quick-scan Slice-3、REQ-109/111/113/114、FIX-306、FIX-311（P2 登记）、FEAT-021/022/025/026 与 FIX-303/304/305 的各任务 P2/P3 遗留、RISK-044 残余面。

## Change Inventory（21 commits — `git log v0.79.0..HEAD`，2026-09-12 核定）

| # | 任务 | commit(s) | 终态要点（✅ + 审查终态 + EVD） |
|---|---|---|---|
| 1 | REL-075 回填 | `e9facf5` | ✅ M-5 回填补提交（release-checklist-0.79.0 row 11 ledger NATIVE_CANDIDATE PASS 回填；EVD-991 收尾） |
| 2 | FEAT-021 | `906b209` | ✅ 最小契约层 L0（CheckID/CommandKey + Finding〔frozen〕/CheckResult/CheckSpec + 四端口 Protocol + to_legacy_dict 键集恒等 + fail-closed 构造校验；87 测试） |
| 3 | FEAT-021 R0 报告 | `4e4de2b` | ✅ REVIEW-FEAT-021-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（P1×1+P2×6+P3×6 → FIX-303 承接） |
| 4 | FEAT-025 | `504cc8f` | ✅ quick-scan Slice-1 检查段事实源注册表（70 段逐段一行 + C3 四段裁决 + 完整性守卫 fail-closed + FEAT-020 快照对账）；EVD-995 |
| 5 | FEAT-025 R0 报告 | `3da4e14` | ✅ REVIEW-FEAT-025-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（P1×1〔F-1 假绿 I/O 机判〕+P2×2+P3×7） |
| 6 | FEAT-022 | `36f2040` | ✅ 轻量注册与按命令加载（`infra/registry.py` 897 行：82 命令键 + 70 CheckSpec + 受控 loader 白名单 + 导入期 join 守卫；71 测试；R5 四路机判 PASS；启动 import 零增；覆盖率 97%）；EVD-996 |
| 7 | FEAT-022/FIX-304 R0 报告 | `c87c47d` | ✅ REVIEW-FEAT-022-CODE-R0（P1×1+P2×4+P3×6 → FIX-305）+ REVIEW-FIX-304-CODE-R0（P2×1+P3×5）双机录 |
| 8 | FIX-303 R0 报告 | `70773da` | ✅ REVIEW-FIX-303-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（P1×1 提交前微补 + P3×4） |
| 9 | FIX-304 R1 报告 | `e143508` | ✅ REVIEW-FIX-304-CODE-R1 APPROVED_WITH_NOTES/unresolved_blockers=0（G-1 已修复 4/4 路径实弹对照） |
| 10 | FIX-304 | `d6d12e8` | ✅ FEAT-025 R0 遗留批 F-1~F-10 闭环 + G-1 显式入参守卫；EVD-998 |
| 11 | FIX-305 R0 报告 | `9410f80` | ✅ REVIEW-FIX-305-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（零 P0/P1/P2；F-1/F-2/F-6 回滚红绿实证关闭） |
| 12 | FIX-305 | `ebb2dce` | ✅ FEAT-022 R0 遗留批 F-1/F-2/F-4/F-6 处置；EVD-999 |
| 13 | FIX-303 R1 报告 | `f87b2fc` | ✅ REVIEW-FIX-303-CODE-R1 APPROVED_WITH_NOTES/unresolved_blockers=0（全量 2592 分类翻转归因成立） |
| 14 | FIX-303 | `4fcc354` | ✅ FEAT-021 R0 遗留批 F-1~F-13 逐条闭环 + NF-1/NF-2 提交前微补；EVD-997 |
| 15 | FEAT-026 | `2a5e9ec` | ✅ quick-scan Slice-2 编排器 + 四态契约 + shadow 通道（`--quick` 复用 FIX-270 product-gate 跳过机制；引擎仅 1 处惰性 import）；EVD-1000 |
| 16 | FEAT-026 R0 报告 | `e74c0a1` | ✅ REVIEW-FEAT-026-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（P1×1 → FIX-306 承接；S-A/S-B 真跑独立复现 chosen=45/compared=45 mismatches=0；性能实测 5.3× quick<15s） |
| 17 | FIX-307 | `4998c6d` | ✅ dsh 0.1.5-rc.2 接入兼容性修复（`skill-filesystem` UPDATE 行补 `disabled:false`）+ 头注 dsh 边界核实段 + README 恢复接入子段 + 守卫测试；R0 APPROVED_WITH_NOTES/unresolved_blockers=0；40/40 绿；EVD-1001 |
| 18 | FIX-307 R0 报告 | `73e04e5` | ✅ REVIEW-FIX-307-CODE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（15 项注释技术断言逐条对照安装态 dsh 0.1.5-rc.2 源核实矩阵） |
| 19 | FIX-308 | `031f0fa` | ✅ **真机致命项根因修复**：`@deepseek-ai/dsh-persona@0.1.5-rc.2` 声明 `prefix: z.string().required()` 而本仓 persona 行用 `text` ⇒ 单行 config 校验失败**否决整棵预设挂载**（真机实测 entries 0 → 1）；EVD-1003 |
| 20 | FIX-309 | `94c0a61` | ✅ 新增 **Check 28v `check-dsh-preset-compat`**：用真实安装的 dsh 插件 Config schema 逐行校验预设组合（不复制任何 schema——独立遮蔽实验证明）；审查链 R0 NEEDS_CHANGE/1 → R1 APPROVED_WITH_NOTES/0；EVD-1004 |
| 21 | FIX-310 | `5a259e2` | ✅ dsh 适配层**零侵入改造**（详见下节）；33 files +1034/−1324（净 −290）；EVD-1005 |

## FIX-310 交付的架构形态（逐项对照 DEC-187 I-1/I-2/I-3 机检判据）

> 本节如实描述**已交付代码**的形态，并逐项给出文件证据。**不声称「宿主平面贡献为零」**——`cordis.patch.yml` 保留**一行自有 insert**、`lib/index.js` 作为该行模块存在；此二者是「官方 `dsh plugin add` 零手工步骤即交付预设」的载体（用户 2026-09-12 要求「支持官方插件安装/卸载/升级命令 + 自定义预设设置页删除」）。判定口径见下 §判定口径。

| 面 | 交付形态 | 文件证据 |
|---|---|---|
| 宿主既有行（dsh / dsh-web-app / 其它 vendor 行） | **零触碰**——无任何 `- id: <host row>` UPDATE；无 `disabled: false` 覆盖部署方决定 | `cordis.patch.yml` 全文（1 行 insert row） |
| `!!js` 自定位 | **零**——无解析 `process.argv` / 扫描 `$DSH_HOME/profiles` 的表达式 | `cordis.patch.yml`（无 `!!js`） |
| 宿主平面注册表 | **零注册**——不注册 provider / 服务 / 工具 / settings 命名空间；不读任何宿主服务 | `lib/index.js` L33-39 边界声明 + L225-227（`apply(ctx)` 唯一动作 `ensurePreset(ctx)`）；导出面仅 `name`/`renderComposition`/`ensurePreset`/`apply` |
| 预设根 trust | **user 根**（`$DSH_HOME/.agent-presets/governance/`）——非 `system`-trust 声明。**代码事实**：写入用户根（`dsh-agent-presets` `resolvedRoots` 的第一个 user-trust 根）已在隔离 DSH_HOME 验证；**设置页显示为「自定义」/ 可删除 / 可打开目录属对宿主 UI 的推断——真机未验证**（见 §真机验收面），本表不将其作为已交付事实 | `lib/index.js` L41-44 + L176-218 |
| 唯一副作用 | 把包内预设载荷渲染为**绝对路径**写入用户自有目录（幂等：`.dsh-bundle-version` 标记；staging 目录 + 先删后改名——**存在一个极短替换窗口**：崩在窗口内则该轮无预设、下次启动重建，措辞按 RELEASE R0 P3-7 更正，不称「原子」；失败只 warn 不抛出——抛出的行会拖垮整个 dsh boot） | `lib/index.js` L161-218 |
| 技能目录来源 | **单源**——不复制 `skills/`；`customSkillDirs` 经三 token 渲染为包内绝对路径（`<plugin_root>` 即包根，核心 prose 零改动） | `agent-presets/governance/agent.cordis.yml.template`（`__GOVERNANCE_SKILLS_ROOT__`/`__GOVERNANCE_SHIMS_ROOT__`/`__GOVERNANCE_REPO_ROOT__`）+ `lib/index.js` L78-83 |
| 双交付路径一致性 | `dsh plugin add` + 重启 与 `adapters/dsh/launch.py --install` 渲染**同一模板、同一 token 契约**，输出字节一致（渲染器 parity 为机检契约） | `lib/index.js` L12-31 + `adapters/dsh/launch.py` 渲染路径 |
| 退役面 | `presets/governance/agent.cordis.yml`（292 行预烘焙副本）、`adapters/dsh/preset.yml`、`adapters/dsh/agent.cordis.yml.template`、`package.json` 死字段 `dsh.skills`（35 项）+ 其守卫扇出（`verify_workflow.py` −239 行） | `git show --stat 5a259e2` |

**判定口径（0.80.0 记录，防误引）**：DEC-187 机检判据的**意图**是「任何**既有**宿主行不被改动」；其**机械形式**（`dsh --profile web --dump-config` 安装前后）为「组合 entry 列表**恰多一行**、且该行只命名本包」。**不是**「与未安装时逐字节等价」——后者在「官方 `dsh plugin add` 零手工步骤交付预设」这一同时成立的用户要求下不可满足（bundle layer 正是 `plugin add` 的交付载体，参照实现 `dsh-novel-writing` 同形）。本候选按上述机械形式声明，不按更强口径声明。

## Candidate Gate Results（M-2 — Coordinator 回填实测）

> 本节由 M-2 打包期实测回填（2026-09-12）。候选 commit hash：**`bcb0d6d`**（`bcb0d6d786c5c1334f02ceac98403b0b311c799c`，36 文件 +1921/−49）——由 `release-ledger --version 0.80.0 --no-remote` 导出（见 #11）。
>
> **commit 后复核（M-5 回填，2026-09-12）**：`check-release --version 0.80.0 --require-changelog --lineage-mode candidate` 复跑——**`release docs` 3 项「must be tracked by git」如预测自消（FAIL→PASS）**；`archive integrity` 仍 FAIL（FIX-312 引擎假阳）、`execution gates` 仍 FAIL（governance health exit=1 + unit tests 门内 180s 超时）、`loop runtime claim gate` 仍 FAIL（`AUTHORITY_SOURCE_OCCURRENCE` + 3×`UNSUPPORTED_AFFIRMATIVE` = AUDIT-152 既有分类）。**回填期另行修复一处我方缺陷**：`check-loop-runtime-claims` 报 `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: plan-tracker ragged table row`——根因是我新增的 FIX-315 行只有 7 个 pipe（缺「状态」列），已补齐为 8；修复后该子项消失（复跑仅余既有分类项）。

| # | Gate（`python skills/software-project-governance/infra/verify_workflow.py <cmd>`） | 预期 | Result（M-2 回填实测 2026-09-12） |
|---|---|---|---|
| 1 | check-version-consistency | PASS（15 projections + bootstrap markers + REQUIRED_SNIPPETS 全 0.80.0） | **PASSED**——13 文件 + bootstrap markers（`AGENTS.md`/`CLAUDE.md`——**gate 覆盖面**，`checks/version.py` L122-137）全绿；**零 FAIL 零 WARN**（0.79.0 遗留的 plan-tracker WARN 已随本次版本回写消除）。**归属更正（RELEASE R0 P3-2）**：`adapters/dsh/AGENTS.md.template` **不在** marker 覆盖面内，它由投影守卫（projection guard）保护。 |
| 2 | check-projection-sync --fail-on-issues | PASS（15 projections，source 0.80.0） | **PASSED**——source version 0.80.0；15 mirrored files 全同步 |
| 3 | check-manifest-consistency | PASS（0.80.0 新增/退役文件面已登记） | **PASS**（实测 2026-09-12 ~09:5x，RELEASE R1 复测得 **659 canonical / 733 actual**；M-2 早期记录 657/727 为**未计时旧值**——活体计数随 staging 变化，RELEASE R1 P2-1/P3-3/N-5 更正，以测量时间为准） |
| 4 | check-cross-references --fail-on-issues | PASS（零悬空/零废弃/零循环） | **PASS**——663 引用，零悬空/零废弃/零循环 |
| 5 | verify（无参） | PASSED（既有基线失败按先例如实披露） | **PASSED**（exit 0）——files/snippets/architecture/**agent_adapter（六适配器 runtime-verified）**/version/loop_role 全绿 |
| 6 | pytest 全量 | 零新增失败（对照存量基线逐类归属） | **零产品代码新增失败；+4 全部来自本版 M-2 归档迁移（数据耦合）**。**冻结树实测**（`git write-tree` = **`58f07fca9ac84ab581d11695928e73d0f4ff6215`**，2026-09-12T10:20:31→10:32:16，`python -X utf8 -m unittest discover`）：`Ran 2675 tests in 700.871s` → **FAILED (failures=36, skipped=1) = 36**。逐族构成：**24 = WSL 环境族**（`test_pre_commit_review_evidence.ReviewEvidenceRegexTests` 10 方法 × 2 hook，实证 rc=1 + `WSL_E_DEFAULT_DISTRO_NOT_FOUND`——本机无 WSL 发行版）+ **5 = `test_hooks.PlanTrackerMatcherTests.test_replay_real_plan_tracker_hits`**（**本版新增的 +4 全部在此族**：该测试对**真实** plan-tracker 回放 6 个 0.78.x 已完成行 ID〔REL-071/REL-072/FIX-282/REL-073/FIX-283/FIX-288，`test_hooks.py` L302-313〕；本版 M-2 执行的归档迁移按引擎规则把这 10 行迁出热文件 ⇒ 4 个 ID 不再命中 ⇒ 断言失效。RELEASE R1 以 `PlanTrackerMatcherTests` 单独复跑（`Ran 14 … failures=5`）独立复现该族与其 +4 归因）+ **7 = 存量**（FIX-300 双口径 ×2〔N1 审查文档 claim 族〕/ `loop_runtime_claims` ×2〔inventory 数据耦合 + RISK-048 性能环境敏感〕/ `triage_write_guard` live 金丝雀 ×1 / `change_triage` lock WARN ×1 / `LoopRuntimeClaimAdapter` ×1）。对照 0.79.0 基线 31F+1E=32：**+4 归因 = M-2 归档迁移的数据后果**（AUDIT-152 N2「归档致 authority 离热」族的放大），**不是产品代码回归**；**零产品代码相关新增失败**。**自我披露（两处）**：① 修复期我的 README 改述曾引入 1 个真实新失败（`test_readme_evidence_levels.test_real_repo_readme_claims_all_annotated`——`dsh-session-projection` claim 行失去证据等级标注），**已修**（补 `〔static: …〕`，该模块 8/8 OK）；② Code R0 F2 的 warn-only 契约修复（`lib/index.js`）后本行数值由 35F+1E 变为 36F+0E（同一族构成，仅一个既有用例的归类由 ERROR 变 FAIL）——**修复未引入新失败**，`test_dsh_adapter` + `test_dsh_compat` **Ran 89, OK**。**门内口径披露**：`check-release` 的 execution gate（180s 上限）对同一套件报 `exit=None`（超时，**不可判**）——本行以独立长跑为准。**RELEASE R1 N-3 处置**：上一版记录的全量实测树为 `ef20d026…`（与本版差 10 文件，全为注释/文档面）；**本行数值取自最终钉住树 `58f07fca…`**，故 N-3 已闭合 |
| 7 | check-governance --summary-only | 零新增缺陷类（对照基线构成） | **65 issues，exit 0**（实测 2026-09-12T09:53:59，HEAD `5a259e2` + 工作树；**双审各自复跑得 62 / 65——本行数字为活体数据耦合项，随 `.governance` 写入漂移，故以测量时间为准**，RELEASE R0 P2-1/P3-3）。`--level strict` 桶构成（同刻）：`function_size` ×6 + `module_size` ×1（e2e 镜像 advisory）／FEAT-023/024/026/027 各 ×5 + FEAT-025 ×1（Check 18d 契约字段完整性，**治理元数据债务，零功能影响**，本版不补写，登记后续批次）／`UNSUPPORTED_AFFIRMATIVE` ×3（loop claim 门 AUDIT-152 既有分类）／`hooks_drift` ×2（`.git/hooks/post-commit` + `prepare-commit-msg` 陈旧——pre-commit/commit-msg 已在本次 commit 尝试中自升级 v0.80.0；agent 不写 `.git/hooks`，故按先例披露）／locks ×7／closure ×7／structural 417（**0 blocking**）／`untracked` ×2（候选中，commit 后自消）／缺 R1 证据行 ×2／machine-provenance WARN ×2／M5.4b ×1／DEC-ID gaps／`release_docs_versions` ×1／archive integrity ×1（见下）。**与 0.79.0 基线 33 的 +32 已逐条归类**（+25 FEAT 契约字段／+4 untracked→commit 后自消／其余为活体漂移与新增 advisory 读数），**无新增缺陷类** |
| 8 | check-injection-contract | PASS（锚点面 0.80.0） | **PASSED**——3 文件 / 23 anchors。**实测对照**（v0.79.0 worktree `17eda48` 运行同一命令 = 4 文件 / 28 anchors）：本窗**移除 2 个锚点承载文件**（`adapters/dsh/agent.cordis.yml.template`、`presets/governance/agent.cordis.yml`）+ **新增 1 个**（`agent-presets/governance/agent.cordis.yml.template`）——即 FIX-310 退役的两份副本；**核心 prose 零改动**。 |
| 9 | check-dsh-preset-compat（Check 28v，FIX-309 新增） | PASSED（真实安装 dsh schema 逐行校验） | **PASSED**——组合 1 / enabled rows 23 / **schema-checked rows 18**；oracle = `@deepseek-ai/cordis@4.0.2` + `cordis-plugin-include@1.0.7` + `cordis-plugin-loader@1.0.3` + `js-yaml@4.3.2`（自 `DSH_HOME/profiles` 解析）；隔离 temp DSH_HOME，**writes: 0** |
| 10 | check-release --version 0.80.0 --require-changelog --lineage-mode candidate | 核心静态门禁 PASS + 既有基线 FAIL 分类披露 | **静态：version consistency / release fact source / hot fact source / runtime readiness matrix / first session measurement / governance pack status / agent adapters / projection sync / cross references / release lineage / gate sequence / one dot zero blockers 全 PASS**；execution gates：`verify` PASS / `e2e check` PASS / **`dsh upgrade regression` PASS**（隔离 temp DSH_HOME 预设会话冒烟，零真实 home 写入）/ `loop fuse block` PASS / `changelog` PASS；**`archive integrity` FAIL（M-3 修复期新增，见下）**；**FAILED - 10 issue(s)**，构成 = ① release docs ×3「must be tracked by git」〔**候选中——commit 后自消，M-2 复核**〕② **archive integrity ×1（新）**③ execution gates 汇总 FAIL（其下 governance health exit=1〔见 #7〕+ unit tests 门内 180s 超时〔见 #6 披露〕）④ loop runtime claim gate（`semantic_verdict=BLOCKED` / `identity_verdict=PASS` / candidates=722 parsed=722——**AUDIT-152 既有分类**：N1 审查文档 affirmative + N2 归档致 authority 离热；**零新增类**）。**W-1 披露**：本仓无凭据，CI ubuntu 权威面未跑（发布后补跑义务登记） |

**⚠️ archive integrity FAIL（M-3 修复期新增，已定位为**引擎缺陷**，非本版内容缺陷）**：DESIGN R0 F4 指出归档迁移（本版 M-2 期执行）把 **DEC-187**（2026-09-12 现行治理裁决）从其热 `decision-log.md` 误迁至 `archive/decisions/decisions-v0.1.0-0.78.1.md`（记 "归档版本: v0.77.0"）并写入 `archive/index.md`。处置按 FIX-169 先例**回迁热文件**（删归档节 + 删 index 条目 + 行内补 DEC-188 澄清注记）。**副作用（如实登记）**：回迁后 `check-archive-integrity` 复报 `Archive trigger gap: 0 hot completed task(s) ... release_forced`（0 task、**1 decision**）——`analyze_auto_archive_candidates()` 实测 `decisions_archived=1`、`explain` 指认 `would_archive: DEC-187 / detail: v0.77.0`：**引擎按"任一被引 task 已归档"给 decision 归版，而 DEC-187 的关联列含 `FEAT-010`（v0.77.0，已归档）**，遂把一条当天新产生、其 governing task（FIX-307~310，0.80.0 活跃）未归档的决策判为可迁 ⇒ 假阳。**本版不修引擎**（属独立任务），已登记 **FIX-312**（P2，含最小修复方向与必备回归 fixture）。故该 FAIL **不是本版交付内容引入的**：回迁前的 PASS 状态恰恰是"现行裁决被误归档"换来的。
| 11 | release-ledger --version 0.80.0 --no-remote | NATIVE_CANDIDATE（candidate commit 后） | **PASS（M-5 回填）**——`state: PASS`，`trust_level: NATIVE_CANDIDATE`，`candidate_commit: bcb0d6d786c5c1334f02ceac98403b0b311c799c`，`effective_state.lifecycle_state: candidate`，`release_authorized: false`，`events: []`（candidate_to_released 事件与 integrity 待 M-4 用户授权后追加——0.79.0 先例）；`event_identity_digest: 37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` |
| 12 | quality-tools | NOT_RUN 如实记录（Ruff/mypy 未安装——ADR-010 不虚构 PASS） | **NOT_RUN**（五工具实证未安装——如实，不虚构 PASS） |
| 13 | check-release --version 0.80.0 --require-changelog --lineage-mode released --release-commit \<commit\> | （M-6 释放态） | 待 M-6 回填 |
| 14 | release-ledger --version 0.80.0 --remote github-https | （M-6）NATIVE_RELEASED PASS | 待 M-6 回填 |

**新增 advisory 披露（M-2 实测，非本版引入）**：`check-governance-data-size`（Check 28s，advisory `fatal_on_error=false`）报 **2 ERROR**——`.governance/plan-tracker.md` 301.3 KB、`.governance/evidence-log.md` 1450.3 KB，均超 `error_bytes=250000`。**RISK-039（治理数据膨胀）本版不关闭**；本版已执行一次真实归档迁移（见下）但 evidence-log 的迁移门控（`live_or_unresolvable_task_ref=308` / `no_task_family_ref=86` / `ref_version_out_of_range=25`）使大部分行按设计保留热文件——**处置属独立任务，不在本版范围**。

**归档迁移执行证据（本版 M-2 期执行）**：备份 `.governance` 全量 1769 文件 → `%TEMP%\governance-backup-20260912-rel076`（R1(b) 三选一留痕）→ `archive.py migrate --auto --dry-run` 预览 → 实跑：归档 **v0.1.0~v0.78.1** 范围 **10 task + 38 evidence + 5 decision → 0 risk**；`check-archive-integrity` **PASS**（hot 85 / archived 91 / index 1081 / total 176）；`check-release` archive integrity 门由 FAIL 转 **PASS**。审计解释面：tasks 扫描 135 中 `pipe_layout_anomaly=15` 未知结构按 P7 **不强删**（仅报告）。

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——0.76.0/0.77.0/0.78.1/0.79.0 先例：以可逆性分析 + 门禁复跑为验证载体）：见 `docs/release/rollback-plan-0.80.0.md`。

## 真机验收面（**未在本候选内验证**——如实披露）

以下三项目标**只有用户真实 dsh 环境**能验证，本候选**不声明**其成立（`adapters/dsh/README.md` 已登记恢复接入路径）：

1. 设置页「自定义」标签 + 删除 + 打开目录三项 UI 行为；
2. 非治理预设（如 `standard`）会话**不含**治理技能（FIX-310 的核心行为目标）；
3. 治理预设会话技能目录完整性。

命令（用户侧）：`dsh plugin --profile web add "link:D:/AI/agent/claude/coding/project_management_workflow"` + 重启。隔离环境已验证面：Check 28v PASSED、`test_dsh_adapter.py` 488 行改动全绿、`launch.py --smoke` 隔离 home 零真实写入、`dsh_compat.py` 18 行组合 manifest。

## Review Evidence（M-3）

- 任务链审查终态（已机录）：本窗 21 commit 中 **9 个为审查报告入库**（RELEASE R0 更正，原记 8）。**报告落位披露（RELEASE R0 §3.4）**：FIX-308/FIX-309 的 R0 报告仅存在于 **gitignored 的 `.governance/`**（`review-FIX-308-CODE-R0.md` 等），**不在 `docs/reviews/`**——外部读者无法从仓库核验这两份报告；`docs/reviews/` 可核的是 FIX-307、FEAT-021/022/025/026、FIX-303/304/305 等报告。其余任务链（FEAT-021/022/025/026 与 FIX-303/304/305）全链 APPROVED 或 APPROVED_WITH_NOTES/unresolved_blockers=0。
- **FIX-310 审查面披露**：原 R0/R1/R2 三轮审查因建立在不成立的缺陷前提（虚构需求「任何预设的会话都需看到 /governance」）上，**全部作废**（DEC-187）。
- **M-3 候选双审（对 v0.79.0..candidate 全窗）**：
  - **REVIEW-REL-076-DESIGN-R0 = NEEDS_CHANGE / unresolved_blockers=2**（2026-09-12，报告 `docs/reviews/review-REL-076-DESIGN-R0.md`，机录 `.governance/review-REL-076-R0.md`）。**架构面经机检验证为 sound**（1 行 insert / 0 UPDATE / 0 可达 `!!js` / `ctx.*` 仅 `ctx.logger` / 无运行时依赖 / 两条渲染路径 SHA256 逐字节一致且已有测试覆盖 / warn-only 在敌意 `DSH_HOME` 下实测不抛 / 无复制 `skills/` 树 / 退役面在代码与清单侧完整、相关测试 46+295 全绿）。**两条 P1 阻塞项均为文档与治理裁决不一致**：F1（`project/CHANGELOG.md:19` 同时断言「逐字节等价」与「宿主平面贡献归零」两条**已被 DEC-188 取代**的措辞）、F2（`README.md:33/:76/:392` 仍称治理技能在**该 profile 的每个会话**中加载——FIX-310 已把该语义退役，与本版核心行为目标相反）。**处置：F1/F2 已就地修复**（CHANGELOG 改述 DEC-188 ② 判据 + 宿主既有行零触碰；README 三处改为「仅治理预设的会话」并显式标注真机确认未完成）。
  - **同轮 P2/P3 处置**：F3（`session-snapshot` 判据行补 DEC-188 更正框）已修；F4（**归档迁移把 DEC-187 误迁出热文件**——见上 §archive integrity FAIL）已按 FIX-169 先例回迁并登记 **FIX-312**；F5（`data-inventory-0.80.0.md:175-176` 三个已退役符号仍记为 live）已改标退役；F6（checklist 把 RISK-050 说成「结构性根因消除」过宽——FIX-308 的 preset-config-key 腿由 advisory Check 28v 护栏而非消除）已改述为「一条腿消除 + 另一条腿护栏」；F7（DEC-187 自身要求的后续交付未履行——I-1/I-2/I-3 未落入 `core/protocol/plugin-contract.md`）**已补**（新增「宿主方承诺：架构不变量 I-1/I-2/I-3」节，含机检判据与五条导出禁令）；F10（`dsh-preset-adapter-0.73.0.md:31` 仍记已删除的 `--mode copy`）已加 0.80.0 更正框；F11（`lib/index.js:44` "`dsh plugin remove` stays symmetric" 与 `launch.py:36-38` 相反）已改述为「remove 管 bundle 层、不能删用户根预设 + 删除非持久」。
  - **F8/F9（P3，本版不修，登记 FIX-313）**：孤立 `\r` 归一化分歧（latent，当前模板实测一致）；`lib/index.js` catch 分支不清理自身 `.staging-*` 目录（已核实不被 roster 可见——`dsh-agent-presets` 按 `^[a-z0-9][a-z0-9-]*$` 过滤）。
  - **审查方明确 `未知`（不阻塞）**：真机验收面（U-1）；参照实现引文的可核性（U-2——**注：`dsh-novel-writing` 实际位于 `D:\AI\agent\deepseek\harness\writing-workflow`，Coordinator 简报未给路径导致审查方无法核验，属简报缺陷而非事实缺陷**）；跨根路径稳定性（U-3，已并入 FIX-313 邻域）；registry 安装形态（U-4，`package.json` `private: true`，已文档化安装均为 `link:`/`file:`/`github:`）；**post-DEC-187 缺少针对 `lib/index.js`/`launch.py` 的 Code 审查（U-5，登记为流程缺口——本 R0 仅为设计半面）**。
  - REVIEW-REL-076-RELEASE-R0 = **NEEDS_CHANGE / unresolved_blockers=2**（2026-09-12，报告 `docs/reviews/review-REL-076-RELEASE-R0.md`）。**P0 = 无**；两条 P1 与 DESIGN R0 的 F1/F2 **互相独立地**命中同一处（CHANGELOG 断言 DEC-188 已撤下的两句 + README 承诺"每个会话"）——均已修复。同轮结论：变更清单 **21/21 commit 一一对应**；回滚计划内部一致且**无静默重新引入已退役架构的路径**；`archguard-ratchet` PASS（0 violations，R7 committed==fresh）；`cleanup.py --dry-run` 干净；`check-release` FAILED 9→6 = 恰好为预测的「release docs ×3 随 commit 自消」；另独立验证 `dsh plugin` 是 pnpm 转发器并 reconcile `dsh.profile.bundles`（佐证 rollback plan 依赖的 add/remove 机制）。P2/P3 处置见下（P2-1/P2-2/P2-3/P2-4/P2-5/P3-2/P3-7/P3-8/P3-9/P3-10 已修；P2-6 见 FIX-314 + 下方记录口径；P3-4 按「先 stage 后审」钉住）。
  - **R1 复审轮（对钉住树 `88915ed2606154219561c3828f23dbf390b4dbe2`，`git write-tree` 双向核实未移动）**：**REVIEW-REL-076-DESIGN-R1 = NEEDS_CHANGE / 1**（报告 `docs/reviews/review-REL-076-DESIGN-R1.md`）——R0 的 F1~F11 **全部关闭**（F1/F2 已核实于 **staged index blob**，非仅工作树；撤下措辞全域扫描 `宿主平面贡献归零` = 0）；新增阻塞项 F13 = 我在修复 P3-10 时**引入**的新失实陈述（`README.md:92` 称 `v0.80.0` 已打 tag——事实上不存在该 tag），**已修**。**REVIEW-REL-076-RELEASE-R1（round 2 槽）= NEEDS_CHANGE / 2**（报告 `docs/reviews/review-REL-076-RELEASE-R1.md`）——R0 的 P1-1/P1-2/P2-2/P2-4/P2-6 与 P3 多数**已关闭**；N-1 = 同上 F13（**两位审查方独立命中同一处**）；N-2 = 我在补 P2-3(a) 时写入的 `files` 白名单失实（称"收敛为 `lib/` + `agent-presets/`"，实际保留 11 项），**均已修**；N-3 = full-suite 实测树 `ef20d026…` ≠ 钉住树（二者差 10 文件，均为注释/文档面）——**已按"修复后重钉 + 在最终树上重跑全量"处置，见本表 #6 的树哈希注记**。**两轮均确认回滚/部署面在修复后仍然成立**。（2026-09-12，报告 `docs/reviews/review-REL-076-CODE-R0.md`，机录 `.governance/review-REL-076-R3.md`，round 3 槽位）
  - **REVIEW-REL-076-CODE-R0 = APPROVED_WITH_NOTES / unresolved_blockers=0**（2026-09-12，报告 `docs/reviews/review-REL-076-CODE-R0.md`，机录 `.governance/review-REL-076-R3.md`，round 3 槽位）——**补上 U-5 缺口**（DEC-187 之后 `lib/index.js` 与新 `launch.py` 从未经 Code 审查）。**已机检确认 good（不再复议）**：渲染器 parity 在**三条独立路径**（JS `ensurePreset` 文件 / Python `render_composition` 文本 / `launch.py --install` 文件）产出**同一 SHA256 `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`**；三 token 集/POSIX 拼写/无尾分隔符/LF 一致；`--dry-run` 零写入；`--uninstall` 范围受限且幂等；`--smoke` 隔离真实（witness 不变，exit 0/1/2 精确）；`dsh_compat.py` **确实内嵌零 schema 副本**（从解析出的安装态 import `entryListSchema`/`evaluate`/`isJsExpr`/`resolveConfig`）并在无 node/无安装/0 enabled 行时降级 NOT_RUN；`lib/index.js` 是合法的具名导出 Cordis 行。**并推翻 DESIGN-R0 的两条判断**：(a) DESIGN-R0 对"`resolveDshHome()` 只读环境字符串、不会抛"的结论**被证伪**——见下 F2；(b) DESIGN-R0 的 U-3（跨根路径稳定性）**被反证**——经 Windows junction 时 `import.meta.url` 解析真实路径，JS 与 Python 在 `link:` 安装下仍一致。
  - **Code R0 的 P1（F1，已登记不阻塞本版）**：Check 28v 对 **5 个 `NO_SCHEMA` 行**（`plan-mode`、`command-compact`、`tool-subagent-control`、`tool-subagent-list-agents`、`tool-ask-user`）无法校验——实测 `plan-mode` 行给 `config:{bogusKey:1}` 时护栏返回 **PASS / checked 0 / issues []**，而安装态该插件自己的校验器会拒绝（`PlanModeConfig needs a string 'section'`）。**已披露的数字口径使其不是"静默全绿"**（`enabled 23 / schema-checked 18` 见本表 #9 与 `reason`），但 `NO_SCHEMA` 的 docstring「loader 会原样透传、不做校验」对这些插件**不成立**，`launch.py:566` 亦传播 `schema_checked=True`。**登记 FIX-315**（最小修复：`rows_checked==0` → NOT_RUN；不再把 NO_SCHEMA 行称作已校验），**本版不修**。
  - **Code R0 的 P2 已修复（F2，破坏"warn-only"契约）**：`ensurePreset()` 中 `resolveDshHome()` 原在 `try` **之外** ⇒ HOME/USERPROFILE/DSH_HOME 全未设时 `homedir()` 抛 `SystemError uv_os_homedir ENOENT`，异常穿出 `apply()`——与模块自身策略及**三份发布文档的 warn-only 声明矛盾**（宿主行抛错会拖垮整个 dsh boot，正是 0.80.0 要修的最坏后果）。**已修**：`resolveDshHome()` 与 `userDir` 全部移入 `try`，catch 与 warn 调用改用 `ctx?.logger`，并顺带在 catch 内做本模块 `.staging-*` 自清理（Code F4；清理自身包在 try 内、绝不外抛）。**验证**：剥离环境变量的 node 探针 `apply({})` **不再抛出**（返回 outcome）；`test_dsh_adapter` + `test_dsh_compat` **Ran 89, OK**。**披露**：该探针把渲染结果写入了本机真实 `%USERPROFILE%\.dsh\.agent-presets\governance\`（我未先重定向 `DSH_HOME`——违反本项目"验证一律用重定向 home"的纪律，如实登记）；写入内容与文档化 parity 哈希**逐字节相同**（`00e0d330…`），`preset.yml` 未被改动，DSH_HOME 其余内容未触碰。
  - **Code R0 其余 P2/P3（登记不修）**：F8（`dsh_compat.py` 探针报告非 UTF-8/截断 ⇒ `UnicodeDecodeError` 穿出公共入口且泄漏 2 个临时目录；`verify_workflow.py` 调用点无 try ⇒ 可中断 check-governance 引擎）、F9/F3（UNREADABLE 组合的 `reason` 失真；`leftovers` 守卫对拼错 token 无效——拼错的 token 会被静默写入，仅 `--smoke` 的字面相对路径检查兜底）、F5（版本 `'0'` 是**掩盖**而非抖动）、F7（带空白的 `DSH_HOME`：内联解析器 **trim**，而安装态 `@deepseek-ai/dsh-home-paths` 与 `launch.py` **不 trim** ⇒ 该输入下两条路径落点不同，"cannot disagree" 对该输入不成立）、F10（`launch.py` 中 `!!js`/`baseUrl` 分支与 `urllib` import 在 FIX-310 后已成死代码）、F11（`test_dsh_compat.py` 两个测试断言同一文件）、F12（`registry.py` 注释计数 83/71/79 vs 实际 82/70）、F13（权威文档 `quickscan-evaluation-0.79.0.md:134` C1 仍列 Check 40 且漏 28v）、F14（`verify_registration` 静默去重重复观测）→ **FIX-316**（F2/F4/F6/F7 邻域与 FIX-313 合并处置）。**测试覆盖缺口披露（Code R0）**：`lib/index.js`、渲染器 parity 机器契约与 warn-only 的**唯一**覆盖在 `test_dsh_adapter.py:1133-1135/1164-1166/1217-1219`，受 `shutil.which("node")` 门控；`test_dsh_compat.py` 有 14 个 live-oracle 测试受 node/dsh 安装门控、5 个受 PyYAML 门控——**在无 node 的机器上，打包预设的宿主行路径实际未被测试**；且既有"never throws"测试只覆盖 payload 缺失模式，因此**抓不到 F2**（已按此补修）。
  - **M-3 记录口径（FIX-314 受限下的合规处置）**：`review_record.py` 以 `(task, round)` 为唯一键 ⇒ 同一轮只能存一位审查方。设计半面占 `(REL-076, 0)`、Release 半面按 `--round 2`、Code 半面按 `--round 3` 记录（三者均经 CLI，`evidence_row_written=true`）；**round 编号在此不代表修复轮次**，仅为绕开键冲突的合规落位，已登记 FIX-314 修正键为 `(task, round, reviewer)`。**未采用**：手写 REVIEW 证据行（M7.5 明确违规）与覆盖他方记录的 `force=True`。
- 证据：EVD-995~1001、EVD-1003（FIX-308 根因诊断）、EVD-1004（FIX-309）、EVD-1005（FIX-310）。

## 出槽登记（无隐藏带入）

- **FIX-312（P2，本版登记）**：归档引擎决策归属误判——新决策因引用历史已归档 task 被归入旧版本范围并迁出热文件（实证 DEC-187；本版 archive integrity FAIL 的成因）。含最小修复方向与必备回归 fixture。
- **FIX-313（P3，本版登记）**：FIX-310 实现面两处已核实未修的潜在缺陷（孤立 `\r` 归一化分歧 latent；`lib/index.js` catch 分支不清理自身 `.staging-*`——已核实不被 roster 可见）。
- **FIX-314（P2，本版登记）**：`review_record.py` 以 `(task, round)` 为唯一键 ⇒ **同一 task 同一轮无法记录两位审查方**（本版 M-3 双审的 Release 半面因此被 CLI 拒绝，exit 2；报告见 `docs/reviews/review-REL-076-RELEASE-R0.md`，机器记录改用 round=2，见 §Review Evidence）。键应扩展为 `(task, round, reviewer)`。
- **FIX-315（P1，本版登记，不阻塞）**：Check 28v 对 NO_SCHEMA 行零校验却报 PASS（5/23 enabled 行；护栏可信面小于声明面）。
- **FIX-316（P2，本版登记）**：`dsh_compat.py`/`launch.py` 健壮性、死代码与口径遗留批（Code R0 F3/F5/F7/F8/F9/F10/F11/F12/F13/F14——含可中断 `check-governance` 引擎的 `UnicodeDecodeError` 路径）。
- **流程缺口（RELEASE/DESIGN R0 共同指认的 U-5，**本版已闭合**）**：DEC-187 之后 `lib/index.js` 与改造后 `launch.py` 的 Code 审查缺口，由 **REVIEW-REL-076-CODE-R0（APPROVED_WITH_NOTES/0）**补上（round 3 槽位）；其 P2 F2 已当场修复（warn-only 契约），P1 F1 与其余 P3 登记为 FIX-315/FIX-316。
- **仓库外部可核性缺口（RELEASE R0 §3.4）**：FIX-308/FIX-309 的 R0 报告只存在于 gitignored `.governance/`，外部读者无法从仓库核验；补入 `docs/reviews/` 属后续批次。
- **历史 commit message 失实（RELEASE R0 P3-6，不可修）**：`5a259e2` 正文写「规模 10 文件 +296/−552（净减 256 行）」，实际 `git show --stat` = **33 files, +1034/−1324**。改写已发布 commit message 属不可逆操作（禁止），故**如实披露**；发布文档使用正确数字。
- **本机 hook 陈旧（RELEASE R0 P3-5）**：`.git/hooks/post-commit`=0.79.0、`prepare-commit-msg`=0.75.0 vs 源 0.80.0（pre-commit/commit-msg 已自升级）。agent 按安全约束不写 `.git/hooks`；用户侧一次性命令见 bootstrap。
- **版本承载面在三个版本门禁之外（RELEASE R0 P3-1，informational）**：`commands/governance-init.md:197/262/533`（+e2e 镜像）、`project/e2e-test-project/CLAUDE.md:5`、三件套 `**Version**` 行、`core/releases/0.80.0.json:"version"`——**本次均为 0.80.0，无失配**；属潜在缺口（无门禁守），登记。
- FIX-306（FEAT-026 R0 P1 承接）、FIX-311（FIX-309 R1 P2 遗留批）→ 0.80.0 后续批次，**不在本版**。
- QUICK-SCAN Slice-3、FEAT-021 §7.2 `RecordScope`/`LogicalRecord` 全集（留待 record-model 切片）、FEAT-022 R5 棘轮消费 registry 扩面、registry 聚合切片（NF-3 前置）、跨包半边（FIX-305 F-4）、REQ-109/111/113/114 → 0.80.0 后续。
- `dsh_compat.py` 归属（core `infra/` → `adapters/dsh/`，core→dsh 耦合）**未裁决**——维持现状，登记为已知偏差候选（`core/protocol/plugin-contract.md` 记录或迁移，二选一待 DEC）。
- RISK-044 残余面（live/headless 会话面等级、非 dsh 适配器等级映射）、RISK-045/046/047/048 维持观察（本版不改变任何风险状态，RISK-050 除外）。

## No-overclaim Boundaries

This candidate does not create or prove `v0.80.0` and does not close RISK-036 or RISK-039. 0.80.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-050 本版交付**一条腿**的结构性根因消除（上游内部行 UPDATE 面 + `!!js` 自定位面退役）但**维持打开**——**另一条腿未消除**（组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema，含 `dsh-persona.config.prefix`；dsh 再改这些行的 schema 时同类漂移仍会发生，由 advisory 级 Check 28v 前移到 CI 护栏而非消除）；收口条件 = 真实环境验收 + 复评窗，**不声明关闭**；RISK-044 缓解中（本版不改变）；RISK-046 根因修复已交付维持打开至 2026-09-30 复评窗；RISK-047/048 维持观察；RISK-049 已关闭（DEC-185，非本版范围）。No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

- candidate-only：`release_authorized=false`——transition/tag/push 待用户授权（DEC-143，M-4 唯一人工门）。
- Breaking changes：见下节。
- DSH 接入时滞：bundle 安装路径 `dsh plugin --profile <name> add <ref>` + **重启**（bundle layer 为 boot 期生效，非 HMR）；手动/离线路径 `python adapters/dsh/launch.py --install`。未重启/未 install 不宣称会话级效果。

## Breaking Changes

1. **dsh 安装形态变更**：预设供给路径由「UPDATE dsh 自己的 `agent-presets` 行、追加一个 `!!js` 计算出的指向包内 `presets/governance/` 的 root」改为「insert 本包自己的行 → 该行模块把预设渲染写入**用户预设根** `$DSH_HOME/.agent-presets/governance/`」（用户 2026-09-12 明确要求可删除）。**用户可见差异（设计预期）**：设置页标签为**「自定义」**、可删除、可打开目录——**代码事实（写入 user-trust 根）已在隔离 DSH_HOME 验证，宿主 UI 三项行为真机未验证**（见 §真机验收面）。对 dsh 既有行的触碰归零。
2. `package.json` 结构性变更（RELEASE R0 P2-3(a) 补全 + R1 N-2 更正）：新增 `type: module` / `main: lib/index.js` / `exports` / `engines: node >= 20`（宿主行模块为 ESM，且只在 node ≥ 20 的 dsh 上加载）；`files` 白名单**保留原有 11 项**（`lib/`、`agent-presets/`、`skills/`、`commands/`、`agents/`、`adapters/dsh/`、两个 `!` 排除项、`cordis.patch.yml`、`README.md`、`LICENSE`）——实际变化是**新增 `lib/` 与 `agent-presets/`、移除 `presets/`**，**不是**「收敛为两项」；**移除死字段 `dsh.skills`**（35 项）——该字段经全量核实 dsh 核心从不读取，其守卫扇出（`verify_workflow.py` −239 行，含 `check_dsh_skills_manifest` 及其数据面）同步退役。
3. 退役的重复面**四处**（RELEASE R0 P2-3(b) 补全）：`presets/governance/agent.cordis.yml`（292 行预烘焙副本）、`adapters/dsh/preset.yml`、`adapters/dsh/agent.cordis.yml.template`（旧模板副本）、以及上述 `dsh.skills` 字段/守卫面——统一为 `agent-presets/governance/agent.cordis.yml.template` **单源模板**。
4. **其它五个适配层与核心规则零改动**：`skills/*/SKILL.md`、`commands/`、`agents/` 仅版本行/路径引用同步。**证据口径（RELEASE R0 P2-3(c) 更正）**：`check-injection-contract` PASSED（3 文件 / 23 anchors，锚点存活）+ 本窗 `skills/`、`commands/`、`agents/` 的 diff **仅版本行**（`git log v0.79.0..HEAD --stat -- skills commands agents` 可核）——**不**把锚点检查当作「逐字节零改动」的证明。
