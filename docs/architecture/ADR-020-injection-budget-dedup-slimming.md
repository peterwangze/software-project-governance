# ADR-020 — strict 注入预算治理：不损害契约的去重瘦身方案（FEAT-073 阶段 1 研究产出）

- **日期**：2026-09-28
- **状态**：PROPOSED（研究阶段产出——只出建议，方案选择权在用户；未经用户裁决不构成决策，零实施）· **R0 修订版（2026-09-28，findings F-1~F-7 已处置**——审查报告 `docs/reviews/review-FEAT-073-R0.md`，APPROVED_WITH_NOTES / unresolved_blockers=0；处置表见 §13）
- **任务**：FEAT-073（P2，目标版本 0.92.0）；授权依据 DEC-269（0.92 批首票开工——研究优先）
- **作者**：Architect Agent（Coordinator 派发）

---

## 1. 背景

### 1.1 预算现状（Coordinator 2026-09-28 HEAD 实测，check-injection-budget）

| 档位 | resident 实测 | 预算 | 余量 | 结论 |
|------|--------------|------|------|------|
| lightweight | 4241 tok | 6000 | 1759 | PASS |
| standard | 5719 tok（DEC-268(2) 记载基线，本阶段未实测） | 6000 | 281 | PASS |
| **strict** | **5991 tok** | 6000 | **9** | PASS（贴线） |

- resident 档为 **hard gate**（FEAT-050 / DEC-211③；`checks/injection_budget.py` L76-78、L187-192）——任何净增 >9 tok 即越界 FAIL（DEC-267(2) 措辞：「当前口径下净增超过 9 tok 即越界；计量或生成内容变化也可能越界」）。
- 登记验收指标（DEC-268(2)）：**三档 PASS 且 strict 余量恢复 ≥100 tok，或出具基准依据的重定标 DEC**。
- 回弹证据：EVD-1104（0.86 瘦身后）基线为 lightweight 4,216 / standard 5,694 / strict 5,966（`injection_budget.py` L44-46 模块注释）→ 当前 4241/5719/5991 = **三档一致 +25 tok**。三档差额完全一致说明增量位于 profile 无关的共享表面（persona / secondary-entry-template / agent-instructions 之一）——此为推断（未逐表面重放历史 diff，标注为待验证），但与该模块自己的警告一致：「预算不守护则瘦身必然回弹」（L4-5）。
- 架构目标方向：预算常数注释明确 arch target 为 4K（L76）——长期方向是**向下**，去重瘦身与该方向一致；直接抬限与 DEC-266(3) 决策顺序（「超限先压缩本条重复表达，再提交瘦身 diff 讨论——不得擅删其他强制行为/既有锚/提预算上限」）相悖。

### 1.2 四个 resident 注入表面（计量器权威定义：`injection_budget.py` L107-168）

| 表面 | 源文件 | 作用域 | strict 实测（chars/CJK/tok） |
|------|--------|--------|------------------------------|
| persona | `agent-presets/governance/agent.cordis.yml.template`（`prefix:` 块，L48-74） | persona-prefix | 2381 / 636 / **1075** |
| entry-template | `commands/governance-init.md` Step 7 模板（strict = standard 共享基座 + strict 差异段，`sync_entry_projection.py` L159-164 拼接） | template-block | 5925 / 2149 / **3111** |
| secondary-entry-template | 同文件（secondary-thin 薄指针模板，L347-379） | template-block | 1884 / 469 / **827** |
| agent-instructions | `adapters/dsh/AGENTS.md.template`（全文 38 行） | full-file | 2289 / 537 / **978** |

说明：strict 与 lightweight 档 entry-template 差异（3111 vs 1361 tok）是**真实内容差异**（strict=共享基座+差异段；lightweight=独立精简模板），非计量口径伪影——计量器按各档实际渲染文本计价（L552-556）。

### 1.3 重复结构诊断（本阶段 Read/Grep 事实）

四个表面的共注入形态（DSH 狗粮会话）：persona（preset 插件）+ entry-template（主入口 CLAUDE.md 投影）+ secondary-thin（次入口 AGENTS.md 投影）+ agent-instructions（preset 插件）。逐对重复分析：

