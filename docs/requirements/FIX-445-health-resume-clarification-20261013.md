# FIX-445 健康恢复的需求与验收约束澄清报告（2026-10-13）

- **Task ID**: FIX-445 — 恢复健康检查的需求与验收约束诊断
- **角色**: Analyst Agent（`agents/analyst.md`；绑定 skill：requirement-clarification）
- **日期**: 2026-10-13（Coordinator 供应会话日期）
- **需求源**: 活性缺陷（用户本会话 `/governance → 继续上次，恢复"检查健康"`）
- **产物边界**: 本文件是本次诊断唯一新建/写入文件；未修改任何治理记录、状态、验收门、产品源或历史报告。
- **决策边界**: 本报告只出方案与归因，不做最终决策；所有需用户裁决项以选项形式返回 Coordinator。

---

## 0. 实际读取输入清单（本报告全部证据来源）

本会话 Analyst 实际 read 以下 13 个文件（零执行、零 shell、除本文件外零写入；#12 为 Coordinator 补充事实送达后增读，对应增补内容见 §6.1/§9/§10；#13 为第二轮校准的一手复核行段，见 §6.1-2 校准记录）：

| # | 文件 | 规模 |
|---|---|---|
| 1 | `agents/analyst.md` | 92 行（角色定义） |
| 2 | `skills/requirement-clarification/SKILL.md` | 115 行（任务规范） |
| 3 | `.governance/reports/FIX-445-R10-contract-decision.md` | 81 行（全文） |
| 4 | `.governance/session-snapshot.md` | 88 行 |
| 5 | `docs/design/FIX-445-mention-contract-R10.md` | 135 行 |
| 6 | `docs/reviews/review-FIX-445-CODE-R6.md` | 100 行 |
| 7 | `docs/reviews/review-FIX-445-DESIGN-R10.md` | 132 行 |
| 8 | `docs/reviews/supplement-FIX-445-DESIGN-R10-evidence.md` | 105 行 |
| 9 | `docs/reviews/supplement-FIX-445-DESIGN-R10-calibration.md` | 44 行 |
| 10 | `.governance/incidents/FIX-445-health-resume-full-20261013.txt` | 28 行（strict 健康 raw） |
| 11 | `.governance/incidents/FIX-445-health-resume-full-20261013.json` | 29 行（机录回执） |
| 12 | `.governance/incidents/FIX-445-health-resume-diagnostics-20261013.json` | 1079 行（Coordinator 定向诊断工件，schema governance-targeted-diagnostics/1，03:18:34→03:18:43Z） |
| 13 | `skills/software-project-governance/infra/verify_workflow.py` | 行段 10405–10464（第二轮校准一手复核：GovernanceDataSource 聚合 hot+archive 的实现与注释；仅该行段） |

Coordinator 单源事实（派发 prompt 供应，Analyst 未直读热面——modern 热数据唯一路径 governance-bootstrap）：工作流 0.97.0 / always-on × maximum-autonomy / modern / standard；维护第 11 阶段，11 Gate passed；34 tasks / 27 completed / 3 unblocked / 4 non-exec / 0 in-progress / 20 open risk / 0 到期升级；health 首次 17、严格 16 issues，以提供 raw 为准，绝不计为 PASS。

---

## 1. 第一步：问题澄清（5 问法）

### Q1 当前痛点是什么？（现状，不含解决方案）

用户恢复"检查健康"后，strict 全量健康检查失败：**16 issues / child_exit_code=1**（首次 full-health 为 17 issues），其中 FIX-445 的执行包记录字段（18c required_evidence、18d success_metrics、18f quality_budget/vertical_slice）与产品验收字段（18d-RB2 last_run）同时不合格；产品侧 **64 tests/92.738s/1 FAIL、Code R6 BLOCKED/3、W1 与完整四源验收门全部未解**。FIX-445 blocked（op-71225664af134e89b9f599ca48da878a），原接口保持与 EVD-1587 正文 clean 的冲突已获 R10 静态分析三重机录支持，无就绪替代契约。

（锚点：`incidents/…20261013.txt:1`「Governance: 16 issues」、`:2–14` FAIL 行；`incidents/…20261013.json:21` child_exit_code=1、`:19–20` 03:11:44.7457265Z→03:13:48.1669702Z；`reports/FIX-445-R10-contract-decision.md:12`；`session-snapshot.md:10,22`。）

### Q2 为什么这是个问题？（影响）

1. 健康门 FAIL（exit 1）使总健康目标不可判定完成（`session-snapshot.md:85`：goal rev5/paused/disarmed，未标 complete）。
2. **记录字段缺口与产品真失败混在同一报告**中，无法区分"补记录即可"与"需架构裁决"——本次诊断的直接动因。
3. 每次全量 strict 检查耗时约 123.4s（json `:19–20` 实际区间）且产生审计噪音；两时点账目（首次 17 vs strict 16）差异未解释，与 R4:22tests/69.724s/3F vs R10:64tests/92.738s/1F 并存（`supplement-…-evidence.md:91` CH-C 已警示混读风险）。

### Q3 不解决会怎样？（代价）

- 健康检查持续 FAIL；18d-RB2 与 18f 的 status 类要求把 **strict 清零锁死在 FIX-445/FIX-444 产品真实通过之后**，非产品项（28s 数据尺寸、31 账目格式、记录文本缺口）也无法清零。
- 已通过的 FEAT-097/FIX-443 保全状态被整体 FAIL 掩盖（`session-snapshot.md:19–20` 两任务 approved 但最终健康未完成）。
- evidence-log 继续增长（当前 1,155,447 bytes，`…txt:12`），28s FAIL 随时间恶化。

