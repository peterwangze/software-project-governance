# REL-094 M-4④ 发布文档批 R0 审查报告（M-4 DOCS）

- **审查对象**：`docs/release/{release-plan,rollback-plan,feature-flags,release-checklist}-0.91.0.md`（git status 4 新增 untracked；纯文档批，零代码变更）
- **审查基准**：任务书 REL-094 M-4④ 五项聚焦清单 × release-review SKILL × agents/release-reviewer.md；M-3 双半面报告（`review-REL-094-M3-CODE-R0.md` AWN/0、`review-REL-094-M3-RELEASE-R0.md` AWN/0 ub=0）为引用基准
- **审查人**：Release Reviewer Agent（独立链）· **Round**：R0 · **日期**：2026-09-28（+0800）
- **角色约束履行**：未修改任何产品文件与 `.governance/**`；无用户交互；唯一产出 = 本报告（全部验证命令只读：git log/rev-parse/rev-list/describe/for-each-ref/show --stat、三份治理文件 grep 实读〔UTF-8〕、ledger.py 机制实读、四件与 0.90 先例对照）

---

## 结论速览

| 项 | 结论 |
|---|---|
| **Verdict** | **APPROVED_WITH_NOTES**（unresolved_blockers=0，无 BLOCKING finding） |
| **unresolved_blockers** | **0** |
| P0 / P1 / P2 | 0 / 0 / 0 |
| P3（非阻塞备注） | 4 项 |
| 五项聚焦清单 | ①事实锚零幻影 ②发布态纪律达标 ③放行条件映射完整 ④回滚序列与机制相符 ⑤零新增旗标声明成立 |

---

## 项 1 —— 事实锚抽验（任务要求 ≥15 处，实抽 24 处）→ **PASS（零幻影）**

**机械比对**：对四件全文提取全部 7 位十六进制串，与 git 实况哈希集合 `{196894a, 9bafdf6, bc3f052, 98104cb, 3f87459, d2b2a6d, 8d25101}` 比对——四件中出现的哈希 **100% ∈ 实况集合，零未知串**。

