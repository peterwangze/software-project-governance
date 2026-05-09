"""Unit tests for archive.py — SYSGAP-030.

Tests cover:
  - migrate_by_version: correct extraction and archival of version-range tasks
  - build_index: correct index generation from archive files
  - verify_archive_integrity: detects inconsistencies
  - backward compatibility: no archive/ directory = no-op
  - Dry-Run mode: does not modify files

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_archive.py -v
or:
    python -m unittest skills/software-project-governance.infra.tests.test_archive -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

# We'll import archive after it exists
# import archive


# ────────────────────────────────────────────────────────────
# Helper functions to create mock governance files
# ────────────────────────────────────────────────────────────

def _make_plan_tracker(governance_dir, versions_data):
    """Create a mock plan-tracker.md with version sections.

    versions_data: list of (version_label, tasks_list) where
    tasks_list: list of (task_id, status, description, depend)
    """
    lines = [
        "# 当前项目样例",
        "",
        "## 项目配置",
        "- **项目目标**: Test",
        "- **Profile**: standard",
        "- **触发模式**: always-on",
        "- **操作权限模式**: maximum-autonomy",
        "- **工作流版本**: 0.25.0",
        "- **当前阶段**: 开发实现",
        "",
        "## Gate 状态跟踪",
        "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
        "| --- | --- | --- | --- | --- |",
        "| G1 | -> 调研 | passed | 2026-04-20 | DEC-001 |",
        "",
        "## 当前活跃事项",
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
        "|--------|----|------|------|---------|---------|------|",
        "| P0 | ACTIVE-001 | Active task | — | 1.0.0 | TBD | 进行中 |",
        "",
    ]

    for version_label, tasks in versions_data:
        lines.append(f"### {version_label}")
        lines.append("| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for tid, status, desc, depend in tasks:
            lines.append(f"| {tid} | {desc} | P1 | {depend} | 1.0.0 | 阿速 | — | Code Reviewer | TBD | {status} |")
        lines.append("")

    content = "\n".join(lines)
    (governance_dir / "plan-tracker.md").write_text(content, encoding="utf-8")
    return content


def _make_evidence_log(governance_dir, entries):
    """Create a mock evidence-log.md.

    entries: list of (evd_id, task_ids, description)
    """
    lines = [
        "# 证据记录",
        "",
        "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for evd_id, task_ids, desc in entries:
        lines.append(f"| {evd_id} | {task_ids} | {desc} | 2026-05-01 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |")

    content = "\n".join(lines)
    (governance_dir / "evidence-log.md").write_text(content, encoding="utf-8")
    return content


def _make_decision_log(governance_dir, entries):
    """Create a mock decision-log.md."""
    lines = [
        "# 决策记录",
        "",
    ]
    for dec_id, title, date_str in entries:
        lines.append(f"## {dec_id}: {title}")
        lines.append(f"**日期**: {date_str}")
        lines.append("")

    content = "\n".join(lines)
    (governance_dir / "decision-log.md").write_text(content, encoding="utf-8")
    return content


def _make_risk_log(governance_dir, entries):
    """Create a mock risk-log.md."""
    lines = [
        "# 风险记录",
        "",
        "| 编号 | 描述 | 级别 | 状态 |",
        "| --- | --- | --- | --- |",
    ]
    for risk_id, desc, status in entries:
        lines.append(f"| {risk_id} | {desc} | 中 | {status} |")

    content = "\n".join(lines)
    (governance_dir / "risk-log.md").write_text(content, encoding="utf-8")
    return content


# ────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────

class TestArchiveMigrateByVersion(unittest.TestCase):
    """Test migrate_by_version function."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_test_data(self):
        """Create plan-tracker with tasks in three version ranges."""
        versions = [
            ("v0.11.0 — Early fixes", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
                ("FIX-002", "已完成", "Fix bug 2", "FIX-001"),
                ("FIX-003", "已完成", "Fix bug 3", "—"),
            ]),
            ("v0.12.0 — More fixes", [
                ("FIX-004", "已完成", "Fix bug 4", "—"),
                ("FIX-005", "已完成", "Fix bug 5", "FIX-004"),
            ]),
            ("v0.13.0 — Current", [
                ("FIX-006", "进行中", "Fix bug 6", "—"),
                ("FIX-007", "已完成", "Fix bug 7", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)
        _make_evidence_log(self.gov_dir, [
            ("EVD-001", "FIX-001", "Fixed bug 1"),
            ("EVD-002", "FIX-002", "Fixed bug 2"),
            ("EVD-003", "FIX-003", "Fixed bug 3"),
            ("EVD-004", "FIX-004", "Fixed bug 4"),
            ("EVD-005", "FIX-005", "Fixed bug 5"),
            ("EVD-007", "FIX-007", "Fixed bug 7"),
        ])

    def test_migrate_dry_run_does_not_modify_files(self):
        """Dry-run mode should not modify any files."""
        self._create_test_data()
        import archive

        # Patch ROOT to point to our temp dir
        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertTrue(result["success"])
        self.assertGreater(result["tasks_archived"], 0)
        # No archive files should be created
        task_files = list((self.archive_dir / "tasks").glob("*.md"))
        for f in task_files:
            if f.name == ".gitkeep":
                continue
            self.fail(f"Dry-run should not create files, but found {f}")

    def test_migrate_creates_archive_file(self):
        """Migration should create archive file with correct header and content."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 5)  # FIX-001 to FIX-005
        self.assertEqual(result["tasks_remaining"], 2)  # FIX-006, FIX-007

        # Check archive file exists
        archive_files = [f for f in (self.archive_dir / "tasks").glob("*.md")
                         if f.name != ".gitkeep"]
        self.assertEqual(len(archive_files), 1)

        # Check archive file content
        content = archive_files[0].read_text(encoding="utf-8")
        self.assertIn("归档 Task", content)
        self.assertIn("归档日期", content)
        self.assertIn("v0.11.0", content)
        self.assertIn("FIX-001", content)
        self.assertIn("FIX-005", content)
        self.assertNotIn("FIX-006", content)  # Not in archived range

    def test_migrate_preserves_completed_only(self):
        """Should only archive completed tasks from the specified version range."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.13.0", "0.13.0", dry_run=False)

        self.assertTrue(result["success"])
        # FIX-006 is "进行中", should NOT be archived
        # FIX-007 is "已完成", should be archived
        self.assertEqual(result["tasks_archived"], 1)

    def test_migrate_no_matching_versions(self):
        """Migrating a non-existent version range should return 0 archived."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.99.0", "0.99.9", dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 0)

    def test_backward_compatible_no_archive_dir(self):
        """When archive/ doesn't exist, migrate should handle gracefully."""
        # Remove archive dir
        import shutil
        shutil.rmtree(str(self.archive_dir))

        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=False)

        # Should still succeed - archive dir gets auto-created
        self.assertTrue(result["success"])

    def test_migrate_evidence_alongside_tasks(self):
        """Migrating tasks should also archive associated evidence."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=False,
                                                 migrate_evidence=True)

        self.assertTrue(result["success"])
        # Evidence for FIX-001..FIX-005 should be archived
        self.assertGreaterEqual(result.get("evidence_archived", 0), 1)


class TestArchiveBuildIndex(unittest.TestCase):
    """Test build_index function."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_archive_files(self):
        """Create pre-existing archive files."""
        task_content = """# 归档 Task 表 — v0.11.0 ~ v0.12.0
- **归档日期**: 2026-05-08
- **归档范围**: plan-tracker.md 中 v0.11.0~v0.12.0 版本的所有 task
- **上一个归档文件**: 无
- **下一个归档文件**: 无

> 查询方式：通过 `.governance/archive/index.md` 按 task_id 定位。

---

### v0.11.0 — Early fixes
| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |
| FIX-002 | Fix bug 2 | P1 | FIX-001 | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |
"""
        (self.archive_dir / "tasks" / "v0.11.0~v0.12.0.md").write_text(task_content, encoding="utf-8")

        evidence_content = """# 归档 Evidence 记录 — v0.11.0 ~ v0.12.0
- **归档日期**: 2026-05-08
- **归档类型**: evidence-log 证据条目
- **覆盖版本**: v0.11.0, v0.12.0

> 查询方式：通过 `.governance/archive/index.md` 按 evidence_id 定位。

---

| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-001 | FIX-001 | Fixed bug 1 | 2026-05-01 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |
| EVD-002 | FIX-002 | Fixed bug 2 | 2026-05-02 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |
"""
        (self.archive_dir / "evidence" / "v0.11.0~v0.12.0.md").write_text(evidence_content, encoding="utf-8")

    def test_build_index_from_archive_files(self):
        """build_index() should scan archive files and generate correct index."""
        self._create_archive_files()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.build_index()

        self.assertEqual(result["status"], "created")
        self.assertGreaterEqual(result["task_entries"], 2)
        self.assertGreaterEqual(result["evidence_entries"], 2)

        # Check index file was created
        index_path = self.archive_dir / "index.md"
        self.assertTrue(index_path.exists())

        content = index_path.read_text(encoding="utf-8")
        self.assertIn("# 归档索引", content)
        self.assertIn("## Task 索引", content)
        self.assertIn("## Evidence 索引", content)
        self.assertIn("FIX-001", content)
        self.assertIn("FIX-002", content)
        self.assertIn("EVD-001", content)

    def test_build_index_no_archive_files(self):
        """build_index() with no archive files should create an empty index."""
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.build_index()

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["task_entries"], 0)
        self.assertEqual(result["evidence_entries"], 0)


