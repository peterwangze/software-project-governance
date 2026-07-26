# ADR-016: verify_workflow.py Phase 5 — evidence/risk/review domain extraction (0.70.0)

- **Status**: Proposed (awaiting Design Review)
- **Date**: 2026-07-26
- **Version**: 0.70.0 (MINOR)
- **Author**: Architect
- **Scope**: FEAT-009 / REL-062
- **Supersedes / continues**: Continues DEC-083 (Phase 1–4 roadmap) and DEC-088 (real-extraction methodology). Does **not** supersede DEC-088; it executes the methodology on the final segment.
- **Related**: DEC-086 (Phase 1 SoD authorization, archived), DEC-087 (Phase 2), DEC-090/091 (downgraded SoD), DEC-096 (active-version authority), DEC-104 (runtime-first roadmap that postponed Phase 5 to 0.70.0), RISK-039 (architecture-degradation watch).

---

## 1. Context

### 1.1 The God Module

`skills/software-project-governance/infra/verify_workflow.py` is currently **22,468 lines**, **485 top-level defs/classes**, and dispatches **54 CLI subcommands**. ArchGuard (`check-architecture-health`) currently reports it as **ERROR** at the module-size threshold (`warn_lines=2000`, `error_lines=5000` in `core/architecture-health.json`), plus several oversized-function ERRORs (`cmd_check_governance`=1211 lines, `main`=720 lines) and WARNs (`check_review_closure`=204, `check_m5_compliance`=217, `check_lifecycle_registry`=448). This is the F1 finding from AUDIT-121.

### 1.2 Methodology — DEC-088 (the binding constraint)

DEC-088 (2026-06-27, archived) was the **corrective** to DEC-083's naïve per-domain plan. Its three findings are binding on this ADR:

1. **Re-export shuffling does not reduce the main file.** Phases 1/2 moved functions to `checks/manifest.py` (517 lines) and `checks/capability_registry.py` (304 lines) but kept `from checks.X import (...)` re-export blocks *inside* verify_workflow.py. That kept call sites working but is position-transplant, not elimination. DEC-088 forbids disguising transplant as extraction.
2. **The legitimate bulk is business logic** (~16,000 lines = 54 commands × governance rules). It cannot be compressed; it can only be **moved**. Progress on it must be measured by **functional-boundary line reduction in the main file**, not by lines in new modules.
3. **The data-driven Step A+B refactor (externalize data tables + render-orchestrator) was attempted, then stalled.** Plan-tracker line 68: `FIX-155/156/REL-047` were marked **停滞/停滞待定**. The hard-coded `cmd_check_governance` print blocks were *not* collapsed into a table-driven renderer. **This ADR does not assume Step B exists**; it extracts domains whose functions are still inline in verify_workflow.py today.

### 1.3 Phase 1–4 precedent (the pattern to follow)

| Phase | Version | Module | Lines moved | Net Δ on verify_workflow.py |
|-------|---------|--------|-------------|------------------------------|
| 1 | 0.59.0 | `infra/checks/manifest.py` | 401 (12 fns + cmd) | 20,937 → 20,516 (−421) |
| 2 | 0.60.0 | `infra/checks/capability_registry.py` | 304 (1 check + 7 consts) | 20,516 → 20,321 (−195) |
| 3–6 | 0.61.0+ | — | — | Stalled per DEC-088; Phase numbers consumed by other topics (0.63.0 took the Phase 5 number for protocol-layer work, 0.64.0 took Phase 6 for resolve_entry). |

The pattern established by Phase 1/2 and replicated by 0.63.0's Check 29/30 additions:

- New module lives at `skills/software-project-governance/infra/checks/<domain>.py`.
- Module header documents scope, version, DEC reference, and a line-number baseline.
- **Deferred `_vw()` accessor** for shared helpers still in verify_workflow.py — *not* a top-level `from verify_workflow import ...`, to avoid an import cycle (verify_workflow imports the new module at load; the new module reaches back lazily). This is the REVIEW-FIX-153 P2 pattern, replicated in capability_registry.py.
- verify_workflow.py keeps a **thin `from checks.<domain> import (...)` re-export block** so existing call sites (`cmd_check_governance` print blocks, `cmd_check_review_debt`, `main()` argparse dispatch, and the test suite `import verify_workflow as vw; vw.check_X()`) continue to resolve.
- New module owns its domain constants (e.g. `DEGRADED_FUSE_THRESHOLD`, `FIX173_NAMING_NORMALIZATION_DATE` move with the review domain).