| # | 抽验点 | 文档声称 | 实况（亲跑命令） | 判定 |
|---|---|---|---|---|
| 1 | `196894a` FEAT-072 | 2026-09-27 23:43 | `git show -s`：23:43:05 +0800，message 含「M7.4 6b/6c 重写…+76B」 | ✓ |
| 2 | `9bafdf6` FIX-399 | 2026-09-28 00:50 | 00:50:28 +0800，message 含「6 测试用例…−1 误报零新增」 | ✓ |
| 3 | `bc3f052` M-1 | 2026-09-28 01:42 | 01:42:35 +0800，message 含「再生 17 面…28b 消解」 | ✓ |
| 4 | `98104cb` M-1R | 2026-09-28 02:32 | 02:32:13 +0800，message 含「archguard 重锚 26385」 | ✓ |
| 5 | `3f87459` = v0.90.0 peel | 「`git rev-parse v0.90.0^{}` 实测」 | 亲跑同命令 = `3f87459196…`；该提交 = REL-093 M-5b transition（2026-09-27 22:06:31） | ✓ |
| 6 | tag object `d2b2a6d` | taggerdate 2026-09-27 22:07:49 +0800 | `git for-each-ref refs/tags/v0.90.0` = `d2b2a6dc… tag 2026-09-27 22:07:49 +0800` | ✓ |
| 7 | 窗口计数 = 5 | 「rev-list 与 describe 双实测」 | `rev-list --count 3f87459..HEAD`=5；`git describe`=v0.90.0-5-g98104cb | ✓ |
| 8 | 区间 5 提交清单 | `8d25101→196894a→9bafdf6→bc3f052→98104cb` | `git log v0.90.0..HEAD` 逐一吻合（8d25101=REL-093 M-8 22:40:28） | ✓ |
| 9 | EVD-1204~1210 | 七行机录在案 | evidence-log 实读七行全在场；**EVD-1206 重复残留行已如实标注**（与 release-plan L41 披露一致） | ✓ |
| 10 | EVD-1210 双源数值 | pwsh-170 1364.03s + pwsh-171 1394.55s，均 4359P/0F/1S/527 | EVD-1210 行逐字吻合 | ✓ |
| 11 | REVIEW 六份 | 盘上路径六处 | glob 实存六份：`review-FEAT-072-DESIGN-R0` / `review-FIX-399-CODE-R0` / `review-REL-094-M1-R0` / `review-REL-094-M1R-R0` / `review-REL-094-M3-CODE-R0` / `review-REL-094-M3-RELEASE-R0` | ✓ |
| 12 | R2/R3 机录行 | 「evidence-log L2868/L2870」 | 实读 L2868=REVIEW-REL-094-R2（CodeReviewer）、L2870=REVIEW-REL-094-R3（ReleaseReviewe…）——**行号精确** | ✓ |
| 13 | DEC-265~268 | 授权链/契约裁决/载荷冻结/收口四则 | decision-log 实读四行全在场，逐项语义对应（见项 3 细目） | ✓ |
| 14 | 双源时长/计数 | 1364.03s + 1394.55s / 4359P/0F/1S/527 | M-3 RELEASE 亲跑#8（1394.55s 同值）+ EVD-1210；M-3 CODE §0 注（4359P/0F/1S/527=pwsh-170 已录） | ✓ |
| 15 | 预算三档 | 4241 / 5719 / 5991（strict 余量 9） | M-3 RELEASE 亲跑#6 同值三方复证 + DEC-268(2) 基线 + plan-tracker L80 | ✓ |
| 16 | 28s 时点 | M-1 1,737,424B → M-3 审查时点 1,744,908B | M-3 RELEASE 亲跑#7（1,744,908B）+ M-3 CODE 亲跑输出（1744908 bytes）逐字节吻合 | ✓ |
| 17 | archguard 重锚 | 26358→26385（+27）；R4 census 1318 不变 | EVD-1209 行 + `98104cb` message（26385）+ M-3 CODE §6（1318） | ✓ |
| 18 | FEAT-072 载荷构成 | 6 文件、persona +76B、四注入面 | `git show --stat 196894a` = 恰 6 files（含 behavior-protocol/references、SKILL.md、persona、interaction-boundary、verify_workflow.py、test_dsh_adapter.py +74） | ✓ |
| 19 | FIX-399 载荷构成 | 2 文件、test +76 行、恰 6 用例 | `git show --stat 9bafdf6` = 恰 2 files（test_verify_workflow.py +76、verify_workflow.py 23±） | ✓ |
| 20 | `FIX_105_SNAPSHOT_RELEASE_VERSION_RE` | 容忍装饰尾巴正则 | verify_workflow.py L1924 实存，捕获组 `(?:\d{4}-\d{2}-\d{2})[^*]*` 与声明一致 | ✓ |
| 21 | M0 重钉区间 | [512,556]→[522,566]（behavior-protocol）、[223,230]→[225,232]（SKILL.md），prior 逐字节存档 | EVD-1209 + M-3 CODE §1.2（rebaseline.last 溯源块实读）同值 | ✓ |
| 22 | FEAT-073 五要素 | plan-tracker L80 已登记 | **L80 恰为 FEAT-073 行**，五要素逐项与 DEC-268(2) 原文一致 | ✓ |
| 23 |联合回归 54+20 OK | DEC-267(1) 冻结锚 | DEC-267 行原文「合并态联合回归证据（54+20 OK/contract+budget PASS@HEAD）」 | ✓（未复跑，M-3 同口径归属声明） |
| 24 | 全库无 B-15 | 「发布态铸造」 | checklist ⑥ 与 M-3 RELEASE P3-2 口径一致（命名词，M-5 落段） | ✓ |

---

## 项 2 —— 发布态纪律 → **PASS**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 无「已发布」声明 | ✓ | 四件正则扫描（`已发布|v0.91.0 已|已打 tag|发布日期：2026-10`）全 clean；「released 态（M-7 tag 后）=」为回滚程序条件描述、checklist「released 验证」为 M-8 计划项，均非完成态声明 |
| 发布日期零预填 | ✓ | 四件日期字段均为起草日 2026-09-28；0.91.0 发布日无字面量；release-plan L16 明文「发布日期不预填——taggerdate 权威（M-7 后回填）」 |
| taggerdate 权威语句在场 | ✓ | release-plan L16/L70、rollback-plan L9、checklist 放行条件⑥⑧四处均载「FIX-349 口径：taggerdate 权威」 |
| rollback tip 零预填 | ✓ | rollback-plan L10-12 占位注释在场（`<!-- 发布 tip 哈希占位：M-5 transition 提交生成后回填（0.81.0 先例 F-04…） -->`）；release-plan 同锚同口径（L15/L73） |
| M-5~M-8 数值不预填 | ✓ | release-plan L17 保守边界明文「只列义务不写通过性数值」；checklist 门禁表 #8 release-ledger 标 `NOT_RUN`（M-5 义务）——与 DEC-267(4)「不提前伪造完成态」一致 |

---

## 项 3 —— 放行条件映射完整性 → **PASS**

**checklist「M-5~M-8 待办」⑥项 与 M-3 RELEASE 报告项 5 条件 5~10 逐项对应**：

