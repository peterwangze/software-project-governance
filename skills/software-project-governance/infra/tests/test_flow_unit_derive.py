"""Unit tests for FX-190 flow-unit derivation (0.65.0 loop-engineering, slice 3).

These tests are the load-bearing verification that the VAL-006 gap is closed:
flow units are derived from a target project's plan-tracker per project type,
not just from the ``python_game`` example baked into the registry.

The single most important test here is
:func:`TestDeriveFlowUnits.test_cli_tool_3_commands_derives_3_units` — the
VAL-006 closure test. A buggy derivation that fell back to a single whole-unit
when the target IS clearly decomposable would fail this test.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_flow_unit_derive.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_flow_unit_derive -v
"""

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import flow_unit_derive as fud  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/

# The 15 required fields from flow_unit_schema.required_fields in
# lifecycle-registry.json. Every derived unit MUST carry all of these.
REQUIRED_FIELDS = [
    "flow_unit_id",
    "title",
    "unit_type",
    "project_type",
    "lifecycle_mode",
    "current_stage",
    "current_subphase",
    "gate_lane",
    "gate_references",
    "allowed_next_transitions",
    "dependencies",
    "blockers",
    "evidence_refs",
    "loop_state",
    "runtime_status_source",
]


# ─── Shared fixtures ─────────────────────────────────────────────────────────

# A synthetic CLI-tool plan-tracker with 3 commands, expressed three ways
# (dotted ids, dotted ids with explicit "command" segment, and prose). Each
# sub-fixture exercises a different tolerant-parsing path.
CLI_TRACKER_DOTTED = (
    "# Plan Tracker — mycli\n"
    "- [ ] mycli.init: scaffold the project\n"
    "- [ ] mycli.build: compile assets\n"
    "- [ ] mycli.deploy: ship to registry\n"
)

CLI_TRACKER_EXPLICIT_SEGMENT = (
    "Tasks:\n"
    "mycli.command.init — scaffolding\n"
    "mycli.command.build — compile\n"
    "mycli.command.deploy — ship\n"
)

CLI_TRACKER_PROSE = (
    "## Commands\n"
    "Implement the init command for project scaffolding.\n"
    "The build command compiles all assets.\n"
    "Finally the deploy command ships artifacts.\n"
)

GAME_TRACKER = (
    "# Plan Tracker — mygame\n"
    "- [ ] game.chapter.01: intro\n"
    "- [ ] game.chapter.02: the forest\n"
    "- [ ] game.chapter.03: the tower\n"
)

LIBRARY_TRACKER = (
    "# Plan Tracker — mylib\n"
    "- [ ] lib.module.auth: authentication\n"
    "- [ ] lib.module.storage: persistence\n"
    "- [ ] lib.api-surface.public: public API\n"
)

EMPTY_TRACKER = "# Plan Tracker\n\nNo tasks yet.\n"


class TestProjectIdDerivation(unittest.TestCase):
    """Sanitization of target_root → project_id."""

    def test_project_id_from_directory_name(self):
        self.assertEqual(
            fud._derive_project_id("/path/to/my-awesome-cli"),
            "my-awesome-cli",
        )

    def test_project_id_lowercases_and_hyphenates(self):
        self.assertEqual(fud._derive_project_id("/x/My Cool Project"), "my-cool-project")

    def test_project_id_preserves_dots(self):
        # Dots are preserved (they're valid in machine ids like package names).
        self.assertEqual(fud._derive_project_id("/x/foo.bar.baz"), "foo.bar.baz")

    def test_project_id_fallback_for_empty(self):
        self.assertEqual(fud._derive_project_id(None), "unknown-project")
        self.assertEqual(fud._derive_project_id(""), "unknown-project")


