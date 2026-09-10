"""Contract matrix package (FEAT-020 — AUDIT-150 REFACTOR-contract-matrix-freeze).

Freezes the three public contract faces of the governance engine plus the
governance-write-guard output pin (FEAT-017 R0 F-2 收编):

  1. CLI dispatch key set       — verify_workflow.py ``main()`` commands dict
  2. Check ID segment list      — banner ids ∪ product-gate registry ids
  3. Result dict shapes         — representative check-function key/type
                                  signatures (actually invoked, never copied)
  4. guard output contract pin  — governance-write-guard Result-line format +
                                  issue-line prefix (hook-panel consumption)

``generator`` holds the programmatic extractor, the explicit ``--regen``
mechanism and the ``--check`` differential harness. ``snapshots.json`` is the
frozen baseline; any contract-face change MUST regenerate it deliberately and
explain the drift (protection-net semantics, not auto-updating).
"""
