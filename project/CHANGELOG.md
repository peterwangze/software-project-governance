# 变更日志

本文件记录 `software-project-governance` 的每个版本变更。

## [0.64.1] - 2026-07-10

### 0.64.1 — marketplace.json source 改回 "./" 恢复本地/离线安装能力（FIX-186）（PATCH）

0.64.1 是 PATCH——修复 0.62.0 引入的离线安装回归。用户反馈：在网络受限环境，下载 zip 后解压到本地目录，通过 `/plugin marketplace add <本地目录>` + `/plugin install` 安装时，install 仍访问 GitHub 导致失败。根因：0.62.0（REL-051/DEC-093）为适配 zcode marketplace 把 `.claude-plugin/marketplace.json` 的插件 source 从 `"./"`（相对路径，读本地 marketplace 目录）改成 `{"source":"github","repo":"peterwangze/software-project-governance"}`（git source，install 时 clone GitHub）。Claude Code/zcode 的 `/plugin install` 按 marketplace.json 的 source 字段决定取插件内容——`github` source 触发联网 clone，`"./"` 读取本地目录。修复：source 改回 `"./"`（恢复 0.61.2 配置），保留 repository/homepage 做元信息。zcode 调查确认 `"./"` 兼容（zcode marketplace add 支持 local path + 复用 Claude marketplace 协议）。

### Fixed
- **FIX-186 — marketplace.json source `"./"` 恢复**：`.claude-plugin/marketplace.json` 插件 source 从 `{"source":"github","repo":"..."}` 改回 `"./"`（相对路径指向 marketplace 根）。插件是单仓自包含（skills/commands/agents/adapters 在仓根），`"./"` 让 install 读取本地 marketplace 目录而非联网 clone。影响：本地 add + install 全程不联网（恢复 0.61.2 之前能力）；远程 `/plugin marketplace add owner/repo` 仍可工作（clone 整个仓后 `"./"` 指向 clone 目录根）。

### Changed
- 版本声明同步到 0.64.1：4 plugin.json、marketplace.json、package.json、SKILL.md、manifest.json、verify_workflow.py REQUIRED_SNIPPETS、4 hook @version + e2e fixture 版本指针。

### Migration Notes
- **行为变更（breaking）**：`/plugin install https://github.com/peterwangze/software-project-governance.git` 直接 git-URL 安装路径不再可用（source 不再是 github 对象）。标准 `/plugin marketplace add` + `/plugin install software-project-governance@spg` 在所有场景（本地/远程/离线）都工作。
- **离线/网络受限环境**：下载 zip → 解压到本地目录 → `/plugin marketplace add <本地目录路径>` → `/plugin install software-project-governance@spg`——全程不联网。

## [0.64.0] - 2026-07-09

### 0.64.0 — 入口确定性重构（resolve_entry.py 双 root 模型 + WORKFLOW_HOME 消除 + 版本权威源切换）（MINOR，DEC-096）

0.64.0 是 MINOR——入口架构级重构（非纯 bug fix）。用户反馈 `/governance` 入口三大缺陷：(1) 版本激活探测不自洽（安装 0.63.4 实际激活 0.54.1）；(2) 依赖未定义的 `WORKFLOW_HOME` 环境变量（全仓 grep 零设置点）；(3) 入口靠 LLM 推理，启动成本 5min+/十万 token。本 release 用确定性解析器替换 LLM 概率推理，并把版本权威源从滞后的 `installed_plugins.json` 切到 SKILL.md frontmatter。**避免 0.54.2/0.54.3 回归（DEC-080/RISK-038）的关键设计**：双 root 模型——PLUGIN_HOME（从 `__file__` 推导，仅定位可执行文件+读 SKILL frontmatter active_version 权威源）vs HOST_PROJECT_ROOT（从 cwd/平台/显式 `--project-root` 解析读事实源，绝不从 `__file__` 推导）+ fail-closed。RISK-040（双 root 发散测试 + 真实宿主项目验证）已 PASSED——验证在独立 host project/e2e-test-project 上（scenario_hint=F there vs D in dev repo，证明读 host 不读 plugin-self）。经 DEC-090/091 降级 SoD 沿用——产品代码由 Coordinator spawn Governance Developer + 只读 Code Reviewer，本 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0 审查。

### Added
- **AUDIT-129 — `/governance` 入口确定性重构诊断 ADR**（commit 77df046）：基于本会话入口架构深度探索（Explore sub-agent 全映射入口设计：版本检测三机制/WORKFLOW_HOME 14 处引用/三层入口 prose/manifest 结构）+ 0.54.2/0.54.3 失败链考古（RISK-038/AUDIT-115/EVD-577~587/DEC-080），产出入口架构 ADR（docs/）。核心结论：三缺陷同根——确定性工作（路径/版本/状态）与语义工作（场景判断）混淆且全部以自然语言编码交由 LLM 概率执行。关键设计约束（DEC-080/RISK-038）：双 root 分离——PLUGIN_HOME vs HOST_PROJECT_ROOT 绝不混用。详见 EVD-668, DEC-096。
- **FX-130 — resolve_entry.py 确定性入口解析器 + 20 测试**（commit c7a9942）：新增 `infra/resolve_entry.py`（352 行纯 stdlib，不 import verify_workflow）+ `infra/tests/test_resolve_entry.py`（328 行 20 测试）。双 root 模型（DEC-080/RISK-038 C1-C4 全满足）：PLUGIN_HOME=Path(__file__).resolve().parent.parent（仅定位可执行文件+读 SKILL frontmatter active_version 权威源）；HOST_PROJECT_ROOT 从 --project-root/cwd 解析（绝不从 __file__）；fail-closed（root 不可解→resolved_root_ok=false+diagnostic+安全默认，事实读取块结构性不可达）。输出 12 字段 JSON。RISK-040 C3 发散测试（0.54.2/0.54.3 缺失的）：两独立 temp dir + 9.9.9 vs 1.2.3 版本断言 + 插件自身 .governance/ 种入断言不泄漏。Code Reviewer R0 APPROVED_WITH_NOTES（6/6，0 P0/P1，4 P2）。详见 EVD-669。

### Changed
- **FX-131 — 入口 prose 重构 + WORKFLOW_HOME 消除 + 版本权威源切换**（commit d70b9f3）：4 commands root + 4 e2e mirror + AGENTS.md 接入 resolve_entry.py。**WORKFLOW_HOME 消除**：commands/ 44→5（全说明性注释零活跃考古）+ canonical 4 层优先级 resolve 块全删。**决策树收敛**：governance.md 25 行 ASCII 树→scenario_hint 指针（resolved_root_ok==false fail-closed）。**版本权威源切换**：版本比较→scenario_hint=="C"（active_version SKILL frontmatter）；GOV-ERR-004 降级检测保留 LLM 侧。**check_plugin_freshness 降 advisory**（governance-status Step 3.5，函数保留不删）。check-projection-sync PASSED。Code Reviewer R0 APPROVED_WITH_NOTES（7/7，0 P0/P1，3 P2）。详见 EVD-670。
- **RISK-040 — 双 root 发散测试 + 真实宿主项目验证 PASSED**：验证在独立 host project/e2e-test-project 上——scenario_hint=F there vs D in dev repo，证明 resolve_entry.py 读 host 不读 plugin-self。关闭标准满足（双 root 发散测试 + 真实宿主项目验证 + fail-closed + 独立审查）。
- 版本声明同步到 0.64.0：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook @version、verify_workflow.py `REQUIRED_SNIPPETS`、CHANGELOG、plan-tracker 工作流版本指针 + 路线图。
- e2e fixture 版本指针同步：`project/e2e-test-project/skills/software-project-governance/SKILL.md` + `project/e2e-test-project/.governance/plan-tracker.md` 的版本指针 0.63.4→0.64.0。

### Migration Notes
- **版本权威源切换（行为变更）**：激活版本权威源从 `installed_plugins.json`（可能滞后的元数据）切到 SKILL.md frontmatter `version` 字段。用户无需手动操作——resolve_entry.py 自动从 SKILL frontmatter 读取 active_version。
- **WORKFLOW_HOME 消除**：未定义的环境变量依赖全部删除。如有用户曾手动设置 `WORKFLOW_HOME`（非推荐），不再被读取——改用 resolve_entry.py 的 `--project-root` 或 cwd。
- **非 breaking change**：resolve_entry.py 输出 JSON 供 LLM 消费，向后兼容现有 `.governance/` 结构；SKILL.md frontmatter `version` 字段原本就存在（0.63.4 起即如此）。
- **避免 0.54.2/0.54.3 回归（DEC-080/RISK-038）**：双 root 模型确保 PLUGIN_HOME（从 `__file__` 推导）绝不用于读事实源——HOST_PROJECT_ROOT 始终从 cwd/平台解析。RISK-040 发散测试守卫此不变量。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` — PASSED（Files checked: 13, all 0.64.0）。
- `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync` — PASSED。
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.64.0 --require-changelog` — PASSED。
- `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` — PASSED。
- **RISK-040 真实宿主项目验证 PASSED**（project/e2e-test-project，独立 host，scenario_hint=F vs dev repo D）。
- resolve_entry.py test suite 20 passed（FX-130 commit 已验证）。

### Boundaries
- **不关闭** RISK-039（架构腐化看护——需外部宿主验证）。RISK-040 关闭标准满足但不自动关闭（独立 Release Reviewer R0 确认）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support（1.0.0 阻塞 RISK-036/037/039 + 外部验证）。
- **MINOR 版本号选择理由**：0.64.0 是入口架构级重构（新增 resolve_entry.py 能力 + 行为变更：版本权威源切换 + WORKFLOW_HOME 消除），非纯 bug fix。与 0.63.0（MINOR，Coordinator 检视循环协议修复 + verify Check 29/30）MINOR 先例同构。占用路线图预留号 0.64.0（DEC-096：原预留给 verify_workflow.py 拆分 Phase 6 顺延到 0.66.0）。

## [0.63.4] - 2026-07-07

### 0.63.4 — check_version_consistency VERSION_FILES 覆盖盲区修复（FIX-182）

0.63.4 发布 FX-183 patch：把 FIX-182（`check_version_consistency` 的 `VERSION_FILES` 字典只覆盖 3/4 plugin.json 目录——缺 `.zcode-plugin/plugin.json` 和 `.chrys-plugin/plugin.json`，打印串硬编码 "3 plugin.json" 但实际有 4 个 plugin.json 目录）版本化为 patch release。FX-181 Release Reviewer R0 独立发现的覆盖盲区。纯 bug fix，**只影响检查工具的覆盖范围、不影响运行时行为**，无 behavior change、无新能力、无 breaking change、无 migration 影响。FIX-182 已通过 Code Reviewer APPROVED（6/6 checklist，0 P0/P1/P2；打印串 N=13 独立核实）+ 703 测试全绿。

经 DEC-090/091 降级 SoD 沿用——产品代码由 Coordinator spawn Governance Developer + 只读 Explore Code Reviewer，本 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0 审查。

### Fixed
- **FIX-182 — check_version_consistency VERSION_FILES 覆盖全部 4 个 plugin.json（zcode + chrys 覆盖盲区修复）**：`verify_workflow.py check_version_consistency`（行 ~9480）的 `VERSION_FILES` 字典原本只覆盖 3 个 plugin 相关文件（`.claude-plugin/plugin.json` + `marketplace.json` + `.codex-plugin/plugin.json`），缺 `.zcode-plugin/plugin.json` 和 `.chrys-plugin/plugin.json`。打印串（行 ~20100）硬编码 "11 files, 3 plugin.json" 但项目实际有 4 个 plugin.json 目录（Claude/Codex/Zcode/Chrys）。影响：若未来 release 漏更新 `.zcode-plugin` 或 `.chrys-plugin` 的 plugin.json version，`VERSION_FILES` 循环不会检测到（`REQUIRED_SNIPPETS` snippet self-check 只扫 `verify_workflow.py` 内嵌字面量，不检查实际 plugin.json 文件内容——真实覆盖盲区）。本次无实际漂移（手动核实 + projection-sync 兜底），但未来潜在风险。**修复**：(1) `VERSION_FILES` 补 `.zcode-plugin/plugin.json` 和 `.chrys-plugin/plugin.json` 两个条目；(2) 打印串修正为 "13 files (SKILL.md, manifest.json, marketplace.json, 4 plugin.json, CHANGELOG, plan-tracker, 4 hooks)"（N=13 = VERSION_FILES 7 + CHANGELOG 1 + plan-tracker 1 + HOOK_FILES 4）；(3) 新增回归测试 `test_fix182_version_files_covers_zcode_and_chrys_plugin`：PASS-after-fix 调真实 `check_version_consistency` 构造 `.zcode-plugin` version 漂移断言检测到；FAIL-on-buggy 自包含回放演示 pre-fix 5-entry dict 盲区。

### Changed
- 版本声明同步到 0.63.4：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook @version、verify_workflow.py `REQUIRED_SNIPPETS`、CHANGELOG、plan-tracker 工作流版本指针 + 路线图。
- e2e fixture 版本指针同步：`project/e2e-test-project/skills/software-project-governance/SKILL.md` + `project/e2e-test-project/.governance/plan-tracker.md` 的版本指针 0.63.3→0.63.4（与 FX-177/179/181 先例一致）。

### Migration Notes
- **无 migration 影响**：纯检查工具覆盖范围修复（VERSION_FILES 补 2 条目 + 打印串修正），不影响运行时行为、协议层或检测能力。无用户可感知变化。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` — PASSED（Files checked: 13, 4 plugin.json, all 0.63.4）。
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.4 --require-changelog --runtime-adapters` — baseline-consistent with 0.63.3（FAIL 项 pre-existing，非本次引入）。
- `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync` — PASSED（4 mirrored files, no drift）。
- `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` — PASS。
- infra suite 703 passed / 64 subtests passed（FIX-182 commit 已验证，无回归）。

### Boundaries
- **不关闭** RISK-039（架构腐化看护——需外部宿主验证）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support（1.0.0 阻塞 RISK-036/037/039 + 外部验证）。
- **纯 bug fix，无 behavior change**：仅 `check_version_consistency` 工具覆盖范围修复（VERSION_FILES 补 2 条目 + 打印串修正），无运行时行为变化、无协议层改动、无新 Check、无新能力声明。降级 SoD（DEC-090/091）沿用。
- **PATCH 版本号选择理由**：FIX-182 是单一检查工具覆盖盲区修复，与 0.63.3（FIX-180）/ 0.63.2（FIX-178）/ 0.63.1（FIX-176）/ 0.54.1（FIX-140）PATCH 先例同构——纯 bug fix、无 behavior change、无新能力。这是连续第 4 个 patch（0.63.1/0.63.2/0.63.3/0.63.4），但每个都是独立的 bug fix，符合 SemVer PATCH 语义。不占用路线图预留号（0.64.0/0.65.0 不变）。

## [0.63.3] - 2026-07-06

### 0.63.3 — e2e fixture SKILL.md adapter 表结构对齐（FIX-180）

0.63.3 发布 FX-181 patch：把 FIX-180（e2e fixture `project/e2e-test-project/skills/software-project-governance/SKILL.md` 的 adapter 表缺 opencode + Chrys 两行，导致 `check-projection-sync` 持续报 "target fixture drift: skills/software-project-governance/SKILL.md" FAIL）版本化为 patch release。纯 bug fix，**只影响 e2e 测试数据、不影响运行时行为**，无 behavior change、无新能力、无 breaking change、无 migration 影响。FIX-180 已通过 Code Reviewer APPROVED（6/6 checklist，0 P0/P1/P2）+ projection-sync FAIL→PASS + 702 测试全绿。

经 DEC-090/091 降级 SoD 沿用——产品代码由 Coordinator spawn Governance Developer + 只读 Explore Code Reviewer，本 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0 审查。

### Fixed
- **FIX-180 — e2e fixture SKILL.md adapter 表对齐 opencode + Chrys（projection-sync FAIL 修复）**：source `skills/software-project-governance/SKILL.md` 的 agent adapter 表含 6 行（Claude Code/Codex/Gemini/opencode/Chrys/国内 Agent CLI），但 e2e fixture `project/e2e-test-project/skills/software-project-governance/SKILL.md` 只有 4 行——0.61.2 引入 Chrys 集成（opencode + Chrys 行）时 fixture 未对齐，造成 fixture 与 source 的 adapter 表结构漂移。这使 `check-projection-sync`（Check 28）持续报 "target fixture drift" FAIL，在 FX-175/177/179 Release Reviewer R0 中被标记为超出 PATCH 范围的 pre-existing 结构性漂移。**修复**：在 fixture SKILL.md 的 adapter 表 Gemini 行后、国内 Agent CLI 行前补入 opencode + Chrys 两行，byte-for-byte 与 source 一致（单文件 +2 行，无 source 改动）。projection-sync FAIL→PASS。

### Changed
- 版本声明同步到 0.63.3：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook @version、verify_workflow.py `REQUIRED_SNIPPETS`、CHANGELOG、plan-tracker 工作流版本指针 + 路线图。
- e2e fixture 版本指针同步：`project/e2e-test-project/skills/software-project-governance/SKILL.md` + `project/e2e-test-project/.governance/plan-tracker.md` 的版本指针 0.63.2→0.63.3（与 FX-177/179 先例一致）。

### Migration Notes
- **无 migration 影响**：纯 e2e fixture 对齐（补 2 行 adapter 表），不影响运行时行为、协议层或检测能力。无用户可感知变化。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` — PASSED（所有版本声明一致）。
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.3 --require-changelog --runtime-adapters` — baseline-consistent with 0.63.2（FAIL 项 pre-existing，非本次引入）。
- `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync` — PASSED（FIX-180 核心交付：4 mirrored files, no drift）。
- `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` — PASS。
- infra suite 702 passed / 64 subtests passed（FIX-180 commit 已验证，无回归）。

### Boundaries
- **不关闭** RISK-039（架构腐化看护——需外部宿主验证）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support（1.0.0 阻塞 RISK-036/037/039 + 外部验证）。
- **纯 bug fix，无 behavior change**：仅 e2e fixture adapter 表补 2 行（对齐 source），无运行时行为变化、无协议层改动、无新 Check、无新能力声明。降级 SoD（DEC-090/091）沿用。
- **PATCH 版本号选择理由**：FIX-180 是单一 e2e fixture 对齐修复（解除 projection-sync FAIL），与 0.63.2（FIX-178）/ 0.63.1（FIX-176）/ 0.54.1（FIX-140）PATCH 先例同构——纯 bug fix、无 behavior change、无新能力。这是连续第 3 个 patch（0.63.1/0.63.2/0.63.3），但每个都是独立的 bug fix，符合 SemVer PATCH 语义。不占用路线图预留号（0.64.0/0.65.0 不变）。

## [0.63.2] - 2026-07-05

### 0.63.2 — Check 29 auto-discovery 排除 session-snapshot 误报修复（FIX-178）

0.63.2 发布 FX-179 patch：把 FIX-178（Check 29 `check_m5_runtime_triggers` 的 auto-discovery 模式把 `session-snapshot.md` 事后记录文件误判为 agent 运行时输出，对 snapshot 中合法的编号步骤/选项记录误报 T2 FAIL）版本化为 patch release。纯 bug fix，无 behavior change、无新能力、无 breaking change、无 migration 影响。FIX-178 已通过 Code Reviewer APPROVED（6/6 checklist，0 P0/P1）+ 真实数据验证（check-governance Check 29 FAIL→PASS）。

经 DEC-090/091 降级 SoD 沿用——产品代码由 Coordinator spawn Governance Developer + 只读 Explore Code Reviewer，本 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0 审查。

### Fixed
- **FIX-178 — Check 29 auto-discovery 排除 session-snapshot（误报修复）**：`verify_workflow.py check_m5_runtime_triggers`（行 ~14316）在 `text=None` auto-discovery 模式下原本把 `session-snapshot.md` 当作一段运行时段扫描（`has_tool=False` 硬编码）。但 session-snapshot 是**事后记录文件**（snapshot 格式规范要求会话末尾写入；其结构化字段可能合法地含编号步骤引用与选择/选项/计划词汇），不是 agent 运行时输出。T2 启发式无法区分"被记录的菜单"与"运行时菜单"，于是 snapshot 里的合法记录（如"第(1)(2)步…第(3)步"引用 + 邻近选择词汇）触发 T2 且无 AskUserQuestion 工具调用 → check-governance Check 29 持续 FAIL。**方案 A 修复（从 auto-discovery 中剔除 session-snapshot）**：(1) `check_m5_runtime_triggers` auto-discovery 分支不再把 session-snapshot 作为 segment 添加，只扫描 evidence-log "事实依据"字段（真正的 agent 输出摘要）；(2) 函数契约不变——调用方仍可显式经 `corpus_sources=[('session-snapshot', text, False)]` 扫描 snapshot（向后兼容）；(3) docstring + 内联注释更新说明 FIX-178 设计决策。**检测能力完整保留**：inline `text=` 路径（真正的运行时扫描入口）逐字节未改；12 个既有 FIX-29 系列测试全部 PASS；新增反向保护回归测试 `test_fix178_detection_capability_preserved_on_fake_runtime_output` 构造真实违规（选项菜单 + 选择词 + 无工具调用）断言 FAIL+T2，证明检测未被削弱。

### Changed
- 版本声明同步到 0.63.2：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook @version、verify_workflow.py `REQUIRED_SNIPPETS`、CHANGELOG、plan-tracker 工作流版本指针 + 路线图。

### Migration Notes
- **无 migration 影响**：纯 bug fix，收紧 Check 29 auto-discovery 的扫描源（不再扫事后记录文件），检测能力完整保留。inline `text=` 运行时扫描路径零改动。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` — PASSED（所有版本声明一致）。
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.2 --require-changelog --runtime-adapters` — baseline-consistent with 0.63.1。
- `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` — baseline-consistent。
- `python skills/software-project-governance/infra/verify_workflow.py check-governance` — Check 29 PASS（FIX-178 修复有效，Scanned segments 2→1，Verdict FAIL→PASS）。
- test_verify_workflow.py 579 passed / 64 subtests passed；infra suite 702 passed / 64 subtests passed（无回归）。