class TestDormantLoopState(unittest.TestCase):
    """Derived units carry the DORMANT 3-field loop_state, NOT FX-189's 5-field shape."""

    def test_dormant_loop_state_has_exactly_three_fields(self):
        ls = fud._dormant_loop_state()
        self.assertEqual(set(ls.keys()), {"active_loop", "loop_count", "last_loop_type"})
        self.assertFalse(ls["active_loop"])
        self.assertEqual(ls["loop_count"], 0)
        self.assertIsNone(ls["last_loop_type"])

    def test_dormant_loop_state_has_no_activated_fields(self):
        """The FX-189 activated fields MUST be absent on derived units."""
        ls = fud._dormant_loop_state()
        for forbidden in (
            "active_loop_tier",
            "agent_phase",
            "iteration_within_inner",
            "pause_points_active",
            "last_gate_result",
            "fuse",
        ):
            self.assertNotIn(forbidden, ls, f"dormant loop_state must not carry {forbidden}")


class TestDeriveFlowUnits(unittest.TestCase):
    # ─── Test 1: VAL-006 CLOSURE (load-bearing) ──────────────────────────────
    def test_cli_tool_3_commands_derives_3_units(self):
        """VAL-006 CLOSURE TEST — a CLI tool with 3 commands yields 3 command units.

        A buggy derivation that fell back to a single whole-unit when the
        target IS decomposable would FAIL here (it would return 1 unit of
        type "script" instead of 3 of type "command"). This is the single
        most important test in the file.
        """
        for label, fixture in (
            ("dotted", CLI_TRACKER_DOTTED),
            ("explicit-segment", CLI_TRACKER_EXPLICIT_SEGMENT),
            ("prose", CLI_TRACKER_PROSE),
        ):
            with self.subTest(form=label):
                units = fud.derive_flow_units(
                    "/path/to/my-cli", "cli-tool", fixture, plugin_home=PLUGIN_HOME
                )
                self.assertEqual(
                    len(units), 3,
                    f"[{label}] expected 3 command units, got {len(units)}: "
                    f"{[u['flow_unit_id'] for u in units]}",
                )
                for u in units:
                    self.assertEqual(u["unit_type"], "command")
                    self.assertEqual(u["project_type"], "cli-tool")
                # The three command names must be init/build/deploy.
                names = sorted(u["flow_unit_id"].split(".")[-1] for u in units)
                self.assertEqual(names, ["build", "deploy", "init"])

    def test_cli_tool_units_have_stable_ids(self):
        """flow_unit_id is stable and machine-readable: {project_id}.command.{name}."""
        units = fud.derive_flow_units(
            "/path/to/my-cli", "cli-tool", CLI_TRACKER_DOTTED, plugin_home=PLUGIN_HOME
        )
        for u in units:
            self.assertTrue(u["flow_unit_id"].startswith("my-cli.command."))

    # ─── Test 2: fallback for empty/featureless plan-tracker ─────────────────
    def test_fallback_single_unit_for_empty_plan_tracker(self):
        """An empty/featureless plan-tracker yields exactly ONE fallback unit."""
        units = fud.derive_flow_units(
            "/path/to/thing", "cli-tool", EMPTY_TRACKER, plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 1)
        u = units[0]
        self.assertEqual(u["flow_unit_id"], "thing.script.whole")
        self.assertEqual(
            u["derivation_reason"], "no-decomposable-structure-found"
        )

    def test_fallback_for_truly_empty_string(self):
        """An empty-string plan-tracker also yields the single fallback unit."""
        units = fud.derive_flow_units(
            "/path/to/thing", "game", "", plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 1)
        self.assertIn("derivation_reason", units[0])

    # ─── Test 3: game chapter regression ─────────────────────────────────────
    def test_game_regression_chapters_derived(self):
        """Game plan-trackers with chapter patterns derive chapter units.

        Regression guard: the game path (the only path that worked pre-FX-190
        via the python_game example) must not break.
        """
        units = fud.derive_flow_units(
            "/path/to/mygame", "game", GAME_TRACKER, plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 3)
        for u in units:
            self.assertEqual(u["unit_type"], "chapter")
            self.assertEqual(u["project_type"], "game")
            self.assertTrue(u["flow_unit_id"].startswith("mygame.chapter."))

    def test_game_chapters_preserve_numeric_names(self):
        """Chapter names from dotted ids are preserved (01, 02, 03)."""
        units = fud.derive_flow_units(
            "/path/to/mygame", "game", GAME_TRACKER, plugin_home=PLUGIN_HOME
        )
        names = sorted(u["flow_unit_id"].split(".")[-1] for u in units)
        self.assertEqual(names, ["01", "02", "03"])

    # ─── Test 4: library modules (proves derivation isn't cli-specific) ──────
    def test_library_derives_modules(self):
        """A library plan-tracker derives module units.

        This proves derivation generalizes beyond the CLI case (step 5 of the
        §3.4 closure procedure: prove it isn't cli-specific).
        """
        units = fud.derive_flow_units(
            "/path/to/mylib", "library", LIBRARY_TRACKER, plugin_home=PLUGIN_HOME
        )
        # 3 modules: auth, storage, public (api-surface name "public").
        self.assertEqual(len(units), 3)
        for u in units:
            self.assertEqual(u["unit_type"], "module")
            self.assertEqual(u["project_type"], "library")
        names = sorted(u["flow_unit_id"].split(".")[-1] for u in units)
        self.assertEqual(names, ["auth", "public", "storage"])

    # ─── Test 5: internal-script is always a single unit ─────────────────────
    def test_internal_script_single_unit(self):
        """internal-script always yields exactly one {project_id}.whole script unit."""
        units = fud.derive_flow_units(
            "/path/to/migrate-script",
            "internal-script",
            "anything in here is ignored",
            plugin_home=PLUGIN_HOME,
        )
        self.assertEqual(len(units), 1)
        u = units[0]
        self.assertEqual(u["flow_unit_id"], "migrate-script.script.whole")
        self.assertEqual(u["unit_type"], "script")
        self.assertEqual(u["project_type"], "internal-script")

    def test_internal_script_single_unit_even_with_decomposable_text(self):
        """Even if the text looks decomposable, internal-script stays single."""
        units = fud.derive_flow_units(
            "/path/to/s", "internal-script", "game.chapter.01 game.chapter.02",
            plugin_home=PLUGIN_HOME,
        )
        self.assertEqual(len(units), 1)

    # ─── Test 6: dormant loop_state on derived units ─────────────────────────
    def test_derived_units_have_dormant_loop_state(self):
        """All derived units have the DORMANT 3-field loop_state (not 5-field)."""
        units = fud.derive_flow_units(
            "/path/to/my-cli", "cli-tool", CLI_TRACKER_DOTTED, plugin_home=PLUGIN_HOME
        )
        self.assertGreaterEqual(len(units), 1)
        for u in units:
            ls = u["loop_state"]
            self.assertEqual(
                set(ls.keys()),
                {"active_loop", "loop_count", "last_loop_type"},
                f"loop_state must be the dormant 3-field shape, got {sorted(ls.keys())}",
            )
            self.assertFalse(ls["active_loop"])
            self.assertEqual(ls["loop_count"], 0)
            self.assertIsNone(ls["last_loop_type"])

    def test_fallback_unit_also_has_dormant_loop_state(self):
        """Even the fallback whole-unit carries the dormant loop_state."""
        units = fud.derive_flow_units(
            "/path/to/x", "cli-tool", EMPTY_TRACKER, plugin_home=PLUGIN_HOME
        )
        ls = units[0]["loop_state"]
        self.assertEqual(set(ls.keys()), {"active_loop", "loop_count", "last_loop_type"})

    # ─── Test 7: all 15 required fields present ──────────────────────────────
    def test_derived_units_have_all_required_fields(self):
        """Each unit carries all 15 flow_unit_schema.required_fields."""
        fixtures = [
            ("/path/to/my-cli", "cli-tool", CLI_TRACKER_DOTTED),
            ("/path/to/mygame", "game", GAME_TRACKER),
            ("/path/to/mylib", "library", LIBRARY_TRACKER),
            ("/path/to/empty", "cli-tool", EMPTY_TRACKER),  # fallback unit too
            ("/path/to/s", "internal-script", "x"),
        ]
        for target_root, ptype, text in fixtures:
            with self.subTest(ptype=ptype, target=target_root):
                units = fud.derive_flow_units(
                    target_root, ptype, text, plugin_home=PLUGIN_HOME
                )
                for u in units:
                    missing = [f for f in REQUIRED_FIELDS if f not in u]
                    self.assertEqual(
                        missing, [],
                        f"unit {u.get('flow_unit_id')} missing required fields: {missing}",
                    )
                # Spot-check a few canonical values.
                self.assertEqual(units[0]["lifecycle_mode"], "dynamic-flow-gate")
                self.assertEqual(units[0]["runtime_status_source"], "example-data-only")
                self.assertEqual(units[0]["current_stage"], "initiation")
                self.assertEqual(units[0]["gate_lane"], "backlog")

    # ─── Test 8: unknown project type falls back ─────────────────────────────
    def test_unknown_project_type_falls_back(self):
        """An unrecognized project_type yields the safe single-unit fallback."""
        units = fud.derive_flow_units(
            "/path/to/x", "not-a-real-type", "some text", plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["flow_unit_id"], "x.script.whole")
        self.assertEqual(
            units[0]["derivation_reason"], "no-decomposable-structure-found"
        )

    def test_non_string_project_type_falls_back(self):
        """A non-string project_type (None/int) yields the fallback, never raises."""
        for bad in (None, 123, ["cli-tool"]):
            units = fud.derive_flow_units(
                "/path/to/x", bad, "text", plugin_home=PLUGIN_HOME
            )
            self.assertEqual(len(units), 1)

    # ─── Test 9: corrupt registry does not crash ─────────────────────────────
    def test_corrupt_registry_does_not_crash(self):
        """A nonexistent plugin_home (no registry) must NOT crash derivation.

        Fail-closed: the hardcoded defaults take over and derivation still
        works, returning decomposable units (not a fallback) because the
        parsing logic doesn't depend on the registry for the core keywords.
        """
        units = fud.derive_flow_units(
            "/path/to/my-cli",
            "cli-tool",
            CLI_TRACKER_DOTTED,
            plugin_home="/no/such/home/anywhere",
        )
        # Registry unavailable, but the hardcoded defaults let parsing work.
        self.assertEqual(len(units), 3)
        for u in units:
            self.assertEqual(u["unit_type"], "command")

    def test_corrupt_registry_fallback_unit_path(self):
        """Even with a corrupt registry, the empty-tracker path yields fallback."""
        units = fud.derive_flow_units(
            "/path/to/x",
            "cli-tool",
            EMPTY_TRACKER,
            plugin_home="/no/such/home",
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["flow_unit_id"], "x.script.whole")

    def test_none_plugin_home_uses_default(self):
        """plugin_home=None resolves to the real PLUGIN_HOME (registry loads)."""
        units = fud.derive_flow_units(
            "/path/to/my-cli", "cli-tool", CLI_TRACKER_DOTTED, plugin_home=None
        )
        self.assertEqual(len(units), 3)


