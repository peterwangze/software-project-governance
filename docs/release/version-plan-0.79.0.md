# Version Plan - 0.79.0

**Version**: 0.79.0 (MINOR — proposed by this plan, subject to user confirmation at M-0)
**Release**: 降噪第二波/规则面批——DEC-172 裁决 A ② 段承接：G3 扩展 + G5 + G6 + W-7/BC-7 + FIX-281 判定面①⑧（Check 30 历史格式迁移 + Check 30c 机器行分类，version-plan-0.78.1 §6 方案 A 同域同批）+ RISK-044 正式复评挂载（DEC-169 ② MUST 含复评结论）
**Date**: 2026-09-08（用户 /governance 盘点后选定启动；plan-tracker REL-074 行）
**Plan task**: REL-074（版本规划——规划先行惯例，REL-071/072/073 先例；候选打包为后续工作单元，本次不做）
**Status**: 规划**已裁决**（M-0 2026-09-08——DEC-177 四项裁决全部采纳推荐项：①基线确认 ②RISK-044 缓解分支 ③同窗双入槽 ④新增候选全采纳；范围核增项已登记 §5 M-0 裁决记录 + 路线图 0.79.0 行）。`release_authorized = false`——transition / tag / push 待用户授权（DEC-143 交互基线；M-4 唯一人工门）
**Produced by**: Release Agent（REL-074 撰写分工）；本文档只读规划 + 仅写入 `docs/release/version-plan-0.79.0.md`，未触碰版本文件/产品代码/`.governance/`。并行 Analyst 同窗执行 queue-triage-0.78x 候选 vs 2026-09-08 现状只读对账（无文件冲突）；对账产出由 Coordinator 合并进本规划后定稿（plan-tracker REL-074 行分工描述）

---

## 0. 规划基线事实（治理记录核验，零编造）

| 事实 | 值 | 来源（留痕） |
|---|---|---|
| 已发布基线 | 0.78.1（2026-09-05，PATCH，Breaking changes 无）——candidate `8155400`（13-commit 窗口 `afb959d..8155400`，NATIVE_CANDIDATE）→ transition `6b5e7bf`（M-4 用户授权 2026-09-05，manifest-only，integrity=sha256:5e9b4497…）→ annotated tag `v0.78.1`（tag object `fece70a`，peel=6b5e7bf；2026-09-08 git tag -l 核实存在）→ 原子推送 github-https（master+tag 远端 SHA 精确一致）→ NATIVE_RELEASED PASS（--no-remote 与 --remote 双证） | plan-tracker L470（路线图 0.78.1 行）/ L11（项目配置·工作流版本）；CHANGELOG.md 0.78.1 节（L5-L9） |
| 工作流版本 | 0.78.1 | plan-tracker L11 `工作流版本: 0.78.1` |
| HEAD | `v0.78.1` transition `6b5e7bf` 为版本链锚点。**待验证**：0.78.1 之后的治理/docs 变更（2026-09-08 bootstrap 回写、REL-074 入账、本规划文档等）的 git commit 状态未在本次规划内核对（Release Agent 本次零命令执行——角色工具权限 Bash 禁止）——M-1 候选窗口核定 MUST `git log v0.78.1..HEAD --oneline` 核定窗口全量 commit | plan-tracker L11（2026-09-08 会话记录）；version-plan-0.78.1.md §0 同型先例（HEAD 待验证→M-1 核定） |
| 版本序列 | v0.78.1 → v0.79.0（MINOR 路径，不跳号；无中间版本） | plan-tracker L470→L471（路线图连续行）；VERSIONING.md L9-L13 |
| 版本号预留核对 | 路线图 0.79.0 行已预留（状态=规划中）：「降噪第二波——G3 扩展 + G5 + G6 + W-7/BC-7 + FIX-281 判定面①⑧（…同 Check 30 形状/终态判定语义域同批——version-plan-0.78.1 §6 方案 A）（MINOR，规则/能力面）」——本规划内容与该行给定范围**一致**；Analyst 对账合并后若有新增候选入槽 = **范围核增**（纪律 5/6：M-0 裁决 + DEC 入账 + 路线图行更新，M-1 执行） | plan-tracker L471（路线图 0.79.0 行）；VERSIONING.md L119-131（纪律规则 1-8） |
| 出槽队列裁决 | DEC-172（2026-08-26，REL-072 用户裁决 A 两段式）② 段：0.79.0 MINOR 承接 G3 扩展/G5/G6/W-7+BC-7 + RISK-044 复评挂载 MUST；搁置 9+1 项维持 | decision-log（DEC-172）；queue-triage-0.78x.md §3.2/§3.3/§5；plan-tracker L259（REL-072 行） |
| FIX-281 判定面出槽承接 | ①⑧由 version-plan-0.78.1 §6 方案 A 建议拆出 → 0.78.1 发布实录确认落位（CHANGELOG 0.78.1 Boundaries L46「判定面 ①⑧ 出槽 0.79.0」+ plan-tracker L470 范围列直接记载）——缺陷修复面②③④⑤⑥⑦⑨已随 FIX-287/288/289 发布 | plan-tracker L470（0.78.1 行范围列）/ L262（FIX-281 行）；CHANGELOG.md 0.78.1 节 L46；version-plan-0.78.1.md §6.1/§6.2；release-checklist-0.78.1.md Scope L10 |
| 0.79.0 承接的 ①⑧ 缺陷现状 | ① Check 30 V2×9/V5×2 对 pre-FIX-174 文件式 review 记录判 11 项 FAIL（历史格式迁移缺失）；⑧ Check 30c 合法机器行（REVIEW-/RECO-）新增即入 WARN 无分类升级路径（router 10→13 实证）——**插件侧未修**（0.78.1 仅交付缺陷面）；router 宿主持续暴露 | plan-tracker L262（FIX-281 行全文：router EV-066 2026-08-23 + EV-071/073 2026-08-27 实证） |
| RISK-044 状态 | 已接受（DEC-149）；2026-08-26 检查点复核通过（维持，DEC-167；实测 32.8s/29.6s 满足修订验收「单次 <60s 且每会话仅一次」）；**正式复评挂 0.79.0**（DEC-169 ②；risk-log 行「0.78.x」字样为 DEC-167 时点表述，以 decision-log 为权威口径——version-plan-0.78.1 §0 同论证） | risk-log L44（RISK-044 行）；decision-log（DEC-169 ②/DEC-149/DEC-167）；version-plan-0.78.1.md §0/§7 |
| 同窗复评风险 | RISK-046（派发锁漂移）/ RISK-047（force 覆盖语义）/ RISK-048（测试环境敏感）/ RISK-049（适配器宣示 vs 验证等级缺口，2026-09-05 登记）——复评窗均登记「2026-09-30（与 RISK-044 同窗）」= 下轮版本规划（本规划） | risk-log L46/L47/L48/L49（各行复评列原文） |
| 既有健康基线 | check-governance --summary-only 实测 **117 issues**（0.78.1 M-2 门禁实测 117 vs 0.78.0 基线 127，-10 零新增；2026-09-08 bootstrap 复测同值 117——构成：Check 10 M5 anti-pattern ×1 + Check 18c 执行包 scope 过宽 ×4 为首项 FAIL 类） | release-checklist-0.78.1.md L25（Gate #7）；plan-tracker L11（2026-09-08 实测注记） |
| pytest 全量基线 | 27 failed / 2049 passed / 226 subtests passed（0.78.1 M-2 amend 后全量复跑 2026-09-05）——逐类归属：test_cleanup manifest-presets 既有（0.77.0 起结构基线）+ test_loop_runtime_claims 既有（RISK-048 环境敏感）+ test_pre_commit_review_evidence SUBFAILED×25 既有（bash/WSL 环境基线） | release-checklist-0.78.1.md L24（Gate #6） |
| 任务面快照 | 0.78.1 任务链（FIX-282~290）全部完成并发布；REL-074（本任务）进行中；Analyst 并行对账任务同窗 | plan-tracker L263（REL-073 行）/ L273（REL-074 行）/ L470 |

