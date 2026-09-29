# Code Review R0 — FEAT-077（demand_source 需求源字段 + 排序加权 + 反倒挂判定件）

- **Task**: FEAT-077（M1-B2：DEC-286(7)/DEC-289 承载——provenance 三值字段进 change-triage + task-priority 排序加权 + 反倒挂/发布门/闭环率纯判定件）
- **Reviewer**: Code Reviewer Agent（独立，R0 首轮）
- **Date**: 2026-09-29
- **审查对象**: 六文件（`infra/change_triage.py` +116 / `infra/task_priority.py` +264/−17 / `infra/checks/provenance_domain.py` 新建 400 行 / `infra/tests/test_change_triage.py` +156 / `infra/tests/test_task_priority.py` +318 / `infra/tests/test_provenance_domain.py` 新建 471 行）
- **锚定**: ①DEC-286(7)（decision-log L228）+ DEC-289 D1 裁决（L231）②Coordinator 约束注入（缺省默认 machine-signal 窗口协议 / 非法值 fail-closed / 不做修订通道留注释 / 禁硬编码检查编号）③ADR-021 稳定节 §2.2.1-2.2.4（在途 R0 返工文本，仅作锚定不作完整基准）
- **范围排除**: FIX-404 在途（verify_workflow.py + test_verify_workflow.py）与 ADR-021 返工在途文件未评审未触碰

## 结论

# APPROVED_WITH_NOTES

**unresolved_blockers = 0**

| 级别 | 计数 |
|------|------|
| P0 阻塞 | 0 |
| P1 关键 | 0 |
| P2 建议 | 1 |
| P3 讨论 | 5 |

## 测试复跑证据（定向三族，协议限定）

```
$env:TEMP/$env:TMP → .governance/tmp/check-run-20260929（协议重定向）
python -m unittest skills.software-project-governance.infra.tests.test_change_triage \
  skills.software-project-governance.infra.tests.test_task_priority \
  skills.software-project-governance.infra.tests.test_provenance_domain -v
→ Ran 311 tests in 29.174s — OK（一次通过，无重试）
```

与 Developer 声明「311 绿」吻合。未跑全量（协议禁止）；`test_verify_workflow.py` 相关面按 ADR §2.2.2 验收 3 属 verify 锁释放后（B3）范围。

## 关键核验结果（验收标准八条逐条）

