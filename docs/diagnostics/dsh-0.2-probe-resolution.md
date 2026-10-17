# FIX-454 — DSH 0.2 probe resolution context

Date: 2026-10-16 (Asia/Shanghai). Scope: dependency resolution only. No CLI install, user profile repair, native preset migration, commit or push was performed.

## Reproduction and root cause

The valid explicit input remains `DSH_INSTALL_DIR=C:/Users/peter/AppData/Roaming/npm` (or its `node_modules` directory). Passing the CLI package directory itself is still invalid and fails closed.

The baseline command below reproduced `NOT_RUN`: the CLI was correctly identified as `0.2.0-rc.2`, but all four oracle versions were unknown. Node tried to resolve `js-yaml` from `npm/node_modules/__dsh_compat_anchor__.js`; the installed dependencies actually live beneath the selected CLI package. The baseline evidence also exists in `.governance/dsh-02-baseline-compat.log`.

The repair selects the real CLI `package.json` as `resolution_anchor` for a selected CLI installation, including its canonical path through pnpm links. A selected legacy profile retains its existing flat plane anchor even if it also contains a CLI manifest; selected source identity decides authority. Discovery reads manifests in that context; the actual Node probe replaces that preliminary metadata with the resolved entry, owning manifest and version from the same context. The probe uses this anchor for oracle imports and bare row imports. `NODE_PATH`/global-only packages cannot fill a missing dependency from an unrelated installation. No second profile/cache fallback was added. The initial R0 implementation did not preserve the profile-with-CLI branch; the correction and withdrawn claim are recorded below.

CLI version remains informational. Schema availability and public API exports determine what can be checked; resolution success does not itself imply compatibility. Probe metadata survives oracle setup failure, so partial discovery is visible.

## Current installation result

After the repair, the same valid explicit input reaches all four real installed oracles:

| Package | Actual version | Resolved entry beneath `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/` |
|---|---|---|
| `@deepseek-ai/cordis` | `4.0.5` | `@deepseek-ai/cordis/lib/index.js` |
| `@deepseek-ai/cordis-plugin-include` | `1.0.10` | `@deepseek-ai/cordis-plugin-include/lib/index.js` |
| `@deepseek-ai/cordis-plugin-loader` | `1.0.6` | `@deepseek-ai/cordis-plugin-loader/lib/index.js` |
| `js-yaml` | `4.3.2` | `js-yaml/index.js` |

The shipped legacy template still produces **FAIL** because `@deepseek-ai/dsh-workflow-worker-thread` is absent from this selected context. Each observed composition has 23 enabled rows, 18 schema-checked rows and four `NO_SCHEMA` rows. The first post-fix discovery also found the pre-existing sandbox composition, giving two copies of this same missing-module finding. This is not overall DSH adapter acceptance or a native preset runtime test. Every observed probe reported zero writes to its isolated home.

## Regression coverage

Nine new Node-backed tests cover flat CLI, nested CLI taking precedence over an older flat set and an unrelated profile, legacy flat profile precedence, pnpm canonical CLI links, private package manifest exports, missing schema, wrong profile, unrelated `NODE_PATH`, schema rejection, and invalid explicit CLI-package override. The fixture oracle implementations are deliberately minimal public APIs used only to test resolution; they are not substitutes for installed host schemas. Windows uses an isolated directory junction if symlink privileges are unavailable.

The first focused run had one test assertion error (`unverified` contains strings, not row objects) and skipped pnpm for missing symlink privilege. The assertion was corrected to inspect the composition row; the pnpm case now executes through a junction. The subsequent complete single-file run executed all nine new tests successfully: **129 passed, 6 failed, 99 subtests passed**, exit 1, 25.06 seconds. The six failures were:

| Existing test | Observed reason |
|---|---|
| `CompositionDiscoveryTests.test_repo_compositions_are_discovered` | Existing sandbox composition makes the fixed single-template inventory assertion false. |
| `InstalledSchemaTests.test_shipped_compositions_raise_no_findings` | Current CLI lacks the template's `dsh-workflow-worker-thread` package. |
| `InstalledSchemaTests.test_shipped_composition_discloses_its_unverified_rows` | Its whole-template accounting assumes no unresolved rows; the missing workflow row is a finding. |
| `NoSchemaFixtureTests.test_fx_no_schema_01_degrades_to_not_run_never_pass` | Historical fixture assumes `dsh-tool-ask-user` has no `Config`; current installed package does have one. |
| `NoSchemaFixtureTests.test_fx_no_schema_01_cli_exits_zero_and_renders_not_run` | Same historical no-schema assumption. |
| `NoSchemaFixtureTests.test_fx_no_schema_02_passes_but_discloses_the_unverified_row` | Same historical no-schema assumption. |

These existing assertions were preserved to avoid concealing remaining adapter and historical fixture work. New hermetic no-schema coverage still requires `NOT_RUN` and zero checked rows. Ancestor-disabled, expression and public API behavior remain covered by the existing tests.

## R0 F1 correction — 2026-10-17 (Asia/Shanghai)

Independent R0 found that manifest presence alone could promote a selected legacy profile to the CLI's transitive dependency context. The initial preservation claim was too broad: the original nine regressions proved the profile branch only without a CLI manifest. That claim is withdrawn; the R0 report is retained unchanged.

Discovery now records the selected context as `resolution_context=profile` or `cli`. Profile discovery, including its installation mirror, keeps its flat anchor even when a CLI manifest exists. Explicit CLI installation overrides and PATH discovery use the real CLI manifest. Static oracle metadata is read from the chosen anchor, and the Node request uses that same anchor. Legacy injected install dictionaries without a context/anchor retain the original flat-context default; manifest presence does not promote them.

The added conflict regression uses the same profile directory in two intentionally distinct selections:

| Selection | Anchor | Oracle versions and owning paths | Verdict |
|---|---|---|---|
| `DSH_HOME/profiles/web` | `profiles/web/node_modules/__dsh_compat_anchor__.js` | All four `1.2.3-profile-authority`, directly under the profile's `node_modules` | PASS, one schema-checked row |
| Explicit `DSH_INSTALL_DIR` pointing to that CLI installation plane | `profiles/web/node_modules/@deepseek-ai/dsh/package.json` | All four `0.0.1-cli-transitive`, under that CLI's nested `node_modules` | PASS, one schema-checked row |

The regression asserts discovery metadata as well as the live probe's resolved entry, owning manifest, version, anchor and source. Before the fix, the profile subtest failed on the CLI anchor while the explicit CLI subtest passed. After the fix, the relevant subset passed: **36 tests / 17 subtests**, including all ten resolution-context tests, install discovery, isolation, ancestor handling, public decode and write-entry guards. The actual installed-schema subset separately passed **17 tests**. These are 53 distinct passing tests; no full repository suite or coverage percentage is claimed.

The real CLI was rechecked against only the shipped template: Cordis **4.0.5**, include **1.0.10**, loader **1.0.6**, js-yaml **4.3.2**, all resolved beneath the selected CLI's own `node_modules`. The template still reports **FAIL** for missing `dsh-workflow-worker-thread`, with **23 enabled / 18 checked / 4 NO_SCHEMA** and isolated-home writes **0**. This preserves a useful failure instead of calling dependency resolution success adapter compatibility.

All six failures listed above were rerun and remain failures (**6 failed / 130 deselected**, 22.16s). Composition discovery now also sees concurrent FIX-453 sandbox copies; the inventory and aggregate row counts depend on those pre-existing/concurrent copies. No inventory change is attributed to F1. The explicit single-template result above avoids that changing denominator. Three historical no-schema assertions still disagree with the installed package's actual exported schema. No assertion was removed, weakened or reclassified. The R0 same-oracle HEAD control remains the attribution evidence.

Static `verify_workflow.py`, `check-cross-references` and `check-manifest-consistency --fail-on-issues` each exited **0**. Their static adapter labels are not native runtime acceptance. Formal acceptance of this correction is pending same-reviewer R1; no release, reinstall, native wiring, profile repair or risk closure is authorized by this producer result.

### R1 repair command audit

Each command below used the prior ledger's isolation rules with `DSH_HOME`, `TEMP` and `TMP` set to `D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/dsh454-repair`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, and `DSH_INSTALL_DIR=C:/Users/peter/AppData/Roaming/npm`. The first driver created this sandbox using `New-Item -ItemType Directory -Path $env:DSH_HOME -Force`. R1-RO-05 through 08 captured their output in the corresponding `R1-RO-NN.log` under that sandbox. Node child invocations and test-only junction behavior are unchanged from the prior ledger. All timestamps below were captured as UTC; installed CLI files were read-only.

```json
[
  {
    "id": "R1-RO-01",
    "cmd": "python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k test_profile_cli_manifest_does_not_override_selected_profile_authority --tb=short",
    "startUTC": "2026-10-16T23:51:37.9571005Z",
    "endUTC": "2026-10-16T23:51:39.4569172Z",
    "exit": 1,
    "impact": "Repository sandbox dsh454-repair scratch only; installed manifests read-only during helper import",
    "access": "isolated"
  },
  {
    "id": "R1-RO-02",
    "cmd": "python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k 'ResolutionContextTests or InstallDiscoveryTests or ProbeIsolationTests or Ancestor or PublicEntryDecodeBoundaryTests or WriteEntryGuardTests' --tb=short",
    "startUTC": "2026-10-16T23:52:17.3312424Z",
    "endUTC": "2026-10-16T23:52:23.7894053Z",
    "exit": 0,
    "impact": "Installed modules/manifests read-only; scratch only in repository sandbox dsh454-repair",
    "access": "isolated"
  },
  {
    "id": "R1-RO-03",
    "cmd": "python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k 'InstalledSchemaTests and not test_shipped_compositions_raise_no_findings and not test_shipped_composition_discloses_its_unverified_rows' --tb=short",
    "startUTC": "2026-10-16T23:52:17.3665580Z",
    "endUTC": "2026-10-16T23:52:24.7515268Z",
    "exit": 0,
    "impact": "Installed modules/manifests read-only; scratch only in repository sandbox dsh454-repair",
    "access": "isolated"
  },
  {
    "id": "R1-RO-04",
    "cmd": "python -",
    "stdin_ref": "R1-live-oracles",
    "startUTC": "2026-10-16T23:52:49.7210493Z",
    "endUTC": "2026-10-16T23:52:51.1683054Z",
    "exit": 0,
    "impact": "Installed CLI oracle modules/manifests read-only; temporary probe home only in repository sandbox dsh454-repair",
    "access": "isolated"
  },
  {
    "id": "R1-RO-05",
    "cmd": "python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q -k 'test_repo_compositions_are_discovered or test_shipped_compositions_raise_no_findings or test_shipped_composition_discloses_its_unverified_rows or NoSchemaFixtureTests' --tb=short",
    "startUTC": "2026-10-16T23:53:06.8326287Z",
    "endUTC": "2026-10-16T23:53:30.2814573Z",
    "exit": 1,
    "impact": "Repository scratch/log R1-RO-05.log under sandbox dsh454-repair; installed modules/manifests read-only when imported",
    "access": "isolated"
  },
  {
    "id": "R1-RO-06",
    "cmd": "python skills/software-project-governance/infra/verify_workflow.py",
    "startUTC": "2026-10-16T23:53:06.8659057Z",
    "endUTC": "2026-10-16T23:53:10.2638788Z",
    "exit": 0,
    "impact": "Repository scratch/log R1-RO-06.log under sandbox dsh454-repair; installed modules/manifests read-only when imported",
    "access": "isolated"
  },
  {
    "id": "R1-RO-07",
    "cmd": "python skills/software-project-governance/infra/verify_workflow.py check-cross-references",
    "startUTC": "2026-10-16T23:53:06.8879507Z",
    "endUTC": "2026-10-16T23:53:08.6952278Z",
    "exit": 0,
    "impact": "Repository scratch/log R1-RO-07.log under sandbox dsh454-repair; installed modules/manifests read-only when imported",
    "access": "isolated"
  },
  {
    "id": "R1-RO-08",
    "cmd": "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
    "startUTC": "2026-10-16T23:53:06.8879595Z",
    "endUTC": "2026-10-16T23:53:08.9106792Z",
    "exit": 0,
    "impact": "Repository scratch/log R1-RO-08.log under sandbox dsh454-repair; installed modules/manifests read-only when imported",
    "access": "isolated"
  }
]
```

### R1-live-oracles stdin

```python
import json,sys
from pathlib import Path
infra=Path('skills/software-project-governance/infra').resolve()
sys.path.insert(0,str(infra))
import dsh_compat as compat
root=Path.cwd()
report=compat.check_dsh_preset_compat(root=root,compositions=[root/'agent-presets/governance/agent.cordis.yml.template'])
install=report['install']
expected=Path(install['dsh_package']).resolve()/'package.json'
assert install['resolution_context']=='cli',install
assert Path(install['resolution_anchor'])==expected,install
assert len(install['oracle_packages'])==4,install
for metadata in install['oracle_packages'].values():
    assert metadata['version'] and Path(metadata['resolvedPath']).is_relative_to(expected.parent/'node_modules'),metadata
assert report['verdict']=='FAIL' and any('workflow-worker-thread' in issue for issue in report['issues']),report
assert report['isolation']['home_writes']==0,report
print(json.dumps({key:report[key] for key in ('verdict','rows_checked','rows_enabled','coverage','isolation','issues')},ensure_ascii=False,indent=2))
print(json.dumps({'install':install},ensure_ascii=False,indent=2))
```

## Real-environment command ledger

All commands ran from `D:/AI/agent/claude/coding/project_management_workflow`. For each Python/Node probe invocation the process environment was set to:

```powershell
$env:DSH_HOME = 'D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/dsh102-baseline'
$env:TEMP = $env:DSH_HOME
$env:TMP = $env:DSH_HOME
$env:DSH_INSTALL_DIR = 'C:/Users/peter/AppData/Roaming/npm'
```

Subsequent test runs additionally set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONIOENCODING=utf-8`. Installed CLI source is read-only. Writable test/probe homes and scratch trees are confined to the repository sandbox and removed by the existing scratch helpers; the pre-existing sandbox installation was not changed. Node subprocesses are invoked by `dsh_compat.py` as `[node, '--version']` and `[node, '--input-type=module', '--eval', _render_probe_script()]`; the latter receives its own freshly created `DSH_HOME`. No DSH CLI session was started. pnpm's test-only Windows junction command is `[cmd, '/c', 'mklink', '/J', <scratch>/node_modules/@deepseek-ai/dsh, <scratch>/node_modules/.pnpm/cli/node_modules/@deepseek-ai/dsh]`.

| Command (literal arguments) | Start / end (+08:00) | Exit | Impact |
|---|---|---|---|
| `python skills/software-project-governance/infra/dsh_compat.py` | `2026-10-16T23:49:17.1608536` / `23:49:19.6593601` | 0 | Baseline read-only CLI imports; isolated home writes=0; `NOT_RUN`, missing `js-yaml`. |
| `python -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_compat.py -k ResolutionContextTests -v` | `2026-10-16T23:51:53.5315340` / `23:51:55.3896240` | 1 | First focused run: 6 pass, 1 assertion error, 1 skip; repository scratch only. |
| `python skills/software-project-governance/infra/dsh_compat.py --fail-on-issues` | `2026-10-16T23:51:55.3896240` / `23:51:58.6489658` | 1 | Current CLI oracle imports succeed; isolated writes=0; template missing-module `FAIL`. The surrounding PowerShell command ended 0 because its final command was `Get-Date`. |
| `python -m pytest skills/software-project-governance/infra/tests/test_dsh_compat.py -q` | `2026-10-16T23:52:35.6341871` / `23:53:01.3203304` | 1 | 129 pass / 6 fail, including all 9 new cases passing; live imports read-only, scratch redirected. |

Further validation and structured evidence are appended below. Independent code review is required before acceptance; this diagnostic does not claim review approval.

The clean-directory command was `python -` with the following stdin (the final focused pytest invocation followed in the same driver). This records the executable operation rather than treating the descriptive `command` label in the JSON evidence as shell syntax:

```python
import datetime, json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, 'skills/software-project-governance/infra')
import dsh_compat
start = datetime.datetime.now().astimezone().isoformat()
scratch = dsh_compat._make_scratch_dir('spg-clean-discovery-')
try:
 target = scratch / 'agent-presets/governance/agent.cordis.yml.template'
 target.parent.mkdir(parents=True)
 shutil.copyfile('agent-presets/governance/agent.cordis.yml.template', target)
 found = [p.relative_to(scratch).as_posix() for p in dsh_compat.discover_compositions(scratch)]
 assert found == ['agent-presets/governance/agent.cordis.yml.template'], found
 result = dsh_compat.check_dsh_preset_compat(root=scratch, compositions=[target])
 evidence = {'command':'python - (clean directory: copy shipped template, discover_compositions, check_dsh_preset_compat)', 'start':start, 'end':datetime.datetime.now().astimezone().isoformat(), 'exit':0, 'clean_discovery':found, 'verdict':result['verdict'], 'reason':result['reason'], 'rows_enabled':result['rows_enabled'], 'rows_checked':result['rows_checked'], 'coverage':result['coverage'], 'isolation':result['isolation'], 'install':result['install'], 'issues':result['issues'], 'impact':'CLI installed files read-only; fresh repo sandbox directory only; removed afterwards'}
finally:
 dsh_compat._remove_scratch_dir(scratch)
with Path('docs/diagnostics/dsh-0.2-probe-resolution.md').open('a', encoding='utf-8') as out:
 out.write('\n\n### Clean discovery and single-template evidence\n\n```json\n' + json.dumps(evidence, ensure_ascii=False, indent=2) + '\n```\n')
print(json.dumps(evidence, ensure_ascii=False, indent=2))
cmd = [sys.executable, '-m', 'pytest', 'skills/software-project-governance/infra/tests/test_dsh_compat.py', '-q', '-k', 'ResolutionContextTests']
start = datetime.datetime.now().astimezone().isoformat()
done = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
end = datetime.datetime.now().astimezone().isoformat()
with Path('docs/diagnostics/dsh-0.2-probe-resolution.md').open('a', encoding='utf-8') as out:
 out.write('\n\n### Final resolution regression run\n\n```text\n' + json.dumps(cmd) + '\nstart=' + start + '\nend=' + end + '\nexit=' + str(done.returncode) + '\n' + done.stdout + done.stderr + '\n```\n')
print(done.stdout + done.stderr)
sys.exit(done.returncode)
```


### Validation command

```text
["C:\\Python314\\python.exe", "-m", "pytest", "skills/software-project-governance/infra/tests/test_dsh_compat.py", "-q", "-k", "not test_repo_compositions_are_discovered and not test_shipped_compositions_raise_no_findings and not test_shipped_composition_discloses_its_unverified_rows and not NoSchemaFixtureTests"]
start=2026-10-16T23:54:57.049232+08:00
end=2026-10-16T23:55:13.206160+08:00
exit=0
........................................................................................................................ [ 93%]
.........                                                             [100%]
129 passed, 6 deselected, 99 subtests passed in 15.60s

```


### Validation command

```text
["C:\\Python314\\python.exe", "skills/software-project-governance/infra/verify_workflow.py", "check-cross-references"]
start=2026-10-16T23:55:13.206875+08:00
end=2026-10-16T23:55:13.972442+08:00
exit=0

=== Cross-Reference Check ===
  Files scanned: 78
  References extracted: 740

  [PASS] No dangling references.

  [PASS] No deprecated paths.

  [PASS] No circular references.

  [PASS] Citation/note quote sync clean (FIX-432 F-4/F-A2).

  [PASS] Exploration-channel evidence forms clean (FEAT-088 F-A3).

  Probe layering (honesty statement):
    - static_evidence_form: native declarations of enrolled adapters must carry dated anchors (this check, FAIL-able)
    - feasible_probe: evidence_ref existence + anchor-date corroboration in the cited document (read-only, DOCUMENT-WIDE substring match, NOT section-scoped — a date present anywhere in the cited document corroborates, so the §-level granularity claimed by evidence prose is human-review territory; FIX-436 F-C1/DEC-317(2); the only live checks a CLI process can honestly perform here)
    - not_probeable: host-session tool liveness (web_search / route_agent) is NOT probed and NOT claimed — harness-layer tools are outside a CLI process's reach; runtime drift is governed by the manifest degraded_mode + EXP-03 and by re-dating the anchor from a live session


```


### Validation command

```text
["C:\\Python314\\python.exe", "skills/software-project-governance/infra/verify_workflow.py", "check-manifest-consistency"]
start=2026-10-16T23:55:13.973496+08:00
end=2026-10-16T23:55:14.746248+08:00
exit=0

=== Manifest Consistency Check ===
  Canonical files:  1147
  Actual files:     1347

  [PASS] Manifest and filesystem are consistent.

