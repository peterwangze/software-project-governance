# 关键行为契约执行细则（FIX-450）

本文件承接入口 SKILL 的按需细则，约束效力不变。入口保留触发器和安全边界；任一触发出现，Coordinator MUST 在执行对应动作前读取相应 C1–C11 / 执法 / 健康摘要节，不能把按需读取当作可选或豁免。原规则逐字承接如下；入口条目计数由十条校正为实际十一条，安全语义不变。

## 关键行为契约完整规则

<a id="c1"></a>

### C1

1. **复审必达（M7.4 step 4.6，T1-T4）**：收到 Reviewer 审查结论后 MUST 立即判定并执行——结论含 NEEDS_CHANGE 且 round<3（触发器 T1）→ spawn 同一 Reviewer 复审（round+1，prompt 注入前轮 review 报告路径为强制读取项），不得跳过、不得询问；round≥3 仍 NEEDS_CHANGE（触发器 T2）→ BLOCKED + escalation AskUserQuestion；APPROVED 或带 `unresolved_blockers=0` 的 APPROVED_WITH_NOTES 为唯一通过终态；BLOCKED → escalation。**delta 注入面（FEAT-091）**：R2+ 复审注入面 = 修复 diff + 前轮报告路径 + 验收标准，不默认全量重审；结构性变更时 Reviewer 可要求全量（M7.4 T1）。

<a id="c2"></a>

### C2

2. **完成必推荐（M7.4 step 6，FIX-223/237.5 增强；FEAT-072/DEC-266 三要素推荐卡）**：任务标记已完成→MUST 运行 `task-priority-analysis`（fail-closed 不跳过），快照记入 evidence-log→按依赖推荐 1~3 项；AskUserQuestion 前 MUST 给正文三要素推荐卡（服务目标/解决问题/方案要点，附可追溯依赖理由）；依据缺失 MUST 明示、不得编造，影响执行则先澄清；按 DEC-143 用对应短选项确认，MUST NOT 默认自主执行；空推荐→结构化空原因；MUST NOT 直接结束会话。

<a id="c3"></a>

### C3

3. **选项必带依据（interaction-boundary.md 任务排序行 + 反打断违规表）**：凡向用户呈现"接下来做什么"类选项，选项 MUST 可追溯到依赖分析输出（排序候选 + 每项依赖状态理由），禁止机械枚举未完成事项。

<a id="c4"></a>

### C4

4. **真实环境必防护（M7.7 R1/R4/R5，FIX-271/274）**：任何涉及用户真实环境（`$HOME` 下配置目录、`$DSH_HOME`、仓库外任意路径）的测试/验收/安装操作，执行前 MUST 满足三选一并留痕——(a) 隔离环境（环境变量重定向至临时目录）/(b) 完整备份 + 操作后一致性校验/(c) 用户逐项授权（ask_user_question）；三者皆缺 = 禁止执行，无豁免。真实环境每条命令 MUST 逐条上报（角色 agent 结构化返回，Coordinator 于收到当下机写 evidence 行；无上报或收到未机写均按违规处理；预授权 incidents log 追加例外）。验收措辞 MUST 用「隔离环境安装冒烟（环境变量重定向至临时目录）通过」——无限定语的「真实安装/真实环境」= 违规措辞。

<a id="c5"></a>

### C5

5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源（用户点名、活性缺陷、机器信号三选一标注），不标即违规；同优先级内 user-named 未闭合时 machine-signal 不得排前（DEC-286(7)）。

<a id="c6"></a>

### C6

6. **发现即闭环**：问题在触发点当场闭环（FAIL 即修/发现即改/风险即决/发布即结账）；「登记待以后」=违规；付不起闭环成本的动作不开始（DEC-286）。

<a id="c7"></a>

### C7

7. **并行优先派发（M7.8.1，FEAT-090）**：独立无依赖任务 MUST 单步批量 spawn；等待子代理期间 Start-Sleep/轮询 = 违规；等待期有就绪任务 MUST 继续派发。

<a id="c8"></a>

### C8

8. **健康检查事件化（M7.8.2，FEAT-090）**：全量深检仅三类触发——会话首检/推进类动作前/异常信号；逐轮例行全量 = 违规。

<a id="c9"></a>

### C9

9. **热路径单源（M7.8.3，FEAT-090，write-guard 同级）**：热数据唯一读取路径 governance-bootstrap --format json；直读 plan-tracker/execution-packets/evidence-log = 违规。

<a id="c10"></a>

### C10