**窗口 commit 清单**：待 M-1 候选窗口核定 `git log v0.78.1..HEAD` 核定（0.78.1 后已知变更面：2026-09-08 bootstrap 回写 + REL-074/Analyst 任务入账 + 本规划文档 + Analyst 对账报告——多属 VERSIONING.md L40-46 不驱动 bump 的治理记录面，随候选打包统一入窗）。

---

## 1. Release Scope（范围特征与任务化结构）

- **范围特征（DEC-172 ② + 路线图 0.79.0 行口径）**：全部入槽候选为规则面/判定面/能力面——G3 扩展（写时门禁新引擎扩展）、W-7/BC-7 + FIX-281 ①⑧（Check 30 形状/终态判定语义域同批）、G5/G6（降噪第二波主题项——单项为 L13 行为面输出变更，主题性打包走 L12 累积 MINOR 论证，如实口径见 §2）；与 0.78.1 PATCH（纯缺陷修复面）边界清晰无交叉。
- **任务化结构**（M-0 裁决后、M-1 前执行；编号由 change-triage 机器分配，本规划不预设）：按域分组注册，预计 4~7 个任务——G3 扩展独立（新写时 guard 引擎 + hooks/集成 + 测试 + 设计审查）；W-7/BC-7 + FIX-281 ①⑧ 同域同批（Check 30 形状/终态判定——DEC-172/version-plan-0.78.1 §6 论证同批承载语义一致性最好，可 1~2 任务）；G5 + G6 同批（tpa/summary 输出域）；Analyst 合并后新增候选（若有）各自 triage。每任务 TDD + Developer/Reviewer 链（SoD：Developer 不审查自己的代码）；判定面变更 MUST 双审（Release Reviewer + Design Reviewer——G2/DEC-166 先例）。
- **拆分执行结构**（FIX-281 先例延续）：①⑧入槽子任务 depends_on 不挂 FIX-281 批次行（避免 REL-002 跨仓 data gap 传染阻塞——version-plan-0.78.1 §6.3 口径）；FIX-281 批次行按拆分进度闭合。
- **90% 完成率（纪律 7）**：全部入槽任务 ✅ 完成 + 审查终态（APPROVED 或 unresolved_blockers=0）后方可 M-1；超 N=2 会话上限自动出槽登记后续版本（DEC-163 惯例，DEC-169 ④ 延续——M-0 ⑨ 确认）。

---

## 2. Version and SemVer（MINOR 论证——VERSIONING.md L12/L37 原文引用）

**结论：MINOR（0.78.1 → 0.79.0，不跳号；建议，M-0 ⑧ 确认）。**

### 2.1 判定规则原文引用（`skills/software-project-governance/core/VERSIONING.md`）

| 条款 | 行号 | 原文 | 本版适用 |
|---|---|---|---|
| Minor 触发条件 | **L12** | 「**Minor** (0.X.0) \| 累积的 PATCH 达到里程碑；或新增 MUST 规则、新增子工作流/skill、**新增 B/C 级自动化能力** \| 每版本里程碑」 | G3 扩展 = 写时门禁**新增 B 级自动化能力**（扩展至 Coordinator 直写路径）；W-7/BC-7 + FIX-281 ①⑧ = 判定规则扩展（规则面）；G5/G6 = 主题性打包（累积里程碑）——三支触发均命中 |
| SKILL MUST 规则新增 | **L37** | 「SKILL.md MUST 规则新增 \| **MINOR** \| 影响所有 agent 行为——但 1.0.0 之前可灵活处理」 | 若 G3 扩展涉及 SKILL/behavior-protocol 契约新增、或判定面变更伴随 MUST 规则落盘 → L37 面直接支撑（queue-triage §1.1 L37 适用注记原文：「若 G3 扩展涉及 SKILL/behavior-protocol 契约新增 → MINOR」） |
| Patch 触发条件（反证/边界） | L13 | 「任何影响 agent 行为或用户可见的变更：bootstrap 模板变更、子工作流活动变更、skill/模板新增或修改…」 | G5/G6 单项为输出文本变更（L13 面）——但作为降噪第二波主题打包由 L12 累积承载（queue-triage §2.1 #8 原口径）；如实陈述不混同 |
| 计划外变更用 PATCH | L123 | 「不在当前 MINOR 范围内的变更 → bump PATCH，不占用下一 MINOR」 | 0.79.0 窗口内出现的计划外缺陷修复 → 0.79.x PATCH 承载（0.78.1 先例同型） |

### 2.2 逐项论证与 0.78.1 PATCH 边界划分

| 判据 | 事实 | 结论 |
|---|---|---|
| 新增 B/C 级自动化能力（L12） | G3 扩展：写时结构看护从 change-triage 成功路径扩展至 Coordinator 直写 plan-tracker/完成记录路径——新写时 guard 引擎（queue-triage §2.1 #7：「扩展 = 规则面/新 B 级自动化能力（L12/L37 面）」；review-FIX-278-DESIGN-R1 W-3/BC-3） | → **MINOR 支撑项** |
| 判定规则扩展（L12 + DEC-169 ③ 先例） | W-7/BC-7（终态 marker 集扩展——状态格混合终态子类判定）+ FIX-281 ①（Check 30 pre-FIX-174 文件式 review 记录历史格式迁移路径——新增历史形状分类）+ ⑧（Check 30c 合法机器行白名单/溯源分类规则）——三项同属 Check 30 形状/终态判定语义域；**G2 L-A/L-B/L-C 先例**：DEC-169 ③ 定性「G2 判定规则 = 行为/规则面显著变更」支撑 0.78.0 MINOR → 本批同型 | → **MINOR 支撑项**（若强行 PATCH 承载 = 与本仓先例自相矛盾——version-plan-0.78.1 §6 ①⑧行已论证，正是 0.78.1 拆两段出槽的依据） |
| 累积里程碑/主题打包（L12） | G5（tpa 重复抑制，-1.7KB/会话——audit-148 L184 量化）+ G6（追查预算提示行——audit-148 L185；G1 已覆盖主体，剩余收尾面）= 降噪第二波主题批（DEC-172 ② 定名） | → **MINOR 支撑项**（主题性打包；单项 L13 面如实陈述） |
| 与 0.78.1 PATCH 的边界 | 0.78.1 已承载并发布全部**缺陷修复面**（FIX-282~290：②③④⑤⑥⑦⑨ + DEC-171 + N-P2 批 + F-3/F-01 + FIX-272 P2×2——L38「仅修复 bug」逐项论证，发布实录确认）；判定面①⑧**显式出槽 0.79.0**（plan-tracker L470 原文）→ 0.79.0 范围零缺陷修复面残留（计划外缺陷走 0.79.x PATCH，L123），全部为规则/判定/能力面 | 边界清晰，**无交叉无跳号** |
| 无 BREAKING CHANGES（预期） | 判定面扩展均走放宽/fail-safe 方向：① FAIL→WARN 历史迁移（放宽不收紧）；W-7/BC-7 修正保守漏降级（向真实终态对齐——G2 DEC-166「ACTIVE/真实 nonzero 恒 FAIL」边界锁定惯例延续）；G3 扩展 = 新增守卫（新增检查不破坏既有行为）——**预期零 BREAKING**；最终以 M-2 门禁实测 + M-3 双审判定为准；1.0.0 前 MINOR 可含有限 Breaking Change 且 MUST CHANGELOG 显式标注（VERSIONING.md L83） | 非 MAJOR |
| 版本号预留（纪律 1/3/5） | 路线图 0.79.0 行已预留（L471）且本规划内容匹配 DEC-172 给定范围；Analyst 合并后范围核增走纪律 5/6 | 一致 |
| 未完成项处置（纪律 7） | 出槽/搁置项全部显式登记（§5）；无隐藏带入 | 合规 |

