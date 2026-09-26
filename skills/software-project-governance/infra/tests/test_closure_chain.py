"""Guard tests for infra/closure_chain.py — FEAT-056 (M3 vertical slice +
chaos release gate, version-plan-0.86.0 §2 batch 2.1/2.2).

Coverage map (evolution §4 DoD items 0-9 + ticket acceptance):

  * spec fail-closed validation (DoD 1 pre-execution full validation)
  * standard ticket-closure end-to-end on a fixture governed workspace —
    row flip / EVD append / lock TTL shrink / ready-to-commit summary —
    with journal envelope + seq-monotonicity validation (DoD 3/4: the
    loop_event_log machine reused; no second persistence implementation)
  * effect-based resume idempotency: a full re-run appends ZERO events and
    re-executes nothing (DoD 2; 查世界不信日志)
  * dry-run zero-write resolution proof (DoD 5) — byte-identical
    .governance snapshot before/after
  * CHAOS (release-gate grade, round-3 BT-9 semantics) — the three
    boundaries, each hard-killed via subprocess + parent controller +
    named fault points at protocol boundaries, resumed with ZERO manual
    repair of governed state:
      - boundary ①: evidence 已写 tracker 未更新 → 复用原 EVD 锚点续
      - boundary ②: commit 成功状态未落盘 → 核验不重复提交（临时仓库夹具,
        不真 push）
      - boundary ③: push 凭据失效 → blocked+诊断, 修复后 resume 先核远端
        （隔离 remote: 本地 bare 仓库, 零真实远端副作用）+ push 超时
        UNKNOWN → 先核远端再收敛
    hard-terminate (Popen.kill) and raise-equivalent (structured exit
    codes) failure classes are exercised SEPARATELY; kill ≠ 掉电持久性
    保证 (round-3 verbatim — nothing here derives power-loss guarantees).
  * concurrent resume: two processes, one run lock — exactly one winner,
    the loser refuses lock_contention (retryable), effects land exactly
    once
  * kill-switch (DoD 8 / BT-7): the standard chain's steps executed
    DIRECTLY via the writer CLIs (no engine) reach the same end state;
    source scans prove the dependency direction (engine never imports
    verify_workflow; writers never import closure_chain)
  * negative controls (DoD 7): CJK payload fidelity, repeated execution,
    torn journal line resilience, UNKNOWN world-check gating (远端查询
    建议非自动执行)

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_closure_chain.py -v
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import closure_chain as cc  # noqa: E402
import loop_event_log  # noqa: E402
import task_row_update as tru  # noqa: E402
import write_guard_state as wgs  # noqa: E402  (FIX-383 ledger constants)

CC_PATH = Path(cc.__file__).resolve()
GS_PATH = _INFRA_DIR / "governance_store.py"
TRU_PATH = _INFRA_DIR / "task_row_update.py"
VW_PATH = _INFRA_DIR / "verify_workflow.py"

TASK = "FEAT-901"
DESCRIPTION = ("FEAT-901 标准链收口纵切验证。目标对齐：票收口链把确定性收尾"
               "软件化，与项目目标（过程自动、质量不低质）一致，用户获得零手"
               "写收口与可恢复闭环。")
BASIS = "事实依据：本夹具守护标准链端到端效果与混沌恢复语义"
EVD_INPUTS = {
    "evd_type": "产品代码",
    "evd_description": DESCRIPTION,
    "evd_basis": BASIS,
    "evd_artifacts": "closure_chain.py;test_closure_chain.py",
}

_TRACKER_HEADER = "| 优先级 | ID | 事项 | 依赖 | 版本 | 执行面与验收 | 状态 |"
_TRACKER_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- |"
_TRACKER_ROW = (
    "| **P1** | {task} | 测试票：标准链收口纵切（fixture 夹具行，"
    "非真实计划面） | TRIAGE-{task} | 0.86.0 | Governance Developer → "
    "Code Reviewer。验收 = 新测试全绿 | approved |")

_EVIDENCE_SEED = (
    "| EVD-900 | FEAT-900 | 产品代码 | seed 旧行（legacy 只读样本，"
    "用于 ID 连续性基线） | 事实依据：seed 行 | someone | 2026-09-01 "
    "| G11 | ✅ 完成 |\n")

_LOCKS_SEED = {
    "active_tasks": {
        TASK: {
            "agent_role": "Governance Developer",
            "spawned_at": "2026-09-20T10:00:00",
            "coordinator_session": "fixture-session",
            "target_files": ["fixture/a.md"],
            "description": "closure_chain fixture dispatch lock",
            "acquired": "2026-09-20T10:00:00",
            "files": ["fixture/a.md"],
        },
    },
    "file_locks": {
        "fixture/a.md": {
            "locked_by": TASK,
            "locked_at": "2026-09-20T10:00:00",
            "ttl_seconds": 14400,
            "ttl_reason": "fixture dispatch lock",
        },
    },
}

# ── fixture external-step scripts (simulated git actions, stdlib only) ──────

COMMIT_SCRIPT = (
    "import subprocess, sys\n"
    "repo, msg = sys.argv[1], sys.argv[2]\n"
    "raise SystemExit(subprocess.run(\n"
    "    ['git', '-C', repo, 'commit', '-m', msg]).returncode)\n")

PUSH_SCRIPT = (
    "import subprocess, sys, time\n"
    "repo, remote, cred, mode = sys.argv[1:5]\n"
    "try:\n"
    "    token = open(cred, encoding='utf-8').read().strip()\n"
    "except OSError:\n"
    "    token = ''\n"
    "if token != 'valid-token':\n"
    "    print('authentication failed for ' + remote, file=sys.stderr)\n"
    "    sys.exit(5)\n"
    "pushed = subprocess.run(\n"
    "    ['git', '-C', repo, 'push', remote, 'HEAD:refs/heads/main'])\n"
    "if pushed.returncode != 0:\n"
    "    sys.exit(pushed.returncode)\n"
    "with open(remote + '.pushes', 'a', encoding='utf-8') as f:\n"
    "    f.write(sys.argv[3] + '\\n')\n"
    "if mode == 'hang':\n"
    "    time.sleep(999)\n")

REMOTE_MATCH_SCRIPT = (
    "import subprocess, sys\n"
    "repo, remote = sys.argv[1], sys.argv[2]\n"
    "local = subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'],\n"
    "                       capture_output=True, text=True)\n"
    "if local.returncode != 0:\n"
    "    sys.exit(1)\n"
    "out = subprocess.run(['git', '-C', remote, 'rev-parse',\n"
    "                      'refs/heads/main'], capture_output=True,\n"
    "                     text=True)\n"
    "sys.exit(0 if out.stdout.strip()\n"
    "         and out.stdout.strip() == local.stdout.strip() else 1)\n")

SLOW_SCRIPT = (
    "import sys, time, pathlib\n"
    "time.sleep(float(sys.argv[2]))\n"
    "pathlib.Path(sys.argv[1]).write_text('done', encoding='utf-8')\n")


# ═══════════════════════════════════════════════════════════════════════════
# Fixture helpers
# ═══════════════════════════════════════════════════════════════════════════


def _git(*argv, cwd=None, check=True):
    proc = subprocess.run(["git"] + list(argv), cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    if check and proc.returncode != 0:
        raise AssertionError(
            "git {0} failed: {1}".format(argv, proc.stderr))
    return proc


def _init_repo(path, bare=False):
    path.mkdir(parents=True, exist_ok=True)
    if bare:
        _git("init", "-q", "--bare", str(path))
        _git("-C", str(path), "config", "user.email", "fixture@example.com")
        _git("-C", str(path), "config", "user.name", "fixture")
        return
    _git("init", "-q", "-b", "main", str(path))
    _git("-C", str(path), "config", "user.email", "fixture@example.com")
    _git("-C", str(path), "config", "user.name", "fixture")
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    _git("-C", str(path), "add", "-A")
    _git("-C", str(path), "commit", "-q", "-m", "seed")


def _build_workspace(root):
    """A minimal-but-real governed workspace (tracker + evidence + locks)."""
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(
        "\n".join([_TRACKER_HEADER, _TRACKER_SEPARATOR,
                   _TRACKER_ROW.format(task=TASK)]) + "\n",
        encoding="utf-8")
    (gov / "evidence-log.md").write_text(_EVIDENCE_SEED, encoding="utf-8")
    (gov / "agent-locks.json").write_text(
        json.dumps(_LOCKS_SEED, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8")
    return gov


def _snapshot_tree(base):
    """{relpath: bytes} of every file under base (zero-write assertions)."""
    snap = {}
    if not base.is_dir():
        return snap
    for path in sorted(base.rglob("*")):
        if path.is_file():
            snap[str(path.relative_to(base))] = path.read_bytes()
    return snap


def _chain_events(root, closure_id):
    log_path = cc.default_event_log_path(root)
    return loop_event_log.read_events(log_path=log_path, unit_id=closure_id)


def _point_marker(handshake_dir, point):
    return Path(handshake_dir) / (
        re.sub(r"[^a-z0-9-]", "__", point) + ".reached")


def _wait_marker(handshake_dir, point, timeout=60.0):
    marker = _point_marker(handshake_dir, point)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if marker.exists():
            return True
        time.sleep(0.05)
    return False


def _clean_env(**extra):
    env = dict(os.environ)
    env.pop(cc.CLOSURE_TEST_FAULT_ENV, None)
    env.update({k: v for k, v in extra.items() if v is not None})
    return env


def _spawn_run(root, closure_id, *, spec_path=None, inputs=None,
               fault_points=None, handshake_dir=None, world_check=False,
               lock_timeout=None, extra=()):
    argv = [sys.executable, str(CC_PATH), "--project-root", str(root),
            "run", "--task", TASK, "--closure-id", closure_id]
    if spec_path is not None:
        argv += ["--spec", str(spec_path)]
    for key, value in (inputs or {}).items():
        argv += ["--input", "{0}={1}".format(key, value)]
    if world_check:
        argv.append("--world-check")
    if lock_timeout is not None:
        argv += ["--lock-timeout", str(lock_timeout)]
    argv += list(extra)
    env = _clean_env()
    if fault_points:
        env[cc.CLOSURE_TEST_FAULT_ENV] = json.dumps({
            "handshake_dir": str(handshake_dir),
            "points": list(fault_points)})
    return subprocess.Popen(argv, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace", env=env,
                            cwd=str(root))


def _run_cli(root, *args):
    """Run the closure_chain CLI synchronously → (exit_code, payload).
    An empty stdout carries the child's stderr tail for diagnosis."""
    proc = subprocess.run(
        [sys.executable, str(CC_PATH), "--project-root", str(root)]
        + list(args), capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=_clean_env(), cwd=str(root), check=False,
        timeout=300)
    raw = proc.stdout.strip()
    if not raw:
        return proc.returncode, {"_empty": True, "_code": proc.returncode,
                                 "_stderr": proc.stderr[-1200:]}
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {"_raw": raw[-400:], "_stderr": proc.stderr[-400:]}
    return proc.returncode, payload


def _write_fixture_spec(root, name, spec_dict):
    path = root / name
    path.write_text(json.dumps(spec_dict, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path


def _standard_cli_steps(root, closure_id, inputs):
    """Resolve the standard chain's cli-step argvs WITHOUT the engine —
    the kill-switch proof executes these directly. Path-like inputs are
    resolved exactly as run_chain resolves them (absolute-path discipline)."""
    spec = cc.parse_chain_spec(json.loads(json.dumps(
        cc.STANDARD_TICKET_CLOSURE)))
    merged = dict(cc._REQUIRED_INPUT_DEFAULTS)
    merged.update(inputs)
    for key in cc._PATH_LIKE_INPUTS:
        value = merged.get(key)
        if value and not os.path.isabs(value):
            merged[key] = str(root / value)
    mapping = cc._template_mapping(closure_id, TASK, merged, root)
    resolved = []
    for step in spec.steps:
        if step.kind != "cli":
            resolved.append((step, None))
            continue
        resolved.append((step, list(cc.resolve_template(step.argv, mapping,
                                                        closure_id))))
    return resolved


# ═══════════════════════════════════════════════════════════════════════════
# Spec validation (DoD 1 — pre-execution, fail-closed)
# ═══════════════════════════════════════════════════════════════════════════


class SpecValidationTests(unittest.TestCase):
    def test_builtin_standard_spec_parses(self):
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        self.assertEqual(spec.chain_id, "standard-ticket-closure")
        self.assertEqual([s.step_id for s in spec.steps],
                         ["flip-completed", "append-evidence",
                          "shrink-locks", "ready-to-commit"])
        self.assertEqual(spec.steps[-1].kind, "summary")

    def test_unknown_step_kind_refused(self):
        with self.assertRaises(ValueError):
            cc.parse_chain_spec({
                "chain_id": "x", "steps": [{"step_id": "a", "kind": "nope"}]})

    def test_non_summary_last_step_refused(self):
        with self.assertRaises(ValueError):
            cc.parse_chain_spec({
                "chain_id": "x",
                "steps": [{"step_id": "a", "kind": "cli",
                           "argv": ["python", "-c", "1"]}]})

    def test_duplicate_step_ids_refused(self):
        with self.assertRaises(ValueError):
            cc.parse_chain_spec({
                "chain_id": "x",
                "steps": [
                    {"step_id": "a", "kind": "cli",
                     "argv": ["python", "-c", "1"]},
                    {"step_id": "a", "kind": "summary"}]})

    def test_external_step_rejects_governed_placeholders(self):
        with self.assertRaises(ValueError):
            cc.parse_chain_spec({
                "chain_id": "x",
                "steps": [
                    {"step_id": "a", "kind": "external",
                     "argv": ["python", "-c", "1", "{task}"]},
                    {"step_id": "done", "kind": "summary"}]})

    def test_unknown_probe_kind_refused(self):
        with self.assertRaises(ValueError):
            cc.parse_chain_spec({
                "chain_id": "x",
                "steps": [
                    {"step_id": "a", "kind": "cli",
                     "argv": ["python", "-c", "1"],
                     "probe": {"kind": "vibes"}},
                    {"step_id": "done", "kind": "summary"}]})

    def test_unknown_placeholder_fails_closed(self):
        mapping = cc._template_mapping("closure-" + "0" * 32, TASK, {},
                                       Path("."))
        with self.assertRaises(ValueError):
            cc.resolve_template(("x", "{nope}"), mapping,
                                "closure-" + "0" * 32)

    def test_deterministic_operation_ids(self):
        cid = "closure-" + "1" * 32
        a = cc.step_operation_id(cid, "flip-completed")
        b = cc.step_operation_id(cid, "flip-completed")
        c = cc.step_operation_id(cid, "append-evidence")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        for value in (a, c):
            cc.require_operation_id("test", value)  # contract form


# ═══════════════════════════════════════════════════════════════════════════
# Standard chain end-to-end + finalize + status
# ═══════════════════════════════════════════════════════════════════════════


class _WorkspaceFixture(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="closure_chain_"))
        self.root = self.tmpdir / "host"
        self.gov = _build_workspace(self.root)
        _init_repo(self.root)
        self.closure_id = cc.new_closure_id()
        cc.require_closure_id("fixture", self.closure_id)

    def tearDown(self):
        for entry in sorted(self.tmpdir.rglob("*"), reverse=True):
            try:
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                else:
                    entry.rmdir()
            except OSError:
                pass
        try:
            self.tmpdir.rmdir()
        except OSError:
            pass

    def tracker_text(self):
        return (self.gov / "plan-tracker.md").read_text(encoding="utf-8")

    def evidence_text(self):
        return (self.gov / "evidence-log.md").read_text(encoding="utf-8")

    def locks_json(self):
        return json.loads((self.gov / "agent-locks.json")
                          .read_text(encoding="utf-8"))


class StandardChainE2ETests(_WorkspaceFixture):
    """Full standard chain: flip → evidence → lock shrink → summary,
    then the explicit finalize gate."""

    def test_full_chain_ready_and_effects(self):
        payload = cc.run_chain(
            cc.parse_chain_spec(json.loads(
                json.dumps(cc.STANDARD_TICKET_CLOSURE))),
            root=self.root, task=TASK, inputs=dict(EVD_INPUTS),
            closure_id=self.closure_id)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertIsNone(payload["halt"])
        self.assertFalse(payload["journal_problems"], payload)

        # effect 1: row flipped to ✅ 完成 with the machine provenance op
        op_flip = cc.step_operation_id(self.closure_id, "flip-completed")
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        self.assertIn("✅ 完成", row)
        self.assertIn(op_flip, row)

        # effect 2: exactly ONE EVD row carrying the evidence op marker
        op_evd = cc.step_operation_id(self.closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)
        self.assertIn("EVD-901", self.evidence_text())

        # effect 3: the task's lock TTL shrunk to the ceiling
        locks = self.locks_json()
        entry = locks["file_locks"]["fixture/a.md"]
        self.assertEqual(entry["ttl_seconds"], 60)

        # journal: valid envelopes, strictly monotonic seq, closed enum
        events = _chain_events(self.root, self.closure_id)
        kinds = [e["event_type"] for e in events]
        self.assertEqual(kinds[0], "closure_started")
        self.assertEqual(kinds[-1], "closure_ready")
        self.assertEqual([],
                         loop_event_log.check_cas_monotonicity(events))
        for ev in events:
            self.assertEqual(cc._validate_closure_event(ev), [])
            self.assertEqual(ev["actor"], cc.WRITER_ID)

        # status read face agrees
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["steps"]["flip-completed"], "completed")
        self.assertEqual(status["steps"]["append-evidence"], "completed")
        self.assertEqual(status["steps"]["shrink-locks"], "completed")

        # ready-to-commit summary: message suggestion + do-not-stage list
        summary = payload["steps"][-1]["summary"]
        self.assertTrue(summary["ready"])
        self.assertIn(TASK, summary["commit_message_suggestion"])
        self.assertIn(".governance/closure-events.jsonl",
                      summary["do_not_stage"])

    def test_finalize_gate_verify_only_and_replay(self):
        cc.run_chain(
            cc.parse_chain_spec(json.loads(
                json.dumps(cc.STANDARD_TICKET_CLOSURE))),
            root=self.root, task=TASK, inputs=dict(EVD_INPUTS),
            closure_id=self.closure_id)
        # a sha that does not exist → structured manual refusal, nothing
        # recorded
        code, refused = _run_cli(self.root, "finalize",
                                 "--closure-id", self.closure_id,
                                 "--commit-sha", "deadbee")
        self.assertEqual(code, 2, refused)
        self.assertEqual(refused["code"], "manual_intervention")
        # make the operator commit, then finalize verifies it
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m",
             "{0}: review 通过收口".format(TASK))
        sha = _git("-C", str(self.root), "rev-parse",
                   "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        self.assertEqual(done["status"], "finalized")
        self.assertFalse(done["replayed"])
        code, replay = _run_cli(self.root, "finalize",
                                "--closure-id", self.closure_id,
                                "--commit-sha", sha)
        self.assertEqual(code, 0, replay)
        self.assertTrue(replay["replayed"])
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual(
            sum(1 for e in events
                if e["event_type"] == "closure_finalized"), 1)

    def test_resume_inputs_mismatch_refused(self):
        cc.run_chain(
            cc.parse_chain_spec(json.loads(
                json.dumps(cc.STANDARD_TICKET_CLOSURE))),
            root=self.root, task=TASK, inputs=dict(EVD_INPUTS),
            closure_id=self.closure_id)
        with self.assertRaises(ValueError):
            cc.run_chain(
                cc.parse_chain_spec(json.loads(
                    json.dumps(cc.STANDARD_TICKET_CLOSURE))),
                root=self.root, task=TASK,
                inputs=dict(EVD_INPUTS, lock_ttl="120"),
                closure_id=self.closure_id)


class IdempotentResumeTests(_WorkspaceFixture):
    """A full re-run after completion appends NOTHING and re-executes
    NOTHING (effect-based idempotency; zero duplicate effects)."""

    def test_second_run_is_a_noop(self):
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        first = cc.run_chain(spec, root=self.root, task=TASK,
                             inputs=dict(EVD_INPUTS),
                             closure_id=self.closure_id)
        self.assertEqual(first["status"], "ready")
        before = _snapshot_tree(self.gov)
        events_before = _chain_events(self.root, self.closure_id)
        second = cc.run_chain(spec, root=self.root, task=TASK,
                              inputs=dict(EVD_INPUTS),
                              closure_id=self.closure_id)
        self.assertEqual(second["status"], "ready")
        self.assertEqual(_snapshot_tree(self.gov), before)
        self.assertEqual(_chain_events(self.root, self.closure_id),
                         events_before)

    def test_torn_journal_line_is_skipped_and_resume_continues(self):
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        cc.run_chain(spec, root=self.root, task=TASK,
                     inputs=dict(EVD_INPUTS), closure_id=self.closure_id)
        log_path = cc.default_event_log_path(self.root)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write('{"event_id": "torn", "broken')
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS),
                               closure_id=self.closure_id)
        self.assertEqual(payload["status"], "ready")
        self.assertFalse(payload["journal_problems"], payload)
        # the closed-world effects never duplicated
        op_evd = cc.step_operation_id(self.closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)


