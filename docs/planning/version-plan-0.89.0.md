# 0.89.0 版本规划（M-0）

> **状态**: **M-0 双 GO**（v1.1，2026-09-25——REVIEW-REL-090-R0〔design〕APPROVED_WITH_NOTES/0 + REVIEW-REL-090-R0-RELEASE〔release〕APPROVED_WITH_NOTES/0；双审 findings 收口落字批已消化：F-1 批次间串行落字/F-2 §5 五项核验回填完成/F-3 §7 引用锚勘正/P2-1 CHANGELOG canonical 继承/F-4 RISK-048 登记；git 入库随 M-0 收口 commit）
> **版本性质**: MINOR（治理精度与健康面收口批；无行为变更激活、无接口删除——§8）
> **范围授权**: DEC-244（用户 2026-09-25 /governance 会话 ask 批准——必选六项 + B-12/B-13 五前置核验（不激活）+ FEAT-045 P-a；**B-12/B-13 激活授权票不捆绑**，行为变更需逐项明示授权）；机录 op-c8517aad1e134c7ab78f1efbdccec8fd
> **先例对齐**: 0.88.0（v2 形态——§3b 发布链映射；M-0~M-8 标准链 DEC-197 语义）；结构节次按 DEC-244 范围面重排
> **版本链**: 0.88.0 已发布（REL-086，2026-09-25；tag v0.88.0 = transition 33d19b0，event integrity sha256:9069916b，ledger 本地+remote 双 PASS）→ 0.89.0 规划（plan-tracker `## 版本规划` 0.89.0 行在案）

## 1. 主题与范围

0.88.0 收口后（发布链 M-0~M-8 全链闭环、工作树干净态），0.89.0 承载**治理精度与健康面收口批**——0.88 深检与 M-5 披露面登记的三类工作：

1. **披露面消解三票**：DEC-241 例外×4（Check 18/18b 分叉——FIX-390 消解）、REL-089 条件③（closure journal 部分兼容——FIX-391 消解）、DEC-242 V3 键控伪像例外×5（Check 30——FIX-392 消解）。
2. **立项深检新票**（2026-09-25 深检实证）：任务状态解析器误判（top pick 误推荐已交付 FEAT-060 + FEAT-061/064/063/385 误 blocked——FIX-393）；13 行终态滞留装饰文本（B~E 批 10 票 + REL-087/088/089——FIX-394）。
3. **能力与健康面**：FEAT-065（EVD-1159 移交提案 P-a——标准链锁腿真释放）；B-12/B-13 五前置核验（只核验不激活——§5）；09-30 风险窗履行（§6）。

**不承载（显式不发布面——Amazon「本次不发布什么」）**：B-12/B-13 激活（授权票独立决策，不捆绑）；God Module 拆分、存储分离其余表、task_status BLOCK 机录化、FEAT-045 P-b、HotFactSource 版本字面量族、GOVERNANCE_SESSION_ID 复核、量测边缘+FIX-380 P2-1（挂起 0.90+——§7）；主文件大拆解（0.88 arch 告诫延续）。

## 2. 载荷票表（DEC-244 六票——零扩缩）

