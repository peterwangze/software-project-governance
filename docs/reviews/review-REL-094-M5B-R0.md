# REL-094 M-5b R0 审查报告 — release ledger transition（先审后提交——单行 manifest 高 stakes）

| 项 | 值 |
|---|---|
| 任务 | REL-094 M-5b（0.91.0 发布链）— `0.91.0.json` lifecycle transition（candidate→released） |
| 轮次 | R0（首轮） |
| 审查人 | Release Reviewer（依据 `agents/release-reviewer.md` + `skills/release-review/SKILL.md` + Coordinator 四项清单） |
| 审查对象 | `skills/software-project-governance/core/releases/0.91.0.json`（M，单行替换 1+/1−）：events[] 追加 `rel094-transition`（candidate_to_released，五字段，integrity sha256:70e09dd9…）+ 双 lifecycle_state 翻转 candidate→released |
| 工作树实况 | `git status --porcelain=v1` 恰 1 条：` M skills/software-project-governance/core/releases/0.91.0.json`（零范围外改动、零 untracked）；`git diff --stat` = 1 file, 1 insertion(+), 1 deletion(-) |
| **结论** | **APPROVED_WITH_NOTES** |
| **unresolved_blockers** | **0**（独立结构字段；非自然语言口径） |
| 分级 | P0=0 / P1=0 / P2=0 / P3=3（全部非阻断备注） |

---

## 一、四项清单逐项结论

### 1. 事件合规 — PASS

**与 `core/releases/0.90.0.json` events[0] 逐字段同构**（亲读两文件 + python 键集比对）：
- 事件键集恰为 `{claims, id, integrity, recorded_at, type}`（0.90 与 0.91 完全一致）；`claims` 键集恰为 `{derivation, m4_authorization, release_task}`（一致）。
- 模式同构对照：`rel093-transition`/`REL-093` → `rel094-transition`/`REL-094`（id=任务号小写去连字符+`-transition` 后缀，惯例一致）；`type` 均为 `candidate_to_released`；`derivation` 均为 `manifest_only_transition`；`m4_authorization` 均为「preauthorization DEC + conditional_go DEC + 决策日本地日期」三段式（0.90：`DEC-253_preauthorization_plus_DEC-263_conditional_go_20260927`；0.91：`DEC-265_preauthorization_plus_DEC-267_conditional_go_20260928`）。
- `recorded_at` 均为 UTC ISO-8601 Z 形态。

**schema v1 事件五字段恰合**（亲读 `core/release-ledger.schema.json` L44-57）：
- `events.items` 为 `additionalProperties:false` + `required` 恰五字段（`id/type/recorded_at/claims/integrity`）；`type` 枚举含 `candidate_to_released`；`integrity` pattern `^sha256:[0-9a-f]{64}$`。
- 顶层 8 键（artifacts/effective_state/events/lifecycle_state/provenance/schema_version/trust/version）⊆ schema required 八项，root `additionalProperties:false` 无违例；`provenance:native` → allOf 分支要求 `trust.candidate_commit` 为 derivedCommit `{derivation:"git_commit_adding_path"}`（在场，亲验）。
- 权威验证器零 schema 投诉（见第 3 项 release-ledger 输出）。

**m4_authorization 与 decision-log 实存对应**（`.governance/decision-log.md` 亲读）：
- `DEC-265` = **L207**（2026-09-27 用户授权）：0.91.0 推进与发布授权——预授权覆盖该单一版本发布链（M-0~M-8）的发布类关键决策 → 授权串「DEC-265_preauthorization」忠实。
- `DEC-267` = **L209**（2026-09-28，经 arch 顾问——DEC-265③ 强制咨询点）：0.91.0 M-0 载荷冻结裁决（arch GO **有条件**冻结——不提前授权 tag/push，附 10 条发布停止条件）→ 授权串「DEC-267_conditional_go」忠实；日期后缀 `20260928` 与 DEC-267 决策日一致。

**变更面恰三处**（diff 逐 token 对照 HEAD 版）：`effective_state.lifecycle_state` candidate→released、顶层 `lifecycle_state` candidate→released、`events` `[]`→1 条 transition 事件。`artifacts/trust/provenance/schema_version/version` 与 HEAD 版逐字节相同（本 diff 未触碰 artifacts 面）。

**recorded_at 时序自洽**（曾疑似早于 DEC-267 决策日，亲证排除）：`2026-09-27T21:12:18Z` = 本地 `2026-09-28 05:12:18 +08:00`——晚于 M-5 candidate 提交 `fed2f53`（09-28 05:06:04+08:00）6 分钟、早于本审查时点（05:18:20+08:00）。decision-log 行日期为本地时区日、事件时间为 UTC Z——非编造、非陈旧，时序链（DEC-267 → M-5 commit → transition 记录 → 本审查）单调。

### 2. integrity 独立复算 — PASS

- **机制亲读**：`infra/release/ledger.py` L157-159——`event_integrity` = payload（事件去 `integrity` 键）→ `_canonical(value)`（L152-154：`canonical_json_bytes` 剥离尾 LF——即 NFC 归一 + `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` **无尾 LF**）→ sha256 → `sha256:<hex>`。
- **独立复算**（python -c 内联实现同机制，未 import ledger 模块）：重算值 `sha256:70e09dd9e7b7813c10ec7acf8f2ea3418ad092565ca8abbda676a5911b4e8c0d` **== 文件内值**（`INTEGRITY MATCH: True`）。
- **canonical 文档字节校验**：raw 文件字节 == canonical 再生成（NFC + sorted keys + compact separators + 单尾 LF）→ `raw == canonical(with trailing LF): True`（无 BOM、无 CRLF、sorted、compact）。
- 附：`_validate_events` L229-232 的 integrity 自引用禁令与 L231 显式比对（declared != event_integrity → issue）在本事件上零触发（release-ledger 输出零 integrity issue 双证）。

