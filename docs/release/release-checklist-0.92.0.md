# Release Checklist — 0.92.0

- **版本**: 0.92.0 · **日期**: 2026-09-29 · **状态**: **候选链 M-4 进行中（未发布——tag 未打）**（M-0~M-3 完成；本票=M-4① 四件套；⑤~⑩ 待办回填位）
- **主题**: 预算优化、验证稳定性与证据分层结构性解锁（Injection Budget Relief, Verification Stability & Evidence-Layer Structural Unlock）——六票载荷 FEAT-073/FIX-400/FIX-401/FEAT-074/FEAT-075/FIX-402 / DEC-269~285 / EVD-1216~1235
- **版本定义**: DEC-282(7) 版本口径「strict 注入预算优化、发布与运行时验证稳定性修复，证据分层结构性解锁与本轮明确遗留项收尾」+ no-overclaim 附加句「结构性解锁已完成；容量问题未技术消除。本轮不执行 EVD 物理迁移，按限期例外控制，后续迁移以读取契约闭合为前提。」（精确措辞：**178 行历史证据面未迁移由 EXC-002 治理**；18 行有界迁移属 DEC-284 补完成授权）；**无破坏性变更、无机制激活**（RB-2/B-12/B-13 出厂姿态不变）。

## 发布范围（冻结清单——DEC-282）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-073 | strict 注入预算 persona 单源化+薄指针压缩——strict 余量 **9→391 tok**；三档实测 lightweight **3859**/standard **5337**/strict **5609**（/6000 全 PASS）；strict 档会话更轻 |
| 载荷 | FIX-400 | release-gate 墙钟预算 **180→2333s** 再校准（=ceil(1554.78×1.5)——DEC-262 先例同式）+regen 分离提交 26385→26413；门禁信号恢复可信 |
| 载荷 | FIX-401 | loop_runtime 计时断言**墙钟→process_time** 去环境化——并行负载假红消除；RISK-048 收窄（预算 27.0→27.8） |
| 载荷 | FEAT-074 | 证据行**五态实体感知分类替代单桶**（28s 结构性解锁——DEC-278 单元一）；输入锚 `b6575bd` 设计准入盘点文档（申报面内） |
| 载荷 | FEAT-075 | 四族只读 dry-run **scan-families**（EVD 477/REVIEW 640/RECO 159/TRIAGE 199——五态子分解）+发布聚合层**例外标注机制 exception_registry**（annotation-only；dry-run 零写入代码级强制）；regen 分离提交 26413→26478 |
| 载荷 | FIX-402 | **160 唯一 ID 八类台账**+C-2 写回 11 处（确定性数据校正——**功能载荷锚** `dc45e24`） |
| 版本面 | REL-095 M-1 | 权威源 bump+六锚+release-projection 单次写入 17 面（幂等复跑 written=0）+双根 entry sync+CHANGELOG 准备态 |
| 整改面 | REL-095 M-2/M-2R | DEC-283 受控回退 6 归期行+DEC-284 有界迁移（2 任务+18 EVD）+DEC-285 EXC-002 纸质例外+B2 精确豁免（`df26f7e`）——**有条件收口**（EVD-1235） |

无破坏性变更（M-3 CODE 聚合终审：窗口 diff 51 文件 +5333/−216（六票+发布链对账区间 e65b317^..df26f7e，搭窗 4cb3081 除外；全窗 bd9bfc1..df26f7e=56 文件 +5523/−239） 全部归因六票申报面或发布链提交——无未申报夹带、共享文件跨票零接口冲突）；无机制激活。

