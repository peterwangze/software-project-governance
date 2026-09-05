# Version Plan - 0.78.1

**Version**: 0.78.1 (PATCH — proposed by this plan, subject to user confirmation)
**Release**: DEC-172 裁决 A 修复/清理/测试卫生批——DEC-171 + N-P2-1 + N-P2-2 + N-P3-1 + FIX-279 P2-1/P2-2 + F-01 + change-triage 措辞 + F-3（新登记）+ FIX-272 P2×2（可选）；FIX-281 子集落点 = M-0 新决策点（§6）
**Date**: 2026-08-27
**Plan task**: REL-073（版本规划——规划先行惯例，REL-071/REL-072 先例；候选打包为后续工作单元，本次不做）
**Status**: 规划建议文档。`release_authorized = false`——transition / tag / push 待用户授权（DEC-143 交互基线：自动推荐 + 用户确认；M-4 唯一人工门）
**Produced by**: Release Agent（REL-073 规划段）；本文档只读规划 + 仅写入 `docs/release/version-plan-0.78.1.md`，未触碰版本文件/产品代码/`.governance/`

---

## 0. 规划基线事实（治理记录核验，零编造）

| 事实 | 值 | 来源（留痕） |
|---|---|---|
| 已发布基线 | 0.78.0（2026-08-26；FIX-278+FIX-279+FIX-280）——transition `afb959d` + tag `v0.78.0`（65eb6b4f，peel=afb959d）已推送 github-https | plan-tracker L458（路线图 0.78.0 行）/ L258（REL-071 行 M-5~M-7）；DEC-170（授权） |
| 工作流版本 | 0.78.0 | plan-tracker `工作流版本`；TRIAGE-REL-073.json `"current": "0.78.0"` |
| HEAD | `afb959d`（任务书基线；0.78.0 transition commit）。**待验证**：0.78.0 之后的治理/docs 变更（REL-072 报告入库 + EVD-909 + plan-tracker 回写 + FIX-281 行 + TRIAGE-REL-073/REL-073 入账 + 本规划文档）的 git commit 状态未在本次规划内核对（Release Agent 本次零命令执行）——M-1 候选打包期 MUST `git log v0.78.0..HEAD --oneline` 核定窗口全量 commit | 任务书基线；queue-triage-0.78x.md §0（基线事实同源） |
| 版本序列 | v0.78.0 → v0.78.1（PATCH 路径，不跳号；无中间版本） | plan-tracker 路线图 L458-459；TRIAGE-REL-073.json version_chain |
| 版本号预留核对 | 路线图 0.78.1 行已预留（状态=规划中）：「0.78.0 后修复/清理/测试卫生批（PATCH，零行为面）」——本规划内容与该行 DEC-172 给定范围**一致**；FIX-281 子集若入槽 = **范围核增**（纪律 5/6：M-0 裁决 + DEC 入账） | plan-tracker L459；VERSIONING.md L121-131（纪律规则 1-8） |
| 出槽队列裁决 | DEC-172（2026-08-26，REL-072 用户裁决 A 两段式）：0.78.1 PATCH 入槽 10 行（9 确定 + 1 可选）+ 0.79.0 MINOR 主题批 + 搁置 9+1 项维持 | decision-log L181（DEC-172）；queue-triage-0.78x.md §3/§5；plan-tracker L259（REL-072 行） |
| FIX-281 申报批次 | 宿主 B 类缺陷 9 项（router 实证），2026-08-27 机器入账（TRIAGE-FIX-281）——**DEC-172 之后新增**，落点未裁决（本规划 §6 评估，M-0 呈报） | plan-tracker L262（FIX-281 行）；TRIAGE-FIX-281（机器入账 2026-08-27） |
| 任务面快照 | 176 任务 175 完成；唯一活跃 = FIX-281（P1，blocked_by=[REL-002]——跨仓任务族依赖，本仓无行 data gap，tpa fail-closed 显示）；REL-073（本任务）规划中；既有 cycle WARN（AUDIT-146↔FEAT-010，FIX-237.2 容忍基线） | TRIAGE-REL-073.json snapshot（task-priority-analysis 2026-08-27） |
| 入槽项任务注册状态 | DEC-172 全部入槽项（含 F-3/FIX-272 P2×2）**均未注册任务行**（tpa unblocked=[]）——M-0 裁决后、M-1 启动前 MUST 完成 triage 机器入账 + 注册 + Developer/Reviewer 链（N=2 会话上限，DEC-163 惯例；DEC-172 后续动作栏原文要求） | decision-log L181（DEC-172 后续动作）；TRIAGE-REL-073.json snapshot |
| 既有健康基线 | governance health **127 issues**（0.78.0 发布后实绩；首个 FAIL = 18c 执行包既有基线——非候选引入） | plan-tracker L258（REL-071 行 M-7/M-8 实绩） |
| 版本适配 WARN | TRIAGE-REL-073 入账时 `planned_next=0.66.2` advisory WARN（版本链解析器把 0.66.2 行「补偿发布规划中」识别为下一未发布版本）——**既有登记漂移**，见 §9 观察 1 | TRIAGE-REL-073.json version.issues |
| RISK 状态 | RISK-036/039 打开（2026-09-30，1.0.0 硬阻塞）；RISK-044 已接受（DEC-149/167 检查点通过）——正式复评挂 **0.79.0**（DEC-169 ② / DEC-172；risk-log 行「0.78.x」字样为 DEC-167 时点表述，以 decision-log 后续裁决为权威口径） | risk-log L42/L43/L44；decision-log L7（DEC-169 ②）/L9（DEC-167）/L181（DEC-172） |

**窗口 commit 清单**：待 M-1 候选打包期 `git log v0.78.0..HEAD` 核定（0.78.0 后已知治理/docs 面变更：REL-072 评估报告 + 治理回写 + FIX-281/TRIAGE-REL-073 入账 + 本规划文档——多数属 VERSIONING.md L40-46 不驱动 bump 的治理记录面，随候选打包统一入窗）。

