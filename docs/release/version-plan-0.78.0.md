# Version Plan - 0.78.0

**Version**: 0.78.0 (MINOR — user confirmed at M-0, DEC-169)
**Release**: 治理降噪第一批打包——FIX-278（G4/F + G1 + G2 + G3）+ FIX-279（write-guard 列数契约修正）+ M5 基线小修（M-0 入槽确认）
**Date**: 2026-08-26
**M-0 裁决**: ✅ 2026-08-26 用户确认（DEC-169 四项：入槽全部三项 / RISK-044 维持 / MINOR 定位 / N=2 延续）——本表由"建议方案"转为已确认规划
**Plan task**: REL-071 第一段（版本规划——规划先行；入出槽裁决 + RISK-044 复评 + M5 基线小修）。**M-1 候选打包不在本任务**（0.77.0 先例：M-0 用户裁决后启动）
**Status**: M-0 已通过，待 M-1 候选打包。`release_authorized = false`——transition / tag / push 待用户授权（DEC-143 交互基线：自动推荐 + 用户确认）
**Produced by**: Release Agent（REL-071 规划段）；本文档只读规划 + 仅写入 `docs/release/version-plan-0.78.0.md`，未触碰版本文件/产品代码/`.governance/`（返回 proposed 条目由 Coordinator 写回）

---

## 0. 规划基线事实（治理记录核验，零编造；git 数字以事实源记录为准，M-1 复验）

| 事实 | 值 | 来源（留痕） |
|---|---|---|
| 发布基线 | `v0.77.0` = transition `db9f6c9`（REL-070；annotated tag object `f0c94b4`，peel=db9f6c9，双端一致） | session-snapshot.md L10；plan-tracker REL-070 行 |
| 版本窗口 | `v0.77.0..HEAD` = **1 个 commit**（FIX-278 `3ad9fdd`，已推送 github-https） | session-snapshot.md L10（`0f9e5bb..3ad9fdd = FIX-277 2dffa8d + candidate ac5df32 + transition db9f6c9 + FIX-278 3ad9fdd`） |
| HEAD | `3ad9fdd`（FIX-278，已推送） | session-snapshot.md L10 |
| 追加待推送 | FIX-279 commit `c193299`（2 文件 +154/-19，**未推送**——M-1 前置动作为推送确认） | plan-tracker.md FIX-279 行（L255） |
| 版本声明现状 | 0.77.0（未 bump——符合"候选打包不做"边界） | plan-tracker 工作流版本（0.77.0） |
| BREAKING 声明 | 窗口内 FIX-278/FIX-279 均非 BREAKING（增量变更；G1 输出契约变更/G2 判定规则修改经 DEC-166 落盘，无接口删除/默认行为破坏） | DEC-166；EVD-FIX-278；EVD-904 |
| 路线图预留 | **plan-tracker 版本路线图无 0.78.0 行**——M-1 打包 MUST 新增该行（规划纪律 1/5/8；登记后与 REL-071 范围一致）；0.77.0 行已发布（2026-08-25） | plan-tracker L453（路线图止于 0.77.0 + 1.0.0 预留） |
| 0.78.x 队列登记 | session-snapshot「未完成/已延期」节：FIX-272 P2×2、F-03、F-04、F-04-env、F-05+BC-1、RISK-044 quick-scan（0.78.x+） | session-snapshot.md L47 |
| 健康基线 | check-governance --summary-only 实测（2026-08-26 本会话 bootstrap）：**105 issues**，首个 FAIL = M5 Check 10（1 项 m5_option_list_no_auq）——既有基线（含 M5 基线小修对象，DEC-167），非本次规划引入；check-governance 墙钟 29-33s 区间（RISK-044 口径） | 本会话 bootstrap 输出；risk-log RISK-044 行 |

---

## 1. Release Scope

### 1.1 候选打包链 → 变更类别

