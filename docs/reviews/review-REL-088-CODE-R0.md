# Code Review Report — REL-088（0.88.0 M-1R 四件套 · R0）

> **Round**: R0（首轮） · **Task**: REL-088（P1——发布链 M-1R；0.87 四件套先例形态） · **日期**: 2026-09-25
> **审查对象**（四新建文件，docs/release/）: `release-plan-0.88.0.md` / `release-checklist-0.88.0.md` / `rollback-plan-0.88.0.md` / `feature-flags-0.88.0.md`
> **审查者**: Code Reviewer Agent（只读审查——未修改被审文档/产品代码/.governance/；唯一写入面 = 本报告）
> **审查方法**: 全文逐节通读 + 实测优先——git 实测（tag peel/count/describe/29 提交全量逐票对照）、命令面实读（write_guard_state.py / decision_repository.py / decision_migration.py / verify_workflow.py / behavior_profile.py / loop_runtime_claims.py 六文件引用行段）、治理数据实读（evidence-log EVD-1132~1163 全量 / decision-log DEC-238④/DEC-239⑦ / risk-log RISK-059）、四连复跑（cross-refs / manifest / version-consistency / release-projection）、对照源实读（version-plan-0.88.0 §3/§3b/§5/§7、CHANGELOG 0.88.0 段、0.87.0 四件套先例）。
> **并行面隔离声明**: 工作树 M-1（REL-087）bump 在途（25 文件）——本审查严格限定四新建 docs/release/ 文件；版本 bump 面仅以「M-1 工作树交付待提交」事实核对其申报一致性，不做 bump 内容审查。

---

## 总结论（先行）

**APPROVED_WITH_NOTES — unresolved_blockers = 0**

- P0 = 0；P1 = 0；P2 = 1（已披露留勘误、实测可收紧定性、不阻塞）；P3 = 2。
- 八项 MUST 重点审查全部通过；载荷、区间锚定、命令面、四重点席、灰度正交性、边缘披露、四连复跑均有实测背书，未发现虚构事实、越权主张或预填未生成事实。
- 唯一 P2 为 24 票逐票表对 EVD-1139 的列示遗漏（归属实测明确为 FIX-374，Developer 边缘披露定性「归属未明」可收紧）——详见发现清单。

---

## 一、重点审查项逐项结论（8/8）

### ① 载荷准确性（24 票表 vs git 实测）— **PASS**

- **窗口全量实测**（非抽验——29 提交逐票对照，超出 ≥8 票要求）：`git log --oneline --reverse v0.87.0..HEAD` 实测 29 提交，与 release-plan §发布范围逐票表、checklist §Change Inventory 表**逐票 commit hash 全部命中**（`fc69196`/`3c3218d`/`44cb534`/`6845756`/`266c32b`/`7d6ff6a`/`0233f49`/`04b7a42`/`3d31c49`/`d6dd300`/`17e5663`/`0840876`/`9df2381`+`cdc3a0a`/`b3577c8`/`b7df86c`/`c349f8e`/`b03a0b4`/`ce93eb3`/`c515776`/`0ff12f3`/`61618a5`/`a8afcbf`/`14797be`/`6360ab1`/`467fb55`/`d68355f`/`d7b9add`/`3fb42c0`）。
- **算术闭合**：29 = 1（`fc69196` 前版收尾）+ 3（M-0 三批）+ 25（24 票任务，FIX-389 双提交 `9df2381`+`cdc3a0a`）；A14+B2+C1+D1+E6 = 24 票 ✓。
- **审查终态逐票比对**（commit message 交叉验证，抽样覆盖 ≥15 票）：FIX-375 R0 APPROVED_WITH_NOTES/0→R1 APPROVED/0、FIX-386 R0 NEEDS_CHANGE/1→R1 APPROVED/0、FIX-387 APPROVED/0、FEAT-061 R0 NEEDS_CHANGE/2（P0-F1 竞窗数据丢失+P0-F2 砖化）→R1 APPROVED_WITH_NOTES/0、FEAT-062 R0 AWN→F-1~F-3→R1 APPROVED/0、FEAT-063 R0 NEEDS_CHANGE/1→R1 AWN、FIX-384 R0 NEEDS_CHANGE/1→R1 AWN、FIX-385 R0 AWN→F-1→R1 AWN、FEAT-044 AWN/0（9 MUST+17 探针）等——与文档宣称**逐票一致**；审查报告文件抽样（docs/reviews/review-FEAT-061-CODE-R1.md：`## **APPROVED_WITH_NOTES** — unresolved_blockers = **0**`，R0 = NEEDS_CHANGE/2）与宣称终态吻合。
- **EVD 在场性全量核验**：EVD-1132~1163 共 30 条在 `.governance/evidence-log.md` 全部在场，任务归属逐条与文档一致（1132/1133→REL-084；1134/1135→FIX-373；1136/1137→FIX-378；1138/1139→FIX-374；1140/1141→FIX-375；……1163→FIX-385）。唯一列示偏差见 P2-1。
- **M-0 链终态**：`0233f49`（Release R2 GO）/`7d6ff6a`（N1 自指修复）/`266c32b`（v2 落库+§3b 补入）与 release-plan M-0 行、checklist #16 专席③ 修复链叙事一致。

