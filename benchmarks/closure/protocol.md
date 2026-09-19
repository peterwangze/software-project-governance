# closure 量测协议（M0 冻结 —— FEAT-049 · version-plan-0.86.0 §3 / arch round-3 P1-2）

> 状态: **冻结**（0.86.0 批 0 交付——量测协议 M0 批 0 内冻结，先冻结协议再采样再下结论）
> 依据: 0.86.0-arch-consult-round3-external.md §P1-2（协议要素清单）· version-plan-0.86.0.md §3（验收三维口径 / R-F5 入库策略 / R-F10 措辞规则）· 0.86.0-architecture-evolution.md §2.2（外部第二轮 Q-4 精化）
> 交付票: FEAT-049（批 0 / M0 契约冻结与验收基座）
> 本票边界: `runs/` 本票**不创建**（批 2.x 首次实测时按 §5 记录规格落盘）；`cases/` 用例文件同批 2.x 落库，本票以 §4 固定用例组描述冻结其定义。

---

## 1. LLM 往返定义（计数口径）

一次 **LLM 逻辑往返** = 一次完整的逻辑模型请求-响应周期。判定规则：

| # | 规则 | 判定 |
|---|---|---|
| 1.1 | 一次逻辑请求-响应计 **1** | 以"发出一次推理请求并取得完整回复"为计数单元 |
| 1.2 | 流式分片（streaming chunks）**不另计** | 一次响应的多个传输分片仍计 1 |
| 1.3 | 工具结果返回后的再响应**另计 1** | agent 调用工具 → 工具返回 → 模型再次响应，构成新的一次往返 |
| 1.4 | 传输层重试（网络超时/5xx/限流后的自动重发）**单列统计**，不并入逻辑往返 | 记入 `results.jsonl` 的 `transport_retries` 字段；目的：暴露基础设施不稳定，不污染确定性环节计数 |
| 1.5 | **不含**规划、评审、返工环节的往返 | 那些是非写入器可控变量（arch round-3 P1-2 原文：不写"每票 ≤2"） |

## 2. 测量起止点

- **起点**：被测链路的触发事件——Coordinator 向写入器/闭环链发出首个确定性操作指令（对标准 closure 路径 = 闭环启动调用）。
- **终点**：该链路的终态事件——结构化结果返回且效果核验完成（标准路径 = 任务状态推进至 `committed` 且投影/审计一致；异常路径 = 到达预定义的恢复终态或升级点）。
- **排除段**：等待人工判断（审查/裁决）的墙钟时间单列为 `wait_human`，不计入确定性环节往返数；等待外部（网络/git 远端）单列为 `wait_external`。
- 起止点之外的会话前置（bootstrap、上下文加载）**不在测量窗口内**。

## 3. 路径分类

| 路径类 | 定义 | 计数范围 |
|---|---|---|
| **标准路径**（standard） | 无冲突、无故障，全部确定性步骤一次通过 | 只计 §1 规则 1.1~1.3 的逻辑往返 |
| **异常路径**（exception） | 含冲突重判（CAS/operation_id）或故障恢复（commit 失败/push 凭据失败/push 超时 UNKNOWN） | 逻辑往返照常计数；恢复动作、人工干预次数、UNKNOWN 核验次数**单列**（version-plan §3：故障路径单列不隐藏） |
| **排除路径**（excluded） | 规划/设计/评审/返工环节 | 不计数（非写入器可控） |

**三维验收口径**（version-plan §3，判定不得混淆）：

1. **历史相对改善**：`NOT_EVALUABLE`（无可信历史 trace 基线——不得宣传达成；固定措辞见 §6）。
2. **新版绝对目标**：标准 closure 路径 LLM 逻辑往返 **≤ 2**（按本协议 §1~§3 口径实测；M3 落地后判定）。
3. **机制正确性**：原子性/幂等/恢复/门禁按功能与故障测试验收（混沌三边界 kill+resume 零人工修复）——独立可验证，不受基线缺失影响。

**门槛变更纪律**：不得测得新版 3 次后为过门改门槛——改目标 = 有理由、有版本记录的需求变更（version-plan §3 原文）。

## 4. 固定用例组（三路径——旧新同协议测量）

