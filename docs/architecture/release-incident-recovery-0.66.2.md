# 0.66.2 Release Incident Recovery Architecture

- **Task**: FIX-214
- **Target**: 0.66.2 PATCH
- **Status**: FIX-218_DESIGN_AMENDMENT_CANDIDATE / AWAITING_INDEPENDENT_DESIGN_REVIEW_R0
- **Date**: 2026-07-18
- **Authority**: original FIX-214 Design R2 and packet R2 approval remain immutable history; this FIX-218 amendment candidate has no authority until independent `REVIEW-FIX-218-DESIGN-R0` is `APPROVED` with zero blockers
- **Requirement inputs**: AUDIT-137 R3 APPROVED; AUDIT-138 R2 APPROVED
- **Immutable incident facts**: AUDIT-136 `BLOCKED_REVIEW_FUSE`; remote `v0.66.1` absent; local `v0.66.1` untrusted; `origin/master=6a78b12`
- **Authorization**: requirement=true; amended-packet=false; implementation=false; rehearsal=false; candidate=false; commit=false; code-review=false; qa=false; tag=false; push=false; release=false

## 1. Context

The 0.66.1 commits reached `origin/master`, but independent post-release review
found six code blockers and seven release blockers. The pushed history is an
incident fact, not a trusted release boundary. Recovery MUST preserve existing
commits and MUST NOT force-push, reset the remote branch, move or publish
`v0.66.1`, rewrite an earlier commit, or convert failed review history into a
pass.

The governing contracts are ADR-010, ADR-011, ADR-012,
`REVIEW-FIX-213-CODE-R0`, `REVIEW-REL-058-R0`, AUDIT-137 R3, and AUDIT-138 R2.
AUDIT-137 defines externally anchored primary-report truth and provisional/full
separation. AUDIT-138 defines the disposable atomic push, refusal, fallback,
cleanup, and RTO contract. Their requirement approval authorizes this design
revision only.

## 2. Goals and non-goals

### Goals

1. Create a non-destructive 0.66.2 compensation path with three narrow,
   serial, independently reviewed slices.
2. Close all thirteen P0 findings with one accountable owner per finding and
   machine proof that cannot be replaced by Coordinator assertion.
3. Make semantic ownership, three-root identity, ledger integrity, candidate
   evidence, rehearsal, and released lineage independently reproducible.
4. Preserve an acyclic ancestry from the incident head through accepted slice
   heads, candidate `C`, transition `T`, and annotated `v0.66.2`.
5. Freeze exact file ownership, versioned interfaces, and compensation-only
   rollback before any implementation packet is created.

### Non-goals

- No runtime activation, migration-validity claim, 0.67.0 feature, historical
  tag backfill, unrelated risk closure, or broad refactor.
- No restoration, movement, or publication of local `v0.66.1`.
- No combined carrier, self-review, Coordinator-as-proof-producer, sequential
  push fallback, provisional-cache reuse, amend, rebase, or subject rewrite.
- No claim that a local candidate check equals a released check against fresh
  remote facts.

## 3. Decision and alternatives

### Decision

Adopt a **0.66.2 PATCH non-destructive serial compensation**. Each slice first
creates a local immutable commit, then Code Review and QA bind their reports to
that exact full SHA; only an accepted subject is pushed and handed to the next
slice. A failed subject remains immutable and receives a new child compensation
commit plus fresh exact-subject review; it is never amended or rebased.

After accepted `S215 -> S216 -> S217(B)`, REL-063 creates local immutable `C`.
The order is exact-C Code Review and QA, approved disposable rehearsal,
Release Review consuming both, manifest-only `T`, annotated tag at `T`, one
atomic branch-plus-tag push, then fresh full remote validation.

### Alternatives

| Alternative | Description | Decision | Reason |
| --- | --- | --- | --- |
| A | Rewrite pushed 0.66.1 commits or move/publish `v0.66.1` | Rejected | Destroys immutable incident lineage and creates tag ambiguity. |
| B | Put semantic, identity, ledger, artifacts, and transition in one carrier | Rejected | Recreates the common failure domain and prevents exact-subject review and independent rollback. |
| C | Three serial compensation slices followed by native `C -> T` | Selected | Preserves history, isolates ownership, and gives every gate an immutable subject. |

PATCH is appropriate because the work repairs release truth and evidence
integrity without adding a supported user capability. An incompatible public
CLI change blocks this design and requires a new SemVer decision.

## 4. Modules, exact scopes, and handoff

### 4.1 Scope algebra

For each task, `M` is the exact existing mutable set, `N` the exact new-file
set, and `R` the exact read-only dependency set. The forbidden repository set
is exactly `F = all repository paths - (M union N union R)`; every ref, tag,
remote, submodule, generated-discovery path, and filesystem target outside the
named release operation is also forbidden. An implementation packet MUST copy
these sets byte-for-byte and may not widen, infer, combine, or replace them.

### 4.2 FIX-215 — semantic historical ownership

Normative responsibilities, exactly three:

1. Repair locator/digest/occurrence and exact-once historical ownership while
   retaining open-vocabulary, provenance-non-authoritative semantics.
2. Keep the canonical Task-Gate model and its E2E materialization identical;
   reject drift rather than weakening the scanner.
3. Produce `loop-semantic-claim-report/v1` while preserving the non-bypassable
   `IDENTITY_ATTESTATION_PENDING` aggregate state.

`M215`:

```text
skills/software-project-governance/core/loop-runtime-claim-allowlist.json
skills/software-project-governance/core/loop-runtime-claim-authority.json
skills/software-project-governance/infra/checks/loop_runtime_claims.py
skills/software-project-governance/infra/tests/test_loop_runtime_claims.py
skills/software-project-governance/core/task-gate-model.md
project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md
```

`N215 = empty`. `R215`:

```text
docs/architecture/ADR-011-loop-runtime-claim-correction.md
docs/architecture/ADR-012-loop-runtime-claim-recovery-split.md
docs/architecture/release-incident-recovery-0.66.2.md
project/CHANGELOG.md
skills/software-project-governance/infra/verify_workflow.py
```

Validation adapters, review aggregation, and performance calibration are not
FIX-215 responsibilities. QA owns the exact `<8.0s` scanner measurement under
DEC-119; a stale `<5s`, missing sample, unexpected skip, or UNKNOWN blocks.

### 4.3 FIX-216 — independent three-root identity

Normative responsibilities, exactly three:

1. Independently enumerate product, plugin, and host bindings and required
   regular files without importing/calling scanner enumeration or accounting.
2. Persist `loop-identity-attestation/v1` for staged index and compare it with
   final candidate `C` using the sole legal index-to-candidate-tree transition.
3. Aggregate semantic and identity reports through the thin adapter, keeping
   N/A, UNKNOWN, stale, or unequal identity non-authorizing.

`M216`:

```text
skills/software-project-governance/infra/checks/loop_runtime_claims.py
skills/software-project-governance/infra/tests/test_loop_runtime_claims.py
skills/software-project-governance/infra/verify_workflow.py
skills/software-project-governance/infra/tests/test_verify_workflow.py
skills/software-project-governance/core/loop-runtime-claim-allowlist.json
skills/software-project-governance/core/loop-runtime-claim-authority.json
skills/software-project-governance/core/manifest.json
```

