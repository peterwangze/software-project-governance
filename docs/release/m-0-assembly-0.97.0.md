# M-0 版本面组装评估报告 — 0.97.0（REL-101）

- **版本**: 0.97.0 · **评估时点**: 2026-10-09（+0800） · **状态**: **M-0 组装评估完成（GO 建议·有条件——条件见 §7；M-1 版本面 bump 待 Coordinator 派发执行）**
- **主题**: 次版本线：治理开销优化承载批（Governance Overhead Optimization）——DEC-146 升级批（Check 30c WARN→FAIL 执法生效版）+ Coordinator 开销削减（M7.8 协调开销纪律）+ 审查链成本收敛（delta 复审/批量审查）+ 子代理预算护栏（execution-packet budget）
- **版本定义**: 0.96.0→0.97.0 MINOR bump（TRIAGE-REL-101 用户立项 2026-10-09「0.97.0 组装立项（推荐）」；版本路线图 L205 0.97.0 行既定；载荷四票全 committed）
- **执行角色说明**: 本报告由 **Release Analyst**（发布评估角色）受 Coordinator 派发起草（REL-101 M-0 评估项）；机器事实全部取自本会话实跑命令输出（§2 逐条记录）与治理台账实读（EVD/REVIEW/DEC/plan-tracker/task 行/git log）。全程只读产品面——不做版本 bump、不改产品代码、不写 `.governance/`、不 git commit；唯一写入 = 本报告文件。
- **仓库时点**: master@602dc79，与 origin/master 同步（无 ahead/behind），工作区干净；载荷窗口 = `v0.96.0（tag 对象 f73bba4 → commit 325289f）..602dc79`，共 6 commits：`1b3636f`（REL-100 M-8 发布终态回填）+ FEAT-089 链 3 commits（`c9dc84f` 本体 + `a4c73b8` DEC-326 rider + `af8fba0` 收口治理面）+ 治理开销批 2 commits（`aca1fe4` 三票本体 + `602dc79` 收口修复）。

---

## 1. 载荷一致性核对（四票 vs 版本行 vs 路线图）

### 1.1 四票状态实读（plan-tracker L80~L84 票行 + git log 实测 + 台账锚）

| 票 | 标题（摘要） | commit（实测） | 证据锚 | 审查锚（终态） |
|---|---|---|---|---|
| FEAT-089 (P1) | DEC-146 升级批——Check 30c 豁免清单载体 + WARN→FAIL 升级路径兑现（V6d 收紧 + 不可伪造 JSON 侧记录 + escalation 判定面 coverage 477/479 vs honored 479/479×23 releases） | `c9dc84f`（本体）+ `a4c73b8`（DEC-326 rider：archguard regen R1 27866→27895/R4 1371→1375/R7 恢复）+ `af8fba0`（收口治理面） | TRIAGE-FEAT-089 + EVD-1349（交付）+ EVD-1348（0.96.0 released 门禁终局）+ RECO-FEAT-089 | REVIEW-FEAT-089-R0 **AWN/0**（2026-10-07；报告 `docs/reviews/review-FEAT-089-CODE-R0.md` 实存在位） |
| FEAT-090 (P1) | Coordinator 开销削减——M7.8 并行优先派发 + 禁睡眠等待 + 健康检查事件化 + 热路径单源（governance-bootstrap 唯一合法读取路径） | `aca1fe4` + `602dc79`（收口修复：M7.8.3 冷面归档路径规范化，Check 12 dangling 消解） | TRIAGE-FEAT-090 + EVD-1350（分析：session-f3f46901 全事件流归因）+ EVD-1351（交付）+ EVD-1352（用户影响分析） | REVIEW-FEAT-090-R0 **AWN/0**（2026-10-09；批量审查——FEAT-091 派发协议首用；报告 `docs/reviews/review-FEAT-090-092-CODE-R0.md` 实存在位） |
| FEAT-091 (P2) | 审查链成本收敛——delta 复审注入面 + 批量审查派发 + review-record --scope/--delta-base + 审查报告摘要注入 | `aca1fe4`（同批归并交付） | TRIAGE-FEAT-091 + EVD-1351（同批归并） | REVIEW-FEAT-091-R0 **AWN/0**（2026-10-09；批量审查） |
| FEAT-092 (P2) | 子代理预算护栏——execution-packet --budget max_steps + 检查点拆分语义 | `aca1fe4`（同批归并交付） | TRIAGE-FEAT-092 + EVD-1351（同批归并） | REVIEW-FEAT-092-R0 **AWN/0**（2026-10-09；批量审查） |

