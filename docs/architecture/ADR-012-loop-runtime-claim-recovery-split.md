# ADR-012: Loop Runtime Claim Recovery Split

- Status: PROPOSED / FIX-201-ARCH-R0 / READY_FOR_REVIEW-FIX-201-DESIGN-R0
- Date: 2026-07-14
- Tasks: FIX-201 (design recovery), FIX-199, FIX-200
- Parent task: FIX-197
- Authority: DEC-107, DEC-108, EVD-716, EVD-717, EVD-725, EVD-726, ADR-011, REVIEW-FIX-199-DESIGN-R2
- Review authority required: independent `REVIEW-FIX-201-DESIGN-R0`, or the latest terminal round in that new FIX-201 chain; this ADR does not self-approve
- Reversibility: partition mechanics are reversible before each commit; truth correction and fail-closed release blocking are not reversible to known-false wording or a healthy release result

## Context

FIX-197 produced a frozen, uncommitted candidate that corrects active Loop
runtime wording and introduces a semantic claim scanner. Its third independent
implementation review cycle reached the review fuse:

- Code Review R2: `NEEDS_CHANGE`, five blockers;
- Design implementation Review R2: `BLOCKED`, four blockers;
- QA R2: `FAIL`, one P0 blocker.

The three reviews agree that a finite capability taxonomy and broad provenance
exemptions still allow unsupported affirmative Loop claims to pass. Design and
Code Review additionally found that the actually loaded `plugin_home` controls
are outside the inventory authority, required-file and root identity are not
closed, installed `NOT_APPLICABLE` is reported as healthy, and the release
path does not compare an independently computed inventory with the final
candidate.

DEC-107 therefore freezes the FIX-197 dirty candidate and replaces further
review of that combined task with two serial recovery tasks:

1. FIX-199 closes open-vocabulary semantic ownership, makes provenance
   non-authoritative, and enforces exact-once historical ownership.
2. FIX-200, only after FIX-199 is reviewed and committed, closes three-root
   authority inventory, canonical root and required-file identity, installed
   N/A semantics, independent inventory/accounting, and final release
   candidate equality.

The repository currently contains 21 modified tracked product files and four
untracked product files from the frozen candidate. Seven files cross both
failure domains. A file-only parallel split would either lose candidate work,
commit known fail-open release behavior, or let two Developers edit the same
scanner and tests concurrently.

The original ADR-012 Design Review chain then reached its own third-round
fuse. `REVIEW-FIX-199-DESIGN-R2` ended `BLOCKED` with four terminal blockers:
the FIX-199 packet still generated an ADR/started stale Design R0, omitted the
`verify_workflow.py` pending-blocker adapter from allowed scope, contradicted
itself on staged-index-to-candidate-tree binding kinds, and permitted a
real-worktree mechanical revert. DEC-108 creates FIX-201 as a design-only
recovery task for exactly those four findings. This revision starts the new
`REVIEW-FIX-201-DESIGN-R0` chain; it is not R3 of the fused review and does not
authorize a Developer.

## Goals

- Produce two independently reviewable serial commits with separate rollback
  domains; FIX-199 rollback is compensating and truth-preserving rather than a
  wholesale revert.
- Preserve all frozen candidate bytes outside the repository before
  repartitioning; no `reset`, checkout, or stash-based recovery is required.
- Make unknown Loop capability vocabulary fail closed without using a finite
  noun allowlist as the claim-potential boundary.
- Ensure provenance supplies evidence about context but never grants policy
  authority by itself.
- Require every reviewed historical claim entry to own exactly one extracted
  semantic unit.
- Include the policy and authority bytes actually loaded from `plugin_home` in
  scanner inventory, independent inventory, final recheck, and release
  candidate comparison.
- Keep release authorization blocked between the FIX-199 and FIX-200 commits.
- Make the FIX-201 terminal Design result, complete FIX-199 product scope, and
  compensating-only rollback contract mechanically consumable by the FIX-199
  execution packet without further architecture production.
- Preserve ADR-011's exhaustive semantic-first, zero-skip, zero-truncate, and
  fail-closed contracts.

## Non-Goals

- No Loop runtime activation, migration redesign, PARO execution, back-edge
  execution, fuse activation, or lifecycle default change.
- No rewrite of historical release facts, EVD rows, DEC rows, tags, or commits.
- No closure of RISK-037 or RISK-042 and no 1.0.0 readiness claim.
- No version bump, release manifest transition, tag, push, or REL-058 release
  authorization from either implementation task.
- No provenance-, path-, heading-, exception-name-, test-name-, or JSON-shape
  based allowlist.
- No reuse of the scanner enumerator by the independent release attestor.

## Decision Drivers

The partition is evaluated against these ordered requirements:

1. Fail closed: an incomplete slice cannot authorize a release.
2. Independent acceptance: each task has its own executable contract and
   rollback. FIX-199 consumes the latest terminal result from the new FIX-201
   Design Review chain and then starts fresh Code Review R0 and QA R0; FIX-200
   starts a fresh Design Review R0, Code Review R0, and QA R0 only after the
   FIX-199 commit.
3. Frozen-work preservation: no candidate hunk is discarded merely because it
   belongs to the later task.
4. Serial shared-file ownership: FIX-200 cannot edit a shared file before the
   FIX-199 commit is reviewed and pushed.
5. Thin integration: `verify_workflow.py` orchestrates leaf modules and does
   not become the second scanner implementation.
6. Acyclic dependencies and bounded additional runtime/memory.

## Alternatives Considered

### Alternative A: One combined FIX-199/FIX-200 commit

Keep the frozen FIX-197 candidate as one change, fix every R2 finding, and
review it again under a renamed task.

Rejected because it recreates the fused failure domain, prevents independent
rollback, and makes a fourth review of substantially the same combined
candidate look like a fresh separation. It also violates DEC-107's explicit
two-task serial commit requirement.

### Alternative B: Directory-exclusive parallel split

Give semantic files to FIX-199 and release/authority files to FIX-200, allowing
both tasks to run concurrently without hunk-level ownership.

Rejected because `loop_runtime_claims.py`, its focused test, policy, authority,
manifest, and verify adapter contain both semantic and identity behavior. A
directory split would either duplicate the scanner or let FIX-200 alter shared
interfaces before FIX-199 establishes them.

### Alternative C: Duplicate a v2 scanner for FIX-200

Leave the FIX-199 scanner unchanged and add a second authority/release scanner
that wraps or copies the original implementation.

Rejected because two policy loaders and two classification paths would drift,
increase common-mode failure, and complicate release verdict ownership. An
independent attestor is required, but it is restricted to inventory,
accounting, and identity; it does not duplicate semantic policy decisions.

### Alternative D: Serial shared-file takeover with an independent attestor

First reduce the frozen candidate to a complete FIX-199 semantic slice, commit
it with an explicit identity-pending release block, then let FIX-200 take over
the seven shared files and add a separate independent identity attestor.

Adopted because it preserves the candidate, gives each failure domain an
independent acceptance boundary, and ensures the interval between commits is
release-blocked by construction.

## Decision

Adopt Alternative D.

FIX-199 owns semantic truth correction and semantic claim classification. Its
leaf scanner may return a semantic PASS, but every governance/release adapter
must add the typed blocker `IDENTITY_ATTESTATION_PENDING` until FIX-200 is
complete. This blocker has no CLI bypass and is removed only in the reviewed
FIX-200 delta when all identity comparisons are PASS.

FIX-200 starts from the pushed FIX-199 commit. It adds an independent stdlib
identity attestor, closes three-root and required-file identity, changes
installed uninitialized status to non-healthy `NOT_APPLICABLE`, and binds the
reviewed/staged inventory to the final per-root candidate envelope: Git trees
for product/plugin and byte-identical immutable snapshots for external host
state. Any content change after attestation invalidates the attestation and
requires regeneration.

FIX-201 is architecture-only. It produces this ADR revision and a new
independent Design Review chain starting at `REVIEW-FIX-201-DESIGN-R0`.
FIX-199 MUST consume the latest terminal result of that chain with
`unresolved_blockers=0`; its execution packet MUST NOT instruct a Developer to
create/update ADR-012 or to start/replay any Design Review R0/R2. Design
production and Design Review are prerequisites completed outside the FIX-199
Developer scope.

## Module Boundaries

Each module has at most three sentences of responsibility.

### Packaged claim controls

`core/loop-runtime-claim-allowlist.json` defines exact historical ownership,
active claim classes, required surfaces, and structured planned markers.
`core/loop-runtime-claim-authority.json` binds those controls to the current
NOT_MET/PARTIAL authority and source-record hashes; neither file can authorize
itself by being policy-shaped.

### Semantic claim scanner

`infra/checks/loop_runtime_claims.py` performs scanner-side inventory,
language extraction, relation analysis, semantic classification, exact
history consumption, and typed findings. It exposes immutable reports and
never imports `verify_workflow.py`, the independent attestor, or release
modules.

### Independent identity attestor

`infra/checks/loop_runtime_claim_attestation.py` independently enumerates root
records, required regular files, content digests, and count-only semantic
accounting from a supplied per-root source envelope. It must not import
`loop_runtime_claims`, call its enumerator/extractors, or consume its candidate
objects; equality is established only by comparing serialized reports.

### Verify and release adapter

`infra/verify_workflow.py` resolves explicit roots, invokes the semantic
scanner and independent attestor, persists/loads candidate attestations, and
aggregates the gate verdict. It contains no claim grammar, policy table,
directory walker, canonicalization implementation, or semantic parser.

### Truth-correction surfaces

The review SKILL files, role mapping, migration comments, release/history
documents, CHANGELOG, and tool documentation are scanner inputs. They do not
import enforcement modules and retain append-only superseding notices where
ADR-011 requires them.

## Dependency Direction

