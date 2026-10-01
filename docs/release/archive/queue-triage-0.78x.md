# Queue Triage — 0.78.x / 0.79.x 出槽队列评估（REL-072）

- **Task**: REL-072（TRIAGE-REL-072，机器入账 2026-08-26）
- **Produced by**: Release Agent（REL-072 第一段——triage 评估；纯评估，零产品代码修改/零版本文件修改/零 tag/零 `.governance/` 写入）
- **Date**: 2026-08-26
- **基线事实**: 0.78.0 已发布闭环（REL-071 ✅，transition `afb959d` + tag `v0.78.0`（65eb6b4f，peel=afb959d）已推送 github-https——session-snapshot L10；plan-tracker 路线图 0.78.0 行 = 已发布 L457；工作流版本 0.78.0）
- **评估范围**: DEC-169 ⑤ 确认的 16 项 + DEC-171 新增 1 项 = **17 项**（零编造：每项均有来源留痕；版本规划表中找不到定义的项如实标注）
- **边界**: 只出建议不做决策；入槽裁决 = 用户（Coordinator 转 ask_user_question，DEC-143 交互基线）；纯评估不注册任务
- **Status**: 评估完成——待 Coordinator 呈报用户 M-0 裁决（0.78.1 PATCH / 0.79.0 MINOR / 入槽项集合）

---

## 0. 评估输入事实（治理记录核验，零编造）

| 事实 | 值 | 来源（留痕） |
|---|---|---|
| 已发布基线 | 0.78.0（2026-08-26；FIX-278+FIX-279+FIX-280） | session-snapshot.md L10；plan-tracker L457/L11 |
| 版本序列 | v0.77.0 → v0.78.0（MINOR 跳级；无 0.77.1/0.78.1） | plan-tracker 版本路线图（L436-457 区间） |
| 出槽队列 | DEC-169 ⑤ 16 项已确认登记 0.78.x+（decision-log L7 原文枚举）；DEC-171 新增 1 项（decision-log L180） | decision-log L7 / L180 |
| 未完成任务 | 0（174/174 完成；task-priority-analysis 结构化空推荐 no_active_tasks） | session-snapshot L19 |
| commit-msg Step 3 实证 | `grep -q "| $TASK_ID |"` 对 REL-071/REL-072（ID 加粗行）**0 命中**；对 REL-070/FIX-278/279/280（无加粗行）1 命中——缺陷真实且影响面 = 加粗 ID 行 | infra/hooks/commit-msg L234（本报告 §B.17 实测）；plan-tracker L258/L259（`\| **P1** \| **REL-071** \|`） |
| Check 39 升 FAIL 条件 | DEC-160 原文："连续 2 个零违规 **0.77.x** 版本关闭后升 FAIL"——0.77.x 系列锚定 | decision-log L176 |
| RISK-044 复评挂点 | 0.79.x 版本规划（DEC-169 ②；M-8 登记） | decision-log L7；session-snapshot L31；version-plan-0.78.0.md M-8 L74 |
| M-3 双审 SUGGESTION 项 | RELEASE-R0 S-1~S-5（发布文档精度/时点口径/对账强度/文件消歧）；DESIGN-R0 F-1/F-2/F-4（文档精度/枚举口径/计数微差）+ **F-3（标记面无机器守卫——建议登记 0.78.x 候选）** | review-REL-071-M3-RELEASE-R0.md L60-68；review-REL-071-CANDIDATE-DESIGN-R0.md L79-84 |

---

## 1. 版本定位论证：0.78.1 PATCH vs 0.79.0 MINOR

### 1.1 判定规则引用（`skills/software-project-governance/core/VERSIONING.md`）

| 条款 | 行号 | 内容 | 本 triage 适用 |
|---|---|---|---|
| Patch 触发条件 | L13 | **任何影响 agent 行为或用户可见的变更**：…skill/模板新增或修改、verify_workflow.py 新增检查项、references 文件新增/修改 | 修复+清理+测试卫生 + 文档措辞类 = PATCH 面 |
| 纯 bug 修复 | L38 | 仅修复 bug（不改变行为语义）→ PATCH | DEC-171（检查器匹配缺陷）、N-P2-1（死代码）、F-01（引号）等 |
| Patch 就是细粒度 / bump 纪律 | L19-21 | 每轮有意义的变更完成后 MUST bump PATCH——**不要攒着等 Minor** | 修复批次应立即 0.78.1 出，不宜囤积到 0.79.0 |
| 计划外变更用 PATCH | L123 | **不在当前 MINOR 范围内的变更 → bump PATCH，不占用下一 MINOR** | 出槽队列全部为 0.78.0 范围外项 → 依此条走 PATCH |
| Minor 触发条件（累积里程碑） | L12 | 累积的 PATCH 达到里程碑；或**新增 MUST 规则、新增子工作流/skill、新增 B/C 级自动化能力** | G3 扩展/W-7（规则或判定面）+ G5/G6（若作为"降噪第二波"主题）→ MINOR 支撑项 |
| SKILL.md MUST 规则新增 | L37 | SKILL.md MUST 规则新增 = MINOR（1.0.0 前可灵活处理） | 若 G3 扩展涉及 SKILL/behavior-protocol 契约新增 → MINOR |
| 不 bump 情形 | L41-46 | 仅修改 `.governance/` 治理记录 / README.md 措辞（不影响 agent 行为） | F-01（README 引号）本身**不驱动** bump——作为 PATCH 批次内小修随行 |