| # | 任务 | commit | 状态/审查 | 类别 | 变更摘要（事实源核验） |
|---|---|---|---|---|---|
| 1 | **FIX-278** 治理降噪第一批 | `3ad9fdd`（16 文件 +2130/-42，已推送） | CODE R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0；DESIGN R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0（REVIEW-FIX-278-CODE-R1/DESIGN-R1 机器行；EVD-FIX-278） | **主链（hardening/behavior）** | G4/F 编码显式化（.governance 读取 pwsh 片段 UTF-8 规约）+ G1 summary top-N（standard 档=汇总+首个 FAIL/WARN+≤5 明细 130 截断+指引行）+ G2 legacy 判定 L-A/L-B/L-C（形状+终态，DEC-166）+ G3 写时 guard（change-triage 成功路径按 record_id 校验，exit 2 fail-closed）+ audit-147/148 报告入库 |
| 2 | **FIX-279** G3 write-guard 列数契约修正 | `c193299`（2 文件 +154/-19，**未推送**） | CODE R0 APPROVED_WITH_NOTES/0（REVIEW-FIX-279-CODE-R0 机器行；EVD-904；DEC-168） | **主链（bug fix/PATCH 面）** | write-guard standard_cols 改取首个非本次写入的 `\| TRIAGE-` 行（行族权威）——消除每次合法 change-triage 入账被 fail-closed exit 2 误报（TRIAGE-REL-071/TRIAGE-FIX-279 两次活体触发）；**DEC-168 明确"随 0.78.0 发布"** |
| 3 | **M5 基线小修**（入槽建议，M-0 裁决） | —（文档级） | DEC-167 登记 0.78.x 小修 | **docs** | `docs/release/version-plan-0.77.0.md` L154 裁决表选项样式触发 `m5_option_list_no_auq`（Check 10 基线）——修法：在裁决表/文档加 AskUserQuestion 引用或豁免注记；**非 FIX-278 引入**（该文档随 0.77.0 候选入库） |

### 1.2 语义定位

- **主链语义**：FIX-278 = 治理降噪第一批（G1 输出契约变更 + G2 判定规则修改经 DEC-166 决策落盘 + G3 写时门禁 + G4/F 文档规约）+ FIX-279 = G3 引入后 write-guard 契约再基线（DEC-168），形成「降噪主链 + 契约修正」闭环（0.78.0 主题 = 治理噪声削减批次落地）。
- **同箱叙事**：AUDIT-147/148（治理开销/告警洪流定性分析）已随 FIX-278 入库——0.78.0 是「分析 → 第一批实施 → 契约修正」的完整交付链，不涉及新外部能力。
- **M-1 候选打包不在本任务**（REL-070 先例：0.78.0 版本规划先行，候选打包待用户 M-0 裁决后）。

---

## 2. Version and SemVer（MINOR vs PATCH 论证）

**结论：MINOR（建议；M-0 确认）。**

| 判据 | 事实 | 结论 |
|---|---|---|
| 行为/规则面变更（VERSIONING.md L12 累积变更达到里程碑 + L37 规则变更） | FIX-278 = 16 文件 +2130/-42 四子项：G1 改变 check-governance --summary-only 的**输出契约**（默认档位展示 top-N 明细+指引行）；G2 引入**判定规则**（legacy 形状+终态降级 WARN，规则经 DEC-166 落盘，影响 Check 30 V2/V5/Check 37 L-C 判定面）；G3 新增**写时门禁**（change-triage 成功路径结构校验，exit 2 fail-closed）——行为/规则面显著变更 + 判定面扩展（0.76.0 看护模式七项 MINOR 同类先例；0.75.0 注入面/空推荐 MINOR 同类先例） | → **MINOR 支撑项** |
| PATCH 面增量如实陈述（**不作为判级依据**） | FIX-279 = bug fix（write-guard 契约错配修正）+ G4/F 文档规约/编码指引（文档面）——按 VERSIONING.md L34 如实陈述为 PATCH 面增量 | 单列项（如实口径） |
| 无 BREAKING CHANGES | 窗口内零 BREAKING：无接口删除/重命名、无默认行为破坏；G2 降级规则 fail-safe 边界锁定（ACTIVE/真实 nonzero 恒 FAIL，DEC-166；DESIGN R1 蓝军 7 条）；G1 其余档位字节不变（lightweight/strict/默认路径不变，DEC-166 ②） | 非 MAJOR |
| 版本号预留核对（规划纪律 1/5/6/8） | 路线图**无 0.78.0 行**——REL-071 任务书（plan-tracker L256）已登记 0.78.0 = FIX-278 降噪第一批打包；0.78.x 队列（snapshot L47）为 DEC-164/167 既定出槽目标版；**M-1 MUST 新增路线图行**（登记后与 REL-071 范围一致）+ decision-log 记录范围 | 一致（FIX-278/279 语义吻合）；行登记为 M-1 动作 |
| 90% 完成率（规划纪律 7） | 入槽候选：FIX-278 ✅（已推送双审终态）、FIX-279 ✅（审查通过待推送）、M5 小修（若入槽 = 文档级 1 循环）；出槽项不进入 0.78.0 范围 | ≥90% 由 M-0 范围确定后复核 |
| 未完成项处置（规划纪律 7） | 出槽项（含 F-03/F-04/F-04-env/F-05+BC-1/FIX-272 P2×2/quick-scan/G3 扩展/G5/G6/W-7/N-P2/P3 组等）按 §5 裁决表显式登记；RISK-044 复评见 §6.1 | 无隐藏带入 |

---

## 3. 里程碑（候选打包 → 发布；REL-070 先例 + DEC-143 基线）

