"""Native work units through the same entry points used by a host project."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))
import loop_workflow
from review_record import write_review_record


class NativeWorkflowTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.rnd = 0

    def cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, "-X", "utf8", str(INFRA / "verify_workflow.py"),
                               "--project-root", str(self.root), *args], cwd=self.root,
                              capture_output=True, encoding="utf-8")
        self.assertEqual(ok, proc.returncode == 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def start(self, uid, tier, **extra):
        return loop_workflow.start(self.root, unit_id=uid, tier=tier, goal="Deliver " + uid,
                                   acceptance="The specified behavior is observed", gate=None, **extra)

    def review(self, uid, result, *, gate=None):
        report = self.root / f"observation-{self.rnd}.md"
        current = self.state(uid)
        version = current.get("release_version") or ""
        reviewer = current.get("release_reviewer") if version and current["gate_state"]["gate_id"] == "G9" else "independent-reviewer"
        report.write_text(f"Candidate {version}. Inspected the declared artifact against its acceptance criteria.\n"
                          f"**审查结论**: **{result}**\n", encoding="utf-8")
        record = write_review_record(task_id=uid, round_n=self.rnd, result=result,
                                     report_path=report.name, reviewer=reviewer,
                                     gate_id=gate, root=self.root, require_loop=True)
        self.rnd += 1
        return record

    def state(self, uid):
        return loop_workflow._unit(loop_workflow._payload(loop_workflow.runtime_path(self.root)), uid)

    def test_nested_rework_then_exit(self):
        self.start("product", "outer")
        self.start("delivery", "middle", parent="product")
        self.start("patch", "inner", parent="delivery")
        results = [("delivery", "G5", "APPROVED", "G7"), ("patch", "G6", "APPROVED", "G6"),
                   ("delivery", "G7", "NEEDS_CHANGE", "G6"), ("delivery", "G6", "APPROVED", "G7"),
                   ("delivery", "G7", "APPROVED", "G9"),
                   ("delivery", "G9", "APPROVED", "G9"), ("product", "G10", "APPROVED", "G11"),
                   ("product", "G11", "APPROVED", "G11")]
        for uid, gate, result, following in results:
            with self.subTest(uid=uid, gate=gate, result=result):
                rec = self.review(uid, result, gate=gate)
                self.assertNotIn("error", rec)
                state = self.state(uid)
                self.assertEqual(following, state["gate_state"]["gate_id"])
                self.assertEqual(result, state["gate_history"][-1]["result"])
                reason = rec["wiring"]["reason"]
                self.assertIn("Deliver " + uid, reason)
                self.assertIn(gate, reason)
                if gate == "G6" and uid == "delivery":
                    self.assertIn("return for recheck at middle G7", reason)
                elif gate == "G5":
                    self.assertIn("advance to middle G7", reason)
                elif rec["wiring"]["decision"] == "exit":
                    self.assertIn("work unit completed", reason)
        self.assertEqual("completed", self.state("product")["runtime_status"])
        self.assertEqual(5, len(self.state("delivery")["gate_history"]))
        replay = loop_workflow.gate_review(self.root, "delivery", "G5", "REVIEW-delivery-R0")
        self.assertEqual("advance", replay["decision"])
        self.assertTrue(replay["replayed"])

    def test_public_single_fix_and_false_approval(self):
        self.cli("loop", "start", "--unit", "fix", "--tier", "inner", "--goal", "Repair greeting",
                 "--acceptance", "The emitted greeting matches the given input")
        record = self.review("fix", "NEEDS_CHANGE")
        self.assertNotIn("error", record)
        failed_record = self.root / ".governance/review-fix-R0.md"
        original = failed_record.read_text(encoding="utf-8")
        failed_record.write_text(original.replace("NEEDS_CHANGE", "APPROVED"), encoding="utf-8")
        self.assertIn("error", self.cli("loop", "gate", "--unit", "fix", "--gate", "G6",
                                        "--review", "REVIEW-fix-R0", ok=False))
        failed_record.write_text(original, encoding="utf-8")
        self.assertNotIn("error", self.review("fix", "APPROVED"))
        status = self.cli("loop", "status", "--unit", "fix")
        self.assertEqual(("completed", 1), (status["runtime_status"], status["loop_count"]))
        self.assertTrue(loop_workflow.release_issues(self.root, "fix", "1.0.0"))

    def test_release_waits_for_approved_scoped_evidence(self):
        self.start("build", "middle", release_version="1.0.0")
        self.start("test", "inner", parent="build")
        self.assertTrue(loop_workflow.release_issues(self.root, "build", "1.0.0"))
        self.assertNotIn("error", self.review("build", "APPROVED"))
        pending = self.review("build", "APPROVED")
        self.assertEqual("loop_gate_pending", pending["code"])
        self.assertNotIn("error", self.review("test", "APPROVED"))
        loop_workflow.gate_review(self.root, "build", "G7", "REVIEW-build-R1")
        self.assertNotIn("error", self.review("build", "APPROVED"))
        self.assertNotIn("error", self.review("build", "APPROVED"))
        self.assertEqual([], loop_workflow.release_issues(self.root, "build", "1.0.0"))
        result = self.cli("check-release", "--unit", "build", "--version", "1.0.0", "--json")
        self.assertTrue(result["pass"], result["issues"])
        self.assertNotIn("one_dot_zero_blockers", result["details"])
        wrong = self.cli("check-release", "--unit", "build", "--version", "0.45.0", "--json", ok=False)
        self.assertFalse(wrong["details"]["release_loop"]["pass"])
        self.assertNotIn("release_replay", wrong["details"])
        self.assertTrue(loop_workflow.release_issues(self.root, "build", "1.1.0"))
        (self.root / "observation-4.md").write_text("changed", encoding="utf-8")
        self.assertTrue(loop_workflow.release_issues(self.root, "build", "1.0.0"))

    def test_lightweight_verification_observes_real_output_and_starts_next_iteration(self):
        artifact = self.root / "greeting.py"
        artifact.write_text("print('incorrect')", encoding="utf-8")
        args = ("loop", "start", "--unit", "greeting", "--tier", "inner",
                "--goal", "Display the requested greeting", "--acceptance", "prints hello",
                "--check-command", json.dumps([sys.executable, str(artifact)]), "--expect-output", "hello")
        self.cli(*args)
        result = self.cli("loop", "verify", "--unit", "greeting", ok=False)
        self.assertEqual("iterate", result["decision"])
        ref = self.state("greeting")["gate_history"][-1]["evidence_ref"]
        observation = json.loads((self.root / ".governance" / ref).read_text(encoding="utf-8"))
        self.assertEqual("incorrect", observation["stdout"].strip())
        artifact.write_text("print('hello')", encoding="utf-8")
        self.assertEqual("exit", self.cli("loop", "verify", "--unit", "greeting")["decision"])
        after = self.cli("loop", "start", "--unit", "feedback", "--tier", "outer", "--after", "greeting")
        self.assertEqual(("Display the requested greeting", ["greeting"]), (after["goal"], after["dependencies"]))

    def test_amount_requires_complete_stdout_in_command_and_receipt(self):
        from checks.loop_receipts import verify_attempt
        emitter = self.root / "invoice.py"
        emitter.write_text("import sys\nfrom pathlib import Path\n"
                           "sys.stdout.buffer.write(Path('amount.bin').read_bytes())\n", encoding="utf-8")
        amount = self.root / "amount.bin"
        for index, wrong in enumerate((b"USD 30", b"USD 310", b"USD 31 extra")):
            uid = f"invoice-{index}"
            self.cli("loop", "start", "--unit", uid, "--tier", "inner", "--goal", "Show the requested invoice amount",
                     "--acceptance", "The displayed total matches USD 31", "--check-command",
                     json.dumps([sys.executable, str(emitter)]), "--expect-output", "USD 31")
            amount.write_bytes(wrong)
            self.assertEqual(self.cli("loop", "verify", "--unit", uid, ok=False)["decision"], "iterate")
            unit = self.state(uid)
            attempt = unit["gate_history"][-1]
            verify_attempt(self.root, unit, attempt, 0)
            with self.assertRaisesRegex(ValueError, "result differs"):
                verify_attempt(self.root, unit, dict(attempt, result="APPROVED"), 0)
            amount.write_bytes(b"USD 31\r\n")
            self.assertEqual(self.cli("loop", "verify", "--unit", uid)["decision"], "exit")
            self.assertEqual(self.cli("loop", "status", "--unit", uid)["runtime_status"], "completed")
        receipt = self.state(uid)["gate_history"][-1]["evidence_ref"]
        (self.root / ".governance" / receipt).write_bytes(b"tampered")
        self.assertEqual(self.cli("loop", "status", "--unit", uid, ok=False)["runtime_status"], "unverified")

    def test_stdout_comparison_preserves_spaces_extra_lines_and_unreadable_bytes(self):
        from checks.loop_receipts import command_observation_passes
        for actual, expected, accepted in (("A\r\nB\n", "A\nB", True), ("USD 31", "USD 31\n", True),
                                           (" USD 31", "USD 31", False), ("USD 31 ", "USD 31", False),
                                           ("USD 31\n\n", "USD 31", False), ("USD 31" + " " * 100000, "USD 31", False)):
            with self.subTest(actual=actual[:30], expected=expected):
                self.assertEqual(command_observation_passes({"returncode": 0, "stdout": actual, "expected_output": expected}), accepted)
        self.assertFalse(command_observation_passes({"returncode": 0, "expected_output": "any"}))
        self.assertFalse(command_observation_passes({"returncode": 1, "stdout": "USD 31", "expected_output": "USD 31"}))
        self.start("encoding", "inner", check_command=[sys.executable, "-c", "import sys;sys.stdout.buffer.write(bytes([255]))"],
                   expect_output="\ufffd")
        self.assertEqual(loop_workflow.verify_command(self.root, "encoding")["decision"], "iterate")
        state = self.state("encoding")
        ref = state["gate_history"][-1]["evidence_ref"]
        observation = json.loads((self.root / ".governance" / ref).read_bytes())
        self.assertIn("not valid UTF-8", observation["error"])
        self.assertNotIn("stdout", observation)

    def test_intake_and_dependency_admission_on_fresh_host(self):
        args = ("change-triage", "--task", "FIX-611", "--priority", "P1", "--files", "item.py",
                "--demand-source", "active-defect", "--title", "Correct output", "--acceptance", "Print accepted value")
        self.assertEqual("FIX-611", self.cli(*args)["unit"])
        self.assertTrue(self.cli(*args)["replayed"])
        self.start("second", "inner", dependencies=["FIX-611"])
        self.assertEqual("dormant", self.state("second")["runtime_status"])
        self.assertNotIn("error", self.review("FIX-611", "APPROVED"))
        self.assertNotIn("error", self.review("second", "APPROVED"))
        self.assertEqual("completed", self.state("second")["runtime_status"])

    def test_reviewer_role_follows_identity_and_preserves_scope(self):
        self.start("delivery", "middle")
        report = self.root / "test.md"
        report.write_text("Observed design conforms. **APPROVED**", encoding="utf-8")
        def record(reviewer):
            return write_review_record(task_id="delivery", round_n=0, result="APPROVED",
                                       report_path=report.name, reviewer=reviewer, root=self.root, require_loop=True)
        self.assertIn("error", record("Code Reviewer"))
        self.assertNotIn("error", record("Design Reviewer"))
        self.assertEqual("G7", self.state("delivery")["gate_state"]["gate_id"])

    def test_g1_escalation_requires_observed_resolution_and_new_review(self):
        loop_workflow.start(self.root, unit_id="init", tier="setup", gate="G1",
                            goal="Authorize the work", acceptance="The project sponsor authorizes the scope")
        self.assertNotIn("error", self.review("init", "NEEDS_CHANGE"))
        self.assertEqual("blocked", self.state("init")["runtime_status"])
        (self.root / "resolution.md").write_text("Sponsor adjusted the agreed scope.", encoding="utf-8")
        recovered = self.cli("loop", "resume", "--unit", "init", "--evidence", "resolution.md", "--actor", "sponsor")
        self.assertEqual(("active", "pending"), (recovered["runtime_status"], recovered["gate_state"]["status"]))
        self.assertNotIn("error", self.review("init", "APPROVED"))
        with self.assertRaisesRegex(ValueError, "one-time"):
            loop_workflow.start(self.root, unit_id="other", tier="setup", gate="G1",
                                goal="Second request", acceptance="Scope authorization")

    def test_inner_test_gate_reworks_then_returns_to_its_original_scope(self):
        unit = loop_workflow.start(self.root, unit_id="tested", tier="inner", gate="G7",
                                   goal="Validate the repair", acceptance="Replaying the witnessed defect succeeds")
        self.assertNotIn("title", unit)
        self.assertNotIn("decomposition_confirmed", loop_workflow._payload(loop_workflow.runtime_path(self.root)))
        for gate, verdict, next_gate in (("G7", "NEEDS_CHANGE", "G6"), ("G6", "APPROVED", "G7"),
                                         ("G7", "APPROVED", "G7")):
            self.assertNotIn("error", self.review("tested", verdict, gate=gate))
            self.assertEqual(next_gate, self.state("tested")["gate_state"]["gate_id"])
        self.assertEqual("completed", self.state("tested")["runtime_status"])

    def test_combined_wait_cycle_is_refused_without_mutation(self):
        self.start("P", "middle")
        self.start("B", "inner", dependencies=["P"])
        path = loop_workflow.runtime_path(self.root)
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "cyclic child/dependency"):
            self.start("C", "inner", parent="P", dependencies=["B"])
        self.assertEqual(original, path.read_bytes())

    def test_consumers_require_their_predecessors_actual_evidence(self):
        self.start("P", "middle")
        self.start("child", "inner", parent="P", check_command=[sys.executable, "-c", "print('actual')"], expect_output="actual")
        loop_workflow.verify_command(self.root, "child")
        self.assertNotIn("error", self.review("P", "APPROVED"))
        closed = self.state("child")
        receipt = self.root / ".governance" / closed["gate_history"][-1]["evidence_ref"]
        receipt.unlink()
        for kwargs in ({"dependencies": ["child"]}, {"after": "child"}):
            with self.assertRaisesRegex(ValueError, "completion evidence unavailable"):
                self.start("next", "inner", **kwargs)
        self.assertEqual("loop_gate_pending", self.review("P", "APPROVED")["code"])
        self.assertEqual("G7", self.state("P")["gate_state"]["gate_id"])

    def test_contradictory_gate_is_invalid_and_unchanged(self):
        self.start("live", "inner")
        path = loop_workflow.runtime_path(self.root)
        state = json.loads(path.read_bytes())
        state["flow_units"][0]["gate_state"]["status"] = "passed"
        path.write_text(json.dumps(state), encoding="utf-8")
        original = path.read_bytes()
        self.assertEqual("invalid", self.cli("loop", "status", "--json", ok=False)["state"])
        with self.assertRaisesRegex(ValueError, "conflicts with gate"):
            self.start("next", "inner")
        self.assertEqual(original, path.read_bytes())

    def test_formal_reviewers_can_serve_multiple_local_gates(self):
        for tier, gate, reviewer, next_gate in (
            ("setup", "G1", "Requirement Reviewer", "G1"), ("setup", "G2", "Requirement Reviewer", "G3"),
            ("setup", "G3", "Tech Reviewer", "G4"), ("setup", "G4", "Design Reviewer", "G4"),
            ("middle", "G8", "Release Reviewer", "G9"), ("inner", "G7", "Test Reviewer", "G7"),
            ("outer", "G10", "Retro Reviewer", "G11"), ("outer", "G11", "Retro Reviewer", "G11"),
        ):
            with self.subTest(gate=gate):
                with tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    loop_workflow.start(root, unit_id="work", tier=tier, gate=gate,
                                        goal="Check observed behavior", acceptance="Review receipt identifies result")
                    report = root / "reported.md"
                    report.write_text("Observed the user path. **APPROVED**", encoding="utf-8")
                    record = write_review_record(task_id="work", round_n=0, result="APPROVED", reviewer=reviewer,
                                                 report_path=report.name, root=root, require_loop=True)
                    self.assertNotIn("error", record)
                    state = loop_workflow._payload(loop_workflow.runtime_path(root))["flow_units"][0]
                    self.assertEqual(next_gate, state["gate_state"]["gate_id"])
