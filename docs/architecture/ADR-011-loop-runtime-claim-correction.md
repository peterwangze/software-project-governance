# ADR-011: Loop Runtime Claim Correction

- Status: PROPOSED / FIX-198_ARCH_R1_BASELINE_REVISION / READY_FOR_DESIGN_REVIEW_R1
- Date: 2026-07-12
- Task: FIX-197
- Authority: AUDIT-133, EVD-707, DEC-104

## Context

The 0.65.0 release delivered Loop Engineering declarations, helpers, migration scaffolding, rollup views, and review-role wording. AUDIT-133 subsequently proved that the production lifecycle remains classic active/default, core loop transition APIs have no production callers, migration output is rejected by the canonical validator, and external effectiveness is not proven.

Current authoritative classification is:

- Loop Engineering: experimental scaffolding;
- runtime activation: NOT_MET;
- migration validity: NOT_MET;
- criteria 2/3/4/5/6: PARTIAL;
- criterion 7: NOT_PROVEN;
- criterion 8: MET-NARROW;
- RISK-037 and RISK-042: open.

Historical release commits, tags, manifests, decisions, evidence rows, test results, and command output remain immutable facts. Their current interpretation must be superseded without rewriting what happened.

## Decision

Adopt four coordinated controls for 0.66.1:

1. Active instruction downgrade: seven review SKILL files and the shared loop-role mapping retain loop vocabulary as a target role mapping, but only Coordinator M7.4 rework/re-review and Check 30 review-chain behavior may be described as currently executable. Generic persisted back-edge, flow-unit loop_count, tier fuse, PARO transition, and automatic escalation remain planned 0.68.0 behavior.
2. Append-only correction: historical CHANGELOG/release/ADR/validation text and old EVD/DEC rows are not deleted or rewritten. Shipped historical documents receive a uniquely parseable superseding notice that points to AUDIT-133, EVD-707, and DEC-104.
3. Exact historical allowlist: historical affirmative claims are permitted only by normalized path, claim id, exact line/block digest, occurrence count, and superseding mode. Directory/path globs and global CHANGELOG/release-doc exclusions are forbidden.
4. Blocking claim gate: a stdlib leaf scanner validates active documents, notices, historical fingerprints, and hot authority references. `verify_workflow.py` is a thin adapter and release-gate integration point. Missing policy, digest drift, changed occurrence count, absent/duplicate/contradictory notice, unknown affirmative claim, or missing authority is a failure.

## Dependency Direction

```text
core/loop-runtime-claim-allowlist.json
  -> infra/checks/loop_runtime_claims.py
  -> verify_workflow thin CLI/release adapter
  -> check-governance and release gate
```

Documents and SKILL files are scanner inputs and do not import implementation modules. The claim leaf does not import `verify_workflow.py` or `loop_migration.py`.

## Scanner Context And Authority

The scanner receives an explicit immutable context object. It never infers the host facts root from a product file path.

```text
ClaimScanContext(
  product_root,   # installed package/repository product root; required
  plugin_home,    # skills/software-project-governance; required
  host_root,      # governed project root; optional and explicit
  scan_mode       # product_release | installed_host
)
```

- `product_root` owns shipped review SKILL files, `project/CHANGELOG.md`, `docs/`, and release surfaces. The verify adapter passes its resolved package root; failure to resolve it is BLOCKED.
- `plugin_home` owns packaged policy and authority data under `core/`. It is resolved by `resolve_entry.py`; divergence from `product_root` is expected and tested.
- `host_root` owns only `.governance/plan-tracker.md`, `session-snapshot.md`, `evidence-log.md`, and `risk-log.md`. It comes from explicit CLI input or `resolve_entry.host_project_root`. It is never replaced by `plugin_home` or `product_root`.
- `product_release` requires repository hot governance and scans it using an explicitly supplied repository host root.
- `installed_host` scans host hot governance only when governance is initialized. An uninitialized host is `NOT_APPLICABLE`, not healthy and not a missing-product-authority failure.

Installed hosts do not need repository-local EVD/DEC files. A shipped, versioned `core/loop-runtime-claim-authority.json` contains the effective classification, `authority_ids=[AUDIT-133,EVD-707,DEC-104]`, open risks, effective version, and source-record hashes. Product release validation additionally proves those source records exist and match the packaged hashes. Installed validation consumes the packaged authority and must not look for product evidence in host governance.

