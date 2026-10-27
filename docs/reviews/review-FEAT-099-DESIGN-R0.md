# REVIEW-FEAT-099-DESIGN-R0 — FEAT-099 设计文档 R0 独立设计审查

- **被审对象**: `docs/architecture/feat-099-dsh-host-enforcement-poc-design.md`（R0，263 行）
- **快照**: SNAP-FEAT-099-R0-20261027T101745 — sha256 `8de013eef817d574e735e1f3ee72b051be9132ca3815f987ffa66fe6b81d93cf`（32740B，审查前重算逐位一致）
- **任务上下文**: FEAT-099 = U1 DSH 宿主级执法接线 PoC（P2，0.100.0，DEC-374 立项 2026-10-26）
- **审查人**: Design Reviewer（独立实例；不修改被审文档；不机录 REVIEW- 行）
- **日期**: 2026-10-27 | **round**: R0（DESIGN 面）
- **结论**: **NEEDS_CHANGE**（unresolved blockers = 3，均为 P1；另有 P2×2 / P3×3 非阻断）

---

## 1. 审查范围与方法

按派单六项重点（a 锚协议可行性 / b expected 源方案 / c DEC 草案完备性 / d 热路径单源 / e C6 张力 / f 通面）逐项审查；锚定源抽查采用「设计引用行号 ↔ 源文件实读」双验证，**不给推断放行**。

**抽查覆盖**（源文件实读，非设计转述）：

| 源 | 实读范围 | 引用核对 |
|---|---|---|
| `dsh-tools/README.md`（npm @0.1.5-rc.3） | 全文 250 行 | L85/L89/L109/L126/L141/L215/L233 全部逐字精确 |
| `dsh-tool-subagent/README.md`（npm） | 全文 252 行 | L45-53（无 toolFilter 行）/L48/L53/L59/L63/L72 全部精确 |
| `skills/software-project-governance/infra/enforcement.py` | L1-260 / L340-439 / L540-727 | ~20 处（策略表/decide/_rule_hit/fail-closed/投影/CLI）全部精确 |
| `adapters/dsh/host-contract.json` | L25-89 / L460-514 / L705-734 / L730-939 / L1112-1139 / L1272-1299 | L34/L79-86/L473-515/L718/L738/L763-775/L776-784/L794-811/L830/L835/L910-928/L1123/L1282-1284 全部精确 |
| `lib/index.js` | L30-94 / L450-467 / L655-700 | L33-36/L60-75/L69-75/L86-92/L457-462/L667-699 全部精确 |
| `lib/dsh-native/bridge.js` | L1-60 / L118-212 | L11-13/L43-50/L129-137/L183-211 全部精确 |
| `docs/research/feat-095-harness-enforcement-capability-2026-10-10.md` | L93-104 / L165-174 / L184-229 / L244-289 | L97-99/L167-171/L191/L207/L209/L213/L221/L227/L247/L249/L286/L288-289 全部精确（节号 1 处瑕疵见 D6） |
| `SKILL.md` | L232-241 | L238 精确 |
| `infra/dsh_doctor.py` | L103-116 / L1915-1946 | L105-114/L1917-1945 精确 |
| `infra/authority_ledger.py` | L14-21 / L812-851 / L935-948 | L17-18/L818/L941 精确（tasks 态确认无修订号字段，设计断言成立） |
| `adapters/dsh/adapter-manifest.json` | L32-73 | L36/L38-70（七键无 enforcement）精确 |
| `adapters/dsh/README.md` | L42-73 | L45/L59-69 精确 |

**统计**：约 45 处行号引用，44 处逐字精确、1 处节号错（行号仍对，D6）。锚定质量为本设计最强面。

## 2. 逐项发现

### D1（P1，blocker — 审查重点 a）锚协议的「guard 可读调用参数」前提未标注未证实，证伪判据缺该分支

- **设计文本**: §2.1（L83-89）「guard 行为：提取锚 → 与治理态 expected revision 投影比对」——锚载体 = `subagent/subagent_fork` 调用的 prompt 首行（L86）。
- **源证据**: `dsh-tools/README.md` L89 仅声明「`ctx.tools.guard(guard)` registers a monotonic synchronous guard … a returned reason denies the call」——**guard 回调的签名与参数面（能否读取被调工具的 arguments/prompt）在 README 全文无一处直接陈述**。L233「`tools/pre-execute` deliberately cannot rewrite `exec.arguments`」证明 **pre-execute 事件面**持有 `exec.arguments`（改写禁令隐含可读），且 L109 管线把 guard 置于 pre-execute 之后——但「guard 回调与 pre-execute 事件共享同一 exec 视图」是**架构推断**，不是文档证实。
- **设计缺口**: §1.4 未证实清单（L62）只列「guard 回调内可用的上下文面（能否定位会话 workspace、调用方身份）」——未列「能否读取工具调用参数」；§3b 治理根探明（L128）也不覆盖参数面。§5.1 证伪判据 F1（L194）只覆盖「guard 恒不可达」——**「guard 可达但读不到调用参数」形态无判据无处置**（该形态下 deny 原语仍在而锚协议失败，属不同结论）。
- **影响**: 锚提取是 PoC 核心机制的载体；若前提不成立，§2.1 整节需换锚载体重新设计。
- **修复要求**: ① §1.4 未证实清单补「guard 回调可读取被调工具 arguments」项；② §5.1 增证伪分支（建议 F1b：guard 可达但调用参数不可读 ⇒ 锚协议证伪，deny 面另行裁定）；③ §4.1 V 步前增首项探明动作（与 §3b 治理根探明同批，先探参数面再跑 V1-V6）。