**结论：四票全 committed（git log 实测五哈希在位：c9dc84f/a4c73b8/af8fba0/aca1fe4/602dc79），审查链全终态（AWN/0——FEAT-089 单轮深审 + FEAT-090/091/092 批量审查单轮），与 REL-101 任务行（L84）调度载荷一致。** 附注（如实披露）：FEAT-089 行状态列形态为「🆕 (2026-10-07——…本日勘正为 ✅ committed 锚，前续 triaged/dev/review 无 receipt 系行插入词汇缺口披露)」——勘正锚在位，交付事实由 git+EVD-1349 认定（DEC-275(3) 口径：以 git+EVD 认定交付，不凭状态字样）。

### 1.2 路线图核对（plan-tracker L205 版本行）

- 0.97.0 行在位：**规划（REL-101 triaged 2026-10-09——载荷四票 committed：FEAT-089 + FEAT-090/091/092 治理开销优化批）**；发布日期列=「未定（M-0 后定）」；约束列=「M-0 前置评估项：strict 注入余量 28tok / 预存失败面核销（M0Fixture pin 重定基后核实）/ DEC-327 契约段预算升档随版披露」——**本报告即三项前置评估的兑现载体**（§3/§4/§2.4）。
- 包含任务列核对：FEAT-089(P1✅), FEAT-090(P1✅), FEAT-091(P2✅), FEAT-092(P2✅), REL-101(P1 🔄 triaged)——与 §1.1 实读一致；REL-101✅ 待 M-8 收口回填（发布链票自身，先例同构）。

### 1.3 需求面对照

- **治理开销优化（session-f3f46901 实测基线）**：✅ 承载——实测基线（EVD-1350：主 103.65M + 子代理 552.3M / 35 次 Start-Sleep≈2.9h / 审查链 31% / 快路径 1 次 vs 慢路径 42 次）→ FEAT-090/091/092 三票针对性交付（M7.8 三契约 / delta 复审+批量审查 / budget 护栏）；预期收益台账（EVD-1352）：省 ~2.9h/会话、检查 42→约 6 次、重复读 20→0。
- **DEC-146 升级路径义务（②③④）**：✅ 全清偿（EVD-1349：豁免登记非补录/历史行零改写/V6d 收紧/侧记录 sha256 钉清单）。

---

## 2. 门禁现状实测（本会话逐条实跑记录）

> 约定：全部为只读评估命令；实测时点 = master@602dc79（bump 前）；输出逐条如实记录，FAIL 不修（修复属后续 M-0 裁定/发布链动作）。注：`check-release` 任务原文语法 `--mode candidate` 不存在（unrecognized arguments，exit 1 首跑实录），已按 0.96.0 先例正确语法 `--lineage-mode candidate` 复跑——如实记录。输出中 UTF-8 box-drawing 字符在 GBK 控制台显示为乱码伪影（鈹�），语义判读不受影响。

### 2.1 `check-governance --summary-only`

**实测：8 issues（`--level strict` 全展开见下）——无产品缺陷 FAIL，唯一 FAIL 族 = REL-101 执行包缺失。**

