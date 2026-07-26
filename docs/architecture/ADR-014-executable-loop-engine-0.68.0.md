# ADR-014: Executable Loop Engine 0.68.0 — Persistent PARO State Machine, Production Gate Back-Edge/Fuse, Restart-Safe Event Log

- Status: PROPOSED / READY_FOR_DESIGN_REVIEW
- Date: 2026-07-23
- Version scope: 0.68.0
- Tasks: FEAT-005 (persistent Plan-Act-Observe-Reflect state machine), FEAT-006 (production gate back-edge/round/fuse/escalation), FEAT-007 (restart-safe event log + dependency blocking + executable WIP)
- Release: REL-060 (0.68.0 — Executable loop engine)
- Authority: DEC-104, AUDIT-133 / EVD-707, RISK-037, RISK-042, `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` (R1 APPROVED — the PARO/back-edge/fuse design this activates), ADR-013 (0.67.0 Loop Runtime Contract v2 — the foundation this builds on)
- Review authority required: independent Design Review (REVIEW-FEAT-005~007-DESIGN-R0 chain or the Coordinator's designated reviewer); this ADR is design-only and does not self-approve any FEAT task
- Reversibility: all 0.68.0 surfaces are additive modules and a new event-log file; the 0.67.0 v2 contract and v1 visibility validator are preserved unchanged; RISK-037/RISK-042 remain open until 0.69.0 external validation

> **Design-only ADR.** This document specifies the executable Loop Engine — the persistent PARO state machine, the production gate/fuse terminal processor, and the restart-safe event log — for 0.68.0. It is written by the Architect role for Design Reviewer review. It does not implement code, does not dispatch a Developer, and does not authorize a release. Each of FEAT-005, FEAT-006, FEAT-007 requires its own DEC + Developer + Code Reviewer + QA cycle per the governance workflow. No-overclaim discipline: 0.68.0 activates the execution engine but does NOT close RISK-037/RISK-042 (those need 0.69.0 dogfood + 2 external project-type validation) and does NOT claim 1.0.0.

<!-- loop-runtime-target:{"claim_id":"LRC-EXEC-PLANNED-001","target_version":"0.68.0","status":"planned_not_active"} -->
> The executable PARO state machine, production gate back-edge/round/fuse/escalation, and restart-safe event log described here are planned-not-active until FEAT-005~007 are implemented, independently reviewed, and REL-060 passes. This ADR is the design; it activates nothing by being written.

---

## 1. Context

### 1.1 DEC-104 roadmap (the binding plan)

DEC-104 (2026-07-11, decision-log row) adopted a runtime-first repair roadmap for Loop Engineering after AUDIT-133 proved the 0.65.0 implementation was schema-only. The version chain:

- **0.66.1–0.66.3** — fail-closed containment + release-incident recovery only.
- **0.67.0 (committed/released)** — canonical versioned Loop Runtime Contract (`runtime-contract/v2`) + single shared migration planner + decomposition confirmation (FEAT-002~004). Units are written **dormant** (`runtime_status: "dormant"`, `active_loop: false`). This is the foundation.
- **0.68.0 (this ADR)** — persistent PARO state machine + production gate back-edge/fuse/escalation + restart-safe event log (FEAT-005~007). **The execution engine.**
- **0.69.0** — production telemetry + dogfood + two external project-type validation (FEAT-008, VAL-008/VAL-009).
- **0.70.0** — verify_workflow Phase 5 extraction (deferred).

0.68.0 is the version that makes Loop Engineering **actually execute** in production — wiring the 0.67.0 contract (schema v2) + planner + dormant decomposition to a real execution path.

### 1.2 AUDIT-133 findings (the problem this ADR solves)

AUDIT-133 (EVD-707) found, against the real code:

> **核心 loop transition API 生产调用点 = 0** — the loop engine exists as schema/tests but nothing in production calls it.

The four FX-189 loop APIs — `derive_round`, `fuse_decision`, `escalation_payload`, `activate_loop_state` (all in `infra/loop_engine.py`) — have **zero production call sites**. The only invocations are standalone CLIs (`cmd_loop_rollup`, `cmd_check_loop_health`) which are read-only views, not execution. Concretely, today:

- A real code-review returning `NEEDS_CHANGE` on a flow unit **does not** drive `reflect→plan`, does **not** increment `loop_state.loop_count`, does **not** record a back-edge, and does **not** consult the fuse. The task-level review-loop fuse (M7.4 §4.6, Check 30) fires at the *task* level, but the *flow-unit / loop-tier* fuse — the one the registry declares per tier (`FUSE-INNER-DEFAULT`, etc.) — is never consulted in any production path.
- A fuse tripped in the registry semantics (`loop_fuses.*.max_rounds`) does **not** block any release or governance gate. RISK-042's closure standard states this verbatim: *"gate fail/back-edge/fuse/Plan-Act-Observe-Reflect 不会在生产路径执行"*.
- Process restart loses any in-flight loop state because loop state is derived statelessly from the evidence log (`derive_round`) rather than persisted per-unit with a version; there is no CAS, no event log, no multi-process write coordination.

**0.68.0 must make the loop engine EXECUTE on real production events, not just exist as schema.** This is the single load-bearing requirement of REL-060.

### 1.3 The 0.67.0 foundation (what is now committed)

ADR-013 / 0.67.0 delivered (now released as `v0.67.0`, tag `b183ca6`):

- **`core/loop-runtime-contract.json`** (schema v2) — the single source of truth for the runtime payload shape. Declares: `allowed_agent_phases: [plan, act, observe, reflect]`; `allowed_runtime_statuses: [active, dormant, blocked, withdrawn]`; `allowed_gate_statuses: [pending, in-progress, passed, failed, blocked, escalated, withdrawn]`; the 9-field `loop_state` (incl. `agent_phase`, `loop_count`, `fuse{max_rounds, tripped}`, `last_gate_result`); `gate_state` (`{status, gate_id, last_result, evidence_refs}`); and the unification invariant `loop_state.last_gate_result == gate_state.last_result`.
- **`infra/checks/flow_unit_runtime_v2.py`** (`validate_flow_unit_runtime_payload_v2`) — the v2 validator. It enforces field presence/types/enums, the unification invariant, the `runtime_status ⇔ active_loop` bidirectional implication, the `example-fixture` guard, and `decomposition_confirmed == true`. It does **not** yet enforce PARO transition legality or CAS — those are FEAT-005.
- **`infra/loop_migration_plan.py`** (`build_migration_plan`, `confirm_decomposition`, `plan_to_payload`) — the pure planner. `plan_to_payload` writes units `dormant` with `agent_phase: "plan"`, `loop_count: 0`, `gate_state.status: "pending"`, `fuse.tripped: false`. The planner is pure and frozen for 0.68.0 (it activates nothing).
- **`infra/loop_engine.py`** — carries the four schema-only APIs plus `rollup_loop_state` (a pure read). `derive_round` is the SACRED pure function (parallel-safe, stateless, derives round from evidence-log `LOOP-{U}-{T}-R{n}` rows). `fuse_decision` combines `derive_round` + the registry fuse. `escalation_payload` builds the 4-option AskUserQuestion. None is wired to production.

The 0.67.0 contract explicitly deferred the execution engine to 0.68.0: its `no_overclaim_boundary_mandatory_tokens` include *"does not activate execution engine"*, and the contract carries `fuse{max_rounds, tripped}` fields ready for FEAT-005/006 to populate.

### 1.4 The registry semantics FEAT-006 must consume (already declared, dormant)

`core/loop-engineering-registry.json` already declares everything FEAT-006 needs:

- **`loop_gate_semantics`** — for each G1-G11: `loop_role` (`loop-setup` / `loop-body` / `loop-entry-gate` / `loop-exit-gate`), `enclosing_loop` (`none` / `setup` / `inner` / `middle` / `outer`), `on_fail` (`iterate-enclosing-loop` / `escalate-directly`), `fuse_ref` (e.g. `FUSE-INNER-DEFAULT`). This is the mapping from a gate result to its loop's iterate-vs-escalate decision.
- **`loop_fuses`** — per tier `max_rounds`: `FUSE-SETUP-DEFAULT` (2), `FUSE-INNER-DEFAULT` (5), `FUSE-MIDDLE-DEFAULT` (3), `FUSE-OUTER-DEFAULT` (2), each with `escalation_exit`. These are the thresholds FEAT-006 trips.
- **`pause_points`** — `PP-Fuse-Escalate` ("when loop fuse trips (MAX_ROUNDS exceeded)", `active: true`) — the mandatory human pause point on fuse trip.
- **`back_edges`** — `release-to-design-replan` (`auto_fire: false`, three conjunctive conditions incl. PP-Fuse-Escalate human approval) — the one cross-Middle-loop back-edge that requires human authorization.

These are **declarations**; FEAT-006 is the code that reads them and acts. No registry change is required for 0.68.0.

### 1.5 The production wiring gap (the AUDIT-133 "call sites = 0" fix)

The production gate path today (in `infra/verify_workflow.py`):

- **Review skills** (`code-review`, `design-review`, etc.) produce conclusions: `APPROVED` / `APPROVED_WITH_NOTES` / `NEEDS_CHANGE` / `BLOCKED`, recorded in `review-{role}-{id}-R{n}.md` files and the evidence log.
- **The task-level review-loop state machine** (Check 30, ~lines 14476–14862): `NEEDS_CHANGE` is non-terminal; `APPROVED`/`BLOCKED` are terminal; a fuse escalates `NEEDS_CHANGE` at `R{max_round}` to `BLOCKED`. This is the *proven, sacred* loop pattern (M7.4 §4.6) — but it operates at **task** granularity, not flow-unit/loop-tier granularity.
- **`check_release_readiness`** (~line 6387) + `run_release_execution_gates` — the release gate path. A blocking finding here fails the release.

**Nothing in this path calls `loop_engine` functions on flow-unit events.** A code-review `NEEDS_CHANGE` on flow unit `shitu.story.Skeleton` does not touch that unit's `loop_state`. FEAT-006's job is to install a **gate/review terminal processor** that consumes each flow-unit gate result and drives the PARO state machine — and to install a **system-level fuse block** in the release/governance gate so a tripped fuse blocks the release *without relying on Coordinator self-discipline*.

### 1.6 The RISK-039 / thin-entry constraint (where new logic lives)

`verify_workflow.py` is ~22.3k lines (RISK-039 God Module; ArchGuard guards its size). DEC-083's split discipline mandates: **no new logic in `verify_workflow.py`** — only thin `cmd_*` entries (≤20 lines, argparse glue + delegation). All 0.68.0 execution logic lives in **new `infra/loop_*` modules**; `verify_workflow.py` gets only thin delegating entries that invoke the loop engine, plus the one system-level fuse check wired into the existing release/governance gate path (an *invocation*, not new logic).

---

## 2. Decision

Adopt three coordinated, strictly-additive changes for 0.68.0, sequenced **FEAT-005 → FEAT-006 → FEAT-007** (state machine → gate/fuse consumes state machine → event log/persistence wraps both):

1. **FEAT-005 — Persistent PARO state machine.** Define the legal Plan-Act-Observe-Reflect transitions over `loop_state.agent_phase`, persisted per-unit to `flow-unit-runtime.json` with a **monotonic CAS version** (`loop_state.cas_version`, new field). Real action/review/gate events drive phase transitions through a pure transition-validator + a CAS-guarded writer. Process restart recovers state by re-reading the persisted per-unit `agent_phase` + `cas_version`; the event log (FEAT-007) is the replayable audit trail.

2. **FEAT-006 — Production gate back-edge/round/fuse/escalation.** A **gate/review terminal processor** (new module `infra/loop_gate_processor.py`) consumes a flow-unit gate result, reads the registry's `loop_gate_semantics` + `loop_fuses`, and atomically records the back-edge (reflect→plan) + increments `loop_state.loop_count` + appends a `gate_result` event. When `loop_count > fuse.max_rounds` it trips the fuse: sets `fuse.tripped: true`, `runtime_status: "blocked"` (or `"escalated"`), and emits a human escalation. A **system-level fuse block** is installed in the release/governance gate path (a query, not new logic): any unit with `fuse.tripped == true` that has not been resolved blocks the release/gate. This does NOT rely on Coordinator self-discipline — it is enforced by `check-release` / Check 28.

3. **FEAT-007 — Restart-safe event log + dependency blocking + executable WIP.** A new **append-only event log** (`.governance/loop-event-log.jsonl`, JSONL — one event per line) records every state mutation as `{timestamp, unit_id, event_type, payload, cas_version, actor}`. Multi-process writes are safe via per-unit CAS on `flow-unit-runtime.json` (read-modify-write with version check, atomic temp-file+rename) **plus** append-only JSONL (concurrent appends don't lose because each line is self-contained and carries the `cas_version` it transitioned from). **Dependency blocking** (admission control): a unit cannot enter `act` until every unit in its `dependencies` has `gate_state.status == "passed"`. **WIP budget**: max concurrent `active` units per tier/lane, enforced at admission (deny → unit stays `dormant`/`blocked`).

These three make the loop engine **execute on real production gate events**, recover from restart, coordinate across processes, and block at the fuse — the exact REL-060 acceptance.

None closes RISK-037/RISK-042 (external validation is 0.69.0). None modifies the 0.67.0 v2 contract's *field set* (only adds `cas_version` to `loop_state`, a forward-compatible additive field) or the v1 validator (frozen). None claims 1.0.0.

---

## 3. PARO State Machine Spec (FEAT-005)

### 3.1 The four phases (already in the v2 contract)

The v2 contract declares `allowed_agent_phases: [plan, act, observe, reflect]`. These are the four PARO phases (architecture ADR §3.4, §5.1). Per-unit, the current phase is `loop_state.agent_phase`. FEAT-005 makes phase transitions **legal-transition-constrained** and **CAS-persisted**.

### 3.2 Legal transitions (the state machine)

The state machine has 6 legal forward transitions and 3 terminal outcomes. Illegal transitions are rejected by the transition validator (FEAT-005 returns a failure; the writer does not mutate state).

```
                    ┌─────────────────────────────────────────────────┐
                    │                                                 ▼
   (entry) ──▶  plan ──▶ act ──▶ observe ──▶ reflect ──┬──▶ plan   (iteration / back-edge; loop_count++)
        •          │                              │    │
        •          │                              │    ├──▶ exit    (gate passed → loop exits for this unit/tier)
        •          │                              │    │
        •          │                              │    └──▶ escalate (fuse tripped → runtime_status: blocked/escalated)
        •          │                              │
                    └──────────────────────────────┘
   (terminal outcomes: exit | escalate | withdrawn)
```

**The transition table** (the executable spec):

| From | To | Triggering event | Side effect on loop_state | Recorded event type |
|------|----|------------------|---------------------------|---------------------|
| (entry) | `plan` | unit activated (`runtime_status: dormant→active`) | `agent_phase: plan`, `loop_count: 0`, `fuse.tripped: false` | `phase_enter` |
| `plan` | `act` | plan accepted (optionally PP-Plan-Approve passed) | `agent_phase: act` | `phase_transition` |
| `act` | `observe` | action complete; observation recorded as evidence | `agent_phase: observe` | `phase_transition` |
| `observe` | `reflect` | review result recorded (`gate_state.last_result` set) | `agent_phase: reflect` | `phase_transition` + `gate_result` |
| `reflect` | `plan` | gate **failed** AND `loop_count < fuse.max_rounds` (iterate) | `agent_phase: plan`, **`loop_count += 1`**, `last_gate_result`/`gate_state.last_result` = failed result | **`back_edge`** + `gate_result` |
| `reflect` | (exit) | gate **passed** | `gate_state.status: passed`, `agent_phase` terminal (stays `reflect` or `null`) | `gate_result` + `loop_exit` |
| `reflect` | `escalate` | gate **failed** AND `loop_count >= fuse.max_rounds` (fuse trip) | `fuse.tripped: true`, `runtime_status: blocked` (or `escalated`) | **`fuse_trip`** + `gate_result` |
| `*` | `withdrawn` | operator withdraws unit | `runtime_status: withdrawn`, `gate_state.status: withdrawn` | `unit_withdrawn` |

**Three rules that make this safe and faithful to the sacred M7.4 §4.6 pattern:**

1. **`NEEDS_CHANGE`/`failed` is non-terminal.** It always drives `reflect→plan` (iterate) unless the fuse trips. There is no "reluctant APPROVED at round N+1" (C5 preserved). `APPROVED`/`passed` is terminal (`exit`). `BLOCKED` is terminal only via fuse trip (`escalate`) or operator withdraw.
2. **The fuse boundary is `loop_count > fuse.max_rounds`** (matching `loop_engine.fuse_decision`: round `1..M` iterate, `M+1` escalates; round == max is STILL iterate). `loop_count` is incremented **atomically with** the back-edge (FEAT-006), never separately — so the count and the back-edge cannot diverge.
3. **The fuse counts per unit per tier.** `loop_count` lives on `loop_state` (per-unit); the tier is `loop_state.active_loop_tier`; the threshold comes from the registry fuse for that tier. A unit iterating its Inner loop does not deplete its Middle-loop fuse budget — they are distinct `loop_state` instances (a unit activates one tier at a time).

### 3.3 The CAS mechanism (optimistic locking, per-unit)

Each unit in `flow-unit-runtime.json` gains one new forward-compatible field on `loop_state`:

```json
"loop_state": {
  "active_loop": true,
  "active_loop_tier": "inner",
  "loop_count": 2,
  "last_loop_type": "defect-rework",
  "agent_phase": "reflect",
  "iteration_within_inner": 2,
  "pause_points_active": ["PP-Reflect-SelfReview"],
  "last_gate_result": "NEEDS_CHANGE",
  "fuse": {"max_rounds": 5, "tripped": false},
  "cas_version": 7          // ← NEW (FEAT-005). Monotonic non-negative int; 0 at activation.
}
```

**CAS protocol** (every transition writer follows this exactly):

```
1. READ   unit = load flow-unit-runtime.json → flow_units[id]
          expected_version = unit.loop_state.cas_version
          from_phase       = unit.loop_state.agent_phase
2. VALIDATE  transition (from_phase, to_phase, event) is legal (§3.2 table); else FAIL (no write)
3. COMPUTE   new_unit = apply side effects (new agent_phase, loop_count±, gate_state, fuse, …)
             new_unit.loop_state.cas_version = expected_version + 1
4. WRITE  (atomic):
             re-read on-disk file; if on-disk cas_version != expected_version → CONFLICT
                (another process advanced this unit; retry from step 1, or fail-closed)
             else: write file via temp-file + os.replace (atomic rename), append event to JSONL log
5. EMIT   event {unit_id, event_type, payload, cas_version: expected_version+1, from_version: expected_version, …}
```

**Why CAS over file-locking:** CAS (optimistic locking) is conflict-serializable without holding a lock across the compute step, which is important because the compute (registry reads, fuse evaluation, escalation generation) is non-trivial. Conflicts are expected to be rare (loop events on one unit are usually driven by one agent at a time); on conflict the writer retries the read-validate-compute with the fresh version. The atomic temp-file+`os.replace` write (already the 0.66.1 transaction discipline) ensures a reader never sees a half-written file. The JSONL append (FEAT-007) is independently safe because each line is self-contained and carries both `from_version` and `cas_version`, so a concurrent append can never corrupt another event's meaning.

**`cas_version` is forward-compatible and additive.** The 0.67.0 v2 validator does not know about it; FEAT-005 extends the validator (§3.6) to require it on `active` units and tolerate its absence on `dormant` units (dormant units are write-once at migration; they have no transitions to version). A 0.67.0 payload with `cas_version` absent still validates under the *0.67.0* validator (the field is optional in v2.0); the 0.68.0 *extended* validator requires it on active units. This is the same additive discipline as `schema_version: 2.0 → 2.1` (ADR-013 §3.7) — but we do **not** bump the contract `schema_version` for `cas_version`; we treat it as a per-unit optional field that FEAT-005 populates and FEAT-005's validator branch enforces on active units. (See §9.2 for the precise validator-extension discipline; the contract `schema_version` stays `"2.0"` and the existing 0.67.0 validator is preserved.)

### 3.4 Per-unit state persistence (two stores, one truth)

| Store | File | Role | Mutability |
|-------|------|------|------------|
| **Current-state (working set)** | `.governance/flow-unit-runtime.json` (v2, from 0.67.0) | The authoritative per-unit current `agent_phase`, `loop_count`, `gate_state`, `fuse`, `cas_version`. Every transition reads + writes this. | CAS-guarded read-modify-write (§3.3). |
| **Event log (audit/replay trail)** | `.governance/loop-event-log.jsonl` (NEW, FEAT-007) | Append-only history of every transition. Used for replay, restart recovery verification, and DORA/telemetry (0.69.0). | Append-only; never rewritten except archival rotation. |

`flow-unit-runtime.json` is the **truth** for "what phase is this unit in right now." The event log is the **history** that produced it. On any divergence, the current-state file wins for operational decisions; the event log is the auditable record. Restart recovery (§3.5) re-reads the current-state file — the event log is consulted only to verify consistency and to repopulate any in-memory caches.

### 3.5 Process restart recovery

Restart recovery is **read-based**, not replay-based, by design:

1. On startup, the loop engine loads `flow-unit-runtime.json` → for each `active` unit, `agent_phase`, `loop_count`, `fuse`, `cas_version` are the recovered state. No replay needed — the current-state file IS the recovered state.
2. The engine verifies consistency against the event log: the last event for each unit should have `cas_version == on-disk cas_version`. If the on-disk version is **ahead** of the last logged event (a write committed to the state file but the event append was lost — should not happen given atomic ordering, but defensive), the state file is trusted and a synthetic `phase_recovery` event is appended to close the gap. If the last logged event is **ahead** of the on-disk version (a state write was lost — the dangerous case), the engine fail-closes that unit to `runtime_status: blocked` with a `recovery_conflict` event and surfaces it; it does **not** silently replay, because replaying a transition whose side effects (e.g. an external action) may have partially occurred is unsafe.
3. In-flight transitions interrupted mid-write: because the state write is atomic (temp-file + `os.replace`), a crash leaves either the pre-transition or post-transition state — never a torn state. The `cas_version` bump is part of the same atomic write, so a restart sees a consistent (phase, version) pair.

**The CAS version is what makes restart safe without a lock daemon.** Two processes that both read `cas_version=7` and both try to write: the second's write sees on-disk `cas_version=8` (the first committed) and fails the conflict check — it retries or fail-closes. No lost updates.

### 3.6 Validator extension (FEAT-005 adds transition + CAS rules)

`infra/checks/flow_unit_runtime_v2.py` gains a **new validation pass** (additive; the existing 0.67.0 checks remain byte-identical):

- **`cas_version` presence**: required on `active` units; optional on `dormant`/`withdrawn` units. Must be a non-negative integer (not bool).
- **`cas_version` monotonicity on the event log** (FEAT-007): for each unit, the sequence of `cas_version` values in the event log must be strictly monotonic by +1; a gap or regression is a validation failure.
- **Phase legality** (the §3.2 table): given the event log for a unit, the sequence of `agent_phase` values must follow legal transitions. An illegal jump (e.g. `plan → observe` skipping `act`) is a validation failure. This is checked by replaying the event log, not by inspecting the current-state file alone (the current file holds only the current phase; legality is a property of the *history*).
- **Unification preserved**: `loop_state.last_gate_result == gate_state.last_result` (the 0.67.0 invariant) is re-asserted after every transition; FEAT-005 never writes one without the other.

The 0.67.0 validator entry point (`validate_flow_unit_runtime_payload_v2`) is preserved; the new rules are an additional function (`validate_loop_runtime_v2_with_transitions`) that the 0.68.0 writer and the release gate call. A payload that passes 0.67.0 validation but lacks `cas_version` on an active unit fails 0.68.0 validation — this is the executable guard that an activated unit has a real CAS-guarded state.

---

## 4. Gate Back-Edge/Round/Fuse/Escalation Spec (FEAT-006)

### 4.1 The gate/review terminal processor (the AUDIT-133 fix)

FEAT-006's core is a new module:

```
skills/software-project-governance/infra/loop_gate_processor.py
```

It exposes one primary entry point:

```python
def process_gate_result(
    unit_id,               # the flow_unit_id whose gate ran
    gate_id,               # G1..G11 (the gate that produced the result)
    result,                # "passed" | "failed" | "blocked" | ... (mapped from review conclusion)
    *,
    evidence_ref,          # pointer to the review/gate evidence (review-*.md path or evidence-log row)
    actor,                 # who/what produced this (reviewer id, agent id, gate engine)
    root=None,             # host project root (RISK-040: via resolve_entry)
    plugin_home=None,      # registry override
) -> GateOutcome:
    ...
```

`GateOutcome` is a frozen dataclass: `{unit_id, decision: "iterate"|"exit"|"escalate", new_agent_phase, new_loop_count, fuse_tripped: bool, escalation_payload: dict|None, cas_version, events: list}`.

**The algorithm (consumes registry semantics, drives the state machine):**

```
1. LOAD   unit = flow-unit-runtime.json → flow_units[unit_id]  (CAS read; §3.3)
         assert unit.runtime_status == "active"  (dormant units have no gate events; FEAT-005 activation first)
2. LOOKUP gate_semantics = registry.loop_gate_semantics[gate_id]
         tier       = gate_semantics.enclosing_loop        # the loop this gate certifies
         on_fail    = gate_semantics.on_fail               # iterate-enclosing-loop | escalate-directly
         fuse_ref   = gate_semantics.fuse_ref              # FUSE-INNER-DEFAULT | ...
         fuse       = registry.loop_fuses[fuse_ref]        # {max_rounds, escalation_exit}
3. MAP   result → {passed, failed, blocked}
         (APPROVED/APPROVED_WITH_NOTES → passed; NEEDS_CHANGE/failed → failed; BLOCKED → blocked)
4. UNIFY set unit.gate_state.last_result = result
         set unit.loop_state.last_gate_result = result     # the 0.67.0 unification invariant
         set unit.gate_state.status = result-as-gate-status (passed→passed, failed→failed, blocked→blocked)
         append unit.gate_state.evidence_ref = evidence_ref
5. DECIDE
   if result == "passed":
       decision = "exit"
       unit.gate_state.status = "passed"
       unit.loop_state.agent_phase = "reflect" (terminal; loop exits this tier)
       → emit gate_result + loop_exit events
   elif result == "blocked" (operator/gate BLOCKED, not fuse):
       decision = "escalate"
       unit.runtime_status = "blocked"
       → emit gate_result + unit_blocked events
   elif result == "failed":
       # the iterate-vs-fuse decision
       new_loop_count = unit.loop_state.loop_count + 1
       if new_loop_count > fuse.max_rounds:     # fuse trip (loop_count > max; C5 preserved)
           decision = "escalate"
           unit.loop_state.fuse.tripped = True
           unit.loop_state.loop_count = new_loop_count
           unit.runtime_status = "blocked"      # system-level block (or "escalated" once human acts)
           escalation = escalation_payload(unit_id, tier, new_loop_count, result, fuse.max_rounds)
           → emit gate_result + back_edge + fuse_trip events; surface escalation
       else:                                     # iterate (back-edge)
           decision = "iterate"
           unit.loop_state.loop_count = new_loop_count
           unit.loop_state.agent_phase = "plan"  # back-edge: reflect → plan
           → emit gate_result + back_edge events
   elif on_fail == "escalate-directly" (G1/initiation):   # the registry's direct-escalate gates
       decision = "escalate"; unit.runtime_status = "blocked"
       → emit gate_result + unit_blocked events
6. CAS-WRITE  unit with cas_version+1 (§3.3); append all events to loop-event-log.jsonl
7. RETURN  GateOutcome
```

**Why this closes AUDIT-133's "call sites = 0":** `process_gate_result` is the function the production path calls. Every review skill conclusion and every gate-engine judgment on a flow unit is routed through it (§6 wiring). It is the single bridge from "a real gate event happened" to "the loop state machine advanced."

### 4.2 Back-edge semantics (atomic record)

When a gate fails and the unit iterates (step 5, `failed` + `loop_count <= max_rounds`), the back-edge is recorded **atomically** in one CAS write + one event-log append:

- `agent_phase: reflect → plan` (the back-edge across phases)
- `loop_count += 1` (the round increment)
- `last_gate_result` / `gate_state.last_result` = the failed result (unified)
- A `back_edge` event `{unit_id, event_type: "back_edge", from_phase: "reflect", to_phase: "plan", gate_id, tier, new_loop_count, cas_version, actor}` appended to the event log.

Because all four mutations share one CAS write and the event is appended in the same atomic step, the back-edge and the round increment can never diverge — a reader either sees both or neither. This is the executable form of the architecture ADR's rule (§3.5): *"a gate that FAILS returns the work into its enclosing loop for another iteration, increments the loop's `loop_count`"* — made atomic and persistent.

The registry's special `release-to-design-replan` back-edge (`auto_fire: false`, three conjunctive conditions incl. PP-Fuse-Escalate human approval) is honored as a **distinct event path**: `process_gate_result` detects when `gate_id == G9` and the result indicates a design-rooted cause, and in that case it does **not** auto-iterate — it emits a `back_edge_request` event requiring the three conjuncts (G9 fail + G5 concurrence + human approval) before converting to a real `back_edge`. This preserves the P1-b resolution (architecture ADR §6.4): the only cross-Middle-loop back-edge stays human-gated.

### 4.3 Round counting (where stored, how derived)

`loop_state.loop_count` is the **authoritative** round counter (per-unit, per active tier). It is incremented exactly once per back-edge (§4.2). This is a **deliberate evolution** of the 0.65.0 stateless `derive_round`:

- **0.65.0 `derive_round`** derives round from evidence-log `LOOP-{U}-{T}-R{n}` rows — stateless, parallel-safe, but **not persistent across restart** in a structured way (it re-scans text). It remains available as a *cross-check / fallback*.
- **0.68.0 `loop_count`** is the persisted, CAS-versioned authoritative counter. On every back-edge, `process_gate_result` also appends a `LOOP-{U}-{T}-R{new_loop_count}` evidence row (preserving the evidence-log contract `derive_round` reads), so the two stay consistent. A consistency check (FEAT-006 test) asserts `derive_round(unit, tier, evidence_log) == loop_state.loop_count` after every transition; a divergence is a fail-closed bug.

This dual representation is intentional: `loop_count` is the fast authoritative counter for the execution engine; the evidence-log row is the auditable, stateless, parallel-safe record that the sacred `derive_round` (and any out-of-band reader) can re-derive. They agree by construction.

### 4.4 Fuse semantics (system-level block, not Coordinator advisory)

The fuse trips when `loop_count > fuse.max_rounds` (per tier, from the registry). On trip:

1. `loop_state.fuse.tripped = true` (persisted, CAS-versioned).
2. `runtime_status = "blocked"` (the unit cannot advance; it requires human resolution). Once the human chooses an escalation option (§4.5), `runtime_status` may move to `"escalated"` or `"withdrawn"`.
3. A `fuse_trip` event is appended to the event log.
4. The `escalation_payload` (the existing `loop_engine.escalation_payload`, 4 options: human arbitration / split unit / accept degraded / withdraw) is surfaced.

**The system-level block (the load-bearing FEAT-006 guarantee, "不依赖 Coordinator 自觉"):** a tripped, unresolved fuse blocks the release/governance gate. This is implemented as a **read query** in the existing release/governance gate path (§6), NOT as a Coordinator advisory:

```
# inside check_release_readiness / Check 28 governance gate (an invocation, not new logic):
tripped_fuses = loop_fuse_check(root)   # reads flow-unit-runtime.json; returns units with fuse.tripped==true AND runtime_status in {blocked, escalated}
if tripped_fuses:
    issues += [f"unit {u}: fuse tripped at round {n} (max {m}); unresolved — release blocked"]
```

`loop_fuse_check` is a pure read in `loop_gate_processor.py` (or `loop_engine.py`). The release gate fails closed on any unresolved tripped fuse. **The Coordinator cannot override this by self-discipline** — the gate is in `check-release` / Check 28, which the Coordinator does not bypass. This is the direct, executable answer to RISK-042's *"fuse 经生产入口触发"* and the FEAT-006 mandate *"不依赖 Coordinator 自觉"*.

The one authorized resolution path is the escalation: the human picks one of the 4 options, which `process_gate_result` (or a sibling `resolve_escalation` function) records as an event and moves `runtime_status` accordingly. "Accept degraded" is recorded with a degraded-evidence contract (not counted as a gate pass — C-degraded preserved); "withdraw" moves to `withdrawn`; "split" creates a new sub-unit (out of scope for atomic-record but the event records the decision).

### 4.5 Escalation generation (reuse the sacred exit verbatim)

`loop_engine.escalation_payload` already builds the exact M7.4 §4.6 C3/C4 4-option AskUserQuestion. FEAT-006 reuses it unchanged — no new escalation mechanism is invented (the architecture ADR §6.5 "sacred pattern" discipline). The only addition is that FEAT-006 *invokes* it from the production path (on fuse trip) and *persists* the human's choice as an event, closing the "escalation generated but never acted on" gap.

---

## 5. Event Log + Dependency Blocking + WIP Spec (FEAT-007)

### 5.1 Event log schema (append-only JSONL)

New file: `.governance/loop-event-log.jsonl` (JSONL — one JSON object per line, UTF-8, newline-terminated). Append-only; rotation/archival is a future FIX task (the archive engine already exists).

**Event envelope** (every line):

```json
{
  "event_id": "evt-01J...",           // ULID or uuid4 hex — unique, monotonic-ish for ordering
  "timestamp": "2026-07-23T14:05:11Z", // ISO-8601 UTC
  "unit_id": "shitu.story.Skeleton",
  "event_type": "back_edge",           // see enum below
  "gate_id": "G6",                     // present when a gate drove the event; else null
  "tier": "inner",                     // the loop tier; null for non-loop events
  "cas_version": 8,                    // the version AFTER this event
  "from_version": 7,                   // the version BEFORE (enables monotonicity check)
  "from_phase": "reflect",
  "to_phase": "plan",
  "actor": "code-reviewer-agent",      // who/what produced the event
  "payload": { ... event-specific ... },
  "evidence_ref": "review-code-Skeleton-R2.md"  // pointer to the evidence; null if none
}
```

**Event types** (closed enum; the validator rejects unknown types):

| `event_type` | When | Key payload |
|--------------|------|-------------|
| `phase_enter` | unit activated (dormant→active) | `entry_tier`, `initial_gate_id` |
| `phase_transition` | plan→act, act→observe, observe→reflect | `from_phase`, `to_phase` |
| `gate_result` | a gate produced a result | `gate_id`, `result`, `mapped_status`, `evidence_ref` |
| `back_edge` | gate failed → iterate (reflect→plan) | `gate_id`, `tier`, `new_loop_count` |
| `loop_exit` | gate passed → loop exits this tier | `gate_id`, `tier`, `final_loop_count` |
| `fuse_trip` | loop_count > max_rounds | `gate_id`, `tier`, `loop_count`, `max_rounds`, `escalation_exit` |
| `escalation_resolved` | human resolved a fuse trip | `resolution` (arbitrate/split/degraded/withdraw), `resolver` |
| `unit_blocked` | runtime_status → blocked (non-fuse) | `reason` |
| `unit_withdrawn` | runtime_status → withdrawn | `reason`, `actor` |
| `dependency_block` | admission denied: a dependency not passed | `unit_id`, `blocking_dependencies` |
| `wip_admit` | admission granted (WIP under budget) | `tier`, `active_count_after` |
| `wip_deny` | admission denied (WIP over budget) | `tier`, `budget`, `active_count` |
| `phase_recovery` | restart found state ahead of log; synthetic gap-close | `recovered_version` |
| `recovery_conflict` | restart found log ahead of state; unit fail-closed | `last_logged_version`, `on_disk_version` |

### 5.2 Multi-process write safety

Two concurrent writers never lose updates, by composition:

1. **Per-unit CAS on `flow-unit-runtime.json`** (§3.3): the current-state file is the serialization point per unit. Two writers racing on the *same* unit: the second's CAS check fails, it retries or fail-closes. Two writers on *different* units: they read-modify-write different unit records; the atomic temp-file+`os.replace` write serializes the whole-file write (last writer wins on the file, but each writer only touched its own unit's record — so the merged file has both updates correctly, because each writer re-read the full file at write time and only mutates its own unit's record). **The CAS check at write time is what prevents a writer from clobbering another unit's concurrent update**: the writer re-reads the file immediately before the atomic write and confirms *its own* unit's `cas_version` is still `expected_version`; the other unit's record (possibly advanced by the other writer) is preserved as-is.

2. **Append-only JSONL event log**: concurrent appends to a single file are atomic at the line level on POSIX (writes < PIPE_BUF, ~4KB, are atomic; our events are small) and on Windows via the temp-buffered-append pattern. To be robust on both, FEAT-007 uses a short-lived exclusive append (open with `O_APPEND`/`"a"` mode and write the full line + `\n` in one `write()` call). Each event line is self-contained and carries `from_version` + `cas_version`, so even if two events interleave in arrival order, each is independently interpretable and the monotonicity check (§3.6) detects any out-of-order `cas_version` regression.

3. **State-write before event-append ordering**: within one transition, the state file is committed first (atomic rename), then the event is appended. A crash between the two leaves a committed state with a missing event — restart recovery (§3.5) detects this (on-disk version > last logged version) and synthesizes a `phase_recovery` event. A crash before the state write leaves nothing committed — the event may or may not be appended; if appended, restart sees `from_version` not matching any on-disk state and treats it as a `recovery_conflict` (fail-closed). The ordering is **state-first** because the state file is the operational truth; the event log is the audit trail that can be gap-filled.

### 5.3 Dependency blocking (admission control)

A unit's `dependencies` (the v2 contract field) list the `flow_unit_id`s it depends on. **Admission rule** (enforced when a unit would enter `act`, or at activation):

```
for dep_id in unit.dependencies:
    dep = flow_units[dep_id]
    if dep.gate_state.status != "passed":
        deny → unit stays dormant/blocked; emit dependency_block event listing blocking_dependencies
```

This makes the dependency graph **executable**: a unit cannot start real work (`act`) until its dependencies have passed their gates. The architecture ADR (§5.5) specified this as the substrate for parallel Inner loops across independent units; FEAT-007 makes it a blocking admission check, not advisory.

`dependency_block` events are recorded so a restart re-derives the blocked set from the current gate statuses (read-based recovery, consistent with §3.5). When a dependency later passes its gate, the blocked unit is re-evaluated (a `gate_result` event on the dependency triggers a re-check of its dependents — a bounded propagation, since the dependency graph is a DAG validated by `confirm_decomposition`).

### 5.4 WIP budget (executable admission cap)

A **WIP budget** limits concurrent `active` units per tier (and optionally per lane). Defaults (from the architecture ADR's risk-profile reasoning; tunable per project-type preset, kept conservative):

| Tier | Default max concurrent `active` units | Rationale |
|------|----------------------------------------|-----------|
| setup | 1 | setup is pre-delivery, sequential by nature |
| inner | 5 | inner loops are cheap; allow parallel slice work |
| middle | 2 | middle loops are expensive (days); cap WIP to force convergence |
| outer | 1 | outer is strategy-level; one winding at a time |

**Enforcement** (at admission — when a `dormant`/`blocked` unit would move to `active`):

```
active_in_tier = count(flow_units where runtime_status=="active" and loop_state.active_loop_tier==tier)
if active_in_tier >= budget[tier]:
    deny → unit stays dormant/blocked; emit wip_deny event {tier, budget, active_count}
else:
    admit → activate; emit wip_admit event {tier, active_count_after}
```

WIP denial is **not** a fuse trip (the unit is not failed; it is queued). It is recorded so the admission queue is reconstructable on restart. The budget is the executable form of the architecture ADR's "stacked loops / parallel review loops" discipline — bounded concurrency, no unbounded fan-out.

---

## 6. Production Wiring (the AUDIT-133 "call sites = 0" fix)

This section is the heart of 0.68.0. The loop engine must **execute on real production events**. Three wiring points:

### 6.1 Wiring point A — review-skill conclusions → `process_gate_result`

Each review skill (`code-review`, `design-review`, `tech-review`, `test-review`, `release-review`, `requirement-review`, `retro-review`) produces a conclusion (`APPROVED` / `APPROVED_WITH_NOTES` / `NEEDS_CHANGE` / `BLOCKED`) for a target. When the target is (or maps to) a flow unit, the review's conclusion is routed to `process_gate_result`:

- The mapping from review target → `flow_unit_id` + `gate_id` uses the registry's `loop_gate_semantics` (e.g. `code-review` → `G6`, inner-loop exit; `design-review` → `G5`, middle-loop entry; `release-review` → `G9`, middle-loop exit). This mapping is data (a new small map, e.g. in the registry or a sidecar), not logic in `verify_workflow.py`.
- The wiring is a **thin invocation** in the review-recording path (wherever a review conclusion is persisted today — the `review-{role}-{id}-R{n}.md` writer or the evidence-log appender). It calls `process_gate_result(unit_id, gate_id, mapped_result, evidence_ref=..., actor=...)`. This is ≤10 lines of delegation at each wiring point; no new logic in `verify_workflow.py`.

**The result**: a real `code-review` returning `NEEDS_CHANGE` on `shitu.story.Skeleton` now drives `reflect → plan` (back-edge), increments `loop_count`, and appends events. This is the executable AUDIT-133 fix.

### 6.2 Wiring point B — gate-engine judgments → `process_gate_result`

`auto_judge_gate` (the registry-backed gate engine, 0.54.0) judges gates G1-G11 from `required_artifacts` / `checks[]` / `evidence_query`. When a gate judgment is rendered for a flow unit, it is routed to `process_gate_result` (same thin-invocation pattern). This connects the *automated* gate path (not just human reviews) to the loop engine.

### 6.3 Wiring point C — system-level fuse block in the release/governance gate

`check_release_readiness` and/or Check 28 (governance gate) gains a **read query** that fails closed on unresolved tripped fuses (§4.4). This is an *invocation* of `loop_fuse_check` (a pure read in a loop module), not new logic in `verify_workflow.py`. A tripped, unresolved fuse → the release/governance gate fails with a specific issue per unit. **This is the system-level block that does not rely on Coordinator self-discipline.**

```
# pseudo-code for the wiring (lives in the release/governance gate path as a query):
from loop_gate_processor import loop_fuse_check
tripped = loop_fuse_check(root=root)
for u in tripped:
    issues.append({
        "severity": "FAIL",
        "gate": "loop-fuse",
        "unit": u.unit_id,
        "message": f"loop fuse tripped at round {u.loop_count} (max {u.max_rounds}, tier {u.tier}); "
                   f"unresolved — release blocked. Resolve via escalation (human arbitration / "
                   f"split / degraded / withdraw)."
    })
```

### 6.4 Wiring point D — agent phase transitions from the agent loop

The agent intrinsic loop (Plan-Act-Observe-Reflect) drives `phase_transition` events: when the agent completes a plan and starts acting (`plan → act`), when it records an observation (`act → observe`), when it self-reviews (`observe → reflect`). These are driven by **thin invocations** at the existing governance checkpoints (PP-Plan-Approve, PP-Observe-Evidence, PP-Reflect-SelfReview — the pause points the registry declares). This wiring is lower-priority than A/B/C (the gate path is the REL-060-critical one); FEAT-005 delivers the transition *machinery*, and the agent-loop wiring can land incrementally within 0.68.0 as the phase transitions are what make the PARO state machine visibly advance between gate events.

### 6.5 What is NOT wired (honest scope)

- **0.68.0 does not auto-fire the `release-to-design-replan` back-edge.** It records a `back_edge_request` and requires the three conjunctive conditions (G9 fail + G5 concurrence + human approval). The human gate is preserved (P1-b).
- **0.68.0 does not wire every conceivable event source.** The REL-060-critical wiring is the gate/review path (A/B/C). Agent-loop phase transitions (D) are wired for the phases that have existing governance checkpoints; deep agent-instrumentation is 0.69.0 (telemetry).
- **0.68.0 does not change the v1 visibility contract or the 0.66.x release-critical assets.** All wiring is additive; v1/classic installations are unaffected (they have no `flow-unit-runtime.json` v2 payload, so `process_gate_result` is a no-op for them — it detects `schema_version != "2.0"` and returns without mutating).

---

## 7. Implementation Order + File Changes

### 7.1 Dependency-confirmed order: FEAT-005 → FEAT-006 → FEAT-007

```
FEAT-005 (PARO state machine: transitions + CAS + persistence + restart recovery)
   │
   ├── infra/loop_paro_engine.py               (NEW — transition validator + CAS writer; the §3.2 table + §3.3 protocol)
   ├── infra/loop_engine.py                    (EXTEND — add activate_unit dormant→active; cas_version helpers)
   ├── infra/checks/flow_unit_runtime_v2.py    (EXTEND — cas_version + transition-legality validation pass)
   ├── core/loop-runtime-contract.json         (EXTEND — declare cas_version as an allowed loop_state field; schema_version stays "2.0")
   └── infra/tests/test_loop_paro_engine.py    (NEW — transition legality, CAS conflict, restart recovery)
   │
   ▼
FEAT-006 (gate/fuse consumes the state machine)
   │
   ├── infra/loop_gate_processor.py            (NEW — process_gate_result, loop_fuse_check, resolve_escalation; §4 algorithm)
   ├── infra/loop_engine.py                    (EXTEND — reuse fuse_decision/escalation_payload; wire loop_count↔derive_round consistency)
   ├── infra/verify_workflow.py                (THIN — loop_fuse_check invocation in check_release_readiness/Check 28; ≤20 lines, delegation only)
   ├── infra/checks/flow_unit_runtime_v2.py    (EXTEND — fuse.tripped ⇔ runtime_status consistency check)
   └── infra/tests/test_loop_gate_processor.py (NEW — back-edge atomicity, fuse trip, escalation, system-level block)
   │
   ▼
FEAT-007 (event log + dependency blocking + WIP wraps both)
   │
   ├── infra/loop_event_log.py                 (NEW — append-only JSONL writer/reader; §5.1/5.2)
   ├── infra/loop_admission.py                 (NEW — dependency blocking + WIP budget; §5.3/5.4)
   ├── infra/loop_paro_engine.py               (EXTEND — every transition also appends an event)
   ├── infra/loop_gate_processor.py            (EXTEND — every gate outcome also appends an event)
   ├── infra/checks/flow_unit_runtime_v2.py    (EXTEND — event-log monotonicity + dependency/WIP consistency)
   └── infra/tests/test_loop_event_log.py      (NEW — multi-process append, restart recovery, dependency block, WIP deny)
       infra/tests/test_loop_admission.py      (NEW)
```

**Why this order (and not another):**

- **FEAT-005 first** because FEAT-006's `process_gate_result` drives the state machine — it cannot be built or tested without the transition validator + CAS writer. FEAT-005 is the substrate.
- **FEAT-006 second** because it is the REL-060-critical production wiring (the AUDIT-133 fix). It consumes FEAT-005's state machine and the registry semantics. It can be built and tested (with an in-memory or simple event capture) before the persistent event log exists.
- **FEAT-007 last** because it wraps both: the event log is appended by *every* transition (FEAT-005) and *every* gate outcome (FEAT-006). Building it last means FEAT-005/006 can land with a minimal event capture (e.g. an in-memory list or a simple append) and FEAT-007 hardens it into the restart-safe, multi-process-safe, dependency/WIP-aware form. FEAT-007 also delivers the restart-recovery and multi-process guarantees that REL-060's "restart/multi-process/WIP 门禁通过" demands.

Each FEAT is a separately reviewable commit with its own DEC + Developer + Code Reviewer + QA cycle. FEAT-006 cannot start until FEAT-005 is committed (gate processor drives the state machine). FEAT-007 cannot start until FEAT-006 is committed (it wraps the gate outcomes).

### 7.2 What is NOT touched (release-critical isolation)

FEAT-005~007 MUST NOT modify:

- `infra/release/verify_rel063_evidence.py` — the 0.66.x release-critical evidence verifier.
- `infra/checks/flow_unit_runtime.py` (the v1 validator) — frozen; v1 payloads route to it unchanged.
- The 0.66.x compensation assets (FIX-195 transaction recovery, FIX-196 health fail-closed) — `loop_migration.apply_migration`'s backup/commit/compensation machinery is preserved.
- `core/loop-runtime-claim-allowlist.json` / `core/loop-runtime-claim-authority.json` — the claim scanner policy (ADR-011/012) is untouched. New 0.68.0 surfaces must comply with the claim contract at write time (scoped-negative / planned-target wording; see §9.5).
- The four FX-189 pure functions' **purity**: `derive_round`, `fuse_decision`, `escalation_payload` remain pure/stateless. FEAT-005~007 add *new* functions and *invoke* these; they do not make them stateful. `derive_round` stays the parallel-safe cross-check (§4.3).
- `core/loop-engineering-registry.json` — structurally unchanged; FEAT-006 *reads* it.

### 7.3 Estimated complexity

**Large — the largest MINOR in the DEC-104 chain.** This is the execution engine: state persistence, concurrency (CAS), a terminal processor, and a multi-process-safe event log. Breakdown:

- **FEAT-005**: ~1 new module (`loop_paro_engine.py`, ~300-450 lines: transition table, CAS writer, restart recovery), validator extension (~100-150 lines), contract additive field, tests (~400-600 lines). **Risk: the CAS protocol and restart-recovery correctness.** Medium-high.
- **FEAT-006**: ~1 new module (`loop_gate_processor.py`, ~350-500 lines: the §4 algorithm, fuse check, escalation wiring), thin verify_workflow invocations (~30-50 lines across wiring points), validator extension (~80 lines), tests (~500-700 lines). **Risk: atomicity of back-edge+round, the system-level fuse block correctness.** Medium-high.
- **FEAT-007**: ~2 new modules (`loop_event_log.py` ~250-350 lines; `loop_admission.py` ~200-300 lines), extensions to paro/gate processors to emit events (~100 lines), validator extension (~120 lines), tests (~600-800 lines, incl. multi-process and restart). **Risk: multi-process append safety across POSIX/Windows, dependency propagation correctness.** Medium-high.

Total: ~5 new modules, ~3 extended modules, ~1 extended contract (additive field), ~2500-3500 lines net, dominated by tests and invariant proofs. The hardest part is not volume but **concurrency-correctness proof**: the CAS protocol, the multi-process append, and the restart-recovery tests must be airtight (REL-060 demands "restart/multi-process/WIP 门禁通过").

---

## 8. REL-060 Acceptance Criteria + Tests

### 8.1 REL-060 acceptance (from plan-tracker row 163)

> MINOR。真实生产命令必须完成 **gate fail→back-edge→round→fuse→escalation**，**restart/multi-process/WIP 门禁通过**。

Translated to executable tests:

### 8.2 Tests that prove FEAT-005 meets REL-060 (PARO state machine)

- `test_legal_transitions_accepted` — each of the 6 forward transitions (§3.2) is accepted; the unit's `agent_phase` and `cas_version` advance correctly.
- `test_illegal_transitions_rejected` — illegal jumps (e.g. `plan → observe`, `act → plan`, `reflect → act`) are rejected with no state mutation and no `cas_version` bump.
- `test_cas_version_monotonic` — across a sequence of transitions, `cas_version` is strictly +1 per transition.
- `test_cas_conflict_detected` — two writers racing on the same unit: the second's write is rejected (on-disk version advanced); retry succeeds with the fresh version.
- `test_cas_no_lost_update_across_units` — two writers on *different* units: both updates land in the merged file (the writer re-reads and preserves the other unit's advanced record).
- `test_restart_recovers_phase_and_count` — write a transition, "restart" (drop in-memory state), re-load: `agent_phase`, `loop_count`, `fuse`, `cas_version` are recovered from `flow-unit-runtime.json`.
- `test_restart_state_ahead_of_log_synthesizes_recovery_event` — committed state with a missing event: restart synthesizes `phase_recovery` and the log is consistent.
- `test_restart_log_ahead_of_state_fail_closes` — event log ahead of state (dangerous case): restart fail-closes the unit to `blocked` with `recovery_conflict`; no silent replay.
- `test_unification_invariant_holds_after_transition` — after every transition, `loop_state.last_gate_result == gate_state.last_result` (0.67.0 invariant preserved).

### 8.3 Tests that prove FEAT-006 meets REL-060 (gate/fuse — the REL-060 chain)

- `test_gate_fail_drives_back_edge_and_round_increment` — **REL-060 load-bearing.** A `failed` gate result on an active unit drives `reflect → plan` (back-edge), increments `loop_count` by exactly 1, and appends a `back_edge` event — all atomically (one CAS write). This is the "gate fail → back-edge → round" half of the chain.
- `test_back_edge_and_round_are_atomic` — the back-edge phase change and the `loop_count` increment share one CAS write; a reader never sees one without the other.
- `test_gate_pass_exits_loop` — a `passed` result drives `loop_exit`; `gate_state.status: passed`; no `loop_count` increment.
- `test_fuse_trips_at_loop_count_gt_max` — **REL-060 load-bearing.** When `loop_count` would exceed `fuse.max_rounds` (e.g. Inner max 5, 6th failure), the fuse trips: `fuse.tripped: true`, `runtime_status: blocked`, `fuse_trip` event, escalation payload generated. This is the "→ fuse → escalation" half of the chain.
- `test_fuse_does_not_trip_at_loop_count_eq_max` — at `loop_count == max_rounds`, the unit still iterates (one more allowed; C5 preserved — no reluctant auto-pass, but also no premature trip).
- `test_loop_count_consistent_with_derive_round` — after every back-edge, `derive_round(unit, tier, evidence_log) == loop_state.loop_count` (the dual representation agrees).
- `test_system_level_fuse_block_in_release_gate` — **REL-060 load-bearing ("不依赖 Coordinator 自觉").** A unit with `fuse.tripped: true` and unresolved `runtime_status: blocked` causes `check_release_readiness` (or Check 28) to FAIL with a specific per-unit issue. The Coordinator cannot bypass it.
- `test_fuse_block_clears_after_escalation_resolution` — after the human resolves the escalation (e.g. withdraw), `runtime_status: withdrawn`, and the fuse block no longer fails the release gate (the unit is no longer blocking).
- `test_release_to_design_replan_requires_three_conjuncts` — the cross-Middle back-edge emits `back_edge_request`, not `back_edge`, until G9-fail + G5-concurrence + human-approval are all recorded (P1-b preserved).
- `test_registry_gate_semantics_consumed` — `process_gate_result` reads `loop_gate_semantics[gate_id]` for tier/on_fail/fuse_ref; a re-mapped registry (e.g. G6 enclosing_loop changed) produces different behavior. This proves FEAT-006 consumes the registry, not hard-coded semantics.
- `test_v1_payload_is_noop` — a v1 (`schema_version: "1.0"`) payload: `process_gate_result` returns without mutating (0.68.0 does not break classic/dynamic installations).

### 8.4 Tests that prove FEAT-007 meets REL-060 (restart/multi-process/WIP)

- `test_event_log_append_only` — events are appended in order; the file is never rewritten (a write-attempt to an existing byte offset fails or is detected).
- `test_multi_process_append_no_loss` — **REL-060 load-bearing ("multi-process").** Two processes append events concurrently; no event is lost; each line is well-formed JSON; `cas_version` sequence is monotonic per unit.
- `test_event_log_monotonicity_check` — a deliberately corrupted log (a `cas_version` regression) is detected by the validator.
- `test_dependency_block_admission` — **REL-060 load-bearing ("WIP/dependency").** A unit whose dependency has `gate_state.status != "passed"` is denied admission to `act`; a `dependency_block` event is recorded.
- `test_dependency_unblocks_on_pass` — when the dependency's gate passes, the blocked unit is re-evaluated and admitted (bounded DAG propagation).
- `test_wip_budget_denies_over_budget` — **REL-060 load-bearing ("WIP").** With the tier budget reached, a new unit is denied activation; a `wip_deny` event is recorded; the unit stays dormant.
- `test_wip_admit_under_budget` — under budget, admission succeeds; `wip_admit` event recorded.
- `test_restart_reconstructs_blocked_and_wip_state` — after restart, the dependency-blocked and WIP-denied sets are re-derived from current gate statuses and active counts (read-based recovery).

### 8.5 Integration tests (the end-to-end REL-060 proof)

- `test_end_to_end_gate_fail_to_escalation` — **THE REL-060 integration test.** Fixture: an active unit at Inner tier with `max_rounds=2`. Drive 3 consecutive `failed` gate results via `process_gate_result`. Assert: rounds 1-2 produce back-edges (`loop_count` 1, 2; `agent_phase` cycles reflect→plan); round 3 trips the fuse (`fuse.tripped: true`, `runtime_status: blocked`, `fuse_trip` event, escalation payload); the release gate fails closed on the unresolved fuse; after human "withdraw" resolution, the release gate no longer fails on this unit. This single test exercises the entire chain: **gate fail → back-edge → round → fuse → escalation → system block → resolution**.
- `test_end_to_end_restart_mid_loop` — drive a back-edge, kill the process mid-CAS-write (simulate via crash-injection), restart, assert the state is either the pre- or post-transition consistent state (never torn); continue the loop; assert `loop_count` is correct.
- `test_end_to_end_multi_process_convergence` — two processes driving different units' loops concurrently; both converge; no lost events; release gate reflects both units' final states.

### 8.6 What does NOT close in 0.68.0

- **RISK-037 remains open.** The "no global stage" criterion is met (0.67.0), and 0.68.0 adds the executable engine — but RISK-037's full closure requires external validation (0.69.0 dogfood + 2 external project types, VAL-008/VAL-009). 0.68.0 ships the engine, not the external proof.
- **RISK-042 remains open** for the same reason. Its closure standard explicitly lists "至少 dogfood+2 外部类型多 unit/multi-lane installed-state PASS" — that is 0.69.0.
- **Production telemetry / honest DORA metrics** — FEAT-008 (0.69.0). 0.68.0 records the *events* that telemetry will compute from, but does not compute/serve the metrics.
- **verify_workflow Phase 5 extraction** — 0.70.0.
- **1.0.0** — not in scope; blocked until RISK-036/037 close.

---

## 9. Risk + Regression Analysis

### 9.1 Existing tests that might break (and how to keep them green)

| Test file | Risk | Mitigation |
|-----------|------|------------|
| `test_loop_engine_round.py` | **LOW.** `derive_round`/`fuse_decision` purity is sacred and unchanged. FEAT-006 *invokes* them; it does not mutate them. | No change. Add a consistency test (§8.3) asserting `derive_round == loop_count` after every back-edge. |
| `test_loop_migration_plan.py` / `test_loop_migration.py` | **LOW-MEDIUM.** The planner is frozen for 0.68.0. `apply_migration` still writes dormant units; the `cas_version` field is additive-optional for dormant units, so existing payloads still validate. | Dormant units written by the 0.67.0 planner are still valid under the 0.68.0 extended validator (`cas_version` optional on dormant). FEAT-005's `activate_unit` is what adds `cas_version` when a unit goes active. |
| `test_loop_runtime_contract.py` (drift test) | **LOW-MEDIUM.** The contract gains `cas_version` as an allowed `loop_state` field; the drift test (registry `loop_state_fields` == contract) must be updated to include it in BOTH places (registry `agent_intrinsic_loop.loop_state_fields` + contract `loop_state_fields`). | Additive: append `cas_version` to both lists in lockstep; the drift test then passes. The 9 → 10 field count change is the one structural additive change in 0.68.0. |
| `test_flow_unit_runtime_v2.py` (0.67.0 validator) | **MEDIUM.** The validator gains the `cas_version` + transition-legality pass. Existing 0.67.0 fixtures (dormant units, no `cas_version`) must still pass. | The new pass requires `cas_version` only on `active` units; dormant fixtures (the 0.67.0 baseline) are unaffected. A dedicated `test_v0670_payloads_still_validate` runs the 0.67.0 fixture set against the 0.68.0 validator and asserts no regressions. |
| `test_loop_health.py` | **LOW.** `loop_health` reads registry + runtime; FEAT-007's event log is a new file it does not read. The FIX-196 fail-closed discipline is preserved. | No change; optionally extend Part 2/DORA to read `fuse_trip` event counts (additive, advisory). |
| `test_loop_rollup.py` | **LOW.** `rollup_loop_state` reads per-unit loop_state; `cas_version` is an extra field it ignores. `no_global_stage: True` invariant preserved. | No change. |
| `test_loop_runtime_claims.py` / `test_loop_runtime_claim_attestation.py` | **MEDIUM.** New 0.68.0 files (`loop_paro_engine.py`, `loop_gate_processor.py`, `loop_event_log.py`, `loop_admission.py`) are new surfaces the claim scanner sees. Any affirmative claim about runtime activation must be classified. | All new files use scoped-negative / planned-target wording at write time (§9.5). The ADR and new files describe *execution* (which 0.68.0 genuinely delivers) — wording must be precise: the loop engine executes on gate events, but RISK-037/042 remain open (external validation is 0.69.0). The `<!-- loop-runtime-target:... -->` marker discipline is preserved. The claim policy itself is NOT modified. |
| `test_verify_workflow.py` (release/governance gate) | **MEDIUM.** The fuse-block wiring (§6.3) adds a query to `check_release_readiness`/Check 28. Existing release-gate tests that assume no fuse state must still pass (no tripped fuses → no block). | The fuse-block query returns empty when no fuses are tripped; existing tests with no active fuse state are unaffected. Add a test with a tripped fuse asserting the block fires. |

### 9.2 Preserving the 0.66.x / 0.67.0 containment and contract

The invariants that MUST remain true after 0.68.0:

1. **Apply validates before write.** `build_migration_plan` → `plan_to_payload` → `validate_flow_unit_runtime_payload_v2` → only then backup + write. **Preserved** (0.67.0 unchanged; FEAT-005~007 do not touch apply).
2. **v1 byte-frozen.** The v1 validator and v1 payloads route unchanged. `process_gate_result` is a no-op for v1. **Preserved.**
3. **The v2 contract field set is additive only.** `cas_version` is added to `loop_state`; no 0.67.0 field is removed or retyped. The contract `schema_version` stays `"2.0"`. **Preserved.**
4. **The four FX-189 pure functions stay pure.** `derive_round`, `fuse_decision`, `escalation_payload`, `activate_loop_state` are unchanged in behavior; FEAT-005~007 add new functions and invoke them. **Preserved** (sacred-pattern discipline, architecture ADR §6.5).
5. **Health fails closed on missing/corrupt authority.** `loop_health` FIX-196 discipline preserved; the contract/registry remain authorities. **Preserved.**
6. **RISK-040 dual-root discipline.** All 0.68.0 runtime reads/writes resolve HOST_PROJECT_ROOT via `resolve_entry`, never PLUGIN_HOME. The event log lives at `HOST_PROJECT_ROOT/.governance/loop-event-log.jsonl`. **Preserved.**
7. **RISK-039 thin-entry discipline.** `verify_workflow.py` gets only thin invocations (fuse-block query, review-conclusion routing); all logic is in new `infra/loop_*` modules. ArchGuard's module-size check must pass. **Preserved.**

A dedicated regression test (`test_066x_0670_containment_preserved`) runs the FIX-195/196 + 0.67.0 validator scenarios against the 0.68.0 code and asserts the same fail-closed behavior.

### 9.3 Does FEAT-005~007 touch release-critical assets?

**No.** FEAT-005~007 do not modify:

- `infra/release/verify_rel063_evidence.py` (0.66.x release-critical evidence).
- The 0.66.x / 0.67.0 release documents, tags, or manifest transitions.
- The claim scanner policy/authority (`core/loop-runtime-claim-*.json`).

The release-critical path for 0.68.0 is REL-060, a new MINOR release with its own release docs. The one touch to an existing gate is the fuse-block *query* in `check_release_readiness`/Check 28 — which is additive (returns empty when no fuses tripped) and cannot break an existing release that has no tripped fuses.

### 9.4 The main residual risks

1. **Concurrency correctness (highest risk).** The CAS protocol, multi-process JSONL append, and restart recovery are the novel concurrency surface. Mitigation: the §8.4 multi-process and restart tests are load-bearing; a threading/multiprocessing test harness is mandatory. The state-first/event-second ordering (§5.2) is chosen so the dangerous case (log ahead of state) is detectable and fail-closed, not silently replayed.

2. **Wiring-point breadth.** FEAT-006 wires review-skill conclusions + gate-engine judgments + the release-gate fuse block. Missing a wiring point would leave a "call sites still 0" gap for some event source. Mitigation: an audit test (`test_all_gate_sources_route_to_processor`) enumerates the review skills + gate engine and asserts each routes through `process_gate_result` when the target is a flow unit.

3. **Validator extension backwards-compatibility.** Adding the `cas_version` + transition-legality pass must not reject 0.67.0 payloads. Mitigation: the `cas_version`-on-active-only rule + the `test_v0670_payloads_still_validate` regression test.

4. **The dual `loop_count` / `derive_round` representation diverging.** If a bug writes one without the other, they disagree. Mitigation: the §8.3 consistency test after every back-edge; divergence is fail-closed.

### 9.5 Loop-runtime claim scanner compliance (ADR-011/012 discipline)

All new 0.68.0 surfaces (this ADR, the new modules, the contract field) must comply with the existing claim contract at write time:

- **Scoped-negative / planned-target wording.** The new files describe *execution* (which 0.68.0 delivers) but must NOT claim RISK-037/042 closure or 1.0.0 readiness. Wording: "the loop engine executes on gate events" (true in 0.68.0) — NOT "loop engineering is production-complete" (false until 0.69.0).
- **The `<!-- loop-runtime-target:... -->` marker** is used in this ADR (top of document) and in any new doc that makes a forward-looking statement. The marker's `status: "planned_not_active"` flips to `"active"` only after REL-060 passes and the claim scanner is updated (a separate FIX task, not FEAT-005~007 scope).
- **The claim policy itself is NOT modified.** Adding `cas_version`, the event log, and the gate processor does not change how the scanner classifies claims; it changes what the runtime *does*. If any new affirmative runtime-activation claim is needed in an audited file, it goes through the existing allowlist/authority amendment process (ADR-011/012), which is out of scope for this ADR.

---

## 10. Authorization Boundary

This ADR is **design only.** It:

- Does NOT implement code. Each of FEAT-005, FEAT-006, FEAT-007 requires:
  1. A separate DEC (task dispatch) from the Coordinator.
  2. A Developer (implementation per this spec).
  3. An independent Code Reviewer (R0, with rounds per Check 30 review-chain fuse).
  4. An independent QA.
  5. For the aggregate, a Release Reviewer for REL-060.
- Does NOT authorize a release. REL-060 requires its own release docs, version projection, and Release Review per the release workflow.
- Does NOT close RISK-037 or RISK-042. Both remain open until 0.69.0 (external validation: dogfood + 2 external project types, VAL-008/VAL-009). 0.68.0 delivers the execution engine; external effectiveness is not proven until 0.69.0.
- Does NOT claim 1.0.0 readiness. 1.0.0 remains blocked until RISK-036 AND RISK-037 close per their recorded standards.
- Does NOT modify the 0.66.x release-critical assets, the v1 visibility contract, or the loop runtime claim scanner policy (ADR-011/012). New v2 surfaces added by FEAT-005~007 comply with the existing claim contract at write time.
- Does NOT auto-fire the `release-to-design-replan` back-edge. That back-edge stays human-gated (three conjunctive conditions, P1-b preserved).
- Does NOT make the four FX-189 pure functions stateful. `derive_round`, `fuse_decision`, `escalation_payload`, `activate_loop_state` remain pure/stateless; FEAT-005~007 add new functions and invoke them.

**Design Review scope:** the Design Reviewer reviews this ADR for (a) PARO transition-table completeness and legality (does the §3.2 table cover all real events? are illegal transitions correctly rejected?), (b) CAS protocol correctness (does §3.3 prevent lost updates within and across units? is restart recovery §3.5 sound?), (c) gate/fuse terminal processor correctness (does §4 atomically record back-edge+round? does the system-level fuse block §4.4/§6.3 truly not rely on Coordinator self-discipline?), (d) event-log multi-process safety (does §5.2 lose no updates on POSIX and Windows?), (e) dependency/WIP enforcement correctness (§5.3/5.4), (f) regression risk to 0.66.x/0.67.0 containment and contract (§9), (g) whether the implementation order §7 is sound, (h) whether the REL-060 tests §8 actually prove the acceptance chain. On APPROVAL_WITH_NOTES with `unresolved_blockers=0`, the Coordinator may dispatch FEAT-005 (then FEAT-006, then FEAT-007) each with its own execution packet and review chain.

**Authority:** DEC-104 (binding roadmap), AUDIT-133 / EVD-707 (the "call sites = 0" findings this addresses), RISK-037 / RISK-042 (the open risks whose 0.68.0 portion this delivers), `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` (the R1-APPROVED design ADR whose PARO/back-edge/fuse activation this implements), ADR-013 (the 0.67.0 contract foundation this builds on), ADR-011/012 (the claim-correction boundary this must respect).

---

## Appendix A: The REL-060 acceptance chain (quick reference)

The plan-tracker row for REL-060 demands: **gate fail → back-edge → round → fuse → escalation**, **restart/multi-process/WIP 门禁通过**. The executable mapping:

| Chain step | Where implemented | Test |
|------------|-------------------|------|
| gate fail | `process_gate_result` maps `NEEDS_CHANGE`/`failed` → `failed` (§4.1 step 3) | `test_gate_fail_drives_back_edge_and_round_increment` |
| → back-edge | `reflect → plan` transition, atomic with round++ (§4.2) | same test + `test_back_edge_and_round_are_atomic` |
| → round | `loop_state.loop_count += 1` + `LOOP-{U}-{T}-R{n}` evidence row (§4.3) | `test_loop_count_consistent_with_derive_round` |
| → fuse | `loop_count > fuse.max_rounds` → `fuse.tripped: true` (§4.4) | `test_fuse_trips_at_loop_count_gt_max` |
| → escalation | `escalation_payload` (4 options) surfaced + `fuse_trip` event (§4.5) | same test |
| system block | `loop_fuse_check` in `check_release_readiness`/Check 28 fails closed (§4.4, §6.3) | `test_system_level_fuse_block_in_release_gate` |
| restart 门禁 | read-based recovery from `flow-unit-runtime.json` + event-log consistency (§3.5) | `test_end_to_end_restart_mid_loop` |
| multi-process 门禁 | per-unit CAS + append-only JSONL (§5.2) | `test_multi_process_append_no_loss` |
| WIP 门禁 | dependency blocking + WIP budget admission (§5.3/5.4) | `test_dependency_block_admission`, `test_wip_budget_denies_over_budget` |

The single end-to-end proof is `test_end_to_end_gate_fail_to_escalation` (§8.5), which exercises the entire chain in one test.

## Appendix B: Field/store reference (for the implementer)

| Artifact | Path | Role in 0.68.0 |
|----------|------|----------------|
| v2 runtime payload (current state) | `HOST_ROOT/.governance/flow-unit-runtime.json` | Authoritative per-unit `agent_phase`, `loop_count`, `gate_state`, `fuse`, `cas_version`. CAS-guarded read-modify-write. (0.67.0 file, extended with `cas_version`.) |
| Event log (audit/replay) | `HOST_ROOT/.governance/loop-event-log.jsonl` | **NEW (FEAT-007).** Append-only history. |
| Loop runtime contract (schema) | `PLUGIN_HOME/core/loop-runtime-contract.json` | The single source of truth; gains `cas_version` as an allowed `loop_state` field. |
| Loop registry (semantics) | `PLUGIN_HOME/core/loop-engineering-registry.json` | FEAT-006 reads `loop_gate_semantics`, `loop_fuses`, `back_edges`. Unchanged structurally. |
| PARO engine | `PLUGIN_HOME/infra/loop_paro_engine.py` | **NEW (FEAT-005).** Transition validator + CAS writer. |
| Gate processor | `PLUGIN_HOME/infra/loop_gate_processor.py` | **NEW (FEAT-006).** `process_gate_result`, `loop_fuse_check`, `resolve_escalation`. |
| Event log module | `PLUGIN_HOME/infra/loop_event_log.py` | **NEW (FEAT-007).** Append-only JSONL writer/reader. |
| Admission module | `PLUGIN_HOME/infra/loop_admission.py` | **NEW (FEAT-007).** Dependency blocking + WIP budget. |
| v2 validator | `PLUGIN_HOME/infra/checks/flow_unit_runtime_v2.py` | Extended: `cas_version` + transition-legality + event-monotonicity passes. |
| Loop engine (existing) | `PLUGIN_HOME/infra/loop_engine.py` | `derive_round`/`fuse_decision`/`escalation_payload` reused (pure); `activate_unit` added. |
| verify_workflow (thin entries) | `PLUGIN_HOME/infra/verify_workflow.py` | Fuse-block query in release/Check 28; review-conclusion routing. Thin invocations only. |

`PLUGIN_HOME = skills/software-project-governance/` (per the fixed-anchor convention in all `loop_*` modules). `HOST_ROOT` is resolved via `resolve_entry.resolve_host_root` (RISK-040: never `PLUGIN_HOME`).