```


### Validation command

```text
["C:\\Python314\\python.exe", "skills/software-project-governance/infra/verify_workflow.py"]
start=2026-10-16T23:55:14.746794+08:00
end=2026-10-16T23:55:16.765595+08:00
exit=0
== Workflow Plugin Verification ==
[INFO] REQUIRED_FILES loaded from manifest.json (1255 entries)
[OK] file exists: Agents -> AGENTS.md
[OK] file exists: Readme -> README.md
[OK] file exists: .Gitattributes -> .gitattributes
[OK] file exists: .Gitignore -> .gitignore
[OK] file exists: Package -> package.json
[OK] file exists: Pyproject -> pyproject.toml
[OK] file exists: License -> LICENSE
[OK] file exists: Changelog -> changelog.md
[OK] file exists: Cordis.Patch -> cordis.patch.yml
[OK] file exists: Skill: software-project-governance -> skills\software-project-governance\SKILL.md
[OK] file exists: core/governance-packs.json -> skills\software-project-governance\core\governance-packs.json
[OK] file exists: core/capability-registry.json -> skills\software-project-governance\core\capability-registry.json
[OK] file exists: core/lifecycle-registry.json -> skills\software-project-governance\core\lifecycle-registry.json
[OK] file exists: core/loop-engineering-registry.json -> skills\software-project-governance\core\loop-engineering-registry.json
[OK] file exists: core/loop-runtime-claim-allowlist.json -> skills\software-project-governance\core\loop-runtime-claim-allowlist.json
[OK] file exists: core/loop-runtime-claim-authority.json -> skills\software-project-governance\core\loop-runtime-claim-authority.json
[OK] file exists: core/architecture-health.json -> skills\software-project-governance\core\architecture-health.json
[OK] file exists: core/Technical Debt Ledger -> skills\software-project-governance\core\technical-debt-ledger.md
[OK] file exists: core/release-ledger.schema.json -> skills\software-project-governance\core\release-ledger.schema.json
[OK] file exists: core/version-projections.json -> skills\software-project-governance\core\version-projections.json
[OK] file exists: infra/Tools -> skills\software-project-governance\infra\TOOLS.md
[OK] file exists: infra/Verify Workflow -> skills\software-project-governance\infra\verify_workflow.py
[OK] file exists: checks/  Init   -> skills\software-project-governance\infra\checks\__init__.py
[OK] file exists: checks/Manifest -> skills\software-project-governance\infra\checks\manifest.py
[OK] file exists: checks/Capability Registry -> skills\software-project-governance\infra\checks\capability_registry.py
[OK] file exists: checks/Flow Unit Runtime -> skills\software-project-governance\infra\checks\flow_unit_runtime.py
[OK] file exists: checks/Loop Runtime Claims -> skills\software-project-governance\infra\checks\loop_runtime_claims.py
[OK] file exists: checks/Loop Runtime Claim Attestation -> skills\software-project-governance\infra\checks\loop_runtime_claim_attestation.py
[OK] file exists: checks/Loop Gate Processor -> skills\software-project-governance\infra\checks\loop_gate_processor.py
[OK] file exists: tests/Test Loop Runtime Claim Attestation -> skills\software-project-governance\infra\tests\test_loop_runtime_claim_attestation.py
[OK] file exists: infra/Verify E2E -> skills\software-project-governance\infra\verify-e2e.sh
[OK] file exists: infra/Bootstrap -> skills\software-project-governance\infra\bootstrap.sh
[OK] file exists: infra/Bootstrap (skills/software-project-governance/infra/bootstrap.cmd) -> skills\software-project-governance\infra\bootstrap.cmd
[OK] file exists: infra/Archive -> skills\software-project-governance\infra\archive.py
[OK] file exists: infra/Change Triage -> skills\software-project-governance\infra\change_triage.py
[OK] file exists: checks/Triage Domain -> skills\software-project-governance\infra\checks\triage_domain.py
[OK] file exists: tests/Test Change Triage -> skills\software-project-governance\infra\tests\test_change_triage.py
[OK] file exists: infra/Dsh Compat -> skills\software-project-governance\infra\dsh_compat.py
[OK] file exists: tests/Test Dsh Compat -> skills\software-project-governance\infra\tests\test_dsh_compat.py
[OK] file exists: infra/Sync Entry Projection -> skills\software-project-governance\infra\sync_entry_projection.py
[OK] file exists: tests/Test Entry Projection -> skills\software-project-governance\infra\tests\test_entry_projection.py
[OK] file exists: Change Triage -> commands\change-triage.md
[OK] file exists: dsh/host-contract.json -> adapters\dsh\host-contract.json
[OK] file exists: fixtures/host-facts-0.1.5-rc.1.json -> adapters\dsh\fixtures\host-facts-0.1.5-rc.1.json
[OK] file exists: Index -> lib\index.js
[OK] file exists: governance/Agent.Cordis.Yml -> agent-presets\governance\agent.cordis.yml.template
[OK] file exists: governance/Preset -> agent-presets\governance\preset.yml
[OK] file exists: Plugin -> .zcode-plugin\plugin.json
[OK] file exists: release/Release Checklist 0.45.0 -> docs\release\release-checklist-0.45.0.md
[OK] file exists: release/Feature Flags 0.45.0 -> docs\release\feature-flags-0.45.0.md
[OK] file exists: release/Rollback Plan 0.45.0 -> docs\release\rollback-plan-0.45.0.md
[OK] file exists: marketplace/Official Submission 0.46.0 -> docs\marketplace\official-submission-0.46.0.md
[OK] file exists: marketplace/Ecosystem Positioning 0.46.0 -> docs\marketplace\ecosystem-positioning-0.46.0.md
[OK] file exists: marketplace/Comparison 0.46.0 -> docs\marketplace\comparison-0.46.0.md
[OK] file exists: marketplace/Migration Guide 0.46.0 -> docs\marketplace\migration-guide-0.46.0.md
[OK] file exists: marketplace/Examples 0.46.0 -> docs\marketplace\examples-0.46.0.md
[OK] file exists: marketplace/Zcode Local Load 0.56.0 -> docs\marketplace\zcode-local-load-0.56.0.md
[OK] file exists: marketplace/Claude Code Submission 0.56.0 -> docs\marketplace\claude-code-submission-0.56.0.md
[OK] file exists: marketplace/Official Readiness Gap Analysis 0.56.0 -> docs\marketplace\official-readiness-gap-analysis-0.56.0.md
[OK] file exists: marketplace/Marketplace Source Matrix 0.65.3 -> docs\marketplace\marketplace-source-matrix-0.65.3.md
[OK] file exists: release/Release Lineage Audit 0.65.3 -> docs\release\release-lineage-audit-0.65.3.md
[OK] file exists: release/Release Checklist 0.46.0 -> docs\release\release-checklist-0.46.0.md
[OK] file exists: release/Feature Flags 0.46.0 -> docs\release\feature-flags-0.46.0.md
[OK] file exists: release/Rollback Plan 0.46.0 -> docs\release\rollback-plan-0.46.0.md
[OK] file exists: release/Release Checklist 0.47.0 -> docs\release\release-checklist-0.47.0.md
[OK] file exists: release/Feature Flags 0.47.0 -> docs\release\feature-flags-0.47.0.md
[OK] file exists: release/Rollback Plan 0.47.0 -> docs\release\rollback-plan-0.47.0.md
[OK] file exists: release/Release Checklist 0.48.0 -> docs\release\release-checklist-0.48.0.md
[OK] file exists: release/Feature Flags 0.48.0 -> docs\release\feature-flags-0.48.0.md
[OK] file exists: release/Rollback Plan 0.48.0 -> docs\release\rollback-plan-0.48.0.md
[OK] file exists: release/Release Checklist 0.49.0 -> docs\release\release-checklist-0.49.0.md
[OK] file exists: release/Feature Flags 0.49.0 -> docs\release\feature-flags-0.49.0.md
[OK] file exists: release/Rollback Plan 0.49.0 -> docs\release\rollback-plan-0.49.0.md
[OK] file exists: release/Release Checklist 0.50.0 -> docs\release\release-checklist-0.50.0.md
[OK] file exists: release/Feature Flags 0.50.0 -> docs\release\feature-flags-0.50.0.md
[OK] file exists: release/Rollback Plan 0.50.0 -> docs\release\rollback-plan-0.50.0.md
[OK] file exists: release/Release Checklist 0.50.2 -> docs\release\release-checklist-0.50.2.md
[OK] file exists: release/Feature Flags 0.50.2 -> docs\release\feature-flags-0.50.2.md
[OK] file exists: release/Rollback Plan 0.50.2 -> docs\release\rollback-plan-0.50.2.md
[OK] file exists: release/Release Checklist 0.50.3 -> docs\release\release-checklist-0.50.3.md
[OK] file exists: release/Feature Flags 0.50.3 -> docs\release\feature-flags-0.50.3.md
[OK] file exists: release/Rollback Plan 0.50.3 -> docs\release\rollback-plan-0.50.3.md
[OK] file exists: release/Release Checklist 0.51.0 -> docs\release\release-checklist-0.51.0.md
[OK] file exists: release/Feature Flags 0.51.0 -> docs\release\feature-flags-0.51.0.md
[OK] file exists: release/Rollback Plan 0.51.0 -> docs\release\rollback-plan-0.51.0.md
[OK] file exists: release/Release Checklist 0.52.0 -> docs\release\release-checklist-0.52.0.md
[OK] file exists: release/Feature Flags 0.52.0 -> docs\release\feature-flags-0.52.0.md
[OK] file exists: release/Rollback Plan 0.52.0 -> docs\release\rollback-plan-0.52.0.md
[OK] file exists: release/Release Checklist 0.53.0 -> docs\release\release-checklist-0.53.0.md
[OK] file exists: release/Feature Flags 0.53.0 -> docs\release\feature-flags-0.53.0.md
[OK] file exists: release/Rollback Plan 0.53.0 -> docs\release\rollback-plan-0.53.0.md
[OK] file exists: release/Release Checklist 0.54.0 -> docs\release\release-checklist-0.54.0.md
[OK] file exists: release/Feature Flags 0.54.0 -> docs\release\feature-flags-0.54.0.md
[OK] file exists: release/Rollback Plan 0.54.0 -> docs\release\rollback-plan-0.54.0.md
[OK] file exists: release/Release Checklist 0.54.1 -> docs\release\release-checklist-0.54.1.md
[OK] file exists: release/Feature Flags 0.54.1 -> docs\release\feature-flags-0.54.1.md
[OK] file exists: release/Rollback Plan 0.54.1 -> docs\release\rollback-plan-0.54.1.md
[OK] file exists: release/Release Checklist 0.55.0 -> docs\release\release-checklist-0.55.0.md
[OK] file exists: release/Feature Flags 0.55.0 -> docs\release\feature-flags-0.55.0.md
[OK] file exists: release/Rollback Plan 0.55.0 -> docs\release\rollback-plan-0.55.0.md
[OK] file exists: release/Release Checklist 0.55.1 -> docs\release\release-checklist-0.55.1.md
[OK] file exists: release/Feature Flags 0.55.1 -> docs\release\feature-flags-0.55.1.md
[OK] file exists: release/Rollback Plan 0.55.1 -> docs\release\rollback-plan-0.55.1.md
[OK] file exists: release/Release Checklist 0.55.2 -> docs\release\release-checklist-0.55.2.md
[OK] file exists: release/Feature Flags 0.55.2 -> docs\release\feature-flags-0.55.2.md
[OK] file exists: release/Rollback Plan 0.55.2 -> docs\release\rollback-plan-0.55.2.md
[OK] file exists: release/Release Checklist 0.55.3 -> docs\release\release-checklist-0.55.3.md
[OK] file exists: release/Feature Flags 0.55.3 -> docs\release\feature-flags-0.55.3.md
[OK] file exists: release/Rollback Plan 0.55.3 -> docs\release\rollback-plan-0.55.3.md
[OK] file exists: release/Release Checklist 0.56.0 -> docs\release\release-checklist-0.56.0.md
[OK] file exists: release/Feature Flags 0.56.0 -> docs\release\feature-flags-0.56.0.md
[OK] file exists: release/Rollback Plan 0.56.0 -> docs\release\rollback-plan-0.56.0.md
[OK] file exists: migration/Dynamic Flow Gate Migration 0.55.0 -> docs\migration\dynamic-flow-gate-migration-0.55.0.md
[OK] file exists: release/Release Checklist 0.56.1 -> docs\release\release-checklist-0.56.1.md
[OK] file exists: release/Feature Flags 0.56.1 -> docs\release\feature-flags-0.56.1.md
[OK] file exists: release/Rollback Plan 0.56.1 -> docs\release\rollback-plan-0.56.1.md
[OK] file exists: release/Release Checklist 0.57.0 -> docs\release\release-checklist-0.57.0.md
[OK] file exists: release/Feature Flags 0.57.0 -> docs\release\feature-flags-0.57.0.md
[OK] file exists: release/Rollback Plan 0.57.0 -> docs\release\rollback-plan-0.57.0.md
[OK] file exists: release/Release Checklist 0.58.0 -> docs\release\release-checklist-0.58.0.md
[OK] file exists: release/Feature Flags 0.58.0 -> docs\release\feature-flags-0.58.0.md
[OK] file exists: release/Rollback Plan 0.58.0 -> docs\release\rollback-plan-0.58.0.md
[OK] file exists: release/Release Checklist 0.59.0 -> docs\release\release-checklist-0.59.0.md
[OK] file exists: release/Feature Flags 0.59.0 -> docs\release\feature-flags-0.59.0.md
[OK] file exists: release/Rollback Plan 0.59.0 -> docs\release\rollback-plan-0.59.0.md
[OK] file exists: release/Release Checklist 0.61.1 -> docs\release\release-checklist-0.61.1.md
[OK] file exists: release/Feature Flags 0.61.1 -> docs\release\feature-flags-0.61.1.md
[OK] file exists: release/Rollback Plan 0.61.1 -> docs\release\rollback-plan-0.61.1.md
[OK] file exists: release/Release Checklist 0.61.2 -> docs\release\release-checklist-0.61.2.md
[OK] file exists: release/Feature Flags 0.61.2 -> docs\release\feature-flags-0.61.2.md
[OK] file exists: release/Rollback Plan 0.61.2 -> docs\release\rollback-plan-0.61.2.md
[OK] file exists: governance/Scenario A -> commands\governance\scenario-a.md
[OK] file exists: governance/Scenario B -> commands\governance\scenario-b.md
[OK] file exists: governance/Scenario C -> commands\governance\scenario-c.md
[OK] file exists: governance/Scenario D -> commands\governance\scenario-d.md
[OK] file exists: governance/Scenario E -> commands\governance\scenario-e.md
[OK] file exists: governance/Scenario F -> commands\governance\scenario-f.md
[OK] file exists: governance/Bootstrap -> commands\governance\bootstrap.md
[OK] file exists: governance/Snapshot Schema -> commands\governance\snapshot-schema.md
[OK] file exists: governance/Overview -> commands\governance\overview.md
[OK] file exists: core/Audit Framework -> skills\software-project-governance\core\audit-framework.md
[OK] file exists: core/Lifecycle -> skills\software-project-governance\core\lifecycle.md
[OK] file exists: core/Manifest -> skills\software-project-governance\core\manifest.md
[OK] file exists: core/Onboarding -> skills\software-project-governance\core\onboarding.md
[OK] file exists: core/Profiles -> skills\software-project-governance\core\profiles.md
[OK] file exists: protocol/Command Schema -> skills\software-project-governance\core\protocol\command-schema.md
[OK] file exists: protocol/External Command Contract -> skills\software-project-governance\core\protocol\external-command-contract.md
[OK] file exists: protocol/Headless Runner Sample -> skills\software-project-governance\core\protocol\headless-runner-sample.md
[OK] file exists: protocol/Plugin Contract -> skills\software-project-governance\core\protocol\plugin-contract.md
[OK] file exists: protocol/Workflow Schema -> skills\software-project-governance\core\protocol\workflow-schema.md
[OK] file exists: core/Stage Gates -> skills\software-project-governance\core\stage-gates.md
[OK] file exists: core/Task Gate Model -> skills\software-project-governance\core\task-gate-model.md
[OK] file exists: core/Technical Debt Ledger (skills/software-project-governance/core/technical-debt-ledger.md) -> skills\software-project-governance\core\technical-debt-ledger.md
[OK] file exists: templates/Decision Log -> skills\software-project-governance\core\templates\decision-log.md
[OK] file exists: deterministic-scaffolds/Cli Tool -> skills\software-project-governance\core\templates\deterministic-scaffolds\cli-tool.md
[OK] file exists: deterministic-scaffolds/Index -> skills\software-project-governance\core\templates\deterministic-scaffolds\index.md
[OK] file exists: deterministic-scaffolds/Web App -> skills\software-project-governance\core\templates\deterministic-scaffolds\web-app.md
[OK] file exists: deterministic-scaffolds/Workflow Plugin -> skills\software-project-governance\core\templates\deterministic-scaffolds\workflow-plugin.md
[OK] file exists: templates/Evidence Log -> skills\software-project-governance\core\templates\evidence-log.md
[OK] file exists: templates/Executable Acceptance Contract -> skills\software-project-governance\core\templates\executable-acceptance-contract.md
[OK] file exists: templates/Execution Packet -> skills\software-project-governance\core\templates\execution-packet.md
[OK] file exists: templates/Plan Tracker -> skills\software-project-governance\core\templates\plan-tracker.md
[OK] file exists: templates/Product Success Contract -> skills\software-project-governance\core\templates\product-success-contract.md
[OK] file exists: templates/Quality Budget -> skills\software-project-governance\core\templates\quality-budget.md
[OK] file exists: templates/Risk Log -> skills\software-project-governance\core\templates\risk-log.md
[OK] file exists: templates/User Interruption Policy -> skills\software-project-governance\core\templates\user-interruption-policy.md
[OK] file exists: templates/Vertical Slice Delivery Packet -> skills\software-project-governance\core\templates\vertical-slice-delivery-packet.md
[OK] file exists: core/Versioning -> skills\software-project-governance\core\VERSIONING.md
[OK] file exists: references/Agent Communication Protocol -> skills\software-project-governance\references\agent-communication-protocol.md
[OK] file exists: references/Agent Dispatch Template -> skills\software-project-governance\references\agent-dispatch-template.md
[OK] file exists: references/Agent Failure Modes -> skills\software-project-governance\references\agent-failure-modes.md
[OK] file exists: references/Authority Ledger -> skills\software-project-governance\references\authority-ledger.md
[OK] file exists: references/Behavior Protocol -> skills\software-project-governance\references\behavior-protocol.md
[OK] file exists: references/Change Impact Checklist -> skills\software-project-governance\references\change-impact-checklist.md
[OK] file exists: references/Company Practices Summary -> skills\software-project-governance\references\company-practices-summary.md
[OK] file exists: references/Evidence Id Prefix Conventions -> skills\software-project-governance\references\evidence-id-prefix-conventions.md
[OK] file exists: references/Interaction Boundary -> skills\software-project-governance\references\interaction-boundary.md
[OK] file exists: references/Loop Role Mapping -> skills\software-project-governance\references\loop-role-mapping.md
[OK] file exists: references/Methodology Routing -> skills\software-project-governance\references\methodology-routing.md
[OK] file exists: references/Skill Index -> skills\software-project-governance\references\skill-index.md
[OK] file exists: references/Stage Skill Depth Rubric -> skills\software-project-governance\references\stage-skill-depth-rubric.md
[OK] file exists: hooks/Commit Msg -> skills\software-project-governance\infra\hooks\commit-msg
[OK] file exists: hooks/Post Commit -> skills\software-project-governance\infra\hooks\post-commit
[OK] file exists: hooks/Pre Commit -> skills\software-project-governance\infra\hooks\pre-commit
[OK] file exists: hooks/Prepare Commit Msg -> skills\software-project-governance\infra\hooks\prepare-commit-msg
[OK] file exists: Skill: stage-architecture -> skills\stage-architecture\SKILL.md
[OK] file exists: Skill: stage-cicd -> skills\stage-cicd\SKILL.md
[OK] file exists: Skill: stage-development -> skills\stage-development\SKILL.md
[OK] file exists: Skill: stage-infra -> skills\stage-infra\SKILL.md
[OK] file exists: Skill: stage-initiation -> skills\stage-initiation\SKILL.md
[OK] file exists: Skill: stage-maintenance -> skills\stage-maintenance\SKILL.md
[OK] file exists: Skill: stage-operations -> skills\stage-operations\SKILL.md
[OK] file exists: Skill: stage-release -> skills\stage-release\SKILL.md
[OK] file exists: Skill: stage-research -> skills\stage-research\SKILL.md
[OK] file exists: Skill: stage-selection -> skills\stage-selection\SKILL.md
[OK] file exists: Skill: stage-testing -> skills\stage-testing\SKILL.md
[OK] file exists: Skill: code-review -> skills\code-review\SKILL.md
[OK] file exists: Skill: design-review -> skills\design-review\SKILL.md
[OK] file exists: Skill: main-workflow -> skills\main-workflow\SKILL.md
[OK] file exists: Skill: okr -> skills\okr\SKILL.md
[OK] file exists: Skill: pr-faq -> skills\pr-faq\SKILL.md
[OK] file exists: Skill: release-checklist -> skills\release-checklist\SKILL.md
[OK] file exists: Skill: release-review -> skills\release-review\SKILL.md
[OK] file exists: Skill: requirement-clarification -> skills\requirement-clarification\SKILL.md
[OK] file exists: Skill: requirement-review -> skills\requirement-review\SKILL.md
[OK] file exists: Skill: retro-meeting -> skills\retro-meeting\SKILL.md
[OK] file exists: Skill: retro-review -> skills\retro-review\SKILL.md
[OK] file exists: Skill: six-pager -> skills\six-pager\SKILL.md
[OK] file exists: Skill: tech-review -> skills\tech-review\SKILL.md
[OK] file exists: Skill: test-review -> skills\test-review\SKILL.md
[OK] file exists: Analyst -> agents\analyst.md
[OK] file exists: Architect -> agents\architect.md
[OK] file exists: Code Reviewer -> agents\code-reviewer.md
[OK] file exists: Coordinator -> agents\coordinator.md
[OK] file exists: Design Reviewer -> agents\design-reviewer.md
[OK] file exists: Developer -> agents\developer.md
[OK] file exists: Devops -> agents\devops.md
[OK] file exists: Governance Developer -> agents\governance-developer.md
[OK] file exists: Maintenance -> agents\maintenance.md
[OK] file exists: Qa -> agents\qa.md
[OK] file exists: Release Reviewer -> agents\release-reviewer.md
[OK] file exists: Release -> agents\release.md
[OK] file exists: Requirement Reviewer -> agents\requirement-reviewer.md
[OK] file exists: Retro Reviewer -> agents\retro-reviewer.md
[OK] file exists: Test Reviewer -> agents\test-reviewer.md
[OK] file exists: Change Triage (commands/change-triage.md) -> commands\change-triage.md
[OK] file exists: Governance Cleanup -> commands\governance-cleanup.md
[OK] file exists: Governance Gate -> commands\governance-gate.md
[OK] file exists: Governance Init -> commands\governance-init.md
[OK] file exists: Governance Review -> commands\governance-review.md
[OK] file exists: Governance Status -> commands\governance-status.md
[OK] file exists: Governance Update -> commands\governance-update.md
[OK] file exists: Governance Verify -> commands\governance-verify.md
[OK] file exists: Governance -> commands\governance.md
[OK] file exists: Readme: claude -> adapters\claude\README.md
[OK] file exists: Readme: codex -> adapters\codex\README.md
[OK] file exists: Readme: dsh -> adapters\dsh\README.md
[OK] file exists: Readme: gemini -> adapters\gemini\README.md
[OK] file exists: Readme: opencode -> adapters\opencode\README.md
[OK] file exists: Readme: pi -> adapters\pi\README.md
[OK] file exists: claude/adapter-manifest.json -> adapters\claude\adapter-manifest.json
[OK] file exists: codex/adapter-manifest.json -> adapters\codex\adapter-manifest.json
[OK] file exists: dsh/adapter-manifest.json -> adapters\dsh\adapter-manifest.json
[OK] file exists: gemini/adapter-manifest.json -> adapters\gemini\adapter-manifest.json
[OK] file exists: opencode/adapter-manifest.json -> adapters\opencode\adapter-manifest.json
[OK] file exists: pi/adapter-manifest.json -> adapters\pi\adapter-manifest.json
[OK] file exists: claude/Launch -> adapters\claude\launch.py
[OK] file exists: codex/Launch -> adapters\codex\launch.py
[OK] file exists: dsh/Launch -> adapters\dsh\launch.py
[OK] file exists: gemini/Launch -> adapters\gemini\launch.py
[OK] file exists: opencode/Launch -> adapters\opencode\launch.py
[OK] file exists: pi/Launch -> adapters\pi\launch.py
[OK] file exists: dsh/Smoke Attribution -> adapters\dsh\smoke_attribution.py
[OK] file exists: fixtures/host-facts-0.1.5-rc.1.json (adapters/dsh/fixtures/host-facts-0.1.5-rc.1.json) -> adapters\dsh\fixtures\host-facts-0.1.5-rc.1.json
[OK] file exists: Marketplace -> .claude-plugin\marketplace.json
[OK] file exists: Plugin (.claude-plugin/plugin.json) -> .claude-plugin\plugin.json
[OK] file exists: assets/Composer Icon -> .claude-plugin\assets\composer-icon.svg
[OK] file exists: assets/Governance Preview -> .claude-plugin\assets\governance-preview.svg
[OK] file exists: assets/Logo -> .claude-plugin\assets\logo.svg
[OK] file exists: Plugin (.codex-plugin/plugin.json) -> .codex-plugin\plugin.json
[OK] file exists: Plugin (.zcode-plugin/plugin.json) -> .zcode-plugin\plugin.json
[OK] file exists: assets/Composer Icon (.zcode-plugin/assets/composer-icon.svg) -> .zcode-plugin\assets\composer-icon.svg
[OK] file exists: assets/Governance Preview (.zcode-plugin/assets/governance-preview.svg) -> .zcode-plugin\assets\governance-preview.svg
[OK] file exists: assets/Logo (.zcode-plugin/assets/logo.svg) -> .zcode-plugin\assets\logo.svg
[OK] file exists: Marketplace JSON: .agents/plugins -> .agents\plugins\marketplace.json
[OK] file exists: governance/Bootstrap (commands/governance/bootstrap.md) -> commands\governance\bootstrap.md
[OK] file exists: governance/Overview (commands/governance/overview.md) -> commands\governance\overview.md
[OK] file exists: governance/Scenario A (commands/governance/scenario-a.md) -> commands\governance\scenario-a.md
[OK] file exists: governance/Scenario B (commands/governance/scenario-b.md) -> commands\governance\scenario-b.md
[OK] file exists: governance/Scenario C (commands/governance/scenario-c.md) -> commands\governance\scenario-c.md
[OK] file exists: governance/Scenario D (commands/governance/scenario-d.md) -> commands\governance\scenario-d.md
[OK] file exists: governance/Scenario E (commands/governance/scenario-e.md) -> commands\governance\scenario-e.md
[OK] file exists: governance/Scenario F (commands/governance/scenario-f.md) -> commands\governance\scenario-f.md
[OK] file exists: governance/Snapshot Schema (commands/governance/snapshot-schema.md) -> commands\governance\snapshot-schema.md
[OK] file exists: Changelog (project/CHANGELOG.md) -> project\CHANGELOG.md
[OK] file exists: .governance/Decision Log -> project\e2e-test-project\.governance\decision-log.md
[OK] file exists: .governance/Evidence Log -> project\e2e-test-project\.governance\evidence-log.md
[OK] file exists: .governance/Plan Tracker -> project\e2e-test-project\.governance\plan-tracker.md
[OK] file exists: .governance/Risk Log -> project\e2e-test-project\.governance\risk-log.md
[OK] file exists: .governance/Session Snapshot -> project\e2e-test-project\.governance\session-snapshot.md
[OK] file exists: agents/Analyst -> project\e2e-test-project\agents\analyst.md
[OK] file exists: agents/Architect -> project\e2e-test-project\agents\architect.md
[OK] file exists: agents/Code Reviewer -> project\e2e-test-project\agents\code-reviewer.md
[OK] file exists: agents/Coordinator -> project\e2e-test-project\agents\coordinator.md
[OK] file exists: agents/Design Reviewer -> project\e2e-test-project\agents\design-reviewer.md
[OK] file exists: agents/Developer -> project\e2e-test-project\agents\developer.md
[OK] file exists: agents/Devops -> project\e2e-test-project\agents\devops.md
[OK] file exists: agents/Governance Developer -> project\e2e-test-project\agents\governance-developer.md
[OK] file exists: agents/Maintenance -> project\e2e-test-project\agents\maintenance.md
[OK] file exists: agents/Qa -> project\e2e-test-project\agents\qa.md
[OK] file exists: agents/Release Reviewer -> project\e2e-test-project\agents\release-reviewer.md
[OK] file exists: agents/Release -> project\e2e-test-project\agents\release.md
[OK] file exists: agents/Requirement Reviewer -> project\e2e-test-project\agents\requirement-reviewer.md
[OK] file exists: agents/Retro Reviewer -> project\e2e-test-project\agents\retro-reviewer.md
[OK] file exists: agents/Test Reviewer -> project\e2e-test-project\agents\test-reviewer.md
[OK] file exists: e2e-test-project/Agents -> project\e2e-test-project\AGENTS.md
[OK] file exists: e2e-test-project/Claude -> project\e2e-test-project\CLAUDE.md
[OK] file exists: governance/Bootstrap (project/e2e-test-project/commands/governance/bootstrap.md) -> project\e2e-test-project\commands\governance\bootstrap.md
[OK] file exists: governance/Overview (project/e2e-test-project/commands/governance/overview.md) -> project\e2e-test-project\commands\governance\overview.md
[OK] file exists: governance/Scenario A (project/e2e-test-project/commands/governance/scenario-a.md) -> project\e2e-test-project\commands\governance\scenario-a.md
[OK] file exists: governance/Scenario B (project/e2e-test-project/commands/governance/scenario-b.md) -> project\e2e-test-project\commands\governance\scenario-b.md
[OK] file exists: governance/Scenario C (project/e2e-test-project/commands/governance/scenario-c.md) -> project\e2e-test-project\commands\governance\scenario-c.md
[OK] file exists: governance/Scenario D (project/e2e-test-project/commands/governance/scenario-d.md) -> project\e2e-test-project\commands\governance\scenario-d.md
[OK] file exists: governance/Scenario E (project/e2e-test-project/commands/governance/scenario-e.md) -> project\e2e-test-project\commands\governance\scenario-e.md
[OK] file exists: governance/Scenario F (project/e2e-test-project/commands/governance/scenario-f.md) -> project\e2e-test-project\commands\governance\scenario-f.md
[OK] file exists: governance/Snapshot Schema (project/e2e-test-project/commands/governance/snapshot-schema.md) -> project\e2e-test-project\commands\governance\snapshot-schema.md
[OK] file exists: commands/Governance Cleanup -> project\e2e-test-project\commands\governance-cleanup.md
[OK] file exists: commands/Governance Gate -> project\e2e-test-project\commands\governance-gate.md
[OK] file exists: commands/Governance Init -> project\e2e-test-project\commands\governance-init.md
[OK] file exists: commands/Governance Review -> project\e2e-test-project\commands\governance-review.md
[OK] file exists: commands/Governance Status -> project\e2e-test-project\commands\governance-status.md
[OK] file exists: commands/Governance Update -> project\e2e-test-project\commands\governance-update.md
[OK] file exists: commands/Governance Verify -> project\e2e-test-project\commands\governance-verify.md
[OK] file exists: commands/Governance -> project\e2e-test-project\commands\governance.md
[OK] file exists: e2e-test-project/E2E Test Checklist -> project\e2e-test-project\E2E-TEST-CHECKLIST.md
[OK] file exists: e2e-test-project/Gemini -> project\e2e-test-project\GEMINI.md
[OK] file exists: Readme: e2e-test-project -> project\e2e-test-project\README.md
[OK] file exists: Skill: code-review (project/e2e-test-project/skills/code-review/SKILL.md) -> project\e2e-test-project\skills\code-review\SKILL.md
[OK] file exists: Skill: design-review (project/e2e-test-project/skills/design-review/SKILL.md) -> project\e2e-test-project\skills\design-review\SKILL.md
[OK] file exists: Skill: main-workflow (project/e2e-test-project/skills/main-workflow/SKILL.md) -> project\e2e-test-project\skills\main-workflow\SKILL.md
[OK] file exists: Skill: okr (project/e2e-test-project/skills/okr/SKILL.md) -> project\e2e-test-project\skills\okr\SKILL.md
[OK] file exists: Skill: pr-faq (project/e2e-test-project/skills/pr-faq/SKILL.md) -> project\e2e-test-project\skills\pr-faq\SKILL.md
[OK] file exists: Skill: release-checklist (project/e2e-test-project/skills/release-checklist/SKILL.md) -> project\e2e-test-project\skills\release-checklist\SKILL.md
[OK] file exists: Skill: release-review (project/e2e-test-project/skills/release-review/SKILL.md) -> project\e2e-test-project\skills\release-review\SKILL.md
[OK] file exists: Skill: requirement-clarification (project/e2e-test-project/skills/requirement-clarification/SKILL.md) -> project\e2e-test-project\skills\requirement-clarification\SKILL.md
[OK] file exists: Skill: requirement-review (project/e2e-test-project/skills/requirement-review/SKILL.md) -> project\e2e-test-project\skills\requirement-review\SKILL.md
[OK] file exists: Skill: retro-meeting (project/e2e-test-project/skills/retro-meeting/SKILL.md) -> project\e2e-test-project\skills\retro-meeting\SKILL.md
[OK] file exists: Skill: retro-review (project/e2e-test-project/skills/retro-review/SKILL.md) -> project\e2e-test-project\skills\retro-review\SKILL.md
[OK] file exists: Skill: six-pager (project/e2e-test-project/skills/six-pager/SKILL.md) -> project\e2e-test-project\skills\six-pager\SKILL.md
[OK] file exists: core/Audit Framework (project/e2e-test-project/skills/software-project-governance/core/audit-framework.md) -> project\e2e-test-project\skills\software-project-governance\core\audit-framework.md
[OK] file exists: core/Lifecycle (project/e2e-test-project/skills/software-project-governance/core/lifecycle.md) -> project\e2e-test-project\skills\software-project-governance\core\lifecycle.md
[OK] file exists: core/Manifest (project/e2e-test-project/skills/software-project-governance/core/manifest.md) -> project\e2e-test-project\skills\software-project-governance\core\manifest.md
[OK] file exists: core/Onboarding (project/e2e-test-project/skills/software-project-governance/core/onboarding.md) -> project\e2e-test-project\skills\software-project-governance\core\onboarding.md
[OK] file exists: core/Profiles (project/e2e-test-project/skills/software-project-governance/core/profiles.md) -> project\e2e-test-project\skills\software-project-governance\core\profiles.md
[OK] file exists: protocol/Command Schema (project/e2e-test-project/skills/software-project-governance/core/protocol/command-schema.md) -> project\e2e-test-project\skills\software-project-governance\core\protocol\command-schema.md
[OK] file exists: protocol/External Command Contract (project/e2e-test-project/skills/software-project-governance/core/protocol/external-command-contract.md) -> project\e2e-test-project\skills\software-project-governance\core\protocol\external-command-contract.md
[OK] file exists: protocol/Headless Runner Sample (project/e2e-test-project/skills/software-project-governance/core/protocol/headless-runner-sample.md) -> project\e2e-test-project\skills\software-project-governance\core\protocol\headless-runner-sample.md
[OK] file exists: protocol/Plugin Contract (project/e2e-test-project/skills/software-project-governance/core/protocol/plugin-contract.md) -> project\e2e-test-project\skills\software-project-governance\core\protocol\plugin-contract.md
[OK] file exists: protocol/Workflow Schema (project/e2e-test-project/skills/software-project-governance/core/protocol/workflow-schema.md) -> project\e2e-test-project\skills\software-project-governance\core\protocol\workflow-schema.md
[OK] file exists: core/Stage Gates (project/e2e-test-project/skills/software-project-governance/core/stage-gates.md) -> project\e2e-test-project\skills\software-project-governance\core\stage-gates.md
[OK] file exists: core/Task Gate Model (project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md) -> project\e2e-test-project\skills\software-project-governance\core\task-gate-model.md
[OK] file exists: templates/Decision Log (project/e2e-test-project/skills/software-project-governance/core/templates/decision-log.md) -> project\e2e-test-project\skills\software-project-governance\core\templates\decision-log.md
[OK] file exists: templates/Evidence Log (project/e2e-test-project/skills/software-project-governance/core/templates/evidence-log.md) -> project\e2e-test-project\skills\software-project-governance\core\templates\evidence-log.md
[OK] file exists: templates/Execution Packet (project/e2e-test-project/skills/software-project-governance/core/templates/execution-packet.md) -> project\e2e-test-project\skills\software-project-governance\core\templates\execution-packet.md
[OK] file exists: templates/Plan Tracker (project/e2e-test-project/skills/software-project-governance/core/templates/plan-tracker.md) -> project\e2e-test-project\skills\software-project-governance\core\templates\plan-tracker.md
[OK] file exists: templates/Risk Log (project/e2e-test-project/skills/software-project-governance/core/templates/risk-log.md) -> project\e2e-test-project\skills\software-project-governance\core\templates\risk-log.md
[OK] file exists: core/Versioning (project/e2e-test-project/skills/software-project-governance/core/VERSIONING.md) -> project\e2e-test-project\skills\software-project-governance\core\VERSIONING.md
[OK] file exists: Readme: tests -> project\e2e-test-project\skills\software-project-governance\infra\tests\README.md
[OK] file exists: infra/Tools (project/e2e-test-project/skills/software-project-governance/infra/TOOLS.md) -> project\e2e-test-project\skills\software-project-governance\infra\TOOLS.md
[OK] file exists: references/Agent Communication Protocol (project/e2e-test-project/skills/software-project-governance/references/agent-communication-protocol.md) -> project\e2e-test-project\skills\software-project-governance\references\agent-communication-protocol.md
[OK] file exists: references/Agent Dispatch Template (project/e2e-test-project/skills/software-project-governance/references/agent-dispatch-template.md) -> project\e2e-test-project\skills\software-project-governance\references\agent-dispatch-template.md
[OK] file exists: references/Agent Failure Modes (project/e2e-test-project/skills/software-project-governance/references/agent-failure-modes.md) -> project\e2e-test-project\skills\software-project-governance\references\agent-failure-modes.md
[OK] file exists: references/Behavior Protocol (project/e2e-test-project/skills/software-project-governance/references/behavior-protocol.md) -> project\e2e-test-project\skills\software-project-governance\references\behavior-protocol.md
[OK] file exists: references/Change Impact Checklist (project/e2e-test-project/skills/software-project-governance/references/change-impact-checklist.md) -> project\e2e-test-project\skills\software-project-governance\references\change-impact-checklist.md
[OK] file exists: references/Company Practices Summary (project/e2e-test-project/skills/software-project-governance/references/company-practices-summary.md) -> project\e2e-test-project\skills\software-project-governance\references\company-practices-summary.md
[OK] file exists: references/Interaction Boundary (project/e2e-test-project/skills/software-project-governance/references/interaction-boundary.md) -> project\e2e-test-project\skills\software-project-governance\references\interaction-boundary.md
[OK] file exists: references/Methodology Routing (project/e2e-test-project/skills/software-project-governance/references/methodology-routing.md) -> project\e2e-test-project\skills\software-project-governance\references\methodology-routing.md
[OK] file exists: references/Skill Index (project/e2e-test-project/skills/software-project-governance/references/skill-index.md) -> project\e2e-test-project\skills\software-project-governance\references\skill-index.md
[OK] file exists: references/Stage Skill Depth Rubric (project/e2e-test-project/skills/software-project-governance/references/stage-skill-depth-rubric.md) -> project\e2e-test-project\skills\software-project-governance\references\stage-skill-depth-rubric.md
[OK] file exists: Skill: software-project-governance (project/e2e-test-project/skills/software-project-governance/SKILL.md) -> project\e2e-test-project\skills\software-project-governance\SKILL.md
[OK] file exists: references/Agent Entry Differences -> project\references\agent-entry-differences.md
[OK] file exists: references/Agent Team Architecture -> project\references\agent-team-architecture.md
[OK] file exists: references/Architecture -> project\references\architecture.md
[OK] file exists: references/Asset Migration Map -> project\references\asset-migration-map.md
[OK] file exists: references/Data Boundary -> project\references\data-boundary.md
[OK] file exists: references/User Perspective Principle -> project\references\user-perspective-principle.md
[OK] file exists: examples/Current Project Decision Log -> project\workflows\software-project-governance\examples\current-project-decision-log.md
[OK] file exists: examples/Current Project Evidence Log -> project\workflows\software-project-governance\examples\current-project-evidence-log.md
[OK] file exists: examples/Current Project Risk Log -> project\workflows\software-project-governance\examples\current-project-risk-log.md
[OK] file exists: examples/Current Project Sample -> project\workflows\software-project-governance\examples\current-project-sample.md
[OK] file exists: research/Agent Integration Models -> project\workflows\software-project-governance\research\agent-integration-models.md
[OK] file exists: research/Company Practices -> project\workflows\software-project-governance\research\company-practices.md
[OK] file exists: research/Competitive Positioning And Official Marketplace Roadmap -> project\workflows\software-project-governance\research\competitive-positioning-and-official-marketplace-roadmap.md
[OK] file exists: research/Default Product Shape -> project\workflows\software-project-governance\research\default-product-shape.md
[OK] file exists: research/Domestic Agent Cli Compatibility -> project\workflows\software-project-governance\research\domestic-agent-cli-compatibility.md
[OK] file exists: research/External Capability Minimum Validation -> project\workflows\software-project-governance\research\external-capability-minimum-validation.md
[OK] file exists: research/External Validation Plan -> project\workflows\software-project-governance\research\external-validation-plan.md
[OK] file exists: research/Repo Local Termination Note -> project\workflows\software-project-governance\research\repo-local-termination-note.md
[OK] file exists: workflows/Governance Check -> project\.github\workflows\governance-check.yml
[OK] file exists: core/manifest.json -> project\e2e-test-project\skills\software-project-governance\core\manifest.json
[OK] file exists: workflows/Ci -> .github\workflows\ci.yml
[OK] file exists: Test Product Code -> tests\test_product_code.py
[OK] file exists: architecture/Adr 001 Systemic Gap Analysis -> docs\architecture\ADR-001-systemic-gap-analysis.md
[OK] file exists: architecture/Adr 002 Goal Alignment User Impact Enforcement -> docs\architecture\ADR-002-goal-alignment-user-impact-enforcement.md
[OK] file exists: architecture/Adr 003 Agent Team Protocol Enforcement -> docs\architecture\ADR-003-agent-team-protocol-enforcement.md
[OK] file exists: architecture/Adr 004 Coordinator Separation Architecture -> docs\architecture\ADR-004-coordinator-separation-architecture.md
[OK] file exists: architecture/Adr 005 Agent Concurrency Protection -> docs\architecture\ADR-005-agent-concurrency-protection.md
[OK] file exists: architecture/Adr 006 Governance Data Scalability -> docs\architecture\ADR-006-governance-data-scalability.md
[OK] file exists: architecture/Adr 007 Governance Upgrade Migration -> docs\architecture\ADR-007-governance-upgrade-migration.md
[OK] file exists: architecture/Adr 008 Llm Independent Product Success Guardrails -> docs\architecture\ADR-008-llm-independent-product-success-guardrails.md
[OK] file exists: architecture/Adr 009 Task Id Naming Convention -> docs\architecture\ADR-009-task-id-naming-convention.md
[OK] file exists: architecture/Adr 010 Declarative Release Manifests -> docs\architecture\ADR-010-declarative-release-manifests.md
[OK] file exists: architecture/Adr 011 Loop Runtime Claim Correction -> docs\architecture\ADR-011-loop-runtime-claim-correction.md
[OK] file exists: architecture/Adr 012 Loop Runtime Claim Recovery Split -> docs\architecture\ADR-012-loop-runtime-claim-recovery-split.md
[OK] file exists: architecture/Adr 013 Loop Runtime Contract 0.67.0 -> docs\architecture\ADR-013-loop-runtime-contract-0.67.0.md
[OK] file exists: architecture/Adr 014 Executable Loop Engine 0.68.0 -> docs\architecture\ADR-014-executable-loop-engine-0.68.0.md
[OK] file exists: architecture/Adr 015 Loop Telemetry 0.69.0 -> docs\architecture\ADR-015-loop-telemetry-0.69.0.md
[OK] file exists: architecture/Adr 016 Verify Phase5 Extraction 0.70.0 -> docs\architecture\ADR-016-verify-phase5-extraction-0.70.0.md
[OK] file exists: architecture/Adr 017 Loop Wiring And Task Planning 0.73.0 -> docs\architecture\ADR-017-loop-wiring-and-task-planning-0.73.0.md
[OK] file exists: architecture/Adr 018 Dsh Host Compatibility Contract -> docs\architecture\ADR-018-dsh-host-compatibility-contract.md
[OK] file exists: architecture/Adr 020 Injection Budget Dedup Slimming -> docs\architecture\ADR-020-injection-budget-dedup-slimming.md
[OK] file exists: architecture/Adr 021 Meta Mechanisms -> docs\architecture\ADR-021-meta-mechanisms.md
[OK] file exists: architecture/Adr Canonical Manifest Cleanup -> docs\architecture\adr-canonical-manifest-cleanup.md
[OK] file exists: architecture/Adr Loop Structure Switch 0.90.0 Consumers Appendix -> docs\architecture\adr-loop-structure-switch-0.90.0-consumers-appendix.md
[OK] file exists: architecture/Adr Loop Structure Switch 0.90.0 -> docs\architecture\adr-loop-structure-switch-0.90.0.md
[OK] file exists: architecture/Dsh Adapter Version Decoupling -> docs\architecture\dsh-adapter-version-decoupling.md
[OK] file exists: architecture/Evidence Layering Design Admission Inventory -> docs\architecture\evidence-layering-design-admission-inventory.md
[OK] file exists: architecture/Feat 074 Classification Diff 20260928 -> docs\architecture\feat-074-classification-diff-20260928.md
[OK] file exists: architecture/Feat 075 Four Family Dryrun 20260928 -> docs\architecture\feat-075-four-family-dryrun-20260928.md
[OK] file exists: architecture/Feat076 Consumer Matrix -> docs\architecture\feat076-consumer-matrix.md
[OK] file exists: architecture/Fix 203 Performance Recovery Audit 0.66.1 -> docs\architecture\fix-203-performance-recovery-audit-0.66.1.md
[OK] file exists: architecture/Rel063 Pre C Ancestry Investigation 0.66.2 -> docs\architecture\rel063-pre-c-ancestry-investigation-0.66.2.md
[OK] file exists: architecture/Release Incident Recovery 0.66.2 -> docs\architecture\release-incident-recovery-0.66.2.md
[OK] file exists: design/Fix 445 Archive Comparison R14 -> docs\design\FIX-445-archive-comparison-R14.md
[OK] file exists: design/Fix 445 Archive Protection R15 -> docs\design\FIX-445-archive-protection-R15.md
[OK] file exists: design/Fix 445 Mention Contract R10 -> docs\design\FIX-445-mention-contract-R10.md
[OK] file exists: design/Fix 445 Mention Interface R11 -> docs\design\FIX-445-mention-interface-R11.md
[OK] file exists: design/Fix 445 Mention Interface R12 -> docs\design\FIX-445-mention-interface-R12.md
[OK] file exists: design/Fix 445 Mention Interface R13 -> docs\design\FIX-445-mention-interface-R13.md
[OK] file exists: design/Fix 445 Source Verification R1 -> docs\design\FIX-445-source-verification-R1.md
[OK] file exists: design/Fix 445 Source Verification R2 -> docs\design\FIX-445-source-verification-R2.md
[OK] file exists: design/Fix 445 Source Verification R3 -> docs\design\FIX-445-source-verification-R3.md
[OK] file exists: design/Fix 445 Source Verification R4 -> docs\design\FIX-445-source-verification-R4.md
[OK] file exists: design/Fix 445 Source Verification R5 -> docs\design\FIX-445-source-verification-R5.md
[OK] file exists: design/Fix 445 Source Verification R7 -> docs\design\FIX-445-source-verification-R7.md
[OK] file exists: design/Fix 445 Source Verification R8 -> docs\design\FIX-445-source-verification-R8.md
[OK] file exists: design/Fix 445 Source Verification R9 -> docs\design\FIX-445-source-verification-R9.md
[OK] file exists: design/Fix 445 Source Verification -> docs\design\FIX-445-source-verification.md
[OK] file exists: diagnostics/Ci Clean Checkout Repair -> docs\diagnostics\ci-clean-checkout-repair.md
[OK] file exists: diagnostics/Ci Failure 0.99.0 -> docs\diagnostics\ci-failure-0.99.0.md
[OK] file exists: diagnostics/Dsh 0.2 Probe Resolution -> docs\diagnostics\dsh-0.2-probe-resolution.md
[OK] file exists: diagnostics/Feat 098 Cost Baseline -> docs\diagnostics\feat-098-cost-baseline.md
[OK] file exists: diagnostics/Fix 449 Version Pins -> docs\diagnostics\fix-449-version-pins.md
[OK] file exists: governance/Fix 402 Data Corrections Ledger 20260928 -> docs\governance\fix-402-data-corrections-ledger-20260928.md
[OK] file exists: governance/Rel 095 Exc002 Baseline 178 20260928 -> docs\governance\rel-095-exc002-baseline-178-20260928.md
[OK] file exists: knowledge/Single Session Continuous Execution Limitations -> docs\knowledge\single-session-continuous-execution-limitations.md
[OK] file exists: marketplace/Claude Code Submission 0.56.0 (docs/marketplace/claude-code-submission-0.56.0.md) -> docs\marketplace\claude-code-submission-0.56.0.md
[OK] file exists: marketplace/Comparison 0.46.0 (docs/marketplace/comparison-0.46.0.md) -> docs\marketplace\comparison-0.46.0.md
[OK] file exists: marketplace/Dsh Preset Adapter 0.73.0 -> docs\marketplace\dsh-preset-adapter-0.73.0.md
[OK] file exists: marketplace/Ecosystem Positioning 0.46.0 (docs/marketplace/ecosystem-positioning-0.46.0.md) -> docs\marketplace\ecosystem-positioning-0.46.0.md
[OK] file exists: marketplace/Examples 0.46.0 (docs/marketplace/examples-0.46.0.md) -> docs\marketplace\examples-0.46.0.md
[OK] file exists: marketplace/Marketplace Source Matrix 0.65.3 (docs/marketplace/marketplace-source-matrix-0.65.3.md) -> docs\marketplace\marketplace-source-matrix-0.65.3.md
[OK] file exists: marketplace/Migration Guide 0.46.0 (docs/marketplace/migration-guide-0.46.0.md) -> docs\marketplace\migration-guide-0.46.0.md
[OK] file exists: marketplace/Official Readiness Gap Analysis 0.41.0 -> docs\marketplace\official-readiness-gap-analysis-0.41.0.md
[OK] file exists: marketplace/Official Readiness Gap Analysis 0.56.0 (docs/marketplace/official-readiness-gap-analysis-0.56.0.md) -> docs\marketplace\official-readiness-gap-analysis-0.56.0.md
[OK] file exists: marketplace/Official Submission 0.46.0 (docs/marketplace/official-submission-0.46.0.md) -> docs\marketplace\official-submission-0.46.0.md
[OK] file exists: marketplace/Privacy Security -> docs\marketplace\privacy-security.md
[OK] file exists: marketplace/Submission Checklist 0.41.0 -> docs\marketplace\submission-checklist-0.41.0.md
[OK] file exists: marketplace/Zcode Local Load 0.56.0 (docs/marketplace/zcode-local-load-0.56.0.md) -> docs\marketplace\zcode-local-load-0.56.0.md
[OK] file exists: marketplace/Zcode Marketplace Install -> docs\marketplace\zcode-marketplace-install.md
[OK] file exists: migration/Dynamic Flow Gate Migration 0.55.0 (docs/migration/dynamic-flow-gate-migration-0.55.0.md) -> docs\migration\dynamic-flow-gate-migration-0.55.0.md
[OK] file exists: migration/Loop Engineering Runtime Contract Migration 0.66.1 -> docs\migration\loop-engineering-runtime-contract-migration-0.66.1.md
[OK] file exists: planning/0.85.0 2.0 Injection Measurement -> docs\planning\0.85.0-2.0-injection-measurement.md
[OK] file exists: planning/0.85.0 Candidate Analysis -> docs\planning\0.85.0-candidate-analysis.md
[OK] file exists: planning/0.86.0 Arch Consult Round1 -> docs\planning\0.86.0-arch-consult-round1.md
[OK] file exists: planning/0.86.0 Arch Consult Round2 External -> docs\planning\0.86.0-arch-consult-round2-external.md
[OK] file exists: planning/0.86.0 Arch Consult Round3 External -> docs\planning\0.86.0-arch-consult-round3-external.md
[OK] file exists: planning/0.86.0 Architecture Evolution -> docs\planning\0.86.0-architecture-evolution.md
[OK] file exists: planning/0.86.0 Boundary Audit -> docs\planning\0.86.0-boundary-audit.md
[OK] file exists: planning/Version Plan 0.86.0 -> docs\planning\version-plan-0.86.0.md
[OK] file exists: planning/Version Plan 0.87.0 -> docs\planning\version-plan-0.87.0.md
[OK] file exists: planning/Version Plan 0.88.0 -> docs\planning\version-plan-0.88.0.md
[OK] file exists: planning/Version Plan 0.89.0 -> docs\planning\version-plan-0.89.0.md
[OK] file exists: planning/Version Plan 0.90.0 -> docs\planning\version-plan-0.90.0.md
[OK] file exists: Reconciliation 0.93.1 -> docs\reconciliation-0.93.1.md
[OK] file exists: Reconciliation 0.94.0 -> docs\reconciliation-0.94.0.md
[OK] file exists: release/Audit 149 Health Noise 0.79.0 -> docs\release\audit-149-health-noise-0.79.0.md
[OK] file exists: release/Closeout Plan 0.99.0 -> docs\release\closeout-plan-0.99.0.md
[OK] file exists: release/Fault Injection 0.98.0 -> docs\release\fault-injection-0.98.0.md
[OK] file exists: release/Feature Flags 0.31.0 -> docs\release\feature-flags-0.31.0.md
[OK] file exists: release/Feature Flags 0.32.0 -> docs\release\feature-flags-0.32.0.md
[OK] file exists: release/Feature Flags 0.34.0 -> docs\release\feature-flags-0.34.0.md
[OK] file exists: release/Feature Flags 0.35.0 -> docs\release\feature-flags-0.35.0.md
[OK] file exists: release/Feature Flags 0.36.0 -> docs\release\feature-flags-0.36.0.md
[OK] file exists: release/Feature Flags 0.37.0 -> docs\release\feature-flags-0.37.0.md
[OK] file exists: release/Feature Flags 0.38.0 -> docs\release\feature-flags-0.38.0.md
[OK] file exists: release/Feature Flags 0.39.0 -> docs\release\feature-flags-0.39.0.md
[OK] file exists: release/Feature Flags 0.40.0 -> docs\release\feature-flags-0.40.0.md
[OK] file exists: release/Feature Flags 0.40.1 -> docs\release\feature-flags-0.40.1.md
[OK] file exists: release/Feature Flags 0.41.0 -> docs\release\feature-flags-0.41.0.md
[OK] file exists: release/Feature Flags 0.42.0 -> docs\release\feature-flags-0.42.0.md
[OK] file exists: release/Feature Flags 0.43.0 -> docs\release\feature-flags-0.43.0.md
[OK] file exists: release/Feature Flags 0.44.0 -> docs\release\feature-flags-0.44.0.md
[OK] file exists: release/Feature Flags 0.44.1 -> docs\release\feature-flags-0.44.1.md
[OK] file exists: release/Feature Flags 0.45.0 (docs/release/feature-flags-0.45.0.md) -> docs\release\feature-flags-0.45.0.md
[OK] file exists: release/Feature Flags 0.46.0 (docs/release/feature-flags-0.46.0.md) -> docs\release\feature-flags-0.46.0.md
[OK] file exists: release/Feature Flags 0.47.0 (docs/release/feature-flags-0.47.0.md) -> docs\release\feature-flags-0.47.0.md
[OK] file exists: release/Feature Flags 0.48.0 (docs/release/feature-flags-0.48.0.md) -> docs\release\feature-flags-0.48.0.md
[OK] file exists: release/Feature Flags 0.49.0 (docs/release/feature-flags-0.49.0.md) -> docs\release\feature-flags-0.49.0.md
[OK] file exists: release/Feature Flags 0.50.0 (docs/release/feature-flags-0.50.0.md) -> docs\release\feature-flags-0.50.0.md
[OK] file exists: release/Feature Flags 0.50.1 -> docs\release\feature-flags-0.50.1.md
[OK] file exists: release/Feature Flags 0.50.2 (docs/release/feature-flags-0.50.2.md) -> docs\release\feature-flags-0.50.2.md
[OK] file exists: release/Feature Flags 0.50.3 (docs/release/feature-flags-0.50.3.md) -> docs\release\feature-flags-0.50.3.md
[OK] file exists: release/Feature Flags 0.51.0 (docs/release/feature-flags-0.51.0.md) -> docs\release\feature-flags-0.51.0.md
[OK] file exists: release/Feature Flags 0.52.0 (docs/release/feature-flags-0.52.0.md) -> docs\release\feature-flags-0.52.0.md
[OK] file exists: release/Feature Flags 0.53.0 (docs/release/feature-flags-0.53.0.md) -> docs\release\feature-flags-0.53.0.md
[OK] file exists: release/Feature Flags 0.54.0 (docs/release/feature-flags-0.54.0.md) -> docs\release\feature-flags-0.54.0.md
[OK] file exists: release/Feature Flags 0.54.1 (docs/release/feature-flags-0.54.1.md) -> docs\release\feature-flags-0.54.1.md
[OK] file exists: release/Feature Flags 0.55.0 (docs/release/feature-flags-0.55.0.md) -> docs\release\feature-flags-0.55.0.md
[OK] file exists: release/Feature Flags 0.55.1 (docs/release/feature-flags-0.55.1.md) -> docs\release\feature-flags-0.55.1.md
[OK] file exists: release/Feature Flags 0.55.2 (docs/release/feature-flags-0.55.2.md) -> docs\release\feature-flags-0.55.2.md
[OK] file exists: release/Feature Flags 0.55.3 (docs/release/feature-flags-0.55.3.md) -> docs\release\feature-flags-0.55.3.md
[OK] file exists: release/Feature Flags 0.56.0 (docs/release/feature-flags-0.56.0.md) -> docs\release\feature-flags-0.56.0.md
[OK] file exists: release/Feature Flags 0.56.1 (docs/release/feature-flags-0.56.1.md) -> docs\release\feature-flags-0.56.1.md
[OK] file exists: release/Feature Flags 0.57.0 (docs/release/feature-flags-0.57.0.md) -> docs\release\feature-flags-0.57.0.md
[OK] file exists: release/Feature Flags 0.58.0 (docs/release/feature-flags-0.58.0.md) -> docs\release\feature-flags-0.58.0.md
[OK] file exists: release/Feature Flags 0.59.0 (docs/release/feature-flags-0.59.0.md) -> docs\release\feature-flags-0.59.0.md
[OK] file exists: release/Feature Flags 0.60.0 -> docs\release\feature-flags-0.60.0.md
[OK] file exists: release/Feature Flags 0.61.0 -> docs\release\feature-flags-0.61.0.md
[OK] file exists: release/Feature Flags 0.61.1 (docs/release/feature-flags-0.61.1.md) -> docs\release\feature-flags-0.61.1.md
[OK] file exists: release/Feature Flags 0.61.2 (docs/release/feature-flags-0.61.2.md) -> docs\release\feature-flags-0.61.2.md
[OK] file exists: release/Feature Flags 0.62.0 -> docs\release\feature-flags-0.62.0.md
[OK] file exists: release/Feature Flags 0.63.0 -> docs\release\feature-flags-0.63.0.md
[OK] file exists: release/Feature Flags 0.63.1 -> docs\release\feature-flags-0.63.1.md
[OK] file exists: release/Feature Flags 0.63.2 -> docs\release\feature-flags-0.63.2.md
[OK] file exists: release/Feature Flags 0.63.3 -> docs\release\feature-flags-0.63.3.md
[OK] file exists: release/Feature Flags 0.63.4 -> docs\release\feature-flags-0.63.4.md
[OK] file exists: release/Feature Flags 0.64.0 -> docs\release\feature-flags-0.64.0.md
[OK] file exists: release/Feature Flags 0.64.1 -> docs\release\feature-flags-0.64.1.md
[OK] file exists: release/Feature Flags 0.65.0 -> docs\release\feature-flags-0.65.0.md
[OK] file exists: release/Feature Flags 0.65.1 -> docs\release\feature-flags-0.65.1.md
[OK] file exists: release/Feature Flags 0.65.2 -> docs\release\feature-flags-0.65.2.md
[OK] file exists: release/Feature Flags 0.65.3 -> docs\release\feature-flags-0.65.3.md
[OK] file exists: release/Feature Flags 0.66.0 -> docs\release\feature-flags-0.66.0.md
[OK] file exists: release/Feature Flags 0.66.2 -> docs\release\feature-flags-0.66.2.md
[OK] file exists: release/Feature Flags 0.66.3 -> docs\release\feature-flags-0.66.3.md
[OK] file exists: release/Feature Flags 0.67.0 -> docs\release\feature-flags-0.67.0.md
[OK] file exists: release/Feature Flags 0.68.0 -> docs\release\feature-flags-0.68.0.md
[OK] file exists: release/Feature Flags 0.69.0 -> docs\release\feature-flags-0.69.0.md
[OK] file exists: release/Feature Flags 0.70.0 -> docs\release\feature-flags-0.70.0.md
[OK] file exists: release/Feature Flags 0.71.0 -> docs\release\feature-flags-0.71.0.md
[OK] file exists: release/Feature Flags 0.72.0 -> docs\release\feature-flags-0.72.0.md
[OK] file exists: release/Feature Flags 0.73.0 -> docs\release\feature-flags-0.73.0.md
[OK] file exists: release/Feature Flags 0.74.0 -> docs\release\feature-flags-0.74.0.md
[OK] file exists: release/Feature Flags 0.75.0 -> docs\release\feature-flags-0.75.0.md
[OK] file exists: release/Feature Flags 0.76.0 -> docs\release\feature-flags-0.76.0.md
[OK] file exists: release/Feature Flags 0.77.0 -> docs\release\feature-flags-0.77.0.md
[OK] file exists: release/Feature Flags 0.78.0 -> docs\release\feature-flags-0.78.0.md
[OK] file exists: release/Feature Flags 0.78.1 -> docs\release\feature-flags-0.78.1.md
[OK] file exists: release/Feature Flags 0.79.0 -> docs\release\feature-flags-0.79.0.md
[OK] file exists: release/Feature Flags 0.80.0 -> docs\release\feature-flags-0.80.0.md
[OK] file exists: release/Feature Flags 0.81.0 -> docs\release\feature-flags-0.81.0.md
[OK] file exists: release/Feature Flags 0.82.0 -> docs\release\feature-flags-0.82.0.md
[OK] file exists: release/Feature Flags 0.83.0 -> docs\release\feature-flags-0.83.0.md
[OK] file exists: release/Feature Flags 0.84.0 -> docs\release\feature-flags-0.84.0.md
[OK] file exists: release/Feature Flags 0.85.0 -> docs\release\feature-flags-0.85.0.md
[OK] file exists: release/Feature Flags 0.86.0 -> docs\release\feature-flags-0.86.0.md
[OK] file exists: release/Feature Flags 0.87.0 -> docs\release\feature-flags-0.87.0.md
[OK] file exists: release/Feature Flags 0.88.0 -> docs\release\feature-flags-0.88.0.md
[OK] file exists: release/Feature Flags 0.89.0 -> docs\release\feature-flags-0.89.0.md
[OK] file exists: release/Feature Flags 0.90.0 -> docs\release\feature-flags-0.90.0.md
[OK] file exists: release/Feature Flags 0.91.0 -> docs\release\feature-flags-0.91.0.md
[OK] file exists: release/Feature Flags 0.92.0 -> docs\release\feature-flags-0.92.0.md
[OK] file exists: release/Feature Flags 0.93.0 -> docs\release\feature-flags-0.93.0.md
[OK] file exists: release/Feature Flags 0.93.1 -> docs\release\feature-flags-0.93.1.md
[OK] file exists: release/Feature Flags 0.94.0 -> docs\release\feature-flags-0.94.0.md
[OK] file exists: release/Feature Flags 0.95.0 -> docs\release\feature-flags-0.95.0.md
[OK] file exists: release/Feature Flags 0.96.0 -> docs\release\feature-flags-0.96.0.md
[OK] file exists: release/Feature Flags 0.97.0 -> docs\release\feature-flags-0.97.0.md
[OK] file exists: release/Feature Flags 0.98.0 -> docs\release\feature-flags-0.98.0.md
[OK] file exists: release/M 0 Assembly 0.95.0 -> docs\release\m-0-assembly-0.95.0.md
[OK] file exists: release/M 0 Assembly 0.96.0 -> docs\release\m-0-assembly-0.96.0.md
[OK] file exists: release/M 0 Assembly 0.97.0 -> docs\release\m-0-assembly-0.97.0.md
[OK] file exists: release/M 0 Assembly 0.98.0 -> docs\release\m-0-assembly-0.98.0.md
[OK] file exists: release/Queue Reconciliation 0.79.0 -> docs\release\queue-reconciliation-0.79.0.md
[OK] file exists: release/Queue Triage 0.78X -> docs\release\queue-triage-0.78x.md
[OK] file exists: release/Real Machine Acceptance 0.81.0 -> docs\release\real-machine-acceptance-0.81.0.md
[OK] file exists: release/Rel 089 M3 Precondition Report -> docs\release\rel-089-m3-precondition-report.md
[OK] file exists: release/Release Checklist 0.31.0 -> docs\release\release-checklist-0.31.0.md
[OK] file exists: release/Release Checklist 0.32.0 -> docs\release\release-checklist-0.32.0.md
[OK] file exists: release/Release Checklist 0.34.0 -> docs\release\release-checklist-0.34.0.md
[OK] file exists: release/Release Checklist 0.35.0 -> docs\release\release-checklist-0.35.0.md
[OK] file exists: release/Release Checklist 0.36.0 -> docs\release\release-checklist-0.36.0.md
[OK] file exists: release/Release Checklist 0.37.0 -> docs\release\release-checklist-0.37.0.md
[OK] file exists: release/Release Checklist 0.38.0 -> docs\release\release-checklist-0.38.0.md
[OK] file exists: release/Release Checklist 0.39.0 -> docs\release\release-checklist-0.39.0.md
[OK] file exists: release/Release Checklist 0.40.0 -> docs\release\release-checklist-0.40.0.md
[OK] file exists: release/Release Checklist 0.40.1 -> docs\release\release-checklist-0.40.1.md
[OK] file exists: release/Release Checklist 0.41.0 -> docs\release\release-checklist-0.41.0.md
[OK] file exists: release/Release Checklist 0.42.0 -> docs\release\release-checklist-0.42.0.md
[OK] file exists: release/Release Checklist 0.43.0 -> docs\release\release-checklist-0.43.0.md
[OK] file exists: release/Release Checklist 0.44.0 -> docs\release\release-checklist-0.44.0.md
[OK] file exists: release/Release Checklist 0.44.1 -> docs\release\release-checklist-0.44.1.md
[OK] file exists: release/Release Checklist 0.45.0 (docs/release/release-checklist-0.45.0.md) -> docs\release\release-checklist-0.45.0.md
[OK] file exists: release/Release Checklist 0.46.0 (docs/release/release-checklist-0.46.0.md) -> docs\release\release-checklist-0.46.0.md
[OK] file exists: release/Release Checklist 0.47.0 (docs/release/release-checklist-0.47.0.md) -> docs\release\release-checklist-0.47.0.md
[OK] file exists: release/Release Checklist 0.48.0 (docs/release/release-checklist-0.48.0.md) -> docs\release\release-checklist-0.48.0.md
[OK] file exists: release/Release Checklist 0.49.0 (docs/release/release-checklist-0.49.0.md) -> docs\release\release-checklist-0.49.0.md
[OK] file exists: release/Release Checklist 0.50.0 (docs/release/release-checklist-0.50.0.md) -> docs\release\release-checklist-0.50.0.md
[OK] file exists: release/Release Checklist 0.50.1 -> docs\release\release-checklist-0.50.1.md
[OK] file exists: release/Release Checklist 0.50.2 (docs/release/release-checklist-0.50.2.md) -> docs\release\release-checklist-0.50.2.md
[OK] file exists: release/Release Checklist 0.50.3 (docs/release/release-checklist-0.50.3.md) -> docs\release\release-checklist-0.50.3.md
[OK] file exists: release/Release Checklist 0.51.0 (docs/release/release-checklist-0.51.0.md) -> docs\release\release-checklist-0.51.0.md
[OK] file exists: release/Release Checklist 0.52.0 (docs/release/release-checklist-0.52.0.md) -> docs\release\release-checklist-0.52.0.md
[OK] file exists: release/Release Checklist 0.53.0 (docs/release/release-checklist-0.53.0.md) -> docs\release\release-checklist-0.53.0.md
[OK] file exists: release/Release Checklist 0.54.0 (docs/release/release-checklist-0.54.0.md) -> docs\release\release-checklist-0.54.0.md
[OK] file exists: release/Release Checklist 0.54.1 (docs/release/release-checklist-0.54.1.md) -> docs\release\release-checklist-0.54.1.md
[OK] file exists: release/Release Checklist 0.55.0 (docs/release/release-checklist-0.55.0.md) -> docs\release\release-checklist-0.55.0.md
[OK] file exists: release/Release Checklist 0.55.1 (docs/release/release-checklist-0.55.1.md) -> docs\release\release-checklist-0.55.1.md
[OK] file exists: release/Release Checklist 0.55.2 (docs/release/release-checklist-0.55.2.md) -> docs\release\release-checklist-0.55.2.md
[OK] file exists: release/Release Checklist 0.55.3 (docs/release/release-checklist-0.55.3.md) -> docs\release\release-checklist-0.55.3.md
[OK] file exists: release/Release Checklist 0.56.0 (docs/release/release-checklist-0.56.0.md) -> docs\release\release-checklist-0.56.0.md
[OK] file exists: release/Release Checklist 0.56.1 (docs/release/release-checklist-0.56.1.md) -> docs\release\release-checklist-0.56.1.md
[OK] file exists: release/Release Checklist 0.57.0 (docs/release/release-checklist-0.57.0.md) -> docs\release\release-checklist-0.57.0.md
[OK] file exists: release/Release Checklist 0.58.0 (docs/release/release-checklist-0.58.0.md) -> docs\release\release-checklist-0.58.0.md
[OK] file exists: release/Release Checklist 0.59.0 (docs/release/release-checklist-0.59.0.md) -> docs\release\release-checklist-0.59.0.md
[OK] file exists: release/Release Checklist 0.60.0 -> docs\release\release-checklist-0.60.0.md
[OK] file exists: release/Release Checklist 0.61.0 -> docs\release\release-checklist-0.61.0.md
[OK] file exists: release/Release Checklist 0.61.1 (docs/release/release-checklist-0.61.1.md) -> docs\release\release-checklist-0.61.1.md
[OK] file exists: release/Release Checklist 0.61.2 (docs/release/release-checklist-0.61.2.md) -> docs\release\release-checklist-0.61.2.md
[OK] file exists: release/Release Checklist 0.62.0 -> docs\release\release-checklist-0.62.0.md
[OK] file exists: release/Release Checklist 0.63.0 -> docs\release\release-checklist-0.63.0.md
[OK] file exists: release/Release Checklist 0.63.1 -> docs\release\release-checklist-0.63.1.md
[OK] file exists: release/Release Checklist 0.63.2 -> docs\release\release-checklist-0.63.2.md
[OK] file exists: release/Release Checklist 0.63.3 -> docs\release\release-checklist-0.63.3.md
[OK] file exists: release/Release Checklist 0.63.4 -> docs\release\release-checklist-0.63.4.md
[OK] file exists: release/Release Checklist 0.64.0 -> docs\release\release-checklist-0.64.0.md
[OK] file exists: release/Release Checklist 0.64.1 -> docs\release\release-checklist-0.64.1.md
[OK] file exists: release/Release Checklist 0.65.0 -> docs\release\release-checklist-0.65.0.md
[OK] file exists: release/Release Checklist 0.65.1 -> docs\release\release-checklist-0.65.1.md
[OK] file exists: release/Release Checklist 0.65.2 -> docs\release\release-checklist-0.65.2.md
[OK] file exists: release/Release Checklist 0.65.3 -> docs\release\release-checklist-0.65.3.md
[OK] file exists: release/Release Checklist 0.66.0 -> docs\release\release-checklist-0.66.0.md
[OK] file exists: release/Release Checklist 0.66.2 -> docs\release\release-checklist-0.66.2.md
[OK] file exists: release/Release Checklist 0.66.3 -> docs\release\release-checklist-0.66.3.md
[OK] file exists: release/Release Checklist 0.67.0 -> docs\release\release-checklist-0.67.0.md
[OK] file exists: release/Release Checklist 0.68.0 -> docs\release\release-checklist-0.68.0.md
[OK] file exists: release/Release Checklist 0.69.0 -> docs\release\release-checklist-0.69.0.md
[OK] file exists: release/Release Checklist 0.70.0 -> docs\release\release-checklist-0.70.0.md
[OK] file exists: release/Release Checklist 0.71.0 -> docs\release\release-checklist-0.71.0.md
[OK] file exists: release/Release Checklist 0.72.0 -> docs\release\release-checklist-0.72.0.md
[OK] file exists: release/Release Checklist 0.73.0 -> docs\release\release-checklist-0.73.0.md
[OK] file exists: release/Release Checklist 0.74.0 -> docs\release\release-checklist-0.74.0.md
[OK] file exists: release/Release Checklist 0.75.0 -> docs\release\release-checklist-0.75.0.md
[OK] file exists: release/Release Checklist 0.76.0 -> docs\release\release-checklist-0.76.0.md
[OK] file exists: release/Release Checklist 0.77.0 -> docs\release\release-checklist-0.77.0.md
[OK] file exists: release/Release Checklist 0.78.0 -> docs\release\release-checklist-0.78.0.md
[OK] file exists: release/Release Checklist 0.78.1 -> docs\release\release-checklist-0.78.1.md
[OK] file exists: release/Release Checklist 0.79.0 -> docs\release\release-checklist-0.79.0.md
[OK] file exists: release/Release Checklist 0.80.0 -> docs\release\release-checklist-0.80.0.md
[OK] file exists: release/Release Checklist 0.81.0 -> docs\release\release-checklist-0.81.0.md
[OK] file exists: release/Release Checklist 0.82.0 -> docs\release\release-checklist-0.82.0.md
[OK] file exists: release/Release Checklist 0.83.0 -> docs\release\release-checklist-0.83.0.md
[OK] file exists: release/Release Checklist 0.84.0 -> docs\release\release-checklist-0.84.0.md
[OK] file exists: release/Release Checklist 0.85.0 -> docs\release\release-checklist-0.85.0.md
[OK] file exists: release/Release Checklist 0.86.0 -> docs\release\release-checklist-0.86.0.md
[OK] file exists: release/Release Checklist 0.87.0 -> docs\release\release-checklist-0.87.0.md
[OK] file exists: release/Release Checklist 0.88.0 -> docs\release\release-checklist-0.88.0.md
[OK] file exists: release/Release Checklist 0.89.0 -> docs\release\release-checklist-0.89.0.md
[OK] file exists: release/Release Checklist 0.90.0 -> docs\release\release-checklist-0.90.0.md
[OK] file exists: release/Release Checklist 0.91.0 -> docs\release\release-checklist-0.91.0.md
[OK] file exists: release/Release Checklist 0.92.0 -> docs\release\release-checklist-0.92.0.md
[OK] file exists: release/Release Checklist 0.93.0 -> docs\release\release-checklist-0.93.0.md
[OK] file exists: release/Release Checklist 0.93.1 -> docs\release\release-checklist-0.93.1.md
[OK] file exists: release/Release Checklist 0.94.0 -> docs\release\release-checklist-0.94.0.md
[OK] file exists: release/Release Checklist 0.95.0 -> docs\release\release-checklist-0.95.0.md
[OK] file exists: release/Release Checklist 0.96.0 -> docs\release\release-checklist-0.96.0.md
[OK] file exists: release/Release Checklist 0.97.0 -> docs\release\release-checklist-0.97.0.md
[OK] file exists: release/Release Checklist 0.98.0 -> docs\release\release-checklist-0.98.0.md
[OK] file exists: release/Release Lineage Audit 0.65.3 (docs/release/release-lineage-audit-0.65.3.md) -> docs\release\release-lineage-audit-0.65.3.md
[OK] file exists: release/Release Plan 0.85.0 -> docs\release\release-plan-0.85.0.md
[OK] file exists: release/Release Plan 0.86.0 -> docs\release\release-plan-0.86.0.md
[OK] file exists: release/Release Plan 0.87.0 -> docs\release\release-plan-0.87.0.md
[OK] file exists: release/Release Plan 0.88.0 -> docs\release\release-plan-0.88.0.md
[OK] file exists: release/Release Plan 0.89.0 -> docs\release\release-plan-0.89.0.md
[OK] file exists: release/Release Plan 0.91.0 -> docs\release\release-plan-0.91.0.md
[OK] file exists: release/Release Plan 0.92.0 -> docs\release\release-plan-0.92.0.md
[OK] file exists: release/Rollback Plan 0.31.0 -> docs\release\rollback-plan-0.31.0.md
[OK] file exists: release/Rollback Plan 0.32.0 -> docs\release\rollback-plan-0.32.0.md
[OK] file exists: release/Rollback Plan 0.34.0 -> docs\release\rollback-plan-0.34.0.md
[OK] file exists: release/Rollback Plan 0.35.0 -> docs\release\rollback-plan-0.35.0.md
[OK] file exists: release/Rollback Plan 0.36.0 -> docs\release\rollback-plan-0.36.0.md
[OK] file exists: release/Rollback Plan 0.37.0 -> docs\release\rollback-plan-0.37.0.md
[OK] file exists: release/Rollback Plan 0.38.0 -> docs\release\rollback-plan-0.38.0.md
[OK] file exists: release/Rollback Plan 0.39.0 -> docs\release\rollback-plan-0.39.0.md
[OK] file exists: release/Rollback Plan 0.40.0 -> docs\release\rollback-plan-0.40.0.md
[OK] file exists: release/Rollback Plan 0.40.1 -> docs\release\rollback-plan-0.40.1.md
[OK] file exists: release/Rollback Plan 0.41.0 -> docs\release\rollback-plan-0.41.0.md
[OK] file exists: release/Rollback Plan 0.42.0 -> docs\release\rollback-plan-0.42.0.md
[OK] file exists: release/Rollback Plan 0.43.0 -> docs\release\rollback-plan-0.43.0.md
[OK] file exists: release/Rollback Plan 0.44.0 -> docs\release\rollback-plan-0.44.0.md
[OK] file exists: release/Rollback Plan 0.44.1 -> docs\release\rollback-plan-0.44.1.md
[OK] file exists: release/Rollback Plan 0.45.0 (docs/release/rollback-plan-0.45.0.md) -> docs\release\rollback-plan-0.45.0.md
[OK] file exists: release/Rollback Plan 0.46.0 (docs/release/rollback-plan-0.46.0.md) -> docs\release\rollback-plan-0.46.0.md
[OK] file exists: release/Rollback Plan 0.47.0 (docs/release/rollback-plan-0.47.0.md) -> docs\release\rollback-plan-0.47.0.md
[OK] file exists: release/Rollback Plan 0.48.0 (docs/release/rollback-plan-0.48.0.md) -> docs\release\rollback-plan-0.48.0.md
[OK] file exists: release/Rollback Plan 0.49.0 (docs/release/rollback-plan-0.49.0.md) -> docs\release\rollback-plan-0.49.0.md
[OK] file exists: release/Rollback Plan 0.50.0 (docs/release/rollback-plan-0.50.0.md) -> docs\release\rollback-plan-0.50.0.md
[OK] file exists: release/Rollback Plan 0.50.1 -> docs\release\rollback-plan-0.50.1.md
[OK] file exists: release/Rollback Plan 0.50.2 (docs/release/rollback-plan-0.50.2.md) -> docs\release\rollback-plan-0.50.2.md
[OK] file exists: release/Rollback Plan 0.50.3 (docs/release/rollback-plan-0.50.3.md) -> docs\release\rollback-plan-0.50.3.md
[OK] file exists: release/Rollback Plan 0.51.0 (docs/release/rollback-plan-0.51.0.md) -> docs\release\rollback-plan-0.51.0.md
[OK] file exists: release/Rollback Plan 0.52.0 (docs/release/rollback-plan-0.52.0.md) -> docs\release\rollback-plan-0.52.0.md
[OK] file exists: release/Rollback Plan 0.53.0 (docs/release/rollback-plan-0.53.0.md) -> docs\release\rollback-plan-0.53.0.md
[OK] file exists: release/Rollback Plan 0.54.0 (docs/release/rollback-plan-0.54.0.md) -> docs\release\rollback-plan-0.54.0.md
[OK] file exists: release/Rollback Plan 0.54.1 (docs/release/rollback-plan-0.54.1.md) -> docs\release\rollback-plan-0.54.1.md
[OK] file exists: release/Rollback Plan 0.55.0 (docs/release/rollback-plan-0.55.0.md) -> docs\release\rollback-plan-0.55.0.md
[OK] file exists: release/Rollback Plan 0.55.1 (docs/release/rollback-plan-0.55.1.md) -> docs\release\rollback-plan-0.55.1.md
[OK] file exists: release/Rollback Plan 0.55.2 (docs/release/rollback-plan-0.55.2.md) -> docs\release\rollback-plan-0.55.2.md
[OK] file exists: release/Rollback Plan 0.55.3 (docs/release/rollback-plan-0.55.3.md) -> docs\release\rollback-plan-0.55.3.md
[OK] file exists: release/Rollback Plan 0.56.0 (docs/release/rollback-plan-0.56.0.md) -> docs\release\rollback-plan-0.56.0.md
[OK] file exists: release/Rollback Plan 0.56.1 (docs/release/rollback-plan-0.56.1.md) -> docs\release\rollback-plan-0.56.1.md
[OK] file exists: release/Rollback Plan 0.57.0 (docs/release/rollback-plan-0.57.0.md) -> docs\release\rollback-plan-0.57.0.md
[OK] file exists: release/Rollback Plan 0.58.0 (docs/release/rollback-plan-0.58.0.md) -> docs\release\rollback-plan-0.58.0.md
[OK] file exists: release/Rollback Plan 0.59.0 (docs/release/rollback-plan-0.59.0.md) -> docs\release\rollback-plan-0.59.0.md
[OK] file exists: release/Rollback Plan 0.60.0 -> docs\release\rollback-plan-0.60.0.md
[OK] file exists: release/Rollback Plan 0.61.0 -> docs\release\rollback-plan-0.61.0.md
[OK] file exists: release/Rollback Plan 0.61.1 (docs/release/rollback-plan-0.61.1.md) -> docs\release\rollback-plan-0.61.1.md
[OK] file exists: release/Rollback Plan 0.61.2 (docs/release/rollback-plan-0.61.2.md) -> docs\release\rollback-plan-0.61.2.md
[OK] file exists: release/Rollback Plan 0.62.0 -> docs\release\rollback-plan-0.62.0.md
[OK] file exists: release/Rollback Plan 0.63.0 -> docs\release\rollback-plan-0.63.0.md
[OK] file exists: release/Rollback Plan 0.63.1 -> docs\release\rollback-plan-0.63.1.md
[OK] file exists: release/Rollback Plan 0.63.2 -> docs\release\rollback-plan-0.63.2.md
[OK] file exists: release/Rollback Plan 0.63.3 -> docs\release\rollback-plan-0.63.3.md
[OK] file exists: release/Rollback Plan 0.63.4 -> docs\release\rollback-plan-0.63.4.md
[OK] file exists: release/Rollback Plan 0.64.0 -> docs\release\rollback-plan-0.64.0.md
[OK] file exists: release/Rollback Plan 0.64.1 -> docs\release\rollback-plan-0.64.1.md
[OK] file exists: release/Rollback Plan 0.65.0 -> docs\release\rollback-plan-0.65.0.md
[OK] file exists: release/Rollback Plan 0.65.1 -> docs\release\rollback-plan-0.65.1.md
[OK] file exists: release/Rollback Plan 0.65.2 -> docs\release\rollback-plan-0.65.2.md
[OK] file exists: release/Rollback Plan 0.65.3 -> docs\release\rollback-plan-0.65.3.md
[OK] file exists: release/Rollback Plan 0.66.0 -> docs\release\rollback-plan-0.66.0.md
[OK] file exists: release/Rollback Plan 0.66.2 -> docs\release\rollback-plan-0.66.2.md
[OK] file exists: release/Rollback Plan 0.66.3 -> docs\release\rollback-plan-0.66.3.md
[OK] file exists: release/Rollback Plan 0.67.0 -> docs\release\rollback-plan-0.67.0.md
[OK] file exists: release/Rollback Plan 0.68.0 -> docs\release\rollback-plan-0.68.0.md
[OK] file exists: release/Rollback Plan 0.69.0 -> docs\release\rollback-plan-0.69.0.md
[OK] file exists: release/Rollback Plan 0.70.0 -> docs\release\rollback-plan-0.70.0.md
[OK] file exists: release/Rollback Plan 0.71.0 -> docs\release\rollback-plan-0.71.0.md
[OK] file exists: release/Rollback Plan 0.72.0 -> docs\release\rollback-plan-0.72.0.md
[OK] file exists: release/Rollback Plan 0.73.0 -> docs\release\rollback-plan-0.73.0.md
[OK] file exists: release/Rollback Plan 0.74.0 -> docs\release\rollback-plan-0.74.0.md
[OK] file exists: release/Rollback Plan 0.75.0 -> docs\release\rollback-plan-0.75.0.md
[OK] file exists: release/Rollback Plan 0.76.0 -> docs\release\rollback-plan-0.76.0.md
[OK] file exists: release/Rollback Plan 0.77.0 -> docs\release\rollback-plan-0.77.0.md
[OK] file exists: release/Rollback Plan 0.78.0 -> docs\release\rollback-plan-0.78.0.md
[OK] file exists: release/Rollback Plan 0.78.1 -> docs\release\rollback-plan-0.78.1.md
[OK] file exists: release/Rollback Plan 0.79.0 -> docs\release\rollback-plan-0.79.0.md
[OK] file exists: release/Rollback Plan 0.80.0 -> docs\release\rollback-plan-0.80.0.md
[OK] file exists: release/Rollback Plan 0.81.0 -> docs\release\rollback-plan-0.81.0.md
[OK] file exists: release/Rollback Plan 0.82.0 -> docs\release\rollback-plan-0.82.0.md
[OK] file exists: release/Rollback Plan 0.83.0 -> docs\release\rollback-plan-0.83.0.md
[OK] file exists: release/Rollback Plan 0.84.0 -> docs\release\rollback-plan-0.84.0.md
[OK] file exists: release/Rollback Plan 0.85.0 -> docs\release\rollback-plan-0.85.0.md
[OK] file exists: release/Rollback Plan 0.86.0 -> docs\release\rollback-plan-0.86.0.md
[OK] file exists: release/Rollback Plan 0.87.0 -> docs\release\rollback-plan-0.87.0.md
[OK] file exists: release/Rollback Plan 0.88.0 -> docs\release\rollback-plan-0.88.0.md
[OK] file exists: release/Rollback Plan 0.89.0 -> docs\release\rollback-plan-0.89.0.md
[OK] file exists: release/Rollback Plan 0.90.0 -> docs\release\rollback-plan-0.90.0.md
[OK] file exists: release/Rollback Plan 0.91.0 -> docs\release\rollback-plan-0.91.0.md
[OK] file exists: release/Rollback Plan 0.92.0 -> docs\release\rollback-plan-0.92.0.md
[OK] file exists: release/Rollback Plan 0.93.0 -> docs\release\rollback-plan-0.93.0.md
[OK] file exists: release/Rollback Plan 0.93.1 -> docs\release\rollback-plan-0.93.1.md
[OK] file exists: release/Rollback Plan 0.94.0 -> docs\release\rollback-plan-0.94.0.md
[OK] file exists: release/Rollback Plan 0.95.0 -> docs\release\rollback-plan-0.95.0.md
[OK] file exists: release/Rollback Plan 0.96.0 -> docs\release\rollback-plan-0.96.0.md
[OK] file exists: release/Rollback Plan 0.97.0 -> docs\release\rollback-plan-0.97.0.md
[OK] file exists: release/Rollback Plan 0.98.0 -> docs\release\rollback-plan-0.98.0.md
[OK] file exists: release/Version Plan 0.77.0 -> docs\release\version-plan-0.77.0.md
[OK] file exists: release/Version Plan 0.78.0 -> docs\release\version-plan-0.78.0.md
[OK] file exists: release/Version Plan 0.78.1 -> docs\release\version-plan-0.78.1.md
[OK] file exists: release/Version Plan 0.79.0 -> docs\release\version-plan-0.79.0.md
[OK] file exists: release/Version Plan 0.81.0 -> docs\release\version-plan-0.81.0.md
[OK] file exists: release/Version Plan 0.85.0 -> docs\release\version-plan-0.85.0.md
[OK] file exists: requirements/Agent Team Bypass Root Cause Analysis 2026 05 02 -> docs\requirements\agent-team-bypass-root-cause-analysis-2026-05-02.md
[OK] file exists: requirements/Analysis Governance Overhead Session F3F46901 0.96.0 -> docs\requirements\analysis-governance-overhead-session-f3f46901-0.96.0.md
[OK] file exists: requirements/Analysis Rpg Longhaul Capability Session F3F46901 0.97.0 -> docs\requirements\analysis-rpg-longhaul-capability-session-f3f46901-0.97.0.md
[OK] file exists: requirements/Archguard Design 0.58.0 -> docs\requirements\archguard-design-0.58.0.md
[OK] file exists: requirements/Architecture Audit Facts 0.80.0 -> docs\requirements\architecture-audit-facts-0.80.0.md
[OK] file exists: requirements/Architecture Degradation Audit 0.57.0 -> docs\requirements\architecture-degradation-audit-0.57.0.md
[OK] file exists: requirements/Architecture Evolution 0.80.0 -> docs\requirements\architecture-evolution-0.80.0.md
[OK] file exists: requirements/Audit 140 Loop Runtime Wiring Gap 0.71.0 -> docs\requirements\audit-140-loop-runtime-wiring-gap-0.71.0.md
[OK] file exists: requirements/Audit 141 Task Dependency Priority Gap 0.71.0 -> docs\requirements\audit-141-task-dependency-priority-gap-0.71.0.md
[OK] file exists: requirements/Audit 143 Loop Planning Behavior Gap 0.74.0 -> docs\requirements\audit-143-loop-planning-behavior-gap-0.74.0.md
[OK] file exists: requirements/Audit 144 Dependency Blind Spot 0.75.0 -> docs\requirements\audit-144-dependency-blind-spot-0.75.0.md
[OK] file exists: requirements/Audit 145 Watchdog Design 0.76.0 -> docs\requirements\audit-145-watchdog-design-0.76.0.md
[OK] file exists: requirements/Audit 145 Watchdog Gap 0.76.0 -> docs\requirements\audit-145-watchdog-gap-0.76.0.md
[OK] file exists: requirements/Audit 146 Feat010 Dsh Config Loss Rca -> docs\requirements\audit-146-feat010-dsh-config-loss-rca.md
[OK] file exists: requirements/Audit 147 Governance Overhead Analysis Dsh Reasoning Level -> docs\requirements\audit-147-governance-overhead-analysis-dsh-reasoning-level.md
[OK] file exists: requirements/Audit 148 V1 Verify Alarm Validation -> docs\requirements\audit-148-v1-verify-alarm-validation.md
[OK] file exists: requirements/Audit 155 Arch Advisory 0.89.0 -> docs\requirements\audit-155-arch-advisory-0.89.0.md
[OK] file exists: requirements/Audit 155 Loop Gate Bias Behavior 0.89.0 -> docs\requirements\audit-155-loop-gate-bias-behavior-0.89.0.md
[OK] file exists: requirements/Audit 155 Loop Gate Bias Structure 0.89.0 -> docs\requirements\audit-155-loop-gate-bias-structure-0.89.0.md
[OK] file exists: requirements/Capability Discovery Orchestration 0.45.0 -> docs\requirements\capability-discovery-orchestration-0.45.0.md
[OK] file exists: requirements/Codex Desktop Marketplace E2E 0.45.0 -> docs\requirements\codex-desktop-marketplace-e2e-0.45.0.md
[OK] file exists: requirements/Codex Desktop Marketplace Lifecycle 0.49.0 -> docs\requirements\codex-desktop-marketplace-lifecycle-0.49.0.md
[OK] file exists: requirements/Command Surface Consolidation Research Audit 120 -> docs\requirements\command-surface-consolidation-research-audit-120.md
[OK] file exists: requirements/Composable Governance Packs 0.44.0 -> docs\requirements\composable-governance-packs-0.44.0.md
[OK] file exists: requirements/Data Inventory 0.80.0 -> docs\requirements\data-inventory-0.80.0.md
[OK] file exists: requirements/Dsh Compat Design 0.81.0 -> docs\requirements\dsh-compat-design-0.81.0.md
[OK] file exists: requirements/Dsh Host Dependency Inventory 0.81.0 -> docs\requirements\dsh-host-dependency-inventory-0.81.0.md
[OK] file exists: requirements/Dynamic Lifecycle Flow Gate 0.51.0 -> docs\requirements\dynamic-lifecycle-flow-gate-0.51.0.md
[OK] file exists: requirements/Entry Loop Planning Rearchitecture 0.72.0 -> docs\requirements\entry-loop-planning-rearchitecture-0.72.0.md
[OK] file exists: requirements/Entry Resolver Architecture 0.64.0 -> docs\requirements\entry-resolver-architecture-0.64.0.md
[OK] file exists: requirements/Env Failure Classification 0.80.0 -> docs\requirements\env-failure-classification-0.80.0.md
[OK] file exists: requirements/External Project Validation 0.49.0 -> docs\requirements\external-project-validation-0.49.0.md
[OK] file exists: requirements/Final Command E2E Ledger 0.48.0 -> docs\requirements\final-command-e2e-ledger-0.48.0.md
[OK] file exists: requirements/First Session Measurement 0.43.0 -> docs\requirements\first-session-measurement-0.43.0.md
[OK] file exists: requirements/Five Minute Success Path 0.42.0 -> docs\requirements\five-minute-success-path-0.42.0.md
[OK] file exists: requirements/Fix 056 Agent Concurrency Requirement Clarification -> docs\requirements\FIX-056-agent-concurrency-requirement-clarification.md
[OK] file exists: requirements/Fix 253 Injection Surface Design 0.75.0 -> docs\requirements\fix-253-injection-surface-design-0.75.0.md
[OK] file exists: requirements/Fix 445 Health Resume Clarification 20261013 -> docs\requirements\FIX-445-health-resume-clarification-20261013.md
[OK] file exists: requirements/Governance Bootstrap Cost Audit 0.84.0 -> docs\requirements\governance-bootstrap-cost-audit-0.84.0.md
[OK] file exists: requirements/Governance Eval Benchmark 0.45.0 -> docs\requirements\governance-eval-benchmark-0.45.0.md
[OK] file exists: requirements/Legacy Requirement Reconciliation 0.48.0 -> docs\requirements\legacy-requirement-reconciliation-0.48.0.md
[OK] file exists: requirements/Loop Engineering Architecture 0.65.0 Proposed -> docs\requirements\loop-engineering-architecture-0.65.0-proposed.md
[OK] file exists: requirements/Loop Engineering Implementation Breakdown 0.65.0 -> docs\requirements\loop-engineering-implementation-breakdown-0.65.0.md
[OK] file exists: requirements/Loop Engineering Post Implementation Audit 0.66.0 -> docs\requirements\loop-engineering-post-implementation-audit-0.66.0.md
[OK] file exists: requirements/Mainstream Agent E2E Risk Release 0.50.0 -> docs\requirements\mainstream-agent-e2e-risk-release-0.50.0.md
[OK] file exists: requirements/Mainstream Agent Loading 0.47.0 -> docs\requirements\mainstream-agent-loading-0.47.0.md
[OK] file exists: requirements/Official Submission Final Bundle Review 0.49.0 -> docs\requirements\official-submission-final-bundle-review-0.49.0.md
[OK] file exists: requirements/One Dot Zero Readiness Gap Analysis 0.48.0 -> docs\requirements\one-dot-zero-readiness-gap-analysis-0.48.0.md
[OK] file exists: requirements/Pi Adapter Design 0.99.0 -> docs\requirements\pi-adapter-design-0.99.0.md
[OK] file exists: requirements/Post Release Review 0.40.1 0.42.0 -> docs\requirements\post-release-review-0.40.1-0.42.0.md
[OK] file exists: requirements/Python Game Dynamic Lifecycle Validation 0.55.0 -> docs\requirements\python-game-dynamic-lifecycle-validation-0.55.0.md
[OK] file exists: requirements/Python Game External Validation 0.50.3 -> docs\requirements\python-game-external-validation-0.50.3.md
[OK] file exists: requirements/Quickscan Evaluation 0.79.0 -> docs\requirements\quickscan-evaluation-0.79.0.md
[OK] file exists: requirements/Runtime Readiness Matrix 0.43.0 -> docs\requirements\runtime-readiness-matrix-0.43.0.md
[OK] file exists: requirements/Shitu Dynamic Lifecycle Validation 0.55.0 -> docs\requirements\shitu-dynamic-lifecycle-validation-0.55.0.md
[OK] file exists: requirements/Shitu External Validation 0.50.3 -> docs\requirements\shitu-external-validation-0.50.3.md
[OK] file exists: requirements/Shitu Loop Engineering Validation 0.65.0 -> docs\requirements\shitu-loop-engineering-validation-0.65.0.md
[OK] file exists: requirements/Sysgap 047 Entry Bootstrap Paradox 0.71.0 -> docs\requirements\sysgap-047-entry-bootstrap-paradox-0.71.0.md
[OK] file exists: requirements/Test Baseline 0.80.0 -> docs\requirements\test-baseline-0.80.0.md
[OK] file exists: requirements/User Entry Audit 2026 05 04 -> docs\requirements\user-entry-audit-2026-05-04.md
[OK] file exists: requirements/Verify Workflow Split Phase1 Manifest Domain 0.59.0 -> docs\requirements\verify-workflow-split-phase1-manifest-domain-0.59.0.md
[OK] file exists: requirements/Verify Workflow Split Phase2 Capability Registry 0.60.0 -> docs\requirements\verify-workflow-split-phase2-capability-registry-0.60.0.md
[OK] file exists: requirements/Workflow Premise Fact Constraint Gap Research -> docs\requirements\workflow-premise-fact-constraint-gap-research.md
[OK] file exists: research/Dsh 0.2 Upgrade Decoupling -> docs\research\dsh-0.2-upgrade-decoupling.md
[OK] file exists: research/Feat 086 Prospective Samples 2026 10 04 -> docs\research\feat-086-prospective-samples-2026-10-04.md
[OK] file exists: research/Feat 087 Channel Loss Samples 2026 10 05 -> docs\research\feat-087-channel-loss-samples-2026-10-05.md
[OK] file exists: research/Feat 095 Harness Enforcement Capability 2026 10 10 -> docs\research\feat-095-harness-enforcement-capability-2026-10-10.md
[OK] file exists: research/Governance Cost Baseline 0.83.0 -> docs\research\governance-cost-baseline-0.83.0.md
[OK] file exists: research/Pi Adapter Integration Research 0.98.0 -> docs\research\pi-adapter-integration-research-0.98.0.md
[OK] file exists: research/Quickscan Wiring Evaluation 0.94.0 -> docs\research\quickscan-wiring-evaluation-0.94.0.md
[OK] file exists: research/Thin Open Evolution Current State 2026 10 04 -> docs\research\thin-open-evolution-current-state-2026-10-04.md
[OK] file exists: research/Thin Open Evolution Phase0 Baseline 2026 10 04 -> docs\research\thin-open-evolution-phase0-baseline-2026-10-04.md
[OK] file exists: research/Thin Open Evolution Proposal 2026 10 04 -> docs\research\thin-open-evolution-proposal-2026-10-04.md
[OK] file exists: reviews/Analysis Fix 427 -> docs\reviews\analysis-FIX-427.md
[OK] file exists: reviews/Performance Feat 097 Attribution -> docs\reviews\performance-FEAT-097-attribution.md
[OK] file exists: reviews/Review Audit 150 Design R0 -> docs\reviews\review-AUDIT-150-DESIGN-R0.md
[OK] file exists: reviews/Review Audit 152 Code R0 -> docs\reviews\review-AUDIT-152-CODE-R0.md
[OK] file exists: reviews/Review Audit 155 156 Design R0 -> docs\reviews\review-AUDIT-155-156-DESIGN-R0.md
[OK] file exists: reviews/Review Audit 155 156 Design R1 -> docs\reviews\review-AUDIT-155-156-DESIGN-R1.md
[OK] file exists: reviews/Review Design 021 Design R0 -> docs\reviews\review-DESIGN-021-DESIGN-R0.md
[OK] file exists: reviews/Review Design 021 Design R1 -> docs\reviews\review-DESIGN-021-DESIGN-R1.md
[OK] file exists: reviews/Review Feat 011 Code R0 -> docs\reviews\review-FEAT-011-CODE-R0.md
[OK] file exists: reviews/Review Feat 011 Code R2 -> docs\reviews\review-FEAT-011-CODE-R2.md
[OK] file exists: reviews/Review Feat 011 Design R0 -> docs\reviews\review-FEAT-011-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 012 Code R0 -> docs\reviews\review-FEAT-012-CODE-R0.md
[OK] file exists: reviews/Review Feat 013 Code R0 -> docs\reviews\review-FEAT-013-CODE-R0.md
[OK] file exists: reviews/Review Feat 014 Code R0 -> docs\reviews\review-FEAT-014-CODE-R0.md
[OK] file exists: reviews/Review Feat 014 Code R1 -> docs\reviews\review-FEAT-014-CODE-R1.md
[OK] file exists: reviews/Review Feat 015 Code R0 -> docs\reviews\review-FEAT-015-CODE-R0.md
[OK] file exists: reviews/Review Feat 016 Code R0 -> docs\reviews\review-FEAT-016-CODE-R0.md
[OK] file exists: reviews/Review Feat 017 Code R0 -> docs\reviews\review-FEAT-017-CODE-R0.md
[OK] file exists: reviews/Review Feat 018 Code R0 -> docs\reviews\review-FEAT-018-CODE-R0.md
[OK] file exists: reviews/Review Feat 019 Code R0 -> docs\reviews\review-FEAT-019-CODE-R0.md
[OK] file exists: reviews/Review Feat 019 Design R0 -> docs\reviews\review-FEAT-019-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 020 Code R0 -> docs\reviews\review-FEAT-020-CODE-R0.md
[OK] file exists: reviews/Review Feat 021 Code R0 -> docs\reviews\review-FEAT-021-CODE-R0.md
[OK] file exists: reviews/Review Feat 022 Code R0 -> docs\reviews\review-FEAT-022-CODE-R0.md
[OK] file exists: reviews/Review Feat 025 Code R0 -> docs\reviews\review-FEAT-025-CODE-R0.md
[OK] file exists: reviews/Review Feat 026 Code R0 -> docs\reviews\review-FEAT-026-CODE-R0.md
[OK] file exists: reviews/Review Feat 028 Design R0 -> docs\reviews\review-FEAT-028-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 028 Design R1 -> docs\reviews\review-FEAT-028-DESIGN-R1.md
[OK] file exists: reviews/Review Feat 029 Code R0 -> docs\reviews\review-FEAT-029-CODE-R0.md
[OK] file exists: reviews/Review Feat 030 Code R0 -> docs\reviews\review-FEAT-030-CODE-R0.md
[OK] file exists: reviews/Review Feat 030 Code R1 -> docs\reviews\review-FEAT-030-CODE-R1.md
[OK] file exists: reviews/Review Feat 031 Code R0 -> docs\reviews\review-FEAT-031-CODE-R0.md
[OK] file exists: reviews/Review Feat 031 Code R1 -> docs\reviews\review-FEAT-031-CODE-R1.md
[OK] file exists: reviews/Review Feat 032 Code R0 -> docs\reviews\review-FEAT-032-CODE-R0.md
[OK] file exists: reviews/Review Feat 033 Code R0 -> docs\reviews\review-FEAT-033-CODE-R0.md
[OK] file exists: reviews/Review Feat 033 Code R1 -> docs\reviews\review-FEAT-033-CODE-R1.md
[OK] file exists: reviews/Review Feat 034 Design R0 -> docs\reviews\review-FEAT-034-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 035 Design R0 -> docs\reviews\review-FEAT-035-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 035 Design R1 -> docs\reviews\review-FEAT-035-DESIGN-R1.md
[OK] file exists: reviews/Review Feat 036 Code R0 -> docs\reviews\review-FEAT-036-CODE-R0.md
[OK] file exists: reviews/Review Feat 036 Code R1 -> docs\reviews\review-FEAT-036-CODE-R1.md
[OK] file exists: reviews/Review Feat 037 Code R0 -> docs\reviews\review-FEAT-037-CODE-R0.md
[OK] file exists: reviews/Review Feat 038 Code R0 -> docs\reviews\review-FEAT-038-CODE-R0.md
[OK] file exists: reviews/Review Feat 039 Code R0 -> docs\reviews\review-FEAT-039-CODE-R0.md
[OK] file exists: reviews/Review Feat 039 Code R1 -> docs\reviews\review-FEAT-039-CODE-R1.md
[OK] file exists: reviews/Review Feat 040 Code R0 -> docs\reviews\review-FEAT-040-CODE-R0.md
[OK] file exists: reviews/Review Feat 040 Code R1 -> docs\reviews\review-FEAT-040-CODE-R1.md
[OK] file exists: reviews/Review Feat 041 Code R0 -> docs\reviews\review-FEAT-041-CODE-R0.md
[OK] file exists: reviews/Review Feat 041 Code R1 -> docs\reviews\review-FEAT-041-CODE-R1.md
[OK] file exists: reviews/Review Feat 044 Code R0 -> docs\reviews\review-FEAT-044-CODE-R0.md
[OK] file exists: reviews/Review Feat 045 Code R0 -> docs\reviews\review-FEAT-045-CODE-R0.md
[OK] file exists: reviews/Review Feat 046 Code R0 -> docs\reviews\review-FEAT-046-CODE-R0.md
[OK] file exists: reviews/Review Feat 046 Code R1 -> docs\reviews\review-FEAT-046-CODE-R1.md
[OK] file exists: reviews/Review Feat 047 Code R0 -> docs\reviews\review-FEAT-047-CODE-R0.md
[OK] file exists: reviews/Review Feat 047 Code R1 -> docs\reviews\review-FEAT-047-CODE-R1.md
[OK] file exists: reviews/Review Feat 049 Code R0 -> docs\reviews\review-FEAT-049-CODE-R0.md
[OK] file exists: reviews/Review Feat 050 Code R0 -> docs\reviews\review-FEAT-050-CODE-R0.md
[OK] file exists: reviews/Review Feat 051 Code R0 -> docs\reviews\review-FEAT-051-CODE-R0.md
[OK] file exists: reviews/Review Feat 051 Code R1 -> docs\reviews\review-FEAT-051-CODE-R1.md
[OK] file exists: reviews/Review Feat 052 Code R0 -> docs\reviews\review-FEAT-052-CODE-R0.md
[OK] file exists: reviews/Review Feat 053 Code R0 -> docs\reviews\review-FEAT-053-CODE-R0.md
[OK] file exists: reviews/Review Feat 054 Release R0 -> docs\reviews\review-FEAT-054-RELEASE-R0.md
[OK] file exists: reviews/Review Feat 054 Release R1 -> docs\reviews\review-FEAT-054-RELEASE-R1.md
[OK] file exists: reviews/Review Feat 055 Code R0 -> docs\reviews\review-FEAT-055-CODE-R0.md
[OK] file exists: reviews/Review Feat 056 Code R0 -> docs\reviews\review-FEAT-056-CODE-R0.md
[OK] file exists: reviews/Review Feat 057 Code R0 -> docs\reviews\review-FEAT-057-CODE-R0.md
[OK] file exists: reviews/Review Feat 057 Code R1 -> docs\reviews\review-FEAT-057-CODE-R1.md
[OK] file exists: reviews/Review Feat 058 Release R0 -> docs\reviews\review-FEAT-058-RELEASE-R0.md
[OK] file exists: reviews/Review Feat 059 Release R0 -> docs\reviews\review-FEAT-059-RELEASE-R0.md
[OK] file exists: reviews/Review Feat 060 Code R0 -> docs\reviews\review-FEAT-060-CODE-R0.md
[OK] file exists: reviews/Review Feat 061 Code R0 Fix -> docs\reviews\review-FEAT-061-CODE-R0-fix.md
[OK] file exists: reviews/Review Feat 061 Code R0 -> docs\reviews\review-FEAT-061-CODE-R0.md
[OK] file exists: reviews/Review Feat 061 Code R1 -> docs\reviews\review-FEAT-061-CODE-R1.md
[OK] file exists: reviews/Review Feat 062 Code R0 -> docs\reviews\review-FEAT-062-CODE-R0.md
[OK] file exists: reviews/Review Feat 062 Code R1 -> docs\reviews\review-FEAT-062-CODE-R1.md
[OK] file exists: reviews/Review Feat 063 Code R0 -> docs\reviews\review-FEAT-063-CODE-R0.md
[OK] file exists: reviews/Review Feat 063 Code R1 -> docs\reviews\review-FEAT-063-CODE-R1.md
[OK] file exists: reviews/Review Feat 064 Code R0 -> docs\reviews\review-FEAT-064-CODE-R0.md
[OK] file exists: reviews/Review Feat 065 Code R0 -> docs\reviews\review-FEAT-065-CODE-R0.md
[OK] file exists: reviews/Review Feat 067 Design R0 -> docs\reviews\review-FEAT-067-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 067 Design R1 -> docs\reviews\review-FEAT-067-DESIGN-R1.md
[OK] file exists: reviews/Review Feat 068 Code R0 -> docs\reviews\review-FEAT-068-CODE-R0.md
[OK] file exists: reviews/Review Feat 069 Code R0 -> docs\reviews\review-FEAT-069-CODE-R0.md
[OK] file exists: reviews/Review Feat 070 Code R0 -> docs\reviews\review-FEAT-070-CODE-R0.md
[OK] file exists: reviews/Review Feat 071 Code R0 -> docs\reviews\review-FEAT-071-CODE-R0.md
[OK] file exists: reviews/Review Feat 072 Design R0 -> docs\reviews\review-FEAT-072-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 073 R0 -> docs\reviews\review-FEAT-073-R0.md
[OK] file exists: reviews/Review Feat 073 R1 -> docs\reviews\review-FEAT-073-R1.md
[OK] file exists: reviews/Review Feat 074 R0 -> docs\reviews\review-FEAT-074-R0.md
[OK] file exists: reviews/Review Feat 074 R1 -> docs\reviews\review-FEAT-074-R1.md
[OK] file exists: reviews/Review Feat 075 R0 -> docs\reviews\review-FEAT-075-R0.md
[OK] file exists: reviews/Review Feat 075 R1 -> docs\reviews\review-FEAT-075-R1.md
[OK] file exists: reviews/Review Feat 076 Code R0 -> docs\reviews\review-FEAT-076-CODE-R0.md
[OK] file exists: reviews/Review Feat 077 Code R0 -> docs\reviews\review-FEAT-077-CODE-R0.md
[OK] file exists: reviews/Review Feat 077 Code R1 -> docs\reviews\review-FEAT-077-CODE-R1.md
[OK] file exists: reviews/Review Feat 078 Code R0 -> docs\reviews\review-FEAT-078-CODE-R0.md
[OK] file exists: reviews/Review Feat 079 Code R0 -> docs\reviews\review-FEAT-079-CODE-R0.md
[OK] file exists: reviews/Review Feat 080 Code R0 -> docs\reviews\review-FEAT-080-CODE-R0.md
[OK] file exists: reviews/Review Feat 081 Code R0 -> docs\reviews\review-FEAT-081-CODE-R0.md
[OK] file exists: reviews/Review Feat 082 Code R0 -> docs\reviews\review-FEAT-082-CODE-R0.md
[OK] file exists: reviews/Review Feat 083 Code R0 -> docs\reviews\review-FEAT-083-CODE-R0.md
[OK] file exists: reviews/Review Feat 085 Design R0 -> docs\reviews\review-FEAT-085-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 086 Design R0 -> docs\reviews\review-FEAT-086-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 087 Design R0 -> docs\reviews\review-FEAT-087-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 088 Code R0 -> docs\reviews\review-FEAT-088-CODE-R0.md
[OK] file exists: reviews/Review Feat 089 Code R0 -> docs\reviews\review-FEAT-089-CODE-R0.md
[OK] file exists: reviews/Review Feat 090 092 Code R0 -> docs\reviews\review-FEAT-090-092-CODE-R0.md
[OK] file exists: reviews/Review Feat 093 Code R0 -> docs\reviews\review-FEAT-093-CODE-R0.md
[OK] file exists: reviews/Review Feat 093 Code R1 -> docs\reviews\review-FEAT-093-CODE-R1.md
[OK] file exists: reviews/Review Feat 094 Code R0 -> docs\reviews\review-FEAT-094-CODE-R0.md
[OK] file exists: reviews/Review Feat 095 Code R0 -> docs\reviews\review-FEAT-095-CODE-R0.md
[OK] file exists: reviews/Review Feat 095 Code R1 -> docs\reviews\review-FEAT-095-CODE-R1.md
[OK] file exists: reviews/Review Feat 096 Code R0 -> docs\reviews\review-FEAT-096-CODE-R0.md
[OK] file exists: reviews/Review Feat 096 Code R1 -> docs\reviews\review-FEAT-096-CODE-R1.md
[OK] file exists: reviews/Review Feat 097 Code R0 -> docs\reviews\review-FEAT-097-CODE-R0.md
[OK] file exists: reviews/Review Feat 097 Code R1 -> docs\reviews\review-FEAT-097-CODE-R1.md
[OK] file exists: reviews/Review Feat 097 Code R2 -> docs\reviews\review-FEAT-097-CODE-R2.md
[OK] file exists: reviews/Review Feat 097 Code R3 -> docs\reviews\review-FEAT-097-CODE-R3.md
[OK] file exists: reviews/Review Feat 097 Code R4 -> docs\reviews\review-FEAT-097-CODE-R4.md
[OK] file exists: reviews/Review Feat 097 Code R5 -> docs\reviews\review-FEAT-097-CODE-R5.md
[OK] file exists: reviews/Review Feat 097 Code R6 -> docs\reviews\review-FEAT-097-CODE-R6.md
[OK] file exists: reviews/Review Feat 100 Code R0 -> docs\reviews\review-FEAT-100-CODE-R0.md
[OK] file exists: reviews/Review Feat 100 Code R2 -> docs\reviews\review-FEAT-100-CODE-R2.md
[OK] file exists: reviews/Review Feat 100 Design R0 -> docs\reviews\review-FEAT-100-DESIGN-R0.md
[OK] file exists: reviews/Review Feat 101 Code R0 -> docs\reviews\review-FEAT-101-CODE-R0.md
[OK] file exists: reviews/Review Feat 102 Design R0 -> docs\reviews\review-FEAT-102-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 282 Code R0 -> docs\reviews\review-FIX-282-CODE-R0.md
[OK] file exists: reviews/Review Fix 283 Code R0 -> docs\reviews\review-FIX-283-CODE-R0.md
[OK] file exists: reviews/Review Fix 284 Code R0 -> docs\reviews\review-FIX-284-CODE-R0.md
[OK] file exists: reviews/Review Fix 285 Code R0 -> docs\reviews\review-FIX-285-CODE-R0.md
[OK] file exists: reviews/Review Fix 286 Code R0 -> docs\reviews\review-FIX-286-CODE-R0.md
[OK] file exists: reviews/Review Fix 287 Code R0 -> docs\reviews\review-FIX-287-CODE-R0.md
[OK] file exists: reviews/Review Fix 288 Code R0 -> docs\reviews\review-FIX-288-CODE-R0.md
[OK] file exists: reviews/Review Fix 289 Code R0 -> docs\reviews\review-FIX-289-CODE-R0.md
[OK] file exists: reviews/Review Fix 291 Code R0 -> docs\reviews\review-FIX-291-CODE-R0.md
[OK] file exists: reviews/Review Fix 291 Code R1 -> docs\reviews\review-FIX-291-CODE-R1.md
[OK] file exists: reviews/Review Fix 291 Code R2 -> docs\reviews\review-FIX-291-CODE-R2.md
[OK] file exists: reviews/Review Fix 291 Design R0 -> docs\reviews\review-FIX-291-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 291 Design R1 -> docs\reviews\review-FIX-291-DESIGN-R1.md
[OK] file exists: reviews/Review Fix 291 Design R2 -> docs\reviews\review-FIX-291-DESIGN-R2.md
[OK] file exists: reviews/Review Fix 292 Code R0 -> docs\reviews\review-FIX-292-CODE-R0.md
[OK] file exists: reviews/Review Fix 292 Design R0 -> docs\reviews\review-FIX-292-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 294 Code R0 -> docs\reviews\review-FIX-294-CODE-R0.md
[OK] file exists: reviews/Review Fix 295 Code R0 -> docs\reviews\review-FIX-295-CODE-R0.md
[OK] file exists: reviews/Review Fix 296 Code R0 -> docs\reviews\review-FIX-296-CODE-R0.md
[OK] file exists: reviews/Review Fix 297 Design R0 -> docs\reviews\review-FIX-297-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 299 Code R0 -> docs\reviews\review-FIX-299-CODE-R0.md
[OK] file exists: reviews/Review Fix 300 Code R0 -> docs\reviews\review-FIX-300-CODE-R0.md
[OK] file exists: reviews/Review Fix 301 Code R0 -> docs\reviews\review-FIX-301-CODE-R0.md
[OK] file exists: reviews/Review Fix 302 Design R0 -> docs\reviews\review-FIX-302-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 303 Code R0 -> docs\reviews\review-FIX-303-CODE-R0.md
[OK] file exists: reviews/Review Fix 303 Code R1 -> docs\reviews\review-FIX-303-CODE-R1.md
[OK] file exists: reviews/Review Fix 304 Code R0 -> docs\reviews\review-FIX-304-CODE-R0.md
[OK] file exists: reviews/Review Fix 304 Code R1 -> docs\reviews\review-FIX-304-CODE-R1.md
[OK] file exists: reviews/Review Fix 305 Code R0 -> docs\reviews\review-FIX-305-CODE-R0.md
[OK] file exists: reviews/Review Fix 307 Code R0 -> docs\reviews\review-FIX-307-CODE-R0.md
[OK] file exists: reviews/Review Fix 311 Code R0 -> docs\reviews\review-FIX-311-CODE-R0.md
[OK] file exists: reviews/Review Fix 313 346 Code R0 -> docs\reviews\review-FIX-313-346-CODE-R0.md
[OK] file exists: reviews/Review Fix 313 Code R0 -> docs\reviews\review-FIX-313-CODE-R0.md
[OK] file exists: reviews/Review Fix 314 Code R0 -> docs\reviews\review-FIX-314-CODE-R0.md
[OK] file exists: reviews/Review Fix 314 Code R1 -> docs\reviews\review-FIX-314-CODE-R1.md
[OK] file exists: reviews/Review Fix 315 Code R0 -> docs\reviews\review-FIX-315-CODE-R0.md
[OK] file exists: reviews/Review Fix 315 Code R1 -> docs\reviews\review-FIX-315-CODE-R1.md
[OK] file exists: reviews/Review Fix 316 Code R0 -> docs\reviews\review-FIX-316-CODE-R0.md
[OK] file exists: reviews/Review Fix 316 Code R1 -> docs\reviews\review-FIX-316-CODE-R1.md
[OK] file exists: reviews/Review Fix 316 Code R2 -> docs\reviews\review-FIX-316-CODE-R2.md
[OK] file exists: reviews/Review Fix 317 Code R0 -> docs\reviews\review-FIX-317-CODE-R0.md
[OK] file exists: reviews/Review Fix 319 Code R0 -> docs\reviews\review-FIX-319-CODE-R0.md
[OK] file exists: reviews/Review Fix 320 322 Code R0 -> docs\reviews\review-FIX-320-322-CODE-R0.md
[OK] file exists: reviews/Review Fix 320 322 Code R1 -> docs\reviews\review-FIX-320-322-CODE-R1.md
[OK] file exists: reviews/Review Fix 321 Code R0 -> docs\reviews\review-FIX-321-CODE-R0.md
[OK] file exists: reviews/Review Fix 323 325 336 Code R0 -> docs\reviews\review-FIX-323-325-336-CODE-R0.md
[OK] file exists: reviews/Review Fix 324 326 Code R0 -> docs\reviews\review-FIX-324-326-CODE-R0.md
[OK] file exists: reviews/Review Fix 328 Code R0 -> docs\reviews\review-FIX-328-CODE-R0.md
[OK] file exists: reviews/Review Fix 330 Code R0 -> docs\reviews\review-FIX-330-CODE-R0.md
[OK] file exists: reviews/Review Fix 332 337 Design R0 -> docs\reviews\review-FIX-332-337-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 333 Code R0 -> docs\reviews\review-FIX-333-CODE-R0.md
[OK] file exists: reviews/Review Fix 333 Code R1 -> docs\reviews\review-FIX-333-CODE-R1.md
[OK] file exists: reviews/Review Fix 334 Code R0 -> docs\reviews\review-FIX-334-CODE-R0.md
[OK] file exists: reviews/Review Fix 339 Code R0 -> docs\reviews\review-FIX-339-CODE-R0.md
[OK] file exists: reviews/Review Fix 339 Code R1 -> docs\reviews\review-FIX-339-CODE-R1.md
[OK] file exists: reviews/Review Fix 339 Code R2 -> docs\reviews\review-FIX-339-CODE-R2.md
[OK] file exists: reviews/Review Fix 341 312 Code R0 -> docs\reviews\review-FIX-341-312-CODE-R0.md
[OK] file exists: reviews/Review Fix 342 344 Code R0 -> docs\reviews\review-FIX-342-344-CODE-R0.md
[OK] file exists: reviews/Review Fix 345 Code R0 -> docs\reviews\review-FIX-345-CODE-R0.md
[OK] file exists: reviews/Review Fix 348 Code R0 -> docs\reviews\review-FIX-348-CODE-R0.md
[OK] file exists: reviews/Review Fix 349 Code R0 -> docs\reviews\review-FIX-349-CODE-R0.md
[OK] file exists: reviews/Review Fix 350 Code R0 -> docs\reviews\review-FIX-350-CODE-R0.md
[OK] file exists: reviews/Review Fix 355 Code R0 -> docs\reviews\review-FIX-355-CODE-R0.md
[OK] file exists: reviews/Review Fix 356 Code R0 -> docs\reviews\review-FIX-356-CODE-R0.md
[OK] file exists: reviews/Review Fix 357 Code R0 -> docs\reviews\review-FIX-357-CODE-R0.md
[OK] file exists: reviews/Review Fix 358 Code R0 -> docs\reviews\review-FIX-358-CODE-R0.md
[OK] file exists: reviews/Review Fix 359 Code R0 -> docs\reviews\review-FIX-359-CODE-R0.md
[OK] file exists: reviews/Review Fix 360 Code R0 -> docs\reviews\review-FIX-360-CODE-R0.md
[OK] file exists: reviews/Review Fix 361 Code R0 -> docs\reviews\review-FIX-361-CODE-R0.md
[OK] file exists: reviews/Review Fix 362 Code R0 -> docs\reviews\review-FIX-362-CODE-R0.md
[OK] file exists: reviews/Review Fix 364 Code R0 -> docs\reviews\review-FIX-364-CODE-R0.md
[OK] file exists: reviews/Review Fix 365 Code R0 -> docs\reviews\review-FIX-365-CODE-R0.md
[OK] file exists: reviews/Review Fix 366 Code R0 -> docs\reviews\review-FIX-366-CODE-R0.md
[OK] file exists: reviews/Review Fix 368 Code R0 -> docs\reviews\review-FIX-368-CODE-R0.md
[OK] file exists: reviews/Review Fix 369 Code R0 -> docs\reviews\review-FIX-369-CODE-R0.md
[OK] file exists: reviews/Review Fix 370 Code R0 -> docs\reviews\review-FIX-370-CODE-R0.md
[OK] file exists: reviews/Review Fix 371 Code R0 -> docs\reviews\review-FIX-371-CODE-R0.md
[OK] file exists: reviews/Review Fix 372 Code R0 -> docs\reviews\review-FIX-372-CODE-R0.md
[OK] file exists: reviews/Review Fix 373 Code R0 -> docs\reviews\review-FIX-373-CODE-R0.md
[OK] file exists: reviews/Review Fix 374 Code R0 -> docs\reviews\review-FIX-374-CODE-R0.md
[OK] file exists: reviews/Review Fix 375 Code R0 -> docs\reviews\review-FIX-375-CODE-R0.md
[OK] file exists: reviews/Review Fix 375 Code R1 -> docs\reviews\review-FIX-375-CODE-R1.md
[OK] file exists: reviews/Review Fix 376 Code R0 -> docs\reviews\review-FIX-376-CODE-R0.md
[OK] file exists: reviews/Review Fix 377 Code R0 -> docs\reviews\review-FIX-377-CODE-R0.md
[OK] file exists: reviews/Review Fix 378 Code R0 -> docs\reviews\review-FIX-378-CODE-R0.md
[OK] file exists: reviews/Review Fix 379 Code R0 -> docs\reviews\review-FIX-379-CODE-R0.md
[OK] file exists: reviews/Review Fix 380 Code R0 -> docs\reviews\review-FIX-380-CODE-R0.md
[OK] file exists: reviews/Review Fix 381 Code R0 -> docs\reviews\review-FIX-381-CODE-R0.md
[OK] file exists: reviews/Review Fix 382 Code R0 -> docs\reviews\review-FIX-382-CODE-R0.md
[OK] file exists: reviews/Review Fix 383 Code R0 -> docs\reviews\review-FIX-383-CODE-R0.md
[OK] file exists: reviews/Review Fix 384 Code R0 -> docs\reviews\review-FIX-384-CODE-R0.md
[OK] file exists: reviews/Review Fix 384 Code R1 -> docs\reviews\review-FIX-384-CODE-R1.md
[OK] file exists: reviews/Review Fix 385 Code R0 -> docs\reviews\review-FIX-385-CODE-R0.md
[OK] file exists: reviews/Review Fix 385 Code R1 -> docs\reviews\review-FIX-385-CODE-R1.md
[OK] file exists: reviews/Review Fix 386 Code R0 -> docs\reviews\review-FIX-386-CODE-R0.md
[OK] file exists: reviews/Review Fix 386 Code R1 -> docs\reviews\review-FIX-386-CODE-R1.md
[OK] file exists: reviews/Review Fix 387 Code R0 -> docs\reviews\review-FIX-387-CODE-R0.md
[OK] file exists: reviews/Review Fix 388 Code R0 -> docs\reviews\review-FIX-388-CODE-R0.md
[OK] file exists: reviews/Review Fix 389 Code R0 -> docs\reviews\review-FIX-389-CODE-R0.md
[OK] file exists: reviews/Review Fix 390 Code R0 -> docs\reviews\review-FIX-390-CODE-R0.md
[OK] file exists: reviews/Review Fix 391 Code R0 -> docs\reviews\review-FIX-391-CODE-R0.md
[OK] file exists: reviews/Review Fix 392 Code R0 -> docs\reviews\review-FIX-392-CODE-R0.md
[OK] file exists: reviews/Review Fix 393 Code R0 -> docs\reviews\review-FIX-393-CODE-R0.md
[OK] file exists: reviews/Review Fix 394 Code R0 -> docs\reviews\review-FIX-394-CODE-R0.md
[OK] file exists: reviews/Review Fix 394 Code R1 -> docs\reviews\review-FIX-394-CODE-R1.md
[OK] file exists: reviews/Review Fix 395 Code R0 -> docs\reviews\review-FIX-395-CODE-R0.md
[OK] file exists: reviews/Review Fix 395 Code R1 -> docs\reviews\review-FIX-395-CODE-R1.md
[OK] file exists: reviews/Review Fix 396 Design R0 -> docs\reviews\review-FIX-396-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 397 Code R0 -> docs\reviews\review-FIX-397-CODE-R0.md
[OK] file exists: reviews/Review Fix 398 Code R0 -> docs\reviews\review-FIX-398-CODE-R0.md
[OK] file exists: reviews/Review Fix 399 Code R0 -> docs\reviews\review-FIX-399-CODE-R0.md
[OK] file exists: reviews/Review Fix 400 R0 -> docs\reviews\review-FIX-400-R0.md
[OK] file exists: reviews/Review Fix 401 R0 -> docs\reviews\review-FIX-401-R0.md
[OK] file exists: reviews/Review Fix 402 R0 -> docs\reviews\review-FIX-402-R0.md
[OK] file exists: reviews/Review Fix 402 R1 -> docs\reviews\review-FIX-402-R1.md
[OK] file exists: reviews/Review Fix 402 R2 -> docs\reviews\review-FIX-402-R2.md
[OK] file exists: reviews/Review Fix 403 Code R0 -> docs\reviews\review-FIX-403-CODE-R0.md
[OK] file exists: reviews/Review Fix 404 Code R0 -> docs\reviews\review-FIX-404-CODE-R0.md
[OK] file exists: reviews/Review Fix 405 Code R0 -> docs\reviews\review-FIX-405-CODE-R0.md
[OK] file exists: reviews/Review Fix 405 Code R1 -> docs\reviews\review-FIX-405-CODE-R1.md
[OK] file exists: reviews/Review Fix 407 Code R0 -> docs\reviews\review-FIX-407-CODE-R0.md
[OK] file exists: reviews/Review Fix 409 Code R0 -> docs\reviews\review-FIX-409-CODE-R0.md
[OK] file exists: reviews/Review Fix 410 Code R0 -> docs\reviews\review-FIX-410-CODE-R0.md
[OK] file exists: reviews/Review Fix 424 Code R0 -> docs\reviews\review-FIX-424-CODE-R0.md
[OK] file exists: reviews/Review Fix 425 Code R0 -> docs\reviews\review-FIX-425-CODE-R0.md
[OK] file exists: reviews/Review Fix 426 Code R0 -> docs\reviews\review-FIX-426-CODE-R0.md
[OK] file exists: reviews/Review Fix 430 Code R0 -> docs\reviews\review-FIX-430-CODE-R0.md
[OK] file exists: reviews/Review Fix 430 Code R1 -> docs\reviews\review-FIX-430-CODE-R1.md
[OK] file exists: reviews/Review Fix 431 Code R0 -> docs\reviews\review-FIX-431-CODE-R0.md
[OK] file exists: reviews/Review Fix 432 Code R0 -> docs\reviews\review-FIX-432-CODE-R0.md
[OK] file exists: reviews/Review Fix 432 Code R1 -> docs\reviews\review-FIX-432-CODE-R1.md
[OK] file exists: reviews/Review Fix 433 Code R0 -> docs\reviews\review-FIX-433-CODE-R0.md
[OK] file exists: reviews/Review Fix 433 Code R1 -> docs\reviews\review-FIX-433-CODE-R1.md
[OK] file exists: reviews/Review Fix 434 Code R0 -> docs\reviews\review-FIX-434-CODE-R0.md
[OK] file exists: reviews/Review Fix 435 Code R0 -> docs\reviews\review-FIX-435-CODE-R0.md
[OK] file exists: reviews/Review Fix 435 Code R1 -> docs\reviews\review-FIX-435-CODE-R1.md
[OK] file exists: reviews/Review Fix 436 Code R0 -> docs\reviews\review-FIX-436-CODE-R0.md
[OK] file exists: reviews/Review Fix 438 Code R0 -> docs\reviews\review-FIX-438-CODE-R0.md
[OK] file exists: reviews/Review Fix 439 Code R0 -> docs\reviews\review-FIX-439-CODE-R0.md
[OK] file exists: reviews/Review Fix 440 Code R0 -> docs\reviews\review-FIX-440-CODE-R0.md
[OK] file exists: reviews/Review Fix 441 Code R0 -> docs\reviews\review-FIX-441-CODE-R0.md
[OK] file exists: reviews/Review Fix 442 Code R0 -> docs\reviews\review-FIX-442-CODE-R0.md
[OK] file exists: reviews/Review Fix 443 Code R0 -> docs\reviews\review-FIX-443-CODE-R0.md
[OK] file exists: reviews/Review Fix 444 Code R0 -> docs\reviews\review-FIX-444-CODE-R0.md
[OK] file exists: reviews/Review Fix 444 Code R1 -> docs\reviews\review-FIX-444-CODE-R1.md
[OK] file exists: reviews/Review Fix 444 Code R2 -> docs\reviews\review-FIX-444-CODE-R2.md
[OK] file exists: reviews/Review Fix 444 Code R3 -> docs\reviews\review-FIX-444-CODE-R3.md
[OK] file exists: reviews/Review Fix 445 Code R6 -> docs\reviews\review-FIX-445-CODE-R6.md
[OK] file exists: reviews/Review Fix 445 Design R0 -> docs\reviews\review-FIX-445-DESIGN-R0.md
[OK] file exists: reviews/Review Fix 445 Design R1 -> docs\reviews\review-FIX-445-DESIGN-R1.md
[OK] file exists: reviews/Review Fix 445 Design R10 -> docs\reviews\review-FIX-445-DESIGN-R10.md
[OK] file exists: reviews/Review Fix 445 Design R11 -> docs\reviews\review-FIX-445-DESIGN-R11.md
[OK] file exists: reviews/Review Fix 445 Design R12 -> docs\reviews\review-FIX-445-DESIGN-R12.md
[OK] file exists: reviews/Review Fix 445 Design R13 -> docs\reviews\review-FIX-445-DESIGN-R13.md
[OK] file exists: reviews/Review Fix 445 Design R14 -> docs\reviews\review-FIX-445-DESIGN-R14.md
[OK] file exists: reviews/Review Fix 445 Design R15 -> docs\reviews\review-FIX-445-DESIGN-R15.md
[OK] file exists: reviews/Review Fix 445 Design R2 -> docs\reviews\review-FIX-445-DESIGN-R2.md
[OK] file exists: reviews/Review Fix 445 Design R3 -> docs\reviews\review-FIX-445-DESIGN-R3.md
[OK] file exists: reviews/Review Fix 445 Design R4 -> docs\reviews\review-FIX-445-DESIGN-R4.md
[OK] file exists: reviews/Review Fix 445 Design R5 -> docs\reviews\review-FIX-445-DESIGN-R5.md
[OK] file exists: reviews/Review Fix 445 Design R7 -> docs\reviews\review-FIX-445-DESIGN-R7.md
[OK] file exists: reviews/Review Fix 445 Design R8 -> docs\reviews\review-FIX-445-DESIGN-R8.md
[OK] file exists: reviews/Review Fix 445 Design R9 -> docs\reviews\review-FIX-445-DESIGN-R9.md
[OK] file exists: reviews/Review Fix 446 Code R16 -> docs\reviews\review-FIX-446-CODE-R16.md
[OK] file exists: reviews/Review Fix 446 Code R17 -> docs\reviews\review-FIX-446-CODE-R17.md
[OK] file exists: reviews/Review Fix 449 Code R0 -> docs\reviews\review-FIX-449-CODE-R0.md
[OK] file exists: reviews/Review Fix 451 Code R0 -> docs\reviews\review-FIX-451-CODE-R0.md
[OK] file exists: reviews/Review Fix 452 Ci R0 -> docs\reviews\review-FIX-452-CI-R0.md
[OK] file exists: reviews/Review Fix 453 Marker R0 -> docs\reviews\review-FIX-453-MARKER-R0.md
[OK] file exists: reviews/Review Fx 195 Design R0 -> docs\reviews\review-FX-195-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 073 Design R0 -> docs\reviews\review-REL-073-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 073 Release R0 -> docs\reviews\review-REL-073-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 074 Design R0 -> docs\reviews\review-REL-074-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 074 Release R0 -> docs\reviews\review-REL-074-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 074 Release R1 -> docs\reviews\review-REL-074-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 074 Release R2 -> docs\reviews\review-REL-074-RELEASE-R2.md
[OK] file exists: reviews/Review Rel 075 Design R0 -> docs\reviews\review-REL-075-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 075 Release R0 -> docs\reviews\review-REL-075-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 076 Code R0 -> docs\reviews\review-REL-076-CODE-R0.md
[OK] file exists: reviews/Review Rel 076 Design R0 -> docs\reviews\review-REL-076-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 076 Design R1 -> docs\reviews\review-REL-076-DESIGN-R1.md
[OK] file exists: reviews/Review Rel 076 Release R0 -> docs\reviews\review-REL-076-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 076 Release R1 -> docs\reviews\review-REL-076-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 077 Code R0 -> docs\reviews\review-REL-077-CODE-R0.md
[OK] file exists: reviews/Review Rel 077 Code R1 -> docs\reviews\review-REL-077-CODE-R1.md
[OK] file exists: reviews/Review Rel 077 Release R0 -> docs\reviews\review-REL-077-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 077 Release R1 -> docs\reviews\review-REL-077-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 077 Release R2 -> docs\reviews\review-REL-077-RELEASE-R2.md
[OK] file exists: reviews/Review Rel 077 Release R3 -> docs\reviews\review-REL-077-RELEASE-R3.md
[OK] file exists: reviews/Review Rel 078 Code R0 -> docs\reviews\review-REL-078-CODE-R0.md
[OK] file exists: reviews/Review Rel 078 Code R1 -> docs\reviews\review-REL-078-CODE-R1.md
[OK] file exists: reviews/Review Rel 078 Release R0 -> docs\reviews\review-REL-078-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 078 Release R1 -> docs\reviews\review-REL-078-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 079 Code R0 -> docs\reviews\review-REL-079-CODE-R0.md
[OK] file exists: reviews/Review Rel 079 Release R0 -> docs\reviews\review-REL-079-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 080 Release R0 -> docs\reviews\review-REL-080-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 080 Release R1 -> docs\reviews\review-REL-080-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 080 Release R2 -> docs\reviews\review-REL-080-RELEASE-R2.md
[OK] file exists: reviews/Review Rel 080 Release R3 -> docs\reviews\review-REL-080-RELEASE-R3.md
[OK] file exists: reviews/Review Rel 080 Release R4 -> docs\reviews\review-REL-080-RELEASE-R4.md
[OK] file exists: reviews/Review Rel 080 Release R5 -> docs\reviews\review-REL-080-RELEASE-R5.md
[OK] file exists: reviews/Review Rel 080 Release R6 -> docs\reviews\review-REL-080-RELEASE-R6.md
[OK] file exists: reviews/Review Rel 081 Design R0 -> docs\reviews\review-REL-081-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 081 Design R1 -> docs\reviews\review-REL-081-DESIGN-R1.md
[OK] file exists: reviews/Review Rel 081 Release R0 -> docs\reviews\review-REL-081-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 081 Release R1 -> docs\reviews\review-REL-081-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 082 Design R0 -> docs\reviews\review-REL-082-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 082 Design R1 -> docs\reviews\review-REL-082-DESIGN-R1.md
[OK] file exists: reviews/Review Rel 082 Release R0 -> docs\reviews\review-REL-082-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 082 Release R1 -> docs\reviews\review-REL-082-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 083 Release R0 -> docs\reviews\review-REL-083-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 084 Design R0 -> docs\reviews\review-REL-084-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 084 Design R1 -> docs\reviews\review-REL-084-DESIGN-R1.md
[OK] file exists: reviews/Review Rel 084 M3 Design R0 -> docs\reviews\review-REL-084-M3-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 084 M3 Release R0 -> docs\reviews\review-REL-084-M3-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 084 Release R0 -> docs\reviews\review-REL-084-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 086 Code M3 -> docs\reviews\review-REL-086-CODE-M3.md
[OK] file exists: reviews/Review Rel 086 Design R0 -> docs\reviews\review-REL-086-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 086 Design R1 -> docs\reviews\review-REL-086-DESIGN-R1.md
[OK] file exists: reviews/Review Rel 086 Release M3 R1 -> docs\reviews\review-REL-086-RELEASE-M3-R1.md
[OK] file exists: reviews/Review Rel 086 Release M3 R2 -> docs\reviews\review-REL-086-RELEASE-M3-R2.md
[OK] file exists: reviews/Review Rel 086 Release M3 R3 -> docs\reviews\review-REL-086-RELEASE-M3-R3.md
[OK] file exists: reviews/Review Rel 086 Release M3 -> docs\reviews\review-REL-086-RELEASE-M3.md
[OK] file exists: reviews/Review Rel 086 Release R0 -> docs\reviews\review-REL-086-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 086 Release R1 -> docs\reviews\review-REL-086-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 086 Release R2 -> docs\reviews\review-REL-086-RELEASE-R2.md
[OK] file exists: reviews/Review Rel 087 Code R0 -> docs\reviews\review-REL-087-CODE-R0.md
[OK] file exists: reviews/Review Rel 088 Code R0 -> docs\reviews\review-REL-088-CODE-R0.md
[OK] file exists: reviews/Review Rel 089 Code R0 -> docs\reviews\review-REL-089-CODE-R0.md
[OK] file exists: reviews/Review Rel 090 Code M3 -> docs\reviews\review-REL-090-CODE-M3.md
[OK] file exists: reviews/Review Rel 090 Design R0 -> docs\reviews\review-REL-090-DESIGN-R0.md
[OK] file exists: reviews/Review Rel 090 Release M3 -> docs\reviews\review-REL-090-RELEASE-M3.md
[OK] file exists: reviews/Review Rel 090 Release R0 -> docs\reviews\review-REL-090-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 091 Release R0 -> docs\reviews\review-REL-091-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 092 Release R0 -> docs\reviews\review-REL-092-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 093 M3 R0 -> docs\reviews\review-REL-093-M3-R0.md
[OK] file exists: reviews/Review Rel 094 M1 R0 -> docs\reviews\review-REL-094-M1-R0.md
[OK] file exists: reviews/Review Rel 094 M1R R0 -> docs\reviews\review-REL-094-M1R-R0.md
[OK] file exists: reviews/Review Rel 094 M3 Code R0 -> docs\reviews\review-REL-094-M3-CODE-R0.md
[OK] file exists: reviews/Review Rel 094 M3 Release R0 -> docs\reviews\review-REL-094-M3-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 094 M4Docs R0 -> docs\reviews\review-REL-094-M4DOCS-R0.md
[OK] file exists: reviews/Review Rel 094 M5 R0 -> docs\reviews\review-REL-094-M5-R0.md
[OK] file exists: reviews/Review Rel 094 M5B R0 -> docs\reviews\review-REL-094-M5B-R0.md
[OK] file exists: reviews/Review Rel 094 M8 R0 -> docs\reviews\review-REL-094-M8-R0.md
[OK] file exists: reviews/Review Rel 095 B2 R1 -> docs\reviews\review-REL-095-B2-R1.md
[OK] file exists: reviews/Review Rel 095 Code R0 -> docs\reviews\review-REL-095-CODE-R0.md
[OK] file exists: reviews/Review Rel 095 M1 R0 -> docs\reviews\review-REL-095-M1-R0.md
[OK] file exists: reviews/Review Rel 095 M4 R4 -> docs\reviews\review-REL-095-M4-R4.md
[OK] file exists: reviews/Review Rel 095 M5 R5 -> docs\reviews\review-REL-095-M5-R5.md
[OK] file exists: reviews/Review Rel 095 Release R0 -> docs\reviews\review-REL-095-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 096 Release R0 -> docs\reviews\review-REL-096-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 096 Release R1 -> docs\reviews\review-REL-096-RELEASE-R1.md
[OK] file exists: reviews/Review Rel 098 M3A Code R0 -> docs\reviews\review-REL-098-M3a-CODE-R0.md
[OK] file exists: reviews/Review Rel 098 M3B Rel R0 -> docs\reviews\review-REL-098-M3b-REL-R0.md
[OK] file exists: reviews/Review Rel 099 Code R0 -> docs\reviews\review-REL-099-CODE-R0.md
[OK] file exists: reviews/Review Rel 099 Rel R0 -> docs\reviews\review-REL-099-REL-R0.md
[OK] file exists: reviews/Review Rel 100 Code R0 -> docs\reviews\review-REL-100-CODE-R0.md
[OK] file exists: reviews/Review Rel 100 Rel R0 -> docs\reviews\review-REL-100-REL-R0.md
[OK] file exists: reviews/Review Rel 101 M3A Code R0 -> docs\reviews\review-REL-101-M3a-CODE-R0.md
[OK] file exists: reviews/Review Rel 101 M3B Release R0 -> docs\reviews\review-REL-101-M3b-RELEASE-R0.md
[OK] file exists: reviews/Review Rel 102 C4 Code R0 -> docs\reviews\review-REL-102-C4-CODE-R0.md
[OK] file exists: reviews/Review Rel 102 M3 Code R0 -> docs\reviews\review-REL-102-M3-CODE-R0.md
[OK] file exists: reviews/Review Rel 102 M3 Release R0 -> docs\reviews\review-REL-102-M3-RELEASE-R0.md
[OK] file exists: reviews/Supplement Fix 445 Design R10 Calibration -> docs\reviews\supplement-FIX-445-DESIGN-R10-calibration.md
[OK] file exists: reviews/Supplement Fix 445 Design R10 Evidence -> docs\reviews\supplement-FIX-445-DESIGN-R10-evidence.md
[OK] file exists: reviews/Supplement Fix 445 Design R12 Evidence -> docs\reviews\supplement-FIX-445-DESIGN-R12-evidence.md
[OK] file exists: reviews/Supplement Fix 445 Design R8 Integrity -> docs\reviews\supplement-FIX-445-DESIGN-R8-integrity.md
[OK] file exists: reviews/Supplement Fix 445 Design R9 Protocol -> docs\reviews\supplement-FIX-445-DESIGN-R9-protocol.md
[OK] file exists: verification/Loop Migration Fullchain 0.90.0 -> docs\verification\loop-migration-fullchain-0.90.0.md
[OK] file exists: verification/Loop Shadow Derivation 0.90.0 -> docs\verification\loop-shadow-derivation-0.90.0.md
[OK] file exists: closure/Protocol -> benchmarks\closure\protocol.md
[OK] file exists: .Gitignore (web/.gitignore) -> web\.gitignore
[OK] file exists: Index (web/index.html) -> web\index.html
[OK] file exists: Package (web/package.json) -> web\package.json
[OK] file exists: Package Lock -> web\package-lock.json
[OK] file exists: public/Favicon -> web\public\favicon.svg
[OK] file exists: Server -> web\server.py
[OK] file exists: Vite.Config -> web\vite.config.js
[OK] file exists: src/Main -> web\src\main.jsx
[OK] file exists: src/Styles -> web\src\styles.css
[OK] file exists: Canonical artifact: governance-pack-registry -> skills\software-project-governance\core\governance-packs.json
[OK] file exists: Canonical artifact: capability-registry -> skills\software-project-governance\core\capability-registry.json
[OK] file exists: Canonical artifact: lifecycle-registry -> skills\software-project-governance\core\lifecycle-registry.json
[OK] file exists: Canonical artifact: loop-engineering-registry -> skills\software-project-governance\core\loop-engineering-registry.json
[OK] file exists: Canonical artifact: loop-runtime-claim-policy -> skills\software-project-governance\core\loop-runtime-claim-allowlist.json
[OK] file exists: Canonical artifact: loop-runtime-claim-authority -> skills\software-project-governance\core\loop-runtime-claim-authority.json
[OK] file exists: Canonical artifact: loop-runtime-identity-attestor -> skills\software-project-governance\infra\checks\loop_runtime_claim_attestation.py
[OK] file exists: Canonical artifact: architecture-health-budget -> skills\software-project-governance\core\architecture-health.json
[OK] file exists: Canonical artifact: release-ledger-schema -> skills\software-project-governance\core\release-ledger.schema.json
[OK] file exists: Canonical artifact: version-projections -> skills\software-project-governance\core\version-projections.json
[OK] file exists: Canonical artifact: dsh-host-contract -> adapters\dsh\host-contract.json
[OK] file exists: Canonical artifact: dsh-host-facts-baseline -> adapters\dsh\fixtures\host-facts-0.1.5-rc.1.json
[OK] snippet found: README.md :: 让 coding agent 帮你看护项目质量
[OK] snippet found: README.md :: ## 安装
[OK] snippet found: README.md :: ## 5 分钟开始
[OK] snippet found: README.md :: ## 内部文档
[OK] snippet found: project\workflows\software-project-governance\research\agent-integration-models.md :: ## 调研目标
[OK] snippet found: project\workflows\software-project-governance\research\agent-integration-models.md :: ## Claude Code
[OK] snippet found: project\workflows\software-project-governance\research\agent-integration-models.md :: ## 通用集成模式对比
[OK] snippet found: project\workflows\software-project-governance\research\default-product-shape.md :: ## 方案摘要
[OK] snippet found: project\workflows\software-project-governance\research\default-product-shape.md :: ## 分层设计
[OK] snippet found: project\workflows\software-project-governance\research\default-product-shape.md :: ## 默认接入矩阵
[OK] snippet found: project\workflows\software-project-governance\research\external-capability-minimum-validation.md :: ## 目标
[OK] snippet found: project\workflows\software-project-governance\research\external-capability-minimum-validation.md :: ## 为什么先选 external runner / shared command
[OK] snippet found: project\workflows\software-project-governance\research\external-capability-minimum-validation.md :: ## 最小验证范围
[OK] snippet found: project\workflows\software-project-governance\research\external-capability-minimum-validation.md :: ## 命令约定草案
[OK] snippet found: project\workflows\software-project-governance\research\external-capability-minimum-validation.md :: software-project-governance.run
[OK] snippet found: project\workflows\software-project-governance\research\domestic-agent-cli-compatibility.md :: ## 目标
[OK] snippet found: project\workflows\software-project-governance\research\domestic-agent-cli-compatibility.md :: ## 兼容抽象
[OK] snippet found: project\workflows\software-project-governance\research\domestic-agent-cli-compatibility.md :: ## 默认接入顺序
[OK] snippet found: project\workflows\software-project-governance\research\domestic-agent-cli-compatibility.md :: ## 能力检查清单
[OK] snippet found: project\workflows\software-project-governance\research\repo-local-termination-note.md :: ## 终止对象
[OK] snippet found: project\workflows\software-project-governance\research\repo-local-termination-note.md :: ## 终止原因
[OK] snippet found: project\workflows\software-project-governance\research\repo-local-termination-note.md :: ## 降级后的资产定位
[OK] snippet found: project\workflows\software-project-governance\research\repo-local-termination-note.md :: ## 新主线如何接管
[OK] snippet found: project\workflows\software-project-governance\examples\current-project-sample.md :: 已迁移
[OK] snippet found: skills\software-project-governance\core\protocol\workflow-schema.md :: ## 通用对象模型
[OK] snippet found: skills\software-project-governance\core\protocol\workflow-schema.md :: ### 1. Workflow
[OK] snippet found: skills\software-project-governance\core\protocol\workflow-schema.md :: ### 3. Gate
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: ## 最小承载单元
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: ## 三层承载模型
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: ## Skill / Plugin 行为描述要素
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: ## 默认接入要求
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: workflow 本体层 + agent 入口投影层 + 外部能力层
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: software-project-governance
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: stages
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: interaction-boundary
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: Agent 适配准入标准
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: 冲击场景
[OK] snippet found: skills\software-project-governance\core\protocol\plugin-contract.md :: SC-1
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ## 目标
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: software-project-governance.run
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ## 最小输入
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ## 最小输出
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ## write-back targets
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ## replacement boundary
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ### 协议层（必读）
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: ### 当前阶段子工作流（按 stage 参数加载）
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: interaction-boundary
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: Validation Matrix
[OK] snippet found: skills\software-project-governance\core\protocol\external-command-contract.md :: 失败与阻断语义
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: ## 目标
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: software-project-governance.headless
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: ## 输入映射
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: ## execution mode
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: dry-run
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: ## 最小返回样例
[OK] snippet found: skills\software-project-governance\core\protocol\headless-runner-sample.md :: ### 当前阶段子工作流（按 stage 参数加载）
[OK] snippet found: skills\software-project-governance\core\manifest.md :: supported_agents
[OK] snippet found: skills\software-project-governance\core\manifest.md :: Claude
[OK] snippet found: skills\software-project-governance\core\manifest.md :: Codex
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Input Parameters 定义规范
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Execution Flow 定义规范
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Output Format 定义规范
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Error Codes 定义规范
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Self-Validation 定义规范
[OK] snippet found: skills\software-project-governance\core\protocol\command-schema.md :: ## Agent 执行纪律
[OK] snippet found: commands\governance-init.md :: ## 输入参数
[OK] snippet found: commands\governance-init.md :: ## 执行流程
[OK] snippet found: commands\governance-init.md :: ## 输出格式
[OK] snippet found: commands\governance-init.md :: ## 错误码
[OK] snippet found: commands\governance-init.md :: ## 自校验
[OK] snippet found: commands\governance-init.md :: INIT-ERR-001
[OK] snippet found: commands\governance-init.md :: INIT-ERR-002
[OK] snippet found: commands\governance-init.md :: INIT-ERR-003
[OK] snippet found: commands\governance-status.md :: ## 输入参数
[OK] snippet found: commands\governance-status.md :: ## 执行流程
[OK] snippet found: commands\governance-status.md :: ## 输出格式
[OK] snippet found: commands\governance-status.md :: ## 错误码
[OK] snippet found: commands\governance-status.md :: ## 自校验
[OK] snippet found: commands\governance-status.md :: permission_mode
[OK] snippet found: commands\governance-status.md :: 操作权限模式
[OK] snippet found: commands\governance-status.md :: STATUS-ERR-001
[OK] snippet found: commands\governance-gate.md :: ## 输入参数
[OK] snippet found: commands\governance-gate.md :: ## 执行流程
[OK] snippet found: commands\governance-gate.md :: ## 输出格式
[OK] snippet found: commands\governance-gate.md :: ## 错误码
[OK] snippet found: commands\governance-gate.md :: ## 自校验
[OK] snippet found: commands\governance-gate.md :: GATE-ERR-001
[OK] snippet found: commands\governance-gate.md :: GATE-ERR-002
[OK] snippet found: commands\governance-verify.md :: ## 输入参数
[OK] snippet found: commands\governance-verify.md :: ## 执行流程
[OK] snippet found: commands\governance-verify.md :: ## 输出格式
[OK] snippet found: commands\governance-verify.md :: ## 错误码
[OK] snippet found: commands\governance-verify.md :: ## 自校验
[OK] snippet found: commands\governance-verify.md :: VERIFY-ERR-001
[OK] snippet found: commands\governance-update.md :: ## 输入参数
[OK] snippet found: commands\governance-update.md :: ## 执行流程
[OK] snippet found: commands\governance-update.md :: ## 输出格式
[OK] snippet found: commands\governance-update.md :: ## 错误码
[OK] snippet found: commands\governance-update.md :: ## 自校验
[OK] snippet found: commands\governance-update.md :: UPDATE-ERR-001
[OK] snippet found: adapters\claude\README.md :: Tier 1
[OK] snippet found: adapters\claude\README.md :: ## Load
[OK] snippet found: adapters\claude\README.md :: ## Verify
[OK] snippet found: adapters\claude\README.md :: ## Boundary
[OK] snippet found: adapters\claude\README.md :: skills/software-project-governance/SKILL.md
[OK] snippet found: adapters\claude\README.md :: python adapters/claude/launch.py
[OK] snippet found: adapters\claude\README.md :: check-agent-adapters
[OK] snippet found: adapters\claude\README.md :: check-agent-adapters --runtime
[OK] snippet found: adapters\claude\adapter-manifest.json :: adapter_id
[OK] snippet found: adapters\claude\adapter-manifest.json :: workflow_id
[OK] snippet found: adapters\claude\adapter-manifest.json :: native_entry
[OK] snippet found: adapters\claude\adapter-manifest.json :: launcher
[OK] snippet found: adapters\claude\launch.py :: Claude Adapter Launcher
[OK] snippet found: adapters\claude\launch.py :: native_entry
[OK] snippet found: adapters\claude\launch.py :: read_order
[OK] snippet found: adapters\claude\launch.py :: validation
[OK] snippet found: adapters\codex\README.md :: Tier 1
[OK] snippet found: adapters\codex\README.md :: ## Load
[OK] snippet found: adapters\codex\README.md :: ## Verify
[OK] snippet found: adapters\codex\README.md :: ## Boundary
[OK] snippet found: adapters\codex\README.md :: skills/software-project-governance/SKILL.md
[OK] snippet found: adapters\codex\README.md :: .codex-plugin/plugin.json
[OK] snippet found: adapters\codex\README.md :: .agents/plugins/marketplace.json
[OK] snippet found: adapters\codex\README.md :: python adapters/codex/launch.py
[OK] snippet found: adapters\codex\README.md :: check-agent-adapters
[OK] snippet found: adapters\codex\README.md :: agent-runtime-e2e --agent codex
[OK] snippet found: adapters\codex\adapter-manifest.json :: adapter_id
[OK] snippet found: adapters\codex\adapter-manifest.json :: workflow_id
[OK] snippet found: adapters\codex\adapter-manifest.json :: launcher
[OK] snippet found: adapters\codex\launch.py :: Codex Adapter Launcher
[OK] snippet found: adapters\codex\launch.py :: read_order
[OK] snippet found: adapters\codex\launch.py :: validation
[OK] snippet found: adapters\gemini\README.md :: ## 兼容要求
[OK] snippet found: adapters\gemini\README.md :: ## Gemini 路线判断
[OK] snippet found: adapters\gemini\README.md :: ## 默认接入顺序
[OK] snippet found: adapters\gemini\README.md :: ## 国内 agent CLI 兼容抽象
[OK] snippet found: adapters\gemini\README.md :: ## 适配原则
[OK] snippet found: adapters\gemini\README.md :: ## 建议的最小验证顺序
[OK] snippet found: .claude-plugin\marketplace.json :: 0.98.0
[OK] snippet found: .claude-plugin\plugin.json :: 0.98.0
[OK] snippet found: .codex-plugin\plugin.json :: 0.98.0
[OK] snippet found: skills\software-project-governance\SKILL.md :: # 软件项目治理工作流入口
[OK] snippet found: skills\software-project-governance\SKILL.md :: 加载本 SKILL 后，你进入软件项目治理工作流
[OK] snippet found: skills\software-project-governance\SKILL.md :: 你是 Coordinator，不是单 agent 任务执行者
[OK] snippet found: skills\software-project-governance\SKILL.md :: Coordinator 接管用户交互
[OK] snippet found: skills\software-project-governance\SKILL.md :: Producer-Reviewer 分离
[OK] snippet found: skills\software-project-governance\SKILL.md :: references/behavior-protocol.md
[OK] snippet found: skills\software-project-governance\SKILL.md :: core/lifecycle.md
[OK] snippet found: skills\software-project-governance\SKILL.md :: core/stage-gates.md
[OK] snippet found: skills\software-project-governance\SKILL.md :: core/task-gate-model.md
[OK] snippet found: skills\software-project-governance\SKILL.md :: references/agent-communication-protocol.md
[OK] snippet found: skills\software-project-governance\SKILL.md :: 六层架构
[OK] snippet found: skills\software-project-governance\SKILL.md :: 适配层（平台投影）
[OK] snippet found: skills\software-project-governance\SKILL.md :: infra/verify_workflow.py
[OK] snippet found: skills\software-project-governance\SKILL.md :: infra/hooks/
[OK] snippet found: skills\software-project-governance\references\behavior-protocol.md :: 完成 Tier 时
[OK] snippet found: project\references\architecture.md :: # 六层架构设计
[OK] snippet found: project\references\architecture.md :: 适配层（Adapter）
[OK] snippet found: project\references\architecture.md :: 入口层
[OK] snippet found: project\references\architecture.md :: 业务智能层（Agent 库）
[OK] snippet found: project\references\architecture.md :: 能力层（SKILL 库）
[OK] snippet found: project\references\architecture.md :: 基础设施层
[OK] snippet found: project\references\architecture.md :: 核心层
[OK] snippet found: project\references\architecture.md :: 依赖方向（铁律）
[OK] snippet found: project\references\architecture.md :: 能力层 vs 业务智能层（关键区分）
[OK] snippet found: project\references\architecture.md :: 入口层 vs 适配层（关键区分）
[OK] snippet found: project\references\architecture.md :: 单向依赖，不可反向
[OK] snippet found: project\references\architecture.md :: 与协议层概念的对齐
[OK] snippet found: skills\software-project-governance\core\audit-framework.md :: Tier 完成时
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: # Agent 失败模式文档
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 1：协议跳过
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 2：选择性执行
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 3：幻觉式证据
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 4：虚假闭环
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 5：跨会话失忆
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 6：自我审计矛盾
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 7：虚假归因
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 失败模式 8：计划漂移
[OK] snippet found: skills\software-project-governance\references\agent-failure-modes.md :: ## 应急流程总览
[OK] snippet found: .agents\plugins\marketplace.json :: software-project-governance
[OK] snippet found: skills\software-project-governance\core\stage-gates.md :: Tier 审计检查点（Tier Audit Checkpoint）
[OK] snippet found: skills\software-project-governance\core\stage-gates.md :: TIER-<layer>-<tier>-AUDIT
[OK] snippet found: skills\software-project-governance\core\VERSIONING.md :: # 版本管理策略
[OK] snippet found: skills\software-project-governance\core\VERSIONING.md :: 语义化版本规则
[OK] snippet found: skills\software-project-governance\core\VERSIONING.md :: 版本升级触发条件
[OK] snippet found: project\CHANGELOG.md :: # 变更日志
[OK] snippet found: project\CHANGELOG.md :: ## [0.10.0]
[OK] snippet found: project\CHANGELOG.md :: ## [0.9.0]
[OK] snippet found: project\CHANGELOG.md :: ## [0.8.0]
[OK] snippet found: project\CHANGELOG.md :: ## [0.7.1]
[OK] snippet found: project\CHANGELOG.md :: ## [0.7.0]
[OK] snippet found: project\CHANGELOG.md :: ## [0.5.0]
[OK] snippet found: .zcode-plugin\plugin.json :: 0.98.0
[OK] snippet found: package.json :: 0.98.0
[OK] snippet found: skills\software-project-governance\core\manifest.json :: 0.98.0
[OK] architecture fact source synchronized
[STATIC] agent adapter claude: runtime-verified
[STATIC] agent adapter codex: runtime-verified
[STATIC] agent adapter gemini: runtime-verified
[STATIC] agent adapter opencode: runtime-verified
[STATIC] agent adapter dsh: runtime-verified
[STATIC] agent adapter pi: runtime-verified
[OK] agent adapter contracts synchronized

