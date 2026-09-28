# REVIEW-REL-095-CODE-R0 — 0.92.0 发布链 M-3 CODE 半面审查（功能载荷终审·聚合面）

- **Round**: R0（CODE 半面首审；机录轮位 round=2——round 0/1 已被 M1-R0/B2-R1 占用）
- **Reviewer**: Code Reviewer（agents/code-reviewer.md + skills/code-review/SKILL.md 已加载；P0~P3 分级）
- **审查对象**: 0.92.0 功能载荷终审（六票已各自独立审查闭合——本审=发布前聚合终审，聚焦跨票聚合面与发布态一致性，不重复逐票深审）
- **审查基线**: HEAD=df26f7e（载荷范围 e65b317^..df26f7e 共 12 提交：8 载荷申报提交 + b6575bd FEAT-074 输入锚 + 3 发布链提交）；工作树干净（git status 零输出亲证）
- **审查日期**: 2026-09-29｜**任务**: REL-095（M-3 CODE 半面）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）** — P0=0 / P1=0 / P2×2 / P3×5

## 一、审查重点逐项结论

### 重点 1：跨票一致性（六票接口/数据流冲突扫描 + diff 总面对账）— PASS

**diff 总面对账**：`git diff e65b317^..df26f7e --stat` = 51 files, +5333/−216。逐提交 numstat 归因（12 提交）后并集恰 51 文件，全部可归因到六票申报面或发布链三提交——**无未申报夹带**。共享文件跨票演进无冲突：verify_workflow.py（FIX-400 超时面 + FEAT-075 例外面 + M-1 版本字面量）、archive.py（FEAT-074→075 两段累计 +389/+566 行）、architecture-baseline.json（FIX-400 regen 26385→26413 → FEAT-075 regen 26413→26478，两段分离提交符合 DEC-260 纪律）、test_verify_workflow.py / test_loop_runtime_claims.py（四票+B2 各自增补）。注记 CR-F6：b6575bd（FEAT-074 设计准入盘点文档，单文件纯文档提交）不在任务简列 8 提交内，但 plan-tracker FEAT-074 行已显式申报（设计准入输入=盘点文档）——属申报面内。

**版本/锚/digest 链条互恰**（五链端到端复证）：
1. **版本链**：SKILL.md frontmatter 0.92.0 权威源 → check-version-consistency PASSED（13 文件+bootstrap markers，exit 0）——FEAT-073 注入面（AGENTS/模板/persona）与 M-1 版本面（24 文件）投影一致。
2. **archguard R1 锚链**：f06a2bf 26385→26413 → 484dd77 26413→26478 → M-1 版本面零逻辑变更 → B2 不触主文件；实跑 `[R1] PASS mainfile loc 26478 ≤ anchor 26478`——**版本面+豁免锚块未触锚**（B2 的 +6/−2 在 infra/checks/loop_runtime_claims.py，非主文件）；R7 regen deterministic=True committed==fresh True。
3. **B2 豁免 digest 链**：LRC 实跑无 EXEMPTIONS_CONTRACT_DIGEST_DRIFT/SET_DRIFT，exemptions_applied 5/5（含新条目 LRC-EXEMPT-FIX401R0-79-1 五元组 UNSUPPORTED_AFFIRMATIVE|product_root|docs/reviews/review-FIX-401-R0.md|accounting:79:1|LRC-ACTIVE-RUNTIME 逐键吻合）——锚-账本-加载器三方一致（B2-R1 独立重算 d47f5d16 复证在案）。
4. **FEAT-074 分类器 ↔ FEAT-075 dry-run**：scan-families 实跑（窗口 [0.1.0,0.92.0]）四族分类语义单源工作正常（EVD 477 行/REVIEW 640/RECO 159/TRIAGE 199，五态子分解完整：missing_task_ref/no_task_family_ref/task_version_unparseable/active_task_ref/explicit_keep_marker/duplicate/unknown_shape）；test_archive.py 170P+6 subtests 绿——两票共享 archive.py 零接口冲突。
5. **FEAT-075 例外机制 ↔ FIX-402 台账 ↔ B2 豁免账本 ↔ EXC-001/002**：EXC-001 例外由 FEAT-05 registry 面承载且 live 生效（见重点 3）；EXC-002 基线 178 行**精确复现**（scan-families [0.1.0,0.90.0] 窗口 EVD 族 would_archive=178——与 EVD-1233/1235 及 12bef7c 基线附件口径逐数吻合）；FIX-402 留热 11 行口径与 dry-run `active_task_ref: 11 rows` 吻合。

