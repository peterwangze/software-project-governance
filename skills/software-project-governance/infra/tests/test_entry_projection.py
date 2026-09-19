"""FEAT-037 — AGENTS/CLAUDE dual-bootstrap dedup tests.

Scope (AUDIT-154 slice A-6):
  1. canonical template extraction from commands/governance-init.md Step 7
     (lightweight / standard / strict / secondary-thin blocks)
  2. bootstrap section span detection + idempotent section splice
  3. dual-entry: primary carries the canonical full bootstrap, secondary
     carries the rendered thin pointer (≤40 lines, ≤3072 bytes)
  4. single-entry regression: a lone entry file always gets the full
     bootstrap (behavior unchanged)
  5. double-apply produces zero diff (idempotency)
  6. thin pointer structural validation keeps the minimal survival checks
     (resolve_entry, plan-tracker read, SELF-CHECK, mode confirmation,
     quick entries, primary pointer)
  7. check_entry_bootstrap_sync over the real repo root + e2e fixture
  8. adapters/dsh/launch.py write_bootstrap reuses the shared splice
     functions (no duplicated logic, CLI behavior unchanged)

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_entry_projection.py -v
"""

import re
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parent.parent.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import sync_entry_projection as sep


# ────────────────────────────────────────────────────────────
# Synthetic canonical source (mirrors governance-init.md Step 7 shape)
# ────────────────────────────────────────────────────────────

_MINI_STANDARD = """## Governance Bootstrap（强制 — 每次会话第一动作）

> @bootstrap-version: 9.9.9（模板最低引导版本）

**⚡ SELF-CHECK**：
1. 读了 plan-tracker？

### Step 0: 确定双维度模式

读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节。

## 干活前检查（每次收到任务时）

- 这个任务在计划跟踪表里吗？
"""

_MINI_THIN = """## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 9.9.9（薄指针版——FEAT-037 双入口去重；完整 bootstrap 见 {PRIMARY_ENTRY}（主入口））

本工作区存在两个平台原生入口文件。本文件是次要平台入口（Codex/opencode 等）的薄指针投影，不复制完整模板。

### 最小存活检查（第一动作）

1. 运行 `python <plugin_home>/skills/software-project-governance/infra/resolve_entry.py --json`；`resolved_root_ok == false` → MUST STOP。
2. 读 `.governance/plan-tracker.md`；完整规则：`skills/software-project-governance/SKILL.md` 或主入口 `{PRIMARY_ENTRY}`。

### SELF-CHECK（在任何输出之前）

1. 读了 `.governance/plan-tracker.md`？否 → 立即停止，先读。
2. 知道当前阶段/Gate/模式？否 → 读 plan-tracker `## 项目配置`。
3. 即将输出问句？→ 改用 AskUserQuestion 工具。
4. 到达交互边界？→ MUST 使用 AskUserQuestion。
5. 写入是否有事实依据？无支撑 → 标 `BLOCKED`，禁止编造。

### 模式确认（每次会话一句，模式自适应）

- always-on → 输出治理状态一句
- on-demand → 仅用户显式调用时展开
- silent-track → 不输出治理面板

### 治理状态快速入口

- 计划跟踪 `.governance/plan-tracker.md` · 证据 `.governance/evidence-log.md`
- 完整 bootstrap：`{PRIMARY_ENTRY}`（主入口）
"""

