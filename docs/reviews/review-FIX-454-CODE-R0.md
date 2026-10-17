# FIX-454 Code Review R0

Date: 2026-10-17 Asia/Shanghai. Reviewer: Code Reviewer DSH Probe. Scope: dependency resolution changes and their diagnostic claims only.

```text
task=FIX-454
round=R0
conclusion=NEEDS_CHANGE
unresolved_blockers=1
runtime_support=NOT_ACCEPTED_BY_THIS_REVIEW
release_authorized=false
```

## Bound inputs

HEAD: `2aae6ff1f1cf49e3566e25c5d55b7fe1afdb762f`.

| File | SHA256 at review |
|---|---|
| skills/software-project-governance/infra/dsh_compat.py | b2afc79bc4a0c64961c82c1f37169b2be8834f82eda159e37d70e0e42c2025a0 |
| skills/software-project-governance/infra/tests/test_dsh_compat.py | b60cdae07668597ec156f3dbbd99f2fd9fc4e28273ae370488eb637e6cd27ad7 |
| docs/diagnostics/dsh-0.2-probe-resolution.md | b4db3de5a8eb202dc982ea6d9aa402ff6391a11b977249ec1397635efd0be386 |

Read `agents/code-reviewer.md`, `skills/code-review/SKILL.md`, plan tracker FIX-454/FEAT-102, and the resolution boundary in `docs/architecture/dsh-adapter-version-decoupling.md` §7.1. `resolve_entry.py --json` returned `resolved_root_ok=true`. Parent preauthorized execution and report writing; no product code or governance record was changed by this reviewer.

## Finding F1 — P1, BLOCKING: a selected legacy profile can silently validate against nested CLI dependencies

Location: `skills/software-project-governance/infra/dsh_compat.py:1070`–1075 and callers at 1081 / 1230. Coverage gap: `tests/test_dsh_compat.py:372` only tests a profile **without** a CLI manifest.

`_resolution_anchor(node_modules)` promotes every present `@deepseek-ai/dsh/package.json` to the resolution anchor, regardless of whether `locate_dsh_install()` selected a CLI installation or a legacy runtime profile. The existing profile contract explicitly identifies the profile's own `node_modules` as authoritative (1104–1113, 1149–1161); the existing test at 269–284 also requires a CLI present in that plane to remain informational. A CLI's nested dependencies can differ from the profile's mounted packages.

Independent hermetic reproduction (`R0-profile-cli`, full stdin below):

1. Set only `DSH_HOME=<scratch>` for discovery. Create `<scratch>/profiles/web/node_modules` with flat oracles at version `1.2.3-profile-authority`.
2. Put a CLI manifest in that same profile, with another oracle set under `.../@deepseek-ai/dsh/node_modules` at `0.0.1-cli-transitive`.
3. The current report says `source=DSH_HOME/profiles/web`, but anchors at the CLI manifest, resolves all four **CLI transitive** packages, and returns `PASS`.
4. Keeping exactly the selected profile and setting only the test seam's anchor to its original flat `node_modules/__dsh_compat_anchor__.js` resolves all four **profile authority** packages instead. Both fixture sets implement the same public API, so the version/path difference directly isolates resolution selection.

Observed paths (common disposable prefix omitted):

| Context | Actual oracle package base | Version |
|---|---|---|
| Current, despite `source=DSH_HOME/profiles/web` | `profiles/web/node_modules/@deepseek-ai/dsh/node_modules/<oracle>` | `0.0.1-cli-transitive` |
| Original profile plane control | `profiles/web/node_modules/<oracle>` | `1.2.3-profile-authority` |

Impact: this breaks the guard's defining invariant that it checks the runtime plugin set it reports. A schema difference between the sets could therefore create false acceptance or rejection. This is an introduced selection regression; the demonstration does not claim an installed current profile actually has this shape.

