# Feature Flags - 0.63.0

**Version**: 0.63.0 (minor)
**Release**: Coordinator 检视循环协议修复 + verify Check 29/30（FIX-173/174）+ archive 引擎修复（FIX-168/170/171/172）
**Date**: 2026-07-04
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## Feature Flag Inventory

This release has **no runtime feature flags** — all additions (Check 29/30, M5.1b/M5.4b triggers, step 4.5b/4.6 state machine) are advisory/protocol-layer and always active.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| Check 29 (M5 runtime scan) | enabled (advisory) | best-effort, no-corpus degrades to no-verdict |
| Check 30 (review closure state machine) | enabled (advisory) | validates M7.4 step 4.6 convergence to APPROVED/BLOCKED |
| M5.1b deterministic triggers | enabled | runtime determinstic triggers (T1 question close + T2 numbered menu) |
| **M5.4b pure-notification tightening** | **enabled — ⚠️ BEHAVIOR CHANGE** | existing SHOULD upgraded to MUST (N1 no question / N2 no numbered options / N3 ℹ️/📢/> prefix) |
| M7.4 step 4.5b spawn guard | enabled (diff-gated) | product-code diff + route-table post-review Agent + no REVIEW evidence → BLOCKING |
| M7.4 step 4.6 review loop state machine | enabled | C1-C7 clauses + circuit breaker (3 rounds) + degraded quota (≤2) |
| FIX-168 Chrys manifest sync | enabled (always active) | CI manifest-consistency fix |
| FIX-170 archive status filter | enabled (always active) | skip OPEN/active risks/decisions in migration |
| FIX-171 evidence subset gate relaxation | enabled (always active) | ignore cross-entity RISK/DEC/REVIEW refs |
| FIX-172 archive body-write fix | enabled (always active) | priority-table task body-write gating fix |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Check 29/30 are advisory, not hard product-code gates. 0.62.0..0.63.0 includes 4 pre-release fixes (FIX-168/170/171/172) not individually versioned, bundled here. Version number repurposed from DEC-088 "verify_workflow.py Phase 5 split" to "protocol + verify check loop" theme; Phase 5 deferred to 0.65.0+.
