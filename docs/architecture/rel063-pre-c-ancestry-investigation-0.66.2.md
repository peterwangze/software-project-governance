# REL-063 pre-C Ancestry Investigation — verifier bug vs. design defect

- **Task / role**: Architect read-only investigation (no code, commit, or governance-record changes)
- **Date**: 2026-07-23
- **Subject**: `verify_rel063_evidence.py --phase pre_c` slice-chain ancestry check
- **Authority**: `docs/architecture/release-incident-recovery-0.66.2.md` (immutable FIX-214 Design R2 + FIX-218 amendment candidate)
- **Status**: Investigation report only. No authorization is implied. Any code change requires a separate DEC + Developer + Code Reviewer task.

---

## 1. Summary (verdict)

**Verdict: verifier bug (with a compensating guard), not a design defect.**

`validate_slice_chain`'s Git cross-check demands that each accepted slice commit be the **direct parent** of the next (`commit_parents(child) == [prior_accepted]`). The architecture's compensation-retry design deliberately produces, for each FIX, an R0/initial commit plus an accepted **child** compensation commit, so the accepted subject's direct parent is its own R0, not the prior accepted slice. The accepted slices DO form the required acyclic ancestry (`S215` is a `merge-base --is-ancestor` of `S216`, etc.), exactly as §2 goal 4, §4.6, §7.1, and §7.2 require. The verifier over-constrains "acyclic ancestry" into "direct parent" and rejects the documented topology. **Recommended fix: Option A** — relax the verifier to acyclic-ancestry (`git merge-base --is-ancestor`) and add a path-set guard proving each R0→accepted-child delta stays inside that slice's declared scope.

## 2. Facts (ancestry mismatch, exact SHAs)

Real Git history (verified read-only, `git show -s --format=%P`, `git merge-base --is-ancestor`, `git diff --name-only`):

```
6a78b12 (incident head / origin master)
  └─ 9816a084  FIX-215 R0      (parent = 6a78b12)
       └─ d3fc6503  S215 accepted child   (parent = 9816a084)   ← evidence subject_sha
            └─ 19b2a17  FIX-216 R0         (parent = d3fc6503)
                 └─ 2d7ae98f  S216 accepted child  (parent = 19b2a17)  ← evidence subject_sha
                      └─ d2df3b66  FIX-217 R0      (parent = 2d7ae98f)
                           └─ 22488058  S217/B accepted child (parent = d2df3b66) ← evidence subject_sha
```

Direct-parent check failures in `validate_slice_chain` (verify_rel063_evidence.py lines 822-838):

| Slice | Topology cross-check (lines 824-829) | Git cross-check (lines 836-838) | Required | Actual direct parent | Result |
| --- | --- | --- | --- | --- | --- |
| S216 (`2d7ae98f`) | `subjects["S216"].parents == [S215.sha]` | `commit_parents("2d7ae98f") == [d3fc6503]` | `[d3fc6503]` | `[19b2a17]` | **FAIL / PHASE_DRIFT** |
| S217 (`22488058`) | `subjects["S217"].parents == [S216.sha]` | `commit_parents("22488058") == [2d7ae98f]` | `[2d7ae98f]` | `[d2df3b66]` | **FAIL / PHASE_DRIFT** |

Acyclic ancestry (verified):

- `git merge-base --is-ancestor d3fc6503 2d7ae98f` → **true** (S215 is an ancestor of S216)
- `git merge-base --is-ancestor 2d7ae98f 22488058` → **true** (S216 is an ancestor of S217)
- `git merge-base --is-ancestor d3fc6503 22488058` → **true** (S215 is an ancestor of S217)
- `git merge-base --is-ancestor 6a78b12 d3fc6503` → **true** (incident head is an ancestor of S215)
- `git log --oneline --first-parent 22488058` walks `22488058 → d2df3b66 → 2d7ae98f → 19b2a17 → d3fc6503 → 9816a084 → 6a78b12`: a single linear chain with **zero cycles, zero back-edges, zero merges**.

The six slice evidence JSONs (`.governance/primary-review-evidence/REL-063/FIX-{215,216,217}-{code,qa}.json`) all bind `subject_sha` to the **accepted child** SHA (d3fc6503 / 2d7ae98f / 22488058), confirming the accepted subject is the child of R0.

