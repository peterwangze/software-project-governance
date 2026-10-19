# FIX-456 — DSH probe contract preflight

Date: 2026-10-19 (Asia/Shanghai). Producer scope: local guard contract validation and its direct regressions. Independent CODE review is pending; this report grants no release or DSH native runtime acceptance.

## Failure and cause

The Linux Python 3.11 CI run `39127309888` failed the existing `TestGuardContractFailureVerdicts.test_missing_apis_exports_is_a_fail_not_an_environment_gap` negative case. Its copied contract omitted `host.apis[js-yaml].exports`. The guard returned `NOT_RUN`, zero issues and exit 0 because no host installation was discovered. The same negative case was reproduced locally before editing production code; the complete RED output is retained at `.governance/sandboxes/fix456-contract-preflight/red-original.log`.

This is a local product contract defect, so absence of optional tooling must not conceal it. The generic accessor requires `host.apis` to be present, but its probe-specific export declarations are consumed by `oracle_api_symbols()` and `_render_probe_script()`. Previously, that rendering happened only after composition discovery, host discovery and Node discovery. Their early returns could bypass the probe's own contract checks.

## Change

The guard now runs its existing local renderer before composition or environment selection, inside the existing structured contract-failure boundary. This renderer reads only shipped contract facts; it does not import any host module, launch Node or perform host discovery. The actual Node probe continues to use that same renderer. No parallel validation schema or package-specific `js-yaml` branch was introduced.

The shared `oracle_api_symbols()` checks that `host.apis` is a non-empty object, every package entry is an object, `exports` is a non-empty list, and each export is a non-empty string. Diagnostics name the offending map, package entry, export list or list index. Missing required oracle roles and the renderer's other local contract defects use `ContractMalformed` consistently, so the public guard produces structured `FAIL` with an issue instead of a traceback or environment downgrade.

The generic `dsh_contract.py` accessor and its public API are unchanged. The public lazy constants and the existing probe renderer remain covered by the contract module. Healthy contracts with no host still produce `NOT_RUN`; an unreadable contract still produces `NOT_RUN`; malformed JSON and unknown schema versions still produce `FAIL`. No installation discovery, resolution anchor, CLI/profile authority, row/schema accounting or zero-validation acceptance rule changed.

## Verification

| Check | Observed result |
| --- | --- |
| Original missing-exports negative case before production edit | RED: 1 failed, `NOT_RUN != FAIL`, 0.248s; exit 1 |
| Guard contract-failure class after repair | 9 tests passed, 4.050s |
| Complete `test_dsh_contract.py` module | 122 tests passed, 6.630s |
| FIX-454 resolution/isolation/public-decode/write-entry subset | 36 tests passed, 2.637s |
| Static `verify_workflow.py` | PASSED, exit 0; existing stale version-exemption WARNs remain in the log |
| Manifest consistency | PASS, exit 0 |
| Cross references | exit 0 |
| Scoped source `git diff --check` | exit 0 |

The complete contract module includes the nine-test class, so its results are not added again as distinct tests. The two module selections contain **158 distinct passing tests**. No complete repository suite or new remote CI run was performed in this slice.

The new guard regressions exercise the real guard and CLI over disposable copied repositories, without mocked verdicts. The missing-exports case now explicitly empties PATH and removes both DSH installation overrides. A separate matrix has 15 API-declaration mutations: null/list/empty/string maps, null/list/string package entries, null/empty/string export lists, null/numeric/empty/whitespace export members, and a declaration unable to supply the required oracle symbols. Each matrix case also removes the copied composition tree, proving contract defects precede the no-composition early return. Each case requires `ContractMalformed`, the relevant field, `FAIL`, at least one issue, zero checked rows and no selected installation. A healthy-contract control under the same no-host mechanism requires `NOT_RUN`, zero issues and zero checked rows.

The existing hermetic zero-schema regression remains part of the 36-test subset and still rejects zero checks as `NOT_RUN`. Flat, nested, pnpm and conflicting CLI/profile authority regressions also pass. No actual DSH installation was run or installed, and no installed SDK was imported for this verification.

Paused FIX-444/445 files were read only to verify their protected SHA256 values; they remain:

- `infra/hooks/commit-msg`: `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`
- `infra/tests/test_hooks.py`: `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`

No commit, index/ref change, governance-ledger write, host configuration repair, FEAT-102 product wiring or user-plugin reinstall was performed.

## Command audit and isolation

The following records contain captured UTC start/end, actual exit code, literal executable arguments, impact and retained log path. All ran from `D:/AI/agent/claude/coding/project_management_workflow` using the already deployed replay venv; no dependency installation was needed. The common PowerShell setup below preceded each command. The sandbox absolute path was checked to stay inside this repository before its directory was created.

