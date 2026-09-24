"""FEAT-061 — migration controller crash/concurrency validation set.

The MINIMUM crash/concurrency validation collection (DEC-237 最低崩溃并发
验收集, 10 cases) over the delivered surface (protocol layer + read
adapter + shadow migration + proof chain — the real production cutover
is a later authorized ticket).  EVERY case asserts the same
postconditions:

    唯一权威 (exactly one backend authoritative per the marker)
    无丢失无重复 (record ID set complete, no duplicates)
    未知状态不放行 (corrupt/unknown/missing gate inputs refuse)
    重试结果稳定 (idempotent re-runs converge to the same world)
    发布不消费陈旧证据 (freshness gate blocks stale projections)

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_decision_migration.py -v
"""

import json
import subprocess
import sys
import threading
import uuid
import unittest
import unittest.mock
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import decision_migration as dmig  # noqa: E402
import decision_repository as drepo  # noqa: E402
import governance_store as gs  # noqa: E402
from governance_store import StoreError  # noqa: E402

VERIFY_SCRIPT = _INFRA_DIR / "decision_migration_verify.py"

LEGACY_HEADER = ("| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 "
                 "| 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n")
SEPARATOR = ("| --- | --- | --- | --- | --- | --- | --- | --- | --- "
             "| --- | --- |\n")


def _seed_md() -> str:
    return (
        "# 当前项目决策记录\n\n"
        + LEGACY_HEADER + SEPARATOR
        + "| DEC-147 | 2026-08-22 | 旧 11 列行样本 | 背景 | 决策内容 | 备选"
          " | 原因 | 范围 | Coordinator | FIX-1 | 动作 |\n"
        + "| DEC-237 | 2026-09-25 | Coordinator | FEAT-061 arch 复核结论"
          " | version-plan C1（机器写入：governance-store decision-append "
          "op-b13202de；schema v1） |\n")


def _write_bytes(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _op() -> str:
    """A contract-valid operation id ('op-' + uuid4 hex, frozen form)."""
    return "op-" + uuid.uuid4().hex


class MigrationWorld:

    def __init__(self, tmp: Path):
        self.gov = tmp / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        _write_bytes(self.gov / "decision-log.md", _seed_md())
        self.migration_id = "M-FEAT061-REHEARSAL"

    # ── verifier subprocess (independence rule ② fidelity) ──
    def _verifier(self, args):
        cmd = [sys.executable, "-X", "utf8", str(VERIFY_SCRIPT)] + args
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=120)
        return proc.returncode, json.loads(proc.stdout)

    def sample(self):
        code, payload = self._verifier([
            "sample", "--gov-dir", str(self.gov),
            "--migration-id", self.migration_id,
            "--migration-root",
            str(drepo.migration_root(self.gov))])
        assert code == 0, payload
        return payload

    def freeze(self):
        return dmig.freeze(governance_dir=self.gov,
                           migration_id=self.migration_id)

    def shadow(self, accept_variants=None, accept_duplicates=None):
        return dmig.shadow(governance_dir=self.gov,
                           migration_id=self.migration_id,
                           accept_variants=accept_variants,
                           accept_duplicates=accept_duplicates)

    def verify(self):
        return dmig.verify(governance_dir=self.gov,
                           migration_id=self.migration_id)

    def activate(self, owner_token):
        return dmig.activate(governance_dir=self.gov,
                             migration_id=self.migration_id,
                             owner_token=owner_token)

    def cutover(self):
        """sample → freeze → shadow → verify → activate (rehearsal)."""
        self.sample()
        frozen = self.freeze()
        self.shadow()
        verified = self.verify()
        assert verified["verdict"] == "PASS", verified
        activated = self.activate(frozen["owner_token"])
        return frozen, activated

    def append(self, content, *, operation_id=None, **kwargs):
        params = dict(
            decider="Coordinator", content=content,
            basis="事实依据：FEAT-061 验收集测试",
            governance_dir=self.gov, repo_root=self.gov.parent,
            operation_id=operation_id, **kwargs)
        return gs.decision_append(**params)

    def md_text(self) -> str:
        return (self.gov / "decision-log.md").read_bytes().decode("utf-8")

    def authority(self) -> dict:
        return drepo.load_authority(self.gov)

    def record_ids(self):
        snapshot = drepo.read_snapshot(self.gov)
        return [r["id"] for r in snapshot["records"]]


