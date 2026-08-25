# 变更日志

本文件记录 `software-project-governance` 的每个版本变更。

## [0.77.0] - 2026-08-25

### 0.77.0 - DSH 标准插件安装支持 + 事故防再发链同槽（FEAT-010 / FIX-271 / AUDIT-146 / FIX-274 / FIX-272 / FIX-273 / FIX-275 + F-02 入槽 FIX-276）（MINOR）

0.77.0 是 MINOR 发布，把 HEAD `0f9e5bb` 上 0.76.0 released（`v0.76.0` = 4f24e74）之后已合入的 **8 个 commit** 打包成发布候选——承载 MINOR 语义的两项主链：FEAT-010（DSH 标准插件安装支持——bundle 形态：根 package.json 增 dsh.bundle / dsh.skills 35 条 / files / keywords，新增 cordis.patch.yml 组合层与 presets/governance 随包 preset，README DSH 行改标准安装命令 + 备选本地路径，纯 md/config 零构建；随包生态接入 dsh 0.1.1-rc.2 plugin 子命令，满足「沉淀可被 coding agent 消费的项目治理 workflow」的分发可达性）与 FIX-274（SKILL.md「关键行为契约」段新增第 4 条行为契约——真实环境必防护（R1 三选一 / R4 逐条上报 / R5 措辞）+ DSH persona 第 5 条，M7.7 防再发规则升为 always-on 注入面）。事故防再发链六 commit 随行：AUDIT-146（FEAT-010 事故 RCA 报告入库）、FIX-271（R1-R5 防再发协议固化：M7.7 三选一/中继留痕/措辞禁令 + 调度红线捆绑包注入 + change-triage 第五步「执行副作用声明」机检）、FIX-272（bundle 同源防漂移守卫：@version-line 动态锚 + dsh.skills 清单双向机器校验 + Check 40）、FIX-273（side-effect 检测盲区加固：UNC/单反斜杠根正则 + normalized 双判定 + IGNORECASE + 9 边界测试）、FIX-275（pyc 打包卫生：files 否定模式，tarball 154 pyc/10.34MB → 0 pyc/5.72MB，-64%），以及 F-02 入槽（DEC-163，用户 M-0 裁决）：FIX-276（README 自动化能力分级声明补注——plugin-contract L114 对外宣示面闭合）。发布目标：把 FEAT-010 事故（RISK-045，2026-08-23 已关闭）的 RCA → 防再发固化 → always-on 注入面 → 守卫补全 → 检测加固 → 打包卫生完整闭环在同版本交付，并让插件进入 dsh 标准 plugin 生态。**不关闭 RISK-036/RISK-039**。版本投影 0.76.0 -> 0.77.0 全 PASS（15 projections 由 `release-projection --write` 确定性写入 + @bootstrap-version 标记面 9 行（commands/governance-init.md ×3 + e2e 镜像 ×3 + e2e CLAUDE.md + 根 AGENTS.md；根 CLAUDE.md gitignored 本地同步不入 commit，FIX-256 先例）+ `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。**Breaking changes：无**（全部为新增能力/检查/规则/打包卫生与增量文本；无既有接口删除、无既有 check 重命名、无默认行为破坏——FIX-271 四步既有输出字节不变）。

### Added

- **FEAT-010 DSH 标准插件安装支持（bundle 形态）**（EVD-FEAT-010，commit 3339d99，2026-08-23）：根 package.json 增 `dsh.bundle.patch` / `dsh.skills`（35 条：34 skill + 命令投影）/ `files` 白名单 / `keywords`；新增 `cordis.patch.yml` 组合层（挂载 agent-presets root 指向随包 `presets/governance/`，preset 内相对路径自包含）；README DSH 行改标准安装命令（`dsh plugin --profile <test> add ./repo`）+ 备选本地路径。契约实证：dsh 0.1.1-rc.2 plugin 子命令（dsh.bundle 声明 → dsh.profile.bundles 层栈自动并入）+ 官方 publish.md + make-dsh-plugin v3.0.0（bundle 包根=仓库根）。验收（R1/R5 隔离协议修订）= 隔离环境安装冒烟：DSH_HOME 重定向至临时目录（禁止触碰真实 ~/.dsh），`--dump-config` 层栈可见、roster 含 governance preset；自证 boot 双 PASS；真实 ~/.dsh 零操作双确认（时窗取证 + 源码反证）。复审链 R0 NEEDS_CHANGE → R1 NEEDS_CHANGE → R2 APPROVED_WITH_NOTES/0（REVIEW-FEAT-010-R2）；遗留登记：F2→FIX-272、F11→FIX-275、F12 P3。用户视角：用户获得标准 dsh plugin add 安装路径与随包 governance preset，无需手动 clone + launch.py。
- **FIX-276 README 自动化能力分级声明补注（F-02 入槽，DEC-163）**（EVD-FIX-276，commit 0f9e5bb，2026-08-25）：README.md 新增「自动化能力分级声明（plugin-contract.md L114）」节（L196-205，+10/-0）——A 级（Agent Protocol Automation）/ B 级（CLI-Enforced Automation）/ C 级（System Automation **未实现，roadmap**，plugin-contract L102 引用）；口径以 SKILL.md「自动化能力分级声明」节为唯一事实源逐条对齐，27 处「自动」表述逐处归属。R0 APPROVED_WITH_NOTES/0（P0=0/P1=0/P2=1/P3=2）。用户视角：README 读者（用户/评审/官方目录）获得准确分级——「自动」承诺可追溯至 A/B 级，C 级明确 roadmap 未实现。
- **AUDIT-146 FEAT-010 事故 RCA**（EVD-AUDIT-146，commit 2bb10ac）：RCA 报告 `docs/requirements/audit-146-feat010-dsh-config-loss-rca.md`（266 行）——事实链 + FEAT-010 交付物逐文件审计 + launch.py 源码审计 + dsh CLI 命令面分析 + 破坏面假设分级（H1a 可能·高 + 工具侧确认级排除）+ 流程缺陷分析（D1-D5）+ 防再发协议建议（R1-R5 草案）。R0 审查 APPROVED_WITH_NOTES/0（REVIEW-AUDIT-146-R0）。用户视角：事故根因与防再发设计公开可查。
- **FIX-274 M7.7 投影 always-on 注入面 + requires_r1 完成门控**（EVD-FIX-274，commit 4d13992）：M7.7 压缩契约（真实环境三选一 / 逐条留痕上报 / R5 措辞）投影进 SKILL.md「关键行为契约」第 4 条（canonical）+ DSH persona 第 5 条（agent.cordis.yml.template 与 presets/governance/agent.cordis.yml 同步）+ e2e 镜像；INJECTION_CONTRACT_ANCHORS 三面锚（27 锚/4 文件）；Check 39 `check_r1_completion_gate`（requires_r1=true 任务完成时须有 R1 留痕证据，WARN-first，收紧条件显式登记：连续 2 个零违规 0.77.x 版本后升 FAIL，升级时 MUST decision-log 入账）；「唯二例外」措辞统一（R1-N2）；DEC-159/160 入账；**DEC-161/162 预算提额**：persona 契约块 1536B→2560B、SKILL 契约段 2048B→2560B（用户裁定方案 A，保真优先；守卫测试更新）。DESIGN R0 APPROVED_WITH_NOTES/0 → CODE R0 NEEDS_CHANGE（P1-1 门控误报 / P1-2 SKILL 预算超顶）→ R1 返工（DEC-161/162；门控修复红→绿 10+2）→ CODE R1 APPROVED_WITH_NOTES/0。用户视角：任意宿主 agent 均受 M7.7 约束；requires_r1 任务缺 R1 留痕时 WARN 可见（0.77.x 观察窗口不阻断）。
- **FIX-272 bundle 同源防漂移守卫**（EVD-FIX-272，commit e3e45c0）：INJECTION_CONTRACT_ANCHORS 增补 @version-line 动态锚（28 anchors，authority=SKILL.md frontmatter，fail-closed，FIX-250 前科防再发）+ `check_dsh_skills_manifest` 双向校验（package.json ↔ 磁盘，35/35）+ CLI `check-dsh-skills-manifest` + 引擎 Check 40（product-gate 同 Check 33 归组）+ agent.cordis.yml 头部注释同步。TDD 9 新例红→绿；pytest 1923 passed/28 存量失败（stash 基线证实无关）。R0 APPROVED_WITH_NOTES/0（P2×2 登记遗留 + P3×6 讨论级）。
- **FIX-273 side-effect 检测盲区加固**（EVD-FIX-273，commit 7d7a966）：`_OUTSIDE_REPO_FILE_RE` 增补 UNC/单反斜杠根分支 + normalized 双 match 参与 outside 判定 + `_REAL_ENV_TEXT_RE` 补 IGNORECASE + 否定语境盲区 docstring 披露（行为不改）+ 9 边界测试（`../` 逃逸、`%USERPROFILE%` 文件目标、UNC、`--side-effects` CLI 端到端；TDD 4红→61绿）。pytest 全量 28 存量失败同基线零新失败。R0 APPROVED_WITH_NOTES/0（P0=0/P1=0/P2=0/P3=3）。
- **FIX-275 pyc 打包卫生**（EVD-FIX-275，commit 618ab13）：package.json `files` 新增 `!**/__pycache__/` + `!**/*.pyc` 否定模式（npm-packlist 10.0.3 源码级实证：files 存在时根 .npmignore/.gitignore 置 null——白名单目录内 ignore 永不生效；否定模式经 `!!` 双反转成明确排除规则）。RED→GREEN 实测：397 entries/154 pyc/10.34MB → 243 entries/0 pyc/5.72MB（**-64% 体积**）；零误删零误增；payload 完整性零破坏（cordis.patch.yml/presets/skills/adapters/commands/agents/README/LICENSE 全在包内）；.npmignore 路线实证否定不引入。R0 APPROVED_WITH_NOTES/0（P0=0/P1=0/P2=0/P3×4：顺序敏感性/双模式重叠/无注释载体/无自动化回归守卫登记候选）。用户视角：最终用户不再收到含本机编译产物（154 个 pyc/9.86MiB + 构建机路径信息）的污染 tarball。
- **FIX-271 R1-R5 防再发协议固化**（EVD-FIX-271，commit d396097）：R1/R4/R5 → behavior-protocol.md M7.7（真实环境三选一强制 / 中继机制逐条上报 / 验收措辞禁令）+ R3 → agent-dispatch-template.md 破坏性红线捆绑包注入段 + R2 → change-triage 第五步「执行副作用声明」（`analyze_side_effects`，触及用户真实环境 → 自动附加 R1 审查条件）+ TDD 测试。TDD 12 新例红→绿（52/52）；四步键序字节不变；27 存量失败经 stash 基线证实无关。CODE R0 APPROVED_WITH_NOTES/0 + DESIGN R0 NEEDS_CHANGE（F-01 R4 执行链矛盾）→ R1 返工（中继机制 + incidents 例外条款 + 捆绑包契约 + F-06/F-07）→ DESIGN R1 APPROVED_WITH_NOTES/0（REVIEW-FIX-271-R1）。用户视角：涉及用户真实环境的派发全程强制隔离/备份/授权三选一 + 逐条留痕。
- **版本声明与 e2e fixture 指针从 0.76.0 推进到 0.77.0**（M-set：SKILL.md frontmatter 0.77.0 权威源 + `release-projection --write` 确定性写入 15 投影——core/manifest、4×plugin.json（.claude/.codex/.zcode/.chrys）、marketplace、package.json、4 hooks @version、dsh persona / AGENTS.md.template、e2e SKILL byte_copy 镜像、e2e plan-tracker + @bootstrap-version 标记面 9 行（governance-init ×3 + e2e 镜像 ×3 + e2e CLAUDE.md + 根 AGENTS.md；根 CLAUDE.md gitignored 本地同步）+ `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉（仅版本字面量 +6/-6 零逻辑，checks/version.py 强制校验面））。
- `project/CHANGELOG.md` 新增 0.77.0 条目；release docs 三件套创建（feature-flags / release-checklist / rollback-plan）；0.77.0 版本规划文档入库（`docs/release/version-plan-0.77.0.md`，REL-070 第一段经 Release R0→R2 + Design R0→R1 双审查 APPROVED_WITH_NOTES/0 终态，DEC-163 入账）。

### Changed

- SKILL.md「关键行为契约」段与 DSH persona 契约块新增 M7.7 第 4/5 条（真实环境必防护）——行为契约注入面从 3 条增至 4 条（SKILL）与 5 条（persona）；预算按 DEC-161/162 提额为 2560B（机器守卫 `test_persona_contract_block_stays_within_budget` + `test_skill_contract_section_stays_within_budget`）。
- change-triage 由四步扩为五步（第五步「执行副作用声明」增量——既有四步输出字节不变，向后兼容）。
- README 对外宣示面补齐能力分级声明（与 SKILL.md/governance.md 口径逐条一致；「过程管理全自动」等承诺归 A 级并显式注明「不是系统后台触发」；C 级 roadmap 未实现）。

### Fixed

- **真实环境操作防护从第四层按需协议升为每会话 always-on 行为契约**（FIX-271 + FIX-274）：R1 从「triage 落 record 后 Coordinator 自觉」变为机器完成门控（Check 39），D1-D5 注入层+消费层双侧闭合（RISK-045 关闭依据链，2026-08-23 已关闭）。
- **bundle 同源漂移**（FIX-272）：preset persona 版本行与 dsh.skills 清单双向机器校验（Check 40 + 独立子命令）——FIX-250 类版本行漂移防再发。
- **side-effect 检测盲区**（FIX-273）：UNC/单反斜杠根路径逃逸与 IGNORECASE 漏检加固（FIX-271 CODE R0 P2-1/P2-2/P3-2/P3-3 收口）。
- **pyc 泄漏进发布包**（FIX-275）：package 打包 154 个 `__pycache__/*.pyc`（10.34MB，含构建机路径信息）→ 0 pyc（-64%）；FEAT-010 R1 F11 闭合。
- **README 分级宣示与 L114 禁令缝隙**（FIX-276）：消除「全自动」笼统宣示与 C 级未实现并置的误导缝隙（review-FIX-269-CODE-R0 F-02 闭合）。

### Validation

- REL-070（0.77.0 MINOR 候选打包，2026-08-25；candidate-only——transition/tag/push 待用户授权后另行执行，DEC-143 基线；release_authorized=false）。
- FEAT-010：隔离冒烟 + 自证 boot 双 PASS；真实 ~/.dsh 零操作双确认；复审链 R0→R1→R2 APPROVED_WITH_NOTES/0（REVIEW-FEAT-010-R2）。
- FIX-271：TDD 12 新例红→绿（52/52）；四步键序字节不变；CODE R0 + DESIGN R0→R1 双审 APPROVED_WITH_NOTES/0×2（REVIEW-FIX-271-R0/R1）。
- AUDIT-146：R0 APPROVED_WITH_NOTES/0（REVIEW-AUDIT-146-R0 机器行）。
- FIX-274：DESIGN R0 APPROVED_WITH_NOTES/0 + CODE R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0（门控修复红→绿 10+2；双预算守卫 15；DEC-161/162）；Check 39 真实数据零误报（35 records/1 r1 未完成合法跳过）。
- FIX-272：TDD 9 新例红→绿；pytest 1923 passed/28 存量失败（stash 基线证实无关）；R0 APPROVED_WITH_NOTES/0。
- FIX-273：TDD 4红→61绿；pytest 全量 28 存量失败同基线零新失败；R0 APPROVED_WITH_NOTES/0。
- FIX-275：RED→GREEN 实测（243 entries/0 pyc/5.72MB）；Reviewer 独立重验（pyc 精确计数 154/10,340,875B 与差分 397-243=154 三方自洽）；verify/cross-refs/manifest/version 全 PASS；R0 APPROVED_WITH_NOTES/0。
- FIX-276：verify_workflow.py 全量 PASSED（exit 0）+ check-cross-references 68 files/649 refs 无悬空 PASS + check-version-consistency 13 files PASS + check-manifest-consistency 565/608 PASS；R0 APPROVED_WITH_NOTES/0（REVIEW-FIX-276-R0 机器行 + RECO-FIX-276）。
- 门禁（0.77.0 candidate，2026-08-25）：`check-version-consistency` PASS（13 文件声明；1 advisory WARN——宿主 plan-tracker 仍 0.76.0，Coordinator 打包后 bump）；`check-projection-sync --fail-on-issues` PASS（15 投影）；`check-manifest-consistency` PASS（canonical 568/actual 608）；`check-cross-references --fail-on-issues` PASS（68 文件/649 refs 零悬空）；`verify` 无参 PASSED（唯一 WARN = plan-tracker 0.76.0）；`check-injection-contract` PASS（4 文件/28 anchors——FIX-272 @version-line 锚在打包期间实际捕获 preset 版本行滞后并已同步）；`check-dsh-skills-manifest` PASS（35/35）；pytest 全量 28 failed/1930 passed/215 subtests（与 HEAD 基线 28 failed/1932 passed 一致——零打包引入失败；28 = 窗口内既有基线：pre_commit_review_evidence 24 SUBFAILED + test_all_manifest_dirs_covered（FEAT-010 `presets/` 未入 cleanup PLUGIN_SCOPE_DIRS）+ loop-claims/ragged-row 3 例）；`check-release --version 0.77.0 --require-changelog --lineage-mode candidate` 8 issues 按先例全分类（3 = 未提交态产物 + 1 = archive trigger gap 过渡态（EVD-894 先例）+ 1 = governance health 106（既有宿主 posture）+ 2 = AUDIT-146 RCA 文档 ragged row 窗口内既有基线（loop-claims FAIL + unit tests 同源），核心静态门禁全 PASS（version/fact-source/lineage candidate/gate-sequence Check 37/one-dot-zero/loop-fuse/changelog）+ verify/e2e 执行门禁 PASS）；`release-ledger --no-remote` 未提交候选过渡态（NATIVE_CANDIDATE，commit 后重跑——REL-067 先例）。

### Boundaries

- 0.77.0 **RISK-036/RISK-039 remain open**（2026-09-30；各自独立关闭标准未满足）；不关闭、不重开任何已关闭风险（RISK-045 已于 2026-08-23 用户授权关闭，0.77.0 不重开）。
- 不声明 official approval、zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success、1.0.0 production-ready；不关闭 RISK-036/RISK-039。
- **Breaking changes：无**。全部为新增能力/检查/规则/打包卫生与增量文本；既有 CLI 默认行为零变化（FIX-271 四步键序字节不变）；Check 39/40 为新增编号（39<40），既有 check 无重命名/删除。
- MINOR bump 依据（VERSIONING.md）：① FEAT-010 新安装能力（L12 类别：新能力/分发面）；② FIX-274 SKILL.md MUST 规则新增（L37）。新 check 39/40 与新 CLI 按 L34（verify_workflow.py 新增检查项 → PATCH）如实陈述为 PATCH 面增量，不作为判级依据。
- **预算提额披露（DEC-161/162 检查值）**：persona 契约块预算 **2560B**（原 1536B，DEC-161 用户裁定方案 A——M7.7 第 5 条行为契约注入所需；M7.4 契约块预算不变）；SKILL.md「关键行为契约」段预算 **2560B**（原 2048B，DEC-162）；守卫测试 `test_persona_contract_block_stays_within_budget` + `test_skill_contract_section_stays_within_budget`。
- **RISK-044 快照（quick-scan 出槽附注）**：`--summary-only` 墙钟实测 31-32s（超设计 §3.1 <15s 门禁——DEC-149 已接受并修订验收信号为「单次 <60s 且每会话仅一次」，31-32s 满足）；**quick-scan 秒级子集出槽 0.77.0 → 0.78.x+ 候选**（本版不含——M-1 经 decision-log + CHANGELOG 附注登记；RISK-044 保持 open，2026-08-28 复核由 Coordinator 执行：维持接受 / quick-scan 前移）。
- **迁移说明（RISK-D5——DSH preset 时滞）**：DSH 平台升级路径为 `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`（DSH 无 `/plugin update`）；persona/bootstrap 模板的 0.77.0 版本行与 5 条契约在 `--sync` 重写 preset 后生效，未 sync 前旧 preset 仍携带旧版本行——不得宣称未 sync 安装的会话级 M7.7 效果；升级同步后对被治理项目自然生效（看护 check 作用于宿主 `.governance/` 读时数据，无需被治理项目单独改造）。

## [0.76.0] - 2026-08-23

### 0.76.0 - 看护模式七项 + /governance 性能修复（REQ-145.1~145.7 / FIX-263~270 + FIX-270 性能）（MINOR）

0.76.0 是 MINOR 发布，把 HEAD `db1078f` 上 0.75.0 released（`v0.75.0` = 543550c）之后已合入的 **15 个 commit** 打包成发布候选——承载 MINOR 语义的主链：AUDIT-145 看护缺口七项修复（FIX-263 设计 + FIX-264~269 实现：会话 bootstrap 自动健康摘要 `check-governance --summary-only`、Check 35 快照新鲜度、Check 36 风险缓解闭环、Check 37 Gate-发布互锁、Check 38 CI 实跑证据、能力分级声明）与 `/governance` 性能修复（FIX-270：status 秒级快路径 + 宿主 check-governance -91% 提速 + mixed-root 去噪）；八个随行 commit（FIX-255/256/258、AUDIT-144、FIX-260/261/262、DOC-002）——其中 FIX-260/261/262 为 REQ-107/108 消费方（审查结论机器持久化 + 完成推荐机器验证回路），FIX-255/256/258 为发布后债务/测试加固，AUDIT-144 为只读诊断报告，DOC-002 为项目质量原则投影。发布目标：AUDIT-145 诊断的「记录+门禁有效但运行时看护缺位」——会话纪律、风险缓解闭环、Gate-发布互锁、CI 实跑证据、bootstrap 健康摘要从「人发现问题」转向「机器看护」，并对 `/governance` 分钟级状态展示与宿主 check-governance 噪音/耗时做性能修复。**不关闭 RISK-036/RISK-039**。版本投影 0.75.0 -> 0.76.0 全 PASS（15 projections 由 `release-projection --write` 确定性写入 + `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。**Breaking changes：无**（全部为新增检查/子命令/文档声明与内部修复，无既有接口破坏；CLI 均为增量参数）。

### Added

- **FIX-263/264 会话 bootstrap 自动健康摘要（REQ-145.1+145.7）**（EVD-FIX-264，commit 66fa210，2026-08-23）：根因 = AUDIT-145 D1——check-governance 仅手动触发，会话无自动健康信号。修复：`verify_workflow.py` 新增 `--summary-only` 子命令（复用全量引擎捕获输出 + `_aggregate_check_summary` + `--level lightweight|standard|strict` 详略分档 + fail-safe 降级）；会话协议 M4.1 新增一步 + 入口 SKILL.md 注入健康摘要段（A3 方案：不进 persona——契约块 1535/1536 字节已满）；阈值对齐 DEC-149（>60s 软超时取消，source/e2e 镜像逐字一致）。**披露（RISK-044，2026-08-22 登记，已接受/DEC-149）**：`--summary-only` 墙钟实测 31-32s，未达设计 §3.1 `<15s` 门禁（复用同引擎=全量引擎耗时，设计「秒级」前提经真机实测不成立）；DEC-149 已接受并修订验收信号为「单次运行 <60s 且每会话仅一次」（31-32s 满足），quick-scan 秒级子集列为 0.77+ 候选（不改变 0.76.0 语义）；RISK-044 保持 open（已接受/DEC-149），deadline 2026-08-28 复核。用户视角：每个新会话 bootstrap 后自动输出 `Governance: {N} issues` 汇总 + 首个 FAIL/WARN 项，无 issue 时 `[PASS]`。验证：test_summary_only 15 用例红→绿；全量 1752 passed+237 subtests（唯一失败 = 既有 resolve_entry 时间敏感 flaky 00:00-02:00 窗口恒败，HEAD 同败）；审查链 R0/R1 APPROVED_WITH_NOTES/0。设计文档 `docs/requirements/audit-145-watchdog-design-0.76.0.md` + `audit-145-watchdog-gap-0.76.0.md` 随实现入库（FIX-263 交付物）。
- **FIX-265 Check 36 风险缓解闭环（REQ-145.3）**（EVD-FIX-265，commit cba247b）：根因 = AUDIT-145 D2——risk-log「写缓解即完成」无闭环断言。修复：`checks/risk_domain.py` 扩展（`is_risk_status_closed` + F11 PriorityReport 四桶状态映射重建 + R1-R5 判定：引用任务未闭环→WARN、截止过/高危→FAIL、跨实体引用→R3 WARN 不升级、无引用无豁免→R4 内容级披露、已关闭/豁免/ragged→skip）；`task_priority ✅` 为规则权威（DEC-151）；解析异常 fail-safe WARN 不 raise。用户视角：风险缓解引用未完成任务时 check-governance 输出警告（内容维度，补充 Check 2/8 时间维度盲区）。24 用例红→绿；全量 1792 passed+237 subtests 零既有断言变化；三项目只读实测 tv FAIL(R2)/router WARN(R3×3)/dogfood WARN(R3×29)；R0 APPROVED_WITH_NOTES/0；遗留 P2×4+P3×7 登记 0.76.x。
- **FIX-266 Check 37 发布前 Gate 互锁（REQ-145.4）**（EVD-FIX-266，commit 15051c1）：根因 = AUDIT-145 D4——发布绕过 pending Gate 无机器断言。修复：`checks/gate_domain.py` 新域（行序推导识别发布 Gate，不硬编码编号——standard 11/lightweight 7 兼容；G-s1 发布<passed 日期或 passed 无日期→FAIL、G-s2 前置 pending 保守 FAIL、G-s3 git 不可见 tag fail-safe WARN；passed-on-entry 视为非 pending；多 tag 只判最高 semver；反引号状态归一化；永不 raise）+ `check_release_readiness` 内嵌调用 + Check 37 块 + `cmd_check_release` BR-4 自动 released 模式；历史豁免 candidate→FAIL/released→WARN 披露（4 分支双态测试）。用户视角：`check-release` 自动横查前置 Gate，绕过发布被 FAIL。41 用例红→绿；全量 1864 passed+237 subtests 0 failed；tv/router 候选 FAIL + 已发布 WARN + BR-4 端到端 [PASS]；R0/R1 APPROVED_WITH_NOTES/0；遗留 P2-3+P3×9 登记 0.76.x。
- **FIX-267 Check 38 CI 实跑证据（REQ-145.5）**（EVD-FIX-267，commit 4e3d08a）：根因 = AUDIT-145 D2/D4——声称 CI 已建/已跑无载体验证。修复：`checks/ci_domain.py` 新域（声明解析 CI word-boundary + 否定词归类 + 规则文本排除；C1 声称已建无载体→FAIL、C2 载体无 remote→WARN 未真跑（fail-safe）、C3 声称已跑无法证实（含无载体 DEC-156）→WARN、C4 无声明无载体→PASS；多路径探针 深走查+GitLab/Jenkins+嵌套 git 排除；`_is_pathlike` 守卫永不 raise）。用户视角：plan-tracker 声称 CI 已建但无 workflow → FAIL；有 workflow 无 remote/运行记录 → WARN「未真跑」。R0 NEEDS_CHANGE（P0-1 TypeError）→ 修复（真实 un-mocked 守卫/run→C3 WARN/词边界等）→ R1 APPROVED_WITH_NOTES/0；RED 5 failed→GREEN 31 passed；全量 1895 passed+237 subtests 0 failed；tv WARN(C2)/router PASS(C4)/host PASS。
- **FIX-268 Check 35 快照新鲜度（REQ-145.2）**（EVD-FIX-268，commit 3a819d0）：根因 = AUDIT-145 D3——会话快照过期无机器保证（三项目实证全部过期）。修复：`checks/snapshot_domain.py` 新域（S1a 缺失/不可解析→WARN、S1b 落后→WARN、S1c AND 双阈值 7 天且 10 commit→FAIL、S1d 无快照→no-verdict；无日历生效日豁免；git 事实源 HOST_PROJECT_ROOT + ls-files 跟踪判定 + mtime 次级基准 FAIL 不可达；adoption-edge 封顶；永不 raise）；DEC-152 裁定 4 项。用户视角：快照比最近治理 commit 落后超阈值时 check-governance 警告/FAIL。31 用例红→绿；全量 1823 passed+237 subtests 0 failed；tv WARN(S1b 4d/72lag)/router PASS/dogfood PASS；R0/R1 APPROVED_WITH_NOTES/0；遗留 P2×2+P3×3 登记 0.76.x。
- **FIX-269 自动化能力分级声明（REQ-145.6）**（EVD-FIX-269，commit db1078f）：根因 = plugin-contract.md L114 禁令——禁止笼统「自动」同时指向 A 级与 C 级能力。修复：SKILL.md 新增「自动化能力分级声明」小节（A 级 Agent Protocol Automation / B 级 CLI-Enforced Automation / C 级 System Automation 未实现——L102 MCP/headless runner 仅协议样例；0.76.0 `--summary-only` 会话级 auto-run 非 C 级 daemon；当前治理自动级别 = A+B，C 级 roadmap）+ L38 逐条标注 + commands/governance.md L64 B 级标注 + 设计原则节分级声明小节（指回 SKILL.md 单一事实源，无定义双写）+ e2e SKILL.md 镜像同步。用户视角：对外宣示不再把 C 级未实现说成已实现。R0 APPROVED_WITH_NOTES/0 零 P0/P1；全量 verify PASSED + projection/crossrefs(646→648 零悬空)/manifest(557/600)/version(13 文件 0.75.0 未 bump) 全 PASS；check-governance 113==113 零新增；遗留 F-02（README 宣示分级补注）+ F-03（e2e commands 投影决策）登记 0.76.x 候选（DEC-157）。
- **FIX-270 /governance 性能修复**（EVD-FIX-270，commit 1479fcc）：根因（用户实测 2026-08-23，tv 项目）＝ Scenario F 要求 LLM 全量读命令文档 639 行 + 4 治理文件（110KB+）+ 渲染 28 字段快照 = 分钟级；宿主 check-governance 28.6s（插件产品自检 22 项每会话必跑）；mixed-root 令宿主噪音化 182 issue。修复：(A) 新增 `status` 命令——复用扩展既有 status（补全 Scenario F 数据/活跃风险/最近活动/插件新鲜度/下一步线索/统计对齐 + Gate 显示循环 bug 修复 + `--json` + skip_evidence_log 零整读 evidence-log 机制）；(B) check-governance 宿主提速——`_PLUGIN_PRODUCT_CHECK_IDS` 22 项按检查事实源根切分（无编号黑名单），宿主默认跳过产品自检 + `[SKIP]` 如实报告，`--product-gates` 显式开启，dogfood 保留全部；宿主 full 25.49s→2.40s（-91%），输出 0 条插件路径条目；(C) mixed-root 修复（Check 28s schema/facts 根拆分、Check 25 git 事实源→HOST_PROJECT_ROOT、Check 28c 双段化+plugin-scope+[INFO] 报告）。用户视角：宿主 `/governance` 状态秒级（tv 实测 status 0.47s / check-governance full 2.42s），输出零插件路径噪音。15 用例红→绿；全量 1768 passed+237 subtests 0 failed；R0/R1 APPROVED_WITH_NOTES/0（F1/F2/F3 逐项核验）；遗留 P2×3+P3×4+N1-N3 登记 0.76.x。
- **FIX-260 审查结论机器持久化 + 复审义务（REQ-107 消费方）**（EVD-FIX-260，commit 8922c6e）：`checks/review_domain.py` +246 纯新增 + Check 30c `check_review_machine_provenance`（V7 机器源标记/V8 next_round 义务字段断言，WARN-only + 生效日豁免 REQ107_MACHINE_PROVENANCE_DATE=2026-08-22，WARN 不进 all_issues）；behavior-protocol M7.4 step 4.6 机器持久化 MUST；DSH persona 契约第 4 行（1535B≤1536B 预算测试断言）。用户视角：审查结论经 review-record CLI 机器入账（本仓首个机器标记审查记录 REVIEW-FIX-260-R0）。TDD 13→14 用例；全量 1696+213 subtests 0 failed；R0 APPROVED_WITH_NOTES/0。
- **FIX-261 提交钩子审查证据正则对齐机器行格式**（EVD-FIX-261，commit 3fd5adf）：pre-commit/commit-msg `has_approved_review_evidence` 双分支改写——legacy 行尾 APPROVED 族逐字保留（零收窄）+ 机器 11 列格式仅接受 APPROVED_WITH_NOTES + 尾列 unresolved_blockers=0（注入/大小写/NEEDS_CHANGE/BLOCKED 全部 MISS）；两钩子字节一致 + `test_hook_copies_stay_identical` 钉住。用户视角：机器行格式的审查结论能被提交钩子识别为通过终态。11 用例红→绿；全量 1707 passed 0 failed；R0 APPROVED_WITH_NOTES/0。
- **FIX-262 完成推荐机器验证回路（REQ-108 消费方）**（EVD-FIX-262，commit cc79dd0）：`task-priority-analysis --evidence-task` 旗标机器写入 RECO-{task} 10 列推荐快照行（fail-closed 坏 ID exit 2 零写入；无旗标行为字节一致）；Check 34 `check_completion_recommendation`（S1 完成行缺快照关联→FAIL、~145 条 legacy 豁免；S2 快照优先级节缺 ID 引用→WARN 渐进 DEC-147；S3 悬空引用→FAIL）；behavior-protocol step 6a 机器路径优先 + 快照引用 MUST。用户视角：任务完成的推荐快照被机器验证、写证据（首个 RECO-FIX-262 行）。TDD 18 新用例；全量 1725+237 0 failed；R0 APPROVED_WITH_NOTES/0；DEC-147 入账。
- 版本声明与 e2e fixture 指针从 0.75.0 推进到 0.76.0（M-set：4×plugin.json（.claude/.codex/.zcode/.chrys）、marketplace、package.json——6 个版本元数据目标、source/e2e SKILL frontmatter、manifest、fixture plan-tracker、四个 source hooks、DSH persona 模板 v0.76.0 与 AGENTS.md.template L3 `@bootstrap-version: 0.76.0`——15 projections 由 `release-projection --write` 确定性写入，written=15；`verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉；`@bootstrap-version` 标记面 9 行——commands/governance-init.md ×3 + e2e 镜像 ×3 + e2e CLAUDE.md + 根 AGENTS.md（根 CLAUDE.md gitignored 本地同步不入 commit），FIX-256 先例）。
- `project/CHANGELOG.md` 新增 0.76.0 条目；release docs 三件套创建（feature-flags / release-checklist / rollback-plan）。

### Changed

- `check-governance --summary-only`：只输出汇总 + 首个 FAIL/WARN 项（`--level` 分档），零回归既有全量输出路径；会话级 bootstrap 自动运行（每会话一次，>60s 软超时取消）。
- `/governance` Scenario F 状态展示与 `commands/governance-status.md` 改为渲染 `status` 命令输出——全量读治理文件降为按需；宿主 check-governance 默认跳过 22 项插件产品自检（`--product-gates` 显式开启；dogfood 保留全部）。
- SKILL.md / commands/governance.md 逐条标注自动化能力级别（A 级协议/B 级 CLI/C 级未实现声明，引用 plugin-contract L114；当前治理自动级别 = A+B，C 级为 roadmap）。

### Fixed

- **风险「写缓解即完成」无机器断言**（Check 36）：缓解措施引用非 completed 任务 → WARN/FAIL，关闭 AUDIT-145 D2 时间维度盲区。
- **会话快照过期无机器保证**（Check 35）：session_date 落后超阈值 → 渐进 WARN/FAIL（AUDIT-145 D3）。
- **发布绕过 pending Gate**（Check 37 内嵌 check-release）：release 就绪检查自动横查前置 Gate（AUDIT-145 D4）。
- **CI 声称与载体不符**（Check 38）：无 workflow 声称已建→FAIL、无 remote/运行记录→WARN（AUDIT-145 D4）。
- **/governance 分钟级状态展示**（FIX-270）：status 命令 <1s（tv 实测 0.47s）；宿主 check-governance 25.49s→2.40s（-91%）。
- **mixed-root 噪音**（FIX-270 C）：Check 28s/25/28c 以宿主事实源定位，宿主输出零插件路径条目。
- **bootstrap 不诊断**（REQ-145.1）：resolve_entry.py 不 import verify，健康摘要走 M4.1 流程步骤（A3 不进 persona）。
- **commit-msg 拒绝机器行格式审查结论**（FIX-261）：双分支正则对齐，legacy 行尾格式字节保持。
- 随行债务/加固（FIX-255/256/258）：test_change_triage 版本字面量对齐（FIX-248 同型复发）、@bootstrap-version 标记面 0.75.0 对齐 + EntryBootstrapTemplate 断言动态化（零版本字面量）+ F-1 单源派生（0.76.0 复发通道关闭）、FIX-254 债务包（bae9d5f/FIX-258 落地：访问预算 10,000 + 菱形测试 + 纯重构拆分），AUDIT-144 依赖盲区只读诊断（热指针行方案论证）。

