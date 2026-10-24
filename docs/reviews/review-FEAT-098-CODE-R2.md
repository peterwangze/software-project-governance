# FEAT-098 CODE R2 — 类型资格签名独立复审

- 日期：2026-10-20（Asia/Shanghai）；本轮实际命令时间为下述 2026-10-20 UTC。
- 结论：NEEDS_CHANGE
- unresolved_blockers=1
- P0=0，P1=1（R2-F3，BLOCKING），P2=0。
- 审查 HEAD：`e28e67c6fb3c3c15fda278d179bf8abc9daae8bd`。本票五路径尚未提交；远端 CI 39243282183 的成功不能证明这些工作区字节通过 CI。
- Reviewer 身份：**新独立实例**承接原 R0/R1；不是原 Reviewer 的恢复实例。已加载 `agents/code-reviewer.md`、`skills/code-review/SKILL.md`，读取前轮报告、失败 raw、执行包及五路径增量。按派发授权运行隔离验证并仅新增本报告和 Reviewer scratch，不修产品、不写治理/index/refs、不提交推送。
- 前轮报告：R0 SHA256 `76138cc983c9c6a6f033288a9a967eb345845814176fe3350d17db3fe252d263`；R1 SHA256 `3897b375233b20267b2260949a409237d61307ae5d4fa1e3df5b3924fb103117`。二者原 NEEDS_CHANGE/3、NEEDS_CHANGE/1 和旧 RED 均保留，不以本轮重跑绿覆盖。

## 对象绑定与保全

| 路径 | 当前文件字节 SHA256 |
| --- | --- |
| skills/software-project-governance/SKILL.md | 820686802ac7a47344d54a691dd598bc2d7ac58f1fe0b3aee6e8647aa7a9f539 |
| skills/software-project-governance/infra/governance_cost.py | cbe400c6d0182efe9c3759b7e6dc4618537e97352c1d87075c24afc51f652fdd |
| skills/software-project-governance/infra/tests/test_governance_cost.py | bfb6a750c5f5c355f41ab3c3d4943cf30e81c55ffecf23037152e55d60955d33 |
| docs/diagnostics/feat-098-cost-baseline.md | ab261abf1b14b936d4fadce5895228cd9240b6829a184104e23b9f89a134c94c |
| docs/diagnostics/feat-098-cost-baseline.json | 9754b901d8919403afdbbd2f1d8d10c4e204365129aa19b7861d2c8d8a31294b |

按上表顺序拼接 `path + NUL + hex_sha256 + LF` 的集合 SHA256：`c07f1f25db9371b6335a32bdfe435832b6be58327051caedbb1e30a896d7348d`。隔离 Git 配置、命令级 `-c core.autocrlf=true` 的三 tracked 产品文件 diff SHA256：`6be59ffb9e25c9713756edef0083b5406b7bf13dab39e4e0b28659216efaf656`；两份新增诊断文件由完整文件字节绑定。

`before-hashes.json` 与 `verified-bindings.json` 覆盖76个既有文件，前后均相同：五产品、R0/R1报告和各自 raw、Producer R2 目录，以及暂停 hook/test。暂停 `infra/hooks/commit-msg` SHA256 `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`，`infra/tests/test_hooks.py` SHA256 `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`；仅作 hash 保全，不审暂停 WIP。

Producer `rework-r2/command-audit.json` 的14条命令已读取，包含两个 RED 和修后结果；它们不是本 Reviewer 的运行。其未完成的最终保护/静态结果不被追造。本轮在新目录独立完成相应验证，归属和时间分开。

## 前轮逐项裁决