### 1.4 Why now (DEC-104 context)

DEC-104 (2026-07-11) placed runtime-first work (Loop Engineering, FEAT-002–008) at 0.67.0–0.69.0 and **postponed** the originally-scheduled 0.67.0 Phase 5 to 0.70.0. With DEC-133 (2026-07-26) closing RISK-037/042 and the runtime chain externally validated, 0.70.0 is unblocked to deliver the final architecture-health segment on the God Module. REL-062 acceptance: "架构健康、兼容性、投影与 release-lineage 全部复验."

---

## 2. Decision

Extract **three domains** into three new modules under `skills/software-project-governance/infra/checks/`, using the Phase 1/2 deferred-`_vw()` pattern. The extraction is **real** (functions physically move; verify_workflow.py line count drops) and **non-behavioral** (identical CLI, output, exit codes).

| Domain | New module | Phase tag |
|--------|-----------|-----------|
| Evidence | `infra/checks/evidence_domain.py` | Phase 5a |
| Risk | `infra/checks/risk_domain.py` | Phase 5b |
| Review | `infra/checks/review_domain.py` | Phase 5c |

**Not in scope for 0.70.0**: extracting shared utilities into a `checks/_shared.py` (path resolution, git helpers, markdown-table parsers). The Phase 1/2 precedent reaches these via `_vw()`; the new domains do the same. A `_shared.py` extraction is deferred to a later release to keep 0.70.0 reviewable and to avoid churning the deferred-access pattern while the bulk of consumers still live in verify_workflow.py.

---

## 3. Domain boundary definitions

Boundaries are derived from the **dispatch call sites in `cmd_check_governance`** (lines 15131–16349) and the CLI surface, then cross-checked against function-name semantics. Each domain is the set of functions + constants that a single Check block in `cmd_check_governance` calls, plus the helpers used only by that block.

Line counts below are **def-function spans** measured on the 0.69.0 baseline (`wc -l` = 22,468). They are the upper bound on what physically moves; the net reduction on verify_workflow.py is slightly smaller because of the re-export block added back (≈ 1 line per re-exported symbol + 12-line section header, matching Phase 1/2).

### 3.1 Evidence domain — `checks/evidence_domain.py`

Owns: "is every completed task backed by a structured evidence row, and is each row well-formed?"

| Function | Lines | Site | Notes |
|----------|------:|------|-------|
| `check_evidence_completeness` | 27 | L9246 | Check 1. Depends on `GovernanceDataSource` (stays in v_w). |
| `check_evidence_quality` | 47 | L9486 | Check 1b (format). |
| `check_structured_evidence` | 52 | L11834 | Validates structured-fact payloads. |
| `check_fact_grounding` | 45 | L11675 | Verifies claims cite a fact row. |
| `parse_evidence_task_ids` | 16 | L9187 | Pure helper, evidence-only. |
| `parse_evidence_task_map` | 18 | L9203 | Pure helper, evidence-only. |
| `_evidence_header_index` | 12 | L7844 | Header detection for evidence-log rows. |
| `_extract_evidence_task_id` | 8 | L7856 | |
| `_evidence_state_cells` | 18 | L7864 | |
| `_is_closed_evidence_state` | 7 | L7882 | |
| `_is_active_evidence_state` | 5 | L7889 | |
| `_parse_evidence_context_tasks` | 49 | L7894 | Used by `discover_governance_context`. |
| `_count_evidence_rows` | 9 | L3775 | Used by migration preview only (cross-domain — keep in v_w, **do not move**). |
| `_evidence_closes_fix_069_while_req_open` | 31 | L1487 | Specific to release-readiness fact-source (Check 23). **Move only if no other call site; default KEEP.** |
| `_evidence_task_type_index` | 44 | L14958 | Used by review domain (Check 30 routing). **Cross-domain — keep in v_w as a shared helper, do not move.** |
| `_iter_archive_aware_evidence_units` | 26 | L16521 | Used by G10 gate-checks. **Cross-domain — keep in v_w.** |
| `_check_evidence_mentions` | 8 | L16458 | Used by G1–G11 gate auto-judge. **Cross-domain — keep in v_w.** |

**Moves (in-scope, evidence-only consumers)**: 11 functions, ≈ **244 lines**.

