结论：**NEEDS_CHANGE** ｜ round=2 ｜ prev_report=`docs/reviews/review-REL-077-RELEASE-R1.md` ｜ unresolved_blockers=3 ｜ 机录 round 建议 = `REVIEW-REL-077-R5`

# Review — REVIEW-REL-077-RELEASE-R2（0.81.0 **发布动作核验**：M-5 transition / M-6 released 门禁 / M-7 tag+push / M-8 归档 · round 2）

- **round**：R2（release 面第 3 轮；R0 自编号 0 / R1 自编号 1 / 本轮 2）
- **prev_report**：`docs/reviews/review-REL-077-RELEASE-R1.md`（**已全文通读**，结论 `APPROVED_WITH_NOTES` / `unresolved_blockers=0`）
- **前前轮**：`docs/reviews/review-REL-077-RELEASE-R0.md`（**已全文通读**，结论 `NEEDS_CHANGE`，blocking = F-01）
- **本轮性质**：发布动作**已按 DEC-190 ⑨ 预授权执行完毕**（不得也不需要由我重新裁决"是否发布"）⇒ 本轮为**独立核验发布结果的公开事实与闭环**
- **返回 Coordinator 的结论与本首行同一**：`NEEDS_CHANGE`，`unresolved_blockers=3`
- **一句话摘要**：**git 层面的声明式发布是完整且正确的**（transition 单父 + manifest 判决释 + 事件 integrity 复算相符 + ledger PASS/NATIVE_RELEASED + 本地/远端 tag 逐位一致 + master 已推送 + 归档完整性 PASS + 真实环境面零 overclaim），**但已发布面存在 3 项可复核的门禁/文档缺陷**：① released 态门禁**实为 6 项 FAIL / 38 issues**（非记录的"16 PASS / 3 残留"），其中 2 项是**新出现**的 `release fact source` 与 `hot fact source`；② 回滚方案的**发布 tip 未回填**（6 处占位）；③ README 仍写"**not yet pushed** / GitHub master still serves 0.78.1"，**已经推送** ⇒ 与 git 事实相反。

---

## 0. 审查对象、送审版本与只读边界

| 项 | 值 |
|---|---|
| 送审对象 | **已发布的 0.81.0 结果集**：transition 提交 `e376ddf`（= `HEAD` = `master` = `refs/tags/v0.81.0^{}`）、`core/releases/0.81.0.json`（released 态）、`docs/release/*-0.81.0.md` 三件套 + 版本规划 + 真机规程、`project/CHANGELOG.md`、`README.md`、`.governance/` 治理记录（**只读**） |
| 基线 | 工作树 = `e376ddf`，`git status` 在全部命令前后未见被审文件变动（唯一新增 = 本报告） |
| 我的写入 | **唯一写入 = 本报告文件**。全程无 `git add/commit/tag/push/restore/reset/checkout/stash/revert`，无 worktree 创建，无全量 `discover` |
| 隔离纪律 | 两条测试命令均把 `DSH_HOME` 重定向至 `%TEMP%` 新建目录（变量名 `$tmpHome`，**未使用保留变量 `$home`**），并逐条上报（§7）。未触碰 `$env:USERPROFILE\.dsh` 或任何仓库外路径 |
| Reviewer 工具权限说明 | `agents/release-reviewer.md` L88 表把 Bash 标为禁用；但本任务规范**显式授权**只读命令（`git log/rev-list/rev-parse/cat-file/show/ls-remote/diff`、`verify_workflow.py` 只读子命令、单模块 unittest）⇒ **以任务规范为准**；写操作仍严格禁止 |

---

## 1. ① M-5 transition（声明式发布状态转变）—— **PASS（全部判据满足，我自己复算）**

### 1.1 提交形态

| 判据 | 实测 | 结论 |
|---|---|---|
| transition 提交 = `e376ddf` | `git log --oneline -1 e376ddf` = `e376ddf REL-077: 0.81.0 transition + 门禁收口与审查退回修复（M-2/M-3/M-5 收束于发布提交）` | ✓ |
| `git rev-list --parents -n 1 e376ddf` | `e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3 a89341e11544df0dbe5e4b5c8fd340bd7e8e5e1c` ⇒ **恰一个 parent** | ✓ |
| parent == 候选提交 `a89341e` | `a89341e11544df0dbe5e4b5c8fd340bd7e8e5e1c` = `git rev-parse a89341e` **逐位相同** | ✓ |
| 无 merge / 无 repeat | `_transition_commits` 只认单父提交；`git log --format=%H -- <manifest>` 仅 2 个提交（`a89341e` 建、`e376ddf` 转），二者皆单父 | ✓ |

### 1.2 manifest 内容（`skills/software-project-governance/core/releases/0.81.0.json`，**813 bytes**）

| 判据 | 实测值 | 结论 |
|---|---|---|
| `lifecycle_state` | `released` | ✓ |
| `effective_state.lifecycle_state` | `released`（`{amendments: [], lifecycle_state: released, withdrawn: false}`） | ✓ |
| `candidate_to_released` 事件数 | **恰 1 个**（`events` 长度 = 1，`id = rel077-transition`） | ✓ |
| 事件 `integrity` | `sha256:d475a2b19c1c77a720195d796487226f78f0c335c2afcf76fae74c4b2ace65a7` | ✓（见 1.4 复算） |
| `claims.derivation` | `manifest_only_transition` | ✓ |
| `claims.m4_authorization` | `DEC-190_9_publish_preauthorization_20260913` ⇒ **引用 DEC-190 ⑨** | ✓ |
| `provenance` / `schema_version` | `native` / `1` | ✓ |
| `trust.candidate_commit` | `{"derivation": "git_commit_adding_path"}`（派生 = `a89341e`，`git log --diff-filter=A` 实测） | ✓ |

### 1.3 字节形态（canonical）—— **以程序判定，非目测**

我**独立重实现**了 `ledger.canonical_json_bytes` 的规则（NFC 归一 → `sort_keys=True` → `separators=(",",":")` → `ensure_ascii=False` → 单尾 LF → UTF-8），并与文件原始字节逐位比对：

```
recomputed_canonical_bytes == file bytes : True len(file)= 813
ledger.event_integrity = sha256:d475a2b19c1c77a720195d796487226f78f0c335c2afcf76fae74c4b2ace65a7
ledger match           = True
parse_canonical ok     = True
derive_effective_state = {'lifecycle_state': 'released', 'withdrawn': False, 'amendments': []}
effective_state in file= {'amendments': [], 'lifecycle_state': 'released', 'withdrawn': False}
transition_events      = 1
```

⇒ 文件字节 **恰等于**其 canonical 形式（NFC + 键排序 + 紧凑分隔符 + 单尾 LF）；`ledger.parse_canonical_manifest_bytes` 不抛 `CANONICAL_BYTES`。✓

### 1.4 event integrity **自校验**（我自己复算）

依 `ledger.py:152-159` 的算法：`payload = event 去掉 integrity 键` → `canonical_json_bytes(payload)[:-1]`（**去掉末尾 LF**）→ `sha256`：

```
independent_recompute  = sha256:d475a2b19c1c77a720195d796487226f78f0c335c2afcf76fae74c4b2ace65a7
declared_in_manifest   = sha256:d475a2b19c1c77a720195d796487226f78f0c335c2afcf76fae74c4b2ace65a7
MATCH                  = True
```

⇒ **声明值与我的独立复算逐位相同**（我未调用 `ledger.event_integrity`，另行实现；随后用 `ledger.event_integrity(ev)` 对照亦相同）。✓

### 1.5 transition diff 的「manifest 面」判决释

`git diff a89341e e376ddf -- …/0.81.0.json` 只有 **1 行替换**，且差异**恰为**：`lifecycle_state` `candidate → released`、`effective_state.lifecycle_state` `candidate → released`、`events` `[] → [rel077-transition]`。**无** `trust.candidate_commit` 重写、**无** `artifacts` 变更、**无**版本/来源/schema 变更 ⇒ **manifest 面的变更确实只承载 transition 本身**（`claims.derivation = manifest_only_transition` 的自述与之相符）。✓

### 1.6 裁决（对 `release-review` / `release-checklist` SKILL 的 release commit 要求）

`release-checklist/SKILL.md:68`：**「release commit 单父且 parent=candidate commit；只有一个 transition event」** —— 三项判据**全部满足**（§1.1 ×2 + §1.2 事件数）。
`stage-release/SKILL.md:58 / :115`：「release commit 仅追加唯一 transition 并改为released，其单一 parent 必须是 candidate commit」「tag 必须 peel 到该 commit；merge/repeat/wrong-parent/rename-delete-add 均阻断」 —— **无任一阻断形态**。

**⇒ ① 裁决：transition 满足规范要求。** 附一条**限定说明（不计缺陷）**：`e376ddf` 自身是**打包提交**（11 文件），除 manifest transition 外还含 `22cf185` 的门禁收口、FIX-334/335 修复、3 份审查报告入库。`manifest_only_transition` 的语义已由 §1.5 证实为「**manifest 面**的变更仅为 transition」；commit 级"只改 manifest"在当前规范文本中**不是**判据（规范只要求单父/parent/事件数），故**不构成 finding**；但收口改动与 transition 同批落库使 `22cf185` 从历史中消失（见 §5 观察 O-2）。

---

## 2. ② M-6 released 态门禁 —— **half：ledger PASS；`check-release` 与记录不符**

### 2.1 `release-ledger`（**PASS，与任务预期一致**）

