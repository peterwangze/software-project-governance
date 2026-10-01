# Feature Flags - 0.66.2

**Version**: 0.66.2 (patch)
**Release**: non-destructive 0.66.1 incident recovery
**Date**: 2026-07-23
**Architecture authority**: `docs/architecture/release-incident-recovery-0.66.2.md` (FIX-214 Design R2)

## Feature Flag Inventory

0.66.2 introduces no runtime feature flag. The recovery is a non-destructive compensation release: it adds a fail-closed evidence gate, a candidate release manifest, and supporting release docs; none activates silently during ordinary governance use. No runtime behavior, default, or migration is changed.

| Capability | Default | Activation and kill-switch boundary |
| --- | --- | --- |
| `verify_rel063_evidence.py` | Explicit, opt-in CLI | Fail-closed: exit 0 only on full PASS, exit 2 on deterministic REJECT, exit 3 on UNKNOWN. Never silently authorizes; never commits/tags/pushes. |
| Candidate manifest (`0.66.2.json`) | Read-only trust record (`lifecycle_state=candidate`) | Phase-gated: `release_authorized=false`, `transition_authorized=false` until the candidate phase passes; advanced to `released` only by the manifest-only transition T. |
| `--phase pre_c` | Explicit command | Admits only the six slice artifacts and forbids exact-C and release-review artifacts; requires transition/tag absent. |
| `--phase candidate` | Explicit command | Requires all nine artifacts plus rehearsal and release review; sets `transition_authorized=true`, `release_authorized=false`. |
| `--phase full` | Explicit command | Requires fresh remote facts after push; sets `release_authorized=true`. |
| Atomic rehearsal harness | Explicit, disposable | One-shot: quarantine-on-leak, RTO<=900s, workspace UNCHANGED, `real_origin_invocations=0`; never mutates origin. |
| Historical manifests | Read-only trust records | Never authorize tag creation; historical tag changes require a separate DEC. The withdrawn 0.66.1 boundary is not restored, moved, or republished. |
| Native release transition T | Explicit release event | A wrong parent, merge, repeated transition, missing history, tag mismatch, or unresolved blocker stops release completion. |

## Rollout

The release is applied as a versioned plugin update. Candidate preparation validates the slice chain, the six slice artifacts, and the path-set topology against base B. The Coordinator may commit, tag, and push only after the candidate phase passes, Release Review is APPROVED, and the disposable rehearsal is clean. Remote tag and released-lineage checks then verify the immutable release boundary through `--phase full`.

## Kill Switch

The operational kill switch is fail-closed evidence gating: retain 0.66.0/0.66.1-installed behavior and stop publication whenever the evidence gate returns FAIL/UNKNOWN, the rehearsal leaks, the topology drifts, the slice chain breaks, or any blocker remains unresolved. The candidate manifest must not be advanced to `released` until `--phase candidate` and `--phase full` both pass. Published tags are never silently retargeted; any correction uses a newer PATCH candidate, never a rewrite or move of the boundary.

## No-overclaim Boundaries (Evidence Boundary)

This package is a release candidate only. This agent does not commit, tag, push, make the final go/no-go decision, close risks, or assert external approval. Specifically:

- No 1.0.0 readiness, official approval, zcode official approval, marketplace approval, curated listing, partnership, universal/full runtime support, or external first-session pilot success claim.
- No runtime activation, runtime behavior change, migration-validity claim, or 0.67.0 feature.
- No restoration, movement, or publication of local `v0.66.1`; the 0.66.1 boundary remains withdrawn/untrusted per FIX-217.
- No historical tag backfill, unrelated risk closure, or silent tag retargeting.
- A local candidate check is not a released check against fresh remote facts; only `--phase full` after push authorizes release.
- The disposable rehearsal is a one-shot quarantine harness; a clean rehearsal does not authorize release without independent Release Review.