```text
packaged claim controls --------------------+
                                             v
per-root source envelope -> semantic claim scanner -> SemanticClaimReport

per-root source envelope -> independent attestor ----> IdentityAttestationReport

SemanticClaimReport + IdentityAttestationReport
  -> verify/release adapter
  -> governance display / check-release / REL-058 gate

truth-correction surfaces -> scanner and attestor inputs only
```

There is no scanner-to-attestor, attestor-to-scanner, adapter-to-leaf reverse
import, or product-document import. The graph is acyclic.

## FIX-199 Semantic Contract

### Open-vocabulary claim potential

Claim potential is predicate- and domain-anchor based, not noun-list based.
For each extracted clause/unit, the analyzer independently locates:

- affirmative/negative state predicates, including word-order variants;
- Loop/runtime/migration domain anchors;
- generic criterion and risk closure anchors;
- temporal and quoted/fixture context.

A unit has open-vocabulary Loop claim potential when it contains an
affirmative state predicate and a Loop-domain anchor in the same semantic
unit, regardless of which appears first or which noun occurs between them.
Known policy subjects map to a reviewed claim class. Any remaining noun phrase
is represented as `unknown_loop_capability:<normalized phrase>` and blocks as
`UNCLASSIFIED_SURFACE`; it is never converted to structural data because the
noun is absent from a finite taxonomy.

Generic forms also remain claim-bearing without the word `Loop` when their
subject is an owned authority concept, including `runtime activation`,
`criterion <number>`, RISK-037/RISK-042 closure, or 1.0.0 readiness. Predicate
synonyms include active, enabled, ready, operational, implemented, complete,
MET, resolved, closed, superseded, replaced, and their existing Chinese
equivalents. Clause-local negation and contradiction rules from ADR-011 remain
mandatory.

Detection is also open-vocabulary on predicates and relations. Once a unit or
its inherited structural context is in the Loop/runtime/migration domain, the
analyzer MUST NOT treat an unrecognized state-like token, unresolved polarity,
or unresolved subject-to-predicate edge as absence of a claim. It emits one of
the following release-blocking results:

- `UNKNOWN_STATE_PREDICATE` when a token occupies a state/predicate position
  but is outside the reviewed positive, negative, planned, and historical
  predicate vocabulary;
- `AMBIGUOUS_POLARITY` when negation, modality, quotation, conditional scope,
  or contradiction cannot be attached to exactly one predicate;
- `AMBIGUOUS_SUBJECT_RELATION` when a Loop-domain subject/context and a state
  predicate are present but their relation cannot be proven absent or attached
  to one exact subject;
- `AMBIGUOUS_DOMAIN_CONTEXT` when structural context propagation is truncated,
  cyclic, dynamically resolved, or otherwise incomplete.

These are typed forms of `AMBIGUOUS_SEMANTIC_UNIT`; they are never downgraded
to `STRUCTURAL_DATA`, negative, or no-claim. A recognized negative may pass
only when the analyzer proves the subject, predicate, and negation edges in the
same propagated context.

### Structural context propagation

Extraction produces both a local payload and an ordered `context_chain`.
Classification analyzes their relation as one semantic unit; context supplies
domain/subject/predicate edges but never supplies policy authority.

Markdown propagation is deterministic:

1. An ATX or Setext heading applies to every following block until the next
   heading of the same or shallower level. The full heading stack is attached
   outermost-first.
2. A list item inherits the heading stack and all ancestor list-item payloads.
   Continuation lines belong to that item; a sibling never inherits another
   sibling's payload.
3. Each non-separator table cell is a unit. A body cell inherits the heading
   stack, its column header, and the first non-empty row-header cell when one
   exists. Missing/duplicate headers or a ragged row that prevents an exact
   column relation is `AMBIGUOUS_DOMAIN_CONTEXT`.
4. Paragraphs, comments, inline code, and fenced content inherit the active
   heading/list context. A fence boundary changes provenance, not domain scope.

JSON propagation uses decoded keys and RFC 6901 pointers. Every object key and
primitive value is a unit. A value inherits all ancestor key tokens plus its
own key; an array element inherits the array key and its exact numeric pointer.
Sibling values do not inherit one another. Duplicate keys, a pointer that
cannot be reconstructed exactly, or a policy-shaped object whose field role
cannot be resolved by exact owner/path/schema becomes typed ambiguous rather
than structural.

Python propagation is intraprocedural and binding-aware. A string/comment unit
inherits enclosing class/function names. An assigned value also inherits the
target identifier/attribute/subscript chain; every later local use inherits
the resolved binding chain. A call argument inherits the resolved callee or
receiver name, the exact keyword/positional parameter when statically known,
and the source binding of the argument. Aliasing, `*args`/`**kwargs`, dynamic
attribute lookup, unknown callees, closure/global escape, or a call mapping
that cannot be completed is `AMBIGUOUS_SUBJECT_RELATION` or
`AMBIGUOUS_DOMAIN_CONTEXT`; it is not fixture proof.

### Provenance is non-authoritative

Extraction provenance may describe where a unit came from, but classification
always evaluates semantic relations before considering a structural state.
The following rules apply:

- Markdown headings, Triggers/rollback lists, inline code, tables, comments,
  and fences do not suppress affirmative relations.
- Python diagnostic/exception strings, append targets, exported constants,
  attributes, subscripts, returned/yielded values, logging messages, and
  unknown call arguments do not become structural data because of AST shape.
- A test-local literal is fixture data only when intraprocedural proof shows
  every use remains inside the test, feeds an isolated scanner/mutation input,
  and is paired with an assertion of a blocking result. Any outer-object
  mutation, return/yield, unknown call, module/global binding, or incomplete
  use graph is `AMBIGUOUS_SEMANTIC_UNIT`.
- JSON structural fields are exempt only by exact root owner, normalized path,
  validated schema, and exact field role. A policy-shaped object at any other
  path, or a natural-language value in an unowned field, is classified by its
  semantics.
- Provenance can support `STRUCTURAL_DATA` only when there is no current
  affirmative product-capability relation, or when the exact fixture proof
  above establishes quoted negative-test input. Provenance alone never maps a
  unit to `AFFIRMATIVE_CLASSIFIED` or historical ownership.

### Exact-once historical ownership

The scanner builds a bijection between reviewed historical policy entries and
consumed semantic units. Each entry must resolve one exact locator and payload,
and exactly one extracted unit must consume that `claim_id`.

- zero consumers -> `HISTORICAL_ENTRY_UNUSED`;
- more than one consumer -> `HISTORICAL_ENTRY_MULTIPLE`;
- one unit consumed by more than one entry -> `HISTORICAL_UNIT_MULTI_OWNED`;
- exact payload/locator/notice drift retains the ADR-011 typed failures;
- path, heading, substring, temporal wording, or provenance cannot substitute
  for the exact fingerprint.

`historical_matches` is therefore equal to the full reviewed historical entry
count on a semantic PASS, not merely the number of distinct IDs encountered.

### FIX-199 interfaces

```text
extract_semantic_units(candidate_bytes, language, locator_contract,
                       semantic_accounting_contract)
  -> ExtractionResult(units, complete=true, accounting)
  ! PARSE_ERROR | UNKNOWN_LANGUAGE | AMBIGUOUS_EXTRACTION |
    ACCOUNTING_CONTRACT_MISMATCH | SEMANTIC_BUDGET_EXCEEDED

analyze_claim_relations(unit)
  -> RelationSet(anchors, predicates, polarity, temporal_scope,
                 unknown_capability_phrase?)
  ! UNKNOWN_STATE_PREDICATE | AMBIGUOUS_POLARITY |
    AMBIGUOUS_SUBJECT_RELATION | AMBIGUOUS_DOMAIN_CONTEXT |
    AMBIGUOUS_SEMANTIC_UNIT | CONTRADICTORY_POLARITY

classify_semantic_unit(unit, relations, policy, authority)
  -> SemanticClassification(state, claim_id?, rationale)
  ! UNCLASSIFIED_SURFACE | UNSUPPORTED_AFFIRMATIVE |
    MISSING_AUTHORITY

consume_historical_ownership(units, historical_entries, notices)
  -> HistoricalConsumption(entry_to_unit, unit_to_entry)
  ! HISTORICAL_ENTRY_UNUSED | HISTORICAL_ENTRY_MULTIPLE |
    HISTORICAL_UNIT_MULTI_OWNED | fingerprint/notice typed failures

scan_loop_runtime_claims(context)
  -> SemanticClaimReport(semantic_verdict, scanner_inventory,
                         semantic_accounting_contract, accounting,
                         findings, history_consumption)
```

The semantic report does not authorize release. Until FIX-200, the adapter
aggregates it with `identity_verdict=PENDING` and emits
`IDENTITY_ATTESTATION_PENDING`.

## FIX-200 Identity Contract

### Three-root inventory

The context retains the three explicit roles from ADR-011:

```text
ClaimScanContext(product_root, plugin_home, host_root, scan_mode)
```

Each configured root is inspected lexically with `lstat`/platform-equivalent
metadata before canonicalization. A root that is itself, or contains, a
symlink/junction/reparse component blocks; `resolve()` may be recorded but
cannot erase lexical identity.

Root records contain role, configured absolute path, canonical path, stable
file identity where available, and allowed role relationship. Exact
`product_root == host_root` is allowed only in `product_release`; two different
lexical paths resolving to the same physical root are
`ROOT_ALIAS_COLLISION`. `plugin_home` remains an independent role even when it
is physically nested under `product_root`.

One process-wide `WorkspaceSource` or Git source is forbidden. Every role has
one explicit binding in a versioned source envelope:

```text
RootSourceEnvelope(
  schema_version="loop-root-source/v1",
  bindings={
    product_root: GitIndexRootSource | GitTreeRootSource,
    plugin_home:  GitIndexRootSource | GitTreeRootSource,
    host_root:    ImmutableWorkspaceSnapshot,
  })
```