> `cases/` 具体用例文件由批 2.x 按【】内描述落库；本节为冻结的用例组定义。每组用例 MUST 记录：输入快照、模型/提示模板/工具配置/代码 revision（§5）。

- **用例组 A【standard-success】标准成功**：一条完整标准 closure——任务进入 dev → 实现 → 审查通过 → 结构化证据追加 → 状态推进（review→approved→completed→committed，走 FEAT-042R 写入器 + M0 契约冻结面）→ 投影/审计一致。判定：全链自动完成、零冲突、零人工干预、逻辑往返数记录。
- **用例组 B【conflict】冲突**：构造 CAS 期望版本过期（`revision_conflict`，含 observed_revision 返回与调用方重判）与同 operation_id 异载荷（`operation_id_conflict`）两类冲突各 ≥1 次。判定：冲突被结构化拒绝、无静默换版重试、重判后收敛、最终一致。
- **用例组 C【recovery】恢复**：三边界故障注入（commit 失败 / push 凭据失败 / push 超时 UNKNOWN）各 kill 一次后 resume。判定：effect-based 恢复（查世界不信日志：push 超时先核远端是否已含目标 SHA 再决定）、零重复追加、零丢失、零人工修复（混沌测试发布门口径，version-plan §2 批 2.2）。

## 5. 记录规格（runs 记录结构——本票不创建 runs）

`benchmarks/closure/runs/<run-id>/`，**标准库生成**（无第三方依赖），**敏感脱敏**（凭据/令牌/用户路径不入文件）：

```
runs/<run-id>/
├── manifest.json    # 一次测量运行的元数据
├── results.jsonl    # 逐事件记录（每行一个 JSON 对象，append-only）
└── summary.md       # 人读摘要（结论 + 与门槛对照）
```

`manifest.json` 必备字段：

| 字段 | 含义 |
|---|---|
| `run_id` | 运行唯一标识 |
| `measured_at` | 测量时间（ISO 8601，UTC） |
| `protocol_revision` | 本协议冻结版（`m0-r1`，随 fixtures manifest 演进） |
| `code_revision` | 被测代码 git commit SHA |
| `model` / `prompt_template` / `tool_config` | 模型、提示模板与工具配置标识（M0 冻结要求：模型/提示模板/工具配置/代码 revision 记录） |
| `use_case` | 用例组标识：`standard-success` / `conflict` / `recovery` |
| `path_class` | `standard` / `exception`（§3 分类） |

`results.jsonl` 每行必备：`seq`（顺序号）、`event`（逻辑往返/工具调用/传输重试/恢复动作/人工干预/UNKNOWN 核验）、`llm_rounds_delta`、`transport_retries_delta`、`ts`；异常路径另记 `failure_point` 与 `recovery_action`。

`summary.md` 必备：逻辑往返总数、传输重试总数、冲突次数、恢复动作数、人工干预次数、UNKNOWN 核验次数、与 §3 门槛的对照结论。

**入库与边界**（version-plan §3 R-F5 / arch round-3 P1-2）：

- `protocol.md` + `cases/` 入库（版本化协议与用例是发布产物）；`runs/` 由创建批次加入 `.gitignore`（本地保留原始 trace，敏感面不出仓库外但不入 git 历史）；EVD 记 run-id 与摘要（可追溯不膨胀）。
- **测量工件 JSON ≠ 业务存储 JSON 化前移**——本目录工件与 `.governance/` 业务存储是两个域。
- M2 后测量结果作为证据引用导入时，**保留原始测量时间 + 导入时间**（不伪装 M2 自动生成）。

## 6. 基线与措辞规则

- **无可信历史 trace 且旧版可运行** → 旧版重演基线（旧新同协议；明确标注**非"历史实测"**）。
- **无法恢复等价环境** → 维度①维持 `NOT_EVALUABLE` 并记录原因 + 绝对目标照常测（维度②）。
- **CHANGELOG/roadmap 固定措辞**（version-plan §3 R-F10）：维度①一律写「基线不可评估（无可信历史 trace）——未宣传达成」；发布不受阻（三维表口径）。
- 评估结果（PASS/FAIL/NOT_EVALUABLE）与继续策略（BLOCK/ADVISORY）分轴——见 contracts.py `EVALUATION_RESULTS` / `CONTINUATION_POLICIES`（M0 face 2/3 冻结面）。