| 原 finding | R2 状态 | 独立事实 |
| --- | --- | --- |
| R0-F1：缺一个分量时另一分量超 prompt 仍可信 | **已修复，维持解除** | `governance_cost.py:469–477` 校验已知非负分量的下界和。原 prefix101/prompt100、increment-only及已知和越界均拒收；合法部分、边界100和显式0保持，未测分量仍 null。继承独立组合和永久回归均通过。 |
| R0-F2：nested requestId 自指返工 | **已修复，维持解除** | `:483` 统一归一化顶层/嵌套身份供自指、输出、去重使用。nested、空白、非法顶层 fallback 等独立探针通过；自指 work_kind=unknown，无有效自指链。 |
| R0-F3：duration冲突任取首行 | **原 duration 分支已修复** | `:557–601` 统一可信投影；100/900ms、来源归因矛盾、step-derived矛盾不进入已知时间/工作桶/coverage；24种重复与反序排列相同。缺测加单一合法0/123ms窗口仍合并，原始行保留。 |
| R1-F3：类型相等但计量资格不同 | **bool与计数float分支已修复；同根阻塞保留** | `:530–553` 区分 JSON bool，并以实际 `_count()` 及共享字段表生成计数资格。40组独立字段交叉、R1原两脚本、真实bool/counter/duration CLI均通过。普通合法价格0/0.0、1/1.0等价也保持。但 `_priced_call()` 的数值计算资格仍可能不同，见下项。 |

## R2-F3 / P1 / BLOCKING — 等值合法费率仍可因中间乘积溢出获得不同计价资格

位置：`governance_cost.py:455–460` 的费率资格/价格计算，`:548–553` 的签名以及 `:575–576` 的 duplicate 选择。

当前签名保留合法 int/float 数值等价，但价格按原 Python 类型执行 `tokens[key] * rate / 1_000_000`。整数先作精确乘法，浮点数先作浮点乘法；即使两个费率**数值精确相等、均为非负有限值**，中间乘积也能只在浮点路径溢出。现有签名仅补齐计数资格，没有覆盖这个实际费用资格差异。

独立 API 与真实 CLI 输入均为同 session、同 requestId 的两条 assistant 观测；exclusive input=100、cache read/write/output=0、total=100，显式 TEST currency 与 `synthetic:rates` 来源。唯一差异为 `rates_per_million.input_uncached` 的 JSON 数字类型：

```python
rate_float = 1e307
rate_integer = int(rate_float)
assert rate_integer == rate_float  # 选择可精确相等的一对，不是十进制近似相等
```

整数路径得到有限价格 `1e303 TEST`；浮点中间乘积成为 infinity，单条调用被正确降为 `cost=null` / `price_out_of_range`。问题出在两条观测的签名仍相同，汇总按第一条决定是否有完整费用。

| 真实隔离 zstd 行序 | CLI exit | duplicate_records | conflicting_call_ids | cost.complete_total | unknown_calls |
| --- | ---: | ---: | --- | --- | ---: |
| 等值整数费率在前 | 0 | 1 | [] | 1e303 TEST | 0 |
| 等值浮点费率在前 | 0 | 1 | [] | null | 1 |

API 等价性断言和真实 CLI 结果比较器均 **exit1**，分别保存 `equal-arithmetic-range-observations.json` 与 `cli-range-observations.json`。这使用极端有限数值，**没有证据表明正常生产费率受到影响**；但产品未声明更小的可接受数值范围，且本轮明确要求费用资格与签名等价一致、反序相同。不能将已经被当前计算器判作 unknown 的观测借 duplicate 变为完整已知，因此保留同根一条 P1，不额外计作第二条阻塞。

修复建议：使数值等价的合法费率经过同源的计算/范围资格得到相同计价结果；如不能计价，应统一保留 unknown 或触发冲突，不能依赖首行。可以统一数值计算路径，或定义并共同验证明确的数值支持范围；不要用全局区分 int/float 破坏已接受的0/0.0、1/1.0兼容。补本反例的两种行序及永久回归，再复核原 bool、计数、合法零、唯一已知时长和基线。Reviewer 未改产品或正式测试。

## 独立正向验证及 SKILL 影响