**一句话论证**：0.79.0 全部入槽候选命中 L12 三支触发（新增 B 级自动化能力〔G3 扩展〕/ 判定规则扩展〔W-7/BC-7 + ①⑧，G2 先例同型〕/ 累积主题里程碑〔G5/G6〕）+ L37 潜在面（契约新增时）——与 0.78.1 已发布的纯 L38 缺陷修复面构成清晰的两段式边界（DEC-172 裁决 A 原设计）。

---

## 3. 里程碑链 M-0~M-8（对齐 0.78.1 先例 + DEC-143 基线）

| 里程碑 | 内容 | 交互边界 |
|---|---|---|
| **M-0 规划裁决** | 本规划 §5 裁决表 + §6 复评挂载呈报用户裁决（裁决点清单 9 项）：① 范围总确认（DEC-172 ② 五项入槽维持/调整）；② G3 扩展前置实绩确认（queue-triage §2.1 #7 前置条件「先观察 G3 首波实绩〔BC-6〕再扩展」——0.78.0/0.78.1 两版实绩是否充分：Analyst 已合并 2026-09-08，三例活体 0 误报实证支持，建议确认解除）；③ FIX-279 P2-3 专项评估落点（并入本版 or 维持出槽）；④ RISK-044 复评结论确认（DEC-169 ② MUST——§6 结论建议供确认，材料已合并 2026-09-08：4 样本墙钟 + 无新用户反馈记载）；⑤ RISK-046/047/048/049 同窗复评处置 + 根因修复/关闭标准候选任务入槽评估（risk-log 各行复评窗 = 本规划时点）；⑥ 搁置项前移可选项（F-04 并入 0.79.0 守卫批次 / F-05 词表版本化 + BC-1 字段化独立前移 / quick-scan 前移——均默认维持搁置）；⑦ Analyst 对账合并后新增候选裁决（REQ-109/111/113/114 草案、治理数据漂移、健康 117 对账产出——Coordinator 合并后呈报）；⑧ MINOR 定位确认（§2）；⑨ N=2 会话上限延续确认（DEC-163/169 ④ 惯例）。裁决后入槽项任务化（triage 机器入账 + 注册 + Developer/Reviewer 链）**须在 M-1 启动前完成**；超期 → 自动出槽登记后续版本 + decision-log | **用户确认（ask_user_question——由 Coordinator 呈报）** |
| **M-1 候选窗口核定** | Release Agent：git 窗口核定（`git log v0.78.1..HEAD`，§0 待验证项①闭环）+ 版本投影 0.78.1→0.79.0（15 投影 M-set + @bootstrap-version 标记面 + REQUIRED_SNIPPETS 版本钉——0.77.0/0.78.1 先例）+ CHANGELOG 0.79.0 条目 + release 三件套（release-checklist / rollback-plan / feature-flags〔本批无 flag 则按先例出「无 flag 声明」〕）+ `core/releases/0.79.0.json` candidate + 路线图 0.79.0 行更新（含 Analyst 合并后范围核增若有）+ DEC（范围核增/出槽登记）→ candidate commit | 自动（产生候选包） |
| **M-2 门禁实测** | §4 全部候选态门禁执行 + 既有基线 FAIL 分类披露（governance health 117 基线——Check 10 M5 ×1 + Check 18c ×4 首个 FAIL 类；pytest 27 failed 存量基线逐类归属；REL-067~073 先例口径） | 自动 |
| **M-3 双审查** | Release Reviewer + Design Reviewer（plan-tracker 登记；**判定面变更 MUST 双审**——W-7/BC-7/①⑧ 规则面 + G3 扩展设计面；REL-071/073 先例 = APPROVED_WITH_NOTES/unresolved_blockers=0 ×2）→ 机器入账 REVIEW-REL-074-*（review-record 路径，禁手写） | 自动（评审链） |
| **M-4 transition 用户授权** | `release_authorized=false → true`；DEC-143 基线（自动推荐 + 用户确认）；授权记录 + DEC 入账。授权后 transition commit：manifest-only 0.79.0.json candidate → released + `rel074-transition` event（integrity / recorded_at）+ 单一 parent = candidate commit；commit 后 `release-ledger --version 0.79.0 --no-remote` 重跑 **NATIVE_RELEASED** | **用户确认（ask_user_question）——发布唯一人工门** |
| **M-5 tag + 原子推送** | annotated tag `v0.79.0`（peel 到 transition commit）→ 原子推送 github-https（master + tag；远端 SHA 精确一致；merge/repeat/wrong-parent 阻断——ADR-010） | 自动（授权后） |
| **M-6 发布后对账** | `check-release --version 0.79.0 --require-changelog --lineage-mode released --release-commit <commit>` 核心门禁 PASS + 既有基线 FAIL 如实披露；`release-ledger --version 0.79.0 --remote github-https` NATIVE_RELEASED PASS（origin SSH 不可达既有环境限制——以 origin 执行须如实报告 UNKNOWN/BLOCKED） | 自动 |
| **M-7 归档触发检测** | `archive.py migrate --auto --dry-run`（0.78.1 发布强制触发器已满足过一次但无可归档数据〔plan-tracker L11〕——0.79.0 发布 + task 增量后大概率触发；报告需归档 → 执行 `--auto` + `verify_workflow.py check-archive-integrity`；失败阻断发布完成——ADR-006/007） | 自动 |
| **M-8 路线图回写** | plan-tracker 工作流版本 → 0.79.0；路线图 0.79.0 行 → 已发布（纪律 8 立即回写）；RISK-044 复评结论落盘 risk-log + 下轮复评点登记；RISK-046/047/048/049 复评处置回写；RISK-036/039 维持打开（2026-09-30，1.0.0 硬阻塞）；DSH preset 时滞迁移说明随发布文档（`git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`） | 自动 |

### 3.1 回滚边界（显式声明——0.77.0/0.78.1 §3.1 先例复刻）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only 可逆） | 常规可逆操作（0.76.0 rollback-plan Reversibility 先例） |
| 已发布 v0.79.0 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（0.76.0 rollback-plan 先例："Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

> **rollback-plan-0.79.0.md MUST 复刻本边界表**（0.77.0 R0 P2-1 先例义务延续）。
> 里程碑纪律（plan-tracker 里程碑段）：里程碑到期 MUST 执行检查；延期 MUST 记录 decision-log。

---

