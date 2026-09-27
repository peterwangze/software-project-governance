# REL-094 M-5 R0 审查报告 — 发布元数据 + CHANGELOG 发布态（先审后提交）

| 项 | 值 |
|---|---|
| 任务 | REL-094 M-5（0.91.0 发布链）— candidate manifest 创建 + CHANGELOG 发布态改写 |
| 轮次 | R0（首轮） |
| 审查人 | Release Reviewer（software-project-governance-release-reviewer；依据 `agents/release-reviewer.md` + `skills/release-review/SKILL.md` + Coordinator 五项清单） |
| 审查对象 | ① `skills/software-project-governance/core/releases/0.91.0.json`（untracked，新增 532B）② `project/CHANGELOG.md`（M，+17/−6，0.91.0 段发布态改写六处） |
| 工作树实况 | `git status --porcelain` 恰两条：`M project/CHANGELOG.md` + `?? skills/.../core/releases/0.91.0.json`（与审查对象一致，零范围外改动） |
| **结论** | **APPROVED_WITH_NOTES** |
| **unresolved_blockers** | **0**（独立结构字段；非自然语言口径） |
| 分级 | P0=0 / P1=0 / P2=0 / P3=3（全部非阻断备注） |

---

## 一、五项清单逐项结论

### 1. releases json 合规 — PASS

**与 0.90.0.json 结构逐字段同构**（亲读两文件 + Python 键集比对）：
- 顶层 8 键完全一致且均为 sorted 形态：`artifacts / effective_state / events / lifecycle_state / provenance / schema_version / trust / version`（`root_extra_keys=[]`）。
- `artifacts` 三键一致（`changelog / release_docs / review_evidence`）；`effective_state` 三键一致（`amendments / lifecycle_state / withdrawn`）。
- `trust` 同构：仅 `candidate_commit`，derivedCommit 形态（`{"derivation":"git_commit_adding_path"}`）与 0.90.0 一致。
- 内容差异均为预期面：`version`；`lifecycle_state`（candidate vs released）；`events`（`[]` vs 1 条 transition 事件——candidate 态无事件正确）；`release_docs` 4 条 vs 3 条（0.91.0 四件套=M-4④ 交付义务面，0.90.0 代三件套——数组元素数差异非结构偏差）。

**schema v1 禁入字段零混入**（亲读 `core/release-ledger.schema.json`）：
- root / `artifacts` / `trust` / `effective_state` / events.items 均为 `additionalProperties:false`；0.91.0.json 键集 ⊆ 允许集（`root_extra_keys=[]`、`trust_extra_keys=[]`）。
- backfill 族五字段（`original_release_commit` / `backfill_commit` / `document_contemporaneity` / `tag_disposition` / `tag_decision`）零在场（`backfill_fields_present=[]`）——native candidate 只允许 `candidate_commit`，allOf 条件分支亲验一致。
- 注：`jsonschema` 库本机未安装，库级 Draft 2020-12 验证未跑；以人工结构核验 + 仓库内权威验证器（`validate_release_ledger` 解析两 manifest 零 schema 投诉——0.90.0 整体 PASS / 0.91.0 唯一 issue 为 commit 计数，见第 3 项）双证。

**canonical 序列化**（亲跑 Python 字节级校验，两文件同法）：
- 0.91.0.json：NFC=True；`json.dumps(sort_keys=True, separators=(',',':'))+'\n'` 再生成 == 文件字节（`canonical_match=True`）；单尾 LF（`trailing_LF_count=1`）；无 CRLF。
- 0.90.0.json：`canonical_match=True`——0.91 形态与 0.90 基准完全同型。

**lifecycle_state=candidate、四件套全列且实存**：
- 顶层与 `effective_state.lifecycle_state` 双位均 `candidate`；`provenance=native`。
- `release_docs` 四路径逐一实存（字节实测）：release-plan 24,264B / release-checklist 9,779B / rollback-plan 4,945B / feature-flags 2,920B——M-4④ commit `5277ca5` 载荷（`git log` 确认）。
- `artifacts.changelog=project/CHANGELOG.md`、`review_evidence=.governance/evidence-log.md` 均实存。

### 2. CHANGELOG 发布态纪律 — PASS