### D2（P1，blocker — 审查重点 d）策略「单源」投影不含 reason/remedy 模板，与 §2.1 文案对齐要求直接矛盾

- **设计文本**: §2.1（L89）「deny（reason 携带 reason_code=revision-mismatch + remedy，对齐 enforcement.py L141-147 文案…）」；§3b（L124）「**策略数据单源** = `_strategy_public()` JSON 投影（enforcement.py L549-574），构建期由 `enforcement-check --print-strategy` 生成 fixture 随包分发」。
- **源证据**: `enforcement.py` L549-574 实读——`_strategy_public()` 的 `hard_block_rules` 仅投影 `rule["id"]`（L560-561：`[rule["id"] for rule in table["hard_block_rules"]]`）；reason/remedy 模板（L137-175，含 L141-147 revision-mismatch 文案）**不在投影输出内**。
- **矛盾**: JS 判定器要产出「对齐 L141-147」的 deny 文案，投影里拿不到——只有两条路：(a) 模板硬编码进 `guard.js` = 第二源（与「单源」主张冲突且无漂移守护）；(b) 扩展 `_strategy_public()` 投影面 = 产品代码改动，§6 S1-S8 未列。
- **修复要求**: 设计显式裁定二选一——建议 (b)：投影增列 `hard_block_rules[].{reason, remedy}` 模板，并把「`--print-strategy` 输出含模板 + parity 断言」列入 S1 判据（与 D8 联动）。

### D3（P1，blocker — 审查重点 e）C6 无差别 allow-through 与带锚调用的 fail-closed 语义不自洽

- **设计文本**: §3c C6（L142）「治理根不可定位 ⇒ 一次性 warn + allow-through」，无锚/带锚不区分；C3（L139）「锚存在但格式非法 ⇒ deny（**声明了锚即请求执法判定，判定不了就拒**…）」。
- **不自洽**: 按 C3 自己的论证，「带锚 = 显式请求执法判定」——治理根不可定位时判定依据缺失，正是「判定不了」的形态，对带锚调用应 deny；C6 却放行。设计的「能力缺失（C6）vs 故障（C1-C3）」分级只对**无锚**调用成立（无锚本就不判定，C7 allow+计数一致）；对**带锚**调用，C1（文件在但坏→deny）与 C6（文件找不到→allow）仅是故障形态差异，处置却相反。
- **对抗意义**: 治理会话中定位序意外穷尽（env 丢失 + 回调上下文无 workspace 信息）时，带锚错配派发被静默放行（虽有一次性披露）——恰是本 PoC 要拦的目标在 fail-closed 总则（§3c 引言「绝不静默放行」）下开出的破口。设计 §8 前置项 5 已自知此张力；本审查裁定：**无锚面成立、带锚面不成立**。
- **修复要求**: C6 按锚状态分流——无锚 ⇒ allow + 披露（维持现设计）；带锚 ⇒ deny（`enforcement-fail-closed` 族，reason 指名「治理根不可定位」+ remedy）。§4.1 V3 补「C6-带锚」用例。

### D4（P2，应修）guard 注册窗口期（inject 延迟）未披露、无观测步骤

- **设计文本**: §6 S3（L228）「apply() 内能力检测 + inject 模式注册（bridge.js L183-211 先例）」；§3a-4（L114）失败分层只覆盖「注册失败」。
- **源证据**: `bridge.js` L183-211 实读——服务在行 apply() 之后才提供，注册经 `ctx.inject(['agentPresets'], …)` 延迟；行激活 → inject 回调触发之间存在窗口。native 预设注册延迟无害；**guard 延迟 = 执法空窗**（窗口期内带锚错配派发不被拦截），语义不同。
- **缺口**: §3c C1-C7 无「注册完成前」条目；V1-V7 全为稳态测试；§5.3 披露面未列窗口期。
- **修复建议**: ① §3c 增 C0（注册前窗口期 = 已知边界，如实披露）；② V 步增一项 boot 后即时派发的时序观测，或论证宿主时序保证（模型首次工具调用晚于服务注入完成）——不允许以概率论证替代判据。