---

## 1. Release Scope

### 1.1 DEC-172 裁决 A 已定入槽项（10 行 = 9 确定 + 1 可选）

| # | ID | 内容 | 类别 | 来源（留痕） |
|---|---|---|---|---|
| 1 | **DEC-171** | commit-msg Step 3 字面量匹配缺陷——`grep -q "\| $TASK_ID \|"` 对加粗 ID 行永不匹配（REL-071 transition 被迫 `--no-verify`；REL-072 同型暴露）；修复面 = infra/hooks/commit-msg L234 正则容忍加粗（或去 markdown 加粗后匹配）+ .git/hooks 一次性重装 | 检查器缺陷修复 | decision-log L180；queue-triage §2.2 #17（实测 0 命中留痕）；plan-tracker L258 |
| 2 | **N-P2-1** | `_legacy_blocker_keys` 重复定义死代码遮蔽（review_domain.py:1613-1628 旧实现 vs :1680-1684 委托版）——纯删除 | 清理 | review-FIX-278-CODE-R1（N-P2-1）；queue-triage §2.1 #11 |
| 3 | **N-P2-2** | 两处惰性 `parse_completed_task_ids` 注入（test_verify_workflow.py:15264-15268 + :15418-15421）——mock 失效死注入，与 :14884 对齐 | 测试卫生 | review-FIX-278-CODE-R1（N-P2-2）；queue-triage §2.1 #12 |
| 4 | **N-P3-1** | docstring 160→130 纯注释修正（行为限值已正确） | 注释修正 | review-FIX-278-CODE-R1（N-P3-1）；queue-triage §2.1 #13 |
| 5 | **FIX-279 P2-1** | 写入行缺失路径 → 显式 issue 的回归测试（FIX-279 契约组件无防护，P-v1 原则 4） | 测试卫生 | review-FIX-279-CODE-R0（P2-1）；DEC-168；queue-triage §2.1 #14 |
| 6 | **FIX-279 P2-2** | remediation 定位标准行来源（消息不提示标准行可能为历史旧行；与 docstring 范围契约张力） | UX 消息/文档 | review-FIX-279-CODE-R0（P2-2）；queue-triage §2.1 #14 |
| 7 | **F-01** | README L204 引号非逐字（引号纪律；与 SKILL L272 非逐字）——宣示面保真 | 文档小修 | plan-tracker FIX-276 行；queue-triage §2.1 #15 |
| 8 | **change-triage「四步」措辞陈旧** | SKILL 描述陈旧（实际五步——FIX-271 引入第五步「执行副作用声明」）；1 行措辞 | 文档措辞（skill 面 = L13/L33 PATCH） | plan-tracker FIX-271/FIX-273 P3-3；version-plan-0.77.0.md §8 观察 2；queue-triage §2.1 #16 |
| 9 | **F-3**（新登记） | bootstrap 标记面无机器守卫——扩展 check-version-consistency 或新增 check-bootstrap-markers（一次性成本低；DESIGN-R0 范围外发现） | 新增守卫（检查项） | review-REL-071-CANDIDATE-DESIGN-R0（F-3 L79-84）；queue-triage §3.3 额外行；DEC-172（登记 0.78.1 候选） |
| 10 | **FIX-272 P2×2**（**可选**） | F1 路径穿越测试 3 例 + F2 穿越/畸形诊断消息拆分——安全无缺陷（14/14 探针验证），P2 仅为回归锚定 + 诊断可操作性；**入槽前须单独 triage 机器入账**（DEC-172 后续动作栏） | 测试+诊断 | review-FIX-272-CODE-R0（F1 L97 / F2 L98）；queue-triage §2.1 #5 |

### 1.2 FIX-281 子集（M-0 新决策点——本规划 §6 评估，未预定入槽）

FIX-281（宿主 B 类缺陷申报批次，router 实证 9 项）于 DEC-172 之后入账，落点待 M-0 裁决。本规划评估建议（§6）：**拆两段**——缺陷修复面子集（②③④⑤⑥⑦⑨）入 0.78.1，判定规则面子集（①⑧）入 0.79.0（与 W-7/BC-7 同批）。该子集若入槽 = 0.78.1 范围核增（纪律 5/6 + DEC 入账）。

### 1.3 范围特征与任务化结构

- **范围特征（DEC-172 裁决 A 原文口径）**：全部确定入槽项为 P2/P3 修复、清理、测试卫生、文档措辞、检查器缺陷、守卫标记面——**零行为语义变更**（无判定规则修改、无 agent 协议变更、无 SKILL MUST 规则新增；F-3/DEC-171 为检查器面增改，按 L13/L34 PATCH 面如实陈述——见 §2）。
- **任务化结构**（M-0 裁决后、M-1 前执行；编号由 change-triage 机器分配，本规划不预设）：按域分组注册，预计 4~6 个任务——DEC-171 独立（hook 修复 + 安装面重装确认 + manifest/投影检查）；N-P2 批 + N-P3-1 + 四步措辞（review_domain/test/change-triage SKILL 同域）；FIX-279 P2-1/P2-2（write-guard 域）；F-01 + F-3（文档 + 守卫，可同任务或分立）；FIX-272 P2×2（若入槽，独立 triage）；FIX-281 拆分子任务（若入槽，见 §6.4 执行结构）。每任务 TDD + Developer/Reviewer 链（SoD：Developer 不审查自己的代码）。
- **90% 完成率（纪律 7）**：全部入槽任务 ✅ 完成 + 审查终态（APPROVED 或 unresolved_blockers=0）后方可 M-1；超 N=2 会话上限自动出槽登记后续版本（DEC-163 惯例，DEC-169 ④ 延续）。

