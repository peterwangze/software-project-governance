# Review — FEAT-032-CODE-R0（治理成本埋点交付 · 独立代码审查 round 0）

> Reviewer：Code Reviewer Agent（独立于 Developer） | 日期：2026-09-18
> 审查规范：`skills/code-review/SKILL.md`（已加载执行）
> 审查边界：FEAT-032 变更集 11 项（并行 FEAT-037 中间态不计入本报告 findings）
> 方法约束：Reviewer 无命令执行权限——性能与运行时数值采用「静态评估 + 产物交叉验证」，不能独立复跑的数值均如实标注。

## 审查对象与事实源清单

| # | 文件 | 审查动作 |
|---|---|---|
| 1 | `skills/software-project-governance/infra/governance_cost.py`（888 行） | 逐行读 |
| 2 | `skills/software-project-governance/infra/tests/test_governance_cost.py`（778 行） | 逐行读，测试方法计数 |
| 3 | `docs/research/governance-cost-baseline-0.83.0.md` + `.json`（928,795 B / 32,720 行） | md 全读；JSON 结构抽查（schema/scan/calibration/totals 头 120 行）+ 与 md 数值交叉复算 |
| 4 | `infra/verify_workflow.py` | grep 定位 + 三处接线点上下文精读（L60-89 / L24440-24617）；全文 grep `governance_cost` 共 7 处命中，全部属于下述三处接线及其注释 |
| 5 | `infra/registry.py`（990 行） | 逐行读 |
| 6 | `infra/contract_matrix/snapshots.json` | 全读 |
| 7 | `core/architecture-baseline.json` | 全读 |
| 8 | `infra/tests/test_registry.py` | 冻结常量段（L75-139）+ migrated 披露段（L315-349）精读 |
| 9 | `infra/tests/test_contract_matrix.py` | 冻结常量段 grep + 读 |
| 10 | `infra/TOOLS.md` TOOL-053 | 表行（L58）+ 详情节（L553-562）读 |
| 11 | `project/research/dsh-trace-analysis/analyze_governance_turns.py`、`deep_dive.py` | 全读（deprecated 指针化验证） |
| 交叉 | `docs/requirements/governance-bootstrap-cost-audit-0.84.0.md`（AUDIT-154）§2/§3.1/§3.3/§4/§6/§8 | 读 |
| 交叉 | `.governance/change-triage/FEAT-032.json` | 全读 |
| 交叉 | `.governance/decision-log.md`（DEC-204）、`.governance/evidence-log.md`（TRIAGE-FEAT-032 / EVD-1072） | grep + 读命中行 |
| 交叉 | `core/manifest.json`、`infra/cleanup.py`（登记/清理边界核查） | grep + 读关键段 |

---

## 一、5 维度逐项结论

### 维度 1：正确性 —— PASS

逐行验证要点（全部有行号依据）：

- **类型分派完备**（`_events_from_bytes` L296-337）：fast 三类（assistant/message、tool/result、tool/call）→ `_FULL_PARSE_TYPES` 七类 → 有 envelope 的非必需类型 `continue` → 无 marker 行走 full parse，失败计 corrupt。每一分支与 L148-153 口径注释及模块 docstring L296-303 一致。
- **fast≡full 等价构造性成立**：fast path 任一字段缺失/可疑即返回 None 落入同一 full-parse 分支（L243/L247/L255-259/L285），解析产物与全量 `json.loads` 逐事件一致；`test_fast_and_full_paths_agree`（test L689-729）对 turn 字典与派生指标双面对比。
- **turn 归属**（`parse_session` L402-433）：`user/message` 无 turn 字段按事件序归属 `current_turn`，首个 `turn/start` 前的 user message 计 orphan 并入 `user_messages_before_first_turn`（L416-419）——与 docstring L29-33 / 审计报告 §2 / 测试 `test_user_message_before_first_turn_is_orphan` 三方一致。
- **边界条件**：空轮（`percentile` L493-504 空返回 None）、`turn_end` 回退仅当 `rec["end_ms"] >= first_ask`（L526）、无配对 tool/call 不计时长且计 `unfinished`（L461-467 / L481-483，测试覆盖 L464-475）、`usage` 字段为 None 记 0（L446-448，测试 L373-384）、嵌套花括号 usage 提取（L210-237，测试 L731-744 覆盖 `"} inside"` 值）。
- **伪 usage 算术防伪**（L230-236）：`totalTokens` 为 int 且 ≠ in+out+cacheRead → 丢弃并从下一位置继续扫描（`test_embedded_fake_usage_is_rejected` 证实拒绝发生在 fast path——fixture 中 fake 先于 envelope usage 序列化）。弱点见 F-P3-1。
- corrupt_lines 计数实测断言（test L393-406）：`""`/`"   "` 静默跳过、`"{not json"`/`"[1, 2,"` 计 2、`"null"` 解析成功非 dict 不计——实现/注释/测试三方一致（措辞张力见 F-P3-2）。