| 重复对 | 共现保证 | 重复内容 | 去重空间 |
|--------|----------|----------|----------|
| **persona ↔ agent-instructions** | **结构性**——两面同属 governance preset 的适配层交付物（`launch.py --install/--sync` 单次装配同时交付 persona prefix 与 AGENTS.md 投影），共现由装配构造保证（R0 F-5 措辞修正——原「两行同在 L45-79」不精确：agent-instructions 内容源为 `adapters/dsh/AGENTS.md.template`，preset 文件 L76-79 仅为组件声明） | 第一动作 4 步（persona L53-57 ≈ AGENTS.md.template L7-13）、FEAT-040 灰度开关句（L59 ≈ L15-17）、SELF-CHECK（L61 ≈ L19-23）、模式确认（L62 ≈ L25-29）、Agent Team（L64 ≈ L31-34）、hooks/升级（L73-74 ≈ L36-38） | **大**（约 persona 的 42-50%） |
| entry-template ↔ 其余三面 | 非结构性（单入口工作区只有 entry-template 加载） | SELF-CHECK/FEAT-040/模式确认等在标准基座内必须自足 | **无跨面去重空间**（自足性不变量所致；FEAT-041 已做过 EVD-1104 瘦身） |
| secondary-thin ↔ persona/agent-instructions | 非结构性（薄指针服务非 DSH 平台 Codex/opencode 会话） | 第一动作/SELF-CHECK/模式确认/快速入口 | 仅行内压缩空间（FEAT-037 保留清单 + 方言锚钉住下限） |

**关键结构性事实**：persona ↔ agent-instructions 是四个表面中**唯一**具有构造性共现保证（同属适配层单次装配交付——R0 F-5）的表面对——这是本 ADR 主候选的成立基础。

---

## 2. 决策建议（供用户裁决，非决策）

**推荐组合**：候选一（A，persona↔agent-instructions 结构性单源化）为主 + 候选二（B，薄指针层行内压缩）为辅；**不建议**现阶段走重定标路线（对照路线 D，证据不足）。预期 strict 余量 9 tok → **约 574 tok（A+B 估算，分量之和口径，见 §5.4）**，满足 DEC-268(2) 的 ≥100 tok 验收指标并留出净增缓冲。A 单独实施即达标（估算余量 ≈420）；B 单独实施达标但下缘脆弱（估算余量 ≈115-190）。**〔R1 实测修订（2026-09-28）：A+B 已实施，实测余量 391；实测 B 单独仅 ≈37 不达标、「仅 B 达标」作废——见 §5.4 R1 注〕**

**边界声明**：本 ADR 为阶段 1 研究产出，全部 token 数字为**估算**（方法与误差见 §5.4）；实施与否、实施哪个候选、是否叠加，均由用户裁决后方可进入实施票。

---

## 3. 候选方案

### 3.1 候选一（A）——persona ↔ agent-instructions 结构性单源化【推荐主选】

**改动内容**（唯一触及文件：`agent-presets/governance/agent.cordis.yml.template` 的 `prefix:` 注入块）：

保留（persona 独有职责）：
- L49 英文身份行（提取锚 `PERSONA_PREFIX_FIRST_LINE` 必须保留，`injection_budget.py` L98/L370）；
- L51 Coordinator 身份 + 仓库根 + infra 绝对路径规则 + 版本行（动态锚 `治理工作流（v0.91.0）` 载体）；
- L66-71 **关键行为契约块全文**（复审必达/完成必推荐/选项必带依据/审查结论必机录/真实环境必防护——persona 全部 14 个契约锚的载体）；
- L59 **压缩改写**为单行：保留「行为灰度开关」marker + 五个安全不变量 marker（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达）+「安全语义不回退」表述 + 开关操作指引两 token（`GOVERNANCE_LEGACY_BEHAVIOR=1` 与 `behavior_profile: legacy`——R0 F-2 补入；Step7 token 钉测试不覆盖 persona，丢弃不会红测，实施时须在 check-injection-contract 之外自查压缩行含完整开关句）。

删除（与 `adapters/dsh/AGENTS.md.template` 重复的操作面，该面原文保留不动）：
- L53-57 每会话第一动作 4 步、L61 SELF-CHECK 行、L62 模式确认行、L64 Agent Team 细则行、L73-74 hooks/版本升级行。

新增：第一动作硬触发器一行 + 指针（合计约 3 行内），示意文本：
> 每会话第一动作（bootstrap，fail-closed）：按 agent-instructions 注入面执行 resolve_entry → 热数据 → 首次交互。
> SELF-CHECK / 模式确认 / Agent Team / hooks 与升级：按本 preset 的 agent-instructions 注入面执行——其缺失时加载 `software-project-governance` skill 获取同等规则；fail-closed 与安全语义不受本指针影响（DEC-080/RISK-038）。

（R0 F-3：第一动作以命令句形态保留于 persona，与 §8 BT-01 缓解承诺一致——两处自洽，BT-01 措辞无需改；该新增行 ≈45 tok 落在候选一 ±12% 区间带内〔下缘 ≈362，调整后净收益 ≈366〕，点估计不另调，以实施实测覆盖。）

