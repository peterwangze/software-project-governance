# Review — FIX-455 并案定因（FORENSIC R0）

- **Reviewer**: independent Code Reviewer (forensic deliverable review; dispatched by Coordinator session dsh-governance-20261026)
- **Date**: 2026-10-26 (Asia/Shanghai), ~13:47–14:0x +08:00
- **Object**: `docs/diagnostics/windows-ledger-atomic-write.md` — esp. the 2026-10-26 "Policy-state discrimination" section and its cited 2026-10-19 sections; raw observations/drivers under `.codex-sandbox/FIX-455/forensics-20261026/`; corroborating chain EVD-2162/EVD-2166, ACL report, historical FIX-449 review-r1 logs.
- **Verdict**: **APPROVED_WITH_NOTES — unresolved_blockers = 0** (3 × P3 notes, none blocking)

All judgments below are based on files I read and commands I reran myself in this review session (danger-full-access state); Coordinator/Developer narratives were treated as claims-to-verify.

## R1 判别实验内部效度 — PASS

- E1/E2/E3 drivers (`probe20261026.py`, `probe20261026-e2fix.py`) all implement the same operation shape as `authority_ledger._atomic_write`'s replacement: unique **same-directory** temp (`snapshot.json.tmp-<hex8>`), write → flush → **fsync** → **handle closed** (with-block exit / explicit `f.close()`) → `os.replace(tmp, target)`. Verified by reading both drivers line-by-line.
- E2 driver-bug disclosure is faithful: first invocation failed at setup (`FileNotFoundError` on `target.write_bytes` because the workdir was not pre-created) — **before any replace was attempted**, so it could not contaminate a replace observation; the fixed rerun is a setup repair, not a retry-to-green. Disclosed both in `observations.json` (note field) and the doc §discrimination.
- Fixed caps (E1=64, E2=32, E3=8), break-on-first-failure, single run each. No rerun-until-green pattern found.

## R2 双向对照逻辑 — PASS

- Full-access side: 104/104 (64+32+8) per `observations.json`; my independent rerun adds 72/72 (see R5).
- Workspace-write side: historical 3 exceptions (argv verified direct-child, in-workspace — R3), 2026-10-19 case 8 natural failure at attempt 28/64 (real AST-extracted `_atomic_write` driver), and the 2026-10-26 morning cluster (in-workspace lock `O_CREAT` denied once with explicit `[sandbox: file access denied under workspace-write mode]` marker; grandchild temp `mkdir` denied 2/2; Check 28u same cause).
- Conclusion wording is properly bounded: "consistent with intermittent op denials by the DSH harness file-sandbox layer under the workspace-write policy state", explicitly "family-level attribution, not a per-incident proof", 10-19 missing-evidence list preserved, no AV/policy accusation, no share-delete fix claim. **No upgrade to per-incident proof occurs anywhere in the section.**

## R3 旁证链核实 — PASS (read originals, not transcripts)

| Claim | Verified against |
|---|---|
| EVD-2162 exists (grandchild temp denial 2/2 etc.) | `.governance/evidence-log.md` row present, content matches doc account |
| EVD-2166 exists (判别实验机录) | row present; caps/results/E2-bug/boundary statements match `observations.json` and the doc |
| ACL diagnosis NOT_THIS_CLASS | `D:\AI\agent\claude\coding\acl-recovery-20261026\acl-report-e84bf9c5e29147858fd7a62229ec0b4d.jsonl` contains the NOT_THIS_CLASS decision record (WRITE_DAC/WRITE_OWNER true, no package ACEs, 0 changes) |
| Historical runs were direct-child, in-workspace | `regression.json` argv = `C:\Python314\python.exe -X utf8 -c <script>` resolving `skills/...` under repo cwd, exit 1; `regression-retry.json` argv head identical shape, exit 1 |
| UTC intervals in doc table | json time fields are +08 local ("2026年10月18日 20:15:35") → 12:15:35Z as the doc states; conversion correct (see P3-3) |

## R4 原始证据未被改动 — PASS

Recomputed all five SHA-256 from `.codex-sandbox/FIX-455/forensics/input-manifest.json`:

| File | Result |
|---|---|
| `skills/software-project-governance/infra/authority_ledger.py` (`4d3acc44…`) | MATCH |
| `regression.log` (`679e31df…`) | MATCH |
| `regression.json` (`87099611…`) | MATCH |
| `regression-retry.log` (`a6649674…`) | MATCH |
| `regression-retry.json` (`69e472f6…`) | MATCH |

## R5 独立复跑 — PASS

Own driver (not reusing theirs), scratch `.codex-sandbox/FIX-455/forensics-20261026/review-r0/`, single run each, fixed caps, current policy state = danger-full-access:

- **E1′** direct child / in-workspace / same-dir replace ×64 → `{"attempts": 64, "succeeded": 64, "first_failure": null}` — reproduces E1.
- **E3′** grandchild (`python`→`python`) / platform temp / replace ×8 → exit 0, `{"succeeded": 8, "first_failure": null}` — reproduces E3.
- Driver exit 0; raw results preserved at `review-r0/review-r0-observations.json`.

## R6 处置合理性 — PASS

- "Product writer unchanged and non-defective": supported by the 10-19 SOURCE+OBSERVED "Writer ordering" section (event truth recoverable, snapshot failure distinct from event commit, exceptions visible) whose inputs hash-verified unchanged (R4).
- "No production code fix required for FIX-455": consistent with family-level environmental attribution and the absence of any demonstrated product defect (10-19 matrix ruled out readonly/held-handle/share-flag reductions; E-contrasts toggle with policy state only).
- Candidate 1 (commit-boundary exposure) demoted to 0.100 hardening pool as optional, not a defect repair — correctly framed.
- Operational note ("retry in a full-access session before code-level conclusions") is bounded and evidence-aligned.
- No overclaim found: nowhere does the section assert per-incident proof or a specific mechanism beyond "file-sandbox policy layer under workspace-write".

## Findings

- **P3-1 (note)**: The only denial with a captured *explicit* sandbox marker is a **create-op** (lock `O_CREAT` / temp `mkdir`); a **replace-op** denial under workspace-write is inferred from error identity + plane + policy-state correlation (incl. 10-19 case 8), not marker-captured. The "consistent with" family-level wording accommodates this; a one-sentence explicit distinction would make it airtight for future readers.
- **P3-2 (note)**: The 10-26 contrasts re-implement the write shape rather than invoking the real AST-extracted `_atomic_write` (as 10-19's probe did). Acceptable — the discriminated variable is the policy state, and the doc says "share shape … os.replace" — but one clarifying sentence would pre-empt "why not the real function" questions.
- **P3-3 (note)**: Historical `regression*.json` store local (+08) formatted times under fields named `start_utc`/`end_utc` (e.g. `2026年10月18日 20:15:35`). Pre-existing runner artifact, correctly converted in the doc; flag for anyone consuming the raw JSON directly.

## Rerun commands (key evidence)

```
python %TEMP%\spg-r4.py                 # hash recompute → ALL: PASS (5/5 MATCH)
python %TEMP%\spg-r5.py                 # E1′ 64/64 PASS, E3′ 8/8 PASS, DRIVER_EXIT=0
Select-String evidence-log.md "EVD-2162 |" -Quiet   → True
Select-String evidence-log.md "EVD-2166 |" (grep)   → row present
Select-String acl-report-…jsonl "NOT_THIS_CLASS"    → True
```

Scratch: `.codex-sandbox/FIX-455/forensics-20261026/review-r0/` (this review's only writes; plus this report file). No product code/test/diagnostic doc changed; nothing staged/committed; no `.governance/**` writes.