## Required Surfaces

- seven `skills/*-review/SKILL.md` review role sections;
- `skills/software-project-governance/references/loop-role-mapping.md`;
- `skills/software-project-governance/infra/loop_migration.py` comments only;
- append-only notices in the 0.65.0 CHANGELOG/release/architecture/shitu validation surfaces;
- `project/CHANGELOG.md` new 0.66.1 correction;
- claim policy, leaf scanner, thin adapter, focused tests, manifest/tool registration;
- mutable hot governance interpretation and a new superseding evidence row.

## Historical Fingerprint Contract

`core/loop-runtime-claim-allowlist.json` has `schema_version: 1.0`, an exact `input_manifest`, an exact `historical_claims` list, and a `notice_schema_version`. Each historical entry uses:

```json
{
  "normalized_relative_path": "...",
  "claim_id": "...",
  "locator": {"kind": "line|heading_block|record|fence", "selector": "kind-specific", "ordinal": 1},
  "locator_sha256": "...",
  "claim_payload_sha256": "...",
  "occurrence_count": 1,
  "superseding_mode": "same_file|hot_evidence"
}
```

Canonicalization is deterministic:

- reject symlinks, `..`, absolute paths, path aliases, duplicate normalized paths, and files outside their owning root;
- relative paths use case-sensitive POSIX separators; Windows case collisions fail;
- decode strict UTF-8, remove one UTF-8 BOM, normalize CRLF/CR to LF, normalize Unicode to NFC, then hash UTF-8 bytes;
- `line` requires `line_number` and hashes that normalized logical line;
- `heading_block` requires exact normalized `heading_text`, `heading_level`, and `ordinal`, and hashes the heading plus content up to the next equal/higher heading;
- `fence` requires exact `language`, optional exact `label`, and `ordinal`, and hashes the complete fence including delimiter lines;
- `record` requires exact `record_id`, `table_heading`, and `ordinal`, and hashes one normalized pipe-table row;
- locator resolution must return exactly one entity. Zero or multiple matches fail;
- `locator_sha256` hashes the resolved canonical entity. `claim_payload_sha256` hashes the exact canonical affirmative clause matched inside that entity;
- `occurrence_count` counts exact `claim_payload_sha256` matches inside the resolved locator. It does not count the external policy `claim_id`, so immutable historical text does not need embedded policy ids.

Every corrected shipped document carries exactly one machine record:

```html
<!-- loop-runtime-superseding:{"schema_version":"1.0","notice_id":"LRC-...","effective_version":"0.66.1","supersedes_claim_ids":["..."],"authority_ids":["AUDIT-133","EVD-707","DEC-104"],"classification":{"runtime_activation":"NOT_MET","migration_validity":"NOT_MET","criteria_2_3_4_5_6":"PARTIAL","criterion_7":"NOT_PROVEN","criterion_8":"MET-NARROW","capability":"experimental_scaffolding"},"open_risks":["RISK-037","RISK-042"]} -->
```

The JSON object must occupy one comment, parse exactly once, use the exact schema and enum values, bind every `supersedes_claim_id` to a historical entry in that file, and contain no orphan or duplicate ids. Human-readable correction text may follow but cannot satisfy the machine gate by token aggregation.

`same_file` requires the bound notice. `hot_evidence` requires the packaged authority plus one current superseding EVD id recorded in policy. New claims adjacent to an allowlisted claim are not covered.

Policy changes are never generated from current files. There is no `--accept-current`, refresh, or auto-update path. Adding or changing a fingerprint requires independent Code Review and Design Review evidence. Duplicate claim ids, policy drift, orphan notices, unused allowlist entries, or changed input classification fail closed.

## Input Closure

### Closure alternatives

The input-closure design was evaluated against four requirements: exhaustive
enumeration, no false pass for a new affirmative claim, no false block for a
legitimate negative fixture or structural declaration, and no truncation.

1. **Cheap-filter-first plus exact file inventory.** Reject. The old vocabulary
   identified approximately 133 surfaces, while the policy listed roughly 25.
   The count changes when vocabulary changes and includes negative fixtures,
   historical facts, registry declarations, and validator tests. Classifying
   every byte match as an unknown surface either blocks the current repository
   or encourages broad exceptions.
2. **Classify all current vocabulary-matching files.** Reject. This can be made
   correct for one snapshot, but it makes file membership rather than semantic
   meaning the authority. A harmless new negative fixture requires policy
   churn, while a new affirmative phrase using unanticipated vocabulary can
   avoid discovery.
