# FIX-455 — Windows ledger atomic replacement forensics

Date: 2026-10-19, Asia/Shanghai. All recorded experiment times below are UTC. This is a diagnostic investigation, not a production fix or independent review. Production writer, historical logs, real governance data, index and refs were not changed.

**Result: the two historical failing command runs remain root-cause UNKNOWN.** They contain three `os.replace()` WinError 5 exceptions. A bounded isolated sequence independently reproduced WinError 5 at write 28 and stopped immediately. Controlled target handles and readonly attributes can each cause the same error, so the number 5 alone does not identify the historical cause. No antivirus, security-policy or particular-process attribution is supported.

## Evidence vocabulary and scope

- **SOURCE**: directly read from current production code or immutable historical command/log files.
- **OBSERVED**: measured by this investigation in repository-local disposable fixtures; controls do not prove the cause of a historical failure.
- **HYPOTHESIS**: possible explanation not directly established at the historical failing instant.
- **NOT_RUN**: deliberately untested; no acceptance or repair claim.

All experiment roots were resolved and checked under `.codex-sandbox/FIX-455/forensics` before creation. HOME, USERPROFILE, APPDATA, LOCALAPPDATA, DSH_HOME, TEMP, TMP and cache roots were redirected below that directory. Existing replay-venv was reused, npm/DSH shims removed from PATH, and real DSH/session-root overrides removed. There was no network access, dependency installation, user-profile access, system-security configuration change, real ledger migration or cleanup. Temporary readonly changes applied only to newly created forensic files and were reversed; no DACL was changed.

Raw evidence is preserved under `.codex-sandbox/FIX-455/forensics/`: `input-manifest.json`, `probe.py`, exact copied `atomic_write.source.txt`, `observations.json`, `probe.log`, `recovery_control.py`, `recovery-observations.json`, `recovery.log`, and `command-audit.json`. Case files and the source-locked leftover temp were retained for inspection. The driver extracts `_atomic_write` from the real source via AST; only its local `os.replace` binding is wrapped to observe/control operations. The transaction case calls the actual `LedgerWriter` against its isolated governance directory.

## Historical failures — SOURCE, not rerun

| Original run | Exact UTC interval / process exit | Failing cases |
|---|---|---|
| `.codex-sandbox/FIX-449/review-r1/regression.json` + `.log` | 2026-10-18 12:15:35.451497–12:15:38.082636; exit 1 | First 19-test suite: `test_fix449_versions_follow_authority_across_bumps`, inner subtest version 0.99.0; and `test_rebuild_wall_budget_on_31_task_scale`. Two errors, 1.901s. |
| `.codex-sandbox/FIX-449/review-r1/regression-retry.json` + `.log` | 2026-10-18 12:16:18.778484–12:16:24.164705; exit 1 | Outer authority 0.98.0 suite passed 19 tests (2.090s), then the next suite failed `test_rebuild_wall_budget_on_31_task_scale` (19 tests, one error, 2.741s). The outer loop is ordered 0.98.0/0.99.0/1.0.0, so this second suite is the 0.99.0 iteration. |

All three exceptions originate in `_atomic_write()` at the historical `authority_ledger.py:337`, from a same-directory `snapshot.json.tmp-*` to `snapshot.json`:

| Run | Fixture root below `.codex-sandbox/FIX-449/review-r1/` | Temp suffix | Append path before replacement |
|---|---|---|---|
| First | `tmp/fix449-bump-f1cc79165629/.governance/authority-ledger/` | `4801b31b` | migrate → `_register_all` → `risk_recorded` → transact → snapshot |
| First | `tmp/feat093-perf-e5d93fb0f254/.governance/authority-ledger/` | `fb7d1df0` | Same risk registration path |
| Retry | `tmp-retry/feat093-perf-5c603aa757f8/.governance/authority-ledger/` | `78b157dc` | migrate → `_register_all` → `record_task` → transact → snapshot |

Historical logs provide no contemporaneous file attributes, ACL, open-handle inventory or failed-temp bytes. All six named original source/target paths are now absent (**OBSERVED** in `input-manifest.json`); none was recreated or modified. `_governance_temp_dir()` closes each fixture with `shutil.rmtree(ignore_errors=True)` (**SOURCE**), but this investigation cannot establish when or which actor removed each original path.

Original input bindings:

