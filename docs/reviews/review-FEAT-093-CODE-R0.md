# Code Review FEAT-093 — R0（权威账本与身份契约·产品代码变更独立审查）

- **Task**: FEAT-093（P1，0.98.0「可信有界执行内核」首票，DEC-330）
- **Reviewer**: Code Reviewer Agent（独立复审，非自审）
- **Round**: R0（首轮）
- **日期**: 2026-10-10
- **审查对象**: 工作区未 commit 变更（git diff 9 文件 + untracked 2 本票文件；HEAD=c783cff）
- **审查依据**: `.governance/plan-tracker.md` L83 任务行 + `.governance/execution-packets.json` packets.FEAT-093（goal/scope_guard/quality_budget 六维/vertical_slice/interruption_policy 实读）+ 11 文件 diff 全量逐行实读 + 三硬门槛本机复现 + 仓库外临时目录行为探针

---

## 一、结论

**NEEDS_CHANGE**（P0=0，P1=1 未解决 → unresolved_blockers=1）

核心交付（追加事件日志+哈希链+撕裂尾 fail-closed、身份契约拒绝+审计、迁移 dry-run 先行零丢失、投影重建计数对照、开关渐进默认 off、单源解析口径、纯派发接线）**架构与实现质量高，验收①~⑤主体成立，三硬门槛全部本机复现通过**。但事务写入器在**批内（intra-batch）身份契约存在实证缺口**：单批两条同 ID 不同锚的 `task_registered` 被整体接受且零审计拒绝事件——这与模块 docstring、references 文档「批内事件全部先验证（含身份契约）」的成文契约直接矛盾，属本票核心不变量（同 ID 双语义结构性不可能）在公开事务面上的漏洞。修复面小且局部，修后进入 R1 复审。

> 循环角色：本审查对应 Inner loop `loop-exit-gate`（NEEDS_CHANGE 非终态，Coordinator 须返工后发起 R1 复审——behavior-protocol M7.4）。

---

## 二、发现列表（P0~P3，全部附文件行号+一手证据）

### P1-1（阻断）：`transact` 批内身份契约缺口——同 ID 双锚可在单事务内静默换义

- **位置**: `skills/software-project-governance/infra/authority_ledger.py` L565-577（`transact` 的身份预检）、L616-628（`_check_identity` 只查 `self.state`——批前折叠态）
- **事实依据（本机探针复现，临时目录，仓库零触碰）**:
  ```text
  PROBE1 status: recorded                      ← 批被整体接受
  PROBE1 events: ['task_registered', 'task_registered']
  PROBE1 identity_conflict_rejected count: 0   ← 零审计拒绝事件
  PROBE1 folded anchor: 锚B                    ← 折叠态静默最后写入胜出
  ```
  探针代码：构造 `LedgerWriter.transact([("task_registered",{task_id:"FEAT-900",anchor:"锚A",...}),("task_registered",{task_id:"FEAT-900",anchor:"锚B",...})])` 单批两事件同 ID 不同指纹。
- **问题**: 身份预检循环 `for kind, payload in batch: if kind == "task_registered": self._check_identity(payload)` 只对**批前**折叠态校验；批内第二条注册看不到批内第一条。后果：(a) 双语义换义在单事务内被接受且**无** `identity_conflict_rejected` 审计（尝试不留痕）；(b) `fold_state`（L375-389）对重复 `task_registered` 最后写入胜出，静默覆盖锚。同族缺口：`supersede_task` 的 new-id 唯一性检查（L735）同样只对批前态，raw `transact` 可完全绕过。
- **成文契约被证伪**: 模块 docstring L500-503「a batch of events is validated ENTIRELY against the closed schema **and the identity contract** BEFORE any byte is appended」；references/authority-ledger.md L35「批内事件全部先验证（闭合 kind + 必填字段 + **身份契约**）再一次性顺序追加」。
- **影响评估**: 当前已装调用面（`record_task`/`supersede_task`/`record_event`/`migrate`）均为单事件批，**今日无触发路径**；但 `transact` 是文档化公开入口（模块 docstring L51-59「Public entry points: LedgerWriter — the transactional writer」），FEAT-094/096 将在其上组合批事务——本票要关闭的失效形态（同 ID 静默换义）恰在该面复活。
- **修复建议**: 批内模拟折叠（对 batch 先应用到一个 fold 视图再校验全部 `task_registered` 的锚一致性与 `task_superseded` 的 new-id 唯一性），或将批内身份检查改为成对校验（同批同 ID 必须同指纹）；补一条红测：同批双注册不同锚 → 整批拒绝 + 审计事件。