> Note (out of scope, recorded for transparency): `.governance/primary-review-evidence/REL-063/FIX-217-qa.json` carries `producer_id` `/root/fix216_qa` (apparent copy-paste from FIX-216). This does not affect this investigation; `validate_distinct_role_sets` keys producers per-role across artifacts and would only flag exact producer overlap, not a mislabeled id. Flag separately if relevant.

> Note (environment): the authority files `authority-input.json`, `orchestration-receipts.json`, and `topology-record.json` are **not yet present** under `.governance/review-authority/REL-063/`. `run_pre_c` would therefore fail earlier at `load_authority_input`/`load_orchestration_receipts`/`load_topology_record` with `UNKNOWN` before reaching `validate_slice_chain`. The ancestry blocker described here is the **next** failure that will surface once those three files are produced with topology-declared parents matching real Git. This report addresses that next blocker.

## 3. Design intent analysis (direct parent vs. acyclic ancestry)

The architecture is internally explicit and unambiguous: the chain requirement is **acyclic ancestry**, not direct parent. Reading (b).

### 3.1 §3 Decision (lines 57-61) — the compensation-retry design is normative

> "Each slice first creates a local immutable commit, then Code Review and QA bind their reports to that exact full SHA; only an accepted subject is pushed and handed to the next slice. **A failed subject remains immutable and receives a new child compensation commit plus fresh exact-subject review; it is never amended or rebased.**"

This sentence defines the accepted subject as the **child** of a compensation commit on failure. The accepted subject's direct parent is therefore the compensation/R0 commit, by design. Demanding `accepted_child.parent == prior_accepted_slice` would contradict this clause whenever a slice retries.

### 3.2 §2 Goals (line 38-39) — the ancestry contract is stated as acyclic

> Goal 4: "Preserve an **acyclic ancestry** from the incident head through accepted slice heads, candidate `C`, transition `T`, and annotated `v0.66.2`."

The governing noun is **"acyclic ancestry"**, not "direct parent chain". An acyclic ancestry relation is exactly the `merge-base --is-ancestor` relation that holds here.

### 3.3 §4.6 (lines 452-455) — failure creates a child, the graph has zero cycles

> "Failed review creates a new immutable child compensation subject within the same exact set and a fresh report pair; no edge returns to an earlier subject, so the execution graph has **zero cycles**."

The integrity property named is **zero cycles** (acyclicity), not edge-adjacency. The R0→accepted-child edge and the accepted-child→next-R0 edge together preserve acyclicity.

### 3.4 §7.1 (lines 743-766) — the state machine formalizes "child, never amend/rebase"

> "LOCAL_COMPENSATION_COMMIT(subject_n_attempt_k+1, parent=attempt_k) -> fresh exact-subject Code Review and QA … The new compensation commit is a child, never an amend/rebase/replacement. Only an accepted terminal subject is named `S215`, `S216`, or `S217` … Attempt number and parent edges are monotonic, so **execution-semantic cycle count is zero**."

Again: the named subject is the terminal child; the integrity guarantee is **cycle count zero**. A direct-parent-equality check is stricter than the formal model.

### 3.5 §7.2 (lines 789-793) — "Required accepted ancestry is linear"

> "Required accepted ancestry is linear:
> `6a78b12 ... -> S215 -> S216 -> S217(B) -> C -> T`"

This is the single phrase that could be read as (a) "direct parent". But it must be read in context with §3 and §7.1: the arrows denote the **acyclic accepted-ancestry order**, and §7.1 already established that accepted subjects are terminal children of compensation commits. "Linear" here means **no branching, no cycles, no parallel heads** — which the `--first-parent` walk confirms (one straight line, no merges). It cannot mean `direct_parent(S216) == S215`, because §7.1 makes that false by construction on any retry. Reading (a) renders §3 and §7.1 self-contradictory; reading (b) reconciles all three.

### 3.6 §12 BT-214-1 (line 877) — the threat the binding protects against

> "Reviewer predicts a future SHA or report is edited after commit — Commit locally first; canonical report binds exact existing SHA; failure creates a new child and fresh report."

The protection is **SHA-binding to an existing immutable commit** (defeats prediction + post-hoc edit) plus **child-not-amend** (defeats history rewrite). Neither protection requires the accepted child's parent to be the prior accepted slice; both are satisfied as long as the bound SHA exists immutably and the accepted chain is acyclic.

