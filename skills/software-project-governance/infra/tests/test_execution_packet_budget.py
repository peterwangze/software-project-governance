"""FEAT-092: execution-packet budget guard (advisory max_steps field).

The pixel-RPG session telemetry (session-f3f46901, 2026-10-09) showed
unbounded single-task agent runs (AUD-001 409 steps / 90.1M tokens,
FEAT-011 277 steps / 79.4M, FIX-002 49.3M): the execution packet
constrained SCOPE but never BUDGET. This suite pins the minimal advisory
addition:

  1. ``execution-packet [--task ...] [--budget N]`` stamps
     ``budget.max_steps`` (positive int) on the generated packets — both
     the ``--write`` face and the read-only JSON preview carry it;
  2. the default generation OMITS the field entirely (缺省不写 — no
     behavioral change for callers that do not ask for a budget);
  3. illegal values fail closed: a non-positive ``--budget`` is an error
     (nothing written), and the shared structural validator
     (``_execution_packet_field_issues`` — Check 18c / write-guard face)
     flags a malformed ``budget`` on a loaded packet.

Advisory semantics by design (triage R3: 字段+派发提示起步，不是硬门禁):
nothing here blocks a dispatch — the Coordinator routing note lives in
SKILL.md「Agent 分发路由」.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_execution_packet_budget.py -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402


def _fake_tasks():
    return [
        {"task_id": "FIX-201", "priority": "P1", "status": "进行中",
         "title": "task one"},
        {"task_id": "FIX-202", "priority": "P1", "status": "进行中",
         "title": "task two"},
    ]


class ExecutionPacketBudgetTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="feat092_budget_")
        self.packet_path = Path(self.tmpdir) / "execution-packets.json"

    def _run(self, *, write=True, task=(), budget=...):
        """Invoke cmd_execution_packet under the patched paths.

        ``budget=...`` (the default sentinel) means "omit the attr", which
        is exactly what older in-repo callers construct via
        SimpleNamespace(write=..., task=...) — the command must keep
        accepting that shape (FEAT-080/FEAT-0296 tests do it bare).
        """
        kwargs = {"write": write, "task": list(task)}
        if budget is not ...:
            kwargs["budget"] = budget
        args = SimpleNamespace(**kwargs)
        with mock.patch.object(vw, "EXECUTION_PACKET_PATH", self.packet_path), \
             mock.patch.object(vw, "_active_execution_packet_tasks",
                               _fake_tasks):
            vw.cmd_execution_packet(args)

    # ── 1. --budget stamps budget.max_steps on write and preview ──────────

    def test_budget_written_for_selected_tasks(self):
        # Seed the runtime file like the FEAT-080 suite does — an unselected
        # active entry survives the incremental merge ONLY via the on-disk
        # carry-over (a bare --task --write regenerates the selection and
        # merges it into what the file already holds).
        seed = {
            "version": 1,
            "packets": {
                "FIX-202": {"task_id": "FIX-202", "priority": "P1",
                            "status": "进行中", "seeded": True},
            },
        }
        self.packet_path.write_text(
            json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
        self._run(write=True, task=["FIX-201"], budget=120)
        written = json.loads(self.packet_path.read_text(encoding="utf-8"))
        self.assertEqual(
            written["packets"]["FIX-201"]["budget"], {"max_steps": 120})
        # unselected active packets are preserved (FIX-296/FEAT-080 merge
        # semantics) and are NOT budget-stamped by a --task --budget run.
        self.assertIn("FIX-202", written["packets"])
        self.assertNotIn("budget", written["packets"]["FIX-202"])

    def test_budget_written_for_full_regeneration(self):
        self._run(write=True, task=[], budget=80)
        written = json.loads(self.packet_path.read_text(encoding="utf-8"))
        for task_id in ("FIX-201", "FIX-202"):
            self.assertEqual(
                written["packets"][task_id]["budget"], {"max_steps": 80})

    def test_read_only_preview_carries_budget_and_writes_nothing(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self._run(write=False, task=["FIX-201"], budget=150)
        self.assertFalse(self.packet_path.exists())
        preview = json.loads(buf.getvalue())
        self.assertEqual(
            preview["packets"]["FIX-201"]["budget"], {"max_steps": 150})

    def test_cli_parser_accepts_budget_flag(self):
        """Subprocess smoke on the real parser wiring (read-only preview —
        no --write, so nothing touches .governance)."""
        import subprocess
        engine = _INFRA_DIR / "verify_workflow.py"
        run = lambda *extra: subprocess.run(  # noqa: E731
            [sys.executable, str(engine), "execution-packet", *extra],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=str(_INFRA_DIR.parents[2]))
        ok = run("--task", "FEAT-092-NOSUCH", "--budget", "64")
        self.assertEqual(ok.returncode, 0, msg=ok.stderr[-400:])
        # read-only preview against the live tracker: a task id that matches
        # no active task yields an empty selection (print face = preview
        # with packets: {}), exit 0 — the flag itself parsed and passed the
        # cmd-level budget validation.
        self.assertIn('"packets"', ok.stdout)
        bad_type = run("--task", "FEAT-092-NOSUCH", "--budget", "many")
        self.assertEqual(bad_type.returncode, 2)  # argparse type=int refusal
        bad_range = run("--task", "FEAT-092-NOSUCH", "--budget", "0")
        self.assertEqual(bad_range.returncode, 2)  # cmd-level fail-closed

    # ── 2. 缺省不写 — no budget key without --budget ──────────────────────

    def test_default_generation_omits_budget(self):
        payload = vw.generate_execution_packets(existing={})
        for packet in payload["packets"].values():
            self.assertNotIn("budget", packet)

    def test_write_without_budget_omits_field(self):
        self._run(write=True, task=[], budget=...)  # attr omitted entirely
        written = json.loads(self.packet_path.read_text(encoding="utf-8"))
        for task_id in ("FIX-201", "FIX-202"):
            self.assertNotIn("budget", written["packets"][task_id])

    def test_regeneration_does_not_drop_manual_budget_enrichment(self):
        """The FIX-296 merge must keep a hand/CLI-enriched budget on
        regeneration without --budget (enrichment overlays the base)."""
        seed = {"FIX-201": {"task_id": "FIX-201", "priority": "P1",
                            "status": "进行中", "goal": "seeded",
                            "budget": {"max_steps": 200}}}
        self.packet_path.write_text(
            json.dumps({"version": 1, "packets": seed}, ensure_ascii=False),
            encoding="utf-8")
        self._run(write=True, task=["FIX-201"], budget=...)
        written = json.loads(self.packet_path.read_text(encoding="utf-8"))
        self.assertEqual(
            written["packets"]["FIX-201"]["budget"], {"max_steps": 200})

    # ── 3. 非法值报错 — fail-closed on non-positive / malformed budget ────

    def test_non_positive_budget_is_rejected_without_write(self):
        for bad in (0, -5):
            with self.assertRaises(SystemExit) as ctx:
                self._run(write=True, task=["FIX-201"], budget=bad)
            self.assertEqual(ctx.exception.code, 2)
            self.assertFalse(self.packet_path.exists())

    def test_validator_flags_malformed_budget_on_loaded_packet(self):
        base = {
            "task_id": "FIX-201", "priority": "P1", "status": "进行中",
            "goal": "g", "source": "plan-tracker.md##当前活跃事项",
        }
        for bad_budget in (
            {"max_steps": 0},             # non-positive
            {"max_steps": -1},            # negative
            {"max_steps": "120"},         # string, not int
            {"max_steps": 1.5},           # float, not int
            {"steps": 120},               # wrong key
            {"max_steps": 120, "x": 1},   # extra keys rejected (shape pin)
            [120],                        # not an object
        ):
            packet = dict(base, budget=bad_budget)
            issues = vw._execution_packet_field_issues(packet)
            self.assertTrue(
                any("budget" in issue for issue in issues),
                msg="malformed budget not flagged: {0!r}".format(bad_budget))

    def test_validator_accepts_legal_budget(self):
        base = {
            "task_id": "FIX-201", "priority": "P1", "status": "进行中",
            "goal": "g", "source": "plan-tracker.md##当前活跃事项",
        }
        issues = vw._execution_packet_field_issues(
            dict(base, budget={"max_steps": 120}))
        self.assertFalse([i for i in issues if "budget" in i])


if __name__ == "__main__":
    unittest.main()