3. **Exhaustive semantic-first enumeration and classification.** Adopt. Every
   Markdown, Python, and JSON candidate is parsed. Safe language extraction and
   semantic claim classification happen before an unknown-surface decision.
   Only an actual affirmative claim-bearing semantic unit that has no policy
   classification becomes `UNCLASSIFIED_SURFACE`.

The cheap vocabulary probe remains optional diagnostic telemetry. It never
selects files, suppresses parsing, assigns a classification, or determines a
pass/fail result.

### Exhaustive candidate enumeration

Candidate enumeration recursively walks `docs/`, `project/`, and `skills/`
under `product_root` and the four declared hot-state files under `host_root`.
Every regular `.md`, `.py`, and `.json` file is included, sorted by normalized
root owner and case-sensitive POSIX relative path. There are no ignored
directories, matching-file shortcuts, or sampling rules. Symlinks, traversal,
case collisions, aliases, unreadable files, and an unknown extension selected
by policy are blocking path/input errors.

The policy `input_manifest` remains an exact inventory of **required authority
surfaces**, not an allowlist of every repository file. It enumerates files that
must exist or carry a known classification, notice, fingerprint, or hot
authority responsibility. A candidate absent from `input_manifest` is still
parsed completely. Its absence from the manifest is not an error unless it
contains an affirmative claim unit that cannot be classified by the semantic
policy.

The initial required paths remain:

```text
product_root:skills/code-review/SKILL.md
product_root:skills/design-review/SKILL.md
product_root:skills/release-review/SKILL.md
product_root:skills/requirement-review/SKILL.md
product_root:skills/retro-review/SKILL.md
product_root:skills/tech-review/SKILL.md
product_root:skills/test-review/SKILL.md
product_root:skills/software-project-governance/references/loop-role-mapping.md
product_root:skills/software-project-governance/infra/loop_migration.py
product_root:skills/software-project-governance/core/loop-engineering-registry.json
product_root:skills/software-project-governance/infra/tests/test_loop_migration.py
product_root:skills/software-project-governance/infra/tests/test_loop_runtime_claims.py
product_root:project/CHANGELOG.md
product_root:docs/release/feature-flags-0.65.0.md
product_root:docs/release/release-checklist-0.65.0.md
product_root:docs/release/rollback-plan-0.65.0.md
product_root:docs/requirements/loop-engineering-architecture-0.65.0-proposed.md
product_root:docs/requirements/loop-engineering-implementation-breakdown-0.65.0.md
product_root:docs/requirements/shitu-loop-engineering-validation-0.65.0.md
product_root:docs/requirements/loop-engineering-post-implementation-audit-0.66.0.md
product_root:docs/migration/loop-engineering-runtime-contract-migration-0.66.1.md
host_root:.governance/plan-tracker.md
host_root:.governance/session-snapshot.md
host_root:.governance/evidence-log.md
host_root:.governance/risk-log.md
```

The implementation creates the new test path before required-surface
validation. Every listed path has a declared `required` flag; missing required
paths fail. No required path or newly enumerated candidate may be skipped.

### Unified semantic-unit schema

All three language extractors emit the same immutable record before policy
classification:

```text
SemanticUnit(
  root_owner,             # product_root | plugin_home | host_root
  normalized_path,
  language,               # markdown | python | json
  locator,                # language-specific stable locator
  source_span,            # start/end line and column or JSON pointer
  raw_text_sha256,
  canonical_text,
  unit_kind,              # prose | structured_assertion | fixture | data | quoted_output
  provenance,             # heading/AST parent/JSON pointer/fence context
  subject,
  predicate,
  polarity,               # affirmative | negative | none | ambiguous
  temporal_scope,         # current | historical | future_planned | unspecified
  extraction_state        # extracted | ambiguous | parse_error | unknown_language
)
```

Extractors may provide hints, but they do not grant an allowlist result. The
classifier consumes the complete unit plus policy and authority. Every output
unit retains a source locator so a finding is reproducible.

### Deterministic language extraction

- **Markdown:** parse headings, prose sentences, list items, individual table
  cells, HTML comments, and fenced blocks. A fence is parsed using its declared
  language when supported. Unlabelled or unsupported fences that contain a
  possible subject/predicate pair become `ambiguous`; they are not ignored.
  Quoted historical command output is emitted as `quoted_output` and still
  requires an exact historical fingerprint when it contains an affirmative
  claim.
