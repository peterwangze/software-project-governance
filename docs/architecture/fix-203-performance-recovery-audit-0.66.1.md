# AUDIT-134: FIX-203 Performance Recovery Architecture for 0.66.1

- Date: 2026-07-15
- Status: `READY_FOR_REVIEW_R1`
- Decision state: `PROPOSED_DECISION`
- Product implementation authorized: false
- Release authorized: false
- Required independent review: `REVIEW-AUDIT-134-DESIGN-R1`
- Decision authority: user critical architecture decision after independent review

## R0 Resolution Map

| R0 blocker | R1 resolution | Normative location |
| --- | --- | --- |
| P0-1: Alternative A exposed one raised typed error and could not preserve ordered multi-finding behavior | The candidate boundary now returns either complete artifacts or a `CandidateFailure` with an ordered non-empty findings tuple. The failure matrix freezes Python, JSON, Markdown, serialization, event-projection, and commit mappings; every failure has zero candidate output and no partial event exposure. | Sections 4.3 and 4.4 |
| P0-2: The unqualified commit freeze deadlocked prerequisite persistence | Task commits are separated from the REL-058 release commit. The dependency order is recovery review/QA, FIX-202 canonical-only commit, FIX-199 exact-25 carrier commit, FIX-200 reviewed task commit, then REL-058 review and release commit/tag/push/publication. | Section 9 |

Both corrections are narrow. They do not change the three countable
alternatives, performance estimates, exact product scopes, invariant set,
proposed user decision, or the prohibition on product implementation and
release authorization.

## 1. Context

FIX-203 is terminal `BLOCKED_PERFORMANCE`. This audit does not reopen its
fused review chain, create a Design R3, or authorize more optimization under
FIX-203.

The bounded prototype established all of the following facts:

| Fact | Observed result | Consequence |
| --- | ---: | --- |
| Candidate cold samples | `5.357103 / 6.113805 / 6.661963s` | High variance and one hard-ceiling failure |
| Candidate median | `6.113805s` | `1.363805s` (22.31%) must be recovered to reach `<=4.750s` |
| Same-window improvement | `0.699752s` | Below the required `>=0.750s` |
| Candidate maximum | `6.661963s` | `0.661963s` (9.94%) must be recovered to make that sample `<6s` |
| Semantic oracle | `114277` versus R2 `114244` | `+33` drift; complete-accounting equivalence failed |
| Python parse count | `52/52` | The single-parse premise was already achieved |
| Encoder count | `114277/114277` | The one-encoder premise was already achieved |
| Parent/context counters | Not established | No optimization claim can rely on them |
| Rollback | Both immutable R2 blobs restored | Current product baseline is the R2 state, not the failed prototype |

The stronger internal target `<=4.500s` requires `1.613805s` (26.40%)
recovery from the failed candidate. The formal hard median `<5.000s` requires
`1.113805s` (18.22%). The last independently recorded peak RSS was
`182.551 MiB`, leaving only `73.449 MiB` below the `<256 MiB` budget.

The R2 profile is inclusive and its rows must not be added as if they were
exclusive:

```text
_python_parse_bundle                    1.856s
_semantic_units_from_accounting         0.787s
_account_candidate                      0.570s
_python_units                           0.562s
_serialize_accounting_records           0.543s
_build_python_claim_provenance_index    0.450s
enumerate_candidates + recheck          0.617s
```

The failed prototype disproves the earlier assumption that candidate-local
Python sharing and one-pass accounting alone provide enough headroom. It also
shows that an optimized sidecar can silently change semantic accounting.
The next recovery boundary must therefore change the production dataflow or
execution model materially, and must prove equivalence before broad cleanup.

## 2. Existing Production DAG

The restored R2 scanner has this effective path:

```text
policy/authority validation
  -> enumerate candidates and read complete bytes
  -> historical/notice validation
  -> for each candidate
       -> canonical text
       -> language accounting records
            Python: one AST/token bundle
       -> JSON encode records into AccountingAccumulator
       -> semantic extraction
            Markdown: reconstruct semantic context from accounting dicts
            Python: revisit the AST/provenance graph
            JSON: separate semantic extraction path
  -> binding/history/classification
  -> complete second inventory enumeration and content recheck
  -> verdict
```

