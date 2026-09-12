# REVIEW-REL-076-RELEASE-R0 — Release Review of the 0.80.0 Release Candidate

- **Task**: REL-076 (release 0.80.0, release candidate; version authority = `skills/software-project-governance/SKILL.md` frontmatter `version: 0.80.0`)
- **Round**: R0
- **Reviewer**: Release Reviewer (independent, delegated). **No product file was modified by this review.** The only write is this report.
- **Verdict**: **NEEDS_CHANGE** — `unresolved_blockers=2` (definition in §7)
- **Object reviewed**: `git log v0.79.0..HEAD` = 21 commits (`17eda48..5a259e2`) **plus the uncommitted candidate working tree**. The candidate commit does not exist; the object is therefore a *moving* index + worktree state, and it moved during this review (§1).

---

## 1. Candidate-state drift observed during this review (fact, timestamped)

The candidate state is **not stable** across this review. At the start of the review the worktree was exactly the brief's 26 staged files (`git status --short` → 26 lines, zero untracked). At the time of writing it is:

```
git status --short            # 32 entries
26 × staged (M/A) + 6 × unstaged-only product edits + 1 × untracked review report
```

Unstaged-only edits (all with mtime in the 09:22–09:24 window, i.e. **after** `REVIEW-REL-076-DESIGN-R0` was machine-recorded at 09:17:21):

| File | mtime | Content of the in-flight edit |
|---|---|---|
| `README.md` | 09:22:30 | removes the "every session of that profile" promise (DESIGN-R0 **F2**) |
| `docs/marketplace/dsh-preset-adapter-0.73.0.md` | — | adds a 0.80.0 correction box for the deleted `--mode copy` (F10) |
| `docs/requirements/data-inventory-0.80.0.md` | — | marks three retired symbols (F5) |
| `lib/index.js` | — | edits the `dsh plugin remove` symmetric" header claim (F11) |
| `skills/software-project-governance/core/protocol/plugin-contract.md` | — | adds the "宿主方承诺：架构不变量 I-1/I-2/I-3" section (F7) |
| `docs/release/release-checklist-0.80.0.md` | — | re-scopes RISK-050, rewrites rows #8/#10, fills the M-3 review-evidence section |
| `project/CHANGELOG.md` | — | rewrites the DEC-187 paragraph to the DEC-188 ② criterion (F1) |

`.governance` was rewritten in the same window (`decision-log.md` + `archive/decisions/decisions-v0.1.0-0.78.1.md` + `archive/index.md` at **09:22:52**, `session-snapshot.md` 09:23:38, `plan-tracker.md` 09:24:30) — the DEC-187 re-migration remediation described in the checklist's new §archive-integrity paragraph.

**Consequence for this verdict**: the two P1 blockers below are stated against the state that is *tracked* (index/HEAD), where both defects are still present verbatim. Their fixes exist only as **unstaged** worktree edits that (a) are not in the candidate, (b) have had no gate re-run since, and (c) are accompanied by a self-declared new `check-release` FAIL (§4 P2-4). An R1 round is required to re-verify the *staged* artifact set.

---

## 2. Per-checklist-item verdicts

### Item 1 — Change inventory completeness: **PASS**

`git log --oneline v0.79.0..HEAD` = **21 commits**. The §Change Inventory table (`release-checklist-0.80.0.md:21-45`) has exactly 21 rows, and every commit maps 1:1 to its row (`e9facf5,906b209,4e4de2b,504cc8f,3da4e14,36f2040,c87c47d,70773da,e143508,d6d12e8,9410f80,ebb2dce,f87b2fc,4fcc354,2a5e9ec,e74c0a1,4998c6d,73e04e5,031f0fa,94c0a61,5a259e2`). No commit is missing; no row cites a commit that does not exist; the summary statistics quoted in the rows match `git show --stat` (FIX-310 = 33 files `+1034/−1324`, net −290).

Two precision notes (non-blocking, P3-6 / P3-8):
- The window base is written `v0.79.0 (17eda48)`; `v0.79.0` is an **annotated tag object** `96a0030` that peels to commit `17eda48` — the notation is a correct peel, not a discrepancy (same conclusion as DESIGN-R0 N-8).
- §Review Evidence says "本窗 21 commit 内 **8** 个为审查报告入库"; the window actually contains **9** report-archive commits (8 on line 1 + `73e04e5` for FIX-307), and two further chains (FIX-308, FIX-309) are machine-recorded only in the gitignored `.governance/`, not under `docs/reviews/` (P3-8).

### Item 2 — Version consistency: **PASS, with an unguarded-surface gap**

`python skills/software-project-governance/infra/verify_workflow.py check-version-consistency` → **PASSED, exit 0**, "Files checked: 13 … + bootstrap markers (AGENTS.md, CLAUDE.md)", zero FAIL and zero WARN. Independently scanned every version-bearing marker I could enumerate: `AGENTS.md:5`, `CLAUDE.md:5`, `adapters/dsh/AGENTS.md.template:3`, `commands/governance-init.md:197/262/533`, `project/e2e-test-project/CLAUDE.md:5`, `project/e2e-test-project/commands/governance-init.md` (mirror, hash-identical to source), 4 plugin/manifest JSONs, `package.json`, `core/manifest.json`, 4 hooks `@version`, `agent-presets/governance/agent.cordis.yml.template:51` — **all 0.80.0**. No stale version declaration found anywhere.

