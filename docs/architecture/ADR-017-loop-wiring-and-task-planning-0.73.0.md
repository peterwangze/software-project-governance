# ADR-017: 入口引导 / Loop 生产接线 / 任务规划闭环重构（0.73.0）

- **Status**: Proposed (awaiting Design Review R1; R0 = NEEDS_CHANGE / unresolved_blockers=3, 2026-08-02)
- **Date**: 2026-08-02
- **Version**: 0.73.0 (MINOR)
- **Author**: Architect
- **Scope**: REQ-104 / REQ-105 / REQ-106 + FIX-236 / FIX-237 / FIX-238（AUDIT-142 消费方）
- **Supersedes / continues**: 不替换 ADR-014；沿用其 §6 四接线点语义（A/B/C/D）与薄调用原则。执行 AUDIT-142 诊断报告的重构建议，并作为 FIX-236~238 的架构授权。
- **Related**: AUDIT-142 诊断报告（docs/requirements/entry-loop-planning-rearchitecture-0.72.0.md）、AUDIT-140/141、SYSGAP-047、EVD-852、FIX-222~229（0.71.0/0.72.0 能力交付）、DEC-096（resolve_entry 双 root）、DEC-138（Check 30 历史豁免）、ADR-014（loop engine 接线）、FIX-226（task-priority-analysis 工具）、REVIEW-ADR-017-DESIGN-R0（2026-08-02，NEEDS_CHANGE/3）

### 1.0 Design Review R0 处置总表（REVIEW-ADR-017-DESIGN-R0）

> R0 结论：NEEDS_CHANGE / unresolved_blockers=3（P1-1/P1-2/P1-3）+ P2×3 + P3×6。架构方向不变，本 ADR 为规格级修订。下表为每条发现的处置位置与状态；全部修订已并入本文档正文。

| # | 发现 | 处置 | 修订位置 |
|---|------|------|---------|
| P1-1 | Wiring A 挂接锚点缺失（全仓无 review 结论机器写入器；review-*.md 与 evidence-log 行由 agent 手工写盘） | **新建薄 CLI `review-record`** 作为唯一机器化 review 结论持久化路径并在此挂接 Wiring A；"调用点≥2" check 改 AST/导入图分析并排除 docstring/注释，加 loop_gate_processor.py:69 docstring 负样本测试 | §3.2 / §3.4 / §3.5 |
| P1-2 | Check 30 V6 语义不完备（无 R≥MAX_ROUNDS 豁免、窗口语义不明、触发对象边界不明、缺负样本） | V6 规格四项明确：R≥3 与 V3 求交豁免；窗口=参数化时长（默认 24h）+ commit 可选附加触发（定义数据来源）；触发对象=晚于 FIX174_NORMALIZATION_DATE 的 NEEDS_CHANGE 终态轮（豁免随链）；补跨 session + fuse 熔断两个负样本测试 | §3.4 / §3.5 |
| P1-3 | 第三类数据债：unblocked 混入非可执行状态行（SYSGAP-046 🚧 / FIX-197 ⏸ SPLIT_TO / REL-058 ⛔ BLOCKED / AUDIT-136 ⛔ BLOCKED_REVIEW_FUSE） | 237.1/237.2 增加第三类：unblocked/next 候选 MUST 排除非可执行状态（⛔/⏸/🚧/✅/漂移⏳）；加工具测试（上述 4 任务不入 unblocked） | §4.2 / §4.4 |
| P2-1 | FIX-238.4 范围过宽（web-console --governance-entry 已非阻塞，FIX-150/d7928c1） | 收缩为 `--install` 超时参数化（SPG_WEB_INSTALL_TIMEOUT）+ 回归测试 | §2.1 / §2.4 / §2.5 |
| P2-2 | fuse fail-open 路径未显式声明 | 显式声明：无 v2 payload 文件才 fail-open（v1/classic no-op 保持）；文件存在但损坏 → fail-closed + 测试 | §3.1 / §3.4 / §3.5 |
| P2-3 | 风险表缓解措辞未绑定验证套件 | 缓解改 Check 30/review-closure 套件验证 | §3.5 |
| P3-1 | 文件名版本不一致（0.72.0 vs 目标 0.73.0） | 文件重命名为 ADR-017-loop-wiring-and-task-planning-**0.73.0**.md | 文件层（本文件） |
| P3-2 | vendor 引导脚本归属未定 | 归属 PLUGIN_HOME 侧（`<plugin_home>/infra/bootstrap.{sh,cmd}`），非宿主 .governance/ | §2.2 / §2.4 |
| P3-3 | 旧宿主"陈旧标记"无定义 | 定义：CLAUDE.md 引导段含 `@bootstrap-version` 头；检测到 SKILL frontmatter `active_version` > 引导段版本 → 标陈旧 | §2.4 |
| P3-4 | Requirement Review 落档未列为前置 | 列为 Phase 1 前置门（REQ-104/105/106 正式 requirement review 文件落档后才实施） | §7 |
| P3-5 | 推荐桥读取端未明确 | 明确：新增 `next-candidates` 薄 CLI（verify_workflow.py），governance-status / Scenario F 消费 | §3.4 / §7 |
| P3-6 | REQ 编号映射未说明 | 说明：诊断报告草案编号 REQ-103/104/105 = 本 ADR/plan-tracker 权威编号 REQ-104/105/106（REQ-103 已被 0.60.0 历史占用） | §1.3 注 |

---

## 1. Context

### 1.1 用户反馈（2026-08-02，三簇 7 项）

