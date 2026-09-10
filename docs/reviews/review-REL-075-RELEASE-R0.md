# Release Review — REL-075-M3-RELEASE (0.79.0 candidate) — Round 0

- **Reviewer**: Release Reviewer Agent（角色规范 `agents/release-reviewer.md` + `skills/release-review/SKILL.md` 全文加载）
- **审查对象**: staged candidate（`git diff --cached`，27 文件 = 24 M 版本投影/发布面 + 3 A 新增 docs/release 三件套；candidate commit 尚未创建——本审为 commit 前置流程，M-3 先于 candidate commit）
- **窗口**: `v0.78.1 (6b5e7bf) .. HEAD (97168f8)`，34 commits
- **日期**: 2026-09-10
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；0 BLOCKING / 4 WARNING / 2 SUGGESTION；**go** 建议——理由见 §4）
- **round**: R0（首轮，无前轮 findings 比对义务）

---

## 0. 事实基线（本审查实测 vs 采信声明）

**Reviewer 亲测（只读 git + 文件读取）**：

| # | 事实 | 结果 |
|---|---|---|
| 1 | staged 文件清单与构成 | 27 文件（24 M + 3 A），与任务申报「版本投影 24 文件 + CHANGELOG + 三件套 + hooks 自升级面」吻合 |
| 2 | 版本投影 diff 全文逐行核 | 全部 0.78.1→0.79.0 单调一致：4 plugin.json + marketplace.json + package.json + manifest.json + 双 SKILL.md frontmatter（源 + e2e fixture）+ e2e plan-tracker + @bootstrap-version 标记面（AGENTS.md / e2e CLAUDE.md / governance-init.md ×3 段 / adapters/dsh/AGENTS.md.template）+ presets + adapters 双 agent.cordis.yml 版本行 + 4 hooks @version + REQUIRED_SNIPPETS 6 版本钉 |
| 3 | 残留版本串扫描（`git grep --cached '0\.78\.1'` 全投影面） | 零漏改——残留均为合法历史/fixture（releases/0.78.1.json 历史台账、FEAT-020 golden_samples 冻结时点快照、测试 fixture、README ×2「GitHub master still serves 0.78.1」推送前提示〔措辞已随 bump 更新为 v0.79.0 前语境，准确〕） |
| 4 | 窗口核定 | `git log v0.78.1..HEAD --oneline` = **34 commits**，HEAD=97168f8（FX-195）；tag `v0.78.1` 存在且 peel=`6b5e7bf`——与 CHANGELOG/checklist 申报一致 |
| 5 | CHANGELOG 0.79.0 节 | 存在（L5，日期 2026-09-10）；五段完整（导语/Added/Changed/Fixed/Validation/Boundaries）；34-commit 窗口逐 commit 列举 + 29 任务行（checklist Change Inventory #1~#29）算术吻合 |
| 6 | 三件套存在性与 needles | release-checklist（99 行）/ rollback-plan（71 行）/ feature-flags（36 行）三文件均含 No-overclaim needles（0.78.1 R0 F-1 先例要求满足）；风险状态措辞与 risk-log 口径一致（RISK-036/039 打开、RISK-049 已关闭〔DEC-185 口径限定〕、RISK-044 缓解中、RISK-046 根因已交付维持打开至 2026-09-30） |
| 7 | 归档迁移备份恢复路径如实性 | `%TEMP%\governance-backup-20260910-prefix301` **实际存在，863 文件**——与 rollback-plan S2/EVD-983 申报（863 文件）精确一致 |
| 8 | 回滚两级边界复刻 | rollback-plan §「回滚边界」与 version-plan-0.79.0 §3.1 逐项保真（候选/transition 态 = git revert 不触碰任务链；已发布 tag = governed recovery only、绝不静默重指）；S1 未演练**如实声明**（rollback-plan L65，不宣称「已在测试环境验证」） |
| 9 | VERSIONING.md L12/L37/L13 原文 | version-plan §2.1 引用逐字准确（L12 Minor 三支触发 / L37 SKILL MUST 新增→MINOR / L13 Patch 面） |
| 10 | loop claim gate 语义（verify_workflow.py L20529-20599） | 门 = semantic claim 扫描 verdict + identity attestation 双维，`pass` 需双 PASS，issues 合并进 check-release——fail-closed 设计；FIX-299 exit 契约注释在案 |
| 11 | AUDIT-152 机器可读清单 | `infra/tests/env_failure_classification.json` 存在 |
| 12 | docs/reviews/ 无既有 REL-075 报告 | 本报告为 R0 首发 |