| 里程碑 | 内容 | 交互边界 |
|---|---|---|
| **M-0 规划裁决** | §5 入槽/出槽项用户确认 + §6.1 RISK-044 复评结论确认 + MINOR 定位确认；若 M5 基线小修入槽 → 新任务注册（triage 机器入账 + DEC + 文档级实施 1 循环，须在 M-1 启动前完成）；**超期 → 自动出槽登记后续版本，0.78.0 按 FIX-278+FIX-279 打包，记 decision-log**（DEC-163 N=2 会话上限惯例） | **用户确认（ask_user_question）** |
| **M-1 候选打包** | **前置：FIX-279 `c193299` 推送确认**（当前未推送——MUST 先推送再打包）；Release Agent：版本投影 0.77.0→0.78.0（15+ 投影 M-set + @bootstrap-version 标记面 + REQUIRED_SNIPPETS 版本钉）+ CHANGELOG 0.78.0 条目（v0.77.0..HEAD 窗口 + FIX-279：Added/Changed/Fixed/Validation/Boundaries）+ release 三件套 + `core/releases/0.78.0.json` candidate + **路线图 0.78.0 行新增** + DEC（范围/入出槽/复评结论落盘）→ candidate commit | 自动（产生候选包） |
| **M-2 候选门禁** | §4 全部候选态门禁执行 + 既有基线 FAIL 分类披露（REL-067/068/069/070 先例） | 自动 |
| **M-3 双审查 R0** | Release Reviewer + Design Reviewer（REL-071 行登记；REL-070 先例 = CODE + RELEASE 双审）→ APPROVED_WITH_NOTES/unresolved_blockers=0；机器入账 REVIEW-REL-071-R0 | 自动（评审链） |
| **M-4 用户授权 transition** | state：`release_authorized=false → true`；DEC-143 基线；授权记录 + DEC 入账（DEC-165 先例） | **用户确认（ask_user_question）——发布唯一人工门** |
| **M-5 transition commit** | manifest-only：0.78.0.json candidate → released + `rel071-transition` event（integrity / recorded_at）+ 单一 parent = candidate commit；commit 后 `release-ledger --no-remote` 重跑 **NATIVE_RELEASED** | 自动（授权后） |
| **M-6 annotated tag + 原子推送** | annotated tag `v0.78.0`（peel 到 transition commit）→ 原子推送 github-https（master + tag；远端 SHA 精确一致；merge/repeat/wrong-parent 阻断） | 自动（授权后） |
| **M-7 发布后验证** | `check-release --version 0.78.0 --require-changelog --lineage-mode released --release-commit <commit>` 核心门禁 PASS + 既有基线 FAIL 如实披露；`release-ledger --version 0.78.0 --remote github-https` NATIVE_RELEASED PASS | 自动 |
| **M-8 发布收尾** | plan-tracker 工作流版本 → 0.78.0；路线图 0.78.0 行 → 已发布；`archive.py migrate --auto --dry-run`（报告需归档 → 执行 + `check-archive-integrity`）；风险复核保持（RISK-044 下轮复评 = 0.79.x 版本规划登记；RISK-036/039 2026-09-30） | 自动 |

## 3.1 回滚边界（显式声明）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only 可逆） | 常规可逆操作（0.76.0 rollback-plan Reversibility L43 先例） |
| 已发布 v0.78.0 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（0.76.0 rollback-plan Reversibility L50 先例："Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

> **rollback-plan-0.78.0.md MUST 复刻本边界表**（0.77.0 规划 R0 P2-1 先例；该表与发布回滚契约共同构成）。
> 里程碑纪律（plan-tracker L497-500）：里程碑到期 MUST 执行检查；延期 MUST 记录 decision-log。

---

## 4. 发布门禁清单

候选态（M-2）与释放态（M-7）的确定性命令（执行路径：`python skills/software-project-governance/infra/verify_workflow.py <cmd>`）：

