# External Project Validation Report - 0.49.0

Date: 2026-06-10
Task: VAL-001
Scope: pre-1.0.0 external validation attempt after `v0.48.0`.

This report records the first 0.49.0 external-project validation attempt. It is intentionally conservative: it documents what ran, what failed, what was fixed as FIX-128, and why VAL-001 is still not a full PASS.

No official approval. No marketplace approval. No universal/full runtime support. No external project validation PASS. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready status.

## Validation Targets

| Target | Source | Real Code Check | Existing Governance State | Result |
| --- | --- | --- | --- | --- |
| `pallets/click` | `https://codeload.github.com/pallets/click/zip/refs/heads/main` | `src/click/core.py` exists | No `.governance/plan-tracker.md` before temporary install | PARTIAL / BLOCKED |
| `psf/requests` | `https://codeload.github.com/psf/requests/zip/refs/heads/main` | `src/requests/api.py` exists | No `.governance/plan-tracker.md` before temporary install | PARTIAL / BLOCKED |

The targets were downloaded as zip archives because `git clone` and `git ls-remote` hit transient GitHub connection resets in this environment. Zip download through `codeload.github.com` succeeded.

## Temporary Install Method

The validation used a temporary local install under `%TEMP%`:

1. Download each target repository through codeload zip.
2. Verify at least one real source-code file exists.
3. Confirm no prior `.governance/plan-tracker.md` exists.
4. Copy the current workflow `skills/software-project-governance/` and `commands/` into the target.
5. Create minimal `.governance/` records and `AGENTS.md` so target-cwd commands can run.
6. Run target-cwd governance commands from each target root.

Temporary validation logs were kept under `%TEMP%\spg-ext-validation-20260611-005043`.

## Command Results

| Target | Command | Exit | Meaning |
| --- | --- | --- | --- |
| `pallets/click` | `python skills/software-project-governance/infra/verify_workflow.py status` | 0 | Status rendering worked from external target cwd. |
| `pallets/click` | `python skills/software-project-governance/infra/verify_workflow.py gate G1` | 0 | Gate rendering worked from external target cwd. |
| `pallets/click` | `python skills/software-project-governance/infra/verify_workflow.py governance-context --fail-on-issues` | 0 | Context discovery found the temporary external validation task without inventing state. |
| `pallets/click` | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` before FIX-128 | 1 | Failed with `IndexError` in Check 13 on empty DEC IDs. |
| `pallets/click` | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` after FIX-128 | 1 | No `IndexError`; remaining failures are partial-install missing README/docs/adapters issues. |
| `psf/requests` | `python skills/software-project-governance/infra/verify_workflow.py status` | 0 | Status rendering worked from external target cwd. |
| `psf/requests` | `python skills/software-project-governance/infra/verify_workflow.py gate G1` | 0 | Gate rendering worked from external target cwd. |
| `psf/requests` | `python skills/software-project-governance/infra/verify_workflow.py governance-context --fail-on-issues` | 0 | Context discovery found the temporary external validation task without inventing state. |
| `psf/requests` | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` before FIX-128 | 1 | Failed with `IndexError` in Check 13 on empty DEC IDs. |
| `psf/requests` | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` after FIX-128 | 1 | No `IndexError`; remaining failures are partial-install missing README/docs/adapters issues. |

## Finding

VAL-001 found a real new-project failure:

| Finding | Severity | Disposition |
| --- | --- | --- |
| `check-governance --fail-on-issues` crashed in newly initialized external projects when governance ID logs had no DEC/EVD/RISK entries. | P1 | Closed by FIX-128 commit `5570774`; remote Governance CI run `27294768188` passed. |

FIX-128 made Check 13 empty-safe and preserved the original blocking semantics:

- empty DEC/EVD/RISK sequences render as `no entries found`;
- DEC gaps and RISK gaps still block;
- current completed tasks without evidence still block;
- EVD gaps, orphan references, and historical completed tasks without evidence remain info-only in `check-governance`.

## Current VAL-001 Decision

VAL-001 is **not a full PASS**.

The validation attempt proves that:

- the workflow can be temporarily installed into two real external code repositories;
- `status`, `gate G1`, and `governance-context` can run from those target cwds;
- the run surfaced a real external-new-project bug and the bug was fixed by FIX-128.

The validation attempt does **not** prove:

- two external projects completed the full Agent Team workflow;
- a project owner participated or confirmed usability;
- a full install package ran `check-governance --fail-on-issues` cleanly in either target;
- official submission or marketplace approval;
- Codex Desktop marketplace-management lifecycle PASS;
- 1.0.0 production readiness.

## Remaining Blockers

| Blocker | Required Next Step |
| --- | --- |
| The temporary install copied only a partial workflow surface, so full governance health failed on missing README/docs/adapters. | Define a complete external-project validation package or a supported minimal external validation profile before re-running VAL-001. |
| No external project owner or independent user pilot participated. | Run at least two owner/user-backed validations or explicitly change the acceptance criteria in governance records. |
| Full Agent Team workflow was not executed end to end in the external projects. | Run an end-to-end task with producer/reviewer separation, evidence, review, and governance health in each target. |

## 1.0.0 Boundary

This report keeps RISK-036 open and keeps 1.0.0 blocked. It should be consumed by FIX-126 and REL-026 as conservative evidence, not as external validation success.
