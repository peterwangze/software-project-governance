# Code Review — FEAT-044 subagent 回合预算与收尾心跳（R0）

- **Round**: R0（首轮）
- **任务**: FEAT-044（P2，0.88.0 阶段 E3——FIX-357/359 等待税缩减）
- **审查对象**: 工作树未 commit diff，纯增量三文件（并行面 closure_chain/archive/verify_workflow 严格排除）
  1. `skills/software-project-governance/infra/loop_engine.py`（+426，diff stat 实测）
  2. `skills/software-project-governance/infra/loop_telemetry.py`（+262）
  3. `skills/software-project-governance/infra/tests/test_loop_telemetry.py`（+428，33 测试）
- **审查依据**: 逐行 diff + 全文上下文 + 独立测试复跑 + 17 项独立边界探针（脚本位于 `%TEMP%`，零仓库写入）+ grep 机械检查
- **总结论**: **APPROVED_WITH_NOTES**（P0=0，P1=0，P2=2 不阻塞，P3=5）· **unresolved_blockers=0**

---

## 1. 验证复现（审查方独立执行，非转抄申报）

| # | 验证项 | Developer 申报 | 审查实测 | 裁决 |
|---|--------|---------------|---------|------|
| V1 | `test_loop_telemetry.py` 全文件 | 62P | **62 passed**（0.18s；33 新增 + 29 既有） | ✅ 吻合 |
| V2 | 新增测试计数 | 33 | **10+6+5+9+3 = 33**（类行号：RoundBudgetParametrization L839 / HeartbeatReport L979 / InterruptRecovery L1034 / StallReportTelemetry L1080 / CrossModuleConsistency L1190） | ✅ 吻合 |
| V3 | loop 族 | 283P | 核心七文件（engine_round/telemetry/health/paro/event_log/registry/rollup）= **233 passed**；`-k loop` 全量 = **488 passed / 1 failed**（唯一失败 `test_loop_runtime_claims.py::test_real_repository_inventory_complete_and_within_budget`，Finding 全部指向 `test_closure_chain.py`——并行面文件，**零指向 FEAT-044 三文件**）。**283P 口径未对上任何实测组合** | ⚠️ 见 F-5 |
| V4 | `verify_workflow.py` | PASSED | **== Verification Result: PASSED ==**（含 5 适配器 runtime-verified + FACTS 同步） | ✅ 吻合 |
| V5 | 全量 | 4080P/21F | 未复跑全量（范围外，抽查归因代替——见 §5 重点 8）；V3 中可复现失败归因并行面/HEAD 遗留，零归因 FEAT-044 | ◑ 抽查代跑 |
| V6 | manifest | 1017 | `core/manifest.json` = 949 行 / 149 product entries；cleanup canonical 展开 = **14154 文件**；全仓 grep 无「manifest 1017」关联（.py 零命中） | ❌ 不可复核，见 F-5 |
| V7 | archguard | 6F 脏树棘轮 R7 自证 | **6 failed / 32 passed** 复现（R1+R4×3+R7+CliGate）；但归因修正——见 F-6 | ◑ 数量吻合/归因修正 |
| V8 | 纯度机械检查 | 同 FX-189 纪律 | loop_engine 新增段 grep `datetime.now\|time.time\|random\|open(\|print(\|input(\|write_text\|os.environ` = **零命中**；loop_telemetry 命中均为既有 `__main__` 冒烟块（L1106-1111）与「no datetime.now()」声明性注释 | ✅ 吻合 |
| V9 | import 耦合 | archive 零 import 耦合 | loop_engine 顶层 import 仅 `json/re/dataclass/Path`（L95-98）；loop_telemetry 仅 `dataclass/datetime`（L81-82）；`importlib\|__import__` 零命中（静态+动态均无耦合） | ✅ 吻合 |
| V10 | 独立边界探针 | —（审查方自建） | **17/17 PASS**（`%TEMP%\feat044_r0_probes.py`，只读调用产品函数） | ✅ 全部语义证实 |

---

