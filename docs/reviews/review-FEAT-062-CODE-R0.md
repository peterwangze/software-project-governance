# Review FEAT-062 · CODE · R0 —— closure 取消纵切（0.88.0 阶段 E1 · arch Q5 最小纵切，rollback §8 #5 清偿首半）

> 审查人: Code Reviewer Agent（独立，只读）· 轮次: R0 · 日期: 2026-09-25
> 审查对象（工作树未提交 diff，**严格限定 closure 两文件**；`git diff --numstat` 实测）: `infra/closure_chain.py`（**+631/−6**——任务申报 +637/−7 有 ±6 行出入，如实注记；新增段 L124-193 模块文档 / L307-375 常量+幂等键 / L1497-1506 resume 拒绝 / L1836-1844 finalize 拒绝 / L1888-1912 status 终态 / L1920-2369 cancel 实现与 CLI，全部逐行读取）+ `infra/tests/test_closure_chain.py`（**+679/−0 纯追加**——单 hunk @L1879 起，import 块字节不变避开 static-pin（checks/version.py:258-264 锚 L86 豁免行），申报 +677 出入注记；17 新测试 L1879-2557 全读）。工作树并行面 FIX-384（archive.py/test_archive.py）**零触碰零读取**——并行纪律遵守
> 语义基准: version-plan-0.88.0 §2 E1 行（L56——限定入口→CAS→op 登记→终态→仅释放自有锁→对账；七场景验收）+ §3b F-5④（L68——cancel locks-release × guard 消费权并发）+ rollback-plan-0.86.0 §8 #5（L158——closure 铺开：取消/重开/异常接管；本票=取消纵切，重开/接管归 FEAT-063）+ DEC-239（decision/review/evidence/ops_ledger 四族 BLOCK——DEC 行合法写入路径=writer）+ DEC-237 C1-ARCH-09（locks-release 同型先例）+ DEC-224 + FEAT-049 写入器契约 + FEAT-056 单飞披露（closure_chain.py:100-106）
> 审查方法: 逐行读 diff 与新增段全文；writer 腿契约面定点实读（governance_store.py decision-append L1260-1460/JSON 腿 L1480-1594/_build_decision_row L1232-1241/locks-release L2196-2309/_replay_payload L652；loop_event_log.py build_event L193-223/append_event L231-358 跨进程锁+单行 O_APPEND）；实测优先——四套件复跑 + 竞争/F-5④ 3× 稳定性 + 管道符纯函数探针 + 畸形 id CLI 探针 + HEAD 基线计数；**全程零 `.governance` 写入、零姿态翻转、零并行面接触**

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（P0=0 · **P1=1** · P2=1 · P3=5 · **unresolved_blockers=0**）

5 维度逐项有结论（§4）· AI 专项 5 项全过（§5）· 设计一致性 8 焦点裁定（§2）· 独立复验 8/8 通过（§3，**Developer 申报全部数字实测复现一致**：66P=49 基线〔git show 实数 49〕+17 新〔逐数 17〕/105P/99P/verify PASSED/竞争与 F-5④ 3× 复跑零 flaky）。八项 MUST 重点逐项核实（§2）：**顺序纪律论证成立**（终态事件=线性化点+意图记录，非「写后执法」——执法全部发生在终态前的零写门；两条 writer 腿是收敛腿非执法腿；CAS append 原子性=run lock per-closure 串行 × loop_event_log 跨进程锁+单行追加 × per-closure seq 连续性；中断收敛=确定性 op id + writer 指纹重放，双腿测试实证）；**DEC 腿 BLOCK 合规**（decision-append 子进程 + 幂等键跨重试字节恒定论证成立——模板字段全部来自 recorded intent）；**对账语义正确**（世界是真相：dec_in_world/locks_world_clear 进 verdict，台账仅披露——台账 ok 世界无标记 → consistent=False 响亮披露）。

**P1-1（原则上本轮修改——改动面 ≈10 行 + 2 测试，建议随本票收口）**：受限入口校验了换行但**未校验管道符 `|`**，而 DEC 行是 md 表格行——`--reason`/`--authorized-by` 携带 raw `|` 的合法自由文本输入会通过全部零写门、落终态事件后，DEC 腿被 writer 确定性拒绝（行形状 6 列≠5 列），且重试从 recorded intent 派生**字节相同** payload → **永久 pending 不可收敛**，`re-run the SAME cancel command` 重试提示对该输入类是死路（详见 F-1）。fail-closed 方向零损坏、leg detail 携带 writer 改写建议、journal 已录意图——非 P0；但破坏本票「中断恢复必收敛」验收性质，且 DEC 行无法经任何自动路径登记。