## 4. 发布门禁清单

候选态（M-2）与释放态（M-6）确定性命令（执行路径：`python skills/software-project-governance/infra/verify_workflow.py <cmd>`；0.78.1 release-checklist 实测口径对齐——`docs/release/release-checklist-0.78.1.md` M-2 实录）：

| # | 门禁 | 0.78.1 实测基线（M-2 打包期 2026-09-05；#13/#14 为 M-6 释放态/M-7 实录） | 0.79.0 预期 | 备注 |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASS（13 文件 0.78.1；advisory WARN ×2 分类：host plan-tracker 记录版本 Coordinator 打包后 bump 同型惯例 + 根 CLAUDE.md gitignored 已同步） | PASS（13 文件 0.79.0） | 同型 WARN 惯例延续 |
| 2 | `check-projection-sync --fail-on-issues` | PASS（15 projections） | PASS | 漂移时 `release-projection --write`（--write 后须 rollback journal/原子写入测试证据 + 再次 check PASS——ADR-010） |
| 3 | `check-manifest-consistency` | PASS | PASS | G3 扩展/判定面若触及文件增删 MUST 登记 manifest |
| 4 | `check-cross-references --fail-on-issues` | PASS（零悬空/零废弃/零循环） | PASS | |
| 5 | `verify`（无参） | PASSED | PASSED | 既有基线失败按先例如实披露 |
| 6 | pytest 全量 | 27 failed / 2049 passed / 226 subtests（逐类归属：cleanup manifest-presets 既有〔0.77.0 起结构基线〕+ loop_runtime_claims 既有〔RISK-048〕+ pre_commit_review_evidence SUBFAILED×25 既有〔WSL 基线〕） | 零新增失败（对照 27 存量基线逐类归属） | 入槽项新测试全绿 |
| 7 | `check-governance --summary-only` | **117 issues vs 0.78.0 基线 127（-10，零新增）**；首个 FAIL = 18c 执行包既有 + Check 10 M5 既有登记 | 零新增（对照 117 基线；以打包期实测为准——基线数字漂移惯例，不引用旧值作新声明） | 零 `.governance/` 文件由发布包触碰（治理记录变更由 Coordinator 通道） |
| 8 | `check-injection-contract` | PASS（28 anchors 含 @version-line 动态锚解析 0.78.1；打包期 preset 版本行漏改已修复先例） | PASS | fail-closed；投影/标记面全量核对 |
| 9 | `check-dsh-skills-manifest` | PASS（35/35） | PASS | |
| 10 | `check-release --version 0.79.0 --require-changelog --lineage-mode candidate` | 核心静态门禁 PASS + 基线 FAIL 分类披露（release docs 三件套缺 No-overclaim needles 曾新引入→当场补齐复跑——R0 F-1 先例：三件套 MUST 含 No-overclaim 节） | 同型 | candidate 模式不要求不证明 tag |
| 11 | `release-ledger --version 0.79.0 --no-remote` | NATIVE_CANDIDATE（candidate commit 后） | 同型 | 两阶段：候选态 NATIVE_CANDIDATE → transition 后 NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装为 PASS |
| 12 | `quality-tools` | NOT_RUN 如实记录（Ruff/mypy 未安装——ADR-010 不虚构 PASS） | 同型 | |
| 13 | `check-release ... --lineage-mode released --release-commit <commit>` | 核心门禁 PASS + 既有基线 FAIL 披露（archive integrity 既有 + execution gates〔governance health + unit tests 既有〕——REL-071 基线分类同型） | 同型 | tag/push 后执行；验证本地+远端 tag |
| 14 | `release-ledger --version 0.79.0 --remote github-https` | NATIVE_RELEASED PASS（--no-remote 与 --remote 双证） | 同型 | 远端 = github-https（既有环境限制基线） |

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——0.76.0/0.77.0/0.78.1 先例：以可逆性分析 + 门禁复跑为验证载体，rollback-plan-0.79.0.md 定义全量/部分回滚路径，回滚后复跑 #1/#2/#10 与 `git diff --check`）。

---

## 5. 入出槽裁决表（DEC-172 队列 + 0.78.1 发布实录 + 同窗风险候选）

> **M-0 交互注记（FIX-280 先例 / DEC-172）**：本裁决表为规划建议与 DEC-172 已裁决项的汇总呈现；M-0 终裁与各决策点经 `ask_user_question`（即 AskUserQuestion 工具；DEC-143 交互基线「自动推荐 + 用户确认」）由用户确认。裁决符号：√ = DEC-172/DEC-176 已裁；○ = M-0 待决；● = 已随 0.78.1 发布（从 0.79.0 候选剔除）。（原 ◐「Analyst 并行对账中」占位符号已随 2026-09-08 合并消解——全表现无 ◐ 行。）

> **M-0 裁决记录（2026-09-08，DEC-177）**：本表全部 ○ 行已裁决——①⑧⑨②③⑥ **基线确认**（六项入槽维持 + MINOR 定位 + N=2 延续 + G3 前置解除〔三例活体 0 误报〕 + FIX-279 P2-3 出槽维持 + 搁置项维持）；④ RISK-044 复评 = **缓解分支**（quick-scan 前移评估随 0.79.0 立项——risk-log RISK-044 已转「缓解中」）；⑤ RISK-046 根因修复 **√入槽（P2）** + RISK-049 关闭标准 3 子任务 **√入槽（P1，preset live 冒烟子项须 M7.7 三选一防护）** + RISK-047/048 维持观察 + 五风险随 0.79.0 周期批量复评；⑦ REQ-109/111/113/114 **排除**（转 0.80.0+ 候选）+ 治理漂移对账快速通道档**即刻执行**（DEC-177 ④）+ 核实档随 0.79.0 规划期 + 健康 117 前置诊断 **√入规划期**（只读）。范围核增（quick-scan 评估 / RISK-046 根因 / RISK-049 关闭标准 / 健康前置诊断）按纪律 5/6 随 DEC-177 入账。

> **范围核增（2026-09-09，DEC-181）**：AUDIT-149 诊断（EVD-958）产出后，用户裁决将 **FIX-292——18c~18i 执行包活跃判定谓词对齐**（`_is_incomplete_task_status` 采纳 W-7/BC-7 终态链语义；AUDIT-149 降噪域 N1，预期 -61/117）入槽 0.79.0。判定面变更 MUST 双审（Code+Design）；只消费不改写 `_status_is_completed_cell` 权威语义；与 G3 扩展（FEAT-011）协同。基线口径注记：健康基线以引擎口径 **117** 为准（AUDIT-149 代码级闭合；早前 119 为 FEAT-015 闭环记录写入前的时点值）。

### 5.1 裁决汇总（21 行：DEC-172 ② 0.79.0 承接项 + 搁置维持项 + 0.78.1 已交付剔除行 + 同窗风险/新增候选行）