This path preserves complete discovery and the final recheck, but it creates
large intermediate dictionaries and revisits information after accounting.
The former FIX-203 prototype tried to share selected Python facts while
retaining two conceptual projections; the `+33` drift demonstrates that this
was not one authoritative event model.

## 3. Evaluation Criteria

Every countable alternative below is evaluated against the same criteria:

1. A bounded prototype must demonstrate candidate median `<=4.750s`; the
   preferred implementation gate is `<=4.500s` so the hard `<5s` gate has at
   least `0.500s` margin.
2. Five fresh-process samples must each be `<6.000s` and the median must be
   `<5.000s`; no warm-up, deletion, cache, skip, truncate, cheap-filter-first,
   or threshold exception is allowed.
3. Peak RSS is `<256 MiB`. A multi-process option measures aggregate process
   tree RSS, not only the parent.
4. Accounting bytes, ordering, per-path hashes, aggregate digest, semantic
   states, classification ledger, historical exact-once behavior, notices,
   findings, and initial/final inventory identities remain exact.
5. Existing typed failures and candidate-atomic zero-output behavior remain.
6. FIX-199 carrier ownership, FIX-202 canonical-only persistence, FIX-200
   separation, and REL-058 release blocking remain unchanged.
7. The production module graph has zero cycles and exactly one scanner path.

The performance ranges below are engineering budgets derived from the
existing inclusive profile. They are not benchmark evidence and cannot
authorize implementation.

## 4. Alternative A: Canonical Event Streaming Transducer

### 4.1 Design

Replace the record-dictionary-then-reproject path with one candidate-local,
language-neutral event stream. Each Markdown, JSON, or Python parser emits a
`CanonicalEvent` exactly once. Accounting encoding and semantic projection
consume that event while its authoritative context is still available.

The production path never reconstructs semantics from encoded accounting
records and never accumulates all record dictionaries. It commits one compact
`CandidateArtifacts` object only after parsing, encoding, and semantic
projection all succeed.

This is materially different from the failed prototype:

- it covers all three languages, not selected Python ancestry facts;
- one canonical event owns accounting and semantic context, rather than an
  accounting record plus a parallel sidecar;
- the production accumulator receives encoded candidate bytes and summaries,
  not record dictionaries that it must encode and recount;
- the legacy R2 path exists only as a test oracle, never as a second
  production path.

### 4.2 Exact Product Scope

If selected, the new recovery task is restricted to exactly:

1. `skills/software-project-governance/infra/checks/loop_runtime_claims.py`
2. `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`

This scope does not change FIX-202, FIX-200, any manifest, version file,
release ledger, tag, or release asset. Because both files are untracked R2
FIX-199 candidate files, the recovery task still has no standalone commit;
the reviewed delta is carried by the final FIX-199 exact-25-path commit.

### 4.3 Proposed APIs

```python
@dataclass(frozen=True)
class CanonicalEvent:
    kind: str
    locator: AccountingLocator
    normalized_payload: str
    context: tuple[AccountingContext, ...]
    semantic_seed: SemanticSeed | None

@dataclass(frozen=True)
class CandidateArtifacts:
    accounting_bytes: bytes
    accounting_unit_count: int
    accounting_payload_bytes: int
    accounting_sha256: str
    semantic_units: tuple[SemanticUnit, ...]

@dataclass(frozen=True)
class CandidateFailure:
    findings: tuple[Finding, ...]  # Ordered and non-empty.

CandidateBuildResult = CandidateArtifacts | CandidateFailure

def build_candidate_artifacts(candidate: Candidate) -> CandidateBuildResult:
    """Return complete artifacts or one atomic ordered failure envelope."""

def commit_candidate_artifacts(
    accumulator: ScanAccumulator,
    candidate: Candidate,
    artifacts: CandidateArtifacts,
) -> CandidateFailure | None:
    """Commit atomically, returning an ordered failure envelope after rollback."""
```