class TestNeverRaises(unittest.TestCase):
    """The public API must NEVER raise on bad input."""

    def test_none_plan_tracker_text_does_not_raise(self):
        """plan_tracker_text=None triggers file read; missing file → fallback."""
        # No .governance/plan-tracker.md under a temp-ish path → empty → fallback.
        units = fud.derive_flow_units(
            "/no/such/project", "cli-tool", None, plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 1)
        self.assertIn("derivation_reason", units[0])

    def test_non_string_plan_tracker_text_does_not_raise(self):
        units = fud.derive_flow_units(
            "/path/to/x", "cli-tool", 12345, plugin_home=PLUGIN_HOME
        )
        self.assertIsInstance(units, list)
        self.assertGreaterEqual(len(units), 1)

    def test_none_target_root_does_not_raise(self):
        units = fud.derive_flow_units(
            None, "cli-tool", "init command", plugin_home=PLUGIN_HOME
        )
        self.assertGreaterEqual(len(units), 1)


class TestRegistryHelpers(unittest.TestCase):
    """The registry-access helpers are fail-closed and return sensible defaults."""

    def test_load_presets_missing_registry_returns_empty(self):
        self.assertEqual(fud._load_project_type_presets("/no/such/home"), {})

    def test_get_preset_missing_returns_none(self):
        self.assertIsNone(fud._get_preset("cli-tool", plugin_home="/no/such/home"))
        self.assertIsNone(fud._get_preset("not-a-type", plugin_home=PLUGIN_HOME))

    def test_resolve_default_unit_type_uses_registry_when_present(self):
        # With the real registry, cli-tool's default is "command".
        self.assertEqual(
            fud._resolve_default_unit_type("cli-tool", PLUGIN_HOME), "command"
        )

    def test_resolve_default_unit_type_falls_back_to_hardcoded(self):
        # Missing registry → hardcoded default.
        self.assertEqual(
            fud._resolve_default_unit_type("cli-tool", "/no/such/home"), "command"
        )
        self.assertEqual(
            fud._resolve_default_unit_type("game", "/no/such/home"), "chapter"
        )

    def test_default_unit_types_match_registry(self):
        """Hardcoded _DEFAULT_UNIT_TYPES must match the registry's declared defaults.

        This is the manual-sync guard: if someone updates the registry's
        default_flow_unit_type without updating the hardcoded fallback (or vice
        versa), this test catches the drift.
        """
        for ptype, expected in fud._DEFAULT_UNIT_TYPES.items():
            with self.subTest(ptype=ptype):
                registry_val = fud._resolve_default_unit_type(ptype, PLUGIN_HOME)
                self.assertEqual(
                    registry_val, expected,
                    f"{ptype}: hardcoded default={expected!r} but registry says "
                    f"{registry_val!r} — defaults drifted out of sync",
                )

    def test_resolve_unit_keywords_returns_list(self):
        kws = fud._resolve_unit_keywords("cli-tool", PLUGIN_HOME)
        self.assertIsInstance(kws, list)
        self.assertIn("command", kws)

    def test_resolve_unit_keywords_fallback(self):
        kws = fud._resolve_unit_keywords("cli-tool", "/no/such/home")
        self.assertEqual(kws, ["command"])


