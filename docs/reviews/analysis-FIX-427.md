# Analysis Record: FIX-427 — REL-098 NO-GO 修复批次影响分析（Governance Developer，只读）

- **Task**: FIX-427（TRIAGE-FIX-427，user-named——用户 M-7 NO-GO 终审 + ask 选定先影响分析）
- **执行**: Governance Developer Agent（零文件修改；仓库 diff 为 REL-098 M-1 预存版本面改动；诊断存证 `$env:TEMP\fix427-checkgov.txt` 仓外）
- **日期**: 2026-10-03

## 核心结论（票前提修正——实证）

`check-governance --fail-on-issues` exit 1 的 **5 个计数 issue 真实构成不是票面三类**：

| 计数源 | 数量 | 代码依据 |
|---|---|---|
| Check 13 DEC-ID gaps | 1 | verify_workflow.py L12408-12410 → L16187 计入 all_issues |
| **Check 36 R3 WARN（票外新发现）** | **4** | L17386「violations+warnings 都计数」——RISK-062/063/064/065 缓解引用 DEC-301/302/303（热 decision-log 真实存在的决策编号）被 R3 当任务引用查不到（cross-entity），archive 豁免不触发（热条目非归档） |
| 18d-RB2 ×3 | **0**（不计数） | render_rb2_goal_contract_block docstring L990-991 "Prints only — never counts" + L16404 调用点无增量 |
| 28o module_size archive.py | **0**（不计数） | L16961-16983 "MUST NOT increment all_issues"、fatal_on_error=false、仅 ERROR+fatal 才计 |

算术闭合 1+4=5；全输出零 [FAIL] 行。**票面 13(1)+RB2(3)+28n(1)=5 为数字巧合误归因——只修三类门 5→4 不清零，必须同批处理 Check 36。**

## 类 1：WARN 13 DEC-ID gaps [3, 24, 141, 142, 178]