---

## 2. Version and SemVer（PATCH vs MINOR 论证）

**结论：PATCH（0.78.0 → 0.78.1，不跳号）。**

| 判据 | 事实 | 结论 |
|---|---|---|
| 纯 bug 修复（VERSIONING.md L38） | DEC-171（检查器匹配缺陷——实测误报，修复 = 匹配面扩大至真实数据现状，任务必须存在语义〔M7.5〕保留）、N-P2-1（纯删除死代码）、N-P2-2（测试注入对齐）、N-P3-1（注释）、FIX-279 P2-1/P2-2（测试 + 消息，不改行为语义）、F-01（引号，L45-46 本身不驱动 bump）、四步措辞（1 行文档）——全部「仅修复 bug（不改变行为语义）」 | → **PATCH 主体** |
| 检查项/守卫新增 = PATCH 面明列（L13/L34） | F-3（bootstrap 标记面守卫 = verify_workflow.py 新增检查项——L34 明列 PATCH）；FIX-272 P2×2 若入槽（回归测试 + 诊断消息拆分 = 测试卫生 + 用户可见小改，L13 PATCH 面） | → PATCH 面增量**如实陈述**（0.77.0 先例口径：不作判级依据亦不构成 MINOR 提升） |
| 计划外变更走 PATCH（L123 纪律 2） | 出槽队列全部项均为 0.78.0 范围外项 → PATCH 路径承载，不占用 0.79.0 MINOR | → PATCH |
| Patch 细粒度纪律（L19-21） | 修复批已完成评估且用户已裁决（DEC-172）——应立即 0.78.1 出，不攒到 0.79.0（DEC-172 未选方案 B 的理由原文：违反 L19-21） | → PATCH |
| 无 MINOR 触发项（L12/L37 反证） | 入槽确定项中无新增 MUST 规则 / 无新子工作流或 skill / 无判定规则扩展——G3 扩展、G5、G6、W-7/BC-7（规则/判定面）已由 DEC-172 裁决出槽 0.79.0 | 非 MINOR |
| 无 BREAKING CHANGES | 全部入槽项零行为语义变更（§1.3）；无接口删除/重命名、无默认行为破坏、无 governance 模板字段变更 | 非 MAJOR |
| FIX-281 子集落点条件论证 | **②③④⑨**（解析器硬编码矛盾/节边界/括号匹配/版本校验事实源）= L38 缺陷修复（恢复设计语义：本就该按 profile 列数解析/读全节/匹配括号节名/用项目当前版本）→ PATCH 成立；**⑤**（review_record 覆盖守卫）= 防数据破坏守卫新增（P7 风险防护）→ 按 L13/L34 类比 PATCH 面增量如实陈述（保守可移 0.79.0）；**⑥**（前缀约定映射说明）= 文档面 → PATCH；**⑦**（tpa 终态过滤）= 输出正确性缺陷修复（M7.4 step 6「完成必推荐」语义本就不含终态任务——router 实证 4 项终态仍列 Top pick = 误导空原因判定）→ L38 论证成立（保守可移 0.79.0：与 G5 同工具判定域）；**①⑧**（Check 30 历史格式迁移 + 30c 机器行分类）= 判定分类规则扩展——**G2 L-A/L-B/L-C 先例**（DEC-169 ③ 定性「G2 判定规则 = 行为/规则面显著变更」支撑 0.78.0 MINOR）→ 若并入 0.78.1 则与本仓先例自相矛盾，PATCH 论证被削弱 → **建议出槽 0.79.0**（与 W-7/BC-7 同语义域同批，DEC-172 已裁决该域走 MINOR） | 拆两段则 PATCH 守住；①⑧入槽则 PATCH 定位受损（不建议） |
| 版本号预留（纪律 1/3） | 0.78.1 已预留（L459）且内容匹配 DEC-172 给定范围；FIX-281 子集入槽 = 范围核增 → 纪律 5/6（先更新路线图/DEC 再发布，M-1 执行） | 一致 |
| 未完成项处置（纪律 7） | 出槽/搁置项全部显式登记（§5）；无隐藏带入 | 合规 |

**一句话论证**：0.78.1 全部确定入槽项零行为语义变更（测试卫生/清理/措辞/检查器守卫标记面，L13/L34/L38 PATCH 明列）；FIX-281 若按本规划建议拆两段（缺陷修复面入、判定面①⑧出），L38「仅修复 bug」逐项成立，PATCH 定位守住——若①⑧判定规则扩展并入，则与 DEC-169 ③「判定规则 = 规则面支撑 MINOR」先例冲突，PATCH 边界失守（此为 §6 建议拆两段的核心依据）。

---

## 3. 里程碑（候选打包 → 发布；REL-071 先例 + DEC-143 基线）

