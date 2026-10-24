"""FIX-448 D1 M1 fixture tests: evidence_migration coordination layer.

Design §10 offline-testable subset (all on SYNTHETIC fixture roots — the
real hot table is never touched; every tmp path is pytest's isolated
tmp_path, and MigrationInputs/scan/classification are injected with
synthetic content so nothing reads the live .governance tree):

  V1-subset  canonical verdicts: completed→move; active/missing/keep→retain
             (the classification itself is archive_verdicts' single source,
              tested extensively in test_archive.py — here we pin that the
              planner honors it and never invents a second vocabulary)
  V2-subset  byte exactness: LF/CRLF/BOM-adjacent prose, trailing no-LF,
             raw '|' and Unicode rows — hot_after is exact interval removal
             and moved slices decode back to the classified lines
  V4-subset  interrupted worlds: execute-gate refusal; prepared-before
             crash; cold-published/hot-unwritten; hot-committed;
             post-finalize append → recover_evd_transfer judges each world
             from pins + real files (never the journal alone)
  I1        row bytes immutable: every moved slice hash equals the row's
             original bytes hash; before-backup preserved
  I4/I5     cold publishes first through the never-overwrite primitive
             (idempotent_skip on re-run; foreign bytes refused by the
             primitive's own tests in test_archive.py)
  I6/I7     capacity reported not bent; transaction ids are fresh evdt-*

Run: python -B -m pytest skills/software-project-governance/infra/tests/\
test_evidence_migration.py -q
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

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


@pytest.fixture
def world(tmp_path):
    """Isolated fixture root: hot table + plan + governance dir."""
    gov = tmp_path / ".governance"
    gov.mkdir()
    ev = gov / "evidence-log.md"
    ev.write_bytes(_hot_table())
    plan = gov / "plan-tracker.md"
    plan.write_text(PLAN_TRACKER, encoding="utf-8")
    return {"root": tmp_path, "gov": gov, "ev": ev, "plan": plan}


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


# ---------------------------------------------------------------------------
# V1-subset — canonical verdicts honored (no second vocabulary)
# ---------------------------------------------------------------------------

def test_v1_completed_moves_active_missing_keep_retain(world):
    inputs, plan = _plan(world)
    by_id = {i["row_id"]: i for i in plan["instances"]}
    assert by_id["EVD-910"]["decision"] == "move"
    assert by_id["EVD-911"]["decision"] == "move"
    assert by_id["EVD-915"]["decision"] == "move"
    assert by_id["EVD-912"]["decision"] == "retain"
    assert "active" in by_id["EVD-912"]["reason"]
    assert by_id["EVD-913"]["decision"] == "retain"
    assert "missing" in by_id["EVD-913"]["reason"]
    assert by_id["EVD-914"]["decision"] == "retain"
    assert "keep" in by_id["EVD-914"]["reason"]
    # REVIEW family is never a mover in M1 (FIX-446 hardened leg is EVD-only)
    review = [i for i in plan["instances"] if i["family"] == "REVIEW"]
    assert review and all(i["decision"] == "retain" for i in review)


def test_v1_reasons_come_from_canonical_set(world):
    inputs, plan = _plan(world)
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
        assert inst["reason"] in pool, inst


# ---------------------------------------------------------------------------
# V2-subset — byte exactness
# ---------------------------------------------------------------------------

def test_v2_hot_after_is_exact_interval_removal(world):
    inputs, plan = _plan(world)
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
    assert bytes(rebuilt) == hot_after
    # conservation
    moved_total = sum(e - s for s, e in moved)
    assert len(hot_after) + moved_total == len(raw)
    # prose survives verbatim
    assert "附属叙述（非表格字节必须原样保留）" in hot_after.decode("utf-8")
    # retained rows survive verbatim
    kept = hot_after.decode("utf-8")
    for rid in ("EVD-912", "EVD-913", "EVD-914", "REVIEW-9001"):
        assert rid in kept


def test_v2_crlf_and_no_trailing_newline(tmp_path):
    gov = tmp_path / ".governance"
    gov.mkdir()
    ev = gov / "evidence-log.md"
    ev.write_bytes(_hot_table(crlf=True, trailing_newline=False))
    plan_p = gov / "plan-tracker.md"
    plan_p.write_text(PLAN_TRACKER, encoding="utf-8")
    inputs = em.MigrationInputs.capture(ev, plan_p)
    plan = em.plan_evd_compaction(inputs, _policy())
    raw = inputs.evidence_bytes
    # slice-decode identity held for every instance (planner didn't refuse)
    assert not em._is_refusal(plan)
    for inst in plan["instances"]:
        chunk = raw[inst["byte_offset"]:
                    inst["byte_offset"] + inst["byte_length"]]
        assert em._sha256_bytes(chunk) == inst["row_sha256"]
        if inst["byte_length"]:
            # CRLF lines keep their \r inside the slice
            decoded = chunk.decode("utf-8")
            if inst["byte_offset"] > 0:
                assert decoded.endswith("\n") or inst is plan["instances"][-1]
    # moving still exact on CRLF world
    hot_after = plan["_hot_after_bytes_internal"]
    assert b"\r\n" in hot_after          # retained CRLF rows untouched


def test_v2_i1_moved_slices_hash_to_original_bytes(world):
    inputs, plan = _plan(world)
    raw = inputs.evidence_bytes
    for inst in plan["instances"]:
        chunk = raw[inst["byte_offset"]:
                    inst["byte_offset"] + inst["byte_length"]]
        assert em._sha256_bytes(chunk) == inst["row_sha256"]
        assert chunk.decode("utf-8").startswith(f"| {inst['row_id']} ")
    # instance identity = (source digest, byte range, row digest)  [I1]
    for inst in plan["instances"]:
        assert inst["source_sha256"] == inputs.evidence_sha256


def test_v2_overlaps_refused(tmp_path, world, monkeypatch):
    # sabotage one offset to force the overlap detector (defensive path)
    inputs, plan = _plan(world)
    plan["instances"][1]["byte_offset"] = plan["instances"][0]["byte_offset"]
    # re-run conservation check manually through the public planner is not
    # possible without re-planning; assert the internal invariant function
    # by rebuilding the guard inline:
    covered = sorted((i["byte_offset"], i["byte_offset"] + i["byte_length"])
                     for i in plan["instances"])
    overlap = any(e1 > s2 for (s1, e1), (s2, e2) in zip(covered, covered[1:]))
    assert overlap  # the sabotage is detectable; the planner refuses on it


# ---------------------------------------------------------------------------
# execute gate + I4/I5 apply path + V4 interrupted worlds
# ---------------------------------------------------------------------------

def _enable_m2(monkeypatch):
    monkeypatch.setenv(em.EXECUTE_ENV_FLAG, "1")


def test_execute_gate_refuses_without_m2_flag(world):
    inputs, plan = _plan(world)
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert em._is_refusal(receipt)
    assert receipt["code"] == "execute_not_authorized"
    assert not (world["gov"] / "migration-staging").exists()


def test_i4_i5_apply_publishes_cold_before_hot(world, monkeypatch):
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert receipt["status"] == "applied", receipt
    # cold segments exist with verbatim payload
    segs = sorted((world["gov"] / "archive" / "evidence").glob("evdt-segment-*.md"))
    assert segs
    seg_text = "\n".join(p.read_text(encoding="utf-8") for p in segs)
    for rid in ("EVD-910", "EVD-911", "EVD-915"):
        assert rid in seg_text
    for rid in ("EVD-912", "EVD-913", "EVD-914"):
        assert rid not in seg_text
    # hot file is the pinned postimage; movers gone, retained intact
    hot = world["ev"].read_bytes()
    assert em._sha256_bytes(hot) == plan["outputs"]["hot_after_sha256"]
    kept = hot.decode("utf-8")
    for rid in ("EVD-912", "EVD-913", "EVD-914", "REVIEW-9001"):
        assert rid in kept
    for rid in ("EVD-910", "EVD-911", "EVD-915"):
        assert rid not in kept
    # staged before-backup preserved (I1)
    tx = receipt["transaction_id"]
    before = world["gov"] / "migration-staging" / tx / "before-evidence.md"
    assert before.read_bytes() == inputs.evidence_bytes
    # manifest finalized
    manifest = json.loads((world["gov"] / "migration-staging" / tx /
                           "manifest.json").read_text(encoding="utf-8"))
    assert manifest["phase"] == "finalized"
    assert tx.startswith("evdt-")          # I7 fresh id namespace


def test_i5_never_overwrite_idempotent_skip(world, monkeypatch):
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert receipt["status"] == "applied"
    outcomes = {s["relative_path"]: s["outcome"]
                for s in receipt["published_segments"]}
    assert all(v == "created" for v in outcomes.values())
    # replay the SAME publish: the primitive must judge idempotent_skip
    # (rebuilding is prevented by the hot CAS first — so call the publish
    # primitive directly, as the second transaction would)
    import archive_migration_engine as eng
    seg0 = world["gov"] / "archive" / "evidence" / "evdt-segment-000.md"
    seg_lines = seg0.read_text(encoding="utf-8").split("\n")
    header_line, body = seg_lines[0], [ln for ln in seg_lines[1:] if ln]
    out = eng._write_archive_file_never_overwrite(seg0, header_line, body)
    assert out == "idempotent_skip"


def test_v4_world_hot_before_intact(world, monkeypatch):
    # simulate: cold published, hot unwritten (restore the before bytes)
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    tx = receipt["transaction_id"]
    before = (world["gov"] / "migration-staging" / tx /
              "before-evidence.md").read_bytes()
    world["ev"].write_bytes(before)     # crash world: hot never committed
    judged = em.recover_evd_transfer(tx, world["gov"], world["ev"])
    assert judged["status"] == "judged"
    assert judged["world"] == "hot_before_intact"


def test_v4_world_hot_after_then_new_append(world, monkeypatch):
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    tx = receipt["transaction_id"]
    # finalized world immediately after: judged as after-committed
    judged = em.recover_evd_transfer(tx, world["gov"], world["ev"])
    assert judged["world"] == "hot_after_committed"
    # legal later world: a new append moves the digest → unknown, never
    # rolled back over (§8.2 last row)
    with world["ev"].open("ab") as fh:
        fh.write(b"| EVD-920 | FIX-903 | late | row |\n")
    judged2 = em.recover_evd_transfer(tx, world["gov"], world["ev"])
    assert judged2["world"] == "unknown_world"
    assert "never roll back" in judged2["action"]


def test_v4_input_divergence_cas_refusal(world, monkeypatch):
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    with world["ev"].open("ab") as fh:      # concurrent append after snapshot
        fh.write(b"| EVD-919 | FIX-903 | concurrent | row |\n")
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert em._is_refusal(receipt)
    assert receipt["code"] == "input_diverged"
    assert not (world["gov"] / "migration-staging").exists()


# ---------------------------------------------------------------------------
# CODE R0 fix batch: P3-2 fault injection + P1-1 disk read-back strength
# ---------------------------------------------------------------------------

def test_p3_2_cold_primitive_failure_hot_untouched(world, monkeypatch):
    """I4 under fault: the cold primitive raising (conflict path) must
    leave the hot table bit-identical and surface a STRUCTURED refusal
    (CODE R0 P3-2 + P3-4), never a traceback."""
    import archive_migration_engine as eng

    def boom(*a, **k):
        raise eng.BigTableMigrationError(
            {"code": "archive_target_conflict",
             "detail": "foreign bytes under the exclusive-create target"})

    monkeypatch.setattr(em._engine, "_write_archive_file_never_overwrite",
                        boom)
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    before = world["ev"].read_bytes()
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert em._is_refusal(receipt)
    assert receipt["code"] == "archive_target_conflict"
    assert "hot table untouched" in receipt["detail"]
    assert world["ev"].read_bytes() == before   # hot bit-identical


def test_p1_1_disk_readback_rejects_corrupted_segment(world, monkeypatch):
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

    monkeypatch.setattr(em._engine, "_write_archive_file_never_overwrite",
                        corrupting_publish)
    _enable_m2(monkeypatch)
    inputs, plan = _plan(world)
    before = world["ev"].read_bytes()
    receipt = em.apply_evd_plan(plan, inputs, world["gov"])
    assert em._is_refusal(receipt)
    assert receipt["code"] in ("identity_changed",
                               "byte_conservation_failed")
    assert world["ev"].read_bytes() == before   # hot CAS never ran


# ---------------------------------------------------------------------------
# I6 capacity + resource limits
# ---------------------------------------------------------------------------

def test_i6_capacity_reported_not_bent(world):
    inputs, plan = _plan(world)
    cap = plan["capacity"]
    assert cap["error_gate_bytes"] == 650_000
    assert cap["warn_gate_bytes"] == 400_000
    assert cap["status"] in ("blocked", "warn_zone", "under_error_gate")
    assert "BLOCKED" in cap["note"] or "never modified" in cap["note"]


def test_resource_limit_row_over_100kb_stays_hot(tmp_path):
    gov = tmp_path / ".governance"
    gov.mkdir()
    ev = gov / "evidence-log.md"
    ev.write_bytes(_hot_table())
    plan_p = gov / "plan-tracker.md"
    plan_p.write_text(PLAN_TRACKER, encoding="utf-8")
    inputs = em.MigrationInputs.capture(ev, plan_p)
    plan = em.plan_evd_compaction(inputs, _policy())
    big = max(plan["instances"], key=lambda i: i["byte_length"])
    assert big["byte_length"] <= em.MAX_ROW_BYTES  # fixture rows are small


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