**采信（Coordinator M-1/M-2 实测通报，任务授权采信 + 上述物理抽查佐证）**：M-1A 版本面五检查全绿（version-consistency 13 文件 + markers/projection 15/manifest/cross-ref/injection 28 anchors/verify 全量）+ 棘轮 R1~R7 PASS（R1 零增长 24,329）；M-1B CHANGELOG 四段 + 三件套；M-2 14 静态门全 PASS（release docs staging 后绿）+ dsh upgrade regression PASS（新门实战）+ loop fuse/changelog PASS；3 FAIL 既有分类态（§4 逐项裁决）。Reviewer 未重跑引擎命令（角色只读约束 + 任务范围「git 只读+读文件」）——上述抽查（#2/#3/#4/#5/#6/#7）与通报数字无矛盾。

---

## 1. 五维度审查（role 文件审查维度逐项）

### 1.1 发布检查清单完备性 — **PASS**

- **对照 0.78.1 结构**：0.79.0 checklist 为 0.78.1 结构超集——保留 Version/Window/Status + Gate Results + Review Evidence + 出槽登记 + No-overclaim 全部节，新增 Release Scope 表（8 分组含 0.80.0 重构线「随窗交付注记」与治理记录面两组——比 0.78.1 Scope 列表更完备）+ Change Inventory 29 行逐 commit 表（34 commits 任务化映射，审查终态 + EVD 逐行可溯）。
- **三件套对照**：feature-flags 延续「无 runtime flag 声明 + Behavior 表」（0.78.0/0.78.1 先例）且 Behavior 表逐项给出确定性旁路（--force / 删 Step 4b / --skip-execution-gates / fail-open）——flag 审查维度无对象即无 kill-switch 义务，旁路文档化即等价物；rollback-plan 为 0.78.1 结构超集（新增 Rollback Triggers 6 条确定性触发判定 + S1/S2/S3 步骤 + Reversibility 表含预计回滚时间——0.78.1 无 Triggers/Reversibility 表，0.79.0 更强）。
- **回滚方案两级边界**：见事实 #8——复刻保真。
- **归档迁移备份恢复路径如实性**：见事实 #7——路径真实、计数精确、恢复步骤（Copy-Item 回 .governance + check-archive-integrity 校验守恒 + 禁手工拼合）可执行；「迁移本身幂等（FIX-301 验证）」有 EVD-982 支撑。S1 未演练如实声明 ✓（stage-release 硬门槛「回滚已验证」按 0.76.0/0.77.0/0.78.1 先例口径 = 可逆性分析 + 门禁复跑载体，本仓无独立测试环境——声明诚实不越界）。
- **硬门槛「清单全部 PASS=100%」判定**：清单自身 Gate 表设计为 M-2 回填（「不预填 PASS」明文），物理 M-2 结果 = 14 静态门 PASS + 3 既有分类态 FAIL 披露——与 #10/#13 行预期（「核心静态门禁 PASS + 既有基线 FAIL 分类披露」）逐行相符，**按 0.78.1 同型口径判 PASS**；回填完成义务见 W-1。

### 1.2 CHANGELOG 用户视角与 breaking 标注 — **PASS**

