"""Unit tests for resolve_entry.py — FX-130 / DEC-096 / AUDIT-129.

These tests are the RISK-040 closure criteria. The most important case
(``test_divergent_roots_active_version_from_skill``) is exactly the test
that 0.54.2/0.54.3 FAILED to have: plugin_home and host_project_root are
fully divergent, and we assert the active version + facts come from the
correct root.

Run:
    python -m unittest skills.software-project-governance.infra.tests.test_resolve_entry -v
or:
    python skills/software-project-governance/infra/tests/test_resolve_entry.py
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import resolve_entry as re_  # noqa: E402


# ─── Fixture builders ──────────────────────────────────────────
def _write_skill_md(plugin_home, version):
    """Write a SKILL.md with YAML frontmatter version (matches real format)."""
    plugin_home.mkdir(parents=True, exist_ok=True)
    (plugin_home / "SKILL.md").write_text(
        "---\n"
        "name: software-project-governance\n"
        f"version: {version}\n"
        "description: test skill\n"
        "---\n\n"
        "# Body — a stray `version: 0.0.0-FAKE` here must not win.\n",
        encoding="utf-8",
    )


def _write_plan_tracker(host_root, workflow_version):
    gov = host_root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(
        "# 项目\n\n"
        "## 项目配置\n"
        f"- **工作流版本**: {workflow_version}\n"
        "- **当前阶段**: 开发实现\n",
        encoding="utf-8",
    )
    (gov / "evidence-log.md").write_text(
        "# 证据记录\n\n| EVD-1 | ... |\n", encoding="utf-8"
    )


def _write_snapshot(host_root, dt):
    gov = host_root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    iso = dt.strftime("%Y-%m-%d")
    sid = dt.strftime("%Y%m%d") + "-120000"
    (gov / "session-snapshot.md").write_text(
        f"# 会话快照 — {iso}\n\n"
        f"- **session_id**: {sid}\n"
        f"- **session_date**: {iso}\n"
        f"- **工作流版本**: 0.0.0\n",
        encoding="utf-8",
    )


def _install_hook(host_root, name):
    hooks = host_root / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / name).write_text("#!/bin/sh\n", encoding="utf-8")


# ─── Tests ─────────────────────────────────────────────────────
class ResolveEntryTests(unittest.TestCase):
    """RISK-040 closure tests for the dual-root entry resolver."""

    # ── RISK-040 #1 + #2: divergent roots ──
    def test_divergent_roots_active_version_from_skill(self):
        """C3: cwd != plugin-root != skill-path. active_version MUST come
        from the plugin_home SKILL.md, not anything in host."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            plugin_home = Path(plugin_td)
            host_root = Path(host_td)
            _write_skill_md(plugin_home, "9.9.9")
            # Host has its own (different) workflow version on record.
            _write_plan_tracker(host_root, "1.2.3")

            version = re_.read_active_version(plugin_home)
            self.assertEqual(version, "9.9.9")

            with patch.object(re_, "PLUGIN_HOME", plugin_home):
                env = re_.resolve(host_root)

            self.assertEqual(env["active_version"], "9.9.9")
            self.assertNotEqual(env["active_version"], "1.2.3")
            self.assertTrue(env["root_divergence"])
            self.assertEqual(
                env["plugin_home"], str(plugin_home)
            )
            self.assertEqual(
                env["host_project_root"], str(host_root)
            )

    def test_host_facts_read_from_host_not_plugin(self):
        """C3: governance_initialized reflects HOST .governance/, not the
        plugin's. The plugin_home here has NO .governance at all."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            plugin_home = Path(plugin_td)
            host_root = Path(host_td)
            _write_skill_md(plugin_home, "2.0.0")
            _write_plan_tracker(host_root, "2.0.0")
            # Plugin home deliberately has NO .governance/.

            with patch.object(re_, "PLUGIN_HOME", plugin_home):
                env = re_.resolve(host_root)

            self.assertTrue(env["governance_initialized"])
            # Negative control: plugin_home has no .governance, so if we
            # had mistakenly read plugin state this would be False.
            self.assertFalse((plugin_home / ".governance").exists())

    # ── RISK-040 #2: fail-closed ──
    def test_fail_closed_when_host_root_unresolvable(self):
        """C4: unresolvable host root -> resolved_root_ok=false + diagnostic,
        and we do NOT fall back to plugin state."""
        with tempfile.TemporaryDirectory() as plugin_td:
            plugin_home = Path(plugin_td)
            # Even if the plugin has its own .governance/, fail-closed must
            # refuse to surface it.
            (plugin_home / ".governance").mkdir(parents=True, exist_ok=True)
            (plugin_home / ".governance" / "plan-tracker.md").write_text(
                "leak", encoding="utf-8"
            )
            _write_skill_md(plugin_home, "3.3.3")

            with patch.object(re_, "PLUGIN_HOME", plugin_home):
                env = re_.resolve(None)

        self.assertFalse(env["resolved_root_ok"])
        self.assertIsNone(env["host_project_root"])
        self.assertIn("diagnostic", env)
        self.assertIn("fail-closed", env["diagnostic"].lower())
        # The tell-tale of the 0.54.2/0.54.3 bug: governance state would
        # leak from the plugin. Assert it does not.
        self.assertFalse(env["governance_initialized"])
        self.assertIsNone(env["scenario_hint"])
        self.assertIsNone(env["root_divergence"])

    def test_resolve_host_root_nonexistent_explicit_path_fails_closed(self):
        """An explicit --project-root that doesn't exist is a hard error."""
        self.assertIsNone(
            re_.resolve_host_root(
                "/this/path/does/not/exist/anywhere/XFWQZ"
            )
        )

    # ── RISK-040 #1: scenario hints A-F ──
    def _env_for(self, plugin_home, host_root):
        with patch.object(re_, "PLUGIN_HOME", plugin_home):
            return re_.resolve(host_root)

    def test_scenario_A_new_project_init(self):
        """Empty host dir, no .governance/ -> A."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            env = self._env_for(Path(plugin_td), Path(host_td))
        self.assertEqual(env["scenario_hint"], "A")

    def test_scenario_B_mid_project_onboarding(self):
        """Host has files but no .governance/ -> B."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            host = Path(host_td)
            (host / "README.md").write_text("hi", encoding="utf-8")
            (host / "src").mkdir()
            env = self._env_for(Path(plugin_td), host)
        self.assertEqual(env["scenario_hint"], "B")

    def test_scenario_C_upgrade(self):
        """Host workflow version < active_version -> C."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "2.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "1.0.0")  # older
            env = self._env_for(Path(plugin_td), host)
        self.assertEqual(env["scenario_hint"], "C")

    def test_scenario_D_session_recovery(self):
        """Fresh snapshot (<=24h), version matches -> D."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "2.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "2.0.0")
            _write_snapshot(host, datetime.now())
            env = self._env_for(Path(plugin_td), host)
        self.assertEqual(env["scenario_hint"], "D")
        self.assertTrue(env["snapshot_fresh"])

    def test_scenario_E_anomaly_recovery(self):
        """.governance/ exists but a core file (evidence-log) missing -> E."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "2.0.0")
            host = Path(host_td)
            gov = host / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "plan-tracker.md").write_text(
                "- **工作流版本**: 2.0.0\n", encoding="utf-8"
            )
            # evidence-log.md intentionally absent -> anomaly
            env = self._env_for(Path(plugin_td), host)
        self.assertEqual(env["scenario_hint"], "E")

    def test_scenario_F_status_display(self):
        """All good, no fresh snapshot, version matches -> F."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "2.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "2.0.0")
            # Stale snapshot (30 days ago) -> not D, falls through to F.
            _write_snapshot(host, datetime.now() - timedelta(days=30))
            env = self._env_for(Path(plugin_td), host)
        self.assertEqual(env["scenario_hint"], "F")
        self.assertFalse(env["snapshot_fresh"])

    # ── Snapshot freshness ──
    def test_snapshot_freshness_recent_is_fresh(self):
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "1.0.0")
            _write_snapshot(host, datetime.now() - timedelta(hours=2))
            env = self._env_for(Path(plugin_td), host)
        self.assertTrue(env["snapshot_exists"])
        self.assertTrue(env["snapshot_fresh"])

    def test_snapshot_freshness_old_is_not_fresh(self):
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "1.0.0")
            _write_snapshot(host, datetime.now() - timedelta(hours=48))
            env = self._env_for(Path(plugin_td), host)
        self.assertTrue(env["snapshot_exists"])
        self.assertFalse(env["snapshot_fresh"])

    def test_snapshot_freshness_missing_is_null(self):
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "1.0.0")
            env = self._env_for(Path(plugin_td), host)
        self.assertFalse(env["snapshot_exists"])
        self.assertIsNone(env["snapshot_fresh"])

    # ── Root divergence flag ──
    def test_root_divergence_true_when_different(self):
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            env = self._env_for(Path(plugin_td), Path(host_td))
        self.assertTrue(env["root_divergence"])

    def test_root_divergence_false_when_dogfood(self):
        """When plugin_home == host (dogfood), divergence is False."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill_md(root, "1.0.0")
            _write_plan_tracker(root, "1.0.0")
            env = self._env_for(root, root)
        self.assertFalse(env["root_divergence"])

    def test_happy_path_envelope_has_diagnostic_none(self):
        """Schema uniformity: happy-path envelope carries ``diagnostic: None``
        so consumers can do ``envelope["diagnostic"]`` on both paths."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            env = self._env_for(Path(plugin_td), Path(host_td))
        self.assertTrue(env["resolved_root_ok"])
        self.assertIn("diagnostic", env)
        self.assertIsNone(env["diagnostic"])

    # ── Hooks detection ──
    def test_hooks_detection(self):
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "1.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "1.0.0")
            _install_hook(host, "pre-commit")
            _install_hook(host, "commit-msg")
            env = self._env_for(Path(plugin_td), host)
        self.assertTrue(env["hooks_installed"]["pre-commit"])
        self.assertTrue(env["hooks_installed"]["commit-msg"])
        self.assertFalse(env["hooks_installed"]["post-commit"])

    # ── SKILL.md frontmatter parsing robustness ──
    def test_active_version_ignores_stray_version_in_body(self):
        """A `version:` line in the body prose must NOT override frontmatter."""
        with tempfile.TemporaryDirectory() as td:
            ph = Path(td)
            _write_skill_md(ph, "5.5.5")  # body has `version: 0.0.0-FAKE`
            self.assertEqual(re_.read_active_version(ph), "5.5.5")

    def test_active_version_none_when_skill_md_missing(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(re_.read_active_version(Path(td)))

    def test_scenario_C_not_triggered_when_host_version_equal(self):
        """Equal versions -> NOT C (no false upgrade hint)."""
        with tempfile.TemporaryDirectory() as plugin_td, \
                tempfile.TemporaryDirectory() as host_td:
            _write_skill_md(Path(plugin_td), "2.0.0")
            host = Path(host_td)
            _write_plan_tracker(host, "2.0.0")  # equal
            env = self._env_for(Path(plugin_td), host)
        self.assertNotEqual(env["scenario_hint"], "C")


if __name__ == "__main__":
    unittest.main()
