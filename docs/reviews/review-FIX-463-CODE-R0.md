# CODE R0 独立审查报告 — FIX-463 决策前提失效器

- 审查对象：未提交工作区 diff vs HEAD=9474310（12 修改文件 + 新模块 premise_tracker.py；decision_repository.py 锁内零改动〔设计即如此〕；另 hooks/commit-msg 与 test_hooks.py 为会话暂停 WIP 指纹，非本票面，逐项复核未动）
- 审查人：Code Reviewer（独立，只读；可运行验证命令）
- 日期：2026-10-24
- 结论行见 L12。

FIX-463: APPROVED_WITH_NOTES (unresolved_blockers=0)

## 1. premise_status 聚合 / review 基线重置语义（核心）— 通过

- 纯函数三态正确：未越阈不浮出 / 越阈浮出且关联任务标「依据失效」 / 重审后恢复压制。测试钉扎：`test_premise_status_three_states`（store 侧）+ TPA 四测（standing 无段渲染 / collapsed 浮出带 related / rereviewed 恢复 / 无数据默认报告不变）。
- review 语义 = 取最新 `premise_reviewed` 事件的 sequence，仅聚合其后 count 事件——历史行零改写（append-only 纪律保持；重审=计数基线自然重置）。
- 坏行 fail-closed：`load_events` 对畸形 JSONL 行抛 ValueError 且带 file:line 定位；`premise status` 捕获后 refused exit 2（L476-482 实读）。
- 幂等双层真实：op-id replay 通道 + 同 (refs,total) count 元组 noop——代码实读（append_event 先查重再落盘）+ store 侧 `test_premise_is_part_of_the_idempotency_key` 证明 premise 参与 decision-append 幂等键。
- 原子写 + 回滚：temp+os.replace；写后 reload 校验（含「原文无尾换行则拼接破坏行」场景——reload 解析失败 → 恢复原文 → refuse，方向安全）。

## 2. bypass 计数规则 v2 与 ±1 方向论证 — 通过

- 规则三件套实读：`--no-verify` 字面 + 行内 hook 语境（排除纯提及行）+ 否定窗口（不/无/未/没/避免/禁 前 8 字符）+ 次数枚举（中文数字/阿拉伯数字取行内最大）。
- 合成用例钉扎：披露行(1)+复发行(2)=3；否定行/非 hook 行/反事件行全部排除（`test_bypass_row_shapes_and_exclusions`）。
- 真树实证（本审查独立复跑）：`premise count --decision DEC-368 --observable bypass_count --source auto --dry-run` → `total=4, refs="L2972(+1); L2973(+1); L2979(+2)"`——逐行可溯；±1 歧义=交叉引用行（EVD-2146 复述 EVD-2145 同一事件），代码注释与测试注释双处披露；**验收底线 ≥3 两处测试断言**（验收用例 L2006 + 独立 `test_live_tree_bypass_floor` L2053）。方向论证成立：把歧义行计入=更早浮出（fail-loud），漏计才是无界静默腐烂方向。
- 验收用例 DEC-368② 只读演示合规：合成 DEC-900 声明 + 真树 total 事件 → collapsed 判定真；真树 decision-log 未动（`premise status` 实跑 collapsed=[]——无真实声明，空闲面正确）。

## 3. R5 2b 段登记完整性 — 通过

- quickscan_registry SegmentSpec("2b", "risk", decision-log.md + premise-events.jsonl) / registry `_SEGMENT_LOADERS` ("2b", verify_workflow.check_decision_premise) / FROZEN_CLI_KEY_COUNT 108→109 与 FROZEN_CHECK_SEGMENT_COUNT 73→74 —— 三方一致，合同套件（test_registry + test_contract_matrix）独立复跑 OK 佐证快照三方一致。

## 4. TPA 输出层语义 — 通过

