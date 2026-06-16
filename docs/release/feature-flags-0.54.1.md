# Feature Flags - 0.54.1

**Version**: 0.54.1

REL-036 / 0.54.1 publishes the governance hook hotfix release package for FIX-140. It versions nested plugin/workflow product path detection and dated evidence row matching that were already implemented and reviewed, but it does not introduce a new feature flag or alter Dynamic Lifecycle activation.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| Hook nested plugin product path detection | Active as FIX-140 hotfix scope | `pre-commit` and `commit-msg` recognize root product paths and nested plugin/workflow product paths while explicitly excluding `.governance/**` |
| Commit evidence row matching | Active as FIX-140 hotfix scope | `commit-msg` evidence matching supports both `EVD | TASK_ID` and `EVD | date | TASK_ID` row shapes |
| Hook implementation changes in REL-036 | Not active | REL-036 only synchronizes release metadata strings and does not modify the already reviewed FIX-140 hook logic |
| `classic-phase-gate` lifecycle mode | Active/default | Existing 0.54.0 classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.54.1 does not make dynamic-flow-gate default and does not migrate projects |
| 0.55.0 migration/external validation planning | Unchanged | 0.55.0 remains the planned Dynamic Lifecycle migration/external validation version |
| Registry automation command execution | Unchanged metadata boundary | 0.54.1 does not change automation command execution behavior |
| FIX-140 regression coverage | Completed before release packaging | CommitMsg focused 8/8, CommitMessageSourceHardening 12/12, and `git diff --check` PASS are recorded in FIX-140 evidence |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation are complete |

## Kill Switch and Rollback Boundary

0.54.1 is a hook hotfix package. If the release package changes hook repair logic beyond metadata, migrates projects, makes `dynamic-flow-gate` default, changes registry automation command execution, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.54.1 release package and return to 0.54.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
