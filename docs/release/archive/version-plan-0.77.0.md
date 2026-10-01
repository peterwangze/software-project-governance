# Version Plan - 0.77.0

**Version**: 0.77.0 (MINOR — proposed by this plan, subject to user confirmation)
**Release**: 四链+加固链七任务同槽——FEAT-010（DSH 标准插件安装支持）+ 事故防再发/守卫链（FIX-271 / AUDIT-146 / FIX-274 / FIX-272 / FIX-273 / FIX-275）
**Date**: 2026-08-24
**Plan task**: REL-070 第一段（版本规划——规划先行；候选打包为后续工作单元，本次不做）
**Status**: 规划建议文档。`release_authorized = false`——transition / tag / push 待用户授权（DEC-143 交互基线：自动推荐 + 用户确认）
**Produced by**: Release Agent（REL-070 规划段）；本文档只读规划 + 仅写入 `docs/release/version-plan-0.77.0.md`，未触碰版本文件/代码/`.governance/`

---

## 0. 规划基线事实（git / 治理记录核验，零编造）

| 事实 | 值 | 核验方式 |
|---|---|---|
| 发布基线 | `v0.76.0` = `4f24e74`（REL-069 transition commit，released lineage；tag peel 一致） | `git rev-list -n 1 v0.76.0` = 4f24e74 |
| 版本窗口 | `v0.76.0..HEAD` = **7 个 commit** | `git rev-list --count` = 7；`git describe` = `v0.76.0-7-g618ab13` |
| HEAD | `618ab13`（FIX-275） | `git log -1` |
| 推送状态 | `github-https/master` == HEAD == 618ab13（七任务已推送）；`origin/master`（SSH）= 9ce4e19 落后——既有环境限制基线（0.75.0/0.76.0 已披露同型："origin SSH 限制"） | `git rev-parse github-https/master` / `origin/master` |
| 版本声明现状 | package.json `0.76.0`、SKILL.md frontmatter `0.76.0`（未 bump——符合"候选打包不做"边界） | `Select-String` 实测 |
| BREAKING 声明 | `v0.76.0..HEAD` 全 commit message grep `BREAKING`/`breaking` = **0 命中** | `git log --format=%B` 过滤 |
| 路线图预留 | plan-tracker 版本路线图 0.77.0 行：状态=规划，"DSH 标准插件安装支持——bundle 形态接入 dsh plugin 生态（MINOR）"，FEAT-010（+ RISK-044 quick-scan 0.77+ 候选共版本槽位注记） | plan-tracker L446 |

窗口内 7 commit（first-parent 顺序，v0.76.0 之上）：

```
618ab13 FIX-275  pyc 打包卫生（files 否定模式）
7d7a966 FIX-273  side-effect 检测盲区加固
e3e45c0 FIX-272  bundle 同源防漂移守卫（@version-line 动态锚 + dsh.skills 校验 + Check 40）
4d13992 FIX-274  R1-R5 约束力加固第二波（M7.7 always-on 注入面 + Check 39 完成门控）
2bb10ac AUDIT-146 FEAT-010 事故 RCA 报告
d396097 FIX-271  R1-R5 防再发协议固化（M7.7 / 调度红线 / change-triage 第五步）
3339d99 FEAT-010  DSH 标准插件安装支持（bundle 形态）
```

---

## 1. Release Scope

### 1.1 七任务 → 变更类别

