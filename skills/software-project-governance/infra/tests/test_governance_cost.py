"""Unit tests for governance_cost.py — FEAT-032 (AUDIT-154 slice A-1).

Governance cost observability: TTFA (user message -> first
ask_user_question), time-to-substantive-work (first ask -> first
non-governance tool call or turn end), governance token breakdown
(in / cache_read / out), tool duration distribution, LLM vs tool time
shares. Fixtures are small SYNTHETIC zstd-compressed session traces built
in temporary directories — real user session data is never read here.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_governance_cost.py" -v
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import governance_cost as gc  # noqa: E402

try:
    import zstandard
except ImportError:  # pragma: no cover - environment without zstandard
    zstandard = None

SESSION_REL = "ws-fixture" + os.sep + "sess-1" + os.sep + "session.v3.jsonl.zstd"


def _require_zstandard(testcase):
    if zstandard is None:
        testcase.skipTest("zstandard not installed — cannot build zstd fixtures")


def _write_session(root, rel, events, extra_lines=()):
    """Compress a synthetic event stream into <root>/<rel> (JSONL in zstd).

    Lines are written COMPACT (separators without spaces) to match the
    harness serializer byte-for-byte — the fast scanner's envelope markers
    (`"type":"` etc.) only match compact JSON, so tests must exercise that
    shape or they silently fall back to full parsing and verify nothing.
    """
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
             for ev in events]
    lines.extend(extra_lines)
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    blob = zstandard.ZstdCompressor().compress(payload)
    path.write_bytes(blob)
    return path


def _ev(etype, time_ms, **data):
    return {"type": etype, "time": time_ms, "data": data}


def _user_msg(time_ms, text, **extra):
    return _ev("user/message", time_ms,
               content=[{"type": "text", "text": text}], **extra)


def _assistant_msg(time_ms, in_tok=0, cache_tok=0, out_tok=0, **extra):
    # Harness serialization order: data.turn first, then usage, then the
    # message payload — the fast scanner relies on envelope fields preceding
    # content.
    data = {}
    turn = extra.pop("turn", None)
    if turn is not None:
        data["turn"] = turn
    data["usage"] = {"inputTokens": in_tok, "cacheReadTokens": cache_tok,
                     "outputTokens": out_tok}
    data["message"] = extra.pop("message", None) or {
        "content": [{"type": "text", "text": "ok"}]}
    data.update(extra)
    return {"type": "assistant/message", "time": time_ms, "data": data}


def _tool_call(time_ms, call_id, name, turn=None, arguments="{}"):
    # Harness order: data.turn first, then callId, then name, then arguments.
    data = {}
    if turn is not None:
        data["turn"] = turn
    data["callId"] = call_id
    data["name"] = name
    data["arguments"] = arguments
    return _ev("tool/call", time_ms, **data)


def _tool_result(time_ms, call_id, turn=None):
    data = {"message": {"source": {"callId": call_id}, "content": []}}
    if turn is not None:
        data["turn"] = turn
    return _ev("tool/result", time_ms, **data)


def _minimal_session(events):
    """A session header + the given in-turn events (turn 1)."""
    return ([_ev("session", 1000, cwd="D:/proj/ws-fixture")]
            + [_ev("turn/start", 1001, turn=1)] + events)


def _run_cmd(argv):
    """Invoke cmd_governance_cost_report with a parsed-style namespace."""
    ns = gc._build_arg_parser().parse_args(argv)
    out = io.StringIO()
    err = io.StringIO()
    code = 0
    try:
        with redirect_stdout(out):
            gc.cmd_governance_cost_report(ns)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TestTurnAttribution(unittest.TestCase):
    """user/message has no turn field — attribution follows event order."""

    def setUp(self):
        _require_zstandard(self)

    def test_user_message_attributed_to_current_turn(self):
        events = _minimal_session([
            _user_msg(1100, "hello"),
            _assistant_msg(1200, in_tok=10, out_tok=5),
            _ev("turn/end", 1300, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["scan"]["files_parsed"], 1)
        self.assertEqual(len(report["sessions"][0]["turns"]), 1)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["turn"], 1)

    def test_first_user_message_is_ttfa_origin(self):
        # Two user messages in the turn; TTFA must measure from the FIRST.
        events = _minimal_session([
            _user_msg(1100, "first"),
            _user_msg(1500, "second"),
            _tool_call(2000, "c1", "ask_user_question", turn=1),
            _tool_result(3000, "c1", turn=1),
            _ev("turn/end", 3100, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["ttfa_ms"], 900)

    def test_user_message_before_first_turn_is_orphan(self):
        events = [
            _ev("session", 1000, cwd="D:/proj/ws-fixture"),
            _user_msg(1050, "pre-turn stray"),
            _ev("turn/start", 1100, turn=1),
            _user_msg(1150, "in turn"),
            _ev("turn/end", 1200, turn=1),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["scan"]["user_messages_before_first_turn"], 1)
        self.assertEqual(len(report["sessions"][0]["turns"]), 1)
        self.assertEqual(report["sessions"][0]["turns"][0]["turn"], 1)

    def test_attribution_switches_after_turn_end(self):
        events = [
            _ev("session", 1000, cwd="D:/proj/ws-fixture"),
            _ev("turn/start", 1100, turn=1),
            _user_msg(1150, "t1"),
            _ev("turn/end", 1200, turn=1),
            _ev("turn/start", 1300, turn=2),
            _user_msg(1350, "t2"),
            _assistant_msg(1400, out_tok=7),
            _ev("turn/end", 1500, turn=2),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turns = report["sessions"][0]["turns"]
        self.assertEqual([t["turn"] for t in turns], [1, 2])
        # The out_tok of turn 2's assistant message lands on turn 2 only.
        self.assertEqual(turns[0]["out_tok"], 0)
        self.assertEqual(turns[1]["out_tok"], 7)


class TestTTFA(unittest.TestCase):
    """TTFA = first ask_user_question tool/call - first user message."""

    def setUp(self):
        _require_zstandard(self)

    def test_ttfa_measured(self):
        events = _minimal_session([
            _user_msg(1100, "/governance"),
            _tool_call(2000, "a1", "read", turn=1),
            _tool_result(2100, "a1", turn=1),
            _tool_call(3000, "a2", "ask_user_question", turn=1),
            _tool_result(3500, "a2", turn=1),
            _ev("turn/end", 3600, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["ttfa_ms"], 1900)
        self.assertTrue(turn["is_governance_turn"])

    def test_turn_without_ask_has_null_ttfa(self):
        events = _minimal_session([
            _user_msg(1100, "plain work"),
            _tool_call(2000, "a1", "read", turn=1),
            _tool_result(2100, "a1", turn=1),
            _ev("turn/end", 2200, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertIsNone(turn["ttfa_ms"])
        self.assertFalse(turn["is_governance_turn"])

    def test_ttfa_totals_percentiles(self):
        # Two measured turns -> p50/p95 over [1000, 3000].
        events = [
            _ev("session", 1000, cwd="D:/proj/ws-fixture"),
            _ev("turn/start", 1100, turn=1),
            _user_msg(1200, "/governance"),
            _tool_call(2200, "a1", "ask_user_question", turn=1),
            _tool_result(2300, "a1", turn=1),
            _ev("turn/end", 2400, turn=1),
            _ev("turn/start", 2500, turn=2),
            _user_msg(2600, "/governance"),
            _tool_call(5600, "a2", "ask_user_question", turn=2),
            _tool_result(5700, "a2", turn=2),
            _ev("turn/end", 5800, turn=2),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        ttfa = report["totals"]["ttfa_ms"]
        self.assertEqual(ttfa["count"], 2)
        self.assertEqual(ttfa["p50"], 2000.0)
        self.assertEqual(ttfa["max"], 3000)


class TestTimeToWork(unittest.TestCase):
    """First ask -> first non-governance tool call, else turn end."""

    def setUp(self):
        _require_zstandard(self)

    def test_first_work_tool_after_ask(self):
        events = _minimal_session([
            _user_msg(1100, "/governance"),
            _tool_call(1500, "a1", "ask_user_question", turn=1),
            _tool_result(2500, "a1", turn=1),
            _tool_call(2600, "a2", "skill", turn=1),      # governance tool
            _tool_result(2700, "a2", turn=1),
            _tool_call(3000, "a3", "edit", turn=1),        # first work tool
            _tool_result(3200, "a3", turn=1),
            _ev("turn/end", 4000, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["time_to_work_ms"], 1500)
        self.assertEqual(turn["work_endpoint"], "first_work_tool")

    def test_falls_back_to_turn_end(self):
        events = _minimal_session([
            _user_msg(1100, "/governance"),
            _tool_call(1500, "a1", "ask_user_question", turn=1),
            _tool_result(2500, "a1", turn=1),
            _ev("turn/end", 4000, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["time_to_work_ms"], 2500)
        self.assertEqual(turn["work_endpoint"], "turn_end")

    def test_work_tool_before_ask_does_not_count(self):
        # A read before the ask must not satisfy the post-ask window.
        events = _minimal_session([
            _user_msg(1100, "/governance"),
            _tool_call(1200, "a0", "read", turn=1),
            _tool_result(1300, "a0", turn=1),
            _tool_call(1500, "a1", "ask_user_question", turn=1),
            _tool_result(2500, "a1", turn=1),
            _ev("turn/end", 3000, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["time_to_work_ms"], 1500)
        self.assertEqual(turn["work_endpoint"], "turn_end")

    def test_totals_endpoint_counts(self):
        report_events_first = _minimal_session([
            _user_msg(1100, "/governance"),
            _tool_call(1500, "a1", "ask_user_question", turn=1),
            _tool_result(2500, "a1", turn=1),
            _tool_call(2600, "a2", "pwsh", turn=1),
            _tool_result(2700, "a2", turn=1),
            _ev("turn/end", 4000, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, report_events_first)
            report = gc.scan_sessions(tmp)
        ttw = report["totals"]["time_to_work_ms"]
        self.assertEqual(ttw["count"], 1)
        self.assertEqual(ttw["endpoint_first_work_tool"], 1)
        self.assertEqual(ttw["endpoint_turn_end"], 0)


class TestTokenAggregation(unittest.TestCase):
    """usage{inputTokens,cacheReadTokens,outputTokens} summed per turn."""

    def setUp(self):
        _require_zstandard(self)

    def test_tokens_summed(self):
        events = _minimal_session([
            _user_msg(1100, "q"),
            _assistant_msg(1200, in_tok=100, cache_tok=900, out_tok=50),
            _assistant_msg(1300, in_tok=30, cache_tok=970, out_tok=20),
            _ev("turn/end", 1400, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["in_tok"], 130)
        self.assertEqual(turn["cache_tok"], 1870)
        self.assertEqual(turn["out_tok"], 70)
        self.assertEqual(report["totals"]["tokens"]["in"], 130)
        self.assertEqual(report["totals"]["tokens"]["cache_read"], 1870)
        self.assertEqual(report["totals"]["tokens"]["out"], 70)

    def test_usage_fallback_in_message_block(self):
        events = [_ev("session", 1000, cwd="D:/proj/ws-fixture"),
                  _ev("turn/start", 1100, turn=1),
                  _user_msg(1150, "q"),
                  _ev("assistant/message", 1200, turn=1,
                      message={"content": [], "usage":
                               {"inputTokens": 5, "cacheReadTokens": 6,
                                "outputTokens": 7}}),
                  _ev("turn/end", 1300, turn=1)]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual((turn["in_tok"], turn["cache_tok"], turn["out_tok"]),
                         (5, 6, 7))

    def test_null_usage_fields_count_as_zero(self):
        events = [_ev("session", 1000, cwd="D:/proj/ws-fixture"),
                  _ev("turn/start", 1100, turn=1),
                  _user_msg(1150, "q"),
                  _ev("assistant/message", 1200, turn=1,
                      usage={"inputTokens": None, "cacheReadTokens": None,
                             "outputTokens": 9}),
                  _ev("turn/end", 1300, turn=1)]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["totals"]["tokens"]["out"], 9)


class TestCorruptLineTolerance(unittest.TestCase):
    """Blank lines / corrupt JSON lines / empty files fail soft, counted."""

    def setUp(self):
        _require_zstandard(self)

    def test_corrupt_and_blank_lines_skipped(self):
        good = _minimal_session([
            _user_msg(1100, "q"),
            _ev("turn/end", 1200, turn=1),
        ])
        lines = [json.dumps(ev, ensure_ascii=False) for ev in good]
        extra = ("", "   ", "{not json", "[1, 2,", "null")
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, good, extra_lines=extra)
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["scan"]["files_parsed"], 1)
        # Blank lines are skipped silently; "{not json" and "[1, 2," fail
        # JSON parsing (counted); "null" parses and is ignored as non-dict.
        self.assertEqual(report["scan"]["corrupt_lines_skipped"], 2)

    def test_empty_file_is_counted_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty" / "session.v3.jsonl.zstd"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                zstandard.ZstdCompressor().compress(b"\n"))
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["scan"]["files_parsed"], 1)
        self.assertEqual(report["sessions"][0]["turns"], [])

    def test_failed_decompression_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad" / "session.v3.jsonl.zstd"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x00this is not zstd\x00")
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["scan"]["files_failed"], 1)
        self.assertEqual(report["scan"]["files_parsed"], 0)


class TestLLMAndToolTime(unittest.TestCase):
    """LLM window = step start -> first assistant message; tools paired."""

    def setUp(self):
        _require_zstandard(self)

    def test_llm_tool_and_residual(self):
        events = _minimal_session([
            _user_msg(1000, "q"),
            # step 1: LLM window 1100->2000 = 900; tool inside step 2000->2500
            _ev("step/start", 1100, turn=1),
            _assistant_msg(2000, in_tok=10, out_tok=10),
            _tool_call(2000, "t1", "pwsh", turn=1),
            _tool_result(2500, "t1", turn=1),
            _ev("step/end", 2600, turn=1),  # residual tail 100
            # step 2: pure answer, LLM window 2700->3400 = 700
            _ev("step/start", 2700, turn=1),
            _assistant_msg(3400, in_tok=10, out_tok=10),
            _ev("step/end", 3500, turn=1),
            _ev("turn/end", 3600, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["llm_ms"], 1600)
        self.assertEqual(turn["tool_ms"], 500)
        # turn/start arrives at 1001 in the fixture (before the user msg).
        self.assertEqual(turn["total_ms"], 2599)  # 1001 -> 3600
        self.assertEqual(turn["other_residual_ms"], 499)
        shares = report["totals"]["shares"]
        self.assertAlmostEqual(shares["llm_pct"],
                               round(1600 / 2599 * 100, 1))
        self.assertAlmostEqual(shares["tool_pct"],
                               round(500 / 2599 * 100, 1))

    def test_unpaired_tool_call_not_counted(self):
        events = _minimal_session([
            _user_msg(1000, "q"),
            _tool_call(1100, "orphan", "read", turn=1),
            _ev("turn/end", 2000, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual(turn["tool_ms"], 0)
        self.assertEqual(turn["unfinished_tool_calls"], 1)


class TestToolDistribution(unittest.TestCase):
    """Per-name aggregation: count / total / max, turn and global."""

    def setUp(self):
        _require_zstandard(self)

    def test_distribution_aggregated(self):
        events = _minimal_session([
            _user_msg(1000, "q"),
            _tool_call(1100, "t1", "read", turn=1),
            _tool_result(1200, "t1", turn=1),   # read 100
            _tool_call(1300, "t2", "read", turn=1),
            _tool_result(1500, "t2", turn=1),   # read 200
            _tool_call(1600, "t3", "pwsh", turn=1),
            _tool_result(2600, "t3", turn=1),   # pwsh 1000
            _ev("turn/end", 2700, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        tools = report["totals"]["tools"]
        self.assertEqual(tools["read"]["count"], 2)
        self.assertEqual(tools["read"]["total_ms"], 300)
        self.assertEqual(tools["read"]["max_ms"], 200)
        self.assertEqual(tools["pwsh"]["count"], 1)
        self.assertEqual(tools["pwsh"]["max_ms"], 1000)
        self.assertEqual(report["totals"]["time"]["ask_suspended_ms"], 0)

    def test_ask_suspension_measured(self):
        events = _minimal_session([
            _user_msg(1000, "q"),
            _tool_call(1100, "a1", "ask_user_question", turn=1),
            _tool_result(5000, "a1", turn=1),   # user waited 3900ms
            _ev("turn/end", 5100, turn=1),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        self.assertEqual(report["totals"]["time"]["ask_suspended_ms"], 3900)


class TestWorkspaceFilterAndDefaults(unittest.TestCase):
    """--workspace filters sessions; --sessions-root resolution rules."""

    def setUp(self):
        _require_zstandard(self)

    def _write_two_workspaces(self, tmp):
        _write_session(tmp, "alpha/s1/session.v3.jsonl.zstd",
                       _minimal_session([
                           _user_msg(1100, "a"),
                           _ev("turn/end", 1200, turn=1)]))
        _write_session(tmp, "beta/s2/session.v3.jsonl.zstd",
                       [_ev("session", 1000, cwd="D:/proj/beta"),
                        _ev("turn/start", 1100, turn=1),
                        _user_msg(1150, "b"),
                        _ev("turn/end", 1250, turn=1)])

    def test_workspace_filter_narrows_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_two_workspaces(tmp)
            report = gc.scan_sessions(tmp, workspace="ws-fixture")
            self.assertEqual(len(report["sessions"]), 1)
            self.assertEqual(report["sessions"][0]["cwd"], "D:/proj/ws-fixture")
            report_all = gc.scan_sessions(tmp)
            self.assertEqual(len(report_all["sessions"]), 2)

    def test_missing_root_and_env_is_fail_closed(self):
        ns = gc._build_arg_parser().parse_args(["--format", "json"])
        with unittest.mock.patch.dict(os.environ,
                                      {"DSH_SESSIONS_ROOT": ""},
                                      clear=False):
            os.environ.pop("DSH_SESSIONS_ROOT", None)
            with self.assertRaises(SystemExit) as ctx:
                gc.cmd_governance_cost_report(ns)
        self.assertEqual(ctx.exception.code, 2)

    def test_env_var_used_when_flag_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_two_workspaces(tmp)
            ns = gc._build_arg_parser().parse_args(["--format", "json"])
            with unittest.mock.patch.dict(os.environ,
                                          {"DSH_SESSIONS_ROOT": tmp}):
                out = io.StringIO()
                with redirect_stdout(out):
                    gc.cmd_governance_cost_report(ns)
            report = json.loads(out.getvalue())
            self.assertEqual(report["scan"]["files_found"], 2)

    def test_nonexistent_root_fails_closed(self):
        ns = gc._build_arg_parser().parse_args(
            ["--sessions-root", "Z:/definitely/not/here"])
        with self.assertRaises(SystemExit) as ctx:
            gc.cmd_governance_cost_report(ns)
        self.assertEqual(ctx.exception.code, 2)


class TestCwdFallbackFromDirectoryName(unittest.TestCase):
    """FIX-356 — workspace filter must hit sessions whose session event
    carries no cwd (real dsh v3 corpus shape, EVD-1088: 344/344 files have
    ``data={}``).

    The only reliable workspace carrier is dsh's encoded ancestor
    directory name (``--<workspace-id>--`` wrapper, path separators
    normalized to ``-``). Fixtures here reproduce that REAL shape next to
    the legacy shape (session event with cwd), which must keep working
    unchanged. The fallback yields a match token only — never a
    reconstructed filesystem path.
    """

    WS_DIR = "--D-AI-agent-claude-coding-project_management_workflow--"
    WS_TOKEN = "D-AI-agent-claude-coding-project_management_workflow"
    OTHER_DIR = "--C-other-project--"

    def setUp(self):
        _require_zstandard(self)

    @staticmethod
    def _real_shape_events():
        # Session header with data={} — the real v3 corpus shape (no cwd).
        return [
            _ev("session", 1000),
            _ev("turn/start", 1100, turn=1),
            _user_msg(1150, "/governance"),
            _tool_call(3000, "a1", "ask_user_question", turn=1),
            _tool_result(3500, "a1", turn=1),
            _ev("turn/end", 3600, turn=1),
        ]

    def test_fallback_unwraps_the_encoded_ancestor(self):
        rel = Path(self.WS_DIR, "sess-abc", gc._SESSION_FILENAME)
        self.assertEqual(gc._cwd_fallback_from_session_path(rel), self.WS_TOKEN)

    def test_fallback_returns_empty_without_encoded_ancestor(self):
        rel = Path("plain-ws", "s1", gc._SESSION_FILENAME)
        self.assertEqual(gc._cwd_fallback_from_session_path(rel), "")
        bare = Path(gc._SESSION_FILENAME)
        self.assertEqual(gc._cwd_fallback_from_session_path(bare), "")

    def test_fallback_prefers_the_nearest_encoded_ancestor(self):
        rel = Path("--outer--", "mid", self.WS_DIR, "s", gc._SESSION_FILENAME)
        self.assertEqual(gc._cwd_fallback_from_session_path(rel), self.WS_TOKEN)

    def test_fallback_token_is_a_match_token_not_a_path(self):
        rel = Path(self.WS_DIR, "s", gc._SESSION_FILENAME)
        token = gc._cwd_fallback_from_session_path(rel)
        self.assertFalse(token.startswith("--"))
        self.assertFalse(token.endswith("--"))
        self.assertNotIn("/", token)
        self.assertNotIn("\\", token)
        self.assertNotIn(":", token)

    def test_real_shape_directory_encoding_hits_workspace_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(
                tmp,
                os.path.join(self.WS_DIR, "sess-real", gc._SESSION_FILENAME),
                self._real_shape_events())
            report = gc.scan_sessions(
                tmp, workspace="project_management_workflow")
            self.assertEqual(len(report["sessions"]), 1)
            self.assertEqual(report["sessions"][0]["cwd"], self.WS_TOKEN)
            report_all = gc.scan_sessions(tmp)
            self.assertEqual(len(report_all["sessions"]), 1)

    def test_other_workspace_directory_does_not_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(
                tmp, os.path.join(self.WS_DIR, "s1", gc._SESSION_FILENAME),
                self._real_shape_events())
            _write_session(
                tmp, os.path.join(self.OTHER_DIR, "s2", gc._SESSION_FILENAME),
                self._real_shape_events())
            # No cwd anywhere and no encoded ancestor — the fallback must
            # NOT over-match this one.
            _write_session(
                tmp, os.path.join("plain", "s3", gc._SESSION_FILENAME),
                self._real_shape_events())
            report = gc.scan_sessions(
                tmp, workspace="project_management_workflow")
            self.assertEqual([s["cwd"] for s in report["sessions"]],
                             [self.WS_TOKEN])
            report_all = gc.scan_sessions(tmp)
            self.assertEqual(len(report_all["sessions"]), 3)

    def test_legacy_cwd_shape_still_wins_and_matches(self):
        events = [_ev("session", 1000, cwd="D:/proj/ws-fixture"),
                  _ev("turn/start", 1100, turn=1),
                  _user_msg(1150, "legacy"),
                  _ev("turn/end", 1200, turn=1)]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(
                tmp, os.path.join(self.WS_DIR, "s1", gc._SESSION_FILENAME),
                events)
            # Event cwd wins over the directory-derived token (no override).
            report = gc.scan_sessions(tmp, workspace="ws-fixture")
            self.assertEqual(len(report["sessions"]), 1)
            self.assertEqual(report["sessions"][0]["cwd"], "D:/proj/ws-fixture")
            # And the directory token is NOT consulted when cwd is present.
            report_by_dir = gc.scan_sessions(
                tmp, workspace="project_management_workflow")
            self.assertEqual(len(report_by_dir["sessions"]), 0)


class TestZstandardFailClosed(unittest.TestCase):
    """Missing zstandard must produce a clear error, never silent data."""

    def test_scan_raises_clear_error_without_zstandard(self):
        original = gc._ZSTD_MODULE
        try:
            gc._ZSTD_MODULE = None  # simulate failed lazy import
            with self.assertRaises(gc.GovernanceCostError) as ctx:
                gc._decompress_bytes(b"\x00\x00")
            self.assertIn("zstandard", str(ctx.exception))
            self.assertIn("pip install", str(ctx.exception))
        finally:
            gc._ZSTD_MODULE = original

    def test_cmd_exits_nonzero_without_zstandard(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, _minimal_session([
                _user_msg(1100, "q"),
                _ev("turn/end", 1200, turn=1)]))
            ns = gc._build_arg_parser().parse_args(
                ["--sessions-root", tmp])
            original = gc._ZSTD_MODULE
            try:
                gc._ZSTD_MODULE = None  # simulate failed lazy import
                with self.assertRaises(SystemExit) as ctx:
                    gc.cmd_governance_cost_report(ns)
                self.assertEqual(ctx.exception.code, 1)
            finally:
                gc._ZSTD_MODULE = original


class TestCLIOutput(unittest.TestCase):
    """--format json|text wiring and report self-description."""

    def setUp(self):
        _require_zstandard(self)

    def test_json_output_has_schema_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, _minimal_session([
                _user_msg(1100, "/governance"),
                _tool_call(1500, "a1", "ask_user_question", turn=1),
                _tool_result(2500, "a1", turn=1),
                _ev("turn/end", 3000, turn=1)]))
            code, out, _ = _run_cmd(["--sessions-root", tmp,
                                     "--format", "json"])
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(report["schema"], gc.REPORT_SCHEMA)
        self.assertEqual(report["task"], "FEAT-032")
        self.assertIn("ttfa_ms", report["totals"])
        self.assertIn("time_to_work_ms", report["totals"])
        self.assertIn("tokens", report["totals"])
        self.assertIn("calibration", report)

    def test_text_output_is_human_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, _minimal_session([
                _user_msg(1100, "/governance"),
                _tool_call(1500, "a1", "ask_user_question", turn=1),
                _tool_result(2500, "a1", turn=1),
                _ev("turn/end", 3000, turn=1)]))
            code, out, _ = _run_cmd(["--sessions-root", tmp])
        self.assertEqual(code, 0)
        self.assertIn("Governance Cost Report", out)
        self.assertIn("TTFA", out)
        self.assertIn("time-to-work", out)

    def test_calibration_notes_disclose_overlap_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, _minimal_session([
                _user_msg(1100, "q"),
                _ev("turn/end", 1200, turn=1)]))
            code, out, _ = _run_cmd(["--sessions-root", tmp,
                                     "--format", "json"])
        report = json.loads(out)
        notes = " ".join(report["calibration"].values())
        # Audit §4 calibration: raw timestamps, cumulative tokens, residual.
        self.assertIn("cumulative", notes)
        self.assertIn("residual", notes)

    def test_calibration_discloses_sessions_cwd_dual_source(self):
        # FIX-360 contract pin: the calibration face must disclose the
        # sessions[].cwd dual-source semantics (event cwd wins; no-cwd
        # sessions carry a directory-derived filter token, not a path).
        self.assertIn("sessions_cwd", gc.CALIBRATION)
        self.assertIsInstance(gc.CALIBRATION["sessions_cwd"], str)
        self.assertTrue(gc.CALIBRATION["sessions_cwd"].strip())


class TestFastScannerEquivalence(unittest.TestCase):
    """Byte fast path ≡ full json.loads path (metrics identical)."""

    def setUp(self):
        _require_zstandard(self)

    def test_embedded_fake_usage_is_rejected(self):
        # Model text contains a usage-shaped lookalike whose arithmetic does
        # NOT close; the real usage object follows. Totals must reflect only
        # the real one. Turn comes first in data (harness order), so this
        # exercises the FAST path rejection, not the full-parse fallback.
        fake = '{"usage":{"inputTokens":1,"outputTokens":1,' \
               '"totalTokens":999999,"cacheReadTokens":1}}'
        events = [_ev("session", 1000, cwd="D:/proj/ws-fixture"),
                  _ev("turn/start", 1100, turn=1),
                  _user_msg(1150, "q"),
                  {"type": "assistant/message", "time": 1200,
                   "data": {"turn": 1,
                            "message": {"content": [
                                {"type": "text", "text": fake}]},
                            "usage": {"inputTokens": 50,
                                      "cacheReadTokens": 40,
                                      "outputTokens": 10,
                                      "totalTokens": 100}}},
                  _ev("turn/end", 1300, turn=1)]
        with tempfile.TemporaryDirectory() as tmp:
            _write_session(tmp, SESSION_REL, events)
            report = gc.scan_sessions(tmp)
        turn = report["sessions"][0]["turns"][0]
        self.assertEqual((turn["in_tok"], turn["cache_tok"], turn["out_tok"]),
                         (50, 40, 10))

    def test_fast_and_full_paths_agree(self):
        events = _minimal_session([
            _user_msg(1100, "/governance"),
            _ev("step/start", 1150, turn=1),
            _assistant_msg(1200, in_tok=100, cache_tok=900, out_tok=50,
                           turn=1),
            _tool_call(1300, "t1", "pwsh", turn=1),
            _tool_result(1500, "t1", turn=1),
            _ev("step/end", 1600, turn=1),
            _tool_call(1700, "a1", "ask_user_question", turn=1),
            _tool_result(2700, "a1", turn=1),
            _ev("turn/end", 2800, turn=1),
        ])
        # Compact separators — the harness serializer shape the fast
        # scanner's markers match; spaced JSON would silently take the
        # full-parse path and verify nothing.
        lines = [json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
                 .encode("utf-8") for ev in events]
        raw = b"\n".join(lines) + b"\n"
        fast_events, fast_corrupt = gc._events_from_bytes(raw)
        full_events, full_corrupt = gc._parse_jsonl_lines(
            raw.decode("utf-8"))
        self.assertEqual(fast_corrupt, full_corrupt)
        fast = gc.parse_session(fast_events)
        full = gc.parse_session(full_events)
        self.assertEqual(sorted(fast["turns"]), sorted(full["turns"]))
        for turn_id, rec in fast["turns"].items():
            other = full["turns"][turn_id]
            self.assertEqual(rec["in_tok"], other["in_tok"])
            self.assertEqual(rec["cache_tok"], other["cache_tok"])
            self.assertEqual(rec["out_tok"], other["out_tok"])
            self.assertEqual(rec["tool_ms"], other["tool_ms"])
            self.assertEqual(rec["llm_ms"], other["llm_ms"])
            self.assertEqual(rec["ask_suspended_ms"],
                             other["ask_suspended_ms"])
        fast_m = gc.turn_metrics(1, fast["turns"][1])
        full_m = gc.turn_metrics(1, full["turns"][1])
        for field in ("ttfa_ms", "time_to_work_ms", "work_endpoint",
                      "in_tok", "out_tok", "llm_ms", "tool_ms",
                      "ask_suspended_ms", "is_governance_turn"):
            self.assertEqual(fast_m[field], full_m[field], field)

    def test_usage_object_with_nested_braces_is_extracted(self):
        raw = json.dumps({
            "type": "assistant/message", "seq": 2, "time": 1200,
            "data": {"turn": 1, "step": 1,
                     "message": {"content": []},
                     "usage": {"inputTokens": 7, "outputTokens": 3,
                               "totalTokens": 10,
                               "nested": {"brace": "} inside"}},
                     "stream": []}},
            separators=(",", ":")).encode("utf-8")
        events, corrupt = gc._events_from_bytes(raw)
        self.assertEqual(corrupt, 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["data"]["usage"]["inputTokens"], 7)

    def test_unneeded_envelope_types_are_skipped_but_needed_are_not(self):
        # The skip branch must only swallow truly unneeded types — a needed
        # type (turn/start, user/message) reaching the skip branch would
        # silently zero TTFA (regression guard for the corpus incident).
        lines = [
            b'{"type":"request/header","time":1005,"data":{"big":1}}',
            b'{"type":"turn/start","time":1001,"data":{"turn":1}}',
            b'{"type":"user/message","time":1100,'
            b'"data":{"content":[{"type":"text","text":"hi"}]}}',
        ]
        events, corrupt = gc._events_from_bytes(b"\n".join(lines) + b"\n")
        self.assertEqual(corrupt, 0)
        types = sorted(e["type"] for e in events)
        self.assertEqual(types, ["turn/start", "user/message"])


class TestPercentile(unittest.TestCase):
    """Deterministic linear-interpolation percentiles."""

    def test_even_count(self):
        self.assertEqual(gc.percentile([10, 20, 30, 40], 0.50), 25.0)
        self.assertEqual(gc.percentile([10, 20, 30, 40], 0.95), 38.5)

    def test_single_value(self):
        self.assertEqual(gc.percentile([7], 0.5), 7)
        self.assertEqual(gc.percentile([7], 0.95), 7)

    def test_empty_is_none(self):
        self.assertIsNone(gc.percentile([], 0.5))


class Feat039ZstandardDependencyAssertionTests(unittest.TestCase):
    """FEAT-039 / DEC-205② (FEAT-032 P2-3 carry-over): dependency presence.

    FEAT-032's zstd fixtures are built by ``zstandard``. On a machine without
    it this module skipped wholesale — CI reported green while none of the
    §2/§3/§4 acceptance measurements had actually run. The carry-over
    acceptance is "tests must not silently skip": the dependency is either
    present (asserted here) or its absence is an explicit FAIL carrying the
    install command.

    Deliberately a hard assertion, not a conditional skip — FEAT-032 needs
    zstandard in dev and CI environments.
    """

    def test_zstandard_dependency_is_present(self):
        """Explicit FAIL (not skip) when zstandard is missing."""
        self.assertIsNotNone(
            zstandard,
            "zstandard is a required dev/CI dependency for FEAT-032 "
            "governance-cost fixtures — install it with "
            "`pip install zstandard`; a missing dependency must FAIL, never "
            "silently skip the measurements.")

    def test_skip_is_driven_only_by_the_import_probe(self):
        """Anti-silence guard: exactly ONE call site may skip, and its sole
        trigger must be the ``zstandard`` import probe — a second silent gate
        (env var / platform) would re-open the hole DEC-205② closed.

        The needle is the bare call (``skip`` + ``Test(``), not a one-form
        spelling — and the single call site must sit INSIDE
        ``_require_zstandard``, so a skip added elsewhere cannot hide behind
        the same count (review-FEAT-039 P3-5). These docstrings must not spell
        the needle out, or the guard would count itself.
        """
        import inspect
        source = inspect.getsource(sys.modules[__name__])
        self.assertIn("except ImportError", source)
        # built by concatenation so this assertion cannot count itself
        needle = "skip" + "Test" + "("
        self.assertEqual(source.count(needle), 1, "skip call sites")
        self.assertIn("if zstandard is None:", source)
        helper = source.split("def _require_zstandard(testcase):", 1)
        self.assertEqual(len(helper), 2, "_require_zstandard helper missing")
        body = helper[1].split("\ndef ", 1)[0]
        self.assertEqual(body.count(needle), 1,
                         "the only skip call site must be the dependency probe")

    def test_import_failure_message_names_the_install_command(self):
        """The fail-closed error path in governance_cost must name the fix —
        a bare 'zstandard missing' costs the reader a search."""
        source = (_HERE.parent / "governance_cost.py").read_text(
            encoding="utf-8")
        self.assertIn("pip install zstandard", source)
        self.assertIn("zstandard 未安装", source)


class Feat040TtfaAcceptanceTests(unittest.TestCase):
    """RISK-055 — the one-click re-verification path (FEAT-040).

    The acceptance itself runs in a LATER session (DEC-207①); what must hold
    here is the path: thresholds in code, the paired TTFA+TTW report, and an
    explicit PENDING verdict while the sample is too small. A face that
    borrows a green light from the unchanged baseline is worse than no face.
    """

    def _report(self, ttfa_values, ttw_values=None):
        ttw_values = ttw_values or [None] * len(ttfa_values)
        turns = [{"turn": index, "ttfa_ms": value,
                  "time_to_work_ms": ttw_values[index],
                  "work_endpoint": ("first_work_tool" if ttw_values[index]
                                    else "none"),
                  "is_governance_turn": index == 0}
                 for index, value in enumerate(ttfa_values)]
        return {"sessions": [{"file": "s/session.v3.jsonl.zstd", "cwd": "/w",
                              "turns": turns}]}

    def test_thresholds_are_code_not_prose(self):
        self.assertEqual(gc.TTFA_ACCEPTANCE_P50_MS, 25000)
        self.assertEqual(gc.TTFA_ACCEPTANCE_P95_MS, 45000)
        self.assertEqual(gc.TTFA_ACCEPTANCE_TASK, "RISK-055")
        self.assertEqual(gc.TTFA_ACCEPTANCE_MIN_TURNS, 3)

    def test_small_sample_is_pending_not_pass(self):
        result = gc.ttfa_acceptance(self._report([1000, 2000]))
        self.assertEqual(result["verdict"], "PENDING")
        self.assertIn("sample too small", result["reason"])
        self.assertEqual(result["samples"]["turns_with_ttfa"], 2)

    def test_empty_scan_is_pending(self):
        result = gc.ttfa_acceptance({"sessions": []})
        self.assertEqual(result["verdict"], "PENDING")

    def test_pass_verdict(self):
        result = gc.ttfa_acceptance(self._report([1000, 2000, 3000]))
        self.assertEqual(result["verdict"], "PASS", result["reason"])
        self.assertEqual(result["ttfa_ms"]["p50"], 2000)

    def test_fail_verdict_names_the_breached_bound(self):
        result = gc.ttfa_acceptance(self._report([30000, 40000, 50000]))
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("p50", result["reason"])
        self.assertIn("p95", result["reason"])

    def test_ttw_is_paired_per_turn(self):
        result = gc.ttfa_acceptance(
            self._report([1000, 2000, 3000], [4000, None, 6000]))
        self.assertEqual(result["samples"]["turns_with_ttfa"], 3)
        self.assertEqual(result["time_to_work_ms"]["count"], 2)
        rows = {row["ttfa_ms"]: row for row in result["paired_rows"]}
        self.assertEqual(rows[1000]["time_to_work_ms"], 4000)
        self.assertIsNone(rows[2000]["time_to_work_ms"])
        self.assertEqual(rows[3000]["time_to_work_ms"], 6000)

    def test_rows_are_ranked_worst_first_and_capped(self):
        result = gc.ttfa_acceptance(
            self._report(list(range(1, gc.TTFA_ACCEPTANCE_ROW_LIMIT + 6))))
        self.assertEqual(len(result["paired_rows"]),
                         gc.TTFA_ACCEPTANCE_ROW_LIMIT)
        self.assertGreater(result["paired_rows_truncated"], 0)
        self.assertGreater(result["paired_rows"][0]["ttfa_ms"],
                           result["paired_rows"][-1]["ttfa_ms"])

    def test_scope_declares_baseline_comparability(self):
        """The caliber must be stated, or the number is not comparable."""
        result = gc.ttfa_acceptance(self._report([1, 2, 3]))
        self.assertIn("totals.ttfa_ms", result["scope"])
        self.assertIn("DEC-207", result["source"])

    def test_text_rendering_carries_the_verdict_and_pairs(self):
        result = gc.ttfa_acceptance(
            self._report([1000, 2000, 3000], [500, None, 700]))
        text = gc.format_ttfa_acceptance(result)
        self.assertIn("RISK-055", text)
        self.assertIn("verdict: PASS", text)
        self.assertIn("TTW", text)
        self.assertIn("paired rows", text)

    def test_cli_flag_reaches_the_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_session(root, "a", _minimal_session([
                _user_msg(0, "/governance 状态"),
                _tool_call(5000, "c1", "ask_user_question"),
                _tool_result(6000, "c1"),
            ]))
            code, out, _err = _run_cmd(["--sessions-root", str(root),
                                        "--ttfa-acceptance",
                                        "--format", "json"])
        self.assertEqual(code, 0, out)
        payload = json.loads(out)
        self.assertIn("ttfa_acceptance", payload)
        self.assertIn(payload["ttfa_acceptance"]["verdict"],
                      ("PASS", "FAIL", "PENDING"))

    def test_cli_flag_absent_keeps_the_report_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_session(root, "a", _minimal_session([
                _user_msg(0, "/governance 状态"),
                _tool_call(5000, "c1", "ask_user_question"),
                _tool_result(6000, "c1"),
            ]))
            code, out, _err = _run_cmd(["--sessions-root", str(root),
                                        "--format", "json"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("ttfa_acceptance", json.loads(out))


if __name__ == "__main__":
    unittest.main()
