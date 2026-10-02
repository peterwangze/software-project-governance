# ADR-021: 元机制设计——M1 优先级执法底层机制 + M2 发现即闭环契约（DEC-288 Wave1）

- **日期**: 2026-09-29（初稿）；同日 R0 返工修订（review-DESIGN-021-DESIGN-R0.md §12 最小修复集 + Coordinator 三项 FEAT-077 B2 交付吸收输入）
- **任务**: DESIGN-021（P1——DEC-287/288 直接承载）
- **状态**: R0 返工修订版（待 R1 复审——同一 Design Reviewer，round+1，R0 报告路径为强制读取项）
- **决策可逆性**: M1-L1/L2 = 可逆（注入面文本与排序键可回退，guard 锚点同 commit 回退）；M1-L3 = 不可逆方向声明（字段位置定义，随 B-12/B-13 翻转生效，翻转本身有既有回滚协议）；M2 契约 = 可逆文本，M2 执法（渐进 FAIL）= 可逆（词集与姿态可调，违规台账不追诉历史）。
- **依据**: DEC-286(1)(2)(6)(7)、DEC-287(1)(2)(3)(5)、DEC-288（原文实读，`.governance/decision-log.md` L228-231 含 DEC-289 采纳记录）；`docs/reviews/review-DESIGN-021-DESIGN-R0.md`（NEEDS_CHANGE，P1×3/P2×5/P3×6——返工依据）；FEAT-077 B2 交付事实（模块层已合入，三处对齐见 §2.2.1/§2.2.4/§4 B3）；代码现状全部实读核对（见 §1.3 事实基线）。

---

## 1. 背景与问题

### 1.1 问题陈述（来自用户裁决，非转述重构）

DEC-286(7) 诊断：用户需求的优先级曾被机器自设信号（检查 FAIL / 风险窗 / 例外到期）**系统性压倒**，机制根因为四机制——闹钟不对称（机器闹钟有升级通道、用户项无守护）、颗粒不对称（机器信号天然可拆细票、用户结构性需求「装不进本批」被无限顺延）、报警只接机器痛、出身洗白（C 级软件化这类用户需求被记为 roadmap 后连续让位）。实证：0.86~0.92 七版自我修正占比病态（DEC-286(3)）。

DEC-286(6) 终态条款：零新账稳态下「登记待以后」状态废除，问题在触发点闭环；付不起触发点闭环成本的动作不开始。DEC-287(3) 重申：复评窗延期=违反总指令。

DEC-288 排序裁定：**(M1) 优先级执法底层机制**与 **(M2) 发现即闭环契约**必须最先落地并产生**可验证效果**，二者见效前不进入其余旧账清偿。

### 1.2 目标

1. **M1**：provenance（需求源）成为任务身份的一等字段，从注入契约→B 级执法→C 级生成四级梯度落地，使倒挂在每一层都成为可机检违规。
2. **M2**：DEC-286(1)(2)(6) 升格为关键行为契约条款 + 执法接线，「登记待以后」成为可检测、可计数、可阻断的违规态。
3. 本 ADR 自身过程内闭环：每项设计含验收判据与测试计划，无「后续完善」节。

### 1.3 事实基线（设计落点全部实读核对，2026-09-29）

| # | 事实 | 出处（实读） |
|---|------|------------|
| F1 | 关键行为契约现有四条（复审必达/完成必推荐/选项必带依据/真实环境必防护），canonical 投影在 SKILL.md「关键行为契约」节（L225-232），完整规则在 behavior-protocol.md M7.4/M7.7 | `skills/software-project-governance/SKILL.md` L225-232 |
| F2 | 注入契约锚点注册表 `INJECTION_CONTRACT_ANCHORS`（verify_workflow.py L6805-6845）守护四个注入面：`agent-presets/governance/agent.cordis.yml.template`（persona，最全锚集）、`skills/software-project-governance/SKILL.md`、`references/behavior-protocol.md`、`adapters/dsh/AGENTS.md.template`；`check_injection_contract()`（L6942）existence-only 判定 | verify_workflow.py L6786-6984 |
| F3 | resident 注入预算 = 6000 tok 硬门（FEAT-050/DEC-211③），strict profile 当前余量 **391 tok**（FEAT-073 优化 9→391）；校准口径：CJK 1 tok/char、ASCII ceil(chars/4)；resident 面 = persona prefix + 所选 profile 入口模板 + secondary-thin 薄指针 + AGENTS.md 载荷 | `infra/checks/injection_budget.py` L76-205；plan-tracker L11（0.92.0 版本行「余量 9→391 tok」） |
| F4 | `change_triage.run_triage()`（change_triage.py L1038-1233）为五步 triage 唯一机录入口：fail-closed（ERROR→`{"error":...}`，CLI exit 2）、记录不可变（re-triage 拒绝）、record schema 顶层键 + `analysis.*` 五步；additive 可选字段先例 = step e `analysis.side_effect`（FIX-271，schema_version 保持 1）；CLI thin entry 在 verify_workflow.py | change_triage.py L1038-1255 |
| F5 | `task_priority.TaskDep` frozen dataclass（L532-559）：`task_id/priority/status/dependencies/cross_entity_refs/target_version`；排序键 `_priority_sort_key`（L1272-1276）= `(priority, version_tuple, task_id)`；行解析 `_parse_task_row`（L1107-1198）ID-anchored（依赖列 = ID+2，`_ID_TOKEN_RE` 只提取 `PREFIX-NNN`，中文字 prose 不干扰解析）；CLI 编排 `run_cli_analysis`（L2127-2244） | task_priority.py |
| F6 | check-governance Check 族最新编号 = Check 39（R1 Completion Gate）；Check 33 = Injection Contract；Check 32 = Change-Control Triage；Check 34 = Completion Recommendation；聚合接线模式 = `cmd_check_governance` 内逐 Check 调用 + box 打印（L16806-17054 先例） | verify_workflow.py L16709-17054 |
| F7 | 发布准入聚合 `check_release_readiness`（L7201-7330）= 子检查列表（version_consistency/release_fact_source/.../release_lineage/gate interlock），新门以子检查函数接入 | verify_workflow.py L7201-7330 |
| F8 | write-guard 违规持久层 `write_guard_state.py`：五族（evidence/review/decision/task_status/ops_ledger，`FAMILY_VOCABULARY` L296）、`DETECTION_TYPE="unattributed_row_change"`（L270，状态机 type-agnostic——「violations of NEW types are a FEAT-064 extension point」，L156-157 原文）、face-5 检测新增行经 guard 基线 diff window（只看新增，存量不追诉） | write_guard_state.py L148-165, L270, L592-605 |
| F9 | FEAT-061 JSON 权威面已交付未激活（B-12/B-13 授权票，0.88 交付、0.90 M-8 注记「不随版翻转——RISK-059 未关闭」）；`governance_store.py` JSON record 已有 `provenance` 键 = **写入器机器溯源**（`{"op_id", "marker"}`，L1597/L1625）——与 M1「需求源」语义不同源 | governance_store.py L1541-1670；plan-tracker L284-285 |
| F10 | 并发约束：`verify_workflow.py` + `infra/tests/test_verify_workflow.py` 被 Developer 锁定——初稿时为 FIX-403，R0 返工时实查已**锁继承为 FIX-404**（缺陷族扫尾，TTL 14400s，FIX-403 锁已释放）；另 FEAT-077（M1-B2 批，Developer）锁 change_triage.py / task_priority.py / checks/provenance_domain.py / tests/test_task_priority.py / tests/test_change_triage.py。本 ADR 涉及锁内文件的一切改动标注「锁释放后实施」；本文统一以「verify 锁」指代 FIX-404 所持之锁 | `.governance/agent-locks.json`（2026-09-29 09:31 实查） |
| F11 | 复评窗机制现状：risk-log 活跃行普遍携带「下次复评 = {版本/事件}」顺延语义；DEC-282(4) 已立「EXC 到期不自动续期」先例 | `.governance/risk-log.md` L31-48 |
| F12 | DEC-287(5) 过渡期执法已在生效：「所有推荐/排序呈现必须逐项标注需求源〔用户点名/活性缺陷/机器信号〕，不标即违规」——L1 注入契约是该纪律的软件化固定 | decision-log L229 |

---

## 2. M1 设计——优先级执法底层机制（四级梯度）

### 术语与字段命名（先决裁决）

**字段名：`demand_source`**（三值枚举 `user-named` / `active-defect` / `machine-signal`）。

不复用 `provenance` 一词：governance_store.py 的 JSON record 已将 `provenance` 定义为写入器机器溯源（`{"op_id", "marker"}`，F9）——同一词两义是架构腐化（P-v1 D2），且 C 级两字段将在同一 record 内共存，必须异名。备选评估见 §6.1。

中文名沿用 DEC-286(7) 用户原词：用户点名 / 活性缺陷 / 机器信号。行内（md）标注格式：`〔用户点名〕`/`〔活性缺陷〕`/`〔机器信号〕`（全角方括号，与治理文本现有 `〔op-…〕` 锚风格一致）。

---

### 2.1 L1 注入契约级：「推荐必标需求源」第五条契约

**落地形态**：关键行为契约新增一条「推荐必标需求源」（以锚点关键词为锚，不用序数——persona 契约块现为五行〔含「审查结论必机录」，template L58-62 实证〕而 SKILL.md 节为四条，双面序数天然漂移；本条在 SKILL.md 面为第 5 项、persona 面为第 6 行，锚点关键词「推荐必标需求源」两面唯一即足）。

**逐字文本建议（canonical，behavior-protocol.md 携带全文；SKILL.md 携带压缩形式——FEAT-078 R0 F-2 消歧；R0 修订：倒挂禁令加同优先级限定，与 INV-1 判据及 §2.2.2 排序键三处自洽——F-P1-1）**：