- **标题零日期**：L5 `## [0.91.0] - <待回填 taggerdate>`（零日期字面）；FIX-349 口径占位注释在场（L6，`<!-- 发布日期占位…M-7 annotated tag 落地后以 taggerdate 权威回填 -->`）。
- **零已发布声明**：对 L5~L49 全节扫描 8 个词形（已发布/正式发布/已上线/released/is,has been released/tag 已/已打 tag）→ **零命中**。终账三行均为时点补记/不预写措辞（「提交 hash 由 M-5 提交生成，不预写」）——DEC-267(4) 不提前伪造完成态义务履行。
- **B-15 行为变更段五要素全齐**（L40~L42）：①形态描述（依赖理由单要素→三要素推荐卡〔服务目标/解决问题/方案要点+依赖理由〕，正文卡与短选项一一对应）；②契约面归类（agent 行为契约面=M7.4 6b/6c 重写，非 CLI 接口面——`task-priority-analysis` 命令行签名不变）；③三态如实（依据充分给完整推荐卡/依据缺失明示且不编造/依据影响执行先澄清）；④回滚说明（`git revert 196894a` 单提交回退 + revert 后 `release-projection --write` 再生版本面；无数据迁移）；⑤legacy 不覆盖声明（`GOVERNANCE_LEGACY_BEHAVIOR` 不回退推荐卡呈现——FEAT-040 只回退性能行为）。「无破坏性变更、无数据迁移」与 FEAT-072 契约面一致。
- **N-1 第二从句逐字**（与 `.governance/decision-log.md` L209 DEC-267(2) 原文对照）：L19「**计量或生成内容变化也可能越界**」逐字一致；同句「当前口径下净增超过 9 tok 即越界」亦逐字；「最终发布态必须再重测」义务保留在场。
- **数值形态**：strict **5991/6000**（M-1 实测；M-5 复测 2026-09-28 04:15 +0800 同值——时点标注在场）＋ evidence-log **1,750,295 bytes**（≈1709KB，M-5 发布态时点 04:15 +0800 实测——提交前最后读取口径——时点标注在场）。
- **数值真实性独立复核**（非仅形态检查）：本审查亲跑 `check-injection-budget --profile strict` → `TOTAL resident 5991 / 6000 PASSED`；`Get-Item` 实测 `.governance/evidence-log.md` Length = **1,750,295 字节精确一致**（Check 28s 同值 1709.3KB 交叉印证）。

### 3. release-ledger 结构面 — PASS（预提交态唯一 issue = 机制时序，符合预期）

- 亲跑 `release-ledger --version 0.91.0 --no-remote` → exit 1，**issues 恰一条**：`candidate_commit: expected exactly one commit adding skills/.../releases/0.91.0.json, found 0`——未提交时序唯一形态；`trust_level=NATIVE_CANDIDATE`、`release_authorized=false`、零其他结构 issue。
- 0.90.0 旁证：exit 0 **PASS**，`NATIVE_RELEASED`，candidate_commit `b91881b` + release_commit `3f87459` 派生与事件身份校验正常。

### 4. check-release 归因核实 — PASS（两 issue 与 Developer 归因一致；无静默包装；无第三个 M-5 issue）

- 亲跑 `check-release --version 0.91.0` → 总出口 **FAILED - 2 issue(s)**，两 issue 全部落在 execution gates：① `governance health (exit=1)`；② `unit tests (exit=None，180s 超时)`。其余全部门 PASS（version consistency / release fact source / hot fact source / release docs / release lineage〔candidate 模式明示边界注记〕/ gate sequence / one-dot-zero blockers / changelog / loop fuse / dsh 升级回归冒烟 / loop runtime claim gate 等）。
- **governance-health advisory 族亲验**：直接复跑 `check-governance --fail-on-issues` → 「19 issues」census 全景枚举——
  - 唯一 ERROR = Check 28s `.governance/evidence-log.md 1750295 bytes`——检查器自标 **advisory（fatal_on_error=false，does not block release）**，与 CHANGELOG 披露字节精确同值（DEC-264 既有结构性约束的已知披露面，非本 diff 引入）。
  - 两条 M-5 链**时序面**：Check 24（plan-tracker 版本 0.90.0≠0.91.0——M-8 收口义务，未到执行时点）+ Check 25（untracked 1 文件 = `0.91.0.json` 本身，gate 自标 ordinary/non-blocking——**提交即消**）。
  - 其余 28n/28q/29/30/30c/35/36 族为 0.81.0（91 issues，EVD-1038）/0.88.0（95→36，EVD-1170）/0.84.0（20 issues，EVD-1087）同型在案先例的历史基线；Check 2 三条 stale risks（RISK-036/039/050）= DEC-268(1) 09-30 窗复评的维持对象。
  - **无第三个 M-5 相关 issue。**
- **unit tests 180s 墙钟（DEC-262 家族）**：超时上限 = `SPG_RELEASE_GATE_TIMEOUT` 默认 180s（verify_workflow.py L6075/L6146 亲证）。本审查以无 180s 上限复跑全套件（`C:\Python314\python.exe -m unittest .../test_verify_workflow.py -v`）→ **exit 0 全套件通过**——证实超时为本机墙钟预算问题、非产品回归。精确墙钟未单独计时（复跑输出截断窗口截去了 unittest 汇总行）；完成时点横跨本审查后续多条命令（>180s 明确成立），与 Developer 声称的本机 ~303s 量级一致。
- **无静默包装**：`release-ledger` 为 candidate_commit 检查的唯一执行点（verify_workflow.py 全文检索：该检查仅存在于专用子命令分发）；check-release 的 release lineage 门以明示边界注记披露 candidate 模式语义（不要求 tag 先于 release commit；released 复跑义务已登记）；untracked json 在 Check 25 以明示身份出现——零隐藏，提交即消。

