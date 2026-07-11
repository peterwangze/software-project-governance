# Feature Flags - 0.66.0

**Version**: 0.66.0 (minor)
**Release**: declarative release ledger, projection generator, and Phase 6 extraction
**Date**: 2026-07-11

## Feature Flag Inventory

0.66.0 introduces no runtime feature flag. The new capabilities are explicit CLI commands and release-state contracts; none activate silently during ordinary governance use.

| Capability | Default | Activation and kill-switch boundary |
| --- | --- | --- |
| `release-ledger` | Read-only, explicit command | Stop release when state is `FAIL`, `UNKNOWN`, or `BLOCKED`; only `PASS` exits the gate. |
| `release-projection` | Check-only | Writes occur only with `--write`; failure triggers byte restoration through the rollback journal. |
| `quality-tools` | Read-only probe | Ruff/mypy absence reports `NOT_RUN`; neither tool is a runtime dependency. |
| Historical manifests | Read-only trust records | Never authorize tag creation; historical tag changes require a separate DEC. |
| Native release transition | Explicit release event | A wrong parent, merge, repeated transition, missing history, or tag mismatch stops release completion. |

## Rollout

The release is applied as a versioned plugin update. Candidate preparation validates projections and local ledger facts. The Coordinator may commit, tag and push only after Release Review; remote ledger and released-lineage checks then verify the immutable release boundary.

## Kill Switch

The operational kill switch is fail-closed release gating: retain 0.65.3 and stop publication whenever ledger, projection, version, manifest, archive or review evidence does not satisfy the release checklist. `release-projection --write` must not be retried over an incomplete rollback journal until recovery is verified.

## Evidence Boundary

- Full suite: 880/882 PASS, with one Windows real-symlink SKIP and one existing Check 13 failure. Not full green.
- Ruff/mypy: `NOT_RUN`, not PASS.
- RISK-036, RISK-037, RISK-039, RISK-040, and RISK-041 remain open.
- No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, historical tag authorization, or 1.0.0 readiness is claimed.