| 簇 | 反馈 | 用户原话要点 |
|---|------|-------------|
| 入口 | 1.1 | 执行 /governance 后运行 resolve_entry.py，真实环境直接找不到脚本 |
| 入口 | 1.2 | 当前环境运行 resolve_entry.py 会卡住 |
| Loop | 2.1 | Developer 修改检视意见后不触发复审——小循环失效 |
| Loop | 2.2 | 单点任务完成后直接结束，不回归上层循环——大循环失效 |
| 规划 | 3.1 | 任务推进不分析依赖和优先级，机械挑未完成项 |
| 规划 | 3.2 | 各层 loop 缺任务规划能力，关键节点完成后不推荐合理推进事项 |
| 规划 | 3.3 | 新事项进入时不系统分析优先级和依赖 |

### 1.2 AUDIT-142 根因（5 项，均 ✅CONFIRMED）

| # | 根因 | 症状覆盖 | 证据 |
|---|------|---------|------|
| R1 | **capability-without-wiring**——resolve_entry / process_gate_result / task-priority-analysis 均存在且可运行，但生产执行链无调用点（process_gate_result 生产调用点 = 0；task-priority-analysis evidence-log 0 次执行记录） | 2.1、2.2、3.2 | F6、F11 |
| R2 | **真实宿主传播缺口**——修复只落在 dev 仓库模板（AGENTS.md/CLAUDE.md/commands），已安装宿主（python_game）仍是 0.54.1 时代引导，升级链鸡生蛋 | 1.1、1.2 | F1、F2 |
| R3 | **卡住复合归因**——resolve_entry 本体不可卡（实测 171~236ms），链路慢（check-governance 24.8s / npm install 阻塞 / hooks find 1.2-1.6s×4）与旧宿主 FileNotFound 重试链构成"卡住"感知 | 1.2 | F3、F4、F5、F14、F15 |
| R4 | **任务规划数据债**——依赖列 10 条环 + 状态漂移（已发布任务仍 ⏳），工具输出被污染 → Coordinator 不信任 → 不调用 → 机械选择（恶性循环） | 3.1、3.3 | F12 |
| R5 | **协议内部不一致**——interaction-boundary.md:187（决策表"取最高优先级"）vs :217（违规表已改依赖分析）；behavior-protocol.md:553 依赖分析为软性条件（"如果存在子命令"） | 3.1、3.2 | F9、F10 |

### 1.3 Requirement Review 发现处置（D1~D8）

> 诚实标注：`.governance/review-AUDIT-142-REQUIREMENT-*` 截至 2026-08-02 尚未落档（AUDIT-142 在 plan-tracker 状态为"⏳ 分析中"）。以下 D1~D8 由 Architect 基于用户 7 项反馈与 AUDIT-142 诊断报告推导，作为本 ADR 的设计输入；正式 Requirement Review 结论落档后，如与 D1~D8 有出入，以正式结论为准并追加修订记录。

> **REQ 编号映射（P3-6）**：AUDIT-142 诊断报告 §6 使用的草案编号 REQ-103/104/105（对应入口/loop/任务规划三需求）与本 ADR 及 plan-tracker 的权威编号 REQ-104/105/106 存在 +1 偏移——REQ-103 已被 0.60.0 历史需求（capability-registry 提取）占用。本 ADR 一律使用 **plan-tracker 权威编号**：REQ-104=入口引导可达性、REQ-105=Loop 双环接线、REQ-106=任务规划闭环。引用诊断报告时其 REQ-103/104/105 应译为 REQ-104/105/106。

| # | 需求评审发现 | 来源反馈 | 处置（设计域） |
|---|-------------|---------|---------------|
| D1 | 入口引导可达性——真实宿主（无 AGENTS.md / 旧插件缓存）无法定位 resolve_entry.py 或等价确定性入口 | 1.1 | 域一（REQ-104 / FIX-238） |
| D2 | 入口调用健壮性——resolve_entry 调用无超时兜底、无分类诊断（FileNotFound/超时/python 缺失），链路慢环节无隔离 | 1.2 | 域一（REQ-104 / FIX-238） |
| D3 | 小循环机器接线——复审触发依赖 prose（T1-T4），process_gate_result 生产调用点 = 0 | 2.1 | 域二（REQ-105 / FIX-236） |
| D4 | 大循环回归——任务完成/loop_exit 事件无消费方，下一步推荐无机器执行 | 2.2 | 域二（REQ-105 / FIX-236） |
| D5 | 任务规划工具未集成——task-priority-analysis 零生产调用（入口/交互边界/变更控制均不调用） | 3.1 | 域三（REQ-106 / FIX-237） |
| D6 | 交互边界机械行为——协议矛盾（决策表 vs 违规表）+ 软条件 prose 给 Coordinator 提供不执行路径 | 3.1、3.2 | 域三（REQ-106 / FIX-237） |
| D7 | 变更控制无强制——triage 流程为 docstring/checklist，任务入账无拦截 | 3.3 | 域三（REQ-106 / FIX-237） |
| D8 | 数据债污染工具输出——10 条环 + 状态漂移使工具不可信，是 3.1/3.3 的机制前置 | 3.1、3.3 | 域三前置（FIX-237.1 数据债先行） |

### 1.4 既有资产边界（不可破坏的约束）