### Validation

- REL-069（0.76.0 MINOR 候选打包，2026-08-23；candidate-only，transition 需用户授权后另行执行）。
- FIX-264：test_summary_only 15 用例红→绿；全量 1752 passed+237 subtests；R0/R1 APPROVED_WITH_NOTES/0。
- FIX-265：24 用例红→绿；全量 1792 passed+237 subtests；三项目实测 tv FAIL/router WARN/dogfood WARN；R0 APPROVED_WITH_NOTES/0。
- FIX-266：41 用例红→绿；全量 1864 passed+237 subtests 0 failed；tv/router 双项目实测 + BR-4 端到端；R0/R1 APPROVED_WITH_NOTES/0。
- FIX-267：31 用例红→绿（RED 5 failed → GREEN）；全量 1895 passed+237 subtests 0 failed；tv WARN/router PASS/host PASS；R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0。
- FIX-268：31 用例红→绿；全量 1823 passed+237 subtests 0 failed；tv WARN/router PASS/dogfood PASS；R0/R1 APPROVED_WITH_NOTES/0。
- FIX-269：全量 verify PASSED + projection/crossrefs/manifest/version 全 PASS；check-governance 113==113 零新增；R0 APPROVED_WITH_NOTES/0。
- FIX-270：15 用例红→绿；全量 1768 passed+237 subtests 0 failed；tv 独立复核 status 0.47s / check-governance full 2.42s / 0 条插件路径；R0/R1 APPROVED_WITH_NOTES/0。
- FIX-260/261/262：全量 1696+213 / 1707+0 / 1725+237 0 failed；机器审查记录 REVIEW-FIX-260/261/262-R0 + RECO-FIX-262；R0 APPROVED_WITH_NOTES/0。
- 门禁（0.76.0 candidate，2026-08-23）：`check-version-consistency` PASS（13 文件声明；1 advisory WARN——宿主 plan-tracker 仍 0.75.0，Coordinator 打包后 bump）；`check-projection-sync --fail-on-issues` PASS（15 投影）；`release-projection --write` written=15 exit=0（再次 check PASS）；`check-manifest-consistency` PASS；`release-ledger --version 0.76.0 --no-remote` NATIVE_CANDIDATE（未提交候选过渡态，commit 后重跑）；`check-release --version 0.76.0 --require-changelog --lineage-mode candidate` 核心静态门禁 PASS（既有基线 FAIL 按 REL-067/068 先例如实分类披露，见 release checklist 0.76.0）。