== Verification Result: PASSED ==

```


### Clean discovery and single-template evidence

```json
{
  "command": "python - (clean directory: copy shipped template, discover_compositions, check_dsh_preset_compat)",
  "start": "2026-10-16T23:56:12.460046+08:00",
  "end": "2026-10-16T23:56:13.289181+08:00",
  "exit": 0,
  "clean_discovery": [
    "agent-presets/governance/agent.cordis.yml.template"
  ],
  "verdict": "FAIL",
  "reason": "1 preset composition row(s) rejected by the plugin set resolved from $DSH_INSTALL_DIR (@deepseek-ai/cordis@4.0.5, @deepseek-ai/cordis-plugin-include@1.0.10, @deepseek-ai/cordis-plugin-loader@1.0.6, js-yaml@4.3.2)",
  "rows_enabled": 23,
  "rows_checked": 18,
  "coverage": {
    "rows_enabled": 23,
    "rows_verified": 18,
    "rows_unverified": 4,
    "unverified_reasons": {
      "NO_SCHEMA": 4
    },
    "unreadable_compositions": 0
  },
  "isolation": {
    "temp_home": "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/dsh102-baseline/spg-dsh-compat-home-167404be8f3f",
    "home_writes": 0,
    "mechanism": "subprocess DSH_HOME redirected to a freshly created empty temp directory, removed afterwards; `home_writes` is this run's entry count of THAT directory (empty by construction), so it proves zero writes to the isolated home — it is not a global no-write proof (module imports and a read-only <home-var>/<profiles-dir> probe still happen outside it). M7.7 (a) precedent, FEAT-015/016"
  },
  "install": {
    "status": "OK",
    "reason": "",
    "source": "$DSH_INSTALL_DIR",
    "plane": "$DSH_INSTALL_DIR",
    "node_modules": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules",
    "dsh_package": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh",
    "dsh_version": "0.2.0-rc.2",
    "cli_package": {
      "version": "0.2.0-rc.2",
      "path": "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh",
      "note": "informational only — the installed CLI package version does not decide a row's schema; the oracle packages below do"
    },
    "resolution_anchor": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
    "oracle_packages": {
      "@deepseek-ai/cordis": {
        "version": "4.0.5",
        "path": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis",
        "manifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\package.json",
        "resolvedPath": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js"
      },
      "@deepseek-ai/cordis-plugin-include": {
        "version": "1.0.10",
        "path": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-include",
        "manifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-include\\package.json",
        "resolvedPath": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-include\\lib\\index.js"
      },
      "@deepseek-ai/cordis-plugin-loader": {
        "version": "1.0.6",
        "path": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader",
        "manifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\package.json",
        "resolvedPath": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js"
      },
      "js-yaml": {
        "version": "4.3.2",
        "path": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\js-yaml",
        "manifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\js-yaml\\package.json",
        "resolvedPath": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\js-yaml\\index.js"
      }
    },
    "other_planes": [],
    "node": "C:\\Program Files\\nodejs\\node.EXE",
    "node_version": "v24.13.1",
    "probe_versions": {
      "yaml": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\js-yaml\\package.json",
      "include": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-include\\package.json",
      "loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\package.json",
      "cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\package.json"
    }
  },
  "issues": [
    "agent-presets/governance/agent.cordis.yml.template: row \"workflow-worker-thread\" (@deepseek-ai/dsh-workflow-worker-thread): cannot resolve from the installed harness (C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules): Error: Cannot find module '@deepseek-ai/dsh-workflow-worker-thread'"
  ],
  "impact": "CLI installed files read-only; fresh repo sandbox directory only; removed afterwards"
}
```


### Final resolution regression run

```text
["C:\\Python314\\python.exe", "-m", "pytest", "skills/software-project-governance/infra/tests/test_dsh_compat.py", "-q", "-k", "ResolutionContextTests"]
start=2026-10-16T23:56:13.290737+08:00
end=2026-10-16T23:56:15.833417+08:00
exit=0
.........                                                                [100%]
9 passed, 126 deselected in 1.97s

```