- 既有 QA replay-venv，成本模块 **92 tests / OK / exit0 / 0.153s**；无安装、联网或取生产费率。
- R1 `combinations.py`、`numeric-counter-probe.py` 按原字节复制到本轮 scratch 后运行：**9方法全部OK / 0.003s**；原整数/浮点计数两例均反序相同且冲突明确。原 R1 raw 未写入。
- 另建独立矩阵：5种 usage、2种分解、显式 duration、4种费率的 **40组** bool/数值与计数int/float冲突全部顺序独立；所有冲突 token/breakdown/cost未知、duration coverage=0，原始行不变。另 **12组** 普通合法 numeric rate 对保持 duplicate 与等价费用。
- 从原8事件基线重新压缩隔离 zstd，经真实 `verify_workflow.py governance-cost-report` JSON/text：逐 session `calls` 和 `call_accounting` 与保存 JSON 逐字段完全相等，仍5调用、缺率费用null，text显示unknown费用和四类/unknown工作计数。原 JSON SHA未变。
- 真实CLI另跑5对反序：true/1费率、false/0费率、usage 1.0/1、duration 1.0/1、合法rate 1.0/1。前四对隔离为conflict/duplicate0/cost null；最后一对duplicate1/无conflict/0.0001 TEST；每对完整 `call_accounting` 相同。两个极端费率CLI如前节，单独保留FAIL。
- SKILL 相对 HEAD 仅FEAT-098两段四行增量；完整 SHA 与R0/R1相同。内容限定最薄可运行体验及同口径账本，禁止以静态数量替代体验、猜费率/返工/等待，与当前执行包目标一致。相关 **M0FixtureManifestTests 6/6 OK**（含SKILL完整行为契约pin），预算直接回归 **2/2 OK**。当前native三profile均PASS：resident 4441/5925/6197，skill15440；未拿历史预算数替代现场结果。
- 五路径 `git diff --check`、默认静态 verify、cross-references、manifest-consistency 均exit0；命令级CRLF规范化，没有改用户Git配置。

## 五维度、设计一致性及 AI 专项

| 维度 | 本轮结论 |
| --- | --- |
| 正确性 | NEEDS_CHANGE：原F1/F2及duration、bool、计数资格修复成立；等值费率在当前允许的极端数值仍有可复现费用资格/首行依赖。 |
| 安全性 | 无新增凭证、网络、权限或用户数据写服务；非法/不可计价观测不能通过重复身份获得已知费用，剩余具体问题见R2-F3。未做全仓安全审计。 |
| 可维护性 | 共享字段表及 `_count()`、身份归一化、统一可信投影符合单一事实源，仍在成本报告领域；费用资格与签名间还需收敛，无需借本票做全模块重构。 |
| 性能 | 按调用/字段线性遍历，没有新增外部I/O；本轮测试/CLI实际耗时可复查。未作大trace吞吐、生产账单或节省量验收。 |
| 测试覆盖 | 92常规项、原反例、矩阵、真实CLI、M0及预算均有证据；独立范围反例RED说明目前正例不足以关闭F3。未量测行覆盖率，不把数量宣称为完整覆盖。 |

设计一致性：对照FEAT-098执行包、五文件契约及旧报告，保留既有schema/旧字段、缓存互斥、分解不重复加总、来源化返工、unknown/null和可重放合成基线；未将本地上游链宣称为完整跨session因果图，未推断残余时间为等待。本轮剩余资格不一致与可靠、泛化的账本目标冲突。

AI专项5项逐一完成：无生产mock成功返回；无硬编码生产账单/节省量；使用实际已有CLI/API，未引用不存在的接口；新增范围无未实现TODO；未引入无关产品扩展。TEST费率及trace明示synthetic，原历史RPG统计不是本轮重算生产证据。

## 命令审计与原始证据

Reviewer证据根：`.codex-sandbox/FEAT-098/review-r2/`。`command-audit.json` 对本轮隔离测试、CLI、静态检查及证据命令逐条保存实际 argv/cwd、UTC起止、exit、stdout/stderr及SHA、环境、影响路径。工具层最初的只读bootstrap/源码读取保留于本会话调用记录，不编造其UTC。Producer14条及R0/R1命令不混入本Reviewer命令数。