- **四段 + Validation/Boundaries 完整**；导语含 MINOR 定位、窗口核定方法、逐 commit 清单、版本归属注记（DEC-184 Q4「0.79.0∥ / 0.80.0 任务行随窗交付」如实披露——无隐藏带入）；Added 每条带「用户视角：」行（13 条）——用户价值可读。
- **Breaking changes：无——论证核验通过**：逐入槽项核对方向——FIX-291（FAIL→WARN 历史迁移 + 白名单 = 放宽；fail-safe 边界「ACTIVE/真实 nonzero 恒 FAIL」锁定不放宽）、FIX-292（谓词委托权威链，消除误报 = 向真实终态对齐）、FEAT-011/017（新增守卫，advisory 非阻断 + SKIP 降级）、FEAT-012 G5（默认缓存 = 唯一默认行为变更项，但有 --force 旁路 + 首次义务穿透 + fail-open，输出面非接口面；G6 纯输出尾行）、FEAT-013（新增 API + Check 26 expected_new 可选向后兼容）、FEAT-016（新 gate 组件 + 显式 [SKIP]）、FIX-294/295（豁免 + 披露 = 放宽）、FIX-296（修静默数据丢失）、**FIX-299（唯一行为语义反转项：恒 exit 1 → healthy/exit 0——性质为恢复文档化契约的缺陷修复，消费面 grep 实证无 quirk 依赖者〔CHANGELOG Fixed 载明〕，不构成 breaking）**、FIX-300（判定规则零改动，仅 verdict_scope 显式化）、FEAT-018/019/020（新增脚本/棘轮/快照 harness，零引擎改动 + 前瞻性 fatal）、FIX-301/302（修复/措辞）。无接口删除/重命名、无默认行为无旁路破坏——「无 breaking」成立。
- 用户影响面：无迁移指南义务（无 breaking、无安装形态变更〔FIX-290 属 0.78.1〕）；DSH preset 时滞迁移说明在三件套 + CHANGELOG 四处一致载明。

### 1.3 版本一致性（抽查） — **PASS**

- 事实 #2/#3：投影面 diff 全量核 + 残留串扫描零漏改；REQUIRED_SNIPPETS 6 钉（4 plugin.json + marketplace + package.json + manifest）与 0.78.1 先例同型；bootstrap 标记面含根 CLAUDE.md（gitignored，本会话系统注入内容已示 0.79.0——已同步）；host plan-tracker 记录版本 0.78.1 = 既有 advisory WARN 同型惯例（打包后 M-8 回写）。
- 采信 M-1A 五检查全绿 + 棘轮 R1~R7（R1 24,329 零增长；sanctioned +60 有 FEAT-013 审计先例）——与抽查无矛盾。

### 1.4 Feature Flag — **PASS（无对象）**

无 runtime flag 声明延续先例；行为变更项旁路文档化（见 1.1）；Kill Switch 义务不适用，等价物 = 各确定性旁路 + 回滚文档。

### 1.5 版本号合规（semver + 范围-版本号一致性） — **PASS**

- **MINOR 论证成立**：L12 三支全命中（①新增 B/C 级自动化能力：governance-write-guard 检查器 / dsh_upgrade_regression gate 组件 / ArchGuard 棘轮 / 契约矩阵 harness；②判定规则扩展：Check 30 形状/终态 + 30c 分类 + 执行包谓词——G2/DEC-169③ MINOR 先例同型；③累积主题里程碑：降噪第二波 G5/G6）+ L37 直接命中（M1.2 MUST 新增已落盘 behavior-protocol + SKILL L116/L126 + e2e 投影）。
- **非 MAJOR**：L11 触发面（删除/重命名 MUST、Gate 行为语义破坏、字段格式破坏）零命中——MUST 为新增非删除，Gate 语义为扩展非破坏。
- **PATCH 不足以承载**：新增 MUST 规则 + 新增子命令/gate 绘制按 L34/L37 均 ≥PATCH 以上，PATCH 定位将与 G2 先例自相矛盾。0.78.1→0.79.0 不跳号、路线图行预留一致（version-plan §0 核对）。
- 范围-版本号一致：34 commits 中 0.80.0 定位任务（AUDIT-150/151/152、DOC-003、FEAT-017/018/019/020、FIX-301/302）「物理合入本窗随 0.79.0 工件交付」的归属注记诚实（DEC-184 Q4），不构成范围漂移——出槽登记 §完整（version-plan §5.1 21 行裁决表全承载）。