| 里程碑 | 内容 | 交互边界 |
|---|---|---|
| **M-0 规划裁决** | 本规划 §5/§6 呈报用户裁决：① FIX-281 落点（§6 三方案 + 建议拆两段）；② FIX-272 P2×2 入槽确认（入 = 单独 triage + 注册；出 = 0.79.x 守卫批次）；③ F-3 实现方向确认（扩展 check-version-consistency vs 新增 check-bootstrap-markers——DESIGN-R0 F-3 建议二选一）；④ N=2 会话上限延续确认（DEC-163/169 ④ 惯例）；⑤ 待验证项处置（§9 观察 1：0.66.2 行状态核实回写——M-8 顺带 or Coordinator 独立处理）。裁决后入槽项任务化（triage 机器入账 + 注册 + 开发审查链）**须在 M-1 启动前完成**；超期 → 自动出槽登记后续版本 + decision-log | **用户确认（ask_user_question）** |
| **M-1 候选打包** | Release Agent：git 窗口核定（`git log v0.78.0..HEAD`，§0 待验证项闭环）+ 版本投影 0.78.0→0.78.1（15 投影 M-set + @bootstrap-version 标记面 + REQUIRED_SNIPPETS 版本钉——0.77.0 先例）+ CHANGELOG 0.78.1 条目 + release 三件套（release-checklist / rollback-plan / feature-flags〔如有 flag——本批无 flag，按先例出「无 flag 声明」〕）+ `core/releases/0.78.1.json` candidate + 路线图 0.78.1 行更新（含 FIX-281 子集范围核增若裁决入槽）+ DEC（范围核增/出槽登记）→ candidate commit | 自动（产生候选包） |
| **M-2 候选门禁** | §4 全部候选态门禁执行 + 既有基线 FAIL 分类披露（governance health 127 基线——18c 执行包首个 FAIL，REL-071 先例） | 自动 |
| **M-3 双审查** | Release Reviewer + Design Reviewer（plan-tracker 登记；REL-071 先例 = 双审 APPROVED_WITH_NOTES/unresolved_blockers=0 ×2）→ 机器入账 REVIEW-REL-073-R0 | 自动（评审链） |
| **M-4 用户授权 transition** | `release_authorized=false → true`；DEC-143 基线（自动推荐 + 用户确认）；授权记录 + DEC 入账 | **用户确认（ask_user_question）——发布唯一人工门** |
| **M-5 transition commit** | manifest-only：0.78.1.json candidate → released + `rel073-transition` event（integrity / recorded_at）+ 单一 parent = candidate commit；commit 后 `release-ledger --version 0.78.1 --no-remote` 重跑 **NATIVE_RELEASED**。**DEC-171 修复闭环核验**：transition commit 前确认 .git/hooks/commit-msg 已重装至修复版（`cp "<plugin_root>/skills/.../infra/hooks/"* .git/hooks/`）——若未重装且触发加粗 ID 行误报，按 DEC-171 先例 `--no-verify` 例外 + 当场入账（不静默） | 自动（授权后） |
| **M-6 annotated tag + 原子推送** | annotated tag `v0.78.1`（peel 到 transition commit）→ 原子推送 github-https（master + tag；远端 SHA 精确一致；merge/repeat/wrong-parent 阻断——ADR-010） | 自动（授权后） |
| **M-7 远端对账** | `check-release --version 0.78.1 --require-changelog --lineage-mode released --release-commit <commit>` 核心门禁 PASS + 既有基线 FAIL 如实披露；`release-ledger --version 0.78.1 --remote github-https` NATIVE_RELEASED PASS | 自动 |
| **M-8 发布收尾** | plan-tracker 工作流版本 → 0.78.1；路线图 0.78.1 行 → 已发布（纪律 4/8：PATCH 事后追加/立即回写）；`archive.py migrate --auto --dry-run`（报告需归档 → 执行 + `check-archive-integrity`）；RISK-036/039/044 复核维持（RISK-044 正式复评仍挂 0.79.0——DEC-169 ②）；§9 观察 1（0.66.2 行）若 M-0 裁决 M-8 顺带 → 执行核实回写 | 自动 |

### 3.1 回滚边界（显式声明——0.77.0 §3.1 先例复刻）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only 可逆） | 常规可逆操作（0.76.0 rollback-plan Reversibility 先例） |
| 已发布 v0.78.1 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（0.76.0 rollback-plan Reversibility 先例："Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

> **rollback-plan-0.78.1.md MUST 复刻本边界表**（0.77.0 R0 P2-1 先例义务延续）。

> 里程碑纪律（plan-tracker 里程碑段）：里程碑到期 MUST 执行检查；延期 MUST 记录 decision-log。

---

## 4. 发布门禁清单

候选态（M-2）与释放态（M-7）确定性命令（执行路径：`python skills/software-project-governance/infra/verify_workflow.py <cmd>`；0.77.0 §4 结构先例 + 0.78.0 实绩基线〔REL-071 M-2/M-7：17 项静态核心门禁 PASS + 127 issues 分类披露〕）：

| # | 门禁 | 0.78.0 实绩基线 | 0.78.1 预期 | 备注 |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASS（13 文件声明 0.78.0） | PASS（13 文件 0.78.1） | host plan-tracker 记录版本由 Coordinator 打包后 bump（同型惯例） |
| 2 | `check-projection-sync --fail-on-issues` | PASS | PASS | 漂移时 `release-projection --write`（--write 后须 rollback journal/原子写入测试证据 + 再次 check PASS——ADR-010） |
| 3 | `check-manifest-consistency` | PASS | PASS | F-3/DEC-171 若触及文件增删 MUST 登记 manifest |
| 4 | `check-cross-references --fail-on-issues` | PASS | PASS（零悬空） | |
| 5 | `verify`（无参） | exit=0 | PASSED | 既有基线失败按先例如实披露 |
| 6 | pytest 全量 | 零新增失败（存量基线如实记录） | 零新增失败 | N-P2-2/FIX-279 P2-1/FIX-272 P2×2 新测试全绿 |
| 7 | check-governance 零新增 | 127==127（A/B 对照，REL-071 M-7 实绩） | 零新增（对照 127 基线） | 18c 执行包既有基线分类披露 |
| 8 | `check-injection-contract` | PASS（28+ anchors） | PASS | fail-closed |
| 9 | `check-dsh-skills-manifest` | PASS（35/35） | PASS | |
| 10 | `check-release --version 0.78.1 --require-changelog --lineage-mode candidate` | 核心静态门禁 PASS + 基线 FAIL 分类披露 | 同型 | candidate 模式不要求不证明 tag |
| 11 | `release-ledger --version 0.78.1 --no-remote` | NATIVE_CANDIDATE（commit 后） | 同型 | 两阶段：候选态 NATIVE_CANDIDATE → transition 后 NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装为 PASS |
| 12 | `quality-tools` | NOT_RUN 如实记录（Ruff/mypy 未安装） | 同型 | ADR-010：不得虚构 PASS |
| 13 | `check-release ... --lineage-mode released --release-commit <commit>` | 核心门禁 PASS + 既有基线 FAIL 披露 | 同型 | tag/push 后执行；验证本地+远端 tag |
| 14 | `release-ledger --version 0.78.1 --remote github-https` | NATIVE_RELEASED PASS | 同型 | 远端 = github-https（既有环境限制基线；origin SSH 不可达——以 origin 执行须如实报告 UNKNOWN/BLOCKED） |

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——0.76.0/0.77.0 先例：以可逆性分析 + 门禁复跑为验证载体，rollback-plan-0.78.1.md 定义全量/部分回滚路径，回滚后复跑 #1/#2/#10 与 `git diff --check`）。

