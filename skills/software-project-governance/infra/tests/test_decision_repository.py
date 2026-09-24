"""FEAT-061 — decision_repository guard tests (Layer 1/3).

Covers the codec + authority faces of the storage-separation first table:

  * authority state machine: legal transitions only, epoch fencing,
    unknown/malformed markers refuse fail-closed (unknown states never
    pass — crash/concurrency case ⑩ posture);
  * md document model: full-input line classification (C1-ARCH-05) with
    the REAL hot-file shapes (legacy11 header + live5 rows), duplicate-ID
    refusal before aggregation, variant rows require explicit per-ID
    acceptance, unresolved lines block;
  * JSON store codec: format/schema window refusal (an old tool reading a
    new format refuses explicitly — never misreads), unknown keys refuse,
    verbatim row_raw preservation;
  * byte-faithful round trip: render_markdown(parse(md)) == md;
  * read_snapshot identity over both backends;
  * projection: freshness gate + stale-projection refusal (case ⑤).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_decision_repository.py -v
"""

import json
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import decision_repository as drepo  # noqa: E402
from governance_store import StoreError  # noqa: E402


def _write_bytes(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


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
          "（机录） | version-plan C1（机器写入：governance-store "
          "decision-append op-b13202de；schema v1） |\n")


def _make_gov(tmp: Path, *, md_text=None) -> Path:
    gov = tmp / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    _write_bytes(gov / "decision-log.md",
                 md_text if md_text is not None else _seed_md())
    return gov


class TestAuthorityStateMachine(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="feat061-repo-"))
        self.gov = _make_gov(self.tmp)

    def test_absent_marker_is_initial_md_world(self):
        authority = drepo.load_authority(self.gov)
        self.assertEqual(authority["state"], drepo.STATE_MD_ACTIVE)
        self.assertEqual(authority["backend"], "md")
        self.assertEqual(authority["epoch"], 0)
        self.assertFalse(authority["present"])

    def test_legal_transition_md_to_frozen_and_back(self):
        doc = drepo.write_authority_transition(
            self.gov, from_state=drepo.STATE_MD_ACTIVE,
            to_state=drepo.STATE_CUTOVER_FROZEN, expected_epoch=0,
            owner_token="tok-1")
        self.assertEqual(doc["state"], drepo.STATE_CUTOVER_FROZEN)
        self.assertEqual(doc["epoch"], 1)
        self.assertEqual(doc["backend"], "md")
        doc2 = drepo.write_authority_transition(
            self.gov, from_state=drepo.STATE_CUTOVER_FROZEN,
            to_state=drepo.STATE_MD_ACTIVE, expected_epoch=1,
            owner_token="tok-1")
        self.assertEqual(doc2["state"], drepo.STATE_MD_ACTIVE)
        self.assertEqual(len(doc2["history"]), 2)

    def test_illegal_transition_refused(self):
        with self.assertRaises(StoreError) as ctx:
            drepo.write_authority_transition(
                self.gov, from_state=drepo.STATE_MD_ACTIVE,
                to_state=drepo.STATE_JSON_ACTIVE, expected_epoch=0)
        self.assertEqual(ctx.exception.payload["code"],
                         "illegal_transition")
        # Nothing was written.
        self.assertFalse(
            (self.gov / drepo.AUTHORITY_STATE_FILE).is_file())

    def test_epoch_fencing_refuses_stale_caller(self):
        drepo.write_authority_transition(
            self.gov, from_state=drepo.STATE_MD_ACTIVE,
            to_state=drepo.STATE_CUTOVER_FROZEN, expected_epoch=0)
        with self.assertRaises(StoreError) as ctx:
            drepo.load_authority(self.gov, expected_epoch=0)
        self.assertEqual(ctx.exception.payload["code"], "revision_conflict")
        self.assertEqual(ctx.exception.payload["observed_epoch"], 1)

    def test_unknown_state_refused_fail_closed(self):
        _write_bytes(self.gov / drepo.AUTHORITY_STATE_FILE,
                     json.dumps({"state": "SOMETHING_ELSE", "backend": "md",
                                 "epoch": 0, "generation": 0,
                                 "history": []}))
        with self.assertRaises(StoreError) as ctx:
            drepo.load_authority(self.gov)
        self.assertEqual(ctx.exception.payload["code"],
                         "manual_intervention")
        self.assertIn("unknown", ctx.exception.payload["detail"])

    def test_corrupt_marker_refused_fail_closed(self):
        _write_bytes(self.gov / drepo.AUTHORITY_STATE_FILE, "{not json")
        with self.assertRaises(StoreError) as ctx:
            drepo.load_authority(self.gov)
        self.assertEqual(ctx.exception.payload["code"],
                         "manual_intervention")

    def test_backend_state_mismatch_refused(self):
        _write_bytes(self.gov / drepo.AUTHORITY_STATE_FILE,
                     json.dumps({"state": drepo.STATE_JSON_ACTIVE,
                                 "backend": "md", "epoch": 0,
                                 "generation": 0, "history": []}))
        with self.assertRaises(StoreError):
            drepo.load_authority(self.gov)