`N216`:

```text
skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py
skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py
```

`R216`:

```text
docs/architecture/ADR-012-loop-runtime-claim-recovery-split.md
docs/architecture/release-incident-recovery-0.66.2.md
project/CHANGELOG.md
skills/software-project-governance/core/task-gate-model.md
project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md
```

QA, not the scanner or attestor, runs the mandatory performance PoC: one
warm-up plus five scanner-only, attestor-only, and aggregate runs. Numeric
aggregate time/RSS remains `PERFORMANCE_BUDGET_PENDING` until an independent
reviewer records the measured budget; PENDING is non-authorizing.

### 4.4 FIX-217 — native incident ledger repair

Normative responsibilities, exactly three:

1. Make production extraction and the independent golden oracle implement
   `release-ledger.schema.json#v1` with identical deterministic event identity.
2. Preserve 0.66.1 as an incident and add append-only correction/withdrawal
   facts; never recast it as a trusted release.
3. Produce the accepted ledger slice head `S217`, named base `B` for `C`.

`M217`:

```text
skills/software-project-governance/infra/release/ledger.py
skills/software-project-governance/infra/release/model.py
skills/software-project-governance/infra/release/schema_validation.py
skills/software-project-governance/infra/tests/test_release_ledger.py
project/e2e-test-project/.governance/plan-tracker.md
skills/software-project-governance/core/release-ledger.schema.json
skills/software-project-governance/core/releases/0.66.1.json
```

`N217 = empty`. `R217`:

```text
docs/architecture/ADR-010-declarative-release-manifests.md
docs/architecture/release-incident-recovery-0.66.2.md
project/CHANGELOG.md
skills/software-project-governance/infra/verify_workflow.py
skills/software-project-governance/core/releases/0.66.0.json
```

Release aggregation and remote lineage are REL-063 responsibilities. FIX-217
does not create 0.66.2 artifacts, change versions, tag, or query a write remote.
The amended exact scope is therefore `M217/N217/R217 = 7/0/5`. The added path
is an outer-Git-tracked non-UI text projection, not an ignored environment
fixture. Its sole legal S217 delta is the workflow version projection
`0.66.0 -> 0.66.1`; no other byte or field in that file may change. It remains
materialized after the full ledger suite and is committed in the exact S217
tree. There is no prerequisite outer commit, nested-repository commit/ref,
tag, or remote write. REL-063 retains the same M063 member and later changes
that projection from `0.66.1 -> 0.66.2` in C.

### 4.5 REL-063 — candidate, evidence, rehearsal, and transition

Normative responsibilities, exactly three:

1. Generate the exact 0.66.2 release artifacts/projections and local immutable
   candidate `C`, then create manifest-only `T` only after its evidence gate.
2. Validate slice, exact-C, rehearsal, and Release Review truth through the
   owned fail-closed verifier without producing any independent review proof.
3. Execute the approved disposable rehearsal and, after Release Review,
   annotated tag, atomic push, fresh full validation, and observation.

`M063`:

```text
project/CHANGELOG.md
skills/software-project-governance/SKILL.md
project/e2e-test-project/skills/software-project-governance/SKILL.md
skills/software-project-governance/core/manifest.json
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
.codex-plugin/plugin.json
.zcode-plugin/plugin.json
.chrys-plugin/plugin.json
package.json
project/e2e-test-project/.governance/plan-tracker.md
skills/software-project-governance/infra/hooks/pre-commit
skills/software-project-governance/infra/hooks/commit-msg
skills/software-project-governance/infra/hooks/post-commit
skills/software-project-governance/infra/hooks/prepare-commit-msg
```

`N063`:

```text
docs/release/release-checklist-0.66.2.md
docs/release/feature-flags-0.66.2.md
docs/release/rollback-plan-0.66.2.md
skills/software-project-governance/core/releases/0.66.2.json
skills/software-project-governance/infra/release/verify_rel063_evidence.py
skills/software-project-governance/infra/tests/test_verify_rel063_evidence.py
skills/software-project-governance/infra/release/invoke_rel063_rehearsal.ps1
skills/software-project-governance/infra/tests/run_rel063_rehearsal_fixtures.ps1
```

`R063` is exactly the repository paths below. Immutable Git objects and other
runtime facts are not repository paths and are separately bounded as `X063` in
section 4.5.2:

```text
docs/architecture/ADR-010-declarative-release-manifests.md
docs/architecture/ADR-011-loop-runtime-claim-correction.md
docs/architecture/ADR-012-loop-runtime-claim-recovery-split.md
docs/architecture/release-incident-recovery-0.66.2.md
skills/software-project-governance/infra/verify_workflow.py
skills/software-project-governance/infra/resolve_entry.py
skills/software-project-governance/infra/cleanup.py
skills/software-project-governance/infra/checks/__init__.py
skills/software-project-governance/infra/checks/capability_registry.py
skills/software-project-governance/infra/checks/commit.py
skills/software-project-governance/infra/checks/flow_unit_runtime.py
skills/software-project-governance/infra/checks/loop_runtime_claims.py
skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py
skills/software-project-governance/infra/checks/manifest.py
skills/software-project-governance/infra/checks/projection.py
skills/software-project-governance/infra/checks/version.py
skills/software-project-governance/infra/release/__init__.py
skills/software-project-governance/infra/release/context.py
skills/software-project-governance/infra/release/git_facts.py
skills/software-project-governance/infra/release/ledger.py
skills/software-project-governance/infra/release/model.py
skills/software-project-governance/infra/release/projection.py
skills/software-project-governance/infra/release/quality.py
skills/software-project-governance/infra/release/schema_validation.py
skills/software-project-governance/infra/tests/test_verify_workflow.py
skills/software-project-governance/core/capability-registry.json
skills/software-project-governance/core/lifecycle-registry.json
skills/software-project-governance/core/loop-engineering-registry.json
skills/software-project-governance/core/loop-runtime-claim-allowlist.json
skills/software-project-governance/core/loop-runtime-claim-authority.json
skills/software-project-governance/core/release-ledger.schema.json
skills/software-project-governance/core/releases/0.66.0.json
skills/software-project-governance/core/releases/0.66.1.json
skills/software-project-governance/core/version-projections.json
.governance/review-authority/REL-063/authority-input.json
.governance/review-authority/REL-063/orchestration-receipts.json
.governance/review-authority/REL-063/topology-record.json
.governance/primary-review-evidence/REL-063/FIX-215-code.json
.governance/primary-review-evidence/REL-063/FIX-215-qa.json
.governance/primary-review-evidence/REL-063/FIX-216-code.json
.governance/primary-review-evidence/REL-063/FIX-216-qa.json
.governance/primary-review-evidence/REL-063/FIX-217-code.json
.governance/primary-review-evidence/REL-063/FIX-217-qa.json
.governance/primary-review-evidence/REL-063/exact-C-code.json
.governance/primary-review-evidence/REL-063/exact-C-qa.json
.governance/primary-review-evidence/REL-063/release-review.json
.governance/review-evidence/REL-063/FIX-215-code.json
.governance/review-evidence/REL-063/FIX-215-qa.json
.governance/review-evidence/REL-063/FIX-216-code.json
.governance/review-evidence/REL-063/FIX-216-qa.json
.governance/review-evidence/REL-063/FIX-217-code.json
.governance/review-evidence/REL-063/FIX-217-qa.json
.governance/review-evidence/REL-063/exact-C-code.json
.governance/review-evidence/REL-063/exact-C-qa.json
.governance/review-evidence/REL-063/release-review.json
.governance/primary-review-evidence/REL-063/atomic-rehearsal.json
.governance/review-evidence/REL-063/atomic-rehearsal.json
```