`AccountingLocator`, `AccountingContext`, and `SemanticSeed` are immutable
typed tuples or frozen dataclasses. They cannot contain back-references to the
accumulator, classifier, or scanner coordinator.

`CandidateFailure.findings` must contain at least one finding and preserves
the exact order in which the current scanner exposes findings. A known
candidate-local failure is returned, not raised past this boundary. A failure
envelope contains no `CanonicalEvent`, accounting bytes, hashes, counters, or
semantic units. Compatibility wrappers may project this result into their
legacy tuple shapes, but they delegate inward to this single builder and may
not parse, encode, project, or commit a second time.

The canonical JSON encoder is invoked exactly once per event. Its line bytes
are appended to candidate-local bytes, counted once, and hashed once. A
semantic unit is projected from the same event before the event is released.
Python creates one parse/token bundle per candidate; JSON performs one
duplicate-key-aware parse/walk; Markdown performs one boundary-aware walk.

### 4.4 Exact Candidate Failure Envelope

The following mapping is normative for Alternative A. A tuple with two codes
is produced from one underlying parser exception; it does not authorize a
second parse or walk.

| Failure source | Ordered `CandidateFailure.findings` codes | Parse/walk count | Required atomic result |
| --- | --- | ---: | --- |
| Python `SyntaxError` or `tokenize.TokenError` | (`ACCOUNTING_PYTHON_PARSE_ERROR`, `PARSE_ERROR`) | Exactly one Python parse attempt | Both findings derive from the same exception; no accounting bytes, semantic units, accumulator mutation, parsed count, or partial events |
| JSON decoder failure, including invalid syntax/token or an unpaired surrogate | (`ACCOUNTING_JSON_PARSE_ERROR`, `PARSE_ERROR`) | Exactly one duplicate-key-aware JSON parse/walk | Both findings derive from the same exception; zero candidate output |
| JSON duplicate key | (`ACCOUNTING_JSON_DUPLICATE_KEY`,) | Exactly one duplicate-key-aware JSON parse/walk | Zero candidate output; no semantic projection from a partially built object |
| Markdown unterminated fence/comment, duplicate table header, ragged row, or other ambiguous boundary | (`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY`,) | Exactly one boundary-aware Markdown walk | Zero candidate output; the partially emitted local event sequence is discarded |
| Canonical decode failure | (`DECODE_ERROR`,) | No language parse after decode fails | Zero candidate output |
| Snapshot digest mismatch before language analysis | (`CANDIDATE_SNAPSHOT_MISMATCH`,) | No language parse after mismatch | Zero candidate output |
| Unsupported language/event kind, malformed locator/context, or accounting-event contract violation | (`ACCOUNTING_CONTRACT_MISMATCH`,) | No retry | Zero candidate output; no malformed event is exposed |
| Canonical JSON encoding, UTF-8 encoding, payload-byte counting, line hashing, or candidate-byte assembly failure | (`ACCOUNTING_SERIALIZATION_ERROR`,) | No re-encode retry | Zero candidate output; the entire candidate-local byte buffer is discarded |
| Semantic projection from an otherwise valid canonical event fails | (`PARSE_ERROR`,) | No parser or event-builder retry | Zero candidate output; locally encoded bytes and events are discarded |
| Accumulator prevalidation or atomic commit fails | (`ACCOUNTING_SERIALIZATION_ERROR`,) | No rebuild/reparse retry | Restore the accumulator, semantic-unit collection, and parsed count to their exact pre-candidate state; expose no partial candidate state |

Commit is a transaction across the path summary, aggregate digest state,
unit/payload counters, semantic-unit append, and parsed-candidate count. The
implementation must validate all fallible fields before mutation and retain a
pre-candidate checkpoint sufficient to restore every surface if mutation
still fails. Only a successful commit makes candidate accounting bytes,
semantic units, or the parsed count observable. Every failure path therefore
has zero candidate accounting bytes, zero semantic units, zero accumulator
delta, zero parsed-count delta, and zero partial events.

### 4.5 Acyclic DAG