| # | 任务 | commit | 类别 | 变更摘要（commit message 核验） |
|---|---|---|---|---|
| 1 | FEAT-010 | `3339d99` | **feature** | DSH 标准插件安装支持——bundle 形态（根 package.json 增 dsh.bundle / dsh.skills 35 条 / files / keywords；新增 cordis.patch.yml 组合层；presets/governance 随包 preset；README DSH 行改标准安装命令 + 备选本地路径）。纯 md/config 零构建 |
| 2 | FIX-271 | `d396097` | **hardening** | AUDIT-146 RCA 根因 D1-D5 系统性修复：R1/R4/R5 → behavior-protocol M7.7；R3 → agent-dispatch-template 破坏性红线注入段；R2 → change-triage 第五步「执行副作用声明」。TDD 12 新例红→绿，四步既有输出字节不变 |
| 3 | AUDIT-146 | `2bb10ac` | **docs** | FEAT-010 事故 RCA 报告入库（`docs/requirements/audit-146-feat010-dsh-config-loss-rca.md`，266 行；H1a 可能·高 + 工具侧确认级排除 + D1-D5 根因 + R1-R5 草案；R0 审查 APPROVED_WITH_NOTES/0） |
| 4 | FIX-274 | `4d13992` | **hardening** | M7.7 压缩契约（R1 三选一 / R4 逐条上报 / R5 措辞）投影进 SKILL.md「关键行为契约」段 + DSH persona 模板第 5 条 + presets/governance/agent.cordis.yml + e2e 镜像；INJECTION_CONTRACT_ANCHORS 三面锚（27 锚/4 文件）；Check 39 `check_r1_completion_gate`（WARN-first + 收紧条件显式登记：连续 2 个零违规 0.77.x 版本后升 FAIL）；DEC-161/162 预算提额 2560B 入账 |
| 5 | FIX-272 | `e3e45c0` | **hardening** | INJECTION_CONTRACT_ANCHORS 增补 @version-line 动态锚（28 anchors，authority=SKILL.md frontmatter，fail-closed，FIX-250 前科防再发）+ `check_dsh_skills_manifest` 双向校验（35/35）+ CLI `check-dsh-skills-manifest` + 引擎 Check 40（product-gate 同 Check 33 归组）+ agent.cordis.yml 头部注释同步。TDD 9 新例红→绿；pytest 1923 passed/28 存量失败（stash 基线证实无关） |
| 6 | FIX-273 | `7d7a966` | **hardening** | side-effect 检测盲区加固：`_OUTSIDE_REPO_FILE_RE` UNC/单反斜杠根分支 + normalized 双 match + `_REAL_ENV_TEXT_RE` IGNORECASE + 否定语境 docstring 披露（行为不改）+ 9 边界测试（TDD 4红→61绿） |
| 7 | FIX-275 | `618ab13` | **hardening** | pyc 打包卫生：package.json `files` 新增 `!**/__pycache__/` + `!**/*.pyc` 否定模式（RED 154 pyc/10.34MB → GREEN 0 pyc/5.72MB，-64%；零误删零误增；payload 完整性零破坏；.npmignore 路线实证否定不引入） |

### 1.2 审查链状态（全部 APPROVED_WITH_NOTES / unresolved_blockers=0）

| 任务 | 审查链 | 遗留登记 |
|---|---|---|
| FEAT-010 | R0 NEEDS_CHANGE → R1 NEEDS_CHANGE → R2 APPROVED_WITH_NOTES/0（REVIEW-FEAT-010-R2） | F2→FIX-272、F11→FIX-275、F12 P3 |
| FIX-271 | CODE R0 APPROVED_WITH_NOTES/0 + DESIGN R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0（REVIEW-FIX-271-R0/R1） | P2×2+P3×4 → FIX-273；F-04/F-05/BC-1 → §5 裁决；R1-N1/N2/N3 → FIX-274 已执行 |
| AUDIT-146 | R0 APPROVED_WITH_NOTES/0（REVIEW-AUDIT-146-R0，机器行） | 无阻塞遗留 |
| FIX-274 | DESIGN R0 APPROVED_WITH_NOTES/0 + CODE R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0（REVIEW-FIX-274-R1；RECO-FIX-274） | P3-2/P3-3、P3-4/P3-5 观察登记 |
| FIX-272 | R0 APPROVED_WITH_NOTES/0（REVIEW-FIX-272-R0） | **P2×2**（F1 路径穿越测试缺失 / F2 诊断消息共用）+ P3×6 讨论级 |
| FIX-273 | R0 APPROVED_WITH_NOTES/0（REVIEW-FIX-273-R0） | P0=0/P1=0/P2=0；P3×3 讨论级（P3-3 change-triage SKILL "四步"描述陈旧） |
| FIX-275 | R0 APPROVED_WITH_NOTES/0（REVIEW-FIX-275-R0，机器行 2026-08-24 入账） | P0=0/P1=0/P2=0；P3×4（F1 顺序敏感性 / F2 双模式重叠 / F3 无注释载体 / F4 无自动化回归守卫）+ F5 证据登记缺口（Coordinator 已补 EVD-FIX-275） |

### 1.3 语义定位

- **主链语义**：FEAT-010（向后兼容新能力 = MINOR 承载主线）。
- **同箱叙事**：FIX-271/AUDIT-146/FIX-274/FIX-272/FIX-273/FIX-275 = FEAT-010 事故的 RCA → 防再发固化 → 注入面加固 → 守卫补全 → 检测盲区加固 → 打包卫生闭环（AUDIT-146 事故链在本版本完整收口，RISK-045 已于 2026-08-23 关闭，0.77.0 不重开）。
- 全部为增量变更：新 check 编号 39<40（无既有 check 重命名/删除）、新 CLI（`check-dsh-skills-manifest`）、FIX-271 四步既有输出字节不变、FIX-275 打包字段零运行时变化。

