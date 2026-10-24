# FEAT-098 CODE R3 — 等价费率数值资格修复独立复审

- 日期：2026-10-20（Asia/Shanghai）；本轮所有运行时间为下述 2026-10-20 UTC。
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=0，P3=3（均为讨论项，不阻塞）。
- 审查 HEAD：`e28e67c6fb3c3c15fda278d179bf8abc9daae8bd`（与 R2 审查基准相同；本票仍未提交，工作树 WIP）。远端 CI 不能证明工作区字节，本结论只覆盖下列绑定对象。
- Reviewer 身份：**新独立实例**承接 R0/R1/R2 报告链（旧实例不可用，不冒称同一实例）。已加载 `agents/code-reviewer.md` 与 `skills/code-review/SKILL.md`，通读三轮报告、工作树 diff、源码/测试全文与基线文件后独立运行全部证据。仅新增本报告与 Reviewer scratch（`.codex-sandbox/FEAT-098/review-r3/`）；未修改任何产品代码/正式测试/治理记录/前轮报告，未提交推送。
- 前轮报告 SHA256：R0 `76138cc983c9c6a6f033288a9a967eb345845814176fe3350d17db3fe252d263`；R1 `3897b375233b20267b2260949a409237d61307ae5d4fa1e3df5b3924fb103117`；R2 `1d882c4fb3427b60f8b0a4b4265c8ddec93ca49b3e216c602325defc27011937`。三轮原 NEEDS_CHANGE 与历史 RED 记录不被本轮绿灯改写。

## 对象绑定

| 路径 | 当前文件字节 SHA256 | 相对 R2 记录 |
| --- | --- | --- |
| skills/software-project-governance/SKILL.md | `820686802ac7a47344d54a691dd598bc2d7ac58f1fe0b3aee6e8647aa7a9f539` | 不变（R0 起同一字节） |
| skills/software-project-governance/infra/governance_cost.py | `5f137050595f0f3c5cb8f69c1d4b6ec0e195c90ea40f85665bbb08ac127c9446` | 变更（R2: `cbe400c6…`）——本轮修复面 |
| skills/software-project-governance/infra/tests/test_governance_cost.py | `2665f95cb346d95377317f85c53c54d04bacce33d0f916ec7b59d8eb5b2123f2` | 变更（R2: `bfb6a750…`）——+8 测试 |
| docs/diagnostics/feat-098-cost-baseline.md | `ab261abf1b14b936d4fadce5895228cd9240b6829a184104e23b9f89a134c94c` | 不变 |
| docs/diagnostics/feat-098-cost-baseline.json | `9754b901d8919403afdbbd2f1d8d10c4e204365129aa19b7861d2c8d8a31294b` | 不变 |

三 tracked 产品文件命令级 `-c core.autocrlf=true` diff SHA256：`55f7147eb2f9be5fff5cfc3939be96d1884150254ed5d9389590464992b6bb1f`；`diff --check` exit 0。基线 JSON 未为新测试数量重写。

**范围排除**（修改纯粹性核查）：工作树另有 `infra/hooks/commit-msg`（SHA `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`）与 `infra/tests/test_hooks.py`（SHA `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799fbfe5669d0db`）——两文件字节与 R2 记录的暂停 FIX-444/445 WIP 完全相同，本轮零变化，不在本审查面、不计入结论。SKILL.md 相对 HEAD 仅 FEAT-098 体验脊柱/成本基线两段四行（与 R0 审查的字节一致），属本任务面。

## 前轮逐项裁决

