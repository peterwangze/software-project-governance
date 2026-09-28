# REVIEW-REL-095-RELEASE-R0 — 0.92.0 发布链 M-3 RELEASE 半面审查报告

- **Round**: R0（RELEASE 半面首审；机录轮位 round=3——round 0/1/2 已被 M1-R0/B2-R1/M3-CODE-R0 占用）
- **Reviewer**: Release Reviewer（agents/code-reviewer.md + skills/release-review/SKILL.md 已加载；P0~P3 分级；APPROVED/APPROVED_WITH_NOTES〔附 unresolved_blockers〕/NEEDS_CHANGE/BLOCKED）
- **审查对象**: 0.92.0 发布就绪 @HEAD=`df26f7e`（工作树干净亲证——`git status --porcelain` 除并行产出的本审姊妹报告外零修改；tag v0.92.0 未打=M-3 前置正确）
- **先例参照**: review-REL-094-M3-RELEASE-R0（0.91 同席）；姊妹半面 review-REL-095-CODE-R0（round 2，AWN/0，2026-09-29 机录 REVIEW-REL-095-R2）
- **审查日期**: 2026-09-29 ｜ **任务**: REL-095（M-3 RELEASE 半面）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）** — P0=0 / P1=0 / **P2×1** / P3×3

---

## 一、审查重点逐项结论

### 重点 1：发布链合规（M-0→M-1→M-2→M-3 链完整性与文档可追溯）— PASS

| 链节 | 事实核验 | 可追溯性 |
|---|---|---|
| M-0（DEC-282 四封口） | DEC-282 全文在 decision-log L224：①例外登记+有效/失效路径验证 ②C-1 边界（M-8 显式跳过 EVD 物理迁移+11 行留热口径+0.93 五条件）③C-3 91 ID 转 0.93 ④四封口动作完成声明——四要素逐条在文 | EVD/plan-tracker REL-095 行（L87）引用链闭合 |
| M-1（40eb6f7） | REVIEW-REL-095-M1-R0 AWN/0（机录 round 0）——23 文件版本面+CHANGELOG 准备态；EVD-1230/1231/1232 承载 | git log 亲证 `40eb6f7` subject 逐字对应 |
| M-2 整改（12bef7c+df26f7e） | 12bef7c=+2 治理文档（EXC-002 基线附件 222 行新建+FIX-402 台账后记 +2）；df26f7e=B2 豁免（账本+11/锚 re-pin/定向测试+96/审查报告+77）——**两提交零产品运行逻辑夹带**（B2 的 loop_runtime_claims.py 改动=锚常量 re-pin，DEC-283 题 2 受控解冻授权在案） | EVD-1233（有界迁移 5/6+EXC-002 承接）/EVD-1234（B2 六项验收 6/6）/EVD-1235（双源复测有条件收口）三行机载；DEC-283/284/285 三裁决实锚 L225~227 |
| M-3 | CODE 半面 R2 AWN/0（review-REL-095-CODE-R0，机录 REVIEW-REL-095-R2）+本审 RELEASE 半面——双半面同席齐备 | 本报告即产物 |

**链完整性判定**：四链节文档/证据/commit 三方互恰，无断链、无越权跳步。M-2 收口口径=「有条件收口/例外接受（非原生全绿）」（EVD-1235 原文）——如实登记不篡改机器输出，符合 DEC-285(4) 验收口径。

### 重点 2：例外治理验收（本版核心）— PASS（两面例外全要素成立）

**EXC-001（机注例外）——五要素逐一实测**：