```
python …/verify_workflow.py release-ledger --version 0.81.0 --remote github-https
{ "state": "PASS", "pass": true, "issues": [] ,
  "manifests": [ { "state":"PASS", "issues": [],
    "effective_state": {"lifecycle_state":"released","withdrawn":false,"amendments":[]},
    "event_identities": [{"id":"rel077-transition","integrity":"sha256:d475a2b1…65a7"}],
    "event_identity_digest": "5f8a8fdd6be53bc20ec930ba94e0f3d77fe6d80234eb5986d3dca33e0ab55ef7",
    "trust_level": "NATIVE_RELEASED",
    "candidate_commit": "a89341e11544df0dbe5e4b5c8fd340bd7e8e5e1c",
    "release_commit":   "e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3",
    "tag_facts": {"state":"PASS","tag":"v0.81.0","remote":"github-https",
                  "local_tag_commit": "e376ddf…","remote_tag_commit": "e376ddf…"} } ] }
```
⇒ **state PASS / trust NATIVE_RELEASED / issues 空** ✓；`candidate_commit = a89341e…` ✓；`release_commit = e376ddf…` ✓。**远端 tag 亦经该命令验证为 PASS**（`local_tag_commit == remote_tag_commit`）。

### 2.2 `check-release --lineage-mode released`（**与记录不符 —— 本轮 P1 finding 的来源**）

```
python …/verify_workflow.py check-release --version 0.81.0 --require-changelog \
       --lineage-mode released --release-commit e376ddf --lineage-remote github-https
   Lineage mode: released
  [PASS] version consistency
  [FAIL] release fact source          ← 本轮新出现（9 条）
  [FAIL] hot fact source              ← 本轮新出现（24 条）
  [PASS] runtime readiness matrix
  [PASS] first session measurement
  [PASS] governance pack status
  [PASS] agent adapters
  [PASS] projection sync
  [PASS] cross references
  [PASS] archive integrity
  [PASS] release docs
  [PASS] release lineage
  [PASS] gate sequence for release
  [PASS] one dot zero blockers
  [FAIL] execution gates
    [PASS] verify (exit=0) | [FAIL] governance health (exit=1)
    [PASS] e2e check (exit=0) | [FAIL] unit tests (exit=None)
  [SKIP] dsh upgrade regression — released-history check (BR-4 / DEC-153 ②)
  [PASS] loop fuse block
  [PASS] changelog
  [FAIL] loop runtime claim gate (semantic_verdict=BLOCKED; identity_verdict=FAIL)
  Result: FAILED - 38 issue(s).
---exit=1
```

**实测口径：14 项 PASS / 6 项 FAIL / 1 项 SKIP；`Result: FAILED - 38 issue(s)`（exit 1）。**

| 任务给定的预期 | 我的实测 | 裁决 |
|---|---|---|
| **16 项 PASS** | **14 项 PASS**（含 `governance pack status`/`release docs`/`release lineage`/`archive integrity` 等；`dsh upgrade regression` 在 released 模式为 **SKIP** 而非 PASS） | **不符** |
| 残留 3 项 FAIL 全为既有基线（`execution gates` / `governance health` 91 issues / `unit tests` 180s / `loop runtime claim gate` BLOCKED） | 残留 **6 项** FAIL：上述 3 组 **+ `release fact source` + `hot fact source`**；`governance health` 实测 **84 issues**（非 91） | **不符（多 2 项）** |
| `release lineage` 与 `archive integrity` 均为 PASS | **两者均 PASS** ✓（另 `check-archive-integrity` 单跑亦 PASS，§4.1） | **符合** |
| 3 项残留是否确与历次测量同源（既有基线）、有无本版引入的新失败 | 3 组执行面残留**同源**（见 2.4）；但**新增 2 项**失败**非同源** | **有新增** |

#### 2.2.1 两项新 FAIL 的构成（逐条）

**`release fact source`（9 条）**：`.governance/plan-tracker.md` missing `1.0.0` dependency chain section / missing `1.0.0` roadmap row / requirement matrix missing `REQ-059`…`REQ-064`（6 条）；`project/references/architecture.md:445` architecture overstates pending Gemini/opencode or real-environment E2E status（1 条）。

**`hot fact source`（24 条）**：missing hot fact-source section `## 版本规划` / `## 需求跟踪矩阵` / `### 1.0.0 依赖链`（3 条）；missing `0.38.0` roadmap row、missing `0.37.0` roadmap row；current active items missing active version `0.38.0`；hot sections overstate `0.38.0` as released before REL-013；active `0.38.0` task table missing `FIX-082`~`FIX-087` + `REL-013`（7 条）；requirement matrix missing `REQ-070`~`REQ-074`（5 条）…（工具打印 15 条 + 「and 9 more」）。

#### 2.2.2 确定性：**非释放模式特有的偶发**（我跑了对照）

我以 **candidate 模式**（`--lineage-mode candidate`）对**同一个工作树**复跑：结果**逐项相同** —— 同样 `[FAIL] release fact source`、`[FAIL] hot fact source`、同样 `Result: FAILED - 38 issue(s)`、同样 exit 1（`Lineage mode: candidate`，`[PASS] dsh upgrade regression` 而非 SKIP）。⇒ 两项失败**与 lineage 模式无关**，是**数据面/工作树面**的确定性失败。

#### 2.2.3 归因：**由 M-8 归档迁移引入**（三条可复核证据）

1. **工具面判据是"必需热节"**：`verify_workflow.py:2011-2023` 的 `required_sections = ["## 项目配置","## 项目总览","## 当前活跃事项","## 版本规划","## 需求跟踪矩阵"]`（dogfood 模式再追加 `### 1.0.0 依赖链`）——缺一即 FAIL；`release fact source` 侧的 `missing 1.0.0 dependency chain section` / `missing 1.0.0 roadmap row` / `requirement matrix missing …` 同源（同一组热节）。
2. **当前 plan-tracker 确实缺 3 个必需节**：`.governance/plan-tracker.md`（61,002 B）的全部标题仅 **7 行**——`# 当前项目样例`、`## 项目配置`、`## Onboarding 声明`、`## Gate 状态跟踪`、`## 项目总览`、`## 当前活跃事项（…）`、`### 优先级一览`；**`## 版本规划`、`## 需求跟踪矩阵`、`### 1.0.0 依赖链` 全部不存在**（三者在 2026-09-10 的备份中**都存在**）。
3. **对照证据（我逐节 diff 了 2026-09-10 的仓库内备份）**：`.governance/backups/governance-backup-20260910-prefix301/plan-tracker.md`（364,114 B）与新 plan-tracker 的标题差集 = **仅存在于备份、现已被移除**的节恰为：
   ```
   ### 最近完成（本会话提交窗口）
   ### 已归档版本 task（hot-fact-source 指针）
   ### 1.0.0 依赖链
   ## 版本规划  →  ### 版本路线图 / ### 版本 Gate（V-Gate）/ ### 版本规划纪律 / #### 版本号分配规则
                    #### 版本内容一致性规则 / #### 违规示例（来自实际教训）/ ### 版本里程碑
   ## 需求跟踪矩阵
   ## 变更控制（临时任务纳入机制）  →  ### 纳入流程（两条路径）/ #### 标准路径 / #### 快速通道
   ```
   即**被移除的两节（`## 版本规划`、`## 需求跟踪矩阵`）与被移除的 `### 1.0.0 依赖链` 正是这两项 FAIL 的判据对象**；同时消失的还有被这些节携带的 `0.38.0/0.37.0` 路线图行、`FIX-082~087`/`REL-013` 行、`REQ-059~064`/`REQ-070~074`。
4. **时点证据**：M-8 归档迁移于 **2026-09-14 20:00:08** 落盘（`.governance/archive/tasks/v0.1.0~v0.80.0.md` 头部逐字写 **「归档范围: plan-tracker.md 中 0.1.0~0.80.0 版本的所有 tasks」「条目数: 16」**，mtime/mtime 与 `decision-log.md`(20:00:08) 同批）；`check-archive-integrity` 实测 **Hot tasks (plan-tracker) = 0**。而 R1 在同日的 candidate 模式运行中，`release fact source` 与 `hot fact source` **均为 PASS**（R1 §7 行 15：静态/其余 PASS 17 项 + 执行面 3 FAIL = 7 issues，**无 hot/release fact source**）⇒ 失败**只能出现在 20:00:08 之后**。
5. **限制说明（不得据此编造）**：迁移前的 plan-tracker 快照**不可得**（`.governance/` 无 2026-09-14 备份；`plan-tracker.md` 自 `e19219a`「untrack governance runtime records」后**不在 git 中**，`git log -- .governance/plan-tracker.md` 仅回放旧版本）。因此我能证明的是**数据现状 + 判据 + 时点三项事实的严格吻合**，**不能**逐字回放 20:00:08 的写入动作。

#### 2.2.4 为何 `archive integrity` 仍 PASS（两者不矛盾，但暴露口径缺口）

`check-archive-integrity` 只验「hot + archived = 索引」的**计数守恒**（实测 `Hot 0 + Archived 91 = Total 91`，`Index entries 1148`，`[PASS]`）——它**不验 hot 文件是否保留了必需的活体节**。⇒ 归档迁移可以把 plan-tracker 削到只剩 7 个标题而该门禁仍 PASS。这解释了「归档完整性 PASS」与「hot fact source FAIL」并存。

#### 2.2.5 治理记录面的连带不一致（属证据诚实性）

`check-release` 的 `loop runtime claim gate` 输出里新增一条 `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: .governance/plan-tracker.md ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` —— 即归档迁移后的 plan-tracker 出现了**畸形表行**。该问题使 `loop runtime claim gate` 的失败条目从 4 条增至 5 条（与既有 `docs/release/release-checklist-0.81.0.md` 的 1 条 `AMBIGUOUS_SUBJECT_RELATION` 并列），进一步说明 `check-release` 的**当前**输出与 EVD-1038 所记"3 项残留"已不可互证。

### 2.3 ② 裁决

- `release-ledger`（含远端）**PASS**、`release lineage` **PASS**、`archive integrity` **PASS** ⇒ **发布事实层（declarative contract）成立**；
- 但**released 态 `check-release` 的实测结果为 14 PASS / 6 FAIL / 38 issues**，与 `EVD-1038.m6_gate` 所记「**16 项 PASS（含 release lineage 与 archive integrity）；residual_fail = 3 项全为既有基线**」**不一致**，且新增的 2 项 FAIL **未被任何发布文档或治理记录披露**；
- ⇒ ② 裁决：**未通过**。详见 **F-R2-01**（P1）。

