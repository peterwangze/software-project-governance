# FIX-485 Code Review — R0 (2026-11-07)

- Reviewer: Code Reviewer subagent e5832a2d-2487-4d5e-ad1a-c8031e646ef0 (focused delta, read-only; one single-module run permitted and used)
- Subject: test-only fix +87/−14 across exactly skills/software-project-governance/infra/tests/test_dsh_compat.py (+77) and test_dsh_plane.py (+24/−10). Original Developer (477a2986) died mid-task after editing; Coordinator verified the tree independently before this review.
- Verdict: **APPROVED_WITH_NOTES** (1 minor non-blocking finding, fold-in pre-approved)

## Context

S1's plane tests failed on CI Linux (run 42344249306, failures=4): fixtures used Windows-drive-letter paths as fake PATH entries; POSIX splits on `:` so the entries shattered. Two failure classes: (a) test_dsh_plane fake-PATH fixtures — fixed with separator-free synthetic roots joined via os.pathsep; (b) test_dsh_compat wiring tests on real scratch dirs — fixed with `_ScratchFs`, an FsPort double whose docstring records the root-slash-strip loss (dsh_plane.py:87 `_join` strips leading "/"; on POSIX CI every real-fs plane lookup missed) and which re-absolutizes; on Windows byte-equivalent to RealFs.

## Six points

1. PASS — diagnosis correct; dsh_plane.py:559 splits PATH on os.pathsep; changed fixtures separator-free on both platforms; remaining D:/C: values are opaque _FakeFs dict keys / process-port strings, never split.
2. PASS — _ScratchFs (test_dsh_compat.py:4330) delegates all 9 FsPort methods; Windows drive-letter branch identical to RealFs; patch seam verified (dsh_plane.py:625 module-attribute lookup at call time → mock.patch.object effective); POSIX re-absolutization unreachable on Windows → no weakening of the four failing assertions (all unchanged).
3. PASS — every −line is fixture/path reshaping; the four assertions intact; node_modules expectation string changed only with the fixture root.
4. PASS — scope pure (2 test files only).
5. PASS — os.pathsep.join correct; no sleeps; no real ~/.dsh or D:\app\dsh dependence introduced.
6. PASS + 1 finding — test_dsh_asar.py clean (D:\app\dsh only in docstrings). FINDING (minor, non-blocking): test_dsh_plane.py:391 `test_a_shim_without_an_install_anchor_is_skipped` keeps `"PATH": "D:/bare"` — on POSIX degenerates to vacuous "no shim found" (green but no longer exercising shim-present/anchor-missing). Fix (pre-approved, exact): `fs.add_file("synth/bare/dsh.exe", b"MZ")` + `{"PATH": os.pathsep.join(["synth/bare"])}`.

Reviewer single-module run: python -m unittest test_dsh_plane → 28 tests, OK.

## Acceptance basis

Coordinator independent: full test_dsh_* family (9 modules, 700 tests) OK 124.1s on FIX-485 bytes. CI failure evidence: run 42344249306 FAILED failures=4 (the four tests, assertions transcribed in EVD-2216); S0's run 42340528977 green (excludes pre-existing red); S2's run 42347591996 failed the same face (predicted; cured by this commit).

## Disposition

Fold-in of the :391 fixture fix dispatched to Developer d8c277e9 (original Developer dead); commit gate after its two-line landing + module re-run.