| 要素 | 条款（exceptions.json） | 实跑核验 |
|---|---|---|
| 两层同屏 | 原始 ERROR+真实字节保留+exception accepted 标注 | `check-governance-data-size` 亲跑：`[ERROR] governance_data_size: .governance/evidence-log.md 1755371 bytes … — exception accepted (EXC-001, ref=DEC-282…, expires=2026-10-12)` 同行同屏 ✓；check-governance 28s 面同形态（1,755,693B 时点）✓；check-release「governance exceptions」面 PASS 且披露 `artifact now 1,755,371 B / growth control 2,036,197 B` ✓ |
| 上限 vs 现值 | growth_control=2,036,197B（=基线 1,786,197+250,000，算术亲证） | 现值复测 1,755,371→1,755,693B（+322B=姊妹半面 REVIEW-REL-095-R2 机录行追加，测量时序差非漂移——CR-F7 同口径）≤ 上限，余量 ~280KB ✓ |
| 期限 | expires 2026-10-12=批准日 2026-09-28+14 自然日（亲算）不自动续期；recheck_on 2026-10-05 | 两个命令面披露一致 ✓；0.93 准入前失效/撤销+禁继承条款在 json note+DEC-282(4)+CHANGELOG L23 三方一致 ✓ |
| 义务 | 每周冷热/总量/积压指标 | 条款在案；首期履行属发布后承接（见重点 6） |
| 摘要一致 | CHANGELOG L20~26 条款摘要 | 基线/上限算术/期限/义务/五条件/11 行留热口径/再生纪律——逐字咬合 exceptions.json+DEC-282(4) ✓ |

**EXC-002（纸质例外）——四要素逐一核验**（docs/governance/rel-095-exc002-baseline-178-20260928.md，12bef7c 入库）：

- **178 行身份级清单** ✓：类 A 160+类 B 4+类 C 14=178（算术亲证；逐 ID 表含行号/字节/引用任务三列，输入锚 commit=40eb6f7+sha256=2365c01c+分析器版本/窗口全载——非数字绑定，换血越界条款在案）；姊妹半面 scan-families [0.1.0,0.90.0] 独立复现 178（CR 重点 1 链 5）双重印证。
- **增长容忍 0** ✓：附件 L217「清单外新增容忍 0；候选减少须逐项授权记录；禁净零兑换；输入锚变→重跑复评」——与 DEC-285(2) 逐字一致。
- **机注不可达注记** ✓：附件 L222 实测注记——Check 27 在 check-release 走独立通路无例外机制接线（FEAT-075 接线面=Check 28s+ArchGuard 共享渲染器），纸质承载体=DEC-285+附件+M-2 双层报告；不改产品（治理封口）；机接线化=0.93 池候选。
- **原始 FAIL 保留** ✓：本审 check-release 实跑 archive-integrity FAIL 在屏（消息面「0 hot completed task(s)」=已知措辞错标 0.93 池，驱动面=证据面 178 行——与 EVD-1235 声明逐字吻合，姊妹半面重点 5 同判）。

**两面例外关系判定**：作用域互不覆盖 ✓（EXC-001=check_id governance_data_size/artifact evidence-log.md；EXC-002=Check 27 should_archive 178 行接受面且明文「不覆盖…EXC-001 与 B2 条件」）；期限一致 ✓（EXC-001 expires 2026-10-12；EXC-002=min(0.93 准入评审开始, 2026-10-12 绝对截止)——绝对截止同日且明文「不延长 EXC-001 的 10-12 到期」，附件 L219）；owner 实名 ✓（EXC-001 owner=Coordinator；EXC-002 四角色实名=债务 Coordinator/验证 独立复核人/发布批准 DEC-274 预授权链/FEAT-076 兼容证明——DEC-285「实名 Owner」条款原样落附件 L218）；0.93 承接义务绑定 ✓（plan-tracker L86 FEAT-076 行含 C-3 交接 91 物理未归档 ID 回填+0.92 例外条款有效期绑定+EXC-001 准入前失效义务+0.93 首轮分诊强制接受/拆票/说明延期）。

### 重点 3：CHANGELOG 准备态 — PASS（骨架成立；M-2 整改叙事缺位列 P2-1 为 M-5/M-8 必补项）