| checklist 条件 | M-3 条件 | 内容对应 | 义务锚齐备性 |
|---|---|---|---|
| ⑤（M-5） | 5 | `core/releases/0.91.0.json` 创建（**N-4** 义务；NFC/sorted/compact 同 0.90 形态）+ lifecycle candidate→transition（单父=候选 commit，tip 现场取值）+ check-release candidate 态 | ✓ |
| ⑥（M-5） | 6 | CHANGELOG 发布态改写双位同步：日期=**taggerdate 权威**+ **B-15 行为变更段**（承接 B-1~B-14；含回滚说明/零迁移/零 flag 面/stdlib-only）+ **N-1**（DEC-267(2) 第二从句「计量或生成内容变化也可能越界」逐字补入）+ 已知边界四条重测落字 + 终账补记 + **N-2**（「HEAD 即此 commit」时点改写） | ✓ |
| ⑦（M-6） | 7 | release-ledger 本地+remote 双 PASS（NATIVE_RELEASED；UNKNOWN/BLOCKED 不得包装 PASS） | ✓ |
| ⑧（M-7） | 8 | annotated tag `v0.91.0`+push（peel 机制；tag_facts 双端核对）+ taggerdate 权威回填 | ✓ |
| ⑨（M-8） | 9 | 归档迁移（扩展至 v0.90.0）+ integrity PASS + 版本收口（0.90.0→0.91.0 消解 WARN 24）+ released 验证 + snapshot 三要素投影首用 | ✓ |
| ⑩（M-8） | 10 | census/身份集维持至 tag（零新增未授权阻断红线）+ loop_runtime 内部登记 + 终版复跑 FAIL 须归因重评禁静默豁免 | ✓ |

**M-3 前置条件 1~4（M-4 门）履行核验**：条件1 P2-1 补账 = EVD-1210 已机录（亲证在场，DEC-268(3)）✓；条件2 P2-2 = plan-tracker L80 五要素已登记（亲证，DEC-268(2)）✓；条件3 风险窗复评 = DEC-268(1) 六风险（036/039/047/048/050/059）逐条在场，与 release-plan「风险窗」表逐行同语义 ✓；条件4 docs/release 三件套 = 本批四件套 ✓。

**已知边界四条一致性**：release-plan L111-116 / checklist L53-58 与 M-3 义务 d 四点（28s 现值/strict 复测/P2-1 候选池/再生纪律）同构；FEAT-073 引用（计量器/范围/基线 4241/5719/5991/责任人/验收）与 DEC-267(2)(a)+DEC-268(2)+plan-tracker L80 三方逐项一致；「0.92 治理票已登记」声明现已有登记实体承托（P2-2 已消解）。

---

## 项 4 —— 回滚序列正确性 → **PASS**

1. **Step 1 revert 序列**：`git revert 98104cb bc3f052 9bafdf6 196894a`（新→旧，与窗口落库顺序相反=正确）；`8d25101` 按需取舍并留痕（非 0.91 行为载荷，归类正确）。「同文件多票禁选择性还原」声明与 M-3 CODE §1.1 亲证一致——verify_workflow.py 三段 hunk 各归其票（锚 dict→FEAT-072 / 28c 正则区→FIX-399 / 版本字面量→M-1），选择性还原必产生半回退混合态。
2. **Step 2 投影再生**：`release-projection --write` + `check-projection-sync`（期望 28/28）+ `check-version-consistency`——与 M-1/EVD-1208 幂等再生实测（17→0→0→0）机制一致，期望值正确。
3. **Step 3 manifest lifecycle**：**亲证 `skills/software-project-governance/infra/release/ledger.py` L240 `derive_effective_state`**——`candidate_to_released`→released、`withdrawal` 事件→`withdrawn=True`，与 rollback-plan Step 3 语义逐字相符；candidate 态回退 = manifest 随候选提交一并消失（manifest 为 repo 内文件，无独立清理面——正确）。
4. **区间锚定**：`3f87459..<发布 tip>`、F-04 教训（终点不得为候选打包提交）、窗口计数现场取值——三件（release-plan/rollback-plan/checklist）同锚同源无漂移。

---

## 项 5 —— feature-flags 零新增声明 → **PASS**