Required correction: carry the selected resolution-plane kind into anchor selection. Preserve the legacy profile's flat authority even when a CLI package happens to be present; use the real CLI manifest for actual CLI installation contexts. Keep static discovery metadata and live imports on the same chosen context. If some profile protocol intentionally uses CLI-first resolution, model and verify that protocol explicitly instead of inferring it from manifest existence. Add a regression with both flat profile oracles and conflicting CLI-nested oracles, and assert actual resolved paths/versions and verdict. Update the diagnostic's broad preservation claim accordingly. No self-fix was performed.

## Independent verification

| Check | Result |
|---|---|
| New nine context regressions plus install discovery, public decode and write-entry guards | 35 passed, 100 deselected, 15 subtests passed; 3.04s |
| Actual installed schema cases, excluding the two known whole-template failures | 17 passed, 118 deselected; 4.44s |
| Partially missing oracle set, with private manifest exports | `NOT_RUN`, zero checked rows; available js-yaml metadata retained, missing three oracle records retain errors |
| Six failures listed in producer diagnostic | All six independently reproduced; 129 deselected; 10.25s |
| Unmodified HEAD probe source executed in memory against the same installed nested oracle plane | Same verdict, every row kind, counts, coverage and isolated-home write count as current code for shipped template and FX-NO-SCHEMA-01/02 |
| Profile containing both flat runtime oracles and CLI-nested oracles | F1 reproduced; wrong selected dependency set, despite profile source label |

The 52 passing selected tests are distinct. No full repository suite or line-coverage percentage was rerun/measured. Successful tests do not override F1.

The actual selected CLI installation resolved Cordis `4.0.5`, include `1.0.10`, loader `1.0.6`, and js-yaml `4.3.2`, all beneath `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/`. This confirms the intended nested-CLI repair works for this installation, while the legacy-profile boundary remains defective.

Six existing failure attribution is supported by the same-oracle HEAD control, not just by test age:

| Existing test(s) | Independent evidence |
|---|---|
| Composition inventory | Both old and new discovery return the existing sandbox composition plus the shipped template. The discovery implementation was not changed. |
| Shipped-template acceptance | Old and new probes both report the missing `dsh-workflow-worker-thread` row, 23 enabled / 18 checked / 4 no-schema. |
| Shipped-template accounting | Existing equality omits unresolved rows: 18+4 differs from 23 (doubled to 44 vs 46 by the pre-existing sandbox copy). Same old/new classifications. |
| Three historical no-schema fixture assertions | Both probes now schema-check `dsh-tool-ask-user`: FX01 is PASS with 1 checked; FX02 is PASS with 2 checked. The old no-Config assumption is stale. The hermetic new no-schema test still requires NOT_RUN with zero checks. |

The first same-oracle control attempt incorrectly compared complete issue strings, including the intentionally different install-plane diagnostic path; it exited 1 after confirming identical shipped-template verdict/counts. The corrected control compares semantic fields and every row kind and passed. This was reviewer harness assertion strictness, not a product finding. Its exact start timestamp was not captured; the audit appendix explicitly records the bounded interval instead of inventing a timestamp.

## Five review dimensions and hard gates

| Dimension | Conclusion |
|---|---|
| Correctness | BLOCKED by F1. Nested CLI, flat CLI and pnpm fixtures otherwise pass; oracle metadata is retained before setup failure. |
| Safety | F1 violates resolution authority. Explicit invalid overrides remain fail-closed; unrelated NODE_PATH and unrelated profile cannot supply a missing selected CLI oracle in tested cases. No new apply/lifecycle call, host configuration writer or shell string execution was introduced. |
| Maintainability | The anchor helper lacks the selected-plane identity needed to preserve the two distinct contracts. File/module resolution and manifest discovery remain bounded and explicit. |
| Performance | Ancestor walks and four oracle metadata reads are bounded by path depth. No unbounded traversal or repeated process spawning was added per row. No performance benchmark claimed. |
| Test coverage | Positive/negative coverage is meaningful, including private exports, zero-schema, pnpm, invalid override, schema rejection and NODE_PATH. F1 is the missing profile-with-CLI branch. No percentage coverage claim. |

Design consistency: the new CLI-manifest context follows ADR §7.1's nested CLI requirement; F1 conflicts with preservation of the selected CLI/profile authority. DEC-187 host-isolation boundary is otherwise retained: the diff does not modify host rows, reverse dependencies, or real profile registration.