- **Python:** use `tokenize` plus `ast` and emit comments, module/class/function
  docstrings, and every string literal. Regex sources, enum/id collections,
  parser fixtures, user-facing messages, and assertions are distinguished by
  AST provenance, not by directory exclusion. A literal inside a `test_*`
  function is `fixture` only when its value flows into a call/assertion/fixture
  object inside that test; a standalone expression, exported constant, module
  docstring, or comment remains normal semantic input. The legitimate negative
  strings in `infra/tests/test_verify_workflow.py` therefore classify as test
  fixtures rather than product assertions, while a new affirmative module
  comment or docstring remains claim-bearing.
- **JSON:** parse the complete document and emit every scalar with its JSON
  pointer and parent-key context. Keys, enum identifiers, regex fragments,
  numeric fuse limits, and schema metadata may classify as structural data.
  Boolean or enum pairs such as `runtime_activation: true` are emitted as
  `structured_assertion`, not hidden as data. Natural-language string values
  are classified regardless of key name. Policy and packaged authority JSON
  additionally pass their versioned schemas.

Strict UTF-8, syntax parsing, and complete-file consumption are mandatory. A
parser cannot downgrade to a byte scan after failure.

### Semantic-first pipeline

| Stage | Input | Output | Blocking errors |
| --- | --- | --- | --- |
| 1. Enumerate | resolved roots and extensions | complete ordered `CandidateFile[]`, total count/bytes | root failure, traversal, symlink, collision, unreadable metadata, candidate budget overflow |
| 2. Decode/parse | every candidate byte stream | complete syntax tree/token stream | strict UTF-8 failure, `PARSE_ERROR`, `UNKNOWN_LANGUAGE`, per-file/parsed-byte overflow |
| 3. Extract | complete parsed representation | `SemanticUnit[]` using the unified schema | locator collision, incomplete consumption, `AMBIGUOUS_EXTRACTION`, semantic-unit budget overflow |
| 4. Classify safety semantics | every semantic unit | deterministic semantic state below | contradictory polarity, unknown subject/predicate with claim potential, invalid temporal scope |
| 5. Apply authority/policy | actual claim-bearing units plus exact fingerprints/notices | allowed result or typed finding | missing authority, fingerprint drift, unsupported current claim, unclassified affirmative claim |
| 6. Aggregate | complete candidate/unit/finding streams | one report with counts and no partial verdict | any prior blocking error; no prefix may be reported as PASS |

The scanner never creates `UNCLASSIFIED_SURFACE` at stages 1-3 merely because
a file contains vocabulary. The state is assigned at stage 5 only when a
semantic unit is both affirmative and claim-bearing, but no active rule,
planned marker, historical fingerprint, or other reviewed policy class owns
it.

### Scanner interfaces and error contract

```text
enumerate_candidates(context, limits)
  -> CandidateInventory(files, candidate_count, candidate_bytes)
  ! RootResolutionError | PathSafetyError | CandidateBudgetError

extract_semantic_units(candidate, extractor_registry, limits)
  -> ExtractionResult(candidate, units, consumed_bytes, complete=true)
  ! DecodeError | ParseError | UnknownLanguageError |
    AmbiguousExtractionError | SemanticUnitBudgetError

classify_semantic_unit(unit, claim_policy, packaged_authority)
  -> SemanticClassification(state, claim_class, authority_ref, rationale)
  ! AmbiguousSemanticError | ContradictoryPolarityError |
    MissingAuthorityError | UnclassifiedAffirmativeError

scan_loop_runtime_claims(context, policy, authority, limits)
  -> ClaimScanReport(inventory, extraction_totals, state_totals,
                     findings, notices_verified, historical_matches,
                     skipped_candidates=0, truncated_candidates=0,
                     verdict=PASS|BLOCKED)
```

`complete=true` is mandatory for every candidate included in a PASS report.
Errors are typed and carry root owner, normalized path, locator when available,
stage, measured budget values, and authority version. The aggregate report may
contain multiple completed findings, but any input/extraction/classification
error fixes the verdict at `BLOCKED`. There is no `WARN_AND_CONTINUE`, fallback
parser, unknown-as-negative, or partial-success state.

### Deterministic semantic states