---

## 2. 硬门槛裁决（role 文件五硬门槛）

| 硬门槛 | 判定 | 依据 |
|---|---|---|
| 发布检查清单全部 PASS | **PASS**（0.78.1 同型口径：核心静态门 PASS + 既有基线 FAIL 分类披露；回填义务 W-1 非 candidate 缺陷） | §1.1 + §4 |
| 回滚方案存在且已验证 | **PASS**（先例口径 = 可逆性分析 + 门禁复跑载体；S1 未演练如实声明；备份恢复路径实测真实） | 事实 #7/#8 |
| CHANGELOG 用户视角完整 | **PASS**（关键段全覆盖 + 逐条用户视角行） | §1.2 |
| breaking changes 标注 | **PASS**（=无 breaking，逐项方向核验） | §1.2 |
| Feature Flag 关闭验证 | **N/A→PASS**（无 flag 声明 + 旁路文档化） | §1.4 |

---

## 3. Findings

**BLOCKING：0**

**WARNING：4**（均为流程收尾义务/披露要求，非 candidate 内容缺陷——不构成未解决阻塞）

- **W-1（checklist Gate 表回填——MUST before candidate commit）**：`docs/release/release-checklist-0.79.0.md`「Candidate Gate Results」#1~#12 仍为「待 M-2 回填」，且 evidence-log 尚无 M-2 实测证据行（热表顶至 EVD-989 + TRIAGE-REL-075）。处置：candidate commit 前（或随候选 commit——0.78.1「门禁/双审回填已并入候选」先例）回填 #1~#10/#12 = M-2 实测值（14 静态门 PASS + 3 FAIL 分类披露原文），#11（release-ledger NATIVE_CANDIDATE）按其自身注记为 **candidate commit 后执行 + 记录**，#13/#14 维持 M-6 待回填；同轮把 M-3 双审结论（含本报告路径与终态）补入「Review Evidence（M-3）」节，并机录 M-2 证据行（review-record/证据通道——禁手写 REVIEW 行）。**不得预填 PASS、不得将 UNKNOWN/BLOCKED 包装为 PASS**（清单自注 + gate #11 备注原文）。
- **W-2（健康基线数字漂移的回填口径）**：M-2 实测 33 vs EVD-983 迁移后 31（+2）。回填 #7 行时 MUST 附构成 A/B 对照（零新增实证——逐类归属），不得只引数字（「基线数字漂移惯例：打包期以实测为准，不引用旧值作新声明」为清单自载纪律）。
- **W-3（CI ubuntu 权威测试面未跑——push 凭据阻塞）**：本地 Windows 全量 + AUDIT-151/152 分类（32F = 24 bash/WSL 环境族 + 6 数据耦合 + 2 已知缺陷，真回归 0，机器可读清单在案）支撑发布判定成立，但 CI 权威面遗留——回填 #6 行 MUST 如实披露「CI ubuntu 未跑（凭据阻塞）」，并登记发布后补跑义务（凭据恢复即执行），不得表述为「CI 绿」。
- **W-4（loop claim gate semantic BLOCKED 跟踪）**：该门为 check-release 有机组成部分（issues 直接合并，fail-closed），identity 维 PASS、semantic 维 BLOCKED（数据耦合——扫描器 ↔ 治理文档/live plan-tracker 行族，AUDIT-152 新类）。回填 #10/#13 行时 MUST 披露该 FAIL 及其分类；修复跟踪锚定 AUDIT-152 N1/N2 候选（0.80.0 承载），不得在候选/释放态报告中隐去该 issues 项。

**SUGGESTION：2**

- **S-1**：`infra/contract_matrix/golden_samples.txt` 保留 0.78.1 时点版本串（FEAT-020 冻结快照）——按设计为冻结 fixture 合法残留；M-1A/M-2 棘轮 R1~R7 + verify 在 staged 树上已 PASS（采信），无需动作；若 0.80.0 契约面变更触发快照再生成，循 documented sanctioned regen（80→82 键先例）留审计即可。
- **S-2**：host `.governance/plan-tracker.md` 工作流版本仍 0.78.1（advisory WARN ×2 同型惯例）——M-8 路线图回写时一并 bump（version-plan §3 M-8 既定动作，勿遗漏）。