10. **goal 预算必收口（FEAT-097，RPG §3.1/§3.8 意图断层修复）**：harness goal 续跑的每一轮经 `goal-bridge --action record` 采集预算信号——四维权（轮次/token/墙钟/成本）任一入危险区即收口（RUNNING→DRAINING→CHECKPOINTED；70% 轮量为必要不充分：仅危险区触发收口，warning 仅披露）；DRAINING 只允许在途任务收尾（`--in-flight`）；CHECKPOINTED MUST AskUserQuestion 带范围裁决选项（缩范围/扩预算/继续/终止）——**禁静默续跑**；BLOCKED 后未授权续跑/执行被拒并机器留痕（恢复仅经 `--action ruling --decision reduce-scope/extend-budget --authorized-by <用户>`）；checkpoint 工件（`.governance/goal-bridge/<goal_id>.json`）携账本/义务/修订/规则版本/预算消耗跨会话恢复（幂等；规则版本变化=响亮披露不静默——DEC-330 禁 mid-session 热升级）；映射表与危险区阈值为配置面数据（`goal-bridge --action thresholds/mapping --text` 可 grep；调整不动状态机）；`GOVERNANCE_GOAL_BRIDGE=off` 回退既有 goal 行为。

<a id="c11"></a>

### C11

11. **六边界动作级执法（FEAT-095，DEC-330「检查必须影响执行权限」）**：Coordinator 在六边界动作（派发执行/派发审查/接受完成/合并/发布/goal 续跑）前 MUST 过执法判定——CLI 面 `verify_workflow.py enforcement-check --facts <边界动作 facts JSON>`（出口码 0=放行 / 2=硬阻断（含 fail-closed）/ 3=限流 / 4=提示重建），非 0 即 MUST 停下按 remedy 解除后重试，不得绕行；完整分层语义与降级披露见下方「动作级执法（FEAT-095）」段。

<a id="enforcement"></a>

### 动作级执法（FEAT-095）——六边界分层阻断（protocol 级契约；CLI 面 `enforcement-check` 强制）

> DEC-330 arch 联合裁定「检查必须影响执行权限否则 advisory 无效」。本段是六边界执法的**协议级落地面**（Coordinator 侧 MUST 检查与阻断语义）；CLI 级落地面为 `infra/enforcement.py` + `verify_workflow.py enforcement-check`（出口码三态可区分），两面对齐由守护测试 `test_enforcement_skill_protocol_face_matches_cli_face` 机守。**降级披露（M-0 调研结论）**：六平台均无已接线宿主级拦截（`docs/research/feat-095-harness-enforcement-capability-2026-10-10.md` §5-§7 U1-U7）——本执法面 = 协议级 + CLI 级，**不做宿主级拦截能力声明**；绕过面（不调用 CLI 直接动作）由本段 MUST 纪律补位，RPG §3.4 实证即此形态衰减来源。

**六边界 × 三层策略表**（策略表与执行器分离——新增边界改表 `enforcement.py STRATEGY` 不动执行器；`--print-strategy` 可 grep）：

| 边界 | 硬阻断（exit 2） | 限流升级（exit 3） | 提示重建（exit 4） |
|---|---|---|---|
| `dispatch-execute` 派发执行 | 四类零漏放（见下） | 审查债预算超阈 | 冷面过期提示 |
| `dispatch-review` 派发审查 | 四类零漏放（修订错配的复审派发同样被拒——白名单不豁免错配） | — | 冷面过期提示 |
| `accept-completion` 接受完成 | 四类零漏放 | —（无关任务不冻结——scoped 非全局） | 冷面过期提示 |
| `merge` 合并 commit/组装 | 四类零漏放（**WIP checkpoint 豁免一切：`wip_checkpoint=true` 始终放行——commit 前不设卡**） | — | 冷面过期提示 |
| `release` 发布 tag/push | 四类零漏放 | — | 冷面过期提示 |
| `goal-resume` goal 续跑 | 四类零漏放 | 审查债预算超阈（21 轮静默续跑的执法补位） | 冷面过期提示 |

**四类硬阻断（零漏放）**：`revision-mismatch` 修订错配（派发目标修订 ≠ 治理期望修订）/ `unauthorized-write` 未授权写入（actor 不在 write 目标授权面）/ `duplicate-identity` 重复身份（actor 身份已 active）/ `unresolved-blocking-review` 相关阻塞复审未闭合（该 task 有未闭合阻塞审查——仅 `fix`/`re-review`/`forensics` 白名单通道豁免本规则，豁免是策略表数据 `allowlist_exempt`；白名单**不**豁免其余三类）。

