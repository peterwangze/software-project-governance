"""Unit tests for the dsh preset ↔ installed-schema compatibility guard.

Enforcement mapping for the failure this module exists to make impossible
(0.79.x / dsh 0.1.5 regression): a shipped preset row carried the config key
``text`` while the upgraded ``@deepseek-ai/dsh-persona`` declares
``prefix: z.string().required()``. The loader rejected the whole preset mount
(``invalid config: $.prefix missing required value``) and users could not
start a session — nothing in CI or in ``verify_workflow.py`` compared our
composition rows against the *installed* dsh's real schemas.

Covers:

  - Install discovery: the explicit ``DSH_INSTALL_DIR`` /
    ``DSH_HARNESS_NODE_MODULES`` override (node_modules dir *and* install
    root), a typo'd override that refuses to fall back to another install,
    the ``dsh``-on-PATH install-anchor walk, and the ``NOT_RUN`` degradation
    when nothing is discoverable.
  - Composition discovery: both shipped forms (``agent.cordis.yml`` and
    ``*.cordis.yml.template``) under the package root, excluding vendored
    trees.
  - Aggregation contract with an injected probe report: FAIL carries row id +
    module + schema message, a parse error is a finding, a partially
    unverified run degrades to PASS **with disclosure** (never a silent
    green), a fully unverified run degrades to NOT_RUN, and an absent install
    / absent node is NOT_RUN with zero gate issues.
  - Live oracle tests against the INSTALLED dsh (skipped, as NOT_RUN, when
    node or the harness install is absent — the repo's optional-tooling
    policy). These are the regression net for the real bug: the fixture whose
    persona row uses ``text`` MUST produce a FAIL naming ``persona`` and
    ``prefix``.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_dsh_compat.py" -v
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import dsh_compat  # noqa: E402
import dsh_fixtures  # noqa: E402

# FIX-310: the composition template IS the preset payload's render source
# (there is no second, self-locating composition any more), so the same file
# is both the "preset composition" and the "template composition" under test.
_PRESET_COMPOSITION = (
    _REPO_ROOT / "agent-presets" / "governance" / "agent.cordis.yml.template")
_TEMPLATE_COMPOSITION = _PRESET_COMPOSITION
_HAS_YAML = importlib.util.find_spec("yaml") is not None


@contextlib.contextmanager
def _scratch(prefix):
    """A ``tempfile.TemporaryDirectory`` that a file sandbox can write into.

    ``tempfile`` creates its directory with mode ``0o700``, whose
    non-inheriting DACL an ACL-based Windows file sandbox cannot write into;
    creating the directory with the default mode keeps the grant. Cleanup
    semantics are identical (the tree is removed on exit).
    """
    path = dsh_compat._make_scratch_dir(prefix)
    try:
        yield path
    finally:
        dsh_compat._remove_scratch_dir(path)


def _fake_install(node_modules):
    """Minimal install-shaped tree: ``<nm>/@deepseek-ai/dsh/package.json``."""
    package = Path(node_modules) / "@deepseek-ai" / "dsh"
    package.mkdir(parents=True, exist_ok=True)
    (package / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh", "version": "0.0.0-test"}),
        encoding="utf-8")
    return Path(node_modules)


_FAKE_ORACLE_VERSIONS = {
    "@deepseek-ai/cordis-plugin-loader": "1.0.3",
    "@deepseek-ai/cordis-plugin-include": "1.0.7",
    "@deepseek-ai/cordis": "4.0.2",
    "js-yaml": "4.3.2",
}


def _fake_plane(node_modules, versions=None):
    """A resolution plane carrying the four oracle packages the guard reports."""
    node_modules = Path(node_modules)
    for name, version in dict(_FAKE_ORACLE_VERSIONS, **(versions or {})).items():
        package = node_modules.joinpath(*name.split("/"))
        package.mkdir(parents=True, exist_ok=True)
        (package / "package.json").write_text(
            json.dumps({"name": name, "version": version}), encoding="utf-8")
    return node_modules


def _which_map(mapping):
    """``shutil.which`` seam resolving only the names in ``mapping``."""
    return lambda name: mapping.get(name)


def _probe_report(files, *, ok=True, probe=None):
    return {
        "status": "OK",
        "reason": "",
        "report": {"ok": ok, "error": None if ok else "oracle unavailable",
                   "probe": probe or {}, "files": files},
        "stdout": "",
        "stderr": "",
        "isolation": {"temp_home": "/tmp/fake", "home_writes": 0,
                      "mechanism": "injected probe"},
    }


def _file_entry(path, rows, *, status="OK", error="", enabled=None, checked=None):
    return {
        "path": str(path),
        "status": status,
        "error": error,
        "enabled": len(rows) if enabled is None else enabled,
        "checked": len(rows) if checked is None else checked,
        "rows": rows,
    }


def _row(row_id, name, kind, message=""):
    return {"row": row_id, "name": name, "kind": kind, "message": message}


# ── install discovery ───────────────────────────────────────────────────────
class InstallDiscoveryTests(unittest.TestCase):
    """The guard must find the installed harness without reading $DSH_HOME."""

    def test_override_accepts_a_node_modules_directory(self):
        with _scratch("spg-test-nm-") as td:
            node_modules = _fake_install(Path(td) / "node_modules")
            probe = dsh_compat.locate_dsh_install(
                env={dsh_compat.NODE_MODULES_ENV: str(node_modules)},
                which=_which_map({}))
        self.assertEqual(probe["status"], "OK")
        self.assertEqual(Path(probe["node_modules"]), node_modules)
        self.assertEqual(probe["source"], f"${dsh_compat.NODE_MODULES_ENV}")
        self.assertEqual(probe["dsh_version"], "0.0.0-test")

    def test_override_accepts_an_install_root(self):
        with _scratch("spg-test-root-") as td:
            node_modules = _fake_install(Path(td) / "node_modules")
            probe = dsh_compat.locate_dsh_install(
                env={dsh_compat.INSTALL_DIR_ENV: str(td)},
                which=_which_map({}))
        self.assertEqual(probe["status"], "OK")
        self.assertEqual(Path(probe["node_modules"]), node_modules)

    def test_invalid_override_reports_instead_of_falling_back(self):
        # A typo'd override must never be silently ignored: validating against
        # a different install than the operator asked for is exactly the drift
        # this guard exists to catch.
        probe = dsh_compat.locate_dsh_install(
            env={dsh_compat.INSTALL_DIR_ENV: str(_REPO_ROOT / "no-such-install")},
            which=_which_map({"dsh": str(_PRESET_COMPOSITION)}))
        self.assertEqual(probe["status"], "NOT_RUN")
        self.assertIn(dsh_compat.INSTALL_DIR_ENV, probe["reason"])
        self.assertIn("refusing to fall back", probe["reason"])
        self.assertIsNone(probe["node_modules"])

    def test_path_walk_finds_the_install_anchor_above_the_dsh_shim(self):
        with _scratch("spg-test-path-") as td:
            node_modules = _fake_install(Path(td) / "node_modules")
            bin_dir = node_modules / ".bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            shim = bin_dir / "dsh.CMD"
            shim.write_text("@echo off\n", encoding="utf-8")
            probe = dsh_compat.locate_dsh_install(
                env={}, which=_which_map({"dsh": str(shim)}))
        self.assertEqual(probe["status"], "OK")
        self.assertEqual(Path(probe["node_modules"]), node_modules)
        self.assertIn("PATH", probe["source"])

    def test_path_walk_finds_the_anchor_from_the_package_entry_point(self):
        with _scratch("spg-test-entry-") as td:
            node_modules = _fake_install(Path(td) / "node_modules")
            entry = node_modules / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("// entry\n", encoding="utf-8")
            probe = dsh_compat.locate_dsh_install(
                env={}, which=_which_map({"dsh": str(entry)}))
        self.assertEqual(probe["status"], "OK")
        self.assertEqual(Path(probe["node_modules"]), node_modules)

    def test_absent_install_degrades_to_not_run(self):
        probe = dsh_compat.locate_dsh_install(env={}, which=_which_map({}))
        self.assertEqual(probe["status"], "NOT_RUN")
        self.assertIn(dsh_compat.INSTALL_DIR_ENV, probe["reason"])
        self.assertIn(dsh_compat.NODE_MODULES_ENV, probe["reason"])

    def test_profile_plane_is_used_when_dsh_home_is_explicit(self):
        # dsh resolves a preset row's bare package names out of its profile
        # plane ($DSH_HOME/profiles/...), which is where the runtime BUNDLE
        # packages live — not out of the @deepseek-ai/dsh CLI package whose
        # version string is a different fact. Read-only, and only from an
        # explicitly exported DSH_HOME.
        with _scratch("spg-test-plane-") as td:
            plane = _fake_plane(Path(td) / "profiles" / "node_modules")
            probe = dsh_compat.locate_dsh_install(
                env={dsh_compat.DSH_HOME_ENV: td}, which=_which_map({}))
        self.assertEqual(probe["status"], "OK", probe)
        self.assertEqual(Path(probe["node_modules"]), plane)
        self.assertIn("profiles", probe["source"])
        self.assertIn("@deepseek-ai/cordis-plugin-loader",
                      probe["oracle_packages"])

    def test_per_profile_plane_wins_over_the_installation_mirror(self):
        # dsh's own ordering: a profile's pnpm-managed node_modules is
        # authoritative, the profiles/ mirror only fills the gap.
        with _scratch("spg-test-plane2-") as td:
            mirror = _fake_plane(
                Path(td) / "profiles" / "node_modules",
                versions={"@deepseek-ai/cordis-plugin-loader": "1.0.0"})
            per_profile = _fake_plane(
                Path(td) / "profiles" / "web" / "node_modules",
                versions={"@deepseek-ai/cordis-plugin-loader": "9.9.9"})
            probe = dsh_compat.locate_dsh_install(
                env={dsh_compat.DSH_HOME_ENV: td}, which=_which_map({}))
        self.assertEqual(Path(probe["node_modules"]), per_profile)
        self.assertEqual(probe["oracle_packages"][
            "@deepseek-ai/cordis-plugin-loader"]["version"], "9.9.9")
        others = {entry["node_modules"] for entry in probe["other_planes"]}
        self.assertIn(str(mirror), others)
        skew = [entry for entry in probe["other_planes"]
                if entry["node_modules"] == str(mirror)][0]
        self.assertEqual(skew["oracle_versions"][
            "@deepseek-ai/cordis-plugin-loader"], "1.0.0")

    def test_dsh_home_is_never_guessed_when_unset(self):
        # The profile plane is consulted only from an EXPLICITLY exported
        # DSH_HOME: an unset variable must not send the guard wandering into
        # a home it was not pointed at.
        with _scratch("spg-test-nohome-") as td:
            _fake_plane(Path(td) / "profiles" / "node_modules")
            probe = dsh_compat.locate_dsh_install(
                env={}, which=_which_map({}))
        self.assertEqual(probe["status"], "NOT_RUN", probe)
        self.assertIsNone(probe["node_modules"])

    def test_resolution_reports_a_cli_package_that_is_not_the_authority(self):
        with _scratch("spg-test-cli-") as td:
            plane = _fake_plane(Path(td) / "profiles" / "node_modules")
            package = plane / "@deepseek-ai" / "dsh"
            package.mkdir(parents=True, exist_ok=True)
            (package / "package.json").write_text(
                json.dumps({"name": "@deepseek-ai/dsh", "version": "0.0.1-cli"}),
                encoding="utf-8")
            probe = dsh_compat.locate_dsh_install(
                env={dsh_compat.DSH_HOME_ENV: td}, which=_which_map({}))
        self.assertEqual(probe["cli_package"]["version"], "0.0.1-cli")
        self.assertIn("informational", probe["cli_package"]["note"])
        # the oracle packages are the authority and are reported with paths
        oracle = probe["oracle_packages"]["@deepseek-ai/cordis"]
        self.assertEqual(oracle["version"], "4.0.2")
        self.assertTrue(oracle["path"])


# ── composition discovery ───────────────────────────────────────────────────
class CompositionDiscoveryTests(unittest.TestCase):
    def test_repo_compositions_are_discovered(self):
        found = [path.relative_to(_REPO_ROOT).as_posix()
                 for path in dsh_compat.discover_compositions(_REPO_ROOT)]
        # FIX-310: one shipped composition form — the preset payload's render
        # source. It must be discovered by the `*.cordis.yml.template` glob so
        # the schema guard covers what the renderers actually write.
        self.assertEqual(
            found, ["agent-presets/governance/agent.cordis.yml.template"], found)

    def test_discovery_is_sorted_and_skips_vendored_trees(self):
        with _scratch("spg-test-disc-") as td:
            root = Path(td)
            (root / "presets" / "b").mkdir(parents=True)
            (root / "presets" / "a").mkdir(parents=True)
            (root / "presets" / "b" / "agent.cordis.yml").write_text("[]\n", encoding="utf-8")
            (root / "presets" / "a" / "agent.cordis.yml").write_text("[]\n", encoding="utf-8")
            vendored = root / "node_modules" / "pkg"
            vendored.mkdir(parents=True)
            (vendored / "agent.cordis.yml").write_text("[]\n", encoding="utf-8")
            found = [path.relative_to(root).as_posix()
                     for path in dsh_compat.discover_compositions(root)]
        self.assertEqual(found, ["presets/a/agent.cordis.yml", "presets/b/agent.cordis.yml"])


# ── aggregation contract (probe injected) ───────────────────────────────────
class AggregationTests(unittest.TestCase):
    """Verdict/issue shaping, with the Node probe replaced by a fixture."""

    _INSTALL = {"status": "OK", "reason": "", "source": "$TEST",
                "node_modules": "C:/fake/node_modules",
                "dsh_package": "C:/fake/node_modules/@deepseek-ai/dsh",
                "dsh_version": "0.0.0-test"}

    def _run(self, files, *, compositions, ok=True):
        def runner(node, install, paths, root, timeout):
            return _probe_report(files, ok=ok)
        return dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[Path(path) for path in compositions],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=runner,
        )

    def test_all_rows_pass_is_pass(self):
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [_row("persona", "@deepseek-ai/dsh-persona", "PASS")])],
            compositions=[path])
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["rows_enabled"], 1)
        self.assertEqual(report["rows_checked"], 1)

    def test_invalid_config_is_fail_with_row_module_and_schema_message(self):
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [
                _row("persona", "@deepseek-ai/dsh-persona", "CONFIG_INVALID",
                     "$.prefix missing required value"),
            ])],
            compositions=[path])
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1)
        issue = report["issues"][0]
        self.assertIn("persona", issue)
        self.assertIn("@deepseek-ai/dsh-persona", issue)
        self.assertIn("prefix", issue)

    def test_unresolvable_module_and_expression_error_are_findings(self):
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [
                _row("gone", "@deepseek-ai/dsh-gone", "MODULE_UNRESOLVED", "cannot resolve"),
                _row("expr", "@deepseek-ai/dsh-tool-fs", "CONFIG_EXPR_ERROR", "threw"),
            ], checked=0)],
            compositions=[path])
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 2)

    def test_parse_error_is_a_finding(self):
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [], status="PARSE_ERROR", error="bad indentation")],
            compositions=[path])
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertIn("valid entry list", report["issues"][0])

    def test_no_schema_rows_only_degrades_to_not_run(self):
        # FIX-315 (V3) / design §4.4.1③. This test used to assert
        # `PASS` + `checked=0`, which is precisely the defect AUDIT-153
        # G-01 filed: a run that validated NOTHING reported a green verdict.
        # The rewritten expectation is the invariant, not a preference —
        # `rows_checked == 0` can never be PASS (design §4.3 L1).
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [
                _row("plan-mode", "@deepseek-ai/dsh-plan-mode", "NO_SCHEMA", "no Config"),
                _row("grp", "cordis:group", "BUILTIN", "builtin"),
            ], checked=0)],
            compositions=[path])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["rows_checked"], 0)
        self.assertEqual(report["rows_enabled"], 2)
        # The verdict reason states the denominator instead of claiming a
        # validation that did not happen ("0 enabled row(s) validated" next to
        # a PASS was the old, self-contradicting sentence).
        self.assertIn("NOT verified", report["reason"])
        self.assertIn("rows_verified 0 of 2", report["reason"])
        # Both unverified rows are disclosed on the report face …
        self.assertEqual(report["coverage"]["rows_verified"], 0)
        self.assertEqual(report["coverage"]["rows_unverified"], 2)
        self.assertEqual(dict(report["coverage"]["unverified_reasons"]),
                         {"NO_SCHEMA": 1, "BUILTIN": 1})
        self.assertEqual(len(report["unverified"]), 2, report["unverified"])
        self.assertTrue(any("NO_SCHEMA" in line for line in report["details"]))
        self.assertTrue(all("NOT verified" in line for line in report["unverified"]))

    def test_mixed_rows_pass_discloses_the_unverified_ones(self):
        # FIX-315 (V3) / design §4.4.1③: exactly one schema-bearing row plus
        # one row no schema can check. The verified surface may still PASS —
        # but only while naming the row it could not verify.
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [
                _row("persona", "@deepseek-ai/dsh-persona", "PASS"),
                _row("tool-ask-user", "@deepseek-ai/dsh-tool-ask-user",
                     "NO_SCHEMA", "no Config schema"),
            ], checked=1)],
            compositions=[path])
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["rows_checked"], 1)
        self.assertEqual(report["coverage"]["rows_unverified"], 1, report["coverage"])
        self.assertEqual(dict(report["coverage"]["unverified_reasons"]),
                         {"NO_SCHEMA": 1})
        self.assertEqual(len(report["unverified"]), 1, report["unverified"])
        self.assertIn("tool-ask-user", report["unverified"][0])
        # The reason carries both numbers: the verified denominator AND the
        # rows left unverified (G01-d).
        self.assertIn("verified 1 of 2", report["reason"])
        self.assertIn("1 enabled row(s) NOT verified", report["reason"])

    def test_everything_unverified_degrades_to_not_run(self):
        # Fail-closed: a run that verified nothing must never read as PASS.
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run(
            [_file_entry(path, [], status="UNREADABLE", error="denied")],
            compositions=[path])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertTrue(any("NOT verified" in line for line in report["details"]))

    def test_partially_verified_run_discloses_the_unverified_part(self):
        good = _REPO_ROOT / "good.cordis.yml"
        locked = _REPO_ROOT / "locked.cordis.yml"
        report = self._run(
            [_file_entry(good, [_row("tool-fs", "@deepseek-ai/dsh-tool-fs", "PASS")]),
             _file_entry(locked, [], status="UNREADABLE", error="denied")],
            compositions=[good, locked])
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["issues"], [])
        self.assertTrue(any("locked.cordis.yml" in line and "NOT verified" in line
                            for line in report["details"]), report["details"])

    def test_zero_enabled_rows_degrades_to_not_run(self):
        path = _REPO_ROOT / "fixture.cordis.yml"
        # FIX-311: "zero enabled rows" now has TWO distinguishable causes, so the
        # fixture names the one this test is about — a row that exists and is
        # disabled — instead of relying on the ambiguity of an empty row list.
        # (`_matrix_entry` derives `inherited_disabled` from the row kinds the
        # way the probe does.)
        report = self._run(
            [_matrix_entry(path, ("DISABLED_INHERITED",))],
            compositions=[path])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["rows_enabled"], 0, report)
        self.assertEqual(report["rows_inherited_disabled"], 1, report)
        # F4: "the preset mounts nothing" is named, not hidden behind a
        # generic unverified message.
        self.assertIn("would mount nothing", report["reason"])
        self.assertIn("disabled", report["reason"])

    def test_no_plugin_row_at_all_does_not_claim_disabled_rows(self):
        # FIX-311: the other cause of "zero enabled rows" — a composition whose
        # only record is a group row (G-02) or which declares no row at all.
        # Nothing measured a disabled row, so the verdict must not assert one.
        path = _REPO_ROOT / "fixture.cordis.yml"
        report = self._run([_file_entry(path, [], enabled=0, checked=0)],
                           compositions=[path])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertIn("would mount nothing", report["reason"])
        self.assertIn("no plugin row", report["reason"])
        self.assertNotIn("every row", report["reason"])

    def test_absent_install_is_not_run_with_zero_issues(self):
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            env={},
            which=_which_map({}),
            install={"status": "NOT_RUN", "reason": "no dsh install discovered",
                     "source": None, "node_modules": None, "dsh_package": None,
                     "dsh_version": None},
        )
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertIn("no dsh install discovered", report["reason"])

    def test_absent_node_is_not_run_with_zero_issues(self):
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            env={},
            which=_which_map({}),
            install=dict(self._INSTALL),
        )
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertIn("node executable not found", report["reason"])

    def test_missing_compositions_is_not_run(self):
        with _scratch("spg-test-empty-") as td:
            report = dsh_compat.check_dsh_preset_compat(root=td, env={},
                                                        which=_which_map({}))
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertIn("no preset composition found", report["reason"])

    def test_oracle_failure_is_not_run_not_fail(self):
        path = _REPO_ROOT / "fixture.cordis.yml"

        def runner(node, install, paths, root, timeout):
            return _probe_report([], ok=False)

        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT, compositions=[path], env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL), probe_runner=runner)
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertIn("oracle unavailable", report["reason"])


# ── FIX-315 / V3: "zero validations MUST NOT PASS" (design §4.3) ────────────
# Three independent invariants, one per layer. Any of them failing means a run
# that validated nothing can reach the user as a green verdict — the defect
# AUDIT-153 G-01 filed (5 `NO_SCHEMA` rows reported `PASS / checked 0`, and
# those rows did not even appear on screen).
#
#: All three are built on injected probe reports, so they need neither node nor
#: an installed harness: the invariant is about this guard's own decision and
#: rendering, and it must hold on every machine.

#: Row kinds that mean "this row's config WAS put through a schema".
_MATRIX_COMPARED_KINDS = ("PASS", "CONFIG_INVALID")
#: Row kinds the probe reports WITHOUT counting the row as enabled: it bumps
#: `inherited_disabled` and `continue`s before `enabled += 1` (a child of a
#: disabled ancestor never starts). Rendering one as an "enabled row not
#: verified" is the F-01 defect, so the fixture must model the split.
_MATRIX_NOT_STARTED_KINDS = ("DISABLED_INHERITED",)


def _matrix_entry(path, kinds, *, status="OK"):
    """A composition entry shaped exactly like the Node probe's output.

    The counters are **derived from the row kinds** the way the probe derives
    them, because a fixture whose counters disagree with its own rows would test
    the fixture instead of the guard:

    * ``enabled`` counts the rows the walk reached and either compared against a
      schema (`PASS`, or the comparison that produced `CONFIG_INVALID`) or had
      no schema to compare against (``UNVERIFIED_KINDS``);
    * ``inherited_disabled`` counts the rows that never started, and they are
      **not** part of ``enabled`` (F-01 — this is the split the probe makes at
      its `inherited_disabled += 1; continue`);
    * ``checked`` counts the comparisons that actually happened.
    """
    not_started = sum(1 for kind in kinds if kind in _MATRIX_NOT_STARTED_KINDS)
    checked = sum(1 for kind in kinds if kind in _MATRIX_COMPARED_KINDS)
    # FIX-311: a row under a group whose `disabled` expression threw is counted on
    # the probe's own `inherited_unverified` channel (G03-b), so the fixture
    # derives it the way the probe does rather than leaving the counter absent.
    inherited_unverified = sum(
        1 for kind in kinds if kind == "DISABLED_INHERITED_UNKNOWN")
    return {
        "path": str(path),
        "status": status,
        "error": "",
        "enabled": len(kinds) - not_started,
        "checked": checked,
        "inherited_disabled": not_started,
        "inherited_unverified": inherited_unverified,
        "rows": [_row(f"row-{index + 1}", f"@deepseek-ai/dsh-mod-{index + 1}", kind,
                      f"{kind} fixture message")
                 for index, kind in enumerate(kinds)],
    }


class ZeroVerificationInvariantTests(unittest.TestCase):
    """L1/L2/L3 — design §4.3, one test per layer.

    The matrix below is the "orthogonal subset" §4.3 L1 asks for: every
    combination of (verified row, unverified row, finding) at zero, one and
    two occurrences, plus the file-level shapes that also produce a report.
    """

    _INSTALL = {"status": "OK", "reason": "", "source": "$TEST",
                "node_modules": "C:/fake/node_modules",
                "dsh_package": "C:/fake/node_modules/@deepseek-ai/dsh",
                "dsh_version": "0.0.0-test"}

    #: (label, row kinds, file status)
    MATRIX = (
        ("only NO_SCHEMA rows", ("NO_SCHEMA", "NO_SCHEMA"), "OK"),
        ("only BUILTIN rows", ("BUILTIN",), "OK"),
        ("only inherited-disabled rows", ("DISABLED_INHERITED",), "OK"),
        ("mixed unverified kinds", ("NO_SCHEMA", "BUILTIN", "DISABLED_INHERITED"), "OK"),
        ("NO_SCHEMA plus a finding", ("NO_SCHEMA", "IMPORT_ERROR"), "OK"),
        ("one verified row", ("PASS",), "OK"),
        ("verified plus one unverified", ("PASS", "NO_SCHEMA"), "OK"),
        ("verified plus one inherited-disabled (F-01)", ("PASS", "DISABLED_INHERITED"), "OK"),
        ("two verified plus two unverified", ("PASS", "PASS", "NO_SCHEMA", "BUILTIN"), "OK"),
        ("only a finding", ("CONFIG_INVALID",), "OK"),
        ("unreadable composition", (), "UNREADABLE"),
    )

    def _report(self, kinds, status="OK"):
        path = _REPO_ROOT / "matrix.cordis.yml"
        return dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[path],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=lambda node, install, paths, root, timeout: _probe_report(
                [_matrix_entry(path, kinds, status=status)]),
        )

    # ── L1: report level ────────────────────────────────────────────────────
    def test_L1_zero_checked_rows_never_verdict_pass(self):
        """§4.3 L1 — no report may satisfy `rows_checked == 0 ∧ verdict == PASS`."""
        for label, kinds, status in self.MATRIX:
            with self.subTest(case=label, kinds=kinds, status=status):
                report = self._report(kinds, status)
                if report["rows_checked"] != 0:
                    continue
                self.assertIn(report["verdict"], ("FAIL", "NOT_RUN"), report)
                self.assertNotEqual(report["verdict"], "PASS", report)

    def test_L1_coverage_block_accounts_for_every_enabled_row(self):
        """G01-b — no enabled row falls outside the trust surface.

        ``verified + unverified == enabled``, exactly: every **enabled** row is
        either put through a schema or disclosed as unverifiable. A row the walk
        could not evaluate never reaches either state — an import failure is a
        finding, and a child of a disabled ancestor never starts (the probe
        counts it in `inherited_disabled`, **not** in `enabled`, F-01) — so
        neither is quietly filed as "verified" nor as "enabled but unverified".

        ``unverified_reasons`` is a histogram of the unverified ROWS only: a
        file-level fact has its own counter, so no row count is invented for a
        composition whose rows could not be read (F-03).
        """
        for label, kinds, status in self.MATRIX:
            with self.subTest(case=label, kinds=kinds, status=status):
                report = self._report(kinds, status)
                coverage = report["coverage"]
                unreached = sum(
                    1 for kind in kinds
                    if kind not in dsh_compat.UNVERIFIED_KINDS
                    and kind not in _MATRIX_COMPARED_KINDS
                    and kind not in _MATRIX_NOT_STARTED_KINDS)
                self.assertEqual(
                    coverage["rows_verified"] + coverage["rows_unverified"]
                    + unreached,
                    coverage["rows_enabled"], report["coverage"])
                self.assertEqual(coverage["rows_enabled"], report["rows_enabled"])
                self.assertEqual(coverage["rows_verified"], report["rows_checked"],
                                 report["coverage"])
                self.assertLessEqual(coverage["rows_verified"],
                                     coverage["rows_enabled"], report["coverage"])
                self.assertEqual(
                    sum(coverage["unverified_reasons"].values()),
                    coverage["rows_unverified"], report["coverage"])
                if status == "OK":
                    self.assertEqual(
                        sorted(coverage["unverified_reasons"]),
                        sorted({kind for kind in kinds
                                if kind in dsh_compat.UNVERIFIED_KINDS}),
                        report["coverage"])
                    self.assertEqual(coverage["unreadable_compositions"], 0,
                                     report["coverage"])
                else:
                    # The rows of an unreadable file are unknowable, so they are
                    # NOT part of the row histogram (a `UNREADABLE=0` bucket
                    # would read as "no unreadable composition"): the count of
                    # such compositions is its own fact, and the composition
                    # itself is disclosed on the `unverified` channel.
                    self.assertEqual(coverage["unreadable_compositions"], 1,
                                     report["coverage"])
                    self.assertNotIn("UNREADABLE", coverage["unverified_reasons"],
                                     report["coverage"])
                    self.assertEqual(coverage["rows_enabled"], 0, report["coverage"])
                    self.assertEqual(coverage["rows_unverified"], 0,
                                     report["coverage"])
                    self.assertEqual(len(report["unverified"]), 1,
                                     report["unverified"])
                    self.assertIn("could not be read", report["unverified"][0])

    def test_L1_verified_plus_inherited_disabled_is_not_self_contradictory(self):
        """F-01 — the exact shape the review measured with the real probe.

        One schema-checked row plus one child of a disabled ancestor: the probe
        reports `enabled=1 / checked=1 / inherited_disabled=1`. Counting the
        non-started row as an enabled-but-unverified row made the arithmetic
        wrong (``1 + 1 != 1``) **and** put a self-contradicting PASS sentence on
        screen ("verified 1 of 1 enabled row(s) …; 1 enabled row(s) NOT
        verified"), which is the very wording defect G01-d exists to remove.
        """
        report = self._report(("PASS", "DISABLED_INHERITED"))
        coverage = report["coverage"]
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["rows_enabled"], 1, report)
        self.assertEqual(report["rows_checked"], 1, report)
        self.assertEqual(report["rows_inherited_disabled"], 1, report)
        self.assertEqual(coverage["rows_enabled"], 1, coverage)
        self.assertEqual(coverage["rows_verified"], 1, coverage)
        self.assertEqual(coverage["rows_unverified"], 0, coverage)
        self.assertEqual(
            coverage["rows_verified"] + coverage["rows_unverified"],
            coverage["rows_enabled"], coverage)
        # No sentence may claim an enabled row went unverified when it did not.
        self.assertIn("verified 1 of 1 enabled row(s)", report["reason"])
        self.assertNotIn("enabled row(s) NOT verified", report["reason"])
        self.assertEqual(report["unverified"], [], report["unverified"])
        # …and the non-started row is still disclosed, just under its own fact:
        # every surface reports the `inherited-disabled rows:` count, and the
        # detail-carrying surfaces print the row itself.
        out = self._render(report, "section")
        self.assertIn("inherited-disabled rows: 1", out, out)
        self.assertNotIn("[NOT_RUN]", out, out)
        cli_out = self._render(report, "cli")
        self.assertIn("inherited-disabled rows: 1", cli_out, cli_out)
        self.assertIn("DISABLED_INHERITED", cli_out, cli_out)
        human = io.StringIO()
        dsh_compat._print_human(report, human)
        self.assertIn("DISABLED_INHERITED", human.getvalue(), human.getvalue())
        self.assertIn("(writes: 0)", human.getvalue(), human.getvalue())

    def test_L1_inherited_disabled_rows_are_still_disclosed(self):
        """F-01 — removing `DISABLED_INHERITED` from the unverified half must
        not make the row disappear.

        Its disclosure path is the `inherited_disabled` counter (every surface
        prints the count) plus the row's own `details` line, and the F4
        "would mount nothing" branch when nothing else is enabled — not the
        `[NOT_RUN]` line, which is reserved for enabled rows.
        """
        report = self._report(("DISABLED_INHERITED",))
        self.assertEqual(report["rows_inherited_disabled"], 1, report)
        self.assertEqual(report["rows_enabled"], 0, report)
        self.assertEqual(report["coverage"]["rows_unverified"], 0,
                         report["coverage"])
        self.assertTrue(any("DISABLED_INHERITED" in line
                            for line in report["details"]), report["details"])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertIn("would mount nothing", report["reason"])
        out = self._render(report, "section")
        self.assertIn("inherited-disabled rows: 1", out, out)

    def test_L1_unreadable_only_names_the_read_failure_not_disabled_rows(self):
        """F-06 — a file we never opened must not be explained as "all rows are
        disabled": that names the wrong cause on the only line the user reads.
        """
        report = self._report((), "UNREADABLE")
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertIn("could not be read", report["reason"])
        self.assertIn("rows NOT verified", report["reason"])
        self.assertNotIn("would mount nothing", report["reason"])
        self.assertNotIn("disabled", report["reason"])
        self.assertEqual(report["coverage"]["unreadable_compositions"], 1,
                         report["coverage"])

    def test_L1_findings_still_win_over_the_zero_checked_degradation(self):
        # Ordering matters: a rejected row is a FAIL (a real, actionable
        # defect), not a NOT_RUN. Degrading a finding to "unverified" would
        # trade one wrong verdict for another.
        report = self._report(("NO_SCHEMA", "CONFIG_INVALID"))
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1, report["issues"])
        self.assertEqual(report["coverage"]["rows_unverified"], 1, report["coverage"])

    # ── L2: render level ────────────────────────────────────────────────────
    def _render(self, report, renderer="section"):
        """Capture one render surface for an already-built report.

        The render entry points run the guard themselves, so the guard is
        patched to return ``report`` — the Renderer must then be judged purely
        on what it does with a given report, which is exactly the L2/L3
        question.
        """
        stream = io.StringIO()
        with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                               return_value=report):
            if renderer == "section":
                dsh_compat.emit_check_section(stream=stream)
            else:
                dsh_compat.run_cli(stream=stream)
        return stream.getvalue()

    def test_L2_zero_checked_report_never_renders_pass(self):
        """§4.3 L2 — a zero-checked report renders `[NOT_RUN]`, never `[PASS]`."""
        for renderer in ("section", "cli"):
            with self.subTest(renderer=renderer):
                out = self._render(self._report(("NO_SCHEMA",)), renderer)
                self.assertNotIn("[PASS]", out, out)
                self.assertIn("[NOT_RUN]", out, out)
                self.assertIn("schema-checked rows: 0", out, out)
                if renderer == "cli":
                    # `run_cli`'s terminal token has no brackets, so the
                    # bracket assertion above cannot see a regression on that
                    # surface (F-04b): assert the token's own spelling.
                    self.assertIn("Result: NOT_RUN", out, out)
                    self.assertNotIn("Result: PASSED", out, out)

    def test_L2_zero_checked_report_lists_each_unverified_row(self):
        out = self._render(self._report(("NO_SCHEMA", "BUILTIN")), "section")
        self.assertIn("[NO_SCHEMA]", out, out)
        self.assertIn("[BUILTIN]", out, out)
        self.assertIn('row "row-1"', out, out)
        self.assertIn('row "row-2"', out, out)

    def test_L2_unreadable_composition_is_disclosed_by_both_surfaces(self):
        """F-02 — a composition nobody could read must not vanish from a PASS run.

        The three surfaces render from the structured `unverified` set, so a
        file-level unverified fact has to travel on that same channel: when it
        lived only in `details`, both `emit_check_section` and `run_cli` printed
        nothing for it, which is the "unverified fact off the screen" defect this
        slice exists to remove.
        """
        good = _REPO_ROOT / "good.cordis.yml"
        locked = _REPO_ROOT / "locked.cordis.yml"
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[good, locked],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=lambda node, install, paths, root, timeout: _probe_report([
                _file_entry(good, [_row("persona", "@deepseek-ai/dsh-persona", "PASS")]),
                _file_entry(locked, [], status="UNREADABLE", error="ENOENT: no such file"),
            ]),
        )
        # The verified half still passes — that is the point: the disclosure has
        # to survive a green verdict.
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["coverage"]["unreadable_compositions"], 1,
                         report["coverage"])
        self.assertEqual(len(report["unverified"]), 1, report["unverified"])
        self.assertIn("could not be read", report["unverified"][0])
        self.assertIn("ENOENT", report["unverified"][0])
        for renderer in ("section", "cli"):
            with self.subTest(renderer=renderer):
                out = self._render(report, renderer)
                self.assertIn(report["unverified"][0], out, out)
                self.assertIn("[NOT_RUN]", out, out)
                self.assertIn("ENOENT", out, out)
        human = io.StringIO()
        dsh_compat._print_human(report, human)
        self.assertIn("ENOENT", human.getvalue(), human.getvalue())

    # ── L3: disclosure level ────────────────────────────────────────────────
    def test_L3_partial_pass_discloses_every_unverified_row(self):
        """§4.3 L3 — a mixed report must put its unverified rows on screen."""
        for renderer in ("section", "cli"):
            with self.subTest(renderer=renderer):
                report = self._report(("PASS", "PASS", "NO_SCHEMA", "BUILTIN"))
                self.assertEqual(report["verdict"], "PASS", report)
                self.assertEqual(len(report["unverified"]), 2, report["unverified"])
                out = self._render(report, renderer)
                for line in report["unverified"]:
                    self.assertIn(line, out, out)
                # Judged by the structured kind, not by a substring: the
                # disclosure survives any rewording of a row message.
                self.assertIn("[NO_SCHEMA]", out, out)
                self.assertIn("[BUILTIN]", out, out)
                # The verified denominator is stated, so "verified 2 of 4" can
                # never be read as "4 rows validated" (G01-d).
                self.assertIn("verified 2 of 4", out, out)
                self.assertIn("2 enabled row(s) NOT verified", out, out)

    def test_L3_disclosure_is_kind_driven_not_message_driven(self):
        # The regression this pins down: the old render branch printed a
        # detail only when its TEXT contained "NOT verified", while the
        # `NO_SCHEMA` message never did — five unverified rows were therefore
        # invisible on a PASS screen. A row whose message contains no such
        # substring must still be disclosed.
        path = _REPO_ROOT / "kind-driven.cordis.yml"
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[path],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=lambda node, install, paths, root, timeout: _probe_report(
                [{"path": str(path), "status": "OK", "error": "", "enabled": 2,
                  "checked": 1, "inherited_disabled": 0,
                  "rows": [_row("ok", "@deepseek-ai/dsh-persona", "PASS"),
                           _row("silent", "@deepseek-ai/dsh-tool-ask-user",
                                "NO_SCHEMA", "message text without the old marker")]}]),
        )
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertNotIn("NOT verified", report["compositions"][0]["rows"][1]["message"])
        out = self._render(report, "section")
        self.assertIn("message text without the old marker", out, out)
        # Exactly one disclosure *line* (the verdict line mentions [NOT_RUN]
        # too; the count is of lines the renderer emitted for unverified rows).
        self.assertEqual(len([line for line in out.splitlines()
                              if "[NOT_RUN]" in line and "[PASS]" not in line]),
                         1, out)

    def test_L3_the_render_is_not_the_old_substring_scan(self):
        """F-04(a) — pin the ROOT-CAUSE fix, not just its current output.

        Reverting the render branches to the HEAD form
        (``for detail in details: if "NOT verified" in detail``) keeps the rest
        of the suite green, because today's disclosure lines happen to contain
        that phrase and to live in `details` too. So the suite must assert the
        *difference* between the two mechanisms:

        * **false negative** — a row disclosed because its KIND says unverified
          but whose message never says "NOT verified" (the real §4.4.1 G-01④
          root cause);
        * **false positive** — a detail line that is not an unverified item at
          all, carrying the phrase only as prose;
        * **file level** — an unreadable composition, whose line is a file fact
          rather than a row fact.

        Any of the three reverted to a substring scan changes the asserted line
        set, so the mutation is caught here.
        """
        # ── false positive: a report whose DETAIL lines carry the phrase as
        #    prose while the actual unverified set excludes them. The old
        #    mechanism would print those prose lines as `[NOT_RUN]` disclosures;
        #    dropping one of them (the mechanism change under test) is what this
        #    pins. Artwork directly on top of a real report, because the phrase
        #    has to appear in a detail line for the asymmetry to exist at all.
        path = _REPO_ROOT / "substring.cordis.yml"
        report = self._report(("PASS", "BUILTIN", "NO_SCHEMA"))
        report["details"].append(
            f"{path.as_posix()}: row \"noise\" (@deepseek-ai/dsh-noise) "
            f"[NO_SCHEMA] — NOT verified: prose that is not a disclosure")
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(len(report["unverified"]), 2, report["unverified"])
        self.assertEqual(
            len([line for line in report["details"] if "NOT verified" in line]), 3,
            report["details"])

        out = self._render(report, "section")
        structured = [line for line in out.splitlines()
                      if "[NOT_RUN]" in line and "[PASS]" not in line]
        # The screen shows exactly the two unverified rows — not three: the
        # prose detail is NOT promoted, because selection is by kind.
        self.assertEqual(len(structured), 2, out)
        for line in report["unverified"]:
            self.assertIn(line, out, out)
        self.assertNotIn("noise", out, out)
        # (2) the disclosure is kind-labelled, so a rewording cannot hide it.
        for kind in ("BUILTIN", "NO_SCHEMA"):
            self.assertIn(f"[{kind}]", out, out)

        # ── false negative: the same shape with the phrase removed from every
        #    unverified message — a substring scan would disclose NOTHING, while
        #    the structured set still finds both (the G-01④ root cause). This is
        #    the direction the old code failed in, kept as its own case so both
        #    directions of the asymmetry are pinned.
        bare = self._report(("PASS", "BUILTIN", "NO_SCHEMA"))
        for row in bare["compositions"][0]["rows"][1:]:
            row["message"] = "message reworded with no marker"
        bare["details"] = [line for line in bare["details"]
                           if "NOT verified" not in line]
        self.assertEqual(bare["verdict"], "PASS", bare)
        self.assertEqual(len(bare["unverified"]), 2, bare["unverified"])
        self.assertEqual([line for line in bare["details"]
                          if "NOT verified" in line], [], bare["details"])
        bare_out = self._render(bare, "section")
        bare_lines = [line for line in bare_out.splitlines()
                      if "[NOT_RUN]" in line and "[PASS]" not in line]
        self.assertEqual(len(bare_lines), 2, bare_out)
        self.assertNotIn("NOT verified", bare["compositions"][0]["rows"][1]["message"])


# ── the pure-Python floor: no node, no dsh install required ─────────────────
_PERSONA_MODULE = "@deepseek-ai/dsh-persona"


def _iter_rows(rows, at=""):
    """Yield ``(label, row)`` for every leaf row, recursing into groups.

    A deliberately tiny reader: it needs neither the loader dialect nor the
    installed harness, so the structural floor below still bites on a machine
    with no node at all.
    """
    if not isinstance(rows, list):
        return
    for index, row in enumerate(rows):
        label = at or f"row {index + 1}"
        if not isinstance(row, dict):
            continue
        if row.get("group"):
            yield from _iter_rows(row.get("config"), label)
            continue
        yield (row.get("id") or label), row


def _parse_composition(path):
    """Parse a composition just far enough for a structural assertion.

    ``!!js`` scalars are accepted as opaque strings (the loader's own
    ``entryListSchema`` is exercised by the live tests); PyYAML is optional, so
    the caller degrades to NOT_RUN when it is missing.
    """
    import yaml

    class JsTolerantLoader(yaml.SafeLoader):
        """Accept the composition's ``!!js`` tag as an opaque scalar."""

    def _js_constructor(loader, tag_suffix, node):
        return loader.construct_scalar(node)

    JsTolerantLoader.add_multi_constructor("tag:yaml.org,2002:js", _js_constructor)
    return yaml.load(path.read_text(encoding="utf-8"), Loader=JsTolerantLoader)


def _check_persona_contract(case, path, label, config):
    """The shared structural contract, factored out so a fixture can exercise it.

    Kept as one function so the assertions the real compositions go through are
    literally the ones the negative control below drives.
    """
    case.assertIsInstance(config, dict, f"{path}: persona row {label} has no config map")
    case.assertIn("prefix", config,
                  f"{path}: persona row {label} must carry `prefix`; the "
                  f"installed {_PERSONA_MODULE} declares it required, and the "
                  f"loader rejects the WHOLE preset mount on a mismatch")
    case.assertNotIn("text", config,
                     f"{path}: persona row {label} carries `text`; the installed "
                     f"{_PERSONA_MODULE} declares `prefix`, so the preset would "
                     f"not mount")


class RowKindClassificationTests(unittest.TestCase):
    """G-18 / FIX-311 — the classification table is guarded, and it fails loud.

    The audit's G-18: `FINDING_KINDS` is a claim about the trust surface
    ("everything else is at most a disclosure") but nothing guarded the claim.
    The companion defect (F-R1-03) is the render layer's consequence: it selected
    `[INFO]` lines by ELIMINATION (`kind ∉ FINDING_KINDS ∪ UNVERIFIED_KINDS ∧
    kind ≠ "PASS"`), so a kind the table did not know landed in `[INFO]` and
    changed no verdict. These tests pin both halves: the vocabulary is
    exhaustive and disjoint, and an undeclared kind is a finding, never `[INFO]`.
    """

    _INSTALL = ZeroVerificationInvariantTests._INSTALL

    def _report(self, kinds):
        path = _REPO_ROOT / "kinds.cordis.yml"
        return dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[path],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=lambda node, install, paths, root, timeout: _probe_report(
                [_matrix_entry(path, kinds)]))

    # ── the vocabulary ──────────────────────────────────────────────────────
    def test_every_kind_belongs_to_exactly_one_category(self):
        """§6.1 V4③ — "each kind belongs to exactly one class", asserted.

        The tables are pairwise disjoint, and each one round-trips through the
        single classifier back to its own category. A kind that drifts into two
        tables (or is misspelled in one) fails here rather than silently moving a
        verdict.
        """
        tables = {dsh_compat.CATEGORY_FINDING: dsh_compat.FINDING_KINDS,
                  dsh_compat.CATEGORY_UNVERIFIED: dsh_compat.UNVERIFIED_KINDS,
                  dsh_compat.CATEGORY_INFO: dsh_compat.INFO_KINDS,
                  dsh_compat.CATEGORY_PASS: (dsh_compat.PASS_KIND,)}
        seen = {}
        for category, kinds in tables.items():
            self.assertTrue(kinds, f"{category} must not be empty")
            for kind in kinds:
                self.assertNotIn(kind, seen,
                                 f"{kind!r} appears in {seen.get(kind)} and {category}")
                seen[kind] = category
                self.assertEqual(dsh_compat._classify_row_kind(kind), category)
        # The coverage table the slice's acceptance asks for: every kind the
        # guard can now emit, exactly once, over the four categories.
        self.assertEqual(sorted(seen), sorted([
            "CONFIG_INVALID", "MODULE_UNRESOLVED", "IMPORT_ERROR",
            "CONFIG_EXPR_ERROR", "DISABLED_EXPR_ERROR", "ROW_SHAPE",
            "GROUP_NAME_UNRESOLVED",
            "NO_SCHEMA", "BUILTIN", "DISABLED_INHERITED_UNKNOWN",
            "DISABLED_INHERITED", "PASS",
        ]), seen)
        # `_assert_kind_tables` is called at import; calling it again must stay
        # silent on a consistent table (and is what a new kind would break).
        dsh_compat._assert_kind_tables()

    def test_the_declared_tables_are_the_only_source_of_a_category(self):
        # No consumer may re-derive a category: the verdict, the `[NOT_RUN]`
        # disclosure and the `[INFO]` face all ask `_classify_row`.
        self.assertEqual(dsh_compat._classify_row_kind("NO_SCHEMA"),
                         dsh_compat.CATEGORY_UNVERIFIED)
        self.assertEqual(dsh_compat._classify_row_kind("DISABLED_INHERITED"),
                         dsh_compat.CATEGORY_INFO)
        self.assertEqual(dsh_compat._classify_row_kind("GROUP_NAME_UNRESOLVED"),
                         dsh_compat.CATEGORY_FINDING)
        self.assertEqual(dsh_compat._classify_row_kind("DISABLED_INHERITED_UNKNOWN"),
                         dsh_compat.CATEGORY_UNVERIFIED)
        self.assertEqual(dsh_compat._classify_row_kind("PASS"),
                         dsh_compat.CATEGORY_PASS)

    # ── the self-check over a report ────────────────────────────────────────
    def test_an_undeclared_kind_is_a_finding_never_an_info_line(self):
        """G-18 / F-R1-03 — the residual bucket is gone.

        A kind in no table must become a gate issue. Before this slice it printed
        as `[INFO]` and changed nothing, which is exactly how a future probe
        diagnostic would have gone unnoticed.
        """
        report = self._report(("PASS", "SOME_FUTURE_PROBE_KIND"))
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1, report["issues"])
        self.assertIn("SOME_FUTURE_PROBE_KIND", report["issues"][0])
        self.assertIn("undeclared row kind", report["issues"][0])
        # …and it is NOT quietly filed as an `[INFO]` line: the render face
        # fails loud on it rather than printing it as information (the residual
        # selection this replaced would have printed it and changed nothing).
        with self.assertRaises(ValueError) as caught:
            dsh_compat._informational_details(report)
        self.assertIn("SOME_FUTURE_PROBE_KIND", str(caught.exception))

    def test_the_report_level_self_check_raises_on_an_undeclared_kind(self):
        # The render layer's own guard: if a report somehow carries a kind in no
        # table, `_informational_details` fails loud instead of printing it as
        # information.
        report = self._report(("DISABLED_INHERITED",))
        self.assertEqual(len(dsh_compat._informational_details(report)), 1)
        report["compositions"][0]["rows"].append(
            _row("future", "@deepseek-ai/dsh-future", "SOME_FUTURE_PROBE_KIND"))
        with self.assertRaises(ValueError) as caught:
            dsh_compat._informational_details(report)
        self.assertIn("SOME_FUTURE_PROBE_KIND", str(caught.exception))
        self.assertIn("G-18", str(caught.exception))

    def test_a_group_record_is_info_not_an_unverified_config(self):
        # FIX-311: a group row is recorded as BUILTIN (G02-a) but it is
        # STRUCTURE — it carries a child count, not a config — so it must not
        # enter `unverified_reasons` (which stays "enabled rows whose config was
        # not verified") and must not change the verdict.
        report = self._report(("PASS", "BUILTIN"))
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["rows_enabled"], 2, report)
        self.assertEqual(report["rows_checked"], 1, report)
        self.assertEqual(dict(report["coverage"]["unverified_reasons"]),
                         {"BUILTIN": 1}, report["coverage"])
        report["compositions"][0]["rows"].append({
            "row": "planning", "name": "cordis:group", "kind": "BUILTIN",
            "builtin": "group", "children": 1,
            "message": "group builtin — 1 child row(s) enumerated"})
        self.assertEqual(
            dsh_compat._classify_row(report["compositions"][0]["rows"][-1]),
            dsh_compat.CATEGORY_INFO)
        self.assertEqual(
            dsh_compat._classify_row_kind("BUILTIN"),
            dsh_compat.CATEGORY_UNVERIFIED)
        lines = dsh_compat._informational_details(report)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("cordis:group", lines[0])

    def test_every_declared_kind_round_trips_through_a_real_report(self):
        # The classifier is what the verdict turns on: driving each declared kind
        # through the aggregation must land it in its declared category — a
        # finding gates, an unverified kind is disclosed, INFO is not a gate
        # issue, PASS neither. Any divergence shows up as a wrong verdict here.
        for kind in dsh_compat.FINDING_KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(self._report((kind,))["verdict"], "FAIL")
        for kind in dsh_compat.UNVERIFIED_KINDS:
            with self.subTest(kind=kind):
                report = self._report((kind,))
                self.assertEqual(report["issues"], [], report["issues"])
                self.assertIn(report["verdict"], ("NOT_RUN", "FAIL"), report)
                self.assertEqual(dict(report["coverage"]["unverified_reasons"]),
                                 {kind: 1}, report["coverage"])
        for kind in dsh_compat.INFO_KINDS:
            with self.subTest(kind=kind):
                report = self._report((dsh_compat.PASS_KIND, kind))
                self.assertEqual(report["verdict"], "PASS", report)
                self.assertEqual(report["coverage"]["rows_unverified"], 0,
                                 report["coverage"])
                self.assertEqual(len(dsh_compat._informational_details(report)), 1)