**Stays in verify_workflow.py** (cross-domain consumers; reached via `_vw()` by the new module if needed): `_count_evidence_rows`, `_evidence_closes_fix_069_while_req_open`, `_evidence_task_type_index`, `_iter_archive_aware_evidence_units`, `_check_evidence_mentions`. This is the same boundary discipline Phase 1/2 used: a function moves only if all its callers move with it; otherwise it stays and the new domain reaches it via `_vw()`.

**Checks affected**: Check 1 (evidence completeness), Check 1b (evidence quality), Check 6 (structured evidence), Check 6b (fact grounding).

### 3.2 Risk domain — `checks/risk_domain.py`

Owns: "are open risks fresh, and do escalated risks carry evidence?"

| Function | Lines | Site | Notes |
|----------|------:|------|-------|
| `check_risk_staleness` | 23 | L9273 | Check 2. |
| `check_risk_escalation` | 61 | L9731 | Check 8. |
| `parse_open_risks` | 20 | L9221 | Pure helper, risk-only. |
| `_parse_context_open_risks` | 26 | L8038 | Used by `discover_governance_context`. Risk-only consumer. |
| `_risk_status_is_closed` | 12 | L6129 | Used by `check_one_dot_zero_release_blockers` (Check 24, stays in v_w). **Cross-domain — keep in v_w.** |
| `_check_risk_has_closed` | 9 | L16700 | Used by G7/G10 auto-judge. **Cross-domain — keep in v_w.** |

**Moves**: 4 functions, ≈ **130 lines**.

**Checks affected**: Check 2 (risk staleness), Check 8 (risk escalation).

### 3.3 Review domain — `checks/review_domain.py`

Owns: "was the agent-team review protocol followed — spawn gap, M5 runtime triggers, round continuity, closure, and reviewer coverage?" This is the **largest** domain because 0.63.0 (FIX-173/174) added Check 29 (M5) and Check 30 (closure) plus hardened Check 21.

| Function | Lines | Site | Notes |
|----------|------:|------|-------|
| `check_review_spawn_gap` | 100 | L13749 | Check 21 (DEC-094 §3.3 spawn guard). Pure 3-source judge; fixture-friendly. |
| `check_m5_runtime_triggers` | 185 | L14337 | Check 29 (DEC-094 M5.1b/M5.4b). |
| `check_m5_compliance` | 221 | L10230 | Check 29 orchestrator. **Oversized (ArchGuard WARN at 217). Extraction is a prerequisite to refactoring it.** |
| `check_review_closure` | 206 | L14752 | Check 30 (DEC-094 V1–V4 state machine). |
| `_build_review_sequence` | 97 | L14655 | Round-continuity builder. |
| `_collect_live_review_sequences` | 99 | L15032 | Live evidence-log scanner for Check 30. |
| `check_review_debt` | 127 | L13622 | Check 22 (degraded-review debt). |
| `check_review_coverage` | 115 | L13849 | Check 21b (reviewer coverage). |
| `check_agent_team_review` | 87 | L13202 | Check 18 (DRI/Reviewer spawn). |
| `check_governance_review_fallback_policy` | 114 | L14106 | Check 18b. |
| `_parse_review_coverage_details` | 81 | L13112 | Review-only helper. |
| `_parse_review_covered_tasks` | 9 | L13193 | |
| `_parse_routing_post_review_table` | 56 | L13479 | Routing-table parser, review-only. |
| `_routing_post_review_for_task_type` | 28 | L13535 | |
| `_is_post_review_exempt` | 12 | L13563 | |
| `_count_degraded_reviews_for_task` | 47 | L13575 | |
| `_review_text_is_degraded` | 7 | L13082 | |
| `_review_text_has_reviewer_marker` | 4 | L13089 | |
| `_review_entry_skip_reason` | 19 | L13093 | |
| `_normalize_review_conclusion` | 9 | L14522 | |
| `_extract_review_conclusion_from_text` | 17 | L14531 | |
| `_parse_unresolved_blockers_fields` | 55 | L14548 | |
| `_merge_unresolved_blocker_evidence` | 17 | L14603 | |
| `_entry_unresolved_blocker_evidence` | 18 | L14620 | |
| `_normalize_review_round` | 17 | L14638 | |
| `_is_review_evidence` | 8 | L11217 | Used by commit-scope (stays in v_w). **Cross-domain — keep.** |
| `_is_audit_or_review_type` | 4 | L11225 | Same. **Keep.** |
| `_generic_reviewer_cells` | 15 | L1374 | Used by adapter-contract checks. **Keep.** |
| `cmd_check_review_debt` | 34 | L20544 | Thin CLI wrapper. Moves with the domain. |