未发现逻辑错误、边界缺陷或资源管理问题。**P0 = 0。**

### 维度 2：安全性 —— PASS

- **只读保证（R4 静态核实）**：`scan_sessions` 全路径仅 `rglob` + `read_bytes` + 内存内解压（L625-696），无任何写/移动/删除调用；不存在写 `~/.dsh` 的代码路径。**基线生成路径纯只读，静态核实通过。**
- **输入校验**：`--sessions-root` 缺失且环境变量未设 → exit 2（L865-872）；root 非目录 → exit 2（L873-876）；**用户路径零硬编码**（默认值仅来自参数或 `DSH_SESSIONS_ROOT`）。
- **敏感数据**：报告 `sessions_root` 字段含用户本机绝对路径（基线 JSON L5 实录 `C:\Users\peter\.dsh\sessions`）。落盘位置 `docs/research/` 属 manifest `repo_only`（manifest L838 `docs/`），不随插件分发；且读取行为本身在 R1(c) 授权链内（见设计一致性节）。披露为 F-P3-4。
- **注入面**：无 SQL/shell 拼接；`sys.stdout.reconfigure` 包 try/except（L860-863）；外部输入（轨迹字节）全程 tolerant 解析，无 `eval`/`exec`。
- **权限检查**：CLI 无权限面（本地只读报告命令），不适用。

**P0 = 0。**

### 维度 3：可维护性 —— PASS

- 模块职责单一（解析/聚合/渲染/CLI 四段清晰分层，888 行在合理范围）；docstring 完整且与实现一致（口径、事件模型事实、边界声明全部可对照行号）。
- 口径全部常量化：`REPORT_SCHEMA` / `GOVERNANCE_TOOL_NAMES` / `CALIBRATION` / `_USER_TEXT_HEAD`——`CALIBRATION` 机读内嵌每份报告（自描述语义），注册表白名单条目带 FEAT-032 注释（registry L200-203）。
- `add_arguments` 单一来源供引擎与测试共用（L830-846），引擎侧零参数复制。
- 事实单一来源纪律：registry 只 +1 键 +1 白名单；test_registry 冻结常量与注释同步更新且注明变更缘由（L80-91）；migrated-keys 披露测试显式纳入 `governance-cost-report`（L327-334）。
- 小瑕疵：`format_text` L819 用 `%r` 打印 title（repr 引号形态，风格小怪）；`_extract_usage` 递归续扫可读性尚可。均不构成 finding 计数（已并入 P3-2 措辞精确化之外的观察，不计）。

### 维度 4：性能 —— PASS（静态评估）