class RefusalDetailPassthroughTests(_WorkspaceFixture):
    """FIX-379 item-1 (0.86.0 M-2 量测边缘观察 #1): a writer CLI's refusal
    must reach the step_failed envelope with the writer's REAL closed code
    + detail — never the ``manual_intervention`` fallback with an empty
    ``detail``.  Two payload shapes exist (nested task_row_update vs flat
    top-level governance_store); both extract, the audit face keeps both.
    """

    def test_flat_top_level_refusal_keeps_writer_code_and_detail(self):
        # governance_store _emit shape: the refusal dict IS the payload.
        payload = json.dumps({
            "code": "cross_record_violation",
            "detail": "reference governance_id:MES-001 is unresolvable "
                      "(unknown governance id family 'MES')",
            "error": True,
            "disposition": "validation",
        }, ensure_ascii=False)
        refusal = cc._refusal_from_cli_output(payload, 2)
        self.assertEqual(refusal["code"], "cross_record_violation")
        self.assertIn("unknown governance id family", refusal["detail"])
        self.assertEqual(refusal["exit_code"], 2)

    def test_nested_result_refusal_extraction_unchanged(self):
        # task_row_update mode-annotated shape — the pre-FIX-379 contract.
        payload = json.dumps({
            "mode": "result",
            "result": {"code": "cross_record_violation",
                       "detail": "target file not found: x",
                       "observed_revision": None},
        }, ensure_ascii=False)
        refusal = cc._refusal_from_cli_output(payload, 3)
        self.assertEqual(refusal["code"], "cross_record_violation")
        self.assertEqual(refusal["detail"], "target file not found: x")
        self.assertEqual(refusal["exit_code"], 3)

    def test_flat_refusal_boolean_error_flag_never_becomes_detail(self):
        # The flat shape carries ``error`` as a BOOLEAN flag — a refusal
        # without a detail must record "" (never leak True into text).
        payload = json.dumps({"code": "manual_intervention",
                              "error": True}, ensure_ascii=False)
        refusal = cc._refusal_from_cli_output(payload, 2)
        self.assertEqual(refusal["detail"], "")
        self.assertEqual(refusal["code"], "manual_intervention")

    def test_chain_journal_carries_writer_refusal_detail(self):
        # Integration: a governance_store CLI step whose writer refuses
        # with cross_record_violation (unknown governance id family).
        # Pre-FIX-379 this landed as code=manual_intervention, detail="".
        spec = _write_fixture_spec(self.root, "gs_refusal_spec.json", {
            "chain_id": "gs-refusal-fixture",
            "required_inputs": [],
            "steps": [
                {"step_id": "append-evidence", "kind": "cli",
                 "argv": ["{python}", "{gs_cli}",
                          "--project-root", "{root}", "evidence-append",
                          "--task", "{task}", "--type", "产品代码",
                          "--description", DESCRIPTION,
                          "--basis", BASIS,
                          "--artifacts", "closure_chain.py",
                          "--refs", "governance_id:XXX-1",
                          "--operation-id", "{op:append-evidence}"],
                 "probe": {"kind": "text_anchor",
                           "file": "{gov}/evidence-log.md",
                           "pattern": "{op:append-evidence}"}},
                {"step_id": "endpoint", "kind": "summary"},
            ],
        })
        payload = cc.run_chain(cc.parse_chain_spec(json.loads(
            Path(spec).read_text(encoding="utf-8"))),
            root=self.root, task=TASK, inputs={},
            closure_id=self.closure_id)
        self.assertEqual(payload["status"], "blocked", payload)
        failed = payload["steps"][0]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["code"], "cross_record_violation")
        self.assertTrue(failed["detail"], payload)
        events = _chain_events(self.root, self.closure_id)
        failures = [e for e in events if e["event_type"] == "step_failed"]
        self.assertEqual(len(failures), 1)
        envelope = failures[0]["payload"]
        self.assertEqual(envelope["code"], "cross_record_violation")
        self.assertTrue(envelope["detail"], envelope)
        self.assertIn("unresolvable", envelope["detail"])
        self.assertEqual(envelope["exit_code"], 2)


class DryRunZeroWriteTests(_WorkspaceFixture):
    """--dry-run: probes + writer dry-runs prove every step resolvable
    while the governed workspace stays byte-identical (DoD 5)."""

    def test_dry_run_writes_nothing_and_reports_resolution(self):
        before = _snapshot_tree(self.gov)
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS),
                               closure_id=self.closure_id, dry_run=True)
        self.assertEqual(_snapshot_tree(self.gov), before)
        self.assertFalse(payload["journal_touched"])
        self.assertEqual(payload["writes_performed"], 0)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        # step 1: writer dry-run parsed+validated (row at approved, so the
        # preview renders; zero writes)
        self.assertEqual(by_id["flip-completed"]["status"], "resolvable")
        self.assertEqual(
            by_id["flip-completed"]["writer_dry_run"]["mode"],
            "writer_dry_run")
        # step 2: full writer dry-run with the predicted next EVD id
        self.assertEqual(by_id["append-evidence"]["status"], "resolvable")
        self.assertEqual(
            by_id["append-evidence"]["writer_dry_run"]["payload"]
            ["next_id"], "EVD-901")
        # step 3: locks-amend has no dry-run face — parse-level only,
        # disclosed as such
        self.assertEqual(by_id["shrink-locks"]["writer_dry_run"]["mode"],
                         "parse_level_help")
        self.assertIn("no --dry-run",
                      by_id["shrink-locks"]["writer_dry_run"]["note"])
        # probes ran read-only and report the pre-chain world
        self.assertFalse(by_id["flip-completed"]["probe"]["satisfied"])
        self.assertFalse(by_id["append-evidence"]["probe"]["satisfied"])
        # the fixture lock sits at 14400s — above the 60s ceiling pre-run
        self.assertFalse(by_id["shrink-locks"]["probe"]["satisfied"])
        self.assertEqual(by_id["shrink-locks"]["probe"]["detail"],
                         "locks above ceiling: {'fixture/a.md': 14400}")


class GuardNegativeTests(_WorkspaceFixture):
    """DoD 7 negative controls at the chain level."""

    def test_cjk_payload_lands_as_utf8(self):
        payload = cc.run_chain(
            cc.parse_chain_spec(json.loads(
                json.dumps(cc.STANDARD_TICKET_CLOSURE))),
            root=self.root, task=TASK, inputs=dict(EVD_INPUTS),
            closure_id=self.closure_id)
        self.assertEqual(payload["status"], "ready")
        self.assertIn("目标对齐", self.evidence_text())
        raw = (self.gov / "evidence-log.md").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))  # no BOM
        raw.decode("utf-8")  # strict decode must hold

    def test_repeated_execution_triple_run_single_effects(self):
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        for _ in range(3):
            payload = cc.run_chain(spec, root=self.root, task=TASK,
                                   inputs=dict(EVD_INPUTS),
                                   closure_id=self.closure_id)
            self.assertEqual(payload["status"], "ready")
        op_evd = cc.step_operation_id(self.closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)
        self.assertEqual(self.evidence_text().count("EVD-901 "), 1)
        op_flip = cc.step_operation_id(self.closure_id, "flip-completed")
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        self.assertEqual(row.count(op_flip), 1)

    def test_journal_envelope_validation_rejects_foreign_events(self):
        bad = [{"event_id": "x", "timestamp": "t", "unit_id": "u",
                "event_type": "not_in_enum", "cas_version": 1,
                "from_version": 0, "actor": "a"}]
        self.assertTrue(cc._validate_closure_event(bad[0]))
        worse = dict(bad[0], cas_version=True, event_type="closure_started")
        problems = cc._validate_closure_event(worse)
        self.assertTrue(any("cas_version" in p for p in problems))
        missing = {k: v for k, v in bad[0].items() if k != "actor"}
        self.assertTrue(any("actor" in p
                            for p in cc._validate_closure_event(missing)))


# ═══════════════════════════════════════════════════════════════════════════
# CHAOS — the three boundaries (subprocess + parent controller + named
# fault points; Popen.kill hard termination; isolated fixtures, zero real
# remote side effects, zero real push)
# ═══════════════════════════════════════════════════════════════════════════


class _ChaosFixture(_WorkspaceFixture):
    """Adds the fixture-chain spec writers used by the chaos tests."""

    def evidence_first_spec(self):
        return {
            "chain_id": "chaos-evidence-first",
            "required_inputs": list(EVD_INPUTS),
            "steps": [
                {"step_id": "append-evidence", "kind": "cli",
                 "description": "evidence-first fixture (round-2 恢复规则表"
                                "场景: evidence 已写 tracker 未更新)",
                 "argv": ["{python}", "{gs_cli}",
                          "--project-root", "{root}",
                          "evidence-append",
                          "--task", "{task}",
                          "--type", "{input:evd_type}",
                          "--description", "{input:evd_description}",
                          "--basis", "{input:evd_basis}",
                          "--artifacts", "{input:evd_artifacts}",
                          "--refs", "governance_id:{task}",
                          "--operation-id", "{op:append-evidence}"],
                 "probe": {"kind": "text_anchor",
                           "file": "{gov}/evidence-log.md",
                           "pattern": "{op:append-evidence}"},
                 "dry_run_flag": "--dry-run"},
                {"step_id": "flip-completed", "kind": "cli",
                 "argv": ["{python}", "{tru_cli}",
                          "--task", "{task}",
                          "--from", "{input:from_state}",
                          "--to", "completed",
                          "--reason",
                          "closure {closure_id}: chaos fixture flip",
                          "--operation-id", "{op:flip-completed}",
                          "--file", "{input:tracker_file}",
                          "--json"],
                 "probe": {"kind": "task_row_state",
                           "file": "{input:tracker_file}",
                           "task": "{task}", "expect": "completed"},
                 "dry_run_flag": "--dry-run"},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}

    def commit_spec(self, repo, message):
        return {
            "chain_id": "chaos-commit-fixture",
            "required_inputs": [],
            "steps": [
                {"step_id": "commit-fix", "kind": "external",
                 "description": "simulated commit in a temp repo (real "
                                "local git commit, no network, no push)",
                 "argv": [sys.executable, "-c", COMMIT_SCRIPT,
                          str(repo), message],
                 "probe": {"kind": "git_head_message",
                           "repo": str(repo), "expect": message},
                 "timeout_seconds": 60,
                 "dry_run_flag": None},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}

    def push_spec(self, repo, remote, cred, mode, timeout=30.0):
        return {
            "chain_id": "chaos-push-fixture",
            "required_inputs": [],
            "steps": [
                {"step_id": "push-fix", "kind": "external",
                 "description": "simulated push to an ISOLATED local bare "
                                "remote (zero real remote side effects)",
                 "argv": [sys.executable, "-c", PUSH_SCRIPT,
                          str(repo), str(remote), str(cred), mode],
                 "world_check": [sys.executable, "-c",
                                 REMOTE_MATCH_SCRIPT, str(repo),
                                 str(remote)],
                 "blocked_exit_codes": [5],
                 "timeout_seconds": timeout,
                 "dry_run_flag": None},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}


class Boundary1EvidenceWithoutTrackerTests(_ChaosFixture):
    """边界①: evidence 已写、tracker 未更新——kill 后 resume 复用原 EVD
    锚点续，零重复追加、零人工修复。"""

    def test_kill_between_evidence_and_flip_resumes_with_reused_anchor(self):
        spec_path = _write_fixture_spec(self.root, "evidence_first.json",
                                        self.evidence_first_spec())
        handshake = self.tmpdir / "hs1"
        proc = _spawn_run(self.root, self.closure_id,
                          spec_path=spec_path, inputs=dict(EVD_INPUTS),
                          fault_points=["post-step-effect:append-evidence"],
                          handshake_dir=handshake)
        self.assertTrue(
            _wait_marker(handshake, "post-step-effect:append-evidence"),
            "child never reached the named fault point")
        proc.kill()
        proc.wait(timeout=60)
        self.assertNotEqual(proc.returncode, 0)

        # the world already has the EVD; the tracker is NOT flipped
        op_evd = cc.step_operation_id(self.closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        self.assertIn("approved", row)   # tracker NOT updated
        events = _chain_events(self.root, self.closure_id)
        self.assertNotIn("step_completed",
                         [e["event_type"] for e in events])

        # resume: zero manual repair — anchor reused, flip executes once
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id,
                                 "--input",
                                 "evd_type={0}".format(EVD_INPUTS["evd_type"]),
                                 "--input",
                                 "evd_description={0}".format(
                                     EVD_INPUTS["evd_description"]),
                                 "--input",
                                 "evd_basis={0}".format(EVD_INPUTS["evd_basis"]),
                                 "--input",
                                 "evd_artifacts={0}".format(
                                     EVD_INPUTS["evd_artifacts"]))
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["append-evidence"]["status"], "reconciled")
        self.assertIn("EVD-", str(by_id["append-evidence"].get("anchor")))
        self.assertEqual(by_id["flip-completed"]["status"], "completed")

        # invariants: exactly one EVD row, tracker flipped exactly once,
        # journal monotonic
        self.assertEqual(self.evidence_text().count(op_evd), 1)
        self.assertEqual(self.evidence_text().count("EVD-901 "), 1)
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        self.assertIn("✅ 完成", row)
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual(
            [], loop_event_log.check_cas_monotonicity(events))


class Boundary1FlipWithoutEvidenceTests(_ChaosFixture):
    """同边界①镜像（标准链顺序）: flip 已落、evidence 未写——resume 只补
    evidence 一次。"""

    def test_kill_after_flip_resumes_appending_evidence_once(self):
        handshake = self.tmpdir / "hs1b"
        proc = _spawn_run(self.root, self.closure_id,
                          inputs=dict(EVD_INPUTS),
                          fault_points=["post-step-effect:flip-completed"],
                          handshake_dir=handshake)
        self.assertTrue(
            _wait_marker(handshake, "post-step-effect:flip-completed"))
        proc.kill()
        proc.wait(timeout=60)
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        self.assertIn("✅ 完成", row)
        self.assertNotIn("governance-store evidence-append",
                         self.evidence_text())

        code, payload = _run_cli(self.root, "run", "--task", TASK,
                                 "--closure-id", self.closure_id,
                                 "--input",
                                 "evd_type={0}".format(EVD_INPUTS["evd_type"]),
                                 "--input",
                                 "evd_description={0}".format(
                                     EVD_INPUTS["evd_description"]),
                                 "--input",
                                 "evd_basis={0}".format(EVD_INPUTS["evd_basis"]),
                                 "--input",
                                 "evd_artifacts={0}".format(
                                     EVD_INPUTS["evd_artifacts"]))
        self.assertEqual(code, 0, payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["flip-completed"]["status"], "reconciled")
        self.assertEqual(by_id["append-evidence"]["status"], "completed")
        op_evd = cc.step_operation_id(self.closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)


class Boundary2CommitStateNotRecordedTests(_ChaosFixture):
    """边界②: commit 成功、状态未落盘——resume 核验目标 commit 后不重复
    提交（临时仓库夹具，不真 push）。"""

    def _commit_count(self, repo):
        return int(_git("-C", str(repo), "rev-list", "--count",
                        "HEAD").stdout.strip())

    def test_kill_after_commit_resumes_without_recommitting(self):
        repo = self.tmpdir / "repo"
        _init_repo(repo)
        message = "fixture: chain-owned commit {0}".format(
            self.closure_id[:16])
        (repo / "work.txt").write_text("1\n", encoding="utf-8")
        _git("-C", str(repo), "add", "-A")
        spec_path = _write_fixture_spec(
            self.root, "commit_fixture.json",
            self.commit_spec(repo, message))
        handshake = self.tmpdir / "hs2"
        proc = _spawn_run(self.root, self.closure_id,
                          spec_path=spec_path, inputs={},
                          fault_points=["post-step-effect:commit-fix"],
                          handshake_dir=handshake)
        self.assertTrue(_wait_marker(handshake, "post-step-effect:commit-fix"))
        proc.kill()
        proc.wait(timeout=60)
        # the commit EXISTS in the world; the journal lacks the completion
        count_after_kill = self._commit_count(repo)
        head = _git("-C", str(repo), "log", "-1",
                    "--format=%s").stdout.strip()
        self.assertEqual(head, message)

        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 0, payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["commit-fix"]["status"], "reconciled")
        self.assertEqual(payload["status"], "ready")
        # 核验不重复提交: commit count unchanged by the resume
        self.assertEqual(self._commit_count(repo), count_after_kill)

    def test_commit_failure_is_structured_then_repaired_by_resume(self):
        repo = self.tmpdir / "repo2"
        _init_repo(repo)
        message = "fixture: repaired commit"
        spec_path = _write_fixture_spec(
            self.root, "commit_fixture2.json",
            self.commit_spec(repo, message))
        # nothing staged → git commit exits non-zero → structured block
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "blocked")
        failed = payload["steps"][0]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["code"], "manual_intervention")
        count_before = self._commit_count(repo)
        # world repair (stage work) — NOT a governed-state hand edit
        (repo / "work.txt").write_text("2\n", encoding="utf-8")
        _git("-C", str(repo), "add", "-A")
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(self._commit_count(repo), count_before + 1)