### Q4 解决后的理想状态是什么？（目标，不含技术方案）

用户运行健康检查可获得真实反映状态的结果；每个失败项可归因到明确处置类别（记录补正 / 治理动作 / 产品修复 / 用户裁决）；合法技术证据行为不再被误报为编造；已通过项与未通过项清晰分列，不互相掩盖。

### Q5 怎么算成功？（可量化成功标准）

**诊断成功（本报告自身）**：每条结论有可定位来源；成功指标分"目标"与"已达标事实"；原 64tests/1FAIL、CodeR6 BLOCKED/3、W1 与完整四源门保持失败/未解；明确哪些记录可补正、哪些 PASS 字段不得填写。

**工作单元成功（候选指标，见 §7）**：至少 1 个可量化——strict 全量健康 issues=0 且 exit 0（当前 16/1）；live 四任务门 hits=[]（当前 FIX-445 FAB_HIT）；模块 64 tests 0 failure（当前 1）。

---

## 2. 第二步：范围澄清（IN/OUT）

### IN（本诊断交付）

1. requirement-clarification 四步核对：目标 / IN-OUT / 约束 / NFR（本 §1–§4）。
2. 原接口保持下"是否存在获证可执行产品修复"的存在性判断（§5）。
3. 健康检查 16 issues 逐项分类：记录可补正 / PASS 不得填 / 需用户裁决 / 需先定位（§6）。
4. 成功指标候选，区分目标与已达标事实，附原证据锚点（§7）。
5. DEC342/DEC343 语义边界说明：继续上次 ≠ 接受变更（§8）。
6. 可供用户决策的具体范围（选项 + 需求源标注，§9）。
7. 剩余证据缺口清单（§10）。

### OUT（看起来应该做但决定不做，附理由）

| # | OUT 事项 | 理由 |
|---|---|---|
| 1 | 修改 `execution-packets.json` 或任何 `.governance/` 记录 | Analyst 只读诊断；治理写回是 Coordinator 职责且需授权（任务禁令 + 角色边界 `agents/analyst.md:34`） |
| 2 | 重跑健康检查 / 测试 / 历史 probe | raw 已提供且"以提供 raw 为准"；json `:3–4` reason 明示本次展开即异常结果触发，非例行复验 |
| 3 | 提出新词形 / 闭表 / ID / hash / sidecar 豁免方案 | R7/R8/R9 已否决该机制类别（R9 补核解除条件"不再只加一个标记"；`reports/FIX-445-R10-contract-decision.md:28`）；任务禁令明示不重复 |
| 4 | 作 R11 设计或任何新接口/架构方案 | DEC343 未授权；架构决策属用户关键决策（`reports/FIX-445-R10-contract-decision.md:79`） |
| 5 | 展开 FIX-444 同类字段的同等诊断 | 本任务对象为 FIX-445；范围纯粹性（P-v1 D4）；FIX-444 同性质 FAIL 已在 §6 标注存在、不展开 |
| 6 | 产出竞品分析 / PR-FAQ / OKR / 用户画像 | 任务上下文明示"非竞品/立项全产物任务，不编造人物、市场或结果"——Analyst 硬门槛中该类门槛不适用于本任务 |

IN/OUT 无重叠自查：§2 IN 各条均为分析/归因/清单产出，OUT 各条均为写操作/重复执行/越权设计/范围蔓延，无同项双侧出现。✔

---

## 3. 第三步：干系人与约束

### 干系人

| 干系人 | 角色 | 职责 |
|---|---|---|
| 用户 | 仓库所有者 / 唯一决策权威 | DEC342（保持原门并暂停）、DEC343（恢复健康工作单元）的实际裁决者；未来范围/架构/验收变更的裁决者 |
| Coordinator | 治理调度 | 派发、锁获取/释放、机录、治理写回、向用户呈现选项与推荐 |
| Analyst（本角色） | 需求诊断 | 本报告；不做技术决策、不写产品代码、不与用户直接交互 |
| Architect / Design Reviewer / Code Reviewer / Developer | 历史链角色（静止） | R0–R10 设计与审查产物已完成并冻结；无 running job（`session-snapshot.md:84`） |

### 硬约束（全部有锚点）

| # | 约束 | 锚点 |
|---|---|---|
| C1 | 唯一写入文件 = 本报告；其余只读 | 任务派发 prompt 修改文件条款 |
| C2 | 原 Guard G / 来源授权 / 完整四源验收（非零/hashbytes/latest/zero skipped/RC0）/ 12 攻击反例拒绝 / B3 保护 / 性能资源门（CPU27.8/CLI36/434339/32MiB/1500）/ 两产品范围保持 | `session-snapshot.md:10,64,86`；`reports/…R10-contract-decision.md:74` |
| C3 | 已否决机制不得复入：局部词形、ID/hash 白名单、sidecar/报告自授豁免、减源 skip、免安全规则 | `reports/…R10-contract-decision.md:28,74`；任务硬门槛 |
| C4 | 健康结果以 raw 为准（strict 16 / 首次 17），绝不计为 PASS | Coordinator 单源事实；`…txt:1`、json `:21` |
| C5 | 无 DRI / human external membership 事实 → 按未知处理，不发明人类评审 | `review-…-DESIGN-R10.md:28`；`supplement-…-calibration.md`（N3，evidence:101） |
| C6 | 破坏性红线：不适用（本任务无用户真实环境操作） | 任务派发 prompt |
| C7 | infra 命令绝对路径、不解析 $WORKFLOW_HOME； Analyst 不执行 shell | 会话 persona；`agents/analyst.md:81` |

