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
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))
# FIX-336: the bare `import dsh_fixtures` below resolves the helper from THIS
# directory, which only worked when unittest put the start dir on `sys.path`
# (i.e. `-s <tests>` without `-t`). Under the full-suite discover
# (`-s <tests> -t <repo>`) modules import by their dotted repo-relative name,
# the start dir is NOT added, and the whole module died with
# `ModuleNotFoundError: No module named 'dsh_fixtures'` — its cases silently
# absent from the collection count. Same preamble as `test_dsh_contract.py`.
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

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


class ReportFaceFailSoftTests(unittest.TestCase):
    """FIX-323 — the standalone report faces survive an undeclared kind.

    REVIEW-FIX-311-CODE-R0 left three findings, all reachable through the SAME
    report — one carrying a row diagnostic no declared table knows:

    * F-01: `run_cli`/`_print_human` called `_informational_details`
      unconditionally BEFORE the FAIL branch was rendered, and its first line
      (`_assert_report_kinds_declared`) raises on exactly that kind — so the
      standalone CLI escaped as a raw `ValueError` and the readable report
      (verdict + issue list) was lost. Both faces now render the verdict
      branches FIRST and degrade a tripped guard to a finding line: report
      completeness wins (fail-soft at the face, still fail-loud in
      `_informational_details` itself — G-18 keeps its own contract).
    * F-02: `_classify_row` answered `CATEGORY_INFO` for a row with NO `kind`
      field, parking a malformed record on the `[INFO]` face. A missing kind
      is not a declared disclosure — it classifies as `CATEGORY_UNKNOWN` and
      gates, exactly like an undeclared kind.
    * F-03: both faces picked `[FAIL]` rows by table membership
      (`kind in FINDING_KINDS`) instead of asking the single classifier, so an
      undeclared kind rendered zero per-row `[FAIL]` lines even though the
      verdict failed on it. The faces now ask `_classify_row`.
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

    def _undeclared_kind_report(self):
        report = self._report(("PASS", "SOME_FUTURE_PROBE_KIND"))
        self.assertEqual(report["verdict"], "FAIL", report)
        return report

    # ── F-02: a missing `kind` is UNKNOWN, never a quiet `[INFO]` ───────────
    def test_a_row_without_a_kind_is_unknown_not_info(self):
        ghost = {"row": "ghost", "name": "@deepseek-ai/dsh-ghost",
                 "message": "no kind at all"}
        self.assertEqual(dsh_compat._classify_row(ghost),
                         dsh_compat.CATEGORY_UNKNOWN)
        self.assertEqual(dsh_compat._classify_row(dict(ghost, kind=None)),
                         dsh_compat.CATEGORY_UNKNOWN)
        self.assertEqual(dsh_compat._classify_row_kind(None),
                         dsh_compat.CATEGORY_UNKNOWN)

    def test_a_missing_kind_gates_instead_of_quietly_informing(self):
        # The verdict-level consequence of F-02: the malformed record used to
        # land on the `[INFO]` face and let the run degrade to NOT_RUN with
        # zero issues; it is now a finding like any undeclared kind.
        path = _REPO_ROOT / "kinds.cordis.yml"
        report = dsh_compat.check_dsh_preset_compat(
            root=_REPO_ROOT,
            compositions=[path],
            env={},
            which=_which_map({"node": "C:/fake/node.exe"}),
            install=dict(self._INSTALL),
            probe_runner=lambda node, install, paths, root, timeout: _probe_report(
                [_file_entry(path, [{"row": "ghost",
                                     "name": "@deepseek-ai/dsh-ghost",
                                     "message": "no kind at all"}])]))
        self.assertEqual(report["verdict"], "FAIL", report)
        self.assertEqual(len(report["issues"]), 1, report["issues"])
        self.assertIn("ghost", report["issues"][0])

    # ── F-01: the faces survive the tripped report guard ────────────────────
    def test_run_cli_survives_an_undeclared_kind_and_renders_the_full_report(self):
        report = self._undeclared_kind_report()
        stream = io.StringIO()
        with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                               return_value=report):
            code = dsh_compat.run_cli(stream=stream)
        out = stream.getvalue()
        self.assertEqual(code, 0, out)
        # The FAIL verdict and its issue list are on screen — exactly the parts
        # the escaping ValueError used to swallow.
        self.assertIn("Result: FAILED", out, out)
        self.assertIn("SOME_FUTURE_PROBE_KIND", out, out)
        # The tripped guard degraded to a finding line instead of crashing.
        self.assertIn("row-kind declaration guard", out, out)

    def test_print_human_survives_an_undeclared_kind_and_keeps_the_issue_list(self):
        report = self._undeclared_kind_report()
        stream = io.StringIO()
        dsh_compat._print_human(report, stream)
        out = stream.getvalue()
        self.assertIn("verdict: FAIL", out, out)
        self.assertIn("issue  :", out, out)
        self.assertIn("SOME_FUTURE_PROBE_KIND", out, out)
        self.assertIn("row-kind declaration guard", out, out)

    # ── F-03: the faces ask the single classifier ───────────────────────────
    def test_an_undeclared_kind_still_renders_a_per_row_fail_line(self):
        # `row-2` carries the undeclared kind: the verdict failed on it, so the
        # per-row `[FAIL]` line must exist on both faces — not only the issue
        # list further down.
        report = self._undeclared_kind_report()
        stream = io.StringIO()
        with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                               return_value=report):
            dsh_compat.run_cli(stream=stream)
        self.assertIn("[FAIL] row-2", stream.getvalue(), stream.getvalue())
        stream = io.StringIO()
        dsh_compat._print_human(report, stream)
        self.assertIn("[FAIL] row-2", stream.getvalue(), stream.getvalue())

    def test_render_faces_still_route_a_group_record_to_info(self):
        # The unification must not reclassify the record-level fact the
        # classifier owns: a group record stays structural `[INFO]`, never a
        # `[FAIL]` row, on both faces.
        report = self._report(("PASS", "BUILTIN"))
        self.assertEqual(report["verdict"], "PASS", report)
        report["compositions"][0]["rows"].append({
            "row": "planning", "name": "cordis:group", "kind": "BUILTIN",
            "builtin": "group", "children": 1,
            "message": "group builtin — 1 child row(s) enumerated"})
        stream = io.StringIO()
        with mock.patch.object(dsh_compat, "check_dsh_preset_compat",
                               return_value=report):
            dsh_compat.run_cli(stream=stream)
        out = stream.getvalue()
        self.assertNotIn("[FAIL]", out, out)
        self.assertIn("cordis:group", out, out)
        stream = io.StringIO()
        dsh_compat._print_human(report, stream)
        self.assertNotIn("[FAIL]", stream.getvalue())
        self.assertIn("cordis:group", stream.getvalue())


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


class RenderAndDecodeGuardTests(unittest.TestCase):
    """The render/decode face of the launcher (FIX-316, design §4.4.3-§4.4.6).

    The guard above decides whether a *row* is valid; this class covers the
    other half of the same delivery — the launcher that writes the composition
    the guard then reads. Every case here is one the audit measured as a
    silent or unactionable failure:

      * a legal same-indent block sequence the hand-written scanner missed;
      * a misspelt render token that used to reach a written preset;
      * a non-UTF-8 file whose ``UnicodeDecodeError`` escaped a public entry;
      * an isolated CR the two renderers disagreed about.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "dsh_launch_render_guard",
            _REPO_ROOT / "adapters" / "dsh" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.launch = module

    # ── G-05: same-indent block sequence ───────────────────────────────────
    def test_same_indent_custom_skill_dirs_are_found(self):
        # FX-CSD-01 puts the sequence items at the KEY's indentation. That is
        # legal YAML; the old `<=` end-of-block test broke out immediately and
        # reported zero entries, which surfaced as the misleading "preset
        # declares no customSkillDirs" message.
        text = dsh_fixtures.fixture_bytes("FX-CSD-01").decode("utf-8")
        entries = self.launch._custom_skill_dir_entries(text)
        self.assertEqual(len(entries), 2, entries)
        self.assertIn("__GOVERNANCE_SKILLS_ROOT__", entries[0])
        self.assertIn("__GOVERNANCE_SHIMS_ROOT__", entries[1])

    def test_rendered_same_indent_fixture_yields_absolute_existing_roots(self):
        """FX-CSD-01 end to end: the block is found AND renders to real dirs."""
        text = dsh_fixtures.fixture_bytes("FX-CSD-01").decode("utf-8")
        rendered = self._render_text(text)
        self.assertTrue(rendered, "the same-indent fixture must render")
        entries = self.launch._custom_skill_dir_entries(rendered)
        self.assertEqual(len(entries), 2, entries)
        for entry in entries:
            form, path, issue = self.launch._resolve_skill_entry(entry, _REPO_ROOT)
            self.assertIsNone(issue, entry)
            self.assertEqual(form, "absolute", entry)
            self.assertTrue(path.is_dir(), entry)
        # Same inputs, same result as the shipped template: the scanner's
        # tolerance must not change what a valid block resolves to.
        shipped = self.launch._custom_skill_dir_entries(self.launch.render_composition())
        self.assertEqual(len(shipped), 2, shipped)

    def test_a_sibling_key_ends_the_block(self):
        # Tolerance must not become greed: a following key at the block's own
        # indentation closes the sequence instead of being read as an entry.
        text = ("- id: skill-filesystem\n"
                "  config:\n"
                "    customSkillDirs:\n"
                "    - /one\n"
                "    - /two\n"
                "    otherKey: 1\n"
                "    - /not-an-entry\n")
        self.assertEqual(self.launch._custom_skill_dir_entries(text),
                         ["/one", "/two"])

    def test_declared_block_shape_is_asserted_on_the_render_source(self):
        # `own.render.custom_skill_dirs_shape` is a declaration, not prose: the
        # shipped render source must still match it (key indent, item indent,
        # entry count and the declared token form).
        source = self.launch._read_text_with_newline_mode(
            _REPO_ROOT / "agent-presets" / "governance"
            / "agent.cordis.yml.template")
        self.assertEqual(
            self.launch._shape_violations(source, stage="template"), [])
        self.assertEqual(self.launch._shape_violations(self._render_text(source)), [])

    def test_unimplemented_list_style_is_a_contract_defect(self):
        # N-3: `list_style` used to be emitted as a per-document violation, but
        # only `block-sequence` is implemented — so for any valid contract the
        # branch was unreachable and a mutation removing it survived. It is now
        # asserted at entry, which has a counter-case: declare another style and
        # the check fails loudly naming the contract field.
        original = self.launch.declared_custom_skill_dirs_shape

        def flowed():
            shape = dict(original())
            shape["list_style"] = "flow-sequence"
            return shape

        self.launch.declared_custom_skill_dirs_shape = flowed
        try:
            with self.assertRaises(Exception) as caught:
                self.launch._shape_violations(
                    "- id: x\n  config:\n    customSkillDirs:\n      - /a\n")
        finally:
            self.launch.declared_custom_skill_dirs_shape = original
        self.assertIn("list_style", str(caught.exception))
        self.assertIn("block-sequence", str(caught.exception))
        # The shipped declaration is the implemented one.
        self.assertEqual(
            original()["list_style"], "block-sequence")

    def test_unreadable_skill_root_marker_is_disclosed_not_silent(self):
        # N-6b: a non-decodable `skill-root.txt` used to fall through to the
        # catalog parent with no issue at all — a silent downgrade. It must now
        # be disclosed, and the report must still be a structured FAIL/PASS
        # rather than a raise.
        with _scratch("spg-test-marker-disclosure-") as td:
            root = Path(td) / "repo"
            preset = Path(td) / "preset"
            (preset / "skills" / "software-project-governance").mkdir(parents=True)
            (preset / "agent.cordis.yml").write_text(
                "- id: x\n", encoding="utf-8")
            (preset / "skill-root.txt").write_bytes(b"\xff bad marker\n")
            surface = self.launch.verify_preset_loading(preset)
        self.assertEqual(surface["verdict"], "FAIL", surface)
        self.assertTrue(
            any("skill-root.txt" in issue and "unreadable" in issue
                for issue in surface["issues"]),
            surface["issues"])

    def test_package_version_is_strict_at_every_call_site(self):
        # N-8: there is exactly ONE package-identity reader and it is strict, so
        # no caller can quietly stamp a wrong marker. The placeholder survives
        # only for the genuinely absent file (a repository copy that ships
        # without `package.json`), and only through `marker_version`.
        self.assertEqual(self.launch.package_version(),
                         json.loads((_REPO_ROOT / "package.json").read_text(
                             encoding="utf-8"))["version"])
        self.assertEqual(self.launch.marker_version(),
                         self.launch.package_version())
        self.assertFalse(hasattr(self.launch, "require_package_version"),
                         "the lenient/strict pair is back — consolidation lost")
        # A present-but-unreadable identity is refused, not degraded.
        with _scratch("spg-test-n8-") as td:
            root = Path(td) / "repo"
            (root / "adapters" / "dsh").mkdir(parents=True)
            (root / "skills" / "software-project-governance" / "infra").mkdir(
                parents=True)
            (root / "package.json").write_bytes(b'{"version": "\xff bad"}')
            shutil.copy2(_REPO_ROOT / "skills" / "software-project-governance"
                         / "infra" / "dsh_contract.py",
                         root / "skills" / "software-project-governance"
                         / "infra" / "dsh_contract.py")
            shutil.copy2(_REPO_ROOT / "adapters" / "dsh" / "launch.py",
                         root / "adapters" / "dsh" / "launch.py")
            shutil.copy2(_REPO_ROOT / "adapters" / "dsh" / "host-contract.json",
                         root / "adapters" / "dsh" / "host-contract.json")
            spec = importlib.util.spec_from_file_location(
                "dsh_launch_n8_probe", root / "adapters" / "dsh" / "launch.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            with self.assertRaises(module.PackageIdentityUnreadable):
                module.marker_version()
        # The writer accepts an explicit version, which is how `install_preset`
        # keeps its strict read ahead of any staging write.
        import inspect
        self.assertIn("version",
                      inspect.signature(self.launch.write_rendered_preset).parameters)

    def test_relative_skill_dir_is_still_reported(self):
        # FX-CSD-02 replaces one entry with a literal relative path (FIX-290):
        # it resolves against the dsh process CWD and silently empties the
        # session catalog, so it MUST be reported — while the other, token
        # substituted entry stays clean.
        text = dsh_fixtures.fixture_bytes("FX-CSD-02").decode("utf-8")
        rendered = self._render_text(text)
        resolved = [self.launch._resolve_skill_entry(entry, _REPO_ROOT)
                    for entry in self.launch._custom_skill_dir_entries(rendered)]
        forms = [form for form, _path, _issue in resolved]
        self.assertIn("relative", forms, resolved)
        self.assertIn("absolute", forms, resolved)
        reported = [issue for _form, _path, issue in resolved if issue]
        self.assertEqual(len(reported), 1, resolved)
        self.assertIn("FIX-290", reported[0])
        # Absolute entries keep no issue: the report is about the relative one.
        for form, _path, issue in resolved:
            if form == "absolute":
                self.assertIsNone(issue)

    # ── G-07: misspelt tokens ──────────────────────────────────────────────
    def test_misspelt_tokens_are_refused_by_both_shipped_forms(self):
        # FX-TOKEN-01 (all caps) and FX-TOKEN-02 (mixed case) both used to
        # render cleanly: the guard only looked for the three KNOWN tokens to
        # survive, so an unknown spelling passed through into the preset. The
        # declared `leftover_scan` catches any `__…__` spelling instead.
        for fixture in ("FX-TOKEN-01", "FX-TOKEN-02"):
            with self.subTest(fixture=fixture):
                text = dsh_fixtures.fixture_bytes(fixture).decode("utf-8")
                self.assertEqual(self._render_text(text), "",
                                 f"{fixture} must not render")
                self.assertTrue(self.launch.leftovers(text), fixture)

    def test_leftovers_uses_the_declared_scan_not_a_known_token_list(self):
        self.assertEqual(self.launch.leftovers("plain text"), [])
        self.assertEqual(self.launch.leftovers("__Governance_Repo_Root__"),
                         ["__Governance_Repo_Root__"])
        # Deduplicated and order-stable (first appearance wins).
        self.assertEqual(self.launch.leftovers("__A_1__ x __A_1__ __B_2__"),
                         ["__A_1__", "__B_2__"])
        self.assertEqual(self.launch._fact("LEFTOVER_SCAN"), "__[A-Za-z0-9_]+__")

    # ── G-10: non-UTF-8 input ──────────────────────────────────────────────
    def test_non_utf8_verification_is_a_structured_failure_not_a_raise(self):
        raw = dsh_fixtures.fixture_bytes("FX-UTF8-01")
        with _scratch("spg-test-utf8-") as td:
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_bytes(raw)
            surface = self.launch.verify_preset_loading(preset)
        self.assertEqual(surface["verdict"], "FAIL", surface)
        self.assertTrue(surface["issues"], surface)
        issue = surface["issues"][0]
        self.assertIn("not valid UTF-8", issue)
        self.assertIn("byte offset", issue)

    def test_non_utf8_render_refuses_without_raising(self):
        raw = dsh_fixtures.fixture_bytes("FX-UTF8-01")
        with _scratch("spg-test-utf8-render-") as td:
            path = Path(td) / "tpl.yml"
            path.write_bytes(raw)
            self.assertEqual(self._render_path(path), "")

    def test_non_utf8_read_raises_the_structured_type_only(self):
        raw = dsh_fixtures.fixture_bytes("FX-UTF8-01")
        with _scratch("spg-test-utf8-read-") as td:
            path = Path(td) / "x.yml"
            path.write_bytes(raw)
            with self.assertRaises(self.launch.CompositionUnreadable) as caught:
                self.launch._read_text(path)
        self.assertEqual(caught.exception.offset, 72)
        self.assertEqual(caught.exception.byte, 0xFF)
        self.assertIn("0xff", caught.exception.diagnostic())

    def test_valid_utf8_still_reads_normally(self):
        # The control: the diagnosis must not fire on a healthy file.
        with _scratch("spg-test-utf8-ok-") as td:
            path = Path(td) / "x.yml"
            path.write_text("ok: true\n", encoding="utf-8")
            self.assertEqual(self.launch._read_text(path), "ok: true\n")

    # ── D-66: line-ending rule shared with lib/index.js ────────────────────
    def test_isolated_cr_is_preserved_like_the_js_renderer(self):
        # The JS renderer normalizes exactly `\r\n` -> `\n` and leaves a lone
        # `\r` alone. The Python renderer used the text layer's universal
        # newlines, which folded EVERY `\r` — so the same template produced
        # different bytes on the two delivery paths.
        text = dsh_fixtures.fixture_bytes("FX-CR-01").decode("utf-8")
        self.assertEqual(text.count("\r"), 1)
        self.assertEqual(text.count("\r\n"), 0)
        rendered = self._render_text(text)
        self.assertTrue(rendered, "the CR fixture must still render")
        self.assertEqual(rendered.count("\r"), 1, "lone CR must survive")

    def test_crlf_template_folds_to_lf(self):
        # The half that must NOT change: a CRLF checkout still renders LF, so
        # `core.autocrlf` cannot change the preset's bytes.
        source = _REPO_ROOT / "agent-presets" / "governance" / "agent.cordis.yml.template"
        lf_text = self.launch._read_text_with_newline_mode(source)
        crlf_text = lf_text.replace("\n", "\r\n")
        self.assertEqual(self._render_text(crlf_text), self._render_text(lf_text))
        self.assertEqual(self._render_text(crlf_text).count("\r"), 0)

    def test_shape_violations_fire_in_the_reverse_direction(self):
        # F-3: five independent neutralizations of `_shape_violations` used to
        # survive the whole suite, because every assertion was `== []`. Each
        # declared dimension now has a counter-case that must produce a
        # violation, so removing a check turns a test red.
        shape = self.launch.declared_custom_skill_dirs_shape()
        key_indent = " " * shape["key_indent"]
        item_indent = " " * shape["item_indent"]

        def block(*items):
            return ("- id: skill-filesystem\n"
                    "  config:\n"
                    f"{key_indent}customSkillDirs:\n"
                    + "".join(f"{item}\n" for item in items))

        cases = {
            "key_indent": block(f"{item_indent}- __GOVERNANCE_SKILLS_ROOT__",
                                f"{item_indent}- __GOVERNANCE_SHIMS_ROOT__")
            .replace(f"{key_indent}customSkillDirs:",
                     f"{key_indent}  customSkillDirs:"),
            "item_indent": block(f"{item_indent}    - __GOVERNANCE_SKILLS_ROOT__",
                                 f"{item_indent}    - __GOVERNANCE_SHIMS_ROOT__"),
            "entry_count": block(f"{item_indent}- __GOVERNANCE_SKILLS_ROOT__"),
            "entry_form": block(f"{item_indent}- @deepseek-ai/dsh-somewhere",
                                f"{item_indent}- __GOVERNANCE_SHIMS_ROOT__"),
        }
        for dimension, text in cases.items():
            with self.subTest(dimension=dimension):
                violations = self.launch._shape_violations(text, stage="template")
                self.assertTrue(violations, f"{dimension}: no violation reported")
        # The same input through the public verifier must reach FAIL, not PASS.
        with _scratch("spg-test-shape-neg-") as td:
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_text(
                cases["item_indent"], encoding="utf-8")
            (preset / "skill-root.txt").write_text(str(_REPO_ROOT) + "\n",
                                                   encoding="utf-8")
            surface = self.launch.verify_preset_loading(preset)
        self.assertEqual(surface["verdict"], "FAIL", surface)
        self.assertTrue(
            any("shape drift" in issue for issue in surface["issues"]),
            surface["issues"])

    def test_shape_violations_are_stable_for_a_healthy_block(self):
        # The counterpart to the counter-cases: a well-formed block yields no
        # violation in either stage, so the assertions above cannot be
        # satisfied by a checker that always reports something.
        shape = self.launch.declared_custom_skill_dirs_shape()
        key_indent = " " * shape["key_indent"]
        item_indent = " " * shape["item_indent"]
        token_block = ("- id: skill-filesystem\n"
                       "  config:\n"
                       f"{key_indent}customSkillDirs:\n"
                       f"{item_indent}- __GOVERNANCE_SKILLS_ROOT__\n"
                       f"{item_indent}- __GOVERNANCE_SHIMS_ROOT__\n")
        self.assertEqual(
            self.launch._shape_violations(token_block, stage="template"), [])
        # The rendered stage holds the substituted absolute paths instead.
        rendered_block = ("- id: skill-filesystem\n"
                          "  config:\n"
                          f"{key_indent}customSkillDirs:\n"
                          f"{item_indent}- '{_REPO_ROOT.as_posix()}/skills'\n"
                          f"{item_indent}- "
                          f"'{_REPO_ROOT.as_posix()}/adapters/dsh/skill-shims'\n")
        self.assertEqual(self.launch._shape_violations(rendered_block), [])

    def test_baseurl_entry_is_accepted_by_both_judgments(self):
        # F-6: `- !!js new URL('skills', baseUrl)` is a form
        # `_resolve_skill_entry` accepts. The shape checker used to call the
        # same line "relative" and report a violation — one file, two
        # contradictory verdicts about one line.
        shape = self.launch.declared_custom_skill_dirs_shape()
        item_indent = " " * shape["item_indent"]
        entry = "!!js new URL('skills', baseUrl)"
        text = ("- id: skill-filesystem\n"
                "  config:\n"
                "    customSkillDirs:\n"
                f"{item_indent}- '{entry}'\n"
                f"{item_indent}- '{entry}'\n")
        violations = self.launch._shape_violations(text)
        self.assertEqual(violations, [], violations)
        form, path, issue = self.launch._resolve_skill_entry(entry, _REPO_ROOT)
        self.assertEqual(form, "baseUrl")
        self.assertIsNone(issue)
        self.assertEqual(path, _REPO_ROOT.resolve() / "skills")

    def test_newline_policy_is_consumed_by_the_writer(self):
        # F-7: `own.render.newline_policy` used to be a declared-but-unread
        # binding, so mutating it to `crlf` changed nothing. The writer now
        # asserts it, which is what makes the declaration load-bearing.
        self.assertEqual(self.launch.require_lf_newline_policy(), "lf")
        original = self.launch._fact

        def crlf(name):
            return "crlf" if name == "NEWLINE_POLICY" else original(name)

        with _scratch("spg-test-newline-") as td:
            isolated = str(Path(td) / "dsh-home")
            stream = io.StringIO()
            self.launch._fact = crlf
            try:
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream), \
                        mock.patch.dict(os.environ, {"DSH_HOME": isolated},
                                        clear=False):
                    code = self.launch.install_preset()
            finally:
                self.launch._fact = original
            output = stream.getvalue()
            written = (Path(isolated) / ".agent-presets" / "governance").exists()
        self.assertEqual(code, 1, output)
        self.assertIn("newline_policy", output)
        self.assertFalse(written, "a refused newline policy must not write a preset")

    def test_skill_frontmatter_binding_is_not_declared_unused(self):
        # F-7: `SKILL_FRONTMATTER` had no reader anywhere. A declared-but-unread
        # binding is the same defect class as a second source of truth, so it is
        # gone rather than annotated.
        self.assertNotIn("SKILL_FRONTMATTER", self.launch.CONTRACT_BINDING)
        for name in self.launch.CONTRACT_BINDING:
            with self.subTest(binding=name):
                self.assertTrue(self.launch._fact(name) is not None, name)

    # ── D-54 / FX-WITNESS-01 ──────────────────────────────────────────────
    def test_witness_ignores_host_settings_rewrite(self):
        # D-54: the host rewrites `settings.yaml` for its own reasons; a change
        # in that file's size and mtime is not evidence that this adapter wrote
        # anything, so the witness must not carry those fields at all.
        with _scratch("spg-test-witness-") as td:
            home = Path(td) / "home"
            preset = home / ".agent-presets" / "governance"
            preset.mkdir(parents=True)
            (preset / "preset.yml").write_text("name: governance\n", encoding="utf-8")
            settings = home / "settings.yaml"
            settings.write_text("a: 1\n", encoding="utf-8")
            before = self.launch._real_home_witness(home)
            stamp = settings.stat().st_mtime_ns
            settings.write_text("a: 2" * 512 + "\n", encoding="utf-8")
            os.utime(settings, ns=(stamp + 10 ** 9, stamp + 10 ** 9))
            after = self.launch._real_home_witness(home)
        self.assertEqual(before["top_level"], after["top_level"])
        result = self.launch.witness_verdict((before, after))
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertFalse(result["failures"])

    def test_witness_fails_on_a_preset_write_without_resampling(self):
        with _scratch("spg-test-witness-") as td:
            home = Path(td) / "home"
            preset = home / ".agent-presets" / "governance"
            preset.mkdir(parents=True)
            (preset / "preset.yml").write_text("name: governance\n", encoding="utf-8")
            before = self.launch._real_home_witness(home)
            (preset / "agent.cordis.yml").write_text("- id: x\n", encoding="utf-8")
            after = self.launch._real_home_witness(home)
        result = self.launch.witness_verdict((before, after), resample=lambda: after)
        self.assertEqual(result["verdict"], "FAIL", result)
        self.assertTrue(any("write surface" in f for f in result["failures"]),
                        result["failures"])

    def test_witness_reproduced_top_level_change_fails(self):
        with _scratch("spg-test-witness-") as td:
            home = Path(td) / "home"
            (home / ".agent-presets").mkdir(parents=True)
            before = self.launch._real_home_witness(home)
            (home / "settled.tmp").write_text("x\n", encoding="utf-8")
            after_first = self.launch._real_home_witness(home)
            result = self.launch.witness_verdict(
                (before, after_first),
                resample=lambda: self.launch._real_home_witness(home))
        self.assertEqual(result["verdict"], "FAIL", result)
        self.assertTrue(any("top level" in f for f in result["failures"]),
                        result["failures"])

    def test_witness_unreproduced_top_level_change_is_advisory(self):
        with _scratch("spg-test-witness-") as td:
            home = Path(td) / "home"
            (home / ".agent-presets").mkdir(parents=True)
            before = self.launch._real_home_witness(home)
            transient = home / "transient.tmp"
            transient.write_text("x\n", encoding="utf-8")
            after_first = self.launch._real_home_witness(home)

            def resample():
                transient.unlink()
                return self.launch._real_home_witness(home)

            result = self.launch.witness_verdict(
                (before, after_first), resample=resample)
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertTrue(result["advisories"], result)
        self.assertFalse(result["failures"])

    def test_fx_witness_01_fixture_is_consumed(self):
        # D-54 acceptance ⑤: `FX-WITNESS-01` must be machine-checked, not merely
        # registered. The emitted artifact is a runnable oracle that drives the
        # launcher's own witness through all four judgments.
        with _scratch("spg-test-witness-fx-") as td:
            path = dsh_fixtures.emit_fixture("FX-WITNESS-01", Path(td))
            self.assertEqual(path.name, "FX-WITNESS-01.py")
            # N-6a: the module claims the emitted source is ASCII-only, so the
            # claim is checked instead of trusted (it was false once).
            path.read_bytes().decode("ascii")
            # Deterministic bytes: two emissions are identical.
            second = dsh_fixtures.emit_fixture("FX-WITNESS-01", Path(td) / "again")
            self.assertEqual(path.read_bytes(), second.read_bytes())
            proc = subprocess.run(
                [sys.executable, str(path),
                 str(_REPO_ROOT / "adapters" / "dsh" / "launch.py")],
                cwd=str(_REPO_ROOT), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual([check["check"] for check in report["checks"]], [
            "settings_yaml_race_is_not_a_failure",
            "witness_records_no_size_or_mtime",
            "host_subtree_churn_is_not_a_failure",
            "write_surface_change_fails_without_resample",
            "unreproduced_top_level_change_is_advisory",
            "reproduced_top_level_change_fails",
        ], report)

    # ── helpers ────────────────────────────────────────────────────────────
    def _render_text(self, text):
        """``render_composition()`` driven against in-memory template text."""
        with _scratch("spg-test-render-") as td:
            path = Path(td) / "template.yml"
            path.write_text(text, encoding="utf-8", newline="")
            return self._render_path(path)

    def _render_path(self, path):
        original = self.launch._composition_template
        self.launch._composition_template = lambda: Path(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                return self.launch.render_composition()
        finally:
            self.launch._composition_template = original


class WriteSideHomeConvergenceTests(unittest.TestCase):
    """`$DSH_HOME` write-side convergence + the write-entry guard (FIX-316).

    Design §4.4.4 states the write side as ONE rule shared by every writer
    (`blank_policy` / `trim_policy` / `fallback` / `tilde_expansion` are
    contract fields), with the *probe* side deliberately excluded from that
    convergence because the guard's safety property is "an explicit
    `$DSH_HOME` or nothing" (G06-b').

    The two writers are `adapters/dsh/launch.py::dsh_home()` and
    `lib/index.js::resolveDshHome()`. The JS side is read-only probed by
    evaluating the module source with `import.meta.url` bound to its real URL —
    reaching the same rule through `ensurePreset()` would write the preset into
    whatever home the case resolves to, which for the blank cases is the user's
    real `~/.dsh`.
    """

    CASES = (
        ("unset", None),
        ("empty", ""),
        ("spaces", "   "),
        ("tab", "\t"),
        ("posix", "C:/tmp/spg-fix316/x"),
        ("trailing", "C:/tmp/spg-fix316/x/"),
        ("backslash", "C:\\tmp\\spg-fix316\\x"),
        ("relative", "spg-fix316/x"),
        ("tilde", "~"),
        ("tilde-slash", "~/spg-fix316/x"),
        ("tilde-backslash", "~\\spg-fix316\\x"),
        ("spaced", "  C:/tmp/spg-fix316/x  "),
    )

    _JS_PROBE = """
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
const libPath = process.argv[2]
const src = readFileSync(libPath, 'utf8').replace(/^export /gm, '')
const shim = 'import.meta.url = ' + JSON.stringify(pathToFileURL(libPath).href) + ';\\n'
  + src + '\\nexport { resolveDshHome, CONTRACT_BINDING };\\n'
const mod = await import('data:text/javascript;base64,'
  + Buffer.from(shim).toString('base64'))
const contract = JSON.parse(readFileSync(process.argv[3], 'utf8'))
const declared = {}
for (const [key, path] of Object.entries(mod.CONTRACT_BINDING)) {
  let node = contract
  for (const part of path.split('.')) node = node?.[part]
  declared[key] = node
}
const bindings = {
  homeVar: declared.homeVar,
  homeFallbackName: String(declared.homeFallback).split(/[\\\\/]/).pop(),
}
console.log(JSON.stringify({ home: mod.resolveDshHome(bindings) }))
"""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "dsh_launch_home_convergence",
            _REPO_ROOT / "adapters" / "dsh" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.launch = module
        cls.contract_path = _REPO_ROOT / "adapters" / "dsh" / "host-contract.json"

    @staticmethod
    def _env(case_value):
        """Controlled env: only what locating the default home requires."""
        env = {key: os.environ[key] for key in
               ("PATH", "SystemRoot", "windir", "PATHEXT", "TEMP", "TMP",
                "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "COMSPEC", "APPDATA",
                "LOCALAPPDATA")
               if key in os.environ}
        if case_value is not None:
            env["DSH_HOME"] = case_value
        return env

    @staticmethod
    def _norm(text):
        """Forward slashes, no trailing separator, case-folded.

        Windows resolves paths case-insensitively, so a drive-letter casing
        difference is the same location (`c:/TMP/X` vs `C:/tmp/X`); comparing
        the raw strings would report a disagreement the filesystem does not
        have.
        """
        return text.replace("\\", "/").rstrip("/").lower()

    def _launch_home(self, case_value):
        """`launch.py::dsh_home()` in its own process, under `case_value`."""
        env = self._env(case_value)
        argv = [sys.executable, "-c",
                "import importlib.util,json,sys;"
                "from pathlib import Path;"
                "s=importlib.util.spec_from_file_location('L',sys.argv[1]);"
                "m=importlib.util.module_from_spec(s);sys.modules['L']=m;"
                "s.loader.exec_module(m);"
                "print(json.dumps({'home':str(m.dsh_home())}))",
                str(_REPO_ROOT / "adapters" / "dsh" / "launch.py")]
        proc = subprocess.run(argv, cwd=str(_REPO_ROOT), env=env,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])["home"]

    def _lib_home(self, case_value):
        """`lib/index.js::resolveDshHome()` — a read-only source probe."""
        node = shutil.which("node")
        if not node:  # pragma: no cover - node is present in the live gates
            self.skipTest("node unavailable — differential gate is NOT_RUN")
        with _scratch("spg-test-home-js-") as td:
            probe = Path(td) / "probe.mjs"
            probe.write_text(self._JS_PROBE, encoding="utf-8")
            proc = subprocess.run(
                [node, str(probe), str(_REPO_ROOT / "lib" / "index.js"),
                 str(self.contract_path)],
                cwd=str(_REPO_ROOT), env=self._env(case_value),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])["home"]

    def test_blank_dsh_home_means_unset(self):
        # `blank_policy = "trimmed-empty-means-unset"`: an unset OR blank value
        # falls back to the declared `<home>/.dsh`. The old `if env:` test
        # treated `"   "` as a real path and produced
        # `"   \\.agent-presets\\governance"`.
        fallback = str(Path.home() / ".dsh")
        for label, value in (("unset", None), ("empty", ""),
                             ("spaces", "   "), ("tab", "\t")):
            with self.subTest(case=label):
                home = self._launch_home(value)
                self.assertEqual(self._norm(home), self._norm(fallback), home)
                self.assertFalse(home.strip() != home,
                                 f"{label}: produced a literal blank path {home!r}")

    def test_tilde_forms_expand(self):
        home = Path.home()
        expected = {
            "~": home,
            "~/spg-fix316/x": home / "spg-fix316" / "x",
            "~\\spg-fix316\\x": home / "spg-fix316" / "x",
        }
        for case, want in expected.items():
            with self.subTest(case=case):
                self.assertEqual(self._norm(self._launch_home(case)),
                                 self._norm(str(want)))

    def test_relative_value_resolves_against_the_process_cwd(self):
        # `trim_policy = "verbatim-then-platform-resolve"`: the value decides
        # what is resolved, the platform decides how. Leaving it relative was
        # the one case where the two writers disagreed.
        got = self._launch_home("spg-fix316/x")
        self.assertTrue(Path(got).is_absolute(), got)
        self.assertEqual(self._norm(got),
                         self._norm(str(_REPO_ROOT / "spg-fix316" / "x")))

    @unittest.skipUnless(shutil.which("node"),
                         "node unavailable — three-way matrix is NOT_RUN")
    def test_writer_case_table_agrees_with_lib_index(self):
        # The differential gate: same input, same result on both writers.
        # The probe side is intentionally NOT in this table (G06-b').
        for label, value in self.CASES:
            with self.subTest(case=label):
                launch_home = self._launch_home(value)
                lib_home = self._lib_home(value)
                self.assertEqual(self._norm(launch_home), self._norm(lib_home),
                                 f"{label}: launch={launch_home} lib={lib_home}")

    def test_probe_side_stays_fail_closed_on_unset_or_blank(self):
        # G06-b'反相断言: the read/probe side must NOT take the fallback.
        # `DSH_HOME` unset or blank ⇒ no plane is discovered, so the guard
        # never guesses `~/.dsh` (the existing safety property, kept).
        for label, value in (("unset", None), ("empty", ""),
                             ("spaces", "   "), ("tab", "\t")):
            with self.subTest(case=label):
                env = {} if value is None else {"DSH_HOME": value}
                self.assertEqual(dsh_compat._profile_planes(env), [], label)