class Boundary3PushCredentialTests(_ChaosFixture):
    """边界③: push 凭据失效 → blocked+诊断；修复后 resume 先核远端
    （隔离 remote：本地 bare 仓库，零真实远端副作用）。push 超时 →
    UNKNOWN → 先核远端再收敛（协议用例组 C 第三腿）。"""

    def _bare(self, name):
        remote = self.tmpdir / name
        _init_repo(remote, bare=True)
        return remote

    def _push_count(self, remote):
        marker = Path(str(remote) + ".pushes")
        if not marker.is_file():
            return 0
        return len(marker.read_text(encoding="utf-8").splitlines())

    def test_credential_failure_blocks_with_diagnostic_then_repairs(self):
        repo = self.tmpdir / "repo3"
        _init_repo(repo)
        remote = self._bare("remote3.git")
        cred = self.tmpdir / "cred.txt"
        cred.write_text("wrong", encoding="utf-8")
        spec_path = _write_fixture_spec(
            self.root, "push_fixture.json",
            self.push_spec(repo, remote, cred, "exit"))
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "blocked")
        failed = payload["steps"][0]
        self.assertEqual(failed["code"], "manual_intervention")
        self.assertIn("repair the external world", failed["detail"])
        # resume without repair → honestly blocked again (no silent retry
        # that pretends health)
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "blocked")
        # credential repair (the sanctioned external remediation), then
        # resume WITH world check: remote queried FIRST, effect absent →
        # push executes exactly once
        cred.write_text("valid-token", encoding="utf-8")
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id,
                                 "--world-check")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(self._push_count(remote), 1)
        head = _git("-C", str(repo), "rev-parse", "HEAD").stdout.strip()
        pushed = _git("-C", str(remote), "rev-parse",
                      "refs/heads/main").stdout.strip()
        self.assertEqual(head, pushed)

    def test_timeout_marks_unknown_and_world_check_resolves_without_repush(self):
        repo = self.tmpdir / "repo4"
        _init_repo(repo)
        remote = self._bare("remote4.git")
        cred = self.tmpdir / "cred4.txt"
        cred.write_text("valid-token", encoding="utf-8")
        spec_path = _write_fixture_spec(
            self.root, "push_fixture4.json",
            self.push_spec(repo, remote, cred, "hang", timeout=8.0))
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check", payload)
        self.assertEqual(payload["steps"][0]["status"], "unknown")
        # push already landed before the hang; the UNKNOWN is honest
        self.assertEqual(self._push_count(remote), 1)
        # resume WITHOUT --world-check: the read-only remote query is
        # suggested, never auto-executed
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check")
        self.assertIn("world-check", payload["steps"][0]["note"])
        self.assertEqual(self._push_count(remote), 1)
        # resume WITH --world-check: remote query resolves the UNKNOWN —
        # the effect is present, no re-push
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id,
                                 "--world-check")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(payload["steps"][0]["status"], "reconciled")
        self.assertEqual(self._push_count(remote), 1)

    def test_hard_kill_after_push_lands_reconciles_via_world_check(self):
        repo = self.tmpdir / "repo5"
        _init_repo(repo)
        remote = self._bare("remote5.git")
        cred = self.tmpdir / "cred5.txt"
        cred.write_text("valid-token", encoding="utf-8")
        spec_path = _write_fixture_spec(
            self.root, "push_fixture5.json",
            self.push_spec(repo, remote, cred, "exit"))
        handshake = self.tmpdir / "hs3"
        proc = _spawn_run(self.root, self.closure_id,
                          spec_path=spec_path, inputs={},
                          fault_points=["post-step-effect:push-fix"],
                          handshake_dir=handshake)
        self.assertTrue(_wait_marker(handshake, "post-step-effect:push-fix"))
        proc.kill()
        proc.wait(timeout=60)
        self.assertEqual(self._push_count(remote), 1)
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id,
                                 "--world-check")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["steps"][0]["status"], "reconciled")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(self._push_count(remote), 1)


# ═══════════════════════════════════════════════════════════════════════════
# Concurrent resume — one run lock, exactly one winner
# ═══════════════════════════════════════════════════════════════════════════


class ConcurrentResumeTests(_ChaosFixture):
    def test_second_resume_refuses_lock_contention_effects_land_once(self):
        sentinel1 = self.tmpdir / "s1.sentinel"
        sentinel2 = self.tmpdir / "s2.sentinel"
        spec = {
            "chain_id": "chaos-slow-fixture",
            "required_inputs": [],
            "steps": [
                {"step_id": "slow-1", "kind": "external",
                 "argv": [sys.executable, "-c", SLOW_SCRIPT,
                          str(sentinel1), "2"],
                 "timeout_seconds": 30, "dry_run_flag": None},
                {"step_id": "slow-2", "kind": "external",
                 "argv": [sys.executable, "-c", SLOW_SCRIPT,
                          str(sentinel2), "2"],
                 "timeout_seconds": 30, "dry_run_flag": None},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}
        spec_path = _write_fixture_spec(self.root, "slow.json", spec)
        winner = _spawn_run(self.root, self.closure_id,
                            spec_path=spec_path, inputs={})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not sentinel1.exists():
            time.sleep(0.05)
        self.assertTrue(sentinel1.exists(), "winner never passed step 1")
        loser = _spawn_run(self.root, self.closure_id,
                           spec_path=spec_path, inputs={},
                           lock_timeout=1.0)
        loser_out, _ = loser.communicate(timeout=120)
        self.assertNotEqual(loser.returncode, 0)
        try:
            loser_payload = json.loads(loser_out.strip() or "{}")
        except ValueError:
            loser_payload = {}
        self.assertEqual(loser_payload.get("code"), "lock_contention")
        self.assertEqual(loser_payload.get("disposition"), "retryable")
        winner_out, _ = winner.communicate(timeout=120)
        self.assertEqual(winner.returncode, 0, winner_out)
        winner_payload = json.loads(winner_out.strip())
        self.assertEqual(winner_payload["status"], "ready")
        self.assertTrue(sentinel2.exists())
        # a post-completion resume converges with zero duplicate effects:
        # each slow step owns exactly started+completed, appended ONCE
        code, payload = _run_cli(self.root, "run", "--spec",
                                 str(spec_path), "--task", TASK,
                                 "--closure-id", self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready")
        events = _chain_events(self.root, self.closure_id)
        for slow in ("slow-1", "slow-2"):
            mine = [e for e in events
                    if (e.get("payload") or {}).get("step_id") == slow]
            self.assertEqual(len(mine), 2, slow)  # started + completed
            self.assertEqual(sorted(e["event_type"] for e in mine),
                             ["step_completed", "step_started"])


# ═══════════════════════════════════════════════════════════════════════════
# Kill-switch (DoD 8 / BT-7) — per-step CLI fallback + dependency direction
# ═══════════════════════════════════════════════════════════════════════════


class KillSwitchTests(_WorkspaceFixture):
    def test_standard_chain_steps_run_standalone_without_the_engine(self):
        """The exact argvs declared by the standard chain, executed DIRECTLY
        (no run_chain, no journal), reach the same governed end state —
        engine removal degrades to the per-step M7.4 protocol, never to
        hand edits."""
        closure_id = cc.new_closure_id()
        resolved = _standard_cli_steps(self.root, closure_id, EVD_INPUTS)
        for step, argv in resolved:
            if argv is None:
                continue  # summary step is engine-computed; nothing to run
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  check=False, timeout=120)
            self.assertEqual(proc.returncode, 0,
                             "{0}: {1}".format(step.step_id, proc.stdout))
        self.assertIn("✅ 完成", self.tracker_text())
        op_evd = cc.step_operation_id(closure_id, "append-evidence")
        self.assertEqual(self.evidence_text().count(op_evd), 1)
        self.assertEqual(
            self.locks_json()["file_locks"]["fixture/a.md"]["ttl_seconds"],
            60)

    def test_dependency_direction_engine_never_imports_engine_writers(self):
        engine_text = CC_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import verify_workflow", engine_text)
        for writer in (TRU_PATH, GS_PATH,
                       _INFRA_DIR / "baseline_metadata.py"):
            text = writer.read_text(encoding="utf-8")
            self.assertNotIn("closure_chain", text,
                             "{0} must not depend on the orchestrator"
                             .format(writer.name))


# ═══════════════════════════════════════════════════════════════════════════
# Fault-injection surface — internal test entry only (round-3 BT-9)
# ═══════════════════════════════════════════════════════════════════════════


class FaultSurfaceTests(_WorkspaceFixture):
    def test_production_cli_exposes_no_fault_flags(self):
        proc = subprocess.run(
            [sys.executable, str(CC_PATH), "run", "--help"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), check=False, timeout=60)
        self.assertEqual(proc.returncode, 0)
        # "fault" alone would match the substring in "default" — check the
        # actual injection-face markers
        self.assertNotIn("--fault", proc.stdout)
        self.assertNotIn("fault-point", proc.stdout.lower())
        self.assertNotIn("fault_point", proc.stdout.lower())

    def test_no_env_means_no_injection(self):
        saved = os.environ.pop(cc.CLOSURE_TEST_FAULT_ENV, None)
        try:
            self.assertFalse(cc._maybe_fault("post-step-effect:anything"))
        finally:
            if saved is not None:
                os.environ[cc.CLOSURE_TEST_FAULT_ENV] = saved

    def test_release_posture_declaration_present(self):
        # the module documents the kill≠power-loss boundary verbatim enough
        # to survive review (round-3: 进程 kill ≠ 掉电/存储故障)
        doc = CC_PATH.read_text(encoding="utf-8")
        self.assertIn("kill", doc)
        self.assertIn("掉电", doc)


# ═══════════════════════════════════════════════════════════════════════════
# CLI-step timeout taxonomy (review-FEAT-056-CODE-R0 P2-1 — FEAT-057 承接)
# ═══════════════════════════════════════════════════════════════════════════


CLI_TIMEOUT_LANDED_SCRIPT = (
    "import pathlib, sys, time\n"
    "pathlib.Path(sys.argv[1]).write_text('ok', encoding='utf-8')\n"
    "time.sleep(30)\n")
"""Effect lands immediately, then hangs past any short timeout (killed).
Backs review-FEAT-057-CODE-R0 P1-1 landed leg."""

CLI_TIMEOUT_NOTLANDED_SCRIPT = (
    "import pathlib, sys, time\n"
    "count = pathlib.Path(sys.argv[2])\n"
    "seen = int(count.read_text(encoding='utf-8')) if count.exists() else 0\n"
    "count.write_text(str(seen + 1), encoding='utf-8')\n"
    "if seen >= 1:\n"
    "    pathlib.Path(sys.argv[1]).write_text('ok', encoding='utf-8')\n"
    "else:\n"
    "    time.sleep(30)\n")
"""First invocation hangs past the timeout (killed, effect NOT landed);
the recovery re-invocation lands the effect and exits 0. Backs the P1-1
not-landed leg."""


class CliStepTimeoutTaxonomyTests(_WorkspaceFixture):
    """P2-1: a governed-writer subprocess TIMEOUT is a hard kill whose
    effect may have landed before the kill — the event taxonomy must match
    the external step (``step_unknown`` / ``awaiting-world-check``), not
    ``blocked``/``manual_intervention``. Both recovery legs reach the ready
    terminal state (review-FEAT-057-CODE-R0 P1-1, 方案 c): effect landed →
    the step's own read-only probe reconciles (no re-run); effect not
    landed → the probe miss releases the step for re-execution (the
    writer's effect-based replay / state-level CAS carries idempotency —
    the pre-P2-1 timeout behavior)."""

    def _timeout_spec(self, world_check):
        return {
            "chain_id": "cli-timeout-fixture",
            "required_inputs": [],
            "steps": [
                {"step_id": "slow-writer", "kind": "cli",
                 "description": "governed writer that hangs past its "
                                "timeout (hard-kill crash window)",
                 "argv": [sys.executable, "-c",
                          "import time; time.sleep(8)"],
                 "timeout_seconds": 1.0,
                 "world_check": list(world_check),
                 "dry_run_flag": None},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}

    def _recovery_spec(self, script, done_path, counter_path):
        """Timeout fixture with NO declared world_check (the standard-chain
        shape that stranded the not-landed leg) and a real effect probe."""
        return {
            "chain_id": "cli-timeout-recovery",
            "required_inputs": [],
            "steps": [
                {"step_id": "slow-writer", "kind": "cli",
                 "description": "governed writer hanging past its timeout; "
                                "no world_check declared (standard-chain "
                                "shape, review-FEAT-057-CODE-R0 P1-1)",
                 "argv": [sys.executable, "-c", script,
                          str(done_path), str(counter_path)],
                 "probe": {"kind": "command_exit",
                           "argv": [sys.executable, "-c",
                                    "import pathlib, sys; sys.exit(0 if "
                                    "pathlib.Path(sys.argv[1]).exists() "
                                    "else 1)",
                                    str(done_path)]},
                 "timeout_seconds": 1.0,
                 "dry_run_flag": None},
                {"step_id": "ready-to-commit", "kind": "summary"},
            ]}

    def _started_count(self, closure_id, step_id="slow-writer"):
        events = _chain_events(self.root, closure_id)
        return sum(
            1 for e in events
            if e.get("event_type") == "step_started"
            and (e.get("payload") or {}).get("step_id") == step_id)

    def test_cli_timeout_records_step_unknown_and_reconciles(self):
        world_check = [sys.executable, "-c", "pass"]
        spec_path = _write_fixture_spec(
            self.root, "cli_timeout.json", self._timeout_spec(world_check))
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check", payload)
        self.assertEqual(payload["steps"][0]["status"], "unknown")
        events = _chain_events(self.root, self.closure_id)
        unknowns = [e for e in events
                    if e.get("event_type") == "step_unknown"]
        self.assertEqual(len(unknowns), 1, events)
        self.assertEqual(unknowns[0]["payload"]["step_id"], "slow-writer")
        self.assertEqual(unknowns[0]["payload"].get("execution"), "unknown")
        self.assertIn("timed out", unknowns[0]["payload"]["detail"])
        self.assertNotIn("manual_intervention",
                         json.dumps(unknowns[0]["payload"]))
        # resume WITHOUT --world-check: the world check is suggested, never
        # auto-executed (round-2 查询建议非自动)
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check")
        self.assertIn("world-check", payload["steps"][0]["note"])
        # resume WITH --world-check: the declared read-only check resolves
        # the UNKNOWN — reconciled, and the writer executed exactly once
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id, "--world-check")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(payload["steps"][0]["status"], "reconciled")
        events = _chain_events(self.root, self.closure_id)
        started = [e for e in events
                   if e.get("event_type") == "step_started"
                   and (e.get("payload") or {}).get("step_id")
                   == "slow-writer"]
        self.assertEqual(len(started), 1, events)  # no blind re-run

    def test_single_flight_assumption_declared_and_do_not_stage_lock(self):
        """P3-④: the single-closure-per-task concurrency assumption is
        disclosed in the module docstring (never silent); P3-①: the
        journal's cross-process lock companion file joins do_not_stage."""
        doc = CC_PATH.read_text(encoding="utf-8")
        self.assertIn("单飞", doc)
        self.assertIn("evolution §6②", doc)
        summary = cc._summary_payload(
            cc.parse_chain_spec({"chain_id": "x", "steps": [
                {"step_id": "a", "kind": "cli",
                 "argv": ["python", "-c", "1"]},
                {"step_id": "s", "kind": "summary"}]}),
            "closure-" + "0" * 32, TASK, {})
        self.assertIn(".governance/closure-events.jsonl",
                      summary["do_not_stage"])
        self.assertIn(".governance/closure-events.jsonl.lock",
                      summary["do_not_stage"])
        # P3-⑥: the vestigial always-true --json flag is gone from the
        # chain's own CLI (writer argvs keep their own writer flags)
        proc = subprocess.run(
            [sys.executable, str(CC_PATH), "run", "--task", TASK, "--json"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), check=False, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--json", proc.stderr)

    # ── review-FEAT-057-CODE-R0 P1-1: both recovery legs reachable ──────

    def test_timeout_not_landed_bare_resume_reexecutes_to_ready(self):
        """P1-1 not-landed leg: probe MISS on a CLI step with no declared
        world_check releases the step for re-execution on a BARE resume —
        the chain reaches ready (pre-fix this halted forever with a literal
        "n/a" remediation)."""
        done = self.tmpdir / "done-notlanded.flag"
        counter = self.tmpdir / "invocations-notlanded.flag"
        spec_path = _write_fixture_spec(
            self.root, "cli_timeout_notlanded.json",
            self._recovery_spec(CLI_TIMEOUT_NOTLANDED_SCRIPT, done, counter))
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check", payload)
        self.assertFalse(done.exists())  # effect NOT landed
        # bare resume (no --world-check): probe miss ⇒ re-execute
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(payload["steps"][0]["status"], "completed")
        self.assertTrue(done.exists())
        self.assertEqual(self._started_count(self.closure_id), 2)

    def test_timeout_landed_bare_resume_reconciles_without_rerun(self):
        """P1-1 landed leg: probe HIT reconciles on a BARE resume (no
        --world-check, no declared world_check) — no re-execution."""
        done = self.tmpdir / "done-landed.flag"
        counter = self.tmpdir / "invocations-landed.flag"
        spec_path = _write_fixture_spec(
            self.root, "cli_timeout_landed.json",
            self._recovery_spec(CLI_TIMEOUT_LANDED_SCRIPT, done, counter))
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "awaiting-world-check", payload)
        self.assertTrue(done.exists())  # effect landed before the kill
        # bare resume: probe hit ⇒ reconcile, never re-execute
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(payload["steps"][0]["status"], "reconciled")
        self.assertEqual(self._started_count(self.closure_id), 1)

    def test_world_check_resume_on_undeclared_world_check_no_longer_crashes(self):
        """P1-1: following the old suggested remediation (--world-check on a
        CLI step with no declared world_check) built an empty command_exit
        argv and crashed with schema_violation. 方案 (c): the step re-
        executes instead — structured success, no crash."""
        done = self.tmpdir / "done-wc.flag"
        counter = self.tmpdir / "invocations-wc.flag"
        spec_path = _write_fixture_spec(
            self.root, "cli_timeout_wc.json",
            self._recovery_spec(CLI_TIMEOUT_NOTLANDED_SCRIPT, done, counter))
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id)
        self.assertEqual(code, 2, payload)
        # the previously-crashing remediation now recovers
        code, payload = _run_cli(self.root, "run", "--spec", str(spec_path),
                                 "--task", TASK, "--closure-id",
                                 self.closure_id, "--world-check")
        self.assertEqual(code, 0, payload)
        self.assertNotEqual(payload.get("code"), "schema_violation", payload)
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(payload["steps"][0]["status"], "completed")


# ═══════════════════════════════════════════════════════════════════════════
# Release-window bootstrap (FIX-383 — 0.88.0 阶段 B2, rollback §8 #7
# ⑩拆票之一): the release chain's checker/writer intermediate states during
# a version switch — guard baseline not re-generated (基线未 regen),
# violation-ledger line-index drift (账本行号漂移), a foreign guard state
# schema (状态文件版本变化), a pending FEAT-060 consumption transaction —
# converge on re-entry with ZERO manual repair (自举). Fault injection
# reuses the round-3 BT-9 machinery: named protocol-boundary fault points,
# parent-controller hard kill, resume judged by the world (查世界不信日志).
# ═══════════════════════════════════════════════════════════════════════════