### 假设（未验证，显式标注 + 验证计划）

| # | 假设 | 验证计划 |
|---|---|---|
| H1 | Coordinator 供应的单源热数据（0.97.0/11 阶段/34tasks/20risks 等）准确 | Coordinator 可用 governance-bootstrap 复核；Analyst 禁直读热面，不自行验证 |
| H2 | ~~首次 17 与 strict 16 的差异 1 项为 strict 收敛~~ **已撤回（当场校准，2026-10-13）**：该方向性表述无事实基础，不应作此方向假设；现仅陈述两时点计数不同（17 vs 16），**差异原因未知**，无任何「收敛/已修」结论 | 取得首次 full-health raw 后对照差异项（G1）；在取得差异项事实前不作任何方向假设 |
| H3 | `…txt` 为 strict 检查完整 raw，除 `:2`（"source files containing"截断）与 `:13`（"2 closure violation(s)"未列明细）外无信息丢失 | 向 Coordinator 索取未截断 stdout 或检查器明细参数（缺口 G3/G4） |

---

## 4. 第四步：非功能需求初筛（初识别，不定量）

| 维度 | 已识别事实 | 何时深入 |
|---|---|---|
| 性能 | strict 全量 ~123.4s（json `:19–20`）；evidence-log 1,155,447B 超限（`…txt:12`）；W1 语料 glob 54 命中/26 JSON 的 IO 面（`supplement-…-calibration.md:27–28`） | 产品重开设计（B 路径）时按 R10 分析 §6 CH4 复测既有门 |
| 安全 | Guard G / typed 凭据 / 攻击逐例拒绝为硬门；**安全维不可豁免**（禁免安全规则，任务硬门槛；C3） | 任何未来接口设计阶段强制 |
| 可用性 | 合法 prose（EVD-1587）被保守拒绝 = 工作流不可用面（`review-…-DESIGN-R10.md:122` CH2 残余风险 High） | 替代提及契约设计时 |
| 可维护性 | 单一可审契约优于词法补丁（`docs/design/…R10.md:120`）；closure_chain/governance_store 等模块规模 WARN（`…txt:16–23`） | R11 设计若获授权 |
| 兼容性 | 原 64 tests / 完整四源 / 两产品文件边界；历史 EVD 零编辑（`session-snapshot.md:64`） | 同上 |

---

## 5. 核心判断：原接口保持下，目前**不存在**获证可执行的产品修复

**结论**：在"当前接口完全保持"（现 M5 / hook:770 框架规则、现 typed 来源验证、现 Guard G）前提下，没有任何一条已获证（经独立审查支持、可实施、可过验收）的产品修复路径。判断链如下，每步有锚点：

1. **冲突已静态证成**：EVD-1587 正文 `已知no-separator当真不能默当获准安全残余` 中 `当真` 无条件成框架命中（hook :770），最近逗号前缀窗 `已知no-separator` 为 **14 字符**，首字 `已` 不在 24-否定表也不在 19-填充表 → 残留 → bad=1 → Step 12 BLOCK。原接口保持与完整四任务源 clean 在该输入上**不能同时满足**。
   （锚点：`docs/design/…R10.md:71–82`；`supplement-…-evidence.md:46` 逐字符复推；`supplement-…-calibration.md:13` 校准 14 字符并确认"残留拒绝而非长度溢出拒绝，BLOCK 结论不变"；`review-…-DESIGN-R10.md:49–57` 独立支持。）
2. **跨记录授权不可用**：credential 只作用于 strict-obj 有效区内 typed field（hook :615–617），普通 prose occurrence 永留 residual；现 typed 来源验证只作用于严格 JSON 获证字段/片段，不能跨记录给普通正文授权；现引用 Guard G 还拒绝含该框架词的 T2 候选（GUARD_TOKENS 含 `当真`，hook :339）。
   （锚点：`supplement-…-evidence.md:46,48`；`reports/…R10-contract-decision.md:20`。）
3. **局部词形 / 语法绑定机制类别已被连续否决**：R7 BLOCKED/1 → R8 AWN0 但独立完整性 BLOCKED/1（攻击反例 `将结论视为事实不能默当获准安全残余`、`把结果当作真实数据不得视作批准合规载荷` 逃逸）→ R9 BLOCKED/1 + 协议补核 BLOCKED/1（反例 `我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷` 单 match 认证误免）。R9 补核解除条件明确："若需来源绑定、显式提及契约或验收 scope 改变必须新关键裁决及独立审，**不再只加一个标记**"。
   （锚点：`session-snapshot.md:39,41,49,58`；`docs/design/…R10.md:90–97`；`review-…-DESIGN-R10.md:67–77`。）
4. **白名单 / 自授路径被明确排除**：新增报告、复制该句、按 EVD/task/hash 建白名单均不能解决来源资格；exact phrase 搜索只见后续讨论与派生提取，且未覆盖全部历史（不据此证明所有历史来源不存在）。
   （锚点：`reports/…R10-contract-decision.md:28`；`session-snapshot.md:33`。）
