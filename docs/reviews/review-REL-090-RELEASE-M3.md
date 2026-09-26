# REL-090 M-3 发布半面窄域复审（RELEASE-M3）

- **审查人**：Release Reviewer Agent（独立链）· **Round**：R0 · **日期**：2026-09-26
- **范围声明**：严格窄域四项——零测试/check 执行（消费 EVD-1184 既有实测记录）、除本报告外零写入、只读命令（read/grep/git log/rev-parse/diff --name-only）。
- **前序事实引用**：EVD-1184（M-2 全席实测）；review-REL-090-CODE-M3.md（CODE 半面 AWN/0，P2×2 version-plan 记录面出入+四抽查义务全 PASS）；REL-091/092 个审 AWN/0 在案。

## 项 1 —— M-2 回填一致性（checklist #1~#17 vs EVD-1184）→ **PASS**

> 注：任务书写 #1~#16；checklist 门禁表实际为 #1~#17（#17 revert 干跑裁决面），EVD-1184 事实依据段同称 #1~#17——按实际全表对照。

| # | checklist 回填值 | EVD-1184 申报 | 裁决 |
|---|---|---|---|
| 1 | pytest 4217P/8F/1S+556 subtests（1191.45s）；8F=archguard×3+loop/FIX300×5 既有基线；净新增 +98 | 同值（4217P/8F/1S+556；archguard×3 随 regen 消解；loop/FIX300 共 5F；+98=4119→4217） | ✅ |
| 2~7 | verify PASSED（唯一 WARN 过渡态）/version-consistency 0 WARN/注入 4216·5694·5966≤6000/projection 三席 PASS@0.89.0/cross-refs 0-0-0/manifest PASS | 同值逐项对应 | ✅ |
| 8 | regen 26193→26358；R1~R7 PASS 0 violations；pin 再基线 38/38P；R4 1318；R5 97/97+71/71 | 同值（含 +165 归因链 EVD-1176 承接——非静默清零） | ✅ |
| 9 | contract-matrix zero drift（97 键，R5 承载） | 经 #8 R1~R7 PASS 间接承载（见 N-1） | ✅* |
| 10 | ledger 预期 FAIL（FileNotFoundError——manifest M-5） | 同值同归类（预期 FAIL 非豁免） | ✅ |
| 11 | e2e 6-0/4-0/9-0/5-0+隔离冒烟通过 real-home writes 0 | 同值 | ✅ |
| 12 | 组合四项 122P+23 subtests；check-archive-integrity PASS 1297 索引 | 同值 | ✅ |
| 13 | census 39 分段全枚举；身份集 REQ-092×6+EVD-1146×1+in-flight×4+ragged×3+Check28s×1 | 同值；49→51→39 时点归因入 EVD（P3-2 教训采纳：附分段快照） | ✅ |
| 14 | 前置归档席 dry-run 50/0 满足零写跳过；1,763,887B ERROR 维持 M-8 复测 | 同值同措辞（不虚报消解） | ✅ |
| 15 | FEAT-065 双面演示 5P∥3P（真实 CLI 零 mock） | 同值 | ✅ |
| 16/17 | check-release M-5 承载 NOT_RUN 如实 / revert 干跑未排程维持 | EVD 无矛盾申报（M-5 期义务口径一致） | ✅ |
| LRC | BLOCKED（semantic_only）；330,494≤361,923；UNSUPPORTED_AFFIRMATIVE×3 全在 legacy 文件 | 同值同披露 | ✅ |

**过程事件双向如实**：Coordinator M-1 后过早翻 plan-tracker 版本→28c×2 瞬态→回滚恢复——checklist L167 与 EVD-1184 归因段一致入账。**未发现虚报/漂移**（EVD 行尾截断段以可读部分核对，申报粒度差异见 N-1）。

## 项 2 —— 回滚方案可执行性 → **PASS**

- **区间锚**：`git rev-parse v0.88.0^{}` = `33d19b0e7eab…` = `git rev-parse 33d19b0` 实证同一；tag object `82905e6f8115…` 与 rollback-plan §区间锚定声明一致。终点 `<发布 tip>` 未生成不预填（M-5 义务——符合保守边界声明）。
- **窗口计数**：实测 `git rev-list --count 33d19b0..HEAD` = **16**（HEAD=`bda7e88`）。12（M-1R 实测）+ `bb6a460` M-1R 四件套 + `d6186ee`/`d293a9e` 两审报告落档 + `bda7e88` M-2 批 = 16，逐 commit 可归因；rollback-plan L24 明示「区间计数不写死：M-5 现场取值」——设计已吸收（见 N-2）。
- **FEAT-065 回退两文件存在性（read 实证）**：`skills/software-project-governance/infra/closure_chain.py` ✅ + `skills/software-project-governance/infra/tests/test_closure_chain.py` ✅——rollback §1「还原两文件」程序对象在场；同文件串行禁单票选择性还原注记在案（§1/§5#6）。
- **B-12/B-13 引用锚存在性**：`rollback-plan-0.88.0.md` §7（L153 B-12/B-13 回退显式化专节）+ §8（L174 部署 tag vs revert 区分节）双锚在场——0.89 §7 引用不触发语义成立。
- **程序完整性**：单轨 revert 程序（§2.1）+ 用户侧四步（§2.2）+ 中止窗口（§2.3）+ 13 项验证表（§4）+ 不可回滚项 8 条（§5）+ 触发条件 8 条（§6）+ 路径 A/B（§8）+ 0.90 移交（§9）齐备。回滚演练未排程如实标注（§4#10——0.85~0.88 四版先例同型；tip 未定先干跑无意义）——维持 checklist #17 裁决：不排程不阻断。

