# Loop Role Mapping — Review Skills (0.65.0)

This document is the **single source of truth** for how each review skill's gate is re-labeled under the loop-engineering architecture. It carries DEC-097 part 1 ("the loop is the ONLY model") into the skill layer: a review skill's gate is no longer a "stage inspection" — it is a **loop-exit / loop-entry certification**.

Per ADR §3.5 (loop-engineering-architecture-0.65.0). See `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` §3.5 and §4 for the authoritative stage-by-stage mapping.

## Why this exists

In 0.51.0-0.55.0 the seven review skills described their gate as "inspect stage X." Under 0.65.0 that semantic is retired. Each review skill now certifies a specific loop's exit or entry. A gate that FAILS does not fail a stage — it **returns the work into its enclosing loop for another iteration**, increments the loop's `loop_count`, and the agent loop re-Plans against the findings. Only when `loop_count` exceeds the fuse (MAX_ROUNDS) does the failed gate escalate instead of iterating.

## Vocabulary (ADR §4)

"Role" uses exactly four values:

- **loop-setup** — one-time / non-iterative prep (initiation is the sole non-loop).
- **loop-body** — the work that iterates.
- **loop-exit-gate** — certifies a loop's exit condition.
- **loop-entry-gate** — certifies entry into the next loop.

## The 7 review skills → loop role (ADR §3.5)

| Skill | Old semantic ("inspect stage") | New loop role | Loop it certifies | What "certifying this gate" means |
|-------|-------------------------------|---------------|-------------------|------------------------------------|
| `requirement-review` | inspect 立项 artifacts | `loop-setup` (+ loop-entry-gate for first Middle) | (non-loop: initiation) | Certify initiation setup is complete. This is the loop-entry gate for the setup-loop, which precedes the first Middle loop. NOT iterative. |
| `design-review` | inspect architecture stage | `loop-entry-gate` | Middle (entry) | Certify a Middle loop's ENTRY — design converges, can begin building this flow unit. On failure the design sub-loop iterates (re-design); it does not fail the project. |
| `tech-review` | inspect technical selection / design quality | `loop-entry-gate` | Middle (entry, technical depth) | Certify a Middle loop's design sub-iteration converged — risk-driven depth verified (PoC, alternatives, blue-army challenge). |
| `code-review` | inspect development stage | `loop-exit-gate` | Inner (exit) | Certify an Inner loop's EXIT — the slice/commit is mergeable. On failure the Inner loop iterates (rework → re-review). Fuse: Inner max_rounds=5. |
| `test-review` | inspect testing stage | `loop-body` + `loop-exit-gate` | Middle (body, quality) | Certify a Middle loop's quality sub-iteration converged — defects closed, regression pass. On failure → `testing-to-development-rework` back-edge returns work to the Inner loop. |
| `release-review` | inspect release stage | `loop-exit-gate` (Middle) / `loop-entry-gate` (Outer) | Middle (exit) / Outer (entry) | Certify a Middle loop's EXIT — flow unit releasable — AND entry to the Outer loop's operate-measure phase. On failure → `release-to-testing-rework` back-edge returns to the testing sub-loop. |
| `retro-review` | inspect maintenance stage | `loop-exit-gate` | Outer (exit) | Certify an Outer loop's iteration CONVERGED — learnings backfilled, next round direction set. On failure → `operations-feedback-to-maintenance-loop` back-edge keeps the Outer loop iterating. |

## The load-bearing rule

> A gate that FAILS does not fail a stage. It **returns the work into its enclosing loop for another iteration**, increments the loop's `loop_count`, and the agent loop re-Plans against the findings. Only when `loop_count` exceeds the fuse (§8) does the failed gate escalate instead of iterating.

This is why "a gate without a loop on each side is a wall": in the old linear model a failed G6 left the project stuck between "development" and "testing" with no defined next action. In the loop model, a failed code-review gate means the Inner loop iterates (agent Reflects on findings, re-Plans, re-Acts) until LGTM or fuse.

## Related

- ADR §3.5 — Gate-as-loop-exit semantics (`docs/requirements/loop-engineering-architecture-0.65.0-proposed.md`).
- ADR §4 — full G1-G11 stage → loop-role mapping table.
- ADR §3.3 — the setup-loop (research / selection / infrastructure) and `MAX_SETUP_ROUNDS=2`.
- ADR §8 — the loop fuses (MAX_ROUNDS per loop tier).