@unittest.skipUnless(_HAS_YAML,
                     "PyYAML unavailable (optional, NOT_RUN per repo policy)")
class CompositionRowContractTests(unittest.TestCase):
    """The (a) half of the regression net — pure Python, no oracle needed.

    The independent review of this defect found that the pre-existing suite is
    green on a composition whose persona row carries ``text``, and stays green
    when the key is renamed to ``preamble``: nothing read the row's config keys
    at all. This class closes that with a structural assertion that needs
    neither ``node`` nor an installed ``dsh``, so the common case (a developer
    machine, CI without the harness) still has a net. The authoritative check —
    "does the INSTALLED package's own ``Config`` accept this row" — is
    :class:`InstalledSchemaTests`; this is its floor, never its replacement.
    """

    def _persona_config(self, path):
        if not path.is_file():
            self.skipTest(f"{path.name} not present in this checkout")
        try:
            rows = _parse_composition(path)
        except OSError as exc:
            # A file sandbox can deny the read; that is NOT_RUN, never a FAIL
            # and never a silent pass (repo optional-tooling policy).
            self.skipTest(f"composition unreadable ({exc.__class__.__name__}): {path}")
        self.assertIsInstance(rows, list, f"{path}: composition must be a row list")
        for label, row in _iter_rows(rows):
            if row.get("name") == _PERSONA_MODULE:
                return label, row.get("config")
        self.fail(f"{path}: no {_PERSONA_MODULE} row found")

    def test_shipped_preset_persona_row_declares_prefix_not_text(self):
        label, config = self._persona_config(_PRESET_COMPOSITION)
        _check_persona_contract(self, _PRESET_COMPOSITION, label, config)

    def test_shipped_template_persona_row_declares_prefix_not_text(self):
        label, config = self._persona_config(_TEMPLATE_COMPOSITION)
        _check_persona_contract(self, _TEMPLATE_COMPOSITION, label, config)

    def test_persona_config_is_not_a_placeholder(self):
        # The pair above would also pass on an empty prefix; a persona that
        # renders nothing is the same user-facing failure by another route.
        for path in (_PRESET_COMPOSITION, _TEMPLATE_COMPOSITION):
            label, config = self._persona_config(path)
            with self.subTest(composition=path.name):
                self.assertTrue(str(config.get("prefix", "")).strip(),
                                f"{path}: persona row {label} has an empty prefix")

    def test_structural_floor_fires_on_the_pre_fix_shape(self):
        # Negative control for the floor ITSELF: on the shape that shipped
        # (``text`` instead of ``prefix``) the shared contract must reject.
        # Without this, the two assertions above could rot into no-ops and the
        # class would still look green.
        with _scratch("spg-test-struct-") as td:
            path = Path(td) / "agent.cordis.yml"
            path.write_text(
                "- id: persona\n"
                f"  name: '{_PERSONA_MODULE}'\n"
                "  config:\n"
                "    text: 'the pre-fix key'\n",
                encoding="utf-8")
            label, config = self._persona_config(path)
        with self.assertRaises(AssertionError):
            _check_persona_contract(self, path, label, config)

    def test_structural_floor_accepts_the_post_fix_shape(self):
        with _scratch("spg-test-struct-ok-") as td:
            path = Path(td) / "agent.cordis.yml"
            path.write_text(
                "- id: persona\n"
                f"  name: '{_PERSONA_MODULE}'\n"
                "  config:\n"
                "    prefix: 'the post-fix key'\n",
                encoding="utf-8")
            label, config = self._persona_config(path)
        _check_persona_contract(self, path, label, config)