### 3. 机制时序 — PASS（唯一 issue = 预期「found 0」）

- **亲跑** `python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.91.0 --no-remote` → exit 1，**issues 恰一条**：`skills/software-project-governance/core/releases/0.91.0.json: expected one candidate-to-released Git transition, found 0`——与任务预期完全一致（未提交时 `_transition_commits` L257-287 在 git 历史中找不到 candidate→released 翻转提交的唯一时序形态）；除此之外零 issue：schema/canonical/artifacts 路径存在性/effective_state 推导（`derive_effective_state` released/withdrawn=false/amendments=[]）/event_identities 抽取全过，`trust_level=NATIVE_RELEASED`，`candidate_commit=fed2f53`。
- **candidate_commit 与 HEAD 一致**（git rev-parse HEAD 亲跑）：`fed2f5312f39b8c7088c776d5dd9da73dd0cfe8c`；且 `git log --diff-filter=A` 亲证 `fed2f53` 即添加 `0.91.0.json` 的提交（M-5，2026-09-28 05:06:04+08:00）→ `git_commit_adding_path` 派生结果 = HEAD。
- **transition commit 单父校验前提成立**：HEAD `parents=[5277ca507e3149bd88592265c6a99a09cc8432fd]`（恰一父）；HEAD 版 manifest 亲证 `lifecycle_state=candidate / events:0` → 提交本 diff 后，翻转提交（父=HEAD）满足 `before=candidate ∧ now=released` 单父判定（L264-280），transitions 恰 1 且 `parent == candidate_commit`（L459）→ **提交后 `--no-remote` 口径预期整体 PASS**。
- **0.90.0 旁证**：`release-ledger --version 0.90.0 --no-remote` → exit 0 **PASS**（NATIVE_RELEASED，candidate_commit `b91881b` / release_commit `3f87459`，事件身份 `rel093-transition` 校验正常）——机制在已提交基线上工作正常。

### 4. 提交纪律前置 — PASS

- `git status --porcelain=v1`：恰 1 条修改（该 manifest），无其他未提交变更、无 untracked → **manifest-only 单父 transition commit 可成立**（commit 必须且仅包含此文件、单父、非 merge）。
- canonical 校验：`raw == canonical True`（见第 2 项）。
- 提交后不变量提示：`_transition_commits` 按「父=candidate ∧ 本身=released」计数翻转——本文件此后**不得再出现 candidate↔released 翻转提交**（revert 后再翻转 → transitions=2 → 永久 FAIL）；后续 amendment/withdrawal 事件（released→released 基线）不计数、不破坏。

## 二、亲跑命令摘要

| # | 命令 | 关键输出 |
|---|------|---------|
| 1 | `git status --porcelain=v1` | 恰 ` M skills/.../core/releases/0.91.0.json` 一条 |
| 2 | `git rev-parse HEAD` | `fed2f5312f39b8c7088c776d5dd9da73dd0cfe8c` |
| 3 | `git diff --stat` | 1 file changed, 1 insertion(+), 1 deletion(-) |
| 4 | `python -c`（独立复算 integrity + canonical + 0.90/0.91 键集比对） | `INTEGRITY MATCH: True`；`raw == canonical(with trailing LF): True`；事件/claims 键集 isomorphic=True；DEC-265/DEC-267 在授权串内在场 |
| 5 | `python skills/.../verify_workflow.py release-ledger --version 0.91.0 --no-remote` | exit 1；issues 恰 1 条 = `expected one candidate-to-released Git transition, found 0`；trust_level=NATIVE_RELEASED；candidate_commit=fed2f53 |
| 6 | 同上 `--version 0.90.0 --no-remote` | exit 0 PASS（旁证基线） |
| 7 | `git log --diff-filter=A -1 -- <manifest>` | `fed2f53… \| Mon Sep 28 05:06:04 2026 +0800 \| REL-094 M-5…` |
| 8 | `git show -s --format='%H parents=[%P]' HEAD` | `parents=[5277ca50…]`（单父）；`git show HEAD:<manifest>` → lifecycle=candidate/events=0 |
| 9 | `Get-Date` / `[DateTime]::UtcNow` | 2026-09-28 05:18:20+08:00 = 2026-09-27 21:18:20Z（recorded_at=21:12:18Z，晚于 M-5 提交、早于本审查） |

## 三、发现分级

**P0 = 0；P1 = 0；P2 = 0。**

- **P3-1（提交后终态非本轮亲证）**：提交后 `--no-remote` PASS 属机制推演（第 3 项前提全部亲证：单父 HEAD、candidate 基线、恰一翻转、parent==candidate_commit 语义）。放行条件：transition commit **必须 manifest-only 单父**（工作树已满足），且提交后 **MUST 复跑** `release-ledger --version 0.91.0 --no-remote` 确认 exit 0 才算 M-5b 闭环——此为 Coordinator 提交动作的既定确认步。
- **P3-2（remote/tag 面未验）**：本轮按任务口径 `--no-remote`——v0.91.0 tag 事实（`tag_facts`）与远端校验未执行；该面属 M-7 tag 落地/M-8 终态义务，非本 R0 范围。
- **P3-3（链级边界）**：本轮只审 manifest diff 机制面与四项清单；M-0~M-8 全链证据（M-1/M-2/M-3/M-4/M-5 各 R0 报告、DEC-267 十条停止条件的逐条履行）未重审，由 Coordinator 按发布链收口。

## 四、结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）——diff 本体四项全 PASS、零阻断发现；diff 可提交。提交时遵守：manifest-only 单父；提交后复跑 release-ledger `--no-remote` 确认 PASS。
