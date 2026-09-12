# REVIEW-REL-076-DESIGN-R0 — Design Review of the 0.80.0 Release Candidate

- **Task**: REL-076 (release 0.80.0, release candidate)
- **Round**: R0
- **Reviewer**: Design Reviewer (independent, delegated; no product file modified)
- **Verdict**: **NEEDS_CHANGE** — `unresolved_blockers=2` (definition in §7)
- **Date of review**: as recorded by `review-record` (see machine record)

---

## 1. Scope reviewed

| Item | Value | Evidence |
|---|---|---|
| Version authority | `skills/software-project-governance/SKILL.md` frontmatter `version: 0.80.0` | read, line 3 |
| Window (committed) | `git log v0.79.0..HEAD` = **21 commits** | `git rev-list --count v0.79.0..HEAD` → 21 |
| Window tip | `5a259e2` (FIX-310, the dsh adapter rework) | `git log --oneline -1` |
| Window base | `v0.79.0` peels to `17eda48` — the brief's `17eda48` is a **commit**, `96a0030` is the **annotated tag object**; `git rev-list --count 17eda48..v0.79.0` = 0 | command output (§6, no-finding N-8) |
| Candidate working tree | **26 files, all staged** | `git status --short` (26 lines) |
| dsh rework artifacts | `cordis.patch.yml` (43 lines), `lib/index.js` (227 lines), `agent-presets/governance/{agent.cordis.yml.template,preset.yml}`, `adapters/dsh/launch.py` (924 lines), `package.json` | read in full / line counts |
| Deletions confirmed absent from disk | `presets/`, `adapters/dsh/preset.yml`, `adapters/dsh/agent.cordis.yml.template`, `presets/governance/agent.cordis.yml` | `Test-Path` → all `False` |
| Governing decision | **DEC-187** — *not in `.governance/decision-log.md`*; it lives in `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:39-44` | grep (§2, F4) |
| Clarifying decision | **DEC-188** — `.governance/decision-log.md:135` | read |
| Risk | **RISK-050** — `.governance/risk-log.md:44` | read |
| Release docs | `docs/release/{release-checklist,feature-flags,rollback-plan}-0.80.0.md` | read in full |

### 1.1 Brief premises that did NOT survive verification

The brief is not evidence. Two of its assertions are contradicted by files:

1. **"`.governance/decision-log.md` DEC-187"** — DEC-187 has **no row in the hot decision-log**. Its only record is the archived row at `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:44`, filed under `- 归档版本: v0.77.0（关联 task 已归档）` despite being dated 2026-09-12. Verified by exhaustive repo grep for `DEC-187` (see §2). The invariants themselves are real and are restated in `.governance/session-snapshot.md:73-86` and in `project/CHANGELOG.md:19` — but the "decision-log.md DEC-187" citation is wrong, and a review that had trusted it would have searched the wrong file.
2. **"DEC-188 rewrote both" (DEC-187's action column *and* RISK-050's mitigation cell)** — **only RISK-050 was rewritten.** `risk-log.md:44` carries the correction inline with an explicit marker (`**交付形态（DEC-188 澄清，替代本行原「…均不保留」文本）**` and `（**非**「与未安装时逐字节等价」——DEC-188 ②）`). The DEC-187 archived row was **not** touched: it still carries both superseded claims unmarked. See **F4**. DEC-188's own 治理记录同步 list (§"治理记录同步") enumerates decision-log(self) + risk-log + plan-tracker + session-snapshot — it does **not** claim to have rewritten DEC-187, so the brief over-claimed on DEC-188's behalf.

Both premises are reported here rather than silently repaired, per the standing warning about fabricated coordinator premises (which DEC-187 itself documents: *"把这条未经验证的前提写进了给审查方的简报，于是三轮『独立审查』都在同一假前提上盖章"*).

---

## 2. Checklist item 1 — Invariant compliance (DEC-187 I-1/I-2/I-3 as clarified by DEC-188)

**Verdict: PASS (verified mechanically, independently of the release docs).**

`cordis.patch.yml` read in full (43 lines; 29 are the explanatory header, the YAML body is lines 41-43).

```
python -c "import io,yaml; t=io.open('cordis.patch.yml',encoding='utf-8').read(); d=yaml.safe_load(t); print(type(d).__name__, len(d)); [print(sorted(r.keys()), r) for r in d]"
```
→
```
safe_load OK (no !!js tag present)
list 1
['insert'] [{'id': 'governance', 'name': '@peterwangze/software-project-governance-plugin'}]
```

| Required property | Result | Evidence |
|---|---|---|
| exactly one `- insert:` row naming only this package | **PASS** | structural parse above: 1 top-level row, single key `insert`, 1 element, only `id` + `name` |
| zero `- id: <host row>` UPDATE rows | **PASS** | only top-level key is `insert`; the sole nested `- id: governance` is the inserted row's own id |
| zero `!!js` | **PASS** | `yaml.safe_load` succeeds — an unresolved `!!js` tag would raise `ConstructorError`. The literal `!!js` occurrence in the file (line 18) is inside the comment block that states the prohibition |
| zero `system`-trust preset root | **PASS** | no `trust` key anywhere in the parsed document; the preset is delivered into `$DSH_HOME/.agent-presets/` (user root) by the row module |
| no `ctx.*` publication beyond `ctx.logger` | **PASS** | `Select-String 'ctx\.' lib/index.js` → 5 hits, all `ctx.logger` (L170 comment, L185, L197, L213, L215). No `ctx.skills` / `ctx.agentPresets` / `registerProvider` / service publication |
| no host service read | **PASS** | the module reads only `process.env.DSH_HOME` + `os.homedir()` (`resolveDshHome()`, L97-107) |
| no runtime dependency that can throw at load | **PASS** | imports are `node:fs`, `node:os`, `node:path`, `node:url` only (L54-57); `python -c` on `package.json` → `dependencies/peerDependencies/devDependencies/optionalDependencies` **all absent**; `"type": "module"` (L19) makes the ESM syntax loadable; `packageRoot()` derives from `import.meta.url`, never cwd |
| import of the row module actually succeeds | **PASS** | `node --input-type=module -e "await import('file:///…/lib/index.js')"` executed successfully in three separate probes |

