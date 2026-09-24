"""Guard tests for infra/governance_store.py — FEAT-046 (batch 1 writer family).

Covers the acceptance red faces and the DoD §4 item 7 negative controls:

  - evidence-append: 10-column skeleton (ID continuity / ISO date / all
    cells non-empty / 目标对齐 >= 30 / 事实依据 non-empty), machine
    provenance marker, ×415 legacy rows untouched;
  - typed --refs machine-check per kind (repo_file / git_object /
    governance_id / url / human_observation) with the frozen three-state
    reference_validation recorded IN the row — never a verdict;
  - decision-append: 5-cell live shape, four mandatory non-empty cells;
  - idempotency: same operation_id + same payload → replay (one row);
    same id + different payload → operation_id_conflict; world-recovery
    after a simulated crash between target write and ledger write;
  - concurrency: threaded appends lose no row (test_loop_paro_engine
    L871 precedent) + lock-contention is retryable;
  - reliability: CRLF preserved, no BOM, explicit UTF-8 (GBK-safe CJK
    payload), byte-prefix preservation, dry-run writes nothing;
  - locks-extend / locks-amend / locks-release reuse the acquire-pipeline
    schema (Check 26 mirror): extend/amend/replay/resume/drift refusals;
  - locks-release (FIX-370): happy release (active entry + all owned file
    locks gone, ops-ledger row on disk), fail-closed zero-write refusal on
    a lockless task, idempotent replay as a success no-op;
  - markdown pipe special characters: raw pipe refused (shape), inline-code
    span accepted (the engine splitter's documented convention).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_governance_store.py -v
"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import governance_store as gs  # noqa: E402
import verify_workflow as vw  # noqa: E402 — FIX-375 边缘① engine dispatch face
from contracts import (  # noqa: E402
    ERROR_CODE_DISPOSITIONS,
    ContractViolation,
    OPERATION_ID_PATTERN,
    REFERENCE_VALIDATION_STATES,
)

GOAL = ("目标对齐：批 1 写入器族把确定性结构操作软件化，"
        "消灭手工追加 schema 事故类，与项目目标（过程自动、质量不低质）一致。")
USER_IMPACT = ("用户影响：获得=锁/EVD/DEC 机器写入路径；感知=结构操作不再手写；"
               "体验变化=正向；迁移指南=不需要。")
DESCRIPTION = (f"FEAT-046 交付三命令写入器族（locks/evidence/decision）验证。"
               f"{GOAL} {USER_IMPACT}")
BASIS = "事实依据：本测试守护写入器骨架契约与幂等协议"


def _payload(overrides=None):
    base = {
        "task_id": "FEAT-046",
        "evd_type": "产品代码",
        "description": DESCRIPTION,
        "basis": BASIS,
        "artifacts": "test_governance_store.py",
        "actor": "governance-store",
        "date": "2026-09-19",
        "gate": "G11",
        "conclusion": "✅ 完成",
        "refs": [],
    }
    base.update(overrides or {})
    return base


def _call_evidence(governance_dir, overrides=None, **kwargs):
    payload = _payload(overrides)
    params = dict(
        task_id=payload["task_id"], evd_type=payload["evd_type"],
        description=payload["description"], basis=payload["basis"],
        artifacts=payload["artifacts"], actor=payload["actor"],
        date=payload["date"], gate=payload["gate"],
        conclusion=payload["conclusion"], refs=payload["refs"],
        governance_dir=governance_dir, repo_root=governance_dir.parent,
        operation_id=None,
    )
    params.update(kwargs)
    return gs.evidence_append(**params)


LEGACY_9_COL = ("| EVD-901 | FIX-900 | 产品代码 | 旧 9 列手工行（×415 基线"
                "样本，只读不动） | 事实依据：历史叙述 | 某审查者 | 2026-08-01 "
                "| G11 | ✅ 完成 |")
STANDARD_10_COL = ("| EVD-902 | FIX-901 | 产品代码 | 标准 10 列机器行样本"
                   " 目标对齐：占位描述文本需要超过三十个字符才能通过校验规则 "
                   "用户影响：占位 | 事实依据：占位依据 | 占位工件 | 测试 "
                   "| 2026-08-02 | G11 | ✅ 完成 |")


def _write_bytes(path: Path, text: str) -> None:
    """Write explicit UTF-8 LF bytes (text mode would translate \\n → CRLF
    on Windows and break byte-prefix assertions)."""
    path.write_bytes(text.encode("utf-8"))


def _make_governance_dir(tmp, *, evidence=True, decision=True, locks=True,
                         archive=False):
    gov = tmp / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    if evidence:
        _write_bytes(gov / "evidence-log.md",
                     "# 当前项目证据记录\n\n"
                     "| id | task | type | description | basis | artifacts "
                     "| actor | date | gate | conclusion |\n"
                     f"{STANDARD_10_COL}\n\n{LEGACY_9_COL}\n")
    if decision:
        _write_bytes(gov / "decision-log.md",
                     "# 当前项目决策记录\n\n"
                     "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 "
                     "| 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
                     "| --- | --- | --- | --- | --- | --- | --- | --- | --- "
                     "| --- | --- |\n"
                     "| DEC-201 | 2026-09-17 | 主题样本 | 背景样本 | 决策内容"
                     "样本 | 备选 | 原因 | 范围 | Coordinator | FIX-1 | 动作"
                     " |\n")
    if locks:
        _write_bytes(gov / "agent-locks.json", json.dumps({
            "active_tasks": {
                "FIX-100": {
                    "agent_role": "Developer",
                    "spawned_at": "2026-09-19T10:00:00",
                    "coordinator_session": "session-x",
                    "target_files": ["docs/a.md"],
                    "description": "",
                    "acquired": "2026-09-19T10:00:00",
                    "files": ["docs/a.md"],
                },
            },
            "file_locks": {
                "docs/a.md": {
                    "locked_by": "FIX-100",
                    "locked_at": "2026-09-19T10:00:00",
                    "ttl_seconds": 3600,
                    "ttl_reason": "seed",
                },
            },
        }, ensure_ascii=False, indent=4) + "\n")
    if archive:
        arch = gov / "archive" / "evidence"
        arch.mkdir(parents=True, exist_ok=True)
        _write_bytes(arch / "archive-evidence-old.md",
                     "- EVD-903 归档样本\n- DEC-150 归档决策样本\n")
    return gov


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.gov = _make_governance_dir(self.tmp, archive=False)

    def tearDown(self):
        self._tmp_ctx.cleanup()

    def evidence_bytes(self):
        return (self.gov / "evidence-log.md").read_bytes()

    def evidence_rows(self):
        text = self.evidence_bytes().decode("utf-8")
        return [line for line in text.split("\n")
                if line.strip().startswith("| EVD-")]

    def dec_rows(self):
        text = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        return [line for line in text.split("\n")
                if line.strip().startswith("| DEC-")]

    def assertRefused(self, payload, code):
        self.assertTrue(payload.get("error"), payload)
        self.assertEqual(payload.get("code"), code)
        self.assertEqual(payload.get("disposition"),
                         ERROR_CODE_DISPOSITIONS[code])


class EvidenceAppendTests(StoreTestCase):
    def test_append_writes_next_id_10_col_row_with_marker(self):
        result = _call_evidence(self.gov, operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result["code"], "ok")
        self.assertEqual(result["execution"], "succeeded")
        self.assertIsNone(result["observed_revision"])
        rows = self.evidence_rows()
        self.assertEqual(len(rows), 3)
        new_row = rows[-1]
        cells = gs._split_row(new_row)
        self.assertEqual(len(cells), gs.EVIDENCE_COLUMNS)
        self.assertEqual(cells[0], "EVD-903")
        self.assertTrue(all(cell.strip() for cell in cells))
        self.assertIn("机器写入：governance-store evidence-append", cells[4])
        self.assertIn(result["operation_id"], new_row)
        self.assertEqual(cells[6], "governance-store")
        # original bytes are a strict byte-prefix of the new file (DoD 3/4)
        before = STANDARD_10_COL + "\n\n" + LEGACY_9_COL + "\n"
        current = self.evidence_bytes().decode("utf-8")
        self.assertTrue(current.startswith(
            "# 当前项目证据记录\n\n"
            "| id | task | type | description | basis | artifacts | actor "
            "| date | gate | conclusion |\n" + before))

    def test_row_validation_and_postwrite_share_one_validator(self):
        captured = {}
        original = gs._post_write_append_check

        def spy(target, original_bytes, row_text, op_id, marker, validator):
            captured["validator"] = validator
            captured["row"] = row_text
            captured["op_id"] = op_id
            return original(target, original_bytes, row_text, op_id, marker,
                            validator)

        with mock.patch.object(gs, "_post_write_append_check", spy):
            _call_evidence(self.gov, operation_id=gs.new_operation_id())
        self.assertIs(captured["validator"], gs._evidence_row_validator)
        # the SAME validator accepts the written row on a clean re-run
        gs._evidence_row_validator(captured["row"].strip(),
                                   captured["op_id"])

    def test_crlf_preserved_and_no_bom(self):
        target = self.gov / "evidence-log.md"
        target.write_bytes(
            target.read_bytes().replace(b"\n", b"\r\n"))
        before = target.read_bytes()
        _call_evidence(self.gov, operation_id=gs.new_operation_id())
        after = target.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertIn(b"\r\n| EVD-903 ", after)
        self.assertFalse(after.startswith(b"\xef\xbb\xbf"))

    def test_raw_pipe_in_cell_refused_and_nothing_written(self):
        before = self.evidence_bytes()
        payload = _call_evidence(
            self.gov,
            overrides={"description": DESCRIPTION + " 非法 | 管道"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")
        self.assertIn("|", payload["detail"])
        self.assertEqual(self.evidence_bytes(), before)
        self.assertFalse((self.gov / gs.LEDGER_FILE_NAME).exists())

    def test_inline_code_pipe_accepted(self):
        result = _call_evidence(
            self.gov,
            overrides={"description": DESCRIPTION + " 状态列写 `✅ 完成 |`"
                                               " 形态测试"},
            operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        self.assertEqual(len(gs._split_row(self.evidence_rows()[-1])),
                         gs.EVIDENCE_COLUMNS)

    def test_newline_in_cell_refused(self):
        before = self.evidence_bytes()
        payload = _call_evidence(
            self.gov,
            overrides={"description": DESCRIPTION + "\n第二行"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")
        self.assertEqual(self.evidence_bytes(), before)

    def test_missing_goal_alignment_refused(self):
        payload = _call_evidence(
            self.gov,
            overrides={"description": "没有目标对齐字段的描述"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_short_goal_alignment_refused(self):
        payload = _call_evidence(
            self.gov,
            overrides={"description": "目标对齐：太短了"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_fact_basis_prefix_normalized_by_writer(self):
        # the writer owns the 事实依据： prefix (cell normalization); a bare
        # payload is prefixed deterministically — the skeleton refuses only
        # an EMPTY payload (enforced by --basis non-empty).
        result = _call_evidence(
            self.gov,
            overrides={"basis": "没有前缀的载荷会被写入器规范化"},
            operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        self.assertIn("事实依据：没有前缀的载荷会被写入器规范化",
                      self.evidence_rows()[-1])

    def test_empty_basis_refused(self):
        payload = _call_evidence(
            self.gov,
            overrides={"basis": "  "},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_bad_date_refused(self):
        payload = _call_evidence(
            self.gov,
            overrides={"date": "2026-13-45"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_bad_task_id_refused(self):
        payload = _call_evidence(
            self.gov,
            overrides={"task_id": "fix-100"},
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_id_collision_with_archive_refused(self):
        # hot max = 902 → candidate EVD-903; the archive already holds 903
        gov2 = _make_governance_dir(self.tmp / "coll", archive=True)
        before = (gov2 / "evidence-log.md").read_bytes()
        payload = _call_evidence(gov2, operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")
        self.assertEqual((gov2 / "evidence-log.md").read_bytes(), before)

    def test_legacy_x415_rows_untouched_after_append(self):
        gov2 = _make_governance_dir(self.tmp / "clean", archive=False)
        result = _call_evidence(gov2, operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        text = (gov2 / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn(LEGACY_9_COL, text)

    def test_same_operation_replays_without_duplicate_row(self):
        op = gs.new_operation_id()
        first = _call_evidence(self.gov, operation_id=op)
        second = _call_evidence(self.gov, operation_id=op)
        self.assertFalse(first.get("error"), first)
        self.assertFalse(second.get("error"), second)
        self.assertTrue(second.get("replayed"))
        self.assertEqual(second.get("replay_source"), "ledger")
        self.assertEqual(second["operation_id"], first["operation_id"])
        self.assertEqual(len(self.evidence_rows()), 3)

    def test_same_operation_different_payload_conflicts(self):
        op = gs.new_operation_id()
        _call_evidence(self.gov, operation_id=op)
        before = self.evidence_bytes()
        payload = _call_evidence(
            self.gov, overrides={"description": DESCRIPTION + "（改）"},
            operation_id=op)
        self.assertRefused(payload, "operation_id_conflict")
        self.assertIsNotNone(payload["observed_revision"])
        self.assertIsNone(payload["execution"])
        self.assertEqual(self.evidence_bytes(), before)

    def test_world_recovery_after_crash_between_write_and_ledger(self):
        op = gs.new_operation_id()
        # Simulate the crash window: the row landed, the ledger did not.
        target = self.gov / "evidence-log.md"
        row, _ = gs._build_evidence_row(
            evd_id="EVD-903", task_id="FEAT-046", evd_type="产品代码",
            description=DESCRIPTION, basis=BASIS, artifacts="recovery", actor="x",
            date_str="2026-09-19", gate="G11", conclusion="✅ 完成",
            refs=[], op_id=op)
        target.write_bytes(target.read_bytes() + (row + "\n").encode("utf-8"))
        result = _call_evidence(self.gov, operation_id=op)
        self.assertFalse(result.get("error"), result)
        self.assertTrue(result.get("replayed"))
        self.assertEqual(result.get("replay_source"), "world_recovery")
        rows = [line for line in
                target.read_text(encoding="utf-8").split("\n")
                if line.strip().startswith("| EVD-")]
        self.assertEqual(len(rows), 3)
        ledger = json.loads(
            (self.gov / gs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(ledger["operations"][op]["status"], "ok")

    def test_dry_run_writes_nothing_anywhere(self):
        before = self.evidence_bytes()
        payload = _call_evidence(self.gov, dry_run=True,
                                 operation_id=gs.new_operation_id())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["bytes_written"], 0)
        self.assertEqual(payload["next_id"], "EVD-903")
        self.assertIn("| EVD-903 ", payload["row"])
        self.assertEqual(len(gs._split_row(payload["row"]),
                         ), gs.EVIDENCE_COLUMNS)
        self.assertEqual(self.evidence_bytes(), before)
        self.assertFalse((self.gov / gs.LEDGER_FILE_NAME).exists())

    def test_expected_revision_conflict_reports_observed(self):
        payload = _call_evidence(
            self.gov, expected_revision=1,
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "revision_conflict")
        self.assertEqual(payload["observed_revision"],
                         len(self.evidence_bytes()))

    def test_concurrent_appends_lose_no_row(self):
        op_ids = [gs.new_operation_id() for _ in range(8)]
        results = [None] * 8
        barriers = threading.Barrier(8)

        def worker(index):
            barriers.wait()
            results[index] = _call_evidence(
                self.gov,
                overrides={"description": DESCRIPTION +
                           f" 并发分片 {index} 号线程的独立叙述"},
                operation_id=op_ids[index])

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(all(r and not r.get("error") for r in results),
                        results)
        ids = [gs._split_row(row)[0] for row in self.evidence_rows()]
        self.assertEqual(len(ids), 2 + 8)  # fixture has 2 EVD rows
        self.assertEqual(len(set(ids)), len(ids))

    def test_lock_contention_is_retryable(self):
        target = self.gov / "evidence-log.md"
        lock_dir = self.gov / gs.LOCK_DIR_NAME
        lock_dir.mkdir(exist_ok=True)
        lock = lock_dir / "evidence-log.md.lock"
        lock.write_text("held")
        payload = _call_evidence(self.gov, timeout_seconds=0.2,
                                 operation_id=gs.new_operation_id())
        self.assertRefused(payload, "lock_contention")
        lock.unlink()

    def test_cjk_payload_survives_utf8_roundtrip(self):
        cjk = "中文载荷与 emoji 🚀 以及全角｜管道均安全"
        result = _call_evidence(
            self.gov,
            overrides={"description": DESCRIPTION + " " + cjk},
            operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        raw = self.evidence_bytes()
        text = raw.decode("utf-8")  # raises if the writer used a locale codec
        self.assertIn(cjk, text)


class EvidenceRefTests(StoreTestCase):
    def refs_result(self, refs, **kwargs):
        return _call_evidence(self.gov, overrides={"refs": refs},
                              operation_id=gs.new_operation_id(), **kwargs)

    def test_missing_repo_file_refused(self):
        payload = self.refs_result(["repo_file:docs/does-not-exist.md"])
        self.assertRefused(payload, "cross_record_violation")
        self.assertIn("unresolvable", payload["detail"])

    def test_existing_repo_file_recorded_resolvable(self):
        real = self.tmp / "docs" / "a.md"
        real.parent.mkdir(exist_ok=True)
        real.write_text("x", encoding="utf-8")
        result = self.refs_result(["repo_file:docs/a.md"])
        self.assertFalse(result.get("error"), result)
        self.assertIn("refs[repo_file:docs/a.md=resolvable]",
                      self.evidence_rows()[-1])

    def test_governance_id_existing_resolvable(self):
        result = self.refs_result(["governance_id:DEC-201"])
        self.assertFalse(result.get("error"), result)
        self.assertIn("refs[governance_id:DEC-201=resolvable]",
                      self.evidence_rows()[-1])

    def test_governance_id_missing_refused(self):
        payload = self.refs_result(["governance_id:DEC-999"])
        self.assertRefused(payload, "cross_record_violation")

    def test_governance_id_unknown_family_refused(self):
        payload = self.refs_result(["governance_id:XXX-1"])
        self.assertRefused(payload, "cross_record_violation")

    # ── FIX-379 item-2: id-family vocabulary aligned to a single source ──

    def _seed_plan_tracker(self, *ids):
        rows = "\n".join(
            f"| **P1** | {i} | 词表对齐夹具行 | - | 0.88.0 | 验收=测试用例 "
            f"| approved |" for i in ids)
        _write_bytes(
            self.gov / "plan-tracker.md",
            "# 计划跟踪\n\n| 优先级 | ID | 事项 | 依赖 | 版本 | "
            "执行面与验收 | 状态 |\n| --- | --- | --- | --- | --- | "
            "--- | --- |\n" + rows + "\n")

    def test_task_family_outside_old_hand_copy_now_addressable(self):
        # DOC is an authoritative task-family prefix (task_priority) that
        # the pre-FIX-379 hand-copied map omitted — a MENTIONED doc-family
        # task id must be addressable as a governance_id ref.
        self._seed_plan_tracker("DOC-042")
        result = self.refs_result(["governance_id:DOC-042"])
        self.assertFalse(result.get("error"), result)
        self.assertIn("refs[governance_id:DOC-042=resolvable]",
                      self.evidence_rows()[-1])

    def test_known_task_family_absent_id_still_refused_as_not_found(self):
        # Deriving the families is additive only: a known family with an
        # id genuinely absent from the tracker still refuses (honest
        # not-found, same closed code).
        self._seed_plan_tracker("DOC-042")
        payload = self.refs_result(["governance_id:DOC-999"])
        self.assertRefused(payload, "cross_record_violation")
        self.assertIn("not found", payload["detail"])

    def test_id_families_cover_task_family_vocabulary_single_source(self):
        # The alignment pin: every authoritative task-family prefix maps
        # to plan-tracker.md; record families keep their dedicated files;
        # the pre-alignment 13 task prefixes are all covered now.
        import task_priority as tp
        for family in tp._TASK_FAMILY_PREFIXES:
            self.assertEqual(gs._GOVERNANCE_ID_FAMILIES.get(family),
                             ("plan-tracker.md",), family)
        self.assertEqual(gs._GOVERNANCE_ID_FAMILIES["DEC"],
                         ("decision-log.md",))
        self.assertEqual(gs._GOVERNANCE_ID_FAMILIES["RISK"],
                         ("risk-log.md",))
        for family in ("EVD", "REVIEW", "RECO", "TRIAGE"):
            self.assertEqual(gs._GOVERNANCE_ID_FAMILIES[family],
                             ("evidence-log.md",), family)

    def test_url_alias_syntax_valid_not_fetched(self):
        result = self.refs_result(["url_syntax:https://example.com/doc"])
        self.assertFalse(result.get("error"), result)
        row = self.evidence_rows()[-1]
        self.assertIn("refs[url:https://example.com/doc=resolvable]", row)

    def test_url_bad_syntax_refused(self):
        payload = self.refs_result(["url:ftp://bad example"])
        self.assertRefused(payload, "cross_record_violation")

    def test_git_object_bad_form_refused(self):
        payload = self.refs_result(["git_object:DROP TABLE;"])
        self.assertRefused(payload, "cross_record_violation")

    def test_git_object_unavailable_is_not_yet_verifiable(self):
        with mock.patch.object(gs.subprocess, "run",
                               side_effect=FileNotFoundError("no git")):
            result = self.refs_result(["git_object:abc1234"])
        self.assertFalse(result.get("error"), result)
        self.assertIn("refs[git_object:abc1234=not_yet_verifiable]",
                      self.evidence_rows()[-1])

    def test_git_object_unknown_sha_in_real_repo_refused(self):
        gov = _make_governance_dir(self.tmp / "repo-case", archive=True)
        payload = _call_evidence(
            gov, overrides={"refs": ["git_object:" + "0" * 40]},
            repo_root=Path(__file__).resolve().parents[4],
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")

    def test_human_observation_recorded_not_yet_verifiable(self):
        result = self.refs_result(["human_note:用户口头确认发布窗口"])
        self.assertFalse(result.get("error"), result)
        row = self.evidence_rows()[-1]
        self.assertIn("human_observation:用户口头确认发布窗口="
                      "not_yet_verifiable", row)

    def test_unknown_kind_refused_by_contract(self):
        payload = self.refs_result(["newspaper:today"])
        self.assertRefused(payload, "schema_violation")

    def test_validation_states_stay_in_frozen_enum(self):
        for kind, value in (("repo_file", "docs/a.md"),
                            ("governance_id", "DEC-201"),
                            ("human_note", "观察")):
            real = self.tmp / "docs" / "a.md"
            real.parent.mkdir(exist_ok=True)
            real.write_text("x", encoding="utf-8")
            payload = _call_evidence(
                self.gov, dry_run=True,
                overrides={"refs": [f"{kind}:{value}"]},
                operation_id=gs.new_operation_id())
            for item in payload["refs"]:
                self.assertIn(item["validation"],
                              REFERENCE_VALIDATION_STATES)


class DecisionAppendTests(StoreTestCase):
    def call_decision(self, **overrides):
        params = dict(
            decider="Coordinator", content="决策内容样本，用于守护测试。",
            basis="依据样本", date="2026-09-19",
            governance_dir=self.gov, operation_id=None)
        params.update(overrides)
        return gs.decision_append(**params)

    def test_append_5_cell_row_at_end(self):
        result = self.call_decision(operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        rows = self.dec_rows()
        self.assertEqual(rows[-1].strip().startswith("| DEC-202"), True)
        cells = gs._split_row(rows[-1])
        self.assertEqual(len(cells), gs.DEC_COLUMNS)
        for index in range(gs.DEC_MANDATORY_CELLS):
            self.assertTrue(cells[index].strip())
        self.assertIn("机器写入：governance-store decision-append", cells[4])

    def test_four_mandatory_cells_enforced(self):
        payload = self.call_decision(decider="   ",
                                     operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")
        payload = self.call_decision(content="  ",
                                     operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_bad_date_refused(self):
        payload = self.call_decision(date="19-09-2026",
                                     operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_replay_and_conflict(self):
        op = gs.new_operation_id()
        first = self.call_decision(operation_id=op)
        second = self.call_decision(operation_id=op)
        self.assertTrue(second.get("replayed"))
        self.assertEqual(len(self.dec_rows()), 2)
        payload = self.call_decision(content="不同内容", operation_id=op)
        self.assertRefused(payload, "operation_id_conflict")

    def test_dry_run_zero_write(self):
        before = (self.gov / "decision-log.md").read_bytes()
        payload = self.call_decision(dry_run=True,
                                     operation_id=gs.new_operation_id())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["next_id"], "DEC-202")
        self.assertEqual(
            (self.gov / "decision-log.md").read_bytes(), before)
        self.assertFalse((self.gov / gs.LEDGER_FILE_NAME).exists())

    def test_world_recovery(self):
        op = gs.new_operation_id()
        target = self.gov / "decision-log.md"
        row = gs._build_decision_row(
            dec_id="DEC-202", date_str="2026-09-19", decider="Coordinator",
            content="恢复样本", basis="", op_id=op)
        target.write_bytes(target.read_bytes() + (row + "\n").encode("utf-8"))
        result = self.call_decision(content="恢复样本", operation_id=op)
        self.assertTrue(result.get("replayed"))
        self.assertEqual(len(self.dec_rows()), 2)

    def test_id_collision_with_archive_refused(self):
        gov = _make_governance_dir(self.tmp / "dcoll", archive=True)
        (gov / "archive" / "evidence" / "old.md").write_text(
            "DEC-202 归档样本\n", encoding="utf-8")
        params = dict(
            decider="Coordinator", content="碰撞样本", basis="", date=None,
            governance_dir=gov, operation_id=gs.new_operation_id())
        try:
            payload = gs.decision_append(**params)
        except gs.StoreError as exc:
            payload = exc.payload
        self.assertRefused(payload, "cross_record_violation")

    def test_raw_pipe_refused(self):
        payload = self.call_decision(content="含 | 管道",
                                     operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")


class LocksExtendTests(StoreTestCase):
    def call_extend(self, **overrides):
        params = dict(
            task_id="FIX-100", files=["docs/a.md"], ttl_seconds=None,
            extend_by=None, reason="续期", governance_dir=self.gov,
            operation_id=None)
        params.update(overrides)
        return gs.locks_extend(**params)

    def test_extend_absolute_updates_entry_keep_identity(self):
        result = self.call_extend(ttl_seconds=7200,
                                  operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        entry = data["file_locks"]["docs/a.md"]
        self.assertEqual(entry["ttl_seconds"], 7200)
        self.assertEqual(entry["locked_by"], "FIX-100")
        self.assertEqual(entry["locked_at"], "2026-09-19T10:00:00")
        self.assertTrue(entry["ttl_reason"].startswith("extend:"))
        self.assertEqual(gs._validate_locks_schema(data), [])

    def test_extend_delta(self):
        result = self.call_extend(extend_by=600,
                                  operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["file_locks"]["docs/a.md"]["ttl_seconds"], 4200)

    def test_refuses_foreign_or_missing_lock(self):
        payload = self.call_extend(files=["docs/other.md"],
                                   ttl_seconds=1,
                                   operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")
        gov2 = _make_governance_dir(self.tmp / "nolock")
        data = json.loads(
            (gov2 / "agent-locks.json").read_text(encoding="utf-8"))
        del data["file_locks"]["docs/a.md"]
        (gov2 / "agent-locks.json").write_text(
            json.dumps(data), encoding="utf-8")
        payload = gs.locks_extend(
            task_id="FIX-100", files=["docs/a.md"], ttl_seconds=1,
            extend_by=None, reason="r", governance_dir=gov2,
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")

    def test_requires_exactly_one_ttl_flag(self):
        payload = self.call_extend(operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")
        payload = self.call_extend(ttl_seconds=10, extend_by=5,
                                   operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_replay_does_not_double_extend(self):
        op = gs.new_operation_id()
        first = self.call_extend(extend_by=600, operation_id=op)
        second = self.call_extend(extend_by=600, operation_id=op)
        self.assertTrue(second.get("replayed"))
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["file_locks"]["docs/a.md"]["ttl_seconds"], 4200)
        self.assertEqual(first["code"], "ok")

    def test_resume_applies_once_from_baseline(self):
        op = gs.new_operation_id()
        fingerprint = gs._fingerprint({
            "command": "locks-extend", "task": "FIX-100",
            "files": ["docs/a.md"], "ttl_seconds": None,
            "extend_by": 600, "reason": "续期",
        })
        baseline = {"file_locks": {"docs/a.md": {
            "locked_by": "FIX-100", "locked_at": "2026-09-19T10:00:00",
            "ttl_seconds": 3600, "ttl_reason": "seed"}}}
        target_state = {"file_locks": {"docs/a.md": dict(
            baseline["file_locks"]["docs/a.md"], ttl_seconds=4200,
            ttl_reason="extend: 续期")}}
        entry = gs._ledger_entry(
            op, "locks-extend", "FIX-100", fingerprint, status="pending",
            revision=None, now=datetime(2026, 9, 19, 10, 0, 0),
            pending_effects=target_state, baseline_effects=baseline)

        def seed(ledger):
            ledger["operations"][op] = entry

        gs._ledger_transaction(self.gov, seed)
        result = self.call_extend(extend_by=600, operation_id=op)
        self.assertFalse(result.get("error"), result)
        # FEAT-055 (batch-2.0): tightened from the original
        # assertIn(..., ("apply", "resume")).  This scenario's world is at
        # the RECORDED BASELINE (crash before apply), so the shared locks
        # pipeline re-applies the deterministic mutator exactly once and
        # completes — replay_source == "apply" is this leg's exact contract
        # (_locks_execute docstring: world==baseline → re-apply → complete);
        # conflating it with "resume" would let an apply-leg regression hide.
        self.assertEqual(result.get("replay_source"), "apply")
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["file_locks"]["docs/a.md"]["ttl_seconds"], 4200)
        ledger = json.loads(
            (self.gov / gs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(ledger["operations"][op]["status"], "ok")

    def test_resume_completes_without_reapplying_when_target_reached(self):
        """FEAT-055 (batch-2.0): the resume leg gets its own exact pin —
        world==pending_effects (the crash happened AFTER the apply) → the
        re-run completes from the recorded target, reports
        replay_source == "resume" and never mutates the TTL again."""
        op = gs.new_operation_id()
        fingerprint = gs._fingerprint({
            "command": "locks-extend", "task": "FIX-100",
            "files": ["docs/a.md"], "ttl_seconds": None,
            "extend_by": 600, "reason": "续期",
        })
        target_state = {"file_locks": {"docs/a.md": {
            "locked_by": "FIX-100", "locked_at": "2026-09-19T10:00:00",
            "ttl_seconds": 4200, "ttl_reason": "extend: 续期"}}}
        entry = gs._ledger_entry(
            op, "locks-extend", "FIX-100", fingerprint, status="pending",
            revision=None, now=datetime(2026, 9, 19, 10, 0, 0),
            pending_effects=target_state,
            baseline_effects={"file_locks": {"docs/a.md": dict(
                target_state["file_locks"]["docs/a.md"],
                ttl_seconds=3600, ttl_reason="seed")}})

        def seed(ledger):
            ledger["operations"][op] = entry

        gs._ledger_transaction(self.gov, seed)
        # the world is ALREADY at the recorded target: the locks file
        # carries ttl 4200 — the apply happened, only the ledger completion
        # was lost to the crash.
        locks = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        locks["file_locks"]["docs/a.md"]["ttl_seconds"] = 4200
        locks["file_locks"]["docs/a.md"]["ttl_reason"] = "extend: 续期"
        gs._atomic_write_bytes(
            self.gov / "agent-locks.json",
            (json.dumps(locks, ensure_ascii=False, indent=4) + "\n")
            .encode("utf-8"))
        result = self.call_extend(extend_by=600, operation_id=op)
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result.get("replay_source"), "resume")
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["file_locks"]["docs/a.md"]["ttl_seconds"],
                         4200)  # completed, never re-applied (+600)

    def test_drift_refuses_manual_intervention(self):
        op = gs.new_operation_id()
        fingerprint = gs._fingerprint({
            "command": "locks-extend", "task": "FIX-100",
            "files": ["docs/a.md"], "ttl_seconds": None,
            "extend_by": 600, "reason": "续期",
        })
        entry = gs._ledger_entry(
            op, "locks-extend", "FIX-100", fingerprint, status="pending",
            revision=None, now=datetime(2026, 9, 19, 10, 0, 0),
            pending_effects={"file_locks": {"docs/a.md": {
                "ttl_seconds": 9999}}},
            baseline_effects={"file_locks": {"docs/a.md": {
                "ttl_seconds": 1}}})

        def seed(ledger):
            ledger["operations"][op] = entry

        gs._ledger_transaction(self.gov, seed)
        payload = self.call_extend(extend_by=600, operation_id=op)
        self.assertRefused(payload, "manual_intervention")

    def test_unknown_task_refused(self):
        payload = self.call_extend(task_id="FIX-999", ttl_seconds=10,
                                   operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")

    def test_corrupt_locks_refused_fail_closed(self):
        gov2 = _make_governance_dir(self.tmp / "corrupt")
        (gov2 / "agent-locks.json").write_text("{not json", encoding="utf-8")
        payload = gs.locks_extend(
            task_id="FIX-100", files=["docs/a.md"], ttl_seconds=10,
            extend_by=None, reason="r", governance_dir=gov2,
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "manual_intervention")


    def test_same_op_different_payload_conflicts_structured(self):
        # P0-1 red phase: the conflict leg must produce a STRUCTURED
        # operation_id_conflict (carrying observed_revision per the frozen
        # face-5 invariant), never an uncaught ContractViolation.
        op = gs.new_operation_id()
        first = self.call_extend(extend_by=600, operation_id=op)
        self.assertFalse(first.get("error"), first)
        before = (self.gov / "agent-locks.json").read_bytes()
        payload = self.call_extend(extend_by=700, reason="改错字",
                                   operation_id=op)
        self.assertRefused(payload, "operation_id_conflict")
        self.assertIsNotNone(payload["observed_revision"])
        self.assertIsNone(payload["execution"])
        self.assertEqual(
            (self.gov / "agent-locks.json").read_bytes(), before)

    def test_same_op_different_payload_conflicts_cli_exit2(self):
        op = gs.new_operation_id()
        first = subprocess.run(
            [sys.executable, str(_INFRA_DIR / "governance_store.py"),
             "--project-root", str(self.tmp),
             "locks-extend", "--task", "FIX-100", "--files", "docs/a.md",
             "--extend-by", "600", "--reason", "first",
             "--operation-id", op],
            capture_output=True, timeout=60)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = subprocess.run(
            [sys.executable, str(_INFRA_DIR / "governance_store.py"),
             "--project-root", str(self.tmp),
             "locks-extend", "--task", "FIX-100", "--files", "docs/a.md",
             "--extend-by", "700", "--reason", "typo",
             "--operation-id", op],
            capture_output=True, timeout=60)
        self.assertEqual(second.returncode, 2, second.stdout + second.stderr)
        payload = json.loads(second.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "operation_id_conflict")
        self.assertIsNotNone(payload["observed_revision"])
        self.assertNotIn("ContractViolation",
                         second.stderr.decode("utf-8"))

    def test_dry_run_executes_id_collision_check(self):
        # P2-1: dry-run must run the SAME collision-checked id assignment
        # as a real write — a dry-run PASS predicts the real write.
        gov2 = _make_governance_dir(self.tmp / "drycoll", archive=True)
        before = (gov2 / "evidence-log.md").read_bytes()
        payload = _call_evidence(gov2, dry_run=True,
                                 operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")
        self.assertEqual((gov2 / "evidence-log.md").read_bytes(), before)

    def test_ledger_entry_without_fingerprint_refused(self):
        # P2-2: a tampered ok-entry with no fingerprint must not make
        # decide_operation_replay treat the op as unseen (double-apply).
        op = gs.new_operation_id()

        def seed(ledger):
            ledger["operations"][op] = {
                "schema_version": 1, "command": "locks-extend",
                "task_id": "FIX-100", "input_fingerprint": None,
                "status": "ok",
                "result": {"operation_id": op, "code": "ok",
                           "new_revision": 1, "observed_revision": None,
                           "execution": "succeeded", "detail": None},
                "pending_effects": None, "baseline_effects": None,
                "recorded_at": "2026-09-19T10:00:00",
                "updated_at": "2026-09-19T10:00:00",
            }

        gs._ledger_transaction(self.gov, seed)
        before = (self.gov / "agent-locks.json").read_bytes()
        payload = self.call_extend(extend_by=600, operation_id=op)
        self.assertRefused(payload, "manual_intervention")
        self.assertEqual(
            (self.gov / "agent-locks.json").read_bytes(), before)

    def test_split_cli_list_accepts_both_separators(self):
        # P2-3: the --files help promises semicolon AND comma forms;
        # refs keep the semicolon-only splitter (a URL value may contain
        # a comma).
        self.assertEqual(gs._split_cli_list("a;b,c"),
                         ["a", "b", "c"])
        self.assertEqual(gs._split_cli_list("a, b ; c"),
                         ["a", "b", "c"])
        self.assertEqual(gs._split_refs_list("url:https://x.io/a,b;c:d"),
                         ["url:https://x.io/a,b", "c:d"])

    def test_empty_target_refused_at_entry_even_with_cas(self):
        # P2-4: an empty hot file is refused BEFORE the CAS check — an
        # observed revision of 0 cannot back the conflict channel.
        target = self.gov / "evidence-log.md"
        target.write_bytes(b"")
        payload = _call_evidence(self.gov, expected_revision=5,
                                 operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")
        self.assertIn("empty", payload["detail"])
        self.assertEqual(target.read_bytes(), b"")
        gov2 = _make_governance_dir(self.tmp / "emptydec")
        (gov2 / "decision-log.md").write_bytes(b"")
        payload = gs.decision_append(
            decider="Coordinator", content="x", basis="", date=None,
            governance_dir=gov2, expected_revision=5,
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_cli_lock_contention_exits_3(self):
        # P3-10: the retryable disposition surfaces as CLI exit 3.
        lock_dir = self.gov / gs.LOCK_DIR_NAME
        lock_dir.mkdir(exist_ok=True)
        lock = lock_dir / "evidence-log.md.lock"
        lock.write_text("held")
        proc = subprocess.run(
            [sys.executable, str(_INFRA_DIR / "governance_store.py"),
             "--project-root", str(self.tmp),
             "evidence-append", "--task", "FEAT-046", "--type", "产品代码",
             "--description", DESCRIPTION, "--basis", BASIS,
             "--artifacts", "guard", "--timeout", "0.2",
             "--operation-id", gs.new_operation_id()],
            capture_output=True, timeout=60)
        lock.unlink()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "lock_contention")
        self.assertEqual(payload["disposition"], "retryable")


class LocksAmendTests(StoreTestCase):
    def call_amend(self, **overrides):
        params = dict(
            task_id="FIX-100", add_file=None, expected_new=False,
            ttl_seconds=None, extend_by=None, reason="外扩",
            governance_dir=self.gov, repo_root=self.tmp, operation_id=None)
        params.update(overrides)
        return gs.locks_amend(**params)

    def test_same_op_different_payload_conflicts_structured(self):
        # P0-1 amend-side red phase: structured operation_id_conflict with
        # observed_revision (frozen face-5 invariant), world unchanged.
        real = self.tmp / "docs" / "b.md"
        real.parent.mkdir(exist_ok=True)
        real.write_text("x", encoding="utf-8")
        op = gs.new_operation_id()
        first = self.call_amend(add_file="docs/b.md", operation_id=op)
        self.assertFalse(first.get("error"), first)
        before = (self.gov / "agent-locks.json").read_bytes()
        payload = self.call_amend(add_file="docs/b.md", reason="改错字",
                                  operation_id=op)
        self.assertRefused(payload, "operation_id_conflict")
        self.assertIsNotNone(payload["observed_revision"])
        self.assertIsNone(payload["execution"])
        self.assertEqual(
            (self.gov / "agent-locks.json").read_bytes(), before)

    def test_add_existing_file_updates_task_and_locks(self):
        real = self.tmp / "docs" / "b.md"
        real.parent.mkdir(exist_ok=True)
        real.write_text("x", encoding="utf-8")
        result = self.call_amend(add_file="docs/b.md",
                                 operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(gs._validate_locks_schema(data), [])
        entry = data["file_locks"]["docs/b.md"]
        self.assertEqual(entry["locked_by"], "FIX-100")
        self.assertEqual(entry["ttl_seconds"], 3600)
        self.assertNotIn("expected_new", entry)
        active = data["active_tasks"]["FIX-100"]
        self.assertIn("docs/b.md", active["target_files"])
        self.assertIn("docs/b.md", active["files"])

    def test_add_expected_new_file(self):
        result = self.call_amend(add_file="docs/new.md", expected_new=True,
                                 operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertTrue(data["file_locks"]["docs/new.md"]["expected_new"])

    def test_add_missing_file_without_expected_new_refused(self):
        payload = self.call_amend(add_file="docs/ghost.md",
                                  operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")

    def test_add_file_conflict_with_other_owner_refused(self):
        gov2 = _make_governance_dir(self.tmp / "conflict")
        data = json.loads(
            (gov2 / "agent-locks.json").read_text(encoding="utf-8"))
        data["file_locks"]["docs/b.md"] = {
            "locked_by": "FIX-200", "locked_at": "2026-09-19T10:00:00",
            "ttl_seconds": 60, "ttl_reason": "other"}
        (gov2 / "agent-locks.json").write_text(json.dumps(data),
                                               encoding="utf-8")
        payload = gs.locks_amend(
            task_id="FIX-100", add_file="docs/b.md", expected_new=False,
            ttl_seconds=None, extend_by=None, reason="r", governance_dir=gov2,
            operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")

    def test_nothing_to_amend_refused(self):
        payload = self.call_amend(operation_id=gs.new_operation_id())
        self.assertRefused(payload, "schema_violation")

    def test_replay_add_file_not_duplicated(self):
        real = self.tmp / "docs" / "b.md"
        real.parent.mkdir(exist_ok=True)
        real.write_text("x", encoding="utf-8")
        op = gs.new_operation_id()
        self.call_amend(add_file="docs/b.md", operation_id=op)
        second = self.call_amend(add_file="docs/b.md", operation_id=op)
        self.assertTrue(second.get("replayed"))
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(
            data["active_tasks"]["FIX-100"]["target_files"].count(
                "docs/b.md"), 1)

    def test_ttl_only_amend(self):
        result = self.call_amend(ttl_seconds=60,
                                 operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertEqual(data["file_locks"]["docs/a.md"]["ttl_seconds"], 60)


class LocksReleaseTests(StoreTestCase):
    """FIX-370 — the release leg of the locks family (B-10 先登记后删除).

    Task contract three faces: happy release (active entry + ALL owned
    file locks gone, ops-ledger row carrying the released file list),
    fail-closed zero-write refusal on a lockless task, and idempotent
    replay (same operation_id → success no-op, locks file untouched).
    """

    def seed_release_fixture(self):
        """FIX-100 holds two file locks + the active entry; FIX-200 holds
        its own entry + one file lock (must stay untouched)."""
        locks = {
            "active_tasks": {
                "FIX-100": {
                    "spawned_at": "2026-09-19T10:00:00",
                    "coordinator_session": "session-x",
                    "target_files": ["docs/a.md"],
                    "files": ["docs/a.md", "docs/b.md"],
                },
                "FIX-200": {
                    "spawned_at": "2026-09-19T11:00:00",
                    "coordinator_session": "session-y",
                    "target_files": ["docs/c.md"],
                    "files": ["docs/c.md"],
                },
            },
            "file_locks": {
                "docs/a.md": {
                    "locked_by": "FIX-100",
                    "locked_at": "2026-09-19T10:00:00",
                    "ttl_seconds": 3600,
                    "ttl_reason": "seed",
                },
                "docs/b.md": {
                    "locked_by": "FIX-100",
                    "locked_at": "2026-09-19T10:05:00",
                    "ttl_seconds": 7200,
                    "ttl_reason": "amend: added",
                },
                "docs/c.md": {
                    "locked_by": "FIX-200",
                    "locked_at": "2026-09-19T11:00:00",
                    "ttl_seconds": 3600,
                    "ttl_reason": "seed",
                },
            },
        }
        gs._atomic_write_bytes(
            self.gov / "agent-locks.json",
            (json.dumps(locks, ensure_ascii=False, indent=4) + "\n")
            .encode("utf-8"))
        return locks

    def call_release(self, **overrides):
        params = dict(task_id="FIX-100", governance_dir=self.gov,
                      operation_id=None)
        params.update(overrides)
        return gs.locks_release(**params)

    def test_release_removes_active_entry_and_all_owned_file_locks(self):
        self.seed_release_fixture()
        result = self.call_release(operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result["code"], "ok")
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertNotIn("FIX-100", data["active_tasks"])
        self.assertNotIn("docs/a.md", data["file_locks"])
        self.assertNotIn("docs/b.md", data["file_locks"])
        # collateral damage zero: the other task's rows stay untouched
        self.assertIn("FIX-200", data["active_tasks"])
        self.assertEqual(data["file_locks"]["docs/c.md"]["locked_by"],
                         "FIX-200")
        self.assertEqual(gs._validate_locks_schema(data), [])
        # B-10 留痕: the ok row carries operation_id + the released file
        # list; the family convention (effects dropped at completion, see
        # _complete_pending) stays pinned, so the FIX-370 retention field
        # is the surviving audit record
        ledger = json.loads(
            (self.gov / gs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))
        entry = ledger["operations"][result["operation_id"]]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["command"], "locks-release")
        self.assertEqual(entry["task_id"], "FIX-100")
        self.assertIsNone(entry["baseline_effects"])
        self.assertEqual(entry["released_files"],
                         ["docs/a.md", "docs/b.md"])

    def test_lockless_task_refused_zero_writes(self):
        self.seed_release_fixture()
        before = (self.gov / "agent-locks.json").read_bytes()
        payload = self.call_release(task_id="FIX-999",
                                    operation_id=gs.new_operation_id())
        self.assertRefused(payload, "cross_record_violation")
        self.assertIn("nothing to release", payload["detail"])
        self.assertEqual((self.gov / "agent-locks.json").read_bytes(),
                         before)
        self.assertFalse((self.gov / gs.LEDGER_FILE_NAME).exists())

    def test_file_locks_only_task_released_without_active_entry(self):
        locks = self.seed_release_fixture()
        del locks["active_tasks"]["FIX-200"]
        gs._atomic_write_bytes(
            self.gov / "agent-locks.json",
            (json.dumps(locks, ensure_ascii=False, indent=4) + "\n")
            .encode("utf-8"))
        result = self.call_release(task_id="FIX-200",
                                   operation_id=gs.new_operation_id())
        self.assertFalse(result.get("error"), result)
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertNotIn("FIX-200", data["active_tasks"])
        self.assertNotIn("docs/c.md", data["file_locks"])
        self.assertIn("docs/a.md", data["file_locks"])  # FIX-100 untouched

    def test_replay_is_success_noop_locks_file_unchanged(self):
        self.seed_release_fixture()
        op = gs.new_operation_id()
        first = self.call_release(operation_id=op)
        self.assertFalse(first.get("error"), first)
        after_first = (self.gov / "agent-locks.json").read_bytes()
        second = self.call_release(operation_id=op)
        self.assertTrue(second.get("replayed"), second)
        self.assertEqual(second["code"], "ok")
        self.assertEqual((self.gov / "agent-locks.json").read_bytes(),
                         after_first)

    def test_resume_leg_completing_release_stamps_released_files(self):
        """FIX-375 边缘③ (REVIEW-FIX-370 F-1): crash AFTER the locks write
        but BEFORE the ledger completion → the re-run resumes from the
        recorded target (replay_source == "resume", no re-apply) and the ok
        row MUST carry ``released_files`` — the same audit semantics the
        apply leg already has.  RED today: the resume leg completes without
        running ``effects_of``, so ``owned_files`` stays empty by
        construction and the apply-leg stamp condition never fires."""
        self.seed_release_fixture()
        op = gs.new_operation_id()
        fingerprint = gs._fingerprint(
            {"command": "locks-release", "task": "FIX-100"})
        # 登记先行: the pending entry carries BOTH effect states exactly as
        # the release pipeline records them — target = released world (empty
        # per-file snapshot = not locked, None = active entry gone)
        target_state = {"file_locks": {"docs/a.md": {}, "docs/b.md": {}},
                        "active_tasks": {"FIX-100": None}}
        baseline_effects = {
            "file_locks": {
                "docs/a.md": {"locked_by": "FIX-100",
                              "locked_at": "2026-09-19T10:00:00",
                              "ttl_seconds": 3600, "ttl_reason": "seed"},
                "docs/b.md": {"locked_by": "FIX-100",
                              "locked_at": "2026-09-19T10:05:00",
                              "ttl_seconds": 7200,
                              "ttl_reason": "amend: added"}},
            "active_tasks": {"FIX-100": {"target_files": ["docs/a.md"],
                                         "files": ["docs/a.md",
                                                   "docs/b.md"]}}}
        entry = gs._ledger_entry(
            op, "locks-release", "FIX-100", fingerprint, status="pending",
            revision=None, now=datetime(2026, 9, 19, 10, 0, 0),
            pending_effects=target_state, baseline_effects=baseline_effects)

        def seed(ledger):
            ledger["operations"][op] = entry

        gs._ledger_transaction(self.gov, seed)
        # the world is ALREADY released: the crash lost only the ledger
        # completion, FIX-100's active entry and both file locks are gone
        locks = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        del locks["active_tasks"]["FIX-100"]
        del locks["file_locks"]["docs/a.md"]
        del locks["file_locks"]["docs/b.md"]
        gs._atomic_write_bytes(
            self.gov / "agent-locks.json",
            (json.dumps(locks, ensure_ascii=False, indent=4) + "\n")
            .encode("utf-8"))
        result = self.call_release(operation_id=op)
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result.get("replay_source"), "resume")
        ledger = json.loads(
            (self.gov / gs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))
        entry = ledger["operations"][op]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["released_files"],
                         ["docs/a.md", "docs/b.md"])

    def test_reapply_leg_completing_release_stamps_released_files(self):
        """FIX-375 F-1 (review R0, 探针⑤): crash AFTER the ledger
        registration but BEFORE the locks write → the re-run finds world ==
        recorded baseline, re-applies the mutator and completes with
        replay_source == "apply".  This recovery leg never runs
        ``effects_of`` either (owned_files stays empty by construction),
        so the fresh-apply stamp branch short-circuits — the leg MUST take
        its audit list from the same pre-read capture.  RED before F-1:
        the ok row carried no released_files."""
        self.seed_release_fixture()
        op = gs.new_operation_id()
        fingerprint = gs._fingerprint(
            {"command": "locks-release", "task": "FIX-100"})
        # 登记先行: target = the released world the crashed apply never
        # reached; baseline = the fixture world exactly as _state_matches
        # reads it (the seeded fixture IS the baseline — nothing to mutate)
        target_state = {"file_locks": {"docs/a.md": {}, "docs/b.md": {}},
                        "active_tasks": {"FIX-100": None}}
        baseline_effects = {
            "file_locks": {
                "docs/a.md": {"locked_by": "FIX-100",
                              "locked_at": "2026-09-19T10:00:00",
                              "ttl_seconds": 3600, "ttl_reason": "seed"},
                "docs/b.md": {"locked_by": "FIX-100",
                              "locked_at": "2026-09-19T10:05:00",
                              "ttl_seconds": 7200,
                              "ttl_reason": "amend: added"}},
            "active_tasks": {"FIX-100": {"target_files": ["docs/a.md"],
                                         "files": ["docs/a.md",
                                                   "docs/b.md"]}}}
        entry = gs._ledger_entry(
            op, "locks-release", "FIX-100", fingerprint, status="pending",
            revision=None, now=datetime(2026, 9, 19, 10, 0, 0),
            pending_effects=target_state, baseline_effects=baseline_effects)

        def seed(ledger):
            ledger["operations"][op] = entry

        gs._ledger_transaction(self.gov, seed)
        result = self.call_release(operation_id=op)
        self.assertFalse(result.get("error"), result)
        self.assertEqual(result.get("replay_source"), "apply")
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertNotIn("FIX-100", data["active_tasks"])
        self.assertNotIn("docs/a.md", data["file_locks"])
        self.assertNotIn("docs/b.md", data["file_locks"])
        self.assertIn("FIX-200", data["active_tasks"])  # collateral zero
        ledger = json.loads(
            (self.gov / gs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))
        entry = ledger["operations"][op]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["released_files"],
                         ["docs/a.md", "docs/b.md"])


class ContractFaceTests(unittest.TestCase):
    def test_success_result_carries_revision_and_execution_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            gov = _make_governance_dir(Path(tmp))
            result = gs.evidence_append(
                task_id="FEAT-046", evd_type="产品代码",
                description=DESCRIPTION, basis=BASIS, artifacts="guard",
                governance_dir=gov, repo_root=Path(tmp),
                operation_id=gs.new_operation_id())
            self.assertFalse(result.get("error"))
            self.assertIsNotNone(result["new_revision"])
            self.assertEqual(result["execution"], "succeeded")
            self.assertIsNone(result["observed_revision"])

    def test_conflict_result_carries_observed_revision_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            gov = _make_governance_dir(Path(tmp))
            op = gs.new_operation_id()
            params = dict(
                task_id="FEAT-046", evd_type="产品代码",
                description=DESCRIPTION, basis=BASIS, artifacts="guard",
                governance_dir=gov, repo_root=Path(tmp), operation_id=op)
            gs.evidence_append(**params)
            conflict = gs.evidence_append(
                **{**params, "description": DESCRIPTION + "（改动）"})
            self.assertTrue(conflict["error"])
            self.assertIsNone(conflict["new_revision"])
            self.assertIsNotNone(conflict["observed_revision"])
            self.assertIsNone(conflict["execution"])

    def test_schema_window_refuses_unknown_versions(self):
        self.assertTrue(gs.SCHEMA_WINDOW.supports(1))
        self.assertFalse(gs.SCHEMA_WINDOW.supports(2))
        with self.assertRaises(Exception):
            gs.SCHEMA_WINDOW.require_supported("x", 2)

    def test_generated_operation_ids_match_frozen_form(self):
        import re
        for _ in range(3):
            self.assertRegex(gs.new_operation_id(), OPERATION_ID_PATTERN)

    def test_split_row_matches_engine_semantics(self):
        line = "| a | `b|c` | d |"
        self.assertEqual(gs._split_row(line), ["a", "`b|c`", "d"])

    def test_commands_registry_is_the_composition_root(self):
        self.assertEqual(
            set(gs.COMMANDS),
            {"locks-extend", "locks-amend", "locks-release",
             "evidence-append", "decision-append"})
        for name, handler in gs.COMMANDS.items():
            self.assertTrue(callable(handler))


class CliSubprocessTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.gov = _make_governance_dir(self.tmp)

    def tearDown(self):
        self._tmp_ctx.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(_INFRA_DIR / "governance_store.py"),
             "--project-root", str(self.tmp), *args],
            capture_output=True, timeout=60)

    def test_evidence_append_happy_path_exit0(self):
        proc = self._run(
            "evidence-append", "--task", "FEAT-046", "--type", "产品代码",
            "--description", DESCRIPTION, "--basis", BASIS,
            "--artifacts", "cli-guard",
            "--operation-id", gs.new_operation_id())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "ok")

    def test_refusal_exit2_with_closed_code(self):
        proc = self._run(
            "evidence-append", "--task", "bad-id", "--type", "x",
            "--description", DESCRIPTION, "--basis", BASIS,
            "--artifacts", "cli-guard")
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "schema_violation")

    def test_decision_append_dry_run_exit0_no_write(self):
        target = self.gov / "decision-log.md"
        before = target.read_bytes()
        proc = self._run("decision-append", "--decider", "Coordinator",
                         "--content", "干跑样本", "--dry-run")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(target.read_bytes(), before)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertTrue(payload["dry_run"])

    def test_malformed_operation_id_structured_exit2_no_traceback(self):
        """FIX-375 边缘②: a malformed --operation-id must come back as the
        structured schema_violation refusal on stdout with a non-zero exit —
        never as a bare ContractViolation traceback on stderr.  RED today:
        the exception leaks through the Namespace executor (_run only
        catches StoreError) and the CLI dies with a traceback (exit 1)."""
        proc = self._run(
            "evidence-append", "--task", "FEAT-046", "--type", "产品代码",
            "--description", DESCRIPTION, "--basis", BASIS,
            "--artifacts", "cli-guard", "--operation-id", "not-an-op-id")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "schema_violation")
        self.assertNotIn("Traceback", proc.stderr.decode("utf-8"))


class MalformedOperationIdTests(StoreTestCase):
    """FIX-375 边缘② — 畸形 --operation-id 的双面语义钉。

    ``require_operation_id`` (contracts face 1) raises ContractViolation;
    the writers' ``@_returns_payload`` only converts StoreError, so the
    exception used to leak to the CLI as a bare traceback.  The dispatch
    face (``cmd_*`` → ``_run``) now renders the closed-code refusal, while
    the LIBRARY face keeps raising — import semantics unchanged (the
    SystemExit/exception disclosure in the task line).
    """

    def call_cmd_evidence(self, operation_id):
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            code = gs.cmd_evidence_append(argparse.Namespace(
                task="FEAT-046", evd_type="产品代码",
                description=DESCRIPTION, basis=BASIS,
                artifacts="cli-guard", actor="governance-store",
                date=None, gate="G11", conclusion="✅ 完成", refs="",
                operation_id=operation_id, dry_run=False,
                expected_revision=None, timeout=10.0,
                project_root=str(self.tmp)))
        return code, out.getvalue()

    def test_cmd_face_renders_structured_schema_violation(self):
        code, rendered = self.call_cmd_evidence("not-an-op-id")
        self.assertEqual(code, 2)
        payload = json.loads(rendered)
        self.assertTrue(payload["error"])
        self.assertEqual(payload["code"], "schema_violation")
        self.assertEqual(payload["disposition"],
                         ERROR_CODE_DISPOSITIONS["schema_violation"])
        self.assertIn("not-an-op-id", payload["detail"])

    def test_library_face_keeps_contract_exception(self):
        # guard (not a red test): the library face NEVER converts — direct
        # import callers keep the ContractViolation semantics unchanged.
        with self.assertRaises(ContractViolation):
            _call_evidence(self.gov, operation_id="not-an-op-id")


# ── FIX-387: engine host-root rebind surface snapshot/restore ────────────
# ``_apply_project_root_override`` (verify_workflow.py L234-276) rebinds
# 12 module globals and mutates REQUIRED_FILES in place whenever the
# engine is invoked in-process with an explicit --project-root, and the
# CLI never restores them — process-lifetime state for a CLI, a leak in
# a shared pytest process (FIX-377 investigation ③: the in-process pin
# below flipped 18 later-run suite nodes red via
# ``_host_plugin_roots_divergent()`` while isolated runs stayed green).
# Every test that reaches that face in-process must snapshot the full
# surface in setUp and restore it in tearDown.
_VW_REBIND_GLOBALS = (
    "HOST_PROJECT_ROOT", "GOVERNANCE_DIR", "EXECUTION_PACKET_PATH",
    "SAMPLE_PATH", "SESSION_SNAPSHOT_PATH", "EVIDENCE_PATH", "RISK_PATH",
    "ARCHIVE_INDEX_PATH", "ARCHIVE_TASKS_DIR", "ARCHIVE_EVIDENCE_DIR",
    "ARCHIVE_DECISIONS_DIR", "ARCHIVE_RISKS_DIR",
)
_VW_MISSING = object()


def _vw_rebind_surface_snapshot():
    """Capture the engine host-root rebind surface (globals + REQUIRED_FILES)."""
    surface = {name: getattr(vw, name, _VW_MISSING)
               for name in _VW_REBIND_GLOBALS}
    surface["REQUIRED_FILES"] = dict(vw.REQUIRED_FILES)
    return surface


def _vw_rebind_surface_restore(surface):
    """Restore a snapshot taken by ``_vw_rebind_surface_snapshot``.

    REQUIRED_FILES is rebuilt in place (clear + update) so objects that
    captured the dict by reference keep seeing the restored contents.
    """
    for name in _VW_REBIND_GLOBALS:
        value = surface[name]
        if value is _VW_MISSING:
            vw.__dict__.pop(name, None)
        else:
            setattr(vw, name, value)
    vw.REQUIRED_FILES.clear()
    vw.REQUIRED_FILES.update(surface["REQUIRED_FILES"])


def _vw_rebind_surface_drift(surface, baseline):
    """Diff two rebind-surface snapshots; ``{}`` means identical."""
    drifted = {}
    for name in _VW_REBIND_GLOBALS:
        base, current = baseline[name], surface[name]
        if base is _VW_MISSING or current is _VW_MISSING:
            if base is not current:
                drifted[name] = (base, current)
        elif base != current:
            drifted[name] = (base, current)
    if surface["REQUIRED_FILES"] != baseline["REQUIRED_FILES"]:
        drifted["REQUIRED_FILES"] = (baseline["REQUIRED_FILES"],
                                     surface["REQUIRED_FILES"])
    return drifted


# Import-time baseline: captured before any test runs, so the file-end
# canary pins "exactly as verify_workflow loaded them" regardless of the
# cwd pytest was invoked from — the cwd-independent equivalent of the
# dogfood identity HOST_PROJECT_ROOT == PLUGIN_ROOT.
_VW_HOST_BASELINE = _vw_rebind_surface_snapshot()


class EngineDispatchExitCodeTests(unittest.TestCase):
    """FIX-375 边缘① — engine dispatch face exit-code transparency.

    verify_workflow.py's ``commands[cmd](args)`` dropped the writer family's
    int return code (0 ok / 2 refusal / 3 retryable — the FEAT-055 batch
    handlers are the return-style exception among otherwise sys.exit-style
    engine handlers), so a refused writer command still exited 0 (假绿).
    The in-process pin holds ``main`` itself to the return-code contract;
    the subprocess pins hold the real process exit codes.  Red-state
    evidence (TRIAGE-FIX-375 机录 2026-09-20 probe): engine-face refusal
    exited 0 while the module's own CLI exited 2.

    FIX-387: the in-process face below is the only in-suite caller that
    reaches ``_apply_project_root_override`` with a VALID root, so setUp
    snapshots the full host-root rebind surface and tearDown restores it
    — the rebinding must not outlive this test (it used to flip 18
    later-run suite nodes red; the file-end
    ``HostRootRebindCanaryTests`` pins the surface against its
    import-time baseline).
    """

    def setUp(self):
        import tempfile
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.gov = _make_governance_dir(self.tmp)
        # FIX-387: the tests below run the engine in-process with a VALID
        # --project-root; snapshot the full rebind surface so the CLI's
        # process-lifetime rebinding (verify_workflow.py L234-276) cannot
        # outlive a test in this class.
        self._vw_surface = _vw_rebind_surface_snapshot()

    def tearDown(self):
        _vw_rebind_surface_restore(self._vw_surface)
        self._tmp_ctx.cleanup()

    def test_engine_main_returns_writer_refusal_code(self):
        # FIX-387: kept in-process on purpose — this pin holds main's
        # return-code contract, which the subprocess siblings cannot see;
        # the setUp/tearDown snapshot/restore around it keeps the
        # host-root rebinding from leaking into the shared pytest process.
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            rc = vw.main(["--project-root", str(self.tmp), "locks-extend",
                          "--task", "nope", "--files", "a.txt",
                          "--extend-by", "600", "--reason", "r"])
        self.assertEqual(rc, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["code"], "schema_violation")

    def test_engine_subprocess_refusal_exit2(self):
        proc = subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "--project-root", str(self.tmp), "locks-extend",
             "--task", "nope", "--files", "a.txt",
             "--extend-by", "600", "--reason", "r"],
            capture_output=True, timeout=120)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "schema_violation")

    def test_engine_subprocess_success_exit0_unchanged(self):
        proc = subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "--project-root", str(self.tmp), "locks-extend",
             "--task", "FIX-100", "--files", "docs/a.md",
             "--extend-by", "600", "--reason", "r"],
            capture_output=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["code"], "ok")


class StaleLockTakeoverTests(unittest.TestCase):
    """P3-2 negative controls (batch-2.0 FEAT-055): the stale-takeover face
    of ``_TargetLock._stale`` now has both red faces — a stale lockfile IS
    taken over, a fresh one never is.  The takeover semantics and the
    transient-exclusion boundary are disclosed in the ``_TargetLock``
    docstring; the 600s window itself stays unreachable by a healthy write.
    """

    def setUp(self):
        import tempfile
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.target = self.tmp / "target.md"
        _write_bytes(self.target, "content")

    def tearDown(self):
        self._tmp_ctx.cleanup()

    def _lock_path(self):
        lock = self.target.parent / gs.LOCK_DIR_NAME \
            / (self.target.name + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        return lock

    def test_stale_lockfile_is_taken_over(self):
        lock = self._lock_path()
        lock.write_text("999999", encoding="ascii")
        old = time.time() - (gs._LOCK_STALE_SECONDS + 60)
        os.utime(lock, (old, old))
        with gs._TargetLock(self.target, timeout_seconds=1.0) as held:
            self.assertTrue(held._acquired)
            self.assertTrue(lock.exists())  # takeover re-created the file
            self.assertEqual(lock.read_text(encoding="ascii"),
                             str(os.getpid()))
        self.assertFalse(lock.exists())  # clean exit unlinks its own lock

    def test_fresh_lockfile_is_never_judged_stale(self):
        lock = self._lock_path()
        lock.write_text("424242", encoding="ascii")
        holder = gs._TargetLock(self.target, timeout_seconds=0.2)
        self.assertFalse(holder._stale())
        self.assertTrue(lock.exists())  # a fresh rival's lock is untouched

    def test_a_stale_successor_cannot_revoke_an_active_holder(self):
        """The takeover only fires past _LOCK_STALE_SECONDS: a lock that is
        seconds old blocks the acquirer (lock_contention), it is never
        silently revoked."""
        lock = self._lock_path()
        lock.write_text("1", encoding="ascii")
        recent = time.time() - 5  # well inside the 600s window
        os.utime(lock, (recent, recent))
        with self.assertRaises(gs.StoreError) as caught:
            with gs._TargetLock(self.target, timeout_seconds=0.1):
                pass
        self.assertEqual(caught.exception.payload["code"], "lock_contention")
        self.assertTrue(lock.exists())  # the recent lock survives


class RepoFileRootContainmentTests(StoreTestCase):
    """P3-4 read-side tightening (batch-2.0 FEAT-055): a repo_file reference
    must resolve INSIDE the repo root — absolute paths and ``..``-prefixed
    escapes report unresolvable (→ cross_record_violation), root-internal
    paths behave exactly as before.
    """

    def refs_result(self, refs):
        return _call_evidence(self.gov, overrides={"refs": refs},
                              operation_id=gs.new_operation_id())

    def test_dotdot_escape_refused(self):
        secret = self.tmp / "outside-secret.txt"
        _write_bytes(secret, "secret")
        payload = self.refs_result(["repo_file:../outside-secret.txt"])
        self.assertRefused(payload, "cross_record_violation")
        self.assertIn("escapes the repo root", payload["detail"])

    def test_absolute_path_refused(self):
        # a real file OUTSIDE the repo root, addressed by absolute path:
        # the governed repo lives at <tmp>/repo, the secret sits beside it.
        repo_root = self.tmp / "repo"
        outside = self.tmp / "outside-abs-secret.txt"
        _write_bytes(outside, "secret")
        result = _call_evidence(
            self.gov, overrides={"refs": ["repo_file:" + str(outside)]},
            repo_root=repo_root, operation_id=gs.new_operation_id())
        self.assertRefused(result, "cross_record_violation")
        self.assertIn("escapes the repo root", result["detail"])

    def test_root_internal_path_still_resolvable(self):
        real = self.tmp / "docs" / "a.md"
        real.parent.mkdir(exist_ok=True)
        _write_bytes(real, "x")
        state, detail = gs._validate_ref(
            gs._parse_refs(["repo_file:docs/a.md"])[0],
            self.tmp, self.gov)
        self.assertEqual(state, "resolvable")

    def test_missing_root_internal_path_reports_plain_unresolvable(self):
        real = self.tmp / "docs" / "a.md"
        real.parent.mkdir(exist_ok=True)
        _write_bytes(real, "x")
        state, detail = gs._validate_ref(
            gs._parse_refs(["repo_file:docs/gone.md"])[0],
            self.tmp, self.gov)
        self.assertEqual(state, "unresolvable")
        self.assertIn("path does not exist", detail)


class WriterCliHandlerTests(StoreTestCase):
    """The engine-dispatch faces added by FEAT-055 (``cmd_*`` Namespace
    handlers) get the same guard the self-contained CLI already has: one
    happy path, one structured refusal, and the project-root default —
    proving the engine Namespace flows straight into the executor (FEAT-047
    P2-1 caliber, no argv round-trip).
    """

    def test_cmd_locks_extend_namespace_exit0(self):
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            code = gs.cmd_locks_extend(argparse.Namespace(
                task="FIX-100", files="docs/a.md", ttl_seconds=None,
                extend_by=600, reason="r", operation_id=gs.new_operation_id(),
                timeout=10.0, project_root=str(self.tmp)))
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["code"], "ok")

    def test_cmd_locks_release_namespace_exit0(self):
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            code = gs.cmd_locks_release(argparse.Namespace(
                task="FIX-100", operation_id=gs.new_operation_id(),
                timeout=10.0, project_root=str(self.tmp)))
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["code"], "ok")

    def test_cmd_locks_release_lockless_refusal_exit2(self):
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            code = gs.cmd_locks_release(argparse.Namespace(
                task="FIX-999", operation_id=gs.new_operation_id(),
                timeout=10.0, project_root=str(self.tmp)))
        self.assertEqual(code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["code"], "cross_record_violation")

    def test_cmd_decision_append_refusal_exit2(self):
        out = io.StringIO()
        with mock.patch.object(gs.sys, "stdout", out):
            code = gs.cmd_decision_append(argparse.Namespace(
                decider="   ", content="x", basis="", date=None,
                operation_id=gs.new_operation_id(), dry_run=False,
                expected_revision=None, timeout=10.0,
                project_root=str(self.tmp)))
        self.assertEqual(code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["code"], "schema_violation")

    def test_governance_dir_defaults_to_cwd_without_project_root(self):
        args = argparse.Namespace(task="FIX-100")
        # the self-contained CLI's original face: a relative default that
        # resolves against the process cwd at use time
        self.assertEqual(gs._governance_dir_from(args),
                         Path(".") / gs.GOVERNANCE_DIR_NAME)


class HostRootRebindCanaryTests(unittest.TestCase):
    """FIX-387 防回归 canary — the engine host-root rebind surface must be
    identical to its import-time baseline once this file's tests have run.

    ``_apply_project_root_override`` (verify_workflow.py L234-276) rebinds
    12 module globals and mutates REQUIRED_FILES in place with no restore:
    that state is the CLI's process lifetime, but a test invoking the
    engine in-process makes it the pytest process's lifetime.  The
    FIX-375 polluter (``EngineDispatchExitCodeTests``, pre-FIX-387)
    leaked host/plugin-root divergence into 18 later-run suite nodes
    while every isolated run stayed green.  Defined last so pytest
    (definition order) runs it after every class in this file, it fails
    if any test here — or any earlier test in the same pytest process —
    leaks the surface again.
    """

    def test_host_root_rebind_surface_unchanged_after_file_run(self):
        drifted = _vw_rebind_surface_drift(
            _vw_rebind_surface_snapshot(), _VW_HOST_BASELINE)
        self.assertEqual(
            drifted, {},
            "FIX-387 canary: engine host-root rebind surface drifted from "
            "its import-time baseline — some test in this file (or an "
            "earlier test in this pytest process) reached the engine "
            "in-process with an explicit --project-root and leaked "
            "_apply_project_root_override's rebinding (verify_workflow.py "
            "L234-276) without restoring it. Snapshot the surface in setUp "
            "and restore it in tearDown (see EngineDispatchExitCodeTests."
            "setUp / _vw_rebind_surface_restore); baseline→current: "
            + repr(drifted))


if __name__ == "__main__":
    unittest.main()
