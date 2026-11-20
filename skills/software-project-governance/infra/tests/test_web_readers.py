"""Exercise /api/governance against the same host with and without the CLI engine."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch

INFRA = Path(__file__).resolve().parents[1]
ROOT = INFRA.parents[2]

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
RISK = '| RISK-1 | date | `a|b` | x | x | x | x | x | 打开 | owner | deadline |'


def load_server(degraded):
    spec = spec_from_file_location("spg_web_fixture", ROOT / "web" / "server.py")
    module = module_from_spec(spec)
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, "path", list(sys.path)))
        if degraded:
            stack.enter_context(patch.dict(sys.modules, {"verify_workflow": None}))
        spec.loader.exec_module(module)
    return module


def request_payload(server):
    """Exercise the actual HTTP request dispatcher and JSON serializer without a socket."""
    handler = server.Handler.__new__(server.Handler)
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
        server.ROOT = self.root
        # The CLI wrapper reads the host's rebound plan, while the repo-only
        # dashboard in fallback reads its own checkout's plan.
        with ExitStack() as stack:
            if not degraded:
                stack.enter_context(patch.object(server._vw, "SAMPLE_PATH", self.plan))
            headers, payload = request_payload(server)
        self.assertIn(b"200 OK", headers)
        self.assertIn(b"application/json", headers)
        self.assertEqual(payload["import_ok"], not degraded)
        if degraded:
            self.assertIn("import_error", payload)
        else:
            self.assertNotIn("import_error", payload)
        return payload

    def check_gate_rows(self, rows):
        self.assertEqual([row["gate"] for row in rows], [f"G{i}" for i in range(1, 7)])
        self.assertEqual([row["transition"] for row in rows], TRANSITIONS)
        self.assertTrue(all(row["status"] == "passed" and row["evidence"] == "EVD-1" for row in rows))

    def test_cli_gate_rows(self):
        server = load_server(False)
        with patch.object(server._vw, "SAMPLE_PATH", self.plan):
            self.check_gate_rows(server._vw.parse_gate_status())

    def test_facts_agree_when_engine_import_fails(self):
        normal = self.payload(False)
        degraded = self.payload(True)
        for payload in (normal, degraded):
            self.assertNotIn("error", payload)
            self.assertEqual(payload["workflow_version"], "fixture")
            self.assertEqual(payload["overview"]["project"], "demo")
            self.check_gate_rows(payload["gates"])
            self.assertEqual(payload["evidence_count"], 2)
            self.assertEqual([row["category"] for row in payload["recent_evidence"]],
                             ["`read|write`", '{"field":"a|b"}'])
            self.assertEqual(payload["open_risks"], [
                {"id": "RISK-1", "description": "`a|b`", "status": "打开", "deadline": "deadline"}])
        for key in ("overview", "gates", "recent_evidence", "open_risks"):
            self.assertEqual(normal[key], degraded[key])
        self.assertEqual(degraded["context"]["status"], "NOT_FOUND")
        self.assertIn("unavailable", degraded["context"]["next_action"])

    def test_missing_read_module_is_reported_without_fabricating_facts(self):
        with patch.dict(sys.modules, {"governance_readers": None}):
            server = load_server(False)
        headers, payload = request_payload(server)
        self.assertIn(b"200 OK", headers)
        self.assertFalse(payload["import_ok"])
        self.assertIn("governance_readers", payload["import_error"])
        self.assertIn("readers unavailable", payload["error"])
        self.assertNotIn("evidence_count", payload)

    def test_bootstrap_keeps_its_projection_and_legacy_formatting(self):
        with patch.object(sys, "path", [str(INFRA), *sys.path]):
            import bootstrap_aggregate as bootstrap
            plan = PLAN.replace("## 项目配置", "## 项目配置（概要）")
            plan = plan.replace("fixture\n", "fixture   \n")
            plan = plan.replace("| demo |", "  | demo |")
            self.assertEqual(bootstrap.parse_project_config(plan)["工作流版本"], "fixture")
            self.assertEqual(bootstrap.parse_overview_row(plan)["project"], "demo")
            self.assertEqual(bootstrap.parse_gate_summary(plan)["passed"], len(TRANSITIONS))

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
            self.assertIn("governance file missing", payload["error"])
            self.assertNotIn("gates", payload)