- 「窗口 diff CLI 面 `add_argument`/`def cmd_`/`sys.argv` 变更行 = 0」与 **M-3 CODE §5.1 亲证原文一致**；「无接口删除、无文件格式破坏」同（§5.1）。
- FEAT-072 归类「契约呈现面非 flag 面」与 M-3 CODE §5.2（RECO 行机器写入格式未变、无 schema 断言依赖旧文案、无机器消费方解析推荐卡正文）一致；rollback-plan 回滚影响①引用同源。
- 旗标表对照 0.90.0 先例：RB-2（`RB2_SENSITIVE_BLOCK_ENFORCED` @ `infra/checks/evidence_domain.py`，False）/ B-12 / B-13 三者**姿态、位置、翻转条件（独立授权票+RISK-059 前置）沿用** ✓；B-12/B-13「本版不翻转」与 DEC-268(1) 不翻转确认（窗口守卫 token 零命中）一致。`GOVERNANCE_LEGACY_BEHAVIOR` 行为 0.84.0 既有运维开关的新增披露行（标注「本版零改动」），非新增旗标（见 P3-2）。

---

## Findings（P0-P3）

**P0（BLOCKING）：无。P1（BLOCKING）：无。P2：无。**

**P3（非阻塞备注，4 项——均无需在本批返工）**：

- **P3-1**（路径写法）：rollback-plan Step 3 写「`infra/release/ledger.py`」，省略 skill 根前缀（全路径 `skills/software-project-governance/infra/release/ledger.py`）。仓库根下无同名文件、文档惯例以 skill 根为基准可解析、函数与语义引用准确——建议后续版本统一完整路径或标注基准根。
- **P3-2**（旗标表披露差异）：feature-flags 0.91 比 0.90 旗标表多披露 `GOVERNANCE_LEGACY_BEHAVIOR` 行（0.84.0 交付的既有运维开关，0.90 文档未列）——已标注「本版零改动」，无误导；仅提示与 0.90 逐行对比的读者：该差异为披露完整度而非旗标新增。RB-2 翻转条件省略 0.90 版「翻转 checklist（N-1/N-5）」细目，前置（RISK-059 关闭）保留，语义未失真。
- **P3-3**（转述措辞）：release-plan/checklist strict 披露行转述「净增超 9 tok 即越界」，DEC-267(2) 原文为「净增超过 9 tok 即越界」——一字之差；两件均已标注「发布态逐字补入（N-1）」义务，转述处不构成失实。M-5 改写 CHANGELOG 时按 DEC-267(2) 原文落字（义务已在放行条件⑥承载）。
- **P3-4**（28s 走势披露简化）：已知边界②只列两档时点（M-1 1,737,424B → M-3 1,744,908B），省略 M-1R 中间值 1,741,479B（M-3 RELEASE P3-3 三档全列）——两件均已标时点且声明「点位随发布链自增」，非失实；发布态重测落字义务已承载，无需回改。

（跨文档一致性观察：M-3 RELEASE 报告条件 6 写「回滚说明 git revert 单提交」系 0.90 句式惯性；本批 rollback-plan/checklist 按 0.91 实际 4-commit revert 序列表述，**更精确**——报告不在本审查对象内，仅记录差异，不要求修改。）

---

## 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）——M-4④ 发布文档批通过，可随批提交。**

五项聚焦清单全部完成：①24 处事实锚抽验零幻影（哈希机械比对 100% ∈ git 实况集合；EVD/DEC/REVIEW/plan-tracker 行号级实存）②发布态纪律达标（无「已发布」声明、日期零预填、taggerdate 权威语句在场、rollback tip 占位注释在场、M-5~M-8 数值不预填）③放行条件⑤~⑩与 M-3 条件 5~10 逐项对应，N-1/N-2/N-4/B-15/taggerdate 回填全部在位，M-3 前置条件 1~4 已履行 ④回滚三步序列与 git 实况及 ledger.py `derive_effective_state` 机制相符（withdrawal→withdrawn=True 亲证）⑤零新增旗标声明与 M-3 CODE CLI 零变更结论一致，既有旗标沿用 0.90 态。P3×4 均为记录性备注，不产生发布链新义务（P3-3 义务已在放行条件⑥既有承载）。本审查未修改产品文件与 `.governance/**`；本报告 review-record 机录由 Coordinator 执行。

---
*REL-094 M-4④ R0（Release Reviewer Agent，2026-09-28）。抽验命令基线：`git rev-parse v0.90.0^{}` / `git for-each-ref refs/tags/v0.90.0` / `git rev-list --count 3f87459..HEAD` / `git describe --tags` / `git log v0.90.0..HEAD` / `git show -s|--stat ×6` / 四件全文哈希正则提取比对 / evidence-log·decision-log·plan-tracker UTF-8 实读（L2868/L2870/L80 行号核）/ `ledger.py` L240-256 实读 / `verify_workflow.py` L1924 实读 / feature-flags 0.90↔0.91 对照 / M-3 双报告全文对照。*
