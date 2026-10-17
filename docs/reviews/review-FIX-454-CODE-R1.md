# FIX-454 Code Review R1

Date: 2026-10-17 Asia/Shanghai. Reviewer: Code Reviewer DSH Probe, same reviewer as R0. Prior round: [review-FIX-454-CODE-R0.md](review-FIX-454-CODE-R0.md).

```text
task=FIX-454
round=R1
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
review_scope=dependency_resolution_only
runtime_support=NOT_ACCEPTED_BY_THIS_REVIEW
release_authorized=false
```

## Bound inputs and prior-round integrity

| File | SHA256 |
|---|---|
| skills/software-project-governance/infra/dsh_compat.py | 13b941e0b3b7857a0b71bea4723f82435b2f97b59bd20f539f464a83da58ff9f |
| skills/software-project-governance/infra/tests/test_dsh_compat.py | 1ac5e29b4ce1cfa419a642c107612ccf02e65490825bf6a556c20e3212a88ca3 |
| docs/diagnostics/dsh-0.2-probe-resolution.md | 452d6457ac082faf7cdbf8a4c044c50b166bdb0408f5187f2ab531c0c158ef06 |
| R0 report, retained immutable | 5eb18028e858863de0dcda466eeb80fedf0b0e748967be11c5e88c7016f403fa |

Reviewed the full current diff, the producer's explicit F1 correction and R1 repair ledger, the prior finding/reproduction, and every call site of `_oracle_versions`/`_resolution_anchor`. Role/skill and original dispatch redlines remain in force. Only this new R1 report was written; no product code, R0 report, governance record or user installation was changed by the reviewer.

## R0 finding comparison

| Finding | R1 status | Evidence |
|---|---|---|
| F1 P1 BLOCKING: manifest presence promoted a selected legacy profile to CLI-nested authority | **Fixed** | `_resolution_anchor(..., context=...)` at 1071 distinguishes `profile` and `cli`; discovery explicitly assigns the context at each selection branch (1199, 1207, 1215). Profile anchors remain flat; CLI anchors use the canonical CLI manifest. Static metadata now takes that same anchor, including competing profile metadata. New conflict regression checks both selection sources, owning paths, versions, entry paths and manifests. Independent negative controls below confirm schema behavior, not only version labels. |

No unresolved R0 finding and no newly discovered blocking finding. Unknown context raises `ValueError`; it does not silently choose another installation. A legacy injected install dictionary with no new context fields retains the old flat default in `_probe_request` (1308–1309), instead of inferring authority from a CLI manifest.

The diagnostic now explicitly withdraws the overbroad R0 preservation claim (§“R0 F1 correction”), distinguishes profile selection from explicit CLI selection, and retains the original review and historical failures. This matches the corrected implementation.

## Independent tests and negative controls

Combined relevant suite: **53 passed, 83 deselected, 17 subtests passed in 12.75s**, exit 0. This includes all ten resolution-context tests, install discovery, public decode/write-entry guards and 17 actual installed-schema cases. The two known whole-template installed-schema failures remain excluded explicitly. No full project suite, benchmark or coverage percentage was rerun/claimed.

An additional hermetic test used conflicting public API fixtures to distinguish the actual selected schema:

| Selection/scenario | Expected and observed |
|---|---|
| Legacy profile contains flat runtime oracles and a CLI with conflicting nested oracles; flat Cordis rejects the supplied config | `source=DSH_HOME/profiles/web`, context `profile`, flat anchor; all four flat `1.2.3-profile-authority` packages used; **FAIL** with `profile-specific schema`. |
| Same physical plane deliberately selected through explicit `DSH_INSTALL_DIR`; CLI-nested schema accepts the config | context `cli`, real CLI manifest anchor; all four nested `0.0.1-cli-transitive` packages used; **PASS**. |
| Selected legacy profile has a CLI and complete nested oracles but no flat runtime oracles | **NOT_RUN**, zero checked rows, missing-oracle error metadata retained; nested CLI packages do not fill the missing profile set. |
| Anchor helper receives unknown context | `ValueError`; no fallback. |

These controls close the false-authority path in F1. Fixture packages are deliberately minimal and test-only. Actual installed-schema coverage remains separate and passed. The resolution suite also preserves flat/nested CLI handling, canonical pnpm links, private manifest exports, explicit invalid override refusal, unrelated NODE_PATH/profile refusal, schema rejection and zero-schema NOT_RUN.

## Review dimensions and remaining notes

| Dimension | Conclusion |
|---|---|
| Correctness | F1 closed by explicit selected-plane identity; discovery metadata and live imports use the same anchor. Both schema-divergent controls behave correctly. |
| Safety | No new host writer, apply/lifecycle execution, reverse dependency, registration or reinstall. Wrong-context fallback is rejected in the exercised negative cases. Existing import and isolated-home witness limitations remain accurately disclosed. |
| Maintainability | Anchor policy has one explicit helper; all callers were checked. No new package dependency or fixed version gate. Legacy test-seam compatibility is documented. |
| Performance | Ancestor walks remain bounded by path depth and four oracle packages; no new per-row subprocess or unbounded traversal. No performance claim beyond code inspection. |
| Test coverage | Relevant suite and additional independent boundary controls pass. No changed implementation is approved solely through producer results. Percentage coverage not measured. |

AI-specific checks: mocks remain test-only; no hardcoded product result/version; Node APIs and actual installed exports exercised; no newly unimplemented TODO; no unrelated native runtime implementation added. Design consistency follows the selected CLI/profile context boundary and DEC-187 host isolation.

P0=0; unresolved P1=0; all five dimensions covered. Approval is limited to the reviewed resolution repair.