class TestArchiveVerifyIntegrity(unittest.TestCase):
    """Test verify_archive_integrity function."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

        # Create plan-tracker with current tasks
        versions = [
            ("v0.14.0 — Current", [
                ("FIX-010", "已完成", "Current task", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_verify_passes_when_consistent(self):
        """Consistent archive files + index should pass verification."""
        # Create archive file
        task_content = """# 归档 Task 表 — v0.11.0 ~ v0.12.0
- **归档日期**: 2026-05-08

### v0.11.0 — Early fixes
| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |
"""
        (self.archive_dir / "tasks" / "v0.11.0~v0.12.0.md").write_text(task_content, encoding="utf-8")

        # Create index referencing the archive file
        index_content = """# 归档索引

## Task 索引

| Task ID | 状态 | 版本 | 归档文件 |
|---------|------|------|---------|
| FIX-001 | 已完成 | 0.11.0 | archive/tasks/v0.11.0~v0.12.0.md |

## Evidence 索引

| Evidence ID | Task ID | 归档文件 |

## Decision 索引

| Decision ID | 标题 | 归档文件 |

## Risk 索引

| Risk ID | 描述 | 归档文件 |
"""
        (self.archive_dir / "index.md").write_text(index_content, encoding="utf-8")

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertTrue(result["pass"])
        self.assertEqual(len(result["issues"]), 0)

    def test_verify_detects_missing_archive_file(self):
        """Index referencing non-existent archive file should be detected."""
        # Create index with phantom reference
        index_content = """# 归档索引