- **版本口径 vs DEC-282(7) no-overclaim 附加句** ✓：L9 原文在（「结构性解锁已完成；容量问题未技术消除。本轮不执行 EVD 物理迁移，按限期例外控制…」）——与 EXC-001 条款/DEC-282(7) 一致，无越权声明。
- **六票 hash** ✓：L13~18 八 hash（e65b317/a7bcd5f+f06a2bf/136d65e/c90768f/16a5157+484dd77/dc45e24）逐一 git log 亲证存在且 subject 对应；载荷锚 dc45e24=窗口内（b6575bd 输入锚申报面注记见 CR-F6）。
- **EXC-001 摘要与 exceptions.json 一致** ✓（重点 2 已证）。
- **发布日期不预填** ✓：L5「未发布（准备态）」+L47 准备态注记（FIX-349 taggerdate 权威口径声明）。
- **M-2 整改叙事充分性评估 → 不足，列 M-8 补记项（P2-1）**：准备态注记「终账随 M-2+ 补记」对**终账**（日期/Commit 区间/验证结论）是设计内正确姿态；但 grep 亲证现稿全段**零提及** DEC-283/284/285、EXC-002、有界迁移（2 任务+18 EVD）、B2 豁免——「已知边界披露」段仅含 EXC-001 单例外，与实际发布准入=**双例外+B2 豁免**的版图结构性不符；决策链行（L7/L28）仍为「269~272/278~282」缺 273/277（M-1 F-1 遗留）且新增缺 283~285；EVD 范围 1216~1229 不含发布链证据 1230~1235；无行为变更段（0.90/0.91 先例形态：无 breaking 声明+回滚说明）。若 M-5 仅按现稿骨架补日期终账，发布版 CHANGELOG 将系统性漏披露 Check 27 例外与 loop 豁免——**M-5 发布态改写 MUST 将 EXC-002 摘要与 EXC-001 并列 + B2 豁免 + 有界迁移叙事 + 决策链/EVD 补全 + 行为变更段纳入改写范围**（放行条件，见项五）。

### 重点 4：风险与回滚 — PASS（引用面齐备；回滚链完整可执行）

**风险窗引用（M-4 前置核对，risk-log 现状亲读）**：

| 风险 | 状态 | 2026-09-28 复评留痕（亲证） |
|---|---|---|
| RISK-036 | 打开 | ✓「0.92.0 M-0 前窗复评（DEC-274/278 授权链）：维持打开——0.92.0 为治理内收尾版…check-release official faces（one-dot-zero blockers/adapters/projection/E2E matrix）全 PASS 维持；no-overclaim 边界维持」 |
| RISK-039 | 打开（收窄维持） | ✓「0.92.0 M-0 前窗复评：维持收窄——ArchGuard R1-R7 fatal gate 全绿 @c90768f…外部宿主验证关闭条件未满足」 |
| RISK-044 | 缓解中 | ✓「0.92.0 M-0 前窗复评：维持缓解中（劣化趋势持续但根因侧处置在途）——evidence-log 1.78MB…」 |
| RISK-047 | 打开（登记观察） | ✓「0.92.0 M-0 前窗复评：维持观察——0.92 会话至本时点 review-record 机录 6 次全部零 force」 |
| （关联）RISK-048 | 打开 | ✓ 2026-09-28 FIX-401 收窄兑现注记（墙钟→进程 CPU，预算 27.0→27.8）——M-4 同窗引用 |

**回滚路径（版本面+豁免+迁移三序）**：

1. **迁移面**（.governance 数据）：有界迁移回滚**已实弹演练**（EVD-1233：隔离副本真迁移→verify→rollback→基线比对——evidence 行级复原+任务行尾置与头块残留 runbook 清理可达基线）；journal 逐 ID 可追溯（DEC-284 验收第 4 项，区分 4 随行 vs 14 补完成）——机制级回滚能力在案 ✓。
2. **豁免面**：df26f7e 单提交自洽（账本第 5 条+双锚 re-pin+定向测试同 commit）——`git revert df26f7e` 整体回退无悬挂 ✓。
3. **版本面**：`git revert 40eb6f7`+`release-projection --write` 再生（0.91 B-15 先例形态，CHANGELOG L85 同构）✓。
4. **EXC-001/002 到期处置预案**：条款面完备（EXC-001：2026-10-12 硬到期+0.93 准入前失效/撤销+每周指标+recheck 2026-10-05；EXC-002：关闭条件=获授权迁移完成+Check 27 原生 PASS+读取验证通过，延期须重审批非周报续期）——**文档化承载（docs/release/rollback-plan-0.92.0.md 等）属 M-4 四件套义务**（P3-2）。