> 5. **推荐必标需求源（DEC-286(7)/DEC-287(5)）**：凡向用户呈现推荐或排序（含完成必推荐的候选清单、交互询问工具中的待选清单、任务进度表摘要），MUST 逐项标注需求源（三类之一：用户点名、活性缺陷、机器信号），标注 MUST 可追溯到 triage 记录或用户原话；不标即违规。**同优先级内** user-named 项未闭合时，machine-signal 项不得排位其前（推荐位倒挂=违规，判据见 Check 41/INV-1；跨 P 级压序经 Check 41 披露 WARN + 发布门拦截，见 ADR-021 §2.2.3/§2.2.4）。

**压缩形式（persona / 入口模板携带；R0 修订：含同优先级限定）**：

> 5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源（用户点名、活性缺陷、机器信号三选一标注），不标即违规；同优先级内 user-named 未闭合时 machine-signal 不得排前（DEC-286(7)）。

**涉及文件**（四面同 commit，原子）：

| 文件 | 改动 | 备注 |
|------|------|------|
| `agent-presets/governance/agent.cordis.yml.template` | 契约块 +压缩行 | persona prefix 进 resident 预算 |
| `skills/software-project-governance/SKILL.md` | 关键行为契约节第 5 条（压缩） | |
| `skills/software-project-governance/references/behavior-protocol.md` | M7.4 附近新增 canonical 全文 + 最小契约投影句更新 | |
| `adapters/dsh/AGENTS.md.template` | 短指针行 | full-file 计价，用指针不复制全文 |
| `commands/governance-init.md` | Step 7 注入模板（canonical source——CLAUDE.md Bootstrap 变更纪律：先改此模板） | 三 profile 模板各加压缩行 |
| `skills/software-project-governance/infra/verify_workflow.py` | `INJECTION_CONTRACT_ANCHORS` 四面各加锚点 `"推荐必标需求源"`（persona 面另加 `"用户点名"`） | **锁释放后实施**（F10）；与注入面同一 commit，否则 check-injection-contract FAIL |

**代码量估算**：verify_workflow.py 锚点数组 +2 关键词/面 ≈ 8 行；其余为文本面。

**注入预算估算（硬约束，F3；R0 修订：压缩行计入「同优先级内」限定 6 CJK char——F-P1-1 措辞修正的预算代价）**：

| resident 面 | 增量文本 | CJK char | ASCII char | 校准 tok（CJK×1 + ASCII/4） | UTF-8 字节 |
|------------|---------|----------|-----------|------------------------------|-----------|
| persona prefix | 压缩行（含限定） | ~52 | ~22 | ~58 | ~178 B |
| entry template（strict 计价面） | 压缩行（含限定） | ~52 | ~22 | ~58 | ~178 B |
| secondary-thin 薄指针 | 极简指针（「推荐必标需求源——见 SKILL 关键行为契约」级） | ~16 | ~10 | ~19 | ~58 B |
| AGENTS.md 载荷 | 极简指针 | ~16 | ~10 | ~19 | ~58 B |
| **M1 合计（strict profile）** | | | | **~154 tok** | **~472 B** |

余量校验：391 − 154 = **~237 tok 余量**（M2 再消耗见 §3.1）。M1+M2 全部落地后 strict profile 余量估算 **~81 tok**（391 − 310，算式见 §3.1）——预算硬门（≤6000）通过；81 < 100 冻结线（验收判据 5）**落地即触发**：此后任何使 resident 余量下降的注入面变更必须先做等量瘦身。

**验收判据**：
1. `check-injection-contract` PASS（四面锚点在场——B1b 注册表与文本面满足「注册表 commit 不得先于文本 commit」序约束，见 §4 B1 拆分）。
2. `check-injection-budget --profile strict --fail-on-issues` PASS（resident ≤ 6000 tok）。
3. light/standard profile 同 PASS（三 profile 分开测量）。
4. `check-entry-bootstrap-sync` PASS（入口模板 canonical 与投影一致）。
5. **冻结线（机检形式）**：M1 落地后 resident 增量 ≤160 tok 且 M1+M2 合计增量 ≤320 tok（本 ADR 逐字文本的预算上界 + 容差；超出 = 文本被夹带扩充，拒绝）；此后若 `check-injection-budget` 实测余量 <100 tok，**禁止任何使余量下降的注入面变更**，除非同 commit 携带等量瘦身（防 BC-1 回弹——本项即 BC-1 缓解的验收承载）。**分档口径勘误（DEC-291，FEAT-079 落地裁定）**：上列 160/320 为本 ADR 估算值，实测低估了校准 tokenizer 对冻结文本的 CJK 计价——机检分档断言采用 DEC-291 校准线 **M1≤180 / M1+M2≤370**，且按 **per-surface 口径**逐面判超（四个 resident 面各自计价，四面合计仅披露不阻断——B1a 实测四面合计 ~711 tok，合计口径会误拒本 ADR 自身授权的契约文本）；常量承载于 `checks/injection_budget.py`（`CONTRACT_M1_BUDGET_TOKENS`/`CONTRACT_COMBINED_BUDGET_TOKENS`），后续调优只动常量不动逻辑。

**测试计划**：
- `infra/tests/test_injection_contract.py`（若存在既有套件则扩展）：负例——移除任一面任一锚点 → check FAIL；正例四面全锚 → PASS。
- `check-injection-budget` 三 profile JSON 输出断言 `tiers.resident.tokens ≤ 6000`，并断言增量分档：M1 批 ≤160 tok、M1+M2 批 ≤320 tok（防夹带，对应验收判据 5）。

**降级路径**：无降级——锚点守护本身 fail-closed（缺锚即 FAIL，现状语义不变）。注入预算超限 = 硬门 FAIL（FEAT-050），无 advisory 通道。

---

### 2.2 L2 B 级执法：四件（全部落在既有 CLI/Check/guard 骨架内）

#### 2.2.1 provenance 三值字段进 change-triage CLI（含写路径窗口协议与修订通道）

**落地形态（R0 修订：三层签名设计——库层缺省兼容 / CLI 层显式执法 / 修订层生命周期）**：

`run_triage()` 新增参数 `demand_source: str = "machine-signal"`（**带缺省默认值**）+ 可选 `demand_basis: str = ""`；record 顶层新增 `"demand_source"` / `"demand_basis"` 键（与 `title`/`priority` 同级——任务身份属性，不进 `analysis.*`）。CLI（verify_workflow.py thin entry，**verify 锁释放后**）加 `--demand-source` **必填**旗标（argparse required）+ `--demand-basis` 可选旗标——**库层缺省兼容、CLI 层显式执法**的分层：库层缺省保证锁内既有调用面（L24124 kwargs 全集）零 TypeError 且不违反 `run_triage` 的 Never-raises 契约（F4）；CLI 层必填保证 B3 后人工路径不可漏标。

**校验规则（fail-closed；R0 修订：缺失不再报错——缺省走 machine-signal，仅显式非法值 fail-closed）**：
- `demand_source` 值不在三枚举（`user-named`/`active-defect`/`machine-signal`）→ `{"error": ...}`，exit 2，零写入（复用既有 fail-closed 模式）。
- `demand_source="user-named"` 时 `demand_basis` 必填（防 BC-4 出身洗白：user-named 判定必须可追溯——用户原话引用 / DEC 引用 / 会话记录锚）。缺失 → exit 2。
- **P2 + user-named 拒绝（R0 返工补入——FEAT-077 任务规格已实现该条款，本 ADR 正式收编并给出依据）**：`demand_source="user-named"` 且 `priority="P2"` → 拒绝（fail-closed，exit 2，error 提示「user-named 项禁用 P2（DEC-286(7) 入账默认 P1）；确需降级：以 P0/P1 入账后经用户显式裁决（DEC 入账）调整任务行 P 值」）。依据：①DEC-286(7) 明文「user-named 入账默认 P1」——P2 不是该类项的合法入账态；②**执法绕过向量封堵**：user-named P2 会使同 P 级 tie-break 保护失效（P2 档内几乎无竞争），同时被 P1 machine-signal 压制属跨级压序（INV-X 仅 WARN、发布门为低频终端拦截）——「标 P2」将成为把用户项合法压到机器信号之下的最短路径，恰是 M1 要防的倒挂以降级形态复活。降级合法性不否认（用户有权定优先级——「期限由用户定」），但降级是关键决策（M5.3），MUST 经显式通道（DEC + task 行调整）而非入账默认可达。
- **user-named 默认 P1 联动（F-P3-3，DEC-286(7)「入账默认 P1」机化）**：CLI 层 `--demand-source user-named` 且未显式传 `--priority` → 默认 P1 并在 CLI 输出与 record `analysis.priority_context` 中标注「DEC-286(7) user-named 缺省 P1」；其余 demand_source 下 `--priority` 仍必填（既有行为）。

**写路径窗口协议（F-P1-2；Coordinator 已裁定，本节写死——实现者不得自由发挥）**：

- **窗口成因**：`run_triage` 为 keyword-only 签名且契约 Never-raises（F4）；其唯一 CLI 调用面在 verify 锁内的 verify_workflow.py。B2（模块层，未锁）先行合入而 B3（调用面，锁内）未跟随时，存在一个**写路径真空窗**——锁内 CLI 无法传新参。
- **窗口协议（三条规定）**：
  1. **缺省默认 machine-signal**：窗口期内经锁内 CLI 入账的所有新 triage 落 `demand_source="machine-signal"`（库层缺省值）。保守归类不产生倒挂误判（machine-signal 在 `_DEMAND_RANK` 中排序最低位，不会被误抬高）；与 DEC-286(7)「机器自设」保守归类的精神一致——宁低抬不高。
  2. **非法值 exit 2**：窗口期与常态一致，显式非法值（API 调用方传入）fail-closed，无窗口豁免。
  3. **B3 接线点更新即窗口关闭**：B3 合入 `--demand-source` 必填旗标后，CLI 路径不再可能缺省；窗口起止 = B2 模块合入（起）→ B3 调用面合入（止）。