| 类别 | Check | 内容 | 归因 |
|---|---|---|---|
| FAIL×6 | 18c/18d/18d-RB2/18f×2/18i | `REL-101: missing execution packet`（六条同根：执行包未落盘） | **流程时序态**——REL-101 执行包属 Coordinator M-1 前置动作（`execution-packet --write` 后消解）；非本批产品缺陷 |
| WARN | 2 | Risk Staleness：2 stale risk(s)（>7 天） | **既有基线** ✓（与任务预期「风险过期×2」一致） |
| WARN | 18d-RB2×3 | 宿主激活前置未满足（TO_BE_DEFINED 占位穿透目标层）+ demo action BLOCK/WARN（enforcement off——授权票翻转前不拦截） | 既有形态（与 REL-101 执行包缺失同根 + 既有授权态） |
| WARN | 28n×8 | closure_chain.py 3672 / _run_probe / _run_locked / dsh_compat.py 2165 / governance_store.py 2708 / _decision_append_json / loop_gate_processor.process_gate_result / loop_migration.py 3297 | **既有债务基线** ✓（0.96.0 m-0 §2.2 遗留披露的 28n 预存组——session-snapshot 观察池「closure_chain 拆分」在案，非本版载荷） |
| WARN | 28q×1 | hooks_drift: prepare-commit-msg | 既有 |
| WARN | 28s×3 | plan-tracker 213.2KB / evidence-log 524.2KB / decision-log 200.7KB（治理数据体量） | 既有（归档触发检测属 M-8 面持续动作） |
| WARN | 30×13 | closure WARN(s) | 既有 |
| WARN | 30c×42 | undated-record WARN(s)（V6d tightening） | **本批引入（FEAT-089 V6d 收紧）但属台账在案的接受基线**——EVD-1349 原文披露「V6d WARN×42（rows 2+files 40 生效日前手写报告）= DEC-146③ 接受基线不计入」；实测 42 与台账数字**精确一致** ✓ |

**Check 12 归零确认** ✓：输出无 Check 12 相关 issue（602dc79 收口修复生效；`check-release` 内 cross-references PASS 佐证）——与任务预期一致。

### 2.2 `check-release --version 0.97.0 --require-changelog --lineage-mode candidate`（候选门面）

**实测：Result: FAILED - 5 issue(s)——三项 FAIL 全部为 M-0 时点预期态（发布链自身待做项），无产品缺陷。**

| 门面 | 结果 | 归因 |
|---|---|---|
| release docs | **FAIL**：checklist / feature-flags / rollback-plan 三件 0.97.0 版缺（3 issues） | M-4 组装面产物（0.96.0 先例同构时序——三件套随 M-4 落盘后消解） |
| execution gates → governance health | **FAIL**（exit=1，8 issues） | 即 §2.1 的 REL-101 执行包族 + WARN 基线——Coordinator 落盘执行包后回归基线态 |
| changelog | **FAIL**：`## [0.97.0]` 段缺（1 issue，`--require-changelog` 显式要求） | M-1 CHANGELOG 0.97.0 段（bump 后消解） |
| **强正面（全 PASS）** | version consistency / release fact source / hot fact source / runtime readiness matrix / first session measurement / governance pack status / **provenance release gate** / sd integrity / agent adapters（六 adapter static runtime-verified）/ projection sync / cross references / archive integrity / release lineage（candidate）/ gate sequence for release / **one dot zero blockers** / governance exceptions / loop runtime claim gate（semantic+identity PASS, 1191/1191 parsed）/ **dsh upgrade regression（隔离 DSH_HOME 冒烟 exit=0）** | 含 **verify exit=0 / e2e check exit=0 / unit tests exit=0** 三执行门全绿——**全量测试面在 HEAD 绿**（§2.4 契约族 + EVD-1351 全套件 4757P/1S 台账互证） |

### 2.3 `check-injection-budget`（三 profile）

**实测：三 profile 全 PASS——lightweight 4416 / standard 5899 / strict 6172 ≤ 6200（resident hard gate）；与 EVD-1351 台账「4416/5899/6172」逐值一致** ✓。

- **strict 面**：`Result: PASSED — resident injection set 6172 tok <= budget 6200 tok`（headroom **28 tok**）；**`[FROZEN] resident headroom 28 tok < 100 — freeze line ACTIVE (ADR-021 §2.1 acceptance 5): no injection-surface growth without an equal same-commit shrink`**——冻结线活体生效（居民注入面任何增长需同 commit 等量收缩）。
- M1+M2 combined 342 ≤ 370（hard，per-surface scope DEC-291）✓；skill 级 15704 ≤ 16000（report-only）；command 级 3562 ≤ 6200（report-only）；over-budget gated/report-only 均 none。