| File | SHA-256 |
|---|---|
| `authority_ledger.py` | `4d3acc44e636b03855766ee656f7f60d13f9afad5b403440b15215447e3b8762` |
| First regression log | `679e31dfca67656b075747e3e699163590032f78fc9eaad5cc86cafdea0361c5` |
| First regression metadata JSON | `87099611db25026ffb755d3de211186ed1c72c766c578293a36add0858cbf424` |
| Retry regression log | `a6649674ccfbd4b9449cf0981bc323a58bd7d9c2b8c9ad61b8eb31ea7ac7d2a3` |
| Retry metadata JSON | `69e472f641cd21a226cea315b65f2dd7ce25e67ef877d7e7d24306d234fad04d` |

## Writer ordering and read-side recovery — SOURCE + OBSERVED

`authority_ledger._atomic_write` writes a unique same-directory temp, flushes/fsyncs it, leaves the `with open` block, then calls `os.replace`. Its own writing handle is closed at replacement. Finally it attempts to unlink a remaining temp, suppressing only cleanup `OSError`; the original replacement exception propagates. It neither unlinks the old destination first nor truncates it in place.

`LedgerWriter.transact` validates the batch, appends and fsyncs the event log, advances its in-memory events/integrity/state, then refreshes the snapshot. Thus a snapshot failure can occur **after the authoritative event commit**. `migrate` handles `LedgerError`, not this `PermissionError`; the historical traceback is not evidence that no events were committed. This does not make the event file and snapshot one all-or-nothing transaction.

The controlled real transaction reproduced that exact boundary:

| State | Observed result |
|---|---|
| First isolated task | Event seq=1; snapshot seq=1. |
| Second task with destination read handle held | `PermissionError` WinError 5 propagates; snapshot bytes remain identical to seq=1; no temp remains. |
| Immediately afterward | Event chain valid, disk and memory seq=2, two task identities; snapshot still seq=1, `stale=true`. |
| New `LedgerWriter` and `status()` | Both reconstruct truth from events; two tasks and valid seq=2 are visible. `status()` reports stale cache separately. Read-only load does **not** rewrite the snapshot. |
| Repeat same task registration after releasing handle | `already_registered`; no extra event, but snapshot still stale. Idempotent registration is not automatic cache repair. |
| Explicit isolated `_write_snapshot()` | Snapshot seq=2, `stale=false`; event count remains two. This is a scratch-only cache recovery demonstration, not a real migration or public-CLI rebuild test. |

`LedgerWriter.__init__` uses `_read_events_raw` + `fold_state`; `status()` also folds events and reads snapshot only to report its freshness. `rebuild_projection` constructs a writer from events, verifies integrity and compares hot-zone state; its write arm refreshes the cache and records audit events. Therefore stale snapshot is not synonymous with damaged events. A torn/invalid event chain is a different condition and must still fail closed. The explicit public `rebuild --write` path was **NOT_RUN** here because it also changes audit state; no claim is made that every unrelated snapshot consumer has been runtime-audited.

## Bounded experiment matrix — OBSERVED

Single matrix command: 2026-10-19T11:15:44.309861–11:15:44.771965 UTC, process exit 0. Expected operation failures are recorded as data; exit 0 means the forensic driver completed, not that every replace succeeded. Runtime: existing QA CPython 3.14.3 on win32. Order is the table order, then the transaction above. There was no ledger suite run or repeated search for a green result.

| Order / condition | Replace result | Attributes / effective DELETE-open probe | Original data and temp state |
|---|---|---|---|
| 1. Clean closed target | Success | Target attributes 32; DELETE open allowed | New complete bytes, no temp. |
| 2. Ordinary Python target reader held | WinError 5 / errno 13 | Attributes 32; DELETE open reports WinError 32 while reader held | Old target unchanged; temp removed. Closing reader permits the one planned recovery control. |
| 3. Win32 target reader, share READ+WRITE (3), same process | WinError 5 | Attributes 32; DELETE open WinError 32 | Old unchanged; no temp. One recovery after closing handle succeeds. |
| 4. Win32 target reader, share READ+WRITE+DELETE (7) | **WinError 5** | Attributes 32; DELETE open **allowed** | Old unchanged; no temp. Recovery after closing handle succeeds. Sharing DELETE alone was insufficient for this tested replacement operation. |
| 5. Separate child process holds target, share 3 | WinError 5 | Attributes 32; DELETE open WinError 32 | Ready handshake guarantees overlap; old unchanged, no temp; child closes/exits 0, planned recovery succeeds. |
| 6. Target readonly, no deliberately held reader | WinError 5 | Attributes **1**; DELETE open allowed | Old unchanged; no temp; clearing only this scratch attribute permits the one planned recovery. |
| 7. Source temp held without delete sharing immediately before replace | **WinError 32** | Source DELETE open WinError 32; destination ordinary | Old target unchanged; finally-unlink also cannot remove held temp and suppresses that cleanup failure. Original WinError 32 propagates; complete new-data temp remains. |
| 8. Sequential closed-handle writer, upper bound 64; each success read/parsed and reader closed | **27 successes, failure at 28; stop** | Post-failure target attributes 32, readable, DELETE open allowed | Target remains generation 26; attempted generation 27 did not replace it; helper removed its failed temp. This is a natural failure without a deliberate test holder, not proof that no outside/short-lived holder existed. |
| 9. Two writers, exactly one write each, barrier after temp-close/fsync | Both succeeded in this one trial | No deliberate readers | Final file is one complete writer payload; no temp. This proves neither transaction serialization nor the absence of concurrency failures elsewhere. |

