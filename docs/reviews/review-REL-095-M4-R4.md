# REVIEW-REL-095-M4-R4 — 0.92.0 发布四件套轻量审查报告

- **Round**: R4（机录轮位 round=4——round 0/1/2/3 已被 REVIEW-REL-095-M1-R0 / B2-R1 / M3-CODE-R0 / M3-RELEASE-R0 占用；前轮引用：本审为 M-4 四件套首审，无同对象前轮，R4 为 REL-095 任务级轮位续接）
- **Reviewer**: Code Reviewer（agents/code-reviewer.md + skills/code-review/SKILL.md 已加载；P0~P3 分级；APPROVED / APPROVED_WITH_NOTES〔附 unresolved_blockers〕/ NEEDS_CHANGE / BLOCKED）
- **审查对象**: REL-095 M-4 发布四件套（纯文档新增，未提交）——`docs/release/release-plan-0.92.0.md`（实测 139 行）/ `release-checklist-0.92.0.md`（99 行）/ `rollback-plan-0.92.0.md`（52 行）/ `feature-flags-0.92.0.md`（30 行）；审查基线工作树 @HEAD=`df26f7e`（`git status --porcelain` 亲证：四文件 untracked，另有 M-3 双报告两 untracked 文件=前批交付非本票对象）
- **审查性质**: 轻量审——事实核对为主（任务简报 7 项重点全部对照权威源：git 实测 / exceptions.json / 基线附件 / evidence-log EVD / decision-log DEC / M-3 双报告 / 0.91 四件套模板）
- **审查日期**: 2026-09-29 ｜ **任务**: REL-095（M-4 四件套）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）** — P0=0 / P1=0 / P2=0 / **P3×2**

---

## 一、审查重点逐项结论（任务简报 7 项）

### 重点 1：FAILED-7 全貌表（checklist 核心）vs 实跑与 EVD-1235/R0 逐字对照 — PASS

- **①②归属实测复现**：本审只读复跑两面——`archive.py scan-families 0.1.0 0.90.0`（dry-run）独立复现 **EVD would_archive=178 rows**（与基线附件/Check 27 聚合语义同源）；`check-governance-data-size` 实跑复现 **EXC-001 两层同屏原文**（`[ERROR] governance_data_size: .governance/evidence-log.md 1756021 bytes … — exception accepted (EXC-001, ref=DEC-282 …, expires=2026-10-12)` 同行同屏；现值 1,756,021B ≤ 上限 2,036,197B）+ decision-log 254,420B advisory 面（fatal_on_error=false）。
- **checklist 核心表（L33~44）逐行对照 review-REL-095-RELEASE-R0.md 重点 5（L75~86）与 EVD-1235（evidence-log L2926）**：①archive integrity=EXC-002 承接（消息措辞错标 0.93 池/任务面 would=0 已闭合/原始 FAIL 保留）✓；②governance health exit=1 38 issues（28s=EXC-001 机注+EVD-702/1194/1198 遗留面+CR-F1/F2 advisory+28c×2/packet 占位）✓；③④hot fact source ×2（session-snapshot 缺 0.91.0 行/plan-tracker 缺 0.92.0 roadmap 行——阶段预期）✓；⑤⑥⑦release docs ×3 missing（本 M-4 创建即消——四文件现已在盘，文件名与检查面期待的恰三件吻合）✓；原生执行门全绿行（verify/unit/e2e exit=0+loop PASS semantic/identity/candidates=1096/豁免 5+one-dot-zero PASS+lineage candidate）与 EVD-1235 逐字一致 ✓；静态面清单与 R0 L84 一致 ✓；判定句「7 issues 全数归属三类……无未预期阻断项」= R0 L86 原文判定 ✓。7=2+1+3+1 计数闭合 ✓。
- **M-2 双层报告对照表（L46~54）**：EVD-1235 声明（archive=178/28s 机注/原生 PASS/「有条件收口/例外接受（非原生全绿）」原文）与 M-3 实跑逐面「一致 ✓」，RL-F2 未枚举面（hot fact source ×2/release-docs ×3）由核心表补承载——与 R0 RL-F2 消解路径吻合 ✓。