| AI-specific check | Result |
|---|---|
| Mock residue | Minimal oracle mocks are test-only and explicitly described as resolution fixtures. Installed-schema tests independently passed. |
| Hardcoded results/versions | No new product version gate or fixed acceptance result. Versions in fixtures are deliberate conflicting-context sentinels. |
| Hallucinated API | Node createRequire/resolve/realpath and installed exports were exercised by the isolated tests. |
| Unimplemented TODO | None introduced in the reviewed diff. |
| Overimplementation | Change remains confined to dependency resolution/metadata and tests; no native runtime migration was added. |

P0 count=0; unresolved P1 blocking count=1; five dimensions covered; finding has severity, line, reproduction, impact and remediation. Therefore merge approval is withheld pending F1 correction and same-reviewer R1. This review grants no full DSH adapter, native-preset runtime, release, reinstall or risk-closure acceptance.

## Real-environment command audit

Common shell prefix for the following Python invocations:

```powershell
$env:DSH_HOME = 'D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/dsh454-review'
$env:TEMP = $env:DSH_HOME
$env:TMP = $env:DSH_HOME
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:DSH_INSTALL_DIR = 'C:/Users/peter/AppData/Roaming/npm'
```

The initial command creates that repository sandbox with `New-Item -ItemType Directory -Path $env:DSH_HOME -Force`. No command registered/reinstalled the user plugin. Only installed manifests/modules were read. Scratch directories and fixture files were confined to the repository sandbox; existing scratch helpers removed their own temporary trees. The sandbox parent remains. The `home_writes=0` witness concerns only each isolated probe home and is not represented as a global filesystem write audit.

Node subprocesses spawned by the probe are `[node, '--version']` and `[node, '--input-type=module', '--eval', rendered_PROBE_SCRIPT]`, with stdin generated by `_probe_request()` and a fresh isolated DSH_HOME. The pnpm fixture may use `[cmd, '/c', 'mklink', '/J', scratch_link, scratch_target]` entirely within its disposable tree. These are nested operations of the listed test drivers, not real profile writes.

```json
[
  {"id":"R0-RO-01","cmd":"python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k 'ResolutionContextTests or InstallDiscoveryTests or ProbeIsolationTests or Ancestor or PublicEntryDecodeBoundaryTests or WriteEntryGuardTests'","startUTC":"2026-10-16T16:00:52.5092326Z","endUTC":"2026-10-16T16:00:56.0951804Z","exit":0,"impact":"Repository sandbox scratch only; installed modules/manifests read-only","access":"isolated"},
  {"id":"R0-RO-02","cmd":"python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k 'test_repo_compositions_are_discovered or test_shipped_compositions_raise_no_findings or test_shipped_composition_discloses_its_unverified_rows or NoSchemaFixtureTests' --tb=short","startUTC":"2026-10-16T16:02:06.2097868Z","endUTC":"2026-10-16T16:02:17.0957274Z","exit":1,"impact":"Installed modules read-only; repository scratch; six expected failures reproduced","access":"isolated"},
  {"id":"R0-RO-03","cmd":"python -","stdin_ref":"R0-control-v1","startUTC":null,"time_status":"Exact timestamp NOT_CAPTURED; command executed after R0-RO-02 start and before R0-RO-04 start","time_boundsUTC":["2026-10-16T16:02:06.2097868Z","2026-10-16T16:03:51.068901Z"],"exit":1,"impact":"Installed modules read-only; repository scratch removed in finally; harness assertion compared diagnostic plane path","access":"isolated"},
  {"id":"R0-RO-04","cmd":"python -","stdin_ref":"R0-control-v2","startUTC":"2026-10-16T16:03:51.068901Z","endUTC":"2026-10-16T16:03:58.878804Z","exit":0,"impact":"Installed modules read-only; HEAD source executed in memory; repository scratch removed in finally","access":"isolated"},
  {"id":"R0-RO-05","cmd":"python -","stdin_ref":"R0-partial-and-live","startUTC":"2026-10-16T16:04:39.957267Z","endUTC":"2026-10-16T16:04:45.297837Z","exit":0,"impact":"Installed schema imports read-only; partial-oracle fixtures and homes only under repository sandbox","access":"isolated"},
  {"id":"R0-RO-06","cmd":"python -","stdin_ref":"R0-profile-cli","startUTC":"2026-10-16T16:05:39.406991Z","endUTC":"2026-10-16T16:05:39.954479Z","exit":0,"impact":"Hermetic profile/CLI fixtures only under repository sandbox; installed manifests read-only during test helper import","access":"isolated"}
]
```

