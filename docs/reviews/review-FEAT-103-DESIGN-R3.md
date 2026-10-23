# FEAT-103 — DESIGN R3 聚焦增量复核（S-C7 更正 / M1 反馈 / 交接状态）

- 日期：2026-10-21（Asia/Shanghai）；独立 Design Reviewer（同一非 Producer Reviewer，只核 R3 增量）。
- **对象绑定**：设计 `docs/architecture/dsh-upstream-owned-registration-R1.md`，SHA-256 `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`（454 行 / 68,925 B）；修订前 = `7B43101CB9AA25561F655F976C5E4C6D1FCF16C3BD0E1AAFaf42261C1EBA3734`（412 行 / 62,356 B，按 R2 报告/M1 报告/设计 §12 R3-V01 的同一 hash；M1 报告中的小写形式为 `7b43101c…3734`）。前轮：`docs/reviews/review-FEAT-103-DESIGN-R2.md`，SHA-256 `E190F3BEBA137334ED992B05C88924A1159DE8C674E92F0C0A19ACBC10190245`（AWN/0）。
- **只读输入**：`.codex-sandbox/FEAT-103/M1-REPORT.md`，SHA-256 `8298ADBBFCBB944B01C80FA949B29FE7CBB723C1060A30D88CB414BDBD92F053`；`.codex-sandbox/FEAT-103/test-audit.txt`，SHA-256 `E2FAB9F21CB3B8D3DE4B09765124B4A96E5068C94C5C73A219E9FA44B90A3F99`；隔离副本 `.../agent-preset-registry/lib/index.js`，SHA-256 `233CF3531293FF1202FCF0A100A83F3BC149B0F4F54C9613567B89CF3299BE88`；`DEC-367`（decision-log L234）。
- **边界**：只判设计文本；M1 实现本身由并行 CODE R0 审查，本报告不评代码质量、不把 M1 当产品通过。未运行宿主、未跑测试、未改任何文件（只写本报告与 scratch）。真实环境无读写；SDK 仅只读核对公开 `Context.root/events` 类型。
- **方法**：复算 hash/行数；读取 S-C7 更正、§11.1、§11 交接状态、§12 R3 记录；对 M1 报告/test-audit 逐项核对；对 R2→R3 做 section 级检查（R2 设计 untracked 且 R2 review record 无 snapshot_bind，精确字节 diff 不可得，见 §4）；扫描 §4-§10 的 R3 标记。命令见 §6。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
four_items=PASS (4/4)
regression=SEMANTIC_PASS (byte-level R2 snapshot NOT_AVAILABLE; see §4)
new_global_blocker=NONE
new_p3_findings=2 (N-R3-1 title/date still R2; N-R3-2 copy-manifest citation)
host_run=NOT_RUN
tests=NOT_RUN
```

四项全部 PASS；无新的全局阻断。两个 P3 是文档/证据表述清理，不影响 R3 设计增量或 DEC-367 授权边界；因此给 `APPROVED_WITH_NOTES / 0`。

## 2. 逐项判定

| 项 | 判定 | 事实与证据 |
|---|---|---|
| **1. S-C7 更正事实成立；§3.5 未被绕过/错误关闭** | **PASS** | §3.3 CH-1.2 步骤 2（L165）已改为 `ownerCtx.root === this.ctx.root`；R3 更正块（L171-177）逐项给出：原谓词（L173，`ownerCtx.events === this.ctx.events`，明确标注“作废”而非“设计从未如此”）、误推来源（把 S-C7“每 root 单一 hook 表”误推为单一 `ctx.events` 对象）、M1 实测（L174：`root.events === ext.events === pctx.events` 均 false，`ctx.root` 同 root true/跨 root false）、无需 Cordis 核心变更的论证（L176：`ctx.root` 与 `events` 同属公开 Context 面，本更正是文本事实订正，不触发 §3.5）、实现落点（L177：sandbox registry L596-604，SHA `233CF353…99BE88`，+171/−0）。M1 报告 L60-L61 与之一致；本机 Cordis 公开类型 `Context.root: this`（`@experimental`）与 `Context.events: EventsService` 存在，root 构造器 `this.root=self`（`cordis/lib/index.js:1682`）。§3.5（L202）证伪出口 (a)(b)(c) 完整保留，未被移除或错误关闭；R3 更正是“无需核心变更”，不是“缺口已关闭”。 |
| **2. §11.1 M1 标签纪律与四条事实** | **PASS（附 P3 N-R3-2）** | 四条事实逐字匹配 M1：11 个源文件双端 SHA（M1 §1 表；registry 3 + agent types 1 + agent-loop 1 + session-controller 1 + subagent 2 + spawn 1 + fork 1 + vendor/scope 1 = 11）；+171/−0（M1 L43）；T01+ positive 5 passed / 0 failed / exit 0（M1 L79；test-audit L1 的 UTC 与 exit 一致）；变异体 no-observer 3/2 exit 1、single-owner 4/1 exit 1（M1 L80-L81；test-audit L2-L3）。§11.1 L405 明确全部为“隔离副本内、进程内、SOURCE 级证据”，不是宿主运行/已安装 SDK 行为/产品交付物。NOT_RUN 清单（L406）覆盖 host boot/真实 preset（M2）、CH-2/CH-3、T05+/T06+/T07+/T09+/T11+、legacy 交互（list/diagnostic/retain/mount/select）、signal-abort、性能 T10、webhook，并额外如实声明 close-before-start 防御性路径未用 fake 时序；与 M1 §5 一致，未混入 PASS。P3：事实 1 的 11 文件数由 M1 §1 表支持，但被引用的 `copy-manifest.txt` 实际只有 8 行（8 个 consumer/vendor 文件；registry 3 由 M1 §1 表/复制命令覆盖），引用应写清“M1 §1 + registry 复制命令”或把 registry 3 补进 manifest。 |
| **3. §11 交接状态与授权** | **PASS（附 P3 N-R3-1）** | L373 `design_revision=R3`；L379 `implementation_authorized=true`（DEC-367，用户 2026-10-21 显式选择隔离实施）；L380 `M1 done (B1 core), M2 pending`；L381 `runtime=NOT_RUN`（host boot 未执行，M1 是进程内 SOURCE）；L385 `upstream_patch_authorized=false`；L386 `release_authorized=false`。DEC-367 原文只授权“仓库内隔离副本实现/验证”，不写已安装 DSH/profile、不对外提交或安装，并要求独立 Code Reviewer 通过前不提交/不发布/不宣称取消安全；设计状态与之一致。`cordis_core_change_required=false`（L383）由 §3.5/`ctx.root` 公开面支持；`webhook_coverage=NOT_OBTAINED` 未冒充。P3：文首标题/日期仍写“FEAT-103 R2 / 2026-10-20”（L1/L3），与 L373 `design_revision=R3`/§12 R3 记录不一致；建议标题改为“R2 修订版 + R3 增量（2026-10-21）”或 R3，并补 R3 日期。 |
| **4. R2→R3 回归：§3/§4/§5/§6/§7/§8/§9/§10 合同语义** | **PASS（语义）；BYTE_DIFF=NOT_RUN** | R2 设计在 git 中 untracked，R2 review record 无 `snapshot_bind`，无 R2 文件字节副本；精确 R2→R3 byte diff 不可得（不伪造）。可做的 section 级检查：① §4/§5/§6 当前起始行 204/235/280，相对 R2 报告的 196/227/272 均为 +8，恰对应 §3.3 前 S-C7 块的插入，未显示 §4-§6 内部增删；§4-§10 行数分别为 31/45/29/15/13/19/6（含尾部空行），与 R2 报告范围一致（+1 为尾随空行）；② §4-§10 全文检索 R3 修订标记（`R3`/`2026-10-21`/`M1`/`S-C7`/`ctx.root`）只命中 L352 的 R2 内容 `BR3'`，无 R3 修订标记；③ R3 变更位置集中在 §3.3（步骤 2 + S-C7 块）、§11 状态、§11.1、§12 R3 证据表，§4-§10 的 B2/B3/D1-D3/T01+/T05+ 合同未见变化；④ 未新增未经 M1/设计证据支持的能力声明。**结论：合同语义未发现 R3 改动；精确字节级零改动因缺 R2 快照而 NOT_RUN，不声称 byte-identical。** |

