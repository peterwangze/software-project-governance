# REVIEW-FEAT-034-DESIGN-R0 — 首次交互前置协议重排 · 独立设计审查（round 0）

- **审查对象**：FEAT-034 工作树未提交改动（4 手改文件 + 3 工具生成面 + 1 遗留测试断言修复）
- **审查类型**：Design Review（协议/规则变更——design-review SKILL + agents/design-reviewer.md）
- **Round**：R0（首审）
- **审查人**：Design Reviewer Agent（只读；本报告为唯一产出物，未修改任何被审文件）
- **日期**：2026-09-18
- **审查证据基座**：工作树活体文件 + `git diff`（7 文件 +56/-18）+ HEAD 对照（a5d678f）+ TRIAGE-FEAT-034.json + EVD-1073/1075 + plan-tracker L78-99 + AUDIT-154 诊断报告（docs/requirements/governance-bootstrap-cost-audit-0.84.0.md L143/180/188）

## 结论：APPROVED_WITH_NOTES（P0=0/P1=0/P2=3/P3=6）

**unresolved_blockers=0**

协议重排的设计语义完整、安全约束零削减、四处文本同构可执行；测量申报符合 D1 事实原则。3 条 P2 为非阻塞跟踪项，其中 P2-2/P2-3 为**闭环前置处置项**（披露补记 + 验收尾巴结构化），P2-1 建议随下一轮协议微调或闭环披露处置。复审锚见文末，供 R1（如触发）逐条比对。

---

## 1. 变更面核实（事实基座）

| 文件 | 申报 | git diff 实测 | 核实 |
|------|------|--------------|------|
| commands/governance.md | +16/-2 | +16/-2（5 hunk：决策树 L136-155 / Scenario C L292 / D L326 / E L386 / 引导时序 L542） | ✓ |
| skills/software-project-governance/SKILL.md | +5/-2 | +5/-2（3 hunk：L36 你负责 bullet / L60 健康摘要时序 / L69 快路径第二动作） | ✓ |
| commands/governance-init.md | +20/-6 | +20/-6（5 hunk：lightweight L199 / standard L330+L412 / strict L605+L688） | ✓ |
| references/behavior-protocol.md | +15/-2 | +15/-2（4 hunk：M4.1 时序 L210 / 步骤5标注 L220 / M5.5 新增 L398-408 / M7.1 指针 L450） | ✓ |
| project/e2e-test-project/CLAUDE.md | 工具生成镜像 | +9/-3 | ✓ |
| project/e2e-test-project/.../SKILL.md | 工具生成镜像 | +4/-1（FEAT-034 三处语义同步入 fixture——顺手修复既有 projection drift） | ✓ |
| .../tests/test_verify_workflow.py | 遗留披露 | +5/-2（EntryBootstrapTemplateTests 断言 3→4） | ✓（归属裁决见 §5.2） |
| CLAUDE.md（repo root） | 本地全模板重投影 | 不在 git diff——**未被 git 跟踪**（`git ls-files` 仅返回 AGENTS.md）；活体态含 FEAT-034 段（Step 1 快路径+首次交互前置 / Step 2 后置深检），@bootstrap-version 0.83.0 | ✓（符合 SKILL.md L334"入口文件是临时文件非产品资产"定位） |
| AGENTS.md | 零 diff（幂等 SKIP） | 零 diff（git 跟踪，无改动）——薄指针模板本次未改，幂等成立 | ✓ |

**删除面核实**：5 条被删行（governance.md 决策树首行/Scenario D FEAT-033 段/SKILL.md 引导句/behavior-protocol 步骤5标题/M7.1 尾句）全部被语义等价+扩展的新行替代——**无静默语义丢失**。

---

## 2. 六个核心问题逐一评估

### Q1 协议语义完整性——Scenario C/E 深检后置是否造成"盲目选择"

**裁决：设计自洽，Scenario E 两段式消解了盲目选择；Scenario C 存在一处衔接歧义（P2-1）。**

