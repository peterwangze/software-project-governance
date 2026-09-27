# Release Checklist — 0.91.0

- **版本**: 0.91.0 · **日期**: 2026-09-28 · **状态**: **已发布 v0.91.0**（tag taggerdate 2026-09-28 05:24:03 +0800 权威，peel `bd9bfc1`；M-0~M-7 完成——⑤~⑧ 勾选回填见下表；M-8 归档+版本收口进行中）
- **主题**: 推荐契约与误报消解（Recommendation Card Contract & False-Positive Fix）——FEAT-072 + FIX-399 载荷 / DEC-265~268 / EVD-1204~1210
- **版本定义**: 完成 DEC-267 M-0 冻结范围内推荐卡契约交付与 Check 28c 误报消解（arch GO 有条件冻结）；**无破坏性变更、无机制激活（B-12/B-13 出厂姿态不变）；权威翻转与行为级终态验收不在本版**（DEC-263 边界延续）。

## 发布范围（冻结清单——DEC-267(1)）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-072 | 完成必推荐三要素推荐卡契约（DEC-266）——M7.4 6b/6c 重写+四注入面投影+canonical 三标签锚（existence-only）+负例测试；persona 净增 +76B（standard/strict 两档 PASS） |
| 载荷 | FIX-399 | Check 28c 发布日期解析器装饰日期单元格健壮性——正则容忍装饰尾巴+多日期取末日期（发布日）语义+恰 6 测试用例；同数据 A/B 净效果 −1 误报零新增 |
| 版本面 | REL-094 M-1 | 0.90.0→0.91.0 权威源 bump+六锚手钉+release-projection 再生 17 面（幂等四度）+双根 entry sync+CHANGELOG 0.91.0 准备态段+收编三份 R0 报告 |
| 基线面 | REL-094 M-1R | archguard 棘轮重锚（R1 26358→26385，+27 授权增量在案）+M0 双源重钉（rebaseline 溯源块，prior 双源哈希逐字节存档）+冻结字面量同步 |

无破坏性变更（M-3 CODE 亲证：CLI 零旗标增删改、无接口删除、无格式破坏）；无机制激活（DEC-268(1) 不翻转确认——守卫 token 零命中）。

## M-链完成态勾选（M-0~M-4——锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 载荷冻结 | ✅ 完成 | DEC-267（arch GO，2026-09-28）：载荷=FEAT-072 `196894a`+FIX-399 `9bafdf6`（均 R0 AWN/0）+合并态联合回归 54+20 OK+strict 9 tok 处置(a)+停止条件十条产出；冻结记录含合并态 HEAD 证明（冻结时 HEAD=`9bafdf6`） |
| M-1 版本 bump | ✅ 完成 | `bc3f052` · EVD-1208 · REVIEW-REL-094-R0 AWN/0（盘上 `docs/reviews/review-REL-094-M1-R0.md`）——再生幂等四度 17→0→0→0（28b 消解）；审查 N-1（第二从句）/N-2（行为变更段）转发布态义务（放行条件⑥） |
| M-1R 基线面 | ✅ 完成 | `98104cb` · EVD-1209 · REVIEW-REL-094-R1 AWN/0（盘上 `docs/reviews/review-REL-094-M1R-R0.md`）——R1 重锚 26358→26385+M0 重钉 prior 存档；loop_runtime 归因=机本地敏感不可复现（内部登记→0.92 池，放行条件⑩） |
| M-2 门禁实测 | ✅ 完成（双源） | EVD-1210（P2-1 补账闭合——DEC-268(3)）：**4359P/0F/1S/527 subtests 双源**（pwsh-170 Coordinator 1364.03s + pwsh-171 M-3 RELEASE 审查者独立复跑 1394.55s）——0.88 以来首次零失败全量（0.89=4217P/8F、0.90=4351P/1F 既有族经 M0 重钉消解） |
| M-3 双半面审查 | ✅ 完成（双 AWN/0） | **R2 CODE**（盘上 `docs/reviews/review-REL-094-M3-CODE-R0.md`——P0=P1=P2=0、P3×3 非阻塞：N-1 第二从句/N-2 终账时点表述/N-3 WARN 24 预期态）+ **R3 RELEASE**（盘上 `docs/reviews/review-REL-094-M3-RELEASE-R0.md`——unresolved_blockers=0、P2×2/P3×5、**停止条件十条逐条零触发**、放行条件⑤~⑩产出）；REVIEW-REL-094-R2/R3 机录行在案 |
| M-4 修复窗+登记收口 | ✅ 登记面完成 / 🔄 文档批=本票 | DEC-268：①风险窗六风险复评留痕（036/039/047/048/050/059——09-30 窗内履行）②FEAT-073 五要素登记（plan-tracker L80）③M-2 双源 EVD 机录；**④发布文档批 = 本票**（放行条件④——release-plan/rollback/feature-flags/checklist 四件套，Coordinator 提交后消解；EVD 预留编号 1211 待机录） |