#### 4.5.1 Closed command-to-read-set map

For this release only, `P063` is the exact Python loader/module set below:

```text
skills/software-project-governance/infra/verify_workflow.py
skills/software-project-governance/infra/resolve_entry.py
skills/software-project-governance/infra/checks/__init__.py
skills/software-project-governance/infra/checks/capability_registry.py
skills/software-project-governance/infra/checks/commit.py
skills/software-project-governance/infra/checks/flow_unit_runtime.py
skills/software-project-governance/infra/checks/loop_runtime_claims.py
skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py
skills/software-project-governance/infra/checks/manifest.py
skills/software-project-governance/infra/checks/projection.py
skills/software-project-governance/infra/checks/version.py
skills/software-project-governance/infra/release/__init__.py
skills/software-project-governance/infra/release/context.py
skills/software-project-governance/infra/release/git_facts.py
skills/software-project-governance/infra/release/ledger.py
skills/software-project-governance/infra/release/model.py
skills/software-project-governance/infra/release/projection.py
skills/software-project-governance/infra/release/quality.py
skills/software-project-governance/infra/release/schema_validation.py
```

`G063` is the exact additional module set loaded by the non-skipped execution
gate inside `check-release`:

```text
skills/software-project-governance/infra/cleanup.py
skills/software-project-governance/infra/tests/test_verify_workflow.py
```

`D063` is the exact repository-resident schema/control-data set parsed by the
four proof rows:

```text
skills/software-project-governance/core/capability-registry.json
skills/software-project-governance/core/lifecycle-registry.json
skills/software-project-governance/core/loop-engineering-registry.json
skills/software-project-governance/core/loop-runtime-claim-allowlist.json
skills/software-project-governance/core/loop-runtime-claim-authority.json
skills/software-project-governance/core/release-ledger.schema.json
skills/software-project-governance/core/releases/0.66.0.json
skills/software-project-governance/core/releases/0.66.1.json
skills/software-project-governance/core/version-projections.json
```

The command repository read-set means paths opened from the checked-out
repository as executable Python, schema, or control data. It excludes bytes
obtained by immutable Git object ID and facts in `X063`; those are not
working-tree path reads. The four mappings are exact:

| P0 row | Invocation | Exact command repository read-set |
| --- | --- | --- |
| C6 | candidate `check-release` | `P063 union G063 union D063` |
| R3 | candidate `check-release`; released `check-release` | each invocation is `P063 union G063 union D063` |
| R4 | candidate `check-release`; `check-projection-sync --fail-on-issues` | candidate is `P063 union G063 union D063`; projection is `P063 union {skills/software-project-governance/core/version-projections.json}`; row union is `P063 union G063 union D063` |
| R6 | released `check-release` | `P063 union G063 union D063` |

Python standard-library/installed-runtime modules are host runtime, not
repository paths. `P063` closes the unconditional and transitive local imports
of `verify_workflow.py`, including the FIX-216 attestor; `G063` closes the
non-skipped unit-test gate; `D063` closes every live repository schema/control
read. There is no wildcard, directory walk, optional "as needed" member, or
runtime path discovery in these sets. A new import or live control-path read is
`READ_SET_VIOLATION`, not an implicit expansion, and blocks authorization until
a new Design Review approves an explicit R-set revision.

#### 4.5.2 Subject bytes and external runtime facts

`X063` is the closed class of runtime inputs that are not repository path
members: immutable candidate/released Git commits, trees and blobs addressed by
object ID; local Git object/ref observations; authenticated `origin` query
results; platform-signed dispatch/review receipt bytes; host `.governance`
snapshot bytes; clock, process, Python/PowerShell/Git executable facts; and
disposable temporary-filesystem facts. `X063` never grants a mutable path.

All candidate payload inspected by the four commands, including the `M063` and
`N063` subjects and any manifest-declared product content, MUST be obtained from
the frozen candidate or released Git object through the FIX-216 source-envelope
adapter. It MUST NOT be reopened by working-tree path. The adapter provides a
finite object-ID/path/byte tuple inventory; Git object identity, rather than a
glob or directory discovery rule, closes that inventory. A direct live read of
any payload, host path, or generated path outside the command set above is
`READ_SET_VIOLATION`. Repository bytecode/cache output is disabled or redirected
to disposable host storage, so the proof commands do not write repository
paths.

The algebraic proof is therefore:

```text
command_read_set(C6) = P063 union G063 union D063
command_read_set(R3) = P063 union G063 union D063
command_read_set(R4) = P063 union G063 union D063
command_read_set(R6) = P063 union G063 union D063

M063 intersection N063 = empty
M063 intersection R063 = empty
N063 intersection R063 = empty

for each q in {C6, R3, R4, R6}:
  command_read_set(q) subset R063
  command_read_set(q) intersection F = empty
```

Every path in `P063`, `G063`, and `D063` appears literally in the R063 block;
no M063 or N063 path appears there. Because `F` is the complement of
`M063 union N063 union R063`, the subset and zero-intersection conclusions
follow without inferred membership. The Coordinator packet remains copy-only:
it copies the literal M063, N063, and R063 blocks and this command map; it may
not recompute, discover, widen, or normalize any member.

The evidence paths are read-only inputs produced by external Code Reviewer,
QA, Release Reviewer, and platform dispatch authorities. The REL-063 Release
producer may neither create nor alter them. `C` changes exactly `M063 union
N063`; `T` changes exactly the 0.66.2 manifest and no other path.

### 4.6 Lock and ownership handoff

```text
terminal Design Review APPROVED
  -> lock M215+N215 -> local subject -> exact-subject CR/QA -> accepted S215 push
  -> release M215+N215 -> acquire M216+N216 -> local subject -> CR/QA -> S216 push
  -> release M216+N216 -> acquire M217+N217 -> local subject -> CR/QA -> S217(B) push
  -> release M217+N217 -> acquire M063+N063 -> local C
```

An overlapping path changes owner only after the prior accepted head is pushed
and its lock is released. Failed review creates a new immutable child
compensation subject within the same exact set and a fresh report pair; no edge
returns to an earlier subject, so the execution graph has zero cycles.
The added FIX-217 projection path follows the same handoff: it belongs to the
seven-path S217 subject and transfers to its already-declared REL-063 M063 owner
only after accepted S217(B) is pushed and the M217 lock is released.

## 5. Thirteen P0 findings: one-owner proof matrix