### R0-profile-cli stdin (F1 reproducer)

```python
import datetime,json,sys
from pathlib import Path
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps({'audit_startUTC':started,'command':'python -','stdin_id':'R0-profile-cli'}),flush=True)
infra=Path('skills/software-project-governance/infra').resolve()
sys.path[:0]=[str(infra),str(infra/'tests')]
import dsh_compat as compat
import test_dsh_compat as fixture
scratch=compat._make_scratch_dir('spg-fix454-review-profile-cli-')
try:
    profile=fixture._fake_install(scratch/'profiles'/'web'/'node_modules')
    helper=fixture.ResolutionContextTests()
    helper._modules(profile,'1.2.3-profile-authority')
    helper._modules(profile/'@deepseek-ai'/'dsh'/'node_modules','0.0.1-cli-transitive')
    env={compat.DSH_HOME_ENV:str(scratch)}
    result=helper._check(scratch,env)
    selected=dict(result['install'])
    selected['resolution_anchor']=str(profile/'__dsh_compat_anchor__.js')
    control=compat.check_dsh_preset_compat(root=scratch,compositions=[scratch/'agent.cordis.yml'],env=env,install=selected)
    def summary(report):
        return {'source':report['install']['source'],'node_modules':report['install']['node_modules'],'anchor':report['install']['resolution_anchor'],'verdict':report['verdict'],'oracles':{k:v['version'] for k,v in report['install']['oracle_packages'].items()}}
    print(json.dumps({'current':summary(result),'legacy_profile_plane_control':summary(control)},ensure_ascii=False,indent=2))
    assert all(v['version']=='0.0.1-cli-transitive' for v in result['install']['oracle_packages'].values())
    assert all(v['version']=='1.2.3-profile-authority' for v in control['install']['oracle_packages'].values())
finally:
    compat._remove_scratch_dir(scratch)
print(json.dumps({'command':'python -','stdin_id':'R0-profile-cli','startUTC':started,'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':0,'impact':'Repository sandbox only; all packages hermetic fixtures; installed package manifests read-only during test helper import','access':'isolated'}))
```

### R0-control-v2 stdin

```python
import datetime, json, subprocess, sys, types
from pathlib import Path
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps({'audit_startUTC':started,'command':'python -','stdin_id':'R0-control-v2'}), flush=True)
infra = Path('skills/software-project-governance/infra').resolve()
sys.path[:0] = [str(infra), str(infra / 'tests')]
import dsh_compat as current
import dsh_fixtures
source = subprocess.check_output(['git', 'show', 'HEAD:skills/software-project-governance/infra/dsh_compat.py'], text=True, encoding='utf-8')
legacy = types.ModuleType('dsh_compat_fix454_baseline')
legacy.__file__ = current.__file__
sys.modules[legacy.__name__] = legacy
exec(compile(source, legacy.__file__, 'exec'), legacy.__dict__)
selected = current.locate_dsh_install()
nested = Path(selected['dsh_package']) / 'node_modules'
legacy_install = dict(selected, node_modules=str(nested), oracle_packages=legacy._oracle_versions(nested))
results = []
scratch = current._make_scratch_dir('spg-fix454-review-control-')
try:
    cases = [('shipped', Path('agent-presets/governance/agent.cordis.yml.template').resolve())]
    for fixture in ['FX-NO-SCHEMA-01', 'FX-NO-SCHEMA-02']:
        directory = scratch / fixture
        directory.mkdir()
        cases.append((fixture, dsh_fixtures.emit_fixture(fixture, directory)))
    for label, composition in cases:
        pair = {}
        for name, module, install in [('current', current, selected), ('HEAD_same_oracle_plane_control', legacy, legacy_install)]:
            report = module.check_dsh_preset_compat(root=composition.parent, compositions=[composition], install=install)
            pair[name] = {'verdict':report['verdict'], 'rows_enabled':report['rows_enabled'], 'rows_checked':report['rows_checked'], 'coverage':report['coverage'], 'rows':[(r['row'],r['kind']) for c in report['compositions'] for r in c['rows']], 'home_writes':report['isolation']['home_writes']}
            if name == 'current':
                print(json.dumps({'case':label,'oracle_packages':report['install']['oracle_packages']},ensure_ascii=False))
        assert pair['current'] == pair['HEAD_same_oracle_plane_control'], pair
        results.append({'case':label, 'pair':pair})
    assert current.discover_compositions(Path.cwd()) == legacy.discover_compositions(Path.cwd())
finally:
    current._remove_scratch_dir(scratch)
print(json.dumps({'command':'python -', 'stdin_id':'R0-control-v2', 'startUTC':started, 'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit':0, 'impact':'Installed CLI modules read-only; repository sandbox scratch only; identical actual oracle plane selected for unmodified HEAD semantic control', 'access':'isolated', 'results':results}, ensure_ascii=False, indent=2))
```