Nonblocking scope notes: six old tests remain failing because of repository sandbox composition inventory, the shipped legacy workflow module absent from the new CLI, and stale no-schema fixture assumptions. Their attribution was independently established by R0's same-oracle HEAD control; the producer reran them in R1 and retained the failures. This report does not clear those adapter/release obligations. Current DSH native-preset lifecycle, first-session readiness, complete adapter compatibility, plugin reinstall and version release remain outside this approval. Do not infer acceptance from residue directories or resolution success.

## Command audit

All executable validation used this environment, with a repository-only sandbox created using `New-Item -ItemType Directory -Path $env:DSH_HOME -Force`:

```powershell
$env:DSH_HOME = 'D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/dsh454-review-r1'
$env:TEMP = $env:DSH_HOME
$env:TMP = $env:DSH_HOME
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:DSH_INSTALL_DIR = 'C:/Users/peter/AppData/Roaming/npm'
```

Installed files were read-only. Probe/fixture scratch trees were removed by the existing scratch helper; only the sandbox parent remains. Node children are the existing `[node, '--version']` and `[node, '--input-type=module', '--eval', rendered_PROBE_SCRIPT]` invocations; each probe receives a fresh isolated DSH_HOME. pnpm fixture junctions are confined to disposable scratch paths. No real CLI session, registration, install, profile repair or paid model call was performed.

```json
[
  {"id":"R1-REVIEW-RO-01","cmd":"python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -p no:cacheprovider -k '(ResolutionContextTests or InstallDiscoveryTests or ProbeIsolationTests or Ancestor or PublicEntryDecodeBoundaryTests or WriteEntryGuardTests) or (InstalledSchemaTests and not test_shipped_compositions_raise_no_findings and not test_shipped_composition_discloses_its_unverified_rows)' --tb=short","startUTC":"2026-10-16T23:57:02.0181383Z","endUTC":"2026-10-16T23:57:15.5110056Z","exit":0,"impact":"Installed schema modules read-only; repository sandbox dsh454-review-r1 scratch; pytest cache disabled","access":"isolated"},
  {"id":"R1-REVIEW-RO-02","cmd":"python -","stdin_ref":"R1-authority-negative","startUTC":"2026-10-16T23:57:44.172220Z","endUTC":"2026-10-16T23:57:45.362161Z","exit":0,"impact":"Hermetic fixtures and probe homes only under repository sandbox; installed manifests read-only at helper import","access":"isolated"}
]
```

### R1-authority-negative stdin

```python
import datetime, json, sys
from pathlib import Path
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps({'command':'python -','stdin_id':'R1-authority-negative','audit_startUTC':started}),flush=True)
infra = Path('skills/software-project-governance/infra').resolve()
sys.path[:0] = [str(infra),str(infra/'tests')]
import dsh_compat as compat
import test_dsh_compat as fixture
scratch = compat._make_scratch_dir('spg-fix454-r1-authority-')
results = {}
try:
    helper = fixture.ResolutionContextTests()
    profile = fixture._fake_install(scratch/'profiles'/'web'/'node_modules')
    helper._modules(profile,'1.2.3-profile-authority')
    nested = helper._modules(profile/'@deepseek-ai'/'dsh'/'node_modules','0.0.1-cli-transitive')
    flat_cordis = profile/'@deepseek-ai'/'cordis'/'index.js'
    flat_cordis.write_text("exports.resolveConfig = (plugin, config) => { if (config.prefix !== 'profile') throw Error('profile-specific schema'); return config }",encoding='utf-8')
    profile_report = helper._check(scratch,{compat.DSH_HOME_ENV:str(scratch)})
    cli_report = helper._check(scratch,{compat.INSTALL_DIR_ENV:str(profile)})
    assert profile_report['verdict'] == 'FAIL' and 'profile-specific schema' in profile_report['issues'][0],profile_report
    assert profile_report['install']['resolution_context'] == 'profile'
    assert cli_report['verdict'] == 'PASS' and cli_report['install']['resolution_context'] == 'cli',cli_report
    for label,report in [('profile',profile_report),('cli',cli_report)]:
        results[label] = {'verdict':report['verdict'],'source':report['install']['source'],'anchor':report['install']['resolution_anchor'],'issues':report['issues'],'oracles':{name:{'version':info['version'],'path':info['path']} for name,info in report['install']['oracle_packages'].items()}}
    missing = scratch/'missing'
    missing_profile = fixture._fake_install(missing/'profiles'/'web'/'node_modules')
    helper._modules(missing_profile/'@deepseek-ai'/'dsh'/'node_modules','nested-only')
    report = helper._check(missing,{compat.DSH_HOME_ENV:str(missing)})
    assert report['install']['resolution_context'] == 'profile'
    assert report['verdict'] == 'NOT_RUN' and report['rows_checked'] == 0,report
    assert all(v['resolvedPath'] is None for v in report['install']['oracle_packages'].values()),report
    results['missing_profile_does_not_borrow_nested_cli'] = {'verdict':report['verdict'],'rows_checked':report['rows_checked'],'anchor':report['install']['resolution_anchor'],'metadata_errors':all(bool(v.get('error')) for v in report['install']['oracle_packages'].values())}
    try:
        compat._resolution_anchor(profile,context='unknown')
    except ValueError:
        results['unknown_context'] = 'ValueError, no fallback'
    else:
        raise AssertionError('unknown context was accepted')
finally:
    compat._remove_scratch_dir(scratch)
print(json.dumps({'command':'python -','stdin_id':'R1-authority-negative','startUTC':started,'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':0,'impact':'Hermetic fixtures and probe homes only under repository sandbox; installed manifests read-only at test helper import','access':'isolated','results':results},ensure_ascii=False,indent=2))
```
