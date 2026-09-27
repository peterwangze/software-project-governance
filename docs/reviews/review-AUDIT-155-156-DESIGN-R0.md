# Design Review R0 — AUDIT-155（含并行票 AUDIT-156）loop 模式线性 Gate 行为偏差根因分析双报告汇合审查

- **轮次**: R0（首轮审查）
- **日期**: 2026-09-26
- **审查人**: Design Reviewer Agent（只读审查；未修改任何审查对象、产品代码与 `.governance/` 治理记录）
- **审查对象（双报告）**:
  1. `docs/requirements/audit-155-loop-gate-bias-behavior-0.89.0.md`（303 行，Analyst 行为面）
  2. `docs/requirements/audit-155-loop-gate-bias-structure-0.89.0.md`（272 行，Architect 结构面）
- **执行依据**: `agents/design-reviewer.md` + `skills/design-review/SKILL.md` + `skills/tech-review/SKILL.md`（角色定义执行协议第 1 步三件均已加载）
- **审查结论**: **NEEDS_CHANGE**（硬门槛全部通过；存在 1 项阻塞级事实缺陷 + 3 项非阻塞缺陷，逐条见 §8。返工量小，复审预期快速收敛）

---

## 1. 结论摘要

两份报告整体质量高：事实抽查 46 处中 41 处逐字证实（含行号级精确命中），假设/事实分离纪律良好，方案完备性与 DEC-097 继承表述经原文核验成立。双报告结论互相印证、无矛盾，汇合归因（投影字段语义层为残余偏差主因候选）有充分证据支撑至结构必然性层面。

**触发 NEEDS_CHANGE 的唯一阻塞项（D-1）**：结构面蓝军挑战 RB-2 的前提「loop runtime **从未通过外部验证**」被治理记录 **DEC-133 证伪**（2026-07-26 以 VAL-008 dogfood PASS + VAL-009 双外部类型 PASS 关闭 RISK-037/RISK-042）；RB-2 所引 `loop-role-mapping.md` L5 的 NOT_MET 是 **0.66.1（2026-07-17）时点声明**，早于 DEC-133 九天。这一失实前提直接支撑对候选 B 的可行性风险画像，且「DEC-133 ↔ loop-role-mapping L5 ↔ dogfood 从未激活」三方矛盾本身就是两报告主题（治理记录间事实漂移无校验）的在案实例——披露它反而强化报告论点。该缺陷必须修复后双报告方可作为用户方案决策（A/B/C）的输入。

---

## 2. 维度 1：事实抽查（46 处；要求 ≥10，每份 ≥5）

抽查方法：read/grep/pwsh 只读实测（文件存在性、mtime、内容逐字比对、计数复现、归档记录核验）。判定：**证实** = 引用与实况一致；**部分证实** = 引用对象存在但表述/映射有偏差；**证伪** = 与治理记录或实况矛盾。

### 2.1 行为面报告（26 处）