### 5. 版本一致性 — PASS

- 亲跑 `check-version-consistency` → **PASSED**（13 文件 + bootstrap markers）；唯一 WARN = `plan-tracker workflow version=0.90.0, expected=0.91.0` = M-8 收口面（义务未到执行时点）——与任务预期一致。

---

## 二、Findings

**P0：无。P1：无。P2：无。**

- **P3-1（流程完整性备注）**：M-5 复测/时点双值（04:15 口径）当前在 evidence-log 无独立机录行（REL-094 现有 EVD-1208=M-1、EVD-1211=M-4）。数值经本审查独立复跑证实为真（5991/6000 + 1,750,295B 双复现）。按链惯例（EVD-1169 先例）M-5 EVD 行应随本提交批 / M-6 机录补账。不阻断——终账已声明「尾账随 M-6/M-7 收口续记」，且 DEC-267(2) 本要求最终发布态再重测。
- **P3-2（文档措辞勘正候选）**：`release-checklist-0.91.0.md` 条件⑥括注「project+root 投影双位同步」与在役裁决不一致——REL-091 登记行（archive v0.1.0~v0.90.0）明载「单 canonical=project/CHANGELOG.md——DEC-242① 继承，不复刻双位过渡」，REL-094 triage 继承同口径。本 diff 单面改写**符合现行裁决**；根 `changelog.md` 停于 0.88.0 过渡终态（头部双位过渡披露在场）系 DEC-242① 前的历史残留，非本次引入。条件⑥括注为 0.88.0 模板残留措辞，建议 M-8 批勘正或登记 0.92 候选。不阻断本 diff。
- **P3-3（登记性备注，零修正必要）**：0.91.0 段首小节标题（L8）口径「DEC-265~267」为载荷链口径（M-0 冻结边界），未含 DEC-268（M-4 留痕非载荷）；权威决策链行（L24）已含 DEC-268。两口径并存无失实。

**审查侧观察**：本审查终端对框线字符的捕获在 GBK 控制台呈 mojibake——审查侧捕获伪影，非产品缺陷（文件 UTF-8 正常，read 工具读入无异常）。

---

## 三、判定

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0**

五项清单全 PASS，零阻断 finding；三条 P3 备注不构成返工义务。可按「先审后提交」序进入提交：提交后 `candidate_commit found 0` 机制时序自然消解，M-6 ledger / M-7 tag+push / M-8 归档按链继续。复审衔接义务（若 Coordinator 需 R1）：逐条核对本报告 P3-1（M-5 EVD 机录补账）处置态。

## 四、亲跑命令摘要

| # | 命令 | 结果 |
|---|---|---|
| 1 | `git status --porcelain` / `git diff -- project/CHANGELOG.md` | 恰两审查对象；+17/−6 与面声明一致 |
| 2 | `release-ledger --version 0.91.0 --no-remote` | exit 1；唯一 issue = candidate_commit found 0（预期时序） |
| 3 | `release-ledger --version 0.90.0 --no-remote` | exit 0 PASS（NATIVE_RELEASED 旁证） |
| 4 | `check-release --version 0.91.0` | exit 1 FAILED - 2 issues（governance health + unit tests 180s）——与归因一致 |
| 5 | `check-governance --fail-on-issues`（full + `--summary-only --level strict`） | 19 issues census 全景；唯一 ERROR=28s 1,750,295B（advisory）；Check 24/25=两条 M-5 时序面；无第三个 M-5 issue |
| 6 | `check-injection-budget --profile strict` | 5991/6000 PASSED（CHANGELOG 复测值独立复现） |
| 7 | `check-version-consistency` | PASSED；唯一 WARN=plan-tracker M-8 面 |
| 8 | Python canonical 字节级校验（NFC/sort_keys/compact/单尾 LF，两 manifest） | `canonical_match=True` 双证；键集 ⊆ schema；backfill 族零在场 |
| 9 | 全套件 unittest 复跑（无 180s 上限，后台） | **exit 0 通过**——180s 超时=墙钟族非产品回归（DEC-262） |
| 10 | 四件套/changelog/evidence-log 实存与字节实测 + commit 哈希四点核验（196894a/9bafdf6/5277ca5/3f87459） | 全实存；字节精确；哈希全命中 |
| 11 | DEC-267(2) 原文对照（decision-log L209）+ 已发布声明词形扫描（L5~L49） | N-1 从句逐字一致；零已发布声明命中 |
| 12 | 根 changelog.md 性质核实（M-3 双位裁决 + REL-091/REL-094 triage 登记） | 单 canonical 现行裁决确认（P3-2 依据） |