- **无线性劣化路径**：每行处理 = 常数次 `bytes.find`（线性于行长）+ `splitlines` 一次遍历；`_extract_usage` 括号深度扫描线性且续扫从上次终止位置开始，行内总代价 O(行长)。全文件代价 O(解压字节总数)，无 O(n²)、无逐行全量反序列化（仅 needed 7 类与 fast 失败行走 `json.loads`，占比小）。
- **懒加载正确支撑冷启动面**：zstandard 仅在首次解压时导入（L92-109），引擎冷导入仍 stdlib-only（R6 实测 196→197，+1 = governance_cost 本体，与 `FROZEN_ENGINE_IMPORT_COUNT=197` 一致）。
- **申报数值核对**：基线 JSON 实录 `duration_ms: 4393`（4.4s，298 文件，`scan` 块 L14）；md 记录 4.8s 与 4.4s 两次采样，均 <5s。**静态评估无瓶颈点，与实测记录自洽；Reviewer 未独立复跑（无命令权限），此项为「静态评估 + 产物佐证」通过。**
- 防御性建议见 F-P3-7（单文件解压体积无上限）。

### 维度 5：测试覆盖 —— PASS（1 条 P2）

- **37 个测试方法计数核实**（逐类累加）：TurnAttribution 4 + TTFA 3 + TimeToWork 4 + TokenAggregation 3 + CorruptLine 3 + LLMAndToolTime 2 + ToolDistribution 2 + WorkspaceFilterAndDefaults 4 + ZstandardFailClosed 2 + CLIOutput 3 + FastScannerEquivalence 4 + Percentile 3 = **37 ✓**（与申报一致）。
- 核心路径：turn 归属（4）、TTFA 起点与 null（3）、time-to-work 双 endpoint + pre-ask 排除（4）、token 聚合 3 形态（3）、fast≡full 等价（4）、fail-closed 双路径（2）、CLI 双格式 + calibration 披露断言（3）。
- 错误路径：corrupt/blank/null 行分类（L393-406）、空文件（L408-416）、坏 zstd（L418-425）、缺 root/env 双 fail-closed exit 2（L545-572）、缺 zstandard exit 1（L575-603）。
- **快速通道真实性看护**：`_write_session` 强制紧凑 separators（L47-63 docstring 说明 marker 依赖紧凑形态），保证 fixture 走 fast path 而非静默回退；skip 分支回归测试（L746-759）显式看护「needed 类型被 skip 吞掉 → TTFA 归零」的语料事故。
- **F-P2-3**：环境无 zstandard 时 37 测试全部 `skipTest`（L42-44）——unittest 显示 skipped，但 CI 门禁通常只拦 FAIL，看护在无依赖环境静默失效。
- 覆盖率工具未运行（Reviewer 无命令权限）；以路径覆盖静态核对替代，核心/边界/错误三路径均有对应测试。

---

## 二、Developer 申报 9 项逐项核实

