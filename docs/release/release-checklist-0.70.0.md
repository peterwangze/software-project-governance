# Release Checklist - 0.70.0

**Version**: 0.70.0 (minor)
**Release**: verify_workflow Phase 5 extraction (FEAT-009) — evidence/risk/review domains extracted to checks/{evidence,risk,review}_domain.py
**Date**: 2026-07-26
**Decision**: FEAT-009 (REL-062, user authorized)
**Candidate parent (B)**: `ed8446c` (FEAT-009 commit, on top of ADR-016 `6b97b5e` and claim-scanner policy fix `b617f8c`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.70.0 MINOR; verify_workflow Phase 5 extraction (FEAT-009, ADR-016), evidence/risk/review domains extracted to checks/{evidence,risk,review}_domain.py, verify_workflow.py 22468 -> 20183 lines (-2285, real extraction per DEC-088); no breaking runtime API |
| 2 | Change list enumerated | PASS - FEAT-009 extraction code commit + version projection 0.69.0 -> 0.70.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - FEAT-009 APPROVED_WITH_NOTES/0 blocker (P0=0, P1=0); ADR-016 design APPROVED_WITH_NOTES/0; real extraction CONFIRMED (function bodies moved, not re-export disguised); behavioral equivalence byte-diff verified (check-governance 134 issues identical both sides); 626 tests + 82 subtests pass, 0 regression |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FEAT-009: verify_workflow Phase 5 extraction — `checks/evidence_domain.py` (402 lines, 14 functions: 12 domain + `_vw` + `_resolve_shared`, Check 1/1b/6/6b), `checks/risk_domain.py` (212 lines, 6 functions: 4 domain + `_vw` + `_resolve_shared`, Check 2/8), `checks/review_domain.py` (2127 lines, 36 functions: 30 domain + constants block + `_vw` + `_resolve_shared`, Check 18/18b/21/21b/22/29/30). `verify_workflow.py` 22468 -> 20183 (git diff stat: +250 / -2535); only thin re-export entries plus the `sys.modules["verify_workflow"] = sys.modules["__main__"]` aliasing guard remain, consistent with the Phase 1 (manifest) / Phase 2 (capability_registry) precedent. KEEP rule + deferred `_vw()` pattern correctly implemented.
- Behavioral equivalence independently verified by byte-diffing the pre-extraction `check-governance` output against the post-extraction output — final Result line is byte-identical (134 issues both sides); 626 tests + 82 subtests identical before and after, zero regression.
- DEC-104 roadmap final segment complete: the verify_workflow Phase 5 originally slated for 0.67.0 was deferred to 0.70.0 by DEC-104, and is now delivered. This also advances one RISK-039 closure criterion (verify_workflow.py decomposed into thin domain entry points).
- Version declarations and e2e fixture pointers advance from 0.69.0 to 0.70.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.70.0 entry.

### Excluded

- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim.
- 0.70.0 does not close RISK-036/RISK-039/RISK-040/RISK-041. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally.

## 2. Version and SemVer

0.70.0 is a MINOR because it adds the verify_workflow Phase 5 domain extraction (evidence/risk/review checks moved out of `verify_workflow.py` into dedicated `checks/` modules) without changing existing plugin runtime APIs or introducing a breaking contract; behavioral equivalence is byte-diff verified with zero regression. Expected declarations are 0.70.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.70.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.70.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.70.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- FEAT-009 Code Review: APPROVED_WITH_NOTES, 0 blocker (P0=0, P1=0); real extraction CONFIRMED (function bodies moved, not re-export disguised; only thin re-exports remain); behavioral equivalence independently verified by byte-diffing pre/post `check-governance` output — final Result line byte-identical (134 issues both sides); 626 tests + 82 subtests identical before and after, zero regression.
- ADR-016 design Design Review: APPROVED_WITH_NOTES / 0 (`review-ADR-016-DESIGN-R0.md`).
- Extraction conforms to DEC-088 (forbids re-export-disguised God-module splits) and is consistent with the Phase 1 (manifest, 0.59.0) / Phase 2 (capability_registry, 0.60.0) precedent.
- 626 tests + 82 subtests, 0 P0.
- The release docs boundary wording is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.70.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.70.0 is reported honestly and is out of scope for this MINOR.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.70.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