```text
ScannerCoordinator
  -> SnapshotEnumerator
  -> CandidateArtifactBuilder
       -> LanguageEventBuilder
       -> AccountingProjector
       -> SemanticProjector
  -> ScanAccumulator
  -> Binder/Classifier
  -> FinalInventoryVerifier
```

Topological order is exactly the order shown. Projectors depend only on an
event contract. The accumulator never calls a parser or projector, and no
parser calls the coordinator. Module cycles: `0`.

### 4.6 Quantitative Feasibility

The proposed disjoint savings budget is:

| Cost removed or reduced | Budgeted net recovery |
| --- | ---: |
| Record dictionaries, repeated context objects, and payload recount | `0.35-0.50s` |
| Post-accounting Markdown semantic replay | `0.55-0.70s` |
| Gather/join/encode/hash handoffs after event production | `0.35-0.45s` |
| Duplicate JSON traversal and other cross-language handoffs | `0.10-0.20s` |
| Total design budget | `1.35-1.85s` |

The resulting estimate is `4.264-4.764s` from the failed `6.113805s`
candidate. The low end is not sufficient. Therefore selection of this design
authorizes only a bounded prototype, and that prototype must demonstrate at
least `1.613805s` recovery and an absolute median `<=4.500s` before any broad
cleanup. A `4.500s` candidate leaves `0.500s` to the hard median and `1.500s`
to the per-sample ceiling.

Removing the 114k-record dictionary graph is expected to reduce, rather than
increase, RSS. The prototype budget is `128-165 MiB`; the only authoritative
result remains measured peak RSS `<256 MiB`.

### 4.7 Risks and Why It Is Recommended

Primary risk is semantic drift during event projection, as already observed
with `+33` units. This is controlled by lockstep reference tests: the restored
R2 implementation generates expected artifacts in an isolated baseline tree,
and the candidate must match every unchanged path exactly before timing is
considered.

This is the proposed recommendation because it has the smallest exact scope,
keeps one process and one production path, can reduce both time and memory,
does not add a runtime dependency, and remains compatible with the FIX-199
carrier. Recommendation is conditional, not an implementation authorization.

## 5. Alternative B: Deterministic Two-Lane Process Pipeline

### 5.1 Design and Scope

Use one parent and one spawned worker. The worker handles Python
parse/provenance/artifact construction while the parent handles Markdown and
JSON. Results are returned candidate-by-candidate and committed by the parent
in original inventory order. The parent performs binding, classification,
history, and final inventory recheck.

Exact product scope remains the same two scanner/test files as Alternative A.
The worker protocol, process-tree RSS sampling, deterministic ordinal merge,
worker crash mapping, and Windows spawn tests all live in those files. There
is no persistent worker, daemon, cross-scan cache, or pre-timed warm-up.

Proposed boundary:

```python
def build_python_artifacts_in_worker(
    candidates: tuple[SerializedCandidate, ...],
) -> Iterator[WorkerArtifactEnvelope]: ...

def merge_worker_artifacts(
    inventory: CandidateInventory,
    local: Iterator[CandidateArtifacts],
    remote: Iterator[WorkerArtifactEnvelope],
) -> Iterator[CandidateArtifacts]: ...
```

The worker receives immutable candidate bytes and returns encoded accounting
bytes plus semantic units. It cannot enumerate paths, load policy, classify,
or commit results. A worker crash or missing ordinal produces one typed batch
failure and zero final candidate output.

### 5.2 Quantitative Feasibility

The largest parallelizable observed bucket is Python parsing and semantic
analysis (`1.856s` plus `0.562s`, with the `0.450s` provenance row treated as
inclusive). A 60-75% overlap yields `1.45-1.81s`; Windows spawn, IPC, merge,
and serialization are budgeted at `0.25-0.45s`. Expected net recovery is only
`1.00-1.56s`, giving an estimated median of `4.55-5.11s`.

Memory is also marginal. Adding an estimated `40-75 MiB` worker to the last
`182.551 MiB` baseline gives `222.551-257.551 MiB`; the upper range violates
the budget. Aggregate process-tree measurement is mandatory.

### 5.3 Why It Is Not Recommended

