# Rollback Plan - 0.58.0

**Version**: 0.58.0
**Release**: ArchGuard Architecture Health Stewardship (advisory-only)
**Reversibility**: Reversible release (version bump + new advisory checks + docs; no schema/data migration)

## Rollback Trigger Conditions

Roll back to 0.57.0 if ANY of the following occur after publishing 0.58.0:

1. ArchGuard findings cause a release-gate failure (advisory contract broken — G7 violated)
2. `check-architecture-health` / `check-duplicate-code` / `check-technical-debt` / `check-complexity` crash on a supported runtime (reliability regression)
3. The 629-test suite shows a regression attributable to ArchGuard code (not the pre-existing FIX-076/EVD-281 issue)
4. ArchGuard is discovered to overclaim (e.g., fatality misconfigured, readiness overclaim)

## Rollback Steps (concrete, verified pattern)

```bash
# 1. Revert the REL-044 release commit (and the FIX-152 implementation commit if needed)
git revert <REL-044-commit-sha>
# If ArchGuard implementation itself is the problem, also revert a3b96c9:
# git revert a3b96c9

# 2. Delete the 0.58.0 tag (local + remote if pushed)
git tag -d v0.58.0
git push origin :refs/tags/v0.58.0   # only if tag was pushed

# 3. Re-sync installed hooks back to 0.57.0 source
git checkout v0.57.0 -- skills/software-project-governance/infra/hooks/
cp skills/software-project-governance/infra/hooks/* .git/hooks/

# 4. Verify version consistency at 0.57.0
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.57.0 --require-changelog --runtime-adapters

# 5. Confirm ArchGuard commands are gone / release gate green at 0.57.0
```

## Data Compatibility

- **No data migration**: 0.58.0 adds advisory checks + a declarative JSON budget + version strings. No schema change to `.governance/`, no plan-tracker format change, no lifecycle registry change.
- **Rollback data-safe**: reverting leaves `.governance/` records (EVD-622, REVIEW-FIX-152, TD-012/013, REL-044 packet) intact as history; they do not break 0.57.0 validation (governance records are gitignored and additive).
- **architecture-health.json** removal: if reverted, the file simply no longer exists; `check-architecture-health` would then be absent too. No stale-config risk.

## Rollback Impact Assessment

| Aspect | Impact |
| --- | --- |
| Existing checks (1-28n) | None — ArchGuard is additive (28o-28r); reverting restores 28n as last check |
| Release gate | Restored to 0.57.0 behavior; the pre-existing FIX-076/EVD-281 advisory is unchanged |
| RISK-039 | Remains open (core mitigation reverted, but closure already required external validation — no false closure risk) |
| Users who upgraded to 0.58.0 | Downgrade via re-installing 0.57.0; any `architecture-health.json` they created is benign (orphaned config) |

## Decision Authority

Rollback decision: Coordinator + user confirmation (release decision is a critical trigger per /governance). Rollback is reversible-recovery, not destructive.

## No-Overclaim Boundary (conservative)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No external host-project validation of ArchGuard. No automatic best-tool selection. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. ArchGuard is advisory-only in 0.58.0 (fatal_on_error=false). If any overclaim appears in the shipped 0.58.0 package (e.g., asserting one of the above as achieved), treat it as a rollback trigger and revert to 0.57.0.