**token 收益估算**：净省 ≈ **411 tok**（区间 350–480）。逐项：删 L53-57≈188、L59 原行≈110、L61≈51、L62≈33、L64≈129、L73-74≈91（手工清点原值合计 602，×0.88 系统偏置校正 ≈530），减新增 ≈119。溯源：各行为 `agent.cordis.yml.template` L53-74 原文；校正系数来源见 §5.4。实施后 strict ≈ 5580（余量 ≈420）、lightweight ≈ 3830、standard ≈ 5308（均估算）。

**为何方向是「persona 瘦、agent-instructions 留」**：
1. persona 是 system-prompt 位置——最适合承载身份与非协商行为契约（M7.4/M7.7 MUSTs，14 锚所在）；操作性配方（跑什么命令）放在项目注入面不影响约束力排序。
2. agent-instructions 本身受薄指针方言机检守护（`validate_dsh_thin_pointer`，`sync_entry_projection.py` L286-303）——它已经是结构化守护的「操作面之家」，改动最小。
3. 反方向（候选 A'，见 §6）需在 agent-instructions 内重排更多被钉内容，编辑面更大、收益更小。

**实施步骤**：改 persona 模板 → `check-injection-contract`（14 锚全保留核验）→ `check-injection-budget` 双档实测 → `check-dsh-preset-smoke`（隔离环境冒烟，FEAT-015/RISK-049②）+ `check-dsh-preset-compat`（persona 行结构契约 `config_keys=[prefix]` 不变）→ 相关测试族（test_dsh_contract / test_dsh_compat / test_behavior_profile）→ 狗粮工作区重渲染 preset → DEC 入账。

**回滚**：单 commit（仅 persona 模板）git revert 即可；无投影联动（本候选不触碰 entry 文件），无数据迁移。

### 3.2 候选二（B）——薄指针层行内压缩【推荐辅选，可独立实施】

**改动内容**（触及文件：`commands/governance-init.md` secondary-thin 模板块 + `adapters/dsh/AGENTS.md.template` 模式确认节）：

| 子项 | 现状 | 压缩为 | 保留的锚/token |
|------|------|--------|----------------|
| B-a thin SELF-CHECK 节（L361-365，5 行） | 三检完整表述 | 2 行（三检全保留、仅去冗余措辞） | `SELF-CHECK`、`AskUserQuestion`、`.governance/plan-tracker.md`、§B0 指针 |
| B-b thin 模式确认（L369-371，3 行） | 三模式各一行 | on-demand/silent-track 两行合一 | `always-on`、`silent-track` token（方言锚） |
| B-c thin 快速入口（L373-378，6 行） | 4 项 3 行 + 空行 | 合并为 2 行 | `.governance/evidence-log.md`、`verify_workflow.py`、`/governance`、FIX-278 UTF-8 实质、主入口指针 |
| B-d agent-instructions 模式确认（L27-29，3 行） | 三模式各一行 | on-demand/silent-track 合一 | `always-on`、`silent-track` |

**明确不动**：thin L358（FEAT-034/040 行——承载测试钉 tokens：`GOVERNANCE_LEGACY_BEHAVIOR`、`behavior_profile`、`安全语义不回退`，test_behavior_profile.py L282-292 逐模板断言）；「行为灰度开关」marker 所在行。

**token 收益估算**：净省 ≈ **154 tok**（区间 115–190）。逐项：B-a≈78、B-b≈21、B-c≈33、B-d≈22（原值合计 ≈175，×0.88 校正）。实施后 strict ≈ 5837（余量 ≈163，估算）。

**约束核验**：压缩后薄指针 ≤40 行/≤3072 字节（现 32 行/2859 字节，压缩后约 27 行/2600 字节）；共享核心锚 + 生成方言锚 + DSH 方言锚全保留（`validate_thin_pointer` / `validate_dsh_thin_pointer` 可机检）。FEAT-037 保留清单（governance-init.md L386「去重不得删除行为约束」）以**压缩不删检**方式满足——三检、快路径、灰度开关、模式确认、快速入口、主入口指针全部仍在。

**实施步骤**：改两处模板 → `sync_entry_projection.py --write` 再生狗粮 AGENTS.md 薄投影 → `check-entry-bootstrap-sync` + `check-projection-sync` + `check-injection-contract` + `check-injection-budget` 双档 + `test_behavior_profile::PublicationTests` / `test_dsh_thin_pointer_dialect_carries_the_switch` → DEC 入账。

**回滚**：模板与投影同一 commit revert；投影幂等（跑两次零 diff，`sync_entry_projection.py` L16-18）保证再生安全。

---

## 4. 对照路线（D）——有依据的重定标：评估结论 = 现阶段不推荐