### 1.2 聚合判定

- **入槽建议全部为 P2/P3 修复、清理、测试卫生、文档措辞、检查器缺陷修复（PATCH 面）** → 无行为/规则面变更 → **0.78.1 PATCH 论证成立**（不跳号：0.78.0 → 0.78.1）。
- **行为/规则面项（G3 扩展 / W-7 marker 扩展 / F-05+BC-1 升 FAIL）**：建议**不入 0.78.1**（见 §2 各行理由）——其中 G3 扩展与 W-7 属判定面/规则面变更（L12/L37 面），若与 G5/G6 组成"降噪第二波"主题则由**0.79.0 MINOR** 承载（L12：新增 B 级自动化能力/规则变更 + 累积里程碑）。
- **F-05+BC-1 升 FAIL 条件严格评估**：DEC-160 原文锚定"连续 2 个零违规 **0.77.x** 版本"——0.77.0 为第 1 个；0.78.0 为 MINOR（非 0.77.x），**不构成第 2 个**；当前版本序列无 0.77.1 → 截至 0.79.0 规划时点累计 0.77.x 零违规版本 = 1 → **升 FAIL 条件结构性持续不可满足**。注：version-plan-0.78.0.md §5.1 L127 表述"最快 0.78.0 发布后评估下一窗口"系按 DEC-160 口径的会话级解读；本报告按 DEC-160 字面（0.77.x 锚定）给出**更严格结论**——若用户意图为"连续 2 个零违规版本（任意系列）"，须先修订 DEC-160 条件（decision-log 入账），该修订本身为规则面变更 → 0.79.0 MINOR 面；本报告按现状字面评估（条件不可满足）。
- **结论建议**：
  - **0.78.1 PATCH** = 修复/清理/测试卫生/检查器缺陷批（DEC-171 + N-P2-1 + N-P2-2 + N-P3-1 + FIX-279 P2-1/P2-2 + F-01 + change-triage 四步陈旧 + 可选 FIX-272 P2×2）——**全部 PATCH 面**（VERSIONING.md L13/L38/L123）。
  - **0.79.0 MINOR** = 降噪第二波/规则面批（G3 扩展 + G5 + G6 + W-7/BC-7 marker 扩展 + RISK-044 复评挂载〔DEC-169 ②〕）——**L12/L37 MINOR 论证**（写时门禁扩展 = 新增 B 级自动化能力 + 判定规则修改；W-7 marker 集 = 判定面规则扩展；RISK-044 复评 = DEC-169 ② 既定挂点）。
  - **不跳号**：0.78.0 → 0.78.1（PATCH 路径）或 0.78.0 → 0.79.0（MINOR 路径）；**禁止** 0.78.0 → 0.79.0 当 PATCH（MINOR 位语义 = 规则/能力面）。

---

## 2. 逐项评估（16 + 1 项）

> 级别/P2/P3 按来源审查定级；条件性项（F-05+BC-1）条件状态如实评估；工作量级 = 小（<1 循环）/中（1-2 循环）/大（专项任务）。

### 2.1 DEC-169 ⑤ 确认的 16 项