| # | 报告引用 | 抽查方式 | 结果 |
|---|---|---|---|
| B1 | SKILL.md L90 模式确认句 canonical（`stage: {stage}, Gate {gate}: {status}`） | read L82-96 | ✅ 证实（逐字一致） |
| B2 | SKILL.md L72 bootstrap 聚合为每会话第二动作（FEAT-033/034） | read L70-75 | ✅ 证实 |
| B3 | SKILL.md L225-232 为行为契约 canonical 定义；§3 称「四条写入 persona L66-71 与 SKILL.md L225-232」 | read L222-235 + grep `机录` | ⚠️ 部分证实——该节存在且自述为 canonical 投影定义处；但现文仅 4 条（复审必达/完成必推荐/选项必带依据/真实环境必防护），**全文 grep `机录` 0 命中**；persona 实为 5 条。报告的「四条含审查结论必机录写入 SKILL.md L225-232」与「五条以 L225-232 为 canonical」均与现状不符（→ D-3） |
| B4 | SKILL.md L425-426 参考表「core/lifecycle.md → 11 阶段生命周期定义」 | read L423-428 | ✅ 证实 |
| B5 | bootstrap_aggregate.py L296 `next_gate = None`、L313-314 首个 pending 赋值、L292 注释 | read L286-320 | ✅ 证实（L313-314 逐字命中；"first pending gate id" 实际在 L291 docstring，±1 行微偏） |
| B6 | bootstrap_aggregate.py L644 `payload["gates"] = parse_gate_summary(...)` | read L640-649 | ✅ 证实 |
| B7 | bootstrap_aggregate.py L877-879 text 面 `"gates: passed %s/%s ...; next %s"` | read L872-883 | ✅ 证实（逐字） |
| B8 | bootstrap_aggregate.py L627 `project.stage` 取单一 `当前阶段` 字段 | read L620-633 | ✅ 证实 |
| B9 | bootstrap_aggregate.py L692-737 `_next_actions` 无「推进下一 Gate」动作模板 | read L692-741 | ✅ 证实（动作源 = scenario/迁移/风险逾期/健康/候选/hooks/behavior，无 Gate 模板） |
| B10 | bootstrap_aggregate.py 全文 grep `loop` 零命中 | Select-String 计数 | ✅ 证实（0 命中） |
| B11 | main-workflow/SKILL.md L74「默认顺序：1→2→3→...→11，前一阶段 Gate 通过后进入下一阶段」 | read L70-79 | ✅ 证实（逐字） |
| B12 | agent.cordis.yml.template L66-71 携带关键行为契约 | read L43-75 | ✅ 证实（L66 头 + L67-71 **五条**在位） |
| B13 | behavior-protocol.md L426 passed =「所有检查满足，进入下一阶段」 | read L418-445 | ✅ 证实（逐字） |
| B14 | behavior-protocol.md L441「Gate 未通过 → MUST NOT 声称进入下一阶段」 | read L439-445 | ✅ 证实 |
| B15 | behavior-protocol.md L435-437 profile 裁剪表（lightweight/standard/strict 均为 11-Gate 队列裁剪） | read L431-437 | ✅ 证实 |
| B16 | behavior-protocol.md L588 step 6b 推荐语境含「当前项目阶段」 | read L583-592 | ✅ 证实（逐字） |
| B17 | task_priority.py L1696 `recommended = sorted(unblocked, key=_priority_sort_key)`；L1630 注释「sorted by priority then version」 | read 两处 | ✅ 证实（逐字）——H2 证伪侧直接证据 |
| B18 | verify_workflow.py L11033-11073 `_status_next_steps` 排序键 =（priority rank，进行中优先，文档序），无 Gate | read L11030-11074 | ✅ 证实 |
| B19 | verify_workflow.py L22486-22493 `cmd_loop_rollup` 为独立薄 CLI 入口 | read L22482-22495 | ✅ 证实 |
| B20 | core/lifecycle.md mtime **2026-05-01 22:05:56**（早于 DEC-097） | pwsh Get-Item | ✅ 证实（精确到秒一致） |
| B21 | `.governance/flow-unit-runtime.json` 不存在 | pwsh Test-Path | ✅ 证实（False） |
| B22 | `.governance/loop-event-log.jsonl` 不存在 | pwsh Test-Path | ✅ 证实（False） |
| B23 | loop-exit-candidates.json `exit_events_consumed: 0`（2026-09-19 生成） | read 全文 | ✅ 证实（L2-L3；字段结构确为 task-priority 输出形态） |
| B24 | AUDIT-143 L322-323（0.74 时点两 loop 数据文件不存在）、L251 REQ-112 | grep/read | ✅ 证实 |
| B25 | 仓库根 CLAUDE.md/AGENTS.md loop=0 | 本会话注入文本复核 | ✅ 证实（loop=0 成立；报告所称 Gate 计数 12/4 未逐字重数，非结论支柱） |
| B26 | 「决策通过 **15 个版本**（0.65→0.89）」 | grep CHANGELOG 版本段 | ❌ **证伪**——`project/CHANGELOG.md` 0.65.0~0.89.0 共 **32 个**版本条目（24 条 minor 线）；「15」与任何口径均不符（→ D-2） |

### 2.2 结构面报告（20 处）