| # | 票 | 优先级 | 内容与验收判据 | 依赖（triage 机录） | 文件面（triage 机录） | 来源锚 |
|---|----|--------|---------------|--------------------|----------------------|--------|
| 1 | FIX-393 | P1 | **任务状态词表收敛**——解析器族识别写入器终态 committed（ops 台账权威状态源）。验收 = task-priority/parse_current_active_tasks/archive 三解析器判据对齐 + 正负测试 + 活体验证零已交付票推荐 | `depends_on=[]` | `task_priority.py`、`verify_workflow.py`、`archive.py` | TRIAGE-FIX-393（机录 2026-09-25）；深检实证 |
| 2 | FIX-394 | P2 | **终态行文本刷新机制**——task-row-update 落状态 token 时刷新状态列进度后缀 + 13 行一次性数据对齐。验收 = 红绿测试 + 一次性对齐凭证（Coordinator 凭证留痕）+ 披露勘正 | `depends_on=[]` | `task_row_update.py`、`closure_chain.py` | TRIAGE-FIX-394（机录 2026-09-25）；深检实证（ops 收据链完整） |
| 3 | FIX-390 | P2 | **Check 18/18b 结构化状态判据**（REL-089 条件②消解票）——检查器改读 basis 列+机器凭证 marker 而非 description 列显示前缀。验收 = 0.88 例外两行（EVD-1140/EVD-1164）红→绿活体 + committed/✅/未知三态回归 + 豁免面差分归因 + 9-cell 列数契约零触碰 | `depends_on=[]` | `verify_workflow.py`、`checks/evidence_domain.py` | TRIAGE-FIX-390（机录 2026-09-25 M-5）；DEC-241；REL-089 报告 |
| 4 | FIX-391 | P2 | **closure journal 版本感知读取器**（REL-089 条件③消解票）——未知事件类型的闭包禁 resume/finalize（机器门禁替代运行手册）；路径 B backport 候选。验收 = 版本感知读取 + 0.87 兼容矩阵收口 + 红绿测试 | `depends_on=[]` | `closure_chain.py` | TRIAGE-FIX-391（机录 2026-09-25 M-5）；REL-089 ③；rollback §8 |
| 5 | FIX-392 | P2 | **Check 30 复合键判据**——review 轮次键控修复（task+chain+round 复合键+链归属字段+V3 判定改链内轮次）。验收 = V3×5 例外消解（全局 R4 伪熔断不再误报）+ 判据回归 | `depends_on=[]` | `verify_workflow.py` | TRIAGE-FIX-392（机录 2026-09-25 M-5）；DEC-242；R3 报告 N1 |
| 6 | FEAT-065 | P2 | **FEAT-045 P-a 落地（DEC-248 验收拆分后范围）**——标准链锁腿 locks-release 真释放升级（替代 TTL 收缩：shrink-locks→release-locks）+ 三处 no locks-release 过时披露勘正；acquire TTL 判定面拆出至 FEAT-066（0.90 池）。验收 = 真释放接线 + task_locks_released 后置条件 gate（任务索引+文件锁归属双面、状态不可读 fail-closed）+ 红绿测试（八项最小集）+ 四红线保持（释放前同文件互斥/只释放本任务锁/释放后不改受锁文件/提交串行隔离）；中断遗留锁仍依赖人工恢复（受控流程）——发布验证分别演示两面 | `depends_on=[FEAT-045]`（0.88 已交付——满足） | `closure_chain.py`、`tests/test_closure_chain.py`（锁面不变——DEC-248①） | TRIAGE-FEAT-065（机录 2026-09-25）；EVD-1159 移交提案 P-a；DEC-248 |

**批次排布建议（依据 triage files/conflicts 机录——同文件面串行）**：

- **批次一（状态面收口）**：FIX-393 → FIX-394（写入器终态判据先收敛，刷新机制后接线）。
- **批次二（披露面消解——检查器族）**：FIX-390 + FIX-392（同文件 `verify_workflow.py`——串行或分腿审查，防判据互踩）。
- **批次三（closure 链健康面）**：FIX-391 → FEAT-065（同文件 `closure_chain.py`——FEAT-065 验收含同文件串行红线；FIX-394 的 closure_chain 腿与本批协调时序）。

**批次间全局串行约束（F-1 收口落字——DESIGN-R0）**：`verify_workflow.py` 共面票实为**三票**（FIX-390 / FIX-392 / FIX-393——FIX-393 files 含 verify_workflow.py，triage conflicts 互列）——批次一的 FIX-393 verify_workflow.py 腿与批次二两票**跨批次同文件串行**（派发锁 + 同文件串行红线既有纪律兜底）；M-1R checklist 须为组合②列补充席（覆盖 393 的 verify_workflow.py 腿）。

六票 triage 依赖面全部 unblocked（FEAT-065 依赖 FEAT-045 已于 0.88 交付）。派发锁由 Coordinator 持有（REL-090 expected-new；本任务不操作锁）。

## 3. 发布链映射

