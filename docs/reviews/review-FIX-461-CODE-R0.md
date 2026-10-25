# FIX-461 CODE R0 Review — 16 pytest→unittest conversion + FIX-460 stopgap removal

- Task: FIX-461 (test_evidence_migration 16 个 pytest 风格测试转 unittest；CI 覆盖洞收口)
- Reviewer: Code Reviewer (independent CODE R0)
- Date: 2026-10-25
- Scope: `git diff` vs HEAD=d21b0bb, file `skills/software-project-governance/infra/tests/test_evidence_migration.py` (323+/343-)

## 1. Conversion semantic equivalence (all 16 tests reviewed line-for-line)

- Harness: `world` fixture → `_world()` helper + `MigrationTestCase.setUp` (TemporaryDirectory + addCleanup); `monkeypatch.setenv` → `_enable_m2` with prior-value save/restore via addCleanup — env-restore semantics preserved.
- `tmp_path` special cases: CRLF/no-trailing-newline world built under a separate `crlf/` subdirectory of the same tmp — isolation from setUp's standard world preserved (pytest gave each test a fresh tmp_path; the subdirectory restores that isolation for the special-shaped world).
- `monkeypatch.setattr` on the engine primitive → `unittest.mock.patch.object` context managers; all assertions inside the `with` block, so the patch lifetime covers every assertion (equivalent to monkeypatch's test-lifetime undo).
- Assertion strength preserved verbatim: `assert x == y` → `assertEqual`; `assertIn(x, y, msg)` keeps the `inst` diagnostic; fault-injection tests keep structured-refusal codes and hot-file byte-identity checks.
- Groups preserved: V1CanonicalVerdictTests×2, V2ByteExactnessTests×4, ExecuteApplyRecoveryTests×6, CodeR0FaultInjectionTests×2, CapacityLimitTests×2 = 16.

## 2. Stopgap removal completeness

- try/except pytest import, `_PytestImportShim`, `HAS_PYTEST`, `PytestSuiteCoverageMarker`, pytest `__main__` branch — all gone; `__main__` is plain `unittest.main()`.
- Repo-wide `git grep 'import pytest'` over infra/tests → zero hits. Remaining `pytest` mentions in the module are documentary only (docstring ×4, comment ×1) — intentional conversion documentation, not dependencies.

## 3. Independent re-runs (not trusting self-report)

- No-pytest simulation (`sys.modules['pytest']=None` + discover): OK, zero errors — full collection, no skip marker remains.
- pytest engine: `python -m pytest <file> -q` → **16 passed in 1.09s** (unittest classes run under pytest too).
- Full-suite discover (all modules): **exit 0 — zero failures/errors**.
- verify / manifest / xref / write-guard: PASS, PASS, exit 0, 0 issues.

## 4. Notes (non-blocking)

- N1: `mock.patch.object` with-block scope is narrower than monkeypatch's test-lifetime; all converted usages place assertions inside the block, so equivalence holds. Future conversions should keep this discipline.
- N2: inline `import archive_migration_engine as eng` inside two tests preserved from the originals (function-local import kept as-is) — faithful, though a module-level import would be cleaner in a future pass.
- N3: docstring "Run:" guidance updated to the unittest invocation — accurate.

FIX-461: APPROVED_WITH_NOTES (unresolved_blockers=0)