## M-链完成态勾选（M-0~M-4——锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 条件冻结 | ✅ 完成 | DEC-282（2026-09-28）：功能载荷锚 `dc45e24`+四封口（①例外登记+有效/失效路径验证 ②C-1 边界〔M-8 显式跳过 EVD 物理迁移+11 行留热+0.93 五条件〕③C-3 91 ID 转 0.93 ④完成声明）+版本口径(7) |
| 载荷六票 | ✅ 完成 | FEAT-073 `e65b317`（EVD-1216~1219；R0/R1 双 AWN/0）→FIX-400 `a7bcd5f`+`f06a2bf`（EVD-1220~1222；R0 AWN/0）→FIX-401 `136d65e`（EVD-1223~1224；R0 AWN/0）→FEAT-074 `b6575bd`+`c90768f`（EVD-1225~1226；R0 NC→R1 AWN/0）→FEAT-075 `16a5157`+`484dd77`（EVD-1227~1228；R0 NC→R1 AWN/0）→FIX-402 `dc45e24`（EVD-1229；R0/R1 NC→R2 AWN/0）——M-3 CODE 对账无夹带 |
| M-1 版本 bump | ✅ 完成 | `40eb6f7` · EVD-1230/1231/1232 · REVIEW-REL-095-M1-R0 AWN/0 P3×1——17 投影面单次收敛+幂等复跑 written=0+双根 entry sync+CHANGELOG 准备态 |
| M-2 整改链 | ✅ 有条件收口 | 首跑 4 失败面→DEC-283（受控回退 6 归期行+B2 一次性授权）→DEC-284（有界迁移 2 任务+18 EVD——EVD-1233 验收 5/6：18/18 精确／守恒 2921+522／幂等 0/0）→DEC-285（EXC-002 纸质例外——基线附件 178 行）→B2 `df26f7e`（EVD-1234 六项验收 6/6；REVIEW-REL-095-B2-R1 AWN/0）→M-2R 复测@`df26f7e` 有条件收口（EVD-1235——原文「有条件收口/例外接受（非原生全绿）」） |
| M-3 双半面审查 | ✅ 完成（双 AWN/0） | **R2 CODE**（盘上 `docs/reviews/review-REL-095-CODE-R0.md`——unresolved_blockers=0，P2×2 advisory〔CR-F1/F2〕+P3×5）+ **R3 RELEASE**（盘上 `docs/reviews/review-REL-095-RELEASE-R0.md`——unresolved_blockers=0 **有条件 GO**，P2×1〔RL-F1〕+P3×3，放行条件①~⑩产出）；机录轮位 round 2/3 |
| M-4 修复窗 | 🔄 本票执行 | ①四件套=本票（放行条件①/RL-F3）②FAILED-7 全貌口径=本表核心表承载（放行条件②/RL-F2）③风险窗引用（release-plan §风险窗引用——036/039/044/047 留痕+048 收窄+050/059 维持）④双报告机录（放行条件④——Coordinator 面）；EVD 编号以实际机录为准 |

## check-release 终态核心表（FAILED-7 全貌——M-3 RELEASE 只读复跑 @`df26f7e`）

| # | 失败面 | 终态与归因（实测） | 承接 |
|---|---|---|---|
| ① | archive integrity（Check 27） | FAIL——消息「0 hot completed task(s)」=**措辞错标 0.93 池**（驱动面=**证据面 178 行**；任务面 would=0 已闭合）；原始 FAIL 保留 | **EXC-002 纸质例外承接**（期限 min(0.93 准入, 2026-10-12)） |
| ② | governance health（exit=1，38 issues） | **28s** evidence-log 超阈=**EXC-001 机注在屏**（两层同屏——原始 ERROR 真实字节+exception accepted）＋遗留旧行格式面 **EVD-702/1194/1198**（**0.91 前既有披露，非本版引入**——本周期 verify_workflow.py 变更面不涉 Check 28 字段校验语义）＋decision-log **254,420B** 超限 **advisory**（CR-F1）＋archive.py **5508 行**越阈 5000 **advisory**（CR-F2）＋28c×2/packet 占位（CR-F3/F4 阶段预期） | 28s=EXC-001（expires 2026-10-12）；CR-F1→M-8 补披露；CR-F2→0.93 拆分候选 |
| ③④ | hot fact source ×2 | session-snapshot 缺 latest published release 0.91.0 行；plan-tracker 缺 0.92.0 roadmap 行（=28c 两子面 mid-chain 形态——RL-F4/CR-F3） | 阶段预期态——会话收工快照刷新+M-8 路线图回填自愈 |
| ⑤⑥⑦ | release docs ×3 | release-checklist/feature-flags/rollback-plan 0.92.0 三件 missing | 阶段预期态——**本 M-4 四件套创建即消**（RL-F3；本表所在文件即其一） |
| — | **原生执行门（全绿）** | verify **exit=0** ✓｜unit tests **exit=0** ✓｜e2e **exit=0** ✓｜loop PASS（semantic=PASS·identity=PASS·**candidates=1096**·豁免 **5 条**全披露）✓｜one-dot-zero blockers **PASS** ✓｜lineage **candidate 态正确** ✓ | 与 EVD-1235 逐项一致（M-3 独立双源） |
| — | 静态/门禁面（全 PASS） | version consistency／release fact source／runtime readiness／first session／governance pack／agent adapters×6／projection sync／cross references／release lineage（candidate）／gate sequence／one-dot-zero blockers／changelog／governance exceptions（EXC-001 effective）／loop fuse／dsh upgrade regression | RISK-036 复评所引 official faces 全 PASS 亲证维持 |