### 2.4 3 组执行面残留的"既有基线"复核（我逐条复核，结论：同源，非本版引入）

| 残留 | 我的实测 | 是否既有基线 |
|---|---|---|
| `governance health` | `ISSUES FOUND — 84 issue(s)`（exit 1） | **是**（历史同族：0.76.0=112 / 0.77.0=103 / 0.78.0=127 / R1=96；**84 低于全部历史值** ⇒ 零增长，非本版引入）。**注意：数值为 84，非 EVD-1038 所记 91** |
| `unit tests` | `Command '[...python.exe', '-m', 'unittest', '…/test_verify_workflow.py', '-v']' timed out after 180 seconds` | **是**（代码事实：`verify_workflow.py:5946 _RELEASE_GATE_TIMEOUT_DEFAULT = 180`、`:6024`「unit tests」面**只跑** `test_verify_workflow.py` 单模块；同模块 discover 实测 258.1s > 180s 预算 ⇒ **确定性预算口径**，非 flake、非本版引入） |
| `loop runtime claim gate` | `semantic_verdict=BLOCKED; identity_verdict=FAIL; candidates=767; parsed=767` + 5 条明细（`AUTHORITY_SOURCE_OCCURRENCE: .governance/decision-log.md found 0`、同 plan-tracker、`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY`（plan-tracker ragged table row，**本轮新形态**）、`AMBIGUOUS_SUBJECT_RELATION`（本 checklist 自身 Gate 13 行）、3×`UNSUPPORTED_AFFIRMATIVE`（既有 `review-FIX-300-CODE-R0.md`，0.66.1 期）） | **是（FIX-320 族，0.66.1 期引入）**；但**本次多出 1 条 ragged table row**，来源 = §2.2.5 的 plan-tracker 畸形行 |

⇒ 「3 组执行面残留 = 既有基线」的定性**成立**（我逐条复核同意）；**不成立的是"只有 3 项"**。

---

## 3. ③ M-7 tag 与推送 —— **PASS（本地 + 远端 + 补推 + 无改写，全部实测）**

### 3.1 本地 annotated tag

| 判据 | 实测 | 结论 |
|---|---|---|
| `git cat-file -t v0.81.0` | `tag`（**annotated**，非 lightweight） | ✓ |
| `git rev-parse 'v0.81.0^{commit}'` | `e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3` = release commit | ✓ |
| tag 对象 | `71e27340aa1cbb7cf29a8cd9ca8eed91b04f19cb`，`object = e376ddf…`，`type commit`，`tagger peterwangze <…> 1789386850 +0800` | ✓ |
| `git for-each-ref --format='%(objecttype) %(objectname) %(*objectname)'` | `tag 71e27340aa1cbb7cf29a8cd9ca8eed91b04f19cb e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3` | ✓ |

> 记录一条**方法学坑（非产品缺陷）**：`git rev-parse v0.81.0^{commit}` 在 pwsh 下被解析为「转义序列 + `-encodedCommand`」，首次执行返回 **candidate `a89341e`**（属错误结果）。必须写 `git rev-parse 'v0.81.0^{commit}'`（单引号）才得到正确 peel。我已用引号版复测得 **`e376ddf`**，并以 `git cat-file tag` / `for-each-ref` 三重交叉确认 ⇒ 上面表格的结论是**引号版**结果。

### 3.2 tag message 内容裁决（**内容与发布事实一致，三项要求齐备**）

tag message（全文经 `git for-each-ref refs/tags/v0.81.0 --format='%(contents)'` 读出）关键段：

- 「授权链：DEC-189（架构）/ DEC-190（**M-0 范围 + ⑧ 真机路径 + ⑨ 发布预授权**）/ DEC-191 / DEC-192 / DEC-193 / DEC-194。**候选打包提交 a89341e；本 tag peel 到 transition 提交**。」⇒ 授权链与 §1 的 commit 事实**一致** ✓
- 「如实披露：**RISK-050 维持打开（不声明关闭）**；**真机三项由用户手动执行回贴，未回贴前标「未验证」**；既有失败基线（FIX-320 等）在 release 文档逐条披露。」⇒ **含"不声明 RISK-050 关闭" + "真机三项未验证"** ✓
- 「**保守边界**：不主张 official/marketplace approval、universal-full runtime support、external first-session pilot success、1.0.0 production-ready。」⇒ **含保守边界** ✓

**⇒ tag message 裁决：与发布事实一致，且三项要求（不声明 RISK-050 关闭 / 真机未验证 / 保守边界）逐条齐备。**

### 3.3 远端 tag + 补推义务 + master

```
git ls-remote --tags github-https 'refs/tags/v0.79.0*' 'refs/tags/v0.80.0*' 'refs/tags/v0.81.0*'
96a0030257d5d85c65447e2cc6e20b9eb65ac60c  refs/tags/v0.79.0
17eda4887a8eead7294239a2292c76e3f1b5cee1  refs/tags/v0.79.0^{}
131debec8fc2817b7c96539fafa0b7b8e888888a  refs/tags/v0.80.0
71f73ebcf837a5c52eb201866f8ce5adb66aee4f  refs/tags/v0.80.0^{}
71e27340aa1cbb7cf29a8cd9ca8eed91b04f19cb  refs/tags/v0.81.0
e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3  refs/tags/v0.81.0^{}

git ls-remote github-https refs/heads/master
e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3  refs/heads/master
```

| 判据 | 期望 | 实测 | 结论 |
|---|---|---|---|
| 远端 v0.81.0 = annotated 对象 + peel | tag 对象 + `^{}` = `e376ddf` | `71e27340…` + `e376ddf…` | ✓ |
| 补推：v0.79.0 存在且 peel = `17eda48` | `17eda4887…` | `17eda4887a8eead7294239a2292c76e3f1b5cee1` | ✓ |
| 补推：v0.80.0 存在且 peel = `71f73eb` | `71f73eb…` | `71f73ebcf837a5c52eb201866f8ce5adb66aee4f` | ✓ |
| `refs/heads/master` = release commit | `e376ddf` | `e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3` | ✓ |
| **本地/远端逐位一致**（三个 tag 的 **object** 与 **peel** 两侧全等） | — | v0.79.0 `96a00302…`/`17eda488…`、v0.80.0 `131debec…`/`71f73ebc…`、v0.81.0 `71e27340…`/`e376ddf8…` **两侧逐位相同** | ✓ |

**⇒ M-7 推送范围完整：master + 三个 tag（含 v0.79.0/v0.80.0 补推义务已履行）。**

### 3.4 「已推送 commit 被改写」风险面 —— **本轮无风险（我实测了三项）**

**风险事实（历史先例，我实测确认）**：`v0.80.0` 的 tag message 逐字写「**本地 tag，push 凭据阻塞（补推义务登记）**」，其 tag 对象 `131debec…`（指向 `71f73eb`）与 0.80.0 期回填记录里曾出现过的另一 object 不同 ⇒ **同族旧事确实存在**（授权后 tag 曾在错误 commit 上创建、未推送即删除重建；见 plan-tracker v0.80.0 行自述「授权后 tag 曾在错误 commit 上创建、未推送即删除重建（本地 tag，无已发布 tag 重指）」）。

**本轮三项实测（均无改写痕迹）**：

1. **推送是 fast-forward，非 force-push**：EVD-1038 记推送前的远端 master = `ce7fa79`。我实测 `git cat-file -t ce7fa79` = `commit`、`git merge-base --is-ancestor ce7fa79 e376ddf` = **exit 0（真）**，`git rev-list --count ce7fa79..e376ddf` = **79** ⇒ 新 master 是旧 master 的**严格后代**，远端不需（也不应）出现非 fast-forward 更新。✓
2. **本地曾被 reset 丢弃的 transition 提交，均不在已发布历史中**：`git reflog show master` 显示 19:47:24–19:50:59 存在 `da473aa`（commit）、`18d5159`（amend）、`29b39b4`/`1241b50`（reset 目标）等中间态，最终于 19:52:48 由 `a89341e` 重新提交为 `e376ddf`。我逐个实测 `merge-base --is-ancestor <c> e376ddf`：`da473aa`=False、`29b39b4`=False、`1241b50`=False、`18d5159`=False ⇒ 这些**本地被丢弃的提交都不在已推送历史中**；结合 1（fast-forward 且远端旧值 `ce7fa79` 为祖先），可判定**远端从未承载过它们**。✓
3. **`v0.80.0` 旧事未在本版重演**：远端 `refs/tags/v0.80.0^{}` = `71f73eb`（与本地 `git rev-parse 'v0.80.0^{commit}'` 逐位一致）、`refs/tags/v0.81.0^{}` = `e376ddf`（与本地一致）⇒ **无已发布 tag 重指**。✓

**⇒ ③ 裁决：M-7 完整且无改写风险面。**（本项为我主动加做的核验，非任务明列项；证据链见 §7 行 13–16、19。）

---

## 4. ④ M-8 归档与治理记录 —— **归档完整性 PASS；真实环境面零 overclaim；但发布收尾有 2 处未闭合**

### 4.1 `check-archive-integrity` —— **PASS**

```
=== Archive Integrity Check (SYSGAP-030 Check 27) ===
  Hot tasks (plan-tracker): 0
  Archived tasks: 91
  Index entries: 1148
  Total tasks (hot + archive): 91
  [PASS] Archive integrity verified.
---exit=0
```

