"""FEAT-096 guard tests — infra/execution_isolation.py (conservative surface).

arch 盲区裁定 (DEC-330 批): 锁可绕过 = 锁未控制实际写入能力; 无法隔离的
共享文件宁可限制写并发, 不用可绕过软锁假装安全.  This module guards the
delivered conservative four-piece set:

  1. 共享文件写并发限制 — begin/end exclusive write slots: a second
     writer on the SAME file domain is refused with holder + expected
     release (ux contract); cross-process proof via real subprocesses;
  2. 同文件域「被审/在写」互斥 — a domain under an active review
     snapshot refuses writes; a domain being written refuses snapshot
     creation (Reviewer reads immutable state, not a mid-write file);
  3. 审查快照只读化 — snapshot files are chmod read-only AND the write
     gate refuses any sanctioned write under the snapshot root;
  4. 租约失权回收 — a writer whose agent-locks lease has expired is
     REFUSED (authority lost) and the refusal triggers the reclaim of
     the expired lease entries (RPG 实测 36 锁悬挂 20h 的根面).

Backward compatibility (hard gate, red test first): OLD-format
agent-locks.json (pre-FEAT-013 field shape, no expected_new / no extra
active_tasks fields) must stay readable and reclaimable — this ticket
adds NO new required lock fields (non_goal).

Capability honesty (acceptance ①): the module's disclosure must REFERENCE
the FEAT-095 research report and must NOT claim verified host-level
worktree/sandbox isolation (U1 未证实).

All fixtures run in temp directories — the real $HOME / $DSH_HOME /
repo .governance are never touched.

Run:
    python -m unittest skills/software-project-governance/infra/tests/test_execution_isolation.py -v
"""

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import execution_isolation as ei  # noqa: E402


MODULE_PATH = _INFRA_DIR / "execution_isolation.py"


def _write_bytes(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _seed_locks(gov: Path, *, task_id="FIX-100", domain="docs/a.md",
                locked_at="2026-09-19T10:00:00", ttl_seconds=3600,
                legacy_shape=False):
    """Write an agent-locks.json fixture.

    ``legacy_shape=True`` writes the OLD pre-FEAT-013 field shape: the
    active_tasks entry carries ONLY the Check 26 mandatory fields and the
    file_locks entry has none of the later optional flags — the backward
    compatibility face (旧锁可读可回收).
    """
    task_entry = {
        "agent_role": "Developer",
        "spawned_at": locked_at,
        "coordinator_session": "session-x",
        "target_files": [domain],
    }
    if not legacy_shape:
        task_entry.update({
            "description": "", "acquired": locked_at, "files": [domain],
        })
    entry = {
        "locked_by": task_id,
        "locked_at": locked_at,
        "ttl_seconds": ttl_seconds,
        "ttl_reason": "seed",
    }
    _write_bytes(gov / "agent-locks.json", json.dumps({
        "active_tasks": {task_id: task_entry},
        "file_locks": {domain: entry},
    }, ensure_ascii=False, indent=4) + "\n")
    return entry


class IsolationTestCase(unittest.TestCase):
    """Temp-dir fixture (never the real .governance / $HOME)."""

    def setUp(self):
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.gov = self.tmp / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.repo = self.tmp  # repo_root == temp project root

    def tearDown(self):
        # snapshots (files + manifests) are read-only BY DESIGN — restore
        # writability so the temp cleanup can remove them (Windows rmtree
        # refuses read-only files).
        snap_root = self.gov / ei.SNAPSHOT_DIR_NAME
        if snap_root.is_dir():
            for path in snap_root.rglob("*"):
                try:
                    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
        self._tmp_ctx.cleanup()

    # ── helpers ────────────────────────────────────────────────────────

    def now(self):
        return datetime(2026, 10, 10, 12, 0, 0)

    def seed_target_file(self, rel="docs/a.md", text="alpha\n"):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            _write_bytes(path, text)
        return rel

    def begin(self, task, files, **kw):
        return ei.begin_write(task, files, governance_dir=self.gov,
                              now=self.now(), **kw)

    def judge(self, task, files, **kw):
        return ei.judge_write(task, files, governance_dir=self.gov,
                              now=self.now(), **kw)

    def end(self, task, files, **kw):
        return ei.end_write(task, files, governance_dir=self.gov,
                            now=self.now(), **kw)

    def snapshot(self, task, files, **kw):
        return ei.create_review_snapshot(
            task, files, governance_dir=self.gov, repo_root=self.repo,
            now=self.now(), **kw)

    def release_review(self, task, **kw):
        return ei.release_review(task, governance_dir=self.gov,
                                 now=self.now(), **kw)

    def reclaim(self, **kw):
        return ei.reclaim_expired_leases(governance_dir=self.gov,
                                         now=self.now(), **kw)

    def load_locks(self):
        return json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))

    def load_state(self):
        return json.loads(
            (self.gov / ei.STATE_FILE_NAME).read_text(encoding="utf-8"))

    def assertRefused(self, result, code):
        self.assertTrue(result.get("error"), result)
        self.assertEqual(result.get("code"), code, result)


# ── 1. 共享文件写并发限制 ─────────────────────────────────────────────


