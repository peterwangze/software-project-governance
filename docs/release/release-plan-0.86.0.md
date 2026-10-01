# Release Plan — 0.86.0（REL-082 M-1R / REL-083）

> **任务**: REL-083（P1；triage `.governance/change-triage/REL-083.json`；DEC-221 预授权链——M-1 GO 后 M-2）· **日期**: 2026-09-20 · **性质**: M-1R 发布材料面（四件套：release plan/checklist/rollback/feature-flags）+ M-2 门禁实测 + closure 量测首跑（sandbox 副本）——非发布执行
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-221 预授权承载；预授权**不免除** M-2 门禁实测与 M-3 双半面审查）；本文件由 Governance Developer Agent 起草，供 Release Reviewer / M-3 审查链消费
> **写入边界**: 仅本四件套（triage `files` 锁定面）；不触 `.governance/` 真实治理数据（量测全在 sandbox 副本——三重 SHA256 零写入证明）、不修改产品代码（门禁只读跑）、不改 CHANGELOG（已于 `44831b8` 冻结）、不执行 tag/push/transition；`core/releases/0.86.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-1R 提交批补齐（本票如实披露，见 checklist 披露 ①）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim**：official approval 未被授予、未被主张；0.86.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.86.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.86.0 为内部治理效率版（写入器时代第一版）；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本四件套不预填——hash 一律由 M-5 生成后回填（FIX-349 口径：taggerdate 权威）。
- **量测维度①不主张**：closure 量测历史相对改善 = `NOT_EVALUABLE`（无可信历史 trace 基线——R-F10 固定措辞「基线不可评估（无可信历史 trace）——未宣传达成」）；维度②绝对目标为本版 M-2 首跑实测（见 checklist 量测专节），历史对照数字仅作机制叙述不构成达成主张。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.86.0**（MINOR；0.85.0 → 0.86.0 不跳号、无预留占用） |
| 发布任务 | **REL-082（规划）/ REL-083（M-2+M-1R）**——REL-082 双半面规划双审 R0→R1 通过（Design R1 + Release R1 双 APPROVED_WITH_NOTES/0，复审必达 T1×2；EVD-1102） |
| 授权链 | DEC-220（确定性核心 / LLM 边界设计公理）→ **DEC-221（0.86.0 设计演进全链预授权：「设计打磨完成后授权 Coordinator 按推荐推进直至完全闭环并发布对应版本」；预授权不免除门禁）** → DEC-222（批 1 归属裁定）/ DEC-223（接线契约口径）/ DEC-224（write-guard 契约修订三条款） |
| MINOR 依据 | `core/VERSIONING.md` L12「新增 B/C 级自动化能力」（四类原子写入器 CLI + contracts.py 契约 MUST 规则扩展 + write-guard 行族全覆盖上线路由——新增受治理能力面）；非纯 bug fix（L38 PATCH 不适用）；Breaking changes = **无**（write-guard 为 WARN 姿态上线路由非门禁硬化，L11 不触发；B-3 保持手工路径兼容——CHANGELOG 0.86.0 段同口径） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release 面产出物由角色 agent 执行，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与 28 投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带 B-3/B-4（CHANGELOG 行为变更节原文口径） |

## 发布范围

### 载荷构成（批 0 / 批 1 / 批 2 + M-链——DEC-220/221）

> git 窗口实测：**0.86.0 窗口 = `c2cc7c1..<发布 tip>`**（`c2cc7c1` = `v0.85.0` tag peel = transition 提交，taggerdate 2026-09-20 01:53:52 实测）；`c2cc7c1..44831b8` 实测 **5 提交**（批 2 全部 + M-1 bump）。批 0/批 1 四提交随 `v0.85.0` 树入库（0.85.0 零行为消费——DEC-222 归属裁定，CHANGELOG 0.86.0 段正式承载）。

| 批 | 任务 | 关键交付 | 提交 | 落库窗口 |
|---|---|---|---|---|
| **批 0「M0 契约冻结」** | FEAT-049 | contracts.py 五面契约冻结 revision **m0-r1**（573→1,140 行纯追加；99 存量契约测试零回归 + 58 新增）+ 量测协议工件（`benchmarks/closure/protocol.md` + 用例组三路径） | `27eeea0` | v0.85.0 树内（零消费） |
| **批 1「原子写入器三票」** | FEAT-051 | task-row-update 写入器 CLI（B-1 根终结面：五步写流程/短时文件锁 fail-closed/双层 CAS/凭证侧车 18 键/effect-based 幂等） | `b2152ea` | v0.85.0 树内（零消费） |
| | FEAT-046 | governance_store 写入器族（B-2/B-3/B-5 根终结面：locks-extend/locks-amend + evidence-append 五类型引用机检 + decision-append） | `1cd224e` | v0.85.0 树内（零消费） |
| | FEAT-047 | BaselineMetadata provenance 机制（W-3 制度化解药：14 必填字段/baselines.json/evaluate 分轴/CLI 退出码 0-1-2-3） | `bff298d` | v0.85.0 树内（零消费） |
| **批 2「集成窗+closure 纵切+混沌发布门+write-guard 执法」（0.86.0 git 窗口载荷）** | FEAT-055 | 集成窗：三写入器 dispatch 接线 **7 键** + 冻结面 88→95 三重钉（DEC-223）+ archguard regen + 留置八项收口 | `a5dec3d` | **0.86.0 窗口** |
| | FIX-365 | review-FEAT-054-RELEASE-R0.md L83 ragged row 转义修复（存量 5 项测试转绿 + LRC PASS + 独立扫描 1→0） | `a7474e4` | **0.86.0 窗口** |
| | FEAT-056 | closure-chain 纵切 + 混沌发布门（B-4 根面终结：纯序排器/独立事件日志/effect-based resume/ready-to-commit 终点；三边界 kill+resume 零人工修复） | `7709987` | **0.86.0 窗口** |
| | FEAT-057 | write-guard 行族执法上线（面 5 受管行族对账 + WARN 姿态路由 + 状态基线 amnesty + 超时恢复腿——**首活体实证 EVD-1117 被 WARN 精确捕获**） | `ffcb787` | **0.86.0 窗口** |
| **M-1 候选打包** | FEAT-058 | 0.85.0→0.86.0 全仓 bump（24 tracked：手工 5 + 再生 19）+ CHANGELOG 0.86.0 段（批 0/1/2 八票+治理面）+ 豁免账本 11 行（FIX-361 bump 程序：scan 11 行逐行归因全部登记） | `44831b8` | **0.86.0 窗口**（REVIEW-FEAT-058-R0 = APPROVED_WITH_NOTES/0——**M-1 GO**） |
| **⑥ 治理面** | REL-082 | 规划闭环 + 7 决策（DEC-218~224）+ 17 EVD（EVD-1102~1118，含写入器时代三活体实证）+ 八票 Developer→Reviewer 审查链全闭环（0 unresolved blockers——含 NEEDS_CHANGE→R1 转化四票） | — | — |
| **M-1R 发布面（本票）** | REL-083 | **四件套**（plan/checklist/rollback/feature-flags——本票 expected-new 锁面）+ M-2 门禁实测 + closure 量测首跑（sandbox 副本零写入）。`core/releases/0.86.0.json` 与 M-2 复跑义务由 Coordinator 提交批承载（锁面外披露，checklist ①） | 本票（Coordinator 提交后为 candidate commit） | 待提交 |

### 本版不发布什么（显式排除——Amazon 实践）

1. **write-guard BLOCK 升级**（WARN→BLOCK——DEC-224 双约束：不得 WARN-once-then-absorb + hook 窗口消费权台账化；留 0.87）；
2. **locks-release 命令缺口修补**（shrink-locks 以 TTL 收缩为最近 Governed 效果——如实披露非静默）;
3. **存储分离 JSON 化**（首表 decision-log）/ closure 铺开（取消/重开/异常接管）/ FEAT-044 回合心跳 / FEAT-045 并行段识别 / B-7 index-rebuild / 大表迁移 / 发版管线自举（0.87 候选池——CHANGELOG 披露⑤）；
4. **FIX-366 引擎两阶段耦合修复**（projection.py 单遍 plan 缺陷——本版 M-1 沿用 FEAT-053 同款绕开手法，fail-closed 无静默腐坏；修复票 0.87.0 在案）；
5. **FIX-364 snapshot freshness 午夜窗修复**（triage 在案未实施；本版全量 pytest 0 失败不含该面——见 checklist #13）；
6. **任何 RISK 的关闭声明**（本版无 RISK 关闭承诺；RISK-036/039/050 维持打开态以 risk-log 实况为准）。

## 回滚区间锚定（两段论证——与 rollback-plan-0.86.0 §区间锚定同锚同源）

**本版回滚区间（triage 锚定，候选面）= `ffcb787..<发布 tip>`；禁用 `44831b8..<发布 tip>`**：

- **论证①（下界必须是 `ffcb787`，不得写 `44831b8`）**：git 区间语义 `X..Y` **排除下界 X 自身**。`44831b8` = FEAT-058 M-1 bump（版本声明面 0.85.0→0.86.0 的 26 文件 diff：SKILL frontmatter 权威源 + 28 投影面 + CHANGELOG 段 + 豁免账本 11 行 + hooks 版本行 + canonical 标记）——**M-1 bump 属候选面**，其 diff 必须完整落在撤销集内。若区间误写 `44831b8..<tip>`，bump diff 残留 ⇒ 回滚后版本声明面仍是 0.86.0 而载荷/行为面已回退 = **版本-载荷不一致混合态**（0.81.0 回滚审查 R0 **F-01** 同形失效模式：区间误写代表提交致首项 diff 残留）。`ffcb787`（FEAT-057 批 2.3——批 2 全清点 + write-guard 执法上线提交）作为下界把 M-1 bump 完整纳入撤销集。
- **论证②（终点必须是 `<发布 tip>`，不得是候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，本文件不预编造）。
- **⚠️ 窗口构成如实披露（M-3 Release Reviewer MUST 复核——0.85.0 先例同款义务）**：0.86.0 完整 git 窗口 = `c2cc7c1..<发布 tip>`（`c2cc7c1..44831b8` 实测 5 提交：批 2 四提交 `a5dec3d`/`a7474e4`/`7709987`/`ffcb787` + M-1 bump `44831b8`，v0.85.0 taggerdate 2026-09-20 01:53:52 之后逐日落库）。**triage 锚定 `ffcb787..<tip>` 为候选面区间（撤销 M-1 bump + M-1R 材料）；批 2 行为载荷（closure-chain/混沌门/write-guard 执法/7 键接线）位于该下界之前，不随候选面区间撤销**——完整行为回退（回到 `v0.85.0` 行为）MUST 采用整窗区间 `c2cc7c1..<发布 tip>` revert（0.85.0 先例「区间锚定」节整窗口径）或 `git checkout v0.85.0`（替代锚，不等价——落点缺 M-1 后文档面）。双轨适用场景与裁决点见 rollback-plan-0.86.0 §区间锚定与 §2.1。

## M-链状态（截至本文件落盘 2026-09-20）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 规划确认 | ✅ 完成 | REL-082（2026-09-19/20）：深度检视→arch 顾问多轮→架构演进设计→版本规划四交付；Design R1 + Release R1 双 APPROVED_WITH_NOTES/0（复审必达 T1×2）；DEC-220/221 生效；EVD-1102 |
| 批 0（M0 契约冻结） | ✅ 完成 | `27eeea0` FEAT-049：revision m0-r1 冻结 + 量测协议工件；REVIEW-FEAT-049-R0 APPROVED_WITH_NOTES/0；EVD-1105 |
| 批 1（写入器三票） | ✅ 完成 | `b2152ea`/`1cd224e`/`bff298d`：三票审查链全闭环（各 R0 NEEDS_CHANGE→R1 APPROVED_WITH_NOTES/0）；EVD-1108/1110/1111 |
| 批 2（集成窗+纵切+执法） | ✅ 完成 | `a5dec3d`/`7709987`/`ffcb787` + `a7474e4`：批 2 全清（EVD-1114/1115/1116/1117）；write-guard 首活体实证 + DEC-224 机录路径开通 + 首机录 EVD-1118 |
| M-1 候选打包 | ✅ 完成（GO） | `44831b8` FEAT-058（2026-09-20 14:52）：bump 24 tracked + CHANGELOG 段 + 豁免账本 11 行；REVIEW-FEAT-058-R0 = APPROVED_WITH_NOTES/0（4/4 复验）——**M-1 GO**；F-2→FIX-366 落票 |
| **M-1R 发布面（本票）** | 🔄 本票执行 | REL-083：四件套 + M-2 门禁实测 + closure 量测首跑 |
| M-2 门禁实测 | 🔄 本票承载 | A 清单全部实测（8 项——见 checklist Candidate Gate Results 与量测专节——verify/pytest 3820/archguard/contract-matrix/三 profile/混沌 35/量测首跑/e2e+dsh 冒烟）；check-release 复合门禁与 candidate 提交后 ledger 复跑 = Coordinator 提交批义务 |
| M-3 双半面审查 | ⏳ 待 Coordinator 派发 | Release Reviewer + Design/Code Reviewer（按变更面）；review-record 机录；复审必达；**含回滚区间双轨裁决（见上节披露）** |
| M-4 用户停点 | ⏳ DEC-221 预授权 | 预授权不免除 M-2/M-3；go/no-go 由 Coordinator 呈现裁决 |
| M-5 transition + tag | ⏳ Coordinator 面 | candidate manifest 提交（复跑 `release-ledger --no-remote` 期望 NATIVE_CANDIDATE PASS）→ release commit（单父 = candidate；manifest-only candidate_to_released + integrity）→ annotated tag v0.86.0（peel = transition commit） |
| M-6 released 门禁 | ⏳ M-5 后 | `check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote` |
| M-7 push | ⏳ Coordinator 面 | master + tag 原子推送（远端 SHA 精确一致） |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | `archive.py migrate --auto --dry-run` → 迁移 → `check-archive-integrity` PASS；plan-tracker `工作流版本` → 0.86.0（当前 0.85.0 过渡态 WARN——check-version-consistency 实测在案，本版 verify 唯一预期 WARN） |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-19 | REL-082 规划闭环（四交付 + 双审 R1）+ 批 0/批 1 落库（随 0.85.0 树） |
| 2026-09-20 上午~午后 | 批 2 四提交落库（`a5dec3d` 09:23 → `a7474e4` 09:59 → `7709987` 11:22 → `ffcb787` 13:48）+ M-1 bump `44831b8`（14:52，M-1 GO） |
| 2026-09-20 | **M-1R/M-2（本票 REL-083）**：四件套 + M-2 门禁实测 + closure 量测首跑（sandbox） |
| M-3 后 | 双半面审查（含回滚区间双轨裁决）→ M-4 go/no-go（DEC-221 预授权呈现）→ M-5 candidate 提交/transition/tag（发布时点按 FIX-349 口径 = **taggerdate 权威**） |

## 门禁摘要（数值基线——本票 2026-09-20 当场实测）

| # | 门禁面 | 基线 / 姿态 | 依据 |
|---|---|---|---|
| 1 | 注入预算 resident 三 profile（**hard**——0.85.0 翻 hard 延续） | lightweight **4,216**/6,000 · standard **5,694**/6,000 · strict **5,966**/6,000 —— 全 PASS（与 0.85.0 基线逐位一致）；`Over budget — gated: none` | 本票实测（check-injection-budget ×3 --fail-on-issues 全 exit 0） |
| 2 | skill 层独立预算线（report-only） | entry-skill **14,459/16,000** ok——**R-F4 动态口径当场值**（较 0.85.0 的 14,456 +3，边缘内；version-plan-0.86.0 §5.5：「34 tok 为申报值不作规划输入，M-2 以批 2.2 canonical 重测当场值为动态口径」——本值即 0.86.0 基线记录）；command 3,466/6,000 report-only | FEAT-052 / version-plan §5.5（R-F4）+ 本票实测 |
| 3 | 混沌测试发布门 | **test_closure_chain 35 passed**（40.07s——三边界 kill+resume + 超时恢复腿）；**本版 M-2 MUST 已履行**（0.85.0 门禁摘要 #3 承诺的兑现面） | 本票实测 + FEAT-056 交付 |
| 4 | closure 量测首跑（三维验收维度②） | **标准路径 LLM 逻辑往返 = 2 ≤ 2 达标**（协议 m0-r1 §1 口径：触发 1 + 结果确认 1；链引擎自身零 LLM 往返）；维度① = NOT_EVALUABLE（固定措辞）；维度③机制正确性 = kill+resume 零重复追加零人工修复实测 + 混沌 35 | 量测协议（FEAT-049 冻结）+ 本票 sandbox 首跑实测 |
| 5 | 既有测试失败披露口径 | 全量 pytest **3,820 passed / 0 failed** / 1 skipped（GBK 负控按设计）/ 502 subtests——0 失败，无归因义务残留 | 本票实测（1119.43s） |
| 6 | 投影 / 版本面 | release-projection check-only 28 面 PASS（source=0.86.0）；check-projection-sync / check-entry-bootstrap-sync PASSED；版本声明 13 面 + bootstrap markers 一致（1 WARN = plan-tracker 过渡态，M-8 收口） | 本票实测 + EVD-1119（M-1） |
| 7 | 冻结面 / 棘轮 | archguard R1~R7 全 PASS 0 violations（R5 cli keys **95/95** + segments 71/71——FEAT-055 冻结面 88→95 三重钉消费面）；contract-matrix **zero drift**（4 faces）；manifest canonical 825 / actual 946 PASS | 本票实测 |
| 8 | candidate ledger 两态 | 本票实测 `release-ledger --version 0.86.0 --no-remote` = **FAIL（预提交态预期）**：`core/releases/0.86.0.json` 尚未创建（manifest 属 M-1R 候选打包面——本票锁面外）；Coordinator 提交后 MUST 复跑（期望 NATIVE_CANDIDATE PASS）→ M-5 后 `--remote` | ADR-010 / 0.85.0 #9 同流程 |

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.85.0 FEAT-054 先例无缺面 | **PASS** | 结构逐节对照 `release-plan/checklist/rollback-plan/feature-flags-0.85.0.md`；全表行管道符转义审查（FIX-365 ragged 教训——表 cell 内零裸管道符（转义感知扫描复核）） |
| verify 全量 | **PASSED**（exit 0；唯一 WARN = plan-tracker 过渡态） | checklist #1 |
| M-2 pytest 全量结果如实 | **3,820 passed / 0 failed** | checklist #13（无先在失败归因义务——0 失败） |
| 量测数据完整（往返计数 + 对照论证 + cases 一致性） | **PASS** | checklist 量测专节（协议 m0-r1 全口径 + 三路径 cases 逐项对照） |
| release-ledger candidate 态 | 提交前 FAIL（预期——manifest 锁面外未建）→ Coordinator 提交后 PASS | checklist #12 披露 ① |
| 真实 `.governance/` 零写入 | **PASS（三重 SHA256 证明）** | sandbox 副本 2,041 文件；真实治理数据 hash 前=中=后 `82360d92…` 逐位一致 |
| 不触在途面 / 不改产品代码 / CHANGELOG 不再改 / tag·push·transition 不执行 | **PASS** | 写入面 = 四件套（triage files 锁定）；门禁全部只读执行 |

---
*REL-083 M-1R 起草冻结（2026-09-20，Governance Developer Agent）。事实基线：5 提交窗口与 hash 取自 `git log`/`git rev-list`/taggerdate 实测（`c2cc7c1..44831b8` = 5；`v0.85.0` taggerdate 2026-09-20 01:53:52 = peel `c2cc7c1`）；门禁数值取自 2026-09-20 当场命令输出（M-2 A 清单 8 项全实测）；B-3/B-4 与 0.87 候选池口径取自 CHANGELOG 0.86.0 段（`44831b8` 冻结版）；量测数据取自 sandbox 首跑当场记录（protocol m0-r1 口径）。未生成事实（发布 tip、tag、released 态门禁、candidate manifest 提交）一律标期义务，不预填。*