File evidence uses attributes and actual bytes/hashes, plus a `CreateFileW(..., DELETE, share=7)` success/error probe. This is an effective operation observation, not a complete ACL audit. No ACL denial was injected; no historical ACL or security policy conclusion follows. The source control distinguishes a source sharing failure (32) from several destination failures (5), while target attributes distinguish the deliberate readonly case from normal-attribute handle cases.

The share-7 counterexample and readonly control specifically forbid reducing WinError 5 to “permanent permissions” or claiming that adding `FILE_SHARE_DELETE` has been validated as a fix. Current source has a brief snapshot read in `status()`; overlapping readers are a **HYPOTHESIS** for the historical runs, not a discovered original holder. Foreign-process locks, filesystem/filter activity and transient access conditions remain unassigned possibilities, not accusations.

### Three-operation supplemental recovery control

2026-10-19T11:17:36.696381–11:17:36.775107 UTC, exit 0; exactly three explicit `os.replace` calls:

1. The original sequential failure source was already deleted by the helper. Before any new attempt, the surviving target is read and its attributes/bytes/hash recorded. A **new source containing the known attempted generation-27 payload** is created; one later replace succeeds. This uses a reconstructed payload, not the original source inode or an immediate retry. The original failure observations remain immutable. It demonstrates later recoverability only.
2. With a deliberate target reader still held, one repeat fails WinError 5; both source and target bytes remain unchanged.
3. With the scratch target readonly bit still set, one repeat also fails WinError 5; both byte streams remain unchanged. The scratch attribute is restored after recording.

There is no retry-until-success loop. The later success does not retroactively prove the historical/natural failures were transient, identify their cause, or validate retry as a production repair. Actual before/after byte hex, attributes and exceptions are in `recovery-observations.json`.

## Minimal candidate changes — proposals, NOT_RUN

No production implementation is authorized by this report. The next ticket needs Coordinator file locks and independent review.

1. **First candidate: expose the real commit boundary and preserve failure evidence.** Confine work to `authority_ledger.py`'s atomic-write helper and snapshot/transaction error boundary. Keep original exceptions visible and distinguish “events committed; snapshot refresh failed” from validation/append rejection. Attach structured phase/path/winerror, committed seq/hash and cleanup outcome without rereading or deleting unrelated files. Do not turn cache failure into silent success or replay the whole transaction. Tests should inject replace/cleanup failures, verify untouched old bytes, valid committed event chain, stale cache, surfaced cause and safe explicit cache recovery. This is justified by observed ambiguity and partial-commit behavior, irrespective of the unidentified historical holder.
2. **Optional mitigation candidate, requiring separate approval:** only after evidence capture, evaluate a small explicit Windows replace retry budget inside the helper, retaining the same closed/fsynced temp. Never retry the whole event append, never unlink/truncate the old target, never retry indefinitely, and preserve the last error if the budget is exhausted. Normal attributes or a successful DELETE probe cannot conclusively classify WinError 5 (share-7 control proves that). Readonly/real-denial controls must remain failures and attempts must be reported. This is a mitigation hypothesis, not an established root-cause fix; this investigation did not validate any retry schedule.
3. **Reader change only if a real overlapping reader is captured:** separately assess short-lived handle scope/coordination in the exact reader. Changing share flags or replacing `os.replace` with another Windows API is **NOT_RUN** and unsupported as a fix by this evidence. Do not introduce a broad platform or security-policy workaround.

Likely product/test scope for a later approved fix: `skills/software-project-governance/infra/authority_ledger.py` plus a narrowly scoped authority-ledger atomic-I/O test file (or the existing ledger classes in `infra/tests/test_verify_workflow.py`). Only if a specific reader is causally demonstrated should its owning file be added. New tests should preserve old success behavior, bound every recovery attempt, distinguish source/target blockage and readonly cases, and ensure event truth remains recoverable without claiming the cache write succeeded. No cache deletion, ledger migration, automatic user-profile repair or system ACL changes are proposed.