**P2-1（建议同批顺手修复，约 6 行）**：`cmd_finalize` 未捕获 `LockContention`——cancel 在 run lock 下跑两条 writer 腿（最长 ~2×(30+30)s）显著扩大了 finalize 10s 锁预算耗尽的实际触发窗，届时并发 finalize 以**裸 traceback exit 1**（空 stdout）呈现而非结构化拒绝；同时构成竞争单终态测试在慢机/锁竞争环境下的 flaky 向量（详见 F-2）。

按 SKILL 关闭表（P0=0 且 P1>0 → 有条件合并+遗留计划）：F-1 遗留条件 = 本轮修复（入口校验 + 红绿测试），F-2 建议同批；修复面均不触及本报告其余结论，Coordinator 可据改动面决定是否需 R1 复审（建议：F-1 修复后同 diff 快速复审一次——触及取消入口语义）。

---

## 2. 设计一致性（八焦点逐项裁定——对应任务 MUST 重点 1~8）

| # | 焦点 | 裁定 | 事实依据 |
|---|------|------|---------|
| ① | **顺序纪律正确性**（终态先行 ≠ 写后执法；CAS append 原子性；中断重跑收敛） | **符合** | 三层论证逐行核实：(a) **执法与写入分离**——全部受限入口门（finalized L2218-2222 / 外部步终态 L2224-2234 / undetermined L2235-2244 / CAS L2245-2252）在终态 append 之前且零写入（测试字节快照坐实）；终态事件本身不执法——它是 **CAS 线性化点 + 意图记录**（authorized_by/reason/observed_status/cancelled_at 全落 payload L2258-2269），run/finalize/resume 三路径都以它为终态判据（L1497-1506/L1836-1844/L1888）。(b) **两条腿是收敛腿非执法腿**——DEC 行与锁释放都走写入器自己的幂等管道，腿失败只 pending 不回滚终态（注释 L2282-2283 明示）。反序（腿先终态后）才会产生「DEC 行已登记而 closure 仍可 resume 完成」的自相矛盾世界——终态先行是唯一安全序。(c) **CAS append 原子性**——seq/prev_seq 从 run lock 下的新鲜 `_load_closure_events` 计算（L2197/L2256），同 closure 的全部 append（run/finalize/cancel）共享同一把 per-closure run lock（`_RunLock`，有界获取+硬拒绝 L1015-1081）；`loop_event_log.append_event` 另有跨进程 companion lock + 单次 write `"a"` 模式（O_APPEND，loop_event_log.py:231-358）——双层原子性成立，per-closure seq 单调性由 `check_cas_monotonicity` 复验（测试 L2050 断言）。(d) **中断收敛**——`cancel_operation_id` = sha256(closure_id\|slot) 确定性（L365-375）；replay 分支从 recorded intent 派生腿 payload（L2273-2281），模板字段全部来自 journal（`_CANCEL_DEC_CONTENT/_BASIS` L2049-2058 注释明示「volatile world reads live in the REPORT, never in the registered row」——volatile 读（locks world/task row inspect）确实只在报告与终态 payload，不进登记行）；writer 侧同 id 同指纹 → replay、异指纹 → operation_id_conflict（governance_store.py:1383-1392 实读）。双腿中断收敛测试（L2361-2409）+ 幂等重放零新事件/行/ops（L2331-2353）实证 |
| ② | **限定入口完备性** | **符合（两处口径缺口：F-1 P1 / F-6 P3）** | 状态完备性：派生态闭集 {cancelled, finalized, blocked, awaiting-world-check, ready, running}（L1948-1964）——两个不可变终态拒绝（cancelled 经 prior 分支收敛、finalized L2218），四个可取消态全放行，**无漏态**。undetermined 语义：dangling step_started（CLI=started/external=unknown，L1430-1431）与 step_unknown 全部拒绝（L2235-2244）——悬挂崩溃窗口的「resume 先收敛再取消」协议有测试实证（L2194-2234：拒绝→resume 收敛→取消成功）。外部步终态（completed/failed/unknown）拒绝（L2224-2234，测试 L2178-2192）。**F-1（P1）**：字符类校验只挡换行（L2345-2349），raw `\|` 漏过——见 §6。**F-6（P3）**：CANCELLABLE_STATUSES 的 awaiting-world-check 条目不可达（该派生态 ⟺ ∃unknown 步 → undetermined 门必先拒）。授权面：authorized_by+reason 必填+单行（L2338-2349，测试 L2122-2147 含换行注入拒绝）；无 journal/无 task 拒绝（L2200-2212） |
| ③ | **锁所有权安全** | **符合** | 新鲜世界读在**决策时刻**（`_read_locks_world` L1967-1992，cancel 在 lock 下 L2255 读一次入终态 payload、腿内 L2105 再读决策是否释放）；释放经 `locks-release` 写入器 **task-scoped**（mutate 只删 active_tasks[task] + locked_by==task 的 file locks，governance_store.py:2234-2240 实读）——所有权变更到其他 task 的文件锁绝不误释（测试 L2429-2450：locked_by→OTHER_TASK 后 active entry 释放、b.md 保持、终态 payload 如实记录 locks_files=[]/locks_held=True）。读后锁所有权变化竞窗：**跨 task** 由 writer apply 时刻的 locked_by 过滤封闭；**同 task 重取** 由既有单飞假设披露覆盖（L100-106——chain 不仲裁同 task 双 closure，operator 义务）。无锁跳过腿+零 ops 登记（L2111-2116，测试 L2452-2469）。agent-locks.json 不可读 → 腿 pending 不猜测（L2106-2110） |
| ④ | **DEC 腿 BLOCK 合规** | **符合** | DEC-239（2026-09-25）：decision 族 BLOCK——合法写入路径=writer。cancel 的 DEC 行经 `governance_store.py decision-append` **子进程**（L2081-2085），全仓无任何 decision-log.md 直写路径（grep 核实——测试夹具写的是种子文件非 cancel 代码路径）。幂等键跨重试字节恒定论证成立：content/basis 全部 substitution 来自 recorded intent（authorized_by/reason/observed_status/cancelled_at；`--date cancelled_at[:10]`——时间戳格式 ISO `2026-09-25T02:28:36Z` 实测，[:10] 确定性成立）；`decider/content` 单行由入口校验前置保证（换行拒绝 ↔ writer `_cells_no_newline`，governance_store.py:1237）。指纹重放/冲突语义实读核实（L1383-1392）；机器凭证标记「decision-append {op}」入行（L1233-1235）——对账 world 标记可用性成立。ops 台账登记经 writer pending→ok 管道（测试 L2060-2064 断言双 op status=ok） |
| ⑤ | **17 测试判别力** | **符合** | 清点 17 个 test 方法与申报一致。**竞争单终态=真双进程**（L2281-2324：两个 Popen 竞 cancel/finalize，断言 terminals==1 + 恰一 winner exit 0 + loser exit 2 + 终态类型↔败者 code 对应断言——不是 mock 竞争）。**F-5④=真并发**（L2479-2549：thread 跑 `wgs.consume_violations` × 主线程跑 `cancel_closure`（真实子进程腿），断言消费恰一次/单用 grant/取消双腿 done/对账 consistent/双域各恰一终态/他 task 锁完好）——与 version-plan L68 ④义务对齐。零写门全部字节快照断言（`_gov_snapshot` 排除 closure-locks/ 锁簿记——先例注释 L2008-2014）。中断恢复双腿各一测试（锁竞争注入用真实 `_TargetLock` 持有者 L2364；DEC 腿用退化空文件世界 L2390）。终态语义断言 detail 文本而非仅 exit code（L2090-2101 注释明示防假绿）。**3× 复跑稳定**（§3-5）。缺口：管道符输入类无测试（=F-1 配套缺失） |
| ⑥ | **对账语义** | **符合** | `consistent` 判定 = legs_done **∧** dec_in_world **∧** locks_world_clear（L2177-2181）——**世界是真相**：dec_in_world 读 decision-log.md 实文（L2164-2171）、locks_world_clear 读 agent-locks.json 新鲜世界（L2172-2176）；ops 台账仅披露（ledger_ops 字段）**不进 verdict**——「台账 ok 世界无标记 → 不一致披露」语义正确落实（腿 state=done 但行不在世界 → consistent=False + retry_hint，exit 3）。locks_world_clear 对 skipped_no_locks 放行正确（无锁世界=清晰）。verdict 不静默吸收：不一致必 exit 3（cmd_cancel L2565-2569） |
| ⑦ | **验证复现** | **8/8 通过（§3）** | 66P/105P/99P/verify 全部本机复跑一致；竞争+F-5④ 3× 稳定；基线计数 git show 实数 49；两探针（管道符/畸形 id）产出 F-1/F-3 直接证据 |
| ⑧ | **向后兼容** | **符合** | −6 行逐行核对全为兼容改写：空行 + closure_status 的 `if finalized:`（→ cancelled>finalized 派生链 L1888-1899，新终态纯增量）+ epilog 3 行（exit 语义扩展，文档自更新）+ handlers 字典行（加 cancel）。既有 CLI 面（run/status/finalize）参数与输出契约零变化；resume 对新终态的拒绝只对携带 closure_cancelled 事件的 closure 生效（存量 closure 无此事件→零影响）；49 基线全绿实测（66P 内含）+ verify PASSED（版本投影/manifest/adapter 契约面含）+ static-pin 豁免行锚定通过（import 块字节不变策略有效——`threading`/`gstore` 均为函数内局部导入 L2482/L2556，理由注释在场） |

