"""FIX-264 / REQ-145.7 — check-governance --summary-only tests (red→green).

Deliverable under test (design §3.1, test plan §5.5 — 11 cases):

1. ``--summary-only`` is a mutually exclusive new argument; the default (no
   ``--summary-only``) path is byte-identical to the pre-existing full-engine
   output (zero-regression, test #4).
2. ``_aggregate_check_summary(stdout_text)`` parses the captured full engine
   output into ``{issues_count, first_fail, first_warn, fail_items,
   warn_items, advisory_items, advisory, parse_degraded}``.
3. ``cmd_check_governance`` with ``--summary-only`` runs the full engine under a
   stdout capture and prints ``Governance: {N} issues`` (or ``[PASS]``) plus the
   first FAIL/WARN detail line; ``--level`` drives detail granularity;
   ``--fail-on-issues`` still exits 1 when N>0.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_summary_only.py -v
"""

import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402


def _engine_output(count, fail_lines=(), warn_lines=(), advisory_lines=(), degraded=False):
    """Build a realistic full-engine stdout with the requested severity lines."""
    parts = []
    parts.append("┌─ Check 1: Evidence Completeness ─────────────────────┐")
    for w in warn_lines:
        parts.append(f"│  [WARN] {w}")
    parts.append("└──────────────────────────────────────────────────────┘")
    parts.append("┌─ Check 18c: AI Execution Packet (FIX-084) ───────────┐")
    for fl in fail_lines:
        parts.append(f"│  [FAIL] {fl}")
    parts.append("└──────────────────────────────────────────────────────┘")
    parts.append("┌─ Check 28s: Governance Data Size (FIX-160) ─────────┐")
    for a in advisory_lines:
        parts.append(f"│  [ADVISORY] {a}")
    parts.append("└──────────────────────────────────────────────────────┘")
    if degraded:
        parts.append("│  Result: <format drifted> — no stable summary")
    elif count == 0:
        parts.append("│  Result: PASSED — 0 issues found")
    else:
        parts.append(f"│  Result: ISSUES FOUND — {count} issue(s)")
    return "\n".join(parts) + "\n"


def _fake_engine(stdout_text, count):
    """A stand-in for ``_run_full_engine_checks`` that prints engine text and
    returns the accumulated count (keeps the dispatch tests fast/deterministic)."""

    def inner(args):
        print(stdout_text, end="")
        return count

    return inner


def _args(summary_only=False, fail_on_issues=False, level="standard"):
    return types.SimpleNamespace(
        summary_only=summary_only, fail_on_issues=fail_on_issues,
        summary_level=level)


class AggregateSummaryTests(unittest.TestCase):
    """Injection tests for the pure ``_aggregate_check_summary`` parser."""

    def test_parse_degraded_on_format_drift(self):
        """Test case 8: no stable Result line → parse_degraded (fail-safe)."""
        text = _engine_output(0, degraded=True)
        s = vw._aggregate_check_summary(text)
        self.assertTrue(s["parse_degraded"])

    def test_count_and_first_severity(self):
        """Test case 7: count is parsed from the same Result line the engine
        printed (same-source); first FAIL/WARN are surfaced."""
        text = _engine_output(
            5, fail_lines=["FIX-222: allowed_change_scope is too broad"],
            warn_lines=["2 stale risk(s):"])
        s = vw._aggregate_check_summary(text)
        self.assertEqual(s["issues_count"], 5)
        self.assertIn("ISSUES FOUND — 5 issue(s)", text)  # same source
        self.assertEqual(s["first_fail"],
                         "18c: AI Execution Packet (FIX-084): "
                         "FIX-222: allowed_change_scope is too broad")
        self.assertEqual(s["first_warn"],
                         "1: Evidence Completeness: 2 stale risk(s):")
        self.assertEqual(s["advisory"], None)

    def test_pass_count_zero_and_no_details(self):
        """Test case 2: N=0 (PASSED) → count 0, no severity details."""
        text = _engine_output(0)
        s = vw._aggregate_check_summary(text)
        self.assertEqual(s["issues_count"], 0)
        self.assertFalse(s["parse_degraded"])
        self.assertIsNone(s["first_fail"])
        self.assertIsNone(s["first_warn"])

    def test_advisory_not_counted(self):
        """Test case 11: advisory (fatal_on_error=false) does not count and is
        surfaced only when it is the first issue."""
        text = _engine_output(0, advisory_lines=["governance files 2 ERROR, 0 WARN"])
        s = vw._aggregate_check_summary(text)
        self.assertEqual(s["issues_count"], 0)  # advisory not counted
        self.assertEqual(s["advisory"],
                         "28s: Governance Data Size (FIX-160): "
                         "governance files 2 ERROR, 0 WARN")
        self.assertIsNone(s["first_fail"])
        self.assertIsNone(s["first_warn"])