FIX-200 changes the scanner entry point to
`scan_loop_runtime_claims(context, root_source_envelope)` and the attestor takes
the same envelope value. No default envelope, current-working-directory
inference, or fallback to live paths is permitted in a release-authorizing
mode.

For a release-authorizing `product_release` scan, `product_root` and
`plugin_home` MUST be Git-backed. A Git binding resolves the exact repository
root tree before selecting a role prefix:

```text
GitRepositoryIdentity(
  schema_version: literal "loop-git-repository-tree/v1",
  object_format: "sha1" | "sha256",
  repository_root_tree_oid: lowercase hexadecimal Git OID
)

PortableGitSourceIdentity(
  role: "product_root" | "plugin_home",
  repository_identity: GitRepositoryIdentity,
  tree_prefix: normalized root-relative string,
  selected_tree_oid: lowercase hexadecimal Git OID
)
```

For `:index`, `repository_root_tree_oid` is the result of writing the complete
index as one root tree without reading unstaged bytes. For a commit or tree
ref, it is the complete root tree selected by that ref. `selected_tree_oid` is
the tree at `tree_prefix`; the empty prefix selects the repository root tree.
This content-addressed definition is the only `repository_identity` used by
portable binding identity, scanner/attestor equality, persisted attestation,
and final-candidate comparison. A repository common-directory locator and
checkout path are diagnostics only and MUST NOT participate in equality.

Product and plugin bindings from the same repository/index or repository/ref
therefore carry the same `repository_identity` and may carry different
prefixes/selected trees. A repository-external plugin resolves its own
`repository_identity`, prefix, and selected tree. Two physically separate
repositories with byte-identical complete root trees intentionally have the
same portable content identity; equality still compares role, prefix,
selected tree, modes, normalized paths, and blob bytes, so a label or hash
alone cannot authorize a source. A missing Git object, dirty live-file
fallback, prefix escape, or repository/prefix ambiguity blocks as
`ROOT_SOURCE_UNAVAILABLE` or `ROOT_SOURCE_AMBIGUOUS`.

`host_root` uses an immutable workspace snapshot because governance hot files
may be untracked or ignored and therefore absent from every Git tree. Snapshot
creation walks the applicable host inventory without Git ignore filtering,
rejects aliases and non-regular files, copies the exact bytes to an artifact
outside all scanned roots, and writes a sorted manifest containing normalized
path, file type, mode, size, and SHA-256. The manifest is sealed only after all
copies rehash successfully. The snapshot identity is the SHA-256 of the
canonical manifest plus the concatenated length-delimited file bytes; scanners
read only sealed snapshot bytes, never the mutable source workspace.

An `installed_host` diagnostic may use immutable snapshots for installed
product/plugin bytes, but that source combination is explicitly
`release_authorized=false`; only the release-mode binding matrix above can
authorize a candidate.

Both scanner and attestor receive the same envelope but resolve every binding
independently. Their inventories contain the exact policy and authority bytes
loaded from the `plugin_home` binding, including an external plugin Git tree.
Control loading consumes the scanner-resolved bytes rather than re-reading a
live path, so classified authority cannot differ from inventoried authority.

Source equality is role-local before it is aggregate:

- the role set and exactly-one binding cardinality must match;
- Git-backed roots compare the exact `PortableGitSourceIdentity` above, then
  file modes, normalized path set, and blob bytes; only these roots are
  subject to staged-index/commit-tree equality;
- immutable snapshots compare the complete sorted record set and raw bytes
  byte-for-byte. A fresh final snapshot may have a different artifact location
  but must reproduce the same snapshot identity; no Git OID is required or
  inferred for it;
- aggregate equality is PASS only when every role-local comparison is PASS.

Each binding identity is SHA-256 over canonical JSON of its portable identity
object and complete sorted record digest. `source_envelope_sha256` is SHA-256
over canonical JSON containing `schema_version`, `scan_mode`, and the three
binding identities in role order; artifact locations and diagnostic absolute
paths are excluded. Canonical JSON uses the same key ordering/escaping rules as
the accounting contract. Envelope equality requires exact schema/mode/role
sets and binding identities, followed by byte-level record comparison; a hash
match alone is not accepted without the records needed for comparison.

Typed failures include `ROOT_SOURCE_ROLE_MISSING`,
`ROOT_SOURCE_ROLE_MULTIPLE`, `ROOT_SOURCE_KIND_INVALID`,
`ROOT_SOURCE_GIT_MISMATCH`, `ROOT_SOURCE_SNAPSHOT_MISMATCH`, and
`ROOT_SOURCE_BYTE_MISMATCH`.

### Required-file closure

Every `required_paths` entry must satisfy all of the following:

1. the root role exists and is applicable to the scan mode;
2. the lexical path is safe and has no alias/reparse component;
3. `lstat` identifies a regular file, not a directory or special file;
4. the exact `(root_owner, normalized_path, content_sha256, raw_bytes)` record
   exists in both scanner and independent inventories;
5. the final candidate comparison contains the same record.

Failures are typed as `REQUIRED_ROOT_UNAVAILABLE`,
`REQUIRED_PATH_NOT_REGULAR`, `REQUIRED_PATH_NOT_IN_SCANNER_INVENTORY`,
`REQUIRED_PATH_NOT_IN_INDEPENDENT_INVENTORY`, or
`REQUIRED_PATH_FINAL_DRIFT`.

### Installed NOT_APPLICABLE

An installed host without initialized `.governance` data returns:

```text
verdict: NOT_APPLICABLE
healthy: false
authorized: false
host_state: NOT_APPLICABLE
reason: HOST_GOVERNANCE_NOT_INITIALIZED
```

The CLI and Check 31 display `[N/A]`, never `[PASS]`, and release aggregation
does not count N/A as green. Product authority and control integrity may still
be reported, but they cannot convert the host result to PASS.

### Independent inventory and accounting

The attestor accepts the per-root envelope, not one filesystem/Git source:

```text
attest_loop_runtime_identity(context, root_source_envelope, limits)
  -> IdentityAttestationReport(
       verdict,
       root_records,
       independent_inventory,
       semantic_accounting_contract,
       semantic_accounting_by_path,
       control_digests,
       required_file_records,
       source_envelope_identity,
       findings)
```

The attestor independently implements binding resolution, path walking,
lexical root checks, canonical content serialization, and count-only
Markdown/Python/JSON accounting. It may share this written contract, golden
inputs/expected bytes, and standard-library parsers, but no scanner code,
candidate objects, enumerator, canonicalization helper, context builder,
provenance index, serializer, or report builder.

#### Versioned semantic accounting contract

Both implementations MUST implement
`semantic_accounting_contract="loop-semantic-accounting/v1"`. A missing or
different version is `ACCOUNTING_CONTRACT_MISMATCH`; equality of unversioned
counts is never sufficient.

Common input and normalization rules are normative:

1. Raw-file identity is computed before text normalization. Semantic input is
   strict UTF-8; one leading UTF-8 BOM is removed, any other BOM or decoding
   failure blocks.
2. `CRLF` and bare `CR` become `LF`, then text is normalized to Unicode NFC.
   No case-folding, tab expansion, internal whitespace collapse, or locale
   transform is permitted.
3. A unit payload removes only syntax delimiters named below and leading/trailing
   ASCII space, tab, and LF introduced at that unit boundary. Internal bytes
   remain exact. Empty normalized payloads are not units.
4. Every unit record is a JSON object with exactly these keys and JSON types:
   `root_owner:string`, `normalized_path:string`, `language:string`,
   `ordinal:integer`, `kind:string`, `locator:object`,
   `context_chain:array<object>`, and `normalized_payload:string`. Ordinals are
   zero-based source order. Missing keys, additional keys, non-integer numeric
   positions, or a type mismatch are `ACCOUNTING_SERIALIZATION_ERROR`.

The `locator` object always contains exactly the following keys, including
explicit JSON `null` values:

```text
end_column: integer >= 0 | null
end_line: integer >= 0 | null
pointer: string | null
role: "key" | "value" | null
start_column: integer >= 0 | null
start_line: integer >= 0 | null
type: "source_span" | "json_pointer"
```

`source_span` requires all four line/column integers and requires
`pointer=role=null`; it is zero-based and half-open. `json_pointer` requires an
escaped RFC 6901 `pointer`, requires `role`, and requires all line/column
members to be `null`. No `#key` suffix is serialized; key-versus-value is the
typed `role` member.

Every `context_chain` member always contains exactly these keys and types,
again retaining explicit `null` members:

```text
index: integer >= 0 | null
kind: "md_heading" | "md_list_item" | "md_table_header" |
      "md_table_row_header" | "json_key" | "json_array_index" |
      "py_class" | "py_function" | "binding" | "source_binding" |
      "receiver" | "call" | "parameter_index" | "parameter_name" |
      "formatted_binding"
level: integer >= 0 | null
name: string | null
payload: string | null
pointer: string | null
```

The fields not named by a context kind are `null`: Markdown heading/list
contexts use `level` and `payload`; Markdown table contexts use `index` and
`payload`; JSON key contexts use `payload` and `pointer`; JSON array contexts
use `index` and `pointer`; Python class/function/binding/source-binding/
receiver/call/formatted-binding contexts use `name`; `parameter_index` uses
`index`; and `parameter_name` uses `name`. Context order is outermost-first
and is semantically significant. An empty chain is `[]`.

Markdown `v1` unit boundaries are evaluated in this precedence order:

- an ATX/Setext heading is one `md_heading` unit; heading markers/underline are
  removed and the heading stack is updated after emitting the unit;
- each list item, including its indented continuation lines up to the next
  sibling/ancestor boundary, is one `md_list_item` unit;