- **窗口期补救路径**：窗口期内用户点名的任务（被缺省记为 machine-signal）经**修订通道**（下节）补标为 user-named——修订通道库函数随 B2 同批交付（change_triage.py 未锁），窗口期内 Coordinator 经库级 API 调用执行修订（机写 evidence 留痕）；CLI 旗标（`demand-source-revise`）B3 规范化。
- **代价声明**：窗口期非 user-named 例行任务无需动作；user-named 任务有一次修订补标成本——由 Coordinator 在窗口期主动执行（新任务入账时若知晓用户点名，直接经库级 API 传参而非依赖缺省），残余漏标由 Check 41 覆盖率披露兜底。

**demand_source 修订通道（F-P1-3；append-only 事件流——triage 记录不可变原则不破）**：

- **存储形态**：`.governance/change-triage/{TASK_ID}.demand-revisions.jsonl`——append-only 事件流，每行一个修订事件。不触碰不可变的 triage record 本体；`.jsonl` 后缀天然不被 `load_triage_records` 的 `glob("*.json")` 误读（F4）。
- **事件 schema**：`{"event_id", "task_id", "from", "to", "basis_kind": "user-quote|dec-ref|session-record", "demand_basis", "revised_by", "revised_at"}`——`from` 由写入器从当前 resolve 结果自动派生（调用方不传，防伪造起点；派生域=写入器可及域：最新修订事件 > triage record——行内标注属 plan-tracker md 面，由 tpa 层消费，不在写入器派生域内，FEAT-077 R1 P3-1 消歧）；`to` 必须是三枚举之一；`demand_basis` 必填非空（修订即重新主张需求源，溯源义务与初次标注相同——BC-4 防造假属性不损失：事件不可变 + 带溯源 = 审计链）。
- **写入校验（fail-closed）**：目标 task_id 必须已存在 triage record（对不存在的任务修订 → exit 2）；`to` 非法 → exit 2；basis 缺失 → exit 2。
- **resolve 语义（取最新有效事件）**：§2.2.2 权威链更新为 **最新修订事件（如有）> triage record `demand_source` > 行内标注 > legacy**。有修订事件时，record/行内的旧值是历史快照，**不构成 conflict**（合法漂移通道）；行内标注与 resolve 终值不一致 → WARN 提示同步行内（不 FAIL——事件流才是权威）。conflict（FAIL）仅指**无修订事件时** triage record 与行内标注的未声明矛盾（原语义保留）。
- **使用场景（DEC-286(7) 核心场景的机器表达）**：用户事后点名一个 active-defect 任务 → 修订事件 `to=user-named, basis_kind=user-quote` → 下次分析权威翻转为 user-named——「用户升级需求源」这一正向漂移从「不可表达/永久 conflict」变为一次可审计的机录动作（R0 RT-1 红队场景闭环）。

**涉及文件 / 代码量**：
- `infra/change_triage.py`：`run_triage` 签名 +2 参数、校验 ~20 行、record +2 键、user-named 默认 P1 联动 ~8 行、修订通道（校验/追加/读取/resolve 集成）~65 行 ≈ **95 行**（未锁——FEAT-077 承载）。
- `verify_workflow.py`：change-triage 子命令 argparse +2 旗标（必填 demand-source）+ `demand-source-revise` 子命令 ≈ **18 行**（**verify 锁释放后实施**）。

**向后兼容**：既有 ~199 个 triage 记录（`change-triage/*.json` 实查）无该字段——记录不可变（F4），消费者（Check 32/41、task-priority 联查）按「缺失 = 未标（legacy）」处理，只对新记录强制。

**验收判据**：
1. **锁内 CLI 兼容性判据（窗口协议核心，F-P1-2）**：模拟锁内调用面（kwargs 不含新参，即 B2 合入后、B3 合入前的调用形态）调用 `run_triage` → 成功返回、record 落 `demand_source="machine-signal"`、无 TypeError、无 error dict——Never-raises 契约保持。
2. 显式传入非法值 → exit 2 零写入；`--demand-source user-named` 缺 `--demand-basis` → exit 2。
3. `--demand-source user-named` 缺 `--priority` → 默认 P1 + record 标注「DEC-286(7) user-named 缺省 P1」。
4. 合法调用 → record 含 `"demand_source"` + `"demand_basis"` 顶层键，evidence 行（`TRIAGE-{task}`）description 追加 `〔{中文需求源}〕` 标注。
5. 修订通道：对已有任务追加修订事件（to=user-named + basis）→ `.demand-revisions.jsonl` 新增一行；resolve 终值翻转；record 本体字节不变；对无 record 任务修订 → exit 2；无 basis → exit 2。
6. 既有记录 JSON 全量 parse 零破坏（schema additive，`TRIAGE_SCHEMA_VERSION` 保持 1——`analysis.side_effect` 先例）；`load_triage_records` 不误读 `.jsonl`。

**测试计划**（`infra/tests/test_change_triage.py` 扩展，FEAT-077 锁内承载）：
- 窗口协议三例：缺省 → machine-signal 落盘无异常；非法值 → error dict；user-named 缺 basis → error dict。
- 默认 P1 联动正/负例。
- 修订通道五例：合法修订/无 record/无 basis/非法 to/事件后 resolve 翻转 + record 不变性（字节比对）。
- 旧 fixture（无 demand_source 的既有记录样例）加载联查 → 判定 `legacy`，不抛异常。

#### 2.2.2 task-priority-analysis 排序加权

**落地形态**（`infra/task_priority.py`，未锁）：

1. `TaskDep` 新增字段 `demand_source: str = "legacy"`（frozen dataclass 带默认值——位置参数构造兼容；值域 `user-named`/`active-defect`/`machine-signal`/`legacy`）。
2. 行内标注解析：`_parse_task_row` 后处理——正则 `〔(用户点名|活性缺陷|机器信号)〕` 扫描整行原始 cells（依赖列或状态列均可携带；`_ID_TOKEN_RE` 不受中文字影响，F5，解析零回归）。
3. **权威裁决（R0 修订：修订事件感知，F-P1-3）**：`最新修订事件（如有）> triage record demand_source > 行内标注 > legacy`。纯函数 `resolve_demand_source(task_id, row_marker, triage_records, revision_events)`：存在合法修订事件 → 取最新事件 `to` 值为权威（record/行内旧值 = 历史快照，不构成 conflict，行内不一致 WARN 提示同步）；无修订事件时 triage record 有 `demand_source` → 权威；否则行内标注；无修订事件且 record 与行内标注同时在场且冲突 → 返回 `"conflict"`（调用方报 FAIL 级 issue——conflict 仅指**未声明修订的矛盾**，数据一致性 fail-closed）。联查 I/O 沿 CLI 编排层（`run_cli_analysis` 调 `change_triage.load_triage_records` + 修订事件读取，与 FIX-341 archive 联查同层——纯函数 purity 契约不破）。
4. **排序键扩展**（`_priority_sort_key`）：

   ```python
   _DEMAND_RANK = {"user-named": 0, "active-defect": 1, "machine-signal": 2, "legacy": 0, "conflict": 0}
   def _priority_sort_key(task):
       return (task.priority, _DEMAND_RANK[task.demand_source],
               _version_tuple(task.target_version), task.task_id)
   ```

   **provenance 排在 priority 之内作第一 tie-break（同 P 级内 user-named > active-defect > machine-signal），不跨 P 级**（R0 修订措辞，F-P1-1③）。理由：P0 语义 = 阻断门禁/主流程（多为 active-defect），跨级压制会把 user-named P1 结构性需求抬到 P0 阻断热修之上，制造新倒挂。**跨级压序（machine-signal P0 排在 user-named P1 之前）的执法归属：Check 41 披露 WARN（INV-X，§2.2.3）+ 发布门拦截（§2.2.4）——排序键不跨级、跨级不归排序键管**；分级执法，各级不越权。`legacy` 与 `user-named` 同 rank：存量未标行保守视为用户/Coordinator 点名（历史行的产生无机器自设通道占比假设成立——DEC-286(7) 诊断的是排序压倒而非出身造假普遍化），同时报告面显式披露 legacy 清单（WARN，倒逼补标）。**此为裁决点 D1（§7），最终裁决归 Coordinator/用户。**
5. **D1 已知边界（残留风险，R0 显式披露——F-P1-1⑤）**：DEC-286(7) 明文「机器自设期限与用户点名项冲突时**撤机器闹钟**而非压用户项」。按其分类学，machine-signal 即「旧账」，一个 machine-signal 项占据 P0 位本身即机器自擢升——(7) 命令撤销的对象。D1 设计下推荐位无「撤闹钟」的自动机制：machine-signal P0 仍压 user-named P1 于推荐序列，仅经 Check 41 WARN 披露与发布门终端拦截。容忍理由：真阻断缺陷应分类 active-defect（其 P0 位正当）；自动撤销 P0 会破坏「阻断即最高」的门禁语义且需语义分类器（超出确定性执法边界）。该张力的完整消解（推荐位撤闹钟机制）**不在本 ADR 范围**——由 Coordinator/用户知情持有；若实证出现 machine-signal 滥用 P0 位，补救路径 = 修订通道改其 demand_source 或降 P（经 DEC 入账）。
6. 渲染：`_format_task_line` 追加 `src={demand_source}`；`format_report` 头部追加 provenance 分布行（`user-named:N active-defect:M machine-signal:K legacy:L`）。

**涉及文件 / 代码量**：`task_priority.py` ≈ **75 行**（字段 5 + 正则常量与解析 15 + 联查纯函数（修订事件感知）25 + 排序键 8 + 渲染 12 + `__all__`/docstring 10）；`change_triage.py` `_report_to_json` +1 键 ≈ 2 行。