## M-2 门禁实测回填（全席——实测值，不预填面已消解）

| # | 门禁面 | 实测值 | 判定 |
|---|---|---|---|
| 1 | 全量 pytest（双源） | **4359P / 0F / 1S / 527 subtests**（1364.03s + 1394.55s 同值双源） | PASS |
| 2 | check-governance | **20 issues；唯一 FAIL=28s**（1,744,908B @M-3 审查时点——点位随发布链自增；DEC-264 披露族获准保留，本身不构成停止条件〔DEC-267(5) 末句〕）；WARN 2/14/15/24 既有 advisory | PASS（28s 披露发布） |
| 3 | 注入预算三档 | lightweight **4241** / standard **5719** / strict **5991**（/6000 全 PASS，strict 余量 9 tok 四方复证） | PASS（FEAT-073 票承接） |
| 4 | check-projection-sync | **28/28 PASSED**（M-3 亲跑 @HEAD）；M-1 再生幂等四度 17→0→0→0 | PASS |
| 5 | check-injection-contract | 4 面/30 锚 PASSED（含 canonical behavior-protocol 三完整标签 existence-only） | PASS |
| 6 | check-version-consistency | PASSED；唯一 WARN 24（plan-tracker 0.90.0 vs expected 0.91.0——发布链进行中预期态，M-8 收口消解） | PASS（WARN 挂账 M-8） |
| 7 | archguard 棘轮 R1~R7 | 全绿（R1 重锚 26385——+27 授权增量归因链在案；R4 census 1318 不变；exemptions=1 既定携带，零新增豁免） | PASS |
| 8 | release-ledger | candidate 未建（DEC-267(4) 不提前伪造——M-3 亲证 `core/releases/0.91.0.json` 缺席=M-5 义务） | NOT_RUN（M-5 义务，见放行条件⑤⑦） |

## M-5~M-8 待办（M-3 RELEASE 放行条件⑤~⑩ 逐项——有条件 GO 的条件本体）