1. **resolve_entry.py 双 root 模型（DEC-096）不改**：`host_root`（宿主项目根）与 `PLUGIN_HOME`（插件根）分离，`resolved_root_ok=false` 时 fail-closed 展示 diagnostic；`detect_scenario()` 纯函数语义不变。
2. **loop_paro_engine / loop_engine 纯函数不改**：本 ADR 的接线是**薄调用**（≤10 行/点），不把业务逻辑塞进 verify_workflow.py。
3. **task-priority-analysis 保持纯读**：`parse_task_dependencies` / `compute_unblocked_tasks` / `format_report` 接口与输出格式向后兼容。
4. **ADR-014 §6 接线点语义沿用**：A=review 结论路径、B=gate 判定路径、C=loop fuse（已接 `check_release_readiness`）、D=agent phase（未实现）。本 ADR 补 A/B，保持 C，D 列作后续候选。
5. **v1/classic 宿主 no-op 保持**：无 `flow-unit-runtime.json` v2 payload 时 `process_gate_result` 不产生副作用。

---

## 2. 设计域一：入口引导可达性（REQ-104 / FIX-238）

### 2.1 目标 / 非目标 / 约束

**目标**

- 任何已初始化宿主（含无 AGENTS.md/CLAUDE.md 的宿主）执行 `/governance` 时，引导流程必须在确定时间内定位入口脚本并返回 envelope，不依赖宿主文件存在或 LLM 路径考古。
- resolve_entry 调用具备超时兜底（15s）与分类诊断（FileNotFound / 超时 / python 缺失 / Store stub），fail-closed 不静默。
- 0.54.1-era 旧引导在检测到更高版本 SKILL.md 时先升级 bootstrap 段再继续（打破鸡生蛋）。
- web-console `--install` 加超时参数化（SPG_WEB_INSTALL_TIMEOUT，默认 120s）+ 回归测试；`--governance-entry` 已非阻塞（FIX-150/d7928c1 落地，实测 verify_workflow.py:19519 "dependency install still requires explicit --install"），不做改动。

**非目标**

- 不在插件外分发独立二进制；不承诺所有平台同一路径。
- 不改变 resolve_entry.py 双 root 模型与 `detect_scenario` 语义。
- 不承诺旧宿主自动升级到最新（用户 /plugin update 授权仍是升级前提）。

**约束**

- resolve_entry.py 保持纯 stdlib（无 subprocess/网络/input）。
- 命令模板同时给出 POSIX / PowerShell 语法说明（跨平台）。
- hooks 结构不改；仅优化 find 扫描或增加缓存/限深。

### 2.2 候选方案

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A（推荐）**：命令模板平台注入 + PLUGIN_HOME 侧 vendor 引导脚本兜底 | governance*.md 模板支持平台注入变量（`$CLAUDE_PLUGIN_ROOT` 等价物 / Codex skill `file:` 路径统一解析），消除 `<plugin_home>` 占位符歧义；同时 vendor 一个最小引导脚本 `<plugin_home>/infra/bootstrap.{sh,cmd}`（**归属插件侧，随发布分发**，非宿主 .governance/）作为兜底，宿主无 AGENTS.md 时仍可定位 | 与 e2e fixture 模式一致；实测可行（Codex 上下文含 file: 路径）；确定性；脚本随版本迭代由发布链管理 | 宿主仍需一条最小引用路径（模板或文档化命令） |
| B：install-time 绝对路径投影 | 插件安装时把插件绝对路径写入宿主 CLAUDE.md/AGENTS.md | 安装后零解析歧义 | 需 marketplace/安装器侧支持，当前不可控（外部依赖） |
| C：多源运行时探测（不 vendor） | 统一 resolve_entry 的 fallback 链（env var + 常见 cache 路径 + skill file: 解析 + 交互询问），不写宿主文件 | 无宿主足迹 | 探测仍可能失败时退回 LLM 考古；交互询问破坏确定性 |

### 2.3 推荐与决策理由

**推荐 A + B 观察（A 为主，B 列为安装器支持后候选）**。与 AUDIT-142 诊断报告 §6 REQ-103 方案权衡一致（"推荐 A + C 兜底"——诊断报告的 C = 宿主内 vendor 引导脚本，即本表 A 的兜底部分）。

决策理由：

1. A 解决**确定性**：平台注入变量 + vendor 脚本把"找入口"从 LLM 推理变为命令模板执行，任何宿主（含旧版）都有可复现路径。
2. 旧宿主升级链（FIX-238.2）依赖"模板内置最低引导版本"——A 使模板自描述，升级检测不需要 `$WORKFLOW_HOME`。
3. B 不可控（外部 marketplace 能力），列为观察而非当前承诺；C 单独使用不满足 fail-closed（探测失败仍退化为考古）。

### 2.4 状态机 / 数据流（宿主引导传播链）

```text
宿主执行 /governance
  |
  +-- 新宿主（有 AGENTS.md 模板，>=0.73.0）
  |    模板注入：$CLAUDE_PLUGIN_ROOT / skill file: 路径 -> <plugin_home>
  |    （无模板时兜底：文档化命令直接调用 <plugin_home>/infra/bootstrap.{sh,cmd}）
  |    python <plugin_home>/infra/resolve_entry.py --json   <- 超时包装（15s）
  |      成功 -> envelope（host_root / plugin_home / scenario_hint）
  |      超时/缺失 -> 分类诊断输出（FileNotFound / timeout / python-missing / store-stub），STOP fail-closed
  |    按 scenario_hint 分发（A..F），沿用现有决策树
  |
  +-- 旧宿主（0.54.1-era CLAUDE.md，$WORKFLOW_HOME 解析）
  |    模板内置最低引导版本检测（FIX-238.2；陈旧标记 = CLAUDE.md 引导段 @bootstrap-version 头
  |       < SKILL frontmatter active_version，P3-3 定义）
  |      标陈旧且更高版本 SKILL.md 已安装 -> 先升级 bootstrap 段（写回 CLAUDE.md 模板），再继续
  |      未检测到更高版本 -> 输出确定性错误 + /plugin update 指引（不无限 fallback）
  |    进入新宿主路径
  |
  +-- web-console（--governance-entry，FIX-238.4）
        --governance-entry 保持非阻塞（FIX-150 已落地，不改）
        --install 加 SPG_WEB_INSTALL_TIMEOUT 超时（默认 120s）+ 回归测试
        端口被占 fail-closed 提示换端口
```