_MINI_CANONICAL_DOC = f"""# init command

### Step 7: 注入 governance bootstrap

**lightweight profile 注入模板**：
```markdown
## Governance Bootstrap（由 software-project-governance 插件注入）

> @bootstrap-version: 9.9.9（轻量版）

### 每次会话第一动作
读取 `.governance/plan-tracker.md`。
```

**standard profile 注入模板**（完整版）：
```markdown
{_MINI_STANDARD}```

**strict profile 注入模板**（strict 差异段——渲染时由提取器组合：strict = standard 共享基座 + 本段，FEAT-041）：
```markdown
### Strict Profile 强制规则

Strict 量化评分与双证据强制。
```

**secondary-thin 注入模板**（薄指针版——FEAT-037 双入口去重）：
```markdown
{_MINI_THIN}```

### Step 8: 安装 hooks
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class Workspace:
    """Temporary project workspace with a synthetic canonical source."""

    def __init__(self, canonical_doc: str = _MINI_CANONICAL_DOC):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        _write(self.root / "commands" / "governance-init.md", canonical_doc)

    def entry(self, name: str) -> Path:
        return self.root / name

    def write_entry(self, name: str, text: str) -> None:
        _write(self.root / name, text)

    def read_entry(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def apply(self, **kwargs):
        return sep.apply_entry_projection(self.root, source_root=self.root, **kwargs)

    def report(self, **kwargs):
        return sep.build_sync_report(self.root, source_root=self.root, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._td.cleanup()


# ────────────────────────────────────────────────────────────
# 1. canonical extraction
# ────────────────────────────────────────────────────────────

class ExtractCanonicalTemplatesTests(unittest.TestCase):

    def test_extracts_all_four_blocks(self):
        templates = sep.extract_canonical_templates(_MINI_CANONICAL_DOC)
        self.assertEqual(
            sorted(templates), ["lightweight", "secondary-thin", "standard", "strict"]
        )

    def test_standard_block_roundtrip(self):
        templates = sep.extract_canonical_templates(_MINI_CANONICAL_DOC)
        self.assertEqual(templates["standard"], _MINI_STANDARD)

    def test_thin_block_carries_placeholder(self):
        templates = sep.extract_canonical_templates(_MINI_CANONICAL_DOC)
        self.assertIn("{PRIMARY_ENTRY}", templates["secondary-thin"])

    def test_missing_block_fails_closed(self):
        with self.assertRaises(ValueError):
            sep.extract_canonical_templates("# no templates here")

    def test_real_repo_canonical_extracts_four_blocks(self):
        text = (_REPO_ROOT / "commands" / "governance-init.md").read_text(encoding="utf-8")
        templates = sep.extract_canonical_templates(text)
        self.assertEqual(
            sorted(templates), ["lightweight", "secondary-thin", "standard", "strict"]
        )
        self.assertIn("### Step 0: 确定双维度模式", templates["standard"])
        self.assertIn("{PRIMARY_ENTRY}", templates["secondary-thin"])
        self.assertNotIn("{PRIMARY_ENTRY}", templates["standard"])

    def test_strict_block_composes_over_standard_base(self):
        """FEAT-041: the strict block carries the strict-profile DELTA; the
        shipped strict template = standard shared base + delta appended."""
        templates = sep.extract_canonical_templates(_MINI_CANONICAL_DOC)
        base, strict = templates["standard"], templates["strict"]
        self.assertTrue(strict.startswith("## Governance Bootstrap"))
        self.assertGreater(len(strict), len(base))
        expected = base.rstrip("\n") + "\n\n" + strict[len(base.rstrip("\n")) + 2:]
        self.assertEqual(strict, expected)
        self.assertIn("### Strict Profile 强制规则", strict[len(base):])

    def test_strict_delta_block_is_not_a_full_template(self):
        """Single-maintenance guard: a full-template copy pasted into the
        strict block would double the shared base after composition — the
        delta must never carry the full-bootstrap marker."""
        for doc in (_MINI_CANONICAL_DOC,
                    (_REPO_ROOT / "commands" / "governance-init.md").read_text(encoding="utf-8")):
            templates = sep.extract_canonical_templates(doc)
            base, strict = templates["standard"], templates["strict"]
            delta = strict[len(base.rstrip("\n")) + 2:]
            self.assertTrue(
                delta.startswith("### Strict Profile 强制规则") or "Strict" in delta,
                "strict delta block lost its heading")
            self.assertNotIn("### Step 0: 确定双维度模式", delta)
            self.assertNotIn("## Governance Bootstrap", delta)


# ────────────────────────────────────────────────────────────
# 2. span + splice
# ────────────────────────────────────────────────────────────

class SectionSpliceTests(unittest.TestCase):

    def test_span_full_section_nested_h2_kept(self):
        doc = "# Title\n\n" + _MINI_STANDARD + "## 项目质量原则\n\n保留\n"
        span = sep.bootstrap_section_span(
            doc, boundary_titles=sep._h2_titles(_MINI_STANDARD)
        )
        self.assertIsNotNone(span)
        section = sep._slice_span(doc, span)
        self.assertTrue(section.startswith("## Governance Bootstrap"))
        self.assertIn("### Step 0: 确定双维度模式", section)
        self.assertIn("## 干活前检查", section)  # canonical nested H2 stays inside
        self.assertNotIn("项目质量原则", section)  # foreign H2 ends the section

    def test_replace_preserves_content_outside_section(self):
        original = "# Title\n\n" + _MINI_THIN.replace(
            "{PRIMARY_ENTRY}", "CLAUDE.md"
        ) + "## 项目质量原则\n\n保留我\n"
        updated = sep.replace_bootstrap_section(original, "NEW SECTION\n")
        self.assertIn("## 项目质量原则", updated)
        self.assertIn("保留我", updated)
        self.assertIn("NEW SECTION", updated)
        self.assertNotIn("次要平台入口薄指针", updated)

    def test_replace_is_idempotent(self):
        section = "## Governance Bootstrap（强制）\n\nNEW SECTION\n"
        original = "# Title\n\nold bootstrap\n"
        once = sep.replace_bootstrap_section(original, section)
        twice = sep.replace_bootstrap_section(once, section)
        self.assertEqual(once, twice)

    def test_append_when_no_section(self):
        updated = sep.replace_bootstrap_section("# Title\n\nbody\n", "NEW SECTION\n")
        self.assertIn("# Title", updated)
        self.assertIn("NEW SECTION", updated)
        self.assertLess(updated.index("# Title"), updated.index("NEW SECTION"))


# ────────────────────────────────────────────────────────────
# 3+4+5. plan / apply / idempotency / single-entry regression
# ────────────────────────────────────────────────────────────

class DualEntryPlanTests(unittest.TestCase):

    def test_dual_entry_primary_full_secondary_thin(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n旧完整 bootstrap\n")
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n旧完整 bootstrap\n")
            plan = sep.plan_entry_writes(ws.root, source_root=ws.root)
            by_path = {w.relative_path: w for w in plan}
            self.assertEqual(by_path["CLAUDE.md"].kind, "full")
            self.assertEqual(by_path["AGENTS.md"].kind, "thin")

    def test_single_entry_agents_only_stays_full(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n旧完整 bootstrap\n")
            plan = sep.plan_entry_writes(ws.root, source_root=ws.root)
            kinds = {w.relative_path: w.kind for w in plan}
            self.assertEqual(kinds, {"AGENTS.md": "full"})

    def test_single_entry_claude_only_stays_full(self):
        with Workspace() as ws:
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n")
            plan = sep.plan_entry_writes(ws.root, source_root=ws.root)
            kinds = {w.relative_path: w.kind for w in plan}
            self.assertEqual(kinds, {"CLAUDE.md": "full"})

    def test_secondary_never_created(self):
        with Workspace() as ws:
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n")
            plan = sep.plan_entry_writes(ws.root, source_root=ws.root)
            self.assertFalse(any(w.relative_path == "AGENTS.md" for w in plan))

    def test_no_entries_noop(self):
        with Workspace() as ws:
            self.assertEqual(sep.plan_entry_writes(ws.root, source_root=ws.root), [])

    def test_thin_sticky_when_primary_absent(self):
        """A committed thin pointer must not be flipped back to full when the
        gitignored primary is absent from the working environment."""
        thin = sep.render_thin_pointer(_MINI_THIN, "CLAUDE.md")
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n" + thin)
            plan = sep.plan_entry_writes(ws.root, source_root=ws.root)
            kinds = {w.relative_path: w.kind for w in plan}
            self.assertEqual(kinds.get("AGENTS.md", "none"), "none")


class ApplyAndIdempotencyTests(unittest.TestCase):

    def test_apply_dual_entry_and_double_apply_zero_diff(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n## 旧完整\n\nStep 0\n")
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n## 旧完整\n")
            ws.apply()
            first = {n: ws.read_entry(n) for n in ("AGENTS.md", "CLAUDE.md")}
            ws.apply()
            second = {n: ws.read_entry(n) for n in ("AGENTS.md", "CLAUDE.md")}
            self.assertEqual(first, second)

    def test_apply_preserves_outside_content(self):
        with Workspace() as ws:
            ws.write_entry(
                "AGENTS.md",
                "# Codex 项目指引\n\n旧\n\n## 项目质量原则（P-v1）\n\n保留我\n",
            )
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n旧\n")
            ws.apply()
            updated = ws.read_entry("AGENTS.md")
            self.assertIn("## 项目质量原则（P-v1）", updated)
            self.assertIn("保留我", updated)

    def test_apply_single_entry_secondary_gets_full(self):
        """A lone secondary entry is upgraded in place; the missing primary is
        never conjured into existence (first-time creation stays with
        governance-init)."""
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n旧\n")
            ws.apply()
            self.assertIn("### Step 0: 确定双维度模式", ws.read_entry("AGENTS.md"))
            self.assertFalse((ws.root / "CLAUDE.md").exists())

    def test_thin_pointer_limits(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n旧\n")
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n旧\n")
            ws.apply()
            section = sep.bootstrap_section_span(
                ws.read_entry("AGENTS.md")
            )
            text = sep._slice_span(ws.read_entry("AGENTS.md"), section)
            self.assertLessEqual(len(text.splitlines()), 40)
            self.assertLessEqual(len(text.encode("utf-8")), 3072)


# ────────────────────────────────────────────────────────────
# 6. thin pointer structural validation
# ────────────────────────────────────────────────────────────

class ThinPointerValidationTests(unittest.TestCase):

    def test_rendered_thin_validates_clean(self):
        rendered = sep.render_thin_pointer(_MINI_THIN, "CLAUDE.md")
        self.assertEqual(sep.validate_thin_pointer(rendered, "CLAUDE.md"), [])

    def test_missing_anchor_flagged(self):
        rendered = sep.render_thin_pointer(_MINI_THIN, "CLAUDE.md")
        broken = rendered.replace("resolve_entry.py --json", "resolve_entry.json")
        issues = sep.validate_thin_pointer(broken, "CLAUDE.md")
        self.assertTrue(any("resolve_entry" in i for i in issues))

    def test_placeholder_residue_flagged(self):
        issues = sep.validate_thin_pointer(_MINI_THIN, "CLAUDE.md")
        self.assertTrue(any("PRIMARY_ENTRY" in i for i in issues))

    def test_dropped_survival_check_flagged(self):
        rendered = sep.render_thin_pointer(_MINI_THIN, "CLAUDE.md")
        broken = "\n".join(
            line for line in rendered.splitlines() if "plan-tracker" not in line
        )
        issues = sep.validate_thin_pointer(broken, "CLAUDE.md")
        self.assertTrue(any("plan-tracker" in i for i in issues))

    def test_real_repo_rendered_thin_within_budget(self):
        templates = sep.extract_canonical_templates(
            (_REPO_ROOT / "commands" / "governance-init.md").read_text(encoding="utf-8")
        )
        rendered = sep.render_thin_pointer(templates["secondary-thin"], "CLAUDE.md")
        self.assertLessEqual(len(rendered.splitlines()), 40)
        self.assertLessEqual(len(rendered.encode("utf-8")), 3072)
        self.assertEqual(sep.validate_thin_pointer(rendered, "CLAUDE.md"), [])


# ────────────────────────────────────────────────────────────
# 7. repo + fixture sync report
# ────────────────────────────────────────────────────────────

class RepoSyncReportTests(unittest.TestCase):

    def test_repo_root_sync_report_passes(self):
        report = sep.build_sync_report(_REPO_ROOT, source_root=_REPO_ROOT)
        self.assertEqual(report["issues"], [], msg=str(report["issues"]))

    def test_fixture_sync_report_passes(self):
        fixture = _REPO_ROOT / "project" / "e2e-test-project"
        report = sep.build_sync_report(fixture, source_root=_REPO_ROOT)
        self.assertEqual(report["issues"], [], msg=str(report["issues"]))

    def test_drift_detected(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex 项目指引\n\n旧\n")
            ws.write_entry("CLAUDE.md", "# Claude 项目指引\n\n被篡改\n")
            report = ws.report()
            self.assertFalse(report["pass"])

    def test_dual_full_bootstrap_flagged(self):
        with Workspace() as ws:
            ws.write_entry("AGENTS.md", "# Codex\n\n" + _MINI_STANDARD)
            ws.write_entry("CLAUDE.md", "# Claude\n\n" + _MINI_STANDARD)
            report = ws.report()
            self.assertFalse(report["pass"])
            self.assertTrue(
                any("dual-full" in i or "完整" in i for i in report["issues"]),
                msg=str(report["issues"]),
            )


# ────────────────────────────────────────────────────────────
# 8. launch.py reuse (shared splice, CLI behavior unchanged)
# ────────────────────────────────────────────────────────────

def _bootstrap_template_version() -> str:
    """Version carried by the DSH bootstrap template's header line (FIX-352).

    ``launch.write_bootstrap`` splices a render of
    ``adapters/dsh/AGENTS.md.template`` into the target ``AGENTS.md`` verbatim,
    so the version landing in the spliced section is the render source's own
    header version — the source closest to this surface. Deriving it here
    (instead of pinning the release literal ``0.83.0``) closes the version-pin
    rot the FIX-335 discipline names: the pin was RED on the next bump and on
    nothing else.

    The template ↔ SKILL.md frontmatter authority binding is deliberately NOT
    re-asserted here — ``test_dsh_adapter.py`` owns that drift channel through
    the ``dsh-agents-bootstrap-version`` projection, so a stale template fails
    once, correctly attributed, instead of surfacing twice. An unreadable
    header raises rather than degrading the assertion to a vacuous compare.
    """
    template = _REPO_ROOT / "adapters" / "dsh" / "AGENTS.md.template"
    if not template.is_file():
        raise AssertionError(f"bootstrap template missing: {template}")
    match = re.search(r"@bootstrap-version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
                      template.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(
            f"{template} carries no @bootstrap-version header — "
            "write_bootstrap renders this file into AGENTS.md")
    return match.group(1)


class LaunchBootstrapReuseTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib.util
        launch_path = _REPO_ROOT / "adapters" / "dsh" / "launch.py"
        spec = importlib.util.spec_from_file_location("dsh_launch_under_test", launch_path)
        cls.launch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.launch)

    def test_shared_splice_functions_reused(self):
        for name in ("bootstrap_section_span", "replace_bootstrap_section"):
            self.assertFalse(
                hasattr(self.launch, name),
                msg=f"launch.py must import {name} from sync_entry_projection, "
                    "not redefine it",
            )
        import inspect
        write_source = inspect.getsource(self.launch.write_bootstrap)
        self.assertIn("replace_bootstrap_section", write_source)
        self.assertIn("bootstrap_section_span", write_source)
        helper = getattr(self.launch, "_entry_projection_shared", None)
        self.assertIsNotNone(helper, "launch.py must load the shared module")
        self.assertIn("sync_entry_projection", inspect.getsource(helper))

    def test_write_bootstrap_splices_section_preserving_tail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            existing = (
                "# Project Guidance\n\n## Governance Bootstrap（DSH — 强制）\n\n"
                "> @bootstrap-version: 0.1.0\n\n旧内容\n\n## 自定义尾段\n\n保留我\n"
            )
            _write(project / "AGENTS.md", existing)
            rc = self.launch.write_bootstrap(project, force=False)
            self.assertEqual(rc, 0)
            updated = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# Project Guidance", updated)
            self.assertIn("## 自定义尾段", updated)
            self.assertIn("保留我", updated)
            # FIX-352: the spliced section carries the *template's* header
            # version (the bytes write_bootstrap renders), derived — never a
            # pinned release literal.
            self.assertIn(
                f"@bootstrap-version: {_bootstrap_template_version()}", updated)
            self.assertNotIn("旧内容", updated)

    def test_write_bootstrap_refuses_sectionless_target_without_force(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            _write(project / "AGENTS.md", "# Plain project file\n")
            rc = self.launch.write_bootstrap(project, force=False)
            self.assertEqual(rc, 1)
            self.assertEqual(
                (project / "AGENTS.md").read_text(encoding="utf-8"),
                "# Plain project file\n",
            )

    def test_write_bootstrap_dry_run_writes_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            _write(project / "AGENTS.md", "# Project\n\n## Governance Bootstrap\n\n旧\n")
            rc = self.launch.write_bootstrap(project, force=False, dry_run=True)
            self.assertEqual(rc, 0)
            self.assertIn("旧", (project / "AGENTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
