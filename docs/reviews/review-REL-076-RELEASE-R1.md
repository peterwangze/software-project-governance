# REVIEW-REL-076-RELEASE-R1 — Release Re-Review of the 0.80.0 Release Candidate

- **Task**: REL-076 (release 0.80.0; version authority = `skills/software-project-governance/SKILL.md` frontmatter `version: 0.80.0`)
- **Round**: R1 (re-verification of the R0 fix batch against the **frozen** candidate)
- **Reviewer**: Release Reviewer (independent, delegated). **No product file was modified by this review.** The only write is this report; it is deliberately left **untracked** so the pinned tree is untouched.
- **Verdict**: **NEEDS_CHANGE** — `unresolved_blockers=2` (definition in §7)
- **Object reviewed**: the **pinned index** — `git write-tree` = `88915ed2606154219561c3828f23dbf390b4dbe2`, 33 staged files. Not the worktree-as-moving-target that R0 had to review (R0 §1, P3-4).
- **Predecessor**: `docs/reviews/review-REL-076-RELEASE-R0.md` (NEEDS_CHANGE, `unresolved_blockers=2`, findings P1-1/P1-2 + P2-1…P2-6 + P3-1…P3-10)

---

## 1. Artifact freeze — VERIFIED (and it did not move)

| Check | Required | Observed (first action, before any file read) | Result |
|---|---|---|---|
| `git write-tree` | `88915ed2606154219561c3828f23dbf390b4dbe2` | `88915ed2606154219561c3828f23dbf390b4dbe2` | **MATCH** |
| Staged files | 33 | `git diff --cached --name-status` → 33 (all `M`/`A`) | **MATCH** |
| Unstaged (index ≠ worktree) | 0 | `git diff --name-only` → 0 | **MATCH** |
| Untracked | 0 | `git ls-files --others --exclude-standard` → 0 | **MATCH** at start |

Re-confirmed **after** every read and after this review's only write: `git write-tree` still `88915ed2…`, staged 33, unstaged 0. Writing an untracked report does not touch the index, so the pin is unchanged and the artifact **no longer moves** — R0's P3-4 is resolved by construction. **This review therefore verifies an immutable object**, unlike R0.

**One state change did occur, outside the frozen surface (disclosed).** `docs/reviews/review-REL-076-DESIGN-R1.md` appeared at **10:12:31** — i.e. *after* this review began (my start-of-review reads show untracked = 0) and after the artifact was pinned. It is the Design Reviewer's R1 half, machine-recorded at **round 1** (`.governance/review-REL-076-R1.md`, 10:12:38; evidence row `REVIEW-REL-076-R1`, `.governance/evidence-log.md:1985`, verdict NEEDS_CHANGE). It is untracked and therefore **not part of the artifact**; the frozen tree is unaffected. Consequences are recorded as N-7 in §4.

---

## 2. Per-finding closure verdicts

Legend: **已关闭** / **部分关闭** / **未关闭** / **不适用**. Every verdict below is against the **staged index blobs**, not the worktree.