## 3. Findings（仅 P3，非 blocking）

| ID | 级别 | Finding | 最小修正 |
|---|---|---|---|
| N-R3-1 | P3 | 文首标题/日期仍为 R2（L1/L3），与 §11 `design_revision=R3`、§12 R3 记录不一致 | 标题/日期改为“R2 修订版 + R3 增量（2026-10-21）”或 R3；保留文件名不变 |
| N-R3-2 | P3 | §11.1 事实 1 的 11 文件双端 SHA 由 M1 §1 表支持，但 `copy-manifest.txt` 仅 8 行；引用“copy-manifest.txt 全部=True”容易被读成 manifest 覆盖 11 文件 | 引用改为“M1 §1 表 + registry 复制命令（copy-manifest 8 个 consumer/vendor + registry 3 单列）”，或把 registry 3 补入 manifest 后再引用 |

无 P0/P1/P2。精确 R2 byte diff 的缺口是证据面限制，不是设计 finding；若 Coordinator 需要 byte-level 零改动证明，需提供 R2 设计快照后再补一行比对。

## 4. Section 级回归说明（R2→R3）

- R2 设计 hash `7B43101C…3734`、412 行 / 62,356 B（R2 报告 L5；M1 报告 L15；设计 §12 R3-V01）。R3 设计当前 454 行 / 68,925 B。R3 修订记录（§12 R3-V01/R3-V02）只列 S-C7 谓词更正、M1 实施反馈、交接状态；本报告独立核对这四处，未发现 §4-§10 的 R3 修订标记。
- 当前 section 起始：§4 204、§5 235、§6 280、§7 309、§8 324、§9 337、§10 356。R2 报告的 §4/§5/§6 起始为 196/227/272，均 +8；这正是 S-C7 块插入的净行数；区间行数差 +1 来自尾随空行，未见内容增删。
- §4-§10 的 R3 标记扫描只命中 L352 `BR3'`（R2 的蓝军编号，不是 R3 修订），未命中 `2026-10-21`/`M1` 等 R3 标记。§12 R3-V01 的“设计 7B43101C”与 R2 报告/M1 报告 hash 一致。
- 因 R2 设计 untracked 且 R2 review record 无 snapshot_bind，**不能**做逐字节 diff；本报告结论限定为“合同语义未发现变化”，不把 NOT_RUN 说成 PASS。

