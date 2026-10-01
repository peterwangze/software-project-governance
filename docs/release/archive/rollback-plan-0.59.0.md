# Rollback Plan - 0.59.0

**Version**: 0.59.0
**Release**: verify_workflow.py Incremental Split Phase 1 (manifest domain)
**Task**: REL-045
**Date**: 2026-06-26

## 1. Rollback Triggers

Roll back 0.59.0 to 0.58.0 if ANY of the following occur post-release:

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | `check-manifest-consistency` CLI output/exit-code differs from 0.58.0 | Manual diff vs 0.58.0 baseline |
| 2 | Circular-import `ImportError` / `ModuleNotFoundError` in any execution path | Direct script run / pytest / subcommand invocation |
| 3 | `check-manifest-consistency --fail-on-issues` exits nonzero (regression) | Release gate / CI |
| 4 | ArchGuard module-size regression (verify_workflow.py did NOT net-shrink, or manifest.py exceeds thresholds) | `check-architecture-health` |
| 5 | Any of the 18 manifest-domain pytest fails | `pytest -k manifest` |
| 6 | Check 11 (verify) regression | `verify` command |

## 2. Rollback Procedure

0.59.0 is a **pure mechanical refactor** — no schema, no data migration, no config change. Rollback is a clean git revert.

```bash
# From repo root, after 0.59.0 tag/commit is on master:
git revert <0.59.0-commit-sha> --no-edit
# This restores verify_workflow.py in-file manifest functions, removes checks/ subpackage,
# reverts manifest.json registration, and rolls version back to 0.58.0.
git push
git tag -d v0.59.0   # remove the release tag if pushed
```

### Why revert is safe
- The 12 moved functions are byte-identical to their 0.58.0 originals (AST + unified-diff verified, REVIEW-FIX-153).
- `verify_workflow.py` after revert contains the full in-file definitions again.
- `checks/manifest.py` and `checks/__init__.py` are removed entirely.
- `manifest.json` loses the 2 checks/ file entries (no other consumer depends on them).
- `.governance/` records are additive and unaffected.

## 3. Data Compatibility

- **`.governance/` records**: No schema change. Plan-tracker / evidence / decision / risk / snapshot remain valid. The version field in plan-tracker rolls back automatically with the revert.
- **User projects**: Users running `/governance` see identical behavior — the manifest check is invoked through the same command path. No migration needed.

## 4. Reversibility Classification

**Fully reversible.** No data loss, no manual cleanup beyond the git revert. The split is self-contained in product code paths.

## 5. Post-Rollback Verification

After rollback, confirm:
```bash
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
# expect: PASS, canonical=409 actual=347 (pre-0.59.0 counts, no checks/ files)
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
# expect: PASSED (all 0.58.0)
```

## 6. Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external validation. No RISK-036 closure (RISK-036 remains open). No RISK-037 closure. No RISK-039 closure (Phase 1/6; closure needs external host validation). No 1.0.0 readiness / production-ready claim. Rollback is a local git operation; it does not constitute any external reliability claim. DEC-086 degraded SoD honestly noted.