5. **唯一未被否决的路径是 B（新提及证据接口），但它超出"原接口保持"范围且未获证可行**：R10 分析对 B 的判定是 "Not ready. Any useful mention route requires a concrete contract decision, source eligibility and independent review"（`docs/design/…R10.md:15`）；R10 契约裁决报告对 B 的依赖理由明示 "**尚未获证可行**……本项不能承诺可实施"（`reports/…R10-contract-decision.md:75`）。DEC342 用户实际选择 A，B 未被选择（该句为 DEC342 时点历史事实；**送达后 DEC344 已另行授权限定来源接口设计 + 独立 R11（零产品），当前状态见 §8.4**）。
6. **Code R6 B1 的三个有界修复方向不能改变上述结论**：(a) 或-析取中位闭表扩展只覆盖 1536 形；(b) ASCII-alnum 技术词填充类、(c) 技术提及封闭标记形 / `当真` 加宾语尾——(b)(c) 正是让 1587/1588 clean 所需、也正是 R7–R9 否决链针对的"局部词形/闭表豁免"机制；Developer 自己的提案"自认不覆盖 1588"，且每项"需有界设计 delta + 用户批准，禁静默扩表"。
   （锚点：`review-…-CODE-R6.md:45–46`。）

**因此**：不存在"既保持原接口、又让完整四源 clean、又拒绝全部已证攻击"的已获证产品修复。**下一项需要的具体裁决与未确定事项**见 §9；在此之前，任何"修好了"的宣称都无证。

---

## 6. 健康检查 16 issues 逐项分类（以 strict raw 为准）

raw 头部计数 16 issues（`…txt:1`）；逐行可见 13 个 `[FAIL]` 条目（Check 30 含 2 violations，18d/18f 各含多条子句；行级 vs 子句级计数口径 raw 未说明，以头部 16 为准，不自行重算）。分类如下：

| raw 行 | 检查 | 对象 | 分类 | 依据/说明 |
|---|---|---|---|---|
| :2 | 10 M5 反模式（1 项） | **已定位（增补）**：`docs/design/FIX-445-source-verification.md:234`（R0 时代旧选项表 A3 行，"选项列表无 AUQ"模式） | **需用户裁决（历史冻结面）** | 定向诊断工件 `…diagnostics-20261013.json:764–774` 为唯一非豁免命中；其余 24 处命中全在 record_scope_dirs（docs/release、docs/reviews、docs/requirements）豁免面（`:776–990`）。该文件是冻结历史设计文档，**不允许直接改**（Coordinator 增补指令）。处置候选仅三种：接受该 FAIL 持续显式 / 授权检查器口径裁决（infra 票）/ 授权不改原文的勘误附件（新文件） |
| :3 | 18c required_evidence 缺"事实依据/结构化事实" | FIX-445 packet | **记录可补正（文本层）** | 补正内容可凭既存事实书写：actual 64/92.738s/1FAIL、CodeR6 BLOCKED/3 报告路径+SHA、R10 三件套路径+SHA、EVD 链（1659/1662/1664）。写入需 Coordinator 授权 |
| :4 | 18d success_metrics 过程性指标 | FIX-444 | **PASS 不得填 / 同类诊断超范围** | FIX-444 blocked（`session-snapshot.md:21`），处置模式同 FIX-445，本报告不展开（OUT#5） |
| :5 | 18d success_metrics 缺用户可见结果 | FIX-445 | **记录可补正（指标文本）** | §7 提供用户可见指标候选+锚点；补的是"指标定义"，不是达成值 |
| :6–7 | 18d-RB2 last_run.status≠PASS / exit≠0 | FIX-444 + FIX-445 | **PASS 字段不得填写** | last_run 反映产品实际运行=FAIL（64tests/1FAIL）；填 PASS=编造（P-v1 P1）。仅当产品真实通过并机录后方可变更 |
| :8,10 | 18f quality_budget 各维 status≠PASS（FIX-444 另含 vertical_slice） | FIX-444 | **PASS 不得填 / 超范围** | 同 :4 |
| :9,11 | 18f validation 缺可运行命令/信号 + status≠PASS + vertical_slice 三字段 | FIX-445 | **混合**：validation/user_visible_slice/demo_path 文本**可补正**；status **不得填 PASS** | 可运行信号候选：`check-governance --summary-only --scope full --level strict`（本次 raw 生成命令，json `:6–16`）、`tests/test_hooks.py` live 测试 `test_current_real_rows_all_clean_under_real_step12`（supplement-evidence:34）、blob/SHA 校验（CodeR6 :6–7）。status=EXEMPT 需 justified 且属用户裁决；**安全维不可豁免**（C3）。vertical_slice.status 同 last_run 逻辑 |
| :12 | 28s evidence-log 1,155,447B | 全局 | **治理动作（归档）需授权**，非记录补正 | 归档流程存在（AGENTS.md E 项）；属推进类动作需授权，本任务不动 |
| :13 | 30 Review Closure 2 violations | **已定位（增补）**：V1×2 = FIX-444（R3=BLOCKED）与 FIX-445（R10=BLOCKED），均为 "closes the chain for escalation but is not an approval"；520 tasks checked | **与产品修复路径绑定（记录不可补、PASS 不得填）** | `…diagnostics-20261013.json:992–1006,1074`。状态机要求链终态为批准类结论，两链现为升级闭合态。唯一正规闭合路径 = 对应产品工作真实完成后复审获 APPROVED / APPROVED_WITH_NOTES(0)（FIX-445 即 §5/§9B 路径；FIX-444 另行裁决）；不可通过记录编辑闭合、不可改冻结审查史 |
| :14 | 31 R1 账目 ragged table row | `docs/design/FIX-445-source-verification-R1.md` | **历史文档修正需授权** | 本任务禁改历史报告（任务硬门槛"不改历史报告与原源"）；修正或接受由用户裁决 |
| :15–28 | 各 WARN（41 untracked、模块规模、hooks_drift、数据尺寸 WARN、42 undated-record、3 风险警示） | 多对象 | 非阻断，**不在本诊断展开** | WARN 不计入 issues 清零的阻断集，但 30c 的 42 undated-record WARN 与 :27 渐进 FAIL 趋势应知悉 |

