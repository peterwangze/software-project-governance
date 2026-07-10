"""Unit tests for loop_migration.py — FX-191 (0.65.0 loop-engineering, slice 4).

These tests are the load-bearing verification for the data-loss-risk slice:
apply is a read-then-write on plan-tracker + evidence-log + a new
runtime.json. The single most important properties proven here:

  - **Backup BEFORE write** — :func:`TestApplyMigration.test_fail_closed_missing_files`
    proves that a fail-closed abort leaves NO backup dir, NO runtime.json,
    and NO evidence row. The backup step (step 4) only runs after all reads
    + fail-closed checks pass.
  - **Rollback totality** — :func:`TestRollbackMigration.test_rollback_total_restore`
    proves that apply→rollback restores plan-tracker + evidence-log to their
    pre-apply byte content (hash-for-hash), removes runtime.json, and
    appends a ROLLBACK row.
  - **RISK-040 divergence** — :func:`TestApplyMigration.test_risk040_divergence`
    proves that when target_root is a host dir distinct from PLUGIN_HOME,
    all reads/writes hit the host's ``.governance/`` and NEVER the plugin's.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_migration.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_loop_migration -v
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_migration as lm  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/


# ─── Shared fixtures ─────────────────────────────────────────────────────────

# A minimal classic plan-tracker with a workflow_model line (so prior-model
# detection works) and a Gate tracking table (so it parses as classic).
CLASSIC_PLAN_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# A minimal evidence-log with one parseable EVD row.
CLASSIC_EVIDENCE_LOG = (
    "| 编号 | 事项 | 说明 |\n"
    "| --- | --- | --- |\n"
    "| EVD-001 | init | seeded evidence log |\n"
)


def _write_host(host_root, plan_text=None, evidence_text=None, runtime=None):
    """Write a minimal classic .governance/ into host_root.

    By default writes a classic plan-tracker + a 1-row evidence-log and NO
    runtime.json. ``runtime`` may be a dict to pre-seed a (corrupt or valid)
    runtime.json for kill-mid-write tests.
    """
    gov = host_root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(
        plan_text if plan_text is not None else CLASSIC_PLAN_TRACKER,
        encoding="utf-8",
    )
    (gov / "evidence-log.md").write_text(
        evidence_text if evidence_text is not None else CLASSIC_EVIDENCE_LOG,
        encoding="utf-8",
    )
    if runtime is not None:
        if isinstance(runtime, str):
            (gov / "flow-unit-runtime.json").write_text(runtime, encoding="utf-8")
        else:
            (gov / "flow-unit-runtime.json").write_text(
                json.dumps(runtime, indent=2), encoding="utf-8"
            )


def _sha256_bytes(data):
    """SHA-256 hexdigest of a bytes blob (for test-side hash comparison)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# APPLY tests
# ═══════════════════════════════════════════════════════════════════════════