- **Scenario E（L389）**：首次 ask 的选项是"立即全量诊断 / 暂缓并记录为已知异常"——这是关于**是否执行诊断的元决策**，不需要诊断结果即可做出；修复方案选项（E2 一键修复/仅修 P0/看详情/暂不处理）出现在诊断**之后**，届时健康信息已就绪。异常标记本身来自 resolve_entry 判定（fail-closed 已在第一动作保证）。**不存在盲目选择。**
- **Scenario C（L295）**：版本差距 + CHANGELOG delta 随快路径首次 ask 一并呈现，升级写序列后置到用户确认后——写操作前有显式确认门。风险窗口：用户确认升级时健康面 deferred，升级序列在未做健康检查的状态上执行。缓解因素：升级序列自带 hook 存活检测（步骤 3.C）与 plan-tracker 结构补全（3.B）；且升级属 M5.5 条 3"治理写回/版本 bump"类推进动作。
  - **P2-1（歧义）**：Scenario C 注记把升级序列称为"深检写操作"，而 M5.5 条 3 要求推进类动作前 MUST 先补跑"对应深检（健康摘要 + 交叉验证）"——两种执行解读并存：(a) 升级序列=深检，确认后直接执行；(b) 确认后还需先补 `check-governance --summary-only` 再执行升级序列。不同 agent 可能执行不一致。**建议**：Scenario C 注记补一句显式衔接（如"确认升级后、执行升级写序列前，MUST 补跑健康摘要"）。不阻塞——git hooks/write-guard 对治理写回有 B 级兜底。
- **Scenario D（L329）/F（L545）**：后置条款 + "继续上次实际修改前 MUST 补齐 D2" + 引导时序注记齐备，无缺口。

### Q2 回归安全——推进类动作前的 MUST 补深检是否覆盖全部危险路径

**裁决：覆盖充分，无时序漏洞；一处边界定义含糊（P3-1）。**

原协议 Step 2 三项强制检查（证据完整性/Gate 一致性/风险过期）的可达性路径：
1. **触发清单**：发布 / 版本 bump / 治理写回 / 恢复遗留任务的实际修改——四处文本（governance.md L143、SKILL.md L63、governance-init L346/621、behavior-protocol M5.5 条 3）清单一致。
2. **独立义务未后置**：M5.5 条 3 显式声明"不削减 M6 Gate 义务、M8 验证义务"——Gate 推进的证据要求与发布验证独立于交叉验证存在；Step 3 阶段跳跃防护（MANDATORY）未后置。
3. **场景级兜底**：Scenario D"继续上次+实际修改前补 D2 交叉验证"（L329）；Scenario C 确认后执行写序列。
4. **机器兜底**：check-governance 的证据/Gate 校验在任务闭环时点强制（B 级），不依赖会话前检。

深检后置开辟的最大窗口 = "首次 ask 后、用户首次推进动作前"——该窗口内所有**读**路径（状态展示、Scenario 引导）均为只读，无危险路径。判定：**原三项检查在后置触发条件下全部可达，安全约束零削减**。

- **P3-1（边界含糊）**："治理写回"未定义边界——宽解（任何 `.governance/` 写入）会使新任务入账也触发深检，使"恢复遗留任务的实际修改"条款冗余；窄解（仅 Gate/版本/风险/归档等治理结论类写入）则需明确枚举。另 Scenario E"暂缓并记录为已知异常"（risk-log 写入）按宽解会自触发深检要求，轻微循环。建议 M5.5 条 3 或词汇表给出边界定义。低危（记录已知异常不依赖深检结果）。

### Q3 M5.5 与既有 M5 系 / M6 / M7.4 / M4 的一致性

**裁决：无矛盾。**