### 重点 2：数字抽核（18 项 ≥ 要求 10 项）— PASS（全部吻合）

| # | 数字 | 权威源核验 | 结果 |
|---|---|---|---|
| 1 | 上限 2,036,197B | exceptions.json `growth_control_bytes: 2036197` | ✓ |
| 2 | 基线 1,786,197B | exceptions.json note「Baseline 1,786,197 B @ post-dc45e24」+算术 1,786,197+250,000=2,036,197 | ✓ |
| 3 | expires 2026-10-12 / recheck 2026-10-05 | exceptions.json `expires_on`/`recheck_on`；=批准日 09-28+14 自然日亲算 | ✓ |
| 4 | 178=160+4+14 | 基线附件节区逐行计数亲数（A=160/B=4/C=14，和=178）+本审 scan-families 独立复现 178 | ✓ 双源 |
| 5 | 18=2 任务+18 EVD | DEC-284「扩至 2任务+18EVD（4 随行+14 补完成）」+EVD-1233 守恒算术亲证（evidence 2939→2921 行=−18；plan-tracker 524→522 行=−2） | ✓ 算术吻合 |
| 6 | `df26f7e` | `git rev-parse HEAD` 实测=窗口 tip；`git show --stat`=4 文件自洽（账本+11/锚 re-pin 8/定向测试+96~97/审查报告+77） | ✓ |
| 7 | `40eb6f7` | git log 在窗（09-28 23:12 M-1 版本面）；基线附件输入锚同 hash 全长亲证 | ✓ |
| 8 | `dc45e24` 功能载荷锚 | DEC-282(1) 原文「功能载荷锚 dc45e24」+git log subject 对应 FIX-402 | ✓ |
| 9 | `bd9bfc1..tip`=13 | `git rev-list --count bd9bfc1..HEAD`=13 实测+`git describe`=v0.91.0-13-gdf26f7e 交叉印证+`git cat-file -p v0.91.0`（tag object `0ea429f`→object `bd9bfc1…`） | ✓ 三源 |
| 10 | taggerdate 2026-09-28 05:24:03 +0800 | epoch 1790544243 亲算换算=2026-09-28 05:24:03 +08:00 | ✓ |
| 11 | 254,420B（CR-F1） | `(Get-Item .governance/decision-log.md).Length`=254420 逐字节实测 | ✓ |
| 12 | 5508 行（CR-F2） | `skills/software-project-governance/infra/archive.py` 实测=5508 行（注意：e2e 副本 1671 行为不同文件，文档口径指真实路径） | ✓ |
| 13 | loop candidates=1096 | EVD-1235 原文+R0 L83 双源（本审未重跑 35min 全量，双源采信+豁免面实跑佐证） | ✓ 双源 |
| 14 | 豁免 5 条 | 本审 `check-loop-runtime-claims` 实跑：verdict=PASS/exit=0/5 豁免在册（CHECKLIST0810-241-1/FIX300R0-71-1/71-4/72-1/**FIX401R0-79-1**——B-5 第 5 条生效） | ✓ 实跑 |
| 15 | 51 文件 +5333/−216 | `git diff --shortstat e65b317^..df26f7e` 命令复现=51 files,+5333/−216（CODE R0 L14 原命令） | ✓ 复现（见 F1 措辞注） |
| 16 | 2333s=ceil(1554.78×1.5) | 算术亲证 1554.78×1.5=2332.17→ceil=2333 | ✓ |
| 17 | digest 4f8a6cc8→d47f5d16 | EVD-1234 原文（re-pin 至 d47f5d16）+loop-claims 实跑第 5 条生效间接印证 | ✓ |
| 18 | 时点演进 1,753,848→1,755,371→1,755,693B | EVD-1235（1,753,848）+R0 L31/32（1,755,371→1,755,693，+322B=机录行追加）；本审现值 1,756,021B 仍 ≤ 上限（后续机录行追加可归因，同口径） | ✓ |

其余抽核：strict 余量 9→391 tok（EVD-1218 原文在案）；EXC-002 期限 min(0.93 准入, 2026-10-12)（DEC-285(2)+附件 L219 逐字）；RISK-050「2026-10-31 到期」在 risk-log L41 亲证。

### 重点 3：回滚三序正确性 — PASS

- **三序内容与次序**：①迁移面（journal 逐 ID 复原+archive.py rollback——「区分 4 随行 vs 14 补完成」与 DEC-284 验收项措辞逐字一致；178 行未迁移面无数据操作=EXC-002 随版本回滚整体失效）→ ②`git revert df26f7e`（单提交自洽：本审 `git show --stat` 亲证账本+锚 re-pin+定向测试同 commit，无悬挂）→ ③`git revert 40eb6f7`+`release-projection --write` 幂等再生+check-projection-sync/check-version-consistency 验证——**先数据后 git、豁免面先于版本面**的次序正确；数据面独立于 git（`.governance` 不入库）前提如实。
- **与 rollback-plan-0.91.0 模板形态一致**：0.91 的「回滚三步序列」（Step 1 git revert 链→Step 2 投影再生→Step 3 manifest lifecycle）在 0.92 演进为「回滚三序」并因 0.92 特有的数据面有界迁移（0.91 为零迁移声明版）前置迁移复原序——形态同构、演进有据；「0.91 先例 `bc3f052` 同构」注记亲证（bc3f052=REL-094 M-1 版本面提交，`git show` 在案）；「同文件多票 revert 禁单票选择性还原」纪律句与 0.91 逐字同型；tag 误推独立 DEC、hotfix 不重写 tag 与 0.91 一致。
- **0.92 特有面（EXC 到期处置）完备**：§EXC 到期处置五要素（不自动续期/失效路径=28s+Check 27 恢复硬阻断+发布冻结直至重评/周义务/0.93 承接 FEAT-076/两面互不覆盖）逐项对照 DEC-282(4)、DEC-285(2)(4)、exceptions.json 全部有据 ✓——RL-F3/P3-2 对 rollback-plan 的义务（EXC 到期处置+回滚三序）完整承载。

### 重点 4：版本口径（no-overclaim）— PASS

- release-plan L14 附加句「结构性解锁已完成；容量问题未技术消除。本轮不执行 EVD 物理迁移，按限期例外控制，后续迁移以读取契约闭合为前提。」与 decision-log DEC-282(7) 原文**逐字一致**（本审 decision-log L224 亲读比对）；checklist L5 同句复载 ✓；project/CHANGELOG.md 0.92.0 段（准备态）同句在文 ✓。
- 「18 行有界迁移（2 任务+18 EVD）属 DEC-284 补完成授权，非『本轮不执行』矛盾」精确措辞在 release-plan L14 与 checklist L5 双处在文 ✓——DEC-284 原文「性质：补完成历史欠账非新迁移面扩张」支撑该表述，逻辑自洽（DEC-284 授权在前、DEC-282(7) 附加句约束的是 178 行剩余面与 0.93 全量迁移面，非矛盾）。
- 发布日期不预填（CHANGELOG「未发布（准备态）」亲证）、发布 tip/tag/M-5~M-8 数值全部为回填位明示——起草期纪律（FIX-349 口径）贯彻 ✓。

### 重点 5：feature-flags — PASS

- **零新增旗标声明**在文（L3「本版零新增旗标（例外标注机制=输出标注面非 flag 面）」）✓；**交叉验证**：窗口 diff（e65b317^..df26f7e）扫描新增行零新增 `GOVERNANCE_*` env 变量/零新增 CLI `add_argument` 旗标面（命中的 GOVERNANCE_DIR/`governance_exceptions` 行均为测试代码与 FEAT-075 标注机制=非 flag 面）✓。
- **既有旗标沿用**：GOVERNANCE_LEGACY_BEHAVIOR（FEAT-040/0.84.0/本版零改动）、RB2_SENSITIVE_BLOCK_ENFORCED（FEAT-069/0.90.0/位置 `infra/checks/evidence_domain.py` 实存/本版零改动）、B-12/B-13（未激活，独立授权票纪律=RISK-059 在案 L51）——与 0.91.0 feature-flags「既有旗标沿用」形态连续 ✓。
- **B-1~B-7 回滚 commit 逐项正确**：B-1 `e65b317` ✓；B-2 revert `f06a2bf a7bcd5f`（新→旧次序正确：f06a2bf 12:06 晚于 a7bcd5f 12:04）✓；B-3 `136d65e` ✓；B-4 revert `484dd77 16a5157`（新→旧正确）✓；B-5 `df26f7e` 单提交自洽（亲证）✓；B-6 迁移面序①（journal+archive.py rollback，EVD-1233 隔离副本实弹演练）✓；B-7 regen 分离提交 `f06a2bf`（26385→26413）+`484dd77`（26413→26478）对称回退——两 commit 的 git log subject 均为 regen 分离提交亲证 ✓。B-2 公式 ceil(1554.78×1.5)=2333 算术亲证 ✓。

### 重点 6：模板一致性（vs 0.91 四件套）— PASS（无缺节，超集演进）

| 文件 | 0.91 章节 | 0.92 章节 | 判定 |
|---|---|---|---|
| release-plan | 保守边界声明/版本号与授权链/发布范围（载荷构成+不发布什么）/风险窗引用/回滚区间锚定/M-链状态/发布窗口/门禁摘要/已知边界/硬门槛自检（10 节） | 同 10 节逐一在文（「已知边界四条」→「已知边界」措辞微变，内容面同构） | ✓ 无缺节 |
| release-checklist | 发布范围/M-链完成态勾选/M-2 门禁实测回填/M-5~M-8 待办/已知问题与边界/发布后验证计划（6 节） | 全部承载+新增 check-release 终态核心表/M-2 双层报告对照/双例外治理对照（RL-F3 要求项） | ✓ 无缺节（超集） |
| rollback-plan | 回滚区间锚定/发布前回滚/发布后回滚/数据兼容性/回滚影响评估（5 节） | 全部承载+新增回滚三序/EXC 到期处置（0.92 特有面） | ✓ 无缺节（超集） |
| feature-flags | 旗标面清单/本版新增非旗标面/无声明变更（3 节） | 同 3 节（零新增声明+B-1~B-7） | ✓ 无缺节 |

尾部边界声明（REL-021 token 全量）四件中三件在文（release-plan 以§保守边界声明承载同口径）——与 0.91 先例形态一致。

### 重点 7：AI 专项（引用抽核 5 处 + 5 项检查）— PASS

- **引用存在性抽核（5/5）**：①DEC-282(7) 附加句（decision-log L224 逐字）②EVD-1235「有条件收口/例外接受（非原生全绿）」原文（evidence-log L2926 逐字）③`dc45e24` 功能载荷锚（DEC-282(1)+git log subject）④`docs/reviews/review-FIX-401-R0.md`（B-5 五元组 locator——盘上实存）⑤exceptions.json EXC-001 数值面（全字段）——全部存在且吻合。附加：基线附件 222 行/输入锚 40eb6f7/sha256 2365c01c/L217 增长容忍 0 条款/L219 期限/L222 机注不可达注记全部亲读 ✓；`docs/governance/fix-402-data-corrections-ledger-20260928.md` 实存 ✓。
- **mock 残留**：零——全部数字来自本审实跑（git/scan-families/data-size/loop-claims）与亲读文件（evidence-log/decision-log/exceptions.json/基线附件/M-3 双报告）。
- **硬编码/幻觉引用**：零——18 项数字抽核全部可溯（表见重点 2）。
- **未实现 TODO**：零——回填位（发布 tip/tag/M-5~M-8 数值/EVD 机录编号）均明示为义务位而非伪实现；「待机录（EVD 编号以实际机录为准）」措辞与 DEC-282「不提前伪造完成态」一致。
- **过度实现**：零——四件套写入边界声明（不触 `.governance/` 治理数据/不改产品代码/不 tag/push/transition；candidate manifest 不在锁面）与本审实测全部吻合：`core/releases/0.92.0.json` 缺席亲证（=M-5 义务未提前 ✓）、v0.92.0 tag 未打、四文件外零工作树改动。

## 二、Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| M4R4-F1 | **P3** | release-plan L27 / checklist L20 | 「窗口 diff 51 文件 +5333/−216」缺区间限定词：该数字的权威源（M-3 CODE R0 L14）对账区间为 `e65b317^..df26f7e`（12 提交，排除搭窗 `4cb3081`）；本审实测全发布窗 `bd9bfc1..df26f7e`=**56 文件 +5523/−239**。数字与源报告逐字一致（命令复现 ✓），但两文档自称的「0.92.0 窗口=bd9bfc1..tip（13 提交）」口径下裸称「窗口 diff 51」存在指代歧义（搭窗提交另有 L40 披露行，但未与 51 数字显式挂钩） | M-5 CHANGELOG 发布态改写或 M-8 终账补限定词：「六票+发布链对账区间 `e65b317^..df26f7e`=51 文件 +5333/−216（搭窗 4cb3081 披露批除外，全窗 56 文件）」。非阻塞 |
| M4R4-F2 | **P3** | release-plan L111（门禁摘要第 1 行） | FAILED-7 压缩式分类「例外覆盖面×2+阶段预期态×5+advisory 披露缺口×2」为**面级计数（2+5+2=9 面）**而非 issue 级（7 issues）混排：② governance health 一个 issue 贡献 28s（例外面）+28c×2（阶段预期）+CR-F1/F2（advisory）多面，且 legacy 旧行/packet 占位子面在压缩行省略（checklist 核心表 ②行有完整枚举，release-plan 亦有「逐项全貌表=checklist 核心表」指针——事实完备，仅压缩行自身粒度混排，误读时 2+5+2≠7） | 后续批（M-5/M-8 消费该摘要时）可将压缩行措辞改为「7 issues 的全部失败面归三类（面级计数 9：…）」或在 ×N 后注 issue 归属。非阻塞 |

**附注（审查输入偏差，非文档缺陷）**：任务简报所言行数（111/79/35/22）与实盘（139/99/52/30）不符——四文件内容与全部权威源事实核对不受影响，如实登记供 Coordinator 校正简报源；0.91 rollback-plan 实为 39 行（简报对 0.92 报 35），同型偏差。

## 三、硬门槛自检

| 门槛项 | 判定 | 依据 |
|---|---|---|
| P0 阻塞问题数=0 | **PASS** | 最高级发现=P3×2（均措辞精度建议，事实无错） |
| 5 维度全覆盖 | **PASS** | 正确性=重点 1/2/3/4（事实核对全过）；安全性=no-overclaim 面完整+零敏感数据+写入边界声明与实测吻合（重点 4/7）；可维护性=模板一致性+引用可追溯（重点 6/7）；性能=纯文档面 N/A 如实声明（无运行时面）；测试覆盖=验证义务/回填位/check-release 承载面完备（重点 1/2+checklist M-5~M-8 义务表） |
| 每条发现标注级别 | **PASS** | M4R4-F1/F2 均 P3；附注单列非 finding |
| 设计一致性（与 ADR/DEC 契约） | **PASS** | DEC-282(1)(2)(4)(7)/DEC-283/284/285/DEC-260（regen 纪律）/DEC-262（超时先例同式）逐项对照一致；RL-F1~F4 与 CR-F1~F4 承接关系正确（checklist M-5~M-8 表=放行条件⑤~⑩逐项） |
| AI 专项 5 项检查全部完成 | **PASS** | 见重点 7（引用抽核 5/5+mock/硬编码幻觉/TODO/过度实现逐项有结论） |

## 四、证据清单（本审亲跑/亲读，2026-09-29 @HEAD df26f7e）

1. `git status --porcelain`（恰四 release 新文件 untracked+M-3 双报告两 untracked）；四文件行数实测 139/99/52/30
2. `git rev-parse HEAD`（df26f7e）/`git rev-list --count bd9bfc1..HEAD`（13）/`git describe`（v0.91.0-13-gdf26f7e）/`git cat-file -p v0.91.0`（object bd9bfc188d38…、tagger epoch 1790544243→2026-09-28 05:24:03+08:00 亲算）
3. `git log --oneline --date=format` bd9bfc1..HEAD——13 提交序列与四件套所载 hash/时刻/归属逐一吻合
4. `git diff --shortstat e65b317^..df26f7e`（51/+5333/−216 复现）；`bd9bfc1..df26f7e`（56/+5523/−239）；`git show --stat df26f7e`（4 文件自洽）/`40eb6f7`/`bc3f052`
5. `archive.py scan-families 0.1.0 0.90.0` 只读 dry-run（EVD would_archive=178 复现）
6. `verify_workflow.py check-governance-data-size` 实跑（EXC-001 两层同屏原文+现值 1,756,021B≤2,036,197B+decision-log 254,420B advisory 面）
7. `verify_workflow.py check-loop-runtime-claims --product-root . --project-root .` 实跑（verdict=PASS/exit=0/5 豁免在册含 LRC-EXEMPT-FIX401R0-79-1）
8. `.governance/exceptions.json` 全文（EXC-001 全字段）；`.governance/evidence-log.md` EVD-1216~1219/1233/1234/1235 全文+EVD-702/1194/1198 存在+REVIEW-REL-095-R3 机录行（round 3 在案=本审 round 4 轮位依据）
9. `.governance/decision-log.md` L224~227（DEC-282/283/284/285 全文——(7) 附加句/四封口/扩至 2任务+18EVD/EXC-002 条款逐字）；实测 254,420B
10. `docs/governance/rel-095-exc002-baseline-178-20260928.md`（222 行实测；A/B/C 节区计数 160/4/14 和=178；L217/L219/L222 条款原文；输入锚 40eb6f7+sha256 2365c01c）
11. `docs/reviews/review-REL-095-RELEASE-R0.md` 全文（FAILED-7 全貌/放行条件①~⑩/EXC 验收）；`review-REL-095-CODE-R0.md` 关键行（51 文件对账/976 vs 1128/26478 锚/13 文件版本一致）
12. `docs/release/*-0.91.0.md` 四件全文/章节头（模板对照）；`skills/software-project-governance/infra/archive.py` 5508 行实测；`core/releases/` 清单（0.92.0.json 缺席）；`infra/checks/evidence_domain.py` 实存；`docs/reviews/review-FIX-401-R0.md`+`docs/governance/fix-402-data-corrections-ledger-20260928.md` 实存
13. `project/CHANGELOG.md` 0.92.0 准备态段（未发布+no-overclaim 句原文+决策链缺项=RL-F1 已知义务与 checklist ⑥ 一致）；`.governance/risk-log.md` RISK-050（2026-10-31 到期）/RISK-059 在案
14. 窗口 diff 新增旗标扫描（零新增 GOVERNANCE_* env/CLI flag 面）

## 五、遗留不确定项

1. **check-release 全量（~35min）未在本审重跑**——①②两面已由针对性只读命令直接复现（scan-families 178/data-size 两层同屏），其余面（candidates=1096 等）以 EVD-1235+R0 双源采信；M-5 candidate 态执行时将全量重跑（放行条件⑤在案）。
2. M-4 本批 EVD 机录编号未定（「以实际机录为准」）——与四件套披露一致，Coordinator 面义务。

---

## 终态结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**

任务简报 7 项审查重点全部完成且 PASS：FAILED-7 全貌表与实跑/EVD-1235/R0 逐字一致且①②归属经本审只读复跑独立复现；18 项数字抽核全部吻合（含 178 双源、18/2 守恒算术、254,420B 与 5508 行逐字节实测、51/+5333/−216 命令复现）；回滚三序正确且与 0.91 模板同构、EXC 到期处置完备；DEC-282(7) 附加句与「补完成授权非矛盾」措辞逐字在文；feature-flags 零新增旗标经窗口 diff 交叉验证、B-1~B-7 回滚 commit 逐项正确；四件套为 0.91 模板无缺节超集；AI 专项引用抽核 5/5。P3×2（M4R4-F1 区间限定词/M4R4-F2 面级计数粒度）为措辞精度建议，随 M-5/M-8 消费时改善，不阻塞 M-4 收口。本审查未修改产品文件；review-record 机录 round 4 随本报告执行（task=REL-095）。