### 2.4 `pytest test_contract_matrix.py + test_contracts.py -q`（预存失败面核销核实）

**实测：184 passed / 0 failed（75.54s）——契约族全绿。**

- **test_contracts M0Fixture pin×1 失败：已消解** ✓（FEAT-091 重定基生效——EVD-1351「M0 pin 重定基复算匹配」台账互证；DEC-327 伴随事实「M0 fixture pin 重定基（behavior-protocol [522,568]/SKILL [225,232]，rebaseline.last 记录三票授权与回退联动语义，prior 链保留）」）。
- **contract_matrix×3 快照漂移：已不在（0 failed）** ✓——0.96.0 m-0 §6 披露的「agent_locks/plan_tracker/write 面 result_shapes 漂移」在当前 HEAD 实测归零（.governance 运行态与快照对齐；check-release 内 projection sync PASS 佐证）。
- 结论：**REL-101 任务行所列「预存失败面核销」两项前置评估均核实通过**；契约族不再是 M-2 披露面候选。

### 2.5 `archguard-ratchet`（七轴）

**实测：`Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green`，anchor 27934** ✓（与 EVD-1351「archguard 七轴 PASS（anchor 27934 sanctioned regen）」台账一致——承接 FEAT-089 rider 27895 → 治理开销批 27934 的 sanctioned regen 链）。

| 轴 | 结果 | 值 |
|---|---|---|
| R1 | PASS | mainfile loc 27934 ≤ anchor 27934（only-down） |
| R2 | PASS | reverse-dep sites 48 ≤ 48（37 files，monotone non-increase） |
| R3 | PASS | matrix 12 edges；managed 2 modules/0 edges/SCC max 1；unmanaged refs 1 disclosed |
| R4 | PASS | print total 1376 ≤ 1376（per-function ratchet） |
| R5 | PASS | cli keys 99/99 frozen，segments 73/73 frozen |
| R6 | INFO | cold import 205 modules（baseline 205，Δ0）advisory |
| R7 | PASS | regen deterministic=True；committed==fresh True |

### 2.6 补充实测（评估支撑）

- `pytest test_review_machine_provenance.py -q`：**41 passed（0.49s）**——含 SKILL 契约段 `≤4096B` 断言（L280），DEC-327 升档 + DEC-328 勘误数字在 HEAD 活体成立（§4）。
- `git rev-parse v0.96.0` = f73bba4（annotated tag 对象 → commit 325289f，与 plan-tracker「tag v0.96.0→325289f」一致〔FIX-349 口径〕）；`git log v0.96.0..HEAD` = 6 commits（§头部窗口）。
- `project/changelog.md` 段头实读：最新段 = `## [0.96.0] - 2026-10-07`（无 0.97.0 段——M-0 时点预期态，M-1 落段）。

---

## 3. strict 余量 28tok 版本面评估（REL-101 前置评估项①）

### 3.1 注入面覆盖面定义（代码实读：`infra/checks/injection_budget.py` L111~L172）

| 面 | tier | 载体文件 | scope |
|---|---|---|---|
| persona | **resident（hard）** | `agent-presets/governance/agent.cordis.yml.template` | persona prefix block |
| entry-template | **resident（hard）** | `commands/governance-init.md` | Step 7 模板块（lightweight/standard/strict 三 profile 选择） |
| secondary-entry-template | **resident（hard）** | `commands/governance-init.md` | secondary-thin 块（双入口工作区） |
| agent-instructions | **resident（hard）** | `adapters/dsh/AGENTS.md.template` | 全文件 |
| entry-skill | skill（report-only） | `skills/software-project-governance/SKILL.md` | 全文件 |
| command-doc | command（report-only） | `commands/governance.md` | 全文件 |

**判定：`project/changelog.md`（CHANGELOG）不在任何注入面**（resident/skill/command 六面均非 CHANGELOG；覆盖面为封闭枚举表 `INJECTION_BUDGET_SURFACES`，新面需改表 fail-closed）。

### 3.2 版本面风险评估结论