The favorable end can pass, but the range does not provide reliable headroom
for `<=4.750s`, Windows variance, or RSS. IPC also creates a new typed-failure
surface and makes exact atomic rollback harder. Keep this only as a
conditional fallback if a fresh isolated prototype proves candidate median
`<=4.500s`, every sample `<6s`, aggregate RSS `<256 MiB`, and zero identity
drift without incorporating Alternative A's event rewrite.

## 6. Alternative C: Native Canonical Event Helper

### 6.1 Design and Exact Scope

Move candidate event extraction and canonical record encoding into a small
Rust helper. Python retains policy, authority, classification, history, final
recheck, and verdict ownership. The helper accepts length-delimited candidate
bytes on stdin and returns length-delimited candidate artifacts in inventory
order. No filesystem path is accepted by the helper.

Minimum exact scope for this alternative is:

1. `skills/software-project-governance/infra/checks/loop_runtime_claims.py`
2. `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`
3. `skills/software-project-governance/infra/native/loop_claims/Cargo.toml`
4. `skills/software-project-governance/infra/native/loop_claims/Cargo.lock`
5. `skills/software-project-governance/infra/native/loop_claims/src/main.rs`
6. `skills/software-project-governance/core/manifest.json`
7. `.github/workflows/ci.yml`

Any prebuilt binary or additional packaging path would require another exact
scope decision; it is not implicitly authorized by this list.

### 6.2 Quantitative Feasibility

Removing Python AST/object traversal, record dictionaries, and JSON encoding
from the timed path could recover an estimated `1.8-2.8s`, giving
`3.31-4.31s`. That is the largest headroom of the reviewed alternatives and
is sufficient for the target if measured. Expected combined RSS is
`110-190 MiB`, but subprocess-tree RSS remains authoritative.

### 6.3 Why It Is Not Recommended for 0.66.1

This changes the plugin's build, platform, packaging, security, and release
model. It introduces compiler/toolchain availability, binary provenance,
cross-platform equivalence, supply-chain review, and fallback semantics. It
also expands the FIX-199 carrier and 0.66.1 containment scope. Those are user
critical decisions and are disproportionate to a patch hotfix. This option is
technically credible but should be considered only as a separately planned
minor-version architecture if the pure-Python transducer cannot pass.

## 7. Non-Counted Alternative D: Continue R2 Micro-Optimization

Additional parent-map caching, payload counting, serializer batching, or
inventory I/O tuning remains in the same optimization family as FIX-203. The
prototype already recovered only `0.699752s`, left a `1.363805s` absolute
gap, exceeded the sample ceiling, and changed semantic units by `+33`.

The remaining isolated enumeration/recheck row is only `0.617s`, and it is a
mandatory complete identity check. Even an impossible 100% removal would not
close the candidate gap. This is not a materially different recovery
architecture, is quantitatively insufficient, and is prohibited as further
optimization under terminal FIX-203.

## 8. Invariant Matrix

| Invariant | Alternative A | Alternative B | Alternative C |
| --- | --- | --- | --- |
| Exhaustive candidates and bytes | Parent owns unchanged enumerator | Parent owns unchanged enumerator | Python parent owns unchanged enumerator |
| Complete accounting | Every event is encoded; zero filtering | Every local/remote event is encoded | Helper protocol requires every event and count reconciliation |
| Exact bytes/order/digest | Candidate bytes committed in inventory order | Parent ordinal merge is authoritative | Protocol includes ordinal and canonical bytes; Python verifies hashes |
| Semantic equivalence | Same event projects accounting and semantics | Existing per-language projection in isolated lanes | Rust/Python golden and real-root differential oracle |
| Python parse count | Exactly one per Python candidate | Exactly one in worker | Exactly one native parse per Python candidate |
| JSON parse count | Exactly one per JSON candidate | Exactly one in parent | Exactly one native parse per JSON candidate |
| Encoder count | Exactly one per accounting event | Exactly one in owning lane | Exactly one native encode per event |
| Candidate atomicity | Commit only complete `CandidateArtifacts`; every failure restores zero candidate delta | No commit until ordered envelope is complete | Reject partial/truncated helper frame |
| Typed failures | Section 4.4 ordered `CandidateFailure` mapping is normative | Adds typed worker startup/crash/protocol failures | Adds typed helper missing/version/protocol failures |
| Historical exact-once | Unchanged post-artifact stage | Unchanged parent stage | Unchanged Python parent stage |
| Identity and final recheck | Unchanged, complete second enumeration | Unchanged parent recheck | Unchanged Python parent recheck |
| Skip/truncate/cache | All zero; no cache | All zero; no persistent worker/cache | All zero; no result cache |
| RSS authority | Current process peak | Aggregate parent+worker tree | Aggregate Python+helper tree |

