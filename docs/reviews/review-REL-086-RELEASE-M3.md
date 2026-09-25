# REL-086 · M-3 发布半面审查报告（Release Reviewer · R0）

> **任务**：REL-086 M-3 双半面审查——发布半面（Release Reviewer 链）；与产品代码半面并行不重叠。
> **工位**：Release Reviewer Agent（角色定义 `agents/release-reviewer.md` + `skills/release-review/SKILL.md` 全文加载）
> **日期**：2026-09-25 · **HEAD**：`f350c95`（REL-089）· **工作树**：CLEAN（`git status --porcelain` 实测零输出）· **分支**：master
> **轮次声明**：**R0**（M-3 发布半面首轮，无前轮报告；M-0 期 RELEASE-R0/R1/R2 属规划链另账，不构成本链前轮）
> **约束遵守**：只读 + 门禁实测（check-release / release-ledger / check-governance / write-guard-bootstrap 实跑）；未修改任何既有文件；本报告为唯一输出文件（机录由 Coordinator 执行）。

---

## 0. 结论速览

| 口径 | 结论 |
|---|---|
| **总结论（父任务 GO 词汇）** | **GO_WITH_CONDITIONS**——发布机制五要素全部就绪或可预判，无 P0；P1×2 为 M-4 go/no-go 前必须收口的条件 |
| **review-record 机录判定建议（SKILL 词汇）** | **NEEDS_CHANGE（round 0）**——存在未解决 BLOCKING-class finding（P1-1 Check 18c 阻断级 FAIL + P1-2 披露面对账缺失）；收口后 MUST 复审（R1），R1 预期 `APPROVED_WITH_NOTES / unresolved_blockers=0`。两个口径不矛盾：GO_WITH_CONDITIONS = 机制面 GO + 条件强制；NEEDS_CHANGE = 审查链诚实性（APPROVED_WITH_NOTES 不允许携带未解决 blocking，见 SKILL L21） |
| 发现计数 | **P0×0 · P1×2 · P2×5 · P3×7** |
| 五维度 | ①发布链完整性 PASS_WITH_NOTES ②check-release 门禁状态 **FAIL（披露面未对账）** ③回滚就绪 PASS_WITH_NOTES ④ledger 预检 PASS ⑤tag/push 前置 PASS ⑥风险登记对账 PASS_WITH_NOTES |

---

## 1. 维度一：发布链完整性 —— 判定 PASS_WITH_NOTES

### 1.1 M 链逐环节证据核验（全部实读机录行 + commit）

| 环节 | commit | 机录证据（evidence-log 实读） | 核验 |
|---|---|---|---|
| M-0 双审 GO | `0233f49`（+`266c32b`/`7d6ff6a`） | REVIEW-REL-086-R0（design, NEEDS_CHANGE）→ R1（APPROVED_WITH_NOTES）；REVIEW-REL-086-R0-RELEASE → R1-RELEASE（NEEDS_CHANGE）→ **R2（APPROVED_WITH_NOTES）**——轮次连续 0/1/2，全部 `review-record CLI 机器写入` | ✅ |
| M-1 bump | `72ddffb` | REVIEW-REL-087-R0（code, APPROVED_WITH_NOTES）+ EVD-1164 | ✅ |
| M-1R 四件套 | `a8a72a3` | REVIEW-REL-088-R0（code, APPROVED_WITH_NOTES）+ EVD-1165；四文件在场实测（release-plan / release-checklist / rollback-plan / feature-flags 各 0.88.0）+ rel-089-m3-precondition-report.md | ✅ |
| M-2 门禁实测 | `501d8dc` + `36cc899` | 实测已执行（commit message 汇总：全量 pytest 4108P/0F、verify PASSED、LRC PASS、Check 28s/REQ-092 披露面维持；Check 18/18b 分叉面披露已落专席②）——**但门禁表 #1~#19 未回填、M-2 checkbox 未勾、无独立 M-2 EVD 行**（commit 自述「M-2 EVD 随发布链总结机录」= 递延中）→ **P2-1** | ⚠️ |
| REL-089 前置补强 | `f350c95` | REVIEW-REL-089-R0（code, APPROVED_WITH_NOTES）+ EVD-1166；DEC-240 三条件全落地：①未激活默认运行时验证（11 测试两路径，报告 §①）②Check 18/18b 2×2 正式例外（限定 2 记录×2 检查×0.88.0 + FIX-390 消解票——报告 §②，活体复现与 M-2 记录逐字一致）③持久状态回退兼容（六工件定性矩阵 + §8 文本已落 rollback-plan——逐段比对一致） | ✅ |

