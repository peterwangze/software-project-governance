# FEAT-098 CODE R1 — 三项计量边界复审

- 日期：2026-10-19（Asia/Shanghai）；本轮运行时间为下述实际 UTC。
- 结论：NEEDS_CHANGE
- unresolved_blockers=1
- 前轮：`docs/reviews/review-FEAT-098-CODE-R0.md`，SHA256 `76138cc983c9c6a6f033288a9a967eb345845814176fe3350d17db3fe252d263`，保持原字节。
- 派发时 HEAD：`c82cc9fd38ceb45f249fcd6b3fce508367fe7aac`；验证时 HEAD：`e28e67c6fb3c3c15fda278d179bf8abc9daae8bd`（Coordinator 提交 FIX-453）。本票五路径字节稳定，本报告不审该别票提交。
- 同一独立 Reviewer，已重新加载 CODE 角色和 code-review 规范。只新增本报告和 `.codex-sandbox/FEAT-098/review-r1/` 证据，未自修产品、改 index/refs/治理、安装依赖或操作真实 DSH/profile/SDK。

## 对象绑定

| 本票路径 | SHA256 |
| --- | --- |
| `skills/software-project-governance/SKILL.md` | 820686802ac7a47344d54a691dd598bc2d7ac58f1fe0b3aee6e8647aa7a9f539 |
| `skills/software-project-governance/infra/governance_cost.py` | 8082a816ea68b7eee7ea63cc83b7ee3588cdd5d28ee6aa6f06c4d22b60eb4228 |
| `skills/software-project-governance/infra/tests/test_governance_cost.py` | 10f6d437097abb3d8a16c6e32a4a977c01ac3d6f191ac73245d95be0fbbc1882 |
| `docs/diagnostics/feat-098-cost-baseline.md` | d163648ff02fdccc33fc33e3011c310b1758a9f2233680cac4dbe09f0f246315 |
| `docs/diagnostics/feat-098-cost-baseline.json` | 9754b901d8919403afdbbd2f1d8d10c4e204365129aa19b7861d2c8d8a31294b |

按上表顺序拼接 `path + NUL + hex_sha256 + LF` 的集合 SHA256 为 `c63be6318241bfd64340de908e7bc7bf24340ac2bcce132ead43bc80bfc545a5`。显式 `git -c core.autocrlf=true diff -- <五路径>` 输出 SHA256 为 `e1c0755dc41bfc757c5eef1f9bf4ab81c1315ec6055772a20e78b03759ec200b`；新诊断文件由完整文件 SHA 单独绑定。SKILL 相对 HEAD 只有原 FEAT-098 两段四行，完整文件 SHA 与 R0 相同；FIX-450 已提交细则不混入本轮。

## R0 逐项裁决

| 原 finding | R1 状态 | 实际依据 |
| --- | --- | --- |
| R0-F1 / 部分分解超 prompt | **已修复** | `governance_cost.py:467` 的 `_input_breakdown()` 用每个已知非负分量的和作为下界；无须另一分量存在。原 prefix101/prompt100 变 null/issue，increment-only 也拒收；合法部分观测及显式0保留，未测项不补0。独立测试及 inclusive cache/两分量边界通过。 |
| R0-F2 / nested ID 返工自指 | **已修复** | `:479` 在归因前统一 `_label(top) or _label(nested)`，自指、输出、去重及上游引用复用该身份。nested self、可裁剪空白、空或非字符串顶层 fallback、顶层优先等独立验证通过，work_kind=unknown、无有效自指链。 |
| R0-F3 / 冲突观测任取首行、coverage 虚报 | **部分修复，仍阻塞** | 原100/900ms、step-derived矛盾、来源归因冲突均已隔离；可信投影供所有总计/桶/coverage统一使用，原始行不改。其缺测窗口与唯一合法0/123ms观测组合也正确。但新观测签名把有效性不同的标量合并，仍能令费用/token/分解按首行改变，见 R1-F3。 |

因此不能把原三个具体探针变绿解释为三项泛化边界全部闭合；本轮只解除 F1/F2，保留一个同根的 F3 阻塞。

## R1-F3 / P1 / BLOCKING — 签名相等与字段计量资格不一致

