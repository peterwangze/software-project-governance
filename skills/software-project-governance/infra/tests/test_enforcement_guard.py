"""FEAT-099 — host-level enforcement guard tests (S1/S2/S3 judgment faces).

Covers the FEAT-099 implementation slice (design §6, docs/architecture/
feat-099-dsh-host-enforcement-poc-design.md R1+):

  * S1①  the strategy projection carries the reason/remedy templates
         (`_strategy_public()` extension, review D2 ruling (b));
  * S1②  the JS×Python decision parity over a fact grid, and the
         byte-assertion keeping the shipped fixture identical to
         `--print-strategy` stdout (review D8);
  * S2    the governance-state cache invalidation rules (stat fingerprint,
         TTL, switch sensitivity, root change, Windows mtime tolerance);
  * S3    the host-row wiring (registration, capability-miss degradation,
         off zero-registration, V8 timestamp anchor).

Node availability gates the JS-driven tests with skipTest, mirroring the
test_dsh_adapter.py precedent ("node unavailable ... cannot be exercised").
The Python judgment face (enforcement.py decide()) is exercised directly for
the parity grid.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_INFRA = _REPO_ROOT / "skills" / "software-project-governance" / "infra"
_GUARD_JS = _REPO_ROOT / "lib" / "dsh-native" / "guard.js"
_FIXTURE = _REPO_ROOT / "lib" / "dsh-native" / "strategy-projection.json"

sys.path.insert(0, str(_INFRA))

import enforcement as enf  # noqa: E402
import verify_workflow as vw  # noqa: E402


def _node_bin():
    return shutil.which("node")


def _guard_url():
    return _GUARD_JS.resolve().as_uri()


def _run_node(body, payload=None, workdir=None):
    """Run one ESM script importing guard.js; return parsed stdout JSON."""
    node = _node_bin()
    if not node:
        raise unittest.SkipTest("node unavailable (governance guard JS cannot be exercised)")
    script = (
        "import { readFileSync } from 'node:fs';\n"
        f"import * as guard from '{_guard_url()}';\n"
        + (f"const INPUT = {json.dumps(payload)};\n" if payload is not None else "")
        + body
        + "\n"
    )
    proc = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(workdir or _REPO_ROOT), timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(f"node driver failed ({proc.returncode}):\n{proc.stderr}")
    return json.loads(proc.stdout)


def _anchor_line(task, rev, channel="normal", actor="Developer"):
    return f"[governance-dispatch task={task} rev={rev} channel={channel} actor={actor}]"


# ── S1① strategy projection shape ───────────────────────────────────────────

class StrategyProjectionShapeTests(unittest.TestCase):
    def test_projection_carries_reason_remedy_templates(self):
        table = enf._strategy_public()
        rules = table["hard_block_rules"]
        self.assertIsInstance(rules, list)
        self.assertEqual(
            sorted(rule["id"] for rule in rules),
            sorted(enf.HARD_BLOCK_RULES),
        )
        for rule in rules:
            self.assertIn("reason", rule)
            self.assertIn("remedy", rule)
            self.assertTrue(rule["reason"].strip(), rule["id"])
            self.assertTrue(rule["remedy"].strip(), rule["id"])
        source = {r["id"]: r for r in enf.STRATEGY["hard_block_rules"]}
        for rule in rules:
            self.assertEqual(rule["reason"], source[rule["id"]]["reason"])
            self.assertEqual(rule["remedy"], source[rule["id"]]["remedy"])

    def test_fixture_bytes_equal_print_strategy_stdout(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with contextlib.redirect_stderr(io.StringIO()):
                rc = vw.main(["enforcement-check", "--print-strategy"])
        self.assertEqual(rc, 0)
        expected = buf.getvalue().encode("utf-8")
        actual = _FIXTURE.read_bytes()
        self.assertEqual(
            actual, expected,
            "strategy-projection.json must be byte-identical to "
            "`enforcement-check --print-strategy` stdout (FEAT-099 D8 byte "
            "assertion); regenerate it via the python in-process writer",
        )


# ── S1② JS×Python decision parity ───────────────────────────────────────────

class GuardParityTests(unittest.TestCase):
    """Same facts, both judgment faces: decision / reason_code / templates.

    Python decides facts {boundary, action{task_id, revision, channel,
    actor}, state{expected_revision}}; the JS guard decides the anchored
    subagent execution against the same expected map with the same single
    source templates. The anchored cases must agree on decision, code, bare
    reason text and remedy, byte for byte.
    """

    CASES = [
        # (task, revision, expected_map, channel)
        ("POC-1", 1, {"POC-1": 2}, "normal"),
        ("POC-1", 2, {"POC-1": 2}, "normal"),
        ("POC-1", 3, {"POC-1": 2}, "fix"),
        ("OTHER", 1, {"POC-1": 2}, "normal"),
        ("POC-1", 1, {}, "normal"),
        ("POC-1", 2, {"POC-1": 2, "X-9": 7}, "re-review"),
    ]

    def test_js_python_parity_over_fact_grid(self):
        py_results = []
        for task, revision, expected, channel in self.CASES:
            facts = {
                "boundary": "dispatch-execute",
                "action": {
                    "task_id": task, "revision": revision,
                    "channel": channel, "actor": "Developer",
                },
                "state": {"expected_revision": dict(expected)},
            }
            py_results.append(enf.decide(facts))
        payload = [
            {
                "name": "subagent",
                "arguments": {"prompt": _anchor_line(task, revision, channel) + "\nbody"},
                "world": {
                    "switchState": "on", "located": True,
                    "expectedRevision": expected, "projectionFault": None,
                },
            }
            for task, revision, expected, channel in self.CASES
        ]
        js_results = _run_node(
            "const strategy = guard.loadStrategyProjection();\n"
            "const out = INPUT.map((c) => guard.decideGuard(c, { ...c.world, strategy }));\n"
            "console.log(JSON.stringify(out));",
            payload=payload,
        )
        self.assertEqual(len(js_results), len(self.CASES))
        for (task, revision, _, _), py, js in zip(self.CASES, py_results, js_results):
            context = f"task={task} revision={revision}"
            py_decision = py["decision"]
            js_decision = "HARD_BLOCK" if js["decision"] == "deny" else "ALLOW"
            self.assertEqual(js_decision, py_decision, context)
            if py_decision == "HARD_BLOCK":
                self.assertEqual(js["reasonCode"], py["reason_code"], context)
                # Bare template text and remedy must agree byte for byte —
                # both faces format the SAME single-source templates.
                self.assertEqual(js["detail"], py["reason"], context)
                self.assertEqual(js["remedy"], py["remedy"], context)
            else:
                self.assertNotIn("reason", js, context)

    def test_subagent_fork_face_parity(self):
        payload = {
            "name": "subagent_fork",
            "arguments": {"prompt": _anchor_line("POC-1", 1) + "\nbody"},
            "world": {
                "switchState": "on", "located": True,
                "expectedRevision": {"POC-1": 2}, "projectionFault": None,
            },
        }
        js = _run_node(
            "const strategy = guard.loadStrategyProjection();\n"
            "console.log(JSON.stringify(guard.decideGuard(INPUT, { ...INPUT.world, strategy })));",
            payload=payload,
        )
        self.assertEqual(js["decision"], "deny")
        self.assertEqual(js["reasonCode"], "revision-mismatch")


# ── anchor parsing + behavior spec C0-C7 (JS face) ──────────────────────────

class AnchorAndBehaviorTests(unittest.TestCase):
    def _decide(self, execution, world):
        return _run_node(
            "const strategy = guard.loadStrategyProjection();\n"
            "console.log(JSON.stringify(guard.decideGuard(INPUT.execution, "
            "{ ...INPUT.world, strategy })));",
            payload={"execution": execution, "world": world},
        )

    def _world(self, **over):
        world = {
            "switchState": "on", "located": True,
            "expectedRevision": {"POC-1": 2}, "projectionFault": None,
        }
        world.update(over)
        return world

    def test_anchor_parse_variants(self):
        out = _run_node(
            "const lines = [\n"
            f"  {json.dumps(_anchor_line('POC-1', 2))},\n"
            "  '[governance-dispatch task=POC-1 rev=abc channel=normal actor=D]',\n"
            "  '[governance-dispatch task=POC-1 rev=1 channel=urgent actor=D]',\n"
            "  '[governance-dispatch task=POC-1 rev=-4 channel=fix actor=D]',\n"
            "  'plain prompt first line',\n"
            "  '',\n"
            "];\n"
            "console.log(JSON.stringify(lines.map((l) => guard.parseDispatchAnchor(l))));",
        )
        self.assertEqual(out[0], {"kind": "ok", "task": "POC-1", "rev": 2,
                                  "channel": "normal", "actor": "Developer"})
        self.assertEqual(out[1]["kind"], "invalid")
        self.assertEqual(out[2]["kind"], "invalid")
        self.assertEqual(out[3]["kind"], "ok")
        self.assertEqual(out[3]["rev"], -4)
        self.assertEqual(out[4]["kind"], "absent")
        self.assertEqual(out[5]["kind"], "absent")

    def test_c4_invalid_switch_denies(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": _anchor_line("POC-1", 1)}},
            self._world(switchState=None))
        self.assertEqual(js["decision"], "deny")
        self.assertEqual(js["reasonCode"], "enforcement-switch-invalid")

    def test_c5_off_allows_with_zero_effects(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": _anchor_line("POC-1", 1)}},
            self._world(switchState="off"))
        self.assertEqual(js, {"decision": "allow"})

    def test_c3_malformed_anchor_denies_fail_closed(self):
        for bad in [
            "[governance-dispatch task=POC-1 rev=one channel=normal actor=D]",
            "[governance-dispatch task=POC-1 channel=normal actor=D]",
            "[governance-dispatch rev=1 task=POC-1 channel=normal actor=D]",
        ]:
            js = self._decide(
                {"name": "subagent", "arguments": {"prompt": bad + "\nbody"}},
                self._world())
            self.assertEqual(js["decision"], "deny", bad)
            self.assertEqual(js["reasonCode"], "enforcement-fail-closed", bad)

    def test_c6a_unanchored_without_root_allows_with_counter(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": "no anchor here"}},
            self._world(located=False))
        self.assertEqual(js["decision"], "allow")
        self.assertEqual(js.get("counter"), "enforcement-unlocated")

    def test_c6b_anchored_without_root_denies(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": _anchor_line("POC-1", 1)}},
            self._world(located=False))
        self.assertEqual(js["decision"], "deny")
        self.assertEqual(js["reasonCode"], "enforcement-fail-closed")
        self.assertIn("GOVERNANCE_REPO_ROOT", js["reason"])

    def test_c1_projection_fault_denies(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": _anchor_line("POC-1", 1)}},
            self._world(projectionFault="corrupt JSON: ...", expectedRevision=None))
        self.assertEqual(js["decision"], "deny")
        self.assertEqual(js["reasonCode"], "enforcement-fail-closed")

    def test_c7_unanchored_allows_with_counter(self):
        js = self._decide(
            {"name": "subagent", "arguments": {"prompt": "plain dispatch"}},
            self._world())
        self.assertEqual(js["decision"], "allow")
        self.assertEqual(js.get("counter"), "enforcement-unanchored")

    def test_unguarded_tool_passes_silently(self):
        js = self._decide(
            {"name": "read_file", "arguments": {"path": "x"}},
            self._world())
        self.assertEqual(js, {"decision": "allow"})

    def test_matching_revision_allows_and_mismatch_denies_with_templates(self):
        js_ok = self._decide(
            {"name": "subagent",
             "arguments": {"prompt": _anchor_line("POC-1", 2) + "\nwork"}},
            self._world())
        self.assertEqual(js_ok, {"decision": "allow"})
        js_bad = self._decide(
            {"name": "subagent",
             "arguments": {"prompt": _anchor_line("POC-1", 1) + "\nwork"}},
            self._world())
        self.assertEqual(js_bad["decision"], "deny")
        self.assertEqual(js_bad["reasonCode"], "revision-mismatch")
        self.assertIn("[governance-enforcement] revision-mismatch:", js_bad["reason"])
        self.assertIn("(remedy:", js_bad["reason"])
        self.assertIn("POC-1", js_bad["detail"])
        self.assertIn("expected revision for POC-1 is 2", js_bad["detail"])


# ── S2 governance-state cache ────────────────────────────────────────────────

class GuardCacheTests(unittest.TestCase):
    DRIVER = (
        "const fsLike = { files: new Map(), statCalls: 0, readCalls: 0 };\n"
        # node:path.join on Windows yields backslash keys — normalize once.
        "const norm = (p) => p.replace(/\\\\/g, '/');\n"
        "const deps = {\n"
        "  repoRoot: () => INPUT.root,\n"
        "  readSwitch: () => INPUT.switchWord,\n"
        "  readFile: (p) => { fsLike.readCalls += 1; "
        "const v = fsLike.files.get(norm(p)); if (v === undefined) throw new Error('missing'); return v.text; },\n"
        "  stat: (p) => { fsLike.statCalls += 1; "
        "const v = fsLike.files.get(norm(p)); if (v === undefined) throw new Error('missing'); "
        "return { mtimeNs: v.mtimeNs, size: v.size }; },\n"
        "  now: () => INPUT.clock,\n"
        "  ttlMs: 30000,\n"
        "  strategy: { hard_block_rules: [{ id: 'revision-mismatch', reason: 'r', remedy: 'm' }] },\n"
        "};\n"
        "const world = guard.createGuardWorld(deps);\n"
        "const probe = () => { const v = world.view(); "
        "return { located: v.located, switchState: v.switchState, "
        "expected: v.expectedRevision, fault: v.projectionFault }; };\n"
        "const out = INPUT.steps.map((step) => {\n"
        "  if (step.set) for (const [k, val] of Object.entries(step.set)) "
        "INPUT[k] = val;\n"
        "  if (step.write) for (const [p, val] of Object.entries(step.write)) "
        "fsLike.files.set(norm(p), val);\n"
        "  const v = probe();\n"  # probe FIRST — the counters must include it
        "  return { reads: fsLike.readCalls, stats: fsLike.statCalls, view: v };\n"
        "});\n"
        "console.log(JSON.stringify(out));\n"
    )

    def _steps_run(self, root, steps):
        return _run_node(
            self.DRIVER,
            payload={"root": root, "switchWord": "", "clock": 1_000,
                     "steps": steps},
        )

    def test_stat_change_ttl_switch_and_root_invalidate(self):
        root = "T:/proj"
        proj = root + "/.governance/enforcement-expected-revision.json"
        locks = root + "/.governance/agent-locks.json"
        steps = [
            {"write": {proj: {"text": '{"POC-1": {"expected_revision": 2}}', "mtimeNs": 1000, "size": 30},
                       locks: {"text": "{}", "mtimeNs": 1000, "size": 2}}},
            # same fingerprint, inside TTL -> cached (no extra read)
            {},
            # W-file mtime_ns change -> invalidate + recompute (read+1)
            {"write": {locks: {"text": "{}", "mtimeNs": 1001, "size": 2}}},
            # same mtime_ns, different SIZE (Windows mtime granularity
            # tolerance — same-length rewrites are the TTL backstop's job)
            {"write": {proj: {"text": '{"POC-2": {"expected_revision": 3}}', "mtimeNs": 1000, "size": 31}}},
            # clock past TTL (30s) -> recompute even with same fingerprint
            {"set": {"clock": 32_000}},
        ]
        out = self._steps_run(root, steps)
        reads = [row["reads"] for row in out]
        self.assertEqual(reads, [1, 1, 2, 3, 4])
        self.assertEqual(out[0]["view"]["expected"], {"POC-1": 2})
        self.assertEqual(out[3]["view"]["expected"], {"POC-2": 3})
        self.assertEqual(out[4]["view"]["expected"], {"POC-2": 3})

    def test_switch_and_root_changes(self):
        root = "T:/proj"
        proj = root + "/.governance/enforcement-expected-revision.json"
        steps = [
            {"write": {proj: {"text": '{"POC-1": {"expected_revision": 2}}', "mtimeNs": 1, "size": 30}}},
            {"set": {"switchWord": "off"}},   # zero-drift: no stats, no state
            {"set": {"switchWord": ""}},      # switch change -> recompute
            {"set": {"root": None}},          # root lost -> unlocated view
        ]
        out = self._steps_run(root, steps)
        self.assertEqual(out[0]["view"]["switchState"], "on")
        self.assertEqual(out[1]["view"], {"located": False, "switchState": "off",
                                          "expected": None, "fault": None})
        self.assertEqual(out[2]["view"]["switchState"], "on")
        self.assertEqual(out[3]["view"]["located"], False)


# ── S3 host-row wiring ───────────────────────────────────────────────────────

class WiringTests(unittest.TestCase):
    DRIVER = (
        "const logs = [];\n"
        "let captured = null, guardCalls = 0;\n"
        "const ctx = { logger: { info: (m) => logs.push(['info', m]), "
        "warn: (m) => logs.push(['warn', m]) } };\n"
        "if (INPUT.withTools) ctx.tools = { guard: (cb) => { captured = cb; guardCalls += 1; return () => {}; } };\n"
        "const outcome = guard.registerEnforcementGuard(ctx, { env: INPUT.env, now: () => 1760000000000 });\n"
        "let denied = null, allowed = 'unset';\n"
        "if (captured) {\n"
        "  denied = captured({ name: 'subagent', arguments: { prompt: "
        "  INPUT.mismatchAnchor + '\\nbody' } });\n"
        "  allowed = captured({ name: 'subagent', arguments: { prompt: 'no anchor' } }) ?? null;\n"
        "}\n"
        "console.log(JSON.stringify({ outcome, guardCalls, logs, denied, allowed }));\n"
    )

    def _run(self, with_tools, env, root, fixture=True):
        if root is not None and fixture:
            gov = Path(root) / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "enforcement-expected-revision.json").write_text(
                '{"POC-1": {"expected_revision": 2}}', encoding="utf-8")
        return _run_node(
            self.DRIVER,
            payload={
                "withTools": with_tools, "env": env,
                "mismatchAnchor": _anchor_line("POC-1", 1),
            },
        )

    def test_registration_success_and_live_deny(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run(True, {"GOVERNANCE_REPO_ROOT": tmp}, tmp)
        self.assertTrue(out["outcome"]["registered"])
        self.assertEqual(out["outcome"]["code"], "REGISTERED")
        self.assertRegex(out["outcome"]["timestamp"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(out["guardCalls"], 1)
        infos = [m for level, m in out["logs"] if level == "info"]
        self.assertTrue(any("enforcement guard registered at" in m for m in infos),
                        out["logs"])  # V8 timestamp anchor
        self.assertIn("[governance-enforcement] revision-mismatch:", out["denied"])
        self.assertIsNone(out["allowed"])  # unanchored -> allow (undefined)

    def test_capability_miss_degrades_with_one_info(self):
        out = self._run(False, {}, None)
        self.assertFalse(out["outcome"]["registered"])
        self.assertEqual(out["outcome"]["code"], "ENFORCEMENT_TOOLS_UNAVAILABLE")
        # Capability miss is a known host shape: reported at INFO (structured
        # code retained) so the row's warn face stays exactly-one-per-failure.
        warns = [m for level, m in out["logs"] if level == "warn"]
        infos = [m for level, m in out["logs"] if level == "info"]
        self.assertEqual(warns, [])
        self.assertEqual(len(infos), 1)
        self.assertIn("ENFORCEMENT_TOOLS_UNAVAILABLE", infos[0])

    def test_off_registers_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run(True, {"GOVERNANCE_ENFORCEMENT": "off"}, tmp)
        self.assertFalse(out["outcome"]["registered"])
        self.assertEqual(out["outcome"]["code"], "enforcement-disabled")
        self.assertEqual(out["guardCalls"], 0)
        self.assertEqual(out["logs"], [])


if __name__ == "__main__":
    unittest.main()