| # | 门禁 | 0.77.0 先例值 | 0.78.0 预期 | 备注/分类惯例 |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASS（13 文件声明；1 advisory WARN——host plan-tracker 滞后） | PASS（13 文件 0.78.0） | 同型 WARN：host plan-tracker 记录版本由 Coordinator 打包后 bump |
| 2 | `check-projection-sync --fail-on-issues` | PASS（15 投影） | PASS | 漂移时 `release-projection --write`（written=15 先例；--write 后须 rollback journal/原子写入测试证据 + 再次 check PASS——ADR-010） |
| 3 | `check-manifest-consistency` | 568/608 PASS（REL-070） | PASS | 打包增删文件 MUST 登记 manifest |
| 4 | `check-cross-references --fail-on-issues` | 68 文件/649 refs PASS（0.77.0 规划） | PASS（零悬空） | |
| 5 | `verify`（无参） | PASSED（0.77.0） | PASSED | 既有基线失败按先例披露 |
| 6 | pytest 全量 | FIX-279 后 1985 tests（EVD-904：0 新增失败归因于本次修改；27 存量失败 = 既定基线——24×WSL 环境 + cleanup + 性能计时抖动，EVD-FIX-278） | 记录实测；零新增失败 | 180s 环境超时先例 |
| 7 | check-governance 零新增 | ==113（0.77.0 发布时点值；当前 bootstrap 105——实时 posture 以实测为准） | 零新增（相对打包后基线） | 宿主基线 issues 数按其实时 posture |
| 8 | `check-injection-contract` | 28 anchors/4 文件 PASS（FIX-272） | 同型 PASS | fail-closed |
| 9 | `check-dsh-skills-manifest` | 35/35 双向 PASS（0.77.0 新 CLI） | 同型 PASS | 随包 35 skills 清单 |
| 10 | `check-release --version 0.78.0 --require-changelog --lineage-mode candidate` | 0.77.0：6 issues 全分类（3 未提交态产物 + 3 既有基线） | 核心静态门禁全 PASS；FAIL 项按类披露 | candidate 模式不要求/不证明 tag；FIX-279 未推送态须在 M-1 前置消除 |
| 11 | `release-ledger --version 0.78.0 --no-remote` | NATIVE_CANDIDATE（candidate commit 后） | 同型 | 两阶段：候选态 NATIVE_CANDIDATE / 释放态 NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装为 PASS |
| 12 | `quality-tools` | Ruff/mypy 未安装 → NOT_RUN 如实记录 | 同型 | ADR-010；不得包装为 PASS |
| 13 | `check-release ... --lineage-mode released --release-commit <commit>` | 核心门禁 PASS + 3 既有基线 FAIL（archive gap / origin SSH / governance health——EVD-894 先例） | 同型 | tag/push 后执行；验证本地+远端 tag |
| 14 | `release-ledger --version 0.78.0 --remote github-https` | NATIVE_RELEASED PASS（0.77.0） | 同型 | **远端 = github-https**（0.75.0/0.77.0 先例；origin SSH 实测不可达——以 origin 执行须如实报告 UNKNOWN/BLOCKED）；ADR-010：唯一 transition、单一 parent、merge/repeat/wrong-parent/rename-delete-add 阻断 |

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——按 0.77.0 先例以可逆性分析 + 门禁复跑为验证载体；rollback-plan-0.78.0.md 定义全量/部分回滚路径，回滚后复跑 #1/#2/#10 与 `git diff --check`）。

---

## 5. 遗留项入槽/出槽裁决表

> 本表为 **建议方案**（REL-071 任务书裁决项），M-0 终裁经 `ask_user_question`（即 AskUserQuestion 工具——M5 合规出口；DEC-143 交互基线「自动推荐 + 用户确认」）由用户确认（DEC-169 四项）。所有来源以文件路径留痕消歧；**来源细节不完整的项如实标注，禁止编造**。

### 5.1 裁决汇总