| Finding | R0 severity | Verdict | One-line basis |
|---|---|---|---|
| P1-1 CHANGELOG asserted the two DEC-188-retracted claims | P1 | **已关闭** | `git show :project/CHANGELOG.md:19` now states the DEC-188 ② criterion verbatim and explicitly rejects 逐字节等价; 宿主平面贡献归零 removed |
| P1-2 README promised per-session global governance skills | P1 | **已关闭** | `git show :README.md:33/76/392` now "in that preset's sessions only" with real-machine confirmation flagged pending; `〔static:〕` marker added at L393 |
| P2-1 M-2 row 7 number+composition not reproducible | P2 | **部分关闭** | re-measured **65 issues / exit 0 = recorded 65** ✓ and timestamp added; bucket list still partly wrong (§3.3) |
| P2-2 settings-page outcomes asserted as delivered | P2 | **已关闭** | checklist L56 + L141 + feature-flags L23/L32 now design-expectation-scoped with host UI explicitly unverified |
| P2-3 §Breaking Changes fidelity gaps (a)/(b)/(c) | P2 | **部分关闭** | (b) and (c) closed (L143 four surfaces; L144 evidence wording corrected); (a) closed for `engines`/`type`/`main`/`exports` **but added a false `files` clause** → **N-2** |
| P2-4 archive integrity FAIL + wrong 条目数 | P2 | **已关闭** | 条目数 corrected 5→4 (file now declares 4 and contains DEC-174/176/177/182); FAIL reproduced as designed and disclosed at L81 + row 10; FIX-312 registered (L118) |
| P2-5 row 6 "zero new failures" not confirmable | P2 | **部分关闭** | attribution schema independently reproduced in full (§3.4); the recorded pin is a **different tree** and the frozen tree has never been full-suite measured → **N-3** |
| P2-6 M-3 double review unrecordable at one round | P2 | **已关闭** | FIX-314 registered (L120); round-2 slot documented (L113); this round is recorded with `--round 2` (§8) |
| P3-1 version surfaces outside the gates | P3 | **已关闭** | disclosed as latent at L125 (the R0 *recommendation* — add `commands/governance-init.md` to the projections — is still unimplemented; informational) |
| P3-2 row 1 attribution error | P3 | **已关闭** | checklist L70 now carries the correction; re-verified against the gate's own output ("+ bootstrap markers (`AGENTS.md`, `CLAUDE.md`)") |
| P3-3 recorded numbers without measurement time | P3 | **部分关闭** | row 7 has a timestamp; **row 3 does not** and its numbers no longer reproduce (§3.3) |
| P3-4 candidate moved during review | P3 | **已关闭** | artifact pinned and verified before/after (§1) |
| P3-5 stale local hooks | P3 | **已关闭** | disclosed at L124; re-verified `post-commit` 0.79.0 / `prepare-commit-msg` 0.75.0 vs source 0.80.0 |
| P3-6 wrong commit-message size claim | P3 | **已关闭** | disclosed as unfixable at L123; `git show --stat 5a259e2` = 33 files, +1034/−1324 re-verified |
| P3-7 "staging+rename 原子" | P3 | **已关闭** | checklist L57 and feature-flags L23 both now state the replace window and "不称「原子」" |
| P3-8 review-evidence attribution imprecise | P3 | **已关闭** | checklist L105 corrected to 9 and discloses the `.governance`-only FIX-308/309 reports; I independently counted **9** report-archive commits |
| P3-9 dangling "§Candidate 元数据" | P3 | **已关闭** | occurrence count in the staged checklist = **0**; L66 now points to "本表 #11" |
| P3-10 stale "before v0.79.0 is pushed" | P3 | **部分关闭** | `README.md:92` rewritten (but into a now-false statement → **N-1**); `README.md:442` still carries the pre-`v0.79.0` framing → **N-4** |

### 2.1 P1-1 (staged `project/CHANGELOG.md:19`) — closed

The paragraph now reads (excerpt, staged blob):

> **机检判据（DEC-188 ② 澄清）**：`dsh --profile <p> --dump-config` 安装前后，**既有**宿主行的存在性 / `config` / `disabled` 与任何宿主平面注册表内容**零变化**，组合 entry 列表**恰多一行且该行只命名本包**——**不是**「与未安装时逐字节等价」（后者在「官方 `dsh plugin add` 零手工步骤即交付预设」同时成立时不可满足…）。FIX-310 即按此不变量重做：**宿主既有行零触碰**（不改任何既有行、不注册全局 provider / 服务 / 工具、不声明 `system`-trust 预设根、无 `!!js` 自定位）…

Machine checks I ran against the staged blob:
- `Select-String -SimpleMatch '宿主平面贡献归零'` → **count 0** (retracted wording gone; "宿主既有行零触碰" present, count 1).
- `Select-String -SimpleMatch '逐字节等价'` → **1 hit, and it is the explicit rejection clause** ("**不是**「与未安装时逐字节等价」…不可满足"), not an assertion.

This matches DEC-188 ② as recorded and the checklist's own criterion at L62/L26. R0's P1-1 is closed.

### 2.2 P1-2 (staged `README.md:33/76/392`) — closed