No alternative may map a new operational failure to PASS. New worker/helper
failures are blocking typed findings and produce no release authorization.

## 9. FIX-199, FIX-202, FIX-200, and Release Boundaries

The following order is strict and contains no commit dependency cycle:

1. `REVIEW-AUDIT-134-DESIGN-R1` must close with zero blockers, after which the
   user may make the critical architecture selection. A selected architecture
   creates a new P0 recovery task with a fresh Design Review R0; it is not
   FIX-203 R3 and does not change the terminal FIX-203 record.
2. The selected recovery task completes its own Design Review, bounded
   prototype, Code Review, and QA. Alternatives A and B still create no
   standalone recovery commit because their two-file delta belongs to the
   FIX-199 carrier. Alternative C still requires a separate user scope,
   dependency, version, and carrier decision before any file is created.
3. After recovery Code Review and QA pass, run `QA-FIX-202-R1`. If it passes,
   create the prerequisite FIX-202 durable commit containing only the tracked
   canonical Task-Gate file. The ignored e2e copy remains local hash,
   no-index, and real-root proof and is never force-added or represented as a
   pushed artifact.
4. Resume FIX-199 Code Review and QA R1 against the exact 25-path carrier. If
   both pass, create the FIX-199 exact-25-path carrier commit; that commit is
   the first durable persistence of an approved Alternative A/B recovery
   delta.
5. Only after the FIX-199 carrier exists may the separate FIX-200 task run its
   fresh Design, implementation, Code Review, and QA chain. If those pass,
   create a distinct FIX-200 task commit. No performance task may implement
   three-root authority, root reparse checks, installed-state authority, or
   final release-candidate attestation.
6. Only after the recovery, FIX-202, FIX-199, and FIX-200 chains and their
   prerequisite task commits are complete may REL-058 enter independent
   Release Review. A passing review then permits, in order, the version and
   release-manifest mutation, the REL-058 release commit, release-gate
   verification, tag creation, commit/tag push, publication, and eligible risk
   closure.

Prerequisite FIX-202, FIX-199, and FIX-200 commits are therefore permitted
only after their stated independent review and QA gates pass; they are not
REL-058 release commits. Until step 6 passes, the version bump, release
manifest mutation, REL-058 release commit, tag, release push/publication, and
risk closure remain frozen. This distinction removes the former deadlock
without authorizing any currently blocked commit, implementation, or release.

## 10. Rollback and Migration

Before a carrier commit, every prototype starts from the immutable R2 blobs:

| Path | Git blob | SHA-256 |
| --- | --- | --- |
| `loop_runtime_claims.py` | `3ab3d3adf4e154d741ebff9bb8f1b8789fd31c1c` | `B7CBAFAA60E265D012326AA176779B79B559DF14EFE72B08E229DAC04BEC0A56` |
| `test_loop_runtime_claims.py` | `bcd20d7844d1eacbdc38a43eab3490293d1dceb7` | `1BA300132E4B5AB02C6563CC35356A821C53E2C2A355AE6C697CF7A4B1408586` |

Any semantic, accounting, identity, typed-failure, performance, sample-ceiling,
or RSS failure restores both blobs byte-for-byte, verifies their hashes,
runs the 37-test minimum correctness suite and full scanner suite, records a
terminal result for the new recovery task, and prohibits unreviewed follow-on
optimization.

