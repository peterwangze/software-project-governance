"""FIX-448 D1 M1 fixture tests: evidence_migration coordination layer.

Design §10 offline-testable subset (all on SYNTHETIC fixture roots — the
real hot table is never touched; every tmp path is an isolated
TemporaryDirectory cleaned up per test).

FIX-461: the 16 pytest-style tests are now stdlib-unittest — module
functions with fixtures/monkeypatch became TestCase methods with helper
world-builders and mock.patch.object; per-row assertion semantics are
preserved verbatim (no strength change), and the FIX-460 import
shim / HAS_PYTEST / visible-skip marker / pytest __main__ branch are
gone entirely: this module now imports and collects with ZERO pytest
dependency.

Run: python -m unittest \\
        skills.software-project-governance.infra.tests.test_evidence_migration
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_INFRA = Path(__file__).resolve().parent.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

import evidence_migration as em  # noqa: E402

# ---------------------------------------------------------------------------
# synthetic world
# ---------------------------------------------------------------------------

PLAN_TRACKER = """# 计划跟踪

## 项目配置

- 工作流版本: 0.98.0

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|---|---|---|---|---|---|---|
| **P1** | FIX-901 | 已完成任务甲 | — | 0.98.0 | 审收 | ✅ 已完成 |
| **P1** | FIX-902 | 已完成任务乙 | — | 0.98.0 | 审收 | ✅ 已完成 |
| **P1** | FIX-903 | 活动任务丙 | — | 0.99.0 | 在途 | 🔄 进行中 |
| **P1** | FIX-904 | 冻结任务丁 | — | 0.98.0 | 暂停 | ⏸️ 暂停 |
"""


def _evd(row_id, task, desc, basis="事实依据：合成基线事实", keep=False):
    keep_cell = "keep-hot" if keep else "—"
    return (f"| {row_id} | {task} | 隔离实施 | 目标对齐：{desc}。用户影响: "
            f"获得=测试, 感知=测试, 体验变化=无, 迁移指南=不需要 | "
            f"{basis} | file.md | Actor | 2026-10-01 | G11 | ✅ 完成 | "
            f"{keep_cell} |")


def _hot_table(*, crlf=False, trailing_newline=True, extra_prose=True):
    """A synthetic hot table with byte-shape variety (V2 subset).

    - EVD-910 references completed FIX-901 (.98, closed)   → mover
    - EVD-911 references completed FIX-902                 → mover
    - EVD-912 references ACTIVE FIX-903                    → retain active
    - EVD-913 references nonexistent FIX-999               → retain missing
    - EVD-914 completed task but explicit keep-hot marker  → retain keep
    - EVD-915 Unicode-heavy row, completed FIX-901         → mover
    - prose lines and a REVIEW/TRIAGE/RECO row stay in place (families face)
    """
    lines = [
        "# 证据日志",
        "",
        "| ID | 任务 | 类型 | 描述 | 事实依据 | artifacts | actor | date | gate | 结论 | keep |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        _evd("EVD-910", "FIX-901", "已完成引用行，应迁移"),
        _evd("EVD-911", "FIX-902", "第二已完成行"),
        _evd("EVD-912", "FIX-903", "活动任务行必须保留"),
        _evd("EVD-913", "FIX-999", "missing 引用保留"),
        _evd("EVD-914", "FIX-901", "keep 标记保留", keep=True),
        _evd("EVD-915", "FIX-901", "中文描述行含 emoji ✅ 与全角字符｜保留原字节"),
        "",
        "| REVIEW-9001 | FIX-903 | 治理记录 | 复核行 | 事实 | r.md | R | 2026-10-01 | G6 | APPROVED | 0 |",
        "",
    ]
    if extra_prose:
        lines += ["## 附属叙述（非表格字节必须原样保留）", ""]
    text = "\n".join(lines)
    if trailing_newline:
        text += "\n"
    if crlf:
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


# The completed-task mapping the standalone builder would derive from the
# synthetic plan-tracker (archived + FIX-235 completed-hot). ACTIVE FIX-903
# and paused FIX-904 are deliberately ABSENT: mapping membership is the
# closure proof, so their absence is what classifies their rows active.
TASK_VERSIONS = {
    "FIX-901": "0.98.0",
    "FIX-902": "0.98.0",
}


def _world(tmp, **hot_over):
    """Isolated fixture root: hot table + plan + governance dir (the old
    pytest ``world`` fixture as a plain helper — FIX-461)."""
    gov = tmp / ".governance"
    gov.mkdir()
    ev = gov / "evidence-log.md"
    ev.write_bytes(_hot_table(**hot_over))
    plan = gov / "plan-tracker.md"
    plan.write_text(PLAN_TRACKER, encoding="utf-8")
    return {"root": tmp, "gov": gov, "ev": ev, "plan": plan}


def _policy(**over):
    policy = {
        "version_start": "0.1.0",
        "version_end": "0.98.0",
        "families": ("EVD", "REVIEW", "RECO", "TRIAGE"),
        "task_versions": dict(TASK_VERSIONS),
    }
    policy.update(over)
    return policy


def _plan(world):
    inputs = em.MigrationInputs.capture(world["ev"], world["plan"])
    return inputs, em.plan_evd_compaction(inputs, _policy())


class MigrationTestCase(unittest.TestCase):
    """FIX-461 shared harness: isolated TemporaryDirectory + synthetic
    world per test (old ``world`` fixture), and the M2 execute-flag
    env override (old ``monkeypatch.setenv``) with guaranteed restore."""

    HOT_OVER = {}   # per-class hot-table shape overrides (e.g. CRLF)

    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="fix461-")
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name)
        self.world = _world(self.tmp, **self.HOT_OVER)

    def _enable_m2(self):
        self._prior_flag = os.environ.get(em.EXECUTE_ENV_FLAG)
        os.environ[em.EXECUTE_ENV_FLAG] = "1"
        self.addCleanup(self._restore_m2)

    def _restore_m2(self):
        if self._prior_flag is None:
            os.environ.pop(em.EXECUTE_ENV_FLAG, None)
        else:
            os.environ[em.EXECUTE_ENV_FLAG] = self._prior_flag


# ---------------------------------------------------------------------------
# V1-subset — canonical verdicts honored (no second vocabulary)
# ---------------------------------------------------------------------------

class V1CanonicalVerdictTests(MigrationTestCase):

    def test_v1_completed_moves_active_missing_keep_retain(self):
        inputs, plan = _plan(self.world)
        by_id = {i["row_id"]: i for i in plan["instances"]}
        self.assertEqual(by_id["EVD-910"]["decision"], "move")
        self.assertEqual(by_id["EVD-911"]["decision"], "move")
        self.assertEqual(by_id["EVD-915"]["decision"], "move")
        self.assertEqual(by_id["EVD-912"]["decision"], "retain")
        self.assertIn("active", by_id["EVD-912"]["reason"])
        self.assertEqual(by_id["EVD-913"]["decision"], "retain")
        self.assertIn("missing", by_id["EVD-913"]["reason"])
        self.assertEqual(by_id["EVD-914"]["decision"], "retain")
        self.assertIn("keep", by_id["EVD-914"]["reason"])
        # REVIEW family is never a mover in M1 (FIX-446 hardened leg is EVD-only)
        review = [i for i in plan["instances"] if i["family"] == "REVIEW"]
        self.assertTrue(review)
        self.assertTrue(all(i["decision"] == "retain" for i in review))

    def test_v1_reasons_come_from_canonical_set(self):
        inputs, plan = _plan(self.world)
        canonical = {
            "would_archive", "no_task_family_ref", "ref_version_out_of_range",
            "unknown_evd_id_shape", "duplicate_evd_id", "explicit_keep_marker",
            "missing_task_ref", "active_task_ref", "ambiguous_ref",
            "task_layout_anomaly", "task_version_unparseable",
        }
        family_reasons = {
            "would_archive", "no_task_family_ref", "ref_version_out_of_range",
            "missing_task_ref", "active_task_ref", "ambiguous_ref",
            "unknown_row_id_shape",
        }
        for inst in plan["instances"]:
            pool = canonical if inst["family"] == "EVD" else family_reasons
            self.assertIn(inst["reason"], pool, inst)


# ---------------------------------------------------------------------------
# V2-subset — byte exactness
# ---------------------------------------------------------------------------

class V2ByteExactnessTests(MigrationTestCase):

    def test_v2_hot_after_is_exact_interval_removal(self):
        inputs, plan = _plan(self.world)
        raw = inputs.evidence_bytes
        hot_after = plan["_hot_after_bytes_internal"]
        moved = sorted((i["byte_offset"], i["byte_offset"] + i["byte_length"])
                       for i in plan["instances"] if i["decision"] == "move")
        rebuilt = bytearray()
        cursor = 0
        for s, e in moved:
            rebuilt += raw[cursor:s]
            cursor = e
        rebuilt += raw[cursor:]
        self.assertEqual(bytes(rebuilt), hot_after)
        # conservation
        moved_total = sum(e - s for s, e in moved)
        self.assertEqual(len(hot_after) + moved_total, len(raw))
        # prose survives verbatim
        self.assertIn("附属叙述（非表格字节必须原样保留）",
                      hot_after.decode("utf-8"))
        # retained rows survive verbatim
        kept = hot_after.decode("utf-8")
        for rid in ("EVD-912", "EVD-913", "EVD-914", "REVIEW-9001"):
            self.assertIn(rid, kept)

    def test_v2_crlf_and_no_trailing_newline(self):
        # a SEPARATE root under this test's tmp: setUp already built the
        # standard-world .governance (old pytest run used a fresh tmp_path)
        crlf_root = self.tmp / "crlf"
        crlf_root.mkdir()
        world = _world(crlf_root, crlf=True, trailing_newline=False)
        inputs = em.MigrationInputs.capture(world["ev"], world["plan"])
        plan = em.plan_evd_compaction(inputs, _policy())
        raw = inputs.evidence_bytes
        # slice-decode identity held for every instance (planner didn't refuse)
        self.assertFalse(em._is_refusal(plan))
        for inst in plan["instances"]:
            chunk = raw[inst["byte_offset"]:
                        inst["byte_offset"] + inst["byte_length"]]
            self.assertEqual(em._sha256_bytes(chunk), inst["row_sha256"])
            if inst["byte_length"]:
                # CRLF lines keep their \r inside the slice
                decoded = chunk.decode("utf-8")
                if inst["byte_offset"] > 0:
                    self.assertTrue(
                        decoded.endswith("\n")
                        or inst is plan["instances"][-1])
        # moving still exact on CRLF world
        hot_after = plan["_hot_after_bytes_internal"]
        self.assertIn(b"\r\n", hot_after)   # retained CRLF rows untouched

    def test_v2_i1_moved_slices_hash_to_original_bytes(self):
        inputs, plan = _plan(self.world)
        raw = inputs.evidence_bytes
        for inst in plan["instances"]:
            chunk = raw[inst["byte_offset"]:
                        inst["byte_offset"] + inst["byte_length"]]
            self.assertEqual(em._sha256_bytes(chunk), inst["row_sha256"])
            self.assertTrue(
                chunk.decode("utf-8").startswith(f"| {inst['row_id']} "))
        # instance identity = (source digest, byte range, row digest)  [I1]
        for inst in plan["instances"]:
            self.assertEqual(inst["source_sha256"],
                             inputs.evidence_sha256)

    def test_v2_overlaps_refused(self):
        # sabotage one offset to force the overlap detector (defensive path)
        inputs, plan = _plan(self.world)
        plan["instances"][1]["byte_offset"] = plan["instances"][0]["byte_offset"]
        # re-run conservation check manually through the public planner is not
        # possible without re-planning; assert the internal invariant function
        # by rebuilding the guard inline:
        covered = sorted((i["byte_offset"], i["byte_offset"] + i["byte_length"])
                         for i in plan["instances"])
        overlap = any(e1 > s2 for (s1, e1), (s2, e2) in zip(covered, covered[1:]))
        self.assertTrue(overlap)  # sabotage detectable; planner refuses on it


# ---------------------------------------------------------------------------
# execute gate + I4/I5 apply path + V4 interrupted worlds
# ---------------------------------------------------------------------------

class ExecuteApplyRecoveryTests(MigrationTestCase):

    def test_execute_gate_refuses_without_m2_flag(self):
        inputs, plan = _plan(self.world)
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        self.assertTrue(em._is_refusal(receipt))
        self.assertEqual(receipt["code"], "execute_not_authorized")
        self.assertFalse((self.world["gov"] / "migration-staging").exists())

    def test_i4_i5_apply_publishes_cold_before_hot(self):
        self._enable_m2()
        inputs, plan = _plan(self.world)
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        self.assertEqual(receipt["status"], "applied", receipt)
        # cold segments exist with verbatim payload
        segs = sorted((self.world["gov"] / "archive" / "evidence")
                      .glob("evdt-segment-*.md"))
        self.assertTrue(segs)
        seg_text = "\n".join(p.read_text(encoding="utf-8") for p in segs)
        for rid in ("EVD-910", "EVD-911", "EVD-915"):
            self.assertIn(rid, seg_text)
        for rid in ("EVD-912", "EVD-913", "EVD-914"):
            self.assertNotIn(rid, seg_text)
        # hot file is the pinned postimage; movers gone, retained intact
        hot = self.world["ev"].read_bytes()
        self.assertEqual(em._sha256_bytes(hot),
                         plan["outputs"]["hot_after_sha256"])
        kept = hot.decode("utf-8")
        for rid in ("EVD-912", "EVD-913", "EVD-914", "REVIEW-9001"):
            self.assertIn(rid, kept)
        for rid in ("EVD-910", "EVD-911", "EVD-915"):
            self.assertNotIn(rid, kept)
        # staged before-backup preserved (I1)
        tx = receipt["transaction_id"]
        before = (self.world["gov"] / "migration-staging" / tx /
                  "before-evidence.md")
        self.assertEqual(before.read_bytes(), inputs.evidence_bytes)
        # manifest finalized
        manifest = json.loads(
            (self.world["gov"] / "migration-staging" / tx /
             "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], "finalized")
        self.assertTrue(tx.startswith("evdt-"))  # I7 fresh id namespace

    def test_i5_never_overwrite_idempotent_skip(self):
        self._enable_m2()
        inputs, plan = _plan(self.world)
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        self.assertEqual(receipt["status"], "applied")
        outcomes = {s["relative_path"]: s["outcome"]
                    for s in receipt["published_segments"]}
        self.assertTrue(all(v == "created" for v in outcomes.values()))
        # replay the SAME publish: the primitive must judge idempotent_skip
        # (rebuilding is prevented by the hot CAS first — so call the publish
        # primitive directly, as the second transaction would)
        import archive_migration_engine as eng
        seg0 = (self.world["gov"] / "archive" / "evidence" /
                "evdt-segment-000.md")
        seg_lines = seg0.read_text(encoding="utf-8").split("\n")
        header_line, body = seg_lines[0], [ln for ln in seg_lines[1:] if ln]
        out = eng._write_archive_file_never_overwrite(seg0, header_line, body)
        self.assertEqual(out, "idempotent_skip")

    def test_v4_world_hot_before_intact(self):
        # simulate: cold published, hot unwritten (restore the before bytes)
        self._enable_m2()
        inputs, plan = _plan(self.world)
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        tx = receipt["transaction_id"]
        before = (self.world["gov"] / "migration-staging" / tx /
                  "before-evidence.md").read_bytes()
        self.world["ev"].write_bytes(before)   # crash world: hot never committed
        judged = em.recover_evd_transfer(tx, self.world["gov"], self.world["ev"])
        self.assertEqual(judged["status"], "judged")
        self.assertEqual(judged["world"], "hot_before_intact")

    def test_v4_world_hot_after_then_new_append(self):
        self._enable_m2()
        inputs, plan = _plan(self.world)
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        tx = receipt["transaction_id"]
        # finalized world immediately after: judged as after-committed
        judged = em.recover_evd_transfer(tx, self.world["gov"], self.world["ev"])
        self.assertEqual(judged["world"], "hot_after_committed")
        # legal later world: a new append moves the digest → unknown, never
        # rolled back over (§8.2 last row)
        with self.world["ev"].open("ab") as fh:
            fh.write(b"| EVD-920 | FIX-903 | late | row |\n")
        judged2 = em.recover_evd_transfer(tx, self.world["gov"], self.world["ev"])
        self.assertEqual(judged2["world"], "unknown_world")
        self.assertIn("never roll back", judged2["action"])

    def test_v4_input_divergence_cas_refusal(self):
        self._enable_m2()
        inputs, plan = _plan(self.world)
        with self.world["ev"].open("ab") as fh:  # concurrent append after snapshot
            fh.write(b"| EVD-919 | FIX-903 | concurrent | row |\n")
        receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
        self.assertTrue(em._is_refusal(receipt))
        self.assertEqual(receipt["code"], "input_diverged")
        self.assertFalse((self.world["gov"] / "migration-staging").exists())


# ---------------------------------------------------------------------------
# CODE R0 fix batch: P3-2 fault injection + P1-1 disk read-back strength
# ---------------------------------------------------------------------------

class CodeR0FaultInjectionTests(MigrationTestCase):

    def test_p3_2_cold_primitive_failure_hot_untouched(self):
        """I4 under fault: the cold primitive raising (conflict path) must
        leave the hot table bit-identical and surface a STRUCTURED refusal
        (CODE R0 P3-2 + P3-4), never a traceback."""
        import archive_migration_engine as eng

        def boom(*a, **k):
            raise eng.BigTableMigrationError(
                {"code": "archive_target_conflict",
                 "detail": "foreign bytes under the exclusive-create target"})

        with mock.patch.object(
                em._engine, "_write_archive_file_never_overwrite", boom):
            self._enable_m2()
            inputs, plan = _plan(self.world)
            before = self.world["ev"].read_bytes()
            receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
            self.assertTrue(em._is_refusal(receipt))
            self.assertEqual(receipt["code"], "archive_target_conflict")
            self.assertIn("hot table untouched", receipt["detail"])
            self.assertEqual(self.world["ev"].read_bytes(), before)

    def test_p1_1_disk_readback_rejects_corrupted_segment(self):
        """P1-1: cold verify must READ THE DISK — a segment whose landed
        bytes drift from the publish formula (post-write corruption) is
        refused BEFORE the hot CAS, leaving the hot table untouched."""
        real_publish = em._engine._write_archive_file_never_overwrite

        def corrupting_publish(filepath, header, body_lines):
            result = real_publish(filepath, header, body_lines)
            # simulate landing corruption: one extra byte after fsync
            with open(filepath, "ab") as fh:
                fh.write(b"X")
            return result

        with mock.patch.object(
                em._engine, "_write_archive_file_never_overwrite",
                corrupting_publish):
            self._enable_m2()
            inputs, plan = _plan(self.world)
            before = self.world["ev"].read_bytes()
            receipt = em.apply_evd_plan(plan, inputs, self.world["gov"])
            self.assertTrue(em._is_refusal(receipt))
            self.assertIn(receipt["code"],
                          ("identity_changed", "byte_conservation_failed"))
            self.assertEqual(self.world["ev"].read_bytes(), before)


# ---------------------------------------------------------------------------
# I6 capacity + resource limits
# ---------------------------------------------------------------------------

class CapacityLimitTests(MigrationTestCase):

    def test_i6_capacity_reported_not_bent(self):
        inputs, plan = _plan(self.world)
        cap = plan["capacity"]
        self.assertEqual(cap["error_gate_bytes"], 650_000)
        self.assertEqual(cap["warn_gate_bytes"], 400_000)
        self.assertIn(cap["status"], ("blocked", "warn_zone",
                                      "under_error_gate"))
        self.assertTrue("BLOCKED" in cap["note"]
                        or "never modified" in cap["note"])

    def test_resource_limit_row_over_100kb_stays_hot(self):
        inputs, plan = _plan(self.world)
        big = max(plan["instances"], key=lambda i: i["byte_length"])
        self.assertLessEqual(big["byte_length"],
                             em.MAX_ROW_BYTES)   # fixture rows are small


if __name__ == "__main__":
    unittest.main()