1. **CHANGELOG 0.97.0 段增文：不触及注入面 → 无版本面风险**。段落长度不受注入预算约束（任何增文量均不影响 6172/6200）。
2. **M-1 bump 对 resident 面的触碰 = 等长数字替换**：版本戳 `0.96.0`→`0.97.0`（6 字符→6 字符，ASCII）发生在 entry-template 模板块/agent-instructions 等 resident 载体内——字节/字符数不变 → 块级 token 计量（ASCII=ceil(chars/4)）不变 → **freeze line 不触发**（无增长即无收缩义务）。
3. **本批（FEAT-090/091/092）的注入面增文已计价在 6172 内**：SKILL 契约 7~9 条/behavior-protocol M7.8/M7.4 T1 delta 面/governance-init 模板同步——当前 strict 6172 即含增文后的终值（三 profile 与 EVD-1351 交付台账逐值一致）。
4. **re-price 预案：不需要**（CHANGELOG 面外 + bump 等长替换，均无计量变化）。**兜底在位**：M-2 门禁复跑 `check-injection-budget` 三 profile（fail-closed——任何 resident 增文即 FAIL 拦截）；若后续版本需 resident 面实质增文 → 按 freeze line 语义同 commit 等量收缩，或走 DEC-325 先例的预算重定标裁定（需 DEC 入账，不得静默）。

---

## 4. DEC-327 契约段预算升档随版披露核对（REL-101 前置评估项③）

| 核对项 | 实读结果 |
|---|---|
| decision-log L194 DEC-327 | ✅ 在位——SKILL「关键行为契约」段字节预算 3072→4096B（六条→九条，M7.8 第 7~9 条）；先例链 DEC-144→162→295(2)；回退语义（若 R0 回退第 7~9 条则预算随票回落 3072）；伴随事实（M0 fixture pin 重定基 + FACTS_PRINT_TOTAL/anchor 冻结字面量随票更新） |
| decision-log L195 DEC-328 勘误 | ✅ 在位——复测段 3686B / 余量 410B（R0 审查复核，R0 勘正 docstring 已同步）；断言 ≤4096 不受影响；不改变升档决策与回退语义 |
| HEAD 活体复核 | ✅ `test_review_machine_provenance.py` 41 passed（含 ≤4096B 断言）——升档后预算护栏活体成立 |
| 版本面动作判定 | **无需额外版本面动作**——披露义务落在 M-1 CHANGELOG 0.97.0 段（素材已由 DEC-327/328 台账备齐：升档理由/先例链/勘误数字/回退语义）；M-0 无欠账。随版披露建议措辞要素：预算升档 3072→4096B + 勘误后实测 3686B/余量 410B + GOVERNANCE_LEGACY_BEHAVIOR 回退联动 |

---

## 5. 风险与余量评估（既有基线 vs 本批引入归因）

| # | 项 | 归因 | 处置建议 |
|---|---|---|---|
| 1 | REL-101 执行包缺失（18c 族 6 FAIL） | 流程时序态（非缺陷） | Coordinator M-1 前 `execution-packet --write` 落盘消解（Check 18c 阻断缺包——硬前置） |
| 2 | 风险过期×2（WARN） | 既有基线 | 不随本版扩大；escalation 到期检测照常（bootstrap 面） |
| 3 | 28n 债务组×8（closure_chain/dsh_compat/governance_store/loop_migration 等） | 既有债务（0.96.0 m-0 §2.2 遗留披露） | 0.98+ 候选池（session-snapshot 观察池「closure_chain 拆分」在案）；本版不计入 |
| 4 | 28s 治理数据体量×3（213.2/524.2/200.7KB） | 既有（evidence-log 前置归档触发已过阈） | M-8 持续归档触发检测（`archive.py migrate --auto --dry-run` 先行——0.96.0 先例第 9 项） |
| 5 | 30c×42 undated WARN | **本批引入（FEAT-089 V6d 收紧）但为 DEC-146③ 台账在案的接受基线**（不计入 all_issues；实测 42=台账精确一致） | 维持披露态；**0.97.0 生效后 V7/V8 → FAIL 执法激活**（见 #7） |
| 6 | strict headroom 28tok + freeze line ACTIVE | 本批增文后的终态（6172 已含 FEAT-090/091/092 增文） | 无版本面风险（§3）；M-2 复跑兜底；后续 resident 增文走等量收缩或 DEC-325 式重定标 |
| 7 | **Check 30c FAIL 执法随版本激活**（PROVENANCE_FAIL_ESCALATION_VERSION=0.97.0 单向棘轮） | **本批关键行为变更**——bump 至 0.97.0 后，手写/无 receipt 审查结论行从 WARN 升级为 FAIL 计入 all_issues | **CHANGELOG 0.97.0 段必须显著披露**（行为变更面）；预期不产生新 FAIL（豁免清单消费后 honored 479/479=100.0%；V6d 无日期 WARN 不计入）——但语义上发布即执法，属版本承诺兑现 |
| 8 | mojibake 伪影（check-release 输出 box-drawing 字符 GBK 显示） | 控制台编码显示层（非产品缺陷；FIX-278 口径仅约束 `.governance` 文件读取） | 无动作；如实记录 |

