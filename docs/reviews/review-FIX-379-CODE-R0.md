# Review: FIX-379 — 量测边缘观察 4 项打包（Code Review · R0）

> **结论：APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 · P1=0 · P2=0 · P3=6**
>
> | 字段 | 值 |
> |---|---|
> | Task | FIX-379（P2，0.88.0 阶段 A5） |
> | 轮次 | R0（首次审查） |
> | 审查对象 | 工作树未 commit diff：4 文件 256+/14−（closure_chain.py +67/−8、governance_store.py +70/−6、test_closure_chain.py +86、test_governance_store.py +47——`git diff --stat` 实测与申报一致） |
> | 审查方法 | 逐行 diff + 八点运行时边界探针 + 三套件复现 + verify 全量复跑 + 权威源比对（FIX-375 dispatch 表 / task_row_update ExitCode / rollback-plan §8 #9 / triage JSON / agent-locks.json） |
> | 结论性质 | APPROVED_WITH_NOTES 仅表示硬门槛通过，不替代测试或发布审查 |
> | 独立结构字段 | **unresolved_blockers=0** |

---

## 0. 审查输入与事实基线

- 仓库根校验：`resolve_entry.py --json` → `resolved_root_ok: true`（active_version 0.87.0）。
- 治理状态：`.governance/plan-tracker.md` 已读——维护与演进阶段，0.88.0 阶段 A5，FIX-379 行「🔄 已 lock 待派发 (2026-09-23——0.88 阶段 A5)」。
- diff 范围实测：`git status --porcelain` = 仅 4 个 M 文件，无未跟踪文件 → **verify_workflow.py（薄入口，承载 FIX-375 权威表）未被触碰**（MUST #3「薄入口未动」直接实证）；resolve_entry/bootstrap_aggregate/change_triage/task_priority/archive 等均未改动。
- 权威观察清单溯源：`docs/release/rollback-plan-0.86.0.md` L162（§8 #9）四项逐字 = 交付四项（journal detail 透传 / triage-id 词表与 governance id family 词表对齐 / conflict 退出码语义统一 / pre-probe 语义注记）；`docs/release/release-checklist-0.86.0.md` L105-110 量测专节四项观察逐一对应。

---

## 1. 五维度审查结论

### 维度 1：正确性 — ✅ 通过（逐项证据见下）

**item1（journal detail 透传根因修复）— 正确。**

代码逐边界分析（closure_chain.py L966-1010 修改后全文 + diff 前后对照）：

| # | 边界 | 行为 | 证据（运行时探针实测） |
|---|------|------|------|
| 1 | 顶层扁平载荷（governance_store `_run`→`_emit` 拒绝 dict） | 第三来源识别：`source = refusal or result or (payload if isinstance(payload, dict) and payload.get("code") else {})` | P2 探针：`{"code":"cross_record_violation","detail":"boom ref","error":True,...}` exit 2 → code/detail/disposition 全透传 ✓ |
| 2 | 嵌套形状优先序 | `refusal or result` 短路在第三来源**之前**——嵌套载荷提取不变 | P3 探针：`{"result":{"code":"revision_conflict","detail":"nested wins"},"code":"toplevel"}` → `revision_conflict`/`nested wins` ✓（与 docstring「nested shapes keep priority」一致） |
| 3 | 布尔 error 旗标守卫 | `detail = source.get("detail") or source.get("error") or ""` 后 `if not isinstance(detail, str): detail = ""`——`True` 不进 detail 文本 | P1 探针：`{"code":"manual_intervention","error":True}` → detail `''` ✓；P6：非 str truthy（dict detail）→ `''` ✓ |
| 4 | 非 dict 顶层载荷（list/str） | isinstance 守卫 → `{}` 回退，不崩溃 | P5 探针：`'[1,2]'` exit 3 → `manual_intervention`/`''` ✓ |
| 5 | 字符串 error 兼容 | `error` 为字符串消息时仍作 detail（先在语义保持） | P7 探针：`{"code":"x","error":"msg text"}` → `'msg text'` ✓ |
| 6 | 空/零 falsy code | `payload.get("code")` truthiness 门 + `source.get("code") or ...` 回退一致 | P8 探针：`{"code":""}` → `manual_intervention`（真实写入器 code 均为非空字符串，无实践影响） |