- 与 EVD-1038 自述「发布后归档 **16 task** + 11 evidence + 2 decision，`check-archive-integrity` PASS」**方向一致**：归档任务文件 `.governance/archive/tasks/v0.1.0~v0.80.0.md` 头部逐字写「**条目数: 16**」「**归档日期**: 2026-09-14」（mtime 20:00:08）✓；evidence/decision 归档文件 `evidence-v0.1.0-0.80.0.md`(30,967 B) 与 `decisions-v0.1.0-0.80.0.md`(8,211 B) 同批落盘 ✓。
- **计数口径差异（我实测值 vs 记录）**：EVD-1038 的 `事实依据` 列写「**Index 1148**」（与实测**一致**），而 `m8_archive` 字段写「发布前 … **Index 1119**；发布后归档…」（1119 与实测 1148 差 29）；`checklist:91` 另记「Index **1119** / Total **180**」。⇒ 同一事实出现 **1119 / 1148** 两个索引计数与 **180 / 91** 两个总量口径。**归档完整性结论不受影响**（PASS），但记录面口径不唯一（见 F-R2-02 的同类问题与 §5 观察 O-3）。

### 4.2 治理记录面（`.governance/`，**我全程只读**）

- **`EVD-1038`（REL-077 / 发布 / 2026-09-14）是否存在且如实记录发布动作** —— **是**，且字段齐备：`candidate_commit: a89341e`、`transition_commit: e376ddf`、`transition.parent = "a89341e（单父，满足 ledger 判据）"`、`event.integrity = sha256:d475a2b1…65a7`、`canonical_bytes = "NFC + 键排序 + 紧凑分隔符 + 单尾 LF（813 bytes）"`、`tag.{name,type,object,peel,remote_peel}`、`m6_gate`、`push.{remote:"github-https", master:"ce7fa79..e376ddf", tags_created:["v0.79.0","v0.80.0","v0.81.0"], back_push_obligation:"已履行"}`、`m8_archive`。**逐项与我的实测相符**（813 bytes ✓、integrity ✓、object `71e27340` ✓、peel `e376ddf` ✓、remote_peel `e376ddf` ✓、master 新值 ✓、三 tag ✓）。
  - **唯一不实项 = `m6_gate`**：`{"release_ledger_remote":"state PASS / trust NATIVE_RELEASED / issues 空"（✓ 我复现一致）, "check_release_released":"**16 项 PASS**（含 release lineage 与 archive integrity）", "residual_fail":"**3 项全为既有基线**：governance health **91 issues** / unit tests 180s 预算 / loop runtime claim gate semantic BLOCKED"}` —— 我复跑为 **14 PASS / 6 FAIL / 38 issues**、`governance health` = **84**。⇒ 见 **F-R2-01**。
- **`EVD-1039`**：发布完成后的 `task-priority-analysis --force` 快照已记录（Total 25 / 12 completed / 9 unblocked / 4 blocked / top_pick FIX-323；推荐 FIX-336/332/333/337）⇒ **M7.4 step 6 义务在发布收尾场景履行**，我确认存在且内容自洽 ✓。
- **`plan-tracker` 的 REL-077 行是否已转 ✅ 已发布且与 git 事实一致** —— **是**（两处）：
  - `plan-tracker.md:44`（项目总览行的 0.81.0 段）：「…**0.81.0** 已发布 **2026-09-14 REL-077**…候选 `a89341e` → transition `e376ddf` → annotated tag `v0.81.0`；**已推送 github-https**（含 v0.79.0/v0.80.0 补推）；RISK-050 维持打开」⇒ **与 §1/§3 的 git 事实逐项一致** ✓（但同一行保留了一句**滞后表述**：「发布半面 Release Reviewer **待执行**」——其已由 R1 执行完毕，属行内残留，见 O-3）。
  - `plan-tracker.md:88`：「✅ **已发布 2026-09-14（REL-077）**——M-1 候选打包 `a89341e`（35 文件 +1251/−110）→ **M-2** 门禁 14 项实测…→ **M-3** 双半面审查…→ **M-5** transition 提交 `e376ddf`（单父 = 候选…）」⇒ **与 git 事实一致** ✓。
  - `plan-tracker.md:11`「工作流版本: **0.80.0**（已发布 2026-09-12 REL-076…）」：该字段语义为**已安装/已记录版本行**（v≥0.66.0 起「发布动作不 bump 版本号」，由 release note 行承载发布状态），且 `check-version-consistency` 把 0.80.0 的 `plan-tracker` 残留列为 **WARN** 而非 FAIL；本版 `check-version-consistency` 实测 **PASS**。⇒ **不构成发布缺陷**，但「M-8 转 0.81.0」的义务在该字段上**未执行**（见 O-3）。
  - **计划表状态列的连带缺口（我实测）**：`REL-077` 在 plan-tracker 中的**任务行**仍为「**发布半面 Release Reviewer 待执行**」（`:44`），且 `REL-077` **已不在 hot task 表**（`check-archive-integrity` = `Hot tasks 0`；REL-077 落 `archive/tasks/v0.1.0~v0.80.0.md`）⇒ 归档把「最新已发布版本」本身也移出 hot（与 `archive.py` 自述口径"保留最新已发布版本"不一致），REL-077 的 ✅ 行仅存于 `:88`。

### 4.3 **真机三项：全库无任何文档声明其通过** —— **确认（我做了三向 grep）**

- 三向 grep（`真机.{0,40}(通过|PASS|已验收|验收通过)` / `三项.{0,30}(通过|完成)` / 发布面文档定向）共 17 处命中，**逐条查看无一是"已通过"声明**：
  - 全部为**禁止性/未验证**表述：`CHANGELOG.md:35`「回贴前 release 文档 MUST NOT 声明真机项通过，未回贴项标「未验证」」；`release-checklist:138`「**状态**：⟦待用户回贴⟧…MUST NOT 声明真机项通过；未回贴项 MUST 标「未验证」」；`:157`「回贴前严禁在任何 release 文档/CHANGELOG 中声明真机项通过」；`real-machine-acceptance:101`「MUST 逐项标注 `未验证` / `FAIL`，不得写 PASS」；`version-plan:135`「本版**不声明**…真机三项验收通过（除非用户手动执行并回贴证据）」；`CHANGELOG:35` / `checklist:9,10,11`（保守边界声明的 no-overclaim 段）；其余为 **R0/R1 两轮审查报告自身**对本项的核验记录（属评审历史，非产品声明）。
  - **我额外核了"发布动作是否被误当作真机验证"**：tag message 显式写「真机三项由用户手动执行回贴，**未回贴前标「未验证」**」；`check-dsh-boundary` 的 K-7 为 `NOT_RUN`（按设计，`verified_on = null`）；README 的 `github:` 安装形态自标「〔static: github: form — packaging semantics by reasoning, not install-verified〕」⇒ **无一处把隔离冒烟 / 静态推理包装成真机通过**。
- **⇒ 真机三项：全库零"通过"声明，标「未验证」** ✓（符合任务要求"未回贴 ⇒ 必须标「未验证」"）。

### 4.4 ④ 裁决

**归档完整性 PASS ✓ / EVD-1038 与 plan-tracker REL-077 行与 git 事实一致 ✓ / 真机零 overclaim ✓**；但发布收尾有 **2 项未闭合**（`F-R2-02` 回滚方案发布 tip 未回填；`hot/release fact source` 未收口见 `F-R2-01`），且记录面存在**陈旧残留**（`F-R2-03` README）。

---

## 5. ⑤ R1 的 P3 收口项逐条确认（F-R1-01~05 与最小清单 ①~⑥）

### 5.1 R1 的 5 条 P3 findings

| ID | R1 诉求 | **本轮裁决** | 事实依据（我的独立复核） |
|---|---|---|---|
| **F-R1-01** | 补 EVD supersede 声明（EVD-1034 `14_rollback_plan` 旧口径作废） | **✅ 已落地** | `evidence-log.md:2076`（EVD-1034）该字段现为：「已交付且可执行（区间 = d87ead8..**发布 tip**；实测计数 d87ead8..a89341e=**33** / ..22cf185=**34**；原写 31+本提交=32 **少 1**，已由 REVIEW-REL-077-RELEASE-R0 **F-03 更正**；**本条于 R1 复审后 supersede：见 FIX-334/EVD-1036 与 release-checklist Gate 14**）」⇒ **旧口径已就地作废并指向终值** ✓（R1 要求的逐字语义均已具备） |
| **F-R1-02** | 三处计数口径漂移就地收口：①Gate 10 两次取数对帐 ②Gate 13 并存 6/7 ③「静态面 13/13」标签 | **✅ 已落地** | ①`checklist:123` 新增「**差集汇总（块级）与口径对帐（REVIEW-REL-077-RELEASE-R1 F-R1-02）**」，明写「快照口径（FIX-335 之前）候选 **38** 块 = 双侧共有 29 + 候选侧特有 9」「**当前口径**候选 **36 块 = 38 − 2**」「38 − 4 = 34」，并加「**勿再以单一数字互证**」✓；②同段给出「**F/E 分类口径（F-R1-05）**」表，明写两侧 F/E 分类互换原因与「三例均红一致」✓；③`checklist:91` 已改为「**以工具打印的 PASS 行数为准确口径**」并列出 17 个具名 PASS 项，删除「13/13」计数 ✓。我复跑 `check-release` 确认印刷项名与之一致（14 项同层 + 子项）✓ |
| **F-R1-03** | 删残留尾句（归因分级第 3 条 ① 的「建议登记独立 FIX」）+ 显式声明送审版本 = working tree | **◐ 部分落地** | **尾句已收口**：`checklist:132` 现为「…属**第 4 例版本钉腐朽**…——**本版已由 FIX-335 修复**（**已由 FIX-335 修复**；本条保留以记录发现时点，**其「建议另立 FIX」的措辞已被本句覆盖**），**建议登记独立 FIX**；② `test_dsh_compat` …建议登记独立 FIX（收集面缺陷，双侧同现）」。⇒ 前半（第 4 例）已明文覆盖，**其余仍是一句未被覆盖的"建议登记独立 FIX"**（对象为 `test_dsh_compat` 收集面缺陷 = FIX-336，仍待登记），**不再自相矛盾但保留了一句建议**——按 R1 原意（"删去该尾句"）属**部分**。**送审版本声明**：本轮为发布后核验，送审对象已由 §3 的 tag/commit/master 逐位固定（无 working tree 歧义），该项**不再适用**（不判缺陷） |
| **F-R1-04** | ①CHANGELOG「无默认行为破坏」→「无 MUST 规则/Gate 语义破坏」 ②README 补「包含真实 home 的父目录亦被拒」 | **◐ 部分落地**（①为**可选**、②的实质**已含**） | ①`CHANGELOG.md:37` **仍写**「**Breaking changes：无**（…口径：无接口删除/重命名、**无默认行为破坏**、无 Gate 语义或治理字段格式变更）」⇒ R1 建议的替换措辞**未采纳**；但紧接同句即列「**行为变更（升级须知，2 项）** B-1/B-2」（含"由可用改为 exit 2 + [REFUSED]"）⇒ **读者可见的实质信息完整**，R1 亦标为「（可选）」⇒ 判**部分（可接受）**。②README **未逐字**写"父目录"，但 `README.md:85` 已写「unless `DSH_HOME` is explicitly set to a directory **outside your real home tree**」⇒ 语义**覆盖**「包含真实 home（父目录）」的拒绝面（"outside your real home tree" 即"不得落在真实 home 之内或其父"），且同段给出「a deliberate manual install MUST redirect `DSH_HOME` to a temporary directory」⇒ **实质已落地**，仅未按 R1 拟的逐字措辞 |
| **F-R1-05** | 候选/pristine 定向重跑的 F/E 分类计数不同：建议 M-4 同命令并列两侧原始输出，勿用「同结果」 | **✅ 已落地** | `checklist:127` 新增独立限定段「**F/E 分类口径（REVIEW-REL-077-RELEASE-R1 F-R1-05）**：本表对 FIX-320 三例的 pristine 侧定向重跑，评审方实测为 `failures=1, errors=2`，而本表记 `failures=2, errors=1` —— **三例均红一致**，仅 **Fail/Error 分类**因运行口径（是否 `-v`、unittest 对 `SystemExit` 的归类）不同而互换…**逐字比对时请勿以「同结果」表述两者的 F/E 分布**」✓ 逐字采纳了评审方数值与禁令 |