Independent confirmation of the surrounding claim: `python skills/software-project-governance/infra/verify_workflow.py check-dsh-preset-compat` → **PASSED**, `Compositions: 1; enabled rows: 23; schema-checked rows: 18`, `writes: 0`, exit 0. This is Check 28v (FIX-309) run against the *delivered* template, resolved from the real `DSH_HOME/profiles` oracle set — it corroborates that the shipped composition is mountable.

---

## 3. Checklist item 2 — DEC-188 consistency sweep

### 3.1 (a) Remaining superseded wording — **FAIL: 3 files**

Sweep commands (repo-wide, excluding `node_modules/.git`, and separately excluding archive/backup/pycache for the "live" reading):

```
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch "node_modules|\\\.git\\" } |
  Select-String -Pattern '均不保留','宿主平面贡献归零','逐字节等价','贡献归零'
```

| Pattern | File:line | Status |
|---|---|---|
| `均不保留` | `.governance/decision-log.md:135` | **acceptable** — DEC-188's 事实起点 cell quotes the superseded text in order to supersede it |
| `均不保留` | `.governance/risk-log.md:44` | **acceptable** — explicitly marked `替代本行原「…」文本` |
| `均不保留` | `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:44` | **FINDING F4** |
| `宿主平面贡献归零` | `.governance/decision-log.md:135` | acceptable (quote) |
| `宿主平面贡献归零` | `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:44` | **FINDING F4** |
| `宿主平面贡献归零` | `project/CHANGELOG.md:19` | **FINDING F1** |
| `逐字节等价` | `.governance/session-snapshot.md:79` | **FINDING F3** |
| `逐字节等价` | `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:44` | **FINDING F4** |
| `逐字节等价` | `project/CHANGELOG.md:19` | **FINDING F1** |
| `逐字节等价` | `.governance/decision-log.md:135` / `risk-log.md:44` / `release-checklist-0.80.0.md:62` | acceptable — all three are explicit **negations** of the stronger criterion |
| `逐字节等价` | `.governance/decision-log.md:102,107` | not applicable — DEC-042/DEC-043, about `skills/` ↔ `.claude/skills/` equivalence, unrelated |

See F1/F3/F4 below for the three real findings.

### 3.2 (b) Release docs state the *delivered* form — **PASS**

- `docs/release/release-checklist-0.80.0.md:47-62` — §"FIX-310 交付的架构形态" is a per-face table with file evidence, and L49 says explicitly **"不声称「宿主平面贡献为零」"**; L53-59 correctly state the delivered form for host rows / `!!js` / host-plane registries / trust / side effect / single-source skills / dual-path parity; L62 states the corrected machine-check criterion and says **"本候选按上述机械形式声明，不按更强口径声明"**.
- `docs/release/feature-flags-0.80.0.md:22-26` — L22 `恰一行自有 - insert:` 零 UPDATE/零 `!!js`/零宿主平面注册; L23 warn-only + no runtime dependency + staging+rename + idempotence; L24 single-source; L26 the corrected criterion. All consistent with the delivered code.
- `docs/release/rollback-plan-0.80.0.md:36-37,50,56` — L36 `git revert 5a259e2` re-introduces the RISK-050 root cause (honest); L37 states `dsh plugin remove` withdraws the bundle row and the user-root copy is the user's own directory; L56 lists the user-root preset as reversible with **"重启自动重建"**.

One wording note in §3.2 (not a superseded-claim finding, folded into F6): `release-checklist-0.80.0.md:115` and `:21` describe RISK-050's root-cause elimination in terms broader than the delivered scope, and broader than `feature-flags-0.80.0.md:32`.

### 3.3 (c) `session-snapshot.md` marks the earlier design superseded and the delivered form authoritative — **PASS with one residual (F3)**

- L63-71: the entire mid-flight design (R0′ / R1 / R2 / R3 / A1–A12 / host-plugin model) is struck with `⛔ 本节以下全部内容…已作废，仅作历史记录保留`, including the explicit anti-mis-citation carve-out at L71 (*"引用 FIX-310 的加载模型/交付形态时 MUST 以「✅ 已交付形态」节为准"*).
- L121-136: `⚠️ 已作废的中间设计` table, with the two retracted acceptance criteria struck and annotated (L136) **[正确：这也是 DEC-188 §③ 要求更正的「验收项 5 删除预设后不被重建」，已改为「会被重建」]**.
- L138-147: `✅ 已交付形态（… commit 5a259e2 + DEC-188 澄清——以此为准）` table with file evidence per row, incl. the deletion-semantics row (L147) citing `lib/index.js` L188-193.
- L149-157: current acceptance standards 1-6, with L157 disclosing that criteria 2/3/4/5 are **not** verified in this candidate.
- **Residual**: L79 (inside the *not*-superseded invariants section) still states the retracted criterion flatly → **F3**.

---

## 4. Checklist item 3 — Renderer parity

**Verdict: PASS — byte-identical, and covered by an existing test.**

Compared `lib/index.js` `renderComposition()` (L145-159) and `adapters/dsh/launch.py` `render_composition()` (L134-155) line by line, then empirically.

**Empirical result (same template, same package root):**
```
python … launch.render_composition()      → 13566 chars, sha256 00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723
node   … renderComposition(t, pkgRoot)    → 13566 chars, sha256 00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723
node leftovers                            → []
```
Token spelling, both sides (verified in-process):
```
__GOVERNANCE_SKILLS_ROOT__ => D:/AI/agent/claude/coding/project_management_workflow/skills
__GOVERNANCE_SHIMS_ROOT__  => D:/AI/agent/claude/coding/project_management_workflow/adapters/dsh/skill-shims
__GOVERNANCE_REPO_ROOT__   => D:/AI/agent/claude/coding/project_management_workflow      ← no trailing separator
```