**载荷形状声明核实**：closure_chain docstring 称「governance_store family（`_run` → `_emit`）在顶层打印拒绝 dict（扁平 code/detail/error）」——governance_store.py L2000-2021（`_run` 的 ContractViolation 分支返回原始 dict `{"code","detail","disposition","error": True}`）+ L842（成功载荷 `"error": False`）实测吻合，布尔 error 旗标声明属实。

**根因定位核实（对 M-2 观察①）**：修复前唯一能产出 `detail==""` + code 误判 `manual_intervention` 的路径就是旧 `_refusal_from_cli_output` 的回退分支（旧代码 `source = refusal or result or {}` + `detail: source.get("detail") or source.get("error") or ""`——对扁平载荷 source={} → detail 空串；对 `{"error":True}` 无 isinstance 守卫 → detail 泄漏 `True`）。external 步骤路径的 detail 为内联生成恒非空（closure_chain.py L1125-1131 / L1137-1139）。集成用例 `test_chain_journal_carries_writer_refusal_detail` 用真实 governance_store CLI（`--refs governance_id:XXX-1` 触发真实 `cross_record_violation` exit 2）精确复现 M-2 B 组红相并断言 report payload 与 journal `step_failed` 信封双面 code/detail/exit_code——**红相→修复→绿相链路完整**。

**4 用例判别力**（对 HEAD 旧代码逐例推导）：`test_flat_top_level_refusal_keeps_writer_code_and_detail`（旧 code=manual_intervention≠cross_record_violation → 红）、`test_flat_refusal_boolean_error_flag_never_becomes_detail`（旧 detail=True 泄漏 → 红）、`test_chain_journal_carries_writer_refusal_detail`（旧 code 误判 → 红）——3 例红-判别；`test_nested_result_refusal_extraction_unchanged` 为无回归钉（新旧皆绿，防未来嵌套面回归）。判别力充分。

**item2（task 族词表派生）— 正确，additive-only 声明成立。**

