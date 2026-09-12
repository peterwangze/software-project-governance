# REVIEW-REL-076-DESIGN-R1 — Design Re-Review of the 0.80.0 Release Candidate

- **Task**: REL-076 (release 0.80.0, release candidate)
- **Round**: R1 (mandatory re-review of the R0 fix batch)
- **Reviewer**: Design Reviewer (independent, delegated; no product file modified)
- **Verdict**: **NEEDS_CHANGE** — `unresolved_blockers=1` (definition in §9)
- **Predecessor**: `docs/reviews/review-REL-076-DESIGN-R0.md` (NEEDS_CHANGE, `unresolved_blockers=2`, findings F1–F11)
- **Date of review**: as recorded by `review-record` (see machine record)

---

## 1. Artifact freeze — VERIFIED

| Check | Required | Observed | Result |
|---|---|---|---|
| `git write-tree` | `88915ed2606154219561c3828f23dbf390b4dbe2` | `88915ed2606154219561c3828f23dbf390b4dbe2` | **MATCH** |
| Staged files | 33 | `git diff --cached --name-only` → 33 | **MATCH** |
| Untracked files | 0 | `git ls-files --others --exclude-standard` → 0 | **MATCH** |

**The artifact did not move.** The hash was re-confirmed *after* all verification reads and *after* my only write (this report) — writing an untracked file does not touch the index, so the pinned tree is unchanged.

Commands (first action of this review, before any file read):
```
git write-tree                                        → 88915ed2606154219561c3828f23dbf390b4dbe2
git diff --cached --name-only | Measure-Object -Line  → 33
git ls-files --others --exclude-standard | Measure... → 0
```

**Note on the frozen surface vs. the governance surface.** `.gitignore:10` is `.governance/`, so the entire governance directory is untracked and is **not** part of the pinned artifact. F3/F4 and the F8/F9/FIX-312/FIX-313 registrations therefore live *outside* the frozen surface: they cannot be pinned by `git write-tree` and their state is "as of review time", not "as of the candidate". This is inherited from R0 (F3/F4 were governance findings there too) and is not a defect — but every governance-side verdict below is timestamped by that caveat.

---

## 2. F1 and F2 re-read from the STAGED INDEX BLOBS (as instructed)

At R0 the blocking problem was that the fixes existed only in the working tree while the index still carried the retracted text. Both are now **in the index**.

```
git show :project/CHANGELOG.md | Select-String '架构不变量|逐字节等价|宿主平面贡献归零|宿主既有行零触碰|DEC-188'
git show :README.md           | Select-String 'every session|每个会话|standard|governance skills|治理 skills'
```

Neither blob contains an unqualified assertion of the retracted wording (full sweep in §4).

---

## 3. Per-finding closure verdicts

Severity key (unchanged from R0): **P0** must not ship / broken; **P1** must fix before release authorization; **P2** should fix; **P3** discussion.

### F1 — P1 — shipped CHANGELOG asserted both superseded claims → **已关闭**

**Evidence** — `project/CHANGELOG.md:19` (staged blob; `git show :project/CHANGELOG.md`):

- The DEC-188 ② criterion is now stated in full: *"**机检判据（DEC-188 ② 澄清）**：`dsh --profile <p> --dump-config` 安装前后，**既有**宿主行的存在性 / `config` / `disabled` 与任何宿主平面注册表内容**零变化**，组合 entry 列表**恰多一行且该行只命名本包**"*.
- The stronger criterion is an explicit **negation**, with the reason: *"——**不是**「与未安装时逐字节等价」（后者在「官方 `dsh plugin add` 零手工步骤即交付预设」同时成立时不可满足：那一行正是官方安装命令的交付载体，参照实现 `dsh-novel-writing` 同形）"*.
- The retracted phrase is gone: **`宿主平面贡献归零` → 0 occurrences** in the staged CHANGELOG; replaced by *"**宿主既有行零触碰**（不改任何既有行、不注册全局 provider / 服务 / 工具、不声明 `system`-trust 预设根、无 `!!js` 自定位）"*.

Bonus: the row's `!!js` clause is now also asserted, which the R0 text omitted.

**Leftover-characterisation check:** `逐字节等价` still occurs on this line, but only inside the negating parenthetical. That is correct usage, identical in kind to `release-checklist-0.80.0.md:62` which R0 already accepted.

### F2 — P1 — README asserted per-session global skill availability → **已关闭**

**Evidence** — three sites, all in `git show :README.md`:

| Site (staged line) | R0 text | R1 text |
|---|---|---|
| `README.md:33` (English adapter table) | *"load in **every session of that profile**〔isolation: 2026-09-05 …〕"* | *"load **in that preset's sessions only** (other presets such as `standard` carry no governance skills; this scoping is FIX-310's core behavioural goal and its real-machine confirmation is still pending)"* |
| `README.md:76` (English install section) | same clause, same stale `2026-09-05` citation | *"load **in that preset's sessions only** — sessions on other presets (e.g. `standard`) carry no governance skills (this scoping is FIX-310's core behavioural goal; its real-machine confirmation is still pending — see the release checklist's acceptance face)"* |
| `README.md:393` (Chinese dsh section) | *"在该 profile 的**每个会话**中可用〔isolation: 2026-09-05 …〕"* | *"在该预设的会话中可用——**仅在治理预设的会话中**；其它预设（如 `standard`）的会话不含治理技能（这是 FIX-310 的核心行为目标）〔static: … **无会话级执行证据**〕。⚠️ **该作用域的真机确认仍未完成**…（旧文案曾称「该 profile 的每个会话中可用」——那是 FIX-310 之前宿主平面全局注册时代的语义，已随宿主行 UPDATE 一并退役。）"* |