## 5. 未被绕过的历史/门

- S-C7 更正文案明确引用原谓词、M1 实测和“作废”原因，没有把“实测不成立”改写成“设计从未如此”；M1 报告 L60-L61 与 §11.1 L407 同时保留“设计事实偏差”披露。
- §3.5 证伪出口 (a)(b)(c) 原文仍在 L202；没有把 S-C7 更正当成核心缺口关闭，也没有移除 D1–D3/B2/B3/CH-1.5 的 NOT_RUN 或禁 timeout/最终清理抵销约束。
- §11.1 四条事实全部限定为隔离副本/进程内/SOURCE；host boot、CH-2/CH-3、T05+~T11+、legacy、signal、T10、webhook 均 NOT_RUN；没有新的“已适配/取消安全”声明。

## 6. 命令审计

完整 JSON：`.codex-sandbox/FEAT-103/design-r3/command-audit.json`，SHA-256 `36E626129B242356B528F7525371A53B7D2C0E2CE4A40409C1CF4D7DC471533A`。四条命令均为只读/scratch；无宿主运行、无 DSH_HOME 运行、无真实 profile 写入。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 影响路径 / 日志 SHA-256 |
|---|---|---|---|---|---|
| R3-STATIC | 设计/R2 报告/M1/test-audit/sandbox hash 与 worktree 状态 | 2026-10-21T05:55:14.5756782Z | 2026-10-21T05:55:14.8976720Z | 0 | 设计 `A1F676EE…`；R2 `E190F3BE…`；M1 `8298ADBB…`；test-audit `E2FAB9F2…`；sandbox `233CF353…`；`r3-static-audit.log` / `F7AEC535…` |
| R3-SECTION | 当前 section 范围 + §4-§10 R3 标记扫描 | 2026-10-21T06:03:47.7624469Z | 2026-10-21T06:03:47.9108319Z | 0 | §4-§10 起始/行数；仅 L352 `BR3'`；`r3-section-check.log` / `414A1A04…` |
| R3-EVIDENCE | M1 报告/test-audit/DEC-367/S-C7/§11/§11.1 逐行读取 | 2026-10-21T06:04:23.4025607Z | 2026-10-21T06:04:23.5255342Z | 0 | `r3-evidence-read.log` / `FF1EE380…`；copy-manifest 8 行 |
| R3-SDK-READ | Cordis 公开 Context `root/events` 类型与 root 赋值 | 2026-10-21T06:04:43.4391966Z | 2026-10-21T06:04:43.5433478Z | 0 | `context.d.ts:20-25`（root @experimental / events）；`index.js:1682` `this.root=self`；`r3-sdk-read.log` / `8BB193BF…` |

