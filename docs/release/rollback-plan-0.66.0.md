# Rollback Plan - 0.66.0

**Version**: 0.66.0 (minor)
**Release**: declarative release ledger, projection generator, and Phase 6 extraction
**Date**: 2026-07-11
**Candidate parent**: `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd`

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Candidate parent or transition invalid | Ledger reports wrong parent, merge, repeated transition, missing history, or non-unique event | Stop release; restore the 0.66 manifest to candidate or discard the uncommitted release candidate. |
| Projection drift or incomplete write | `release-projection` is not PASS or a rollback journal remains | Stop release; use journal backups to restore every target byte before retrying. |
| Version declarations diverge | Version/projection checks fail | Restore the authoritative SKILL version and rerun projection generation atomically. |
| Phase 6 compatibility regression | Legacy `check-release` or compatibility tests fail | Revert the Phase 6/CLI slice as one auditable change and retain 0.65.3. |
| Local/remote tag mismatch | Released ledger or lineage check fails | Stop publication; never silently move a published tag. Escalate governed recovery. |
| Optional tooling overclaim | Ruff/mypy absence is recorded as PASS | Correct the release evidence to `NOT_RUN` before review. |
| Historical/approval overclaim | Package creates historical tags, closes RISK-039/041, or claims zcode approval | Revert the unauthorized action or wording before release. |

## Candidate Rollback

1. Remove the uncommitted 0.66.0 release documents and CHANGELOG entry.
2. Restore `core/releases/0.66.0.json` to the committed candidate state from `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd`.
3. Restore SKILL frontmatter to 0.65.3 and run `release-projection --write` to regenerate every declared projection.
4. Confirm `release-projection`, version consistency, manifest consistency, hot-fact source, archive integrity, and `verify` return to the prior state.
5. Confirm no `v0.66.0` tag exists locally or remotely.

## Projection Write Recovery

If a write fails, preserve the rollback journal unless the tool reports complete restoration. Restore each target from its immutable backup, verify byte-copy targets exactly, and rerun check-only `release-projection`. Do not manually repair a subset of generated targets or delete a journal that records incomplete rollback.

## Released-State Recovery

If the release commit or tag has been created but remote gates fail, stop publication and retain all diagnostics. Determine whether the manifest transition, commit parent, local tag, remote tag or remote availability is wrong. Do not force-push or silently retarget an existing published tag. Any tag correction requires Coordinator governance and explicit evidence; users remain on 0.65.3 until a corrected release receives review.

## Full Capability Rollback

Revert the 0.66.0 release commit first. If the underlying capability must be withdrawn, revert FEAT-001 commit `8bd283c2f77cf49a3ec17a7f58c823c2ecc46ddd` as a separate auditable operation. This removes the schema/manifests, ledger/projection/quality commands, Phase 6 modules and release-workflow additions together; do not leave a half-enabled projection or ledger contract.

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py release-projection
python skills/software-project-governance/infra/verify_workflow.py release-ledger --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py verify
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag creation, force-push, or RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, or 1.0.0 readiness. Ruff/mypy remain optional and may legitimately be `NOT_RUN`.
