# FEAT-113 S2 Code Review — R0 (2026-11-07)

- Reviewer: Code Reviewer subagent 9aca3600-0f07-4a85-a0d8-36d86c06ae65 (read-only)
- Subject: uncommitted working-tree diff — 2 NEW (dsh_walk.py 262 L, test_dsh_walk.py 373 L) + 3 modified (dsh_compat.py ±361, test_dsh_compat.py +158/−27, test_dsh_contract.py +4/−1 ratified deviation)
- Verdict: **APPROVED_WITH_NOTES** (1 LOW comment fix + 2 INFO)

## Six points — all PASS

1. PASS — §10.2 semantics preserved: ScanBudget/DEFAULT_SCAN_BUDGET/CompositionScanOverflow moved with identical docstrings/defaults; discover_compositions keeps (root, *, budget, report, clock), sorted-relative-posix return, same 7 counter keys; default budget resolved from dsh_compat's namespace (re-export dsh_compat.py:109-110) so mock.patch.object(dsh_compat, "DEFAULT_SCAN_BUDGET") still steers (pinned test_dsh_compat.py:4039-4058).
2. PASS — single declared generalization only: reparse fallback 0→0x400 (dsh_walk.py:133); Windows identical (real constant = 0x400); real POSIX stats never carry st_file_attributes so the flag can only fire for injected doubles.
3. PASS — skip tables stay in dsh_compat, injected as skip_predicate (dsh_compat.py:1630-1632); dsh_walk has zero _SKIP_/_fact/dsh_contract references outside docstrings — policy-free engine.
4. PASS — default face (root=None) walks contract discovery.roots with type-checked bounds (→ ContractMalformed, dsh_compat.py:1660-1680) + exclude_names disclosure; explicit --root/doctor keeps whole-root semantics (pinned test_an_explicit_root_keeps_whole_root_semantics); overflow → merged counters → NOT_RUN/SCAN_OVERFLOW unchanged (:2421-2440); DISCOVERY_EXCLUDE_NAMES/DISCOVERY_BOUNDS additive bindings pinned end-to-end.
5. PASS — regressions ①:3902 ②:3933 ③:3844+3987 ④:4022+4039 ⑤:3955+4060 unchanged; test_dsh_walk exactly 12 tests, all FakeFs/FakeClock; the −27 in test_dsh_compat.py is 100% docstring/comment reshape (zero assertion/code lines removed).
6. PASS — verify_workflow.py untouched; stdlib only; no template/agent-presets changes; no sandbox deletion; no ~/.dsh writes; no sleeps.

## Verbatim-transplant check (vs git show bf039bc)

Loop body + classes compared after normalizing only the declared seams (fs/os stat+scandir, skip_predicate, pattern source, reparse flag): **IDENTICAL** — remaining deltas are exactly the declared seams + the 0→0x400 fallback + comment wording. Zero semantic drift (check order, counters, overflow message format, visited-identity seeding, sorted return all line-for-line).

## Reviewer's independent gate run (default face, read-only)

dirs=5 (was 7242), entries=23 (was 13229), elapsed 6.1–7.9 ms (was ~3.1 s), bounded_out=false, single composition found (agent-presets/governance/agent.cordis.yml.template) — matches §5.4's pre-S7 expectation and the claimed numbers.

## Ratified deviation judged on merits

test_dsh_contract.py:2341-2344: correct and minimal — dsh_compat's module-level `from dsh_walk import …` makes the sibling copy structurally required; comment accurate; no assertion weakened.

## Findings (dispositions)

1. LOW — dsh_walk.py:105-108 comment overclaims "patching either module's name steers discover_compositions" (dsh_walk.DEFAULT_SCAN_BUDGET does NOT — dsh_compat resolves its own default). → R1 reword: dsh_compat's re-export steers discover_compositions; dsh_walk's default steers direct walk() calls. Reviewer pre-approved landing with this slice.
2. INFO — real LOC: dsh_walk.py 262 / test_dsh_walk.py 373 (declared 222/315); recorded in slice note and closure evidence.
3. INFO — red-first (ModuleNotFoundError) not independently verifiable from the working tree; module-scope import structure consistent with the claim; Developer's captured output recorded in the R1 report.

## Acceptance basis

Developer: 518 tests OK (six modules) + 182 more (doctor/adapter/native_bridge — family 700 green) + boundary PASS + compat PASSED 2.4s. Coordinator independent re-run: full family 700 tests OK 226.3s + boundary PASS issues=0 + compat PASSED 2.5s.
