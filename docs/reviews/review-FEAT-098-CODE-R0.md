# FEAT-098 CODE R0 — 体验脊柱与调用成本账本

- 报告日期：2026-10-19（Asia/Shanghai）。运行证据来自 **2026-10-18 UTC**；10-19 仅复核保存结果和源码 hash，未重跑或改写原运行时间。
- 结论：NEEDS_CHANGE
- unresolved_blockers=3
- 审查基准 HEAD：`3622889ba35c909c07951045761257b97c9b662c`
- 范围：下列五路径的 FEAT-098 增量。SKILL 相对 HEAD 仅体验脊柱/成本两段四行，已提交 FIX-450 不属于本轮审查；其他票及已有审查报告不被本结论改写。

## 对象绑定

| 路径 | 文件字节 SHA-256 |
| --- | --- |
| skills/software-project-governance/SKILL.md | 820686802ac7a47344d54a691dd598bc2d7ac58f1fe0b3aee6e8647aa7a9f539 |
| skills/software-project-governance/infra/governance_cost.py | 19c98d1bfaa59a51ef584b0b02f5d0e654a1a5774e4d043d9fc4e4688300dae5 |
| skills/software-project-governance/infra/tests/test_governance_cost.py | 50ebe9127a9d2715d1afb4e10c76c89e53ee12f9b603150f8e2930f515cff6cd |
| docs/diagnostics/feat-098-cost-baseline.md | fe9e9bcfeee114d26b56bb03efed3cf453daeff98bc80aee1c68369f274d46be |
| docs/diagnostics/feat-098-cost-baseline.json | 9754b901d8919403afdbbd2f1d8d10c4e204365129aa19b7861d2c8d8a31294b |

10-19 复核上述五文件与原运行对象相同，HEAD 未变，R0 报告此前不存在。

## 阻塞发现

### R0-F1 / P1 / BLOCKING — 部分输入分解可以超过整个已知 prompt

位置：`governance_cost.py:495` 的 `_call_record()` 分解校验，以及 L580 起的 breakdown 汇总。

校验仅在 prefix、increment **同时非 null** 时运行。合法的部分观测只提供 prefix、未提供 increment 时，即使已知 prefix 已超过整个 prompt，也直接进入已知合计。

独立最小输入：exclusive input=100、cache read/write=0、output=0、total=100，`role_prefix_tokens=101`，不提供 `task_increment_tokens`。真实输出为：

```json
{"prompt":100,"role_prefix_tokens":101,"task_increment_tokens":null,
 "issues":["rates_missing"],
 "summary":{"known_sum":101,"known_calls":1,"unknown_calls":0,"complete_total":101}}
```

这与文档「已知分解超过已知 prompt 时置 unknown」冲突：未观测的另一个非负分量不可能消除已知分量已经超限的矛盾。影响是角色/任务输入账本产生不可能的完整已知结果，覆盖率也错误。

修复建议：已知 prompt 下校验每个已知分量及已知分量和，不要求另一分量先存在；矛盾值不得进入可信 breakdown 合计，并留下 issue/unknown 覆盖率。补 prefix-only、increment-only 超限与合法部分观测/显式零的回归。

### R0-F2 / P1 / BLOCKING — 实际采用的嵌套调用 ID 绕过返工自指校验

位置：`governance_cost.py:487` 的自指比较与 L509 起最终 `call_id` 构造。

账本支持 `data.message.requestId` 作为调用身份，但自指只比较未归一化的顶层 `data.get('requestId')`。同一条调用使用嵌套 ID 时，完整 source/cause/evidence 不能阻止它把自己认作有效返工上游。

独立输入：无顶层 requestId，`message.requestId='self'`，`work_kind='rework'`，`rework.upstream_call_id='self'`，并提供显式 cause/evidence/source。真实输出为：

```json
{"call_id":"self","work_kind":"rework","issues":["rates_missing"],
 "rework_links":[{"upstream_call_id":"self","link_status":"in_trace"}]}
```

与文档「拒绝自指」直接冲突，形成虚假的因果返工链及分类。当前正例仅覆盖顶层 ID，未验证最终实际使用的 fallback 身份。