All three now match the candidate's own acceptance target (`session-snapshot.md:152` criterion 3) and name `standard` explicitly. `every session of that profile` → **0 occurrences in the staged README**.

**Evidence-marker fix independently reproduced** (the test named in the brief):

```
python -X utf8 -m pytest .../tests/test_readme_evidence_levels.py -q   →  8 passed, exit 0
vw.check_readme_claim_evidence_levels()  →  verdict PASS, claims_checked=6,
                                            claims_annotated=6, warnings=[]
```
`dsh-session-projection` (the claim id targeted by the registry regex at `verify_workflow.py:19624`) is annotated again. The brief's claim that this test was broken by the missing marker and is now fixed is **confirmed** (the checklist self-discloses the incident at `:75`).

Note the Chinese list was also **renumbered** (item 1 = preset roster, item 2 = skills), which is why the third site is now `:393`, not R0's `:392`.

### F3 — P2 — `session-snapshot.md` restated the retracted criterion → **已关闭**

**Evidence** — `.governance/session-snapshot.md:79-81`. L79 still carries the original sentence (un-struck), but a correction box now sits **directly beneath it** (L81):

> `> ⚠️ **判据更正（2026-09-12，DEC-188 ②——本行原措辞已被取代，勿再引用）**：上句「与未安装时逐字节等价」**不可满足**——官方 `dsh plugin add/remove/update` 交付预设的载体就是本包那一行自有 `- insert:`，删掉它「官方安装命令零手工步骤交付」即不成立。**现行判据**：安装前后**既有**宿主行的存在性 / `config` / `disabled` 与任何宿主平面注册表内容**零变化**，组合 entry 列表**恰多一行且该行只命名本包**。I-1/I-2/I-3 本身与导出禁令**不变、永久生效**。`

The retracted text is now explicitly flagged as superseded **in the section that R0 identified as the uncovered one** (the section exempted from the `⛔` blanket supersession at L65 by the carve-out at L71). The contradiction R0 found — "asserted as current in one place, retracted in another" — no longer holds: the assertion site itself now carries the retraction. Adjacent headers (`:148`) and the acceptance list (`:152`) agree with the corrected form.

### F4 — P2 — archived DEC-187 row carried both superseded claims unmarked → **已关闭**

All three required moves verified:

1. **Row returned to the hot file.** `.governance/decision-log.md:135` = DEC-187, between **DEC-186 at L134** and **DEC-188 at L136** — the ordering the brief described.
2. **Clarification note added to the action cell.** The row's tail now carries:
   > `【2026-09-12 DEC-188 澄清（本行 2026-09-12 于归档迁移中被误归档至 v0.1.0-0.78.1 范围，已回迁热文件）】本行「决策/动作」列原记「`cordis.patch.yml` 与 `lib/index.js` 均不保留（宿主平面贡献归零）」**已被 DEC-188 更正**为实际交付形态：`cordis.patch.yml` 保留为**恰一行自有 `- insert:`** …机检判据亦由 DEC-188 ② 澄清为「**既有**宿主行的存在性/config/`disabled` 及任何宿主平面注册表内容零变化、组合 entry 列表恰多一行且该行只命名本包」，**非**「与未安装时逐字节等价」。本 DEC-187 的 I-1/I-2/I-3 与导出禁令**不变、永久生效**。`

   This is the same in-place-replacement pattern R0 accepted for `risk-log.md:44`, and it names both of DEC-187's own retracted propositions. The original text is left in place but is now unambiguously marked superseded **within the same record** — i.e. quoted history, not assertion.