### Boundaries
- **不关闭** RISK-039（架构腐化看护——需外部宿主验证）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support（1.0.0 阻塞 RISK-036/037/039 + 外部验证）。
- **纯 bug fix，无 behavior change**：Check 29 auto-discovery 扫描源收紧，inline 运行时扫描路径零改动、检测能力完整保留（反向保护测试守卫）。无用户可感知行为变化、无协议层改动、无新 Check、无新能力声明。降级 SoD（DEC-090/091）沿用。
- **PATCH 版本号选择理由**：FIX-178 是单一 Check 29 auto-discovery 误报修复，与 0.63.1（FIX-176 archive bug fix）/ 0.54.1（FIX-140 hotfix patch）PATCH 先例同构——纯 bug fix、无 behavior change、无新能力。0.63.0 的 MINOR 升级因 M5.4 收紧是 behavior change，本次无此类变更。不占用路线图预留号（0.64.0/0.65.0 不变）。

## [0.63.1] - 2026-07-05

### 0.63.1 — archive 引擎 build_index 非结构化归档登记修复（FIX-176）

0.63.1 发布 FX-177 patch：把 FIX-176（archive 引擎 `build_index` 不登记 narrative/recent-completed 类非结构化归档文件）版本化为 patch release。纯 bug fix，无 behavior change、无新能力、无 breaking change、无 migration 影响。FIX-176 已通过 Code Reviewer APPROVED（6/6 checklist，0 P0/P1）+ 真实数据验证（archive-integrity 双重 PASS）。

经 DEC-090/091 降级 SoD 沿用——产品代码由 Coordinator spawn Governance Developer + 只读 Explore Code Reviewer，本 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0→R1 审查。

### Fixed
- **FIX-176 — archive build_index 登记非结构化归档文件**：`archive.py build_index()`（行 1389-1540）原本只从归档文件**内容**提取条目生成 index 行（tasks 用 `_extract_tasks_from_archive_file` 从表格行、evidence 用 EVD ID、decisions 用 `## DEC-` 头、risks 用 `| RISK-` 行），`narrative-*.md`/`recent-completed-*.md` 是自由叙述类归档文件（无 task 表行、无 DEC 头、无 RISK 行）→ build_index 不为它们生成任何 index 条目 → rebuild 后变 orphan → `verify_archive_integrity` Check 2（每个 archive 文件必须被 index 引用）FAIL。FIX-169 曾手动登记 narrative，但 build_index rebuild 会丢失该手动条目。**方案 A 修复**：(1) 新增 `_UNSTRUCTURED_ARCHIVE_PREFIXES` 元组 + 3 个 helper（`_is_unstructured_archive_file`/`_unstructured_archive_kind`/`_unstructured_archive_description`，基于文件名前缀匹配 + 从 frontmatter 防御性解析描述）；(2) `build_index()` 加 `elif _is_unstructured_archive_file(f)` 分支登记到 `narrative_entries`；(3) index.md 在 Risk 索引后追加 `## 非结构化归档` section（三列表 `| 归档文件 | 类型 | 描述 |`）；(4) `verify_archive_integrity._parse_index_section` 加 `"非结构化归档"` 分支并入 `all_index_refs`；(5) Check 3 per-category 计数双重保险不污染（新 section 不在 `section_map` + narrative 行不匹配 `[A-Z]+-\d+` 正则）。**避免重复登记**：含 60 行 task 表格的 `recent-completed-*.md` 走结构化分支，不进 narrative_entries。

### Changed
- 版本声明同步到 0.63.1：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook @version、verify_workflow.py `REQUIRED_SNIPPETS`、CHANGELOG、plan-tracker 工作流版本指针 + 路线图。

### Migration Notes
- **无 migration 影响**：纯 bug fix，修复归档引擎覆盖盲区（让 build_index 正确登记非结构化归档文件，不再误报 orphan），无 breaking change。下次 `archive.py migrate --auto` 运行时 build_index 会自动重建 index.md 含新 section。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` — PASSED（所有版本声明一致）。
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.1 --require-changelog --runtime-adapters` — baseline-consistent with 0.63.0。
- `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` — PASS。
- test_archive.py 89 passed（86 baseline + 3 new FAIL-on-buggy/PASS-after-fix），infra suite 700 passed（0 regressions）。

### Boundaries
- **不关闭** RISK-039（架构腐化看护——本体已修，build_index 治标自动化，但 RISK-039 需外部宿主验证）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support（1.0.0 阻塞 RISK-036/037/039 + 外部验证，DEC-095 已记录）。
- **纯 bug fix，无 behavior change**：archive 引擎覆盖盲区补全，无用户可感知行为变化、无协议层改动、无新 Check、无新能力声明。降级 SoD（DEC-090/091）沿用。
- **PATCH 版本号选择理由**：FIX-176 是单一 archive 引擎 bug 修复，与 0.54.1（FIX-140 hotfix patch）先例同构——纯 bug fix、无 behavior change、无新能力。0.63.0 的 MINOR 升级因 M5.4 收紧是 behavior change，本次无此类变更。

## [0.63.0] - 2026-07-04

### 0.63.0 — Coordinator 检视循环协议修复 + verify Check 29/30（FIX-173/174）+ archive 引擎修复（FIX-168/170/171/172）

0.63.0 修复 Coordinator 检视循环三行为缺陷（用户反馈：忽略 AskUserQuestion / 不发起检视 / 不复审循环），协议层（FIX-173）+ verify 基础设施层（FIX-174）双落地。同时发布 0.62.0 后累积的 4 个 archive 引擎/CI 修复（FIX-168/170/171/172，原未单独发版）。

经 Architect v2 + Design Reviewer round2 APPROVED + AUDIT-128 诊断 + 用户 3 决策。Code Reviewer R0 APPROVED 6/6（FIX-173）+ R0→R1 闭环（FIX-174）。

### Added
- **Check 29（M5 运行时扫描）** — verify_workflow.py `check_m5_runtime_triggers`：best-effort 扫描 behavior-protocol.md M5.1b 运行时确定性触发器（T1 裸问句收尾+词集 / T2 编号选项菜单+选择词邻近上下文），检测"段尾问号或选项菜单但无 AskUserQuestion"违规。advisory，无语料降级 no-verdict。
- **Check 30（复审终态校验）** — verify_workflow.py `check_review_closure`：校验 M7.4 step 4.6 review 闭环状态机——每条 REVIEW 证据须收敛到 APPROVED(✓) 或 BLOCKED(✗→escalation)，不得停留中间态；含熔断（最大 3 轮）+ degraded 限额（≤2 次）+ 向后兼容（裸 REVIEW-{id}=R0 / 旧 review-{id}-v*.md→UNKNOWN）。
- **M5.1b 确定性触发器** — behavior-protocol.md：运行时确定性触发器定义（问号主信号 + 词集辅 + 4 类豁免区）。
- **M5.4b 纯通知结构性定义** — behavior-protocol.md：N1 无问号 / N2 无编号选项 / N3 ℹ️/📢/> 注：/>> 派发 前缀。⚠️ **behavior change**——既有 SHOULD 收紧为 MUST。
- **M7.4 step 4.5b（spawn 守卫，DIFF-GATED）** — behavior-protocol.md：产品代码 diff + 路由表后置审查 Agent + 无 REVIEW 证据 → BLOCKING。3 类豁免。
- **M7.4 step 4.6（Review 闭环状态机）** — behavior-protocol.md：C1-C7 强制条款（NEEDS_CHANGE 必须 spawn 复审 / 复审引用前轮 / 熔断 3 轮 / 终态仅 APPROVED 与 BLOCKED / round 由 evidence-log 派生并行安全）+ degraded 限额 + escalation 4 选项。
- **methodology-routing.md 后置审查列** — 路由表 4→6 列重构，新增"后置审查 Agent(s)"+"触发条件"列对齐 SKILL.md，保留"执行方法"列。
- **agent-communication-protocol.md Review 处理流程** — Review 结论 Coordinator 处理流程表 + 复审协议 4 条 MUST + escalation 上下文区分 + REVIEW-{id}-R{n} 字段约定。
- **6 Reviewer agent + developer.md 复审协议** — code/design/requirement/test/release/retro reviewer + developer 注入复审协议（逐条比对前轮 findings + round 号 + 不看前轮不得 APPROVED）。
- **FIX-174 单测** — test_verify_workflow.py +580 行（Check 21 强化 / Check 29 / Check 30 覆盖）。

### Changed
- ⚠️ **behavior change — M5.4 "纯通知"收紧为 MUST（behavior-protocol.md M5.4b）**：既有 SHOULD 升级为结构性硬定义（N1 无问号 / N2 无编号 / N3 通知前缀）。违反任一 → 不得援引 M5.4 跳过 AskUserQuestion。既有"输出通知。不需要 AskUserQuestion"须加 ℹ️ 前缀且不含问号。
- **Check 21 强化** — verify_workflow.py `check_review_debt` → `review_spawn_gap`（三源交叉：产品代码 diff ∧ 路由表后置审查 Agent ∧ 无 REVIEW 证据）+ degraded fuse（同 task ≥3 → FAIL）。
- **verify_workflow.py Check 18-27 编号漂移系统性修正** — 52 行无逻辑改动，函数头/docstring/子命令/print/help 标签全部对齐主运行 cmd_check_governance。

### Fixed
- **FIX-173 / 问题 1（忽略 AskUserQuestion）** — M5.1b 确定性触发器 + Check 29 运行时扫描。
- **FIX-173 / 问题 2（不发起检视）** — M7.4 step 4.5b spawn 守卫 + methodology-routing.md 后置审查列 + Check 21/30 强制。
- **FIX-173 / 问题 3（不复审循环）** — M7.4 step 4.6 闭环状态机（C1-C7 + 熔断 + degraded 限额）+ 6 Reviewer agent 复审协议 + Check 30 终态校验。
- **FIX-168** — CI manifest-consistency 失败修复（Chrys adapter 遗漏 5 个 manifest/scope 同步点）。
- **FIX-170** — archive.py `_migrate_risks`/`_migrate_decisions` 增加状态过滤，跳过 OPEN/活跃状态条目（AUDIT-127 根因）。
- **FIX-171** — evidence 迁移 subset gate 放宽（忽略 RISK/DEC/REVIEW 跨实体引用）+ legacy 版本解析 + 路线图修正（AUDIT-126 根因 B）。
- **FIX-172** — archive migrate body-write 数据丢失修复（FIX-158 回归，priority-table task 的 target_version 永不匹配 section → body 空 + 行被删）。

### Migration Notes
- ⚠️ **M5.4 收紧（behavior change）**：升级后"纯通知"段必须以 ℹ️ / 📢 / > 注： / >> 派发 之一开头，且不得含问号、不得含编号选项列表。否则判非纯通知 → 必须 AskUserQuestion。既有无前缀裸通知加前缀即可合规。
- **Check 29/30 是 advisory**：Check 29 best-effort runtime scan，非产品代码硬 gate；Check 30 针对 governance 证据。
- 版本号全量同步 0.62.0→0.63.0（17 文件）。

### Boundaries
- **不关闭** RISK-036（官方收录准备）/ RISK-037（1.0.0 阻塞）/ RISK-039（架构腐化看护，本体已修但需外部宿主验证）。
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support。
- **0.62.0..0.63.0 含 4 个 pre-release fix**（FIX-168/170/171/172），原未单独发版，本次一并发布。
- **版本号占用声明**：0.63.0 原规划为"verify_workflow.py 拆分 Phase 5"（DEC-088 路线图），本次占用为"协议层+verify check 闭环"主题，拆分 Phase 5 顺延到 0.65.0+。
- **降级 SoD（DEC-090/091）**：本版本产品代码由 Coordinator 降级 Developer + 只读 Explore Code Reviewer（FIX-173/174 已 R0 APPROVED）；FX-175 release 评估由 Coordinator spawn Release Agent + 独立 Release Reviewer R0→R1 审查。

## [0.62.0] - 2026-07-01

### 0.62.0 — zcode 插件市场适配(废弃逆向 local-load 机制)

0.62.0 把 zcode 的适配方式从"逆向工程硬编码植入本地安装"改为"通过 zcode 新版插件市场原生安装"。zcode 新版运行时已支持完整的市场链(`addMarketplace`/`installMarketplacePlugin`/`clonePluginSource`/`known_marketplaces.json`),接受 `{source:"github",repo}` 源,与 Claude Code 市场协议同构。0.56.0 的逆向 seed-hash 工具因此废弃。

### Added
- `.claude-plugin/marketplace.json` 的 `source` 字段从本地相对路径 `"./"` 改为结构化 github 对象 `{"source":"github","repo":"peterwangze/software-project-governance"}`——与 zcode 新版运行时 `resolveGitPluginSource` 接受的格式、Claude 官方市场格式一致。
- `docs/marketplace/zcode-marketplace-install.md`——新版市场安装文档(两步:`/plugin marketplace add` + `/plugin install`),含从 0.56.0 local-load 迁移指引。
- README Tier 1 加载表新增 zcode 行(走 marketplace 协议);中文安装段新增 zcode 小节。

### Changed
- zcode 安装路径统一为 marketplace 协议(`/plugin marketplace add peterwangze/software-project-governance` + `/plugin install software-project-governance@spg`),zcode 与 Claude Code 共享同一协议。
- `docs/marketplace/zcode-local-load-0.56.0.md` 顶部加 DEPRECATED 横幅,指向新文档(保留为历史记录)。
- `docs/marketplace/official-readiness-gap-analysis-0.56.0.md` 与 `docs/release/feature-flags-0.56.0.md` 加 0.62.0 更新注记(local-load 机制已废弃)。

### Removed
- `project/zcode-local-load.py`(20KB 逆向 seed-hash 工具)。verify_workflow.py 不引用、无测试引用,删除零代码破坏。该工具逆向 `D:\app\zcode\resources\glm\zcode.cjs` 的 `rdt()`/`sCr()` 算法绕过 `isSeedCurrent`,是脆弱的运行时耦合(DEC-093)。

### Fixed
- (none)

### Upgrade Notes
- **无破坏性变更**。已用 0.56.0 local-load 装上本地 zcode 的安装不受影响(zcode 不主动 re-seed 第三方插件);新装一律走 marketplace。
- 这是**协议一致性安装**,不是 zcode 官方收录或审核批准。RISK-036(官方收录准备)继续打开。
- verify 输出:check-version-consistency 仅 plan-tracker 本地滞后(WARN,非阻塞)、check-agent-adapters 5/5、全量测试绿。

## [0.61.2] - 2026-07-01

### Added
- Chrys agent adapter (`adapters/chrys/`) — new Tier 1 agent platform with native ask_user_question, sub_agent, and tool_calling support. Chrys is the first adapter with native AskUserQuestion-equivalent capability.
- Chrys entries in README Tier 1 loading guide, SKILL.md adapter table, core/manifest.md supported_agents, mainstream-agent-loading-0.47.0.md, and runtime-readiness-matrix-0.43.0.md.
- Chrys validation in verify_workflow.py (MAINSTREAM_AGENT_ADAPTERS, ADAPTER_RUNTIME_CAPABILITY_POLICY, PROJECTION_SNIPPETS, OPTIONAL_PROJECTION_FILES, MAINSTREAM_AGENT_LOADING_TIER1, MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS, MAINSTREAM_AGENT_LOADING_ADAPTERS, RUNTIME_MATRIX_AGENT_IDS).
- AGENTS.md title updated to acknowledge Chrys alongside Codex.

### Changed
- verify_workflow.py agent adapter contract check now validates 5 adapters (was 4).
- opencode added to supported_agents in core/manifest.md and SKILL.md adapter table (pre-existing omission fixed alongside Chrys addition).

### Fixed
- (none)

### Upgrade Notes
- No breaking changes. All existing adapter contracts unchanged.
- Chrys adapter is runtime-verified from live Chrys session on 2026-07-01.
- verify output: 653 tests passed, check-agent-adapters 5/5 synchronized, check-mainstream-agent-loading PASSED.

## [0.61.1] - 2026-06-30

### 0.61.1 - Patch: archive engine decision/risk migration + verify cross-check (TD-014/015)

0.61.1 是 0.61.0 的补丁版本，兑现 0.61.0 遗留的两个技术债：TD-014（archive.py decision/risk 迁移逻辑未实现）和 TD-015（verify_archive_integrity Check 3 死统计）。这两个是 AUDIT-125 治理数据膨胀修复的覆盖盲区残留——decision-log/risk-log 此前永不归档、归档完整性检查不交叉比对。

### Added
- `skills/software-project-governance/infra/archive.py` — 新增 `_migrate_decisions`（archive.py:585-647）、`_migrate_risks`（archive.py:650-686）、`_entry_version_for_archive`（archive.py:567-579）helper。按 task_id→version lookup（this-run archived + 已归档历史 task）扫描 decision-log/risk-log 行，引用已归档 task 且版本在范围的行迁出到 archive/decisions、archive/risks。dry-run 对真实数据：**29 decisions + 11 risks 可迁出**。
- `skills/software-project-governance/infra/tests/test_archive.py` — +TestDecisionRiskMigration（5 测试：decision 迁移/不迁移/risk 迁移/_version_to_tuple 防御/_version_in_range None）+ test_verify_check3_symmetric_with_decisions_risks（耦合回归 guard）

### Changed
- `skills/software-project-governance/infra/archive.py` — `_version_to_tuple` 改用 re.search 提取 x.y.z token（对"未规划版本"返回 None，对"未规划版本（0.61.0）"返回 (0,61,0) 合理）；`_version_in_range` 处理 None 返回 False；verify_archive_integrity Check 3 从只统计改为 **per-category 对称交叉比对**（tasks/evidence/decisions/risks 各自比对，任一 category 文件数≠索引数则 FAIL）
- `skills/software-project-governance/core/technical-debt-ledger.md` — TD-014/TD-015 标记 RESOLVED
- 版本号全量同步 0.61.0→0.61.1（13 文件）

### Fixed
- **FIX-162/163 耦合回归**（审查员发现的 P0）：FIX-163 Check 3 原本 total_in_files 只算 tasks+evidence、total_in_index 算全部 ID，FIX-162 真实迁移 decisions/risks 后 verify 必假阳性。改为 per-category 对称计数修复。新增 test_verify_check3_symmetric_with_decisions_risks 守护。
- **FIX-162 decision 保真**（审查员 P2-1）：decision 迁移原只保留 dec_id+title（丢 9 列核心字段），改为同时保留原始 `| DEC-... |` 整行作为附录（与 risks 一致）

### Boundaries
- **不关闭** RISK-039（治理数据膨胀本体已修，但 RISK-039 关闭需外部宿主验证）
- **不关闭** RISK-036/RISK-037（1.0.0 阻塞）
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support
- **降级 SoD 诚实标注**（DEC-090/091）：产品代码由 Coordinator 直写 + 事后 Explore 审查（REVIEW-FIX-162/163 APPROVED）
- **P2-2 留 follow-up**：多 task 混合引用、dry_run 写隔离、版本超上界 3 个测试场景未补（审查员 P2-2，非阻断）

## [0.61.0] - 2026-06-28

### 0.61.0 - Governance Data Bloat Remediation (archive engine + size guard + doc align)

0.61.0 落地 **AUDIT-125 诊断的治理数据膨胀根因彻底修复**（4 Phase，FIX-157~160）。这是 RISK-039（架构腐化看护缺口）的**本体修复**——治理数据自身膨胀此前完全无 check 守护，归档机制静默失效但 dry-run 报"健康假象"。

**起因**：会话恢复时发现 plan-tracker.md 达 298KB（超出 agent 256KB 单次读取上限），但 `archive.py migrate --auto --dry-run` 报"无可归档数据"。AUDIT-125 只读调查查明 3 层根因：(1) archive.py 解析逻辑与 plan-tracker 实际格式不匹配（task 行正则要求 ID 在第1列，实际在第2列；状态列硬编码 parts[10]；版本 section 模型不识别"目标版本"列归类）；(2) early-return（archive.py:1364）让 release_forced/fallback_90d 触发器成死代码；(3) 覆盖盲区（叙述段 219KB 无归档机制、decision/risk 迁移是未实现 stub、无体积 check 守护）。

**4 Phase 修复**：
- **FIX-157**：plan-tracker "当前活跃事项"段 298KB→91.7KB（-69%），迁出 212KB 历史至 3 个归档文件（narrative/completed-tasks/recent-completed）。事后 Explore 审查 APPROVED。
- **FIX-158**：archive.py 6 点根因修复——新增 `_parse_priority_table_tasks`（支持 7 列宽表 ID 第2列+目标版本列归类）、`_find_status_column`（表头动态定位状态列，替代硬编码 parts[10]）、`_task_status_is_archivable`（认 ✅变体：已发布/保守闭环/完成候选等）、early-return 移除让触发器评估照常、`_extract_tasks_from_archive_file` 双格式支持。+9 单测。实测 `_extract` 对真实归档 0→198 提取。
- **FIX-160**：新增 `check_governance_data_size`（Check 28s，ArchGuard 声明式范式，warn 200KB/error 250KB，advisory）——治理数据体积现在被 check 直接守护。CLI `check-governance-data-size`。+5 单测。实测 evidence-log 1.3MB 触发 ERROR。
- **FIX-159**：commands/governance.md Scenario E 新增"归档失效检测" P1 检查（超阈值但 dry-run 报无可归档 = 异常）。
- **FIX-161**：修复 2 个测试隔离缺陷（`test_real_interruption_policy_passes` / `test_cmd_status_outputs_stable_permission_mode_line`）——之前测试未隔离 ROOT/module 路径，读到真实 `.governance/` 的 in-flight 任务导致失败。现在 patch `EXECUTION_PACKET_PATH`/`INTERACTION_BOUNDARY_PATH`/`SESSION_SNAPSHOT_PATH` 等模块路径使用隔离 fixture。unit-tests gate 从 2 失败变为全绿（547 passed）。

**测试**：81 passed（archive 62 + arch_health 19），0 回归。2 项 pre-existing 测试失败（测试隔离缺陷，非本次回归，REVIEW-FIX-153 已记录）。