---

## 2. Version and SemVer（MINOR vs PATCH 论证）

**结论：MINOR。**

| 判据 | 事实 | 结论 |
|---|---|---|
| 新安装能力（MINOR 判据 ①——VERSIONING.md L12） | FEAT-010 为新增安装分发能力（bundle 形态随包 + cordis 组合层 + 随包 preset），对既有用户零破坏（既有路径/CLI/解包语义不变，review-FIX-275 §1 声明 7 独立核验）——对应 VERSIONING.md L12 Minor 触发类别（新增子工作流/skill、新增 B/C 级自动化能力）的分发面新能力 | → **MINOR 支撑项** |
| MUST 规则新增（MINOR 判据 ②——VERSIONING.md L37） | FIX-274 在 SKILL.md「关键行为契约」段新增第 4 条行为契约（真实环境必防护：R1 三选一 / R4 逐条上报 / R5 措辞）+ DSH persona 第 5 条——SKILL.md MUST 规则新增 → MINOR（VERSIONING.md L37 明列，影响所有 agent 行为） | → **MINOR 支撑项** |
| 无 BREAKING CHANGES | `v0.76.0..HEAD` 全 commit message grep BREAKING/breaking = 0 命中；无接口删除/重命名、无默认行为破坏（FIX-271 四步键序字节不变；FIX-272/273/274 为引擎注册/锚/门控增量；FIX-275 为打包字段） | 非 MAJOR |
| PATCH 面增量如实陈述（**不作为判级依据**） | 新 check 39/40 与新 CLI（`check-dsh-skills-manifest`）按 VERSIONING.md L34 "verify_workflow.py 新增检查项 → PATCH" 如实陈述为 **PATCH 面增量**；@version-line 锚/投影机制与打包卫生变更同理为增量——本窗口存在多项 PATCH 面增量（累积变更），**不**以"超出 PATCH 语义面"作为判 MINOR 依据；MINOR 判断依据 = 判据 ①② | 单列项（如实口径） |
| 累积变更达到里程碑（VERSIONING.md L12 前半） | 本窗口 = 7 任务同槽（1 feature + 5 hardening + 1 docs），其中含 2 项 MINOR 触发变更（判据①②）+ 多项 PATCH 面增量——构成里程碑级累积变更（0.76.0 发布后首个多变更窗口） | → MINOR 佐证项 |
| 版本号预留核对（规划纪律第 1/5 条） | 路线图 0.77.0 行已预留"DSH 标准插件安装支持（MINOR）"FEAT-010；本计划内容 = 该行 FEAT-010 主线 + 事故链关联扩展（AUDIT-146/FIX-271/272/273/274/275） | 一致（FEAT-010 语义吻合）；**打包时 MUST 更新路线图行**：增列六任务 + decision-log 记录范围核增（规划纪律 5/6） |
| 90% 完成率（规划纪律 7） | 7/7 任务全部 ✅ 完成并推送 | 100% |
| 未完成项处置（规划纪律 7） | 遗留项 P2×2/P3×N/RISK-044 quick-scan 均为非阻塞观察/登记项——按 §5 裁决表显式入槽/出槽 | 无隐藏带入 |

---

## 3. 里程碑（候选打包 → 发布；REL-069 先例 + DEC-143 基线）

