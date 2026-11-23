"""FEAT-022 light-registry tests (AUDIT-150 §9.1 REFACTOR-light-registry).

TDD order (packet acceptance ⑤): this file was written and run RED (module
absent) BEFORE ``infra/registry.py`` existed; the RED run is recorded in the
task evidence.

Machine judgements, each anchored to a live fact source (none hand-copied):

  ① R5 registration integrity — the registry's declared faces are compared to
     the FEAT-020 frozen snapshot (fast face) and to the live engine faces
     extracted by ``contract_matrix.generator`` (consumed, never redefined);
     synthetic projections carry the negative controls.
  ② startup import set unchanged — the ``-X importtime`` caliber named by the
     packet (§9.5, FEAT-018) plus the R6 ``sys.modules`` probe: the engine's
     frozen 196-module face (``core/architecture-baseline.json`` r6) is
     neither grown by the registry nor reachable from ``import registry`` /
     per-command assembly, and the light faces stay under that budget. The
     importtime rows are parsed by ``perf_protocol.parse_importtime`` — the
     module owning that caliber is consumed, never re-implemented.
  ③ assembly path (loader whitelist) — declared keys resolve; undeclared keys
     and out-of-whitelist modules fail closed with explicit errors.
  ④ CheckSpec shape identity — the registry rows ARE
     ``contracts.CheckSpec`` instances (reflection + AST: the module never
     redefines an L0 shape).

The engine source is read for measurements only; the registry module is the
only artifact under test.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_registry.py" -v
"""

import ast
import dataclasses
import functools
import inspect
import importlib
import io
from contextlib import ExitStack, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch
import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_SKILL_ROOT = _INFRA_DIR.parent
_REPO_ROOT = _SKILL_ROOT.parents[1]
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import contracts as c  # noqa: E402
import perf_protocol as protocol  # noqa: E402 — owns the -X importtime caliber
import quickscan_registry as qr  # noqa: E402
import registry as reg  # noqa: E402

ENGINE = _INFRA_DIR / "verify_workflow.py"
REGISTRY_PATH = _INFRA_DIR / "registry.py"
SNAPSHOT = _INFRA_DIR / "contract_matrix" / "snapshots.json"
BASELINE = _SKILL_ROOT / "core" / "architecture-baseline.json"

# Independent import budget measured by the isolated R6 probe.
FROZEN_ENGINE_IMPORT_COUNT = 212

# Mechanism red lines (§9.1): no discovery scan, no third-party plugin loader.
FORBIDDEN_REGISTRY_NAMES = {
    "pkgutil", "walk_packages", "iter_modules", "importlib.metadata",
    "entry_points", "glob", "rglob", "iterdir", "walk", "listdir",
    "scandir", "open", "print", "eval", "exec", "compile", "__import__",
}
FORBIDDEN_REGISTRY_ATTRS = {
    "glob", "rglob", "iterdir", "walk", "listdir", "scandir",
    "read_text", "write_text", "system", "popen",
}
L0_SHAPE_NAMES = (
    "CheckID", "CommandKey", "Finding", "CheckResult", "CheckSpec",
    "ContractViolation", "SEVERITIES",
)


# ── live engine measurements (read-only) ────────────────────────────────────


def _engine_source():
    return ENGINE.read_text(encoding="utf-8")


def _report_tree(report):
    function = ast.parse(inspect.getsource(report)).body[0]
    for index, statement in enumerate(function.body):
        if isinstance(statement, ast.Return):
            function.body = function.body[:index + 1]
            break
    return function


def _contributes_issues(report):
    """Follow the report's returned counter, including the shared packet renderer."""
    node = _report_tree(report)
    returned = node.body[-1].value
    if isinstance(returned, ast.Constant):
        return returned.value != 0
    for operation in ast.walk(node):
        if (isinstance(operation, ast.AugAssign) and isinstance(operation.target, ast.Name)
                and operation.target.id == returned.id):
            return True
        if (isinstance(operation, ast.Assign) and isinstance(operation.value, ast.Call)
                and isinstance(operation.value.func, ast.Name)
                and any(isinstance(t, ast.Name) and t.id == returned.id for t in operation.targets)):
            renderer = getattr(inspect.getmodule(report), operation.value.func.id)
            return _contributes_issues(renderer)
    return False


def _segment_facts():
    """Observe the actual full run's bindings independently of its source census."""
    import verify_workflow as engine

    facts = {}

    def record(report, *args):
        segment = report.__name__.split("_")[1]
        if segment in facts:
            raise AssertionError(f"full profile ran Check {segment} twice")
        bound = inspect.signature(report).bind(*args).arguments
        tree = _report_tree(report)
        calls = {node.func.id for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        targets = {bound[name] for name in calls & bound.keys() if callable(bound[name])}
        for statement in ast.walk(tree):
            if isinstance(statement, ast.ImportFrom):
                for alias in statement.names:
                    if (alias.asname or alias.name) in calls:
                        targets.add(getattr(importlib.import_module(statement.module), alias.name))
        calls = {getattr(bound[name], "__name__", None) if name in bound else name
                 for name in calls}
        facts[segment] = {
            "calls": calls, "targets": targets, "all_issues": _contributes_issues(report),
        }
        return 1

    with ExitStack() as stack, redirect_stdout(io.StringIO()):
        for path in _INFRA_DIR.glob("health_*_sections.py"):
            owner = importlib.import_module(path.stem)
            for name, report in inspect.getmembers(owner, inspect.isfunction):
                if name.startswith("section_"):
                    stack.enter_context(patch.object(owner, name, functools.partial(record, report)))
        if engine._run_full_engine_checks(SimpleNamespace(product_gates=True)) != len(facts):
            raise AssertionError("full engine omitted a returned report count")
    return facts


def _engine_modules():
    """{defined symbol: set(infra module path)} over the tree (tests excluded)."""
    modules = {}
    for path in sorted(_INFRA_DIR.rglob("*.py")):
        posix = path.as_posix()
        if "__pycache__" in posix or "/tests/" in posix:
            continue
        rel = path.relative_to(_INFRA_DIR).as_posix()[:-3].replace("/", ".")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                modules.setdefault(node.name, set()).add(rel)
    return modules


@functools.lru_cache(maxsize=1)
def _frozen_faces():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))["faces"]


def _isolated_script(body):
    """A ``python -I -B`` probe body with the infra dir on ``sys.path``."""
    return ("import sys, json\n"
            f"sys.path.insert(0, {str(_INFRA_DIR)!r})\n"
            + body)