| State | Deterministic rule | Result |
| --- | --- | --- |
| `NEGATIVE_NONCLAIM` | same unit has the same normalized subject and predicate with an approved scoped negative; no later contradictory affirmative predicate | pass; retained in counts, never added to historical allowlist |
| `STRUCTURAL_DATA` | extractor proves schema/id/regex/numeric/fixture provenance and classifier finds no product-capability affirmative assertion | pass; retained in counts |
| `HISTORICAL_FACT` | unit has explicit past version/time/evidence context and, when affirmative, matches an exact reviewed historical fingerprint plus required superseding authority | pass only through the historical contract; historical wording alone is not self-authorizing |
| `PLANNED_NOT_ACTIVE` | exact structured target marker binds the unit to a future version and `planned_not_active` | pass; free words such as `planned` or `target` do not qualify |
| `AFFIRMATIVE_CLASSIFIED` | current affirmative unit maps to an explicit supported/forbidden policy claim class | pass only if supported by packaged authority; unsupported classes produce their typed blocking finding |
| `UNCLASSIFIED_SURFACE` | actual affirmative claim-bearing unit has no reviewed semantic/policy owner | blocking |
| `AMBIGUOUS_SEMANTIC_UNIT` | subject, predicate, polarity, temporal scope, fixture provenance, or quoted-vs-asserted status cannot be determined uniquely | blocking |
| `PARSE_ERROR` / `UNKNOWN_LANGUAGE` | complete safe extraction cannot be performed | blocking |

An ambiguous unit is never silently converted to `STRUCTURAL_DATA`,
`NEGATIVE_NONCLAIM`, or `HISTORICAL_FACT`. Conversely, a safely extracted
negative fixture or structural declaration is not blocked merely because its
raw bytes contain a claim vocabulary token.

### Measured repository baseline and closure budget

The baseline is a reproducible **current uncommitted workspace inventory**, not
a commit, tree, tag, or release identity. ADR-011 is untracked at measurement
time and is included in the inventory. The snapshot covers every regular
`.md`, `.py`, and `.json` candidate recursively under current-workspace
`product_root:{docs,project,skills}`. Host governance is intentionally not part
of this fixed capacity snapshot because `host_root` varies by installation; it
is still enumerated and compared in real time by `installed_host` validation.

The final FIX-198-ARCH-R1 snapshot is:

```text
snapshot_kind: uncommitted_workspace_inventory
measured_at: 2026-07-12 Asia/Shanghai
scope: product_root:{docs,project,skills}/**/*.{md,py,json}
candidate_count: 477
candidate_bytes_raw: 6742254
candidate_mib_raw: 6.430
largest_candidate: product_root:skills/software-project-governance/infra/verify_workflow.py
largest_candidate_bytes_raw: 949286
inventory_sha256: f73ab5844dfca0cdf7da33a198c1443ff713d21c9e6c20a3838b06ba8e2ab1a2
git_commit: none
git_tree: none
```

`candidate_mib_raw = candidate_bytes_raw / 1,048,576`, rounded to three decimal
places using round-half-up for display only. Candidate count and raw bytes are
the capacity facts. Logical/non-empty line counts are deliberately removed:
they do not gate scanner capacity and previously depended on an unstated line
reader convention.

#### Deterministic inventory digest

The digest is independently reproducible from the workspace:

1. Enumerate the complete snapshot scope using the same path safety rules as
   candidate discovery. Set `root_owner="product_root"` for every snapshot
   record. Normalize each relative path to a case-sensitive POSIX path, Unicode
   NFC, with no absolute form, empty segment, `.`, `..`, alias, symlink, or
   case-colliding peer.
2. Read raw bytes. `byte_count` is the raw on-disk byte length before decoding
   or newline normalization. Decode strict UTF-8, remove at most one leading
   UTF-8 BOM, convert CRLF and lone CR to LF, normalize decoded text to Unicode
   NFC, and encode UTF-8. Decode or normalization failure blocks inventory
   construction.
3. To avoid self-reference for this ADR only, the normalized ADR content must
   contain exactly one line matching
   `inventory_sha256: [0-9a-f]{64}` inside the snapshot block above. Replace
   only those 64 hexadecimal characters with 64 ASCII zeroes before computing
   ADR `content_sha256`. Zero or multiple matches fail. The replacement is
   fixed-width, so it does not change raw `byte_count`; all other ADR bytes,
   including snapshot counts, scope, algorithm, and status, remain covered.