## 项 3 —— 「无新增功能激活」三方一致 + 零触碰 → **PASS**

- **三方同口径**：①feature-flags-0.89.0 保守边界 L14+§1 L20（B-12 全 WARN·0.89 窗口无 `--activate-block` 执行 / B-13 缺省 `MD_ACTIVE` 零足迹·无真实切换）；②CHANGELOG 0.89.0 段行为变更节 L60（同两句措辞，DEC-246⑥ 口径）；③checklist 保守边界 L14（同口径并互引「与 CHANGELOG 同口径·详见 feature-flags §5」）。三方均引 DEC-244（激活授权票不捆绑）+ DEC-246⑥（措辞收紧——行为修正三面非激活面），**一致无漂移**。
- **零 posture/state 工件触碰（git 实证）**：`git log --name-only 33d19b0..HEAD` 全窗口（16 commits，57 files，+7615/−243）diff 文件清单中 `posture`/`decision-store-state`/`write-guard`/`decision_repository`/`MD_ACTIVE` 模式命中 = **0**。任务前提 15 commits 与实测 16 差异 = 任务书写时点早于 `bda7e88` 落库；16 为 15 的超集，零触碰结论在更大范围成立（见 N-2）。
- 窗口内含 M-1 bump（版本面 24 文件）与 M-2 批——均为治理/文档/测试面，行为修正三面（①gate 闭集 ②零写拒绝 ③判据收敛）在 CHANGELOG/feature-flags/rollback 三处回退口径逐字对齐。

## 项 4 —— go/no-go 建议面（建议权在 Reviewer，决策权在 Coordinator+arch）→ **建议 go-with-conditions**

**依据**：M-2 全席实测回填一致（项1）；门禁面可发布性经全席实测背书（verify/version/budget/projection/refs/manifest/archguard R1~R7/组合/e2e+隔离冒烟全绿；8F 全部既有基线披露非窗口引入）；双半面审查在案（CODE AWN/0 + 本审 AWN/0）；REL-091/092 AWN/0；回滚方案可执行且引用锚实证在场（项2）；无激活声明三方一致+零触碰实证（项3）。**no-go 无事实支撑**（无 P0/P1、census 身份集达成、零新增未授权阻断项）；**无条件 go 不成立**——发布完成前存在设计内必收口义务。

**条件清单（M-4 裁决前/M-5~M-8 依序履行）**：
1. **09-30 风险窗履行**（RISK-036/039/046 复评+RISK-047/048 观察）入账后方可 go/no-go（DEC-244 必选项；不迟于 2026-09-30）；
2. **M-5 收口**：candidate manifest 创建（NFC/sorted/compact）+ ledger NATIVE_CANDIDATE PASS（#10 刷新）+ check-release candidate 态执行（#16 刷新；DEC-246⑧ 绑定核验）；
3. **M-6 预推校验全绿方进 M-7**（released 模式+`--remote origin`；UNKNOWN/BLOCKED 不得包装 PASS）；
4. **census 身份集维持**至 tag（REQ-092×6+EVD-1146×1——零豁免红线；零新增未授权阻断项）；
5. **M-8 义务保留**：Check 28s 复测（1,763,887B ERROR 维持——不虚报消解）+ plan-tracker 版本收口 + roadmap 行回填；
6. 若补 revert 演练：MUST 隔离副本 + 真实 tip 生成后复跑（rollback §4#10）。

## Findings

- **P3-1（记录级）**：EVD-1184 对 #9 contract-matrix 97 键/R5 97+71 无独立单列（经 archguard R1~R7 PASS 间接承载；checklist #8/#9 数值自洽）——申报粒度改进建议：关键门禁值单列留证。
- **P3-2（记录级）**：窗口计数时点漂移 12→16（checklist L31/EVD 起草时点 12；本审实测 16）——「计数不写死：M-5 现场取值」设计已吸收；建议 M-5 取值时同步刷新 checklist L31 注记或以 M-5 EVD 为准。
- 无 P0/P1/P2 发现；无 BLOCKING finding。

## 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

四项裁决：①M-2 回填一致性 PASS ②回滚方案可执行性 PASS ③无新增功能激活三方一致+零触碰 PASS ④go/no-go 建议=go-with-conditions（条件 6 条如上）。无 BLOCKING；P3×2 记录级 notes 不阻断发布链推进。终局 go/no-go 决策权在 Coordinator+arch（M-4，消费 09-30 风险窗结论）。