| # | ID | 范围一句话 | 来源依据（文件+小节） | 裁决 | 版本定位 | M-0 决策点 |
|---|---|---|---|---|---|---|
| 1 | **G3 扩展** | 写时结构看护扩展至 Coordinator 直写 plan-tracker/完成记录路径（新 guard 引擎） | queue-triage-0.78x.md §2.1 #7/§3.2；review-FIX-278-DESIGN-R1.md（W-3 L42-44 + BC-3 L78）；DEC-166；plan-tracker L471 | √ 入槽（DEC-172 ②） | **0.79.0**（L12 新增 B 级自动化能力 / L37 契约面） | **② 前置实绩确认**——Analyst 合并 2026-09-08（A.1#1/D-2；引文行号经 R0 P1-1 勘误校正）：G3 首波 write-guard 活体 0 误报实证**三例**（均 2026-08-26、0.78.0 发布窗口当日——plan-tracker **L255** FIX-279 行「活体验证 TRIAGE-FIX-279/REL-071 0 误报」含 TRIAGE-REL-071/TRIAGE-FIX-279 两例 + **L257** FIX-280 行「TRIAGE-FIX-280（write-guard 活体 0 误报实证）」一例）——**前置观察条件已满足，建议确认解除**；M-0 ② 确认即生效 |
| 2 | **G5** | task-priority-analysis 同会话重复抑制（`--no-cache` 语义或「已分析，推荐未变」提示） | queue-triage-0.78x.md §2.1 #8/§3.2；audit-148-v1-verify-alarm-validation.md L184（-1.7KB/会话量化）；DEC-166；plan-tracker L471 | √ 入槽（DEC-172 ②）；Analyst 合并 2026-09-08（D-1）：⑦终态过滤已随 FIX-288 交付——2026-08-25 收益基线（-1.7KB/会话）待重估，若趋零可缩为 G6 附带项（M-0 呈报选项） | **0.79.0**（L12 主题打包；单项 L13 面如实陈述） | ① 范围总确认（含 G5 收益重估处置） |
| 3 | **G6** | 告警追查预算提示（summary 尾部「详见 \<command\> 获取 full report」收尾行） | queue-triage-0.78x.md §2.1 #9/§3.2；audit-148 L185；DEC-166；plan-tracker L471 | √ 入槽（DEC-172 ②） | **0.79.0**（与 G5 同批；G1 已覆盖主体，剩余收尾面） | ① 范围总确认 |
| 4 | **W-7 / BC-7** | 终态 marker 集扩展（状态格混合终态子类「⏳/🔄 + ✅ 已发布/已关闭」保守漏降级修正——判定面规则修改） | queue-triage-0.78x.md §2.1 #10/§3.2；review-FIX-278-DESIGN-R1.md（N-2/W-7 L20 + §3 BC-7 L82）；version-plan-0.78.0.md §5.1 L133；plan-tracker L471 | √ 入槽（DEC-172 ②） | **0.79.0**（L12 判定规则扩展；需 DEC + 双审） | ① 范围总确认 |
| 5 | **FIX-281 ①** | Check 30 pre-FIX-174 文件式 review 记录历史格式迁移路径（V2×9/V5×2 误判 11 项 FAIL → 历史形状分类 FAIL→WARN） | plan-tracker L262（FIX-281 行①项）；version-plan-0.78.1.md §6.1 ①行/§6.2 方案 A；plan-tracker L470（0.78.1 行「判定面①⑧出槽 0.79.0」）；DEC-176 | √ 入槽（0.78.1 规划建议→发布实录承接确认） | **0.79.0**（L12 判定规则扩展——G2 先例 DEC-169 ③ 同型） | ① 范围总确认；router 宿主持续暴露（EV-071/073 实证） |
| 6 | **FIX-281 ⑧** | Check 30c 合法机器行（REVIEW-/RECO-）白名单/溯源分类升级路径（新增即入 WARN——router 10→13 实证） | plan-tracker L262（FIX-281 行⑧项）；version-plan-0.78.1.md §6.1 ⑧行/§6.2 方案 A；plan-tracker L470；DEC-176 | √ 入槽（同上） | **0.79.0**（L12 判定分类扩展；plan-tracker FIX-281 行定位提示原文「历史格式迁移+30c 分类面或涉判定面 MINOR」） | ① 范围总确认；与 #4 同 Check 30 语义域同批承载（version-plan-0.78.1 §6.2 论证） |
| 7 | **RISK-044 正式复评** | 复评结论 MUST 进本版本（挂载义务，非开发入槽项——quick-scan 秒级子集是否前移随复评裁决） | decision-log DEC-169 ②；risk-log L44（RISK-044 行）；plan-tracker L471（路线图 0.79.0 行「MUST 含复评结论」）；version-plan-0.78.0.md §6.1（复评结构先例） | √ 挂载 MUST（DEC-169 ②） | **0.79.0**（§6 专节；材料已合并 2026-09-08——结论待 M-0 ④ 确认） | **④ 复评结论确认** + ⑥ quick-scan 前移与否 |
| 8 | F-03（e2e 投影决策） | commands/governance.md 投影注册 vs 独立维护声明（决策型） | queue-triage-0.78x.md §2.1 #1/§3.3；DEC-164；DEC-157 ③ | ○ 维持搁置（触发式） | 触发式（下次 e2e 触碰批次或候选打包期落 decision-log） | ⑥ 可选前移（默认维持——无版本驱动） |
| 9 | F-04（npm pack 机器守卫） | `npm pack --dry-run` 断言（0 pyc + 关键文件在包） | queue-triage-0.78x.md §2.1 #2/§3.3；review-FIX-275-CODE-R0.md（F4 L95） | ○ 维持搁置（0.79.x 守卫批次候选） | 0.79.x 守卫批次 | **⑥ M-0 可选**：并入 0.79.0（与判定面/守卫域同窗）or 维持出槽（默认维持——新开发任务，FIX-275 验收已覆盖） |
| 10 | F-04-env（锁模型扩展） | file_locks 环境路径锁扩展（side_effect.blast_radius 非空时真实环境路径入锁判定） | queue-triage-0.78x.md §2.1 #3/§3.3；review-FIX-271-DESIGN-R0.md（F-04 L95）；plan-tracker FIX-274 行 | 维持搁置（独立任务，不进 0.79.0） | 0.78.x+ 独立任务 | 无（安全敏感需锁模型设计审查——不塞窄窗口批次） |
| 11 | F-05 + BC-1（升 FAIL 批次） | R5 词表版本化 + BC-1 备份留痕字段化 + Check 39 升 FAIL | queue-triage-0.78x.md §2.1 #4/§3.3；DEC-160（条件原文）；review-FIX-271-DESIGN-R0.md（F-05 L96/BC-1 L82） | ○ 维持搁置（**升 FAIL 条件结构性不可满足**——DEC-160 锚定「连续 2 个零违规 0.77.x 版本」，0.78.0/0.78.1 均非 0.77.x，累计仍 =1） | 条件挂起（升 FAIL 若修订条件属规则面变更 → MINOR 面） | **⑥ 可选前移**：词表版本化 + BC-1 字段化为独立 PATCH 面小修可随本批（不依赖升 FAIL 条件——queue-triage §3.3 原口径） |
| 12 | FIX-279 P2-3（EVD fallback 残余误报） | 无 TRIAGE 行族旧库 + EVD 首行 <10 列时首次 triage 仍 fail-closed——误报 vs 漏报权衡 | queue-triage-0.78x.md §2.1 #14/§3.3；review-FIX-279-CODE-R0.md（P2-3 L60）；DEC-168 | ○ 维持搁置（0.79.x 专项评估） | 0.79.x 专项评估 | **③ M-0 裁决**：专项评估并入本版 or 维持出槽（权衡需独立 DEC——默认维持） |
| 13 | FIX-279 P3×3 | 重复行/排序场景/注解/边缘断言测试候选 | queue-triage-0.78x.md §2.1 #14/§3.3；review-FIX-279-CODE-R0.md（P3-1~3 L61-63） | 维持搁置（观察池） | 随下轮触碰归并 | 无 |
| 14 | N-P3-2/3/4 + DESIGN N-3~N-5 + 前轮 P3-2/P3-4 | Check 19 谓词不同源（N-P3-2 若实施 = 判定面对齐评估）/ 规则交互边界 / 簿记边角 / 组合测试建议 | queue-triage-0.78x.md §2.1 #13/§3.3；review-FIX-278-CODE-R1.md + DESIGN-R1.md | 维持搁置（观察池） | 随下轮触碰归并 | 无（N-P3-2 实施前需判定面评估——登记维持） |
| 15 | 0.78.1 已交付项（修复/守卫/测试/规划产物全链） | DEC-171/FIX-282 + FIX-283（N-P2 批+四步）+ FIX-285（F-3+F-01）+ FIX-287（②③④）+ FIX-288（⑨⑦）+ FIX-289（⑤⑥）+ FIX-290 + FIX-272 P2×2（随 FIX-286/284）+ REL-072/073 产物 | plan-tracker L470（0.78.1 行发布实录）；CHANGELOG.md 0.78.1 节（L9 commit 清单）；release-checklist-0.78.1.md Scope | ● 已发布（2026-09-05）——**从 0.79.0 候选剔除** | 已交付（不占 0.79.0 范围） | 无（Analyst 对账的剔除基线——本行即对账锚点） |
| 16 | RISK-046 根因修复候选 | 派发锁写入前路径存在性校验 + 与同期 change-triage 记录 files 交叉核对（可作 verify_workflow 新 check 或 dispatch 模板强制步骤） | risk-log L46（RISK-046 行缓解列原文：「根因修复候选（观察项，**0.78.1 后评估入槽**）」+ 复评列「2026-09-30（下轮版本规划复评，与 RISK-044 同窗）」） | ○ 待 M-0（0.78.1 后评估时点 = 本规划） | 0.79.0 候选（若入槽：verify_workflow 新 check = L34 PATCH 面增量 / dispatch 协议变更 = L12 能力面——按实现面定级，M-0 呈报） | **⑤ 同窗复评处置 + 入槽评估** |
| 17 | RISK-047 后续候选 | evidence 行替换语义 或 CLI --force 旗标（DEC-174 后续动作） | risk-log L47（RISK-047 行：「后续候选任务…（DEC-174 后续动作）」+ 复评列 2026-09-30 同窗） | ○ 待 M-0（默认维持观察；Analyst 报告〔2026-09-08〕无 RISK-047 相关新事实记载——「无触发再评估证据」为对报告空缺的显式推断，非报告结论；批量复评建议来自 Analyst 报告 C.3-5） | 0.79.x 候选（默认维持观察） | ⑤ 同窗复评处置 |
| 18 | RISK-048 后续候选 | 计时断言去环境化（FIX-240 先例：进程级计时/阈值分级）或 skip-under-load 标注 | risk-log L48（RISK-048 行候选列 + 复评列 2026-09-30 同窗） | ○ 待 M-0（默认维持观察；pytest 27 failed 存量基线中 test_loop_runtime_claims 类归属依赖本项——此归属出自本规划 §0/release-checklist-0.78.1.md L24，非 Analyst 报告；批量复评建议来自 Analyst 报告 C.3-5） | 0.79.x 候选（默认维持观察；pytest 门禁基线逐类归属依赖本项状态） | ⑤ 同窗复评处置 |
| 19 | RISK-049 关闭标准候选任务 | (1) 适配器面 claim→evidence 等级映射（live-session/isolation/static 三级，README check 扩展）；(2) preset 会话 live 冒烟门禁（headless 或受控真实会话）；(3) dsh 升级回归清单固化为 release gate 一部分 | risk-log L49（RISK-049 行关闭标准列原文：「关闭标准（候选任务 **0.78.x/0.79.0 入槽评估**）」+ 复评列 2026-09-30 同窗） | ○ 待 M-0（risk-log 明示 0.79.0 为入槽评估时点之一） | 0.79.0 候选（若入槽：(1) 为新 check = L34 面 + README 宣示面；(2) 涉及受控真实会话 = M7.7 真实环境防护三选一约束——**需隔离协议设计**，FIX-271/RISK-045 先例） | **⑤ 同窗复评处置 + 入槽评估**（高优先风险——不关闭不等于不推进关闭标准） |
| 20 | REQ-109/111/113/114 草案 + 治理数据漂移对账批 | Analyst 合并结论（2026-09-08，A.4-N4/N6 + B.2/B.3）：**(a) REQ 四草案 → 建议不入 0.79.0**（主题不符——交互可追溯/注入面/hook 前移/loop 接线 ≠ 降噪/判定面主题；立项窗错过至少一次有据（0.75.0 候选——L612-617 仍草案 vs L463 已发布）且自 2026-08-17 起持续草案未立项；M-0 若纳入任一项 = 范围核增走纪律 5/6 + DEC）；**(b) 治理数据漂移对账批 → 拆两档**：快速通道档（Coordinator 直写 M1.2——REL-073 行回写 ✅/FIX-281 行进度注记〔7/9 已交付+①⑧落点〕+ **REL-002 data gap 注记**〔blocked_by 消歧——version-plan-0.78.1 §6.3「申报通道关联，非执行前提」口径〕+ **依赖环 AUDIT-146↔FEAT-010 边注记**〔FIX-237.2 容忍基线〕/REQ 矩阵三族+REQ-110/112 回写/项目总览统计刷新；不占版本范围、L40-46 不驱动 bump，建议即刻执行）+ 核实档（路线图 0.66.2/0.67.0~0.70.0 行回写 + 0.71.0/0.72.0 补行——需逐版本 release 事实核对〔L466「不凭记忆编造」〕，建议 0.79.0 规划期承载） | Analyst 对账报告 A.4-N4/N6 + B.2/B.3（行号：plan-tracker L263/L262/L549-554/L563-567/L618-624/L613/L615/L44/L456-460/L466） | ○ 待 M-0（⑦ 裁决：(a) 排除确认 + (b) 两档处置确认） | (a) 0.80.0+；(b) 快速通道档即刻（治理记录面）+ 核实档 0.79.0 规划期 | **⑦ 合并后新增候选裁决** |
| 21 | 健康 117 issues 构成诊断（收敛前置） | Analyst 合并结论（2026-09-08，A.4-N5 + B.2）：会话事实仅披露首项（Check 10 M5 ×1 + Check 18c ×4），其余 ~112 项构成**待诊断**——建议健康检查域收敛前置诊断（示意 AUDIT-149，只读）入 0.79.0 规划期（M-0 前或并行），输出适合降噪的检查域清单衔接 G 组主题；Check 10 M5 ×1 可先按 FIX-280 先例定位（是否同型待验证）；修复项按诊断结论另行定入槽 | Analyst 对账报告 A.4-N5 + B.2；plan-tracker L11（2026-09-08 实测注记）；release-checklist-0.78.1.md L25 | ○ 待 M-0（⑦ 裁决：诊断任务入 0.79.0 规划期确认） | 0.79.0 规划期（诊断只读；修复项按结论定级） | ⑦ 合并后呈报 |