`R0-control-v1` used the same source-load/installation/fixture/cleanup setup, without the initial audit print. Its per-report pair omitted `rows`, retained full `issues`, and added current `oracle_packages`; it separately asserted equality of verdict, rows_checked and the complete issues strings. The third assertion failed because the message's parenthesized install plane differs. It never proceeded to the no-schema fixtures. No failure timestamp was fabricated.

### R0-partial-and-live stdin

```python
import datetime, json, subprocess, sys
from pathlib import Path
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps({'audit_startUTC':started,'command':'python -','stdin_id':'R0-partial-and-live'}),flush=True)
infra = Path('skills/software-project-governance/infra').resolve()
sys.path[:0] = [str(infra),str(infra / 'tests')]
import dsh_compat
import test_dsh_compat as fixture
scratch = dsh_compat._make_scratch_dir('spg-fix454-review-partial-')
try:
    plane = fixture._fake_install(scratch / 'node_modules')
    package = plane / 'js-yaml'
    package.mkdir()
    (package / 'package.json').write_text(json.dumps({'name':'js-yaml','version':'5.0.0-review','main':'index.js','exports':{'.':'./index.js'}}),encoding='utf-8')
    (package / 'index.js').write_text('exports.load = JSON.parse',encoding='utf-8')
    report = fixture.ResolutionContextTests()._check(scratch,{dsh_compat.INSTALL_DIR_ENV:str(scratch)})
    assert report['verdict'] == 'NOT_RUN' and report['rows_checked'] == 0,report
    oracle = report['install']['oracle_packages']
    assert oracle['js-yaml']['version'] == '5.0.0-review',oracle
    assert oracle['js-yaml']['manifest'] == str(package / 'package.json'),oracle
    assert all(v['resolvedPath'] is None and v.get('error') for k,v in oracle.items() if k != 'js-yaml'),oracle
    print(json.dumps({'partial_failure':{'verdict':report['verdict'],'rows_checked':report['rows_checked'],'oracle_packages':oracle,'reason':report['reason']}},ensure_ascii=False))
finally:
    dsh_compat._remove_scratch_dir(scratch)
args = [sys.executable,'-m','pytest','skills/software-project-governance/infra/tests/test_dsh_compat.py','-q','-k','InstalledSchemaTests and not test_shipped_compositions_raise_no_findings and not test_shipped_composition_discloses_its_unverified_rows']
done = subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
print(done.stdout + done.stderr)
print(json.dumps({'command':'python -','stdin_id':'R0-partial-and-live','subcommand':args,'startUTC':started,'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':done.returncode,'impact':'Installed schemas imported read-only; partial oracle fixtures and probe homes only under repository sandbox','access':'isolated'}))
sys.exit(done.returncode)
```