**本批引入面小结**：仅 #5/#6/#7 三项且全部台账在案/预期内；**无未披露的本批引入 FAIL**；无产品缺陷 FAIL。

---

## 6. 版本号决策记录（semver + bump 理由）

| 项 | 决策 | 依据 |
|---|---|---|
| bump 级别 | **MINOR：0.96.0 → 0.97.0** | ①`core/VERSIONING.md` MUST 触发——references/ 行为契约文件变更（behavior-protocol.md M7.8/M7.4 T1 + SKILL.md 契约第 7~9 条）；②新增 B 级自动化能力（review-record --scope/--delta-base、execution-packet --budget、批量审查派发协议）；③**版本号本身是执法生效载体**：FEAT-089 `PROVENANCE_FAIL_ESCALATION_VERSION=0.97.0` 单向棘轮硬编码——DEC-146 升级路径绑定 0.97.0，不可改号；④路线图 L205 既定 + TRIAGE-REL-101 用户立项 |
| 版本号合法性 | 无冲突 | 0.96.0 已发布顺延 +1 不跳号；1.0.0 预留位未触碰；v0.97.0 tag 不存在 |
| semver 合规性 | 合规 | 0.x 段 MINOR=向后兼容新功能累积；无 Breaking（见下） |
| Breaking 评估 | **无** | ①行为增强均为 MUST 语义强化（并行派发/禁睡眠/事件化/单源/delta 复审/budget advisory 字段），合法调用方零破坏；②Check 30c FAIL 执法为 DEC-146 既定升级路径兑现（预告在案）；③`GOVERNANCE_LEGACY_BEHAVIOR=1` 可回退 M7.8.3 的 FEAT-034 fallback 面（EVD-1352 台账）；④CLI/schema 变更均为可选字段追加（--budget/--scope/--delta-base）；⑤`.governance` schema 无变更 |
| 回归基线 | 全绿 | 全量 unit tests exit=0（check-release 执行门实测）+ 契约族 184P/0F + provenance 族 41P/0F + archguard 七轴 0 violations + 三 profile 注入预算 PASS（§2） |
| 升级路径 | /plugin update | 入口 bootstrap 版本戳 0.97.0 后经 FEAT-035 升级确认门自升级（用户未响应前零写操作）；无迁移指南需求（EVD-1352：迁移指南=不需要） |

---

## 7. GO-NOGO 建议与条件

### 建议：**GO（有条件）**

**依据**：载荷四票全 committed + 审查链全终态 AWN/0（§1）；全量测试面/契约族/archguard/注入预算/发布门静态面全绿（§2）；三项 M-0 前置评估全部通过（strict 余量无版本面风险 §3 / 预存失败面核销归零 §2.4 / DEC-327 披露无欠账 §4）；check-release 5 issues 全部为发布链自身待做项（执行包/CHANGELOG/三件套），无产品缺陷阻断。

### 条件（按链序）：