- **派生源核实**：`task_priority._TASK_FAMILY_PREFIXES`（L111-115）= 20 前缀；派生 `_PLAN_TRACKER_ID_FAMILIES = {family: ("plan-tracker.md",) for family in sorted(...)}`（governance_store.py L252-254）。`sorted()` 确定性构造。
- **词表三副本普查**（edge 发现②核查基础）：task_priority L111（20）= change_triage L132-136 镜像（20，逐字一致）≠ archive.py L967-971（18，**缺 FEAT/DOC，先在漂移**）。
- **additive-only 论证成立**：原 7 task 族（FIX/FEAT/REL/AUDIT/REQ/VAL/SYSGAP）⊂ task_priority 20 前缀且映射不变（同 plan-tracker.md）；原 6 record 族（DEC/EVD/RISK/REVIEW/RECO/TRIAGE）显式保留（`_RECORD_ID_FAMILIES`）；新增 13 族 = 20−7，与 docstring 所列清单逐一吻合（FMT/DIAG/MAINT/TD/DESIGN/CLEANUP/PRINCIPLE/TASK/RESEARCH/ACCEPT/INIT/PLAN/DOC）。已知族缺 id 仍拒绝（`_validate_governance_id` L979 `not found in ...`），MES 等两词表外 ad-hoc 前缀仍 unknown-family 拒绝（L960-963）——「无已可解析 ref 变义」成立。
- **合并序无碰撞**：`{**_RECORD_ID_FAMILIES, **_PLAN_TRACKER_ID_FAMILIES}`（L263）——record 6 族与 task 20 前缀无交集（实测枚举）；若未来 task_priority 新增前缀撞 record 族，派生层会静默覆盖，但 `test_id_families_cover_task_family_vocabulary_single_source` 断言 REVIEW→evidence-log.md 等 6 条 record 映射 → 碰撞即红（防碰撞钉存在）。可选加固（不阻塞）：import 时 `assert not (set(_RECORD_ID_FAMILIES) & _TASK_FAMILY_PREFIXES_SOURCE)` 更早失败。
- **消费方唯一**：`_GOVERNANCE_ID_FAMILIES` 全仓仅 L263（构造）+ L959/L963（`_validate_governance_id` 解析与错误消息）——无其他消费面受影响。
- **import 面核实（MUST #2）**：task_priority 为纯 stdlib 模块（L48-54「Purity contract (load-bearing)」明文）→ 无循环导入、冷导入成本可忽略；模块级导入 task_priority 已是既有惯例（bootstrap_aggregate L79、change_triage L104、checks/triage_domain L57、checks/risk_domain L29、loop_exit_bridge L25）——governance_store 新增导入与既成架构方向一致。声明实质成立。
- **3 用例判别力**：对 HEAD 旧手抄表（无 DOC）三例全红-判别——`test_task_family_outside_old_hand_copy_now_addressable`（旧 unknown family 拒绝 → 红）、`test_known_task_family_absent_id_still_refused_as_not_found`（旧 detail=「unknown governance id family 'DOC'」不含「not found」→ 红）、`test_id_families_cover_task_family_vocabulary_single_source`（旧 DOC 不在映射 → 红）。

**item3（epilog + docstring×2）— 与权威表一致，链自身标度属实。**

- closure_chain.py epilog（L1694-1709）中两族标度与 FIX-375 权威表（verify_workflow.py L25516-25518）**逐值 verbatim 一致**：governance_store `0 ok / 2 refusal / 3 retryable`；task_row_update `0 ok / 2 usage / 3 validation / 4 conflict / 5 retryable / 6 manual`。
- task_row_update 权威源抽查：task_row_update.py L1142-1166 `ExitCode(OK=0/USAGE=2/VALIDATION=3/CONFLICT=4/RETRYABLE=5/MANUAL=6)`——标度真实。
- governance_store `_emit` 实现核验（L2040-2045）：`return 3 if disposition == "retryable" else 2`——0/2/3 三值标度与 docstring 声明一致；「差异 DOCUMENTED not silently unified」的处置与 FIX-375 行为变更面独立评审纪律一致。
- epilog 链自身标度（0=ready/finalized/status ok；2=blocked/awaiting-world-check/validation/usage；3=retryable contention）与实现逐值吻合（L1798-1805 error 分派 + L1801 halted 状态、L1816/L1824 status/finalize、L1792-1797 LockContention/ValueError 分类；usage error = argparse 惯例 exit 2）。
- 「链不按写入器退出码分支」声明核实：`_execute_cli_step` L1057 仅判零/非零，非零统一走 `_refusal_from_cli_output` JSON 解码；external 步骤按声明 `blocked_exit_codes` 分支（L1119）——epilog 描述与代码行为一致。
- 四族差异以「canonical four-family table lives at the verify_workflow.py dispatch comment（FIX-375 F-2/F-3）」指针承载，epilog 内联两族（本链实际调用的写入器族）——表述准确。

**item4（pre-probe 语义注记）— 准确。**

- docstring（L663-673）与 `_run_locked` 内注记（L1332-1343）声明：probe 为执行前世界观测、决定 reconcile-vs-execute、执行后不复跑、resume 重新探世界。
- 代码行为逐一吻合：probe 先于 step-state 判定与执行（L1344-1347）；`satisfied=True` → reconcile（L1355-1369，用原始 anchor 不重执行）；执行完成由 `step_completed` + 写入器回执记录（L1421-1428 起），**无执行后复探**；UNKNOWN 恢复双腿同样以 probe 结果为准（L1370-1420）。注记与「查世界不信日志」既有设计语义一致，无过度声明。