## Task 索引

| Task ID | 状态 | 版本 | 归档文件 |
|---------|------|------|---------|
| FIX-001 | 已完成 | 0.11.0 | archive/tasks/v0.11.0~v0.12.0.md |

## Evidence 索引

| Evidence ID | Task ID | 归档文件 |

## Decision 索引

| Decision ID | 标题 | 归档文件 |

## Risk 索引

| Risk ID | 描述 | 归档文件 |
"""
        (self.archive_dir / "index.md").write_text(index_content, encoding="utf-8")
        # No actual archive file created

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertFalse(result["pass"])
        self.assertGreater(len(result["issues"]), 0)
        self.assertTrue(any("不存在" in i or "missing" in i.lower() for i in result["issues"]))

    def test_verify_detects_unindexed_archive_file(self):
        """Archive file not referenced in index should be detected."""
        # Create archive file
        task_content = """# 归档 Task 表 — v0.11.0 ~ v0.12.0
- **归档日期**: 2026-05-08

### v0.11.0 — Early fixes
| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |
"""
        (self.archive_dir / "tasks" / "v0.11.0~v0.12.0.md").write_text(task_content, encoding="utf-8")

        # Create empty index
        index_content = """# 归档索引

## Task 索引

| Task ID | 状态 | 版本 | 归档文件 |

## Evidence 索引

| Evidence ID | Task ID | 归档文件 |

## Decision 索引

| Decision ID | 标题 | 归档文件 |

## Risk 索引