### Boundaries

- 0.76.0 **RISK-036/RISK-039 remain open**。RISK-036（official marketplace operations）与 RISK-039（ArchGuard external validation）各自独立关闭标准未满足；本版本不重开任何已关闭风险。
- 不声明 official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success、1.0.0 production-ready；不关闭 RISK-036/RISK-039。
- **Breaking changes：无**。全部变更为新增检查/子命令/流程步骤/文档声明（增量文本与增量参数），既有 CLI 默认行为零变化；Check 35~38 为新增 check 编号（35<36<37<38 链），既有 check 无重命名/删除。
- MINOR bump 来自看护能力新增（5 项机器看护 check/子命令 + status 快路径 + 能力分级声明 + 审查机器持久化/推荐机器验证回路），不引入 breaking runtime API。
- **迁移说明（RISK-D5——DSH preset 时滞）**：DSH 平台升级路径为 `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`（DSH 无 `/plugin update`）；persona/bootstrap 模板的 0.76.0 版本行在 `--sync` 重写 preset 后生效，未 sync 前旧 preset 仍携带旧版本行——**升级同步后（git pull + adapters/dsh/launch.py --sync）对被治理项目自然生效**（看护 check 作用于宿主 `.governance/` 读时数据，无需被治理项目单独改造）。

## [0.75.0] - 2026-08-21

### 0.75.0 - 关键行为规则注入面 + 空推荐降级（REQ-112/REQ-110，DEC-143 前置放大器双落地）（MINOR）