| # | 申报 | 核实结果 | 依据 |
|---|---|---|---|
| 1 | 单命令 4.8s < 5s | **通过（静态评估 + 产物佐证）**：O(解压字节) 线性、无全量反序列化路径；JSON 实录 4393ms/298 文件。未独立复跑（Reviewer 无命令权限） | governance_cost.py L296-337；基线 JSON L14 |
| 2 | TTFA p50=271.8s / max=428.0s 复现 AUDIT-154 §3.1 | **通过**：§3.1 五轮样本 428.0/294.0/271.8/163.9/95.9s → max ✓ 中位 ✓；基线 md 校准表与审计逐值吻合 | 审计 §3.1 L26-32；基线 md L40-46 |
| 3 | 引擎仅接线零 print | **通过**：全文 grep 仅 7 处命中 = import（L76-77）+ subparser（L24463-24474，参数委托 `governance_cost.add_arguments`）+ dispatch（L24608）及其注释；R4=1301 与 architecture-baseline `r4.total=1301` 一致；governance_cost 自身 print 不入 R4 主文件预算，与 archguard_ratchet 先例同构 | verify_workflow.py；architecture-baseline L541 |
| 4 | corrupt_lines 口径 | **通过**：实现/注释/docstring/测试四方一致（计「无 marker 且不可解析」与「needed 双失败」；带 envelope 非必需类型跳过不计数）；首句注释措辞与 null 行行为有轻微张力 → F-P3-2 | L148-153 / L296-337；test L393-406 |
| 5 | GOVERNANCE_TOOL_NAMES 最小声明集 | **通过但记 P2**：分类声明式、可复审、calibration 有披露；偏差方向（ask 后治理性 read 被计为 work → time_to_work 低估治理开销）未写明 → F-P2-2 | L66-72；CALIBRATION L723-727 |
| 6 | zstandard 懒加载 fail-closed | **通过**：import 失败缓存错误并重抛 `GovernanceCostError`（消息含 pip install 指引），cmd 层 exit 1；无静默降级；双测试看护 | L92-109 / L878-882；test L575-603 |
| 7 | 伪 usage 算术防伪 | **通过（附弱点）**：拒绝+续扫逻辑正确且在 fast path 上被测试证实；无 totalTokens 的 usage 形状不经验算直接信任 → F-P3-1 | L200-237；test L663-687 |
| 8 | 快速通道 skip 分支回归测试 | **通过**：`test_unneeded_envelope_types_are_skipped_but_needed_are_not` 显式标注 corpus incident 回归看护；紧凑 separators 前提在 fixture 层强制 + docstring 声明；「spaced 序列化 → 性能回退」无显式测试 → F-P3-3 | test L746-759 / L47-63 |
| 9 | 真实环境合规 R1(c)+R4 只读 | **通过（附义务提醒）**：授权链 = 用户 2026-09-18 会话授权（基线 md L10 留痕）+ DEC-204（decision-log L145 机录，明确「预授权不免除门禁」）；代码路径静态核实纯只读、无写 `~/.dsh` 路径。evidence-log 尚无 FEAT-032 实现证据行（TRIAGE/EVD-1072 为立项证据）——**属审查环节正常时序，Coordinator 闭环时 MUST 按 R4 逐条机写上报** | 基线 md §授权与边界；decision-log L145；evidence-log L2218/L2238 |

---

## 三、特别审查点

### 3.1 architecture-baseline regen 正当性 —— 正当

- R1 锚语义 = `infra/verify_workflow.py` 主文件物理行数（baseline `r1_mainfile_budget.path`）；新增 `governance_cost.py` 本身不进 R1 锚，**进锚的是引擎三处接线（实测 +20 行：24583→24603）**——充分理由成立。当前锚 24617 = 合并态实测（本次审查 Read EOF 行号 24617 独立证实）。
- 棘轮纪律遵循：exemptions 未新增（仍仅 FEAT-019 零配额披露条目）；`design_anchor_note` 延续实测为准口径；FEAT-032 +20 / FEAT-037 +14 的分解与申报一致。
- R6 197（+1 = governance_cost 冷导入面，stdlib-only 已由模块 import 区 L49-58 静态核实——仅 argparse/datetime/io/json/os/sys/time/pathlib）与 test_registry `FROZEN_ENGINE_IMPORT_COUNT=197` 同步。
- snapshots.json `key_count=86` = 合并态（FEAT-032 85 + FEAT-037 +1），`FROZEN_CLI_KEY_COUNT=86` / `FROZEN_CLI_KEYS=85`（registry 自身声明口径）两套冻结常量各自自洽；regen 时间戳 2026-09-18T02:51:05Z 与基线 JSON（02:49:58Z）时序合理。

### 3.2 并行工作边界 —— 未发现 FEAT-032 关联

`test_bootstrap_version_marker_injected_into_all_profiles`（4≠3）与 `test_hooks.py` replay 失败属 FEAT-037 中间态/活数据耦合，**不计入本报告 findings**。审查中核对：governance_cost.py / registry.py / 测试冻结常量均不触及 bootstrap 版本标记投影或 hooks 路径，未发现 FEAT-032 文件与上述失败的关联。

### 3.3 AI 专项 5 项 —— 全部通过