### P2-1：未注册身份的状态事件被接受后遭折叠态静默丢弃（无写入时信号）

- **位置**: `authority_ledger.py` L696-709（`record_task_state_change` 不校验 task_id 已注册）、L390-396（fold 对未知 id 的 `task_state_changed` 静默跳过）
- **事实依据（探针）**: `record_task_state_change("FEAT-999", ...)` → `status: recorded`，事件落日志；`FEAT-999 in folded tasks: False`——投影静默丢该事实。
- **影响**: 开关 on 但未先 `migrate --write` 播种（references L47 的采用顺序仅为文档约定，钩子不强制）时，双写镜像全部成为孤儿事件：写入「成功」披露、投影零反映，只能靠 rebuild drift 面事后发现。写入器对未知身份应拒绝（或显式审计分类），而非接受后静默丢。
- **建议**: writer 面校验 task_id 已注册（fail-closed 拒绝并留审计），或在文档+drift 面明示该孤儿类别的对账路径。

### P2-2：`supersede_task` 接受未注册 old_task_id（幻影替代关系）

- **位置**: `authority_ledger.py` L711-740（只校验 new id 未注册，不校验 old id 已注册）；fold L397-402 对未注册 old 不落 `superseded_by`
- **事实依据（探针）**: `supersede_task("FEAT-777","FEAT-888",...)` → `status: superseded`，`FEAT-777 in folded tasks: False`——替代关系引用不存在的旧身份，血统断裂。
- **建议**: old id 必须已注册（身份血统完整性），拒绝幻影 supersede。

### P3-1：开关非法值语义——文档「落下一臂/fall through」与代码（立即返回 invalid，不落臂）不符

- **位置**: 代码 L783-794（invalid → 立即 return，不咨询 plan-tracker）vs docstring L774-777「the next arm decides」、references L45「并落下一臂」、测试注释「fall through (fail-closed to OFF)」。
- **判定**: 可观测行为安全（`switch_enabled` L816-819 将 invalid 投影为 off，测试 L25407-25411 断言通过）——但三处文档措辞与实现矛盾。修文档（或实现真落臂，二选一，保持一致）。

### P3-2：「默认 off 旧路径逐字节不变」措辞精度——CLI stdout 成功载荷新增 `authority_ledger` 键

- **位置**: `task_row_update.py` L2334-2340/L2398-2404（成功且非 replay 时 `result_face["authority_ledger"]={"status":"off"}`）。
- **判定**: 行写入文件字节不变 ✓、失败路径不增键 ✓；但 stdout JSON 载荷在成功路径多一个披露键（references L47 已记载该 face，属已披露的加性漂移）。建议 references 明说「off 时载荷仍含 `authority_ledger: {"status":"off"}`」以免机器消费方对照字节级快照时误判。

### P3-3：dry-run 演练固定针对空账本——再迁移场景的 dry-run 计数保真度

- **位置**: `authority_ledger.py` L1046-1075（dry-run 在空临时账本上跑全量注册序列）。
- **判定**: 首次迁移的 dry-run 保真 ✓；对**已播种账本的再迁移**，dry-run 会把幂等重复行仍计为 registered（live 实跑则计 duplicate）——dry-run 报告不再预测 live 行为。零丢失证明语义仍成立（对空账本）。备注级：可选用 live 账本副本播种 temp 演练。

