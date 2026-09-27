"""FIX-398 — migration commit-window robustness tests (RISK-060 vehicle).

Replay discipline (execution-packet FIX-398 / RISK-060 closure standard):

  - **SIGKILL is simulated by subprocess termination** — a child process runs
    the real apply and calls ``os._exit(137)`` at an injected window point.
    No real kernel signals are used, and the child dies without running any
    cleanup handler (finally/atexit), which is the SIGKILL-class semantics
    the compensating transaction must survive.
  - **Window-point coverage table** (each replayed point asserts zero partial
    state after re-entry — self-healed, cleaned, or a complete state):

    | point id | window                                    | FEAT-068 场景⑥ anchor      | re-entry semantics                    |
    |----------|-------------------------------------------|----------------------------|---------------------------------------|
    | wp-backup| backup created, transaction not started   | 60~180ms 段后延（读/派生段）| E-5 sweep removes the orphan; fresh apply |
    | wp-runtime| runtime replace landed, evidence not      | **240ms wc6d 实证点**       | E-4 self-heal + fresh apply (RISK-060 core) |
    | wp-evidence| both replaces landed, validation not run | 265ms wc6e                 | complete state → idempotency refusal (correct) |
    | (arm) ambiguous | wp-runtime + post-kill evidence evolution | —                    | fail-closed guidance, runtime untouched   |

  - **Isolation**: every host lives in ``tempfile.TemporaryDirectory`` — the
    real ``.governance/`` is NEVER touched; no ``$HOME`` assignment anywhere.
  - **Assertions are content-based only** (file bytes, row counts, result
    fields). No wall-clock timing is asserted; the subprocess timeout is a
    safety cap, not a judge. MIGRATION_VERSION is never modified (DEC-257).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_migration_commit_window.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_migration as lm  # noqa: E402
import verify_workflow as vw  # noqa: E402
import checks.evidence_domain as ed  # noqa: E402
from loop_migration_plan import (  # noqa: E402
    build_migration_plan,
    confirm_decomposition,
)

VERSION = lm.MIGRATION_VERSION  # 0.65.0 — read, never written (DEC-257)

# ─── Fixtures (self-contained; mirrors test_loop_migration's minimal host) ───

CLASSIC_PLAN_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

CLASSIC_EVIDENCE_LOG = (
    "| 编号 | 事项 | 说明 |\n"
    "| --- | --- | --- |\n"
    "| EVD-001 | init | seeded evidence log |\n"
)


def _write_host(root, runtime=None):
    """Seed a minimal classic .governance/ (plan + evidence [+ runtime])."""
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(CLASSIC_PLAN_TRACKER, encoding="utf-8")
    (gov / "evidence-log.md").write_text(CLASSIC_EVIDENCE_LOG, encoding="utf-8")
    if runtime is not None:
        (gov / "flow-unit-runtime.json").write_text(runtime, encoding="utf-8")
    return gov


def _sha256_of(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migration_row_count(evidence_path):
    text = evidence_path.read_text(encoding="utf-8")
    return sum(
        1 for line in text.splitlines()
        if lm._evidence_has_migration_row(line, VERSION)
    )


def _backup_names(root):
    return [entry.name for entry, _v, _ts in lm._list_migration_backups(root)]


# ─── The fault-injection driver (runs as a CHILD process) ────────────────────
#
# The child monkeypatches the module-global ``_atomic_replace_bytes`` /
# ``_backup_governance_files`` (both are resolved through module globals at
# their call sites, so patching is exact) and hard-exits at the requested
# window point — no exception path, no cleanup handler: SIGKILL-class death
# simulated without any kernel signal dependency.

_FAULT_DRIVER_SOURCE = r'''
import json
import os
import sys

infra_dir, point, target = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, infra_dir)
import loop_migration as lm

try:  # the result JSON is ASCII-safe, but keep the CLI's own guard
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

real_replace = lm._atomic_replace_bytes
calls = {"count": 0}


def inject(path, content):
    calls["count"] += 1
    real_replace(path, content)
    if point == "after_runtime_replace" and calls["count"] == 1:
        os._exit(137)  # runtime landed, evidence replace not reached (wc6d)
    if point == "after_evidence_replace" and calls["count"] == 2:
        os._exit(137)  # both replaces landed, post-write validation not run


lm._atomic_replace_bytes = inject

if point == "after_backup":
    real_backup = lm._backup_governance_files

    def backup_inject(*args, **kwargs):
        real_backup(*args, **kwargs)
        os._exit(137)  # backup dir created, transaction not started

    lm._backup_governance_files = backup_inject

result = lm.apply_migration(target_root=target)
print(json.dumps(result, ensure_ascii=False))
'''


def _run_apply_with_fault(root, point):
    """Run one real apply in a child process, killed at ``point``."""
    driver_path = root / "_fault_driver.py"
    driver_path.write_text(_FAULT_DRIVER_SOURCE, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(driver_path), str(_INFRA_DIR), point, str(root)],
        capture_output=True, text=True, timeout=180,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Commit-window replay tests (subprocess termination = simulated SIGKILL)
# ═══════════════════════════════════════════════════════════════════════════


class TestCommitWindowReplay(unittest.TestCase):
    """≥3 window points (incl. the wc6d empirical point), per RISK-060."""

    def test_replay_wp_backup_zero_partial_state_orphan_swept(self):
        """wp-backup: kill after backup creation, before the transaction.

        Nothing live was written (zero partial state by construction); the
        killed attempt leaves ONE orphan backup dir, and re-entry must sweep
        it (E-5) before creating its own — the archive never accumulates.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            plan_before = _sha256_of(gov / "plan-tracker.md")

            killed = _run_apply_with_fault(root, "after_backup")
            self.assertEqual(killed.returncode, 137,
                             f"child did not die at the window: {killed.stderr}")
            self.assertFalse((gov / "flow-unit-runtime.json").exists())
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 0)
            orphans = _backup_names(root)
            self.assertEqual(len(orphans), 1, "killed apply leaves one backup dir")

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"], f"re-apply failed: {result}")
            # E-5: the orphan was swept and disclosed in the result.
            self.assertEqual(result["orphan_backup_sweep"]["cleaned"], orphans)
            self.assertEqual(_backup_names(root),
                             [Path(result["backup_dir"]).name],
                             "archive must hold exactly the fresh backup")
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 1)
            self.assertTrue((gov / "flow-unit-runtime.json").is_file())
            self.assertEqual(_sha256_of(gov / "plan-tracker.md"), plan_before,
                             "apply never writes the plan-tracker")

    def test_replay_wc6d_runtime_landed_self_heals(self):
        """wp-runtime — the wc6d 240ms empirical point (RISK-060 core).

        Kill between the runtime replace and the evidence replace reproduces
        the exact partial state FEAT-068 scenario ⑥ proved (runtime landed,
        MIGRATION row missing, re-apply used to refuse without compensating).
        Re-entry must now SELF-HEAL: verify the live evidence against the
        transaction's pre-state snapshot, remove the half-committed runtime
        and the interrupted attempt's orphan backup, then complete a fresh,
        fully validated apply — zero partial state, no manual rollback.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            plan_before = _sha256_of(gov / "plan-tracker.md")
            evidence_before = (gov / "evidence-log.md").read_bytes()

            killed = _run_apply_with_fault(root, "after_runtime_replace")
            self.assertEqual(killed.returncode, 137,
                             f"child did not die at the window: {killed.stderr}")

            # The wc6d partial state, reproduced and asserted:
            runtime_path = gov / "flow-unit-runtime.json"
            self.assertTrue(runtime_path.is_file(), "runtime landed pre-kill")
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertEqual(runtime["migration_version"], VERSION)
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 0,
                             "evidence MIGRATION row never landed (the window)")
            interrupted_backup = _backup_names(root)
            self.assertEqual(len(interrupted_backup), 1)
            # The commit-window snapshots exist (heal's verification anchor):
            self.assertTrue(
                (root / ".governance" / "archive" / interrupted_backup[0]
                 / "evidence.before").is_file())

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"],
                            f"self-heal re-entry failed: {result}")
            heal = result["healed_interrupted_commit"]
            self.assertTrue(heal["detected"])
            self.assertTrue(heal["healed"])
            self.assertTrue(heal["runtime_removed"])
            self.assertTrue(heal["evidence_matches_pre_state"])
            self.assertEqual(heal["backup_dir_removed"], interrupted_backup[0],
                             "the interrupted attempt's orphan backup is removed")

            # Zero partial state after re-entry:
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 1,
                             "exactly one MIGRATION row for this version")
            self.assertIn("EVD-001",
                          (gov / "evidence-log.md").read_text(encoding="utf-8"),
                          "pre-migration evidence rows are preserved")
            self.assertEqual(
                (gov / "evidence-log.md").read_bytes(),
                evidence_before.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
                + ("| MIGRATION-{0} | FX-191 | migrated classic-phase-gate -> "
                   "loop-engineering | backup={1} |\n".format(
                       VERSION, Path(result["backup_dir"]).name)).encode("utf-8"),
                "evidence = pristine pre-state (newline-normalized by the "
                "bytes-writer, same as any normal apply) + exactly the new "
                "MIGRATION row")
            self.assertEqual(_sha256_of(gov / "plan-tracker.md"), plan_before)
            final_runtime = json.loads(
                runtime_path.read_text(encoding="utf-8"))
            self.assertEqual(final_runtime["workflow_model"], "loop-engineering")
            self.assertEqual(_backup_names(root),
                             [Path(result["backup_dir"]).name],
                             "archive holds exactly the completed apply's backup")
            leftovers = list(gov.glob("*.tmp"))
            self.assertEqual(leftovers, [],
                             "no scoped .tmp leftovers may survive the heal")

    def test_replay_wp_evidence_landed_complete_state_refuses(self):
        """wp-evidence (≈ wc6e): both replaces landed, validation did not run.

        The on-disk state IS the complete intended apply. Re-entry must
        refuse via the idempotency guard — that is a correct, non-partial
        terminal state, not a deadlock.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)

            killed = _run_apply_with_fault(root, "after_evidence_replace")
            self.assertEqual(killed.returncode, 137,
                             f"child did not die at the window: {killed.stderr}")
            self.assertTrue((gov / "flow-unit-runtime.json").is_file())
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 1)

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"])
            self.assertIn("idempotency", result["aborted_reason"].lower())
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 1,
                             "no duplicate MIGRATION row")
            self.assertEqual(len(_backup_names(root)), 1)

    def test_replay_ambiguous_evidence_fails_closed_with_guidance(self):
        """Ambiguous arm: wc6d kill + post-kill legal evidence evolution.

        When the live evidence-log differs from the transaction's pre-state
        snapshot, the state is ambiguous (post-interruption writes vs an
        out-of-chain edit) — auto-heal MUST refuse (P7) with explicit
        interrupted-state guidance naming the rollback path, and the runtime
        must be left untouched.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)

            killed = _run_apply_with_fault(root, "after_runtime_replace")
            self.assertEqual(killed.returncode, 137)
            # Post-kill evolution: a legal EVD row lands after the kill.
            evidence_path = gov / "evidence-log.md"
            evidence_path.write_text(
                evidence_path.read_text(encoding="utf-8")
                + "| EVD-002 | post-kill | legal evidence write after kill |\n",
                encoding="utf-8")

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"],
                             f"ambiguous state must not auto-heal: {result}")
            self.assertIn("interrupted migration commit detected",
                          result["aborted_reason"])
            self.assertIn("--rollback", result["aborted_reason"])
            interrupted = result["interrupted_commit"]
            self.assertTrue(interrupted["detected"])
            self.assertFalse(interrupted["healed"])
            self.assertFalse(interrupted["evidence_matches_pre_state"])
            # P7: the half-committed runtime is NOT silently deleted.
            self.assertTrue((gov / "flow-unit-runtime.json").is_file())
            self.assertEqual(_migration_row_count(evidence_path), 0)
            self.assertEqual(len(_backup_names(root)), 1,
                             "fail-closed arm writes nothing and removes nothing")


# ═══════════════════════════════════════════════════════════════════════════
# Orphan backup hygiene (E-5) — unit arms of the safety verification
# ═══════════════════════════════════════════════════════════════════════════


class TestOrphanBackupSweep(unittest.TestCase):

    def test_unreferenced_verified_backup_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            backup_dir, _hashes = lm._backup_governance_files(root, VERSION)
            self.assertTrue(backup_dir.is_dir())

            result = lm._sweep_orphan_migration_backups(
                root, CLASSIC_EVIDENCE_LOG)

            self.assertEqual(result["cleaned"], [backup_dir.name])
            self.assertFalse(backup_dir.exists())

    def test_migration_row_referenced_backup_kept(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            result = lm.apply_migration(target_root=str(root))
            self.assertTrue(result["applied"])
            backup_name = Path(result["backup_dir"]).name
            evidence = (gov / "evidence-log.md").read_text(encoding="utf-8")

            sweep = lm._sweep_orphan_migration_backups(root, evidence)

            self.assertEqual(sweep["cleaned"], [])
            # P7 guard: with a live runtime present the whole sweep is
            # skipped and the skip is disclosed, not silently empty.
            self.assertEqual(len(sweep["skipped"]), 1)
            self.assertEqual(sweep["skipped"][0]["name"], "*")
            self.assertIn(backup_name, _backup_names(root))

    def test_rollback_restored_from_referenced_backup_kept(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            applied = lm.apply_migration(target_root=str(root))
            self.assertTrue(applied["applied"])
            rolled = lm.rollback_migration(target_root=str(root))
            self.assertTrue(rolled["rolled_back"])
            backup_name = Path(rolled["restored_from"]).name
            evidence = (gov / "evidence-log.md").read_text(encoding="utf-8")

            sweep = lm._sweep_orphan_migration_backups(root, evidence)

            self.assertEqual(sweep["cleaned"], [],
                             "a ROLLBACK restored_from reference protects its "
                             "backup from the sweep")
            self.assertIn(backup_name, _backup_names(root))

    def test_tampered_orphan_skipped_not_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            backup_dir, _hashes = lm._backup_governance_files(root, VERSION)
            (backup_dir / "plan-tracker.md").write_text("TAMPERED",
                                                        encoding="utf-8")

            result = lm._sweep_orphan_migration_backups(
                root, CLASSIC_EVIDENCE_LOG)

            self.assertEqual(result["cleaned"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertIn("plan-tracker", result["skipped"][0]["reason"])
            self.assertTrue(backup_dir.exists(),
                           "unverifiable dirs are disclosed, never deleted")

    def test_foreign_version_backup_kept(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            foreign = (gov / "archive" / "migration-9.9.9-20260101T000000Z")
            foreign.mkdir(parents=True)
            (foreign / "manifest.json").write_text(
                json.dumps({"migration_version": "9.9.9"}), encoding="utf-8")

            result = lm._sweep_orphan_migration_backups(
                root, CLASSIC_EVIDENCE_LOG)

            self.assertEqual(result["cleaned"], [])
            self.assertEqual(result["skipped"][0]["reason"],
                             "foreign migration version — untouched")
            self.assertTrue(foreign.exists())

    def test_sweep_without_archive_is_noop_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            result = lm._sweep_orphan_migration_backups(
                root, CLASSIC_EVIDENCE_LOG)

            self.assertEqual(result, {"cleaned": [], "skipped": []})
            self.assertFalse((root / ".governance" / "archive").exists(),
                             "the sweep must never create the archive dir")

    def test_sweep_skipped_entirely_when_live_runtime_present(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root, runtime='{"legacy": true}')
            backup_dir, _hashes = lm._backup_governance_files(root, VERSION)

            result = lm._sweep_orphan_migration_backups(
                root, CLASSIC_EVIDENCE_LOG)

            self.assertEqual(result["cleaned"], [])
            self.assertEqual(result["skipped"][0]["name"], "*")
            self.assertTrue(backup_dir.exists())


# ═══════════════════════════════════════════════════════════════════════════
# Heal fail-closed arms (no commit-window backup available)
# ═══════════════════════════════════════════════════════════════════════════


class TestHealFailClosedArms(unittest.TestCase):

    def test_interrupted_state_without_snapshot_backup_refuses(self):
        """runtime@version + no row + no evidence.before anywhere → guidance.

        The wc6d window guarantees the snapshot backup exists, so its absence
        means the state was produced some other way — fail-closed with the
        rollback guidance, runtime untouched, zero writes.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root, runtime=json.dumps(
                {"schema_version": "2.0", "migration_version": VERSION,
                 "workflow_model": "loop-engineering"}))

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"])
            self.assertIn("interrupted migration commit detected",
                          result["aborted_reason"])
            self.assertIn("--rollback", result["aborted_reason"])
            self.assertTrue((gov / "flow-unit-runtime.json").is_file())
            self.assertEqual(_migration_row_count(gov / "evidence-log.md"), 0)
            self.assertFalse((gov / "archive").exists())

    def test_unparseable_runtime_is_not_healed(self):
        """A corrupt runtime is NOT an interrupted-commit artifact — the
        heal must not touch it (existing apply-overwrite semantics govern).
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, runtime="{ this is not valid json,,,")

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"], f"apply failed: {result}")
            self.assertNotIn("healed_interrupted_commit", result)


# ═══════════════════════════════════════════════════════════════════════════
# F-6/F-8 — plan re-derivation failure is its own WARN type (C-10 Face 4)
# ═══════════════════════════════════════════════════════════════════════════
# Placement note: the natural home (test_evidence_binding_drift.py) is outside
# this task's locked write face; FIX-398 subitem ④ coverage lives here, in the
# batch's robustness test file, until that file's next sanctioned edit.


def _build_real_migration(gov):
    """Run a REAL apply on the fixture host (valid v2 runtime + MIGRATION row)."""
    result = lm.apply_migration(target_root=str(gov.parent))
    assert result["applied"], f"fixture apply failed: {result}"
    return result


class TestF6PlanRederiveFailedWarn(unittest.TestCase):

    def test_plan_read_failure_reports_dedicated_type_not_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            _build_real_migration(gov)
            # Plan face becomes unreadable (invalid UTF-8) after the migration.
            (gov / "plan-tracker.md").write_bytes(b"\xff\xfe-not-valid-utf8-\xff")
            patches = [mock.patch.object(vw, "GOVERNANCE_DIR", gov)]
            try:
                for p in patches:
                    p.start()
                block = ed.check_evidence_binding_drift()
            finally:
                for p in reversed(patches):
                    p.stop()
            warn_types = [issue["type"] for issue in block["warn"]]
            self.assertIn("plan_rederive_failed", warn_types)
            self.assertNotIn(
                "unit_set_drift", warn_types,
                "FIX-398 F-6: a read failure is NOT unit_set_drift — the "
                "types must be distinguishable by consumers")
            self.assertTrue(block["pass"])
            rederive = [issue for issue in block["warn"]
                        if issue["type"] == "plan_rederive_failed"][0]
            self.assertIn("计划面重派生失败", rederive["detail"])
            self.assertIn("UnicodeDecodeError", rederive["detail"],
                          "the exception class is surfaced in the detail")

    def test_derive_crash_is_surfaced_not_escaped(self):
        """FIX-398 F-8: a non-(OSError/UnicodeDecodeError/ValueError) crash
        inside the Face 4 re-derivation is reported as
        plan_rederive_failed instead of escaping the check.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            _build_real_migration(gov)
            patches = [
                mock.patch.object(vw, "GOVERNANCE_DIR", gov),
                mock.patch("loop_migration_plan.build_migration_plan",
                           side_effect=RuntimeError("boom")),
            ]
            try:
                for p in patches:
                    p.start()
                block = ed.check_evidence_binding_drift()
            finally:
                for p in reversed(patches):
                    p.stop()
            self.assertTrue(block["pass"])
            rederive = [issue for issue in block["warn"]
                        if issue["type"] == "plan_rederive_failed"]
            self.assertEqual(len(rederive), 1)
            self.assertIn("RuntimeError", rederive[0]["detail"])
            self.assertIn("boom", rederive[0]["detail"])

    def test_real_drift_still_reports_unit_set_drift(self):
        """Contrast arm: genuine unit-set divergence keeps unit_set_drift —
        proving the new type splits semantics rather than renaming them.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = _write_host(root)
            _build_real_migration(gov)
            runtime_path = gov / "flow-unit-runtime.json"
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            runtime["flow_units"][0]["flow_unit_id"] = "renamed-away-unit"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            patches = [mock.patch.object(vw, "GOVERNANCE_DIR", gov)]
            try:
                for p in patches:
                    p.start()
                block = ed.check_evidence_binding_drift()
            finally:
                for p in reversed(patches):
                    p.stop()
            warn_types = [issue["type"] for issue in block["warn"]]
            self.assertIn("unit_set_drift", warn_types)
            self.assertNotIn("plan_rederive_failed", warn_types)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
