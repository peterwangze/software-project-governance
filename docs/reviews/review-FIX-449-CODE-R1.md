# FIX-449 CODE R1 — 共享版本夹具复审

- 日期：2026-10-18
- 结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- 当前 HEAD：`36b13a4fbe4a46219fca3eb78e99efbd83cab945`
- 前轮：`docs/reviews/review-FIX-449-CODE-R0.md`，SHA-256 `8191ef745fae5acc658b3f5c69198560fa5382768e3d44a5a0550e7211409228`；已重读，原报告未改写。
- 审批范围：本票六处活动版本针、同一 PLAN 冲突版本派生、共享消费者漏渲染修复及对应回归/诊断。不能据此认定该大测试文件的其他 CI 失败、Windows 文件系统异常、完整 CI 或发布已修复。

## 对象绑定

| 对象 | SHA-256 |
| --- | --- |
| `skills/software-project-governance/infra/tests/test_verify_workflow.py` | e9e33cdd8843a7d9725bd253ac8eb32961231de38ce53b941d195f8936726799 |
| `docs/diagnostics/fix-449-version-pins.md` | 22b75e18b32b0e9542aec4c6bde327d1ba8e9fe5521dac516227d4175eb7f75f |
| 测试文件相对 HEAD 的 diff | 50162a9f9a6232b03e9e861ce76a5cf08dbada47ce552c430f7fa2b16a2fb3d8 |

## 前轮发现逐项裁决

| Finding | 本轮状态 | 事实 |
| --- | --- | --- |
| R0-F1 / P1 / BLOCKING：第二消费者将未渲染 token 写入 plan/ledger | **已修复** | `_gov()` 改为 classmethod；`_migrated_gov()` 在 L25750 直接复用该唯一构造入口，再执行真实 migration。新增消费者回归直接检查 plan、冲突版本、实际 ledger target_version、完整性及计数；独立三版本探针全部验证无 token。 |

新增回归不是仅检查模板字符串：它实际调用前轮遗漏的 `_migrated_gov()`，并读取 `LedgerWriter(gov).state`。全文件共享 PLAN 的直接构造入口只剩 `cls.PLAN + plan_extra_rows`；switch-state 测试也改为读取统一 helper 已渲染的 plan，不继续消费原始模板。没有用第二套替换逻辑修补单点，符合前轮统一构造入口建议。

六处活动版本均从 `resolve_entry.read_active_version()` 派生；冲突行始终为同 major 下一 minor。原冲突标题/状态、4 行/3 ID/1 conflict、31-task 性能数据及 2s/50ms 门保持。缺锚负向夹具的空事项仍为空，dry/live `schema_violation_row` 拒收、部分迁移完整性与幂等检查未放宽。没有新增静态针豁免或改生产版本。

## 独立验证与运行限制

Windows CPython 3.14.3。命令、真实 argv/cwd、UTC 起止、exit、访问范围和原始输出均保存在仓内 `.codex-sandbox/FIX-449/review-r1/`；TEMP/TMP/DSH_HOME 指向该范围，无用户应用 HOME 操作、SDK 读取或实际安装。

**通过的聚焦验证**（`focused.json` / `focused.log`，UTC 2026-10-18 12:17:34.975736→12:17:44.047907，exit 0）：

1. `test_static_version_pins` 全模块 **25 tests / OK / 4.010s**；真实整树扫描结果 `[]`，目标文件零 WARN。整树旧 archive exemption 的改善有 FIX-453 贡献，不全部归因 FIX-449。
2. 新消费者回归及原缺锚 dry/live 负例 **2 tests / OK / 0.409s**。版本 mock 仅替换权威输入，真实 migration/ledger 读写没有 mock。
3. 独立直接调用 `_migrated_gov()`，结果如下：

| 注入权威版本 | plan token | FEAT-093 / FEAT-094 / FIX-442 的真实 ledger 版本 | 完整性 | 历史冲突数 |
| --- | --- | --- | --- | ---: |
| 0.98.0 | 无 | 均 0.98.0 | True | 1 |
| 0.99.0 | 无 | 均 0.99.0 | True | 1 |
| 1.0.0 | 无 | 均 1.0.0 | True | 1 |

4. 0.98.0 下主 helper 渲染的 PLAN 与从 HEAD AST 提取的原 PLAN 逐字相等；当前 `authority_ledger.py` 相对 HEAD 无改动。目标两文件 `git diff --check` exit 0。

**不能包装为全绿的两次批量尝试**：Reviewer 原计划独立复跑两个 class 的三版本全组，但遇到下述真实 I/O 错误，保留失败日志且未继续反复重跑：