> **覆盖核对**（queue-triage-0.78x.md §3.2 0.79.0 候选 5 项 → 本表映射）：G3 扩展→#1；G5→#2；G6→#3；W-7/BC-7→#4；RISK-044 复评挂载→#7。**§3.3 搁置 9+1 项**：F-03→#8；F-04→#9；F-04-env→#10；F-05+BC-1→#11；RISK-044 quick-scan→#7（复评联动）；FIX-279 P2-3+P3×3→#12/#13；N-P3-2 等→#14。**0.78.1 version-plan §5.1 已裁决行承接**（本句「其 #n」= **0.78.1 §5.1 表空间**，「本表 #n」= 本表空间——映射经 0.78.1 §5.1 实文核验 2026-09-08）：其 #11~#14（G3/G5/G6/W-7「√ 出槽维持→0.79.0」）→ **本表 #1~#4** 入槽承接；其 #15（RISK-044 quick-scan「√ 搁置维持」+ 复评挂 0.79.0 MUST）→ **本表 #7**（复评挂载行）；其 #16~#21（搁置维持组：F-03/F-04/F-04-env/F-05+BC-1/FIX-279 P2-3+P3×3/N-P3 组）→ **本表 #8~#14** 维持搁置；其 #22 判定面拆分（①⑧）→ **本表 #5/#6** 入槽承接；其 #1~#10 缺陷面 → 已全部随 0.78.1 发布（**本表 #15** 剔除锚点）。「搁置 9+1 项」分解：9 项 = queue-triage §3.3 搁置组（本表 #7 quick-scan 复评联动 + #8~#14 承载，含合并计行）；+1 = F-3 额外行——**已随 FIX-285 于 0.78.1 交付（本表 #15 已列），非本表新增承载行**（Analyst 报告 D-3 的范围外发现登记）。**新增行**（0.78.1 发布后新事实）：#16~#19（RISK-046/047/048/049 同窗复评与候选——risk-log 各行复评列/候选列原文支撑）、#20/#21（Analyst 并行对账占位——plan-tracker REL-074 行分工描述支撑）。零编造：每行来源留痕。