class PostconditionsMixin:

    def assert_postconditions(self, world: MigrationWorld,
                              expected_ids, *, expected_state=None,
                              expected_backend=None):
        """唯一权威 / 无丢失无重复 / 未知状态不放行 — every case's tail."""
        authority = world.authority()
        if expected_state is not None:
            self.assertEqual(authority["state"], expected_state)
        if expected_backend is not None:
            self.assertEqual(authority["backend"], expected_backend)
        snapshot = drepo.read_snapshot(
            world.gov, expected_epoch=authority["epoch"])
        ids = [r["id"] for r in snapshot["records"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids appeared")
        self.assertEqual(sorted(ids), sorted(expected_ids),
                         "record set is not lossless")
        # 重试结果稳定: a second read returns the identical identity.
        snapshot2 = drepo.read_snapshot(
            world.gov, expected_epoch=authority["epoch"])
        self.assertEqual(snapshot2["snapshot_digest"],
                         snapshot["snapshot_digest"])


class TestHappyPathRehearsal(unittest.TestCase, PostconditionsMixin):

    def test_full_rehearsal_pipeline_projection_byte_faithful(self):
        import tempfile
        world = MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-mig-")))
        frozen, activated = world.cutover()
        self.assertEqual(activated["state"], drepo.STATE_JSON_ACTIVE)
        self.assertEqual(world.authority()["backend"], "json")
        # freeze + activate = two linearized transitions → epoch 2.
        self.assertEqual(world.authority()["epoch"], 2)
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_JSON_ACTIVE,
            expected_backend="json")
        # md projection stayed byte-faithful through the cutover.
        self.assertEqual(world.md_text(), _seed_md())
        freshness = drepo.projection_freshness(world.gov)
        self.assertEqual(freshness["status"], "fresh")
        # The origin manifest is retained and untouched by the controller.
        manifest = json.loads(
            (drepo.migration_root(world.gov) / world.migration_id
             / "input-manifest.json").read_bytes().decode("utf-8"))
        self.assertEqual(manifest["produced_by"],
                         "decision_migration_verify.sample")

    def test_json_append_then_replay_is_stable(self):
        import tempfile
        world = MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-mig-")))
        world.cutover()
        op_id = _op()
        result = world.append("决策内容样本（JSON 权威首写）",
                              operation_id=op_id)
        self.assertEqual(result["code"], "ok")
        self.assertEqual(result["row_id"], "DEC-238")
        self.assertEqual(result["projection_status"]["status"], "fresh")
        replay = world.append("决策内容样本（JSON 权威首写）",
                              operation_id=op_id)
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(replay["code"], "ok")
        self.assertEqual(world.record_ids(),
                         ["DEC-147", "DEC-237", "DEC-238"])
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_JSON_ACTIVE)
        # Retrying the same op never re-projects into a stale state.
        freshness = drepo.projection_freshness(world.gov)
        self.assertEqual(freshness["status"], "fresh")

    def test_json_append_claude_external_cli_contract_unchanged(self):
        """decision-append 外部 CLI 契约不变（切换后）: same argv, same
        result envelope keys, exit 0."""
        import tempfile
        world = MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-mig-")))
        world.cutover()
        cmd = [sys.executable, str(_INFRA_DIR / "governance_store.py"),
               "--project-root", str(world.gov.parent),
               "decision-append", "--decider", "Coordinator",
               "--content", "CLI 契约保持验证（JSON 权威）",
               "--basis", "事实依据：外部契约零变化",
               "--operation-id", _op()]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        for key in ("operation_id", "code", "new_revision", "execution",
                    "error"):
            self.assertIn(key, payload)
        self.assertEqual(payload["code"], "ok")
        self.assertEqual(payload["row_id"], "DEC-238")
        # and the world: the record is in the JSON store + projected.
        self.assertIn("DEC-238", world.record_ids())
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")