For Alternative C, rollback additionally removes only the newly introduced
native directory and restores `core/manifest.json` and `.github/workflows/ci.yml`
from their pre-task blobs. No binary may remain installed after rollback.

After the FIX-199 carrier exists, rollback is a new compensating FIX-199
commit preserving all reviewed truth surfaces. A standalone FIX-203 revert,
partial fast path, threshold flag, or mechanical reset is not valid.

There is no user data migration for Alternatives A or B. Alternative C has a
distribution migration and therefore cannot be treated as a patch-internal
implementation detail.

## 11. Future Benchmark Protocol

The selected task must add one reusable harness in the allowed test scope.
The proposed invocation is:

```powershell
python -X utf8 skills/software-project-governance/infra/tests/test_loop_runtime_claims.py `
  --audit134-perf-batch `
  --baseline-scanner-blob 3ab3d3adf4e154d741ebff9bb8f1b8789fd31c1c `
  --baseline-tests-blob bcd20d7844d1eacbdc38a43eab3490293d1dceb7 `
  --pairs 5 `
  --candidate-median-max-seconds 4.500 `
  --hard-median-max-exclusive-seconds 5.000 `
  --sample-max-exclusive-seconds 6.000 `
  --paired-improvement-min-seconds 1.500 `
  --process-tree-rss-max-mib 256 `
  --max-invalid-retries 2
```

The switch does not exist yet; it is an interface requirement for the future
task, not a command claimed as executed by this audit.

Protocol requirements:

1. Create isolated before/after trees from one workspace snapshot. The before
   tree overlays both R2 blobs; the after tree overlays only the reviewed
   candidate. Never mutate the real worktree during a sample.
2. Run five baseline/candidate pairs in a balanced alternating order. Every
   child is fresh, serial, worker-free except when Alternative B or C is the
   architecture under test. No warm-up is allowed.
3. Time only `scan_loop_runtime_claims(context)`. Record disjoint stage timers
   for validation, enumeration, artifact building by language, classification,
   and final recheck. Do not sum inclusive profiler rows.
4. Record Python/JSON parse counts, canonical event counts, encoder calls,
   context constructions, parent edges, candidate commits, and retry reason.
5. Before and after each child, enforce the existing CPU, load, memory, AC
   power, power-plan, logical-CPU, exclusive-lock, and competing-batch
   sentinels. A sentinel failure invalidates the whole batch; a valid slow
   batch is not retried.
6. Measure peak process-tree RSS. For a single-process implementation this is
   equivalent to the scanner process peak.
7. All five candidate identity tuples must match. Fixed corpus is byte exact;
   every unchanged real-root path is exact; only the two reviewed self-scan
   paths may have an explained delta. Initial/final inventory equality,
   complete candidate accounting, zero skip/truncate, typed failures,
   history, notices, and ordered findings remain mandatory.
8. The bounded prototype stops unless candidate median is `<=4.500s`, paired
   median improvement is `>=1.500s`, every candidate sample is `<6s`, process
   tree RSS is `<256 MiB`, and every oracle passes. These are stronger than,
   and do not relax, the formal `<=4.750s` feasibility and `<5s` hard gates.
9. Independent QA repeats the complete valid batch; Developer timings alone
   cannot close the performance task.

## 12. Blue-Team Challenges

| ID | Challenge | Required mitigation | Residual risk |
| --- | --- | --- | --- |
| BT-134-01 | What if the canonical event model repeats the prototype's `+33` drift while producing faster timings? | Oracle evaluation precedes timing acceptance; fixed corpus and every unchanged real-root path must be exact, and candidate commit is atomic. | Low after independent differential QA |
| BT-134-02 | What if the `1.35-1.85s` budget double-counts inclusive profiler rows? | Future harness records disjoint exclusive stage timers and requires absolute `<=4.500s`; estimates never authorize implementation. | Medium until prototype evidence exists |
| BT-134-03 | What if the median passes but Windows variance still exceeds `<6s`? | Keep all five samples, require every sample `<6s`, use same sentinel policy, and target `<=4.500s` for margin. | Medium; environment noise can still block |
| BT-134-04 | What if a process/native option appears fast by measuring only parent RSS or excluding startup? | Measure aggregate process-tree RSS and include worker/helper startup and teardown inside the scan timer. | Low if harness is independently reviewed |
| BT-134-05 | What if a new recovery task is used to bypass the FIX-203 fuse or smuggle FIX-200/release work? | New task has a fresh review chain, exact path allowlist, immutable FIX-203 history, and explicit release/authority exclusions. | Low with Coordinator lock and scope checks |
| BT-134-06 | What if self-scanning makes exact before/after aggregate equality impossible? | Use the established changed-path-aware oracle: exact unchanged paths, exactly two reviewed self-scan deltas, and stable post-change identity tuples. | Low |