---

## 4. M-2 姿态裁决（3 个既有分类态 FAIL 的发布可接受性）——**GO**

先例基线：0.78.1 以「governance health 117（0.78.0 打包基线 127，EVD-894 宿主 posture 先例）+ pytest 27 failed 分类归属」披露后发布，check-release 报 FAILED-2-issues 分类披露同型通过（release-checklist-0.78.1 L24/L25/L28 实录）。

| FAIL | 定性 | 与先例对比 | 裁决 |
|---|---|---|---|
| ① governance health 33（advisory 姿态） | 宿主 posture 既有类；A/B 零新增实证 | **严格优于先例**（117→33；0.78.0 基线 127）；构成可溯（AUDIT-149 诊断 + FIX-292/294/295 降噪链逐步留痕 + EVD-983 迁移后构成一致） | **可接受** |
| ② unit tests exit=1（AUDIT-152 分类 32F：24 bash/WSL 环境族 + 6 数据耦合〔审查文档 claim 族 + live plan-tracker 行族〕+ 2 已知缺陷；真回归 0） | 环境敏感/数据耦合/已知缺陷三类全分类；机器可读清单 `env_failure_classification.json` 在案（Reviewer 实测存在） | 0.78.1 以 27F 分类发布同型；本版分类学**更强**（逐例 100% 定性 + 机器清单 + 当日全量 2,304 收集算术闭合）；残余 = CI ubuntu 权威面（凭据阻塞）——与 0.78.0/0.78.1 推送/网络受限先例同族，且本地 Windows 口径与先例发布姿态一致 | **可接受**（W-3 披露 + 发布后补跑义务） |
| ③ loop claim gate semantic BLOCKED（identity PASS） | fail-closed 门按设计工作；语义维阻塞根因 = 数据耦合（非 shipped 工件缺陷——插件侧 loop 声明不过度宣示，identity 维即证）；AUDIT-152 N1/N2 修复候选已登记 | 0.78.1 窗内 test_loop_runtime_claims 族失败同为分类发布先例；identity/semantic 双维中**实质维（identity）PASS**，semantic 维属检查器与治理文档的数据耦合面 | **可接受**（W-4 披露 + 0.80.0 跟踪） |

**综合**：三项均命中先例模式（既有/环境/数据耦合分类 + 零真回归 + 如实披露），且数字与分类学质量均优于先例发布。无未分类失败、无真回归、无范围漂移、版本面全绿、新 gate（dsh_upgrade_regression）实战 PASS。**go**——建议 Coordinator 在完成 W-1 回填后落 candidate commit，按 DEC-143 呈报 M-4 用户授权。

---

## 5. 审查边界自检（SKILL 红线）

- 本审查仅基于可复查事实：staged diff、git 只读命令输出、release docs/CHANGELOG/VERSIONING/version-plan 文本、evidence-log 既有行、备份目录实测；M-2 引擎数字按任务授权采信并物理抽查佐证（§0）。
- 未实际重跑的检查（14 门引擎输出、pytest、ledger）未写成「Reviewer 验证通过」——全部标注采信来源；#11 release-ledger 属 commit 后义务未跑未包装。
- 未修改任何文件（唯一写入 = 本报告）；未与用户交互。

## 6. 终态

- **结论**: `APPROVED_WITH_NOTES`
- **unresolved_blockers**: `0`
- 机器记录义务归 Coordinator：review-record 持久化 `REVIEW-REL-075-RELEASE-R0`（含本终态与 round=0；禁手写 REVIEW 行），并按 W-1 完成清单回填与 M-2 证据机录。
- 后续轮次：如 coordinator 对 candidate 内容返工（非回填类修订），重 spawn 本 Reviewer 复审（R1 注入本报告路径比对修复项）。