**链型**：M-0 规划双审（Design Reviewer + Release Reviewer）→ M-1 版本 bump → M-1R 四件套 → M-2 门禁实测 → M-3 双半面 → M-4 风险裁决+go → M-5 checklist+manifest → M-6 ledger → M-7 tag+push → M-8 归档收口（DEC-197 标准链语义）。

### 3b. M-0~M-8 全表

| M | 内容 | 出口判据 |
|---|------|---------|
| M-0 | 本文档起草 + 双审（Design Reviewer + Release Reviewer）+ §5 五前置核验回填（F-2 收口落字——回填义务显式绑入 M-0 出口） | 双 GO（APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES）+ §5 五项核验结论回填完成——**已达成 2026-09-25** |
| M-1 | 版本 bump 0.88.0→0.89.0（REL-087 先例形态）：SKILL.md frontmatter 权威锚 + REQUIRED_SNIPPETS 锚 + 投影面再生 + 双根 entry sync + CHANGELOG 0.89.0 段（行为变更节如实写「无激活」——§8；**单 canonical=project/CHANGELOG.md——DEC-242① 0.88 M-3 裁决直接继承，不复刻双位过渡**〔RELEASE-R0 P2-1 收口〕）；bump 票随链启动入账 | check-version-consistency / projection-sync / static-pin / manifest 四项 PASSED |
| M-1R | 四件套（REL-088 先例）：release-plan-0.89.0（六票载荷 + 本表 M 链全表）/ release-checklist-0.89.0（回填位）/ rollback-plan-0.89.0（区间锚定 + B-12/B-13 回退预案引用不触发——§7）/ feature-flags-0.89.0 如适用（B-12 分族姿态全 WARN + B-13 MD_ACTIVE 未激活如实登记） | 四件齐 + cross-refs PASS + 回退显式化 |
| M-2 | §4 门禁全条目 + §9 组合测试集 | 全条目实测留 EVD；组合测试集四项必查 |
| M-3 | 双半面审查：产品代码半面（Code Reviewer 链）+ 发布半面（Release Reviewer 链） | 双半面 GO（终态口径同 0.88：APPROVED / AWN/0） |
| M-4 | 风险裁决 + go：§6 09-30 风险窗履行（RISK-036/039/046 复评 + RISK-047 同窗观察）入账后 go/no-go（DEC-243 先例形态） | 复评机录入 risk-log + go 裁决 DEC 入账 |
| M-5 | checklist 全席回填 + manifest 创建（candidate transition） | candidate commit manifest=`candidate`；TO_BE_DEFINED=0 |
| M-6 | ledger 实测：check-release released 模式 + release-ledger（tag 后 `--remote origin`） | ledger PASS；UNKNOWN/BLOCKED 不得包装为 PASS |
| M-7 | tag v0.89.0 + push（taggerdate 权威——FIX-349 口径；event integrity sha256 双锚） | 本地/remote tag peel 一致 |
| M-8 | 归档收口：`archive.py migrate --auto`（dry-run 先行）+ `check-archive-integrity` PASS + roadmap 0.89.0 行状态回填 + REL-090 任务行终态回填 + Check 28s 复测（§4.5） | 归档完整性 PASS；零待归档滞留 |

**回滚锚定原则**：发布全程 tag + event integrity sha256 双锚（0.87 FIX-349 口径承袭——0.88 §3b）。

## 4. 门禁面（M-2 实测基准）