Missing historical evidence: source/destination attributes and bytes at failure, effective access, handle/share owner at the failing instant, and relevant concurrent operation ordering. Their absence is the reason the historical cause stays UNKNOWN, not a reason to invent a system-level explanation.

## Verification and command audit

Only this diagnostic and authorized forensic scratch were written. No production code/test was changed. Default static verification, cross references and manifest results are recorded below; no ordinary full ledger suite was run. Command argv/UTC/exit/impact include the controlled child process. Source and old-log hashes are checked again after the investigation.

```json
[
  {
    "id": "FIX455-MATRIX",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\probe.py"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:15:44.309861+00:00",
    "end_utc": "2026-10-19T11:15:44.771965+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\probe.log",
    "environment": {
      "HOME": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\home",
      "USERPROFILE": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\userprofile",
      "APPDATA": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\appdata",
      "LOCALAPPDATA": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\localappdata",
      "DSH_HOME": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\dsh_home",
      "TMP": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\tmp",
      "TEMP": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\temp",
      "XDG_CACHE_HOME": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\xdg_cache_home",
      "PIP_CACHE_DIR": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\pip_cache_dir",
      "UV_CACHE_DIR": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\uv_cache_dir",
      "NPM_CONFIG_CACHE": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\environment\\npm_config_cache"
    },
    "impact": {
      "read": [
        "authority_ledger.py and its local imports",
        "old FIX449 logs/metadata",
        "existing QA venv"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "DSH_started": false,
      "network": false
    }
  },
  {
    "id": "FIX455-RECOVERY-CONTROL",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\recovery_control.py"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:17:36.696381+00:00",
    "end_utc": "2026-10-19T11:17:36.775107+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\recovery.log",
    "impact": {
      "read": [
        "preserved scratch observations and case files",
        "existing QA venv"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "os_replace_attempts": 3,
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "DSH_started": false,
      "network": false
    }
  },
  {
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\probe.py",
      "--hold",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\destination-child-no-delete\\snapshot.json",
      "3"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:15:44.445585+00:00",
    "end_utc": "2026-10-19T11:15:44.537439+00:00",
    "exit": 0,
    "impact": "hold/read/release only this scratch destination",
    "ready": "{\"ready\": true, \"pid\": 23124}",
    "stdout": "",
    "stderr": "",
    "id": "FIX455-CHILD-HOLDER"
  },
  {
    "id": "FIX455-INPUTS-UNCHANGED",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "-c",
      "import hashlib,json;from pathlib import Path;r=Path.cwd();m=json.loads((r/'.codex-sandbox/FIX-455/forensics/input-manifest.json').read_text(encoding='utf-8'));assert all(hashlib.sha256((r/p).read_bytes()).hexdigest()==v['sha256'] for p,v in m.items());print('Production writer and four historical log/metadata files unchanged')"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:19:34.089884+00:00",
    "end_utc": "2026-10-19T11:19:34.153733+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\FIX455-INPUTS-UNCHANGED.log",
    "impact": {
      "read": [
        "repository source/diagnostic and historical evidence"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "network": false
    }
  },
  {
    "id": "FIX455-VERIFY",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "skills/software-project-governance/infra/verify_workflow.py"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:19:34.155293+00:00",
    "end_utc": "2026-10-19T11:19:35.993040+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\FIX455-VERIFY.log",
    "impact": {
      "read": [
        "repository source/diagnostic and historical evidence"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "network": false
    }
  },
  {
    "id": "FIX455-CROSS",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "skills/software-project-governance/infra/verify_workflow.py",
      "check-cross-references"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:19:35.994434+00:00",
    "end_utc": "2026-10-19T11:19:36.572759+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\FIX455-CROSS.log",
    "impact": {
      "read": [
        "repository source/diagnostic and historical evidence"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "network": false
    }
  },
  {
    "id": "FIX455-MANIFEST",
    "argv": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\ci-integration-20261018\\replay-venv\\Scripts\\python.exe",
      "-B",
      "-X",
      "utf8",
      "skills/software-project-governance/infra/verify_workflow.py",
      "check-manifest-consistency"
    ],
    "cwd": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "start_utc": "2026-10-19T11:19:36.573940+00:00",
    "end_utc": "2026-10-19T11:19:37.114385+00:00",
    "exit": 0,
    "log": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics\\FIX455-MANIFEST.log",
    "impact": {
      "read": [
        "repository source/diagnostic and historical evidence"
      ],
      "write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.codex-sandbox\\FIX-455\\forensics"
      ],
      "real_HOME_access": false,
      "real_governance_mutation": false,
      "network": false
    }
  }
]
```