| # | 验收标准 | 结果 | 事实依据 |
|---|---------|------|---------|
| ① | 三值封闭 + fail-closed 三重语义 | ✅ PASS | `DEMAND_SOURCES` 元组封闭（change_triage.py L131）；三重门禁：非法值（L1161-1165，归一后仍非枚举 → error 零写入）/ user-named 缺 basis（L1166-1170，防 BC-4）/ P2+user-named 拒绝（L1171-1178）。测试 `test_invalid_demand_source_fails_closed_zero_write`（含 "user_named"/"usernamed" 拼写漂移负例）、`test_user_named_without_basis_fails_closed`、`test_user_named_p2_rejected_floor_p1` 均断言零写入（record 不存在 + evidence 无行）。exit 2 语义由 CLI thin entry 承载（B3 接线，库层 error dict 分层与 ADR §2.2.1 一致） |
| ② | D1 tie-break 精确（同 P 级内；不跨 P 级） | ✅ PASS | `_priority_sort_key` = (priority, `_DEMAND_RANK[ds]`, version, id)（task_priority.py L1382-1396）；`_DEMAND_RANK` 与 ADR §2.2.2(4) 代码逐字一致（user-named:0/active-defect:1/machine-signal:2/legacy:0/conflict:0）。跨级实证：`test_demand_rank_does_not_cross_priority_levels`（P0 machine 先于 P1 user）；同级实证：`test_same_priority_user_named_before_machine_signal` + 完整键 `test_full_order_priority_demand_version_id` + 集成 `test_report_rows_judged_by_inversion_guard`（真实 tracker 文本四行序断言）。`_DEMAND_RANK[ds]` 直接索引（非法值 KeyError fail-loud）为 ADR 逐字代码，docstring 论证充分 |
| ③ | resolve 优先级与 conflict 保守处理 | ✅ PASS | `resolve_demand_source`（L1399-1435）：record 合法值权威 → 与行内一致返回该值 / 不一致返回 conflict；record 无键或值非法 → 无权威 fail-open 到行内（ADR §2.4 L2 tpa 联查行——已核实在册 L279）；无源 → legacy。conflict 排序保守 rank 0 + `demand_source_conflicts` 报告面 + 横幅披露（`test_conflict_sorts_conservatively_as_user_named_rank`）。Never-raises（纯字符串操作）。CLI 端到端两例：JSON 覆盖缺失行内标注（排序翻转实证）/ 冲突披露 |
| ④ | 缓存失效键有效性 | ✅ PASS | `triage_records_mtime` 新键（`_triage_records_mtime` L886-897）：复用条件加入 `state["triage_records_mtime"] == 目录 mtime`；写缓存同步落键（L2459）。旧缓存无键 + change-triage 目录存在 → None≠mtime → 强制重算一次（FIX-341 升级模式，never stale）。端到端实证：`test_new_triage_record_invalidates_cached_analysis`（无 force 复用断言「复用上次分析」→ 新增 triage 记录 → 复用消失 + 重算含 src=user-named），且覆盖「目录从无到有」边界 |
| ⑤ | 纯函数性（provenance_domain 不 import verify_workflow） | ✅ PASS | provenance_domain.py import 区仅 `re` + `from task_priority import DEMAND_SOURCE_VALUES`（L61-65，全文已读实证）；docstring 声明 wiring 单向纪律（同 snapshot_domain/gate_domain 先例）。三函数（check_priority_inversion / check_release_admission / session_closure_rate）全纯判定、Never-raises、无 I/O |
| ⑥ | 既有行为零回归（懒加载 import 无环） | ✅ PASS | 模块级依赖单向实证：change_triage → task_priority（既有顶部 import，本批仅 +`demand_source_distribution`）；task_priority 模块级 stdlib-only（change_triage 为 `_resolve_row_demand_sources` 函数内 lazy import，L905-907 注释明示环规避）；provenance_domain → task_priority 单向。`TaskDep` 为 `@dataclass(frozen=True)`（L576），`demand_source` 带默认值追加于字段尾——位置参数构造兼容（`test_default_field_value_is_legacy`）；既有四 fixture 全量解析 legacy 零回归（`test_existing_fixtures_stay_legacy_zero_regression`）；`_ID_TOKEN_RE` 中文字标注 byte-identical 回归（`test_id_token_extraction_regression_with_marker`）；311 绿含全部既有测试 |
| ⑦ | 测试真实覆盖（非 happy-path only） | ✅ PASS | 三族新增 ~57 测试方法：负例（非法值三变体/缺 basis/P2 混合/冲突/畸形事件/未知 kind）、边界（completed≠open、blocked≠停放、recommended-pool 限定、空 rows、跨级、无版本、非载荷版本、目录从无到有）、fail-closed 与 fail-open 双向、时序（缓存失效）、真实文件 I/O 集成（tempdir + 真实 JSON 落盘 + CLI 编排）、DEC-287(1) C 级软件化场景回归。ADR §2.2.3 测试计划验收 1-5 全覆盖 |
| ⑧ | 零范围外修改 | ✅ PASS | `git status` 实证：修改文件 = 六文件中 4 个 + FIX-404 在途 2 个（非本批）+ ADR-021 untracked（在途返工，非本批产物）。六文件之外零产品代码修改 |

## 五维度逐项结论

### 维度 1：正确性 — PASS
- 窗口协议缺省（None/"" → machine-signal，`test_missing_demand_source_defaults_machine_signal_window_protocol` 双形态）与 Coordinator R0 P1-2 裁定一致；大小写归一（"USER-NAMED" → 合法）有正例。
- 排序/联查/缓存/发布门/闭环率逻辑逐行核验无误（见上表）；`demand_source_distribution` 四桶 + conflict 独立披露口径自洽（conflict 不入四桶，分布行附 `conflict:N`）。
- 发布门 `_parse_semver` 严格 X.Y.Z（None 语义区分「无版本」与「高于发布版」——避免 (inf) sentinel 把未版本化 user-named 误判为显式改期，注释论证充分）；未版本化 UN 留在集合（隐形顺延防线，`test_user_named_without_version_counts_open` + DEC-287(1) 场景）。

