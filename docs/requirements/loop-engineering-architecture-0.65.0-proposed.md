# Loop-Engineering Architecture ADR — Redesigning the Workflow Around Loops

> **Version**: 0.65.0-proposed (design-only; version number承载 is decided after Design Reviewer approval)
> **Status**: Revised (R0.1) — APPROVED_WITH_NOTES by Design Reviewer R0 (REVIEW-AUDIT-130-R0); P0 resolved via DEC-098; 3 P1 findings addressed in this revision. Awaiting R1.
> **Triggering decisions**: DEC-097 (binding, three parts) + DEC-098 (re-scopes RISK-037 criterion 4: compatibility = (a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3), not parallel active mode — resolves the P0 from REVIEW-AUDIT-130-R0)
> **Risk addressed**: RISK-037 (1.0.0 hard blocker, due 2026-07-30) + RISK-039 (God Module constraint)
> **History**: AUDIT-114 (dynamic lifecycle research) → 0.51.0-0.55.0 (schema-only investments, dormant) → DEC-097 (loop-first refactor mandate) → **this ADR v0** (designs the activation) → REVIEW-AUDIT-130-R0 (APPROVED_WITH_NOTES) → DEC-098 (resolves P0 criterion-4 conflict) → **this ADR R0.1** (addresses 3 P1 findings: P1-a setup-loop, P1-b design-replan back-edge, P1-c velocity-justification check)
> **Scope**: Architecture decision record ONLY. No product code changes. No RISK closure. No 1.0.0 claim.

---

## 1. Title, Status, and Context

### 1.1 Title

**Make loop the only model: activate dormant flow-unit and loop assets, promote the Plan-Act-Observe-Reflect agent loop to a first-class governance object, and retire the linear G1-G11 as the primary execution model.**

### 1.2 Status

Proposed. Not yet approved. Version承载 (whether this lands as 0.65.0 or a later number) is decided after Design Reviewer approves the design, per DEC-097 part 3.

### 1.3 The problem (RISK-037)

RISK-037 is a 1.0.0 hard blocker, due 2026-07-30 (extended from 2026-06-30). Its recorded statement (`.governance/risk-log.md` row 38):

> 固定 G1→G11 线性阶段模型与真实项目动态迭代不匹配，导致外部项目使用体验严重僵硬 (The fixed G1→G11 linear stage model does not match real-project dynamic iteration, producing a severely rigid external UX.)

The harm, as recorded: real projects advance by independent increments, but the workflow can only express a single "current stage" (`当前阶段`). A project where chapter 1 is released, chapter 2 is in testing, and chapters 3-10 are in design must be flattened into one fake global stage. The AI agent then misjudges "G6 passed = all development done," and subsequent units miss their proper design/test/release gates. Shipping 1.0.0 without fixing this wraps a core flow defect in a "ready" label.

### 1.4 The user feedback (verbatim)

> 当前的工作流线性的状态迁移并不合理，工作流除了特殊的立项之外，其他流程应该包含在不同层级的 loop 中，例如设计→开发→测试→发布的循环，开发阶段的修改→检视的循环等等。

Translation of the load-bearing requirement: **Except for special initiation (立项), all other processes should live in loops at different levels** — e.g. the design→dev→test→release cycle (a cross-stage iteration loop), the modify→review cycle within development (a within-stage loop), etc.

This feedback is a structural mandate, not a preference: it demands **loops as the organizing primitive** and **initiation as the explicit exception**.

### 1.5 Binding decisions (DEC-097)

Three user decisions bind this design (plus DEC-098, added in R0.1 to resolve the P0):

1. **Refactor mode — loop is the ONLY model.** The linear G1-G11 model is retired as the *primary* model. G1-G11 stages degrade into "loop-setup" (initiation/立项 remains special; research/selection/infrastructure form a bounded setup-loop per P1-a, §3.3). **This breaks backward compatibility — that is accepted.** This is a sharp departure from 0.51.0-0.55.0, which preserved `classic-phase-gate` as the active default.
2. **AI agent loop (Plan-Act-Observe-Reflect) is a first-class citizen.** It must be an explicitly-named object in the governance model. Governance checkpoints (review, human approval) are defined as **pause points** inserted into the agent loop, and **each pause must justify its cost to loop velocity** (enforced per P1-c, §9.5).
3. **Design ADR first — version not yet decided.** No product code changes in this step. Only this design document.
4. **DEC-098 (R0.1) — criterion-4 re-scoping.** Resolves the P0 from REVIEW-AUDIT-130-R0: "compatibility" in RISK-037 criterion 4 means *(a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3)*, not a parallel active classic mode. See §10 criterion 4 and §12 Q3.

### 1.6 Why now, and why this is a refactor not an extension

0.51.0-0.55.0 invested in five versioned assets — the lifecycle registry, flow-unit schema, runtime visibility, project-type presets, and the declarative gate engine. They were deliberately shipped **dormant** (`registry_mode: "schema-only-no-runtime-activation"`, all `runtime_activation` flags false). The design bet was: ship the declaration layer, prove it parses, then activate later. That bet is now paying off — but the *activation* was never done, and the *loop semantics* were never made first-class. RISK-037 cannot close on schema-only assets.

DEC-097 changes the constraint that shaped 0.51.0-0.55.0: instead of preserving `classic-phase-gate` as the active default and making `dynamic-flow-gate` opt-in, **loop becomes the primary and only model**, and G1-G11 becomes a compatibility/teaching vocabulary over the loops. This is the unblocking move: it stops treating the linear model as sacred.

### 1.7 External research grounding

This design synthesizes loop models from outside (full citations in the external research notes):

- **OODA** (Observe-Orient-Decide-Act) — incident/operations tier.
- **PDCA / Deming / Toyota Kata** — the improvement loop; Toyota Kata's inner-kata + outer-coaching-kata is the canonical *nested* loop pattern.
- **Build-Measure-Learn** (Lean Startup) — the outermost product/strategy loop.
- **Spiral Model (Boehm)** — **risk-driven**: loop count and content are determined by risk profile. This is directly relevant because governance IS risk management.
- **ReAct** (Yao 2022) — the foundational AI agent execution loop (Reason + Act).
- **Reflexion** (Shinn 2023) — verbal self-critique + episodic memory on top of ReAct; the self-reflection loop.
- **QWAN three loops** (inner Build/Verify, middle Deliver/Learn, outer Decide/Adapt) — the most transferable taxonomy.
- **Google CL model + stacked diffs** — review as a loop with exit condition (LGTM / all-blocking-resolved), not a one-shot checkpoint; stacking enables parallel review loops.

The design core that emerges across all sources:

> **A gate is a loop's EXIT condition AND the next loop's ENTRY condition. A failed gate does NOT "fail a stage" — it RETURNS work into the loop for another iteration. Loops and gates are complementary: a gate without a loop on each side is a wall; a loop without a gate never converges.**

---

## 2. Decision

**Adopt a loop-engineering model as the primary and only execution model for software-project-governance.** Concretely:

1. **Three nested main loops** (Outer / Middle / Inner) become the organizing structure, replacing G1-G11 as the primary mental model. G1-G11 stages are re-mapped onto loop roles (loop-setup / loop-body / loop-exit-gate / loop-entry-gate).
2. **A bounded setup-loop** (research → selection → infrastructure, G2/G3/G4) sits between initiation and the first Middle loop. It is pre-delivery, tighter than the three main loops, fused at `MAX_SETUP_ROUNDS=2` (§3.3, §8.1).
3. **Initiation (立项) is the sole non-loop**: a one-time setup that prepares the first setup-loop. It keeps a special gate (G1) but is not itself iterative.
4. **The AI agent's intrinsic loop — Plan-Act-Observe-Reflect — is promoted to an explicitly-named, governable object.** It sits *inside* the Inner loop and is the atomic unit of agent execution. Governance checkpoints are **pause points** inserted between its phases, each with a justified velocity cost.
5. **Gates do not disappear.** Each of the 6 existing `*-review` skills (`requirement-review`, `design-review`, `tech-review`, `code-review`, `test-review`, `release-review`) plus `retro-review` becomes a **loop-exit gate** (certify that a loop's exit condition is met) rather than a "stage inspector." The `gate_execution_registry` (0.54.0, ACTIVE) is extended, not replaced.
6. **Loop latency becomes a first-class governance metric**, bridged to DORA (Deployment Frequency, Lead Time for Changes, Change Failure Rate, MTTR).
7. **The proven task-level review-loop fuse from M7.4 §4.6** (MAX_ROUNDS=3, stateless round derivation, parallel-safe) is **generalized** to flow-unit/loop level. No new loop-control mechanism is invented.
8. **No new logic is added to `verify_workflow.py`** (21,651 lines, TD-001 / RISK-039 God Module). New loop-engineering logic targets the 0.59-0.64 split modules and eventually a thin entry.

This design **breaks backward compatibility** at the primary-model level (DEC-097 part 1), while **preserving the data and assets** invested in 0.51.0-0.55.0 — it *activates* dormant machinery rather than rebuilding it.

---

## 3. The Loop Model

### 3.1 The three nested main loops

The model is a Spiral-at-its-core (risk-driven iteration count), structured as three concentric *main* loops drawn from the QWAN taxonomy. (The setup-loop of §3.3 is a separate, sequential pre-delivery bounded tier — it runs once before entering these delivery loops, not nested inside them.)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OUTER LOOP — Decide/Adapt  (weeks–months; Build-Measure-Learn / PDCA)   │
│  ENTRY: release passed gate   EXIT: strategy/risk profile updated        │
│  Driver: operations + maintenance feedback reshapes the risk map         │
│  Body: release → operate → measure → retro → re-plan                      │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ MIDDLE LOOP — Deliver/Learn  (days–weeks; per flow-unit release)  │   │
│  │  ENTRY: design gate passed   EXIT: release gate passed            │   │
│  │  Body: design → develop → test → release (for ONE flow unit)       │   │
│  │  This is the user's "设计→开发→测试→发布的循环"                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐   │   │
│  │  │ INNER LOOP — Build/Verify  (seconds–minutes–hours)         │   │   │
│  │  │  ENTRY: code gate entry   EXIT: code gate passed            │   │   │
│  │  │  Body: code → test → debug (for ONE slice/commit)           │   │   │
│  │  │  ┌──────────────────────────────────────────────────────┐   │   │   │
│  │  │  │ AGENT INTRINSIC LOOP — Plan-Act-Observe-Reflect      │   │   │   │
│  │  │  │  (atomic; runs inside every Inner iteration)         │   │   │   │
│  │  │  │  PAUSE POINTS sit between its phases (see §5)        │   │   │   │
│  │  │  └──────────────────────────────────────────────────────┘   │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

              ┌──────────────────────────────────────────┐
              │ INITIATION (立项) — NOT a loop            │
              │  one-time setup; prepares the             │
              │  first setup-loop entry                    │
              │  gate_out: G1                              │
              └──────────────────────────────────────────┘
                            │ (G1 passed)
                            ▼
              ┌──────────────────────────────────────────┐
              │ SETUP LOOP (pre-delivery; bounded)        │
              │  research → selection → infrastructure     │
              │  EXIT: G4 pass (infra ready to build)      │
              │  FUSE: MAX_SETUP_ROUNDS = 2                │
              │  Distinct from initiation (no loop/no-fuse)│
              │  and the three main loops (pre-delivery,   │
              │  tighter). See §3.3.                        │
              └──────────────────────────────────────────┘
                            │ (G4 passed)
                            ▼
                   [first Middle loop entry]
```

| Loop | Duration | Analogue | Exit gate(s) | What "iteration" means |
|------|----------|----------|--------------|------------------------|
| **Setup** | hours–days (pre-delivery) | Bootstrap/seed loop; bounded exploration | G2→G3→G4, final exit = G4 (infrastructure ready) | One research→selection→infrastructure attempt; a PoC fail or broken infra restarts selection (G3) or infra (G4) within the setup-loop. Fused at MAX_SETUP_ROUNDS=2 (§3.3, §8.1). |
| **Outer** | weeks–months | Build-Measure-Learn / PDCA outer kata / Spiral outer winding | G10 (operations) + G11 (retro/next-round) | One released-and-operated cycle reshapes the risk map for the next |
| **Middle** | days–weeks | Deliver/Learn; per flow-unit delivery | G5 (design) → G6/G7/G8/G9 chain | One flow unit (e.g. `game.chapter.03`) goes design→dev→test→release |
| **Inner** | seconds–hours | Build/Verify; Google small-CL loop | G6 entry + G6 exit (code review) | One slice/commit goes code→test→debug until review LGTM |
| **Agent intrinsic** | within one Inner iteration | ReAct + Reflexion | (pause points, not gates — see §5) | One Plan-Act-Observe-Reflect cycle; may recurse |

**Why three *nested main* loops, not two or four:** The three-loop split is the empirically most-transferable taxonomy (QWAN) and maps cleanly onto the existing G1-G11 gates (see §4). This argument is scoped to the *concentric/nested runtime loops* that run inside each other during delivery (Inner ⊂ Middle ⊂ Outer). Adding a fourth *nested* main loop would not reduce mapping ambiguity; collapsing to two would merge Inner and Middle and lose the build-vs-deliver latency distinction that DORA requires. The setup-loop (§3.3) is not a counter-example to this argument: it is a separate, non-nested, sequential pre-delivery tier that runs once before the first Middle entry, not a fourth concentric loop. So the coherent taxonomy is **three nested main loops + one pre-delivery bounded setup-loop**.

**Where Spiral lives:** Spiral's risk-driven nature is expressed through **loop count and gate content being set by risk profile** — a high-risk flow unit gets more Inner iterations and tighter Middle exit gates; a low-risk internal-script flow unit (per the `internal-script` preset's `can_skip_stages`) collapses the Middle loop to a single pass. The `profiles.md` intensity (lightweight/standard/strict) and project-type presets already provide the knobs; the design *uses* them rather than adding new ones.

### 3.2 Where initiation (立项) fits — the sole non-loop

DEC-097 part 1 names 立项 as the explicit exception. In this design:

- **Initiation is a one-time setup, not a loop.** It produces the project charter, scope boundary, and initial risk baseline (per `lifecycle.md` §1 and `stage-gates.md` G1).
- Its `gate_out` (G1) is the **entry gate to the setup-loop** (§3.3), which in turn prepares the first Middle loop — i.e. G1 is a loop-entry gate for the project's first setup-loop, not the exit of a loop body.
- Because it is not iterative, it has **no fuse, no loop_count**. Its `loop_state` field (which already exists in `flow_unit_schema`, see §6.2) is `{"active_loop": false, "loop_count": 0, "last_loop_type": "initiation-setup"}`.
- This is why the user said "除了特殊的立项之外" (other than special initiation): 立项 sets the goal that the loops then deliver against. Loops without a goal never converge (Spiral lesson); 立项 provides that goal.

Retro (currently G11) is the *reflection phase of the Outer loop*, not a second special non-loop. The distinction: 立项 happens once at project start and is not revisited; retro happens every Outer iteration and feeds the next.

### 3.3 The setup-loop — research / selection / infrastructure (P1-a resolution)

**The gap (R0 finding P1-a).** The §4 mapping table assigns stages 2/3/4 (research / selection / infrastructure) the role "loop-setup (Middle-loop prep)", but — unlike G5/G6/G7/G9/G11 — their on-fail behavior was unspecified. If G4 (infrastructure) fails, does the setup loop iterate (like a re-attempt) or is it a hard block? Research/selection failing is a common iteration point in real projects (PoC fails → re-select; chosen infra doesn't work → try an alternative). Leaving this unspecified is a coherence gap.

**Resolution: a setup-loop distinct from both initiation and the three main loops.** The setup stages G2/G3/G4 form a **bounded pre-delivery loop**:

- **Distinct from initiation:** initiation (G1) is *no-loop, no-fuse* (one-time). The setup-loop *iterates* — a G3 PoC fail returns to G2 (re-research) or re-runs G3 (re-select); a G4 infra fail returns to G3 (re-select an alternative) or re-runs G4 (re-provision).
- **Distinct from the three main loops:** the setup-loop is *pre-delivery* and *tighter*. It does not produce a flow-unit release; it produces the precondition (infrastructure ready) for the first Middle loop. Its fuse is `MAX_SETUP_ROUNDS = 2` (§8.1) — tighter than Inner and Middle, and tied with Outer (Outer=2 for different reasons: strategy cost; Setup=2 because pre-delivery misjudgment signal); setup failures that don't converge in 2 rounds almost always indicate an architectural-level misjudgment that belongs in initiation (re-scope) or a human escalation, not a third PoC attempt.
- **Loop tier label:** `setup`. In `loop_state.active_loop_tier` the values are now: `setup | inner | middle | outer` (was `inner | middle | outer`).
- **Evidence type:** `LOOP-{flow_unit_id}-setup-R{n}` (parallel-safe stateless derivation, §8.2 — identical mechanism to other tiers).
- **Preset interaction:** `can_skip_stages` in project-type presets (§6.6) already allows `internal-script`/`library` to skip research/selection/infrastructure; for those presets the setup-loop collapses to zero rounds (passes straight through), mirroring how Spiral collapses for low-risk profiles. No preset data change.

**On-fail semantics for G2/G3/G4 (the load-bearing clarification):**

| Gate | On fail (setup-loop, within MAX_SETUP_ROUNDS=2) | On fuse trip (round > 2) |
|------|--------------------------------------------------|--------------------------|
| G2 (research) | iterate setup-loop: re-research (risk-map too thin to start Middle) | escalate (PP-Fuse-Escalate): likely an initiation-level re-scope |
| G3 (selection) | iterate setup-loop: re-select (PoC failed → alternative direction) | escalate (PP-Fuse-Escalate): human picks direction or re-scopes |
| G4 (infrastructure) | iterate setup-loop: re-provision / try alternative infra | escalate (PP-Fuse-Escalate): infra blocker needs human decision |

This closes the coherence gap: every gate in §4 now has a stated on-fail semantics. Setup-stage failures do **not** escalate directly (they are not initiation-like one-shot); they iterate within the setup-loop, fused at 2.

### 3.4 The AI intrinsic loop (Plan-Act-Observe-Reflect) as first-class citizen

**Where it sits:** Inside every Inner-loop iteration. The Inner loop's body (code→test→debug) is *executed by* the agent's intrinsic loop. When the agent writes code, it is in the Act phase; when it runs a test, it Observes; when a test fails, it Reflects and re-Plans.

**Why first-class:** In an AI-governed workflow, the agent loop IS the unit of execution. If governance cannot name it, governance cannot pause it, budget it, or fuse it. Making it an explicit object lets the design:

1. Name pause points precisely (between Plan and Act, between Act and Observe, between Observe and Reflect — see §5).
2. Charge each pause point against loop velocity, forcing a justification (DEC-097 part 2).
3. Apply the Reflexion pattern (self-review before sending to a human reviewer) as a *governance primitive* — the agent's own Reflect phase is the cheapest possible review loop.

**Governable properties of the agent intrinsic loop** (new explicit fields, see §6.3):

- `active_phase`: plan | act | observe | reflect
- `iteration_within_inner`: int (how many agent cycles inside the current Inner loop iteration)
- `pause_points_active`: list of active pause-point ids (see §5.2)
- `velocity_budget_ms` / `velocity_spent_ms`: latency accounting per DEC-097 part 2

**What is NOT changed:** The agent loop's *mechanics* are not replaced. ReAct/Reflexion already exist as how agents work. This design makes them *visible and governable*, it does not impose a new execution algorithm.

### 3.5 Gate-as-loop-exit semantics

This is the design core. Restated concretely against the 6 existing review skills:

| Existing skill | Old semantic ("inspect stage") | New semantic ("certify loop exit") | Loop it certifies |
|----------------|-------------------------------|------------------------------------|-------------------|
| `requirement-review` | inspect 立项 artifacts | certify initiation setup is complete (loop-entry gate for the setup-loop, which precedes the first Middle loop) | (non-loop: initiation) |
| `design-review` | inspect architecture stage | certify a Middle loop's ENTRY — design converges, can begin building this flow unit | Middle (entry) |
| `tech-review` | inspect technical selection/design quality | certify a Middle loop's design sub-iteration converged (risk-driven depth) | Middle (entry, technical depth) |
| `code-review` | inspect development stage | certify an Inner loop's EXIT — slice/commit is mergeable | Inner (exit) |
| `test-review` | inspect testing stage | certify a Middle loop's quality sub-iteration converged | Middle (body, quality) |
| `release-review` | inspect release stage | certify a Middle loop's EXIT — flow unit releasable; entry to Outer | Middle (exit) / Outer (entry) |
| `retro-review` | inspect maintenance stage | certify an Outer loop's iteration converged — learnings backfilled, next round set | Outer (exit) |

**The rule (load-bearing):**

> A gate that FAILS does not fail a stage. It **returns the work into its enclosing loop for another iteration**, increments the loop's `loop_count`, and the agent loop re-Plans against the findings. Only when `loop_count` exceeds the fuse (§8) does the failed gate escalate instead of iterating.

This is why "a gate without a loop on each side is a wall": in the old linear model, a failed G6 left the project stuck between "development" and "testing" with no defined next action except "fix and re-run G6." In the loop model, a failed code-review gate means the Inner loop iterates (agent Reflects on findings, re-Plans, re-Acts) until LGTM or fuse. The work never sits in an undefined inter-stage limbo.

### 3.6 Loop-latency as a first-class governance metric

DEC-097 part 2 requires each pause point to justify its cost to loop velocity. To make "cost" measurable, the design adopts a **DORA bridge** as the velocity vocabulary:

| DORA metric | Loop-engineering expression | What we measure |
|-------------|----------------------------|-----------------|
| **Deployment Frequency** | Outer loop + Middle loop throughput | How many flow units pass their release gate per unit time |
| **Lead Time for Changes** | Middle loop cycle time | Plan entry → release exit, per flow unit |
| **Change Failure Rate** | Inner/Middle fuse-trip rate | Fraction of loops that hit MAX_ROUNDS and escalate |
| **MTTR** | Outer-loop feedback → fix latency | Operations-feedback-to-maintenance-loop time |

These are *not* new external tools. They are computed from the loop_state and pause-point accounting that this design activates (§6.2, §6.3). Loop latency becomes a Check in the governance suite (targeting a split module, §9), reporting "your Middle loops average N days, your Inner loops average M rounds, X% trip the fuse" — turning governance from "did you do the steps" into "is your loop velocity healthy."

This is also how the design earns the Spiral framing: a high Change Failure Rate (fuse trips) is a risk signal that raises the project's risk profile, which in turn justifies tighter gates and more iterations on the next winding — the Spiral's risk-driven loop count, made operational.

---

## 4. Mapping Table — Every G1-G11 Stage → Loop Role

Exhaustive mapping. "Role" uses exactly four values: **loop-setup** (one-time/non-iterative prep), **loop-body** (the work that iterates), **loop-exit-gate** (certifies a loop's exit condition), **loop-entry-gate** (certifies entry into the next loop).

| Stage | Old gate | New loop role | Loop | What it does in the loop model |
|-------|----------|---------------|------|--------------------------------|
| **1. initiation (立项)** | G1 | **loop-setup** (+ loop-entry-gate for first Middle) | (non-loop) | One-time setup: charter, scope, risk baseline. G1 is the entry gate to the project's first Middle loop. NOT iterative — `last_loop_type: "initiation-setup"`. |
| **2. research** | G2 | **loop-body** (setup-loop) + **loop-entry-gate** (setup-loop entry) | **Setup** (P1-a, §3.3) | Feeds the risk map that the setup-loop and first Middle loop build on. G2 is the entry gate to the setup-loop. **On fail:** iterate setup-loop (re-research) within MAX_SETUP_ROUNDS=2 (§3.3, §8.1); on fuse trip → escalate (PP-Fuse-Escalate). `internal-script`/`library` presets skip via `can_skip_stages`. |
| **3. selection** | G3 | **loop-body** + **loop-exit-gate** (setup-loop body, sub-iteration) | **Setup** (P1-a, §3.3) | Technical direction set before the first Middle iteration. G3 certifies risk verified by PoC. **On fail:** iterate setup-loop (PoC failed → re-select alternative) within MAX_SETUP_ROUNDS=2; on fuse trip → escalate. Can be skipped per preset (`game`, `library`, `internal-script` skip it). |
| **4. infrastructure** | G4 | **loop-exit-gate** (setup-loop) / **loop-entry-gate** (first Middle) | **Setup** (exit) / Middle (entry) | Environment/repo/CI ready. G4 is the setup-loop EXIT and the entry gate to the first Middle loop body. **On fail:** iterate setup-loop (re-provision / try alternative infra) within MAX_SETUP_ROUNDS=2; on fuse trip → escalate (PP-Fuse-Escalate). |
| **5. architecture (design)** | G5 | **loop-entry-gate** | Middle (entry) | G5 certifies the Middle loop can BEGIN for this flow unit — design converges. This is the user's "设计" anchor in "设计→开发→测试→发布". On failure: design sub-loop iterates (re-design) — G5 does not fail the project. |
| **6. development** | G6 | **loop-body** + **loop-exit-gate** | Middle (body) / **Inner (whole)** | The development STAGE contains the **entire Inner loop**: code→test→debug per slice. G6-exit certifies an Inner loop's slice review LGTM (code-review gate). This is the user's "开发阶段的修改→检视的循环". |
| **7. testing** | G7 | **loop-body** + **loop-exit-gate** | Middle (body) | Quality sub-iteration per flow unit. G7 certifies the quality sub-loop converged (defects closed, regression pass). On failure → `testing-to-development-rework` back-edge (already declared!) returns work to the Inner loop. |
| **8. ci-cd** | G8 | **loop-body** | Middle (body, toward release) | Safety-net posture for the flow unit. Often merged with testing (per `web-app`/`cli-tool`/`internal-script` `can_merge_stages`). |
| **9. release** | G9 | **loop-exit-gate** (Middle) / **loop-entry-gate** (Outer) | Middle (exit) / Outer (entry) | G9 certifies the Middle loop EXIT — flow unit releasable — and entry to the Outer loop's operate-measure phase. On failure → `release-to-testing-rework` back-edge (already declared!) returns to the testing sub-loop. |
| **10. operations** | G10 | **loop-body** | Outer (body) | Operate + measure + collect feedback. G10 certifies real ops data collected. Feeds the Outer loop's reflection. |
| **11. maintenance / retro** | G11 | **loop-exit-gate** (Outer) | Outer (exit) | G11 certifies the Outer loop's iteration CONVERGED — learnings backfilled, next round direction set. On failure → `operations-feedback-to-maintenance-loop` back-edge (already declared!) keeps the Outer loop iterating. |

**Back-edges already exist (this is why reuse is possible).** The registry already declares three `flow-unit-loop` transitions:

- `testing-to-development-rework` (testing → development) — **this IS the Inner-loop re-entry on test failure.**
- `release-to-testing-rework` (release → testing) — **this IS the Middle-loop iteration on release-gate failure.**
- `operations-feedback-to-maintenance-loop` (operations → maintenance) — **this IS the Outer-loop feedback back-edge.**

The 0.51.0 design *declared* these back-edges but never *activated* them as loop iterations (they sit in a schema-only registry). This design's job is to make them the primary mechanism, not dormant metadata.

**What's still missing in the registry** (gaps this design must address):

1. **No cross-stage design→dev→test→release *iteration* back-edge** beyond the three rework edges. The Middle loop's normal iteration (release fails → re-plan design) is not yet declared as a forward-loop transition. §6.4 adds it.
2. **No loop_count enforcement** — `loop_policy.loop_counter_policy` is literally `"schema-only-recorded-by-future-runtime"`. §8 activates it.
3. **No fuse** at flow-unit level. §8 generalizes MAX_ROUNDS=3.

---

## 5. AI Agent Loop Governance (Plan-Act-Observe-Reflect)

### 5.1 The four phases, made governable

| Phase | What the agent does | Governance question |
|-------|---------------------|---------------------|
| **Plan** | Decide next action from goal + observation | Is the plan within scope_guard / vertical_slice? Does it need human approval (Plan Mode)? |
| **Act** | Execute (write code, run tool, edit file) | Is the action within the declared scope? (M7.5 product-code vs governance-record boundary) |
| **Observe** | Read results (test output, tool return) | Is the observation recorded as evidence? (M7.4 step 1) |
| **Reflect** | Self-critique: did Act move toward goal? Should plan change? | Reflexion: should the agent self-rework before invoking a human reviewer? |

### 5.2 Pause points (DEC-097 part 2: each must justify velocity cost)

A **pause point** is a governance checkpoint inserted between agent-loop phases. It is NOT a gate (gates certify loop exits; pause points are inside the agent's own execution). Every pause point carries a mandatory `velocity_cost_justification`.

| Pause point | Location | Triggered when | Velocity cost | Justification |
|-------------|----------|----------------|---------------|---------------|
| **PP-Plan-Approve** (Plan Mode) | between Plan → Act | plan touches scope_guard boundary OR P0/governance-critical file (per M7.4 step 4) | One human round-trip | Prevents an unfixable Act (e.g. wrong-file edit, scope breach). Cheaper than reverting. **Highest-value pause point** — ReAct + Plan Mode literature. |
| **PP-Act-Scope** | start of Act | every Act | near-zero (automated check) | Cheap guard: does target file match declared scope? (M7.6a file_locks is this, reused.) |
| **PP-Observe-Evidence** | end of Observe | every Observe that yields a fact | near-zero (write to evidence-log) | Makes the loop auditable (M7.4 step 1). Without it, Reflect operates on memory not facts. |
| **PP-Reflect-SelfReview** (Reflexion) | before invoking human reviewer | when a loop iteration is about to claim "done" | One extra agent cycle | Reflexion: agent self-critiques before sending to reviewer → fewer review rounds (empirically, Shinn 2023). Cheaper than a human round. |
| **PP-Fuse-Escalate** | when loop_count > MAX_ROUNDS | fuse trip | One AskUserQuestion (escalation, per M7.4 §4.6) | Prevents infinite loops; the ONLY mandatory human pause point that is NOT optional. |

**The velocity accounting rule (DEC-097 part 2, operationalized):** Every pause point that is NOT near-zero-automated must carry, in its declaration, a one-sentence `velocity_cost_justification`. A pause point without a justification is a protocol violation (mirrors how M7.4 §4.6 makes "skipping review" a violation). The reviewer (Design Reviewer now, Code Reviewer later) may strike any pause point whose justification is "we've always done this" rather than a measured latency tradeoff.

**Enforcement (P1-c resolution):** the "protocol violation" claim is no longer aspirational. A concrete Check is added in `loop_health.py` (§9.5) that (1) **fails** if any active pause point lacks a `velocity_cost_justification` (this operationalizes DEC-097 part 2's "each pause must justify its cost"); and (2) **flags advisory** if measured `velocity_cost_ms` exceeds the justification's stated bound by N× (default 3×) for M consecutive iterations (default 3). The justification-presence check is blocking from day one; the cost-exceedance check starts advisory with a documented advisory→blocking upgrade path deferred to implementation. This resolves §12 Q2.

### 5.3 Plan Mode as a gate (PP-Plan-Approve)

PP-Plan-Approve is the implementation of "Plan Mode" in the AI-coding literature: the agent produces a plan, *pauses*, and a human approves before the agent Acts. In this design:

- It maps directly onto the existing **M7.4 step 4** (交付物审查 before commit, via AskUserQuestion) — *but lifted earlier*: M7.4 step 4 pauses before commit (after Act); Plan Mode pauses before Act (before any change). Both are the same primitive at different loop depths.
- It is triggered by scope/risk, not by "every action" — otherwise it would destroy velocity (DEC-097 part 2's exact concern). Trigger = P0 task OR governance-critical file OR scope_guard boundary touch.
- This is the **highest-value** pause point and the one the Design Reviewer should pressure-test most: too lax and scope creeps, too strict and the agent loop stalls.

### 5.4 Reflection as pre-review (PP-Reflect-SelfReview)

The Reflexion pattern: before the agent asks a human (or Reviewer sub-agent) to review, it self-critiques. In the governance model:

- PP-Reflect-SelfReview runs **before** the code-review gate (Inner loop exit). Its output is a self-critique that travels with the work to the reviewer.
- This is already half-implemented: M7.4 step 3 (自审计 for P0/governance-critical tasks) is a Reflexion step. This design *names* it as PP-Reflect-SelfReview and makes it a first-class loop phase rather than a task-completion side-step.
- Measured benefit (from Reflexion literature + the review-loop fuse data this project already collects): self-review before review reduces average review rounds. The M7.4 §4.6 MAX_ROUNDS=3 fuse exists *because* rounds are expensive; Reflexion lowers the expected round count, raising loop velocity — exactly what DEC-097 part 2 demands.

### 5.5 Sub-agent parallel dispatch (stacked loops)

Stacked-diffs / parallel review loops translate to: **multiple Inner loops running concurrently for different flow units**, each with its own agent intrinsic loop and pause points. This design accommodates it through:

- The existing **M7.6 / M7.6a** parallel-dispatch safety (worktree isolation, agent-locks.json) — reused unchanged. These already solve "two agents editing the same file."
- The flow-unit dependency graph (`flow_unit_schema.dependencies`, `blocked_dependency_rule`) — already declares which units block which. Parallel Inner loops are safe *across* independent flow units; within one unit, the Inner loop is serial (code→test→debug cannot be parallelized for the same slice).
- The `loop_state` field becomes per-flow-unit, so parallel loops each carry their own `loop_count` and fuse — generalizing the task-level MAX_ROUNDS to per-unit (§8).

**Loop type taxonomy** (from external research, mapped to governance triggers):

| Loop type | Trigger | Governance analogue |
|-----------|---------|---------------------|
| **goal-based** | run until objective met | The default — Middle/Inner loops exit on gate pass |
| **hook (event-triggered)** | event fires | `operations-feedback-to-maintenance-loop` — an ops event triggers an Outer iteration |
| **heartbeat (scheduled)** | periodic | Retro cadence (G11) — scheduled Outer-loop reflection |
| **cron (time-triggered)** | deadline | M7.3 risk-escalation deadline check (existing) |

The first two are native to this design; the last two are existing mechanisms re-expressed as loop types.

---

## 6. Reuse Plan — Exactly Which 0.51-0.55 Assets Are Reused and How

This design **activates dormant assets, it does not rebuild them.** Below: each asset, its current state (with exact field/file references), and what "activation" means.

### 6.1 `gate_execution_registry` (0.54.0, ACTIVE) — extend, don't replace

**Current state** (`lifecycle-registry.json` lines 1748-2440): declarative gate engine with `gate_checks[]` for G1-G11, each carrying `required_artifacts`, `checks[]` (with `executor` ∈ {function, snippet_in_file, file_exists, evidence_mentions, completed_ratio, constant_result, research_doc_count}, `severity`, `function`/`path`/`snippet`), `evidence_query`, `automation_command` (metadata-only), `human_confirmation_policy`, `severity`, `project_type_overrides`. `auto_judge_gate()` is already an engine over this registry.

**Reuse action — EXTEND the registry with loop semantics, do NOT change the executor mechanism:**

1. Add a top-level `loop_gate_semantics` block to each gate entry:
   ```json
   "loop_role": "loop-exit-gate",
   "enclosing_loop": "inner",
   "on_fail": "iterate-enclosing-loop",
   "fuse_ref": "FUZE-INNER-DEFAULT"
   ```
2. The `executor` field set stays exactly as-is (function / snippet_in_file / etc.) — the engine already runs them. Loop semantics are metadata the engine reads to decide iterate-vs-escalate.
3. `human_confirmation_policy.needs_human_when` already exists and already maps to AskUserQuestion (per stage-gates.md principle 10 / M5). PP-Plan-Approve and PP-Fuse-Escalate reuse this field — no new confirmation mechanism.

**Why this is reuse not rebuild:** The registry is 0.54.0's investment and is ACTIVE (`status: "active-classic-compatibility"`). DEC-097 changes the *default lifecycle mode* and the *gate semantics*, not the gate *engine*. The engine that reads `gate_checks[]` and runs `function` executors is reusable as-is.

### 6.2 `flow_unit_schema.loop_state` (declared, dormant) — ACTIVATE

**Current state** (`lifecycle-registry.json` lines 503-567): `loop_state` is a **required field** of `flow_unit_schema` (line 520), with value shape `{active_loop, loop_count, last_loop_type}`. In every example (lines 749-753, 779-783, etc.) it is `{false, 0, null}` — **declared but never active**.

**Reuse action — populate loop_state at runtime:**

```json
"loop_state": {
  "active_loop": true,
  "active_loop_tier": "inner",          // NEW: setup | inner | middle | outer (setup added by P1-a, §3.3)
  "loop_count": 2,                       // iterations of the active loop
  "last_loop_type": "defect-rework",     // from allowed_loop_types (line 493)
  "agent_phase": "reflect",              // NEW: plan|act|observe|reflect (§5.1)
  "iteration_within_inner": 4,           // NEW: agent cycles in current Inner iter
  "pause_points_active": ["PP-Reflect-SelfReview"],  // NEW (§5.2)
  "last_gate_result": "NEEDS_CHANGE",    // NEW: drives iterate-vs-escalate
  "fuse": {"max_rounds": 3, "tripped": false}        // NEW (§8)
}
```

The 3 original fields stay (backward compatible with the schema). The 5 new fields activate the dormant machinery. This is the single most important activation in the design: **the loop_state field was built for exactly this and never turned on.**

### 6.3 New explicit objects (named, governable) — minimal additions

DEC-097 part 2 requires the agent loop to be "an explicitly-named object." This needs three new named objects, all living in the (to-be-split) governance domain, NOT in verify_workflow.py (§9):

1. **`AgentIntrinsicLoop`** — named representation of Plan-Act-Observe-Reflect for one flow unit. Fields: the §6.2 additions (`active_loop_tier`, `agent_phase`, `iteration_within_inner`, `pause_points_active`, `last_gate_result`, `fuse`).
2. **`PausePoint`** — named representation of a §5.2 pause point. Fields: `id`, `location` (between which phases), `trigger`, `velocity_cost_ms` (measured), `velocity_cost_justification` (mandatory text), `active`.
3. **`LoopFuse`** — named representation of §8 fuse. Fields: `loop_tier`, `max_rounds`, `current_round` (derived stateless from evidence-log, per M7.4 §4.6 C7), `escalation_exit` (AskUserQuestion per M7.4 §4.6).

These are *declarations* (data objects), not new algorithms. Their behavior is implemented by generalizing the M7.4 §4.6 state machine (§8).

### 6.4 Declared back-edges (3 exist) — promote to primary; add the missing Middle-loop iteration

**Existing 3 back-edges** (`allowed_transitions`, lines 461-487): `testing-to-development-rework`, `release-to-testing-rework`, `operations-feedback-to-maintenance-loop`. These are `transition_type: "flow-unit-loop"` / `"flow-unit-feedback-loop"`.

**Reuse action:** Promote these from "declared but dormant" to the **primary iteration mechanism**. When a gate fails, the engine follows the back-edge (not "stuck between stages"). `runtime_activation` flags flip to true (§7).

**Gap to fill — add the Middle-loop design iteration back-edge (P1-b tightened).** The three existing back-edges cover: test-fail→redev, release-fail→retest, ops-feedback→retro. **Missing:** release-fail that indicates a *design* problem → redesign (Middle loop top). Unlike the other three back-edges, this one crosses the *entire* Middle loop (release back to architecture) — a much longer arc. R0 finding P1-b flagged the original weak trigger ("design-rooted cause recorded in findings") as rubber-stampable: a reviewer could self-certify "design-rooted" to force a redesign path. The conservative resolution: **this back-edge CANNOT fire automatically.** It requires three conjunctive conditions and a mandatory human pause point (PP-Fuse-Escalate) by default:

```json
{
  "id": "release-to-design-replan",
  "from_stage": "release",
  "to_stage": "architecture",
  "gate_references": ["G9", "G5"],
  "transition_type": "flow-unit-middle-loop-iteration",
  "auto_fire": false,
  "trigger": {
    "requires_all_of": [
      { "gate": "G9", "result": "fail", "evidence": "release-review findings recorded" },
      { "gate": "G5", "concurrence": "design-review concurs the root cause is design-level (architecture/selection), recorded in G5 findings, NOT merely a build/test/release defect" },
      { "pause_point": "PP-Fuse-Escalate", "human_approval": "explicit human authorization to restart the Middle loop from design (rationale: a full Middle-loop restart is expensive and must not be rubber-stamped)" }
    ]
  }
}
```

**Trigger discipline (P1-b):** the three conjuncts prevent thrashing:
1. **G9 fail** — the release gate must actually fail; a pass never fires this edge.
2. **G5 concurrence** — the *design-review gate* (not the release reviewer alone) must concur the root cause is design-level (architecture or technical-selection), not a build/test/release defect. This blocks the rubber-stamp: a single reviewer cannot self-certify "design-rooted"; it requires the gate that owns design (G5) to agree. A build defect that *manifests* at release goes to `release-to-testing-rework`, not here.
3. **PP-Fuse-Escalate human approval** — by default this back-edge requires explicit human authorization. A full Middle-loop restart (design→dev→test→release) is expensive; conservative policy is that it never fires automatically. The Middle fuse (§8.1, max_rounds=3) still bounds total rounds, but the human gate is the primary guard against design↔release thrashing.

**Rationale for default-`auto_fire: false`:** Q5 (§12) asked whether this back-edge needs a human pause point. The resolution: yes, by default. This is the conservative choice for any back-edge whose arc exceeds a single sub-loop hop. If, post-implementation, telemetry shows the human gate is never the right intervention (e.g. the G5-concurrence check already filters false positives cleanly), the implementation may expose a `auto_fire: true` opt-in per project-type preset — but the default stays human-gated. Q5 is resolved (see §12).

This is the only structural addition to `allowed_transitions`. It completes the Middle loop's iteration graph while bounding its most expensive arc behind a human gate.

### 6.5 M7.4 §4.6 review-loop state machine — generalize, don't reinvent (sacred)

**Current state** (`behavior-protocol.md` lines 493-536): a task-level review-loop state machine with:
- States: 待审查 → 审查中(R0) → {APPROVED ✓ | NEEDS_CHANGE → rework → 审查中(R{n+1}) | BLOCKED → escalation ✗}
- **MAX_ROUNDS = 3** fuse (C3): round > 3 NEEDS_CHANGE → MUST escalate, no infinite loop, no "reluctant APPROVED."
- **Stateless round derivation (C7):** round is derived entirely from the max existing R{n} in evidence-log — no in-memory state, parallel-safe.
- Two terminals only: APPROVED or BLOCKED→escalation (C4).
- Degraded-mode cap: ≤2 degraded reviews per task, 3rd forces BLOCKED.

**This is the proven loop pattern. The design generalizes it, it does NOT invent a new loop-control mechanism.**

**Generalization to flow-unit/loop level (§8 details the fuse):**

| M7.4 §4.6 (task level) | Generalized (loop level) |
|------------------------|--------------------------|
| `task_id` | `flow_unit_id` + `loop_tier` |
| `REVIEW-{task_id}-R{n}` evidence | `LOOP-{flow_unit_id}-{tier}-R{n}` evidence (new evidence type) |
| MAX_ROUNDS=3 (review) | `LoopFuse.max_rounds` per tier (Setup=2, Inner=5, Middle=3, Outer=2 — see §8) |
| stateless round from evidence-log max R{n} | identical mechanism, identical parallel-safety proof |
| escalation via AskUserQuestion (4 options) | identical exit |
| degraded-mode cap (≤2) | identical cap, applied per loop |

**Why this is sacred:** M7.4 §4.6 is the ONLY loop mechanism in the project that is (a) validated (Check 30), (b) parallel-safe (stateless), and (c) has a working fuse. Inventing a new one would violate "reuse over rebuild" and reintroduce the infinite-loop risk the fuse was built to prevent.

### 6.6 Project-type presets (0.53.0) — reused as loop-content selectors

**Current state** (`project_type_gate_presets`, lines 1007-1746): 7 presets (game/web-app/mobile-app/library/cli-tool/ai-agent-plugin/internal-script), each with `default_flow_unit_type`, `unit_templates`, `quality_budget`, `acceptance_templates`, `release_checks`, `gate_policy` (`can_skip_stages`, `can_merge_stages`), `gate_standards`.

**Reuse action:** These become **Spiral's risk-profile drivers.** A preset's `can_skip_stages` and `can_merge_stages` directly determine loop content:
- `internal-script.can_skip_stages: [research, selection, release]` → Outer loop minimal, Middle loop collapsed (architecture+development merged, testing+ci-cd merged).
- `game.gate_policy.can_merge_stages: [[architecture, development], [testing, ci-cd]]` → Middle loop allows design+build as one sub-iteration.
- `library` semver discipline → tighter Middle exit gate (G9) for API-changing units.

No preset data changes. They are read by the loop engine to set per-unit loop depth.

### 6.7 Vertical-slice delivery packet — reused as Inner-loop output unit

**Current state** (`templates/vertical-slice-delivery-packet.md`): a packet with `user_visible_slice`, `demo_path`, `scope_guard`, `rollback_plan`, `status`, `evidence`.

**Reuse action:** The vertical slice IS the Inner loop's deliverable. `scope_guard` IS PP-Act-Scope's check target (§5.2). `rollback_plan` IS the Inner loop's undo path when an iteration fails. No template change; the packet is re-described as "one Inner-loop iteration's output."

### 6.8 `resolve_entry.py` double-root model (0.64.0) — reused for host-vs-plugin fact separation

**Current state** (`infra/resolve_entry.py`, 360 lines, 0.64.0): separates `PLUGIN_HOME` (locate executables + read active version from SKILL frontmatter) from `HOST_PROJECT_ROOT` (read `.governance/` facts). Fixes the VAL-005/006 blocker where the plugin read its own dogfood state instead of the host project's.

**Reuse action:** Loop-engineering runtime MUST read `HOST_PROJECT_ROOT/.governance/flow-unit-runtime.json` (the activated loop_state store) from the host, never the plugin. `resolve_entry.py` is the established, RISK-040-gated mechanism for this. New loop logic calls it; it does NOT re-derive roots. This also means the design inherits RISK-040's divergence-test discipline (cwd ≠ plugin-root ≠ skill-path).

### 6.9 `task-gate-model.md` — reused as the dependency-graph substrate

**Current state** (`core/task-gate-model.md`): task-level gates + explicit dependency graph + `workflow_model: agent-team` vs `phase-gate`.

**Reuse action:** The dependency graph (`dependencies` column, transitive blocking, parallel-safe independent tasks) is exactly the substrate for parallel Inner loops across flow units (§5.5). `workflow_model` gains a third value: `loop-engineering` (superseding both `phase-gate` and `agent-team` as the default). The dependency graph mechanism is unchanged.

---

## 7. Migration Path — Classic G1-G11 → Loop-Engineering (the blocked `--apply`)

### 7.1 What's currently blocked

`verify_workflow.py:20352 cmd_dynamic_lifecycle_migration`: `--apply` is blocked (`sys.exit(1)` at line 20361-20363). Only `--dry-run` works. The `docs/migration/dynamic-flow-gate-migration-0.55.0.md` guide is explicit: no write path, no rollback path, classic stays active/default.

DEC-097 part 1 unblocks this: loop becomes the only model, so the migration is no longer "opt-in to a parallel model" but "convert the primary model."

### 7.2 The `--apply` path (design; implementation targets split module, §9)

The activated `--apply` performs a **read-then-write** transformation with mandatory backup:

```
1. resolve_entry.py → confirm HOST_PROJECT_ROOT (RISK-040 C1-C5 hard constraints)
2. read .governance/plan-tracker.md → hash (SHA-256, evidence_preservation contract from 0.55.0)
3. read .governance/evidence-log.md → hash
4. backup both to .governance/archive/migration-{version}-{timestamp}/
5. derive flow units from target state (the VAL-006 gap, §7.4):
     - one flow unit per declared chapter/module/story/screen/etc.
     - map each unit's current "stage" to a loop_state (loop_count=0, last_loop_type=<derived>)
     - if target has no decomposable units → single flow unit = whole project
6. set workflow_model: loop-engineering (was: phase-gate or agent-team)
7. write .governance/flow-unit-runtime.json (the file that currently "doesn't exist")
8. write migration record to evidence-log: MIGRATION-{version} with before/after hashes
9. print structured result (same JSON shape as dry-run preview, + applied: true)
```

**Fail-closed cases** (reuse the 0.55.0 list + add loop-specific):
- Missing plan-tracker / evidence-log (0.55.0)
- Evidence log has no parseable rows (0.55.0)
- HOST_PROJECT_ROOT unresolvable (RISK-040 C4)
- Target already claims loop-engineering active (idempotency guard)
- Derived flow units = 0 (target has no decomposable structure AND no fallback single-unit)

### 7.3 Rollback

Because step 4 backs up plan-tracker + evidence-log with hashes, rollback is:

```
1. operator: dynamic-lifecycle-migration --rollback --target <path>
2. verify .governance/archive/migration-{version}-{timestamp}/ hashes match
3. restore plan-tracker.md + evidence-log.md from backup
4. set workflow_model back to prior value (phase-gate / agent-team)
5. remove .governance/flow-unit-runtime.json
6. write rollback record to evidence-log
```

**Rollback is total** (restores exact prior state) because the migration only adds `flow-unit-runtime.json` and changes `workflow_model` + adds evidence rows — it never destroys the classic gate history. This satisfies the 0.55.0 guide's demand: "A future write-capable migration must ship a separate command, independent review, backup plan, and rollback proof."

### 7.4 The VAL-006 gap — target-derived flow-unit generation

VAL-006 proved flow units only come from the `python_game` example, not derived from real non-game targets. The migration's step 5 (derive flow units from target state) is the unblocking work:

- **Game target:** derive from chapter/level structure (already works — the python_game example).
- **Web-app/mobile-app target:** derive from `story`/`screen`/`module` decomposition in plan-tracker. If plan-tracker tasks lack a unit-type prefix, group by feature area.
- **Library target:** derive from `module`/`api-surface` (public API boundaries).
- **CLI target:** derive from `command` (one flow unit per command).
- **ai-agent-plugin target:** derive from `adapter`/`skill`/`manifest`.
- **Fallback:** if no decomposition is detectable, create ONE flow unit = `{project_id}.whole` with a recorded `derivation_reason: "no-decomposable-structure-found"`. This is honest (doesn't fake granularity) and still activates loop semantics at project level.

**This is implementation work**, not design — but the design specifies the derivation rules so the implementer has a contract. VAL-006's closure requires running this derivation on a real non-game target and archiving the result.

---

## 8. Loop Fuse/Budget — Generalize MAX_ROUNDS=3

### 8.1 The generalized fuse

M7.4 §4.6's task-level MAX_ROUNDS=3 generalizes to a **per-tier LoopFuse**. The fuse is the ONLY mechanism that prevents infinite loops; it is non-optional.

| Loop tier | `max_rounds` default | Rationale | Escalation |
|-----------|---------------------|-----------|------------|
| **Setup** | 2 (P1-a, §3.3) | Setup iterations (research/selection/infra) are pre-delivery; a failure that doesn't converge in 2 rounds almost always indicates an initiation-level misjudgment, not a third PoC attempt. Tighter than Inner/Middle because no flow unit is in-flight yet. | Fuse trip → escalate (PP-Fuse-Escalate): likely an initiation re-scope or a human infra/direction decision. Evidence type `LOOP-{U}-setup-R{n}`. |
| **Inner** | 5 | Inner iterations are cheap (seconds-minutes); allow more before escalating. Google small-CL data: most reviews converge in ≤3 rounds; 5 gives margin. | Fuse trip → escalate to human (PP-Fuse-Escalate) OR split the slice (reduce scope, restart Inner). |
| **Middle** | 3 | Middle iterations are expensive (days); 3 is the proven M7.4 default. | Fuse trip → escalate: split the flow unit, reduce scope, or accept degraded release (with degraded-evidence contract from M7.4 §4.6). |
| **Outer** | 2 | Outer iterations are very expensive (weeks-months); 2 max — a project that can't converge its Outer loop in 2 windings has a strategy problem, not a process problem. | Fuse trip → escalate: strategy review (this is Spiral's "the risk profile itself is wrong"). |

**Tunability:** These are defaults in `LoopFuse`; `profiles.md` intensity and project-type presets can tighten (never loosen beyond the Spiral risk-driven justification). A `strict` profile may set Inner=3; an `internal-script` may set Outer=1.

### 8.2 Stateless round derivation (the sacred property, preserved)

Per M7.4 §4.6 C7: round is derived **entirely** from the max existing `R{n}` in evidence-log. Generalized:

```
For loop tier T, flow unit U:
  current_round = max({n | evidence-log has LOOP-{U}-{T}-R{n}})
  (0 if none)
```

This is **parallel-safe by construction** (no in-memory counter; two concurrent agents reading the same evidence-log derive the same round). This is the property that makes the fuse safe under M7.6/M7.6a parallel dispatch — and it MUST be preserved in the generalization.

The tier `T` ranges over `{setup, inner, middle, outer}` (setup added by P1-a, §3.3). The setup-loop uses evidence type `LOOP-{U}-setup-R{n}` and derives rounds identically to the other tiers — no special path.

### 8.3 Escalation (reuse M7.4 §4.6 exit verbatim)

On fuse trip, escalation via AskUserQuestion (the M7.4 §4.6 exit, generalized):

> Loop {tier} for flow unit {U} tripped fuse at round {N}. Last result: {NEEDS_CHANGE/BLOCKED}. Options: (1) human arbitration (2) split the unit / reduce scope (3) accept degraded (degraded evidence, explicitly NOT counted as pass) (4) withdraw the unit.

Two terminals only (C4 preserved): APPROVED or BLOCKED→escalation. No "reluctant APPROVED at round N+1" (C5 preserved). Degraded cap (≤2 per unit, C-degraded preserved).

### 8.4 Loop budget vs. fuse

**Fuse** = hard stop (max_rounds). **Budget** = soft signal (latency/velocity). The DORA-bridge metrics (§3.6) are the budget: a Middle loop averaging 2.8 rounds (near the 3 fuse) is a *budget warning* even if it hasn't tripped. Budget warnings surface in the loop-latency Check (§9) as advisory; only fuse trips block.

---

## 9. The `verify_workflow.py` Constraint — Where New Logic Lives

### 9.1 The hard constraint

`verify_workflow.py` is **21,651 lines** (TD-001 in `technical-debt-ledger.md`, RISK-039). DEC-083 + RISK-039 mandate: **no new logic in this file.** The 0.59-0.64 split roadmap (DEC-083 part 3) is progressively extracting check domains into modules.

### 9.2 Where loop-engineering logic lives

| Logic | Target module | Status of target |
|-------|---------------|------------------|
| `AgentIntrinsicLoop` / `PausePoint` / `LoopFuse` declarations | `core/loop-engineering-registry.json` (new, data — like lifecycle-registry.json) | New file, NOT in verify_workflow.py |
| Loop-state read/write, fuse derivation, iterate-vs-escalate engine | `infra/loop_engine.py` (new module) | New file. The split roadmap's pattern: extract domain → thin entry delegates (see `verify-workflow-split-phase1-manifest-domain-0.59.0.md` §3 methodology). |
| `--apply` migration (§7.2) | `infra/loop_migration.py` (new module) | New file. Reuses `resolve_entry.py` for roots. |
| Flow-unit derivation (§7.4) | `infra/flow_unit_derive.py` (new module) | New file. |
| `check-loop-health` (DORA-bridge, §3.6; velocity-justification sub-check, §9.5) | `infra/loop_health.py` (new module) | New file. Registered as a new CLI command following the Phase-1 pattern (argparse subparser + dispatch + thin `cmd_check_loop_health` in verify_workflow.py that ONLY delegates — ~10 lines, the "thin entry" discipline). |
| `loop-engineering-migration --apply/--rollback` | thin `cmd_loop_engineering_migration` in verify_workflow.py (~15 lines, delegates to `loop_migration.py`) | Thin entry only — mirrors `cmd_dynamic_lifecycle_migration` but delegates. |

### 9.3 The thin-entry discipline (from the Phase-1 split methodology)

`verify-workflow-split-phase1-manifest-domain-0.59.0.md` §3 establishes the pattern: extract domain functions to a module, leave only a thin `cmd_*` dispatcher in verify_workflow.py that delegates. The loop-engineering commands follow this: the `cmd_*` functions in verify_workflow.py are **≤20 lines each**, purely argparse-glue + delegation. All real logic is in the new `infra/loop_*.py` modules. ArchGuard (`check-architecture-health`, 0.58.0) guards that verify_workflow.py does not grow — this design's commands must pass ArchGuard's module-size check.

### 9.4 Sequencing with the split roadmap

DEC-083's roadmap (0.59-0.64 split, now partially reshuffled by DEC-096 for the 0.64.0 entry-resolver) extracts domains incrementally. Loop-engineering logic should land **after** the governance-domain split (so it has a clean home) but does not *block* on full split completion — it can land in new `infra/loop_*.py` files independently, since those are net-new, not extractions. The Design Reviewer should confirm this does not conflict with the split's per-version domain assignments.

### 9.5 Velocity-justification enforcement Check (P1-c resolution)

**The gap (R0 finding P1-c).** §5.2 requires a `velocity_cost_justification` per pause point and says "a pause point without a justification is a protocol violation" — but R0 found no check enforces this. Q2 honestly asked whether a hard gate should disable high-cost pause points at runtime. This subsection adds a concrete Check design that operationalizes DEC-097 part 2 ("each pause must justify its cost").

**Module:** `infra/loop_health.py` (same new module that hosts the DORA-bridge `check-loop-health`, §9.2). The velocity-justification sub-check is a sub-function of `check-loop-health`, invoked with the same evidence sources (the `flow-unit-runtime.json` activated store + the `PausePoint` declarations).

**Check design — two parts:**

**Part 1 — Justification-presence (BLOCKING from day 1).**
- **Input:** the set of active `PausePoint` declarations (`pause_points_active` per flow unit, §6.2/§6.3) and each pause point's `velocity_cost_justification` field.
- **Rule:** for every active pause point, `velocity_cost_justification` must be a non-empty string.
- **On violation:** the Check returns FAIL with a per-violation line: `PP {id} active but velocity_cost_justification missing — protocol violation (DEC-097 part 2)`.
- **Severity:** blocking. This is the direct enforcement of "a pause point without a justification is a protocol violation."

**Part 2 — Cost-exceedance (ADVISORY initially; documented upgrade path).**
- **Input:** each pause point's declared `velocity_cost_ms` bound (parsed from the justification text or a structured field) and the *measured* `velocity_cost_ms` from the loop-latency accounting (§3.6).
- **Rule:** if measured `velocity_cost_ms` > N × declared bound (default `N = 3`) for M consecutive iterations (default `M = 3`) for the same pause point id, flag it.
- **On violation:** the Check returns ADVISORY (warning, not fail) with: `PP {id} measured cost {measured}ms exceeds justified bound {bound}ms by {N}× for {M} consecutive iterations — review justification or re-tune the pause point`.
- **Severity:** advisory at first. **Documented upgrade path:** the implementation exposes a config flag `velocity_check_blocking` (default `false`); flipping it to `true` promotes Part 2 to blocking. The upgrade is deferred to implementation, gated on collecting real telemetry about whether the 3×/3-iteration threshold has acceptable false-positive rate. This mirrors how RISK-039 architecture-health started advisory.

**Why Part 1 blocking, Part 2 advisory:** missing justifications are an unambiguous declaration defect (cheap to detect, no telemetry needed) — blocking is safe. Cost-exceedance depends on measured latency distributions that don't exist yet post-design; forcing it blocking prematurely would either (a) fire on noise or (b) pressure authors to over-state bounds to avoid the check, defeating its purpose. Advisory-first lets the threshold calibrate against real data, with a pre-declared path to blocking.

**Outputs:** both parts write findings to the evidence-log under evidence type `LOOP-HEALTH-{flow_unit_id}-velocity`, and Part 1 failures surface in the loop-health CLI report. This is consistent with the stateless, evidence-log-grounded discipline of §8.2.

---

## 10. Impact on RISK-037 Closure Criteria

RISK-037's closure standard (from `.governance/risk-log.md` row 38), broken into its constituent criteria, with honest assessment of what THIS DESIGN solves vs. what needs implementation:

| # | Closure criterion (paraphrased from risk-log) | This design's status |
|---|-----------------------------------------------|----------------------|
| 1 | Dynamic lifecycle registry published and versioned | **Met (0.51.0)** — `lifecycle-registry.json` exists, versioned. This design extends it, doesn't re-publish from scratch. |
| 2 | plan-tracker supports flow units / task-gate rollup (no more single `当前阶段`) | **DESIGN-MET, IMPL-PENDING.** This design specifies the rollup (per-flow-unit loop_state, §6.2) and the migration to write `flow-unit-runtime.json` (§7). Implementation is the `--apply` path + plan-tracker field additions. **Not closed by this ADR.** |
| 3 | At least game + one non-game project type preset has runnable gate standards | **Met (0.53.0)** — game + library + 5 others, with validator/tests. |
| 4 | Declarative gate engine keeps classic G1-G11 compatibility | **DESIGN-MET (DEC-098), IMPL-PENDING.** The DEC-097-vs-criterion-4 tension (P0 in REVIEW-AUDIT-130-R0) is resolved by **DEC-098**: "compatibility" is re-scoped to mean *(a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3)*, not a parallel active classic mode. Classic G1-G11 becomes a vocabulary over loops (§4 mapping: every stage maps to a loop role, including the setup-loop for G2/G3/G4 per P1-a). The gate engine (`gate_execution_registry`) is fully reused (§6.1). Classic is preserved as a rollback target — §7.3's rollback restores the exact prior classic-gate state, so the classic mode remains reachable if activation is reversed. Implementation must verify every classic gate still resolves to a loop role; the mapping table in §4 is the contract. No change to design-met-impl-pending status. §12 Q3 is resolved (see Q3). |
| 5 | Migration guide + external validation proving real projects can express multiple chapters/modules at different stages | **DESIGN-MET, IMPL-PENDING.** This design specifies the `--apply` migration (§7) and flow-unit derivation (§7.4). External validation (re-running VAL-005/VAL-006 with the activated runtime) is implementation work. **Not closed by this ADR.** |
| 6 | Apply/write path or explicit conservative handling | **DESIGN-MET, IMPL-PENDING.** §7 designs the `--apply` + `--rollback` path that is currently `sys.exit(1)`. **Not closed by this ADR.** |
| 7 | Installed-state full PASS or acceptable failure archive | **IMPL-PENDING.** Depends on criterion 5/6 implementation. **Not closed by this ADR.** |
| 8 | Non-game target-derived flow-unit generalization boundary | **DESIGN-MET, IMPL-PENDING.** §7.4 specifies derivation rules per project type + fallback. Validation requires running on a real non-game target. **Not closed by this ADR.** |

**Honest summary:** This ADR *designs* the unblocking for criteria 2, 5, 6, 8 (the four that were unmet). It does not *close* them — closure requires implementation + external validation + archiving, per the no-overclaim discipline (§11). Criteria 1, 3 were already met by 0.51.0/0.53.0. Criterion 4's design tension is resolved by **DEC-098** (compatibility = (a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3), §12 Q3); it is now DESIGN-MET, IMPL-PENDING like the others. No criterion is closed by this ADR alone.

---

## 11. No-Overclaim Boundaries

This section is mandatory given the project's history of conservative versioning (every 0.5x.0 release explicitly states what it does NOT close/claim).

**This ADR does NOT:**
- Change any product code. It is a design document only (DEC-097 part 3).
- Close RISK-037. Closure requires implementation of §7 (migration), §6.2 (loop_state activation), re-running VAL-005/VAL-006 with activated runtime, and archiving results. This ADR designs those; it does not perform them.
- Close RISK-036 (official submission), RISK-039 (architecture health — though this design respects it via §9), or RISK-040 (entry resolver — though this design reuses its output).
- Claim 1.0.0 readiness. 1.0.0 remains blocked until RISK-036 AND RISK-037 close per their recorded standards.
- Decide the version number. Version承载 is decided after Design Reviewer approval (DEC-097 part 3). The "0.65.0-proposed" in the filename is a placeholder.
- Claim the loop model is validated. It is designed, grounded in external research + existing assets. Validation is post-implementation.
- Reinvent the M7.4 §4.6 fuse. It generalizes it (§8). Reinvention would violate the sacred-pattern principle.

**This ADR DOES:**
- Break backward compatibility at the primary-model level (DEC-097 part 1) — this is an accepted, user-mandated break, not an accidental one.
- Specify where new code lives (split modules, §9) and where it must NOT live (verify_workflow.py monolith).
- Provide a concrete, file-path-grounded, field-name-grounded design that a Design Reviewer can pressure-test and an implementer can build against.

---

## 12. Open Questions for the Design Reviewer

These are genuine design tensions. I am asking the reviewer to pressure-test them, not rubber-stamp.

### Q1 — Is "loop is the ONLY model" compatible with a migration that preserves classic evidence?

DEC-097 part 1 says loop is the only model and breaks backward compatibility. But RISK-037 closure criterion 4 says "declarative gate engine keeps classic G1-G11 compatibility," and the 0.55.0 migration guide mandates `plan-tracker is preserved; evidence-log is preserved`. **Tension:** if loop is the ONLY primary model, what does "preserve classic" mean? My design's answer (§4): classic G1-G11 becomes a *vocabulary/teaching layer over loops*, and the evidence is preserved verbatim while `workflow_model` flips to `loop-engineering`. Is that reinterpretation acceptable, or does the user want a literal parallel `classic-phase-gate` mode to persist as a fallback? (My recommendation: vocabulary-over-loops; a parallel mode contradicts "loop is the ONLY model.")

### Q2 — Pause-point velocity justification: how is "cost" measured before the loop runs? — RESOLVED (P1-c)

DEC-097 part 2 requires each pause point to justify its cost to loop velocity. But velocity cost can only be *measured* after the loop has run enough times to gather latency data. The original tension: at design time, the justification is qualitative; at runtime, it becomes quantitative.

**Resolution (P1-c):** The qualitative-at-declaration / quantitative-at-runtime split is retained, AND a concrete enforcement Check is added in `loop_health.py` (§9.5). Part 1 is **blocking**: any active pause point missing a `velocity_cost_justification` fails the check (this is the direct enforcement of "a pause point without a justification is a protocol violation"). Part 2 is **advisory**: if measured `velocity_cost_ms` exceeds the justified bound by 3× for 3 consecutive iterations, the check flags it. Part 2 starts advisory with a pre-declared config flag (`velocity_check_blocking`) to promote it to blocking once real telemetry calibrates the threshold. So the answer to "does the reviewer want a hard gate that disables high-cost pause points at runtime?" is: yes for the missing-justification case (blocking now), and advisory-with-upgrade-path for the cost-exceedance case (not premature-blocking, because latency distributions don't yet exist to set a sound threshold). This operationalizes DEC-097 part 2 without over-constraining on un-measured data.

### Q3 — Does making loop primary satisfy RISK-037 criterion 4, or reopen it? — RESOLVED (DEC-098, P0)

RISK-037 closure criterion 4 explicitly requires "declarative gate engine keeps classic G1-G11 compatibility." DEC-097 part 1 makes loop the only primary model. These are in direct tension if "compatibility" means "a runnable classic mode."

**Resolution (DEC-098, the P0 from REVIEW-AUDIT-130-R0):** criterion 4 is formally re-scoped by **DEC-098**, which records that "compatibility = (a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3), not parallel active mode." My §4 recommendation was adopted: classic G1-G11 becomes a vocabulary over loops (every stage maps to a loop role, now including the setup-loop for G2/G3/G4 per P1-a), and the gate engine (`gate_execution_registry`) is fully reused (§6.1); the classic mode is preserved as a rollback target because §7.3's rollback restores the exact prior classic-gate state. The re-scope is auditable via DEC-098, so the closure is not silent. Criterion 4 status is now **DESIGN-MET, IMPL-PENDING** (§10) — implementation must verify every classic gate resolves to a declared loop role.

### Q4 — Inner-loop fuse default of 5: too lax or too strict?

I set Inner `max_rounds=5` (§8.1) on the reasoning that Inner iterations are cheap and Google small-CL data shows most reviews converge in ≤3, so 5 gives margin. **Question:** is 5 right, or should Inner mirror Middle's 3 for consistency? The risk of 5: a stuck agent loops 5 times burning tokens before escalating. The risk of 3: a legitimately complex slice gets force-escalated. My lean: 5 for Inner (cheap), 3 for Middle (expensive) — asymmetric by cost. Reviewer to confirm or override.

### Q5 — The `release-to-design-replan` back-edge: does it risk unbounded Middle loops? — RESOLVED (P1-b)

§6.4 adds a `release-to-design-replan` back-edge for release failures with design-rooted causes. This completes the Middle loop's iteration graph, but it also means a release failure can send work all the way back to design (architecture stage) — a long back-edge. The original question asked whether the weak trigger ("design-rooted cause recorded in findings") was strong enough, or whether the back-edge should require a human pause point.

**Resolution (P1-b):** The back-edge now requires a human pause point by default. It cannot fire automatically. The trigger is tightened to three conjunctive conditions: (1) G9 fail, (2) G5 (design-review) concurrence that the root cause is design-level — blocking the rubber-stamp by requiring the design-owning gate to concur rather than letting a single reviewer self-certify, and (3) PP-Fuse-Escalate human approval. The Middle fuse (max_rounds=3) remains a secondary bound. The conservative default (`auto_fire: false`) holds for any back-edge whose arc exceeds a single sub-loop hop. Implementation may expose a per-preset opt-in to `auto_fire: true` only if telemetry proves the G5-concurrence filter is sufficient; the default stays human-gated. See §6.4 for the full declaration.

### Q6 — Should loop-latency (DORA bridge) be advisory or blocking?

§3.6 / §8.4 specify loop-latency metrics as advisory (budget) while fuse trips are blocking. **Question:** should sustained bad latency (e.g. Middle loops averaging 2.8 rounds for 3 consecutive units) become a blocking gate, or stay advisory? My lean: advisory — governance should surface health, not block on averages (averages mask individual variation). But the reviewer may argue that a project consistently near the fuse has a structural problem that blocking would force to be addressed. This connects to RISK-039 (architecture health is currently advisory; should loop health mirror it?).

### Q7 — Where does `core/loop-engineering-registry.json` sit relative to `lifecycle-registry.json`?

§9.2 proposes a new `core/loop-engineering-registry.json` for `AgentIntrinsicLoop`/`PausePoint`/`LoopFuse` declarations. **Question:** should these declarations instead be *added to* the existing `lifecycle-registry.json` (which already holds `flow_unit_schema`, `loop_policy`, `allowed_transitions`), to avoid two registries? My lean: extend `lifecycle-registry.json` (single source of truth, matches its `source_of_truth: true` field), with the new declarations as new top-level blocks. The `core/loop-engineering-registry.json` name in §9.2 is a placeholder; reviewer preference sought. (Concern with extending: lifecycle-registry.json is already 2,441 lines; adding to it worsens the God-File problem at the data layer.)

### Q8 — Migration idempotency and re-migration

§7.2's `--apply` has an idempotency guard (fail if target already claims loop-engineering). **Question:** what if a project migrates, runs a few Outer loops, then wants to re-migrate (e.g. after a major restructure that changes flow-unit decomposition)? My design's answer: `--apply` refuses; a separate `--rederive-flow-units` subcommand handles re-decomposition without touching `workflow_model`. Is that the right split, or should `--apply` be re-runnable with a `--force` that re-derives?

### Q9 — Does this design need its own RISK entry (like RISK-040 for the entry-resolver)?

The entry-resolver work (0.64.0) introduced RISK-040 because it touched the entry path with a history of failure (0.54.2/0.54.3). This design touches the primary execution model with a history of conservative dormancy (0.51-0.55 schema-only). **Question:** should this design register a new RISK-041 (loop-engineering activation) with its own closure criteria + external validation gate, mirroring how RISK-040 governed the entry-resolver? My lean: yes — it's the honest move, and it prevents the loop activation from being silently rolled into a RISK-037 closure claim. Reviewer to confirm.

---

## Appendix A — File/Field Reference Index

For the implementer. Every path/field referenced in this ADR, grounded:

| Reference | Location |
|-----------|----------|
| `lifecycle-registry.json` | `skills/software-project-governance/core/lifecycle-registry.json` |
| `registry_mode`, `runtime_activation` | lifecycle-registry.json lines 9-18 |
| `flow_unit_schema.loop_state` | lifecycle-registry.json line 520 (required field), examples lines 749-753 |
| `loop_policy.allowed_loop_types` | lifecycle-registry.json lines 492-498 |
| 3 back-edges | lifecycle-registry.json lines 461-487 |
| `gate_execution_registry` | lifecycle-registry.json lines 1748-2440 |
| `project_type_gate_presets` | lifecycle-registry.json lines 1007-1746 |
| M7.4 §4.6 review-loop fuse | `skills/software-project-governance/references/behavior-protocol.md` lines 493-536 |
| `resolve_entry.py` double-root | `skills/software-project-governance/infra/resolve_entry.py` (360 lines, 0.64.0) |
| `--apply` block | `skills/software-project-governance/infra/verify_workflow.py:20352-20371` |
| `flow-unit-runtime.json` path | verify_workflow.py:1805 `FLOW_UNIT_RUNTIME_STATE_REL` |
| `discover_flow_unit_runtime_context` | verify_workflow.py:3361 |
| `task-gate-model.md` | `skills/software-project-governance/core/task-gate-model.md` |
| `vertical-slice-delivery-packet.md` | `skills/software-project-governance/core/templates/vertical-slice-delivery-packet.md` |
| verify_workflow.py size | 21,651 lines (TD-001, RISK-039) |
| Split roadmap | `docs/requirements/verify-workflow-split-phase1-manifest-domain-0.59.0.md` (+ phase2) |
| RISK-037 closure standard | `.governance/risk-log.md` row 38 |
| RISK-039 (God Module) | `.governance/risk-log.md` row 39 |
| DEC-096 (entry-resolver, 0.64.0) | `docs/requirements/entry-resolver-architecture-0.64.0.md` |
| 0.51.0 design doc | `docs/requirements/dynamic-lifecycle-flow-gate-0.51.0.md` |
| 0.55.0 migration guide | `docs/migration/dynamic-flow-gate-migration-0.55.0.md` |
| 6 review skills | `skills/{requirement,design,tech,code,test,release,retro}-review/` |

## Appendix B — Decision Provenance

- **AUDIT-114** (2026-06-15): dynamic lifecycle research (GitLab, Google, GitHub, Microsoft SDL, Atlassian, DORA) → informed 0.51.0-0.55.0.
- **DEC-083** (2026-06-24): verify_workflow.py split roadmap (0.59-0.64), ArchGuard.
- **DEC-096**: entry-resolver double-root (0.64.0), RISK-040.
- **DEC-097** (this ADR's mandate): loop-first refactor, AI agent loop first-class, design-first.
- **DEC-098** (resolves R0 P0): re-scopes RISK-037 criterion 4 — "compatibility = (a) gate-engine mechanism reuse + (b) G1-G11 as loop vocabulary + (c) classic preserved as rollback target (§7.3), not parallel active classic mode." Resolves the P0 criterion-4 conflict from REVIEW-AUDIT-130-R0.
- **REVIEW-AUDIT-130-R0**: Design Reviewer R0 review — APPROVED_WITH_NOTES. Surfaced 1 P0 (criterion-4, resolved by DEC-098) and 3 P1 findings (resolved in this R0.1 revision).
- **RISK-037** (due 2026-07-30): the 1.0.0 hard blocker this ADR designs against.
- **VAL-005/VAL-006** (0.55.0): external validation proving the schema-only assets work as data but exposing the apply-path and non-game-generalization gaps.

---

## Appendix C — Revision History (P1 Resolution Log, R0.1)

This revision addresses the 3 P1 findings from REVIEW-AUDIT-130-R0. The P0 (criterion-4 conflict) was resolved by DEC-098 (not a design change to this ADR, but recorded in §1.5, §10 criterion 4, and §12 Q3).

**P1-a — §4 G2/G3/G4 on-fail behavior unspecified. RESOLVED.**
- Added a **setup-loop** tier (research → selection → infrastructure, G2/G3/G4) distinct from both initiation (no-loop/no-fuse) and the three main loops (pre-delivery, tighter).
- §3.1: extended the loop diagram and added a Setup row to the loop summary table.
- §3.2: initiation now feeds the setup-loop (G1 = entry gate to setup-loop), not the first Middle loop directly.
- §3.3 (new): defines the setup-loop, its on-fail table for G2/G3/G4, its fuse (MAX_SETUP_ROUNDS=2), evidence type, and preset interaction.
- §3.4–§3.6: renumbered (was §3.3–§3.5); `active_loop_tier` now ranges over `{setup, inner, middle, outer}`.
- §2: added Decision point 2 (setup-loop); renumbered subsequent points (now 1–8).
- §4: rewrote the G2/G3/G4 mapping rows with explicit on-fail semantics and setup-loop tier labels.
- §8.1: added a Setup fuse row (MAX_SETUP_ROUNDS=2); §8.2 notes the setup tier in the stateless-derivation formula.

**P1-b — §6.4 `release-to-design-replan` back-edge trigger too weak. RESOLVED.**
- §6.4: tightened the back-edge to require three conjunctive conditions: (1) G9 fail, (2) G5 (design-review) concurrence that the root cause is design-level — blocking the rubber-stamp by requiring the design-owning gate to concur, (3) PP-Fuse-Escalate human approval. `auto_fire: false` by default; a per-preset opt-in to `auto_fire: true` is deferred to implementation and gated on telemetry.
- §12 Q5: RESOLVED — the back-edge requires a human pause point by default.

**P1-c — §5.2 pause-point velocity justification lacks enforcement. RESOLVED.**
- §5.2: added an Enforcement paragraph referencing the new check.
- §9.5 (new): concrete Check design in `loop_health.py` — Part 1 BLOCKING (any active pause point missing `velocity_cost_justification` fails the check); Part 2 ADVISORY (measured cost > 3× justified bound for 3 consecutive iterations is flagged), with a documented `velocity_check_blocking` upgrade flag.
- §9.2: updated the `check-loop-health` row to reference the velocity-justification sub-check and §3.6 (loop-latency metric section).
- §12 Q2: RESOLVED — blocking for missing justification, advisory-with-upgrade-path for cost-exceedance.

**Internal-consistency notes for R1:**
- `MAX_SETUP_ROUNDS=2` is referenced in §2, §3.1 (table), §3.3, §4 (G2/G3/G4 rows), §8.1 (table), §8.2.
- The setup-loop introduces a new tier in `active_loop_tier` and a new evidence type `LOOP-{U}-setup-R{n}` (§3.3, §8.2). It is fused at 2, below Inner=5 / Middle=3 / Outer=2 — note Outer and Setup share the numeric value 2 but for different reasons (Outer: strategy cost; Setup: pre-delivery misjudgment signal).
- The `release-to-design-replan` back-edge is the only back-edge that requires PP-Fuse-Escalate by default; the other three (test→dev, release→test, ops→retro) remain single-sub-loop hops and fire on gate fail without a mandatory human gate. R1 should confirm this asymmetry is intended (it is: only this edge crosses the entire Middle loop).

---

*End of ADR (R0.1). P0 resolved via DEC-098; 3 P1 findings addressed. Ready for Design Reviewer R1 pressure-testing per §12.*