Schema aliases in this table are normative: `E1`=`rel063.primary-review-report.v1`
+ `rel063.review-evidence-sidecar.v1`; `E2`=`rel063.evidence-verdict.v1`;
`S1`=`loop-semantic-claim-report/v1`; `I1`=`loop-identity-attestation/v1`;
`L1`=`release-ledger.schema.json#v1`; `H1`=`rel063.atomic-rehearsal-report.v1`.

| ID | Accountable owner | Evidence provider/dependency | Verifier owner and exact path | Command | Required negative fixture |
| --- | --- | --- | --- | --- | --- |
| C1 | FIX-215 | S215 Developer; exact-S215 CR+QA | FIX-215: `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`, S1 | `python -m unittest skills.software-project-governance.infra.tests.test_loop_runtime_claims -v` | locator/digest/occurrence drift, unused/multi-owned history, unexpected skip |
| C2 | REL-063 | six slice reports, exact-C CR/QA, Release Review | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, E1/E2 | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-all-nine` | missing/duplicate report, wrong result/subject/digest, four-record forge |
| C3 | REL-063 | accepted S215/S216/S217 commit objects | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, `rel063.topology-record.v1` | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase pre_c --require-slice-chain S215,S216,S217` | combined path, wrong parent, reused subject, hidden amend/rebase |
| C4 | FIX-216 | S216 Developer; exact-S216 CR+QA | FIX-216: `skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py`, I1 | `python -m unittest skills.software-project-governance.infra.tests.test_loop_runtime_claim_attestation -v` | root alias/reparse, non-regular file, N/A misuse, post-attestation mutation |
| C5 | REL-063 | DEC-119/AUDIT-135 and terminal FIX-215 report | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, E2 | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-fix213-supersession --scanner-limit-seconds 8.0` | stale `<5s`, different `<8s` encoding, missing audit, PENDING/UNKNOWN budget |
| C6 | REL-063 | all accepted slices and candidate artifacts | REL-063: `skills/software-project-governance/infra/verify_workflow.py`, `check-release/v1` | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.2 --require-changelog --lineage-mode candidate` | missing predecessor, projection drift, FAIL/UNKNOWN/BLOCKED |
| R1 | REL-063 | terminal slice CR/QA subjects | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, E2 | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-slice-chain S215,S216,S217 --require-all-nine` | failed/fused/reordered/wrong-subject predecessor |
| R2 | REL-063 | external platform dispatch receipts | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, E1/E2 | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-distinct-role-sets` | self-review, CR=QA, Release Reviewer overlaps any CR/QA |
| R3 | REL-063 | FIX-216 I1 at C and fresh Git/remote facts at T | REL-063: `skills/software-project-governance/infra/verify_workflow.py`, I1 + `check-release/v1` | candidate command above; full command adds `--lineage-mode released --release-commit <T> --lineage-remote origin` | pending/stale attestation, candidate-as-released, remote unavailable |
| R4 | REL-063 | FIX-215 S1, FIX-217 L1, exact-C QA | REL-063: `skills/software-project-governance/infra/verify_workflow.py`, `check-release/v1` | candidate `check-release` plus `check-projection-sync --fail-on-issues` | claim failure, ledger failure, one of 13 projections drifted |
| R5 | FIX-217 | production Git/manifest facts and independent golden oracle | FIX-217: `skills/software-project-governance/infra/tests/test_release_ledger.py`, L1 | `python -m unittest skills.software-project-governance.infra.tests.test_release_ledger.ReleaseLedgerTests.test_production_path_ledger_extraction_matches_golden -v` | integrity mismatch, duplicate event, wrong effective state, production/golden divergence |
| R6 | REL-063 | T object and authenticated origin query | REL-063: `skills/software-project-governance/infra/verify_workflow.py`, `check-release/v1` | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.2 --require-changelog --lineage-mode released --release-commit <T> --lineage-remote origin` | local/remote missing, wrong object, peel not T, multiple transition |
| R7 | REL-063 | QA-produced H1; three release documents | REL-063: `skills/software-project-governance/infra/release/verify_rel063_evidence.py`, H1/E2 | `python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-rehearsal --require-release-review` | RTO>900, W0!=W1, partial ref update, unsupported atomic, review predates rehearsal |

Each row has exactly one accountable owner. A verifier owner maintains code but
does not produce the independent proof it validates. The Coordinator only
dispatches roles and locks; it is neither accountable owner nor proof producer.

## 6. Normative interfaces and vectors

### 6.1 Canonical JSON rule and common failures

All JSON contracts below use strict UTF-8, no BOM, NFC strings, no duplicate
keys, no NaN/Infinity, `additionalProperties=false`, sorted object keys,
compact separators `,` and `:`, and one trailing LF. Digests are lowercase
SHA-256 of those canonical bytes unless the field explicitly uses
`sha256:<64-lowercase-hex>`. Arrays whose schema says `set` are sorted by their
declared key before serialization; other arrays preserve declared order.

Missing required field=`SCHEMA_MISSING`; duplicate key/record=`DUPLICATE`;
wrong JSON type including bool-as-int=`TYPE_DRIFT`; unknown field or version=
`SCHEMA_UNKNOWN`; noncanonical bytes=`CANONICAL_BYTES`; digest mismatch=
`DIGEST_MISMATCH`; wrong phase/state=`PHASE_DRIFT`; unavailable Git/platform/
filesystem/remote fact=`UNKNOWN`. None can be converted to PASS or absence.

### 6.2 Evidence and authority contracts

`rel063.primary-review-report.v1` has exactly these required fields:

| Field | Type and constraint |
| --- | --- |
| `schema_version` | string const `rel063.primary-review-report.v1` |
| `task_id` | nonempty NFC string; exact matrix value |
| `evidence_kind` | enum `code_review`,`qa`,`exact_c_code_review`,`exact_c_qa`,`release_review` |
| `producer_role`,`producer_id` | nonempty NFC strings; role exact for kind, ID bound by external dispatch |
| `result` | CR/RR=`APPROVED` or `APPROVED_WITH_NOTES`; QA=`PASS` |
| `unresolved_blockers` | integer >=0, bool forbidden; required value 0 |
| `subject_sha` | 40 lowercase hex, exact immutable Git commit |
| `generated_at` | UTC seconds `YYYY-MM-DDTHH:MM:SSZ` |
| `release_authorized` | boolean; true only Release Review, false otherwise |

`rel063.review-evidence-sidecar.v1` adds required `report_path` canonical
repo-relative string and `report_sha256` 64 lowercase hex, then repeats all
nine primary fact fields with type- and case-sensitive equality. Primary bytes
are the sole report truth; the sidecar is an index, never an override.

The exact nine artifact IDs are `FIX-215-code`, `FIX-215-qa`, `FIX-216-code`,
`FIX-216-qa`, `FIX-217-code`, `FIX-217-qa`, `exact-C-code`, `exact-C-qa`, and
`release-review`. Their fixed paths are the R063 paths in section 4.5.

The three external authority files have these schemas and all fields required:

| Schema/path | Required fields |
| --- | --- |
| `rel063.evidence-authority.v1` / `authority-input.json` | `schema_version`, `frozen_at:UTC`, `coordinator_id:string`, `developers:{FIX-215,FIX-216,FIX-217}:string`, `release_producer_id:string`, `artifacts:set[9]` of `{artifact_id,task_id,evidence_kind,producer_role,producer_id,receipt_id,subject_symbol,primary_path,sidecar_path}` |
| `rel063.orchestration-receipts.v1` / `orchestration-receipts.json` | `schema_version`, `generated_at:UTC`, `receipts:set[9]` of `{receipt_id,artifact_id,task_id,assigned_role,producer_id,dispatched_at}` |
| `rel063.topology-record.v1` / `topology-record.json` | `schema_version`, `phase` enum `provisional` or `full`, `observed_at:UTC`, `subjects:{S215,S216,S217,C,T}` where each present value is `{sha,created_at,owner,parents:list[string],path_set_sha256}` and provisional `T` is JSON null; `attempts:list` ordered by `(task_id,attempt_no)` with exact rows `{task_id,attempt_no:int>=1,sha,parent_sha,created_at,terminal_result,code_report_sha256:string-or-null,qa_report_sha256:string-or-null}` where terminal result is `ACCEPTED`, `CR_FAILED`, or `QA_FAILED` |

Each pre-C or pre-T authority document has a lowercase SHA-256 pin frozen
before the commit for that phase. A post-T topology record that contains T is
instead pinned by an immutable platform control-plane receipt created after T;
its digest is written only to the released validation output, never back into
T. Production identity comes from platform dispatch and immutable Git object
queries, not workspace JSON; the three files are cross-checks and cannot
refresh their own pins.

For every attempt, `created(commit) < generated(code report) < generated(QA
report)` when QA ran, and a compensation child's creation is later than all
reports for its failed parent. The accepted attempt is the sole row mapped to
S215/S216/S217. Missing attempt, duplicate attempt number, rewritten parent,
report timestamp before subject creation, or an accepted mapping to a failed
attempt is `G070.TIME` or `G060.SLICE` and no-go.

`rel063.evidence-verdict.v1` requires `schema_version`, `phase:pre_c|candidate|full`,
`candidate_sha:string|null`, `transition_sha:string|null`, `artifact_ids:list`,
`authority_roots:{evidence,dispatch,topology}`, `rehearsal_sha256:string|null`,
`released_validation_root:64hex|null`, `verdict:PASS|REJECT|UNKNOWN`,
`gate:string`, `transition_authorized:boolean`, and
`release_authorized:boolean`. `pre_c` validates six slice reports;
`candidate` validates all nine plus rehearsal and may set
`transition_authorized=true` only after Release Review; only `full`, after fresh
remote facts, may set a non-null released-validation root and
`release_authorized=true`.

Positive vector: nine canonical report/sidecar pairs, external dispatch and Git
facts, strict time DAG, rehearsal PASS, and exact phase produce one PASS.
Negative vectors: missing/duplicate/type/unknown field, wrong digest/subject/
role/result/time/path, hardlink/reparse, self-review, four-record producer or
subject forge, provisional T/tag present, remote query unknown, and reused
provisional root each produce their named nonzero gate. Exact command:

```text
python -m unittest skills.software-project-governance.infra.tests.test_verify_rel063_evidence -v
```

### 6.3 Rehearsal report contract

`rel063.atomic-rehearsal-report.v1` is a canonical primary report with required
fields: `schema_version`, `producer_role` const `QA`, `producer_id:string`,
`subject_sha` exact C, `tag_type` const `annotated`, `fixture` const `positive`,
`result` const `PASS`, `raw_exit` const integer 0, `writes:integer>=0`,
`workspace_identity` const `UNCHANGED`, `real_origin_invocations` const 0,
`sequential_fallbacks` const 0, `precondition_sha256:64hex`, `a_master_sha:40hex`,
`a_tag_object_sha:40hex`, `a_tag_peel_sha:40hex`, `abort_absent:boolean true`,
`fallback_sha:40hex`, `rto_seconds:number 0..900`, and `generated_at:UTC`.
Its sidecar is `rel063.rehearsal-evidence-sidecar.v1` with fixed report path,
primary digest, platform receipt ID, mirrored producer/subject/result/time, and
the same canonical rule.

The harness interface is:

```text
pwsh -NoLogo -NoProfile -NonInteractive -File skills/software-project-governance/infra/release/invoke_rel063_rehearsal.ps1 -WorkspaceRoot <absolute-root> -TagType annotated -Fixture positive
pwsh -NoLogo -NoProfile -NonInteractive -File skills/software-project-governance/infra/tests/run_rel063_rehearsal_fixtures.ps1
```

Missing tag type exits 64; unknown/case-drift exits 65; deterministic rejection
exits 2; UNKNOWN exits 3; harness mismatch exits 70. Negative vectors are the
complete AUDIT-138 R2 matrix: head/parent/policy/abort/source errors, native
exit/cwd ambiguity, path escape/reparse/marker failure, partial master/tag/
abort movement, origin alias, fallback failure, W0/W1 drift, RTO breach, and
atomic unsupported; no vector may SKIP.

### 6.4 Scanner, attestor, and aggregate contracts

Input schema IDs remain ADR-012 constants: `loop-root-source/v1`,
`loop-git-repository-tree/v1`, and `loop-semantic-accounting/v1`.
`loop-root-source/v1` requires `schema_version` and exactly three bindings.
Product/plugin Git bindings require `role:product_root|plugin_home`,
`repository_identity:{schema_version:"loop-git-repository-tree/v1",
object_format:"sha1"|"sha256",repository_root_tree_oid:lowercase-oid}`,
`tree_prefix:normalized-string`, `selected_tree_oid:lowercase-oid`, and
`records_digest:64hex`. The host binding requires `role:"host_root"`,
`schema_version:"loop-immutable-workspace-snapshot/v1"`,
`manifest_digest:64hex`, `bytes_digest:64hex`, and sorted
`records:list[{path:string,mode:integer,size:integer,sha256:64hex}]`.
Each role appears exactly once; a default binding, cwd inference, live-file
fallback, absent role, duplicate role, or extra role is invalid.

`loop-semantic-claim-report/v1` requires:

```text
schema_version:string const
scan_mode:product_release|installed_host
semantic_verdict:PASS|FAIL|UNKNOWN|NOT_APPLICABLE
source_envelope_sha256:64hex
scanner_inventory_digest:64hex
accounting_contract:string const loop-semantic-accounting/v1
accounting:{record_count:int,payload_bytes:int,record_digest:64hex,aggregate_digest:64hex}
controls:{policy_sha256:64hex,authority_sha256:64hex}
findings:list[{code:string,root_owner:string,path:string,locator:object|null,detail:string}]
```

`loop-identity-attestation/v1` requires:

```text
schema_version:string const
phase:staged_index|candidate_commit
scan_mode:string
subject:{kind:index|commit,sha:string|null}
bindings:{product_root:object,plugin_home:object,host_root:object}
source_envelope_sha256:64hex
required_paths_digest:64hex
accounting_contract:string const loop-semantic-accounting/v1
accounting:{record_count:int,payload_bytes:int,record_digest:64hex,aggregate_digest:64hex}
identity_verdict:PASS|FAIL|UNKNOWN|NOT_APPLICABLE
created_at:UTC
```

`loop-claim-aggregate/v1` requires both canonical report digests,
role-local binding/record/byte equality, semantic-accounting equality,
`phase:candidate`, and `verdict:PASS` before `authorized=true`. Installed N/A,
PENDING, stale artifact, source-kind drift other than the reviewed index-to-C
transition, missing root, unknown field/version, or a digest-only comparison
is non-authorizing.

Canonicalization uses section 6.1. The scanner and attestor independently
produce the four accounting fields; they may share only schema literals and
golden bytes, not traversal, extraction, serializer, cache, or expected-value
builders. Positive vectors include same-repo prefixes, external plugin repo,
ignored host snapshot, installed N/A, and exact index-to-C equality. Negative
vectors include missing/duplicate binding, alias/reparse, wrong owner/type,
loaded-control mutation, record/byte/count/digest divergence, shared-enumerator
import/call, stale attestation, and every other phase transition.

Exact acceptance interface:

```text
python -m unittest skills.software-project-governance.infra.tests.test_loop_runtime_claims -v
python -m unittest skills.software-project-governance.infra.tests.test_loop_runtime_claim_attestation -v
python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow.FIX200ScopedAttestationRehearsalTests -v
python skills/software-project-governance/infra/verify_workflow.py check-loop-runtime-claims --scan-mode product_release --product-git-repo <repo> --product-git-ref :index --product-prefix <prefix> --plugin-git-repo <repo> --plugin-git-ref <ref> --plugin-prefix <prefix> --host-root <root> --snapshot-dir <dir> --write-attestation <artifact> --require-identity --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-loop-runtime-claims --scan-mode product_release --product-git-repo <repo> --product-git-ref <C> --product-prefix <prefix> --plugin-git-repo <repo> --plugin-git-ref <ref> --plugin-prefix <prefix> --host-root <root> --snapshot-dir <dir> --compare-attestation <artifact> --require-identity --fail-on-issues
```

### 6.5 Ledger contract

`release-ledger.schema.json#v1` requires `schema_version:integer const 1`,
`version:SemVer string`, `lifecycle_state:candidate|released`, and
`provenance:native|historical_backfill`. It also requires
`artifacts:{changelog:string,release_docs:list[string],review_evidence:list[string]}`,
`trust:{candidate_commit:{derivation:"git_commit_adding_path"}}`, `events:list`,
and `effective_state:{lifecycle_state:candidate|released,withdrawn:boolean,
amendments:list[string]}`. A native event requires unique
`id:string`, `type:amendment|withdrawal|candidate_to_released`,
`recorded_at:UTC`, `claims:object`, and `integrity:sha256:<64hex>`.