- **窗口计数（实测 2026-09-25，HEAD=`f350c95`）**：`git rev-list --count v0.87.0..HEAD` = **34**（`git describe` = `v0.87.0-34-gf350c95` 交叉印证）。⚠️ 任务书口径「35 commits」与实测差 1——**以实测为准**（P1 原则）；四件套「29 提交」为 M-1R 冻结时点（HEAD=`3fb42c0`）值，其后 +5（`72ddffb`/`a8a72a3`/`501d8dc`/`36cc899`/`f350c95`）= 34，与 rollback-plan「区间计数不写死：M-5 现场以 `git rev-list --count 602f8f3..<发布 tip>` 取值记入 EVD」条款自洽。
- **v0.87.0 tag 存在性（回退锚）**：annotated tag object `2e5f715`，taggerdate `2026-09-21 14:02:27 +0800`（FIX-349 taggerdate 权威口径），peel = `602f8f3` ↔ `core/releases/0.87.0.json` `release_commit` ↔ 三份发布文档——**三方逐字一致**。
- **M-5/M-7/M-8 输入义务明确性**：release-plan L97-100 M 链表 + checklist「M-8 收尾义务」节 + rollback-plan §区间锚定/§8 已将三站义务落到可执行粒度（明细见本报告 §8）；**M-5 的输入侧需追加一项：M-2 门禁表回填 + checkbox 勾选 + M-2 EVD 机录同批落账（P2-1 收口）**。

**判定**：链完整、轮次连续、终态全为通过终态、无跳轮；唯一缺口为 M-2 的清单面收尾（P2-1，不破坏链完整性本身）→ PASS_WITH_NOTES。

---

## 2. 维度二：check-release 门禁状态 —— 判定 FAIL（披露面未对账 → P1-2）

### 2.1 实跑记录（2026-09-25，本审查工位，candidate 模式预演）

```
SPG_RELEASE_GATE_TIMEOUT=600 python <infra>/verify_workflow.py check-release --version 0.88.0 --require-changelog
→ Result: FAILED - 1 issue(s)（execution gates）
  16 组件 PASS：version consistency / release fact source / hot fact source / runtime readiness matrix /
  first session measurement / governance pack status / agent adapters / projection sync / cross references /
  archive integrity / release docs / release lineage（candidate）/ gate sequence / one dot zero blockers /
  dsh upgrade regression（isolated smoke PASS）/ loop fuse block / changelog / loop runtime claim gate
  （semantic_verdict=PASS, candidates=1002, parsed=1002, skip=0, truncate=0）
  唯一 FAIL：execution gates → governance health（--fail-on-issues exit=1，"ISSUES FOUND — 95 issue(s)"）
  执行门内部：verify PASS / e2e check PASS / unit tests PASS（exit=0）/ governance health FAIL
```

**发布机制解读**：check-release 唯一 FAIL 来源 = governance health 的 issue 计数面（`--fail-on-issues` 语义下任何 issue 即 exit 1）。0.87.0 M-8 同门实测为 **29 issues 披露面维持**并照常发布——本门 FAIL 本身不是 NO-GO 机制；问题在于 **29 → 95 的 +66 增量未对账**（见 2.3）。

### 2.2 与 checklist 期望席位对账（专席②/#1 期望 vs 实测）

| checklist 期望席位 | 实测 | 对账 |
|---|---|---|
| REQ-092×6（Check 16×3 + 17×3，EVD-476/473/423） | 恰 6 行 FAIL（实测 `REQ-092` 计 6） | ✅ 零豁免红线维持 |
| EVD-1146 superseded 残留（不动+披露） | Check 16 FAIL（目标对齐仅 13 chars）+ 17 面 WARN 各 1 | ✅ 处置口径在案（见 §9.1） |
| Check 18/18b 2×2（EVD-1140/EVD-1164） | 恰 4 行 FAIL | ✅ 在 REL-089②/DEC-240②/241 例外限定内（记录×2×检查×2×0.88.0，FIX-390 消解） |
| Check 28s ERROR（F-6 席位） | 1 ERROR：evidence-log.md **1,735,257 bytes**（≈1,695KB；0.87 M-8 期 1,620KB → 窗口增长 ~+75KB） | ✅ 席位维持；M-8 归档后复测消解 |
| 结构性 WARN 0 blocking | `472 structural issue(s) (0 blocking)` | ✅ |
| plan-tracker 过渡态 WARN | 1 WARN（workflow version=0.87.0, expected=0.88.0） | ✅ M-8 收口 |
| 4 stale risks（Check 2） | RISK-036（16d）/ RISK-039（16d）/ RISK-046（16d）/ RISK-050（14d） | ✅ 与披露⑧对齐（处置见 §6） |
| hooks_drift | 1 WARN | ✅ M-8 重装提示席位在案 |