## 2. 五维度审查结论

### 维度 1：正确性 — ✅ 通过（1 条 P2 语义建议）

- **三层参数化优先序**（重点 2）：`resolve_round_budget`（loop_engine.py L630-688）defaults → registry fuse 可选 `round_budget` → overrides，`merged.update` 顺序保证优先序；registry 读取委托既有 `get_fuse`（L179，fail-closed 返回 None → issue line L663-667），`tier=None` 跳过 registry 层。逐键 fail-closed 由 `_validate_budget_patch`（L592-627）实现：非法值保默认 + issue、**never raise**。实测（正式测试 + 探针 probe2/2b/2c/2d/2e）：registry 层非法值保默认、合法键照常生效、issue 带 `registry FUSE-xxx` 标签、未知键 ignored、部分覆盖跨层叠加正确。**优先序与逐键 fail-closed 全部证实**。
- **_usable_int 排除 bool**（L587-589）：`isinstance(True, int)` 陷阱被显式防御，`heartbeat_should_fire(budget, True)` → False（测试 L1024 钉住）。
- **stall 轮次判定**：闭区间 `start <= a <= end`（含端点，测试 `test_gate_result_on_anchor_boundary` 钉住 FEAT-006 同 CAS 写语义）；`_by_unit` 复用保证 (ts, cas_version) 排序确定性；锚点/产物事件无 parseable ts 一律跳过且计入 malformed（probe5/5b 证实不伪造）。
- **P2 F-1**：`within_budget` 在全部事实缺失时为 `True`（`test_evaluate_never_raises_on_garbage_facts` 已钉「no MEASURED breach → True」）——与 loop_telemetry 的 unknown-when-insufficient 原则（`compute_metrics` 无样本给 `status="unknown"`）存在跨模块语义偏差。当前 `not_measured` + `note` 披露完备且零 enforcement 消费者，不阻塞；见发现清单。

### 维度 2：安全性 — ✅ 通过

- 纯函数无 I/O/网络/环境变量读取（V8 零命中）——无注入面、无敏感数据暴露、无权限面。
- `minimal_instruction` 的 `.format()`：unit_id/anchor 值作为**替换值**注入，Python format 不对替换值做二次格式化，无格式化字符串注入路径；产物仅是内存 dict，无命令执行消费方。
- 无硬编码密钥/token。

### 维度 3：可维护性 — ✅ 通过

- 命名表达意图（`heartbeat_should_fire` / `STALL_SCOPE_NOTE` / `_usable_int`）；frozen dataclass（probe7 证实不可变）；`_validate_budget_patch` 单点复用避免三层校验重复；provenance 注释密度高（EVD-1101①、FIX-357/359、W-3、FEAT-063 逐处锚定）。
- `compute_stall_report` ~90 行、`resolve_round_budget` ~60 行——超 SKILL 50 行建议线但与仓库既有风格一致（`compute_metrics` 同量级），结构单一不拆。
- `RoundBudget.source` 在「registry 部分覆盖 + overrides 部分覆盖」时 = `"overrides"`（probe2e 实测）——与 docstring「which layer last contributed」字面一致但易误读为「全部值来自 overrides」，见 F-8。

### 维度 4：性能 — ✅ 通过

- stall 判定最坏 O(anchors × artifact_ts) 每单元（`any(start <= a <= end ...)` 内层线性）——治理事件日志量级下无风险；`compute_stall_report` 单次遍历分组，无 N+1 I/O（纯函数零 I/O）。R6 冷启动不受影响（archguard 实测 cold import 205 modules 持平）。

### 维度 5：测试覆盖 — ✅ 通过（3 条缺口 P3）

