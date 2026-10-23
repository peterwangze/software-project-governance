# FEAT-103 — DESIGN R4 聚焦增量复核（closedIds / fallback / CH-1.6 / M2 API / 交接）

- 日期：2026-10-22（Asia/Shanghai）；独立 Design Reviewer（同一非 Producer Reviewer，只核 R4 增量）。
- **对象绑定**：设计 `docs/architecture/dsh-upstream-owned-registration-R1.md`，SHA-256 `D383D7E909C828C100A96FEC7A8B74CD8736851F5B0419E36AA448F73E7BEE43`（512 行 / 82,066 B）；修订前 R3 = `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`（454 行 / 68,925 B）。前轮 `docs/reviews/review-FEAT-103-DESIGN-R3.md`，SHA-256 `0C9116357351E3AD8A893A4392ADAD87DC780D5B065022911A193504ADA9AEE4`（AWN/0）。
- **只读依据**：`docs/reviews/review-FEAT-103-CODE-R2.md`（NEEDS_CHANGE/1，SHA `AD32DF7CEC952CAA528047C97CD41A13FC7C0BAA38B9C52879C729CE8F0544D9`）；`.codex-sandbox/FEAT-103/M2-REPORT.md`（`C35FD656B601D99161AC16F69F7B537465635DA86CA0F3BEC56CFEFA2C097FB6`）；`M2-TEST-AUDIT.md`（`A7421DFE6ADDE082AB3DCFCC972E308F037B37660BC1CBC489714E02A0376FC0`）；`M1-FIX-REPORT.md`（`F9562B7DC6424E08C2F6AA176875A17A976371FB2FABD4F08B5D6B852915B9BB`）；`DEC-367`（decision-log L234）。
- **边界**：M2-FIX 代码返工**并行进行中、未完成未审查**，不作为 R4 修复证据；本报告只判设计文本，不评 M2/M2-FIX 实现质量。未运行宿主/测试，未改任何文件（只写本报告与 scratch）。
- **方法**：复算 hash/行数；逐项读取 §5.6/§5.3/§3.3/§5.4/§6.1/§11/§13；对 R3→R4 做 section 级行数与位置比对；逐条核对 CODE R2/M2/M1-FIX 事实；命令见 §6。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
five_items=PASS (5/5, with P2/P3 notes)
regression=SEMANTIC_PASS (R3 byte snapshot NOT_AVAILABLE; see §4)
new_global_blocker=NONE
p2=2 (N-R4-1 error-code naming; N-R4-2 CH-1.6 tombstone wording)
p3=4 (N-R4-3 §9 risk missing; N-R4-4 §5.4 status P3-2; N-R4-5 fallback test gap; N-R4-6 title/date)
host_run=NOT_RUN
tests=NOT_RUN
```

五项全部 PASS；无新的全局阻断。P2/P3 是**文本合同/证据链清理**，不影响 R4 的设计方向或 DEC-367 授权边界；因此给 `APPROVED_WITH_NOTES / 0`。

## 2. 逐项判定

| 项 | 判定 | 事实与证据 |
|---|---|---|
| **1. §5.6 `closedIds` 墓碑合同** | **PASS（附 N-R4-1/N-R4-3）** | §5.6（L297-305）逐条定义：consumer 可见 `agent-preset/closed` vs `not-found` 及判定点（acquire/select/attach/publicationCommit）；写入点=close/activation-failed（L300）；**仅同 id 成功重注册后清除**、失败保留、不得在 owner 校验前清除；legacy `register` 的 disposer/unregister 不写墓碑、legacy 关闭仍 not-found（L301）；G1→G2 后冻结 G1 的 select/attach/publicationCommit/回退一律 closed（L302）；明示取代/细化 §5.3 #6/#7 并覆盖 fallback（L304）；清理/容量策略 L303。与 CODE R2 P2-4/P2-1/P3-5 的合同要求一致。P2 N-R4-1：§4.2 L227/L234、§5.3 #3 L261 仍写 `REGISTRATION_CLOSED`，而 §5.3 #6/#7 L264-265、§5.6 L299/L302 写 `agent-preset/closed`；M2 代码只产 `agent-preset/closed`（`presetClosedError` :870），设计未声明二者映射。P3 N-R4-3：L303 称“增长面在 §9 风险面披露”，但 §9 表（L365-374）没有 `closedIds` 增长/容量行 |
| **2. fallback 冻结 generation** | **PASS（附 N-R4-5）** | §5.3 #6/#7（L264-265）要求回退 attempt 携带首个 attempt 的冻结 generation/标识，禁止按 id 重取；同一精确 generation closed/retired → `agent-preset/closed`，不静默取 G2；L271 的“冻结 generation 的传递”bullet 覆盖 StartedSinceObserved 与 SessionAlreadyOwned-无 live，并说明 M2 现状仍按 id 重取（CODE R2 P1-1 未关闭），M2-FIX 修正并补用例。与 §5.3 #4/#5 的新 operation 取当前代、#3 live-switch 的冻结事务不矛盾（代号命名问题见 N-R4-1）。P3 N-R4-5：L271 只点名补“G1→G2 + StartedSinceObserved”用例；#7 的 SessionAlreadyOwned-无 live 也是 fallback，测试要求应同时覆盖 |
| **3. §3.3 CH-1.6 `activation-failed` 终态** | **PASS（附 N-R4-2）** | L198 给出完整链：ready failed → closed/`activation-failed` → definitions 精确删除 → closed settle `{previous:'failed'}` → `_drain()`（无 generation 同步）→ drained + `_forget` + signal detach；L199 first-reason-wins（T01-h）；L200 内部终态不进公开 `close(reason)` 四值词表，`OWNED_INTERNAL_TERMINAL_REASONS`/`OwnedTerminalReason` 区分；L201 标 M1-FIX SOURCE 级、host NOT_RUN。与 §5.6 L300 的“activation-failed 写入墓碑”不冲突的前提是 `_forget` 不清墓碑；但 L198 括号“owner 索引与**墓碑清理**路径同 close”措辞含糊，可能被读成清理 tombstone（N-R4-2） |
| **4. §5.4 R4 增量 + §6.1 L312 M2 API 合同** | **PASS（附 N-R4-1/N-R4-4）** | §5.4 L285-288：token `HELD→ATTACHED→COMMITTED`、`release()` 仅 HELD；`attach` 两阶段 `commit()`/`publicationCommit()`，后者同步不 append、只做 fence；attach 事务化（join/rebind 成功后才置 ATTACHED，失败回滚并释放 hold）；selectWithAdmission append 失败先恢复旧 binding/不 collect，成功才 users--/collect/COMMITTED，成功 collect 失败隔离为诊断；冻结 generation 一致性。§6.1 L312 publicationCommit 同步 fence。M2 报告 A1-A6、M2 实现事实与 CODE R2 判定（CH-3.2 主路径、CH-3.3、A4/A5）对应；CODE R2 P2-3 的已知缺陷面（先 ATTACHED 再 rebind）被设计明确称为缺陷并交 M2-FIX，未冒充已修。P3 N-R4-4：L289 状态只列 P2-2/P2-3 未覆盖，未列 CODE R2 P3-2 的“成功后 collect(previous) 失败隔离”实现/测试缺口；合同 L287 已写，状态应同样披露 |
| **5. §11 交接状态** | **PASS（附 N-R4-6）** | L401 `design_revision=R4`；L408 `implementation_authorized=true`（DEC-367）；L409 `implementation_progress=M1 done / M2 done / M2-FIX in progress`；L407 `independent_review=R4 待独立复审（RECHECK-FEAT-103-R8）`；L414 `upstream_patch_authorized=false`；L415 `release_authorized=false`；L410 runtime=NOT_RUN；L413 webhook=NOT_OBTAINED。与 DEC-367（只授权仓库内隔离副本、不写已安装 DSH/profile、不对外提交/安装、独立 Code Reviewer 通过前不提交/不发布）一致，无越权声明。P3 N-R4-6：文首标题/日期仍写“FEAT-103 R2 / 2026-10-20”（L1/L3），与 L401 R4 状态不一致 |
| **6. 回归** | **PASS（语义/结构）；R3 byte diff=NOT_RUN** | 见 §4。§4/§7/§8/§9/§10 行数与 R3 **完全相同**（31/15/13/19/6），仅整体下移；§3 +7（CH-1.6）、§5 +20（§5.3/5.4/5.6）、§6 +1（§6.1）、§11 +1、§12 +12、§13 新增；§3.5 L209 证伪出口文本未改；§14/§15 不存在（N/A）。R3 设计文件 untracked、无快照，精确 byte diff **NOT_RUN**，不伪造 |

## 3. Findings（P2/P3，非 blocking）

| ID | 级别 | Finding | 最小修正 |
|---|---|---|---|
| N-R4-1 | P2 | **closed 错误命名不一致**：§4.2 L227/L234、§5.3 #3 L261 使用 `REGISTRATION_CLOSED`；§5.3 #6/#7 L264-265、§5.6 L299/L302、§5.4/§6.1 使用 `agent-preset/closed`。M2 代码只产 `agent-preset/closed`（`presetClosedError` :870），设计未定义 `REGISTRATION_CLOSED` 是内部别名还是旧文档残留 | 在 §5.6 增加一行映射“`REGISTRATION_CLOSED`（内部/旧名）↔ `agent-preset/closed`（consumer 可见）”，或把 §4.2/§5.3 #3 统一改为 `agent-preset/closed`；不得让两套名并存而无映射 |
| N-R4-2 | P2 | **CH-1.6 与 §5.6 墓碑关系措辞含糊**：L198 说 `_forget` 执行“owner 索引与**墓碑清理**路径同 close”；§5.6 L300 要求 activation-failed **写入**墓碑且仅成功重注册才清除。M2 代码 `_forget` 只清 owner 索引，不碰 `closedIds`；文本可能被实现者读成“activation-failed 后清墓碑”，从而把 closed 退化为 not-found | 把 L198 改为“`_forget` 只清 owner 索引；`closedIds` 已在激活失败终态写入并保留（§5.6）”，或明确“墓碑处理同 close（写入，不清除）” |
| N-R4-3 | P3 | §5.6 L303 声称 `closedIds` 增长面在 §9 风险面披露；§9（L365-374）没有 closedIds/容量行，属悬空引用 | 在 §9 增加一行“closedIds 无上限，增长面=已关闭 id 字符串；当前接受”或删除“在 §9 披露”措辞 |
| N-R4-4 | P3 | §5.4 L289 状态只列 attach 抛错路径/HELD=0 聚合未覆盖（P2-2/P2-3），未列 CODE R2 P3-2（`selectWithAdmission` 成功后 `collect(previous)` 失败隔离）的实现/测试状态；L287 已写成合同，但“A1-A6 通过”可能让读者以为该异常出口已覆盖 | 在 L289 增加“成功后 collect 失败隔离（P3-2）未实现/未测，M2-FIX 或 CODE R3 处理”，或把该合同标为设计合同、实现 NOT_RUN |
| N-R4-5 | P3 | §5.3 L271 只要求补“G1→G2 + StartedSinceObserved”用例；#7 的 SessionAlreadyOwned-无 live 也是 fallback，CODE R2 P1-1 同时点名二者，测试要求不完整 | L271 补“SessionAlreadyOwned-无 live 同 G1→G2 用例”，断言 closed 或精确复用 G1，不取 G2 |
| N-R4-6 | P3 | 文首标题/日期仍“FEAT-103 R2 / 2026-10-20”，与 §11 R4 状态、§13 R4 记录不一致 | 标题/日期改为“R2 修订版 + R4 增量（2026-10-22）”或 R4；文件名不变 |

**§13 编号**：可接受。文件原止于 §12，R4 记录紧随 §12 记为 §13，无 §14/§15、无悬空 §17 引用；§13 的编号偏差说明清楚。未发现引用/一致性缺陷，不因此判 NEEDS_CHANGE（仅建议该说明写成“新增本节前文件止于 §12”更精确）。

## 4. Section 级回归（R3→R4）

| 区段 | R3 行范围/行数 | R4 行范围/行数 | 判定 |
|---|---|---|---|
| §1 | 10-32 / 23 | 10-32 / 23 | SAME |
| §2 | 33-125 / 93 | 33-125 / 93 | SAME |
| §3 | 126-203 / 78 | 126-210 / 85 | +7：CH-1.6 插入；§3.4/§3.5 仅下移，§3.5 L209 证伪出口未改 |
| §4 | 204-234 / 31 | 211-241 / 31 | 行数相同；无 R4 修订标记，语义未发现变化 |
| §5 | 235-279 / 45 | 242-306 / 65 | +20：§5.3 #6/#7+bullet、§5.4 R4 块、§5.6 新增 |
| §6 | 280-308 / 29 | 307-336 / 30 | +1：§6.1 publicationCommit bullet |
| §7 | 309-323 / 15 | 337-351 / 15 | 行数相同，仅下移 +28 |
| §8 | 324-336 / 13 | 352-364 / 13 | 行数相同，仅下移 +28 |
| §9 | 337-355 / 19 | 365-383 / 19 | 行数相同，仅下移 +28 |
| §10 | 356-361 / 6 | 384-389 / 6 | 行数相同，仅下移 +28 |
| §11 | 362-408 / 47 | 390-437 / 48 | +1：交接状态字段 |
| §12 | 409-454 / 46 | 438-495 / 58 | +12：R4 事实复核表 |
| §13 | — | 496-512 / 17 | 新增 R4 修订记录 |

- 结论：§4/§7/§8/§9/§10 行数完全相同且仅整体下移，未发现 R4 编辑；§5/§6 的变化与任务列出的合同增量一致；§3.5 证伪出口、§14/§15（不存在）无改写。R3 设计文件 untracked 且无快照，**精确 byte-level R3→R4 diff = NOT_RUN**；上表是 section 级结构/语义比对，不声称 byte-identical。
- 标签纪律：CH-1.6/SOURCE 实现（M1-FIX）与 host NOT_RUN 分离；§5.4 status/SOURCE 与 NOT_RUN 分离；§5.6 status/SOURCE 与 NOT_RUN 分离；§11/§13 未把 M2-FIX 写成已审。未新增未验证能力声明。

## 5. 证据摘要

- R4 设计 = `D383D7E9…`（512 行/82,066 B）；R3 报告 = `0C911635…`；CODE R2 = `AD32DF7C…F0544D9`；M2 = `C35FD656…C097FB6`；M2 audit = `A7421DFE…A0376FC0`；M1-FIX = `F9562B7D…2915B9BB`。
- CODE R2：P1-1 fallback 跨代、P2-1 closedIds 清除时机、P2-3 attach ATTACHED 泄漏、P3-2 collect 失败隔离；M2 A1-A6、C1-C10/C12；M1-FIX activation-failed/T01-g/T01-h 9/9；设计 R4 对应文本已复核。
- 设计 §5.4/§5.6 的实现状态与 M2-FIX 在途一致；未把 M2-FIX 当已修复。
- `§13` 编号按上述“可接受”；无 §14/§15 历史。

## 6. 命令审计

完整 JSON：`.codex-sandbox/FEAT-103/design-r4/command-audit.json`，SHA-256 `67E0D050FD62A8780F82FD21EAC381CB69F647F98A533BB3EAAB69F6F349F3E6`。三条命令均只读/scratch；无宿主运行、无 DSH_HOME、无真实 profile 读写。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 日志 / SHA-256 |
|---|---|---|---|---|---|
| R4-STATIC | 设计/R3 报告/CODE R2/M2/M1-FIX hash 与 worktree 状态 | 2026-10-22T06:10:35.8264035Z | 2026-10-22T06:10:36.1103501Z | 0 | `r4-static-audit.log` / `E04EAB49…` |
| R4-SECTION | 当前 section 范围 + R3→R4 行数/标记扫描 | 2026-10-22T06:13:08.9456524Z | 2026-10-22T06:13:09.1339053Z | 0 | `r4-section-check.log` / `EF35ADBE…` |
| R4-EVIDENCE | CODE R2/M2/M1-FIX 事实与设计 R4 行读取 | 2026-10-22T06:14:13.2726668Z | 2026-10-22T06:14:13.4123514Z | 0 | `r4-evidence-read.log` / `71629230…` |

未运行：宿主 boot/真实 preset、pytest/产品测试、M2/M1-FIX 重跑、真实 profile 检查。代码返工 M2-FIX 未纳入判定。

## 7. NOT_RUN / 限制

- **R3→R4 精确 byte diff = NOT_RUN**：R3 设计文件 untracked，未发现快照；本报告只做 section 级结构/语义比对。
- **M2-FIX = 未完成/未审查**：实现面由 CODE R3 复审；本报告不把 M2-FIX 当设计修复证据。
- host boot/真实 publish、CH-2/T06+、legacy 回归、storage gap、fork 运行、T10、webhook = NOT_RUN（M2 报告 §5 已披露；本报告不重跑）。
- 未新增/未验证运行能力；`runtime=NOT_RUN`、`release_authorized=false`、`upstream_patch_authorized=false` 保持。

## 8. 结论与路由

- **`APPROVED_WITH_NOTES`，`unresolved_blockers=0`；五项 PASS，无新的全局阻断。**
- 两个 P2（N-R4-1 错误码映射、N-R4-2 CH-1.6 墓碑措辞）与四个 P3 是文本合同/证据链清理，不阻断 R4 方向；建议机录前修。
- §13 编号可接受；无需用户再裁定。DEC-367 已覆盖实现授权，M2-FIX 仍交 CODE R3，设计不声称其已通过。
- 若需 byte-level R3→R4 零改动证明，需提供 R3 设计快照后再补；当前明确 NOT_RUN。

## 附录：hash

| 文件 | SHA-256 |
|---|---|
| 设计（R4） | `D383D7E909C828C100A96FEC7A8B74CD8736851F5B0419E36AA448F73E7BEE43` |
| R3 报告 | `0C9116357351E3AD8A893A4392ADAD87DC780D5B065022911A193504ADA9AEE4` |
| CODE R2 | `AD32DF7CEC952CAA528047C97CD41A13FC7C0BAA38B9C52879C729CE8F0544D9` |
| M2 报告 | `C35FD656B601D99161AC16F69F7B537465635DA86CA0F3BEC56CFEFA2C097FB6` |
| M2 TEST AUDIT | `A7421DFE6ADDE082AB3DCFCC972E308F037B37660BC1CBC489714E02A0376FC0` |
| M1-FIX | `F9562B7DC6424E08C2F6AA176875A17A976371FB2FABD4F08B5D6B852915B9BB` |
| command-audit.json | `67E0D050FD62A8780F82FD21EAC381CB69F647F98A533BB3EAAB69F6F349F3E6` |
| r4-static-audit.log | `E04EAB49095D6C2DDB1ED4DBC10A454279A12159A8194A01F815A680F072EF5E` |
| r4-section-check.log | `EF35ADBECE6EE0EB3356FF3FA7812968E3880CB0D8A73A9EB9632F3DB6E0A185` |
| r4-evidence-read.log | `716292301DD9664FEF1B14124561331637B5D645FA3468BA5FEDD8356DF22777` |