### 2.5 风险与回滚

| 风险 | 缓解 | 回滚 |
|------|------|------|
| 跨平台命令注入差异（POSIX/PowerShell 变量语法） | 模板同时给出两平台显式语法说明；e2e fixture 双平台验证 | 回退模板占位符为显式 `<plugin_home>` 说明（现状），无产品逻辑依赖 |
| 旧宿主误升级（版本检测误判） | 版本比较 fail-closed（无法确定新版本 -> 不升级，输出指引） | 升级仅写 bootstrap 段，其余内容不变；可手动还原 CLAUDE.md |
| 超时兜底误杀慢环境（网络盘/冷启动 >15s） | 超时值参数化（环境变量，默认 15s）；超时后输出诊断而非静默 | 提高超时值即可，无状态变更 |
| hooks find 扫描仍慢（感知"卡住"残留） | find 加深度限制/结果缓存；hook 路径探测顺序优化（env var -> repo 本地 -> cache） | 保持旧 find 逻辑为 fallback |
| web-console --install 超时参数化回归（P2-1） | SPG_WEB_INSTALL_TIMEOUT（默认 120s）超时后输出诊断不挂起；回归测试覆盖超时与正常两路径 | 移除超时包装恢复 FIX-150 现状 |

---

## 3. 设计域二：Loop 双环接线（REQ-105 / FIX-236）

### 3.1 目标 / 非目标 / 约束

**目标**

- `process_gate_result` 生产调用点 ≥2（A：review 结论记录路径；B：gate-engine 判定路径），可被 check 枚举验证。
- NEEDS_CHANGE 记录后，复审触发可机器验证——Check 30 从"验已记录格式"升级为"验复审时效"（R{n+1} 存在且日期晚于 R{n}）。
- 任务完成 / loop_exit 事件消费路径产出 next-unit 候选（调用 task-priority-analysis 或等价），推荐出现在交互边界。
- 状态机写失败不得阻断 review 记录（best-effort + 降级标记）。
- **fuse fail-open 边界显式化（P2-2）**：无 `flow-unit-runtime.json` v2 payload 文件 → fail-open（v1/classic no-op 保持，ADR-014 §6.5 不变）；**文件存在但损坏（JSON 解析失败/结构非法）→ fail-closed**（该单元按 blocked 处理 + 明确诊断 + 测试覆盖），不得静默降级为 fail-open。

**非目标**

- 不实现 escalation 4 选项 UI；不重写 PARO 状态机；不改 v1 宿主行为（no-op 保持）。
- 不实现 Wiring D（agent phase 深层插桩）——与 ADR-014 §6.4 一致列为低优先级，0.73.0 不承诺。
- 机器不代替 Coordinator spawn 复审 agent——系统强制"记录结论时生成复审指令 + Check 检测未复审即 FAIL"，实际 spawn 仍由 Coordinator 执行。

**约束**

- 接线为薄调用（≤10 行/点，ADR-014 §6 原则）；不在 verify_workflow.py 新增业务逻辑。
- review→unit/gate 映射为数据（registry 侧 map），非 verify_workflow.py 硬编码。
- Check 30 升级不得误伤既有历史豁免（DEC-138 语义保持）。
- **Wiring A 挂接锚点（P1-1）**：全仓无 review 结论机器写入器（rg 实证：无 review-record/evidence-append 命令；review-*.md 与 evidence-log 行由 agent 手工写盘）。FIX-236.1 MUST 新建薄 CLI `review-record`（verify_workflow.py 薄入口，逻辑委托 infra 模块）作为**唯一机器化 review 结论持久化路径**，Wiring A 挂接在该 CLI 内——不依赖任何手工写盘路径。

### 3.2 候选方案

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A+B（推荐）**：新建 `review-record` 薄 CLI（唯一机器化 review 结论持久化路径）+ auto_judge_gate 判定路径双薄接线 | A：`review-record` CLI（verify_workflow.py 薄入口 + infra/review_record.py 逻辑）写入 review-{role}-{id}-R{n}.md 与 evidence 行后置 `process_gate_result(unit_id, gate_id, mapped_result, evidence_ref, actor)`（P1-1 锚点）；B：`auto_judge_gate` 判定渲染后置同款薄调用。新增 `loop_exit` 事件消费桥（见 3.4） | 改动最小（每点 ≤10 行）；机器化单一写入路径消除手工写盘歧义；覆盖人工 review 与自动化 gate 双源；与诊断报告推荐一致 | 需新增 registry 映射数据 + review-record CLI + 调用点 check（AST/导入图，排除 docstring/注释） |
| C：hook 层强制触发 | git hooks 在 review 记录 commit 时调用 process_gate_result | 系统级强制 | 侵入 git 流程；review 结论不一定伴随 commit（跨 session/子 agent）；时序不可控 |
| D：仅扩展 C（fuse block） | 仅把 fuse block 扩展为记录 review 结论 | 改动最小 | 覆盖不到 A/B 语义；review 结论仍不驱动 back-edge |

