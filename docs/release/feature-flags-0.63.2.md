# Feature Flags - 0.63.2

**Version**: 0.63.2 (patch)
**Release**: Check 29 auto-discovery 排除 session-snapshot 误报修复（FIX-178）
**Date**: 2026-07-05

## Feature Flag Inventory

This release has **no runtime feature flags** — pure Check 29 false-positive fix. Detection capability fully preserved.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| Check 29 auto-discovery source | enabled (always active) | no longer scans `session-snapshot.md` as a runtime segment; only scans evidence-log "事实依据" field. Inline `text=` runtime scan path unchanged |
| Check 29 detection capability | fully preserved | inline `text=` path byte-unchanged; 12 existing FIX-29 series tests all PASS; new reverse-protection test guards against capability weakening |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Pure bug fix, no behavior change. Detection capability complete (reverse-protection test guards).