| 原 finding | R3 状态 | 独立事实（本轮实际运行） |
| --- | --- | --- |
| R0-F1：缺另一分量时已知分量超 prompt 仍可信 | **已修复，维持解除** | `governance_cost.py:493-501` 以已知非负分量下界和校验。4 组独立探针（prefix101/increment101 单独或配 0/1，prompt=100）全部 `input_breakdown_exceeds_prompt`、两分量 null、coverage known=0；合法部分观测（100 边界/显式 0/99）保留且另一分量 null。 |
| R0-F2：nested requestId 自指返工 | **已修复，维持解除** | `:507` 统一 `_label(top) or _label(nested)` 身份。探针：无顶层 ID、`message.requestId='self'`、upstream='self' → call_id='self'、work_kind=unknown、`rework_self_reference` issue、rework_links=[]。 |
| R0-F3：duration 冲突任取首行、coverage 虚报 | **已修复，维持解除** | 100/900ms 同 ID → conflicting=['c1']、duration coverage known=0、unknown 桶 known_duration=0、正反序 summary 全等、原始行不改。 |
| R1-F3：类型相等但计量资格不同（bool/计数 float） | **已修复，维持解除** | 真实 CLI 等价探针之外另跑 API：rate true/1 与 false/0 → conflicts=['typed']、complete_total=null、unknown=1、序无关；inputTokens/totalTokens 1.0 vs 1 → conflict、complete_total=null、序无关。合法 1/1.0 仍 duplicate=1、0.0001 TEST。 |
| **R2-F3：等值合法 int/float 费率计价资格/首行依赖** | **已修复（本轮关闭）** | 见下节。 |

## R2-F3 修复验证（本轮唯一复审目标）

修复实现（`governance_cost.py:443-490`）：`rate.as_integer_ratio()` 统一 int/float 为同一精确有理值；`ratio = tokens[key] * numerator, denominator * 1_000_000` 保持整数乘积精确；`_price_float()` 仅在输出边界做一次转换，`OverflowError`→拒收、正价下溢为 0→拒收（非测得免费）；`_sum_price_ratios()` 用 `math.lcm` 精确通分求和（`:453-460`，序无关）；`_call_totals()` 币种小计对每调用 `amount.as_integer_ratio()` 精确求和，超范围保 null 不产 inf（`:672-689`）；`_fmt_tok` 增加整数回退显示（`:1293-1308`）。未采用 bool 签名单点修改，未加任意费率上限——资格由"最终价格可表示性"统一判定，泛化到所有四个计价桶与汇总面。

**R2 反例逐条复验**（`rate=int(1e307)` 与 `1e307`，断言 `int(1e307)==1e307` 且类型分别为 int/float；同 session 同 requestId 双观测，input=100/total=100，TEST 币种、显式来源）：

1. **API 面**（`probe-observations.json` `r2_counterexample`）：两条观测 cost 全等（amount=1e303，components.input_uncached=1e303）；正反序 summary 全等；duplicate_records=1；conflicting_call_ids=[]；complete_total=1e303；unknown_calls=0。旧 float 路径的中间 inf 溢出不复存在。
2. **真实 CLI 面**（`verify_workflow.py governance-cost-report`，两个隔离 zstd，仅交换行序）：两进程均 exit 0，`call_accounting` 整体相等（`r2_cli_equal: true`）；两序均 duplicate=1、无冲突、`cost.complete_total=1e303 TEST`、unknown_calls=0；text 模式两序均打印 `cost=1e+303 currency=TEST unknown-cost-calls=0`。R2 时"整数在前=完整已知 1e303 / 浮点在前=null+unknown=1"的反序分歧消除。
3. **泛化面**：
   - 真正不可表示的最终价（rate=10^400；及 float_info.max×10M tokens 组合，测试 `test_final_unrepresentable_bucket_prices_are_unknown_for_both_numeric_types` 覆盖）：int/float 两型一致 `price_out_of_range`→cost=null、序无关、duplicate=1。
   - 正价下溢（rate=5e-324, tokens=1）→ null+`price_out_of_range`，不冒充免费；显式 0 费率 → 测得 0.0 且无 issue。
   - 巨计数×微费率（2^2000 tokens × 2.0^-1000）：精确比例路径得 1.0715086071862673e+295（==期望），不崩溃——旧 `int*float` 中间乘法在该输入会抛未捕获 OverflowError，本轮一并修复。
   - 单次舍入：1M tokens×费率 {1e16,1,1} 三调用 → complete_total=10000000000000002.0，4 种行序（含轮转）全等。
   - 币种聚合：两调用各 1e308（TEST）+ 一调用 0（OTHER）→ `{"TEST": null, "OTHER": 0.0}`、unknown_calls=0（只计未定价调用）、complete_total/currency=null、`json.dumps(allow_nan=False)` 通过、序无关；单币种情形 currency=TEST 保留、complete_total=null。**任务要求②的三点语义（null/unknown、其它币种保留、unknown_calls 只计未定价）全部实测成立。**
   - 兼容保持：合法 1/1.0 仍 duplicate=1 → 0.0001 TEST（R1 既有正例未破坏）。