### P3-4：哈希链「内容改写」分支已实现未测试

- **位置**: `authority_ledger.py` L297-301（hash mismatch 分支）；测试只覆盖撕裂尾（L25210-25225 torn tail）。建议补篡改测试：改写中行内容 → 加载报 integrity 破损 + 拒绝追加。
- **附带备注**: 无密钥哈希链无法检测「整尾重算哈希的全程改写」——同信任域内的已知边界，FEAT-094 的 commit SHA 锚定是该缓解的规划落点（另票）。

### P3-5：迁移遇不可提取锚的行时以未捕获异常中止（局部迁移状态）

- **位置**: `authority_ledger.py` L1016-1019（`# pragma: no cover` 的 `raise LedgerError`）；`record_task` 对空锚返回 schema_violation refused → `_register_all` 直接 raise，CLI 栈回溯。
- **判定**: 响亮不静默（fail-closed 方向正确）且可幂等续跑；但半程迁移+traceback 不如结构化 FAIL 报告。建议 migrate 捕获后返回 `{"status":"FAIL","code":"schema_violation_row",...}`。

### P3-6：plan-tracker 开关键解析未做节作用域限定

- **位置**: `authority_ledger.py` L796-812（全文扫描 `- **authority_ledger**: x`）vs Gate 解析有节作用域（L825-840）。plan-tracker 任意位置出现该形态行（如引文/代码块）都会翻转开关。建议同 Gate 口径限定 `## 项目配置` 节。

### P3-7：锚口径假设首个粗体段=声明标题

- **位置**: `authority_ledger.py` L198-200。畸形「事项」格（标题前另有粗体段，如行内重复优先级标记）会取错锚→跨任务锚碰撞→误拒。现行 plan-tracker 格式使其不可能出现；备注防退化。

### P3-8：每次事务后全量重折叠（O(n)/写，迁移累计 O(n²)）

- **位置**: `authority_ledger.py` L598。预算内实测达标（31 任务重建 <2s、单事务 <50ms，测试守护 L25468-25492）；规模增长时再议（增量折叠）。

### P3-9：Developer 声称与实际不一致（如实指出）

- 「authority_ledger.py 1249 行」→ **实际 1400 物理行**（`Get-Content | Measure` 复核）。其余声称全部核实准确：verify_workflow +23 行纯派发 ✓、2 类 14 新测试 ✓、FROZEN 99→100 + rider ✓、205→206 ✓、27934→27957 ✓、handler 96→97 ✓、`Ran 1075 OK` ✓（本机复现逐字一致）。

### 未构成发现的核实项（审查重点逐面）

1. **锚误伤（重点①）**: 合法演化不误伤——状态装饰在「状态」列不进锚；追加叙述被 `——` 截断排除（测试 L25175-25185 实证 `already_registered` 幂等）；空白不敏感指纹吸收排版微调。标题本身修改=换语义被拒→supersede 唯一正道，属设计意图且文档明示。换锚拒绝后旧 ID 身份冻结闭环 ✓（测试 L25187-25203：supersede 后旧 ID 换义仍拒、旧锚幂等重注册为 no-op、无理由 supersede 被拒）。
2. **绕过写入器（重点②）**: 直接写文件可物理绕过（任何文件皆然），但哈希链使任意改写在下次加载被检（L297-301），撕裂尾 fail-closed 拒追加（测试实证）；并发双写→链断→下次加载拒绝（docstring L508-512 披露，跨进程隔离=FEAT-096 边界）。无密钥链对全程重算改写的边界见 P3-4 备注。
3. **审计不可绕过面**: `record_task` 拒绝路径必留 `identity_conflict_rejected`（测试断言恰好 1 条新事件+重载后仍在）；迁移期历史双语义 flag 一次并幂等（`conflict_keys` 去重 L461-470）✓。