_BOOT_VIOLATION_ID = "WV-" + "a" * 32
_BOOT_GRANT_ID = "grant-" + "b" * 32
_BOOT_TXN_ID = "txn-" + "c" * 32
_BOOT_STATE_FILE = ".write-guard-state.json"
_BOOT_LEDGER_FILE = ".write-guard-violations.json"


def _bootstrap_cli(root, *args):
    """Run verify_workflow write-guard-bootstrap → (exit_code, payload)."""
    proc = subprocess.run(
        [sys.executable, str(VW_PATH), "--project-root", str(root),
         "write-guard-bootstrap"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_clean_env(), cwd=str(root), check=False, timeout=300)
    raw = proc.stdout.strip()
    if not raw:
        return proc.returncode, {"_empty": True, "_code": proc.returncode,
                                 "_stderr": proc.stderr[-1200:]}
    try:
        return proc.returncode, json.loads(raw)
    except ValueError:
        return proc.returncode, {"_raw": raw[-400:],
                                 "_stderr": proc.stderr[-400:]}


def _row_digest32(text):
    """The guard's row digest (verify_workflow._write_guard_row_digest
    semantics — 128-bit truncation of the stripped row's sha256)."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:32]


def _bootstrap_run(root, closure_id, **kwargs):
    """One release-window-bootstrap chain run via the CLI."""
    return _run_cli(root, "run", "--chain", "release-window-bootstrap",
                    "--task", TASK, "--closure-id", closure_id, **kwargs)


class ReleaseBootstrapTests(_WorkspaceFixture):
    """FIX-383 acceptance: 自举路径实现 + 故障注入恢复测试（中断后重入
    零人工修复到达终态）."""

    def test_builtin_bootstrap_spec_parses(self):
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.RELEASE_WINDOW_BOOTSTRAP)))
        self.assertEqual(spec.chain_id, "release-window-bootstrap")
        self.assertEqual([s.step_id for s in spec.steps],
                         ["write-guard-converge", "bootstrap-ready"])
        step = spec.steps[0]
        self.assertEqual(step.kind, "cli")
        self.assertIsNone(step.dry_run_flag)  # parse-level resolution only
        self.assertEqual(step.probe["kind"], "command_exit")
        self.assertIn("--check-only", step.probe["argv"])
        self.assertNotIn("--check-only", step.argv)

    def test_standard_chain_summary_bytes_unchanged_by_chain_awareness(self):
        """FIX-383 generalized the summary payload per chain — the standard
        chain's endpoint bytes stay the pre-FIX-383 literal (backward
        compat is guarded, not assumed; unknown chain ids keep the same
        fallback), and only the bootstrap chain's message names what
        actually converged."""
        spec = cc.parse_chain_spec(json.loads(
            json.dumps(cc.STANDARD_TICKET_CLOSURE)))
        summary = cc._summary_payload(spec, self.closure_id, TASK, {})
        self.assertEqual(
            summary["commit_message_suggestion"],
            "{0}: review 通过收口（closure-chain 标准链）\n\n"
            "Closure: {1}\n"
            "Chain: standard-ticket-closure (FEAT-056 standard ticket "
            "closure)\n"
            "Task row flipped via task-row-update; evidence appended via\n"
            "evidence-append; dispatch-lock TTLs shrunk via locks-amend\n"
            "(locks-release remains a registered gap — TTL shrink is the\n"
            "governed stand-in, disclosed not silent).\n"
            "Completion gate: closure-chain --finalize --closure-id {1}\n"
            "--commit-sha <sha-of-this-commit>".format(
                TASK, self.closure_id))
        self.assertNotIn(".governance/" + _BOOT_STATE_FILE,
                         summary["do_not_stage"])
        boot_summary = cc._summary_payload(
            cc.parse_chain_spec(json.loads(
                json.dumps(cc.RELEASE_WINDOW_BOOTSTRAP))),
            self.closure_id, TASK, {})
        self.assertNotEqual(boot_summary["commit_message_suggestion"],
                            summary["commit_message_suggestion"])
        self.assertIn("FIX-383 release-window bootstrap",
                      boot_summary["commit_message_suggestion"])
        # the guard's own state artifacts join the do-not-stage class only
        # on the bootstrap chain (post-commit bookkeeping, FEAT-056 R0 P3-1)
        self.assertIn(".governance/" + _BOOT_STATE_FILE,
                      boot_summary["do_not_stage"])

    def test_check_only_is_zero_write_and_reports_unbaselined_window(self):
        before = _snapshot_tree(self.gov)
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 1, report)
        self.assertFalse(report["converged"])
        self.assertIn("guard_state_current", report["not_converged"])
        self.assertEqual(report["tool"],
                         "governance-write-guard/release-bootstrap-check")
        # zero writes, zero window consumption (the probe-face contract)
        self.assertEqual(_snapshot_tree(self.gov), before)

    def test_converge_reaches_ready_and_reentry_reconciles_without_rerun(self):
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["write-guard-converge"]["status"],
                         "completed")
        # the chain-aware summary + the guard-owned do_not_stage extension
        summary = payload["steps"][-1]["summary"]
        self.assertIn("FIX-383 release-window bootstrap",
                      summary["commit_message_suggestion"])
        self.assertIn(".governance/" + _BOOT_STATE_FILE,
                      summary["do_not_stage"])
        self.assertIn(".governance/" + _BOOT_LEDGER_FILE,
                      summary["do_not_stage"])
        state_path = self.gov / _BOOT_STATE_FILE
        self.assertTrue(state_path.is_file())
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["converged"], report)
        # idempotent re-entry: bookkeeping present + probe confirms the
        # effect — the guard is NOT re-run (its state artifact is
        # byte-identical afterwards). ("reconciled" is the crash-window
        # label — journal not yet completed but world already converged —
        # covered by the kill-after-effect test below.)
        state_bytes = state_path.read_bytes()
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["write-guard-converge"]["status"],
                         "completed")
        self.assertEqual(by_id["write-guard-converge"].get("note"),
                         "bookkeeping present; probe confirms effect")
        self.assertEqual(state_path.read_bytes(), state_bytes)
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual([],
                         loop_event_log.check_cas_monotonicity(events))

    # ── fault injection: kill AFTER the guard's effect landed ───────────

    def test_kill_after_effect_resumes_reconciled_zero_manual_repair(self):
        handshake = self.tmpdir / "hs-boot-post"
        proc = _spawn_run(self.root, self.closure_id,
                          fault_points=[
                              "post-step-effect:write-guard-converge"],
                          handshake_dir=handshake,
                          extra=["--chain", "release-window-bootstrap"])
        self.assertTrue(
            _wait_marker(handshake, "post-step-effect:write-guard-converge"),
            "child never reached the named fault point")
        proc.kill()
        proc.wait(timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        # the guard's effect landed (baseline established); the chain's
        # bookkeeping did not (the crash window)
        state_path = self.gov / _BOOT_STATE_FILE
        self.assertTrue(state_path.is_file())
        events = _chain_events(self.root, self.closure_id)
        self.assertNotIn("step_completed", [e["event_type"] for e in events])
        state_bytes = state_path.read_bytes()
        # resume: zero manual repair — the world probe reconciles, the
        # guard is NOT re-run
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["write-guard-converge"]["status"],
                         "reconciled")
        self.assertEqual(state_path.read_bytes(), state_bytes)
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual([],
                         loop_event_log.check_cas_monotonicity(events))

    # ── fault injection: kill BEFORE the guard ran ──────────────────────

    def test_kill_before_effect_resumes_reexecuting_once(self):
        handshake = self.tmpdir / "hs-boot-pre"
        proc = _spawn_run(self.root, self.closure_id,
                          fault_points=["pre-step:write-guard-converge"],
                          handshake_dir=handshake,
                          extra=["--chain", "release-window-bootstrap"])
        self.assertTrue(
            _wait_marker(handshake, "pre-step:write-guard-converge"),
            "child never reached the named fault point")
        proc.kill()
        proc.wait(timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse((self.gov / _BOOT_STATE_FILE).is_file())
        # resume: the probe misses (world not converged) → the governed
        # recovery action executes exactly once → terminal state
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["write-guard-converge"]["status"],
                         "completed")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["converged"], report)

    # ── intermediate state: foreign guard-state schema (版本变化) ────────

    def test_foreign_state_schema_converges_with_disclosed_rebaseline(self):
        (self.gov / _BOOT_STATE_FILE).write_text(
            json.dumps({"schema_version": 99, "tool": "foreign",
                        "files": {}}),
            encoding="utf-8")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 1, report)
        self.assertIn("guard_state_current", report["not_converged"])
        # the chain converges: the guard re-baselines loudly (never a
        # silent amnesty) and the world judgment turns green
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        state = json.loads((self.gov / _BOOT_STATE_FILE)
                           .read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], 1)
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["converged"], report)

    # ── intermediate state: pending FEAT-060 consumption transaction ────

    def test_pending_txn_resumed_by_chain_three_branch_world_judgment(self):
        # world==target leg: the ledger journal + the current baseline agree
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 0, payload)
        state_path = self.gov / _BOOT_STATE_FILE
        state_bytes = state_path.read_bytes()
        row = [ln for ln in self.tracker_text().splitlines()
               if TASK in ln][0]
        ledger = {
            "schema_version": wgs.SCHEMA_VERSION, "tool": wgs.TOOL_ID,
            "updated_at": None,
            "violations": {
                _BOOT_VIOLATION_ID: {
                    "violation_id": _BOOT_VIOLATION_ID,
                    "family": "plan-tracker.md",
                    "object_id": TASK,
                    "before_hash": None,
                    "after_hash": _row_digest32(row),
                    "workflow_run_id": "run-fixture",
                    "hook_identity": wgs.GUARD_CLI_IDENTITY,
                    "first_seen": "2026-09-24T10:00:00",
                    "occurrence": 1,
                    "status": "open",
                    "grant_id": None,
                    "consumption_event": None,
                },
            },
            "grants": {
                _BOOT_GRANT_ID: {
                    "consumer": wgs.CLI_CONSUMER,
                    "issued_at": "2026-09-24T10:00:00",
                    "issued_by_run": "run-fixture",
                    "status": "active",
                },
            },
            "pending_txn": {
                "txn_id": _BOOT_TXN_ID, "operation": "consume",
                "consumer": wgs.CLI_CONSUMER, "grant_id": _BOOT_GRANT_ID,
                "violation_ids": [_BOOT_VIOLATION_ID],
                "baseline_target": json.loads(
                    state_bytes.decode("utf-8")),
                "baseline_target_sha256": hashlib.sha256(
                    state_bytes).hexdigest(),
                "baseline_prev_sha256": "0" * 64,
                "recorded_at": "2026-09-24T10:00:00",
            },
        }
        (self.gov / _BOOT_LEDGER_FILE).write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 1, report)
        self.assertIn("no_pending_txn", report["not_converged"])
        # the chain converge resumes the transaction (world==target →
        # finalize only): violation consumed + grant burned + journal cleared
        recovery_id = cc.new_closure_id()
        code, payload = _bootstrap_run(self.root, recovery_id)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        ledger_after = json.loads((self.gov / _BOOT_LEDGER_FILE)
                                  .read_text(encoding="utf-8"))
        self.assertIsNone(ledger_after["pending_txn"])
        self.assertEqual(
            ledger_after["violations"][_BOOT_VIOLATION_ID]["status"],
            "consumed")
        self.assertEqual(ledger_after["grants"][_BOOT_GRANT_ID]["status"],
                         "used")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["converged"], report)

    # ── intermediate state: violation-ledger line-index drift ───────────

    def test_ledger_drift_detected_then_consumed_by_converge(self):
        ops_name = "fixture.ops.jsonl"
        ops_lines = ['{"operation_id": "op-1"}', '{"operation_id": "op-2"}',
                     '{"operation_id": "op-3"}']
        (self.gov / ops_name).write_text("\n".join(ops_lines) + "\n",
                                         encoding="utf-8")
        code, payload = _bootstrap_cli(self.root)  # converge: baseline ops
        self.assertEqual(code, 0, payload)
        # a mid-window shift moved the recorded identity away: the open
        # violation's object_id points past EOF, its content is gone
        ledger = {
            "schema_version": wgs.SCHEMA_VERSION, "tool": wgs.TOOL_ID,
            "updated_at": None,
            "violations": {
                _BOOT_VIOLATION_ID: {
                    "violation_id": _BOOT_VIOLATION_ID,
                    "family": ops_name,
                    "object_id": "5",
                    "before_hash": None,
                    "after_hash": _row_digest32(
                        '{"operation_id": "op-gone"}'),
                    "workflow_run_id": "run-fixture",
                    "hook_identity": wgs.GUARD_CLI_IDENTITY,
                    "first_seen": "2026-09-24T10:00:00",
                    "occurrence": 1,
                    "status": "open",
                    "grant_id": None,
                    "consumption_event": None,
                },
            },
            "grants": {},
            "pending_txn": None,
        }
        (self.gov / _BOOT_LEDGER_FILE).write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 1, report)
        self.assertIn("ledger_no_drift", report["not_converged"])
        self.assertEqual(len(report["ledger_drift"]), 1, report)
        self.assertEqual(report["ledger_drift"][0]["violation_id"],
                         _BOOT_VIOLATION_ID)
        # the chain converge consumes the drifted record (its identity no
        # longer reproduces — the eligibility rule judges it consumable)
        code, payload = _bootstrap_run(self.root, cc.new_closure_id())
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready", payload)
        ledger_after = json.loads((self.gov / _BOOT_LEDGER_FILE)
                                  .read_text(encoding="utf-8"))
        self.assertEqual(
            ledger_after["violations"][_BOOT_VIOLATION_ID]["status"],
            "consumed")
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["converged"], report)
        self.assertEqual(report["ledger_drift"], [])

    # ── fail-closed: R6 corrupt ledger halts loudly, zero absorption ────

    def test_corrupt_ledger_blocks_loudly_with_zero_ledger_writes(self):
        (self.gov / _BOOT_LEDGER_FILE).write_text("{not json",
                                                  encoding="utf-8")
        ledger_before = (self.gov / _BOOT_LEDGER_FILE).read_bytes()
        code, payload = _bootstrap_run(self.root, self.closure_id)
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["status"], "blocked", payload)
        by_id = {s["step_id"]: s for s in payload["steps"]}
        self.assertEqual(by_id["write-guard-converge"]["status"], "failed")
        self.assertEqual(by_id["write-guard-converge"].get("code"),
                         "manual_intervention")
        # R6: the corrupt ledger is never absorbed or rewritten here —
        # recovery is manual per rule, disclosed not silent
        self.assertEqual((self.gov / _BOOT_LEDGER_FILE).read_bytes(),
                         ledger_before)
        # the world check says the same thing on its own face
        code, report = _bootstrap_cli(self.root, "--check-only")
        self.assertEqual(code, 1, report)
        self.assertIn("violation_ledger_healthy", report["not_converged"])


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-062 — closure cancellation vertical slice (arch Q5 minimal slice,
# rollback-0.86.0 §8 #5 清偿; seven-scenario acceptance + F-5④ combination)
# ═══════════════════════════════════════════════════════════════════════════

OTHER_TASK = "FEAT-902"

_CANCEL_FLIP_SPEC = {
    "chain_id": "cancel-fixture",
    "steps": [
        {
            "step_id": "flip",
            "kind": "cli",
            "argv": [
                "{python}", "{tru_cli}",
                "--task", "{task}",
                "--from", "approved", "--to", "completed",
                "--reason", "cancel fixture flip step（machine via "
                            "task-row-update）",
                "--operation-id", "{op:flip}",
                "--file", "{input:tracker_file}",
                "--json",
            ],
            "probe": {
                "kind": "task_row_state",
                "file": "{input:tracker_file}",
                "task": "{task}",
                "expect": "completed",
            },
            "dry_run_flag": "--dry-run",
        },
        {
            "step_id": "halt",
            "kind": "cli",
            "argv": ["{python}", "-c", "import sys; sys.exit(2)"],
            "dry_run_flag": "--dry-run",
        },
        {"step_id": "end", "kind": "summary"},
    ],
}
"""A closure that completes ONE governed step (the flip) then blocks —
the cancellation's retained-effects + reconciliation fixture."""

_CANCEL_EXTERNAL_SPEC = {
    "chain_id": "cancel-fixture-external",
    "steps": [
        {
            "step_id": "outside",
            "kind": "external",
            "argv": ["{python}", "-c", "print('outside effect')"],
            "timeout_seconds": 30,
        },
        {"step_id": "end", "kind": "summary"},
    ],
}
"""A closure whose external step COMPLETED — cancellation must refuse
explicitly (有副作用明确拒绝; the standard production chain carries no
external steps, the kind is fixture-only, same as the chaos specs)."""

_DEC_SEED = (
    "# 决策记录\n\n"
    "| 编号 | 日期 | 决策人 | 决策内容 | 依据 |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| DEC-50 | 2026-09-01 | Coordinator | seed 行（fixture 基线，"
    "非真实决策面） | seed |\n")

_GUARD_BASELINE_TARGET = {
    "schema_version": 1,
    "tool": "governance-write-guard/row-family-reconciliation",
    "updated_at": "2026-09-25T00:00:00",
    "files": {},
}


class _CancellationFixture(_WorkspaceFixture):
    """Cancellation fixtures: a writer-compatible decision log + a second
    task's dispatch locks (the only-own-locks control)."""

    def setUp(self):
        super().setUp()
        (self.gov / "decision-log.md").write_text(_DEC_SEED,
                                                  encoding="utf-8")
        locks = self.locks_json()
        locks["active_tasks"][OTHER_TASK] = {
            "agent_role": "Developer",
            "spawned_at": "2026-09-20T10:00:00",
            "coordinator_session": "fixture-session-b",
            "target_files": ["fixture/b.md"],
            "description": "other task control lock",
            "acquired": "2026-09-20T10:00:00",
            "files": ["fixture/b.md"],
        }
        locks["file_locks"]["fixture/b.md"] = {
            "locked_by": OTHER_TASK,
            "locked_at": "2026-09-20T10:00:00",
            "ttl_seconds": 14400,
            "ttl_reason": "other task control lock",
        }
        (self.gov / "agent-locks.json").write_text(
            json.dumps(locks, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8")

    def _resume_cli_argv(self, spec_path, closure_id):
        """Full resume CLI argv — the chain's recorded inputs MUST be
        replayed (closure identity = inputs digest)."""
        argv = [sys.executable, str(CC_PATH), "--project-root",
                str(self.root), "run", "--spec", str(spec_path),
                "--task", TASK, "--closure-id", closure_id]
        for key, value in EVD_INPUTS.items():
            argv += ["--input", "{0}={1}".format(key, value)]
        return argv

    def _run_spec(self, spec, closure_id=None):
        return cc.run_chain(
            cc.parse_chain_spec(json.loads(json.dumps(spec))),
            root=self.root, task=TASK, inputs=dict(EVD_INPUTS),
            closure_id=closure_id or self.closure_id)

    def _make_blocked_closure(self, closure_id=None):
        payload = self._run_spec(_CANCEL_FLIP_SPEC, closure_id)
        self.assertEqual(payload["status"], "blocked", payload)
        return payload

    def _cancel(self, *args):
        return _run_cli(self.root, "cancel", "--closure-id",
                        self.closure_id, *args)

    def _gov_snapshot(self):
        """Byte snapshot of .governance minus the run-lock bookkeeping
        (closure-locks/ is the loop_event_log lock-file precedent — its
        mere creation is not a governance write)."""
        return {rel: data for rel, data in
                _snapshot_tree(self.gov).items()
                if not rel.startswith("closure-locks")}

    def _ops_ledger(self):
        path = self.gov / "governance-store-ops.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8")).get(
            "operations", {})

    def _cancel_event(self):
        events = _chain_events(self.root, self.closure_id)
        return next((e for e in events
                     if e["event_type"] == "closure_cancelled"), None)