**判定**：7 issues 全数归属三类——例外覆盖面（①=EXC-002、②的 28s=EXC-001——两层报告与实跑**一致**）／阶段预期态（③④收口期、⑤⑥⑦ M-4）／advisory 披露缺口（②的 CR-F1/F2）——**无未预期阻断项**（M-3 RELEASE 原文判定）。

## M-2 有条件收口双层报告对照（EVD-1235 声明 vs M-3 实跑——RL-F3 要求承载）

| 面 | EVD-1235（M-2R 机录） | M-3 实跑复核 | 一致性 |
|---|---|---|---|
| archive-integrity | FAIL=证据面 178 行（任务面 would=0 已闭合；EXC-002 纸质承接） | 同形态 FAIL 在屏；scan-families [0.1.0,0.90.0] 独立复现 **178** | 一致 ✓ |
| governance health 28s | EXC-001 机注在屏 | 两层同屏同形态（时点字节 1,753,848→1,755,371→1,755,693B，增量=机录行追加可归因，非漂移） | 一致 ✓ |
| 原生执行门 | verify+unit+loop+e2e 原生 PASS | 逐项独立复跑同值 | 一致 ✓（双源） |
| 未枚举面 | —（hot fact source×2/release-docs×3 未列=RL-F2） | 实跑在屏=阶段预期态 | **本表补承载 FAILED-7 全貌口径（RL-F2 消解）** |
| 收口口径 | 「有条件收口/例外接受（非原生全绿）」原文 | 如实登记不篡改机器输出 | DEC-285(4) 验收口径 ✓ |

## 双例外治理对照（例外验收对照——M-3 RELEASE 重点 2 全要素亲证）

| 要素 | EXC-001（机注例外） | EXC-002（纸质例外） |
|---|---|---|
| 形态 | `.governance/exceptions.json` 登记+发布聚合层机注（FEAT-075 registry 面承载） | DEC-285+基线附件+M-2 双层报告（Check 27 走独立通路无例外机制接线——机注不可达注记 L222） |
| 作用域 | check_id `governance_data_size`／artifact `.governance/evidence-log.md` | Check 27 证据面 **178 行**（A=160 已归档任务债／B=4 FEAT-001 双在／C=14 裸 ID） |
| 基线/上限 | 基线 **1,786,197B** @post-dc45e24；绝对上限 **2,036,197B**=基线+250K **不滚动** | 基线附件 222 行（输入锚 `40eb6f7`+sha256 2365c01c）；**增长容忍 0**（清单外新增容忍 0／候选减少须逐项授权／禁净零兑换／输入锚变→重跑复评） |
| 期限 | expires **2026-10-12**（批准日+14 自然日；recheck_on 2026-10-05） | **min(0.93 准入评审开始, 2026-10-12 绝对截止)**——明文不延长 EXC-001 的 10-12 到期 |
| Owner | Coordinator | 四角色实名（债务 Coordinator／验证 独立复核人／发布批准 DEC-274 预授权链／FEAT-076 兼容证明） |
| ref | DEC-282（M-0 冻结批准）+DEC-278（先例） | DEC-285 |
| 呈现 | **两层同屏**（原始 ERROR 真实字节+exception accepted） | **原始 FAIL 保留** |
| 0.93 承接 | 0.93 准入前失效/撤销+禁继承 | FEAT-076（五条件+91 物理未归档 ID 回填 C-3） |
| 两面关系 | **互不覆盖**（作用域／期限／owner 三维亲证——M-3 RELEASE 重点 2） | |

## M-5~M-8 待办（M-3 RELEASE 放行条件⑤~⑩逐项——有条件 GO 的条件本体）