- M5.1（AskUserQuestion 唯一合法方式）：M5.5 条 1 的首次交互经 AskUserQuestion ✓——是提前 ask，不是跳过 ask。
- M5.2/M5.3（关键决策必停）：M5.5 不触碰关键决策清单 ✓。
- M5.4/M5.4b（跳过例外/纯通知结构定义）：M5.5 未新增跳过理由 ✓。
- M6 Gate 行为：条 3 显式不削减 ✓；Gate 通过类型/裁剪规则未动 ✓。
- M7.4（完成必推荐/复审必达）：与 M5.5 的 bootstrap 时序分属不同生命周期时点，无交叉冲突 ✓。
- M4.1：时序段（L213）+ 步骤 5 标注"FEAT-034 起为后置深检"（L223）与 M5.5 同构 ✓。
- M7.1：L453 指针句准确指向 M5.5 ✓。
- M5.5 编号插位于 M5.4b 与 M6 之间（L401），顺延无冲突 ✓。
- 条 4 与 FEAT-032 的 governance-cost-report 契约（TTFA+time_to_work 成对、DEC-205 lower-bound、RISK-052 同快照口径）对齐 ✓。

一处待观察（并入 P3-2）：M4.1 步骤 2 的 pending decisions 对比与 D3 恢复面板"待确认决策"节的数据面，最小状态行契约（模式+阶段/Gate+carry-over/风险计数）未含该计数。

### Q4 fallback 路径设计

**裁决：bootstrap 面触发条件明确、回退后 ask 前置语义保持；命令面一处未对齐（P3-3）。**

- **触发条件三分类明确**：命令缺失/超时/解析失败（governance-init L333/L608 两模板同款）；`--budget-ms` 内建 fail-safe 返回 `deferred` 明示未完成范围（governance.md L468）；缺面时"用 read 工具按需展开对应段落"（L340/L615）。
- **回退后语义**：fallback 六段读取的终点同样是"热数据就绪"→ L346/L621 的"热数据就绪后 MUST 立即呈现最小状态行 + AskUserQuestion"对快路径与 fallback 两条路同样生效——**ask 前置语义在 fallback 中保持** ✓。
- **lightweight 模板**（L202）：简化版 fallback（"不可用时回退直接读取 plan-tracker"）与完整版同构（简化不失义）✓。
- **P3-3**：governance.md 决策树第二动作（L141）MUST 运行 governance-bootstrap 但**无 fallback 句**——/governance 手动入口在命令执行失败时行为未定义（bootstrap 面已定义，命令面未对齐）。建议同构补一句。

### Q5 多平台投影一致性

**裁决：语义可达性成立（SKILL.md 双保险）；薄指针静默与 DSH persona 过渡期双口径各记一条观察（P3-4/P3-5）。**

- **薄指针承载**：secondary-thin 注入条件 = 双入口并存（governance-init L832/L869）——主入口 CLAUDE.md 必在同工作区，"行为约束以主入口为准"指针可达。FEAT-034 时序语义对次要平台的可达性经**两条通道**保证：(a) 同工作区主入口 CLAUDE.md（已重投影含 FEAT-034）；(b) SKILL.md（所有平台每会话必加载，L39/L61-72 已携带新时序）。**FEAT-034 语义对次要平台可达。**
- **P3-5**：AGENTS.md 薄指针自身"最小存活检查"第 2 步仍是"读 plan-tracker"（无快路径）——次要平台在 SKILL.md 加载前走旧慢路径；行为安全（旧路径=深检前置，安全侧倾），仅体验差异。FEAT-037 去重哲学（L873 行为约束清单未含时序语义）下不更新薄指针属可辩护设计；后续可加一行快路径指针。
- **DSH persona 延后（P3-4）**：persona（agent.cordis.yml.template）携带的 bootstrap 压缩投影未随本次更新——过渡期 persona 旧时序句与 SKILL.md 新时序句双口径并存。安全评估：persona 旧时序=健康摘要前置=更慢非更弱，无安全削减；且 persona 是压缩投影、SKILL.md 是完整权威注入（governance.md 分工表）。**延后到 FEAT-040（多平台回归+灰度+GOV_FAST_PATH 回退开关）合理**——避免 persona 在回退机制就位前改两次；建议补一条过渡期口径声明（0.84.0 CHANGELOG 或临时 risk："过渡期 bootstrap 时序以 SKILL.md 为准"）。
- **canonical 流向**：见 §5.1，合规。