**汇总（2026-10-13 增补定位后）**：记录可补正 = :3、:5、:9/:11 的 validation/user_visible_slice/demo_path 文本；PASS 不得填 = :6–7、:8–11 的全部 status 字段；与产品修复路径绑定（记录不可补）= :13（V1×2）；需用户裁决 = :2（M5 历史冻结面）、:12（归档授权）、:14（历史格式）、EXEMPT 正当性；超范围同类 = :4、:6、:8、:10（FIX-444）。

### 6.1 检查器可靠性与定向诊断增补事实（Coordinator 2026-10-13 送达）

定向诊断工件 `.governance/incidents/FIX-445-health-resume-diagnostics-20261013.json`（只读既有 verify_workflow 检查函数、无新门规则，`whole_health_pass_claimed:false`、`product_changes:false`）提供三项增补事实：

1. **风险检查盲点（fail-closed 保持，不计为已修）**：工件内 `risk_staleness.total_open=0`、`risk_escalation.total_open=0`（`:754–763`），与 bootstrap 聚合的 20 open risks（Coordinator 单源事实）不一致。Coordinator 已定位差异机理：`risk_domain.py:95–97` 仅认可 status **精确等于**「打开」，而实际 risk-log 50 行的第 9 字段无任何精确「打开」——既有打开均带括注；RISK052 等行列偏移进缓解动作列。**结论：checks 2/8 返回 0 不能证明 20 条风险被正确检查**。处置纪律（按 Coordinator 增补指令）：不据此称 0 risk 或风险过期检查通过；不把该差异计为已修；不扩产品、不补造风险 deadline/内容；20 open / 0 到期升级以 bootstrap 单源为准并标注解析正确性存疑；列偏移的历史成因不调查（不深入陌生原因）。治理纠正须新 infra 票并保持每条既有风险语义（§9A-3）。
2. **证据完整性面（位于工件，非 strict 16 计数内；本条经当场校准）**：`evidence_completeness` completed=36 / evidenced=29，历史缺证 7 项 = AUDIT-097、SYSGAP-015~020（`:9–21`）。**校准记录（2026-10-13，Coordinator 指正 + Analyst 一手复核）**：初稿称「本工件未并入归档口径」系**错误**——工件 `:7` 明示复用既有只读检查函数，而 `verify_workflow.py:10408–10462` 的 `check_gate_consistency`/`check_evidence_completeness` 经 `GovernanceDataSource` 聚合 hot+archive（`:10411–10412` 实例化与取数；注释 `:10437`"cover both hot files + archive files"、`:10452`"include archived tasks"；Analyst 本会话实读核对）。故 active missing=[] 与 historical 7 项保留**已是归档聚合口径下的结果**——7 项属历史分类面，不存在「待归档重验」缺口，G9 相应闭合，无需凭空重验归档弥补假设。另有 700+ orphan_evidence 条目（`:37–751`）按不深入陌生原因纪律仅记录存在、不逐项归因。
3. **M5 豁免面确认**：record_scope_dirs = docs/release、docs/reviews、docs/requirements（`:986–990`）；本报告位于 docs/requirements/ 属记录豁免面，§9 选项呈现不构成新 M5 触发。

---

## 7. 成功指标候选（目标 vs 已达标事实，附原证据锚点）

### 7.1 目标类指标（**全部未达成**，供 18d success_metrics / vertical_slice 补正候选）

| # | 候选指标（用户可观察口径） | 当前实际值 | 原证据锚点 |
|---|---|---|---|
| T1 | strict 全量健康检查 issues=0 且 exit 0 | 16 issues / exit 1 | `…txt:1`；json `:21` |
| T2 | live 四任务门四任务全 clean（hits=[]） | FIX-445 批 FAB_HIT（56 行；72/24/72/56 中 445 命中） | `review-…-CODE-R6.md:27`（M2）、`:40`；`session-snapshot.md:64` |
| T3 | 模块测试 64 tests / 0 failure | 1 failure（=live 门） | `review-…-CODE-R6.md:32`（M7）；`session-snapshot.md:63` |
| T4 | Code R6 三 blocker（B1 live 门 / B2 batch-any / B3 D20）闭合并经独立 Code 复审 | BLOCKED/3 保持 | `review-…-CODE-R6.md:11,20,38–57` |
| T5 | W1 语料分配裁决落地（per-line8 / 独立 glob24 / 总32 + 诊断分类，若产品重开） | 未裁决；触发条件当前已满足（54>32、26 JSON>24） | `reports/…R10-contract-decision.md:32–50`；`supplement-…-calibration.md:27–32,36–38` |
| T6 | 用户运行 `/governance → 检查健康` 时，合法技术证据行不再被误报为编造（vertical_slice.user_visible_slice 候选） | 三合法技术行假 BLOCK（EVD-1536/1587/1588） | `review-…-CODE-R6.md:38–44`（B1） |
| T7 | demo_path 信号：live 测试名 + strict 健康命令 + blob 绑定（vertical_slice.demo_path 候选） | 字段缺失（raw :11） | `supplement-…-evidence.md:34`；json `:6–16`；`review-…-CODE-R6.md:6–7` |