### ② M 链映射一致性（release-plan 十行 vs version-plan §3b）— **PASS**

- release-plan M 链表（M-0/M-1/M-1R/M-2/M-3/M-4/M-5/M-6/M-7/M-8 十里程碑行 + 载荷状态行）与 version-plan-0.88.0 §3b 逐行对齐：M-2 行「§3 全条目 + F-6 28s 复测 + 组合测试四条 + 证明包门 + 全量 pytest 一次预算」= §3b M-2 行原文展开 ✓；M-3 行「双半面+按阶段边界分节+review-record 机录+复审必达」= §3b 原文 ✓；M-5/M-7/M-8 分解与 §3b「transition candidate→released + tag v0.88.0 推送 + ledger PASS + M-8 归档迁移含 Check 28s 消解复测 + roadmap 0.88.0 行回填 + REL-086 行终态回填」逐项对应 ✓。
- **M-4 修复窗非标签填充**：version-plan §3b 未单列 M-4，但 0.87.0 先例 M 链有「M-4 用户停点」（go/no-go 由 Coordinator 呈现裁决）；0.88 M-4 =「修复窗 + go/no-go（DEC-229 预授权形态，门禁不予放弃）」为语义兼容演进，且 F-13 口径（RISK-036/039/046 窗裁决 2026-09-30 到期即裁决、不迟于 M-4、Check 8 自 10-01 转 FAIL）与 version-plan §7 原文逐字一致——有事实依据。
- **M-6 预推校验非标签填充**：0.87.0 先例 M-6 行同命令面（`check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote`）；EVD-1133 实测在场（REL-084 M-6 released 门禁复跑——release-ledger --remote origin = PASS/NATIVE_RELEASED），先例流程真实存在 ✓。
- 对照 0.87.0 四件套先例（docs/release/ 四文件 0.87.0 版全部在场）：结构逐节同形，无缺面。

### ③ B-12/B-13 双层表述正确性（命令面实读背书）— **PASS**