---

## 三、验收对照（L83 验收①~⑤）

| # | 验收项 | 判定 | 依据 |
|---|--------|------|------|
| ① | 权威账本 schema+事务写入器（含审计日志） | **成立（附 P1-1 但书）** | `EVENT_KINDS` 17 种闭合词汇+`REQUIRED_FIELDS` 必填集（L98-141）；`transact` 验证原子性+单次顺序追加+fsync+快照原子刷新（L565-612）；审计族 4 种。批内身份验证缺口见 P1-1 |
| ② | plan-tracker 热区改为投影 | **成立（渐进形态）** | `rebuild_projection` 折叠态↔现行热区逐项计数对照+drift 三类披露面（L1155-1242）；物化投影=快照；执行包 assumption_record 明载「写路径先双写后读切换」，读切换后置属契约内 |
| ③ | 同 ID 双语义写入侧被拒 | **成立（record_task 面）/缺口（transact 面）** | 拒绝+审计+整批不落业务事件（测试 L25135-25170）；supersede 唯一正道+旧 ID 冻结（L25187-25203）。批内缺口=P1-1 |
| ④ | 历史数据迁移零丢失 | **成立** | dry-run 默认先行、零字节落盘（L25422-25430：`wrote.events=0`+无 authority-ledger 目录）；temp 副本全序列演练；计数逐 facet 对照含 rows/id_set（L1131-1149）；历史双语义行 flagged 保留不静默漂白（L25432-25465）；重跑幂等（L25467-25481）。保真度备注=P3-3 |
| ⑤ | 全套件回归零退化 | **成立（本机复现）** | `Ran 1075 tests in 364.504s / OK / exit 0`（含 14 新测试）；check-governance `[PASS]` |

## 四、硬门槛复现结果（一手命令输出）