| # | 报告引用 | 抽查方式 | 结果 |
|---|---|---|---|
| S1 | lifecycle-registry.json L10-11 `active/default_lifecycle_mode: "classic-phase-gate"` | read L5-34 | ✅ 证实（逐字） |
| S2 | lifecycle-registry L13-14 runtime_activation（flow_unit_status_runtime/project_migration = false） | read L12-18 | ✅ 证实 |
| S3 | lifecycle_modes 仅含 classic-phase-gate 与 dynamic-flow-gate 两值、loop-engineering 无席位 | grep 模式 id | ✅ 证实（仅 L32/L68 两命中） |
| S4 | lifecycle-registry L19-29 no_overclaim（preserves classic G1-G11、不关 RISK-037） | read L19-29 | ✅ 证实 |
| S5 | loop-engineering-registry.json L9 `registry_mode: "schema-only-no-runtime-activation"` | read L1-25 | ✅ 证实（逐字） |
| S6 | loop-engineering-registry L13-14「不激活运行时」「不修改 classic G1-G11 判定」 | read L11-18 | ✅ 证实（两语句在 L13/L14；报告另引 L16 为 RISK-037 条款，微偏不害意） |
| S7 | loop_migration.py L241-243 以 `## Gate 状态跟踪` 存在性推断 classic 模式 | read L225-254 | ✅ 证实（逐字，含启发式注释） |
| S8 | verify_workflow.py L9917-9972 `check_gate_consistency` 空转：`found` 计算后未使用、passed-on-entry 分支 `pass` | read L9912-9973 | ✅ 证实（L9930-9934 计算/L9937 `pass`；L9944 `pass`——「呈现性权威无事实约束」判定成立） |
| S9 | loop_engine.py L973-1096 `rollup_loop_state` 的 no_global_stage 载重不变量 | read L973-1012 | ✅ 证实（docstring L985-1007 明载不变量与回归锁） |
| S10 | plan-tracker L12「当前阶段: 维护与演进（第 11 阶段）」 | read L8-87 | ✅ 证实 |
| S11 | plan-tracker L21「当前阶段（11）Gate: G11 pending」 | read L16-22 | ✅ 证实（逐字） |
| S12 | plan-tracker L38 G11 行状态 `passed`（2026-04-21） | read L24-38 | ✅ 证实 |
| S13 | plan-tracker L44 项目总览「最近 Gate 结论: G11 通过」——**三处矛盾无 Check 发现** | read L40-44 | ✅ 证实（L21 pending / L38 passed / L44 通过三方矛盾实锤，与 S8 校验空转互证；C-10 成立） |
| S14 | plan-tracker L82-83 AUDIT-155/156 并行票登记（🔄 进行中） | read L78-87 | ✅ 证实 |
| S15 | plan-tracker L11 确认 0.89.0 已发布态 | read L11 | ✅ 证实 |
| S16 | DEC-097 原文（archive L11/L16）：重构式为唯一模型、并存式被否决 | read archive L1-24 | ✅ 证实（否决理由「并存双模式导致双轨维护成本且不解决根因（线性心智模型仍在）」与报告引用**逐字一致**） |
| S17 | DEC-133 关闭 RISK-037/RISK-042 系「外部验证标准满足，非方向变更」 | grep archive + read L96/L101 | ✅ 证实（decisions-v0.1.0-0.78.0.md L96/L101） |
| S18 | loop-role-mapping.md L5「0.66.1 定位 experimental scaffolding：runtime activation NOT_MET、migration validity NOT_MET」 | read 全文 50 行 | ⚠️ 部分证实——文件逐字如此；但该声明锚定 0.66.1（2026-07-17）时点，早于 DEC-133（07-26），报告将其用作「从未通过外部验证」的现行证据不成立（→ D-1） |
| S19 | RB-2 前提「loop runtime **从未通过外部验证**」 | 对照 DEC-133 | ❌ **证伪**——DEC-133 明载 VAL-008 dogfood PASS + VAL-009 双外部类型（shitu Android/mobile-app + python_game）PASS、「从 experimental/scaffolding 升级为 externally-validated runtime（3 项目原型验证）」（→ D-1，阻塞） |
| S20 | 「0.65~0.89 的 **fifteen-version** 停滞」 | 同 B26 | ❌ **证伪**——实际 32 个发布条目（→ D-2） |

### 2.3 未抽查项（存在引用但本轮未逐一验证；均非结论支柱）

行为面 §2 1-2（governance-init.md L222/L278/L369）、1-4（verify L11190/L11194/L11528-11544）、3-2（SKILL L146/L161）、3-4（stage-research L36/L100-102）、4-4（governance-init L335/L339）、§4.3 全量密度统计的 Top15 行级数字、launch.py 18 处计数。已抽查的同类锚点（B1/B4/B11/B13 等）全部命中，未抽查项风险低；R1 复审无需补查，除非返工触及。