**验收判据**：
1. 构造 fixture：同 P1 三任务（user-named/machine-signal/legacy 无标注）→ `recommended_next` 顺序 user-named/legacy 在 machine-signal 前。
2. 无修订事件且行内标注与 triage JSON 冲突 → report 含 conflict issue，排序按 user-named 保守处理 + 显式披露；存在修订事件 → 以事件 `to` 为权威终值，旧值不触发 conflict（行内不一致仅 WARN）。
3. 现有全量测试零回归（`TaskDep` 默认值保证既有构造点不破坏；`test_verify_workflow.py` 相关面**verify 锁释放后**跑全量）。
4. DEC-288 M1 生效判据半项：「排序含 provenance 加权」——`--format json`（若 CLI 支持）/ report_text 含 provenance 分布行 + 每行 src 标注。

**测试计划**（`infra/tests/` 新文件 `test_demand_source_priority.py`，未锁）：
- 排序矩阵测试：3×4（P0/P1/P2 × 四 demand_source）全排列序断言。
- 联查权威测试（R0 扩展，F-P1-3）：同任务行内 vs JSON vs 修订事件组合（一致/仅行内/仅 JSON/未声明冲突/有修订事件覆盖/修订后行内滞后）六例。
- `_ID_TOKEN_RE` 回归：依赖列含 `〔用户点名〕` 中文字 → ID 提取结果与无标注时 byte-identical。
- legacy fixture（截取现有 plan-tracker 三行）→ legacy 判定 + 分布行披露。

#### 2.2.3 反倒挂 Check（新 Check 41: Priority Inversion Guard；R0 编号重定，F-P3-4/RT-4）

**编号重定说明**：初稿用「Check 40」——R0 实证 Check 40 是 **FIX-310 退役编号**（旧 check-dsh-skills-manifest，`infra/tests/test_registry.py` L69-72 注释），编号虽空闲但复用使 `grep Check 40` 同时命中三个语义世界（退役 manifest guard / verify_workflow.py L17105 stale 注释 / 新检查）——六个月后的故障排查付出可避免的混淆成本（RT-4）。**重定：反倒挂 = Check 41，会话闭环率 = Check 42（§3.2.3）；编号来源 = Check 39（R1 Completion Gate，verify_workflow.py L17054 实证）为最新在用编号，40 跳过不复用，41/42 为下一可用连续编号。B3 批附带清理 L17105 处以现在时引用旧 Check 40 的 stale 注释（改为历史时态或删除）。**

**落地形态**：新函数 `check_priority_inversion(governance_dir=None)`（建议放 `infra/checks/` 新域模块 `checks/provenance_domain.py`——ArchGuard R1 主文件预算纪律，同 snapshot_domain/gate_domain 先例），`cmd_check_governance` 接线为 **Check 41**（verify_workflow.py 接线 **verify 锁释放后实施**）。

**机器判定规则（确定性，非语义；R0 修订：INV-1 加 same-priority 限定 + 新增 INV-X 跨级披露，与排序键 D1 三处自洽——F-P1-1①②）**：

输入 = task-priority-analysis 结果（含 demand_source）+ plan-tracker 解析。`recommended_next` 为全量 unblocked 跨 P 级排序列表（F5 实证 task_priority.py L1696/L1714）。

- **INV-1（推荐位倒挂，FAIL）**：`recommended_next` 列表中存在 machine-signal 项 M 与 user-named 项 U，**M.priority == U.priority（同 P 级）**，且 M 排在 U 之前。同 P 级限定与 §2.2.2 排序键（provenance 仅作 P 级内 tie-break）一致——排序键正确时本判据恒不触发，触发即排序实现缺陷或手写推荐绕过，两者都该 FAIL。**第三形态（FIX-406 P3-3 收编，B4-2 落地）**：M 与 U 的 P 级**均已解析**且 M 的 P 级严格更低（如 M=P2 排 U=P1 前）——排序键正确时同样不可能（P1 恒先于 P2），归 INV-1 FAIL（`checks/provenance_domain.py` else 臂拆分：已解析乱序 FAIL / 未解析保守 WARN——无法证明级序时只披露不阻断）。
- **INV-X（跨级压序，WARN——披露不阻断）**：`recommended_next` 中存在 machine-signal 项 M 与 user-named 项 U，M.priority 严格高于 U.priority（数值更小，如 M=P0/U=P1），且 M 排在 U 之前 → WARN 列出行对 `{M}（machine-signal,P{i}）压序 {U}（user-named,P{j>i}）`。跨级压序是 D1 设计的**已知容忍**（§2.2.2 第 5 点 D1 已知边界）：排序键不跨级，执法归属 = 本 WARN 披露 + 发布门终端拦截（§2.2.4）。
- **INV-2（可执行性倒挂，FAIL）**：存在非 completed、依赖已满足（unblocked 资格）的 user-named 项 U 因状态标记被滤入 `non_executable`，同时 `recommended_next` 非空且全部为 machine-signal——「用户项被停放而机器项占据全部推荐位」（DEC-286(7)「结构性大需求不得因装不进本批无限顺延」的可机检近似）。

**分阶段 fail-closed（防 BC-2 存量海瘫痪）**：
- 全库 demand_source 覆盖率（已标/可解析任务数）= 0 → **SKIP + WARN**（披露「provenance 标注覆盖率 0——DEC-287(5) 过渡期执法未落地」）。
- 覆盖率 > 0 → INV-1/INV-2 命中即 **FAIL**（check-governance `--fail-on-issues` exit 非 0）；INV-X 恒 WARN。
- `conflict` 数据存在（无修订事件的未声明矛盾，§2.2.2）→ FAIL（数据一致性优先于排序判断）。

**涉及文件 / 代码量**：`infra/checks/provenance_domain.py` 新文件 ≈ **125 行**（INV-1/INV-X/INV-2 判定 70 + 渲染 25 + argparse/CLI 面 30——模式同 `checks/injection_budget.py`）；verify_workflow.py 接线（Check 41 box + CMD 表 + L17105 stale 注释清理）≈ **17 行（verify 锁释放后）**。

**验收判据**：
1. 构造同级倒挂 fixture（同 P1 内 machine-signal 排 user-named 前）→ check FAIL，issue 含行对 `{M} 排位高于 {U}`。
2. 构造跨级情形（machine-signal P0 排 user-named P1 前）→ **WARN 不 FAIL**，issue 披露行对（INV-X——F-P1-1 判据面验收）。
3. 无倒挂 + 覆盖率>0 → PASS。
4. 覆盖率 0 → SKIP + WARN（不 FAIL）。
5. DEC-288 M1 生效判据另半项：「反倒挂 Check 在场」——check-governance 输出含 Check 41 box。

**测试计划**：`infra/tests/test_provenance_domain.py`（未锁，随域模块先行）：INV-1 正/负例（含同 P 级边界）、INV-X WARN 正/负例、INV-2 正/负例、覆盖率 0 SKIP、conflict FAIL、与 task-priority 集成（真实 plan-tracker 文本 fixture）。

#### 2.2.4 版本准入门（provenance release gate）

**落地形态**：新纯函数 `check_provenance_release_gate(plan_tracker_text, triage_records, release_version)`（放 `checks/provenance_domain.py` 同文件），接入 `check_release_readiness` 聚合子检查（F7 模式：`details["provenance_release_gate"]` + issues 前缀 `provenance release gate:`）。

**机器判定规则**：
- 收集 `demand_source="machine-signal"` 且 `target_version == release_version` 且 plan-tracker 行非 completed 的任务集 MS。
- 收集 `demand_source="user-named"` 且非 completed 的任务集 UN（不限版本——结构性大需求不得因版本边界隐形顺延）。
- **FAIL 条件**：MS 非空 ∧ UN 非空 → FAIL，issue 逐对列出 `{MS 项}（machine-signal）载入 {V} 而 user-named {UN 项} 未闭合`。
- 例外通道：UN 项的 target_version 明确 > release_version（用户已知悉的显式改期，DEC-286(7)「或显式请用户改期」）→ 不计入 UN。**改期判定语义（R0 返工注记——FEAT-077 B2 实现对齐）**：豁免判定使用**严格 semver 解析**（非裸 `X.Y.Z` → None，`_parse_semver` 口径），**禁止**依赖 `task_priority._version_tuple`——后者对未版本化输入返回 `(inf, 0, 0)` 哨兵（「sorts last」设计意图），若用于豁免判定会把未版本化 user-named 项误判为「改期至无穷远」从而静默豁免——未版本化（「未规划版本」/「—」）**不构成豁免**，该项留在 UN 内经 FAIL→remediation 排期交互处置（与 F-P2-3 常态性设计一致：未排期 = user-named 默认态，豁免必须显式且可解析）。无 triage 记录的任务（理论上不可能——Check 32 门禁，但存量窗口期）→ 该任务视为未申报，**FAIL**（fail-closed：版本载荷的 provenance 不完整即拒绝发布）。**窗口协议衔接（§2.2.1）**：写路径真空窗内经缺省入账的任务已携带 `demand_source="machine-signal"`，属「已申报」——不触发未申报分支，但其 user-named 补标经修订通道完成后进入 UN 集合正常执法。

**常态性与 remediation 协议（R0 修订，F-P2-3）**：DEC-286(7)「入账默认 P1+期限由用户定」意味着**未排期是 user-named 项的常态默认态**——因此「版本载 machine-signal 工作 ∧ 存在未排期 user-named」的 FAIL 在过渡期是**常态触发**而非异常。这是设计意图（显式改期正是 (7) 原意的落实时机），但 MUST 配交互协议防止 FAIL 沦为噪音：**FAIL issue 附带 remediation 说明**——一次 AskUserQuestion 批量呈现未排期 user-named 清单，用户逐项选择「排期至本版 / 显式改期（target_version > 本版，豁免通道）/ 本版前必须闭合（升级 P）」；决策结果经修订通道或 CLI 落机录（排期/改期即 demand 生命周期事件），重跑发布门即收敛。不采用「首版 WARN→FAIL 渐进」：发布门是低频高杠杆点，渐进会让「结构性大需求无限顺延」在过渡期继续发生——恰是 (7) 要防的。

