# Release Checklist — 0.86.0（REL-082 M-1R / REL-083）

> **M-1R 草案（REL-083，2026-09-20）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/release-checklist-0.85.0.md` 先例。**本文件中的 M-2 数值全部为 2026-09-20 当场实测值**（命令输出原样摘录），未实测项一律标「Coordinator 提交批义务/M-5 期义务/未执行/待回填」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.86.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.86.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.86.0 为内部治理效率版；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本文件不预填。
- **量测维度①不主张**：closure 量测历史相对改善 = `NOT_EVALUABLE`（基线不可评估——无可信历史 trace，R-F10 固定措辞）；本文档量测节仅记录维度②实测值与维度③机制正确性证据，不构成历史改善主张。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.86.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-082（规划）/ REL-083（M-1R+M-2 本票）**（DEC-221 预授权链——M-1 GO 后 M-2；M-1 = FEAT-058 `44831b8`） |
| 承载决策 | DEC-218~224（7 决策；DEC-220 确定性核心公理 / DEC-221 全链预授权 / DEC-222 批 1 归属 / DEC-223 接线契约口径 / DEC-224 write-guard 三条款） |
| 核心范围 | 批 0 M0 契约冻结（FEAT-049）+ 批 1 原子写入器三票（FEAT-051/046/047）+ 批 2 集成窗/closure 纵切/混沌发布门/write-guard 执法（FEAT-055/056/057+FIX-365）+ ⑥ 治理面（7 DEC + 17 EVD）+ M-1 打包（FEAT-058）+ M-1R/M-2 发布面（REL-083 本票） |
| 目标版本下不发布 | write-guard BLOCK 升级（DEC-224 双约束留 0.87）/ locks-release 缺口 / 存储分离 JSON 化 / closure 铺开 / FEAT-044/045 / B-7 index-rebuild / 大表迁移 / 发版管线自举（0.87 候选池）/ FIX-366 引擎两阶段耦合修复 / FIX-364 snapshot 午夜窗 / 任何 RISK 关闭声明 |
| 时间窗口 | 2026-09-19 REL-082 规划闭环 + 批 0/1 随 0.85.0 树入库 → 2026-09-20 批 2 四提交（09:23~13:48）+ M-1 bump（14:52，M-1 GO）→ 2026-09-20 M-1R 四件套 + M-2 门禁实测（本票）→ M-3 双审 → M-4/M-5 另记（taggerdate 权威） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；M-1R 材料由 Governance Developer Agent 起草，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）；升级说明 MUST 携带 B-3/B-4 行为变更（CHANGELOG 0.86.0 段原文口径）；B-3 既有手工路径仍可用（非破坏收敛） |

## Change Inventory（**5 个窗口提交 + M-1R 待落** — `git rev-list --count c2cc7c1..44831b8` = 5，2026-09-20 实测）

> 窗口起点前一位 `c2cc7c1` = `v0.85.0` tag peel（REL-081 M-5 transition 提交，taggerdate 2026-09-20 01:53:52 实测）。批 0/批 1 四提交（FEAT-049/051/046/047）随 `v0.85.0` 树入库（0.85.0 零行为消费——DEC-222 归属裁定），不占本窗口计数；含批 2 全部载荷的完整清单如下（git 时间序）：

| # | commit | 任务 | 关键交付 | 证据 |
|---|---|---|---|---|
| 1 | `a5dec3d` | FEAT-055 | 0.86.0 批 2.0 集成窗——三写入器 dispatch 接线 7 键 + 冻结面 88→95 三重钉（DEC-223）+ archguard regen + 留置八项收口 | EVD-1114 |
| 2 | `a7474e4` | FIX-365 | review-FEAT-054-RELEASE-R0.md L83 ragged row 转义修复——存量 5 项测试转绿 + LRC PASS + 独立扫描 1→0 | EVD-1115 |
| 3 | `7709987` | FEAT-056 | closure-chain 纵切 + 混沌发布门（B-4 根面终结——纯序排器/独立事件日志/effect-based resume/ready-to-commit） | EVD-1116 |
| 4 | `ffcb787` | FEAT-057 | write-guard 行族执法上线 + 超时恢复腿修复（批 2 全清——首活体实证 EVD-1117 被 WARN 精确捕获） | EVD-1117 |
| 5 | `44831b8` | FEAT-058 | **M-1 版本 bump + 候选打包**（24 tracked：手工 5 + 再生 19 + CHANGELOG 0.86.0 段 + 豁免账本 11 行；26 文件 +262/−32） | EVD-1119（机录）；REVIEW-FEAT-058-R0 = APPROVED_WITH_NOTES/0 |
| — | 本票 | REL-083 | **M-1R prep 批（Coordinator 提交后为 candidate commit）**：本四件套 + `core/releases/0.86.0.json`（candidate manifest——**本票锁面外**，Coordinator 按候选打包程序创建并随提交入索引）+ M-2 复跑义务执行 | 本文件 + release-plan |

**版本 bump 平面清单（M-1 = `44831b8` 已执行，EVD-1119 口径）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | **0.86.0** |
| JSON 声明面 / hook 版本行 / canonical 模板标记 / DSH 方言面 / 入口投影 / fixture 面 / `REQUIRED_SNIPPETS` 六锚 | 再生 19（`release-projection --write` 28 面 + entry 双根）+ 手工 5（SKILL frontmatter / 6 版本锚 / 豁免账本 11 行 / CHANGELOG 段 / canonical 标记） | 全部 **0.86.0**（24 tracked——EVD-1119 Reviewer 独立复验） |
| 豁免账本（FIX-361 bump 程序） | `checks/version.py` STATIC_PIN_EXEMPTIONS | bump 时点双重信号如期触发——scan 命中 **11 行新增**（fixture 表行 ×9 + instrument-version fixture ×1 + write-guard 披露措辞 ×1）逐行归因全部登记；0.85.0 期 10 行 dormant 零 stale |
| ledger manifest | `core/releases/0.86.0.json` | **尚未创建**（M-1R 候选打包面——本票锁面外；Coordinator 提交批承载，`lifecycle_state: candidate`，唯一 transition 由 M-5 追加） |
| plan-tracker `工作流版本` | `.governance/`（gitignored） | 仍 0.85.0（**过渡态 WARN**——M-8 收尾由 Coordinator 更新为 0.86.0；check-version-consistency 2026-09-20 实测 1 WARN 在案——本版 verify 唯一预期 WARN） |

## 行为变更（面向用户 —— CHANGELOG 0.86.0 段已载，本表为索引）

| # | 变更 | 任务 | 性质 | 回退通道 |
|---|---|---|---|---|
| **B-3** | 治理行写入路径收敛：受管行族（EVD/DEC/REVIEW/任务状态列/ops 台账）变更**机录优先**——写入器 CLI 为主路径留凭证；write-guard 对无凭证手写行 WARN 响亮披露（exit 0 不阻断——非破坏性执法；BLOCK 升级留 0.87 双约束） | FEAT-051/046/057 | 写入路径收敛（执法姿态 WARN） | 版本级回滚（既有手工路径仍可用——非破坏；feature-flags §2） |
| **B-4** | CLI 步超时分类学 step_unknown：closure-chain CLI 步超时不再笼统失败——分类为 step_unknown 执行态交 effect-based resume 世界核验门控处置（landed=reconcile / NOT-landed=重执行 + replay 兜底互斥双腿） | FEAT-056 | 链内部语义（不改变既有 CLI 对外退出码契约） | 版本级回滚（feature-flags §3） |

## 版本号决策记录（semver 论证——CHANGELOG 0.86.0 段同口径）

- **MINOR（0.85.0 → 0.86.0）**：VERSIONING.md L12「新增 B/C 级自动化能力」——载荷 = 四类新写入器 CLI + contracts.py 契约 MUST 规则扩展 + write-guard 行族全覆盖上线路由（**新增受治理能力面**）；
- **非 PATCH**：L38 口径不适用——主体为新增受治理能力与执法面，非纯缺陷修复；
- **非 MAJOR / Breaking changes = 无**：L11 口径逐项核对不成立——无 MUST 规则删除/重命名、无 governance 文件字段格式变更；write-guard 为 **WARN 姿态上线路由**非门禁硬化（L11 不触发）；B-3 保持手工路径兼容（既有 CLI/记录格式零破坏）；版本号未占用预留（Release Reviewer R0 V5 代验：无 0.86.0 roadmap 行占用、tag 序顺延不跳号——CHANGELOG MINOR bump 依据段同口径，version-plan-0.86.0 §0 Release R1 审定）。

## Candidate Gate Results（M-2 —— 2026-09-20 实测；A 清单 8 项全履行）

| # | 门禁 / 命令 | 结果 | 关键实测值 |
|---|---|---|---|
| 1 | `verify` 全量 | **PASSED**（exit 0） | 全量资产 + 适配器契约同步（6 adapter runtime-verified）+ snippet 面全 OK；**唯一 WARN：plan-tracker `工作流版本` = 0.85.0（expected 0.86.0）→ M-8 收尾更新**（0.81.0~0.85.0 M-1 先例同型过渡态——本版 verify 唯一预期 WARN） |
| 2 | `check-version-consistency` | **PASSED**（exit 0） | 源 = 0.86.0；13 面 + 双入口 marker（AGENTS.md/CLAUDE.md）全一致；1 WARN 同 #1（过渡态）。**静态版本钉豁免账本落库复核（FEAT-058 边缘义务）：11 行（fixture 表行 ×9〔test_task_row_update ×7 / test_closure_chain ×1 / test_triage_write_guard ×1〕+ instrument-version ×1〔test_baseline_metadata〕+ write-guard 披露措辞 ×1）全部行号/token 有效** |
| 3 | `check-injection-budget`（×3 profile，**hard**） | **PASSED ×3**（exit 0） | resident：lightweight **4,216**/6,000 · standard **5,694**/6,000 · strict **5,966**/6,000（与 0.85.0 基线逐位一致）；skill：entry-skill **14,459/16,000** ok（report-only——**R-F4 动态口径 0.86.0 基线当场值**，较 0.85.0 的 14,456 +3 边缘内；version-plan-0.86.0 §5.5 口径履行）；command：3,466/6,000 report-only；`Over budget — gated: none` |
| 4 | `check-projection-sync --fail-on-issues` + `check-entry-bootstrap-sync` | **PASSED ×2**（exit 0） | entry：CLAUDE.md=9,552B/full、AGENTS.md=2,834B/thin（repo-root 与 fixture 同值，profile=standard）；DSH 方言互认 present（3,402B/38L） |
| 5 | `release-projection`（check-only） | **PASS**（issues 空） | source_version = **0.86.0**；projections_checked = **28**；declared legacy snapshots 10（pass） |
| 6 | `check-cross-references` | **PASSED**（exit 0） | 78 文件 / 725 引用——**0 dangling / 0 deprecated / 0 circular**（含本四件套落盘后复核窗口） |
| 7 | `check-manifest-consistency` | **PASSED**（exit 0） | canonical 825 / actual 946（0.85.0 期 813/917 → 本版随批 2 测试与文档面自然增长） |
| 8 | `archguard-ratchet`（R1~R7） | **PASS**（0 violations；raw findings 0） | R1 25,291 ≤ 25,291（only-down）；R2 47 ≤ 47（37 文件）；R3 matrix 12 edges / SCC max 1（unmanaged refs 1 disclosed）；R4 print 1,306 ≤ 1,306；R5 cli keys **95/95** frozen + segments **71/71** frozen（FEAT-055 冻结面 88→95 消费面）；R6 cold import 205 modules（Δ0，advisory）；R7 regen deterministic=True / committed==fresh True |
| 9 | contract-matrix（`contract_matrix/generator.py --check`） | **PASS**（exit 0） | `contract matrix: current implementation matches snapshot (4 faces, zero drift)` |
| 10 | `release-ledger --version 0.86.0 --no-remote` | **FAIL — 预提交态预期**（exit 1；2026-09-20 实测） | 唯一 issue：`core/releases/0.86.0.json: cannot read release manifest: FileNotFoundError`——**candidate manifest 尚未创建**（M-1R 候选打包面，本票 triage `files` 锁面外；与 0.85.0 #9「已 staged 未提交」的 FAIL 形态不同型，如实分述）。**复跑义务**：Coordinator 创建 manifest 并提交后 MUST 复跑（期望 PASS / NATIVE_CANDIDATE）；M-5 tag/push 后 `--remote`（期望 NATIVE_RELEASED；`UNKNOWN`/`BLOCKED` 不得包装为 PASS） |
| 11 | 全量测试套件（`python -m pytest skills/software-project-governance/infra/tests/ -q`，M-1 bump 后全量） | **3,820 passed / 0 failed / 1 skipped / 502 subtests passed（1119.43s ≈ 18:39）** | **0 失败——Reviewer deferred 面复建达标（目标 3,820+ passed/0 failed 精确达成）**；1 skipped = GBK 负控按设计 skip；无先在失败归因义务残留（0.85.0 期 6F 全部收敛：ragged row 族由 FIX-365 转绿、午夜窗 snapshot freshness 未在本轮触发——00:00~02:00 窗外时段复跑，FIX-364 候选仍登记） |
| 12 | 混沌复演（`test_closure_chain.py` 单套件复跑） | **35 passed（40.07s）** | 三边界 kill+resume（commit 失败/push 凭据失败/push 超时 UNKNOWN——隔离 bare 夹具零真实远端副作用）+ 超时恢复腿全绿；**混沌发布门 M-2 MUST 履行**（0.85.0 门禁摘要 #3 的 0.86.0 承诺兑现） |
| 13 | e2e / dsh 隔离冒烟 | **PASSED ×2**（exit 0） | `e2e-check`：source_cli_proxy 6/6 + target_cwd 4/4 + target_fixture 9/9 + contract_only 5 全 OK（4.4s）；`check-dsh-preset-smoke --fail-on-issues`：**isolated preset-session smoke PASSED（real-home writes: 0；temp DSH_HOME 自清）——skill catalog + /governance 手势解析生效**（隔离环境安装冒烟（环境变量重定向至临时目录）通过口径；入口标记 0.86.0 生效验证 = #2 双入口 marker + 本冒烟 skill catalog 解析） |
| 14 | check-release 复合门禁（candidate） | **未执行（Coordinator 提交批义务——如实标注）** | 依赖 `core/releases/0.86.0.json` 在场（release-docs/release lineage 门禁的 manifest 面）+ 安静窗；0.85.0 先例由 M-1R 提交批内执行。本票已实测其可独立复核的核心子面：#1~#13 + release-docs 四件套结构自检（见下节） |
| 15 | M-2 revert 干跑（回滚演练） | **未执行（如实标注——本票无演练义务票面）** | 0.84.0 演练由 FIX-354 专项承载；0.85.0/0.86.0 批内无对应演练票。回滚区间结构核对（双轨锚定 + 两段论证 + 窗口构成披露）已入 `rollback-plan-0.86.0.md` §区间锚定。是否补演练 = M-3 审查/Coordinator 裁决；本票不预填演练结果 |
| 16 | `check-loop-runtime-claims`（LRC gate） | **BLOCKED（semantic_only）— 预算容量越线，如实披露**（exit 1；2026-09-20 实测） | 唯一 finding = `SEMANTIC_BUDGET_EXCEEDED`（stage=extract）：semantic_units **300,701 > max 300,000**（超 0.23%；payload 15.3MB < 32MB 未超）——引擎 **fail-closed 提前 return**（预算超限即拒绝语义分类，绝不假装扫描通过；`verdict_scope=semantic_only`）。**非 claim 违规发现**（findings 零违规项；candidates 925 全量解析完成）。归因：0.85.0 发布当日（2026-09-20 01:45）LRC = semantic PASS + identity PASS（checklist-0.85.0 #11，inventory 4d2f1186…）；当日午后治理活数据自然增长（evidence-log 8,996 units / plan-tracker 1,521 units 等机录行膨胀）使 units 越线——**既有容量趋势问题，非本票四件套引入**（四件套 4 文档不占 units 主导面）。**处置**：容量重定标候选移交 0.87/Coordinator（与 FIX-361/364 同族门禁容量面）；identity 面随 semantic 提前 return 未出账，M-3/提交批复跑时点一并复核 |

**M-2 执行序纪律**（0.85.0 先例沿用）：①安静窗——涉及 candidate 集合枚举的检查 MUST 无并发写盘；②顺序：verify → check-version-consistency → check-injection-* ×3 → check-projection-sync → check-entry-bootstrap-sync → release-projection → check-cross-references → check-manifest-consistency → archguard-ratchet → contract-matrix → release-ledger → 混沌复演 → closure 量测（sandbox）→ e2e/dsh 冒烟 → 全量 pytest（后台先行、终态汇总）；③每个 FAIL 逐项落披露，不以「已知」豁免（#10 ledger FAIL 为预提交态预期——如实归类非豁免）；④tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote`。