### 3.3 推荐与决策理由（ADR-014 §6 对齐）

**推荐 A+B**，与 ADR-014 §6.1/6.2 语义逐字一致，且是 AUDIT-142 诊断报告 §7 FIX-236 的既定拆解（236.1 Wiring A + 236.2 Wiring B）。

四接线点对齐表：

| 接线点 | ADR-014 §6 语义 | 0.73.0 状态 | 本 ADR 动作 |
|--------|----------------|------------|-------------|
| A | review 结论 -> process_gate_result | 未实现（生产调用点 0） | **实现**（FIX-236.1，薄调用） |
| B | gate-engine 判定 -> process_gate_result | 未实现 | **实现**（FIX-236.2，薄调用） |
| C | loop fuse -> check_release_readiness | 已接（verify_workflow.py:6688-6711） | 保持不动 |
| D | agent phase transitions | 未实现（低优先级） | 不承诺，列为 0.73.0 后候选 |

决策理由：

1. A/B 双源覆盖（人工 review + 自动化 gate）满足 REQ-105 验收"生产调用点 ≥2"。
2. 薄调用保持 loop_paro_engine / loop_gate_processor 纯函数性（ADR-014 原则），回归风险最小。
3. C 方案（hook 强制）引入 git 时序耦合；D 方案语义不全。两者均排除。

### 3.4 状态机 / 数据流（含 loop_exit -> next-unit 推荐桥）

```text
[Wiring A] review 结论（APPROVED / NEEDS_CHANGE / BLOCKED）
  -> 唯一机器化持久化路径：review-record CLI（FIX-236.1，P1-1 锚点）
       review-record --task <id> --round <n> --result <结论> --report <path> [--unit <unit_id> --gate <gate_id>]
       a. 写入 review-{id}-R{n}.md + evidence-log 行（机器写入，格式 Check 21/30 可验）
       b. 后置薄调用 process_gate_result(unit_id, gate_id, mapped_result, evidence_ref, actor)
       |-- 结果 passed -> decision=exit -> loop_exit 事件
       |-- 结果 failed (NEEDS_CHANGE) -> decision=iterate -> back_edge 事件（loop_count+1）
       |     复审指令生成：记录 R{n} 时输出"复审必达"结构化字段（next_round=R{n+1}）
       |       （next_round=R{n+1}，注入前轮 report 路径）-> 供 Coordinator spawn 同一 Reviewer
       +-- 结果 blocked -> decision=escalate -> unit_blocked 事件
  -> best-effort：process_gate_result 失败（CAS conflict / 文件锁）
       -> 记录降级标记，不阻断 review 落盘

[Wiring B] auto_judge_gate(gate_id) 判定渲染
  -> 薄调用 process_gate_result（同 A，actor="gate-engine"）

[loop_exit -> next-unit 推荐桥]（FIX-236.3，新模块 loop_exit_bridge.py）
  loop_exit 事件（unit 通过 gate 退出当前 tier）
    -> 消费桥调用 task-priority-analysis 纯读（compute_unblocked_tasks）
    -> 产出 next-unit 候选 top-N + 推荐理由（依赖解除说明）
    -> 写入候选 JSON（evidence-log 调用快照 / 交互边界读取点）
    -> 读取端（P3-5）：新增 `next-candidates` 薄 CLI（verify_workflow.py），
       governance-status / Scenario F / 交互边界（AskUserQuestion 候选）统一消费该 CLI 输出

[Check 30 升级]（FIX-236.4）
  现有 V1~V5 格式校验保留；新增 V6 复审时效校验（规格四项，P1-2）：
    V6a 触发对象：晚于 FIX174_NORMALIZATION_DATE（2026-07-18，DEC-138）的
         NEEDS_CHANGE 终态轮（复用既有豁免边界；豁免随链——终态轮日期决定整链是否触发，
         与 V1/V5 的 rounds[max_round].date 谓词一致）
    V6b 熔断豁免：R >= MAX_ROUNDS(3) 的链与 V3 fuse 求交豁免——R3 NEEDS_CHANGE 后
         合法 escalation（T2 熔断转 BLOCKED）不得被判违约（无 R4 不是违约）
    V6c 窗口语义：参数化时长 SPG_REVIEW_REVISIT_WINDOW（默认 24h）为主判定；
         "下一 commit"仅作可选附加触发，数据来源 = check-governance 运行时经 git 读取
         最近 commit 时间（无 git 上下文时仅以时长窗口判定，不产生假阳性）
    V6d 普通行判定：无"复审必达"结构化字段的行以 evidence 行日期 + 窗口为准
  新增调用点 check（P1-1）：枚举 process_gate_result 生产调用点 >=2，
    用 AST/导入图分析（rg 文本匹配会命中 loop_gate_processor.py:69 docstring 示例——
    该示例须作为负样本测试，断言 docstring/注释/字符串字面量不计数，防 AUDIT-133/140 同款假阳性）
  新增负样本测试（P1-2）：(1) 跨 session 复审——R+1 在 48h 后（>24h 窗口）但复审已发生，
    链闭合 → 不 FAIL（V6 只惩罚"无复审"，不惩罚"慢复审"）；
    (2) fuse 熔断链——R3 NEEDS_CHANGE 后转 BLOCKED + escalation 记录 → 不 FAIL（V6b）

[fuse fail-open/fail-closed 边界]（P2-2）
  无 flow-unit-runtime.json（v2）文件 -> fail-open（v1/classic no-op）
  文件存在但损坏（JSON 解析失败/结构非法）-> fail-closed（blocked + 诊断 + 测试）
```