Events are ordered by `(recorded_at,id)`. Event integrity is SHA-256 of section
6.1 canonical bytes after removing only the event's top-level `integrity`.
Duplicate IDs, unknown fields/type/version, invalid integrity, wrong event
order, inconsistent effective state, multiple native transitions, missing Git
objects, or production/golden disagreement fails closed.

The phase machine is exact: FIX-217 makes 0.66.1 ledger-integrity-valid but
withdrawn/untrusted; 0.66.2 `C` is candidate with remote facts explicitly
pending and `release_authorized=false`; `T` is the only candidate-to-released
event and full remote facts are mandatory before released PASS. Candidate or
full manifests cannot contain their own commit SHA.

For 0.66.2, schema v1's native manifest requires
`recovery_evidence:{schema_version:"rel063.release-evidence-binding.v1",
phase:"candidate"|"full",frozen_at:UTC,subjects:object,reports:object,
authority_roots:object,artifact_blobs:object,provisional_root:64hex,
rehearsal_sha256:64hex|null,full_root:64hex|null}`. Candidate subjects contain
only S215/S216/S217 and candidate rehearsal/review fields are null; full
subjects add C but never T, and rehearsal/full-root fields are non-null. The
candidate manifest cannot name exact-C or later evidence; the full manifest
must name exact-C CR/QA, rehearsal, and Release Review digests. Unknown phase,
illegal nullability, candidate/full field leakage, or self-reference is
`PHASE_DRIFT` and no-go.