- `git show :README.md | Select-String -SimpleMatch 'every session of that profile'` → **count 0**.
- L33: "…the governance skills and `/governance` command projections load **in that preset's sessions only** (other presets such as `standard` carry no governance skills; this scoping is FIX-310's core behavioural goal and its real-machine confirmation is still pending)".
- L76: same scoping, plus "Delivery is a pure insert: `cordis.patch.yml` adds ONE row naming this package only … (DEC-187 I-1/I-2/I-3 as clarified by DEC-188 ②…)".
- L392/393 (Chinese item 2): scoped to 治理预设的会话, marked **`〔static: 规则级推导 … 无会话级执行证据〕`**, and flagged "⚠️ **该作用域的真机确认仍未完成**", with an explicit note that the old "每个会话" wording is retired. The only remaining `每个会话` occurrence in the staged README is that retirement note (count 1, inside the parenthetical).
- The `〔static: …〕` marker does repair the registered claim: `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p "test_readme_evidence_levels.py"` → **Ran 8 tests … OK**, exit 0, independently reproduced (row 6's self-disclosure verified).

### 2.3 P2-4 (`.governance` archive) — closed, and the FAIL is as disclosed

`check-archive-integrity` → **FAIL, exit 1**, counters hot 85 / archived 91 / index 1080 / total 176, issue = "Archive trigger gap: 0 hot completed task(s) should be archived via release_forced for v0.1.0~v0.78.1" — i.e. the FIX-312 engine false positive (0 task, 1 decision), exactly as disclosed at checklist L81 and row 10, with FIX-312 registered at L118. `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:4` now reads **`- **条目数**: 4`** and the file contains exactly four headings (DEC-174/176/177/182) — the R0 residue is fixed. Note the checklist's §归档迁移执行证据 (L89) still records `index 1081 / PASS`: that is the **M-2-period** state and is coherent with L81, which discloses the post-rollback FAIL (index now 1080).

### 2.4 P2-6 — closed on the process plane; the record is produced by this round

FIX-314 is registered (L120) and the slot convention is documented (L113: "round 编号在此**不代表修复轮次**，仅为绕开键冲突的合规落位"). Round 1 is held by the Design half (recorded 10:12:38), so `--round 2` is free; the mandated command was run and its raw output is in §8.

---

## 3. Re-measured numbers vs the checklist's recorded numbers

Rows 1/2/3/4/7/8 were re-run as instructed. **Row 6's full suite was deliberately NOT re-run** (the brief forbids racing the frozen-tree measurement recorded in that row); targeted single-module checks were used instead. **Row 10 (`check-release`) was not run at all** — its execution gates include the 180 s-capped unit-test invocation.

### 3.1 Gate rows

| # | Command | Recorded in checklist | Measured by me (R1) | Verdict |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASSED — 13 files + bootstrap markers, zero FAIL/WARN (L70) | **PASSED, exit 0** — "Files checked: 13 … + bootstrap markers (`AGENTS.md`, `CLAUDE.md`)" | **reproduced** |
| 2 | `check-projection-sync --fail-on-issues` | PASSED — source 0.80.0, 15 (L71) | **PASSED, exit 0** — source 0.80.0, 15 mirrored | **reproduced** |
| 3 | `check-manifest-consistency` | **PASS — 657 canonical / 727 actual** (L72) | **[PASS], exit 0 — 659 canonical / 733 actual** | verdict reproduced; **numbers stale** |
| 4 | `check-cross-references --fail-on-issues` | PASS — 663 refs (L73) | **PASS, exit 0** — 663 references, zero dangling/deprecated/circular | **reproduced** |
| 6 | full unittest (frozen tree) | 2675 / 35F+1E+1S = 36 (L75) | **not re-run (instructed)**; targeted: `PlanTrackerMatcherTests` → `Ran 14 tests … FAILED (failures=5)`, `test_readme_evidence_levels` → `Ran 8 … OK` | structurally corroborated (§3.4) |
| 7 | `check-governance --summary-only` | **65 issues, exit 0** (measured 2026-09-12T09:53:59) (L76) | **`Governance: 65 issues`, exit 0**, 58.7 s | **number + exit code reproduced exactly**; buckets partly differ (§3.3) |
| 8 | `check-injection-contract` | PASSED — 3 files / 23 anchors (L77) | **PASSED, exit 0** — 3 files / 23 anchors | **reproduced** |
| 10 | `check-release … --lineage-mode candidate` | FAILED - 10 issue(s) (L79) | **NOT RUN** (instructed) | 未复验 |

Row 3's count growth is fully explained and is **not** a defect: `check-manifest-consistency` derives "actual" from `git ls-files --cached` (`checks/manifest.py:391-403`) and "canonical" by expanding the manifest's glob entries, so both grow with the two newly staged review reports (727 → 731 at R0 when the release docs were staged → **733** now; canonical 657 → **659**). `git diff HEAD -- core/manifest.json` is the version line only. The defect is that row 3 records a stale pair with **no timestamp** → N-5 / P3-3 residue.

Extra gate (not a checklist row): `check-archive-integrity` → FAIL exit 1, as designed and disclosed (§2.3).

### 3.2 Row 8's decomposition claim — verified at source

Row 8 states the anchor face moved 4 files/28 anchors → 3 files/23 anchors by removing two anchor-bearing copies and adding one. The anchor table in `skills/software-project-governance/infra/verify_workflow.py` now keys on `agent-presets/governance/agent.cordis.yml.template` (L6623) and its comment at L6616 records that the former `presets/governance/agent.cordis.yml` spelling is gone. Consistent.

### 3.3 Row 7 — my buckets vs the recorded buckets

Measured on the frozen tree, `--level strict` → 57 report lines under `Governance: 65 issues`:

| Bucket (recorded L76) | Recorded | Measured | |
|---|---|---|---|
| total / exit | 65 / 0 | **65 / 0** | ✓ |
| `module_size` (e2e mirror) | ×1 | ×1 (L22) | ✓ |
| `function_size` | ×6 | **×7** (1 FAIL e2e `cmd_check_governance` + 6 WARN: 4 e2e mirror + 2 `.governance` val008 backups) | ✗ |
| Check 18d | "FEAT-023/024/026/027 各 ×5 + FEAT-025 ×1" | **18d ×8 = 4 FEATs × 2** (`product_success_contract` + `acceptance_contract`); **FEAT-025 = 0** | ✗ |
| `UNSUPPORTED_AFFIRMATIVE` | ×3 | ×3 (L30-32) | ✓ |
| `hooks_drift` | ×2 | ×2 (`post-commit`, `prepare-commit-msg`) | ✓ |
| locks | ×7 | "7 lock consistency issue(s) (7 blocking)" (L43) | ✓ |
| closure | ×7 | "7 closure violation(s)" (L29) | ✓ |
| structural | 417 (0 blocking) | "417 structural issue(s) (0 blocking)" (L37) | ✓ |
| `untracked` | ×2 (候选中，commit 后自消) | **absent** — both R0 reports are now staged | ✗ |
| 缺 R1 证据行 | ×2 | "2 missing R1 evidence row(s)" (L58) | ✓ |
| machine-provenance WARN | ×2 | "2 … WARN(s) (showing first 2)" (L55) | ✓ |
| M5.4b | ×1 | "1 M5.4b … WARN(s)" (L54) | ✓ |
| DEC-ID gaps | present | "DEC-ID gaps: missing [175]" (L36) | ✓ |
| `release_docs_versions` | ×1 | ×1 (L51) | ✓ |
| archive integrity | ×1 | ×1 (L44) | ✓ |
| **unlisted in the row** | — | Check **18f ×8**, **18i ×4**, **28p ×3**, **28s ×2**, **32 ×1**, **34 ×1**, WARN **17 ×5**, **35 ×1**, **36 ×1**, **5 ×1**, **13 ×1**, **14 ×1**, **26 ×1**, **27 ×1**, **29 ×1**, **30c ×1**, **39 ×1** | ✗ |

So the **headline number and exit code reproduce byte-for-byte** (65 / exit 0) and 12 of the row's bucket clauses reproduce exactly, but ~5 clauses do not and 9 measured buckets are unlisted. Since the row now carries both a measurement timestamp and an explicit "live-data coupled, drifted across runs (62 / 65)" caveat, this is disclosed drift rather than a false PASS — hence **部分关闭** rather than 未关闭. Row 7's own rollback trigger #3 treats baseline drift as requiring re-measurement, which is the right disposition at M-6.

### 3.4 Row 6 — attribution independently reproduced (without running the full suite)

Row 6 attributes the +4 over the 0.79.0 baseline to the M-2 archive migration, in the family `test_hooks.PlanTrackerMatcherTests.test_replay_real_plan_tracker_hits`, citing `tests/test_hooks.py` L302-313. I verified all three legs:

1. **Source**: `test_hooks.py:302-313` replays exactly the six IDs the row names — `("REL-071", "REL-072", "FIX-282", "REL-073", "FIX-283", "FIX-288")` — plus an absent-ID miss check. ✓
2. **Count**: `python -X utf8 -m unittest skills.software-project-governance.infra.tests.test_hooks.PlanTrackerMatcherTests` → **`Ran 14 tests … FAILED (failures=5)`**, exit 1 — matching the row's "5 = … `test_replay_real_plan_tracker_hits`". Failing subtest IDs: **REL-071, FIX-282, REL-073, FIX-283, FIX-288**; REL-072 is the one that still hits. With REL-071 as the sole 0.79.0-baseline member of this family, the delta is **+4**, exactly as recorded. ✓
3. **Self-disclosure**: `test_readme_evidence_levels` → **Ran 8 … OK**. ✓

**What I did not verify**: the full-suite totals (`Ran 2675 tests in 720.962s`, `failures=35, errors=1, skipped=1`) — not re-run by instruction, and the row's recorded pin is a different tree (N-3). The collection count 2675 was reproduced at R0.

---

## 4. NEW findings introduced or exposed by the fix batch

### N-1 — **P1** — the shipped README asserts `v0.80.0` is tagged locally, and cites a disclosure that is not in the 0.80.0 checklist → **BLOCKER**

**File**: `README.md:92` — **in the frozen index** (`git show :README.md`), i.e. inside the pinned artifact.

> Note on `github:`: `v0.79.0` and `v0.80.0` are tagged locally but **not yet pushed** (push credentials blocked — disclosure in the release checklist), so GitHub's master still serves 0.78.1; install from a local checkout (`link:`/`file:`) or wait for the push.

Verified by me, independently of the sibling review:

```
git tag -l 'v0.80*'        → NONE
git tag -l | tail           → … v0.78.0, v0.78.1, v0.79.0 (highest); no v0.80.0
git rev-parse v0.80.0       → fatal: ambiguous argument 'v0.80.0': unknown revision
git show :skills/…/core/releases/0.80.0.json → lifecycle_state: "candidate", events: []
release-checklist-0.80.0.md:5   → "candidate（release_authorized=false；transition/tag/push 待 M-4 用户授权）"
release-checklist-0.80.0.md:135 → "candidate-only：release_authorized=false——transition/tag/push 待用户授权（DEC-143）"
git show :docs/release/release-checklist-0.80.0.md | Select-String '凭据' → L79 only (the W-1 CI-ubuntu note)
```

`v0.80.0` **cannot** be tagged: the release is unauthorized and its manifest sits at `candidate` with zero lifecycle events. The cited "disclosure in the release checklist" is not in the 0.80.0 checklist — the only credentials mention there (L79) concerns the **CI ubuntu** face, not the tag push.

**Introduced by the fix batch.** R0's P3-10 remediation rewrote this line (R0-era wording: "before v0.79.0 is pushed: GitHub's master still serves 0.78.1…"). The rewrite added the false `v0.80.0` tag claim.

**Why P1**: it is the same defect class as the two findings that blocked R0 — a shipped, user-visible file asserting something the repository contradicts — but worse in kind: it is a false statement of **release state** in the document a user reads at the M-4 gate, and it contradicts the candidate's own `release_authorized=false`. A one-line fix suffices (scope the tag claim to `v0.79.0`; state that `v0.80.0` is a candidate awaiting authorization). *Independent corroboration: Design R1 F13 (found in the sibling round).*

### N-2 — **P1** — the fixed §Breaking Changes now contains a false `files` claim → **BLOCKER**

**File**: `docs/release/release-checklist-0.80.0.md:142` (staged), §Breaking Changes item 2:

> 新增 `type: module` / `main: lib/index.js` / `exports` / `engines: node >= 20`（宿主行模块为 ESM…）；**`files` 收敛为 `lib/` + `agent-presets/`**；**移除死字段 `dsh.skills`**…

Measured on the **staged** `package.json`:

```
files  = ["lib/", "agent-presets/", "skills/", "commands/", "agents/", "adapters/dsh/",
          "!**/__pycache__/", "!**/*.pyc", "cordis.patch.yml", "README.md", "LICENSE"]   (11 entries)
HEAD   = ["skills/", "commands/", "agents/", "adapters/dsh/", "presets/", …]            (10 entries)
```

`files` did **not** converge to two entries. The real change is `presets/` removed and `lib/` + `agent-presets/` added, with `skills/`, `commands/`, `agents/`, `adapters/dsh/`, `cordis.patch.yml`, `README.md` and `LICENSE` **retained** — i.e. the package still ships the whole plugin surface. Read literally (and that is how a Breaking Changes list is read), the sentence tells a reviewer that the published package contains only `lib/` and `agent-presets/`.

**Introduced by the fix batch**: this clause was added while satisfying R0 P2-3(a); the four genuinely missing fields are correctly listed, the `files` clause is not. No other document repeats the error (checked CHANGELOG, feature-flags, rollback-plan). One-line fix: "`files` 增补 `lib/` + `agent-presets/`、移除 `presets/`（其余 `skills/`、`commands/`、`agents/`、`adapters/dsh/`、`cordis.patch.yml`、`README.md`、`LICENSE` 保留）".

**Why P1**: §Breaking Changes is the release gate's enumeration of user-visible breakage; a false claim about the shipped file whitelist is a documentation defect that would be frozen into the release. It is also the second consecutive round in which this section was found misdescribing the same surface.

### N-3 — **P2** — row 6's recorded "frozen tree" is not the frozen candidate

**File**: `docs/release/release-checklist-0.80.0.md:75`. The row records `git write-tree` = **`ef20d026765e415b82edf3ac6a86ba25b2287fab`**; the pinned candidate is **`88915ed2606154219561c3828f23dbf390b4dbe2`**. Both are real tree objects (`git cat-file -t` → `tree`), so these are two distinct index states, not a typo:

```
git ls-tree -r ef20d026 | count → 731   (the two R0 review reports not yet present)
git ls-tree -r 88915ed2 | count → 733
git diff-tree -r --name-status ef20d026 88915ed2 →
  M README.md, M docs/marketplace/dsh-preset-adapter-0.73.0.md,
  M docs/release/{feature-flags,release-checklist}-0.80.0.md,
  M docs/requirements/data-inventory-0.80.0.md, M lib/index.js,
  M project/CHANGELOG.md, M skills/…/core/protocol/plugin-contract.md,
  A docs/reviews/review-REL-076-{DESIGN,RELEASE}-R0.md          (10 files)
```

The row labels `ef20d026` "**冻结树实测**", but that tree is not the artifact under review, and the pinned tree has **never** been full-suite measured. The fix batch's own worktree mtimes show the two product-relevant files were already final before the run window started (`lib/index.js` 09:24:51, `project/CHANGELOG.md` 09:24:01 vs run start 09:54:43) and the `lib/index.js` delta between the two trees is **comment-only** (staged L41-48) — so the *tested content* was most likely final for product code; but the recorded hash is not a valid pin and the measurement is not reproducible from it.

**Disposition**: P2 (evidence integrity; the row is essentially honest but mislabelled). Correct form: re-pin after staging, or state that the measurement predates the fix batch and name the 10 differing files. *Independent corroboration: Design R1 F12.*

### N-4 — **P3** — `README.md:442` still carries the pre-`v0.79.0` framing (P3-10 residue)

`README.md:92` was rewritten; **`README.md:442` was not**: "…`github:` 形式打包语义与 `file:` 同构——但 v0.79.0 推送前从 GitHub 安装到的是 0.78.1 旧版，请用本地 `link:`/`file:` 或等待发布". With `v0.79.0` and `v0.80.0` both past, the "v0.79.0 推送前" framing is stale (the operative fact — GitHub's master still serves 0.78.1 — is unchanged). R0's P3-10 cited both lines (`:92`, `:440`); only one was touched.

### N-5 — **P3** — row 3 records stale counts with no timestamp (P3-3 residue)

`release-checklist-0.80.0.md:72` records "657 canonical / 727 actual"; measured on the frozen tree: **659 / 733** (PASS unchanged). R0's P3-3 asked for measurement timestamps next to live-data numbers; row 7 got one, row 3 did not.

### N-6 — **P3** — `rollback-plan-0.80.0.md:65` under-enumerates the Breaking Changes pointer

It still summarises "（4 项——dsh 安装形态变更 / `dsh.skills` 退役 / `presets/` 目录删除 / 其它五适配层零改动）", while checklist §Breaking Changes item 3 now enumerates **four** retired surfaces (L143). The pointer is stale relative to the section it points at.

### N-7 — **observation** — the chain plane moved after the pin; the staged checklist's review-evidence section is now behind the chain

- The staged checklist was authored at **10:07:10**; the Design R1 report landed at **10:12:31** and was machine-recorded at round 1 at **10:12:38** (`.governance/review-REL-076-R1.md`; `evidence-log.md:1985`).
- Consequently the frozen checklist's §Review Evidence (L107-113) documents DESIGN-R0 + RELEASE-R0 + the round-2 plan only, and cannot mention the Design R1. The Design R1's own verdict is **NEEDS_CHANGE / unresolved_blockers=1 (= its F13 / my N-1)**, so further remediation and a re-pin are already implied by the sibling round.
- Design R1 **F14** (P2: the checklist claims the Release half was recorded at round 2, but no such record existed) is **repaired by this round**: the record is now produced by the mandated CLI call in §8, which converts the checklist's forward-looking claim at L113/L120 into a true statement.

---

## 5. Deployment / rollback plane — still holds after the doc changes

- **The rollback plan was not touched by the fix batch.** `docs/release/rollback-plan-0.80.0.md` mtime 08:29:51 and it is absent from the `ef20d026 → 88915ed2` delta; its 8 triggers and the S1/S2/S3 steps are byte-identical to what R0 reviewed.
- **User-side ordering is still correct and is now better grounded.** L37 keeps `dsh plugin --profile <p> remove <ref>` **first**, then deletion of the rendered user-root preset. The corrected `lib/index.js` comment (staged L44-48) now states the same mechanism from the code side: "`dsh plugin remove` withdraws the bundle row (it manages the profile's pnpm bundle layer and never the user preset root, so it cannot delete the rendered preset — use the settings page or `launch.py --uninstall` for that); a subsequent boot with the row still present re-renders the preset, so deleting it alone is not persistent." The plan's Reversibility row ("重启自动重建", L56) agrees, and it does **not** depend on the unverified settings-page UI because it also offers manual directory deletion.
- **The `launch.py --uninstall` path exists**: `adapters/dsh/launch.py` L31/L288/L856 (`uninstall_preset()`, with an unexpected-path refusal at L300).
- **No silent re-introduction path**: L36 still discloses that `git revert 5a259e2` re-introduces the RISK-050 root cause and mandates a DEC + a new disposal task; L63 still declares S1 was never executed; L61's no-overclaim needles are intact.
- **The new `engines: node >= 20` floor does not change the rollback plane** (a revert to 0.79.0 simply drops the floor; no user-side step is implied).
- Residual: N-6's stale pointer.

---

## 6. `未知` (explicitly not verified — no file, command, or user statement available to me)

1. **Full-suite totals on the pinned tree.** Not measured (instructed), and never measured by anyone (N-3). Whether the 10-file fix-batch delta changes any test outcome is **未知**. My targeted coverage: `test_readme_evidence_levels` 8 OK, `PlanTrackerMatcherTests` 14 run / 5F (matching row 6), and gates 1/2/3/4/8 green on the frozen tree.
2. **M-2 row 10 (`check-release`)** — not run (its execution gates include the raced unit-test invocation); the recorded "FAILED - 10 issue(s)" is **未复验**.
3. **Rows 13/14** (released-mode gate, remote ledger) — post-M-6 by construction.
4. **CI ubuntu authoritative face (W-1)** — no credentials here; `git ls-remote <origin>` failed with `Host key verification failed`, so the remote state of tags is **unverified from this machine**. The *local* tag absence (N-1) is verified directly.
5. **Real-machine acceptance face** — settings-page 「自定义」/ delete / open-folder, non-governance sessions free of governance skills, governance session skill-catalog completeness. Unchanged from R0; the candidate declares them unverified, and I neither confirm nor deny.
6. **Governance-side state is "as of review time", not "as of the candidate"** — `.governance/` is gitignored and outside the pin, so the archive-integrity FAIL, FIX-312/FIX-313/FIX-314 registrations, and the review records cannot be pinned by `git write-tree`.
7. **REV-076** — unchanged from R0: no such identifier exists (`REL-076` does); I did not assume one.
8. **Design R1 F14's cause** (why no round-2 record existed before this round) — not determinable from the repository; this round closes the factual gap regardless.
9. **Design R1's location citation for the push-credential disclosure** (`release-checklist-0.79.0.md:69`) — **not independently confirmed by me** (my grep hit that line for `凭据|push` but the visible text is a pytest row whose tail I did not read). What I *did* verify: the **0.80.0** checklist contains no push-credential disclosure.

---

## 7. Conclusion

`unresolved_blockers=2`

> **Definition used** (unchanged from R0): `unresolved_blockers` = findings that must be closed before this candidate may proceed to M-4 user authorization = **N-1** (shipped `README.md:92` falsely states `v0.80.0` is tagged locally, citing a disclosure absent from the 0.80.0 checklist, and contradicting the candidate's own `release_authorized=false`) + **N-2** (shipped `release-checklist-0.80.0.md:142` falsely states `package.json` `files` converged to `lib/` + `agent-presets/`). P2/P3 findings are recorded for the fix batch and do not by themselves block authorization; §6 items are declared `未知` and are not counted.

**What the fix batch achieved.** The artifact is frozen and did not move; both R0 P1 blockers are closed **in the index**, not merely in the worktree — the CHANGELOG now states the DEC-188 ② criterion and explicitly retires 逐字节等价 / 宿主平面贡献归零, and the README scopes governance availability to the preset's sessions with the real-machine confirmation flagged pending and a `〔static:〕` marker that repairs the registered claim (module 8/8 OK, reproduced). The M-2 ledger is materially more honest: row 7's headline number (65 / exit 0) now reproduces **exactly** and carries a timestamp plus a drift caveat; row 6's attribution is reproducible in full (the family's 5 failures and the six replay IDs match, and the +4 reconciles against the 0.79.0 baseline); row 1's attribution error is corrected; the archive-integrity FAIL is disclosed with FIX-312 registered and the archive file's 条目数 corrected; P3-2/P3-5/P3-6/P3-7/P3-8/P3-9 are all properly closed or honestly disclosed-as-unfixable; and P2-6's process blocker is registered (FIX-314) with a compliant round-2 slot that this round fills.

**Why it still cannot be authorized.** The remediation introduced **two false statements into shipped release documents** — the same defect class that blocked R0. One is a false claim of release state (N-1) in the README the user reads at the M-4 gate; the other (N-2) is a false claim about the published package's file whitelist in the very section that was being repaired, so the section cannot be trusted without re-verification. Both are one-line fixes, but both are inside the pinned artifact and therefore require a re-pin and a fresh freeze verification. Alongside them, three R0 items are only partially closed (P2-1 buckets, P2-3's `files` clause, P2-5's pin, P3-3 row 3, P3-10 `README:442`), and the frozen tree has never been full-suite measured (N-3). The sibling Design R1 independently reached the same conclusion on N-1 and N-3, and also holds a NEEDS_CHANGE with one blocker — so the chain needs one more remediation round plus a re-pin regardless.

**Verdict: NEEDS_CHANGE.** I did not modify any product file; my only write is this report, left untracked so that `git write-tree` remains `88915ed2…`.

---

## 8. Machine recording (mandated command, raw output)

```
$ python skills/software-project-governance/infra/verify_workflow.py review-record --task REL-076 --round 2 \
    --result NEEDS_CHANGE --report docs/reviews/review-REL-076-RELEASE-R1.md --reviewer "Release Reviewer"
{
  "review_id": "REVIEW-REL-076-R2",
  "task_id": "REL-076",
  "round": 2,
  "result": "NEEDS_CHANGE",
  "review_file": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\review-REL-076-R2.md",
  "evidence_row_written": true,
  "wiring": {
    "wired": false,
    "degraded": false,
    "unit_id": null,
    "gate_id": "G9",
    "reason": "role 'RELEASE' maps to gate G9 but no flow-unit id is available (pass --unit or register a unit mapping)"
  },
  "revisit_required": true,
  "next_round": "REVIEW-REL-076-R3",
  "prev_report": "docs/reviews/review-REL-076-RELEASE-R1.md"
}
[exit code: 0]
```

Contrary to R0's §3.8, the mandated command **succeeds** this round: `--round 2` is free because the Design half holds rounds 0 and 1. Written artifacts, verified on disk: `.governance/review-REL-076-R2.md` (10:14:29) and evidence row `REVIEW-REL-076-R2` at `.governance/evidence-log.md:1987` with reviewer `Release Reviewer`; the CLI chained `prev_report` to this report and armed `next_round = REVIEW-REL-076-R3`. **This closes the Design R1's F14** (the checklist's claim at L113/L120 that the Release half was CLI-recorded at round 2 is now factually true).

Two recording-plane observations for the chain (not defects of this artifact):
- `wiring.wired = false` — role `RELEASE` maps to gate G9 but no flow-unit id is available, so the record is not wired to a unit (unchanged behaviour; the CLI reports it rather than failing).
- `revisit_required = true` — consistent with a NEEDS_CHANGE result and with `next_round` being armed. Per FIX-314 the round number is a **slot**, not a fix cycle; the CLI's own `next_round = R3` string does not reflect the chain's actual progression, and the checklist's L113 caveat covers that.

Post-write state re-confirmed: `git write-tree` still `88915ed2606154219561c3828f23dbf390b4dbe2`, staged 33, unstaged 0; the only untracked files are the two R1 reports (`review-REL-076-DESIGN-R1.md`, `review-REL-076-RELEASE-R1.md`), neither of which touches the index.

`unresolved_blockers=2`