class CancellationNormalTests(_CancellationFixture):
    """场景 1（正常取消）+ 场景 7（对账）: a blocked closure with one
    completed governed step cancels cleanly — terminal journal event,
    writer-registered DEC row, own locks released, reconciliation
    consistent, terminal semantics enforced afterwards."""

    def test_normal_cancel_full_semantics_and_reconciliation(self):
        self._make_blocked_closure()
        flips_before = self.tracker_text().count("✅ 完成")
        code, payload = self._cancel(
            "--authorized-by", "test-coordinator",
            "--reason", "票作废：验收口径变更，收口链废弃")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "cancelled")
        self.assertFalse(payload["replayed"])
        self.assertEqual(payload["authorized_by"], "test-coordinator")
        # terminal journal event: valid envelope, seq continuity holds
        event = self._cancel_event()
        self.assertIsNotNone(event)
        self.assertEqual(cc._validate_closure_event(event), [])
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual([], loop_event_log.check_cas_monotonicity(events))
        self.assertEqual(event["payload"]["observed_status"], "blocked")
        self.assertEqual(event["payload"]["locks_files"], ["fixture/a.md"])
        # the DEC row registered THROUGH the writer (machine provenance)
        dec_op = payload["operation_ids"]["decision"]
        dec_text = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        self.assertIn("decision-append {0}".format(dec_op), dec_text)
        self.assertIn("test-coordinator", dec_text)
        self.assertIn("closure {0}".format(self.closure_id), dec_text)
        # the ops ledger carries BOTH cancellation ops (可审计)
        ops = self._ops_ledger()
        self.assertEqual(ops[dec_op]["status"], "ok")
        locks_op = payload["operation_ids"]["locks"]
        self.assertIsNotNone(locks_op)
        self.assertEqual(ops[locks_op]["status"], "ok")
        # own locks released; the other task's locks are untouched
        locks = self.locks_json()
        self.assertNotIn(TASK, locks["active_tasks"])
        self.assertNotIn("fixture/a.md", locks["file_locks"])
        self.assertIn(OTHER_TASK, locks["active_tasks"])
        self.assertIn("fixture/b.md", locks["file_locks"])
        # retained effects: the completed flip STAYS (append-only audit)
        self.assertEqual(payload["retained_effects"]["completed_steps"],
                         ["flip"])
        self.assertEqual(self.tracker_text().count("✅ 完成"), flips_before)
        self.assertTrue(payload["retained_effects"]["task_row"]["found"])
        # reconciliation verdict: consistent (场景 7 对账)
        self.assertTrue(payload["reconciliation"]["consistent"],
                        payload["reconciliation"])
        self.assertTrue(payload["reconciliation"]["decision_row_in_world"])
        self.assertTrue(payload["reconciliation"]["locks_world_clear"])

    def test_terminal_semantics_after_cancel(self):
        """DEC/EVD/任务终态语义 (ticket point 4): cancelled = terminal —
        resume refuses, finalize refuses, status reports the terminal."""
        self._make_blocked_closure()
        code, _ = self._cancel("--authorized-by", "test-coordinator",
                               "--reason", "终态语义验证")
        self.assertEqual(code, 0)
        # resume refused (terminal semantics — asserted on the message, not
        # just the code, so a digest-mismatch refusal can't masquerade)
        spec_path = _write_fixture_spec(self.root, "spec.json",
                                        _CANCEL_FLIP_SPEC)
        proc = subprocess.run(
            self._resume_cli_argv(spec_path, self.closure_id),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), cwd=str(self.root),
            timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        refused = json.loads(proc.stdout)
        self.assertEqual(refused["code"], "schema_violation")
        self.assertIn("CANCELLED", refused["detail"])
        # finalize refused
        code, refused = _run_cli(self.root, "finalize",
                                 "--closure-id", self.closure_id,
                                 "--commit-sha", "deadbee")
        self.assertEqual(code, 2, refused)
        self.assertEqual(refused["code"], "cross_record_violation")
        # status reports the terminal + the recorded authorization
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertEqual(status["status"], "cancelled")
        self.assertEqual(status["cancellation"]["authorized_by"],
                         "test-coordinator")


class CancellationEntryGateTests(_CancellationFixture):
    """限定入口: 无权取消（未授权零变化）/ 不可取消状态 / 有副作用明确
    拒绝 / undetermined world / 在途写冲突 — every gate is a ZERO-WRITE
    structured refusal."""

    def test_unauthorized_zero_state_change(self):
        """场景 6（未授权零变化）: missing authorizer/reason →
        schema_violation, .governance byte-identical."""
        self._make_blocked_closure()
        before = self._gov_snapshot()
        # missing flag → argparse usage error (exit 2, zero writes)
        code, payload = self._cancel("--reason", "r")
        self.assertEqual(code, 2, payload)
        self.assertNotIn("error", payload)   # usage error, not JSON refusal
        # empty authorizer/reason → structured schema_violation refusal
        for args in (["--authorized-by", ""],
                     ["--authorized-by", "   "]):
            code, payload = self._cancel(*args, "--reason", "r")
            self.assertEqual(code, 2, payload)
            self.assertEqual(payload.get("code"), "schema_violation", payload)
        # missing --reason → argparse usage error (exit 2, zero writes)
        code, payload = self._cancel("--authorized-by", "test-coordinator")
        self.assertEqual(code, 2, payload)
        self.assertNotIn("error", payload)
        # newline injection refused (writer row cells are single-line)
        code, payload = self._cancel("--authorized-by", "a\nb",
                                     "--reason", "r")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload.get("code"), "schema_violation", payload)
        self.assertEqual(self._gov_snapshot(), before)
        self.assertIsNone(self._cancel_event())

    def test_unknown_closure_refused_zero_writes(self):
        fresh = cc.new_closure_id()
        before = self._gov_snapshot()
        code, payload = _run_cli(self.root, "cancel", "--closure-id", fresh,
                                 "--authorized-by", "test-coordinator",
                                 "--reason", "no such closure")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["code"], "cross_record_violation", payload)
        self.assertEqual(self._gov_snapshot(), before)

    def test_finalized_closure_not_cancellable(self):
        """场景 4（不可取消状态）: finalized = immutable terminal."""
        self._run_spec(cc.STANDARD_TICKET_CLOSURE)
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m", "closure commit")
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        before = self._gov_snapshot()
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "too late")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["code"], "cross_record_violation", payload)
        self.assertIn("FINALIZED", payload["detail"])
        self.assertEqual(self._gov_snapshot(), before)

    def test_external_side_effects_refuse_explicitly(self):
        """场景 7（有副作用明确拒绝）: an external-step terminal event
        makes the closure un-cancellable in the minimal slice."""
        self._run_spec(_CANCEL_EXTERNAL_SPEC)
        events = _chain_events(self.root, self.closure_id)
        self.assertTrue(any(e["event_type"] == "step_completed"
                            for e in events))
        before = self._gov_snapshot()
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "outside effect present")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["code"], "manual_intervention", payload)
        self.assertIn("external-step", payload["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertIsNone(self._cancel_event())

    def test_undetermined_step_refuses_until_world_converges(self):
        """A dangling step_started (crash window) = undetermined effect —
        resume-first protocol, then cancel succeeds."""
        log_path = cc.default_event_log_path(self.root)
        merged = dict(cc._REQUIRED_INPUT_DEFAULTS)
        merged.update(EVD_INPUTS)
        merged["tracker_file"] = str(
            self.root / ".governance" / "plan-tracker.md")
        seq, prev = 1, None
        cc._append_closure_event(
            log_path, self.closure_id, "closure_started", seq, prev,
            {"chain_id": "cancel-fixture", "task": TASK,
             "inputs_digest": cc._inputs_digest(merged),
             "inputs": dict(sorted(merged.items())),
             "code_revision": None})
        cc._append_closure_event(
            log_path, self.closure_id, "step_started", seq + 1, seq,
            {"step_id": "flip", "kind": "cli"})
        before = self._gov_snapshot()
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "crash window open")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["code"], "manual_intervention", payload)
        self.assertIn("undetermined", payload["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        # resume-first protocol: converging the world unlocks the cancel
        # (the dangling CLI step's probe misses → re-execution → the halt
        # step blocks → cancellable blocked world)
        spec_path = _write_fixture_spec(self.root, "spec.json",
                                        _CANCEL_FLIP_SPEC)
        proc = subprocess.run(
            self._resume_cli_argv(spec_path, self.closure_id),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), cwd=str(self.root),
            timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertEqual(json.loads(proc.stdout)["status"], "blocked")
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "world converged")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "cancelled", payload)

    def test_in_flight_write_conflict_is_retryable_zero_write(self):
        """在途写冲突: an in-flight chain holds the closure run lock — the
        cancel refuses lock_contention (retryable) with zero changes."""
        self._make_blocked_closure()
        before = self._gov_snapshot()
        lock_path = (self.gov / "closure-locks"
                     / (self.closure_id + ".lock"))
        with cc._RunLock(lock_path, 1.0):
            proc = subprocess.Popen(
                [sys.executable, str(CC_PATH), "--project-root",
                 str(self.root), "cancel", "--closure-id", self.closure_id,
                 "--authorized-by", "test-coordinator", "--reason",
                 "while a chain is in flight", "--lock-timeout", "0.5"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", errors="replace", env=_clean_env(),
                cwd=str(self.root))
            out, _err = proc.communicate(timeout=120)
        self.assertEqual(proc.returncode, 3, out)
        payload = json.loads(out)
        self.assertEqual(payload["code"], "lock_contention", payload)
        self.assertEqual(payload["disposition"], "retryable")
        self.assertEqual(self._gov_snapshot(), before)
        self.assertIsNone(self._cancel_event())

    def test_pipe_character_refused_at_zero_write_gate(self):
        """review-FEAT-062-R0 F-1 (红绿): a raw '|' in reason/authorized_by
        would make the DEC row deterministically unwritable → the leg
        permanently pending (non-convergent). The entry gate refuses it
        with ZERO changes, same class as newlines — 红相判据：任何放行管
        道符进入写腿的实现都产生永久 pending 的取消（破坏中断恢复必收敛）."""
        self._make_blocked_closure()
        before = self._gov_snapshot()
        for args in (["--authorized-by", "test-coordinator",
                      "--reason", "a|b"],
                     ["--authorized-by", "coord|session",
                      "--reason", "r"]):
            code, payload = self._cancel(*args)
            self.assertEqual(code, 2, payload)
            self.assertEqual(payload.get("code"), "schema_violation", payload)
            self.assertIn("|", payload.get("detail", ""))
        self.assertEqual(self._gov_snapshot(), before)
        self.assertIsNone(self._cancel_event())


class CancellationCasTests(_CancellationFixture):
    """CAS 取消: expected-status CAS + cancel×finalize 竞争单终态
    （the run lock is the linearization point — exactly ONE terminal)."""

    def test_expect_status_cas_mismatch_returns_observed(self):
        self._make_blocked_closure()
        before = self._gov_snapshot()
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "cas probe",
                                     "--expect-status", "ready")
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload["code"], "revision_conflict", payload)
        self.assertEqual(payload["observed_status"], "blocked")
        self.assertEqual(self._gov_snapshot(), before)
        # matching CAS proceeds
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "cas match",
                                     "--expect-status", "blocked")
        self.assertEqual(code, 0, payload)

    def test_cancel_finalize_race_single_terminal(self):
        """场景 3（竞争单终态）: two processes race cancel vs finalize —
        exactly one terminal event lands, the loser refuses (exit 2)."""
        self._make_blocked_closure()
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        cancel_proc = subprocess.Popen(
            [sys.executable, str(CC_PATH), "--project-root", str(self.root),
             "cancel", "--closure-id", self.closure_id, "--authorized-by",
             "test-coordinator", "--reason", "race cancel"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=_clean_env(),
            cwd=str(self.root))
        finalize_proc = subprocess.Popen(
            [sys.executable, str(CC_PATH), "--project-root", str(self.root),
             "finalize", "--closure-id", self.closure_id,
             "--commit-sha", sha],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=_clean_env(),
            cwd=str(self.root))
        cancel_out, _ = cancel_proc.communicate(timeout=300)
        finalize_out, _ = finalize_proc.communicate(timeout=300)
        cancel_payload = json.loads(cancel_out)
        finalize_payload = json.loads(finalize_out)
        events = _chain_events(self.root, self.closure_id)
        terminals = [e["event_type"] for e in events
                     if e["event_type"] in ("closure_cancelled",
                                            "closure_finalized")]
        self.assertEqual(len(terminals), 1, terminals)
        # exactly one winner (exit 0); the loser is a structured refusal
        winners = [p for p, c in ((cancel_payload, cancel_proc.returncode),
                                  (finalize_payload,
                                   finalize_proc.returncode))
                   if c == 0]
        self.assertEqual(len(winners), 1)
        loser_codes = [c for c in (cancel_proc.returncode,
                                   finalize_proc.returncode) if c != 0]
        self.assertEqual(loser_codes, [2])
        if terminals == ["closure_cancelled"]:
            self.assertEqual(finalize_payload["code"],
                             "cross_record_violation",
                             finalize_payload)
        else:
            self.assertEqual(cancel_payload["code"],
                             "cross_record_violation", cancel_payload)


class CancellationCliRefusalTests(_CancellationFixture):
    """review-FEAT-062-R0 F-2/F-3: the CLI face never leaks a bare
    traceback — finalize lock contention is a structured retryable refusal
    (F-2), and a malformed closure id is a structured validation refusal on
    BOTH cancel and finalize (F-3)."""

    def test_finalize_lock_contention_structured_refusal(self):
        """F-2 (红绿): a cancel holding the run lock (writer legs in
        flight) exhausts finalize's lock budget — structured
        lock_contention (retryable, exit 3), never a traceback."""
        self._make_blocked_closure()
        lock_path = (self.gov / "closure-locks"
                     / (self.closure_id + ".lock"))
        with cc._RunLock(lock_path, 1.0):
            proc = subprocess.Popen(
                [sys.executable, str(CC_PATH), "--project-root",
                 str(self.root), "finalize", "--closure-id",
                 self.closure_id, "--commit-sha", "deadbee"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", errors="replace", env=_clean_env(),
                cwd=str(self.root))
            out, err = proc.communicate(timeout=120)
        self.assertNotIn("Traceback", err)
        self.assertEqual(proc.returncode, 3, out)
        payload = json.loads(out)
        self.assertEqual(payload["code"], "lock_contention", payload)
        self.assertEqual(payload["disposition"], "retryable")
        # the journal is untouched by the refused finalize
        events = _chain_events(self.root, self.closure_id)
        self.assertFalse(any(e["event_type"] == "closure_finalized"
                             for e in events))

    def test_malformed_closure_id_structured_refusal(self):
        """F-3 (红绿): a malformed closure id → schema_violation JSON on
        cancel AND finalize, never a bare ValueError traceback."""
        for sub, extra in (
                ("cancel", ["--authorized-by", "test-coordinator",
                            "--reason", "r"]),
                ("finalize", ["--commit-sha", "deadbee"])):
            proc = subprocess.run(
                [sys.executable, str(CC_PATH), "--project-root",
                 str(self.root), sub, "--closure-id", "not-a-closure-id"]
                + list(extra),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=_clean_env(), cwd=str(self.root),
                timeout=300)
            self.assertNotIn("Traceback", proc.stderr, proc.stderr[-400:])
            self.assertEqual(proc.returncode, 2, proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("code"), "schema_violation", payload)


class CancellationIdempotencyTests(_CancellationFixture):
    """场景 2（幂等重试/重放）: the same cancel command replays — zero new
    journal events, zero new DEC rows, zero new ops entries."""

    def test_replay_is_zero_new_events_and_rows(self):
        self._make_blocked_closure()
        code, first = self._cancel("--authorized-by", "test-coordinator",
                                   "--reason", "first cancel")
        self.assertEqual(code, 0, first)
        events_after_first = len(_chain_events(self.root, self.closure_id))
        ops_after_first = sorted(self._ops_ledger())
        dec_text_after_first = (self.gov / "decision-log.md") \
            .read_text(encoding="utf-8")
        # replay with DIFFERENT caller args — the recorded authorization
        # stands; the legs converge at the writers, nothing is re-recorded
        code, second = self._cancel("--authorized-by", "someone-else",
                                    "--reason", "retry with other args")
        self.assertEqual(code, 0, second)
        self.assertTrue(second["replayed"])
        self.assertEqual(second["authorized_by"], "test-coordinator")
        self.assertEqual(len(_chain_events(self.root, self.closure_id)),
                         events_after_first)
        self.assertEqual(sorted(self._ops_ledger()), ops_after_first)
        self.assertEqual((self.gov / "decision-log.md")
                         .read_text(encoding="utf-8"),
                         dec_text_after_first)
        self.assertTrue(second["reconciliation"]["consistent"])


class CancellationInterruptionTests(_CancellationFixture):
    """场景 5（中断恢复）: a crash/refusal between the terminal event and a
    writer leg leaves the leg pending — re-running the SAME command
    converges with zero manual repair (deterministic op ids → replay)."""

    def test_locks_leg_contention_converges_on_retry(self):
        self._make_blocked_closure()
        locks_path = self.gov / "agent-locks.json"
        with gstore_target_lock(locks_path):
            code, payload = self._cancel(
                "--authorized-by", "test-coordinator",
                "--reason", "interrupted release",
                "--writer-timeout", "2")
        self.assertEqual(code, 3, payload)      # pending leg → retryable
        self.assertEqual(payload["status"], "cancelled")
        self.assertEqual(payload["legs"]["decision"]["state"], "done")
        self.assertEqual(payload["legs"]["locks"]["state"], "pending")
        self.assertFalse(payload["reconciliation"]["consistent"])
        self.assertIsNotNone(self._cancel_event())   # terminal already in
        # the locks are STILL held (the leg never landed)
        self.assertIn("fixture/a.md", self.locks_json()["file_locks"])
        # converge: re-run the SAME command after the holder goes away
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "converge retry")
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["replayed"])
        self.assertIn(payload["legs"]["locks"]["state"],
                      ("done", "done_replayed"))
        self.assertTrue(payload["reconciliation"]["consistent"])
        self.assertNotIn("fixture/a.md", self.locks_json()["file_locks"])

    def test_decision_leg_refusal_converges_on_retry(self):
        self._make_blocked_closure()
        # degenerate decision world: the writer refuses (empty hot file)
        (self.gov / "decision-log.md").write_bytes(b"")
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "dec leg pending")
        self.assertEqual(code, 3, payload)
        self.assertEqual(payload["legs"]["decision"]["state"], "pending")
        self.assertEqual(payload["legs"]["locks"]["state"], "done")
        self.assertFalse(payload["reconciliation"]["consistent"])
        # repair the world, then converge — the DEC row lands exactly once
        (self.gov / "decision-log.md").write_text(_DEC_SEED,
                                                  encoding="utf-8")
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "converge retry")
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["replayed"])
        self.assertEqual(payload["legs"]["decision"]["state"], "done")
        self.assertTrue(payload["reconciliation"]["consistent"])
        dec_op = payload["operation_ids"]["decision"]
        dec_text = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        self.assertEqual(dec_text.count("decision-append {0}".format(
            dec_op)), 1)