- **路线定义**：出具基准依据（如与宿主真实 BPE tokenizer 的对照证据）后，以 DEC 重定标预算常数或计量口径（DEC-268(2) 明示的替代验收路径）。
- **当前证据状态**：仓库内现有两个计量器均为启发式——校准口径（CJK=1 tok/char，预算权威）与宿主口径（ceil(chars/4)，仅对照列）。宿主口径**不能**作为放宽依据：计量器自身文档明确其会对 CJK 面低估 3-4 倍（`injection_budget.py` L15-20、L266-278）——用它转绿就是「为转绿抬限」的换名。本阶段未发现任何真实 BPE tokenizer 对四个表面的实测基准产物（Read/Grep 检索范围内；Bash 禁止故无法现场生成）。
- **决策顺序约束**：DEC-266(3) 明令预算处置顺序为「先压缩→瘦身 diff→提上限为最后手段」；且 arch target 为 4K（向下）。重定标与两者方向相悖，只能作为证据齐备后的兜底。
- **结论**：重定标**不进入推荐序列**（亦不作为唯一推荐——本 ADR 推荐为 A+B 去重路线）。若用户意欲走此路线，前置门槛为：先产出基准证据包（对四个 resident 表面跑真实 tokenizer 实测 + 与校准口径的对照曲线），再立重定标 DEC。该门槛本身即 DEC-268(2) 的原文要求。

---

## 5. 估算方法论与溯源（no-overclaim 核心）

### 5.1 计量口径（与预算门一致）

CJK 字符（含全角标点，regex 见 `injection_budget.py` L213-214）=1 tok；ASCII=ceil(chars/4)；其他=ceil(chars×2/5)；逐表面汇总取整（L250-262）。HostTok 列仅为对照，不参与预算。

### 5.2 手工清点 + 系统偏置校正

本角色 Bash 禁止，无法现场运行计量器；估算方法：对拟删块逐行清点字符（按 §5.1 口径），并与实测总量对账——persona 逐行清点合计 2722 chars/716 CJK vs 实测 2381/636，**系统性偏高 ≈13%**（字符 +14.3%、CJK +12.6%）。故全部点估计按 **×0.88** 校正，报 **±12% 区间**，并声明：**最终以实施 PR 内 check-injection-budget 双档实测为准，实测数字取代本 ADR 估算**。此为显式标记的已验证假设（校正法）与残余不确定项（§9）。

### 5.3 溯源表（估算 → 证据）

| 估算项 | 手工原值 (tok) | 校正后 | 溯源 |
|--------|---------------|--------|------|
| A-R1 persona L53-57 | 188 | 165 | `agent.cordis.yml.template` L53-57 原文逐行清点 |
| A-R2 persona L59 | 110 | 97 | 同上 L59 |
| A-R3 persona L61 | 51 | 45 | 同上 L61 |
| A-R4 persona L62 | 33 | 29 | 同上 L62 |
| A-R5 persona L64 | 129 | 114 | 同上 L64 |
| A-R6 persona L73-74 | 91 | 80 | 同上 L73-74 |
| A-新增（压缩行+指针） | −119 | −119 | 新拟文本按同口径清点 |
| **候选一净收益** | **602−119=483** | **≈411** | 实测基线：persona 1075 tok（strict/lightweight 双档同值，sha 8431118734f144a4） |
| B-a thin SELF-CHECK | 89 | 78 | `commands/governance-init.md` L361-365 |
| B-b thin 模式确认 | 24 | 21 | 同上 L369-371 |
| B-c thin 快速入口 | 38 | 33 | 同上 L373-378 |
| B-d agent 模式确认 | 25 | 22 | `adapters/dsh/AGENTS.md.template` L27-29 |
| **候选二净收益** | **176** | **≈154** | 实测基线：secondary-entry-template 827 tok / agent-instructions 978 tok（sha 3cf3d22c7cb96aeb / a60641f93737d052） |

### 5.4 组合预估（全部为估算，非实测）

| 情形 | strict resident | strict 余量 | 满足 ≥100？ |
|------|----------------|-------------|-------------|
| 现状（实测） | 5991 | 9 | — |
| 仅 A | ≈5580 | ≈420 | ✓（区间下缘 350 仍 ✓） |
| 仅 B | ≈5837 | ≈163 | ✓ 但下缘（≈115）贴线 |
| A+B（R0 F-1：分量之和口径） | ≈5426 | ≈574 | ✓ |

注（R0 F-1）：A+B = 5991 − (411+154) ≈ 5426（余量 ≈574）；修订前报告的 ≈5447/≈553 为中间舍入合成噪声，两口径差异 21 tok，均满足 ≥100，不影响结论方向；分量估算值（A≈411 / B≈154）未变。