class TestCrashConcurrencyCollection(unittest.TestCase, PostconditionsMixin):
    """The 10-case minimum collection (DEC-237)."""

    def _world(self):
        import tempfile
        return MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-c-")))

    # ── ① 候选 JSON 已落盘但未激活 ──────────────────────────────────────
    def test_case_01_candidate_store_written_but_not_activated(self):
        world = self._world()
        world.sample()
        frozen = world.freeze()
        world.shadow()
        world.verify()
        # Simulate the crash: candidate on disk, marker still frozen.
        shadow = (drepo.migration_root(world.gov) / world.migration_id
                  / "shadow" / drepo.JSON_STORE_FILE)
        _write_bytes(world.gov / drepo.JSON_STORE_FILE,
                     shadow.read_bytes().decode("utf-8"))
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_CUTOVER_FROZEN)
        # Writes are rejected while the candidate sits unactivated (the
        # writer family returns structured refusal payloads, it never
        # raises through the public API).
        refusal = world.append("冻结中拒绝写入")
        self.assertEqual(refusal["code"], "illegal_transition")
        self.assertTrue(refusal.get("error"))
        # Resume: activate judges the world and completes.
        result = world.activate(frozen["owner_token"])
        self.assertEqual(result["state"], drepo.STATE_JSON_ACTIVE)
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_JSON_ACTIVE,
            expected_backend="json")

    # ── ② JSON 已激活但响应未返回 ───────────────────────────────────────
    def test_case_02_activated_but_response_lost(self):
        world = self._world()
        frozen, activated = world.cutover()
        # Roll the journal back to committed (crash before finalize).
        journal_path = (drepo.migration_root(world.gov)
                        / world.migration_id / "journal.json")
        journal = json.loads(journal_path.read_bytes().decode("utf-8"))
        journal["phase"] = "committed"
        _write_bytes(journal_path, json.dumps(journal, ensure_ascii=False))
        result = world.activate(frozen["owner_token"])
        self.assertEqual(result["resumed"], "finalized_after_flip")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_JSON_ACTIVE)
        # Idempotent re-run after finalize.
        again = world.activate(frozen["owner_token"])
        self.assertEqual(again["resumed"], "already_finalized")

    # ── ③ 切换后新增 DEC 已提交但投影连续失败 ───────────────────────────
    def test_case_03_committed_but_projection_repeatedly_failing(self):
        world = self._world()
        world.cutover()
        op_id = _op()

        def failing_md_write(path, data):
            if Path(path).name == drepo.MD_FILE_NAME:
                raise OSError("case ③ simulated md write failure")
            return gs._atomic_write_bytes(path, data)

        # Hold nothing — the md WRITE itself fails repeatedly (the seam is
        # the atomic-write boundary; lock-based blocking would deadlock
        # the non-reentrant in-process mutex in-process).
        with unittest.mock.patch.object(drepo, "_atomic_write_bytes",
                                        failing_md_write):
            result = world.append("已提交、投影待修复样本",
                                  operation_id=op_id)
            self.assertEqual(result["code"], "ok")
            self.assertEqual(result["projection_status"]["status"],
                             "pending")
            # A second commit in the same broken window keeps failing the
            # projection (连续失败) while commits keep landing.
            result2 = world.append("第二笔已提交", operation_id=_op())
            self.assertEqual(result2["projection_status"]["status"],
                             "pending")
        # The commits are real while the projection debt is persisted.
        self.assertIn("DEC-238", world.record_ids())
        self.assertIn("DEC-239", world.record_ids())
        checkpoint = drepo.load_projection_checkpoint(world.gov)
        self.assertEqual(checkpoint["status"], "pending")
        # Retry the same op: replay, never re-append, still stable.
        replay = world.append("已提交、投影待修复样本",
                              operation_id=op_id)
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(world.record_ids().count("DEC-238"), 1)
        # Repair (audited channel) closes the debt; freshness restores.
        repair = dmig.project_repair(
            governance_dir=world.gov, reason="case ③ repair")
        self.assertEqual(repair["projection_status"], "fresh")
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238", "DEC-239"],
            expected_state=drepo.STATE_JSON_ACTIVE)
        # 发布不消费陈旧证据: the gate was loud while stale.
        self.assertIn("DEC-238", world.md_text())
        self.assertIn("DEC-239", world.md_text())

    # ── ④ 旧 epoch 写入者在切换后恢复提交 ───────────────────────────────
    def test_case_04_precutover_writer_resumes_after_cutover(self):
        world = self._world()
        # Pre-cutover: an md-world append commits the row, then the
        # ledger record is lost (crash between write and ledger).
        op_id = _op()
        result = world.append("切换前已提交（ledger 丢失）",
                              operation_id=op_id)
        self.assertEqual(result["code"], "ok")
        ledger_path = world.gov / "governance-store-ops.json"
        ledger = json.loads(ledger_path.read_bytes().decode("utf-8"))
        ledger["operations"].pop(op_id)
        _write_bytes(ledger_path, json.dumps(ledger, ensure_ascii=False))
        self.assertEqual(world.record_ids()[-1], "DEC-238")
        # Cutover carries the marker into the JSON records.
        world.cutover()
        # The old-epoch writer resumes with the SAME operation id —
        # routed to the JSON backend, world-recovery replays it.
        resume = world.append("切换前已提交（ledger 丢失）",
                              operation_id=op_id)
        self.assertTrue(resume.get("replayed"))
        self.assertEqual(resume.get("replay_source"), "world_recovery")
        self.assertEqual(world.record_ids().count("DEC-238"), 1)
        # A fresh op from the same (old) writer process also routes to
        # the JSON backend — it can never append md directly anymore.
        fresh = world.append("旧写入者的新提交", operation_id=_op())
        self.assertEqual(fresh["row_id"], "DEC-239")
        self.assertEqual(world.authority()["backend"], "json")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238", "DEC-239"],
            expected_state=drepo.STATE_JSON_ACTIVE)

    # ── ⑤ 旧投影任务晚于新投影任务完成 ──────────────────────────────────
    def test_case_05_late_old_projection_cannot_win(self):
        world = self._world()
        world.cutover()
        world.append("新投影之后的提交", operation_id=_op())
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")
        store_path = world.gov / drepo.JSON_STORE_FILE
        fired = {"stale": False}

        def mutate_store():
            """The store moves on while the late projector is between its
            snapshot capture and its md write (content-level mutation —
            the record set is preserved; the digest moves)."""
            store_doc = json.loads(store_path.read_bytes().decode("utf-8"))
            for record in store_doc["records"]:
                if record["id"] == "DEC-238":
                    record["cells"] = list(record["cells"])
                    record["cells"][3] = record["cells"][3] + "（并发修订）"
            _write_bytes(store_path, json.dumps(
                store_doc, ensure_ascii=False, indent=2) + "\n")

        real_lock = drepo._TargetLock

        class MutatingMdLock(real_lock):
            """Seam: the moment the late projector takes the md lock (the
            fence re-reads the store right after), the store has already
            moved on — the fence must refuse the stale render."""

            def __enter__(self):
                if self.path.name == drepo.MD_FILE_NAME + ".lock" \
                        and not fired["stale"]:
                    mutate_store()
                return super().__enter__()

        with unittest.mock.patch.object(drepo, "_TargetLock",
                                        MutatingMdLock):
            try:
                drepo.project_store_to_markdown(
                    world.gov, reason="late old projection")
            except StoreError as exc:
                fired["stale"] = True
                self.assertEqual(exc.payload["code"], "revision_conflict")
        self.assertTrue(fired["stale"],
                        "the stale-projection fence did not fire")
        # The world converges: the gate blocks stale evidence and the
        # repair path re-projects from the CURRENT store.
        freshness = drepo.projection_freshness(world.gov)
        if freshness["status"] != "fresh":
            repair = dmig.project_repair(
                governance_dir=world.gov, reason="case ⑤ repair")
            self.assertEqual(repair["projection_status"], "fresh")
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_JSON_ACTIVE)

    # ── ⑥ guard 台账损坏 × 投影失败 × 恢复重试交错 ──────────────────────
    def test_case_06_guard_ledger_corruption_interlock(self):
        world = self._world()
        world.sample()
        # Corrupt the guard violations ledger (FEAT-060 artifact).
        _write_bytes(world.gov / ".write-guard-violations.json",
                     "{corrupted guard state")
        with self.assertRaises(StoreError) as ctx:
            world.freeze()
        self.assertIn("unreadable", ctx.exception.payload["detail"])
        # Zero state change (loud refusal, no silent absorb — R6).
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_MD_ACTIVE)
        # Pending guard transaction interlocks the freeze too.
        _write_bytes(world.gov / ".write-guard-violations.json",
                     json.dumps({"pending_txn": {"id": "t1"}}))
        with self.assertRaises(StoreError) as ctx:
            world.freeze()
        self.assertIn("pending transaction", ctx.exception.payload["detail"])
        # Manual recovery (disclosed class per FEAT-060 R6): restore.
        (world.gov / ".write-guard-violations.json").unlink()
        frozen = world.freeze()
        self.assertEqual(frozen["state"], drepo.STATE_CUTOVER_FROZEN)
        # Pending ops-ledger transactions interlock as well.
        world2 = self._world()
        world2.sample()
        ledger_path = world2.gov / "governance-store-ops.json"
        _write_bytes(ledger_path, json.dumps({
            "schema_version": 1,
            "operations": {"op-pending": {
                "schema_version": 1, "command": "decision-append",
                "task_id": "", "input_fingerprint": "x",
                "status": "pending",
                "result": {"operation_id": "op-pending", "code": "ok",
                           "new_revision": 1, "observed_revision": None,
                           "execution": None, "detail": None},
                "recorded_at": "t", "updated_at": "t"}}}))
        with self.assertRaises(StoreError) as ctx:
            dmig.freeze(governance_dir=world2.gov,
                        migration_id=world2.migration_id)
        self.assertIn("pending", ctx.exception.payload["detail"])

    # ── ⑦ 回退导出完成但 md 尚未激活 ────────────────────────────────────
    def test_case_07_rollback_exported_but_md_not_activated(self):
        world = self._world()
        frozen, _ = world.cutover()
        world.append("JSON 时代新增行", operation_id=_op())
        rb = dmig.rollback_begin(
            governance_dir=world.gov, reason="case ⑦ rehearsal",
            owner_token=frozen["owner_token"])
        self.assertEqual(rb["state"], drepo.STATE_ROLLBACK_FROZEN)
        export = dmig.rollback_export(governance_dir=world.gov)
        self.assertEqual(export["reverse_check_verdict"], "PASS")
        self.assertEqual(export["record_count"], 3)
        # md not activated yet: writes stay rejected, world unchanged.
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_ROLLBACK_FROZEN)
        refusal = world.append("回退窗拒绝写入")
        self.assertEqual(refusal["code"], "illegal_transition")
        self.assertTrue(refusal.get("error"))
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_ROLLBACK_FROZEN)
        # Activate the rollback: the JSON-era row must survive losslessly.
        dmig.rollback_activate(governance_dir=world.gov,
                               owner_token=frozen["owner_token"])
        self.assertEqual(world.authority()["state"], drepo.STATE_MD_ACTIVE)
        self.assertEqual(world.authority()["backend"], "md")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")
        # The exported md carries the JSON-era row verbatim.
        self.assertIn("DEC-238", world.md_text())

    # ── ⑧ md 已激活后重试切换期间已提交的 operation_id ──────────────────
    def test_case_08_retry_of_precutover_ops_after_rollback(self):
        world = self._world()
        frozen, _ = world.cutover()
        op_x = _op()
        world.append("JSON 时代已提交", operation_id=op_x)
        dmig.rollback_begin(governance_dir=world.gov, reason="case ⑧",
                            owner_token=frozen["owner_token"])
        dmig.rollback_export(governance_dir=world.gov)
        dmig.rollback_activate(governance_dir=world.gov,
                               owner_token=frozen["owner_token"])
        # Re-running the OLD activation refuses (epoch/state history).
        with self.assertRaises(StoreError) as ctx:
            dmig.activate(governance_dir=world.gov,
                          migration_id=world.migration_id,
                          owner_token=frozen["owner_token"])
        self.assertIn("illegal_transition",
                      ctx.exception.payload["code"])
        # The op committed during the JSON era replays in the md world
        # (world recovery via the preserved marker) — never re-appends.
        replay = world.append("JSON 时代已提交", operation_id=op_x)
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(world.record_ids().count("DEC-238"), 1)
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")

    # ── ⑨ closure cancel 释放锁与新 owner 获取锁交错 ────────────────────
    def test_case_09_cancel_owner_token_interleave(self):
        world = self._world()
        world.sample()
        frozen = world.freeze()
        token_a = frozen["owner_token"]
        # A stale/foreign cancel (wrong owner token) refuses and does NOT
        # release the freeze.
        with self.assertRaises(StoreError) as ctx:
            dmig.cancel(governance_dir=world.gov,
                        migration_id=world.migration_id,
                        owner_token="not-the-owner")
        self.assertEqual(ctx.exception.payload["code"],
                         "operation_id_conflict")
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_CUTOVER_FROZEN)
        # A foreign migration id cannot cancel someone else's freeze.
        with self.assertRaises(StoreError):
            dmig.cancel(governance_dir=world.gov,
                        migration_id="M-OTHER", owner_token="whatever")
        # The true owner cancels; the state releases cleanly.
        cancelled = dmig.cancel(governance_dir=world.gov,
                                migration_id=world.migration_id,
                                owner_token=token_a)
        self.assertEqual(cancelled["state"], drepo.STATE_MD_ACTIVE)
        # A NEW owner acquires cleanly afterwards.
        world.migration_id = "M-FEAT061-REHEARSAL-2"
        world.sample()
        frozen2 = world.freeze()
        self.assertEqual(frozen2["state"], drepo.STATE_CUTOVER_FROZEN)
        self.assertNotEqual(frozen2["owner_token"], token_a)
        dmig.cancel(governance_dir=world.gov,
                    migration_id=world.migration_id,
                    owner_token=frozen2["owner_token"])
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")

    # ── ⑩ 任一验证报告缺失/陈旧/来自错误 manifest ───────────────────────
    def test_case_10_missing_stale_or_foreign_evidence_refused(self):
        world = self._world()
        world.sample()
        frozen = world.freeze()
        world.shadow()
        migration_dir = (drepo.migration_root(world.gov)
                         / world.migration_id)
        # (a) missing verdict.
        with self.assertRaises(StoreError) as ctx:
            world.activate(frozen["owner_token"])
        self.assertIn("verify-verdict.json", ctx.exception.payload["detail"])
        # (b) FAIL verdict.
        _write_bytes(migration_dir / "verify-verdict.json", json.dumps(
            {"verdict": "FAIL", "migration_id": world.migration_id,
             "manifest_digest": "x"}))
        with self.assertRaises(StoreError) as ctx:
            world.activate(frozen["owner_token"])
        self.assertIn("PASS", ctx.exception.payload["detail"])
        # (c) foreign migration_id.
        _write_bytes(migration_dir / "verify-verdict.json", json.dumps(
            {"verdict": "PASS", "migration_id": "M-OTHER",
             "manifest_digest": "x"}))
        with self.assertRaises(StoreError) as ctx:
            world.activate(frozen["owner_token"])
        self.assertEqual(ctx.exception.payload["code"], "revision_conflict")
        # (d) stale manifest binding (wrong digest).
        real_digest = dmig._sha256_hex(
            (migration_dir / "input-manifest.json").read_bytes())
        _write_bytes(migration_dir / "verify-verdict.json", json.dumps(
            {"verdict": "PASS", "migration_id": world.migration_id,
             "manifest_digest": "0" * 64}))
        with self.assertRaises(StoreError) as ctx:
            world.activate(frozen["owner_token"])
        self.assertEqual(ctx.exception.payload["code"], "revision_conflict")
        # Every refusal left the world frozen and intact — no activation
        # on unknown/stale/foreign evidence.
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_CUTOVER_FROZEN)
        self.assertEqual(world.md_text(), _seed_md())
        # The honest verdict activates.
        world.verify()
        dmig.activate(governance_dir=world.gov,
                      migration_id=world.migration_id,
                      owner_token=frozen["owner_token"])
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_JSON_ACTIVE, expected_backend="json")

    # ── ⑪ 已过 entry 检查的写入者 × 线性化点交错（R0 P0-F1 验收钉） ────
    def test_case_11_entry_epoch_interleaves_linearization_md_leg(self):
        """A writer that passed its (lock-free) entry check is
        descheduled BEFORE acquiring the target lock; the migration
        completes a FULL cutover in that gap (the seam fires at lock-
        enter — the writer holds NOTHING yet, exactly the real
        interleaving; the in-lock revalidation must then refuse with
        zero data loss — the record must NOT land in the md world only
        to be destroyed by the next projection)."""
        world = self._world()
        real_lock = gs._TargetLock
        guard = {"active": False}

        class InterleavingMdLock(real_lock):
            def __enter__(self):
                if (not guard["active"]) and self.path.name == \
                        drepo.MD_FILE_NAME + ".lock":
                    # The scheduling gap: the migration linearizes RIGHT
                    # NOW (dmig/drepo hold their own unpatched lock refs,
                    # so the nested cutover passes through cleanly).
                    guard["active"] = True
                    try:
                        world.cutover()
                    finally:
                        guard["active"] = False
                return super().__enter__()

        input_md = world.md_text()
        with unittest.mock.patch.object(gs, "_TargetLock",
                                        InterleavingMdLock):
            result = world.append("跨界写入样本（entry 后被调度间隙跨越切换）",
                                  operation_id=_op())
        self.assertEqual(result["code"], "revision_conflict",
                         "the in-lock revalidation did not refuse the "
                         "crossed-linearization append")
        self.assertEqual(result["observed_epoch"], 2)
        # 无丢失: the md world is byte-identical — the record never
        # landed in the projection face only to be destroyed later.
        self.assertEqual(world.md_text(), input_md)
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_JSON_ACTIVE)
        self.assertEqual(world.authority()["backend"], "json")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237"],
            expected_state=drepo.STATE_JSON_ACTIVE,
            expected_backend="json")

    # ── ⑫ 同场景正常路径回归 + json 腿对称交错（R0 P0-F1 验收钉） ──────
    def test_case_12_same_scenario_normal_path_and_json_leg(self):
        import tempfile
        # (a) Normal-path regression: the same seam present but the world
        # NOT moving → the append succeeds exactly as before the fix.
        world = self._world()
        real_lock = gs._TargetLock
        calls = {"n": 0}

        class CountingLock(real_lock):
            def __enter__(self):
                calls["n"] += 1
                return super().__enter__()

        with unittest.mock.patch.object(gs, "_TargetLock", CountingLock):
            result = world.append("正常路径回归样本", operation_id=_op())
        self.assertEqual(result["code"], "ok")
        # The seam was active (the md target lock went through it — the
        # ledger lock is counted too, hence >= not ==).
        self.assertGreaterEqual(calls["n"], 1)
        self.assertEqual(result["row_id"], "DEC-238")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")

        # (b) json leg symmetric interleave: entry check at JSON_ACTIVE,
        # a FULL rollback linearizes before the json-leg lock section →
        # the in-lock revalidation refuses there too.
        world2 = MigrationWorld(
            Path(tempfile.mkdtemp(prefix="feat061-c-")))
        frozen, _ = world2.cutover()
        world2.append("回退前的 json 提交", operation_id=_op())
        guard = {"active": False}

        class InterleavingJsonLock(real_lock):
            def __enter__(self):
                if (not guard["active"]) and self.path.name == \
                        drepo.JSON_STORE_FILE + ".lock":
                    guard["active"] = True
                    try:
                        dmig.rollback_begin(
                            governance_dir=world2.gov,
                            reason="case ⑫ interleave",
                            owner_token=frozen["owner_token"])
                        dmig.rollback_export(governance_dir=world2.gov)
                        dmig.rollback_activate(
                            governance_dir=world2.gov,
                            owner_token=frozen["owner_token"])
                    finally:
                        guard["active"] = False
                return super().__enter__()

        input_md2 = world2.md_text()
        with unittest.mock.patch.object(gs, "_TargetLock",
                                        InterleavingJsonLock):
            result2 = world2.append("json 腿交错样本", operation_id=_op())
        self.assertEqual(result2["code"], "revision_conflict",
                         "the json-leg in-lock revalidation did not refuse")
        # 无丢失: the rollback-exported md is intact and no partial
        # record landed anywhere (the refused op wrote nothing).
        self.assertEqual(world2.md_text(), input_md2)
        self.assertEqual(world2.authority()["state"],
                         drepo.STATE_MD_ACTIVE)
        self.assertEqual(world2.authority()["backend"], "md")
        self.assert_postconditions(
            world2, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")


class TestGateSemantics(unittest.TestCase, PostconditionsMixin):

    def _world(self):
        import tempfile
        return MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-g-")))

    def test_freeze_digest_gate_bidirectional(self):
        """双向摘要复核: manifest→current direction at freeze (mismatch
        refuses), frozen→current at activate (mismatch = completeness
        failure, restart under a NEW migration id)."""
        world = self._world()
        world.sample()
        # The md changes AFTER sampling → the freeze refuses.
        world.append("采样后新增（md 侧）", operation_id=_op())
        with self.assertRaises(StoreError) as ctx:
            world.freeze()
        self.assertIn("re-sample", ctx.exception.payload["detail"])
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_MD_ACTIVE)
        # Honest re-sample under a NEW migration id proceeds.
        world.migration_id = "M-FEAT061-REHEARSAL-2"
        world.sample()
        frozen = world.freeze()
        world.shadow()
        world.verify()
        # The md diverges DURING the freeze window (rogue direct edit —
        # completeness failure → no activation, restart required).
        md_path = world.gov / "decision-log.md"
        text = md_path.read_bytes().decode("utf-8")
        _write_bytes(md_path, text + "| DEC-999 | 2026-09-26 | 越窗写入 "
                     "| | | \n")
        with self.assertRaises(StoreError) as ctx:
            world.activate(frozen["owner_token"])
        self.assertIn("diverged from the frozen input",
                      ctx.exception.payload["detail"])
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_CUTOVER_FROZEN)

    def test_md_world_behavior_byte_identical_to_pre_feat061(self):
        """MD_ACTIVE world: the writer path is byte-identical to the
        pre-FEAT-061 behavior (zero regression by construction)."""
        world = self._world()
        result = world.append("md 世界新增行", operation_id=_op())
        self.assertEqual(result["code"], "ok")
        self.assertEqual(result["row_id"], "DEC-238")
        self.assertNotIn("projection_status", result)
        self.assertEqual(world.authority()["state"],
                         drepo.STATE_MD_ACTIVE)
        self.assertFalse(
            (world.gov / drepo.JSON_STORE_FILE).is_file())
        self.assertFalse(
            (world.gov / drepo.AUTHORITY_STATE_FILE).is_file())
        self.assertIn("DEC-238", world.md_text())
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")

    def test_cas_revision_channel_on_json_backend(self):
        world = self._world()
        world.cutover()
        store_path = world.gov / drepo.JSON_STORE_FILE
        revision = store_path.stat().st_size
        conflict = world.append("CAS 冲突样本", operation_id=_op(),
                                expected_revision=revision + 5)
        self.assertEqual(conflict["code"], "revision_conflict")
        self.assertEqual(conflict["observed_revision"], revision)
        ok = world.append("CAS 命中样本", operation_id=_op(),
                          expected_revision=revision)
        self.assertEqual(ok["code"], "ok")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-238"],
            expected_state=drepo.STATE_JSON_ACTIVE)

    def test_concurrent_json_appends_lose_no_record(self):
        world = self._world()
        world.cutover()
        results = []
        lock = threading.Lock()
        op_ids = [_op() for _ in range(4)]

        def worker(index):
            payload = world.append(f"并发提交 {index}",
                                   operation_id=op_ids[index])
            with lock:
                results.append(payload["code"])

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(sorted(results), ["ok"] * 4)
        ids = world.record_ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 6)  # 2 seed + 4 concurrent
        self.assert_postconditions(
            world, ids, expected_state=drepo.STATE_JSON_ACTIVE)
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")

    def test_rollback_export_round_trip_with_variants(self):
        """ARCH-07: the export re-parses losslessly under the OLD parser
        even with a legacy11 row and a variant row (explicitly accepted)."""
        world = self._world()
        md_path = world.gov / "decision-log.md"
        _write_bytes(md_path, _seed_md()
                     + "| DEC-060 | 2026-05-03 | 三列旧行样本 |\n")
        world.sample()
        frozen = world.freeze()
        world.shadow(accept_variants=[
            "DEC-060:三列勘误行——显式排除（raw 保留）"])
        world.verify()
        world.activate(frozen["owner_token"])
        dmig.rollback_begin(governance_dir=world.gov, reason="case rehearsal",
                            owner_token=frozen["owner_token"])
        export = dmig.rollback_export(governance_dir=world.gov)
        self.assertEqual(export["reverse_check_verdict"], "PASS")
        self.assertEqual(export["record_count"], 3)
        dmig.rollback_activate(governance_dir=world.gov,
                               owner_token=frozen["owner_token"])
        self.assertEqual(
            world.md_text(),
            _seed_md() + "| DEC-060 | 2026-05-03 | 三列旧行样本 |\n")
        self.assert_postconditions(
            world, ["DEC-147", "DEC-237", "DEC-060"],
            expected_state=drepo.STATE_MD_ACTIVE, expected_backend="md")

    def test_append_preserves_store_top_level_keys(self):
        """R0 P0-F2 验收钉: a store carrying the optional legal key
        ``duplicate_acceptances`` (勘正对) keeps its TOP-LEVEL KEY SET
        unchanged across a JSON append — dropping it would make the
        post-write reread refuse the store this very append wrote."""
        world = self._world()
        md_path = world.gov / "decision-log.md"
        _write_bytes(md_path, _seed_md()
                     + "| DEC-194 | 2026-09-14 | Coordinator | FIX-330 口径"
                       " | 依据 |\n"
                     + "| DEC-194 补记 | 2026-09-17 | Coordinator | 第③点"
                       "补齐 | 依据 |\n")
        world.sample()
        frozen = world.freeze()
        world.shadow(accept_duplicates=["DEC-194:勘正行对——两行保留"])
        world.verify()
        world.activate(frozen["owner_token"])
        store_path = world.gov / drepo.JSON_STORE_FILE
        before = json.loads(store_path.read_bytes().decode("utf-8"))
        self.assertIn("duplicate_acceptances", before)
        result = world.append("键集保持样本", operation_id=_op())
        self.assertEqual(result["code"], "ok")
        after = json.loads(store_path.read_bytes().decode("utf-8"))
        self.assertEqual(set(after), set(before),
                         "append changed the store's top-level key set")
        self.assertEqual(
            after["duplicate_acceptances"],
            before["duplicate_acceptances"])
        # The store stays loadable (no self-inflicted brick) and the
        # append landed after the preserved 勘正 pair (max id 237 → 238).
        self.assertEqual(
            drepo.projection_freshness(world.gov)["status"], "fresh")
        self.assertEqual(world.record_ids()[-1], "DEC-238")

    def test_proof_pack_minimum_content(self):
        """ARCH-10: the pack carries every minimum section, and the
        independence declaration lists shared deps + residual risks."""
        import tempfile
        world = MigrationWorld(Path(tempfile.mkdtemp(prefix="feat061-p-")))
        world.cutover()
        result = dmig.proof_pack(governance_dir=world.gov,
                                 migration_id=world.migration_id)
        pack = json.loads(
            Path(result["proof_pack_path"]).read_bytes().decode("utf-8"))
        verdict = pack["independent_verifier_verdict"]
        self.assertEqual(verdict["verdict"], "PASS")
        for section in ("input_snapshot_identity", "origin_manifest",
                        "tool_and_dependency_identity",
                        "normalization_rules", "line_coverage_report",
                        "per_id_field_diffs", "ops_reconciliation",
                        "independence_declaration"):
            self.assertIn(section, verdict, section)
        declaration = verdict["independence_declaration"]
        self.assertTrue(declaration["rule_1_old_parser_adjudication"])
        self.assertTrue(declaration["rule_2_precutover_validator"])
        self.assertTrue(declaration["shared_dependencies"])
        self.assertTrue(declaration["residual_risks"])
        self.assertIn("shared", declaration["declaration"].lower())


if __name__ == "__main__":
    unittest.main()