def _run_isolated(body, *extra_args):
    """Run one isolated interpreter probe; non-zero exit fails loudly.

    A measurement that did not run must never look like a measurement that
    passed — the assertion error carries the probe's own stderr.
    """
    completed = subprocess.run(
        [sys.executable, "-I", "-B", *extra_args, "-c",
         _isolated_script(body)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, check=False)
    if completed.returncode != 0:
        raise AssertionError(
            f"probe failed (exit {completed.returncode}):\n"
            f"{completed.stderr[-2000:]}")
    return completed


def _probe(body):
    """Run a probe whose last stdout line is a JSON payload."""
    completed = _run_isolated(body)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _importtime_rows(body):
    """``-X importtime`` rows of one probe (§9.5 caliber, FEAT-018 owner).

    ``perf_protocol.parse_importtime`` is consumed rather than re-implemented:
    the row grammar (``self_us | cumulative_us | <indent><module>``) has one
    owner in this tree.
    """
    completed = _run_isolated(body, "-X", "importtime")
    return protocol.parse_importtime(completed.stderr)


@functools.lru_cache(maxsize=1)
def _engine_startup_face():
    """The engine's own startup face, measured with the R6 probe caliber.

    Same probe as ``archguard_ratchet.measure_cold_import`` /
    ``perf_protocol.probe_sys_modules``: ``python -I -B`` importing
    ``verify_workflow`` and dumping ``sorted(sys.modules)``. Cached because
    the engine import is the most expensive probe in this file.
    """
    return _probe(
        "import verify_workflow\n"
        "mods = sorted(sys.modules)\n"
        "print(json.dumps({'count': len(mods), 'modules': mods}))\n")


# ── ④ CheckSpec shape identity ──────────────────────────────────────────────


class ContractShapeTests(unittest.TestCase):
    """Acceptance ④ — consume the L0 shape, never redefine it."""

    def test_rows_are_contract_checkspec_instances(self):
        self.assertTrue(reg.CHECK_SPECS)
        for spec in reg.CHECK_SPECS:
            self.assertIsInstance(spec, c.CheckSpec)

    def test_registry_reexports_the_contract_type_itself(self):
        self.assertIs(reg.CheckSpec, c.CheckSpec)

    def test_field_set_is_identical_to_the_contract(self):
        contract = tuple(f.name for f in dataclasses.fields(c.CheckSpec))
        self.assertEqual(tuple(reg.CHECK_SPEC_FIELDS), contract)
        for spec in reg.CHECK_SPECS:
            self.assertEqual(
                tuple(f.name for f in dataclasses.fields(type(spec))), contract)
            self.assertEqual(set(spec.__dict__), set(contract))

    def test_quickscan_subset_alignment(self):
        self.assertLessEqual(set(qr.SEGMENT_SPEC_FIELDS),
                             set(reg.CHECK_SPEC_FIELDS))

    def test_registry_module_does_not_redefine_l0_shapes(self):
        tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
        defined = {node.name for node in tree.body
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
        for shape in L0_SHAPE_NAMES:
            self.assertNotIn(shape, defined,
                             f"{shape} must be consumed from contracts.py")

    def test_registry_imports_the_contract_module(self):
        tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
        modules = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        self.assertIn("contracts", modules)


# ── ① command registry ────────────────────────────────────────────


class CommandRegistryTests(unittest.TestCase):

    def test_gate_handler_follows_public_override_and_restoration(self):
        import governance_fact_cli
        import verify_workflow as workflow

        native = reg.load_handler("gate-check", parsed_args=True)
        self.assertIs(native, governance_fact_cli.cmd_gate_check)
        def override(args):
            return args.unit

        with patch.object(workflow, "cmd_gate_check", override):
            selected = reg.load_handler("gate-check", parsed_args=True)
            self.assertIs(selected, override)
            self.assertEqual(selected(SimpleNamespace(unit="FIX-535")), "FIX-535")
        with patch.object(workflow, "cmd_gate_check", None):
            with self.assertRaisesRegex(reg.LoaderResolutionError, "verify_workflow.cmd_gate_check.*NoneType"):
                reg.load_handler("gate-check", parsed_args=True)
        original = workflow.cmd_gate_check
        try:
            del workflow.cmd_gate_check
            with self.assertRaisesRegex(reg.LoaderResolutionError, "does not define 'cmd_gate_check'"):
                reg.load_handler("gate-check")
        finally:
            workflow.cmd_gate_check = original
        self.assertIs(reg.load_handler("gate-check"), native)

    def test_gate_registration_observes_the_inspected_owner_and_real_namespace_call(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("verify_workflow", "registry", "workflow_cli", "workflow_cli_checks",
                         "workflow_cli_operations", "governance_fact_cli", "loop_workflow", "resolve_entry"):
                shutil.copyfile(_INFRA_DIR / (name + ".py"), root / (name + ".py"))
            def inspect_gate():
                return inspect_cli_registration(root / "verify_workflow.py", "gate-check", "cmd_gate_check")
            self.assertTrue(all(inspect_gate().values()))
            owner = root / "governance_fact_cli.py"
            original = owner.read_bytes()
            for replacement in (None, b"def cmd_gate_check(args, extra): pass", b"cmd_gate_check = None",
                                b"def cmd_gate_check(args): yield args", b"def (", original + b"\ncmd_gate_check = None"):
                with self.subTest(replacement=None if replacement is None else replacement[-32:]):
                    if replacement is None:
                        owner.unlink()
                    else:
                        owner.write_bytes(replacement)
                    self.assertFalse(inspect_gate()["dispatch"])
                    owner.write_bytes(original)
            for provider, name in (("loop_workflow", "gate_review"), ("resolve_entry", "current_host_root")):
                imported = f"from {provider} import {name}".encode()
                with self.subTest(provider=provider):
                    for replacement in (b"pass", f"from missing_provider import {name}".encode(),
                                        imported + b" as wrong_reference"):
                        owner.write_bytes(original.replace(imported, replacement))
                        self.assertFalse(inspect_gate()["dispatch"])
                    owner.write_bytes(original)
            owner.write_bytes(original.replace(b"from loop_workflow import gate_review",
                                               b"from loop_workflow import gate_review as review")
                                      .replace(b"= gate_review(", b"= review("))
            self.assertTrue(inspect_gate()["dispatch"])
            owner.write_bytes(original)
            registry_source = root / "registry.py"
            declared = registry_source.read_bytes()
            for override in (b"LOADER_WHITELIST = ()", b"del LOADER_WHITELIST",
                             b"LOADER_WHITELIST = ['governance_fact_cli']\nLOADER_WHITELIST.clear()"):
                registry_source.write_bytes(declared + b"\n" + override)
                self.assertFalse(inspect_gate()["dispatch"])
            registry_source.write_bytes(declared)
            dependency = root / "loop_workflow.py"
            source = dependency.read_bytes()
            dependency.write_bytes(source + b"\ngate_review = None")
            self.assertFalse(inspect_gate()["dispatch"])
            dependency.write_bytes(source)
            self.assertTrue(all(inspect_gate().values()))

    def test_workspace_entries_preserve_replacements_and_loader_errors(self):
        import verify_workflow as workflow

        for load, key, attr in ((reg.load_handler, "check-plugin-freshness", "cmd_check_plugin_freshness"),
                                (reg.load_check, "check-10", "check_m5_compliance_with_record_scope"),
                                (reg.load_check, "check-25", "check_untracked_files")):
            with self.subTest(key=key):
                native = load(key)
                replacement = lambda *args: key
                with patch.object(workflow, attr, replacement):
                    self.assertIs(load(key), replacement)
                with patch.object(workflow, attr, None), self.assertRaises(reg.LoaderResolutionError):
                    load(key)
                self.assertIs(load(key), native)

    def test_freshness_command_preserves_inner_global_and_outer_loader_errors(self):
        import verify_workflow as workflow

        args = SimpleNamespace()
        public = workflow.check_plugin_freshness
        entries = (workflow.cmd_check_plugin_freshness, reg.load_handler("check-plugin-freshness"))
        try:
            del workflow.check_plugin_freshness
            for entry in entries:
                with self.assertRaises(NameError) as error:
                    entry(args)
                self.assertEqual(error.exception.name, "check_plugin_freshness")
        finally:
            workflow.check_plugin_freshness = public
        with patch.object(workflow, "check_plugin_freshness", None):
            for entry in entries:
                with self.assertRaises(TypeError):
                    entry(args)
        outer = workflow.cmd_check_plugin_freshness
        try:
            del workflow.cmd_check_plugin_freshness
            with self.assertRaises(reg.LoaderResolutionError):
                reg.load_handler("check-plugin-freshness")
        finally:
            workflow.cmd_check_plugin_freshness = outer
        self.assertIs(reg.load_handler("check-plugin-freshness"), entries[1])

    def test_workspace_command_observes_the_target_handler_and_freshness_reader(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("verify_workflow", "registry", "workflow_cli", "workflow_cli_checks",
                         "workflow_cli_operations", "workspace_check_cli", "workspace_checks", "project_paths"):
                shutil.copyfile(_INFRA_DIR / (name + ".py"), root / (name + ".py"))
            def facts():
                return inspect_cli_registration(root / "verify_workflow.py", "check-plugin-freshness",
                                                "cmd_check_plugin_freshness")

            self.assertTrue(all(facts().values()))
            for name, mutation in (("workspace_checks", b"cmd_check_plugin_freshness = None"),
                                   ("workspace_check_cli", b"report_plugin_freshness = None"),
                                   ("workspace_checks", b"def check_plugin_freshness(extra): pass"),
                                   ("registry", b"LOADER_WHITELIST = ()")):
                with self.subTest(name=name, mutation=mutation):
                    path = root / (name + ".py")
                    original = path.read_bytes()
                    path.write_bytes(original + b"\n" + mutation)
                    self.assertFalse(facts()["dispatch"])
                    path.write_bytes(original)

            engine = root / "verify_workflow.py"
            source = engine.read_bytes()
            owner = root / "workspace_checks.py"
            native = owner.read_bytes()
            for setter, bad_setter, bad_default in (
                (b"_workspace_checks._product_root = lambda: ROOT",
                 b"_workspace_checks._product_root = lambda required: ROOT", b"_product_root = None"),
                (b"_workspace_checks.effective_entry = _effective_engine_command",
                 b"_workspace_checks.effective_entry = lambda name, native, required: native", b"del effective_entry"),
            ):
                with self.subTest(setter=setter):
                    self.assertEqual(source.count(setter), 1)
                    owner.write_bytes(native + b"\n" + bad_default)
                    self.assertTrue(facts()["dispatch"])
                    engine.write_bytes(source.replace(setter, b""))
                    self.assertFalse(facts()["dispatch"])
                    owner.write_bytes(native)
                    self.assertTrue(facts()["dispatch"])
                    engine.write_bytes(source.replace(setter, bad_setter))
                    self.assertFalse(facts()["dispatch"])
                    engine.write_bytes(source + b"\n" + bad_setter + b"\n")
                    self.assertTrue(facts()["dispatch"])  # sys.exit(main()) already ran
                    engine.write_bytes(source)

            root_setter = b"_workspace_checks._product_root = lambda: ROOT"
            engine.write_bytes(source.replace(root_setter, b"_workspace_checks._product_root = lambda: RO0T"))
            self.assertFalse(facts()["dispatch"])
            engine.write_bytes(source.replace(root_setter, b"_workspace_checks._product_root = lambda: 1 + 2"))
            self.assertFalse(facts()["dispatch"])
            owner.write_bytes(native.replace(b"from project_paths import package_root",
                                            b"from project_paths import absent_package_root as package_root"))
            engine.write_bytes(source.replace(root_setter, b""))
            self.assertFalse(facts()["dispatch"])
            engine.write_bytes(source)
            self.assertTrue(facts()["dispatch"])  # the broken default is unused
            owner.write_bytes(native)
            reader = b"current = check_plugin_freshness if name"
            self.assertEqual(source.count(reader), 1)
            engine.write_bytes(source.replace(reader, b"current = check_plugin_freshnes if name"))
            self.assertFalse(facts()["dispatch"])
            engine.write_bytes(source)
            registry = root / "registry.py"
            registry_source = registry.read_bytes()
            registered = b"    return resolve_loader(path)\n\n\ndef handler_alias_groups"
            self.assertEqual(registry_source.count(registered), 1)
            registry.write_bytes(registry_source.replace(registered, b"    return None\n\n\ndef handler_alias_groups"))
            self.assertFalse(facts()["dispatch"])
            registry.write_bytes(registry_source)
            self.assertTrue(all(facts().values()))

    def test_declares_the_frozen_key_count(self):
        self.assertEqual(len(reg.COMMAND_SPECS), _frozen_faces()["cli_dispatch"]["key_count"])
        self.assertEqual(len(reg.command_keys()), _frozen_faces()["cli_dispatch"]["key_count"])
        self.assertEqual(len(set(reg.command_keys())), _frozen_faces()["cli_dispatch"]["key_count"])

    def test_key_set_matches_the_frozen_snapshot(self):
        frozen = set(_frozen_faces()["cli_dispatch"]["keys"])
        self.assertEqual(set(reg.command_keys()), frozen)

    def test_rows_are_sorted_and_generated_from_the_declaration(self):
        keys = reg.command_keys()
        self.assertEqual(list(keys), sorted(keys))
        for spec in reg.COMMAND_SPECS:
            self.assertEqual(spec, reg.command_spec(spec.key))

    def test_handlers_are_dotted_paths_inside_the_whitelist(self):
        for spec in reg.COMMAND_SPECS:
            module = reg.loader_module(spec.handler)
            attr = reg.loader_attr(spec.handler)
            self.assertEqual(spec.handler, f"{module}.{attr}")
            self.assertIn(module, reg.LOADER_WHITELIST)

    def test_alias_groups_match_the_frozen_snapshot(self):
        frozen = _frozen_faces()["cli_dispatch"]["alias_groups"]
        derived = {attr: list(keys)
                   for attr, keys in reg.handler_alias_groups().items()}
        self.assertEqual(derived, frozen)

    def test_dsh_registry_respects_replaced_workflow_commands(self):
        import verify_workflow as workflow

        for key in ("check-dsh-preset-compat", "check-dsh-preset-smoke", "check-dsh-boundary", "dsh-doctor"):
            name = "cmd_" + key.replace("-", "_")
            with self.subTest(key=key):
                native = reg.load_handler(key, parsed_args=True)
                self.assertNotEqual(native.__module__, workflow.__name__)
                with patch.object(workflow, name, lambda args: args.command) as replacement:
                    self.assertIs(reg.load_handler(key, parsed_args=True), replacement)
                    self.assertEqual(workflow.main([key]), key)
                self.assertIs(reg.load_handler(key, parsed_args=True), native)

    def test_dsh_routes_observe_the_inspected_installation(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "infra"
            shutil.copytree(_INFRA_DIR, target, ignore=shutil.ignore_patterns("tests", "__pycache__"))
            engine = target / ENGINE.name
            for key, handler, module in (
                ("check-dsh-preset-compat", "cmd_check_dsh_preset_compat", "dsh_compat.py"),
                ("check-dsh-preset-smoke", "cmd_check_dsh_preset_smoke", "host_loader_probes.py"),
                ("dsh-doctor", "cmd_dsh_doctor", "host_validation_cli.py"),
            ):
                with self.subTest(key=key):
                    owner = target / module
                    saved = owner.read_bytes()
                    self.assertTrue(all(inspect_cli_registration(engine, key, handler).values()))
                    owner.unlink()
                    self.assertFalse(inspect_cli_registration(engine, key, handler)["handler"])
                    owner.write_bytes(saved)
                    self.assertTrue(all(inspect_cli_registration(engine, key, handler).values()))

    def test_engine_hosted_and_domain_hosted_keys_are_disclosed(self):
        definitions = _engine_modules()
        for spec in reg.COMMAND_SPECS:
            attr = reg.loader_attr(spec.handler)
            self.assertIn(reg.loader_module(spec.handler),
                          definitions.get(attr, set()),
                          f"{spec.key}: {attr} is not defined there")
        migrated = sorted(spec.key for spec in reg.COMMAND_SPECS
                          if reg.loader_module(spec.handler)
                          != reg.ENGINE_MODULE)
        self.assertEqual(migrated, [
            "archguard-ratchet",
            "authority-ledger",
            "baseline-evaluate", "baseline-register",
            "check-capability-registry",
            "check-dsh-boundary", "check-dsh-preset-compat", "check-dsh-preset-smoke",
            "check-entry-bootstrap-sync",
            "check-injection-budget",
            "check-manifest-consistency", "check-plugin-freshness", "check-review-debt",
            "decision-append", "dsh-doctor",
            "evidence-append", "gate-check",
            "governance-bootstrap",
            "governance-cost-report",
            "locks-amend", "locks-extend", "locks-release",
            "pins",
            "premise",
            "quality-tools", "release-ledger", "release-projection",
            "task-row-update",
        ])

    def test_release_commands_resolve_native_and_follow_live_overrides(self):
        from unittest.mock import patch
        import release_validation_cli
        import verify_workflow

        for key in ("quality-tools", "release-projection", "release-ledger"):
            name = "cmd_" + key.replace("-", "_")
            with self.subTest(key=key):
                native = getattr(release_validation_cli, name)
                self.assertIs(reg.load_handler(key), native)
                marker = lambda args: args
                with patch.object(verify_workflow, name, marker):
                    self.assertIs(reg.load_handler(key), marker)
                with patch.object(verify_workflow, name, None):
                    with self.assertRaises(reg.LoaderResolutionError):
                        reg.load_handler(key)
                self.assertIs(reg.load_handler(key), native)

    def test_release_registration_observes_the_target_owner_and_its_final_binding(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in ("verify_workflow.py", "registry.py", "workflow_cli.py", "workflow_cli_checks.py",
                         "workflow_cli_operations.py", "release_validation_cli.py"):
                shutil.copyfile(Path(reg.__file__).parent / name, target / name)
            source = Path(reg.__file__).parent
            shutil.copyfile(source / "project_paths.py", target / "project_paths.py")
            shutil.copytree(source / "release", target / "release")
            engine = target / "verify_workflow.py"
            owner = target / "release_validation_cli.py"
            original = owner.read_text(encoding="utf-8")
            for key in ("release-projection", "release-ledger", "quality-tools"):
                name = "cmd_" + key.replace("-", "_")
                misbinding = {
                    "release-ledger": ("host, plugin, context, validate =", "host, plugin, unused, validate ="),
                    "release-projection": ("plugin, check, write =", "plugin, unused, write ="),
                    "quality-tools": ("probe_quality_tools=_quality_probe", "probe_quality_tools=_unused"),
                }[key]
                for label, content, available in (
                        ("healthy", original, True), ("missing", None, False),
                        ("provider binding", original.replace(*misbinding), False),
                        ("final binding", original + "\n" + name + " = None\n", False),
                        ("extra required argument", original.replace("def " + name + "(",
                                                                    "def " + name + "(policy, "), False),
                        ("restored", original, True)):
                    with self.subTest(key=key, state=label):
                        if content is None:
                            owner.unlink()
                        else:
                            ast.parse(content, filename=str(owner))
                            owner.write_text(content, encoding="utf-8")
                        self.assertEqual(inspect_cli_registration(engine, key, name),
                                         {"main": True, "argparse": True, "handler": available,
                                          "dispatch": available})

            shipped = engine.read_text(encoding="utf-8")
            selected = {
                "release-ledger": ("lambda: PLUGIN_ROOT, RepositoryContext,",
                                   "lambda: PLUGIN_ROOT, missing_context,",
                                   "from release.context import RepositoryContext"),
                "release-projection": ("lambda: PLUGIN_ROOT, check_projections,",
                                       "lambda: PLUGIN_ROOT, missing_check,",
                                       "from release.projection import check_projections, write_projections"),
                "quality-tools": ('"probe_quality_tools": "release.quality"',
                                  '"probe_quality_tools": "missing_quality"',
                                  "from release.quality import probe_quality_tools"),
            }
            guard = 'if __name__ in ("verify_workflow", "__main__"):\n        _bind_release_commands('
            for key, (live, broken, fallback) in selected.items():
                handler = "cmd_" + key.replace("-", "_")
                native_missing = original.replace(fallback, fallback.replace("from release.", "from unavailable."))
                provider = {"release-ledger": "_ledger_inputs", "release-projection": "_projection_inputs",
                            "quality-tools": "_quality_probe"}[key]
                names = ["_ledger_inputs", "_projection_inputs", "_quality_probe", "effective_command"]
                declaration = "    global " + ", ".join(names)
                remaining = "    global " + ", ".join(name for name in names if name != provider)
                self.assertEqual(original.count(declaration), 1)
                local_only = original.replace(declaration, remaining)
                self.assertIn(live, shipped)
                self.assertIn(fallback, original)
                self.assertIn(guard, shipped)
                for state, engine_text, owner_text, available in (
                        ("active input missing", shipped.replace(live, broken), original, False),
                        ("unused fallback missing", shipped, native_missing, True),
                        ("setter writes a local", shipped, local_only, True),
                        ("unselected override missing", shipped.replace(live, broken), local_only, True),
                        ("selected fallback missing", shipped, native_missing.replace(declaration, remaining), False),
                        ("owner defaults selected", shipped.replace(guard, guard.replace('"__main__"', '"other"')),
                         native_missing, False),
                        ("restored", shipped, original, True)):
                    with self.subTest(key=key, state=state):
                        engine.write_text(engine_text, encoding="utf-8")
                        owner.write_text(owner_text, encoding="utf-8")
                        facts = inspect_cli_registration(engine, key, handler)
                        self.assertEqual((facts["handler"], facts["dispatch"]), (available, available))

            provider = target / "release/quality.py"
            provider.unlink()
            quality = inspect_cli_registration(engine, "quality-tools", "cmd_quality_tools")
            self.assertFalse(quality["dispatch"])
            self.assertFalse(quality["handler"])
            shutil.copyfile(source / "release/quality.py", provider)
            registry_source = target / "registry.py"
            original_registry = registry_source.read_text(encoding="utf-8")
            for suffix, available in (("\nLOADER_WHITELIST = ()\n", False), ("", True)):
                registry_text = original_registry + suffix
                ast.parse(registry_text, filename=str(registry_source))
                registry_source.write_text(registry_text, encoding="utf-8")
                for key in ("quality-tools", "release-ledger", "release-projection"):
                    facts = inspect_cli_registration(engine, key, "cmd_" + key.replace("-", "_"))
                    self.assertEqual(facts["dispatch"], available)
                    self.assertTrue(facts["handler"])

    def test_foreign_checkout_wiring_reads_only_its_own_declarations(self):
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "verify_workflow.py"
            engine.write_text(
                "def cmd_status(args): pass\n"
                "def _build_cli_parser(): subparsers.add_parser('status')\n"
                "def main():\n"
                "    parser, _ = _build_cli_parser()\n"
                "    args = parser.parse_args()\n"
                "    return registry.load_handler(args.command or 'verify', parsed_args=True)(args)\n", encoding="utf-8")
            table = engine.with_name("registry.py")
            for source, expected in (
                    (None, False),
                    ("# ('status', 'verify_workflow.cmd_status')", False),
                    ("_COMMANDS: tuple = (", False),
                    ("_COMMANDS: tuple = (('status', 'verify_workflow.cmd_wrong'),)", False),
                    ("raise RuntimeError()\n_COMMANDS: tuple = (('status', 'verify_workflow.cmd_status'),)", True)):
                with self.subTest(source=source):
                    if source is not None:
                        table.write_text(source, encoding="utf-8")
                    facts = inspect_cli_registration(engine, "status", "cmd_status")
                    self.assertEqual(facts, {"main": True, "argparse": True,
                                             "handler": True, "dispatch": expected})

    def test_unused_table_and_unused_loader_do_not_register_a_command(self):
        import tempfile
        from cli_registration import inspect_cli_registration

        parser = "    subparsers.add_parser('status')\n    args = parser.parse_args()\n"
        unused = ("    decoy = {'status': cmd_status}\n",
                  "    unused = registry.load_handler('verify')\n",
                  "    unused = registry.load_handler(args.command or 'verify')\n")
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "verify_workflow.py"
            engine.with_name("registry.py").write_text(
                "_COMMANDS: tuple = (('status', 'verify_workflow.cmd_status'),)", encoding="utf-8")
            for line in unused:
                with self.subTest(line=line):
                    engine.write_text("def cmd_status(args): pass\ndef main():\n" +
                                      parser + line + "    return 7\n", encoding="utf-8")
                    facts = inspect_cli_registration(engine, "status", "cmd_status")
                    self.assertTrue(facts["argparse"])
                    self.assertFalse(facts["dispatch"])

    def test_foreign_family_must_be_called_on_the_returned_parser_group(self):
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "verify_workflow.py"
            engine.write_text(
                "def cmd_status(args): pass\n"
                "def _build_cli_parser(argv):\n"
                "    from workflow_cli import build_cli_parser\n"
                "    return build_cli_parser(argv)\n"
                "def main():\n"
                "    parser, _ = _build_cli_parser([])\n"
                "    args = parser.parse_args()\n"
                "    return registry.load_handler(args.command or 'verify', parsed_args=True)(args)\n",
                encoding="utf-8")
            engine.with_name("registry.py").write_text(
                "_COMMANDS: tuple = (('status', 'verify_workflow.cmd_status'),)", encoding="utf-8")
            family = engine.with_name("workflow_cli_checks.py")
            family.write_text("from pathlib import Path\nPath(__file__).with_suffix('.imported').touch()\n"
                              "def register_status(subparsers, argv):\n"
                              "    subparsers.add_parser('status')\n", encoding="utf-8")
            schema = engine.with_name("workflow_cli.py")

            def write_builder(call, extra_import=""):
                schema.write_text(
                    "import argparse\nimport workflow_cli_checks\n" + extra_import + "\n"
                    "def build_cli_parser(argv):\n"
                    "    parser = argparse.ArgumentParser()\n"
                    "    subparsers = parser.add_subparsers()\n"
                    f"    {call}\n    return parser, subparsers\n", encoding="utf-8")

            for call, expected in (
                    ("workflow_cli_checks.register_status(subparsers, argv)", True),
                    ("pass", False),
                    ("workflow_cli_checks.register_status(other, argv)", False),
                    ("workflow_cli_checks.register_status(subparsers)", False),
                    ("if False: workflow_cli_checks.register_status(subparsers, argv)", False),
                    ("return parser, subparsers\n    workflow_cli_checks.register_status(subparsers, argv)", False)):
                with self.subTest(call=call):
                    write_builder(call)
                    facts = inspect_cli_registration(engine, "status", "cmd_status")
                    self.assertEqual(facts, {"main": True, "argparse": expected,
                                             "handler": True, "dispatch": True})
            # Even without a call into it, a required sibling import must load.
            for statement, expected in (("import workflow_cli_operations", False),
                                        ("if False: import workflow_cli_operations", True)):
                write_builder("workflow_cli_checks.register_status(subparsers, argv)", statement)
                self.assertEqual(inspect_cli_registration(engine, "status", "cmd_status")["argparse"], expected)
            self.assertFalse(family.with_suffix(".imported").exists())

    def test_capability_adapter_follows_the_target_owners(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            engine = target / "verify_workflow.py"
            for module in ("verify_workflow", "capability_context", "status_cli"):
                shutil.copyfile(_INFRA_DIR / (module + ".py"), target / (module + ".py"))

            def has_handler():
                return inspect_cli_registration(engine, "capability-context", "cmd_capability_context")["handler"]

            self.assertTrue(has_handler())
            for module in ("capability_context", "status_cli"):
                with self.subTest(module=module):
                    owner = target / (module + ".py")
                    original = owner.read_bytes()
                    owner.unlink()
                    self.assertFalse(has_handler())
                    owner.write_text("# no exported implementation", encoding="utf-8")
                    self.assertFalse(has_handler())
                    owner.write_bytes(original)
                    self.assertTrue(has_handler())

    def test_capability_handler_uses_its_imported_name_and_forwards_its_arguments(self):
        import tempfile
        from cli_registration import inspect_cli_registration

        # Exercise the shipped wrappers in a foreign source-only installation.
        # A sibling deliberately raises if the observation imports that code.
        entry = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        lines = entry.splitlines(keepends=True)
        names = {"cmd_capability_context", "discover_capability_context", "check_capability_context"}
        original = "\n".join("".join(lines[n.lineno - 1:n.end_lineno]) for n in ast.parse(entry).body
                             if isinstance(n, ast.FunctionDef) and n.name in names)
        binding = "from status_cli import cmd_capability_context as read"
        delegate = binding + "\n    return read("
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "verify_workflow.py"
            for module in ("status_cli", "capability_context"):
                source = (_INFRA_DIR / (module + ".py")).read_text(encoding="utf-8")
                engine.with_name(module + ".py").write_text(
                    "raise AssertionError('observer imported a target module')\n" + source, encoding="utf-8")

            def check(source, expected):
                engine.write_text(source, encoding="utf-8")
                facts = inspect_cli_registration(engine, "capability-context", "cmd_capability_context")
                self.assertEqual(facts["handler"], expected)

            check(original, True)
            for old, new, expected in (
                    (binding, binding.replace("from status_cli", "from .status_cli"), False),
                    (binding, binding.replace("as read", "as report"), False),
                    (delegate, delegate.replace("read", "report"), True),
                    (delegate, "from status_cli import cmd_capability_context\n    return cmd_capability_context(", True),
                    (binding, "if False: " + binding, False),
                    (binding, "return\n    " + binding, False),
                    (binding, "from other_owner import cmd_capability_context as read", False),
                    (delegate, delegate.replace("read", "args"), False),
                    ("discover=discover_capability_context", "discover=check_capability_context", False),
                    ("plugin_root=ROOT,", "", False),
                    ("        args,", "        unknown_args,", False),
                    ("from capability_context import discover_capability_context as read",
                     "from .capability_context import discover_capability_context as read", False),
                    ("return validate(", "return disconnected(", False)):
                with self.subTest(old=old, new=new):
                    self.assertEqual(original.count(old), 1)
                    check(original.replace(old, new), expected)
            check(original, True)
            owner = engine.with_name("status_cli.py")
            source = owner.read_text(encoding="utf-8")
            for changed in (source.replace("def cmd_capability_context(args, *", "def cmd_capability_context(args, cfg, *"),
                            source + "\ncmd_capability_context = None\n"):
                with self.subTest(owner_change=changed[-40:]):
                    self.assertNotEqual(changed, source)
                    owner.write_text(changed, encoding="utf-8")
                    check(original, False)
            owner.write_text(source, encoding="utf-8")
            check(original, True)

    def test_early_command_requires_the_complete_shipped_schema(self):
        import shutil
        import tempfile
        from cli_registration import inspect_cli_registration

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in ("verify_workflow", "registry", "workflow_cli", "workflow_cli_checks",
                         "workflow_cli_operations", "status_cli", "capability_context"):
                shutil.copyfile(_INFRA_DIR / (name + ".py"), target / (name + ".py"))
            operations = target / "workflow_cli_operations.py"
            original = operations.read_text(encoding="utf-8")

            def assert_available(expected):
                facts = inspect_cli_registration(target / "verify_workflow.py",
                                                 "capability-context", "cmd_capability_context")
                self.assertEqual(facts, {"main": True, "handler": True,
                                         "argparse": expected, "dispatch": True})

            assert_available(True)
            operations.unlink()
            assert_available(False)
            operations.write_text(original, encoding="utf-8")
            assert_available(True)
            name = "register_authority_and_isolation"
            for label, change in (
                    ("missing definition", original.replace("def " + name + "(", "def retired_family(")),
                    ("required argument", original.replace("def " + name + "(subparsers):",
                                                            "def " + name + "(subparsers, extra):")),
                    ("positional-only argument", original.replace(
                        "def " + name + "(subparsers):", "def " + name + "(configuration, /, subparsers):")),
                    ("rebound name", original + "\n" + name + " = None\n")):
                with self.subTest(label=label):
                    self.assertNotEqual(change, original)
                    operations.write_text(change, encoding="utf-8")
                    assert_available(False)
            operations.write_text(original, encoding="utf-8")
            assert_available(True)

    def test_schema_witness_recognizes_only_its_supported_call_shapes(self):
        from cli_registration import _binds_schema_call

        def binds(signature, call, *, body="pass", prefix="", wrapper=False):
            definition = ast.parse(prefix + f"def registrar({signature}):\n    " + body).body[0]
            invocation = ast.parse(f"registrar({call})", mode="eval").body
            return _binds_schema_call(invocation, definition, wrapper=wrapper)

        self.assertTrue(binds("group, name, *, root", "group, root=root, name=name"))
        self.assertTrue(binds("argv=()", "", wrapper=True))
        self.assertTrue(binds("group", "group", body="def nested():\n        yield 1"))
        for signature, call in (
                ("configuration, /, group", "group"), ("group, /", "group"),
                ("group, *rest", "group"), ("group, **kw", "group"),
                ("group=()", "group"), ("group, *, root=None", "group, root=root"),
                ("group, *, root", "group"), ("group, *, root", "group, root=root, extra=extra"),
                ("group", "group, group=group"), ("group", "*items"), ("group", "**kwargs")):
            with self.subTest(signature=signature, call=call):
                self.assertFalse(binds(signature, call))
        self.assertFalse(binds("group", "group", prefix="@decorate\n"))
        self.assertFalse(binds("group", "group", prefix="async "))
        self.assertFalse(binds("group", "group", body="if False:\n        yield 1"))
        self.assertFalse(binds("group", "group", body="yield from ()"))

    def test_cli_builder_reads_current_engine_root_and_choices(self):
        from unittest.mock import patch
        import verify_workflow as vw

        with patch.multiple(vw, ROOT=Path("fixture"), AGENT_RUNTIME_E2E_PLATFORMS=("runtime",),
                            DETERMINISTIC_SCAFFOLD_TYPES=("scaffold",), QUALITY_BUDGET_DIMENSIONS=("budget",)):
            parser, commands = vw._build_cli_parser()
        runtime = parser.parse_args(["agent-runtime-e2e", "--agent", "runtime"])
        self.assertEqual(runtime.target, str(Path("fixture/project/e2e-test-project")))
        self.assertEqual(runtime.agent, ["runtime"])
        scaffold = parser.parse_args(["generate-deterministic-scaffold", "--type", "scaffold"])
        self.assertEqual(scaffold.type, "scaffold")
        dimension = commands.choices["execution-packet"]._option_string_actions["--quality-dimension"]
        self.assertEqual(dimension.choices, ("budget",))

    def test_mutated_legacy_dispatch_table_is_not_proof_of_registration(self):
        import tempfile
        from cli_registration import inspect_cli_registration

        source = ("def cmd_status(args): pass\ndef main():\n"
                  "    subparsers.add_parser('status')\n"
                  "    args = parser.parse_args()\n"
                  "    commands = {'status': cmd_status}\n")
        final_call = "    cmd = args.command or 'verify'\n    return commands[cmd](args)\n"
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "verify_workflow.py"
            for mutation in ("", "    commands['status'] = cmd_wrong\n",
                             "    other = commands\n    other.clear()\n"):
                with self.subTest(mutation=mutation):
                    engine.write_text(source + mutation + final_call, encoding="utf-8")
                    facts = inspect_cli_registration(engine, "status", "cmd_status")
                    self.assertEqual(facts["dispatch"], not mutation)

    def test_declared_keys_resolve_to_callables(self):
        modules = {}
        for spec in reg.COMMAND_SPECS:
            handler = reg.load_handler(spec.key)
            self.assertTrue(callable(handler), spec.key)
            modules.setdefault(reg.loader_module(spec.handler), []).append(
                spec.key)
        self.assertGreaterEqual(len(modules), 3)


# ── ① check registry ──────────────────────────────────────────


class CheckRegistryTests(unittest.TestCase):

    def test_declares_the_frozen_segment_count(self):
        self.assertEqual(len(reg.CHECK_SPECS), _frozen_faces()["check_segments"]["count"])
        self.assertEqual(len(reg.segment_ids()), _frozen_faces()["check_segments"]["count"])
        self.assertEqual(len(set(reg.segment_ids())), _frozen_faces()["check_segments"]["count"])

    def test_segment_set_matches_the_frozen_snapshot(self):
        frozen = tuple(_frozen_faces()["check_segments"]["ids"])
        self.assertEqual(set(reg.segment_ids()), set(frozen))

    def test_segment_set_matches_the_quickscan_registry(self):
        self.assertEqual(set(reg.segment_ids()), set(qr.registry_ids()))

    def test_check_ids_use_the_frozen_stable_form(self):
        for spec in reg.CHECK_SPECS:
            self.assertTrue(spec.check_id.startswith("check-"))
            self.assertEqual(reg.segment_of(spec.check_id),
                             spec.check_id[len("check-"):])
            self.assertEqual(reg.check_id_of(reg.segment_of(spec.check_id)),
                             spec.check_id)
        self.assertEqual(reg.check_spec("28p").check_id, "check-28p")
        self.assertEqual(reg.check_spec("check-28p"), reg.check_spec("28p"))

    def test_domain_input_deps_and_modes_are_faithful_to_feat025(self):
        """FEAT-025 owns the input/policy facts — the registry must not fork."""
        for spec in reg.CHECK_SPECS:
            row = qr.segment(reg.segment_of(spec.check_id))
            self.assertEqual(spec.domain, row.domain)
            self.assertEqual(tuple(spec.input_deps), tuple(row.input_deps))
            self.assertIn("full", spec.modes)
            self.assertEqual("quick" in spec.modes, "quick" in row.modes)

    def test_severity_floor_follows_the_engine_gate_face(self):
        facts = _segment_facts()
        advisory = set(reg.ADVISORY_SEGMENTS)
        self.assertEqual(advisory, {segment for segment, slot in facts.items()
                                    if not slot["all_issues"]})
        for spec in reg.CHECK_SPECS:
            segment = reg.segment_of(spec.check_id)
            expected = ("WARN" if segment in advisory else "BLOCKING")
            self.assertEqual(spec.severity_floor, expected, segment)

    def test_loaders_are_the_segment_entry_and_stay_in_the_whitelist(self):
        facts = _segment_facts()
        for spec in reg.CHECK_SPECS:
            segment = reg.segment_of(spec.check_id)
            module = reg.loader_module(spec.loader)
            attr = reg.loader_attr(spec.loader)
            self.assertIn(module, reg.LOADER_WHITELIST, segment)
            self.assertIn(attr, facts[segment]["calls"],
                          f"{segment}: {attr} is not called in its section")
            via = reg.DELEGATED_LOADERS.get(spec.check_id, spec.loader)
            target = getattr(importlib.import_module(reg.loader_module(via)), reg.loader_attr(via))
            self.assertIn(target, facts[segment]["targets"], f"{segment}: checker owner changed")

    def test_swapping_a_checker_changes_the_observed_loader(self):
        import verify_workflow as engine

        with patch.object(engine, "check_evidence_completeness", engine.check_risk_staleness):
            calls = _segment_facts()["1"]["calls"]
        self.assertNotIn("check_evidence_completeness", calls)
        self.assertIn("check_risk_staleness", calls)

    def test_same_named_dsh_emitters_have_distinct_owners(self):
        import dsh_compat
        from checks import dsh_boundary

        original = dsh_compat.emit_check_section
        with patch.object(dsh_compat, "emit_check_section", dsh_boundary.emit_check_section):
            targets = _segment_facts()["28v"]["targets"]
        self.assertNotIn(original, targets)
        self.assertIn(dsh_boundary.emit_check_section, targets)

    def test_advisory_errors_are_rendered_without_incrementing_the_total(self):
        from full_check_runner import run_full_checks
        from health_product_sections import section_28p_duplicate_code

        def reports():
            yield section_28p_duplicate_code(lambda: True, lambda: {
                "findings": [{"severity": "ERROR", "check": "dup"}],
                "summary": {"errors": 1, "warnings": 0},
            }, self.fail)
            yield 2

        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_full_checks(reports()), 2)
        self.assertIn("1 ERROR, 0 WARN (advisory)", output.getvalue())

    def test_full_profile_stops_at_the_first_checker_error(self):
        import verify_workflow as engine

        with patch.object(engine, "check_evidence_completeness", side_effect=LookupError("first")), \
             patch.object(engine, "check_risk_staleness") as later, redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(LookupError, "first"):
                engine._run_full_engine_checks(SimpleNamespace(product_gates=True))
        later.assert_not_called()
        self.assertIn("Check 1: Evidence Completeness", out.getvalue())
        self.assertNotIn("Check 2:", out.getvalue())
        self.assertNotIn("Governance Health Summary", out.getvalue())

    def test_domain_hosted_loaders_match_the_declaring_module(self):
        definitions = _engine_modules()
        facts = _segment_facts()
        for spec in reg.CHECK_SPECS:
            segment = reg.segment_of(spec.check_id)
            module = reg.loader_module(spec.loader)
            attr = reg.loader_attr(spec.loader)
            self.assertIn(segment, facts)
            self.assertIn(module, definitions.get(attr, set()),
                          f"{segment}: {attr} is not defined in {module}")

    def test_engine_hosted_face_is_disclosed(self):
        hosted = reg.legacy_engine_hosted()
        self.assertEqual(len(hosted),
                         len([spec for spec in reg.CHECK_SPECS
                              if reg.loader_module(spec.loader)
                              == reg.ENGINE_MODULE]))
        self.assertLess(len(hosted), _frozen_faces()["check_segments"]["count"])
        for check_id in hosted:
            self.assertTrue(check_id.startswith("check-"))

    def test_declared_check_loaders_resolve_to_callables(self):
        for spec in reg.CHECK_SPECS:
            self.assertTrue(callable(reg.load_check(spec.check_id)),
                            spec.check_id)

    def test_segment_ids_use_the_frozen_stable_form(self):
        for segment in reg.segment_ids():
            self.assertRegex(segment, r"^[0-9]+[a-z]?$")

    def test_declared_order_follows_the_numeric_segment_caliber(self):
        """``10`` sorts after ``9`` (numeric, not lexicographic) and an
        unexpected id form sorts last instead of crashing — the ordering is
        the registry's determinism contract for ``CHECK_SPECS``."""
        self.assertLess(reg._segment_sort_key("9"),
                        reg._segment_sort_key("10"))
        self.assertLess(reg._segment_sort_key("28"),
                        reg._segment_sort_key("28b"))
        self.assertGreater(reg._segment_sort_key("zzz"),
                           reg._segment_sort_key("40"))
        ordered = [reg._segment_sort_key(segment)
                   for segment in reg.segment_ids()]
        self.assertEqual(ordered, sorted(ordered))

    def test_check_id_and_segment_forms_fail_closed(self):
        for bad in (None, "", "28p", "check-999", "CHECK-28p"):
            with self.assertRaises(reg.UnknownCheckID) as ctx:
                reg.segment_of(bad)
            self.assertIn(repr(bad), str(ctx.exception))
        with self.assertRaises(reg.UnknownCheckID):
            reg.check_id_of(None)

    def test_check_id_of_refuses_anything_but_a_bare_segment(self):
        """F-6: the same fail-closed caliber ``segment_of`` applies.

        Prefixing an arbitrary string would mint a "CheckID" no consumer could
        resolve (``""`` → ``check-``), against the module's own
        "fail-closed, never guessed" discipline.
        """
        for bad in (None, "", "   ", "28p!", "nosuch", "check-28p", "28pa", 28):
            with self.assertRaises(reg.UnknownCheckID) as ctx:
                reg.check_id_of(bad)
            self.assertIn(repr(bad), str(ctx.exception))
        for segment in reg.segment_ids():  # negative control: all 70 resolve
            self.assertEqual(reg.check_id_of(segment), f"check-{segment}")


class DelegatedLoaderTests(unittest.TestCase):
    """Segments whose implementation is reached through an engine wrapper."""

    def _engine_import_aliases(self):
        tree = ast.parse(_engine_source())
        aliases = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    aliases[bound] = f"{node.module}.{alias.name}"
        return aliases

    def test_disclosure_covers_the_delegating_segments(self):
        self.assertTrue(reg.DELEGATED_LOADERS)
        for check_id, wrapper in reg.DELEGATED_LOADERS.items():
            self.assertIn(check_id, reg.check_ids())
            self.assertEqual(reg.loader_module(wrapper), reg.ENGINE_MODULE)
            self.assertNotEqual(reg.loader_module(reg.check_spec(check_id).loader),
                                reg.ENGINE_MODULE)

    def test_engine_wrapper_is_a_single_delegation_to_the_declared_loader(self):
        aliases = self._engine_import_aliases()
        tree = ast.parse(_engine_source())
        for check_id, wrapper in reg.DELEGATED_LOADERS.items():
            attr = reg.loader_attr(wrapper)
            function = next(node for node in ast.walk(tree)
                            if isinstance(node, ast.FunctionDef)
                            and node.name == attr)
            body = [node for node in function.body
                    if not isinstance(node, ast.Expr)]
            expected = reg.check_spec(check_id).loader
            if len(body) == 2:
                binding, result = body
                self.assertIsInstance(binding, ast.ImportFrom)
                self.assertEqual(binding.level, 0)
                self.assertEqual(len(binding.names), 1)
                imported = binding.names[0]
                self.assertEqual(f"{binding.module}.{imported.name}", expected)
                self.assertIsInstance(result, ast.Return)
                self.assertIsInstance(result.value, ast.Call)
                self.assertIsInstance(result.value.func, ast.Name)
                self.assertEqual(result.value.func.id, imported.asname or imported.name)
            else:
                self.assertEqual(len(body), 1, f"{attr} is no longer a wrapper")
                self.assertIsInstance(body[0], ast.Return)
                call = body[0].value
                self.assertIsInstance(call, ast.Call)
                self.assertIsInstance(call.func, ast.Attribute)
                self.assertEqual(call.func.attr, reg.loader_attr(expected))
                self.assertEqual(aliases.get(call.func.value.id), reg.loader_module(expected))


# ── ③ loader whitelist / assembly path ──────────────────────────────────────


class LoaderWhitelistTests(unittest.TestCase):
    """Acceptance ③ — declared keys resolve; undeclared keys fail closed."""

    def test_whitelist_is_a_closed_declaration(self):
        self.assertTrue(reg.LOADER_WHITELIST)
        self.assertIn(reg.ENGINE_MODULE, reg.LOADER_WHITELIST)
        for module in reg.LOADER_WHITELIST:
            self.assertNotIn("/", module)
            self.assertNotIn("\\", module)
            self.assertNotIn(".py", module)
            for part in module.split("."):
                self.assertTrue(part.isidentifier(), module)
        # The bound is the "no package walk, no discovery" red line — it is a
        # magnitude guard, not an exact count: FEAT-039 added the 21st leaf
        # (``checks.injection_budget``) and the declaration is still hand-kept.
        self.assertLess(len(reg.LOADER_WHITELIST), 32)

    def test_declared_loader_resolves(self):
        handler = reg.resolve_loader("archguard_ratchet.cmd_archguard_ratchet")
        self.assertTrue(callable(handler))
        self.assertEqual(handler.__name__, "cmd_archguard_ratchet")

    def test_undeclared_module_fails_closed(self):
        for path in ("os.system", "subprocess.run", "pkghack.run"):
            with self.assertRaises(reg.LoaderWhitelistViolation) as ctx:
                reg.resolve_loader(path)
            message = str(ctx.exception)
            self.assertIn("whitelist", message)
            self.assertIn(path.rsplit(".", 1)[0], message)

    def test_malformed_loader_paths_fail_closed(self):
        for path in ("", "nodot", "a/b.c", "C:\\x.py", "checks.ci_domain.py"):
            with self.assertRaises(reg.RegistryError):
                reg.resolve_loader(path)

    def test_missing_attribute_fails_closed(self):
        with self.assertRaises(reg.LoaderResolutionError) as ctx:
            reg.resolve_loader("archguard_ratchet.no_such_handler")
        message = str(ctx.exception)
        self.assertIn("no_such_handler", message)
        self.assertIn("archguard_ratchet", message)

    def test_import_failure_of_a_whitelisted_module_fails_closed(self):
        """A whitelisted module that cannot import is refused with context.

        ``sys.modules[name] = None`` blocks the import with a real
        ``ImportError`` (CPython's documented halt mechanism) — no test
        double is needed to reach the branch.
        """
        probe = _probe(
            "import registry\n"
            "sys.modules['archguard_ratchet'] = None\n"
            "try:\n"
            "    registry.assemble('archguard-ratchet')\n"
            "except Exception as exc:\n"
            "    payload = {'type': type(exc).__name__, 'message': str(exc),\n"
            "               'cause': type(exc.__cause__).__name__}\n"
            "else:\n"
            "    payload = {'type': None}\n"
            "print(json.dumps(payload))\n")
        self.assertEqual(probe["type"], "LoaderResolutionError")
        self.assertIn("archguard_ratchet", probe["message"])
        self.assertIn("failed to import", probe["message"])
        self.assertEqual(probe["cause"], "ModuleNotFoundError")

    def test_non_callable_entry_fails_closed(self):
        """A real non-callable attribute (``checks.manifest.sys`` is a
        module) is refused instead of being handed back as a handler."""
        with self.assertRaises(reg.LoaderResolutionError) as ctx:
            reg.resolve_loader("checks.manifest.sys")
        self.assertIn("not a callable entry", str(ctx.exception))

    def test_non_identifier_parts_fail_closed(self):
        for path in ("checks.1bad.entry", "checks.manifest.1bad"):
            with self.assertRaises(reg.LoaderResolutionError) as ctx:
                reg.resolve_loader(path)
            self.assertIn("non-identifier", str(ctx.exception))

    def test_handler_path_is_looked_up_not_guessed(self):
        for key in ("status", "check-governance", "archguard-ratchet"):
            self.assertEqual(reg.handler_path(key),
                             reg.command_spec(key).handler)

    def test_command_spec_construction_is_fail_closed(self):
        with self.assertRaises(reg.RegistryError):
            reg.CommandSpec(key="", handler="verify_workflow.cmd_status")
        with self.assertRaises(reg.RegistryError):
            reg.CommandSpec(key="status",
                            handler=" verify_workflow.cmd_status ")
        with self.assertRaises(reg.LoaderWhitelistViolation):
            reg.CommandSpec(key="status", handler="os.system")

    def test_unknown_command_key_fails_closed_with_an_explicit_message(self):
        for key in ("", "no-such-command", "STATUS"):
            with self.assertRaises(reg.UnknownCommandKey) as ctx:
                reg.command_spec(key)
            self.assertIn(repr(key), str(ctx.exception))
        with self.assertRaises(reg.UnknownCommandKey):
            reg.assemble("no-such-command")

    def test_unknown_check_id_fails_closed_with_an_explicit_message(self):
        with self.assertRaises(reg.UnknownCheckID) as ctx:
            reg.check_spec("check-999")
        self.assertIn("check-999", str(ctx.exception))
        with self.assertRaises(reg.UnknownCheckID):
            reg.load_check("check-999")

    def test_error_types_share_one_chained_base(self):
        for error in (reg.UnknownCommandKey, reg.UnknownCheckID,
                      reg.LoaderWhitelistViolation, reg.LoaderResolutionError):
            self.assertTrue(issubclass(error, reg.RegistryError))
        self.assertTrue(issubclass(reg.RegistryError, ValueError))

    def test_registry_mechanism_scan_is_not_used(self):
        tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, FORBIDDEN_REGISTRY_NAMES)
            elif isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, FORBIDDEN_REGISTRY_ATTRS)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, FORBIDDEN_REGISTRY_NAMES)


class CompositionRootTests(unittest.TestCase):
    """L6 组合根雏形 — per-command assembly over the declared registry."""

    def test_assemble_returns_the_declared_spec_and_handler(self):
        assembly = reg.assemble("archguard-ratchet")
        self.assertEqual(assembly.key, "archguard-ratchet")
        self.assertEqual(assembly.command, reg.command_spec("archguard-ratchet"))
        self.assertTrue(callable(assembly.handler))
        self.assertEqual(assembly.handler.__name__, "cmd_archguard_ratchet")
        self.assertEqual(assembly.checks, ())

    def test_assemble_selects_checks_for_a_mode(self):
        assembly = reg.assemble("check-governance", mode="quick")
        quick = reg.select_checks(mode="quick")
        self.assertEqual(assembly.checks, quick)
        self.assertTrue(quick)
        for spec in quick:
            self.assertIn("quick", spec.modes)
        self.assertEqual(reg.select_checks(mode="full"), reg.CHECK_SPECS)

    def test_assemble_selects_checks_for_a_domain(self):
        domain = reg.select_checks(domain="review")
        self.assertTrue(domain)
        for spec in domain:
            self.assertEqual(spec.domain, "review")
        self.assertLess(len(domain), len(reg.CHECK_SPECS))

    def test_assemble_accepts_a_domain_mode_selector(self):
        """``domain:<name>`` is the §3.6 selector form for a whole domain."""
        selected = reg.select_checks(mode="domain:review")
        self.assertEqual(selected, reg.select_checks(domain="review"))
        self.assertTrue(selected)
        assembly = reg.assemble("check-governance", mode="domain:review")
        self.assertEqual(assembly.checks, selected)

    def test_unknown_selection_token_fails_closed(self):
        for mode in ("", "fast", "domain:", "domain:nosuch"):
            with self.assertRaises(reg.RegistryError):
                reg.select_checks(mode=mode)
        with self.assertRaises(reg.RegistryError):
            reg.select_checks(mode="full", domain="")
        with self.assertRaises(reg.RegistryError):
            reg.select_checks(domain="nosuch")
        with self.assertRaises(reg.RegistryError):
            reg.select_checks()


# ── ① R5 registration integrity ─────────────────────────────────────────────


class RegistrationIntegrityTests(unittest.TestCase):

    def test_negative_control_missing_and_extra_keys(self):
        keys = list(reg.command_keys())
        report = reg.verify_registration(
            observed_cli_keys=keys[:-1],
            observed_segment_ids=reg.segment_ids(),
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.missing_keys, (keys[-1],))
        self.assertEqual(report.extra_keys, ())
        report = reg.verify_registration(
            observed_cli_keys=keys + ["ghost-key"],
            observed_segment_ids=reg.segment_ids(),
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.extra_keys, ("ghost-key",))

    def test_negative_control_missing_and_extra_segments(self):
        segments = list(reg.segment_ids())
        report = reg.verify_registration(
            observed_cli_keys=reg.command_keys(),
            observed_segment_ids=segments[:-1],
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.missing_segments, (segments[-1],))
        report = reg.verify_registration(
            observed_cli_keys=reg.command_keys(),
            observed_segment_ids=segments + ["999"],
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.extra_segments, ("999",))

    def test_report_renders_every_face(self):
        report = reg.verify_registration()
        lines = report.lines()
        self.assertTrue(lines)
        joined = "\n".join(lines)
        # Derived from the frozen faces rather than re-spelled: the assertion
        # is "both faces are rendered", not a hard-coded caliber that has to
        # be edited alongside every deliberate contract change.
        self.assertIn(str(_frozen_faces()["cli_dispatch"]["key_count"]), joined)
        self.assertIn(str(_frozen_faces()["check_segments"]["count"]), joined)

    def test_failed_report_discloses_drift_on_both_axes(self):
        """A registered face that drifted is disclosed, never a silent FAIL."""
        keys = list(reg.command_keys())
        segments = list(reg.segment_ids())
        report = reg.verify_registration(
            observed_cli_keys=keys[:-1] + ["ghost-key"],
            observed_segment_ids=segments[:-1] + ["999"])
        self.assertFalse(report.ok)
        joined = "\n".join(report.lines())
        self.assertIn("FAIL", joined)
        self.assertIn("registration drift", joined)
        self.assertIn("declaration is stale", joined)
        self.assertIn(keys[-1], joined)
        self.assertIn("ghost-key", joined)
        self.assertIn("'999'", joined)

    def test_single_axis_observation_defaults_the_other_face(self):
        report = reg.verify_registration(
            observed_cli_keys=list(reg.command_keys()))
        self.assertEqual(report.source, reg.INJECTED_SOURCE)
        self.assertTrue(report.ok, "\n".join(report.lines()))
        self.assertEqual(report.observed_segments, reg.segment_ids())
        mirrored = reg.verify_registration(
            observed_segment_ids=list(reg.segment_ids()))
        self.assertTrue(mirrored.ok, "\n".join(mirrored.lines()))
        self.assertEqual(mirrored.observed_keys, reg.command_keys())

    def test_a_defaulted_axis_is_disclosed_as_unobserved(self):
        """F-2: ``ok`` can be green with an axis that was never measured.

        The defaulted face is the registry's own declaration, so that axis is
        a self-comparison; the report names it instead of letting a single
        boolean read as a two-axis measurement.
        """
        report = reg.verify_registration(
            observed_cli_keys=list(reg.command_keys()))
        self.assertTrue(report.ok, "\n".join(report.lines()))
        self.assertEqual(report.observed_axes, (reg.CLI_KEYS_AXIS,))
        self.assertEqual(report.unobserved_axes, (reg.SEGMENTS_AXIS,))
        rendered = "\n".join(report.lines())
        self.assertIn(f"[unobserved] {reg.SEGMENTS_AXIS}", rendered)
        self.assertNotIn(f"[unobserved] {reg.CLI_KEYS_AXIS}", rendered)
        mirrored = reg.verify_registration(
            observed_segment_ids=list(reg.segment_ids()))
        self.assertEqual(mirrored.unobserved_axes, (reg.CLI_KEYS_AXIS,))
        self.assertIn(f"[unobserved] {reg.CLI_KEYS_AXIS}",
                      "\n".join(mirrored.lines()))
        dual = reg.verify_registration(
            observed_cli_keys=list(reg.command_keys()),
            observed_segment_ids=list(reg.segment_ids()))
        self.assertEqual(dual.observed_axes,
                         (reg.CLI_KEYS_AXIS, reg.SEGMENTS_AXIS))
        self.assertEqual(dual.unobserved_axes, ())
        self.assertNotIn("unobserved", "\n".join(dual.lines()))

    def test_missing_provider_fails_closed_and_injection_still_works(self):
        """With the FEAT-020 extractors unavailable, the live source refuses
        and names the provider; an explicitly injected face still judges."""
        probe = _probe(
            "import registry\n"
            "sys.modules['contract_matrix'] = None\n"
            "outcome = {}\n"
            "try:\n"
            "    registry.verify_registration()\n"
            "except Exception as exc:\n"
            "    outcome['type'] = type(exc).__name__\n"
            "    outcome['message'] = str(exc)\n"
            "injected = registry.verify_registration(\n"
            "    observed_cli_keys=registry.command_keys(),\n"
            "    observed_segment_ids=registry.segment_ids())\n"
            "outcome['injected_ok'] = injected.ok\n"
            "print(json.dumps(outcome))\n")
        self.assertEqual(probe["type"], "RegistryError")
        self.assertIn("unavailable", probe["message"])
        self.assertIn("contract_matrix", probe["message"])
        self.assertTrue(probe["injected_ok"])

    def test_matches_the_frozen_snapshot_face(self):
        faces = _frozen_faces()
        report = reg.verify_registration(
            observed_cli_keys=faces["cli_dispatch"]["keys"],
            observed_segment_ids=faces["check_segments"]["ids"],
            source="frozen-snapshot",
        )
        self.assertTrue(report.ok, "\n".join(report.lines()))
        self.assertEqual(report.source, "frozen-snapshot")
        self.assertEqual(report.observed_axes,
                         (reg.CLI_KEYS_AXIS, reg.SEGMENTS_AXIS))
        self.assertEqual(report.unobserved_axes, ())
        self.assertNotIn("unobserved", "\n".join(report.lines()))

    def test_the_frozen_snapshot_path_never_imports_the_engine(self):
        """F-1: the caliber a frozen-snapshot caller wants is engine-free.

        Injecting both faces must not reach the live provider: the whole point
        of the frozen comparison is a cheap, engine-free pass.
        """
        faces = _frozen_faces()
        probe = _probe(
            "import registry\n"
            f"keys = {faces['cli_dispatch']['keys']!r}\n"
            f"ids = {faces['check_segments']['ids']!r}\n"
            "report = registry.verify_registration(\n"
            "    observed_cli_keys=keys, observed_segment_ids=ids,\n"
            "    source='frozen-snapshot')\n"
            "print(json.dumps({\n"
            "    'ok': report.ok,\n"
            "    'source': report.source,\n"
            "    'axes': list(report.observed_axes),\n"
            "    'provider': 'contract_matrix' in sys.modules,\n"
            "    'engine': 'verify_workflow' in sys.modules}))\n")
        self.assertTrue(probe["ok"])
        self.assertEqual(probe["source"], "frozen-snapshot")
        self.assertEqual(probe["axes"], [reg.CLI_KEYS_AXIS, reg.SEGMENTS_AXIS])
        self.assertFalse(probe["provider"], "the live provider was imported")
        self.assertFalse(probe["engine"], "the engine was imported")

    def test_provenance_cannot_be_asserted_over_an_injected_face(self):
        """F-1: labelling an injected observation ``live-engine`` is refused."""
        with self.assertRaises(reg.RegistryError) as ctx:
            reg.verify_registration(
                observed_cli_keys=list(reg.command_keys()),
                observed_segment_ids=list(reg.segment_ids()),
                source=reg.LIVE_SOURCE)
        message = str(ctx.exception)
        self.assertIn(reg.LIVE_SOURCE, message)
        self.assertIn("contradict", message)

    def test_a_contradicting_label_is_refused_before_the_provider_loads(self):
        """F-1: no injected face + ``source='frozen-snapshot'`` used to run the
        *live* branch while keeping the frozen label. It is now refused, and
        refused before ``_live_faces()`` imports the engine."""
        probe = _probe(
            "import registry\n"
            "outcome = {}\n"
            "try:\n"
            "    registry.verify_registration(source='frozen-snapshot')\n"
            "except Exception as exc:\n"
            "    outcome['type'] = type(exc).__name__\n"
            "    outcome['message'] = str(exc)\n"
            "else:\n"
            "    outcome['type'] = None\n"
            "outcome['provider'] = 'contract_matrix' in sys.modules\n"
            "outcome['engine'] = 'verify_workflow' in sys.modules\n"
            "print(json.dumps(outcome))\n")
        self.assertEqual(probe["type"], "RegistryError")
        self.assertIn("frozen-snapshot", probe["message"])
        self.assertFalse(probe["provider"], "the live provider was imported")
        self.assertFalse(probe["engine"], "the engine was imported")

    def test_matches_the_live_engine_face(self):
        """Default provider consumes the FEAT-020 extractors (lazy import)."""
        report = reg.verify_registration()
        self.assertEqual(report.source, "live-engine")
        self.assertTrue(report.ok, "\n".join(report.lines()))
        self.assertEqual(report.observed_axes,
                         (reg.CLI_KEYS_AXIS, reg.SEGMENTS_AXIS))
        self.assertEqual(len(report.declared_keys), _frozen_faces()["cli_dispatch"]["key_count"])
        self.assertEqual(len(report.declared_segments), _frozen_faces()["check_segments"]["count"])
        self.assertEqual(len(report.observed_keys), _frozen_faces()["cli_dispatch"]["key_count"])
        self.assertEqual(len(report.observed_segments), _frozen_faces()["check_segments"]["count"])

    def test_an_explicit_live_label_on_the_live_branch_is_accepted(self):
        """F-1 negative control: the honest label is not refused."""
        report = reg.verify_registration(source=reg.LIVE_SOURCE)
        self.assertEqual(report.source, reg.LIVE_SOURCE)
        self.assertTrue(report.ok, "\n".join(report.lines()))


# ── ② startup import set ────────────────────────────────────────────────────


class StartupImportTests(unittest.TestCase):
    """Acceptance ② — registry load and per-command load add no startup mass."""

    def test_public_bootstrap_resolves_once_and_loads_only_its_handler(self):
        from textwrap import dedent

        result = _probe(dedent(f"""
            import io
            import runpy
            from contextlib import ExitStack, redirect_stdout
            from unittest.mock import patch
            import registry, resolve_entry

            engine = {str(_INFRA_DIR / 'verify_workflow.py')!r}
            cases = []
            for options in ([], ['--project-root', '.']):
                with ExitStack() as scope:
                    argv = [engine, *options, 'governance-bootstrap', '--budget-ms=0']
                    scope.enter_context(patch.object(sys, 'argv', argv))
                    def count(module, name):
                        return scope.enter_context(patch.object(module, name, wraps=getattr(module, name)))
                    explicit = count(resolve_entry, 'validate_project_root')
                    cwd = count(resolve_entry, 'resolve_host_root')
                    resolve = count(resolve_entry, 'resolve')
                    load = count(registry, 'load_handler')
                    out = scope.enter_context(redirect_stdout(io.StringIO()))
                    try:
                        runpy.run_path(engine, run_name='__main__')
                    except SystemExit as stop:
                        assert stop.code in (None, 0), stop.code
                    face = json.loads(out.getvalue())['resolve']
                    cases.append([explicit.call_count + cwd.call_count, resolve.call_count,
                                  [call.args[0] for call in load.call_args_list], face['resolved_root_ok']])
            unrelated = {{'verify_workflow', 'governance_store', 'execution_isolation'}} & sys.modules.keys()
            print(json.dumps([cases, sorted(unrelated)]))
        """))
        self.assertEqual(result, [[[1, 1, ["governance-bootstrap"], True]] * 2, []])

    def test_engine_baseline_is_an_executable_portable_budget(self):
        """F-4: enforce the frozen R6 ceiling with an executable caliber.

        ``core/architecture-baseline.json`` labels its r6 block with the
        shorthand ``python -I -B -c 'import verify_workflow' (isolated)``,
        which cannot run as written: ``-I`` implies ``-P``, so the cwd never
        enters ``sys.path`` and the import dies with ``ModuleNotFoundError``.
        The executable caliber is the one both producers require
        (``perf_protocol.probe_sys_modules(infra_dir)`` /
        ``archguard_ratchet.measure_cold_import(infra_dir)``): the infra dir on
        ``sys.path`` first. OS/interpreter standard-library imports vary, so
        the recorded count is a ceiling, not an exact portable population.
        The label string itself is baseline-owned — correcting
        it is registered on the archguard/baseline side, not edited here.
        """
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        budget = baseline["r6_startup_budget"]
        self.assertLessEqual(budget["import_count"], FROZEN_ENGINE_IMPORT_COUNT)
        self.assertIn("import verify_workflow", budget["probe"])
        face = _engine_startup_face()
        self.assertEqual(face["count"], len(set(face["modules"])))
        self.assertIn("verify_workflow", face["modules"])
        self.assertLessEqual(face["count"], budget["import_count"],
                             "cold startup exceeded the frozen R6 budget")

    def test_importing_the_registry_pulls_no_engine_and_no_domain(self):
        probe = _probe(
            "import registry\n"
            "mods = sorted(m for m in sys.modules if not m.startswith('_'))\n"
            "print(json.dumps({'count': len(mods), 'modules': mods}))\n")
        modules = probe["modules"]
        self.assertNotIn("verify_workflow", modules)
        self.assertNotIn("checks", modules)
        self.assertFalse([m for m in modules
                          if m.startswith(("checks.", "release.", "loop_"))],
                         modules)
        self.assertLess(probe["count"], FROZEN_ENGINE_IMPORT_COUNT)
        for allowed in ("registry", "contracts", "quickscan_registry"):
            self.assertIn(allowed, modules)

    def test_assembling_a_light_command_loads_only_its_module(self):
        probe = _probe(
            "import registry\n"
            "handler = registry.assemble('archguard-ratchet').handler\n"
            "print(json.dumps({'engine': 'verify_workflow' in sys.modules,\n"
            "                  'callable': callable(handler),\n"
            "                  'module': handler.__module__}))\n")
        self.assertFalse(probe["engine"])
        self.assertTrue(probe["callable"])
        self.assertEqual(probe["module"], "archguard_ratchet")

    def test_loading_a_domain_check_does_not_pull_the_engine(self):
        probe = _probe(
            "import registry\n"
            "handler = registry.load_check('check-1')\n"
            "print(json.dumps({'engine': 'verify_workflow' in sys.modules,\n"
            "                  'callable': callable(handler),\n"
            "                  'module': handler.__module__}))\n")
        self.assertFalse(probe["engine"])
        self.assertTrue(probe["callable"])
        self.assertEqual(probe["module"], "checks.evidence_domain")

    def test_parser_defaults_cannot_override_registered_handlers(self):
        from unittest.mock import Mock, patch
        import verify_workflow as vw

        parser, commands = vw._build_cli_parser()
        unrelated = Mock()
        commands.choices["status"].set_defaults(_cli_handler=unrelated)
        with patch.object(vw, "_build_cli_parser", return_value=(parser, commands)), \
             patch.object(reg, "load_handler") as load:
            vw.main(["status"])
        load.assert_called_once_with("status", parsed_args=True)
        load.return_value.assert_called_once()
        unrelated.assert_not_called()

    def test_unrelated_cli_help_leaves_the_doctor_implementation_unloaded(self):
        loaded = _probe(
            "from contextlib import redirect_stdout\n"
            "from io import StringIO\n"
            "import verify_workflow as vw\n"
            "try:\n"
            "    with redirect_stdout(StringIO()): vw.main(['status', '--help'])\n"
            "except SystemExit as stop:\n"
            "    assert stop.code == 0\n"
            "print(json.dumps('dsh_doctor' in sys.modules))\n")
        self.assertFalse(loaded)

    def test_cli_resolves_only_the_selected_handler(self):
        from unittest.mock import patch
        import verify_workflow as vw

        for argv, key in (([], "verify"), (["status", "--json"], "status")):
            with self.subTest(key=key), patch.object(reg, "load_handler") as load:
                self.assertIs(vw.main(argv), load.return_value.return_value)
                load.assert_called_once_with(key, parsed_args=True)
                args, = load.return_value.call_args.args
                self.assertEqual(args.command, argv[0] if argv else None)

    def test_the_engine_frozen_face_is_not_grown_by_the_registry(self):
        """Loading the engine alone stays within the measured cold import budget."""
        face = _engine_startup_face()
        modules = set(face["modules"])
        self.assertNotIn("registry", modules)
        self.assertNotIn("quickscan_registry", modules)
        self.assertIn("contracts", modules)
        self.assertLessEqual(face["count"], FROZEN_ENGINE_IMPORT_COUNT)
        self.assertGreater(face["count"], 100)

    def test_importtime_trace_of_the_registry_carries_no_monolith_mass(self):
        """② the caliber the packet names: ``-X importtime`` rows (§9.5)."""
        rows = _importtime_rows("import registry\n")
        self.assertGreater(len(rows), 50,
                           "the importtime trace is too small to be a face")
        modules = {row["module"] for row in rows}
        for allowed in ("registry", "contracts", "quickscan_registry"):
            self.assertIn(allowed, modules)
        self.assertNotIn(reg.ENGINE_MODULE, modules)
        self.assertFalse(
            [module for module in modules
             if module.split(".")[0] in ("checks", "release", "loop_runtime")],
            sorted(modules))
        self.assertLess(len(modules), FROZEN_ENGINE_IMPORT_COUNT)

    def test_importtime_trace_of_a_per_command_assembly_stays_engine_free(self):
        rows = _importtime_rows(
            "import registry\n"
            "registry.assemble('archguard-ratchet')\n")
        modules = {row["module"] for row in rows}
        self.assertNotIn(reg.ENGINE_MODULE, modules)
        self.assertLess(len(modules), FROZEN_ENGINE_IMPORT_COUNT)

    def test_per_command_assembly_face_stays_inside_the_engine_budget(self):
        """按命令懒加载：装配后的集合仍远低于巨石启动面（R6 口径计数）。"""
        probe = _probe(
            "import registry\n"
            "registry.assemble('archguard-ratchet')\n"
            "mods = sorted(sys.modules)\n"
            "print(json.dumps({'count': len(mods), 'modules': mods}))\n")
        modules = set(probe["modules"])
        self.assertIn("archguard_ratchet", modules)
        self.assertNotIn(reg.ENGINE_MODULE, modules)
        self.assertLess(probe["count"], FROZEN_ENGINE_IMPORT_COUNT)
        self.assertLess(probe["count"], _engine_startup_face()["count"])


# ── declaration face (``__all__`` / domain tokens) ──────────────────────────


class DeclarationFaceTests(unittest.TestCase):
    """The module's own declaration face must be complete and resolvable."""

    def test_all_names_resolve(self):
        self.assertTrue(reg.__all__)
        for name in reg.__all__:
            self.assertTrue(hasattr(reg, name), name)

    def test_every_public_definition_is_exported(self):
        """A public callable that ``__all__`` omits is declaration drift."""
        tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
        defined = [node.name for node in tree.body
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                        ast.AsyncFunctionDef))
                   and not node.name.startswith("_")]
        self.assertTrue(defined)
        for name in defined:
            self.assertIn(name, reg.__all__,
                          f"{name} is public but missing from __all__")

    def test_declared_domains_is_the_check_spec_domain_face(self):
        domains = reg.declared_domains()
        self.assertEqual(domains, tuple(sorted(
            {spec.domain for spec in reg.CHECK_SPECS})))
        self.assertEqual(len(domains), len(set(domains)))
        self.assertGreater(len(domains), 1)
        for domain in domains:
            declared = {spec.check_id for spec in reg.CHECK_SPECS
                        if spec.domain == domain}
            self.assertEqual(
                {spec.check_id for spec in reg.select_checks(domain=domain)},
                declared)

    def test_domain_mode_token_covers_every_declared_domain(self):
        for domain in reg.declared_domains():
            selected = reg.select_checks(mode=reg.DOMAIN_MODE_PREFIX + domain)
            self.assertTrue(selected, domain)
            self.assertTrue(all(spec.domain == domain for spec in selected),
                            domain)


# ── import-time registration guard (R5's other half) ────────────────────────


class ImportTimeGuardTests(unittest.TestCase):
    """The join with FEAT-025 is re-checked at import and fails closed.

    A declaration table that silently disagrees with the segment registry —
    or that names a mode outside the contract vocabulary — must never produce
    a half-built registry; it refuses at import time with an explicit message.
    """

    _PROBE = (
        "import dataclasses\n"
        "import types\n"
        "import quickscan_registry as real\n"
        "stub = types.ModuleType('quickscan_registry')\n"
        "stub.registry_ids = {ids}\n"
        "stub.segment = {segment}\n"
        "sys.modules['quickscan_registry'] = stub\n"
        "try:\n"
        "    import registry\n"
        "except Exception as exc:\n"
        "    payload = {{'type': type(exc).__name__, 'message': str(exc)}}\n"
        "else:\n"
        "    payload = {{'type': None}}\n"
        "print(json.dumps(payload))\n")

    def _stub_probe(self, ids, segment):
        return _probe(self._PROBE.format(ids=ids, segment=segment))

    def test_import_fails_closed_when_feat025_disagrees(self):
        probe = self._stub_probe("lambda: tuple(real.registry_ids())[:-1]",
                                 "real.segment")
        self.assertEqual(probe["type"], "RegistryError")
        self.assertIn("disagree", probe["message"])
        self.assertIn("FEAT-025", probe["message"])

    def test_import_fails_closed_on_a_non_contract_mode(self):
        probe = self._stub_probe(
            "lambda: real.registry_ids()",
            "lambda s: dataclasses.replace(real.segment(s), modes=('legacy',))")
        self.assertEqual(probe["type"], "RegistryError")
        self.assertIn("contract-vocabulary mode", probe["message"])

    def test_the_stubbed_join_is_the_only_reason_those_imports_fail(self):
        """Negative control: the same probe with an unmodified stub imports."""
        probe = self._stub_probe("lambda: real.registry_ids()", "real.segment")
        self.assertIsNone(probe["type"])


if __name__ == "__main__":
    unittest.main()