## closure 量测首跑（M-2 关键交付——三维验收维度②实测；协议 m0-r1）

> **sandbox 纪律（红线履行证明）**：量测全程在 `%TEMP%\rel083-sandbox` 闭环境副本执行——真实 `.governance/` 全量副本 2,041 文件；**真实治理数据 SHA256 全文件指纹前/中/后三重实测逐位一致（`82360d923293edaa…`，ZERO_WRITE_PROOF=True×2）——真实 .governance 零写入**。协议依据：`benchmarks/closure/protocol.md`（FEAT-049 冻结 m0-r1）+ cases 三路径（`benchmarks/closure/cases/{standard-success,conflict,recovery}.json`）。

### 量测数据总表

| 项 | 值（当场实测） |
|---|---|
| **链全程 LLM 往返计数（维度②）** | **2 次逻辑往返 ≤ 2 达标**——协议 §1 规则 1.1/1.3 口径：①Coordinator 发出推理请求→发起链触发调用（往返 1）；②结构化 JSON 返回→模型再响应确认结果（往返 2）。**链引擎自身零 LLM 往返**（纯确定性序列器——cases standard-success.json measurement 口径）。对照论证：历史手工闭环同工作面需**多次手工交互**（状态翻转/EVD 追加/锁收缩/摘要各需独立人工往返 + 校验往返——机制叙述非量化主张，历史数字未核实；DEC-220 公理语境的「手工路径」；**维度①历史相对改善仍 = NOT_EVALUABLE**——无可信历史 trace 基线，未宣传达成） |
| **链耗时（A 组全程）** | **494 ms**（单命令 run，4 步全通；C 组 resume 腿 259 ms） |
| **事件日志行数** | journal 总计 **19 行 / 3 closure units**（MES-001 链 5 + VAL-861 链 7 + VAL-862 链 7）；**每 unit cas_version 严格单调 +1 实测通过**（5/5、7/7、7/7——protocol §A expected「seq 严格单调 +1（复用 loop_event_log 单调性管道）」按 unit 判定口径） |
| A 组【standard-success】 | 票 VAL-861（triage→行→锁→链全真实驱动）：**status=ready**、4 步全通（flip-completed completed / append-evidence completed / shrink-locks reconciled〔zero_locks 锚——VAL-861 的锁 acquire 被 MES-001 先占锁结构化拒绝 exit 2，M7.6a 并行安全语义意外实证；链对锁缺失如实报 reconciled 非假报成功〕/ ready-to-commit completed）+ commit message 建议 + do_not_stage 清单（closure-events.jsonl / closure-locks/ 自指约束）；**effects_exactly_once**：tracker 行翻转恰 1 条〔op-be9dbbde…〕、EVD-1120 恰 1 条；**zero_manual_intervention** ✓（cases expected 四项全对齐） |
| B 组【conflict】 | 三探针谱系（写入器层直驱，副本内）：① **cross_record_violation**（MES-001 链 append 步——`governance_id:MES-001` 触发五类型引用机检：MES 非合法 id family → 结构化拒绝 exit 2 → 链层 step_failed/manual_intervention/**blocked 停链不盲重试**——拒绝语义与 conflict.json `on_conflict` 口径一致）；② **revision_conflict**（VAL-861 过期 `--expected-revision 12345` → `content-level CAS: expected 12345 != observed 1125763796…` + observed_revision 返回 + "a CAS conflict never auto-rebases"——**与 case 声明逐字一致**）；③ **operation_id_conflict 全谱系**：post-write 拒绝（骨架缺失 validation 拒绝但效果已落盘 EVD-1121——effect-first window 实态）→ 同 id 重试 **world_recovery** 幂等收敛（补 receipt、**EVD-1121 恰 1 条零重复**）→ receipt 在账后再变载荷 → **operation_id_conflict**（exit 2，disposition=conflict，"a stored result is never reused for a different payload" + observed_revision 返回）。**case 判定四项全过：结构化拒绝 ✓ / 无静默换版重试 ✓ / 重判后收敛 ✓ / 最终一致 ✓** |
| C 组【recovery】 | 票 VAL-862：受控 fault 注入（`CLOSURE_CHAIN_TEST_FAULT_POINTS`——测试专用握手协议，生产零暴露）于 **post-step-effect:append-evidence** 边界：append 效果落盘（EVD-1122 在世界）→ 进程 hard kill（marker 0.5s 出现后 Stop-Process，不写 release）→ **单命令 resume（`run --closure-id` 同 id）259 ms → ready**；flip probe 世界核验 satisfied=True 跳过重执行、append-evidence **reconciled（零重复追加——EVD-1122 恰 1 条）**、shrink-locks reconciled、ready-to-commit completed。**case 判定全过：effect-based 恢复（查世界不信日志）✓ / 零重复追加 ✓ / 零丢失 ✓ / 零人工修复 ✓**；三边界 kill+resume 完整覆盖由 #12 混沌 35 passed 承载 |
| 协议记录义务 | 本节即 runs 记录的 EVD 引用面（protocol §5：`runs/` 由创建批落盘 `.gitignore` 本地保留；EVD 记 run-id 与摘要——Coordinator 落账时引用本节 + closure-id 三元组：`closure-45773c16…`〔A〕/`closure-375ec112…`〔B 素材〕/`closure-01234567…`〔C〕） |

### 量测边缘观察（如实登记——不阻断，移交 Coordinator/0.87 候选评估）

1. **journal step_failed 事件 detail 为空**：`_execute_external_step` 生成 detail 文本（"external action failed (exit 2)"）与 stderr_tail，但最终 envelope payload.detail 实测为空串——审计面细节丢失（事件分类/exit_code/disposition 正确保存）。候选：事件构造链 detail 透传核查（0.87 候选）。
2. **change-triage 词表 vs governance id family 词表不一致**：change-triage 接受 `MES-001`（PREFIX-NNN 校验通过），而 evidence-append 引用机检 id family 封闭词表（AUDIT/DEC/EVD/FEAT/FIX/RECO/REL/REQ/REVIEW/RISK/SYSGAP/TRIAGE/VAL）不含 MES ⇒ triage 可入账但其票不可被 evidence refs 引用（量测首跑即实证）。候选：词表对齐或 triage 前缀约束扩展（0.87 候选）。
3. **写入器 conflict 类结果 exit code = 0**：illegal_transition/revision_conflict 以 `mode=result` 输出且 exit 0（cross_record_violation/operation_id_conflict 为 exit 2）——链层 blocked_exit_codes 以 exit code 分类时对前者按成功消费（实际由 probe 主导兜底）。候选：退出码语义统一评估（0.87 候选）。
4. **flip/append 步 payload 中 probe.satisfied=false 为执行前观测**（resume 判定用 pre-probe，执行后不复跑）——行为解释非缺陷，登记避免后续误读。

## 三先在失败归因复核（M-2 义务状态——0.85.0 遗留面收敛核对）

> 0.85.0 M-2 期 6 失败的 0.86.0 终态：①review_doc_claim 族 5 项——ragged row 即时成因已由 FIX-365（`a7474e4`）修正转绿；②`test_snapshot_freshness_recent_is_fresh` 午夜窗口时间敏感——**本轮全量 pytest（日间时段）0 失败，未触发**；FIX-364 候选（fixture 以引擎同口径取日期粒度）仍登记在案。**本轮实测 0 失败 ⇒ 归因复核义务无残留对象**（如实记录：未在午夜窗复跑，该单点不构成通过性声明的一部分——0.85.0 #14 方法论保留供 M-3 参考）。

## 披露清单（如实披露项 —— 不得写成通过）

① **candidate manifest 缺席（本票锁面外）**：`core/releases/0.86.0.json` 未创建 → `release-ledger --no-remote` FAIL（#10）+ check-release 复合门禁未跑（#14）。**收口 = Coordinator M-1R 提交批**：按候选打包程序创建 canonical manifest（`canonical_json_bytes`——NFC/sorted/compact/trailing-LF）+ 四件套同批提交 → 复跑 ledger（期望 NATIVE_CANDIDATE PASS）+ check-release（candidate）。0.85.0 先例为三件套+manifest 同 commit（602a794）；本票 triage `files` 仅锁定四件套，manifest 面按锁面纪律移交。

② **plan-tracker `工作流版本` = 0.85.0 过渡态 WARN——仍开放**：M-8 收口（Coordinator），#1/#2 实测在案。

③ **引擎两阶段耦合缺陷仍在（FEAT-053 P2-1 → FIX-366）**：projection.py 单遍 plan——byte_copy 源 = 同批 transformed 目标时必回滚（fail-closed 无静默腐坏）；本版 M-1 沿用 FEAT-058 同款绕开手法。修复票 0.87.0 在案（triage 已入账）。

④ **8 次手工行编辑事故披露链（CHANGELOG 0.86.0 段披露①转引）**：窗口内 8 次手工行编辑事故全部被 write-guard/审查链捕获并制度性终结（能力→执法跨越，EVD-1117）——首 WARN 精确捕获手写行 → DEC-224 裁定转机录路径 → 首机录 EVD-1118 经 evidence-append 落账（写入器时代三活体实证）。数字演进如实注记：DEC-220 期记录 5 次（3 行锚定+1 锁 schema+1 入账截断）→ session-snapshot 期 7 次（全捕获）→ EVD-1117 第 8 次（首 WARN 捕获）为终值口径。

⑤ **豁免账本双账本状态**：版本钉豁免 **11 行**（FEAT-058 bump 程序）——#2 复核零 stale；LRC 豁免账本（`core/loop-runtime-claim-exemptions.json`）4 条维持打开（历史记录性文本豁免）——本四件套按记录性/非主张措辞起草，不新增 LRC 发现。

⑥ **量测边缘观察 4 项**（见量测专节——detail 透传/词表不一致/conflict 退出码/pre-probe 语义）：均不阻断本版门禁，0.87 候选评估。

⑦ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张；量测维度① NOT_EVALUABLE 未宣传达成。

⑧ **回滚安全弱化面**：回滚到 0.85.0 即整体恢复——(a) B-3 机录路径收敛消失（write-guard 对账面回退，手工直写无守卫——0.85.0 态）；(b) B-4 step_unknown 分类学消失（CLI 步超时回退笼统失败——恢复可靠性弱化）。两者均无 flag 级中间态（版本级回滚，rollback-plan §1/§5）。

⑨ **LRC semantic 容量越线（#16）**：semantic_units 300,701 > 300,000（超 0.23%）→ 引擎 fail-closed BLOCKED——**非 claim 违规、非本票引入**（0.85.0 发布当日活数据增长越线）；容量重定标候选移交 0.87/Coordinator；identity 面未出账待复跑。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 规划确认**：REL-082 双半面规划双审 R1 通过；DEC-220/221 生效（EVD-1102）
- [x] **批 0/批 1/批 2 载荷**：八票全闭环（含 NEEDS_CHANGE→R1 转化四票；0 unresolved blockers）
- [x] **M-1 版本 bump（全平面）**：`44831b8`（FEAT-058）——24 tracked 面 + 投影 28 面 + CHANGELOG 段 + 豁免账本 11 行（EVD-1119）；**M-1 GO**（REVIEW-FEAT-058-R0 APPROVED_WITH_NOTES/0）
- [x] **M-1R 发布材料**：本四件套（REL-083 锁面 expected-new）
- [x] **M-2 快速门禁**：#1~#13 实测（2026-09-20；FAIL 项已披露——#10 预提交态预期）
- [x] **M-2 量测首跑**：closure 量测 sandbox 零写入完成（三维口径数据齐——往返计数 2/耗时/事件行数/cases 三路径一致性）
- [ ] **M-2 复合门禁（Coordinator 提交批）**：candidate manifest 创建 + 提交 → 复跑 `release-ledger --no-remote`（期望 NATIVE_CANDIDATE PASS）+ `check-release --version 0.86.0 --require-changelog --lineage-mode candidate`（SPG_RELEASE_GATE_TIMEOUT=600）
- [x] **M-3 前置材料**：本四件套就绪，供 Release Reviewer / Design Reviewer 双半面审查（含回滚区间双轨裁决输入）
- [ ] **M-3 双半面审查**：Release Reviewer + Code/Design Reviewer（按变更面）；review-record 机录；复审必达
- [ ] **M-4 go/no-go**：DEC-221 预授权形态——Coordinator 呈现，门禁不予放弃
- [ ] **M-5b transition/tag**：candidate → released（单父 transition）+ tag `v0.86.0`（peel = transition commit）+ push——Coordinator 面
- [ ] **M-6 released 门禁**：`check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote`
- [ ] **M-7 push**：master + tag 原子推送
- [ ] **M-8 提交 + 收尾**：commit message 含 REL-082/REL-083；plan-tracker `工作流版本` → 0.86.0（消 #1 WARN）；session-snapshot 刷新；`archive.py migrate --auto --dry-run` 触发检测 → `check-archive-integrity` PASS；证据行落账

## M-8 收尾义务（Coordinator 面——本票不执行）

- [ ] candidate 提交（四件套 + manifest 入索引后）→ 复跑 `release-ledger --version 0.86.0 --no-remote`（期望 NATIVE_CANDIDATE PASS——刷新 #10）+ check-release candidate（刷新 #14）
- [ ] plan-tracker：`工作流版本` → 0.86.0；REL-082/REL-083 行状态更新；0.86.0 路线图行 → 已发布（待 tag 后）
- [ ] session-snapshot 刷新（含可解析 session_date）——Check 28c hot fact source 面
- [ ] hooks_drift 一次性重装提示：`cp "<plugin_root>/skills/software-project-governance/infra/hooks/"* .git/hooks/`（DEC-213④）
- [ ] 归档触发检测与迁移（ADR-006/007；完整性失败阻断发布完成）
- [ ] 量测 EVD 落账（引用本文件量测专节 + protocol §5 runs 记录规格）
- [ ] 本披露开放项收口：plan-tracker 工作流版本（M-8）/ candidate manifest + ledger 复跑（提交批）/ 量测边缘观察 4 项 → 0.87 候选 triage

---
*REL-083 M-1R 草案冻结（2026-09-20，Governance Developer Agent 起草；同日 M-2 实测回填 #1~#16 与量测专节）。事实基线：5 提交窗口取自 `git log`/`git rev-list` 实测；门禁数值取自 2026-09-20 当场命令输出（A 清单 8 项全履行）；量测数据取自 sandbox 副本首跑当场记录（真实 .governance 零写入——SHA256 三重一致证明在案）；B-3/B-4/0.87 候选池取自 CHANGELOG 0.86.0 段（`44831b8` 冻结版）；豁免账本取自 `checks/version.py` STATIC_PIN_EXEMPTIONS 实读。未实测项（candidate 提交后 ledger/check-release 复跑、M-5 revert 演练、transition/tag、released 态门禁）一律标「期义务/未执行/待复跑」，不预填。*