修复建议：先统一计算/归一化最终 call ID，身份、去重、自指验证复用同一值；返工自指降为 unknown 并记录原因，不生成有效自指链。补嵌套 ID 及顶层 ID 含可裁剪空白等归一化路径回归，避免再次以原始字段校验最终身份。

### R0-F3 / P1 / BLOCKING — 身份冲突后的耗时仍任取首行，覆盖率虚报完整

位置：`governance_cost.py:521–548` 的 `summarize_calls()`，尤其 coverage 与 `known_duration_ms` / `duration_unknown_calls`。

同 ID 两条观测的显式 duration 分别为 100ms、900ms，其余相同，代码已把该 ID 标成 conflict；token/cost 基础会置 unknown，但 duration 和 coverage 仍使用选中的第一行。独立实测：

```json
{"conflicting_call_ids":["c1"],
 "forward_known_ms":100,"reverse_known_ms":900,
 "duration_unknown_calls":0,
 "duration_coverage":{"known_calls":1,"total_calls":1}}
```

同一组矛盾观测仅交换顺序，已知耗时就改变；同时仍宣称 1/1 有可靠耗时。这违反「冲突调用的汇总计量 unknown」和不猜归因原则，足以污染成功/探索/返工/等待的时间账本。

修复建议：统一定义冲突记录的可信字段资格，并让耗时汇总及相应 coverage 使用该资格；矛盾 duration 不得任取首记录计入已知时间。若工作归因本身冲突，也不得从首行制造确定分类。保留原始行供审计，补顺序反转、duration-only 冲突和其他归因冲突回归。

三个缺陷均来自本次新增账本逻辑；Reviewer 未修改产品代码或正式测试，只在授权 scratch 中编写复现。当前 **75 项测试通过不能覆盖这三处错误**。

## 正向验证、设计与职责边界

已读取版本规划及 `.governance/execution-packets.json` 的 FEAT-098 包：目标为 0.99.0，要求最薄可运行体验、调用口径、返工归因、基线与可靠回归；验收包仍为 triaged/NOT_RUN_YET，不把这些计划字段当作已完成证据。

正常路径的独立事实：

- QA 既有 venv：CPython 3.14.3，zstandard 0.25.0；无重复安装、无联网取费率。
- 原生 unittest **75 tests / OK / exit 0，0.118s**，含原59项及新增16项，验证既有 CLI/字段兼容和常规负例。
- 从交付 JSON 的8个合成事件生成仓内 `.zstd`，实际调用既有 `verify_workflow.py governance-cost-report --sessions-root <isolated-path> --format json` 与 text 两个真实 entrypoint，均 exit 0。逐 session `calls`、`call_accounting` 与保存基线逐项相等，5个调用候选、缺费率 cost=null；text 明示 unknown cost 与四类工作/unknown 数量。
- 常规 inclusive 输入1000含缓存读700/写100时，未缓存输入为200；prefix/increment未再次加到 usage。显式来源化费率、零费率与缺率的区别有真实回归；没有根据模型名称猜费率。
- 普通 compact/spaced JSON 的快慢解析、旧字段、同 session 去重/冲突披露、不同 session ID 命名空间与本地上游链测试通过。外部/未找到的上游明确 not_in_trace；本轮不把这些局部链路宣称为完整跨 session 因果重建。
- 合成快照明确 `synthetic_replay_not_production`；历史 RPG 汇总另标未重算、money/raw coverage 为 null。没有生产 trace，不能声称生产节省、实际账单或按 FIX 名称获得因果返工比例；残余墙钟未被推断成等待。

SKILL 的体验路径条款适用于 CLI/API 等产品，明确静态可达性、测试数或文件生成不能单独证明体验成功，失败/未运行不得借其他指标宣称完成。真实 CLI 重放已证明其正常最薄路径，但三条账本边界错误关闭前不能接受功能完成。

维护性方面，新增约275行集中在调用计量纯函数，没有引入网络、其他产品领域或新的写入服务；不因文件已有1372行就无依据断言为架构级阻塞。但 `_call_record` 的身份解析/验证分离及汇总资格散落已造成 F2/F3 的具体不一致。修复应收敛这些单一事实入口，必要时提取小型纯验证函数；不借本票进行无关大重构。

## 五维度与 AI 专项