0.75.0 是 MINOR 发布，把 HEAD `d90c167` 上 0.74.0 released（`v0.74.0` = 3a64d54）之后已合入的 9 个 commit 打包成发布候选——两个承载 MINOR 语义的主 commit：FIX-253（REQ-112 关键行为规则注入面，DEC-144 方案 A）与 FIX-254（REQ-110 空推荐降级）；六个 0.74.0 后观察项/债务 commit（FIX-247/FIX-248/FIX-249/FIX-250/FIX-251/FIX-252）与一个审计 commit（AUDIT-143）随行。发布目标：AUDIT-143 定位的 loop engineering 三层断裂中，注入层根因（关键行为规则只存在于 DSH persona/SKILL 注入链不携带的第四层文件，agent 行为约束靠自觉）与数据层根因（全部任务被阻塞时推荐恒空，用户得不到任何下一步建议）双修复——FIX-253 把三条关键行为规则（复审必达/完成必推荐/选项必带依据）注入确定性注入面（DSH persona + 入口 SKILL.md 双点），并以 version-projections transformed_text 锚定 persona 版本行与 AGENTS.md.template bootstrap 版本行（L33 漂移类问题机器防再发）；FIX-254 为任务推荐链增加空推荐降级——当无未阻塞任务时输出「解锁链推荐」（Unblock pick + 结构化空原因 + 最近可行动作），推荐交互不再恒空退化。**不关闭 RISK-036/RISK-039**：官方市场操作与 ArchGuard 外部宿主验证各自独立关闭标准未满足。版本投影 0.74.0 -> 0.75.0 全 PASS——本次为 FIX-253 新增的 2 个 transformed_text 投影（dsh-persona-version / dsh-agents-bootstrap-version）首次参与发版：`release-projection --write` 写入 15 投影（written=15，exit=0），persona L33（v0.75.0）与 AGENTS.md.template L3（@bootstrap-version: 0.75.0）由投影机制确定性推进（M-set：15 projections + `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。

### Added

- **FIX-253 关键行为规则注入面（REQ-112，DEC-144 方案 A：双点最小注入 + 版本投影锚定 + 锚点检查）**（EVD-FIX-253，2026-08-21）：根因 = AUDIT-143 定位注入层断裂——T1-T4 复审触发器与 M7.4 step 6 推荐规则位于第四层按需加载文件，DSH persona/SKILL 注入链不携带，行为约束依赖 agent 自觉；persona L33 版本行曾漂移 v0.73.0（FIX-250 逃逸者）。修复（9 文件 +213/-6）：(1) DSH persona 契约块 4 行 1404B≤1.5KB（R1 复审必达 / R2 完成必推荐 / R3 选项必带依据——三条与铁律同级的压缩契约），agent.cordis.yml.template 会话注入即生效；(2) 入口 SKILL.md「关键行为契约」段 1623B≤2KB（canonical 投影定义处）+ e2e fixture byte_copy 同步重生成（20884B 相等）；(3) AGENTS.md.template 单行指针（thin-pointer 纪律）；(4) version-projections.json +2 transformed_text 投影（dsh-persona-version / dsh-agents-bootstrap-version，pattern 唯一命中 persona L33 与 AGENTS L3）+ manifest projection_ids 同步（15=15 集合相等）——发版时版本行随投影机制确定性推进，L33 类漂移机器防再发；(5) verify_workflow.py INJECTION_CONTRACT_ANCHORS 12 锚点 + check_injection_contract() + Check 33 接入 check-governance + 独立子命令（fail-closed）；(6) test_dsh_adapter 版本断言动态化（从 SKILL frontmatter 权威源读取，消灭 FIX-250 姊妹手动同步通道）；(7) behavior-protocol.md canonical 注记 + step 6b/6c 改写（统一 DEC-143「自动推荐 + 用户确认」基线，废止「自动执行推荐项」默认分支）。验证：S1-S8 全 PASS（S4 projection-sync 15 投影 exit 0、S6 Check 33 PASS、S8 18/18）；全量回归 699+18+107+12+40 全绿。审查链：Design R0 APPROVED_WITH_NOTES/0（4 WARNING 返工核实）+ DEC-144 用户确认（方案 A）+ Code R0 APPROVED_WITH_NOTES/0（5 P3 非阻塞）。
- **FIX-254 空推荐降级——解锁链推荐 + 结构化空原因（REQ-110）**（EVD-FIX-254，2026-08-21）：根因 = AUDIT-143 定位数据层断裂——live unblocked=0 时 recommended_next 恒空，任务完成后的推荐交互退化为机械枚举或直接结束（用户反馈 2a/2b 直接根因）。修复（4 文件 +647/-2）：task_priority.py 新增 UnblockRecommendation 与 _walk_blocker_roots（unknown_dependency / non_executable_status / cycle 三类根因，菱形去重 + 环终止 + 深度上限 200）+ _build_empty_recommendation_fallback（价值排序 = 下游解锁数降序 → 优先级 → 版本 → ID 严格全序）；compute 单点接线（仅空推荐触发，正常路径零行为变化）；format_report all_blocked 分支渲染 Unblock pick / 空原因 / 最近可行动作；loop_exit_bridge.py 传播 recommended_fallback / empty_reason 两键（含 parse-error 路径）。19 个新测试红→绿（红相 Ran 119 failures=3 errors=15 → 绿相 119 OK）；全量回归 159/159 + test_verify_workflow 全绿。live 验证：task-priority-analysis unblocked=0 输出非空——Unblock pick: FIX-205 [P0]（解锁 7 下游）+ 结构化空原因。审查链：R0 APPROVED_WITH_NOTES/unresolved_blockers=0（F-1 P1 当轮返工修复）。
- 版本声明与 e2e fixture 指针从 0.74.0 推进到 0.75.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、fixture plan-tracker、四个 source hooks、DSH persona L33 与 AGENTS.md.template L3——15 projections 由 `release-projection --write` 确定性写入，written=15；以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 6 版本钉）。
- `project/CHANGELOG.md` 新增 0.75.0 条目；release docs 三件套创建。

### Fixed

0.74.0 released 之后、0.75.0 打包之前合入的六个观察项/债务 commit（均已具备各自 evidence 与审查链，随 0.75.0 一并进入用户安装面）：

- **FIX-247 FIX-237/238 遗留观察项处置**（EVD-FIX-247，commit c9739d0）：change-triage 证据 append 失败时 best-effort 回滚 + 明确报错；同 task_id 重 triage 拒绝（fail-closed）；bootstrap.sh timeout 分支退出码折叠与 stdlib 兜底诊断。用户视角：triage 记录不再出现半写状态，入口引导失败原因可区分。
- **FIX-248 change-triage CLI 测试 fixture 版本对齐**（EVD-FIX-248，commit 9ce4e19，测试-only）：fixture roadmap 与 CLI 调用从 0.73.0 对齐 0.74.0，unknown-dep fail-closed 测试恢复真实覆盖。用户视角：无可见行为变化（测试强度提升）。
- **FIX-249 FIX-247 R0 §6 五 P3 债务包**（EVD-FIX-249，commit 113a959，测试加固）：bootstrap.sh stdlib 兜底分支补「resolve_entry exited non-zero」诊断、区分 timeout(1) 自身失败（125/126/127）与真实非零、malformed triage 记录 immutable 边界（拒绝而非静默覆盖）。用户视角：引导失败诊断更精确、triage 记录防覆盖。
- **FIX-250 候选债务包**（EVD-FIX-250，commit 856301e）：`@bootstrap-version` 模板标记 0.73.0→0.74.0 全投影面同步（REL-067 投影缺口）；parse_version_chain 表后误追加加固（triage 机器记录 version_chain 不再混入路线图后续表行）；archive dry-run「校验: FAILED」误导输出修复为 N/A；`.gitattributes` 补 `*.json text eol=lf`。用户视角：后续版本发布时模板标记不再陈旧、triage 依赖/版本分析准确。
- **FIX-251 parse_task_dependencies 无表头窗口表可见性**（EVD-FIX-251，commit 0dc1786）：plan-tracker「最近完成（本会话提交窗口）」子节的无表头任务表此前永不进入解析（新任务依赖这些任务时被 unknown-dep fail-closed 拒收）。修复后 live 统计 124→131（+7 全可见）。用户视角：新任务引用最近完成窗口任务不再被误拒。
- **FIX-252 观察项债务包**（EVD-FIX-252，commit 439f8b4）：`_coerce_text` str 路径/文本歧义修复（像路径但不存在 → 明确 ValueError 而非静默 total 0 或 IsADirectoryError；空串/多行守卫）；web-console 测试 stdout 泄漏修复；fixture 对齐与组合顺序锁定。用户视角：CLI 输入误用从静默错误结果变为明确报错。

### Validation

- REL-068（0.75.0 MINOR 候选打包，2026-08-21；candidate-only，transition 需用户授权后另行执行）。
- FIX-253：S1-S8 全 PASS（S1 grep NEEDS_CHANGE×1、S2 task-priority-analysis×2+1、S3 依赖状态理由×1+1、S4 check-projection-sync 15 投影 PASS、S5 check-version-consistency PASS、S6 Check 33 PASS + 子命令 exit=0、S7 fixture byte-equal、S8 18/18）；verify/crossref/manifest 全 PASS；全量回归 699+18+107+12+40 全绿；Design R0 + DEC-144 + Code R0 审查链关闭。
- FIX-254：19 新测试红→绿（119 OK）；全量回归 159/159（task_priority + loop_exit_bridge + change_triage）+ test_verify_workflow 全绿；live CLI 输出 Unblock pick 非空 + all_blocked 结构化空原因；Code R0 APPROVED_WITH_NOTES/0。
- 随行六 commit（FIX-247~252）：各自 evidence 记录完整（EVD-FIX-247~252）+ 审查链关闭（FIX-247 R0 APPROVED/0、FIX-248 R0 APPROVED/0、FIX-249 R0→R2 APPROVED_WITH_NOTES/0、FIX-250 R0 APPROVED_WITH_NOTES/0、FIX-251 R0 APPROVED_WITH_NOTES/0、FIX-252 R0 NEEDS_CHANGE→R1 APPROVED_WITH_NOTES/0）；合并回归 test_task_priority + test_loop_exit_bridge + test_change_triage 159/159 + test_verify_workflow 全绿 + test_archive 119 全绿。
- 门禁（0.75.0 candidate，2026-08-21）：`check-version-consistency` PASS（1 advisory WARN——宿主 plan-tracker 仍 0.74.0，Coordinator 打包后 bump）；`check-projection-sync --fail-on-issues` PASS（15 投影，含 2 新投影达成态——dsh-persona-version / dsh-agents-bootstrap-version 首次发版实战）；`release-projection --write` written=15 exit=0（新投影首次实战记录）；`check-manifest-consistency` PASS（554 canonical / 580 actual）；`check-injection-contract` PASS（3 文件 12 锚点）；unittest test_release_ledger 39 OK + test_dsh_adapter 18 OK（版本断言动态化自动适配 0.75.0）+ test_verify_workflow 699 OK（254.9s）；`release-ledger --no-remote` 报告未提交候选过渡态 issue（git_commit_adding_path 派生要求文件已提交——commit 后重跑，同 REL-067 先例）；`check-release --version 0.75.0 --require-changelog --lineage-mode candidate` 记录 6 项 issue 按先例分类：3 = release docs 未跟踪（未提交态产物，commit 后消解）、1 = archive trigger gap 过渡态（既有基线，0 可迁 task）、1 = governance health 既有基线（宿主治理记录 217 issues，非本 diff 引入）、1 = unit tests 180s 环境超时（直跑 699 OK）——核心静态门禁（version consistency / projection sync / cross references / changelog / release lineage candidate / loop runtime claim 578/578 / one-dot-zero blockers）全 PASS。

### Boundaries

- 0.75.0 **RISK-036/RISK-039 remain open**。RISK-036（official marketplace operations）与 RISK-039（ArchGuard external validation）各自独立关闭标准未满足；本版本不重开任何已关闭风险。
- 不声明 official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success、1.0.0 production-ready；不关闭 RISK-036/RISK-039。
- MINOR bump 来自注入面行为改进 + 空推荐降级两项新能力（新投影机制落地 + 推荐链降级路径），不引入 breaking changes（纯行为改进：注入为增量文本块、推荐仅在原空路径上增加降级输出，正常路径零行为变化）。
- **迁移说明（RISK-D5——DSH preset 时滞）**：DSH 平台升级路径为 `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`（DSH 无 `/plugin update`）；persona/bootstrap 模板的 0.75.0 版本行与契约块在 `--sync` 重写 preset 后生效，未 sync 前旧 preset 仍携带旧版本行——升级后首次会话完成其余。

## [0.74.0] - 2026-08-07

### 0.74.0 - 入口确定性五修复链打包（archive 双 root / --auto 冷却端点 / --project-root fail-closed 三端对齐 / 审查遗留清理）（MINOR）

0.74.0 是 MINOR 发布，把 HEAD `1a375e6` 上 0.73.0 released 之后已合入的 5 个 commit 打包成发布候选（FIX-242 / FIX-243 / FIX-244 / FIX-245 / FIX-246），并同步版本投影与 release 文档。发布目标：archive.py 双 root 宿主解析与 `--project-root`（FIX-242）、`--auto` 终点冷却期有界推进（FIX-243，DEC-140）、archive 端与 verify_workflow 端 `--project-root` fail-closed 校验逐字对齐（FIX-244/245）、审查遗留观察项清理与仓库 EOL 基线（FIX-246）——入口确定性三链（resolve-entry/bootstrap/archive）输入边界完整闭环。但**不关闭 RISK-036/RISK-039**：官方市场操作（Codex Desktop marketplace E2E / 官方提交包）与 ArchGuard 外部宿主验证各自独立关闭标准未满足。版本投影 0.73.0 -> 0.74.0 全 PASS（M-set：13 projections + `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。

### Added

- **FIX-242 archive.py 双 root 宿主解析 + `--project-root`**（EVD-886，2026-08-05）：根因 = `ROOT = Path(__file__).resolve().parents[3]` 单根同时承载宿主事实源与插件资产，CLI 无 `--project-root`——cache 安装宿主（bootstrap Step E 文档化路径）归档操作指向插件包自身 .governance 幻影数据（EVD-885 实证：python_game cwd dry-run 报 134 条幻影证据）。修复（镜像 FIX-187 双 root）：`_resolve_plugin_root()`/`_resolve_host_root()`（resolve_entry.PLUGIN_HOME / resolve_host_root cwd 优先，失败 fallback parents[3] dogfood 兼容）；PLUGIN_ROOT 承载插件资产（`_latest_released_version()` 读 SKILL frontmatter 不再受宿主影响）；ROOT 保留为宿主事实 seam；CLI 新增 `--project-root <path>`（migrate/build-index/verify/rollback 全可用，`_extract_project_root_arg` 预扫描位置无关，缺值 exit 2，override 只重绑定宿主根）。验证：test_archive.py 106 passed（新增 13 项 TestDualRootResolution/TestArchiveCliProjectRoot，先红后绿 75 failed/31 passed → 106 passed）；test_verify_workflow.py 688 + 87 subtests 零回归。Code Review R0 APPROVED_WITH_NOTES/0（P2-1/P3-1~P3-4 记遗留观察项）。
- **FIX-243 archive --auto 终点冷却期有界推进**（EVD-887，DEC-140 方案 A，2026-08-05）：根因 = FIX-235 后 `--auto` 终点直接推进到 SKILL frontmatter 当前版本（0.73.0），连当前发布窗口证据一并归档过激进。修复：`_release_ledger_released_versions()`（读发布台账 `core/releases/*.json`，条件 lifecycle_state==released 且 withdrawn 非真——0.66.1 排除；单文件损坏/非 dict/非字符串 version fail-open 跳过不 crash）+ `_auto_archive_bounded_endpoint()`（台账 released 排序倒数第二）；终点公式 = bounded if（bounded 非 None 且 >= roadmap 终点）else roadmap 终点（`_version_to_tuple` 语义比较，advance-only 不回归 + 冷却上限），frontmatter 不再参与推进。验证：test_archive.py 115 passed（TestArchiveFix243 8 项 + fail-open 类型守卫 1 项，红→绿）；test_verify_workflow 688+87 零回归；仓库 dry-run 归档范围 v0.1.0~v0.72.0（128 条证据），0.73.0 证据 9 条保留热；check-archive-integrity trigger gap 范围同步。Code Review R0/R1 APPROVED_WITH_NOTES/0（P2-1 类型守卫 R1 关闭、P2-2 保留声明、P3 非阻塞）。
- **FIX-244 archive `--project-root` fail-closed 校验**（EVD-889，2026-08-06，FIX-242 R0 P2-1/P3-1/P3-4 处置）：`_validate_project_root()`——空值拦截在 Path 解析前（空串 strict resolve 会静默落 cwd）、resolve(strict=True) 失败或非目录 → stderr 分类诊断 `spg-archive-error: invalid-project-root — <path> (<reason>)` + exit 2；校验先于任何读写（main 中 override 先于命令分发）；与 resolve_entry.resolve_host_root fail-closed 语义逐行对齐。验证：test_archive.py 118 passed（3 新测试先红后绿——旧代码 SystemExit not raised + 空值落 cwd 实证）；test_verify_workflow 688+87 零回归；手工矩阵 4 场景 exit 码 + 分类诊断。Code Review R0 APPROVED_WITH_NOTES/0（P2-1/P2-2 测试加固建议记遗留观察项；P3-1 em-dash 编码可选）。
- **FIX-245 verify_workflow `--project-root` fail-closed 校验对齐**（EVD-890/891，2026-08-06，FIX-244 同型）：根因 = `_apply_project_root_override`（FIX-187 引入）对显式 `--project-root` 无存在性/目录/空值校验（Path.resolve() 无 strict），非法路径静默重绑定 phantom root 致 check 系列读错宿主；空值落 cwd。修复：`_validate_project_root()`（镜像 FIX-244 archive 端逐字一致——空值 Path 解析前拒绝/path is empty、strict resolve 失败/path does not exist、非目录/not a directory），`_apply_project_root_override` 入口先于任何宿主事实读取校验，失败输出 `verify_workflow: error: invalid-project-root — <path> (<reason>)` + exit 2（模块既有 CLI 错误约定）；默认路径零变化。验证：test_verify_workflow.py 693+87（5 新用例先红后绿——HEAD 版 5 failed）；test_archive.py 118 零回归；手工矩阵 3 场景。Code Review R0/R1 APPROVED_WITH_NOTES/0（P2-1 CLI 层 reason 后缀锁定 R1 关闭）。
- **FIX-246 遗留观察项清理**（EVD-892，2026-08-07）：FIX-244 P2-1/P2-2——test_archive.py 3 个 fail-closed 用例补齐 HOST_PROJECT_ROOT 未重绑定断言（突变实证：HOST 提前重绑定 3/3 FAIL）+ 错误原因串锁定（path does not exist / not a directory / path is empty 逐字比对）；FIX-242 P3-3——`_load_archive_module` 同步重绑定 module.ROOT 与 module.HOST_PROJECT_ROOT（红相实证 + 注释/docstring 同步）；FIX-242 P3-2——新增 `.gitattributes`（`*.py text eol=lf`；实测 index 556/556 全 LF、零 commit diff、无 EOL 幻影 diff），登记 `core/manifest.json` root_entries.files（check-manifest-consistency 门禁必需）。验证：红相 1 failed → 全绿；突变实证 2 组已恢复；test_archive 118 passed、test_verify_workflow 695+87 全绿；verify_workflow 全量 PASSED、check-manifest-consistency PASS、check-cross-references PASS。Code Review R1 APPROVED_WITH_NOTES/0。
- 版本声明与 e2e fixture 指针从 0.73.0 推进到 0.74.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、fixture plan-tracker、四个 source hooks，以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 6 版本钉；13 projections 由 `release-projection --write` 确定性写入）。
- `project/CHANGELOG.md` 新增 0.74.0 条目；release docs 三件套创建。