**No OTP-invisible mismatch exists in this candidate.** What does exist is a *coverage* gap: `commands/governance-init.md` (the canonical bootstrap template, 3 `@bootstrap-version` markers — the FIX-238.2 staleness authority users receive at init time) is in **none** of the three version gates: not in `core/version-projections.json` (15 projections — read in full), not in `checks/version.py` `VERSION_PATHS`/`entry_names` (source read: `entry_names = ("AGENTS.md", "CLAUDE.md")` only), not in `REQUIRED_SNIPPETS`. The same is true for `project/e2e-test-project/CLAUDE.md` (needle-only guard: `verify_workflow.py:18008`), the release docs' own `**Version**:` lines, and `core/releases/0.80.0.json`. All read 0.80.0 today, so this is a latent gap, not a release defect → **P3-1**.

Related recorded-evidence error → **P3-2**: M-2 row #1 credits `check-version-consistency` with covering `adapters/dsh/AGENTS.md.template`; the gate's own output and source cover only `AGENTS.md` + `CLAUDE.md`. The template is guarded by `check-projection-sync` (projection `dsh-agents-bootstrap-version`), which also passed.

### Item 3 — Manifest / cleanup / projection coupling: **PASS**

- `check-manifest-consistency` → `[PASS]`, canonical 657 (recorded 657 ✓) / actual **731** (recorded 727). Explained, not a defect: `checks/manifest.py:391-403` computes "actual" from `git ls-files --cached`, and the 4 candidate files (3 release docs + `core/releases/0.80.0.json`) became tracked when staged — exactly the +4 the checklist predicted. → **P3-3** records the stale number.
- `check-projection-sync --fail-on-issues` → **PASSED**, "Source version: 0.80.0; Mirrored files checked: 15".
- New files are genuinely covered by the canonical manifest (verified by loading `core/manifest.json` and matching all 152 `path` entries with `fnmatch`): the three new release docs fall under the `repo_only` entry `docs/`, `core/releases/0.80.0.json` under `skills/software-project-governance/core/`, and `lib/index.js` / `agent-presets/governance/preset.yml` have their own explicit entries (manifest lines 243-256).
- Deleted surfaces: `presets/` is absent from the manifest, from `PLUGIN_SCOPE_DIRS` (`cleanup.py:46-63`) and from `cleanup_scope.directories` (`manifest.json:818+`); the two lists are equal as sets (11 dirs). `python …/cleanup.py --dry-run` → `[CLEANUP-ERR-002] No redundant files found. Plugin installation is clean.` — zero residue after the deletions. `presets/` residual cleanup risk for a link-installed upgrade is handled by git (the deletion is committed); no stale `presets/` exists in this checkout.
- `check-cross-references --fail-on-issues` → **PASS** (69 files, 663 references — matches the recorded 663).

### Item 4 — Breaking changes: **three fidelity gaps → P2-3**

The four listed items are each individually verifiable: (1) preset supply path change — `cordis.patch.yml` is exactly one `- insert:` row (read in full; no `!!js`, no `- id: <host>` UPDATE); (2) `dsh.skills` removal — `git show 5a259e2 -- package.json` shows the 35-entry array deleted; (3) `presets/` deletion — `git show 5a259e2 --stat` (`presets/governance/agent.cordis.yml | 292 ------------`); (4) other adapters/core unchanged — only reference/version lines moved.

