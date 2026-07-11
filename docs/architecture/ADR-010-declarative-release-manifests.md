# ADR-010: Declarative Release Manifests and Phase 6 Extraction

## Status

Accepted for 0.66.0 implementation. The 0.66.0 manifest remains `candidate` in the FEAT-001 commit. REL-057 is the only change allowed to transition it to `released`.

## Context

The 0.62.0 through 0.65.0 release history exposed three independent failure modes: release records without immutable tag anchors, release documents created after the recorded release, and version projections maintained by manual multi-file edits. The existing `check-release --lineage-mode candidate|released` guard protects future tags, but it does not provide a durable version-to-artifact ledger or an atomic projection writer. Release checks also remained embedded in `verify_workflow.py`, contrary to the Phase 6 architecture direction.

## Decision

### Per-version manifests

Each version has one manifest under `core/releases/<version>.json`, validated against `core/release-ledger.schema.json`. `lifecycle_state` (`candidate` or `released`) and `provenance` (`native` or `historical_backfill`) are orthogonal.

Published facts are not rewritten to hide corrections. Corrections use append-only `amendment` or `withdrawal` events. Events are ordered by `(recorded_at, id)` and carry a SHA-256 integrity value over the canonical event without its `integrity` member. `effective_state` is derived from the declared base state and ordered events.

### Native transition

The candidate commit is derived from the unique Git commit that adds the manifest. A native release transition is valid only when:

1. Exactly one commit changes the manifest from `candidate` to `released`.
2. That commit has exactly one parent.
3. Its parent is the derived candidate commit.
4. Exactly one `candidate_to_released` event exists.
5. The local tag peels to the transition commit.
6. The selected configured remote exists and its peeled tag resolves to the same commit.

Merge, rename/delete/re-add, repeated transition, wrong parent, or wrong tag fails closed. Missing shallow history returns `UNKNOWN`, never `PASS`. Invalid remote identity is `BLOCKED`; inaccessible remote facts are `UNKNOWN`; observable mismatches are `FAIL`.

### Historical backfill

Historical manifests are always `provenance: historical_backfill` and never count as native lineage PASS. They record:

- the original release commit;
- a backfill commit derived from the Git commit adding the manifest;
- release-document contemporaneity;
- tag disposition;
- the governing DEC when a historical tag is ever approved.

Missing historical tags use `missing_requires_decision` with no invented decision. FEAT-001 creates no historical tags.

An authorized historical tag uses the distinct `created_by_decision` disposition. Its DEC must be resolved from governance decision sources, or by an injected resolver in an isolated host, and must explicitly bind the version, release commit, and tag action. A syntactically valid but absent ID such as `DEC-999` is rejected. `verified_present` and `missing_requires_decision` require a null decision field.

### Artifact projections

`core/version-projections.json` declares byte, structured JSON, and transformed-text projections. `skills/software-project-governance/SKILL.md` frontmatter remains the only active-version authority.

The projection command is check-only by default. `--write` first builds every output in memory, validates every source, JSON pointer, replacement count, repo-relative path, target uniqueness, and symlink boundary, then stages all outputs and records a rollback journal. Targets are replaced atomically. Any replacement or post-write validation failure restores all previous bytes; mixed-version output is not accepted.

The registry declares required projection IDs and required validation inventories. Removing a required projection, leaving the registry empty, omitting one of byte/structured/transformed kinds, or losing the `REQUIRED_SNIPPETS`/fixture mirror inventory fails closed. If rollback itself is incomplete, the journal plus immutable backup and staged artifacts are retained for executable recovery; cleanup occurs only after success or a complete rollback.

### Phase 6 module boundary

Release code lives in `infra/release/`; commit, version, and projection checks live in `infra/checks/`. These modules receive root, Git runner, clock, timeout, and context as parameters. They do not import or re-export `verify_workflow.py`. The legacy file is a CLI adapter and preserves the 0.65.3 `check-release --lineage-mode candidate|released` contract.

No third-party runtime dependency is introduced. Ruff and mypy settings are optional progressive configuration; absence of either tool is reported as `NOT_RUN`, not as a passing check.

Runtime manifest validation is dependency-free but schema-equivalent for the schema features in use: types, required and additional properties, constants, enums, patterns, semantic version, date-time, arrays, references, one-of branches, and provenance/trust conditionals. Unsupported schema major or unavailable validation is fail-closed.

## Commands and exit states

- `release-ledger [--version X.Y.Z] [--remote origin] [--no-remote]`
- `release-projection [--write] [--config path]`
- `quality-tools` reports optional Ruff/mypy probes as `PASS`, `NOT_RUN`, or `FAIL`.
- Existing `check-release --lineage-mode candidate|released` remains compatible.

Structured commands return `PASS`, `FAIL`, `UNKNOWN`, or `BLOCKED`. Exit codes are respectively 0, 1, 2, and 3.

## Consequences

Release lineage and projections become reproducible from explicit records and live Git facts. Historical trust remains deliberately weaker than native trust. REL-057 must replace the 0.66.0 candidate planning document with the final release documents, append the transition event, create and push the tag, and run both the ledger and released-lineage checks.

This ADR does not close RISK-039 or RISK-041, does not establish zcode official marketplace approval, and does not authorize historical tag creation.