**抽查统计**：46 处 = 证实 41 + 部分证实 2 + 证伪 3（满足「合计 ≥10、每份 ≥5」要求）。

---

## 3. 维度 2：结论一致性与双报告汇合归因

### 3.1 R1-R8 ↔ C-01~C-10 对应关系

**成立，无矛盾**。两报告是同一病灶的两个正交切面（行为面=语言如何到达 agent；结构面=结构为何只供给线性语言），对应关系为层互补而非 1:1：

| 行为面 | 结构面对应 | 关系 |
|---|---|---|
| R1 模式确认句 | C-08（入口确认句线性坐标） | 同一注入点的两面 |
| R2 next_gate + loop 零投影 | C-04 + C-06 | 完全对应 |
| R3 main-workflow 线性规则 | C-02（核心定义层）+ C-08 | 部分——main-workflow 本身无独立 C 条目，建议返工时补映射表（→ D-4） |
| R4 M6 passed=进入下一阶段 | C-02（stage-gates 原则 1） | 语义同源（L426 与 stage-gates L108 同表述，均经查证） |
| R5 阶段跳跃防护 | C-03 + C-08（判定对象） | 对应 |
| R6 数据模型线性队列 | C-07 + C-01 | 完全对应（R6 即 C-07 的数据面表述，且 S10-S13 已实证） |
| R7 核心层脱节 | C-01/C-02/C-03 | 对应 |
| R8 loop 运行时零激活 | C-01 + §4 接线度分析 | 完全对应 |

狗粮数据三件（B21/B22/B23）两报告口径一致，且与 AUDIT-143 0.74 时点记录（B24）形成时间序列闭环。**未发现任何两报告互相矛盾的陈述。**

### 3.2 RB-1 裁断：投影字段语义层 vs 注入链断链的主因竞争

**裁断：合并证据足以支撑「投影字段语义层是残余偏差的主因」这一归因，限定语是「残余偏差」（0.74/0.75 修复链之后的剩余症状）；但行为级因果确认仍属未定，须按 RB-1/RB-3 缓解路径以行为取证闭合。**理由：

1. **竞争解释已被削弱**：AUDIT-143 诊断的「注入链断链」对象是**行为规则**（复审/推荐/机录契约）；FIX-253 修复后，契约确已到达注入面（B12 实证 persona L66-71 五条在位）。用户反馈发生于修复链之后——对**修复后仍存在**的线性症状，「规则不在上下文」解释已失去竞争资格。
2. **排序层替代解释已被证伪排除**：H2 证伪侧三处独立代码证据（B17/B18/B9）+ 协议措辞（B16）均显示推荐排序是依赖+优先级+版本驱动，无 Gate 排序倾向。排除该替代解释后，剩下的唯一「每会话必经且带方向性」的结构事实就是投影字段语义层（next_gate 一等字段 + stage 单值 + 模式确认句 Gate 坐标 + plan-tracker 11-Gate 表），全部经抽查证实（B5-B8/B10/B11/S1/S10-S13）。
3. **未定部分如实标记**：H-1/H-2（投影→行为的因果）为机制推断，无会话行为样本（行为面 §8 未验证项 1/3、结构面 H-1/H-2/RB-3 自认）。两报告均未把推断升格为事实——纪律正确。
4. **裁断的决策含义**：归因成立到「结构必然性」层面即可支撑修复立项的方向判断（投影/呈现层改造有据）；但验收必须按 RB-1 缓解定义**行为级信号**（新会话不预读第四层文件仍执行 loop 语义），不得以「字段存在」验收——这与 RB-1 缓解原文一致，审查予以背书。

### 3.3 H2「部分证伪」证据充分性

**充分**。证伪侧：排序键逐字证实无 Gate 参数（B17/B18）；动作模板无 Gate 类（B9）；推荐规则语境（B16）依赖驱动。证实侧：`next_gate` 从初始化（L296）到赋值（L313-314）到 payload（L644）到 text 渲染（L877-879）全链路逐字证实，且对照面（bootstrap 全文 loop=0，B10）成立。「部分证伪 + 呈现层部分证实」的表述精确反映了证据分布，无过度声称。

---

## 4. 维度 3：方案完备性（结构面）