| # | ID | 来源（文件+行留痕） | 级别 | 依赖状态 | 工作量 | 建议 | 理由 |
|---|---|---|---|---|---|---|---|
| 1 | **F-03**（e2e commands/governance.md 投影决策：fixture-command-governance 投影注册 vs 独立维护声明） | DEC-164（2026-08-25 出槽 0.78.x 候选）；version-plan-0.77.0.md §5.1（L157）；review-FIX-269-CODE-R0（F-03）+ DEC-157 ③ | P2 | unblocked（决策型；无版本/任务依赖） | 极小（决策记录）→ 中（若裁决"注册投影"= 投影同步任务） | **继续搁置（保持 0.78.x 登记；随下次 e2e fixture 触碰批次或候选打包期由 Coordinator 落 decision-log）** | (a) 本质 = 投影契约决策（version-projections.json 未声明 commands 投影 vs PROJECTION_SYNC_PATTERNS 含 commands/*.md 且 e2e harness 以 fixture 为真运行目标——DEC-157 ③ 完整描述），无需独立开发任务；(b) 与 0.78.1 修复批/0.79.0 降噪主题均无强关联；(c) 若裁决"注册投影"→ 归入 0.79.x 投影同步任务（届时走开发+审查链） |
| 2 | **F-04**（npm pack --dry-run 断言机器守卫：0 pyc + 关键文件在包） | review-FIX-275-CODE-R0.md（F4 L95）；version-plan-0.77.0.md §5.1（L154） | P3 | unblocked | 小-中（verify_workflow.py 新断言 + 测试） | **继续搁置（0.78.x+ 守卫批次候选；不建议入 0.78.1）** | (a) 观察级（P3）；(b) FIX-275 验收已含 RED→GREEN 实测 + Reviewer 独立重验（243 entries/0 pyc/5.72MB），缺失不构成门禁缺口；(c) 实现 = verify_workflow.py 新断言 + 测试 = 新开发任务（tri M7.3 机器入账 + 审查链），0.78.1 建议定位 = 修复/清理批，混入新开发任务改变范围；(d) 建议与 0.79.x 守卫批次合并评估 |
| 3 | **F-04-env**（agent-locks file_locks 环境路径锁扩展：side_effect.blast_radius 非空时真实环境路径记入 active_tasks 参与文件锁冲突判定） | review-FIX-271-DESIGN-R0.md（F-04 L95）；plan-tracker FIX-274 行（"F-04 独立 FIX"）；version-plan-0.77.0.md §5.1（L158） | P2 | unblocked（锁模型扩展） | 中（锁模型扩展 + 设计审查 + 实现 + 测试） | **继续搁置（0.78.x+ 独立任务；不进 0.78.1/0.79.0）** | (a) 并发互斥 = 不同于事故实际形态（单 agent 破坏）的失效模式，R0 裁定低概率、可观测性已被 R2+R4 覆盖；(b) 安全敏感——需锁模型扩展设计审查，不宜塞入任何窄窗口批次；(c) 与降噪/修复域无承载动因；建议登记为独立任务（ID 登记时避开 F-04 歧义——version-plan-0.77.0.md L202 已注记命名冲突） |
| 4 | **F-05 + BC-1**（R5 词表版本化 + R1(b) 备份留痕显式化〔路径/文件数/字节数 + 校验命令输出〕+ Check 39 升 FAIL 批次） | review-FIX-271-DESIGN-R0.md（F-05 L96 / BC-1 L82）+ DEC-160（收紧条件原文：连续 2 个零违规 0.77.x 版本后升 FAIL）；plan-tracker FIX-274 行；version-plan-0.77.0.md §5.1（L155） | P2/P3 | **条件性——升 FAIL 条件结构性不可满足** | 小-中（拆分子项：词表版本化=记录级小修；BC-1 备份清单字段化=检查逻辑小改） | **继续搁置（条件不满足不构成入槽紧迫性；若用户要求前移 → 只前移独立子项〔词表版本化 + BC-1 字段化〕为 PATCH 面，升 FAIL 维持条件挂起）** | **条件如实评估**：① 0.78.0 发布时零违规观察窗口 = 1 个版本（0.77.0）；② **0.78.0 本身非 0.77.x**（MINOR 跳级），不构成第 2 个 0.77.x 零违规版本；③ 当前序列无 0.77.1 → 截至 0.79.0 规划时点累计 = 1 → **DEC-160 条件不可满足**（比 version-plan-0.78.0.md L127 的例行表述更严格——该表述隐含"下一窗口评估"，本报告按 DEC-160 字面锚定给出结论）；④ 升级时 MUST decision-log 入账（DEC-160 义务）——条件满足时点评估应挂 0.79.x 或之后；⑤ BC-1（备份清单字段化）与词表版本化为独立小修（PATCH 面），可随任意批次，**不依赖**升 FAIL 条件 |
| 5 | **FIX-272 P2×2**（F1 路径穿越测试 3 例〔`../skills/x/SKILL.md` / `/skills/x/SKILL.md` / `C:\skills\x\SKILL.md`〕+ F2 穿越/畸形诊断消息拆分） | review-FIX-272-CODE-R0.md（F1 L97 / F2 L98）；version-plan-0.77.0.md §5.1（L153） | P2×2 | unblocked（独立测试+诊断任务） | 小（3 例测试 + 1 处诊断消息分支——约 1 循环） | **建议入槽 0.78.1（可选项——随修复批合并）** | (a) Reviewer 独立 14/14 探针验证拦截全部正确（安全无缺陷）→ P2 仅为**回归锚定缺口**（P-v1 原则 4 测试看护面的补全）+ 诊断可操作性；(b) 工作量小（<1 循环）、与 0.78.1 修复批同窗口；若入槽 → 需 triage 机器入账 + DEC + Developer/Reviewer 链（M-1 前完成，N=2 上限 DEC-163 惯例）；(c) **备选**：继续搁置 → 0.79.x 守卫批次（与 F-04 同批）——两者权衡在 M-0 呈报 |
| 6 | **RISK-044 quick-scan**（`--summary-only` 秒级子集快速扫描） | risk-log RISK-044 行（2026-08-26 检查点通过）；DEC-149；DEC-164（措辞收窄 0.78.x+）；DEC-167；version-plan-0.78.0.md §6.1 | —（优化项） | **已接受风险维持**；quick-scan = 未注册设计+开发任务；**正式复评挂 0.79.x 规划（DEC-169 ②）** | 大（子集划分 + 性能优化 + 测试——专项） | **继续搁置（0.78.x+；复评点 = 0.79.x 规划）** | (a) DEC-167 检查点通过（实测 32.8s/29.6s 满足修订验收「<60s 且每会话仅一次」）；(b) 无新事实触发「延迟不可接受」；用户自 2026-08-23 起未反馈（DEC-167 ② 依据保持）；(c) quick-scan 入槽 = 新任务注册 + 开发审查链，挤占任何批次范围；(d) **下轮复评已挂 0.79.x（DEC-169 ②）**——0.79.0 规划时按复评结论再裁决，不复评前不移入 |
| 7 | **G3 扩展**（plan-tracker 行/完成记录写时结构看护——Coordinator 直写路径） | review-FIX-278-DESIGN-R1.md（W-3 L42-44 "登记后续任务候选" + BC-3 L78）；DEC-166（后续动作栏） | P2 面 | unblocked（G3 首波已落地 0.78.0；扩展 = 新开发引擎） | 中（新写时 guard 引擎 + hooks/集成 + 测试） | **继续搁置（0.78.x+ 候选；若与 G5/G6/W-7 组成"降噪第二波"主题 → 建议 0.79.0 MINOR）** | (a) 先观察 G3 write-guard 实绩再扩展（BC-6 自愈面验证——验证写时 guard 是否真遏制 Check 14 静默恶化后才扩到 Coordinator 直写路径）；(b) 扩展 = **规则面/新 B 级自动化能力**（L12/L37 面）——若入槽即 MINOR 支撑项，不宜混入 PATCH 批；(c) 独立任务为宜（与主链解耦），登记为 0.79.x 候选 |
| 8 | **G5**（task-priority-analysis 重复抑制——同会话第 2 次调用带 `--no-cache` 语义或提示「已分析，推荐未变」） | docs/requirements/audit-148-v1-verify-alarm-validation.md（L184 优化方向表）；DEC-166（第一批 = G4/F+G1+G2+G3，G5/G6 未入选） | 低收益 | unblocked | 小（输出抑制/提示分支） | **继续搁置（0.78.x+ 噪声优化池候选；建议与 G6 同批 0.79.0）** | (a) 收益量化 = -1.7KB/会话（audit-148 L184）；(b) 用户 2026-08-25 裁定第一批未含 G5/G6（DEC-166）；(c) 与 G1（已落地 top-N）同域但独立；建议作为"降噪第二波"与 G6 一并评估 → 绑定 0.79.0 主题评估（届时若入槽 = 行为面输出变更，PATCH 面 L13；作为主题性打包则 MINOR 论证 L12 累积） |
| 9 | **G6**（告警追查预算提示——summary 输出尾部附一行「详见 <command> 获取 full report」） | docs/requirements/audit-148-v1-verify-alarm-validation.md（L185 优化方向表）；DEC-166 | 低收益 | **部分已覆盖**——G1 指引行已在 FIX-278 落地（standard 档 "共 N issues，--level strict 查看全部"——behavior-protocol.md L222）；剩余面 = 收尾提示行 | 小 | **继续搁置（0.78.x+；与 G5 同批 0.79.0 候选）** | (a) 剩余收益面窄（G1 已覆盖主体）；(b) 与 G5 同批评估（降噪第二波）;(c) 若单独入槽 = 输出文本小变更（PATCH 面），可与 G5 一并作为 0.79.0 主题项 |
| 10 | **W-7 / BC-7**（状态格混合终态子类「⏳/🔄 + ✅ 已发布/已关闭」无「完成」→ 判 ACTIVE → 保守漏降级；本仓静态实例 REL-068/069） | review-FIX-278-DESIGN-R1.md（N-2/W-7 L20 + §3 BC-7 L82 + N-2 L107）；version-plan-0.78.0.md §5.1（L133） | 中低 | unblocked（G2 L-A 后置 marker 扩展） | 中（终态 marker 集扩展 = **判定面规则修改** + 测试 + DEC） | **继续搁置（0.78.x+ 后续 marker 扩展；建议与 G2 L-A 后续触碰合并评估 → 0.79.0 MINOR 候选）** | (a) 保守方向（fail-safe 一侧——不掩盖当前工作），非误降级；(b) marker 集扩展 = **判定面规则修改**（L12/L37 面）——需 DEC + 审查链；若入槽即 MINOR 支撑项（与 0.78.1 纯修复批不兼容）；(c) 建议随 G2 判定面下次触碰合并（同一语义域：状态格→终态判定） |
| 11 | **N-P2-1**（`_legacy_blocker_keys` 重复定义——死代码遮蔽；review_domain.py:1613-1628 旧实现 vs :1680-1684 委托版） | review-FIX-278-CODE-R1.md（N-P2-1 L66-70） | P2 | unblocked（纯维护清理） | 极小（删除旧定义） | **建议入槽 0.78.1（推荐）** | (a) 死代码遮蔽维护陷阱（改错一个不生效——语义等价但误导后续）；(b) 纯删除 = 不改行为语义（VERSIONING.md L38 PATCH 面）；(c) 与 FIX-279 观察项同域（review_domain 家族），0.78.1 修复批同窗触达 |
| 12 | **N-P2-2**（两处惰性 `parse_completed_task_ids` 注入——mock 失效死注入；test_verify_workflow.py:15264-15268 + :15418-15421） | review-FIX-278-CODE-R1.md（N-P2-2 L72-76） | P2 | unblocked（测试卫生） | 小（与 :14884 对齐 patch 行源或删除死注入 + 注释） | **建议入槽 0.78.1（推荐）** | (a) 用例仍绿仅因断言不依赖 completed（日期/类型豁免）——未来动 completed 集合时无保护（P-v1 原则 4 防护网面）；(b) 纯测试注入点对齐 = PATCH 面；(c) 与 N-P2-1 同源同批（同一 review 发现的修复批） |
| 13 | **P3 组**（N-P3-1 docstring 160→130 / N-P3-2 Check 19 谓词不同源 / N-P3-3 规则 3-4 交互边界 / N-P3-4 written_cols 簿记边角 / DESIGN N-3/N-4/N-5 / 前轮 P3-2/P3-4 维持观察） | review-FIX-278-CODE-R1.md（N-P3-1 L78-80 / N-P3-2 L82-83 / N-P3-3 L85-86 / N-P3-4 L88-89 + §7）；review-FIX-278-DESIGN-R1.md（N-3/N-4/N-5）；review-FIX-278-CODE-R0.md（P3-2/P3-4 维持观察） | P3 | unblocked（讨论级/观察级） | 极小（N-P3-1 纯注释）→ 观察（N-P3-2/3/4 + DESIGN N-3~N-5） | **N-P3-1 入槽 0.78.1（随 N-P2 批）；N-P3-2/N-P3-3/N-P3-4 + DESIGN N-3/N-4/N-5 + 前轮 P3-2/P3-4 继续搁置（登记观察池，随下轮触碰归并）** | (a) N-P3-1 = docstring 160→130 纯注释修正（行为限值已正确，PATCH 面，成本≈0）；(b) N-P3-2（Check 19 谓词不同源）= **语义对齐候选——若实施需判定面对齐评估**（属行为面观察，暂不实施，登记）；(c) N-P3-3/N-P3-4/DESIGN N-3~N-5 = 理论/边角/组合测试建议（讨论级），不构成 0.78.1 门禁缺口；(d) 批量归并随下轮触碰，避免碎片任务 |
| 14 | **FIX-279 遗留观察项**（P2-1 写入行缺失路径回归测试 / P2-2 remediation 定位标准行来源 / P2-3 EVD fallback 残余误报 + P3×3） | review-FIX-279-CODE-R0.md（P2-1 L58 / P2-2 L59 / P2-3 L60 + P3-1 L61 / P3-2 L62 / P3-3 L63）；DEC-168（后续动作："登记 0.78.x 队列评估"）；plan-tracker FIX-279 行（L255 尾） | P2×3 + P3×3 | unblocked（FIX-279 本体已随 0.78.0 发布，观察项与其解耦） | 小-中（P2-1 补 1 测试；P2-2 消息/文档改进；P2-3 权衡评估） | **P2-1 + P2-2 建议入槽 0.78.1；P2-3 + P3×3 继续搁置（登记观察池）** | (a) P2-1（写入行缺失 → 显式 issue 的回归测试）= FIX-279 契约组件无防护（P-v1 原则 4）——补 1 用例，PATCH 面；(b) P2-2（remediation 消息不提示标准行可能为历史旧行；与 docstring 范围契约张力）= UX 消息/文档改进，不改行为语义（PATCH 面）；(c) **P2-3（EVD fallback 残余误报——无 TRIAGE 行族旧库 + EVD 首行 <10 列时首次 triage 仍 fail-closed）**：fail-closed 取向正确，误报 vs 漏报权衡需独立评估（可能需 DEC 规则权衡）——建议 0.79.x 专项评估不入 0.78.1；(d) P3×3（重复行/排序场景/注解/边缘断言）= 后续测试候选，随 P2 批或观察池 |
| 15 | **F-01**（README L204 引号非逐字——引号纪律；与 SKILL L272 非逐字） | plan-tracker FIX-276 行（"0.77.0 后小修候选"；REVIEW-FIX-276-CODE-R0 P2 遗留）；version-plan-0.77.0.md §5.1（L156 区域 F-01 出槽行）；review-FIX-269-CODE-R0（F-04 先例） | P2 | unblocked（文档引号纪律） | 极小（引号逐字化） | **建议入槽 0.78.1（推荐——文档级极小修）** | (a) 引号纪律项（README 分级声明节引号与 SKILL L272 非逐字——宣示面保真）；(b) 成本极小（<0.1 循环），随 docs 面批次顺带；(c) 按 VERSIONING.md L45-46 该更改本身不驱动版本号——作为 0.78.1 PATCH 批次内容随行（不影响 PATCH 定位：批次内混合文档小修 + 修复，全部 PATCH 面） |
| 16 | **change-triage SKILL "四步"描述陈旧**（实际五步） | plan-tracker FIX-271 行（边缘发现）+ FIX-273 P3-3 + version-plan-0.77.0.md §8 观察项 2（L201） | P3 | unblocked（文档措辞） | 极小（1 行措辞） | **建议入槽 0.78.1（推荐——随 N-P2 触碰批次顺带；change-triage 域）** | (a) 文档描述陈旧（实际五步——FIX-271 已引入第五步"执行副作用声明"）；(b) 观察级但措辞修正成本≈0；(c) 与 N-P2-2（test_verify_workflow.py）同属 change-triage/verify 域——但注意：**change-triage SKILL 修改 = skill 内容变更 → VERSIONING.md L13/L33 PATCH（skill/模板修改 = PATCH 面）**，不构成 MINOR 提升项；若 M-0 选择与 0.79.0 降噪主题同批亦可（届时 L12 累积面中 1 项） |

### 2.2 DEC-171 新增 1 项

| # | ID | 来源（文件+行留痕） | 级别 | 依赖状态 | 工作量 | 建议 | 理由 |
|---|---|---|---|---|---|---|---|
| 17 | **DEC-171 commit-msg Step 3 字面量匹配缺陷**（`grep -q "| $TASK_ID |"` 对加粗 ID 行永不匹配——REL-071 transition commit 被迫 `--no-verify`） | DEC-171（decision-log L180）；infra/hooks/commit-msg L234（Step 3 字面量匹配）；**本报告实证**：`\| REL-071 \|` 0 命中 / `\| REL-072 \|` 0 命中（而行内 `\| **REL-071** \|` / `\| **REL-072** \|` 存在——plan-tracker L258/L259）；REL-070/FIX-278/279/280 行无加粗 → 1 命中（匹配正常） | **P2（检查器缺陷；实测误报）** | unblocked；修复面 = infra/hooks/commit-msg Step 3（L234 的正则容忍加粗：按 DEC-171 建议——去 markdown 加粗后匹配或正则 `\| \*\*[A-Z0-9-]+\*\* \|`）→ 安装面 = .git/hooks/commit-msg（Step 0 自升级机制 + 一次性重装） | 小（单处正则 + 回归确认〔正常行不误报 + 加粗行不再误报〕+ manifest/投影检查〔hook @version 面〕） | **建议入槽 0.78.1（推荐——高优先修复）** | (a) **已实证误报**（REL-071 transition afb959d 被迫 `--no-verify` 例外——DEC-171 入账；流程侵蚀：发布链唯一人工门〔用户授权〕与钩子强校验本应双保险）；(b) **即时影响面**：REL-072（本任务）任务行同为加粗格式——任何涉及 REL-072 的 commit（评估报告入库/后续任务注册）将再次误报 → 继续消耗 --no-verify 例外；(c) 修复 = 单行正则容忍 markdown 格式（匹配面扩大至真实数据现状——**检查器缺陷修复，非规则变更**；任务必须存在的要求〔M7.5 语义〕保留）→ VERSIONING.md L38「仅修复 bug（不改变行为语义）」= PATCH 面；(d) 若推迟到 0.79.0——0.78.1 窗口内所有 commit（含后续发布链）持续暴露误报 + 例外侵蚀；(e) DEC-171 候选 B（改数据迁就检查器）/C（阻塞发布链）已被用户未选（decision-log L180——B 破坏全表惯例、C 不成比例）——修复面 = hook 侧，唯一正确方向 |

---

## 3. 入槽建议汇总

### 3.1 建议 0.78.1 PATCH

| ID | 级别 | 一句话理由 |
|---|---|---|
| DEC-171（commit-msg Step 3 匹配缺陷） | P2 | 检查器缺陷实测误报（REL-071/072 加粗行 0 命中）——发布链被迫 --no-verify，修复面单行正则、PATCH 面；**建议高优先** |
| N-P2-1（_legacy_blocker_keys 重复定义） | P2 | 死代码遮蔽（review_domain.py），纯删除不改行为语义（L38 PATCH 面） |
| N-P2-2（两处惰性 parse_completed_task_ids 注入） | P2 | 测试防护网死注入——未来动 completed 集合无保护（P-v1 原则 4）；纯测试注入点对齐（PATCH 面） |
| N-P3-1（docstring 160→130） | P3 | 纯注释修正（行为限值已正确），成本≈0 |
| FIX-279 P2-1（写入行缺失回归测试） | P2 | FIX-279 契约组件无回归防护（P-v1 原则 4）；补 1 用例（PATCH 面） |
| FIX-279 P2-2（remediation 定位标准行来源） | P2 | UX 消息/文档改进（不改行为语义；PATCH 面） |
| F-01（README 引号非逐字） | P2 | 宣示面引号纪律（与 SKILL L272 非逐字）；极小修；本身不驱动版本号（L45-46），随批次 |
| change-triage SKILL "四步"陈旧 | P3 | 文档陈旧（实际五步）；1 行措辞；skill 修改 = L13/L33 PATCH 面 |
| FIX-272 P2×2（**可选**） | P2×2 | 路径穿越回归锚定（14/14 探针已验证安全）+ 诊断拆分——小工作量；若 M-0 选入 = 需注册+审查链（N=2 上限） |

**范围特征**：全部为 P2/P3 修复、清理、测试卫生、文档措辞、检查器缺陷——**零行为/规则面变更** → 0.78.1 PATCH 论证（VERSIONING.md L13/L38/L123）。

### 3.2 建议 0.79.0 MINOR（候选主题——降噪第二波/规则面）

| ID | 级别 | 一句话理由 |
|---|---|---|
| G3 扩展（写时结构看护扩展至 Coordinator 直写路径） | P2 面 | 写时门禁扩展 = 新增 B 级自动化能力/规则面（L12/L37）——先观察 G3 首波实绩（BC-6） |
| G5（task-priority 重复抑制） | 低收益 | 与 G6 同批"降噪第二波"（-1.7KB/会话）；主题性打包 |
| G6（追查预算提示） | 低收益 | 剩余收尾提示面（G1 已覆盖主体）；与 G5 同批 |
| W-7 / BC-7（终态 marker 集扩展） | 中低 | 判定面规则修改（标记集扩展/尾部终态胜出）——需 DEC + 审查链；与 G2 L-A 后续触碰合并评估 |
| RISK-044 复评（挂载，非入槽项） | — | DEC-169 ② 既定：下轮复评 = 0.79.x 规划——0.79.0 规划 MUST 含复评结论 |

**范围特征**：规则面/判定面变更 + 优化主题打包 → MINOR 论证（L12 累积里程碑 + 新增 B 级自动化能力 + L37 若 SKILL 规则新增）；不跳号（0.78.0 → 0.79.0）。

### 3.3 建议继续搁置（登记后续版本/观察池）

| ID | 级别 | 理由摘要 |
|---|---|---|
| F-03（e2e 投影决策） | P2 | 决策型事项——随下次 e2e 触碰批次或候选打包期落 decision-log；无版本驱动 |
| F-04（npm pack 机器守卫） | P3 | 观察级；FIX-275 验收已覆盖；新开发任务不宜混入修复批 → 0.79.x 守卫批次 |
| F-04-env（锁模型扩展） | P2 | 低概率失效模式 + 安全敏感需设计审查；独立任务（0.78.x+） |
| F-05+BC-1（升 FAIL 部分） | P2/P3 | **DEC-160 条件（连续 2 个零违规 0.77.x）结构性不可满足**（0.78.0 非 0.77.x；无 0.77.1）——条件满足时点 ≥ 未来 0.77.x PATCH 后才可能；词表版本化 + BC-1 字段化可独立前移（PATCH 面，可选） |
| RISK-044 quick-scan | — | 检查点通过（32.8s/29.6s < 60s 修订验收）；复评挂 0.79.x（DEC-169 ②） |
| FIX-279 P2-3 + P3×3 | P2×1+P3×3 | P2-3 误报 vs 漏报权衡需独立 DEC 评估；P3 后续测试候选 |
| N-P3-2（Check 19 谓词不同源） | P3 | 语义对齐候选（若实施 = 判定面评估）——登记观察 |
| N-P3-3/N-P3-4 + DESIGN N-3~N-5 + 前轮 P3-2/P3-4 | P3 | 讨论级/观察级——随下轮触碰归并 |
| (额外) DESIGN-R0 F-3（标记面无机器守卫——check-bootstrap-markers 候选） | P3（审查观察） | **范围外新发现**：review-REL-071-CANDIDATE-DESIGN-R0.md F-3 建议登记 0.78.x 候选——本报告未并入 17 项（非 DEC-169 ⑤ 清单）；如实标注供 Coordinator 决定是否登记（扩展 check-version-consistency 或新增 check-bootstrap-markers，一次性成本低） |

---

## 4. M-3 双审 SUGGESTION 项与队列重叠检查（REL-071 报告核对）

- **review-REL-071-M3-RELEASE-R0.md S-1~S-5**（窗口计数时点口径 / manifest 计数时点 / standard-strict 档位差异披露 / 远端对账证据强度 / 报告文件名消歧）：全部为**发布文档精度/时点口径/对账强度注记**类——非任务候选，与 17 项队列**无重叠**；S-4（远端对账）已由 M-7 `release-ledger --remote github-https` NATIVE_RELEASED PASS 权威执行（M3 报告仅记录 best-effort 局限）。
- **review-REL-071-CANDIDATE-DESIGN-R0.md F-1/F-2/F-4**（窗口计数锚定 / 标记面 9 行枚举口径统一 / manifest 计数微差）：文档精度类，无重叠。**F-3**（标记面无机器守卫）：**建议登记 0.78.x 候选**——为审查发现的新候选观察项，**不在 DEC-169 ⑤ 16 项清单内**，本报告如实标注（§3.3 额外行）供 Coordinator 决定是否登记；与 17 项**无直接重叠**（现有 16 项无"bootstrap 标记面机器守卫"对应项）。
- **结论**：M-3 双审 SUGGESTION 项合计 9 项，其中 8 项为文档精度类（无任务化必要），1 项（DESIGN-R0 F-3）为范围外新候选（如实披露，不私自并入）。

---

## 5. 呈报用户裁决选项组合（Coordinator 转 ask_user_question，DEC-143 基线）

**选项 A（推荐）——0.78.1 PATCH 修复批 + 0.79.0 MINOR 降噪第二波两段式**：
- 0.78.1 PATCH = §3.1 全部（9 项：DEC-171 + N-P2-1 + N-P2-2 + N-P3-1 + FIX-279 P2-1/P2-2 + F-01 + 四步陈旧 +（可选）FIX-272 P2×2）——纯修复/清理/测试卫生/文档措辞（L13/L38/L123 PATCH 论证；不跳号）
- 0.79.0 MINOR = §3.2 主题（G3 扩展 + G5 + G6 + W-7/BC-7 + RISK-044 复评挂载）——规则面/判定面/主题打包（L12/L37 MINOR 论证；不跳号）

**选项 B——全部入 0.79.0 MINOR（单次发布）**：
- §3.1 + §3.2 全部合一——含规则面项（G3 扩展/W-7）→ MINOR 定位成立（L12），但违反 L19-21（Patch 细粒度——修复类不应攒着等 Minor）+ L123 倾向（计划外变更优先 PATCH 路径）

**选项 C——仅 0.78.1 PATCH 修复批（0.79.0 再规划）**：
- §3.1 全部；§3.2 主题项全部维持搁置 → 0.79.0 规划另起（届时含 RISK-044 复评 + G3/G5/G6/W-7 决策）

**注**：任一项入槽（0.78.1）MUST 在 M-1 启动前完成注册（triage 机器入账 + DEC + Developer/Reviewer 链），超期自动出槽登记后续版本（DEC-163 N=2 上限惯例）。

---

## 6. 边界与合规确认

- 本任务零产品代码修改、零版本文件修改、零 tag、零 `.governance/` 写入（唯一写入 = 本报告 `docs/release/queue-triage-0.78x.md`）。
- 不关闭 RISK-036/039（1.0.0 阻塞保持，2026-09-30）；RISK-044 保持已接受（复评 = 0.79.x）。
- 全部来源为只读核验 + 已入账治理记录引用；DEC-171 缺陷影响面为**本报告实测**（pwsh 只读 grep 模拟 Step 3），如实标注。
- 入槽/搁置均为**建议**——最终裁决 = 用户（Coordinator 转 DEC-143 交互基线）。