**先例审查链核验**：六票终态逐报告复核——FEAT-073-R0 AWN/0→R1 AWN/0、FIX-400-R0 AWN/0、FIX-401-R0 AWN/0、FEAT-074-R0 NC→R1 AWN/0、FEAT-075-R0 NC→R1 AWN/0、FIX-402-R0/R1 NC→R2 AWN/0、REL-095-M1-R0 AWN/0、REL-095-B2-R1 AWN/0——全链闭合，与任务申报一致；8 载荷提交 hash 逐一在 git log 亲证存在且 subject 对应。

### 重点 2：发布态验证复跑（只读）— 全 PASS

| 检查 | 结果 | 事实 |
|---|---|---|
| verify 聚合 | **PASSED exit 0** | 全量资产/锚点/投影面绿（review 报告双件、manifest 973→976 与 +3 新文件精确对应） |
| archguard fatal gate | **PASS 0 violations** | R1~R5/R7 全 PASS（R6 advisory 205 模块 Δ0）——26478 锚未触 |
| check-version-consistency | **PASSED exit 0** | 13 文件+bootstrap markers 全 0.92.0 |
| check-manifest-consistency | **PASS exit 0** | 976 canonical/1128 actual；与 M1-R0 时点 973/1125 差恰=12bef7c+df26f7e 新增 3 文件 |

### 重点 3：B2 豁免发布面 — PASS

- **LRC 实跑**（check-loop-runtime-claims --product-root . --project-root .）：verdict=**PASS** / findings=**0** / exemptions_count=**5**，5 条全部出现在 exemptions_applied 披露面（4 旧条目+新条目逐键核对）——与 DEC-283(4)「按既有契约 PASS 并披露豁免」一致。
- **EXC-001 两层同屏**（check-governance-data-size + check-governance Check 28s 双面）：`evidence-log.md 1755371 bytes … exceeds error_bytes=250000 — exception accepted (EXC-001, ref=DEC-282 (M-0 freeze approval; DEC-278 precedent), expires=2026-10-12)`——原始超标层+例外接受层**同行同屏**，两命令面形态一致；1,755,371B ≤ 上限 2,036,197B（基线 1,786,197+250K 口径）。数值与 EVD-1235 时点 1,753,848B 差 +1,523B=EVD-1235 行自身+机录行追加（见 CR-F7），非漂移。
- **dry-run 零写入红线**（负向探针）：`--output .governance/probe-tsv.txt` → `Scan REFUSED: family_scan_output_refused … dry-run 零写入`，exit 1，Test-Path=False——写拒绝为**代码级强制**（非操作员约定），红线兑现。

### 重点 4：回归面 — PASS

- **test_loop_runtime_claims.py 全量**：**64 passed + 81 subtests passed** in 258.96s（exit 0）——与预期 64P+81 subtests **逐数吻合**，已提交态稳定绿（B2 预期红自愈闭环复证）。
- **test_verify_workflow.py --lf**：1 passed / 979 deselected in 27.06s（exit 0）——缓存面已自 M-2 时点衰减（非 3 级联态）；3 级联转绿由 LRC 全量（级联族超集）+ EVD-1234 机录双重佐证（见 CR-F5）。
- **附加（跨票共享面）**：test_archive.py **170 passed + 6 subtests** in 2.64s——FEAT-074↔FEAT-075 共享 archive.py 面无回归。