`full_root` hashes only facts available before T: C, candidate-manifest blob,
provisional root, exact-C CR/QA, rehearsal, Release Review, and pre-T authority
roots where T is null. It excludes T identity and all local/remote tag facts.
After T, `released_validation_root` is freshly computed from `full_root`, the
external T object/parent/path facts, and local/remote tag object and peel facts;
it exists only in E2 validation evidence and is never stored in T.

Positive vectors cover corrected 0.66.1 incident state, 0.66.2 candidate
no-remote, and 0.66.2 full remote. Negative vectors cover wrong integrity,
duplicate/reordered event, rewritten incident, self-reference, multiple C/T,
wrong T parent/scope, missing peel, and remote unavailable. Exact commands:

```text
python -m unittest skills/software-project-governance.infra.tests.test_release_ledger -v
python -m unittest skills/software-project-governance.infra.tests.test_release_ledger.ReleaseLedgerTests.test_production_path_ledger_extraction_matches_golden -v
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.1 --no-remote
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.2 --no-remote
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.2 --remote origin
```

### 6.6 Validation, aggregation, and calibration boundaries

- Slice modules emit only their versioned reports and domain state. Their
  focused tests validate domain behavior but cannot authorize a later phase.
- REL-063 evidence verifier validates evidence truth; existing
  `verify_workflow.py` aggregates claim, identity, projection, ledger, and
  lineage states; neither produces CR/QA/Release Review evidence.
- Independent QA owns runtime measurements and rehearsal execution. Independent
  reviewers own verdicts. Platform dispatch and immutable Git/remote queries
  own identity facts. The Coordinator owns scheduling/locks only.

## 7. Acyclic execution and ancestry

### 7.1 Slice state machine — B1

For each `FIX-n`, `n in {215,216,217}`, the only transitions are:

```text
PACKET_FROZEN
  -> LOCAL_COMMIT_CREATED(subject_n_attempt_k)
  -> EXACT_SUBJECT_CODE_REVIEW
  -> EXACT_SUBJECT_QA
  -> ACCEPTED -> PUSHED -> HANDOFF
                  |
                  no backward edge

CODE_REVIEW_FAIL or QA_FAIL
  -> LOCAL_COMPENSATION_COMMIT(subject_n_attempt_k+1, parent=attempt_k)
  -> fresh exact-subject Code Review and QA
```

Reports are created only after the local commit object exists. Failed subjects
and reports remain immutable. The new compensation commit is a child, never an
amend/rebase/replacement. Only an accepted terminal subject is named `S215`,
`S216`, or `S217`; pushing that head may transfer its immutable failed ancestor
objects but never labels them accepted. Attempt number and parent edges are
monotonic, so execution-semantic cycle count is zero.

### 7.2 Candidate-to-release state machine — B2