**涉及文件 / 代码量**：`checks/provenance_domain.py` +65 行（判定 45 + remediation 提示渲染 20）；`check_release_readiness` 接线 +12 行（**verify 锁释放后**）；release CLI（`stage-release check-release` 路径）无需新旗标（聚合自动获得）。

**验收判据**：
1. 版本载未闭合 machine-signal + 存在开放 user-named → `check_release_readiness` FAIL，issue 含 remediation 提示（未排期清单 + 三选项指引）。
2. user-named 全闭合或全部显式改期（target_version > 本版）→ PASS。
3. 无 triage 记录的版本载荷任务 → FAIL（未申报分支）。
4. DEC-287(1) 场景回归：C 级软件化（user-named）未闭合时，任何载 machine-signal 工作的版本无法过发布门。

**测试计划**：域模块单测（四情形含 remediation 提示断言）；`test_verify_workflow.py` 发布门集成测试**verify 锁释放后**补（聚合 details 键断言）。

---

### 2.3 L3 C 级终态方向：队列由类型化数据机器生成（只定义字段位置，不设计实现）

**与 FEAT-061 存储切换协议层衔接（不重复设计存储层）**：

1. **JSON record 字段位置**：任务类记录（未来 task store——decision store 的 record 形制先例：`{"id","shape","cells","row_raw","source_line","provenance","date",...}`，F9）新增三个可选键：
   - `"demand_source"`: `"user-named" | "active-defect" | "machine-signal"`（三值枚举，与 L2 同名同域——md/JSON 双面同语义）
   - `"demand_basis"`: string（溯源依据）
   - `"demand_source_revisions"`: array（R0 新增，F-P1-3）——修订事件数组的 JSON 投影（事件 schema 同 §2.2.1 修订通道；L2 的 `.demand-revisions.jsonl` 事件流在 L3 收敛为 record 内数组，md 侧事件文件随翻转退役，resolve 语义「取最新有效事件」不变）
   - **禁止**写入既有 `provenance` 键（该键保留给写入器溯源 `{"op_id","marker"}`——两键在同一 record 并存，语义分工：`provenance`=谁写的，`demand_source`=为谁而做）。
2. **md 投影兼容**：JSON 权威面激活（B-12/B-13 翻转）后，plan-tracker 投影渲染行内 `〔用户点名〕` 标注由 `render_markdown` 侧行级重放保证（md 面的 L2 解析规则不变——双面同一事实源，投影只是渲染）。
3. **队列生成终态**：task-priority-analysis 从「解析 md 表」演进为「读 JSON 权威面生成」——本 ADR 只声明：届时 `parse_task_dependencies` 的 demand_source 解析层（§2.2.2 第 2/3 点）被「JSON 直读」替换，`_priority_sort_key`/Check 41/发布门/渲染层**零改动**（消费的是已解析的 `TaskDep.demand_source`，数据源替换对下游透明）。这一接口不变式是 L2 设计的约束条件，也是 L3 不需要新设计的理由。
4. **激活前置**：B-12/B-13 翻转授权（DEC-287(1) 列为清偿轮一等公民）→ FEAT-076 读取契约闭合（DEC-282(2) 五条件）→ demand_source 字段随首版 task store schema 冻结进 JSON 面。

**代码量**：0（本 ADR 不含 L3 实现；字段位置声明由 B-12/B-13 承载票的 schema 冻结动作兑现）。

**验收判据（方向性，随承载票兑现）**：task store 首版 schema 含 `demand_source`/`demand_basis` 键定义与三值枚举约束；`_priority_sort_key` 等下游零改动回归通过。

**测试计划**：随 FEAT-076/B-12 承载票（本 ADR 不立测试面——避免「为本条立新项目」违反 DEC-286 执行注记）。

---

### 2.4 L4 降级路径（各级不可用时的行为，fail-closed vs fail-open 及理由）

| 层 | 不可用情形 | 行为 | 理由 |
|----|-----------|------|------|
| L1 锚点守护 | 锚点缺失/文件缺失 | **fail-closed**（FAIL，现状语义） | 注入面是契约存在性的唯一保证；fail-open = 契约可被静默移除 |
| L1 注入预算 | 超预算 | **fail-closed**（硬门 FAIL，FEAT-050） | 预算不守护则瘦身必然回弹（AUDIT-154 诉点 3 原文） |
| L2 triage | `demand_source` 显式非法值 | **fail-closed**（exit 2 零写入；R0 修订：缺省走 machine-signal 不再报错——窗口协议，§2.2.1） | 库层缺省兼容保 Never-raises 与锁内调用面；显式非法值放行 = 出身洗白通道重开（DEC-286(7) 四机制之一） |
| L2 写路径窗口 | B2-B3 间锁内 CLI 无法传参 | **缺省 machine-signal**（Coordinator 裁定，§2.2.1 窗口协议） | 保守归类不抬高排序；user-named 补标经修订通道；窗口代价已声明并由覆盖率披露兜底 |
| L2 tpa 联查 | triage JSON 损坏/不可读 | **fail-open to 行内标注**（JSON 层降级，行内标注仍可解析；两者皆无 → legacy） | md 优先落地（DEC-287 约束）保证单面可用即工作；排序降级不阻断分析输出（分析是纯函数，F5）——但 conflict（无修订事件的未声明矛盾）**fail-closed**（数据一致性高于可用性） |
| L2 Check 41 | provenance 覆盖率 0 | **SKIP + WARN**（分阶段 fail-closed） | 存量 ~199 记录无标注，立即 FAIL = 清偿轮自瘫痪（BC-2）；覆盖率 >0 即严格执法，过渡窗口由标注覆盖率单调收紧 |
| L2 发布门 | 版本载荷任务无 triage 记录 | **fail-closed**（FAIL=未申报） | 发布门是最后一道；Check 32 已强制新任务 triage，缺记录只可能是绕过或存量异常，两者都应被拦 |
| L3 | B-12/B-13 未翻转（现状） | **N/A**（L3 本身是终态方向，无运行时依赖） | L2 全部能力已在 md 面自足（DEC-287「md 优先落地」约束的兑现） |
| M2 词集检测 | 检测器异常 | **fail-closed**（face-5 沿线：检测器自身错误 = loud disclosure，不静默跳过——write-guard R6 同精神） | 检测失效静默 = 「登记待以后」回归不可见 |
| M2 Check 42 指标 | session-snapshot 缺失/损坏（R0 新增，F-P3-6） | **SKIP + WARN 披露**（不 FAIL）：当日无新增问题行 → SKIP（无观测义务）；有新增问题行但 snapshot 不可用 → WARN 披露并按日聚合降级（§3.2.3 窗口函数） | 指标不可算 ≠ 违规发生；SKIP+WARN 与 M2 检测器的 fail-closed 不对称是有意的——前者是观测数据缺失（保守披露），后者是检测机制自身故障（必须响亮） |

---

## 3. M2 设计——发现即闭环契约（三件）

### 3.1 契约文本（DEC-286(1)(2)(6) 压缩为关键行为契约条款）

**与 M1 同面承载**（关键行为契约新增一条「发现即闭环」——锚点关键词制，同 §2.1 修订：SKILL.md 面为第 6 项、persona 面为第 7 行，序数仅描述；四面注入与 governance-init 模板同步，同 §2.1 模式）。

**逐字文本建议（canonical）**：

> 6. **发现即闭环（DEC-286(1)(2)(6)）**：问题在其触发点当场闭环——检查 FAIL 任务内修、审查发现即改即合、风险发现即决（终局三选一：关闭/收窄/升级，「维持待复评」非法）、证据随任务沉档、发布即结账。每个动作当场付清全部闭环成本；「登记待以后」状态废除——新增问题行携带待以后语义 = 可检违规。付不起触发点闭环成本的动作不开始。

**压缩形式（persona / 入口模板）**：

> 6. **发现即闭环**：问题在触发点当场闭环（FAIL 即修/发现即改/风险即决/发布即结账）；「登记待以后」=违规；付不起闭环成本的动作不开始（DEC-286）。

**注入预算估算（续 §2.1 表）**：

| resident 面 | CJK char | ASCII char | 校准 tok | UTF-8 字节 |
|------------|----------|-----------|----------|-----------|
| persona 压缩行 | ~58 | ~16 | ~62 | ~190 B |
| entry template（strict） | ~58 | ~16 | ~62 | ~190 B |
| secondary-thin 指针 | ~14 | ~8 | ~16 | ~50 B |
| AGENTS 指针 | ~14 | ~8 | ~16 | ~50 B |
| **M2 合计** | | | **~156 tok** | **~480 B** |

**M1+M2 合计 resident 增量 ≈ 310 tok**（M1 154〔R0 重算，含同优先级限定〕+ M2 156）；strict 余量 391 − 310 = **~81 tok**（≥0，过预算硬门；81 < 100 冻结线落地即触发，机检形式与防夹带分档断言见 §2.1 验收判据 5——R0 修订：消除初稿 87/93 残稿不一致，统一 81）。

### 3.2 执法接线

#### 3.2.1 写入时校验（write-guard 扩展：新增行族闭环标记检测）

**落地形态**：write-guard **face-5 引擎**（verify_workflow.py L23235-23474 区域——**锁释放后实施**）在受管行族新增行检测中追加一类语义检测；`write_guard_state.py` 状态机零改动（type-agnostic 设计，F8——`DETECTION_TYPE` 常量旁新增平行常量即可）。

**机器判定规则（确定性正则词集，M5.1b 先例——非语义猜测；R0 修订：否定语境窗口由 §7 BC-3 升入本规范为第四要素，F-P2-4）**：