位置：`governance_cost.py:529` `_observation_key()` 的 scalar 原样返回；`:549` 生成签名，`:557` 将相等签名判作 duplicate，并继续使用第一个 selected row。字段资格则由 `:396` `_count()`、`:441` `_priced_call()` 明确区分。

Python 的 `True == 1`、`False == 0` 和 `1 == 1.0` 进入当前 frozenset/tuple key 后仍相等，但字段校验规则不同：

- 计价率允许非负有限 int/float，拒 bool；故 rate `true` 非法、`1` 合法，`false` 非法、`0` 合法。
- token、prefix/increment 等计数器只允许非负 **int**，拒 bool 和 float；故 `true/1` 及 `1.0/1` 的可信计量资格不同。
- 合法费率 `1/1.0` 应继续按现有兼容口径等价。本轮该正例独立通过，修复不能用一刀切区分所有 int/float 破坏它。

**真实 CLI 最小复现**：同 session、同 requestId `typed-price` 的两条 assistant 观测，其 exclusive usage 均为 input100/cache-read0/cache-write0/output0/total100；都有 `currency=TEST`、显式 `source_ref=synthetic:rates`，仅 `rates_per_million.input_uncached` 分别为 JSON `true` 与数字 `1`，其余三费率为0。两个实际 `.zstd` trace 仅交换这两行顺序，经未 mock 的 `verify_workflow.py governance-cost-report --sessions-root ... --format json` 得到：

| 行序 | calls | duplicate_records | conflicting_call_ids | cost.complete_total | cost.unknown_calls |
| --- | ---: | ---: | --- | --- | ---: |
| 非法 bool 费率在前 | 1 | 1 | [] | null | 1 |
| 合法数值费率在前 | 1 | 1 | [] | 0.0001 TEST | 0 |

两个 CLI 进程均 exit0，比较器实际 exit1。未知费用会仅因输入顺序变为完整已知费用；没有费率来源缺失、价格查询或 mock 介入。将 true/1 换成 false/0，同一 API 反例由 unknown 变为「已知零费用」，不能把这种0当成合法显式零对照。

同根的另外两种字段也独立复现：

| 同ID不同观测 | 首行与反序的实际差异 |
| --- | --- |
| `role_prefix_tokens=true` 与 `1` | prefix complete_total 为 null / 1；coverage 为0/1 / 1/1，conflicts仍空、duplicate=1 |
| `inputTokens=true` 与 `1`（total=1） | input_uncached complete_total 为 null / 1，conflicts仍空 |
| 计数器 `inputTokens=1` 与 `1.0`；prefix `1` 与 `1.0` | 两组均因 int合法/float非法而反序汇总不等，conflicts仍空 |

这些不是单条调用缺测的合法补充：原始声明具有不同字段类型且经过当前规则得到不同合法性/计量结果，却被签名当成同一观测。按本票既定冲突隔离规则，它们不能任取首行成为可信总计。

**修复建议与验收约束**：让观测签名的等价关系与实际字段有效性一致，统一处理 usage、breakdown、duration、rates 等参与计量的资格；不要仅特判某个费率或 bool 字面值。可以在现有签名中纳入语义/规范化结果的有效性，或使用字段感知的类型/数值规则；同时保留合法价格 int/float 等价及真实缺测窗口不等于冲突的规则。补相同ID的 bool-vs-number、int-only counter-vs-float、反序与混合合法零调用回归，并重跑原12项防护和合法 rate1/1.0正例。Reviewer 不自修。

## 独立运行、正常兼容与证据边界

复用既有 QA venv，Windows CPython3.14.3/zstandard0.25.0。未重复原87项全模块或全仓 suite。

- **目标16 tests：OK，0.012s，exit0。** 包含本轮12项永久回归、快慢解析账本一致、来源化费率/显式零、跨session命名空间与CLI扫描、保存基线精确重放。
- **独立9组合 tests：6个方法通过，3个方法共4个 failure，0 errors，exit1。** 通过项覆盖原F1/F2/100与900ms冲突、24种重复/反序排列、inclusive cache/分解下界、真实step缺测与0/123ms、单条合法零和未知费用。失败对应上述bool费率两组、prefix和usage签名碰撞；同一根因计一个P1，不虚报为4个独立阻塞。
- **补充 int-vs-float 计数器探针：两例均反序不等，exit1。** 详见 `numeric-counter-observations.json`；未扩大到无关功能。
- **真实最薄CLI正常路径：JSON/text均exit0。** 从原交付JSON的8个合成事件生成隔离zstd，逐session `calls` 和 `call_accounting` 与原基线逐字段完全相等，仍5 calls，cost unknown；text明确unknown费用及各工作类别计数。原基线JSON SHA未变，未为新测试数量重写基线。
- **真实CLI坏类型反序：两个CLI各exit0，结果比较exit1**，上表为实际输出，不仅是直接API推演。

