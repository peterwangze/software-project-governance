# Release Plan — 0.91.0（REL-094 M-4④ 发布文档批）

> **任务**: REL-094（P1；DEC-265 用户 2026-09-27 授权链——0.91.0 推进与发布授权 M-0~M-8 预授权 + arch 顾问决策协议）· **日期**: 2026-09-28 · **性质**: M-4④ 发布文档面（本票为四件套：release plan/checklist/rollback/feature-flags——非发布执行；M-2 门禁实测已回填〔EVD-1210 双源〕，M-5~M-8 发布态义务逐项列入 checklist 放行条件⑤~⑩）
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-265② 授权覆盖 0.91.0 单一版本发布链；范围外新增决策与不可逆例外动作仍走用户确认；预授权**不免除** M-5~M-8 各门禁实测与放行条件；安全语义不因授权削减）；本文件由 Governance Developer Agent 起草，供 M-5 candidate 批与发布态收口消费
> **写入边界**: 仅本四件套（REL-094 M-4④ files 锁定面）；不触 `.governance/` 真实治理数据、不修改产品代码、不执行 tag/push/transition；`skills/software-project-governance/core/releases/0.91.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-5 提交批创建（M-3 RELEASE 审查亲证 0.91.0 缺席=M-5 义务；DEC-267(4) 不提前伪造完成态，本票如实披露，见 checklist 放行条件⑤）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim / No marketplace approval claim**：official approval 与 marketplace approval 未被授予、未被主张；RISK-036 维持打开（外部验证/官方提交/1.0.0 review 未满足——DEC-268(1) 复评留痕）。
- **No universal/full runtime support claim**：非 Windows 平台未验证；本版全部验收在仓库内与隔离环境口径下完成，隔离验收不等于真实外部环境验证通过。
- **No 1.0.0 production-ready claim**：RISK-036 继续打开；do not claim 1.0.0 production-ready。
- **无机制激活主张**：本版**零新增 feature flag、零机制翻转**——B-12/B-13 出厂 WARN-only 姿态不变，RB-2 阻断面维持未翻转（DEC-268(1)：0.91.0 窗口 diff 守卫 token 零命中〔M-3 RELEASE 审查亲证亲跑 #9〕，五前置未齐备，翻转仍需独立授权票）；FEAT-072 三要素推荐卡为 **agent 行为契约呈现面，非 flag 面**（M7.4 6b/6c prose 契约——feature-flags-0.91.0 §3 同口径）。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本四件套不预填——hash 一律由 M-5/M-7 生成后回填（FIX-349 口径：taggerdate 权威）。
- **发布日期不预填**：CHANGELOG 0.91.0 段维持「未发布（准备态）」，发布态日期落字按 taggerdate 权威（M-7 后回填——checklist 放行条件⑥）。
- **M-5~M-8 数值不预填**：candidate manifest、ledger 双端核对、taggerdate、归档增量、released 验证均为待办回填位——本票只列义务不写通过性数值（已知边界 28s 等点位数值均带时点标注，发布态 MUST 重测落字）。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.91.0**（MINOR；0.90.0 → 0.91.0 顺延 +1、不跳号、无预留占用；无 0.91.x tag/预留冲突；1.0.0 预留位未触碰——CHANGELOG 0.91.0 段同源） |
| 发布任务 | **REL-094**（M-1 bump `bc3f052` / M-1R `98104cb` / M-2 双源门禁 / M-3 双半面 / M-4 本批）——M-0 载荷冻结 DEC-267（arch GO 有条件冻结，2026-09-28） |
| 授权链 | **DEC-265（用户 2026-09-27 授权——0.91.0 推进与发布授权 + arch 顾问决策协议〔FEAT-072 契约设计 / M-0 载荷冻结 / round≥3 升级类 MUST 经 arch〕）→ DEC-266（FEAT-072 契约设计裁决——三行卡标签/面范围/机检锚/防编造三态/批序）→ DEC-267（M-0 载荷冻结 arch GO——载荷两票 + strict 9 tok 处置(a) + 披露分层 + 停止条件十条）→ DEC-268（M-4 风险窗复评留痕与登记面收口——六风险复评 + FEAT-073 五要素登记 + M-2 双源 EVD 机录）** |
| MINOR 依据 | DEC-267（M-0 载荷冻结——arch GO）；载荷 = **完成必推荐三要素推荐卡契约（FEAT-072）+ Check 28c 装饰日期误报修复（FIX-399）**；新增行为契约面非纯 bug fix（PATCH 不适用）；Breaking changes = **无**（M-3 CODE §5 亲证：窗口 diff CLI 面 `add_argument`/`def cmd_`/`sys.argv` 变更行 = 0、无接口删除、无文件格式破坏；推荐卡呈现无下游机器消费方依赖旧文案格式——DEC-267(3) M-3 指定确认项确认成立） |
| 行为变更面 | **无新增功能激活、无 flag 面**；行为变化 = FEAT-072 推荐呈现升级（agent 行为契约面=M7.4 6b/6c 三行卡+短选项——预期分类 DEC-267(3)「无 breaking」）+ FIX-399 判据召回向放宽（纯格式旧行行为不变）；发布态 CHANGELOG 行为变更段 = **B-15**（命名待发布态铸造——承接 B-1~B-14 序列，M-3 RELEASE 命名；落段义务见 checklist 放行条件⑥） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；发布文档面由 Governance Developer Agent 执行，M-3 双半面 Reviewer 独立审查（R2 CODE / R3 RELEASE 已 AWN/0） |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带行为变更段（B-15——推荐卡呈现升级，无破坏性变更、无数据迁移，M-5 落段） |

## 发布范围

### 载荷构成（两票载荷 + M-1/M-1R 版本与基线面 + M-2/M-3/M-4 门禁审查链——DEC-265~268）

> git 窗口实测（2026-09-28）：**0.91.0 窗口 = `3f87459..<发布 tip>`**（`3f87459` = `git rev-parse v0.90.0^{}` 实测 = v0.90.0 transition 提交；tag object `d2b2a6d`，taggerdate 2026-09-27 22:07:49 +0800 实测——FIX-349 口径 taggerdate 权威）；`3f87459..HEAD`（HEAD = `98104cb` REL-094 M-1R，2026-09-28 02:32 +0800）实测 **5 提交**（`git rev-list --count` 与 `git describe`（v0.90.0-5-g98104cb）双实测交叉印证）。**载荷两票与 CHANGELOG 0.91.0 段同源**（DEC-267(1) M-0 冻结边界内——冻结记录含合并态 HEAD 证明〔冻结时 HEAD=`9bafdf6`〕+ 联合回归 54+20 OK 证据）。

| 批 | 任务 | 关键交付 | 提交 | 证据 |
|---|---|---|---|---|
| **搭窗（0.90.0 期收尾）** | REL-093 M-8 | 发布后已知边界披露批（release docs 边界 token 四件全量 + CHANGELOG 口径注记 + 余量处置 DEC-264）——**非 0.91 行为载荷**（回退影响 = 披露文档面，如实纳入区间） | `8d25101`（2026-09-27 22:40） | — |
| **载荷一** | FEAT-072 | **完成必推荐三要素推荐卡契约（DEC-266）**——behavior-protocol.md M7.4 step 6b/6c 重写（三行卡固定标签「服务目标：/解决问题：/方案要点：」+第三行内子标签「依赖理由：」；三态依据缺失降级；短选项与卡一一对应含自主执行推荐项与暂停；空推荐禁虚构选项）+ 四注入面投影 + 机检锚 canonical 三标签（existence-only fail-closed）+ 正向与三路移除负例测试；persona 净增 +76B，注入预算 standard/strict 两档 PASS | `196894a`（2026-09-27 23:43） | EVD-1204；REVIEW-FEAT-072-R0 AWN/0（盘上 `docs/reviews/review-FEAT-072-DESIGN-R0.md`） |
| **载荷二** | FIX-399 | **Check 28c 发布日期解析器装饰日期单元格健壮性**——`FIX_105_SNAPSHOT_RELEASE_VERSION_RE` 正则容忍装饰尾巴 + `_latest_published_release_fact` 单元格内取末日期（发布日语义，语义与局限注释在案）+ 恰 6 个 `test_fix399_*` 用例；同数据 A/B 净效果 **−1 误报零新增**（stash 对照 34→33） | `9bafdf6`（2026-09-28 00:50） | EVD-1205/1207（EVD-1206 为已被取代的重复残留行，如实披露）；REVIEW-FIX-399-R0 AWN/0（盘上 `docs/reviews/review-FIX-399-CODE-R0.md`） |
| **M-1 版本面** | REL-094 M-1 | 0.90.0→0.91.0 版本面：SKILL.md frontmatter 权威源 bump + verify_workflow.py 六锚手钉（REL-091 先例——仅版本字面量零逻辑变更，M-3 CODE 亲证）+ `release-projection --write` 再生 17 面（**幂等四度：17→0→0→审查复跑 0**，28b 消解）+ 双根 entry sync + CHANGELOG 0.91.0 准备态段 + 收编三份 R0 审查报告 | `bc3f052`（2026-09-28 01:42） | EVD-1208；REVIEW-REL-094-R0 AWN/0（盘上 `docs/reviews/review-REL-094-M1-R0.md`——N-1 第二从句缺 / N-2 行为变更段未落 = 准备态正确姿态，转发布态义务） |
| **M-1R 基线面** | REL-094 M-1R | 基线锚定族 sanctioned regen：archguard ratchet 重锚（R1 anchor 26358→26385，+27 授权增量归因链在案；R4 1318 不变）+ M0 fixture 双源重钉（behavior-protocol.md [512,556]→[522,566]、SKILL.md [223,230]→[225,232]——FEAT-072 授权变更所致漂移，**rebaseline 溯源块携带 prior 双源哈希逐字节存档**，DEC-262② 同型非静默漂移）+ 冻结字面量同步；loop_runtime 归因 = 机本地敏感不可复现（3 次定向 PASS 含审查独立复现——内部登记处置见 checklist 放行条件⑩） | `98104cb`（2026-09-28 02:32） | EVD-1209；REVIEW-REL-094-R1 AWN/0（盘上 `docs/reviews/review-REL-094-M1R-R0.md`） |
| **M-2 门禁实测** | REL-094 M-2/M-2R | **双源全量零失败**：pwsh-170（Coordinator，1364.03s）+ pwsh-171（M-3 RELEASE 审查者独立复跑，1394.55s）均 **4359 passed / 0 failed / 1 skipped / 527 subtests**——0.88 以来首次零失败全量（0.89=4217P/8F 披露、0.90=4351P/1F M0-pin 族披露——本批 M0 双源重钉后既有族消解） | —（纯门禁实测） | EVD-1210（P2-1 闭合——M-3 RELEASE 补账义务履行） |
| **M-3 双半面审查** | REL-094 M-3 | **R2 CODE 半面**（`docs/reviews/review-REL-094-M3-CODE-R0.md`——AWN/0，P0=P1=P2=0、P3×3：N-1 第二从句 / N-2 终账时点表述 / N-3 WARN 24 预期态）+ **R3 RELEASE 半面**（`docs/reviews/review-REL-094-M3-RELEASE-R0.md`——AWN/0 建议有条件 GO，unresolved_blockers=0，P2×2 / P3×5，**DEC-267(5) 停止条件十条逐条零触发**，放行条件⑤~⑩产出） | — | REVIEW-REL-094-R2 / REVIEW-REL-094-R3 机录行（evidence-log L2868/L2870） |
| **M-4 修复窗 + 登记收口 + 本批** | REL-094 M-4 | DEC-268：①风险窗复评留痕（09-30 窗内履行——RISK-036/039/047/048/050/059 逐条，见下「风险窗」节）②FEAT-073 治理票五要素登记（DEC-267(2) 承接——plan-tracker L80 已登记）③M-2 双源 EVD 机录（P2-1 闭合）；**④ 发布文档批 = 本票**（四件套——M-3 RELEASE 放行条件④履行；提交后由 Coordinator 机录 EVD〔预留编号 EVD-1211，以实际机录为准〕） | 本票（Coordinator 提交后为候选提交） | 待提交 |

### 本版不发布什么（显式排除——Amazon 实践）

1. **B-12 / B-13 机制翻转**（DEC-268(1) 不翻转确认——守卫 token 零命中实锤、五前置未齐备，翻转留独立授权票；RISK-059 维持打开）；
2. **FEAT-073 strict 注入预算治理票执行**（DEC-268(2) 已登记五要素——0.92.0 批承载，本版只登记不执行；优先去重瘦身、不单为转绿抬限）；
3. **28c 正则跨行加固**（REVIEW-FIX-399-R0 P2-1——0.91+ 候选池出槽，plan-tracker 已登记）；
4. **loop_runtime 去环境化改造票**（M-3 RELEASE 裁决内部登记——0.92 候选池，不入 CHANGELOG 已知限制；红线=M-2 终版复跑该族再现 FAIL 须归因重评禁静默豁免）；
5. **任何 RISK 的关闭声明**（DEC-268 六风险复评全部维持/观察，无关闭承诺）；
6. **权威翻转 / 纵向切片 / 行为级终态验收**（0.90 版本定义边界 DEC-263 面不变——本版不推进结构切换批次）。

## 风险窗引用（DEC-268(1) 复评留痕——09-30 窗内履行）

| 风险 | 复评结论（DEC-268 实读） |
|---|---|
| RISK-036 | 维持（1.0.0 官方收录准备边界不变——本版不涉及市场面） |
| RISK-039 | 维持（ArchGuard R1~R7 棘轮已重锚 26385 且全绿，缺口面不因本批扩大） |
| RISK-047 | 维持观察（review-record force 覆盖语义——本链 review-record 零 force 使用） |
| RISK-048 | 维持观察（loop_runtime 环境敏感——内部登记不入 CHANGELOG，去环境化票入 0.92 候选池，红线=M-2 终版复跑该族再 FAIL 须归因重评禁静默豁免） |
| RISK-050 | 维持（dsh 上游耦合——2026-10-31 到期不变，本版 release-projection 机制未触 dsh 内部行） |
| RISK-059 | **不翻转确认**（B-12/B-13 随版不翻转——窗口 diff 守卫 token 零命中〔M-3 审查实锤〕，五前置未齐备，翻转仍需独立授权票） |

## 回滚区间锚定（与 rollback-plan-0.91.0 §区间锚定同锚同源）

**本版回滚区间（triage 锚定）= `3f87459..<发布 tip>`**（回退点 = `v0.90.0` tag；`3f87459` = tag peel = 0.90.0 transition 提交实测；tag object `d2b2a6d`，taggerdate 2026-09-27 22:07:49 +0800 实测——FIX-349 口径 taggerdate 权威）：

- **论证①（下界 = `3f87459`，本版单轨无双轨分歧）**：git 区间语义 `X..Y` 排除下界自身。载荷两票（FEAT-072 + FIX-399）+ M-1 版本面 + M-1R 基线面**全部落在 `3f87459` 之后**；搭窗提交（`8d25101` 0.90.0 发布后披露批——非行为载荷）亦在 tag 后落库，如实纳入区间（回退影响 = 披露文档面，见 rollback-plan-0.91.0）。单轨，M-3 审查已复核单轨锚定与窗口计数（M-3 RELEASE 亲跑 #2/#9：窗口 diff 37 文件恰=载荷两票+六锚版本字面量+基线面——冻结边界未越界）。
- **论证②（终点必须是 `<发布 tip>`，不得是候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，本文件不预编造）。
- **窗口计数如实登记**：`git rev-list --count 3f87459..HEAD` = **5**（2026-09-28 实测，HEAD = `98104cb`；`git describe` = v0.90.0-5-g98104cb 交叉印证）；区间计数不写死——M-5 现场以 `git rev-list --count 3f87459..<发布 tip>` 取值记入 EVD。

## M-链状态（截至本文件落盘 2026-09-28）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 载荷冻结 | ✅ 完成（arch GO） | DEC-267（2026-09-28）：载荷两票冻结（FEAT-072 `196894a` + FIX-399 `9bafdf6`，均 R0 AWN/0）+ 合并态联合回归 54+20 OK + strict 9 tok 处置(a) + 披露分层 + 停止条件十条产出；冻结记录含合并态 HEAD 证明（冻结时 HEAD=`9bafdf6`） |
| 载荷两票 | ✅ 完成 | FEAT-072（`196894a`，EVD-1204）→ FIX-399（`9bafdf6`，EVD-1205/1207）——批序按 DEC-266(5)（契约先落、验证器修复在其上验证）；同文件（verify_workflow.py）三段 hunk 各归其票，M-3 CODE §1.1 亲证非交叉夹带 |
| M-1 版本 bump | ✅ 交付（已落库） | `bc3f052`（2026-09-28 01:42）：六锚手钉 + release-projection 再生 17 面**幂等四度**（17→0→0→0）+ 双根 entry sync + CHANGELOG 0.91.0 准备态段；EVD-1208；REVIEW-REL-094-R0 AWN/0 |
| M-1R 基线面 | ✅ 交付（已落库） | `98104cb`（2026-09-28 02:32）：archguard 重锚 26358→26385 + M0 双源重钉（rebaseline 溯源块 prior 逐字节存档）+ 冻结字面量同步；EVD-1209；REVIEW-REL-094-R1 AWN/0 |
| M-2 门禁实测 | ✅ 完成（双源） | **4359P/0F/1S/527 双源**（pwsh-170 1364.03s + pwsh-171 1394.55s——EVD-1210）；check-governance 20 issues 唯一 FAIL=28s（既有 DEC-264 披露族）；injection budget 三档 4241/5719/5991 全 PASS；check-projection-sync 28/28（M-3 亲跑 @HEAD）；check-version-consistency PASSED（唯一 WARN 24 = plan-tracker 版本过渡态预期，M-8 收口项） |
| M-3 双半面审查 | ✅ 完成（双 AWN/0） | R2 CODE（P0=P1=P2=0、P3×3 非阻塞）+ R3 RELEASE（unresolved_blockers=0、停止条件十条零触发、放行条件⑤~⑩产出）——REVIEW-REL-094-R2/R3 机录行在案 |
| M-4 修复窗 + 登记收口 | ✅ 风险窗与登记面完成 / 🔄 本批执行 | DEC-268：六风险复评留痕 + FEAT-073 五要素登记 + M-2 EVD 机录（P2-1 闭合）；**M-4④ 发布文档批 = 本票**（放行条件④——四件套，Coordinator 提交后消解） |
| M-5 candidate | ⏳ Coordinator 面 | 放行条件⑤⑥：`core/releases/0.91.0.json` 创建（N-4 义务）+ manifest lifecycle candidate→transition + CHANGELOG 发布态改写（日期 taggerdate 权威 / B-15 行为变更段 / N-1 第二从句 / 已知边界四条重测落字 / 终账补记） |
| M-6 预推校验 | ⏳ M-5 后 push 前 | 放行条件⑦：release-ledger 本地+remote 双 PASS（NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装 PASS） |
| M-7 tag+push | ⏳ Coordinator 面 | 放行条件⑧：annotated tag `v0.91.0` + master/tag 原子推送 + taggerdate 权威回填 |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | 放行条件⑨⑩：归档迁移（范围扩展至 v0.90.0）+ integrity PASS + 版本收口（plan-tracker 0.90.0→0.91.0，消解 WARN 24）+ released 验证全 PASS + census/身份集维持至 tag |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-27 22:07 | v0.90.0 发布（tag taggerdate 22:07:49 +0800 权威，peel `3f87459`，tag object `d2b2a6d`） |
| 2026-09-27 | DEC-265 用户授权 → DEC-266 FEAT-072 契约裁决 → REL-093 M-8 搭窗批（`8d25101` 22:40）→ FEAT-072 载荷提交（`196894a` 23:43） |
| 2026-09-28 | FIX-399 载荷提交（`9bafdf6` 00:50）→ DEC-267 M-0 载荷冻结（arch GO）→ M-1（`bc3f052` 01:42）→ M-1R（`98104cb` 02:32）→ M-2 双源门禁（EVD-1210）→ M-3 双半面（R2+R3 AWN/0）→ DEC-268 M-4 收口 → **M-4④ 本批（四件套）** → M-5~M-8 待办（taggerdate 权威，另记） |

## 门禁摘要（M-2 实测已回填；M-5~M-8 数值待办不预填）

| # | 门禁面 | 实测 / 姿态 | 依据 |
|---|---|---|---|
| 1 | 全量 pytest（双源） | **4359P / 0F / 1S / 527 subtests**（pwsh-170 1364.03s + pwsh-171 1394.55s 同值双源——0.88 以来首次零失败全量；唯一 skip 为既有标记项）；M-3 改可执行代码须退回验证（0.88 §3 口径承袭） | EVD-1210；checklist M-2 席 |
| 2 | check-governance | **20 issues，唯一 FAIL=28s**（evidence-log 尺寸——M-3 RELEASE 审查时点 1,744,908B；点位随发布链自增、发布态 MUST 重测落字）；获准保留本身不构成停止条件（DEC-267(5) 末句）；WARN 2/14/15/24 全为既有 advisory（24=M-8 收口项预期态） | DEC-264 披露族；checklist 放行条件⑥ |
| 3 | 注入预算三档 | **lightweight 4241 / standard 5719 / strict 5991**（/6000 全 PASS——strict 余量 9 tok 四方复证）；已知边界 = FEAT-073 治理票（五要素已登记，0.92 批承载）；「计量或生成内容变化也可能越界」第二从句发布态逐字补入（N-1） | EVD-1208/DEC-267(2)；checklist 放行条件⑥ |
| 4 | 版本投影面 | check-projection-sync **28/28 PASSED**（M-3 亲跑 @HEAD；28b 维持绿）+ M-1 再生幂等四度（17→0→0→0）+ e2e 双面 blob 同一；check-version-consistency PASSED（唯一 WARN 24 预期态）；check-injection-contract 4 面/30 锚 PASSED | M-3 RELEASE 亲跑 #3~#5；checklist M-2 席 |
| 5 | candidate ledger 两态 | 本票时点 candidate manifest 未建（DEC-267(4) 不提前伪造——M-3 亲证 0.91.0 缺席）；M-5 创建后 MUST 复跑 `release-ledger --version 0.91.0 --no-remote`（期望 NATIVE_CANDIDATE PASS）→ M-6 `--remote` 双 PASS；UNKNOWN/BLOCKED 不得包装 PASS | checklist 放行条件⑤⑦ |
| 6 | archguard 棘轮 + census | R1~R7 全绿（M-1R 重锚 26385，+27 授权增量归因链在案；regen exemptions=1 既定携带，零新增豁免）；R4 census 1318 不变；census/身份集维持至 tag = 放行条件⑩红线（零新增未授权阻断项） | EVD-1209；DEC-268(1)；checklist 放行条件⑩ |

## 已知边界四条（发布态措辞——arch 分层口径，与 CHANGELOG 0.91.0 段同源）

1. **strict 注入预算余量 9 tok**：strict 档 5991/6000（M-1 后实测）——当前口径下净增超 9 tok 即越界；**计量或生成内容变化也可能越界**（DEC-267(2) 第二从句——发布态逐字补入）；FEAT-073 治理票已登记五要素（DEC-268(2)：计量器=check-injection-budget / 范围=DSH persona+入口注入面 / 基线=4241/5719/5991 / 责任人=Coordinator / 验收=三档 PASS 且 strict 余量恢复 ≥100 tok 或出具基准依据的重定标 DEC）。
2. **evidence-log 尺寸（Check 28s）**：1,737,424 bytes（≈1697KB，M-1 时点实测）→ 1,744,908 bytes（M-3 审查时点）——点位随发布链自增，DEC-264 既有结构性约束披露发布；0.91 池产品票候选（归档判据扩展族）；发布态重测落字。
3. **28c 正则跨行加固延期**：REVIEW-FIX-399-R0 P2-1（`[^*]*`→`[^*\n]*` 建议——V7 实证跨行吞噬形态）——0.91+ 候选池出槽（plan-tracker 已登记）；本版交付面为装饰尾巴容忍+末日期语义，跨行形态已知未修。
4. **版本面再生幂等纪律**：本版版本面经 `release-projection --write` 确定性再生（非手改——M-1：权威源 bump → written=17 → 幂等复跑 written=0 → 审查复跑 0，28 面收敛 28b 消解）；任何版本面后续变更 MUST 走同一再生路径。

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.90.0 三件套 + 0.89.0 release-plan 先例无缺面 | **PASS** | 结构逐节对照 `docs/release/{rollback-plan,feature-flags,release-checklist}-0.90.0.md` + `docs/release/release-plan-0.89.0.md`（0.90.0 无 release-plan 先例——0.89.0 为最近模板）；全表行内零裸管道符（FIX-365 ragged 教训） |
| 回滚区间实测 | **PASS** | `git rev-list --count 3f87459..HEAD` = **5**；`git describe` = v0.90.0-5-g98104cb 交叉印证；`3f87459` = `git rev-parse v0.90.0^{}` 实测同一（tag object `d2b2a6d`，taggerdate 2026-09-27 22:07:49 +0800） |
| 内容事实源引用准确 | **PASS** | 载荷两票 commit/EVD（EVD-1204/1205/1207/1208/1209/1210）逐项对照 git log 实测 + CHANGELOG 0.91.0 段实读；DEC-265~268 取自 `.governance/decision-log.md` 实读（UTF-8）；审查终态取自盘上六份报告实读 + REVIEW×4/TRIAGE×3 机录行实读；FEAT-073 五要素取自 plan-tracker L80 实读；28s/预算/双源数值取自 EVD-1210 与 M-3 审查亲跑记录 |
| check-manifest-consistency / check-cross-references | 见本票验证记录（四件套落盘后运行） | docs/release 四文件与 0.90.0 先例同形态（manifest 不逐文件登记 docs/ 面——两检查器落盘后实测） |
| 真实 `.governance/` 零写入 | **PASS** | 写入面 = 四件套（REL-094 M-4④ files 锁定）；不触治理数据、不改产品代码、不执行 tag/push/transition；EVD 机录由 Coordinator 执行（本票预留编号 EVD-1211 仅为待办注记，非已入账事实） |

---
*REL-094 M-4④ 起草冻结（2026-09-28，Governance Developer Agent）。事实基线：5 提交窗口与 hash/日期取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.90.0^{}`/`git for-each-ref refs/tags/v0.90.0` 实测（`3f87459..98104cb` = 5；v0.90.0 taggerdate 2026-09-27 22:07:49 +0800 = peel `3f87459`）；载荷两票、已知边界四条、决策链口径取自 CHANGELOG 0.91.0 段（M-1 交付准备态——project/CHANGELOG.md canonical）与 DEC-265~268 实读（`.governance/decision-log.md`，UTF-8）；M-2 双源数值取自 EVD-1210 机录行实读；M-3 双半面结论与放行条件⑤~⑩取自 `docs/reviews/review-REL-094-M3-CODE-R0.md` / `review-REL-094-M3-RELEASE-R0.md` 实读；FEAT-073 五要素取自 `.governance/plan-tracker.md` L80 实读；archguard/M0 重钉数值取自 EVD-1209 实读。未生成事实（发布 tip、tag、M-5~M-8 门禁数值、candidate manifest 提交、B-15 发布态铸造、发布日期）一律标期义务/回填位，不预填。*
