# Rollback Plan - 0.66.2

**Version**: 0.66.2 (patch)
**Release**: non-destructive 0.66.1 incident recovery
**Date**: 2026-07-23
**Candidate parent (B)**: `22488058f80228f714367231ee2d030948f0ca2e` (accepted S217)
**Architecture authority**: `docs/architecture/release-incident-recovery-0.66.2.md` (FIX-214 Design R2)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Slice chain broken | `verify_rel063_evidence.py --phase pre_c --require-slice-chain S215,S216,S217` returns FAIL/UNKNOWN | Stop release; quarantine the candidate. Do not advance to candidate phase. |
| Six slice evidence incomplete | Missing/unresolved primary or sidecar, or result not APPROVED/PASS, or unresolved_blockers>0 | Stop release; re-dispatch the missing review. Do not fabricate evidence. |
| Path-set topology drift | `--assert-staged-path-set` or `--assert-candidate-topology --require-path-count 23` fails | Stop release; the candidate C touches paths outside M063 union N063 or has wrong parent. |
| Authority inputs absent | `.governance/review-authority/REL-063/{authority-input,orchestration-receipts,topology-record}.json` missing | Stop release; the gate fails closed (exit 3 UNKNOWN). External dispatch must populate the authority tree first. |
| Phase contract violation | pre_c admits exact-C/release-review artifacts, or candidate lacks any of the nine artifacts or rehearsal/release-review | Stop release; the phase boundary is load-bearing and must not be bypassed. |
| Rehearsal leak | AUDIT-138 atomic rehearsal reports workspace CHANGED, RTO>900, or real_origin_invocations>0 | Stop release; quarantine the candidate. The rehearsal is one-shot and disposable. |
| exact-C review or Release Review not APPROVED | Independent review result is not APPROVED, or release_authorized!=true at Release Review | Stop release; re-dispatch review. Do not advance to T. |
| Candidate manifest self-reference or stale phase | T manifest references C as subject, or phase drift on any artifact | Stop release; the manifest must remain in `candidate` until T. |
| Local/remote tag mismatch | `--verify-local-tag` or `--verify-push-preconditions` fails; tag does not peel T | Stop publication; never silently move a published tag. |
| Atomic push rejected | `--verify-atomic-push-result` reports partial push or non-atomic update | Stop publication; retain diagnostics. Escalate governed recovery. |
| Fresh full validation fails | `--phase full` after push returns FAIL/UNKNOWN, or 1800s no-trigger observation detects origin invocation | Quarantine the release; retain 0.66.0/0.66.1-installed behavior. Do not retarget the tag. |
| Boundary overclaim | Package restores/moves `v0.66.1`, creates historical tags, claims official/marketplace approval, or activates runtime | Revert the unauthorized action or wording before release. |

## Candidate Quarantine (before T)

1. Stop all candidate-phase work. Do not commit C, do not run exact-C review, do not create T.
2. Preserve the candidate working tree (M063 union N063 = 23 paths) for Coordinator review.
3. Restore any partially-modified M063 file from base B if a version bump is to be withdrawn.
4. Remove the uncommitted N063 files only if the entire candidate is discarded; otherwise leave them in place for re-validation.
5. Confirm no `v0.66.2` tag exists locally (`--require-local-tag-absent v0.66.2`) or remotely (`--require-remote-tag-absent origin:v0.66.2`).
6. Confirm `skills/software-project-governance/core/releases/0.66.2.json` remains `lifecycle_state=candidate`, `release_authorized=false`.

## Transition Quarantine (before push)

1. If T was created but the candidate phase or Release Review is not satisfied, discard T. T is manifest-only and disposable.
2. Restore `skills/software-project-governance/core/releases/0.66.2.json` to the candidate-phase bytes.
3. Re-run `--phase candidate` to confirm `transition_authorized=true`, `release_authorized=false` before any new T.
4. Confirm the annotated tag `v0.66.2` is absent locally; do not create it until `--phase candidate` passes.

## Released-State Recovery (after push)

If the release commit or tag has been pushed but remote gates fail, stop publication and retain all diagnostics. Determine whether the manifest transition, commit parent, local tag peel, remote tag, or remote availability is wrong. Do not force-push or silently retarget an existing published tag. Any tag correction requires Coordinator governance and explicit evidence; users remain on the previously-released version until a corrected PATCH release receives review.

Published tags are never silently retargeted. Any correction uses a newer PATCH candidate (e.g. 0.66.3), never a rewrite or move of the 0.66.2 boundary.

## Non-destructive Fallback

Because 0.66.2 is a non-destructive compensation release with no runtime activation, the safest fallback is to retain the previously-installed plugin version. No runtime migration is required to stay on the prior version. The withdrawn 0.66.1 boundary is not restored, moved, or republished under any rollback path.

## Rehearsal Quarantine

The atomic rehearsal harness (`invoke_rel063_rehearsal.ps1`) is disposable and one-shot. If it leaks (workspace CHANGED, RTO>900, or real_origin_invocations>0), quarantine the candidate, preserve the rehearsal report and observation artifacts, and do not retry the same rehearsal over a dirty workspace. Re-run only from a clean baseline.

## Validation After Rollback

```text
python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase pre_c --require-slice-chain S215,S216,S217 --require-artifact-count 6 --forbid-artifacts exact-C-code,exact-C-qa,release-review --require-transition-absent --require-local-tag-absent v0.66.2 --require-remote-tag-absent origin:v0.66.2
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.2 --no-remote
python skills/software-project-governance/infra/verify_workflow.py verify
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize commit, tag, push, candidate C creation, exact-C review, runtime activation, historical tag creation, force-push, silent tag retargeting, or restoration/movement/publication of the withdrawn 0.66.1 boundary. It claims no 1.0.0 readiness, official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, or 0.67.0 feature. A clean candidate check is not a released check; only `--phase full` after push authorizes release.