**Constants that move** (review-only): `DEGRADED_FUSE_THRESHOLD`, `FIX173_NAMING_NORMALIZATION_DATE`, `PRODUCT_CODE_PATTERNS` (the L13842 duplicate flagged by ArchGuard — the review-domain copy moves; the L11166 commit-scope copy stays).

**Moves**: 25 functions + 3 constants, ≈ **1,358 lines**.

**Checks affected**: Check 18 (agent-team review), Check 18b (fallback policy), Check 21 (spawn gap), Check 21b (coverage), Check 22 (review debt), Check 29 (M5 runtime), Check 30 (review closure).

### 3.4 Estimated net line-count reduction on verify_workflow.py

| Segment | Gross moved | Re-export added back | Net Δ |
|---------|------------:|--------------------:|------:|
| Evidence | 244 | ~25 | −219 |
| Risk | 130 | ~10 | −120 |
| Review | 1,358 | ~40 | −1,318 |
| **Total** | **1,732** | **~75** | **≈ −1,657** |

Projected post-extraction: **22,468 → ≈ 20,811**. This is the **honest** estimate. It does not bring verify_workflow.py below the ArchGuard `error_lines=5000` threshold in a single release — DEC-088 was explicit that ~16,000 lines of business logic cannot be compressed, only relocated, and the God Module will require multiple subsequent extraction releases (command-domain, gate-domain, context-domain, projection-domain, e2e-domain) to retire. **The 0.70.0 success criterion is "real measurable reduction + clean domain boundary + zero behavioral regression," not "ArchGuard green."**

---

## 4. Module structure

### 4.1 File layout

```
skills/software-project-governance/infra/
├── verify_workflow.py            # thin dispatch + re-export blocks (−1,657 lines)
└── checks/
    ├── __init__.py               # unchanged (0.59.0 docstring; optionally append Phase 5 note)
    ├── manifest.py               # Phase 1 (0.59.0)
    ├── capability_registry.py    # Phase 2 (0.60.0)
    ├── commit.py                 # (existing, unrelated extraction)
    ├── flow_unit_runtime*.py     # (existing)
    ├── loop_runtime_claims*.py   # (existing)
    ├── projection.py             # (existing)
    ├── version.py                # (existing)
    ├── evidence_domain.py        # NEW — Phase 5a (0.70.0)
    ├── risk_domain.py            # NEW — Phase 5b (0.70.0)
    └── review_domain.py          # NEW — Phase 5c (0.70.0)
```

Module names use the `_domain` suffix to distinguish from existing single-topic modules (`manifest.py`, `commit.py`) and to signal that each is a multi-function domain boundary, not a single check.

### 4.2 Shared utilities — explicitly out of scope

The following remain in verify_workflow.py and are reached via `_vw()`:

- **Path resolution**: `_resolve_plugin_root`, `_resolve_host_root`, `_extract_project_root_arg`, `_apply_project_root_override`, `_display_path`, `ROOT`, `_context_root`, `_context_file`, `_governance_dir` (181 lines).
- **I/O / text**: `_read_text_normalized`, `_is_plugin_path`, `_is_context_product_file`, `_read_archive_aware_governance_text` (100 lines).
- **Git**: `_git_files`, `_run_context_git`, `_context_git_toplevel`, `_is_context_git_repo_root`, `_run_git_lineage`, `_validated_git_remote_name` (100 lines).
- **Markdown-table parsers** (245 lines across 15 fns).
- **Task-ID helpers** (99 lines).

**Rationale for not extracting `_shared.py` in 0.70.0**: every consumer of these helpers except the three new domains still lives in verify_workflow.py. Moving the helpers now would force *verify_workflow.py itself* to reach them through a deferred accessor (or re-import), which is the exact re-export-shuffling anti-pattern DEC-088 prohibits. The right time to extract `_shared.py` is **after** the next 2–3 domain extractions, when the consumers are genuinely distributed across modules. Phase 1/2 established this discipline explicitly (manifest.py docstring lines 6–12).

### 4.3 Import graph

