# FEAT-080 代码审查 R0（B3 接线批）

- **Reviewer**: Code Reviewer Agent（独立；round R0）
- **日期**: 2026-09-29
- **基线**: HEAD=2ef9fc2（FEAT-079 已落库）；工作树 = 15M + 1??（+882/−90）——与任务声明一致（`git status --porcelain` + `diff --stat` 实测复核）
- **对象**: FEAT-080 M1-B3 接线批 (a)~(i)（TRIAGE-FEAT-080 reason 字段已实读，清单一致；feat080-notes.md 终账已实读）
- **执行协议**: TEMP 重定向 `.governance/tmp/check-run-20260929`；复跑限定向族（禁全量）；本报告增量落盘

## 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0，P0=0，P1=0，P2×1，P3×3）

十项验收标准全部核验通过；定向复跑 439 tests 全绿；regen 算术与 ratchet 语义实测吻合；零范围外文件。P2/P3 findings 均为非阻塞改进项，不构成合并障碍。

---

## 一、十项验收核验

| # | 验收项 | 判定 | 事实依据 |
|---|--------|------|----------|
| ① | INV-1 三分支语义 | **PASS**（附 F-1 边界注记） | 同级 FAIL：`test_machine_signal_above_open_user_named_fails`（`_row` 默认 priority="P1"，P1/P1 构造行→FAIL，测试在场且绿）；跨级 WARN：`test_cross_level_inversion_warns_not_fails`（P0/P1→PASS+WARN+invx_pairs）；未解析保守 WARN：`test_unparsed_priority_warns_conservatively`（""/P1→WARN）。`_priority_rank`=正则 `^P([0-9])$`，裸 P 级才解析。与 ADR §2.2.3 R0 修订语义一致（L206-207 实读）。边界注记见 F-1：ADR 未定义的第四态（双方可解析但 rank_m>rank_u）落入 else 分支，消息文本与事实矛盾 |
| ② | Check 42 事件抽取确定性 | **PASS**（附 F-2 注记） | 列偏移与真实表头逐一实测吻合：evidence-log `cells[1]=ID/cells[2]=任务/cells[8]=日期/cells[10]=状态`；risk-log `cells[1]=编号/cells[2]=日期/cells[9]=当前状态/cells[13]=备注`（**刻意排除 cells[10] 缓解动作列**——防缓解叙事中「关闭」误触发终局判定，设计正确）。REVIEW: NEEDS_CHANGE→problem、APPROVED*（startswith）→closure；EVD: 状态列含 ✅→closure（实测历史 149 条 ✅ 行中 96 条在状态列、53 条在他列——他列正确不计入）；RISK: 当日行→problem、终局词（关闭/收窄/升级）在当前状态+备注→closure。手写 REVIEW 行会被计入——但 REVIEW 行本为 review-record 机录专用面（禁手写），log 即事实源语义，属设计内行为非误配；表头行/分隔行经 `cells[0]` 空校验+前缀匹配排除。本机复现（today=2026-09-29）：events 与 Developer 样本逐字一致（DESIGN-021 problem + RISK-061/062 problem；rate 33%，unclosed=RISK-061/062）。注记见 F-2：BLOCKED 结论的 REVIEW 行两不记 |
| ③ | W(session) 窗口两态 | **PASS** | 在场态：session-snapshot 携带今日→`window=session（session-snapshot 会话身份关联，2026-09-29）`（本机复现）；缺席态：显式 `window=daily-aggregate（按日聚合，同日多会话合并，精度降级——session-snapshot 未携带…；禁止无标注的静默降级，ADR-021 §3.2.3/§2.4 L4）`。两态均有测试（`test_collect_session_closure_events_risk_and_daily_note` / `_snapshot_window`）且实测复现。无静默降级 |
| ④ | CLI 关窗完备 | **PASS** | `--demand-source required=True` + choices 三值 + `--demand-basis`（user-named 时库层强制，BC-4）；`cmd_change_triage` 传参贯通（run_triage 调用 +2 参数）；既有测试调用面 2 处 `_run_cli` helper 注入缺省旗标；新增负例 `test_cli_missing_demand_source_exits_two`（完整合法参数集缺旗标→argparse exit 2 + record 零写入实测断言）；test_change_triage **120/120 本机复跑绿**。仓库内无其他脚本化 change-triage CLI 调用面（md 面仅文档示例）；change_triage.py 三处窗口注释→已关闭时态（diff 逐处核实）。`demand-source-revise` 子命令：thin entry→`append_demand_revision`（校验全在库层，RISK-039 纪律）+ registry `_COMMANDS` 登记 + CMD 表接线 |
| ⑤ | 发布门豁免=target_version（NF-2） | **PASS** | `check_release_admission`：豁免=`_parse_semver(target_version) > release_vt`（严格更高 semver=显式改期）；未版本化/不可解析 target 留在 UN（结构性需求不得隐形顺延）；MS=open machine-signal 且 target==release；未申报/conflict 载荷 FAIL（fail-closed）；无版本→SKIP+warning（非静默 PASS）。接线于 `check_release_readiness`（`if version:` 载荷时判，issues 进 FAIL 面、warnings 进 release_warnings） |
| ⑥ | regen 三票 lineage 算术与 ratchet 语义 | **PASS** | 26478+30+74+339=**26921** 算术成立，且=本机实测 verify_workflow.py 物理行数（26921，ReadAllLines 口径）；R4 1318→**1338**（+20=`_run_full_engine_checks` 589→608 +19 与 `cmd_demand_source_revise` +1，architecture-baseline.json 逐键吻合）；test_archguard_ratchet 锚断言 26385→26921 + FACTS_PRINT_TOTAL 1318→1338 随批更新（三预存在红之一：HEAD 处 baseline=26478 vs 测试断言 26385 不一致——FEAT-079 报告③所述，本批消解）；only-down ratchet 语义延续（锚=提交真值，regen 即 sanctioned 变更）。test_registry substring→真则修复：旧 `assertNotIn("import registry")` 对 `from exception_registry import registry_error_note` 误命中（"import registry" 是 "import registry_error_note" 前缀），新正则 `(?m)^\s*(?:from\|import)\s+registry\b` 语义不变零误配（`\b` 拒绝 `registry_` 续接）。contract_matrix 快照 98 keys/95 handlers/73 segments 与 registry 双表一致（FROZEN 计数三处同步） |
| ⑦ | (g) 增量合并保真 | **PASS** | `--task --write`：`merged = 既有文件 packets 全集（含非活跃/手工充实）∪ 选中再生`；顶层手工键经 `packets_meta`（排除 version/generated_at/packets）保留。RED 实证语义经 HEAD 代码对照成立：旧 `--task --write` 直写 `payload`（active-only 再生产物）→必丢非活跃条目（FIX-199）与顶层手工键——新测试 `test_task_write_preserves_unselected_inactive_and_top_level` 四断言（未选 FIX-202 seeded / 非活跃 FIX-199 / coordinator_note / 选中包 manual_note 充实经 existing overlay 存续）；bare `--write` 语义不变有专测。本机 2/2 绿 |
| ⑧ | ADR 三处微注 | **PASS** | ①L62 消歧：「behavior-protocol.md 携带全文；SKILL.md 携带压缩形式——FEAT-078 R0 F-2 消歧」——与 zerodrift 测试的全文/压缩双提取面互证；②§2.1 判据 5 DEC-291 句：M1≤180/M1+M2≤370 + per-surface 口径 + 常量名 `CONTRACT_M1_BUDGET_TOKENS`/`CONTRACT_COMBINED_BUDGET_TOKENS`——常量实测在场（injection_budget.py L228-229：180/370），引用非虚指；③§2.2.1 from 派生域：「派生域=写入器可及域：最新修订事件>triage record——行内标注属 plan-tracker md 面…FEAT-077 R1 P3-1 消歧」。三处逐字恰当、无过度声称 |
| ⑨ | 295 定向绿复跑 | **PASS** | 本机定向复跑 **439 全绿**：provenance_domain 35 + zerodrift 5（=40）；B3 wiring 5 + xp 增量合并 2（=7）；change_triage 120；registry 定向 25（CheckRegistry/StartupImport/Advisory/Segment 族——ADVISORY+42 的 AST 判定机核）；contract_matrix + archguard_ratchet 65；task_priority 182（Check 41 上游数据面）。超集覆盖 Developer 声明的 295 清单；`check-governance --summary-only` 一次收尾：35 issues——构成=既有面（EVD-1252 用户影响字段〔FEAT-078 行格式〕+ REL-095 quality budget）+ FEAT-080 缺 execution packet（18d/18d-RB2，Coordinator 侧写包义务，非本批代码缺陷），无本批新增缺陷面 |
| ⑩ | 零范围外 | **PASS** | 工作树 16 文件逐一核对：7 锁内（verify_workflow/test_verify_workflow/provenance_domain/test_provenance_domain/injection_budget/ADR-021/test_injection_zerodrift〔expected-new〕）+ 9 声明偏差（change_triage.py〔(b) 注释〕/test_change_triage.py〔(e)+(b)〕/registry+quickscan_registry+test_registry+test_contract_matrix+test_archguard_ratchet+snapshots.json+architecture-baseline.json〔(d) regen 族〕）——与 feat080-notes.md 终账「偏差/上报」节逐项对应，均有任务上下文授权。无未声明文件 |