### 2.3 席位外新面（checklist 未对账——+66 增量的构成）

| # | family | 实测 | 初步归因 |
|---|---|---|---|
| N1 | **Check 18c 执行包缺失** | 18 行 FAIL = 3 任务（**REL-087 / REL-088 / REL-089**）× 6 面 | 活跃 P1 任务缺执行包——违反「活跃 P0/P1 缺包 → execution-packet --write」契约；M-0 先例曾为 REL-086 补 4 包，三张发布链票未补 → **P1-1** |
| N2 | **M7.4 step-6 推荐快照缺失（S1）** | 18 violations（盒内展示 8：FIX-375×2、FIX-376、FIX-379、FIX-383、FIX-386、FIX-387、FEAT-060） | 批次执行（DEC-229 预授权链）下「完成必推荐 → task-priority-analysis 快照入 evidence-log」义务未逐票落账 → **P1-2 组成** |
| N3 | 获得-词表 WARN 族 | 21 行（EVD-1140~1166 新机录行「获得=值不在合法范围」） | 词表一致性检查对新机录行措辞 WARN；非数据缺陷，需披露或词表扩展票 |
| N4 | check-manifest-consistency | 1 WARN：`changelog.md on disk but not in manifest` | 披露⑥双位过渡的 manifest 注册面（见 §9.2 裁决） |
| N5 | REL-089 "unreviewed product-code task" | 1 WARN | REVIEW-REL-089-R0（APPROVED_WITH_NOTES）在案——疑为 plan-tracker 任务行状态滞后所致，M-5/M-8 行刷新时核销 |
| N6 | 其余既有面 | 29 closure WARN（V1 历史非终态残留）/ 16 R3 risk→task 交叉引用 WARN / scope side_effect WARN 1（`d68355f`「顺带」）/ function_size×6 + module_size×2（ArchGuard/RISK-039 面）/ machine-provenance revisit WARN×2 | 既有老化面，非本窗新增债 |
| — | **risk-log 表结构** | Check 36：ragged **7 行**——含 **RISK-059 非独立表行**（`||` 粘连于 RISK-051 行尾，`^\| RISK-059` 扫描不可见——本审查独立复现） | → **P2-2** |

### 2.4 判定

机制面（verify/e2e/单测/dsh 冒烟/LRC/投影/交叉引用/归档完整性/门禁序/1.0.0 blocker）全绿；FAIL 集中于披露面记账。**#15（check-release 复合门禁）按 checklist 定义为 M-5 提交批义务，M-2 执行序不含它——因此 M-2 记录的「已知披露面维持」只覆盖了 #1/#17 等已跑席位，复合门的面从未在本窗实测过**；本审查实跑即该面的首次测量，结果 = 期望席位全对账 + 席位外新面 6 族未披露 → **M-4 go/no-go 不能按现版 checklist 的披露面记账消费** → 判 FAIL（披露面未对账），收口动作见 §7 P1-1/P1-2 与 §8。

---

## 3. 维度三：回滚就绪终验 —— 判定 PASS_WITH_NOTES