1. **全量 pytest**：0.88 M-2 基线 4119P/0F（历史首次全绿）——0.89 零回归目标；六票红绿测试落位。「全量只在 M-2」是预算不是变更后免检许可（0.88 §3 口径承袭）；M-3 后修改可执行代码时原 M-2 证据不自动覆盖。
2. **verify 全量 + e2e-check + check-governance --fail-on-issues**：已知披露面基线 = 36 issues（FAIL census：REQ-092×6 + EVD-1146×1 + DEC-241 例外×4 + Check 30 V3×5——DEC-243 实测口径）。FIX-390/392 落地后 census 目标收窄至 REQ-092×6 + EVD-1146×1；REQ-092 外部依赖零豁免红线维持（非本版范围），EVD-1146 superseded 残留维持披露（DEC-227 路线 a）。
3. **LRC 复算**（预算 361,923）：本版 TRIAGE×6 + REL-090 + EVD/REVIEW 机录增量可观——越线按 FIX-369 公式口径重定标（非豁免）。
4. **archguard 棘轮席**：0.88 基线 regen 26193（sanctioned）——M-1R 门禁摘要显式列。
5. **Check 28s 复测**：ERROR 现值 1690.6KB——0.88 窗口行进入归档范围后复测（session-snapshot 下一会话建议③；0.87/0.88 先例同型——下归档周期消解）。
6. **check-release 两态 + release-ledger + release-projection check-only + quality-tools 结构化记录**（ADR-010/stage-release 退出条件承接）：候选态 `--lineage-mode candidate`、tag 后 released 态复跑；quality-tools 未安装记 NOT_RUN 不虚报。
7. **§9 组合测试集为 M-2 必查席**——「禁全量」不得退化为「只测单票」（0.88 §3.2 口径）。

## 5. B-12/B-13 五前置核验清单（只核验不激活——DEC-244）

> 依据 DEC-244：M-0 内含五前置核验（DEC-238④×3 + DEC-239⑦×2），**只核验不激活**；激活授权票独立决策、不捆绑本版。RISK-059（打开，2026-09-25 登记行）承载前置三缺口。

| # | 前置项 | DEC 锚 | 现状与证据锚 | M-0 核验动作 | 核验结论位 |
|---|--------|--------|-------------|-------------|-----------|
| ① | archive.py DEC 归档路由改造方案 | DEC-238④-1 | 已登记未闭环——RISK-059 缺口①；FEAT-061 cutover 授权票验收项①（plan-tracker FEAT-061 行） | 复核 RISK-059 行与验收项登记一致性 | ✅ 一致（2026-09-25 M-0 收口回填）——RISK-059 缺口①（archive DEC 归档路由）↔ FEAT-061 行 cutover 验收项①逐字对应在案 |
| ② | verify_workflow freshness 接线方案 | DEC-238④-2 | 已登记未闭环——RISK-059 缺口②（DEC-238① 注记：JSON 未激活时检查面不可行使必真值假绿）；验收项② | 同上 | ✅ 一致（2026-09-25 M-0 收口回填）——RISK-059 缺口②（freshness 接线）↔ 验收项②对应在案；DEC-238① 假绿注记在案（JSON 未激活时检查面不可行使必真值假绿） |
| ③ | 11 处 DEC-nnn① 勘误行源文件处置 | DEC-238③④-3 | 已登记未闭环——RISK-059 缺口③；验收项③；DEC-194/214 同 ID 勘正行已由 `--accept-duplicate` 支持 | 复核 decision-log 现存勘误行计数（11 处为 2026-09-25 RISK-059 登记时点口径——当前实测行数**待验证**） | ⚠️ 口径漂移实测（2026-09-25 M-0 收口回填）——decision-log.md 当前 `DEC-\d+①` 形态 **3 处出现/2 行**（勘误行本体=DEC-214①〔L156〕一行；DEC-236①〔L181〕系 DEC-239 行内引用非勘误行），与登记口径「11 处」不一致、差异归因待考；迁移阻断判定以 B-13 授权票演练引擎实测为准（fail-closed 报真实阻断数）。核验结果=登记项在案（RISK-059 缺口③维持打开），计数以引擎实测为准 |
| ④ | archguard R1 锚处置（regen 或 shrink） | DEC-239⑦-1 | 0.88 M-2 已执行 regen 26193（sanctioned）——session-snapshot M-2 终态 | 复核 0.89 规划期棘轮基线现状；regen/shrink 续接决策属激活授权票 M-2 前置义务，非本版激活动作 | ✅ 基线在案（2026-09-25 M-0 收口回填）——core/architecture-baseline.json `anchor_loc: 26193` 实读吻合（0.88 M-2 sanctioned regen）；续接决策留激活授权票 M-2 前置 |
| ⑤ | F-5①③ 组合测试（台账损坏×切换窗共存 / 基线更新×投影失败恢复） | DEC-239⑦-2 | 已登记未执行——DEC-239⑦ 原文「归切换授权票」；FEAT-061 cutover 验收项④ | 复核其仍登记于切换授权票验收面 | ✅ 在案（2026-09-25 M-0 收口回填）——FEAT-061 行 cutover 验收项④「F-5①③ 组合测试」+ DEC-239⑦ 原文「归切换授权票」双锚一致 |