### 维度 2：安全性 — PASS
- 输入校验：demand_source 三重 fail-closed；行内 marker 正则只匹配三个固定中文词；`_rows`/`_source`/`_bucket` 全防御。
- 无注入面（纯文本/JSON 处理，json.dumps 转义 demand_basis 自由文本）；无硬编码密钥；无权限面变更；evidence 行的 demand_zh 来自固定映射（非用户可控）。

### 维度 3：可维护性 — PASS（1×P2）
- 命名一致（DEMAND_SOURCE_VALUES/_DEMAND_RANK/resolve_demand_source/check_release_admission）；注释锚定 ADR 节引用 + 裁决编号可追溯；函数职责单一。
- P2-1：test_change_triage.py `DemandSourceStepTests` 类头注释 bullet 4 与实现语义相反（见 findings）。

### 维度 4：性能 — PASS
- INV-1 双重循环 O(n²) 限于 recommended 池（实际 <100）；resolve 联查 O(tasks×records) ≈ 10⁴ 量级字符串比较；triage 记录一次批量加载（无 N+1 I/O）；mtime 缓存键避免重复联查。无热点。

### 维度 5：测试覆盖 — PASS
- 见验收 ⑦；覆盖率无独立报告（profile 未要求），以判据覆盖面核验替代——核心路径/边界/错误路径三类齐备。

## AI 代码专项 5 项检查

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | 无——新增测试全部真实临时目录 + 真实文件 I/O，零 patch/mock |
| 2 | 硬编码返回值 | 无——所有判定自输入推导；DEMAND_SOURCE_ZH 为协议常量（正当） |
| 3 | 幻觉 API 调用 | 无——resolve_demand_source/demand_source_distribution/DEMAND_SOURCE_VALUES 均实证存在于 task_priority.py；dataclasses.replace 用于 frozen TaskDep 正确 |
| 4 | 未实现 TODO | 无 TODO/FIXME/placeholder；修订通道为 Coordinator 明示批次裁剪 + 注释锚定（`revision channel: see ADR-021 rework (P1-3)`），非未实现残留 |
| 5 | 过度实现 | 无——三判定函数均任务上下文列明；P2+user-named 门禁为任务规则（Developer 已诚实标注 ADR 缺口并上报） |

## 设计一致性（与 DEC/ADR 锚定比对）

- **D1 裁决（DEC-289①）**：排序键不跨 P 级 ✓ 逐字落地；跨级执法归 Check/发布门（分级执法）✓。
- **窗口协议（Coordinator 注入①/ADR §2.2.1）**：缺省 machine-signal / 非法值 fail-closed / B3 接线点注释（argparse required）三条全落地。
- **修订通道不做（Coordinator 注入③）**：未实现 + 留注释锚定 ✓；resolve 签名因此缺第四参 revision_events（ADR §2.2.2(3) 四参形态）——批次裁剪如实记录（P3-3）。
- **禁硬编码检查编号（Coordinator 注入④）**：provenance_domain.py 全文无 "Check 41/42" 字样，锚定用 ADR §2.2 节引用，docstring 明示「编号随 ADR 返工重编」✓。
- **已知偏差（任务预告，非阻塞）**：INV-1 现实现无 P 级限定（跨级倒挂也 FAIL，`test_cross_level_inversion_is_flagged` 实证当前语义）——较 ADR 稳定节（same-priority FAIL + 跨级 INV-X WARN）更严。见 P3-2 升级提醒。

## Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P2-1 | **P2** | `infra/tests/test_change_triage.py` `DemandSourceStepTests` 类头注释第 4 条 bullet | 注释声称「缺失参数 → 按 legacy（未标）入账 + WARN 披露（绝不静默、绝不误标 machine-signal）」——与实现（缺省 → machine-signal）、同文件测试断言（`test_missing_demand_source_defaults_machine_signal_window_protocol` 明确断言 machine-signal）、ADR §2.2.1 窗口协议第 1 条、Coordinator R0 P1-2 裁定四方相反，系早期方案残留。行为本身三重一致正确（不受影响），但关键协议语义的反向注释会误导后续维护者 | 修正注释为窗口协议语义（缺省 → 保守默认 machine-signal）；可随 B3 接线一并处理 |
| P3-1 | P3 | `infra/change_triage.py` L1173-1174 及 run_triage docstring | 「ADR-021 §2.2.1 无对应条款——已上报 ADR 缺口」陈述：ADR 在途返工文本（ADR-021 L121）已将 P2+user-named 拒绝条款正式收编（标注「FEAT-077 任务规格已实现该条款，本 ADR 正式收编」）。ADR 合入后注释过时 | ADR 返工合入后同步更新该注释（引用 ADR 条款号）；报告义务已如实履行，无行为问题 |
| P3-2 | P3 | `infra/checks/provenance_domain.py` `check_priority_inversion` INV-1 | 已知后续小改（任务预告非阻塞）：现实现无 P 级限定（跨级倒挂也 FAIL），较 ADR 稳定节（same-priority 限定 + INV-X 跨级 WARN 披露）更严。**升级提醒：B3 接线（check-governance box）之前必须随 ADR R1 定稿完成微调**——否则 D1 已知容忍的跨级压序（machine-signal P0 热修排 user-named P1 前）会 FAIL 而非 WARN，可能阻断合法 P0 场景的治理检查（与 §2.2.2 D1「已知容忍」设计冲突） | ADR R1 定稿后按 same-priority 限定 + INV-X WARN 分拆微调；现有测试 `test_cross_level_inversion_is_flagged` 届时同步改写为 WARN 断言 |
| P3-3 | P3 | `infra/task_priority.py` `resolve_demand_source` 签名 | 缺第四参 `revision_events`（ADR §2.2.2(3) 四参形态）——与「本批不做修订通道」裁定一致，非缺陷；修订通道批补参时签名变更，调用方（`_resolve_row_demand_sources`）与测试需同步 | 修订通道实施批次（ADR P1-3 返工）补参时一并处理；B3 接线无需动作 |
| P3-4 | P3 | `infra/task_priority.py` `_resolve_row_demand_sources` | `except Exception → records=[]` fail-open 防御分支无直接单测触发（load_triage_records 自身已吞 OSError/ValueError，该分支覆盖其余异常形态）。ADR §2.4 L2 行语义正确 | B3 接线测试可补 monkeypatch 注入异常的负例；非阻塞 |
| P3-5 | P3 | `infra/task_priority.py` `_triage_records_mtime` | 目录 st_mtime 捕获记录增删（FIX-247 不可变契约下唯一合法变更），不捕获记录文件内容原地篡改（目录 mtime 不变 → 缓存可能 stale）。与既有 archive_index_mtime 同款模式同款边界；原地手改本身违反 immutability（Check 32 面另有执法） | 已知边界记录在案；如需更强保证可改 max(文件 mtime)，代价是每次 stat 全目录——当前规模不值得，维持现状 |

## 硬门槛裁决

| 门槛项 | 阈值 | 结果 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 0 |
| 5 维度全覆盖 | = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐项有结论 |
| 每条发现标注级别 | = 100% | ✅ P2×1 + P3×5 全标注 |
| 设计一致性检查 | 已完成 | ✅ DEC-286(7)/DEC-289 D1/ADR §2.2.1-2.2.4/Coordinator 注入四锚定比对，两处已知偏差均有依据并标注 |
| AI 专项 5 项 | 全部完成 | ✅ 见表 |

## Developer 声明交叉核对（以 diff 为准）

| 声明 | 核对 |
|------|------|
| DEMAND_SOURCES 三值封闭 + 中文映射 | ✅ 一致 |
| run_triage 窗口协议缺省 + 三重 fail-closed | ✅ 一致（exit 2 为 CLI 层映射，B3） |
| record 顶层 +2 键（schema 保持 1） | ✅ 一致（`test_schema_version_stays_one_additive`） |
| _DEMAND_RANK 五值 / 排序键四元组 / resolve 权威链 / 缓存键 / 渲染 src=+分布行+conflict 横幅 | ✅ 全部一致 |
| provenance_domain 三纯函数（INV/发布门/闭环率） | ✅ 一致（session_closure_rate 属任务范围 §3.2.3 B2 面） |
| 红绿 13 红 → 311 绿 | ✅ 311 实测复现（三族 29.174s OK） |
| 全链路演示 user-named 排前带 src= | ✅ CLI 集成测试 `test_triage_json_overrides_missing_row_marker` 实证（FIX-981 排 FIX-980 前 + src=user-named） |

## 遗留项（随批跟进，均不阻塞本批合入）

1. P2-1 注释修正（建议 B3 批）
2. P3-2 INV-1 same-priority 微调（**必须先于 B3 接线**，随 ADR R1 定稿）
3. P3-1/P3-3/P3-4/P3-5（随对应批次自然收口）