class CancellationLockOwnershipTests(_CancellationFixture):
    """仅释放自有锁 (ARCH-09 same-type): only the closure task's own locks
    are released; ownership changed / other-owner locks are never
    released by a stale cancel."""

    def test_releases_only_own_locks(self):
        self._make_blocked_closure()
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "own locks only")
        self.assertEqual(code, 0, payload)
        locks = self.locks_json()
        self.assertNotIn(TASK, locks["active_tasks"])
        self.assertNotIn("fixture/a.md", locks["file_locks"])
        self.assertIn(OTHER_TASK, locks["active_tasks"])
        other_entry = locks["file_locks"]["fixture/b.md"]
        self.assertEqual(other_entry["locked_by"], OTHER_TASK)

    def test_ownership_changed_lock_not_released(self):
        """锁所有权变化不误释放: the file lock now belongs to ANOTHER task
        (fresh world read) — the cancel releases the task's active entry
        but never the newer owner's file lock."""
        self._make_blocked_closure()
        locks = self.locks_json()
        locks["file_locks"]["fixture/a.md"]["locked_by"] = OTHER_TASK
        (self.gov / "agent-locks.json").write_text(
            json.dumps(locks, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8")
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "stale owner")
        self.assertEqual(code, 0, payload)
        locks_after = self.locks_json()
        self.assertNotIn(TASK, locks_after["active_tasks"])
        released = locks_after["file_locks"]["fixture/a.md"]
        self.assertEqual(released["locked_by"], OTHER_TASK)
        # the terminal event recorded the ownership world it SAW: no file
        # locks owned by the task, but its active_tasks entry was held
        event = self._cancel_event()
        self.assertEqual(event["payload"]["locks_files"], [])
        self.assertTrue(event["payload"]["locks_held"])

    def test_no_locks_held_skips_the_locks_op(self):
        self._make_blocked_closure()
        locks = self.locks_json()
        locks["active_tasks"].pop(TASK)
        locks["file_locks"].pop("fixture/a.md")
        (self.gov / "agent-locks.json").write_text(
            json.dumps(locks, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8")
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "nothing to release")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["legs"]["locks"]["state"],
                         "skipped_no_locks")
        self.assertIsNone(payload["operation_ids"]["locks"])
        self.assertEqual(
            sorted(self._ops_ledger()),
            [payload["operation_ids"]["decision"]])
        self.assertTrue(payload["reconciliation"]["consistent"])


class CancellationGuardCombinationTests(_CancellationFixture):
    """F-5④ 组合测试 (version-plan §3 ④): closure 取消期间的 locks-release
    × guard 消费权并发 — both writers run CONCURRENTLY; the consumption
    right stays the registered guard CLI's exclusive property (the cancel
    never touches the violations ledger), each terminal state lands
    exactly once, and both worlds stay consistent."""

    def test_cancel_locks_release_vs_guard_consumption_concurrent(self):
        # thread-local import: keeps the module import block byte-identical
        # (STATIC_PIN_EXEMPTIONS keys line numbers on this file)
        import threading  # noqa: E402
        # seed one open guard violation + the CLI consumer's grant
        detection = wgs.build_detection(
            wgs.FAMILY_EVIDENCE, "text", "EVD-9001",
            ".governance/evidence-log.md", 2, "| EVD-9001 | bare row |",
            "a" * 32)
        issues, _changed = wgs.record_detections(
            self.gov, [detection], run_id="run-f54",
            hook_identity=wgs.GUARD_CLI_IDENTITY)
        self.assertEqual(issues, [])
        grant_id, grant_issues = wgs.ensure_grant(
            self.gov, consumer=wgs.CLI_CONSUMER, run_id="run-f54")
        self.assertEqual(grant_issues, [])
        ledger = json.loads((self.gov / wgs.LEDGER_FILE_NAME)
                            .read_text(encoding="utf-8"))
        violation_ids = sorted(ledger["violations"])
        self.assertEqual(len(violation_ids), 1)
        state_path = self.gov / ".write-guard-state.json"
        # a blocked closure with held locks; then BOTH writers at once
        self._make_blocked_closure()
        guard_result = {}

        def guard_consumes():
            guard_result["payload"] = wgs.consume_violations(
                self.gov, state_path, consumer=wgs.CLI_CONSUMER,
                grant_id=grant_id, violation_ids=violation_ids,
                baseline_target=_GUARD_BASELINE_TARGET, run_id="run-f54")

        thread = threading.Thread(target=guard_consumes)
        thread.start()
        payload = cc.cancel_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="F-5④ combination: locks-release vs guard consumption")
        thread.join()
        # guard side: consumed exactly once, by the REGISTERED consumer
        self.assertTrue(guard_result["payload"]["ok"],
                        guard_result["payload"])
        ledger_after = json.loads((self.gov / wgs.LEDGER_FILE_NAME)
                                  .read_text(encoding="utf-8"))
        record = ledger_after["violations"][violation_ids[0]]
        self.assertEqual(record["status"], "consumed")
        self.assertEqual(record["consumption_event"]["consumer"],
                         wgs.CLI_CONSUMER)
        self.assertIsNone(ledger_after["pending_txn"])
        second = wgs.consume_violations(
            self.gov, state_path, consumer=wgs.CLI_CONSUMER,
            grant_id=grant_id, violation_ids=violation_ids,
            baseline_target=_GUARD_BASELINE_TARGET, run_id="run-f54")
        self.assertFalse(second["ok"])
        self.assertEqual(second["error"], "grant_used")   # single-use R5
        # cancel side: terminal + both writer legs done + consistent
        self.assertEqual(payload["status"], "cancelled", payload)
        self.assertTrue(payload["reconciliation"]["consistent"],
                        payload["reconciliation"])
        self.assertEqual(payload["legs"]["decision"]["state"], "done")
        self.assertIn(payload["legs"]["locks"]["state"],
                      ("done", "done_replayed"))
        # the two writers' shared world: agent-locks valid, own locks
        # released, the other owner's locks intact
        locks = self.locks_json()
        self.assertNotIn("fixture/a.md", locks["file_locks"])
        self.assertIn("fixture/b.md", locks["file_locks"])
        # single terminal per domain: the closure journal is terminal, the
        # violation is consumed, the grant is used — exactly once each
        events = _chain_events(self.root, self.closure_id)
        self.assertEqual(
            sum(1 for e in events
                if e["event_type"] == "closure_cancelled"), 1)


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-063 — closure reopen (attempt lineage) + execution-generation
# fencing (0.88.0 阶段 E2; rollback-0.86.0 §8 #5 清偿后半)
# ═══════════════════════════════════════════════════════════════════════════

_FENCE_STEP_SPEC = {
    "chain_id": "fence-fixture",
    "steps": [
        {
            "step_id": "write-one",
            "kind": "cli",
            "argv": ["{python}", "-c",
                     "import pathlib,sys; "
                     "pathlib.Path(sys.argv[1]).write_text("
                     "'one', encoding='utf-8')",
                     "{input:marker_one}"],
            "dry_run_flag": None,
        },
        {
            "step_id": "write-two",
            "kind": "cli",
            "argv": ["{python}", "-c",
                     "import pathlib,sys; "
                     "pathlib.Path(sys.argv[1]).write_text("
                     "'two', encoding='utf-8')",
                     "{input:marker_two}"],
            "dry_run_flag": None,
        },
        {"step_id": "end", "kind": "summary"},
    ],
}
"""Two observable cli steps — the per-step fence re-check fixture: the
fault point pauses after write-one lands, the world is re-bound
out-of-band, and write-two's write boundary must refuse."""


class ReopenLineageTests(_CancellationFixture):
    """重开 = 保留原 closure + 新尝试编号关联（不擦历史）: the terminal
    original only GAINS one closure_reopened event; the successor binds
    the RECORDED linkage via --reopen-of; single-successor lineage."""

    def _cancel_ok(self, reason):
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", reason)
        self.assertEqual(code, 0, payload)
        return payload

    def test_reopen_cancelled_records_linkage_zero_erasure(self):
        self._make_blocked_closure()
        self._cancel_ok("取消旧链")
        events_before = _chain_events(self.root, self.closure_id)
        payload = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="验收口径变更后重开")
        self.assertEqual(payload["status"], "reopened", payload)
        successor = payload["successor_closure_id"]
        cc.require_closure_id("successor", successor)
        self.assertEqual(payload["reopen_attempt"], 2)
        self.assertEqual(payload["prior_status"], "cancelled")
        self.assertTrue(payload["original_records_preserved"])
        # the suggested run argv carries the recorded binding
        self.assertIsInstance(payload["run_argv"], list)
        self.assertIn("--reopen-of", payload["run_argv"])
        self.assertIn(successor, payload["run_argv"])
        # append-only: original records are byte-identical (零擦除) and the
        # journal gained exactly ONE seq-continuous closure_reopened event
        events_after = _chain_events(self.root, self.closure_id)
        self.assertEqual(len(events_after), len(events_before) + 1)
        self.assertEqual(events_after[:-1], events_before)
        reopen_event = events_after[-1]
        self.assertEqual(reopen_event["event_type"], "closure_reopened")
        self.assertEqual(cc._validate_closure_event(reopen_event), [])
        self.assertEqual([], loop_event_log.check_cas_monotonicity(
            events_after))
        rp = reopen_event["payload"]
        self.assertEqual(rp["successor_closure_id"], successor)
        self.assertEqual(rp["reopen_attempt"], 2)
        self.assertEqual(rp["prior_status"], "cancelled")
        self.assertEqual(rp["authorized_by"], "test-coordinator")
        # the original stays terminal; the status face discloses the
        # lineage without changing the derived status
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertEqual(status["status"], "cancelled")
        self.assertEqual(status["reopen"]["successor_closure_id"], successor)
        self.assertEqual(status["reopen"]["reopen_attempt"], 2)
        spec_path = _write_fixture_spec(self.root, "spec.json",
                                        _CANCEL_FLIP_SPEC)
        proc = subprocess.run(
            self._resume_cli_argv(spec_path, self.closure_id),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), cwd=str(self.root),
            timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("CANCELLED", json.loads(proc.stdout)["detail"])

    def test_reopen_finalized_closure(self):
        self._run_spec(cc.STANDARD_TICKET_CLOSURE)
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m", "closure commit")
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        payload = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="后续工作另起尝试")
        self.assertEqual(payload["status"], "reopened", payload)
        self.assertEqual(payload["prior_status"], "finalized")
        self.assertEqual(payload["reopen_attempt"], 2)
        # the finalized terminal is untouched — cancel still refuses
        code, refused = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "too late")
        self.assertEqual(code, 2, refused)
        self.assertEqual(refused["code"], "cross_record_violation")

    def test_reopen_requires_terminal_zero_write(self):
        self._make_blocked_closure()          # blocked = non-terminal
        before = self._gov_snapshot()
        payload = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="not terminal yet")
        self.assertEqual(payload["code"], "cross_record_violation", payload)
        self.assertIn("TERMINAL", payload["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertFalse(any(
            e["event_type"] == "closure_reopened"
            for e in _chain_events(self.root, self.closure_id)))

    def test_single_successor_lineage_no_fork(self):
        self._make_blocked_closure()
        self._cancel_ok("第一次取消")
        first = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="first reopen")
        self.assertEqual(first["status"], "reopened", first)
        count = len(_chain_events(self.root, self.closure_id))
        before = self._gov_snapshot()
        second = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="fork attempt")
        self.assertEqual(second["code"], "cross_record_violation", second)
        self.assertIn(first["successor_closure_id"], second["detail"])
        self.assertIn("single-successor", second["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertEqual(len(_chain_events(self.root, self.closure_id)),
                         count)

    def test_successor_binds_recorded_linkage_and_resumes(self):
        self._make_blocked_closure()
        self._cancel_ok("取消旧链")
        opened = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="重开")
        successor = opened["successor_closure_id"]
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        # no --closure-id: the run ADOPTS the recorded successor id
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS),
                               reopen_of=self.closure_id)
        self.assertEqual(payload["closure_id"], successor, payload)
        self.assertEqual(payload["status"], "blocked", payload)
        started = next(e for e in _chain_events(self.root, successor)
                       if e["event_type"] == "closure_started")
        inputs = started["payload"]["inputs"]
        self.assertEqual(inputs["reopen_of"], self.closure_id)
        self.assertEqual(inputs["reopen_attempt"], "2")
        # status face discloses the back-link
        code, status = _run_cli(self.root, "status",
                                "--closure-id", successor)
        self.assertEqual(status["reopen_lineage"],
                         {"reopen_of": self.closure_id,
                          "reopen_attempt": "2"}, status)
        # resume carries the same binding (inputs-digest identity)
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS), closure_id=successor,
                               reopen_of=self.closure_id)
        self.assertEqual(payload["status"], "blocked", payload)
        # resume WITHOUT the binding → digest mismatch refusal
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=successor)
        self.assertIn("digest mismatch", str(ctx.exception))
        # a conflicting fresh reopen_of input refuses (recorded intent)
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS, reopen_of="closure-"
                                      + "f" * 32),
                         closure_id=successor, reopen_of=self.closure_id)
        self.assertIn("conflicting fresh", str(ctx.exception))

    def test_reopen_binding_refusals(self):
        fresh = cc.new_closure_id()
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        # a closure with no journal at all
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), reopen_of=fresh)
        self.assertIn("no journal", str(ctx.exception))
        # a started closure without a recorded reopen event
        self._make_blocked_closure()
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS),
                         reopen_of=self.closure_id)
        self.assertIn("never mints a successor", str(ctx.exception))
        # a recorded linkage stands — a different closure id refuses
        code, _ = self._cancel("--authorized-by", "test-coordinator",
                               "--reason", "取消")
        self.assertEqual(code, 0)
        opened = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="重开")
        self.assertEqual(opened["status"], "reopened", opened)
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=fresh,
                         reopen_of=self.closure_id)
        self.assertIn("recorded successor", str(ctx.exception))

    def test_reopen_field_validation_and_malformed_id(self):
        self._make_blocked_closure()
        self._cancel_ok("取消")
        before = self._gov_snapshot()
        for kwargs in ({"authorized_by": "", "reason": "r"},
                       {"authorized_by": "test-coordinator",
                        "reason": "a\nb"},
                       {"authorized_by": "test-coordinator",
                        "reason": "a|b"}):
            payload = cc.reopen_closure(self.root, self.closure_id,
                                        **kwargs)
            self.assertEqual(payload["code"], "schema_violation", payload)
        self.assertEqual(self._gov_snapshot(), before)
        # malformed closure id → structured refusal, never a traceback
        code, payload = _run_cli(self.root, "reopen", "--closure-id",
                                 "bogus", "--authorized-by", "a",
                                 "--reason", "r")
        self.assertNotIn("Traceback", payload.get("_stderr", ""))
        self.assertEqual(code, 2, payload)
        self.assertEqual(payload.get("code"), "schema_violation", payload)

    def test_attempt_chain_deepens_three_levels(self):
        """P2-1 (review-FEAT-063-R0): the attempt numbering deepens along
        the single-successor lineage — A(1) → S2(2) → S3(3); every hop is
        append-only and the earlier originals stay untouched."""
        self._make_blocked_closure()
        self._cancel_ok("取消 A")
        open1 = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="第一跳")
        self.assertEqual(open1["status"], "reopened", open1)
        self.assertEqual(open1["reopen_attempt"], 2)
        s2 = open1["successor_closure_id"]
        # S2 runs (blocked world) then reaches ITS terminal — the chain
        # deepens by reopening the successor, never by forking A again
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS), closure_id=s2,
                               reopen_of=self.closure_id)
        self.assertEqual(payload["status"], "blocked", payload)
        cancelled = cc.cancel_closure(self.root, s2,
                                      authorized_by="test-coordinator",
                                      reason="S2 终态")
        self.assertEqual(cancelled["status"], "cancelled", cancelled)
        open2 = cc.reopen_closure(self.root, s2,
                                  authorized_by="test-coordinator",
                                  reason="第二跳")
        self.assertEqual(open2["status"], "reopened", open2)
        self.assertEqual(open2["reopen_attempt"], 3)
        s3 = open2["successor_closure_id"]
        self.assertNotEqual(s3, s2)
        # S2's journal carries the full lineage: back-link to A (attempt
        # 2) + the forward reopen event naming S3 (attempt 3)
        events_s2 = _chain_events(self.root, s2)
        started_s2 = next(e for e in events_s2
                          if e["event_type"] == "closure_started")
        self.assertEqual(
            started_s2["payload"]["inputs"]["reopen_of"], self.closure_id)
        self.assertEqual(
            started_s2["payload"]["inputs"]["reopen_attempt"], "2")
        reopens_s2 = [e for e in events_s2
                      if e["event_type"] == "closure_reopened"]
        self.assertEqual(len(reopens_s2), 1)
        self.assertEqual(reopens_s2[0]["payload"]["reopen_attempt"], 3)
        self.assertEqual(reopens_s2[0]["payload"]["successor_closure_id"],
                         s3)
        # A's journal gained exactly ONE reopen event and never changed
        # after it (the later hops live in their own journals)
        events_a = _chain_events(self.root, self.closure_id)
        self.assertEqual(
            sum(1 for e in events_a
                if e["event_type"] == "closure_reopened"), 1)
        self.assertEqual(events_a[-1]["event_type"], "closure_reopened")