### 7.2 已达标事实（**不是待办**，防混读、防重复立项、防填 PASS）

| # | 事实 | 原证据锚点 |
|---|---|---|
| F1 | FEAT-097 approved（独立 R6 AWN0/seq17；bridge33/接线5/注册77/契约27；纯 judge 9call<10ms；完整 engine 1115/612.826s 保持） | `session-snapshot.md:19,86` |
| F2 | FIX-443 approved（独立 R0 AWN0/seq16；CPU27.8/CLI36/434339semantic/32MiB/1500 门实际通过） | `session-snapshot.md:20` |
| F3 | 安全对抗面逐例独立复现全 BLOCK（24/25 有效 probe，G1 为审查方装置缺陷） | `review-…-CODE-R6.md:28`（M3）、`:70–74` |
| F4 | R10 静态契约分析质量经三重机录审查闭环（seq46 BLOCKED/1 证据缺 → seq47 AWN0 补核 → seq48 AWN0 校准；中心论证保持成立） | `reports/…R10-contract-decision.md:8–10`；`session-snapshot.md:29–32` |
| F5 | 治理守卫 5 faces PASS0（EVD1660/1664，结构守卫，**非产品健康通过**） | `session-snapshot.md:72` |
| F6 | 冻结产品源绑定一致（hook blob a327f812…/SHA c7d5a01f…；test blob 0e8aff2f…/SHA 60fe5db5…；R9 机录前实测校验一致） | `session-snapshot.md:62`；`review-…-CODE-R6.md:6` |

**填报纪律**：7.1 各项在产品/裁决未落地前不得作为已达成写入任何 status 字段；7.2 各项不得再立项为待办。T1–T4 依赖 §5 判断的产品修复路径裁决，T5 依赖产品重开决策——**本报告不承诺其中任何一项可达成**。

---

## 8. DEC342/DEC343 语义边界：继续上次 ≠ 接受变更

1. **DEC342**（机录 op-44c90963b29d451dbe49d81bd7665bbd / EVD-1662，2026-10-13T02:39:31Z）：用户在 A/B 两可审查处置项中实际选择 **A=保持原门并暂停**；随后 goal 实读 rev4 → pause → **rev5/paused/disarmed**，roundsStarted0/max8，未标 complete 或 blocked。**B（新提及证据接口设计）未被选择**：不启动 R11、不产品实施、无提交/推送/发布。
   （锚点：`reports/…R10-contract-decision.md:79–80`；`session-snapshot.md:10–11,85`。）
2. **DEC343**（本会话）：仅恢复**健康工作单元**（检查健康 + 本诊断），不授权新接口/架构或实施。
   （锚点：任务派发 prompt 任务上下文。）
3. **推论（防误读）**：本次"继续上次"恢复的是 DEC342 暂停时的工作单元上下文，**不等于接受 B、不等于接受任何验收变更、不等于风险接受、不等于健康完成**。原 Guard G、来源授权、完整四源验收、性能资源门、两产品范围全部保持（`session-snapshot.md:10`）；暂停语义是"明确停止执行与保全，不把登记未解问题当完成"（`reports/…R10-contract-decision.md:66`）。B 类工作若要启动，必须新的显式用户裁决（§9 选项一）。
4. **当前事实更新（2026-10-13 本报告送达后，DEC344——事实不追溯）**：用户已新裁决 **DEC344 = 限定来源接口设计 + 独立 R11 审查，不做产品**。本节 1–3 对 DEC342/DEC343 的描述为报告送达时点的历史事实，原样保留不改；自 DEC344 起，**「B 未被选择」不再是当前状态**——§9B 所载「设计 + 独立 R11、零产品」授权范围即 DEC344 已生效的选择。该更新**不改变本报告任何产品/验收结论**：§5（原接口保持下无获证可执行产品修复）、§6（PASS 不得填）、§7.1（目标全部未达成）全部维持——DEC344 授权的是设计工作开始，不是可行性获证、实现就绪、产品写入或任何状态变更；可行性仍以 R11 设计与独立审查结果为准。
5. **优先级**：沿用 FIX-445 已登记优先级，不调整任务排序（任务上下文明示；本报告不产生排序变更）。

---

## 9. 可供用户决策的具体范围（方案，非决策；逐项标注需求源；不承诺原接口就绪）

### 9A 基于原目标的补正建议——明确范围（记录/治理层，产品阻断不动）

**原目标锚定**：用户「恢复检查健康」（DEC343 健康工作单元）+ 治理总目标（plan-tracker:7 自动化治理健康，经 `docs/design/…R10.md:18` 引用）。本包服务于「健康报告可归因、非产品项可清零」，不触碰产品验收门。