测试/CLI HOME、USERPROFILE、APPDATA、LOCALAPPDATA、DSH_HOME、TEMP/TMP、XDG和PIP/UV/npm缓存均先验证在本Reviewer目录内再重定向；清DSH overrides、NODE_PATH与真实session roots，PATH仅既有QA Python/Git/System32；使用隔离Git config/NOSYSTEM。输出和合成输入仅写scratch，无真实会话读取、DSH/SDK运行、安装或网络。它是执行环境约束说明，不是系统调用级监控声明。

| 关键命令label（完整argv见JSON） | 实际UTC 2026-10-20 | exit / 实际结果 |
| --- | --- | --- |
| cost-module | 08:21:24.002975→08:21:24.397224 | 0；92 OK |
| inherited-combinations-corrected | 08:21:34.934829→08:21:35.044708 | 0；9 OK |
| inherited-numeric | 08:21:25.529412→08:21:25.606988 | 0；原2例解除 |
| m0-pins | 08:21:26.081872→08:21:26.245875 | 0；6 OK |
| independent-type-matrix | 08:22:36.610513→08:22:36.692669 | 0；40冲突+12合法对 |
| equal-arithmetic-range | 08:22:50.693614→08:22:50.807189 | **1；API等价断言失败** |
| cli-batch | 08:23:26.270384→08:23:32.109972 | 0；14个实际CLI子命令均另有各自审计 |
| compare-baseline-and-types | 08:23:32.637671→08:23:32.720617 | 0；5对正常CLI+原基线 |
| compare-range-cli | 08:23:33.218922→08:23:33.318984 | **1；真实CLI反序费用不同** |
| diff-check / static-verify | 08:23:54.242747→08:23:57.180869（各自独立命令） | 0 / 0 |
| skill-budget-regressions / live-budget | 08:24:32.170426→08:24:33.015472（各自独立命令） | 0 / 0 |
| check-cross-references / check-manifest-consistency | 08:24:33.489269→08:24:35.358150（各自独立命令） | 0 / 0 |
| protection-check | 08:24:35.834333→08:24:35.934238 | 0；76既有文件不变 |
| read-history-raw | 08:25:08.289815→08:25:08.379923 | 0；前轮raw关键hash及旧FAIL确认 |

审查工具准备失败也保留：PATH收紧后第一次rg不可达（子命令未启动，工具调用trace有记录）；一次PowerShell `@python`参数被解释为splat导致WinError2/exit127；新scratch曾命名 `inspect.py` 遮蔽stdlib，首次继承组合导入失败/exit1。已分别用明确PY标记和scratch文件重命名纠正，后续9方法实际执行通过；它们不冒作产品FAIL或被删除。最早范围探针使用的两个十进制数并不精确相等，实际无冲突错误；该结果仍保留，最终BLOCKING只依据精确相等的修正输入和真实CLI。

| Reviewer证据 | SHA256 |
| --- | --- |
| equal-arithmetic-range-observations.json | c9608e67603be274e2396fd54cb99186cbe691d83a5f506a5b0edd0651ac7578 |
| cli-range-observations.json | 646c8d5e4b4dbf5a921eff767fe457762f16b3c1bb94d006d86a15293fd6620c |
| cli-observations.json | 2118e206d3f451a66b1610adff1030589ccf545c160998948516f846a911a463 |
| verified-bindings.json | ae393226ff7dc8656150c377ae2ae1dc5c77c9a6064f0fc77410ef1c1e1a8154 |
| logs/cost-module.stderr | 0791667777a2d6f105aecf42770748654b891e26498d9510c1a3c7ff0139fba4 |

## 硬门槛与裁决

五维度、设计一致性、AI专项、finding分级及可复查证据已覆盖，P0=0；仍有P1 BLOCKING=1，故 **NEEDS_CHANGE，unresolved_blockers=1**。原bool/count具体错误已解除，不等于通用费用资格闭合。建议Producer按同源数值语义最小整改后复审；不得把当前报告写成已通过，也不因普通92绿或已提交HEAD的远端CI成功关闭本票。

完整发布、全仓CI、生产费用、真实宿主体验与DSH能力不由本报告批准。Coordinator负责机器记录本轮full scope与上述五bind-file，并释放报告锁；Reviewer没有自写REVIEW行或更改治理终态。