---

## 5. 遗留项入槽/出槽裁决表（DEC-172 队列 17 项 + F-3 + FIX-281）

> **M-0 交互注记（FIX-280 先例 / DEC-172）**：本裁决表为规划建议与 DEC-172 已裁决项的汇总呈现；M-0 终裁与新增决策点（FIX-281 落点 / FIX-272 可选项 / F-3 方向）经 `ask_user_question`（即 AskUserQuestion 工具；DEC-143 交互基线「自动推荐 + 用户确认」）由用户确认——DEC-169/DEC-172 即该模式实证。本注记即 FIX-280 修复所加同型样式（避免 Check 10 `m5_option_list_no_auq` 误报）。

### 5.1 裁决汇总（22 行：17 项 DEC-172 队列全覆盖（含 #13/#14 拆行展开为 20 行）+ F-3 登记行 + FIX-281 新增评估行；DESIGN-R0 P1-1 修正 19→22）

| # | ID | 级别 | 裁决（DEC-172 已定 √ / M-0 待决 ○） | 落点 | 理由摘要（依赖状态依据） |
|---|---|---|---|---|---|
| 1 | DEC-171（commit-msg Step 3 匹配缺陷） | P2 | √ 入槽 | **0.78.1** | 检查器缺陷实测误报（REL-071/072 加粗行 0 命中）；发布链被迫 --no-verify 例外侵蚀；修复面单行正则（L38 PATCH 面）；修复方向唯一正确（候选 B/C 已被 DEC-171 否决） |
| 2 | N-P2-1（_legacy_blocker_keys 死代码） | P2 | √ 入槽 | **0.78.1** | 死代码遮蔽维护陷阱；纯删除不改行为语义（L38）；与 FIX-279 观察项同域同窗 |
| 3 | N-P2-2（惰性 parse_completed_task_ids 注入） | P2 | √ 入槽 | **0.78.1** | 测试防护网死注入（P-v1 原则 4）；纯测试注入点对齐（PATCH 面） |
| 4 | N-P3-1（docstring 160→130） | P3 | √ 入槽 | **0.78.1** | 纯注释修正，成本≈0（随 N-P2 批） |
| 5 | FIX-279 P2-1（写入行缺失路径回归测试） | P2 | √ 入槽 | **0.78.1** | FIX-279 契约组件无回归防护（P-v1 原则 4）；补 1 用例 |
| 6 | FIX-279 P2-2（remediation 定位标准行来源） | P2 | √ 入槽 | **0.78.1** | UX 消息/文档改进，不改行为语义 |
| 7 | F-01（README 引号非逐字） | P2 | √ 入槽 | **0.78.1** | 宣示面引号纪律；本身不驱动 bump（L45-46），随批次 |
| 8 | change-triage「四步」措辞陈旧 | P3 | √ 入槽 | **0.78.1** | 文档陈旧（实际五步）；skill 修改 = L13/L33 PATCH 面 |
| 9 | F-3（bootstrap 标记面机器守卫——DESIGN-R0 范围外发现） | P3 | √ 登记 0.78.1 候选（实现方向 ○ M-0） | **0.78.1** | DEC-172 已裁决登记；实现二选一（扩展 check-version-consistency / 新增 check-bootstrap-markers）呈 M-0；新增检查项 = L34 PATCH 面 |
| 10 | FIX-272 P2×2（路径穿越测试 + 诊断拆分） | P2×2 | ○ **可选**——M-0 确认（入槽前须单独 triage 机器入账，DEC-172 后续动作栏） | 0.78.1（若选入）/ 0.79.x 守卫批次（若选出） | 安全无缺陷（14/14 探针验证），P2 为回归锚定 + 诊断可操作性；工作量小（<1 循环）；DEC-172 留 M-0 权衡 |
| 11 | G3 扩展（写时结构看护扩展至 Coordinator 直写路径） | P2 面 | √ 出槽维持 | **0.79.0** | 写时门禁扩展 = 新增 B 级自动化能力/规则面（L12/L37）——先观察 G3 首波实绩（BC-6）；DEC-172 ② |
| 12 | G5（task-priority 重复抑制） | 低收益 | √ 出槽维持 | **0.79.0** | 降噪第二波主题（-1.7KB/会话）；DEC-172 ② |
| 13 | G6（追查预算提示） | 低收益 | √ 出槽维持 | **0.79.0** | 剩余收尾提示面（G1 已覆盖主体）；与 G5 同批；DEC-172 ② |
| 14 | W-7 / BC-7（终态 marker 集扩展） | 中低 | √ 出槽维持 | **0.79.0** | 判定面规则修改（标记集扩展）——需 DEC + 审查链；**与 FIX-281 ①⑧ 同语义域（Check 30 形状/终态判定）**——§6 建议同批承载；DEC-172 ② |
| 15 | RISK-044 quick-scan | — | √ 搁置维持 | **复评挂 0.79.0**（DEC-169 ② MUST 含复评结论） | 检查点通过（32.8s/29.6s <60s 修订验收，DEC-167）；quick-scan = 未注册设计+开发任务不入任何修复批 |
| 16 | F-03（e2e 投影决策） | P2 | √ 搁置维持 | 触发式（下次 e2e 触碰批次或候选打包期落 decision-log） | 决策型事项，无版本驱动（queue-triage §2.1 #1） |
| 17 | F-04（npm pack 机器守卫） | P3 | √ 搁置维持 | 0.79.x 守卫批次 | 观察级；FIX-275 验收已覆盖；新开发任务不混入修复批 |
| 18 | F-04-env（agent-locks 环境路径锁扩展） | P2 | √ 搁置维持 | 0.78.x+ 独立任务（不进 0.78.1/0.79.0） | 低概率失效模式 + 安全敏感需锁模型设计审查（queue-triage §2.1 #3） |
| 19 | F-05 + BC-1（词表版本化 + 备份留痕 + Check 39 升 FAIL） | P2/P3 | √ 搁置维持（DEC-172 如实标注） | 条件挂起 | **升 FAIL 条件结构性不可满足**（DEC-160 锚定「连续 2 个零违规 0.77.x 版本」——0.78.0 非 0.77.x 且无 0.77.1，累计=1）；词表版本化 + BC-1 字段化为独立 PATCH 面小修可随任意批次（不依赖升 FAIL 条件）；18c 执行包基线（127 issues 首个 FAIL）与本项搁置维持关系 = DEC-172 既有口径延续 |
| 20 | FIX-279 P2-3 + P3×3 | P2×1+P3×3 | √ 搁置维持 | P2-3 = 0.79.x 专项评估；P3×3 观察池 | P2-3（EVD fallback 残余误报）误报 vs 漏报权衡需独立 DEC；queue-triage §2.1 #14 |
| 21 | N-P3-2 / N-P3-3 / N-P3-4 + DESIGN N-3~N-5 + 前轮 P3-2/P3-4 | P3 | √ 搁置维持 | 观察池（随下轮触碰归并） | 讨论级/观察级（N-P3-2 若实施 = 判定面对齐评估——登记）；queue-triage §2.1 #13 |
| 22 | **FIX-281（宿主 B 类缺陷申报批次 9 项）** | P1 | ○ **新决策点**——本规划 §6 评估 + M-0 裁决 | 建议：缺陷修复面 ②③④⑤⑥⑦⑨ → **0.78.1**（范围核增）；判定面 ①⑧ → **0.79.0**（与 W-7/BC-7 同批） | DEC-172 之后新增（2026-08-27 入账）；逐项面分析与三方案见 §6；router 宿主活体持续受害（⑨ 第三现）支撑缺陷面前移紧迫性 |