- collapsed_premises 为 PriorityReport 新字段（default 空 tuple——无声明零影响有默认报告不变测试钉扎）；浮出段 active-defect 姿态 + related 行「依据失效」标注（不误伤无关行——浮出测试断言 related 精确匹配）；纯函数契约保持（events/declarations 数据注入，函数内零读取）。
- 缓存守卫正确：report_text 依赖 premise-events（append-only 流）→ mtime 捕获 append/增删——`premise_events_mtime` 注入 run_cli_analysis。

## 5. Check 2b WARN 段 — 通过

- check_decision_premise 空闲面：缺 decision-log 声明/缺事件文件均不抛错（真树实跑 collapsed=[] idle）；check-governance 渲染块读该函数（verify_workflow diff 实读），WARN 语义=已崩未重审（与 Check 2 风险过期同族）。

## 6. 合同链与 regen — 通过

- R1 28275→28366（+91/-0 全归因本票，ratchet 注释七块+15 提取分解）；R4 1376→1383（+7 Check 2b 渲染与收据 print，FACTS_PRINT_TOTAL=1383 冻结）；R6 210→211（premise_tracker stdlib-only 冷面 +1，FEAT-096/097 先例同构）。
- **N1 rider 已落地**：FIX-462 子分解注释补列（`[N1 correction, REVIEW-FIX-462-R0]` 标记在案），净数 28275 不变、锚差钉扎语义保持。
- test_archguard_ratchet 断言 anchor_loc=28366 与字面量同步；三合同套件独立复跑全 OK。

## 7. 安全 / 纪律面 — 通过

- decision_repository.py 零改动（status 无此文件——verbatim 原则保持，premise 走尾注）；decision-append 校验（枚举闭集/正整数/bool 排除/双参数同行）。
- Developer 零 .governance 写入：premise-events.jsonl 不存在（dry-run 后 Test-Path=False）；governance-write-guard PASS 0 issue。
- WIP 指纹逐项复核：commit-msg 742/1 + test_hooks.py 855/2 与冻结态一致，零触碰。
- register 类比安全：premise 命令只写事件流文件，不触碰 checks/version.py 台账（pin 面 6 无新豁免）。

## 8. 独立复跑汇总 — 全绿

| 门 | 结果 |
|---|---|
| test_governance_store.py（含 premise 通道/三态/adapter/验收用例） | 123 OK, exit 0 |
| test_task_priority.py（含 premise 四态） | 186 OK, exit 0 |
| test_registry / test_contract_matrix / test_archguard_ratchet | 全 OK, exit 0 |
| verify_workflow 全量 | **PASSED**, exit 0, [FAIL] 计数=0 |
| governance-write-guard | PASS, 0 issue |
| premise --help / status / count --dry-run | 全 exit 0；dry-run total=4 零写入 |

## Notes（非阻塞 N1-N5）

- **N1（语义缝隙，0.100 候选）**：auto 源 total 为全史累计——重审后再跑 `premise count --source auto` 会把重审前的历史事件再次计入并可能立即再崩（本审查推演；事件级语义本身正确且有测试钉扎）。方向有界安全（fail-loud、浮出非阻断）；建议 0.100 在 review 事件中存 `reviewed_at_total` 基线，status 聚合时按基线差值计。
- **N2**：bypass ±1 交叉引用行计入（4 vs 3）——已双处披露且底线 ≥3 断言；维持 fail-loud 方向正确。
- **N3**：面数口径：代码面=12 修改+1 新模块（派单语「14 文件面」若含 runtime 工件 premise-events.jsonl 或锁内零改的 decision_repository.py 则账实相符，无缺陷）。
- **N4**：否定窗口为行级跳过（非出现级）——保守方向（漏计可能），被 ≥3 底线断言钉住下界；与 EVD-2145 hook 缺陷同族但方向相反（安全侧）。
- **N5**：`premise review` 的重审权在用户（设计明示）——CLI 允许任意调用方落 review 事件；当前治理纪律下可接受（append-only 可追溯），0.100 可考虑 review 事件要求 refs 佐证。

## 审查边界声明

只读命令 + 仅写本报告文件；未改代码、未碰 .governance、未动 git/WIP。