---

## 3. 独立复验（8/8 通过——Reviewer 本机实跑，全程零 .governance 写入）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 目标套件 66P | `python -m pytest infra/tests/test_closure_chain.py -q` | **66 passed in 79.53s**——49 基线 + 17 新，全绿 |
| 2 | governance_store 105P | `pytest infra/tests/test_governance_store.py -q` | **105 passed in 3.56s**——申报一致 |
| 3 | triage_write_guard 99P | `pytest infra/tests/test_triage_write_guard.py -q` | **99 passed in 2.12s**——申报一致 |
| 4 | verify 全量 | `python infra/verify_workflow.py` | **PASSED, exit 0**（版本投影/manifest/六 adapter 契约面含）——申报一致 |
| 5 | 竞争+F-5④ 稳定性 | 两测试 ×3 复跑 | **3/3 全绿**（1.88~2.33s/run）——本机零 flaky |
| 6 | 基线计数 | `git show HEAD:…test_closure_chain.py` 计 `def test_` | **HEAD=49 / 工作树=66**——申报「49 基线+17 新」实数吻合 |
| 7 | 管道符探针（F-1） | 纯函数调用 `_build_decision_row`（reason 携 raw `\|`） | **StoreError: row has 6 columns, expected 5 — a raw '\|' outside an inline code span changes the shape; reword, use the full-width ｜…**——writer 确定性拒绝实锤 |
| 8 | 畸形 closure-id 探针（F-3） | CLI `cancel --closure-id bogus …` | **裸 ValueError traceback，exit 1**——结构化拒绝面缺口实锤 |