class WriteConcurrencyLimitTests(IsolationTestCase):
    def test_second_writer_same_domain_refused_with_holder_and_release(self):
        domain = self.seed_target_file()
        first = self.begin("FIX-100", [domain])
        self.assertFalse(first.get("error"), first)
        second = self.begin("FIX-200", [domain])
        self.assertRefused(second, ei.CODE_WRITE_CONFLICT)
        refusals = second["refusals"]
        self.assertEqual(len(refusals), 1)
        refusal = refusals[0]
        self.assertEqual(refusal["file"], domain)
        self.assertEqual(refusal["holder"], "FIX-100")
        # ux contract: the refusal carries the holder AND the expected
        # release time (机器可读 + 人可读 both live in the detail).
        self.assertIn("expires_at", refusal)
        self.assertIn("FIX-100", refusal["detail"])
        self.assertIn(refusal["expires_at"], refusal["detail"])

    def test_same_task_reentrant_begin_refreshes_slot(self):
        domain = self.seed_target_file()
        first = self.begin("FIX-100", [domain], ttl_seconds=60)
        again = self.begin("FIX-100", [domain], ttl_seconds=120)
        self.assertFalse(again.get("error"), again)
        state = self.load_state()
        self.assertEqual(
            state["writers"][domain]["expires_at"],
            again["expires_at"])

    def test_end_write_releases_domain_for_next_writer(self):
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        released = self.end("FIX-100", [domain])
        self.assertFalse(released.get("error"), released)
        self.assertIn(domain, released["released"])
        nxt = self.begin("FIX-200", [domain])
        self.assertFalse(nxt.get("error"), nxt)

    def test_end_write_by_non_holder_refused(self):
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        rogue = self.end("FIX-200", [domain])
        self.assertRefused(rogue, ei.CODE_NOT_HOLDER)
        # the rightful holder is untouched
        self.assertIn(domain, self.load_state()["writers"])

    def test_distinct_domains_do_not_conflict(self):
        a = self.seed_target_file("docs/a.md")
        b = self.seed_target_file("docs/b.md")
        self.assertFalse(self.begin("FIX-100", [a]).get("error"))
        self.assertFalse(self.begin("FIX-200", [b]).get("error"))

    def test_cross_process_write_mutex_real_subprocesses(self):
        # the O_EXCL lockfile is the actual cross-process primitive: two
        # REAL python processes serialize on the domain lockfile. stdio is
        # DEVNULL (no named-pipe capture — sandbox safe); the exit code is
        # the assertion face (0 acquired / 2 refused).
        domain = self.seed_target_file()
        base = [sys.executable, str(MODULE_PATH),
                "--project-root", str(self.repo)]

        def run(task):
            return subprocess.run(
                base + ["isolation-write", "--action", "begin",
                        "--task", task, "--files", domain],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        first = run("FIX-100")
        self.assertEqual(first.returncode, 0, "first writer must acquire")
        second = run("FIX-200")
        self.assertEqual(second.returncode, 2, "second writer must refuse")
        end = subprocess.run(
            base + ["isolation-write", "--action", "end",
                    "--task", "FIX-100", "--files", domain],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(end.returncode, 0)
        after = run("FIX-200")
        self.assertEqual(after.returncode, 0,
                         "domain must be free again after end")

    def test_disabled_switch_passthrough_legacy_behavior(self):
        # rollback plan face: the concurrency switch OFF restores the
        # pre-FEAT-096 behavior (zero gate — the soft-lock status quo).
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        with mock_env(ei.DISABLE_ENV_VAR, "off"):
            passthrough = ei.begin_write(
                "FIX-200", [domain], governance_dir=self.gov,
                now=self.now())
        self.assertFalse(passthrough.get("error"), passthrough)
        self.assertTrue(passthrough.get("gate_disabled"))

    def test_refused_writer_recorded_as_waiter(self):
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        self.assertRefused(self.begin("FIX-200", [domain]),
                           ei.CODE_WRITE_CONFLICT)
        state = self.load_state()
        waiters = [w for w in state["waiters"] if w["task_id"] == "FIX-200"]
        self.assertEqual(len(waiters), 1)
        self.assertEqual(waiters[0]["holder"], "FIX-100")

    def test_expired_slot_is_stale_and_cleaned_on_next_begin(self):
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain],
                                    ttl_seconds=30).get("error"))
        later = self.now() + timedelta(seconds=120)
        nxt = ei.begin_write("FIX-200", [domain], governance_dir=self.gov,
                             now=later)
        self.assertFalse(nxt.get("error"), nxt)
        state = self.load_state()
        self.assertEqual(state["writers"][domain]["task_id"], "FIX-200")


# ── 2. 同文件域「被审/在写」互斥 ─────────────────────────────────────


