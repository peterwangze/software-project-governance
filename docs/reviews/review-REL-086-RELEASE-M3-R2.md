# REL-086 · M-3 发布半面复审报告（Release Reviewer · R2）

> **轮次声明**：**R2（round 2）**——前轮引用：`docs/reviews/review-REL-086-RELEASE-M3.md`（R0，NEEDS_CHANGE，P1-1/P1-2）→ `docs/reviews/review-REL-086-RELEASE-M3-R1.md`（R1，NEEDS_CHANGE，N-R1-1/N-R1-2）。本复审按 M7.4 复审必达发起，全部判定基于实测（check-governance 实跑、execution-packets.json 全文正则、evidence-log/governance-store-ops.json 实读、git 状态实测），不依赖收口声明自述。
> **日期**：2026-09-25 · **HEAD**：`f350c95`（未动）· 工作树：3 个 untracked 审查报告（R0/R1 + 产品半面——Coordinator 提交批承载）
> **输出**：本文件为唯一输出；机录由 Coordinator 执行。

---

## 0. 结论速览

| 项 | 裁决 |
|---|---|
| **审查结论（SKILL 词汇）** | **NEEDS_CHANGE（R2）——unresolved_blockers = 1**（N-R1-1 延续、收窄未清零） |
| N-R1-2（Check 21 review debt ×2） | **已收口** ✅——实测 review debt = 0；EVD-1167/1168 事实性核验通过；ops 收据双确认 |
| N-R1-1（包合同占位/不合规） | **未收口（收窄：35 → 28 FAIL 行）** ❗——user/job 类子项已消解（−7），但 **18d success_metrics ×7 + 18f threshold ×7 + 18g vertical_slice ×7 + assumption_record ×7 = 28 行 FAIL**；`TO_BE_DEFINED` 残留 **203 处**（quality_budget 24/包 + interruption_policy 5/包） |
| 收口声明准确性 | **「Check 18d/18e/18f/18g 实测全绿」与实测不符**——实测仅 18e 绿（7/7 PASS）；18d/18f/18g 各 7 行 FAIL。声明中「18d 35 行消解」实为仅 user/job 子项消解 |
| 计数演进对账 | 95→92→74→67→**64**（实测确认）——算术自洽（−7 = user/job 子项、−3 = Check 21×2+聚合行），但 67 的构成含 28 行包合同 FAIL，非声明所述「已知披露面」 |
| ⚠️ 熔断提示 | **round 2 已达；R3 为熔断前最后一轮**——若 R3 仍有 BLOCKING → 按 T2 转 BLOCKED + escalation。R3 收口 MUST 一次做对（清单见 §5），申报前 MUST 自跑四检查粘贴输出 |

---

## 1. N-R1-2 复验（实测）——判定：已收口 ✅

```
┌─ Check 21: Review Debt / Spawn Gap (FIX-174) ─────────┐
│  Product-code tasks (all, with evidence): 19
│  Review debt (have execution evidence, no review): 0
│  [PASS] All product-code tasks have review evidence.
```

四层核验全部通过：
1. **Check 21 实测 = 0**（R1 = 2 FAIL + 聚合行）；
2. **EVD-1167（FIX-385）/ EVD-1168（REL-089）行实读**：内容为「审查汇总」（Code Reviewer 终态链汇总），引用事实与本工位独立掌握的审查史**逐点吻合**——EVD-1167 引 REVIEW-FIX-385-R0（七面全过+RED 16F 隔离实测）→F-1 TOCTOU 修复→R1 APPROVED_WITH_NOTES/0 终态；EVD-1168 引 REVIEW-REL-089-R0 APPROVED_WITH_NOTES/0（0.87 方法论独立复验/git show+子进程实跑/4 FAIL 活体复现）——均为真实既存事实的汇总登记，**非编造**（与 EVD-1147 合格重写先例同型合法）；
3. **ops 收据双确认**：`governance-store-ops.json` 实读——op-67a67caf…（evidence-append, FIX-385, status=ok）、op-f040d080…（evidence-append, REL-089, status=ok）；
4. **零新 FAIL**：新增两行未触发 Check 16/17/18 任何新 FAIL（新增行零豁免全严检红线未触碰——DEC-227 红线保持）。

处置方式认可：以「审查汇总 EVD 行」补全机录联动可达性，属数据面补全而非谓词放宽——方向正确。

## 2. N-R1-1 复验（实测）——判定：未收口（收窄）

### 2.1 有进展的部分
- `product_success_contract.user` / `job_to_be_done`：**已按票面事实填写**（抽读 REL-087「插件版本的用户（bootstrap 版本检查与 /plugin update 流程）」、FEAT-060「治理插件的 Coordinator 与守护进程使用者」——事实性、非占位）→ 对应 18d 子项 FAIL 消解（−7）。
- Check 18e（acceptance contract）：**7/7 全绿** ✅。

### 2.2 未清零的部分（28 行 FAIL，逐族）

```
[FAIL] 18d ×7：success_metrics needs at least one user-visible outcome /
        must not contain process-only metrics（FEAT-060/061/064, REL-086/087/088/089）
[FAIL] 18f ×7：quality_budget.performance.threshold must be specific and non-placeholder
[FAIL] 18g ×7：vertical_slice.user_visible_slice must describe a user-observable behavior or scenario
[FAIL] assumption_record ×7：assumption must not be placeholder text
```