### 5.2 R1 最小待办清单 ①~⑥

| # | R1 动作 | 覆盖 | **本轮裁决** | 事实依据 |
|---|---|---|---|---|
| **①** | M-4 复跑 `check-release` 与全量测试，**以当场值为唯一口径**刷新 Gate 10（38/36）、Gate 13（6/7）与「静态面 13/13」标签 | F-R1-02 / F-09④ | **◐ 部分落地（公式已收口，但"当场值"未覆盖 released 态）** | Gate 10 已改为 38/36 双口径 + 对帐（✓）；Gate 13 已改为"以工具印刷行数为准"+ 17 具名项（✓）；但 **released 态的实际输出为 6 FAIL / 38 issues**，文档未刷新（**F-R2-01**）。R1 还要求"M-5 打 tag 前 MUST 复跑一次门禁并以当场值为准"⇒ **tag 之后门禁被 M-8 归档改变，未见复跑留证**（这是本轮 P1 的直接成因） |
| **②** | 补 EVD 行 supersede 声明（EVD-1034 `14_rollback_plan` 旧口径作废） | F-R1-01 | **✅ 已落地** | 见 5.1 F-R1-01 |
| **③** | 删 residual 尾句 + 声明送审版本 = working tree | F-R1-03 | **◐ 部分（尾句保留、送审版本项不适用）** | 见 5.1 F-R1-03 |
| **④** | （可选）CHANGELOG「无默认行为破坏」→「无 MUST 规则/Gate 语义破坏」；README 补父目录面 | F-R1-04 | **◐ 部分（两条均为「可选」，实质信息齐备）** | 见 5.1 F-R1-04 |
| **⑤** | （**可选**）由具写权限者补跑一次**隔离 revert 干跑**并留证 | F-04 复跑项 | **✅ 已落地（记录在案）** | `rollback-plan-0.81.0.md` §4/§4.1 保留 ups 两次干跑记录（候选点：**0 冲突 / 80 路径**；tip：**3 冲突 / 35 路径 = 5 D + 27 M + 3 UU**），并在 `:36-44` 给出"终点为什么必须是发布 tip"的完整论证（F-04）✓。**注**：我仍未复跑该干跑（需写权限 + 隔离 worktree，超出本轮只读边界，且 R1 已判定"记录存在 + 每一数字可从树结构精确导出"）；本轮 R1 只要求"留证"，已满足 |
| **⑥** | FIX-336 修复时同步把限定语写进 Gate 10 **行标题/结论句**（若 FIX-336 未做，只确认限定语要求已被记录） | 新增事实③ | **✅ 已落地（以"已被记录"标准满足）** | 限定语**已进入 Gate 10 行的 Result 单元格结论句**：`checklist:88` 的 Gate 10 行明写「…`Ran 2983 tests` — **该模块的 120 用例在本模式下整体未被收集（"Ran 2983" 不含它们…）**」且明细段行 #12 与归因⑤复述；另 `:123` 把口径差额写为「本口径不含题 #12 的 test_dsh_compat 120 用例」等价表述 ⇒ 满足"若 FIX-336 未做，只确认限定语要求已被记录"。FIX-336 本身**仍未做**（`plan-tracker:93` 仍列为高优候选 / EVD-1039 推荐首位）——**不属本轮缺陷** |

**F-R1-01~05 汇总：✅ 2 项（F-R1-01 / F-R1-05）、◐ 3 项（F-R1-02 实质收口但被新事实覆盖、F-R1-03 部分、F-R1-04 部分且均为可选项）；R1 最小清单 ①~⑥：✅ 3 项（②⑤⑥）、◐ 3 项（①③④）。**

### 5.3 前轮 F-01（R0 的 blocking）在**已发布树**上的复验

| R0/R1 finding | 我的独立复跑（**已发布树 = e376ddf**） | 裁决 |
|---|---|---|
| F-01：`test_dsh_doctor.py` 渲染 sha256 硬钉腐朽 | `python -m unittest …tests.test_dsh_doctor`（`DSH_HOME` → `%TEMP%\spg-r2-doctor-690ae8f5`）= **Ran 86 tests in 35.383s / OK** | **已修复且在已发布树成立** ✓ |
| FIX-335（第 4 例版本钉腐朽，`test_archguard_ratchet` 豁免 fixture） | `python -m unittest …tests.test_archguard_ratchet`（`DSH_HOME` → `%TEMP%\spg-r2-arch-20e7a470`）= **Ran 38 tests in 115.749s / OK** | **已修复且在已发布树成立** ✓ |
| Gate 10 的 38 块明细 / F-02 逐条清单 | `checklist:94-133` 段存在、可分块复算（R1 已逐块核 22+2）；我复核了 `#4/#5` 现已在候选态消失（FIX-335）✓ | **已落地** ✓ |

⇒ **R0 的唯一 blocking 项在已发布树上确实闭环、测试确实绿**——这一点**没有被 F-R2-01 推翻**：F-R2-01 讲的不是"测试红"，而是"**released 态门禁结果被记录成 16 PASS / 3 残留，实为 14 PASS / 6 FAIL / 38 issues，且 2 项新失败未披露/未修**"。

---

## 6. 硬门槛逐条裁决（`agents/release-reviewer.md`）

| 门槛项 | 阈值 | **本轮裁决** | 依据 |
|---|---|---|---|
| **发布检查清单全部 PASS / 逐项有可复核证据** | = 100% | **未满足（NEEDS_CHANGE）** | ①14 项表内条目本身证据齐备（R1 已核、我抽核 Gate 6/7/10/14 值可信、Gate 14 计数不写死 ✓）；②**但"发布态门禁"这一自证链断裂**：released 态 `check-release` 实测 **6 FAIL / 38 issues**（含 2 项新失败），而 `checklist`(无 release 态复跑记录) / `EVD-1038`（记 16 PASS / 3 残留）与之**矛盾** ⇒ 清单的"全部 PASS"声明在**当前已发布树**上不成立、且"逐项有可复核证据"对新增失败项缺失。**另**：回滚方案的发布 tip 未回填（6 处占位）使其"可执行"性存在未闭合点（虽可从上下文推断） |
| **回滚方案存在且已验证** | = 已验证 | **满足（有保留）** | 方案存在 + §4/§4.1 两次隔离 worktree 干跑记录在案（0 冲突/80 路径；3 冲突/35 路径 = 5D+27M+3UU），且其数字与树结构一致（R1 已逐项导出，我认可）✓；**保留**：`<发布 tip>` 未替换为实际 hash（6 处），终点语义可从上下文（"M-5 生成的 transition 提交"= `e376ddf`）唯一确定 ⇒ **不构成阻塞**，列为 F-R2-02（P2） |
| **CHANGELOG 用户视角完整** | 关键段全部覆盖 | **满足** | `CHANGELOG:5-39` 含范围/AUDIT-153/FEAT-028~031/FIX-311~317·319·321/行为变更 B-1/B-2/既有失败披露/RISK-050 不声明关闭/真机未验证/显式 `**Breaking changes：无**`；用户视角完整 ✓（措辞选项见 5.1 F-R1-04①） |
| **breaking changes 已标注** | = 100% | **满足** | 显式结论行 + B-1/B-2 升级须知（`CHANGELOG:37` + `feature-flags §2` + `checklist:67-71`）✓；`VERSIONING.md:11` 口径下"无 breaking"成立 ✓ |
| **Feature Flag 关闭验证** | 全部通过 | **满足** | 新增 opt-in 开关 = 0 ✓（`feature-flags §1/§3`）；B-1/B-2 回退路径 = 版本回滚且文档写明 ✓；写入守卫无 Kill Switch 已如实登记 FIX-324 ✓；`loop fuse block` PASS ✓ |