1. **文档完整性**：rollback-plan-0.88.0 含保守边界声明 / 区间锚定（单轨两段论证 + 0.81.0 F-04 终点纪律）/ §1 影响分类 / §2 程序（维护者+用户+发布前中止）/ §3 数据安全 / §4 回滚后验证 12 项 / §5 不可回滚 8 项 / §6 触发条件 8 项 / **§7 B-12/B-13 回退显式化专节** / **§8 两路径区分（REL-089 · DEC-240③）** / **§9 0.89 候选池 9 项（含 FIX-390/391）**——结构完整，无占位编造（`<发布 tip>` 未预填 ✅）。
2. **§7 专节复核（M-3 MUST 项）**：双层表述（未激活=零回退需求 / 激活后=族级 flag 回 WARN `--deactivate-block` audited + break-glass 五限定不可静默〔guard 自指同适用〕；B-13 反向转换 rollback-begin→rollback-export〔覆盖迁移后新增行〕→rollback-activate）与代码事实一致；本轮抽验运行时实态：`write-guard-bootstrap --check-only` **exit 0**（violation_ledger_healthy open=3 / no_pending_txn / ledger_no_drift 全 ok）✅。
3. **§8 回退前四步可执行性（实测）**：
   - 步骤 1 closure 事件清单：`.governance/closure-events.jsonl` **缺席 = 0.88 事件闭包为空** ✅（实测 Test-Path False）
   - 步骤 2 `write-guard-bootstrap --check-only` 世界判定：**实跑 exit 0**，converged ✅
   - 步骤 3 权威状态：`.governance/.decision-store-state.json` **缺席 = MD_ACTIVE epoch 0**（缺省零足迹）✅；`.decision-migration/` 缺席（无迁移在途）✅
   - 步骤 4 冻结写窗：程序性动作（Coordinator 执行）——无机制障碍
   - 工件面：`.write-guard-posture.json` 缺席（B-12 第一层交付态）✅；`.write-guard-state.json`/`.write-guard-violations.json` 在场 = rollback §8「共同前提」已列名的持久工件，路径 A（amnesty 重建）/路径 B 同型兼容（REL-089 §③ 定性矩阵背书）
4. **v0.87.0 tag 存在性**：见 §1.1（annotated 2e5f715 / taggerdate 权威 / peel 602f8f3 三方一致）✅。
5. **演练缺口（M-3 裁决项）**：revert 干跑未排程——**裁决：不阻断、不强制排程**（0.85.0/0.86.0/0.87.0 三版同先例；F-04 教训决定 tip 生成前干跑验证的是错误终点，现时点干跑证据价值有限）；**建议（非门禁）**：M-5 生成真实 tip 后、M-7 push 前，按 FIX-354 隔离副本法做一次 `revert --no-commit` 干跑并留档，作为可选加固。

**判定**：PASS_WITH_NOTES（唯一 notes = 演练未排程，已如实标注并裁决；无阻断项）。

---

## 4. 维度四：ledger 预检 —— 判定 PASS

| 实测项 | 结果 |
|---|---|
| `release-ledger --version 0.88.0 --no-remote` | **FAIL：cannot read release manifest: FileNotFoundError** = `core/releases/0.88.0.json` 缺席——**与 checklist #10 预提交态预期逐字一致**（M-5 义务非缺陷）✅ |
| `release-ledger --no-remote` 全量（38 manifests） | 最新三版健康：0.85.0/0.86.0/0.87.0 全 PASS；**0.87.0 = NATIVE_RELEASED PASS**，release_commit=`602f8f3`（tag peel 同一）✅ |
| 全量扫描 4 个历史 FAIL | 0.66.2（recovery_evidence 多余属性）/ 0.66.3（trust.candidate_commit.sha + events 结构旧形）/ 0.67.0（events 结构旧形）/ **0.71.0（NATIVE_RELEASED 态 integrity hash mismatch）**——`git log v0.87.0..HEAD` 四文件**零改动** = 全部窗口外预存，特定版本门（`--version`）不受影响 → **P3-1**（建议 0.89 历史账本审计票；0.71.0 的 released 态 hash 失配值得专查） |
| candidate 面就绪度 | M-5 前置全部可预判：manifest 创建程序（canonical 形态 + schema 对齐 0.87.0 先例）+ 四件套同批提交 + 复跑期望 NATIVE_CANDIDATE PASS——路径无未知阻塞 |

---

## 5. 维度五：tag/push 前置清单（M-7 义务预演） —— 判定 PASS

**sha256 双锚口径（FIX-349 / 代码级确认）**：`ledger.py L157-159`——`event_integrity(event) = "sha256:" + sha256(canonical(event − integrity 字段))`（事件体自斥规范哈希，manifest 内 `events[].integrity` 承载）；`ledger.py L360`——`event_identity_digest = sha256(canonical(identity 列表))`（工具侧 L1 交叉锚）。0.87.0 实例：event `rel084-transition` integrity=`sha256:a1536981…` + digest=`f67cd537…`。