## 独立运行与覆盖

- **全量测试**：`python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q` = **100 passed, 108 subtests passed, 0.29s, exit 0**（与 Coordinator EVD-2106 记录一致，本轮独立复跑）；原生 unittest（replay-venv 3.14.3）= **Ran 100 tests / OK / 0.145s / exit 0**。
- **测试语义保持**：以 rework-r2 `R2-MODULE.log` 的 92 项 R2 时点清单与本轮 verbose 100 项做差集——**恰好新增 8 项**（`test_equal_extreme_rates_price_every_bucket_and_mixed_duplicates_identically`、`test_huge_integer_counts_and_rates_preserve_representable_prices_and_real_zero`、`test_final_unrepresentable_bucket_prices_are_unknown_for_both_numeric_types`、`test_nonzero_price_underflow_is_unknown_and_not_reported_as_free`、`test_call_component_sum_checks_final_range_and_rounds_once`、`test_summary_prices_round_once_independent_of_call_and_session_order`、`test_unrepresentable_currency_subtotal_is_null_without_losing_other_currency`、`test_huge_count_and_known_zero_price_survive_json_and_text_cli`），**零删除、零重命名**——旧断言无从被偷换。且 R0/R1/R2 全部反例场景已由本轮独立探针另行重放通过，不依赖测试文件本身。
- **真实 CLI 双模式**（均为 `skills/software-project-governance/infra/verify_workflow.py governance-cost-report` 真实进程，4 组隔离合成 trace × json/text 共 8 次调用，全部 exit 0）：
  - R2 反例双行序（见上）；
  - **基线重放**：从 `feat-098-cost-baseline.json` 的 8 事件重建 zstd → JSON 模式逐 session `calls` 与 `call_accounting` 与保存基线逐字段全等（5 调用、缺率 cost=null、unknown-cost-calls=5）；顶层 `call_accounting` 与基线差异仅为跨 session `file::` 命名空间投影（record_id/upstream_call_id 前缀），cost 块完全一致，与 R0-R2 行为相同；text 模式输出 `cost=unknown currency=unknown unknown-cost-calls=5; missing call IDs=1` 与四类+unknown 工作计数 1/1/1/1/1；
  - **strict JSON**：R2 反例两序原始 stdout 经正则扫描无 `NaN/Infinity/-Infinity` token 且可严格解析；
  - 巨计数（2^4000）×显式零费率：JSON exit 0（complete_total=0.0，in=精确大整数）、text exit 0（`cost=0.0 currency=TEST unknown-cost-calls=0`，`_fmt_tok` 回退格式正常），无 Traceback。
- **静态**：五路径中三产品文件 `git -c core.autocrlf=true diff --check` exit 0。

## 新发现（全部 P3，不阻塞）