class WorkerAndRecoveryTests(IsolationTestCase):
    def cli(self, cwd, project, command, *args):
        return subprocess.run([sys.executable, str(MODULE_PATH), "--project-root", str(project),
                               command, *args], cwd=cwd, capture_output=True,
                              encoding="utf-8", timeout=15)

    def test_two_workspaces_same_shared_slot_and_independent_copies(self):
        target = self.seed_target_file()
        shared = self.repo / target
        shared_before = shared.read_bytes()
        roots = [self.tmp / "workspace-a", self.tmp / "workspace-b"]
        for workspace in roots:
            (workspace / ".governance").mkdir(parents=True)
            (workspace / target).parent.mkdir(parents=True)
            (workspace / target).write_text(workspace.name, encoding="utf-8")

        def args(action, session):
            return ["isolation-write", "--action", action, "--task", "FIX-100",
                    "--writer", "Dev", "--session", session, "--files", target]

        procs = [subprocess.Popen([sys.executable, str(MODULE_PATH), "--project-root",
                                   str(self.repo), *args("begin", "shared")], cwd=workspace,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for workspace in roots]
        results = [json.loads(proc.communicate(timeout=15)[0]) for proc in procs]
        self.assertEqual(sorted(p.returncode for p in procs), [0, 2])
        winner = next(i for i, r in enumerate(results) if not r.get("error"))
        owner, other = roots[winner], roots[1-winner]
        self.assertEqual(results[1-winner]["refusals"][0]["holder_worker"],
                         results[winner]["worker"])
        for workspace, session, action in [(other, "shared", "end"), (owner, "different", "end"),
                                           (owner, "different", "begin")]:
            self.assertEqual(self.cli(workspace, self.repo, *args(action, session)).returncode, 2)
        self.assertEqual(self.cli(owner, self.repo, *args("begin", "shared")).returncode, 0)
        self.assertEqual(shared.read_bytes(), shared_before)
        for workspace in roots:
            self.assertEqual(self.cli(workspace, workspace, *args("begin", "shared")).returncode, 0)
            (workspace / target).write_text("owned by " + workspace.name, encoding="utf-8")
            self.assertEqual(self.cli(workspace, workspace, *args("end", "shared")).returncode, 0)
        self.assertNotEqual((owner / target).read_bytes(), (other / target).read_bytes())
        self.assertEqual(self.cli(owner, self.repo, *args("end", "shared")).returncode, 0)
        self.assertEqual(shared.read_bytes(), shared_before)

    def test_late_writer_cannot_end_successor_or_partially_release_batch(self):
        a, b = self.seed_target_file("a"), self.seed_target_file("b")
        self.begin("FIX-100", [a], writer="A", ttl_seconds=3)
        self.begin("FIX-100", [b], writer="A")
        later = self.now() + timedelta(seconds=4)
        nxt = ei.begin_write("FIX-100", [a], writer="B", governance_dir=self.gov, now=later)
        self.assertIn(a, nxt["granted"])
        self.assertRefused(self.end("FIX-100", [b, a], writer="A"), ei.CODE_NOT_HOLDER)
        self.assertEqual(self.load_state()["writers"][a]["writer"], "B")
        self.assertEqual(self.load_state()["writers"][b]["writer"], "A")

    def test_interrupted_reviewer_exact_expired_recovery_preserves_snapshot_and_successor(self):
        domain = self.seed_target_file()
        source = self.repo / domain
        original = source.read_bytes()
        receipt = self.repo / "created.json"
        script = (
            "import json,sys,time; from pathlib import Path; from datetime import datetime,timedelta; "
            "sys.path.insert(0,sys.argv[1]); import execution_isolation as ei; "
            "root=Path.cwd(); result=ei.create_review_snapshot('FIX-100',['docs/a.md'],"
            "reviewer='Review',session_id='first',governance_dir=root/'.governance',"
            "repo_root=root,ttl_seconds=60,now=datetime.now()-timedelta(minutes=5)); "
            "Path('created.json').write_text(json.dumps(result),encoding='utf-8'); time.sleep(60)"
        )
        proc = subprocess.Popen([sys.executable, "-c", script, str(_INFRA_DIR)], cwd=self.repo)
        try:
            limit = time.monotonic() + 10
            while not receipt.exists() and proc.poll() is None and time.monotonic() < limit:
                time.sleep(0.02)
            self.assertTrue(receipt.exists())
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        snap = json.loads(receipt.read_text(encoding="utf-8"))
        sid = snap["snapshot_id"]
        frozen = Path(snap["snapshot_root"]) / domain
        manifest = Path(snap["snapshot_root"]) / ei.SNAPSHOT_MANIFEST_NAME
        before = (frozen.read_bytes(), manifest.read_bytes())
        self.assertEqual(before[0], original)
        retry = dict(governance_dir=self.gov, reason="reviewer process ended", session_id="new")
        start = datetime.fromisoformat(snap["created_at"])
        self.assertRefused(ei.recover_review("FIX-100", sid, now=start, **retry),
                           ei.CODE_UNDER_REVIEW)
        self.assertRefused(ei.release_review("FIX-100", governance_dir=self.gov,
                                           session_id="new"), ei.CODE_NOT_HOLDER)
        after = start + timedelta(seconds=61)
        self.assertFalse(ei.judge_write("FIX-100", [domain], governance_dir=self.gov,
                                      now=after)["allowed"])
        self.assertTrue(ei.isolation_status(governance_dir=self.gov,
                                           now=after)["reviews"][domain]["recoverable"])
        recovered = self.cli(self.repo, self.repo, "isolation-snapshot", "--action", "recover",
                             "--task", "FIX-100", "--snapshot-id", sid, "--session", "new",
                             "--reason", retry["reason"])
        self.assertEqual(recovered.returncode, 0, recovered.stdout)
        self.assertEqual(json.loads(recovered.stdout)["released"], [domain])
        self.assertIn(domain, ei.create_review_snapshot("FIX-100", [domain], governance_dir=self.gov,
                            repo_root=self.repo, session_id="new", now=after)["domains"])
        cli = self.cli(self.repo, self.repo, "isolation-snapshot", "--action", "recover",
                       "--task", "FIX-100", "--snapshot-id", sid, "--reason", "retry")
        self.assertEqual(cli.returncode, 0, cli.stdout)
        self.assertEqual(json.loads(cli.stdout)["released"], [])
        self.assertIn(domain, self.load_state()["reviews"])
        self.assertEqual(self.load_state()["snapshots"][sid]["recovery_reason"], retry["reason"])
        self.assertEqual((frozen.read_bytes(), manifest.read_bytes()), before)
        self.assertEqual(source.read_bytes(), original)

    def test_interrupted_state_mutation_releases_kernel_guard(self):
        ready = self.repo / "locked"
        script = (
            "import sys,time; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "import execution_isolation as ei; "
            "guard=ei._StateLock(Path.cwd()/'.governance'); guard.__enter__(); "
            "Path('locked').touch(); time.sleep(60)"
        )
        proc = subprocess.Popen([sys.executable, "-c", script, str(_INFRA_DIR)], cwd=self.repo)
        try:
            limit = time.monotonic() + 10
            while not ready.exists() and proc.poll() is None and time.monotonic() < limit:
                time.sleep(0.02)
            self.assertTrue(ready.exists())
            self.assertRefused(self.begin("FIX-100", ["a"], timeout_seconds=0.05),
                               ei.CODE_LOCK_CONTENTION)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        self.assertEqual(self.begin("FIX-100", ["a"], timeout_seconds=1)["granted"], ["a"])

    def test_old_bindings_and_unknown_expiry(self):
        task, domain, sid = "FIX-100", "docs/a.md", "SNAP-OLD"
        state = ei._new_state()
        state["reviews"][domain] = {"snapshot_id": sid, "task_id": task}
        state["writers"]["other"] = {"task_id": task, "writer": "",
                                     "expires_at": ei._iso(self.now() + timedelta(seconds=5))}
        path = self.gov / ei.STATE_FILE_NAME
        _write_bytes(path, json.dumps(state))
        self.assertRefused(self.begin(task, ["other"]), ei.CODE_WRITE_CONFLICT)
        self.assertRefused(self.end(task, ["other"]), ei.CODE_NOT_HOLDER)
        kwargs = dict(governance_dir=self.gov, reason="legacy reviewer ended", now=self.now())
        self.assertRefused(ei.recover_review(task, sid, **kwargs), ei.CODE_UNDER_REVIEW)
        state["reviews"][domain]["began_at"] = ei._iso(self.now() - timedelta(hours=2))
        _write_bytes(path, json.dumps(state))
        self.assertEqual(ei.recover_review(task, sid, **kwargs)["released"], [domain])
        self.assertEqual(self.load_state()["snapshots"][sid]["files"], [domain])
        self.assertIn("other", ei.begin_write(task, ["other"], governance_dir=self.gov,
                                      now=self.now() + timedelta(seconds=6))["granted"])

    def test_flattening_collision_allows_two_writers_and_keeps_separate_markers(self):
        nested = self.seed_target_file("reports/report.md", "nested")
        flat = self.seed_target_file("reports__report.md", "flat")
        self.assertFalse((self.repo / nested).samefile(self.repo / flat))
        children = [subprocess.Popen([sys.executable, str(MODULE_PATH), "--project-root",
                    str(self.repo), "isolation-write", "--action", "begin", "--task", task,
                    "--session", task, "--files", name], cwd=self.repo, stdout=subprocess.PIPE)
                    for task, name in (("FIX-101", nested), ("FIX-102", flat))]
        for child in children:
            result = json.loads(child.communicate(timeout=15)[0])
            self.assertEqual(child.returncode, 0, result)
        status = ei.isolation_status(governance_dir=self.gov)
        self.assertEqual(set(status["writers"]), {nested, flat})
        self.assertNotEqual(ei._domain_lockfile(self.gov, nested), ei._domain_lockfile(self.gov, flat))
        self.assertEqual(self.cli(self.repo, self.repo, "isolation-write", "--action", "end",
                                  "--task", "FIX-102", "--session", "FIX-102",
                                  "--files", flat).returncode, 0)
        self.assertEqual(set(ei.isolation_status(governance_dir=self.gov)["writers"]), {nested})
        self.assertEqual((self.repo / nested).read_bytes(), b"nested")
        self.assertEqual((self.repo / flat).read_bytes(), b"flat")

    def test_volume_case_lookup_applies_to_status_write_review_and_missing_files(self):
        named, other = "Reports/Note.MD", "Reports/nOTE.md"
        self.seed_target_file(named, "Original")
        path = self.repo / named
        alias = self.repo / other
        insensitive = alias.exists() and path.samefile(alias)
        self.begin("FIX-100", [named], writer="one")
        if not insensitive:
            self.seed_target_file(other, "Separate")
            self.assertIn(other, self.begin("FIX-200", [other], writer="two")["granted"])
            self.assertEqual(len(ei.isolation_status(governance_dir=self.gov)["writers"]), 2)
            return
        self.assertRefused(self.begin("FIX-200", [other], writer="two"), ei.CODE_WRITE_CONFLICT)
        self.assertRefused(self.snapshot("FIX-200", [other]), ei.CODE_WRITE_IN_PROGRESS)
        self.assertIn(other, self.begin("FIX-100", [other], writer="one")["granted"])
        status = ei.isolation_status(governance_dir=self.gov)
        self.assertEqual(list(status["writers"]), [named])
        self.assertEqual(status["writers"][named]["domain_key"], ei._domain_key(self.gov, other))
        self.assertIn(other, self.end("FIX-100", [other], writer="one")["released"])
        snap = self.snapshot("FIX-100", [named, other])
        self.assertEqual(snap["domains"], [named])
        self.assertRefused(self.begin("FIX-200", [other]), ei.CODE_UNDER_REVIEW)
        self.assertEqual(self.release_review("FIX-100", snapshot_id=snap["snapshot_id"])["released"], [named])
        self.assertEqual(path.read_bytes(), b"Original")
        pending = "Reports/Future.MD"
        self.begin("FIX-100", [pending], writer="one")
        self.assertRefused(self.begin("FIX-200", ["Reports/fUture.md"]), ei.CODE_WRITE_CONFLICT)
        self.seed_target_file(pending, "new")
        self.assertIn("Reports/future.md", self.end("FIX-100", ["Reports/future.md"],
                                                    writer="one")["released"])

    def test_old_flat_marker_handoff_keeps_unrelated_path_and_orphan_evidence(self):
        named = self.seed_target_file("reports/report.md", "original")
        other = self.seed_target_file("reports__report.md", "unrelated")
        row = {"task_id": "FIX-100", "writer": "old", "began_at": ei._iso(self.now()),
               "expires_at": ei._iso(self.now() + timedelta(minutes=1))}
        state = ei._new_state()
        state["writers"][named] = dict(row, purpose="original grant")
        _write_bytes(self.gov / ei.STATE_FILE_NAME, json.dumps(state))
        old = self.gov / ei.LOCK_DIR_NAME / "reports__report.md.write.lock"
        old.parent.mkdir()
        _write_bytes(old, json.dumps(dict(row, pid=123)))
        old_bytes = old.read_bytes()
        self.assertRefused(self.begin("FIX-200", [named]), ei.CODE_WRITE_CONFLICT)
        self.assertEqual(self.begin("FIX-200", [other])["granted"], [other])
        self.assertEqual(old.read_bytes(), old_bytes)
        self.end("FIX-200", [other])
        self.assertEqual(old.read_bytes(), old_bytes)
        self.assertEqual(self.begin("FIX-100", [named], writer="old")["granted"], [named])
        self.assertFalse(old.exists())
        self.end("FIX-100", [named], writer="old")
        # A marker left before the legacy state write has no path attribution.
        old.write_bytes(old_bytes)
        for name in (named, other):
            self.assertRefused(self.begin("FIX-100", [name], writer="old"), ei.CODE_WRITE_CONFLICT)
            self.assertRefused(self.end("FIX-100", [name], writer="old"), ei.CODE_NOT_HOLDER)
        self.assertIn(old.name, ei.isolation_status(governance_dir=self.gov)["unattributed_markers"])
        later = self.now() + timedelta(minutes=2)
        self.assertIn(other, ei.begin_write("FIX-200", [other], governance_dir=self.gov,
                                           now=later)["granted"])
        self.assertIn(other, ei.end_write("FIX-200", [other], governance_dir=self.gov,
                                         now=later)["released"])
        self.assertEqual(old.read_bytes(), old_bytes)
        self.assertEqual((self.repo / named).read_bytes(), b"original")
        self.assertEqual((self.repo / other).read_bytes(), b"unrelated")

    def test_orphan_marker_and_multifile_failure_preserve_existing_grants(self):
        task = "FIX-100"
        self.begin(task, ["a"], writer="A")
        original = ei._domain_lockfile(self.gov, "a").read_bytes()
        held = ei._domain_lockfile(self.gov, "b")
        _write_bytes(held, json.dumps({"task_id": "FIX-200", "writer": "B",
                                       "expires_at": ei._iso(self.now() + timedelta(hours=1))}))
        self.seed_target_file("b")
        self.assertRefused(self.snapshot(task, ["b"]), ei.CODE_WRITE_IN_PROGRESS)
        self.assertRefused(self.begin(task, ["a", "b"], writer="A"), ei.CODE_WRITE_CONFLICT)
        self.assertEqual(ei._domain_lockfile(self.gov, "a").read_bytes(), original)
        with mock.patch.object(ei, "_create_domain_lockfile", side_effect=OSError("disk full")):
            self.assertRefused(self.begin(task, ["a", "c"], writer="A", ttl_seconds=12),
                               ei.CODE_MANUAL_INTERVENTION)
        self.assertEqual(ei._domain_lockfile(self.gov, "a").read_bytes(), original)
        self.assertNotIn("c", self.load_state()["writers"])

    def test_corrupt_state_and_same_second_snapshot_refuse_without_overwrite(self):
        domain = self.seed_target_file()
        snap = self.snapshot("FIX-100", [domain])
        manifest = Path(snap["snapshot_root"]) / ei.SNAPSHOT_MANIFEST_NAME
        data = manifest.read_bytes()
        self.release_review("FIX-100")
        self.assertRefused(self.snapshot("FIX-100", [domain]), ei.CODE_SCHEMA_VIOLATION)
        self.assertEqual(manifest.read_bytes(), data)
        path = self.gov / ei.STATE_FILE_NAME
        for corrupt in (b"{bad", b'{"writers":[]}'):
            path.write_bytes(corrupt)
            self.assertRefused(self.begin("FIX-100", [domain]), ei.CODE_MANUAL_INTERVENTION)
            self.assertRefused(self.snapshot("FIX-100", [domain]), ei.CODE_MANUAL_INTERVENTION)
            self.assertEqual(path.read_bytes(), corrupt)


class ReviewWriteMutexTests(IsolationTestCase):
    def test_write_to_under_review_domain_refused_then_allowed_after_release(self):
        domain = self.seed_target_file(text="v1\n")
        snap = self.snapshot("FIX-100", [domain], review_round=0)
        self.assertFalse(snap.get("error"), snap)
        blocked = self.begin("FIX-300", [domain])
        self.assertRefused(blocked, ei.CODE_UNDER_REVIEW)
        refusal = blocked["refusals"][0]
        self.assertEqual(refusal["holder"], "FIX-100")
        self.assertIn("snapshot", json.dumps(refusal))
        released = self.release_review("FIX-100")
        self.assertFalse(released.get("error"), released)
        after = self.begin("FIX-300", [domain])
        self.assertFalse(after.get("error"), after)

    def test_snapshot_create_while_domain_being_written_refused(self):
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        snap = self.snapshot("FIX-100", [domain])
        self.assertRefused(snap, ei.CODE_WRITE_IN_PROGRESS)
        self.assertIn("FIX-100", json.dumps(snap["refusals"]))


# ── 3. 审查快照只读化 ─────────────────────────────────────────────────


class ReviewSnapshotReadOnlyTests(IsolationTestCase):
    def test_snapshot_file_direct_write_rejected_by_readonly_bit(self):
        domain = self.seed_target_file(text="immutable payload\n")
        snap = self.snapshot("FIX-100", [domain])
        self.assertFalse(snap.get("error"), snap)
        snap_file = Path(snap["snapshot_root"]) / domain
        self.assertTrue(snap_file.is_file())
        with self.assertRaises(PermissionError):
            with open(snap_file, "w", encoding="utf-8") as fh:
                fh.write("tamper\n")

    def test_write_gate_refuses_sanctioned_write_under_snapshot_root(self):
        domain = self.seed_target_file(text="payload\n")
        snap = self.snapshot("FIX-100", [domain])
        snap_rel = str((Path(snap["snapshot_root"]) / domain)
                       .relative_to(self.repo)).replace("\\", "/")
        blocked = self.begin("FIX-300", [snap_rel])
        self.assertRefused(blocked, ei.CODE_SNAPSHOT_IMMUTABLE)

    def test_snapshot_manifest_records_sha256_digests(self):
        domain = self.seed_target_file(text="digest me\n")
        snap = self.snapshot("FIX-100", [domain])
        files = snap["files"]
        self.assertEqual(len(files), 1)
        recorded = files[0]["sha256"]
        import hashlib
        actual = hashlib.sha256(
            (self.repo / domain).read_bytes()).hexdigest()
        self.assertEqual(recorded, actual)
        self.assertEqual(files[0]["source"], domain)


# ── 4. 租约失权回收 ───────────────────────────────────────────────────


class LeaseLossOfAuthorityTests(IsolationTestCase):
    def test_expired_lease_writer_refused_and_reclaim_triggered(self):
        # acceptance ④ verbatim: 过期写者写入被拒并触发回收.
        domain = self.seed_target_file()
        expired_at = self.now() - timedelta(hours=2)
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=(expired_at - timedelta(hours=1))
                    .replace(microsecond=0).isoformat(),
                    ttl_seconds=3600)
        result = self.begin("FIX-100", [domain])
        self.assertRefused(result, ei.CODE_LEASE_EXPIRED)
        refusal = result["refusals"][0]
        self.assertIn("authority", refusal["detail"].lower())
        # the refusal TRIGGERED the reclaim: the expired entry is gone…
        locks_now = self.load_locks()
        self.assertNotIn(domain, locks_now["file_locks"])
        self.assertNotIn("FIX-100", locks_now["active_tasks"])
        # …and the reclaim is audited machine-readably.
        state = self.load_state()
        reclaimed = [r for r in state["reclaim_log"]
                     if r["domain"] == domain]
        self.assertEqual(len(reclaimed), 1)
        self.assertEqual(reclaimed[0]["task_id"], "FIX-100")
        # the domain is FREE for the next legitimate writer.
        nxt = self.begin("FIX-200", [domain])
        self.assertFalse(nxt.get("error"), nxt)

    def test_active_lease_writer_allowed(self):
        domain = self.seed_target_file()
        locked_at = (self.now() - timedelta(minutes=10)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=locked_at, ttl_seconds=14400)
        result = self.begin("FIX-100", [domain])
        self.assertFalse(result.get("error"), result)

    def test_unexpired_leases_never_reclaimed(self):
        domain = self.seed_target_file()
        locked_at = (self.now() - timedelta(minutes=10)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=locked_at, ttl_seconds=14400)
        report = self.reclaim()
        self.assertFalse(report.get("error"), report)
        self.assertEqual(report["reclaimed"], [])
        self.assertIn(domain, self.load_locks()["file_locks"])

    def test_reclaim_corrupt_locks_file_fail_closed(self):
        _write_bytes(self.gov / "agent-locks.json", "{not json")
        report = self.reclaim()
        self.assertRefused(report, ei.CODE_MANUAL_INTERVENTION)
        self.assertIn("not json", (self.gov / "agent-locks.json")
                      .read_text(encoding="utf-8"))

    def test_standalone_reclaim_reports_and_cleans(self):
        domain_a = self.seed_target_file("docs/a.md")
        domain_b = self.seed_target_file("docs/b.md")
        stale = (self.now() - timedelta(hours=3)) \
            .replace(microsecond=0).isoformat()
        fresh = (self.now() - timedelta(minutes=5)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain_a,
                    locked_at=stale, ttl_seconds=3600)
        locks = self.load_locks()
        locks["file_locks"][domain_b] = {
            "locked_by": "FIX-100", "locked_at": fresh,
            "ttl_seconds": 14400, "ttl_reason": "seed",
        }
        _write_bytes(self.gov / "agent-locks.json",
                     json.dumps(locks, indent=4) + "\n")
        report = self.reclaim()
        self.assertFalse(report.get("error"), report)
        self.assertEqual([r["domain"] for r in report["reclaimed"]],
                         [domain_a])
        locks_now = self.load_locks()
        self.assertNotIn(domain_a, locks_now["file_locks"])
        self.assertIn(domain_b, locks_now["file_locks"])