**⇒ 硬门槛 2 项不满足（清单证据 100% / 发布态门禁自证一致）⇒ 结论 `NEEDS_CHANGE`。**

---

## 7. Findings

### F-R2-01 — **P1（blocking）** — released 态门禁被记录为「16 PASS / 3 项既有残留」，**实为 14 PASS / 6 FAIL / 38 issues**，且新出现的 `release fact source` / `hot fact source` 2 项失败未被任何发布文档或治理记录披露

- **位置**：`.governance/evidence-log.md:2090`（**EVD-1038** `m6_gate`，本轮被审的新证据行）；`docs/release/release-checklist-0.81.0.md:91`（Gate 13，无 release 态复跑记录）；连带 `docs/release/release-checklist-0.81.0.md:73-92`（M-2 表口径）
- **事实依据（全部由我独立复跑 / 复算）**：
  1. `python …/verify_workflow.py check-release --version 0.81.0 --require-changelog --lineage-mode released --release-commit e376ddf --lineage-remote github-https` ⇒ **`Result: FAILED - 38 issue(s)`，exit 1**；FAIL 项 = `release fact source`（9）+ `hot fact source`（24）+ `execution gates`（含 `governance health` exit 1 = **84 issues**、`unit tests` 180s 超时）+ `loop runtime claim gate`（BLOCKED/identity FAIL）
  2. `python …/verify_workflow.py check-release --version 0.81.0 --require-changelog --lineage-mode candidate`（**同一工作树对照**）⇒ **逐项相同**：同 2 项 FAIL、同 `FAILED - 38 issue(s)`、同 exit 1 ⇒ **与 lineage 模式无关的确定性失败**（非偶发、非模式特例）
  3. 判据代码：`verify_workflow.py:2011-2023` 要求 hot 节 `## 项目配置/## 项目总览/## 当前活跃事项/## 版本规划/## 需求跟踪矩阵`（dogfood 追加 `### 1.0.0 依赖链`）；`plan-tracker.md` 实测**仅 7 个标题**，缺 `## 版本规划`/`## 需求跟踪矩阵`/`### 1.0.0 依赖链` ⇒ 三项"missing hot fact-source section"逐字可解释
  4. 对照备份：`.governance/backups/governance-backup-20260910-prefix301/plan-tracker.md`（364,114 B，2026-09-10）**含全部三节**（`## 版本规划` + `## 需求跟踪矩阵` + `### 1.0.0 依赖链`）以及 `0.38.0/0.37.0` 路线图行、`FIX-082~087`、`REL-013`、`REQ-059~064`、`REQ-070~074`——**与当前 FAIL 清单逐项互为补集**（标题差集实测列出被移除的 10 个节/子节）
  5. 时点：M-8 归档迁移落盘 **2026-09-14 20:00:08**（`archive/tasks/v0.1.0~v0.80.0.md` 头部「归档范围: plan-tracker.md 中 0.1.0~0.80.0 版本的所有 tasks / 条目数: 16」；`decision-log.md` 同 mtime）；`check-archive-integrity` 实测 **`Hot tasks (plan-tracker): 0`**；而 R1 于同日 candidate 模式运行时 **`release fact source` 与 `hot fact source` 均 PASS**（R1 §7 行 15 + §1 F-09① 仅列 7 issues）⇒ 两项失败**必在 20:00:08 之后才出现**
  6. **诚实边界（不编造）**：迁移前快照不可得（`plan-tracker.md` 自 `e19219a` 起不在 git；`.governance/` 无 2026-09-14 备份）⇒ 我把成因表述为**"判据 + 数据现状 + 时点三者的严格吻合，且 R1 时点为 PASS"**，而非逐字回放写入动作
- **影响**：
  1. **发布自证链断裂**：以"零校验不得 PASS / 严格看护"为本版主题的 0.81.0，其**已发布态**的门禁实测与治理记录（EVD-1038）**互斥**——EVD-1038 是公开可复核的"发布完成"证据行，其 `m6_gate` 字段现在**不实**；
  2. **两项失败未进任何风险/任务账**：`release fact source`（含 `architecture.md:445` overstate）与 `hot fact source`（24 条）既未在 checklist 披露，也未见登记 FIX/RISK ⇒ 治理记录出现"门禁红而无账"的空白；
  3. **热文件被削至 7 个标题**（`Hot tasks = 0`）：`## 版本规划`/`## 需求跟踪矩阵`/`## 变更控制` 与 `1.0.0 依赖链` 均消失，连带 `loop runtime claim gate` 新增 `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row`（失败条目 5 条）⇒ 后续会话的 bootstrap 事实源（Gate 状态/活跃事项/路线图）与"变更控制快速通道"记录面**受损**（治理数据面，不改变已发布 git 产物）；
  4. **重复触发面**：只要 hot 节不恢复，后续每次 `check-release` 都会复现该 2 项 FAIL，且会污染下一版本的发布门禁基线
- **不可逆性说明**：本项**不涉及重打 tag / 重推**（git 产物本身正确，见 §1/§3）⇒ 修复**可逆**（补齐 plan-tracker 热节 + 复跑 + 更新记录），无需用户授权破坏性操作
- **建议（最小补救）**：① 恢复 `plan-tracker.md` 的 `## 版本规划`（含 `## 变更控制`）/`## 需求跟踪矩阵`/`### 1.0.0 依赖链` 三个必需热节（可从 2026-09-10 备份取结构、以当前版本事实重写，勿直搬旧数字）；② 修复迁移产生的 ragged table row；③ 就地登记 `release fact source`（`architecture.md:445` overstate）与 `hot fact source` 的归属（FIX 或 RISK）；④ **复跑 released 态 `check-release` 并把当场输出贴入 checklist Gate 13 与 EVD-1038（或追加 EVD supersede 行）**，把"16 PASS / 3 残留"更正为实测值

### F-R2-02 — **P2** — 回滚方案的**发布 tip 未回填**（6 处 `<发布 tip>` 占位）且 checklist Gate 14 亦未写入 release commit hash

- **位置**：`docs/release/rollback-plan-0.81.0.md:32,34,35,37`（+ `:44` 等，实测 `<发布 tip>` 共 **6 处**）；`docs/release/release-checklist-0.81.0.md:92`（Gate 14）
- **事实依据**：`Select-String -Pattern "e376ddf" docs/release/rollback-plan-0.81.0.md` = **零命中**；同命令对 `release-checklist-0.81.0.md` = **零命中** ⇒ 最终发布提交 hash **未写入这两份已发布文档**；`rollback-plan:34` 逐字写「终点 = **发布 tip**（M-5 transition 提交；**其 hash 由 M-5 生成后回填，不预先编造**）」⇒ **回填义务由文档自身声明，而 M-5/M-8 未执行**
- **影响**：事故时执行者需自行把 `<发布 tip>` 解析为 `e376ddf`（可从 `git rev-parse v0.81.0^{commit}` 唯一确定，故非致命）；但已发布文档含 6 处未闭合占位，与"发布文档冻结"纪律（R0 F-06 已因残留 ⟦⟧ 判过同类问题）不一致；对以"证据完整"为主题的版本属**公开面瑕疵**
- **建议**：M-8 收尾补回填（`d87ead8..e376ddf`，并注明该 hash 由 `release-ledger` 的 `release_commit` 派生），同步在 Gate 14 写入终值；若坚持"不写死计数"，至少写入**端点 hash**（计数可仍留现场取）

### F-R2-03 — **P2** — 已发布树 `README.md:94` 的推送状态陈述**与 git 事实相反**（"not yet pushed" / "master still serves 0.78.1"）

- **位置**：`README.md:94`
- **事实依据（逐字 vs 实测）**：
  - README 原文：「Note on `github:`: `v0.79.0` and `v0.80.0` are **tagged locally** … but **not yet pushed to the remote** (**no push has been performed as part of this release preparation**) … GitHub's master therefore **still serves 0.78.1** (last pushed state), and the `github:` install form becomes available only **after that M-7 push**」
  - 实测：`git ls-remote --tags github-https` ⇒ `refs/tags/v0.79.0^{}` = `17eda48`、`refs/tags/v0.80.0^{}` = `71f73eb`、`refs/tags/v0.81.0^{}` = `e376ddf` **三者均已在远端**；`git ls-remote github-https refs/heads/master` = **`e376ddf`**（非 0.78.1）；`EVD-1038.push.master = "ce7fa79..e376ddf"`、`tags_created = ["v0.79.0","v0.80.0","v0.81.0"]`、`back_push_obligation = "已履行"`
  - ⇒ README 的「未推送 / master 仍是 0.78.1 / github: 形态要等推送后才可用」**三项均已过时且方向为"低估可用性"**
- **影响**：README 是用户第一入口（`github:` 安装形态）；该陈述会**劝退用户认为 github 形态不可用**，与已完成的 M-7 事实相反。虽属"保守方向"（不夸大），但属**可复核的不实陈述**，且 R0/R1 两轮均以"README 与代码行为逐字一致"为质量要求。**注**：用户可见且已推送到远端 master 与 tag ⇒ 纠正需**新提交**（不涉及重打 tag/重推历史）
- **建议**：以一次文档提交更新该段为「`v0.79.0`/`v0.80.0`/`v0.81.0` **均已推送**（`master` = `e376ddf`；`github:` 形态自 2026-09-14 起可用）」，并把"未推送"表述移入历史（v0.80.0 期事实）；同批修订 `release-checklist:142`（M-8 收尾义务仍写"**从未推送**⇒ 本版 M-7 推送时 MUST 一并补推"）为"已履行 + 证据 = EVD-1038.push"

### F-R2-04 — **P3** — 已发布文档/记录中的陈旧残留与口径不唯一（不阻断）