### 维度 2：安全性 — ✅ 通过

- 无新输入面、无 shell 插值变化：detail 为结构化 JSON 字段透传（`json.dumps` 信封），不进入 argv/路径拼接；`_run_subprocess` 未动。
- 布尔守卫消除的是**审计文本污染**（`True` 泄漏进 journal），属诚实审计面增强，无注入面。
- 无硬编码密钥/token；无权限面变化；probe/写入器 READ-ONLY 声明未破坏（diff 内 `_run_probe` 只增 docstring）。

### 维度 3：可维护性 — ✅ 通过

- item2 是净减语义双源的维护性修复：governance_store task 族从手抄 7 条改为派生 20 条单一来源；私有名导入附完整理由注释（「public accessor 超出本票文件面；第三份手抄会再造漂移」）——范围纪律良好。
- item1 docstring 记录两载荷形状 + M-2 实测红相（「payload.detail == '' with only the exit code preserved」），修复动机可考古。
- item3 把「为什么不统一退出码」的裁决写进被误读风险最高的三处（链 epilog、_emit、main）——防误读注释质量高。
- 函数长度/命名/重复代码：无超 50 行新函数；`_PLAN_TRACKER_ID_FAMILIES`/`_RECORD_ID_FAMILIES` 命名达意。

### 维度 4：性能 — ✅ 通过

- 词表映射为模块级一次性 dict 构造（O(n) n=20）；查询路径 O(1) 不变。
- import 增量为纯 stdlib 模块，无 I/O、无重依赖（见维度 1 import 面核实）。

### 维度 5：测试覆盖 — ✅ 通过

- 新增 7 用例（4+3）全部有断言到具体闭包码/明细/映射值，非冒烟断言（见维度 1 判别力分析）。
- 三套件零回归实测复现（见 §4）；端到端集成用例覆盖 journal `step_failed` 信封面（code/detail/exit_code 三断言 + 事件计数断言）。
- 防碰撞钉（record 族映射断言）已含（见维度 1 item2）。

---

## 2. AI 代码专项 5 项

| # | 检查项 | 结论 | 证据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 测试用真实文件夹具 + 真实 governance_store CLI 子进程（`test_chain_journal_carries_writer_refusal_detail` 走真拒绝路径），无 mock/patch 注入 |
| 2 | 硬编码返回值 | ✅ 无 | 第三来源识别为数据驱动（payload 键存在性判断）；无按输入返回固定结果的分支 |
| 3 | 幻觉 API 调用 | ✅ 无 | 引用的 `task_priority._TASK_FAMILY_PREFIXES` 实存（task_priority.py L111）；其余为 json/argparse/re 标准面 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME；「范围外行为变更（triage 入口词表约束）」显式声明归属后续 triage 票，非 TODO 掩盖 |
| 5 | 过度实现 | ✅ 无 | 四项交付均在 rollback §8 #9 声明面内；测试 7 用例对位 2 处行为变更（4 对 item1、3 对 item2），无额外机制 |

---

## 3. 设计一致性 + 锁面外测试扩展合规性（MUST #5）

**设计一致性**：
- FEAT-056 契约：refusal 信封形状 `{code, disposition, detail, observed_revision, exit_code}` 不变（L1009-1010），item1 为纯提取面扩展。
- FEAT-046/051 写入器族：标度差异「DOCUMENTED, not silently unified」与 FIX-375 已评审的行为变更面（verify_workflow dispatch 表）一致，未引入任何退出码行为变更。
- task_priority 纯净契约（L48-54）：未被破坏（单向导入，无反向依赖）。
- FIX-375 权威表单源保持：verify_workflow.py 未触碰（§0 实证），新文档面以指针引用之，无第二权威副本。