# ── backward compatibility (hard gate — 旧锁可读可回收) ────────────────


class LegacyLockCompatibilityTests(IsolationTestCase):
    def test_old_format_lock_file_readable_and_releasable(self):
        # RED TEST FIRST (hard gate): the OLD pre-FEAT-013 field shape —
        # no expected_new, minimal active_tasks fields — must stay
        # READABLE (lease judgment) and RELEASABLE (reclaim). FEAT-096
        # adds NO new required lock fields (non_goal).
        domain = self.seed_target_file()
        stale = (self.now() - timedelta(hours=5)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=stale, ttl_seconds=3600,
                    legacy_shape=True)
        # readable: the judge sees the (expired) lease and refuses
        judged = self.judge("FIX-100", [domain])
        self.assertFalse(judged.get("error"), judged)
        self.assertFalse(judged["allowed"])
        self.assertEqual(judged["refusals"][0]["reason"],
                         ei.CODE_LEASE_EXPIRED)
        # releasable: the standalone reclaim cleans the legacy entry
        report = self.reclaim()
        self.assertFalse(report.get("error"), report)
        self.assertEqual(len(report["reclaimed"]), 1)
        self.assertNotIn(domain, self.load_locks()["file_locks"])

    def test_legacy_unexpired_lock_judged_active(self):
        domain = self.seed_target_file()
        fresh = (self.now() - timedelta(minutes=1)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=fresh, ttl_seconds=14400,
                    legacy_shape=True)
        judged = self.judge("FIX-100", [domain])
        self.assertTrue(judged["allowed"], judged)