Producer 14条审计保留：06:18:56 UTC 原三边界3F/exit1，11:02:46 三边界3P/exit0，最终11:04:15原模块87P（75+12）以及CLI/verify等。已读原日志与Producer整改段；这些是 Producer 运行，不合并为 Reviewer 独立通过数，不改写原10-18 Reviewer R0三RED或历史75P。87项通过不能覆盖本轮真实新反例。

本次静态检查有两个**实际失败记录**：隔离 `GIT_CONFIG_GLOBAL`/NOSYSTEM 后，未显式设CRLF转换的 `git diff --check` 将既有CRLF SKILL视作整文件新增尾随CR，两个 verify-bindings 驱动均exit1（第一次未打印内部stdout，第二次完整保存）。当前SKILL字节与R0相同；随后仅在命令中指定 `-c core.autocrlf=true`，四行增量及 whitespace 检查exit0。未修改文件、Git配置或原失败日志。该规范化静态通过与 F3 的实际计量失败是独立事实。

## 五维度、设计一致性与 AI 专项

| 维度 | 本轮结论 |
| --- | --- |
| 正确性 | NEEDS_CHANGE：F1/F2与原duration冲突修复成立，但签名等价关系仍使费用/计数按首行改变，真实API及CLI均复现。 |
| 安全性 | 无凭证、权限、用户文件或宿主写入扩张；可信计量资格仍不闭合，非法类型不能借相等签名获得确定金额/覆盖率。 |
| 可维护性 | 提取分解验证、统一身份和可信投影方向正确，仍在既有成本报告职责内；需统一签名与字段语义，不能继续散点修补bool或某一种rate。未发现需扩大为架构级重构的依据。 |
| 性能 | 聚焦运行及CLI耗时有原始记录；新流程按调用和观测字段遍历，无新增网络/宿主I/O。未做大trace基准，不宣称吞吐/生产节省改善。 |
| 测试覆盖 | 16常规/整改项通过，独立组合与实际CLI揭示仍缺类型交叉去重回归；保留全部RED。未测行覆盖率，不用测试数替代边界正确性或全CI结论。 |

对照原 FEAT-098 执行目标：体验路径、成本口径、unknown/null、返工因果来源与可重放基线仍保持；不根据 FIX 名称猜返工、不把残余墙钟猜等待、不联网猜费率。两段SKILL未增加新范围。当前 F3 与 P1/P3/P4/P5/P6 的事实、回归和泛化要求不符，故不能仅凭局部绿灯接受交付。

AI五项逐项完成：生产无mock成功返回；无硬编码账单成功/生产采样；使用真实已有CLI/API；无新增未实现TODO；没有无关产品扩展。合成TEST费率与trace均明示来源，不宣称真实账单或生产节省。

## R4 命令审计与保全

命令根：`.codex-sandbox/FEAT-098/review-r1/`。`command-audit.json` 为可机器消费的13条记录，逐条保存实际argv/cwd/UTC/exit/log/hash/environment/impact。执行均使用已有 replay-venv；HOME/USERPROFILE/APPDATA/LOCALAPPDATA/DSH_HOME 指向本仓 `home`，TEMP/TMP 指向 `tmp`，XDG/PIP/UV/npm cache均指向本仓 `cache`；路径先验证在仓内。清除DSH安装/真实会话根及NODE_PATH等覆盖，PATH仅QA Python、Git、System32。无真实会话读取、DSH/SDK启动或导入、联网、安装、真实HOME操作。

下表的 I 表示只读本票源码/既有解释器/合成输入，输出与临时trace仅写Reviewer scratch；V 表示另只读HEAD、保护文件hash和Producer日志，仍仅写Reviewer scratch。测试内部fixture操作也受这套重定向环境约束；不是系统级访问监控声明。