**claimed 项核对**：无——Developer 四项申报（66P/105P/99P/verify）全部独立复现。**numstat 出入如实注记**：实测 +631/−6/+679 vs 申报 +637/−7/+677（±6 行；全部计数类申报与实测吻合，出入不影响任何结论，判定为申报时点快照差异）。

---

## 4. 五维度审查结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ✅（P1×1 / P2×1） | 逐行核对：状态派生链 cancelled>finalized>blocked>awaiting-world-check>ready>running 与 status/derived 双面一致（L1888-1899 vs L1948-1964）；replay 分支跳过入口门正确（终态已立，CAS 仅入口语义）；expected_status 校验在 undetermined 门之后（优先级正确——不可取消态优先于 CAS 口径）；`_run_writer_cli` 超时→UNKNOWN→retryable 语义与 contracts m0-r1 执行结果三态一致（L2019-2032）；exit 码量表（0/2/3）epilog 自文档化且测试覆盖三态。缺陷：F-1（入口字符类缺口→腿永久 pending）、F-2（finalize 竞争面裸 traceback） |
| 安全性 | ✅ | 零注入面（argv list 无 shell；`_run_subprocess` 全 list argv）；全部拒绝 fail-closed 零写入（字节快照测试坐实）；授权者+原因强制+单行约束（换行注入拒绝有测试）；写后执法边界如实（终态先行≠写后执法的论证见 §2①——执法门全在写入前）；EVD append-only 保留+任务行只披露不修改（`_inspect_task_row` 只读 inspect 子进程 L1995-2016）；他 task 锁零触碰有测试；信任模型与全仓写入器一致（本地 CLI 记录 WHO/WHY 无密码学强制——DEC 腿经 writer 与全仓同模型）。残余：F-1（输入校验缺口，fail-closed 方向） |
| 可维护性 | ✅（P3×4） | 模块文档新增段与实现逐点对应（六点契约+顺序纪律+F-5④ 义务——L124-193）；确定性幂等键与 slot 白名单单源（L314-317/L371-374）；腿状态机词汇闭集（pending/done/done_replayed/skipped_no_locks）；locks 家族 replayed=True 家族约定差异以代码注释显式披露（L2128-2137——Developer 边缘披露与代码一致）。注释精度四小项：F-4（对账 docstring/journal_terminal 夸大）、F-5（「fresh args disclosed」未实现于 payload）、F-6（不可达集合条目）+ 观察 C（F-5④ docstring「shared lock discipline」措辞比测试证明面宽——实际是同纪律不同锁目标，各自内部串行） |
| 性能 | ✅ | 有界锁预算（run lock 10s 默认、writer 锁 30s、子进程 60s 上限）；单遍世界读无循环 I/O；对账读三个小文件各一次；无 N+1/O(n²) 新增。权衡如实：cancel 在 run lock 下执行两条 writer 子进程（线性化代价——使 F-2 的 finalize 竞争窗实际化），属设计内串行化而非缺陷 |
| 测试覆盖 | ✅（1 缺口=F-1 配套） | 17 新测试覆盖七场景全数（正常+对账/幂等重放/竞争单终态/中断恢复×2/锁所有权×3/未授权零变化/外部副作用拒绝）+ CAS + 终态语义 + 在途写冲突 + 未知 closure + F-5④ 组合；零写断言用字节快照、终态语义断言用 detail 文本、竞争用真双进程、组合用真线程×子进程；红线（resume/finalize/status 对 cancelled 的行为）各有着落。缺口：`--reason`/`--authorized-by` 字符类（管道符）无红绿测试（F-1） |

