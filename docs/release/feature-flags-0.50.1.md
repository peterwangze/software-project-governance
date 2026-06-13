# Feature Flags - 0.50.1

**Version**: 0.50.1

REL-028 / 0.50.1 is a release-gate guard patch. It does not add a runtime feature flag, does not change default governance execution behavior, and does not enable an approval, marketplace lifecycle, external validation, Desktop lifecycle, or automatic tool-selection feature.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| 1.0.0 release blocker guard | Active in release readiness | Applies only to `check-release --version 1.0.0`; patch releases such as 0.50.1 are not blocked by 1.0.0-specific checks |
| 0.50.1 release package | Available as versioned release docs and metadata | Packages FIX-130 only; does not add 1.0.0 release assets or approval evidence |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |

## Kill Switch and Rollback Boundary

The release package has no runtime flag to disable. The rollback trigger is a release-gate false result: revert the 0.50.1 package if `check-release --version 0.50.1` fails because of the package, or if `check-release --version 1.0.0` stops reporting explicit hard blockers while RISK-036 and final evidence remain unresolved.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