4. Compute `content_sha256` as lowercase SHA-256 of the normalized content
   bytes. For each candidate serialize exactly:
   `root_owner + U+001F + normalized_path + U+001F + content_sha256 + U+001F + decimal(byte_count) + LF`.
   Root owners and paths containing U+001F or LF are invalid. Decimal byte
   counts have no leading zero except `0`.
5. Sort records by the unsigned UTF-8 byte sequence of
   `(root_owner + U+001F + normalized_path)`. Concatenate the serialized UTF-8
   records without a header or footer. `inventory_sha256` is lowercase SHA-256
   of that byte stream.

This placeholder rule excludes only the digest's own 64 characters, which
cannot securely commit to themselves. It does not exclude the ADR, the
snapshot, any count, any path, or any other content from the inventory.

REVIEW-FIX-197-DESIGN-R2 recorded approximately 133 surfaces for the original
cheap vocabulary. That number remains migration context only; it is neither a
parse queue nor a baseline identity.

At runtime, the scanner and an independent enumerator operate on the **current
complete inventory** and prove:

```text
enumerated_candidates == independently_enumerated_candidates
decoded_candidates == enumerated_candidates
parsed_candidates == decoded_candidates
extracted_candidate_paths == parsed_candidate_paths
reported_semantic_units == independently_counted_extractor_units
skipped_candidates == 0
truncated_candidates == 0
```

They do not compare current count, bytes, or digest with this snapshot as a
permanent golden value. Candidate additions/removals are legal within the
declared budgets, provided scanner and independent enumerator agree on the
real-time complete inventory and every candidate is parsed. Any new
affirmative claim must still be semantically classified or block.

### REVIEW-FIX-197-DESIGN-R2 resolution mapping

| R2 blocker element | Resolution in this revision |
| --- | --- |
| Cheap vocabulary match became `UNCLASSIFIED_SURFACE` before semantics | Stages 1-3 enumerate, parse, and extract all candidates. `UNCLASSIFIED_SURFACE` exists only at policy classification for an actual affirmative claim unit. |
| Roughly 25 manifest paths did not close roughly 133 matching surfaces | `input_manifest` now defines required authority surfaces, not the parse universe. The parse universe is the complete current snapshot candidate set plus declared host files. |
| Legitimate negative fixtures and structural registry data blocked | Unified Markdown/Python/JSON provenance and deterministic `NEGATIVE_NONCLAIM` / `STRUCTURAL_DATA` states precede policy ownership. |
| Unknown or ambiguous semantics could be skipped | `AMBIGUOUS_SEMANTIC_UNIT`, `PARSE_ERROR`, and `UNKNOWN_LANGUAGE` are distinct blocking states with no fallback parser. |
| Deep-scan cap 100 was below the observed corpus | The matched-file cap is removed. All candidates are parsed under 1,500-file/24-MiB and 300,000-unit/32-MiB budgets, with overflow blocking and no partial verdict. |
| No repository baseline proved closure | Validation independently compares candidate paths/bytes, parsed paths, semantic-unit accounting, and zero skip/truncation; mutation fixtures require a new unclassified affirmative claim to fail. |

### REVIEW-FIX-198-DESIGN-R0 P1-BLOCKING-1 resolution mapping

| Required fix | Resolution | Status |
| --- | --- | --- |
| Re-measure after final ADR revision | Snapshot count, raw bytes, displayed MiB, maximum file, and digest are recomputed only after all R1 prose is final. | RESOLVED |
| Bind baseline to reproducible identity | Snapshot carries deterministic `inventory_sha256` over every sorted `(root_owner, normalized_path, content_sha256, byte_count)` record. | RESOLVED |
| Define encoding/newline/line counting | Strict UTF-8, one BOM removal, CRLF/CR to LF, and NFC normalization are explicit. Non-gating line counts are removed. | RESOLVED |
| Do not permanently require `==477` | Runtime acceptance compares scanner and an independent enumerator over the real-time complete inventory. Snapshot counts are capacity evidence only; within-budget candidate growth is legal. | RESOLVED |
| Do not claim commit/tree identity for untracked ADR | Snapshot explicitly records `uncommitted_workspace_inventory`, `git_commit:none`, and `git_tree:none`; ADR is included through fixed-width digest canonicalization. | RESOLVED |

## Claim Classes