---

## 5. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 证据 |
|---|--------|------|------|
| 1 | mock 残留 | **通过** | grep `mock\|Mock\|patch\(` 两文件 **0 命中**——全部真实子进程/真实文件/真实锁竞争注入 |
| 2 | 硬编码返回值 | **通过** | 无；全部行为经真实 writer CLI/真实 journal/真实世界读（闭环路径 66P 全绿即活体证明） |
| 3 | 幻觉 API 调用 | **通过** | 逐个核实存在性：`loop_event_log.build_event/append_event/check_cas_monotonicity`、`governance_store decision-append`（--decider/--content/--basis/--date/--operation-id/--timeout 全部在 parser 注册）、`locks-release`（--task/--operation-id/--timeout）、`task_row_update --inspect`、`wgs.build_detection/record_detections/ensure_grant/consume_violations`——全部被通过中的测试活体调用 |
| 4 | 未实现 TODO | **通过** | grep `TODO\|FIXME\|XXX\|NotImplemented` closure_chain.py **0 命中**（测试文件同 0） |
| 5 | 过度实现 | **通过** | 切片边界克制：不接引擎 dispatch（standalone CLI 维持 L63-65 姿态）、不回滚任务行（披露式终态，replay 留给独立治理决策 L156-162）、不触碰 violations 台账（F-5④ 消费权独占保持——测试断言 consumer=CLI）、不动既有链条语义；与 FEAT-056/060 同类切片体量相称 |

---

## 6. 发现清单（P1×1 / P2×1 / P3×5——每条附文件:行号+证据+修复建议）

### F-1（P1 · 关键）受限入口未拒绝管道符 → DEC 腿永久 pending 不可收敛，重试提示死路