### 5.2 裁决后 0.79.0 范围预判

- **基线范围（DEC-172 ② 已定，无需再裁）**：#1~#6 六项 + #7 复评挂载——降噪第二波/规则判定面批。
- **M-0 变量叠加后**：+ RISK-046 根因修复 / RISK-049 关闭标准子项（若 ⑤ 裁决入槽）；+ F-04 / F-05 子项（若 ⑥ 裁决前移）；+ Analyst 合并新增候选（⑦）——**⑤/⑥/⑦ 三支入槽分支均为范围核增路径，统一走纪律 5/6（M-0 裁决 + DEC 入账 + 路线图行更新，M-1 执行）**。
- **任何组合下 MINOR 定位论证**：见 §2——基线范围已锁定 L12 三支触发；叠加项按各自面级如实陈述（PATCH 面增量不削弱 MINOR，规则/能力面增强 MINOR）。

---

## 6. RISK-044 正式复评挂载（DEC-169 ② MUST——复评结论 MUST 进本版本）

> **M-0 交互注记（FIX-280 先例）**：本节复评结论建议经 `ask_user_question`（DEC-143 基线）呈用户裁决；复评材料**已合并**（2026-09-08——Analyst C 节 + Coordinator 4 样本实测），结论建议见 §6.2。

### 6.1 挂载义务与背景口径

- **义务来源**：DEC-169 ②（decision-log）——0.79.0 版本规划 MUST 含 RISK-044 正式复评结论；路线图 0.79.0 行原文「RISK-044 正式复评挂载（DEC-169 ② MUST 含复评结论）」（plan-tracker L471）。
- **风险现状**（risk-log L44，零编造）：已接受（DEC-149——接受 31s 每会话一次性成本，完整看护优先于秒级体验；REQ-145.7 验收修订「单次 <60s 且每会话仅一次」）；2026-08-26 检查点复核通过（维持，DEC-167——FIX-278 后实测 32.8s/29.6s 满足修订验收）。
- **口径澄清**（version-plan-0.78.1 §0 同论证）：risk-log 行「下轮复评 = 下次版本规划（0.78.x）」字样为 DEC-167 时点表述；decision-log DEC-169 ② 为权威口径 = **0.79.x 版本规划（本次）**。

### 6.2 复评判定路径（材料已合并 2026-09-08）

| 复评输入 | 状态 | 来源 |
|---|---|---|
| 0.78.1 后 `--summary-only` 墙钟实测值 | **已实测（Coordinator 2026-09-08 会话，4 样本）**：负载态（两 subagent 并行时）65.7s / 61.3s；空闲态 64.7s / 56.6s——4 样本中 3 超 60s 修订验收线，较 DEC-167 基线 32.8s/29.6s 抬升约 1.7~2×；样本波动大（空闲双样本即分裂 64.7/56.6），环境因素（会话宿主/IO）未隔离 | Coordinator 会话实测（2026-09-08，Measure-Command 双轮 ×2）；DEC-167 基线（risk-log L44） |
| 用户延迟反馈（2026-08-26 检查点后是否有新反馈） | 治理记录中未检索到新反馈记载（risk-log/decision-log 2026-08-26 后无 RISK-044 相关用户反馈）——**M-0 时向用户直接确认**（会话事实，文件不可查证） | Analyst 报告 C.3-2；risk-log RISK-044 触发列 |
| quick-scan 候选状态 | 维持出槽（DEC-164 收窄/DEC-167 维持——无新裁决记录）；本复评若走缓解分支则前移评估 | risk-log L44；queue-triage §2.1 #6 |

**复评结论（M-0 ④ 已裁决 2026-09-08——DEC-177 ②：缓解分支，quick-scan 前移评估随 0.79.0 立项；材料与建议保留如下供追溯）**：

1. **实测判定**：4 样本 3 超 60s 修订验收线 + 较基线抬升 1.7~2× → **倾向触发缓解分支评估**（Analyst C.4 路径②：quick-scan 前移立项评估）；但样本波动大（56.6~65.7s 区间）且环境未隔离——**备选：先做受控复测（静态环境 3~5 样本）再判**，避免单日噪声驱动规则变更。
2. **判定路径**（Analyst C.4 三分支）：维持接受（需实测 <60s + 无用户反馈——当前证据不支持）/ **缓解（quick-scan 前移评估——证据倾向此分支）** / 关闭（无证据基础，不建议预判——Analyst C.4 明示）。
3. **同窗联动（Analyst C.3-5 建议）**：RISK-046/047/048/049 复评截止均 2026-09-30 且 risk 行自标「与 RISK-044 同窗」——建议 M-0 ⑤ 批量复评处置（单独分批 = 重复打断）；域辨析（Analyst C.3-6）：RISK-049「preset 会话 /governance 失效」属宣示-vs-验证等级域，不得误作 RISK-044 延迟域升级依据（反向亦然）。
4. **RISK-036/039 不受本复评影响**（独立关闭标准，2026-09-30——本节边界）。

### 6.3 同窗复评披露（RISK-046/047/048/049——risk-log 复评列原文）

四项风险复评窗均登记「2026-09-30（与 RISK-044 同窗）」= 下轮版本规划时点（本规划）。处置路径：§5 #16~#19 各行（根因修复/关闭标准候选入槽评估 + 观察维持）；M-0 ⑤ 统一呈报；M-8 复评处置回写 risk-log。**复评结论不预判**——材料已合并（2026-09-08），结论待 M-0 ⑤ 裁决。

---

## 7. 风险披露