### 重点 5：门禁终态（check-release 只读复跑）— PASS（FAILED-7 全貌=EVD-1235 两面例外一致+阶段预期态；原生执行门全绿）

本审独立复跑 `check-release --version 0.92.0 --require-changelog --lineage-mode candidate`（RELEASE 半面裁量项——CODE 半面遗留 1 明示由本半面承载；后台 job 全量 ~35min）：**Result: FAILED - 7 issue(s)**。

| # | 面 | 实跑结果 | 与 EVD-1235 比对 |
|---|---|---|---|
| 1-2 | hot fact source | FAIL×2（session-snapshot missing latest published release 0.91.0；plan-tracker missing 0.92.0 roadmap row） | **EVD-1235 未枚举**（其「版本态双发现已清」声明范围=overstate/missing active version 定向复检，CODE 半面已核实同两项零命中不失实；本两面=收口期义务——P3-1/CR-F3） |
| 3 | archive integrity | FAIL（消息「0 hot completed task(s)」=措辞错标；驱动面=证据面 178 行） | **一致** ✓（EVD-1235「archive-integrity FAIL=证据面 178 行（任务面 would=0 已闭合；EXC-002 纸质承接）」逐字吻合） |
| 4-6 | release docs | FAIL×3（release-checklist/feature-flags/rollback-plan 0.92.0 三件 missing） | **EVD-1235 未枚举**——M-4 义务（REL-094 P3-4 同型先例；P3-2） |
| 7 | execution gates | governance health exit=1（38 issues：28s evidence=EXC-001 机注 ✓ 一致；decision-log 254,420B 无例外=CR-F1；archive.py 5508=CR-F2；遗留旧行格式面 EVD-702/1194/1198=EVD-1235「0.91 既有披露面」一致 ✓；28c×2/REL-095 packet 占位=CR-F3/F4） | 28s 两层同屏+遗留面**一致**；decision-log/archive.py 两 advisory 面未披露=CODE 半面 P2 已登 |
| — | **原生执行门** | verify **exit=0** ✓｜unit tests **exit=0** ✓｜e2e **exit=0** ✓｜loop 门 PASS（semantic=PASS/identity=PASS/candidates=1096）✓ | 与 EVD-1235「verify+unit+loop+e2e 原生 PASS」**逐项一致** ✓（本审独立双源） |
| — | 静态/门禁面 | version consistency/release fact source/runtime readiness/first session/governance pack/agent adapters×6/projection sync/cross references/**release lineage（candidate）**/**gate sequence**/**one-dot-zero blockers**/changelog/governance exceptions（EXC-001 effective）/loop fuse/dsh upgrade regression 全 PASS | one-dot-zero blockers PASS=1.0.0 硬阻塞零新增 ✓；lineage candidate 态正确（boundary 注记：tag 后以 released 模式复跑）✓ |

**判定**：7 issues 全数归属三类——例外覆盖面（#3=EXC-002、#7 的 28s=EXC-001，两层报告与实跑**一致**）/阶段预期态（#1-2 收口期、#4-6 M-4）/advisory 披露缺口（#7 的 decision-log+archive.py，CR-F1/F2 承载）——**无未预期阻断项**；RISK-036 复评所引「official faces 全 PASS」亲证维持。

### 重点 6：BT-01 义务（0.92 安装后首会话抽测）— PASS（承接链三面可见）

