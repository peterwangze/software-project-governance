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
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
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


class ExecutionPacketWriteTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        gov = self.root / ".governance"
        gov.mkdir()
        self.path = gov / "execution-packets.json"
        (gov / "plan-tracker.md").write_text("\n".join([
            "# 计划跟踪", "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P1** | FIX-201 | first | | | one | 🔄 进行中 |",
            "| **P1** | FIX-202 | second | | | two | 🔄 进行中 |",
        ]), encoding="utf-8")
        self.command = [
            sys.executable, "-X", "utf8", str(_INFRA_DIR / "verify_workflow.py"),
            "--project-root", str(self.root), "execution-packet", "--write",
        ]

    def write(self, *tasks, write=True):
        args = SimpleNamespace(write=write, task=tasks)
        with mock.patch.object(vw, "EXECUTION_PACKET_PATH", self.path), \
             mock.patch.object(vw, "_active_execution_packet_tasks", _fake_tasks):
            vw.cmd_execution_packet(args)

    def test_selected_build_reads_one_locked_snapshot_and_converts_legacy_map(self):
        untouched = {"manual": "旧契约"}
        self.path.write_text(json.dumps({"FIX-202": untouched}), encoding="utf-8")
        read_text = Path.read_text
        lockfile = self.path.parent / vw.governance_store.LOCK_DIR_NAME / (self.path.name + ".lock")

        def read_locked(path, **kwargs):
            self.assertEqual(path, self.path)
            self.assertTrue(lockfile.is_file())
            return read_text(path, **kwargs)

        with mock.patch.object(Path, "read_text", autospec=True, side_effect=read_locked) as read, \
             mock.patch.object(vw, "build_execution_packet", wraps=vw.build_execution_packet) as build:
            self.write("FIX-201", "FIX-404")
        self.assertEqual(read.call_count, 1)
        self.assertEqual([c.args[0]["task_id"] for c in build.call_args_list], ["FIX-201"])
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(stored), {"version", "generated_at", "packets"})
        self.assertEqual(stored["packets"]["FIX-202"], untouched)
        self.assertEqual(set(stored["packets"]), {"FIX-201", "FIX-202"})

    def test_invalid_documents_refused_without_changing_bytes(self):
        for raw in (b"{", b"\xff", b"[]", b'{"packets":[]}', b'{"FIX-201":42}',
                    b'{"notes":{}}', b'{"packets":{"notes":{}}}', b'{"**FIX-201**":{}}',
                    b'{"packets":{"**FIX-201**":{}}}', b'{"packets":{"FIX-201":null}}',
                    b'{"version":2,"packets":{}}'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(SystemExit) as refusal:
                    self.write("FIX-201")
                self.assertEqual(refusal.exception.code, 1)
                self.assertEqual(self.path.read_bytes(), raw)

    def test_future_version_is_visible_to_readers_and_preview(self):
        raw = b'{"version":2,"packets":{}}'
        self.path.write_bytes(raw)
        with self.assertRaises(SystemExit):
            self.write("FIX-201", write=False)
        packets, error = vw._load_execution_packets(self.path)
        self.assertEqual(packets, {})
        self.assertIn("unsupported execution packet version", error)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_preview_of_other_task_refuses_malformed_packet_without_hiding_diagnostics(self):
        raw = b'{"packets":{"FIX-202":"broken"}}'
        self.path.write_bytes(raw)
        with mock.patch.object(vw, "_active_execution_packet_tasks", _fake_tasks):
            report = vw.check_execution_packets(self.path)
        self.assertEqual(report["entries"][1],
                         {"task_id": "FIX-202", "status": "FAIL", "issues": ["packet must be object"]})
        with self.assertRaises(SystemExit):
            self.write("FIX-201", write=False)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_failed_io_releases_lock_and_preserves_original(self):
        original = b'{ "packets": {} }'
        self.path.write_bytes(original)
        for failure in (
            mock.patch.object(Path, "read_text", side_effect=PermissionError("read denied")),
            mock.patch.object(vw.governance_store.os, "replace", side_effect=OSError("replace failed")),
            mock.patch.object(vw.governance_store, "_TargetLock",
                              side_effect=vw.governance_store.StoreError({"detail": "lock busy"})),
        ):
            with failure, self.assertRaises(SystemExit) as refusal:
                self.write("FIX-201")
            self.assertEqual(refusal.exception.code, 1)
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(list(self.path.parent.rglob("*.lock")), [])
            self.assertEqual(list(self.path.parent.glob("*.tmp")), [])
        with mock.patch.object(vw, "build_execution_packet") as build:
            self.write("FIX-404")
            build.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)

    def test_failed_lock_acquisition_keeps_external_file_and_allows_same_process_retry(self):
        lock = vw.governance_store._TargetLock(self.path)
        lock.path.write_bytes(b"another writer")
        with mock.patch.object(os, "open", side_effect=PermissionError("open denied")), \
             self.assertRaises(SystemExit):
            self.write("FIX-201")
        self.assertEqual(lock.path.read_bytes(), b"another writer")
        self.assertFalse(lock._inproc.locked())
        # An undeletable stale lock must respect the normal contention timeout.
        os.utime(lock.path, (1, 1))
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("unlink denied")):
            self.assertFalse(lock._stale())
        lock.path.unlink()
        self.assertFalse(self.path.exists())
        self.write("FIX-201")
        self.assertTrue(self.path.is_file())

    def test_failed_lock_pid_write_closes_descriptor_and_allows_same_process_retry(self):
        lock = vw.governance_store._TargetLock(self.path)
        with mock.patch.object(os, "write", side_effect=OSError("disk full")) as write, \
             self.assertRaises(SystemExit):
            self.write("FIX-201")
        with self.assertRaises(OSError):
            os.fstat(write.call_args.args[0])
        self.assertFalse(lock.path.exists())
        self.assertFalse(lock._inproc.locked())
        self.assertFalse(self.path.exists())
        self.write("FIX-201")
        self.assertTrue(self.path.is_file())

    def test_concurrent_cli_merges_and_real_cli_errors(self):
        with ExitStack() as processes:
            with vw.governance_store._TargetLock(self.path):
                writers = [
                    processes.enter_context(subprocess.Popen(
                        self.command + ["--task", task, "--budget", str(budget)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE))
                    for task, budget in (("FIX-201", 11), ("FIX-202", 22))
                ]
            for writer in writers:
                stdout, stderr = writer.communicate(timeout=60)
                self.assertEqual(writer.returncode, 0, stderr)
                self.assertIn(b"[OK] wrote", stdout)
        packets = json.loads(self.path.read_text(encoding="utf-8"))["packets"]
        self.assertEqual({k: v["budget"]["max_steps"] for k, v in packets.items()},
                         {"FIX-201": 11, "FIX-202": 22})
        self.path.write_bytes(b"damaged")
        refused = subprocess.run(self.command, capture_output=True, timeout=60)
        self.assertEqual(refused.returncode, 1)
        self.assertIn(b"invalid JSON", refused.stderr)
        self.assertEqual(self.path.read_bytes(), b"damaged")


if __name__ == "__main__":
    unittest.main()
