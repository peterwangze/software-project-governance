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