- 33 新测试计数吻合（V2）；**判别力**：threshold 边界（0/2/3/4/-1）、garbage facts（str/bool/None）、registry 层缺失/存在/优先序、空事件、window 过滤、malformed、open round、端点闭区间、确定性+非变异（JSON 深拷贝比对）——核心路径与错误路径均有钉。
- **跨模块镜像守卫**（重点 6）：`test_telemetry_threshold_mirrors_engine_default`（L1194，`lt.DEFAULT_IDLE_THRESHOLD == le.HEARTBEAT_IDLE_ROUNDS_DEFAULT`）+ `test_engine_default_budget_heartbeat_n_matches_telemetry`（L1199，resolve 后 budget == telemetry 默认）——stdlib-only import 契约（ADR-015 §6.4）下的等同性钉成立。
- **E2E 链钉**：`test_stall_report_feeds_heartbeat_pipeline`（L1204）——stall 测量 → `heartbeat_should_fire` → `heartbeat_payload`（stop_proof=False）→ `interrupt_recovery_payload`（stop_proof=False）全链贯通。
- 缺口见 F-7（防御分支/registry 层 issue 标签/minutes breach 无直接测试；行为经探针证实正确）。

---

## 3. AI 代码专项 5 项检查（硬门槛必达）

| # | 检查项 | 结论 | 证据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | 新增 33 测试零 mock——registry 层测试用真实 tempfile + 完整 registry 结构（比 mock 更强判别力）；文件内 `unittest.mock.patch` 均为既有纯度守护测试（L449-492/L764），L890「patch」命中为注释单词 |
| 2 | 硬编码返回值 | **无** | 所有输出由输入推导；`DEFAULT_ROUND_BUDGET` 是声明式参数基线（逐键可覆盖、有 source 溯源），非硬编码返回 |
| 3 | 幻觉 API 调用 | **无** | 逐一核实实存：`get_fuse`(loop_engine.py L179)、`_tier_to_fuse_id`(L207)、`load_loop_registry`(L115)、`_filter_window`/`_by_unit`/`_parse_ts`/`_window_label`/`_cycle_times_for_unit`(loop_telemetry.py L245/L349/L221/L236/L422)、`loop_event_log.EVENT_TYPES`(L87，封闭 14 类型枚举实测)、`PP-Fuse-Escalate`（registry pause-point 语义引用，escalation_note 文本） |
| 4 | 未实现 TODO | **无** | 两源文件 grep `TODO\|FIXME\|XXX\|HACK\|NotImplemented` 零命中 |
| 5 | 过度实现 | **无** | REPORT-only 边界克制：无终止/杀进程/状态写入路径；`interrupt_recovery_payload(budget=...)` 未用于文本但 docstring 显式声明「accepted for API symmetry and future bounding」——诚实声明而非隐藏死参 |

---

## 4. MUST 重点审查逐项裁决（任务上下文 9 项）