# ── the live oracle: real installed dsh, real Config schemas ────────────────
def _live_probe():
    """(install, node) when the real oracle is reachable, else (None, None)."""
    install = dsh_compat.locate_dsh_install()
    node = shutil.which("node")
    if install.get("status") != "OK" or not node:
        return None, None
    return install, node


_LIVE_INSTALL, _LIVE_NODE = _live_probe()
_LIVE_SKIP = ("live dsh oracle unavailable (node and/or the installed dsh "
              "install not discoverable) — NOT_RUN, per the repo's "
              "optional-tooling policy")


class InstalledSchemaTests(unittest.TestCase):
    """The regression net: real compositions, real installed Config schemas."""

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_persona_row_using_text_is_rejected_naming_persona_and_prefix(self):
        # THE regression this guard exists for: the row key was `text` while
        # the installed @deepseek-ai/dsh-persona declares
        # `prefix: z.string().required()`. Before this guard, the defect was
        # discovered by users whose preset would not mount at all.
        with _scratch("spg-test-neg-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: persona\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  config:\n"
                "    text: |-\n"
                "      regression fixture: the pre-fix key\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1, report["issues"])
        issue = report["issues"][0]
        self.assertIn("persona", issue)
        self.assertIn("prefix", issue)
        self.assertIn("@deepseek-ai/dsh-persona", issue)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_persona_row_using_prefix_passes(self):
        with _scratch("spg-test-pos-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: persona\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  config:\n"
                "    prefix: 'regression fixture: the post-fix key'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["issues"], [])
        kinds = {row["kind"] for row in report["compositions"][0]["rows"]}
        self.assertEqual(kinds, {"PASS"})

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_disabled_rows_are_not_validated(self):
        # The loader starts a row only when Boolean(disabled) is false; a
        # guard that validated disabled rows would fail compositions the
        # loader accepts.
        with _scratch("spg-test-dis-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: persona\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  disabled: true\n"
                "  config:\n"
                "    text: 'would be rejected if it were validated'\n"
                "- id: persona-js\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  disabled: !!js true\n"
                "  config:\n"
                "    text: 'same, via the loader expression form'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["rows_enabled"], 0)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_group_rows_recurse_into_their_config_list(self):
        with _scratch("spg-test-grp-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: planning\n"
                "  name: cordis:group\n"
                "  group: true\n"
                "  config:\n"
                "    - id: persona\n"
                "      name: '@deepseek-ai/dsh-persona'\n"
                "      config:\n"
                "        text: 'nested row carries the pre-fix key'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertIn("persona", report["issues"][0])
        self.assertIn("prefix", report["issues"][0])

    def _group_disabled_report(self, td, disabled_line):
        composition = Path(td) / "agent.cordis.yml"
        composition.write_text(
            "- id: planning\n"
            "  name: cordis:group\n"
            "  group: true\n"
            f"  disabled: {disabled_line}\n"
            "  config:\n"
            "    - id: persona\n"
            "      name: '@deepseek-ai/dsh-persona'\n"
            "      config:\n"
            "        text: 'broken child under a disabled group'\n",
            encoding="utf-8")
        return dsh_compat.check_dsh_preset_compat(
            root=Path(td), compositions=[composition], env={},
            install=_LIVE_INSTALL, node=_LIVE_NODE)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_t05_child_of_a_disabled_group_is_not_a_finding(self):
        # Entry._disabled walks the OWNING-PARENT chain
        # (`while (entry) { if (this.disabledOf(entry.options)) return true; … }`),
        # so a child of a `disabled: true` group never starts. Reporting its
        # config would be a false FAIL on a composition the loader accepts —
        # the worst direction for a gate people must trust.
        with _scratch("spg-test-t05-") as td:
            report = self._group_disabled_report(td, "true")
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["rows_enabled"], 0)
        self.assertEqual(report["rows_inherited_disabled"], 1)
        self.assertTrue(
            any("DISABLED_INHERITED" in line and "planning" in line
                for line in report["details"]), report["details"])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_t06_child_of_a_js_disabled_group_is_not_a_finding(self):
        with _scratch("spg-test-t06-") as td:
            report = self._group_disabled_report(td, "!!js true")
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["rows_inherited_disabled"], 1)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_group_enabled_child_is_still_validated(self):
        # The complement of t05/t06: `disabled: false` must NOT suppress the
        # child — the inheritance rule may not decay into "never validate
        # inside a group".
        with _scratch("spg-test-t05b-") as td:
            report = self._group_disabled_report(td, "false")
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(report["rows_inherited_disabled"], 0)
        self.assertIn("prefix", report["issues"][0])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_throwing_group_disabled_expression_is_a_finding(self):
        # FIX-311 (V4) / design §4.4.2③ — **C-23 expected rewrite, not a
        # regression**. This test used to assert only "a throwing group
        # expression is a finding", on the comment that "`disabledOf` is called
        # unguarded by the loader's ancestor walk". That is true OF THE ANCESTOR
        # WALK and false of the group itself: `Entry._disabled` line 1
        # (`if (options.group) return false`) short-circuits the group's own
        # `disabled`, so nothing evaluates it *at the group row*. What the old
        # expectation encoded — FAIL at the group row and stop — also swallowed
        # the child: `continue` left it out of the report entirely, neither
        # PASSed nor FAILed (AUDIT-153 §5 G-03, the false negative).
        #
        # The corrected attribution: the expression IS evaluated, but as an
        # ANCESTOR of the child rows (that walk carries no short-circuit), so the
        # child's inheritance — not the group's own mount — is what breaks. The
        # assertions below pin all three halves of the corrected behaviour:
        # the finding, the child's disclosure, and (see
        # `test_group_children_are_still_validated_when_the_group_expression_throws`)
        # the child still being validated.
        with _scratch("spg-test-t05c-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: planning\n"
                "  name: cordis:group\n"
                "  group: true\n"
                "  disabled: !!js \"(() => { throw new Error('group-boom') })()\"\n"
                "  config:\n"
                "    - id: persona\n"
                "      name: '@deepseek-ai/dsh-persona'\n"
                "      config:\n"
                "        prefix: 'never reached'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1, report["issues"])
        # The finding is attributed to the group's INHERITANCE evaluation, not to
        # a mount of the group itself (G03-b).
        self.assertIn("planning", report["issues"][0])
        self.assertIn("group-boom", report["issues"][0])
        self.assertIn("child rows", report["issues"][0])
        # …and the child it decides is disclosed instead of disappearing (the
        # false negative the old `continue` produced). The child now carries TWO
        # records, and that is the point of the fix: one says its mount cannot be
        # determined (the inheritance), the other is the schema comparison that
        # the old `continue` never reached — the child is disclosed *and*
        # validated, which the pre-fix behaviour managed neither of.
        rows = report["compositions"][0]["rows"]
        self.assertEqual(
            sorted((row["row"], row["kind"]) for row in rows),
            [("persona", "DISABLED_INHERITED_UNKNOWN"), ("persona", "PASS"),
             ("planning", "BUILTIN"), ("planning", "DISABLED_EXPR_ERROR")], rows)
        self.assertEqual(report["rows_inherited_unverified"], 1, report)
        self.assertEqual(
            report["coverage"]["unverified_reasons"].get(
                "DISABLED_INHERITED_UNKNOWN"), 1, report["coverage"])
        self.assertTrue(
            any("persona" in line and "DISABLED_INHERITED_UNKNOWN" in line
                for line in report["unverified"]), report["unverified"])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_group_children_are_still_validated_when_the_group_expression_throws(self):
        # FIX-311 (V4) / design §4.4.2③ + acceptance 2②: the connected false
        # negative. Before the fix, a throwing group expression `continue`d and
        # every child of that group was simply never walked — the report held no
        # row for them at all. The child below carries a BAD config (`text`
        # instead of persona's required `prefix`), so once the walk continues the
        # child must be checked and must FAIL on its own schema — independently
        # of the group's finding.
        with _scratch("spg-test-grpwalk-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: planning\n"
                "  name: cordis:group\n"
                "  group: true\n"
                "  disabled: !!js \"(() => { throw new Error('group-boom') })()\"\n"
                "  config:\n"
                "    - id: persona\n"
                "      name: '@deepseek-ai/dsh-persona'\n"
                "      config:\n"
                "        text: 'the pre-fix key, rejected by the installed schema'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        # The group's own finding …
        self.assertTrue(any("group-boom" in issue for issue in report["issues"]),
                        report["issues"])
        # … and the child's, which only exists because the walk continued.
        self.assertTrue(any("persona" in issue and "prefix" in issue
                            for issue in report["issues"]), report["issues"])
        # The child entered the trust surface: it was compared against the
        # installed schema (and rejected), so it is counted, not merely listed.
        self.assertEqual(report["rows_enabled"], 1, report)
        self.assertEqual(report["rows_checked"], 1, report)
        self.assertIn(("persona", "CONFIG_INVALID"),
                      [(row["row"], row["kind"])
                       for row in report["compositions"][0]["rows"]],
                      report["compositions"][0]["rows"])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_throwing_group_disabled_without_children_is_not_a_finding(self):
        # FIX-311 (V4) / design §4.4.2 G03-c + `FX-GROUP-02`: a group with a
        # throwing `disabled` and NO children. `_disabled` short-circuits the
        # group's own `disabled`, and the ancestor walk exists only to serve
        # children — with none, nothing ever evaluates the expression. The old
        # guard reported a mount failure here that the loader cannot produce: a
        # false FAIL on a composition the loader accepts (AUDIT-153 §5 G-03).
        with _scratch("spg-test-grponly-") as td:
            composition = dsh_fixtures.emit_fixture("FX-GROUP-02", td)
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        # Nothing was verified, so nothing may read as PASS (G01-a) …
        self.assertEqual(report["rows_enabled"], 0, report)
        self.assertEqual(report["rows_checked"], 0, report)
        # … and the group still leaves a record (G02-a): the whole point of the
        # slice is that a group is never silently absent from the report.
        rows = report["compositions"][0]["rows"]
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["row"], "planning")
        self.assertEqual(rows[0]["kind"], "BUILTIN")
        self.assertEqual(rows[0]["builtin"], "group")
        self.assertEqual(rows[0]["children"], 0)
        self.assertIn("no child row", rows[0]["message"])
        # The verdict must not claim what nothing measured: with no disabled row
        # observed and no enabled row, "every row is disabled" is not a fact of
        # this run — the group is structure, and structure mounts nothing.
        self.assertIn("no plugin row", report["reason"], report["reason"])
        self.assertNotIn("every row", report["reason"], report["reason"])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_group_name_that_is_not_the_declared_builtin_is_a_finding(self):
        # FIX-311 (V4) / design §4.4.2 G02-b + `FX-GROUP-01`: G-02 was a silent
        # false negative — the walk recursed past every group row without ever
        # resolving its `name`, so `cordis:group` and `cordis:gruop` were equally
        # green (AUDIT-153 §5: the `planning` row produced NO record at all).
        # Only the declared builtin is a measured form; anything else fails
        # closed instead of being assumed equivalent.
        with _scratch("spg-test-grpname-") as td:
            composition = dsh_fixtures.emit_fixture("FX-GROUP-01", td)
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(
            [row["kind"] for row in report["compositions"][0]["rows"]],
            ["GROUP_NAME_UNRESOLVED"], report["compositions"][0]["rows"])
        self.assertIn("GROUP_NAME_UNRESOLVED", report["issues"][0],
                      report["issues"])
        self.assertIn("cordis:group", report["issues"][0], report["issues"])
        self.assertIn("cordis:gruop", report["issues"][0], report["issues"])
        # The name is resolved against the CONTRACT's declared builtin, not a
        # literal in the probe.
        self.assertEqual(dsh_compat._fact("_builtin_group_name"), "cordis:group")

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_group_children_of_a_disabled_group_are_still_disclosed(self):
        # FIX-311 (V4) / design §4.4.2 G03-a regression guard: the fix moves the
        # group's `disabled` evaluation to the children's inheritance path —
        # `disabled: true` must still reach every child. Evaluating the group's
        # expression is not allowed to become "the group is enabled".
        with _scratch("spg-test-grpinherit-") as td:
            report = self._group_disabled_report(td, "true")
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["rows_inherited_disabled"], 1, report)
        self.assertEqual(report["rows_inherited_unverified"], 0, report)
        rows = report["compositions"][0]["rows"]
        # The child is disclosed exactly as before the fix (the inheritance rule
        # is untouched) …
        self.assertEqual(
            sorted((row["row"], row["kind"]) for row in rows),
            [("persona", "DISABLED_INHERITED")], rows)
        # … and the group row is NOT enumerated here. Its own `disabled: true` is
        # what the children inherited, so it did not enumerate anything: the
        # group record exists to state what a group did for its children, and
        # the "enumerated N child row(s)" form belongs to the path that walked
        # them. Recording a child count here would claim an enumeration that
        # never happened.
        self.assertFalse(any(row["kind"] == "BUILTIN" for row in rows), rows)
        self.assertEqual(
            report["coverage"]["rows_unverified"], 0, report["coverage"])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_nested_group_inheritance_propagates(self):
        # The loader walks the whole ancestor chain, not just the direct
        # parent, so an outer disabled group disables a grandchild too.
        with _scratch("spg-test-t05d-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: outer\n"
                "  name: cordis:group\n"
                "  group: true\n"
                "  disabled: true\n"
                "  config:\n"
                "    - id: inner\n"
                "      name: cordis:group\n"
                "      group: true\n"
                "      config:\n"
                "        - id: persona\n"
                "          name: '@deepseek-ai/dsh-persona'\n"
                "          config:\n"
                "            text: 'grandchild of a disabled group'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["rows_inherited_disabled"], 1)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_js_scope_carries_base_url_and_process(self):
        # The loader evaluates `!!js` with the entry context; `baseUrl` must be
        # the composition's own directory and `process` must reach the
        # expression (the shipped preset uses both forms).
        with _scratch("spg-test-js-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: skill-filesystem\n"
                "  name: '@deepseek-ai/dsh-skill-filesystem'\n"
                "  config:\n"
                "    customSkillDirs:\n"
                "      - !!js \"process.getBuiltinModule('node:url')"
                ".fileURLToPath(new URL('./', baseUrl))\"\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["compositions"][0]["checked"], 1)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_throwing_js_expression_is_a_finding_not_a_crash(self):
        with _scratch("spg-test-throw-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: skill-filesystem\n"
                "  name: '@deepseek-ai/dsh-skill-filesystem'\n"
                "  config:\n"
                "    customSkillDirs: !!js \"(() => { throw new Error('boom') })()\"\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertIn("boom", report["issues"][0])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_unresolvable_module_is_a_finding(self):
        with _scratch("spg-test-mod-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: ghost\n"
                "  name: '@deepseek-ai/dsh-does-not-exist'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertIn("ghost", report["issues"][0])
        self.assertIn("cannot resolve", report["issues"][0])

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_isolated_home_witness_reports_zero_writes(self):
        with _scratch("spg-test-iso-") as td:
            composition = Path(td) / "agent.cordis.yml"
            composition.write_text(
                "- id: tool-fs\n  name: '@deepseek-ai/dsh-tool-fs'\n",
                encoding="utf-8")
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["isolation"]["home_writes"], 0, report["isolation"])
        self.assertFalse(Path(report["isolation"]["temp_home"]).exists(),
                         "the isolated temp DSH_HOME must be removed after the run")

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_shipped_compositions_raise_no_findings(self):
        # The repo's own compositions must be accepted by the installed
        # schemas. A permission-denied read in a sandboxed agent session is
        # disclosed as an unverified composition (NOT_RUN for that file) and
        # must never be reported as a finding.
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT, env={}, install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertIn(report["verdict"], {"PASS", "NOT_RUN"}, report)
        self.assertEqual(report["issues"], [], report["issues"])
        paths = [entry["path"] for entry in report["compositions"]]
        self.assertEqual(
            paths, ["agent-presets/governance/agent.cordis.yml.template"], paths)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_shipped_composition_discloses_its_unverified_rows(self):
        # FIX-315 / V3: the repo itself carries rows whose modules export no
        # `Config`. The aggregate verdict legitimately stays PASS (18 of the
        # 23 enabled rows ARE schema-checked, and this slice must not shrink
        # that surface), but the unverified remainder is now named on screen
        # instead of being absent from the output entirely.
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT, env={}, install=_LIVE_INSTALL, node=_LIVE_NODE)
        coverage = report["coverage"]
        self.assertEqual(coverage["rows_enabled"], report["rows_enabled"])
        self.assertEqual(coverage["rows_verified"], report["rows_checked"])
        self.assertEqual(
            coverage["rows_verified"] + coverage["rows_unverified"],
            coverage["rows_enabled"], coverage)
        if report["verdict"] == "PASS":
            self.assertGreater(coverage["rows_unverified"], 0, coverage)
            self.assertEqual(len(report["unverified"]),
                             coverage["rows_unverified"], report["unverified"])
            self.assertIn("NOT verified", report["reason"])
            out = self._rendered_section(report)
            for line in report["unverified"]:
                self.assertIn(line, out, out)

    @staticmethod
    def _rendered_section(report):
        stream = io.StringIO()
        with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                               return_value=report):
            dsh_compat.emit_check_section(stream=stream)
        return stream.getvalue()


# ── the generated negative fixtures (design §5.6 / §6.1 V3③) ────────────────
# FX-NO-SCHEMA-01/02 are emitted by `dsh_fixtures.py` rather than checked in
# (§4.4.1④: "生成式"), so the acceptance command of §4.4.1⑤ is reproducible on
# any machine: same id ⇒ same bytes ⇒ same verdict.
class NoSchemaFixtureTests(unittest.TestCase):
    """End-to-end: emitted fixture → real loader dialect → real schemas."""

    def _emit(self, fixture_id, out_dir):
        return dsh_fixtures.emit_fixture(fixture_id, out_dir)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_fx_no_schema_01_degrades_to_not_run_never_pass(self):
        # The fixture carries a config key (`BOGUS_KEY`) that any schema
        # would reject. The row's module exports no schema, so nothing can
        # reject it — and therefore nothing may be reported as verified:
        # `NOT_RUN`, with zero gate issues (the optional-tooling policy).
        with _scratch("spg-test-fx01-") as td:
            composition = self._emit("FX-NO-SCHEMA-01", td)
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "NOT_RUN", report)
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["rows_enabled"], 1, report)
        self.assertEqual(report["rows_checked"], 0, report)
        self.assertEqual(report["coverage"]["rows_unverified"], 1, report["coverage"])
        self.assertEqual(dict(report["coverage"]["unverified_reasons"]),
                         {"NO_SCHEMA": 1})
        self.assertIn("NOT verified", report["reason"])
        # The message must not claim what the loader does with the config:
        # that behaviour is a separate, unverified fact (G01-e).
        message = report["compositions"][0]["rows"][0]["message"]
        self.assertIn("cannot validate", message)
        self.assertNotIn("passes this config through", message)
        self.assertNotIn("unvalidated", message)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_fx_no_schema_01_cli_exits_zero_and_renders_not_run(self):
        # The standalone surface too: NOT_RUN is disclosed, exits 0, and does
        # not print a [PASS] the report never earned.
        with _scratch("spg-test-fx01-cli-") as td:
            composition = self._emit("FX-NO-SCHEMA-01", td)
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
            stream = io.StringIO()
            with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                                   return_value=report):
                code = dsh_compat.run_cli(stream=stream)
            out = stream.getvalue()
        self.assertEqual(code, 0, out)
        self.assertIn("Result: NOT_RUN", out, out)
        self.assertNotIn("[PASS]", out, out)
        self.assertIn("schema-checked rows: 0", out, out)
        self.assertIn("[NO_SCHEMA]", out, out)

    @unittest.skipUnless(_LIVE_INSTALL and _LIVE_NODE, _LIVE_SKIP)
    def test_fx_no_schema_02_passes_but_discloses_the_unverified_row(self):
        with _scratch("spg-test-fx02-") as td:
            composition = self._emit("FX-NO-SCHEMA-02", td)
            report = dsh_compat.check_dsh_preset_compat(
                root=Path(td), compositions=[composition], env={},
                install=_LIVE_INSTALL, node=_LIVE_NODE)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertEqual(report["rows_enabled"], 2, report)
        self.assertEqual(report["rows_checked"], 1, report)
        self.assertEqual(report["coverage"]["rows_unverified"], 1, report["coverage"])
        self.assertEqual(len(report["unverified"]), 1, report["unverified"])
        self.assertIn("tool-ask-user", report["unverified"][0])


if __name__ == "__main__":
    unittest.main()