# ── performance / ux / accessibility ──────────────────────────────────


class PerformanceAndUxTests(IsolationTestCase):
    def test_judge_write_wall_clock_under_10ms(self):
        # quality_budget.performance: 互斥/租约判定开销 ≤10ms 量级.
        # Median-of-9 damps scheduler noise (重复运行零 flake).
        domain = self.seed_target_file()
        fresh = (self.now() - timedelta(minutes=1)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=fresh, ttl_seconds=14400)
        samples = []
        for _ in range(9):
            t0 = time.perf_counter()
            result = self.judge("FIX-100", [domain])
            samples.append(time.perf_counter() - t0)
            self.assertTrue(result["allowed"])
        median = sorted(samples)[len(samples) // 2]
        self.assertLess(median, 0.010,
                        "judge_write median {0:.4f}s blew the 10ms budget"
                        .format(median))

    def test_no_conflict_path_zero_perception(self):
        # ux: 无冲突路径零感知 — begin succeeds instantly, no warnings,
        # no refusals, and end restores the empty-state world.
        domain = self.seed_target_file()
        t0 = time.perf_counter()
        result = self.begin("FIX-100", [domain])
        elapsed = time.perf_counter() - t0
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result.get("warnings"), [])
        self.assertLess(elapsed, 0.5)
        self.assertFalse(self.end("FIX-100", [domain]).get("error"))
        self.assertEqual(self.load_state()["writers"], {})

    def test_status_is_machine_readable_and_greppable(self):
        # accessibility: 谁持锁 / 租约到期时间 / 等待者 all greppable.
        domain = self.seed_target_file()
        self.assertFalse(self.begin("FIX-100", [domain],
                                    ttl_seconds=900).get("error"))
        self.assertRefused(self.begin("FIX-200", [domain]),
                           ei.CODE_WRITE_CONFLICT)
        fresh = (self.now() - timedelta(minutes=1)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain,
                    locked_at=fresh, ttl_seconds=14400)
        status = ei.isolation_status(governance_dir=self.gov,
                                     now=self.now())
        self.assertFalse(status.get("error"), status)
        self.assertEqual(status["writers"][domain]["task_id"], "FIX-100")
        self.assertIn("expires_at", status["writers"][domain])
        lease = status["leases"][domain]
        self.assertEqual(lease["task_id"], "FIX-100")
        self.assertIn("lease_expiry", lease)
        self.assertFalse(lease["expired"])
        waiters = [w for w in status["waiters"]
                   if w["task_id"] == "FIX-200"]
        self.assertEqual(len(waiters), 1)
        text = ei.render_status_text(status)
        for anchor in ("writer domain=", "lease domain=",
                       "lease_expiry=", "waiter domain="):
            self.assertIn(anchor, text)