## 二、Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-1 | **P2** | `checks/provenance_domain.py` `check_priority_inversion` INV-1/INV-X 判定 else 分支（三分支 elif 链） | else 分支合并两种不同条件：(a) P 级未全部可解析；(b) 双方均解析但 `rank_m > rank_u`（machine 更低优先级却排前）。对 (b)，消息「P 级未全部可解析（'P2' vs 'P1'）」与事实矛盾（两值均可见地可解析——自相矛盾的治理披露文本）。且按 ADR §2.2.3 对 INV-1 的立论（「排序键正确时本判据恒不触发，触发即排序实现缺陷或手写推荐绕过，两者都该 FAIL」——排序键 P 级优先，P2 machine 排 P1 user 之前同样不可能出自正确排序），(b) 至少应得准确披露文本；是否升 FAIL 需 ADR 澄清（ADR 现文只定义同级 FAIL 与「M 严格更高」WARN 两态）。该子态无测试覆盖 | 拆分 else 为两臂：未解析→维持现行保守 WARN 文本；已解析但 rank_m>rank_u→独立消息（如「低优先级 machine-signal 排于高优先级 user-named 之前——排序不变量破坏」），并随 B4 或 ADR 勘误裁定该臂是否 FAIL；补一行动作测试（P2 machine/P1 user） |
| F-2 | **P3** | `verify_workflow.py` `_collect_session_closure_events` REVIEW 行族 | 结论为 `BLOCKED` 的 REVIEW 行既不计 problem 也不计 closure——对 Check 42 不可见。BLOCKED 是升级未决态（按 code-review 规范非通过终态），语义上更接近「当日新增问题」；若某任务当日仅得 BLOCKED 复审且无其他行，problems_raised=0→SKIP，该升级不产生闭环义务 | 随 B4 词集面一并裁定：BLOCKED 是否入 problem 词集（一行改动+测试）；当前 box 已显式披露 deferred_registration 恒 0，BLOCKED 面建议同法披露 |
| F-3 | **P3** | `verify_workflow.py` `cmd_execution_packet` 写入 note | note 打印「regenerated {args.task}」用的是**请求的**任务名列表——若请求名不在活跃集（typo/已归档），实际未再生（仅原样保留），note 仍声称已再生 | note 改用 `', '.join(sorted(selected))`（实际再生集合），与 preserved 计数同口径 |
| F-4 | **P3** | `verify_workflow.py` `_provenance_rows_for_governance` | `except Exception: return []` 把「tracker 不可读」与「解析抛异常」合并呈现为同一 SKIP 文案——解析回归会以 SKIP（而非错误）面貌静默降档。方向安全（SKIP 有披露、绝不静默 PASS），仅可观测性欠佳 | 可选：except 中把异常摘要带入 SKIP 文案（不改变 fail-closed 方向）；或维持现状并在 B4 观察期评审时复核 |