注（**R1 F-1 实测修订**，2026-09-28 A+B 实施后——实测取代估算，§5.2 条款行使）：实测分量 A = −354（persona 1075→721，落在声明区间 [350,480] 内）、B = **−28**（secondary −29 + agent-instructions +1）；实测余量：**A+B = 391**、仅 A = 363、**仅 B = 37**。§2「B 单独实施达标但下缘脆弱」论断**被实测证伪**（37 < 100）——以本注为准。估算失真根因：§5.3 候选 B 各行未扣减压缩后保留文本（B-a「三检全保留」使保留行承载 ≈80% 原内容；B-d 两 bullet 合一仅省换行+短横，实测 +1 佐证）——方法论沉淀：**压缩类候选一律按「净省 = 原值 − 重写值」计价**（R1 BTR-4）。术语别名登记（R1 BTR-2）：persona 措辞「工作区 AGENTS.md 注入面」≡ agent-instructions 表面（`test_verify_workflow.py` L21272 禁字面）。

---

## 6. 排除的备选方案与理由

| 备选 | 内容 | 排除理由（可溯源） |
|------|------|--------------------|
| A'（反向单源化） | 保留 persona 操作面，瘦 agent-instructions | agent-instructions 受薄指针方言锚钉（shared core + DSH extras + 行为灰度开关，`sync_entry_projection.py` L67-101）——锚下限使其可压缩空间远小于 persona 侧；且操作面离开方言守护面，编辑面更大收益更小 |
| B'（A~E 序列→§B1 指针） | 将 standard 基座 Step 1 第 5 条的内联 A~E 升级序列压缩为纯指针（粗估可省 ≈140 tok） | **否决**：该文本被 ≥4 个测试族故意钉住——`tpl.count("版本升级写序列属推进类动作")==1`（test_verify_workflow.py L9890）、`"DEC-207② P2-1 / M5.5 条 3"` 须在 init（L9915）、cleanup 删除面三 needle 须在 init（L9930-9933）、归档 Step E 7 项 required needles 须在 init（L9816-9826）。设计意图 = 升级写序列的安全细节（确认门/删除面披露/dry-run 先行/归档阻断）必须在 bootstrap 主路径可见、无需按需读——属升级确认门（FEAT-035 安全不变量）的操作化载体，非普通重复 |
| B2（升级门页脚删除） | 删 standard 基座 L290（与 L288 重复的「呈现升级待处理…零写操作」强调句，粗估 ≈58 tok） | **否决**：`tpl.count("呈现升级待处理")==2` 与 `tpl.count("用户未响应前零写操作")==2`（L9887-9888，注释明示 trigger + footer）——双写是测试钉住的故意冗余，服务安全不变量显著性；触碰即削弱 FEAT-040 保护面 |
| 直接抬限（6000→6200 等） | 提高预算常数 | DEC-266(3) 明令禁止作为首择；与 arch target 4K 方向相悖；且 +25 tok 回弹证据表明抬限会被持续增长吃掉 |
| 宿主口径转正（以 HostTok 计预算） | 换计量口径转绿 | 见 §4——宿主口径对 CJK 低估 3-4 倍（计量器自述），等于变相抬限 ~2 倍，属「为转绿抬限」 |

---

## 7. 契约影响评估（逐候选核对注入契约锚）

### 7.1 锚位清单与核对矩阵

| 契约锚组 | 权威位置 | 候选一影响 | 候选二影响 |
|----------|----------|-----------|-----------|
| persona 14 契约锚（关键行为契约/复审必达/NEEDS_CHANGE/完成必推荐/task-priority-analysis/选项必带依据/审查结论必机录/review-record/真实环境必防护/三选一/逐条上报/隔离环境安装冒烟/三要素/推荐卡 + 动态版本行） | verify_workflow.py L6749-6772（@version-line 动态解析 L6895-6921） | **全保留**——全部位于保留的 L51+L66-71；删除行不含任何锚 | 不触及 persona |
| AGENTS.md.template 锚组（关键行为契约 + 共享核心 7 + DSH 方言 3 + 行为灰度开关） | verify_workflow.py L6788；sync_entry_projection.py L67-101 | 不触及该文件 | 仅触 L27-29；`always-on`/`silent-track`/`SELF-CHECK`/`ask_user_question` 等锚全保留 |
| SKILL.md 11 锚 + references/behavior-protocol.md 3 标签锚（服务目标：/解决问题：/方案要点：） | verify_workflow.py L6773-6787 | 零触碰（两候选均不触及该两文件） | 零触碰（同左） |
| 六发布面「行为灰度开关」marker（PROTOCOL_SURFACES） | behavior_profile.py L165-175；test_behavior_profile.py L275-280 | persona 压缩行**保留 marker** | thin 的 marker 所在行（L358）不动 |
| 五安全不变量 marker（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达） | behavior_profile.py L121-152；发布要求=任一发布面+两最富面全覆盖（test L237-256） | persona 压缩行保留全部五个（现行 L59 即承载，压缩不弱化） | 不触及 |
| 四 Step7 模板 token 钉（GOVERNANCE_LEGACY_BEHAVIOR/behavior_profile/安全语义不回退） | test_behavior_profile.py L282-292（对 composed templates 断言） | 不触及 entry 模板 | thin L358 不动 → 三 token 保留 |
| 升级确认门双写钉（呈现升级待处理/零写操作 ×2） | test_verify_workflow.py L9887-9889 | 不触及 | 不触及（B2 已排除） |
| A~E 序列/cleanup 删除面/归档 Step E 钉 | test_verify_workflow.py L9811-9832, L9900-9917, L9919-9949 | 不触及 | 不触及 |

