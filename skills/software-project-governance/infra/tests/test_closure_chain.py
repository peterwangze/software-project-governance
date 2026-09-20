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

CC_PATH = Path(cc.__file__).resolve()
GS_PATH = _INFRA_DIR / "governance_store.py"
TRU_PATH = _INFRA_DIR / "task_row_update.py"

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