3. **Archive cleaned.** `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md` → **0 occurrences** of `DEC-187`, `逐字节等价`, `均不保留`, `宿主平面贡献归零`; the archived narrative section is gone; the row is gone from `.governance/archive/index.md` (that file's `decisions-v0.1.0-0.78.1.md` rows are now exactly DEC-174/176/177/182). The header `- **条目数**: 4` matches that count — the 5→4 correction is real and internally consistent.

**New consequence — verified and correctly registered.** `check-archive-integrity` now reports exactly what the brief predicted:

```
=== Archive Integrity Check (SYSGAP-030 Check 27) ===
  Hot tasks (plan-tracker): 85 ; Archived tasks: 91 ; Index entries: 1080
  Issues (1):
    - Archive trigger gap: 0 hot completed task(s) should be archived via
      release_forced for v0.1.0~v0.78.1. Run archive.py migrate --auto.
  [FAIL] Archive integrity issues detected.     (exit 1)
```
Registered as **FIX-312 (P2)** at `.governance/plan-tracker.md:84` and disclosed at `release-checklist-0.80.0.md:81` (`⚠️ archive integrity FAIL（M-3 修复期新增，已定位为**引擎缺陷**…）`) and `:118`. The cause is correctly diagnosed as the engine (`analyze_auto_archive_candidates()` following DEC-187's `FEAT-010` reference into the v0.77.0 range), not as a content defect. **Not counted as a blocker**: the FAIL is the *correct* consequence of refusing to archive a live, permanently-effective decision — suppressing it would require re-corrupting the record.

### F5 — P2 — data inventory listed the retired guard as live → **已关闭**

`docs/requirements/data-inventory-0.80.0.md:175-176` — both rows are now struck through cell-by-cell and marked `已退役`:

> `| ~~DSH_SKILLS_DISK_PATTERNS~~ | ~~L6784-L6792~~ | ~~9~~ | ~~tuple[2]~~ | — | **已退役（0.80.0 FIX-310）**…本行原引行号已为空行/无关行（DESIGN R0 F5 更正） | —— | 已退役 |`
> `| ~~_REJECT_SECURITY_DETAIL~~ | ~~L6796-L6801~~ | ~~6~~ | ~~dict[2]~~ | — | **已退役（0.80.0 FIX-310）**——同上…候选实现中 0 次出现（DESIGN R0 F5 更正） | —— | 已退役 |`

The stale line references are struck rather than silently updated, and the correction attributes the change to R0 F5 — the honest form.

### F6 — P2 — "结构性根因消除" over-scoped for the FIX-308 leg → **已关闭**

The requested scoping now appears in **both** files the brief named:

- `release-checklist-0.80.0.md:17` (scope table): *"本版交付**一条腿**的结构性根因消除（上游内部行 UPDATE 面 + `!!js` 自定位面退役）；**另一条腿未消除**——组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema，由 advisory Check 28v 前移护栏（**不声明关闭**）"*.
- `release-checklist-0.80.0.md:133` (the No-overclaim paragraph): *"RISK-050 本版交付**一条腿**的结构性根因消除…但**维持打开**——**另一条腿未消除**（组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema，含 `dsh-persona.config.prefix`；dsh 再改这些行的 schema 时同类漂移仍会发生，由 advisory 级 Check 28v 前移到 CI 护栏而非消除）"*.
- `project/CHANGELOG.md:21` (staged): *"**消除 RISK-050 的一条腿**…**范围限定**：RISK-050 的**另一条腿未消除**——组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema（含 `dsh-persona.config.prefix`）…该腿由 **advisory 级 Check 28v** 前移到 CI（护栏，非消除）；因此**不声明 RISK-050 关闭**"*.

The 23-row Config-schema coupling is now named, the `dsh-persona.config.prefix` surface (R0's exact FIX-308 defect) is named, and the guard is correctly described as a guard rather than an elimination. The `feature-flags-0.80.0.md:32` form R0 held up as the correct model is now matched, not contradicted.

### F7 — P2 — DEC-187's forward deliverable absent from the product surface → **已关闭**

`skills/software-project-governance/core/protocol/plugin-contract.md` now contains a complete section at **L248-266**, positioned **before** `## 当前建议目录布局` (L268) as required:

| Required element | Line | Content |
|---|---|---|
| heading | L248 | `## 宿主方承诺：架构不变量 I-1 / I-2 / I-3（DEC-187，永久生效）` |
| three invariants | L252-254 | I-1 / I-2 / I-3 stated individually |
| DEC-188 ② machine criterion | L256 | *"**机检判据（DEC-188 ②，dsh 适配面）**：安装前后，**既有**宿主行的存在性 / `config` / `disabled` 状态与任何宿主平面注册表内容**零变化**，组合 entry 列表**恰多一行且该行只命名本插件**"* |
| explicit rejection of the stronger form | L257 | *"判据**不是**"与未安装时逐字节等价"…该等价口径已被 DEC-188 明确为不可满足"* |
| five derived prohibitions | L260-264 | `❌` ×5 — no host-row `UPDATE`; no `disabled: false` override; no host-plane provider/service/tool registration; no `!!js` self-location; no `system`-trust preset root |
| delivered-form reference | L266 | `已交付形态（0.80.0 / FIX-310 / commit 5a259e2，作为合规参照）` |

The invariant tokens are no longer confined to code/test comments and governance records: they now exist as contract prose in the shipped skill package.

**Gate impact — independently checked, all clean** (see §5): `check-injection-contract` PASSED (3 files / 23 anchors — unchanged from R0, so the new section neither added nor removed an anchor), `check-manifest-consistency` PASSED, `check-projection-sync --fail-on-issues` PASSED, `check-version-consistency` PASSED, plus `tests/test_contract_matrix.py` **27 passed** (that suite is the one that does snippet-existence assertions against `plugin-contract.md` — `contract_matrix/golden_samples.txt:821-831` — and every asserted snippet still resolves).

### F8 / F9 — P3 — deliberately not fixed → **已关闭（按 P3 登记处置）**

Registered as **FIX-313** at `.governance/plan-tracker.md:85`, priority `**P3**`, version `未规划版本`, status `⏳ 待执行 (2026-09-12)——审查方明确判为 P3、不阻塞 0.80.0`. Both sub-defects are transcribed accurately, including the two facts that make them P3 rather than P1/P2: (a) the lone-CR divergence is latent because the current template yields identical bytes on both renderers; (b) the `.staging-*` leak is **not roster-visible** because `dsh-agent-presets` filters child names with `PRESET_ID=/^[a-z0-9][a-z0-9-]*$/` and the name contains `.`. Also disclosed at `release-checklist-0.80.0.md:110`. Deferral with an accurate, checkable registration is the correct disposition for P3 — **not** a defect.

### F10 — P3 — stale CLI flag in a marketplace doc → **已关闭**（with one P3 residual)

`docs/marketplace/dsh-preset-adapter-0.73.0.md`:
- The command block at **L29-34** no longer contains the `--mode copy` line — L30 is now `python adapters/dsh/launch.py --install` alone, L31 `--bootstrap-project`. R0's cited `:31` (`--install --mode copy   # 自包含快照模式`) is gone.
- A correction box was added at **L36**: *"⚠️ **0.80.0 更正（FIX-310，DESIGN R0 F10）**：上文原有的 `--install --mode copy`（自包含快照模式）**已随 FIX-310 退役**——预设交付改为「单源模板 + 三 token 渲染为包内绝对路径」，不再有复制快照路径；…本文档记录的是 0.73.0 时点的形态，保留作历史证据。"*

**Residual (P3, not a new finding):** one further `--mode copy` mention survives at **L53**, in the `## no-overclaim 边界` section *below* the box, so the box's word *"上文"* does not literally cover it. It is nonetheless inside the document-scope historical framing the same box establishes (*"本文档记录的是 0.73.0 时点的形态，保留作历史证据"*) and the file is version-scoped (`-0.73.0`), so it is not an asserted current behaviour. Recorded for completeness; the wording *"上文"* → *"本文"* would remove the ambiguity.

### F11 — P3 — "`dsh plugin remove` stays symmetric" unsupported by the code → **已关闭**

`lib/index.js:41-48` (staged blob) — the clause is replaced by text that matches `adapters/dsh/launch.py:36-38`:

> `* open-folder available. `dsh plugin remove` withdraws the bundle row (it`
> `* manages the profile's pnpm bundle layer and never the user preset root, so`
> `* it cannot delete the rendered preset — use the settings page or`
> `* launch.py --uninstall for that); a subsequent boot with the row still`
> `* present re-renders the preset, so deleting it alone is not persistent.`

The word "symmetric" is gone. The replacement states the bundle-layer scope of `dsh plugin remove`, the actual removal paths, and the re-render semantics — the same three facts as `launch.py:31-38` and `rollback-plan-0.80.0.md:37`. Verified as the only change to `lib/index.js` in the fix batch (6 lines, comment block only; no executable line touched — see §6).

---

## 4. Task 3 — retracted-wording sweep: **no unmarked assertion remains**

Sweep of the **staged index** (`git grep --cached`, which is the frozen artifact):

```
git grep --cached -n -E '逐字节等价|宿主平面贡献归零|每个会话|every session of that profile|均不保留'
```

Working-tree sweep (needed because `.governance/` is gitignored) additionally covered `.governance/**`, excluding `node_modules`, `.git`, `__pycache__` and `.governance/incidents/**` (raw session transcripts — machine noise, not governance text).

| Pattern | Occurrences in staged tree | Classification |
|---|---|---|
| `宿主平面贡献归零` | **0** | fully removed from the frozen artifact |
| `every session of that profile` | **0** in README | only in test fixtures + detector regex (below) |
| `每个会话` | `README.md:393` | **quoted history, explicitly marked** — *"（旧文案曾称「该 profile 的每个会话中可用」…已随宿主行 UPDATE 一并退役。）"* |
| | `adapters/dsh/AGENTS.md.template:5` | **not applicable** — different subject: *"dsh 会把本文件自动注入到…每个会话"* (AGENTS.md injection), unrelated to skill availability |
| | `release-checklist-0.80.0.md:108,112` | historical narrative quoting the R0 finding it records as fixed |
| | `tests/test_readme_evidence_levels.py:47` | **negative fixture** — `test_unannotated_claim_detected_warn` feeds this text in and asserts `verdict=WARN` + `claim_id=dsh-session-projection` |
| | `verify_workflow.py:19624` | **detector regex** for the claim registry, not a claim |
| `逐字节等价` | `project/CHANGELOG.md:19`, `README.md:395`, `release-checklist-0.80.0.md:62`, `plugin-contract.md:257` | **explicit negations** (*"**不是**「与未安装时逐字节等价」"*) |
| | `release-checklist-0.80.0.md:108` | historical quote of the R0 finding |
| | `review-FEAT-026-CODE-R0.md:44`, `.governance/decision-log.md:102,107` | **not applicable** — unrelated subjects (quick-path byte-equality; DEC-042/043 `skills/`↔`.claude/skills/` equivalence) |
| | `.governance/session-snapshot.md:79` | superseded in place — correction box at `:81` |
| | `.governance/decision-log.md:135` | DEC-187's original text — supersession note in the same row (§F4) |
| | `test_readme_evidence_levels.py:61,95` | negative fixtures |
| `均不保留` | staged tree: **0** | removed from the frozen artifact |
| | `.governance/decision-log.md:135` | DEC-187 original + same-row DEC-188 note |
| | `.governance/decision-log.md:136` | DEC-188's 事实起点 cell, quoting in order to supersede |
| | `.governance/risk-log.md:44` | *"**交付形态（DEC-188 澄清，替代本行原「…均不保留」文本）**"* |

**Result: every remaining occurrence is a negation, a detector, a negative test fixture, an unrelated subject, or quoted history carrying an adjacent supersession marker. There is no site in the frozen tree or in the live governance records where a retracted proposition is still asserted as current.** The R0 §3.1 failure (3 files) is cleared.

---

## 5. Task 4 — gates run (fast gates only, as instructed)

The full unittest suite was **not** run, `check-release`'s execution gates were **not** run, and no measurement was raced.

| Gate | Result | Detail | Exit |
|---|---|---|---|
| `check-injection-contract` | **PASSED** | `Files checked: 3; anchors: 23` — identical to R0, so F7's new section changed no anchor set | 0 |
| `check-manifest-consistency` | **PASSED** | `Canonical files: 659 ; Actual files: 733` | 0 |
| `check-projection-sync --fail-on-issues` | **PASSED** | `Source version: 0.80.0 ; Mirrored files checked: 15` | 0 |
| `check-version-consistency` | **PASSED** | `Files checked: 13 (… CHANGELOG, plan-tracker, 4 hooks) + bootstrap markers` — all consistent | 0 |
| `check-archive-integrity` (run for F4, not requested) | **FAIL (expected, disclosed)** | see §F4 | 1 |
| `pytest tests/test_contract_matrix.py` (targeted, F7 impact) | **27 passed** | the suite that does snippet-existence checks against `plugin-contract.md` | 0 |
| `pytest tests/test_readme_evidence_levels.py` (targeted, F2 impact) | **8 passed** | the module the fix batch broke and repaired | 0 |

All four requested gates pass. F7's new section breaks nothing I can detect via gates.

---

## 6. NEW findings introduced or exposed by the fix batch

The fix batch is not merely a set of deletions: `git diff ef20d026765e415b82edf3ac6a86ba25b2287fab 88915ed2606154219561c3828f23dbf390b4dbe2` shows it changed **10 files, +722/-31** relative to the tree that was measured (see F12) and added the two R0 reports. Three defects trace to it.

### F12 — P2 — checklist row 6 attributes the full-suite measurement to a tree that is NOT the frozen candidate

**File**: `docs/release/release-checklist-0.80.0.md:75`

> *"**冻结树实测**（`git write-tree` = `ef20d026765e415b82edf3ac6a86ba25b2287fab`，2026-09-12T09:54:43→10:06:49，`python -X utf8 -m unittest discover`）：`Ran 2675 tests in 720.962s` → **FAILED (failures=35, errors=1, skipped=1) = 36**"*

**The hashes differ.** The pinned candidate is `88915ed2606154219561c3828f23dbf390b4dbe2`. Both objects exist in the object database (both are `tree`), confirming they are two distinct index states, not a typo:

```
git write-tree                                       → 88915ed2606154219561c3828f23dbf390b4dbe2
git cat-file -t ef20d026765e415b82edf3ac6a86ba25b2287fab → tree
git ls-tree -r <ef20d026> | count                     → 731 files
git ls-tree -r <88915ed2> | count                     → 733 files
git diff --name-status ef20d026 88915ed2              → 10 files (M README.md, M lib/index.js,
    M project/CHANGELOG.md, M skills/.../plugin-contract.md, M docs/release/{release-checklist,
    feature-flags}-0.80.0.md, M docs/requirements/data-inventory-0.80.0.md,
    M docs/marketplace/dsh-preset-adapter-0.73.0.md, A docs/reviews/review-REL-076-{DESIGN,RELEASE}-R0.md)
```

So the release's **only** full-suite evidence was taken on a tree that is not the artifact under review, and the frozen tree `88915ed2` has **never** been full-suite measured. The row is not deceptive — it self-discloses the drift at its tail (*"**自我披露**：本版修复期我的 README 改述曾引入 1 个真实新失败（`test_readme_evidence_levels.test_real_repo_readme_claims_all_annotated`…），**已修**（补 `〔static: …〕` 标注，该模块 8/8 OK）"*) — but the parenthetical still labels the stale hash *"冻结树实测"*.

**Why P2 and not a blocker.** The product-code delta between the two trees is **comment/doc-only**: `lib/index.js` (6 lines, inside the module header comment — no executable line), `plugin-contract.md` (+20 doc lines inside the skill package), plus README/CHANGELOG/data-inventory/marketplace docs and the two new review reports. I independently covered the two changed files that any test could plausibly assert on: `test_contract_matrix.py` **27 passed** (snippet checks against `plugin-contract.md`) and the manifest/projection/injection/version gates **all PASSED** on the frozen tree. Correct disposition: either re-measure the frozen tree, or state plainly that the measurement predates the fix batch and that `88915ed2` differs from the measured tree by 10 named files.

**Brief-premise failure.** The brief asserted that row 6 records *"`git write-tree` = the pinned hash"*. **It does not** — it records `ef20d026…`. Reported here rather than silently repaired, in the same spirit as the R0 §1.1 disclosures. (This also means the brief's instruction not to race the measurement protects a measurement of a *different* tree, which is worth knowing before the release is authorized.)

### F13 — **P1** — shipped README falsely claims `v0.80.0` is tagged locally, citing a disclosure that does not exist → **BLOCKER**

**File**: `README.md:92` — **in the frozen index** (`git show :README.md`), i.e. inside the pinned artifact.

> *"Note on `github:`: **`v0.79.0` and `v0.80.0` are tagged locally but not yet pushed** (push credentials blocked — disclosure in the release checklist), so GitHub's master still serves 0.78.1; install from a local checkout (`link:`/`file:`) or **wait for the push**."*

**Half of this is true and half is false.**

*True half:* `v0.79.0` **is** tagged locally and **is** absent from the remote.
```
git show-ref --tags | Select-String 'v0.79|v0.80'  → 96a0030… refs/tags/v0.79.0   (only)
git ls-remote --tags github-https                  → refs/tags/v0.78.0, refs/tags/v0.78.1
                                                      (no v0.79.0, exit 0)
```
A `push 凭据阻塞` disclosure genuinely exists — at `docs/release/release-checklist-0.79.0.md:69` (*"W-3 披露：CI ubuntu 权威面未跑〔push 凭据阻塞〕"*).

*False half — `v0.80.0` is not tagged, and cannot be:*
```
git tag -l 'v0.80.0'                                  → 0 matches
git for-each-ref refs/tags | Select-String 'v0\.8'    → refs/tags/v0.79.0, refs/tags/v0.8.0 (older) only
git show :skills/.../core/releases/0.80.0.json        → "lifecycle_state":"candidate", "events":[]
docs/release/release-checklist-0.80.0.md:5            → "candidate（release_authorized=false；
                                                         transition/tag/push 待 M-4 用户授权…）"
docs/release/release-checklist-0.80.0.md:135          → "candidate-only：release_authorized=false——
                                                         transition/tag/push 待用户授权（DEC-143）"
```
The candidate's own release manifest says `candidate` with **zero** lifecycle events; the checklist says tag/push awaits the M-4 user gate that has not been granted. `v0.80.0` cannot have been tagged, because the release is not authorized.

**Introduced by the fix batch.** The R0 text of this same line made **no** `v0.80.0` tag claim — `git diff ef20d026… 88915ed2… -- README.md` shows the old wording was *"Note on `github:` before v0.79.0 is pushed: GitHub's master still serves 0.78.1, so install from a local checkout (`link:`/`file:`) or wait for the release."* The fix batch replaced it with the version that names `v0.80.0`.

**Why this is P1 / release-blocking.** It is the *same defect class* as the two findings that blocked R0: a shipped, user-visible product file asserting something the repository contradicts. It is worse in one respect — R0's F1/F2 concerned a *superseded criterion*, whereas this is a plain false statement of **release state** in the file the user reads to decide at the M-4 gate. A reader is told the 0.80.0 release has been tagged and is merely waiting on push credentials, when in fact the candidate is at M-3 awaiting their authorization and `release_authorized=false`. It also undercuts the release's own no-overclaim discipline (`CHANGELOG.md:80`: *"不声明、不证明 `vX` tag 存在"*) and its P1 project principle (*"分析和推演基于事实，不允许假设和编造"* — here an unbacked *"disclosure in the release checklist"* is attributed to a document that, for 0.80.0, says the opposite). The secondary attribution error — the credentials disclosure is in the **0.79.0** checklist, not 0.80.0's — is the same defect in miniature.

**Minimal fix**: scope the claim to the version it is true of, e.g. *"`v0.79.0` is tagged locally but not yet pushed; `v0.80.0` is a candidate awaiting release authorization"*.

### F14 — P2 — checklist claims the Release half was machine-recorded at round 2; no such record exists

**Files**: `docs/release/release-checklist-0.80.0.md:113` and `:120`; repeated at `.governance/plan-tracker.md:86`.

> `:113` *"**M-3 记录口径（FIX-314 受限下的合规处置）**：`review_record.py` 以 `(task, round)` 为唯一键 ⇒ 同一轮只能存一位审查方。设计半面占 `(REL-076, 0)`，故 **Release 半面按 `--round 2` 记录**（同样经 CLI，exit 0）；round 编号在此**不代表修复轮次**…"*
> `:120` *"…机器记录改用 round=2，见 §Review Evidence"*

**Observed governance state contradicts this.** `review_record.py` writes deterministically to `review-{task}-R{n}.md` **and** appends an evidence-log row (`review_record.py:357-359`). Neither exists for round 2:

```
.governance/review-REL-076*.md                      → review-REL-076-R0.md ONLY
Select-String .governance/evidence-log.md 'REVIEW-REL-076' → L1983 = REVIEW-REL-076-R0 only
   (no REVIEW-REL-076-R2 row)
```

So the Release half of the M-3 double review currently has a **report** (`docs/reviews/review-REL-076-RELEASE-R0.md`, staged ✓) but **no machine record at all**, while the checklist states twice that it was CLI-recorded with `exit 0`. Since M7.5 forbids hand-written REVIEW evidence rows, the recorded form the checklist describes is the *only* compliant form — and it is absent.

**Cause: 未知.** I cannot exclude (a) the CLI call was not in fact made, (b) it was made while `.governance` was mid-archive-migration and the record was subsequently lost, or (c) `.governance` was restored from a backup afterwards. The pre-migration backup at `%TEMP%\governance-backup-20260912-rel076` **cannot adjudicate this**: it contains **zero** `review-REL-076*` files — not even R0 — so it predates both records. What *is* established is the current fact: the claimed record does not exist.

**Disposition**: P2 — re-run `review-record --task REL-076 --round 2 …` to produce the record the checklist already claims, or correct `:113`/`:120`. Not counted as a blocker (the underlying Release review report exists and is staged; the gap is in the machine-record layer, and it is repairable without touching the frozen artifact). Flagged for the Coordinator because it is the same class of "document asserts an artifact that isn't there" as F13, and because the Release half should carry a machine record before M-4.

### P3 observation (not a defect) — the reference implementation is not a zero-host-plane plugin

Now that `D:\AI\agent\deepseek\harness\writing-workflow` is available (closing R0 **U-2**, §7), I verified the structures DEC-188 quotes:

| Quotation | Verified |
|---|---|
| `writing-workflow/cordis.patch.yml` = one insert row | **TRUE** — 13 lines, exactly one top-level `- insert:` → `id: novel-writing` / `name: dsh-novel-writing` |
| `lib/index.js` L1425 calls L157-190 `ensurePreset` | **TRUE** — `L1425: service.ensurePreset()`; `ensurePreset()` defined L157-184 with the same shape (version marker, `existsSync(userDir) && current === version` idempotence guard L171, staging dir L174-177, `rmSync` + `renameSync` L178-179, warn-only `catch` L181-183) |

One nuance worth recording so it is not mis-cited later: the reference row is a **dual-face host row** — its own header comment (L4-9) declares that it provides a novel-writing service, copies its preset into `$DSH_HOME/.agent-presets/`, and exposes a browser view via `dsh.client`; the module also does `ctx.settings.register(NS, Config)` (L1423) and registers HTTP routes (L1429). `dsh-novel-writing` therefore **does** contribute to the host plane (settings namespace, web routes, client entry). DEC-188 and `CHANGELOG.md:19` cite it only for the *delivery vehicle* (one insert row as the official `plugin add` carrier), which is exactly the scope in which the citation is accurate. DEC-187's I-1/I-2 are this project's **stricter self-imposed** constraint, not a property inherited from the reference; no document currently claims otherwise, so this is an observation, not a finding.

---

## 7. `未知` items

- **U-1 — Real-machine acceptance surface. UNCHANGED, still the single most load-bearing unknown.** Whether the settings page shows the 「自定义」 tag with delete + open-folder, whether a non-governance preset session is genuinely free of governance skills, and whether a governance session's catalog is complete. Only the user's real dsh can answer; the candidate declares these unverified (`release-checklist-0.80.0.md:91-99`, `session-snapshot.md:157`). I neither confirm nor deny. Note the F2 fix does **not** depend on the outcome: the README now says "pending" in all three sites, which is correct under either result.
- **U-2 — `dsh-novel-writing` reference implementation. NOW CLOSED** (was 未知 at R0). Path supplied as `D:\AI\agent\deepseek\harness\writing-workflow`; both quoted structures verified as accurate (see §6). The R0 brief's omission of the path was indeed a brief defect, not a fact defect.
- **U-3 — Cross-root path stability. UNCHANGED.** `launch.py` resolves symlinks (`Path.resolve()`) while `lib/index.js` does not (`import.meta.url`). Under `dsh plugin … add link:<repo>` the two delivery paths receive different roots. Whether pnpm materialises that link as a junction whose unresolved path is stable across `dsh plugin update` cycles — and what happens to an already-rendered user-root preset whose absolute `customSkillDirs` point into a `.pnpm` directory a later install moves — remains unverifiable from this repository. Version-marker idempotence means a version bump self-heals; a re-resolution at the same version would not. Folded into FIX-313's neighbourhood (`release-checklist-0.80.0.md:111`). Not asserted as a defect.
- **U-4 — `npm publish` / registry availability. UNCHANGED.** `package.json` keeps `"private": true`; every documented install form is `link:` / `file:` / `github:`. Whether a non-checkout end user could install from a registry is unknown and **not claimed** by the candidate.
- **U-5 — No Code review of the post-DEC-187 implementation. UNCHANGED, and now explicitly registered.** `release-checklist-0.80.0.md:121` records it as a process gap: *"DEC-187 之后**没有针对 `lib/index.js` 与改造后 `launch.py` 的 Code 审查**（本版 M-3 为 Release + Design 双审，非 Code 半面）。登记为待补任务，不在本版声明已覆盖。"* I am not the code reviewer; the gap is confirmed to still exist and is now honestly disclosed rather than silently carried.
- **U-6 (new) — Full-suite result for the frozen tree `88915ed2`.** Not measured (§F12), and I was instructed not to measure it. Whether the 10-file fix-batch delta introduces any failure the two targeted modules and four gates did not catch is **unknown**. My independent coverage: `test_contract_matrix.py` 27 passed, `test_readme_evidence_levels.py` 8 passed, `check-manifest-consistency` / `check-injection-contract` / `check-projection-sync` / `check-version-consistency` all PASSED on the frozen tree.
- **U-7 (new) — Cause of the missing Release-half machine record (§F14).** See F14; not determinable from the repository.

---

## 8. Items re-checked and found sound (no finding)

| # | Checked | Evidence |
|---|---|---|
| N-1 | Artifact freeze | `git write-tree` = `88915ed2…`, 33 staged, 0 untracked — re-verified after all reads and after my only write |
| N-2 | F1/F2 present in the **index**, not merely the working tree | `git show :project/CHANGELOG.md`, `git show :README.md` — the R0 gap is closed |
| N-3 | No unmarked retracted wording anywhere | §4 sweep — every occurrence is negation / detector / negative fixture / unrelated / marked history |
| N-4 | F7's new section breaks no gate | 4 requested gates PASSED + `test_contract_matrix.py` 27 passed; anchors unchanged at 23 |
| N-5 | F4's new consequence is correctly diagnosed and registered | `check-archive-integrity` FAIL reproduced verbatim; FIX-312 registered P2 with the engine-side root cause |
| N-6 | Archive cleanup is internally consistent | `条目数: 4` matches exactly 4 DEC rows (174/176/177/182) in the file and in `archive/index.md`; DEC-187 fully removed from both |
| N-7 | Governance-plane findings cannot be pinned | `.gitignore:10` = `.governance/` — F3/F4 and the FIX-312/313/314 rows are outside the frozen artifact by construction (§1) |
| N-8 | F8/F9 deferral is legitimate, not a silent drop | FIX-313 registered P3 at `plan-tracker.md:85` with both sub-defects, the roster-invisibility evidence, and an explicit *"不阻塞 0.80.0"* |
| N-9 | Brief-premise failure disclosed rather than absorbed | the brief's *"row 6 records git write-tree = the pinned hash"* is contradicted by `:75` (see F12) |

---

## 9. Conclusion

**The fix batch did its job.** All eleven R0 findings are closed: F1 and F2 — the two that blocked R0 — are now fixed **in the frozen index**, not merely in the working tree, and they are fixed in the right direction (F1 adopts the DEC-188 ② criterion and drops "宿主平面贡献归零" in favour of "宿主既有行零触碰"; F2 scopes skill availability to the governance preset's own sessions, names `standard`, and marks the real-machine confirmation pending). F3's correction box now sits in the exact section R0 identified as uncovered. F4's DEC-187 row is back in the hot decision-log between DEC-186 and DEC-188 with an explicit DEC-188 clarification, and the archive is consistent at 4 entries. F5/F6/F10/F11 are corrected in substance, not cosmetically. F7's forward deliverable now exists as shipped contract prose and breaks no gate. F8/F9 are deferred with an accurate, checkable P3 registration, which is the correct disposition. The §4 sweep finds **no** remaining site — in the frozen tree or in the live governance records — where a retracted proposition is still asserted as current.

**But the fix batch also introduced a new blocking defect of the same class it was repairing.** F13: the frozen `README.md:92` tells the user that `v0.80.0` *"are tagged locally but not yet pushed"* and invites them to *"wait for the push"*, citing *"disclosure in the release checklist"*. The tag does not exist, the candidate's own manifest says `lifecycle_state: candidate` with zero events, the checklist says `release_authorized=false` with tag/push awaiting the M-4 gate, and the cited disclosure lives in the **0.79.0** checklist. The R0 wording of this same line made no such claim — the fix batch added it. Since R0 blocked on shipped-document-versus-repository contradictions, consistency requires blocking on this one, all the more so because it misstates **release state** in the file the user reads when deciding whether to authorize.

Two further traceability defects come out of the same batch, both P2 and both repairable without touching the frozen artifact: the checklist's full-suite row attributes the measurement to tree `ef20d026…`, not the frozen `88915ed2…` (so the frozen tree is unmeasured — repairable by re-measuring or by correcting the attribution), and the checklist claims a Release-half machine record at round 2 that does not exist anywhere in `.governance`.

The architecture remains sound and I re-confirmed the parts I could reach: the four requested gates pass on the frozen tree, the contract-matrix and README-evidence suites pass, and the `dsh-novel-writing` reference structure that the whole "official command stays the delivery vehicle" argument rests on is now verified rather than assumed (R0's U-2 closed).

**Disposition**: the candidate may not proceed to M-4 authorization until F13 is corrected in the index. F12 and F14 should be corrected in the same pass; neither is subject to the freeze, and F14 requires only a CLI re-run.

I did not modify any product file. My only write is this report.

`unresolved_blockers=1`

> **Definition used** (unchanged from R0): `unresolved_blockers` = the number of findings that must be closed before the release candidate may proceed to M-4 user authorization = **F13** (P1 — a false release-state claim in the shipped, frozen `README.md`). The R0 blockers F1 and F2 are **closed**, which is why the count fell 2 → 1 rather than to 0. The P2 findings **F12** (stale measured-tree hash) and **F14** (missing Release-half machine record) are recorded as required repairs but are not counted, consistent with R0's treatment of its P2 findings (F3–F11): neither asserts a false proposition to the user, and neither requires a change to product behaviour. Findings F3–F11 are all closed and are not counted. Items in §7 are declared `未知` and are **not** counted as blockers, because none is a technical impossibility — each is a verification I am not positioned to perform from this repository (the largest remaining being U-1, the real-machine acceptance that only the user can run, and U-6, the unmeasured frozen tree).