### 重点 5：M-2 双层报告一致性（EVD-1235 声明 vs 实跑）— PASS（附注记）

- **archive-integrity FAIL 形态**：实跑单 issue=「Archive trigger gap: **0 hot completed task(s)** should be archived via release_forced for v0.1.0~v0.90.0」——与声明的「任务面 would=0 已闭合」+「0 hot completed task(s)」消息面**逐字吻合**；驱动面=证据面 178 行（scan-families 独立复现 178，见重点 1）——EXC-002 纸质承接口径与 12bef7c 基线附件互恰。注：standalone check exit 1 / check-governance 聚合面记 WARN——同源不同级，均非 fatal。
- **governance health 28s EXC-001 标注**：Check 28s 面实跑 `[ERROR] … 1755371 bytes — exception accepted (EXC-001, ref=DEC-282…)` 机注在屏 ✓。
- **遗留格式面=既有非本版引入**：EVD-702（2026-07-12）/EVD-1194（2026-09-27）/EVD-1198（2026-09-27）三行日期均**先于 0.91.0 发布**（2026-09-28 05:24 taggerdate）且行内容未在本范围 diff 内被改动；本周期 verify_workflow.py 变更面（FIX-400 超时/FEAT-075 例外/M-1 字面量）不涉 Check 28 字段校验语义——FAIL 面为既有披露面，非本版引入 ✓。
- **M-2R「复检零命中」口径核实**：EVD-1235 声明范围为 overstate/missing active version 定向复检——本次实跑同两项零命中 ✓；当前在屏的 Check 28c 两项 FAIL（session-snapshot/roadmap 行）属另一子面（见 CR-F3），不构成 EVD-1235 声明失实。
- **未复跑项**：check-release 全量（unit 26min/e2e/loop 门）——按任务边界以 M-2 机录为准（EVD-1235+EVD-1234 含 job 锚），本审以 LRC 全量+定向套件+verify 聚合覆盖其关键信号面（见遗留不确定项 1）。

### 重点 6：AI 专项 — 5/5 通过

- **编号/事实抽核**：EVD-1216~1235 **20/20 全存在**且 task 映射连贯（FEAT-073×4→FIX-400×3→FIX-401×2→FEAT-074×2→FEAT-075×2→FIX-402×1→REL-095×6）；RECO 链互证（plan 行「RECO EVD-1219 Top①」=EVD-1219 为 FEAT-073 完成必推荐行荐出 FIX-400；「RECO EVD-1222 Top①」同构）✓。DEC-269~285 **17/17 全存在**（decision-log 表行 L211~227）✓。
- **mock 残留**：零——本报告全部数字来自本会话实跑输出（命令/exit code/字节数/行数均在本审证据清单可溯）。
- **硬编码/幻觉 API**：零——所有引用命令亲跑且 exit 码记录（verify 0/archguard 0/version 0/manifest 0/LRC 0/data-size 0/archive-integrity 1 形态面）。
- **TODO/过度实现**：本审面零——聚合终审不重复逐票深审（六票各自 AI 专项已闭合）。