| 条件 | M | 发布态义务 |
|---|---|---|
| ⑤ | M-5 | 创建 `skills/software-project-governance/core/releases/0.92.0.json`（NFC/sorted/compact；lifecycle candidate→transition；tip 以 M-5 现场 `git rev-parse HEAD` 为准）+check-release candidate 态执行（DEC-282「不提前伪造完成态」至此解除——M-3 亲证 json 缺席=义务未提前 ✓） |
| ⑥ | M-5 | **CHANGELOG 发布态改写（RL-F1 全项）**：发布日期=FIX-349 taggerdate 权威（M-7 后回填）+**EXC-002 条款摘要与 EXC-001 并列**（覆盖面/增长容忍 0/期限/关闭条件/机注不可达注记）+B2 豁免（loop-claims 第 5 条+受控解冻语义）+有界迁移终账+决策链补全 **269~285**（含 273/277 缺项与新增 283~285）+EVD 范围含发布链证据 **1230~1235**+行为变更段（B-1~B-7——无 breaking+回滚三序说明）+已知限制发布时点重测（28s 现值／decision-log 254,420B 披露 CR-F1／archive.py 5508 披露 CR-F2）+终账/Commit 区间补记 |
| ⑦ | M-6 | release-ledger 本地+**remote** 双 PASS（NATIVE_RELEASED；tag_facts 双端核对；UNKNOWN/BLOCKED 不得包装 PASS——0.90/0.91 条件同型） |
| ⑧ | M-7 | annotated tag `v0.92.0`+push（peel 机制+taggerdate 权威回填 CHANGELOG 与路线图）+master push |
| ⑨ | M-8 | plan-tracker 工作流版本 0.92.0 收口+**路线图 0.92.0 行回填**（28c 面——released 验证 fact-source PASS 硬前置）+session-snapshot 刷新（含 latest published release 0.92.0 三要素投影行——RL-F4 自愈闭合）+released 验证（lineage/changelog/archive/docs/fact-source 全 PASS——**含例外标注路径**：EXC-001 机注在屏+EXC-002 纸质双层报告归档）+decision-log 越阈披露（CR-F1——254,420B 面发布时点重测落字） |
| ⑩ | M-8 | 零 EVD 迁移写入验证（DEC-282 C-1(b)：三族守卫有效+11 行留热口径=已复验未物理迁移）+**EXC 周义务首期履行排程**（EXC-001 recheck 2026-10-05 冷热/总量/积压指标；EXC-002 周报——增长容忍 0 监控）；census/身份集维持至 tag（零新增未授权阻断项红线） |

## 已知问题与边界

1. **EXC-001**（evidence-log 容量机注例外）——容量问题**未技术消除**；上限 2,036,197B 不滚动；expires 2026-10-12；周义务首期 M-8 排程。
2. **EXC-002**（Check 27 证据面 178 行纸质例外）——增长容忍 0；期限 min(0.93 准入, 2026-10-12)；0.93 承接 FEAT-076（五条件+91 ID 回填 C-3）；「0 hot completed task(s)」措辞错标=0.93 候选。
3. decision-log **254,420B** 超限（CR-F1 advisory——M-8 补披露）。
4. archive.py **5508 行**越阈 5000（CR-F2 advisory——0.93 拆分候选）。
5. 遗留旧行格式面 EVD-702/1194/1198（0.91 前既有披露——非本版引入）。
6. 18 EVD 出热后消费者读取契约=`archive/index.md`（bootstrap 协议既有——不变）。

## 发布后验证计划

- check-release `--lineage-mode released --release-commit <sha>` PASS（tag peel 本地=remote+ledger 单父 transition+非 UNKNOWN/BLOCKED）。
- **BT-01：0.92 安装后首会话抽测**（M-0 绑定——三面绑定 plan-tracker REL-095 行／execution-packets goal 段／session-snapshot carry-over；授权链 DEC-272 承诺/DEC-274 兑现条款——发布后承接）。
- 核心功能冒烟：`/governance` bootstrap（0.92.0）+ governance-bootstrap 热数据面正常 + strict 档注入预算余量 ≥391 tok 呈现（FEAT-073 行为面）。
- **EXC 周义务启动**：EXC-001 冷热/总量/积压指标（recheck 2026-10-05）+EXC-002 周报；到期处置预案=rollback-plan-0.92.0 §EXC 到期处置。
- 观察期：发布后 48h 无新增 P0/P1 报告（内部工具替代标准）。
- **回滚触发绑定**：观察期内出现任一情形 → 立即进入 hotfix 0.92.1 或回滚决策（按 rollback-plan-0.92.0；历史 tag 变更须独立 DEC）：①新增 P0/P1 缺陷报告 ②`/governance` bootstrap 或 governance-bootstrap 冒烟失败 ③check-release released 复跑 FAIL ④EXC 增长控制击穿（evidence-log >2,036,197B 或 Check 27 清单外新增——例外失效面恢复硬阻断）。

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
