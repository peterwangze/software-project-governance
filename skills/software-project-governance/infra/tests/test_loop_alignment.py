"""Normal host commands preserve the user's acceptance from intake through independent exit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))

from delivery_acceptance import CONTRACT, RECEIPT, evaluate_delivery_acceptance
from loop_workflow import accept_delivery, release_issues
from review_record import write_review_record


class OutcomeWorkflowTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / ".governance").mkdir()
        self.labels = {"open": "Reopen the export", "total": "Reconcile every exported row"}
        self.file("product.txt", "invoice 19.99")
        self.file("trial.txt", "Compared the screen total against reopening the exported file.")
        self.contract = {"schema_version": 1, "goal_id": "invoice", "release_version": "1.2.0",
                         "artifact": "product.txt", "entrypoint": "invoice export",
                         "producer": "developer", "verifier": "Customer QA", "authority": "customer", "criteria": self.labels}
        self.contract_hash = self.write_json(CONTRACT, self.contract)
        self.receipt = dict(schema_version=1, contract_sha256=self.contract_hash,
                            artifact_sha256=self.sha("product.txt"), entrypoint="invoice export",
                            verifier="Customer QA", results={})

    def cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, "-X", "utf8", str(INFRA / "verify_workflow.py"),
                               "--project-root", str(self.root), *args], cwd=self.root,
                              env={**os.environ, "GIT_CONFIG_COUNT": "0"},
                              capture_output=True, encoding="utf-8", timeout=30)
        self.assertEqual(ok, proc.returncode == 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def file(self, name, text):
        (self.root / name).write_bytes(text.encode("utf-8"))
        return self.sha(name)

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def write_json(self, name, data):
        return self.file(name, json.dumps(data))

    def start(self, *extra):
        return self.cli("loop", "start", "--unit", "invoice", "--intent", "Audit the invoice total",
                        "--goal", "Deliver the invoice", "--acceptance", "Use the complete invoice export",
                        "--tier", "middle", "--gate", "G9", "--product-goal", "invoice", *extra)

    def status(self, uid="invoice", **kwargs):
        return self.cli("loop", "status", "--unit", uid, "--json", **kwargs)

    def learn(self, uid="invoice", candidate="product.txt", criterion="total", ok=True, replace=False):
        return self.cli("loop", "learn", "--unit", uid, "--id", "rows-v2" if replace else "rows", "--kind", "decision",
                        "--observation", "First-row export missed the second amount", "--action", "Export all rows",
                        "--validation", "Reopen the export and add both rows", "--evidence", "trial.txt",
                        "--candidate", candidate, "--criterion", criterion, *(("--supersedes", "rows") if replace else ()), ok=ok)

    def observation(self, criterion, status, text):
        name = criterion + ".log"
        self.receipt["results"][criterion] = dict(status=status, evidence=name,
                                                  evidence_sha256=self.file(name, text))
        self.receipt["artifact_sha256"] = self.sha("product.txt")
        self.write_json(RECEIPT, self.receipt)

    def test_scope_rework_product_and_fresh_process(self):
        self.start()
        self.learn()
        self.cli("loop", "start", "--unit", "format", "--parent", "invoice", "--criterion", "open", "--candidate", "trial.txt",
                 "--goal", "Check file opens", "--acceptance", "Print filename", "--tier", "inner",
                 "--check-command", json.dumps([sys.executable, "-c", "print('opens')", "trial.txt"]), "--expect-output", "opens")
        self.assertEqual(self.status("format")["root_contract"]["intent"], "Audit the invoice total")
        self.cli("loop", "verify", "--unit", "format")
        self.assertEqual(self.status()["learning"][0]["revalidation"]["status"], "pending")
        self.observation("open", "PASS", "Reopened via invoice export")
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.observation("total", "FAIL", "15.00 was exported")
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.assertEqual(self.status()["learning"][0]["revalidation"]["status"], "failed")
        self.file("product.txt", "invoice repaired 19.99")
        self.observation("total", "PASS", "Reopened the same invoice; sum equals 19.99")
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.learn(replace=True)
        self.cli("loop", "accept", "--unit", "invoice")
        completed = self.status()
        proof = completed["learning"][-1]["revalidation"]
        self.assertEqual((completed["runtime_status"], proof["status"]), ("completed", "passed"))
        self.assertTrue((self.root / ".governance" / proof["evidence_ref"]).is_file())
        bootstrap = self.cli("governance-bootstrap", "--format", "json")
        self.assertTrue(any(u["flow_unit_id"] == "invoice" and u["root_contract"]["criteria"]
                            for u in bootstrap["loops"]["units"]))
        self.file("product.txt", "wrong delivery candidate")
        self.assertEqual(self.status(ok=False)["learning"][0]["revalidation"]["status"], "stale")

    def test_windows_gbk_help_exposes_normal_intake_and_recovery(self):
        env = {**os.environ, "PYTHONIOENCODING": "gbk:strict", "PYTHONUTF8": "0"}
        for args, expected in (([], "goal-bridge"), (["loop"], "recheck"), (["loop", "start"], "--criteria")):
            proc = subprocess.run([sys.executable, str(INFRA / "verify_workflow.py"), *args, "--help"],
                                  env=env, capture_output=True, timeout=30)
            self.assertEqual(0, proc.returncode, proc.stderr.decode("gbk", errors="replace"))
            self.assertIn(expected, proc.stdout.decode("gbk"))

    def test_registered_intent_and_acceptance_cannot_be_replaced(self):
        self.cli("change-triage", "--task", "FIX-901", "--title", "Repair export", "--priority", "P1",
                 "--files", "product.txt", "--acceptance", "Reconcile all rows", "--demand-source", "user-named",
                 "--demand-basis", "User asked to audit the invoice")
        args = ("loop", "start", "--unit", "other", "--task", "FIX-901", "--tier", "inner", "--goal", "Format title")
        for alternative in (("--acceptance", "Title exists"), ("--intent", "Only the title matters")):
            self.cli(*args, *alternative, ok=False)
        self.assertEqual(self.status("FIX-901")["root_contract"]["acceptance"], "Reconcile all rows")

    def test_completed_product_rechecks_counterevidence_and_registered_revision(self):
        self.start()
        for key in self.labels:
            self.observation(key, "PASS", "Original sample ran " + key)
        self.cli("loop", "accept", "--unit", "invoice")
        event = dict(id="refund", kind="counterevidence", unit="invoice", base_revision=0,
                     actor="reporting customer", reason="Refund row disappears when reopened",
                     criteria={"total": self.labels["total"]})
        first = self.write_json("reported.json", event)
        self.cli("loop", "revise", "--unit", "invoice", "--evidence", "reported.json")
        self.assertNotEqual(self.status()["runtime_status"], "completed")
        self.assertFalse(evaluate_delivery_acceptance(self.root, goal_id="invoice")["pass"])
        self.receipt["revisions"] = [first]
        self.write_json(RECEIPT, self.receipt)
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.observation("total", "PASS", "Replayed reported refund row in the invoice")
        self.cli("loop", "accept", "--unit", "invoice")
        event.update(id="require-tax", kind="authorization", base_revision=1, actor="customer",
                     reason="Customer added the tax display to the order", criteria={"tax": "See tax after reopening"},
                     response=dict(message_id="support/4501", source="response.txt",
                                   sha256=self.file("response.txt", "Please include tax in the reopened invoice."),
                                   quote="Please include tax in the reopened invoice."))
        second = self.write_json("approved.json", event)
        self.cli("loop", "revise", "--unit", "invoice", "--evidence", "approved.json", ok=False)
        self.file(".governance/decision-log.md", f"| DEC-001 | 2026-11-22 | customer | Approved {second} | Verified user request |\n")
        self.cli("loop", "revise", "--unit", "invoice", "--evidence", "approved.json", "--decision", "DEC-001")
        basis = self.status()["root_contract"]
        self.assertEqual((basis["revision"], basis["original_criteria"], basis["intent"]),
                         (2, self.labels, "Audit the invoice total"))
        self.receipt["revisions"].append(second)
        self.observation("tax", "PASS", "Verified customer tax in reopened receipt")
        self.cli("loop", "accept", "--unit", "invoice")
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])

    def test_release_still_requires_independent_release_reviewer(self):
        self.start("--release-version", "1.2.0")
        for key in self.labels:
            self.observation(key, "PASS", "Signed product trial " + key)
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.file("review.md", "Independent release inspection of candidate 1.2.0.\n**审查结论**: **APPROVED**\n")
        record = write_review_record(task_id="invoice", round_n=0, result="APPROVED",
                                     report_path="review.md", reviewer="Release Reviewer",
                                     gate_id="G9", root=self.root, require_loop=True)
        self.assertNotIn("error", record, record)
        self.assertEqual([], release_issues(self.root, "invoice", "1.2.0"))
        self.file("product.txt", "swapped after reviewer exit")
        self.assertTrue(release_issues(self.root, "invoice", "1.2.0"))

    def test_ordinary_successor_retains_root_and_product_criteria(self):
        self.start()
        for key in self.labels:
            self.observation(key, "PASS", "Signed trial " + key)
        self.cli("loop", "accept", "--unit", "invoice")
        next_unit = self.cli("loop", "start", "--unit", "next", "--tier", "middle", "--gate", "G9", "--after", "invoice")
        self.assertEqual((next_unit["product_goal"], next_unit["product_contract_sha256"]), ("invoice", self.contract_hash))
        state = self.root / ".governance/flow-unit-runtime.json"
        before = state.read_bytes()
        competing = self.cli("loop", "start", "--unit", "rival", "--tier", "middle", "--gate", "G9",
                             "--after", "invoice", ok=False)
        self.assertIn("already continues in next", competing["error"])
        self.assertEqual(state.read_bytes(), before)
        self.assertEqual(self.status("next")["root_contract"]["criteria"], self.labels)
        self.observation("total", "FAIL", "New output is missing a row")
        self.cli("loop", "accept", "--unit", "next", ok=False)
        self.assertNotEqual(self.status("next")["runtime_status"], "completed")

    def assert_product_readiness(self, ready, uid="invoice"):
        check = self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice", ok=ready)
        self.assertEqual(ready, check["pass"])
        self.assertEqual(ready, evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.cli("loop", "accept", "--unit", uid, ok=ready)

    def test_preflights_consume_child_receipts_without_learning(self):
        self.start()
        self.file("component.txt", "rows")
        self.cli("loop", "start", "--unit", "format", "--tier", "inner", "--parent", "invoice",
                 "--criterion", "open", "--candidate", "component.txt", "--goal", "Check format",
                 "--acceptance", "Print rows", "--check-command",
                 json.dumps([sys.executable, "-c", "print('rows')", "component.txt"]), "--expect-output", "rows")
        for key in self.labels:
            self.observation(key, "PASS", "Independent product trial " + key)
        self.assert_product_readiness(False)
        self.cli("loop", "verify", "--unit", "format")
        self.assert_product_readiness(True)
        self.file("component.txt", "changed")
        self.assert_product_readiness(False)
        self.file("component.txt", "rows")
        self.assert_product_readiness(True)
        state = json.loads((self.root / ".governance/flow-unit-runtime.json").read_bytes())
        child = next(u for u in state["flow_units"] if u["flow_unit_id"] == "format")
        receipt = self.root / ".governance" / child["gate_history"][-1]["evidence_ref"]
        saved = receipt.read_bytes()
        receipt.write_bytes(saved + b" ")
        self.assert_product_readiness(False)
        receipt.unlink()
        self.assert_product_readiness(False)
        receipt.write_bytes(saved)
        self.assert_product_readiness(True)
        self.file("component.txt", "newly checked rows")
        self.cli("loop", "recheck", "--unit", "format")
        self.cli("loop", "verify", "--unit", "format")
        self.assert_product_readiness(True)

    def test_preflights_consume_unscoped_children_and_their_dependencies(self):
        self.start()
        self.file("component.txt", "rows")
        command = json.dumps([sys.executable, "-c", "print('rows')", "component.txt"])
        self.cli("loop", "start", "--unit", "prerequisite", "--tier", "inner", "--parent", "invoice",
                 "--criterion", "open", "--candidate", "component.txt", "--goal", "Check prerequisite",
                 "--acceptance", "Print rows", "--check-command", command, "--expect-output", "rows")
        self.cli("loop", "verify", "--unit", "prerequisite")
        self.cli("loop", "start", "--unit", "unscoped", "--tier", "inner", "--parent", "invoice",
                 "--depends-on", "prerequisite", "--goal", "Check local behavior", "--acceptance", "Print rows",
                 "--check-command", command, "--expect-output", "rows")
        for key in self.labels:
            self.observation(key, "PASS", "Independent product trial " + key)
        self.assert_product_readiness(False)
        self.cli("loop", "verify", "--unit", "unscoped")
        self.assert_product_readiness(True)
        self.file("component.txt", "changed")
        self.cli("loop", "recheck", "--unit", "prerequisite")
        self.assert_product_readiness(False)
        self.file("component.txt", "rows")
        self.cli("loop", "verify", "--unit", "prerequisite")
        self.assert_product_readiness(True)

    def root_route_successor(self, bound):
        if bound:
            self.cli("goal-bridge", "--action", "bind-intent", "--goal", "invoice", "--intent", "Audit invoice")
        else:
            self.start()
        self.learn()
        for key in self.labels:
            self.observation(key, "PASS", "Independent A trial " + key)
        accept = (("goal-bridge", "--action", "accept-delivery", "--goal", "invoice") if bound else
                  ("loop", "accept", "--unit", "invoice"))
        self.cli(*accept)
        self.cli(*accept)  # Original native receipt remains replayable.
        if bound:
            event = dict(id="route-sample", kind="counterevidence", unit="invoice", base_revision=0,
                         actor="customer", reason="Recheck the original row sample", criteria={"total": self.labels["total"]})
            self.receipt["revisions"] = [self.write_json("route-sample.json", event)]
            self.cli("loop", "revise", "--unit", "invoice", "--evidence", "route-sample.json")
            self.observation("total", "PASS", "Replayed the original row sample on A")
            self.cli(*accept)
            self.cli(*accept)
        path = self.root / ".governance/flow-unit-runtime.json"
        original = json.loads(path.read_bytes())["flow_units"][0]
        self.cli("loop", "start", "--unit", "next", "--after", "invoice", "--tier", "middle", "--gate", "G9")
        interrupted = json.loads(path.read_bytes())["flow_units"][-1]
        self.file("product.txt", "Independent replacement B")
        for key in self.labels:
            self.observation(key, "PASS", "Independent B trial " + key)
        self.assert_product_readiness(False, "next")  # Interrupted before selecting B.
        self.learn(uid="next", replace=True, ok=False)  # Cannot edit an ancestor's learning entry.
        self.file("alternative.txt", "Different root artifact")
        self.learn(uid="next", candidate="alternative.txt")
        self.assert_product_readiness(False, "next")  # Root decisions must target the frozen product path.
        self.learn(uid="next", replace=True)
        self.assert_product_readiness(True, "next")
        self.assertEqual(original, json.loads(path.read_bytes())["flow_units"][0])
        old_receipt = self.root / ".governance" / original["gate_history"][-1]["evidence_ref"]
        signed = old_receipt.read_bytes()
        old_receipt.unlink()
        self.assert_product_readiness(False, "next")
        old_receipt.write_bytes(signed)
        self.assert_product_readiness(True, "next")
        self.cli(*accept, ok=False)  # A's native exit cannot certify B retroactively.
        if bound:
            event.update(id="successor-sample", base_revision=1, reason="Recheck the sample on B")
            self.receipt["revisions"].append(self.write_json("successor-sample.json", event))
            # The mutable receipt can go missing while the signed A and B observations survive.
            (self.root / RECEIPT).unlink()
            self.cli("loop", "revise", "--unit", "invoice", "--evidence", "successor-sample.json")
            self.write_json(RECEIPT, self.receipt)
            self.assert_product_readiness(False, "next")
            self.observation("total", "PASS", "Independent A trial total")
            self.assert_product_readiness(False, "next")
            self.observation("total", "PASS", "Replayed the original row sample on B")
            self.assert_product_readiness(True, "next")
            preserved = json.loads(path.read_bytes())["flow_units"][0]
            self.assertEqual(original["gate_history"], preserved["gate_history"])
            self.assertEqual("completed", preserved["runtime_status"])
        self.cli("loop", "start", "--unit", "fork", "--after", "invoice", "--tier", "middle", "--gate", "G9", ok=False)
        self.assert_product_readiness(True, "next")
        # An older/interrupted runtime may already contain a divergent branch.
        # Preserve its ordinary declaration shape in this private fixture.
        interrupted.update(flow_unit_id="fork", task_id="fork")
        state = json.loads(path.read_bytes())
        state["flow_units"].append(interrupted)
        self.write_json(".governance/flow-unit-runtime.json", state)
        self.assert_product_readiness(False, "fork")  # Divergent live continuations cannot authorize each other.

    def test_root_route_successor_keeps_original_signed_history(self):
        self.root_route_successor(False)

    def test_bound_root_route_successor_cannot_replay_old_native_exit(self):
        self.root_route_successor(True)

    def test_product_dependency_preflight_is_nonrecursive(self):
        self.start()
        for key in self.labels:
            self.observation(key, "PASS", "Independent product trial " + key)
        self.cli("loop", "accept", "--unit", "invoice")
        self.cli("loop", "start", "--unit", "consumer", "--tier", "middle", "--gate", "G9",
                 "--product-goal", "invoice", "--depends-on", "invoice", "--goal", "Consume product",
                 "--acceptance", "Use independently accepted product")
        self.assert_product_readiness(True, "consumer")
        self.assert_product_readiness(True, "consumer")

    def test_scoped_successor_inherits_verifier_and_blocks_parent_until_retest(self):
        self.start()
        command = [sys.executable, "-c", "print(open('component.txt').read())", "component.txt"]
        self.file("component.txt", "rows")
        self.cli("loop", "start", "--unit", "format", "--tier", "inner", "--parent", "invoice", "--criterion", "open",
                 "--candidate", "component.txt", "--goal", "Check format", "--acceptance", "Print rows",
                 "--check-command", json.dumps(command), "--expect-output", "rows")
        self.cli("loop", "verify", "--unit", "format")
        params = ("loop", "start", "--unit", "format-next", "--after", "format", "--tier", "inner")
        self.cli(*params, "--criterion", "total", ok=False)
        successor = self.cli(*params)
        self.assertEqual((successor["parent_unit_id"], successor["criterion_scope"], successor["scope_artifact"],
                          successor["acceptance_command"]), ("invoice", ["open"], "component.txt", command))
        self.assertEqual(self.status("format-next")["root_contract"]["unit"], "invoice")
        for key in self.labels:
            self.observation(key, "PASS", "Independent trial " + key)
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.file("component.txt", "missing")
        self.cli("loop", "verify", "--unit", "format-next", ok=False)
        self.assertEqual(self.status("format")["scope_successors"], ["format-next"])
        self.file("component.txt", "rows")
        self.cli("loop", "verify", "--unit", "format-next")
        self.cli("loop", "accept", "--unit", "invoice")

    def test_consecutive_challenges_cannot_reuse_old_evidence_or_another_contract(self):
        self.start()
        for key in self.labels:
            self.observation(key, "PASS", "First signed trial " + key)
        self.cli("loop", "accept", "--unit", "invoice")
        hashes = []
        for n in range(2):
            event = dict(id=f"sample-{n}", kind="counterevidence", unit="invoice", base_revision=n,
                         actor="customer", reason=f"Original input {n} fails", criteria={"total": self.labels["total"]})
            name = f"sample-{n}.json"
            hashes.append(self.write_json(name, event))
            self.cli("loop", "revise", "--unit", "invoice", "--evidence", name)
            self.cli("loop", "revise", "--unit", "invoice", "--evidence", name)
        self.receipt["revisions"] = hashes
        self.write_json(RECEIPT, self.receipt)
        for selection in (dict(goal_id="invoice"), dict(release_version="1.2.0")):
            result = evaluate_delivery_acceptance(self.root, **selection)
            self.assertFalse(result["pass"], result)
            self.assertIn("fresh observation", " ".join(result["issues"]))
        self.observation("total", "PASS", "Replayed both reported cases and the normal input")
        self.cli("loop", "accept", "--unit", "invoice")
        self.contract["criteria"] = {"new": "Entirely different acceptance"}
        new_digest = self.write_json(CONTRACT, self.contract)
        self.assertFalse(evaluate_delivery_acceptance(self.root, goal_id="invoice")["pass"])
        self.receipt.update(contract_sha256=new_digest, revisions=[], results={})
        self.observation("new", "PASS", "New product independently checked")
        self.assertFalse(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.cli("loop", "start", "--unit", "new-invoice", "--tier", "middle", "--gate", "G9",
                 "--product-goal", "invoice", "--goal", "Another approved workflow", "--acceptance", "New verification")
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.cli("loop", "accept", "--unit", "new-invoice")
        self.assertEqual(self.status("invoice", ok=False)["root_contract"]["revision"], 2)

    def test_root_challenge_opens_only_affected_child_without_learning(self):
        self.start()
        for key in self.labels:
            self.file(key + ".txt", key)
            self.cli("loop", "start", "--unit", key, "--parent", "invoice", "--criterion", key, "--candidate", key + ".txt",
                     "--tier", "inner", "--goal", self.labels[key], "--acceptance", self.labels[key],
                     "--check-command", json.dumps([sys.executable, "-c", "print('ok')", key + ".txt"]), "--expect-output", "ok")
            self.cli("loop", "verify", "--unit", key)
            self.observation(key, "PASS", "Signed trial " + key)
        self.cli("loop", "accept", "--unit", "invoice")
        event = dict(id="another-total", kind="counterevidence", unit="invoice", base_revision=0, actor="tester",
                     reason="Refund not included", criteria={"total": self.labels["total"]})
        self.receipt["revisions"] = [self.write_json("reported.json", event)]
        self.cli("loop", "revise", "--unit", "invoice", "--evidence", "reported.json")
        self.assertEqual(self.status("open")["runtime_status"], "completed")
        self.assertEqual(self.status("total")["runtime_status"], "dormant")
        self.observation("total", "PASS", "Replayed refund fixture")
        self.cli("loop", "accept", "--unit", "invoice", ok=False)
        self.cli("loop", "verify", "--unit", "total")
        self.assertNotEqual(self.status()["runtime_status"], "completed")
        self.cli("loop", "accept", "--unit", "invoice")

    def test_scoped_lightweight_decision_needs_real_command_target(self):
        self.file("greeting.py", "print('old')")
        self.cli("loop", "start", "--unit", "greeting", "--tier", "inner", "--goal", "Display greeting",
                 "--acceptance", "Print hello", "--check-command", json.dumps([sys.executable, "greeting.py"]),
                 "--expect-output", "hello")
        self.learn("greeting", "product.txt", "acceptance", ok=False)
        self.learn("greeting", "greeting.py", "acceptance")
        self.cli("loop", "verify", "--unit", "greeting", ok=False)
        self.assertEqual(self.status("greeting")["learning"][0]["revalidation"]["status"], "failed")
        self.file("greeting.py", "print('hello')")
        self.cli("loop", "verify", "--unit", "greeting", ok=False)
        self.learn("greeting", "greeting.py", "acceptance", replace=True)
        self.cli("loop", "verify", "--unit", "greeting")
        self.assertEqual(self.status("greeting")["learning"][-1]["revalidation"]["status"], "passed")
        self.file("greeting.py", "print('hello')\n# another candidate")
        self.assertEqual("unverified", self.status("greeting", ok=False)["runtime_status"])
        self.cli("loop", "recheck", "--unit", "greeting")
        self.cli("loop", "learn", "--unit", "greeting", "--id", "rows-v3", "--kind", "decision",
                 "--observation", "New code with the same greeting", "--action", "Use replacement",
                 "--validation", "Run exact greeting check", "--evidence", "trial.txt", "--candidate", "greeting.py",
                 "--criterion", "acceptance", "--supersedes", "rows-v2")
        self.cli("loop", "verify", "--unit", "greeting")
        self.assertEqual("passed", self.status("greeting")["learning"][-1]["revalidation"]["status"])

    def test_named_criteria_can_precede_the_artifact_contract(self):
        (self.root / CONTRACT).unlink()
        self.cli("loop", "start", "--unit", "invoice", "--tier", "middle", "--gate", "G9", "--goal", "Audit the invoice",
                 "--acceptance", "Reopen and reconcile", "--authority", "customer", "--criteria", json.dumps(self.labels))
        self.assertIn("bind-product", self.status()["next_action"])
        self.write_json(CONTRACT, self.contract)
        self.cli("loop", "bind-product", "--unit", "invoice")
        self.cli("loop", "bind-product", "--unit", "invoice")
        for key in self.labels:
            self.observation(key, "PASS", "Reopen and check " + key)
        self.cli("loop", "accept", "--unit", "invoice")

    def test_early_accept_identifies_registered_product_and_pending_design_review(self):
        self.cli("loop", "start", "--unit", "design", "--tier", "middle", "--goal", "Review the invoice",
                 "--acceptance", "Reopen the invoice", "--product-goal", "invoice")
        issue = self.cli("loop", "accept", "--unit", "design", ok=False)["error"]
        self.assertIn("current G5 review", issue)
        self.assertIn("loop status --unit design --json", issue)

    def test_bound_goal_preflight_uses_the_same_revised_criteria_as_release(self):
        import goal_bridge
        gov = self.root / ".governance"
        goal_bridge.bind_intent("invoice", intent="Audit the invoice total", governance_dir=gov)
        for key in self.labels:
            self.observation(key, "PASS", "Observed " + key)
        self.assertTrue(goal_bridge._check_completion("invoice", gov)["pass"])
        accept_delivery(self.root, "invoice")
        event = dict(id="bound-refund", kind="counterevidence", unit="invoice", base_revision=0, actor="reporter",
                     reason="Refund was missed", criteria={"total": self.labels["total"]})
        self.receipt["revisions"] = [self.write_json("challenge.json", event)]
        self.cli("loop", "revise", "--unit", "invoice", "--evidence", "challenge.json")
        self.assertFalse(goal_bridge._check_completion("invoice", gov)["pass"])
        self.assertFalse(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.observation("total", "PASS", "Observed refund from the challenged sample")
        self.assertTrue(goal_bridge._check_completion("invoice", gov)["pass"])
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.assertEqual(accept_delivery(self.root, "invoice")["decision"], "exit")

    def test_changed_comparison_evidence_blocks_goal_release_and_native_replay(self):
        self.cli("goal-bridge", "--action", "bind-intent", "--goal", "invoice", "--intent", "Audit invoice")
        self.learn()
        for key in self.labels:
            self.observation(key, "PASS", "Independent acceptance for " + key)
        self.cli("goal-bridge", "--action", "accept-delivery", "--goal", "invoice")
        original = (self.root / "trial.txt").read_bytes()
        self.file("trial.txt", "Overwritten comparison testimony")
        check = self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice", ok=False)
        self.assertIn("learning evidence SHA-256 mismatch", " ".join(check["issues"]))
        release = evaluate_delivery_acceptance(self.root, release_version="1.2.0")
        self.assertFalse(release["pass"])
        with self.assertRaisesRegex(ValueError, "learning evidence SHA-256 mismatch"):
            accept_delivery(self.root, "invoice")
        (self.root / "trial.txt").write_bytes(original)
        self.assertTrue(self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice")["pass"])
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.assertTrue(accept_delivery(self.root, "invoice")["replayed"])
        self.file("product.txt", "A separately built invoice")
        self.observation("total", "PASS", "Checked the new invoice independently")
        check = self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice", ok=False)
        self.assertIn("selected candidate changed", " ".join(check["issues"]))
        self.assertFalse(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.cli("loop", "recheck", "--unit", "invoice")
        self.learn(replace=True)
        self.assertEqual("exit", self.cli("goal-bridge", "--action", "accept-delivery", "--goal", "invoice")["decision"])
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])

    def test_root_candidate_path_is_bound_and_child_can_validate_its_own_artifact(self):
        self.cli("goal-bridge", "--action", "bind-intent", "--goal", "invoice", "--intent", "Audit invoice")
        (self.root / "alternative.txt").write_bytes((self.root / "product.txt").read_bytes())
        self.learn(candidate="alternative.txt")
        for key in self.labels:
            self.observation(key, "PASS", "Independent receipt for the contracted product " + key)
        check = self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice", ok=False)
        self.assertIn("alternative.txt", " ".join(check["issues"]))
        self.assertFalse(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        with self.assertRaisesRegex(ValueError, "alternative.txt"):
            accept_delivery(self.root, "invoice")
        self.learn(replace=True)
        self.file("format.txt", "open")
        cmd = [sys.executable, "-c", "import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())", "format.txt"]
        self.cli("loop", "start", "--unit", "format", "--parent", "invoice", "--tier", "inner", "--criterion", "open",
                 "--candidate", "format.txt", "--goal", "Validate local format", "--acceptance", "Opens normally",
                 "--check-command", json.dumps(cmd), "--expect-output", "open")
        self.learn(uid="format", candidate="format.txt", criterion="open")
        self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice", ok=False)
        self.cli("loop", "verify", "--unit", "format")
        self.assertTrue(self.cli("goal-bridge", "--action", "check-completion", "--goal", "invoice")["pass"])
        self.assertTrue(evaluate_delivery_acceptance(self.root, release_version="1.2.0")["pass"])
        self.assertEqual(accept_delivery(self.root, "invoice")["decision"], "exit")

    def test_legacy_adoption_preserves_history_and_needs_new_source(self):
        args = ("loop", "start", "--unit", "historic", "--tier", "inner", "--goal", "Local goal", "--acceptance", "Local test")
        self.cli(*args)
        path = self.root / ".governance/flow-unit-runtime.json"
        state = json.loads(path.read_bytes())
        historic = state["flow_units"][0]
        del historic["root_contract"]  # A real pre-feature v2 shape.
        path.write_text(json.dumps(state), encoding="utf-8")
        before = path.read_bytes()
        self.cli(*args)
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("legacy", self.status("historic")["root_provenance"])
        self.file("original.txt", "I need every exported row to reconcile")
        params = ("loop", "start", "--unit", "new", "--tier", "middle", "--goal", "Audit export",
                  "--acceptance", "All rows reconcile", "--adopt-legacy", "historic", "--intent-source", "original.txt")
        self.cli(*params, "--intent", "missing quote", ok=False)
        self.cli(*params, "--intent", "I need every exported row to reconcile")
        self.assertEqual(self.status("new")["root_contract"]["adopted_from"], "historic")
        self.assertEqual(json.loads(path.read_bytes())["flow_units"][0], historic)