- **检测对象**：guard 基线 diff window 内的**新增行**（存量行不追诉——guard 现有窗口语义天然满足；这是选 write-guard 而非独立全量扫描 Check 的决定性理由，备选评估见 §6.2）。
- **行族范围**：evidence（EVD- 行）、task_status（plan-tracker 任务行）。**豁免行族**：decision（DEC- 行——裁决原文引用「登记待以后」字样是记录治理事实，不是实施该行为；DEC-286/287/288 自身即含此词）、review（REVIEW- 机录行）、ops_ledger（receipt 机器行）。豁免清单是裁决点 D3（§7）。
- **词集（首个版本，可随台账数据调优）**：`待以后`、`后续处理`、`后续完善`、`待后续`、`留待`、`择期`、`登记待`、`待收尾`、`留池`、`候选池`、`下版处理`、`延后处理`、`0.9[4-9]\s*池`。
- **否定语境窗口（第四判定要素，规范级；方向消歧 DEC-301：双向）**：命中词**前或后 8 个字符**内含 `废除`、`禁止`、`违规`、`=`、`不得` 之一 → 不触发（治理文本引用规则原文并否定它 ≠ 实施该行为——「‘登记待以后’=违规」「废除登记待以后」类表述因此豁免；本 ADR、behavior-protocol 契约条款、DEC 裁决原文虽多数已被行族豁免覆盖，本窗口是双保险并覆盖 evidence/task_status 行内的规则引用）。
- **判定**：新增行（`^\\|\\s*(EVD-|RISK-|PREFIX-NNN)` 行形状，复用 face-5 行识别）文本命中词集任一 **且** 否定语境窗口不豁免 → 产生 `deferred_registration` 类 face issue。
- **观察期台账（RT-5，R0 采纳：给「数据回流调词集」一个容器，否则是承诺了没有观测的调优）**：每条 WARN 级检测按三键分桶落账——`命中词 × 行族 × 否定语境命中（布尔）`；翻转 FAIL 前必须产出误报率报告（分桶计数 + 否定语境豁免占比），报告入 evidence 后翻转决议才可提交 decision-log。
- **姿态**：**渐进 FAIL**（FIX-260/Check 30c 先例：首个版本 WARN 起步 + 台账记录 + 升级路径显式登记；一版观察期后翻 FAIL——翻转经 decision-log 入账，不静默）。与 write-guard 现有 WARN/BLOCK 姿态层正交：`deferred_registration` 作为新 issue type 走 face-5 通用渲染，其 BLOCK 与否由渐进表控制。

#### 3.2.2 触发点闭合的可检测判据

「新 EVD/风险行的『登记待以后』语义检测」机器判定 = §3.2.1 词集命中（行级、新增行限域、豁免清单、否定语境窗口**四要素**共同保证零语义猜测）。补充闭合侧判据（问题已发现但是否「当场闭环」）：

- **会话内配对**：新增问题行（EVD 问题类 / RISK 新行 / 检查 FAIL 记录）在**同一会话窗口**（session-snapshot 会话标识 + 当日 evidence 行）内存在对应终态行：修复 EVD / 风险终局（关闭/收窄/升级——「维持」不算）/ FAIL→PASS 复跑记录 / review APPROVED 配对。
- 配对判定为行级启发（ID 前缀关联：`EVD-{n}` 问题行 ↔ 同任务修复行 / `RISK-{m}` ↔ 同 ID 终局标注），不追求语义完备——**未配对即计入未闭环**（保守计数：宁可多计不可漏计，因为漏计=零新账失守，多计只是指标偏严）。

#### 3.2.3 会话内闭环率指标（DEC-288 M2 生效判据：100%）

**指标定义**：

```
session_closure_rate = closed_in_session / problems_raised_in_session
  problems_raised_in_session = 本会话新增问题行数（EVD 问题类 + RISK 新行 + 检查 FAIL 新记录）
  closed_in_session          = 其中在本会话内取得终态配对的行数（§3.2.2 判据）
  违规前置                  = 本会话 deferred_registration 检测数必须 = 0（否则直接 0%——
                              「登记待以后」行为本身即未闭环的极端形态）
```

**M2 生效判据（DEC-288 原文口径）**：新产生的问题在触发会话内闭环率 **100%** 且无新「登记待以后」行——机器可执行形式 = `session_closure_rate == 1.0 ∧ deferred_detections == 0`。

**会话窗口函数（R0 规格化，F-P3-5——Check 42 实施的前置定义）**：窗口边界优先以 session-snapshot 会话身份关联——`W(session) = {evidence 行 : 行日期 == snapshot 日期 ∧ 行归属经 snapshot「本轮已完成」任务锚或当日 guard diff window 关联}`；session-snapshot 缺会话身份或不可读 → 降级为**按日聚合**并在指标输出显式标注「按日聚合（同日多会话合并，精度降级）」（L4 表 M2 Check 42 行：有新增问题行且 snapshot 不可用 → WARN 披露该降级）。禁止无标注的静默降级。

**落点**：`checks/provenance_domain.py` 同域新函数 `compute_session_closure_metrics(...)`（复用 §3.2.1/3.2.2 判定件）+ **Check 42: Discovery Closure Rate**（编号重定见 §2.2.3——Check 40 退役不复用，check-governance 接线 verify 锁释放后）：当会话有新增问题时输出率值，<100% → WARN（观察期一版）→ 渐进 FAIL；`governance-bootstrap` behavior 面追加该指标（bootstrap_aggregate.py，未锁，+~10 行）——**B4′ 拆批承载 = FEAT-082**（DEC-301(4)：该子项在 FEAT-081 triage files 边界外，显式拆批禁止悬置；TRIAGE-FEAT-082 已机录）。

**涉及文件 / 代码量汇总**：verify_workflow.py face-5 检测 ≈ 50 行（含否定语境窗口）+ Check 42 接线 ≈ 15 行（**均 verify 锁释放后**）；`checks/provenance_domain.py` 指标函数 ≈ 45 行（含窗口函数，未锁）；`bootstrap_aggregate.py` ≈ 10 行（未锁）。〔附录勘误（DEC-302 附带，FEAT-082 交付实测）：`bootstrap_aggregate.py` 实测 +276 行——behavior 面平键在锁外 behavior_profile.py、引擎采集器受 R2 禁导入，最小诚实实现需披露镜像+差分测试守护（review-FEAT-082-CODE-R0 核查点⑨成立）；接口统一票（采集纯函数提取入 checks/provenance_domain 双端调用，落地后回收 ~90 行镜像）承载 = FEAT-083。〕

**验收判据**：
1. 构造新增 EVD 行含「待以后」→ guard 运行产出 `deferred_registration` issue（WARN 姿态期）+ 台账记录 open（按三键分桶）。
2. 豁免行族构造（DEC- 行含同词）→ 零 issue。
3. **否定语境负例（R0 新增，F-P2-4；DEC-301 双向消歧）**：新增 EVD/任务行含「‘登记待以后’=违规」「废除登记待以后」类表述（命中词前或后 8 字符含 `=`/`废除`——前例的 `=` 在命中词之后）→ 零 issue。
4. 存量行（基线内）含同词 → 零 issue（窗口限域证明）。
5. 闭环率 fixture：3 新增问题 3 闭合 → 100%；2 闭合 → <100% WARN；1 含待以后 → 0%。
6. 会话窗口：snapshot 带会话身份 → 精确窗口；snapshot 缺失 + 有新增问题行 → 指标输出含「按日聚合（精度降级）」标注（禁止静默降级）。
7. DEC-288 M2 生效判据机检可用：Check 42 输出即判定面。