- a valid GFM table emits each non-separator header/body cell as one
  `md_table_cell` in row-major order; escaped pipes do not split cells;
- an HTML comment body is one `md_comment`; an unterminated comment blocks;
- fence delimiters are not units; every non-empty logical line inside a fence
  is one `md_fence_line` and retains the active outer context;
- every maximal remaining run of non-empty lines is one `md_paragraph`, joined
  with `LF`. Blank lines emit no unit.

The heading/list/table context rules in `Structural context propagation` are
part of the accounting record. Ambiguous Setext precedence, unterminated
fences/comments, or a ragged/duplicate-header table blocks as
`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY`.

JSON `v1` is strict RFC 8259 with duplicate-key rejection. Pre-order traversal
emits every decoded object key as `json_key`, then recursively emits its value;
each string, number, boolean, or null is one `json_string`, `json_number`,
`json_boolean`, or `json_null` unit. String payload is the decoded scalar;
boolean/null payload is lowercase; number payload is the exact valid source
lexeme, including `-0`. Object/array containers are not units. Keys and values
carry exact escaped RFC 6901 pointers and the ancestor/current-key context
defined above. Parse, duplicate-key, invalid-surrogate, or pointer construction
failures are `ACCOUNTING_JSON_PARSE_ERROR`,
`ACCOUNTING_JSON_DUPLICATE_KEY`, or `ACCOUNTING_JSON_POINTER_ERROR`.

Python `v1` requires both `ast.parse` and `tokenize` to succeed. Each comment
token is one `py_comment` after removing the leading `#`. Each outermost
`Constant(str)` or `JoinedStr` expression is one `py_string`; compiler-folded
adjacent literals are one unit, nested constant fragments of a `JoinedStr` are
not double-counted, and bytes literals are not units. A constant payload is its
decoded string. A `JoinedStr` payload concatenates decoded literal fragments
and the exact token `{EXPR}` for each formatted expression; referenced binding
names are added to context. The locator is the AST half-open source span and
the binding/call context rules above are mandatory. Syntax/tokenization,
missing spans, overlapping outermost string spans, or incomplete call/binding
mapping blocks as `ACCOUNTING_PYTHON_PARSE_ERROR`,
`ACCOUNTING_PYTHON_SPAN_ERROR`, or `ACCOUNTING_PYTHON_CONTEXT_ERROR`.

Canonical serialization is UTF-8 NDJSON with no BOM. Record keys are sorted by
Unicode code point; arrays preserve order; non-ASCII is unescaped; only JSON
control characters, quote, and backslash use shortest JSON escapes; there is
no insignificant whitespace and every record ends in `LF`. Records are sorted
by role order `product_root`, `plugin_home`, `host_root`, then normalized-path
UTF-8 bytes, then ordinal. Each per-path summary contains unit count, sum of
normalized-payload UTF-8 byte lengths, and SHA-256 of its exact record lines;
the aggregate SHA-256 covers the concatenated record lines without truncation.
Serialization/limit failures are `ACCOUNTING_SERIALIZATION_ERROR` or
`ACCOUNTING_LIMIT_EXCEEDED`.

The following normative golden vectors are authored constants from this ADR,
not output examples. Each positive code block is the literal UTF-8 NDJSON byte
sequence: no BOM, one `0A` byte after every displayed JSON record, and no
additional blank record. The record key order and nested key order shown below
are normative Unicode-code-point order. Each implementation test module MUST
embed these bytes and digest literals independently. Vector inputs may be
shared; expected records, expected bytes, expected digests, and serializers
MUST NOT be generated by or imported from either production implementation.

`ACCT-V1-MD-01` input bytes are
`# Loop runtime\n- state: frobnicated\n` at
`product_root:golden/ACCT-V1-MD-01.md`. Normative NDJSON bytes:

```ndjson
{"context_chain":[],"kind":"md_heading","language":"markdown","locator":{"end_column":14,"end_line":0,"pointer":null,"role":null,"start_column":0,"start_line":0,"type":"source_span"},"normalized_path":"golden/ACCT-V1-MD-01.md","normalized_payload":"Loop runtime","ordinal":0,"root_owner":"product_root"}
{"context_chain":[{"index":null,"kind":"md_heading","level":1,"name":null,"payload":"Loop runtime","pointer":null}],"kind":"md_list_item","language":"markdown","locator":{"end_column":20,"end_line":1,"pointer":null,"role":null,"start_column":0,"start_line":1,"type":"source_span"},"normalized_path":"golden/ACCT-V1-MD-01.md","normalized_payload":"state: frobnicated","ordinal":1,"root_owner":"product_root"}
```

Normative summary: `unit_count=2`, `payload_bytes=30`,
`ndjson_bytes=712`, per-path and aggregate
`sha256=5ce9ad09d7cc4b418da7b1cedd64448b92d998e209f438e6fbe15463c4755b43`.

`ACCT-V1-JSON-01` input bytes are
`{"loop_runtime":{"state":"frobnicated"}}` at
`product_root:golden/ACCT-V1-JSON-01.json`. Normative NDJSON bytes:

```ndjson
{"context_chain":[],"kind":"json_key","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime","role":"key","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"loop_runtime","ordinal":0,"root_owner":"product_root"}
{"context_chain":[{"index":null,"kind":"json_key","level":null,"name":null,"payload":"loop_runtime","pointer":"/loop_runtime"}],"kind":"json_key","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime/state","role":"key","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"state","ordinal":1,"root_owner":"product_root"}
{"context_chain":[{"index":null,"kind":"json_key","level":null,"name":null,"payload":"loop_runtime","pointer":"/loop_runtime"},{"index":null,"kind":"json_key","level":null,"name":null,"payload":"state","pointer":"/loop_runtime/state"}],"kind":"json_string","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime/state","role":"value","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"frobnicated","ordinal":2,"root_owner":"product_root"}
```

Normative summary: `unit_count=3`, `payload_bytes=28`,
`ndjson_bytes=1311`, per-path and aggregate
`sha256=8b06455b9e738669066c77c29e53263a38cb8fc35d1065e939b370bfddd258bb`.

`ACCT-V1-PY-01` input bytes are
`loop = "frobnicated"\nemit("ready")\n` at
`product_root:golden/ACCT-V1-PY-01.py`. Normative NDJSON bytes:

```ndjson
{"context_chain":[{"index":null,"kind":"binding","level":null,"name":"loop","payload":null,"pointer":null}],"kind":"py_string","language":"python","locator":{"end_column":20,"end_line":0,"pointer":null,"role":null,"start_column":7,"start_line":0,"type":"source_span"},"normalized_path":"golden/ACCT-V1-PY-01.py","normalized_payload":"frobnicated","ordinal":0,"root_owner":"product_root"}
{"context_chain":[{"index":null,"kind":"call","level":null,"name":"emit","payload":null,"pointer":null},{"index":0,"kind":"parameter_index","level":null,"name":null,"payload":null,"pointer":null}],"kind":"py_string","language":"python","locator":{"end_column":12,"end_line":1,"pointer":null,"role":null,"start_column":5,"start_line":1,"type":"source_span"},"normalized_path":"golden/ACCT-V1-PY-01.py","normalized_payload":"ready","ordinal":1,"root_owner":"product_root"}
```

Normative summary: `unit_count=2`, `payload_bytes=16`,
`ndjson_bytes=859`, per-path and aggregate
`sha256=10a22c5e617b6b9e4ac55b22c9a0602a78f3405e7c40fdf04aae2e0129bf92d0`.