未运行：宿主 boot、pytest/产品测试、M1/T01+ 重跑、真实 profile 检查。M1 的 5/0/exit0 与变异体结果是设计引用的 M1 证据，本轮未重跑；未把 RE-RUN 当 PASS。

## 7. NOT_RUN / 限制

- **R2→R3 精确 byte diff = NOT_RUN**：R2 设计文件 untracked，R2 review record 无 snapshot_bind；本轮只完成语义/结构 section 检查。若要求 byte-identical，需 Coordinator 提供 R2 快照后再补。
- **M1 实跑 = 未重跑**：T01+ 5/0/exit0、mutants 3/2、4/1 来自 M1 报告/test-audit；本报告只核对文本与审计行，不重跑进程内测试。
- **host boot/真实 preset、CH-2/CH-3、T05+/T06+/T07+/T09+/T11+、legacy 交互、signal、T10、webhook = NOT_RUN**（设计 §11.1 L406 已声明；M1 §5 同）。
- 未读/未写真实 `~/.dsh`；未运行宿主；设计 SDK 只读核对 Cordis 类型。

## 8. 结论与路由

- **`APPROVED_WITH_NOTES`，`unresolved_blockers=0`；四项 PASS，无新的全局阻断。**
- 两个 P3（N-R3-1 标题/日期、N-R3-2 copy-manifest 引用）是文本/证据清理，不阻断 R3 设计增量或 CODE R0/M1 交接；建议在机录前修。
- 无用户再裁定事项：DEC-367 已覆盖实现授权；R3 只是设计增量，`upstream_patch_authorized=false`、`release_authorized=false`、`runtime=NOT_RUN` 不变。
- 设计 §11.1 的四条事实只作“隔离副本内进程内 SOURCE 级证据”，不得被 CODE 链写成 host/runtime 通过；CODE R0 仍需独立审查 M1 实现。

## 附录：hash

| 文件 | SHA-256 |
|---|---|
| 设计（R3） | `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF` |
| R2 报告 | `E190F3BEBA137334ED992B05C88924A1159DE8C674E92F0C0A19ACBC10190245` |
| M1 报告 | `8298ADBBFCBB944B01C80FA949B29FE7CBB723C1060A30D88CB414BDBD92F053` |
| test-audit | `E2FAB9F21CB3B8D3DE4B09765124B4A96E5068C94C5C73A219E9FA44B90A3F99` |
| sandbox registry | `233CF3531293FF1202FCF0A100A83F3BC149B0F4F54C9613567B89CF3299BE88` |
| command-audit.json | `36E626129B242356B528F7525371A53B7D2C0E2CE4A40409C1CF4D7DC471533A` |
| r3-static-audit.log | `F7AEC535A1B40E24861076B6D8A331793922469B86B1F63E33409DB56B4D8420` |
| r3-section-check.log | `414A1A04A0DD8332031BF61B7A9363C82D840EF87837229BB17918562C12BA8A` |
| r3-evidence-read.log | `FF1EE380689ABD5CB896D1B36B5C60D071500B8A16114C536FAC4638DB7BB3FF` |
| r3-sdk-read.log | `8BB193BF07AD7FAD6B26CD04AD6617C6E84608341C24617F71071E89F17F9D19` |