class SummaryOnlyDispatchTests(unittest.TestCase):
    """cmd_check_governance --summary-only flow (fast: engine mocked)."""

    def _run(self, text, count, args, expect_exit=None):
        buf = io.StringIO()
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(text, count)):
            if expect_exit is not None:
                with self.assertRaises(SystemExit) as ctx:
                    with redirect_stdout(buf):
                        vw.cmd_check_governance(args)
                self.assertEqual(ctx.exception.code, expect_exit)
            else:
                with redirect_stdout(buf):
                    vw.cmd_check_governance(args)
        return buf.getvalue()

    def test_issues_with_first_fail(self):
        """Test case 1: N>0 → 'Governance: {N} issues' + first [FAIL]."""
        text = _engine_output(3, fail_lines=["FIX-222: allowed_change_scope is too broad"])
        out = self._run(text, 3, _args(summary_only=True))
        self.assertIn("Governance: 3 issues", out)
        self.assertIn("[FAIL]", out)
        self.assertIn("FIX-222", out)

    def test_pass_when_no_issues(self):
        """Test case 2: N=0 → 'Governance: [PASS]' with no detail line (F1)."""
        text = _engine_output(0)
        out = self._run(text, 0, _args(summary_only=True))
        self.assertEqual(out.strip(), "Governance: [PASS]")

    def test_warn_without_fail_outputs_warn_line(self):
        """Test case 3: WARN without FAIL → [WARN] line, exit 0."""
        text = _engine_output(2, warn_lines=["2 stale risk(s):"])
        out = self._run(text, 2, _args(summary_only=True))
        self.assertIn("Governance: 2 issues", out)
        self.assertIn("[WARN]", out)
        self.assertNotIn("[FAIL]", out)

    def test_fail_on_issues_exits_one(self):
        """Test case 5: --fail-on-issues --summary-only → exit 1."""
        text = _engine_output(2, fail_lines=["FIX-222: x"])
        self._run(text, 2, _args(summary_only=True, fail_on_issues=True),
                  expect_exit=1)

    def test_level_lightweight_summary_plus_first_fail(self):
        """Test case 6: --level lightweight → summary + first FAIL only."""
        text = _engine_output(5, fail_lines=["FIX-222: x", "FIX-223: y"],
                              warn_lines=["2 stale risk(s):"])
        out = self._run(text, 5, _args(summary_only=True, level="lightweight"))
        lines = out.splitlines()
        self.assertEqual(lines[0], "Governance: 5 issues")
        self.assertEqual(len(lines), 2)  # summary + first FAIL only
        self.assertIn("FIX-222", lines[1])

    def test_level_strict_lists_all_severity(self):
        """--level strict → summary + all FAIL/WARN items (not just first)."""
        text = _engine_output(3, fail_lines=["FIX-222: x", "FIX-223: y"],
                              warn_lines=["2 stale risk(s):"])
        out = self._run(text, 3, _args(summary_only=True, level="strict"))
        self.assertIn("FIX-222", out)
        self.assertIn("FIX-223", out)
        self.assertIn("2 stale risk(s)", out)

    def test_parse_degraded_fail_safe_output(self):
        """Test case 8: format drift → 'Governance: N issues (parse degraded)'."""
        text = _engine_output(0, degraded=True)
        out = self._run(text, 0, _args(summary_only=True))
        self.assertIn("parse degraded", out)

    def test_advisory_only_annotated_after_pass(self):
        """Test case 11: advisory only → [PASS] count + [ADVISORY] note."""
        text = _engine_output(0, advisory_lines=["governance files 2 ERROR, 0 WARN"])
        out = self._run(text, 0, _args(summary_only=True))
        self.assertIn("Governance: [PASS]", out)
        self.assertIn("[ADVISORY]", out)

    def test_default_path_transparent_no_summary_prefix(self):
        """Test case 4: no --summary-only delegates to the full engine with no
        summary-only prefix (zero-regression mechanism)."""
        engine_output = (
            "┌─ Check 1: Evidence Completeness ─────────────────────┐\n"
            "│  Result: ISSUES FOUND — 3 issue(s)\n"
            "└──────────────────────────────────────────────────────┘\n")
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(engine_output, 3)) as eng:
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_governance(_args(summary_only=False))
            eng.assert_called_once()
            self.assertEqual(buf.getvalue(), engine_output)
            self.assertNotIn("Governance: ", buf.getvalue())


class BootstrapContractTests(unittest.TestCase):
    """Fail-safe states of the bootstrap health summary are documented
    (test cases 9/10: unavailable / timed out)."""

    def test_skill_documents_fail_safe_states(self):
        text = (_INFRA_DIR.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("check-governance --summary-only", text)
        self.assertIn("Governance: unavailable", text)
        self.assertIn("Governance: timed out", text)
        self.assertIn("parse degraded", text)

    def test_behavior_protocol_documents_fail_safe_states(self):
        proto = (_INFRA_DIR.parent / "references" / "behavior-protocol.md"
                 ).read_text(encoding="utf-8")
        self.assertIn("健康摘要", proto)
        self.assertIn("Governance: unavailable", proto)
        self.assertIn("Governance: timed out", proto)


if __name__ == "__main__":
    unittest.main()