@contextlib.contextmanager
def _isolated_profile(fake_home):
    """Point ``Path.home()`` at ``fake_home`` for the duration (F-8).

    The write entry points derive the real DSH home from ``Path.home()``, so a
    test that exercises them would — with the guard removed or regressed —
    happily write ``<home>/.agent-presets`` and ``<home>/.dsh/.agent-presets``
    into the developer's real profile. That is precisely the incident shape this
    task hit three times, so the tests may not *depend* on the guard to stay
    harmless: with ``USERPROFILE``/``HOME`` redirected, a regressed guard writes
    into a throwaway directory instead. On Windows ``Path.home()`` reads
    ``USERPROFILE`` first, hence all four variables.
    """
    fake = Path(fake_home)
    fake.mkdir(parents=True, exist_ok=True)
    with mock.patch.dict(os.environ, {
        "USERPROFILE": str(fake),
        "HOME": str(fake),
        "HOMEDRIVE": fake.drive or "",
        "HOMEPATH": str(fake)[len(fake.drive):] if fake.drive else str(fake),
    }, clear=False):
        yield fake


def _assert_profile_is_redirected(test, fake_home):
    """Fail loudly if the ambient home is still the developer's real one."""
    import importlib
    home = Path.home()
    test.assertEqual(
        home.resolve(), Path(fake_home).resolve(),
        "refusing to exercise write entry points: Path.home() is still the "
        f"real profile ({home}) — the F-8 isolation seam is not in effect")