**审查债预算（限流层，reason_code=`review-debt-budget-exceeded`）**：`Σ min(severity,5) × min(age_days,30)`（未闭合义务按严重性×年龄），默认阈 100（表数据）；超阈 → 新工作准入边界（dispatch-execute / goal-resume）限流（exit 3），白名单通道不受冻。**冷面提示（第 3 层）**：gate/总览/TPA/风险 touch 时效超 7 天 → 非阻断提示重建（exit 4，动作仍放行）。

**执法语义铁边界**：①scoped 语义（DEC-357）：硬阻断与未闭合复审按任务/通道 scoped；审查债预算是**全局新工作准入限流**（仅 dispatch-execute/goal-resume 两 admission 面），修复/复审/取证白名单通道与用户裁定额度逃生门保留；②commit 前不设卡（WIP checkpoint 始终放行）；③不改各 Check 判定语义（执法只消费检查输出 facts 投影）；④fail-closed（执法器自身异常/未知边界/非法开关值 → 保守阻断 exit 2 并披露，绝不静默放行）；⑤零漂移开关 `GOVERNANCE_ENFORCEMENT=off` → advisory 基线（一切放行、零记录、零副作用）；⑥每次判定留机器可读记录（`<record-dir>/enforcement-log.jsonl`，grep 锚点 `ENFORCEMENT-ACTION`，含 reason 与解除路径 remedy）。

**Coordinator MUST 用法**：六边界动作前组装 facts JSON（boundary/action/state——修订号、channel、actor、write_paths、未闭合审查、义务账、冷面时效），运行 `python <plugin_home>/infra/verify_workflow.py enforcement-check --facts <path>`；exit 2 → 按 remedy 解除（重对齐修订/走授权写者/释放身份/闭合复审）后重试，禁止 `--facts` 造假绕行；exit 3 → 先闭合义务或经用户裁决提额；exit 4 → 重建展示面后继续（动作本身放行）。

<a id="bootstrap-health"></a>

### 每会话 bootstrap 健康摘要（REQ-145.1, A3）

本 SKILL 每会话经 persona 第一动作（加载本入口 + 运行 `resolve_entry.py --json`）**必然加载**。**执行时序（FEAT-034 首次交互前置）**：第 2 步（resolve_entry，fail-closed 不变）之后先走快路径——运行 `governance-bootstrap --format json` 获取热数据（resolve+状态+候选+migration 标志+next_actions）并**立即**呈现最小状态行 + AskUserQuestion 首次交互；健康摘要（`check-governance --summary-only --scope quick`）**后置**为用户选择后按需执行的深检——深检结果不作为首次 ask 的前置条件；`health.state="deferred"` 期间状态行健康位显示「待检查」而非绿色通过。**深检后置 ≠ 深检可选**：用户选择推进类动作（发布/版本 bump/治理写回/恢复遗留任务的实际修改）时 MUST 先补跑健康摘要与对应深检再继续——**推进类深检固定 full 面（FEAT-084/DEC-303，安全语义不回退）**：用 `check-governance --summary-only`（缺省 scope=full，全量引擎全部段）或显式 `--scope full`，quick 通过 ≠ 完整治理通过（插件产品自检/ArchGuard/loop-claim 等排除面段不在 quick 面）。后置执行时按以下契约运行健康摘要：

- 运行 `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only --scope quick`（DSH 支持 CLI；FEAT-084/DEC-303 形态 B——会话摘要默认 quick 面：FEAT-025 注册表 quick 面段执行 + 排除面段 NOT_RUN 披露，段数以注册表为准）。读取四态汇总行 `Governance: {N} issues (quick) | {p} passed / {f} failed / {nr} not-run / {c} cache-reused / {u} undetermined | run check-governance (full) for the {nr} not-run segments`——**quick N 与 full N 是两个口径，不得混读**（`(quick)` 标记与四态计数由 QR-4 机守卫强制；发布门基线/审查 census 一律按 full 口径解读）；NOT_RUN 段逐段携带注册表原因码，全部实质段未执行时 N 显示 `N=unknown` 而非 0；注册表守卫不可信时 fail-closed 自动回退 full 跑满（FIX-304 口径）。摘要**只读、只显示、不阻断**（fail-safe 到简报而非硬失败）；`--level` 详略档仅对 full 面生效，quick 输出不按 level 拆。legacy 回退（FEAT-040）：`GOVERNANCE_LEGACY_BEHAVIOR=1` 时会话摘要命令回退 `--summary-only`（无 scope，全量引擎）。按摘要驱动后续动作：
  - `Governance: [PASS]`／`0 issues (quick)`（N=0）→ 无动作，继续 bootstrap。
  - `Governance: {N} issues (quick)`（N>0，附首条 digest——FAIL 类优先，≤3 条）→ FAIL 级直达用户、WARN 记入会话上下文（M5.4b 纯通知；只读优先，不因摘要本身阻断）。
  - `Governance: unavailable` → `check-governance` 不可运行（verify_workflow.py 未定位）→ 继续 bootstrap 不阻断（fail-safe）。
  - `Governance: timed out` → 运行超时（>60s）→ 软超时取消该步，继续会话。
  - `Governance: N=unknown (quick)` / `Governance: N issues (parse degraded)` → quick 面无实质执行知识或摘要解析降级（输出格式漂移 fail-safe），不报错；需要确数时运行 full 面深检。