| 维度 | 结论 |
| --- | --- |
| 正确性 | NEEDS_CHANGE：三个独立可复现的计量/身份边界缺陷，见 F1–F3。 |
| 安全性 | 没有新增凭证、权限扩张或用户数据写入；数据可信边界不足，不能将矛盾观测包装成已知。 |
| 可维护性 | 需统一身份及冲突后的字段资格，防止各汇总面各选一套规则；其余改动集中于既有成本报告领域。 |
| 性能 | 实际75项与最薄CLI耗时有记录，算法为线性处理；未做同环境大 trace 性能对照，不宣称吞吐或生产费用优化。 |
| 测试覆盖 | 正常75项及真实CLI通过，但独立边界3项均失败；必须新增永久回归并复审，不能以既有绿灯代替。 |

AI 五项完成：无 mock 成功返回或伪造生产采样；使用真实现有 CLI/API；合成数据及未知项有标签；无新增未实现 TODO 或无关扩展。F1–F3 是实际逻辑缺陷，不因测试由 AI 生成或数量足够而降低要求。

## 命令审计与原始证据

证据根：`.codex-sandbox/FEAT-098/review-r0/`。`command-audit.json` 保存每条真实 argv、cwd、UTC 起止、exit、日志及 impact。执行使用既有 `.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe`；HOME/USERPROFILE/TEMP/TMP/DSH_HOME 全部重定向仓内 scratch，未读取真实会话、启动 DSH、写用户配置或安装依赖。

下表所有时刻均为 **2026-10-18 UTC**，不是报告续写日：

| 命令标签 | UTC 起止 | exit / 影响 |
| --- | --- | --- |
| environment：读取解释器/zstandard版本 | 12:26:29.224685→12:26:29.292218 | 0；只读既有 venv，日志写 scratch |
| cost-tests：原生 unittest 模块 | 12:26:29.293484→12:26:29.603516 | 0；75项通过，测试临时文件在 scratch |
| prepare-trace：保存基线压缩为隔离输入 | 12:26:29.604902→12:26:29.678694 | 0；仅生成 scratch trace |
| cli-json：真实成本CLI/JSON | 12:26:29.679908→12:26:30.060954 | 0；只读隔离 trace，输出日志 |
| cli-text：真实成本CLI/text | 12:26:30.062902→12:26:30.452837 | 0；只读隔离 trace，输出日志 |
| boundary-probes：独立边界测试 | 12:27:16.845575→12:27:16.967508 | **1；3 tests / 3 failures / 0 errors**，对应 F1–F3 |

最小复现脚本 `boundary_probes.py` 可由同 venv 直接运行；完整输入/观测见 `boundary-observations.json`，没有依赖真实 HOME 或外部费率。证据绑定：

| 文件 | SHA-256 |
| --- | --- |
| command-audit.json | 4ff3b0f0df59c8ce07e9a71619ce821f5ffb11a346d61a7cf754acb1e9f50a20 |
| cost-tests.log | a498936e478755c34540e98d37219963f12e828679f0f239eaa811a4e6d9f7e2 |
| cli-json.log | cd1b3615b463f35ba5c801e2d520957ac200a0b2b4e4eed540450b32a6f3bec4 |
| cli-text.log | 37c57ebd26f31cf51864458ff00ad90ec8d68ee11d766e4003d9bffd26bbfe4d |
| boundary_probes.py | bb4279c7cb7d7f414dfc59b04a3846e83bfd950cd6a22a98629f6582e8a27789 |
| boundary-probes.log | 78a39adbd546bebe224921ea00a5c7d3fa47ee3a4a5ec8570ec2bd26ca1bcff6 |
| boundary-observations.json | 0023b62ef55c7113edcb33b9506998b06db8d045c6e7af6d59f102b217c878ca |

## 裁决与下一轮

P0=0，P1=3（F1/F2/F3，均 BLOCKING），P2=0；尚不批准提交/交付。Producer 应分别修复三个发现并补永久负例，再由同 Reviewer R1 逐条关闭；不得只改测试预期或把矛盾数据当有效部分和。

五维度、分级、设计与实际证据检查完成。完整 CI、生产账单、宿主实际体验及发布均未在本轮验收；诊断中旧预算数据是原时点测量，不替代 FIX-450 已提交后的集成预算复验。Reviewer 只新增本报告，未自修产品、修改 index/治理记录或改写其他审查报告。