| 检查项 | 要求 | 实际 | 判定 |
|---|---|---|---|
| 候选方案数 | ≥2 | 3（A 投影重解释 / B 结构切换 / C 混合渐进） | ✅ |
| 每候选改动面 | 完整 | A：4 项枚举+6~10 文件估算；B：7 项枚举+30+ 文件+分批授权票；C：5 项枚举 | ✅ |
| 迁移成本/风险/回滚 | 每候选齐备 | 三候选均含四要素；B 的回滚有机器支持依据（rollback_migration + 备份，引用 loop_migration L41/L281-284）；A 纯增量可逆 | ✅ |
| 比较标准前置 | 在比较前定义 | §5.0 五条（S-1~S-5）位于 §5.1~5.3 候选之前，含度量方式 | ✅ |
| 蓝军挑战 | ≥3、独立 ID、每条有缓解 | 4 条 RB-1~RB-4，各具独立攻击向量与缓解措施 | ✅ |
| 不做最终决策边界 | 决策留用户 | §5.4 明文「本报告不推荐具体候选」 | ✅（措辞「决策留给用户 + Design Reviewer」中 Design Reviewer 的角色按边界仅为本报告这类质量裁决，不含方案选择——建议返工时改为「决策归用户（经设计审查质量裁决后）」，→ D-4） |

附注（非缺陷）：RB-4 的缓解（Gate 结构消费点普查进 ADR、S-3 从「预估」降为「清点」）与候选 B 的分批授权票模式（参照 FEAT-064 先例）质量高，审查背书。

---

## 5. 维度 4：假设与事实分离

**总体纪律良好，一处违例（D-1）。**

- 行为面：H1/H2/H3 均给出验证过程而非断言；H2 残余不确定显式标注并映射 §8 未验证项 3；§8 五项未验证含现状依据/验证计划/阻碍三栏；§9 明确「观察性描述，非修改方案」。✅
- 结构面：§1 关键发现第 6 条显式标「假设」；§7 事实四条 vs 假设 H-1~H-4 分离；H-4（校验空转属无意缺陷）诚实标注无文档证据。✅
- **违例**：RB-2 把过时的 0.66.1 时点标记当作现行事实，断言「loop runtime 从未通过外部验证」——被 DEC-133 证伪（§2.2 S19）。这是把失实前提写成事实的段落，且位于影响用户决策的风险评估项中。→ D-1（阻塞）。
- 措辞建议（非阻塞）：结构面 §1「必然后果」的「必然」依赖 H-1，建议限定为「结构层面必经信息环境的必然产物（行为因果见 H-1）」；行为面 L34「全部三个触发模式共用此句式定义」与 SKILL.md L89-92 实况不符（on-demand/silent-track 变体不同，仅 always-on 用完整句式）→ D-4。

---

## 6. 维度 5：硬门槛裁决

| 门槛 | 阈值 | 实际 | 判定 |
|---|---|---|---|
| Architect：候选方案数 | ≥2 | 3 | ✅ |
| Architect：蓝军挑战 | ≥3、独立 ID | 4（RB-1~RB-4） | ✅（但 RB-2 前提失实 → D-1 修复后维持通过） |
| Architect：比较标准前置 | 评估前定义 | §5.0 前置 | ✅ |
| Analyst：四观察面各 ≥2 实证注入点 | 4×2 | 面 1：1-1/1-5（B1/B6-B7 证实）；面 2：2-1/2-2/2-3（B5/B16/B13 证实）；面 3：3-1/3-3（B14/B11 证实）；面 4：4-1/4-2/4-3（S10-S13/B20/B15 证实） | ✅ |
| Analyst：假设显式化 | 显式 | 两报告 H 系全标记 + 未验证项各 5 条 | ✅ |
| Analyst：grep 计数可复现 | 可复现 | §4.1 给出命令；关键计数经本轮独立复现（B10 loop=0；S3 两值枚举） | ✅ |
| ADR 关键字段 / Bar Raiser | — | 本轮审查对象为分析报告非 ADR；独立评审职责由本设计审查承担 | ✅（不适用/已覆盖） |

**硬门槛全部通过。NEEDS_CHANGE 由维度 4/§8 的阻塞问题 D-1 触发，非门槛失败。**

---

## 7. 维度 6：与 DEC-097 的继承关系审查（专项）

对照 DEC-097 原文（`.governance/archive/decisions/decisions-v0.1.0-0.64.0.md` L11/L16，本轮实际读取）逐候选核验：

