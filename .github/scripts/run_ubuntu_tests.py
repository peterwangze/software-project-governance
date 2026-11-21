"""Run the public Ubuntu suite and surface tests lost to missing dependencies."""

import sys
import unittest
from pathlib import Path


# These tests read the current host project's private governance records.
PRIVATE_DATA_TESTS = {
    "test_governance_store.PremiseAutoSourceTests.test_live_tree_bypass_floor",
    "test_governance_store.PremiseTrackerEventTests.test_dec368_retro_calibration_readonly_demo",
    "test_hooks.RealEvdStep12ReplayTests.test_current_real_rows_all_clean_under_real_step12",
    "test_triage_write_guard.GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows",
}

# The encoding control also requires Windows PowerShell with ANSI code page 936.
WINDOWS_TESTS = {
    "test_loop_learning.LearningTest.test_windows_state_lock_timeout_preserves_state",
    "test_verify_workflow.BootstrapScriptTests.test_bootstrap_cmd_success_emits_envelope_on_windows",
    "test_verify_workflow.BootstrapScriptTests.test_bootstrap_cmd_timeout_classified_on_windows",
    "test_utf8_read_guard.Utf8ReadSimulationTests.test_bare_getcontent_reproduces_gbk_mojibake_on_gbk_codepage",
}


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(
        str(root / "skills/software-project-governance/infra/tests")
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    allowed = PRIVATE_DATA_TESTS | WINDOWS_TESTS
    unexpected = [(test.id(), reason) for test, reason in result.skipped
                  if test.id() not in allowed]
    for test_id, reason in unexpected:
        print(f"Unexpected Ubuntu skip: {test_id}: {reason}", file=sys.stderr)
    return 0 if result.testsRun and result.wasSuccessful() and not unexpected else 1


if __name__ == "__main__":
    sys.exit(main())
