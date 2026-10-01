# Release Checklist - 0.63.0

**Version**: 0.63.0 (minor)
**Release**: Coordinator 检视循环协议修复 + verify Check 29/30（FIX-173/174）+ archive 引擎修复（FIX-168/170/171/172）
**Date**: 2026-07-04
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.63.0 (minor: protocol behavior change M5.4 tightening + new checks + bundled pre-release fixes) |
| 2 | Change list enumerated | ✅ FIX-173 (protocol layer) + FIX-174 (verify infrastructure) + FIX-168/170/171/172 (bundled archive/CI fixes) |
| 3 | Change types marked | ✅ Added (Check 29/30, M5.1b/M5.4b, step 4.5b/4.6, routing table, 6 reviewer agents) / ⚠️ Changed (M5.4 SHOULD→MUST behavior change, Check 21 强化, ID drift fix) / Fixed (FIX-168/170/171/172) |
| 4 | Release window | ✅ 2026-07-04 |

### Change inventory
- **Check 29 (M5 runtime scan)** — `check_m5_runtime_triggers`: best-effort scan of M5.1b triggers (T1 question close + T2 numbered menu + choice words proximity), detects "question/menu but no AskUserQuestion" violations; advisory.
- **Check 30 (review closure state machine)** — `check_review_closure`: validates M7.4 step 4.6 — each REVIEW evidence converges to APPROVED/BLOCKED, circuit breaker (max 3 rounds), degraded quota (≤2), backward compat (bare REVIEW-{id}=R0).
- **M5.1b deterministic triggers** — behavior-protocol.md runtime deterministic trigger definition (question mark main signal + word set auxiliary + 4 exemption zones).
- **⚠️ M5.4b pure-notification tightening (BEHAVIOR CHANGE)** — N1 no question / N2 no numbered options / N3 ℹ️/📢/>注：/>>派发 prefix. Existing SHOULD → MUST.
- **M7.4 step 4.5b (spawn guard, diff-gated)** — product-code diff + route-table post-review Agent + no REVIEW evidence → BLOCKING; 3 exemptions.
- **M7.4 step 4.6 (review loop state machine)** — C1-C7 mandatory clauses + circuit breaker + degraded quota + escalation 4 options.
- **methodology-routing.md post-review column** — routing table 4→6 column restructure.
- **agent-communication-protocol.md review process** + **6 reviewer agent + developer.md review protocol**.
- **FIX-174 unit tests** — test_verify_workflow.py +580 lines.
- **Check 21 强化** — `check_review_debt` → `review_spawn_gap` (three-source cross: product diff ∧ route table ∧ no REVIEW evidence) + degraded fuse (same task ≥3 → FAIL).
- **Check 18-27 ID drift systematic fix** — 52 lines no-logic-change alignment.
- **Bundled pre-release fixes**: FIX-168 (CI manifest-consistency, Chrys adapter 5 sync points), FIX-170 (archive status filter, AUDIT-127 root cause), FIX-171 (evidence subset gate relaxation + legacy version parse + roadmap fix), FIX-172 (archive body-write data loss, FIX-158 regression).

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.0
→ Result: to be confirmed at commit time
```

Review evidence: FIX-173 Code Reviewer R0 APPROVED 6/6; FIX-174 Code Reviewer R0→R1 closed loop. Architect v2 + Design Reviewer round2 APPROVED + AUDIT-128 diagnosis + user 3 decisions.

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Check 29/30 advisory. 4 pre-release fixes bundled. Version number repurposed from DEC-088 Phase 5 split (deferred to 0.65.0+). 降级 SoD (DEC-090/091).