| 检查项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | **无** | 产品代码零 mock；测试仅 `unittest.mock.patch.dict` 环境变量（正当用途） |
| 硬编码返回值 | **无** | 全部指标由事件时间戳/token 字段计算；无假数据路径（测试 fixture 为合成数据，正当） |
| 幻觉 API | **无** | zstandard `ZstdDecompressor().stream_reader`、stdlib 均为真实存在且用法正确的 API |
| 未实现 TODO | **无** | 全文无 TODO/FIXME/占位实现 |
| 过度实现 | **无** | CLI 面（--sessions-root/--workspace/--format）为 §8 验收最小所需；无超范围功能 |

---

## 四、设计一致性（AUDIT-154 §8 FEAT-032 验收契约）

| 契约 | 裁决 | 依据 |
|---|---|---|
| 指标可机读输出（单命令 <5s） | **满足**（运行时数值为产物记录佐证 + 静态评估，未独立复跑） | schema `governance-cost-report/1`；duration 4393ms |
| 0.83.0 基线快照入库 | **满足，数值一致性有瑕疵 → F-P2-1** | md+JSON 落盘；两处 token 数值不一致 |
| 口径分离 TTFT/解码/工具/并行 | **满足（诚实披露形态）**：工具/LLM/残差三分 + residual 带标签不归因；TTFT/解码因事件模型无 first-token 事件物理不可分离，`CALIBRATION["llm_window_ms"]` 如实声明而非伪分离——符合审计 §4.3 防过度归因的本意 | CALIBRATION L701-728；审计 §4 L72-77 |

change-triage 对照披露：`FEAT-032.json`（tool_version 0.77.0）**无 `acceptance` 字段**，`files` 仅申报 2 文件（实际变更集 11 项），`side_effect.touches_real_env=false`——与「读取真实 sessions 目录」的后来事实存在申报时点差异；基线 md 已补 R1/R4 留痕，治理链自洽 → F-P3-6。

---

## 五、发现列表（每条含级别/位置/事实/影响/建议）

### BLOCKING（P0）

无。

### P1（关键）

无。

### P2（建议，不阻塞合并）

- **F-P2-1** `docs/research/governance-cost-baseline-0.83.0.md` L31 vs `governance-cost-baseline-0.83.0.json` L29-31 —— md 表格 token 数值与配套机读产物不一致：cache_read **5797.72M vs 5797511744（=5797.51M，差 ~0.21M）**；out **26.54M vs 26534750（=26.53M）**。同表时间指标（14736m36s/42.4%/53.6%/5.0%）、in=67.57M、98.4% 命中率口径均与 JSON 精确吻合。影响：该快照是 FEAT-034 等后续任务的同口径对照基准，数值必须可复算一致；0.004% 量级差异不改变结论方向，但来源不明（疑似另一次采样或换算笔误）。建议：以落盘 JSON 为准修正 md 两值，或在 md 注明表格数值的采样时点与 JSON 的对应关系。
- **F-P2-2** `governance_cost.py` L66-72 / CALIBRATION L723-727 —— GOVERNANCE_TOOL_NAMES 最小分类的**偏差方向未披露**：ask 之后 Coordinator 按治理协议执行的 read/pwsh（读 plan-tracker、跑 verify 子命令等）会被判为 `first_work_tool`，`time_to_work_ms` 系统性**低估**治理开销（把治理自读计为实质工作）。FEAT-034 验收（冷启动→首次 ask p50≤25s，另含 time-to-work 类消费）复验时数字将偏乐观。现有 calibration 披露了「generic tools 计入 work 候选」但未写明方向与量级。建议：在 `CALIBRATION["governance_tools"]` 追加一句偏差方向声明（"post-ask governance reads count as work — time-to-work is a lower bound of true governance cost"），或在基线 md 口径节补充。
- **F-P2-3** `test_governance_cost.py` L42-44 —— zstandard 缺失时 37 测试全部 `skipTest`：CI/新环境未装 zstandard 时本模块看护整体静默失效（unittest 报 skipped，门禁通常不拦），与项目 fail-closed 文化存在张力。建议：CI 显式安装 zstandard，或增加一个不依赖 zstandard 的依赖在场断言测试（缺失即 FAIL 并提示安装），使看护失效变为显式失败。