| 需要什么（序列） | 当前缺什么（实测） |
|---|---|
| ① M-4 go/no-go 决策（DEC-229 预授权形态，Coordinator 呈现）+ **五风险窗裁决同批**（§6/C3） | M-4 未到（正常） |
| ② M-5：`core/releases/0.88.0.json` 创建（NFC/sorted/compact/trailing-LF；schema 对齐 0.87.0：artifacts{changelog=project/CHANGELOG.md, release_docs=四件套, review_evidence=.governance/evidence-log.md} + lifecycle_state=candidate + provenance=native + trust.candidate_commit{derivation=git_commit_adding_path}）+ 四件套同批提交 | **manifest 缺席**（Test-Path False 实测） |
| ③ M-5：复跑 `release-ledger --version 0.88.0 --no-remote`（期望 NATIVE_CANDIDATE PASS）+ check-release candidate（SPG_RELEASE_GATE_TIMEOUT=600）+ **P1-1/P1-2 收口后的干净披露面** | 待②后执行 |
| ④ M-5：transition 事件（candidate_to_released；manifest-only 单父；id 沿 `rel086-transition` 命名先例；recorded_at + claims{derivation=manifest_only_transition, m4_authorization=按 M-4 实际授权 DEC, release_task=REL-086}；integrity=事件体 canonical sha256） | tip 不存在（正常——`<发布 tip>` 占位未预填 ✅） |
| ⑤ M-6：`check-release --lineage-mode released --release-commit <tip>` + `release-ledger --remote origin` 全绿方进 M-7——**`origin` remote 在场实测**（ssh://git@ssh.github.com:443/…，master upstream=origin/master；另有 github-https 镜像） | 待④后执行 |
| ⑥ M-7：annotated tag `v0.88.0`（peel=transition 提交；**taggerdate 权威**——FIX-349）+ master + tag 原子推送（远端 SHA 精确一致）+ tag 事实（peel/taggerdate）回填 checklist L15/L27 与 rollback §区间锚定/§2.1 占位 + `git rev-list --count 602f8f3..<tip>` 记入 EVD | **v0.88.0 tag 缺席**（`git tag -l v0.88*` 空——实测，正确前置态） |
| ⑦ push 不可逆提醒（rollback §5#1：tag 一经推送只能前进 0.88.1）+ 审计报告归档副本义务（§5#7——本报告与产品半面报告如需保留 MUST 回滚前归档） | 常设义务 |

**判定**：前置全部可枚举、无未知阻塞；「缺什么」均为尚未到达的站点交付物而非缺陷 → PASS。

---

## 6. 风险登记对账 —— 判定 PASS_WITH_NOTES

| 项 | 实测 | 发布前处置需求 |
|---|---|---|
| **RISK-059**（FEAT-061 切换前置三缺口，高，打开） | 行**在场**（2026-09-25；三缺口①archive 路由②freshness 接线③11 处勘误行——触发条件=启动真实权威切换时）但**行格式畸形**：`||` 粘连于 RISK-051 收口行尾，非独立表行，`^\| RISK-059` 机器扫描不可见（本审查独立复现；Check 36 ragged=7 同族）→ **P2-2** | **不阻断发布**——RISK-059 是 B-13 真实切换授权票的前置（DEC-238④），本版 B-13 机制交付未激活（缺省 MD_ACTIVE 零足迹实测）；行格式修复入 M-5 批（Coordinator 一行重排） |
| **4 stale risks（Check 2 实测）** | RISK-036（16d）/ RISK-039（16d）/ RISK-046（16d）/ RISK-050（14d） | RISK-036/039/046 裁决窗 **2026-09-30 在发布窗内**——checklist M-4 行 + 披露⑧已绑定「到期即裁决（不迟于 M-4——F-13）」→ **C3：M-4 go/no-go MUST ≤ 2026-09-30 或届时一次完成三项裁决**（+RISK-047/048 同日观察窗复核、RISK-050 10-31 维持打开）；否则 tag/push 日带着 5 项过期风险窗（Check 2 escalation 责任面） |
| 发布阻断性评估 | 三项 stale 均为运营/架构/治理协调类风险，无一是发布机制面（tag/ledger/rollback/门禁）阻断项 | 无需发布前关闭；裁决动作本身即 F-13 义务的履行 |

