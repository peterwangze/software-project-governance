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


def _make_plan_tracker_checklist(governance_dir, versions_data):
    """Create a mock plan-tracker.md with checklist-format task sections.

    versions_data: list of (version_label, tasks_list) where
    tasks_list: list of (task_id, checked, description)
        checked: True for [x], False for [ ]
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
    ]

    for version_label, tasks in versions_data:
        lines.append(f"### {version_label}")
        lines.append("")
        lines.append("**交付清单**:")
        for tid, checked, desc in tasks:
            mark = "x" if checked else " "
            lines.append(f"- [{mark}] **{tid}**: {desc}")
        lines.append("")

    content = "\n".join(lines)
    (governance_dir / "plan-tracker.md").write_text(content, encoding="utf-8")
    return content


def _make_plan_tracker_with_roadmap(governance_dir, roadmap_versions, version_tasks):
    """Create a plan-tracker.md with version roadmap table + version sections.

    roadmap_versions: list of (version, status)
        e.g., [("0.11.0", "已发布"), ("0.12.0", "已发布"), ("0.13.0", "进行中")]
    version_tasks: list of (version_label, tasks_list)
        where tasks_list: list of (task_id, status, desc, depend)
    """
    lines = [
        "# 当前项目样例",
        "",
        "## 项目配置",
        "- **项目目标**: Test project for archive --auto",
        "- **Profile**: standard",
        "- **触发模式**: always-on",
        "- **操作权限模式**: maximum-autonomy",
        "- **工作流版本**: 0.25.0",
        "- **当前阶段**: 开发实现",
        "",
        "## Gate 状态跟踪",
        "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
        "| --- | --- | --- | --- | --- |",
        "| G1 | -> 调研 | passed | 2026-04-20 | DEC-001... |",
        "",
        "## 版本规划",
        "",
        "版本规划回答...",
        "",
        "### 版本路线图",
        "",
        "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
        "|------|------|---------|---------|---------------|-----------|",
    ]

    for version, status in roadmap_versions:
        lines.append(
            f"| {version} | {status} | 2026-05-01 | Test scope | - | Test deliverables |"
        )

    lines.append("")

    # Add version sections
    for version_label, tasks in version_tasks:
        lines.append(f"### {version_label}")
        lines.append(
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for tid, status, desc, depend in tasks:
            lines.append(
                f"| {tid} | {desc} | P1 | {depend} | 1.0.0 | 阿速 | — | Code Reviewer | TBD | {status} |"
            )
        lines.append("")

    content = "\n".join(lines)
    (governance_dir / "plan-tracker.md").write_text(content, encoding="utf-8")
    return content


def _pad_plan_tracker(governance_dir, min_bytes=82 * 1024):
    """Pad plan-tracker so first-migration size threshold is met."""
    path = governance_dir / "plan-tracker.md"
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) < min_bytes:
        content += "\n\n<!-- test padding -->\n" + ("x" * min_bytes)
        path.write_text(content, encoding="utf-8")
    return content


# ────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────

class TestVersionParsing(unittest.TestCase):
    """Test _parse_version_from_title with various title formats."""

    def test_standard_format_with_separator(self):
        """Titles with — or - separator should parse correctly (existing behavior)."""
        import archive
        v, desc = archive._parse_version_from_title("### v0.11.0 — Early fixes")
        self.assertEqual(v, "0.11.0")
        self.assertEqual(desc, "Early fixes")

        v, desc = archive._parse_version_from_title("## 0.24.0 - Bar baz qux")
        self.assertEqual(v, "0.24.0")
        self.assertEqual(desc, "Bar baz qux")

    def test_chinese_parenthesis_no_separator(self):
        """Version followed by Chinese parentheses without separator."""
        import archive
        v, desc = archive._parse_version_from_title("### 0.11.0（已发布）")
        self.assertEqual(v, "0.11.0")

        v, desc = archive._parse_version_from_title("### 0.12.0（已完成）")
        self.assertEqual(v, "0.12.0")

    def test_version_with_text_no_separator(self):
        """Version followed by description text without — or - separator."""
        import archive
        v, desc = archive._parse_version_from_title("### 0.11.0 交付清单（12/12 ✅）")
        self.assertEqual(v, "0.11.0")

        v, desc = archive._parse_version_from_title("### 1.0.0 依赖链")
        self.assertEqual(v, "1.0.0")

    def test_bare_version_no_description(self):
        """Just a version number with no description at all."""
        import archive
        v, desc = archive._parse_version_from_title("### 0.32.0")
        self.assertEqual(v, "0.32.0")

        v, desc = archive._parse_version_from_title("## 1.2.3")
        self.assertEqual(v, "1.2.3")

    def test_version_with_v_prefix_and_chinese_text(self):
        """v-prefix + version with Chinese text, no — separator."""
        import archive
        v, desc = archive._parse_version_from_title("### v0.15.0（已发布）")
        self.assertEqual(v, "0.15.0")

    def test_non_version_title_returns_none(self):
        """Titles without version numbers should return None, None."""
        import archive
        v, desc = archive._parse_version_from_title("### 交付清单")
        self.assertEqual(v, None)
        self.assertEqual(desc, None)

        v, desc = archive._parse_version_from_title("## 项目配置")
        self.assertEqual(v, None)
        self.assertEqual(desc, None)

    def test_find_version_sections_with_varied_formats(self):
        """_find_version_sections should detect versions in mixed formats."""
        import archive
        content = """# 项目样例

