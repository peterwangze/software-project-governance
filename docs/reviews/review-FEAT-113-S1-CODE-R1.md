# FEAT-113 S1 Code Review — R1 delta (2026-11-07)

- Reviewer: Code Reviewer subagent 055c38ce-2398-4582-a242-3eae5e43b64c (delta scope, read-only)
- Delta base: R0 report (docs/reviews/review-FEAT-113-S1-CODE-R0.md), 6 findings
- Verdict: **APPROVED** — 6/6 closed, no new code issues

## Findings closure

- F1 ✓ dsh_asar.py:255-271 — hop counter counts link→target transitions, chain appends targets only; 5-hop resolves with clean chain (test pins 6-tuple), 9-hop refuses "more than 8 link hops", code stays ASAR_LINK_CYCLE, cycle-check intact; §3.3 ≤8-hop semantics now exact.
- F2 ✓ dsh_compat.py:1280-1287 — comment states doctor/28v read evidence through this function; dsh_boundary never calls/inherits; --install doesn't call; matches the verified caller map.
- F3 ✓ dsh_plane.py:238-241 — Uninstall* filtered case-insensitively, exactly-one-candidate rule kept (ambiguity stays None); test pins program="D:/app/dsh/DeepSeek Harness.exe" + source=asar-sibling-executable, consistent with the read-only listing of D:\app\dsh (exactly those two exes).
- F4 ✓ dsh_asar.py:44,382-390 — size>0/no-offset/not-unpacked raises ASAR_ENTRY_CORRUPT before bounds math; size-0/no-offset returns b""; both tests real (hand-built lying indexes, coded assertions). LOW doc-sync note: 7th code beyond design §3.3's six — added to the design enumeration in the same commit (Coordinator).
- F5 ✓ dsh_plane.py:346-366 — all six WinAPI signatures typed; restype=HANDLE makes INVALID_HANDLE_VALUE comparison semantically correct.
- F6 ✓ test_dsh_compat.py:4380-4394 — real shim file + which={"dsh": shim}; asserts NOT_RUN + reason + planes face OK/empty; non-trivial (fails if the early return ever precedes the planes assignment).

## Notes

- Scope: 7th untracked file = machine-recorded R0 review report (review-record discipline); committed consciously with S1 (FIX-484 convention).
- Cosmetic: _entry_in_bounds' offset-None branch (dsh_asar.py:312) now dead via read_bytes — harmless.
- Red-first evidence attached by Developer: ImportError/ModuleNotFoundError for test_dsh_asar + test_dsh_plane captured 2026-11-07 13:06 pre-implementation.

## Acceptance basis (final bytes)

Developer: 501 tests OK 99.8s + boundary PASS + compat PASSED; real-asar smoke unchanged (ea371c0a…07b1 / 25418 / 0.2.2-rc.1). Coordinator independent re-run: 501 tests OK 99.2s + boundary PASS issues=0 + compat PASSED.