plan-tracker L87 REL-095 行（「BT-01=0.92 安装后首会话抽测义务（M-0 已绑定）」）+ execution-packets.json goal 段（同句）+ session-snapshot L23 carry-over（「BT-01: 0.92 安装后首会话抽测（发布后承接）」）——三面绑定 ✓；授权链 DEC-272（抽测承诺）/DEC-274（总授权含「BT-01 抽测承诺兑现」）在案。发布后首会话触发路径明确，无悬空。

### 重点 7：AI 专项（数字抽核）— 5/5 通过

- **数字抽核** ✓：178=160+4+14（附件三表行数亲数）；18（有界迁移 EVD 数，EVD-1233/DEC-284 清单 2任务+18EVD）；2,036,197=1,786,197+250,000（算术）；1,753,848（EVD-1235 时点）→1,755,371（本审首测）→1,755,693（姊妹半面机录行追加后）——均 ≤ 上限、增量可归因；2026-10-12=2026-09-28+14 自然日；六票 8 hash+12 提交窗（e65b317^..df26f7e，CODE 半面对账 51 文件无夹带）。
- **mock 残留**：零——本报告全部数字来自本会话实跑输出/亲读文件。
- **硬编码/幻觉 API**：零——引用命令全部亲跑且 exit 码在案（check-release 1/DataSize 0/LRC 0/检查面均记录）。
- **TODO/未实现**：零。
- **过度实现**：零——本审只读审查+报告落盘+机录，无越界动作。