## 项目配置

### 0.11.0（已发布）
| Task | Status |
| --- | --- |
| FIX-001 | 已完成 |

### 0.12.0 - With separator
| Task | Status |
| --- | --- |
| FIX-002 | 进行中 |

### 0.13.0
| Task | Status |
| --- | --- |
| FIX-003 | 已完成 |
"""
        sections, lines = archive._find_version_sections(content)
        versions_found = [s["version"] for s in sections]
        self.assertIn("0.11.0", versions_found)
        self.assertIn("0.12.0", versions_found)
        self.assertIn("0.13.0", versions_found)
        self.assertEqual(len(sections), 3)

    def test_parse_task_status_emoji(self):
        """F-03: _parse_task_status should strip leading/trailing emoji
        but preserve all text characters (CJK, Latin, etc)."""
        import archive

        def _make_row(status_text):
            return f"| FIX-001 | desc | P1 | - | 1.0.0 | 阿速 | - | Code Reviewer | TBD | {status_text} |"

        # Leading emoji + CJK
        self.assertEqual(archive._parse_task_status(_make_row("✅ 已完成")), "已完成")
        # Leading emoji + CJK (blocked)
        self.assertEqual(archive._parse_task_status(_make_row("🚧 阻塞中")), "阻塞中")
        # Leading emoji + CJK (pending)
        self.assertEqual(archive._parse_task_status(_make_row("⏳ 待开始")), "待开始")
        # No emoji — CJK only
        self.assertEqual(archive._parse_task_status(_make_row("进行中（no emoji）")), "进行中（no emoji）")
        # ASCII status — must NOT be stripped
        self.assertEqual(archive._parse_task_status(_make_row("Done")), "Done")
        # Trailing emoji
        self.assertEqual(archive._parse_task_status(_make_row("Completed ✅")), "Completed")

    def test_section_boundary_non_version_heading(self):
        """F-04: version section should close at non-version ### heading."""
        import archive
        content = """# 项目样例

## 项目配置

### 0.11.0（已发布）
| Task | Status |
| --- | --- |
| FIX-001 | ✅ 已完成 |

### 优先级一览

Some free text outside any version section.

### 0.12.0 - With separator
| Task | Status |
| --- | --- |
| FIX-002 | 进行中 |
"""
        sections, lines = archive._find_version_sections(content)
        versions_found = [s["version"] for s in sections]
        self.assertIn("0.11.0", versions_found)
        self.assertIn("0.12.0", versions_found)
        self.assertEqual(len(sections), 2)

        # The v0.11.0 section should end before the non-version heading
        v011 = next(s for s in sections if s["version"] == "0.11.0")
        v012 = next(s for s in sections if s["version"] == "0.12.0")
        # v0.11.0 end_line should be before v0.12.0 starts
        self.assertLess(v011["end_line"], v012["start_line"])
        # v0.11.0 should NOT contain lines from after the non-version heading
        for line_idx, _, _ in v011["task_lines"]:
            self.assertIn(line_idx, range(v011["start_line"], v011["end_line"] + 1))


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

    def test_checklist_format_parsing_completed_tasks(self):
        """Checklist-format tasks with [x] should be detected as completed."""
        versions = [
            ("v0.24.0 — Checklist version", [
                ("SYSGAP-021", True, "project_goal 字段存储"),
                ("SYSGAP-022", True, "Checklist 增强"),
                ("SYSGAP-023", True, "Check 16 目标一致性检查"),
                ("SYSGAP-024", False, "Check 17 用户影响检查"),
            ]),
        ]
        _make_plan_tracker_checklist(self.gov_dir, versions)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.24.0", "0.24.0", dry_run=False)

        self.assertTrue(result["success"])
        # [x] items: SYSGAP-021,022,023 → 3 completed
        # [ ] items: SYSGAP-024 → NOT archived
        self.assertEqual(result["tasks_archived"], 3)
        self.assertEqual(result["tasks_remaining"], 1)

    def test_checklist_format_all_incomplete(self):
        """Checklist-format tasks with [ ] only should archive nothing."""
        versions = [
            ("v0.25.0 — WIP version", [
                ("SYSGAP-030", False, "未完成的任务 A"),
                ("SYSGAP-031", False, "未完成的任务 B"),
            ]),
        ]
        _make_plan_tracker_checklist(self.gov_dir, versions)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.25.0", "0.25.0", dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 0)
        self.assertEqual(result["tasks_remaining"], 2)

    def test_checklist_format_dry_run(self):
        """Checklist-format dry-run should report but not modify files."""
        versions = [
            ("v0.23.0 — Dry run version", [
                ("SYSGAP-015", True, "方案 4A: 测试定义"),
                ("SYSGAP-016", True, "方案 4B: 单元测试"),
            ]),
        ]
        _make_plan_tracker_checklist(self.gov_dir, versions)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.23.0", "0.23.0", dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 2)

        # No archive files should be created in dry-run mode
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(task_files), 0)

    def test_checklist_format_mixed_sections_table_and_checklist(self):
        """Sections with both table and checklist tasks should detect both."""
        # Create a plan-tracker with table tasks in one version and
        # checklist tasks in another, to verify they coexist.
        versions_table = [
            ("v0.11.0 — Table version", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions_table)

        # Now append checklist-format section to the same file
        pt_path = self.gov_dir / "plan-tracker.md"
        existing = pt_path.read_text(encoding="utf-8")
        checklist_section = """
### v0.23.0 — Checklist version

**交付清单**:
- [x] **SYSGAP-015** (方案 4A): 本项目测试类型对应定义
- [x] **SYSGAP-016** (方案 4B): verify 单元测试
- [ ] **SYSGAP-017** (方案 4C): e2e 测试项目
"""
        pt_path.write_text(existing + checklist_section, encoding="utf-8")

        import archive

        with patch.object(archive, 'ROOT', self.root):
            # Archive v0.11.0-v0.11.0 (table only)
            result_table = archive.migrate_by_version("0.11.0", "0.11.0", dry_run=False)
            self.assertEqual(result_table["tasks_archived"], 2)

            # Archive v0.23.0-v0.23.0 (checklist only)
            result_ck = archive.migrate_by_version("0.23.0", "0.23.0", dry_run=True)
            self.assertEqual(result_ck["tasks_archived"], 2)  # 2 completed [x], 1 [ ] skipped


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

    def test_rollback_groups_task_and_evidence_when_evidence_file_is_newer(self):
        """Rollback should undo same-name task/evidence archives as one migration."""
        versions = [
            ("v0.10.0 — Old release", [
                ("FIX-001", "已完成", "Fix old bug", "—"),
            ]),
            ("v0.11.0 — Current", [
                ("FIX-002", "进行中", "Keep hot", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)
        _make_evidence_log(self.gov_dir, [
            ("EVD-001", "FIX-001", "Archived evidence"),
            ("EVD-002", "FIX-002", "Hot evidence"),
        ])

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version(
                "0.10.0", "0.10.0", dry_run=False, migrate_evidence=True
            )
            archive.build_index()

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 1)
        self.assertEqual(result["evidence_archived"], 1)

        task_file = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        evidence_file = self.archive_dir / "evidence" / "v0.10.0~v0.10.0.md"
        self.assertTrue(task_file.exists())
        self.assertTrue(evidence_file.exists())

        pt_after_migrate = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        ev_after_migrate = (self.gov_dir / "evidence-log.md").read_text(encoding="utf-8")
        self.assertNotIn("| FIX-001 |", pt_after_migrate)
        self.assertNotIn("| EVD-001 |", ev_after_migrate)
        self.assertIn("| EVD-002 |", ev_after_migrate)

        # Force the evidence archive to be the newest file.  The rollback must
        # still find and process the same-name task archive.
        newer = task_file.stat().st_mtime + 10
        os.utime(evidence_file, (newer, newer))

        with patch.object(archive, 'ROOT', self.root):
            rollback = archive.rollback_last_migration()

        self.assertTrue(rollback["success"])
        self.assertEqual(
            set(rollback["rolled_back_files"]),
            {
                "archive/tasks/v0.10.0~v0.10.0.md",
                "archive/evidence/v0.10.0~v0.10.0.md",
            },
        )
        self.assertFalse(task_file.exists())
        self.assertFalse(evidence_file.exists())

        pt_after_rollback = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        ev_after_rollback = (self.gov_dir / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("| FIX-001 |", pt_after_rollback)
        self.assertIn("| EVD-001 |", ev_after_rollback)
        self.assertIn("| EVD-002 |", ev_after_rollback)

        index_content = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertNotIn("v0.10.0~v0.10.0.md", index_content)

    def test_rollback_supports_evidence_only_archive_file(self):
        """Backward compatibility: evidence-only archives can still rollback."""
        _make_plan_tracker(self.gov_dir, [])
        _make_evidence_log(self.gov_dir, [
            ("EVD-002", "FIX-002", "Hot evidence"),
        ])
        evidence_file = self.archive_dir / "evidence" / "v0.10.0~v0.10.0.md"
        evidence_file.write_text(
            "# 归档 Evidence 表 — v0.10.0 ~ v0.10.0\n\n"
            "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| EVD-001 | FIX-001 | Archived evidence | 2026-05-01 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |\n",
            encoding="utf-8",
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            archive.build_index()
            rollback = archive.rollback_last_migration()

        self.assertTrue(rollback["success"])
        self.assertEqual(
            rollback["rolled_back_files"],
            ["archive/evidence/v0.10.0~v0.10.0.md"],
        )
        self.assertFalse(evidence_file.exists())
        ev_after_rollback = (self.gov_dir / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("| EVD-001 |", ev_after_rollback)
        self.assertIn("| EVD-002 |", ev_after_rollback)

    def test_incremental_archive_uses_independent_file_and_rollback_keeps_history(self):
        """Repeated version-range archive should rollback only the increment file."""
        versions = [
            ("v0.10.0 — Old release", [
                ("FIX-001", "已完成", "Original task", "—"),
            ]),
        ]
        _make_plan_tracker(self.gov_dir, versions)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            first = archive.migrate_by_version("0.10.0", "0.10.0", dry_run=False)
            archive.build_index()

        self.assertTrue(first["success"])
        base_file = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        self.assertTrue(base_file.exists())

        # Simulate a later completed task becoming eligible in the same
        # version range after the base archive already exists.
        pt_path = self.gov_dir / "plan-tracker.md"
        pt_content = pt_path.read_text(encoding="utf-8")
        pt_content = pt_content.replace(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-002 | Incremental task | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |",
        )
        pt_path.write_text(pt_content, encoding="utf-8")

        with patch.object(archive, 'ROOT', self.root):
            second = archive.migrate_by_version("0.10.0", "0.10.0", dry_run=False)
            archive.build_index()

        self.assertTrue(second["success"])
        self.assertEqual(second["tasks_archived"], 1)
        inc_files = sorted((self.archive_dir / "tasks").glob("v0.10.0~v0.10.0-incremental-*.md"))
        self.assertEqual(len(inc_files), 1)
        self.assertTrue(base_file.exists())

        with patch.object(archive, 'ROOT', self.root):
            rollback = archive.rollback_last_migration()

        self.assertTrue(rollback["success"])
        self.assertTrue(base_file.exists(), "Rollback must keep historical base archive")
        self.assertFalse(inc_files[0].exists(), "Rollback should remove only the increment file")

        pt_after = pt_path.read_text(encoding="utf-8")
        self.assertNotIn("| FIX-001 |", pt_after, "Rollback must not restore old archived history")
        self.assertIn("| FIX-002 |", pt_after, "Rollback should restore only incremental task")
        self.assertRegex(
            pt_after,
            r"### v0\.10\.0 .* \[已归档\]",
            "v0.10.0 title must stay marked while base archive still covers it",
        )

    def test_archive_version_range_parser_supports_base_and_incremental_names(self):
        """Filename parser should recognize base and incremental archive ranges."""
        import archive

        self.assertEqual(
            archive._parse_archive_version_range("v0.10.0~v0.10.0.md"),
            ("0.10.0", "0.10.0"),
        )
        self.assertEqual(
            archive._parse_archive_version_range(
                "v0.10.0~v0.12.0-incremental-20260513-2.md"
            ),
            ("0.10.0", "0.12.0"),
        )
        self.assertIsNone(
            archive._parse_archive_version_range("legacy-v0.10.0.md")
        )


class TestArchiveMigrateAuto(unittest.TestCase):
    """Test migrate_auto function (--auto mode)."""

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

    def test_auto_normal_migration(self):
        """--auto should archive oldest published versions, keeping latest."""
        # Override: need 3 published versions for a meaningful test
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
            ("0.13.0", "进行中"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Early fixes", [
                ("FIX-002", "已完成", "Fix bug 2", "FIX-001"),
                ("FIX-003", "已完成", "Fix bug 3", "—"),
            ]),
            ("v0.12.0 — Latest published", [
                ("FIX-004", "已完成", "Fix bug 4", "—"),
                ("FIX-005", "进行中", "Fix bug 5", "—"),
            ]),
            ("v0.13.0 — Current", [
                ("FIX-006", "进行中", "Fix bug 6", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        _make_evidence_log(self.gov_dir, [
            ("EVD-001", "FIX-001", "Fixed bug 1"),
            ("EVD-002", "FIX-002", "Fixed bug 2"),
            ("EVD-003", "FIX-003", "Fixed bug 3"),
            ("EVD-004", "FIX-004", "Fixed bug 4"),
        ])
        _pad_plan_tracker(self.gov_dir)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        # Published: 0.10.0, 0.11.0, 0.12.0 → archive 0.10.0 ~ 0.11.0
        self.assertIn("0.10.0", result["versions_archived"])
        self.assertIn("0.11.0", result["versions_archived"])
        self.assertNotIn("0.12.0", result["versions_archived"])  # Latest kept
        self.assertGreaterEqual(result["tasks_archived"], 3)  # FIX-001,002,003
        self.assertTrue(result["verify_pass"])

        # Check archive file exists
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertGreaterEqual(len(task_files), 1)

        # Check index exists
        self.assertTrue((self.archive_dir / "index.md").exists())

    def test_auto_skip_few_published(self):
        """< 2 published versions → skip with skipped=True."""
        roadmap = [
            ("0.11.0", "已发布"),
            ("0.12.0", "进行中"),
        ]
        tasks = [
            ("v0.11.0 — First", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result.get("skipped", False))
        self.assertIn("不足", result.get("reason", ""))

    def test_auto_no_version_roadmap_table(self):
        """Fallback: no roadmap table → parse version section titles."""
        # Create plan-tracker without roadmap table but with version sections
        versions = [
            ("v0.11.0 — Old release", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.12.0 — Newer release", [
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
            ("0.13.0 — Current WIP", [
                ("FIX-003", "进行中", "Fix bug 3", "—"),
            ]),
        ]
        # Use _make_plan_tracker (no roadmap) and DO NOT add roadmap section
        _make_plan_tracker(self.gov_dir, versions)
        # No roadmap dates are available, so use an existing index to trigger
        # continuous release-forced archive without relying on first threshold.
        (self.archive_dir / "index.md").write_text("# 归档索引\n", encoding="utf-8")

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        # When parsing from titles, all found versions are treated as "已发布"
        # So it would see 0.11.0, 0.12.0, 0.13.0 as published
        # Archive range: 0.11.0 ~ 0.12.0
        self.assertTrue(result.get("success"))
        # Should not be skipped
        self.assertFalse(result.get("skipped", False))

    def test_auto_no_completed_tasks(self):
        """Archive range has no completed tasks → skipped."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "进行中", "In-progress task", "—"),
            ]),
            ("v0.11.0 — Early fixes", [
                ("FIX-002", "进行中", "In-progress task", "—"),
            ]),
            ("v0.12.0 — Latest", [
                ("FIX-003", "进行中", "In-progress task", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        _pad_plan_tracker(self.gov_dir)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result.get("skipped", False))
        self.assertIn("无可归档数据", result.get("reason", ""))

    def test_auto_existing_index_no_new_data_idempotent_skip(self):
        """If index exists and no hot archivable data exists → skip without changes."""
        # Create pre-existing index + archive file for FIX-001.
        task_archive = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        task_archive.write_text(
            "# 归档 Task 表 — v0.10.0 ~ v0.10.0\n\n"
            "### v0.10.0 — Initial\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "index.md").write_text(
            "# 归档索引\n\n## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-001 | 已完成 | 0.10.0 | archive/tasks/v0.10.0~v0.10.0.md |\n",
            encoding="utf-8",
        )

        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Latest published", [
                ("FIX-002", "进行中", "Fix bug 2", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        before = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result.get("skipped", False))
        self.assertIn("无可归档数据", result.get("reason", ""))
        self.assertTrue(result["success"])
        after = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_auto_dry_run(self):
        """--auto + dry-run → preview but no files modified."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Early fixes", [
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
            ("v0.12.0 — Latest", [
                ("FIX-003", "进行中", "Fix bug 3", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        _pad_plan_tracker(self.gov_dir)

        import archive

        # Record original content
        pt_before = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=True)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        self.assertGreaterEqual(result.get("tasks_archived", 0), 1)

        # Plan-tracker should be UNMODIFIED
        pt_after = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertEqual(pt_before, pt_after)

        # No archive files should be created
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(task_files), 0)

        # No index should be created
        self.assertFalse((self.archive_dir / "index.md").exists())

    def test_auto_output_has_required_fields(self):
        """--auto result dict must contain all required summary fields."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Early fixes", [
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
            ("v0.12.0 — Latest", [
                ("FIX-003", "进行中", "Fix bug 3", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        _pad_plan_tracker(self.gov_dir)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        # Required fields must exist
        for key in [
            "success", "skipped", "reason", "versions_archived",
            "versions_range", "tasks_archived", "evidence_archived",
            "plan_tracker_before", "plan_tracker_after",
            "evidence_log_before", "evidence_log_after",
            "archive_files_created", "verify_pass",
        ]:
            self.assertIn(key, result, f"Required key '{key}' missing from result")

        # For successful migration, verify_pass should be True
        self.assertTrue(result["verify_pass"])

    def test_auto_with_2_published_archives_oldest_only(self):
        """With exactly 2 published versions, archive only the oldest."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "进行中"),
        ]
        tasks = [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Latest published", [
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        _make_evidence_log(self.gov_dir, [
            ("EVD-001", "FIX-001", "Fixed bug 1"),
        ])
        _pad_plan_tracker(self.gov_dir)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        # published: [0.10.0, 0.11.0] → archive 0.10.0 only
        self.assertEqual(result["versions_archived"], ["0.10.0"])
        self.assertEqual(result["tasks_archived"], 1)

    def test_auto_existing_index_new_published_version_incremental_archive(self):
        """Existing index must not block newly eligible published-version data."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Already archived", [
                ("FIX-001", "已完成", "Fix old bug", "—"),
            ]),
            ("v0.11.0 — Newly old", [
                ("FIX-002", "已完成", "Fix new old bug", "—"),
            ]),
            ("v0.12.0 — Latest published", [
                ("FIX-003", "已完成", "Keep latest hot", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        existing = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        existing.write_text(
            "# 归档 Task 表 — v0.10.0 ~ v0.10.0\n\n"
            "### v0.10.0 — Already archived\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | Fix old bug | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "index.md").write_text(
            "# 归档索引\n\n## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-001 | 已完成 | 0.10.0 | archive/tasks/v0.10.0~v0.10.0.md |\n",
            encoding="utf-8",
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=False)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        self.assertIn("release_forced", result["triggers"])
        self.assertEqual(result["tasks_archived"], 1)

        pt_content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertNotIn("| FIX-002 |", pt_content)
        self.assertIn("| FIX-003 |", pt_content)
        index_content = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("FIX-002", index_content)

    def test_auto_task_incremental_threshold_dry_run_reports_archive_needed(self):
        """A large batch of hot completed tasks should trigger dry-run reporting."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
        ]
        old_tasks = [
            (f"FIX-{i:03d}", "已完成", f"Fix bug {i}", "—")
            for i in range(1, 22)
        ]
        tasks = [
            ("v0.10.0 — Old release", old_tasks),
            ("v0.11.0 — Latest published", [
                ("FIX-999", "进行中", "Keep hot", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=True)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        self.assertIn("task_incremental", result["triggers"])
        self.assertEqual(result["tasks_archived"], 21)
        self.assertFalse((self.archive_dir / "index.md").exists())

    def test_auto_90_day_fallback_reports_archive_needed(self):
        """A stale archive cadence with hot historical data should trigger fallback."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Old release", [
                ("FIX-001", "已完成", "Fix old bug", "—"),
            ]),
            ("v0.11.0 — Another old release", [
                ("FIX-002", "已完成", "Fix another bug", "—"),
            ]),
            ("v0.12.0 — Latest", [
                ("FIX-003", "进行中", "Keep hot", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)
        index = self.archive_dir / "index.md"
        index.write_text("# 归档索引\n", encoding="utf-8")
        stale = 0
        import time
        stale = time.time() - (91 * 24 * 60 * 60)
        os.utime(index, (stale, stale))

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_auto(dry_run=True)

        self.assertTrue(result["success"])
        self.assertIn("fallback_90d", result["triggers"])
        self.assertGreaterEqual(result["tasks_archived"], 2)

    def test_analyze_candidates_no_archive_dir_is_read_only(self):
        """Candidate analysis must not create archive/ in unarchived projects."""
        import shutil
        shutil.rmtree(str(self.archive_dir))

        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
        ]
        tasks = [
            ("v0.10.0 — Old release", [
                ("FIX-001", "已完成", "Fix old bug", "—"),
            ]),
            ("v0.11.0 — Latest", [
                ("FIX-002", "进行中", "Keep hot", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov_dir, roadmap, tasks)

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.analyze_auto_archive_candidates()

        self.assertTrue(result["success"])
        self.assertFalse((self.gov_dir / "archive").exists())


def _make_plan_tracker_with_sample_table(governance_dir, sample_tasks, version_tasks=None,
                                           roadmap_versions=None):
    """Create a plan-tracker.md with a 样例跟踪表 section + optional version sections.

    sample_tasks: list of (task_id, status, description)
        e.g., [("DESIGN-002", "已终止", "补齐 Claude 半可执行入口"), ...]
        Status is placed in column 10 (matching _parse_task_status convention).
    version_tasks: optional list of (version_label, tasks_list) for version sections
    roadmap_versions: optional list of (version, status) for version roadmap table
    """
    lines = [
        "# 当前项目样例",
        "",
        "## 项目配置",
        "- **项目目标**: Test project with sample table",
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
    ]

    # Add version roadmap if provided
    if roadmap_versions:
        lines.extend([
            "## 版本规划",
            "",
            "版本规划回答...",
            "",
            "### 版本路线图",
            "",
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
            "|------|------|---------|---------|---------------|-----------|",
        ])
        for version, status in roadmap_versions:
            lines.append(
                f"| {version} | {status} | 2026-05-01 | Test | - | Test |"
            )
        lines.append("")

    # Add version sections if provided
    if version_tasks:
        for version_label, tasks in version_tasks:
            lines.append(f"### {version_label}")
            lines.append(
                "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |"
            )
            lines.append(
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
            )
            for tid, status, desc, depend in tasks:
                lines.append(
                    f"| {tid} | {desc} | P1 | {depend} | 1.0.0 | 阿速 | — | Code Reviewer | TBD | {status} |"
                )
            lines.append("")

    # Add 样例跟踪表 section (20-column format matching real plan-tracker)
    lines.append("## 样例跟踪表")
    lines.append("")
    lines.append("| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for tid, status, desc in sample_tasks:
        lines.append(
            f"| {tid} | 维护 | {desc} | Test goal | Test input | Test output "
            f"| 项目负责人 | Claude | 项目负责人 | {status} | P1 "
            f"| 2026-04-01 | 2026-04-15 | 2026-04-10 | G8 "
            f"| Test criteria | EVD-999 | — | — | Test note |"
        )
    lines.append("")
    lines.append("## 下一个章节")
    lines.append("")
    lines.append("Content after sample table.")

    content = "\n".join(lines)
    (governance_dir / "plan-tracker.md").write_text(content, encoding="utf-8")
    return content


class TestSampleTableArchive(unittest.TestCase):
    """Test sample tracking table (样例跟踪表) integration with archive."""

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

    def test_sample_table_section_detected(self):
        """_find_version_sections should create a synthetic section for 样例跟踪表."""
        sample_tasks = [
            ("DESIGN-002", "已终止", "补齐 Claude 半可执行入口"),
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
            ("MAINT-002", "已终止", "补更多大厂实践映射"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.2.0", "已发布"),
            ("0.3.0", "进行中"),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
            sections, lines = archive._find_version_sections(content)

        sample_sections = [s for s in sections if s.get("sample_table", False)]
        self.assertEqual(len(sample_sections), 1)
        sample = sample_sections[0]
        self.assertTrue(sample["sample_table"])
        self.assertEqual(sample["version"], "0.1.0")  # Earliest published
        self.assertEqual(len(sample["task_lines"]), 3)
        task_ids = [tid for _, _, tid in sample["task_lines"]]
        self.assertIn("DESIGN-002", task_ids)
        self.assertIn("AUDIT-003", task_ids)
        self.assertIn("MAINT-002", task_ids)

    def test_sample_table_completed_archived(self):
        """Completed tasks in 样例跟踪表 should be archived."""
        sample_tasks = [
            ("DESIGN-002", "已终止", "补齐 Claude 半可执行入口"),
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
            ("AUDIT-008", "已完成", "P2: README 承诺措辞修正"),
            ("MAINT-002", "已终止", "补更多大厂实践映射"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.2.0", "已发布"),
            ("0.3.0", "进行中"),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.1.0", "0.2.0", dry_run=False)

        self.assertTrue(result["success"])
        # AUDIT-003 and AUDIT-008 are "已完成" → 2 archived
        # DESIGN-002 and MAINT-002 are "已终止" → NOT archived
        self.assertEqual(result["tasks_archived"], 2)

        # Check archive file content
        archive_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(archive_files), 1)
        archive_content = archive_files[0].read_text(encoding="utf-8")
        self.assertIn("AUDIT-003", archive_content)
        self.assertIn("AUDIT-008", archive_content)
        self.assertNotIn("DESIGN-002", archive_content)

    def test_sample_table_rows_not_deleted_from_hot_file(self):
        """Sample table rows must NOT be deleted from plan-tracker after archive."""
        sample_tasks = [
            ("DESIGN-002", "已终止", "补齐 Claude 半可执行入口"),
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
            ("MAINT-002", "已终止", "补更多大厂实践映射"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.2.0", "已发布"),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.1.0", "0.2.0", dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 1)  # Only AUDIT-003

        # All sample table rows should still be in plan-tracker
        pt_content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertIn("DESIGN-002", pt_content)
        self.assertIn("AUDIT-003", pt_content)
        self.assertIn("MAINT-002", pt_content)

    def test_sample_table_with_version_sections(self):
        """Sample table tasks archived alongside regular version section tasks."""
        sample_tasks = [
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
            ("AUDIT-008", "已完成", "P2: README 承诺措辞修正"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.2.0", "已发布"),
            ("0.3.0", "已发布"),
        ]
        version_tasks = [
            ("v0.2.0 — Version tasks", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
            ("v0.3.0 — Current", [
                ("FIX-003", "进行中", "Fix bug 3", "—"),
            ]),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            version_tasks=version_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.1.0", "0.2.0", dry_run=False)

        self.assertTrue(result["success"])
        # Sample table (version=0.1.0): 2 completed → archived
        # v0.2.0 section: 2 completed → archived
        # v0.3.0 section: out of range, FIX-003 not completed
        # Total: 4 archived
        self.assertEqual(result["tasks_archived"], 4)

        # v0.2.0 task rows should be REMOVED from hot file
        pt_content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertNotIn("| FIX-001 |", pt_content)
        self.assertNotIn("| FIX-002 |", pt_content)

        # Sample table rows should still be PRESENT
        self.assertIn("AUDIT-003", pt_content)
        self.assertIn("AUDIT-008", pt_content)

    def test_sample_table_out_of_archive_range(self):
        """Sample table tasks outside archive range should not be archived."""
        sample_tasks = [
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.5.0", "已发布"),
            ("0.6.0", "已发布"),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            # Archive range 0.5.0 ~ 0.5.0 — sample table version is 0.1.0, OUT of range
            result = archive.migrate_by_version("0.5.0", "0.5.0", dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 0)

    def test_sample_table_no_roadmap_fallback_version(self):
        """When no roadmap exists, sample table uses fallback version '0.1.0'."""
        sample_tasks = [
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
        ]
        # No roadmap_versions provided — fallback to '0.1.0'
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=None,
        )

        import archive

        with patch.object(archive, 'ROOT', self.root):
            content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
            sections, lines = archive._find_version_sections(content)

        sample_sections = [s for s in sections if s.get("sample_table", False)]
        self.assertEqual(len(sample_sections), 1)
        self.assertEqual(sample_sections[0]["version"], "0.1.0")

    def test_sample_table_dry_run(self):
        """Dry-run mode should report sample table tasks without modifying files."""
        sample_tasks = [
            ("AUDIT-003", "已完成", "P0: 外部项目验证"),
            ("AUDIT-008", "已完成", "P2: README 承诺措辞修正"),
        ]
        roadmap = [
            ("0.1.0", "已发布"),
            ("0.2.0", "已发布"),
        ]
        _make_plan_tracker_with_sample_table(
            self.gov_dir, sample_tasks,
            roadmap_versions=roadmap,
        )

        import archive

        pt_before = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")

        with patch.object(archive, 'ROOT', self.root):
            result = archive.migrate_by_version("0.1.0", "0.2.0", dry_run=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 2)

        # Plan-tracker should be UNMODIFIED
        pt_after = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertEqual(pt_before, pt_after)

        # No archive files should be created
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(task_files), 0)


    def test_sample_table_sub_chapter_scanning(self):
        """样例跟踪表 should scan across ### sub-chapters to capture all tasks."""
        import archive

        pt_content = """# 项目样例

## 项目配置

## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-001 | 维护 | First task | Goal | In | Out | Dev | Peer | Lead | 已完成 | P1 | 2026-01 | 2026-02 | 2026-03 | G1 | Criteria | EVD-1 | — | — | Note |
| TASK-002 | 维护 | Second task | Goal | In | Out | Dev | Peer | Lead | 已完成 | P1 | 2026-01 | 2026-02 | 2026-03 | G1 | Criteria | EVD-2 | — | — | Note |

Text between tables — should be skipped.

### 主线 A：产品内容层

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-003 | 维护 | Sub-chapter task | Goal | In | Out | Dev | Peer | Lead | 已完成 | P1 | 2026-01 | 2026-02 | 2026-03 | G1 | Criteria | EVD-3 | — | — | Note |

### 主线 B：交付架构层

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-004 | 维护 | Fourth task | Goal | In | Out | Dev | Peer | Lead | 进行中 | P1 | 2026-01 | 2026-02 | 2026-03 | G1 | Criteria | EVD-4 | — | — | Note |
| TASK-005 | 维护 | Fifth task | Goal | In | Out | Dev | Peer | Lead | 已完成 | P1 | 2026-01 | 2026-02 | 2026-03 | G1 | Criteria | EVD-5 | — | — | Note |

## 下一个章节

Content after sample table.
"""
        (self.gov_dir / "plan-tracker.md").write_text(pt_content, encoding="utf-8")

        with patch.object(archive, 'ROOT', self.root):
            content = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
            sections, lines = archive._find_version_sections(content)

        sample_sections = [s for s in sections if s.get("sample_table", False)]
        self.assertEqual(len(sample_sections), 1, "Should have exactly 1 sample_table section")
        sample = sample_sections[0]
        self.assertTrue(sample["sample_table"])
        self.assertEqual(len(sample["task_lines"]), 5, "Should capture all 5 tasks across sub-chapters")
        task_ids = [tid for _, _, tid in sample["task_lines"]]
        self.assertIn("TASK-001", task_ids)
        self.assertIn("TASK-002", task_ids)
        self.assertIn("TASK-003", task_ids)
        self.assertIn("TASK-004", task_ids)
        self.assertIn("TASK-005", task_ids)

        # Verify completed count
        completed = sum(1 for _, line, _ in sample["task_lines"]
                       if archive._parse_task_status(line) == "已完成")
        self.assertEqual(completed, 4, "TASK-001,002,003,005 completed; TASK-004 in progress")


if __name__ == "__main__":
    unittest.main()
