# FEAT-103 — DESIGN R4-P2 聚焦复核（N-R4-1/2/3/5/6）

- 日期：2026-10-22（Asia/Shanghai）；独立 Design Reviewer（同一非 Producer Reviewer，只核 R4-P2 五项与回归）。
- **对象绑定**：设计 `docs/architecture/dsh-upstream-owned-registration-R1.md`，SHA-256 `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5`（515 行 / 83,810 B）；修正前 R4 = `D383D7E909C828C100A96FEC7A8B74CD8736851F5B0419E36AA448F73E7BEE43`（512 行 / 82,066 B）。前轮 `docs/reviews/review-FEAT-103-DESIGN-R4.md`，SHA-256 `EB3BBF5D0823A8D9A496C3A113FED9032DC4C6388CC7C532C69B780E893F7D7F`（116 行）。
- **范围**：只核 R4 报告指定的五项 **N-R4-1（P2 错误码映射）、N-R4-2（P2 `_forget` 措辞）、N-R4-3（P3 §9 容量行）、N-R4-5（P3 fallback 两类用例）、N-R4-6（P3 文首一致性）** 与回归。R4 的 **N-R4-4**（§5.4 状态漏列 P3-2）不在本轮指定五项内；文件未见该项改动，本轮不判 PASS/FAIL。M2-FIX 代码仍在 CODE R3 复审，排除；CODE R3 报告当前不存在。未运行宿主/测试。
- **方法**：复算设计/R4 报告 hash；读取五处修正点与 R4 report finding labels；对 R4→R5 做 section 级行数/位置比对；命令见 §6。

## 1. 结论

```text
conclusion=APPROVED
unresolved_blockers=0
five_items=PASS (5/5)
regression=SEMANTIC_STRUCTURAL_PASS
r4_to_r5_byte_diff=NOT_RUN (R4 design snapshot unavailable; see §4)
new_global_blocker=NONE
host_run=NOT_RUN
tests=NOT_RUN
```

五项均按最小修正落地，未发现新增偏差或全局阻断；R4→R5 的 section 级比对只显示 §5 +2 行、§9 +1 行及已指定的同数量行内修正，其余区段行数不变。因此给 `APPROVED / 0`。

## 2. 逐项 PASS/FAIL

| 项 | 判定 | 事实 |
|---|---|---|
| **N-R4-1 错误码映射** | **PASS** | §4.2 L227 已补“**R4 映射：owned 路径的消费者可见 code 为 `agent-preset/closed`，见 §5.3「错误码映射」**”；§5.3 #3 L261 已改为“owned 路径消费者码为 `agent-preset/closed`；`REGISTRATION_CLOSED` 是既有接口合同名，映射见本节末”；L273 新增映射段：`REGISTRATION_CLOSED`=既有错误合同名（legacy/接口层）、`agent-preset/closed`=owned 消费者可见 code、**语义等价**、**owned 一律发后者、legacy 保持前者**、禁止无解释混用；其余历史出现按此映射阅读（覆盖 §4.3 L234 等历史行）。 |
| **N-R4-2 `_forget` 措辞** | **PASS** | §3.3 L198 已改为：`_forget`（**只清 owner 多值索引与 id 主表**；`closedIds` **墓碑保留**，后续仅由同 id 成功重注册清除，见 §5.6；signal listener 同路径 detach）。不再出现“墓碑清理”的歧义表述，与 §5.6 L300/L305 的写入/保留/成功重注册清除一致。 |
| **N-R4-3 §9 容量行** | **PASS** | §9 新增 L377 行“墓碑容量/清理”：`closedIds` 仅保留已关闭 id 字符串；同 id 成功重注册清除、registry 卸载整体丢弃（§5.6）；无 LRU/容量上限，长期增长占内存（未测），若需上限另立合同。§5.6 L305 的“在 §9 风险面披露”引用现已成立。 |
| **N-R4-5 fallback 两类用例** | **PASS** | §5.3 L271 已要求“补「G1→G2 + `StartedSinceObserved`」与「G1→G2 + `SessionAlreadyOwned`-无 live」**两类** fallback 用例（断言 closed 或精确复用 G1，不得静默取 G2）”；与 #6/#7 的合同面一致，覆盖 CODE R2 P1-1 的两个分支。 |
| **N-R4-6 文首一致性** | **PASS** | L1 标题已改为“R2 修订版 + R3/R4 增量”（含 R3 S-C7、R4 合同增量）；L3 日期已加“R3 增量 2026-10-21、R4 增量 2026-10-22（与 §11 `design_revision=R4` 一致）”；L5 文件性质已改为“R2 修订版 + R3/R4 增量”，并列出 R4 错误码映射。与 `design_revision=R4` 一致。 |
| **6. 回归** | **PASS（结构/语义）** | 见 §4：仅 §5 +2 行、§9 +1 行；§3/§4/§6-§13 行数不变，整体下移；§3.5 证伪出口与 §13 编号未改。**R4→R5 byte-level diff=NOT_RUN**（R4 设计快照不可得，不伪造）。 |

## 3. 新偏差

**未发现指定五项范围内的新增偏差。** 设计仅增加 L273 映射段、§9 L377 容量行，修改 L198/L227/L261/L271 与文首 L1/L3/L5。N-R4-4 不在本轮五项内，文件 §5.4 状态行仍只列 P2-2/P2-3，本轮不判；若需闭环，另行派单。

## 4. R4→R5 section 级回归