## 二、Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| CR-F1 | **P2** | .governance/decision-log.md（check-governance-data-size ERROR 面） | decision-log 254,420B > error_bytes 250,000，**无例外登记**（EXC-001 仅覆盖 evidence-log）且 advisory 面在 CHANGELOG 0.92.0 披露段与 EVD-1235 双层报告均未提及——披露完整性缺口（非缺陷：advisory/fatal_on_error=false/exit 0；本周期 DEC-269~285 十七行增量 ~4KB 推测为越阈诱因，因 .governance untracked 无法 git 精确归因越阈时点） | M-8 收口补披露（CHANGELOG 已知限制或 EVD 注记）；0.93 经例外治理路径登记或瘦身（FEAT-061 decision-log JSON 权威化后端已在） |
| CR-F2 | **P2** | skills/software-project-governance/infra/archive.py（check-architecture-health module_size ERROR） | archive.py 5508 行**本周期越阈 5000**（pre-cycle 4553 → FEAT-074 后 4942 → FEAT-075 16a5157 后 5508，splitlines 全行口径实测）——advisory ERROR 新增（3→4），FEAT-075-R1/EVD-1227/1228/EVD-1235/CHANGELOG 0.92.0 均未披露。非阻塞：「advisory — does not block release」原文在屏；archguard fatal gate（主文件锚）不受影响 | M-8 补披露；0.93 候选模块拆分（scan-families/例外逻辑独立——exception_registry.py 361 行独立模块先例已在本次交付面内） |
| CR-F3 | P3 | check-governance Check 28c | 两项 mid-chain FAIL（session-snapshot missing latest published release 0.91.0；plan-tracker missing 0.92.0 roadmap row）未列入 EVD-1235 FAIL 面清单——前者会话收工写快照自愈、后者 M-8 发布态回填（REL-094 M-8 同形先例） | 本会话收工消解前项；M-8 回填后项；M-8 收口时可在 EVD 补注面清单口径 |
| CR-F4 | P3 | REL-095 注册契约面 | REL-095 行注册契约占位触发 product_success_contract/acceptance_contract/quality_budget/vertical_slice/assumption_record 五组 FAIL——mid-chain 预期形态（发布中任务），但未在 M-2 报告枚举 | M-8 收口前填充（vertical_slice 状态字段支持 NOT_RUN_YET for planned work）或登记 deferral |
| CR-F5 | P3 | 测试元数据 | pytest --lf 缓存面衰减为 1P/979 deselected——无法原样复现 M-2 时点 3 级联态；级联绿由 LRC 全量 64P+81 subtests（级联族超集）+EVD-1234 机录佐证 | 无动作；知识记录：级联态以 M-2 机录为准 |
| CR-F6 | P3 | 提交面口径 | b6575bd（FEAT-074 输入锚，260 行单文件文档）不在任务简列 8 载荷提交内——plan-tracker FEAT-074 行已申报（设计准入输入），51 文件面全数可归因 | 无动作；终审口径注记 |
| CR-F7 | P3 | EVD-1235 数值口径 | 热表 1,753,848B（M-2 测量）vs 当前 1,755,371B——+1,523B=EVD-1235 行自身+REVIEW-REL-095-R1 机录行追加（测量先于追加的时序差），非数据漂移；距上限 2,036,197B 仍余 ~280KB | 无动作；M-8 收口复测时以新值为基线 |

## 三、硬门槛自检

| 门槛 | 结果 |
|------|------|
| P0 阻塞数=0 | ✓（最高级发现=P2，均 advisory 披露缺口，非缺陷） |
| 5 维度全覆盖 | ✓（正确性=验证组+跨票链复证／安全性=零写入代码级强制+fail-closed 豁免面不可静默扩大〔B2 负向因果〕／可维护性=CR-F2 披露／性能=verify 157.7ms advisory+LRC 258.96s+FIX-400 校准 2333s 在链／测试覆盖=64P+81sub+170P+6sub+--lf 1P） |
| 每条发现标注级别 | ✓（P2×2/P3×5） |
| 设计一致性（DEC 比对） | ✓（DEC-278 三单元交付面/DEC-282 发布口径/DEC-283 B2 授权边界/DEC-284 有界迁移/DEC-285 判据——全部以实跑复证，见重点 1/3/5） |
| AI 专项 5 项 | ✓（见重点 6） |

## 四、终态结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**。