```
                    ┌──────────────────────────┐
                    │  verify_workflow.py      │
                    │  (thin dispatch + CLI)   │
                    └───────────┬──────────────┘
              top-level import  │  (load time)
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ evidence_domain   │  │ risk_domain       │  │ review_domain     │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                       │                       │
          │  deferred _vw() — lazy, called inside fn bodies only
          ▼                       ▼                       ▼
      ┌───────────────────────────────────────────────────────┐
      │  verify_workflow.py shared helpers (path / git /      │
      │  markdown / task-id / GovernanceDataSource /          │
      │  parse_open_risks's dependencies, etc.)               │
      └───────────────────────────────────────────────────────┘
```

**Critical invariant**: the new modules never `import verify_workflow` at module top level. They use the cached `_vw()` accessor inside function bodies. This is what breaks the load-time cycle (verify_workflow imports the domain module first; the domain module reaches back only when a check actually runs). REVIEW-FIX-153 P2 validated this for Phase 1; Phase 2 (capability_registry) replicated it after a top-level import was found to deadlock during initialization.

**Cross-domain references between the three new modules** (e.g. review_domain calling `parse_evidence_task_ids`): these go through `_vw()` to reach the re-exported symbol in verify_workflow.py, **not** directly via `from checks.evidence_domain import ...`. Rationale: a direct cross-domain import recreates an inter-module cycle (review_domain → evidence_domain → v_w → review_domain) and couples release cadence. The single source of truth remains v_w's re-export; once `_shared.py` lands in a future release, the indirection collapses to a direct import.

---

## 5. Extraction strategy

### 5.1 Per-domain procedure (replicated 3×)

1. **Snapshot baseline.** Run `python verify_workflow.py check-architecture-health` and `python verify_workflow.py check-governance` before any change; save outputs to `docs/release/0.70.0/baseline-*.txt`. Run `pytest skills/software-project-governance/infra/tests/` and capture pass/fail counts.
2. **Create the new module.** Copy the Phase 1/2 module header template, scoped to this domain. Add the `_vw()` deferred-accessor block + thin wrappers for every shared helper the domain reaches.
3. **Move functions** verbatim (byte-identical bodies). Move domain-only constants with them. Do **not** edit logic.
4. **Add the thin re-export block** at the top of verify_workflow.py, mirroring the `from checks.manifest import (...)` block (L999–L1012). One symbol per line, sorted.
5. **Delete the original definitions** from verify_workflow.py. This is the step that makes the extraction real (DEC-088).
6. **Run the verification gauntlet** (Section 7.2). Any diff in output is a regression — investigate before proceeding.

### 5.2 Thin dispatch (CLI)

`cmd_check_review_debt` (L20544, 34 lines) moves with the review domain; the `argparse` subparser entry in `main()` (L22423 dispatch table `"check-review-debt": cmd_check_review_debt`) now resolves through the re-export — no change to the CLI surface. Same for any per-domain cmd.

For the inline Check blocks inside `cmd_check_governance` (L15131–L16349): these **do not** move in 0.70.0. They call the now-extracted functions (`check_evidence_completeness`, `check_risk_staleness`, `check_m5_compliance`, `check_review_closure`, etc.) through the re-export, so they continue to work byte-for-byte. Moving the print-blocks themselves is the cancelled DEC-088 Step B and is explicitly **out of scope**.

### 5.3 No behavioral change

Contract preserved:

- Same CLI flags, same `argparse` subcommands, same `main()` dispatch keys.
- Same stdout format (the `┌─ Check N: ... ──┐` blocks render byte-identically because the rendering code in `cmd_check_governance` is untouched).
- Same exit codes (0 = clean, 1 = issues found).
- Same fixture outputs (Check 29/30 fixture tests in `test_verify_rel063_evidence.py` and the FIX21-* / FIX29-* suites must pass unchanged).

### 5.4 Test preservation

- `import verify_workflow as vw; vw.check_X()` — **unchanged**. The re-export makes the symbol resolve to the same callable.
- `from checks.X import ...` — only `checks.flow_unit_runtime` is imported by tests today; no test imports the three new modules directly. No test path update is **required** for 0.70.0.
- Optional (reviewer-discretion): add one smoke test per new module that imports the module directly and asserts the public check function is callable. This guards against future re-export drift. ~15 lines per domain.

---

## 6. DEC-088 compliance