| # | 重点 | 裁决 | 关键证据 |
|---|------|------|---------|
| 1 | 纯函数纪律 + STALL_SCOPE_NOTE 诚实性 | ✅ 通过 | V8 零副作用；trailing 窗口锚定 latest 事件 ts 而非 wall-clock（`_filter_window` L245-310）；STALL_SCOPE_NOTE（L875-887）明确「静默停滞仅以 last_anchor_ts 陈旧度可见，需调用方 wall clock 判断」且「NOT stop proofs / RISK-037/042 remain open」——与实现一致（open round 不计 streak，测试 L1148 钉住）。锚定分歧披露缺口见 F-3 |
| 2 | 三层参数化 + 逐键 fail-closed | ✅ 通过 | §2 维度 1；正式测试 + 探针 probe2 系列全证实 |
| 3 | stop_proof=False 语义全链 | ✅ 通过 | 全链钉死：`heartbeat_payload` L821 `"stop_proof": False` + `stop_proof_basis`（FEAT-063/NOT a stop proof 文本，测试 L1008 钉）；`interrupt_recovery_payload` L903 同钉（测试 L1103 钉）；`evaluate_round_budget` note（L744-748）「RECOMMENDS interrupt-recovery; nothing is auto-terminated」；`OVER_BUDGET_ACTION`（L540）= report/recommend 语义命名；telemetry 侧 STALL_SCOPE_NOTE 同口径 + 镜像守卫测试；E2E 链测试对两 payload 同时断言 `assertIs(stop_proof, False)`。代码库无任何 enforcement 消费者读取 breaches/heartbeat 去终止执行体（grep 证实） |
| 4 | interrupt 恢复产品化质量 | ✅ 通过 | 最小指令事实绑定（idle_txt/uid/anchor_txt，L868-883；测试 L1040-1056 + probe8）；防扩面守卫「Do NOT re-plan and do NOT expand scope」在指令文本内（L870-871）；三段响应形状（`expected_response_shape` 三键，测试 L1051-1054 钉）；有界 escalation：`escalation_note` 明确 recovery turn 再 idle 走 PP-Fuse-Escalate 而非无限 interrupt（L885-889，测试 L1093 钉）；idle 未知时诚实降级「an unknown number of」（L868-871，测试 L1070 钉） |
| 5 | PROVISIONAL 标注纪律 | ✅ 通过 | 双标注证实：模块注释 L543-548「PROVISIONAL initial thresholds — no measured in-repo baseline exists yet (W-3 provenance discipline)」+ RoundBudget 字段 docstring L568/571「provisional default; parametrized」；`max_idle_rounds=3` 单独实证锚定（L531-535：FIX-357 ~15 轮/FIX-359 16 轮 → N=3 ≈ 1/5 等待税）；enforcement 隔离：PROVISIONAL 值仅进 advisory REPORT 路径（`evaluate_round_budget` breaches → note 显式 nothing auto-terminated），无任何 enforcement 消费者 |
| 6 | 33 测试判别力 | ✅ 通过 | §2 维度 5；镜像守卫 + E2E 链钉均实存且通过 |
| 7 | 验证复现 | ◑ 部分 | V1/V2/V4 吻合；V3/V6 申报口径不可复核（F-5）；archguard 归因修正（F-6） |
| 8 | 21F 归因抽查 | ✅ 方向成立 | ①archive 零 import 耦合 grep 复核：静态顶层 import 纯 stdlib + 动态 import 零命中（V9）；②archguard 6F 复现且全部 pre-existing 于 HEAD——但归因表述需修正（F-6）；③V3 中唯一可复现失败 Finding 零指向 FEAT-044 文件 |
| 9 | __version__ bump 合理性 | ✅ 通过（P3 备注） | grep 证实无测试钉 `__version__`（0.69.0/0.88.0 命中均为注释/RISK 文案）；与既有模式一致（0.69.0 交付时同样无钉）；注释 L85 自述「tracks the last slice that changed this module」——0.88.0 E3 即最后切片，语义成立；62P 证实 bump 零破坏 |

---

## 5. 发现清单（P0~P3）

### P0（阻塞）— 无

### P1（关键）— 无

### P2（建议——不阻塞合并，建议本轮或入账时处理）

| ID | 级别 | 位置 | 发现 | 证据 | 建议 |
|----|------|------|------|------|------|
| F-1 | P2 | `loop_engine.py:726-733`（`within_budget` 构造） | **无事实时 `within_budget=True` 的乐观默认，与 telemetry 侧 unknown-when-insufficient 原则存在跨模块语义偏差**。`evaluate_round_budget` 对全部维度缺事实返回 `within_budget=True` + `not_measured=["steps","minutes"]`——bool 类型无法表达 unknown，docstring「True when no measured breach exists」虽精确，但未来 enforcement 消费者若只读主 bool 会把「未测量」当「合规」（PROVISIONAL 值的 enforcement 隔离是本任务申报纪律，该字段是唯一潜在穿破门） | 测试 `test_evaluate_never_raises_on_garbage_facts`（L962-971）自证该行为并钉住；对照 `compute_metrics` 无样本 metric 的 `status="unknown"`（loop_telemetry.py L464-469）；当前全库零 enforcement 消费者（grep 证实） | 三选一：(a) 后续切片将 `within_budget` 升为三态（`"measured_within"/"measured_breach"/"not_measured"`）；(b) 保持 bool 但在 docstring 加「MUST NOT be consumed without checking `not_measured`」硬警示；(c) 至少在 note 中追加同款警示。不阻塞当前 REPORT-only 交付 |
| F-5 | P2 | 申报面（evidence 入账） | **「manifest 1017」与「loop 族 283P」两项申报数字不可复核**。实测：cleanup canonical 展开 = 14154 文件；`core/manifest.json` = 949 行 / 149 product entries / version 0.87.0；全仓 grep（.py/.governance/docs）无 manifest-1017 关联。loop 族实测七文件 233P、`-k loop` 488P/1F、单文件 62P——283P 未对上任何组合 | §1 V3/V6 表 | Developer 入账 evidence-log 时附产生两个数字的精确命令与口径（若为中间态计数或笔误，按实测勘正）；无法给出口径则按「待验证」降级申报 |