> 覆盖核对（queue-triage-0.78x.md §2 17 项 → 本表映射，逐项可追溯）：§2.1 #1 F-03→#16；#2 F-04→#17；#3 F-04-env→#18；#4 F-05+BC-1→#19；#5 FIX-272 P2×2→#10；#6 RISK-044→#15；#7 G3→#11；#8 G5→#12；#9 G6→#13；#10 W-7/BC-7→#14；#11 N-P2-1→#2；#12 N-P2-2→#3；#13 P3 组→#4（N-P3-1 入槽）+ #21（其余搁置）；#14 FIX-279 观察项→#5 + #6（P2-1/P2-2 入槽）+ #20（P2-3+P3×3 搁置）；#15 F-01→#7；#16 四步→#8；§2.2 #17 DEC-171→#1。**17 项全覆盖**（#13/#14 按入槽/搁置拆行呈现，无遗漏无新增编造）；#9 F-3 = DEC-172 登记行（queue-triage §3.3 额外行）；#22 FIX-281 = DEC-172 后新增申报批次评估行（§6）。

### 5.2 裁决后 0.78.1 范围预判

- **基线范围（DEC-172 已定，无需再裁）**：§1.1 前 9 行（F-3 实现方向除外）——纯修复/清理/测试卫生/文档措辞/守卫标记批。
- **M-0 变量叠加后**：+ FIX-272 P2×2（若选入）；+ FIX-281 缺陷修复面子集（若采纳拆两段建议）→ 范围核增走 DEC + 路线图行更新（纪律 5/6，M-1 执行）。
- **任何组合下 PATCH 定位论证**：见 §2——唯一削弱场景 = FIX-281 ①⑧判定面并入（不建议，§6）。

---

## 6. FIX-281 入槽评估（M-0 新决策点——评估建议，最终裁决 = 用户）

> **M-0 交互注记（FIX-280 先例）**：本节选项组合经 `ask_user_question`（AskUserQuestion 工具，DEC-143 交互基线）呈用户裁决；本节全部为评估建议，不构成决策。

### 6.1 九项逐项面分析（来源：plan-tracker L262 FIX-281 行——router EV-066 2026-08-23 + EV-071/073 2026-08-27 实证）