| DEC-088 requirement | How 0.70.0 satisfies it |
|---|---|
| **Real extraction** — functions MOVE; main file line count drops. | §3.4: net −1,657 lines. Each moved function is physically deleted from verify_workflow.py. |
| **No re-export disguised as extraction.** | The re-export blocks at the top of v_w are **thin** (≈75 lines total across 3 domains, ~1 line per symbol). The bulk of the code (function bodies, constants) lives in the new modules. This is the Phase 1/2 ratio (manifest re-export = 14 lines for 401 moved; capability_registry = 12 lines for 304 moved) and is explicitly endorsed by DEC-088 ("现有 Phase 1/2 保留有效"). |
| **Data-driven, not arbitrary.** | Boundaries are derived from `cmd_check_governance` dispatch blocks (Check 1/2/6/8/18/21/22/29/30) and cross-checked against symbol-name semantics. Functions were classified KEEP if they had any cross-domain caller (§3.1, §3.2, §3.3). |
| **Projection single source of truth.** | Each moved symbol has exactly one canonical definition — in the new module. v_w's re-export points at it; it does not duplicate it. `check-duplicate-code` must report one fewer `PRODUCT_CODE_PATTERNS` duplicate (the L13842 copy moves to review_domain). |
| **Business logic is irreducible.** | This ADR does **not** promise to collapse `cmd_check_governance` or to drop v_w below ArchGuard's error threshold. It promises to relocate 3 coherent domains and to leave the irreducible remainder for subsequent releases. |

---

## 7. Risk + regression

### 7.1 Risk inventory

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Import cycle deadlock at startup (top-level `import verify_workflow` in a new module). | Medium (happened in Phase 2). | High — every CLI command breaks. | Mandatory `_vw()` deferred-accessor pattern; smoke test `python verify_workflow.py --help` after each domain. |
| Hidden cross-domain caller of a "moved" function — NameError at runtime. | Medium. | Medium — surfaces only when an affected Check runs. | Pre-flight `grep -rn "<fn_name>"` across `infra/` for every moved symbol; classify as KEEP if any non-domain caller exists. |
| Behavioral drift from copy-paste (e.g. dropped `global`, missing decorator). | Low. | Medium. | Byte-diff the moved function against the pre-extraction snapshot. |
| `cmd_check_governance` output diff (whitespace, ordering). | Low. | High (breaks fixture tests). | §7.2 gauntlet step (c). |
| ArchGuard `duplicate_constant` for `PRODUCT_CODE_PATTERNS` persists if a stale copy is left behind. | Medium. | Low (advisory only — `fatal_on_error=false`). | Delete the L13842 copy; verify the duplicate disappears from the post-extraction ArchGuard output. |
| Test breakage from `vw.check_X` resolution. | Very low. | High. | Re-export block mirrors Phase 1/2 exactly. |
| New module triggers `module_size` WARN/ERROR on its own (review_domain ≈ 1,400 lines > warn=2000? — no, under). | Low. | Low. | review_domain lands at ~1,400 lines, under `warn_lines=2000`. No new ERROR introduced. |

### 7.2 Verification gauntlet (run after each domain; full run before REL-062)

1. `python skills/software-project-governance/infra/verify_workflow.py --help` — must exit 0 (smoke).
2. `py_compile` on verify_workflow.py and all three new modules.
3. `python verify_workflow.py check-governance` — **byte-diff against pre-extraction baseline** (`diff` of stdout). Zero diff required.
4. `python verify_workflow.py check-architecture-health` — confirm: (a) verify_workflow.py line count dropped by the expected delta, (b) the `PRODUCT_CODE_PATTERNS` duplicate at L13842 is gone, (c) no new ERROR/WARN introduced on the new modules.
5. `python verify_workflow.py check-projection-sync` — no new drift.
6. `python verify_workflow.py check-duplicate-code` — duplicate_constant count decreases by ≥1.
7. `pytest skills/software-project-governance/infra/tests/ -q` — all 1,385 tests pass (626 in `test_verify_workflow.py` + 759 across other files). Particularly: `TestCheckAgentTeamReview` (FIX-18*), `test_verify_rel063_evidence.py` (FIX-29/30 fixture suite), and the evidence-completeness / risk-staleness tests at L8828–L8936.
8. `python verify_workflow.py check-release-readiness --version 0.70.0` + `check-release-lineage` — REL-062 acceptance.