# ── capability honesty (acceptance ①) ────────────────────────────────


class CapabilityDisclosureTests(unittest.TestCase):
    def test_disclosure_references_feat095_report_without_host_claim(self):
        disclosure = ei.capability_disclosure()
        self.assertIn(ei.CAPABILITY_REPORT_REF, json.dumps(disclosure))
        text = json.dumps(disclosure, ensure_ascii=False)
        # U1 未证实 must be DISCLOSED, never claimed verified.
        self.assertIn("unverified", text)
        self.assertIn("U1", text)
        # the conservative surface is exactly the CLI-level four pieces.
        self.assertEqual(disclosure["conservative_surface"], [
            "shared-file write concurrency limit",
            "same-file-domain under-review/being-written mutex",
            "read-only review snapshots",
            "lease reclaim with loss-of-authority verification",
        ])
        self.assertEqual(disclosure["host_isolation_level"], "unverified")


class mock_env:
    """Context manager for a temporary environment variable."""

    def __init__(self, name, value):
        self.name = name
        self.value = value
        self._saved = None

    def __enter__(self):
        self._saved = os.environ.get(self.name)
        os.environ[self.name] = self.value
        return self

    def __exit__(self, *exc_info):
        if self._saved is None:
            os.environ.pop(self.name, None)
        else:
            os.environ[self.name] = self._saved
        return False