| # | 级别 | 位置 | 描述 |
| --- | --- | --- | --- |
| R3-N1 | P3 | `governance_cost.py:1293-1308` | `_fmt_tok` 整数回退的"same two-decimal, half-even display"是规则等价（精确十进制 half-even），非与 float 路径的字节等价（float 路径先舍入到 double 再格式化）。仅显示面，不影响任何账本数值，不要求修改。 |
| R3-N2 | P3 | `governance_cost.py:672-682` | 币种小计 caliber 为"各调用已单次舍入 amount 的精确和，再单次舍入"，与"原始精确比例之和再舍入"理论上可差 1 ulp。序无关、无 inf、测试已钉住（10000000000000002.0），属可接受口径，建议未来在 CALIBRATION 文案中明示。 |
| R3-N3 | P3 | JSON 输出面 | 被接受的巨大整数计数（如 2^4000）在 JSON 中序列化为精确大整数（约 1205 位）。合法 JSON，但仅支持 IEEE-754 double 的严格消费方需注意。text 面已由 `_fmt_tok` 格式化。设计取舍（保精确、不造 0），不要求修改。 |

## 五维度、设计一致性与 AI 专项

| 维度 | 结论 |
| --- | --- |
| 正确性 | 通过：R2-F3 及其泛化面（四桶、汇总、币种、下溢、巨计数、单次舍入）经 API 与真实 CLI 双序实测等价；R0/R1 全部反例无回归；溢出拒收保持。 |
| 安全性 | 无新增凭证/网络/权限/用户数据写入；CLI 仍 fail-closed（缺 root exit 2，既有测试保持）；不可计价观测不能借重复身份获得已知费用。 |
| 可维护性 | 计价收敛到单一精确比例事实源（`as_integer_ratio`+`_sum_price_ratios`），无 bool 单点特判或魔法上限；改动限于计价/汇总/显示面，未扩大重构。 |
| 性能 | 线性遍历不变；`as_integer_ratio`/`lcm` 为 O(1) 级，分母族有界（2^k×10^6），无新增 I/O。未做大 trace 基准，不宣称吞吐变化。 |
| 测试覆盖 | 100 项+108 subtests 全绿；8 新增测试精确对应 R2-F3 验收约束（双行序、双类型、下溢、汇总、币种、CLI）；92 项旧测试零删除零重命名；R0-R3 全部反例另有独立探针重放。 |

设计一致性：对照 FEAT-098 执行包与 R2 修复验收约束——同源数值计算路径、反序相同、不破坏 0/0.0 与 1/1.0 兼容、不以 bool 单点或费率上限规避——全部满足。unknown/null 语义、来源化归因、会话命名空间、可重放基线、不猜费率/返工/等待均保持。

AI 专项 5 项：无 mock 成功返回残留（测试仅 env patch）；无硬编码生产账单/费率；`int.as_integer_ratio`(3.8+)/`float.as_integer_ratio`/`math.lcm`(3.9+) 均为真实存在 API（运行环境 3.14.3）；无新增未实现 TODO；无 FEAT-098 范围外产品扩展（范围外文件字节与 R2 记录相同，未混入）。

## 命令审计（本轮 Reviewer 全部命令）

工具层文件读取（Read/git status/hash 等）保留于会话记录；下列为运行类命令，环境均重定向 HOME/USERPROFILE/TEMP/TMP 至 `.codex-sandbox/FEAT-098/review-r3/` 仓内 scratch，未读取真实会话、未启动 DSH、未安装依赖、未联网。审查工具准备失败两次并已纠正后成功：replay-venv 无 pytest（`No module named pytest`，该次无测试执行）改用系统 Python 3.14.3（pytest 9.0.3，与 Coordinator 命令形态一致）；首轮 unittest 复合命令日志落盘失败，单独重跑成功。探针脚本一次自身期望值计算溢出（`int*float`）——恰为旧产品缺陷同型算术，修正为精确整数比例后通过；保留该失败事实于本记录，不冒作产品结果。