### 7.2 FEAT-040 安全语义不变量逐条声明（一律不触碰）

| 不变量 | 本 ADR 候选的影响 |
|--------|--------------------|
| 升级确认门（确认前零写操作） | 零触碰——两候选均不涉升级写序列文本；B'/B2 因触碰其载体被排除（§6） |
| 异常不隐藏（deferred 显示「待检查」） | 零触碰 |
| fail-closed（resolved_root_ok==false 即停） | 零触碰——persona 删除的 L56 叙述在 AGENTS.md.template L11 与 SKILL.md 原样存在；persona 压缩行保留 `fail-closed` marker |
| 真实环境防护（三选一留痕） | 零触碰——契约块 L71 全文保留 |
| 复审必达（NEEDS_CHANGE round<3 必复审） | 零触碰——契约块 L67 全文保留 |

### 7.3 守卫联动面（影响范围）

`check-injection-contract`（锚存在性）、`check-injection-budget`（双档预算）、`check-entry-bootstrap-sync`/`check-projection-sync`（候选二的投影再生）、`check-dsh-preset-smoke`/`check-dsh-preset-compat`（候选一的 preset 结构与冒烟）、`test_behavior_profile`（发布矩阵）、`test_verify_workflow` FEAT-035 族（升级门钉——两候选均不触碰）、test_dsh_contract/compat（persona 行结构）。

**发现的一个 guard 粒度差（披露 + 加固建议，非本两候选的阻塞项）**：`check_injection_contract` 对 persona 模板检查**整个文件文本**（verify_workflow.py L6913-6923，含非注入的 YAML 注释区），而预算只计 `prefix:` 注入块——理论上把锚移入注释可过检但注入面失约。本 ADR 将「锚必须留在注入块内」列为红线（§8 BT-02）；建议随实施或单列 0.92 票把该检查对 persona 改为对 `extract_persona_prefix_from_template` 输出断言。

---

## 8. 蓝军挑战（5 条，独立 ID + 缓解措施）

| ID | 挑战 | 缓解措施 |
|----|------|----------|
| BT-01 | **persona 约束位置弱化**：第一动作移出 system-prompt 位置后，模型可能先响应再 bootstrap，削弱 fail-closed 首动作的遵循率 | persona 保留一行硬触发器 + 指针（首动作仍以命令句形态出现于 persona）；实施后跑 `check-dsh-preset-smoke`（隔离环境冒烟）；0.92 窗口内对 DSH 会话做 bootstrap 先行行为抽测，异常即回滚并登记风险 |
| BT-02 | **锚检查粒度被利用**：check-injection-contract 是整文件检查，锚可被移入 YAML 注释「过检但失约」 | ADR 红线：候选实施不得把任何锚移出注入块（压缩改写必须原地保留锚词）；后续动作登记 guard 加固票（persona 锚检查改为注入块抽取后断言，见 §7.3） |
| BT-03 | **估算偏差**：手工清点+校正非实测；实施期文本重写可能引入新增行，实际收益缩水（尤其候选二下缘） | 合并前 MUST 在实施 PR 内跑 `check-injection-budget --profile lightweight` 与 `--profile strict` 双档实测；验收以实测余量恢复 ≥100 tok 为准（DEC-268(2)）；不足则叠加另一候选补足 |
| BT-04 | **共注入假设被本地定制破坏**：用户本地删改 preset 的 agent-instructions 行会使 persona 指针悬空 | 指针行内置兜底句（「注入面缺失时——含平台不支持 agent-instructions 注入的情形（R0 F-7）——加载 skill 获取同等规则」）；`check-dsh-preset-compat` 已守护 persona 行结构与模板一致性（模板为唯一装配源）；假设本身在 §9 显式登记 |
| BT-05 | **第三档与次入口平台回归盲区**：候选二改薄指针模板，Codex/opencode 会话（无 persona/agent-instructions 的环境）自足性可能下降；standard 档仅靠 DEC-268(2) 记载未实测 | 压缩以「三检全保留」为硬约束（FEAT-037 保留清单逐项复核 + `validate_thin_pointer` 机检）；实施验收 MUST 三档（lightweight/standard/strict）全部实测 PASS，不只测 strict |

---

## 9. 非功能需求对应与影响范围