class TestWebAndMobileAndAiPlugin(unittest.TestCase):
    """Cover the remaining project types so §3.4 closure is complete."""

    def test_web_app_derives_stories(self):
        text = "- [ ] app.story.login\n- [ ] app.story.dashboard\n"
        units = fud.derive_flow_units(
            "/path/to/myapp", "web-app", text, plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 2)
        for u in units:
            self.assertEqual(u["unit_type"], "story")

    def test_mobile_app_derives_units(self):
        text = "screen: home\nscreen: settings\n"
        units = fud.derive_flow_units(
            "/path/to/mymob", "mobile-app", text, plugin_home=PLUGIN_HOME
        )
        self.assertGreaterEqual(len(units), 1)
        for u in units:
            self.assertEqual(u["project_type"], "mobile-app")

    def test_ai_agent_plugin_mixed_types(self):
        """An ai-agent-plugin with adapter + skill + manifest yields typed units."""
        text = (
            "- [ ] plugin.adapter.github\n"
            "- [ ] plugin.skill.code-review\n"
            "- [ ] plugin.manifest.main\n"
        )
        units = fud.derive_flow_units(
            "/path/to/myplugin", "ai-agent-plugin", text, plugin_home=PLUGIN_HOME
        )
        self.assertEqual(len(units), 3)
        types = sorted(u["unit_type"] for u in units)
        self.assertEqual(types, ["adapter", "manifest", "skill"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