**测试计划**：`infra/tests/test_deferred_registration.py`（词集正/负/豁免/窗口/**否定语境**五组）+ `test_session_closure_metrics.py`（率值三档 + 违规前置归零 + 窗口函数两态）+ face-5 集成测试（**verify 锁释放后**在 test_verify_workflow.py 补）。

> **附录勘误（CR-R1-3，FEAT-081 B4 交付实测落点——随 DEC-301 勘误动作入账）**：上列两个独立测试文件未按原落点建立——B4 交付（FEAT-081）将五组用例（词集正/负/豁免/窗口限域/否定语境）并入 `infra/tests/test_verify_workflow.py` 三个测试类（`LoopGateProcessorWordSetTests` / `DeferredRegistrationFace5Tests` / `Check42DeferredSignalTests`，19 用例）；闭环率三档/违规前置归零/窗口函数两态由既有 `tests/test_provenance_domain.py`（FEAT-080 交付）+ 采集器测试承载。理由 = FEAT-081 派发锁边界（三文件）+ 既有套件已覆盖指标面，避免同域第二形状源。face-5 集成测试按原文落 `test_verify_workflow.py`（与本勘误一致）。否定语境窗口按 DEC-301 消歧为**双向**（前或后 8 字符）。

### 3.3 与既有机制的关系映射（逐项）+ 冲突裁决建议

| 既有机制 | 关系 | 说明 |
|---------|------|------|
| Check 32（triage_domain） | **扩展** | 五步校验追加第六要素 demand_source（CLI 层必填 + 库层缺省 machine-signal 窗口协议，§2.2.1）；既有四步校验零改动 |
| Check 33（injection contract） | **扩展** | 锚点注册表 +新条款锚（§2.1）；B1a/B1b 拆批序约束（§4） |
| Check 34（completion recommendation） | **不动**（间接受益） | RECO 快照行随 tpa 输出自然携带 src 标注——推荐呈现面即 L1 契约的执行面 |
| task-priority-analysis（task_priority.py） | **扩展** | 解析/排序/渲染三层 + 修订事件感知 resolve（§2.2.2）；`_priority_sort_key` 签名不变 |
| change-triage CLI（change_triage.py） | **扩展** | +2 参数（缺省窗口协议）+2 record 键 + 修订通道 `.demand-revisions.jsonl`（§2.2.1） |
| write-guard（face-5 + write_guard_state.py） | **扩展** | 新检测类型 + 新 issue type；状态机/姿态层/消费事务零改动（§3.2.1） |
| review-record CLI | **不动** | 审查闭环语义与 M2 同向（NEEDS_CHANGE→复审必达已是触发点闭环的审查域实现） |
| task_row_update | **不动** | 行内〔标注〕属 task_status 族 WARN 姿态下合法手工面（F8 裁定表），与 provenance 标注兼容；机录激活后可收敛 |
| check_release_readiness | **扩展** | +provenance_release_gate 子检查（§2.2.4） |
| Git hooks（pre/post-commit） | **不动** | post-commit 已跑 write-guard → 新检测自动生效，hook 本体零改动 |
| FEAT-061 / B-12 / B-13（JSON 权威面） | **衔接** | L3 字段位置声明（§2.3）；激活前置链已有 |
| 复评窗机制（risk-log） | **冲突——裁决 D2** | 见下 |
| M5.2 触发映射表「审计发现：立即修复/排程为任务/接受风险」 | **冲突——裁决 D4** | 见下 |
| 「0.93 池」候选池实践 | **替换（废除）** | DEC-287(3)「不产生 0.94 池」——清偿轮后候选直接 triage 入账（带 demand_source），池形态退役；词集检测「候选池/留池」即针对此残留 |

**冲突裁决建议**（分歧点全文见 §7）：

- **D2 复评窗**：建议裁决为「废除『复评=顺延』逃生口，保留『定期复核』动作但改判语义」——每次复评必须终局三选一（关闭/收窄/升级），「维持观察/下次复评」不再合法；DEC-282(4)「EXC 到期不自动续期」已是同语义先例，本裁决将其一般化到全部活跃风险。复评窗机制本身**不是**被废除对象（定期复核是合理的健康动作），被废除的是其作为延期工具的用法。
- **D4 M5.2「排程为任务」选项**：建议保留（用户显式确认的排期 ≠ agent 自行「登记待以后」——M2 禁的是后者的静默通道），但加约束：该选项被选择后 MUST 当场建 triage 记录（demand_source=user-named，demand_basis=本次用户确认），禁止「先记一笔以后再 triage」的中间态。

---

## 4. 分批实施顺序建议（含锁约束；最终排序裁决归 Coordinator/用户）

> 并发约束（F10，R0 更新）：`verify_workflow.py` + `infra/tests/test_verify_workflow.py` 由 **FIX-404** 持锁（FIX-403 已释放、锁继承——R0 实查 agent-locks.json）；change_triage.py / task_priority.py / checks/provenance_domain.py / tests/test_task_priority.py / tests/test_change_triage.py 由 **FEAT-077** 持锁（M1-B2 批已派发 Developer）。原则：触碰锁内文件的改动 = 批次内「锁释放后实施」标注；未锁文件的域模块/测试可先行交付但不得接线。
>
> **B1 拆批安全序（R0 修订，F-P2-2——初稿「整批等锁」论断过强，已按 existence-only 语义修正）**：`check_injection_contract` 为 existence-only 判定（F2：旧锚全在场即 PASS，多出的文本不违规）→ 「文本面先行、注册表后行」**不产生 FAIL 中间态**；FAIL 只在反向序（注册表先行、文本未落）出现。故拆分为 B1a（文本面，未锁）+ B1b（注册表，锁内），唯一序约束 = **注册表 commit 不得先于文本 commit**。收益：L1 契约提前一个锁周期落地（DEC-287(5) 过渡纪律的软件化提前）。

| 批次 | 内容 | 文件 | 锁约束 | 依赖 |
|------|------|------|--------|------|
| **B0（本批）** | 本 ADR（含 R0 返工修订）+ decision-log entry（Coordinator 写回） | docs/architecture/、.governance/ | 无（DESIGN-021 锁内） | — |
| **B1a M1-L1+M2 契约文本面**（R0 拆出，先行） | 两条款四面注入文本 + governance-init 模板 + 锚点关键词在场 | persona template、SKILL.md、behavior-protocol.md、AGENTS.md.template、governance-init.md | **无锁——立即**（五文件均不在任何锁内；existence-only 语义下先行安全，F-P2-2） | B0 |
| **B1b 锚点注册表 + 预算验证** | `INJECTION_CONTRACT_ANCHORS` +锚点 + 注入预算三 profile 验证 + 锚点负例测试；**序约束：本 commit 不得先于 B1a 文本 commit** | verify_workflow.py | **verify 锁（FIX-404）释放后** | B1a |
| **B2 M1-L2 数据层**（已派发 FEAT-077） | change_triage demand_source（**窗口协议：库层缺省 machine-signal + 非法值 exit 2 + user-named 默认 P1 + 修订通道**，§2.2.1）+ task_priority 加权/联查（修订事件感知）/渲染 + `checks/provenance_domain.py` Check 41 判定件与发布门纯函数（域模块+测试，未接线） | change_triage.py、task_priority.py、checks/provenance_domain.py、tests/（test_task_priority、test_change_triage） | FEAT-077 锁内承载（与本 ADR 修订同步；**窗口期起 = 本批模块合入**） | B0（与 B1a 并行——零文件交集） |
| **B3 M1-L2 接线半批**（**窗口关闭点**） | verify_workflow.py：change-triage CLI `--demand-source` 必填旗标 + `demand-source-revise` 子命令 + Check 41 box + L17105 stale 注释清理 + check_release_readiness 子检查接线 + 集成测试 + **registry/contract_matrix 冻结面 regen**（F-P2-5：新增 Check box 与 CLI 键改变 check segments/CLI key 计数——`registry.py`/`quickscan_registry.py` 声明面 + `tests/test_contract_matrix.py` snapshot regen + registry 双表一致验证，E-17 import-time raise 即抛故 regen 是合入前置）+ **INV-1 same-priority 限定同步调整**（R0 P1-1：B2 已交付的 `provenance_domain.check_priority_inversion` 按旧口径实现（无 P 级限定）——接线时 MUST 同步加 same-priority 限定并新增 INV-X 跨级 WARN 判定，小改 ~10 行，避免接线遗漏） | verify_workflow.py、test_verify_workflow.py、registry.py、quickscan_registry.py、tests/test_contract_matrix.py、checks/provenance_domain.py（INV-1 调整） | **verify 锁释放后**；合入即写路径窗口关闭（§2.2.1） | B2、B1b |
| **B4 M2 执法** | face-5 deferred_registration 检测（含否定语境窗口+台账分桶）+ Check 42 + bootstrap 指标面 + 词集测试 | verify_workflow.py（锁内）、checks/provenance_domain.py、bootstrap_aggregate.py（未锁先行） | verify 面**锁释放后**；域函数可随 B2 先行 | B2 |
| **B5 生效确认** | DEC-288 判据机检：Check 41 在场 + 排序加权实测 + Check 42 闭环率首个会话测量 → evidence + decision 入账「M1/M2 生效」 | .governance/ | 依赖 B1b-B4 全落地 | B3+B4 |

**排序依据**：DEC-288「M1/M2 最先落地并须产生可验证效果」——B1a/B2 并行启动（零锁等待），B1b/B3/B4 的 verify 面是唯一串行点（FIX-404 锁）；B5 是清偿轮其余部分（EXC/91 ID/178 行/池/风险终局）的准入闸。

**写路径窗口期声明（F-P1-2，§2.2.1 窗口协议的批次面）**：窗口 = B2 模块合入（起）→ B3 调用面合入（止）。窗口期经锁内 CLI 入账的新 triage 缺省落 machine-signal；user-named 任务由 Coordinator 经修订通道库级 API 补标（机写 evidence 留痕）；窗口代价与补救路径见 §2.2.1——已由 Coordinator 裁定注入 FEAT-077。

---

## 5. 验收判据汇总（含 DEC-288 生效判据）

### 5.1 DEC-288 生效判据（原文口径 → 机检形式）

| 判据 | 原文 | 机检形式 | 承载 |
|------|------|---------|------|
| M1 生效-① | 排序含 provenance 加权 | tpa 输出含 provenance 分布行 + 每行 src 标注 + 排序矩阵测试绿（§2.2.2 验收 1/4） | B2/B3 |
| M1 生效-② | 反倒挂 Check 在场 | check-governance 输出 Check 41 box + INV-1/INV-X/INV-2 判定测试绿（§2.2.3 验收 1-5） | B3 |
| M2 生效 | 新产生的问题在触发会话内闭环率 100%（无新「登记待以后」行） | Check 42 `session_closure_rate == 1.0 ∧ deferred_detections == 0`（§3.2.3 验收 5/7） | B4/B5 |

### 5.2 分级验收判据索引

L1：§2.1（锚点四面/预算三 profile/入口同步/增量分档防夹带/冻结线机检——验收 1-5）；L2-1：§2.2.1（窗口协议兼容性/非法值 exit 2/默认 P1/修订通道/record 键/旧记录兼容）；L2-2：§2.2.2（排序矩阵/联查权威含修订事件/conflict/解析零回归）；L2-3：§2.2.3（INV-1 同级 FAIL/INV-X 跨级 WARN/INV-2/覆盖率 SKIP/conflict FAIL——验收 1-5）；L2-4：§2.2.4（四情形含 remediation+未申报 fail-closed）；L4：§2.4 表逐行（含窗口与 Check 42 数据不可用行）；M2：§3.2.3 验收 1-7（含否定语境负例与窗口函数两态）。

---

## 6. 备选方案与排除理由（ADR 硬门槛：≥2 候选）

### 6.1 M1 排序加权落点

- **A（选中）**：`task_priority.py` 排序键扩展——`_priority_sort_key` 加 demand rank。
- B：change-triage 层一次性排序快照（triage 时固化顺序）——**排除**：排序是 plan-tracker 的纯函数（F5），每次分析重算；快照会随表变化过期，且推荐时刻的排序与 triage 时刻必然漂移，倒挂无法在推荐点执法。
- C：独立 rank 覆盖文件（sidecar 每任务 rank）——**排除**：新增文件面+第二事实源，违反「不引入新的大型框架」与 D4 冗余修改原则；demand_source 已是充分排序输入。

### 6.2 M2 检测落点

- **A（选中）**：write-guard face-5 新增行窗口检测——**选中决定性理由**：guard 基线 diff window 天然只看新增行（存量不追诉），豁免行族/词集/姿态全部复用 face-5 既有分类与渲染，post-commit 自动生效（hooks 零改动）。
- B：独立 post-hoc Check 全文件扫描——**排除**：无法区分新增行与存量行，risk-log/evidence-log 历史满布「下次复评/后续」字样（F11），全量扫描 = 误报海。
- C：会话结束 snapshot 校验（事后审计）——**排除**：M2 要求触发点闭环，事后发现时「登记待以后」已经发生且已付了登记成本，检测时点违背契约本意；C 可作为 Check 42 指标面的**补充**保留（§3.2.3 正是会话级指标），但不是执法主体。

### 6.3 provenance 字段名

- **A（选中）**：`demand_source`——「为谁而做」语义直白，与既有 `provenance`（写入器溯源）异名共存。
- B：`source_type`——**排除**：过泛（source of what?），在 record 内与其他 source 类键不可辨。
- C：复用 `provenance` 键嵌套扩展——**排除**：F9 已定义该键为 `{"op_id","marker"}`；一词两义 = 架构腐化（P-v1 D2），且 C 级两键必须同 record 并存。

---

## 7. 蓝军挑战（≥3 条，每条含 ID 与缓解）

- **BC-1 注入预算回弹**：两条款契约把 strict profile 推近 6000 硬门（余量 ~81 tok），后续任何「再加一条契约」的提案都会立即爆预算——这不是缺陷而是设计特性（预算硬门正是反扩张机制），但短期风险是 M1/M2 文本调优（改词、加例）时无意识越线。**缓解**：§2.1 验收判据 5 冻结线（机检形式：余量 <100 tok 时禁止任何使余量下降的注入面变更，防夹带分档断言 M1 ≤160 / M1+M2 ≤320）；`check-injection-budget` 进 B1b 验收命令；两条款文本以本 ADR 逐字建议为基线，改动需 re-run 预算检查。
- **BC-2 存量海瘫痪**：~199 个既有 triage 记录无 demand_source，若 Check 41/发布门对存量 fail-closed，清偿轮开工即全红——执法机制瘫痪了自己要护航的清偿轮。**缓解**：分阶段 fail-closed（§2.2.3：覆盖率 0 → SKIP+WARN；>0 即严）；发布门只看「版本载荷」任务（本版本 triage 的记录必有该字段——新任务强制），存量不在发布门作用域。
- **BC-3 词集检测误报**：本 ADR 自身、DEC-286/287/288 原文、behavior-protocol 契约条款都含「登记待以后」字样；治理文档引用规则文本 ≠ 实施该行为。**缓解**：四层限域（R0 升级为规范级，§3.2.1）——只查 guard 受管面新增行（docs/**、skills/** 规则文件不在五族受管面）+ 豁免行族（decision/review/ops）+ **否定语境窗口（词前或后 8 字符含 `废除|禁止|违规|=|不得` 则不触发——已入 §3.2.1 规范文本与验收判据 3 负例，F-P2-4；方向消歧 DEC-301 双向）** + 观察期台账三键分桶（命中词×行族×否定语境，RT-5）。误报残余走 write-guard 既有 WARN 姿态披露，翻转 FAIL 前必须产出误报率报告。
- **BC-4 出身洗白（Goodhart）**：把任务标成 user-named 即可插队——demand_source 若无溯源要求，三值枚举会沦为新的优先级套利通道。**缓解**：user-named 强制 `demand_basis`（用户原话/DEC 引用，§2.2.1 fail-closed）；Check 41 的 issue 输出携带 basis 摘要供人工抽验；triage 记录不可变（F4）使造假留痕；**修订通道同样带溯源且不可变（R0，F-P1-3）——防造假属性覆盖生命周期全程，同时不焊死正向漂移（用户事后点名经修订事件合法入账）**。

---

## 8. 影响范围

- **行为面**：Coordinator 推荐呈现（+src 标注义务）、triage 调用方（+2 参数——库层缺省兼容）、发布流程（+provenance 门与 remediation 交互）、write-guard 输出（+新 issue type）。
- **数据面**：triage record +2 键（additive）+ 修订事件流 `.demand-revisions.jsonl`（append-only 新文件类）；plan-tracker 任务行新增可选〔标注〕（解析兼容，F5 零回归论证）；JSON store schema 预留 3 键（L3，含 `demand_source_revisions`）。
- **零影响面**：review-record、task_row_update、hooks 本体、governance_store 写入器（L3 仅声明不改码）、既有 ~199 triage 记录（不可变，消费者按 legacy 处理）。
- **预算面**：resident strict 余量 391 → **~81 tok**（M1 154 + M2 156 = 310）；冻结线见 §2.1 验收判据 5。
- **实施状态（R0 返工时点）**：B2 已由 FEAT-077 交付（change_triage/task_priority/provenance_domain 模块层+测试）；B2 交付与 R0 修订的三处对齐动作见 §4 批次表 B3 行（INV-1 same-priority 限定随接线调整）与 §2.2.1/§2.2.4 吸收注记。

## 9. 后续动作（本 ADR 闭环内——每项已有所属批次与验收，非「待后续完善」）

1. ~~本 ADR 送 Design Review~~ 已执行：R0 = **NEEDS_CHANGE**（unresolved_blockers=3，`docs/reviews/review-DESIGN-021-DESIGN-R0.md`）；本版 = 按 R0 §12 最小修复集 + Coordinator 三项 FEAT-077 吸收输入完成的返工修订版，待 R1 复审（同一 Reviewer，注入 R0 报告路径）。
2. **R0 返工修订的增量入账（Coordinator 写回）**：DEC-289 已按初稿入账（decision-log L231，R0 实读证实）；本版相对初稿的裁决性变化——D1 措辞三处自洽化（同优先级限定 + INV-X 跨级 WARN + D1 已知边界披露）、写路径窗口协议（缺省 machine-signal，Coordinator 已裁定）、demand_source 修订通道（append-only 事件流）、检查编号重定（Check 41/42，40 退役不复用）、预算重算（~81 tok）、B1 拆批（B1a 文本先行/B1b 注册表等锁）、P2+user-named 拒绝条款（FEAT-077 实现对齐）、发布门严格 semver 判定（FEAT-077 实现对齐）——建议以新 DEC（如 DEC-290）承载「ADR-021 R0 返工修订采纳」，DEC-289 不改写（append-only 治理记录，初稿采纳事实保留）。
3. B1a/B2 后续批次按 §4 派发（B2 已由 FEAT-077 交付模块层；B3 接线含三处对齐动作——见批次表）。
4. B5 完成后 DEC-288 生效判据入 evidence + decision-log「M1/M2 生效」——清偿轮其余部分的准入闸打开。

---

## 附：本 ADR 自身的过程内闭环声明

- 覆盖完整性：M1 四级梯度（§2.1-2.4）+ M2 三件（§3.1-3.3）逐项含落地形态/涉及文件/代码量/验收判据/测试计划；生效判据（§5.1）；关系映射与冲突裁决（§3.3/§7）；实施批次（§4）。
- 无「待后续完善」节：L3 是方向声明（字段位置定义即其交付物，实现属 B-12/B-13 承载票——引用既有票据而非新立项目，符合 DEC-286 执行注记）；词集与渐进 FAIL 翻转时点显式登记为治理动作（decision-log 入账 + 翻转前误报率报告义务，RT-5），不是未闭合设计；D1 残余张力作为已知边界显式披露（§2.2.2 第 5 点）——知情持有，不是回避。
- 硬门槛自检：ADR 字段完整（标题/日期/背景/决策/备选×3 组/排除理由/影响范围/后续动作/可逆性）✓；候选方案 ≥2 每组 ✓；蓝军 4 条带 ID+缓解（R0 红队 RT-1~5 缺口已吸收：RT-1/2→P1 修复、RT-3→B3 regen、RT-4→编号重定、RT-5→台账分桶）✓；所有引用文件名/函数名/字段名实读核对（§1.3 F1-F12，F10 已按 R0 更新锁继承事实）✓；零代码修改（唯一产出 = 本文档）✓。
- **R0 返工修订记录（2026-09-29，依据 review-DESIGN-021-DESIGN-R0.md §12 + Coordinator 三项 FEAT-077 吸收输入）**：P1-1 三处自相矛盾→契约文本/INV-1 加同优先级限定 + INV-X 跨级披露 WARN + 发布门兜底措辞修正 + D1 已知边界披露（§2.1/§2.2.2/§2.2.3）；P1-2 写路径真空窗→窗口协议写死（缺省 machine-signal/非法值 exit 2/B3 调用面更新即窗口关闭/窗口期修订通道补标，§2.2.1+§4）；P1-3 修订通道→append-only `.demand-revisions.jsonl` 事件流 + resolve 取最新有效 + conflict 语义修订感知 + L3 键同步（§2.2.1/§2.2.2/§2.3）；P2×5→预算统一 81+冻结线入验收（F-P2-1）、B1a/B1b 拆批（F-P2-2，existence-only 安全性评估后采纳）、发布门 remediation 协议+常态性明示（F-P2-3）、否定语境窗口入规范+负例（F-P2-4）、B3 补 registry/contract_matrix regen 面（F-P2-5）；P3→F10 锁事实更新（F-P3-1）、序数锚定改关键词制（F-P3-2）、user-named 默认 P1 机化（F-P3-3）、Check 40 退役编号跳用 41/42+L17105 stale 注释清理（F-P3-4，编号来源已注明）、会话窗口函数规格化（F-P3-5）、L4 补 Check 42 数据不可用行（F-P3-6）；FEAT-077 吸收→P2+user-named 拒绝条款收编（§2.2.1）、发布门严格 semver 判定注记（§2.2.4）、B3 标注 INV-1 same-priority 同步调整（§4）。检查编号全文已同步（40→41 反倒挂、41→42 闭环率）。