| 区段 | R4 行范围 / 行数 | R5 行范围 / 行数 | 判定 |
|---|---|---|---|
| §1 | 10-32 / 23 | 10-32 / 23 | 行数不变 |
| §2 | 33-125 / 93 | 33-125 / 93 | 行数不变 |
| §3 | 126-210 / 85 | 126-210 / 85 | 行数不变；仅 L198 同位置措辞（N-R4-2） |
| §4 | 211-241 / 31 | 211-241 / 31 | 行数不变；仅 L227 同位置映射脚注（N-R4-1） |
| §5 | 242-306 / 65 | 242-308 / 67 | **+2**：L273 映射段（N-R4-1）；L261/L271 同位置修正 |
| §6 | 307-336 / 30 | 309-338 / 30 | 行数不变，仅下移 +2 |
| §7 | 337-351 / 15 | 339-353 / 15 | 行数不变 |
| §8 | 352-364 / 13 | 354-366 / 13 | 行数不变 |
| §9 | 365-383 / 19 | 367-386 / 20 | **+1**：L377 容量行（N-R4-3） |
| §10 | 384-389 / 6 | 387-392 / 6 | 行数不变 |
| §11 | 390-437 / 48 | 393-440 / 48 | 行数不变 |
| §12 | 438-495 / 58 | 441-498 / 58 | 行数不变 |
| §13 | 496-512 / 17 | 499-515 / 17 | 行数不变，§13 编号未改 |

- 结论：**仅 §5 +2、§9 +1**；其余区段行数不变，仅因插入整体下移。文首 L1/L3/L5 同为行数不变的 N-R4-6 修正；§3 L198、§4 L227、§5 L261/L271 为指定同位置修正。未发现 §6-§13 合同语义或 §3.5 证伪出口被改写；§13 编号未改。
- **R4→R5 精确 byte diff = NOT_RUN**：R4 设计文件 untracked、未发现快照；以上为 section 级行数/位置 + 已指定行读取，不声称 byte-identical。R4 报告中的 N-R4-4 不在五项，未作为回归差异判定。

## 5. 证据与命令审计

### 5.1 事实

- 设计 `30E6FF02…`（515 行 / 83,810 B）；R4 报告 `EB3BBF5D…`（116 行）；CODE R3 报告不存在（未生成）。
- R4→R5 行数：§5 65→67（+2）、§9 19→20（+1）；其他区段行数相同（见 §4）。
- 五处读取：L227/L261/L273（N-R4-1）、L198（N-R4-2）、L377（N-R4-3）、L271（N-R4-5）、L1/L3/L5（N-R4-6）。
- 未运行宿主/测试；M2-FIX 代码未纳入。

### 5.2 命令审计

完整 JSON：`.codex-sandbox/FEAT-103/design-r5/command-audit.json`，SHA-256 `C3BC7ED68C7E00402521AB38BBEA72B5C623A3FF6D0445370E0EE4F6C136DD29`。三条只读/scratch；无宿主运行。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 日志 / SHA-256 |
|---|---|---|---|---|---|
| R5-STATIC | 设计/R4 报告/CODE R3 存在性、hash、worktree 状态 | 2026-10-22T06:19:12.0009466Z | 2026-10-22T06:19:12.2688634Z | 0 | `r5-static-audit.log` / `E8E7F5E8…` |
| R5-SECTION | R5 section 范围（用于 R4→R5 回归） | 2026-10-22T06:19:36.7872993Z | 2026-10-22T06:19:36.9773030Z | 0 | `r5-section-check.log` / `69C343D1…` |
| R5-EVIDENCE | 五处修正点与 R4 finding labels | 2026-10-22T06:20:22.9005335Z | 2026-10-22T06:20:23.0292742Z | 0 | `r5-evidence-read.log` / `2716E722…` |

未运行：任何 DSH 宿主、pytest/产品测试、M2/M2-FIX 重跑、真实 profile 检查；均 NOT_RUN。R4→R5 byte-level diff NOT_RUN（R4 snapshot 不可得）。

## 6. 结论与路由

- **`APPROVED`，`unresolved_blockers=0`；五项全部 PASS，无新的全局阻断。**
- N-R4-1/N-R4-2（P2）与 N-R4-3/N-R4-5/N-R4-6（P3）均按最小修正落地；N-R4-4 不在指定范围，保持原状、不判。
- R4→R5 精确 byte diff 只能标 NOT_RUN；section 级回归无指定范围外改动。若 Coordinator 需要 byte-level 证明，需提供 R4 设计快照后再补。
- 无用户再裁定事项；M2-FIX 仍交 CODE R3，R4 设计增量不声称 M2-FIX 已通过。

## 附录：hash

| 文件 | SHA-256 |
|---|---|
| 设计（R5） | `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5` |
| R4 报告 | `EB3BBF5D0823A8D9A496C3A113FED9032DC4C6388CC7C532C69B780E893F7D7F` |
| command-audit.json | `C3BC7ED68C7E00402521AB38BBEA72B5C623A3FF6D0445370E0EE4F6C136DD29` |
| r5-static-audit.log | `E8E7F5E8EFF142B74959D3C38C9235ABCD3A772F1BB18C80F611405ECDD96480` |
| r5-section-check.log | `69C343D15DC382A998A206D314D67A1CBF07FAE525C46B5483CB9EBCE6726F70` |
| r5-evidence-read.log | `2716E72238B4174E5B2BB9102DC179F202EB0BA3FC9C2B9BB96E8AAA9B13337B` |