| ID | 来源（留痕） | 级别 | 建议 | 理由（依赖状态依据） |
|---|---|---|---|---|
| **FIX-278**（降噪第一批 G4/F+G1+G2+G3） | plan-tracker FIX-278 行（L254）；EVD-FIX-278；REVIEW-FIX-278-CODE-R1/DESIGN-R1 机器行；DEC-166 | P1 | **入槽 0.78.0（主链，已定）** | REL-071 任务书明确 0.78.0 = FIX-278 降噪第一批打包；commit 3ad9fdd 已推送；双审终态 APPROVED_WITH_NOTES/0（五发现全闭合）；G4/F+G1+G2+G3 四子项契约经 DEC-166 落盘 |
| **FIX-279**（write-guard 列数契约修正） | DEC-168（影响范围栏："FIX-279 随 0.78.0 发布"）；plan-tracker FIX-279 行（L255）；EVD-904；REVIEW-FIX-279-CODE-R0 | P1 | **入槽 0.78.0（已定）** | 归属 0.78.0 为 DEC-168 既定契约；修复对象 = FIX-278 G3 引入的 write-guard 误报（TRIAGE-REL-071/TRIAGE-FIX-279 活体触发）；审查 APPROVED_WITH_NOTES/0；**commit c193299 未推送——M-1 前置动作 = 推送确认** |
| **M5 基线小修**（version-plan-0.77.0.md L154 裁决表样式触发 m5_option_list_no_auq） | DEC-167 ④（"登记 0.78.x 小修（在裁决表/文档加 AskUserQuestion 引用或豁免注记）"）；risk-log RISK-044 行（2026-08-26 复核注记） | —（基线） | **建议入槽 0.78.0（M-0 确认）** | (a) 文档级小修（裁决表样式注记/豁免），成本 ≈1 循环且与 0.78.0 打包同窗（版本规划/CHANGELOG/docs 面）；(b) 自指性：本 0.78.0 规划文档若沿用同型裁决表样式将再触发同一基线条目——入槽可顺带覆盖，避免基线条目持续累积（Check 10 当前 1 项、health 105 首个 FAIL）;(c) 备选出槽 → 随下次触碰合并（FIX-247 先例），基线条目保留披露 |
| **F-03**（e2e commands/governance.md 投影决策） | DEC-164（2026-08-25 裁决出槽 0.78.x 候选）；version-plan-0.77.0.md §5.1 F-03 行 | P2 | **出槽（0.78.x+ 候选登记；不在 0.78.0）** | (a) DEC-164 已裁决：测试资产卫生，随下次 e2e 维护批次处理（触发 = e2e fixture 同步/改版时登记）；(b) 与 0.78.0 主链（降噪批次）无强关联；(c) 入槽需投影契约裁决（注册 vs 独立维护声明，DEC-157 ③ 完整描述）+ e2e 开发审查链 → 扩张 0.78.0 范围 |
| **F-04**（npm pack --dry-run 断言机器守卫） | review-FIX-275-CODE-R0.md（F4 L95）；version-plan-0.77.0.md §5.1 | P3 | **出槽（0.78.x+ 守卫批次候选）** | (a) 观察级 P3；(b) FIX-275 验收已含 RED→GREEN 实测 + Reviewer 独立重验（243 entries/0 pyc/5.72MB），缺失不构成门禁缺口；(c) 实现 = verify_workflow.py 新断言 + 测试（新开发任务），独立于降噪主链 |
| **F-04-env**（agent-locks file_locks 环境路径锁扩展） | review-FIX-271-DESIGN-R0.md（F-04 L95）；plan-tracker FIX-274 行（"F-04 独立 FIX"）；version-plan-0.77.0.md §5.1 | P2 | **出槽（独立任务，0.78.x+）** | (a) 并发互斥 = 不同于事故实际形态（单 agent 破坏）的失效模式，R0 裁定低概率、可观测性已被 R2+R4 覆盖；(b) 安全敏感——需锁模型扩展设计审查，不宜塞入本已重载的降噪窗口；(c) 0.78.0 主链为降噪批次而非环境防护链，无承载动因 |
| **F-05 + BC-1**（R5 词表版本化 + R1(b) 备份留痕显式化 + Check 39 升 FAIL 批次） | review-FIX-271-DESIGN-R0.md（F-05 L96 / BC-1 L82）；DEC-160（收紧条件）；plan-tracker FIX-274 行；version-plan-0.77.0.md §5.1 | P2/P3 | **出槽（条件性：0.78.0 时点结构性不可满足升 FAIL）** | Check 39 升 FAIL 触发 = "连续 2 个零违规 0.77.x 版本后计算"——第 1 个零违规版本 = 0.77.0 发布后开始计；0.78.0 发布时观察窗口仅 1 个版本（0.77.0），**升 FAIL 条件不可满足**；最快 0.78.0 发布后评估下一窗口，升级时 MUST decision-log 入账（DEC-160 义务）。BC-1（备份清单字段化）建议并入同一批次 |
| **FIX-272 P2×2**（路径穿越测试 3 例 + 穿越/畸形诊断消息拆分） | review-FIX-272-CODE-R0.md（F1 L97 / F2 L98）；version-plan-0.77.0.md §5.1 | P2×2 | **出槽（0.78.x 登记；M-0 可复议）** | (a) Reviewer 独立 14/14 探针验证拦截全部正确（安全无缺陷，P2-1 仅为回归锚定缺口）；(b) P2 测试锚定 + 诊断可操作性，非阻塞；(c) 入槽 → 需 triage 机器入账 + DEC + 开发审查链，改变 0.78.0 范围（规划纪律 5/6）；(d) 与降噪主链不同域（守卫测试域） |
| **RISK-044 quick-scan** 秒级子集 | risk-log RISK-044 行（2026-08-26 检查点通过）；DEC-149；DEC-164（措辞收窄 0.78.x+）；DEC-167 | — | **维持出槽（0.78.x+；复评结论见 §6.1——本次版本规划即复评点）** | (a) DEC-167 检查点通过（实测 32.8s/29.6s 满足修订验收「<60s 且每会话仅一次」）；(b) quick-scan = 未注册设计+开发任务（子集划分+性能优化+测试），入 0.78.0 挤占降噪主链范围（DEC-167 备选 B 未选先例）；(c) 用户当前未反馈延迟不可接受；(d) M-0 若选前移 → 需新任务注册 + 开发审查链，扩张范围——如实披露 |
| **G3 扩展**（plan-tracker 行/完成记录写时结构看护） | review-FIX-278-DESIGN-R1.md（W-3 "登记后续任务候选" + BC-3 "残余披露、登记 G3 扩展后续"） | P2 面 | **出槽（0.78.x+ 后续任务候选）** | G3 首波落地 = 0.78.0 主链；扩展（Coordinator 直写 plan-tracker/完成记录的结构看护）为新开发引擎，独立任务为宜——与主链批次解耦（先观察 G3 write-guard 实绩再扩展，BC-6 自愈面验证） |
| **G5**（task-priority-analysis 重复抑制） | docs/requirements/audit-148-v1-verify-alarm-validation.md（L184 优化方向表）；DEC-166（第一批 = G4/F+G1+G2+G3，G5/G6 未入选） | 低收益 | **出槽（0.78.x+ 噪声优化池候选）** | 消除重复 881×2 输出，收益 -1.7KB/会话（audit-148 L184 量化）；用户 2026-08-25 裁定第一批未含 G5/G6；与 G1（已落地 top-N）同域但为独立小任务，建议随降噪第二波批次合并登记 |
| **G6**（告警追查预算提示） | docs/requirements/audit-148-v1-verify-alarm-validation.md（L185 优化方向表）；DEC-166 | 低收益 | **出槽（0.78.x+；与 G1 协同候选）** | 追查 25KB → 1 行提示（audit-148 L185）；**G1 指引行（"共 N issues，--level strict 查看全部"）已在 FIX-278 落地——部分覆盖**；剩余面（"详见 <command> 获取 full report"）为收尾提示，可随 G5 同批评估 |
| **W-7 / BC-7**（状态格混合终态子类「⏳/🔄 + ✅ 已发布/已关闭」无「完成」→ 判 ACTIVE → 保守漏降级） | review-FIX-278-DESIGN-R1.md（N-2/W-7 + §3 BC-7 新挑战；本仓静态实例 REL-068/069） | 中低 | **出槽（后续 marker 扩展；不阻塞）** | 保守方向（不掩盖当前工作——该子类 legacy 缺口保持 FAIL，fail-safe 一侧）；缓解 = 扩展终态 marker 集（无 ✅ 的 已发布/已关闭/已终止/已撤回/失效/不可信/取消/废弃 形态，或混合格尾部终态胜出）；建议与 G2 L-A 后续触碰合并评估；若 M-0 入槽 → marker 集扩展属判定面修改，需 DEC + 审查链 |
| **N-P2-1**（`_legacy_blocker_keys` 重复定义——死代码遮蔽） | review-FIX-278-CODE-R1.md（N-P2-1，review_domain.py:1613-1628 旧实现 vs :1680-1684 委托版） | P2 | **出槽（下轮触碰清理；可随 0.78.x 批次）** | 纯维护清理（删除旧定义）；语义等价无运行时错误；Reviewer 建议"随下轮触碰清理"——0.78.0 主链不触碰该函数域（无同窗动因）；若 M-0 选"同槽清理" → 小任务可并 |
| **N-P2-2**（两处惰性 `parse_completed_task_ids` 注入——mock 失效死注入） | review-FIX-278-CODE-R1.md（N-P2-2，test_verify_workflow.py:15264-15268 + :15418-15421） | P2 | **出槽（下轮触碰清理；测试语义）** | 用例仍绿仅因断言不依赖 completed（前者日期豁免、后者类型豁免）；未来动 completed 集合时无保护——建议与 :14884 对齐（patch task_priority.parse_task_dependencies 行源）；归属测试卫生，可随 FIX-279 触碰批次或独立 |
| **P3 组**（N-P3-1 docstring 160→130 / N-P3-2 Check 19 谓词不同源 / N-P3-3 规则 3-4 交互边界 / N-P3-4 written_cols 簿记 / DESIGN N-3/N-4/N-5 / 前轮 P3-2/P3-4 维持） | review-FIX-278-CODE-R1.md（N-P3-1~N-P3-4 + §7）；review-FIX-278-DESIGN-R1.md（N-3/N-4/N-5）；review-FIX-278-CODE-R0.md（P3-2/P3-4 维持观察） | P3 | **出槽（讨论级；随批次归并/观察）** | 全部讨论级非阻塞（docstring 陈旧/谓词同源观察/边界理论/簿记边角/组合测试建议）；N-5/Check 19 谓词不同源 = 后续对齐候选（与 N-P3-2 同源）；不构成 0.78.0 门禁缺口；建议登记观察池，随下轮触碰批量归并 |
| **FIX-279 遗留观察项**（P2-1 写入行缺失路径回归测试 / P2-2 remediation 定位标准行来源 / P2-3 EVD fallback 残余误报 + P3×3） | DEC-168（后续动作栏："登记 0.78.x 队列评估（不阻塞合并）"） | P2×3+P3×3 | **出槽（0.78.x 队列评估项）** | DEC-168 显式登记 0.78.x 队列评估、不阻塞合并；与 FIX-279 本体（入槽）解耦——本体入槽 + 观察项出槽登记，避免范围扩张 |
| **FIX-276 R0 P2 遗留 F-01**（README L204 引号非逐字——引号纪律） | plan-tracker FIX-276 行（"0.77.0 后小修候选"；review-FIX-276-CODE-R0 P2 遗留） | P2 | **出槽（0.77.0 后小修候选——即 0.78.x）** | 文档引号纪律项（README 分级声明节引号与 SKILL L272 非逐字）；与 0.78.0 主链无耦合；可随 docs 面批次/下次 README 触碰合并（FIX-269 R0 F-04 先例） |
| **change-triage SKILL "四步"描述陈旧** | plan-tracker FIX-271 行（边缘发现）+ FIX-273 P3-3 + version-plan-0.77.0.md §8 观察项 2 | P3 | **出槽（随下轮触碰合并）** | 文档描述陈旧（实际五步）；观察级；可随 N-P2 触碰批次（change-triage 域）顺带合并 |