### P3（讨论/记录）

| ID | 级别 | 位置 | 发现 | 证据 | 建议 |
|----|------|------|------|------|------|
| F-3 | P3 | `loop_telemetry.py:889`（`_STALL_ROUND_ANCHORS`）/ `:961` docstring | **stall 锚定与 cycle-time 锚定在 loop_exit 端点存在未披露分歧**。docstring 声称「anchored exactly like the cycle-time metric」，但 `_cycle_times_for_unit`（L422-452）用 `loop_exit` 关闭最后一轮，stall 报告不含 `loop_exit`——已退出单元的最后轮不计入 closed rounds，trailing streak 不因退出归零。探针实测（probe4/4b/4c）：`phase_enter + back_edge×2(idle) + loop_exit` 的事件集，stall 视角 = 2 rounds/trailing=2/**suspects=('PX',)**，cycle-time 视角 = 3 cycles。实际误报路径需非标准事件流（正常退出轮 gate_result 与 back_edge 同 CAS 伴生 → trailing=0；且 stop_proof=False 钉死下游无终止行为），故为披露缺口而非行为缺陷 | 探针输出存审查记录；`_cycle_times_for_unit` L447-452 对照 L889 | 在 docstring/STALL_SCOPE_NOTE 追加一句：「`loop_exit` 不作为 stall 锚（已退出/撤销单元最后轮不计；与 cycle-time 的终止锚分歧是有意的——已完成单元不应进入心跳候选）」；或后续切片对 loop_exit/unit_withdrawn 显式重置 trailing |
| F-6 | P3 | 申报面 + `core/architecture-baseline.json`（HEAD 状态） | **6 archguard 失败的「脏树棘轮」归因表述不精确**。R1/R4 棘轮只测 `infra/verify_workflow.py`（`archguard_ratchet.py` L80 `ENGINE_REL`）——工作树未修改该文件（git status 证实），故 R1（loc 26193 > anchor 25462, +731）与 R4（print 1318>1316；`cmd_write_guard_bootstrap` +2）在**干净 HEAD 树上同样 FAIL**。根因：baseline 最后 regen 于 2026-09-21 REL-084（commit 008efa6），之后 0.88.0 阶段 A~D 已提交已过审票（FEAT-060 c515776 / FIX-383 0ff12f3 / FEAT-064 a8afcbf）使 engine 增长 +731 行且新增 2 print，regen 义务悬置至下次发布门禁。R7（committed ≠ fresh）才与工作树在途修改相关（FEAT-044 + 并行面共同贡献 fresh 漂移，机制性现象，R7 消息自证「engine changed without regen」）。**6F 全部 pre-existing 于 HEAD，零归因 FEAT-044/并行面回归**——申报方向成立（非回归、R7 自证），但「脏树」表述低估了 baseline 滞后 | git log 时间线（baseline 008efa6 @09-21 vs verify_workflow a8afcbf @09-25）；R7 消息 `regen deterministic=True; committed==fresh False`；R4 violation 指向 FIX-383 交付的 `cmd_write_guard_bootstrap` | 申报归因改为「HEAD baseline 滞后（0.88 阶段 A~D 票后未 regen）+ 工作树在途修改的 R7 机制性漂移」；regen 义务由发布门禁（M-2 惯例，REL-084 修复批同款）承担 |
| F-7 | P3 | `tests/test_loop_telemetry.py` 新增段 | 三处测试缺口（行为经探针证实正确，判别力护网未覆盖）：(a) `heartbeat_should_fire` 的 budget 非 RoundBudget 防御分支（L768-769，probe1/1b → False）；(b) registry 层逐键 fail-closed 的 issue 标签与合法键共存（probe2/2b/2c/2d——现有 registry 测试只测合法路径）；(c) `minutes` 维度 breach 无直接测试（现有 breach 测试只打 steps，probe3 证实 minutes 路径正确） | probe 记录 | 返工或下轮补 3 用例：(a) `heartbeat_should_fire(object(), 3) is False`；(b) registry round_budget 含 `max_idle_rounds=0` + 合法键的混合 patch；(c) `evaluate_round_budget(minutes_used=999)` breach 断言 |
| F-8 | P3 | `loop_engine.py:665-668/683-685` | `RoundBudget.source` 在「registry 部分键 + overrides 部分键」时 = `"overrides"`，实际值为两层混合（probe2e：steps=9 来自 registry、minutes=45 来自 overrides、source=overrides）——docstring「which layer last contributed」字面准确但易误读为「全部值来自该层」 | probe2e 输出 | docstring 补一句「source 记录最后**有效覆盖**层；merged 值可为多层叠加」或改值为贡献层集合 |
| F-9 | P3 | `loop_engine.py:561-585`（`RoundBudget.tier: object`） | `tier` 字段类型注解为 `object`（其余字段均具体类型）——实际合法值为 tier 字符串或 None，注解可更精确（`Optional[str]`；仓库其余 dataclass 均具体注解） | L566 `tier: object` | 后续顺手改为 `Optional[str]`（Python 3.10+ 语法 `str \| None`，与模块 import 风格一致即可） |

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | §2 五维度逐一有结论 | ✅ |
| 每条发现标注级别 | 100% | F-1~F-9 全部带 P0~P3 | ✅ |
| 设计一致性检查 | 已完成 | 与 ADR-015（§5 窗口/§6.2 纯度/§6.4 stdlib-only import）、FEAT-063 对齐声明（stop_proof 全链）、version-plan-0.88.0 E3 范围（预算/心跳/interrupt/遥测四件）逐一比对，无偏离；并行面零触碰（diff 审查仅三文件，写操作仅本报告） | ✅ |
| AI 专项 5 项 | 全部完成 | §3 表格 5/5 有结论 | ✅ |

## 7. 总结论

**APPROVED_WITH_NOTES**

- **unresolved_blockers=0**（P0=0，P1=0；P2×2 为不阻塞建议——F-1 语义防护建议后续切片处理，F-5 为申报口径勘正义务）
- 代码质量总评：三层参数化 fail-closed、stop_proof=False 全链钉死、PROVISIONAL 双标注、纯函数纪律与 STALL_SCOPE_NOTE 诚实性均达到申报标准且有测试钉 + 审查方 17 探针独立证实；发现全部为披露/口径/护网加固性质，无正确性或安全性缺陷。
- 并行面纪律：审查严格限定三文件；V3 可复现失败与 archguard 6F 经归因均 pre-existing 或并行域，**零 FEAT-044 归因**。
- 遗留建议：F-7 三用例补钉（成本低、防回归价值高）建议随返工或下轮任务入账；F-1/F-3 建议在 0.88.0 后续切片处理。

---
*审查方法注：本报告全部结论基于——逐行 diff（三文件 3865 行增量中的本任务 1116 行）+ 工作树全文上下文（loop_engine 947 行 / loop_telemetry 1111 行 / 测试 1054 行）+ 独立测试复跑（62P/233P/488P+1F/6F+32P/verify PASSED）+ 17 项独立边界探针（%TEMP% 脚本，零仓库写入）+ grep 机械检查（纯度/import/TODO/mock/版本钉）。审查写操作仅本报告文件；产品代码零修改，并行面零触碰。*
