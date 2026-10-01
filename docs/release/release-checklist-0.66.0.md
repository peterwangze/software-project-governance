# Release Checklist - 0.66.0

**Version**: 0.66.0 (minor)
**Release**: declarative release ledger, complete artifact projection generator, and Phase 6 extraction
**Date**: 2026-07-11
**Candidate parent**: `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd`

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | SemVer defined | PASS - 0.66.0 MINOR; new ledger/projection/CLI capabilities, no breaking runtime API |
| 2 | Candidate parent exact | PASS - HEAD and manifest claim use full `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd` |
| 3 | Native manifest transition | PREPARED/PENDING - the release commit must add the unique `candidate_to_released` transition with the single parent `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd`; this item becomes PASS only after local and remote tag gates verify the release commit |
| 4 | Independent reviews | PASS - Code R3 APPROVED, QA R1 PASS, Test Review R1 APPROVED_WITH_NOTES; all `unresolved_blockers=0` |
| 5 | Test disclosure | PASS - 880/882 PASS, 1 real-symlink SKIP, 1 existing Check 13 failure; no full-green claim |
| 6 | Optional quality tools | PASS boundary - Ruff/mypy are `NOT_RUN`, not runtime dependencies and not PASS evidence |
| 7 | Historical/marketplace boundaries | PASS - no historical tag creation, risk closure, zcode approval, or 1.0.0 claim |

## 2. Included

- Per-version immutable release manifests, runtime schema-equivalent validation, append-only events and effective state.
- Native candidate-to-released lineage with Git-derived candidate/transition commits and local/remote tag checks.
- Historical manifests for 0.62.0~0.65.3 with deliberately weaker `HISTORICAL_ONLY` trust.
- Complete byte/JSON/text projection registry with atomic write, rollback journal, portable symlink guard and inventory completeness checks.
- Phase 6 release/commit/version/projection modules and thin legacy CLI adapters.
- `release-ledger`, `release-projection`, and `quality-tools` commands while retaining the 0.65.3 `check-release` contract.

## 3. Excluded

- No historical tag creation or backfill.
- No RISK-036, RISK-037, RISK-039, RISK-040, or RISK-041 closure.
- No official approval, zcode official approval, marketplace approval, curated listing, partnership, universal/full runtime support, external first-session pilot success, or 1.0.0 readiness claim.
- No claim that the optional Ruff/mypy probes ran when the tools are unavailable.

## 4. Candidate Validation

Run before independent Release Review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py release-projection
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py quality-tools
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py verify
git diff --check
```

The uncommitted candidate is expected to report that the released Git transition is not yet committed. That state is not release completion evidence. After the Coordinator creates the single-parent release commit, tag, and push, run:

```text
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.0 --remote origin
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.0 --require-changelog --lineage-mode released --release-commit <release-commit>
```

Both commands must PASS with local and remote tag peel equal to the exact release commit.

## 5. Test and Review Evidence

- Full suite: 882 total, 880 PASS, 1 SKIP because Windows real symlink creation was unavailable, and 1 existing Check 13 fixture isolation failure.
- The portable symlink guard mutation test passes; the real-symlink SKIP is retained as a residual portability note.
- Focused release-ledger/projection/Phase 6 tests: 29 total = 28 PASS + 1 Windows real-symlink SKIP.
- Compatibility tests: 70/70 PASS.
- Code Review R3, QA R1, and Test Review R1 are terminal with zero unresolved blockers.

## 6. Release Decision Boundary

This package is a release candidate only. This agent does not commit, tag, push, make the final go/no-go decision, close risks, or assert external marketplace approval. Independent Release Review is required before release execution.

## 7. Rollback Verification

`docs/release/rollback-plan-0.66.0.md` covers candidate rollback, projection recovery, transition/tag failure and Phase 6 rollback. Published tags are never silently retargeted. After any rollback, rerun projection, version, ledger, manifest, hot-fact, archive and verify gates.