| 候选 | 报告表述 | 核验结果 |
|---|---|---|
| A 投影重解释 | 「部分继承……该决议明确否决过并存式，本候选实质是受控并存，需用户显式重新授权该偏离」 | ✅ **准确**。DEC-097 备选 (b) 即「并存式双模式」，被否决；A 保留 classic 判定权威 + 增量 loop face，实质属并存形态，要求重新授权的表述正确且必要 |
| B 结构切换 | 「完全继承——三项决议全部兑现……0.65~0.89 的停滞是该决策的执行欠账而非否决（无任何后继 DEC 推翻 DEC-097——DEC-133 关闭的 RISK-042 是外部验证标准满足，非方向变更）」 | ✅ **准确**。DEC-097 决议 = (A) 重构式 loop 唯一模型 + (B) AI 循环一等公民 + gate-as-loop-exit/三层嵌套环，B 候选逐项对应；「无后继 DEC 推翻」经 DEC-133 归档记录核验成立（关闭理由为验证标准满足，见 S17）。⚠️ 但候选 B 风险①引用 VAL-006（0.55 时点「非 game 派生失败」）时未对账 DEC-133 已将「非 game 泛化边界」列为满足的关闭标准——同一过时证据模式，随 D-1 一并修正 |
| C 混合渐进 | 「与决议方向冲突（DEC-097 明确否决并存式）——需新 DEC 入账」，引排除理由原话 | ✅ **准确**。排除理由「双轨维护成本且不解决根因（线性心智模型仍在）」与归档 L16 **逐字一致**（S16） |

**专项结论**：三候选的 DEC-097 继承/偏离表述全部准确，且正确地把「是否偏离已确认决策」上升为用户决策项而非分析方代决。这是本双报告最强的部分之一。

---

## 8. 缺陷清单与返工指引

### D-1（BLOCKING——本轮 NEEDS_CHANGE 唯一触发项）

- **位置**：结构面 §6 RB-2（前提句）；关联 §5.2 候选 B 风险①（VAL-006 时点）；关联 §8 未验证项 3。
- **缺陷**：RB-2 声称「VAL-006 + loop-role-mapping.md L5（NOT_MET）表明 loop runtime **从未通过外部验证**」。证伪事实：**DEC-133（2026-07-26，`archive/decisions/decisions-v0.1.0-0.78.0.md` L96/L101）以 8 项关闭标准全 PASS 关闭 RISK-037/RISK-042**，明载 VAL-008 dogfood PASS + VAL-009 双外部类型（shitu Android/mobile-app、python_game）PASS，及「Loop Engineering 从 experimental/scaffolding 升级为 externally-validated runtime（3 项目原型验证）」。loop-role-mapping L5 的 NOT_MET 是 0.66.1（2026-07-17）时点声明，早于 DEC-133 九天，引用它否定其后的决策记录属时序错置。同时，候选 B 风险①仅引 VAL-006（0.55 时点），未对账 DEC-133 已满足「非 game 泛化边界」关闭标准。
- **为何阻塞**：RB-2 是四条蓝军中唯一针对候选 B 可行性的挑战，其失实前提会系统性抬高用户对 B 的风险感知；且「DEC-133 ↔ loop-role-mapping L5 ↔ dogfood 从未激活（flow-unit-runtime.json 不存在，经 B21 复核）」三方矛盾恰是两报告主题（治理记录事实漂移无校验、R7/C-10 同类病理）的在案实例，隐瞒它使报告错过一个强化自身论点的发现。
- **修复建议**：① RB-2 前提改写为：「原型级外部验证曾通过（DEC-133，VAL-008/009），但**宿主激活从未发生**（dogfood flow-unit-runtime.json 至 0.89.0 不存在）且 loop-role-mapping.md L5 仍滞留 0.66.1 时点 NOT_MET 声明未更新——验证通过 ≠ 宿主激活，迁移有效性在真实宿主仍为 NOT_MET 口径」；② 将三方矛盾列为独立发现（可归入 C-10 类或新增 C-11），并作为「治理记录无一致性校验」的补充证据；③ §5.2 风险①补 DEC-133 对账，缓解措施可复用 DEC-133 关闭标准作为候选 B 验证门模板；④ §8 未验证项 3 同步改写。
- **复审验证方法**：R1 直接对照 DEC-133 归档 L96/L101 与改写后 RB-2 文本。