## 三、五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | 通过（F-1 边界注记） | 三分支/四桶映射/列匹配/窗口两态/发布门豁免/增量合并均经代码逐行审读+构造用例+真实数据复现三重验证；invx_pairs 三处返回结构同步；`_priority_rank`/`_parse_semver` 边界（空串/prose/P9/非 semver）均归 None |
| 安全性 | 通过 | 无硬编码密钥；CLI 输入 argparse choices+库层三重 fail-closed（非法值/user-named 缺 basis/P2+user-named 拒绝）；修订通道 append-only 不可变记录+防伪造起点（from 派生）；子进程测试全部 TemporaryDirectory 隔离；无注入面（regex 仅读侧匹配） |
| 可维护性 | 通过 | 触点注释全部同步时态（窗口关闭/RT-4/lineage 注释含授权链）；registry/快照/冻结计数三处一致性由 CheckRegistryTests 机核；纯判定/引擎接线单向依赖纪律（provenance_domain 不 import 引擎）保持 |
| 性能 | 通过 | 采集器单遍行扫描 O(行数)；Check 41 复用 run_cli_analysis 同款 parse→resolve→compute 管线（无重复实现）；41/42 每次检查新增两次文件读+一次 tracker 解析，有界 |
| 测试覆盖 | 通过（F-1 子态缺口） | 439 定向复跑全绿；INV 三分支/采集器四族/窗口两态/合并保真/CLI 负例各有专测；standard profile 覆盖达标（核心路径+边界+错误路径） |