- **性能**：strict 余量 9 → ≈420（A）/≈574（A+B，R0 F-1 分量之和口径）（估算）；方向与 arch target 4K 一致；resident hard gate 仍是净增防护。
- **安全**：五不变量零触碰（§7.2 逐条声明）；guard 粒度差披露并给出加固路径。
- **可维护性**：bootstrap 操作面收敛到 `adapters/dsh/AGENTS.md.template` 单一维护点——bootstrap 变更不再需要 persona 双处同步（P-v1 P5/D4 对应）。
- **可扩展性**：指针模式可推广至未来新增 resident 表面（先单源、后指针投影）。
- **影响文件**：候选一 = `agent-presets/governance/agent.cordis.yml.template`（prefix 块）；候选二 = `commands/governance-init.md`（secondary-thin 模板块）+ `adapters/dsh/AGENTS.md.template`（L27-29）+ 狗粮工作区 AGENTS.md 投影（再生产物）。
- **机制边界（R0 F-7）**：persona 注入 = governance preset 装配注入（system prompt 位置）；agent-instructions 注入 = 工作区 AGENTS.md 宿主自动注入（workspace instructions 机制）——非 DSH 宿主复用该 preset 时后者机制不存在；§8 BT-04 兜底句（加载 skill）覆盖该情形。
- **循环依赖检查**：**不适用（无模块变更）**——本任务为注入文本的文档级瘦身，不新增/不改任何代码模块；两候选触及的守卫依赖方向不变（verify_workflow → checks/injection_budget、→ sync_entry_projection、→ behavior_profile 均为既有单向依赖，无环）。
- **可逆性**：两候选均为单 commit 可 revert 的可逆变更；投影幂等性由 `sync_entry_projection` 构造保证。

---

## 10. 后续动作

1. **Design Reviewer 审查（Coordinator 派发）**——本 ADR 为关键架构决策产出，MUST 经独立设计审查；审查重点：§3 候选完整性、§6 排除理由充分性、§7 契约核对无遗漏、§8 蓝军缓解可执行。
2. **用户裁决**（DEC-269③：架构方案产出后按关键决策交用户裁定）：选 A / A+B / 仅 B / 走重定标证据包路线 / 否决。
3. 裁决后立实施票（0.92.0）：按 §3 实施步骤执行；合并门 = 双档（建议三档）check-injection-budget 实测 PASS 且 strict 余量恢复 ≥100 tok + 全部 §7.3 守卫绿 + `check-dsh-preset-smoke`（隔离环境）通过；实测数字回写 evidence-log 取代本 ADR 估算。
4. Guard 加固票（可并入实施票或单列）：`check_injection_contract` 对 persona 改为注入块级断言（封堵 §7.3 粒度差）。
5. 回弹归因小票（可选）：对 EVD-1104→当前的 +25 tok 增量做逐表面历史 diff 归因，把 §1.1 的推断升级为实证。
6. 若用户选重定标路线：先产出真实 tokenizer 基准证据包（四表面实测 + 对照曲线），再立重定标 DEC——不得跳过证据直接抬限。

---

## 11. no-overclaim 声明

- 本 ADR 为**研究阶段**产出：**零实施、零预算恢复**——strict 当前仍为 5991/6000（余量 9 tok），本文一切「恢复至 ≈X」均为估算预演，不构成完成事实。
- 全部 token 收益为**估算**（手工清点+校正，±12% 区间），最终以实施 PR 的 check-injection-budget 实测为准。
- standard 档 5719 tok 来自 DEC-268(2) 记载，本阶段未实测；+25 tok 回弹归因为**推断**（已标注待验证）。
- 推荐意见不构成决策：方案选择权在用户（DEC-269③）；对外表述应为「已登记治理票并产出方案研究」，不得表述为「预算已恢复/问题已解决」。

---

## 12. 证据清单（引用文件 + 行号）

