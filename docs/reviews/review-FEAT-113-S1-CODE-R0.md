# FEAT-113 S1 Code Review — R0 (2026-11-07)

- Reviewer: Code Reviewer subagent 055c38ce-2398-4582-a242-3eae5e43b64c (read-only)
- Subject: uncommitted working-tree diff — 4 NEW files (dsh_asar.py 330 L · dsh_plane.py 529 L · test_dsh_asar.py 305 L · test_dsh_plane.py 357 L) + dsh_compat.py +49/−1 · test_dsh_compat.py +110
- Verdict: **APPROVED_WITH_NOTES** (6 findings, all LOW, none blocking)

## Point-by-point — all PASS

1. PASS — dsh_asar pure functions take bytes; FsPort-injectable; framing byte-confirmed against the real archive (prefix=4, payload=5748132, dup=5748128, json=5748124, base=5748140 — true pickle-in-pickle layout); all declared codes raised+pinned (HEADER_TRUNCATED/MAGIC_INVALID/JSON_INVALID/ENTRY_OUT_OF_RANGE/LINK_CYCLE/dot-dot); unpacked sibling read + contract cap 200000 pinned; only deviation = finding 1.
2. PASS — resolve() iterates contract host.planes.precedence verbatim in design §3.2 order (unknown entry → loud ValueError, dsh_plane.py:598-604); env names via dsh_contract.get; explicit-but-unusable → single PLANE_UNUSABLE plane + plane_verdict NOT_RUN, never silent fallback (:605-608); probe off unless port injected AND switch≠0 (:444-447); identity() emits full dsh-plane/1 face.
3. PASS — install["planes"]={verdict,reason,identities} is the only new report face, computed before all four returns (dsh_compat.py:1387); legacy fields/verdict semantics diff-pure-additive, still npm-CLI-resolved; ImportError degradation mirrors the existing lazy-import precedent (:611-614) and covers missing dsh_asar.
4. PASS (one note) — synthetic-only tests; six-source precedence pin; 4 unusable variants; probe off-by-default/kill-switch/ancestor-found; every-return-path covered except finding 6; red-first (ModuleNotFoundError pre-impl) not machine-verifiable in-repo — Developer to attach captured output in R1 report.
5. PASS — independent from-scratch parser (no dsh_asar import), read-only on D:\app\dsh\resources\app.asar (213,202,918 B): header_sha256 = ea371c0a1f7a938f26fb37f0850801a4623a758e9a074553ed41eb3acf7207b1 — EXACT match to claimed; entry_count = 25418 EXACT (all-nodes; files-only would be 22102); dsh_version 0.2.2-rc.1 at the single anchor hit. Numbers are real, not transcribed.
6. PASS — §9.1 single responsibility; stdlib-only; ctypes Toolhelp32 read-only/failure-tolerant; no subprocess spawn; D:\app\dsh read-only; no ~/.dsh writes; no Start-Sleep.

## Kill-switch ruling (Reviewer)

ACCEPT the Developer's position: DSH_PLANE_PROBE_PROCESS is our operational mitigation knob (design §3.2/§11 R1), not a host fact; the contract carries only host facts; constant is single-source (PROBE_SWITCH_ENV) and test-pinned. Promote to a shared governance-constants module only if a second consumer appears — never into host-contract.

## Findings (dispositions: Coordinator → Developer R1 round, same day)

1. LOW — dsh_asar.py:250-263 link loop appends from-node every iteration → effective budget 4 hops, not 8; legitimate 5-hop chain mislabeled ASAR_LINK_CYCLE. → R1: append targets only / hop counter + 5-pass/9-reject tests.
2. LOW — dsh_compat.py:1281-1287 comment's enabled_in claims "exactly the faces that call this function" but dsh_boundary.py never calls it; actual callers = doctor + 28v builder (:2367). → R1: align comment to design §3.2 wording.
3. LOW — dsh_plane.py:225-233 real install has "Uninstall DeepSeek Harness.exe" sibling → _sibling_executable None → env-sourced asar plane runner.program=null. → R1: exclude Uninstall* / prefer package-named exe + test.
4. LOW — dsh_asar.py:304-309,383 malformed file node (no offset/link, size>0) passes bounds then TypeErrors at content_base+None. → R1: coded AsarError reject + test.
5. LOW — dsh_plane.py:337-341 ctypes lacks argtypes/restype; truncated c_int −1 ≠ INVALID_HANDLE_VALUE; errors degrade via Process32FirstW instead. → R1: restype=wintypes.HANDLE / BOOL + argtypes.
6. LOW — test_dsh_compat.py:4342 covers only env-override-invalid return path. → R1: add planes-face assertion for PATH-shim-no-anchor return (dsh_compat.py:1424-1429).

## Acceptance basis

Developer: 495 tests OK 103s + check-dsh-boundary PASS + check-dsh-preset-compat PASSED (legacy face unchanged; gate JSON lists the asar plane). Coordinator independent re-run: 495 tests OK 103.7s + boundary PASS issues=0 + compat PASSED. Real-asar smoke: asar-desktop/process-ancestor/D:/app/dsh/resources/app.asar/0.2.2-rc.1/ea371c0a…07b1 + entry_count 25418 + runtime 24.21.0 + runner DeepSeek Harness.exe; four planes listed together.