- **位置**: closure_chain.py:2338-2349（入口校验仅 `strip()` 非空 + 换行拒绝）；:2049-2053/:2076-2080（reason/authorized_by 拼入 DEC content/basis 模板）；:2270-2281（replay 从 recorded intent 派生**字节相同** payload）；:2164-2171/:2177-2181（dec_in_world 恒 False → consistent 恒 False）；:2565-2569（恒 exit 3）；governance_store.py:1232-1241（`_build_decision_row` → `_validate_row_shape` 5 列强制）
- **证据**（实测探针，§3-7）：reason 携 raw `|` → writer `StoreError: row has 6 columns, expected 5 — a raw '|' outside an inline code span changes the shape; reword, use the full-width ｜, or wrap the segment in backticks`。全链推演：合法输入通过全部零写门 → 终态事件落（不可变）→ DEC 腿拒 → pending → 重试 payload 确定性相同 → 同拒 → **永不收敛**；「re-run the SAME cancel command」重试提示（:2187-2191）对该输入类为死路。
- **影响**: 该 closure 的 DEC 行无法经任何自动路径登记（授权审计降级为 journal-only；手工补录 DEC 行用其他 op id 也无法让本票对账转绿——dec_in_world 匹配的是 cancel 自身 op id）；对账永挂 inconsistent + exit 3 噪声。缓解面（为什么不是 P0）：fail-closed 零损坏；意图已完整落 journal（审计不丢失）；leg detail 携带 writer 改写建议（操作者有行动信息）；触发需自由文本含 `|`（`--reason "A | B"` 形态现实中 plausible）。
- **修复建议**: 受限入口对 authorized_by/reason 增加 raw `|` 拒绝（与换行同款 `schema_violation` 零写拒绝；writer 错误消息的「全角 ｜ 或 backtick 包裹」是模板侧备选），附一红一绿测试（红=拒绝零写、绿=全角不受影响）。

### F-2（P2 · 建议）`cmd_finalize` 未捕获 `LockContention` —— cancel 持锁腿窗内并发 finalize 裸 traceback exit 1，竞争测试 flaky 向量

- **位置**: closure_chain.py:2547-2552（cmd_finalize 无 try/except）；:1821（finalize_closure `_RunLock(lock_path, 10.0)`）；:2284-2288（cancel 在 run lock 下跑两条 writer 腿——每腿子进程超时 `writer_timeout+30`=60s、writer 锁超时 30s）；:2363-2369（cancel_closure 捕获 LockContention——对照）；:2520-2522（cmd_run 捕获——对照）；:2300-2317（竞争测试断言 loser exit 2 + JSON stdout）
- **证据**: 代码路径推演（finalize 10s 预算 < cancel 腿最长持锁 ~120s）+ 既有对照面（run/cancel 均有结构化捕获，finalize 独缺）；本机 3× 复跑未触发（腿实耗 ~1s——窗口存在但需慢机/锁竞争）。
- **影响**: 结构化拒绝契约在该竞争面破坏（exit 1 + traceback + 空 stdout，调用方无法按 code/disposition 分支）；竞争单终态测试在慢环境可能以 JSONDecodeError 失败（非产品终态错误——终态恰一性由 run lock 保证不受影响，仅败者呈现形态）。注：finalize 缺口系 FEAT-056 既有，FEAT-062 的 under-lock 腿首次使其现实化。
- **修复建议**: cmd_finalize 捕获 LockContention → `{error: true, code: "lock_contention", disposition: "retryable"}` + exit 3（与 cancel/run 同款），可加一条 contention 注入测试。

### F-3（P3 · 建议）`cmd_cancel` 缺 ValueError 包装 —— 畸形 closure-id 裸 traceback exit 1

- **位置**: closure_chain.py:2555-2561（cmd_cancel 无 try/except）；:2337（require_closure_id 抛 ValueError）；对照 cmd_run:2514-2525 / cmd_status:2538-2542 均有包装
- **证据**: 实测探针（§3-8）：`cancel --closure-id bogus` → ValueError traceback，exit 1。
- **影响**: CLI 面结构化词汇（schema_violation/exit 2）对该输入类不可达；cmd_finalize 同病（既有，:1813 抛点）。轻量一致性问题。
- **修复建议**: cmd_cancel（及顺手 cmd_finalize）加同款 try/except ValueError → schema_violation 结构化拒绝。

### F-4（P3）`_cancel_reconciliation` docstring 与 `journal_terminal` 字段夸大

- **位置**: closure_chain.py:2145-2148（docstring「re-read the journal terminal」）；:2182（`"journal_terminal": True` 硬编码）；对照 :2290（journal 重读发生在 _cancel_locked，但不进对账 verdict）
- **影响**: 报告字段声称的对账输入之一（journal 终态在场）并未实测——若腿后 journal 损坏移除终态行，报告仍称 True。语义透明度小缺口，无行为危害。
- **修复建议**: 将 events 传入对账并实测终态在场（一行 `any(...)`），或改字段语义/docstring 为「terminal asserted by control flow」。

### F-5（P3）模块 docstring「fresh CLI args are disclosed」未实现于 replay 报告