```text
S217(B) PUSHED
  -> local immutable C
  -> exact-C Code Review
  -> exact-C QA
  -> approved disposable AUDIT-138 rehearsal bound to C
  -> Release Review bound to C and consuming rehearsal digest
  -> local T, sole parent C, manifest-only
  -> annotated local v0.66.2 peels T
  -> one atomic push master(T)+v0.66.2
  -> fresh full external/remote validation
  -> observation
```

Release Review cannot start before the canonical rehearsal primary, sidecar,
platform receipt, and digest exist. `T` freezes exact-C CR/QA, rehearsal, and
Release Review evidence. There is one Release Review; no later supplemental
review is inferred.

Required accepted ancestry is linear:

```text
6a78b12 ... -> S215 -> S216 -> S217(B) -> C -> T
```

## 8. Candidate C and transition T

### 8.1 Candidate C

- `C` has sole parent `B` and changes exactly `M063 union N063`.
- Its candidate manifest freezes accepted S215/S216/S217, six slice CR/QA
  primary/sidecar pairs, authority/dispatch/topology roots, projection/artifact
  blobs, and provisional root. It does not contain C's SHA.
- Provisional validation requires complete external queries proving transition
  count zero, `T=null`, and both local/remote `v0.66.2` absent. Missing,
  timeout, parse error, remote unavailable, present tag/T, or serialized T
  identity is UNKNOWN/G080 no-go.

### 8.2 Transition T

- `T` has sole parent `C` and changes only
  `skills/software-project-governance/core/releases/0.66.2.json` from candidate
  to released form.
- Its full manifest freezes C, candidate manifest blob, provisional root,
  exact-C CR/QA pairs, canonical rehearsal pair and receipt/digest, Release
  Review pair, and the pre-T full root defined in section 6.5. It does not
  contain T's SHA or any digest derived from T/tag/remote facts.
- Full validation discards provisional caches and re-queries platform dispatch,
  immutable Git objects, local annotated tag, and authenticated remote tag.
  It emits the external released-validation root; transition count is one and
  both peels equal T. Remote unavailable is UNKNOWN.

The self-reference break follows ADR-010: C/T identities are derived from
immutable Git topology; a manifest freezes only facts available before the
commit whose identity would otherwise be self-referential.

## 9. Atomic rehearsal and real push

The rehearsal occurs only in section 7.2 after exact-C QA. It uses a verified
direct child of canonical system TEMP, a disposable bare remote/clone, fixed
empty hooks, isolated Git config, and W0/W1 workspace tuples. Real origin is a
read-only string and invocation count must be zero.

`TagType=annotated` is mandatory, ordinal, and noninteractive. Scenario A
proves atomic capability and records remote master, tag object, and peel.
Scenario B uses one exact atomic command for pending master, moved policy tag,
and abort tag; its classified refusal must leave all remote identities
byte-identical and abort absent. Unsupported atomic, unrelated exit 1,
native-exit/cwd ambiguity, partial update, unsafe cleanup, failed v0.66.0
fallback, W0/W1 drift, or RTO >900 seconds is no-go; sequential fallback is
forbidden.

Release Review consumes the canonical H1 report and its external receipt.
After T, the real operation recomputes preconditions and performs one atomic
push of `master:T` and annotated `v0.66.2:T`; no abort ref or rehearsal remote
is reused. Fresh full validation follows the push.

## 10. Rollback and reversibility

- Before accepted slice push: add a compensation commit and fresh review; do
  not amend/rebase the failed subject.
- After a slice push, before C: preserve accepted prior slices and repair only
  through the next explicitly owned compensation task.
- After C, before T: quarantine C without a tag; a required repair uses a newer
  PATCH candidate, not C rewrite.
- After T, before push: quarantine local T/tag and do not move either.
- After atomic push: never rewrite/move the boundary; use documented v0.66.0
  operational fallback and create a newer PATCH.
- Mechanical inverse calculation is allowed only in verified disposable trees.
  Real worktree/index intermediates remain truth-preserving and stale
  attestations remain non-authorizing.

## 11. Non-functional requirements

| Dimension | Measure | Architecture control | Satisfaction before R1 | Residual risk |
| --- | --- | --- | --- | --- |
| Reliability | every missing/duplicate/ambiguous/unparseable/remote-unavailable fact non-PASS | typed schemas, phase state machines, fresh full queries | Designed | implementation defects remain untested |
| Security | zero traversal/reparse/hardlink/self-review/subject-substitution path | lexical+resolved checks, external dispatch/Git authority, role-set separation | Designed | platform identity availability |
| Performance | evidence fixtures <10s; rehearsal/fallback <=900s; FIX-215 <8.0s | exact timers; FIX-216 measured PoC before numeric budget | Designed, FIX-216 budget pending by contract | host variance |
| Maintainability | module responsibilities <=3; dependency cycles=0 | exact scopes, serial handoff, versioned reports, no shared enumerator | Designed | higher review cost |
| Compatibility | Windows/Python/PowerShell; existing CLI preserved | ordinal paths/tag type, native-exit wrapper, unsupported atomic no-go | Designed | remote capability unknown until rehearsal |
| Auditability | every verdict binds role, producer, subject, digest, phase | E1/E2/H1/S1/I1/L1 and immutable failed history | Designed | external receipt retention |

## 12. Blue-team challenges

| ID | Attack | Required defense |
| --- | --- | --- |
| BT-214-1 | Reviewer predicts a future SHA or report is edited after commit | Commit locally first; canonical report binds exact existing SHA; failure creates a new child and fresh report. |
| BT-214-2 | Four forged workspace records agree | External platform dispatch and immutable Git facts reject refreshed local pins. |
| BT-214-3 | Provisional already has T/tag or query failure is called absence | Require successful count/exists queries, zero T/tag, and reject UNKNOWN/G080. |
| BT-214-4 | Release Review passes before rollback proof exists | Rehearsal precedes Release Review; T freezes rehearsal and review digests. |
| BT-214-5 | Scanner and attestor share omission | Import/call boundary, independent enumeration/accounting, differential vectors. |
| BT-214-6 | Atomic exit 1 masks partial movement | Freeze preconditions, capture native exit, classify porcelain, compare all refs; any partial change fails. |
| BT-218-1 | A dual-tracked projection is called ignored, synchronized only for a test, then restored so exact S217 still contains 0.66.0 | Treat the path as outer-Git-tracked M217, commit the sole 0.66.0-to-0.66.1 delta in S217, forbid restoration and nested Git/ref actions, and let REL-063 later own the 0.66.2 projection. |

## 13. R0 to R1 blocker resolution map