### P3（建议/披露，不要求修改）

- **F-P3-1** `governance_cost.py` L230-236 —— 算术防伪为单向：`totalTokens` 缺失（非 int）的 usage 形状不经验算直接信任；fast≡full 测试仅覆盖带 totalTokens 场景。建议：无 totalTokens 时回退 full parse 或显式披露该信任边界。
- **F-P3-2** `governance_cost.py` L148-153 —— corrupt 口径注释首句「cannot be interpreted as events」与细化口径（无 marker 且不可解析才计数）在 `null`/非 dict 行上存在措辞张力（null 不可解释为事件却不计数，test L398-406 断言如此）。建议注释首句精确化。
- **F-P3-3** 测试布局 —— 「harness 序列化改为 spaced → fast marker 全不匹配 → 静默回退 full parse（变慢但正确）」的退化方向无显式测试；正确性已由 fast≡full 等价兜底，属性能回归盲区。可加一条 spaced 形态烟测断言「仍解析正确」。
- **F-P3-4** 基线 JSON L5 —— 落盘产物含用户本机绝对路径（`C:\Users\peter\.dsh\sessions`）；`docs/` 为 repo_only 不随插件分发、读取在授权链内，风险低。披露备忘：后续如将基线产物纳入分发或示例，需先脱敏。
- **F-P3-5** `governance_cost.py` L143-147 —— fast scanner 依赖「envelope 字段先于 content」的 harness 序列化约定（已声明 + fixture 看护 + 破坏时全量回退仍正确）。接受，知会即可。
- **F-P3-6** `.governance/change-triage/FEAT-032.json` —— 无 acceptance 字段（tool_version 0.77.0 schema）、files 申报 2 项 vs 实际 11 项、`touches_real_env=false` vs 后来的真实 sessions 只读扫描（R1 授权后补且留痕）。机录时点差异披露；建议后续任务 triage 时把「将读取真实环境只读数据」纳入 side_effect 声明。
- **F-P3-7** `governance_cost.py` L638-640 —— 单文件解压无体积上限（`reader.read()` 全量入内存）；当前语料均值 ~2.5MB/文件无风险，超大单文件场景可加防御上限。

---

## 六、硬门槛裁决

| 门槛项 | 阈值 | 裁决 |
|---|---|---|
| P0 阻塞问题数 | = 0 | **0 ✓** |
| 5 维度全覆盖 | = 100% | **5/5 逐项有结论 ✓**（第一节） |
| 每条发现标注级别 | = 100% | **10/10 条有 P2/P3 标签 ✓**（0×P0 + 0×P1 + 3×P2 + 7×P3） |
| 设计一致性检查 | 已完成 | **已完成 ✓**（第四节，含 change-triage 字段缺失披露） |
| AI 专项 5 项检查 | 全部完成 | **5/5 ✓**（3.3 节） |

## 七、结论

**无 BLOCKING 问题。** 模块实现与申报事实全部核实相符（接线三处零混入、只读保证静态成立、fail-closed 完备、37 测试计数属实、基线校准值与审计逐值吻合）；3 条 P2 均为「不阻塞合并、建议本轮或随切片后续任务修改」级别。

## 结论：APPROVED_WITH_NOTES（P0=0/P1=0/P2=3/P3=7）

unresolved_blockers=0

> 遗留建议（非阻塞）：F-P2-1（基线 md 两处 token 数值修正）建议在 FEAT-033/034 消费基线前完成——对照基准必须可复算；F-P2-2/F-P2-3 可随切片 A 后续任务落地。
> 义务提醒（Coordinator）：审查闭环时按 R4 将 Developer 结构化返回的逐条命令上报机写 evidence-log（当前热区仅有 TRIAGE-FEAT-032 / EVD-1072 立项证据）。