### D-2（WARNING）

- **位置**：行为面 §3 末行「决策通过 15 个版本（0.65→0.89）」；结构面 §5.2「0.65~0.89 的 fifteen-version 停滞」。
- **缺陷**：`project/CHANGELOG.md` 0.65.0~0.89.0 实为 **32 个版本条目**（24 条 minor 线）；「15」与任何口径不符。两报告同病。
- **修复建议**：统一改为「32 个发布版本（0.65.0~0.89.0，CHANGELOG 实计）」或「24 条 minor 线」；若「15」另有所指（如 0.75→0.89 的 15 条 minor 线）须写明口径。

### D-3（WARNING）

- **位置**：行为面 §3 表格行「FIX-253……把**行为契约四条**……写入 persona（L66-71）与 SKILL.md（L225-232）」与 §5-H1 第 1 点「SKILL.md L225-232 为 canonical 定义」（称五条）。
- **缺陷**：现状实证——persona L66-71 为**五条**（含真实环境必防护）；SKILL.md L225-232 为**四条**（复审必达/完成必推荐/选项必带依据/真实环境必防护），且 SKILL.md **全文 grep `机录` 0 命中**——「审查结论必机录」在该 canonical 块中不存在。§3 的「四条（含机录）写入两处」与 §5 的「五条以 L225-232 为 canonical」互相矛盾且均与现状不符。
- **修复建议**：改为「FIX-253 将四条契约写入注入面；现行 persona 演化为五条（后续 FIX-271/274 增补真实环境必防护）；SKILL.md L225-232 为 canonical 投影定义处，当前承载四条——审查结论必机录的 canonical 定义在 behavior-protocol.md M7.4，persona 携带其压缩形式」。此偏差不改变 H1 结论（契约确已到达注入面，反而更强）。
- **复审验证方法**：R1 read persona L66-71 + SKILL.md L225-232 比对条目清单。

### D-4（SUGGESTION——合并返工，不单独设轮）

1. 行为面 §2 表 1-1「全部三个触发模式共用此句式定义」→ 改为「always-on 模式使用完整句式（L90）；on-demand/silent-track 为变体（L91-92）」。
2. 结构面 §1「必然后果」措辞按 §5 建议限定（避免与 H-1 假设标记自相摩擦）。
3. 结构面 §5.4「决策留给用户 + Design Reviewer」→「决策归用户（经设计审查质量裁决后）」，与「不做最终决策」边界精确对齐。
4. 建议在任一报告（或 Coordinator 汇合层）补一张 R1-R8 ↔ C-01~C-10 显式映射表（本报告 §3.1 可直接复用），便于后续修复立项按图索骥。
5. 微偏行号勘正（可选）：bootstrap docstring「first pending gate id」在 L291 非 L292。

---

## 9. 复审声明与自检

- **给 Coordinator**：本审查结论 NEEDS_CHANGE（round R0）。按 M7.4/T1：返工由 Architect/Analyst 按缺陷清单修复（D-1 为主，D-2/D-3 同轮必改，D-4 建议顺带）后，**MUST spawn 同一 Design Reviewer 复审（R1）并注入本报告路径** `docs/reviews/review-AUDIT-155-156-DESIGN-R0.md`。R1 复审聚焦：D-1（对照 DEC-133）、D-2/D-3 文本核对；其余维度已达标，无重复全量审查必要。
- **本审查自检**：
  - [x] 只读审查：除本报告外零文件修改；未触碰 `.governance/`（plan-tracker/decision 归档均只读）
  - [x] 事实抽查 46 处（≥10），每处记录验证结果（证实/部分证实/证伪）
  - [x] 结论三选一：NEEDS_CHANGE（逐维度判定 §3-§7 + 缺陷清单 §8）
  - [x] 不做方案选择决策（A/B/C 归用户）；不与用户交互
  - [x] 全部审查结论有可复查事实依据（文件+行号/命令输出/归档记录）；无法验证项显式标注（§2.3）

## 审查对象质量总评（供 Coordinator 参考）

证据密度与引用精度在同类分析报告中属上乘（行号级命中率高、历史锚点全部实际读取、假设分离纪律严格）；阻塞项单一且修复成本低；R1 预期可通过（若 D-1 修复到位且无新引入）。
