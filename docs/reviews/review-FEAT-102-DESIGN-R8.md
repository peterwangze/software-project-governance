# FEAT-102 — DESIGN R8 聚焦增量复核（R7 N-R7 修正）

- 日期：2026-10-21（Asia/Shanghai）；独立 Design Reviewer（同一非 Producer Reviewer）。
- **对象绑定**：修正后的设计 `docs/architecture/dsh-adapter-version-decoupling.md`，SHA-256 `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE`（806 行 / 119,217 B）；修正前 = R7 审查对象 `488140EC...`（788 行 / 116,401 B）。delta = R7 报告 `docs/reviews/review-FEAT-102-DESIGN-R7.md`，SHA-256 `5DACF2FD2984262C7EEFD3D7934B8D312897A24DE58E405BB6492D3A67C60A6B`（其机器记录为 `REVIEW-FEAT-102-R8`；本报告是聚焦的 DESIGN R8，不复用该记录 ID）。
- **范围**：只核 R7 的 N-R7-1～5 是否按最小修改落地，以及是否引入 new deviation；**不重开全量设计复审**。CODE 链代码/测试/契约/README/投影仍在途，继续**排除**，本报告不把其当已修复，也不因漂移改判。
- **方法**：复算设计/R7 报告 hash；用归一化 section 比对 R7→R8（只应影响 §3/§4/§16/§17）；逐条读取五处修正点与 `REWORK.md` 权威时间/结果；未运行宿主、未跑测试（测试面以 CODE R1 稳定字节为准）。命令见 §5.3。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
five_fixes=PASS (5/5)
new_global_blocker=NONE
new_p3_findings=2 (N-R8-1 table note placement, N-R8-2 row wording)
host_run=NOT_RUN
tests=NOT_RUN
```

5 项 N-R7 修正全部按最小要求落地；未发现新的全局阻断。两项 P3 是 **§3.1 的排版/措辞清理**，不影响设计方向或支持声明，因此给 `APPROVED_WITH_NOTES / 0`（不是 `NEEDS_CHANGE`）。

## 2. 逐项 PASS/FAIL

| 项 | 判定 | 事实 |
|---|---|---|
| **N-R7-1** 权威 585/0/0；580/5 非一致；旧两句删除 | **PASS** | §16.3（L757）写 **585 passed / 0 failed / 0 skipped（119 subtests，670.36s，UTC 2026-10-20 13:00:27.929Z→13:11:38.991Z，exit 0）**，并标 **EVD-2120**；`REWORK.md` L3/L106 确认日期、UTC、585/0/0、119 subtests、670.36s。`580 passed/5 failed` 在 §16.3、§17 D-R6-6（L785）、§17.1（L798）均明确为“返工进行中、conftest 未收口的**非一致快照，不作为结果**”。旧句“5 项失败……须由 CODE R1 关闭”和“本设计不声称 585 全绿”的**实时断言已删除**（§17.1 仅作为“已移除”的修订记录出现，不是 live claim）。§17 D-R6-6 有 585/0/0 摘要，§17.1 有完整时间/subtests/exit 细节 |
| **N-R7-2** §3.1 三行改状态；表下口径一致 | **PASS（附 P3 N-R8-1/N-R8-2）** | L53 `lib/index.js`、L55 `source.js`、L59 `bridge.js` 均从“已实现”改为“**设计已定；实现待 CODE R1**”；L61 表下口径写明“未提交、未经审查 ≠ 已落地，语义同 §16.4.5/6”，与 §16.4.5/6 一致。P3：该口径实际插入在表内最后一行（L62 infra）**之前**，不是表下，且 L53 括号“（不改自动 legacy 写入）”措辞有歧义/与 DEC-366② 易混——见 N-R8-1/N-R8-2 |
| **N-R7-3** §4.1 第 5 条末句标历史 | **PASS** | L105 末句“不能删去 BASE_BROKEN 拒收要求”后已加〔**此句为历史表述**：2026-10-21 已按 DEC-366③ 降级为 known boundary，见本节修订块〕；不再作为当前硬门 |
| **N-R7-4** §4.3 code 集合/历史字面 | **PASS** | L127 的 code 集合已补 `BASE_DISABLED`、`BASE_DISABLED_UNEVALUABLE`、`PERSONA_ROW_MISSING`、`PERSONA_ROW_DUPLICATE`、`SKILL_ROW_MISSING`、`SKILL_ROW_DUPLICATE`、`NATIVE_PATH_UNAVAILABLE`，并注“**非穷举，以 CODE R1 复核为准**”；L130 的 `RuntimeOutcome` 字面与 L132 的“错误码至少”段均已加“**历史合同/仅作追溯**”前缀 |
| **N-R7-5** §16.4.1 首句与后文统一 | **PASS** | L762 首句改为“19/23 行校验、4 行 NO_SCHEMA 披露；**CLI 回退计数以下方事实限定为准**”，不再断言“1 行经 CLI 回退”；后文明确隔离实测 0、合成平面 1、CODE R0 改判 **NOT_RUN**（EVD-2119） |

## 3. 新偏差（P3，非全局阻断）

### N-R8-1（P3）§3.1 状态口径插在表格中间，拆开最后一行

L61 的 blockquote 口径位于 L59 `bridge.js` 行与 L62 既有 infra 行之间。Markdown 表格在插入 blockquote 后结束，L62 可能被渲染为表外/无表头行，且口径并非“表下”。**最小修正**：把 L61 整体移动到 L62 之后（并用空行分隔），或把 infra 行移到注记之前，保持表行连续。

### N-R8-2（P3）L53 括号“（不改自动 legacy 写入）”措辞歧义

该行职责文本已正确写“**不再自动写 legacy 目录**，DEC-366②”，但状态列括号“（不改自动 legacy 写入）”容易被读成“保持自动写入不变”，与 DEC-366②/§16.1 冲突。**最小修正**：删除该括号，或改为“（DEC-366②：不再自动写 legacy；实现待 CODE R1）”。这只是同一行的措辞清理，不影响 N-R7-2 主项 PASS。

## 4. 回归检查

归一化 section 比对（R7 期望 hash vs R8 当前）结果：

- **SAME**：§1、§2、§5、§6、§7、§8、§9、§10、§11、**§12**、§13、**§14**、**§15**。
- **CHANGED（均对应 N-R7 修正）**：§3（N-R7-2）、§4（N-R7-3/4）、§16（N-R7-1/5）、§17（N-R7-1 记录 + §17.1 新增）。
- **未发现**对 §14/§15/R3/G/S-A3 历史、§12 ADR/结论、支持声明限定的改动：§12 section hash 仍为 R7 的 `D9F80BC9...`；§14 `16738FDC...`、§15 `25EC6BFE...` 与 R7 一致；§16.2 支持声明文本未变。
- 当前设计全文检索未发现“取消已解决”“FEAT-102 完成”“全链 PASS”等越权断言；出现的只是“不得写取消已解决”“FEAT-102 不因此标完成”等否定/限定语。**无新的全局阻断。**

## 5. 证据与命令审计

### 5.1 输入事实

- 设计 `122CFB22...`（806 行 / 119,217 B）；R7 报告 `5DACF2FD...`；R6→R8 `git diff --stat` 为 +112/−44（包含 R7 的 +92/−42 与 R8 的 5 项修正）。
- R7→R8 section 比对日志 `.codex-sandbox/FEAT-102/design-r8/r8-section-compare.log`：§12/§14/§15 等 SAME；仅 §3/§4/§16/§17 变化。
- `REWORK.md` L3：日期 2026-10-20，全部时刻 UTC；L106：`13:00:27.929Z→13:11:38.991Z`，585 passed/119 subtests/0 failed/0 skipped/670.36s。设计 §16.3 的时间与之一致。
- `EVD-2120`（`evidence-log.md:3023`）与 §16.3 的 585/0/0 一致。

### 5.2 命令审计

完整 JSON：`.codex-sandbox/FEAT-102/design-r8/command-audit.json`，SHA-256 `8D3BFC5DFAA680F27406F5353AC4B2E4DAF767A1B9511F145CDCA6807914BC63`。三条命令均只读/scratch；无宿主运行、无测试运行。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 日志 / SHA-256 |
|---|---|---|---|---|---|
| R8-STATIC | 设计/R7 报告 hash、大小、行数、设计 diffstat、worktree 状态 | 2026-10-21T00:16:02.9179118Z | 2026-10-21T00:16:03.4147944Z | 0 | `r8-static-audit.log` / `E7DB1781...` |
| R8-SECTIONS | R7 期望 section hash vs R8 当前 section | 2026-10-21T00:17:03.0900049Z | 2026-10-21T00:17:03.2768123Z | 0 | `r8-section-compare.log` / `8BCCA7AD...` |
| R8-FIX-READ | 五处修正点 + REWORK/EVD/overclaim 扫描 | 2026-10-21T00:17:56.4095715Z | 2026-10-21T00:17:56.5474286Z | 0 | `r8-fix-read.log` / `86071222...` |

补充：R8-FIX-READ 的 overclaim 扫描只命中“未闭合/不得写取消已解决/不因此标完成”等限定语，没有命中 live 的“取消已解决/全链 PASS/585 全绿”断言。未运行 `check-dsh-preset-compat`、DSH boot、任何测试套件；均 **NOT_RUN**。

## 6. 备注与路由

- **5/5 PASS，无新的全局阻断。** 结论 `APPROVED_WITH_NOTES / 0`；两项 P3（N-R8-1 表格注记位置、N-R8-2 括号措辞）是文本清理，不需要用户再裁定，也不改变设计方向或支持声明。
- 若要求严格“无任何新偏差”，可在机录前把 L61 注记移至表后并修掉 L53 括号；完成后本复核即为 clean。当前 AWN/0 已可推进 CODE R1，但不要把这当成代码/测试已审。
- §17.1 的“复审结论 AWN/0”是 **R7 报告（机器记录 REVIEW-FEAT-102-R8）** 的历史记录，不是本次 R8 的预判；本报告独立给出上述结论。

## 附录：证据 hash

| 文件 | SHA-256 |
|---|---|
| 设计（R8 被审） | `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE` |
| R7 报告（delta base） | `5DACF2FD2984262C7EEFD3D7934B8D312897A24DE58E405BB6492D3A67C60A6B` |
| command-audit.json | `8D3BFC5DFAA680F27406F5353AC4B2E4DAF767A1B9511F145CDCA6807914BC63` |
| r8-static-audit.log | `E7DB17814CE40D2BC47CF2F0B72866C1A439AEBAF7733B7DB8E85680FE46FEA6` |
| r8-section-compare.log | `8BCCA7AD69EBACBD0B5732832AED2BB046138A8348822456692983A0CD445A13` |
| r8-fix-read.log | `860712226D36490CC4A407F1B704E8CEE7EE730D12DAE74279AC48BADF60A48D` |