**锁面外测试扩展合规性——成立**：
- triage 原始申报面（`.governance/change-triage/FIX-379.json` L8-11）：**仅 closure_chain.py + governance_store.py 两文件**。
- agent-locks.json：初始锁 18:52:12/29（含 verify_workflow.py，未动）；两个测试文件 **19:41:31/32 后补锁**，ttl_reason = 「Test file extension per stage-maintenance hard rule (bug-fix MUST have regression tests) - disclosed in evidence」。
- 裁定：stage-maintenance「Bug 修复 MUST 回归测试」为硬性要求，测试扩展**必要且已披露**（补锁 + 理由机录于锁文件）→ 合规。item1 为行为变更（审计保真），4 用例回归测试不可豁免； Developer 未静默扩面。
- 残留流程项 → F-5。

---

## 4. 验证复现记录（MUST #6）

| 申报 | 复现命令（infra 目录） | 实测 | 裁定 |
|---|---|---|---|
| 39P（35+4） | `python -m pytest tests/test_closure_chain.py` | **39 passed** | ✅ 精确（HEAD 基线 35 个 `def test_`，+4 新增） |
| 105P | `python -m pytest tests/test_governance_store.py` | **105 passed** | ✅ 总量精确（HEAD 基线 102 个 `def test_`，实际 +3——申报拆分 101+4 笔误 → F-1） |
| 284P（三套件零回归） | `python -m pytest tests/test_task_priority.py tests/test_change_triage.py tests/test_task_row_update.py` | **284 passed in 39.86s** | ✅ 计数精确（147+95+42；派生/镜像/退出码三相关面零回归。申报未披露套件构成，本组合为审查推断复现） |
| 两套件合并 | `pytest tests/test_closure_chain.py tests/test_governance_store.py` | **144 passed in 45.71s** | ✅ |
| verify 全量 PASSED | `python verify_workflow.py verify` | **`== Verification Result: PASSED ==`，exit 0** | ✅ 复合门通过（fail-closed 合成面——任一子检查 FAIL 即翻红；cross-refs/manifest 申报 PASS 被复合通过覆盖，单项行未在输出尾部捕获，如实注明） |
| manifest 866/995 | 同上复合内 | 未单独取行 | ⚠️ 以复合 PASSED 覆盖认定，单项数字未独立复现（如实标注，不影响结论） |

**八点运行时边界探针**（item1，`_refusal_from_cli_output` 直接驱动）：P1-P8 全部符合预期（明细见维度 1 表格；P4 证实先在 AttributeError，见 F-3）。

---

## 5. 边缘发现三条归因核实（MUST #7）——三条全部归因正确

| # | Developer 边缘发现 | 归因核实 | 证据 |
|---|---|---|---|
| ① | triage 入口形状校验限制（仅 PREFIX-NNN 形状校验，词表约束属后续票） | ✅ 正确 | change_triage.py L829（dispatch/locks 路径）+ L1085（triage-record 路径）双入口均为 shape-only `task_id must match PREFIX-NNN`；governance_store.py L245-248 注记显式声明约束入口属行为变更、归属独立 triage 票（范围纪律正确） |
| ② | 镜像词表未去重 | ✅ 正确（且漂移真实存在） | 三副本普查：task_priority L111（20）= change_triage L132 镜像（20，与权威逐字一致）≠ **archive.py L967-971（18，缺 FEAT/DOC）**——先在漂移，影响面为归档迁移 gating（FEAT-*/DOC-* 关联 Task 被视 cross-entity），超出本票文件面未修；谱系注释 task_priority L1863-1866 自证副本链（archive.py 在先） |
| ③ | 非 dict result AttributeError | ✅ 正确（先在行为，本 diff 未引入未恶化） | 探针 P4：`_refusal_from_cli_output('{"result":"plain string"}', 3)` → `AttributeError: 'str' object has no attribute 'get'`；旧代码 `source = refusal or result or {}` 对 truthy 非 dict result 同样崩溃——行为等价 |