class ExecutionGenerationFencingTests(_CancellationFixture):
    """异常接管 = 执行代际/fencing token 写入端校验: after the takeover
    promotes the generation, the OLD executor's writes are refused at the
    write side (旧代际写入被拒). Heartbeat timeout is NEVER a stop proof —
    takeover stands on explicit authorization + the prior holder's run
    lock being free."""

    def test_takeover_fences_stale_holder_writes(self):
        """RED-GREEN core: the stale generation's resume is refused with
        ZERO effects (no probe, no subprocess, no bookkeeping beyond the
        single idempotent closure_fenced audit event)."""
        self._make_blocked_closure()
        stale_id = self.closure_id
        new_holder = cc.new_closure_id()
        tracker_before = (self.gov / "plan-tracker.md").read_bytes()
        evidence_before = (self.gov / "evidence-log.md").read_bytes()
        locks_before = (self.gov / "agent-locks.json").read_bytes()
        events_before = _chain_events(self.root, stale_id)
        payload = cc.takeover_execution(
            self.root, TASK, new_holder, authorized_by="test-operator",
            reason="旧执行者失联，人工接管判定（非心跳超时）")
        self.assertFalse(payload.get("error"), payload)
        self.assertEqual(payload["generation"], 1)     # first takeover
        self.assertIsNone(payload["prior_holder_closure_id"])
        self.assertEqual(payload["holder_closure_id"], new_holder)
        self.assertIn("not a stop proof", payload["fence_note"])
        record = json.loads(
            (self.gov / cc.CLOSURE_GENERATIONS_FILENAME)
            .read_text(encoding="utf-8"))
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["tasks"][TASK]["generation"], 1)
        self.assertEqual(record["tasks"][TASK]["holder_closure_id"],
                         new_holder)
        # GREEN: the stale executor's next run refuses at the fence
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        with self.assertRaises(cc.ExecutionFenced) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=stale_id)
        fence = ctx.exception.payload
        self.assertEqual(fence["code"], "revision_conflict", fence)
        self.assertEqual(fence["disposition"], "conflict")
        self.assertEqual(fence["observed_holder"], new_holder)
        self.assertEqual(fence["observed_generation"], 1)
        self.assertIn("stale generation", fence["detail"])
        self.assertIn("heartbeat", fence["detail"])
        # ZERO effects: the governed world is byte-identical
        self.assertEqual((self.gov / "plan-tracker.md").read_bytes(),
                         tracker_before)
        self.assertEqual((self.gov / "evidence-log.md").read_bytes(),
                         evidence_before)
        self.assertEqual((self.gov / "agent-locks.json").read_bytes(),
                         locks_before)
        # the journal gained exactly ONE idempotent closure_fenced event
        events_after = _chain_events(self.root, stale_id)
        self.assertEqual(len(events_after), len(events_before) + 1)
        self.assertEqual(events_after[-1]["event_type"], "closure_fenced")
        self.assertEqual(events_after[-1]["payload"]["observed_holder"],
                         new_holder)
        with self.assertRaises(cc.ExecutionFenced):
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=stale_id)
        self.assertEqual(len(_chain_events(self.root, stale_id)),
                         len(events_after))     # no second audit event

    def test_takeover_requires_authorization_zero_write(self):
        self._make_blocked_closure()
        before = self._gov_snapshot()
        for kwargs in ({"authorized_by": "", "reason": "r"},
                       {"authorized_by": "test-operator",
                        "reason": "a|b"},
                       {"authorized_by": "test-operator",
                        "reason": "a\nb"}):
            payload = cc.takeover_execution(
                self.root, TASK, cc.new_closure_id(), **kwargs)
            self.assertEqual(payload["code"], "schema_violation", payload)
        self.assertFalse(
            (self.gov / cc.CLOSURE_GENERATIONS_FILENAME).is_file())
        self.assertEqual(self._gov_snapshot(), before)

    def test_takeover_in_flight_refuses_lock_contention(self):
        """An in-flight prior holder (its run lock is held) refuses the
        takeover — no heartbeat/staleness reading is consulted, the lock
        IS the in-flight evidence; zero changes made."""
        self._make_blocked_closure()
        first = cc.takeover_execution(self.root, TASK, self.closure_id,
                                      authorized_by="test-operator",
                                      reason="绑定为在途持有者")
        self.assertFalse(first.get("error"), first)
        before = self._gov_snapshot()
        lock_path = (self.gov / "closure-locks"
                     / (self.closure_id + ".lock"))
        with cc._RunLock(lock_path, 1.0):
            payload = cc.takeover_execution(
                self.root, TASK, cc.new_closure_id(),
                authorized_by="test-operator", reason="in-flight probe",
                lock_timeout=0.5)
        self.assertEqual(payload["code"], "lock_contention", payload)
        self.assertEqual(payload["disposition"], "retryable")
        self.assertIn("in flight", payload["detail"])
        self.assertIn("heartbeat", payload["detail"])
        # zero changes: the record still binds the ORIGINAL holder
        self.assertEqual(self._gov_snapshot(), before)

    def test_new_holder_runs_and_third_closure_fenced(self):
        self._make_blocked_closure()
        holder_b = cc.new_closure_id()
        cc.takeover_execution(self.root, TASK, holder_b,
                              authorized_by="test-operator",
                              reason="接管到 B")
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        # the CURRENT holder runs normally
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS), closure_id=holder_b)
        self.assertEqual(payload["status"], "blocked", payload)
        # a THIRD closure is fenced at fresh start with ZERO writes
        third = cc.new_closure_id()
        before = self._gov_snapshot()
        with self.assertRaises(cc.ExecutionFenced) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=third)
        self.assertEqual(ctx.exception.payload["code"],
                         "revision_conflict")
        self.assertEqual(_chain_events(self.root, third), [])
        self.assertEqual(self._gov_snapshot(), before)
        # re-bind the third closure: generation deepens, prior holder B
        rebound = cc.takeover_execution(self.root, TASK, third,
                                        authorized_by="test-operator",
                                        reason="转绑到 C")
        self.assertFalse(rebound.get("error"), rebound)
        self.assertEqual(rebound["generation"], 2)
        self.assertEqual(rebound["prior_holder_closure_id"], holder_b)
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS), closure_id=third)
        self.assertEqual(payload["status"], "blocked", payload)

    def test_finalize_of_stale_generation_refused(self):
        self._run_spec(cc.STANDARD_TICKET_CLOSURE)
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m", "closure commit")
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        events_before = _chain_events(self.root, self.closure_id)
        cc.takeover_execution(self.root, TASK, cc.new_closure_id(),
                              authorized_by="test-operator", reason="接管")
        refused = cc.finalize_closure(self.root, self.closure_id, sha)
        self.assertTrue(refused.get("error"), refused)
        self.assertEqual(refused["code"], "revision_conflict", refused)
        events_after = _chain_events(self.root, self.closure_id)
        self.assertEqual(len(events_after), len(events_before) + 1)
        self.assertEqual(events_after[-1]["event_type"], "closure_fenced")
        self.assertFalse(any(e["event_type"] == "closure_finalized"
                             for e in events_after))

    def test_cancel_of_stale_generation_skips_locks_release(self):
        """ARCH-09 same-type: a stale owner's cancel records the
        termination but NEVER releases the newer holder's dispatch
        locks."""
        self._make_blocked_closure()
        new_holder = cc.new_closure_id()
        cc.takeover_execution(self.root, TASK, new_holder,
                              authorized_by="test-operator", reason="接管")
        payload = cc.cancel_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="终止被接管的旧执行者")
        self.assertEqual(payload["status"], "cancelled", payload)
        self.assertEqual(payload["legs"]["locks"]["state"],
                         "skipped_fenced", payload)
        self.assertIsNone(payload["operation_ids"]["locks"])
        # the newer holder's dispatch locks stay
        locks = self.locks_json()
        self.assertIn("fixture/a.md", locks["file_locks"])
        self.assertIn(TASK, locks["active_tasks"])
        # termination still records: terminal event + DEC row + verdict
        self.assertIsNotNone(self._cancel_event())
        self.assertEqual(payload["legs"]["decision"]["state"], "done")
        self.assertTrue(payload["reconciliation"]["consistent"],
                        payload["reconciliation"])
        self.assertTrue(payload["reconciliation"]["journal_terminal"])

    def test_generations_record_corrupt_fails_closed(self):
        self._make_blocked_closure()
        (self.gov / cc.CLOSURE_GENERATIONS_FILENAME).write_text(
            "{not json", encoding="utf-8")
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        with self.assertRaises(cc.ExecutionFenced) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS),
                         closure_id=self.closure_id)
        fence = ctx.exception.payload
        self.assertEqual(fence["code"], "revision_conflict", fence)
        self.assertIn("unreadable", fence["detail"])
        takeover = cc.takeover_execution(
            self.root, TASK, cc.new_closure_id(),
            authorized_by="test-operator", reason="corrupt probe")
        self.assertEqual(takeover["code"], "manual_intervention", takeover)
        # repair restores the judgeable world (unbound → unfenced)
        (self.gov / cc.CLOSURE_GENERATIONS_FILENAME).unlink()
        payload = cc.run_chain(spec, root=self.root, task=TASK,
                               inputs=dict(EVD_INPUTS),
                               closure_id=self.closure_id)
        self.assertEqual(payload["status"], "blocked", payload)

    def test_takeover_stale_preread_refused_lock_contention_zero_write(self):
        """P0-1 (review-FEAT-063-R0, 红态注入): T1's pre-read captured
        holder A; T2's full promotion (A→B) lands in the pre-read→lock
        window (the ``post-generations-preread`` fault point); T1's
        in-lock re-read detects the mismatch and refuses with ZERO
        writes — the acquired run lock belonged to a FORMER holder and
        promoting on it would fence the REAL holder's possibly-in-flight
        run (violating the lock_contention invariant)."""
        import threading  # noqa: E402 (local import — byte-stable block)
        self._make_blocked_closure()
        holder_a = self.closure_id
        first = cc.takeover_execution(self.root, TASK, holder_a,
                                      authorized_by="test-operator",
                                      reason="绑定为持有者")
        self.assertFalse(first.get("error"), first)
        holder_b = cc.new_closure_id()
        holder_c = cc.new_closure_id()
        handshake = self.tmpdir / "handshake-p0"
        os.environ[cc.CLOSURE_TEST_FAULT_ENV] = json.dumps({
            "handshake_dir": str(handshake),
            "points": ["post-generations-preread"]})
        result = {}

        def stale_takeover():
            result["payload"] = cc.takeover_execution(
                self.root, TASK, holder_c, authorized_by="test-operator",
                reason="stale pre-read probe")

        thread = threading.Thread(target=stale_takeover)
        thread.start()
        try:
            self.assertTrue(
                _wait_marker(handshake, "post-generations-preread"),
                "T1 never reached the fault point")
            # the window is open: T1's pre-read saw A. Drop the fault env
            # BEFORE T2 so only T1's already-consumed config pauses (T2
            # must run to completion inside the window), then promote B.
            os.environ.pop(cc.CLOSURE_TEST_FAULT_ENV, None)
            second = cc.takeover_execution(
                self.root, TASK, holder_b, authorized_by="test-operator",
                reason="窗口内接管到 B")
            self.assertFalse(second.get("error"), second)
            self.assertEqual(second["generation"], 2)
            self.assertEqual(second["holder_closure_id"], holder_b)
            # the zero-write baseline for T1 = the world AFTER T2's
            # legitimate promotion (T1 must add nothing to it)
            after_t2 = self._gov_snapshot()
        finally:
            _point_marker(handshake, "post-generations-preread") \
                .with_suffix(".release").write_text("go", encoding="utf-8")
            thread.join(timeout=60)
            os.environ.pop(cc.CLOSURE_TEST_FAULT_ENV, None)
        payload = result["payload"]
        self.assertEqual(payload["code"], "lock_contention", payload)
        self.assertEqual(payload["disposition"], "retryable")
        self.assertIn("former holder", payload["detail"])
        self.assertIn("ZERO changes", payload["detail"])
        # zero writes by T1: B's promotion stands untouched
        self.assertEqual(self._gov_snapshot(), after_t2)
        record = json.loads(
            (self.gov / cc.CLOSURE_GENERATIONS_FILENAME)
            .read_text(encoding="utf-8"))
        self.assertEqual(record["tasks"][TASK]["holder_closure_id"],
                         holder_b)
        self.assertEqual(record["tasks"][TASK]["generation"], 2)

    def test_per_step_fence_recheck_refuses_out_of_band_rebind(self):
        """P1-1 (review-FEAT-063-R0): the per-step write-side re-check —
        the OUT-OF-BAND face. Under the takeover path a mid-run fence is
        unreachable (the promotion holds the run lock); this test
        simulates the out-of-band authority change (hand-edit class) via
        the fault-point window: the chain pauses after write-one lands,
        the world is re-bound to another holder, and write-two's write
        boundary refuses — write-one's landed effect STAYS (the fence
        stops at the NEXT write, never reverts)."""
        import threading  # noqa: E402 (local import — byte-stable block)
        executor = cc.new_closure_id()
        first = cc.takeover_execution(self.root, TASK, executor,
                                      authorized_by="test-operator",
                                      reason="绑定为执行者")
        self.assertFalse(first.get("error"), first)
        marker_one = self.root / "marker-one.txt"
        marker_two = self.root / "marker-two.txt"
        handshake = self.tmpdir / "handshake-step"
        os.environ[cc.CLOSURE_TEST_FAULT_ENV] = json.dumps({
            "handshake_dir": str(handshake),
            "points": ["post-step-effect:write-one"]})
        result = {}

        def run_chain_thread():
            try:
                result["payload"] = cc.run_chain(
                    cc.parse_chain_spec(json.loads(json.dumps(
                        _FENCE_STEP_SPEC))),
                    root=self.root, task=TASK,
                    inputs={"marker_one": str(marker_one),
                            "marker_two": str(marker_two)},
                    closure_id=executor)
            except cc.ExecutionFenced as exc:
                result["fenced"] = exc.payload

        thread = threading.Thread(target=run_chain_thread)
        thread.start()
        try:
            self.assertTrue(
                _wait_marker(handshake, "post-step-effect:write-one"),
                "the chain never reached the write-one fault point")
            # OUT-OF-BAND re-bind (hand-edit class — bypasses the takeover
            # path's run-lock serialization by construction)
            record = json.loads(
                (self.gov / cc.CLOSURE_GENERATIONS_FILENAME)
                .read_text(encoding="utf-8"))
            record["tasks"][TASK]["holder_closure_id"] = cc.new_closure_id()
            record["tasks"][TASK]["generation"] += 1
            (self.gov / cc.CLOSURE_GENERATIONS_FILENAME).write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        finally:
            _point_marker(handshake, "post-step-effect:write-one") \
                .with_suffix(".release").write_text("go", encoding="utf-8")
            thread.join(timeout=60)
            os.environ.pop(cc.CLOSURE_TEST_FAULT_ENV, None)
        # write-one's effect landed; write-two never spawned
        self.assertTrue(marker_one.is_file())
        self.assertFalse(marker_two.is_file())
        fence = result.get("fenced")
        self.assertIsNotNone(fence, result)
        self.assertEqual(fence["code"], "revision_conflict", fence)
        self.assertEqual(fence["disposition"], "conflict")
        # journal: write-one completed + ONE idempotent closure_fenced
        events = _chain_events(self.root, executor)
        self.assertEqual(
            sum(1 for e in events if e["event_type"] == "step_completed"
                and (e.get("payload") or {}).get("step_id") == "write-one"),
            1)
        self.assertEqual(
            sum(1 for e in events if e["event_type"] == "closure_fenced"),
            1)
        self.assertFalse(any(e["event_type"] == "step_started"
                             and (e.get("payload") or {}).get("step_id")
                             == "write-two" for e in events))

    def test_same_holder_retakeover_refused_zero_write(self):
        """P1-2 (review-FEAT-063-R0): re-binding the CURRENT holder
        refuses (no takeover needed) — the record is byte-identical."""
        self._make_blocked_closure()
        first = cc.takeover_execution(self.root, TASK, self.closure_id,
                                      authorized_by="test-operator",
                                      reason="首次绑定")
        self.assertFalse(first.get("error"), first)
        record_before = (self.gov / cc.CLOSURE_GENERATIONS_FILENAME) \
            .read_bytes()
        before = self._gov_snapshot()
        again = cc.takeover_execution(self.root, TASK, self.closure_id,
                                      authorized_by="test-operator",
                                      reason="同 holder 重接管")
        self.assertEqual(again["code"], "schema_violation", again)
        self.assertIn("already holds", again["detail"])
        self.assertEqual(
            (self.gov / cc.CLOSURE_GENERATIONS_FILENAME).read_bytes(),
            record_before)
        self.assertEqual(self._gov_snapshot(), before)