Point-by-point:
| Contract point | Python | JS | Verdict |
|---|---|---|---|
| same 3 tokens, same names | `TOKEN_PATHS` keys L100-102 | `TOKEN_PATHS` L79-83 | identical |
| same token→relative mapping | `ROOT/skills`, `ADAPTER_DIR/skill-shims`, `ROOT` | `'skills'`, `join('adapters','dsh','skill-shims')`, `''` | identical |
| repo-root token has no trailing sep | `str(Path.resolve())` | `pkgRoot.replace(/[\\/]+$/,'')` (L115) | identical |
| forward-slash spelling | `.replace("\\","/")` | `posixPath()` (L119-121) | identical |
| LF normalization | `read_text` universal newlines | `replace(/\r\n/g,'\n')` (L150) | identical **for LF/CRLF**; diverges on lone CR → **F8 (P3, latent)** |
| output written with no added newline | `write_text(..., newline="\n")` L201-202 | `writeFileSync(..., text, 'utf8')` L206 | identical |
| unresolved token = failure | return `""` (L153-154) | `{text,leftovers}` + caller warns & skips (L157,196-200) | equivalent |
| marker contents | `version + "\n"`, `ROOT.resolve() + "\n"` | `${version}\n`, `${posixPath(pkgRoot)}\n` | identical |
| `preset.yml` copy | `shutil.copyfile` L203 | `cpSync` L207 | content-identical |

**Test coverage — YES, exists**: `skills/software-project-governance/infra/tests/test_dsh_adapter.py` L1105-1160, section comment *"FIX-310: single-source payload + two-renderer parity"*, which shells out to `node --input-type=module` importing `lib/index.js` `renderComposition` and asserts equality against `launch.render_composition`. It is **node-gated**: `self.skipTest("node unavailable (JS renderer cannot be exercised)")` (L1133-1135) — so on a node-less machine the parity contract silently becomes untested. Two further node-gated tests (L1164, L1217) exercise the host row itself.

Independent run of that suite: **46 passed, exit 0**.

Note on the "same place" claim (`cordis.patch.yml:38-40`): the two renderers are given **different** package roots in real use — `launch.py` computes `ROOT = Path(__file__).resolve().parents[2]` (**symlinks resolved**) while `lib/index.js` computes `packageRoot()` from `import.meta.url` (**symlinks not resolved**; relevant because `dsh plugin … link:` installs a junction/symlink). Parity therefore holds *given the same root*, which is the contract both files actually state; the two delivery paths can legitimately write different absolute paths into the same destination when invoked from different roots (repo checkout vs `node_modules` link). This is disclosed nowhere but is not a contradiction of any written claim — recorded as **未知 U-3** rather than a finding.

---

## 5. Checklist item 4 — Failure policy (warn-only, no half-written preset)

**Verdict: PASS for both stated contracts; one P3 remark (F9).**

**(a) Cannot throw out of `apply()` — verified empirically, not just by reading.**
`apply(ctx)` is a one-liner calling `ensurePreset(ctx)` (L225-227). The whole body of `ensurePreset` is inside `try { … } catch { ctx.logger?.warn(...) }` (L180-216). Two statements sit **outside** the try — `packageVersion()` (L177) and `resolveDshHome()`/`join()` (L178) — but `packageVersion()` has its own `try/catch` returning `'0'` (L124-131) and `resolveDshHome()` only touches env strings.

Probe with a hostile `DSH_HOME` (nonexistent drive → `mkdirSync` must fail), and **with no logger at all** to test the optional-chaining path:
```
DSH_HOME='Z:\definitely-not-a-real-drive\dsh'
node … ensurePreset({})            → no-throw OK, outcome={"synced":false,"dir":"Z:\\definitely-not-a-real-drive\\dsh\\.agent-presets\\governance","version":"0.80.0"}
node … ensurePreset({logger})      → no-throw OK, synced=false
                                     logs=["WARN:software-project-governance: preset sync failed: Error: ENOENT: no such file or directory, mkdir 'Z:\\…\\.agent-presets'"]
```
No exception escaped in either case. The warn-only contract holds.

**(b) Cannot leave a half-written preset — holds.**
Every write goes to a fresh `staging` dir (`${userDir}.staging-${Date.now()}-${rand}`, L203-209); the destination is only touched at L210-211. An aborted render therefore cannot produce a half-populated `governance/` directory. `launch.py` implements the same shape (L261-272).

**(c) Remark → F9 (P3).** The replace step is `rmSync(userDir)` **then** `renameSync(staging, userDir)` (L210-211; Python L270-272). That is a *replace-with-a-window*, not an atomic swap — so release-checklist L57 and feature-flags L23 calling it "staging+rename **原子**" is stronger than the implementation. The window is self-healing (a missing marker ⇒ rebuild next boot), and the JS catch block (L214-216) does not delete the staging dir, unlike Python (L266) — so a failure at the rm/rename step permanently leaks `<userDir>.staging-*/`. I verified this leak is **not** roster-visible: installed `@deepseek-ai/dsh-agent-presets/lib/index.js:403` filters child names with `PRESET_ID = /^[a-z0-9][a-z0-9-]*$/` (L~390), and a name containing `.` fails it — so the orphan cannot appear as an extra preset. Latent housekeeping asymmetry only.

---

## 6. Checklist item 5 — Single-source discipline

**Verdict: PASS.**