class TestMdDocumentModel(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="feat061-repo-"))

    def test_full_input_classification(self):
        items = drepo.classify_md_document(_seed_md())
        kinds = [item["kind"] for item in items]
        self.assertEqual(kinds.count(drepo.CLASS_RECORD), 2)
        self.assertEqual(kinds.count(drepo.CLASS_TABLE_HEADER), 1)
        self.assertEqual(kinds.count(drepo.CLASS_TABLE_SEPARATOR), 1)
        self.assertNotIn(drepo.CLASS_UNRESOLVED, kinds)
        records = [item for item in items
                   if item["kind"] == drepo.CLASS_RECORD]
        self.assertEqual([r["id"] for r in records],
                         ["DEC-147", "DEC-237"])
        self.assertEqual(records[0]["shape"], "legacy11")
        self.assertEqual(records[1]["shape"], "live5")
        # provenance extracted from the live5 marker
        self.assertEqual(records[1]["provenance"]["op_id"], "op-b13202de")

    def test_unresolved_line_reported(self):
        text = _seed_md() + "| 手写悬空行 | 无 DEC 锚点 |\n"
        items = drepo.classify_md_document(text)
        unresolved = [item for item in items
                      if item["kind"] == drepo.CLASS_UNRESOLVED]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["line_no"], 7)

    def test_zero_padded_id_preserved_verbatim(self):
        text = _seed_md() + "| DEC-060 | 2026-05-03 | 三列旧行样本 |\n"
        items = drepo.classify_md_document(text)
        records = [item for item in items
                   if item["kind"] == drepo.CLASS_RECORD]
        self.assertIn("DEC-060", [r["id"] for r in records])

    def test_variant_row_requires_explicit_acceptance(self):
        text = _seed_md() + "| DEC-060 | 2026-05-03 | 三列旧行样本 |\n"
        items = drepo.classify_md_document(text)
        with self.assertRaises(StoreError) as ctx:
            drepo.build_store_from_document(items)
        self.assertIn("explicit", ctx.exception.payload["detail"])
        # With an explicit acceptance the migration proceeds and the
        # acceptance is recorded verbatim.
        store = drepo.build_store_from_document(
            items, variant_acceptances={"DEC-060": "三列勘误行——显式排除"})
        variant = [r for r in store["records"] if r["id"] == "DEC-060"][0]
        self.assertEqual(variant["shape"], "variant")
        self.assertEqual(variant["variant_acceptance"],
                         "三列勘误行——显式排除")
        self.assertEqual(variant["cells"],
                         ["DEC-060", "2026-05-03", "三列旧行样本"])

    def test_duplicate_id_refused_before_aggregation(self):
        text = _seed_md() + "| DEC-237 | 2026-09-26 | 重复行 | | | \n"
        items = drepo.classify_md_document(text)
        with self.assertRaises(StoreError) as ctx:
            drepo.build_store_from_document(items)
        self.assertEqual(ctx.exception.payload["code"],
                         "cross_record_violation")

    def test_unresolved_line_blocks_migration(self):
        text = _seed_md() + "| 无锚点 |\n"
        items = drepo.classify_md_document(text)
        with self.assertRaises(StoreError) as ctx:
            drepo.build_store_from_document(items)
        self.assertIn("unresolved", ctx.exception.payload["detail"])

    def test_render_round_trip_is_byte_faithful(self):
        text = _seed_md()
        items = drepo.classify_md_document(text)
        store = drepo.build_store_from_document(items)
        rendered = drepo.render_markdown(store)
        self.assertEqual(rendered, text)

    def test_render_is_duplicate_safe_and_positional(self):
        """勘正对（base + 注记行，同 ID）逐字保留——位置配对渲染，禁止
        按 id 字典折叠（真实数据演练抓到的缺陷回归钉）。"""
        text = (_seed_md()
                + "| DEC-194 | 2026-09-14 | Coordinator | FIX-330 口径 |"
                  " 依据 |\n"
                + "| DEC-194 补记 | 2026-09-17 | Coordinator | 第③点补齐 |"
                  " 依据 |\n")
        items = drepo.classify_md_document(text)
        store = drepo.build_store_from_document(
            items, duplicate_acceptances={"DEC-194": "勘正行对——两行保留"})
        self.assertEqual(len(store["records"]), 4)
        rendered = drepo.render_markdown(store)
        self.assertEqual(rendered, text)
        # The store re-load accepts the pair (acceptance persisted).
        import tempfile
        gov = _make_gov(self.tmp)
        store_path = gov / drepo.JSON_STORE_FILE
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        loaded = drepo.load_json_store(store_path)
        self.assertEqual(len(loaded["records"]), 4)
        # Without the acceptance the store codec refuses.
        store.pop("duplicate_acceptances")
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        with self.assertRaises(StoreError):
            drepo.load_json_store(store_path)

    def test_store_codec_refuses_unknown_format_and_keys(self):
        import tempfile
        gov = _make_gov(self.tmp)
        store_path = gov / drepo.JSON_STORE_FILE
        items = drepo.classify_md_document(_seed_md())
        store = drepo.build_store_from_document(items)
        _write_bytes(store_path,
                     json.dumps(store, ensure_ascii=False))
        loaded = drepo.load_json_store(store_path)
        self.assertEqual(loaded["format"], "decision-store")
        # unknown top-level key
        store["future_field"] = 1
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        with self.assertRaises(StoreError) as ctx:
            drepo.load_json_store(store_path)
        self.assertEqual(ctx.exception.payload["code"], "schema_violation")
        # wrong format — explicit refusal, never a silent misread
        store.pop("future_field")
        store["format"] = "something-else"
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        with self.assertRaises(StoreError) as ctx:
            drepo.load_json_store(store_path)
        self.assertEqual(ctx.exception.payload["code"],
                         "schema_version_unsupported")
        # newer schema version — refused, never guessed
        store["format"] = "decision-store"
        store["schema_version"] = 2
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        with self.assertRaises(StoreError) as ctx:
            drepo.load_json_store(store_path)
        self.assertEqual(ctx.exception.payload["code"],
                         "schema_version_unsupported")

    def test_store_codec_refuses_duplicate_ids(self):
        import tempfile
        gov = _make_gov(self.tmp)
        store_path = gov / drepo.JSON_STORE_FILE
        items = drepo.classify_md_document(_seed_md())
        store = drepo.build_store_from_document(items)
        store["records"].append(dict(store["records"][0]))
        _write_bytes(store_path, json.dumps(store, ensure_ascii=False))
        with self.assertRaises(StoreError) as ctx:
            drepo.load_json_store(store_path)
        self.assertEqual(ctx.exception.payload["code"],
                         "cross_record_violation")