```powershell
$tmpHome='D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight'
$env:HOME=$tmpHome
$env:USERPROFILE=$tmpHome
$env:APPDATA=$tmpHome
$env:LOCALAPPDATA=$tmpHome
$env:DSH_HOME=$tmpHome
$env:TEMP=$tmpHome
$env:TMP=$tmpHome
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
Remove-Item Env:DSH_INSTALL_DIR,Env:DSH_HARNESS_NODE_MODULES -ErrorAction SilentlyContinue
$env:PATH='D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts;C:/Program Files/nodejs;C:/Program Files/Git/cmd;C:/Program Files/Git/bin;C:/Windows/System32'
```

This excludes the user's npm/DSH shim directory. No-host regression children additionally set PATH to an empty string and point DSH_HOME at their own copied repository's empty home. The existing Node-backed resolution fixtures use the deployed Node executable against their own synthetic packages. Scratch removal is confined to disposable trees created by the test helpers beneath the redirected repository TEMP. Subprocess output is captured to the listed UTF-8 logs before any tail is displayed. These records describe isolated test and static-check operations, not a global filesystem write monitor.

```json
[
  {
    "id": "FIX456-01",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_contract.py -k test_missing_apis_exports_is_a_fail_not_an_environment_gap -v",
    "startUTC": "2026-10-19T06:02:44.6089860Z",
    "endUTC": "2026-10-19T06:02:45.0395277Z",
    "exit": 1,
    "impact": "Read repository modules and contract; write isolated sandbox red-original.log and disposable copied repos only",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/red-original.log"
  },
  {
    "id": "FIX456-02",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_contract.py -k TestGuardContractFailureVerdicts -v",
    "startUTC": "2026-10-19T06:04:24.8795357Z",
    "endUTC": "2026-10-19T06:04:29.2151890Z",
    "exit": 0,
    "impact": "Repository modules/contract read-only; copied mutant contracts and green-guard-verdicts.log under isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/green-guard-verdicts.log"
  },
  {
    "id": "FIX456-03",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_contract.py -v",
    "startUTC": "2026-10-19T06:04:51.5557894Z",
    "endUTC": "2026-10-19T06:04:58.3900727Z",
    "exit": 0,
    "impact": "Repository source/contract reads; logs and disposable subprocess scratch only inside isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/contract-module.log"
  },
  {
    "id": "FIX456-04",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_compat.py -k ResolutionContextTests -k InstallDiscoveryTests -k ProbeIsolationTests -k Ancestor -k PublicEntryDecodeBoundaryTests -k WriteEntryGuardTests -v",
    "startUTC": "2026-10-19T06:04:51.5384237Z",
    "endUTC": "2026-10-19T06:04:54.5035687Z",
    "exit": 0,
    "impact": "Repository source/contract reads; logs and disposable subprocess scratch only inside isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/resolution-safety.log"
  },
  {
    "id": "FIX456-05",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 skills/software-project-governance/infra/verify_workflow.py",
    "startUTC": "2026-10-19T06:04:51.5885041Z",
    "endUTC": "2026-10-19T06:04:53.6350930Z",
    "exit": 0,
    "impact": "Repository source/contract reads; logs and disposable subprocess scratch only inside isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/static-verify.log"
  },
  {
    "id": "FIX456-06",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
    "startUTC": "2026-10-19T06:04:51.5878273Z",
    "endUTC": "2026-10-19T06:04:52.3084795Z",
    "exit": 0,
    "impact": "Repository source/contract reads; logs and disposable subprocess scratch only inside isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/manifest.log"
  },
  {
    "id": "FIX456-07",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 skills/software-project-governance/infra/verify_workflow.py check-cross-references",
    "startUTC": "2026-10-19T06:04:51.6192359Z",
    "endUTC": "2026-10-19T06:04:52.3835303Z",
    "exit": 0,
    "impact": "Repository source/contract reads; logs and disposable subprocess scratch only inside isolated sandbox",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/crossrefs.log"
  },
  {
    "id": "FIX456-08",
    "cmd": "git diff --check -- skills/software-project-governance/infra/dsh_compat.py skills/software-project-governance/infra/tests/test_dsh_contract.py",
    "startUTC": "2026-10-19T06:06:07.6790427Z",
    "endUTC": "2026-10-19T06:06:07.8002287Z",
    "exit": 0,
    "impact": "Read two scoped source diffs; write only isolated sandbox diff-check.log",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/diff-check.log"
  },
  {
    "id": "FIX456-09",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
    "startUTC": "2026-10-19T06:07:15.2680425Z",
    "endUTC": "2026-10-19T06:07:15.8851220Z",
    "exit": 0,
    "impact": "Read final scoped report and repository references; write only isolated sandbox log",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/manifest-with-report.log"
  },
  {
    "id": "FIX456-10",
    "cmd": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -X utf8 skills/software-project-governance/infra/verify_workflow.py check-cross-references",
    "startUTC": "2026-10-19T06:07:15.2781374Z",
    "endUTC": "2026-10-19T06:07:15.9419747Z",
    "exit": 0,
    "impact": "Read final scoped report and repository references; write only isolated sandbox log",
    "access": "isolated",
    "log": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/fix456-contract-preflight/crossrefs-with-report.log"
  }
]
```