These challenges are the Architect's adversarial self-check. They do not
replace the independent Bar Raiser review, which remains pending.

## 13. Proposed Decision (Not Yet Authorized)

Propose Alternative A, the single-process canonical event streaming
transducer, for a new bounded recovery task. The selection should authorize
only a prototype against the stronger benchmark stop, not broad
implementation, commit, or release.

Decision rationale:

- it preserves the two-file scope and FIX-199 carrier;
- it attacks the 114k-record object/reprojection path across all languages;
- it removes, rather than adds, memory pressure;
- it keeps deterministic single-process execution and one production DAG;
- it requires exact R2 differential proof before performance is considered;
- its expected range can close the `1.613805s` target gap, but the low end is
  honestly insufficient and therefore fail-closed behind a prototype.

Alternative B is a conditional fallback with marginal RSS and Windows
headroom. Alternative C has the strongest raw headroom but is rejected for
0.66.1 because it materially expands build and release architecture.
Alternative D is not a new architecture and is quantitatively insufficient.

## 14. ADR Record Fields

The following is a proposed decision-log entry for the Coordinator to write
only after independent review and the user's critical decision:

| ADR field | Proposed value |
| --- | --- |
| Title | `0.66.1 scanner recovery via canonical event streaming transducer` |
| Date | `2026-07-15` |
| Background | FIX-203 ended `BLOCKED_PERFORMANCE`: median `6.113805s`, improvement `0.699752s`, max `6.661963s`, semantic drift `+33`; R2 blobs restored. |
| Decision | Create a new recovery task for Alternative A, beginning with a fail-closed bounded prototype; do not reopen FIX-203 R3. |
| Alternatives | B: deterministic two-lane process pipeline; C: native canonical event helper; D: continued R2 micro-tuning. |
| Exclusion reasons | B has marginal process-tree RSS/Windows headroom; C expands build/release scope; D is insufficient and prohibited under FIX-203. |
| Impact scope | Two scanner/test files only; no FIX-202, FIX-200, version, release, tag, risk, or dependency mutation. |
| Consequences | One authoritative event DAG and stronger differential/benchmark harness; implementation remains blocked until prototype and fresh reviews pass. |
| Reversibility | High before carrier: restore immutable R2 blobs. After carrier: compensating FIX-199 commit only. |
| Follow-up actions | Independent Design Review R1; user architecture selection; new task packet; bounded prototype; Code Review; QA; then resume FIX-202/FIX-199/FIX-200/REL-058 in the strict Section 9 order. |

ADR field completeness: `100%`. Module cycles in the proposed DAG: `0`.
Independent Bar Raiser history: R0 `NEEDS_CHANGE` with two blockers; R1 is
`PENDING REVIEW-AUDIT-134-DESIGN-R1`.

## 15. Authorization Boundary

This report is architecture evidence only. It does not:

- modify product or governance state;
- reopen FIX-203 or permit Design R3;
- select the final architecture on the user's behalf;
- create a recovery implementation task;
- relax any performance, accounting, semantic, identity, typed-failure, RSS,
  or release gate;
- authorize FIX-199, FIX-202, FIX-200, REL-058, versioning, commit, tag, push,
  publication, or risk closure.

The next valid action is an independent `REVIEW-AUDIT-134-DESIGN-R1`. Only a
review with `unresolved_blockers=0` may be escalated for the user's single
critical architecture decision.