class TestReadSnapshot(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="feat061-repo-"))
        self.gov = _make_gov(self.tmp)

    def test_md_backend_snapshot_identity(self):
        snapshot = drepo.read_snapshot(self.gov)
        self.assertEqual(snapshot["backend"], "md")
        self.assertEqual(snapshot["record_count"], 2)
        self.assertEqual([r["id"] for r in snapshot["records"]],
                         ["DEC-147", "DEC-237"])
        self.assertEqual(snapshot["epoch"], 0)
        self.assertEqual(snapshot["generation"], 0)
        import hashlib
        self.assertEqual(
            snapshot["content_digest"],
            hashlib.sha256(
                (self.gov / "decision-log.md").read_bytes()).hexdigest())

    def test_json_backend_snapshot_identity(self):
        items = drepo.classify_md_document(_seed_md())
        store = drepo.build_store_from_document(items)
        _write_bytes(self.gov / drepo.JSON_STORE_FILE,
                     json.dumps(store, ensure_ascii=False, indent=2) + "\n")
        _write_bytes(self.gov / drepo.AUTHORITY_STATE_FILE, json.dumps({
            "schema_version": 1, "state": drepo.STATE_JSON_ACTIVE,
            "backend": "json", "epoch": 1, "generation": 1,
            "manifest_digest": None, "migration_id": "M-1",
            "owner_token": None, "content_digest": None, "frozen": None,
            "history": [],
        }))
        snapshot = drepo.read_snapshot(self.gov, expected_epoch=1)
        self.assertEqual(snapshot["backend"], "json")
        self.assertEqual(snapshot["epoch"], 1)
        self.assertEqual(snapshot["record_count"], 2)
        self.assertEqual(snapshot["schema_version"], 1)

    def test_next_decision_id_and_archive_collision(self):
        snapshot = drepo.read_snapshot(self.gov)
        self.assertEqual(
            drepo.next_decision_id(snapshot["records"]), "DEC-238")
        with self.assertRaises(StoreError) as ctx:
            drepo.next_decision_id(snapshot["records"],
                                   archive_numbers={238})
        self.assertEqual(ctx.exception.payload["code"],
                         "cross_record_violation")