The scanner blocks unsupported affirmative claims about runtime activation/completion/only-model status, classic supersession, absence of a global stage, generic persisted back-edges/rounds/loop_count/fuse execution, migration validity/full installed-state PASS, criteria MET/IMPL-MET/closure, risk closure, and 1.0.0 readiness.

The scanner tokenizes Markdown into clauses: prose sentences, list items, individual table cells, headings, and comments. Code fences are ignored for active semantics unless a historical `fence` locator explicitly owns them. English and Chinese punctuation delimit clauses. A negative applies only when the same clause contains the same normalized subject, claim predicate, and an approved negative predicate.

Future behavior is allowed only through a structured adjacent marker:

```html
<!-- loop-runtime-target:{"claim_id":"...","target_version":"0.68.0","status":"planned_not_active"} -->
```

Free tokens such as `target`, `planned`, `experimental`, or an unrelated negation do not suppress a finding. A clause containing both a negative and a later affirmative predicate fails as contradictory. Cross-sentence, cross-table-cell, and cross-list-item masking is forbidden.

The seven SKILL files and mapping have explicit per-surface invariants: gate role vocabulary may remain; current execution may state only Coordinator M7.4 `NEEDS_CHANGE -> rework -> re-review` and Check 30 review-chain enforcement. Every generic persisted back-edge, flow-unit `loop_count`, tier fuse, automatic escalation, and PARO transition statement is removed or bound to a `0.68.0/planned_not_active` marker.

## Validation

- a real-repository baseline independently enumerates `docs/`, `project/`, and
  `skills/` and asserts candidate path equality, byte equality, parsed path
  equality, complete semantic-unit accounting, and zero skip/truncation; the
  recorded workspace snapshot must independently reproduce its exact count,
  raw bytes, maximum file, and `inventory_sha256`, while runtime comparison
  uses the current complete inventory rather than a permanent snapshot count;
- existing legitimate negative fixtures in
  `infra/tests/test_verify_workflow.py`, structural loop registry values, regex
  sources, numeric fuse declarations, and exact historical facts reach their
  deterministic nonclaim/data/history states without `UNCLASSIFIED_SURFACE`;
- adding a new Markdown prose assertion, Python module comment/docstring, or
  JSON natural-language/structured affirmative claim with no policy owner
  produces `UNCLASSIFIED_SURFACE` and a non-zero release check;
- malformed Markdown fence semantics, invalid Python/JSON, unsupported
  embedded language with claim potential, or ambiguous fixture provenance
  produces a typed blocking error rather than a partial semantic verdict;
- corrected repository passes scanner and release adapter;
- each of seven SKILL surfaces fails when unconditional generic runtime behavior is injected;
- missing/changed historical digest, changed occurrence count, missing/duplicate notice, missing authority, and new claim beside old claim all fail;
- exact old line plus valid notice passes;
- shitu command output remains byte-preserved while current-validity restatement fails;
- hot plan/snapshot completion claim fails;
- scoped negative and planned-target wording passes; negation masking fails;
- FIX-195 migration and FIX-196 health suites remain green;
- independent Code Review, QA, Design Review, and Release Review complete before REL-058.
- root divergence fixtures cover `product_root != plugin_home != host_root`, installed hosts without repository EVD/DEC, uninitialized hosts, and explicit host-root failure;
- path fixtures cover CRLF/LF, BOM, NFC/NFD, Windows case collision, separators, symlink, traversal, duplicate normalized paths, locator ambiguity, and file-size failure;
- grammar fixtures cover cross-sentence/table/list masking, contradictory clauses, code fences, Chinese/English wording, free `target` tokens, and structured planned markers;
- discovery fixtures prove a newly added nonclaim candidate is fully parsed and
  passes without manifest churn, while a newly added unclassified affirmative
  Markdown/Python/JSON semantic unit fails.

## Blue-Team Challenges