### 5.2 裁决后 0.78.0 范围预判

- **推荐终态（用户确认后）**：0.78.0 范围 = **FIX-278（主链）+ FIX-279（契约修正）+ M5 基线小修（文档级，低成本）**；其余全部出槽登记（0.78.x+ 队列：F-03/F-04/F-04-env/F-05+BC-1/FIX-272 P2×2/quick-scan/G3 扩展/G5/G6/W-7/N-P2/P3 组/FIX-279 观察项/F-01/"四步"陈旧）。
- 若用户选择 M5 小修也出槽：0.78.0 范围 = FIX-278 + FIX-279（零新开发窗口，最短）；M5 基线条目在发布文档如实披露（Check 10 1 项既有基线）。
- 任一入槽项（含 M5 小修）均须在 M-1 启动前完成注册与实施链；**超期自动出槽**（DEC-163 N=2 会话上限惯例）。M-0 后范围确定时复核 90% 完成率（规划纪律 7）。

---

## 6. 风险披露

| 风险 | 状态 | 0.78.0 处置 |
|---|---|---|
| RISK-036（official marketplace operations） | **保持打开**（2026-09-30；1.0.0 硬阻塞；无关闭标准满足） | 0.78.0 **不关闭**；不声明 official/marketplace approval |
| RISK-039（治理数据膨胀与架构腐化看护） | **保持打开**（2026-09-30；1.0.0 硬阻塞） | 0.78.0 **不关闭**；不声明 universal/full runtime support |
| RISK-044（`--summary-only` 31-32s 超设计 <15s 门禁） | **已接受（DEC-149）——2026-08-26 检查点复核通过（维持）（DEC-167）**；**下轮复评 = 0.78.x 版本规划（本次）** | **复评结论建议见 §6.1**（供 M-0 确认）；quick-scan 裁决见 §5.1（维持出槽） |
| M5 Check 10 基线（`m5_option_list_no_auq` 1 项） | 既有基线（health 105 首个 FAIL；version-plan-0.77.0.md L154 触发；DEC-167 登记 0.78.x 小修） | 小修入槽建议（§5.1）；若出槽 → 发布文档如实披露基线条目；**本 0.78.0 规划文档同型样式属同一基线面**（小修入槽可顺带覆盖） |
| 既有基线 FAIL 披露惯例 | 0.77.0 发布时 3 基线 FAIL（archive trigger gap / origin SSH 限制 / governance health）；check-governance 105 issues（2026-08-26 bootstrap 实测——实时 posture） | 0.78.0 候选/释放态按 REL-067/068/069/070 先例**如实分类披露**；`governance health` 类以候选打包实测为准（零 `.governance/` 文件由发布包触碰）；`origin SSH` 环境限制保持（github-https 为标准推送面） |
| DSH preset 时滞（RISK-D5） | 已知 | 0.78.0 迁移说明随发布文档：`git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`；未 sync 前旧 preset 携带旧版本行——不得宣称未 sync 安装的会话级效果 |