def gstore_target_lock(target: Path):
    """A governance-store _TargetLock context (test-side contention
    fixture for the F-5④/interruption scenarios — same lock discipline the
    guard's consumption transaction and the writer CLIs serialize on)."""
    import governance_store as gstore  # noqa: E402 (local composition face)
    return gstore._TargetLock(Path(target), timeout_seconds=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# FIX-391 — closure journal 版本感知读取器 (REL-089 condition-③ closure
# ticket, DEC-241 附带裁定): the rollback runbook's resume/finalize gate
# becomes CODE. A closure whose raw journal carries event type(s) or
# envelope schema_version(s) this reader does not know belongs to a NEWER
# writer — every journal-consuming write entry (run/resume, finalize,
# cancel, reopen) refuses ZERO-WRITE before any recovery side effect
# (preflight over the COMPLETE journal, arch ①). Reads stay fail-safe.
# The writer side carries an anti-occupation backstop so the measured
# seq-collision vector (kept=[1,2] → next=3 while raw 3 is occupied) is
# machine-impossible. Matrix cells pin every old-journal form's behavior
# (红绿逐格). The forged-tombstone negative: a tombstone-SHAPED event of
# an unknown type is refused, never misread as an active closure (the
# DEC-241 discipline stands — no reader ever FABRICATES a known-type
# tombstone to defend an older reader; P1/append-only).
# ═══════════════════════════════════════════════════════════════════════════

_HISTORICAL_EVENT_TYPES = frozenset({
    "closure_started", "step_started", "step_completed", "step_failed",
    "step_unknown", "step_reconciled", "closure_ready",
    "closure_finalized",
})
"""The reader vocabulary BEFORE the terminal/lineage/fence trio landed
(closed enum of 8 types — a historical fact about the journal format's
first release, not a pin of any active version)."""

_FUTURE_TOMBSTONE_TYPE = "closure_voided"
"""A plausible NEWER writer's terminal type — unknown to this reader."""

_FUTURE_LINEAGE_TYPE = "closure_superseded"
"""A plausible NEWER writer's lineage type — unknown to this reader."""


def _raw_closure_event(closure_id, event_type, seq, prev_seq,
                       payload=None, actor="fixture/newer-writer",
                       schema_version=1):
    """Build one raw journal envelope (fixture world — hand-assembled,
    NOT written through the gate; build_event fills id/timestamp)."""
    ev = loop_event_log.build_event(
        closure_id, event_type, cas_version=seq, from_version=prev_seq,
        actor=actor, payload=dict(payload or {}))
    ev["schema_version"] = schema_version
    return ev


def _append_raw_journal_lines(root, events):
    """Hand-append raw JSON lines to the closure journal (the simulation
    of a newer writer's lines landing in a shared journal file)."""
    log_path = cc.default_event_log_path(root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as handle:
        for ev in events:
            handle.write(
                json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")


def _raw_unit_line_count(root, closure_id):
    """Line count for one closure in the RAW journal file — counts every
    parseable line of the unit (known type or not); the zero-write and
    seq-collision probe the kept-view reader cannot provide."""
    log_path = cc.default_event_log_path(root)
    if not log_path.is_file():
        return 0
    count = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict) and ev.get("unit_id") == closure_id:
            count += 1
    return count


def _next_raw_seq(root, closure_id):
    events = _chain_events(root, closure_id)
    return (max(e["cas_version"] for e in events) + 1) if events else 1


class VersionAwareJournalReaderTests(_CancellationFixture):
    """FIX-391 红绿矩阵: the version gate refuses conflicted journals
    zero-write at every write entry; known-vocabulary journals (the
    backward-compat cells) keep flowing exactly as before."""

    def _conflict(self):
        return cc._journal_version_conflict(
            cc.default_event_log_path(self.root), self.closure_id)

    def _make_ready_closure(self, closure_id=None):
        """A standard-chain closure driven to the ready-to-commit state
        (flip → evidence → lock-TTL shrink → summary)."""
        payload = self._run_spec(cc.STANDARD_TICKET_CLOSURE,
                                 closure_id=closure_id or self.closure_id)
        self.assertEqual(payload["status"], "ready", payload)
        return payload

    def _seed_future_tombstone(self):
        """Hand-append the newer-writer tombstone at the true next raw
        seq (the measured 0.87-side misread shape: an invisible terminal
        occupying the seq the kept view would reuse)."""
        seq = _next_raw_seq(self.root, self.closure_id)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(
                self.closure_id, _FUTURE_TOMBSTONE_TYPE, seq, seq - 1,
                {"authorized_by": "newer-writer-operator",
                 "reason": "terminal in a newer vocabulary",
                 "observed_status": "cancelled"})])
        return seq

    # ── vocabulary + preflight units ─────────────────────────────────────

    def test_historical_enum_is_strict_subset_of_live_enum(self):
        """Matrix precondition: the 8-type historical vocabulary is fully
        contained in the live closed enum, and the fixture's future types
        are genuinely unknown to this reader."""
        self.assertTrue(
            _HISTORICAL_EVENT_TYPES <= set(cc.CLOSURE_EVENT_TYPES))
        self.assertEqual(len(_HISTORICAL_EVENT_TYPES), 8)
        for future in (_FUTURE_TOMBSTONE_TYPE, _FUTURE_LINEAGE_TYPE):
            self.assertNotIn(future, cc.CLOSURE_EVENT_TYPES)

    def test_preflight_clean_journals_return_none(self):
        """Matrix cells (backward-compat): a historical-form journal, the
        current-form journal, and a terminal-recorded journal are ALL
        judgeable — the gate stays silent (no false rejection)."""
        self._make_blocked_closure()   # started/step_started/completed/failed
        self.assertIsNone(self._conflict())
        self._make_ready_closure()     # + closure_ready (current vocabulary)
        self.assertIsNone(self._conflict())
        code, payload = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "matrix cell")
        self.assertEqual(code, 0, payload)   # + closure_cancelled
        self.assertIsNone(self._conflict())

    def test_preflight_flags_unknown_event_type(self):
        self._make_blocked_closure()
        self.assertIsNone(self._conflict())
        self._seed_future_tombstone()
        conflict = self._conflict()
        self.assertIsNotNone(conflict)
        self.assertTrue(conflict["error"])
        self.assertEqual(conflict["code"], "schema_violation")
        self.assertEqual(conflict["disposition"], "validation")
        self.assertEqual(conflict["unknown_event_types"],
                         [_FUTURE_TOMBSTONE_TYPE])
        self.assertEqual(conflict["foreign_schema_versions"], [])
        self.assertIn(_FUTURE_TOMBSTONE_TYPE, conflict["detail"])
        self.assertIn("NEWER writer", conflict["detail"])

    def test_preflight_flags_out_of_window_schema_version(self):
        """版本感知 beyond types: a KNOWN type carrying an envelope
        schema_version outside the supported window is a conflict too
        (refuse foreign/newer schemas, never guess — the window face)."""
        self._make_blocked_closure()
        seq = _next_raw_seq(self.root, self.closure_id)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(self.closure_id, "step_reconciled", seq,
                               seq - 1, {"step_id": "flip"},
                               schema_version=2)])
        conflict = self._conflict()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["unknown_event_types"], [])
        self.assertEqual(conflict["foreign_schema_versions"], [2])
        seq = _next_raw_seq(self.root, self.closure_id)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(self.closure_id, "step_reconciled", seq,
                               seq - 1, {"step_id": "flip"},
                               schema_version=0)])
        conflict = self._conflict()
        self.assertEqual(conflict["foreign_schema_versions"], [0, 2])

    def test_preflight_absent_schema_version_stays_fail_safe(self):
        """Backward-compat boundary: a known-type event WITHOUT the
        schema_version stamp is not a version signal — the preflight
        stays silent (the existing fail-safe envelope lane keeps owning
        that shape; this fix widens nothing retroactively)."""
        seq = _next_raw_seq(self.root, self.closure_id)
        bare = loop_event_log.build_event(
            self.closure_id, "closure_started", cas_version=seq,
            from_version=(seq - 1) if seq > 1 else None,
            actor="fixture/bare", payload={})
        bare.pop("schema_version", None)
        _append_raw_journal_lines(self.root, [bare])
        self.assertIsNone(self._conflict())

    # ── resume gate (run/resume — the ticket MUST) ───────────────────────

    def test_resume_of_unknown_type_closure_refused_zero_write(self):
        """红绿核心 (DEC-241 实测向量): resume of a closure whose journal
        carries a newer writer's tombstone — refused ZERO-WRITE with the
        unknown type named; the kept-view resume that misread the closure
        as active and collided at the occupied seq is gone."""
        self._make_blocked_closure()
        self._seed_future_tombstone()
        before = self._gov_snapshot()
        lines_before = _raw_unit_line_count(self.root, self.closure_id)
        spec_path = _write_fixture_spec(self.root, "spec.json",
                                        _CANCEL_FLIP_SPEC)
        proc = subprocess.run(
            self._resume_cli_argv(spec_path, self.closure_id),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=_clean_env(), cwd=str(self.root),
            timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        refused = json.loads(proc.stdout)
        self.assertEqual(refused["code"], "schema_violation", refused)
        self.assertEqual(refused["disposition"], "validation")
        self.assertIn(_FUTURE_TOMBSTONE_TYPE, refused["detail"])
        # zero writes: no closure_started / fenced / step bookkeeping, no
        # governed-record change, and NO seq-collision append
        self.assertEqual(self._gov_snapshot(), before)
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id),
                         lines_before)

    def test_preflight_precedes_the_fenced_audit_write(self):
        """arch ① 预检 vs 副作用隔离 — the sharp case: a FENCED stale
        generation whose journal ALSO carries an unknown type. The stale
        resume would record one closure_fenced audit event; the version
        preflight must fire FIRST — the fenced-audit write never happens
        (a conflicted journal must not gain even audit events from a
        reader that cannot judge it)."""
        self._make_blocked_closure()
        new_holder = cc.new_closure_id()
        takeover = cc.takeover_execution(
            self.root, TASK, new_holder, authorized_by="test-operator",
            reason="接管后旧链 journal 被更新版本续写（预检时序钉住）")
        self.assertFalse(takeover.get("error"), takeover)
        self._seed_future_tombstone()
        before = self._gov_snapshot()
        lines_before = _raw_unit_line_count(self.root, self.closure_id)
        spec = cc.parse_chain_spec(json.loads(json.dumps(
            _CANCEL_FLIP_SPEC)))
        with self.assertRaises(ValueError) as ctx:
            cc.run_chain(spec, root=self.root, task=TASK,
                         inputs=dict(EVD_INPUTS), closure_id=self.closure_id)
        self.assertIn(_FUTURE_TOMBSTONE_TYPE, str(ctx.exception))
        self.assertIn("NEWER writer", str(ctx.exception))
        # ZERO writes — in particular NO closure_fenced audit event
        self.assertEqual(self._gov_snapshot(), before)
        events = _chain_events(self.root, self.closure_id)
        self.assertFalse(
            any(e["event_type"] == "closure_fenced" for e in events))
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id),
                         lines_before)

    # ── finalize gate (the ticket MUST) ──────────────────────────────────

    def test_finalize_of_unknown_type_closure_refused_zero_write(self):
        self._make_ready_closure()
        self._seed_future_tombstone()
        before = self._gov_snapshot()
        lines_before = _raw_unit_line_count(self.root, self.closure_id)
        code, refused = _run_cli(self.root, "finalize",
                                 "--closure-id", self.closure_id,
                                 "--commit-sha", "deadbee")
        self.assertEqual(code, 2, refused)
        self.assertEqual(refused["code"], "schema_violation", refused)
        self.assertIn(_FUTURE_TOMBSTONE_TYPE, refused["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id),
                         lines_before)
        self.assertFalse(any(
            e["event_type"] == "closure_finalized"
            for e in _chain_events(self.root, self.closure_id)))

    # ── the same-vector append/derive entries (cancel / reopen) ─────────

    def test_cancel_of_unknown_type_closure_refused_zero_write(self):
        """The DEC-241 vector's cancel leg: a closure terminal in a newer
        vocabulary looks ACTIVE to this reader — an ungated cancel would
        terminate it again and release the newer holder's dispatch
        locks. The gate refuses zero-write instead."""
        self._make_blocked_closure()
        self._seed_future_tombstone()
        before = self._gov_snapshot()
        lines_before = _raw_unit_line_count(self.root, self.closure_id)
        code, refused = self._cancel("--authorized-by", "test-coordinator",
                                     "--reason", "误读防护验证")
        self.assertEqual(code, 2, refused)
        self.assertEqual(refused["code"], "schema_violation", refused)
        self.assertIn(_FUTURE_TOMBSTONE_TYPE, refused["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id),
                         lines_before)
        self.assertIsNone(self._cancel_event())
        locks = self.locks_json()
        self.assertIn(TASK, locks["active_tasks"])   # nothing released

    def test_reopen_of_unknown_type_closure_refused_zero_write(self):
        """A finalized closure whose journal later gained a newer writer's
        event: the derived terminal is no longer judgeable — reopen (the
        lineage-minting entry) refuses zero-write instead of forking the
        attempt chain from a partial view."""
        self._make_ready_closure()
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m", "closure commit")
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        self._seed_future_lineage()
        before = self._gov_snapshot()
        lines_before = _raw_unit_line_count(self.root, self.closure_id)
        payload = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="版本冲突面验证")
        self.assertEqual(payload["code"], "schema_violation", payload)
        self.assertIn(_FUTURE_LINEAGE_TYPE, payload["detail"])
        self.assertEqual(self._gov_snapshot(), before)
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id),
                         lines_before)
        self.assertFalse(any(
            e["event_type"] == "closure_reopened"
            for e in _chain_events(self.root, self.closure_id)))

    def _seed_future_lineage(self):
        seq = _next_raw_seq(self.root, self.closure_id)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(
                self.closure_id, _FUTURE_LINEAGE_TYPE, seq, seq - 1,
                {"successor_closure_id": cc.new_closure_id(),
                 "reopen_attempt": 2})])

    # ── forged-tombstone negative (arch ③ 负例) ──────────────────────────

    def test_forged_tombstone_shape_never_misread_as_terminal_or_active(self):
        """负例 (arch ③): a tombstone-SHAPED unknown event must leave the
        closure in NEITHER diagnosable state — the reader refuses instead
        of (a) honoring it as a terminal (unknown vocabulary — honoring
        it would let a forged line terminate a live closure) or (b)
        misreading the closure as active and resuming across it (the
        measured 0.87 vector). The kept view contains no terminal."""
        self._make_blocked_closure()
        self._seed_future_tombstone()
        # (a) not honored as a terminal: no known terminal in the kept view
        events, _problems = cc._load_closure_events(
            cc.default_event_log_path(self.root), self.closure_id)
        self.assertFalse(any(
            e["event_type"] in ("closure_cancelled", "closure_finalized")
            for e in events))
        # (b) not resumable across it
        before = self._gov_snapshot()
        payload = cc.reopen_closure(
            self.root, self.closure_id, authorized_by="test-coordinator",
            reason="伪造终态负例")
        self.assertEqual(payload["code"], "schema_violation", payload)
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertNotIn(status["status"],
                         ("cancelled", "finalized"))
        self.assertTrue(status["journal_problems"])
        self.assertTrue(any(_FUTURE_TOMBSTONE_TYPE in p
                            for p in status["journal_problems"]))
        self.assertEqual(self._gov_snapshot(), before)

    # ── writer-side anti-occupation backstop (ticket acceptance) ─────────

    def test_append_refused_at_occupied_raw_seq(self):
        """碰撞向量机消灭 (DEC-241 实测: kept=[1,2] → next=3 与 raw 3 相撞):
        the writer refuses to append into an occupied raw seq — the
        collision is machine-impossible even for a path that forgets the
        entry gate; the journal keeps its append-only integrity."""
        log_path = cc.default_event_log_path(self.root)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(self.closure_id, "closure_started", 1, None,
                               {"chain_id": "fixture", "task": TASK}),
            _raw_closure_event(self.closure_id, "closure_ready", 2, 1,
                               {"step_id": "end"}),
            _raw_closure_event(self.closure_id, _FUTURE_TOMBSTONE_TYPE, 3,
                               2, {}),
        ])
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id), 3)
        with self.assertRaises(ValueError) as ctx:
            cc._append_closure_event(
                log_path, self.closure_id, "closure_fenced", 3, 2,
                {"task": TASK})
        self.assertIn("occupied", str(ctx.exception))
        self.assertIn("anti-occupation", str(ctx.exception))
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id), 3)

    def test_append_at_free_seq_still_lands(self):
        """Positive control: the backstop never blocks the normal
        seq-continuous append path (existing writes unchanged)."""
        log_path = cc.default_event_log_path(self.root)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(self.closure_id, "closure_started", 1, None,
                               {"chain_id": "fixture", "task": TASK})])
        envelope = cc._append_closure_event(
            log_path, self.closure_id, "step_started", 2, 1,
            {"step_id": "flip", "kind": "cli"})
        self.assertEqual(envelope["cas_version"], 2)
        self.assertEqual(cc._validate_closure_event(envelope), [])
        self.assertEqual(_raw_unit_line_count(self.root, self.closure_id), 2)

    # ── status stays read-only fail-safe (读 fail-safe 半面不变) ──────────

    def test_status_face_stays_read_only_disclosure_on_conflict(self):
        self._make_blocked_closure()
        self._seed_future_tombstone()
        before = self._gov_snapshot()
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertTrue(status["found"])
        self.assertEqual(status["status"], "blocked")  # derived from KEPT
        self.assertTrue(any(_FUTURE_TOMBSTONE_TYPE in p
                            for p in status["journal_problems"]))
        self.assertEqual(self._gov_snapshot(), before)

    # ── 0.87-compatibility matrix: every old form keeps flowing ─────────

    def test_matrix_historical_form_journal_status_and_finalize_flow(self):
        """Matrix cell (旧 journal 形态各得其所 ①): a fully hand-assembled
        HISTORICAL-form journal (only the 8-type vocabulary, schema
        version 1) is read, derived, and completed by this reader —
        no false version rejection on the old form."""
        log_path = cc.default_event_log_path(self.root)
        merged = dict(cc._REQUIRED_INPUT_DEFAULTS)
        merged.update(EVD_INPUTS)
        _append_raw_journal_lines(self.root, [
            _raw_closure_event(
                self.closure_id, "closure_started", 1, None,
                {"chain_id": "standard-ticket-closure", "task": TASK,
                 "inputs_digest": cc._inputs_digest(merged),
                 "inputs": dict(sorted(merged.items())),
                 "code_revision": None}, actor=cc.WRITER_ID),
            _raw_closure_event(self.closure_id, "step_started", 2, 1,
                               {"step_id": "flip-completed", "kind": "cli"},
                               actor=cc.WRITER_ID),
            _raw_closure_event(self.closure_id, "step_completed", 3, 2,
                               {"step_id": "flip-completed",
                                "execution": "succeeded"},
                               actor=cc.WRITER_ID),
            _raw_closure_event(self.closure_id, "closure_ready", 4, 3,
                               {"step_id": "ready-to-commit"},
                               actor=cc.WRITER_ID),
        ])
        self.assertIsNone(self._conflict())
        code, status = _run_cli(self.root, "status",
                                "--closure-id", self.closure_id)
        self.assertEqual(code, 0, status)
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["journal_problems"], [])
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        self.assertFalse(done.get("error"), done)
        self.assertEqual(done["status"], "finalized")
        self.assertIsNone(self._conflict())

    def test_matrix_standard_chain_lock_leg_not_false_rejected(self):
        """arch ③ 正例: with the version gate live, the STANDARD chain's
        lock-leg closure flows end-to-end — idempotent resume appends
        zero events, finalize records the terminal, and the full journal
        (including the terminal) stays conflict-free."""
        self._make_ready_closure()
        events_after_run = _chain_events(self.root, self.closure_id)
        payload = self._run_spec(cc.STANDARD_TICKET_CLOSURE)   # resume
        self.assertEqual(payload["status"], "ready", payload)
        self.assertEqual(
            _chain_events(self.root, self.closure_id), events_after_run)
        (self.root / "out.md").write_text("x", encoding="utf-8")
        _git("-C", str(self.root), "add", "-A")
        _git("-C", str(self.root), "commit", "-q", "-m", "closure commit")
        sha = _git("-C", str(self.root), "rev-parse", "HEAD").stdout.strip()
        code, done = _run_cli(self.root, "finalize",
                              "--closure-id", self.closure_id,
                              "--commit-sha", sha)
        self.assertEqual(code, 0, done)
        self.assertIsNone(self._conflict())


class RunLockOwnershipTests(_WorkspaceFixture):
    """arch ② 锁归属模型 (钉住现状): the per-closure run lock FILE is
    never deleted and its byte-range lease is per-fd — after a new
    instance re-acquires the lock, a stale old instance's release cannot
    disturb (unlock or delete) the new holder's lease. The dispatch-lock
    ownership face is pinned separately by CancellationLockOwnershipTests
    (ownership-changed locks) + ExecutionGenerationFencingTests
    (skipped_fenced releases)."""

    def test_stale_release_cannot_disturb_new_holder_lease(self):
        lock_dir = cc._closure_lock_dir(self.root)
        lock_path = lock_dir / (self.closure_id + ".lock")
        old = cc._RunLock(lock_path, 10.0)
        new = cc._RunLock(lock_path, 10.0)
        probe = cc._RunLock(lock_path, 0.2)
        with old:
            pass                       # old instance released its lease
        with new:                      # new instance re-acquired
            # a stale/double release from the old instance is a no-op and
            # must NOT unlock the new holder's lease
            old.__exit__(None, None, None)
            with self.assertRaises(cc.LockContention):
                with probe:
                    pass
        # the lock FILE survives every release (never deleted — the
        # loop_event_log precedent an old instance cannot violate)
        self.assertTrue(lock_path.is_file())
        # lease recycling still works for the next acquirer
        with cc._RunLock(lock_path, 10.0):
            with self.assertRaises(cc.LockContention):
                with probe:
                    pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