| 子项 | 内容与既存事实来源 | 边界（不含什么） |
|---|---|---|
| A-1 执行包记录文本补正（FIX-445） | ① 18c required_evidence 补「事实依据/结构化事实」措辞——素材：actual 64/92.738s/1FAIL、CodeR6 报告路径+SHA、R10 三件套路径+SHA、EVD1659/1662/1664；② 18d success_metrics 以 §7.1 T1/T2/T3/T6 用户可见指标替换过程性指标；③ 18f validation 填可运行信号：strict 健康命令（本次 raw 生成命令，json `:6–16`）、live 测试 `test_current_real_rows_all_clean_under_real_step12`（supplement-evidence:34）、blob/SHA 双验（CodeR6:6–7）；④ vertical_slice.user_visible_slice / demo_path 文本（§7.1 T6/T7） | 所有 **status 字段一律不动**（FAIL 保持）；写入主体 = Coordinator 经授权（Analyst 不写 .governance/）；精确 diff 需 packet 当前值（G2）；FIX-444 同类字段另派发（G5） |
| A-2 治理数据动作（各自需授权，不含"登记待以后"） | ① evidence-log 归档（28s，1,155,447B；推进类动作，dry-run 先行）；② Check 31（R1 ragged row）与 Check 10（M5 :234）均为历史冻结文档面——处置候选仅三种：接受持续 FAIL 显式 / 授权检查器口径裁决（infra 票）/ 授权不改原文的勘误附件（新文件），授权时点当场选定 | 一律**不直接改冻结历史**（Coordinator 增补指令）；每项须在授权时点当场裁决处置类别，不得悬置 |
| A-3 风险检查盲点治理纠正（新增，源自 §6.1-1） | `risk_domain.py:95–97` 状态口径修复（精确匹配 → 覆盖带括注打开 + 列偏移行）；属插件 infra 代码变更，须**新票入账（change-triage）+ 独立审查**；验收 = 50 行真实数据逐条对账，20 open 的 staleness/escalation 真实状态以修复后正确解析为准 | 不扩产品语义；**不补造风险 deadline/内容**；**保持每条既有风险语义**（Coordinator 增补指令）；修复落地并核验前，checks 2/8 的 0 不作为任何通过依据 |

**需求源（9A 整包）**：机器信号（strict raw 16 issues `…txt:2–14` + 定向诊断工件）。**9A 不承诺 T1（issues=0）达成**——18d-RB2/18f status 与 Check 30 V1 仍锁在产品修复之后。

### 9B 新设计授权——明确范围（B 路径 R11；**DEC344 已选择授权本范围**——2026-10-13 报告送达后事实，见 §8.4；下表范围内容不变，原「仅当用户裁决选择」条件已由 DEC344 满足，授权边界仍以表中"包含/不包含"为准）

| 面 | 内容 |
|---|---|
| 授权**包含** | ① 新 prose/mention 来源绑定**接口设计文档**（唯一交付物）；② 独立 R11 审查（账本 max10+1 不重置；R11 MUST 以原 R10 报告/补核/校准三件套 + 本报告 §5/§7 为强制输入挑战）。设计必须覆盖：来源资格规则（含 EVD-1587 既有 provenance 调查的存在/不存在证据边界）、提及载体完整载荷与 occurrence 边界、raw-slice 映射、strict JSON 故障语义、与 M5/Guard G 的显式交互（现 T2/Guard G 原规则保持、不得默扩豁免）、W1 语料分配规范并入（per-line8 / 独立 glob24 / 总32 + globcap 与 PATHDROP 分列诊断 + 三静态验收例，`reports/…R10-contract-decision.md:36–50`） |
| 授权**不包含** | 产品写入/实施；减源/skip；改历史 EVD/审查报告/冻结分析；新授权权威、hash/ID 白名单、sidecar/报告自授；验收放宽（完整 EVD-1587 零改、12 攻击逐例拒绝、四任务源非零/zero skipped/RC0、B3 保护、性能资源门全部保持）；自动 R12（R11 仍 BLOCKED 则再升级，不自动续） |
| 非承诺声明 | 授权 ≠ 可行性获证：R10 明示 B「尚未获证可行……不能承诺可实施」（`reports/…R10-contract-decision.md:75`）；EVD-1587 既有合格 provenance 未建立（同文件 :28）；**本报告同样不承诺原接口或 B 路径就绪**（遵 Coordinator 增补指令） |
| 需求源 | 活性缺陷（R10 分析推荐方向 `docs/design/…R10.md:109,124`；`reports/…R10-contract-decision.md:69–75`） |

### 9C 健康目标口径裁决（保留原选项三）

裁决本健康工作单元成功口径：(a) strict 完整清零——被 18d-RB2/18f status 与 Check 30 V1 锁死在 FIX-445/FIX-444 产品通过之后；或 (b) 分阶段口径——9A 非产品项先清零、产品类 FAIL 保持显式归因并挂起。需求源：用户点名（「恢复检查健康」意图边界由用户自定）。口径 (b) 不改变任何验收门，只改变工作单元目标定义与呈现。

**未确定事项**（任一选项落地前必须知悉）：EVD-1587 正文是否存在全部历史范围内的既有获证提及载体（未证明存在也未证明不存在）；B 路径可实施性未获证；human external membership/DRI 资格未知；首次 17 vs strict 16 差异项未定位（G1）。