### Validation

- REL-067（0.74.0 MINOR 候选打包，2026-08-07；candidate-only，transition 需用户授权后另行执行）。
- FIX-242：test_archive.py 106 passed（13 新测试）+ test_verify_workflow 688+87 零回归；python_game cwd 双跑实证（修复后跳过 vs 基线 134 条幻影证据）；Code Review R0 APPROVED_WITH_NOTES/0。
- FIX-243：test_archive.py 115 passed（8+1 新测试）+ test_verify_workflow 688+87 零回归；dry-run v0.1.0~v0.72.0/128 条实证、0.73.0 证据 9 条保留热；Code Review R0/R1 APPROVED_WITH_NOTES/0。
- FIX-244：test_archive.py 118 passed（3 新测试）+ test_verify_workflow 688+87 零回归；手工验证矩阵 4 场景；Code Review R0 APPROVED_WITH_NOTES/0。
- FIX-245：test_verify_workflow 693+87（5 新用例）+ test_archive 118 零回归；手工矩阵 3 场景；Code Review R0/R1 APPROVED_WITH_NOTES/0。
- FIX-246：test_archive 118 passed、test_verify_workflow 695+87 全绿；红相+突变实证；verify_workflow 全量 PASSED、check-manifest-consistency PASS、check-cross-references PASS；Code Review R1 APPROVED_WITH_NOTES/0。
- 门禁（0.74.0 candidate，2026-08-07）：`check-version-consistency` PASS（13 声明）；`check-projection-sync` PASS（13 投影）；`release-ledger --no-remote` 0.74.0 candidate 记录（candidate_commit 派生要求文件已提交，commit 后重跑 PASS）；`check-release --version 0.74.0 --require-changelog --lineage-mode candidate` 记录——静态门禁全 PASS，执行门禁 2 项既有 FAIL（governance health 宿主治理记录 112 issues；unit tests 180s 超时，环境性，pytest 直跑全绿）。

### Boundaries

- 0.74.0 **RISK-036/RISK-039 remain open**。RISK-036（official marketplace operations）与 RISK-039（ArchGuard external validation）各自独立关闭标准未满足；本版本不重开任何已关闭风险。
- 不声明 official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success、1.0.0 production-ready；不关闭 RISK-036/RISK-039。
- MINOR bump 来自 archive/verify_workflow 双 root 契约与 fail-closed 输入边界生产强化（五修复链），不引入 breaking runtime API（CLI 新增参数为增量；默认路径零行为变化）。

## [0.73.0] - 2026-08-03

### 0.73.0 - 三链重构（入口/循环/任务规划）生产接线打包（MINOR）