1. **`plan-tracker.md:44` 行内残留**：「发布半面 Release Reviewer **待执行**」——该审查已于 2026-09-14 完成（R1 `APPROVED_WITH_NOTES/0`，`review-REL-077-RELEASE-R1.md` 入 `e376ddf`），同文件 `:88` 已写"→ **R1 APPROVED_WITH_NOTES / unresolved_blockers=0（可进入 M-4/M-5）**" ⇒ **同行自相矛盾**（R1 已处理同类问题 F-R1-03 于 checklist，此处为 plan-tracker 面的同型残留）
2. **索引/总量计数两个口径**：`EVD-1038.事实依据` 写 "Index **1148**"（= 我实测 1148 ✓），而 `EVD-1038.m8_archive` 写 "发布前 … Index **1119**"、`checklist:91` 写 "Index **1119** / Total **180**"；`check-archive-integrity` 实测 **Index entries 1148 / Total tasks 91** ⇒ 同批记录的索引计数与总量口径不唯一（1119 vs 1148；180 vs 91）
3. **`governance health` 三值并存**：R1 实测 96、EVD-1038 记 91、我实测 **84** ⇒ 活体数据面漂移（方向 = **改善**，非恶化）；因属活体治理记录面，不判缺陷，但 headline 数字宜标注取值时点
4. **`release-checklist:142`（M-8 收尾义务）**「tag **从未推送**」在推送完成后**未更新**（并入 F-R2-03 同批修订即可）
5. **`<发布 tip>` 占位**：见 F-R2-02（单列）

---

## 8. 观察（非缺陷，但影响后续判断）

- **O-1（P3）`e376ddf` 是"打包提交"而非纯 transition 提交**：11 文件含 `22cf185` 的门禁收口、FIX-334/335 的 2 个测试文件、3 份审查报告入库。规范（`release-checklist:68` / `stage-release:58,115`）只要求"单父 + parent=candidate + 恰一事件"，故**不构成缺陷**（`claims.derivation` 的 manifest 面语义已由 §1.5 证实）；但副作用是 **`22cf185` 从历史中消失**（R1 报告 §0.1 以其为基线，其"送审版本"在当前历史中已不可检出）⇒ 复审的可追溯性下降，建议后续版本把"release transition"与"审查退回修复"分成两个提交。
- **O-2（P3）判据"当场值"未覆盖发布态**：R1 要求"以当场值为唯一口径"刷新，但**tag 之后**若有任何数据面变更（本例：M-8 归档），门禁结果会再次变化 ⇒ 建议把"**M-8 收尾后复跑 released 态门禁**"写成 M-8 的显式义务（现文本只要求"ledger 核对 / plan-tracker 版本行转 released"）。
- **O-3（P3）`plan-tracker` 工作流版本字段**：`:11` 仍 `0.80.0`（`check-version-consistency` 判 WARN 非 FAIL，本版实测 PASS）；按 v0.66.0 起的"发布动作不 bump 版本号"语义属**合规**，但 M-8 自述的"plan-tracker 版本行转 released"在该字段上**未执行**——发布状态实际由 `:44`/`:88` 的版本注记行承载。建议明确字段语义以免后续审查反复追问。
- **O-4（P3）`unit tests` 门禁在当前默认配置下恒不绿**：单模块 `test_verify_workflow.py` 预算 180s（`verify_workflow.py:5946`）< 实跑墙钟 ≈258s（`:6024`）⇒ 建议提高默认预算或改用可配置 discover 口径，使"发布门禁全绿"成为可达目标（否则每次发布都要以"既有基线"豁免该项）。

---

## 9. 独立复现声明（我亲自复算/复跑的项）

**亲自执行（命令结果，非文档采信）**：

1. **event integrity 独立复算**：自实现 canonical（NFC + sort_keys + 紧凑分隔符 + ensure_ascii=False + 单尾 LF）→ 对"去 integrity 键"的 payload 取 `[:-1]` 后 sha256 = `sha256:d475a2b1…65a7` = 清单声明值 ✓；并用 `ledger.event_integrity` 对照相同 ✓。
2. **canonical 字节判定**：`canonical_json_bytes(manifest) == 文件原始字节` = **True**（813 bytes）；`parse_canonical_manifest_bytes` 通过 ✓。
3. **transition 形态**：`git rev-list --parents -n 1 e376ddf` = 单父 `a89341e`；`git diff a89341e e376ddf -- 0.81.0.json` = 1 行、仅 candidate→released + events 追加 ✓。
4. **M-6 ledger**：`release-ledger --version 0.81.0 --remote github-https` = `state PASS` / `NATIVE_RELEASED` / `issues []` / `candidate_commit a89341e…` / `release_commit e376ddf…` / `candidate==release` tag 两面一致 ✓。
5. **M-6 check-release ×2 模式**：released 模式（`--release-commit e376ddf --lineage-remote github-https`）= **14 PASS / 6 FAIL / 38 issues**；candidate 模式（同工作树）= **逐项相同** ✓（两项对照）。
6. **M-7 本地 tag**：`git cat-file -t v0.81.0` = `tag`；`git rev-parse 'v0.81.0^{commit}'` = `e376ddf…`；`git for-each-ref` = `tag 71e27340… e376ddf…`；tag message **全文读入并逐条裁决**（授权链 / RISK-050 不声明关闭 / 真机未验证 / 保守边界五项 token 齐备）✓。
7. **M-7 远端 tag + master + 补推**：`git ls-remote --tags github-https`（v0.79.0/v0.80.0/v0.81.0 各含 annotated 对象 + `^{}` peel）= 期望值；`git ls-remote github-https refs/heads/master` = `e376ddf`；**本地/远端 object 与 peel 六值逐位一致** ✓。
8. **改写风险三项实测**：`ce7fa79` 是 `e376ddf` 祖先（`merge-base --is-ancestor` exit 0）且距离 **79** ⇒ fast-forward；四个被 reset/amend 丢弃的中间态（`da473aa`/`18d5159`/`29b39b4`/`1241b50`）**均非** `e376ddf` 祖先 ⇒ 未进入已推送历史；`v0.80.0` 远端 peel = 本地 peel ⇒ 无已发布 tag 重指 ✓。
9. **M-8 归档完整性**：`check-archive-integrity` = `Hot tasks 0 / Archived 91 / Index 1148 / Total 91` + `[PASS]`（exit 0）✓。
10. **两项新 FAIL 的判据与数据面**：`verify_workflow.py:2011-2023` 必需热节清单；`plan-tracker.md` 全部标题（7 行）；`plan-tracker.md` 缺 3 个必需节；**与 2026-09-10 备份的标题差集**（被移除 10 个节/子节，恰为判据对象所在节）✓。
11. **已发布树的测试绿**：`test_dsh_doctor` = **Ran 86 OK**（35.383s，`DSH_HOME=%TEMP%\spg-r2-doctor-690ae8f5`）；`test_archguard_ratchet` = **Ran 38 OK**（115.749s，`DSH_HOME=%TEMP%\spg-r2-arch-20e7a470`）✓。
12. **治理记录**：`EVD-1038`（全文含 `m6_gate`/`push`/`m8_archive`）、`EVD-1039`、`EVD-1034`（含 supersede 声明全文）、`EVD-1036`、`EVD-1037`；`plan-tracker.md:11/44/88` 与 `archive/tasks/v0.1.0~v0.80.0.md` 头部 ✓。
13. **文档面**：`CHANGELOG.md:5-39` 与 `:37`（Breaking 显式行）、`README.md:85-94`（B-2 限定句 + 推送陈述）、`release-checklist-0.81.0.md`（Gate 1~14 全文 + Gate 10 明细 + 归因分级 + M-8 义务）、`rollback-plan-0.81.0.md:32-44`、`version-plan-0.81.0.md:118/135`、`release-checklist/SKILL.md:68`、`stage-release/SKILL.md:58/115/156` ✓。
14. **真机三向 grep**（17 处命中逐条查看，全部为禁止性/未验证表述 + 评审历史）✓。
15. **无副作用核查**：每条命令前后 `git status` 一致（唯一新增 = 本报告）；未创建任何 worktree/tag/commit ✓。

**我未能独立复现（标注为边界外，且不作为本轮 blocking 依据）**：

- **全量 `discover`**（≈13 分钟）——按指令未跑；以单模块 + 块级复跑替代；
- **`revert` 干跑本身**（需写权限 + 隔离 worktree）⇒ 采信 R1 已做的"结构签名可精确导出"论证 + §5.2⑤ 的记录存在性；
- **迁移前 plan-tracker 快照**（`plan-tracker.md` 不在 git，`.governance/` 无 2026-09-14 备份）⇒ `F-R2-01` 的成因表述为"三项事实严格吻合"，未逐字回放写入动作；
- **远端 API 侧的历史推送审计**（如需证明"远端从未收到被丢弃提交"，可用 GitHub events/API 复核）⇒ 本轮以"fast-forward + 被丢弃提交非祖先 + 远端 peel/ref 逐位一致"三项间接证据判定**无改写风险面**；
- `governance health` 84 issues 的**逐条分类**（我只取汇总值与首发项）。

---

## 10. 命令上报（全部只读；唯一写入 = 本报告）