### 3.5 风险与回滚

| 风险 | 缓解 | 回滚 |
|------|------|------|
| 状态机写失败影响 review 记录 | best-effort + 失败降级标记；事件日志与 review 记录解耦（state-first/event-second 已定）；**由 Check 30/review-closure 测试套件验证降级标记不破坏链闭合（P2-3）** | 移除薄调用行即可，review 记录路径恢复原状 |
| 接线点回归（新版本删掉调用） | FIX-236.4 新 check（AST/导入图）断言生产调用点 ≥2，回归即 FAIL；docstring 负样本随 check 套件验证 | 恢复调用行 |
| Check 30 V6 误伤正常跨 session 复审 | V6c 窗口参数化（默认 24h）；V6a 只对晚于 FIX174 边界的终态轮判定；**跨 session 负样本（R+1 48h 后已闭合 → 不 FAIL）入 review-closure 套件（P1-2/P2-3）** | 关闭 V6 或调大窗口 |
| fuse 损坏文件被误当 fail-open | P2-2 fail-closed 显式声明 + 损坏 payload 负样本测试（JSON 解析失败/结构非法 → blocked 诊断） | 恢复 fail-open 仅限"文件不存在" |
| review->unit/gate 映射缺失（新 review skill 未登记） | 映射为 registry 数据；缺失时跳过接线并 WARN（不阻断记录），review-record 仍正常落盘 | 补映射数据 |
| 推荐桥输出与真实依赖状态漂移 | 数据债治理（域三 FIX-237.1，含第三类非可执行状态过滤 P1-3）前置；推荐桥对 cycle 容错（警告非阻断） | 关闭推荐桥消费点 |

---

## 4. 设计域三：任务规划闭环（REQ-106 / FIX-237）

### 4.1 目标 / 非目标 / 约束

**目标**

- 新事项进入（变更控制）与任务完成后的下一步推荐 MUST 经过 task-priority-analysis；交互边界呈现依赖排序后的候选（含推荐理由）。
- 变更控制标准路径从 docstring 升级为可执行（triage 命令 MUST 调用依赖分析；无分析记录时入账被拦截）。
- 数据债清零：task-priority-analysis 输出 0 cycle；已发布任务状态与 git tag 一致（漂移检测 0）。
- evidence-log 出现 task-priority-analysis 调用记录（命令输出快照）。

**非目标**

- 不自动执行任务（推荐后仍需用户/Coordinator 决策）；不做跨版本自动重排。
- 不改 P0/P1/P2 判定规则本身。

**约束**

- tool 保持纯读；输出格式向后兼容。
- 快速通道（.governance/ 治理记录范畴）保留，但产品代码新任务 MUST 走标准路径。

### 4.2 候选方案

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **C1（推荐）**：数据债先行 + 工具增强 + 强制集成三阶段 | 237.1 修三类数据债（10 条环 + 状态漂移回填 + **非可执行状态过滤，P1-3**）；237.2 工具过滤已发布任务 + cycle 容错 + 非可执行状态排除；237.3~237.5 入口/变更控制/交互边界强制集成 + 证据化 | 根治不可信问题；推荐质量有保证；与诊断报告推荐一致（数据修复 + 工具过滤双管） | 工作量最大；237.1 需历史数据处置授权 |
| C2：仅工具侧过滤（不修数据） | 只加已发布版本过滤 + cycle 容错 | 快速 | 治标；环仍在，工具输出仍可能误导跨版本依赖判断；非可执行状态行仍混入 unblocked |
| C3：仅强制调用（不修数据） | 直接在所有入口强制调用 tool | 最小改动 | 数据污染（含非可执行状态行）-> 错误推荐 -> Coordinator 再次不信任（恶性循环不破） |

### 4.3 推荐与决策理由

**推荐 C1**（数据债前置 237.1 可独立先行），与 AUDIT-142 诊断报告 §6 REQ-105 方案权衡一致（"推荐 A（数据修复）+ B（工具过滤）双管"）。

决策理由：

1. R4 已实证：工具输出含 10 环 + 漂移任务 -> 推荐列表混入已完成项 -> Coordinator 不信任。**不修数据直接强制 = 把错误推荐制度化**（C3 排除）。
2. C2 单独使用无法支撑 REQ-106 验收"tool 输出 0 cycle"。
3. 237.1（数据债）是纯治理记录处置，可与本 ADR 评审并行先行，缩短 0.73.0 关键路径。

### 4.4 状态机 / 数据流（变更控制 triage 强制点）