## 二、Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| RL-F1 | **P2** | project/CHANGELOG.md 0.92.0 段 | **M-2 整改叙事缺位**：DEC-283~285/EXC-002/有界迁移（2任务+18EVD）/B2 豁免全段零提及（grep 零命中亲证）；「已知边界披露」仅 EXC-001 单例外——与发布准入=双例外+B2 豁免的实际版图不符；决策链行缺 273/277（M-1 F-1 遗留）+283~285（新增）；EVD 范围 1216~1229 不含发布链证据 1230~1235；无行为变更段（0.90/0.91 先例形态） | **M-5 发布态改写 MUST 纳入**：EXC-002 条款摘要与 EXC-001 并列（覆盖面/增长容忍 0/期限/关闭条件/机注不可达注记）+B2 豁免（loop-claims 第 5 条+受控解冻语义）+有界迁移终账+决策链补全（269~285 或注明选择性）+EVD 范围含发布链证据+行为变更段（无 breaking+回滚三序说明）；并入 M-8 终账核对单 |
| RL-F2 | P3 | EVD-1235（check-release 非原生面枚举） | 枚举仅含 archive-integrity+governance health 两面，未列 hot-fact-source×2 与 release-docs×3（实跑 FAILED-7 全貌的 5/7）——均为阶段预期态非新风险，且「版本态双发现已清」声明范围（定向复检）经 CODE 半面核实不失实 | M-4 补增量 EVD 注记或随 M-4 四件套 EVD 承载 FAILED-7 全貌口径；M-8 收口 EVD 补注 |
| RL-F3 | P3 | docs/release/*0.92.0*（缺席） | 四件套未创建（release-plan/checklist/rollback-plan/feature-flags）——REL-094 P3-4 同型（M-4 义务）；本版 rollback-plan 须额外承载 EXC-001/002 到期处置预案与回滚三序（迁移 journal→B2 revert→版本面 revert+投影再生） | M-4 创建四件套（checklist 含 M-2 有条件收口双层报告+例外验收对照；feature-flags 含「本版无新增 flag——例外机制为输出标注面非 flag 面」声明） |
| RL-F4 | P3 | .governance/session-snapshot.md | 快照滞后一拍（「M-2 整改中——B2 在途」；实际 df26f7e 已提交+M-2 已有条件收口 EVD-1235）——28c snapshot 面 FAIL 的成因之一 | 会话收工快照刷新自愈（含 latest published release 0.91.0 行——M-8 released 验证 fact-source PASS 硬前置） |

**与姊妹半面去重声明**：decision-log 254,420B 无例外未披露（CR-F1 P2）/archive.py 5508 越阈未披露（CR-F2 P2）/28c 两面+REL-095 packet 占位（CR-F3/F4 P3）——CODE 半面已登记且本审 check-release 实跑**确认其呈现在发布门禁聚合面**（governance health exit=1 组成项、advisory 非致命），处置建议随 CR 原文（M-8 补披露+0.93 候选），本审不重复开票。

## 三、硬门槛自检

| 门槛 | 结果 |
|------|------|
| P0 阻塞数=0 | ✓（最高级发现=P2，为 M-5/M-8 文档义务非候选缺陷） |
| 发布就绪四维度全覆盖 | ✓（发布就绪=重点 1/5/6；质量门禁=重点 5 执行门+静态面；回滚能力=重点 4（含实弹演练佐证）；用户影响=无 breaking+例外披露面（RL-F1 为其补全项）） |
| 每条发现标注级别 | ✓（P2×1/P3×3+去重声明） |
| 事实依据红线 | ✓（全部结论可溯至命令输出/文件亲读；未实际运行项=零——本审未跑全量 pytest 独立套件，以 check-release 内嵌 unit tests exit=0+M-2 机录 EVD-1234（64P+81subtests）+CODE 半面 LRC 全量 258.96s 三源采信，归属如实声明） |
| AI 专项 5 项 | ✓（重点 7） |

## 四、M-4~M-8 放行条件清单（有条件 GO 的条件本体）

1. **M-4（放行前置门）**：①四件套创建（RL-F3——rollback-plan 含 EXC 到期处置+回滚三序）；②FAILED-7 全貌口径补记（RL-F2）；③风险窗引用（036/039/044/047 已留痕 2026-09-28+048 收窄兑现+050/059 维持引用——REL-094 M-4 同型）；④本报告+CODE 半面报告经 review-record 机录（round 3/已录 round 2）。
2. **M-5（manifest+transition+CHANGELOG 发布态）**：⑤core/releases/0.92.0.json 创建（NFC/sorted/compact；lifecycle=candidate→transition；tip 现场取值）+check-release candidate 态执行；⑥**CHANGELOG 发布态改写（RL-F1 全项+双位同步 project+root）**：日期落字（FIX-349 taggerdate 权威，M-7 后回填）+EXC-002 摘要并列+B2 豁免+有界迁移终账+决策链 269~285+EVD 含发布链+行为变更段+已知限制发布时点重测（28s 现值/decision-log 254,420B 面披露（CR-F1）/archive.py 5508 面披露（CR-F2））。
3. **M-6（ledger）**：⑦release-ledger 本地+remote 双 PASS（NATIVE_RELEASED；tag_facts 双端核对）。
4. **M-7（tag+push）**：⑧annotated tag v0.92.0+push（peel 机制+taggerdate 权威回填）。
5. **M-8（收口）**：⑨plan-tracker 工作流版本 0.92.0 收口态+**路线图 0.92.0 行回填**（28c 面——M-8 released 验证 fact-source PASS 硬前置）+session-snapshot 刷新（含 latest published release 0.92.0 三要素投影行）+released 验证（lineage/changelog/archive/docs/fact-source 全 PASS——**含例外标注路径**：EXC-001 机注在屏+EXC-002 纸质双层报告归档）；⑩零 EVD 迁移写入验证（DEC-282 C-1(b)：三族守卫有效+11 行留热口径=已复验未物理迁移）+EXC 周义务首期履行排程（EXC-001 recheck 2026-10-05/EXC-002 周报）。

## 五、证据清单（本审亲跑/亲读，2026-09-29 @HEAD df26f7e）

1. `git rev-parse HEAD`（df26f7e）+`git status --porcelain`（干净——除姊妹半面报告 untracked）+`git tag --list`（v0.92.0 缺席=M-3 前置正确）
2. `git show --stat` 12bef7c/df26f7e（M-2 两提交文件范围亲证）+`git log --oneline -12`（六票 8 hash+链节全在）
3. **check-release 全量复跑**（后台 job，--version 0.92.0 --require-changelog --lineage-mode candidate）：FAILED-7 全文日志（verify exit=0/unit exit=0/e2e exit=0/loop PASS/one-dot-zero PASS/lineage candidate PASS/EXC-001 effective 1,755,371B÷2,036,197B）
4. `check-governance-data-size` 实跑（EXC-001 两层同屏原文+decision-log 254,420B ERROR 面）
5. `check-governance --summary-only [--level strict]` 实跑（38 issues 全列表：28s×2/28c×2/28n/16/17/18b×8/18d/18d-RB2/18f×2/18i/34）
6. `check-loop-runtime-claims --product-root . --project-root .` 实跑 JSON（verdict=PASS/findings=0/exemptions_applied=5——第 5 条 accounting:79:1 B2 生效逐键）
7. exceptions.json 全文（EXC-001 五要素）+ DEC-282/283/284/285 全文（decision-log L224~227，DEC-285 尾段 1500 字符补读）
8. docs/governance/rel-095-exc002-baseline-178-20260928.md 全文（222 行：输入锚/三类逐 ID 表 160+4+14/条款摘要/机注不可达注记 L222）
9. docs/governance/fix-402-data-corrections-ledger-20260928.md 尾部（验证命令/估算标注/交付边界）
10. risk-log L37~42 亲读（036/039/044/047/048 的 2026-09-28 复评留痕原文提取）
11. project/CHANGELOG.md L1~47（0.92.0 准备态全段）+ grep（DEC-283~285/EXC-002/有界迁移/B2/受控回退——零命中）
12. plan-tracker L11/L44/L80~87/L86（FEAT-076 行 C-3 交接+REL-095 行 BT-01）+ session-snapshot 全文（BT-01 L23/0.93 池 L24）+ execution-packets.json goal 段
13. evidence-log EVD-1230~1235 六行全文+REVIEW-REL-095-R2 机录行（姊妹半面并行完成事实）+尾部行数 2928
14. core/releases/ 清单（0.92.0.json 缺席=M-5 义务未提前 ✓）；docs/release/*0.92*（glob 零命中）
15. .governance/review-REL-095-R0/R1.md（round 0/1 占位事实——round 3 归位依据）+ review-REL-095-CODE-R0.md 全文（姊妹半面结论交叉引用）

## 六、遗留不确定项

1. **全量 pytest 独立套件未单跑**（~26min）——以 check-release 内嵌 unit tests exit=0（本审）+M-2 机录+CODE 半面 LRC 全量三源采信；若 M-4 需静默窗第四源，属 Coordinator 调度裁量。
2. **EXC-002 周报/EXC-001 周指标的首期履行人排程**——条款在案但发布前无履行记录属正常（发布后义务）；M-8 收口排程建议已入放行条件 ⑩。
3. **decision-log 越阈时点**（.governance untracked 无法 git 归因）——随 CR-F1 口径（字节算术推测+不确定度如实标注），本审不重复认定。
4. M-4~M-8 步骤本身不在本审范围；RL-F1 的消化点=M-5 发布态改写（Coordinator 调度）。

---

## 终态结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**（建议有条件 GO）。

七项审查重点全部完成：发布链四节完整可追溯（PASS）；双例外治理验收全要素成立且互不覆盖、期限一致、实名 owner、0.93 承接绑定（PASS）；CHANGELOG 准备态骨架成立但 M-2 整改叙事缺位列 P2-1（M-5/M-8 必补）；风险窗 2026-09-28 留痕齐备+回滚三序可执行（迁移面已实弹演练）（PASS）；check-release 只读复跑 FAILED-7 与 EVD-1235 双层报告两面逐字一致、原生执行门全绿、无未预期阻断（PASS）；BT-01 三面可见（PASS）；AI 专项数字全核（PASS）。无 BLOCKING finding；P2×1 为 M-5 发布态改写范围义务，P3×3 随 M-4/M-8 承载；与 CODE 半面（R2 AWN/0）去重互恰。终局 go/no-go 决策权在 Coordinator（M-4，消费风险窗复评结论）。本审查未修改产品文件；review-record 机录 round 3 随本报告执行。