| # | 命令（摘要） | 退出码 | 结论摘要 |
|---|---|---|---|
| 1 | `resolve_entry.py --json` | 0 | `resolved_root_ok: true`；plugin_home/host_root 双根；hooks 三件齐；`active_version 0.81.0` |
| 2 | `git rev-list --parents -n 1 e376ddf` / `log --oneline -1` / `rev-parse a89341e` | 0 | **单父 = `a89341e`** ✓ |
| 3 | `git log --oneline -6 --graph` | 0 | `e376ddf → a89341e → 5e6d8c7 → 3074120 …`（线性） |
| 4 | `git show --stat/--name-only e376ddf` | 0 | 11 文件（manifest + 三件套 release 文档 + CHANGELOG + README + 2 测试 + 3 审查报告） |
| 5 | `python -c`（canonical + event_integrity 复算 + ledger 对照） | 0 | 字节 canonical=True；integrity 复算 = 声明值；effective_state 一致；transition 事件数 1 |
| 6 | `git log --format="%H %s" -- <manifest>` + `git diff a89341e e376ddf -- <manifest>` | 0 | 仅 2 个提交触碰 manifest；diff = 1 行 candidate→released + 事件追加 |
| 7 | `verify_workflow.py release-ledger --version 0.81.0 --remote github-https` | 0 | **PASS / NATIVE_RELEASED / issues []**；candidate/release commit + tag 两面一致 |
| 8 | `verify_workflow.py check-release … --lineage-mode released --release-commit e376ddf --lineage-remote github-https` | **1** | **14 PASS / 6 FAIL / 38 issues**；新增 `release fact source` + `hot fact source` |
| 9 | `verify_workflow.py check-release … --lineage-mode candidate`（对照） | **1** | **逐项相同**（38 issues）⇒ 非模式特有 |
| 10 | `verify_workflow.py check-archive-integrity` | 0 | `Hot 0 / Archived 91 / Index 1148 / Total 91` + **PASS** |
| 11 | `git cat-file -t v0.81.0` / `rev-parse 'v0.81.0^{commit}'` / `cat-file tag` / `for-each-ref` | 0 | **annotated tag**，object `71e27340…`，peel **`e376ddf`**；message 全文读出并裁决 |
| 12 | `git show-ref --tags` + 三 tag object/peel | 0 | v0.79.0 `96a00302→17eda48`；v0.80.0 `131debec→71f73eb`；v0.81.0 `71e27340→e376ddf` |
| 13 | `git ls-remote --tags github-https 'refs/tags/v0.79.0*' …v0.80.0* …v0.81.0*` | 0 | **三 tag（含 annotated 对象 + ^{} peel）均已在远端，peel 与本地逐位一致** |
| 14 | `git ls-remote github-https refs/heads/master` | 0 | **`e376ddf`** = release commit |
| 15 | `git reflog show master --date=iso` | 0 | 19:47–19:52 有 commit/amend/reset 中间态（`da473aa`/`18d5159`/`29b39b4`/`1241b50`）→ 19:52:48 定稿 `e376ddf` |
| 16 | `git merge-base --is-ancestor ce7fa79 e376ddf` + 四中间态逐一 is-ancestor + `rev-list --count ce7fa79..e376ddf` | 0 / 1 | **fast-forward（祖先，79 commits）**；四中间态**均非祖先** ⇒ 未进已推送历史 |
| 17 | `python -m unittest …tests.test_dsh_doctor`（`DSH_HOME=%TEMP%\spg-r2-doctor-690ae8f5`） | 0 | **Ran 86 tests OK**（35.383s） |
| 18 | `python -m unittest …tests.test_archguard_ratchet`（`DSH_HOME=%TEMP%\spg-r2-arch-20e7a470`） | 0 | **Ran 38 tests OK**（115.749s） |
| 19 | `Get-Content -Encoding UTF8` 只读治理文件（EVD-1034/1036/1037/1038/1039、plan-tracker、archive index/任务文件头部） | 0 | EVD-1038 字段齐备但 `m6_gate` 不实；EVD-1034 supersede 已落地；归档文件「16 条 / 2026-09-14」 |
| 20 | 只读 grep/读：`verify_workflow.py:2011-2023/5946/6024`、`release-checklist/SKILL.md:68`、`stage-release/SKILL.md:58/115`、`README.md:85-94`、`CHANGELOG.md:5-39`、`rollback-plan/checklist/version-plan` 定向 | 0 | 见 §5/§7 各条 |
| 21 | `Get-ChildItem -Recurse -Filter plan-tracker.md` + 逐文件节探测 + 标题差集 diff | 0 | 当前文件缺 3 必需节；**2026-09-10 备份含全部三节**；差集 = 被移除 10 节 |
| 22 | 三向 grep `真机…通过` / `三项…通过` | 0 | 17 处命中**全部为禁止/未验证表述**+评审历史 ⇒ 零 overclaim |

**未执行**：任何 `git add/commit/tag/push/restore/reset/checkout/stash/revert`、任何 worktree 创建、任何全量 `discover`、任何仓库外或真实 home 读写。两条测试命令均以 `$tmpHome`（非保留名 `$home`）把 `DSH_HOME` 重定向到 `%TEMP%` 新建目录并逐条上报。

---

## 11. 发布闭环裁决

### 11.1 0.81.0 是否已按声明式契约**完整发布**？

**分两层回答（关键区分）**：

| 层 | 裁决 | 依据 |
|---|---|---|
| **声明式契约 / git 产物层** | **已完整发布 ✓（正确、可复现、无改写）** | transition 单父 + parent = candidate（§1.1）；manifest 判决释 + 事件 integrity 复算相符 + canonical 字节精确（§1.2-1.5）；`release-ledger`（含远端）`PASS / NATIVE_RELEASED / issues []`（§2.1）；annotated tag peel = `e376ddf` 且**本地/远端逐位一致**（§3.1-3.3）；`master = e376ddf` 且为 fast-forward、无 tag 重指、无被丢弃提交进入远端（§3.4）；归档完整性 PASS（§4.1）⇒ **用户侧"可获得 v0.81.0"这一事实成立，且无需重打 tag/重推** |
| **发布闭环 / 记录与文档层** | **未闭环 ✗（3 项可复核缺陷）** | ① release 态门禁被记为"16 PASS / 3 残留"，实为 **14 PASS / 6 FAIL / 38 issues** 且 2 项新失败未披露未修（**F-R2-01 P1**）；② 回滚方案**发布 tip 未回填**（6 处占位，**F-R2-02 P2**）；③ README 仍称**未推送 / master 仍 0.78.1**（**F-R2-03 P2**） |

⇒ **总裁决：0.81.0 的"发布动作"成功且无需撤销；但"发布闭环"未完成 ⇒ 须以 `NEEDS_CHANGE` 退回补收口（**全部为可逆的治理数据/文档动作，不涉及重打 tag 或重推**）。**

### 11.2 最小补救动作（按优先级；**均不涉及不可逆操作**）

| # | 动作 | 覆盖 | 判据（验收） |
|---|---|---|---|
| 1 | **补齐 plan-tracker 必需热节**：`## 版本规划`（含 `## 变更控制`）/`## 需求跟踪矩阵`/`### 1.0.0 依赖链`，并修复迁移产生的 ragged table row | **F-R2-01** | `check_hot_fact_source_consistency` / `release fact source` 的 hot-节类条目**清零**（`plan-tracker.md` 标题恢复至含 5+1 必需节） |
| 2 | **登记 `release fact source` 与 `hot fact source` 的剩余失败归属**（`project/references/architecture.md:445` overstate 等）并处置 | F-R2-01 | 每条 FAIL 有 FIX/RISK 编号或就地修正；复跑后该 2 项转为 PASS 或**如实**列为残留并标注归属 |
| 3 | **复跑 released 态门禁并以当场值刷新记录**：`check-release --lineage-mode released --release-commit e376ddf --lineage-remote github-https` 的原始输出贴入 `release-checklist` Gate 13 与 **EVD-1038（或追加 EVD supersede 行）**，把「16 项 PASS / 残留 3 项（91 issues）」更正为实测值 | F-R2-01 / F-R2-04③ | 记录值 == 当场输出（逐项）；`governance health` 数值标注取值时点 |
| 4 | **回填发布 tip**：`rollback-plan-0.81.0.md` 6 处 `<发布 tip>` → `e376ddf`（可注明由 `release-ledger.release_commit` 派生），Gate 14 同步写入终值 | F-R2-02 | 文件内 `<发布 tip>` = 0 处；`e376ddf` 命中 ≥1 |
| 5 | **修订 README:94 + checklist:142 的推送陈述** | F-R2-03 / F-R2-04④ | README 写"三 tag 已推送、master = `e376ddf`、`github:` 形态可用"；checklist M-8 义务标"已履行 + 证据 EVD-1038.push" |
| 6 | **清理陈旧残留**：`plan-tracker:44` 删"发布半面 Release Reviewer 待执行"（已由 R1 完成） | F-R2-04① | 该行不再自相矛盾 |
| 7 | （建议，非阻塞）① 把"M-8 收尾后复跑 released 态门禁"写成 M-8 显式义务（O-2）；② 后续版本把"release transition"与"审查退回修复"拆成两个提交（O-1）；③ 复核 `unit tests` 180s 预算（O-4） | O-1~O-4 | 下版规划中体现 |

**⚠️ 不可逆性提示（明确标注）**：上述 1~6 项**均不需要** `git tag` 重打、`git push --force` 或历史改写 —— 已发布的 tag / commit 事实经我实测**完全正确**（§1/§3）。若后续有人主张"重打 `v0.81.0` 让 release commit 变成纯 manifest 提交"（针对 O-1），那将**改写已推送 tag**，属**不可逆且影响用户已有克隆**的操作，**MUST 先取得用户逐项授权**（`DEC-143`/模式纪律下亦须显式确认），本报告**不建议**此举。

**真机三项**：仍由用户手动执行并回贴；**回贴前任何文档不得声明其通过**（本轮已核：全库零此类声明，§4.3）。

---

*审查方：Release Reviewer Agent（只读；唯一写入 = 本报告）｜审查对象：已发布的 0.81.0（REL-077），release commit `e376ddf`，candidate `a89341e`｜round=2，prev_report=`docs/reviews/review-REL-077-RELEASE-R1.md`｜结论：**NEEDS_CHANGE**（`unresolved_blockers=3`：F-R2-01 P1 / F-R2-02 P2 / F-R2-03 P2）｜机录建议：Coordinator 以 review-record 持久化（`--task REL-077 --round 5 --result NEEDS_CHANGE`；报告 = `docs/reviews/review-REL-077-RELEASE-R2.md`；prev = `docs/reviews/review-REL-077-RELEASE-R1.md`），随后按 §11.2 最小补救 1~6 返工并**发起 R3 复审**（同一 Release Reviewer，须逐条比对 F-R2-01~04）*