```text
[变更控制 triage 强制点]（FIX-237.4）
新事项提出（产品代码）
  -> triage 命令（governance-update 扩展或新 change-triage 命令）MUST 执行：
       a. task-priority-analysis（依赖/阻塞检查 + cycle 检测）
       b. 优先级判定（P0/P1/P2，结合 in-flight + 版本链）
       c. 冲突检查（与 in-flight 任务修改相同文件）
       d. 版本适配（目标版本）
  -> 产出 triage 记录（含 tool 输出快照）-> 无分析记录时创建 task 被拦截（CLI fail-closed + Check 扩展）
  -> 快速通道仅限 .governance/ 治理记录（FIX-228 边界保持）

[任务完成 -> 下一步推荐]（FIX-237.3 + 237.5，M7.4 step 6 升级）
任务完成
  -> 依赖分析 MUST 运行 task-priority-analysis（删除 behavior-protocol.md:553 "如果存在"软条件）
  -> 推荐候选 = tool 输出 top-N + 理由（依赖解除说明）
  -> evidence-log 记录调用快照（命令输出 JSON）
  -> AskUserQuestion 候选呈现（含推荐项 + "自主执行推荐项" + "暂停"）

[协议修正]（FIX-237 附带）
  interaction-boundary.md:187 决策表：任务排序 -> "运行 task-priority-analysis，按依赖排序候选"
  （消除 :187 与 :217 的矛盾）
  behavior-protocol.md:553：软条件 -> MUST 运行

[数据债治理]（FIX-237.1，前置；三类，P1-3）
  类 1 依赖环：10 条环（FIX-199<->FIX-201、FIX-217<->FIX-218、FIX-220<->REL-063 等
    0.66.1 事故链历史行）-> 与 Check 30 历史豁免同批处置（DEC-138 语义沿用；历史行豁免需 DEC 级授权）
  类 2 状态漂移：FIX-225~229/FEAT-006~009/VAL-008 已发布仍 ⏳
    -> 按 git tag 回填 ✅（漂移检测 0 验收）
  类 3 非可执行状态混入 unblocked（R0 实测）：SYSGAP-046 🚧、FIX-197 ⏸ SPLIT_TO、
    REL-058 ⛔ BLOCKED、AUDIT-136 ⛔ BLOCKED_REVIEW_FUSE——依赖满足即判 unblocked，
    状态列不参与过滤，且不属于已发布版本/环/漂移类
    -> unblocked/next 候选 MUST 排除非可执行状态（⛔/⏸/🚧/✅/漂移⏳）；
       compute_unblocked_tasks 增加状态过滤谓词 + 工具测试：上述 4 任务不入 unblocked（FIX-237.2）
```

### 4.5 风险与回滚

| 风险 | 缓解 | 回滚 |
|------|------|------|
| 数据债未清时误推 | 237.1 先行（0 cycle 验收）+ 237.2 过滤已发布任务 + cycle 容错（警告非 ERROR） | 关闭推荐桥消费点；tool 输出向后兼容 |
| Coordinator 绕过强制集成 | 237.5 证据化（调用快照必落 evidence-log）+ Check 扩展（无记录 FAIL） | 保留 prose 兜底教育层（诊断报告 §8 反面证据 3） |
| triage 拦截误伤合法任务（映射缺失） | 拦截仅针对"产品代码新任务无分析记录"；未知依赖 ID fail-closed（FIX-171 保守默认） | 放宽为 WARN 需 DEC 授权 |
| 状态漂移回填误改（git tag 与任务映射偏差） | 回填以 git tag + 版本投影为唯一事实源；逐任务核对后写 | 回填为治理记录，git 历史可还原 |
| 历史环处置影响 Check 30 豁免语义 | 环修复与 Check 30 历史豁免同批、同 DEC 授权；验证 check-loop-runtime-claims PASS | 撤销豁免行 |

---

## 5. 跨域依赖与模块边界（无循环依赖）

```text
commands/governance*.md（域一：模板注入）-> resolve_entry.py（不变，纯 stdlib）
verify_workflow.py（薄接线，域二）-> loop_gate_processor.process_gate_result（不变）
loop_exit_bridge.py（域二新增，FIX-236.3）-> task_priority.py（域三，纯读）
change-triage 命令（域三新增，FIX-237.4）-> task_priority.py（纯读）
task_priority.py（纯读）-> 无新依赖
registry（loop_gate_semantics / review->gate map）-> 数据驱动接线
```

- **无循环依赖**：新增模块只单向依赖既有纯函数模块；verify_workflow.py 只做薄入口委托。
- 新增产品文件候选：`infra/loop_exit_bridge.py`（推荐桥）、registry 侧 review->gate 映射数据（可并入现有 loop registry）、triage 命令（可并入 verify_workflow.py 薄入口或独立模块）。最终文件归属由 Developer 按 manifest 域拆分惯例决定（manifest.json 登记）。

## 6. 蓝军挑战（≥3）

| # | 挑战 | 回应/缓解 |
|---|------|----------|
| BT-1 | 如果 process_gate_result 接线后状态机写失败（CAS conflict / 文件锁），review 结论被吞掉怎么办？ | 接线为 best-effort：失败降级标记 + review 记录独立落盘（不依赖状态机成功）；Check 只验已记录链；事件日志 state-first/event-second 已定 |
| BT-2 | 如果旧宿主（0.54.1）连"更高版本 SKILL.md"都探测不到（插件未更新），升级链仍失败？ | fail-closed 输出确定性错误 + /plugin update 指引，不无限 fallback；REQ-104 验收只承诺"确定时间内产出确定性诊断"，不承诺自动升级 |
| BT-3 | 如果 task-priority-analysis 数据债未清就强制集成，会不会把错误推荐制度化？ | 237.1 数据债先行是硬前置（0 cycle + 漂移 0 验收后才开强制）；237.2 过滤已发布任务；cycle 容错为警告非 ERROR |
| BT-4 | Check 30 V6 时效窗口会不会误伤跨 session 的正常复审节奏（比如 R+1 在 3 天后）？ | 窗口参数化（默认 24h/下一 commit 二选一触发）；只对 NEEDS_CHANGE 终态轮判定；窗口可调，误伤即调大 |
| BT-5 | 新接线点被后续版本无意删除（回归），如何保证不退回"调用点 0"？ | FIX-236.4 新增 check 断言生产调用点 ≥2（rg/导入图可验证），回归即 FAIL；与 Check 31 identity attestation 同机制 |
| BT-6 | 模板平台注入在无 shell 环境（纯 GUI 宿主）失效？ | vendor 引导脚本兜底（.sh/.cmd 双平台）；脚本再失效时 resolve_entry 单文件可直接调用（文档化），不依赖模板 |

