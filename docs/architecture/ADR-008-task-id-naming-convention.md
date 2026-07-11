# ADR-008: Task ID Naming Convention

> **Status**: Proposed (pending DEC-100 adoption)
> **Date**: 2026-07-11
> **Addresses**: SYSGAP-045 (task ID prefix has no formal spec; FX/FIX number-space overlap)
> **Supersedes**: Implicit convention (none — FX prefix adopted without decision record)

## 1. Context

The project has accumulated 12+ task ID prefixes (FIX, FX, REL, AUDIT, REQ, VAL, DOC, MAINT, SYSGAP, TD, DEC, EVD, RISK) over 324+ tasks without a formal naming convention document. Key problems surfaced:

1. **No formal definition**: No governance document, ADR, or decision record defines prefix semantics. The FX prefix (first used FX-175, 2026-07-04) was adopted by Coordinator without a decision record. Full-repo grep for "FX 缩写"/"FX 代表"/"FX 全称" returns zero hits.

2. **Number-space collision**: plan-tracker simultaneously contains `FX-187` and `FIX-187` (two completely different tasks) — FX-187 is "release 0.64.1 patch", FIX-187 is "verify_workflow.py ROOT/SAMPLE_PATH crash fix". Same collision for FX-130/FIX-130, FX-131/FIX-131, FX-188/FIX-188. Referencing "187" is ambiguous.

3. **No validation**: `verify_workflow.py` validates format (`[A-Z]+-\d+`) but not prefix membership — `FOO-123` or `XYZ-999` would pass.

4. **FX/REL overlap**: Both FX-187 and REL-053 are "version-sliced release tasks" — same semantic, different prefixes.

## 2. Decision

### 2.1 Prefix taxonomy (authoritative)

| Prefix | Domain | Semantic | Example |
|--------|--------|----------|---------|
| **FIX** | Bug fix | Product code defect repair (root-cause fix, not feature) | FIX-170 (archive engine state filter) |
| **FX** | Feature execution | Version-sliced architecture/feature implementation slice with explicit release carrying (Slice N of M, Release Reviewer) | FX-188~194 (0.65.0 loop-engineering 7 slices) |
| **REL** | Release | Version publication task (CHANGELOG + version sync + release docs) | REL-053 (release 0.65.0) |
| **AUDIT** | Audit | Diagnostic/investigation task (read-only Analyst/Explore, produces finding) | AUDIT-130 (loop-engineering ADR) |
| **REQ** | Requirement | Requirement analysis / competitive research / needs definition | REQ-101 |
| **VAL** | Validation | External validation task (real-target verification run) | VAL-007 (shitu loop-engineering) |
| **DOC** | Documentation | Documentation completion (treatment-record category, Coordinator-direct) | DOC-001 |
| **MAINT** | Maintenance | Maintenance/cleanup/housekeeping | MAINT-001 |
| **SYSGAP** | System gap | Systemic governance gap identification (feeds improvement backlog) | SYSGAP-030 |
| **TD** | Tech debt | Tech-debt item (tracked, may not be versioned) | TD-014 |
| **COORD** | Coordinator | Coordinator internal task (reserved, currently unused) | — |

**FX vs FIX disambiguation rule**:
- **FIX** = reactive repair of an existing defect (something is broken)
- **FX** = proactive feature/architecture implementation slice (building something new, version-carried, multi-slice)

**FX vs REL disambiguation rule**:
- **FX** = implementation slice within a version (one of N slices, has Developer work + Code Reviewer)
- **REL** = the release publication itself (version bump + CHANGELOG + release docs + Release Reviewer)

### 2.2 Number-space uniqueness (mandatory)

**Rule**: Within a single prefix, numbers MUST be unique and sequential. Across prefixes, numbers MAY overlap (FX-187 and FIX-187 are syntactically distinct IDs).

**Rationale**: `[A-Z]+-\d+` already guarantees global uniqueness via the prefix. The number-space collision is only a *human-readability* concern, not a correctness concern.

**Mitigation for readability**: When referencing a task verbally or in prose, MUST include the full prefix (say "FIX-187" not "187").

### 2.3 Validation (verify_workflow.py enhancement — future)

**Current**: format-only regex `[A-Z]+-\d+`.
**Future (P3, not blocking)**: add a known-prefix whitelist check (advisory WARN, not FAIL) to catch typos like `FIXX-123`. This requires a product-code change and is deferred to a separate FIX/FX task.

### 2.4 Historical reconciliation (FIX-187 / FIX-188)

**Decision**: DO NOT renumber committed tasks (FIX-187, FIX-188). Rationale:
- `FIX-187` and `FIX-188` are already committed (407b74c, referenced in evidence-log EVD-686).
- Renumbering would break commit-message task-ID traceability, evidence-log cross-references, and Code Reviewer REVIEW-FIX-187-R0 / REVIEW-FIX-188 references.
- The collision is human-readability only, not correctness — both IDs are syntactically distinct.
- **Forward rule**: new FIX numbers MUST check FX number-space collision before assignment. If FX-{N} exists, FIX-{N} is discouraged (pick FIX-{N+1} or higher to avoid the same number). This rule is advisory (Coordinator judgment), not mechanically enforced.

## 3. No-overclaim boundary

- This convention governs task ID prefix selection for human clarity and future validation.
- It does NOT make any prefix "more correct" than another for a given task — the task's actual work and evidence determine correctness.
- It does NOT retroactively invalidate FX-175's adoption or any committed task.
- It does NOT claim the prefix list is exhaustive — new prefixes may be added via future ADR if a genuine new domain emerges.

## 4. References

- SYSGAP-045 (this gap's task entry)
- DEC-100 (adoption decision, pending)
- Existing prefixes audit: plan-tracker.md priority table + archive/index.md
- `verify_workflow.py:9774` (commit task-ID regex `^([A-Z]+-\d+)`)
- `behavior-protocol.md` M7.4 step 5 / M7.5 step 4 (commit prefix requirement)