| 记录 | 真实结果 |
| --- | --- |
| regression.json / .log，UTC 12:15:35.451497→12:15:38.082636 | 首轮 19 tests / 2 errors / exit 1。新主路径回归的一个子例及原 31-task 性能测试在 `authority_ledger._atomic_write:337` 的 `os.replace` 抛 Windows `PermissionError: WinError 5`，目标为仓内临时 ledger snapshot。 |
| regression-retry.json / .log，UTC 12:16:18.778484→12:16:24.164705 | 不改代码、只换新仓内 TEMP 的一次复验：外层 0.98.0 的 19 tests 通过；下一轮 0.99.0 的原 31-task 性能测试同位置 1 error，exit 1。未完成全部三轮。 |

两次均没有版本值/token 断言失败，但文件替换拒绝的根因**未查明、未修复**。未修改或 mock `_atomic_write`，未放宽性能门，也没有删除失败项。诊断文档中 Producer 的 **19×3=57P** 是其早先实际结果，已核对其记录；本 Reviewer **不声称独立重现了完整 57P**。本轮 F1 关闭依据是统一消费者实现、真实三版本 plan/ledger 探针及直接回归通过，不能用该裁决关闭 Windows I/O 异常。

## 五维度、设计一致性与 AI 专项

| 维度 | 结论 |
| --- | --- |
| 正确性 | 本范围通过：唯一渲染入口覆盖全部共享消费者，三版本真实 ledger 无泄漏且冲突语义保持，R0-F1 关闭。 |
| 安全性 | 通过：仅测试输入派生；坏行拒收和真实账本完整性仍检查，没有绕过 I/O 错误或操作用户数据。 |
| 可维护性 | 通过：删除重复 PLAN/RISKS 写入，统一 classmethod；switch 消费者使用相同已渲染数据，避免再次遗漏。 |
| 性能 | 版本逻辑无新增高复杂度，31-task 与预算门未放宽；本机性能夹具遇 I/O 异常，不能认定所有性能验证全通过。 |
| 测试覆盖 | F1 修复证据充分：新消费回归、三版本直接探针、坏行负例与静态针25项通过；整组重放限制和失败原样披露。 |

设计对照 DEC-213③：版本来自权威渲染源，历史/故意错误数据不批量替换，无新增豁免。AI 五项完成：没有伪造 migration 返回、硬编码成功、幻觉 API、未实现 TODO 或无关扩展；mock 只控制版本输入，不模拟 ledger/文件系统成功。

## 发现、残余与证据绑定

P0=0，P1=0，P2=1（下述范围外运行发现，非本六针改动的阻塞）；R0-F1 已修复，无本范围未解决 BLOCKING finding。

**R1-N1 / P2：Windows atomic snapshot 替换拒绝需独立归因。** 具体位置、临时路径及堆栈在上述两个失败日志。当前只确认同一 I/O 错误两次出现，不能猜测为杀毒软件、权限策略或确定的产品缺陷。建议 Coordinator 另行登记/承接该证据，在正式 Windows 回归与发布质量评估前明确其处置；不得把它随 FIX-449 一并标为已修。该生产函数不在本次 diff，Reviewer 未自修或扩展本票。

**R1-N2 / P3：范围限制。** 静态针和共享 fixture 修复通过不代表该大文件其他 clean-checkout/CI 失败消失；GitHub Python 3.11、完整套件及版本发布仍需各自验证。

| 证据 | JSON SHA-256 | log SHA-256 |
| --- | --- | --- |
| regression | 87099611db25026ffb755d3de211186ed1c72c766c578293a36add0858cbf424 | 679e31dfca67656b075747e3e699163590032f78fc9eaad5cc86cafdea0361c5 |
| regression-retry | 69e472f641cd21a226cea315b65f2dd7ce25e67ef877d7e7d24306d234fad04d | a6649674ccfbd4b9449cf0981bc323a58bd7d9c2b8c9ad61b8eb31ea7ac7d2a3 |
| focused | ebca80c883a48c111413401fd5c8c6d0277688f99f968a9c680d77574bfe7887 | faddc5397197e0cbd39cdef816e783588c7bcd642673a7e7e607092cde92515b |

五维度、前轮逐项复查、分级、设计一致性及 AI 五项完成。仅批准已绑定的 FIX-449 代码/诊断范围；Reviewer 只新增本 R1 报告及授权仓内 scratch 证据，未修改产品、index、治理记录或 R0 报告。
