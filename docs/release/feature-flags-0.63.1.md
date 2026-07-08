# Feature Flags - 0.63.1

**Version**: 0.63.1 (patch)
**Release**: archive 引擎 build_index 非结构化归档登记修复（FIX-176）
**Date**: 2026-07-05

## Feature Flag Inventory

This release has **no runtime feature flags** — pure archive engine bug fix.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| archive.py build_index unstructured-archive registration | enabled (always active) | narrative-*.md / recent-completed-*.md now registered as index entries, no longer become orphans after rebuild |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (本体已修 but RISK-039 needs external host validation). No 1.0.0 readiness. Pure bug fix, no behavior change.