### Added
- `skills/software-project-governance/infra/archive.py` — 3 新函数（`_find_status_column`/`_parse_priority_table_tasks`/`_task_status_is_archivable`）+ priority-table 扫描分支 + early-return 重构 + 双格式提取
- `skills/software-project-governance/infra/verify_workflow.py` — `check_governance_data_size` + `cmd_check_governance_data_size` + Check 28s 块（CLI 接入 6 处）
- `skills/software-project-governance/core/architecture-health.json` — `governance_data_size` section（声明式阈值预算）
- `.governance/archive/tasks/narrative-2026-04-30_2026-06-27.md`（gitignored 运行态，+99 段历史叙述归档）
- `.governance/archive/tasks/completed-tasks-2026-04-30_2026-06-27.md`（gitignored，+138 行已完成 task 归档）
- `.governance/archive/tasks/recent-completed-2026-04-30_2026-06-27.md`（gitignored，+60 行最近完成归档）

### Changed
- `skills/software-project-governance/infra/archive.py` — `_parse_task_status` 从硬编码 parts[10] 改动态 status_col 参数；`_find_version_sections` 捕获 header_line（含 sample table 子章节）；`migrate_by_version` 状态匹配从 `== "已完成"` 改 `_task_status_is_archivable`；`_extract_tasks_from_archive_file` 支持 ID 第1列+第2列双格式；`analyze_auto_archive_candidates` early-return 移除
- `skills/software-project-governance/core/technical-debt-ledger.md` — +TD-014（decision/risk 迁移未实现）/TD-015（verify Check 3 死统计未修）
- `commands/governance.md` — Scenario E P1 检查表新增"归档失效（FIX-159/160）"
- `skills/software-project-governance/infra/tests/test_archive.py` — +TestPriorityTableArchive（9 单测：_find_status_column 3 表头格式+边界、_parse_priority_table_tasks 7 列解析+legacy 不误匹配、_task_status_is_archivable 变体、_parse_task_status 动态列）
- `skills/software-project-governance/infra/tests/test_architecture_health.py` — +GovernanceDataSizeTest（5 单测：超阈值 ERROR/达 warn/阈值内 PASS/schema 缺失/disabled）+ SCHEMA_JSON fixture 补 governance_data_size section
- 版本号全量同步 0.60.0→0.61.0（SKILL.md/plugin.json×3/marketplace.json/manifest.json/hooks×4/verify_workflow.py/capability_registry.py）

### Known Issues (non-blocking)
- 2 个 pytest（`test_cmd_status_outputs_stable_permission_mode_line` / `test_real_interruption_policy_passes`）因读取 `.governance/plan-tracker.md`（gitignored 实时状态）含 in-flight 任务而失败——预先存在的测试隔离缺陷，非本次修复回归
- TD-014：archive.py decision-log/risk-log 迁移逻辑未实现（path getter + 目录创建 + index/verify 读取就绪，但 migrate 无迁移分支）——留 0.62.0+
- TD-015：verify_archive_integrity Check 3 只统计不交叉比对（文件数 vs 索引数）——留 0.62.0+

### Boundaries
- **不关闭** RISK-039（治理数据膨胀本体已修，但 RISK-039 关闭需外部宿主验证 ArchGuard 持续有效）
- **不关闭** RISK-036/RISK-037（1.0.0 阻塞，截止 2026-07-30 延期窗口期）
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support
- **降级 SoD 诚实标注**（DEC-090/091）：产品代码由 Coordinator 直写 + 事后 Explore 只读审查（REVIEW-FIX-157~160 APPROVED），非标准先审后合路径
- **decision/risk 归档盲区**（TD-014）和 verify Check 3 死统计（TD-015）已知未修，留 0.62.0+

## [0.60.0] - 2026-06-26

### 0.60.0 - verify_workflow.py Incremental Split Phase 2 (capability-registry domain)

0.60.0 落地 DEC-083 路线图第 (3) 项：verify_workflow.py 渐进式按 check 域拆分的第二步。抽出 **capability-registry 域**（check_capability_registry + _capability_registry_text_values + cmd + 7 CAPABILITY_REGISTRY_* 常量，304 行）到新 `infra/checks/capability_registry.py` 模块，verify_workflow.py 退化为薄入口委托——20,516 → **20,321**（净减 **−195 行**）。两轮累计净减 **616 行**（20,937 → 20,321）。

这是 ArchGuard（0.58.0 advisory）**连续第二次实战守护真实重构**：拆分后 capability_registry.py 零 ERROR/WARN，verify_workflow.py 净减——进一步证明 advisory 能力对真实重构有效（RISK-039 自验证证据增强）。与 Phase 1 manifest 域完美同构（registry schema 校验模式），方法论连续验证成功。

设计先行（REQ-103/AUDIT-123，Explore 实测 4 候选域选 capability-registry），实现经 DEC-087 授权主 agent 直写（沿用 DEC-085/086）+ 事后 Explore 只读审查 APPROVED（REVIEW-FIX-154）。54 个 CLI 命令契约零变化。

### Added
- `skills/software-project-governance/infra/checks/capability_registry.py` — capability-registry 域迁入（check_capability_registry + _capability_registry_text_values + cmd_check_capability_registry + 7 CAPABILITY_REGISTRY_* 常量，304 行）

### Changed
- `skills/software-project-governance/infra/verify_workflow.py` — 删除迁出函数/常量定义（净减 195 行）、加 `from checks.capability_registry import ...` 薄入口委托（含常量 re-export 保测试兼容）、dispatch/argparse/governance-pack Check 28k 注册全保留
- `skills/software-project-governance/core/manifest.json` — 登记 `infra/checks/capability_registry.py`（type:file）
- 版本号全量同步 0.59.0→0.60.0（SKILL.md/plugin.json×4/marketplace.json/package.json/manifest.json/hooks×4 @version/REQUIRED_SNIPPETS×6/target fixture）

### Design Decisions (D1~D5, REQ-103)
- **D1** 7 个 CAPABILITY_REGISTRY_* 常量全迁 capability_registry.py（含死常量 CAPABILITY_REGISTRY_PATH 改纯字符串清理）
- **D2** 通用 helper（`_is_valid_string_list` 21 处 / `_line_has_scoped_claim_negation` 18 处）留 verify_workflow.py
- **D3** `_manifest_artifact_entries` 用延迟 import（设计原定顶层 import，实测引发循环，改函数内延迟）
- **D4** `cmd_check_capability_registry` 迁移 capability_registry.py
- **D5** 沿用 Phase 1 `_vw()` 延迟 import 模式（含 _VW_CACHE 缓存）

### Known Issues (non-blocking)
- 2 个 pytest（`test_cmd_status_outputs_stable_permission_mode_line` / `test_real_interruption_policy_passes`）因读取 `.governance/plan-tracker.md`（gitignored 实时状态）含 in-flight 任务而失败——预先存在的测试隔离缺陷，非本次重构回归，REL-046 任务关闭后自动修复
- P2（不阻断）：延迟 import 在直接脚本运行时产生双模块实例（与 Phase 1 同，留 common 模块化时消除）

### Boundaries
- **只拆 capability-registry 域**——其它 check 域留 0.61.0~0.64.0（agent/runtime 成对、lifecycle-registry、governance-pack 等）
- **不引入** src/pyproject.toml/ruff/mypy（F2 留 0.64.0）
- **不关闭** RISK-039（拆分 Phase 2/6 非全部完成，且关闭需外部宿主验证）
- **不关闭** RISK-036/RISK-037
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support
- DEC-087 降级 SoD 诚实标注：主 agent 直接实现 + 事后 Explore 只读审查

## [0.59.0] - 2026-06-26

### 0.59.0 - verify_workflow.py Incremental Split Phase 1 (manifest domain)

0.59.0 落地 DEC-083 路线图第 (3) 项：verify_workflow.py 渐进式按 check 域拆分的第一步。抽出 **manifest 域**（A 组 12 函数 ~401 行）到新 `infra/checks/manifest.py` 模块，verify_workflow.py 退化为薄入口委托——God Module 首次实质性缩减（20,937 → 20,516，净减 **−421 行**）。这是 ArchGuard（0.58.0 advisory）**首次实战守护真实重构**：拆分后 manifest.py 零 ERROR/WARN，verify_workflow.py 净减——证明 advisory 能力对真实重构有效（RISK-039 部分自验证证据）。

设计先行（REQ-102/AUDIT-122，Explore 实测勘察定边界），实现经 DEC-086 授权主 agent 直写（沿用 DEC-085，当前 harness 仅只读 Explore sub-agent）+ 事后 Explore 只读审查 APPROVED（REVIEW-FIX-153）。54 个 CLI 命令契约零变化。

### Added
- `skills/software-project-governance/infra/checks/` — 新建 check 域子包（为 0.60.0~0.64.0 各域预留位置）
- `skills/software-project-governance/infra/checks/__init__.py` — 包标记 + 用途 docstring
- `skills/software-project-governance/infra/checks/manifest.py` — manifest 域 12 函数迁入（build_required_files_from_manifest / expand_manifest_to_canonical_set / _path_to_label / _manifest_product_file_entries / _manifest_artifact_entries / check_manifest_canonical_product_artifacts / check_manifest_cleanup_scope / _manifest_requires_product_artifact_guards / scan_actual_files / scan_manifest_visible_files / check_manifest_consistency / cmd_check_manifest_consistency），含 `_vw()` 延迟 import（带 _VW_CACHE 缓存）规避循环依赖

### Changed
- `skills/software-project-governance/infra/verify_workflow.py` — 删除 12 个迁出函数定义（净减 421 行）、加 `from checks.manifest import ...` 薄入口委托、dispatch/argparse/governance-pack 注册全保留、Check 24 REQUIRED_SNIPPETS 正则适配新结构锚点（`\n{2,}# ── Manifest`，未削弱守护）
- `skills/software-project-governance/core/manifest.json` — 登记 `infra/checks/__init__.py` + `infra/checks/manifest.py`（type:file）
- 版本号全量同步 0.58.0→0.59.0（SKILL.md/plugin.json×4/marketplace.json/package.json/manifest.json/hooks×4 @version/REQUIRED_SNIPPETS×6/target fixture SKILL.md + plan-tracker/snapshot）

### Design Decisions (D1~D6, REQ-102)
- **D1** `PLUGIN_SCOPE_DIRS` 留 verify_workflow.py（plugin-scope 域未拆，避免反向依赖）
- **D2** `_manifest_artifact_entries` 迁 manifest.py，3 个 registry 域改 import 共享（跨域依赖显式化）
- **D3** `REQUIRED_FILES`/`OPTIONAL_PROJECTION_FILES` 留 verify_workflow.py（files-check 域消费方语义）
- **D4** Check 11 打印段留 cmd_verify（编排逻辑，不撕裂）
- **D5** `cmd_check_manifest_consistency` 迁 manifest.py
- **D6** 新建 `infra/checks/` 子包

### Known Issues (non-blocking)
- 2 个 pytest（`test_cmd_status_outputs_stable_permission_mode_line` / `test_real_interruption_policy_passes`）因读取 `.governance/plan-tracker.md`（gitignored 实时状态）含 in-flight 任务而失败——预先存在的测试隔离缺陷，非本次重构回归，REL-045 任务关闭后自动修复
- P2（不阻断）：`_vw()` 延迟 import 在直接脚本运行时产生 verify_workflow 双模块实例（`__main__` + `verify_workflow`）——当前能跑通，留 0.60.0+ 抽 common 模块时改单向顶层 import 消除

### Boundaries
- **只拆 manifest 域**——其它 check 域（release/governance/agent/capability 等）留 0.60.0~0.64.0
- **不引入** src/pyproject.toml/ruff/mypy 等现代工程基础设施（F2 留 0.64.0）
- **不关闭** RISK-039（拆分 Phase 1/6 非全部完成，且关闭需 1 个外部宿主项目验证 ArchGuard）
- **不关闭** RISK-036/RISK-037
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support
- DEC-086 降级 SoD 诚实标注：主 agent 直接实现 + 事后 Explore 只读审查（当前 harness 仅只读 Explore sub-agent），不如标准先审后合

## [0.58.0] - 2026-06-25

### 0.58.0 - ArchGuard Architecture Health Stewardship (advisory-only)

0.58.0 把 AUDIT-121 F6 架构腐化看护缺口从设计变为可运行产品能力——交付 **ArchGuard**：4 个可独立调用的架构健康 check 命令，让采用本工作流的大型项目在零外部依赖下持续守护架构健康。ArchGuard 守护自身：对 verify_workflow.py（约 2 万行 God Module）触发 module_size ERROR、对 PRODUCT_CODE_PATTERNS 重复定义触发 duplicate_constant ERROR。

**advisory-only 边界**：0.58.0 `gate_integration.fatal_on_error=false`，ArchGuard 的 WARN/ERROR 告警但不阻断 release gate——先观测后收紧，未来版本可启用 fatal。这是 DEC-083 规划的"0.58.0 作为独立产品能力版本交付 ArchGuard，阈值保守默认不阻断现有 release gate，可复用于其他大型项目"。

设计先行（REQ-101/DEC-084），实现前经独立只读复核（EVD-621 READY WITH MINOR GAPS），实现经事后 Explore 只读审查 APPROVED（REVIEW-FIX-152，DEC-085 授权降级 SoD）。约束合规：G6 manifest 双重登记、G7 advisory 不递增 all_issues、G8 ledger 登记、G9 hooks-drift 复用既有 helper（root-leak 已修复+回归测试）。

### Added
- **ArchGuard 4 check 命令**（`check-architecture-health` / `check-duplicate-code` / `check-technical-debt` / `check-complexity`，advisory-only）——模块/函数/常量大小阈值检测（AST）、source/projection 语义重复检测（normalize CRLF+忽略空白）、技术债巡检（游离脚本/release文档/hooks漂移/ledger交叉验证）、复杂度 line-based proxy
- `skills/software-project-governance/core/architecture-health.json` — 声明式架构健康阈值预算 schema（module_size/function_size/module_constants/duplicate_code/complexity/technical_debt/gate_integration）
- `skills/software-project-governance/infra/tests/test_architecture_health.py` — 14 个 unittest（覆盖 module/function/常量大小、重复常量、CRLF 归一化、空白忽略、ledger 交叉验证、hooks 漂移含 G9 root-isolation 回归、G7 advisory、真实 God Module 触发）
- Check 28o~28r 接入 `cmd_check_governance`（3 级 PASS/WARN/ERROR，advisory 不阻断）
- TOOL-043~046（TOOLS.md）

### Changed
- `skills/software-project-governance/infra/verify_workflow.py` 新增 4 个 self-contained `check_*` 函数 + 4 个 `cmd_check_*` handler + CLI subparser + dispatch dict（+~647 行）
- `skills/software-project-governance/core/manifest.json` — G6 双重登记 architecture-health.json（product.entries + canonical_product_artifacts）+ G8 technical-debt-ledger.md 登记
- 版本号全量同步 0.57.0→0.58.0（SKILL.md/plugin.json/marketplace.json/codex-plugin/manifest/hooks/REQUIRED_SNIPPETS/target fixture）

### Known Issues (advisory, non-blocking)
- **TD-012**：`check_duplicate_code` 用"归一化行集合对称差"而非设计 §2.2 的"行计数 diff"计算 duplicate_pct——重复样板行去重使数值偏高于 diff 校准基线。0.59.0+ 承载
- **TD-013**：`check-architecture-health` 全仓库扫描含 `project/e2e-test-project/` projection 副本，导致 module_size/function_size 发现计数虚高（source + projection 双计）。0.59.0+ 承载

### Boundaries
- **不关闭** RISK-036（官方收录准备）/ RISK-037（动态生命周期）/ RISK-039（架构腐化看护——核心缓解 ArchGuard 已就绪，关闭需外部宿主项目验证）
- **不声明** 1.0.0 production-ready / official approval / marketplace approval / universal runtime support
- 0.58.0 ArchGuard 是 advisory-only（fatal_on_error=false），不阻断现有 release gate
- DEC-085 降级 SoD 诚实标注：主 agent 直接实现 + 事后 Explore 只读审查（当前 harness 仅只读 Explore sub-agent），不如标准先审后合

## [0.57.0] - 2026-06-25

### 0.57.0 - Architecture Degradation Audit Archive

0.57.0 是文档/治理记录专用版本，承载 AUDIT-121 全项目架构腐化深度审视归档。该版本**无功能代码变更**——只改版本号字符串断言和新增诊断文档/治理记录。新增诊断报告 `docs/requirements/architecture-degradation-audit-0.57.0.md`（F1-F6 六项腐化事实：verify_workflow.py God Module 20,294 行/439 def+class/54 CLI 子命令；缺失现代工程基础设施 src/lint/type/package；source/projection 双写差异 6,128 行；命令面冗余；自演进遗留物堆积；架构腐化看护缺口根因），新增技术债登记表 `skills/software-project-governance/core/technical-debt-ledger.md`（TD-001~006），清理根目录遗留物（`nul` + `_fix_030_reconstruct.py`）。规划后续 0.58.0 ArchGuard 独立能力版本 + 0.59.0~0.64.0 verify_workflow.py 渐进式按域拆分。该版本不修改 verify_workflow.py 功能代码、不实现 ArchGuard、不拆分任何模块、不引入 lint/type 基础设施、不关闭 RISK-036/RISK-037/RISK-039、不声明 1.0.0 readiness。

### Added
- `docs/requirements/architecture-degradation-audit-0.57.0.md` — AUDIT-121 全项目架构腐化深度审视诊断报告（F1-F6 事实清单 + 影响分析 + 重构路线图）
- `skills/software-project-governance/core/technical-debt-ledger.md` — 技术债登记表 TD-001~006（ArchGuard 0.58.0 将消费）
- `docs/release/release-checklist-0.57.0.md`、`docs/release/feature-flags-0.57.0.md`、`docs/release/rollback-plan-0.57.0.md` — 0.57.0 release docs（含 no-overclaim boundary）
- DEC-083（架构审视三项决策）、RISK-039（架构腐化看护缺口）、EVD-619（AUDIT-121 证据）入账
- plan-tracker 版本路线图扩展 0.57.0~0.64.0 + 活跃事项 + 风险数（2→3）

### Changed
- 版本声明 bump 0.56.1 → 0.57.0：SKILL.md、core/manifest.json、4 个 plugin metadata（Claude/Codex/zcode/marketplace）、顶层 package.json、4 个 source hooks + 4 个 installed hooks @version、zcode-local-load.py、verify_workflow.py REQUIRED_SNIPPETS（6 处版本断言）、README readiness boundary、e2e-test-project projection（SKILL.md + plan-tracker）
- 发现并修复 hooks 内容漂移：4 个已安装 .git/hooks 长期未跟随源更新（post-commit 停在 0.32.0），从 0.57.0 源全覆盖对齐（含 self-upgrade 机制，未来 commit 自动保持同步）

### Removed
- `nul`（根目录，Windows 设备名误创建的未跟踪文件，189 字节，无引用）
- `_fix_030_reconstruct.py`（根目录，FIX-030 一次性重构脚本残留，90 行，FIX-030 早已完成）

## [0.56.1] - 2026-06-24

### 0.56.1 - Web Console Real-Data Dashboard Patch

0.56.1 发布 REL-043 Web console real-data dashboard patch：把已完成、审查通过并经运行时验证的 FIX-151 版本化。该版本修复 Web console 从 100% 硬编码 mock 改为真实数据驱动，解决用户报告的 Project root 假数据和按键无功能问题。Web console 保持只读本地 dashboard 边界不变。

### Added

- **`web/server.py` local API server**: 轻量 stdlib-only Python HTTP server，复用 verify_workflow.py 的 parse 函数读真实 `.governance/` 文件，提供 `/api/governance` JSON 端点 + serve dist 静态文件。
- **`web/vite.config.js`**: Vite 配置 + `/api` proxy 到 API server（dev 模式），无新 npm 依赖。
- **0.56.1 release docs**: 新增 release checklist、feature flags、rollback plan。

### Changed

- **`web/src/main.jsx` refactored to real-data driven**: 删除所有硬编码 mock 常量数组，改为 `fetch('/api/governance')` 真实数据驱动；Project root/project_name/version/gates/evidence/risks 全部来自真实 governance 文件；loading/error/refreshing/notice 状态完整。
- **所有按键功能修复**: 17 个 button 全部有明确 onClick（refresh 刷新数据、navigate 切换路由、notice 显示说明），不能执行的诚实标注 read-only/CLI-only。
- **`cmd_web_console` updated**: 启动 Vite 前后台启动 API server（PID 记录 + 停止提示）。
- **`web/src/styles.css`**: 追加 loading/error/notice/spin 状态类。
- 版本声明同步到 0.56.1。

### Verification

- `npm run build` PASS（1700 modules，dist 生成）。
- `check-manifest-consistency --fail-on-issues` PASS（web/server.py + vite.config.js 在 repo_only 登记）。
- live API 验证：`GET /api/governance` 返回真实数据（project_name=project_management_workflow、release_version=0.56.0、gates=11、evidence_count=595、open_risks=RISK-036/037 真实 deadline）。
- 重启验证通过：API server (5174) + Vite proxy (5173/api) + 前端渲染真实数据三层链路全通。
- Code Reviewer APPROVED（无 P0/P1，3 个 P2 已处理）。

### Boundary

RISK-036 与 RISK-037 保持打开。Web console 仍是只读本地 dashboard（不执行 agent/release/approval 动作），不声明 official approval、marketplace approval、universal runtime support 或 1.0.0 readiness。

## [0.56.0] - 2026-06-24

### 0.56.0 - zcode Plugin Marketplace Adapter Patch

0.56.0 发布 REL-042 zcode plugin marketplace adapter patch：把已完成、审查通过并经运行时验证的 AUDIT-118 版本化。该版本新增 zcode 原生插件市场格式适配产物，并验证本插件能以 zcode 原生格式加载到本机 zcode 运行。这是向 zcode 官方插件市场提交的基础工作，但 0.56.0 本身不提交到官方市场、不声明 marketplace approval。Web console governance-entry、summary-link read-only 行为、动态生命周期边界均不变。

### Added