0.73.0 是 MINOR 发布，把 HEAD `c14bce7` 上 0.72.0 released 之后已合入的 13 个 commit 打包成发布候选（AUDIT-142 / FIX-237 / FIX-239 / FIX-236 / FIX-240 / FIX-241 / FIX-233~235 / FIX-238），并同步版本投影与 release 文档。发布目标：入口引导确定性兜底（FIX-238）、循环引擎生产接线（FIX-236）、任务规划数据债去环与变更控制 triage 强制（FIX-237）三链重构落地。但**不关闭 RISK-036/RISK-039**：官方市场操作（Codex Desktop marketplace E2E / 官方提交包）与 ArchGuard 外部宿主验证各自独立关闭标准未满足。版本投影 0.72.0 -> 0.73.0 全 PASS（M-set：13 projections + `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。

### Added

- **FIX-236 loop 生产接线**（EVD-875，DEC-139 + ADR-017 §3）：Wiring A `review-record` CLI（review_record.py，record/reopen/close + 结构化 token + 证据写回）+ Wiring B `auto_judge_gate` 循环接入；`loop_exit_bridge.py` loop_exit -> next-candidates 推荐桥（fuse corrupt fail-closed）；Check 30 V6（review closure 终态 token 校验）；调用点 AST check（verify_workflow.py 接线完整性）。TDD 红→绿 36 新测试 + R1 8 新测试。
- **FIX-237 任务规划三件套**（EVD-872/873/880）：(1) 237.1 task-priority 数据债去环——12 行依赖去环 + 15 行状态回填，task-priority-analysis 0 cycle；(2) 237.2/237.3 工具过滤（open/plan 工具按角色过滤）+ cycle 默认 exit 0 + WARNING（--strict 保留）；(3) 237.4 变更控制 triage 强制集成——`change-triage` CLI（四步分析：依赖快照/优先级/冲突检查/版本适配）+ 机器 triage 记录（`.governance/change-triage/{id}.json` + TRIAGE- 证据行）+ Check 32（CLI 接线 AST 校验 + 无记录拦截，fail-closed）+ 237.5 交互边界 evidence 化（任务完成→下一步推荐写证据）。33 新测试红→绿。
- **FIX-238 入口引导修复**（EVD-881）：vendor `bootstrap.sh`/`bootstrap.cmd`（SPG_RESOLVE_TIMEOUT 15s 非法回退 + 四类分类诊断 + 退出码契约 0/1/2/3/4/5）；`resolve-entry` 薄入口（resolve_entry.py 本体零改动 DEC-096）；`SPG_WEB_INSTALL_TIMEOUT`（120s）；`@bootstrap-version` 陈旧标记升级链 + 3 profile 模板注入 + 宿主入口标记。29 新测试红→绿，test_verify_workflow 688 OK。
- **FIX-239 hook locale 硬化**（EVD-874）：has_approved_review_evidence 的 grep/sed 加 `LC_ALL=C`（pre-commit +6/-2、commit-msg +3/-1），消除 4 字节 UTF-8/emoji 下 GNU grep 字符类遍历失败导致的审查证据假阴性。
- **FIX-240 CI 流水线修复**（EVD-876/877/878）：manifest AGENTS.md 登记 + fresh-checkout unit-test 确定性 + threading-determinism 测试 Linux 适配（CI 全量 1527 测试唯一失败消除）+ 临时 CI debug workflow 已 revert。
- **FIX-241 resolve_entry 编码健壮性回归测试**（EVD-879）：外部 cp936 论断核验为不成立，检测缺口关闭（spy 断言 + write_bytes fixture）。
- **FIX-233/234/235 债务包**（EVD-868/869）：Check 30 历史 review 行终态豁免 + check-release 执行门禁 unit-test 超时参数化（180s -> 可配置）+ archive 证据迁移（release-forced 版本范围推进 + evidence-only 迁移）。
- **AUDIT-142 三链复诊 + ADR-017**（EVD-871）：entry/loop/task-planning 三链重构诊断报告（docs/requirements/entry-loop-planning-rearchitecture-0.72.0.md）+ 设计评审（docs/adr/ADR-017-loop-wiring-and-task-planning-0.73.0.md），REQ-104/105/106 已交付。
- **FIX-232 evidence-log 列数结构修复**（EVD-867，治理记录，非 git commit）：20 行 evidence_col_mismatch 归零。
- 版本声明与 e2e fixture 指针从 0.72.0 推进到 0.73.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、fixture plan-tracker、四个 source hooks，以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 6 版本钉）。
- `project/CHANGELOG.md` 新增 0.73.0 条目。

### Validation

- REL-066（用户授权 "0.73.0 发布方向"，2026-08-03）。
- FIX-236：36 新测试 + R1 8 新测试（review_record 271 行 / loop_exit_bridge 133 行 / loop_gate_processor 48 行 / test_verify_workflow +241 行）。
- FIX-237：33 新测试（test_change_triage 431 行）+ test_task_priority +298 行；Code Review R0 NEEDS_CHANGE/1P1 -> R1 APPROVED_WITH_NOTES/0。
- FIX-238：29 新测试；test_verify_workflow 688 OK；Code Review R0/R1 APPROVED_WITH_NOTES/0（P2-1 CI fresh-checkout 阻断已修）。
- FIX-240：CI 全量 1527 测试唯一失败消除；FIX-241：核验 + 回归测试（R0 APPROVED_WITH_NOTES）。
- `check-version-consistency` PASS（13 文件版本声明一致）；`check-projection-sync` PASS（13 投影同步）；release docs 三件套含保守边界 needle 且无未否定 forbidden claim。

### Boundaries

- 0.73.0 **RISK-036/RISK-039 remain open**。RISK-036（official marketplace operations）与 RISK-039（ArchGuard external validation）各自独立关闭标准未满足；本版本不重开任何已关闭风险。
- 不声明 official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success、1.0.0 production-ready；不关闭 RISK-036/RISK-039。
- MINOR bump 来自三链重构生产接线（入口/循环/任务规划），不引入 breaking runtime API（协议修正仅行为契约 MUST 强化，无接口破坏）。

## [0.72.0] - 2026-08-01

### 0.72.0 - Check 31 安装态消解打包 + release lineage 多版本授权 + 0.64.x docs 债务（MINOR）

0.72.0 是 MINOR 发布，把 HEAD `e2537c0` 上四个已合入 commit 打包成发布候选（FIX-200 / FIX-230 / AUDIT-140 / FIX-231），并同步版本投影与 release 文档。发布目标：安装包 Check 31 安装态 finding（EVD-853，0.71.0 插件包内 audit-140 旧措辞）随 `/plugin update` 消解。但**不关闭 RISK-036/RISK-039**：官方市场操作（Codex Desktop marketplace E2E / 官方提交包）与 ArchGuard 外部宿主验证各自独立关闭标准未满足；RISK-040/041 已由 DEC-135/DEC-137 关闭（本版本不重开）。版本投影 0.71.0 -> 0.72.0 全 PASS（M-set：13 projections + `verify_workflow.py` REQUIRED_SNIPPETS 6 版本钉）。

### Added

- **FIX-200 identity attestation gate**：`verify_workflow.py` `_loop_runtime_claim_gate_detail` 运行真实 `build_identity_attestation`（替代硬编码 `IDENTITY_ATTESTATION_PENDING`）；`core/loop-runtime-claim-authority.json` 同步（`identity_attestation` -> FIXTURE_PASS、`open_risks` -> []，RISK-037/042 已按 DEC-133 关闭）；`checks/loop_runtime_claims.py` 期望值同步；测试覆盖真实 identity verdict PASS/FAIL 路径。Check 31 identity_verdict=PASS；Check 31 残余 BLOCKED 仅为安装包 audit-140 旧措辞（EVD-853，本发布消解）。
- **FIX-230 release-ledger 多版本 tag 授权解析器**：`infra/release/ledger.py` 解析器按 `(decision_id, version, commit)` 三元组匹配（TDD）；8 个历史 `core/releases` manifest（0.63.0/0.63.1/0.63.2/0.63.3/0.63.4/0.64.0/0.64.1/0.65.0）回补 `tag_disposition=created_by_decision` / `tag_decision=DEC-136`；`test_release_ledger.py` +67 行（2 新测试）。RISK-041 关闭标准（DEC-137）最后一段（历史 tag 处置）闭环，EVD-859。
- **AUDIT-140 claim-scanner-safe 措辞**：`docs/requirements/audit-140-loop-runtime-wiring-gap-0.71.0.md` 自然语言措辞调整为 claim-scanner-safe，仓库侧 Check 31 的 UNSUPPORTED_AFFIRMATIVE 消除（EVD-858）。
- **FIX-231 0.64.x release docs 边界 token**：`docs/release/release-checklist-0.64.1.md`、`docs/release/rollback-plan-0.64.0.md`、`docs/release/rollback-plan-0.64.1.md` 补齐保守边界表述（DOC-001 回补 gap 闭环，EVD-863）。
- 版本声明与 e2e fixture 指针从 0.71.0 推进到 0.72.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、plan-tracker、四个 source hooks，以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 版本钉）。
- `project/CHANGELOG.md` 新增 0.72.0 条目。

### Validation

- REL-065（用户授权 "0.72.0 发布 + 0.64.x docs 债务"）。
- FIX-200：identity attestation 测试覆盖真实 verdict PASS/FAIL；Check 31 identity_verdict=PASS。
- FIX-230：ledger 解析器 TDD + 2 新测试（+67 行；39 测 38 PASS + 1 既有 0.66.2 FAIL）；8 个历史 manifest 回补并校验（DEC-136 / EVD-859）。
- AUDIT-140：仓库侧 Check 31 unblock（EVD-858）；FIX-231：DOC-001 gap 闭环（EVD-863）。
- `check-version-consistency` PASS（13 文件版本声明一致）；`check-projection-sync` PASS（13 投影同步）；release docs 三件套含 5 个保守边界 needle 且 0 个未否定 forbidden claim。

### Boundaries

- 0.72.0 **RISK-036/RISK-039 remain open**。Check 31 安装态消解（EVD-853）推进风险看护，但这两个风险各自独立关闭标准（官方市场操作 / ArchGuard 外部宿主验证）未满足。
- 0.72.0 **does not close RISK-036/RISK-039**（official marketplace / ArchGuard external validation 各自独立关闭标准未满足）；RISK-040/041 已由 DEC-135/DEC-137 关闭，本版本不重开。
- 不声明 official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-039，不声明 1.0.0 production-ready。
- MINOR bump 来自 Check 31 修复打包（identity attestation gate + ledger 授权 + 措辞修复），不引入 breaking runtime API。

## [0.71.0] - 2026-07-27

### 0.71.0 - systematic UX fixes for entry/loop/task-planning（MINOR）

0.71.0 是 MINOR 发布，完成 FIX-222~229 系统化 UX 修复：针对用户反馈的真实治理断裂——bootstrap 入口鸡生蛋（SYSGAP-047）、task-completion 推荐机械取最高优先级不分析依赖（AUDIT-140）、任务依赖与优先级系统三重断裂（AUDIT-141）。三份独立分析报告（sysgap-047/audit-140/audit-141）先定位根因，再分别修复：(1) 入口——AGENTS.md bootstrap 第一动作增加 3 方法定位 plugin_home（file: 路径推导 / dev fallback / 显式参数），消除 `<plugin_home>` 鸡生蛋（FIX-222）；(2) 循环——M7.4 step 6 + interaction-boundary.md:217 把 task-completion 从"机械取最高优先级"改为"依赖分析→推荐 next→AskUserQuestion"（FIX-223），step 4.6 增加 T1-T4 确定性 review 复审触发器（NEEDS_CHANGE→MUST 复审不问、APPROVED→终态、BLOCKED→escalation，FIX-224）；(3) 任务规划——plan-tracker 模板升级（`依赖` 列机器可解析格式 + `workflow_model`/`permission_mode` 字段，FIX-225），新增 `task_priority.py` 纯 DAG 解析器 + `compute_unblocked_tasks` + 环检测 + `task-priority-analysis` CLI 子命令（57 测试，FIX-226），behavior-protocol 依赖分析替代机械最高优先级（FIX-227），change-control stub 实质化为依赖分析+优先级+冲突检查（产品代码强制，FIX-228），change-impact-checklist 增加任务级依赖/冲突分析段（FIX-229）。但**不关闭 RISK-036/RISK-039/RISK-040/RISK-041**：这四个风险各自独立关闭标准（官方市场操作 / ArchGuard 外部验证 / 入口确定性宿主验证 / release-lineage 历史 tag 处置）未满足。版本投影 0.70.0 -> 0.71.0 全 PASS（M-set，纯字符串替换：plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。

### Added

- **FIX-222 bootstrap 入口确定性**：`AGENTS.md` bootstrap 第一动作增加 3 方法定位 plugin_home——(a) 平台 skill `file:` 路径推导（最可靠，主流平台支持）、(b) dev fallback（开发环境 `skills/` 目录）、(c) 显式参数（用户传入）。所有原 `<plugin_home>` 引用从"来自 resolve_entry.py"改为"见上方 bootstrap 第一动作"，消除鸡生蛋（需先知道 plugin_home 才能运行获取 plugin_home 的脚本）。SYSGAP-047 分析报告归档 `docs/requirements/sysgap-047-entry-bootstrap-paradox-0.71.0.md`。
- **FIX-223 task-completion 依赖分析推荐**：`behavior-protocol.md` M7.4 step 6 增强——task 完成后 MUST 运行依赖分析（`task-priority-analysis`）→ 推荐下一可执行任务 → 用 AskUserQuestion 呈现 → 不得直接结束。`interaction-boundary.md:217` 同步修正，从"机械取最高优先级未完成"改为"依赖分析推荐"。AUDIT-140 分析报告归档 `docs/requirements/audit-140-loop-runtime-wiring-gap-0.71.0.md`。
- **FIX-224 review 复审确定性触发器**：M7.4 step 4.6 增加 T1-T4 确定性触发器——T1（NEEDS_CHANGE 且 round<3 → MUST 立即 spawn 同一 Reviewer 复审，round+1，不输出"是否需要复审"问句）、T2（APPROVED/APPROVED_WITH_NOTES → 通过终态，后者 `unresolved_blockers=0`）、T3（BLOCKED → escalation 闭链终态）、T4（round>3 仍 NEEDS_CHANGE → MUST 转 BLOCKED，不得无限循环）。Check 21/30 违反检测同步说明。
- **FIX-225 plan-tracker 模板结构化依赖**：`core/templates/plan-tracker.md` 升级——新增 `workflow_model`/`permission_mode` 配置字段、`依赖` 列从自由文本升级为机器可解析格式（逗号分隔 task ID）、依赖格式规范说明。任务行新增结构化依赖数据，使机器可建依赖图。
- **FIX-226 task-priority-analysis 工具**：新增 `infra/task_priority.py`（861 行）纯 DAG 解析器——`parse_task_dependencies`（从 plan-tracker 解析 task 表为 DAG，区分 task-family vs cross-entity 引用，遵循 FIX-171 先例）+ `compute_unblocked_tasks`（计算无未完成依赖的可执行任务）+ 环检测（cycle detection，避免循环依赖死锁）+ `format_report`（人类可读报告）。`verify_workflow.py` 新增 `task-priority-analysis` CLI 子命令（薄入口，逻辑全在纯模块）。57 个测试覆盖解析/计算/环检测/CLI。
- **FIX-227 behavior-protocol 依赖分析替代机械优先级**：behavior-protocol M7.4 step 6 + interaction-boundary.md:217 依赖分析替代机械最高优先级（与 FIX-223 同 commit，此 FIX 显式登记行为协议修订范畴）。
- **FIX-228 change-control 实质化**：`change-control` reference 从 2 行 stub 升级为实质步骤——变更提出 → **依赖分析**（运行 `task-priority-analysis`，检查新任务是否阻塞/被阻塞）→ **优先级判定**（P0/P1/P2，结合 in-flight 任务与版本依赖链）→ **冲突检查**（是否与 in-flight 任务修改相同文件）→ **版本适配** → 创建 task → 执行。产品代码变更 MUST 走完整依赖分析+优先级+冲突检查。
- **FIX-229 change-impact-checklist 任务级分析**：`change-impact-checklist.md` 新增 2b 任务级依赖/冲突分析段——产品代码变更必须在影响评估中包含任务级依赖图分析与跨任务冲突检查。
- 版本声明与 e2e fixture 指针从 0.70.0 推进到 0.71.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、plan-tracker、四个 source hooks，以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 版本钉）。
- `project/CHANGELOG.md` 新增 0.71.0 条目。

### Validation

- DEC-134 授权（FIX-222~229 系统化 UX 修复），EVD-852。
- `task_priority.py` 57 个测试覆盖 DAG 解析 / unblocked 计算 / 环检测 / CLI 全 PASS。
- 3 份独立分析报告（sysgap-047/audit-140/audit-141）先定位根因再修复，遵循治理改进"分析先行"原则。
- `check-version-consistency` PASS（13 文件版本声明一致）；`check-projection-sync` PASS（13 投影同步）。

### Boundaries

- 0.71.0 **RISK-036/039/040/041 remain open**。系统化 UX 修复推进入口确定性与任务规划可用性，但这四个风险各自独立关闭标准（官方市场操作 / ArchGuard 外部宿主验证 / 入口确定性宿主验证 / release-lineage 历史 tag 处置）均未满足。
- 0.71.0 **does not close RISK-036/RISK-039/RISK-040/RISK-041**（official marketplace / ArchGuard external validation / entry determinism host validation / release lineage historical tags 各自独立关闭标准未满足）。
- 不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-039/RISK-040/RISK-041，不声明 1.0.0 production-ready。
- MINOR bump 来自系统化 UX 修复（入口/循环/任务规划），不引入 breaking runtime API。

## [0.70.0] - 2026-07-26

### 0.70.0 - verify_workflow Phase 5 extraction（MINOR）

0.70.0 是 MINOR 发布，完成 FEAT-009：把 `verify_workflow.py` 的 evidence/risk/review 三个检查域真实抽取到 `checks/evidence_domain.py`（402 行，12 域函数）、`checks/risk_domain.py`（212 行，4 域函数）、`checks/review_domain.py`（2127 行，30 域函数），`verify_workflow.py` 由 22468 行降至 20183 行（净 −2285，真实抽取经 DEC-088 校验——函数体迁移而非 re-export 伪装，仅保留薄入口 re-export）。行为等价性由独立 byte-diff 验证：抽取前后 `check-governance` 最终 Result 行逐字节相同（两侧均 134 issues），626 tests + 82 subtests 抽取前后完全一致，0 回归。这是 DEC-104 路线图最后一段（原 0.67.0 verify Phase 5 顺延到 0.70.0），也是 RISK-039（架构腐化看护）关闭标准之一——verify_workflow.py 按域拆分退化为薄入口。但**不关闭 RISK-036/RISK-039/RISK-040/RISK-041**：RISK-039 关闭还需 ArchGuard 在外部宿主项目验证、source/projection 双写消除与技术债登记闭环；RISK-036 需官方市场操作（本地无法完成）。FEAT-009 独立 Code Review APPROVED_WITH_NOTES / 0 blocker，ADR-016 设计 Design Review APPROVED_WITH_NOTES / 0。版本投影 0.69.0 -> 0.70.0 全 PASS（M-set，纯字符串替换：plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。

### Added

- **FEAT-009 verify_workflow Phase 5 extraction**：新增 `checks/evidence_domain.py`（402 行，14 函数：12 域函数 Check 1/1b/6/6b + `_vw` + `_resolve_shared`）、`checks/risk_domain.py`（212 行，6 函数：4 域函数 Check 2/8 + `_vw` + `_resolve_shared`）、`checks/review_domain.py`（2127 行，36 函数：30 域函数 Check 18/18b/21/21b/22/29/30 + 常量块 + `_vw` + `_resolve_shared`）。`verify_workflow.py` 22468→20183 行（git diff stat: +250 / −2535），仅保留薄 re-export 入口与 `sys.modules["verify_workflow"] = sys.modules["__main__"]` aliasing guard（与 Phase 1 manifest / Phase 2 capability_registry 先例一致）。KEEP rule + deferred `_vw()` pattern 正确实现。
- **行为等价性独立验证**：byte-diff 抽取前后 `check-governance` 输出——最终 Result 行逐字节相同（134 issues 两侧），626 tests + 82 subtests 抽取前后完全一致，0 回归。`check-governance` 134 issues 与 baseline 相同（非新增缺陷）。
- **DEC-104 路线图最后一段完成**：原 0.67.0 verify_workflow Phase 5 经 DEC-104 顺延到 0.70.0，至此 DEC-104 runtime-first 修复路线（0.66.1~0.70.0）全部段完成。RISK-039（架构腐化看护）关闭标准之一（verify_workflow.py 按域拆分退化为薄入口）由此推进，但 RISK-039 整体仍打开（还需 ArchGuard 外部验证 + 双写消除 + 技术债闭环）。
- 版本声明与 e2e fixture 指针从 0.69.0 推进到 0.70.0（M-set：plugins、marketplace、package.json、source/e2e SKILL frontmatter、manifest、plan-tracker、四个 source hooks，以及 `verify_workflow.py` 的 `REQUIRED_SNIPPETS` 版本钉）。
- `project/CHANGELOG.md` 新增 0.70.0 条目。

### Validation

- FEAT-009 Code Review：APPROVED_WITH_NOTES，0 blocker（P0=0，P1=0）；真实抽取经独立验证（函数体迁移而非 re-export 伪装，仅薄 re-export 残留）；行为等价性由 byte-diff `check-governance` 输出最终 Result 行逐字节相同确认（134 issues 两侧）；626 tests + 82 subtests 抽取前后一致，0 回归。
- ADR-016 设计 Design Review：APPROVED_WITH_NOTES / 0（`review-ADR-016-DESIGN-R0.md`）。
- 抽取符合 DEC-088（禁止以 re-export 伪装 God module 拆分），与 Phase 1（manifest）/ Phase 2（capability_registry）先例一致。
- 共 626 tests + 82 subtests，0 P0。

### Boundaries

- 0.70.0 **RISK-036/039/040/041 remain open**。RISK-039 关闭标准之一（verify_workflow.py 按域拆分）由此推进，但整体仍打开（还需 ArchGuard 外部宿主项目验证 + source/projection 双写消除 + 技术债登记闭环）。
- 0.70.0 **does not close RISK-036/RISK-039/RISK-040/RISK-041**（official marketplace / ArchGuard external validation / entry determinism host validation / release lineage historical tags 各自独立关闭标准未满足）。
- 不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-039/RISK-040/RISK-041，不声明 1.0.0 production-ready。
- MINOR bump 来自 verify_workflow.py 按域拆分（evidence/risk/review extraction），不引入 breaking runtime API；行为等价性经 byte-diff 验证 0 回归。

## [0.69.0] - 2026-07-26

### 0.69.0 - production telemetry + honest DORA metrics + dogfood/external validation proof（MINOR）

0.69.0 是 MINOR 发布，完成 FEAT-008 + VAL-008 + VAL-009：从 0.68.0 可执行 Loop Engine 的事件日志产出诚实 flow/DORA 遥测（`loop_telemetry.py` 纯函数 `compute_metrics` + `MetricValue` + `MetricsReport`，unknown-when-insufficient + anti-proxy），并在两个独立验证场景证明引擎真实运行——VAL-008 dogfood（3 单元多 tier/依赖阻塞/restart/fuse/rollback 全链，修复 DEFECT-1/2 后 28 PASS / 0 FAIL / 1 INFO）与 VAL-009 shitu 首个外部类型执行（preview/apply plan_hash identity、v2 validator、真实 flow-unit 推导、native entry、CAS 写盘、PASS 含两个非阻塞缺陷如实归档）。但**不关闭 RISK-037/RISK-042**：第二个外部类型验证仍待完成。新增 29 个 telemetry 测试 + VAL-008/009 全链验证，FEAT-008 独立 Code Review APPROVED_WITH_NOTES / 0 blocker。版本投影 0.68.0 -> 0.69.0 全 PASS（M-set，纯字符串替换：plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。

### Added

- **FEAT-008 production telemetry + honest DORA metrics**：新增 `loop_telemetry.py` 纯函数 `compute_metrics`（pure，从事件日志计算 flow lead time / DORA deployment frequency / lead time / change fail / MTTR / fuse trips），`MetricValue` + `MetricsReport` 类型化输出；unknown-when-insufficient（证据不足时显式 `unknown`，不编造数值）+ anti-proxy（不把活动/计划当成功）。`loop_health.py` `_compute_dora_metrics` 重命名为 `_dora_metrics_legacy_proxy` 并标注 deprecated，新增 advisory `telemetry` key；`verify_workflow.py` 新增 `cmd_loop_telemetry` CLI 入口。29 个新测试覆盖 purity / unknown-when-insufficient / anti-proxy。
- **VAL-008 dogfood 验证 PASS**：`val008_dogfood_driver.py` 在 `tempfile.TemporaryDirectory` 隔离工作区驱动 3 单元（middle `feature-auth` + inner `auth-login-form`/`auth-token-refresh`，依赖链）走 plan→activate→forward PARO→gate-fail back-edges→fuse trip→system block→restart recovery→telemetry→rollback。修复 DEFECT-1（`loop_gate_processor._event()` 现含全部 REQUIRED_FIELDS，事件通过 `validate_event`）+ DEFECT-2（`fuse_trip` payload 携带持久化 `loop_count`，telemetry iteration_count 正确）。**28 PASS / 0 FAIL / 1 INFO**（修复前 26 PASS / 2 FAIL）。211 loop tests + 2 subtests 通过，0 回归。
- **VAL-009 shitu 外部验证 PASS（首个类型）**：在真实外部项目 shitu（Android/Kotlin mobile-app，HEAD `c037a04`）执行 0.68.0/0.69.0 引擎：`build_migration_plan(shitu,"mobile-app")` + `confirm_decomposition` + `plan_to_payload`（v2 validator PASS）+ 真实 flow-unit 推导（mobile-app derive PASS）+ native entry 解析 + preview/apply plan_hash identity（REL-059/REL-060）+ `activate_unit`/`apply_transition` CAS 写盘（post-transition v2 validator PASS）+ v1/classic-gate rollback。**Overall verdict PASS**（含两个非阻塞缺陷如实归档：shitu 既存 VAL-007 @0.65.0 artifact 在 v1/v2 validator FAIL，属外部既有债务非引擎缺陷）。这是首个真实外部类型执行；第二个外部类型仍待完成以完全关闭 RISK-037/042。

### Validation

- FEAT-008 Code Review：APPROVED_WITH_NOTES，0 blocker（P0=0）；honesty 契约 purity/unknown-when-insufficient/anti-proxy 独立对源验证（非仅测试）；设计权威 ADR-015（review APPROVED_WITH_NOTES / 0）。
- VAL-008 dogfood：28 PASS / 0 FAIL / 1 INFO（DEFECT-1/2 修复后）；211 loop tests + 2 subtests 通过，0 回归。
- VAL-009 shitu：Overall verdict PASS（含两个非阻塞缺陷如实归档）；preview/apply plan_hash identity、v2 validator、真实 flow-unit 推导、CAS 写盘全 PASS。
- 共 29 个新 telemetry 测试 + VAL-008/009 全链验证，0 P0。

### Boundaries

- 0.69.0 **RISK-037/042 remain open**（second external type validation pending for closure）。Loop Engineering runtime 仍 NOT_MET。
- 0.69.0 **does not close RISK-037/RISK-042**（second external type validation pending）。
- 不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042，不声明 1.0.0 production-ready。
- MINOR bump 来自新增 telemetry 能力 + dogfood/外部验证证明，不引入 breaking runtime API。

## [0.68.0] - 2026-07-23

### 0.68.0 - executable Loop Engine（MINOR）

0.68.0 是 MINOR 发布，完成 FEAT-005~007：构建可执行 Loop Engine 的持久化 PARO 状态机 + 生产 gate back-edge/fuse/escalation + 重启安全 append-only 事件日志。三者合起来把 Loop runtime 从"规范契约"推进到"可执行引擎"：状态机以 CAS 写盘持久化、gate 失败触发 back-edge→round→fuse→escalation→system-level block、事件日志跨进程锁 + 单调性/合法性校验保证重启一致性。但**不关闭 RISK-037/RISK-042**（外部验证在 0.69.0）；执行引擎激活，但运行时完备性仍需 0.69.0 dogfood + 外部验证。新增 159 个测试，0 P0；FEAT-005~007 均独立 Code Review APPROVED。版本投影 0.67.0 -> 0.68.0 全 PASS（M-set，纯字符串替换：plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。

### Added

- **FEAT-005 persistent PARO state machine + CAS**：`loop_paro_engine.py` 新增 `validate_transition`（6 legal + 3 terminal）+ `apply_transition` CAS writer + `activate_unit` + `recover_state`；`flow_unit_runtime_v2.py` +257/0 `validate_loop_runtime_v2_with_transitions`（0.67.0 byte-frozen 完整）。CAS threading 12-thread 1-success/11-conflict 60x stable；fuse boundary >max_rounds。
- **FEAT-006 production gate back-edge/fuse/escalation + system-level fuse block**：`loop_gate_processor.py` 新增 `process_gate_result` terminal processor + `loop_fuse_check` pure read + `collect_loop_fuse_issues`；`verify_workflow.py` +25/0 `check_release_readiness` fuse check（system-level block，非 Coordinator advisory）。端到端 gate fail→back-edge→round→fuse→escalation→block；`loop_fuse_check` pure read CONFIRMED。
- **FEAT-007 restart-safe event log + dependency blocking + WIP**：`loop_event_log.py` append-only JSONL event log（14 types，cross-process lock，monotonicity/legality checks）；`loop_admission.py` dependency blocking + WIP budget（setup=1/inner=5/middle=2/outer=1）；`loop_paro_engine.py` + `loop_gate_processor.py` additive event_log hook（state-first/event-second，backward compat）。multi-process 4×100=400 0 loss win32，restart consistency CONFIRMED。

### Validation

- FEAT-005 Code Review：APPROVE，0 blocker（CAS threading 12-thread 1-success/11-conflict 60x stable；fuse boundary >max_rounds）；61 新 + 104 regression 通过。
- FEAT-006 Code Review：APPROVED_WITH_NOTES，0 blocker（`loop_fuse_check` pure read CONFIRMED，端到端 gate fail→back-edge→round→fuse→escalation→block）；45 新 + 101 regression 通过。
- FEAT-007 Code Review：APPROVED_WITH_NOTES，0 blocker（multi-process 4×100=400 0 loss win32，restart consistency CONFIRMED）；53 新 + 146 regression 通过。
- 共 159 个新测试，0 P0。

### Boundaries

- 0.68.0 **执行引擎激活，但运行时完备性仍需 0.69.0 dogfood + 外部验证**。Loop Engineering runtime 仍 NOT_MET，**RISK-037 remains open**，**RISK-042 remains open**。
- 0.68.0 **does not close RISK-037/RISK-042**（外部验证在 0.69.0）。
- 不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042，不声明 1.0.0 production-ready。
- MINOR bump 来自新增可执行 Loop Engine 能力（持久化状态机 + 生产 gate fuse + 重启安全事件日志），不引入 breaking runtime API。

## [0.67.0] - 2026-07-23

### 0.67.0 - canonical Loop Runtime Contract + shared migration planner + decomposition confirmation（MINOR）

0.67.0 是 MINOR 发布，完成 FEAT-002~004：建立规范化的 Loop Runtime Contract 与共享迁移规划器，并锁定分解确认与规范初始 gate 状态。三者合起来把 Loop runtime 的字段、schema 版本、plan identity 与初始状态收敛为机器可校验的单一契约，但**不激活运行时执行引擎**（执行引擎为 0.68.0，RISK-037/RISK-042 保持打开）。新增 104 个测试，0 P0；FEAT-002~004 均独立 Code Review APPROVED。版本投影 0.66.3 -> 0.67.0 全 PASS（M-set，纯字符串替换：plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。

### Added

- **FEAT-002 canonical Loop Runtime Contract**：新增 `core/loop-runtime-contract.json` v2 schema 与 `flow_unit_runtime_v2.py` validator（452 行），writer/validator/reader/rollup/health 共用单一契约和 schema version；`flow_unit_runtime.py` v1 字节冻结（byte-frozen containment boundary，FIX-195 containment 完整），新增 +76 行版本路由。消除 workflow_model、gate state、status source、rollup 字段漂移；v1/v2 drift parity 9/9 match，无回归。
- **FEAT-003 shared migration planner + immutable plan hash**：抽取纯 `build_migration_plan()` 函数（purity 16-thread CONFIRMED）；`MigrationPlan` 为 frozen/immutable，`plan_hash` = 8 结构字段 SHA-256 NFC；dry-run 与 apply 序列化同一 plan，apply 只验证并执行该 plan；同 target 的 unit IDs/count/project_type/gate schema 必须一致。FIX-195 containment 字节完整。
- **FEAT-004 decomposition confirmation + canonical initial gate state**：`confirm_decomposition` 全逻辑（候选验证 + operator 确认 + hash 重算）；`plan_to_payload` 产生规范初始状态（dormant/pending gate/example-fixture guard）；heuristic derivation 保持 advisory；激活前确认 flow-unit 分解，**不允许 dormant/example-data-only 冒充 active**（dormant-as-active 不可表达）。

### Validation

- FEAT-002 Code Review：APPROVED_WITH_NOTES，0 blocker；40 测试通过。
- FEAT-003 Code Review：APPROVED，0 blocker（purity 16-thread CONFIRMED，FIX-195 containment byte-intact）；28+68 regression 通过。
- FEAT-004 Code Review：APPROVED_WITH_NOTES，0 blocker；36+96 regression 通过。
- 共 104 个新测试，0 P0。preview/apply plan hash 相同，apply 前后 validator PASS；双 unit 可持不同 gate/phase。

### Boundaries

- 0.67.0 **does not activate execution engine**（运行时执行引擎为 0.68.0）。Loop Engineering runtime 仍 NOT_MET，**RISK-037 remains open**，**RISK-042 remains open**。
- 不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support、external first-session pilot success，不关闭 RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042，不声明 1.0.0 production-ready。
- MINOR bump 来自新增可执行契约/规划器/分解确认能力，不引入 breaking runtime API。

## [0.66.3] - 2026-07-23

### 0.66.3 - 0.66.2 release docs content fix（PATCH）

0.66.2 已发布（HEAD=T=`f859bb6`，tag v0.66.2），但 `check-release` 的 release docs 门禁有 3 项 FAIL：0.66.2 的 release-checklist/feature-flags/rollback-plan 边界文案（1）缺失 `RISK-036` 边界 token（`boundary_needles` 要求），且（2）使用过于冗长的否定语句使 `_line_has_scoped_claim_negation` 对 "external first-session pilot success" 等短语返回 False。0.66.3 是文档修复 PATCH：三份 0.66.3 release docs 改用 0.65.3 验证通过的紧凑边界模板（含 `RISK-036` token 且否定可被检测），使 release docs 门禁完全转绿、RISK-043 可关闭。版本投影同步 0.66.2 -> 0.66.3（plugins/marketplace/package.json/SKILL/manifest/plan-tracker/4 hooks/`verify_workflow.py` REQUIRED_SNIPPETS 版本钉）。无任何 runtime/逻辑/产品行为变更。DEC-131 授权。

## [0.66.2] - 2026-07-23

### 0.66.2 - 0.66.1 发布事故补偿与可信 lineage 恢复（PATCH）

0.66.1 commits 已到达 origin/master 但独立 post-release 审查发现发布阻塞（远端 v0.66.1 tag 缺失、release docs/manifest transition/semantic identity gate 非绿）。0.66.2 是非破坏性补偿发布：保留 0.66.1 历史为 incident（withdrawn/untrusted），通过三个串行精确-subject slice（FIX-215 semantic historical ownership + FIX-216 independent three-root identity attestation + FIX-217 native incident ledger repair）建立可信 lineage，再以 REL-063 创建 candidate C + manifest-only transition T + annotated v0.66.2 tag。新增 `verify_rel063_evidence.py` 证据门禁验证器（pre_c/candidate/full 三相 + atomic rehearsal + 13-row ownership matrix）。RISK-043（发布事故）在独立 Release Review 与 released-lineage 全绿后关闭。Loop Engineering runtime activation 仍 NOT_MET，RISK-037/RISK-042 保持打开。

## [0.66.1] - 2026-07-17

### 0.66.1 - Loop runtime containment hotfix（PATCH）

AUDIT-133 审计判定 Loop Engineering runtime activation 为 NOT_MET。0.66.1 把该审计结论固化为机器可校验的 fail-closed semantic claim gate（Check 31 + check-loop-runtime-claims CLI），防止 capability overclaim。所有 7 个 review SKILL 和 loop-role-mapping 的 overclaim 语句改为诚实的 experimental scaffolding 表述。loop_migration.py apply 路径由 FIX-195 canonical validator fail-closed 保护。性能门槛经 DEC-119 调整为绝对 8.0s（6 轮优化证明 paired improvement 数学不可达成）。RISK-037/RISK-042 保持打开。
## [0.66.0] - 2026-07-11

### 0.66.0 - Declarative release ledger、完整版本投影与 Phase 6（MINOR）

0.66.0 是 MINOR 发布：新增每版本不可变 release manifest、Git 实时 lineage、完整 artifact projection generator 和 `verify_workflow.py` Phase 6 真拆分。它把 0.55.3 后审计暴露的 tag、发布文档 provenance 与版本投影漂移问题转化为可执行、fail-closed、可回滚的机器门禁，同时保持 0.65.3 `check-release` CLI 兼容。

### Added

- **Declarative release ledger**：新增 `core/release-ledger.schema.json`、0.62.0~0.65.3 historical manifests、0.66.0 native manifest、append-only event/effective-state 模型，以及 `release-ledger` CLI。Native release 要求 candidate commit、唯一单父 candidate-to-released transition、本地 tag 和选定 remote tag 全链路一致。
- **完整 artifact projection generator**：`core/version-projections.json` 以 SKILL frontmatter 为唯一 active-version authority，覆盖 byte-copy、structured JSON 和 transformed text 投影；`release-projection --write` 使用预生成、symlink/path/JSON pointer/inventory 校验、原子替换和 rollback journal，失败时恢复原字节。
- **Phase 6 真拆分**：release、commit、version 和 projection 检查移入 `infra/release/` 与 `infra/checks/`，通过 root/Git runner/clock/timeout/context 注入运行，不 import 或 re-export `verify_workflow.py`。
- **可选质量工具探测**：`quality-tools` 对 Ruff/mypy 返回 `PASS`、`NOT_RUN` 或 `FAIL`；两者不是运行时依赖，未安装不会被包装为 PASS。

### Changed

- 版本声明由权威 SKILL frontmatter 推进到 0.66.0，并通过 projection registry 同步 canonical manifest、Claude/Codex/Zcode/Chrys metadata、package.json、四个 hooks 和 e2e fixture。
- 发布工作流新增 declarative ledger、projection check/write 和 optional quality-tool 边界；候选 commit 与 release transition commit 分离，避免 release commit 自引用。
- 0.62.0~0.65.3 historical manifests 只提供 `HISTORICAL_ONLY` 信任，不把缺失历史 tag 包装为 native lineage PASS。

### Validation

- FEAT-001 Code Review R3：`APPROVED`，`unresolved_blockers=0`。
- QA R1：PASS；Test Review R1：`APPROVED_WITH_NOTES`，`unresolved_blockers=0`。
- Full suite：882 tests 中 880 PASS、1 Windows real-symlink SKIP、1 个既有 Check 13 fixture isolation failure。该结果不是全绿。
- Focused release-ledger/projection/Phase 6 validation：29 total = 28 PASS + 1 Windows real-symlink SKIP；compatibility：70/70 PASS。
- Ruff 与 mypy：`NOT_RUN`，未安装；不作为运行时依赖或通过证据。

### Boundaries

- 本候选的 committed parent 必须精确为 `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd`；最终 commit/tag/push 后仍需运行 remote ledger 与 released-lineage 复验。
- 不回补任何历史 tag，不关闭 RISK-039 或 RISK-041，不声明 zcode official approval、marketplace approval、curated listing、universal/full runtime support 或 1.0.0 production readiness。
- 0.66.0 不引入 breaking runtime API；MINOR bump 来自新增可调用 CLI、ledger schema、projection workflow 与 Phase 6 模块能力。

## [0.65.3] - 2026-07-11

### 0.65.3 - release lineage/tag gate 与 marketplace source 事实修复 (PATCH)

0.65.3 是 PATCH 发布包，版本化 FIX-192 对发布边界和 marketplace source 事实的修复。它为后续发布增加 candidate/released 双模式 lineage 校验，记录 0.62.0~0.65.2 的发布链路审计，并明确本地、离线、远程 marketplace 与 direct git URL 的支持边界。它不创建或回补历史 tag，也不实现 0.66.0 规划的完整 declarative release ledger。

### Added

- **FIX-192 - release lineage fail-closed 门禁**（commit `1c734c7`）：`check-release` 新增 `--lineage-mode candidate|released`。candidate 模式用于 release commit/tag 产生前的候选包，不证明 tag 已存在；released 模式要求显式 `--release-commit`，并验证本地 `vX.Y.Z`、release commit 与远端 tag 指向一致。
- lineage Git 查询使用 `HOST_PROJECT_ROOT`，remote 只接受安全配置名；查询前验证 remote 存在，并使用 `GIT_TERMINAL_PROMPT=0`、15 秒 timeout 和脱敏诊断。URL、userinfo、option-like、unknown remote 或无法解析的 commit/tag 均 fail-closed。
- 新增 `docs/release/release-lineage-audit-0.65.3.md`：审计 0.62.0~0.65.2 的 release commit、本地/远端 tag 与 release docs provenance。0.62.0~0.63.4 的 18 份历史三件套均明确标为 `BACKFILLED`，但未创建历史 tag。
- 新增 `docs/marketplace/marketplace-source-matrix-0.65.3.md`：区分 local marketplace add + install、offline zip/package、remote marketplace clone/add 后使用 `source: "./"`，以及 0.64.1+ 当前不支持 direct git URL 的契约边界。

### Changed

- 版本声明同步到 0.65.3：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、四个 source hooks，以及 e2e fixture 指针。
- 发布流程明确要求候选态使用 `--lineage-mode candidate`；release commit 创建且 tag 推送后，必须使用 `--lineage-mode released --release-commit <commit>` 复验本地与远端不可变锚点。

### Validation

- FIX-192 独立 Code Review：R0/R1 为 `NEEDS_CHANGE`，分别发现 source/direct-URL/timeout 与 credential diagnostic 问题；R2 为 `APPROVED`，`unresolved_blockers=0`。
- Focused validation：53/53 PASS。
- Full unit suite：609/610；唯一失败为既有 Check 13 fixture 隔离问题。该结果不是全绿，不得包装为 full-suite PASS。
- 发布候选执行：`check-version-consistency`、`check-projection-sync`、`check-hot-fact-source --fail-on-issues`、`check-archive-integrity`、`check-release --version 0.65.3 --require-changelog --skip-execution-gates --lineage-mode candidate`、`verify` 与 `git diff --check`。

### Boundaries

- Candidate lineage 明确不要求也不证明 `v0.65.3` 已存在；只有 release commit/tag 创建并推送后，released lineage 复验才能证明完整链路。
- 不回补 0.63.0~0.65.0 的历史缺失 tag；任何回补必须先有独立治理决策批准 version-to-commit 映射。
- 不声明 zcode official approval、zcode marketplace approval、curated listing、universal/full runtime support 或 external first-session pilot success。
- 不关闭 RISK-036、RISK-037、RISK-039、RISK-040 或 RISK-041，也不声明 1.0.0 production-ready。

## [0.65.2] - 2026-07-11

### 0.65.2 - SKILL Loop Role 与审查终态规范一致性修复 (PATCH)

0.65.2 是 PATCH 发布包，收口 AUDIT-132 发现的 review SKILL Loop Role 表达与可执行语义问题，并修复发布审查 R0 暴露的 Check 30 审查终态协议不一致。它不改变 loop runtime、迁移数据格式或既有 P0-P3 审查职责。

### Fixed

- **FIX-191 - review SKILL Loop Role 规范化**（commit `35e13bd`）：7 个 review SKILL 统一使用稳定中文标题 `## 循环角色`；版本信息移至正文，避免把发布版本写入通用规范标题。
- 修复 Loop Role mapping 的相对引用，并明确失败结果回到所属 loop/fuse、Reviewer 不直接修改产品代码，以及终态由 Check 30 与复审链消费。
- 新增 fail-closed `check-loop-role-skills` 校验及正/负例覆盖，能拒绝缺失文件、错误标题、坏引用与缺失关键语义。
- **FIX-193 - Check 30 四态协议与 blocker 证据门禁**：统一 Check 30、M7.4、Agent 通信/路由、共享 mapping 与 7 个 review SKILL 的审查终态契约。`APPROVED_WITH_NOTES` 仅在存在唯一且无矛盾的结构化 `unresolved_blockers=0` 时通过；`APPROVED` 保持兼容；`BLOCKED` 可闭合审查链但不构成通过；`NEEDS_CHANGE(S)`、unknown 和 malformed evidence 均 fail-closed。
- **REL-055 R0 阻断闭环**：发布审查 R0 的 `NEEDS_CHANGE` 已通过 FIX-193 R0-R3 独立复审链解决，R3 Code Review 为 `APPROVED`。live Check 30 当前为 WARN，且无 V5/closure violations；7 条历史 `APPROVED_WITH_NOTES` evidence marker 已补充 `unresolved_blockers=0`。