---

## 7. 发现清单（P0~P3）

| # | 级别 | 发现 | 处置（收口工位） |
|---|---|---|---|
| — | **P0** | 无 | — |
| P1-1 | **P1（阻断级）** | **Check 18c：REL-087/REL-088/REL-089 三张发布链票缺 execution packet**（18 行 FAIL=3 任务×6 面）；活跃 P1 缺包违反执行包契约（Check 18c 阻断语义）；checklist #19 席位期望「全绿确认」未达成；M-0 期 REL-086 已补 4 包先例 | Coordinator：`execution-packet --write` ×3（REL-087/088/089，按四件套+commit 事实补写）——**M-4 前** |
| P1-2 | **P1（阻断级）** | **governance-health 披露面 29→95 未对账**：期望席位（§2.2 八项）全对账 ✅，但席位外 6 族（§2.3 N1~N6）无任何 checklist 披露承载；#15 复合门在本窗首次实测即暴露该面；no-overclaim 边界要求 M-4 消费真实披露记账 | Coordinator：(a) P1-1 补包 + M7.4 step-6 推荐快照补落（N2——18 项 S1 violations 的补快照或经 DEC 的显式豁免登记，禁止静默）；(b) checklist 专席②/#15 预回填本次 95-issue 全 family 归因表（本报告 §2.3 可直接承载）+ N3 词表 WARN 与 N5 状态滞后披露——**M-4 前** |
| P2-1 | P2 | M-2 门禁表 #1~#19 未回填（仍 ⏳）、M-2 checkbox 未勾、无独立 M-2 EVD 行（数值仅存于 `501d8dc` commit message + 专席②披露）；违反 checklist 自身纪律（L3「实测后由执行工位原样回填」/L16「未实测项一律标待回填」的对偶义务） | Coordinator：M-5 提交批同批回填 + 勾选 + `governance-store evidence-append` 机录 M-2 EVD（引用 501d8dc/36cc899 实测值） |
| P2-2 | P2 | risk-log 表结构缺陷：RISK-059 非独立表行（`||` 粘连）+ Check 36 ragged=7 行——高Severity风险对机器解析（Check 2 stale 扫描/escalation）不可见 | Coordinator：RISK-059 重排为独立 13 列表行（内容零改写）；其余 ragged 行一并顺修——M-5 批 |
| P2-3 | P2 | 风险裁决窗排期硬约束：RISK-036/039/046（+047/048 观察）2026-09-30 到期，落在 M-4~M-7 时段内 | 与 C3 同一：M-4 ≤ 09-30 或提前一次完成五项裁决（F-13 已绑定，属确认性义务） |
| P2-4 | P2 | CHANGELOG 双位 manifest 注册缺口：根 `changelog.md` 已 tracked（M-1 落库）但不在 canonical manifest（check-manifest-consistency WARN「on disk but not in manifest」）；实质内容零漂移（95 行 vs 95 行，仅 2 行空白/行尾差异——逐行比对实测） | §9.2 裁决落地：canonical=project/CHANGELOG.md；根位去留（manifest 注册 or 0.89 移除）由 M-8/0.89 决策，M-8 披露⑥收口时落字 |
| P3-1 | P3 | 4 个历史 manifest FAIL（0.66.2/0.66.3/0.67.0 旧 schema 形态；**0.71.0 NATIVE_RELEASED 态 integrity hash mismatch**）——窗口外预存（四文件 v0.87.0..HEAD 零改动实测），特定版本门不受影响 | 0.89 候选：历史 ledger 审计票（0.71.0 专查） |
| P3-2 | P3 | REL-089 报告「根 changelog.md UNTRACKED」披露已过时（现 tracked）——无害，M-8 收口时顺手勘正 | M-8 |
| P3-3 | P3 | revert 干跑未排程 | §3.5 裁决：不阻断；可选加固 = M-5 tip 后隔离副本一次干跑 |
| P3-4 | P3 | REL-089 "unreviewed product-code" WARN（REVIEW-REL-089-R0 终态在案）——疑 plan-tracker 行状态滞后 | M-5/M-8 行刷新核销 |
| P3-5 | P3 | scope side_effect WARN（`d68355f`「顺带」F-4/F-5）——FEAT-063 R1 已覆盖审查 | 留档即可 |
| P3-6 | P3 | hooks_drift WARN | M-8 重装提示席位已在 checklist ✅ |
| P3-7 | P3 | 29 closure WARN（V1 历史非终态残留）+ 16 R3 交叉引用 WARN——老化已知面，非本窗债 | 不处置（随维护周期） |