**Conclusion: the design means (b) acyclic ancestry. The verifier's direct-parent check is an over-strict implementation of (b). It is a verifier bug, not a design defect.**

## 4. Threat-model impact analysis (does acyclic-ancestry weaken Gate C3?)

Gate C3 (§5 matrix line 471) negative fixture: "**combined path, wrong parent, reused subject, hidden amend/rebase**". The question is whether replacing `commit_parents == [prior]` with `merge-base --is-ancestor prior current` lets any of these four slip through. It does not, provided the acyclic-ancestry check is paired with the path-set guard in §6 below.

| C3 threat | Direct-parent check catches it? | Acyclic-ancestry + path-set guard catches it? (reasoning) |
| --- | --- | --- |
| **combined path** (a slice smuggles another slice's files) | **No.** Direct parent says nothing about file scope. | **Yes, with the guard.** The R0→accepted-child delta path-set guard (§6) plus the existing per-slice `M`/`N` scope algebra (§4.2-4.4) and `assert_path_set` (used for C/T topology) bound each slice to its declared files. Acyclic ancestry alone does not add or remove this protection. |
| **wrong parent** (a slice descends from the wrong base, e.g. S216 from 6a78b12 skipping S215) | Yes. | **Yes.** `merge-base --is-ancestor S215 S216` fails if S215 is not reachable from S216. A wrong base that skips a prior accepted slice fails the ancestry check exactly as before. |
| **reused subject** (the same SHA appears twice, or a later slice points back at an earlier accepted SHA) | Yes, accidentally (a back-edge would change direct parent). | **Yes, explicitly.** Acyclicity is the formal negation of reuse-with-back-edge. `merge-base --is-ancestor S216 S215` returning true would prove a cycle and is rejected. The topology's `attempts` table (one ACCEPTED per task, unique `(task_id, attempt_no)`, monotonic parents in §6.2) and the SHA-uniqueness of `S215/S216/S217` already forbid reuse at the record level. |
| **hidden amend/rebase** (an accepted SHA's content was rewritten) | **Indirectly and weakly.** Direct-parent equality would also change if a rebase altered parent edges — but a content-only amend of a commit that preserves its parent list passes the direct-parent check. The real defense is BT-214-1's SHA-binding: an amended commit has a different SHA, so the evidence `subject_sha` no longer resolves to it. | **Yes, via SHA-binding (unchanged).** The accepted subject SHAs are bound by the six evidence JSONs and the topology ACCEPTED attempts. Any amend produces a new SHA; the verifier's `resolve_commit` + `subjects[symbol].sha` equality against the ACCEPTED attempt SHA (lines 819-820) fails. Acyclic ancestry does not weaken this; the SHA pins do the work. |

**Precise argument on "hidden amend/rebase"**: the direct-parent check does NOT detect a content amend that preserves parent edges (the most common amend). What actually detects amend/rebase is (i) the bound `subject_sha` no longer resolving to the reviewed commit, and (ii) for rebases that move a commit, the resulting acyclicity or reachability violation between slices. Switching to ancestry-only loses nothing here, because direct-parent equality was never the amend/rebase detector — the immutable SHA binding was, and remains.

**Precise argument on "reused subject"**: acyclic ancestry is *stronger* than direct-parent equality against reuse. A direct-parent check only inspects one edge; it cannot tell if S216 and S217 secretly share an identical tree or if a fourth hidden commit reuses S215's SHA. The acyclic-ancestry relation over the *accepted set* {S215, S216, S217} plus the uniqueness constraints in `validate_topology` (`_validate_attempts` enforces exactly one ACCEPTED per task, unique `(task_id, attempt_no)`) collectively forbid reuse. No C3 weakening occurs.

**Net: Option A with the path-set guard preserves all four C3 defenses.** The only thing removed is the spurious rejection of the documented R0+child compensation topology.

## 5. Recommended fix path

### Recommendation: **Option A (fix the verifier)** — with a mandatory path-set guard.

Rationale for each option:

- **Option B (re-slice so accepted subjects are direct parents)**: **Infeasible and forbidden.** §3 line 61 ("it is never amended or rebased"), §4.6 ("no edge returns to an earlier subject"), §7.1 ("never an amend/rebase/replacement"), and §10 ("do not amend/rebase the failed subject") all forbid rewriting the accepted subjects. Re-slicing would also destroy the immutable incident lineage that the entire 0.66.2 recovery exists to preserve (§1). Rejected.

- **Option C (trust topology-declared `parents`)**: **Weaker than A and abandons the Git-truth cross-check.** The topology record is a `.governance` JSON file; §6.2 explicitly says "Production identity comes from platform dispatch and immutable Git object queries, not workspace JSON; the three files are cross-checks and cannot refresh their own pins." Gate C3's whole point is to cross-check the topology against immutable Git objects. Trusting `subjects[*].parents` without a Git reachability query reopens the BT-214-2 four-record-forgery surface. Rejected as the primary fix; the topology-declared `parents` should remain a *secondary* record validated for acyclicity, not the source of truth.

- **Option A (relax to acyclic ancestry + path-set guard)**: **Correct, minimal, and threat-model-preserving.** Concretely:
  1. Add a helper `is_ancestor(ctx, ancestor, descendant) -> bool` using `git merge-base --is-ancestor <ancestor> <descendant>` (exit 0 = true, exit 1 = false, anything else = `GitUnknown`).
  2. In `validate_slice_chain`, replace the direct-parent Git cross-check (lines 834-838) with: for each consecutive pair `(prior, current)` in the chain, require `is_ancestor(prior_sha, current_sha)`. Also assert the incident head (`6a78b12`) is an ancestor of `S215` if the chain starts at S215, to anchor the chain to the incident base.
  3. Keep the topology-side `subjects[*].parents` record, but validate it for **acyclic consistency** (the declared parents, followed transitively, must not cycle and must be consistent with the Git reachability order), not for direct-parent equality against the prior accepted slice.
  4. **Add the compensating path-set guard** (this is the load-bearing addition that preserves the "combined path" defense once direct-parent equality is gone): for each accepted subject SHA, compute `changed_paths_between(topology-declared-parent, accepted_child_sha)` and assert it is a subset of that slice's declared `M ∪ N` (M215∪N215, M216∪N216, M217∪N217 from §4.2-4.4). This proves the R0 and its accepted child only ever touched that slice's exact scope — defeating a slice that smuggles another slice's work into its R0.
  5. Preserve the existing direct-parent check **only where the design actually requires it**: `run_assert_candidate_topology` (C sole parent B — line 1499-1501) and `run_assert_transition_topology` (T sole parent C — line 1514-1516) and `run_full` (T sole parent C — line 1392-1394). Those commits ARE single direct commits with no compensation retry, so direct-parent equality is correct there and must not change.

  Product code change → Governance Developer implements + Code Reviewer reviews under the normal FIX task gate. This report does not authorize that work.

### Why A beats C on the "Git-truth cross-check" concern

C3's threat model is "the topology record lies about Git". Option A keeps the immutable-Git reachability query as the cross-check (just `is-ancestor` instead of `== parent`); Option C drops the Git query and trusts the JSON. A keeps C3's integrity contract; C does not.

## 6. Regression risk and required tests

### 6.1 Existing tests at risk in `test_verify_rel063_evidence.py`

- `SliceChainTests.test_valid_linear_chain_passes` (line 701): uses `_NoTagGit` whose `parents` map models a **direct** linear chain (`S216.parent = S215`, `S217.parent = S216`). Under Option A this test still passes (direct parent ⇒ ancestor), but the fake git runner `_NoTagGit`/`FakeGitWithCandidate` must be extended to answer `merge-base --is-ancestor` queries, otherwise the new check raises `GitUnknown` (UNKNOWN). **Required test-harness change.**
- `SliceChainTests.test_wrong_parent_rejected` (line 706): sets `subjects["S216"]["parents"] = ["0"*40]` and expects PHASE_DRIFT. Under Option A the topology-side check becomes "acyclic consistency", so this must still reject — but the rejection now comes from the ancestry query (`is_ancestor("0"*40, S216_sha)` is false / UNKNOWN) rather than list inequality. The assertion (`PHASE_DRIFT`) still holds; the fake runner must model the wrong-parent case as non-ancestor.
- `SliceChainTests.test_wrong_chain_spec_rejected` (line 715): reorders the chain to `["S216","S215","S217"]`. Under ancestry, `is_ancestor(S216, S215)` is false, so this still rejects. Behavior preserved.
- `PreCDriverTests.test_pre_c_passes_and_writes_candidate_manifest` (line 966) and `CandidateDriverTests.test_candidate_phase_passes_with_rehearsal_and_review` (line 1178): both rely on `_NoTagGit`/`FakeGitWithCandidate` modeling a direct linear chain. They will PASS under Option A only after the fake runners learn `merge-base --is-ancestor` and the path-set guard is fed the per-slice `M∪N` sets (or the guard is made injectable per test).

No test currently models the R0+accepted-child topology, so **no existing test encodes the bug as "expected PASS"** — the bug is a missing fixture, not an encoded regression. This lowers regression risk: the fix adds capability rather than inverting an assertion.

### 6.2 New tests required

1. **Positive: R0+accepted-child slice chain PASSES pre_c.** A fixture topology where `subjects["S216"].parents == [R0_216_sha]` (the real compensation pattern), `R0_216_sha`'s parent is `S215.sha`, and the fake runner answers `is_ancestor(S215, S216)=true`, `is_ancestor(S216, S217)=true`. The path-set guard is given each slice's real `M∪N` and the R0→child deltas are subsets. Verdict: PASS. (This is the regression test for the actual blocker.)
2. **Positive: direct-parent chain still PASSES.** The existing linear fixture continues to pass (direct parent ⇒ ancestor). Ensures the relaxation is a strict generalization.
3. **Negative: wrong base (skipped slice) rejected.** Topology where S216's R0 descends from `6a78b12` directly, bypassing S215. `is_ancestor(S215, S216)` must be false → PHASE_DRIFT. Covers C3 "wrong parent".
4. **Negative: back-edge / reused subject rejected.** Topology where S217's ancestry includes S217 itself (cycle), or where two slices bind the same accepted SHA. Must reject via acyclicity or `_validate_attempts` uniqueness. Covers C3 "reused subject".
5. **Negative: R0 smuggles out-of-scope paths rejected.** A fixture where the R0→accepted-child delta for S216 includes a path outside M216∪N216 (e.g. a FIX-217 ledger file). The new path-set guard must raise PHASE_DRIFT. Covers C3 "combined path".
6. **Negative: hidden amend detected via SHA pin.** A fixture where the topology ACCEPTED attempt SHA differs from `subjects[symbol].sha` (already covered by lines 819-820, but add an explicit test that an amended commit with a new SHA is rejected even if its ancestry is otherwise valid). Covers C3 "hidden amend/rebase".
7. **Negative: incident-head anchor.** A fixture where S215 does NOT descend from the incident head `6a78b12` (e.g. it was built on an unrelated branch). The anchor check must reject. Covers lineage forgery outside the slice set.

### 6.3 Test-harness work

- Extend `_NoTagGit` and `FakeGitWithCandidate` to answer `["merge-base","--is-ancestor",A,B]`: return rc=0 when the pair is in the modeled ancestor relation, rc=1 when not, rc=124/125 for unavailability. The modeled relation should be derived transitively from the `parents` map.
- Add a way to inject per-slice `M∪N` path sets and per-slice R0 SHAs into the fakes so the path-set guard can be exercised in both positive (subset) and negative (out-of-scope) cases.

## 7. Authorization boundary

This document is an **investigation report only**. It:

- Does **not** authorize any change to `verify_rel063_evidence.py`, `test_verify_rel063_evidence.py`, the architecture doc, or any governance record.
- Does **not** constitute Design Review approval of Option A. The architecture doc's status is `FIX-218_DESIGN_AMENDMENT_CANDIDATE / AWAITING_INDEPENDENT_DESIGN_REVIEW_R0`; per §14, only an independent `REVIEW-FIX-218-DESIGN-R0` with `APPROVED` and `unresolved_blockers=0` may authorize resuming implementation.
- Recommends that the Option A code change be tracked as a **separate FIX/DEC task** with its own Developer + Code Reviewer gate, and that the architecture doc receive a narrow amendment clarifying that C3's ancestry contract is acyclic (`merge-base --is-ancestor`) rather than direct-parent, with the path-set guard named as the "combined path" defense. That amendment itself requires independent design review before any verifier code change merges.
- The missing authority files (`authority-input.json`, `orchestration-receipts.json`, `topology-record.json`) are a separate, earlier blocker; producing them with topology-declared parents consistent with real Git (R0 parents on the accepted children) is a prerequisite for `run_pre_c` to even reach `validate_slice_chain`. That work is likewise out of scope here.