| 条件 | M | 发布态义务 |
|---|---|---|
| ⑤ ✅ | M-5 | 创建 `skills/software-project-governance/core/releases/0.91.0.json`（N-4 义务；NFC/sorted/compact 同 0.90 形态）+ manifest lifecycle candidate→transition（单父=候选 commit；tip 以 M-5 现场 `git rev-parse HEAD` 为准）+ check-release candidate 态执行（DEC-267(4)「不提前伪造完成态」至此解除）——**✅ 完成回填（M-8 批）**：releases json 随 `fed2f53`（M-5 candidate manifest）入库 + transition 提交 `bd9bfc1`（M-5b，candidate→released 单父翻转，单父=`fed2f53`，0.90 先例 `3f87459` 同型）；态验证面归 M-8 released 复跑（⑨） |
| ⑥ ✅ | M-5 | CHANGELOG 发布态改写（单 canonical=project/CHANGELOG.md——DEC-242① 继承；原「project+root 投影双位同步」为 0.88 模板残留，M-5 审查 P3-2 勘正）：发布日期=FIX-349 taggerdate 权威（M-7 后回填）+ **行为变更段落段（N-2——B-15 命名承接 B-1~B-14 序列：推荐呈现形态升级 + 回滚说明=git revert 序列/零数据迁移/零 flag 面 + 无依赖变更 stdlib-only）** + **DEC-267(2) 第二从句「计量或生成内容变化也可能越界」逐字补入（N-1）** + 已知边界四条发布时点重测落字（28s 现值/strict 复测/候选池出槽/再生纪律）+ 终账/Commit 区间/发布验证结论补记 + 「HEAD 即此 commit」时点表述改写（M-3 CODE N-2）——**✅ 完成回填（`fed2f53` 发布态改写 + M-8 批收口）**：B-15 段/N-1 第二从句/边界四条重测已在段（fed2f53）；标题日期 2026-09-28 与终账/Commit 区间已回填（M-8 批） |
| ⑦ ✅ | M-6 | release-ledger 本地+**remote** 双 PASS（NATIVE_RELEASED；tag_facts local==remote；UNKNOWN/BLOCKED 不得包装 PASS——0.90 条件同型）——**✅ 完成回填（M-8 批）**：本地+remote 双 PASS / NATIVE_RELEASED / issues=[]（M-6 ledger 权威实测） |
| ⑧ ✅ | M-7 | annotated tag `v0.91.0` + push（peel 机制：tag object→commit；ledger tag_facts 双端核对）+ master push；**taggerdate 权威回填** CHANGELOG 日期与路线图行（FIX-349 口径）——**✅ 完成回填（M-8 批）**：tag object `0ea429f`（peel=`bd9bfc1`，taggerdate 2026-09-28 05:24:03 +0800 权威）+ push 完成（origin master `8d25101..bd9bfc1` + tag）；CHANGELOG 日期已回填 2026-09-28（本批），路线图 0.91.0 行（plan-tracker 版本行表 L282）实测已呈已发布态 2026-09-28——M-8 收口面已在位（本批只读核查） |
| ⑨ 🔄 | M-8 | 归档迁移（范围扩展至 v0.90.0——M-3 预估增量：任务行 ~6-9/证据行 ~12-18，以现场 dry-run 复测为准）+ check-archive-integrity PASS + **版本收口**（plan-tracker 工作流版本 0.90.0→0.91.0 消解 WARN 24；版本行表序归位——M-3 P3-5）+ 路线图 0.91.0 行终态回填 + released 验证（lineage/changelog/archive/docs/fact-source 全 PASS）+ session-snapshot 三要素投影行首用（FEAT-072 SHOULD 面）——**🔄 M-8 进行中（Coordinator 面）**：发布态回填批已落（本批——日期/taggerdate/tip 占位消解 + ⑤~⑧ 勾选回填 + ⑥括注勘正）；归档迁移+版本收口+released 终验待收口 |
| ⑩ | M-8 | **census/身份集维持至 tag**——零新增未授权阻断项（0.90 条件同型红线）；loop_runtime 裁决执行=内部登记（0.92 候选池去环境化票，不入 CHANGELOG 已知限制）；红线=终版复跑该族再现 FAIL 须归因重评禁静默豁免（DEC-268(1)） |

## 已知问题与边界（四条——DEC-267(2) arch 分层口径，与 CHANGELOG 0.91.0 段同源）

1. strict 注入预算余量 9 tok（5991/6000 @M-1 后实测）——当前口径下净增超 9 tok 即越界；计量或生成内容变化也可能越界（N-1 发布态补入）；FEAT-073 五要素已登记（0.92.0 批承载——优先去重瘦身，不单为转绿抬限）
2. evidence-log 尺寸（Check 28s）——1,737,424B（M-1 时点）→1,744,908B（M-3 审查时点）；DEC-264 结构性约束披露发布；0.91 池归档判据扩展票候选；发布态重测落字（放行条件⑥）
3. 28c 正则跨行加固延期——REVIEW-FIX-399-R0 P2-1 → 0.91+ 候选池（plan-tracker 已登记出槽）；本版交付面为装饰尾巴容忍+末日期语义，跨行形态已知未修
4. 版本面再生幂等纪律——`release-projection --write` 确定性再生非手改（written=17→幂等复跑 0）；版本面后续变更 MUST 走同一再生路径

## 发布后验证计划

- check-release `--lineage-mode released --release-commit <sha>` PASS（tag peel 本地=remote + ledger 单父 transition + 非 UNKNOWN/BLOCKED）
- 归档 integrity PASS（M-8）
- 核心功能冒烟：`/governance` bootstrap（0.91.0）+ governance-bootstrap 热数据面正常 + 完成必推荐三要素卡呈现（FEAT-072 行为面——单候选/三候选/空推荐结构化空原因三态）
- 观察期：发布后 48h 无新增 P0/P1 报告（内部工具替代标准）
- **回滚触发绑定**：观察期内出现任一情形 → 立即进入 hotfix 0.91.1 或 tag 回退决策（按 rollback-plan-0.91.0；历史 tag 变更须独立 DEC）：①新增 P0/P1 缺陷报告 ②`/governance` bootstrap 或 governance-bootstrap 冒烟失败 ③check-release released 复跑 FAIL

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