- 六票+发布链三提交的跨票聚合面与发布态一致性**成立**：diff 总面 51 文件无未申报夹带；版本/锚/digest/例外四链端到端互恰；四项发布态检查全 PASS；LRC PASS/0/5；EXC-001 两层同屏；EXC-002 基线 178 精确复现；零写入红线代码级强制；回归面全绿且与预期逐数吻合；EVD/DEC 编号事实全核。
- P2×2 为 advisory 面披露完整性缺口（decision-log 超限未披露 + archive.py 越阈未披露），均不触发停止条件、不阻塞 M-4 及后续；建议 M-8 收口补披露（与 M-1 F-1 的 M-8 补记先例同轨）。
- 本结论为 CODE 半面硬门槛通过，**不替代 RELEASE 半面审查**（按链型先例由另一半面承载）。

## 五、证据清单

1. `git log e65b317^..df26f7e`（12 提交）+ `git diff --stat`（51 files +5333/−216）+ 逐提交 numstat 对账
2. verify 聚合实跑输出（Result: PASSED / VERIFY_EXIT=0；manifest 973→976 增量对账）
3. archguard-ratchet 实跑（R1 26478≤26478 / R7 committed==fresh True / Result: PASS 0 violations）
4. check-version-consistency PASSED exit 0；check-manifest-consistency PASS exit 0（976/1128）
5. check-loop-runtime-claims 实跑 JSON（verdict=PASS/findings=0/exemptions_count=5；5 条 exemption_id+五元组清单）
6. check-governance-data-size 实跑（EXC-001 两层同屏原文；decision-log 254,420B ERROR）+ check-governance 全量落盘（Check 28s L1061 机注原文；Check 27 L961「0 hot completed task(s)」；28c 两项 FAIL；REL-095 契约 FAIL 组）
7. pytest test_loop_runtime_claims.py 全量（64 passed + 81 subtests in 258.96s）；test_verify_workflow.py --lf（1 passed/979 deselected）；test_archive.py（170 passed + 6 subtests in 2.64s）
8. scan-families 双窗口实跑（[0.1.0,0.92.0] 锚面 commit=df26f7e/1,755,371B；[0.1.0,0.90.0] EVD would_archive=178=EXC-002 基线；active_task_ref=11=FIX-402 留热口径）+ .governance 输出拒绝负向探针（REFUSED exit 1 / Test-Path=False）
9. check-archive-integrity 实跑（单 issue「0 hot completed task(s)」形态，exit 1）
10. archive.py 四时点行数实测（4553→4942→5508→5508，python splitlines 口径）；architecture-health.json module_size error_lines=5000
11. evidence-log EVD-1216~1235 20/20 存在+task 映射表；decision-log DEC-269~285 17/17 存在（表行 L211~227）；EVD-702/1194/1198 日期提取（2026-07-12/09-27/09-27）
12. 六票+M1+B2 八份审查报告终态行 grep（全 AWN/0 或 NC→AWN/0）
13. CHANGELOG 0.92.0 段披露面 grep（EXC-001 条款摘要/FIX-402 口径在屏；5508/module/decision-log 超限零命中——CR-F1/F2 依据）
14. git status --porcelain 空（工作树干净，审查基线=提交态）

## 六、遗留不确定项

1. **check-release 全量未在本审复跑**（unit ~26min/e2e/loop 门聚合）——以 M-2 机录（EVD-1235/EVD-1234，job 锚在案）为准；本审以 verify 聚合+LRC 全量+定向套件覆盖其关键信号面。若 RELEASE 半面需要独立复跑，属该半面裁量。
2. **decision-log 越阈时点无法 git 归因**（.governance untracked）——「本周期 DEC 增量为诱因」为字节算术推测（254,420 − ~4K ≈ 250.4K 边缘），已在 CR-F1 如实标注不确定度；不影响「未披露」事实认定。
3. **3 级联转绿的测试名清单**未在 M-2 机录中逐名枚举（记为「级联 3 红」）——本审以超集绿+机录双重佐证采信（CR-F5）；如需逐名对账须回放 M-2 job 输出。
4. M-4~M-8 后续步骤（风险窗引用/manifest+transition/ledger/tag/收口）不在本审范围；CR-F1~F4 的消化点（M-8 收口）以 Coordinator 调度为准。