| label（完整argv见同名JSON记录） | 开始UTC 2026-10-19 | 结束UTC 2026-10-19 | exit | impact |
| --- | --- | --- | ---: | --- |
| target-tests：unittest精确16项 | 11:15:22.686274 | 11:15:22.851088 | 0 | I |
| independent-combinations：独立9项 | 11:15:22.852643 | 11:15:22.962527 | 1 | I，实际4 failures |
| prepare-baseline：压缩原合成trace | 11:15:22.963891 | 11:15:23.035416 | 0 | I |
| cli-json：真实governance-cost-report | 11:15:23.036784 | 11:15:23.378743 | 0 | I |
| cli-text：同CLI text | 11:15:23.381025 | 11:15:23.723266 | 0 | I |
| verify-bindings：初次原始Git检查 | 11:15:23.724737 | 11:15:23.978519 | 1 | V，CRLF口径失败保留 |
| verify-bindings-followup：保留内部stdout复核 | 11:16:31.975710 | 11:16:32.227152 | 1 | V，同上 |
| numeric-counter-probe：int/float两例 | 11:16:32.233161 | 11:16:32.314036 | 1 | I，实际资格碰撞 |
| verify-bindings-crlf-normalized：命令级CRLF规范化 | 11:17:09.066901 | 11:17:09.296240 | 0 | V，无配置/文件写入 |
| prepare-negative-cli：合成坏类型双trace | 11:17:55.730252 | 11:17:55.799526 | 0 | I |
| negative-cli-invalid-first | 11:17:55.804730 | 11:17:56.161212 | 0 | I，CLI费用null |
| negative-cli-valid-first | 11:17:56.165422 | 11:17:56.516556 | 0 | I，CLI费用0.0001 |
| negative-cli-compare：实际结果比较 | 11:17:56.518244 | 11:17:56.594104 | 1 | I，反序不等 |

证据SHA256：

| Reviewer scratch 内相对路径 | SHA256 |
| --- | --- |
| command-audit.json | 581bcf98e8b7b8de505edbcaf5485dfbba2d67f582b48dafe36cff58767b63a5 |
| combinations-observations.json | 818798e6bd862b153f3bce2f5ef43081ca0026c053731cd400f1d79d8c00ce85 |
| numeric-counter-observations.json | 5d0fff4c1df9b07356552b4641b9cb5d1b354cdc8e0ff16e7d837401b79e53ee |
| negative-cli-observations.json | 8e8fe39c59dba52a6283fa1913264aa1ab01ef35713a2a918d2cfb51798b6c0a |
| logs/target-tests.log | b837ac5b45752f09064bb72a1a4215cd66f33ba792a05a315aa0601c322eb245 |
| logs/independent-combinations.log | d91818ceb4c89f17d82bf727c237184fe1b29ca0c4ec66c4ad8fb871fc0326cb |
| logs/numeric-counter-probe.log | a54f67b1448428656250ce05f9f03ed972b5503f63c910605382e34a630a1c4d |
| logs/negative-cli-compare.log | 3e041a12fdcba171777f0dfa2d487ca7f0ba346196ee45e8cf8cb9ba1dca888f |
| logs/verify-bindings-crlf-normalized.log | 63ef9ef9deb27518e36866fd611544e3152a14dc863fe99040df3e6c9f80647e |

Producer `.codex-sandbox/FEAT-098/rework-r1/command-audit.json` SHA256 `a17fc7f84a399212495d8371a845fc37970c80314233dad171748f73246c78e8`，不是本轮Reviewer审计。

原R0报告、command-audit、boundary-probes.log、boundary-observations.json均按R0记录SHA复核相同。暂停 commit-msg SHA256仍 `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`，test_hooks.py仍 `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`。只读hash，无暂停内容审查或修改。

## 裁决

P0=0，P1=1（R1-F3，BLOCKING），P2=0。R0-F1/F2解除，F3的具体duration分支已修，但类型有效性签名边界未闭合。需最小泛化修订与同Reviewer下一轮复审，当前不批准功能交付。完整CI、真实生产费用、宿主验收、FIX-455的原子账本I/O与版本发布均不由本轮关闭。