### Changed

- 版本声明同步到 0.65.2：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、四个 source hooks，以及 e2e fixture 指针。

### Validation

- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync`
- `python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-loop-role-skills`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.65.2 --require-changelog --skip-execution-gates`
- `git diff --check`

### Known Release-Gate Conditions

- `check-release` 的 archive trigger gap 仍是既有失败，未被包装为 PASS。
- 当前其余 governance health 仍有 43 issues，未由本 PATCH 关闭或包装为健康全绿。
- FIX-193 后未获得新的全量单测全绿证据；已验证的是 CheckReviewClosureTests 17/17、R2 focused 19/19 与 Loop Role 7/7。不得用 focused PASS 替代未验证的 full-suite 结论。
- 本发布包不回补历史 tag，不声明 zcode 官方 marketplace approval，不关闭 RISK-036、RISK-037、RISK-039、RISK-040 或 RISK-041，也不声明 1.0.0 readiness。

## [0.65.1] - 2026-07-11

### 0.65.1 — 证据可信度 + post-0.65.0 hotfix 收口（PATCH）

0.65.1 是 PATCH 发布包：不引入新 loop-engineering 能力、不实现 0.65.2/0.65.3 的 SKILL Loop Role 或 tag-gate 机制，只把 0.65.0 后发现的证据口径、入口双 root、hook 审查状态兼容和 release-lineage 风险记录收口为一个可安装版本。