| label | UTC 2026-10-20（起≈止） | exit | 要点 |
| --- | --- | ---: | --- |
| env-check（venv/zstd 版本） | 09:18 | 0 | CPython 3.14.3 / zstandard 0.25.0 |
| pytest-full（系统 Python，Coordinator 同形命令） | 09:19:00 | 0 | 100 passed + 108 subtests / 0.29s |
| unittest-full（replay-venv discover） | 09:19:23 | 0 | Ran 100 tests / OK / 0.145s |
| probes（API 独立探针 23 组场景） | 09:20:41 | 0 | `probe-observations.json` 全通过（含 R2 反例、下溢、币种、round-once） |
| cli-driver（真实 verify_workflow.py × 8 次子进程：R2 双序 json/text、基线 json/text、巨大计数 json/text、strict-JSON 复扫） | 09:21:33 | 0 | 全部子进程 exit 0；`r2_cli_equal: true`；strict 无 NaN/Inf |
| test-names-diff（verbose 清单 vs R2 时点 92 项） | 09:23:14–09:23:34 | 0 | +8 / -0 / 重命名 0 |
| diff-check + diff-hash（三产品文件） | 09:24 | 0 | whitespace 干净；diff SHA `55f7147e…` |
| evidence-hashes | 09:25 | 0 | 见下表 |

Reviewer 证据 SHA256（`.codex-sandbox/FEAT-098/review-r3/` 下相对路径）：

| 文件 | SHA256 |
| --- | --- |
| probes.py | `567450d189d373712fb34988a33d0c8c17263be8a031c73268d1136717e44076` |
| cli_driver.py | `f3af953fb66eb71b22ef639a6f1efa5866919d24e5322b487d9fdb40091f604a` |
| probe-observations.json | `a11ea6ffc0deb5813a16fa6e25abb1b015aae87c32372a2d080c32c13b6704e4` |
| cli-observations.json | `c52185e430d290bbb7d7197e996543ac396b68a12def531080e0f5c130569a18` |
| logs/pytest-full.log | `d9e2c48f5807145d21891b442cb657c339e290608f972c0a00c3c20d38cdeddd` |
| logs/unittest-full.log | `116bd8c739d7ac10ee2b0c8d7bfa13407a07c8261bcfbe8b7a11b670877e9983` |
| logs/probes.log | `2dfe2a9dca601a146974cf72697f2c1f06a0739d8967a013825caffdb67993ca` |
| logs/cli-driver.log | `6d56fabf37214dfb72b9d579e50d2a09f1494ce4ac3d605e982cf67aa0c93ff3` |
| logs/current-test-names.txt | `8f2fcc71bec4c9faed6815523d2c4c2c6f67c60fc6c5861b1af5a5bfd326259c` |
| logs/r2-test-names.txt | `f5d836426b2828626387200421455e941d8b902709b8f2eff35ee6cefebcac56` |

Producer `rework-r3/command-audit.jsonl` 30 条与 `logs/` 已读取作背景（含 permanent-tests-red 26 failures 的 RED 证据）；它们是 Developer 运行，不并入本 Reviewer 命令数或通过数。

## 硬门槛自检与裁决

1. 未修改任何产品代码/正式测试/治理记录——仅写本报告（锁内唯一写面）与 Reviewer scratch。✓
2. 每条结论均有实际运行/读取证据（命令、输出、文件:行号），无推断性通过；测试失败的两处准备事故与探针自伤均如实保留。✓
3. 全部运行在仓内完成，输入为 scratch 合成 trace，未触碰用户真实环境。✓
4. 五维度/AI 五项/分级/设计一致性全覆盖。✓

P0=0，P1=0，P2=0，P3=3（讨论项）。**APPROVED_WITH_NOTES，unresolved_blockers=0**——R2 唯一 P1（R2-F3）经 API 与真实 CLI 双行序独立复验关闭，R0/R1 各 finding 无回归，原 92 测试语义保持（+8/-0），修改纯粹（范围外文件零变化）。本结论只覆盖代码审查面：完整 CI、生产费用、宿主体验验收、发布与 FIX-444/445 暂停面不由本报告批准；Coordinator 负责机录 REVIEW 证据与裁决终态。
