# FIX-464 CODE R0 Review — pins writer amnesty-exit sync

- Task: FIX-464 (pins register/re-anchor 不同步 DELIVERY_AMNESTY_ENTRIES——违反写器自述语义 rows-leave-on-touch；FIX-462 域缺陷)
- Reviewer: Code Reviewer (independent CODE R0)
- Date: 2026-10-25
- Scope: `git diff` vs HEAD=d21b0bb — pin_ledger.py (140+/4-), tests/test_static_version_pins.py (220+/3-), checks/version.py (4+/2- machine-written product)

## 1. Sync implementation correctness

- `_sync_amnesty_exit`: exact-tuple regex locate → provenance-shaped comment replace → `compile()` gate → temp-file shadow import → **three post-checks**: (a) touched row absent from candidate amnesty; (b) zero ghost rows (amnesty ⊆ live ledger); (c) every live row outside amnesty carries a pins provenance comment — exactly the face-6/snapshot invariant. `os.replace` atomic swap only after all three pass.
- Same-transaction semantics: `register`/`re-anchor` call the sync after the ledger swap; on sync refusal the caller **restores the ledger bytes** while the amnesty temp was never swapped → dual-file consistency holds (ledger restored + amnesty untouched).
- Sabotage test proves it: corrupted-amnesty injection → exit 2, ledger byte-identical to before, and no FIX-464 fixture-targeted exit comment ever lands in the module — fail-closed confirmed.
- `noop_self_absent` for mini-roots without a pin_ledger copy — harness-safe.

## 2. Self-heal channel (noop branch)

- Re-introduced ghost + re-run of the same re-anchor → `effect=idempotent_noop`, `amnesty_sync=written`, **ledger bytes unchanged** — precisely repairs the FIX-462 gap with zero ledger churn. Idempotent: a second noop finds no amnesty row → `noop_not_in_amnesty`, no further writes.

## 3. Bilateral invariant vs literal equality (test redesign) — verified STRONGER

- The FIX-462 form (`amnesty == live`) was a latent contradiction: the first legitimate machine write adds a live row **outside** amnesty by design, so equality could only hold while the writer had never really written. The redesign asserts (no ghosts) ∧ (no unattributed live rows) — it catches both writer-gap ghosts AND hand edits; drift-detection intent preserved and strengthened on both sides. Sound argument, verified against the live tree.

## 4. Real-tree repair chain

- version.py: two machine-written re-anchors with provenance comments + op-ids (test_evidence_migration 80→51; test_static_version_pins 166→167). pin_ledger.py: two ghost rows left DELIVERY_AMNESTY_ENTRIES with FIX-464 provenance comments and the same op-ids — the 80-ghost that failed the snapshot contract is resolved, chain fully traceable.

## 5. Independent re-runs

- Pin suite: **36/36 OK** (32 prior + 4 new PinsWriterAmnestySyncTests: re-anchor exit / sync-failure dual restore / register exit / noop self-heal).
- verify / manifest / xref / write-guard: PASS / PASS / exit 0 / **0 issues** (write-guard pin-ledger face: PASS 0 issues on final tree).
- Full-suite discover: **exit 0 — zero failures** (the amnesty snapshot test that was the sole pre-fix failure is green in the run).

## 6. Notes (non-blocking)

- N1: the dispatch mentioned a write-guard WARN (pins op-id not recognized as machine credential); my guard run on the final tree shows **0 issues** — either it referred to an intermediate state or was transient; not reproduced on the review tree.
- N2: the noop self-heal requires the ghost's original from-line to be re-supplied by the operator; ghosts at unknown lines are caught by the invariant test (red) rather than auto-repaired — acceptable, primary paths now prevent ghost creation entirely.
- N3: `_sync_amnesty_exit` rewrites pin_ledger.py itself (self-modification discipline) — guarded by compile+shadow+three post-checks; provenance comments accumulate in the frozenset block; a future 0.100 candidate could compact them at version bumps.

FIX-464: APPROVED_WITH_NOTES (unresolved_blockers=0)