| Claim | Result | Evidence |
|---|---|---|
| preset payload is exactly 2 files, no copied `skills/` tree | **PASS** | `Get-ChildItem -Recurse agent-presets` → `agent-presets\governance\agent.cordis.yml.template`, `agent-presets\governance\preset.yml` (2 files). No third file, no `skills/`, no `commands/`, no `agents/` under it |
| no duplicate 231-file skills copy introduced anywhere in the candidate | **PASS** | every `SKILL.md` in the repo enumerated: 27 under `skills/` + 27 under `project/e2e-test-project/skills/` (the pre-existing projected e2e mirror, byte-size-identical) — **no third tree**. The only other dir named `software-project-governance` is the pre-existing `project/workflows/software-project-governance`. The 231-file copy described in the FIX-310 commit message ("已全部删除") is traced in the commit message as an incident; nothing remains on disk or in the index |
| `customSkillDirs` resolves to absolute in-package paths rendered from tokens | **PASS** | template L134-136 declares `'__GOVERNANCE_SKILLS_ROOT__'` / `'__GOVERNANCE_SHIMS_ROOT__'`; both renderers substitute package-absolute paths (verified hashes, §4); `launch.py` `_resolve_skill_entry` (L468-496) actively rejects a literal relative entry as the FIX-290 regression class |
| `<plugin_root>` in shipped prose still resolves to the package root | **PASS** | template L51 `治理插件仓库根目录：__GOVERNANCE_REPO_ROOT__（下称 <plugin_root>）` renders to `…/project_management_workflow` (= package root); the persona's `<plugin_root>/skills/…`, `<plugin_root>/agents/<role>.md`, `<plugin_root>/adapters/dsh/…` all exist relative to it. `package.json.files` ships `lib/`, `agent-presets/`, `skills/`, `commands/`, `agents/`, `adapters/dsh/`, `cordis.patch.yml` (L28-39) — all referenced roots are shipped |
| no core prose had to change | **PASS (scoped)** | `check-injection-contract` **PASSED — 3 files; anchors: 23** (independently reproduced; the release claims the same numbers, down from 28 because the retired `presets/` copy and the `dsh.skills` anchor left the set). `git show 5a259e2 -- skills/software-project-governance/SKILL.md` shows **only** the dsh adapter-table row (L312) and the dsh 平台说明 加载模型 bullet (L317) changed — i.e. the prose that *describes the dsh delivery model*, which necessarily changes; the guarded persona/contract prose is untouched. The commit's own scoping ("核心 persona / 命令 shim / AGENTS.md 文案一字未改") is accurate |

`INJECTION_CONTRACT_ANCHORS` was correctly re-pointed (§`verify_workflow.py:6614-6634`): the single key is now `agent-presets/governance/agent.cordis.yml.template`, with a FIX-310/DEC-187 comment explaining that the former second spelling `presets/governance/agent.cordis.yml` is gone with the copy model.

---

## 7. Checklist item 6 — Consistency of the retirement

**Verdict: PASS in product code; one documentation fan-out gap (F5) + one stale flag doc (F10).**

Commands: `grep -rn "dsh.skills"` and `grep -rn "presets/governance"` (excluding `node_modules`/`.git`), then symbol-level checks for the guard fan-out.

**`dsh.skills` — fully retired from code.**
- `package.json` has no `dsh.skills` key (only `dsh.bundle.patch`, L41-45). ✓
- `verify_workflow.py`: `DSH_SKILLS_DISK_PATTERNS`, `check_dsh_skills_manifest`, `_REJECT_SECURITY_DETAIL` → **0 occurrences**. ✓
- the CLI key `check-dsh-skills-manifest` is gone; `registry.py:428-430` documents the removal (*"Segment 40 (verify_workflow.check_dsh_skills_manifest) was removed with its subject"*). ✓
- frozen faces updated and documented: `test_registry.py:69-74` (83→82 CLI keys, 71→70 segments), `test_contract_matrix.py:49-53`, `test_archguard_ratchet.py:50-54` (print census 1311→1298). All three carry a comment naming the deliberate change and `generator.py --regen`. ✓
- `infra/TOOLS.md` updated in the same commit. ✓
- surviving `dsh.skills` mentions are historical only: archived evidence/task rows, prior dated review reports, `project/CHANGELOG.md` historical entries (L120/169/195/227) — and `feature-flags-0.80.0.md:25` which marks the field **`retired`** as the current state. ✓

**`presets/` — fully retired.**
- directory gone; `manifest.json` has **0** `"presets` entries and instead registers `lib/`, `lib/index.js`, `agent-presets/`, `agent-presets/governance/agent.cordis.yml.template`, `agent-presets/governance/preset.yml` (L239-255, L822). ✓
- `PLUGIN_SCOPE_DIRS` contains the new dirs in **both** copies that the code requires be kept in sync: `cleanup.py:46-57` and `verify_workflow.py:273-290` (each with a FIX-310 comment). ✓
- `cleanup.py` `manifest_cleanup_scope_dirs` derives from the manifest, so cleanup scope follows automatically (L68-77). ✓
- contract-matrix artifacts (`golden_samples.txt`, `snapshots.json`) regenerated in-commit. ✓
- surviving `presets/governance` mentions are historical/dated (prior reviews, archived rows, `docs/release/feature-flags-0.{77,78}.0.md`, `docs/requirements/audit-146-…rca.md`) plus the two *current* docs that intentionally reference the retired path while explaining its retirement (`cordis.patch.yml:27-28`, `verify_workflow.py:6616`). ✓