### 6.1 RISK-044 复评（本规划时点——DEC-167 既定复评点）

**背景口径（DEC-164/DEC-167）**：08-28 为权威检查点 → 2026-08-26 检查点复核通过（维持接受，DEC-167）；DEC-167 明确"**下轮复评 = 下次版本规划（0.78.x）**"——本次版本规划即该复评点。

**复评输入事实**（risk-log RISK-044 行 + DEC-167，零新测）：

| 事实 | 值 | 来源 |
|---|---|---|
| 接受口径 | DEC-149：接受 31s（每会话一次性成本，完整看护优先于秒级体验）；REQ-145.7 验收修订为「单次 <60s 且每会话仅一次」 | risk-log RISK-044；DEC-149 |
| 检查点实测 | FIX-278 发布后 2026-08-26 两次：**32.8s / 29.6s**——与 DEC-149 记录（31-32s）一致，满足修订验收 | DEC-167 |
| quick-scan 出槽 | DEC-164 措辞收窄「0.78.x+ 候选」；DEC-167 维持 0.78.x+（暂不前移） | DEC-164；DEC-167 |
| 检查点状态 | 2026-08-26 检查点通过，风险状态保持「已接受」 | risk-log RISK-044 |
| 附随披露 | M5 基线小修登记（version-plan-0.77.0.md L154 裁决表样式） | DEC-167 ④ |

