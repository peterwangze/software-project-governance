# Release Lineage Audit - 0.65.3

**Audit date**: 2026-07-11  
**Scope**: 0.62.0 through 0.65.2  
**Task**: FIX-192 / SYSGAP-046 / RISK-041

This audit records observed release commits, local/remote tag state, and release-document provenance. It is an audit snapshot, not the complete declarative release ledger planned for 0.66.0. Missing historical tags are reported as gaps; this work does not create or backfill them. Any historical tag backfill requires a separate governance decision that approves the version-to-commit mapping.

| Version | Release commit | Local tag | Remote tag | Release docs provenance | Disposition |
| --- | --- | --- | --- | --- | --- |
| 0.62.0 | `2a1e5283db21fa5fe0b7b7b7dab0a6d8b8033737` | present, matches | present, matches | backfilled in `7792b4e` after release | historical fact retained |
| 0.63.0 | `589f3eb8645957a4a7bb8d84c3a293bd7cb9ab16` | missing | missing | backfilled in `7792b4e` after release | gap; no automatic tag creation |
| 0.63.1 | `5ea150bdfd7a0c4d06d957b2ed46d8cff6b15936` | missing | missing | backfilled in `7792b4e` after release | gap; no automatic tag creation |
| 0.63.2 | `f37384ad1abb9bf59df2f14c04a10f516b32600e` | missing | missing | backfilled in `7792b4e` after release | gap; no automatic tag creation |
| 0.63.3 | `90dee13c78d26ad940f08229ea76d54318ccf544` | missing | missing | backfilled in `7792b4e` after release | gap; no automatic tag creation |
| 0.63.4 | `f393346992da525c2a805259f5d28f741797b066` | missing | missing | backfilled in `7792b4e` after release | gap; no automatic tag creation |
| 0.64.0 | `6bdcd3da9a689fa1186b45cf3efec31b00d380ca` | missing | missing | release-time docs present | gap; no automatic tag creation |
| 0.64.1 | `01dfa462f2f5e30d8324fdd0f00c6d02e55d39f4` | missing | missing | release-time docs present | gap; no automatic tag creation |
| 0.65.0 | `0ac878e203f2323b7b0705cd28839f81448dfadf` | missing | missing | release-time docs present; FIX-190 corrected archive-integrity wording | gap; no automatic tag creation |
| 0.65.1 | `fe6403767c3bae3f78d256a7cbdf44b20b8bb273` | present, matches | present, matches | release-time docs present | verified |
| 0.65.2 | `073c2c07251b87b8e7d309be8d527770847c24b6` | present, matches | present, matches | release-time docs present | verified |

## Mechanism Added in 0.65.3

- Candidate validation: `check-release --version X.Y.Z --require-changelog --lineage-mode candidate` keeps existing pre-tag release checks usable and explicitly states that tag lineage is not yet proven.
- Completed-release validation: `check-release --version X.Y.Z --require-changelog --lineage-mode released --release-commit <commit>` fails closed when the local tag is absent, points to another commit, cannot be resolved remotely, is absent remotely, or differs remotely.
- The default remote is `origin`; `--lineage-remote` declares another remote when needed.

## Boundaries

This audit does not backfill historical tags, does not approve a historical commit mapping, does not claim zcode official marketplace approval, does not close RISK-041, and does not implement the 0.66.0 complete release ledger.