`TO_BE_DEFINED` 全文正则 = **203 处**：`quality_budget` 24 处/包（六轴中除已填轴外仍占位——18f 只查 performance.threshold，其余轴占位属残留债）+ `interruption_policy` 5 处/包。

### 2.3 声明与实测的偏差（如实记录）

| 收口声明 | 实测 |
|---|---|
| 「Check 18d/18e/18f/18g 实测全绿」 | 仅 **18e** 全绿；18d/18f/18g 各 7 行 FAIL + assumption_record ×7 |
| 「18d 35 行消解联动 → 67」 | 35 → 28（仅 user/job 子项 −7）；「消解」表述不准确 |
| 「product_success_contract…全键含 last_run PASS…」 | 键在、user/job 已填；success_metrics 内容不合规（process-only）为当前 18d FAIL 主因 |

连续两轮出现申报口径与实测偏差（R1「74=已知面」、R2「四检查全绿」）——**要求 R3 收口方申报前自跑 check-governance 并粘贴 18d~18g+Check 21 段输出**，申报以实测为准（P-v1 P1 原则）。

## 3. R1 findings 逐条比对

| R1 发现 | R2 实测 | 判定 |
|---|---|---|
| N-R1-1 包合同占位（35 FAIL 行） | 28 FAIL 行 + TO_BE_DEFINED 203 | **未收口（收窄）**——本轮唯一 unresolved blocker |
| N-R1-2 Check 21 review debt ×2 | 0；汇总行+收据四层核验通过 | **已收口** |
| M-5 批绑定项（P2-1 checklist 回填 / P2-2 RISK-059 行 / 74 分解回填） | 未动（声明确认） | 维持——**绑定：M-5 批先于 tag/push** |
| 其余披露面（REQ-092×6 / EVD-1146 / 18-18b 2×2 / Check 28s / 结构 472 / plan-tracker WARN / 4 stale / hooks / 获得 21 / changelog manifest） | 实测在案（11 FAIL 已知席位行 + WARN 族） | 与 R1 §4 分解一致 ✅ |

## 4. 计数 64 对账（实测构成——修正声明口径）

```
64 = FAIL 39（包合同族 28 + 已知席位 11）
   + WARN ~24（获得 21 族计数、4 stale、hooks、plan-tracker、changelog manifest、scope、结构 472〔0 blocking〕、closure 29、R3 16 等）
   + ERROR 1（Check 28s，evidence-log 1,735,257B）
```
演进归因修正：74→67 = user/job 子项消解（−7，**非「18d 全族消解」**）；67→64 = Check 21×2+聚合行（−3）✅。**R3 预期计数 = 64 − 28 = 36**（若 quality_budget 其余轴与 interruption_policy 的占位清理引出新检查面，以实测为准并逐行归因）。

## 5. R3 收口清单（熔断前最后一轮——一次做对）

1. **7 包 × 4 族清零**（信息源=票面 + commit + 交付证据的用户可见结果表述）：
   - `success_metrics`：≥1 条 **user-visible outcome**（写用户得到什么，如「/plugin update 后 0.88.0 版本声明面 28/28 投影一致生效」）；删除/改写 process-only 指标；
   - `quality_budget.performance.threshold`：具体非占位（用票面真实验收值，如「指定套件全绿零回归」「check-governance 单次 <60s」——与实测口径一致）；
   - `vertical_slice.user_visible_slice`：用户可观察行为/场景（B-12/B-13 缺省零足迹、bump 后版本面一致等**用户侧**描述，非流程步骤）；
   - `assumption_record.assumption`：真实假设文本（非占位）；
   - **一并清理** `quality_budget` 其余轴 + `interruption_policy` 的 TO_BE_DEFINED（203→0——不被检查的占位同样违反 no-overclaim 边界，且是后续轮次的复发源）。
2. **申报前自验（MUST）**：`grep TO_BE_DEFINED execution-packets.json = 0`；check-governance 中 18d/18e/18f/18g/assumption 全 `[PASS]`；**粘贴四检查段输出随申报**。
3. R3 复审焦点：28 行清零 + 203→0 + 计数 36 ± 实测归因 + 无新 FAIL；通过则 `APPROVED_WITH_NOTES / unresolved_blockers=0`（notes = M-5 批绑定项 + P3 备查 + M-4 五风险裁决）。
4. **熔断后果预告（T2）**：R3 若包合同族仍有 BLOCKING → 本链按轮次纪律转 **BLOCKED + escalation**，发布半面不得进入 M-4。

---

## 6. 硬门槛状态（增量视角）

| 门槛 | R1 | R2 |
|---|---|---|
| checklist 全 PASS | 未达（#19 席位 18d 红） | **仍未达**——#19 席位语义下 18d/18f/18g+assumption 28 行 FAIL；Check 21 面已转绿 ✅ |
| 回滚已验证 / CHANGELOG / breaking / flag / semver | 达成（R0 §3/§10 结论） | 不变（无相关变更信号：HEAD 未动；本复审未重测，R0 结论继续有效） |

**审查结论：NEEDS_CHANGE（R2）· unresolved_blockers = 1（N-R1-1 延续）**。round 2 < 3——返工后 R3；R3 为熔断前最后一轮。

---
*R2（2026-09-25，Release Reviewer Agent）。全部判定基于本复审实测（check-governance 实跑 + 包实体全文正则 + governance-store-ops.json/evidence-log 实读）；声明与实测的偏差已逐条如实记录；机录由 Coordinator 执行。*