`ACCT-V1-ERR-01` input bytes are `{"loop":1,"loop":2}` at
`product_root:golden/ACCT-V1-ERR-01.json`. The normative result is
`ACCOUNTING_JSON_DUPLICATE_KEY`, zero emitted records, literal NDJSON bytes of
length `0`, and
`sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The empty-byte digest is a vector constant only; the typed error prevents it
from being accepted as a successful zero-unit accounting result.

These literal constants fix input bytes, record fields and types, ordinal,
locator, context order, root/path, JSON escaping, payload byte count, NDJSON
length, and digest. An implementation-derived expected value fails this ADR
even when both production paths agree with each other.

The adapter compares, without truncation:

```text
scanner role/source binding set == independent role/source binding set
scanner path set == independent path set
scanner per-path raw bytes/digest == independent per-path raw bytes/digest
scanner parsed path set == independent accounted path set
scanner semantic_accounting_contract == independent contract == v1
scanner per-path count/payload-bytes/record-sha256 == independent values
scanner aggregate accounting NDJSON SHA-256 == independent value
scanner policy/authority digest == independent plugin_home control digest
```

Any mismatch blocks with `INDEPENDENT_SOURCE_BINDING_MISMATCH`,
`INDEPENDENT_INVENTORY_MISMATCH`, `INDEPENDENT_CONTENT_MISMATCH`,
`INDEPENDENT_ACCOUNTING_MISMATCH`, or `INDEPENDENT_CONTROL_MISMATCH`. The
release adapter also performs an import/reference boundary test that fails if
the attestor imports the scanner or either implementation imports a shared
accounting helper.

### Persisted final-candidate identity

The final comparison uses a versioned JSON attestation envelope stored outside
the scanned product and hot-file set, for example a caller-selected CI artifact
or `.governance/release-attestations/<version>-loop-runtime-claims.json`.
Persistence is performed by the Coordinator/Release Agent or CI caller, not by
the semantic leaf.

The envelope contains:

```text
schema_version
scan_mode
root_source_envelope        # exactly one versioned binding per root role
source_binding_identities   # per-role Git tuple or snapshot identity
source_envelope_sha256
root_records
scanner_inventory_sha256
independent_inventory_sha256
semantic_accounting_contract
semantic_accounting_sha256
policy_sha256
authority_sha256
required_file_records_sha256
semantic_verdict
identity_verdict
```

For FIX-200 pre-commit review, the product binding uses the exact staged index,
not an unstaged worktree. The plugin binding uses that index with its own prefix
when it is in the product repository, or an exact tree OID from its external
repository. The host binding is a sealed immutable snapshot that includes
applicable ignored governance files.

The only legal source-kind transition is the role-local relation
`GitIndexRootSource -> GitTreeRootSource(candidate_commit)`. It is transition
equivalence, not literal binding-kind equality, and it is PASS if and only if
all of the following hold:

1. the role is unchanged, `candidate_commit` resolves to a commit, and its
   complete repository root tree OID exactly equals the root tree written from
   the recorded staged index;
2. the pre-commit and final bindings have the exact same
   `GitRepositoryIdentity`, including object format and repository root tree
   OID, and the exact same normalized selected `tree_prefix`;
3. the selected tree OID is equal on both sides after applying that prefix;
4. independently materialized complete record sets are equal in cardinality,
   normalized paths, modes, object/blob identities, sizes, raw bytes, per-file
   digests, and aggregate record digest; no live-worktree fallback, omitted
   record, ignored scoped byte, or diagnostic repository locator participates
   in or substitutes for this comparison; and
5. scanner and attestor independently recompute equal portable binding,
   inventory, accounting, control, and required-file digests from the final
   candidate tree.

This relation permits the acquisition kind to change from index to candidate
tree while requiring portable binding equality and complete scoped byte
equality. It does not rewrite the persisted pre-commit source fact. A
tree-to-index, index-to-snapshot, snapshot-to-tree, different-role,
different-repository-identity, different-prefix, or any other source-kind
transition fails closed as `CANDIDATE_SOURCE_BINDING_MISMATCH`; root-tree or
selected-tree inequality additionally reports `CANDIDATE_GIT_TREE_MISMATCH`.

After the candidate commit:

1. each staged-index Git binding MUST satisfy the transition equivalence above
   against its corresponding `GitTreeRootSource(candidate_commit)`;
2. each already-pinned external `GitTreeRootSource` must retain the same source
   kind, repository identity, OID, prefix, modes, paths, bytes, and digests;
3. a fresh `ImmutableWorkspaceSnapshot` must reproduce the original host
   record set and raw bytes exactly, therefore the same snapshot identity;
4. scanner and attestor recompute all inventory/accounting/control/required
   digests from those final per-root sources.

Git equality is never applied to the host snapshot, and a Git tree match for
product/plugin cannot mask host byte drift. Conversely, a matching snapshot
digest cannot substitute for a missing Git candidate tree. The envelope is
equal only when the role set matches, every binding-kind relation is either
same-kind or the single legal index-to-candidate-tree transition, and all
role-local portable identities, materialized records, raw bytes, and aggregate
digests match.

REL-058 must repeat this protocol after its own final release changes are
staged. A FIX-200 attestation cannot authorize a later release candidate;
changing any scanned file, required file, policy/authority byte, or root
identity produces `CANDIDATE_ATTESTATION_STALE` and requires a new independent
reviewed attestation.

Final comparison failures are typed as
`CANDIDATE_ATTESTATION_MISSING`, `CANDIDATE_SOURCE_BINDING_MISMATCH`,
`CANDIDATE_GIT_TREE_MISMATCH`, `CANDIDATE_SNAPSHOT_BYTE_MISMATCH`,
`FINAL_INVENTORY_DIGEST_MISMATCH`, `FINAL_ACCOUNTING_DIGEST_MISMATCH`,
`FINAL_POLICY_DIGEST_MISMATCH`, `FINAL_AUTHORITY_DIGEST_MISMATCH`, and
`FINAL_REQUIRED_FILE_DIGEST_MISMATCH`.

### FIX-200 scoped attestation rehearsal

FIX-200 validates only the claim/identity adapter. It MUST NOT invoke the full
`check-release --version 0.66.1` gate, create versioned release documents,
change a version declaration, tag, or publish. Those operations belong only to
REL-058 after FIX-199 and FIX-200 are committed and pushed.

The adapter extends the existing `check-loop-runtime-claims` command with a
source-binding mode. Its executable FIX-200 boundary is:

```text
python skills/software-project-governance/infra/verify_workflow.py check-loop-runtime-claims --scan-mode product_release --product-git-repo <repo> --product-git-ref :index --product-prefix <product-prefix> --plugin-git-repo <repo-or-external-repo> --plugin-git-ref <index-or-tree> --plugin-prefix <plugin-prefix> --host-root <host-root> --snapshot-dir <outside-all-roots> --write-attestation <artifact> --require-identity --fail-on-issues