| 项 | 缺陷 | 面 properties | VERSIONING 定性 | 落点建议 |
|---|---|---|---|---|
| ① | Check 30 V2×9/V5×2 对 pre-FIX-174 文件式 review 记录（无 R0 起始机器行）判 11 项 FAIL——FIX-174 状态机无历史格式迁移路径，G2 L-A/L-B/L-C 未覆盖该形状（与 W-7/BC-7 部分重叠但 V2 形状不同） | **判定规则扩展**（新增历史形状分类：FAIL→WARN 迁移路径） | G2 形状分类先例 = 规则面（DEC-169 ③ 定性支撑 0.78.0 MINOR）→ MINOR 支撑项；若强行 PATCH 承载 = 与先例自相矛盾 | **0.79.0**（与 W-7/BC-7 同批同域） |
| ② | Check 1 `get_all_completed_task_entries` 硬编码 parts[9] 与 `_PROFILE_TASK_COLUMNS[lightweight]=6` 自相矛盾（router 实证行号 9113 vs 13510，**0.78.0 行号需复核**——拆分任务执行时核） | 解析器实现 bug（硬编码 vs 配置矛盾） | L38 缺陷修复（恢复「按 profile 列数解析」设计语义）→ PATCH | **0.78.1** |
| ③ | `parse_current_active_tasks` 节边界只 break 于 `### 最近完成`——自定义节顺序宿主漏解析 | 解析器健壮性缺陷（合法结构漏读） | L38 缺陷修复 → PATCH | **0.78.1** |
| ④ | `parse_gate_status` 括号节名精确匹配失效 | 解析器健壮性缺陷 | L38 缺陷修复 → PATCH | **0.78.1**（②③④ router EV-066 宿主侧已绕过修复——插件侧方案已知，实证充分） |
| ⑤ | `review_record.py:335` 无存在性检查直接覆盖（历史补录数据破坏风险 P7） | 防破坏守卫**新增**（存在性检查 + 拒绝/提示——新防护行为） | L13/L34 类比（新增防护 = PATCH 面增量**如实陈述**）；类比 FIX-271 R1-R5 防再发（0.77.0 先例随 MINOR 打包但本身为防护缺陷修复） | **0.78.1**（保守变体：0.79.0） |
| ⑥ | EV-/EVD- 跨仓编号前缀约定差异无映射说明 | 文档/约定说明缺失 | 文档面 → PATCH | **0.78.1**（若实现含映射逻辑再按实现面重评） |
| ⑦ | task-priority-analysis 完成态过滤缺失——router 2026-08-27 实测 4 项全部终态仍列 Top pick/Unblocked（误导 M7.4 step 6 完成必推荐的空原因判定） | 工具输出正确性缺陷（推荐了语义上不该推荐的终态任务） | L38 缺陷修复论证成立（「完成必推荐」语义本就不含终态任务）；与 G5 同工具但性质不同（缺陷 vs 优化） | **0.78.1**（保守变体：0.79.0——若 M-0 认为 tpa 过滤规则新增属判定面） |
| ⑧ | Check 30c 合法机器行（REVIEW-/RECO-）新增即入 WARN 无白名单/分类升级路径（router 10→13 实证） | **判定分类扩展**（新形状白名单/溯源分类规则） | 同①——判定规则扩展 → MINOR 支撑（plan-tracker FIX-281 行定位提示原文：「历史格式迁移+30c 分类面或涉判定面 MINOR」） | **0.79.0** |
| ⑨ | change-triage 版本适配以**工作流版本**（0.78.0）替代**项目当前版本**作 current——宿主项目版本号低于工作流版本时合法目标版本被 fail-closed 拒绝（router REL-002 入账活体**第三现**：EVO-004/EV-038 先例——宿主被迫改用「未规划版本」绕过，丢失版本链挂载） | 校验事实源缺陷（用错 current 基准） | L38 缺陷修复（恢复「以项目当前版本为基准」设计语义）→ PATCH；**router 活体持续受害——紧迫性最高** | **0.78.1**（高优先） |

### 6.2 落点方案（M-0 呈报选项）

| 方案 | 0.78.1 承载 | 0.79.0 承载 | PATCH 边界 | 代价/收益 |
|---|---|---|---|---|
| **A. 拆两段（本规划推荐）** | ②③④⑤⑥⑦⑨（7 项缺陷修复面） | ①⑧（2 项判定面，与 W-7/BC-7 同批同域） | **守住**——L38 逐项成立；⑤⑦按 L13/L34 增量如实陈述 | 收益：⑨ router 活体止血（第三现）+ ②③④方案已知低风险；代价：0.78.1 范围核增（DEC + 路线图更新）+ 窗口拉长约 2~3 循环 |
| B. 任务书候选组合 | ①②③④⑨（5 项） | ⑤~⑧（4 项） | **部分受损**——①（Check 30 判定输出 FAIL→WARN）入 PATCH 批与 DEC-169 ③「判定规则=规则面支撑 MINOR」先例冲突；「零行为面」表述须降级为「PATCH 面增量」口径 | ①入 0.78.1 的正面论证 = 检查器适配真实数据现状（DEC-171 同型）——可用但先例张力如实呈报；⑤⑥⑦顺延一版 |
| C. 全部 9 项 → 0.79.0 | —（仅 DEC-172 原批） | 全部 9 项 | 0.78.1 保持最纯净 PATCH（DEC-172 原范围零核增） | 代价：⑨ router 宿主合法版本被拒持续一个版本周期（第四现风险）+ 版本链挂载持续漂移；0.79.0 范围膨胀（9+4+1 项） |

**本规划建议：方案 A（拆两段）**。核心理由：①⑧ 与 DEC-172 已裁决 0.79.0 的 W-7/BC-7 同属 Check 30 形状/终态判定语义域（plan-tracker FIX-281 行自身定位提示亦锚定「或涉判定面 MINOR」）——同批承载语义一致性最好且 PATCH 边界无损；②③④⑨缺陷确凿、方案已知（router 宿主侧绕过实证）、⑨有活体紧迫性；⑤⑥⑦的 PATCH 论证成立但留有保守退路（M-0 可将⑤⑥⑦一并移 0.79.0，0.78.1 收窄为②③④⑨最窄缺陷面——零判定争议变体）。

### 6.3 依赖与阻塞说明