class WriteEntryGuardTests(unittest.TestCase):
    """The write entry points refuse a real-home target (FIX-316 / V7).

    The guard is symmetric on purpose: install/sync and uninstall both mutate
    the user's real preset root, so both answer to the same rule the isolated
    smoke gate applies. `smoke_preset()` refuses an unset `$DSH_HOME`; without
    the same rule on `install_preset()` a mis-set variable silently rewrites
    the real preset.

    **F-8**: every test here runs under :func:`_isolated_profile`, so the
    "real home" they refuse is a throwaway directory and a *regressed* guard
    cannot touch the developer's profile. The refusal shapes are additionally
    asserted on the pure predicate first — that judgment needs no write path at
    all.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "dsh_launch_write_guard",
            _REPO_ROOT / "adapters" / "dsh" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.launch = module

    def _call(self, func_name, case_value):
        """Run one write entry point with `DSH_HOME` patched; return (rc, out)."""
        func = getattr(self.launch, func_name)
        saved = os.environ.get("DSH_HOME", None)
        had = "DSH_HOME" in os.environ
        try:
            if case_value is None:
                os.environ.pop("DSH_HOME", None)
            else:
                os.environ["DSH_HOME"] = case_value
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream), \
                    contextlib.redirect_stderr(stream):
                code = func()
            return code, stream.getvalue()
        finally:
            if had:
                os.environ["DSH_HOME"] = saved
            else:
                os.environ.pop("DSH_HOME", None)

    # ── the predicate, with no write path involved at all (F-8) ────────────
    def test_refusal_predicate_covers_every_real_home_shape(self):
        with _scratch("spg-test-predicate-") as td:
            fake = Path(td) / "profile"
            with _isolated_profile(fake):
                _assert_profile_is_redirected(self, fake)
                target = self.launch.preset_dir()
                # unset, set-but-blank, the profile itself, the real DSH home.
                for value in (None, "", "   ", "\t", str(fake),
                              str(fake / ".dsh")):
                    with self.subTest(home=value):
                        saved = os.environ.get("DSH_HOME")
                        had = "DSH_HOME" in os.environ
                        try:
                            if value is None:
                                os.environ.pop("DSH_HOME", None)
                            else:
                                os.environ["DSH_HOME"] = value
                            refusal = self.launch.write_side_refusal(
                                target, operation="install")
                        finally:
                            if had:
                                os.environ["DSH_HOME"] = saved
                            else:
                                os.environ.pop("DSH_HOME", None)
                        self.assertIsNotNone(refusal, value)
                # A redirected home is allowed.
                allowed = Path(td) / "redirected"
                saved = os.environ.get("DSH_HOME")
                had = "DSH_HOME" in os.environ
                try:
                    os.environ["DSH_HOME"] = str(allowed)
                    self.assertIsNone(self.launch.write_side_refusal(
                        allowed / ".agent-presets" / "governance",
                        operation="install"))
                finally:
                    if had:
                        os.environ["DSH_HOME"] = saved
                    else:
                        os.environ.pop("DSH_HOME", None)

    def test_blank_and_unset_report_different_reasons(self):
        # F-13: "not set" and "set but blank" need different fixes, so they get
        # different messages.
        with _scratch("spg-test-predicate-") as td, \
                _isolated_profile(Path(td) / "profile"):
            target = self.launch.preset_dir()
            saved = os.environ.get("DSH_HOME")
            had = "DSH_HOME" in os.environ
            try:
                os.environ.pop("DSH_HOME", None)
                unset = self.launch.write_side_refusal(target, operation="install")
                os.environ["DSH_HOME"] = "   "
                blank = self.launch.write_side_refusal(target, operation="install")
            finally:
                if had:
                    os.environ["DSH_HOME"] = saved
                else:
                    os.environ.pop("DSH_HOME", None)
        self.assertIn("is not set", unset)
        self.assertIn("is set but blank", blank)
        self.assertNotEqual(unset, blank)

    # ── entry level, always under a redirected profile (F-8) ───────────────
    def test_unset_dsh_home_is_refused_not_redirected_to_the_real_home(self):
        with _scratch("spg-test-entry-") as td, \
                _isolated_profile(Path(td) / "profile"):
            fake = Path(td) / "profile"
            _assert_profile_is_redirected(self, fake)
            for func_name in ("install_preset", "uninstall_preset"):
                with self.subTest(entry=func_name):
                    code, output = self._call(func_name, None)
                    self.assertEqual(code, self.launch.SMOKE_EXIT_REFUSED, output)
                    self.assertIn("[REFUSED]", output)
                    self.assertIn("DSH_HOME is not set", output)
            # Nothing may have been created under the fake profile.
            self.assertEqual(
                sorted(p.name for p in fake.iterdir()), [],
                "a refused entry point must not create anything")

    def test_real_home_shapes_are_refused(self):
        with _scratch("spg-test-entry-") as td, \
                _isolated_profile(Path(td) / "profile"):
            fake = Path(td) / "profile"
            _assert_profile_is_redirected(self, fake)
            real_home = str(fake)
            real_dsh = str(fake / ".dsh")
            for func_name in ("install_preset", "uninstall_preset"):
                for value in (real_home, real_dsh):
                    with self.subTest(entry=func_name, home=value):
                        code, output = self._call(func_name, value)
                        self.assertEqual(code, self.launch.SMOKE_EXIT_REFUSED, output)
                        self.assertIn("real DSH home", output)
            self.assertEqual(
                [p.name for p in fake.iterdir() if p.name != ".agent-presets"],
                [], "a refused entry point must not create anything")
            self.assertFalse((fake / ".agent-presets").exists())

    def test_uninstall_dry_run_is_allowed_and_writes_nothing(self):
        # R0 F-1 / R2 microfix: `install --dry-run` was allowed (its dry-run
        # branch sits before the guard) while `uninstall --dry-run` was refused
        # (its guard sat first), so the documented read-only preview of the
        # REAL preset root was unreachable. The guard now runs after the
        # dry-run early return, in both entry points.
        with _scratch("spg-test-uninstall-dry-") as td, \
                _isolated_profile(Path(td) / "profile"):
            fake = Path(td) / "profile"
            _assert_profile_is_redirected(self, fake)
            # A real-home SHAPE (the throwaway profile) plus a populated preset.
            fake_dsh = fake / ".dsh"
            target = fake_dsh / ".agent-presets" / "governance"
            target.mkdir(parents=True)
            (target / "preset.yml").write_text("name: governance\n", encoding="utf-8")
            before = sorted(p.name for p in target.iterdir())

            stream = io.StringIO()
            had = "DSH_HOME" in os.environ
            saved = os.environ.get("DSH_HOME")
            try:
                os.environ["DSH_HOME"] = str(fake_dsh)
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream):
                    code = self.launch.uninstall_preset(dry_run=True)
            finally:
                if had:
                    os.environ["DSH_HOME"] = saved
                else:
                    os.environ.pop("DSH_HOME", None)

            output = stream.getvalue()
            after = sorted(p.name for p in target.iterdir())
            still_dir = target.is_dir()
        self.assertEqual(code, 0, output)
        self.assertIn("[DRY-RUN]", output)
        self.assertIn("planned delete", output)
        self.assertNotIn("[REFUSED]", output)
        self.assertEqual(before, after, "uninstall --dry-run must not delete")
        self.assertTrue(still_dir, "uninstall --dry-run must not delete")

    def test_uninstall_dry_run_writes_nothing_under_a_redirected_home(self):
        with _scratch("spg-test-uninstall-dry2-") as td:
            isolated = Path(td) / "dsh-home"
            stream = io.StringIO()
            had = "DSH_HOME" in os.environ
            saved = os.environ.get("DSH_HOME")
            try:
                os.environ["DSH_HOME"] = str(isolated)
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream):
                    code = self.launch.uninstall_preset(dry_run=True)
            finally:
                if had:
                    os.environ["DSH_HOME"] = saved
                else:
                    os.environ.pop("DSH_HOME", None)
            output = stream.getvalue()
            # Zero writes: not even the DSH home may be created for a preview.
            created = isolated.exists()
        self.assertEqual(code, 0, output)
        self.assertIn("[DRY-RUN]", output)
        self.assertFalse(created, "uninstall --dry-run must not create anything")

    def test_real_uninstall_is_still_refused_in_a_real_home_shape(self):
        # The microfix must not weaken the guard on the REAL path.
        with _scratch("spg-test-uninstall-guard-") as td, \
                _isolated_profile(Path(td) / "profile"):
            fake = Path(td) / "profile"
            _assert_profile_is_redirected(self, fake)
            fake_dsh = fake / ".dsh"
            target = fake_dsh / ".agent-presets" / "governance"
            target.mkdir(parents=True)
            (target / "preset.yml").write_text("name: governance\n", encoding="utf-8")
            code, output = self._call("uninstall_preset", str(fake_dsh))
            still_there = (target / "preset.yml").is_file()
        self.assertEqual(code, self.launch.SMOKE_EXIT_REFUSED, output)
        self.assertIn("[REFUSED]", output)
        self.assertTrue(still_there, "a refused uninstall must delete nothing")

    def test_redirected_home_still_installs_and_uninstalls(self):
        # The guard must not block the isolated path every other check uses.
        with _scratch("spg-test-guard-") as td, \
                _isolated_profile(Path(td) / "profile"):
            _assert_profile_is_redirected(self, Path(td) / "profile")
            isolated = str(Path(td) / "dsh-home")
            code, output = self._call("install_preset", isolated)
            self.assertEqual(code, 0, output)
            preset = Path(isolated) / ".agent-presets" / "governance"
            self.assertTrue(preset.is_dir(), output)
            self.assertEqual(
                sorted(p.name for p in preset.iterdir()),
                [".dsh-bundle-version", "agent.cordis.yml", "preset.yml",
                 "skill-root.txt"])
            # newline_policy "lf" applies to the whole preset, not just the
            # composition: copying the metadata as raw bytes made its line
            # endings depend on the checkout.
            for name in ("agent.cordis.yml", "preset.yml", "skill-root.txt",
                         ".dsh-bundle-version"):
                self.assertNotIn(b"\r\n", (preset / name).read_bytes(), name)
            code, output = self._call("uninstall_preset", isolated)
            self.assertEqual(code, 0, output)
            self.assertFalse(preset.exists())

    def test_dry_run_never_writes_even_into_a_real_home(self):
        # `--dry-run` is the documented safe verification path (DEC-158 R1):
        # it must report the resolved home without creating even the preset
        # root. It is the one write-shaped entry that may target the real home,
        # precisely because it writes nothing — so it must NOT be refused.
        # F-8: "the real home" here is the throwaway profile, never the
        # developer's.
        with _scratch("spg-test-dryrun-") as td, \
                _isolated_profile(Path(td) / "profile"):
            fake = Path(td) / "profile"
            _assert_profile_is_redirected(self, fake)
            fake_dsh = str(fake / ".dsh")
            target = fake / ".dsh" / ".agent-presets" / "governance"

            stream = io.StringIO()
            had = "DSH_HOME" in os.environ
            saved = os.environ.get("DSH_HOME")
            try:
                os.environ["DSH_HOME"] = fake_dsh
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream):
                    code = self.launch.install_preset(dry_run=True)
            finally:
                if had:
                    os.environ["DSH_HOME"] = saved
                else:
                    os.environ.pop("DSH_HOME", None)

            output = stream.getvalue()
            self.assertEqual(code, 0, output)
            self.assertIn("[DRY-RUN]", output)
            self.assertNotIn("[REFUSED]", output)
            self.assertFalse(target.exists(), "dry-run must not create the preset")
            self.assertFalse((fake / ".dsh").exists(),
                             "dry-run must not create the DSH home either")


class PublicEntryDecodeBoundaryTests(unittest.TestCase):
    """`main()` must never leak a stack, and a failed install leaves nothing.

    Covers the two R0 findings the first submission missed:

      * **F-2** — design §4.4.6 names three entry points
        (`render_composition` / `verify_preset_loading` / **`main(["--install"])`**)
        and the third had no coverage. Three read points were still able to
        raise out of it (`package.json`, `preset.yml`, `skill-root.txt`).
      * **F-4** — a decode failure *inside* the already-created staging
        directory made `install_preset`'s cleanup branch unreachable, so
        `governance.staging-<pid>-…` stayed behind forever.

    Every case runs against a throwaway repository copy under `%TEMP%` (the
    corruption has to be a real file for the launcher to read) and every
    `DSH_HOME` is a fresh temporary directory. The real repository is copied
    from, never modified.
    """

    COPIES = (
        "adapters/dsh/launch.py",
        "adapters/dsh/AGENTS.md.template",
        "adapters/dsh/adapter-manifest.json",
        "adapters/dsh/host-contract.json",
        "agent-presets/governance/agent.cordis.yml.template",
        "agent-presets/governance/preset.yml",
        "package.json",
        "skills/software-project-governance/infra/dsh_contract.py",
    )

    def _copy_repo(self, root: Path) -> Path:
        for relative in self.COPIES:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_REPO_ROOT / relative, target)
        (root / "adapters" / "dsh" / "skill-shims").mkdir(parents=True, exist_ok=True)
        (root / "skills").mkdir(exist_ok=True)
        return root

    def _launch_from(self, root: Path):
        spec = importlib.util.spec_from_file_location(
            "dsh_launch_entry_probe", root / "adapters" / "dsh" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _run_main(self, module, args, dsh_home):
        """`main()` in-process, under a redirected DSH_HOME. Never raises."""
        stream = io.StringIO()
        with mock.patch.dict(os.environ, {"DSH_HOME": str(dsh_home)}, clear=False):
            with contextlib.redirect_stdout(stream), \
                    contextlib.redirect_stderr(stream):
                code = module.main(args)
        return code, stream.getvalue()

    def test_non_utf8_package_json_is_refused_by_the_install_entry(self):
        with _scratch("spg-test-f2-pkg-") as td:
            root = self._copy_repo(Path(td) / "repo")
            (root / "package.json").write_bytes(
                b'{"version": "\xff bad"}')
            module = self._launch_from(root)
            code, output = self._run_main(module, ["--install"], Path(td) / "home")
        self.assertEqual(code, 1, output)
        self.assertIn("package identity unreadable", output)
        self.assertIn("not valid UTF-8", output)
        self.assertIn("byte offset 13", output)

    def test_non_utf8_preset_metadata_is_refused_with_offset_and_no_residue(self):
        with _scratch("spg-test-f2-meta-") as td:
            root = self._copy_repo(Path(td) / "repo")
            (root / "agent-presets" / "governance" / "preset.yml").write_bytes(
                b"name: x\nbytes: \xff bad\n")
            module = self._launch_from(root)
            home = Path(td) / "home"
            code, output = self._run_main(module, ["--install"], home)
            preset_root = home / ".agent-presets"
            residue = sorted(p.name for p in preset_root.glob("*.staging-*")) \
                if preset_root.is_dir() else []
        self.assertEqual(code, 1, output)
        self.assertIn("not valid UTF-8", output)
        self.assertIn("byte offset 15", output)
        self.assertEqual(residue, [], "a failed install must leave no staging dir")

    def test_failed_install_leaves_no_staging_directory_anywhere(self):
        # F-4 directly: whatever the failure, nothing named
        # `<preset>.staging-*` may survive under the target DSH home, and no
        # partial `governance` preset may be published in its place.
        with _scratch("spg-test-f4-") as td:
            root = self._copy_repo(Path(td) / "repo")
            (root / "agent-presets" / "governance" / "preset.yml").write_bytes(
                b"\xff not utf-8 at all\n")
            module = self._launch_from(root)
            home = Path(td) / "home"
            code, output = self._run_main(module, ["--install"], home)
            leftovers = sorted(
                p.name for p in (home / ".agent-presets").iterdir()) \
                if (home / ".agent-presets").is_dir() else []
        self.assertEqual(code, 1, output)
        self.assertEqual(leftovers, [], leftovers)

    def test_non_utf8_skill_root_marker_does_not_raise_the_verifier(self):
        with _scratch("spg-test-f2-marker-") as td:
            root = self._copy_repo(Path(td) / "repo")
            module = self._launch_from(root)
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_text("- id: x\n", encoding="utf-8")
            (preset / "skill-root.txt").write_bytes(b"\xff bad marker\n")
            surface = module.verify_preset_loading(preset)
        self.assertEqual(surface["verdict"], "FAIL", surface)
        self.assertTrue(surface["issues"], surface)

    def test_healthy_copy_still_installs_through_the_public_entry(self):
        # The control: the boundary above must not block the normal path.
        with _scratch("spg-test-f2-ok-") as td:
            root = self._copy_repo(Path(td) / "repo")
            module = self._launch_from(root)
            home = Path(td) / "home"
            code, output = self._run_main(module, ["--install"], home)
            written = sorted(p.name for p in
                             (home / ".agent-presets" / "governance").iterdir()) \
                if (home / ".agent-presets" / "governance").is_dir() else []
        self.assertEqual(code, 0, output)
        self.assertEqual(written, [".dsh-bundle-version", "agent.cordis.yml",
                                   "preset.yml", "skill-root.txt"])

    # ── N-1: the guard must refuse when the profile is unresolvable ────────
    _PROFILE_VARS = ("USERPROFILE", "HOME", "HOMEDRIVE", "HOMEPATH")

    _DRIVER = (
        "import contextlib, importlib.util, io, json, os, sys\n"
        "from pathlib import Path\n"
        "root = Path(sys.argv[1]); entry = sys.argv[2]; dsh_home = sys.argv[3]\n"
        "spec = importlib.util.spec_from_file_location("
        "'L', root / 'adapters' / 'dsh' / 'launch.py')\n"
        "module = importlib.util.module_from_spec(spec); "
        "sys.modules['L'] = module\n"
        "spec.loader.exec_module(module)\n"
        "os.environ['DSH_HOME'] = dsh_home\n"
        "stream = io.StringIO()\n"
        "raised = None\n"
        "code = None\n"
        "try:\n"
        "    with contextlib.redirect_stdout(stream), "
        "contextlib.redirect_stderr(stream):\n"
        "        if entry == 'main':\n"
        "            code = module.main(['--install'])\n"
        "        elif entry == 'smoke':\n"
        "            code = module.smoke_preset()\n"
        "        else:\n"
        "            code = getattr(module, entry)()\n"
        "except BaseException as exc:\n"
        "    raised = f'{type(exc).__name__}: {exc}'\n"
        "print(json.dumps({'code': code, 'raised': raised, "
        "'traceback': 'Traceback (most recent call last)' in stream.getvalue(), "
        "'output': stream.getvalue()}))\n"
    )

    @staticmethod
    def _profileless_env(dsh_home):
        """Only what a process needs to start — no profile at all."""
        env = {}
        for key in ("PATH", "SystemRoot", "windir", "PATHEXT", "TEMP", "TMP",
                    "COMSPEC", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
                    "OS"):
            if key in os.environ:
                env[key] = os.environ[key]
        env["DSH_HOME"] = str(dsh_home)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def test_unresolvable_profile_is_refused_not_raised(self):
        """N-1 reverse case: the guard's `Path.home()` must not escape.

        With every profile variable absent, ``Path.home()`` raises
        ``RuntimeError``. The guard needs it only to *compare* against, so an
        unresolvable profile has to become a fail-closed refusal — not a
        traceback out of a public entry point, which is what this test pins.
        Removing the `try/except` in `write_side_refusal` turns this red.

        Runs in a subprocess because the profile must be absent from the
        environment the launcher sees; `DSH_HOME` is a fresh %TEMP% directory
        and nothing may be written into it.
        """
        # The premise: this environment really does raise (otherwise the case
        # would be vacuous and would silently stop testing anything).
        saved = {name: os.environ.pop(name, None) for name in self._PROFILE_VARS}
        try:
            raised = False
            try:
                Path.home()
            except RuntimeError:
                raised = True
        finally:
            for name, value in saved.items():
                if value is not None:
                    os.environ[name] = value
        if not raised:
            self.skipTest(
                "Path.home() resolves even with every profile variable "
                "cleared — the unresolvable-profile case is NOT_RUN here")

        with _scratch("spg-test-n1-") as td:
            root = self._copy_repo(Path(td) / "repo")
            for entry in ("install_preset", "uninstall_preset", "main"):
                with self.subTest(entry=entry):
                    home = Path(td) / f"home-{entry}"
                    home.mkdir()
                    before = sorted(p.name for p in home.rglob("*"))
                    proc = subprocess.run(
                        [sys.executable, "-c", self._DRIVER, str(root), entry,
                         str(home)],
                        cwd=str(root), env=self._profileless_env(home),
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
                    payload = json.loads(proc.stdout.strip().splitlines()[-1])
                    after = sorted(p.name for p in home.rglob("*"))
                    self.assertIsNone(payload["raised"],
                                      f"{entry} raised: {payload['raised']}")
                    self.assertFalse(payload["traceback"], payload["output"])
                    self.assertEqual(payload["code"], 2, payload["output"])
                    self.assertIn("cannot be resolved", payload["output"])
                    self.assertIn("DSH_HOME is set", payload["output"])
                    self.assertEqual(before, after,
                                     f"{entry} wrote into DSH_HOME")

    def test_smoke_refuses_when_the_real_home_cannot_be_fingerprinted(self):
        # N-1's smoke half: `smoke_preset()` fingerprints the real home, so an
        # unresolvable profile must be a REFUSED exit, not a `RuntimeError`
        # escaping a public entry point.
        saved = {name: os.environ.pop(name, None) for name in self._PROFILE_VARS}
        try:
            raised = False
            try:
                Path.home()
            except RuntimeError:
                raised = True
        finally:
            for name, value in saved.items():
                if value is not None:
                    os.environ[name] = value
        if not raised:
            self.skipTest("Path.home() resolves here — NOT_RUN")

        with _scratch("spg-test-n1-smoke-") as td:
            root = self._copy_repo(Path(td) / "repo")
            home = Path(td) / "home"
            home.mkdir()
            before = sorted(p.name for p in home.rglob("*"))
            proc = subprocess.run(
                [sys.executable, "-c", self._DRIVER, str(root), "smoke",
                 str(home)],
                cwd=str(root), env=self._profileless_env(home),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=300)
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            after = sorted(p.name for p in home.rglob("*"))
        self.assertIsNone(payload["raised"], payload["raised"])
        self.assertFalse(payload["traceback"], payload["output"])
        self.assertEqual(payload["code"], 2, payload["output"])
        self.assertIn("REFUSED", payload["output"])
        self.assertEqual(before, after)


class StagingCleanupTests(unittest.TestCase):
    """N-2: the cleanup fuse for a failure *after* the staging dir exists.

    F-4 moved the metadata decode ahead of `mkdir`, which is why the ordinary
    corrupt-file cases cannot reach the fuse any more. That made the fuse
    untested — and an untested fuse is exactly the silent-removal hazard the
    reviewer flagged. This class induces a failure *inside* the write loop
    instead, so the `rmtree(staging)` branch is the only thing that can keep
    the DSH home clean.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "dsh_launch_staging", _REPO_ROOT / "adapters" / "dsh" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.launch = module

    def test_write_failure_leaves_no_staging_directory(self):
        # Fail *inside* the write loop, which is strictly after `staging` was
        # created — the only way to reach the cleanup fuse now that the
        # metadata decode happens before `mkdir` (F-4). `pathlib.Path.write_bytes`
        # is patched on the ABC so every concrete path object is affected;
        # `write_rendered_preset`'s own `except OSError` returns False, and
        # `install_preset` must clear the residue (N-2).
        state = {"fired": False}
        original_write_bytes = Path.write_bytes

        def failing_write_bytes(self, data):
            if not state["fired"] and b"phase-boom" in data:
                state["fired"] = True
                raise OSError(28, "No space left on device (induced)")
            return original_write_bytes(self, data)

        original_version = self.launch.package_version
        self.launch.package_version = lambda: "phase-boom"
        try:
            with _scratch("spg-test-n2-") as td, \
                    mock.patch.object(Path, "write_bytes", failing_write_bytes):
                isolated = Path(td) / "dsh-home"
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream), \
                        mock.patch.dict(os.environ, {"DSH_HOME": str(isolated)},
                                        clear=False):
                    code = self.launch.install_preset()
                output = stream.getvalue()
                preset_root = isolated / ".agent-presets"
                leftovers = sorted(p.name for p in preset_root.rglob("*")) \
                    if preset_root.is_dir() else []
        finally:
            self.launch.package_version = original_version

        self.assertTrue(state["fired"], "the induced failure never fired")
        self.assertEqual(code, 1, output)
        self.assertEqual(leftovers, [],
                         f"a failed install left the DSH home dirty: {leftovers}")

    def test_caller_fuse_removes_a_staging_tree_the_writer_left_behind(self):
        # N-2's real subject: `install_preset`'s own `finally`-style removal.
        # The test above is satisfied by the writer's internal cleanup, so it
        # cannot pin the caller's fuse. Here the writer aborts by *raising*
        # after creating the directory — exactly the shape `install_preset`
        # documents it must survive (`governance.staging-<pid>-…` must not
        # survive a failed install). Removing either of the caller's two
        # `rmtree(staging, ...)` lines turns this red.
        original = self.launch.write_rendered_preset

        def aborting_writer(destination, version=None):
            Path(destination).mkdir(parents=True, exist_ok=True)
            (Path(destination) / "partial.tmp").write_text(
                "partial\n", encoding="utf-8")
            raise OSError(28, "No space left on device (induced)")

        with _scratch("spg-test-n2b-") as td:
            isolated = Path(td) / "dsh-home"
            stream = io.StringIO()
            self.launch.write_rendered_preset = aborting_writer
            try:
                with contextlib.redirect_stdout(stream), \
                        contextlib.redirect_stderr(stream), \
                        mock.patch.dict(os.environ, {"DSH_HOME": str(isolated)},
                                        clear=False):
                    code = self.launch.install_preset()
            finally:
                self.launch.write_rendered_preset = original
            output = stream.getvalue()
            preset_root = isolated / ".agent-presets"
            leftovers = sorted(p.name for p in preset_root.rglob("*")) \
                if preset_root.is_dir() else []

        self.assertEqual(code, 1, output)
        self.assertEqual(leftovers, [],
                         f"the caller's fuse did not clear the staging tree: "
                         f"{leftovers}")


if __name__ == "__main__":
    unittest.main()
