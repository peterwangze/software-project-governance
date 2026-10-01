# Feature Flags - 0.50.3

**Version**: 0.50.3

REL-030 / 0.50.3 changes installed runtime behavior and validation diagnostics, not a user-facing runtime feature flag. The repaired hook/runtime paths are part of the shipped hook surface, while `external-project-validation` remains opt-in.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| Installed runtime resolver | Enabled in shipped hooks and command templates | Resolves explicit env, repo-local install, or global plugin cache; does not imply target validation full PASS |
| Commit message source hardening | Enabled in shipped hooks | pre-commit ignores stale message bridge files; commit-msg remains the authoritative message gate |
| Target-native diagnostics | Available on demand | Runs only through `external-project-validation --target`; reports target entry and installed hook drift without mutating the target |
| VAL-003 shitu diagnostic archive | FAIL/PARTIAL | Diagnostic evidence only; not a full PASS or 1.0.0 readiness signal |
| VAL-004 python_game diagnostic archive | FAIL/PARTIAL | Diagnostic evidence only; not a full PASS or 1.0.0 readiness signal |
| 0.50.3 release package | Available as versioned release docs and metadata | Packages FIX-132/FIX-133/FIX-134/VAL-003/VAL-004; does not add approval evidence or close RISK-036 |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |

## Kill Switch and Rollback Boundary

The validation command remains opt-in. If the installed runtime resolver breaks installed hooks, commit message hardening blocks valid commits, target-native diagnostics mutate target projects, or the release wording overclaims FAIL/PARTIAL archives as full PASS, revert the 0.50.3 release package and return to 0.50.2 while keeping 1.0.0 blocked.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