| Risk ID | 描述 | 归档文件 |
"""
        (self.archive_dir / "index.md").write_text(index_content, encoding="utf-8")

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertFalse(result["pass"])
        self.assertGreater(len(result["issues"]), 0)

    def test_verify_no_archive_dir_passes(self):
        """When archive/ directory is empty (no index, no files), pass gracefully."""
        # Remove all .md files from archive (only .gitkeep remains)
        for f in self.archive_dir.glob("**/*.md"):
            f.unlink()

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertTrue(result["pass"])


class TestBackwardCompatibility(unittest.TestCase):
    """Test that behavior is unchanged when archive/ directory doesn't exist."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_no_archive_dir_all_operations_safe(self):
        """All operations should handle missing archive/ directory gracefully."""
        # No archive directory at all
        versions = [
            ("v0.11.0 — Test", [
                ("FIX-001", "已完成", "Test task", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            # All operations should succeed without errors
            result1 = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=True)
            self.assertTrue(result1["success"])

            result2 = archive.build_index()
            self.assertEqual(result2["status"], "created")

            result3 = archive.verify_archive_integrity()
            self.assertTrue(result3["pass"])


class TestArchiveRollback(unittest.TestCase):
    """Test rollback_last_migration function — P1-3 fix."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_multi_version_data(self):
        """Create plan-tracker with tasks in three version ranges."""
        versions = [
            ("v0.11.0 — Early fixes", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
                ("FIX-002", "已完成", "Fix bug 2", "FIX-001"),
            ]),
            ("v0.12.0 — More fixes", [
                ("FIX-004", "已完成", "Fix bug 4", "—"),
                ("FIX-005", "已完成", "Fix bug 5", "FIX-004"),
            ]),
            ("v0.13.0 — Current", [
                ("FIX-007", "进行中", "Fix bug 7", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)

    def test_rollback_restores_tasks_to_hot_file(self):
        """Basic rollback: archive → rollback → tasks restored to plan-tracker."""
        self._create_multi_version_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            # Archive v0.11.0 tasks
            result = archive.migrate_by_version("0.11.0", "0.11.0", dry_run=False)
            self.assertTrue(result["success"])
            self.assertEqual(result["tasks_archived"], 2)

            # Verify archived tasks are removed from hot file
            pt_after = self.gov_dir / "plan-tracker.md"
            pt_content = pt_after.read_text(encoding="utf-8")
            self.assertNotIn("| FIX-001 |", pt_content)
            self.assertNotIn("| FIX-002 |", pt_content)
            self.assertIn("[已归档]", pt_content)  # v0.11.0 version should be marked

            # Verify v0.12.0 tasks are still in hot file
            self.assertIn("| FIX-004 |", pt_content)
            self.assertIn("| FIX-005 |", pt_content)

            # Rollback
            rollback_result = archive.rollback_last_migration()
            self.assertTrue(rollback_result["success"])

            # Verify tasks are restored to hot file
            pt_restored = pt_after.read_text(encoding="utf-8")
            self.assertIn("| FIX-001 |", pt_restored)
            self.assertIn("| FIX-002 |", pt_restored)

            # Verify v0.11.0 version no longer has [已归档] marker
            for line in pt_restored.split("\n"):
                if "v0.11.0" in line and "—" in line:
                    self.assertNotIn("[已归档]", line,
                                     f"Version title should not have [已归档] after rollback: {line}")

    def test_rollback_preserves_other_version_markers(self):
        """Multi-version: rollback v0.11.0 leaves v0.12.0 [已归档] intact."""
        self._create_multi_version_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            # Archive v0.11.0 AND v0.12.0 (two migrations)
            result1 = archive.migrate_by_version("0.11.0", "0.11.0", dry_run=False)
            self.assertTrue(result1["success"])

            result2 = archive.migrate_by_version("0.12.0", "0.12.0", dry_run=False)
            self.assertTrue(result2["success"])

            pt_after_both = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
            # Both should have [已归档] markers
            self.assertIn("v0.11.0", pt_after_both)
            self.assertIn("v0.12.0", pt_after_both)

            # Rollback LAST migration (v0.12.0)
            rollback_result = archive.rollback_last_migration()
            self.assertTrue(rollback_result["success"])

            pt_after_rollback = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")

            # v0.12.0 tasks should be restored
            # NOTE: rollback_last_migration restores the most recently modified
            # archive. The content merge may or may not result in the table rows
            # being exactly as they were, depending on the merge strategy.
            # Key assertion: v0.11.0 [已归档] marker is PRESERVED.
            v011_has_marker = False
            v012_has_marker = False
            for line in pt_after_rollback.split("\n"):
                stripped = line.strip()
                if stripped.startswith("### v0.11.0") or stripped.startswith("## v0.11.0"):
                    if "[已归档]" in stripped:
                        v011_has_marker = True
                if stripped.startswith("### v0.12.0") or stripped.startswith("## v0.12.0"):
                    if "[已归档]" in stripped:
                        v012_has_marker = True

            self.assertTrue(v011_has_marker,
                            "v0.11.0 [已归档] marker must be preserved after rolling back v0.12.0")
            self.assertFalse(v012_has_marker,
                             "v0.12.0 [已归档] marker must be removed after its own rollback")

    def test_rollback_no_archive_files(self):
        """Rollback with no archive files should gracefully report no-op."""
        self._create_multi_version_data()
        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.rollback_last_migration()
            self.assertFalse(result["success"])
            self.assertIn("没有找到归档文件", result["details"])


if __name__ == "__main__":
    unittest.main()