- **详略分档（full 面）**（`--level lightweight|standard|strict`，缺省 standard）：轻量=汇总+首个 FAIL；标准=汇总+首个 FAIL/WARN+最多 5 条明细（FAIL 优先，每条截断 130 字符）+「共 N issues，--level strict 查看全部」指引行（FIX-278 G1 top-N——消除 103 字符摘要触发 ~25KB 追查链的放大（audit-148 §2.1））；严格=汇总+全部 FAIL/WARN。三档**跑同一个** `--summary-only`，仅输出详略不同，**不按 profile 拆逻辑**。
- **bootstrap 聚合快路径（FEAT-033；FEAT-034 起为第二动作）**：会话 bootstrap 在健康摘要之前 MUST 先跑 `python skills/software-project-governance/infra/verify_workflow.py governance-bootstrap --format json`（只读聚合，≤8KB 投影：resolve envelope + 状态投影 + 候选 + migration 标志 + next_actions）以支撑首次交互前置；其 `health.state="deferred"` 表示本命令未做健康检查——健康摘要仍以后置的 `check-governance --summary-only --scope quick` 为准，deferred 期间显示「待检查」，不得把 deferred 当作已通过。


<a id="automation-levels"></a>

## 自动化能力分级声明（plugin-contract.md L114）

本工作流对「自动/看护」的承诺按 plugin-contract.md 三级划分；**禁止用笼统的「自动」一词同时指向 A 级与 C 级能力**（plugin-contract.md L114 禁令——README 和对外文档必须显式说明当前各项能力处于哪一级）：

- **A 级（Agent Protocol Automation）**：行为协议自动化——agent 按协议纪律自动执行。例如「Coordinator 接管用户交互：只在 critical triggers 触发时打断；常规执行自动推进并记录假设」（见上方「你负责」清单）= A 级。
- **B 级（CLI-Enforced Automation）**：CLI/脚本强制——`verify_workflow.py check-governance` 与 commit hooks 在命令/commit 时点强制（= B 级）。本文件「治理基础设施（自动使用）」与 `commands/governance.md`（FEAT-038 起为**路由层**：只含 Coordinator 身份/检测逻辑/决策树/六 Scenario 摘要与路由，执行规程按需 Read `commands/governance/` 下文件）「自动分类，不问用户」均属本级（事件驱动，非持续）。
- **governance-write-guard（FEAT-011 / FIX-297 / FEAT-017）= B 级检查器工件 + A 级协议触发（post-commit advisory 显示面）**：CLI 被调用即强制（结构违约 FAIL 退出码 1）；post-commit 面板接线已交付（FEAT-017——advisory 显示、非阻断，回滚=删 post-commit Step 4b 段），复跑时点仍由 `references/behavior-protocol.md` M1.2「直写后 MUST 复跑」协议纪律约束并保留为权威与回退路径；对外宣示不得写成 write-guard hook 时点强制或 C 级（B 级时点强制属 commit-msg/pre-commit 既有 hook 面）。
- **C 级（System Automation）**：后台系统自动触发、不依赖 agent 记忆——**未实现**（plugin-contract.md L102：MCP/headless runner 仅有协议样例，无可用实现）。0.76.0 通过 `check-governance --summary-only` 的会话 bootstrap 自动运行实现「会话级」自动触发（见上方「每会话 bootstrap 健康摘要」），但**不是** C 级后台 daemon。

**当前治理自动级别 = A 级 + B 级；C 级为 roadmap（未实现）**。各级别能力所处级别必须向用户显式说明（plugin-contract.md L114）；对外宣示不得把 C 级未实现说成已实现。