- **B-12**：`write_guard_state.py` L301 `POSTURE_CONFIG_FILE_NAME = ".write-guard-posture.json"` ✓；L299-300 注释「written ONLY by the guard CLI management modes; absent = all-WARN = byte-identical WARN-era behavior」——「guard CLI 管理模式独占写入」「文件缺席 = 全 WARN = 零足迹」双语义背书 ✓；L1668-1671 管理 CLI 六动作（activate_block/deactivate_block/show_posture/break_grant/break_clear/break_show）✓；`verify_workflow.py` L23916-23917「``--deactivate-block`` is the audited B-12 flag rollback (reason + authorized-by demanded)」逐字命中 ✓；L23913-23915 break-glass 五限定 + use 审计不可静默 ✓；L25869-25893 旗标面（--activate-block/--deactivate-block/--show-posture + --break-grant/--break-clear/--break-show）✓。
- **B-13**：`decision_repository.py` L131 `AUTHORITY_STATE_FILE = ".decision-store-state.json"` ✓；L36-42「A MISSING state file is the initial world: ``MD_ACTIVE`` epoch 0 — zero footprint for a host that never migrates」——「缺省 MD_ACTIVE epoch 0 = 零足迹（文件缺席即初始世界）」逐字背书 ✓；L150-157 `LEGAL_TRANSITIONS` 闭表含 `(ROLLBACK_FROZEN, MD_ACTIVE)`（rollback completes）——「回退是状态机一等公民非补丁」成立 ✓；`decision_migration.py` L1009-1048 argparse 11 子命令（freeze/shadow/verify/activate/rollback-begin/rollback-export/rollback-activate/cancel/status/project-repair/proof-pack）与 rollback-plan §7.2 清单**逐字一致** ✓；rollback-begin 带 `--owner-token`+`--reason` 必填 ✓。
- **「仅备份不算可回滚」红线承载**：version-plan §5 B-13 原文「回退 = 反向转换方案 + 切换前快照（**仅备份不算可回滚**——须覆盖迁移后新增行的反向转换）」逐字在案；rollback-plan §5 #5/§7.1/§7.2 + feature-flags §3 + checklist B-13 行四处置方式一致（rollback-export 全量反向导出含迁移后新增行 → rollback-activate）；DEC-238④ 原文段印证 DEC-237 条款 01（权威恢复协议——推荐从当前 JSON 全量导出）承重 ✓。
- **第一层（未激活）为本版实际交付态**：与代码缺省态一致（两文件缺席 = 零足迹）——表述无越权。

### ④ 四重点席完备性（checklist ①~④ vs §3 门禁口径）— **PASS**