- FIX-281 批次行当前 `blocked_by=[REL-002]`（tpa 快照）——REL-002 为 **router 仓任务**（本仓无行 data gap，tpa fail-closed 显示 blocked；router 2026-08-27 REL-002 入账活体即⑨的第三现实证）。**该依赖是申报通道关联，非插件侧修复执行的前提**。
- **拆分执行结构**（plan-tracker FIX-281 行交付物列原文：「修复执行时逐项拆分独立 FIX 任务」）：入槽子集 → 独立 FIX 任务各自 triage 机器入账（**depends_on 不挂 FIX-281/REL-002**，避免 data gap 传染阻塞；依赖列为空或指向具体源材料）；FIX-281 批次行在拆分任务全部落地后按拆分进度闭合（部分落地 = 部分闭合 + 剩余项登记落点版本）。
- M-0 须确认：拆分执行不因 REL-002 data gap 阻塞（本规划建议口径如上）。

---

## 7. 风险披露

| 风险 | 状态 | 0.78.1 处置 |
|---|---|---|
| RISK-036（official marketplace operations） | **打开**（2026-09-30；1.0.0 硬阻塞） | 0.78.1 **不关闭**；不声明 official/marketplace approval |
| RISK-039（ArchGuard external validation） | **打开**（2026-09-30；1.0.0 硬阻塞） | 0.78.1 **不关闭**；不声明 universal/full runtime support |
| RISK-044（`--summary-only` 30-33s） | **已接受**（DEC-149；2026-08-26 检查点通过 DEC-167） | 0.78.1 不改变语义；**正式复评挂 0.79.0**（DEC-169 ② MUST——risk-log 行「0.78.x」字样为 DEC-167 时点表述，以 decision-log 为权威口径）；若 0.78.1 打包期实测显著劣化（>60s 违反修订验收）按 risk-log 触发条款升级处理 |
| 既有健康基线 | governance health 127 issues（18c 执行包首个 FAIL——0.78.0 发布后实绩） | 候选/释放态按 REL-067~071 先例**如实分类披露**（A/B 对照零新增）；零 `.governance/` 文件由发布包触碰（治理记录变更由 Coordinator 通道） |
| DEC-171 修复期窗口暴露 | 修复发布并重装 hook 前，涉加粗任务 ID 行的 commit（含本发布链 M-1~M-6 各 commit）仍可能触发 Step 3 误报 | M-5 预案内置（§3）：hook 重装确认优先；未重装遇误报 → DEC-171 先例 `--no-verify` 例外 + 当场入账，不静默 |
| FIX-281 范围核增风险 | 子集入槽改变 0.78.1 范围（DEC-172 裁决时点未知） | 纪律 5/6：M-0 裁决 + DEC 入账 + 路线图行更新（M-1 执行）；N=2 会话上限兜底防悬置 |
| DSH preset 时滞 | 已知（0.77.0 先例） | 迁移说明随发布文档：`git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`；不宣称未 sync 安装的会话级效果 |

---

## 8. No-overclaim 边界

本规划（及后续 0.78.1 候选）**不声明**：

- 1.0.0 production-ready / 1.0.0 正式发布
- official approval / marketplace approval / curated listing
- universal / full runtime support
- RISK-036 / RISK-039 关闭
- FIX-281 全部 9 项已修复（M-0 裁决前仅存在评估建议；落点未定）
- 任何历史已发布 version tag 的状态变更（v0.78.0 及之前未受本版影响；0.66.2 行状态核实属治理记录回写，非 tag 操作）

并**不创建、不证明** `v0.78.1` tag 存在（candidate-only；`release_authorized=false`——transition/tag/push 待用户授权 M-4，DEC-143 基线）。0.78.1 主线语义 = 缺陷修复/清理/测试卫生批（+M-0 裁定的 FIX-281 子集），不关乎官方收录/市场批准/1.0.0 就绪。

---

## 9. 边缘问题与观察项

1. **0.66.2 行状态漂移（TRIAGE-REL-073 版本适配 WARN 根因）**：路线图 0.66.2 行自 2026-07 起为「补偿发布规划中」——版本链解析器据此将 planned_next 识别为 0.66.2，产生 TRIAGE-REL-073 入账 advisory WARN（既有登记）。任务书背景断言该行「已发布未回写漂移」——**本规划未能从已读治理记录独立确证 0.66.2 实际发布状态**（RISK-041 行提及 ledger 全量 16 issues 含 0.66.2 债务，与「已发布闭环」存在张力）→ **待验证**：M-0 或 M-8 前核实（git tag `v0.66.2` 存在性 + `release-ledger --version 0.66.2` 状态 + DEC 记录核对）；确证后由 Coordinator 回写路线图行（治理记录小修，不占 0.78.1 版本范围）。**本规划建议**：随 M-8 收尾顺带处理（若核实为已发布）或 Coordinator 独立处理——呈 M-0 ⑤。
2. **路线图 0.67.0~0.70.0 行状态漂移 + 0.71.0/0.72.0 缺行**：既有登记（plan-tracker L455 fact-source 观察项注记：0.71.0/0.72.0 缺行——0.70.0→0.73.0 断档，回补需各自 release 事实核对，不凭记忆编造）——维持登记，本规划不新增动作。
3. **HEAD 窗口待核定**：§0 已列——0.78.0 后治理/docs 变更 commit 状态 M-1 核定（纯规划段零命令执行是本任务边界，非事实缺口）。
4. **FIX-281 ②行号复核**：router 实证行号（verify_workflow.py:9113 vs 13510）为 router 时点值，0.78.0 行号需复核（plan-tracker FIX-281 行原文自带标注）——拆分任务执行时核。
5. **基线数字漂移惯例**：governance health 127 为 0.78.0 发布后实绩时点值——0.78.1 打包期以实测为准，不引用旧值作新声明（0.76.0 checklist 先例）。
6. **AUDIT-146↔FEAT-010 cycle WARN**：既有容忍基线（FIX-237.2）——TRIAGE-REL-073 快照再现，非本规划新增，不处理。

---

*本文档为 REL-073 规划段产出（唯一写入文件）。M-0 用户裁决 → 入槽项任务化 → M-1 候选打包为后续工作单元。*