| # | 证据 | 位置 |
|---|------|------|
| E1 | 预算常数/三档/hard gate/表面表/计量口径/EVD-1104 基线 | `skills/software-project-governance/infra/checks/injection_budget.py` L44-46, L76-80, L107-168, L187-205, L213-262 |
| E2 | strict=基座+差异段拼接；薄指针方言锚；投影幂等 | `skills/software-project-governance/infra/sync_entry_projection.py` L36-40, L67-101, L118-165, L282-343 |
| E3 | 注入契约锚注册表（persona 14 锚等）+ 整文件检查实现 | `skills/software-project-governance/infra/verify_workflow.py` L6730-6789, L6886-6928 |
| E4 | 五安全不变量表 + 六发布面 + marker | `skills/software-project-governance/infra/behavior_profile.py` L95-152, L165-175 |
| E5 | 发布矩阵测试（逐面 marker/最富面全覆盖/模板 token 钉/DSH 方言） | `skills/software-project-governance/infra/tests/test_behavior_profile.py` L237-256, L268-302 |
| E6 | 升级门双写钉/A~E 序列钉/cleanup 删除面钉/归档 Step E 钉 | `skills/software-project-governance/infra/tests/test_verify_workflow.py` L9811-9832, L9872-9898, L9900-9917, L9919-9949 |
| E7 | 四个注入表面原文（拟删/拟压缩块的逐行依据） | `agent-presets/governance/agent.cordis.yml.template` L48-79；`commands/governance-init.md` L194-379, L381-386；`adapters/dsh/AGENTS.md.template` L1-38 |
| E8 | 裁决链（决策顺序/9 tok 措辞/验收指标/授权边界） | `.governance/decision-log.md` L207-211（DEC-265~DEC-269） |
| E9 | Coordinator 双档实测表（本任务 prompt 提供，2026-09-28 HEAD） | §1.1/§1.2 引用的全部数字 |

---

## 附 A：proposed decision-log entry 草案（Coordinator 写回；编号/日期由 Coordinator 定）

```markdown
| DEC-XXX | <今天> | Coordinator（FEAT-073 阶段 1 研究产出入账——ADR-020；方案待用户裁决） | FEAT-073 strict 注入预算治理阶段 1 完成：strict resident 5991/6000（余量 9 tok，2026-09-28 HEAD 实测）；ADR-020 产出 ≥2 个不损害契约的去重瘦身候选 + 重定标对照评估 | 候选一 A（persona↔agent-instructions 结构性单源化，估算净省 ≈411 tok）/ 候选二 B（薄指针层行内压缩，估算 ≈154 tok）/ 对照 D（重定标——现无真实 tokenizer 基准，不推荐）/ 已排除：A' 反向单源化、B' A~E→指针（4 测试族+升级确认门载体否决）、B2 升级门页脚删除（count==2 双写钉否决）、直接抬限（DEC-266(3) 禁止首择） | 待用户裁决（DEC-269③）——本条仅入账研究完成与推荐排序（A 为主、B 为辅） | FEAT-040 五安全不变量零触碰（ADR-020 §7.2 逐条声明）；锚核对矩阵覆盖 persona 14 锚/六发布面 marker/模板 token 钉；全部收益为估算（手工清点×0.88 校正，±12%），验收以实施票内双档实测 ≥100 tok 余量恢复为准 | docs/architecture/ADR-020-injection-budget-dedup-slimming.md；0.92.0 实施票（待立） | FEAT-073 | 已入账（研究阶段） | <裁决后复核> |
```

---

## 13. R0 findings 处置表（2026-09-28 修订）

> 审查报告：`docs/reviews/review-FEAT-073-R0.md`（APPROVED_WITH_NOTES / unresolved_blockers=0）。本表为修订留痕；状态行仍为 PROPOSED（研究产出语义不变，实施未开始）。

| ID | 级别 | 处置方式 |
|----|------|----------|
| F-1 | P2 | 已改 §5.4 + §2（并同步 §9 性能行同源数字）：A+B 行改为分量之和口径（5991−411−154≈5426，余量 ≈574），加注说明原 ≈5447/≈553 为中间舍入合成噪声（差异 21 tok，均满足 ≥100，不影响结论方向） |
| F-2 | P2 | 已改 §3.1：L59 压缩保留规格补入 `GOVERNANCE_LEGACY_BEHAVIOR=1` 与 `behavior_profile: legacy` 两 token，并注明 token 钉测试不覆盖 persona、实施须自查完整开关句 |
| F-3 | P2 | 已改 §3.1（取建议一）：新增文本补第一动作硬触发器命令句，与 §8 BT-01 缓解承诺（「首动作仍以命令句形态出现于 persona」）一致，BT-01 措辞无需改；新增行 ≈45 tok 落在候选一 ±12% 区间带内（下缘 ≈362，调整后净收益 ≈366），点估计不另调，以实施实测覆盖 |
| F-4 | P3 | 已改 §6：B' 行「四 needle」→「7 项 required needles」 |
| F-5 | P3 | 已改 §1.3（表行 + 关键结构性事实句）：共现措辞改为「同属 governance preset 适配层交付物（launch.py --install/--sync 单次装配同时交付 persona prefix 与 AGENTS.md 投影）」口径 |
| F-6 | P3 | 已改 §7.1：矩阵补一行「SKILL.md 11 锚 + references/behavior-protocol.md 3 标签锚——两候选零触碰」 |
| F-7 | P3 | 已改 §8 BT-04 + §9：缓解句补「（或平台不支持 agent-instructions 注入时）」；§9 补机制边界（persona=preset 装配注入 vs agent-instructions=工作区 AGENTS.md 宿主注入） |