- **位置**: closure_chain.py:182-184（docstring 声称 disclosed）；:2273-2281/:2297-2320（replay 分支直接丢弃 fresh args，payload 无任何披露位）
- **证据**: 测试 L2342-2346 证实「first authorization stands」（recorded intent 生效）——正确；但「disclosed」半句无实现对应。
- **修复建议**: 措辞收敛为「ignored, never re-recorded」，或 payload 增加 `discarded_args` 披露位（低成本高透明）。

### F-6（P3）CANCELLABLE_STATUSES 的 awaiting-world-check 条目不可达

- **位置**: closure_chain.py:307-308（集合含 awaiting-world-check）；:1960-1961（该派生态 ⟺ ∃unknown 步）；:2235-2244（undetermined 门必先拒）；:2462-2463（--expect-status choices 含它）
- **影响**: 集合承诺与实际可达性不符（该状态下取消必被 undetermined 门拒绝）——口径精度问题，无行为缺陷（拒绝方向正确且更保守）。
- **修复建议**: docstring 注记「reachable only in derived states without undetermined steps」，或从集合移除（行为不变性由 undetermined 门保证）。

### F-7（P3 · 潜伏耦合登记——触发条件明确）dec_in_world 世界标记耦合 md backend；FEAT-061 json cutover 后投影失败窗永不 consistent

- **位置**: closure_chain.py:2164-2171（dec_in_world 读 decision-log.md 找 `decision-append <op>`）；:2087-2089（DEC 腿仅取 code/detail/replayed——**丢弃 writer payload 的 projection_status**）；governance_store.py:1274-1276（absent authority marker = md world）+ :1503-1509（json 腿投影失败=已提交投影待修复，exit 0）
- **当前事实**（实测）: `.governance/` 无 decision 权威标记、无 decision-store JSON——**md backend 活跃，本发现今日不触发**；md 行携带凭证标记（governance_store.py:1233-1235）→ 标记匹配有效。
- **触发条件**: FEAT-061 cutover 激活 json backend 后——权威成功/投影失败窗内 DEC 行已 committed 但 md 缺行 → legs done + dec_in_world=False → **永不 consistent**（重试只重放不修投影；retry_hint 误导）。fail-safe 方向（不产生错误 verdict，只产生永久 exit 3）。
- **修复建议**: 登记 FEAT-061 cutover 票验收项——cancel 对账面切权威 store 读取或消费 projection_status；激活前无需改动。

---

## 7. 非阻塞观察（不计发现）

- **A（§8#5 清偿口径）**: rollback-plan-0.86.0 §8 #5 全项 =「取消/重开/异常接管」——本票清偿其取消纵切，重开/接管归 FEAT-063（plan-tracker L112 E2）。任务上下文「rollback §8#5 清偿」按首半理解成立，建议任务收尾注记按部分清偿表述。
- **B（numstat 出入）**: 实测 +631/−6/+679 vs 任务申报 +637/−7/+677——判定为申报时点快照差异；计数类申报（66/49/17/105/99）全部实测吻合。
- **C（F-5④ docstring 措辞）**: closure_chain.py:191-192「both writers serialize through the shared governance-store lock discipline」——实测两 writer 锁的是**不同**目标（agent-locks.json vs guard ledger/state），各自内部串行；测试证明的是并发安全+双域各恰一终态，非同锁串行。措辞可比照收敛。
- **D（任务行终态语义）**: version-plan E1 行「DEC/EVD/任务终态」——实现口径为 DEC 行登记 + EVD append-only 保留 + **任务行只披露不修改**（replay 是独立治理决策，出最小切片；模块文档 L156-162 显式披露）。判定为实现对计划措辞的合法最小切片诠释且已如实披露，与七场景验收无冲突；留 Coordinator 在任务收尾时确认口径。
- **E（执行包）**: `.governance/execution-packets.json` 现有 FEAT-060/061/064/REL-086——FEAT-062 无包（P2 非 Check 18c 强制面，合规；如 Coordinator 认为需要可补）。

---

## 8. 复审指引（R1 若因 F-1 修复触发）

1. 逐条比对本轮 F-1~F-7：F-1 修复 = 入口新增管道符拒绝 + 红绿测试（标注「已修复」并复跑探针形态用例）；F-2 若同批修复 = cmd_finalize 捕获 + 竞争测试仍绿。
2. 复跑面：test_closure_chain.py 全套（≥66P）+ verify PASSED；static-pin L86 锚仍绿（改动在文件尾部追加区则锚不动）。
3. 终态判据不变：仅 APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES 为通过。