---

## 8. M-5 / M-7 / M-8 前置义务清单（可执行粒度）

### M-5（candidate 提交 + transition）——输入义务
1. `[P1-1]` `execution-packet --write` ×3：REL-087 / REL-088 / REL-089（事实源=各自 commit + REVIEW 终态行 + EVD-1164/1165/1166）。
2. `[P1-2]` M7.4 step-6 推荐快照补落或 DEC 显式豁免登记（18 S1，§2.3 N2）；checklist #15/专席② 回填 95-issue 全 family 归因表。
3. `[P2-1]` M-2 回填批：门禁表 #1~#19 实测值原样回填（4108P/0F、verify PASSED、LRC PASS、Check 28s/REQ-092/EVD-1146/Check18-18b 2×2、archguard regen 前后、contract-matrix 97 键、ledger 预提交 FAIL、组合测试集四条、证明包门、e2e/dsh 冒烟、Check 28s 现值）+ M-2 checkbox 勾选 + M-2 EVD 机录行。
4. `[P2-2]` risk-log：RISK-059 独立表行重排（+ragged 顺修）。
5. manifest 创建（§5 表②规格）→ 四件套+manifest 同批提交（0.87.0 先例同 commit）→ `release-ledger --version 0.88.0 --no-remote`（期望 NATIVE_CANDIDATE PASS）→ `check-release --version 0.88.0 --require-changelog`（SPG_RELEASE_GATE_TIMEOUT=600；期望=披露面对账后的可解释态）。
6. transition：candidate_to_released 事件（§5 表④字段规格；integrity=event_integrity 代码口径）→ 单父 manifest-only；`git rev-list --count 602f8f3..<tip>` 记入 EVD。
7. `[P2-4]` 披露⑥ canonical 裁决落字（§9.2）。

### M-6（预推校验）
8. `check-release --lineage-mode released --release-commit <tip>` 全绿 + `release-ledger --remote origin`（origin 在场已实测）——全绿方进 M-7。
9. （可选加固）隔离副本 revert 干跑一次并留档（§3.5）。

### M-7（tag + push）
10. annotated tag `v0.88.0`（peel=tip；taggerdate 权威）→ master + tag 原子推送（远端 SHA 精确一致）→ peel/taggerdate 回填 checklist L15/L27、rollback §区间锚定/§2.1 占位；push 前呈报不可逆提醒（rollback §5#1/#7——审计报告归档副本义务含本报告）。

### M-8（归档 + 收尾）——checklist「M-8 收尾义务」六项全数有效，另加
11. `[P2-4/P3-2]` 披露⑥收口落字 + REL-089 报告 UNTRACKED 措辞勘正；`[P3-4]` plan-tracker REL-089 行状态核销；`[P3-6]` hooks 重装提示执行；Check 28s 复测（现值 1,695KB）+ 归档完整性（失败阻断发布完成）。

---

## 9. M-3 专项裁决项（checklist/rollback 点名 M-3 裁决的四项）

1. **EVD-1146 处置口径（披露②）**：**维持「不动历史行 + 披露」**（DEC-227 路线 a 先例——补录=编造风险，违反 P1）；不得入 B-11 历史豁免账本（0.88 窗口新增行零豁免红线）。EVD-1147 合格重写在案，状态链完整。复核通过，无异议。
2. **CHANGELOG 双位过渡（披露⑥）**：实测实质**零内容漂移**（两段各 95 行，差异仅 2 行空白/行尾）→ 用户可见分歧风险不成立；**裁决：canonical = `project/CHANGELOG.md`**（0.87.0 manifest `artifacts.changelog` 契约指向 + 历史连续判据面）；根 `changelog.md` 定位为过渡投影位，其 manifest 注册或移除去留 → M-8/0.89 决策（P2-4）。不阻断发布。
3. **revert 干跑是否补演（#18 / rollback §4#10）**：**不排程、不作为门禁**（§3.5 理由）；可选加固建议见 P3-3。
4. **Check 18/18b 2×2 例外（REL-089② / DEC-240② / DEC-241）**：复核通过——例外限定面（记录={EVD-1140,EVD-1164}×检查={18,18b}×候选=0.88.0）+ 消解条件（FIX-390）+ 人工复核记录（ops 收据状态链三层核验）完备；与 M-2 记录逐字一致（活体复现独立验证）。