- **AUDIT-118 zcode plugin marketplace adapter**: 新增 `.zcode-plugin/plugin.json`（zcode 原生插件清单，字段对齐官方 superpowers/restore-legacy-sessions/skill-creator）+ `.zcode-plugin/assets/{logo,composer-icon,governance-preview}.svg` 品牌资产。
- **Top-level `package.json`**: `@zcode/software-project-governance-plugin` npm 包标识，对齐官方 `@zcode/<name>-plugin` scope。
- **`project/zcode-local-load.py` local load tool**: 忠实移植 zcode 运行时种子 hash 算法（`rdt`/`sCr`），提供 `load/--verify/--reload/--unload` 幂等操作 + 备份回滚；实测对官方 skill-creator 字节级复现种子 hash。
- **0.56.0 release docs**: 新增 release checklist、feature flags、rollback plan，并纳入 manifest 覆盖。

### Changed

- `skills/software-project-governance/core/manifest.json` 在 product.entries/glob_patterns/cleanup_scope/root_entries 四处登记 `.zcode-plugin/` 与顶层 `package.json`。
- `verify_workflow.py` 与 `cleanup.py` 的 `PLUGIN_SCOPE_DIRS` 同步新增 `.zcode-plugin`；`verify_workflow.py` REQUIRED_SNIPPETS 补充 `.zcode-plugin/plugin.json` 与 `package.json` 版本断言。
- 版本声明同步到 0.56.0：source SKILL、canonical manifest、Claude/Codex/zcode plugin metadata、Claude marketplace metadata、顶层 package.json、hook `@version`、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。

### Verification

- `check-manifest-consistency --fail-on-issues` PASS（Canonical/Actual 一致，含 `.zcode-plugin` 覆盖）。
- `check-version-consistency` PASS（11+ 文件版本声明一致为 0.56.0）。
- 本机加载四项产物就绪（缓存/seed/marketplace/config），运行时验证通过（EVD-610：用户重启 zcode 后 `/governance` 被本插件消费，Coordinator 激活，Web console 启动）。
- Code Reviewer APPROVED（P0 无；P1 marketplace 重启覆盖风险已用 `--verify`/`--reload` 工具化解决；P2 算法忠实化与拼写已修正）。

### Boundary

RISK-036 与 RISK-037 保持打开。0.56.0 仅证明本插件能本机 zcode 加载运行，不声明 official approval、marketplace approval（zcode 官方市场收录）、universal runtime support、external validation full PASS、Codex Desktop lifecycle PASS、RISK closure 或 1.0.0 readiness。已知限制：手动模拟种子输出依赖 zcode 当前内部逻辑；zcode 升级若改变种子流程，本加载方式可能失效（缓解：`--verify` 复查 + `--reload` 恢复）。

## [0.55.3] - 2026-06-22

### 0.55.3 - Web Console Governance Entry Correction Patch

0.55.3 发布 REL-041 Web console governance-entry correction patch：把已完成并审查通过的 FIX-150 版本化。该版本纠正 0.55.2 对用户意图的误解：用户手动执行 `/governance` 时，产品应该默认启动或复用本地 Web console，并输出 URL，方便后续使用 Web UI 查看工作流状态和继续交互。阶段性任务、工作单元或 session 总结仍只追加 `web-console --summary-link` 的只读结果，不额外启动服务。

### Added

- **FIX-150 Web console governance-entry correction**: 新增 `web-console --governance-entry`，作为手动 `/governance` 的默认 Web UI 启动/复用入口。
- **Governance-entry regression coverage**: 新增 focused tests 覆盖已运行复用、缺依赖显式 `--install`、非 SPG 端口占用 fail-closed、真实 start path 和 summary-link/start conflict。
- **REL-041**: 新增 0.55.3 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- `/governance` source 与 target fixture 改为 SHOULD 在解析 `WORKFLOW_HOME` 后运行 `web-console --governance-entry`，启动或复用本地 Web console 并输出 URL。
- README 与 TOOL-042 将 manual `/governance` 表述为默认 Web UI 入口；`web-console --summary-link` 仍只用于 task/phase/session summary footer。
- `web-console --status` 输出新增 `/governance entry command`，同时保留手动 start/install 命令。
- 版本声明同步到 0.55.3：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook `@version`、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。

### Verification

- `python -m py_compile skills/software-project-governance/infra/verify_workflow.py`
- `python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow.WebConsoleGovernanceEntryTests -v`
- `python -m unittest discover -s skills/software-project-governance/infra/tests -v`
- `python skills/software-project-governance/infra/verify_workflow.py web-console --governance-entry --port 59997 --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py web-console --summary-link --port 59997`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.3 --require-changelog --runtime-adapters`

### Boundaries

- RISK-036 remains open. 0.55.3 does not include official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.55.3 does not implement an apply/write path, does not migrate projects, does not make `dynamic-flow-gate` the default, does not claim non-game preset generalization complete, does not close RISK-037, and does not claim dynamic lifecycle readiness.
- Web remains an optional local companion dashboard. Manual `/governance` may start or reuse it, but Web does not replace CLI/client execution, does not execute agent tasks, does not silently install dependencies, and summary footer mode remains read-only.

## [0.55.2] - 2026-06-21

### 0.55.2 - Web Console Passive Summary Entry Patch

0.55.2 发布 REL-040 Web console passive summary entry patch：把已完成并审查通过的 FIX-149 版本化。该版本让阶段性任务、工作单元或 session 总结可以追加 `web-console --summary-link` 的只读结果；如果 Web console 已运行则报告本地 URL，如果未运行则只报告手动启动命令。手动执行 `/governance` 不会默认启动 Web console、Vite dev server、`npm run dev` 或 `web-console --start`。

### Added

- **FIX-149 Web console passive summary entry**: 新增 `web-console --summary-link`，作为 task/phase/session summary footer 的无副作用入口。
- **Summary-start conflict guard**: `web-console --summary-link --start --fail-on-issues` 在启动逻辑前阻断，避免 summary footer 意外启动服务。
- **REL-040**: 新增 0.55.2 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- `/governance` source 与 target fixture 明确禁止默认启动 Web/Vite/npm dev server，并要求 summary footer 使用解析后的 `WORKFLOW_HOME` 路径，而不是 repo-local `python skills/...` 命令。
- README 与 TOOL-042 将 `--start` 统一表述为用户明确要求时才运行的手动/显式启动路径。
- 版本声明同步到 0.55.2：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook `@version`、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。

### Verification

- `python -m py_compile skills/software-project-governance/infra/verify_workflow.py`
- `python skills/software-project-governance/infra/verify_workflow.py web-console --summary-link --port 59997`
- `python skills/software-project-governance/infra/verify_workflow.py web-console --summary-link --start --fail-on-issues --port 59997`
- `python -m unittest discover -s skills/software-project-governance/infra/tests -v`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.2 --require-changelog --runtime-adapters`

### Boundaries

- RISK-036 remains open. 0.55.2 does not include official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.55.2 does not implement an apply/write path, does not migrate projects, does not make `dynamic-flow-gate` the default, does not claim non-game preset generalization complete, does not close RISK-037, and does not claim dynamic lifecycle readiness.
- Web remains an optional local companion dashboard. It does not replace CLI/client execution or `/governance`, does not execute agent tasks, and does not start by default from manual `/governance`.

## [0.55.1] - 2026-06-21

### 0.55.1 - Web Console CLI/Client Entry Patch

0.55.1 发布 REL-039 Web console CLI/client entry patch：把已完成并审查通过的 FIX-148 版本化。该版本让 CLI/客户端用户可以通过 `web-console --status` 发现本地 Web companion dashboard，并通过 `web-console --start [--install]` 启动它；同时保持 Web 只是本地状态/配置可视化 companion，不替代 `/governance`、不执行 agent 任务、不声明 Desktop embedded UI 或 marketplace lifecycle PASS。

### Included

- **FIX-148 Web console CLI/client entry redesign**: 新增 `web-console --status/--start/--install/--open`，README/TOOLS 改为 CLI 入口优先，Web 首屏和移动端突出 CLI companion 与启动命令。
- **Fail-closed identity probing**: `web/index.html` 新增 SPG identity meta，`verify_workflow.py` 只在页面含 SPG identity 时认定 dashboard running；非 SPG 服务占用端口时报告 `occupied` 并阻断 `--start`。
- **Mobile entry usability**: Web 首屏移动端压缩 topbar/nav/entry，使 Start/Copy 操作在 390x844 首屏内可见。
- **REL-039**: 新增 0.55.1 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Release Sync

- 版本声明同步到 0.55.1：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook `@version`、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.55.1 Web console entry patch + 0.55.0 migration preview/external validation archive，继续保留 `classic-phase-gate` 默认、`dynamic-flow-gate` inactive/non-default opt-in preview。