### 7.3 Rollback

Each domain extraction is one commit. If gauntlet step 3 or 7 fails, `git revert <commit>` returns to the pre-extraction state with no migration step (the new module file simply becomes unused and can be deleted). No data migration, no schema change, no breaking CLI — rollback is trivial.

### 7.4 Effort estimate

| Activity | Effort |
|---|---|
| Baseline capture + gauntlet tooling | 0.5 day |
| Evidence domain (move + re-export + gauntlet) | 0.5 day |
| Risk domain | 0.25 day |
| Review domain (largest; M5/closure state-machine care required) | 1.5 days |
| Test additions (smoke per domain, optional) | 0.25 day |
| Full REL-062 gauntlet + release docs | 0.5 day |
| **Total** | **≈ 3.5 days** |

Review domain dominates because `check_m5_compliance` (221) and `check_review_closure` (206) carry subtle invariants (DEC-094 §3.3 fuse, FIX-173 naming-normalization exemption, FIX-178 session-snapshot exclusion) that must be preserved byte-for-byte.

---

## 8. REL-062 acceptance criteria

The release is acceptable when **all** of the following hold:

1. **Real extraction** — `wc -l skills/software-project-governance/infra/verify_workflow.py` decreased by ≥ 1,500 lines (target ≈ 1,657). The three new modules exist and contain the moved function bodies.
2. **No behavioral change** — `check-governance` stdout is byte-identical to the 0.69.0 baseline.
3. **Test suite green** — all 1,385 tests pass without modification.
4. **Architecture health** — `check-architecture-health` reports: (a) verify_workflow.py line count down, (b) the `PRODUCT_CODE_PATTERNS` L13842 duplicate resolved, (c) no new ERROR/WARN on the three new modules.
5. **Projection single source** — `check-duplicate-code` does not report a duplicate between verify_workflow.py and any new module (the re-export is import-only, not a copy).
6. **CLI contract intact** — all 54 subcommands still resolve; `python verify_workflow.py <cmd>` works for every cmd in the 0.69.0 dispatch table.
7. **Release lineage** — `check-release-lineage --version 0.70.0` PASS; `check-projection-sync` PASS; ArchGuard `fatal_on_error=false` is unchanged (no threshold tightening under release pressure — that would be gaming the metric).
8. **DEC-088 SoD** — implementation follows DEC-090/091 downgraded separation-of-duties (Coordinator/Developer writes, independent Reviewer reviews), matching Phase 1/2 (DEC-086/087) and 0.63.0 (FIX-173/174).

---

## 9. Out of scope (explicit non-goals for 0.70.0)

- Extracting `_shared.py` (path/git/markdown/task-id helpers). Deferred until consumers are distributed.
- Collapsing `cmd_check_governance` print blocks into a table-driven renderer (cancelled DEC-088 Step B).
- Splitting any other domain (command, gate, context, projection, e2e, adapter-contract, lifecycle, loop-runtime, release). Each warrants its own release.
- Renaming or renumbering CLI subcommands (DEC-082 deferred command-surface work indefinitely).
- Tightening ArchGuard thresholds. The error threshold stays at 5000; verify_workflow.py will still ERROR post-0.70.0, and that is the intended "倒逼质量" pressure for the *next* extraction release.
- Closing RISK-039. One more extraction release does not satisfy "external host-project validation."

---

## 10. Key decisions summary

- **Three new modules**: `infra/checks/evidence_domain.py`, `infra/checks/risk_domain.py`, `infra/checks/review_domain.py`.
- **Pattern**: Phase 1/2 deferred-`_vw()` accessor + thin `from checks.X import (...)` re-export. No new architectural mechanism invented.
- **What moves**: 11 evidence fns (244 ln), 4 risk fns (130 ln), 25 review fns + 3 constants (1,358 ln). Total gross 1,732 lines.
- **What stays**: any function with a cross-domain caller (`_count_evidence_rows`, `_risk_status_is_closed`, `_evidence_task_type_index`, `_is_review_evidence`, etc.) — reached via `_vw()`.
- **Projected verify_workflow.py size**: 22,468 → ≈ 20,811 lines (−1,657 net).
- **Effort**: ≈ 3.5 days (review domain dominates).
- **Success bar**: real line reduction + zero behavioral regression + REL-062 gauntlet green. Not "ArchGuard green."
