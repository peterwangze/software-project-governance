# 治理成本基线快照（0.83.0）——FEAT-032 交付产物

> 任务：FEAT-032（P1，v0.84.0，AUDIT-154 切片 A-1） | 生成时间：2026-09-18T02:49:58Z（本地）
> 数据源：`C:\Users\peter\.dsh\sessions`（298 个 `session.v3.jsonl.zstd`，生成时点快照——语料为活动目录，数字会随后续会话增长）
> 生成命令：`python skills/software-project-governance/infra/verify_workflow.py governance-cost-report --sessions-root <dir> --format json`（单命令 4.8s < 5s 验收线）
> 配套机读产物：本目录 `governance-cost-baseline-0.83.0.json`（schema `governance-cost-report/1`，含全量每轮指标与 calibration 口径披露）

## 授权与边界（R1/R4 留痕）

- **授权**：用户 2026-09-18 会话明确授权读取其会话轨迹用于本分析（"你可以实际去找一些会话……辅助分析"）——R1 (c) 逐项授权路径；本任务对 sessions 目录**仅只读扫描**，零写入、零移动、零删除（破坏性红线 AUDIT-146 / FIX-271 R3）。
- **命令上报（R4）**：本次基线生成对真实环境共执行 2 次扫描命令（--format json 落盘本目录；--format text 生成摘要），均 exit=0；另有开发期剖析/等价性验证若干次只读扫描，逐条见 FEAT-032 Developer 结构化返回（Coordinator 机写 evidence-log）。

## 口径（详见 JSON 内 `calibration` 字段与模块 docstring）

1. 全部时间为**事件时间戳原始差值**，不加工不推算（AUDIT-154 报告 §4.3）。
2. token 为**累计请求量**（in / cache_read / out），非上下文驻留量（§4.1）。
3. `llm_ms` = 各 step 内「step/start → 首条 assistant/message」窗口和（TTFT 与解码在事件模型中不可分离，如实合并报告）；`tool_ms` = 配对 tool/call→tool/result 时长和；`other_residual_ms` = 轮时长 − llm − tool 的**带标签算术残差**，不归因单一因素（§4.3/§4.4）。
4. `user/message` 无 turn 字段，按事件序归属当前 turn（EVD-1071 / 报告 §2）。
5. ask_user_question 挂起时长（用户等待）单列于 `ask_suspended_ms`；**包含在轮总时长内**（§4.4：累计时长含用户等待与闲置）。
6. 治理轮识别口径与 EVD-1071 一致（`/governance` 前缀 / `name="governance"` / `<skill_content name="governance"`）。

## 全语料总量（298 会话 / 998 轮）

| 指标 | 值 |
|---|---|
| 轮墙钟合计 | 14736m36s（≈245.6h） |
| LLM 时间占比 | 42.4%（6242m36s） |
| 工具时间占比 | 53.6%（7895m21s） |
| 残差占比 | 5.0%（730m4s） |
| ask_user_question 挂起（用户等待）合计 | 4694m49s（93 次，max 831m15s——含挂起后用户长期离开的会话） |
| 累计 token | in 67.57M / cache_read 5797.51M / out 26.53M（缓存命中率 ≈98.4% of 计费输入口径；数值以配套 JSON 为权威——md 与 JSON 如有出入，以 JSON 为准〔review-FEAT-032-CODE-R0 P2-1 修正：活动语料连续两次采样存在微小漂移，本行已对齐 JSON 数值〕） |
| TTFA（全部轮，N=76） | p50 2m09s · p95 18m44s · max 915m47s* |
| 进入实质工作时间（全部轮，N=75） | p50 3m36s · p95 321m14s*（endpoint：first_work_tool=60 / turn_end=15） |
| 扫描性能 | 4.4s（298 文件 / ≈210MB 压缩 / ≈750MB 解压） |

\* p95/max 被长挂起会话与**活动会话**（扫描时点仍开放、尚未结束的 turn 以 turn 已流逝时间为界）拉高——这正是 §4.4 预警的"累计时长含用户等待与闲置"，属口径内真实值，解读时以 p50 与治理轮子集为准。

## 治理轮子集（与 AUDIT-154 §3.1 对照校准）

| 指标 | 本次快照（N=5 治理轮） | AUDIT-154 §3.1 实测（5 轮） |
|---|---|---|
| TTFA p50 | **271.8s（4m31.8s）** | 中位 ~4.5min；样本含 4m31.8s |
| TTFA max | 428.0s（7m08.0s） | 7m08.0s ✓ |
| 进入实质工作时间 p50 | 370.0s | —（新增指标，无历史对照） |

**校准结论**：正式模块对 EVD-1071 五个 /governance 治理轮的 TTFA 复现值与审计报告逐轮吻合（p50=271.8s 即报告样本中的 4m31.8s，max=428s 即 7m08.0s）——研究脚本逻辑提升未引入漂移。

## 基线用途与后续

- 本文件是 0.83.0（FEAT-033~040 改造前）的**治理成本基线**：FEAT-034（首次交互前置）验收「冷启动→首次 ask p50≤25s/p95≤45s（轨迹复验）」、切片 A 整体验收均以同口径复跑 `governance-cost-report` 对照本快照。
- 复跑方式见 TOOL-053（`infra/TOOLS.md`）；正式模块 `infra/governance_cost.py`，研究脚本（`project/research/dsh-trace-analysis/`）已改为 deprecated 指针，不再维护双源。
- zstandard 为可选运行时依赖（缺失时命令 fail-closed 报错，不静默降级）；依赖登记决策留 Coordinator（未修改 requirements/pyproject）。