### Q6 测量诚实性——本轮闭环 vs 留验收尾巴

**裁决：Developer 申报诚实；应本轮闭环协议落盘部分 + 结构化验收尾巴（P2-3）。**

- **零漂移复现的正确解读**：p50=271.8s = FEAT-032 基线快照值（EVD-1073：TTFA p50=271.8s 逐值复现审计 §3.1）。协议落盘后重跑成本报告数值不变，恰恰证明**机制就位而效果未兑现**（尚无会话按新协议执行）——Developer 未拿机制就位冒充效果达成，符合 D1。
- **"效果验证需后续会话采样"+"预期机制推演标注为推演非实测"**：协议改造的验收信号天然滞后一轮会话（验收标准本身要求"轨迹复验"——L82/审计报告 L180）。
- **闭环结构判定**：任务**应当在本轮闭环协议落盘部分**（否则轨迹采样永远无法开始——等待本身阻塞验收），但闭环 MUST 满足：
  1. 效果复验尾巴**结构化**（三选一：plan-tracker 拆子任务行 / 并入 FEAT-040 验收面（其已依赖 FEAT-034）/ RISK 登记复验窗口）——不能只留在申报文本；
  2. 补 FEAT-034 交付证据行（EVD）——evidence-log 当前仅 TRIAGE-FEAT-034，无交付行（审查时点正常，闭环时 MUST 补）；
  3. plan-tracker L82 状态随闭环同步。
- 审计报告 L188 的切片 A 整体验收（交互前工具调用 ≤3、串行模型决策节点 ≤4）同属轨迹复验面——与 FEAT-034 复验尾巴合并采样即可，无需独立任务。

---

## 3. Developer 申报 8 项逐项核实

| # | 申报 | 核实结果 |
|---|------|---------|
| 1 | 协议一致性四处同构 | ✓ 四处（governance.md L141/143、SKILL.md L39/63/72、governance-init L202/333-346/415-416/608-621/691-692、behavior-protocol M4.1/M5.5/M7.1）关键词四件套齐备：快路径立即 ask / 深检后置 / 推进类动作 MUST 补 / deferred「待检查」 |
| 2 | 安全约束保持 | ✓ resolve_entry fail-closed 第一动作文本未动（L139"不变"显式声明）；深检后置≠可选四处均含推进类清单；M5.5 条 3 显式不削减 M6/M8 |
| 3 | 诚实语义 deferred≠PASS | ✓ 四处一致（governance.md L143/L468/L545、SKILL.md L63/72、governance-init L202/346/621、M5.5 条 2"MUST NOT 显示绿色通过"） |
| 4 | 口径注入 DEC-205/RISK-052 | ✓ M5.5 条 4 含 lower-bound 声明 + 跨时点不可直接 diff + 同快照对比口径；SKILL.md L39 成对跟踪义务 |
| 5 | 投影同步双 apply 幂等 | ◑ 申报值未独立复跑（审查角色工具约束）；**活体态佐证一致**：CLAUDE.md 含 FEAT-034 段且不被 git 跟踪（=本地 [WROTE] 后与模板一致）；AGENTS.md 零 diff（=[SKIP]）；fixture SKILL.md +4/-1 与主 SKILL.md 三处语义一一对应。复跑留 Code Reviewer/Coordinator 面 |
| 6 | 六项校验 PASS + 105 测试 | ◑ 申报值，无机写证据行，未独立复跑（Code Reviewer 职责面）——闭环 MUST 随 EVD 补机器输出 |
| 7 | 测量如实性 | ✓ p50=271.8s 与 EVD-1073 基线吻合（零漂移=效果未兑现的诚实信号）；"效果验证需后续会话采样"+推演标注齐备 |
| 8 | 遗留披露 | ✓ test 3→4 与 fixture drift 修复均核实（裁决见 §5.2/§5.3） |

