"""FEAT-076 (0.93.0) — the layered evidence read entry.

GovernanceDataSource's row-family surface is the unified read entry the
migration's read-compatibility gate requires (DEC-282 C-1(b) condition 3):
hot + cold + per-family rows + find-by-id + layer stats. Check 19's
review-coverage path and Check 28s's three-track face are the first
layering-aware consumers proven here.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_workflow as vw


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


HOT_EVIDENCE = "\n".join([
    "# 当前项目证据记录",
    "| EVD-1 | FIX-950 | 产品代码 | hot evd |",
    "| REVIEW-FIX-950-CODE-R0 | FIX-950 | 产品代码 | hot review |",
    "| TRIAGE-FIX-950 | FIX-950 | 变更控制 | hot triage |",
    "| RECO-FIX-950 | FIX-950 | 治理记录 | hot reco |",
    "| REVIEW-FIX-951-R1 | FIX-951 | 产品代码 | hot review 2 |",
])

COLD_EVIDENCE_FILE = "\n".join([
    "# 归档 Review 行族记录 — v0.1.0 ~ v0.90.0",
    "- **归档日期**: 2026-09-29",
    "- **条目数**: 2",
    "",
    "| 审查ID | 关联任务 | 阶段 | 审查类型 | 结论纪要 | 事实依据 | 审查人 | 日期 | Gate | 状态 |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    "| REVIEW-FIX-940-R2 | FIX-940 | 产品代码 | 代码审查 | APPROVED | facts | Code Reviewer | 2026-05-01 | G11 | APPROVED |",
    "| REVIEW-FIX-939 | FIX-939 | 产品代码 | 代码审查 | APPROVED | facts | Code Reviewer | 2026-05-01 | G11 | APPROVED |",
    "| EVD-900 | FIX-940 | 产品代码 | cold evd row |",
])


class FEAT076GovernanceDataSourceFamilySurfaceTests(unittest.TestCase):
    """The unified read entry: family rows across hot + cold layers."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        _write(self.gov / "evidence-log.md", HOT_EVIDENCE)
        _write(self.gov / "plan-tracker.md", "### 优先级一览\n")
        _write(self.gov / "archive" / "evidence"
               / "evidence-review-v0.1.0-0.90.0.md", COLD_EVIDENCE_FILE)

    def tearDown(self):
        self.tempdir.cleanup()

    def _ds(self):
        return vw.GovernanceDataSource(
            sample_path=self.gov / "plan-tracker.md",
            evidence_path=self.gov / "evidence-log.md",
        )

    def test_get_all_family_rows_aggregates_hot_and_cold(self):
        ds = self._ds()
        review = ds.get_all_family_rows("REVIEW")
        by_id = {r["row_id"]: r for r in review}
        # Hot rows…
        self.assertEqual(by_id["REVIEW-FIX-950-CODE-R0"]["source"], "hot")
        self.assertEqual(by_id["REVIEW-FIX-951-R1"]["source"], "hot")
        # …and cold rows from the archive file, same record shape.
        self.assertEqual(by_id["REVIEW-FIX-940-R2"]["source"], "cold")
        self.assertEqual(by_id["REVIEW-FIX-940-R2"]["task_ids"], "FIX-940")
        self.assertEqual(by_id["REVIEW-FIX-939"]["file"],
                         "archive/evidence/evidence-review-v0.1.0-0.90.0.md")
        # EVD family sees BOTH the hot EVD row and the cold one.
        evd_ids = ds.get_all_family_row_ids("EVD")
        self.assertEqual(evd_ids, {"EVD-1", "EVD-900"})
        # Unknown family fails loudly (never an empty silent answer).
        with self.assertRaises(ValueError):
            ds.get_all_family_rows("BOGUS")

    def test_find_row_locates_across_layers_hot_wins(self):
        ds = self._ds()
        hot_hit = ds.find_row("EVD-1")
        self.assertEqual(hot_hit["source"], "hot")
        cold_hit = ds.find_row("REVIEW-FIX-940-R2")
        self.assertEqual(cold_hit["source"], "cold")
        self.assertIsNone(ds.find_row("EVD-424242"))

    def test_layer_stats_counts_and_three_track_basis(self):
        ds = self._ds()
        stats = ds.layer_stats()
        self.assertEqual(stats["families"]["REVIEW"],
                         {"hot_rows": 2, "cold_rows": 2, "total_rows": 4})
        self.assertEqual(stats["families"]["TRIAGE"]["cold_rows"], 0)
        layers = stats["layers"]
        self.assertEqual(
            layers["hot_bytes"],
            (self.gov / "evidence-log.md").stat().st_size)
        self.assertEqual(
            layers["cold_bytes"],
            (self.gov / "archive" / "evidence"
             / "evidence-review-v0.1.0-0.90.0.md").stat().st_size)
        self.assertEqual(layers["total_bytes"],
                         layers["hot_bytes"] + layers["cold_bytes"])

    def test_layer_stats_empty_archive_world(self):
        # Pre-layering world: no archive dir → cold side reports zeros,
        # never raises (backward compatibility).
        import shutil
        shutil.rmtree(self.gov / "archive")
        ds = self._ds()
        stats = ds.layer_stats()
        self.assertEqual(stats["layers"]["cold_bytes"], 0)
        self.assertEqual(stats["families"]["REVIEW"]["cold_rows"], 0)