| 风险 | 状态 | 0.79.0 处置 |
|---|---|---|
| RISK-036（official marketplace operations） | **打开**（2026-09-30；1.0.0 硬阻塞） | 0.79.0 **不关闭**；不声明 official/marketplace approval |
| RISK-039（ArchGuard external validation / 治理数据膨胀看护） | **打开**（2026-09-30；1.0.0 硬阻塞） | 0.79.0 **不关闭**；不声明 universal/full runtime support |
| RISK-044（`--summary-only` 墙钟） | 已接受（DEC-149；DEC-167 检查点通过） | **正式复评挂载本版**（§6——DEC-169 ② MUST）；材料已合并（2026-09-08）——结论待 M-0 ④ 确认 |
| RISK-046/047/048/049 | 打开（复评窗 2026-09-30 与 RISK-044 同窗） | §6.3 披露 + §5 #16~#19 入槽评估；RISK-049 关闭标准子项若涉受控真实会话 = **M7.7 真实环境防护三选一约束**（隔离环境/完整备份+校验/用户逐项授权——RISK-045/FIX-271 隔离协议先例，缺一禁止执行） |
| 判定面变更风险（W-7/BC-7 + ①⑧ + G3 扩展） | 规则/判定面修改 = 行为影响面大 | MUST DEC + 双审（Release + Design Reviewer——G2/DEC-166 先例）；fail-safe 边界锁定惯例（ACTIVE/真实 nonzero 恒 FAIL 不可破——降级方向仅限历史形状/保守漏降级修正）；G3 扩展前置实绩确认（M-0 ②） |
| 既有健康基线 | governance health 117 issues（2026-09-08 时点值） | 候选/释放态按 REL-067~073 先例**如实分类披露**（A/B 对照零新增）；基线数字漂移惯例——打包期以实测为准 |
| DSH preset 时滞 | 已知（0.77.0 起先例） | 迁移说明随发布文档（M-8）；不宣称未 sync 安装的会话级效果 |
| Analyst 并行对账合并风险 | 对账可能修正 §5 行（新增候选/剔除项/复评材料） | **已合并（2026-09-08）**：◐ 占位行全部消解（#17/#18/#20/#21）+ §6.2 复评材料填充 + #1/#2 行注记（G3 前置解除 / G5 收益重估）；范围核增走纪律 5/6（M-0 ⑦） |

---

## 8. No-overclaim 边界

本规划（及后续 0.79.0 候选）**不声明**：

- 1.0.0 production-ready / 1.0.0 正式发布 / 1.0.0 readiness
- official approval / marketplace approval / curated listing
- universal / full runtime support
- **RISK-036 / RISK-039 关闭**（对齐 0.78.1 CHANGELOG Boundaries 措辞纪律——各自独立关闭标准未满足）
- **RISK-049 关闭**（关闭标准候选任务仅处于入槽评估——risk-log 明示为候选，非已交付）
- **RISK-044 复评结论**（复评材料已合并 2026-09-08——结论待 M-0 ④ 用户确认；本规划仅出建议与选项路径）
- RISK-046/047/048 复评结论（同窗复评待处置——§6.3）
- FIX-281 ①⑧/W-7/BC-7/G3 扩展/G5/G6 已实现或已修复（M-0 裁决前仅存在规划建议；任务未注册未开发）
- Analyst 对账结论已合并（2026-09-08），但其性质为**评估建议**——全部候选的入槽终裁权在 M-0 用户（本规划不预设裁决）
- 任何历史已发布 version tag 的状态变更（v0.78.1 及之前未受本版影响）

并**不创建、不证明** `v0.79.0` tag 存在（candidate-only；`release_authorized=false`——transition/tag/push 待用户授权 M-4，DEC-143 基线）。0.79.0 主线语义 = 降噪第二波/规则判定能力批（G3 扩展/G5/G6/W-7/BC-7/①⑧ + RISK-044 复评挂载），不关乎官方收录/市场批准/1.0.0 就绪。

---

## 9. 待验证项与观察项（显式标注——无事实源支撑的内容禁止假设成事实）

1. **HEAD commit 窗口（待验证→M-1 核定）**：`v0.78.1..HEAD` 窗口内 commit 清单未在本次规划内核对（Release Agent 本次零命令执行——角色工具权限约束，非事实缺口）；M-1 MUST `git log v0.78.1..HEAD --oneline` 核定（§0 待验证项①闭环——0.78.1 规划 §0/§9 同型先例）。
2. **RISK-044 复评输入材料（已合并 2026-09-08）**：墙钟实测 4 样本（§6.2——65.7/61.3 负载态 + 64.7/56.6 空闲态，3/4 超 60s 线，波动大）；用户反馈状态待 M-0 直接确认（治理记录无新反馈记载）。若 M-0 选择受控复测先行 → 复测为新增待验证项（静态环境 3~5 样本）。
3. **G3 扩展前置实绩（已合并 2026-09-08→M-0 ②）**：queue-triage §2.1 #7 前置条件「先观察 G3 首波实绩（BC-6 自愈面验证）」——实证锚点（R0 P1-1 勘误后）= plan-tracker L255（TRIAGE-REL-071/TRIAGE-FIX-279 两例 0 误报）+ L257（TRIAGE-FIX-280 一例）共三例活体 0 误报；建议解除前置观察。残余待验证：三例样本量是否充分 = M-0 ② 用户判断项（非文档缺口）。
4. **REQ-109/111/113/114 草案 + 治理数据漂移明细 + 健康 117 构成（已合并 2026-09-08→M-0 ⑦）**：§5 #20/#21 已按 Analyst A.4/B.2/B.3 结论填充——REQ 四草案建议 0.80.0+；漂移对账拆快速通道档（即刻）/核实档（0.79.0 规划期）；健康 117 建议前置诊断（AUDIT-149 示意）。剩余待验证：其余 ~112 项构成明细（诊断任务产出）与 G5 收益重估（Analyst D-1：⑦落地后 -1.7KB 基线不再必然成立）。
5. **FIX-281 ①⑧ router 实证细节复核（待验证→入槽任务化时）**：router EV-066/EV-071/073 申报材料中的行号/计数（0.78.1 时点插件侧代码已变——FIX-287 等已合入）——拆分任务执行时按当时代码核对（version-plan-0.78.1 §9.4 行号复核惯例延续）。
6. **基线数字漂移（惯例提醒）**：governance health 117 / pytest 27 failed 均为 2026-09-05~09-08 时点值——0.79.0 打包期以实测为准，不引用旧值作新声明（0.76.0 checklist 先例）。
7. **AUDIT-146↔FEAT-010 cycle WARN**：既有容忍基线（FIX-237.2）——维持登记，本规划不新增动作（0.78.1 规划 §9 同口径）。
8. **0.66.2 行状态 / 0.71.0/0.72.0 缺行**（历史观察项——version-plan-0.78.1 §9.1/9.2 登记）：0.78.1 M-8 是否已处置未见记录——维持登记，不凭记忆判断状态；如有回写需求由 Coordinator 独立处理（治理记录面，不占 0.79.0 范围）。

---

*本文档为 REL-074 版本规划产物（Release 撰写 + Analyst 对账 + Coordinator 合并，2026-09-08 定稿）。下一站：规划期双审（Release Reviewer + Design Reviewer）→ M-0 用户裁决 → 入槽项任务化 → M-1 候选打包（后续工作单元）。*