**核验结论判据**：五项登记一致性复核完成 + 结论逐项回填本节 = 核验通过。任何一项若发现被绕开执行（如 11 处勘误行被手工提前改动）= 核验失败 → 上报 Coordinator，**不视为可激活**。B-12/B-13 激活条件 = 五前置闭环 + 证明包审查（feat061-rehearsal-result.json 口径）后另行授权（DEC-238④ / RISK-059）。

## 6. 风险窗履行（2026-09-30 窗——M-4 内含）

| 风险 | DEC-243 裁决（2026-09-25，窗内 09-25 履行） | 0.89 窗内履行义务 | 承载/关联 |
|------|---------------------------------------------|-------------------|-----------|
| RISK-036（官方收录/市场采用） | 维持打开——0.88 窗口无新交付；关闭标准（marketplace readiness/E2E 矩阵/官方提交包）未满足 | 09-30 前复评：0.89 载荷无外部收录面（如实记录）→ 维持打开 + 复评入账 | M-4（或窗内先行） |
| RISK-039（架构腐化看护） | 维持打开（正向注记：4119P/0F + archguard regen + 拆分候选入池） | 09-30 前复评：God Module 拆分经 DEC-244 挂起 0.90+（候选仍在池、交付后置）——复评如实双面记录 | M-4（或窗内先行） |
| RISK-046（派发锁/triage files 漂移） | 维持打开（实质接近关闭——FEAT-013 根因修复 + F-2 竞态独立验证 + acquire 锁腿候选入 0.89） | 09-30 前复评：确认候选池承载 = FEAT-065 已立票入 0.89 载荷（DEC-244）→ 维持观察至 0.89 落地关闭 | FEAT-065 + M-4 |
| RISK-047（force 覆盖语义） | 维持观察（本窗口 review-record 无 force 参数实证——R3 N1 键控挡行即活体注记） | 同窗观察：CLI --force 旗标候选未入 0.89 载荷（未排期）——复评维持观察 | M-4 |
| RISK-048（DEC-243⑤ 同窗裁决对象） | 维持观察（DEC-243⑤——0.88 M-4 五风险裁决之一，与 036/039/046/047 同窗） | 同窗观察登记（DESIGN-R0 F-4 收口——防与 triage/热表口径歧义；内容详见 risk-log 行） | M-4（或窗内先行） |
| RISK-050（dsh 上游内部面耦合） | 打开（窗外——截止 2026-10-31） | 不属 09-30 窗；本表仅登记在案 | — |
| RISK-059（B-13 前置三缺口） | 打开（2026-09-25 登记） | §5 五前置核验对象——激活授权票前置，非 09-30 窗义务 | §5 |

**时序纪律**：窗内履行不迟于 2026-09-30。若 0.89 M-4 晚于 09-30，复评裁决须窗内独立先行入账（risk-log 机录），M-4 消费其结论——0.88 规划 F-13 口径（Check 8 自 10-01 转 FAIL 的门禁联动；现值待 M-1R 核对——**待验证**）。

## 7. 回退与挂起项

**回退面**：

- 本版无行为变更激活（§8）→ 无数据级回退触发面。发布级回退 = 标准链口径（tag + event integrity sha256 双锚；ledger candidate/released 语义，ADR-010）。
- B-12 回退预案（族级 flag 回 WARN 经 break-glass 通道）与 B-13 反向转换方案已作为 0.88 rollback-plan 显式交付件（REL-088 F-11——`docs/release/rollback-plan-0.88.0.md` **§7 专节（B-12/B-13 回退预案）+ §8 部署 tag vs revert 重建区分节**双锚〔DESIGN-R0 F-3 勘正〕）——0.89 不触发；激活授权票决策时按该预案 + RISK-059 前置执行。