| 里程碑 | 内容 | 交互边界 |
|---|---|---|
| **M-0 规划裁决** | §5 遗留项入槽/出槽用户确认；若 F-02（README 分级补注）入槽 → 新任务注册（triage 机器入账）+ DEC（范围核增）+ Developer 实施 + 审查链——**须在 M-1 启动前完成**（上限 **N 个 Coordinator 会话**，N 由 M-0 向用户确认）；**超期 → F-02 自动出槽登记 0.78.x，0.77.0 按七任务打包，记 decision-log**（D.P2-4 回退规则） | **用户确认（ask_user_question）** |
| **M-1 候选打包** | Release Agent：版本投影 0.76.0→0.77.0（15 投影 M-set + @bootstrap-version 标记面 + REQUIRED_SNIPPETS 6 版本钉）+ CHANGELOG 0.77.0 条目（v0.76.0..HEAD 7-commit 全窗口：Added/Changed/Fixed/Validation/Boundaries）+ release 三件套（feature-flags / release-checklist / rollback-plan）+ `core/releases/0.77.0.json` candidate + 路线图 0.77.0 行更新 + DEC（范围核增/预算披露注记/**遗留项出槽登记**：RISK-044 quick-scan 出槽 0.78.x+ 经 decision-log + CHANGELOG 附注登记——P3-4）→ candidate commit | 自动（产生候选包） |
| **M-2 候选门禁** | §4 全部候选态门禁执行 + 既有基线 FAIL 分类披露（REL-067/068/069 先例） | 自动 |
| **M-3 双审查 R0** | Release Reviewer + Design Reviewer（plan-tracker REL-070 行登记；候选包阶段 REL-069 先例 = CODE + RELEASE 双审）→ APPROVED_WITH_NOTES/unresolved_blockers=0；机器入账 REVIEW-REL-070-R0 | 自动（评审链） |
| **M-4 用户授权 transition** | state：`release_authorized=false → true`；DEC-143 基线（自动推荐 + 用户确认）；授权记录 + DEC 入账 | **用户确认（ask_user_question）——发布唯一人工门** |
| **M-5 transition commit** | manifest-only：0.77.0.json candidate → released + `rel070-transition` event（integrity / recorded_at）+ 单一 parent = candidate commit；commit 后 `release-ledger --no-remote` 重跑 **NATIVE_RELEASED**（transition commit 后 lifecycle_state→released——ledger.py L433-436 状态机：lifecycle=="candidate"→NATIVE_CANDIDATE，否则 NATIVE_RELEASED；候选态 NATIVE_CANDIDATE 为 M-2 阶段值） | 自动（授权后） |
| **M-6 annotated tag + 原子推送** | annotated tag `v0.77.0`（peel 到 transition commit）→ 原子推送 github-https（master + tag；远端 SHA 精确一致；merge/repeat/wrong-parent 阻断） | 自动（授权后） |
| **M-7 发布后验证** | `check-release --version 0.77.0 --require-changelog --lineage-mode released --release-commit <commit>` 核心门禁 PASS + 既有基线 FAIL 如实披露；`release-ledger --version 0.77.0 --remote github-https` NATIVE_RELEASED PASS | 自动 |
| **M-8 发布收尾** | plan-tracker 工作流版本 → 0.77.0；路线图 0.77.0 行 → 已发布；`archive.py migrate --auto --dry-run`（报告需归档 → 执行 + `check-archive-integrity`）；风险复核保持（RISK-044 2026-08-28 / RISK-036/039 2026-09-30） | 自动 |

## 3.1 回滚边界（显式声明）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only 可逆） | 常规可逆操作（0.76.0 rollback-plan Reversibility **L43** "Revert the release-package commit" 先例——L43 为 Reversibility 表对应行；L46 为 Watchdog checks 行，与引文不匹配故不作引用） |
| 已发布 v0.77.0 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据） | **绝不静默重指**——远程 tag 修正为不可逆发布动作，须 Coordinator 治理流程（0.76.0 rollback-plan **Reversibility L50 先例**："Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

> **rollback-plan-0.77.0.md MUST 复刻本边界表**（R0 P2-1；该表与 §4 回滚验证段共同构成发布回滚契约）。

> 里程碑纪律（plan-tracker L497-500）：里程碑到期 MUST 执行检查；延期 MUST 记录 decision-log。

---

## 4. 发布门禁清单

候选态（M-2）与释放态（M-7）的确定性命令（执行路径：`python skills/software-project-governance/infra/verify_workflow.py <cmd>`）：

| # | 门禁 | 0.76.0 先例值 | 0.77.0 预期 | 备注/分类惯例 |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASS（13 文件声明；1 advisory WARN——host plan-tracker 仍 0.75.0） | PASS（13 文件 0.77.0） | 同型 WARN：host plan-tracker 记录版本由 Coordinator 打包后 bump |
| 2 | `check-projection-sync --fail-on-issues` | PASS（15 投影） | PASS | 漂移时 `release-projection --write`（written=15 先例；--write 后须 rollback journal/原子写入测试证据 + 再次 check PASS——ADR-010） |
| 3 | `check-manifest-consistency` | 560/600 PASS（FIX-275 后基线 564/608） | PASS | 打包增删文件 MUST 登记 manifest |
| 4 | `check-cross-references --fail-on-issues` | 68 文件/649 refs PASS | PASS（零悬空） | |
| 5 | `verify`（无参） | PASSED | PASSED | 既有基线失败按先例披露（28 存量失败；resolve_entry 00:00-02:00 时间敏感 flaky——0.76.0 先例） |
| 6 | pytest 全量 | 1895 passed+237 subtests 0 failed（FIX-272 新基线 1923 passed/28 存量失败） | 记录实测；零新增失败 | 180s 环境超时先例（0.75.0：直跑全绿） |
| 7 | check-governance 零新增 | 113==113（FIX-269 先例 A/B Compare-Object） | 零新增 | 宿主基线 issues 数按其实时 posture（0.76.0 发布时 check-release 报 111/112——以候选打包实测为准） |
| 8 | `check-injection-contract` | 27 锚/4 文件 PASS（FIX-274） | 28+ anchors（FIX-272 增 @version-line 动态锚） | fail-closed |
| 9 | `check-dsh-skills-manifest` | —（0.76.0 无此命令；0.77.0 新 CLI） | 35/35 双向 PASS | Check 40（product-gate 同 Check 33 归组） |
| 10 | `check-release --version 0.77.0 --require-changelog --lineage-mode candidate` | 6 issues 全分类（3 未提交态产物 + 3 既有宿主基线：hot-fact-source/archive gap/governance health） | 核心静态门禁全 PASS；FAIL 项按类披露（REL-067/068/069 先例） | candidate 模式不要求不证明 tag |
| 11 | `release-ledger --version 0.77.0 --no-remote` | NATIVE_CANDIDATE（未提交候选过渡态，commit 后重跑） | 同型 | **两阶段**：候选态（M-2）= NATIVE_CANDIDATE（candidate commit 提交后）；释放态（M-5/7 transition commit 后）= NATIVE_RELEASED（lifecycle→released，ledger.py L433-436）；UNKNOWN/BLOCKED 不得包装为 PASS |
| 12 | `quality-tools` | 渐进检查 | Ruff/mypy 未安装 → NOT_RUN 如实记录；执行失败 = FAIL；不得包装为 PASS | ADR-010 |
| 13 | `check-release ... --lineage-mode released --release-commit <commit>` | 核心门禁 PASS + 4 既有基线 FAIL（hot-fact-source/archive gap/origin SSH 限制/governance health——EVD-894 先例） | 同型 | tag/push 后执行；验证本地+远端 tag |
| 14 | `release-ledger --version 0.77.0 --remote github-https` | NATIVE_RELEASED PASS | 同型 | **远端 = github-https**（0.75.0 先例 + 本规划 §0：推送远端即 github-https；origin SSH 实测不可达——Host key verification failed；**以 origin 执行须如实报告 UNKNOWN/BLOCKED，不得包装为 PASS**）；ADR-010：唯一 transition、单一 parent、merge/repeat/wrong-parent/rename-delete-add 阻断 |

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——按 0.76.0 先例以可逆性分析 + 门禁复跑为验证载体，rollback-plan-0.77.0.md 定义全量/部分回滚路径，回滚后复跑 #1/#2/#10 与 `git diff --check`）。

**回滚边界（发布态）**：候选/transition 态回滚 = `git revert` 候选 commit（manifest-only 可逆）；已发布 v0.77.0 tag 回滚 = **仅 governed recovery**（Coordinator + 显式证据、绝不静默重指）——完整边界表见 **§3.1**；**rollback-plan-0.77.0.md MUST 复刻 §3.1 边界表**（0.76.0 rollback-plan Reversibility L50 先例）。

---

## 5. 遗留项入槽/出槽裁决表

> 本表为 **建议方案**（REL-070 任务书裁决项）。最终决策归用户/Coordinator（M-0 交互边界）。所有来源以文件路径留痕消歧。

### 5.1 裁决汇总

> **M-0 交互注记（FIX-280 / DEC-169 追加）**：本裁决表为规划建议；M-0 终裁经 `ask_user_question`（即 AskUserQuestion 工具；DEC-143 交互基线「自动推荐 + 用户确认」）由用户确认——0.78.0 版裁决（DEC-169）即该模式实证。

| ID | 来源（留痕） | 级别 | 建议 | 理由（依赖状态依据） |
|---|---|---|---|---|
| **FIX-272 R0 F1+F2**（路径穿越测试 3 例 + 穿越/畸形诊断消息拆分） | `.governance/review-FIX-272-CODE-R0.md`（F1 L97 / F2 L98） | P2×2 | **出槽（延后 0.78.x 登记）** | (a) FIX-272 实现级路径穿越拦截经 Reviewer 独立 14/14 探针验证全部正确（安全无缺陷，P2-1 仅为回归锚定缺口）；(b) P2 为测试锚定 + 诊断可操作性增强，非阻塞；(c) 0.77.0 打包基线 = 已合入七任务；新增开发任务须 triage 机器入账 + DEC + Developer/Reviewer 链，将改变发布范围（规划纪律 5/6）并延长窗口；(d) 若用户裁决入槽 → 前置条件：DEC + 新任务注册（FIX-276 候选）+ 开发+审查链在 M-1 前完成 |
| **F-04**（npm pack --dry-run 断言机器守卫：0 pyc + 关键文件在包） | `.governance/review-FIX-275-CODE-R0.md`（F4 L95） | P3 | **出槽（延后 CI/check 候选，0.78.x+）** | (a) 观察级（P3）；(b) FIX-275 验收已含 RED→GREEN 实测 + Reviewer 独立重验（243 entries/0 pyc/5.72MB，零误删零误增），该守卫缺失不构成 0.77.0 门禁缺口；(c) 实现 = verify_workflow.py 新断言 + 测试，属新开发；建议随 0.78.x 守卫批次或独立任务登记 |
| **F-05 + BC-1**（R5 词表版本化 + R1(b) 备份留痕显式化 + Check 39 升 FAIL 批次） | `.governance/review-FIX-271-DESIGN-R0.md`（F-05 L96 / BC-1 L82）+ DEC-160（收紧条件："连续 2 个零违规 0.77.x 版本后升 FAIL，升级时 MUST decision-log 入账"）+ plan-tracker FIX-274 行（"F-05+BC-1 并入 Check 39 升 FAIL 批次"） | P2/P3 | **出槽（延后 0.78.x 批次——结构性不能在 0.77.0 内）** | 升 FAIL 触发条件 = "连续 2 个零违规 **0.77.x** 版本后"——第 1 个零违规版本恰是 0.77.0 发布后开始计；0.77.0 打包窗口内该条件不可满足（零违规观察窗口尚未开始）。0.77.0 发布后计入第 1 个零违规版本，若 0.77.1/0.78.0 连续零违规 → 0.78.x 或之后转 FAIL，升级时 MUST decision-log（DEC-160 义务）。BC-1（R1(b) 留痕含备份清单：路径/文件数/字节数 + 校验命令输出——把"完整"从形容词变可核对事实）建议并入同一批次 |
| **F-02**（README 能力分级宣示补注："当前治理自动级别 = A 级 + B 级；C 级为 roadmap 未实现"） | `.governance/review-FIX-269-CODE-R0.md`（F-02）+ DEC-157 ② + plan-tracker FIX-269 行 | P2 | **建议入槽 0.77.0（推荐）** | (a) README 为对外宣示面（dsh 生态首屏）；0.76.0 能力分级声明已在 SKILL/commands 落地，而 README **L183/L189-190/L495**（2026-08-24 实测行号——较 2026-08-23 审查时点 L169/L175/L481 +14 漂移，FEAT-010 增改 README 所致）仍为"全自动"笼统宣示，落入 plugin-contract L114 禁令字面（DEC-157 确认）；(b) 0.77.0 主链 FEAT-010 已改 README（DSH 安装行）——同一窗口统一 README 宣示面，防口径漂移；也可与 F-03 同任务；(c) **代价 = 需追加一个完整开发+审查循环**（文档级改动，预计 1 个会话；含 triage/DEC/Developer/Reviewer/门禁复跑）；**若优先最短窗口，选全部出槽（§5.2）——M-0 选项 MUST 携带该代价**；(d) **再定位声明**：DEC-157 ② 原登记为「0.76.x 候选」，本次入 0.77.0 = **显式再定位**（0.76.x PATCH 系列不承载文档开发任务；0.77.0 窗口统一 README 宣示面）——**M-0 决策须入 decision-log 注记**；(e) **截止/回退规则**：F-02 链须在 **M-1 启动前**完成（上限 **N 个 Coordinator 会话**，N 由 M-0 向用户确认）；**超期 → 自动出槽登记 0.78.x，0.77.0 按七任务打包，记 decision-log**；(f) 若用户裁决出槽 → 登记 0.78.x，0.77.0 CHANGELOG/checklist 披露"README 分级补注未含本版本" |
| **F-03**（e2e commands/governance.md 投影决策：fixture-command-governance 投影注册 vs 独立维护声明） | `.governance/review-FIX-269-CODE-R0.md`（F-03）+ DEC-157 ③ | P2 | **建议：决策型——0.77.0 候选打包期由 Coordinator 裁决并落 decision-log**（Release Reviewer 无 decision-log 写入权——评审角色权限边界），无需独立开发任务 | (a) 该事项本质是投影契约决策（version-projections.json 未声明 commands 投影，PROJECTION_SYNC_PATTERNS 含 commands/*.md 且 e2e harness 以 fixture 为真运行目标——DEC-157 完整描述）；(b) 不改变代码/打包内容，仅登记决策；(c) 与候选打包并行零冲突；若裁决"注册投影"→ 归入 0.78.x 投影同步任务 |
| **F-04-env**（agent-locks file_locks 扩展：side_effect.blast_radius 非空时真实环境路径记入 active_tasks 参与文件锁冲突判定——并发互斥维度） | `.governance/review-FIX-271-DESIGN-R0.md`（F-04 L95）+ plan-tracker FIX-274 行（"F-04 独立 FIX"） | P2 | **出槽（延后独立任务，0.78.x+）** | (a) 并发互斥是不同于事故实际形态（单 agent 破坏）的失效模式，R0 裁定低概率、可观测性已被 R2+R4 覆盖（Design R0 S2 重评：部分充分）；(b) FIX-271 已"不阻塞"裁定；0.77.0 已含完整防护链（R1-R5 + always-on 注入面 + Check 39 门控）；(c) 独立 FIX 需要锁模型扩展设计审查——安全敏感，不宜塞入本已重载的 0.77.0 窗口。注：本项与 FIX-275 F4（npm pack 守卫）**命名冲突**——以来源文件消歧 |
| **RISK-044 quick-scan 秒级子集** | risk-log RISK-044（2026-08-22）+ DEC-149 + CHANGELOG 0.76.0 L13 | — | **出槽（延后 0.78.x+ 候选；RISK-044 2026-08-28 复核独立执行）** | (a) quick-scan 为未注册的设计+开发任务（子集划分 + 性能优化 + 测试），0.77.0 范围已定（七任务），引入新功能违反规划纪律 5/6；(b) 时序：复核 deadline 2026-08-28 早于/临近 0.77.0 可能完成时点——**无论 0.77.0 进度，2026-08-28 复核 MUST 由 Coordinator 独立执行**（决策：维持接受（DEC-149）/ quick-scan 前移）；(c) 0.77.0 发布文档仍需披露 RISK-044 现状（31-32s 实测 + DEC-149 修订口径——0.76.0 checklist L104 先例）；(d) **出槽登记动作**：M-1 候选打包 MUST 将「quick-scan 出槽 0.78.x+」经 **decision-log + CHANGELOG 附注**登记（M-1 记录动作），并与 RISK-044 **2026-08-28 复核结论**衔接（复核确认 quick-scan 维持延后/前移） |

### 5.2 裁决后 0.77.0 范围预判

- **推荐终态（用户确认后）**：0.77.0 范围 = 七任务（已合入）+ **F-02 README 分级补注**（若用户采纳入槽，前置条件见 5.1）；F-03 打包期记 DEC；其余全部出槽登记 0.78.x。
- 若用户选择全部出槽：0.77.0 范围 = 七任务，零新开发，窗口最短（与 REL-069 同型：candidate-only 打包）。
- 两种情形下 0.77.0 的 semver 定位不变（MINOR 由 FEAT-010 新安装能力 + FIX-274 MUST 规则新增承载；新 check/CLI 按 PATCH 面增量如实陈述，不作判级依据）。

---

## 6. 风险披露

| 风险 | 状态 | 0.77.0 处置 |
|---|---|---|
| RISK-036（official marketplace operations） | **保持打开**（2026-09-30；1.0.0 硬阻塞；无关闭标准满足） | 0.77.0 **不关闭**；不声明 official/marketplace approval |
| RISK-039（ArchGuard external validation） | **保持打开**（2026-09-30；1.0.0 硬阻塞） | 0.77.0 **不关闭**；不声明 universal/full runtime support |
| RISK-044（`--summary-only` 31-32s 超设计 <15s 门禁） | **打开**（2026-08-22 登记；已接受/DEC-149；deadline **2026-08-28 复核**） | 0.77.0 不改变 0.76.0 语义；quick-scan 裁决见 §5.1（出槽建议）；发布文档 MUST 披露（0.76.0 checklist L104/feature-flags L30 先例）；**08-28 复核由 Coordinator 独立执行——早于发布完成时点也照常执行** |
| RISK-045（FEAT-010 事故） | **已关闭**（2026-08-23，用户授权） | 0.77.0 不重开。**关闭依据（risk-log L45 正式三条件）**：① AUDIT-146 RCA（EVD-AUDIT-146；根级删除确认级定性/工具侧确认级排除/H1a 归因框架，R0 审查 APPROVED_WITH_NOTES/0，commit 2bb10ac）+ ② FEAT-010 隔离协议闭环（R0→R1→R2 复审链 REVIEW-FEAT-010-R2；自证 boot + 时窗取证双确认真实 ~/.dsh 零操作，commit 3339d99）+ ③ R1-R5 固化双审（FIX-271：CODE R0 + DESIGN R1 均 APPROVED_WITH_NOTES/0，REVIEW-FIX-271-DESIGN-R1，commit d396097）——**关闭依据 = EVD-AUDIT-146 + REVIEW-FEAT-010-R2 + REVIEW-FIX-271-DESIGN-R1 + commits**；**FIX-274（及 FIX-272/273）= 关闭后持续加固承接，非关闭依据** |
| 既有基线 FAIL 披露惯例 | 0.76.0 发布时 check-release 6 issues（3 未提交态 + 3 基线：hot-fact-source / archive trigger gap / governance health）；released 4 基线 FAIL（+ origin SSH 限制；governance health 112 / 早期 111 报告值以时点为准） | 0.77.0 候选/释放态按 REL-067/068/069 先例**如实分类披露**；`governance health` 类型（host `.governance/` posture，105+ 类 issue 数为实时值——以候选打包实测为准；零 `.governance/` 文件由发布包触碰） |
| DSH preset 时滞（RISK-D5） | 已知 | 0.77.0 迁移说明随发布文档：`git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`；未 sync 前旧 preset 携带旧版本行——不得宣称未 sync 安装的会话级效果 |
| 预算提额披露义务（DEC-161 后续） | persona 契约块 2560B / SKILL 契约段 2560B（DEC-161/162，2026-08-23） | **0.77.0 发布文档 MUST 披露检查值**（DEC-161 "检查值在 0.77.0 发布文档披露"）；守卫测试 `test_persona_contract_block_stays_within_budget` + `test_skill_contract_section_stays_within_budget` |

---

## 7. No-overclaim 边界

本规划（及后续 0.77.0 候选）**不声明**：

- 1.0.0 production-ready / 1.0.0 正式发布
- official approval / zcode official approval / marketplace approval / curated listing
- universal / full runtime support
- external first-session pilot success（外部项目首会话试点成功）
- RISK-036 / RISK-039 关闭
- 任何历史已发布 version tag 的状态变更（v0.76.0 及之前未受本版影响）

并**不创建、不证明** `v0.77.0` tag 存在（candidate-only；`release_authorized=false`——transition/tag/push 待用户授权，DEC-143 基线）。七任务主线语义 = FEAT-010（bundle 安装支持），不关乎官方收录/市场批准；FEAT-010 遗留的 gh topics 标签动作（Coordinator 职责）独立于本发布包。

---

## 8. 边缘问题与观察项

1. **plan-tracker 热文件滞后（已回写）**：FIX-275 行在规划初稿时点（2026-08-24 上午）仍为 "⏳ 待执行 (2026-08-23 补入账)"，git log 终态 = ✅ 已推送（618ab13）+ REVIEW-FIX-275-R0 机器行已入账（2026-08-24）——**快照注记（2026-08-24 复核）**：plan-tracker FIX-275 行已回写为「→ ✅ 完成 (2026-08-24)——commit `618ab13` 已推送 github-https（EVD-FIX-275 + REVIEW-FIX-275-R0 APPROVED_WITH_NOTES/0…）」；本观察项关闭（FIX-272/273 行同源已带「→ ✅ 完成」）。
2. **change-triage SKILL 描述陈旧**（"四步"；FIX-271 边缘发现 + FIX-273 P3-3 登记）：观察级，建议随 F-02 入槽任务或 0.78.x 顺手合并。
3. **F-04 命名冲突**：FIX-275 R0 F4（npm pack 守卫，P3）vs FIX-271 DESIGN R0 F-04（环境路径锁扩展，P2）——本表以来源文件路径消歧；后续任务注册时 MUST 避免同 ID 歧义（建议新 ID 如 FIX-276/277）。
4. **0.77.0 与 RISK-044 时序交互**：若候选打包/发布拖过 2026-08-28，RISK-044 复核独立执行（不阻塞发布流程，反之发布不替复核）。
5. **路线图行更新义务**：规划纪律 5/6——候选打包时更新 0.77.0 行（状态/任务列表）并记 decision-log（范围核增：AUDIT-146/FIX-271/272/273/274/275 为 FEAT-010 预留给定列的关联扩展）。
6. **基线数字漂移**：0.76.0 各文档对 governance health 有 111/112/116 等不同时点取值——后续发布文档写"以候选打包实测为准"，不引用旧值作新声明（0.76.0 checklist 先例正确做法）。