## 7. 分阶段实施建议（与 0.73.0 版本规划衔接）

| 阶段 | 内容 | 依赖 | 可独立先行 |
|------|------|------|-----------|
| Phase 0 | **FIX-237.1 数据债治理**：三类数据债（10 条环处置（DEC 授权）+ 状态漂移回填 + 非可执行状态过滤 P1-3）-> tool 输出 0 cycle / unblocked 无 ⛔⏸🚧 行 | 无（纯治理记录） | 可与本 ADR 评审并行 |
| Phase 1 | **前置门（P3-4）**：Requirement Review 正式落档（REQ-104/105/106 review 文件存在）后启动；**FIX-236.1/236.2 Wiring A+B**：新建 review-record 薄 CLI（唯一 review 结论持久化路径）+ registry review->gate 映射 + best-effort 降级 | ADR-017 通过 + Requirement Review 落档 | |
| Phase 2 | **FIX-236.3 loop_exit -> next-unit 推荐桥**（新模块 loop_exit_bridge.py）+ **next-candidates 薄 CLI（P3-5）** + FIX-236.4 check（AST/导入图调用点 ≥2 + V6 时效 + 负样本） | Phase 1 + 237.2 | |
| Phase 3 | **FIX-237.2~237.5**：工具增强（过滤+容错+非可执行状态排除）、入口集成、triage 命令、交互边界契约 + 协议修正（interaction-boundary:187 / behavior-protocol:553） | Phase 0 + 2 | |
| Phase 4 | **FIX-238.1~238.4**：模板平台注入 + PLUGIN_HOME 侧 bootstrap 脚本、旧宿主升级链（@bootstrap-version 陈旧标记）、resolve_entry 超时兜底、web-console --install 超时参数化 | 无强依赖 | 可与 Phase 1~3 并行 |
| Phase 5 | **REL-066 发布 0.73.0**：版本投影 + CHANGELOG + release docs + manifest + 发布门禁 | 全部 Phase | |

**0.73.0 范围边界**：Wiring D（agent phase 深层插桩）不承诺；escalation UI 不实现；v1 宿主行为不变；不自动执行任务。

## 8. 非功能需求覆盖

| NFR | 设计措施 |
|-----|---------|
| 性能 | resolve_entry 保持 <1s（纯 stdlib 不变）；接线点 ≤10 行无新逻辑；hooks find 加深度限制/缓存；推荐桥为纯读 O(tasks) |
| 安全 | fail-closed 分类诊断（不静默）；resolve_entry 双 root 不变；无凭证/网络新增 |
| 可维护性 | 薄调用 + 纯函数保留；新模块职责单一（loop_exit_bridge 只做推荐桥；triage 只做强制入口）；registry 数据驱动 |
| 可扩展性 | review->gate 映射为数据，新增 review skill 自动路由；时效窗口参数化；超时值参数化 |
| 可验证性 | FIX-236.4 调用点 check + V6 时效 check；237.5 evidence 快照；tool 输出向后兼容测试 |

## 9. 影响范围

- **产品代码（候选）**：verify_workflow.py（薄接线 + triage 入口 + `review-record` CLI + `next-candidates` CLI）、新模块 `loop_exit_bridge.py` 与 `infra/review_record.py`、registry（review->gate 映射）、commands/governance*.md（模板注入）+ `<plugin_home>/infra/bootstrap.{sh,cmd}`（P3-2）、hooks（find 优化）、references/behavior-protocol.md 与 interaction-boundary.md（协议修正）、core/manifest.json（新文件登记）。
- **不修改**：resolve_entry.py 本体逻辑（DEC-096）、loop_paro_engine.py / loop_engine.py 纯函数、task_priority.py 解析逻辑、v1 payload 行为。
- **治理记录**：plan-tracker（REQ-104/105/106 + FIX-236/237/238 状态）、evidence-log（接线验证 + triage 快照）、decision-log（本 ADR + 数据债处置 DEC）。
- **用户影响**：/governance 引导确定性提升；review 复审与下一步推荐可机器验证；交互边界候选有依赖依据。迁移指南随 0.73.0 发布文档。

## 10. 后续动作

1. **Design Review R1**：独立 Reviewer 复审本 ADR（R0 三项 P1 已修订：P1-1 review-record 锚点 + AST 调用点 check + docstring 负样本；P1-2 V6 四项规格 + 双负样本；P1-3 第三类数据债 + 工具测试；P2×3/P3×6 已全部并入）。
2. **决策点（返回 Coordinator/用户）**：
   - 历史依赖环数据债（0.66.1 事故链）处置授权（与 Check 30 历史豁免同批，DEC 级）
   - 0.73.0 范围确认（Phase 0~5 全量 vs 裁剪）
   - Check 30 V6 时效窗口默认值（24h/下一 commit）
   - triage 拦截的 fail-closed 强度（产品代码无分析记录时阻断入账）
   - SPG_WEB_INSTALL_TIMEOUT / SPG_REVIEW_REVISIT_WINDOW 默认值确认
3. **proposed decision-log entry**：ADR-017 决策记录（含可逆性标注——本 ADR 接线为可逆（薄调用可移除）；数据债回填为不可逆（但 git 可还原））。
4. **Requirement Review 落档后对照**：D1~D8 与正式结论比对，如有出入修订本 ADR（落档为 Phase 1 前置门，P3-4）。