## 四、AI 代码专项 5 项检查

| 项 | 结论 | 依据 |
|----|------|------|
| mock 残留 | 无 | patch.object 全部 with 上下文内（EXECUTION_PACKET_PATH/_active_execution_packet_tasks），无模块级注入泄漏 |
| 硬编码返回值 | 无 | 41/42 box 均由实时采集计算；本机复现与 Developer 样本独立吻合（非复述） |
| 幻觉 API 调用 | 无 | tpa.parse_task_dependencies/_resolve_row_demand_sources/compute_unblocked_tasks/read_archive_index_completed_ids、extract_canonical_templates 均实测存在且调用成功 |
| 未实现 TODO | 已披露非隐藏 | deferred_registration 恒 0 在 Check 42 box 显式披露「随 B4 落地」——范围边界声明，非死代码 |
| 过度实现 | 无 | 全部触点映射 (a)~(i) 条目；demand-source-revise 为 triage 授权项（ADR §2.2.1 F-P1-3） |

## 五、硬门槛裁决

- P0 阻塞问题数 = **0** ✓
- 5 维度全覆盖 = 100% ✓
- 每条发现标注级别 = 100%（P2×1/P3×3）✓
- 设计一致性（对 ADR-021）= 已完成（§2.2.1/§2.2.3/§2.2.4/§3.2.3/§2.1 判据 5 逐节比对；唯一开放点=F-1 第四态待 ADR 澄清，已按 P2 记录不阻塞）✓
- AI 代码专项 5 项 = 全部完成 ✓

## 六、复跑记录（协议内）

| 套件 | 结果 |
|------|------|
| test_provenance_domain.py + test_injection_zerodrift.py | 40 passed |
| test_verify_workflow.py -k "B3Provenance or ExecutionPacketIncremental" | 7 passed |
| test_change_triage.py | 120 passed |
| test_registry.py -k "CheckRegistry or StartupImport or Advisory or Segment" | 25 passed |
| test_contract_matrix.py + test_archguard_ratchet.py | 65 passed |
| test_task_priority.py | 182 passed |
| check-governance --summary-only（一次） | 35 issues（构成=既有面+Coordinator 侧缺包，无本批代码缺陷面） |

另：`_collect_session_closure_events`/`_provenance_rows_for_governance`/`check_priority_inversion` 真实数据直调复现（今日 events/rate 33%/Check41 Rows 30/labeled 3/10% PASS——与 Developer 样本逐字一致）；verify_workflow.py 物理行数实测 26921=新锚。

## 七、遗留项

| 项 | 级别 | 建议处置 | 截止 |
|----|------|----------|------|
| F-1 else 臂拆分+第四态测试 | P2 | 随 B4 批或 ADR 勘误随批承载 | 0.93.0 窗口内 |
| F-2 BLOCKED 词集裁定 | P3 | B4 词集面一并 | B4 批 |
| F-3 note 口径 | P3 | 顺手修（一行） | 下次触碰该函数 |
| F-4 SKIP 可观测性 | P3 | 可选 | 观察期复盘 |

---

*Reviewer 不修改产品代码；本报告为唯一产出物。复审链消费：APPROVED_WITH_NOTES（unresolved_blockers=0）= 通过终态。*