| R0 blocker | R1 normative closure | Architect disposition |
| --- | --- | --- |
| B1 slice review/commit cycle | Sections 4.6 and 7.1: local immutable commit before exact-subject CR/QA; accepted head pushes; failure creates child compensation commit without amend/rebase | `RESOLVED` |
| B2 Release Review before rehearsal | Sections 7.2, 8.2, 9: exact-C CR/QA -> rehearsal -> Release Review -> T; T freezes rehearsal and review evidence | `RESOLVED` |
| B3 multiple/no owner and assertion proof | Section 5: thirteen rows each have one accountable owner, evidence provider, verifier owner/path/schema/command/negative vector; Coordinator scheduling only | `RESOLVED` |
| B4 candidate rather than exact scope | Sections 4.1-4.6: exact M/N/R/F algebra, finite path sets, closed C/T sets, serial shared-path lock handoff; packet copy-only | `RESOLVED` |
| B5 incomplete interface contract | Sections 6.1-6.5: fixed schema IDs, required field/type rules, canonical bytes/digests, errors, phase machines, commands, positive/negative vectors | `RESOLVED` |
| B6 responsibilities >3 and mixed layers | Sections 4.2-4.5 and 6.6: exactly three normative responsibilities per module; validation, aggregation, reviewer proof, rehearsal, and performance calibration separated | `RESOLVED` |

These are Architect closure claims for independent R1 review, not self-approval.
No new blocker is knowingly introduced; all R0-passed PATCH, alternatives,
SemVer, UNKNOWN/no-go, immutable-0.66.1, C/T, fresh-full-facts, rollback, NFR,
and blue-team conclusions remain in force.

### 13.1 R1 to R2 narrow-resolution map

The immutable R1 review remains `NEEDS_CHANGE/1`; R2 does not rewrite its
finding or claim approval. It changes only the frozen R063 read dependency set
and its coverage proof:

| R1 finding | R2 normative closure | Architect disposition |
| --- | --- | --- |
| B4 C6/R3/R4/R6 verifier path fell in F | Sections 4.5.1-4.5.2: `verify_workflow.py`, every repository-local transitive loader module, the non-skipped gate modules, and the finite schema/control data are literal R063 members; all candidate content is object-ID-bound external input; exact command maps prove subset R063 and zero intersection F | `RESOLVED_PENDING_INDEPENDENT_R2_REVIEW` |

R1-resolved B1, B2, B3, B5, and B6 are unchanged. M063, N063, FIX-215,
FIX-216, and FIX-217 sets; the 13-row ownership matrix; the DAG; schemas;
module responsibilities; authorization flags; and all retained R0/R1 passed
facts are byte-for-byte or semantically unchanged. No R2 authority is inferred
from this Architect disposition.

### 13.2 FIX-218 single-path design amendment

The original FIX-214 Design R2 and packet R2 decisions remain immutable. A
subsequent tests-first FIX-217 run exposed one pre-existing full-command drift:
the outer repository tracks
`project/e2e-test-project/.governance/plan-tracker.md` at workflow version
0.66.0 while the authoritative SKILL projection is 0.66.1. Because the path was
in F217, the Developer stopped before GREEN.

FIX-218 changes only the literal M217 membership and its mechanically dependent
scope/authorization prose: that one path moves from F217 to M217, making
M/N/R `7/0/5`, with only `0.66.0 -> 0.66.1` legal. Every other FIX-217 path,
responsibility, L1 interface, canonical rule, command, negative vector,
review/QA role, withdrawn/untrusted incident rule, performance budget, S217/B
handoff, and release prohibition is unchanged. M063 and its 23-path C count are
unchanged. The amendment does not authorize implementation or any Git/ref/
remote action.

## 14. Design acceptance and authorization boundary

R2 MUST independently verify the R1 B4 closure, the five retained R1-resolved
findings, and the retained R0 PASS facts. An `APPROVED` or
`APPROVED_WITH_NOTES` R2 with `unresolved_blockers=0` authorizes only
Coordinator creation of exact packets copied from section 4. It does not
authorize implementation, rehearsal, candidate/commit creation, tag, push, or
release. Each later authorization remains false until its own preceding gate
and independent evidence pass. R0 and R1 verdicts remain immutable history.

After the FIX-218 amendment candidate, FIX-217 packet consistency and all
implementation/local-commit/Code-Review/QA/push/handoff/transition/release
authorizations are false. Only a new independent
`REVIEW-FIX-218-DESIGN-R0` result of `APPROVED` with
`unresolved_blockers=0` may authorize the Coordinator to freeze the amended
architecture hash and seven-path packet, reacquire exact locks, and resume
FIX-217 GREEN. The reviewer must be distinct from this Architect.

## 15. ADR record

| Field | Decision |
| --- | --- |
| Title | Non-destructive 0.66.2 incident recovery with exact-subject serial slices |
| Date | 2026-07-18 |
| Context | 0.66.1 history is pushed but has no trusted remote tag and fails independent release truth. |
| Decision | Recover with 0.66.2 PATCH; local-commit-before-review slices; exact scope handoff; versioned evidence/identity/ledger contracts; rehearsal before Release Review; manifest-only C/T boundary and annotated tag at T. |
| Alternatives | Reject history rewrite and combined carrier; select serial compensation. |
| Exclusion reasons | Rewrite destroys lineage; combined carrier recreates common-mode failure and unverifiable ownership. |
| Consequences | More immutable attempts and independent reviews, but no SHA prediction, smaller rollback domains, and deterministic phase evidence. |
| Impact | FIX-215/216/217 and REL-063 packets, new evidence/rehearsal verifier modules, release projections, manifests, docs, and independent review artifacts. |
| Reversibility | Revise before accepted packet/commit; after a failed immutable subject add compensation; after C/T use a newer PATCH and never rewrite/move history or tags. |
| Follow-up | Same independent Design Reviewer performs R2 against the immutable R1 blocker; only zero blockers permits exact packet creation, followed by phase-specific Developer/CR/QA/Release gates. |

### 15.1 FIX-218 amendment record

| Field | Decision |
| --- | --- |
| Title | Bind the outer-tracked 0.66.1 E2E plan projection into exact S217 |
| Date | 2026-07-18 |
| Context | The frozen full FIX-217 unittest includes the real projection no-op test, but outer S216 tracks the E2E plan at 0.66.0 while the projection authority is 0.66.1; temporary synchronization cannot prove the immutable S217 object. |
| Decision | Move only the E2E plan-tracker path from F217 to M217, freeze M/N/R at 7/0/5, commit only its 0.66.0-to-0.66.1 version delta in direct-child S217, and retain it until REL-063 changes it to 0.66.2. |
| Alternatives | Separate no-commit synchronization; weaken/skip the full test; defer synchronization to REL-063; amend M217. |
| Exclusion reasons | Temporary synchronization tests bytes not present in S217; skipping weakens the frozen gate; deferral deadlocks the exact FIX-217 command. |
| Consequences | One more outer-tracked text path enters S217 and later overlaps M063 under serial lock handoff; no module responsibility, runtime interface, release scope, or accepted ancestry changes. |
| Impact | FIX-217 M/F sets, exact lock/path assertions, S217 review/QA subject, and mechanically dependent accessibility/scope wording only; REL-063 M063 remains unchanged. |
| Reversibility | Before an accepted S217 push, use a child compensation commit and fresh exact-subject review; never restore the projection merely to make the worktree resemble S216. |
| Follow-up | Independent REVIEW-FIX-218-DESIGN-R0 must approve with zero blockers before any GREEN, local commit, Code Review, QA, push, handoff, transition, or release authorization. |