Gaps:
- **(a) Missing**: `package.json` also gains `"type": "module"`, `"main": "lib/index.js"`, `"exports"`, and **`"engines": {"node": ">=20"}`** (a new runtime floor) — none of which appear in §Breaking Changes. Impact is bounded (the package is `"private": true`, only `lib/index.js` is affected by `type: module`, and pnpm's engine check is advisory by default), but a MINOR release's breaking-change section is the right place for a new engine floor.
- **(b) Under-enumerated**: item 3 names only `presets/`, while the same document's §FIX-310 table (line 60) lists four retired surfaces — `presets/governance/agent.cordis.yml`, `adapters/dsh/preset.yml`, `adapters/dsh/agent.cordis.yml.template`, `package.json` `dsh.skills`. Both adapter files were shipped in 0.79.0 and are now gone.
- **(c) Inaccurate evidence basis**: item 4 says "`check-injection-contract` PASSED 证明核心 prose 零改动". That gate is explicitly a keyword-presence gate — its own source says *"Deliberately asserted as keyword presence, never full-text equality"* (`verify_workflow.py:6595-6604`) — so it cannot prove prose equality; and `skills/…/references/behavior-protocol.md` (2 lines) plus the dsh 平台说明 paragraph in `SKILL.md` **were** edited by `5a259e2` (path-references, but not "仅版本行"). The accurate form of the claim is "the diff touches only version/path-reference lines" — evidenced by `git show`, not by that gate.

### Item 5 — No-overclaim discipline: **needles PASS; two positive overclaims remain in the tracked candidate (P1-1, P1-2)**

Needle check (verified with a content search, not the doc's own word): all three release docs carry `No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure.` — `release-checklist-0.80.0.md:117`, `feature-flags-0.80.0.md:32`, `rollback-plan-0.80.0.md:61`. (My first PowerShell counting loop returned 0 for these needles; the harness content search returned all three lines. The loop was wrong, not the docs — recorded so the next reviewer does not repeat the false positive.)

The **real-machine acceptance face is correctly disclosed as unverified** in all three docs (checklist §真机验收面 lines 91-99; feature-flags line 32; rollback-plan line 13 + 61) and no document claims it was verified. **Confirmed.**

However two positive overclaims survive in the *tracked* candidate:

- **P1-1 — `project/CHANGELOG.md:19` (index blob, `git show :project/CHANGELOG.md`)**: *"机检判据 = 安装后 dsh 组合后 entry 列表与未安装时**逐字节等价**。FIX-310 即按此不变量重做：宿主平面贡献归零…"*. Both propositions are retracted by this release's own records: `DEC-188 ②` (`.governance/decision-log.md:135` — *"「与未安装时逐字节等价」…不可满足…**不再**引用更强口径"*), `RISK-050` (`.governance/risk-log.md:44` — *"（**非**「与未安装时逐字节等价」——DEC-188 ②）"*), and the checklist itself (`:49` *"**不声称「宿主平面贡献为零」**"*; `:62` supplies the corrected criterion). This is the file `check-release --require-changelog` treats as the release's user-facing note. (Independent corroboration of DESIGN-R0 F1 — reached before reading that report.)
- **P1-2 — `README.md:33`, `:76`, `:392` (HEAD/index; unstaged fix only)**: the README promises the governance skills and `/governance` projections load *"in **every session of that profile**"* / *"在该 profile 的**每个会话**中可用"*. That availability came from the host-plane `skill-filesystem` UPDATE row deleted by FIX-310; skills now reach only sessions mounting the governance preset. The candidate's own acceptance target is the opposite (`release-checklist-0.80.0.md:96` lists "非治理预设（如 `standard`）会话**不含**治理技能" as an **unverified** acceptance item). Verified against HEAD directly: `git show 5a259e2:README.md` still contains `every session of that profile` and `每个会话`. (Independent corroboration of DESIGN-R0 F2.)

### Item 6 — M-2 table honesty: **two rows do not fully reproduce (#7 composition → P2-1; #6 failure count → P2-5)**

Full ledger in §3. Five rows re-run byte-for-byte identical (#1, #2, #4, #8, #9) plus #12; #5 reproduced through `check-release`'s nested execution gate; #3 reproduces its verdict with an explained +4 count; #10 reproduces with exactly the predicted −3 self-resolution; #11/#13/#14 honestly marked 待回填. **Two rows do not fully reproduce: #7 (61 recorded → 62 measured, and the stated composition is wrong → P2-1) and #6 (collection 2675 reproduced, but 36F+1E=37 measured vs 32 recorded → P2-5).** No row claims a PASS that the Coordinator did not measure.

### Item 7 — Rollback plan: **PASS (internally consistent; no silent re-introduction path)**

- Trigger set matches the checklist's gate numbering (#1-#10) and the candidate's own posture; trigger #4 ("Check 28v FAIL on a real dsh → fix the composition, not the guard") and trigger #6 (M-3 NEEDS_CHANGE ≥ round 3 → freeze) are consistent with the release chain.
- **No silent re-introduction of the removed architecture.** The one path that would restore the pre-FIX-310 shape (`git revert 5a259e2`) is disclosed as such in `rollback-plan-0.80.0.md:36` — it states the revert re-introduces the RISK-050 root cause and mandates a DEC + a new disposal task. The user-side ordering is also correct: `dsh plugin remove` **first**, then delete the rendered user-root preset (`:37`), which is the right order because `ensurePreset()` re-renders on the next boot while the bundle row is still installed (the Reversibility table line 56 says "重启自动重建" — consistent).
- Mechanism claims check out against the installed host: `dsh plugin` is a pnpm forwarder that reconciles `dsh.profile.bundles` against installed state (`…/node_modules/@deepseek-ai/dsh/lib/plugin-Ddi42qoW.js:9-14,35-43,109`), so both `add` and `remove` (pnpm verbs) genuinely add/drop the bundle layer — including the removal step the rollback plan relies on.
- Residual precision note (P3-7): "staging+rename **原子**" (checklist `:57`, feature-flags `:23`) is stronger than the code — `lib/index.js:210-211` does `rmSync(userDir)` then `renameSync(staging, userDir)`, a replace-with-a-window; a crash inside the window leaves the preset absent until the next boot (self-healing, because the version marker left with the directory). The module's own docstring scopes this correctly ("can never leave a half-rendered preset"), so this is wording, not behaviour.
- Revert/dependency ordering (`:39-40` — 310 before 307; FEAT-026 → FIX-305 → FEAT-022 → FIX-304 → FEAT-025 → FIX-303 → FEAT-021) is dependency-sound (consumers before their producers); the list places the not-included `FIX-306` between two reverted nodes with only a "(未入)" marker, which is slightly confusing but not wrong.
- The plan honestly declares that the S1 full-revert path was **never executed** (`:63`) and that it is an analysis carrier, matching the 0.76.0/0.77.0/0.78.1/0.79.0 precedent.

---

## 3. M-2 reproduction ledger (rows re-run by this reviewer)

| # | Command | Recorded | Measured by me | Verdict |
|---|---|---|---|---|
| 1 | `check-version-consistency` | PASSED, zero FAIL/WARN | **PASSED**, exit 0, 13 files + AGENTS.md/CLAUDE.md markers | reproduced (attribution note P3-2) |
| 2 | `check-projection-sync --fail-on-issues` | PASSED, source 0.80.0, 15 | **PASSED**, source 0.80.0, 15 | reproduced |
| 3 | `check-manifest-consistency` | PASS, 657 / 727 | **[PASS]**, 657 / **731** | verdict reproduced; count delta explained (+4 staged) |
| 4 | `check-cross-references --fail-on-issues` | PASS, 663 refs | **PASS**, 69 files / 663 refs | reproduced |
| 5 | `verify` (no arg) | PASSED exit 0 | `[PASS] verify (exit=0)` inside `check-release` | reproduced (nested invocation) |
| 6 | full unittest run | `Ran 2675`, `failures=30, errors=2, skipped=1` = 32 = 0.79.0 baseline | **`Ran 2675 tests in 756.659s`, `FAILED (failures=36, errors=1, skipped=1)` = 37** | collected count reproduced exactly; **failure count NOT reproduced (+5)** — see §3.6 (run raced the in-flight edits) |
| 7 | `check-governance --summary-only` | 61 issues, exit 0 | **62 issues, exit 0** | exit code reproduced; **number + composition NOT reproduced** (P2-1) |
| 8 | `check-injection-contract` | PASSED, 3 files / 23 anchors | **PASSED**, 3 files / 23 anchors | reproduced |
| 9 | `check-dsh-preset-compat` | PASSED, 1 comp / 23 rows / 18 schema-checked, writes 0 | **PASSED**, identical + same 4 oracles | reproduced |
| 10 | `check-release --version 0.80.0 --require-changelog --lineage-mode candidate` | static all PASS; **FAILED - 9 issue(s)** | static all PASS **including `release docs`**; **FAILED - 6 issue(s)** | reproduced; −3 = exactly the predicted "release docs ×3 commit 后自消" (my run: already resolved by *staging*) |
| 11 | `release-ledger --version 0.80.0 --no-remote` | NATIVE_CANDIDATE (after commit) | `trust_level: NATIVE_CANDIDATE`, `candidate_commit: null`, exit 1 | consistent with 待回填 |
| 12 | `quality-tools` | NOT_RUN (tools absent) | **NOT_RUN** for all five tools | reproduced |
| 13/14 | released-mode / remote ledger | 待 M-6 | not run (post-tag) | correctly marked pending |

Extra gates run by me (beyond the M-2 table): `archguard-ratchet` → **PASS (0 violations; R1 24204≤24204, R4 1298≤1298, R5 82/82+70/70, R7 regen deterministic + committed==fresh True)**; `cleanup.py --dry-run` → no redundant files; `check-archive-integrity` → **FAIL (exit 1)** — see P2-4.

### 3.6 Row #6 (full unit-test baseline) — independently re-run, **not reproduced**

Command: `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests` (CI-equivalent form, `.github/workflows/ci.yml`). First run 762 s (output tail lost); capturing run: **`Ran 2675 tests in 756.659s` → `FAILED (failures=36, errors=1, skipped=1)` = 37**.

- **Collection count reproduces exactly** (2675 = recorded 2675), so the test set is identical.
- **Failure count does not**: 36F+1E=37 measured vs the recorded 30F+2E=32 (`"零新增失败 … 与 0.79.0 基线 31F+1E=32 同数"`).
- Family decomposition of my run: **24 = `test_pre_commit_review_evidence.ReviewEvidenceRegexTests` × 2 hooks — the recorded WSL family, exactly as recorded**; then 2 (`FIX300DualCaliberAgreementTests`), 2 (`loop_runtime_claims`: inventory + performance), 1 (`LoopRuntimeClaimAdapterTests`), 1 (`change_triage.AgentLocksAcquireCliTests`), 1 (`triage_write_guard` live canary) — all as recorded — **plus 5 `test_hooks.PlanTrackerMatcherTests.test_replay_real_plan_tracker_hits` (FIX-282/283/288/REL-071/REL-073; recorded as "hooks REL-071 replay 1") and 1 `test_readme_evidence_levels.RealReadmeBaselineTests.test_real_repo_readme_claims_all_annotated` (not in the recorded composition at all)**.
- **Attribution (evidence-based, not a conclusion of regression)**: my run **raced the in-flight remediation**. `test_readme_evidence_levels` asserts on `README.md`, which was edited at **09:22:30**, mid-run; the hook-replay family replays archived task IDs against the hot `.governance/plan-tracker.md`, which was rewritten at **09:24:30**, also mid-run (the DEC-187/archive re-migration at **09:22:52** changed `archive/index.md` and the archive files). So the +5 is most plausibly governance-data/README churn during the run rather than a product regression — but I **cannot confirm "zero new failures"**, and the recorded row must be treated as `未独立复验` until it is re-measured on a frozen candidate (R1), with `.governance` untouched for the duration.
- The recorded row's other claim **is** reproduced verbatim by my `check-release` run: `unit tests: command did not complete: … timed out after 180 seconds` → `exit=None` inside the gate.

### 3.7 Row #7 — the row I could not reproduce (P2-1)

`check-governance --summary-only` → `Governance: 62 issues`, exit 0 (advisory posture reproduced). `--level strict` enumerates 56 report lines whose buckets are: 18d ×8 (FEAT-023/024/026/027 — **FEAT-025 is not flagged**), 18f ×12, 18i ×4, 28n FAIL ×2, 28p ×3, 28s ×2, 30 ×1 ("6 closure violation(s)"), 31 ×3, 34 ×1 ("9 violation(s)"), plus WARN 5/13/14/17×6/26/28n×6/28q×3/29/30c/35/36/39. The recorded composition ("+25 = FEAT-023/024/025/026/027 … +4 untracked … 其余 32 = 存量族 (… 454 structural …, hooks_drift ×4 …)") therefore does not describe the measured set: FEAT-025 has no 18d FAIL, the 18f/18i/28p/34/WARN-17 buckets are unlisted, and the sub-counts have moved (structural **417** vs 454; `hooks_drift` **×2** vs ×4 — now exactly `post-commit` and `prepare-commit-msg`, whose installed copies read `@version: 0.79.0` and `0.75.0` while the source reads 0.80.0; `plan-tracker.md` 303.1 KB vs 301.3 KB; `evidence-log.md` 1454.5 KB vs 1450.3 KB — the governance files grew after the M-2 snapshot, which is the expected direction since the M-2/EVD rows were written afterwards). The checklist's own rollback trigger #3 treats baseline drift as needing re-measurement, so the fix is a re-measure at M-6, not a code change.

### 3.8 The mandated machine-record command **fails** (raw error, verbatim)

```
$ python skills/software-project-governance/infra/verify_workflow.py review-record --task REL-076 --round 0 \
    --result APPROVED_WITH_NOTES --report docs/reviews/review-REL-076-RELEASE-R0.md --reviewer "Release Reviewer"
{
  "error": "review record already exists: D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\review-REL-076-R0.md — refusing to overwrite (FIX-289⑤ task+round record guard; historical backfill data is protected). To replace it deliberately, re-run with force=True: the previous record is backed up and the overwrite is marked in the new record."
}
[exit code: 2]
```

The `--result` value used was `APPROVED_WITH_NOTES` (the literal set offered by the brief); the guard fires **before** any validation of the result value, so the refusal is independent of it. Cause: the Design Reviewer's half of the M-3 double review already occupies `(task=REL-076, round=0)` — `.governance/review-REL-076-R0.md`, written 09:17:21 by `review-record`. The guard keys on **task+round only** (`review_record.py:23-25`, `:182` — the file name is `review-{task}-R{round}.md`), so the repository's model cannot hold two independent reviewers' records at the same round. I did **not** work around this: forcing would overwrite and re-label the Design Reviewer's record (the CLI's own `force=True` path backs the old one up and marks the overwrite), and hand-writing a `REVIEW-{id}` evidence row is a documented process violation. **The recording step is therefore blocked by a tooling/process limitation, not by the review** — the Coordinator owns the adjudication (see P2-6).

---

## 4. Findings

Severity key: **P0** = must not ship / broken; **P1** = must fix before release authorization; **P2** = should fix (release-blocking only if unaddressed); **P3** = discussion / precision.

### P0 — none
No gate failure, corruption, data-loss path, or invariant violation was found in the delivered code. The architecture claims of FIX-310 hold under my own independent checks (§3, item 7 mechanism check, `cordis.patch.yml` single-insert read, `lib/index.js` export surface = exactly `name` / `renderComposition` / `ensurePreset` / `apply`, `ctx.*` = `ctx.logger` only, no `rmSync` outside the preset id directory).

### P1-1 — the tracked CHANGELOG asserts both claims DEC-188 was written to retire
**File/line**: `project/CHANGELOG.md:19` (index blob; `git show :project/CHANGELOG.md`) — *"机检判据 = 安装后 dsh 组合后 entry 列表与未安装时**逐字节等价**。FIX-310 即按此不变量重做：宿主平面贡献归零（…不声明 system-trust 预设根）。"*
**Contradicted by**: `.governance/decision-log.md:135` (DEC-188 ②), `.governance/risk-log.md:44` (RISK-050 correction), `docs/release/release-checklist-0.80.0.md:49` and `:62`.
**Command evidence**: `git show :project/CHANGELOG.md | Select-String '逐字节等价|宿主平面贡献归零'` → present; working tree already carries the corrected sentence (unstaged, `git diff -- project/CHANGELOG.md`).
**Status**: open against the tracked candidate; the fix must be staged and the CHANGELOG re-read in R1.

### P1-2 — the tracked README promises governance skills in every session of the profile
**File/line**: `README.md:33` ("load **in every session of that profile**"), `:76` (same clause), `:392` ("在该 profile 的**每个会话**中可用").
**Contradicted by**: the delivered form (skills reach only preset sessions after `5a259e2` deleted the host-plane `skill-filesystem` UPDATE row) and by the candidate's own acceptance item `release-checklist-0.80.0.md:96`, which is listed as **unverified** with the opposite target ("非治理预设会话不含治理技能").
**Command evidence**: `git show 5a259e2:README.md` still contains `every session of that profile` and `每个会话`; the wording is still in HEAD and in the index (`git diff --cached -- README.md` = 0 entries). Unstaged fix exists (README mtime 09:22:30).
**Why it matters**: this is the sentence a user reads while performing exactly the acceptance step the release declares unverified.

### P2-1 — M-2 row #7 recorded number and composition are not reproducible
See §3.7. **File/line**: `release-checklist-0.80.0.md:76`. Recommend re-measurement at M-6 against the final `.governance` state, with the bucket list generated from `--level strict` rather than summarised by hand.

### P2-2 — the checklist asserts the settings-page outcome as delivered while declaring it unverified
**File/line**: `release-checklist-0.80.0.md:56` ("设置页显示为「自定义」，可删除 / 可打开目录" — stated as delivered form with `lib/index.js` cited as evidence) and `:125` ("用户可见差异：设置页标签变为**「自定义」**、可删除、可打开目录") versus `:91-97` (§真机验收面: the same three behaviours are "**未在本候选内验证**"). `feature-flags-0.80.0.md:23` carries the same claim.
**Assessment**: the *code* fact (user-trust preset root) is verified; the *host behaviour* (settings-page label / delete / open-folder) is an inference about dsh's UI and is what the candidate itself refuses to claim. Both places should be expectation-scoped ("期望显示为『自定义』——真机验收面未验证"), as DESIGN-R0's U-1 also notes. Not touched by the in-flight remediation.

### P2-3 — §Breaking Changes has three fidelity gaps
See item 4 above: (a) missing `engines: node>=20` / `type: module` / `main` / `exports`; (b) item 3 enumerates only `presets/` while four surfaces were retired; (c) item 4's "check-injection-contract PASSED 证明核心 prose 零改动" overstates a keyword-presence gate, while `references/behavior-protocol.md` and the dsh 平台说明 paragraph in `SKILL.md` were in fact edited by `5a259e2`.

### P2-4 — archive integrity is FAILing at review time; the archive file's own count is now wrong
**Command**: `python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity` → **FAIL, exit 1**: *"Archive trigger gap: 0 hot completed task(s) should be archived via release_forced for v0.1.0~v0.78.1"*; counters **hot 85 / archived 91 / index 1080 / total 176** (the checklist's §归档迁移执行证据 records index **1081** and PASS).
**Cause (as now disclosed by the in-flight checklist update)**: the DESIGN-R0 F4 remediation moved DEC-187 out of `archive/decisions/decisions-v0.1.0-0.78.1.md` back into the hot `decision-log.md` at 09:22:52, and the engine's `analyze_auto_archive_candidates()` now mis-attributes that current decision to the v0.77.0 range because its related-task column contains `FEAT-010`.
**Additional, so-far-undisclosed residue (new)**: that archive file's header still declares `- **条目数**: 5` while the file now contains **4** entries (`## DEC-174/176/177/182`, verified by heading scan) — the re-migration did not update the count, and `archive/index.md` no longer carries a DEC-187 entry.
**Impact**: `.governance` is gitignored and outside the candidate diff, but `check-release`'s `archive integrity` component is part of the M-2/M-6 gate set, so the release gate will FAIL until FIX-312 (or a data repair) lands. The FAIL itself is now disclosed in the checklist's updated row #10 + dedicated paragraph; the stale `条目数` is not.

### P2-5 — M-2 row #6 ("zero new failures") cannot be confirmed on the current tree
**File/line**: `release-checklist-0.80.0.md:75`. My independent full-suite run reproduces the collection count exactly (**2675**) but reports **36F+1E=37** against the recorded **30F+2E=32**; +5 = 4 extra `test_hooks.PlanTrackerMatcherTests.test_replay_real_plan_tracker_hits` cases (FIX-282/283/288/REL-073 besides the recorded REL-071) and 1 `test_readme_evidence_levels.RealReadmeBaselineTests.test_real_repo_readme_claims_all_annotated`. Both surfaces were being edited **during** my run (`README.md` 09:22:30; `.governance/plan-tracker.md` 09:24:30; archive/index 09:22:52), so the delta is most plausibly churn, not regression — but the claim as recorded is **not reproducible** and must be re-measured on a frozen candidate in R1 (do not re-use this delta as evidence of a regression, and do not re-use the recorded 32 as evidence of zero-new-failures either).

### P2-6 — the M-3 double review cannot be machine-recorded as two reviewers in one round (my record is refused)
**Evidence**: §3.8 raw error, `[exit code: 2]`, from the exact command this review was told to run. Cause: `review_record.py` keys records on `(task, round)` alone (`:23-25`, `:182`), and the Design Reviewer's REL-076 R0 record already occupies that key.
**Impact**: the checklist's own M-3 section now reads `REVIEW-REL-076-RELEASE-R0：待回填` — a slot the CLI cannot fill while the Design record exists. Unless the chain's owner acts, the Release half of the M-3 double review will not appear in `.governance/evidence-log.md`, and `check-governance` Check 30/30c (review machine provenance / `next_round` wiring) will not see it.
**Options for the Coordinator (not taken by me — this review modifies nothing)**:
1. Record the Release half under a distinct round (e.g. `--round 1`), accepting that `next_round`/`prev_report` wiring then chains Release-R1 to Release-R0; or
2. Deliberately force the `(REL-076, 0)` key through the **library** API `review_record.write_review_record(..., force=True)` (per DEC-174 the CLI intentionally has no `--force` flag), accepting the backup + `force_overwrite` marker on the Design record — only defensible if the chain treats "REL-076 R0" as one round with two report artifacts; or
3. Extend the guard's key to `(task, round, reviewer)` as its own task (the two-reviewer model is otherwise unrepresentable).
**Not acceptable**: hand-writing a `REVIEW-REL-076-R0` evidence row (behavior-protocol M7.5: *"手写 REVIEW-{id} 证据行 = 流程违规"*).

### P3-1 — version-bearing surfaces outside all three version gates
`commands/governance-init.md:197/262/533` (and its byte-identical fixture mirror), `project/e2e-test-project/CLAUDE.md:5`, the three release docs' `**Version**:` lines, `core/releases/0.80.0.json:"version"`. All currently 0.80.0 → **no mismatch**; the class is latent (a future bump can ship a stale init-time bootstrap template — the FIX-238.2 failure mode). Recommend adding `commands/governance-init.md` to `core/version-projections.json` as a `transformed_text` projection.

### P3-2 — M-2 row #1 attribution error
Row #1 credits the marker face with `adapters/dsh/AGENTS.md.template`; the gate covers `AGENTS.md` + `CLAUDE.md` only (`checks/version.py:122-137`). The template is projection-guarded. Verdict unaffected.

### P3-3 — recorded numbers that no longer reproduce
`check-manifest-consistency` 727 → 731 (explained); `check-governance` 61 → 62 (P2-1). Both are live-data drift, not fabrication; record the measurement time alongside the number next time.

### P3-4 — the candidate moved during the review
See §1. For R1, pin the exact blob set (`git write-tree` / stage-then-review) so the reviewed artifact is immutable. Six product files plus two index files changed without a commit or a gate re-run between the Design R0 and this review.

### P3-5 — the candidate commit will be created with stale local hooks
`.git/hooks/post-commit` `@version: 0.79.0` and `.git/hooks/prepare-commit-msg` `@version: 0.75.0` vs source `0.80.0` (pre-commit and commit-msg are correctly 0.80.0). This is disclosed only implicitly through the `hooks_drift ×2` advisory; the repo cannot self-install hooks (agent must not write `.git/hooks`), so a one-time user command is required before the release commit if the 0.80.0 panels are wanted for that commit.

### P3-6 — commit-message scope claim contradicts the commit
`5a259e2` body: *"规模 10 文件 +296/-552（净减 256 行）"*; `git show --stat 5a259e2` = **33 files changed, 1034 insertions(+), 1324 deletions(−)**. The release docs use the correct figures (`:45`), so only the commit message is wrong.

### P3-7 — "staging+rename 原子" is stronger than the code
See item 7. `lib/index.js:210-211` (and `adapters/dsh/launch.py` equivalently) delete-then-rename; a crash in the window leaves no preset until the next boot. Prefer the module docstring's wording.

### P3-8 — review-evidence attribution is imprecise
`release-checklist-0.80.0.md:103` heads the list "（已机录，`docs/reviews/`）" and gives "8 个为审查报告入库"; the window has 9 such commits, and FIX-308's and FIX-309's reports exist only under the gitignored `.governance/` (`review-FIX-308-CODE-R0.md`, `review-FIX-309-CODE-R0.md`/`-R1.md`, with machine evidence rows `REVIEW-FIX-309-R0/R1` in `evidence-log.md:1973/1975`). The chains **are** machine-recorded and their verdicts (R0 NEEDS_CHANGE/1 → R1 APPROVED_WITH_NOTES/0) are backed — the point is only that "docs/reviews/" is not where two of them live.

### P3-9 — dangling internal reference in the checklist
`release-checklist-0.80.0.md:66` says the candidate commit hash is "待回填（见 §Candidate 元数据）"; no section by that name exists (headings: L1, 7, 21, 47, 64, 91, 101, 108, 115, 123). `check-cross-references` cannot see prose anchors, hence PASS.

### P3-10 — pre-existing stale README statement carried into this release
`README.md:92` and `:440` still say "before v0.79.0 is pushed: GitHub's master still serves 0.78.1". Introduced by `d995df5` (REL-075, 2026-09-10), i.e. **not** this window, but `v0.79.0` is now tagged, so the sentence is stale and will be more wrong after 0.80.0. Not gated by anything.

---

## 5. `未知` (explicitly not verified here — no file, command, or user statement available to me)

1. **REV-076** — the brief calls the plan-tracker artefact "the REV-076 / REL-076 row". No `REV-076` identifier exists anywhere (`git grep -n REV-076` → 0 hits; `.governance/plan-tracker.md` contains `REL-076` at L198 and the release row at L11). Whether a separate REV-076 row was required is **未知**; I did not assume it, and the machine record below uses `--task REL-076` exactly as instructed.
2. **Real-machine acceptance face** — settings-page 「自定义」/ delete / open-folder, non-governance sessions free of governance skills, governance session skill-catalog completeness. Only the user's environment can answer; the candidate declares them unverified.
3. **CI ubuntu authoritative face (W-1)** — no credentials here; not run. The local Windows run cannot substitute.
4. **M-3 "double review" completeness** — the Design half exists (`docs/reviews/review-REL-076-DESIGN-R0.md`, machine record `.governance/review-REL-076-R0.md`, NEEDS_CHANGE/2), but there is **no post-DEC-187 Code review** of `lib/index.js` / the reworked `launch.py` anywhere in the window (no `REVIEW-FIX-310-*` under `docs/reviews/`; the only FIX-310 records are the voided `.governance/review-FIX-310-R0/R1/R2.md`). Whether the M-3 "candidate double review" was intended to substitute for it is **未知**.
5. **Reference-implementation quotes** (`dsh-novel-writing`) — DEC-188 and the commit message quote its `cordis.patch.yml` and `lib/index.js`; I did not locate/verify that repository and therefore do not treat the quotations as evidence. (The mechanism I *could* check — that `dsh plugin add` reconsiles `dsh.profile.bundles` from a `dsh.bundle` declaration — I verified against the installed host: `…/@deepseek-ai/dsh/lib/plugin-Ddi42qoW.js`.)
6. **Cross-root path stability under `link:` installs** — `launch.py` resolves symlinks, `lib/index.js` does not; whether the two paths always write the same destination after an install/update cycle is not verifiable from this repo.
7. **Row #6's "zero new failures" claim** — my run collected the same 2675 tests but reported 37 failures vs the recorded 32, while the tree was being edited; whether the baseline is genuinely unchanged is `未知` until a frozen-tree re-run (§3.6). I neither confirm nor refute it.
8. **W-1 / post-release obligations** (CI face, release-ledger remote, tag peel) — post-M-4/M-6.

---

## 6. Brief premises that did not survive verification

Per the standing warning about fabricated premises, I checked the review brief itself:

- "**21 commits (`17eda48..5a259e2`)**" ✅ verified (`git log --oneline v0.79.0..HEAD` = 21; `v0.79.0` = annotated tag `96a0030` peeling to `17eda48`).
- "**26 files, currently staged**" ✅ true at 09:0x; **no longer true** at report time (26 staged + 6 unstaged product edits + 1 untracked report) — §1.
- "**FIX-310 (`5a259e2`, 33 files +1034/−1324)**" ✅ verified.
- "**FIX-309 (`94c0a61`, adds Check 28v)**" ✅ verified (commit contents + `check-dsh-preset-compat` PASSED).
- "**the 15 version projections**" ✅ verified (`core/version-projections.json`, 15 entries).
- "**4 `.git/hooks`-shipped hook scripts**" ✅ verified (`infra/hooks/{pre,commit-msg,post,prepare-commit-msg}`, all `@version: 0.80.0`).
- "**`.governance/decision-log.md` (DEC-187, DEC-188)**" ⚠️ **half wrong at the time the brief was written**: DEC-187 had been mis-archived and was *not* in the hot file (DESIGN-R0 §1.1, corroborated by the row's own annotation "于归档迁移中被误归档…已回迁热文件" and by the 09:22:52 mtime). DEC-187 is in the hot file **now**. DEC-188 is at `:135`.
- "**governance records … `.governance/plan-tracker.md` (REV-076 / REL-076 row, `工作流版本` line)**" ⚠️ `工作流版本: 0.80.0` ✅; `REL-076` ✅ (L198); `REV-076` — **no such identifier** (see 未知 #1).
- "**EVD-1003/1004/1005/1006**" ✅ all four exist (`evidence-log.md:1961/1977/1980/1981`); EVD-1006 is the REL-076 M-1/M-2 record.
- "**two independent main lines**" ✅ matches the checklist §Release Scope and the commit inventory.

---

## 7. Conclusion

The **delivered code** of this candidate is the strongest part of it, and I verified the load-bearing claims myself rather than from the release prose: the bundle layer is structurally incapable of touching an existing host row (one `insert` key, one row, no reachable `!!js`), the host row publishes nothing and reads no host service, the retirement of `presets/` + `dsh.skills` is complete across manifest/cleanup-scope/registry/contract-matrix with green fan-out tests and zero cleanup residue, the renderer parity and warn-only contracts are test-covered, and the rollback plan neither hides nor silently re-opens the removed architecture. Gate reproduction is excellent: six M-2 rows reproduce byte-for-byte, `check-release`'s static set is fully green, and its residual FAIL count reproduced with exactly the self-resolution the checklist predicted.

The **release-artifact plane** is not ready. Two P1 defects sit in tracked, user-visible release surfaces — the CHANGELOG asserts the two propositions DEC-188 was written to retire, and the README promises per-session global governance skills that FIX-310 exists to remove — and both are still present in the index at report time (their fixes exist only as unstaged worktree edits made after the Design R0). On top of that, the candidate working tree changed under this review, two M-2 rows do not reproduce (#7 composition, #6 failure count — the latter measured while the tree was being edited), the breaking-change section under-describes three surfaces, and the archive-integrity gate is currently FAILing. None of these is a product defect; all of them are things an M-4 authorization would freeze into a release. **NEEDS_CHANGE, with one re-review round (R1) after the remediation batch is staged and the gates re-run on a frozen tree.**

I did not modify any product file. My only write is this report.

**One process blocker is reported separately from the verdict**: the mandated `review-record` command is refused (exit 2) because the round-0 key is already held by the Design Reviewer's record, and the CLI (by design, DEC-174/FIX-289⑤) cannot hold two reviewers at one round — §3.8 / P2-6. That blocks the *machine recording* of this review, not the review itself, and it needs a decision from the release-chain owner.

`unresolved_blockers=2`

> **Definition used**: `unresolved_blockers` = findings that must be closed before this candidate may proceed to M-4 user authorization = **P1-1** (CHANGELOG asserts the two DEC-188-retracted claims) + **P1-2** (README promises governance skills in every session of the profile, contradicting the release's own unverified acceptance target). P2/P3 findings are recorded for the fix batch and do not by themselves block authorization; §5 items are declared `未知` and are not counted, because each is a verification I am not positioned to perform (the largest being the real-machine acceptance face, which only the user can run).

unresolved_blockers=2
