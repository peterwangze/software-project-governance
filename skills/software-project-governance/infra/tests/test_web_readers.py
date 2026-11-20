"""Exercise /api/governance against the same host with and without the CLI engine."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

INFRA = Path(__file__).resolve().parents[1]
ROOT = INFRA.parents[2]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

PLAN = """## 项目配置
- **工作流版本**: fixture
- **触发模式**: always-on
## 项目总览
| 项目 | 阶段 | 总数 | 完成 | 阻塞 | 风险 | Gate | 复盘 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| demo | test | 3 | 2 | 1 | 1 | G1 | today |
## Gate 状态跟踪（G1-G11）
| Gate | 跃迁 | 状态 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| G1 | `start|resume` | passed | today | EVD-1 |
| G2 | unpaired [ | passed | today | EVD-1 |
| G3 | display 5" panel | passed | today | EVD-1 |
| G4 | code `[` | passed | today | EVD-1 |
| G5 | {"next":["a|b","["]} | passed | today | EVD-1 |
| G6 | unpaired `tick | passed | today | EVD-1 |
"""
TRANSITIONS = ["`start|resume`", "unpaired [", 'display 5" panel', "code `[`",
               '{"next":["a|b","["]}', "unpaired `tick"]
EVIDENCE = """| EVD-1 | TASK-1 | `read|write` | notes | 2026-01-01 | G1 | done |
| REVIEW-API-1 | TASK-2 | {"field":"a|b"} | notes | 2026-01-02 | G1 | done |
EVD-999 appears outside the table.
"""
RISK = """| 编号 | 风险/阻塞描述 | 当前状态 | 截止日期 |
| --- | --- | --- | --- |
| RISK-1 | DSH runtime | **缓解中** | deadline |
"""


def load_server(degraded):
    spec = spec_from_file_location("spg_web_fixture", ROOT / "web" / "server.py")
    module = module_from_spec(spec)
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, "path", list(sys.path)))
        if degraded:
            stack.enter_context(patch.dict(sys.modules, {"verify_workflow": None}))
        spec.loader.exec_module(module)
    return module


def request_payload(server, root):
    """Exercise the actual HTTP request dispatcher and JSON serializer without a socket."""
    handler = server.Handler.__new__(server.Handler)
    handler.server = SimpleNamespace(project_root=root)
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"
    handler.requestline = "GET /api/governance HTTP/1.1"
    handler.path = "/api/governance"
    handler.address_string = lambda: "fixture"
    with redirect_stderr(io.StringIO()):
        handler.do_GET()
    headers, body = handler.wfile.getvalue().split(b"\r\n\r\n", 1)
    return headers, json.loads(body)


class WebReaderContractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.facts = self.root / ".governance"
        self.facts.mkdir()
        self.plan = self.facts / "plan-tracker.md"
        self.plan.write_text(PLAN, encoding="utf-8")
        (self.facts / "evidence-log.md").write_text(EVIDENCE, encoding="utf-8")
        (self.facts / "risk-log.md").write_text(RISK, encoding="utf-8")

    def payload(self, degraded):
        server = load_server(degraded)
        headers, payload = request_payload(server, self.root)
        self.assertIn(b"200 OK", headers)
        self.assertIn(b"application/json", headers)
        return payload

    def record_review(self, unit, gate, verdict):
        from review_record import write_review_record

        report = self.root / f"{unit}-report.md"
        report.write_text(f"Checked the delivered behavior against its acceptance criteria.\n"
                          f"**审查结论**: **{verdict}**\n", encoding="utf-8")
        record = write_review_record(task_id=unit, round_n=0, result=verdict,
                                     report_path=report.name, reviewer="independent-reviewer",
                                     gate_id=gate, root=self.root, require_loop=True)
        self.assertNotIn("error", record, record)

    def test_dashboard_does_not_depend_on_cli_engine(self):
        normal = self.payload(False)
        without_engine = self.payload(True)
        self.assertEqual(normal, without_engine)
        self.assertNotIn("error", normal)
        self.assertEqual(normal["workflow_version"], "fixture")
        self.assertNotIn("gates", normal)
        self.assertEqual(normal["loops"]["state"], "empty")
        self.assertEqual(normal["evidence_count"], 2)
        self.assertEqual([row["category"] for row in normal["recent_evidence"]],
                         ['{"field":"a|b"}', "`read|write`"])
        self.assertEqual(normal["open_risks"], [
            {"id": "RISK-1", "description": "DSH runtime", "status": "**缓解中**", "deadline": "deadline"}])

    def test_bootstrap_web_and_rollup_share_the_same_units(self):
        import bootstrap_aggregate as bootstrap
        import governance_readers as readers
        import loop_workflow as workflow
        import resolve_entry
        import time

        workflow.start(self.root, unit_id="parent", tier="middle", goal="Ship the host command",
                       acceptance="A clean host runs the command.")
        workflow.start(self.root, unit_id="child", tier="inner", parent="parent", goal="Quote paths",
                       acceptance="A path containing a space works.")
        self.record_review("child", "G6", "NEEDS_CHANGE")
        path = workflow.runtime_path(self.root)
        view = readers.loop_state(self.root)
        self.assertEqual(view["state"], "ready")
        self.assertEqual(view, self.payload(True)["loops"])
        payload = bootstrap._build_payload(self.root, resolve_entry.resolve(self.root),
                                           3000, "standard", time.monotonic())
        self.assertEqual(payload["loops"], view)
        self.assertNotIn("candidates", payload)
        self.assertEqual(view["units"][0]["open_children"], ["child"])
        unit = view["units"][1]
        self.assertEqual((unit["parent_unit_id"], unit["active_loop_tier"], unit["loop_count"]),
                         ("parent", "inner", 1))
        self.assertIn("Rework", unit["next_action"])
        self.assertIn("review-child-R0.md", bootstrap.format_text(payload))

        # A malformed snapshot must never fall back to the fixture's historical passes.
        for corrupt in (b"{invalid", b"\xff", b'{"workflow_model":"loop-engineering"}'):
            with self.subTest(corrupt=corrupt):
                path.write_bytes(corrupt)
                view = self.payload(False)["loops"]
                self.assertEqual(view["state"], "invalid")
                self.assertTrue(view["runtime_found"])
                self.assertTrue(view["message"])
                self.assertEqual(view["units"], [])

    def test_rework_keeps_the_review_at_its_original_gate(self):
        import bootstrap_aggregate
        import loop_workflow as workflow

        workflow.start(self.root, unit_id="correct-parser", tier="middle", gate="G7",
                       goal="Correct parser results", acceptance="The client parses quoted paths.")
        self.record_review("correct-parser", "G7", "NEEDS_CHANGE")
        review = workflow._payload(workflow.runtime_path(self.root))["flow_units"][0]["gate_history"][-1]
        view = self.payload(False)["loops"]
        result = view["units"][0]
        self.assertEqual((result["gate_id"], result["gate_status"]), ("G6", "pending"))
        self.assertEqual(result["last_review"], review)
        self.assertIn("Rework", result["next_action"])
        text = bootstrap_aggregate.format_text({"loops": view})
        self.assertIn("return to middle G7", text)
        self.assertIn(f"last review G7 R{review['iteration']} NEEDS_CHANGE", text)
        self.assertIn(review["evidence_ref"], text)

    def test_section_readers_preserve_delimiters_in_runtime_independent_records(self):
        import governance_readers as readers
        rows = readers.gate_status(PLAN)
        self.assertEqual([row["transition"] for row in rows], TRANSITIONS)

    def test_native_parent_waits_only_at_a_gate_that_consumes_children(self):
        import loop_workflow as workflow
        for gate in ("G5", "G7"):
            workflow.start(self.root, unit_id=gate, tier="middle", gate=gate,
                           goal="Publish " + gate, acceptance="The installed tool works.")
            workflow.start(self.root, unit_id="child-" + gate, tier="inner", parent=gate,
                           goal="Exercise the installed tool", acceptance="Output matches the request.")
        units = {u["flow_unit_id"]: u for u in self.payload(False)["loops"]["units"]}
        self.assertIn("child-G7", units["G7"]["next_action"])
        self.assertIn("Wait", units["G7"]["next_action"])
        self.assertNotIn("Wait", units["G5"]["next_action"])
        self.assertEqual(units["G5"]["open_children"], ["child-G5"])

    def test_bound_receipt_and_previous_iteration_remain_distinguishable(self):
        import bootstrap_aggregate as bootstrap
        import governance_readers as readers
        import loop_workflow as workflow
        from checks import loop_receipts

        workflow.start(self.root, unit_id="feedback", tier="outer", gate="G11",
                       goal="Act on observed feedback", acceptance="A reviewer checks the outcome.")
        self.record_review("feedback", "G11", "APPROVED")
        workflow.start(self.root, unit_id="external", tier="inner",
                       goal="Check integration", acceptance="Two components agree.")
        workflow.start(self.root, unit_id="next", tier="outer", goal=None,
                       after="feedback", dependencies=["external"])
        with patch.object(loop_receipts, "verify_attempt", wraps=loop_receipts.verify_attempt) as checked:
            view = readers.loop_state(self.root)
        self.assertEqual(checked.call_count, 1)
        self.assertEqual(view["state"], "ready", view)
        self.assertEqual(view, self.payload(False)["loops"])
        next_unit = next(u for u in view["units"] if u["flow_unit_id"] == "next")
        self.assertEqual(next_unit["previous_unit_id"], "feedback")
        self.assertEqual(next_unit["dependencies"], ["external", "feedback"])
        prior = next_unit["previous_review"]
        self.assertEqual((prior["gate"], prior["result"]), ("G11", "APPROVED"))
        self.assertIn("previous unit feedback: G11", bootstrap.format_text({"loops": view}))
        self.assertIn(prior["evidence_ref"], bootstrap.format_text({"loops": view}))

    def test_receipt_tampering_or_loss_preserves_the_original_and_healthy_siblings(self):
        import bootstrap_aggregate as bootstrap
        import governance_readers as readers
        import loop_workflow as workflow
        for key, depends in (("fix", []), ("integration", ["fix"]), ("unrelated", [])):
            workflow.start(self.root, unit_id=key, tier="inner", goal=key, acceptance="Output says ready.",
                           dependencies=depends, check_command=[sys.executable, "-c", "print('ready')"],
                           expect_output="ready")
            workflow.verify_command(self.root, key)
        clean = readers.loop_state(self.root)
        self.assertEqual(clean["state"], "ready")
        ref = next(u for u in clean["units"] if u["flow_unit_id"] == "fix")["last_review"]["evidence_ref"]
        path = self.facts / ref
        source = workflow.runtime_path(self.root)
        frozen = source.read_bytes()
        for bad in (b"changed", None):
            with self.subTest(value=bad):
                if bad is None:
                    path.unlink()
                else:
                    path.write_bytes(bad)
                view = self.payload(False)["loops"]
                self.assertEqual("invalid", view["state"])
                by_id = {u["flow_unit_id"]: u for u in view["units"]}
                for key in ("fix", "integration"):
                    self.assertEqual(by_id[key]["runtime_status"], "unverified")
                    self.assertEqual(by_id[key]["recorded_runtime_status"], "completed")
                    self.assertIn(ref, by_id[key]["next_action"])
                self.assertEqual(by_id["unrelated"]["runtime_status"], "completed")
                self.assertIn(ref, bootstrap.format_text({"loops": view}))
                self.assertEqual(source.read_bytes(), frozen)
                if bad is None:
                    self.assertFalse(path.exists())
                else:
                    self.assertEqual(path.read_bytes(), bad)

    def test_active_unit_without_a_receipt_cannot_display_a_pass(self):
        import loop_workflow as workflow
        workflow.start(self.root, unit_id="fix", tier="inner", goal="Repair restart",
                       acceptance="The application resumes saved work.")
        path = workflow.runtime_path(self.root)
        state = json.loads(path.read_bytes())
        state["flow_units"][0]["gate_state"]["status"] = "passed"
        original = json.dumps(state).encode()
        path.write_bytes(original)
        loops = self.payload(False)["loops"]
        self.assertEqual(loops["state"], "invalid")
        self.assertIn("fix", loops["message"])
        self.assertEqual(loops["units"], [])
        self.assertEqual(path.read_bytes(), original)

    def test_historical_runtime_cannot_authorize_active_or_completed_work(self):
        import bootstrap_aggregate
        import loop_engine
        from tests.test_flow_unit_runtime_v2 import _valid_payload

        source = _valid_payload()
        path = self.facts / "flow-unit-runtime.json"
        for origin in (None, "history"):
            for status in ("active", "completed"):
                with self.subTest(origin=origin, status=status):
                    if origin is not None:
                        source["origin"] = origin
                    unit = source["flow_units"][0]
                    unit["runtime_status"] = status
                    unit["loop_state"]["active_loop"] = status != "completed"
                    unit["gate_state"]["status"] = "passed"
                    unit["gate_history"] = []
                    raw = json.dumps(source).encode()
                    path.write_bytes(raw)
                    view = self.payload(False)["loops"]
                    self.assertEqual(view, loop_engine.rollup_loop_state(str(self.root)))
                    self.assertEqual(view["state"], "invalid")
                    self.assertTrue(view["runtime_found"])
                    self.assertEqual(view["units"], [])
                    self.assertIn("origin", view["message"])
                    self.assertNotIn("Work unit complete", "\n".join(bootstrap_aggregate.format_loop_lines(view)))
                    self.assertEqual(raw, path.read_bytes())

    def test_bootstrap_keeps_its_projection_and_legacy_formatting(self):
        with patch.object(sys, "path", [str(INFRA), *sys.path]):
            import bootstrap_aggregate as bootstrap
            plan = PLAN.replace("## 项目配置", "## 项目配置（概要）")
            plan = plan.replace("fixture\n", "fixture   \n")
            plan = plan.replace("| demo |", "  | demo |")
            self.assertEqual(bootstrap.parse_project_config(plan)["工作流版本"], "fixture")
            self.assertEqual(bootstrap.parse_overview_row(plan)["project"], "demo")

    def test_missing_facts(self):
        (self.facts / "evidence-log.md").unlink()
        (self.facts / "risk-log.md").unlink()
        for degraded in (False, True):
            payload = self.payload(degraded)
            self.assertEqual(payload["evidence_count"], 0)
            self.assertEqual(payload["recent_evidence"], [])
            self.assertEqual(payload["open_risks"], [])
        self.plan.unlink()
        for degraded in (False, True):
            payload = self.payload(degraded)
            self.assertNotIn("error", payload)
            self.assertEqual(payload["loops"]["state"], "empty")
            self.assertNotIn("gates", payload)

    def test_new_project_title_used_before_any_unit_is_registered(self):
        import bootstrap_aggregate as boot
        import resolve_entry
        import time
        for config, expected in [("", "Shipping project"), ("- **项目名称**: Explicit", "Explicit")]:
            self.plan.write_text("# Shipping project\n\n## 项目配置\n" + config, encoding="utf-8")
            payload = boot._build_payload(self.root, resolve_entry.resolve(self.root), 3000, "lite", time.monotonic())
            self.assertEqual(payload["project"]["name"], expected)
            self.assertEqual(self.payload(False)["project_name"], expected)
            self.assertEqual(payload["loops"]["state"], "empty")

    def test_lost_state_with_a_live_journal_cannot_be_treated_as_a_new_project(self):
        import loop_workflow as workflow
        workflow.start(self.root, tier="inner", unit_id="repair", goal="Recover drafts",
                       acceptance="Restarting restores the last saved title.")
        path = workflow.runtime_path(self.root)
        log = path.with_name("loop-event-log.jsonl")
        recorded = log.read_bytes()
        path.unlink()
        view = self.payload(False)["loops"]
        self.assertEqual((view["state"], view["units"]), ("invalid", []))
        self.assertIn("restore the state", view["message"])
        with self.assertRaisesRegex(ValueError, "restore the state"):
            workflow.start(self.root, tier="inner", unit_id="new", goal="Start again", acceptance="A new unit is readable.")
        self.assertFalse(path.exists())
        self.assertEqual(log.read_bytes(), recorded)
