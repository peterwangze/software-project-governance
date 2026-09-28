# Release Plan — 0.92.0（REL-095 M-4 发布文档批）

> **任务**: REL-095（P1；DEC-269 批启动 → DEC-274 总授权〔含 BT-01 首会话抽测承诺兑现〕→ DEC-278 28s 结构性解锁三单元 → DEC-282 M-0 条件冻结+版本口径）· **日期**: 2026-09-29 · **性质**: M-4 发布文档面（本票为四件套：release plan/checklist/rollback/feature-flags——非发布执行；M-3 RELEASE 有条件 GO 放行条件①〔四件套——RL-F3〕+②〔FAILED-7 全貌口径——RL-F2〕随本票承载，③风险窗引用随文，④双报告机录由 Coordinator 执行；⑤~⑩ 发布态义务逐项列入 checklist）
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-274 预授权链覆盖 0.92.0 单一版本发布链；例外到期处置与 0.93 准入为独立决策面仍走用户确认；预授权**不免除** M-5~M-8 各门禁实测与放行条件；安全语义不因授权削减）；本文件由 Governance Developer Agent 起草，供 M-5 candidate 批与发布态收口消费
> **写入边界**: 仅本四件套（REL-095 M-4 files 锁定面）；不触 `.governance/` 真实治理数据、不修改产品代码、不执行 tag/push/transition；`skills/software-project-governance/core/releases/0.92.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-5 提交批创建（M-3 RELEASE 亲证 0.92.0 缺席=M-5 义务；DEC-282 不提前伪造完成态，本票如实披露，见 checklist 放行条件⑤）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim / No marketplace approval claim**：official approval 与 marketplace approval 未被授予、未被主张；RISK-036 维持打开（M-0 前窗 2026-09-28 复评留痕——0.92.0 为治理内收尾版，check-release official faces 全 PASS 维持不构成外部验证）。
- **No universal/full runtime support claim**：非 Windows 平台未验证；本版全部验收在仓库内与隔离环境口径下完成，隔离验收不等于真实外部环境验证通过。
- **No 1.0.0 production-ready claim**：RISK-036 继续打开；do not claim 1.0.0 production-ready。
- **容量问题未技术消除（本版核心 no-overclaim 句——DEC-282(7)）**：「结构性解锁已完成；容量问题未技术消除。本轮不执行 EVD 物理迁移，按限期例外控制，后续迁移以读取契约闭合为前提。」——精确措辞：**178 行历史证据面未迁移由 EXC-002 纸质例外治理**；18 行有界迁移（2 任务+18 EVD）属 DEC-284 补完成授权，非「本轮不执行」矛盾。
- **例外非续期承诺**：EXC-001/EXC-002 均**不自动续期**（2026-10-12 硬到期；EXC-001 recheck_on 2026-10-05；延期须重审批非周报续期）；到期未完成 0.93 准入 → 28s/Check 27 恢复硬阻断 → 发布冻结直至重评（rollback-plan §EXC 到期处置）。
- **发布 tip 未生成前不预先编造（起草期纪律）**：发布 tip（M-5b transition 提交）与 tag 事实本四件套起草期不预填，hash 由 M-5/M-7 生成后回填（FIX-349 口径：taggerdate 权威）。
- **发布日期不预填**：CHANGELOG 0.92.0 段维持「未发布（准备态）」，发布态日期落字按 taggerdate 权威（M-7 后回填——checklist 放行条件⑥）。
- **M-5~M-8 数值不预填**：candidate manifest、ledger 双端核对、taggerdate、released 验证均为待办回填位——本票只列义务不写通过性数值（已知边界点位数值均带时点标注，发布态 MUST 重测落字）。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.92.0**（MINOR；0.91.0 → 0.92.0 顺延 +1、不跳号、无预留占用；无 0.92.x tag 冲突；CHANGELOG 0.92.0 段同源） |
| 发布任务 | **REL-095**（M-0 DEC-282 条件冻结 → M-1 `40eb6f7` → M-2 整改链〔`12bef7c`+`df26f7e`；EVD-1233/1234/1235〕→ M-3 双半面 → M-4 本批）——功能载荷锚 `dc45e24`（DEC-282） |
| 授权链 | **DEC-269**（0.92 批启动）→ DEC-271/272（FEAT-073 路线裁决与完成入账；BT-01 抽测承诺）→ DEC-274（0.92.0 总授权）→ DEC-278（28s 结构性解锁三单元）→ DEC-279~281（三单元完成入账）→ **DEC-282（M-0 条件冻结+版本口径+四封口）** → DEC-283/284/285（M-2 整改三裁决——受控回退／有界迁移扩展授权／EXC-002 纸质例外） |
| MINOR 依据 | DEC-282(7) 版本口径：「strict 注入预算优化、发布与运行时验证稳定性修复，证据分层结构性解锁与本轮明确遗留项收尾」；六票载荷非纯 bug fix（PATCH 不适用）；Breaking changes = **无**（M-3 CODE 聚合终审：窗口 diff 51 文件 +5333/−216〔六票+发布链对账区间 `e65b317^..df26f7e`，搭窗 `4cb3081` 除外；全窗 `bd9bfc1..df26f7e`=56 文件 +5523/−239〕全部可归因六票申报面或发布链提交——无未申报夹带；共享文件跨票演进零接口冲突） |
| 行为变更面 | **无新增 flag**（见 feature-flags-0.92.0）；行为变更 = **B-1~B-7**（strict persona 单源化／release-gate 超时预算／loop 计时去环境化／例外标注机制／LRC 豁免第 5 条／有界迁移 18 EVD 出热／archguard 两次 regen——每项含回滚，feature-flags §非旗标面） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；发布文档面由 Governance Developer Agent 执行，M-3 双半面 Reviewer 独立审查（R2 CODE / R3 RELEASE 均 AWN/0——unresolved_blockers=0） |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带行为变更段（B-1~B-7——无破坏性变更；数据面有界迁移 18 EVD 出热经实弹演练、消费者读取契约〔archive/index.md〕不变，M-5 落段） |

## 发布范围

### 载荷构成（六票载荷 + M-1/M-2 版本与整改面 + M-3/M-4 审查链——DEC-269~285）

> git 窗口实测（2026-09-29）：**0.92.0 窗口 = `bd9bfc1..<发布tip 回填位>`**（下界 `bd9bfc1` = v0.91.0 tag peel 实测——tag object `0ea429f`，taggerdate 2026-09-28 05:24:03 +0800 权威；`git rev-list --count bd9bfc1..HEAD` = **13**（HEAD = `df26f7e`）；`git describe` = v0.91.0-13-gdf26f7e 交叉印证）。**载荷六票与 CHANGELOG 0.92.0 段同源**（DEC-282 冻结边界内——功能载荷锚 dc45e24）。

| 批 | 任务 | 关键交付 | 提交 | 证据／审查 |
|---|---|---|---|---|
| **搭窗（0.91.0 期收尾）** | REL-094 M-8 | 0.91.0 发布态回填批（CHANGELOG 日期 taggerdate 回填+release docs tip 回填+checklist ⑤~⑧ 勾选+归档 verify+版本收口）——**非 0.92 行为载荷**（回退影响 = 披露文档面，如实纳入区间） | `4cb3081`（09-28 05:54） | REVIEW-REL-094-R7 AWN/0 |
| **载荷一** | FEAT-073 | **strict 注入预算 persona 单源化+薄指针压缩**——strict 余量 **9→391 tok**；三档实测 lightweight **3859**/standard **5337**/strict **5609**（/6000 全 PASS）；strict 档会话更轻 | `e65b317`（09-28 11:23） | EVD-1216~1219；FEAT-073-R0 AWN/0→R1 AWN/0 |
| **载荷二** | FIX-400 | **release-gate 墙钟预算 180→2333s 再校准**（=ceil(1554.78×1.5)——DEC-262 先例同式）；门禁信号恢复可信；regen 分离提交 26385→26413 | `a7bcd5f`+`f06a2bf`（09-28 12:04/12:06） | EVD-1220~1222；FIX-400-R0 AWN/0 |
| **载荷三** | FIX-401 | **loop_runtime 计时断言去环境化**（墙钟→process_time）——并行负载假红消除；RISK-048 收窄（预算 27.0→27.8） | `136d65e`（09-28 18:08） | EVD-1223~1224；FIX-401-R0 AWN/0（盘上 `docs/reviews/review-FIX-401-R0.md`） |
| **载荷四** | FEAT-074 | **证据行五态实体感知分类替代单桶**（28s 结构性解锁——DEC-278 单元一）；输入锚=设计准入盘点文档（`b6575bd`，申报面内——CR-F6） | `b6575bd`+`c90768f`（09-28 18:17/20:08） | EVD-1225~1226；FEAT-074-R0 NC→R1 AWN/0 |
| **载荷五** | FEAT-075 | **四族只读 dry-run scan-families**（EVD 477/REVIEW 640/RECO 159/TRIAGE 199——五态子分解完整）+**发布聚合层例外标注机制 exception_registry**（annotation-only 不改原始结果/字节/退出码；dry-run 零写入代码级强制）；regen 分离提交 26413→26478 | `16a5157`+`484dd77`（09-28 21:34/21:36） | EVD-1227~1228；FEAT-075-R0 NC→R1 AWN/0 |
| **载荷六** | FIX-402 | **160 唯一 ID 八类台账+确定性数据校正**（DEC-278 单元三）；C-2 写回 11 处（留热 11 行口径与 dry-run `active_task_ref: 11 rows` 吻合）——**功能载荷锚** | `dc45e24`（09-28 22:43） | EVD-1229；FIX-402-R0/R1 NC→R2 AWN/0；台账 `docs/governance/fix-402-data-corrections-ledger-20260928.md` |
| **M-1 版本面** | REL-095 M-1 | 0.91.0→0.92.0 版本面：权威源 bump+六锚+`release-projection --write` 单次写入 17 面→幂等复跑 written=0+双根 entry sync+CHANGELOG 准备态段 | `40eb6f7`（09-28 23:12） | EVD-1230/1231/1232；REVIEW-REL-095-M1-R0 AWN/0 P3×1 |
| **M-2 整改链** | REL-095 M-2/M-2R | 首跑 4 失败面→DEC-283 受控回退 6 归期行→DEC-284 扩展授权有界迁移 2 任务+18 EVD〔EVD-1233；验收 5/6：18/18 精确／守恒 2921+522／幂等 0/0〕→EXC-002 纸质例外承接剩余 178 行〔DEC-285；基线附件 A=160 已归档任务债/B=4 FEAT-001 双在/C=14 裸 ID〕→B2 单条精确豁免 LRC-EXEMPT-FIX401R0-79-1〔九键实测+双锚 re-pin digest 4f8a6cc8→d47f5d16+正负因果测试；EVD-1234 六项验收 6/6〕→M-2R 复测@df26f7e 有条件收口〔EVD-1235〕 | `12bef7c`+`df26f7e`（09-29 00:10/00:27） | EVD-1233/1234/1235；REVIEW-REL-095-B2-R1 AWN/0 |
| **M-3 双半面审查** | REL-095 M-3 | **R2 CODE 聚合终审**（AWN/0——P2×2 advisory〔CR-F1/F2〕+P3×5；51 文件对账无夹带）+ **R3 RELEASE 发布审查**（AWN/0 **有条件 GO**——P2×1〔RL-F1 CHANGELOG M-5 改写〕+P3×3；check-release 只读复跑 FAILED-7 全貌+放行条件①~⑩产出） | —（纯审查） | 盘上 `docs/reviews/review-REL-095-CODE-R0.md` / `review-REL-095-RELEASE-R0.md`；机录轮位 round 2/3 |
| **M-4 本批** | REL-095 M-4 | ①四件套=本票（RL-F3）+②FAILED-7 全貌口径承载（RL-F2→checklist 核心表）+③风险窗引用+④M-3 双报告机录 | 本票（Coordinator 提交后为候选提交） | 待机录（EVD 编号以实际机录为准） |

### 本版不发布什么（显式排除——Amazon 实践）

1. **178 行历史证据面物理迁移**（EXC-002 纸质例外限期治理——0.93 承接 FEAT-076：五条件+91 物理未归档 ID 回填 C-3；后续迁移以读取契约闭合为前提）；
2. **EXC-001/002 到期续期**（均不自动续期；延期须重审批非周报续期——2026-10-12 硬到期）；
3. **RB-2/B-12/B-13 机制翻转**（独立授权票纪律不变——RISK-059 维持）；
4. **archive.py 拆分**（5508 行越阈 5000——CR-F2 advisory，0.93 拆分候选）；
5. **decision-log 容量治理票**（254,420B 超限——CR-F1 advisory，M-8 补披露后入 0.93 池）；
6. **Check 27 例外机接线化+消息措辞错标修复**（Check 27 走独立通路无例外机制接线——机注不可达注记 L222；「0 hot completed task(s)」实指 0.93 池——均 0.93 候选）；
7. **EVD 全量物理迁移与权威翻转**（DEC-282 C-1 边界——M-8 显式跳过 EVD 物理迁移+11 行留热口径）。

## 风险窗引用（M-0 前窗 2026-09-28 复评留痕——risk-log 亲读，M-3 RELEASE 重点 4 亲证）

| 风险 | 复评结论 |
|---|---|
| RISK-036 | 维持打开（0.92.0 为治理内收尾版；check-release official faces 全 PASS 维持；no-overclaim 边界维持——外部验证/官方提交/1.0.0 review 未满足） |
| RISK-039 | 维持打开（收窄维持——ArchGuard R1~R7 fatal gate 全绿 @c90768f；外部宿主验证关闭条件未满足） |
| RISK-044 | 维持缓解中（evidence-log 容量劣化趋势持续、根因侧处置在途——本版双例外+结构性解锁即处置面） |
| RISK-047 | 维持观察（review-record force 覆盖语义——0.92 会话至 M-3 时点机录 6 次全部零 force） |
| RISK-048 | **已缓解/收窄兑现**（FIX-401 `136d65e`——墙钟→进程 CPU，预算 27.0→27.8；2026-09-28 注记在案） |
| RISK-050/059 | 维持引用（REL-094 M-4 同型——dsh 上游耦合 2026-10-31 到期；B-12/B-13 翻转前置未齐备） |

## 回滚区间锚定（与 rollback-plan-0.92.0 §回滚区间锚定同锚同源）

**本版回滚区间（triage 锚定）= `bd9bfc1..<发布tip 回填位>`**（回退点 = `v0.91.0` tag）：

- **论证①（下界 = `bd9bfc1`，单轨无双轨分歧）**：git 区间语义 `X..Y` 排除下界自身。`bd9bfc1` = v0.91.0 tag peel 实测（`git cat-file -p v0.91.0` 亲证 tag object `0ea429f` → object `bd9bfc1`；taggerdate 2026-09-28 05:24:03 +0800 权威——FIX-349 口径）= 0.91.0 M-5b transition 提交；六票载荷+M-1+M-2 整改链**全部落在其后**；搭窗提交（`4cb3081` 0.91.0 发布态回填——非行为载荷）亦在 tag 后落库，如实纳入区间（回退影响 = 披露文档面）。
- **论证②（终点必须是发布 tip，不得是候选打包提交）**：0.81.0 先例 F-04——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突。**终点 = M-5b transition 提交（生成后回填——起草期不预编造纪律）**。
- **窗口计数如实登记**：`git rev-list --count bd9bfc1..HEAD` = **13**（2026-09-29 实测，HEAD = `df26f7e`；`git describe` = v0.91.0-13-gdf26f7e 交叉印证）；发布终值 = M-8 批回填位。区间内 13 提交（旧→新）：`4cb3081`→`e65b317`→`a7bcd5f`+`f06a2bf`→`136d65e`→`b6575bd`→`c90768f`→`16a5157`+`484dd77`→`dc45e24`→`40eb6f7`→`12bef7c`→`df26f7e`；本票（M-4 四件套+M-3 报告收编）提交后入区间。

## M-链状态（截至本文件落盘 2026-09-29）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 条件冻结 | ✅ 完成 | DEC-282（2026-09-28）：功能载荷锚 `dc45e24` + **四封口**（①例外登记+有效/失效路径验证 ②C-1 边界〔M-8 显式跳过 EVD 物理迁移+11 行留热口径+0.93 五条件〕③C-3 91 ID 转 0.93 ④封口动作完成声明）+ 版本口径(7) no-overclaim 附加句 |
| 载荷六票 | ✅ 完成 | FEAT-073 `e65b317` → FIX-400 `a7bcd5f`+`f06a2bf` → FIX-401 `136d65e` → FEAT-074 `b6575bd`+`c90768f` → FEAT-075 `16a5157`+`484dd77` → FIX-402 `dc45e24`——审查链全闭合（终态均 AWN/0；FEAT-074/075 经 NC 复审转正、FIX-402 经两轮 NC 至 R2）；M-3 CODE 对账 51 文件 +5333/−216 无未申报夹带 |
| M-1 版本 bump | ✅ 交付（已落库） | `40eb6f7`（09-28 23:12）：权威源+六锚+17 投影面单次收敛→幂等复跑 written=0+双根 entry sync+CHANGELOG 准备态；EVD-1230/1231/1232；REVIEW-REL-095-M1-R0 AWN/0 P3×1 |
| M-2 整改链 | ✅ 有条件收口 | 首跑 4 失败面 → DEC-283（受控回退 6 归期行+B2 一次性授权）→ DEC-284（有界迁移 2 任务+18 EVD——EVD-1233 验收 5/6）→ DEC-285（EXC-002 纸质例外）→ B2 `df26f7e`（EVD-1234 六项验收 6/6）→ M-2R 复测有条件收口（EVD-1235——「有条件收口/例外接受（非原生全绿）」原文如实登记，不篡改机器输出） |
| M-3 双半面审查 | ✅ 完成（双 AWN/0） | R2 CODE（P2×2 advisory+P3×5 非阻塞）+ R3 RELEASE（**有条件 GO**——unresolved_blockers=0、P2×1+P3×3、放行条件①~⑩产出）；盘上双报告在案 |
| M-4 修复窗 | 🔄 本批执行 | ①四件套=本票（放行条件①/RL-F3）②FAILED-7 全貌口径（放行条件②/RL-F2——checklist 核心表承载）③风险窗引用（放行条件③——本文件§风险窗引用）④双报告机录（放行条件④——Coordinator 面） |
| M-5 candidate | ⏳ Coordinator 面 | 放行条件⑤⑥：`core/releases/0.92.0.json` 创建+manifest lifecycle candidate→transition+CHANGELOG 发布态改写（RL-F1 全项——EXC-002 摘要并列+B2 豁免+有界迁移终账+决策链 269~285+EVD 含发布链+行为变更段+已知限制重测） |
| M-6 预推校验 | ⏳ M-5 后 push 前 | 放行条件⑦：release-ledger 本地+remote 双 PASS（NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装 PASS） |
| M-7 tag+push | ⏳ Coordinator 面 | 放行条件⑧：annotated tag `v0.92.0`+master/tag 原子推送+taggerdate 权威回填 |
| M-8 归档+收尾 | ⏳ Coordinator 面 | 放行条件⑨⑩：版本收口+路线图 0.92.0 行回填+session-snapshot 刷新+released 验证（含例外标注路径）+零 EVD 迁移写入验证+EXC 周义务首期排程+CR-F1 decision-log 披露；BT-01 首会话抽测发布后承接 |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-28 05:24 | v0.91.0 发布（tag taggerdate 05:24:03 +0800 权威，peel `bd9bfc1`，tag object `0ea429f`） |
| 2026-09-28 05:54 | REL-094 M-8 发布态回填批落库（`4cb3081`——搭窗） |
| 2026-09-28 11:23~22:43 | 六票载荷依次落库（`e65b317`→`a7bcd5f`+`f06a2bf`→`136d65e`→`b6575bd`+`c90768f`→`16a5157`+`484dd77`→`dc45e24` 功能载荷锚） |
| 2026-09-28 23:12 | M-1 版本面（`40eb6f7`；DEC-282 M-0 条件冻结于功能载荷锚后、M-1 前完成——四封口在案） |
| 2026-09-28~29 | M-2 首跑 4 失败面 → DEC-283/284/285 整改链（`12bef7c` 09-29 00:10 + `df26f7e` 00:27）→ M-2R 复测有条件收口（EVD-1235） |
| 2026-09-29 | M-3 双半面（R2 CODE+R3 RELEASE 双 AWN/0——R3 有条件 GO）→ **M-4 本批（四件套）** → M-5~M-8 待办（taggerdate 权威，另记） |

## 门禁摘要（M-2R/M-3 实测已回填；M-5~M-8 数值回填位——发布态重测落字）

| # | 门禁面 | 实测 / 姿态 | 依据 |
|---|---|---|---|
| 1 | check-release 聚合（candidate 态） | **FAILED-7 全貌** = 例外覆盖面×2（archive integrity→EXC-002；governance health 28s→EXC-001）+ 阶段预期态×5（28c×2 会话收工+M-8 自愈；release-docs×3 本 M-4 创建即消）+ advisory 披露缺口×2（CR-F1/F2）（面级 9 面；issue 级 7）；**无未预期阻断项**（M-3 RELEASE 判定）——逐项全貌表 = checklist 核心表 | M-3 RELEASE 重点 5；EVD-1235 |
| 2 | 原生执行门 | verify **exit=0** ✓｜unit tests **exit=0** ✓｜e2e **exit=0** ✓｜loop 门 **PASS**（semantic=PASS·identity=PASS·candidates=**1096**·豁免 **5 条**全披露）✓｜one-dot-zero blockers **PASS**（1.0.0 硬阻塞零新增）✓｜release lineage **candidate 态正确** ✓（tag 后以 released 模式复跑——boundary 注记） | M-3 RELEASE 只读复跑（独立双源，与 EVD-1235 逐项一致） |
| 3 | 注入预算三档 | lightweight **3859** / standard **5337** / strict **5609**（/6000 全 PASS；strict 余量 **9→391 tok**——FEAT-073 兑现） | EVD-1216~1219 |
| 4 | LRC（loop-claims） | verdict **PASS** / findings **0** / exemptions **5/5** 披露（含 B2 新条目五元组逐键吻合；锚-账本-加载器三方一致，digest `d47f5d16` 独立复算在案） | M-3 CODE 重点 3；EVD-1234 |
| 5 | EXC-001 例外治理（机注） | 两层同屏实跑：原始 ERROR 真实字节+exception accepted 同行；时点演进 1,753,848（EVD-1235）→1,755,371→1,755,693B（M-3 双半面，增量=机录行追加可归因）≤ 上限 **2,036,197B**（=基线 1,786,197B@post-dc45e24+250K，不滚动）；expires 2026-10-12 | `.governance/exceptions.json`；M-3 双半面亲跑 |
| 6 | EXC-002 纸质例外 | Check 27 证据面 **178 行**（A=160 已归档任务债/B=4 FEAT-001 双在/C=14 裸 ID；scan-families [0.1.0,0.90.0] 独立复现 178 双重印证）；增长容忍 0；原始 FAIL 保留 | 基线附件 `docs/governance/rel-095-exc002-baseline-178-20260928.md`（222 行，输入锚 `40eb6f7`+sha256 2365c01c）；DEC-285 |
| 7 | archguard 棘轮 | R1~R5/R7 fatal gate 全绿（锚 **26478**——两次 sanctioned regen 26385→26413→26478 分离提交，DEC-260 纪律）；R6 advisory（205 模块 Δ0）；regen deterministic | M-3 CODE 重点 2 |
| 8 | 版本/manifest/投影面 | check-version-consistency PASSED（13 文件+bootstrap markers）；check-manifest-consistency PASS（976 canonical/1128 actual @M-3 CODE 时点）；check-projection-sync/cross-references 及其余静态面全 PASS（check-release 静态席） | M-3 CODE 重点 2；M-3 RELEASE 重点 5 |

## 已知边界（发布态措辞——与 CHANGELOG 0.92.0 段同源，发布时点重测落字）

1. **EXC-001（evidence-log 容量机注例外）**：容量问题**未技术消除**——基线 1,786,197B@post-dc45e24、绝对上限 2,036,197B=基线+250K **不滚动**、expires 2026-10-12（recheck_on 2026-10-05）；两层同屏（原始 ERROR 真实字节+exception accepted）；周义务（冷热/总量/积压指标）首期 M-8 排程。
2. **EXC-002（Check 27 证据面 178 行纸质例外）**：增长容忍 0（清单外新增容忍 0/候选减少须逐项授权/禁净零兑换/输入锚变→重跑复评）；期限 min(0.93 准入评审开始, 2026-10-12 绝对截止)；原始 FAIL 保留；0.93 承接 FEAT-076（五条件+91 物理未归档 ID 回填 C-3）；消息「0 hot completed task(s)」措辞错标=0.93 候选。
3. **advisory 两面**：decision-log 254,420B 超限（CR-F1——M-8 补披露）；archive.py 5508 行越阈 5000（CR-F2——0.93 拆分候选）。
4. **遗留旧行格式面**：EVD-702/1194/1198 三行（**0.91 前既有披露，非本版引入**——本周期 verify_workflow.py 变更面不涉 Check 28 字段校验语义）。
5. **数据面读取契约**：18 EVD 出热后消费者经 `archive/index.md` 读取（bootstrap 协议既有——归档证据=有效证据口径不变）。

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.91.0 四件先例无缺面 | **PASS** | 结构逐节对照 `docs/release/*-0.91.0.md`；rollback 含 EXC 到期处置+回滚三序（RL-F3）；checklist 含 FAILED-7 全貌+M-2 双层报告对照+双例外验收对照；feature-flags 含零新增 flag 声明+B-1~B-7 各含回滚；全表行内零裸管道符（FIX-365 ragged 教训） |
| 回滚区间实测 | **PASS** | `git rev-list --count bd9bfc1..HEAD` = **13**；`git describe` = v0.91.0-13-gdf26f7e 交叉印证；`git cat-file -p v0.91.0` 亲证 object `bd9bfc1`（tag object `0ea429f`，taggerdate 2026-09-28 05:24:03 +0800 权威） |
| 内容事实源引用准确 | **PASS** | 六票 commit/EVD/审查链逐一对照 `git log` 实测 + M-3 双半面报告实读 + CHANGELOG 0.92.0 段实读；DEC-269~285（17/17）与 EVD-1216~1235（20/20）存在性经 M-3 CODE AI 专项核验引用；EXC 数值取自 exceptions.json/基线附件/M-3 亲跑记录 |
| check-manifest-consistency / check-cross-references | **PASS**（docs/release 非 manifest 登记面——0.91.0 四件先例同形态；四件套落盘后实测，记录随 M-4 EVD 承载） | 本票验证记录 |
| 真实 `.governance/` 零写入 | **PASS** | 写入面 = 四件套（REL-095 M-4 files 锁定）；不触治理数据（EXC 条目/例外裁决零触碰）、不改产品代码、不执行 tag/push/transition；EVD 机录由 Coordinator 执行（本票不预留编号——以实际机录为准） |

---
*REL-095 M-4 起草冻结（2026-09-29，Governance Developer Agent）。事实基线：13 提交窗口与 hash/日期取自 `git log`/`git rev-list`/`git describe`/`git cat-file -p v0.91.0` 实测（`bd9bfc1..df26f7e` = 13；v0.91.0 taggerdate 2026-09-28 05:24:03 +0800 = peel `bd9bfc1`）；六票载荷、版本口径、已知边界取自 CHANGELOG 0.92.0 段（M-1 交付准备态——project/CHANGELOG.md canonical）与 DEC-269~285 引用链实读；M-2 整改链与双例外条款取自 EVD-1233/1234/1235、`.governance/exceptions.json`、`docs/governance/rel-095-exc002-baseline-178-20260928.md` 及 M-3 双半面报告（`docs/reviews/review-REL-095-CODE-R0.md` / `review-REL-095-RELEASE-R0.md`）实读；门禁实测数值取自 M-3 双半面亲跑记录（check-release FAILED-7 全貌/原生执行门/LRC/EXC 两层同屏）。未生成事实（发布 tip、tag、M-5~M-8 门禁数值、candidate manifest 提交、发布日期）一律标期义务/回填位，不预填。*