---

## 4. 发现清单

### P0（BLOCKING）——无

### P1（阻塞）——无

### P2（非阻塞跟踪；P2-2/P2-3 为闭环前置处置项）

- **P2-1 Scenario C 升级确认与 M5.5 条 3 衔接歧义**：升级序列被注记称为"深检写操作"，与条 3"推进类动作前 MUST 补跑对应深检"存在两种执行解读。证据：governance.md L295 vs behavior-protocol L407。建议：Scenario C 注记补显式衔接句。处置时点：随闭环披露或下一轮协议微调。
- **P2-2 变更控制申报面与实际改动面偏差（闭环前置）**：TRIAGE-FEAT-034.json `files` 仅 3 文件（governance.md / SKILL.md / governance-init.md），实际手改 4 文件——**behavior-protocol.md（新增 M5.5 行为协议条目）未入 triage 申报面**，导致冲突检测未覆盖其交叉面（FIX-262/297/302 的 behavior-protocol.md 关联均未被判 overlap）。闭环披露 MUST 补记该偏差及其原因（执行中范围扩展未回写 triage 面）。
- **P2-3 验收尾巴结构化（闭环前置）**：见 Q6——闭环时 MUST 三选一结构化效果复验尾巴 + 补 EVD 交付行 + plan-tracker 状态同步。申报文本中的"需后续会话采样"不构成结构化载体。

### P3（观察登记）

- **P3-1**："治理写回"边界未定义（宽/窄两解执行差异大；Scenario E 记录已知异常按宽解自触发深检，轻微循环）。建议词汇表/条 3 边界定义。
- **P3-2**：最小状态行契约不含"待确认决策"计数，而 Scenario D3 面板模板含该节；聚合快路径若无此面，D3 立即执行时数据源缺兜底句（governance-init L340 有"缺面按需展开"，governance.md Scenario D 注记 L329 未写同款）。建议对齐。
- **P3-3**：governance.md 决策树第二动作（L141）无 fallback 句——/governance 手动入口在 governance-bootstrap 执行失败时行为未定义（bootstrap 面模板 L333 已定义三条件 fallback）。建议同构。
- **P3-4**：DSH persona 过渡期双口径（旧时序 persona + 新时序 SKILL.md 并存）——安全侧倾、归属 FEAT-040 披露合理；建议补过渡期口径声明（CHANGELOG 或临时 risk）。
- **P3-5**：AGENTS.md 薄指针最小存活检查不含快路径语义——次要平台 SKILL.md 加载前走旧慢路径；安全侧倾、语义经 SKILL.md 双保险可达；后续可加一行快路径指针。
- **P3-6**：`sync_entry_projection --source-root` DX 陷阱——默认 fallback 到 `--project` 目录（sync_entry_projection.py L480），fixture 项目场景必须显式传插件仓库根（fail-closed 不静默，行为正确但易踩）。值得登记为改进候选（错误信息提示补参或从 manifest 推断）；**建议随闭环披露一并登记**，不单独开任务。

---

## 5. 特别审查点裁决

### 5.1 canonical 模板改动流向（FIX-011 纪律）——**合规**

- 手改仅落在 canonical source（governance-init.md Step 7 注入模板 + 引用协议文件）；活体入口 CLAUDE.md/AGENTS.md 未手改——CLAUDE.md 不被 git 跟踪（`git ls-files` 实证），其 FEAT-034 语义与 canonical 模板逐句一致（本地工具重投影产物）；AGENTS.md 零 diff 与"薄指针模板未改"自洽（双 apply 幂等的 SKIP 面）。生成链方向正确：模板 → sync_entry_projection → 活体投影。
- fixture SKILL.md +4/-1 为 sync 镜像（确定性工具顺手修复既有 projection drift）——符合"工具生成非手改"纪律。