python skills/software-project-governance/infra/verify_workflow.py check-loop-runtime-claims --scan-mode product_release --product-git-repo <repo> --product-git-ref <candidate-commit> --product-prefix <product-prefix> --plugin-git-repo <repo-or-external-repo> --plugin-git-ref <final-tree> --plugin-prefix <plugin-prefix> --host-root <host-root> --snapshot-dir <new-outside-all-roots> --compare-attestation <artifact> --require-identity --fail-on-issues
```

`:index` is accepted by either Git-ref argument and means the adapter obtains
that repository's exact index tree OID without reading unstaged bytes; every
other ref must resolve to one tree OID before scanning. The command seals the
host snapshot in `--snapshot-dir`, builds
the per-root envelope, runs both implementations, and writes or compares the
attestation. Tests use disposable Git repositories and host roots, so the
rehearsal is runnable before any 0.66.1 release document exists. PASS means the
scoped semantic-plus-identity adapter is internally valid; it is not release
readiness or REL-058 authorization.

The two commands above are one atomic FIX-200 acceptance rehearsal. Both the
`--write-attestation --require-identity` command and the subsequent
`--compare-attestation --require-identity` command are mandatory execution-
packet commands; a unit test, one half of the pair, a report-only invocation,
or a full `check-release` run is not a substitute. The comparison command MUST
consume the artifact written by the first command and a fresh host snapshot.

The exact focused regression entry, which is additional evidence rather than
a replacement for either CLI command, is:

```text
python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow.FIX200ScopedAttestationRehearsalTests -v
```

## File Ownership And Serial Takeover

ADR-012 itself is an architecture prerequisite outside both Developer scopes.
It is reviewed and committed before product implementation; neither FIX-199
nor FIX-200 `allowed_change_scope`, staged path set, implementation commit, or
rollback may add, edit, restore, or revert this ADR. A later architecture
change requires a separately locked Architect task and a new Design Review
terminal result before any affected Developer is dispatched.

### FIX-199 exclusive product files

| Path | FIX-199 ownership |
| --- | --- |
| `skills/code-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/design-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/release-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/requirement-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/retro-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/tech-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/test-review/SKILL.md` | current-vs-planned semantic correction |
| `skills/software-project-governance/references/loop-role-mapping.md` | shared role truth correction |
| `skills/software-project-governance/infra/loop_migration.py` | comments/current behavior wording only |
| `skills/software-project-governance/infra/TOOLS.md` | scanner command and no-overclaim documentation |
| `project/CHANGELOG.md` | append-only 0.66.1 correction and historical notice |
| `docs/migration/loop-engineering-runtime-contract-migration-0.66.1.md` | migration truth boundary |
| `docs/release/feature-flags-0.65.0.md` | append-only superseding notice |
| `docs/release/release-checklist-0.65.0.md` | append-only superseding notice |
| `docs/release/rollback-plan-0.65.0.md` | append-only superseding notice |
| `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` | append-only superseding notice/current interpretation |
| `docs/requirements/loop-engineering-implementation-breakdown-0.65.0.md` | append-only superseding notice |
| `docs/requirements/shitu-loop-engineering-validation-0.65.0.md` | append-only superseding notice |

FIX-200 does not modify these files. If final identity detects drift in one of
them, the result is a blocking mismatch, not a FIX-200 content edit.

### Shared files, owned serially

| Path | FIX-199 delta | FIX-200 delta after FIX-199 commit |
| --- | --- | --- |
| `skills/software-project-governance/infra/checks/loop_runtime_claims.py` | semantic report, open vocabulary, non-authoritative provenance, exact-once history, scanner inventory A | plugin_home inventory records, snapshot-byte control loading, root/required-file closure, comparison fields |
| `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py` | semantic/provenance/history matrix and semantic performance | three-root, alias, required-file, N/A, independent comparison, final mutation matrix |
| `skills/software-project-governance/core/loop-runtime-claim-allowlist.json` | exact semantic/history policy and required-surface declaration | root-role/required-inventory schema additions only if approved by Design Review R0; no semantic allowlist expansion |
| `skills/software-project-governance/core/loop-runtime-claim-authority.json` | current NOT_MET/PARTIAL authority and policy digest | control identity/schema additions only; no claim-status relaxation |
| `skills/software-project-governance/core/manifest.json` | ship/register scanner, policy, authority, tests/tools as required | register independent attestor and any attestation schema; required-file type metadata |
| `skills/software-project-governance/infra/verify_workflow.py` | thin semantic CLI/gate adapter plus non-bypassable `IDENTITY_ATTESTATION_PENDING` | independent attestor orchestration, N/A display, persistence/final comparison; remove pending blocker only when aggregate contract is enforced |
| `skills/software-project-governance/infra/tests/test_verify_workflow.py` | semantic command and pending-release-block assertions; existing migration truth correction hunk | explicit three-root adapter, N/A, attestation persistence/final-candidate CLI assertions |

The FIX-199 execution packet `allowed_change_scope` MUST enumerate all 18
exclusive product paths and all seven shared paths above. In particular,
`skills/software-project-governance/infra/verify_workflow.py` is mandatory
FIX-199 scope because it owns the non-bypassable
`IDENTITY_ATTESTATION_PENDING` adapter behavior. Omitting that path, replacing
the 25-path boundary with an open-ended directory, or adding ADR-012 makes the
packet invalid and blocks Developer dispatch.

FIX-200 MUST NOT acquire a write lock for any shared file until FIX-199 has:

1. obtained the latest terminal FIX-201 Design Review result with
   `unresolved_blockers=0`, then passed fresh Code Review R0 and QA R0;
2. been committed as one scoped task commit;
3. been pushed;
4. released its shared-file locks.

### FIX-200 exclusive new files

| Path | Ownership |
| --- | --- |
| `skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py` | independent production inventory/accounting/final identity leaf |
| `skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py` | independence, source, root, digest, accounting, and final-candidate tests |

These two paths are already present in the FIX-200 execution packet. Before
dispatching the FIX-200 Developer, the Coordinator verifies that the packet
and locks still include them. Their presence is a scoped response to the R2
independent-enumerator blocker, not authorization for unrelated modules.

## Frozen Dirty Candidate Preservation And Staging

The existing candidate is evidence and must remain recoverable throughout the
split. The Developer uses this non-destructive sequence:

1. Before editing, create an out-of-repository frozen bundle containing the
   binary diff for all 21 tracked files, byte-for-byte copies of the four
   untracked files, a normalized path manifest, and SHA-256 for every member.
   Record only the bundle digest/location in governance evidence.
2. Verify the bundle can reconstruct the candidate in a disposable temporary
   tree. Do not use `git reset`, checkout, clean, or stash as the partition
   mechanism.
3. In the real worktree, reduce the seven shared files to the approved FIX-199
   boundary, preserving/reworking the semantic portions and removing/defering
   partial FIX-200 identity behavior. The adapter must contain the explicit
   pending identity blocker.
4. Stage the 18 FIX-199-exclusive paths and the seven FIX-199 shared-file
   states by explicit path. The cached path set must equal the ownership table;
   no FIX-200-exclusive file may exist in the index.
5. Validate `git diff --cached`, scanner tests, pending release block, the
   latest terminal ADR Design result, and fresh FIX-199 Code Review R0/QA R0.
   Commit and push FIX-199 only.
6. Compare the new worktree/commit with the frozen bundle and ownership ledger
   to prove no candidate hunk disappeared. Reapply only the preserved
   FIX-200 identity hunks that remain valid, then implement the reviewed
   FIX-200 design on top of the FIX-199 commit.
7. Stage the two FIX-200-exclusive files and only the FIX-200 deltas in the
   seven shared files. The cached diff must not modify any FIX-199-exclusive
   truth surface.
8. Generate the staged-index attestation, run all FIX-200 R0 reviews, commit,
   compare the commit tree to the attestation, and push FIX-200 only.

Patch/bundle preservation is a recovery control, not a source of truth. The
reviewed ADR and current repository facts determine which preserved hunks are
reapplied.

## Acceptance Matrix

### FIX-199 acceptance

| Area | Required evidence |
| --- | --- |
| Baseline | Complete real repository semantic scan; zero skip/truncate/finding; parsed candidates equal scanner inventory; all reviewed historical entries consumed exactly once |
| Unknown nouns | Markdown, Python, and JSON mutations for controller, coordinator, worker, engine, lifecycle driver, and at least one unseen noun all block |
| Unknown predicates/relations | Under inherited Loop context, one unseen state predicate, unresolved negation, and unresolved subject edge in each language block as `UNKNOWN_STATE_PREDICATE`, `AMBIGUOUS_POLARITY`, or `AMBIGUOUS_SUBJECT_RELATION` |
| Word order | Both `Loop controller is operational` and `The scheduler is operational for Loop execution` block |
| Generic authority subjects | `Runtime activation is complete`, `Criterion 5 is MET`, and `RISK-037 is resolved` block |
| Markdown provenance/context | Heading-to-paragraph, parent-to-child list, header-to-table-cell, inline code, comment, and fence inherited Loop context all classify; ragged/duplicate table context blocks typed ambiguous |
| Python provenance/context | Binding target/use, diagnostic/exception, append/outer mutation, escaping assignment, returned/yielded value, exported constant, resolved call parameter, and unknown/dynamic call argument block or become typed ambiguous |
| JSON provenance/context | Key/RFC6901 pointer context reaches descendant scalars; forged policy-shaped objects, duplicate keys, and natural-language affirmative values block; exact validated control fields remain structural only by field contract |
| Accounting v1 | Scanner independently passes the four normative golden vectors, exact NDJSON/digests, and all typed parser/boundary failures without an implementation-derived expected serializer |
| History | missing, duplicate, unused, multi-owned, substring-expanded, digest-drifted, and notice-drifted entries block |
| Negative/planned controls | legitimate scoped negatives, exact mutation fixtures, and adjacent structured planned markers pass without broad exemptions |
| Release boundary | standalone semantic report may PASS; `check-governance`/`check-release` remain non-green with `IDENTITY_ATTESTATION_PENDING` |
| Packet handoff and scope | packet contains no ADR production or Design Review command; it cites the latest terminal FIX-201 Design result with `unresolved_blockers=0`; its allowed scope contains exactly the 18 exclusive plus seven shared product paths, including `verify_workflow.py`, and excludes ADR-012 |
| Rollback | a compensating rollback fixture retains all 18 truth surfaces, NOT_MET/PARTIAL authority, historical notices, and mandatory blockers; packet scan rejects a standalone/simple revert, frozen-candidate restore, or any real-worktree/index mechanical-revert intermediate state, including one followed by same-transaction reapplication |
| Regression | FIX-195 migration and FIX-196 health suites remain green; existing known unrelated baseline failures are reported, not relabeled |
| Performance | three serial real-repository semantic scans after one warm-up: median <5 s, peak RSS <256 MiB; basis is the prior complete-corpus isolated medians 3.973 s/179.86 MiB and 4.549 s/191.98 MiB from FIX-197 QA R1/R2 |
| Reviews | latest terminal independent FIX-201 Design Review result from the new chain beginning at `REVIEW-FIX-201-DESIGN-R0`, plus fresh FIX-199 Code Review R0 and QA R0; every chain has `unresolved_blockers=0` before commit/push |

### FIX-200 acceptance

| Area | Required evidence |
| --- | --- |
| Root source bindings | release mode binds product/plugin to explicit same-repo or external-repo Git OIDs/prefixes and host to an immutable all-files snapshot; ignored host files and external plugin_home are present in both inventories |
| Root identity | product/plugin/host divergence passes when valid; missing/duplicate binding, root symlink, junction, reparse, lexical alias, and unexpected physical alias block |
| Loaded controls | mutating the actually loaded plugin_home policy or authority after initial inventory blocks final comparison |
| Required files | directory/special-file substitution, missing inventory membership, content drift, and wrong root owner block |
| N/A | uninitialized installed host returns `NOT_APPLICABLE`, `healthy=false`, `authorized=false`, non-PASS display, and non-authorizing exit/result semantics |
| Independence | import/reference test proves attestor does not import/call scanner or a shared accounting helper; intentional scanner-vs-attestor binding, path, byte, digest, context, and unit-count mismatches block |
| Accounting | both implementations independently pass `loop-semantic-accounting/v1` golden NDJSON/digests and match contract/count/payload-bytes/record-digest/aggregate-digest for real and divergent-root fixtures |
| Final candidate | every staged-index Git binding satisfies the sole legal index-to-candidate-tree transition: same role, `GitRepositoryIdentity`, selected prefix/tree, complete materialized records, scoped bytes, and digests; every other kind transition and every post-attestation file/control/required-path mutation blocks as mismatch or stale |
| Scoped rehearsal | the execution packet runs both mandatory `check-loop-runtime-claims --require-identity` commands as one atomic write-then-compare rehearsal in disposable roots without 0.66.1 release docs; the second consumes the first artifact and a fresh snapshot; stale FIX-200 attestation is rejected; full `check-release` is not invoked |
| Aggregate gate | pending blocker is removed only when semantic and identity verdicts are both PASS; N/A/PENDING/BLOCKED never authorize release |
| Rollback | a compensating FIX-200 rollback reproduces the reviewed FIX-199 shared-file bytes and exact pending blocker before validation; all FIX-200 attestations are removed from authorization lookup, become stale, and cannot authorize release; simple/unconditional revert is rejected |
| Regression | focused scanner, attestor, verify adapter, manifest, cross-reference, FIX-195, and FIX-196 suites pass; release-doc/version gate remains deferred to REL-058 |
| Performance PoC gate | before FIX-200 integration can be approved, run one warm-up plus five serial scanner-only, attestor-only, and aggregate full-corpus runs with stage timings and peak RSS; record an independently reviewed numeric aggregate budget from those measurements and keep `PERFORMANCE_BUDGET_PENDING` until then; no prefix/cache/shared enumerator may hide changed files |
| Reviews | fresh independent Design Review R0, Code Review R0, and QA R0 for FIX-200; `unresolved_blockers=0` before commit/push |

Correctness failures override performance success. The prior scanner already
used 4.549 s median and 191.98 MiB in isolated QA R2, so imposing the same
<5 s/<256 MiB aggregate limit before measuring the new independent pass is not
factually supported. The PoC gate is mandatory and cannot be satisfied by
skipping candidates, caching unchanged prefixes, or sharing the scanner
enumerator/accounting implementation with the attestor.

## Review Plan

### FIX-201 terminal-design handoff to FIX-199 implementation

1. FIX-201 owns this ADR-only recovery revision. It does not modify product
   code and does not continue `REVIEW-FIX-199-DESIGN-R2` as R3.
2. An independent Design Reviewer starts a new chain at
   `REVIEW-FIX-201-DESIGN-R0` and reviews the four FIX-201 resolution rows. If
   rework is required, rounds advance only within the FIX-201 chain; only its
   latest terminal result is authoritative.
3. After that terminal result has `unresolved_blockers=0`, the Coordinator
   synchronizes the FIX-199 packet with this ADR, records the terminal review
   evidence, removes every ADR-production/Design-Review command, and validates
   the exact 25-path scope and compensating-only rollback text.
4. Only then may Governance Developer implement the FIX-199 product ownership;
   the Developer does not edit ADR-012 and does not start a Design Review.
5. A fresh independent Code Reviewer R0 reviews implementation and staged path
   scope. A fresh independent QA R0 executes the FIX-199 matrix and performance
   budget.
6. Coordinator commits/pushes only when the latest FIX-201 Design terminal and
   both fresh FIX-199 implementation reviews report
   `unresolved_blockers=0`.

### FIX-200 R0 chain

1. After the FIX-199 commit/push, a fresh independent Design Reviewer R0
   reviews the actual committed interfaces, attestor independence, root model,
   and final-candidate protocol.
2. Only after that FIX-200 Design R0 passes, Governance Developer implements
   only FIX-200 product ownership and does not edit ADR-012.
3. A different independent Code Reviewer R0 reviews the implementation,
   dependency boundary, and staged-index identity.
4. Independent QA R0 executes the FIX-200 matrix and final-candidate rehearsal.
5. Coordinator commits/pushes only when all three report
   `unresolved_blockers=0`.

Architect, Developer, Code Reviewer, Design Reviewer, and QA evidence remain
separate. This ADR is not a substitute for either independent review chain.

## Rollback

### FIX-199 rollback

A wholesale or standalone revert is forbidden, even as a nominally temporary
rollback step or an intermediate state in one unpushed transaction, because it
can restore known-false active runtime wording. The FIX-199 execution packet's
only rollback contract is the following truth-preserving compensating
transaction:

1. create a new compensating change on top of FIX-199;
2. keep all 18 truth-correction surfaces, packaged NOT_MET/PARTIAL authority,
   exact historical notices, and `IDENTITY_ATTESTATION_PENDING` byte-identical
   or semantically stricter than the reviewed FIX-199 state;
3. disable/revert only defective semantic-enforcement internals and add
   `SEMANTIC_ENFORCEMENT_ROLLBACK_PENDING` if the scanner cannot still prove a
   complete semantic PASS;
4. prove `check-governance`, `check-loop-runtime-claims`, and every release
   aggregation path remain non-green, then obtain independent review before
   commit/push.

Mechanical inverse calculation, simple `git revert FIX-199`, and frozen-
candidate/pre-FIX-199 restoration may occur only offline in a disposable tree
that is not the real worktree and does not share its index. They are diagnostic
hunk inputs only. Neither the real worktree nor its index may enter any
mechanical-revert or frozen-candidate state, even if the packet promises to
reapply protections before commit, and whole files from that disposable state
MUST NOT be copied back. Every real-worktree/index edit must directly produce
the compensating state described above. A generated execution packet
containing a real-worktree mechanical inverse, simple revert, restore, or
same-transaction revert-then-reapply instruction is invalid and blocks
dispatch. REL-058 remains blocked throughout.

### FIX-200 rollback

FIX-200 rollback is a compensating transaction whose target bytes are the
reviewed FIX-199 commit, not a generic inverse patch. Before the rollback can
be validated or committed it MUST:

1. reproduce byte-for-byte the reviewed FIX-199 state for all seven shared
   files and prove the 18 FIX-199-exclusive truth surfaces are unchanged;
2. restore the exact reviewed `IDENTITY_ATTESTATION_PENDING` blocker and keep
   every governance/release aggregation path non-green;
3. mark every FIX-200 attestation stale, move it outside the authorization
   lookup set, and prove compare/release paths reject it as
   `CANDIDATE_ATTESTATION_STALE`;
4. retain packaged NOT_MET/PARTIAL authority, historical notices, open risks,
   and REL-058 blocking.

A simple or unconditional `git revert FIX-200` is not the rollback contract.
It may be used only in a disposable tree to calculate candidate inverse hunks.
If exact reviewed FIX-199 bytes and blocker state cannot be reconstructed, the
rollback remains blocked and no validation, commit, push, release, or risk
closure is allowed. Rollback never changes historical source records or the
NOT_MET/PARTIAL authority.

## Non-Functional Requirements

### Reliability and security

- Every unknown, ambiguous, parse, root, required-file, control, inventory,
  accounting, and final-candidate error is typed and release-blocking.
- No partial/prefix PASS, fallback parser, unknown-as-negative, provenance
  allowlist, or same-enumerator independence claim exists.
- Reports identify root owner, normalized path, locator when available,
  stage, expected/actual identity, authority version, and source identity.

### Performance

- ADR-011 limits remain: at most 1,500 candidates, 24 MiB candidate bytes,
  300,000 semantic units, 32 MiB semantic payload, 2 MiB default per file.
- FIX-199 retains a <5 second median and <256 MiB peak RSS because complete
  isolated FIX-197 QA runs measured 3.973 s/179.86 MiB and
  4.549 s/191.98 MiB on the same corpus and host class.
- FIX-200 has no invented aggregate threshold. Its first implementation stage
  is the mandatory scanner/attestor/comparison PoC described in acceptance;
  the independently reviewed measurements set the numeric aggregate budget
  before integration review, and `PERFORMANCE_BUDGET_PENDING` blocks earlier
  completion.
- Independent enumeration may optimize traversal and count-only extraction,
  but may not reuse scanner results or skip canonicalization.

### Maintainability

- Semantic policy remains in one scanner; identity comparison remains in one
  independent attestor.
- Root source, semantic accounting, and report schemas are separately
  versioned immutable dataclasses/JSON and compared at the adapter boundary.
- New claim nouns do not require taxonomy edits merely to be detected; policy
  edits are required only to authorize a reviewed claim class.

## Blue-Team Challenges

| ID | Challenge | Failure chain | Required mitigation | Residual risk |
| --- | --- | --- | --- | --- |
| BT-012-1 | A new noun or reversed sentence order avoids all known subject regexes. | finite noun list -> no relation -> structural PASS | Predicate/domain-anchor analysis creates `unknown_loop_capability` independent of noun and word order; three-language mutation corpus | Medium: new predicate vocabulary still requires corpus growth, but ambiguous state blocks |
| BT-012-2 | A maintainer places an active claim under Triggers, in inline code, in a diagnostic string, or inside a forged policy JSON. | provenance/schema shape -> structural exemption -> false PASS | Relations are evaluated before provenance; only exact path+schema+field or proven isolated negative fixture may be structural | Low after R0 adversarial coverage |
| BT-012-3 | The policy loaded from a divergent plugin_home changes after scan while product_root inventory remains stable. | loaded control outside inventory -> final digest unchanged -> false authorization | Both inventories include plugin_home controls; scanner consumes snapshot bytes; final comparison checks policy and authority digests | Low; platform file-identity variance is reported and tested |
| BT-012-4 | The release is attested, then a release document changes or an unrelated tree is presented as the candidate merely because its source kind changed from index to tree. | stale/ambiguous transition -> later candidate accepted | The sole index-to-candidate-tree transition requires the same role, repository identity, selected prefix/tree, complete records, scoped bytes, and digests; any mutation or other kind transition fails closed and REL-058 regenerates the attestation | Low if release workflow supplies the exact candidate ref |
| BT-012-5 | Rolling back FIX-200 accidentally removes all release blocking or rolling back FIX-199 restores active overclaims. | broad/simple revert -> healthy incomplete gate / false wording | Both rollbacks are compensating transactions; FIX-199 never restores frozen/pre-fix bytes, while FIX-200 proves reviewed FIX-199 bytes, pending blocker, and attestation invalidation before validation | Medium: rollback procedure requires reviewer enforcement |
| BT-012-6 | The independent attestor imports scanner helpers, so a common bug makes both digests agree. | shared implementation -> correlated false PASS | Separate module, no scanner import/call, import-boundary test, injected differential mutations | Low; both implementations still share the written contract and stdlib |
| BT-012-7 | One Git source omits ignored host governance files, cannot address an external plugin repository, or compares a repository field absent from the portable tuple. | single/contradictory source identity -> incomplete role inventory or non-portable equality | Exactly one per-root binding; product/plugin use the same `loop-git-repository-tree/v1` identity in portable tuples and equality; host uses immutable all-files snapshot; same-repo and external-repo fixtures | Low after divergent-repository, identical-tree, and ignored-file fixtures |
| BT-012-8 | `frobnicated` appears under a Loop heading, JSON key, or Python binding but is unknown and separated from the domain anchor. | local-token scan -> no known predicate/relation -> structural PASS | Deterministic context propagation plus typed unknown predicate/polarity/subject/domain ambiguity in all three languages | Medium: new container syntax requires a contract version, never silent fallback |
| BT-012-9 | Scanner and attestor both report the same count while segmenting tables, strings, or JSON keys differently. | count-only equality -> different semantic units -> false agreement | Versioned v1 boundaries, exact context records, canonical NDJSON/digests, independently embedded golden expectations | Low; contract changes require a new version and vectors |
| BT-012-10 | FIX-200 runs full 0.66.1 release checks, or runs only one scoped identity command, and is forced either to create release docs or accept an unproved comparison. | task/release boundary leak or half-rehearsal -> false blocker / missing final equality | The write and compare `check-loop-runtime-claims --require-identity` commands are one mandatory atomic acceptance command; `check-release` is deferred to REL-058 | Low after packet-command equality and disposable-root rehearsal |
| BT-012-11 | A generic execution-packet rollback performs a real-worktree revert, promises same-transaction reapplication, and briefly exposes known-false wording or reusable stale attestations. | temporary mechanical state -> false truth surfaces / stale authorization | Real worktree/index is compensating-only at every intermediate state; mechanical inverses, simple reverts, and frozen restores stay in isolated disposable trees and cannot be copied back wholesale | Low after packet validation and independent rollback review |
| BT-012-12 | A Developer edits ADR-012 inside FIX-199/FIX-200 or follows stale R0/R2 wording after the original design chain fused. | architecture prerequisite enters implementation scope -> producer self-changes contract / wrong review authority | ADR-012 is excluded from both scopes and staged sets; FIX-199 consumes the latest terminal FIX-201 Design result and contains no Design command, while FIX-200 begins fresh Design R0 only after the FIX-199 commit | Low after staged-path, packet-field, and review-lineage checks |
| BT-012-13 | FIX-200 inherits the scanner's <5 s/<256 MiB limit before the independent pass is measured. | invented aggregate budget -> skipped work, shared cache, or unreviewable failure | `PERFORMANCE_BUDGET_PENDING` blocks integration; mandatory PoC measures scanner-only, attestor-only, and aggregate runs before an independent reviewer records a numeric budget | Medium until the PoC completes |

## R1 Blocker Resolution Map

`REVIEW-FIX-199-DESIGN-R1.md` is the finding authority for this map. R0 B2
remains resolved by the open-vocabulary/context contract and had no R1
blocker; the seven rows below are the complete unresolved R1 set.

| R1 blocker | R2 resolution in ADR-012 | Acceptance proof | Status |
| --- | --- | --- | --- |
| 1 / R0 B1 partial: equality requires repository identity that portable Git identity omitted | `Three-root inventory` defines `GitRepositoryIdentity(loop-git-repository-tree/v1)` from object format plus exact repository root tree OID and includes that same object in `PortableGitSourceIdentity`; every equality and attestation comparison uses that exact definition for same-repo and external-repo bindings | same-repository/different-prefix, external-repository, byte-identical separate repository, repository-root drift, prefix drift, and selected-tree drift fixtures compare tuple plus records/bytes | RESOLVED |
| 2 / R0 B3: golden vectors lack literal normative NDJSON/SHA-256 and fixed locator/context types | `loop-semantic-accounting/v1` now fixes exact record, locator, and uniform context JSON schemas, including null members and ordering, and embeds literal UTF-8 NDJSON bytes, byte lengths, payload counts, and SHA-256 constants for all four vectors | independently hash the ADR literals to the three positive digests and empty error digest; both production test modules embed constants without production-derived expected builders | RESOLVED |
| 3 / R0 B4 partial: packet acceptance does not require both scoped rehearsals | `FIX-200 scoped attestation rehearsal` makes the displayed write and compare `--require-identity` invocations one atomic acceptance command; the focused unit test is explicitly additional evidence only | execution-packet command equality plus disposable repositories prove both commands run in order, the second consumes the first artifact/fresh snapshot, and full `check-release` is absent | RESOLVED |
| 4 / R0 B5: another FIX-199 packet field restores the frozen candidate | `FIX-199 rollback` forbids restoration of the frozen candidate, pre-FIX-199 bytes, real-worktree mechanical revert, or simple revert; preserved bundles are hunk evidence only and the only rollback is truth-preserving compensation | packet-field scan rejects forbidden phrases/actions; rollback fixture preserves 18 truth surfaces, NOT_MET/PARTIAL authority, notices, pending blockers, and non-green gates | RESOLVED |
| 5 / new: FIX-200 packet hardcodes aggregate <5 s/<256 MiB | FIX-200 has no numeric aggregate budget before measurement; one warm-up plus five scanner-only, attestor-only, and aggregate runs are mandatory, and `PERFORMANCE_BUDGET_PENDING` blocks integration until independent review records the budget | packet budget equals the ADR PoC contract; evidence includes stage timings, peak RSS, complete inventories, and reviewer-recorded numeric budget after measurement | RESOLVED |
| 6 / new: ADR is in both Developer scopes and FIX-199 review wording is stale | `File Ownership` excludes ADR-012 from both allowed scopes, staged sets, implementation commits, and rollbacks; FIX-199 uses the latest terminal FIX-201 Design result plus fresh Code/QA R0, while FIX-200 starts fresh Design R0 after the FIX-199 commit | staged-path and packet-field checks exclude ADR-012 and Design commands; review lineage proves FIX-201 terminal Design -> fresh FIX-199 Code/QA and FIX-199 commit -> fresh FIX-200 Design/Code/QA | RESOLVED |
| 7 / new: FIX-200 permits unconditional simple revert | `FIX-200 rollback` is a compensating transaction that must reproduce reviewed FIX-199 shared-file bytes, preserve exclusive truth surfaces, restore exact `IDENTITY_ATTESTATION_PENDING`, invalidate/remove all FIX-200 attestations from authorization lookup, and keep REL-058 blocked | rollback fixture proves byte equality to reviewed FIX-199, pending blocker equality, stale-attestation rejection, non-green aggregate gates, and rejection of a simple/unconditional revert packet | RESOLVED |

## FIX-201 Terminal Blocker Resolution Map

`REVIEW-FIX-199-DESIGN-R2` and EVD-725 are the immutable finding authority for
this map. FIX-201 resolves only these four findings and begins a new independent
review chain; it does not convert the prior R2 result to PASS.

| FIX-201 blocker | Normative resolution in ADR-012 | Required acceptance evidence | Status |
| --- | --- | --- | --- |
| 1. FIX-199 packet still generates ADR-012 and starts stale Design R0 | `Decision` and `Review Plan` make FIX-201 the ADR-only producer and require FIX-199 to consume the latest terminal result from the new chain beginning at `REVIEW-FIX-201-DESIGN-R0`; FIX-199 MUST contain no ADR create/update or Design Review command | packet-field scan shows zero ADR production/edit commands and zero Design Review start/replay commands; required evidence cites the latest terminal FIX-201 review with `unresolved_blockers=0`; staged scope excludes ADR-012 | RESOLVED_PENDING_INDEPENDENT_REVIEW |
| 2. FIX-199 scope omits the pending-blocker adapter | `File Ownership And Serial Takeover` requires exactly 18 exclusive plus seven shared product paths and explicitly makes `skills/software-project-governance/infra/verify_workflow.py` mandatory for non-bypassable `IDENTITY_ATTESTATION_PENDING` | packet scope equality proves all 25 product paths are present, `verify_workflow.py` is included, ADR-012 is absent, and no open-ended path grants extra scope; focused adapter evidence proves governance/release aggregation stays non-green | RESOLVED_PENDING_INDEPENDENT_REVIEW |
| 3. index-to-tree replacement conflicts with unchanged binding kinds | `Persisted final-candidate identity` defines the sole legal `GitIndexRootSource -> GitTreeRootSource(candidate_commit)` transition as same role, exact `GitRepositoryIdentity`, selected prefix/tree, complete materialized records, scoped bytes, and digests; source kind may change only under this relation while portable binding equality remains exact | positive staged-index/candidate-commit fixture proves all five equivalence conditions; negative fixtures mutate repository identity, prefix, selected/root tree, mode/path/blob/raw byte/digest and exercise every other kind transition, each producing a typed blocking mismatch | RESOLVED_PENDING_INDEPENDENT_REVIEW |
| 4. packet permits real-worktree mechanical revert | `FIX-199 rollback` requires every real-worktree/index intermediate state to be compensating-only; mechanical inverse, simple revert, and frozen/pre-FIX-199 restore are limited to an isolated disposable tree and cannot be copied back wholesale | packet-field scan rejects real-worktree revert/restore and same-transaction revert-then-reapply wording; rollback fixture preserves all 18 truth surfaces, NOT_MET/PARTIAL authority, notices, `IDENTITY_ATTESTATION_PENDING`, and non-green gates without materializing a mechanical inverse in the real index | RESOLVED_PENDING_INDEPENDENT_REVIEW |

## Consequences And Impact

### Positive

- Semantic and identity failures receive separate owners, acceptance evidence,
  commits, and rollback paths.
- The known incomplete interval remains visibly release-blocked.
- Provenance cannot silently become policy authority.
- The actually loaded controls and final candidate become part of the reviewed
  identity rather than incidental filesystem reads.
- REL-058 receives an explicit repeatable final-candidate protocol.

### Costs

- Seven files are edited in two serial commits, increasing staging discipline.
- Independent inventory/count-only extraction adds implementation and runtime
  cost by design.
- The FIX-200 execution packet already contains the two attestor leaf/test
  paths and must retain them through dispatch.
- The release workflow must persist and compare an attestation for every final
  candidate change.

### Unchanged boundaries

- Loop Engineering remains experimental scaffolding.
- Runtime activation and migration validity remain NOT_MET.
- RISK-037 and RISK-042 remain open.
- REL-058 remains blocked until FIX-199, FIX-200, and independent Release
  Review all pass.

## Follow-Up Actions

1. Independent Design Reviewer starts `REVIEW-FIX-201-DESIGN-R0` and verifies
   the four FIX-201 terminal blocker rows while preserving the previously
   passed R2 facts. This ADR authorizes no implementation or release by itself.
2. After the latest terminal FIX-201 result has `unresolved_blockers=0`, the
   Coordinator replaces the FIX-199 packet fields with the exact reviewed
   handoff, 25-path scope, evidence, commands, done definition, and
   compensating-only rollback contract. Packet validation must exclude ADR-012
   and every Design production/review command before Developer dispatch.
3. Governance Developer then executes FIX-199 product scope only, followed by
   fresh independent Code Review R0 and QA R0, then one scoped commit/push.
4. Coordinator releases shared locks only after that FIX-199 commit/push and
   dispatches the fresh FIX-200 Design Review R0 against the committed FIX-199
   interfaces.
5. Governance Developer executes FIX-200, followed by independent Code Review
   R0 and QA R0, staged-index attestation, final commit comparison, and one
   scoped commit/push.
6. Release Agent recalibrates REL-058, creates a new final-candidate
   attestation, obtains independent Release Review, and only then performs any
   version/tag/push release action.