class FEAT076CheckFacesTests(unittest.TestCase):
    """The layering-aware check faces: Check 19 coverage + Check 28s track 3."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        # A COMPLETED task whose EVD + REVIEW rows live ONLY in the cold
        # layer (the post-migration world for closed cycles).
        _write(self.gov / "evidence-log.md", "# 当前项目证据记录\n")
        _write(self.gov / "plan-tracker.md", "\n".join([
            "### 优先级一览",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| **P2** | FIX-940 | item | — | 0.80.0 | path | ✅ 已完成 |",
            "",
        ]))
        _write(self.gov / "archive" / "evidence"
               / "evidence-review-v0.1.0-0.90.0.md", "\n".join([
            "# 归档 Review 行族记录 — v0.1.0 ~ v0.90.0",
            "| 审查ID | 关联任务 | 阶段 | 审查类型 | 结论纪要 | 事实依据 | 审查人 | 日期 | Gate | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| REVIEW-FIX-940-CODE-R0 | FIX-940 | 产品代码 | 代码审查 | APPROVED | facts | Code Reviewer | 2026-05-01 | G11 | APPROVED |",
        ]))
        _write(self.gov / "archive" / "evidence"
               / "evidence-v0.1.0-0.80.0.md", "\n".join([
            "# 归档 Evidence 记录 — v0.1.0 ~ v0.80.0",
            "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| EVD-900 | FIX-940 | product work | 2026-05-01 | 产品代码 | skills/foo.py | Dev | CR | APPROVED |  |",
        ]))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_check_agent_team_review_sees_cold_coverage(self):
        with patch.object(vw, "EVIDENCE_PATH", self.gov / "evidence-log.md"), \
                patch.object(vw, "SAMPLE_PATH", self.gov / "plan-tracker.md"), \
                patch.object(vw, "GOVERNANCE_DIR", self.gov), \
                patch.object(vw, "HOST_PROJECT_ROOT", self.root):
            import checks.review_domain as rd
            result = rd.check_agent_team_review()
        # The cold EVD row proves FIX-940 touched product code; the cold
        # REVIEW row proves independent coverage → NOT a review gap.
        self.assertEqual(result["total_tasks"], 1)
        self.assertEqual(result["reviewed"], 1)
        self.assertEqual(result["review_gap_tasks"], [])
        self.assertTrue(result["pass"])

    def test_check_governance_data_size_reports_layer_track(self):
        # The schema stays a plugin asset; only the layer facts come from
        # the fixture root (explicit-root legacy semantics). Passing the
        # schema dict directly keeps the fixture hermetic.
        schema = {"governance_data_size": {
            "enabled": True, "warn_bytes": 200000, "error_bytes": 250000,
            "files": [".governance/evidence-log.md"],
        }}
        result = vw.check_governance_data_size(root=str(self.root),
                                               schema=schema)
        self.assertIn("layers", result)
        layers = result["layers"]
        self.assertIsNotNone(layers)
        self.assertGreater(layers["cold_bytes"], 0)
        self.assertGreater(layers["total_bytes"], layers["hot_bytes"])
        self.assertEqual(
            layers["hot_bytes"],
            (self.gov / "evidence-log.md").stat().st_size)


if __name__ == "__main__":
    unittest.main()