### Fixed
- **FIX-187 — 双 root crash 修复**（commit `407b74c`）：修复入口双 root 场景中 host/project root 解析导致的崩溃风险，保持 PLUGIN_HOME 与 HOST_PROJECT_ROOT 分离的 DEC-096 边界。
- **FIX-188 — 显式 `--project-root` 覆盖 + hook `APPROVED_WITH_NOTES` 兼容**：`verify_workflow.py` 支持在子命令后传入 `--project-root <host>` 并重新绑定 host `.governance` 事实路径；pre-commit / commit-msg hook 接受独立审查结论 `APPROVED_WITH_NOTES`，避免 REL-053 这类真实 review evidence 被误挡。
- **FIX-190 — 0.65.0 release checklist / session snapshot 证据口径修正**：纠正 0.65.0 发布资产中把 `check-archive-integrity` 写成 PASS 的错误口径；权威口径是 REL-053 审查时存在 pre-existing archive integrity FAIL，作为 non-blocking P2 / out-of-scope 处理，不追溯包装成全绿。

### Changed
- **AUDIT-132 / RISK-041 — 0.55.3 后质量审计与 release-lineage 风险归档**：把 0.55.3 后 release-lineage / tag 缺口作为显式风险边界记录进入 0.65.1 发布叙述；本版本不回补历史 tag、不创建 0.65.1 tag、不关闭 RISK-041。
- 版本声明同步到 0.65.1：source SKILL、canonical manifest、Claude/Codex/Zcode/Chrys plugin metadata、Claude marketplace metadata、package.json、4 hook `@version`、`verify_workflow.py` REQUIRED_SNIPPETS，以及 e2e fixture 指针（`project/e2e-test-project/skills/software-project-governance/SKILL.md` + `project/e2e-test-project/.governance/plan-tracker.md`）。

### Validation
- `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
- `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync`
- `python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.65.1 --require-changelog`
- `git diff --check`

### Boundaries
- No git tag created. No commit or push performed by the release package preparation step.
- No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, RISK closure, or 1.0.0 readiness is claimed.
- Pre-existing archive/tag/lineage failures remain visible and must be reported honestly by release checks.

## [0.65.0] - 2026-07-10

### Loop-Engineering Workflow Refactor (DEC-097/098/099, RISK-037)

**Major architectural evolution:** the linear G1-G11 stage model is superseded by a three-tier nested loop model (Outer/Middle/Inner) with AI's Plan-Act-Observe-Reflect cycle as a first-class citizen. Classic G1-G11 gates are preserved as loop-exit/entry certifications (DEC-098 criterion-4 compatibility).

#### New Modules (FX-188~FX-194, 7 implementation slices)
- **`core/loop-engineering-registry.json`** (FX-188): loop_gate_semantics G1-G11, PausePoints, LoopFuses, back-edges
- **`infra/loop_engine.py`** extensions (FX-189/193): loop_state activation, stateless round derivation (sacred parallel-safe property), fuse generalization (setup=2/inner=5/middle=3/outer=2), per-flow-unit rollup view
- **`infra/flow_unit_derive.py`** (FX-190): target-derived flow-unit generation — closes VAL-006 gap (non-game targets now derivable)
- **`infra/loop_migration.py`** (FX-191): `--apply` + `--rollback` with SHA-256 backup, manifest-verified hash integrity, collision-safe naming, 5 fail-closed cases, RISK-040 divergence guard
- **`infra/loop_health.py`** (FX-192): velocity-justification enforcement (Part 1 BLOCKING) + cost-exceedance advisory (Part 2) + DORA bridge metrics

#### New CLI Commands
- `loop-engineering-migration --apply/--rollback/--dry-run`: migrate classic-phase-gate → loop-engineering
- `check-loop-health`: velocity justification + DORA metrics (advisory-only, not blocking Check 28)
- `loop-rollup`: per-flow-unit loop_state view (resolves RISK-037 criterion 2 — no more single global stage)

#### Semantic Updates
- 7 review skills (requirement/design/tech/code/test/release/retro-review) re-labeled with loop-role semantics (ADR §3.5)
- `cmd_dynamic_lifecycle_migration` --apply path unblocked (was sys.exit(1) in 0.55.0)

#### Backward Compatibility
- Classic-phase-gate execution unchanged
- Rollback path fully restores pre-migration state (DEC-098 criterion-4)
- advisory-only checks don't block release gate

### RISK-037 Progress (1.0.0 hard blocker)
- Criterion 2 (plan-tracker rollup): IMPL-MET (FX-193)
- Criterion 4 (gate engine classic compat): IMPL-MET (FX-188 + FX-194)
- Criterion 5 (loop runtime activation): IMPL-MET (FX-189)
- Criterion 6 (apply path): IMPL-MET (FX-191)
- Criterion 8 (non-game generalization): IMPL-MET (FX-190)
- Criteria 5/7/8 external validation: still pending (not closed by 0.65.0)

### Tests
- 827 infra tests + 82 subtests passing
- Sacred property tests: stateless round derivation parallel-safety proven
- VAL-006 closure test: cli-tool 3 commands → 3 units (3 fixture forms)
- Data integrity: manifest-verified backup, tamper detection, rollback totality

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

<!-- loop-runtime-superseding:{"schema_version":"1.0","notice_id":"LRC-CHANGELOG-0661","effective_version":"0.66.1","supersedes_claim_ids":["LRC-HIST-CHANGELOG-001"],"authority_ids":["AUDIT-133","EVD-707","DEC-104"],"classification":{"runtime_activation":"NOT_MET","migration_validity":"NOT_MET","criteria_2_3_4_5_6":"PARTIAL","criterion_7":"NOT_PROVEN","criterion_8":"MET-NARROW","capability":"experimental_scaffolding"},"open_risks":["RISK-037","RISK-042"]} -->

## 0.66.1 Loop capability correction

AUDIT-133 supersedes the current interpretation of the 0.65.0 Loop claims. Loop Engineering is experimental scaffolding: runtime activation and migration validity are NOT_MET; criteria 2/3/4/5/6 are PARTIAL; criterion 7 is NOT_PROVEN; criterion 8 is MET-NARROW. RISK-037 and RISK-042 remain open. Historical release statements above remain records of what was asserted and tested at that time.