class TestProjectionFace(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="feat061-repo-"))
        self.gov = _make_gov(self.tmp)
        items = drepo.classify_md_document(_seed_md())
        self.store = drepo.build_store_from_document(items)
        self.store_path = self.gov / drepo.JSON_STORE_FILE
        _write_bytes(self.store_path,
                     json.dumps(self.store, ensure_ascii=False, indent=2)
                     + "\n")
        _write_bytes(self.gov / drepo.AUTHORITY_STATE_FILE, json.dumps({
            "schema_version": 1, "state": drepo.STATE_JSON_ACTIVE,
            "backend": "json", "epoch": 1, "generation": 1,
            "manifest_digest": None, "migration_id": "M-1",
            "owner_token": None, "content_digest": None, "frozen": None,
            "history": [],
        }))

    def test_projection_writes_and_checkpoint_fresh(self):
        result = drepo.project_store_to_markdown(
            self.gov, reason="test")
        self.assertEqual(result["status"], "fresh")
        checkpoint = drepo.load_projection_checkpoint(self.gov)
        self.assertEqual(checkpoint["status"], "fresh")
        freshness = drepo.projection_freshness(self.gov)
        self.assertEqual(freshness["status"], "fresh")

    def test_freshness_detects_manual_md_edit_as_stale(self):
        drepo.project_store_to_markdown(self.gov, reason="test")
        # A direct (unattributed) md edit diverges the projection.
        with open(self.gov / "decision-log.md", "a", encoding="utf-8") as fh:
            fh.write("| DEC-999 | 2026-09-26 | 手改 | | | \n")
        freshness = drepo.projection_freshness(self.gov)
        self.assertEqual(freshness["status"], "stale")

    def test_missing_projection_reported(self):
        (self.gov / "decision-log.md").unlink()
        freshness = drepo.projection_freshness(self.gov)
        self.assertEqual(freshness["status"], "missing")


if __name__ == "__main__":
    unittest.main()