### 5.2 test_verify_workflow.py 断言 3→4 的归属——**随 FEAT-034 commit 披露纳入：合理，附条件**

事实链：HEAD 的 governance-init.md 中 `> @bootstrap-version: 0.83.0` 精确计数已为 **4**（含薄指针模板标记行），HEAD 测试断言 3 → 该测试在 HEAD/0.83.0 状态**必然 FAIL**（数学事实，未复跑即成立）——属 FEAT-037 引入薄指针标记行时的**存量测试欠账**。工作树修复使其与模板事实一致。
裁决：(a) 该 1 行修复是 FEAT-034 分支测试转绿的必要项，随 FEAT-034 commit 纳入是务实折中；(b) **条件**：commit message MUST 显式披露"含 FEAT-037 遗留测试断言修复（3→4，修复 EntryBootstrapTemplateTests 存量失败）"以保 D4 可追溯——Developer 申报已建议此做法，确认执行即可。

### 5.3 fixture SKILL.md 顺手修复——**合规**

镜像 diff 与主 SKILL.md 的 FEAT-034 三处语义一一对应（你负责 bullet / 健康摘要时序段 / 快路径 bullet），由确定性同步工具产生，非选择性手改；drift 修复降低了双面守护（check-projection-sync）的假警报面。

---

## 6. AI 专项——协议文本可执行性

- 四处文本的指令均明确可遵循：第一/第二动作有精确命令行；最小状态行有三要素清单；deferred 显示词有精确字面（「待检查」）；推进类动作有四项枚举；fallback 有三条件枚举 + 逐段回退序列。
- 保留的歧义已在 P2-1（Scenario C 衔接）/P3-1（治理写回边界）逐条标注——均为局部歧义，不影响主干时序的可执行性。
- M5.5 四条均为 MUST 且互不重叠（时序/诚实/后置不豁免/测量口径），无相互冲突的指令对。

## 7. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 | =0 | 0 | PASS |
| 维度覆盖 | 5 维 | 设计一致性 §2.Q1/Q3 ✓ / 安全性 §2.Q2 ✓ / 可维护性 §5（编号顺延、canonical 单源、fallback 同构）✓ / 回归风险 §2.Q2+Q5 ✓ / 验收充分性 §2.Q6 ✓ | PASS |
| 发现分级 | 每条 P0~P3 | P2×3 + P3×6 全部带文件/行号证据 | PASS |
| AI 专项（可执行性） | 无主干歧义 | §6 | PASS |
| 事实依据红线 | 全引用可复查事实 | 本报告所有结论锚定文件行号/diff/CLI JSON/既有 EVD；未复跑项显式标 ◑（非 PASS 依据） | PASS |

## 8. 复审锚（供 R1 使用——如 Coordinator 触发返工复审）

R1 MUST 逐条比对以下锚点并标注"已修复/未修复/新引入"：
1. P2-1 → governance.md Scenario C 注记是否含与 M5.5 条 3 的显式衔接句
2. P2-2 → 闭环披露是否含 triage files 面偏差补记（behavior-protocol.md）
3. P2-3 → 效果复验尾巴是否结构化（plan-tracker 行/RISK/FEAT-040 验收三选一）+ EVD 交付行是否补
4. P3-1~P3-6 → 逐条登记或处置说明

## 9. 审查局限声明

- 本审查为设计审查：未复跑六项校验与 105 测试（Code Reviewer 职责面）；申报值标 ◑。
- 测试断言归属判断基于 HEAD/工作树文本数学对比（断言 3 vs 计数 4），未实际在 HEAD checkout 上执行测试。
- governance-bootstrap 聚合输出的字段全集（含/不含 pending decisions 面）未从 CLI 输出直接核实，P3-2 按协议文本面判定——如聚合实际含该面，P3-2 自动消解。
