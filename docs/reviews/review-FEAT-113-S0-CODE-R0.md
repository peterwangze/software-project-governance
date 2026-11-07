# FEAT-113 S0 Code Review — R0 (2026-11-07)

- Reviewer: Code Reviewer subagent 75704571-b262-47e4-b40f-aac58322a79f (read-only)
- Subject: uncommitted working-tree diff, 6 slice files (host-contract.json +134/−3 · dsh_contract.py · dsh_compat.py · test_dsh_contract.py · test_dsh_compat.py +107/−0 · lib/index.js +1/−1); numstat on dsh_contract/dsh_compat/test_dsh_contract varies with CRLF renormalization (−11→−1 class) — content-level findings below are line-verified on the actual bytes
- Verdict: **APPROVED_WITH_NOTES** (1 minor + 3 nits, no blocker/major)

## Six verification points — all PASS

1. ADDITIVE ONLY — PASS. JSON: 7 new groups verbatim per §8.2.1 + §6.2.2.1 (persona_prefix = exactly the 11 table fields, values match incl. separator/trailing/CRLF/trim); schema 1→2; host.rows (all 29 entries) and own.preset.template retained in JSON AND in REQUIRED_PATHS; sidecar deprecations.entries = exactly {host.rows, own.preset.template}×{deprecated_in:2}; is_deprecated (dsh_contract.py:555+) reads only the sidecar, no code-side copy. All deletions are pure re-anchors: JSON `]`→`,` after composition_globs + write_policy comma; py version tuple; dsh_compat `value=tuple(value)` → order-preserving filter (identical output for the 4 packages); tests −6 = assertion updates only, zero tests removed.
2. PASS — SUPPORTED_SCHEMA_VERSIONS=(2,) (dsh_contract.py:94-97); schema 1 → ContractSchemaUnknown, pinned incl. message "schema_version 1"/"(supported: 2)".
3. PASS — exactly the 4 bindings (dsh_compat.py:414-417); _FACT_ALIASES untouched (:446-462); discover_compositions untouched, still reads host.home.composition_globs (:1594), pinned by test.
4. PASS — (a) _APIS_STRUCTURAL_KEYS derived via `_DECLARED_BINDING["LOADER_CTX_MEMBERS"].split(".")[-2]` (dsh_compat.py:428-430), no literal — double-pinned (binding present AND `'"loader_ctx"'` absent from guard source, test_dsh_contract.py:1256-1259); (b) oracle face pinned as exact ORDERED 4-tuple + oracle_api_symbols keys == packages + loader_ctx ∉ symbols; JSON keeps loader_ctx last so filter preserves order; (c) by construction only bound keys are skipped — an unbound structural key reaches oracle_api_symbols which raises ContractMalformed on missing `exports` (loud).
5. PASS — lib/index.js exactly 1 line (:277, 1→2); comment :269-275 accurately states the mirror; only JS schema_version reader; adapters fixture host-facts-*.json is a different document type, uncoupled; the 5 JS-mutation tests exist at :2099/:2168/:2180/:2210/:2228 and the tokens test requires the JS renderer to actually read the mutated schema-2 contract.
6. PASS — missing new key/leaf → ContractMalformed naming the path; REQUIRED_PATHS loop (dsh_contract.py:398-400) runs before direct-index shape checks, no KeyError path; deprecation pinned BOTH directions; bindings resolve end-to-end via module __getattr__ + _contract_value.

P1-P7/D1-D4/safety: no verify_workflow.py or dsh_boundary.py changes; validation additions stay in dsh_contract.py's existing fail-loud named-field style; stdlib only; no real ~/.dsh access; docstrings fact-check accurate.

## Findings and dispositions (Coordinator, same day)

1. minor — the 7th diff file (design doc §10 S0 row, +1/−1) appeared during review. Disposition: authored by the Coordinator as the pre-announced §10 S0 file-list correction (lib/index.js omission, disclosed to Developer and in session); re-pinned post-review: exactly 7 modified files, numstat variance is CRLF renormalization noise; content-level review + Coordinator's 516-test run + both gates ran on the final bytes. RESOLVED.
2. nit — 19 new tests, not 18 (15 TestContractV2AdditiveKeys + 4 ContractV2DeclaredBindingTests). Disposition: corrected in this record and closure evidence (19).
3. nit — `deprecations.entries must be non-empty` validator would make the S7-retired state self-malformed. Disposition: obligation added to design §10 S7 row (sidecar retires with the keys in the same atomic commit).
4. nit — 4 of 5 JS-mutation tests are negative-shaped; only the tokens test positively pins the JS contract read. Disposition: awareness only (positive face pinned by non-mutation suites); candidate hardening for S8.

## Acceptance basis

Developer: 438 tests (contract+compat+boundary) OK + test_dsh_adapter 78 OK 52.5s + check-dsh-boundary PASS + check-dsh-preset-compat PASSED + json.load OK; TDD red-first evidence (2 failures + 45 errors before implementation). Coordinator independent re-run: 516 tests OK 132.4s + boundary PASS issues=0 + compat PASSED.