**Independent test evidence (all green, run by me with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`):**
```
test_dsh_adapter.py                                                       46 passed            exit 0
test_contract_matrix / test_registry / test_quickscan_registry /
test_archguard_ratchet / test_dsh_compat / test_review_machine_provenance  295 passed (+2 subtests) exit 0
```

**Gaps:** F5 (`data-inventory-0.80.0.md:175-176` still inventories the deleted symbols as live) and F10 (`docs/marketplace/dsh-preset-adapter-0.73.0.md:31` documents `--mode copy`, a flag this commit deleted).

---

## 8. Checklist item 7 — Deletion-then-restart semantics

**Verdict: PASS. The code does rebuild, and every document that mentions it discloses it.**

**Code.** `lib/index.js:188-193`:
```js
const markerPath = join(userDir, PRESET_MARKER)
let current = ''
try { current = readFileSync(markerPath, 'utf8').trim() } catch { /* no marker = first install */ }
if (existsSync(userDir) && current === version) return outcome
```
A settings-page delete removes `userDir` ⇒ `existsSync(userDir)` is false ⇒ the guard falls through ⇒ full re-render on the next dsh boot. Same for a version bump. `launch.py --install` has no such guard and always rewrites. Confirmed behaviourally: my hostile-home probe returned `synced:false` only because `mkdir` failed — i.e. it *attempted* the sync, which is what the rebuild path requires.

**Disclosure sweep.** Searched for claims that deletion persists (`delete is refused`, `不被重建`, `deletion persists`, `persist after delete`). **Zero documents claim persistence.** Every mention discloses the rebuild:

| File:line | Disclosure |
|---|---|
| `README.md:395` | *"删除后下次启动会重新渲染（除非同时 `dsh plugin remove` 撤回 bundle 行）"* |
| `docs/release/rollback-plan-0.80.0.md:56` | reversibility row: *"设置页删除 / 手工删目录 / **重启自动重建**"* |
| `docs/release/rollback-plan-0.80.0.md:37` | `dsh plugin remove` withdraws the row; the user-root copy is deleted by the user |
| `.governance/session-snapshot.md:103` | *"用户经设置页删除该预设后，**下次启动会被重新同步**"* |
| `.governance/session-snapshot.md:136` | the old criterion 5 (*"删除预设后不被重建"*) struck and annotated *"与实际语义相反…用户未要求删除后持久存续"* |
| `.governance/session-snapshot.md:147` | delivered-form table row `删除后语义 = 重建`, evidence `lib/index.js L188-193` |
| `.governance/session-snapshot.md:154` | acceptance criterion 5 = *"删除后**会被重建**（如实记录，非缺陷）"* |
| `.governance/decision-log.md:135` (DEC-188 ③) | the ruling itself, quoting the user's requirement scope |
| `adapters/dsh/launch.py:31-38` | `--uninstall` is documented as the official *preset-side* removal path, and states plainly that `dsh plugin remove` *"cannot remove this preset"* |

One wording tension, **not** a persistence claim: `lib/index.js:44` says *"`dsh plugin remove` stays symmetric"* while `launch.py:36-38` says `dsh plugin remove` *"cannot remove this preset"*. Read together, install is automatic and removal of the user-root copy is manual — the asymmetry is real and is disclosed in `rollback-plan-0.80.0.md:37`, so I record this as a P3 wording note (**F11**) rather than a defect: the word "symmetric" in the module header is not supported by the code it describes.

---

## 9. Checklist item 8 — RISK-050 residual

**Verdict: the *host-plane* root cause is genuinely removed; the *preset-plane* root cause is NOT, and the release docs' "结构性根因消除" language does not disclose the residual. → F6 (P2).**

RISK-050's own registration (`risk-log.md:44`) names two legs:
1. *"安装层以 UPDATE 打 dsh 内部行（`agent-presets`/`skill-filesystem`）并用 `!!js` 自定位"* → **structurally removed**. After FIX-310 the patch layer cannot reach any pre-existing row: the only top-level key is `insert` (§2). Unlike the old form, no host row's `config` or `disabled` is rewritten, so a dsh/deployment row rename or a `disabled` flip can no longer be silently overridden by this plugin. Blast radius also genuinely shrinks: an invalid row in the *user-root preset* can only affect sessions that mount the governance preset, not the whole profile (contrast FIX-308's *"单行坏行否决整棵预设挂载"* which the risk cell itself calls 致命).
2. *"预设行的 config 键随 dsh 升级失效"* / *"dsh 任一版本调整这些内部行的 id/name/schema/默认值，或调整预设行插件的 Config 契约"* → **NOT removed**. The delivered `agent-presets/governance/agent.cordis.yml.template` still declares **23 enabled rows** naming `@deepseek-ai/dsh-*` packages with their Config keys — `dsh-persona.config.prefix` (L48, the exact FIX-308 defect surface), `dsh-skill-filesystem.config.customSkillDirs` (L134-136), `dsh-plan-mode.config.section`, `dsh-compaction-tool-result-pruner.config.*`, `dsh-tool-subagent.config.*`, etc. Check 28v reports `schema-checked rows: 18`. If a future dsh renames `prefix` again, the same whole-preset rejection returns. This is **guarded** (advisory Check 28v + `--smoke`, CI/release-time) but **not eliminated** — and under DEC-187 I-3 it is an explicitly *permitted* forward dependency, so this is a disclosure question, not an invariant violation.

The residual is disclosed accurately in `feature-flags-0.80.0.md:32` — *"本版交付**结构性根因消除**（上游内部行 UPDATE 面 + `!!js` 自定位面退役）"* — which scopes the claim to precisely the two retired faces. `release-checklist-0.80.0.md:115` does not: it attributes the elimination to *"FIX-307/308 同源的上游内部面耦合面退役"*, and FIX-308's leg is leg 2, which is not retired. L21 (*"消除 RISK-050 的结构性根因"*) has the same unscoped phrasing. See F6.

---

## 10. Findings

Severity key: **P0** = must not ship / broken; **P1** = must fix before release authorization; **P2** = should fix (release-blocking only if unaddressed); **P3** = discussion.

### F1 — P1 — shipped CHANGELOG asserts both superseded claims
**File**: `project/CHANGELOG.md:19`
> `机检判据 = 安装后 dsh 组合后 entry 列表与未安装时**逐字节等价**。FIX-310 即按此不变量重做：宿主平面贡献归零（不改任何既有行、不注册全局 provider/服务/工具、不声明 system-trust 预设根）。`

Two superseded propositions in one sentence. DEC-188 ② declares the byte-identical criterion unsatisfiable under the user's official-command requirement and *"**不再**引用更强口径"*; and the delivered form explicitly does **not** claim zero host-plane contribution — `release-checklist-0.80.0.md:49` says *"**不声称「宿主平面贡献为零」**"* and `:62` supplies the corrected criterion (entry list gains exactly one row naming only this package). `project/CHANGELOG.md` is a tracked, gate-checked release artifact (`check-release --require-changelog`) and the most user-visible release surface, so the candidate currently contradicts its own release checklist and the governing decision on the release's headline architecture change.
**Evidence**: `grep '宿主平面贡献归零' / '逐字节等价'` → this line; read of L19; `check-version-consistency` PASSED (so the file is in the authoritative set).

### F2 — P1 — README asserts per-session global skill availability, which FIX-310 removed
**Files**: `README.md:33` (English adapter table), `README.md:76` (English install section), `README.md:392` (Chinese dsh section)
> L76: *"Two things then activate together: the governance skills and `/governance` command projections load in **every session of that profile**〔isolation: 2026-09-05, isolated DSH_HOME, dsh 0.1.2-rc.1 + pnpm 11.22.0, Windows-only〕, **and the `governance` preset … appears in the preset roster**〔isolation: 2026-09-12 …〕"*
> L392: *"治理 skills 与 `/governance` 命令投影在该 profile 的**每个会话**中可用〔isolation: 2026-09-05 …〕"*

That availability came from the host-plane `skill-filesystem` UPDATE row, which FIX-310 deleted. Skills now register only through the *preset's* `skill-filesystem.customSkillDirs`, i.e. only in sessions that mount the governance preset. The candidate's own documents state the opposite as the target: `session-snapshot.md:152` criterion 3 — *"**非治理预设会话（如 `standard`）：技能目录不含任何治理技能。** ← 反向依赖的判据（本次改造核心目标）"* — and `release-checklist-0.80.0.md:96` lists it as an **unverified 真机验收面** item. Note that commit `5a259e2` rewrote the *adjacent* clause in both L33 and L76 and re-cited it as `2026-09-12`, but deliberately left this clause with its pre-FIX-310 `2026-09-05` citation. A user reading the shipped README will expect `/governance` in a `standard` session and, per the release's own acceptance test, will not get it.
**Evidence**: exact line reads; `git show 5a259e2 -- README.md` (shows the kept clause + its stale citation beside the re-cited clause); `grep 'every session|每个会话' README.md` → 33, 76, 392.

### F3 — P2 — `session-snapshot.md` restates the retracted criterion in its non-superseded invariants section
**File**: `.governance/session-snapshot.md:79`
> `**可机检判据（I-3）**：安装本插件后，dsh 的**组合后 entry 列表**（…）必须与**未安装时逐字节等价**。`

This is the exact "byte-identical entry list" wording checklist 2(a) asks about, and it sits in the section headed *"不可违反的架构不变量（用户裁定 2026-09-12，**永久生效**）"* (L73) — which the `⛔` supersession at L65 and its carve-out at L71 do **not** cover (L71 exempts only the two *later* sections). The retraction exists, but only inside the later `已作废的中间设计` table (L123, L136). Net effect: the snapshot asserts the unsatisfiable criterion as current authoritative text in one place and as retracted in another. Headers and acceptance list also contradict it (L146, L150).

### F4 — P2 — archived DEC-187 row still carries both superseded claims, unmarked
**File**: `.governance/archive/decisions/decisions-v0.1.0-0.78.1.md:44` (the DEC-187 row)
> action cell: ``` `cordis.patch.yml` 与 `lib/index.js` 均不保留（宿主平面贡献归零）```
> 机检判据 cell: `安装后 dsh 组合后 entry 列表（全部 host 行的存在性 / config / disabled 状态 + 任何宿主平面注册表内容）与未安装时逐字节等价`

DEC-188 corrected the RISK-050 cell in place with an explicit replacement marker (`risk-log.md:44`) but left DEC-187's own row untouched — consistent with DEC-188's own 治理记录同步 list, which names decision-log(self)/risk-log/plan-tracker/session-snapshot and not DEC-187. The row is also mis-filed: a 2026-09-12 decision is stored under `- 归档版本: v0.77.0`, which is why a reviewer searching `.governance/decision-log.md` for the governing invariant (as this brief did) finds nothing. This finding also **refutes the brief's premise** that DEC-188 rewrote both records.
**Note**: the archive is gitignored, so this is not part of the candidate diff — but checklist 2(a) asks about *remaining* governance records, and this one is quotable as the authoritative text of a decision DEC-188 says is "永久生效".

### F5 — P2 — retirement fan-out gap: data inventory still lists the deleted guard as live
**File**: `docs/requirements/data-inventory-0.80.0.md:175-176`
> `| DSH_SKILLS_DISK_PATTERNS | L6784-L6792 | 9 | tuple[2] | … 内部：check_dsh_skills_manifest L6914 | 保持 |`
> `| _REJECT_SECURITY_DETAIL | L6796-L6801 | 6 | dict[2] | … 内部：check_dsh_skills_manifest L6889/L6895 | 保持 |`

All three symbols now have **0 occurrences** in `verify_workflow.py`, and the cited line ranges have moved: L6784 is blank, L6796 is an unrelated comment about a temp home, L6914 is unrelated smoke-verdict code. The doc is a 2026-09-29-window deliverable (DOC-003) whose data-block inventory is now objectively wrong for two rows; `session-snapshot.md:210` enumerated the FIX-310 coupling faces to close and did **not** include this file, which is why it was missed. Verified the file was untouched by `5a259e2` (`git show --stat`).

### F6 — P2 — "结构性根因消除" over-scoped for the FIX-308 leg
**Files**: `docs/release/release-checklist-0.80.0.md:115` (and `:21`)
> L115: *"RISK-050 本版交付**结构性根因消除**（FIX-307/308 同源的上游内部面耦合面退役）"*

FIX-308's leg — *"预设行的 config 键随 dsh 升级失效"*, whose failure mode RISK-050 itself calls 致命 (*"单行坏行否决整棵预设挂载 → 新会话无法创建 + 预设面崩溃"*) — is not retired: the delivered template still binds 23 `@deepseek-ai/dsh-*` rows to their Config schemas (`dsh-persona.config.prefix` at template L48 being the exact former defect). `feature-flags-0.80.0.md:32` states the same conclusion correctly scoped (*"上游内部行 UPDATE 面 + `!!js` 自定位面退役"*); the release checklist should adopt that scoping, or say plainly that the preset-plane config-schema coupling is *guarded* (advisory Check 28v, release-time `dsh_upgrade_regression`) and remains a live forward dependency permitted by DEC-187 I-3. **This is a disclosure defect, not an invariant violation** — see §9.

### F7 — P2 — DEC-187's own forward deliverable is unfulfilled (no product-surface record of I-1/I-2/I-3)
DEC-187's 后续 cell requires: *"把 I-1/I-2/I-3 写入 `core/protocol/plugin-contract.md` 作为对宿主方的承诺（防回流）"*.
**Evidence**: `skills/software-project-governance/core/protocol/plugin-contract.md` (10774 chars) contains **0** occurrences of `I-1`, `I-2`, `I-3`, or `DEC-187`. Repo-wide, the invariant tokens appear only in `lib/index.js:33` (a code comment), `skills/…/tests/test_dsh_adapter.py:434` (a test comment), and governance records — so no machine-checkable guard exists in the product surface for the architecture constraint the candidate's headline change exists to satisfy. (The `!!js` clause of DEC-187 *is* partially guarded, by `test_dsh_adapter.py`.)
**Note**: this requirement traces to a real file (the archived DEC-187 row), not to the brief.

### F8 — P3 — lone-CR normalization diverges between the two renderers
Python `Path.read_text` / `open(newline=None)` maps `\r`, `\n` **and** `\r\n` to `\n`; `lib/index.js:150` normalizes only `\r\n`. Demonstrated in-memory (no file written):
```
python -c "import io; print(repr(io.TextIOWrapper(io.BytesIO(b'a\rb\r\nc'), encoding='utf-8').read()))"  → 'a\nb\nc'
node   -e "console.log(JSON.stringify('a\rb\r\nc'.replace(/\r\n/g,'\n')))"                              → "a\rb\nc"
```
Latent only: for the current LF/CRLF template the two renderers agree byte-for-byte (§4, equal SHA256), and no test exercises a lone-CR template. Recorded because the checklist's "LF normalization" contract is stated as absolute in both module headers and is not total.

### F9 — P3 — "staging+rename 原子" wording; JS path leaks its staging dir, Python path does not
`lib/index.js:210-211` and `launch.py:270-272` both do `rm(target)` → `rename(staging, target)`; that is a replace-with-a-window, not an atomic swap, so "原子" (release-checklist L57, feature-flags L23) is stronger than the code. A crash in the window leaves no preset until the next boot — self-healing, because the version marker went with the directory. Additionally the Python path removes its staging dir on render failure (`launch.py:266`) while the JS catch block (`lib/index.js:214-216`) does not, so a failure at the rm/rename step permanently leaks `<userDir>.staging-<ts>-<rand>/`. **Verified not roster-visible**: `@deepseek-ai/dsh-agent-presets/lib/index.js:403` filters child names by `PRESET_ID = /^[a-z0-9][a-z0-9-]*$/`, which a name containing `.` fails. Disk litter + a Python/JS asymmetry in the paths that are documented as unable to disagree.

### F10 — P3 — stale CLI flag in a marketplace doc
**File**: `docs/marketplace/dsh-preset-adapter-0.73.0.md:31` — `python adapters/dsh/launch.py --install --mode copy   # 自包含快照模式`.
`--mode link|copy` existed before `5a259e2` and was deleted by it (`git show 5a259e2^:adapters/dsh/launch.py` still contains `--mode link|copy`; HEAD's `argparse` has no `--mode`). The doc is version-scoped (`-0.73.0`) so impact is low, but it is not marked historical and now documents a removed flag.

### F11 — P3 — "`dsh plugin remove` stays symmetric" is not supported by the code
**File**: `lib/index.js:44` — *"the settings page shows it as a custom preset with delete and open-folder available, and `dsh plugin remove` stays symmetric."*
The install side is automatic (the row renders the preset on boot); the removal side is manual — `adapters/dsh/launch.py:36-38` states that `dsh plugin remove` *"manages the profile's pnpm bundle layer, never the user preset root, so it cannot remove this preset"*. After an official uninstall the user-root preset survives (now pointing at skill roots that may no longer exist) until the user deletes it. The asymmetry itself is disclosed in `rollback-plan-0.80.0.md:37`; only the word "symmetric" in the module header is inaccurate.

---

## 11. Items explicitly checked and found sound (no finding)

| # | Checked | Evidence |
|---|---|---|
| N-1 | one insert row, zero UPDATE, zero `!!js`, zero `trust`, `ctx.` only `ctx.logger` | structural YAML parse + 5 `ctx.` hits all `ctx.logger` |
| N-2 | warn-only contract — no throw escaped `apply()` even with a hostile `DSH_HOME` and no logger | two node probes |
| N-3 | renderer parity is byte-identical and test-covered | equal SHA256 `00e0d330…` (13566 chars); `test_dsh_adapter.py:1105-1160`; 46 passed |
| N-4 | no half-written preset possible (staging + rename on both paths) | read of `lib/index.js:202-211`, `launch.py:260-272` |
| N-5 | no copied `skills/` tree; single source preserved | `agent-presets/` = 2 files; full `SKILL.md` enumeration |
| N-6 | retirement complete in product code (manifest, both `PLUGIN_SCOPE_DIRS`, cleanup scope, contract-matrix snapshots, registry, TOOLS.md) | symbol greps = 0; 295 + 46 tests green |
| N-7 | deletion-then-rebuild is what the code does, and every mentioning document discloses it | §8 — zero persistence claims found |
| N-8 | `17eda48` vs `96a0030` — **not** a discrepancy | `96a0030` is an annotated tag object peeling to commit `17eda48`; `git rev-list --count 17eda48..v0.79.0` = 0 |
| N-9 | release gates independently reproduced | `check-injection-contract` PASSED (3 files/23 anchors); `check-version-consistency` PASSED (exit 0); `check-dsh-preset-compat` PASSED (1 composition / 23 enabled rows / 18 schema-checked / writes: 0) |
| N-10 | `README.md:33`/`:76` "byte-identical composition" (between the two delivery paths) | true given the same package root — see U-3 |

---

## 12. `未知` items (explicitly not verified — no file, command, or quoted-user evidence available to me)

- **U-1 — Real-machine acceptance surface.** Whether the settings page shows the「自定义」tag, offers delete + open-folder, whether a non-governance preset session is really free of governance skills, and whether a governance session's catalog is complete. Only the user's real dsh can answer; the candidate itself declares these unverified (`release-checklist-0.80.0.md:91-99`, `session-snapshot.md:157`). I neither confirm nor deny them. **This is the single most load-bearing unknown for both F2 and the RISK-050 closure path**, and it is why F2 must be fixed on the *documentation* side regardless of the runtime outcome.
- **U-2 — `dsh-novel-writing` reference implementation.** Both DEC-188 and `session-snapshot.md:88-101` rest heavily on *"参照用户已跑通的 `dsh-novel-writing`"* and quote `writing-workflow/cordis.patch.yml` (one insert row) and `lib/index.js` L1425 → L157-190 `ensurePreset`. I could not locate that repository on this machine and therefore **did not verify** any of those quotations. They are load-bearing for the "the official install command must stay the delivery vehicle" argument, so an unreviewed premise remains inside the decision chain — the same failure mode DEC-187 documents.
- **U-3 — Cross-root path stability.** `launch.py` resolves symlinks (`Path.resolve()`) while `lib/index.js` does not (`import.meta.url`). Under `dsh plugin … add link:<repo>` the two delivery paths are given *different* roots (repo checkout vs a junction into `node_modules`), so their outputs are byte-identical *as functions* but not necessarily *as files written to the same destination*. Whether dsh/pnpm materialises that link as a junction whose unresolved path is stable across `dsh plugin update` cycles — and what happens to an already-rendered user-root preset whose absolute `customSkillDirs` point into a `.pnpm` directory that a later install moves — I could not verify from this repo. The version-marker idempotence means a version bump re-renders and self-heals; a *re-resolution at the same version* would not. Not asserted as a defect; recorded as unresolvable here.
- **U-4 — `npm publish` / registry availability.** `package.json:5` sets `"private": true` while `cordis.patch.yml` names the package for resolution. Every install command documented (`README.md:377-388`, `release-checklist:99`) uses `link:` / `file:` / `github:` — no registry install is claimed or demonstrated. Whether a non-checkout end user can install via the official command from a registry is **unknown** and **not claimed** by the candidate. Additionally the brief's premise that the official `add/remove/update` commands "work unchanged" is verified only for the `link:` form.
- **U-5 — FIX-310 has no implementation review.** `release-checklist-0.80.0.md:104` records that the original R0/R1/R2 rounds are **void** (built on the fabricated premise) and that the rework is covered by "M-3 候选双审". This R0 is the Design half of that; I found no completed **Code** review of `lib/index.js` / the reworked `launch.py` in the window (`docs/reviews/` contains no `REVIEW-FIX-310-*` for the post-DEC-187 implementation). I am not the code reviewer, so I flag this as an unverified process gap rather than a finding.

---

## 13. Conclusion

The **architecture** is sound and I verified it mechanically, not from the release prose: `cordis.patch.yml` is structurally incapable of touching a pre-existing host row (single `insert` key, one row, no `!!js` tag reachable by `yaml.safe_load`), `lib/index.js` publishes nothing and reads no host service, the two renderers agree byte-for-byte from the same root and are test-covered, the warn-only and staging contracts hold under a hostile-`DSH_HOME` probe, single-source discipline is intact (no copied skills tree), the `dsh.skills` + `presets/` retirement is complete in product code with green fan-out tests and regenerated contract-matrix snapshots, and the deletion-then-rebuild semantics are honestly disclosed everywhere they are mentioned. FIX-310 does what DEC-187/DEC-188 say it does, and it genuinely removes the host-plane leg of RISK-050.

The **design-consistency** plane does not yet hold. The candidate ships a `CHANGELOG` that asserts both claims DEC-188 was written to retire (F1), and a `README` that promises governance skills in *every* session of the profile while the release's own acceptance criterion demands the opposite and leaves it unverified (F2). Three further governance/live documents still carry superseded or stale text (F3/F4/F5), DEC-187's own anti-regression deliverable was never written into the product surface (F7), and the RISK-050 closure language outruns the delivered scope for the FIX-308 leg (F6). Because F1 and F2 contradict the governing decision and the candidate's own release checklist on the release's headline change — and F2 is exactly what the user will read when performing the unverified real-machine acceptance — the candidate needs correction and one re-review before M-4 authorization.

I did not modify any product file. My only write is this report.

`unresolved_blockers=2`

> **Definition used**: `unresolved_blockers` = the number of findings that must be closed before the release candidate may proceed to M-4 user authorization = **F1** (P1) + **F2** (P1). The P2/P3 findings (F3-F11) are recorded for the fix batch and do not by themselves block authorization. Items in §12 are declared `未知` and are **not** counted as blockers, because none of them is a technical impossibility — each is a verification I am not positioned to perform from this repository (the largest being U-1, the real-machine acceptance that only the user can run).
