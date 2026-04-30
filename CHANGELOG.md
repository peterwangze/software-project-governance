# Changelog

本文件记录 `software-project-governance` 的每个版本变更。

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
- **pre-commit hook Step 6 升级**：CLAUDE.md 直接修改检测从 WARNING → BLOCKING——BOOTSTRAP DISCIPLINE 违反（第 5+ 次）后升级为阻断级强制力
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

- **bootstrap 变更纪律**：governance-init.md 和 CLAUDE.md 新增 Step 1.5——MUST NOT 直接修改 CLAUDE.md 添加新行为，MUST 先改 governance-init.md 注入模板（canonical source），通过版本 bump + /plugin update + bootstrap 自升级到达用户
- **Tier 审计补齐**：EVD-123——用户反馈驱动密集修复轮次审计（D1/D3/D4）。审计发现 2 项治理违规：所有 FIX 任务 Gate 标记错误（G8→G11 修正）+ 全部先执行后入账（违反 M7.5）

---

## [0.6.8] — 2026-04-29

### 修复

- **bootstrap 自升级**：版本变化检测不再只是提示用户运行命令——agent 检测到 bootstrap 落后时**自动替换 CLAUDE.md 的 bootstrap 段为最新模板**。用户 `/plugin update` → 下次会话 → 自动完成，零用户行动。governance-update 命令降级为手动回退选项。

---

## [0.6.7] — 2026-04-29

### 新增

- **governance-update 命令**：老用户升级路径的核心——`/plugin update` 获取新版本后运行此命令，将 CLAUDE.md 的 bootstrap 段更新到最新。**不触碰 .governance/ 数据**——只替换 bootstrap 模板段，保留用户的项目配置和治理记录。bootstrap 版本变化检测自动提示用户运行此命令。

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

- **用户视角强制原则**（`references/user-perspective-principle.md`）：所有规划/设计/开发/测试 MUST 回答三个问题——用户怎么获得变更？用户怎么知道变更存在？用户体验真的变了吗？含 6 项检查清单 + 5 种反模式定义 + 用户旅程描述要求。集成到 SKILL.md M2.1 + CLAUDE.md 干活前检查 + governance-init 注入模板。
- **governance-status 版本新鲜度检查**（Step 3.5）：每次展示状态时自动检查插件是否最新，OUTDATED 时输出版本差距 + commits behind + 更新指引。已安装用户不再被遗忘。
- **近期变更用户可达性审计**：4 个版本逐版审查——发现 3/4 对已安装用户有断点。0.6.1 治理开关是唯一对已安装用户立即可用的功能。

---

## [0.6.4] — 2026-04-28

### 新增

- **post-commit governance hook**：每次 `git commit` 后自动触发——提取 commit message 中的 task ID → 检查 plan-tracker 中是否存在 → 检查 evidence-log 中是否有证据 → 输出 check-governance 摘要。消除会话中间"commit 之间"的治理盲区。Hook 不阻塞 commit——只报告，不拒绝。
- **RISK-024**：记录"端点强制模型 vs 流式执行行为的结构性不匹配"风险——5-Why 根因分析

### 修复

- **governance-init Step 8**：新项目初始化时自动安装 post-commit hook
- **CLAUDE.md bootstrap**：新增 Hook 存活检测——hook 缺失时 MUST 提醒用户重装

---

## [0.6.3] — 2026-04-28

### 变更

- **VERSIONING.md 重写**：砍掉 alpha/beta/rc 预发布标签——三层 Major.Minor.Patch 本身提供细粒度。Patch 就是最小增量单位。每轮有意义的变更 MUST bump PATCH，不攒着等 Minor。新增"用户如何更新"章节（3 种更新方式 + freshness 检查）。
- **check-plugin-freshness 子命令**：`python scripts/verify_workflow.py check-plugin-freshness` 对比 installed_plugins.json 的 gitCommitSha 与源仓库 HEAD，输出 installed/source/status/action。

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
- **跨会话状态恢复**：M4.1/M4.2 升级——session-snapshot.md 格式定义 + 会话加载/生成协议。CLAUDE.md 收工前检查自动生成快照
- **触发模式实现**：CLAUDE.md Bootstrap Step 0 —— always-on/on-demand/silent-track 三种行为差异可检测
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

- **governance-init bootstrap 不对称**：本仓库 CLAUDE.md 与注入模板严重不对称（~80 行 vs 4 行）→ 同步为完整中文模板，按 profile 差异化注入

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
- **CLAUDE.md 自包含升级**：关键决策分类内嵌（不依赖 SKILL.md 加载状态）+ 故障排除章节

### 变更

- **DRI 模型落地**：plan-tracker Owner 列改为单值 DRI，新增 Escalation 列（20 列模板）
- **交互边界规则升级**：新增 DRI 决策权限定义章节
- **stage-gates.md**：新增原则 #6（Closure Follow-Through）、原则 #7（审计检查点）、原则 #8（DRI 检查）、原则 #9（Tier 审计检查点）
- **Tier 1 双源合并**：skills/ 成为运行时唯一事实源，workflows/rules/ 和 workflows/stages/ 已删除
- **审计触发条件扩展**：SKILL.md M2.1 + audit-framework.md D1/D3/D4 新增"Tier 完成"触发条件

### 修复

- parse_gate_detail regex 从 `###` 改为 `##`（pre-existing bug——gate 和 gate-check 子命令均无法找到 Gate 定义）
- 证据质量升级：5 条"会话上下文"引用替换为持久化文件路径，EVD-070 循环引修复
- CLAUDE.md/SKILL.md 循环依赖解耦

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