---

## 10. 硬门槛裁决表（role 硬门槛 × 本审查）

| 硬门槛 | 阈值 | 裁决 |
|---|---|---|
| 发布检查清单全部 PASS | =100% | **未达**——M-2 站点实测已执行但清单面未回填未勾选（P2-1）+ #19 席位 FAIL（P1-1）+ 复合门披露面未对账（P1-2）→ NEEDS_CHANGE 主因 |
| 回滚方案存在且已验证 | 已验证 | 结构完整 + 回退前步骤 2/4 机器实测、1/4 缺席即满足、1/4 程序性；演练未排程已裁决（三版先例）→ 达成（含如实标注） |
| CHANGELOG 用户视角完整 | 关键段覆盖 | 双位同段、实质零漂移、行为变更 B-12/B-13/B-14+退出码透传均显式 → 达成（canonical 裁决留 M-8/0.89） |
| breaking changes 已标注 | =100% | semver 论证「非 MAJOR/Breaking=无」+ 行为变更表四行显式回退通道 → 达成 |
| Feature Flag 关闭验证 | 全部通过 | B-12/B-13 缺省零足迹**机器实测**（posture/decision-store-state 文件缺席 + write-guard-bootstrap check-only exit 0 + REL-089 11 测试两路径）→ 达成 |
| 版本号合规 | semver | 0.87.0→0.88.0 MINOR 论证充分（B/C 级能力），无跳号无占用 → 达成 |

**审查结论（SKILL 词汇）：NEEDS_CHANGE（round 0）**——阻断项 = P1-1 + P1-2；均为 Coordinator 侧小规模收口（预估 ≤0.5 天），不触及发布机制面。按复审必达契约，收口后 MUST 重 spawn 本工位 R1 复审（注入本报告路径）；R1 验证点 = §7 P1-1/P1-2 处置事实 + #15 门禁复跑的披露面增量归零/对账。**父任务 GO 词汇总结论：GO_WITH_CONDITIONS**——条件 C1（=P1-1）、C2（=P1-2）于 M-4 前、C3（M-4 ≤ 2026-09-30 含五风险裁决）、C4~C6（P2-1/P2-2/P2-4 于 M-5 批）全部满足后，本半面无残余反对意见。

---

## 附：本审查实测命令清单（可复跑）

```
git log v0.87.0..HEAD --oneline / rev-parse HEAD / tag -l / for-each-ref refs/tags/v0.87.0 / rev-parse v0.87.0^{} / rev-list --count（=34）/ describe（v0.87.0-34-gf350c95）/ status --porcelain（CLEAN）/ ls-files changelog.md / remote -v / branch --show-current
release-ledger --no-remote（38 manifests 全量解析）/ release-ledger --version 0.88.0 --no-remote（FAIL=manifest 缺席，符合预期）
check-release --version 0.88.0 --require-changelog（SPG_RELEASE_GATE_TIMEOUT=600；FAILED-1=governance health 95 issues）
check-governance（三次取样的 issue family 全量归类；Check 18c=3×6；S1=18；词表 WARN=21；ragged=7；stale=4）
write-guard-bootstrap --check-only（exit 0）
Test-Path：.governance/{.write-guard-posture.json=False, .decision-store-state.json=False, closure-events.jsonl=False, .decision-migration=False, archive/.migration=False, .write-guard-state.json=True, .write-guard-violations.json=True}；core/releases/0.88.0.json=False
```

未复跑项（如实标注）：全量 pytest（M-2 实测 4108P/0F + REL-089 期 4119P/0F 在案——M-5 绑定实际发布提交时 MUST 复跑）、组合测试集四条（#12）、独立证明包门（#13）、混沌复演、B-12 真实翻转 / B-13 真实切换（本版明确不执行）。

---
*REL-086 M-3 发布半面 R0（2026-09-25，Release Reviewer Agent）。全部结论基于本报告「实测命令清单」输出与所引文件实读；未实测项均标注，无编造。机录（review-record / evidence）由 Coordinator 执行。*