| ID | Challenge | Failure chain | Mitigation | Residual risk |
| --- | --- | --- | --- | --- |
| BT-1 | A maintainer adds an affirmative claim inside a Python test file, expecting the whole directory to be treated as fixtures. | directory assumption -> string is classified as fixture -> release false-pass | No directory exemptions. Only AST-proven literals consumed by a `test_*` call/assertion are fixtures; comments, docstrings, exported constants, and ambiguous values remain claim inputs or block. | Low; mutation tests must cover each provenance branch. |
| BT-2 | A negative validator fixture contains `RISK-037 closed`, causing a vocabulary-only gate to block every release. | cheap match -> unknown file -> `UNCLASSIFIED_SURFACE` before semantics | Parse every candidate first; same-unit subject/predicate negation and AST fixture provenance yield `NEGATIVE_NONCLAIM` or `STRUCTURAL_DATA`. Cheap matches are telemetry only. | Low; grammar changes can introduce ambiguity, which blocks rather than passes. |
| BT-3 | Candidate growth silently exceeds scanner capacity and an implementation scans only the first N files. | repository growth -> cap reached -> suffix omitted -> hidden overclaim | Enumerate and measure the complete candidate set before parsing. Any cap overflow returns a budget error with no PASS/partial verdict; baseline asserts exact independent path equality and zero skipped/truncated candidates. | Low; release remains blocked until the budget is reviewed or repository size is reduced. |
| BT-4 | A historical release sentence is copied into a new document and presented as current truth. | copied wording -> historical vocabulary recognized -> broad historical exemption | `HISTORICAL_FACT` requires explicit historical context and exact path/locator/payload fingerprint plus superseding authority. A copied line has no matching fingerprint and becomes unclassified or unsupported affirmative. | Low. |
| BT-5 | An unsupported or malformed Markdown fence hides a current claim. | opaque fence -> extractor ignores content -> false-pass | Known fence languages use their extractor; an unknown/unlabelled fence with claim potential is `AMBIGUOUS_SEMANTIC_UNIT`/`UNKNOWN_LANGUAGE` and blocks. | Medium; detector coverage is guarded by bilingual and mutation corpora. |

## Alternatives Rejected

- Notice only: rejects because active agent instructions would remain false.
- Rewrite historical facts: rejects because it destroys auditability.
- File or directory allowlist: rejects because new claims in an excluded file would pass silently.

## Non-Goals

- no change to 0.65.0 manifest/tag/commit or old EVD-678/682/683/685 and DEC-097/098/099 rows;
- no 0.67.0 canonical Loop Runtime Contract;
- no 0.68.0 PARO/back-edge/fuse activation;
- no closure of RISK-037/RISK-042;
- no claim that FIX-195/FIX-196 activate Loop runtime.

## Rollback

Truth correction and enforcement have separate rollback policies.

- Active instruction downgrades, superseding notices, packaged authority, and hot-state correction are safety facts and are not rolled back to known-false wording. Emergency replacement requires a new superseding notice/decision.
- The scanner/release adapter may be disabled only by an explicit emergency DEC that records the gap, keeps a manual release block, and preserves the correction surfaces. Removing enforcement must not restore old active claims.
- Policy data rolls back only with the scanner version that consumes it; mixed schema versions fail closed.

Rollback therefore never restores a known runtime-completion overclaim.

## Non-Functional Budget

- exhaustive enumeration supports up to 1,500 candidate files and 24 MiB total
  candidate bytes; every candidate is decoded and parsed, so there is no
  separate matched/deep-scan file cap;
- extraction supports up to 300,000 semantic units and 32 MiB of canonical
  semantic payload. The final workspace snapshot remains below both limits;
  semantic-unit headroom is verified by the real extractor baseline rather
  than inferred from a non-gating line count;
- default per-file limit is 2 MiB, covering the current 949,286-byte maximum.
  A larger file fails with `INPUT_TOO_LARGE` unless a reviewed exact per-path
  limit exists; the exception changes capacity only and never skips parsing;
- candidate enumeration completes before candidate-count/byte verdicts. If a
  count, byte, per-file, parsed-payload, or semantic-unit budget is exceeded,
  the scanner returns a blocking budget finding and **no semantic PASS or
  prefix verdict**. It does not scan or report a selected prefix as complete,
  and it never drops suffix paths/findings to make the run green;
- the real-repository acceptance baseline compares scanner enumeration and
  extraction accounting with an independent test enumerator. It must prove all
  current candidates were parsed, including every old cheap-vocabulary match
  and every non-matching candidate;
- patterns are precompiled, clause-local, and prohibit nested unbounded quantifiers or catastrophic backtracking constructs;
- performance target is under 5 seconds for the current snapshot corpus on the
  release-test host. Memory is O(total parsed input plus semantic-unit index)
  with a 256 MiB process ceiling; streaming is allowed only if it preserves
  complete counts, stable locators, and the no-partial-verdict rule;
- every finding includes root owner, normalized path, line/locator, claim id, classification, and authority version.
