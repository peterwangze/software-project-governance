# FIX-484 Code Review — R1 delta (2026-11-07)

- Reviewer: Code Reviewer subagent 136aaff5-64d9-4ee6-8037-957e15d2f884 (delta scope; read-only)
- Delta base: R0 report (docs/reviews/review-FIX-484-CODE-R0.md), findings 1–3
- Verdict: **APPROVED** — no new issues; findings 1–3 all landed and correctly implemented

## Finding 1 deviation (ContractMalformed vs ValueError) — technical adjudication

- (a) Confirmed — `_contract_failure_report` (dsh_compat.py:587-605) classifies via `_contract_failure_types()` accessor tuple `(ContractUnreadable, ContractMalformed, ContractSchemaUnknown)`; `:600 isinstance(exc, rest)` (the latter two) yields FAIL; a literal ValueError falls to NOT_RUN. The isinstance targets the accessor's own classes, so raising `dsh_contract.ContractMalformed` itself (not a namesake) is required — the code does exactly that (:1496/:1500). Coordinator's acceptance ruling is technically sound: semantics = §2.5.1 "contract is there but wrong" → FAIL.
- (b) No import cycle/timing problem — dsh_contract.py imports only json/pathlib/typing (:47-49); :1492 is a lazy function-level import, same pattern as `_contract_failure_types` (:578); at runtime `_fact` has already resolved through the accessor (module in sys.modules). No new failure mode (accessor missing → ImportError → existing None branch → NOT_RUN, unchanged from pre-R0).
- (c) Confirmed — `test_the_preset_check_maps_a_bad_glob_to_fail_not_not_run` (test_dsh_compat.py:4156-4169) asserts on the check face: verdict=="FAIL", issues non-empty, reason contains ContractMalformed + the offending pattern — not a raise-only test. Supported by 7 illegal forms (incl. ""/"**"/"**/") each subTest-asserted on the message (:4126-4138); both legal forms' translation + depth-0 file hit pinned (:4140-4154).

Validator branch-by-branch: all 7 illegal forms hit a rejection branch; non-strings rejected via isinstance; both legal forms pass — no gap.

## Findings 2–3

- Finding 2 ✓: counters init includes `max_depth_hit` (:1563-1565), `finish` writes it (:1572); success and overflow faces share the same 7 keys; docstring lists it.
- Finding 3 ✓: test:4078-4102 pins both directions — under max_depth=1 a depth-1 file is matched with no overflow and bounded_out/max_depth_hit both False; after adding a depth-2 directory it overflows with max_depth_hit True.

## Extra tests (Developer-initiated)

Both genuine: disclosure-line test (:3951-3977) asserts details text + counters ≥1 + dirs==2 (following the junction would make dirs 3 — catches regressions); glob-validation class asserts behavior, not trivia.

## Scope purity

Cumulative diff still exactly two files (264+345, 594+/15−); no third file under infra/.

## Acceptance basis (Coordinator independent re-run, final bytes)

- `python -m unittest test_dsh_compat`: Ran 161 tests, 70.2s, OK
- `verify_workflow check-dsh-boundary --json`: verdict=PASS, issues=0
- `verify_workflow check-dsh-preset-compat`: PASSED — 1 composition, 19/23 verified, 4 NO_SCHEMA disclosed
- Developer full run on final bytes: test_dsh_compat 161 OK 60.8s; test_dsh_doctor 92 OK; test_dsh_boundary 136 OK; both gates green

## Disposition

R1 = APPROVED. Commit gate cleared (Coordinator). Known residual (unchanged, disclosed): repo-root scan 3–9s vs the 30s budget on slow machines may surface as SCAN_OVERFLOW → NOT_RUN (safe, never PASS); budget injectable; S2 (FEAT-113) narrows default roots.
