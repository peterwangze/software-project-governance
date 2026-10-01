# Feature Flags - 0.58.0

**Version**: 0.58.0

0.58.0 delivers **ArchGuard** — the architecture-health stewardship capability (REQ-101/FIX-152, design DEC-084). It adds 4 advisory-only check commands that surface architecture-degradation signals (module/function/constant size, source/projection duplication, technical debt, complexity proxy) without blocking the release gate. ArchGuard guards itself: it flags the ~20k-line `verify_workflow.py` God Module and the duplicated `PRODUCT_CODE_PATTERNS` constant.

**Advisory-only boundary**: `gate_integration.fatal_on_error=false`. ArchGuard WARN/ERROR findings are reported but do NOT increment `all_issues` or fail the gate. This is the conservative DEC-083 design — observe first, tighten in a future version.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `check-architecture-health` | **New** (advisory) | module/function/constant-size + duplicate-constant detection via AST; 3-level PASS/WARN/ERROR; advisory-only (exit 0 on findings) |
| `check-duplicate-code` | **New** (advisory) | source/projection semantic duplicate; normalizes CRLF→LF + ignores whitespace; warns at ≥60%, errors at ≥80% |
| `check-technical-debt` | **New** (advisory) | root residue scripts, release-docs version count, hooks content drift (reuses `_external_validation_*`), technical-debt-ledger cross-validation |
| `check-complexity` | **New** (advisory, disabled) | `complexity.enabled=false`; line-based proxy only; AST cyclomatic deferred to 0.59.0+ |
| Check 28o~28r (in `check-governance`) | **New** (advisory) | ArchGuard wired into governance health; G7: does NOT increment `all_issues` when `fatal_on_error=false` |
| `core/architecture-health.json` | **New** (declarative budget) | Schema v1.0; threshold budget; manifest dual-registered (G6) |
| `verify_workflow.py` functional code | Changed (ArchGuard additions, +~647 lines) | 4 self-contained `check_*` helpers + 4 `cmd_check_*` + CLI subparsers + dispatch entries; self-contained `root=None` signature for 0.59.0+ extraction |
| `classic-phase-gate` lifecycle mode | Active/default (unchanged) | Existing classic registry-backed gate judgment unchanged |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default (unchanged) | 0.58.0 does not migrate projects |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open |
| RISK-039 open-risk boundary | Active release boundary | RISK-039 remains open — core mitigation (ArchGuard) delivered, closure needs external host-project validation |

## Kill Switch and Rollback Boundary

0.58.0 ArchGuard is advisory-only. If the release makes ArchGuard findings fatal (increments `all_issues` / fails the gate), overclaims readiness, closes RISK-036/RISK-037/RISK-039, removes the `fatal_on_error=false` default, or declares 1.0.0 readiness, revert the 0.58.0 release package and return to 0.57.0 while keeping RISK-036, RISK-037, and RISK-039 open.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external validation full PASS for two real projects. No external host-project validation of ArchGuard yet. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No fatal-on-error ArchGuard (advisory only in 0.58.0). No AST cyclomatic complexity (deferred to 0.59.0+). No `verify_workflow.py` split (0.59.0~0.64.0). No modern engineering infrastructure (lint/type/package). No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.