| 门槛 | 命令 | 本机结果 | 判定 |
|------|------|---------|------|
| ① | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py` | `Ran 1075 tests in 364.504s` `OK` exit 0 | ✅ 与声称逐字一致 |
| ② | `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only` | `Governance: [PASS]` exit 0 | ✅ |
| ③ | `python ... verify_workflow.py check-architecture-health` | `4 ERROR, 33 WARN (advisory)` exit 0；**零新增**：authority_ledger.py（1400 行<2000 warn 阈值）与 mirror 函数均不在告警列表；task_row_update 2485 行 WARN 为预存（改前 2409 已超 2000）；4 ERROR 均为 ratchet 管理的预存面（verify_workflow 27957=新锚、_run_full_engine_checks/main 等） | ✅ 零新增告警成立 |
| 附加 | `verify_workflow.py authority-ledger status --text`（派发冒烟） | `[INFO] authority-ledger/1`，switch off/default，integrity ok，live .governance **零账本文件**（实数据未污染、默认 off 实证） | ✅ |
| 附加 | 行为探针（%TEMP% 临时目录，仓库零触碰） | P1-1/P2-1/P2-2 三缺口实证（见发现列表） | ⚠️ |

## 五、修改纯粹性核验（D4）

- **11 文件全在 scope_guard 内**：新模块+references 文档；verify_workflow +23 行纯派发（import 块+subparser+dispatch 行，无 handler 逻辑）；registry 白名单+_COMMANDS 各一处；task_row_update 双写钩子单函数+两调用点；4 测试文件；2 快照 sanctioned regen。无顺带重构、无版本 bump、无 FEAT-094/095/096 越界（review/recheck/goal 事件 kind 为 schema 级覆盖，L83 goal 行明载「审查结论/复审义务/goal 预算」属本票范围，非过度实现；深度绑定显式另票）。
- **frozen count rider 如实披露**：99→100（test_contract_matrix/test_registry 注释含归因）、205→206、27934→27957（archguard 注释逐块归因：+6/+12/+3+注释=+23，与 diff 逐行吻合）；handler 96→97；**预存漂移吸收 `result_shapes deferred_observation.skip_kind str→NoneType` 已按 FIX-438 先例作为 make-up rider 明示**（归因 AUDIT-159 会话治理行）——披露合格，随票吸收符合仓库既有惯例。
- **非本票 untracked**：`docs/research/feat-095-harness-enforcement-capability-2026-10-10.md`（FEAT-095 调研产物）未混入本票 diff，边界干净。
- **快照 git_head=c783cff 与当前 HEAD 一致**；regen 时工作区含本票变更属 sanctioned regen 标准形态。

## 六、测试覆盖评估

- **14 新测试（2 类）逐条核实**，覆盖映射：①= kinds/schema/txn 原子性 2 条；③= 拒绝+审计/幂等/supersede 正道 3 条；④= dry-run 零写/零丢失计数/重跑幂等 3 条；②= 重建计数一致+drift 诚实 FAIL 2 条；开关三臂+非法值 1 条；双写钩子 off/on 1 条；性能预算（<2s/<50ms）1 条。验收①~⑤全部有测试面。
- **红绿方法论有效性**：测试锚定新模块存在性（RED=模块缺失即红），门函数内在；「RED phase evidence」注释为方法叙事，历史 RED 运行不可独立复核——本轮以行为探针补足了等价的独立红面证据（P1-1 探针即「未关闭门的红」）。
- **缺口**：P1-1 批内双注册无测试（洞本身）；P3-4 内容改写分支无测试；P2-1/P2-2 未知身份路径无测试。
- **测试质量**：fixture 含同 ID 双语义行（迁移真实形态）；双写测试用 FEAT-094 锚避开 fixture 歧义并注释了原因——诚实且可读。

## 七、五维度+AI 专项结论（code-review SKILL 硬门槛）

| 维度 | 结论 |
|------|------|
| 正确性 | 主体正确；P1-1（批内身份）/P2-1/P2-2（未知身份 laxity）三处实证缺口；边界（空锚/撕裂尾/非法 kind）处理到位 |
| 安全性 | 无硬编码密钥、无注入面（无 shell/SQL）；UTF-8+fsync+同目录原子替换；fail-closed（完整性破损拒写、非法开关值→off）；审计留痕不可静默 |
| 可维护性 | 闭合词汇+必填 schema 可 grep（锚点入 references）；单源口径 live 导入反漂移（`_iter_positional_tables`/`_gate_bucket`/`_resolve_risk_status` 经 grep 实证存在于 bootstrap_aggregate L289/L389/L557）；注释质量高、归因诚实 |
| 性能 | 预算内（实测守护用例）；P3-8 全量重折叠备注 |
| 测试覆盖 | 14 测试覆盖验收全面部；上述三缺口待补 |
| AI 专项 5 项 | mock 残留=无（mock.patch 上下文管理器规范使用）；硬编码返回=无；幻觉 API=无（peer-leaf 导入实证存在）；未实现 TODO=无（FEAT-094/095/096 为显式边界非桩）；过度实现=无（schema 级事件族在 L83 goal 明文范围内） |

## 八、给 Developer 的返工清单（R1 复审对象）

1. **[P1-1] 修 `transact` 批内身份校验**（批内模拟折叠或成对指纹校验；覆盖 `task_superseded` new-id 唯一性）+ 补红测（同批同 ID 双锚→整批拒+审计）。
2. **[P2-1] 未注册 id 的状态事件**：writer 面拒绝或显式审计分类（+测试）。
3. **[P2-2] `supersede_task` 校验 old id 已注册**（+测试）。
4. P3 各项可随票顺手修（文档措辞 P3-1/P3-2 优先，成本最低），不阻断。

—— R1 复审将逐条比对上述清单标注「已修复/未修复/新引入」。

*审查过程零仓库写操作（唯一写面=本报告）；探针仅在 %TEMP%，已清理。*