### D5（P2，应修 — 审查重点 b）expected_revision 生产化路径的派生源未指认，现成 observed_revision 机制未提及

- **设计文本**: §2.1（L91）「生产化路径 = 后续批把 expected_revision 固化进 governance-bootstrap 热数据投影（单源）」。
- **核实**: 「今天无单点权威 expected_revision 治理文件」断言成立——`enforcement.py` L230 `decide()` 只消费 facts 不读文件（实读确认）；`authority_ledger.py` tasks 态（L812-817/L818/L941）持 semantic_anchor/anchor_fingerprint/priority/target_version/status，**无修订号字段**（实读确认）。PoC 用隔离 fixture 的裁定如实且成立。
- **缺口**: 生产化投影的**数据派生源**（authority-ledger events / plan-tracker `.ops.jsonl` receipts / `task-row-update --inspect` 的 `observed_revision`）未指认——三者中 `observed_revision` 已是机写通道现成机制（verify_workflow `task-row-update --help`：「Content-level CAS expectation (from --inspect observed_revision)」），生产化设计应至少列候选源并对账方向；不阻断 PoC（fixture 已如实裁定），列 P2 供后续批。

### D6（P3，备注 — 审查重点 f）§1.3 引用节号勘误

- 设计 §1.3（L53）「与调研 §3.1 发现1『插件零接线』一致（I1 L207）」——L207 实位于调研 **§6「关键发现」发现1**（§3.1 是平台证据档案）。行号正确、节号错；不影响断言成立（L207 原文即「插件零接线」）。

### D7（P3，备注 — 审查重点 c）DEC 草案建议补「注册时序/窗口期」定性

- §3a 六要点完备覆盖 warn_only 收窄/三服务边界/parity 四面/失败分层/可逆性，Coordinator 可据以起 DEC 不需返工主干；建议随 D4 一并补第七要点：guard 注册窗口期在 DEC 中的定性（已知边界披露 or 待宿主时序论证）。

### D8（P3，备注 — 审查重点 d）parity 守护建议追加投影字节断言

- S1 parity 测试（L226）对「同一 facts 集合输出一致」守护判定行为；若 facts 集合未覆盖新改规则分支，投影 fixture 过期可静默漂移。建议加「fixture 文件与 `--print-strategy` 当前 stdout 逐字节相等」断言（比 facts 集合更强、成本零；与 D2 修复联动后一并守护文案模板）。

## 3. 六项审查重点逐项判定

| 重点 | 判定 | 承载发现 |
|---|---|---|
| a 锚协议可行性 | **有条件成立**——锚协议设计合理（无锚 allow 的误伤面裁定成立、U7 如实登记），但载体前提（guard 可读参数）未标注未证实 | D1（P1） |
| b expected 源方案 | **成立**——「无单点权威文件」断言经实读证实；fixture 裁定如实；生产化派生源留白（不阻断） | D5（P2） |
| c DEC 草案完备性 | **基本完备**——六要点足 Coordinator 起 DEC；建议补窗口期定性 | D7（P3） |
| d 热路径单源边界 | **方向正确、有一处实质矛盾**——python 表为源/JS 为投影方向对，但投影缺 reason/remedy 模板使单源声明与文案需求冲突 | D2（P1）、D8（P3） |
| e C6 与 fail-closed 张力 | **部分成立**——无锚面的能力缺失分级成立；带锚面 fail-closed 破口 | D3（P1） |
| f 通面 | **高质量**——~45 处引用 44 处逐字精确；V1-V7 可执行；F1-F4 可判定（缺 F1b 分支）；S1-S8 可验证且全程隔离；未证实面基本如实（除 D1 一项漏标） | D1/D4/D6 |

## 4. 结论

**NEEDS_CHANGE — unresolved blockers = 3**（D1 / D2 / D3，均 P1 必须修）。

- 设计的**架构骨架成立**：切片选择（subagent/subagent_fork × revision-mismatch 最小面）有调研 §5 矩阵 L191 直接依据；缓存架构（stat 指纹 + TTL + 开关敏感）合理；隔离纪律（重定向 DSH_HOME 先例链）完备；锚定质量在同类设计文档中属最高档。
- 三个 blocker 均为**局部条款增补/裁定**，不动架构：D1 = 补未证实标注 + 证伪分支 + 探明步骤；D2 = 投影面扩展裁定；D3 = C6 按锚分流。预计修订量小（<30 行增量）。
- P2×2（窗口期披露 / 派生源指认）与 P3×3 建议随修订一并处理，不单独阻断。

## 5. 复审建议

- 复审 round = R1，同一 Reviewer；聚焦面 = D1/D2/D3 三处修订的逐条闭环（修订文本 ↔ 本报告条款对照），外加 D4-D8 处置披露。
- 修订后快照建议重取（sha256 将变化）；R1 采用 delta 复审（M7.8 先例），不重查已通过的锚定面。

— 审查报告完 —
