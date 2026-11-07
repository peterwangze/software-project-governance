# FIX-484 Code Review — R0 (2026-11-07)

- Reviewer: Code Reviewer subagent 136aaff5-64d9-4ee6-8037-957e15d2f884 (independent; no files modified, no write commands run)
- Subject: working-tree diff, `skills/software-project-governance/infra/dsh_compat.py` + `skills/software-project-governance/infra/tests/test_dsh_compat.py` only (224/220 changed lines, 15 deletions)
- Verdict: **PASS** — 4 advisory findings (1 minor, 3 nits), no blocker/major, no minimal change set required

## Verified against the brief

- Depth: root=depth 0; only directory descent past cap raises (dsh_compat.py:1591 `depth + 1 > max_depth` before push); files never depth-checked (1596-1601) so a file AT max depth is still matched — no off-by-one.
- entries/time ceilings checked per-entry (1568-1572); `finish()` guards `report is None` (1534); `overflow()` fills report + snapshots counters before raising (1538-1545); `with scan:` closes iterator on raise.
- `set(found)` + sort by `relative_to(root).as_posix()` (1604): every found path is `Path(entry.path)` chained from `root` string-wise, so `relative_to` cannot throw (same guarantee the old glob path had, incl. relative roots).
- Junction can never be followed: reparse/symlink test (1581-1583) precedes S_ISDIR branch and stack push; junction attr from non-following `os.stat`; `entry.is_symlink()` covers POSIX. Zero-inode identities are never inserted into `visited` (1554, 1593) so the unconditional membership check (1589) can't false-skip on inode-less filesystems.
- `.governance/sandboxes` pruned before `os.scandir` (1586-1587) — never entered; tests write only in `_scratch` temp dirs; junction removed via unlink/rmdir of the LINK itself in `finally` before scratch cleanup; no real `C:\Users\peter\.dsh` access in the diff.
- Caller: overflow except (2285) sits before generic `except Exception` (2302) in the same try; maps to VERDICT_NOT_RUN + SCAN_OVERFLOW reason + `report["scan"]` counters; reparse/errors disclosure line 2229-2234. Verdict vocabulary intact; names from `_fact("_composition_globs")` only — no hardcoded host facts; 58-min incident docstring matches provided context.
- Tests are genuine: junction test asserts exact found-set AND measured (not slept) elapsed <5s AND `skipped_reparse_points>=1` — the counter assertion is what actually catches a reparse-check regression (visited-set alone would terminate the root-loop); prune test asserts `dirs==3` (observable never-entered); fake clock advances 1.0/call with max_seconds=0.5, zero sleeps; repo-root test asserts exact single composition + bounded_out False. Fallback chain mklink /J → os.symlink → skipTest(reason) as specified.
- Diff purity: 224/220 lines; the 15 deletions = old function body + 2 caller lines; nothing unrelated. Walk stays one function family; caller mapping separated (D1-D4 ok; docs' planned S2 dsh_walk.py extraction is out of scope).

## Findings

1. minor (P5 generality) — dsh_compat.py:1521: `pattern.rsplit("/", 1)[-1]` reduces every contract glob to its basename, so a future multi-segment glob (e.g. `agent-presets/**/*.cordis.yml`) would silently over-match at any depth; validate patterns are `**/<name>` or bare `<name>` and fail loudly otherwise.
2. nit (quality) — dsh_compat.py:2228 vs 2287: success-path `report["scan"]` lacks `max_depth_hit` (finish's `report.update(counters)` at 1535 omits it) while the overflow face includes it; initialize `"max_depth_hit": False` in counters (1525) so both faces share shape.
3. nit (P4 test guard) — test_dsh_compat.py:3987: no case pins "a file exactly at max_depth is still matched" (the off-by-one hazard); add max_depth=1 with a composition at depth 1 asserting found-without-overflow.
4. nit (quality) — dsh_compat.py:1571: time ceiling is read only per-entry, so a single hung zero-entry directory enumeration (network share) can block past 30s; inherent to single-threaded walks, note only. Also noted: symlinked composition FILES are now skipped (old glob found them) — brief-mandated and disclosed via the counter; fnmatch-vs-pathlib docstring claim verified equivalent for basename-only patterns (both normcase on Windows, identity on POSIX; pathlib additionally never crosses separators, immaterial for single-segment matches).

## Disposition (Coordinator, same day)

R0 = APPROVED_WITH_NOTES. Findings 1–3 dispatched to the Developer as review-fix round R1 (cheap, in-scope; DEC-286 发现即闭环); finding 4 accepted as note-only. Commit gate: after R1 lands + Reviewer delta confirmation.
