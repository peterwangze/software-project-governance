"""Unit tests for archive.py — SYSGAP-030.

Tests cover:
  - migrate_by_version: correct extraction and archival of version-range tasks
  - build_index: correct index generation from archive files
  - rebuild_index: index-loss/corruption recovery — rebuild + integrity
    verification (FIX-384 B-7a), idempotent on an intact index, damage-tolerant
  - verify_archive_integrity: detects inconsistencies
  - backward compatibility: no archive/ directory = no-op
  - Dry-Run mode: does not modify files

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_archive.py -v
or:
    python -m unittest skills/software-project-governance.infra.tests.test_archive -v
"""

import contextlib
import io
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


def _write_release_manifest(root, version, lifecycle="released",
                            withdrawn=False, withdrawn_effective=False,
                            corrupt=False, missing_version=False):
    """Write a release-ledger manifest fixture under the plugin root.

    Mirrors the declarative release ledger schema (release/ledger.py):
    top-level lifecycle_state/version plus effective_state; ``withdrawn``
    may appear at top level or inside effective_state (FIX-243/DEC-140).
    """
    releases = (
        root / "skills" / "software-project-governance" / "core" / "releases"
    )
    releases.mkdir(parents=True, exist_ok=True)
    path = releases / f"{version}.json"
    if corrupt:
        path.write_text("{ not valid json", encoding="utf-8")
        return path
    manifest = {
        "artifacts": {},
        "effective_state": {
            "amendments": [],
            "lifecycle_state": lifecycle,
            "withdrawn": withdrawn_effective,
        },
        "events": [],
        "lifecycle_state": lifecycle,
        "provenance": "native",
        "schema_version": 1,
        "version": version,
    }
    if withdrawn:
        manifest["withdrawn"] = True
    if missing_version:
        del manifest["version"]
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


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
        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.migrate_by_version("0.13.0", "0.13.0", dry_run=False)

        self.assertTrue(result["success"])
        # FIX-006 is "进行中", should NOT be archived
        # FIX-007 is "已完成", should be archived
        self.assertEqual(result["tasks_archived"], 1)

    def test_migrate_no_matching_versions(self):
        """Migrating a non-existent version range should return 0 archived."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.migrate_by_version("0.11.0", "0.12.0", dry_run=False)

        # Should still succeed - archive dir gets auto-created
        self.assertTrue(result["success"])

    def test_migrate_evidence_alongside_tasks(self):
        """Migrating tasks should also archive associated evidence."""
        self._create_test_data()
        import archive

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            # Archive v0.11.0-v0.11.0 (table only)
            result_table = archive.migrate_by_version("0.11.0", "0.11.0", dry_run=False)
            self.assertEqual(result_table["tasks_archived"], 2)

            # Archive v0.23.0-v0.23.0 (checklist only)
            result_ck = archive.migrate_by_version("0.23.0", "0.23.0", dry_run=True)
            self.assertEqual(result_ck["tasks_archived"], 2)  # 2 completed [x], 1 [ ] skipped

    def test_migrate_priority_table_tasks_writes_to_archive_body(self):
        """FIX-172 regression guard: priority-table tasks MUST be written to the
        archive file body, even when there is NO matching `### <version>` section.

        Root cause of the data-loss bug (FIX-158 regression): the body-write loop
        gated each version group on `if section:` (a matching version section
        existed). Tasks found via `_parse_priority_table_tasks` carry a target
        version (e.g. '0.61.0') that does NOT match any version-section header in
        the real plan-tracker (which only has `### 1.0.0 依赖链`). So `section`
        was None for every priority-table task, the task lines were NEVER appended
        to `archive_lines`, and the deletion step still removed them from
        plan-tracker -> the archive file body was empty -> DATA LOSS.

        This test mirrors the real plan-tracker layout: archivable tasks live ONLY
        in `### 优先级一览` (7-col table) with target_version='0.61.0', and the
        only version section is `### 1.0.0 依赖链` (zero overlap). On the buggy
        code the archive file body is empty (only a header) -> assertion fails.
        After FIX-172 the body is non-empty and contains the task IDs.
        """
        import archive

        # Build a plan-tracker that mirrors the real one: tasks ONLY in the
        # priority table, with a target version (0.61.0) that has NO matching
        # `### 0.61.0` version section. The only version section is 1.0.0.
        lines = [
            "# 当前项目样例",
            "",
            "## 项目配置",
            "- **工作流版本**: 0.61.0",
            "",
            "## 当前活跃事项",
            "",
            "### 优先级一览",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-172 | Priority-table task A | — | 0.61.0 | TBD | ✅ 已完成 |",
            "| **P1** | FIX-173 | Priority-table task B | FIX-172 | 0.61.0 | TBD | ✅ 已完成 |",
            "| **P0** | FIX-199 | Out-of-range task | — | 0.99.0 | TBD | ✅ 已完成 |",
            "",
            "### 1.0.0 依赖链",
            "",
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| REL-100 | Future release | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | ⏳ 进行中 |",
            "",
        ]
        (self.gov_dir / "plan-tracker.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
        # An evidence-log is required so the migration's evidence step does not
        # choke on a missing file; no entries reference our tasks.
        _make_evidence_log(self.gov_dir, [])

        with patch.object(archive, "ROOT", self.root), patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.migrate_by_version(
                "0.1.0", "0.61.0", dry_run=False
            )

        # 1. tasks_archived >= 1 (both FIX-172 and FIX-173 are in range & done)
        self.assertTrue(result["success"], f"migration failed: {result}")
        self.assertGreaterEqual(result["tasks_archived"], 1)
        # Specifically FIX-172 and FIX-173 should be archived; FIX-199 (0.99.0)
        # is out of range and REL-100 (1.0.0 / 进行中) is not archivable.
        self.assertEqual(result["tasks_archived"], 2)

        # 2. THE core assertion: the archive file body must be NON-EMPTY and
        #    contain the task IDs. On the buggy code the body is empty (header
        #    only) -> these assertions fail.
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(task_files), 1, "exactly one archive file expected")
        body = task_files[0].read_text(encoding="utf-8")
        self.assertIn("FIX-172", body, "priority-table task missing from archive body")
        self.assertIn("FIX-173", body, "priority-table task missing from archive body")
        self.assertNotIn("FIX-199", body, "out-of-range task leaked into archive")
        # Sanity: body is not just the header (must contain a task row line).
        self.assertIn("| FIX-172 |", body)

        # 3. The archived tasks must have been removed from plan-tracker.
        remaining = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertNotIn("FIX-172", remaining,
                         "archived task still present in plan-tracker")
        self.assertNotIn("FIX-173", remaining,
                         "archived task still present in plan-tracker")
        # Out-of-range / in-progress tasks must remain.
        self.assertIn("FIX-199", remaining)
        self.assertIn("REL-100", remaining)


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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.build_index()

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["task_entries"], 0)
        self.assertEqual(result["evidence_entries"], 0)

    def test_build_index_registers_unstructured_narrative_file(self):
        """FIX-176 regression: a task-archive file whose body is free narrative
        prose (no extractable task-table rows, filename matches narrative-* or
        recent-completed-*) must still be registered in the index under a
        dedicated 非结构化归档 section. Without the fix, build_index() drops the
        file entirely and verify_archive_integrity Check 2 then flags it as an
        orphan (FAIL-on-buggy)."""
        import archive

        # Structured task archive file (yields 1 task row).
        (self.archive_dir / "tasks" / "v0.1.0~v0.2.0.md").write_text(
            "# 归档\n\n### v0.1.0\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | d | P1 | — | 0.1.0 | o | r | rt | p | 已完成 |\n",
            encoding="utf-8",
        )
        # Non-structured narrative file (free prose, no task rows). Mirrors the
        # real archive/tasks/narrative-2026-04-30_2026-06-27.md header format.
        (self.archive_dir / "tasks" / "narrative-2026-04-30_2026-06-27.md").write_text(
            "# 归档叙述段 — 历史活跃事项（2026-04-30 ~ 2026-06-27）\n"
            "\n"
            "- **归档日期**: 2026-06-28（FIX-157）\n"
            "- **归档范围**: plan-tracker 段中已闭环历史事项叙述\n"
            "- **条目数**: 98 段\n"
            "\n"
            "**2026-06-26 某事项叙述**：自由文本，无 task 表格行。\n",
            encoding="utf-8",
        )

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.build_index()

        # Result reports the narrative registration.
        self.assertEqual(result["task_entries"], 1)
        self.assertEqual(result["narrative_entries"], 1)

        index_path = self.archive_dir / "index.md"
        content = index_path.read_text(encoding="utf-8")
        # New dedicated section exists.
        self.assertIn("## 非结构化归档", content)
        # The narrative file is referenced in the index.
        rel = "archive/tasks/narrative-2026-04-30_2026-06-27.md"
        self.assertIn(rel, content)
        # Date range extracted from filename appears in the description column.
        self.assertIn("2026-04-30~2026-06-27", content)
        # The structured task row is unchanged in the Task section.
        self.assertIn("FIX-001", content)

    def test_build_index_unstructured_recent_completed_without_table(self):
        """FIX-176: a recent-completed-* file with no task table (pure pointer
        file) is also registered as non-structured. (When it DOES contain a
        task table it is handled by the normal structured path, not here.)"""
        import archive

        (self.archive_dir / "tasks" / "recent-completed-2026-04-30_2026-06-27.md").write_text(
            "# 归档 Task 表 — 最近完成\n"
            "- **归档范围**: 提交窗口\n"
            "\n> 仅指针，无表格。\n",
            encoding="utf-8",
        )
        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.build_index()
        self.assertEqual(result["narrative_entries"], 1)
        content = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("archive/tasks/recent-completed-2026-04-30_2026-06-27.md", content)
        self.assertIn("## 非结构化归档", content)


class TestArchiveIndexRebuild(unittest.TestCase):
    """FIX-384 (B-7a): archive/index.md rebuild path — index loss/corruption
    recovery. The index is a pure DERIVATIVE of the archive files: rebuild
    restores the view, never creates data, never touches the archive files,
    and must reach integrity PASS even when the archive files themselves
    carry content-level damage (empty / unreadable / row-less)."""

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

    def _create_full_archive_files(self):
        """Structured archive files across all four categories."""
        (self.archive_dir / "tasks" / "v0.11.0~v0.12.0.md").write_text(
            "# 归档 Task 表 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "### v0.11.0 — Early fixes\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |\n"
            "| FIX-002 | Fix bug 2 | P1 | FIX-001 | 1.0.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "evidence" / "v0.11.0~v0.12.0.md").write_text(
            "# 归档 Evidence 记录 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| EVD-001 | FIX-001 | Fixed bug 1 | 2026-05-01 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |\n"
            "| EVD-002 | FIX-002 | Fixed bug 2 | 2026-05-02 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "decisions" / "decisions-v0.11.0-0.12.0.md").write_text(
            "# 归档 Decision 记录 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "## DEC-001: Use SQLite for storage\n\n"
            "- 归档版本: v0.11.0（关联 task 已归档）\n\n"
            "> 原始决策记录（完整字段）：\n"
            "> | DEC-001 | 2026-05-01 | 存储选型 | 背景 | 决策 | 备选 | 原因 | 影响 | 用户 | FIX-001 | 后续 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "risks" / "risks-v0.11.0-0.12.0.md").write_text(
            "# 归档 Risk 记录 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "| RISK-001 | Data loss during archive | 中 | 已关闭 |\n",
            encoding="utf-8",
        )

    def _snapshot_archive_state(self):
        """Return {rel_path: bytes} for every archive file (index excluded)."""
        state = {}
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            for f in sorted((self.archive_dir / sub).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                state[f"{sub}/{f.name}"] = f.read_bytes()
        return state

    # ── Acceptance chain: 索引丢失 → 重建 → integrity PASS ──

    def test_full_chain_index_missing_rebuild_verify_pass(self):
        """Acceptance chain: index missing → rebuild_index() → integrity PASS.
        Rebuild must not touch the archive files (pure derivative view)."""
        self._create_full_archive_files()
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            # Pre-state: verify FAILS because the index does not exist.
            pre = archive.verify_archive_integrity()
            self.assertFalse(pre["pass"])
            self.assertTrue(
                any("index.md 不存在" in i for i in pre["issues"]),
                f"expected the missing-index issue, got: {pre['issues']}",
            )

            before = self._snapshot_archive_state()
            result = archive.rebuild_index()

            self.assertTrue(
                result["verify_pass"],
                f"rebuild must reach integrity PASS: {result['verify_issues']}",
            )
            self.assertFalse(result["index_existed"])
            self.assertTrue(result["changed"])
            self.assertEqual(result["damaged_files"], [])
            self.assertGreaterEqual(result["task_entries"], 2)
            self.assertGreaterEqual(result["evidence_entries"], 2)
            self.assertGreaterEqual(result["decision_entries"], 1)
            self.assertGreaterEqual(result["risk_entries"], 1)
            # 重建不创造数据也不破坏归档：archive files byte-identical.
            self.assertEqual(
                self._snapshot_archive_state(), before,
                "rebuild must never modify the archive files",
            )
            # Every category's entries are reachable through the index.
            index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
            self.assertIn("FIX-001", index)
            self.assertIn("EVD-001", index)
            self.assertIn("DEC-001", index)
            self.assertIn("RISK-001", index)
            # Post-state: the standalone integrity check (check-archive-integrity
            # contract) passes against the rebuilt index too.
            post = archive.verify_archive_integrity()
            self.assertTrue(
                post["pass"],
                f"post-rebuild verify issues: {post['issues']}",
            )

    def test_full_chain_index_empty_file_rebuild_verify_pass(self):
        """0-byte index.md (空文件) → rebuild → integrity PASS."""
        self._create_full_archive_files()
        (self.archive_dir / "index.md").write_text("", encoding="utf-8")
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"rebuild must reach integrity PASS: {result['verify_issues']}",
        )
        self.assertTrue(result["index_existed"])
        self.assertTrue(result["changed"])
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("FIX-001", index)
        self.assertIn("# 归档索引", index)

    def test_full_chain_index_partial_corruption_rebuild_verify_pass(self):
        """Partially corrupted index (a risk row lost) → rebuild → integrity
        PASS, with the regenerated index byte-identical to the healthy one."""
        self._create_full_archive_files()
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            archive.build_index()
            index_path = self.archive_dir / "index.md"
            healthy = index_path.read_text(encoding="utf-8")

            risk_row = (
                "| RISK-001 | Data loss during archive "
                "| archive/risks/risks-v0.11.0-0.12.0.md |"
            )
            self.assertIn(risk_row, healthy,
                          "fixture guard: expected the risk row in the index")
            corrupted = healthy.replace(risk_row + "\n", "")
            index_path.write_text(corrupted, encoding="utf-8")

            # Pre-state: the truncated index lost the risks reference —
            # verify must FAIL (orphan + Check 3 count mismatch).
            pre = archive.verify_archive_integrity()
            self.assertFalse(
                pre["pass"],
                f"corrupted index must fail verify: {pre['issues']}",
            )

            result = archive.rebuild_index()

            self.assertTrue(
                result["verify_pass"],
                f"rebuild must reach integrity PASS: {result['verify_issues']}",
            )
            self.assertTrue(result["changed"])
            # Deterministic regeneration: the view is restored byte-identical.
            self.assertEqual(index_path.read_text(encoding="utf-8"), healthy)

    def test_full_chain_index_garbage_format_rebuild_verify_pass(self):
        """Format-broken index (prose garbage, no valid sections) → rebuild →
        integrity PASS."""
        self._create_full_archive_files()
        (self.archive_dir / "index.md").write_text(
            "这不是归档索引\n随便写的垃圾内容\n## 某个别的章节\n",
            encoding="utf-8",
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            pre = archive.verify_archive_integrity()
            self.assertFalse(pre["pass"])
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"rebuild must reach integrity PASS: {result['verify_issues']}",
        )
        self.assertTrue(result["changed"])
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("## Task 索引", index)
        self.assertIn("FIX-001", index)

    # ── 重建幂等：已有完好索引时重建 = 等价重生成（no-op） ──

    def test_rebuild_idempotent_with_intact_index(self):
        """Rebuild with an intact index: equivalent no-op — changed=False,
        index byte-identical, archive files untouched."""
        self._create_full_archive_files()
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            archive.build_index()
            index_path = self.archive_dir / "index.md"
            healthy = index_path.read_text(encoding="utf-8")
            before = self._snapshot_archive_state()

            result = archive.rebuild_index()

        self.assertTrue(result["verify_pass"])
        self.assertTrue(result["index_existed"])
        self.assertFalse(
            result["changed"],
            "rebuild with an intact index must be an equivalent no-op",
        )
        self.assertEqual(index_path.read_text(encoding="utf-8"), healthy)
        self.assertEqual(self._snapshot_archive_state(), before)

    # ── 损坏恢复：归档源文件损伤时重建不崩溃、登记、报告 ──

    def test_rebuild_registers_empty_archive_file_and_verifies_pass(self):
        """0-byte task archive file: registered in 非结构化归档 (not an orphan),
        reported in damaged_files, integrity PASS after rebuild."""
        (self.archive_dir / "tasks" / "v0.13.0~v0.14.0.md").write_text(
            "", encoding="utf-8"
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"empty archive file must not break the rebuild: {result['verify_issues']}",
        )
        kinds = {d["file"]: d["kind"] for d in result["damaged_files"]}
        self.assertEqual(kinds.get("archive/tasks/v0.13.0~v0.14.0.md"), "empty")
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("archive/tasks/v0.13.0~v0.14.0.md", index)
        self.assertIn("空文件", index)

    def test_rebuild_survives_unreadable_archive_file(self):
        """Binary-garbage task archive file: rebuild must not raise, the file
        is registered as 损坏 and integrity stays PASS."""
        (self.archive_dir / "tasks" / "v0.15.0~v0.16.0.md").write_bytes(
            b"\xff\xfe\x00\x01binary garbage not utf8 \xff\xff"
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"unreadable archive file must not break the rebuild: {result['verify_issues']}",
        )
        kinds = {d["file"]: d["kind"] for d in result["damaged_files"]}
        self.assertEqual(kinds.get("archive/tasks/v0.15.0~v0.16.0.md"), "decode_errors")
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("archive/tasks/v0.15.0~v0.16.0.md", index)
        self.assertIn("损坏", index)

    def test_rebuild_salvages_readable_rows_from_partially_corrupted_archive(self):
        """Partially corrupted task archive (valid rows + binary tail): the
        readable rows are salvaged into the index, the damage is reported,
        and integrity PASSes (partial recovery, no data invention)."""
        readable = (
            "### v0.17.0\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-101 | Readable row | P1 | — | 0.17.0 | 阿速 | — | Code Reviewer | TBD | 已完成 |\n"
        ).encode("utf-8")
        (self.archive_dir / "tasks" / "v0.17.0~v0.18.0.md").write_bytes(
            readable + b"\n\xff\xff\xff TRUNCATED BINARY TAIL\n"
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"partially corrupted archive must still verify: {result['verify_issues']}",
        )
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("FIX-101", index)
        kinds = {d["file"]: d["kind"] for d in result["damaged_files"]}
        self.assertEqual(kinds.get("archive/tasks/v0.17.0~v0.18.0.md"), "decode_errors")

    def test_rebuild_registers_rowless_structured_archive_file(self):
        """A readable, structured-named task archive with no extractable rows
        (mangled table) is registered (无条目) instead of becoming an orphan."""
        (self.archive_dir / "tasks" / "v0.19.0~v0.20.0.md").write_text(
            "# 归档 Task 表 — v0.19.0 ~ v0.20.0\n"
            "- **归档日期**: 2026-05-08\n"
            "- **条目数**: 0\n\n"
            "（正文表结构已损坏，仅存头部）\n",
            encoding="utf-8",
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"row-less archive must not become an orphan: {result['verify_issues']}",
        )
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("archive/tasks/v0.19.0~v0.20.0.md", index)
        self.assertIn("无条目", index)

    def test_rebuild_registers_empty_evidence_archive_file(self):
        """Entry-less damage handling covers non-task categories too: an
        empty evidence archive is registered and integrity PASSes."""
        (self.archive_dir / "evidence" / "v0.21.0~v0.22.0.md").write_text(
            "", encoding="utf-8"
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"empty evidence archive must not break the rebuild: {result['verify_issues']}",
        )
        kinds = {d["file"]: d["kind"] for d in result["damaged_files"]}
        self.assertEqual(kinds.get("archive/evidence/v0.21.0~v0.22.0.md"), "empty")
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("archive/evidence/v0.21.0~v0.22.0.md", index)

    # ── P1-1 red-green: build/verify Check 3 counting-caliber symmetry ──
    # REVIEW-FIX-384-R0 P1-1: build_index's extraction caliber and verify
    # Check 3's counting caliber for decisions/risks disagreed on damaged
    # rows, making the post-rebuild integrity PASS unreachable (the verify
    # message "Run build_index() to rebuild" became a dead loop). Both sides
    # now share ONE extraction function per category; these tests pin the
    # damaged-row corners.

    def test_rebuild_passes_with_colon_damaged_decision_header(self):
        """P1-1 corner ①: a DEC header with the colon lost (`## DEC-001 title`)
        is NOT indexable by the canonical `## DEC-n: title` caliber — the file
        must be registered entry-less and Check 3 must count 0 on BOTH sides,
        so the rebuild reaches integrity PASS (red on the pre-fix caliber
        split: verify counted the damaged header, build_index did not)."""
        (self.archive_dir / "decisions" / "decisions-v0.11.0-0.12.0.md").write_text(
            "# 归档 Decision 记录 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "## DEC-001 Use SQLite for storage\n\n"
            "- 归档版本: v0.11.0（冒号损坏头，不可索引）\n",
            encoding="utf-8",
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"colon-damaged DEC header must not dead-loop the rebuild: "
            f"{result['verify_issues']}",
        )
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        # The damaged file is registered (P2-1 registration-branch coverage).
        self.assertIn("archive/decisions/decisions-v0.11.0-0.12.0.md", index)
        self.assertIn("无条目", index)

    def test_rebuild_passes_with_truncated_risk_row(self):
        """P1-1 corner ②: a truncated risk row (2 data cells instead of ≥4)
        is NOT indexable — registered entry-less, Check 3 symmetric on both
        sides, rebuild reaches integrity PASS (red pre-fix: verify counted
        the truncated row, build_index did not)."""
        (self.archive_dir / "risks" / "risks-v0.11.0-0.12.0.md").write_text(
            "# 归档 Risk 记录 — v0.11.0 ~ v0.12.0\n"
            "- **归档日期**: 2026-05-08\n\n"
            "| RISK-001 | Data loss during archive\n",
            encoding="utf-8",
        )
        import archive

        with patch.object(archive, "ROOT", self.root), \
                patch.object(archive, "PLUGIN_ROOT", self.root):
            result = archive.rebuild_index()

        self.assertTrue(
            result["verify_pass"],
            f"truncated risk row must not dead-loop the rebuild: "
            f"{result['verify_issues']}",
        )
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        # The damaged file is registered (P2-1 registration-branch coverage).
        self.assertIn("archive/risks/risks-v0.11.0-0.12.0.md", index)
        self.assertIn("无条目", index)

    # ── 损伤分类器（单元级） ──

    def test_archive_file_damage_classifier(self):
        """_archive_file_damage: None / unreadable / empty / decode_errors."""
        import archive

        ok = self.archive_dir / "tasks" / "ok.md"
        ok.write_text("# 归档\n", encoding="utf-8")
        self.assertIsNone(archive._archive_file_damage(ok))

        missing = archive._archive_file_damage(
            self.archive_dir / "tasks" / "missing.md"
        )
        self.assertEqual(missing["kind"], "unreadable")

        empty = self.archive_dir / "tasks" / "empty.md"
        empty.write_bytes(b"")
        self.assertEqual(archive._archive_file_damage(empty)["kind"], "empty")

        bad = self.archive_dir / "tasks" / "bad.md"
        bad.write_bytes(b"# ok\n\xff\xfe trailing garbage")
        damage = archive._archive_file_damage(bad)
        self.assertEqual(damage["kind"], "decode_errors")
        self.assertIn("byte", damage["detail"])

    # ── CLI 恢复入口 ──

    def test_cli_rebuild_index_reports_and_exits_zero(self):
        """`archive.py rebuild-index` rebuilds, prints the integrity verdict,
        and exits 0; a second run is an idempotent no-op."""
        self._create_full_archive_files()
        import archive

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            archive.main(["rebuild-index", "--project-root", str(self.root)])
        printed = out.getvalue()
        self.assertIn("Status: rebuilt", printed)
        self.assertIn("Integrity: PASS", printed)

        out2 = io.StringIO()
        with contextlib.redirect_stdout(out2):
            archive.main(["rebuild-index", "--project-root", str(self.root)])
        printed2 = out2.getvalue()
        self.assertIn("Status: unchanged (idempotent no-op equivalent)", printed2)
        self.assertIn("Integrity: PASS", printed2)


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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertFalse(result["pass"])
        self.assertGreater(len(result["issues"]), 0)

    def test_verify_no_archive_dir_passes(self):
        """When archive/ directory is empty (no index, no files), pass gracefully."""
        # Remove all .md files from archive (only .gitkeep remains)
        for f in self.archive_dir.glob("**/*.md"):
            f.unlink()

        import archive

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertTrue(result["pass"])

    def test_verify_detects_index_count_mismatch(self):
        """FIX-163 (TD-015): Check 3 must flag when archive-file entry count
        != index entry count (silent drift detection). Previously Check 3 only
        counted both but never compared, so drift went undetected."""
        import archive

        # Add an archive task file with an extractable entry (10-col format,
        # ID in col 1) WITHOUT a corresponding index row -> drift.
        tasks_arch = self.archive_dir / "tasks"
        drift_file = tasks_arch / "drift-v0.5.0.md"
        drift_file.write_text(
            "# 归档\n\n### v0.5.0\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| DRIFT-001 | drift | P1 | — | 0.5.0 | owner | reviewer | review | path | 已完成 |\n",
            encoding="utf-8"
        )
        # Create an index.md that does NOT reference DRIFT-001 (so index count=0,
        # but file count=1 -> mismatch detected by Check 3).
        index_file = self.archive_dir / "index.md"
        index_file.write_text(
            "# 归档索引\n\n## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n",
            encoding="utf-8"
        )
        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.verify_archive_integrity()

        self.assertFalse(result["pass"], "must flag count mismatch")
        self.assertTrue(any("mismatch" in i.lower() or "count" in i.lower() for i in result["issues"]),
                        f"issues should mention count mismatch: {result['issues']}")

    def test_verify_check3_symmetric_with_decisions_risks(self):
        """FIX-162 + FIX-163 coupling regression guard: when decisions/risks
        are migrated (archive/decisions + archive/risks have files AND index
        has matching DEC/RISK rows), Check 3 must NOT false-positive a count
        mismatch. The per-category comparison keeps tasks/evidence/decisions/
        risks counts symmetric on both sides."""
        import archive

        # decisions archive file with 2 DEC headers
        (self.archive_dir / "decisions" / "decisions-v0.1.0-0.59.0.md").write_text(
            "## DEC-001: Old\n\n- 归档版本: v0.38.0\n\n"
            "## DEC-002: Older\n\n- 归档版本: v0.38.0\n",
            encoding="utf-8"
        )
        # risks archive file with 2 RISK rows
        (self.archive_dir / "risks" / "risks-v0.1.0-0.59.0.md").write_text(
            "# 归档风险\n\n| RISK-001 | desc |\n| RISK-002 | desc2 |\n",
            encoding="utf-8"
        )
        # index.md with balanced DEC (2) + RISK (2) rows in their sections.
        # Also reference the archive files so Check 2 doesn't trip.
        (self.archive_dir / "index.md").write_text(
            "# 归档索引\n\n"
            "## Task 索引\n\n| Task ID | 状态 | 版本 | 归档文件 |\n\n"
            "## Evidence 索引\n\n| EVD ID | 归档文件 |\n\n"
            "## Decision 索引\n\n"
            "| DEC ID | 归档文件 |\n"
            "| DEC-001 | archive/decisions/decisions-v0.1.0-0.59.0.md |\n"
            "| DEC-002 | archive/decisions/decisions-v0.1.0-0.59.0.md |\n\n"
            "## Risk 索引\n\n"
            "| RISK ID | 归档文件 |\n"
            "| RISK-001 | archive/risks/risks-v0.1.0-0.59.0.md |\n"
            "| RISK-002 | archive/risks/risks-v0.1.0-0.59.0.md |\n",
            encoding="utf-8"
        )
        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.verify_archive_integrity()
        # Check 3 specifically must not flag a count mismatch (the coupling bug)
        check3_issues = [i for i in result["issues"] if "mismatch" in i.lower() or "count" in i.lower()]
        self.assertEqual(check3_issues, [],
                         f"Check 3 must be symmetric for decisions/risks (no false mismatch): {check3_issues}")

    def test_verify_passes_after_build_index_with_narrative_file(self):
        """FIX-176 end-to-end regression: after build_index() rebuilds the
        index from scratch, a non-structured narrative-* task-archive file
        must NOT be flagged as an orphan by verify_archive_integrity. On the
        unpatched archive.py, build_index() drops the narrative file and
        verify_archive_integrity() fails Check 2 with
        '归档文件未在索引中记录: archive/tasks/narrative-...md' (FAIL-on-buggy),
        and after the fix both build_index + verify pass cleanly."""
        import archive

        # One structured task archive + one narrative (free-prose) archive.
        (self.archive_dir / "tasks" / "v0.1.0~v0.2.0.md").write_text(
            "# 归档\n\n### v0.1.0\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | d | P1 | — | 0.1.0 | o | r | rt | p | 已完成 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "tasks" / "narrative-2026-04-30_2026-06-27.md").write_text(
            "# 归档叙述段 — 历史活跃事项（2026-04-30 ~ 2026-06-27）\n"
            "\n"
            "- **归档范围**: 已闭环历史事项叙述\n"
            "- **条目数**: 5 段\n"
            "\n"
            "**2026-06-26 某事项**：自由叙述文本，无 task 表格行。\n",
            encoding="utf-8",
        )

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            archive.build_index()  # rebuild index from scratch
            result = archive.verify_archive_integrity()

        self.assertTrue(
            result["pass"],
            f"verify should pass after rebuild with a narrative file: {result['issues']}",
        )
        self.assertEqual(result["issues"], [])
        # No orphan complaint in particular.
        self.assertFalse(
            any("narrative" in i for i in result["issues"]),
            f"narrative file must not be flagged as orphan: {result['issues']}",
        )


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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.migrate_by_version(
                "0.10.0", "0.10.0", dry_run=False, migrate_evidence=True
            )
            archive.build_index()

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 1)
        self.assertEqual(result["evidence_archived"], 1)

        task_file = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        evidence_file = self.archive_dir / "evidence" / "evidence-v0.10.0-0.10.0.md"
        self.assertTrue(task_file.exists())
        self.assertTrue(evidence_file.exists())

        pt_after_migrate = (self.gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
        ev_after_migrate = (self.gov_dir / "evidence-log.md").read_text(encoding="utf-8")
        self.assertNotIn("| FIX-001 |", pt_after_migrate)
        self.assertNotIn("| EVD-001 |", ev_after_migrate)
        self.assertIn("| EVD-002 |", ev_after_migrate)

        # Force the evidence archive to be the newest file.  The rollback must
        # still find and group both files (different names now, but the same
        # version range — grouped via the FIX-164 range fallback).
        newer = task_file.stat().st_mtime + 10
        os.utime(evidence_file, (newer, newer))

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            rollback = archive.rollback_last_migration()

        self.assertTrue(rollback["success"])
        self.assertEqual(
            set(rollback["rolled_back_files"]),
            {
                "archive/tasks/v0.10.0~v0.10.0.md",
                "archive/evidence/evidence-v0.10.0-0.10.0.md",
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            second = archive.migrate_by_version("0.10.0", "0.10.0", dry_run=False)
            archive.build_index()

        self.assertTrue(second["success"])
        self.assertEqual(second["tasks_archived"], 1)
        inc_files = sorted((self.archive_dir / "tasks").glob("v0.10.0~v0.10.0-incremental-*.md"))
        self.assertEqual(len(inc_files), 1)
        self.assertTrue(base_file.exists())

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

    def test_auto_dry_run_summary_reports_verify_na_not_failed(self):
        """FIX-250: a dry-run performs no migration, so the summary must not
        report a misleading '校验: FAILED' (verify_pass stays False because
        verify_archive_integrity never runs in dry-run); report N/A instead."""
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
            result = archive.migrate_auto(dry_run=True)

        summary = archive._format_auto_summary(result)
        self.assertIn("校验: N/A", summary)
        self.assertNotIn("校验: FAILED", summary)

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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        with patch.object(archive, 'ROOT', self.root), patch.object(archive, 'PLUGIN_ROOT', self.root):
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

        # Verify completed count (FIX-158: status column now dynamic via header)
        status_col = archive._find_status_column(sample.get("header_line") or "")
        completed = sum(1 for _, line, _ in sample["task_lines"]
                       if archive._parse_task_status(line, status_col=status_col) == "已完成")
        self.assertEqual(completed, 4, "TASK-001,002,003,005 completed; TASK-004 in progress")


class TestPriorityTableArchive(unittest.TestCase):
    """FIX-158: tests for the 7-column priority table format (ID in col 2,
    target version in col 5, status last) and the dynamic status-column
    detection that fixed AUDIT-125 '无可归档数据'."""

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive

    def test_find_status_column_priority_table(self):
        """7-col priority table: 状态 is the last column (index 6)."""
        header = "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |"
        self.assertEqual(self.archive._find_status_column(header), 6)

    def test_find_status_column_legacy_10col(self):
        """Legacy 10-col version-section table: 状态 at index 9."""
        header = "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |"
        self.assertEqual(self.archive._find_status_column(header), 9)

    def test_find_status_column_sample_20col(self):
        """20-col sample table: 状态 at index 9."""
        header = "| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |"
        self.assertEqual(self.archive._find_status_column(header), 9)

    def test_find_status_column_none_cases(self):
        """None header, empty, non-table, and no-状态 header all return None."""
        self.assertIsNone(self.archive._find_status_column(None))
        self.assertIsNone(self.archive._find_status_column(""))
        self.assertIsNone(self.archive._find_status_column("not a table"))
        self.assertIsNone(self.archive._find_status_column("| A | B | C |"))

    def test_parse_priority_table_tasks_7col(self):
        """Parse the real 7-col priority table: ID in col 2, version in col 5."""
        content = "\n".join([
            "## 当前活跃事项",
            "",
            "### 优先级一览",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-084 | Active task | — | 0.38.0 | TBD | ✅ 已完成 |",
            "| **P1** | FIX-085 | Pending task | FIX-084 | 0.38.0 | TBD | ⏳ 进行中 |",
            "| **P0** | REL-013 | Release | FIX-084 | 0.38.0 | TBD | ✅ 已发布 |",
            "",
            "### 1.0.0 依赖链",
        ])
        tasks = self.archive._parse_priority_table_tasks(content)
        self.assertEqual(len(tasks), 3)
        ids = [t[2] for t in tasks]
        self.assertIn("FIX-084", ids)
        self.assertIn("FIX-085", ids)
        self.assertIn("REL-013", ids)
        # Version classification from col 5
        fix084 = next(t for t in tasks if t[2] == "FIX-084")
        self.assertEqual(fix084[3], "0.38.0")
        self.assertEqual(fix084[4], "✅ 已完成")

    def test_parse_priority_table_tasks_ignores_legacy_10col(self):
        """Must NOT pick up the legacy 10-col '| 任务ID | 描述 | 优先级 |...' format
        (where 优先级 is in the middle, not the first cell)."""
        content = "\n".join([
            "### v0.11.0",
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| FIX-001 | desc | P1 | — | 1.0.0 | 阿速 | — | Reviewer | TBD | 已完成 |",
        ])
        tasks = self.archive._parse_priority_table_tasks(content)
        self.assertEqual(len(tasks), 0, "Legacy 10-col table must not be parsed as priority table")

    def test_task_status_is_archivable_variants(self):
        """Closed/delivered ✅-variants are archivable; open/pending are not."""
        archivable = [
            "✅ 已完成", "✅ 已发布", "✅ 保守闭环 / 未满足 full PASS",
            "✅ 完成候选", "✅ 发布候选完成", "已交付", "调查完成",
            "诊断完成", "✅ 已撤回/失效", "✅ Phase 1 完成 (2026-06-28)",
        ]
        not_archivable = [
            "⏳ 进行中", "⏳ 待启动 (依赖 FIX-157)", "⏸ 停滞待重新评估",
            "🚧 阻塞中", "待决", "未完成", "TO_BE_DEFINED",
        ]
        for s in archivable:
            self.assertTrue(self.archive._task_status_is_archivable(s), f"should be archivable: {s}")
        for s in not_archivable:
            self.assertFalse(self.archive._task_status_is_archivable(s), f"should NOT be archivable: {s}")

    def test_task_status_is_archivable_no_false_positive_on_completed(self):
        """'已完成' must be archivable, and substring '待' must not falsely match it."""
        self.assertTrue(self.archive._task_status_is_archivable("已完成"))
        self.assertFalse(self.archive._task_status_is_archivable("待启动"))

    def test_parse_task_status_dynamic_col(self):
        """Status extraction uses the passed status_col, not a hardcoded column."""
        # 7-col row: status is last data cell
        row7 = "| **P0** | FIX-084 | desc | — | 0.38.0 | TBD | ✅ 已完成 |"
        self.assertEqual(self.archive._parse_task_status(row7, status_col=6), "已完成")
        # Without status_col, defaults to last column (correct for 7-col)
        self.assertEqual(self.archive._parse_task_status(row7), "已完成")


class TestDecisionRiskMigration(unittest.TestCase):
    """FIX-162 (TD-014): decision-log and risk-log migration when related
    tasks have been archived."""

    def setUp(self):
        import archive
        self.archive = archive

    def _make_decision_log(self, gov, rows):
        lines = ["# 决策记录", ""]
        for dec_id, date, title, related in rows:
            lines.append(f"| {dec_id} | {date} | {title} | ctx | decision | alt | reason | impact | owner | {related} | scope |")
        (gov / "decision-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _make_risk_log(self, gov, rows):
        """Create a risk-log.md mirroring the real 13-column format.

        rows: list of (risk_id, date, desc, related[, status]).
        status defaults to '已关闭' (closed) so a risk is migratable by default;
        pass '打开' / '缓解中' to model an OPEN/active risk that must stay hot
        (FIX-170). The header includes a '当前状态' column so the archive engine
        can locate the status cell dynamically.
        """
        lines = [
            "# 风险记录", "",
            "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            risk_id, date, desc, related = row[0], row[1], row[2], row[3]
            status = row[4] if len(row) > 4 else "已关闭"
            lines.append(
                f"| {risk_id} | {date} | {desc} | 维护 | 触发 | 影响 | 中 "
                f"| Owner | {status} | 缓解动作 | 2026-09-30 | {related} | 备注 |"
            )
        (gov / "risk-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _make_archived_tasks(self, gov, tasks):
        """Create an archive/tasks file with completed historical tasks."""
        arch = gov / "archive" / "tasks"
        arch.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 归档 Task 表 — v0.1.0 ~ v0.59.0",
            "",
            "### v0.38.0",
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for tid, version in tasks:
            lines.append(f"| {tid} | desc | P1 | — | {version} | owner | reviewer | review | path | 已完成 |")
        (arch / "legacy-v0.38.0.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _make_evidence_log(self, gov, rows):
        """FIX-164: create an evidence-log with the given EVD rows.

        rows: list of (evd_id, task_ids, summary). task_ids is the 关联 Task
        column value (may be comma-separated).
        """
        lines = [
            "# 证据记录", "",
            "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for evd_id, task_ids, summary in rows:
            lines.append(
                f"| {evd_id} | {task_ids} | {summary} | 2026-05-01 | 代码 | src/ | 阿速 | 老赵 | 通过 | — |"
            )
        (gov / "evidence-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_decision_migrates_when_related_task_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_decision_log(gov, [
                ("DEC-001", "2026-05-01", "Old decision", "FIX-084, REL-013"),
                ("DEC-050", "2026-06-28", "Active decision", "FIX-157, REL-048"),
            ])
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0"), ("REL-013", "0.38.0")])
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                # DEC-001 references archived FIX-084 (v0.38.0, in range) -> migrates
                # DEC-050 references FIX-157 (not in archive) -> stays
                count = self.archive._migrate_decisions("0.1.0", "0.59.0", {"FIX-084": "0.38.0", "REL-013": "0.38.0"}, dry_run=False)
                self.assertEqual(count, 1)
                # Decision-log should now have only DEC-050
                kept = (gov / "decision-log.md").read_text(encoding="utf-8")
                self.assertIn("DEC-050", kept)
                self.assertNotIn("DEC-001", kept)
                # Archive file written with ## DEC-001: title format
                arch = (gov / "archive" / "decisions" / "decisions-v0.1.0-0.59.0.md").read_text(encoding="utf-8")
                self.assertIn("## DEC-001: Old decision", arch)

    def test_decision_not_migrated_when_no_related_task_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_decision_log(gov, [
                ("DEC-050", "2026-06-28", "Active decision", "FIX-157, REL-048"),
            ])
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_decisions("0.1.0", "0.59.0", {"FIX-084": "0.38.0"}, dry_run=False)
                self.assertEqual(count, 0)
                kept = (gov / "decision-log.md").read_text(encoding="utf-8")
                self.assertIn("DEC-050", kept)

    def test_risk_migrates_when_related_task_archived(self):
        """A CLOSED risk whose related task is archived migrates to the archive;
        a risk referencing a still-live task stays (regardless of status)."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_risk_log(gov, [
                ("RISK-001", "2026-04-01", "Old risk", "FIX-084"),
                ("RISK-039", "2026-06-24", "Active risk", "AUDIT-121"),
            ])
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_risks("0.1.0", "0.59.0", {"FIX-084": "0.38.0"}, dry_run=False)
                self.assertEqual(count, 1)
                kept = (gov / "risk-log.md").read_text(encoding="utf-8")
                self.assertIn("RISK-039", kept)
                self.assertNotIn("RISK-001", kept)
                arch = (gov / "archive" / "risks" / "risks-v0.1.0-0.59.0.md").read_text(encoding="utf-8")
                self.assertIn("| RISK-001 |", arch)

    def test_risk_status_closed_markers(self):
        """FIX-170 (AUDIT-127): _is_risk_closed detects the closed-status
        variants seen in the real risk-log, including decorated forms."""
        header = ("| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 "
                  "| 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |")
        closed_rows = [
            "| RISK-005 | 2026-04-18 | x | y | z | w | 中 | O | 已关闭 | m | d | t | n |",
            "| RISK-006 | 2026-04-18 | x | y | z | w | 中 | O | **已关闭** | m | d | t | n |",
            "| RISK-007 | 2026-04-18 | x | y | z | w | 中 | O | 已关闭 (2026-05-05) | m | d | t | n |",
            "| RISK-008 | 2026-04-18 | x | y | z | w | 中 | O | closed | m | d | t | n |",
        ]
        for row in closed_rows:
            self.assertTrue(self.archive._is_risk_closed(row, header),
                            f"should be closed: {row}")

    def test_risk_status_open_markers_stay_hot(self):
        """FIX-170 (AUDIT-127): open/active status markers keep a risk in the hot
        file even when its related task is archived (the AUDIT-127 regression)."""
        header = ("| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 "
                  "| 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |")
        open_rows = [
            "| RISK-036 | 2026-06-23 | x | y | z | w | 高 | O | 打开 | m | d | t | n |",
            "| RISK-024 | 2026-04-28 | x | y | z | w | 高 | O | 缓解中 | m | d | t | n |",
            "| RISK-002 | 2026-04-17 | x | y | z | w | 中 | O | 缓解完成 | m | d | t | n |",
            "| RISK-099 | 2026-04-17 | x | y | z | w | 中 | O | Open | m | d | t | n |",
        ]
        for row in open_rows:
            self.assertFalse(self.archive._is_risk_closed(row, header),
                             f"should NOT be closed: {row}")

    def test_risk_open_not_migrated_despite_archived_related_task(self):
        """FIX-170 (AUDIT-127) regression: the exact bug — RISK-036/037/039 were
        OPEN 1.0.0 hard blockers whose related tasks fell in the v0.1.0~0.59.0
        range and got migrated OUT of the hot risk-log. After the fix, an OPEN
        risk with an archived related task stays in the hot file, while a CLOSED
        risk with the same related task migrates. Both rows are in-range."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_risk_log(gov, [
                # OPEN risk, related task FIX-084 (v0.38.0, in range) — must stay.
                ("RISK-036", "2026-06-23", "OPEN 1.0.0 blocker", "FIX-084", "打开"),
                # CLOSED risk, same related task, in range — migrates.
                ("RISK-001", "2026-04-01", "Old closed risk", "FIX-084", "已关闭"),
            ])
            task_versions = {"FIX-084": "0.38.0"}
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_risks(
                    "0.1.0", "0.59.0", task_versions, dry_run=False
                )
            # Only the closed risk migrates.
            self.assertEqual(count, 1)
            kept = (gov / "risk-log.md").read_text(encoding="utf-8")
            # OPEN risk MUST remain in the hot risk-log.
            self.assertIn("| RISK-036 |", kept)
            # Closed risk is removed from hot and written to archive.
            self.assertNotIn("| RISK-001 |", kept)
            arch = (gov / "archive" / "risks"
                    / "risks-v0.1.0-0.59.0.md").read_text(encoding="utf-8")
            self.assertIn("| RISK-001 |", arch)
            self.assertNotIn("RISK-036", arch)

    def test_risk_open_kept_hot_via_migrate_auto(self):
        """FIX-170 end-to-end via migrate_auto: an OPEN risk referenced by an
        archived task survives a full --auto run in the hot risk-log."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            (gov / "archive").mkdir()
            for sub in ["tasks", "evidence", "decisions", "risks"]:
                (gov / "archive" / sub).mkdir()
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
            _make_plan_tracker_with_roadmap(gov, roadmap, tasks)
            _pad_plan_tracker(gov)
            # Risk-log: OPEN risk referencing an in-range archived task + closed.
            self._make_risk_log(gov, [
                ("RISK-036", "2026-06-23", "OPEN blocker", "FIX-001", "打开"),
                ("RISK-001", "2026-04-01", "Old closed", "FIX-001", "已关闭"),
            ])

            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                result = self.archive.migrate_auto(dry_run=False)

            self.assertTrue(result["success"])
            kept = (gov / "risk-log.md").read_text(encoding="utf-8")
            # OPEN risk survives in hot file.
            self.assertIn("| RISK-036 |", kept)
            # Closed risk migrated out of hot file.
            self.assertNotIn("| RISK-001 |", kept)
            # The closed risk lands in the single risks archive file written.
            risk_archives = sorted((gov / "archive" / "risks").glob("*.md"))
            self.assertEqual(len(risk_archives), 1)
            arch = risk_archives[0].read_text(encoding="utf-8")
            self.assertIn("| RISK-001 |", arch)
            self.assertNotIn("RISK-036", arch)

    def test_risk_status_column_aware_not_whole_row(self):
        """FIX-170 column-aware guard: an OPEN risk whose mitigation/notes cells
        contain the words '关闭'/'关闭标准'/'不关闭' must NOT be detected as
        closed. A whole-row substring scan would false-positive here (this is
        the real RISK-036 mitigation text)."""
        header = ("| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 "
                  "| 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |")
        tricky = ("| RISK-036 | 2026-06-23 | desc | 维护 | trig | impact | 高 "
                  "| Coord | 打开 | 此风险关闭标准不变，不关闭本风险 "
                  "| 2026-07-30 | DEC-072 | 关闭标准 |")
        self.assertFalse(self.archive._is_risk_closed(tricky, header),
                         "OPEN risk with '关闭' in mitigation must stay hot")

    def test_risk_status_missing_column_keeps_hot(self):
        """FIX-170 conservative default: if no status column can be located in
        the header, the row is treated as NOT closed (kept hot) rather than
        riskily migrating an unknown-status risk."""
        # Header with no 状态 cell at all.
        header = "| 编号 | 日期 | 描述 | 影响 |"
        row = "| RISK-001 | 2026-04-01 | x | y |"
        self.assertFalse(self.archive._is_risk_closed(row, header))

    def test_migrate_evidence_with_only_historical_tasks(self):
        """FIX-164 regression guard: evidence migrates even when ZERO tasks are
        archived this run, as long as the referenced tasks exist in
        archive/tasks/ (historical). This is the exact bug being fixed — the old
        inline block was gated by the this-run `archived_tasks` set (empty here)
        and so never ran, letting evidence-log bloat."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_evidence_log(gov, [
                ("EVD-001", "FIX-084", "Evidence for fully-archived task"),
                ("EVD-002", "REL-013", "Evidence for another archived task"),
                ("EVD-050", "FIX-157", "Evidence for a LIVE task — must stay"),
            ])
            # No plan-tracker tasks at all this run → archived_tasks would be ∅.
            # But historical tasks exist in archive/tasks/.
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0"), ("REL-013", "0.38.0")])
            task_versions = {"FIX-084": "0.38.0", "REL-013": "0.38.0"}
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_evidence(
                    "0.1.0", "0.59.0", task_versions, dry_run=False
                )
            self.assertEqual(count, 2)  # EVD-001 + EVD-002 migrate; EVD-050 stays
            kept = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("EVD-050", kept)
            self.assertNotIn("EVD-001", kept)
            self.assertNotIn("EVD-002", kept)
            arch = (gov / "archive" / "evidence"
                    / "evidence-v0.1.0-0.59.0.md").read_text(encoding="utf-8")
            self.assertIn("| EVD-001 |", arch)
            self.assertIn("| EVD-002 |", arch)

    def test_migrate_evidence_preserves_mixed_refs(self):
        """FIX-164: an EVD row referencing one archived + one live task is NOT
        migrated (kept). An EVD row referencing two archived tasks IS migrated.
        This guards the ev_task_ids.issubset(task_versions) semantics."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_evidence_log(gov, [
                ("EVD-010", "FIX-084, FIX-157", "mixed archived+live — keep"),
                ("EVD-011", "FIX-084, REL-013", "both archived — migrate"),
            ])
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0"), ("REL-013", "0.38.0")])
            task_versions = {"FIX-084": "0.38.0", "REL-013": "0.38.0"}
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_evidence(
                    "0.1.0", "0.59.0", task_versions, dry_run=False
                )
            self.assertEqual(count, 1)  # only EVD-011
            kept = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("EVD-010", kept)
            self.assertNotIn("EVD-011", kept)

    def test_migrate_evidence_dry_run_no_write(self):
        """FIX-164: dry_run returns the count and writes nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_evidence_log(gov, [
                ("EVD-001", "FIX-084", "archivable evidence"),
            ])
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0")])
            task_versions = {"FIX-084": "0.38.0"}
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_evidence(
                    "0.1.0", "0.59.0", task_versions, dry_run=True
                )
            self.assertEqual(count, 1)
            self.assertFalse((gov / "archive" / "evidence"
                              / "evidence-v0.1.0-0.59.0.md").exists())
            kept = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("EVD-001", kept)

    def test_migrate_evidence_ignores_cross_entity_refs(self):
        """FIX-171 (AUDIT-126 root cause B) core regression: an EVD row that
        references an archived task-family ID PLUS cross-entity refs (RISK-/DEC-)
        must MIGRATE — the cross-entity refs are descriptive context and must NOT
        gate the subset check. Before the fix this row was blocked forever because
        RISK-/DEC- are structurally never in task_versions.

        Also guards the preserved mixed-ref semantic: a second row referencing one
        archived + one LIVE task-family ID still does NOT migrate."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_evidence_log(gov, [
                # Row 1: archived FIX-084 + cross-entity RISK-036/DEC-072 → migrates.
                ("EVD-100", "FIX-084, RISK-036, DEC-072", "archived task + cross-entity refs"),
                # Row 2: archived FIX-084 + LIVE FIX-157 → stays (mixed-ref guard).
                ("EVD-101", "FIX-084, FIX-157", "archived + live task-family — keep"),
            ])
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0")])
            task_versions = {"FIX-084": "0.38.0"}  # FIX-157 deliberately absent (live)
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_evidence(
                    "0.1.0", "0.59.0", task_versions, dry_run=False
                )
            self.assertEqual(count, 1)  # only EVD-100 migrates
            kept = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertNotIn("EVD-100", kept)   # migrated out
            self.assertIn("EVD-101", kept)      # mixed-ref → kept hot
            arch = (gov / "archive" / "evidence"
                    / "evidence-v0.1.0-0.59.0.md").read_text(encoding="utf-8")
            self.assertIn("| EVD-100 |", arch)
            self.assertNotIn("EVD-101", arch)

    def test_migrate_evidence_only_cross_entity_refs_stays(self):
        """FIX-171 (AUDIT-126): an EVD row referencing ONLY cross-entity IDs
        (no task-family ID at all) is ambiguous — no version can be resolved —
        so it is KEPT hot rather than riskily migrating an unversionable row."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir()
            self._make_evidence_log(gov, [
                ("EVD-200", "RISK-036, DEC-072", "cross-entity only — no task-family ref"),
            ])
            self._make_archived_tasks(gov, [("FIX-084", "0.38.0")])
            task_versions = {"FIX-084": "0.38.0"}
            with patch.object(self.archive, "ROOT", Path(tmp)), patch.object(self.archive, "PLUGIN_ROOT", Path(tmp)):
                count = self.archive._migrate_evidence(
                    "0.1.0", "0.59.0", task_versions, dry_run=False
                )
            self.assertEqual(count, 0)  # nothing migrates
            kept = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("EVD-200", kept)  # stays hot

    def test_is_task_family_id_classification(self):
        """FIX-171: _is_task_family_id correctly distinguishes task-family
        prefixes (can be tasks) from cross-entity prefixes (never tasks)."""
        # task-family prefixes → True
        for tid in ("FIX-084", "REL-013", "AUDIT-126", "REQ-082", "SYSGAP-030",
                    "TD-014", "MAINT-002", "FMT-008", "DIAG-003", "DESIGN-002"):
            self.assertTrue(self.archive._is_task_family_id(tid),
                            f"should be task-family: {tid}")
        # cross-entity prefixes → False
        for tid in ("RISK-036", "DEC-072", "REVIEW-001", "EVD-650", "TIER-001",
                    "CONSTRAINT-001", "TOOL-001", "ADR-006"):
            self.assertFalse(self.archive._is_task_family_id(tid),
                             f"should be cross-entity: {tid}")

    def test_extract_tasks_from_legacy_filename_version(self):
        """FIX-171 (AUDIT-126 factor C): an archive file named legacy-v0.10.0.md
        with NO in-file `### v0.10.0` title header must still yield version
        "0.10.0" (parsed from the filename) instead of "unknown"."""
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            arch = gov / "archive" / "tasks"
            arch.mkdir(parents=True, exist_ok=True)
            # legacy file with a task row but NO version title header
            (arch / "legacy-v0.10.0.md").write_text(
                "# 归档 Task 表 — v0.10.0 遗留收编\n\n"
                "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-010 | legacy task | P1 | — | 0.10.0 | owner | reviewer | review | path | 已完成 |\n",
                encoding="utf-8",
            )
            results = self.archive._extract_tasks_from_archive_file(
                arch / "legacy-v0.10.0.md"
            )
            self.assertEqual(len(results), 1)
            task_id, status, version = results[0]
            self.assertEqual(task_id, "FIX-010")
            self.assertEqual(version, "0.10.0")  # from filename, not "unknown"

    def test_extract_tasks_range_filename_version(self):
        """FIX-171 (AUDIT-126 factor C): a range file named v0.1.0~v0.31.0.md
        with no in-file title header yields the range START version "0.1.0"
        (the conservative lower-bound label; _version_in_range handles membership
        regardless of which bound is used)."""
        with tempfile.TemporaryDirectory() as tmp:
            arch = Path(tmp) / "archive" / "tasks"
            arch.mkdir(parents=True, exist_ok=True)
            (arch / "v0.1.0~v0.31.0.md").write_text(
                "# 归档 Task 表 — v0.1.0 ~ v0.31.0\n\n"
                "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-020 | range-file task | P1 | — | 0.5.0 | owner | reviewer | review | path | 已完成 |\n",
                encoding="utf-8",
            )
            results = self.archive._extract_tasks_from_archive_file(
                arch / "v0.1.0~v0.31.0.md"
            )
            self.assertEqual(len(results), 1)
            task_id, status, version = results[0]
            self.assertEqual(task_id, "FIX-020")
            self.assertEqual(version, "0.1.0")  # range start, not "unknown"

    def test_extract_tasks_date_named_file_stays_unknown(self):
        """FIX-171 guard: date-named files (completed-tasks-YYYY-MM-DD_...md)
        are NOT version-scoped — the filename fallback returns None and the
        version stays "unknown" (current behavior), since these files legitimately
        span many versions with no single version label."""
        with tempfile.TemporaryDirectory() as tmp:
            arch = Path(tmp) / "archive" / "tasks"
            arch.mkdir(parents=True, exist_ok=True)
            (arch / "completed-tasks-2026-04-30_2026-06-27.md").write_text(
                "# 归档 Task 表 — 历史已完成事项\n\n"
                "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-030 | date-file task | P1 | — | 0.40.0 | owner | reviewer | review | path | 已完成 |\n",
                encoding="utf-8",
            )
            results = self.archive._extract_tasks_from_archive_file(
                arch / "completed-tasks-2026-04-30_2026-06-27.md"
            )
            self.assertEqual(len(results), 1)
            task_id, status, version = results[0]
            self.assertEqual(task_id, "FIX-030")
            self.assertEqual(version, "unknown")  # date-named → no version label

    def test_version_from_archive_filename_helper(self):
        """FIX-171: direct unit tests for _version_from_archive_filename covering
        all three naming families (single-version, range, date-named)."""
        from pathlib import Path
        self.assertEqual(
            self.archive._version_from_archive_filename(Path("legacy-v0.10.0.md")),
            "0.10.0",
        )
        self.assertEqual(
            self.archive._version_from_archive_filename(Path("v0.1.0~v0.31.0.md")),
            "0.1.0",  # range start
        )
        self.assertEqual(
            self.archive._version_from_archive_filename(Path("v0.10.0~v0.10.0.md")),
            "0.10.0",
        )
        # incremental range file → still returns start
        self.assertEqual(
            self.archive._version_from_archive_filename(
                Path("v0.10.0~v0.12.0-incremental-20260513-2.md")
            ),
            "0.10.0",
        )
        # date-named / narrative / recent-completed → None
        self.assertIsNone(
            self.archive._version_from_archive_filename(
                Path("completed-tasks-2026-04-30_2026-06-27.md")
            )
        )
        self.assertIsNone(
            self.archive._version_from_archive_filename(
                Path("narrative-2026-04-30_2026-06-27.md")
            )
        )
        self.assertIsNone(
            self.archive._version_from_archive_filename(
                Path("recent-completed-2026-04-30_2026-06-27.md")
            )
        )

    def test_version_to_tuple_handles_non_semver(self):
        """FIX-162: defensive parsing of placeholder versions. Extracts semver
        if present, returns None only when no x.y.z token exists at all."""
        self.assertIsNone(self.archive._version_to_tuple("未规划版本"))
        self.assertIsNone(self.archive._version_to_tuple(""))
        self.assertIsNone(self.archive._version_to_tuple("TBD"))
        self.assertEqual(self.archive._version_to_tuple("0.38.0"), (0, 38, 0))
        # extracts semver from text when one is present
        self.assertEqual(self.archive._version_to_tuple("未规划版本（0.61.0）"), (0, 61, 0))
        self.assertEqual(self.archive._version_to_tuple("release 1.2.3 candidate"), (1, 2, 3))

    def test_version_in_range_handles_none(self):
        self.assertFalse(self.archive._version_in_range("未规划版本", "0.1.0", "0.59.0"))
        self.assertFalse(self.archive._version_in_range("", "0.1.0", "0.59.0"))
        self.assertTrue(self.archive._version_in_range("0.38.0", "0.1.0", "0.59.0"))
        self.assertFalse(self.archive._version_in_range("1.0.0", "0.1.0", "0.59.0"))


class TestArchiveFix235(unittest.TestCase):
    """FIX-235: evidence migration for completed-but-hot plan-tracker tasks.

    plan-tracker keeps completed task rows hot for full traceability
    (EVD-854) instead of physically archiving them; their evidence rows must
    still be archivable by the row's 目标版本. The --auto range advance to
    the frontmatter version (FIX-235) was replaced by FIX-243/DEC-140's
    ledger-bounded cooldown endpoint — see TestArchiveFix243.
    """

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_plan_tracker(self, content):
        (self.gov / "plan-tracker.md").write_text(content, encoding="utf-8")

    def test_fix235_parse_completed_task_versions_tolerates_table_breaks(self):
        """FIX-235: the evidence mapping scans priority tables tolerantly —
        blank lines / blockquote notes inside a table do NOT terminate the
        scan (the real plan-tracker interleaves them), and anomalous pipe
        counts are skipped (column alignment cannot be trusted)."""
        content = "\n".join([
            "## 当前活跃事项",
            "",
            "### 优先级一览",
            "",
            "> 状态漂移清理说明：保留全部历史 task 行。",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "",
            "| **P1** | REL-055 | 发布 0.65.2 | FIX-193 | 0.65.2 | done | ✅ 已发布 |",
            "| **P1** | FIX-192 | lineage gate | SYSGAP-046 | 0.65.3 | done | ✅ 完成 |",
            "| **P0** | SYSGAP-046 | gap | AUDIT-132 | 0.65.3 | open | 🚧 前向门禁完成，历史处置待 DEC |",
            "| **P2** | FEAT-001 | ledger | DEC-096 | 0.66.0 | done | ✅ 完成 |",
            "| **P0** | FIX-222 | malformed | x | 0.72.0 | done | ✅ 完成 | extra | cell |",
            "",
            "### 最近完成",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-084 | task | — | 0.38.0 | done | ✅ 已完成 |",
        ])
        mapping = self.archive._parse_completed_task_versions(content)
        self.assertEqual(mapping.get("REL-055"), "0.65.2")
        self.assertEqual(mapping.get("FIX-192"), "0.65.3")
        self.assertEqual(mapping.get("FEAT-001"), "0.66.0")
        self.assertEqual(mapping.get("FIX-084"), "0.38.0")  # second table scanned
        self.assertNotIn("SYSGAP-046", mapping)  # open status — not completed
        self.assertNotIn("FIX-222", mapping)     # anomalous pipe layout — skipped

    def test_fix235_evidence_migrates_for_hot_completed_tasks(self):
        """FIX-235: the 'task row kept hot, evidence row still hot' scenario.
        Completed tasks in the priority table contribute their 目标版本 to
        the evidence mapping, so in-range evidence rows migrate even when the
        task row is NOT archived in this run (out-of-range hot row FEAT-001
        keeps covering that path after FIX-301). Since FIX-301 the in-range
        completed rows ARE physically archived, which additionally unlocks
        the decision migration through the this-run archive set."""
        plan = "\n".join([
            "## 当前活跃事项",
            "",
            "### 优先级一览",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "",
            "| **P1** | REL-055 | 发布 0.65.2 | FIX-193 | 0.65.2 | done | ✅ 已发布 |",
            "| **P1** | FIX-192 | lineage gate | SYSGAP-046 | 0.65.3 | done | ✅ 完成 |",
            "| **P1** | REL-056 | 发布 0.65.3 | FIX-192 | 0.65.3 | done | ✅ 已发布 |",
            "| **P0** | SYSGAP-046 | gap | AUDIT-132 | 0.65.3 | open | 🚧 前向门禁完成，历史处置待 DEC |",
            "| **P2** | FEAT-001 | ledger | DEC-096 | 0.66.0 | done | ✅ 完成 |",
        ])
        self._write_plan_tracker(plan)
        _make_evidence_log(self.gov, [
            ("EVD-695", "REL-055", "0.65.2 release evidence"),
            ("EVD-696", "REL-055", "0.65.2 release commit evidence"),
            ("EVD-699", "FIX-192", "lineage gate evidence"),
            ("EVD-700", "REL-056", "0.65.3 release evidence"),
            ("EVD-701", "REL-056", "0.65.3 commit evidence"),
            ("EVD-697", "FIX-192, SYSGAP-046", "mixed hot+open — must stay"),
            ("EVD-698", "FEAT-001", "out of range — must stay"),
        ])
        (self.gov / "decision-log.md").write_text(
            "| DEC-200 | 2026-07-01 | 决策标题 | 背景 | 决策 | 备选 | 原因 | 影响 | 决策人 | REL-055 | 后续 |\n",
            encoding="utf-8",
        )
        (self.gov / "risk-log.md").write_text(
            "| RISK-200 | 2026-07-01 | 风险描述 | 中 | 缓解动作 | REL-055 | 打开 |\n",
            encoding="utf-8",
        )

        with patch.object(self.archive, "ROOT", self.root), patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_by_version(
                "0.63.1", "0.65.3", dry_run=False
            )

        # FIX-301 behavior update: in-range completed priority-table rows are
        # now PHYSICALLY archived (real-shape recognition fix). REL-055 /
        # FIX-192 / REL-056 (0.65.2/0.65.3, all ✅) migrate; SYSGAP-046 (open)
        # and FEAT-001 (0.66.0, out of range) stay hot — the out-of-range hot
        # row keeps covering the original FIX-235 semantics below.
        self.assertTrue(result["success"])
        self.assertEqual(result["tasks_archived"], 3)
        self.assertEqual(result["evidence_archived"], 5)  # EVD-695/696/699/700/701
        # DEC-200 references REL-055, which THIS RUN physically archived, so
        # the decision migration unlocks (related task genuinely archived —
        # the FIX-162 contract now holds via the this-run archive set).
        self.assertEqual(result["decisions_archived"], 1)
        self.assertEqual(result["risks_archived"], 0)  # RISK-200 open — stays hot

        kept = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        for evd in ("EVD-695", "EVD-696", "EVD-699", "EVD-700", "EVD-701"):
            self.assertNotIn(evd, kept)
        self.assertIn("EVD-697", kept)  # mixed hot+open ref → kept
        self.assertIn("EVD-698", kept)  # out-of-range ref → kept

        # plan-tracker: archived rows physically removed; open and
        # out-of-range rows preserved. FEAT-001 remains a HOT completed row
        # whose evidence still resolves via the FIX-235 tolerant mapping.
        tracker = (self.gov / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertNotIn("REL-055", tracker)
        self.assertNotIn("FIX-192", tracker)
        self.assertNotIn("REL-056", tracker)
        self.assertIn("SYSGAP-046", tracker)
        self.assertIn("FEAT-001", tracker)

        arch = self.archive_dir / "evidence" / "evidence-v0.63.1-0.65.3.md"
        self.assertTrue(arch.exists())
        arch_content = arch.read_text(encoding="utf-8")
        self.assertIn("| EVD-695 |", arch_content)
        self.assertIn("| EVD-701 |", arch_content)
        self.assertNotIn("EVD-697", arch_content)
        dec_arch = self.archive_dir / "decisions" / "decisions-v0.63.1-0.65.3.md"
        self.assertTrue(dec_arch.exists())
        self.assertIn("DEC-200", dec_arch.read_text(encoding="utf-8"))

    def test_fix235_evidence_dry_run_reports_hot_task_rows(self):
        """FIX-235: dry-run reports the evidence count without writing files —
        the acceptance path for `archive.py migrate <range> --dry-run`."""
        plan = "\n".join([
            "## 当前活跃事项",
            "",
            "### 优先级一览",
            "",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "",
            "| **P1** | REL-055 | 发布 0.65.2 | FIX-193 | 0.65.2 | done | ✅ 已发布 |",
        ])
        self._write_plan_tracker(plan)
        _make_evidence_log(self.gov, [
            ("EVD-695", "REL-055", "0.65.2 release evidence"),
        ])
        with patch.object(self.archive, "ROOT", self.root), patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_by_version(
                "0.63.1", "0.65.3", dry_run=True
            )
        self.assertEqual(result["evidence_archived"], 1)
        self.assertFalse(
            (self.archive_dir / "evidence" / "evidence-v0.63.1-0.65.3.md").exists()
        )
        kept = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("EVD-695", kept)

    def test_fix243_auto_range_no_longer_advances_to_frontmatter(self):
        """FIX-243 (DEC-140 方案 A): without a release ledger the --auto
        range end stays at the roadmap-derived second-newest published row.
        The FIX-235 'advance to SKILL.md frontmatter current version'
        behavior is replaced — it archived the current release window's
        evidence. The frontmatter version (0.13.0) must NOT move the end."""
        skill = self.root / "skills/software-project-governance/SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\nname: test\nversion: 0.13.0\n---\n",
            encoding="utf-8",
        )
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
                ("FIX-002", "已完成", "Fix bug 2", "FIX-001"),
                ("FIX-003", "已完成", "Fix bug 3", "—"),
            ]),
            ("v0.12.0 — Latest roadmap published", [
                ("FIX-004", "已完成", "Fix bug 4", "—"),
            ]),
            ("v0.13.0 — Current", [
                ("FIX-006", "进行中", "Fix bug 6", "—"),
            ]),
        ]
        _make_plan_tracker_with_roadmap(self.gov, roadmap, tasks)
        _make_evidence_log(self.gov, [
            ("EVD-001", "FIX-001", "Fixed bug 1"),
            ("EVD-002", "FIX-002", "Fixed bug 2"),
            ("EVD-003", "FIX-003", "Fixed bug 3"),
            ("EVD-004", "FIX-004", "Fixed bug 4"),
        ])
        _pad_plan_tracker(self.gov)

        with patch.object(self.archive, "ROOT", self.root), patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_auto(dry_run=True)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        # No ledger available → roadmap-derived end (second-newest published
        # row = 0.11.0); the frontmatter 0.13.0 must not extend the range.
        self.assertEqual(result["versions_range"], ("0.10.0", "0.11.0"))
        self.assertIn("0.11.0", result["versions_archived"])
        self.assertNotIn("0.13.0", result["versions_archived"])
        self.assertEqual(result["tasks_archived"], 3)     # FIX-001..003
        self.assertEqual(result["evidence_archived"], 3)  # EVD-001..003


class TestArchiveFix243(unittest.TestCase):
    """FIX-243 (DEC-140 方案 A): --auto endpoint bounded by release ledger.

    The archive range end must be the second-newest released version from
    the release ledger (PLUGIN_ROOT asset — never the host root), keeping
    the newest released version's evidence hot (≥1 release-period cooldown).
    The roadmap derivation remains the advance-only floor: the bounded
    endpoint wins only when it is at least the roadmap-derived end.
    """

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _analyze(self, roadmap):
        """Build a padded plan-tracker + evidence log and run the analysis."""
        _make_plan_tracker_with_roadmap(self.gov, roadmap, [
            ("v0.10.0 — Initial", [
                ("FIX-001", "已完成", "Fix bug 1", "—"),
            ]),
            ("v0.11.0 — Early fixes", [
                ("FIX-002", "已完成", "Fix bug 2", "—"),
            ]),
            ("v0.12.0 — Latest", [
                ("FIX-003", "已完成", "Fix bug 3", "—"),
            ]),
            ("v0.13.0 — Current", [
                ("FIX-004", "进行中", "Fix bug 4", "—"),
            ]),
        ])
        _make_evidence_log(self.gov, [
            ("EVD-001", "FIX-001", "Fixed bug 1"),
            ("EVD-002", "FIX-002", "Fixed bug 2"),
            ("EVD-003", "FIX-003", "Fixed bug 3"),
        ])
        _pad_plan_tracker(self.gov)
        with patch.object(self.archive, "ROOT", self.root), \
             patch.object(self.archive, "PLUGIN_ROOT", self.root):
            return self.archive.analyze_auto_archive_candidates()

    def test_auto_range_uses_ledger_second_newest_endpoint(self):
        """DEC-140: --auto end = second-newest released ledger version; the
        newest released version (0.13.0) stays hot despite being a published
        roadmap row."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
            ("0.13.0", "已发布"),
        ]
        for v in ("0.10.0", "0.11.0", "0.12.0", "0.13.0"):
            _write_release_manifest(self.root, v)
        result = self._analyze(roadmap)

        self.assertTrue(result["success"])
        self.assertFalse(result.get("skipped", False))
        self.assertEqual(result["versions_range"], ("0.10.0", "0.12.0"))
        self.assertEqual(
            result["versions_archived"], ["0.10.0", "0.11.0", "0.12.0"]
        )
        self.assertNotIn("0.13.0", result["versions_archived"])

    def test_auto_range_advances_to_ledger_bound_beyond_roadmap(self):
        """FIX-235 scenario: the roadmap 状态 column lags (0.12.0/0.13.0
        released per ledger but not marked 已发布) — the endpoint still
        advances to the ledger bound, but never past the newest release."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
        ]
        for v in ("0.10.0", "0.11.0", "0.12.0", "0.13.0"):
            _write_release_manifest(self.root, v)
        result = self._analyze(roadmap)

        self.assertEqual(result["versions_range"], ("0.10.0", "0.12.0"))
        self.assertNotIn("0.13.0", result["versions_archived"])

    def test_release_ledger_excludes_withdrawn_manifests(self):
        """0.66.1-style withdrawn manifests (top-level or effective_state)
        never count as released — the bounded endpoint skips them."""
        _write_release_manifest(self.root, "0.10.0")
        _write_release_manifest(self.root, "0.11.0")
        _write_release_manifest(self.root, "0.12.0", withdrawn_effective=True)
        _write_release_manifest(self.root, "0.12.1", withdrawn=True)
        _write_release_manifest(self.root, "0.13.0")
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            released = self.archive._release_ledger_released_versions()
        self.assertEqual(released, ["0.10.0", "0.11.0", "0.13.0"])
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            self.assertEqual(
                self.archive._auto_archive_bounded_endpoint(), "0.11.0"
            )

    def test_auto_range_excludes_withdrawn_ledger_versions(self):
        """End-to-end: 0.12.0 withdrawn → bound stays 0.11.0 → range end is
        0.11.0 (would be 0.12.0 if the withdrawal were ignored)."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        _write_release_manifest(self.root, "0.10.0")
        _write_release_manifest(self.root, "0.11.0")
        _write_release_manifest(self.root, "0.12.0", withdrawn_effective=True)
        _write_release_manifest(self.root, "0.13.0")
        result = self._analyze(roadmap)

        self.assertEqual(result["versions_range"], ("0.10.0", "0.11.0"))
        self.assertNotIn("0.12.0", result["versions_archived"])

    def test_auto_range_falls_back_to_roadmap_end_when_ledger_insufficient(self):
        """Ledger with <2 released versions → roadmap-derived end wins."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        _write_release_manifest(self.root, "0.10.0")  # only one released
        result = self._analyze(roadmap)

        self.assertEqual(result["versions_range"], ("0.10.0", "0.11.0"))

    def test_auto_range_falls_back_when_ledger_dir_absent(self):
        """No ledger at all → plain roadmap derivation."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        result = self._analyze(roadmap)
        self.assertEqual(result["versions_range"], ("0.10.0", "0.11.0"))

    def test_auto_range_never_regresses_below_roadmap_end(self):
        """Advance-only: when the ledger bound is BELOW the roadmap-derived
        end, the roadmap end wins (no regression, per DEC-140 formula)."""
        roadmap = [
            ("0.10.0", "已发布"),
            ("0.11.0", "已发布"),
            ("0.12.0", "已发布"),
        ]
        # Ledger lags roadmap: newest released is 0.11.0 → bound = 0.10.0
        for v in ("0.10.0", "0.11.0"):
            _write_release_manifest(self.root, v)
        result = self._analyze(roadmap)

        # bounded (0.10.0) < roadmap end (0.11.0) → roadmap end wins
        self.assertEqual(result["versions_range"], ("0.10.0", "0.11.0"))

    def test_release_ledger_skips_corrupt_manifests_fail_open(self):
        """A corrupt, non-dict, missing-version or non-released manifest is
        skipped without crashing; remaining manifests still drive the bound."""
        _write_release_manifest(self.root, "0.10.0")
        _write_release_manifest(self.root, "0.11.0", corrupt=True)
        _write_release_manifest(self.root, "0.12.0", missing_version=True)
        _write_release_manifest(self.root, "0.12.1", lifecycle="candidate")
        releases = (
            self.root / "skills" / "software-project-governance"
            / "core" / "releases"
        )
        (releases / "0.12.2.json").write_text("[]", encoding="utf-8")
        _write_release_manifest(self.root, "0.13.0")
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            released = self.archive._release_ledger_released_versions()
        self.assertEqual(released, ["0.10.0", "0.13.0"])
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            self.assertEqual(
                self.archive._auto_archive_bounded_endpoint(), "0.10.0"
            )

    def test_release_ledger_skips_non_string_version_fail_open(self):
        """A manifest whose ``version`` field is not a string (e.g. a number)
        is skipped without crashing — the regex in _version_to_tuple would
        raise TypeError, so the type guard keeps the fail-open contract."""
        _write_release_manifest(self.root, "0.10.0")
        releases = (
            self.root / "skills" / "software-project-governance"
            / "core" / "releases"
        )
        (releases / "0.11.0.json").write_text(json.dumps({
            "artifacts": {},
            "effective_state": {
                "amendments": [],
                "lifecycle_state": "released",
                "withdrawn": False,
            },
            "events": [],
            "lifecycle_state": "released",
            "provenance": "native",
            "schema_version": 1,
            "version": 0.11,  # non-string → must be skipped, not crash
        }), encoding="utf-8")
        _write_release_manifest(self.root, "0.12.0")
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            released = self.archive._release_ledger_released_versions()
        self.assertEqual(released, ["0.10.0", "0.12.0"])
        with patch.object(self.archive, "PLUGIN_ROOT", self.root):
            self.assertEqual(
                self.archive._auto_archive_bounded_endpoint(), "0.10.0"
            )