1. **C1（M-1 硬前置）**：Coordinator 落盘 REL-101 执行包（`execution-packet --write`）——消解 18c 族 6 FAIL（Check 18c 阻断缺包）。
2. **C2（M-1）**：bump 全套一致（0.96.0→0.97.0，先例 13 处面：SKILL frontmatter 权威锚 + REQUIRED_SNIPPETS 锚 + 投影面再生 + 双根 entry sync）+ CHANGELOG 0.97.0 段落段（必含：四票载荷叙事 / DEC-327 升档+DEC-328 勘误披露 / **Check 30c FAIL 执法激活的行为变更披露** / DEC-326 rider / EVD-1350~1352 事实链）。
3. **C3（M-2 门禁复跑定谳）**：bump 后复跑——check-governance（预期 18c 族消解、回归 §2.1 基线 WARN 面）/ check-injection-budget 三 profile（预期等长替换后 4416/5899/6172 不变）/ 契约族 + test_review_machine_provenance / archguard-ratchet / check-release candidate（预期 changelog 消解；release-docs 待 M-4）。
4. **C4（M-4 组装面）**：三件套落盘 `docs/release/release-checklist-0.97.0.md` / `feature-flags-0.97.0.md`（N/A 声明件先例——0.95.0/0.96.0 同构）/ `rollback-plan-0.97.0.md`（回滚=git revert 版本面提交 + /plugin update 回退）。
5. **C5（M-3 双审）**：CODE R0 + RELEASE R0 双 AWN/0（载荷批已审终态——发布面审查聚焦版本面/CHANGELOG/发布链完整性）。
6. **C6（纪律线）**：既有 WARN 基线不扩界（#2~#5）；30c×42 维持 DEC-146③ 接受基线口径不计入；M-8 收口回填 REL-101✅ + 路线图行发布终态。

### 阻断项：**无硬阻断**（所有 FAIL 均为流程时序态；修复路径全部在发布链自身动作内闭环）。

---

## 8. 需 Coordinator 复跑/回填清单（M-2 面）

1. `check-governance --summary-only`（C1 执行包落盘后）——预期 FAIL 归零、回归 §2.1 WARN 基线。
2. `check-injection-budget` 三 profile（M-1 bump 后）——预期 4416/5899/6172 三值不变（等长替换论证 §3.2）。
3. `python -m pytest`（契约族 + provenance 族定向 + 全量）——预期全绿维持（0.96.0 先例第 1 项口径）。
4. `archguard-ratchet` —— 预期七轴 PASS 维持（bump 不触 mainfile loc 面；若版本面再生触碰行数 → 按 A5 棘轮纪律先例裁定）。
5. `check-release --version 0.97.0 --require-changelog --lineage-mode candidate`（M-1 后 / M-4 后两拍复跑）——预期 changelog 拍消解 → release-docs 拍消解 → 全绿。
6. `release-ledger --version 0.97.0 --no-remote`（M-5/M-6 candidate 态；tag/push 后 `--remote origin` + released 模式）。
7. `quality-tools` —— 结构化记录（未安装记 NOT_RUN，不虚构 PASS）。
8. `archive.py migrate --auto --dry-run`（M-8 持续归档触发检查——28s 三文件已过阈，如需归档→执行 + `check-archive-integrity`）。
9. git 区间锚回填：载荷窗口终值 `325289f..M-4 组装 commit`（六 commits 已实测在位 §头部；M-5a/M-5b/tag 哈希待回填 rollback-plan 回填位）。

---

## 9. 边界声明（保守边界——REL-021 token 全量）

本报告为 M-0 评估时点快照（master@602dc79，bump 前）：版本一致性/CHANGELOG/发布三件套的 FAIL 态均为预期时序态而非缺陷结论；「GO（有条件）」为 Release Analyst 建议，正式 GO/NOGO 裁定权在 Coordinator/用户（M-2 全绿或 GO 终审先例口径）。本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success；非 Windows 平台未验证；dsh upgrade regression 语义=隔离环境安装冒烟（环境变量重定向至临时目录，零真实 home 写入），非 live marketplace 升级证明。治理开销收益数字（省 ~2.9h/检查 42→6/重复读 20→0）为 EVD-1350/1352 台账实测基线的预期推算，实际收益待后续会话实证回收。