**挂起 0.90+（DEC-244 挂起清单）**：God Module 拆分 / 存储分离其余表 / task_status BLOCK 机录化 / FEAT-045 P-b / HotFactSource 版本字面量族 / GOVERNANCE_SESSION_ID 复核 / 量测边缘 + FIX-380 P2-1（双源互检）。

**独立授权票（不捆绑、不排期）**：B-12 翻转授权票 / B-13 切换授权票——五前置闭环 + 证明包审查后另行决策（DEC-244）。

**候选未排期（如实登记）**：review-record CLI --force 旗标（RISK-047 / DEC-243④ 候选——未入 0.89 载荷亦未入挂起清单）。

## 8. 行为变更面（= 无激活）

- **B-12**（write-guard 分族 BLOCK）：机制 0.88 已交付（FEAT-064）——出厂全 WARN；0.89 **无 `--activate-block` 执行**。
- **B-13**（decision-log JSON 权威化）：协议层 0.88 已交付（FEAT-061）——权威标记缺省 MD_ACTIVE epoch0；0.89 **无真实切换**。
- **CHANGELOG 0.89.0 行为变更节如实写「无激活」**（M-1 落字依据——本节为规划口径）。
- 载荷六票均属内部工具面修正（解析判据收敛 / 终态文本刷新 / journal 读取门禁 / 锁腿释放语义 / 检查器判据），无接口删除、无用户可见 breaking；B-x 新登记预期 = 无——M-1/M-3 按实际 diff 复核，若出现实质行为面（如 FIX-394 状态列文本格式变化被判定为可见面）如实入账并知会双审。
- 六票 triage files 面均不含 SKILL.md/commands 投影面；投影面再生随 M-1 常规执行。

## 9. 组合测试集（M-0 预指定——M-2 必查席）

> 依据 0.88 §3.2 先例：跨票边界 M-0 预指定组合测试集。本版四项组合全部锚定 triage files/conflicts 机录事实（同文件面 = 交互面）。

| # | 组合 | 文件交集 | 判据 |
|---|------|---------|------|
| ① | **状态面闭环一致性**（FIX-393 × FIX-394） | 终态行「写入→读取」链（task_row_update 写 / parse_current_active_tasks·task_priority 读） | 同一终态行三面一致：解析器归类为已交付 / 优先分析不推荐 / 状态列无滞留装饰文本；正负测试共享 fixture |
| ② | **检查器判据双票互不回归**（FIX-390 × FIX-392，同文件 `verify_workflow.py`） | `verify_workflow.py` | 两票落地后 36-issue census 中 DEC-241 例外×4 与 V3×5 同窗转绿；9-cell 列数契约零触碰（FIX-390 验收项）；历史真实 NC 熔断不误放行（FIX-392 链内轮次判定） |
| ③ | **closure 链三票串行面**（FIX-391 × FEAT-065 × FIX-394 closure 腿，同文件 `closure_chain.py`） | `closure_chain.py` | 版本感知门禁开启后标准链锁腿真释放路径 resume/finalize 不被误拒（正例）；伪造 tombstone / 未知事件仍拒（负例）；同文件串行红线保持（FEAT-065 验收项） |
| ④ | **archive 判据 × 归档完整性**（FIX-393 archive 腿 × 0.88 FIX-384 index-rebuild 既有路径） | `archive.py` | 判据对齐后归档迁移不误收/不漏收 committed 行；`check-archive-integrity` PASS + `migrate --auto --dry-run` 对 0.88 窗口行的归档判定与 FIX-393 判据一致（Check 28s 复测联动——§4.5） |

**验证方式**：①~④ 于 M-2 以 pytest 指定组合套件 + 活体命令实测留 EVD；组合清单随 M-1R 四件套转入 release-checklist 重点席。

**收口注记（DESIGN-R0 F-5/F-6）**：批次一中间态（FIX-393 落地 / FIX-394 未落地）活体验证于 M-2 **独立留 EVD**——防「终态组合绿」掩盖中间态判据断裂；M-3 审查须抽查 FIX-390/392 红侧 fixture 为非预录形态。