### Verification

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.1 --require-changelog --runtime-adapters`

### Boundaries

- RISK-036 remains open. 0.55.1 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.55.1 does not implement an apply/write path, does not migrate projects, does not make `dynamic-flow-gate` the default, does not claim non-game preset generalization complete, does not close RISK-037, and does not claim dynamic lifecycle readiness.
- Web console remains an optional local companion dashboard. It does not replace CLI/client execution, does not execute agent tasks, does not silently install dependencies, and is not a Desktop embedded UI lifecycle PASS.

## [0.55.0] - 2026-06-20

### 0.55.0 - Dynamic Lifecycle Migration Preview and External Validation Archive

0.55.0 发布 REL-035 Dynamic Lifecycle migration/external validation package：把已完成并审查通过的 FIX-139 dry-run-only migration preview、VAL-005 python_game validation archive、VAL-006 shitu non-game validation archive 版本化。该版本发布迁移预览和保守外部验证事实，不迁移项目、不把 `dynamic-flow-gate` 设为默认、不关闭 RISK-036/RISK-037、不声明 external validation full PASS 或 1.0.0 readiness。

### Added

- **FIX-139 Dynamic lifecycle migration preview**: 新增 `dynamic-lifecycle-migration --target <path> --dry-run` / `dynamic-flow-gate-migration` 只读预览、0.55.0 migration guide、TOOL-041、manifest coverage 和 dry-run fail-closed 边界。
- **VAL-005 python_game validation archive**: 真实 `python_game` 目标 dry-run preview `READY_FOR_REVIEW`，保留 plan/evidence hash，10 个 chapter flow units 覆盖 released/testing/development/backlog；installed-state full PASS 被 `CLAUDE.md:32` repo-local workflow home assumption 阻断。
- **VAL-006 shitu non-game validation archive**: 真实 Android/Kotlin `shitu` 目标 dry-run preview `READY_FOR_REVIEW`，保留 plan/evidence hash 与 89 条 evidence rows；非 game preset 泛化仍 PARTIAL，因为 flow units 仍来自 `python_game_10_chapters` 示例，installed-state validation 被 native entry/hook drift 阻断。
- **REL-035**: 新增 0.55.0 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- 版本声明同步到 0.55.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook `@version`、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.55.0 migration preview + external validation archive，明确 `classic-phase-gate` 仍为默认、`dynamic-flow-gate` 仍为 inactive/non-default opt-in preview。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.0 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.55.0 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.55.0 releases a dry-run migration preview and validation archives only; it does not implement an apply/write path, does not migrate projects, does not make `dynamic-flow-gate` the default, does not claim non-game preset generalization complete, does not close RISK-037, and does not claim dynamic lifecycle readiness.

## [0.54.1] - 2026-06-16

### 0.54.1 - Governance Hook Nested Plugin Hotfix

0.54.1 发布 REL-036 governance hook hotfix release package：把已完成并审查通过的 FIX-140 版本化为 patch release。该版本只包装 nested plugin/workflow product path detection 与 commit-msg dated evidence row matching hotfix，不改变 0.55.0 Dynamic Lifecycle migration/external validation 规划，不修改 hook 修复逻辑本身，不关闭 RISK-036/RISK-037。

### Fixed

- **FIX-140 nested plugin product path detection**: governance hooks 已能识别根目录产品段和 nested plugin/workflow 产品段，并显式排除 `.governance/**`，避免插件内产品代码提交绕过看护。
- **FIX-140 dated evidence row matching**: `commit-msg` 证据行匹配兼容 `EVD | TASK_ID` 与 `EVD | date | TASK_ID` 两类格式，避免带日期证据行误阻断已审查提交。

### Changed

- **REL-036**: 新增 0.54.1 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。
- 版本声明同步到 0.54.1：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.54.1 hook hotfix package，明确 RISK-036/RISK-037 继续打开。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.1 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.54.1 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, project migration, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.54.1 is a hook hotfix patch only; it does not change 0.55.0 migration/external validation planning, does not migrate projects, does not make dynamic-flow-gate the default, does not change registry automation command execution, does not close RISK-037, and does not claim dynamic lifecycle readiness.

## [0.54.0] - 2026-06-16

### 0.54.0 - Declarative Gate Engine Classic Registry Execution

0.54.0 发布 REL-034 Declarative Gate Engine release package：把 FIX-138 classic registry-backed gate execution 版本化为 lifecycle registry gate execution metadata、TOOL-040 guard、release docs 和 metadata。该版本让 classic G1-G11 gate judgment 从 lifecycle registry 的 `gate_execution_registry` 读取 required artifacts、checks、evidence query、human confirmation policy、severity 和 project-type override metadata，同时保持 automation commands 为 metadata。

### Added

- **FIX-138 classic registry-backed gate execution**: `gate_execution_registry` 覆盖 classic G1-G11 required artifacts、checks、evidence query、automation command metadata、human confirmation policy、severity 和 project-type override metadata。
- **Registry-backed gate judgment**: `auto_judge_gate()` 已改为读取 registry definitions，并在运行前 fail-closed 校验 registry contract。
- **TOOL-040 Declarative Gate Engine guard**: `check-lifecycle-registry --fail-on-issues` 校验 gate execution registry 完整性、executor 合法性、evidence query、override contract、malformed checks runtime fail-closed behavior 和 no-overclaim boundaries。
- **REL-034**: 新增 0.54.0 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- 版本声明同步到 0.54.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.54.0 Declarative Gate Engine classic registry execution package，明确 RISK-036/RISK-037 继续打开。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-lifecycle-registry --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.0 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.54.0 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.54.0 releases classic registry-backed gate judgment only; it does not migrate projects, does not make dynamic-flow-gate the default, does not execute registry automation commands as part of gate judgment, does not close RISK-037, and does not claim dynamic lifecycle readiness.

## [0.53.0] - 2026-06-16

### 0.53.0 - Project-Type Gate Presets

0.53.0 发布 REL-033 Project-Type Gate Presets release package：把 FIX-137 project-type gate presets 版本化为 lifecycle registry preset data、TOOL-039 guard、release docs 和 metadata。该版本覆盖 game、web-app、mobile-app、library、cli-tool、ai-agent-plugin、internal-script，并为每类声明 profile/project-type 正交边界、default packs、quality budget、acceptance templates、release checks、gate policy 和 gate standards。

### Added

- **FIX-137 project-type gate presets**: `project_type_gate_presets` 已覆盖 game/web-app/mobile-app/library/cli-tool/ai-agent-plugin/internal-script；game 标准覆盖 chapter、level、asset、narrative、playability，library 标准覆盖 api、semver、docs、downstream-tests。
- **TOOL-039 Project-Type Gate Presets guard**: `check-lifecycle-registry --fail-on-issues` 校验 preset 完整性、preset/hook 对应、default flow unit type、profile/project-type 正交、game/library 必需标准和 no-overclaim variants。
- **LifecycleRegistry coverage**: FIX-137 证据记录 LifecycleRegistryTests 28/28 PASS，支撑 release package 版本化。
- **REL-033**: 新增 0.53.0 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- 版本声明同步到 0.53.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill/plan、CHANGELOG、README 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.53.0 Project-Type Gate Presets package，明确 RISK-036/RISK-037 继续打开。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-lifecycle-registry --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.53.0 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.53.0 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.53.0 releases project-type preset data and guard coverage only; it does not activate a declarative gate engine, does not migrate projects, does not make dynamic-flow-gate the default, does not close RISK-037, and does not claim dynamic lifecycle readiness.

## [0.52.0] - 2026-06-15

### 0.52.0 - Flow Unit Runtime Visibility

0.52.0 发布 REL-032 Flow Unit Runtime Visibility release package：把 FIX-136 optional flow-unit hot-state visibility 版本化。该版本新增 `.governance/flow-unit-runtime.json` 的可选热状态校验、`check-flow-unit-runtime` CLI，以及 governance context/status 对 flow-unit lanes、per-unit gate_state、loop counters、blocked downstream units 和 rollup status 的只读可见性。

### Added

- **FIX-136 flow-unit runtime visibility**: 新增 optional `.governance/flow-unit-runtime.json` hot-state validator；缺失时 NOT_FOUND safe，格式错误或越界声明 fail-closed。
- **Flow-unit context/status facts**: governance context/status discovery 可以展示 active lanes、per-unit gate_state、loop counters、blocked downstream units 和 rollup status。
- **CLI guard**: `check-flow-unit-runtime [--fixture <path>] [--fail-on-issues]` 用于验证 visibility-only hot state 和 no-overclaim 边界。
- **REL-032**: 新增 0.52.0 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- 版本声明同步到 0.52.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill、CHANGELOG 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.52.0 Flow Unit Runtime Visibility package，明确 RISK-036/RISK-037 继续打开。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-flow-unit-runtime --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.52.0 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.52.0 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.52.0 releases optional runtime visibility only; it does not activate a declarative gate engine, does not migrate projects, does not make dynamic-flow-gate the default, does not close RISK-037, and does not claim dynamic lifecycle readiness.

## [0.51.0] - 2026-06-15

### 0.51.0 - Dynamic Lifecycle Spec Schema-Only Release

0.51.0 发布 REL-031 schema-only release package：把 FIX-135 dynamic lifecycle registry 版本化为 registry/schema/validator/docs。该版本保留 `classic-phase-gate` 作为 active/default compatibility preset，把 `dynamic-flow-gate` 明确为 inactive schema-only mode，并提供 python_game 10 章节示例数据来表达不同章节处于 released/testing/development/backlog 的状态。

### Added

- **FIX-135 lifecycle registry**: `skills/software-project-governance/core/lifecycle-registry.json` 登记 classic stage vocabulary、subphase vocabulary、G1-G11 gate references、allowed transitions、loop policy、flow unit schema、project type hooks 和 python_game 10-chapter example data。
- **Lifecycle validator**: `check-lifecycle-registry` 校验 registry 保持 schema-only、classic-compatible，并阻断 runtime activation、dynamic mode active/default、project type default drift、non-object root crash 和 no-overclaim 文案漂移。
- **REL-031**: 新增 0.51.0 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Changed

- 版本声明同步到 0.51.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill、target fixture plan tracker、CHANGELOG 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.51.0 Dynamic Lifecycle Spec schema-only package，明确 RISK-036/RISK-037 继续打开。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.51.0 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.51.0 does not include official approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.
- RISK-037 remains open. 0.51.0 releases registry/schema/validator/docs only; it does not activate flow-unit runtime, does not migrate projects, does not replace classic G1-G11 behavior, and does not claim dynamic lifecycle runtime readiness.

## [0.50.3] - 2026-06-15

### 0.50.3 - External Installed Runtime Field Repair

0.50.3 发布 REL-030 conservative patch release package：把 FIX-132、FIX-133、FIX-134、VAL-003 和 VAL-004 纳入同一版本边界。该版本修复外部安装态 runtime 路径解析和 hook commit message source 风险，并把 external-project-validation 扩展到 target-native diagnostics；shitu 与 python_game 两个真实外部目标只归档为 FAIL/PARTIAL diagnostic，不构成 external validation full PASS。

### Changed

- **FIX-132 external installed runtime path resolver**: hooks 和 governance command templates 解析 `SOFTWARE_PROJECT_GOVERNANCE_HOME` / `SPG_HOME`、repo-local install 或全局 plugin cache，不再只依赖目标仓库内的 repo-local `skills/software-project-governance/`。
- **FIX-133 hook message source hardening**: pre-commit 不再使用 stale `.git/COMMIT_EDITMSG` / `.git/GOV_COMMIT_MSG` 作为当前提交消息语义来源；commit-msg 继续以实际消息文件为权威来源。
- **FIX-134 target-native field checks**: `external-project-validation --target` 报告目标原生入口 repo-local path assumption、installed hook version/content drift、legacy stale message source 和 repo-local self-upgrade source diagnostics。
- **REL-030**: 新增 0.50.3 release checklist、feature flags、rollback plan、manifest coverage、README readiness boundary 和 release no-overclaim boundary。

### Validation Archives

- **VAL-003 shitu**: `D:\AI\agent\claude\coding\android\shitu` enhanced validation returned exit 1 and is archived as FAIL/PARTIAL diagnostic. It found `CLAUDE.md` repo-local path / verify / hook-copy assumptions plus installed hook drift and legacy pre-commit message-source semantics. Target files were not mutated.
- **VAL-004 python_game**: `D:\AI\agent\claude\coding\python_game` enhanced validation returned exit 1 and is archived as FAIL/PARTIAL diagnostic. Native `CLAUDE.md` passed the repo-local path check, but installed hooks remained at 0.49.0 and pre-commit retained legacy message-source / self-upgrade semantics. Target files were not mutated.

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.3 --require-changelog --runtime-adapters`
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.50.3 releases field repairs and diagnostic archives, not two real external project full PASS evidence.
- 0.50.3 release package does not include official submission approval, marketplace approval, two-real-project external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.

## [0.50.2] - 2026-06-13

### 0.50.2 - External Project Validation Harness

0.50.2 发布 REL-029 patch release package：把 FIX-131 的 external project validation harness 版本化。该版本新增 `external-project-validation --target <path>`，在隔离临时工作区复制 workflow surface、生成最小治理记录、安装 hooks，并运行 status/G1/governance-context/check-governance 矩阵；target 目录保持只读，不被 harness 写入。

### Added

- **REL-029**: 新增 0.50.2 release checklist、feature flags、rollback plan、manifest coverage 和 release boundary。
- **FIX-131 external validation harness**: 新增 `external-project-validation` CLI、temporary workspace builder、generated external validation governance profile、hook installation、command matrix execution、target mutation boundary、workspace-parent containment guard、sentinel-scoped hot fact-source skip 和 timeout/OSError structured failure。
- **TOOL-036**: 在 `infra/TOOLS.md` 中登记 External Project Validation harness。

### Validation

- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ExternalProjectValidationHarnessTests -v`
- `python skills/software-project-governance/infra/verify_workflow.py external-project-validation --target <temp-target> --fail-on-issues --timeout 120`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.2 --require-changelog --runtime-adapters`

### Boundary

- RISK-036 remains open. 0.50.2 releases only the validation harness, not two real external project full PASS evidence.
- 0.50.2 release package does not include official submission approval, marketplace approval, external validation full PASS for two real projects, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.

## [0.50.1] - 2026-06-13

### 0.50.1 - 1.0.0 Release Gate Blocker Guard

0.50.1 发布 REL-028 patch release package：把 FIX-130 的 1.0.0 release gate blocker guard 版本化。该版本确保 `check-release --version 1.0.0 --require-changelog --runtime-adapters` 不会因为缺少 1.0.0 release docs/changelog 而掩盖真实硬阻塞；输出必须显式报告 RISK-036、外部验证 full PASS、official submission result/approval、Codex Desktop lifecycle PASS 或明确保守处置等 blocker。

### Changed

- **REL-028**: 新增 0.50.1 release checklist、feature flags、rollback plan、manifest coverage 和 release boundary。
- **FIX-130 release gate guard**: 0.50.1 release package 消费 `check_one_dot_zero_release_blockers()`，保留 patch release 可发布，同时要求 1.0.0 release gate 在证据不足时显式失败。
- 版本声明同步到 0.50.1：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill、target fixture plan tracker、root plan tracker、CHANGELOG 和 `verify_workflow.py` REQUIRED_SNIPPETS。
- README 的 1.0.0 Readiness Boundary 更新为 0.50.1 guard package，同时保留 0.50.0 四平台 target-cwd read E2E 证据范围。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.1 --require-changelog --runtime-adapters`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters` (expected FAIL with explicit blockers)
- `git diff --check`

### Boundary

- RISK-036 remains open. 0.50.1 releases only the 1.0.0 release gate blocker guard.
- 0.50.1 release package does not include official submission approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready approval.

## [0.50.0] — 2026-06-12

### 0.50.0 — Mainstream Agent E2E Risk Release

0.50.0 发布 Mainstream Agent E2E Risk Release：把 FIX-129 的四平台真实 target-cwd read E2E 证据打包为版本化 release package。该版本记录用户完成 Codex、Claude Code、Gemini CLI 和 opencode 配置后，最终 runtime harness 返回 `pass=4, blocked=0, fail=0, total=4`；同时继续明确这只是主流 agent read/bootstrap E2E 分项风险释放，不关闭 RISK-036，不代表 official approval、marketplace approval、external validation PASS、Codex Desktop lifecycle PASS 或 1.0.0 readiness。

### 新增

- **REL-027**: 新增 0.50.0 release checklist、feature flags、rollback plan、manifest coverage 和 release boundary。
- **FIX-129 evidence package**: 0.50.0 release docs 消费 `docs/requirements/mainstream-agent-e2e-risk-release-0.50.0.md`，把四个平台的 target-cwd read E2E PASS/DEGRADED 事实版本化。

### 变更

- 版本声明同步到 0.50.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill 和 target fixture plan tracker。
- README 的 1.0.0 Readiness Boundary 更新为 0.50.0 evidence package，明确四平台 read E2E 已通过，但外部验证、Desktop lifecycle、official approval/marketplace approval 与 RISK-036 仍未关闭。
- `verify_workflow.py` REQUIRED_SNIPPETS 版本字面量更新为 0.50.0。

### 验证

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.0 --require-changelog --runtime-adapters`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- `git diff --check`

### 发布边界

- No official approval, marketplace approval, universal/full runtime support, external validation PASS, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- RISK-036 remains open. 0.50.0 consumes FIX-129 as mainstream agent target-cwd read E2E sub-risk release evidence only.
- 0.50.0 release package does not include official submission, official approval, marketplace approval, RISK-036 closure, or 1.0.0 release approval.

## [0.49.0] — 2026-06-11

### 0.49.0 — External Validation and Official Submission Closure

0.49.0 发布 External Validation and Official Submission Closure：把 VAL-001、VAL-002、FIX-126 与 FIX-128 的保守证据打包为 pre-1.0.0 release package。该版本记录两个真实外部项目 smoke、Codex CLI marketplace source sync、official-submission candidate bundle final review 和外部新项目空治理 ID 崩溃修复，同时明确 external validation 仍未 full PASS，Codex Desktop marketplace-management lifecycle 仍为 BLOCKED/NOT_RUN，RISK-036 remains open，0.49.0 不是 1.0.0。

### 新增

- **VAL-001**: 新增 `docs/requirements/external-project-validation-0.49.0.md`，记录 `pallets/click` 与 `psf/requests` 真实公开仓库 target-cwd smoke；`status`、`gate G1` 与 `governance-context` 可运行，但完整治理健康仍因临时部分安装缺 README/docs/adapters、无 owner/user pilot、无 full Agent Team E2E 而不标记 external validation PASS。
- **VAL-002**: 新增 `docs/requirements/codex-desktop-marketplace-lifecycle-0.49.0.md`，记录 Codex CLI `codex-cli 0.125.0`、marketplace `add`/`upgrade`/`remove` command surface 和 configured source sync；该证据只证明 CLI marketplace source sync，不证明 Desktop UI install/enable/visibility/invocation/upgrade/uninstall lifecycle。
- **FIX-126**: 新增 `docs/requirements/official-submission-final-bundle-review-0.49.0.md`，把 0.46.0 marketplace submission materials、0.47.0 loading guidance、0.48.0 readiness reconciliation、VAL-001、VAL-002 与 FIX-128 收口为 conservative official-submission candidate bundle review。
- **REL-026**: 新增 0.49.0 release checklist、feature flags、rollback plan、manifest coverage 和 release boundary。

### 变更

- **FIX-128**: 外部新项目空 DEC/EVD/RISK 序列不再让 `check-governance --fail-on-issues` 在 Check 13 崩溃；空序列输出 `no entries found`，DEC/RISK gaps 与当前 completed missing evidence 仍保持阻断，EVD gaps/orphans/historical missing evidence 保持 info-only。
- 版本声明同步到 0.49.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill 和 target fixture plan tracker。
- README 的 1.0.0 Readiness Boundary 更新为 0.49.0 evidence package，明确外部验证、Desktop lifecycle、official approval/marketplace approval 与 RISK-036 仍未关闭。
- `verify_workflow.py` REQUIRED_SNIPPETS 版本字面量更新为 0.49.0。

### 验证

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.49.0 --require-changelog --runtime-adapters`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- `git diff --check`

### 发布边界

- No official approval, marketplace approval, universal/full runtime support, external validation PASS, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- RISK-036 remains open. 0.49.0 consumes VAL-001, VAL-002, FIX-126, and FIX-128 as conservative evidence only.
- 0.49.0 release package does not include commit, push, tag, official submission, official approval, marketplace approval, RISK-036 closure, or 1.0.0 release approval.

## [0.48.0] — 2026-06-10

### 0.48.0 — 1.0.0 Readiness Reconciliation

0.48.0 发布 1.0.0 Readiness Reconciliation：把用户要求推进到 1.0.0 的大目标拆成可验证的 pre-1.0.0 发布链。该版本确认 1.0.0 当前不可发布，完成 readiness gap analysis、legacy requirement reconciliation、final command E2E ledger 和 governance health release-gate false blocker 修复，并把外部验证、Codex Desktop marketplace-management disposition、official submission bundle final review 和 RISK-036 open-risk disposition 保守移交到 0.49.0 或后续正式发布边界。

### 新增

- **AUDIT-113**: 新增 `docs/requirements/one-dot-zero-readiness-gap-analysis-0.48.0.md`，确认当前没有 `v1.0.0` tag，RISK-036 仍打开，缺少两个外部项目验证、Desktop marketplace-management lifecycle PASS 或保守 blocked disposition、final official submission bundle review。
- **FIX-124**: 新增 `docs/requirements/legacy-requirement-reconciliation-0.48.0.md`，把旧 1.0.0 降级需求映射为 absorbed、superseded、still blocking 或 needs final ledger，避免历史路线图误导当前正式发布边界。
- **FIX-125**: 新增 `docs/requirements/final-command-e2e-ledger-0.48.0.md`，集中记录 source proxy、target cwd、target fixture、runtime readiness、mainstream loading、capability context、official submission guard 和 agent-runtime E2E 事实，同时诚实暴露 release-gate blocker。
- **FIX-127**: 修复 governance health release gate 中 historical hot evidence structural WARN 被 `--fail-on-issues` 误当成 blocking issue 的问题；WARN-only structural validity 继续打印但不阻断 governance health，缺省 ERROR 仍阻断。
- **REL-025**: 新增 0.48.0 release checklist、feature flags、rollback plan、manifest coverage 和 release boundary。

### 变更

- 版本声明同步到 0.48.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill 和 target fixture plan tracker。
- README 新增 1.0.0 Readiness Boundary，明确 0.48.0 不是 1.0.0 正式发布。
- `check-release --version 0.48.0 --require-changelog --runtime-adapters` 走通用 release docs coverage、version consistency、manifest consistency、governance health、E2E 和 unit execution gates。

### 验证

- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.48.0 --require-changelog --runtime-adapters`
- `git diff --check`

### 发布边界

- No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- RISK-036 remains open. VAL-001, VAL-002, FIX-126, REL-026, final official submission bundle review, external validation completion, and Desktop marketplace-management disposition are not included in 0.48.0.
- 0.48.0 release package does not include commit, tag, push, official submission, marketplace approval, or 1.0.0 release approval.

## [0.47.0] — 2026-06-10

### 0.47.0 — Mainstream Agent Loading Readiness

0.47.0 发布 Mainstream Agent Loading Readiness：把 Codex、Claude Code、Gemini CLI、opencode 作为 Tier 1 loading guide 目标，把 Cursor、GitHub Copilot coding agent、Cline、Windsurf/Cascade、Kiro 保持为 Tier 2 compatibility/research rows，并用 Check 28n / TOOL-035 防止加载指南、source citations、validation commands 和 no-overclaim boundary 漂移。本 release package 同时披露 tag 范围内已完成的 FIX-120 `0.46.0-post` Codex marketplace root schema hotfix，作为 FIX-123 和 0.47.0 Codex loading readiness 的 carried-forward prerequisite，而不是 0.47.0 新主线功能。

### 新增

- **AUDIT-112**: 新增 `docs/requirements/mainstream-agent-loading-0.47.0.md`，调研主流 agent 加载入口并规划 0.47.0 范围。
- **FIX-120 (carried-forward `0.46.0-post` prerequisite)**: 披露 `.agents/plugins/marketplace.json` 已修复 Codex marketplace root schema（top-level `name`、Codex entry `source` object、policy/category metadata），为后续 Codex manifest asset path validation 和 loading guide 提供前置 schema 基础；该 hotfix 不声明 Codex Desktop marketplace lifecycle E2E PASS。
- **FIX-123**: 修复 Codex manifest asset paths，使 `.codex-plugin/plugin.json` 在 repo-root marketplace source 下引用 `.codex-plugin/assets/*.svg`。
- **FIX-121**: README 与 Tier 1 adapter READMEs 新增 Mainstream Agent Loading 指南、验证命令和运行时边界。
- **FIX-122 / TOOL-035**: 新增 `check-mainstream-agent-loading [--fail-on-issues]`、`check-governance` Check 28n 和 MainstreamAgentLoading 回归测试，阻断 Tier 2 runtime PASS、approval、universal/full runtime support、Desktop marketplace E2E PASS、automatic best-tool selection、catalog runtime PASS 和 1.0.0 overclaim。
- **REL-024**: 新增 0.47.0 release checklist、feature flags、rollback plan、manifest coverage 和 release-doc mainstream loading detail。

### 变更

- 版本声明同步到 0.47.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill 和 target fixture plan tracker。
- `check-release --version 0.47.0 --require-changelog --runtime-adapters` 要求 0.47.0 release docs 存在、被 manifest 覆盖、保留 conservative no-overclaim boundary，并运行 mainstream loading release detail。

### 验证

- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.47.0 --require-changelog --runtime-adapters --skip-execution-gates`
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k MainstreamAgentLoading -v`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ReleaseReadiness -v`

### 发布边界

- No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- Tier 2 rows remain compatibility/research only until native entry projection and target-cwd E2E evidence exist.
- 0.47.0 release package does not include commit, tag, push, official submission, or marketplace approval.

## [0.46.0] — 2026-06-09

### 0.46.0 — Ecosystem & Official Submission Positioning

0.46.0 发布 Ecosystem & Official Submission 定位包：把 0.45.0 的 capability context selection trace、external capability registry、restricted-environment benchmark fixtures、Governance Eval & Benchmark report 和 Codex Desktop marketplace-management BLOCKED/NOT_RUN 结果消费进官方提交材料、生态定位页、对比页、迁移指南、示例和 release checks。本 release 将 workflow 定位为 governance trust layer：负责编排、记录和审查外部 plugin/skill/tool/MCP/browser/host-native capability 的选择与降级边界，而不是替代 Superpowers、Agent Skills、MCP servers、browser tools、host-native plugins 或其他生态能力。

### 新增

- **FIX-118**: 新增 `docs/marketplace/official-submission-0.46.0.md`、`ecosystem-positioning-0.46.0.md`、`comparison-0.46.0.md`、`migration-guide-0.46.0.md` 和 `examples-0.46.0.md`，说明互补定位、迁移路径、受限环境选择示例和官方提交边界。
- **TOOL-034**: 新增 `check-official-submission-ecosystem [--fail-on-issues]`、`check-governance` Check 28m 和 `check-release --version 0.46.0` release-doc detail，确定性阻断官方提交/生态材料缺失 0.45.0 证据消费或出现越界声明。
- **REL-023**: 新增 0.46.0 release checklist、feature flags 和 rollback plan，覆盖官方提交材料、ecosystem boundary、validator、manifest coverage 和 no-overclaim release boundary。

### 变更

- 版本声明同步到 0.46.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、Claude marketplace metadata、hook @version、target fixture skill 和 target fixture plan tracker。
- `check-release --version 0.46.0 --require-changelog --runtime-adapters` 要求 0.46.0 官方提交生态材料被 git 跟踪、被 manifest 覆盖、保留 conservative no-overclaim boundary，并消费 0.45.0 capability selection trace、capability registry、restricted benchmark 与 Codex Desktop marketplace-management BLOCKED/NOT_RUN evidence。

### 验证

- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k official_submission -v`
- `python skills/software-project-governance/infra/verify_workflow.py check-official-submission-ecosystem --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.46.0 --require-changelog --runtime-adapters --skip-execution-gates`
- `git diff --check`

### 发布边界

- No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- Codex Desktop marketplace-management lifecycle remains **BLOCKED / NOT_RUN** until real Desktop add/install/enable/invoke/upgrade/uninstall evidence is captured or the official submission package explicitly preserves the blocked status.
- 0.46.0 release package does not include commit, tag, push, official submission, or marketplace approval.

## [0.45.0] — 2026-06-08

### 0.45.0 — Governance Eval & Benchmark + Capability Discovery

0.45.0 发布 Governance Eval & Benchmark + Capability Discovery：把 capability context trace、external capability registry、restricted-environment benchmark fixtures 和 Codex Desktop marketplace-management E2E report boundary 纳入 release package。本 release 不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS、automatic best-tool selection、universal plugin/skill/tool availability、catalog entry runtime PASS 或 1.0.0 production-ready。RISK-036 继续打开，0.46.0 official submission materials 必须消费本 release 的 blocked Desktop E2E 事实和 capability selection 证据。

### 新增

- **FIX-115**: 新增 `capability-context [--fixture <project-root>] [--fail-on-issues]`、fact-backed capability selection trace、TOOL-031 和 Check 28j；输出 scenario、host facts、available capabilities、selected capability、rejected alternatives、degradation、side-effect boundary、validation command、review requirement 和 no-overclaim boundary。
- **FIX-116**: 新增 canonical `skills/software-project-governance/core/capability-registry.json`、`check-capability-registry`、TOOL-032、Check 28k 和 manifest canonical artifact coverage；registry 记录 plugin/skill/tool/MCP/browser/sub-agent/script/fallback 候选能力，但 catalog membership 不是 runtime PASS。
- **FIX-117**: 新增 `check-host-capability-context`、TOOL-033、Check 28l 和 restricted-environment benchmark fixtures，覆盖 no network、no plugin install、no MCP、no browser、no sub-agent、local skill only、Codex CLI blocked、Gemini auth blocked。
- **REL-022**: 新增 0.45.0 release checklist、feature flags、rollback plan、Governance Eval & Benchmark report 和 Codex Desktop marketplace-management E2E result matrix。

### 变更

- 版本声明同步到 0.45.0：source SKILL、canonical manifest、Claude/Codex plugin metadata、marketplace metadata、governance pack registry、capability registry、hook @version、target fixture skill 和 target fixture plan tracker。
- `check-release --version 0.45.0 --require-changelog --runtime-adapters` 要求 release docs 存在、被 manifest 覆盖、保留 conservative no-overclaim boundary，并对 0.45.0 Codex Desktop marketplace-management report 执行 no-PASS-without-real-evidence guard。

### 验证

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.45.0 --require-changelog --runtime-adapters`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`
- `git diff --check`

### 发布边界

- Codex Desktop marketplace-management lifecycle is **BLOCKED / NOT_RUN** in this release because no real Desktop add/install/enable/invoke/upgrade/uninstall evidence was executed or captured.
- No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready claim.
- 0.45.0 release package does not include commit, tag, or push.

## [0.44.1] — 2026-06-07

### 0.44.1 — Patch Release: no-overclaim 与 context fact coverage

0.44.1 是 0.44.x patch release，发布 FIX-113 和 FIX-114：修复 0.43.0~0.44.0 post-review 发现的 no-overclaim false-pass 与 governance-context fact coverage 缺口。本 release 不改变 pack semantics、不进行物理拆包、不改变 runtime/readiness matrix 或 first-session measurement 状态；不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS 或 1.0.0 production-ready。RISK-036 继续打开，0.45.0~0.46.0 仍承载评测、Desktop marketplace E2E 与官方提交准备链。

### 修复

- **FIX-113**: no-overclaim direct-claim 检查改为 claim-scoped negation，防止 `No physical split; marketplace approved.` 这类同一行无关否定词掩盖 official approval、marketplace approval、universal/full runtime support、external first-session pilot success 或 1.0.0 production-ready 的肯定式越界声明。
- **FIX-114**: governance context discovery 补齐 evidence-log 与 root-scoped git fact discovery，避免把历史 completed/approved/closed/resolved evidence 或父仓库 dirty state 发明成当前 unfinished work，同时让真实 evidence/git/recent work facts 能进入 context handoff。
- **REL-021**: 版本声明、CHANGELOG、release checklist、rollback plan、feature flag 状态、target fixture/projection 版本、hook @version、pack registry workflow version 与 release validation command 同步到 0.44.1。

### 验证

- FIX-113 commit `777bd66758cb6515c488c2eac25dde5f7a7ddd1b` 已推送且 GitHub Governance CI success。
- FIX-114 commit `fa4f2d115a762afe8c92f7debea0cfa8f89beed9` 已推送且 GitHub Governance CI success。
- `check-version-consistency` 作为 REL-021 版本一致性门禁。
- `check-release --version 0.44.1 --require-changelog --runtime-adapters --skip-execution-gates` 作为 REL-021 发布门禁。
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ProjectionSync -v` 作为投影同步回归。
- `git diff --check` 作为 whitespace 门禁。

### Release 边界

- 0.44.1 只准备 patch release package，不包含 commit、tag、push。
- Pack enabled / pack membership 仍不是任务证据、独立审查、质量门禁、发布门禁、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready 证明。
- `governance-core` context resume 只基于事实源承接 unfinished work；没有事实时不得编造。
- 0.44.1 不改变 0.43.0 runtime/readiness matrix 和 first-session measurement 事实边界：外部 first-session pilot 仍未被本 release 声明为成功。

## [0.44.0] — 2026-06-07

### 0.44.0 — Composable Governance Packs

0.44.0 将治理能力从单一整包叙事推进为 registry-first 的 Composable Governance Packs：先建立可检查的 pack registry、README 首跑映射、manifest/cleanup 保护、上下文恢复能力和 status/release 边界，而不进行物理拆包。现有 `lite` / `standard` / `strict` profiles 保持为治理强度预设；packs 是能力模块。 本 release 不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS 或 1.0.0 production-ready；RISK-036 继续打开，0.45.0~0.46.0 仍承载评测、Desktop marketplace E2E 与官方提交准备链。

### 新增

- **AUDIT-108**: 完成 0.44.0 Composable Governance Packs 需求拆解，确定 registry-first/no physical split 最小切片，并规划 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise` 五类能力包。
- **AUDIT-109 / FIX-112**: 新增 context-aware governance resume：`governance-context`、`/governance`/status contract、target fixture 与 Check 28g 基于 plan/session/risk/evidence/git facts 发现 unfinished work；无事实时必须输出 `not found` / `do not invent`。
- **FIX-108**: 新增 canonical `skills/software-project-governance/core/governance-packs.json`、`check-governance-packs`、Check 28f 与 TOOL-026，阻断缺字段、未知/重复 pack、缺引用文件、未知检查和 pack overclaim。
- **FIX-109**: README 中英文 5-Minute Start 新增 packs vs profiles 说明和首跑映射：lite -> `governance-core`；standard -> `governance-core` / `quality-gates` / `release-governance` / `agent-team`；strict -> 五个 pack 全部启用。
- **FIX-110**: `core/manifest.json` 将 pack registry 声明为 canonical product artifact，并新增 manifest/cleanup scope guard 与 TOOL-029，防止 registry 漏发、未跟踪或被 cleanup 范围漂移误删。
- **FIX-111**: `/governance`、`/governance-status` 与 release readiness 新增 Pack summary、Default packs、Enabled packs、Pack boundary；新增 `check-governance-pack-status`、Check 28i 与 TOOL-030，逐行阻断把 pack membership/enablement 包装成任务证据、审查通过、质量门禁、发布门禁、官方/市场批准、全量 runtime 支持或 1.0.0 readiness。
- **REL-020**: 版本声明、CHANGELOG、release checklist、rollback plan、feature flag 状态、target fixture/projection 版本和 hook @version 同步到 0.44.0。

### 验证

- `check-governance-packs --fail-on-issues` PASS。
- `governance-context --fixture project/e2e-test-project --fail-on-issues` PASS。
- `check-readme-pack-guidance --fail-on-issues` PASS。
- `check-manifest-consistency --fail-on-issues` PASS。
- `check-governance-pack-status --fail-on-issues` PASS。
- 完整 unittest PASS：351/351。
- `check-governance --fail-on-issues` PASS。
- `check-version-consistency` 与 `check-release --version 0.44.0 --require-changelog --runtime-adapters` 作为 REL-020 发布门禁。

### Pack 与 Release 边界

- 0.44.0 是 registry-first/no physical split；安装包仍向后兼容现有入口。
- Pack enabled / pack membership 不是任务证据、独立审查、质量门禁、发布门禁、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready 证明。
- `governance-core` 的 context resume 只基于事实源承接 unfinished work；没有事实时不得编造。
- 0.44.0 不改变 0.43.0 runtime/readiness matrix 和 first-session measurement 事实边界：外部 first-session pilot 仍未被本 release 声明为成功。

## [0.43.0] — 2026-06-05

### 0.43.0 — Cross-Harness E2E Closure

0.43.0 关闭 0.40.1~0.42.0 发布后复核发现：把跨会话恢复事实、主流 agent runtime/readiness 状态和 first-session measurement 边界转成 tracked artifacts 与机器检查。本 release 不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success 或 1.0.0 production-ready；RISK-036 继续打开，后续 0.44.0~0.46.0 仍承载官方收录准备链。

### 新增

- **FIX-105**: `check-hot-fact-source` / `check-governance` 新增 session snapshot freshness 与 1.0.0 readiness blocker drift 检查，覆盖 REL-018/REL-019 dependency wording。
- **FIX-106**: 新增公开 runtime/readiness matrix：`docs/requirements/runtime-readiness-matrix-0.43.0.md`；刷新 Claude/Codex/Gemini/opencode adapter facts；新增 `check-runtime-readiness-matrix` 与 Check 28d。
- **FIX-107**: 新增 first-session measurement artifact：`docs/requirements/first-session-measurement-0.43.0.md`；README 增加 measured-state pointer；新增 `check-first-session-measurement`、Check 28e、release readiness detail 与 TOOL-025。
- **REL-019**: 版本声明、CHANGELOG、release checklist、rollback plan、feature flag 状态、target fixture/projection version、hook versions 和 release gate expectation 同步到 0.43.0。

### 验证

- `check-runtime-readiness-matrix --fail-on-issues` PASS。
- `check-first-session-measurement --fail-on-issues` PASS。
- `first-run-demo --assert-snapshot` PASS。
- 完整 unittest PASS：316/316。
- `check-governance --fail-on-issues` PASS。
- `check-release --version 0.43.0 --require-changelog --runtime-adapters` 作为 REL-019 发布门禁。

### Runtime 与 Measurement 边界

- Claude 与 opencode real target-cwd E2E 为 PASS，但 workflow closure 仍按宿主能力保持 DEGRADED 边界。
- Codex real `codex exec` target-cwd E2E 在当前环境保持 BLOCKED，阻塞原因为 timeout。
- Gemini 在当前环境因 auth 未配置保持 BLOCKED。
- Cursor 与 GitHub Copilot 在本仓库保持 RESEARCH_ONLY / NOT_RUNTIME_VERIFIED。
- First-session measured state 为 `local_demo=PASS`、`external_pilot=NOT_MEASURED`；local/demo-only proof 不是 external user success evidence。

## [0.42.0] — 2026-06-04

### 0.42.0 — 5-Minute Success Path

面向新用户首次接触时的 5 分钟成功路径，0.42.0 将 0.41.0 的 marketplace-ready 定位落到可感知的本地 trust signal：用户可以通过 `/governance` 或 status 输出看到 Delivery Trust Snapshot，并用本地 demo harness 验证 happy path。该版本是 5-minute success path release package，不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready；RISK-036 继续打开，等待后续 0.43.0~0.46.0 与外部验证闭环。

### 新增
- **AUDIT-106**: 完成 5-minute success path 审计，定义 happy path、验收信号、最小切片和 no-overclaim 边界。
- **FIX-100**: 新增 Delivery Trust Snapshot 垂直切片，让 status/governance 输出展示 goal、stage、gate、risk、evidence、next action、preset guidance 和 no-overclaim boundary。
- **FIX-101**: 新增 existing-project resume happy path，已有治理状态会显示 resume state、carry-over、open risks、hooks 和 next action，而不是要求用户重学完整流程。
- **FIX-102**: 新增 lite/standard/strict first-run preset guidance，帮助用户按项目复杂度选择首次运行路径。
- **FIX-103**: 新增 `first-run-demo --assert-snapshot` 本地 demo harness，输出 Delivery Trust Snapshot 并断言 happy path 字段完整。
- **FIX-104**: README 中英文 5-Minute Start 收敛到 first-success path，直接指向 Delivery Trust Snapshot 和本地 demo harness。

### 变更
- `.codex-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、canonical manifest、source skill、hooks 和 target fixture/projection 版本声明同步到 0.42.0。
- Release gate expectations、target fixture plan-tracker 和 target workflow skill markers 更新为 0.42.0。
- 0.42.0 release docs 新增 checklist、rollback plan 和 feature flag 状态，范围限定为 AUDIT-106、FIX-100、FIX-101、FIX-102、FIX-103、FIX-104 与 REL-018。

### 验证
- `check-version-consistency` PASS。
- `check-release --version 0.42.0 --require-changelog --runtime-adapters` PASS。
- `check-governance --fail-on-issues` PASS。
- `git diff --check` PASS。

## [0.41.0] — 2026-06-02

### 0.41.0 — Official Marketplace Readiness

面向 Codex/Claude 官方目录可评审准备，0.41.0 将项目对外定位收敛为 AI coding delivery trust layer，并补齐 marketplace reviewer 能快速检查的 metadata、README 首屏、privacy/security 文档、submission checklist 和可追踪视觉资产。该版本是 readiness package，不声明官方收录、marketplace approval、1.0.0 production-ready 或 universal/full runtime support；RISK-036 继续打开，等待后续 0.42.0~0.46.0 与外部验证闭环。

### 新增
- **AUDIT-105**: 完成 official marketplace readiness gap analysis，拆解 0.41.0 可执行事项与非目标。
- **FIX-096**: Codex/Claude plugin metadata 升级为官方评审友好的保守包信息；Codex manifest 增加 `skills` 与 `interface` metadata、capabilities、default prompts、logo/icon/preview references。
- **FIX-097**: README 首屏改为英文 marketplace-review-ready positioning，突出 AI coding delivery trust layer、install paths、trust/data boundary 和 5-minute start。
- **FIX-098**: 新增 privacy/security posture 与 submission checklist，说明 local data boundary、permissions and side effects、runtime capability honesty、No telemetry service 与 No official acceptance claim。
- **FIX-099**: 新增 Codex/Claude plugin package 的 tracked SVG logo、composer icon 和 governance preview assets，并让 manifests 引用这些可检查资产。

### 变更
- `.codex-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、canonical manifest、source skill、hooks 和 target fixture/projection 版本声明同步到 0.41.0。
- `docs/marketplace/submission-checklist-0.41.0.md` 从准备中清单更新为 0.41.0 pre-submission readiness checklist，保留 no-overclaim 和风险披露边界。

### 验证
- `check-version-consistency` PASS。
- `verify` PASS。
- `check-manifest-consistency` PASS。
- `check-release --version 0.41.0 --require-changelog --runtime-adapters` PASS。
- `check-governance --fail-on-issues` PASS。
- `git diff --check` PASS。

## [0.40.1] — 2026-06-01

### 0.40.1 — GitHub CI clean checkout hotfix

面向 0.40.0 发布后的 GitHub Actions 失败，0.40.1 只承载 `FIX-095` 的 CI clean checkout 修复链正式版本化，不引入新功能。该版本把默认 CI 校验边界收敛为可追踪产品/repo 资产，避免依赖本机 `.governance/` 运行态或根入口文件，并保证 GitHub workflow 固定的 Python 3.11 环境可运行。

### 修复
- **FIX-095**: 默认 `verify` 不再依赖未跟踪的本地治理运行态或根入口文件；clean checkout 可复现。
- **FIX-095**: 修复 Python 3.11 不能解析 nested f-string 的远端失败。
- **FIX-095**: CI unit test step 改为标准库 `unittest discover`，避免 workflow 未安装 `pytest` 时失败，同时保持 360 个测试收集覆盖不降低。

### 验证
- GitHub Governance CI run `26754020310` 在 `c5f66206f8b8df968ea6c4f2b419c51dc95af5fd` 上 `completed/success`。
- 最新 GitHub Governance CI run `26757836225` 在 `e882006d3343be291bb3f7f75a0f15862af981ae` 上 `completed/success`。
- `check-release --version 0.40.1 --require-changelog --runtime-adapters` 作为发布门禁。

## [0.40.0] — 2026-05-30

### 0.40.0 — AI 指令精度收敛

面向 AI 执行者读取 workflow 文本时的歧义风险，把角色、契约、skill、入口、路由和调度模板中的昵称、人设故事、PUA/味道注入、口号式方法论和无操作定义描述收敛为可执行职责、边界、证据要求和路由规则。0.40.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再发布正式标签。

### 变更
- **AUDIT-104**: 完成 AI-facing 文本审计，识别入口 SKILL、agents、references、commands、target fixture 和当前实际入口中的歧义文本类别。
- **FIX-094**: 去人格化、去口号化并同步 source 与 target fixture；`methodology-routing` 改为任务类型、执行方法和证据要求映射；dispatch template 去掉 `agent_nickname`；failure modes 改为事实依据、完成定义和升级链。
- 主入口 Agent 分发路由列从“核心方法论”改为“执行要求与证据”，部署、模糊任务和测试相关行改为可检查动作与证据。

### 验证
- 完整 `test_verify_workflow.py` 回归 285/285 PASS。
- `verify` PASS；`e2e-check` PASS；`check-projection-sync --fail-on-issues` PASS；`check-governance --fail-on-issues` PASS。
- `git diff --check` PASS，仅 CRLF warning。
- Code Reviewer Copernicus 复审 APPROVED。

## [0.39.0] — 2026-05-30

### 0.39.0 — LLM 依赖降低与产品成功门禁

面向“流程跑完但产品仍是低质半成品”的真实使用风险，把成熟软件公司的产品成功、验收、质量预算、小批量交付和 paved path 经验固化为可检查契约。0.39.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再发布正式标签。

### 新增
- **FIX-088**: 新增 Product Success Contract、`check-product-success-contracts` 和 Check 18d，要求 P0/P1 任务写明用户、JTBD、非目标、成功指标、竞争基线和完成定义。
- **FIX-089**: 新增 Executable Acceptance Contract、`check-acceptance-contracts` 和 Check 18e，阻断缺少可运行验收命令、预期输出、last-run 结果或 demo 证据的闭环。
- **FIX-090**: 新增 Quality Budget Gate、`check-quality-budget` 和 Check 18f，覆盖 performance、reliability、security、accessibility、ux、maintainability 六维阈值和证据。
- **FIX-091**: 新增 Vertical Slice Delivery Packets、`check-vertical-slices` 和 Check 18g，要求大任务具备用户可见小切片、demo path、scope guard 和 rollback plan。
- **FIX-092**: 新增 Weak-LLM Deterministic Scaffolds、`generate-deterministic-scaffold`、`check-deterministic-scaffolds`/`check-scaffold-templates` 和 Check 18h，提供 web-app、cli-tool、workflow-plugin 三类确定性脚手架。
- **FIX-093**: 新增 User Interruption Policy v2、`check-interruption-policy`/`check-user-interruption-policy` 和 Check 18i，只在产品意图、验收标准、不可逆、发布、风险、外部依赖和模式变更处打断用户。

### 变更
- P0/P1 execution packet 扩展为产品成功、可执行验收、质量预算、垂直切片、用户打断策略的统一短上下文载体。
- release gate 现在会联动 0.39.0 产品成功门禁，降低弱 LLM 仅凭治理文本和主观判断闭环的空间。
- RISK-034 由 0.39.0 发布链路承载关闭；1.0.0 依赖链继续要求外部验证通过。

### 验证
- 完整 `test_verify_workflow.py` 回归达到 285/285 PASS。
- `check-governance --fail-on-issues` PASS，Check 18d、18e、18f、18g、18h、18i 均通过。
- `check-release --version 0.39.0 --require-changelog --runtime-adapters` PASS。
- `verify` PASS；`e2e-check` PASS；`check-agent-adapters --runtime` PASS。
- Code Reviewer/Release Reviewer 均已 APPROVED。

## [0.38.0] — 2026-05-28

### 0.38.0 — AI 执行底座：能力契约、结构化证据、执行包与事实源一致性

面向“AI 辅助人开发”场景的执行可靠性版本，把长规则遵从下沉为可检查的运行时能力契约、结构化证据、短执行包、Agent Team 降级模式、投影同步和热区事实源一致性。0.38.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再发布正式标签。

### 新增
- **FIX-082**: Claude/Codex/Gemini/opencode adapter manifest 新增 `runtime_capabilities`，声明 AskUserQuestion、sub-agent、tool、browser、MCP、git hook 和 workflow closure 的真实能力与降级模式。
- **FIX-083**: `check-governance` 新增 Structured Evidence 检查，当前 release 产品代码证据必须包含 `结构化事实:` JSON，记录命令、退出码、摘要、文件 diff 和 review 结论。
- **FIX-084**: 新增 `.governance/execution-packets.json`、`execution-packet` 子命令和 Check 18c，活跃 P0/P1 任务必须具备短上下文执行包。
- **FIX-086**: 新增 `check-projection-sync`，发布前检查 source workflow、target fixture、native entry 和 plugin manifest 的版本与投影同步。
- **FIX-087**: 新增 `check-hot-fact-source`，并接入 `check-governance` Check 28c 与 `check-release` hot fact source detail，阻断 0.37.0/0.38.0/1.0.0 热区叙事冲突。

### 变更
- **FIX-085**: Agent Team review coverage 排除 degraded evidence、Coordinator/Developer 自审和缺独立 Reviewer 标识的 review-like 记录；宿主无真实 sub-agent/Reviewer 分离时不得伪装完整闭环。
- **FIX-086**: Projection sync release blocker 仅基于 git 可复现的 tracked target fixture；未跟踪 materialized projection copies 只作为 skipped diagnostics。
- **FIX-087**: 1.0.0 依赖链必须保留 RISK-033、REL-013 和阻断语言；已完成 FIX range 不得继续写成待实施或待闭环。

### 验证
- 完整 `test_verify_workflow.py` 回归达到 229/229 PASS。
- `check-governance --fail-on-issues` PASS，Check 18b、18c、28b、28c 均通过。
- `check-release --version 0.38.0 --require-changelog --runtime-adapters` PASS。
- `verify` PASS；`e2e-check` PASS；`check-agent-adapters --runtime` PASS。
- Code Reviewer/Release Reviewer 均已 APPROVED。

## [0.37.0] — 2026-05-22

### 0.37.0 — 事实依据看护 + CLAUDE.md 升级 hook 例外

用户反馈驱动的可信度修复版本，覆盖“修改和检视必须基于可复查事实”的全流程看护，以及 `CLAUDE.md` 通过插件版本升级自动同步时被 pre-commit Step 6 误拦截的问题。

### 新增
- **FIX-080**: bootstrap、behavior protocol、change-impact checklist 和 reviewer skills 新增事实依据红线；产品代码证据必须包含 `事实依据:`。
- **FIX-080**: `check-governance` 新增 Fact Grounding 检查，覆盖当前进行中版本的产品代码证据，阻断缺少事实依据或含风险措辞的闭环记录。
- **FIX-080**: `commit-msg` Step 12 新增事实依据阻断，产品代码提交在缺少 evidence-log、缺少 `事实依据:` 或证据含风险措辞时失败。
- **FIX-081**: `pre-commit` Step 6 新增合法 bootstrap self-upgrade 例外，允许插件版本升级同步 `CLAUDE.md`。

### 变更
- **FIX-081**: `CLAUDE.md` 升级例外收紧为真实版本转换：staged plan-tracker 工作流版本必须升级到 source `SKILL.md` version，HEAD 必须存在旧版本，staged `CLAUDE.md` 必须保留 bootstrap marker，且 bootstrap 区域之外内容不得变化。
- **FIX-080**: release/design/code review skill 均要求审查结论基于文件、命令、测试、日志、用户输入或外部文档证据；未验证内容必须标注为 blocked/unknown，而不是作为完成事实。

### 验证
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k FactGrounding -v`: 7/7 PASS。
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k PreCommitClaudeBootstrapUpgradeHookTests -v`: 5/5 PASS。
- 完整 `test_verify_workflow.py` 回归达到 195/195 PASS。
- `check-governance --fail-on-issues` PASS，Fact Grounding 当前版本证据通过。

## [0.36.0] — 2026-05-22

### 0.36.0 — 真实 agent runtime E2E 闭环补强

面向“主流 agent 适配闭环必须通过真实环境 E2E 用例验证”的补强版本，覆盖 Claude/Codex/Gemini/opencode 四平台真实命令矩阵、target fixture/native entry 升级、Codex CLI full coverage 防夸大、Gemini auth preflight、opencode provider/model preflight 与 90s target-cwd real runtime E2E PASS。

### 新增
- **FIX-075**: `project/e2e-test-project` 升级到当前 workflow 版本并补齐 `CLAUDE.md`、Codex/opencode `AGENTS.md`、Gemini `GEMINI.md` thin projection；`e2e-check` target fixture checks 扩展到 7 项。
- **FIX-076**: 新增 `agent-runtime-e2e` 子命令，统一 Claude/Codex/Gemini/opencode 真实 runtime command matrix、PASS/BLOCKED/FAIL schema、timeout 进程树清理和 opencode JSON text event 解析。
- **FIX-078**: 新增 `gemini-auth-preflight`，secret-safe 检测 Gemini CLI、version、API key、Vertex、GCA、settings auth 来源；缺凭据时输出机器可读 BLOCKED guidance。
- **FIX-079**: 新增 `opencode-provider-preflight`，secret-safe 检测 opencode provider/model 配置，识别 `deepseek-v4-pro` / `deepseek-v4-flash`，阻断 invalid suffix、ANSI residue 和 unsupported model 回退。

### 变更
- **FIX-077**: Codex adapter 当前状态从 Codex App session full coverage 纠正为 CLI headless target-cwd `blocked` / `full_e2e_verified=false`；`check-agent-adapters` 要求 Codex full coverage 必须有真实 `codex exec` target-cwd headless 证据。
- **FIX-078**: Gemini adapter 显式区分 runtime/version probe、auth preflight 和 real agent E2E；当前本机因 auth missing/401 保持 blocked，不宣称 full coverage。
- **FIX-079**: opencode adapter 从旧 DeepSeek invalid model blocked 口径更新为 provider/model preflight PASS + `agent-runtime-e2e --agent opencode --timeout 90` real target-cwd PASS，`full_e2e_verified=true`。

### 验证
- `agent-runtime-e2e --timeout 90`: Claude PASS；opencode PASS；Codex BLOCKED timeout；Gemini BLOCKED auth；fail=0。
- `check-agent-adapters --runtime`: Claude/Codex/Gemini/opencode runtime version probes PASS。
- 完整 `test_verify_workflow.py` 回归达到 183/183 PASS。
- 0.36.0 不声明 1.0.0 production-ready；Codex/Gemini 仍按真实阻塞状态记录，不宣称 full coverage。

## [0.35.0] — 2026-05-20

### 0.35.0 — 八维度复核收口：事实源、适配层、Agent 边界与 E2E 真实性

AUDIT-100 八维度复核后的收口版本，覆盖架构事实源一致性、Agent Team 角色边界、主流 code agent 适配状态真实化、Skill/工具库收口、防跑偏看护强化，以及 E2E 从 source proxy 扩展到 external target cwd 与 agent runtime 分层。0.35.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再发布正式标签。

### 架构与事实源
- **AUDIT-100**: 八维度复核完成，形成 FIX-069~074 修复链和 RISK-030 风险处置。
- **FIX-069**: 架构事实源状态收敛，`verify` 纳入 1.0.0 依赖链、路线图、需求矩阵、RISK-030 和 architecture.md 状态一致性检查。
- **FIX-070**: Agent Team 角色边界收口，Governance Developer、具名 Reviewer、通信 I/O 和 Coordinator 单点写回边界进入文档与回归门禁。

### 适配层与 E2E 真实性
- **FIX-071**: Claude/Codex/Gemini/opencode adapter manifest、launcher、README 与 runtime probe 状态真实化；未验证平台不得宣称 full coverage。
- **FIX-074**: `e2e-check` 新增 external target cwd 命令矩阵；adapter contract 强制 `target_cwd_e2e` 与 `agent_runtime_e2e` 双块，`full_e2e_verified=true` 不得绕过真实执行证据。Claude real agent target cwd PASS；Codex App workflow session PASS；Gemini/opencode agent runtime 当前 blocked 且不宣称 full coverage。

### 工具化与防跑偏看护
- **FIX-072**: `infra/TOOLS.md` 完整索引发布/适配/归档/清理/hooks/cross-reference 工具，`check-release` 子命令默认执行 verify、governance health、e2e 和 unittest execution gates。
- **FIX-073**: 目标对齐、用户影响和审查覆盖检查纳入当前产品代码交付证据，避免 impact/review checks 因归档、证据类型或表结构漂移而空跑。
- **RISK-030**: 0.35.0 修复链闭环后关闭；Gemini/opencode blocked 状态和 1.0.0 外部验证门槛继续显式保留。

## [0.34.0] — 2026-05-14

### 0.34.0 — 审查驱动质量回收 + plan-tracker 标准化

AUDIT-099 全项目审查后的质量回收版本，覆盖真实 E2E、防护网恢复、审查降级防护、归档数据源、持续归档、治理信噪比、架构事实源、Gate 证据质量和治理热文件标准化。

### 审查与验证防护
- **AUDIT-099**: 全项目质量审查闭环，识别并收敛 0.34.0 质量回收范围。
- **FIX-059**: Stage 子工作流路径事实源修复，恢复 stage skill 路径验证可靠性。
- **FIX-060**: E2E 从静态检查升级为真实命令代理矩阵，提升端到端验证可信度。
- **FIX-061**: `/governance-review` 禁止 Coordinator 自审降级，补充 review fallback 防护与 Check 27。

### 归档与治理数据质量
- **FIX-062**: verify_workflow 归档数据源测试隔离与审查覆盖检查修复，避免归档数据污染当前验证。
- **FIX-063**: 持续归档触发闭环，archive.py --auto 支持发布强制、task 增量和 90 天兜底触发。
- **FMT-001**: plan-tracker 热文件标准化，移除历史路线图/样例表/已归档任务段，保持活跃治理数据轻量可读。

### 治理信噪比与事实源收敛
- **FIX-064**: `/governance` 升级路径同步持续归档 Step E，status/init 输出契约补齐 permission_mode。
- **FIX-065**: 架构事实源收敛，统一 Agent/Coordinator 数量、Release/operations 边界、入口层边界和路由表口径。
- **FIX-066**: 治理检查信噪比治理，收敛 M5、manifest、归档历史、cross-reference、lock 和 untracked 噪音。
- **FIX-067**: G10/G11 Gate 自动判定可信度修复，弱代理条件替换为真实证据并补归档感知。

## [0.33.0] — 2026-05-10

### 0.33.0 — 治理数据升级迁移流程

**SYSGAP-030 Phase 2**: 治理数据升级迁移流程

- archive.py 新增 `migrate --auto` 模式——自动检测版本边界、pre-check dry-run、内建 verify + 回滚
- governance-init.md 新增 Step 5.5（归档目录结构创建）
- governance-init.md Step 7 三级 profile 模板同步——归档感知读取 + Step E 归档迁移检测
- test_archive.py 新增 8 个 `--auto` 模式测试用例（24/24 PASSED）

## [0.32.0] — 2026-05-08

### 0.32.0 — Agent 调度可靠性——并发控制 + 清洁度治理

FIX-056 和 FIX-057 两项 Agent 可靠性专项，建立"防多 spawn + 防脏仓库"双层系统级防护。

### Agent 并发防护 (P0)
- **FIX-056**: Agent 意外并发防护——两道防线（task_id 去重 + agent-locks.json 文件锁），防止 Coordinator 误判超时导致重复 spawn 同一任务。
  - Phase 1（核心锁机制）: agent-locks.json 锁表模板 + behavior-protocol.md M7.6a 锁协议 + agent-communication-protocol.md 超时处理语言强化（MUST AskUserQuestion）+ SKILL.md Coordinator 铁律 + agent-dispatch-template.md 锁声明占位符
  - Phase 2（锁清理 + 检测）: post-commit hook Step 5 锁清理 + scope creep 检测 + verify_workflow.py Check 25 agent_lock_consistency + check-locks 子命令
  - ADR-005 架构决策记录归档（5 WARNING → 全部修复）

### 仓库清洁度治理 (P1)
- **FIX-057**: 项目清洁度治理——未跟踪文件分类归档 + .gitignore 更新 + 系统级未跟踪检测。
  - Phase 1: 6 个文档归档到 docs/ + .gitignore 新增项目特定忽略规则 + evidence-log.md/risk-log.md 解除 Git 跟踪
  - Phase 2: verify_workflow.py Check 24 未跟踪文件检测 + pre-commit hook Step 10 未跟踪文件阻断（cleanliness BLOCK）

## [0.31.0] — 2026-05-05

### 0.31.0 — 验证驱动修复 + 收尾打磨

外部项目实战验证 (FIX-042) 发现 3 个问题（cleanup 范围边界/Check 10 M5 误报/commit-msg hook 缺失）全部修复。同时完成内部归档清理、Agent 体验打磨和版本 bump 自动化。

### 验证驱动修复 (P0/P1)
- **FIX-053 (P0)**: cleanup.py 范围边界修复——`PLUGIN_SCOPE_DIRS` 常量化，`scan_actual()` 重写为仅扫描插件目录。不再误删用户项目文件。
- **FIX-054 (P1)**: Check 10 M5 反模式检测误报修复——排除 `skills/`/`agents/`/`commands/` 等插件自审计路径，262 hits → 0。
- **FIX-055 (P2)**: commit-msg hook 安装链路补全——governance-init.md + bootstrap 模板 + Hook 存活检测等 9 文件补充 commit-msg hook 引用。

### 版本 bump 自动化 (P1)
- **FIX-052**: verify_workflow.py 新增 `check-version-consistency` 子命令——跨 11 文件同步版本号（JSON/MD/hook @version）+ SKILL.md 为事实源 + CHANGELOG + plan-tracker 对比 + snippet 自检。check-governance Check 23 集成。

### 内部归档 (P2)
- **FIX-031**: 六层架构文档归档——从 SKILL.md 移除空引用（`references/architecture.md` → `docs/architecture/`）
- **FIX-032**: M2 预加载路径修复——`main-workflow.md` → `skills/main-workflow/SKILL.md`
- **FIX-034**: 清理幽灵 Agent 文件确认——coordinator.md 已于 AUDIT-095 标注 DEPRECATED，governance-developer.md 仍被路由表引用（非幽灵文件）

### 体验打磨 (P2)
- **FIX-039**: Agent 工作可见性——Coordinator spawn agent 时输出进度通知 + 完成报告格式标准化
- **FIX-040**: 角色昵称收敛——用户可见消息用功能性描述替代昵称（5 文件）
- **FIX-041**: Scenario F 状态面板输出折叠优化——3 项非关键信息（Gate 表/最近活动/插件版本）用 `<details>` 折叠
- **FIX-042**: 外部项目实战验证——6/12 场景通过，3 问题发现并全部修复

## [0.30.0] — 2026-05-04

### 用户入口统一
- FIX-049: README 安装链接修复——`peterwangze/governance` → `peterwangze/software-project-governance`，用户指引重写为"唯一命令 `/governance`"
- FIX-050: `/governance` 嵌入 Coordinator 激活——身份+铁律+路由表+产品代码边界+交互规则
- FIX-051: 用户视角全路径修复——Scenario 自动衔接 + Scenario F 任务入口 + 新鲜度放宽
- 7 个旧命令全部添加重定向头 → `/governance`

### Hook 架构修复
- FIX-044: GOV_COMMIT_MSG 桥接文件清理——post-commit 安全网
- FIX-045: COMMIT_EDITMSG 过期修复——GOV_BRIDGE_VALID 标志跳过不可靠的 Source 3
- FIX-046: Hook 自升级链路——pre-commit Step 0 自动同步 `.git/hooks/`
- FIX-047: 新建 commit-msg hook——消息依赖检查从 pre-commit 迁移（$1 可靠读取）
- FIX-048: integer expression 修复 + 冒号匹配修复（全角/半角）+ 3-hook 存活检测
- 3-hook 架构（pre-commit + commit-msg + post-commit）端到端验证通过

## [0.29.0] — 2026-05-04

### 系统级强制
- FIX-036: pre-commit hook Step 7 WARN→BLOCK — 产品代码无审查证据 → 拒绝 commit
- FIX-037: verify_workflow.py Check 21 — 审查覆盖率量化检查
- FIX-038: verify_workflow.py Check 22 — Profile 一致性自动校验
- FIX-043: 路由表补全 (16→18行) + Agent namespace 限制文档化降级方案

## [0.28.0] — 2026-05-04

### 0.28.0 — 用户入口精简

Bootstrap 模板按 Profile 三级差异化 + /governance 职责边界重定义 + 简单操作快速通道。

- **FIX-030**: Profile 差异化 bootstrap 模板——lightweight ~47行/standard ~212行/strict ~232行，governance-init.md Step 7 三级注入
- **FIX-033**: bootstrap 与 /governance 职责边界重定义——governance.md 新增分工章节
- **FIX-035**: 简单操作快速通道——M1.2 规则，治理记录修改跳过 Agent Team 激活

## [0.27.0] — 2026-05-03

### 0.27.0 — Agent Team 并行安全 + 基础设施修复

3 项 Hook/模板修复 + 并行调度双重防护（Coordinator 预检规则 + Worktree 物理隔离）。

- **FIX-028**: COMMIT_EDITMSG 过期窗口 5→60 秒——消除 Windows 版本 bump 的 --no-verify 依赖
- **FIX-026**: pre-commit is_product_code() 公共函数提取——统一 Step 7b/9 产品代码检测 + 7 单元测试
- **FIX-027**: governance-init.md 模板补全调度模板+行为协议引用
- **SYSGAP-043**: M7.6 并行调度预检规则——spawn 前 MUST 校验文件目标无重叠
- **SYSGAP-044**: Worktree 物理隔离——并行 Agent 文件目标重叠时使用 isolation: "worktree"

## [0.26.0] — 2026-05-03

### 0.26.0 — 审查跟踪层

Agent Team 协议强制执行 Phase 3。

- **SYSGAP-040~042**: 审查跟踪层——产品代码任务的后置审查状态追踪（plan-tracker 审查状态列 + verify Check 18/19 + hook Step 7b review BLOCK）

## [0.25.1] — 2026-05-03

### 0.25.1 — Agent Team 协议强制执行 Phase 2

- **SYSGAP-035~039**: Check 18/19——审查覆盖率检测 + Agent 激活检测

## [0.25.0] — 2026-05-03

### 0.25.0 — Agent Team 协议强制执行 Phase 1

- **SYSGAP-030~034**: 路由 1:N + hook BLOCK——Developer→CodeReviewer 强制分离 + pre-commit Step 7b review BLOCK

## [0.24.0] — 2026-05-03

### 0.24.0 — 目标一致性 + 用户影响系统强制

三层强制体系：每次 commit 产品代码时 MUST 论证变更如何服务于项目目标 + 回答用户影响三问。缺失 → pre-commit hook BLOCK。

- **SYSGAP-021**: project_goal 字段存储（governance-init.md 模板）
- **SYSGAP-022**: change-impact-checklist 增强——Step 3.5 目标一致性 + Step 3/5 强制格式
- **SYSGAP-023**: verify_workflow.py Check 16——目标一致性检查
- **SYSGAP-024**: verify_workflow.py Check 17——用户影响检查
- **SYSGAP-025**: pre-commit hook Step 10-12——目标+用户影响 BLOCK
- **SYSGAP-026**: governance-init.md 模板更新（project_goal 注入）
- **SYSGAP-027**: behavior-protocol.md M7.5 系统强制说明
- **SYSGAP-028**: audit-framework.md D1/D2 引用 Check 16/17
- **SYSGAP-029**: 回归测试——8 新用例（31 tests PASSED）

## [0.23.0] — 2026-05-02

### 0.23.0 — 测试体系 + CI

建立适配 skill/workflow 项目的测试体系：36 个单元测试 + e2e 测试 + GitHub Actions CI pipeline。

- **SYSGAP-015**: 本项目测试类型对应定义（stage-testing/SKILL.md）
- **SYSGAP-016**: verify_workflow.py 单元测试（23 个用例，6 个测试类）
- **SYSGAP-017**: e2e 测试项目（13 个用例，5 个测试类）
- **SYSGAP-018**: GitHub Actions CI pipeline（6 步自动检查）
- **SYSGAP-019**: 缺陷驱动测试积累（stage-maintenance/SKILL.md）
- **SYSGAP-020**: 版本一致性增强（CHANGELOG + plan-tracker 版本检查）

## [0.22.1] — 2026-05-02

### 0.22.1 — 检查器解析缺陷修复

修复 verify_workflow.py 3 个解析缺陷：sequential ID 检查器（plan-tracker 任务表解析修复，orphan 降为 INFO）、结构有效性检查（代码块过滤 + exclude→exclude_from_cleanup）、交叉引用检查（代码块/内联代码过滤）。Issue count: 1304→633 (-51%)。

- **FIX-021**: DEC-046 缺失占位补充
- **FIX-022**: plan-tracker 任务表头补"状态"列
- **FIX-023**: Sequential ID 检查修复
- **FIX-024**: 交叉引用/结构有效性检查修复

## [0.22.0] — 2026-05-02

### 0.22.0 — 检查体系升级

verify_workflow.py 从"文件存在性检查"升级为"语义一致性检查"——从 11 项扩展到 15 项自动检查。

- **SYSGAP-008**: 交叉引用检查——扫描 51 文件 1012 引用，检测悬空引用+废弃路径+循环引用
- **SYSGAP-009**: 顺序 ID 检查——DEC/EVD/RISK 编号连续 + 交叉引用完整性
- **SYSGAP-010**: 结构有效性检查——表格列数一致 + frontmatter 必需字段 + JSON 段完整
- **SYSGAP-011**: M5 语义检查增强——中英文内联提问模式检测 + 选项列表无 AskUserQuestion 检测
- **SYSGAP-012**: Commit scope verify——重复 task ID + "顺带"关键词 + bulk commit 检测
- **SYSGAP-013**: Governance Developer agent（阿治）创建
- **SYSGAP-014**: 影响分析路由——Agent 分发表新增 Analyst+Architect 行

## [0.21.0] — 2026-05-02

### 0.21.0 — 纪律防线

建立"不再继续犯错"的系统机制——产品代码边界定义 + Agent Team 强制激活 + 影响分析 checklist + commit 粒度规范。

- **SYSGAP-001**: 产品代码 vs 治理记录边界定义（SKILL.md + interaction-boundary.md）
- **SYSGAP-002**: M7.5 Agent Team 强制激活检查（behavior-protocol.md Step 2.5）
- **SYSGAP-003**: 变更影响分析 checklist 创建（change-impact-checklist.md）
- **SYSGAP-004**: M7.5 影响分析步骤嵌入（behavior-protocol.md Step 2.6）
- **SYSGAP-005**: Commit message 规范强化（behavior-protocol.md M7.4 Step 5）
- **SYSGAP-006**: Pre-commit scope WARN（infra/hooks/pre-commit Step 8）
- **SYSGAP-007**: Pre-commit Agent Team bypass WARN（infra/hooks/pre-commit Step 9）

## [0.20.0] — 2026-05-02

### 0.20.0 — 声明式清理机制

清理命令从硬编码冗余列表改为 canonical manifest + 结构 diff，每次目录结构调整后清理命令自动生效。

- **CLEANUP-001**: 创建 `core/manifest.json`——v0.19.0 完整目录结构声明（product + repo_only + exclude）
- **CLEANUP-002**: 新增 `infra/cleanup.py`——声明式 diff 清理脚本（支持 --dry-run/--json）
- **CLEANUP-002**: 重写 `commands/governance-cleanup.md`——基于 manifest.json 的声明式清理流程
- **CLEANUP-003**: `verify_workflow.py` 增强——新增 `check-manifest-consistency` 子命令 + REQUIRED_FILES 从 manifest.json 读取（124 entries）
- **CLEANUP-004**: Bootstrap 清理逻辑更新——CLAUDE.md + governance-init.md 改用 manifest-based cleanup
- **CLEANUP-005**: 文档纪律更新——manifest.md 简化 + VERSIONING.md 新增 manifest 更新规则

## [0.19.0] — 2026-05-02

### 0.19.0 — 代码仓对齐 Claude Code 官方插件约定

目录结构从 nested 改为 flat：Agent 和 SKILL 文件迁至 plugin root 平铺。

- **AUDIT-097**: 14 Agent 文件从 `skills/software-project-governance/agents/<组>/<角色>/prompt.md` 迁至 `agents/<name>.md`
- **AUDIT-098**: 25 真实 SKILL 从 `skills/software-project-governance/skills/<name>/` 迁至 `skills/<name>/`，删除 25 stub，git rm 清理旧目录
- 11+ 文件路径引用更新（verify_workflow.py 27 处、CLAUDE.md、governance-init/cleanup 等）
- 版本 bump 0.18.0→0.19.0（7 文件）

## [0.10.0] — 2026-05-01

### 0.10.0 正式发布——全 8 角色 Agent Team

0.10.0 补齐全部 8 个角色 Agent：
- AUDIT-063(P1): QA Agent——测试者(阿测),边界case+集成/性能/安全测试,CEO打脸教训
- AUDIT-064(P1): DevOps Agent——运维者(老管),Pipeline+环境一致性+监控告警,凌晨3点教训
- AUDIT-065(P1): Analyst Agent——分析者(阿析),需求澄清+竞品分析+PR/FAQ+OKR,87%教训
- AUDIT-066(P1): Release Agent——发布者(老发),发布检查+版本规划+回滚方案,周五下午教训
- AUDIT-067(P2): Maintenance Agent——维护者(老维),5-Why根因+同类扫查+预防机制,47次教训
- SKILL.md M2.2b 更新——全 8 角色 Agent Team 路由表

### 新增
- `agents/qa.md`, `agents/devops.md`, `agents/analyst.md`, `agents/release.md`, `agents/maintenance.md`
- 每个 Agent 含 persona(人物+教训)+座右铭+擅长+痛恨+职责+输入输出

## [0.9.0] — 2026-05-01

### 0.9.0 正式发布——Agent Team 基础架构

0.9.0 完成 Agent Team 最小可行架构——Coordinator + 3 核心角色 + 通信协议：
- AUDIT-053(P0): Coordinator Agent, AUDIT-054(P0): Developer Agent, AUDIT-055(P0): Reviewer Agent, AUDIT-056(P0): Architect Agent
- AUDIT-057(P0): Task-Gate 模型, AUDIT-058(P0): Agent 通信协议

## [0.8.0] — 2026-05-01

### 0.8.0 正式发布——统一治理命令（用户易用性基础设施）

0.8.0 完成 5 个任务（5 P0）：
- AUDIT-077(P0): 统一命令设计——6 场景决策树 + 场景 A/C/F 实现
- AUDIT-078(P0): 场景 B——半途接入（项目探索信号矩阵+阶段推断+差异化 onboarding）
- AUDIT-079(P0): 场景 D/E——会话恢复+异常恢复（诊断+修复）
- AUDIT-080(P1): Snapshot 格式升级（新增 session_id/current_gate/permission_mode/incomplete/user_preferences 字段）
- AUDIT-081(P1): 旧 5 命令统一路由（governance-update 标记 DEPRECATED）

### 新增
- `commands/software-project-governance.md`——统一入口，一个命令覆盖全部 6 场景
- Snapshot 格式 7 个新字段支撑会话恢复

### 变更
- governance-init/status/verify 添加统一入口路由说明
- governance-update 标记为 DEPRECATED
- SKILL.md M3 引用统一命令替代 governance-init
- SKILL.md M4.2 snapshot 格式升级

## [0.7.3] — 2026-04-30

### 修复

- **FIX-018: M7.4 结构修复——review 移到 commit 之前 + summary 嵌入 AskUserQuestion**。M5 under-use 复发 7 次后的深度根因：独立 summary 与 AskUserQuestion 形成结构性竞争——summary 总是赢（更简单、不需暂停、LLM 训练数据默认模式）。5 层文本规则修复（FIX-013/015/016/017 + AUDIT-053 C1）全部失效。修复：(A) summary 嵌入 AskUserQuestion 内部——禁止审查前输出独立 summary；(B) 审查移到 commit 之前——commit 是审查通过的奖励，不是跳过审查的触发器。M7.4 新顺序: evidence→verify→audit→AskUserQuestion 审查→commit→continue。M8 自检 + 失败模式 11 根因同步更新。

## [0.7.2] — 2026-04-30

### 修复

- **AUDIT-053: 全规则一致性审计修复——32 项矛盾/死规则/漂移闭环（20/32 已修复）**
  - **P0 严重矛盾（8/8）**：C1 M7.2 停止规则加例外 / C2 review 区分 / C3 Gate 独立使用例外 / C4 commit 触发点替换 / C5 方向确认限定 / C6 maximum-autonomy 加 P0 审查 / C7 Gate 评估区分 / C8 session end 边界
  - **P1 重要矛盾（5/7）**：S1 阶段重叠 profile 约束 / S2 关键决策列表同步 / S3 M7.4 步骤数修正 / S5 Step2 profile-aware / S6 interaction-boundary 同步
  - **P2 引用/漂移/M5（7/17）**：V1 agent-team-architecture 版本 banner / AQ1 确认行模式自适应 / R1 TOOLS.md 路径修正 / R2 Replacement Boundary 路径 / R3 孤儿引用补全 / S6 M5.2 同步声明
  - 剩余 12 项 P2（R4 Gate AUTO/ASK 标注、D1-D7 死规则标注、DR1-DR3 非关键列表漂移、AQ2 on-demand Gate 状态）归入 0.10.0
- **pre-commit hook Step 6 升级**：平台原生入口文件 直接修改检测从 WARNING → BLOCKING——BOOTSTRAP DISCIPLINE 违反（第 5+ 次）后升级为阻断级强制力
- 版本 bump 0.7.1→0.7.2

## [0.7.1] — 2026-04-30

### 修复

- **FIX-015: M5 AskUserQuestion 绕过根因修复——6 缺口系统性闭环**。此前 FIX-013 修复了 M5 触发覆盖但未解决子工作流层面的源头污染——agent 读到 `询问用户："当前项目目标是什么？"` 这样的内联指令会直接照做。
  - **GAP-1 (P0)**: `development/sub-workflow.md:27` — 清除 `询问用户` 内联指令，替换为 AskUserQuestion 工具调用指令
  - **GAP-2 (P0)**: `SKILL.md` 新增 M2.3 M5 交互信号——所有子工作流的 `需用户确认/输入/判断` 标注 MUST 通过 AskUserQuestion 执行
  - **GAP-3 (P1)**: 轻量 profile bootstrap 模板补 M5 提问规则——此前轻量用户完全没有 AskUserQuestion 指令
  - **GAP-4 (P1)**: `stage-gates.md` 新增原则 #10——Gate 确认 MUST 绑定 AskUserQuestion
  - **GAP-5 (P1)**: `verify_workflow.py` 新增 Check 10——M5 反模式静态检测（`询问用户` 污染模式 + bootstrap 覆盖 + interaction-boundary 绑定）
  - **GAP-6 (P2)**: SKILL.md M8.1 表格从 9→10 checks，覆盖 M5 外部验证
- `development/sub-workflow.md` + `release/sub-workflow.md` — 降级行为中的 `告知用户` 标注为单向通知（非提问），与 M5.1 禁令边界明确

## [0.7.0] — 2026-04-29

### 0.7.0 正式发布——外部验证 + 企业实践 + 交互覆盖闭环

0.7.0 完成 12 个任务（3 P0 + 4 P1 + 5 P2）：
- AUDIT-003(P0): E2E 外部验证——e2e-test-project 全链路走通
- FIX-013(P1): M5 AskUserQuestion 交互覆盖审计——3 缺口修复
- FIX-014(P0): 任务级防护——跨任务 evidence 链 + 用户插入先入账
- AUDIT-034(P2): 蓝军单 agent 结构化协议
- AUDIT-036(P2): 现代发布实践——金丝雀/feature flag/kill switch
- AUDIT-038(P2): 子工作流目标锚定自包含化 + 降级行为
- AUDIT-004/006/023(P1): governance-init/命令/可用性端到端验证
- MAINT-013/014(P1): 数据边界说明 + Agent 入口差异文档
- MAINT-023(P1): Gemini/国内 agent CLI 最小验证路径
- AUDIT-003 闭环(P0): E2E 验证完成

### 新增
- data-boundary.md + agent-entry-differences.md 参考文档
- prepare-commit-msg hook（Windows git bash 桥接）

---

## [0.6.15] — 2026-04-29

### 新增

- **AUDIT-034 蓝军单agent结构化协议**：tech-review-checklist 蓝军章节升级——视角切换三序列（框架切换/角色扮演/场景推演）+ 标准蓝军输出格式（攻击向量/影响评估/缓解/残余风险/建议增强）
- **AUDIT-036 现代发布实践**：release 子工作流新增发布策略选择（5 种策略含选型规则）+ Feature Flag 管理 + Kill Switch 验证（触发条件/可执行验证/负责人）
- **AUDIT-038 目标锚定自包含化**：development + release 子工作流锚定节升级——含具体文件路径和检查目标 + 降级行为定义（.governance/ 不存在时告知用户风险但不阻塞执行）

## [0.6.14] — 2026-04-29

### 新增

- **任务级防护（pre-commit Step 4.5）**：跨任务证据链——切换到新 task 时自动检测前序 task 是否有 evidence。未补齐 → M7.4 DEBT 警告。消灭任务间盲区。
- **干活前检查升级**（governance-init 模板）：从"三件事"升级为"五件事"——新增任务入账检查（用户临时插入也需先入账）+ 跨任务检查（先补齐上任务证据再开新任务）

## [0.6.13] — 2026-04-29

### 新增

- **E2E 防护网**：verify-e2e.sh（23 项 shell 检查）+ verify_workflow.py e2e-check 子命令（19 项 Python 检查）。e2e-test-project/ 固化为仓库永久验收基准。

## [0.6.12] — 2026-04-29

### 修复

- **M5 AskUserQuestion 交互覆盖审计**：修复 3 个缺口——SKILL.md M5.2 新增 risk escalation/audit finding 触发点；interaction-boundary.md 类型 C 新增风险评估/审计发现/阶段推进，强制 AskUserQuestion 格式；bootstrap Step 3 升级为 AskUserQuestion 选项。
- **post-commit hook M7.4 违规标记强化**：evidence 缺失时输出带框 M7.4 VIOLATION 警告——"DO NOT start another task until evidence is logged"。

---

## [0.6.11] — 2026-04-29

### 修复

- **版本规划纪律强化**：plan-tracker + VERSIONING.md 新增 8 条版本规划纪律——版本号分配规则（已预留不可占用/计划外用 PATCH/bump 前检查路线图/PATCH 事后追加）+ 版本内容一致性规则（内容匹配路线图/范围变更记录 DEC/90%完成率/实时更新）。含 0.7.0 被占用的实际违规案例。
- **agent-failure-modes 失败模式 9**：无版本管理环境下的治理盲区。非 git 用户降级到 session 级约束。

---

## [0.6.10] — 2026-04-29

### 新增

- **系统级约束架构**：设计假设从"agent 会遵守规则"翻转为"agent 一定不会自觉遵守，必须用系统级约束强制"。pre-commit hook（阻断型——commit 前验证 task ID + plan-tracker 存在，不通过则 BLOCK commit）+ post-commit hook（报告型——commit 后检查 evidence + check-governance）。双重屏障：pre-commit 阻断违规 commit，post-commit 报告 governance 状态。
- **governance-init Step 8 重写**：安装双 hook（pre-commit + post-commit），定义双重屏障设计
- **bootstrap Hook 存活检测升级**：从只检查 post-commit 升级为双 hook 检查

### 变更

- **设计哲学转变**：所有现有 MUST 规则按"系统可强制执行 vs agent 自执行"重新分类。pre-commit hook 是第一个 BLOCKING 级别的系统约束。CI check-governance --fail-on-issues 是第二个。未来所有新规则 MUST 优先设计系统级强制执行方案。

---

## [0.6.9] — 2026-04-29

### 修复

- **bootstrap 变更纪律**：governance-init.md 和 平台原生入口文件 新增 Step 1.5——MUST NOT 直接修改 平台原生入口文件 添加新行为，MUST 先改 governance-init.md 注入模板（canonical source），通过版本 bump + /plugin update + bootstrap 自升级到达用户
- **Tier 审计补齐**：EVD-123——用户反馈驱动密集修复轮次审计（D1/D3/D4）。审计发现 2 项治理违规：所有 FIX 任务 Gate 标记错误（G8→G11 修正）+ 全部先执行后入账（违反 M7.5）

---

## [0.6.8] — 2026-04-29

### 修复

- **bootstrap 自升级**：版本变化检测不再只是提示用户运行命令——agent 检测到 bootstrap 落后时**自动替换 平台原生入口文件 的 bootstrap 段为最新模板**。用户 `/plugin update` → 下次会话 → 自动完成，零用户行动。governance-update 命令降级为手动回退选项。

---

## [0.6.7] — 2026-04-29

### 新增

- **governance-update 命令**：老用户升级路径的核心——`/plugin update` 获取新版本后运行此命令，将 平台原生入口文件 的 bootstrap 段更新到最新。**不触碰 .governance/ 数据**——只替换 bootstrap 模板段，保留用户的项目配置和治理记录。bootstrap 版本变化检测自动提示用户运行此命令。

---

## [0.6.6] — 2026-04-28

### 新增

- **Bootstrap 版本变化自动检测**：每次会话开始自动对比 plan-tracker `工作流版本` 与当前安装版本。用户更新插件后首次会话自动输出——版本跨度 + CHANGELOG 摘要 + 需手动采纳项清单（hook/模板/配置字段）+ 自动生效项清单。**用户不需要记住任何命令。**
- **plan-tracker 新增 `工作流版本` 字段**：记录最后一次"治理更新"时的版本，作为版本变化检测的基线

### 用户视角

此前 `/governance-status` 需要用户主动调用——用户更新后不会主动跑。现在 bootstrap 在每次会话自动检测版本变化，用户更新插件 → 下次打开会话 → 自动看到"从 0.6.0 升级到 0.6.6，新增 X/Y/Z，需手动采纳 hook 安装"。

---

## [0.6.5] — 2026-04-28

### 新增

- **用户视角强制原则**（`references/user-perspective-principle.md`）：所有规划/设计/开发/测试 MUST 回答三个问题——用户怎么获得变更？用户怎么知道变更存在？用户体验真的变了吗？含 6 项检查清单 + 5 种反模式定义 + 用户旅程描述要求。集成到 SKILL.md M2.1 + 平台原生入口文件 干活前检查 + governance-init 注入模板。
- **governance-status 版本新鲜度检查**（Step 3.5）：每次展示状态时自动检查插件是否最新，OUTDATED 时输出版本差距 + commits behind + 更新指引。已安装用户不再被遗忘。
- **近期变更用户可达性审计**：4 个版本逐版审查——发现 3/4 对已安装用户有断点。0.6.1 治理开关是唯一对已安装用户立即可用的功能。

---

## [0.6.4] — 2026-04-28

### 新增

- **post-commit governance hook**：每次 `git commit` 后自动触发——提取 commit message 中的 task ID → 检查 plan-tracker 中是否存在 → 检查 evidence-log 中是否有证据 → 输出 check-governance 摘要。消除会话中间"commit 之间"的治理盲区。Hook 不阻塞 commit——只报告，不拒绝。
- **RISK-024**：记录"端点强制模型 vs 流式执行行为的结构性不匹配"风险——5-Why 根因分析

### 修复

- **governance-init Step 8**：新项目初始化时自动安装 post-commit hook
- **平台原生入口文件 bootstrap**：新增 Hook 存活检测——hook 缺失时 MUST 提醒用户重装

---

## [0.6.3] — 2026-04-28

### 变更

- **VERSIONING.md 重写**：砍掉 alpha/beta/rc 预发布标签——三层 Major.Minor.Patch 本身提供细粒度。Patch 就是最小增量单位。每轮有意义的变更 MUST bump PATCH，不攒着等 Minor。新增"用户如何更新"章节（3 种更新方式 + freshness 检查）。
- **check-plugin-freshness 子命令**：`python skills/software-project-governance/infra/verify_workflow.py check-plugin-freshness` 对比 installed_plugins.json 的 gitCommitSha 与源仓库 HEAD，输出 installed/source/status/action。

---

## [0.6.2] — 2026-04-28

### 新增

- **版本规划机制**：plan-tracker 新增 `## 版本规划` 节——版本路线图（显式 task ID 映射）+ 版本里程碑（M1~M5）+ V-Gate（6 项检查）+ 版本规划纪律
- **需求跟踪矩阵**：REQ-001~008 需求→任务→验证全链路可追溯
- **变更控制流程**：临时任务的 4 步 triage（优先级判定→版本适配→冲突检查→范围更新）
- **3 个缺失模板**：`pr-faq-template.md`（Amazon PR/FAQ）、`okr-template.md`（Google OKR + ByteDance 基线）、`six-pager-template.md`（Amazon 6-Pager/Narrative）

### 修复

- **AUDIT-051 审计闭环**：16 条企业实践 31% 敷衍率——5 条只有文档无模板无强制力。建立纪律：每条实践 MUST 有模板 + 检查项 + 自动化验证，缺一不可。

---

## [0.6.1] — 2026-04-28

### 新增

- **触发模式 × 操作权限双维度融合**：trigger_mode（何时激活治理）和 permission_mode（能做什么不打断）正交组合——maximum-autonomy（除关键决策外全自动，含 git push/本地命令/文件删除）/ default-confirm（4 类危险操作必须确认）
- **治理开关**：用户会话中随时说"切换到最高权限模式"等 → 立即切换 + 更新 plan-tracker
- **governance-init Q4**：交互式选择操作权限模式
- **interaction-boundary.md 重写**：新增操作权限模式章节，定义 4 类危险操作边界

---

## [0.6.0] — 2026-04-28

### 新增

- **交互式初始化**：`governance-init` 在参数缺失时通过 AskUserQuestion 引导用户选择 profile/触发模式/项目类型，不再静默应用默认配置
- **Bootstrap 模板全面升级**：注入模板从 4 行英文 stub 升级为完整中文 bootstrap（Step 0 触发模式 + Step 1 跨会话恢复 + Step 2 三项交叉验证 + Step 3 优先级 + 干活前检查 + 提问规则 + 关键决策分类 + 收工快照生成），按 profile 差异化注入（lightweight 精简版 / standard+strict 完整版）
- **旧版 Bootstrap 升级检测**：检测到旧版英文 stub 时主动提示用户升级，不再静默跳过
- **跨会话状态恢复**：M4.1/M4.2 升级——session-snapshot.md 格式定义 + 会话加载/生成协议。平台原生入口文件 收工前检查自动生成快照
- **触发模式实现**：平台原生入口文件 Bootstrap Step 0 —— always-on/on-demand/silent-track 三种行为差异可检测
- **Profile 差异化行为落地**：governance-init 按 profile 生成不同 plan-tracker 结构（lightweight 7 Gates+6列 / standard 11 Gates+20列 / strict 11 Gates+量化评分列+强制证据注释）
- **CI 集成 check-governance**：`.github/workflows/governance-check.yml` —— push/PR 自动运行 check-governance + verify_workflow.py，`--fail-on-issues` 阻断不完整治理记录合并
- **Bar Raiser 否决权**：技术评审结论新增"否决（Block）"选项——独立评审人可单方面阻止 Gate 通过。单 agent 最低标准：切换分析框架 + 挑战 3 个核心假设
- **字节 A/B 测试纳入 release**：release 子工作流新增"影响评估"活动（A/B 测试分析 + 核心指标对比 + 5 种无数据替代标准）；release-checklist 新增"数据验证计划"步骤

### 变更

- **子工作流全 11 阶段统一深度标准**：research/selection/infrastructure/ci-cd/release/operations/maintenance 7 个子工作流从骨架升级为深度指南（AI 风险表 + 企业实践映射列 + Gate 自动判定列 + 企业实践溯源节）
- **company-practices-summary 可执行化**：23 行纯导航 → ~200 行自包含可执行规则摘要（每条实践有"什么时候用"+ 可执行检查项 + 适用 profile 三级标注）
- **Evidence 范围编号展开**：parse_evidence_task_ids() 支持 AUDIT-015~020 → 6 独立 ID 展开
- **Layer 0-D 防漂移机制完成**：跨会话记忆 + 触发模式 + Profile 差异化全部落地

### 修复

- **governance-init bootstrap 不对称**：本仓库 平台原生入口文件 与注入模板严重不对称（~80 行 vs 4 行）→ 同步为完整中文模板，按 profile 差异化注入

---

## [0.5.1] — 2026-04-27

### 新增

- **Gate 自动判定覆盖率 45%→100%**：G6-G11 各新增 3-4 条启发式检查项，`auto_judge_gate()` 从覆盖 5/11 扩展到 11/11 Gate。新增 6 个 helper 函数（`_check_completed_ratio`/`_check_evidence_mentions`/`_check_risk_has_closed`/`_check_plan_has_priority`/`_check_version_consistency_heuristic`）。gate-check 全部 11 个 Gate 返回 ≥3 条检查项，0 误报 FAIL，NEEDS_HUMAN 仅保留给真正无法自动化的检查

### 修复

- **产品核心能力不完整闭环**：gate-check 对 G6-G11 返回空结果（0 checks）→ 用户运行 `gate-check G11` 得到空结论。现在 44 条启发式规则覆盖全部 11 个 Gate

---

## [0.5.0] — 2026-04-26

### 新增

- **M7.3 风险 escalation 强制执行**：打开状态的风险在截止日期过后 MUST 升级或关闭。`check_risk_escalation()` 检测过期未处理的风险——解决"风险 escalation deadline 过了但什么都没发生"的系统性漏洞（与 M7.4/M7.5 同类模式）
- **M7.3 任务 deadline 强制执行**：未完成任务在"计划完成"日期过后 MUST 完成、重排或显式降级。`check_task_deadline()` 检测过期未处理的任务
- **Check 8：Risk Escalation Deadline**：check-governance 第 8 项检查——检测 risk-log 中"打开"状态且 escalation 截止日期已过的风险
- **Check 9：Task Deadline Enforcement**：check-governance 第 9 项检查——检测 plan-tracker 中非"已完成/已终止"状态且"计划完成"日期已过的任务
- **M8 自检升级**：新增 M7.3 风险 escalation 和任务 deadline 检查项
- **M8.1 表格升级**：从 7 checks 扩展到 9 checks

### 修复

- **Deadline 盲区闭环**：风险 escalation 和任务 deadline 两个字段被定义但从未被自动检测——check-governance 的 Check 2（风险 staleness）只检测 >7 天未更新，不检测 escalation deadline。Check 8/9 补上了这个检测盲区

---

## [0.4.0] — 2026-04-26

### 新增

- **M7.5 任务启动协议**：M7.4 的镜像——修改文件前 MUST 验证任务已在 plan-tracker 中存在。不在则先入账（创建 task ID + 填必填字段）再动手。解决"agent 可绕过 plan-tracker 直接修改文件"的系统性跟踪漏洞
- **M7.4 步骤 4 commit 格式强化**：commit message MUST 包含 task ID 前缀（如 "AUDIT-044: description"）——task ID 是代码变更与 plan-tracker 条目之间的链接，没有它 traceability 就断了
- **Check 7：Commit-Task Traceability**：check-governance 新增第 7 项检查——检测最近 20 个 commit message 是否包含 plan-tracker 中存在的 task ID，无引用→WARN。`check_commit_task_references()` 是 M7.5 步骤 4 的外部验证对应物
- **M8 自检升级**：新增 M7.5 检查项（pre-task protocol executed?）
- **M8.1 表格升级**：从 6 checks 扩展到 7 checks（新增 Check 7：Commit-task traceability）

### 修复

- **跟踪漏洞闭环**：AUDIT-043（M7.4 fix）在入账前就动手修改了 8 个文件——事后才补的 task 条目。M7.5 将这个教训固化为协议：先入账再动手。AUDIT-044 是第一个遵循 M7.5 的任务——task 条目先于任何代码修改被提交

---

## [0.3.0] — 2026-04-26

### 新增

- **M7.4 任务完成协议**：将 evidence → check-governance → audit → commit → continue 绑定为原子不可跳过序列。解决"规则存在但 agent 不执行"的系统性执行一致性问题——每项任务标记"已完成"后 MUST 按序执行 5 步
- **M8 自检升级**：新增 M7.4 检查项（任务完成协议是否执行？）
- **M8.1 表格升级**：从 5 checks 扩展到 6 checks（新增 Check 6：Tier 审计完整性）
- **audit-framework.md D1 触发条件具体化**：新增 governance-critical 文件清单——任何修改了这些文件的任务完成时 MUST 触发审计（不论任务优先级）

### 修复

- **执行一致性漏洞闭环**：AUDIT-040 完成时发现的 4 项 MUST 规则被跳过（审计未触发/未 commit/执行中断/内联提问）通过 M7.4 原子协议系统性修复

## [0.2.0] — 2026-04-26

### 新增

- **M3.1 DRI 规则**：直接责任人模型（Apple DRI + Amazon STO）——每任务 MUST 有唯一 DRI，多 owner=未分配，AI agent DRI 时 agent 有执行决策权/human 是 Escalation
- **M8.1 外部验证机制**：双重机制（agent 自检 + 脚本独立验证）——`check_protocol_compliance()` 独立检测 DRI 违规/条件通过未纠偏/证据格式缺失
- **M5.1~M5.4 AskUserQuestion 协议**：唯一合法提问通道 + 关键决策分类（6 类关键 + 6 类非关键）+ 禁止场景
- **M7.1~M7.3 执行连续性**：用户决策模式声明（stop for critical only / stop for all）、5 条禁止中断模式、实时闭环规则
- **Gate 自动判定**：`gate-check G<N>` 子命令——对 G1~G5 执行启发式自动判定（PASS/FAIL/NEEDS_HUMAN），支持 `--fail-on-blocked` 用于 CI 集成
- **证据质量自动检查**：`check_evidence_quality()` — 检测会话上下文引用/循环引用/空输出声明
- **协议合规自动检查**：`check_protocol_compliance()` — 独立检测 3 类协议违规（DRI/条件通过/证据格式）
- **审计框架**（`audit-framework.md`）：6 维度 × 3 类别审计体系，融入 Gate 原则 #7 / SKILL.md M2.1 / lifecycle.md 治理规则 #5
- **Agent 失败模式文档**（`agent-failure-modes.md`）：8 种失败模式 + 检测方法 + 用户应急动作
- **Tier 审计检查点**（stage-gates.md 原则 #9）：分层推进模型的 Tier 完成后必须执行审计
- **平台原生入口文件 自包含升级**：关键决策分类内嵌（不依赖 SKILL.md 加载状态）+ 故障排除章节

### 变更

- **DRI 模型落地**：plan-tracker Owner 列改为单值 DRI，新增 Escalation 列（20 列模板）
- **交互边界规则升级**：新增 DRI 决策权限定义章节
- **stage-gates.md**：新增原则 #6（Closure Follow-Through）、原则 #7（审计检查点）、原则 #8（DRI 检查）、原则 #9（Tier 审计检查点）
- **Tier 1 双源合并**：skills/ 成为运行时唯一事实源，workflows/rules/ 和 workflows/stages/ 已删除
- **审计触发条件扩展**：SKILL.md M2.1 + audit-framework.md D1/D3/D4 新增"Tier 完成"触发条件

### 修复

- parse_gate_detail regex 从 `###` 改为 `##`（pre-existing bug——gate 和 gate-check 子命令均无法找到 Gate 定义）
- 证据质量升级：5 条"会话上下文"引用替换为持久化文件路径，EVD-070 循环引修复
- 平台原生入口文件/SKILL.md 循环依赖解耦

---

## [0.1.0] — 2026-04-17

### 初始版本

- 三层承载模型（workflow 本体层 + agent 入口投影层 + 外部能力层）
- 11 阶段生命周期定义 + 11 Gate 检查
- 4 个治理记录模板（plan-tracker / evidence-log / decision-log / risk-log）
- verify_workflow.py 基础校验脚本
- Claude/Codex adapter 基础入口
- 4 家企业实践调研（Google/Amazon/华为/字节）
- 11 个子工作流骨架
- 5 个 stage skill（需求澄清/技术评审/Code Review/发布 checklist/回顾会议）
- 3 种项目 Profile（lightweight/standard/strict）
- 中途接入协议（onboarding）
- 交互边界规则