---

## 10. 剩余证据缺口

| # | 缺口 | 影响 | 建议补齐方式（需授权/Coordinator） |
|---|---|---|---|
| G1 | 首次 full-health 17 issues 的 raw（与 strict 16 的差异项未定位，**原因未知**——H2 方向假设已撤回） | 两时点账目混读风险；在事实取得前不得宣称差异已修或收敛 | 提供首次检查 raw 文件或重放对照（重放属推进类动作）；取得事实前不作方向假设 |
| G2 | `execution-packets.json` FIX-445 packet 当前字段值 | §6 可补正项只能给建议内容，不能给精确 diff（Analyst 禁直读热面） | Coordinator 经 governance-bootstrap/授权读取后对照本报告 §6/§7 补正 |
| G3 | ~~FAIL 10 M5 具体源文件~~ **已定位（增补闭合）**：`docs/design/FIX-445-source-verification.md:234` | 处置候选已入 §6/§9A-2，待用户裁决（接受显式 / 检查器口径票 / 勘误附件） | — |
| G4 | ~~FAIL 30 violations 明细~~ **已定位（增补闭合）**：V1×2 = FIX-444 R3 / FIX-445 R10（升级闭合非批准） | 闭合路径 = 产品修复 + 复审获批准类终态（§6.1/§9B），记录不可补 | — |
| G8 | `risk_domain.py:95–97` 口径修复的授权与入账（§9A-3） | 修复核验前 checks 2/8 的 0 不可用作通过依据；不补造风险内容 | 用户/Coordinator 授权新 infra 票 + 独立审查 |
| G9 | ~~7 项历史缺证的归档覆盖核对~~ **已闭合（当场校准）**：初稿「工件未并入归档口径」系错误 | 检查函数已聚合 hot+archive（`verify_workflow.py:10408–10462`，Analyst 一手复核，见 §6.1-2 校准记录）；active missing=[]、historical 7 项为归档口径下保留的历史分类，无需重验 | — |
| G5 | FIX-444 同类字段（18d/18d-RB2/18f）的同等诊断 | 其 PASS 同样不得填，但补正候选未生成 | 另行派发或并入选项二授权包 |
| G6 | EVD-1587 正文全部历史来源覆盖 | B 路径先决条件之一 | 仅在选项一获裁后由授权的 provenance 调查执行 |
| G7 | DRI / human external membership 资格 | 独立性声明边界 | 用户提供事实，否则保持"未知" |

---

## 11. 质量标准自检（requirement-clarification 输出 + Analyst 硬门槛）

- [x] 问题陈述不包含解决方案描述（§1 Q1 为现状+锚点）
- [x] 成功标准至少 1 个可量化（§1 Q5：issues=0/exit 0、hits=[]、0 failure）
- [x] IN/OUT 列表无重叠，OUT ≥1 条有理由（§2，6 条 OUT 各附理由）
- [x] 干系人列表非空，每条有角色描述（§3）
- [x] 约束和假设已列出（§3：C1–C7、H1–H3 含验证计划；假设显式化 100%）
- [x] 每条结论有可定位来源（全文锚点制：文件:行 / SHA / 机录 op/EVD）
- [x] 原 64tests/1FAIL、CodeR6 BLOCKED/3、W1、完整四源门保持失败/未解（§1、§5、§7.1；本报告零状态变更）
- [x] 记录可补正 vs PASS 不得填已分列（§6 汇总）
- [x] DEC342 时点「B 未被选择」与继续 ≠ 接受变更已说明（§8.1–8.3）；送达后 DEC344 已授权 §9B 范围（§8.4 当前事实更新，不追溯历史）
- [x] 可供用户决策的具体范围已提出且逐项标需求源（§9；不承诺无证可行）
- [x] 非竞品/立项全产物任务：未编造人物、市场、结果（§2 OUT#6）
- [x] 未创建子 agent、未执行 shell、未写产品代码、未审自己的产物、未直读热面、未与用户直接交互
- [x] Coordinator 增补事实（定向诊断工件 + 风险口径差异）已并入 §0/§6/§6.1/§9/§10；风险差异保持 fail-closed、未计为已修、未深挖列偏移成因、未扩产品、未补造风险 deadline/内容（遵增补指令）；初稿 §0 文件计数笔误（13→12）已当场修正并留痕于本行
- [x] 第二轮当场校准（Coordinator 指正，2026-10-13）：① §6.1-2/G9「未并入归档口径」错误已纠正——`verify_workflow.py:10408–10462` 检查函数经 GovernanceDataSource 聚合 hot+archive（Analyst 一手实读复核），historical 7 项为归档口径下保留的历史分类，G9 闭合；② H2「差异一项为 strict 收敛」方向性假设已撤回——17/16 差异原因未知、无收敛/已修结论（G1 同步一致化）；③ §5/§8/§9B 已加 DEC344 当前事实更新（限定来源接口设计 + 独立 R11、零产品；历史 DEC343 描述保留不追溯）；全部校准记录保留于原文对应位置

**本报告不变项声明**：未修改任何状态或验收门；FIX-445 保持 blocked；DEC342 原门暂停语义未被推翻；所有历史报告与原源冻结不动；无新授权权威、hash/ID 白名单、减源 skip 或免安全规则。DEC344（送达后事实）授权范围 = §9B 所载设计 + 独立 R11、零产品，不改变本报告任何产品/验收结论。