---

## 6. 发现清单（P0~P3）

> 无 P0 / P1 / P2。以下 6 条 P3 均为记录性/后续票候选，不阻塞合并。

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-1 | P3 | 申报文本（非代码） | 申报拆分「105P（101+4）」与实际不符：HEAD 基线 102 个 test_ + 新增 3 = 105（+4 的新增在 39 套件侧）。套件总量与新增总数（7）均正确，属拆分笔误 | 收口时按 102+3/35+4 口径机录更正 |
| F-2 | P3 | governance_store.py L2031-2032 | `_emit` docstring 括注「six-value scale (3 validation / 4 conflict / 6 manual)」仅列 3/6 非零值——为两族分叉 disposition 的对比性选择，但字面易误读为三值标度；`main()` docstring（L2268-2270）则列全 5 非零值 | 后续小修括注补全或改写为「whose validation/conflict/manual dispositions map to 3/4/6」 |
| F-3 | P3 | closure_chain.py L1003-1007 | 非 dict `result`/`refusal` 值 → AttributeError（先在，Developer 已披露，本函数本轮在编辑面内未顺手加守卫） | 后续票加 `isinstance(source, dict)` 一行防御 + 负例测试 |
| F-4 | P3 | archive.py L967-971 | 第三份 `_TASK_FAMILY_PREFIXES` 漂移（18 vs 权威 20，缺 FEAT/DOC），governance_store 新注释仅声明 change_triage 镜像、未提此副本；「single source」叙事在仓库全局面不完全 | 后续票对齐 archive.py 或显式声明多副本政策（与 FIX-381 backport 政策呼应）；本票不加文件面，维持如实披露 |
| F-5 | P3 | .governance/evidence-log.md | 锁面外测试扩展披露目前仅机录于 agent-locks.json ttl_reason；evidence-log 现仅 TRIAGE-FIX-379 一行（L2562），披露 EVD 与验证命令尚未回填 | Coordinator 收口时回填（任务验收「验证命令留档」要求），与 task-row-update 机录路径一致 |
| F-6 | P3 | release-checklist-0.86.0.md L107（观察①文本） | 观察① prose 以 `_execute_external_step` 归因 detail 丢失机制；实际修复落在 `_refusal_from_cli_output`（CLI 写入器路径）。代码证据支持根因正确：external 路径 detail 内联生成恒非空（closure_chain.py L1125-1139），全链唯一空 detail 生产者是旧回退分支——观察文本机制归属不精确，不影响修复正确性 | 仅记录；0.86.0 文档为已发布历史，不回改 |

---

## 7. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 硬门槛：P0=0 ✅；五维度全覆盖且逐一有结论 ✅；每条发现带级别/位置/证据 ✅；设计一致性检查完成（FEAT-056/FEAT-046/051/task_priority 纯净契约/FIX-375 权威表五面对照）✅；AI 专项 5 项全完成 ✅。
- 四项交付与 rollback-plan-0.86.0 §8 #9 权威清单逐字对应，无「不适用」项：item1 行为变更（审计保真）根因正确 + 红相精确复现；item2 additive-only 论证成立且带防碰撞钉；item3 以 DOCUMENTED-not-unified 处置与三处防误注记落地，权威表单源未动；item4 注记与代码行为逐点吻合。
- Developer 三条边缘发现全部归因正确且披露诚实（§5）。
- 验证复现：39P/105P/284P + verify 全量 PASSED（exit 0）独立复跑通过；manifest 单项数字未独立取行（复合覆盖，如实标注）。
- 遗留项（P3×6，无截止阻塞）：F-1 收口更正口径；F-2/F-3/F-4 为后续票候选（各自 triage）；F-5 为 Coordinator 收口义务；F-6 仅记录。

*审查人：Code Reviewer Agent（R0）· 证据均为本会话实测（命令/探针/文件行号），未采信未经复现的申报。*