- 判定：`_find_gaps` L12300-12311（纯数值连续性，**无任何白名单/豁免机制**）；数据源 `get_all_decision_ids` L10163-10178（热 decision-log + archive/decisions/*.md 全文 regex `\bDEC-\d+\b`，不扫 archive/evidence 提及）；WARN 计数 L12408-12410
- 考古（git log -S/-G 全历史）：五编号**从未作为 decision-log 条目存在**（非误删）；DEC-141/142 曾被 REL-067 发布证据真实引用（archive/evidence EVD-894 L47「DEC-141 授权+DEC-142 远端分歧处置」）——幽灵编号（引用过未入账）；DEC-3/24 全历史零痕迹；DEC-178 有 EVD-954「处置项」薄引用
- 方案：**A1 数据回填（推荐）**——141/142 按 EVD-894/REL-067 文档实质回填、178 薄回填、3/24 墓碑条目（「前纪元跳号，考古无对应决策」诚实披露非造假）；纯 .governance 数据（Coordinator 域）M 工作量低风险；**门效果：确定性清零**。A2 检查器白名单（产品码 M-L，长期腐化）。A3 降级 INFO（语义拉伸）。推荐 A1。

## 类 2：WARN 18d-RB2 ×3

- 判定器：`infra/checks/evidence_domain.py` L810-1019（非主引擎）。face① 激活前置 L860-938：goal_face AND ≥1 contract-ready unit；**unit 源 = `_active_execution_packet_tasks()` L13136-13140 = plan-tracker 热任务表 P0/P1 未完成行——不是 flow-unit 注册表**。face② demo 判定 L941-980
- 数据面实证：execution-packets.json packets 为空；热任务表 P1 行均已完成 →「无活跃 P0/P1 unit」= 发布间隙态（真实状态非缺陷）。demo action 常量硬编码 L856-857（"release 0.90.0" 过时）；enforcement 翻转 = RB2_SENSITIVE_BLOCK_ENFORCED L833（出厂 False），翻转属 B-12/B-13 族授权票域（ADR-019 §6 step 4）
- 方案：B1 登记真 unit（为消 WARN 造任务本末倒置，不推荐）。B2 改判间隙态 N/A（产品码+测试 S-M，但触碰 ADR-RB-2 face 语义与授权票边界冲突）。**B3 接受出厂形态（推荐）**——3 行 WARN 是设计内可观测性输出（docstring 明示 factory WARN-grade），发布 checklist/M-2 记录「RB2 WARN 行预期存在、不计数、不阻断」S 纯文档。三方案均不改 exit code。推荐 B3（0.94.0）+ 间隙态语义问题登记 B-12/B-13 backlog。

## 类 3：WARN module_size archive.py 4241（引擎编号 28o；票面 28n 系标签漂移，建议勘误）

- 判定：`check_architecture_health` L20671-20750；schema=`core/architecture-health.json`（L20598 加载）：module_size warn 2000/error 5000/target 1500；**exclusions 登记面 = 同文件 module_size.exclusions（L20682，fnmatch glob+reason，FIX-350 扩到全扫描面 L20699-20715）**
- 两机制语义（代码实证）：**schema exclusions = finding 根本不生成**（L20706 `if not excluded:` 才 append）；**.governance/exceptions.json = annotation-only**（L1102-1111「never changes a severity, byte count, or summary」）→ 永不改 exit code。当前 fatal_on_error=false 下两者对门均无影响
- 方案：**C1 exclusions 登记**（architecture-health.json 加 archive.py 条目 reason 引 DEC+台账，S 配置，WARN 行消失，代价=尺寸看护冻结债转台账显式化）。**C2 二期拆分**（需移出 ≥2242 行 ≤1999；拆分面实读：auto-migration+explain L3257-3818 ~560 → archive_auto.py；resumable evidence 管线 L1269-1500+L1951-2457 ~700 → archive_resumable.py；四族扫描+写守卫 L1523-1950 ~430；legacy 一次性迁移 L648-1268 ~620；FIX-417 先例 6016→4241 已拆 archive_parsing 1435/archive_indexing 870；L 工作量真还债 WARN 自愈；reconciliation §三 #7 已登记 0.95 候选）。C3 阈值上调（弱化看护，不推荐）。推荐：C1（如要求 WARN 输出清零）+ C2 入 0.95；若 NO-GO 语义只是清 exit-1，C2 单独承接 C1 可免。

## 批次建议（票切分/顺序/并行）

- **票 1（P1，数据，清 4/5）**：Check 36 R3 ×4——risk-log RISK-062~065 缓解引用修正（DEC-301/302/303 → 实际承载任务 ID FEAT-081/FEAT-083/FEAT-084 或补任务引用语义）；数据路径 S-M，Coordinator 写 risk-log
- **票 2（P1，数据，清 1/5）**：DEC gaps A1 回填五条目（141/142 实质 / 178 薄 / 3、24 墓碑），Coordinator 写 decision-log，附考古证据（本报告 + EVD-894 引文）
- 票 1 ∥ 票 2 并行（不同文件、均 .governance 数据、无锁冲突）；完成后复跑 `check-governance --fail-on-issues` 应 PASS → REL-098 M-2 解锁
- 票 3（P2，文档）：B3——checklist 记录 RB2 WARN 出厂预期 + 28n/28o 标签勘误 + B-12/B-13 backlog 登记 RB2 间隙态语义
- 票 4（P2，产品，0.95）：C2 archive.py 拆分（§三 #7 升级正式票）；可选前置 C1（视口径）
- **建议先向用户确认 NO-GO 口径**：清 exit-1（票 1+2 即达）vs 清全部 WARN 输出行（另加票 3 的 B3 + C1）——直接决定批次大小

## 边缘发现（如实披露，非本批范围）

① demo action "release 0.90.0" 版本常量过时（可随票 3 顺手动态化，纯文案）；② Check 30 的 13 条 closure WARN、30c 的 2 条、hooks_drift ×4、gds ×2（plan-tracker 202.4KB/evidence 521.3KB）均不计数；③ execution-packets.json 空+无活跃 P0/P1 时 Check 18c/18d/18e 主检查均 PASS（"No active P0/P1" 分支）不阻断。