# ── review R0 P1-1: reclaim vs acquire lost-update race ────────────────


class ReclaimProtocolLockTests(IsolationTestCase):
    """P1-1 regression — the reclaim's agent-locks.json read-modify-write
    must run under the file's ESTABLISHED cross-process protocol lock
    (governance_store._TargetLock) with decisions computed against a
    FRESH in-lock read, so a lease committed by a concurrent
    ``agent-locks-acquire`` in the read→write window can never be lost
    (losing an ACTIVE lease re-opens the two-writers-one-domain face —
    the REV-009 class this ticket exists to close)."""

    def test_reclaim_preserves_lease_committed_during_reclaim_window(self):
        # Deterministic lost-update construction: _load_locks is wrapped
        # so that on its SECOND call (the judge's read, which sits in
        # the read→write window between the gate's own load and the
        # reclaim's write-back) a racing acquire's commit lands IN THE
        # FILE additively. Pre-fix (stale in-memory snapshot written
        # back) the racing entry is silently dropped — the assertIn
        # below is the red face.
        domain_a = self.seed_target_file("docs/a.md")   # expired lease
        domain_b = self.seed_target_file("docs/b.md")   # racing commit
        stale = (self.now() - timedelta(hours=3)) \
            .replace(microsecond=0).isoformat()
        _seed_locks(self.gov, task_id="FIX-100", domain=domain_a,
                    locked_at=stale, ttl_seconds=3600)
        original_load = ei._load_locks
        calls = {"n": 0}

        def racing_load(governance_dir, locks_path=None):
            calls["n"] += 1
            if calls["n"] == 2:
                # agent-locks-acquire commits domain_b RIGHT NOW —
                # after the gate's first read, before the reclaim's
                # authoritative re-read under the protocol lock.
                current = json.loads(
                    (self.gov / "agent-locks.json")
                    .read_text(encoding="utf-8"))
                fresh_ts = self.now().replace(microsecond=0).isoformat()
                current["file_locks"][domain_b] = {
                    "locked_by": "FIX-777", "locked_at": fresh_ts,
                    "ttl_seconds": 14400,
                    "ttl_reason": "racing acquire commit",
                }
                current["active_tasks"]["FIX-777"] = {
                    "agent_role": "Developer", "spawned_at": fresh_ts,
                    "coordinator_session": "race",
                    "target_files": [domain_b],
                }
                _write_bytes(self.gov / "agent-locks.json",
                             json.dumps(current, indent=4) + "\n")
            return original_load(governance_dir, locks_path)

        with mock.patch.object(ei, "_load_locks", racing_load):
            result = self.begin("FIX-100", [domain_a])
        self.assertRefused(result, ei.CODE_LEASE_EXPIRED)
        self.assertGreaterEqual(calls["n"], 3,
                                "the reclaim must RE-READ the locks file "
                                "under the protocol lock (fresh read)")
        locks_final = self.load_locks()
        # the racing ACTIVE lease SURVIVES the reclaim write-back…
        self.assertIn(domain_b, locks_final["file_locks"])
        self.assertIn("FIX-777", locks_final["active_tasks"])
        # …while the expired lease is genuinely reclaimed.
        self.assertNotIn(domain_a, locks_final["file_locks"])
        self.assertNotIn("FIX-100", locks_final["active_tasks"])

    def test_reclaim_blocks_on_held_target_lock_cross_process(self):
        # the reclaim path takes the REAL protocol lock: while a
        # governance_store writer holds _TargetLock over agent-locks.json
        # (an in-flight acquire), a cross-process reclaim must WAIT, not
        # write around it. Pre-fix the subprocess finishes in ~ms while
        # the lock is still held → poll() is not None → red.
        # Timestamps are seeded against the REAL clock — the subprocess
        # judge has no injectable now.
        import governance_store as gs
        real_now = datetime.now()
        domain_a = self.seed_target_file("docs/a.md")
        domain_b = self.seed_target_file("docs/b.md")
        stale = (real_now - timedelta(hours=3)) \
            .replace(microsecond=0).isoformat()
        fresh_ts = (real_now - timedelta(minutes=1)) \
            .replace(microsecond=0).isoformat()
        locks = {
            "active_tasks": {
                "FIX-100": {
                    "agent_role": "Developer",
                    "spawned_at": stale,
                    "coordinator_session": "s",
                    "target_files": [domain_a],
                },
                "FIX-777": {
                    "agent_role": "Developer",
                    "spawned_at": fresh_ts,
                    "coordinator_session": "s",
                    "target_files": [domain_b],
                },
            },
            "file_locks": {
                domain_a: {"locked_by": "FIX-100", "locked_at": stale,
                           "ttl_seconds": 3600, "ttl_reason": "seed"},
                domain_b: {"locked_by": "FIX-777", "locked_at": fresh_ts,
                           "ttl_seconds": 14400, "ttl_reason": "seed"},
            },
        }
        _write_bytes(self.gov / "agent-locks.json",
                     json.dumps(locks, indent=4) + "\n")
        locks_file = self.gov / "agent-locks.json"
        # acquire the protocol lock FIRST, then spawn: the subprocess
        # provably arrives at a HELD lock — no startup race.
        with gs._TargetLock(locks_file, 10.0):
            proc = subprocess.Popen(
                [sys.executable, str(MODULE_PATH),
                 "--project-root", str(self.repo),
                 "isolation-lease-reclaim"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # reclaim window while the protocol lock is held by an
            # in-flight governance_store writer
            time.sleep(0.5)
            still_running = proc.poll() is None
        try:
            rc = proc.wait(timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
        self.assertTrue(still_running,
                        "reclaim completed while the agent-locks target "
                        "lock was held — the protocol lock is not taken "
                        "on the reclaim path (P1-1)")
        self.assertEqual(rc, 0)
        locks_final = self.load_locks()
        self.assertNotIn(domain_a, locks_final["file_locks"])  # expired
        self.assertIn(domain_b, locks_final["file_locks"])     # active


# ── review R0 P2-2: domain canonicality + snapshot containment ────────


class DomainCanonicalityTests(IsolationTestCase):
    def test_noncanonical_domains_refused_fail_closed(self):
        canonical = self.seed_target_file("docs/a.md")
        bad_inputs = [
            "docs/../../outside.txt",   # snapshot-root escape vector
            "/abs/path.md",             # absolute path
            "C:/drive/path.md",         # windows drive (also ':' fold)
            "docs//double.md",          # empty segment
            "docs/./dot.md",            # '.' segment
            "docs/\x00nul.md",          # control character
        ]
        for bad in bad_inputs:
            judged = self.judge("FIX-100", [bad])
            self.assertRefused(judged, ei.CODE_SCHEMA_VIOLATION)
            begun = self.begin("FIX-100", [bad])
            self.assertRefused(begun, ei.CODE_SCHEMA_VIOLATION)
            ended = self.end("FIX-100", [bad])
            self.assertRefused(ended, ei.CODE_SCHEMA_VIOLATION)
        # one bad input refuses the WHOLE call (no partial grant)
        mixed = self.begin("FIX-100", [canonical, "docs/../../x.txt"])
        self.assertRefused(mixed, ei.CODE_SCHEMA_VIOLATION)
        self.assertFalse((self.gov / ei.STATE_FILE_NAME).exists(),
                         "a refused non-canonical call must write no "
                         "isolation state")

    def test_snapshot_create_noncanonical_domain_refused_no_escape(self):
        # the escape target EXISTS (the existence check would pass) —
        # only the canonicality gate stops a file landing OUTSIDE the
        # snapshot root.
        escape = (self.repo / "escape.txt")
        _write_bytes(escape, "escaped payload\n")
        snap = self.snapshot("FIX-100", ["docs/../../escape.txt"])
        self.assertRefused(snap, ei.CODE_SCHEMA_VIOLATION)
        snap_root = self.gov / ei.SNAPSHOT_DIR_NAME
        if snap_root.exists():
            self.assertEqual(list(snap_root.rglob("*")), [],
                             "nothing may land under the snapshot root "
                             "from a refused call")
        # no read-only artifact escaped anywhere new
        self.assertEqual(escape.read_text(encoding="utf-8"),
                         "escaped payload\n")

    def test_snapshot_prefix_gate_cannot_be_smuggled_noncanonical(self):
        # pre-P2-2 this spelling resolved INSIDE the snapshot root but
        # missed the literal prefix gate; now the non-canonical input
        # is refused at the door (schema_violation fires BEFORE the
        # snapshot_immutable test can even be consulted).
        smuggle = "docs/../.governance/review-snapshots/SNAP-x/f.md"
        begun = self.begin("FIX-300", [smuggle])
        self.assertRefused(begun, ei.CODE_SCHEMA_VIOLATION)
        snap = self.snapshot("FIX-100", [smuggle])
        self.assertRefused(snap, ei.CODE_SCHEMA_VIOLATION)

    def test_canonical_domains_still_pass_the_gate(self):
        # positive control: the canonicality gate must not over-reach —
        # ordinary repo-relative paths (including dot-directories like
        # .governance hot files) keep flowing through every face.
        domain = self.seed_target_file("docs/a.md")
        self.assertFalse(self.begin("FIX-100", [domain]).get("error"))
        self.assertFalse(self.end("FIX-100", [domain]).get("error"))
        hot = self.seed_target_file(".governance/notes.md")
        judged = self.judge("FIX-100", [hot])
        self.assertTrue(judged["allowed"], judged)


if __name__ == "__main__":
    unittest.main()