class TestArchiveFix301(unittest.TestCase):
    """FIX-301 (AUDIT-150 / REFACTOR-archive-recognition-fix): archive
    recognition surface vs the REAL hot-data shapes.

    Real-data diagnostics (2026-09, this repo's .governance) found the dry-run
    reporting "触发器满足（release_forced）但无可归档数据" while plan-tracker
    was 355KB and evidence-log 1446KB. Root causes mirrored here:

      * RC-A: the priority table interleaves blank lines / blockquote notes
        between priority groups; ``_parse_priority_table_tasks`` reset its
        scan state on ANY non-table line, seeing only the FIRST group
        (32 of 208 real rows) → tasks_archived=0 while 88 in-range completed
        rows existed. Its sibling ``_parse_completed_task_versions``
        (FIX-235) already fixed this for the evidence mapping — the two
        parsers had drifted.
      * RC-B (cascade): decisions/risks resolve versions from THIS-RUN
        archived + already-archived tasks only; with this-run empty (RC-A)
        all 134 decision rows reported no_archived_task_ref.
      * RC-C: evidence rows with compound IDs (``EVD-FIX-247`` — evidence
        rows keyed by their task) failed the plain ``EVD-\\d+`` shape check
        and were skipped as unknown (52 real rows).
      * RC-D (deliverable): the dry-run must explain itself — per category
        scanned / parsed / would-archive / retained / unknown-structure plus
        a per-row retention reason (auditable explanation, NOT a black box).
    """

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov / "archive"
        for sub in ["tasks", "evidence", "decisions", "risks"]:
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_plan_tracker(self, content):
        (self.gov / "plan-tracker.md").write_text(content, encoding="utf-8")

    # Real-shape priority table: header + first group, then blank line +
    # blockquote note (priority-group boundary), then the second group.
    _REAL_SHAPE_TABLE = "\n".join([
        "## 当前活跃事项",
        "",
        "### 优先级一览",
        "",
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
        "|--------|----|------|------|---------|---------|------|",
        "| **P0** | FIX-313 | open task | — | 0.76.0 | TBD | ⏳ 进行中 |",
        "| **P0** | REL-999 | out of range | — | 0.99.0 | TBD | ✅ 已完成 |",
        "",
        "> 状态漂移清理说明（真实表组间穿插的 blockquote 注记）。",
        "",
        "| **P1** | FIX-311 | task A | — | 0.76.0 | TBD | ✅ 已完成 |",
        "| **P1** | FIX-312 | task B | FIX-311 | 0.77.0 | TBD | ✅ 已完成 |",
        "| **P2** | BAD-777 | pipe anomaly | x | 0.76.0 | TBD | ✅ 完成 | extra | cell |",
    ])

    def test_fix301_priority_scan_survives_group_breaks(self):
        """RC-A: blank lines / blockquote notes between priority groups must
        NOT terminate the priority-table scan (sibling parser parity with
        FIX-235's _parse_completed_task_versions)."""
        tasks = self.archive._parse_priority_table_tasks(self._REAL_SHAPE_TABLE)
        ids = [t[2] for t in tasks]
        self.assertIn("FIX-313", ids, "first group must be seen")
        self.assertIn("FIX-311", ids, "second group must be seen after blank+quote")
        self.assertIn("FIX-312", ids)
        # Pipe-anomaly rows are NOT trusted for physical migration (column
        # alignment unverifiable) — they surface as unknown structure instead.
        self.assertNotIn("BAD-777", ids)
        # Parser-parity guard: the evidence mapping parser agrees on the
        # archivable rows (the two parsers must not drift again).
        mapping = self.archive._parse_completed_task_versions(self._REAL_SHAPE_TABLE)
        for tid in ("FIX-311", "FIX-312", "REL-999"):
            self.assertIn(tid, mapping)

    def test_fix301_priority_scan_reports_pipe_anomalies(self):
        """RC-A/RC-D: pipe-anomaly rows are collected for the auditable
        unknown-structure list via the optional anomalies_out parameter."""
        anomalies = []
        self.archive._parse_priority_table_tasks(
            self._REAL_SHAPE_TABLE, anomalies_out=anomalies
        )
        anomaly_ids = [a[0] for a in anomalies]
        self.assertIn("BAD-777", anomaly_ids)

    def test_fix301_end_to_end_migration_unlocks_all_categories(self):
        """RC-A + RC-B + RC-C end-to-end: migrating the real-shape table
        physically archives the in-range completed rows across groups and
        unlocks decisions/risks (this-run archive set) and compound-ID
        evidence; open/out-of-range/anomalous rows stay hot with reasons."""
        self._write_plan_tracker(self._REAL_SHAPE_TABLE)
        _make_evidence_log(self.gov, [
            ("EVD-301", "FIX-311", "task A evidence"),
            ("EVD-FIX-312", "FIX-312", "compound-ID evidence"),
            ("EVD-302", "REL-999", "out-of-range evidence — must stay"),
        ])
        (self.gov / "decision-log.md").write_text(
            "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| DEC-301 | 2026-09-09 | 决策标题 | 背景 | 决策 | 备选 | 原因 | 影响 | 用户 | FIX-311 | 后续 |\n",
            encoding="utf-8",
        )
        (self.gov / "risk-log.md").write_text(
            "| 编号 | 日期 | 风险描述 | 影响 | 缓解动作 | 关联任务 | 当前状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| RISK-301 | 2026-09-09 | 风险描述 | 中 | 缓解动作 | FIX-311 | 已关闭 |\n",
            encoding="utf-8",
        )

        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_by_version(
                "0.1.0", "0.80.0", dry_run=False
            )
            self.archive.build_index()
            verify = self.archive.verify_archive_integrity()

        self.assertTrue(result["success"], f"migration failed: {result}")
        self.assertEqual(result["tasks_archived"], 2)
        self.assertEqual(result["decisions_archived"], 1)
        self.assertEqual(result["risks_archived"], 1)
        self.assertEqual(result["evidence_archived"], 2)

        # Hot plan-tracker: archived rows physically removed; open,
        # out-of-range and anomalous rows retained (business reasons, no
        # forced deletion — P7).
        tracker = (self.gov / "plan-tracker.md").read_text(encoding="utf-8")
        self.assertNotIn("FIX-311", tracker)
        self.assertNotIn("FIX-312", tracker)
        self.assertIn("FIX-313", tracker)
        self.assertIn("REL-999", tracker)
        self.assertIn("BAD-777", tracker)

        # Archive bodies carry the migrated rows (FIX-172 guard extended).
        task_files = [
            f for f in (self.archive_dir / "tasks").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(task_files), 1)
        body = task_files[0].read_text(encoding="utf-8")
        self.assertIn("FIX-311", body)
        self.assertIn("FIX-312", body)

        # Compound-ID evidence landed in the archive AND the index (all
        # three ID-shape surfaces in sync — migration, extraction, index).
        ev_arch = (self.archive_dir / "evidence" / "evidence-v0.1.0-0.80.0.md")
        self.assertTrue(ev_arch.exists())
        ev_body = ev_arch.read_text(encoding="utf-8")
        self.assertIn("EVD-FIX-312", ev_body)
        index = (self.archive_dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("EVD-FIX-312", index)
        self.assertIn("DEC-301", index)
        self.assertIn("RISK-301", index)

        # Out-of-range evidence stays hot.
        kept_ev = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        self.assertNotIn("EVD-301", kept_ev)
        self.assertNotIn("EVD-FIX-312", kept_ev)
        self.assertIn("EVD-302", kept_ev)

        self.assertTrue(verify["pass"], f"integrity issues: {verify['issues']}")

    def test_fix301_compound_evd_id_shape_admitted(self):
        """RC-C in isolation: compound evidence IDs (EVD-FIX-101) participate
        in migration, archive extraction and the index — not 'unknown'."""
        # Pre-existing archived task so the evidence mapping resolves.
        (self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md").write_text(
            "# 归档 Task 表 — v0.10.0 ~ v0.10.0\n\n"
            "### v0.10.0 — Initial\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-101 | Fix bug | P1 | — | 0.10.0 | 阿速 | — | Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        self._write_plan_tracker("### 优先级一览\n")
        _make_evidence_log(self.gov, [
            ("EVD-100", "FIX-101", "plain evidence row"),
            ("EVD-FIX-101", "FIX-101", "compound evidence row"),
        ])
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_by_version(
                "0.1.0", "0.20.0", dry_run=False
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["evidence_archived"], 2)
        # Extraction from the archive file sees BOTH rows (index source).
        ev_files = [
            f for f in (self.archive_dir / "evidence").glob("*.md")
            if f.name != ".gitkeep"
        ]
        self.assertEqual(len(ev_files), 1)
        rows = self.archive._extract_evidence_from_archive_file(ev_files[0])
        evd_ids = {r[0] for r in rows}
        self.assertEqual(evd_ids, {"EVD-100", "EVD-FIX-101"})

    def test_fix301_explain_report_structure(self):
        """RC-D: dry-run explain carries, per category, the five auditable
        numbers plus per-row retention reasons and the unknown-structure
        list."""
        self._write_plan_tracker(self._REAL_SHAPE_TABLE)
        _make_evidence_log(self.gov, [
            ("EVD-301", "FIX-311", "task A evidence"),
            ("EVD-302", "REL-999", "out-of-range evidence"),
        ])
        explain = {}
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            result = self.archive.migrate_by_version(
                "0.1.0", "0.80.0", dry_run=True, explain=explain
            )
        self.assertTrue(result["success"])
        for cat in ("tasks", "decisions", "risks", "evidence"):
            self.assertIn(cat, explain, f"missing category: {cat}")
            stats = explain[cat]
            for key in ("scanned", "parsed", "would_archive", "retained",
                        "unknown_structure"):
                self.assertIn(key, stats, f"{cat} missing {key}")
                self.assertIsInstance(stats[key], int)
            self.assertIn("rows", stats)
        # Per-row reasons on the real shapes.
        task_rows = {r["id"]: r["reason"] for r in explain["tasks"]["rows"]}
        self.assertEqual(task_rows.get("FIX-311"), "would_archive")
        self.assertEqual(task_rows.get("FIX-313"), "status_not_archivable")
        self.assertEqual(task_rows.get("REL-999"), "out_of_range_version")
        self.assertEqual(task_rows.get("BAD-777"), "pipe_layout_anomaly")
        self.assertEqual(explain["tasks"]["unknown_structure"], 1)
        self.assertIn("BAD-777", explain["tasks"]["unknown_ids"])
        evd_rows = {r["id"]: r["reason"] for r in explain["evidence"]["rows"]}
        self.assertEqual(evd_rows.get("EVD-301"), "would_archive")
        self.assertEqual(evd_rows.get("EVD-302"), "ref_version_out_of_range")
        self.assertEqual(
            explain["decisions"]["rows"], [],
            "no decision-log rows in this fixture",
        )

    def test_fix301_bold_id_cells_extract_from_archive_file(self):
        """FIX-301 (found by the temp-copy conservation check): real hot rows
        may bold the ID cell itself ('| **P1** | **REL-071** | ...'). The
        migration parser strips the bold, so the archive-file extraction must
        tolerate it too — otherwise already_archived and the index go blind
        for those IDs (88 migrated, 87 extracted)."""
        f = self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md"
        f.write_text(
            "# 归档 Task 表 — v0.10.0 ~ v0.10.0\n\n"
            "### v0.10.0\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| **P1** | **REL-071** | bolded id row | — | 0.10.0 | done | ✅ 已发布 |\n"
            "| **P1** | FIX-101 | plain id row | — | 0.10.0 | done | ✅ 已完成 |\n",
            encoding="utf-8",
        )
        rows = self.archive._extract_tasks_from_archive_file(f)
        ids = {t for t, _s, _v in rows}
        self.assertIn("REL-071", ids, "bolded ID cell must be extracted")
        self.assertIn("FIX-101", ids)
        # and already-archived detection sees it (no re-migration risk)
        with patch.object(self.archive, "ROOT", self.root):
            self.assertIn("REL-071", self.archive._get_archived_task_ids())

    def test_fix301_cli_auto_dry_run_renders_explanation_when_skipped(self):
        """RC-D acceptance path: `migrate --auto --dry-run` with triggers
        satisfied but nothing archivable must render the auditable
        explanation (the FIX-301 black-box scenario), not a bare skip line."""
        # Pre-existing index + archive file (release_forced trigger fires).
        (self.archive_dir / "tasks" / "v0.10.0~v0.10.0.md").write_text(
            "# 归档 Task 表 — v0.10.0 ~ v0.10.0\n\n"
            "### v0.10.0 — Initial\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | Fix bug 1 | P1 | — | 1.0.0 | 阿速 | — | Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        (self.archive_dir / "index.md").write_text(
            "# 归档索引\n\n## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-001 | 已完成 | 0.10.0 | archive/tasks/v0.10.0~v0.10.0.md |\n",
            encoding="utf-8",
        )
        _make_plan_tracker_with_roadmap(
            self.gov,
            [("0.10.0", "已发布"), ("0.11.0", "已发布")],
            [
                ("v0.10.0 — Initial", [("FIX-001", "已完成", "Fix bug 1", "—")]),
                ("v0.11.0 — Latest", [("FIX-002", "进行中", "Fix bug 2", "—")]),
            ],
        )
        buf = io.StringIO()
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            with contextlib.redirect_stdout(buf):
                self.archive.main(["migrate", "--auto", "--dry-run"])
        out = buf.getvalue()
        self.assertIn("无可归档数据", out)  # honest skip reason retained
        self.assertIn("归档可审计解释", out)  # FIX-301 explanation section
        for cat_label in ("tasks", "decisions", "risks", "evidence"):
            self.assertIn(cat_label, out)


class TestDualRootResolution(unittest.TestCase):
    """FIX-242: archive.py dual-root model.

    Host governance facts (.governance/**) must resolve to the host project
    (cwd via resolve_entry / --project-root), never to the plugin cache's
    phantom .governance copy; the SKILL.md version read stays on the plugin
    root. ``ROOT`` remains the runtime host-facts seam: verify_workflow.py
    rebinds ``module.ROOT`` and ``module.HOST_PROJECT_ROOT`` in
    _load_archive_module (FIX-187 / FIX-242 P3-3), tests patch it, and
    --project-root rebinds it.
    """

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_host_root_defaults_to_cwd_via_resolve_entry(self):
        """resolve_host_root(None) is cwd-first: without --project-root the
        host facts root is the current working directory (FIX-242)."""
        old_cwd = os.getcwd()
        try:
            os.chdir(self.root)
            host = self.archive._resolve_host_root()
            self.assertEqual(host, Path(self.root).resolve())
        finally:
            os.chdir(old_cwd)

    def test_host_root_falls_back_to_legacy_root_when_resolve_fails(self):
        """resolve_entry failure -> legacy parents[3] root (dogfood compat)."""
        with patch("resolve_entry.resolve_host_root",
                   side_effect=RuntimeError("resolve failed")):
            self.assertEqual(
                self.archive._resolve_host_root(), self.archive._LEGACY_ROOT
            )

    def test_plugin_root_resolves_from_resolve_entry_plugin_home(self):
        """PLUGIN_ROOT mirrors verify_workflow FIX-187: resolve_entry.PLUGIN_HOME
        -> parents[2] of infra/."""
        fake_plugin_home = (
            self.root / "pkg" / "skills" / "software-project-governance"
        )
        with patch("resolve_entry.PLUGIN_HOME", str(fake_plugin_home)):
            self.assertEqual(
                self.archive._resolve_plugin_root(),
                fake_plugin_home.parent.parent,
            )

    def test_plugin_root_falls_back_to_legacy_root_when_resolve_unavailable(self):
        """resolve_entry import failure -> legacy parents[3] root."""
        with patch.dict(sys.modules, {"resolve_entry": None}):
            self.assertEqual(
                self.archive._resolve_plugin_root(), self.archive._LEGACY_ROOT
            )

    def test_gov_dir_default_follows_host_root(self):
        """At import time ROOT == HOST_PROJECT_ROOT (cwd-derived), so
        _gov_dir() points at the host .governance, not the plugin cache."""
        self.assertEqual(self.archive.ROOT, self.archive.HOST_PROJECT_ROOT)
        self.assertEqual(
            self.archive._gov_dir(),
            self.archive.HOST_PROJECT_ROOT / ".governance",
        )

    def test_legacy_root_patch_seam_controls_host_facts(self):
        """Backward compat: patching archive.ROOT (the verify_workflow
        _load_archive_module rebind seam) redirects all host facts."""
        with patch.object(self.archive, "ROOT", self.root), patch.object(self.archive, "PLUGIN_ROOT", self.root):
            self.assertEqual(
                self.archive._gov_dir(), self.root / ".governance"
            )
            self.assertEqual(
                self.archive._archive_dir(),
                self.root / ".governance" / "archive",
            )
            self.assertEqual(
                self.archive._index_path(),
                self.root / ".governance" / "archive" / "index.md",
            )
            self.assertEqual(
                self.archive._plan_tracker(),
                self.root / ".governance" / "plan-tracker.md",
            )
            self.assertEqual(
                self.archive._evidence_log(),
                self.root / ".governance" / "evidence-log.md",
            )
            self.assertEqual(
                self.archive._decision_log(),
                self.root / ".governance" / "decision-log.md",
            )
            self.assertEqual(
                self.archive._risk_log(),
                self.root / ".governance" / "risk-log.md",
            )

    def test_project_root_override_rebinds_host_facts_only(self):
        """--project-root rebinds host facts; PLUGIN_ROOT is never moved."""
        orig_root = self.archive.ROOT
        orig_host = self.archive.HOST_PROJECT_ROOT
        orig_plugin = self.archive.PLUGIN_ROOT
        try:
            self.archive._apply_project_root_override(str(self.root))
            host = Path(self.root).resolve()
            self.assertEqual(self.archive.ROOT, host)
            self.assertEqual(self.archive.HOST_PROJECT_ROOT, host)
            self.assertEqual(self.archive._gov_dir(), host / ".governance")
            self.assertEqual(
                self.archive._plan_tracker(),
                host / ".governance" / "plan-tracker.md",
            )
            self.assertEqual(
                self.archive._archive_dir(), host / ".governance" / "archive"
            )
            self.assertEqual(self.archive.PLUGIN_ROOT, orig_plugin)
        finally:
            self.archive.ROOT = orig_root
            self.archive.HOST_PROJECT_ROOT = orig_host

    def test_latest_released_version_reads_plugin_root_not_host(self):
        """SKILL.md frontmatter version read is plugin-rooted (FIX-242): a
        host root without the skill tree must not affect the version."""
        orig_plugin = self.archive.PLUGIN_ROOT
        orig_root = self.archive.ROOT
        orig_host = self.archive.HOST_PROJECT_ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                plugin = Path(td) / "plugin"
                skill = plugin / "skills" / "software-project-governance" / "SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(
                    "---\nname: spg\nversion: 9.9.9\n---\n",
                    encoding="utf-8",
                )
                host = Path(td) / "host"
                host.mkdir()
                self.archive.PLUGIN_ROOT = plugin
                self.archive.ROOT = host
                self.archive.HOST_PROJECT_ROOT = host
                self.assertEqual(
                    self.archive._latest_released_version(), "9.9.9"
                )
        finally:
            self.archive.PLUGIN_ROOT = orig_plugin
            self.archive.ROOT = orig_root
            self.archive.HOST_PROJECT_ROOT = orig_host

    def test_extract_project_root_arg_position_independent(self):
        """--project-root is accepted before or after the subcommand."""
        self.assertEqual(
            self.archive._extract_project_root_arg(
                ["migrate", "--project-root", "X", "--dry-run"]
            ),
            ("X", ["migrate", "--dry-run"]),
        )
        self.assertEqual(
            self.archive._extract_project_root_arg(["--project-root=X", "verify"]),
            ("X", ["verify"]),
        )
        self.assertEqual(
            self.archive._extract_project_root_arg(["migrate", "--dry-run"]),
            (None, ["migrate", "--dry-run"]),
        )
        with self.assertRaises(ValueError):
            self.archive._extract_project_root_arg(["migrate", "--project-root"])


class TestArchiveCliProjectRoot(unittest.TestCase):
    """FIX-242: archive.py CLI --project-root targets the host project."""

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self._orig_root = archive.ROOT
        self._orig_host = archive.HOST_PROJECT_ROOT
        self._orig_plugin = archive.PLUGIN_ROOT

    def tearDown(self):
        self.archive.ROOT = self._orig_root
        self.archive.HOST_PROJECT_ROOT = self._orig_host
        self.archive.PLUGIN_ROOT = self._orig_plugin
        self.tempdir.cleanup()

    def test_cli_verify_project_root_after_subcommand(self):
        """`archive.py verify --project-root <host>` reads HOST facts: the
        index ghost-reference is reported from the host fixture."""
        tasks_dir = self.gov / "archive" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (self.gov / "archive" / "index.md").write_text(
            "# 归档索引\n\n"
            "## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-001 | 已完成 | 0.10.0 | archive/tasks/ghost.md |\n",
            encoding="utf-8",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["verify", "--project-root", str(self.root)])
        self.assertEqual(ctx.exception.code, 1)
        printed = out.getvalue()
        self.assertIn("Pass: False", printed)
        self.assertIn("ghost.md", printed)
        # Host fixture archive dir was read, not created/modified.
        self.assertFalse(tasks_dir.joinpath("ghost.md").exists())

    def test_cli_verify_project_root_before_subcommand(self):
        """`archive.py --project-root <host> verify` (global position)."""
        (self.gov / "archive" / "tasks").mkdir(parents=True, exist_ok=True)
        (self.gov / "archive" / "index.md").write_text(
            "# 归档索引\n\n"
            "## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-001 | 已完成 | 0.10.0 | archive/tasks/ghost.md |\n",
            encoding="utf-8",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["--project-root", str(self.root), "verify"])
        self.assertEqual(ctx.exception.code, 1)
        printed = out.getvalue()
        self.assertIn("Pass: False", printed)
        self.assertIn("ghost.md", printed)

    def test_cli_migrate_auto_dry_run_targets_host(self):
        """`archive.py migrate --auto --dry-run --project-root <host>` runs
        the auto analysis on the host fixture (skipped: no triggers) instead
        of the plugin cache."""
        (self.gov / "plan-tracker.md").write_text(
            "# 当前项目样例\n\n"
            "## 版本规划\n\n"
            "### 版本路线图\n\n"
            "| 版本 | 状态 | 日期 |\n"
            "| --- | --- | --- |\n"
            "| 0.10.0 | 已发布 | 2026-01-01 |\n"
            "| 0.11.0 | 已发布 | 2026-02-01 |\n\n"
            "### v0.10.0 — Old\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-001 | fix | P1 | — | 0.10.0 | a | — | Code Reviewer | TBD | 已完成 |\n",
            encoding="utf-8",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.archive.main(
                ["migrate", "--auto", "--dry-run", "--project-root", str(self.root)]
            )
        printed = out.getvalue()
        self.assertIn("治理数据归档", printed)
        # Dry-run must not create the host archive index.
        self.assertFalse((self.gov / "archive" / "index.md").exists())

    def test_cli_project_root_missing_value_errors(self):
        """`--project-root` without a value exits 2 with a clear message."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["verify", "--project-root"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--project-root requires a path", err.getvalue())

    def test_cli_project_root_nonexistent_path_fails_closed(self):
        """FIX-244 P2-1: an explicit --project-root that does not exist
        exits 2 with a classified diagnostic — no phantom-root rebind."""
        missing = self.root / "does-not-exist"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["verify", "--project-root", str(missing)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("spg-archive-error: invalid-project-root", err.getvalue())
        self.assertIn(str(missing), err.getvalue())
        # FIX-244 R0 P2-2: the classified error reason suffix is contract.
        self.assertIn("path does not exist", err.getvalue())
        # ROOT must NOT be rebound to the phantom path.
        self.assertEqual(self.archive.ROOT, self._orig_root)
        self.assertEqual(self.archive.HOST_PROJECT_ROOT, self._orig_host)

    def test_cli_project_root_file_path_fails_closed(self):
        """FIX-244 P2-1: --project-root pointing at a file (not a
        directory) exits 2 with the same classified diagnostic."""
        some_file = self.root / "plain.txt"
        some_file.write_text("not a directory", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["verify", "--project-root", str(some_file)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("spg-archive-error: invalid-project-root", err.getvalue())
        # FIX-244 R0 P2-2: the classified error reason suffix is contract.
        self.assertIn("not a directory", err.getvalue())
        # FIX-244 R0 P2-1: HOST_PROJECT_ROOT must NOT be rebound either —
        # guard against a future split of the ROOT/HOST assignment.
        self.assertEqual(self.archive.ROOT, self._orig_root)
        self.assertEqual(self.archive.HOST_PROJECT_ROOT, self._orig_host)

    def test_cli_project_root_empty_value_fails_closed(self):
        """FIX-244 P3-4: `--project-root=` (empty string) exits 2 — must
        not silently resolve to the current working directory."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["verify", "--project-root="])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("spg-archive-error: invalid-project-root", err.getvalue())
        # FIX-244 R0 P2-2: the classified error reason suffix is contract.
        self.assertIn("path is empty", err.getvalue())
        # FIX-244 R0 P2-1: HOST_PROJECT_ROOT must NOT be rebound either —
        # guard against a future split of the ROOT/HOST assignment.
        self.assertEqual(self.archive.ROOT, self._orig_root)
        self.assertEqual(self.archive.HOST_PROJECT_ROOT, self._orig_host)


# ────────────────────────────────────────────────────────────
# FIX-385 (B-7b) fixture helpers
# ────────────────────────────────────────────────────────────

def _make_big_table_world(governance_dir, evidence_count=57):
    """FIX-385 fixture: a row-heavy evidence-log + the plan-tracker priority
    table that resolves the FIX-235 completed-hot task mapping.

    Deterministic content: the same world can be rebuilt byte-identically
    (crash/resume tests reset between runs). Evidence rows referencing
    FIX-900 (live task, 进行中) are retained; rows referencing FIX-101/102
    (completed, 目标版本 0.60.0) migrate in the 0.60.0~0.61.0 range.
    """
    plan_lines = [
        "# 当前项目样例",
        "",
        "## 项目配置",
        "- **工作流版本**: 0.88.0",
        "",
        "### 优先级一览",
        "",
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| **P2** | FIX-101 | task one | — | 0.60.0 | TBD | ✅ 已完成 |",
        "| **P2** | FIX-102 | task two | FIX-101 | 0.60.0 | TBD | ✅ 已完成 |",
        "| **P2** | FIX-103 | task three | — | 0.61.0 | TBD | ✅ 已完成 |",
        "| **P1** | FIX-900 | live task | — | 0.88.0 | TBD | 进行中 |",
        "",
    ]
    (governance_dir / "plan-tracker.md").write_text(
        "\n".join(plan_lines), encoding="utf-8")

    evd_lines = [
        "# 证据记录",
        "",
        "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i in range(1, evidence_count + 1):
        task = "FIX-900" if i % 17 == 0 else ("FIX-101" if i % 2 else "FIX-102")
        evd_lines.append(
            f"| EVD-{i:03d} | {task} | evidence row {i} | 2026-09-24 | 代码 | "
            f"src/ | 阿速 | 老赵 | 通过 | — |"
        )
    (governance_dir / "evidence-log.md").write_text(
        "\n".join(evd_lines) + "\n", encoding="utf-8")


def _make_decision_log_legacy_rows(governance_dir, entries):
    """FIX-385 fixture: decision-log in the 11-column legacy schema with a
    关联任务 column, so decisions are migratable in the md world."""
    lines = [
        "# 决策记录",
        "",
        "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for dec_id, title, related in entries:
        lines.append(
            f"| {dec_id} | 2026-09-01 | {title} | ctx | content | alt | why | "
            f"scope | 阿速 | {related} | follow |"
        )
    (governance_dir / "decision-log.md").write_text(
        "\n".join(lines), encoding="utf-8")


class TestBigTableResumableMigration(unittest.TestCase):
    """FIX-385 (B-7b): batched, journaled, resumable big-table migration
    (evidence → archive) with FEAT-060/061 crash-recovery semantics.

    Crash injection uses mock.patch on the engine's own write primitives —
    no product test hooks. Each crash window mirrors a real interruption:
      - staging crash     → resume continues at the batch cursor
      - commit crash      (archive written, hot not rewritten) → resume
                            completes the hot leg without duplicating data
      - finalize crash    (hot rewritten, journal unfinalized) → resume
                            finalizes only
      - hot divergence    (concurrent writer mid-migration) → loud refusal
    """

    RANGE = ("0.60.0", "0.61.0")
    MIGRATABLE = 54  # 57 rows − 3 FIX-900-referencing rows retained

    def setUp(self):
        import archive
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ("tasks", "evidence", "decisions", "risks"):
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    # ── helpers ──

    @contextlib.contextmanager
    def _patched_root(self):
        with patch.object(self.archive, "ROOT", self.root), \
             patch.object(self.archive, "PLUGIN_ROOT", self.root):
            yield

    def _reset_world(self):
        """Rebuild the pristine deterministic world (clears archive + state)."""
        import shutil
        _make_big_table_world(self.gov_dir)
        for f in (self.archive_dir / "evidence").glob("*.md"):
            f.unlink()
        mig = self.archive_dir / ".migration"
        if mig.exists():
            shutil.rmtree(mig)

    def _hot_text(self):
        return (self.gov_dir / "evidence-log.md").read_text(encoding="utf-8")

    def _hot_rows(self):
        return self._hot_text().count("| EVD-")

    def _journal_path(self):
        return self.archive._migration_journal_path("evidence", *self.RANGE)

    def _journal(self):
        jp = self._journal_path()
        if not jp.is_file():
            return None
        return json.loads(jp.read_text(encoding="utf-8"))

    def _archive_files(self):
        return sorted(p.name for p in (self.archive_dir / "evidence").glob("*.md"))

    def _archive_text(self, name):
        return (self.archive_dir / "evidence" / name).read_text(encoding="utf-8")

    def _assert_conservation(self):
        """Every original EVD id appears EXACTLY once across hot + archive."""
        import re
        ids = re.findall(r"\| (EVD-\d+) \|", self._hot_text())
        for name in self._archive_files():
            ids.extend(re.findall(r"\| (EVD-\d+) \|", self._archive_text(name)))
        self.assertEqual(sorted(ids),
                         [f"EVD-{i:03d}" for i in range(1, 58)])

    def _terminal_state_reference(self):
        """One-shot _migrate_evidence terminal state on a pristine world:
        returns (hot_text, archive_text) as the equivalence reference."""
        self._reset_world()
        mapping = {"FIX-101": "0.60.0", "FIX-102": "0.60.0",
                   "FIX-103": "0.61.0"}
        with self._patched_root():
            count = self.archive._migrate_evidence(
                self.RANGE[0], self.RANGE[1], mapping, dry_run=False)
        self.assertEqual(count, self.MIGRATABLE)
        hot = self._hot_text()
        files = self._archive_files()
        self.assertEqual(files, ["evidence-v0.60.0-0.61.0.md"])
        return hot, self._archive_text(files[0])

    # ── core equivalence (终态等价一次性迁移) ──

    def test_resume_terminal_state_equivalent_to_one_shot(self):
        ref_hot, ref_arc = self._terminal_state_reference()
        self._reset_world()
        with self._patched_root():
            result = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertTrue(result["success"])
        self.assertEqual(result["migrated"], self.MIGRATABLE)
        self.assertFalse(result["resumed"])
        self.assertEqual(result["batches_total"], 6)
        self.assertEqual(self._hot_text(), ref_hot)
        files = self._archive_files()
        self.assertEqual(files, ["evidence-v0.60.0-0.61.0.md"])
        self.assertEqual(self._archive_text(files[0]), ref_arc)
        self._assert_conservation()

    # ── crash window: staging (断点续迁 cursor) ──

    def test_stage_crash_resume_skips_completed_batches(self):
        ref_hot, ref_arc = self._terminal_state_reference()
        self._reset_world()
        real_stage = self.archive._migration_write_batch
        calls = {"n": 0}

        def crashing(batches_dir, batch_index, rows):
            calls["n"] += 1
            if calls["n"] > 3:
                raise OSError("simulated crash after 3 staged batches")
            return real_stage(batches_dir, batch_index, rows)

        with self._patched_root():
            with patch.object(self.archive, "_migration_write_batch",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            # crash state: cursor at 3, hot table untouched, no archive file
            journal = self._journal()
            self.assertEqual(journal["batches_staged"], 3)
            self.assertEqual(journal["phase"], "staging")
            self.assertEqual(self._hot_rows(), 57)
            self.assertEqual(self._archive_files(), [])
            # resume: only the REMAINING batches are staged (cursor honored,
            # no restart from batch 0)
            staged = {"n": 0}

            def counting(batches_dir, batch_index, rows):
                staged["n"] += 1
                return real_stage(batches_dir, batch_index, rows)

            with patch.object(self.archive, "_migration_write_batch",
                              side_effect=counting):
                result = self.archive.migrate_evidence_resumable(
                    self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertTrue(result["success"])
        self.assertTrue(result["resumed"])
        self.assertEqual(result["migrated"], self.MIGRATABLE)
        self.assertEqual(staged["n"], 3)  # 6 batches total, 3 already staged
        self.assertEqual(self._hot_text(), ref_hot)
        files = self._archive_files()
        self.assertEqual(self._archive_text(files[0]), ref_arc)
        self._assert_conservation()

    # ── crash window: commit (archive written, hot NOT rewritten) ──

    def test_commit_crash_after_archive_write_resume_completes(self):
        ref_hot, ref_arc = self._terminal_state_reference()
        self._reset_world()
        real_atomic = self.archive._atomic_write_text

        def crashing(path, text):
            if Path(path).name == "evidence-log.md":
                raise OSError("simulated crash before hot rewrite")
            return real_atomic(path, text)

        with self._patched_root():
            with patch.object(self.archive, "_atomic_write_text",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            # the exact window the one-shot path cannot recover from:
            # archive file written, hot table NOT rewritten
            files = self._archive_files()
            self.assertEqual(len(files), 1)
            self.assertIn("| EVD-001 |", self._archive_text(files[0]))
            self.assertEqual(self._hot_rows(), 57)
            # resume: completes the hot rewrite WITHOUT duplicating the archive
            result = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertTrue(result["success"])
        self.assertTrue(result["resumed"])
        self.assertEqual(self._archive_files(), files)  # still exactly one
        self.assertEqual(self._hot_text(), ref_hot)
        self.assertEqual(self._archive_text(files[0]), ref_arc)
        self._assert_conservation()

    # ── crash window: finalize (hot rewritten, journal unfinalized) ──

    def test_finalize_crash_resume_completes(self):
        ref_hot, ref_arc = self._terminal_state_reference()
        self._reset_world()
        real_journal = self.archive._migration_write_journal

        def crashing(journal_path, doc):
            if doc.get("phase") == "finalized":
                raise OSError("simulated crash before finalize")
            return real_journal(journal_path, doc)

        with self._patched_root():
            with patch.object(self.archive, "_migration_write_journal",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            # hot already rewritten, journal stuck at commit_intent
            self.assertEqual(self._hot_rows(), 3)
            self.assertEqual(self._journal()["phase"], "commit_intent")
            result = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertTrue(result["success"])
        self.assertTrue(result["resumed"])
        self.assertEqual(self._hot_text(), ref_hot)
        self._assert_conservation()

    # ── divergence (concurrent writer mid-migration) ──

    def test_resume_refuses_loudly_on_hot_divergence(self):
        self._reset_world()
        real_stage = self.archive._migration_write_batch
        calls = {"n": 0}

        def crashing(batches_dir, batch_index, rows):
            calls["n"] += 1
            if calls["n"] > 2:
                raise OSError("simulated crash after 2 staged batches")
            return real_stage(batches_dir, batch_index, rows)

        with self._patched_root():
            with patch.object(self.archive, "_migration_write_batch",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            # a concurrent writer appends a row mid-migration
            hot = self.gov_dir / "evidence-log.md"
            hot.write_text(
                self._hot_text().rstrip("\n") + "\n"
                "| EVD-058 | FIX-900 | late arrival | 2026-09-25 | 代码 | "
                "src/ | 阿速 | 老赵 | 通过 | — |\n",
                encoding="utf-8")
            with self.assertRaises(self.archive.BigTableMigrationError) as ctx:
                self.archive.migrate_evidence_resumable(
                    self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertEqual(ctx.exception.payload["code"], "hot_table_diverged")
        # nothing was migrated behind the operator's back
        self.assertEqual(self._hot_rows(), 58)
        self.assertEqual(self._archive_files(), [])

    def test_cursor_ahead_of_staged_artifacts_refuses(self):
        self._reset_world()
        real_stage = self.archive._migration_write_batch
        calls = {"n": 0}

        def crashing(batches_dir, batch_index, rows):
            calls["n"] += 1
            if calls["n"] > 3:
                raise OSError("simulated crash")
            return real_stage(batches_dir, batch_index, rows)

        with self._patched_root():
            with patch.object(self.archive, "_migration_write_batch",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            # tamper: a staged batch disappears while the cursor claims it
            (self._journal_path().parent / "batches"
             / "batch-000001.json").unlink()
            with self.assertRaises(
                    self.archive.BigTableMigrationError) as ctx:
                self.archive.migrate_evidence_resumable(
                    self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertEqual(ctx.exception.payload["code"],
                         "migration_cursor_ahead_of_artifacts")

    # ── operational modes ──

    def test_dry_run_zero_writes(self):
        self._reset_world()
        with self._patched_root():
            result = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["migrated"], self.MIGRATABLE)
        self.assertFalse((self.archive_dir / ".migration").exists())
        self.assertEqual(self._archive_files(), [])
        self.assertEqual(self._hot_rows(), 57)

    def test_dry_run_on_resumed_world_zero_writes(self):
        """FIX-385: dry-run honors zero-write even when a resumable journal
        exists — a resumed-world dry-run must never stage/commit/apply."""
        self._reset_world()
        real_stage = self.archive._migration_write_batch
        calls = {"n": 0}

        def crashing(batches_dir, batch_index, rows):
            calls["n"] += 1
            if calls["n"] > 2:
                raise OSError("simulated crash after 2 staged batches")
            return real_stage(batches_dir, batch_index, rows)

        with self._patched_root():
            with patch.object(self.archive, "_migration_write_batch",
                              side_effect=crashing):
                with self.assertRaises(OSError):
                    self.archive.migrate_evidence_resumable(
                        self.RANGE[0], self.RANGE[1], batch_size=10)
            hot_before = self._hot_text()
            result = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10, dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertTrue(result["resumed"])
            self.assertEqual(result["migrated"], self.MIGRATABLE)
            # zero writes: hot unchanged, no archive file, journal untouched
            self.assertEqual(self._hot_text(), hot_before)
            self.assertEqual(self._archive_files(), [])
            self.assertEqual(self._journal()["batches_staged"], 2)
            self.assertEqual(self._journal()["phase"], "staging")

    def test_nothing_to_migrate_creates_no_journal(self):
        self._reset_world()
        with self._patched_root():
            result = self.archive.migrate_evidence_resumable(
                "0.80.0", "0.81.0", batch_size=10)
        self.assertTrue(result["success"])
        self.assertEqual(result["migrated"], 0)
        self.assertFalse((self.archive_dir / ".migration").exists())

    def test_second_run_after_finalize_is_idempotent_noop(self):
        self._reset_world()
        with self._patched_root():
            self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10)
            hot_after_first = self._hot_text()
            files_after_first = self._archive_files()
            second = self.archive.migrate_evidence_resumable(
                self.RANGE[0], self.RANGE[1], batch_size=10)
        self.assertEqual(second["resumed"], "already_finalized")
        self.assertEqual(second["migrated"], self.MIGRATABLE)
        self.assertEqual(self._hot_text(), hot_after_first)
        self.assertEqual(self._archive_files(), files_after_first)

    # ── CLI smoke ──

    def test_cli_migrate_big_table_smoke(self):
        self._reset_world()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.archive.main(["migrate-big-table", "evidence", "0.60.0",
                               "0.61.0", "--batch-size", "10",
                               "--project-root", str(self.root)])
        self.assertIn("Migrated rows: 54", out.getvalue())
        self.assertEqual(len(self._archive_files()), 1)

    def test_cli_migrate_big_table_refusal_exits_1(self):
        self._reset_world()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
             self.assertRaises(SystemExit) as ctx:
            self.archive.main(["migrate-big-table", "evidence", "0.60.0",
                               "0.61.0", "--batch-size", "0",
                               "--project-root", str(self.root)])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("REFUSED", out.getvalue())


class TestDecisionStoreAuthorityInterface(unittest.TestCase):
    """FIX-385 衔接面: the archive migration mechanism vs the FEAT-061
    storage-separation architecture.

    A non-MD_ACTIVE decision-store authority must NEVER let the migration
    rewrite the decision-log projection (fail-closed loud refusal, recorded
    as a deferral on the run result); the other tables migrate normally and
    the resumable evidence path is unaffected.
    """

    def setUp(self):
        import archive
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.gov_dir = self.root / ".governance"
        self.gov_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = self.gov_dir / "archive"
        for sub in ("tasks", "evidence", "decisions", "risks"):
            (self.archive_dir / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()

    @contextlib.contextmanager
    def _patched_root(self):
        with patch.object(self.archive, "ROOT", self.root), \
             patch.object(self.archive, "PLUGIN_ROOT", self.root):
            yield

    def _world(self):
        _make_big_table_world(self.gov_dir)
        _make_decision_log_legacy_rows(self.gov_dir, [
            ("DEC-501", "decision one", "FIX-101"),
            ("DEC-502", "decision two", "FIX-900"),
        ])

    def _write_archived_tasks(self):
        (self.archive_dir / "tasks" / "v0.60.0~v0.61.0.md").write_text(
            "# 归档 Task 表 — v0.60.0 ~ v0.61.0\n"
            "- **归档日期**: 2026-09-24\n"
            "- **归档范围**: plan-tracker.md 中 0.60.0~0.61.0 版本的所有 tasks\n"
            "- **条目数**: 2\n"
            "- **上一个归档文件**: 无\n"
            "- **下一个归档文件**: 无\n"
            "\n"
            "### v0.60.0\n"
            "| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | "
            "审查类型 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| FIX-101 | task one | P2 | — | 0.60.0 | 阿速 | — | "
            "Code Reviewer | TBD | 已完成 |\n"
            "| FIX-102 | task two | P2 | FIX-101 | 0.60.0 | 阿速 | — | "
            "Code Reviewer | TBD | 已完成 |\n",
            encoding="utf-8")

    def _write_authority_marker(self, state="JSON_ACTIVE", backend="json",
                                raw=None):
        marker = self.gov_dir / ".decision-store-state.json"
        if raw is not None:
            marker.write_text(raw, encoding="utf-8")
            return marker
        marker.write_text(json.dumps(self._authority_marker_doc(state, backend),
                                     ensure_ascii=False), encoding="utf-8")
        return marker

    @staticmethod
    def _authority_marker_doc(state="JSON_ACTIVE", backend="json"):
        return {
            "schema_version": 1, "state": state, "backend": backend,
            "epoch": 1, "generation": 1, "manifest_digest": None,
            "migration_id": None, "owner_token": None,
            "content_digest": None, "frozen": None, "history": [],
        }

    def _concurrent_cutover_state_probe(self, marker):
        """REVIEW-FIX-385-R0 F-1: a state probe that simulates the concurrent
        cutover committing JSON_ACTIVE between the migration's ENTRY gate
        (call 1) and its IN-LOCK re-check (call 2) — the TOCTOU window."""
        real_state = self.archive._decision_authority_state
        calls = {"n": 0}

        def flipping_state():
            calls["n"] += 1
            if calls["n"] >= 2:
                marker.write_text(json.dumps(
                    self._authority_marker_doc(), ensure_ascii=False),
                    encoding="utf-8")
            return real_state()

        return flipping_state

    def test_concurrent_cutover_into_window_refuses_rewrite_in_lock(self):
        """REVIEW-FIX-385-R0 F-1: the authority flips between the entry gate
        and the projection rewrite — the IN-LOCK re-check refuses with ZERO
        writes (the projection is never rewritten with authority posture)."""
        self._world()
        self._write_archived_tasks()
        marker = self.gov_dir / ".decision-store-state.json"
        with self._patched_root():
            with patch.object(self.archive, "_decision_authority_state",
                              side_effect=self._concurrent_cutover_state_probe(
                                  marker)):
                with self.assertRaises(
                        self.archive.DecisionStoreAuthorityConflict) as ctx:
                    self.archive._migrate_decisions(
                        "0.60.0", "0.61.0", {"FIX-101": "0.60.0"})
        self.assertEqual(ctx.exception.payload["authority_state"],
                         "JSON_ACTIVE")
        self.assertEqual(ctx.exception.payload["recheck"], "in_lock")
        # zero writes: projection unchanged, no decisions archive file
        decision_log = (self.gov_dir / "decision-log.md").read_text(
            encoding="utf-8")
        self.assertIn("DEC-501", decision_log)
        self.assertIn("DEC-502", decision_log)
        self.assertEqual(
            [p.name for p in (self.archive_dir / "decisions").glob("*.md")
             if p.name != ".gitkeep"],
            [])

    def test_concurrent_cutover_window_records_deferral(self):
        """REVIEW-FIX-385-R0 F-1: the in-lock refusal flows through
        migrate_by_version's deferral path (loud, never silent) while the
        other categories migrate normally."""
        self._world()
        self._write_archived_tasks()
        marker = self.gov_dir / ".decision-store-state.json"
        decision_before = (self.gov_dir / "decision-log.md").read_text(
            encoding="utf-8")
        with self._patched_root():
            with patch.object(self.archive, "_decision_authority_state",
                              side_effect=self._concurrent_cutover_state_probe(
                                  marker)):
                result = self.archive.migrate_by_version(
                    "0.60.0", "0.61.0", dry_run=False)
        self.assertEqual(
            result["decision_migration_deferred"]["authority_state"],
            "JSON_ACTIVE")
        self.assertEqual(result["decision_migration_deferred"]["recheck"],
                         "in_lock")
        # projection not rewritten; the other categories still migrated
        self.assertEqual(
            (self.gov_dir / "decision-log.md").read_text(encoding="utf-8"),
            decision_before)
        self.assertEqual(result["evidence_archived"], 54)

    def test_md_authority_still_migrates_decisions(self):
        """Control: with no authority marker (md world) the decision route
        behaves exactly as before FIX-385."""
        self._world()
        self._write_archived_tasks()
        with self._patched_root():
            result = self.archive.migrate_by_version(
                "0.60.0", "0.61.0", dry_run=False)
        self.assertIsNone(result.get("decision_migration_deferred"))
        self.assertEqual(result["decisions_archived"], 1)
        decision_log = (self.gov_dir / "decision-log.md").read_text(
            encoding="utf-8")
        self.assertNotIn("DEC-501", decision_log)   # migrated
        self.assertIn("DEC-502", decision_log)      # live ref retained

    def test_json_authority_defers_decisions_and_migrates_other_tables(self):
        self._world()
        self._write_archived_tasks()
        decision_before = (self.gov_dir / "decision-log.md").read_text(
            encoding="utf-8")
        self._write_authority_marker()
        with self._patched_root():
            result = self.archive.migrate_by_version(
                "0.60.0", "0.61.0", dry_run=False)
        self.assertEqual(
            result["decision_migration_deferred"]["authority_state"],
            "JSON_ACTIVE")
        # the md projection was NOT rewritten
        self.assertEqual(
            (self.gov_dir / "decision-log.md").read_text(encoding="utf-8"),
            decision_before)
        # the other categories migrated normally
        self.assertEqual(result["evidence_archived"], 54)
        # deferral is NOT a silent drop: the decision rows stay hot
        self.assertIn(
            "DEC-501",
            (self.gov_dir / "decision-log.md").read_text(encoding="utf-8"))

    def test_direct_decision_migration_raises_on_json_authority(self):
        self._world()
        self._write_authority_marker()
        with self._patched_root():
            with self.assertRaises(
                    self.archive.DecisionStoreAuthorityConflict) as ctx:
                self.archive._migrate_decisions(
                    "0.60.0", "0.61.0", {"FIX-101": "0.60.0"})
        self.assertEqual(ctx.exception.payload["authority_state"],
                         "JSON_ACTIVE")

    def test_corrupt_authority_marker_fails_closed(self):
        self._world()
        self._write_authority_marker(raw="{ not valid json")
        with self._patched_root():
            with self.assertRaises(
                    self.archive.DecisionStoreAuthorityConflict) as ctx:
                self.archive._migrate_decisions(
                    "0.60.0", "0.61.0", {"FIX-101": "0.60.0"})
        self.assertEqual(ctx.exception.payload["authority_state"],
                         "unreadable")

    def test_resumable_evidence_migration_runs_under_json_decision_authority(self):
        """The evidence big-table path is independent of the decision-store
        authority (separation of concerns) — it completes and REPORTS the
        decision world it ran in."""
        self._world()
        self._write_authority_marker()
        with self._patched_root():
            result = self.archive.migrate_evidence_resumable(
                "0.60.0", "0.61.0", batch_size=10)
        self.assertTrue(result["success"])
        self.assertEqual(result["migrated"], 54)
        self.assertEqual(result["decision_authority_state"], "JSON_ACTIVE")


if __name__ == "__main__":
    unittest.main()