- 四重点席与 version-plan §3b M-1R 行四席**逐一对应无漏席**：专席① Check 10 修复验证（FIX-348 白名单面——`verify_workflow.py` L14914-14959 实读：docs/release/** + docs/reviews/** 自 FIX-295/AUDIT-149 N6、docs/requirements/** 自 FIX-348 入 M5_RECORD_DOC_DIRS record-class 白名单，四件套落 docs/release/** 不触发 M5 反模式的机制背书成立）/ 专席② Check 16-17 披露（REQ-092×3 + EVD-1146 superseded 残留，均非豁免——EVD-1146/1147 双行在 evidence-log 实测在场）/ 专席③ Check 31 修复验证（R0 BLOCKED→R2 PASS 链；预算 361,923 本版零改动——`infra/checks/loop_runtime_claims.py` L225-242 实读命中 FIX-369 公式注释原文「ceil(301602 x 1.2) = ceil(361922.4) = 361923」「silent raises are forbidden」；M-0 期实测 305,604 + 余量 56,319 = 361,923 算术闭合）/ 专席④ archguard 棘轮席（6F 存量 regen 归 M-2 发布窗 sanctioned + R5 期望 97/97）。
- §3 五条口径承载面：条 1 全量 pytest 一次预算 → #11 ✓；条 2 组合测试四条 → #12 **逐字一致**（台账损坏×切换窗共存 / BLOCK 激活后迁移全走写入器 / 基线更新×投影失败恢复 / closure 取消期间 locks-release 与消费权并发）✓；条 3 独立证明包门 → #13 七要素逐字一致 ✓；条 4 既有面 → #1/#3/#4/#5/#8/#16 + 豁免账本零 stale（专席② historical 26=8+18——0.87 checklist L37/L98 实读对账基线一致）✓；条 5 REQ-092 → #1 + 专席② ✓。
- 0.87 基线抽验：injection budget 4,216/5,694/5,966（0.87 checklist L79 实读在场）——checklist #3 与 rollback-plan §4 #6 引用一致 ✓。

### ⑤ 回滚区间锚定（tag peel 复验 + 29 单轨）— **PASS**

- `git rev-parse 'v0.87.0^{}'` = `602f8f3f90b63eaae78ad5fc335ce622122e520b` **实测同一**（首次裸 `^{}` 转义伪差 `390934a` 已带引号复跑排除）；tag object `2e5f7151692bd3903c373dfccbdc88672f700b81` cat-file 实测 object 行 = `602f8f3f90...`（peel 同一）✓；taggerdate **2026-09-21 14:02:27 +0800** 实测精确一致（FIX-349 taggerdate 权威口径）✓。
- `602f8f3` 提交主题实测 =「REL-084 M-5: 0.87.0 transition candidate→released（manifest-only——DEC-226 预授权…）」与文档描述逐字一致 ✓。
- `git rev-list --count v0.87.0..HEAD` = **29**；`git describe --tags` = **v0.87.0-29-g3fb42c0** 双实测交叉印证 ✓。
- **单轨论证成立**：29 提交全部实测位于 `602f8f3` 之后（无 0.86.0 期树内搭车批的 DEC-222 双轨归属面）；`602f8f3..HEAD` 区间 = triage 锚定 = 完整行为回退区间 ✓；「区间计数不写死——M-5 现场以 `git rev-list --count 602f8f3..<发布 tip>` 取值」纪律正确（当前 HEAD `3fb42c0` 为窗口终点候选、M-1 bump 落库后延伸——如实注记非预填）✓。
- `fc69196` 前版收尾标注正确：窗口首位提交、REL-084 M-8 收口（commit message 实读含 EVD-1132/1133）✓；0.87.0 双轨先例教训注记（论证①）与 0.81.0 F-04 / 0.84.0 P-12 教训沿用注记在案。

### ⑥ feature-flags 面准确性 — **PASS**

- B-12 posture：文件名 `.write-guard-posture.json` / 六动作 / reason+authorized-by 必填 / 出厂全 WARN 缺省（代码实况——见③）逐项一致 ✓；`--activate-block` help 文本「the REAL flip moment is the Coordinator's decision」（verify_workflow.py L25890）与「真实翻转经授权票另行执行」表述一致 ✓。
- B-13 state：文件名 `.decision-store-state.json` / 缺省 MD_ACTIVE epoch 0 / 11 子命令 / 179 行演练字节回环（EVD-1155 在场——FEAT-061 交付记录）逐项一致 ✓；「当前必为 MD_ACTIVE」（`decision_migration.py status` 用户视角）与缺省态一致 ✓。
- B-14：无 flag 面也无需求论证（入口守卫即安全兜底、版本级回滚即消失）与 rollback-plan §1/§3 一致 ✓。
- **灰度开关正交性实测背书**：`LEGACY_REVERTS` 位于 `behavior_profile.py` L87；`ALLOWED_REVERT_CLASSES = {performance}`（review-FEAT-040-CODE-R0 L26 实证）；回退表 4 条全部 FEAT-034/034/036/038（performance 类）；守护测试注入式负例在场（test_behavior_profile.py L214-228 `revert_contract_issues()` 机检）——「B-12/B-13/B-14 均不在 LEGACY_REVERTS 白名单」「无 legacy=关执法/回退权威中间态」主张成立 ✓。

### ⑦ 边缘披露核验 — **PASS（一处定性收紧——见 P2-1）**

- **EVD-1139**：evidence-log 实测 L1139 =「FIX-374 完成必推荐分析快照（M7.4 step 6…）task-priority-analysis 输出——25 任务 25 完成…」·类型「治理记录」——**归属明确为 FIX-374**，非「归属未明」。真正的缺陷是 release-plan L42 FIX-374 行证据列仅列 EVD-1138（漏列 1139），CHANGELOG 0.88.0 段逐票行同源同样未列；release-plan L67「**30 EVD（EVD-1134~1163）**」区间计数声明本身正确（实测 30 条全在场）。→ P2-1。
- **「五前置」两源分解**：decision-log 实测 DEC-238④ 原文「④真实切换授权前置三条件（RISK-059 承载）：archive.py DEC 归档路由改造方案+verify_workflow freshness 接线方案+11 处勘误行源文件处置——三条件闭环+证明包审查后授权切换票」；DEC-239⑦ 原文「⑦M-2 前置：archguard R1 锚处置（regen 或 shrink）+ F-5①③ 组合测试（**归切换授权票**：台账损坏×切换窗共存/基线更新×投影失败恢复）」——feature-flags §3「3+2 合计五项前置」取舍正确（archguard R1 锚处置属 M-2 前置、未被计入切换票五前置，与原文括注「归切换授权票」仅限 F-5①③ 一致）✓；RISK-059 在 risk-log 在场 ✓。
- **fc69196 前版收尾标注**：窗口首位 + 属 0.87.0 收尾——git 实测正确，29 计数含它、24 票不含它的边界表述无歧义 ✓。
- **CHANGELOG 双位过渡态注记**：根 `changelog.md` 在 M-1 在途变更面（`git status --porcelain -- changelog.md` 确认 untracked/modified 态）——checklist 披露⑥「工作树 untracked 态如实注记」与实况一致 ✓；`project/CHANGELOG.md` 0.88.0 段在场（L5 起，双位同段——canonical 归属留 M-3 裁决如实标注）✓。

### ⑧ cross-refs/验证复现（四连复跑）— **PASS**

| 复跑项 | 实测结果 | 申报/期望 | 判定 |
|---|---|---|---|
| `check-cross-references` | 78 files scanned / **727 references** / 0 dangling / 0 deprecated / 0 circular | PASS 727 引用 | ✓ 逐位一致 |
| `check-manifest-consistency` | PASS——canonical **891** / actual **1023** | PASS 891/1023 | ✓ 逐位一致 |
| `check-version-consistency` | **PASSED** + 1 WARN（plan-tracker workflow version=0.87.0, expected=0.88.0） | PASSED（1 WARN 预期） | ✓ 一致（checklist #2 期望口径同） |
| `release-projection` | **PASS** / source_version=**0.88.0** / projections_checked=**28** / issues=[] | PASS 28 面 | ✓ 逐位一致 |

- **manifest 缺席性实测**：`skills/software-project-governance/core/releases/0.88.0.json` 不存在（披露①「candidate manifest 缺席——本票锁面外」证实）；0.87.0.json 在场且 `lifecycle_state: released`（先例形态对照——release_docs 四件套 + 单 transition 事件）✓。无 0.88.x tag（`git tag --list '*0.88*'` = 0 条——「无 0.88.x tag/预留冲突」证实）✓。

---

## 二、五维度逐项结论

| 维度 | 结论 | 依据摘要 |
|---|---|---|
| 1 正确性 | **PASS** | 载荷 29 提交逐票命中、区间锚定三重实测同一、命令面 17 个 CLI 面/子命令实读在场、M 链映射与 §3b/先例无矛盾（发现仅 P2-1 列示遗漏，不影响行为载荷事实） |
| 2 安全性 | **PASS** | no-overclaim 五 token + 激活态不越权主张全在且为否定形态；break-glass 不可静默/guard 自指适用红线承载；M-2 数值不预填纪律（门禁表全回填位）；RISK 关闭声明显式排除；reset/破坏性命令确认面标注（rollback-plan §2.3 P-9 同口径） |
| 3 可维护性 | **PASS** | 同源引用可追溯（CHANGELOG/version-plan/DEC/RISK/EVD 五源逐一对上）、0.87.0 先例结构逐节同形、披露①~⑨均可执行承载；P2-1 一处列示遗漏为唯一缺口 |
| 4 性能（适配：验证成本与可复现性） | **PASS** | 本审查全部结论可复现（git/命令面/四连复跑命令在本报告均可重放）；M-2 执行序纪律（安静窗→顺序→逐 FAIL 落披露）明确 |
| 5 测试覆盖（适配：门禁覆盖完备性） | **PASS** | §3 五条口径在 #1~#19 全有承载席；组合测试四条/证明包门七要素逐字；四重点席齐备；M-2 执行序含混沌复演/e2e/全量 pytest 一次预算/Check 28s |

## 三、AI 专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock/占位符纪律（占位未虚构） | **PASS** | `<发布 tip>` 占位 4 处均标注「M-5 生成后回填、不预编造」；M-2 门禁数值全部 ⏳ 回填位；未生成事实（tag/transition/翻转/切换）一律期义务 |
| 2 | 硬编码未溯源值 | **PASS** | 抽查数值 29/28/727/891/1023/361,923/305,604/56,319/4,216-5,694-5,966/26=8+18/602f8f3/2e5f715/taggerdate 全部实测溯源命中；文档引用行号（L23908-23917/L301/L131/L151-163/L1009-1048/L14914-14957/L225-242 等）逐段实读无偏差 |
| 3 | 幻觉 API/命令调用 | **PASS** | governance-write-guard 六旗标、decision_migration 11 子命令、--reason/--authorized-by/--owner-token 参数面全部实读在场，无虚构命令 |
| 4 | 未实现伪装已实现 | **PASS** | M-2/M-3/M-4~M-8 期义务、回滚演练未排程、manifest 缺席、plan-tracker 过渡态 WARN 全部如实标注，无「写成通过」面 |
| 5 | 过度实现/越权主张 | **PASS** | 保守边界声明（激活态不越权/隔离验收≠真实环境/RISK-036 打开）与代码缺省态、RISK 实况一致；无超版本能力主张 |

## 四、发现清单

### P2-1 · EVD-1139 逐票列示遗漏 + 勘误义务未落承载面（不阻塞——已披露留勘误）

- **位置**: `docs/release/release-plan-0.88.0.md` L42（FIX-374 行证据列仅「EVD-1138」）；L67（治理面行「30 EVD（EVD-1134~1163）」计数正确）；对照 `docs/release/release-checklist-0.88.0.md`（通篇无 EVD-1139 字样）与 `project/CHANGELOG.md` 0.88.0 段逐票行（FIX-374 行同源未列 1139）。
- **事实**: `.governance/evidence-log.md` 实测 EVD-1139 =「FIX-374 完成必推荐分析快照（治理记录）」——**归属明确**。Developer 边缘申报「归属未明（changelog 声明 30 EVD 但逐票 29 编号）」的定性可由实测收紧为：**归属明确（FIX-374），逐票表列示遗漏**——「30 EVD」区间声明（1134~1163）与逐票表 29 个编号之间的差即 1139。
- **影响**: 文档内部不自洽（30 声明 vs 逐票 29 编号）需 M-3 复核者自行考古；且「留 M-2/M-3 勘误」的申报目前仅存在于 Developer 返回面，四件套与 checklist M-2/M-3 义务行（仅列 EVD-1146/披露②⑥）均未承载该勘误义务——M-2/M-3 执行工位从文档上不可见。不影响发布决策（1139 为完成必推荐分析快照记录，非载荷缺陷；窗口计数/区间锚定/manifest 缺席等关键事实不受影响）。
- **建议**: (a) release-plan L42 FIX-374 行证据列补「EVD-1138/1139」（或 L67 治理面行加一句「EVD-1139 为 FIX-374 完成必推荐分析快照——逐票表未单列」注记）；(b) 将「EVD-1139 勘误核对」显式列入 checklist M-2/M-3 复核义务（与 EVD-1146 并列）。可随 M-2 勘误批或 M-3 审查修复，不阻塞 M-1R 交付。

### P3-1 · CHANGELOG B-12 回退通道措辞歧义（纯表述层——已被 §7.2 消解）

- **位置**: `project/CHANGELOG.md` 0.88.0 段行为变更节 B-12 行「回退 = 族级 flag 回 WARN（数据级）经 break-glass 通道」。
- **事实**: 该措辞与 version-plan §3b 原文逐字一致，非四件套新增偏差；但权威代码注释（verify_workflow.py L23916-23917）把 `--deactivate-block` 定为 the audited B-12 flag rollback，break-glass（--break-grant）为临时恢复窗（不改姿态文件）；rollback-plan §7.2「两通道互补：日常回退走 deactivate，紧急止损走 break-grant」已作操作化消解。按最窄读法「经 break-glass 通道」可被误读为回 WARN 须走 break-glass。
- **建议**: 无需修改四件套（M-3 发布半面审查 CHANGELOG 时可选澄清一句）。不要求修改。

### P3-2 · checklist 专席③ provenance 路径为 infra 相对缩写（无需修改）

- **位置**: `docs/release/release-checklist-0.88.0.md` 专席③「provenance `checks/loop_runtime_claims.py` L225-242」。
- **事实**: 实际路径 = `skills/software-project-governance/infra/checks/loop_runtime_claims.py`；L225-242 实读精确命中 FIX-369 公式注释；`checks/` 为 infra 基座相对缩写（仓内文档惯例），行号引用准确。仅作记录，不要求修改。

## 五、硬门槛裁决

| 门槛项 | 阈值 | 判定 |
|---|---|---|
| P0 阻塞问题数 | = 0 | **PASS**（P0 = 0） |
| 5 维度全覆盖 | = 100% | **PASS**（五维度逐一有结论，见 §二） |
| 每条发现标注级别 | = 100% | **PASS**（P2-1/P3-1/P3-2 全标注） |
| 设计一致性检查 | 已完成 | **PASS**（与 version-plan §3/§3b/§5、DEC-238④/DEC-239⑦/DEC-227 路线、FIX-349/F-5/F-6/F-11/F-13 口径逐一对表，见 §一） |
| AI 专项 5 项检查 | 全部完成 | **PASS**（5 项逐一有结论，见 §三） |
| 只读约束 | 被审文档与 .governance/ 只读 | **PASS**（唯一写入面 = 本报告；四件套/产品代码/治理数据零修改；实测全部为只读命令） |

## 六、证据清单（本审查实测命令/文件）

- git：`git rev-parse 'v0.87.0^{}'`（=602f8f3f90b6…）、`git cat-file -p 2e5f715`（object 行=602f8f3f90b6…）、`git for-each-ref refs/tags/v0.87.0`（2026-09-21 14:02:27 +0800）、`git rev-list --count v0.87.0..HEAD`（29）、`git describe --tags`（v0.87.0-29-g3fb42c0）、`git log --oneline --reverse v0.87.0..HEAD`（29 行逐票对照）、`git tag --list '*0.88*'`（0 条）、`git status --porcelain -- changelog.md`（在途变更面）。
- 代码实读：`write_guard_state.py` L294-311/L1662-1701；`decision_repository.py` L36-53/L126-165；`decision_migration.py` L1004-1051；`verify_workflow.py` L23900-23924/L25864-25895/L14914-14959；`behavior_profile.py` LEGACY_REVERTS（grep 定位 L87 + 守护测试 test_behavior_profile.py）；`infra/checks/loop_runtime_claims.py` L225-242。
- 治理数据实读（UTF-8）：`.governance/evidence-log.md`（EVD-1132~1163 全量 30 条）、`.governance/decision-log.md`（DEC-238④/DEC-239①②⑦ 原文段）、`.governance/risk-log.md`（RISK-059 行）。
- 四连复跑：`check-cross-references`（78/727/0-0-0）、`check-manifest-consistency`（891/1023）、`check-version-consistency`（PASSED+1 WARN）、`release-projection`（PASS/0.88.0/28/[]）。
- 文档对照：`docs/planning/version-plan-0.88.0.md`（§1/§3/§3b/§4/§5/§7 全文）、`project/CHANGELOG.md` 0.88.0 段（L5~L100 关键行）、`docs/release/*-0.87.0.md` 先例（M 链行/checklist 基线/四件套在场性）、`skills/software-project-governance/core/releases/0.87.0.json`（released 先例形态）与 `0.88.0.json`（不存在）、`docs/reviews/review-FEAT-061-CODE-R1.md`（终态抽样）。

---
*REL-088 CODE-R0 审查冻结（2026-09-25，Code Reviewer Agent）。本报告全部结论以实测为据——无实测支撑处均注明；APPROVED_WITH_NOTES 仅表示硬门槛通过，不替代 M-2 门禁实测与 M-3 发布半面审查。*
