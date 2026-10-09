# 治理开销实测分析——像素风RPG会话 session-f3f46901（2026-10-09）

> 分析对象：外部宿主项目 `D:\AI\agent\deepseek\web\game\像素风RPG游戏` 的治理会话（用户反馈：「几乎大部分的时间和 token 都消耗在治理动作本身」）。
> 数据源：DSH 会话事件流 `~/.dsh/sessions/--D-AI-agent-deepseek-web-game-~50CF~7D20~98CERPG~6E38~620F--/session-f3f46901-b553-4901-8a21-8f8c5f0c18cd/session.v3.jsonl.zstd`（64 轮 405 步，2026-10-08T23:50Z 创建，跨度 748 分钟）+ 同目录 41 个子代理会话。
> 方法：解压事件流，按 step 归类工具调用（治理读/治理写/审查派发/等待轮询/产品操作），聚合 `assistant/message.usage`（totalTokens=缓存读+未缓存输入+输出）；时间归属用 gap-cap 180s 剔除轮间空闲。
> 用途：FEAT-090/091/092 的需求源证据（TRIAGE-FEAT-090/091/092）。

## 1. 总量画像

| 维度 | 数值 |
|---|---|
| 主会话显示 token | 103.65M（=GUI「104M tok」；缓存读 ~100.5M / 未缓存输入 2.55M / 输出 0.54M） |
| 缓存命中率 | 98%（计费口径 ~3.1M：未缓存 in+out） |
| 子代理 41 个显示 token | 552.3M（未缓存 in 10.88M + out 4.09M） |
| 全系统合计 | ~656M 显示 token（计费口径 ~18.1M） |
| compaction | 2 次，各剪 ~184K |
| 墙钟跨度 | 748 min（12.5h，含空闲）；活跃（gap-cap 180s）~4.5h |

## 2. 主会话（Coordinator）405 步归属

| 类别 | 步数 | 显示 token | 活跃时间 | 说明 |
|---|---|---|---|---|
| text-only（纯推理/叙述） | 66 | 18.84M | 1217.7s | 含轮末总结 |
| product（直接产品操作） | 62 | 18.70M | 1072.4s | |
| gov-read（治理读取） | 96 | 16.50M | 2198.4s | plan-tracker 直读 20、execution-packets 12、evidence-log 6 |
| wait-poll（睡眠/轮询） | 46 | 13.15M | 8163.9s | **35 次 Start-Sleep（22×300s/6×330s/5×320s/5×310s…）≈2.9h** |
| other-pwsh（多为治理 CLI） | 38 | 11.24M | 995.5s | verify_workflow 58 次：check-governance 21 + 裸全量 21 + write-guard 3 + locks-release 2 + 其他 |
| gov-write（治理记录写入） | 47 | 11.15M | 1278.9s | **输出 0.15M > product 0.11M** |
| subagent-review 派发 | 24 | 6.83M | 353.4s | 11 REV + 7 FIX |
| 其余（list_agents/route/dev 派发/ask 等） | ~22 | ~8.0M | ~1450s | ask_user_question 仅 2 步 |

治理/协调相关步骤合计 ≈ 220/405（54%）。**governance-bootstrap 快路径仅用 1 次**（FEAT-034 现场失效证据）。

## 3. 子代理 41 个（552.3M）

| 分类 | 数量 | 显示 token | 说明 |
|---|---|---|---|
| 产品 FEAT | 12 | 168.7M | 含 FEAT-011 剧情对话 79.4M/277 步 |
| 审查 REV | 11 | 99.4M | 含 REV-005-R2 9.96M、REV-007-R2 7.36M、REV-009 22.7M |
| 修复 FIX | 7 | 101.5M | 含 FIX-002 49.3M |
| AUD-001 音频合成器 | 1 | 90.1M | **409 步**（单任务无上限长跑） |
| CONTENT 地图 | 4 | 41.1M | 含 CONTENT-002 23.9M |
| ART 美术 | 2 | 27.8M | |
| INFRA | 2 | 20.3M | |
| DES | 2 | 9.2M | |

审查链（REV+FIX）≈ 200.8M = 全系统 31%。子代理内部治理 I/O=0（verify_workflow 0 次、skill ≤1）→ 子代理开销 = 步数 × 上下文重建。

## 4. 根因（六条）

- **D1 串行化+睡眠等待**：Gate/锁/逐票审查促成串行；Coordinator 等待期无反空闲派发队列 → Start-Sleep 轮询（活跃时间 50%）。会话末尾一次并行派发 5 FEAT 成功，证明并行可行。
- **D2 复审全量重建上下文**：T1 触发的 R2 重审全量产物（契约仅要求注入前轮报告路径）。
- **D3 健康检查频率失控**：42 次全量/check（协议规定「后置深检」被执行为逐轮检查）。
- **D4 快路径现场失效**：六层 fallback 指令面过宽，1 次快路径 vs 42 慢路径。
- **D5 子代理无预算**：execution-packet 约束范围不约束步数 → 409 步/90.1M 失控。
- **D6 治理记录读改写放大**：evidence/plan-tracker 全文件 read+edit 对反复推入上下文，助推 2 次 compaction。

## 5. 优化映射（→ 任务）

| 根因 | 任务 | 措施 | 预估收益 |
|---|---|---|---|
| D1/D3/D4 | FEAT-090 | 并行优先派发+禁睡眠契约；检查事件化（3 触发器）；热路径单源 | 消除 ~2.9h 等待；检查 42→~6；重复读 20→0 |
| D2 | FEAT-091 | delta 复审（diff+前轮报告+验收标准）；批量审查 2-4 产物/Reviewer；报告摘要注入 | REV 族 99M→~50M；R2 单次 9-10M→≤3M |
| D5 | FEAT-092 | execution-packet budget 字段+检查点拆分（advisory） | 防单任务 400 步/90M 失控 |
| D6 | （随 FEAT-091/后续） | evidence 追加式写入已有 evidence-append CLI——推广使用即可，无需新票 | gov-write 输出 ~0.15M→~0.06M |

## 6. 边界与诚实声明

- 「104M tok」为显示口径（含缓存读）；真实计费口径 ~3.1M（主）+~15M（子）。主要成本是**时间与延迟**（12.5h 墙钟、2.9h 睡眠、2 次 compaction），不是账单 token。
- 步骤分类按工具调用启发式归因，混合步骤归主类，个别边界（other-pwsh 中少数产品构建命令）可能小幅高估治理占比（±3%）。
- 本分析不构成对复审/门禁/证据义务的否定——所有优化以「安全语义不回退」为前提（复审必达/fail-closed/升级确认门不变）。