**复评结论建议（供 M-0 用户裁决，非最终决策）**：

1. **维持接受（推荐）**——复评输入与 DEC-167 检查点完全一致（30-33s 稳定、满足修订验收「<60s 且每会话仅一次」）；无新事实触发「延迟不可接受」判断；用户自 2026-08-23 起未反馈摘要延迟不可容忍（DEC-167 ② 依据保持）。
2. **quick-scan 维持 0.78.x+ 出槽（推荐）**——本规划时点无新事实改变 DEC-164/DEC-167 裁决；若前移入 0.78.0 = 新任务注册（子集划分+性能优化+测试）+ 开发审查链，将挤占降噪主链范围（DEC-167 备选 B 未选先例，如实披露代价）。
3. **下轮复评登记**：0.79.x（或下一版本规划）——M-8 发布收尾时登记 risk-log（由 Coordinator 写回）。
4. **RISK-036/039 不关闭（本任务边界=不关闭）**：1.0.0 阻塞保持打开（2026-09-30），0.78.0 不涉及。

---

## 7. No-overclaim 边界

本规划（及后续 0.78.0 候选）**不声明**：

- 1.0.0 production-ready / 1.0.0 正式发布
- official approval / zcode official approval / marketplace approval / curated listing
- universal / full runtime support
- external first-session pilot success（外部项目首会话试点成功）
- RISK-036 / RISK-039 关闭
- 任何历史已发布 version tag 的状态变更（v0.77.0 及之前未受本版影响）

并**不创建、不证明** `v0.78.0` tag 存在（candidate-only；`release_authorized=false`——transition/tag/push 待用户授权，DEC-143 基线）。主链语义 = 治理降噪批次（G1/G2/G3/G4-F + write-guard 契约），不关乎官方收录/市场批准；FEAT-010 遗留 gh topics 标签（Coordinator 职责）独立于本发布包；**M-1 候选打包不在本任务**（待 M-0 裁决）。

---

## 8. 边缘问题与观察项

1. **FIX-279 未推送态**：commit `c193299` 审查通过但未推送（plan-tracker L255）——M-1 前置动作 = 推送确认 + `release-ledger --no-remote` 在候选 commit 后重跑；若 M-0 前仍未推送，候选打包须披露未推送 commit 面（REL-066 候选后推送先例）。
2. **M5 基线小修自指性**：本规划文档 §5 裁决表沿用 0.77.0 同型样式——M5 小修入槽后可豁免/注记当前与后续规划文档，避免基线条目持续累积（Check 10 当前 1 项）。
3. **路线图 0.78.0 行缺失**：M-1 MUST 新增（状态=规划/已发布随发布推进；规划纪律 1/5/8）；0.71.0/0.72.0 行仍缺（fact-source 观察项登记 0.76.x 候选——非本版本范围，plan-tracker L451 注记）。
4. **gh topics 标签**（FEAT-010 遗留，Coordinator 职责——随包启动冒烟已过，标签待执行）：独立于本发布包（session-snapshot L48；0.77.0 规划 §7 同口径）。
5. **FIX-279 遗留观察项**（DEC-168 后续动作 P2-1/P2-2/P2-3 + P3×3）：0.78.x 队列评估项（§5.1 已登记），不阻塞合并。
6. **基线数字漂移惯例**：health 103/105/108 等不同时点取值——后续发布文档写"以候选打包实测为准"，不引用旧值作新声明（0.76.0 checklist 先例正确做法）。
7. **FIX-278 全量测试基线**：pytest 1976 passed / 27 failed（既有基线：24×WSL 环境 + cleanup + 计时抖动 + snapshot-freshness；EVD-FIX-278 注记 "R1 Reviewer 披露未复跑，待 0.78.0 门禁复验"）——M-2 门禁复跑时验证（EVD-904 后基线 1985 tests/0 新增失败归因）。
8. **YAGNI 披露**：§5.1 出槽行数较多系既有登记候选的如实汇总（每行均有来源留痕与依赖理由）；无机械堆列——全部为已登记/已裁决候选，M-0 只裁决入槽/出槽而非重新立项。