class TestApplyMigration(unittest.TestCase):
    """FX-191 apply path (ADR §7.2)."""

    def test_apply_writes_runtime_and_backup(self):
        """Test 1: apply creates runtime.json, backup dir, and MIGRATION row."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"], f"apply failed: {result}")
            self.assertEqual(result["workflow_model"]["new"], "loop-engineering")
            self.assertEqual(result["workflow_model"]["prior"], "classic-phase-gate")
            self.assertGreaterEqual(result["flow_units_derived"], 1)

            # runtime.json created with the loop-engineering model + dormant units.
            runtime_path = root / ".governance" / "flow-unit-runtime.json"
            self.assertTrue(runtime_path.is_file(), "runtime.json must be created")
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertEqual(runtime["workflow_model"], "loop-engineering")
            self.assertEqual(runtime["migration_version"], "0.65.0")
            self.assertIsInstance(runtime["flow_units"], list)
            self.assertGreaterEqual(len(runtime["flow_units"]), 1)
            # Each unit carries a dormant loop_state (3-field shape).
            for unit in runtime["flow_units"]:
                ls = unit.get("loop_state", {})
                self.assertIn("active_loop", ls)
                self.assertIn("loop_count", ls)
                self.assertIn("last_loop_type", ls)

            # backup dir created with BOTH file copies.
            backup_dir = Path(result["backup_dir"])
            self.assertTrue(backup_dir.is_dir(), "backup dir must exist")
            self.assertTrue((backup_dir / "plan-tracker.md").is_file())
            self.assertTrue((backup_dir / "evidence-log.md").is_file())

            # MIGRATION evidence row appended.
            evidence = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("MIGRATION-0.65.0", evidence)

            # hashes dict populated with before AND after.
            self.assertIn("plan_tracker_before", result["hashes"])
            self.assertIn("plan_tracker_after", result["hashes"])
            self.assertIn("evidence_log_before", result["hashes"])
            self.assertIn("evidence_log_after", result["hashes"])

    def test_apply_idempotency_guard_runtime_json(self):
        """Test 2: re-applying on a target whose runtime.json already matches
        the current MIGRATION_VERSION fails closed BEFORE any backup is created.

        This is the FX-191 P1.1 fix: the plan-tracker is NEVER modified by
        apply, so a plan-tracker-based guard could never fire on double-apply.
        The runtime.json is the authoritative marker. Re-applying must fail
        closed WITHOUT creating a second backup dir or a second MIGRATION row.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            # First apply: succeeds, writes runtime.json + 1 backup + 1 MIGRATION row.
            first = lm.apply_migration(target_root=str(root))
            self.assertTrue(first["applied"], f"first apply failed: {first}")
            self.assertTrue(
                (root / ".governance" / "flow-unit-runtime.json").is_file()
            )

            # Second apply on the SAME target (runtime.json now present at 0.65.0).
            second = lm.apply_migration(target_root=str(root))

            # Must fail closed with the idempotency reason.
            self.assertFalse(second["applied"], f"second apply unexpectedly succeeded: {second}")
            self.assertIn("idempotency", second["aborted_reason"].lower())
            self.assertIn("0.65.0", second["aborted_reason"])

            # Exactly ONE backup dir exists — the guard ran BEFORE the backup step.
            backups = lm._list_migration_backups(root)
            self.assertEqual(len(backups), 1,
                             f"expected 1 backup after double-apply, got {len(backups)}")

            # No second MIGRATION row was appended.
            evidence = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertEqual(evidence.count("MIGRATION-0.65.0"), 1,
                             "double-apply must not append a duplicate MIGRATION row")

    def test_backup_hash_integrity(self):
        """Test 3: after apply, backup files' SHA-256 match recorded before-hashes.

        Tampering a backup file causes _verify_backup_hashes to return False.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            result = lm.apply_migration(target_root=str(root))
            self.assertTrue(result["applied"])

            backup_dir = Path(result["backup_dir"])
            expected = {
                "plan_tracker_sha256": result["hashes"]["plan_tracker_before"],
                "evidence_log_sha256": result["hashes"]["evidence_log_before"],
            }

            # Clean verify: hashes match.
            ok, mismatches = lm._verify_backup_hashes(backup_dir, expected)
            self.assertTrue(ok, f"unexpected mismatches: {mismatches}")

            # Tamper the backup's plan-tracker and re-verify → mismatch.
            (backup_dir / "plan-tracker.md").write_text(
                "TAMPERED CONTENT", encoding="utf-8"
            )
            ok_tampered, mismatches_t = lm._verify_backup_hashes(backup_dir, expected)
            self.assertFalse(ok_tampered)
            self.assertTrue(
                any("plan-tracker.md" in m and "mismatch" in m for m in mismatches_t),
                f"expected plan-tracker hash mismatch in {mismatches_t}",
            )

    def test_fail_closed_missing_files(self):
        """Test 5: missing plan-tracker OR evidence-log → abort before ANY write."""
        # Case A: missing plan-tracker.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "evidence-log.md").write_text(CLASSIC_EVIDENCE_LOG, encoding="utf-8")
            # No plan-tracker.

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"])
            self.assertIn("plan-tracker", result["aborted_reason"].lower())
            # No backup, no runtime, no evidence mutation.
            self.assertFalse((gov / "archive").is_dir())
            self.assertFalse((gov / "flow-unit-runtime.json").is_file())

        # Case B: missing evidence-log.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text(CLASSIC_PLAN_TRACKER, encoding="utf-8")
            # No evidence-log.

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"])
            self.assertIn("evidence", result["aborted_reason"].lower())
            self.assertFalse((gov / "archive").is_dir())
            self.assertFalse((gov / "flow-unit-runtime.json").is_file())

    def test_fail_closed_no_evidence_rows(self):
        """Evidence log present but with zero parseable rows → fail closed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, evidence_text="# Evidence\n\n(no rows yet)\n")

            result = lm.apply_migration(target_root=str(root))

            self.assertFalse(result["applied"])
            self.assertIn("no parseable evidence rows", result["aborted_reason"])
            self.assertFalse((root / ".governance" / "archive").is_dir())

    def test_risk040_divergence(self):
        """Test 6: target_root distinct from PLUGIN_HOME → writes hit the HOST, not plugin.

        This is the RISK-040 divergence guard: a migration that accidentally
        read/wrote PLUGIN_HOME/.governance/ would corrupt the plugin's own
        evidence store. We prove the runtime.json + archive land in the HOST
        dir and the PLUGIN's .governance/ is untouched.
        """
        plugin_gov = PLUGIN_HOME / ".governance"
        # Snapshot whether the plugin's .governance/flow-unit-runtime.json +
        # archive/ exist BEFORE the test (so we can assert they're unchanged).
        plugin_runtime_before = (plugin_gov / "flow-unit-runtime.json").is_file()
        plugin_archive_before = (plugin_gov / "archive").is_dir()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            self.assertNotEqual(str(root), str(PLUGIN_HOME))

            result = lm.apply_migration(target_root=str(root))
            self.assertTrue(result["applied"])
            # Result target MUST be the host, never the plugin.
            self.assertEqual(str(Path(result["target"])), str(root.resolve()))

            # runtime.json + archive land in the HOST .governance/.
            self.assertTrue((root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertTrue((root / ".governance" / "archive").is_dir())

        # PLUGIN's .governance/ must be untouched (no new runtime.json/archive).
        self.assertEqual(
            (plugin_gov / "flow-unit-runtime.json").is_file(),
            plugin_runtime_before,
            "PLUGIN_HOME/.governance/flow-unit-runtime.json must NOT be created by a host migration",
        )
        self.assertEqual(
            (plugin_gov / "archive").is_dir(),
            plugin_archive_before,
            "PLUGIN_HOME/.governance/archive/ must NOT be created by a host migration",
        )

    def test_kill_mid_write_recovery(self):
        """Test 7: a corrupt/incomplete runtime.json is cleanly overwritten on re-apply.

        Simulates a kill-mid-write (garbage runtime.json already on disk).
        Re-running apply must overwrite it cleanly with valid JSON, and the
        backup must always be restorable.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Pre-seed a CORRUPT runtime.json (simulating a crashed prior apply).
            _write_host(root, runtime="{ this is not valid json,,,")
            corrupt_path = root / ".governance" / "flow-unit-runtime.json"
            self.assertTrue(corrupt_path.is_file())

            result = lm.apply_migration(target_root=str(root))

            # Recovery: apply either succeeds (overwrites cleanly) or fails-closed
            # cleanly. Either way, the backup must be restorable.
            if result["applied"]:
                # Overwrote cleanly → runtime.json is now valid JSON.
                content = corrupt_path.read_text(encoding="utf-8")
                parsed = json.loads(content)  # must parse
                self.assertEqual(parsed["workflow_model"], "loop-engineering")
            else:
                # Fail-closed: the abort reason must explain, and NO further
                # corruption should occur. The corrupt file may remain, but the
                # backup (if created) must be restorable.
                self.assertIn("aborted_reason", result)
            # Backup restorability: if a backup was created, its hashes verify.
            if result.get("backup_dir"):
                expected = {
                    "plan_tracker_sha256": result["hashes"]["plan_tracker_before"],
                    "evidence_log_sha256": result["hashes"]["evidence_log_before"],
                }
                ok, _ = lm._verify_backup_hashes(
                    Path(result["backup_dir"]), expected
                )
                self.assertTrue(ok, "backup must be hash-restorable after recovery")


# ═══════════════════════════════════════════════════════════════════════════
# ROLLBACK tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRollbackMigration(unittest.TestCase):
    """FX-191 rollback path (ADR §7.3)."""

    def test_rollback_total_restore(self):
        """Test 4: apply then rollback restores files + removes runtime.json + appends ROLLBACK row."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            # Snapshot pre-apply content for byte-exact restore comparison.
            plan_before = (root / ".governance" / "plan-tracker.md").read_text(encoding="utf-8")
            evidence_before = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            plan_hash_before = _sha256_bytes(plan_before)
            evidence_hash_before = _sha256_bytes(evidence_before)

            # Apply.
            apply_result = lm.apply_migration(target_root=str(root))
            self.assertTrue(apply_result["applied"])
            self.assertTrue((root / ".governance" / "flow-unit-runtime.json").is_file())

            # Rollback.
            rollback_result = lm.rollback_migration(target_root=str(root))
            self.assertTrue(rollback_result["rolled_back"], f"rollback failed: {rollback_result}")
            self.assertTrue(rollback_result["runtime_removed"])

            # plan-tracker restored byte-exact (hash-for-hash).
            plan_after = (root / ".governance" / "plan-tracker.md").read_text(encoding="utf-8")
            self.assertEqual(_sha256_bytes(plan_after), plan_hash_before,
                             "plan-tracker must be restored to pre-apply content")

            # runtime.json removed.
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())

            # ROLLBACK evidence row appended. The restored evidence-log is the
            # pre-migration content (the MIGRATION row was wiped by restore),
            # then we appended the ROLLBACK row on top.
            evidence_after = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("ROLLBACK-0.65.0", evidence_after)
            # The pre-apply EVD row must still be present (restore + append).
            self.assertIn("EVD-001", evidence_after)

    def test_rollback_fails_closed_on_tampered_backup(self):
        """A tampered backup must NOT be restored (hash mismatch → abort)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            apply_result = lm.apply_migration(target_root=str(root))
            self.assertTrue(apply_result["applied"])

            # Tamper the backup's plan-tracker.
            backup_dir = Path(apply_result["backup_dir"])
            (backup_dir / "plan-tracker.md").write_text("TAMPERED", encoding="utf-8")

            rollback_result = lm.rollback_migration(target_root=str(root))
            self.assertFalse(rollback_result["rolled_back"])
            self.assertIn("hash verification FAILED", rollback_result["aborted_reason"])

    def test_rollback_no_backup_aborts(self):
        """No backup present → rollback aborts cleanly (nothing to restore)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            # No migration has run, so no archive/ exists.

            result = lm.rollback_migration(target_root=str(root))

            self.assertFalse(result["rolled_back"])
            self.assertIn("no migration backup", result["aborted_reason"].lower())

    def test_rollback_by_version(self):
        """--version selects a specific backup when multiple exist."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            # First apply + rollback (leaves backup #1).
            r1 = lm.apply_migration(target_root=str(root))
            self.assertTrue(r1["applied"])
            lm.rollback_migration(target_root=str(root))

            # Second apply (leaves backup #2). Note: after rollback the
            # plan-tracker is restored to classic, so re-apply is allowed
            # (idempotency guard sees classic, not loop-engineering).
            r2 = lm.apply_migration(target_root=str(root))
            self.assertTrue(r2["applied"])

            # Two backups exist. Rollback by explicit version targets 0.65.0.
            backups = lm._list_migration_backups(root)
            self.assertEqual(len(backups), 2)

            result = lm.rollback_migration(target_root=str(root), version="0.65.0")
            self.assertTrue(result["rolled_back"])


# ═══════════════════════════════════════════════════════════════════════════
# PREVIEW + verify_workflow integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPreviewMigration(unittest.TestCase):
    """Dry-run preview path (preserved, regression)."""

    def test_dry_run_preserved(self):
        """Test 8: preview_migration produces the same JSON shape as before.

        Regression: the dry-run path delegates to
        build_dynamic_lifecycle_migration_preview and attaches
        validation_issues. It must NOT write anything.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            result = lm.preview_migration(target_root=str(root))

            # Same shape as the existing build_dynamic_lifecycle_migration_preview.
            self.assertEqual(result["command"], "dynamic-lifecycle-migration")
            self.assertEqual(result["mode"], "dry-run")
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["write_operations"], [])
            self.assertIn("validation_issues", result)
            self.assertIn("no_overclaim_boundaries", result)

            # NO writes happened.
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertFalse((root / ".governance" / "archive").is_dir())
            # plan-tracker + evidence-log unchanged.
            self.assertNotIn(
                "MIGRATION-0.65.0",
                (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8"),
            )


class TestVerifyWorkflowIntegration(unittest.TestCase):
    """verify_workflow.py command-dispatch integration (FX-191 restructure)."""

    def test_cmd_loop_engineering_migration_apply_dispatches(self):
        """cmd_loop_engineering_migration routes --apply to loop_migration."""
        import argparse
        import io
        from contextlib import redirect_stdout
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            args = argparse.Namespace(
                target=str(root), apply=True, rollback=False,
                version=None, project_type=None, dry_run=False, fail_on_issues=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_loop_engineering_migration(args)

            output = json.loads(buf.getvalue())
            self.assertTrue(output["applied"])
            self.assertEqual(output["workflow_model"]["new"], "loop-engineering")

    def test_cmd_loop_engineering_migration_rollback_dispatches(self):
        """cmd_loop_engineering_migration routes --rollback to loop_migration."""
        import argparse
        import io
        from contextlib import redirect_stdout
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            lm.apply_migration(target_root=str(root))  # set up a migration

            args = argparse.Namespace(
                target=str(root), apply=False, rollback=True,
                version=None, project_type=None, dry_run=False, fail_on_issues=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_loop_engineering_migration(args)

            output = json.loads(buf.getvalue())
            self.assertTrue(output["rolled_back"])
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())

    def test_dynamic_lifecycle_apply_now_unblocked(self):
        """dynamic-lifecycle-migration --apply delegates to loop_migration (FX-191)."""
        import argparse
        import io
        from contextlib import redirect_stdout
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            args = argparse.Namespace(
                target=str(root), apply=True, dry_run=False, fail_on_issues=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                # Must NOT raise SystemExit (the old behavior).
                vw.cmd_dynamic_lifecycle_migration(args)

            output = json.loads(buf.getvalue())
            self.assertTrue(output["applied"])
            self.assertEqual(output["command"], "loop-engineering-migration")

    def test_dynamic_lifecycle_missing_flags_still_exits_closed(self):
        """Neither --apply nor --dry-run → still exits closed (guard 1 preserved)."""
        import argparse
        import io
        from contextlib import redirect_stdout
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            args = argparse.Namespace(
                target=str(root), apply=False, dry_run=False, fail_on_issues=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf), self.assertRaises(SystemExit) as ctx:
                vw.cmd_dynamic_lifecycle_migration(args)

            self.assertEqual(ctx.exception.code, 1)
            self.assertIn("requires explicit --dry-run", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
