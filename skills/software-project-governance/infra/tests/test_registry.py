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
import json
import re
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

# Box-drawing dashes used by the engine's ``# ── <id>. `` section markers.
_DASH = "\u2500"
_ENGINE_ENTRY = "def _run_full_engine_checks"
_SECTION_RE = re.compile(r"^\s*#\s*" + _DASH + r"{2}\s*([0-9][A-Za-z0-9]*)\.\s")

# FEAT-020 frozen faces, extended once by the DSH preset schema-compat guard
# in the same change as the regenerated snapshot: the new check segment 28v
# (70→71) and its `check-dsh-preset-compat` subcommand (82→83) — the
# documented contract-change path (generator.py --regen + review).
# FIX-310: 83 -> 82 CLI keys and 71 -> 70 check segments — retiring the
# dead `dsh.skills` declaration also retired its guard (Check 40 /
# `check-dsh-skills-manifest`); the FEAT-020 snapshot was regenerated with
# `contract_matrix/generator.py --regen` to record that deliberate change.
# FEAT-031 (0.81.0 slice V8): 82 -> 84 CLI keys (`dsh-doctor` + the
# `check-dsh-boundary` gate entry) and 70 -> 71 check segments (`28w`); the
# snapshot was regenerated with `contract_matrix/generator.py --regen` in the
# same change — the same deliberate-change path as FEAT-025/FIX-310, and the
# reason the segment is declared in `quickscan_registry.py` too
# (`registry._build_check_specs()` raises at import time when the two tables
# disagree, E-17).
# FEAT-032 (0.84.0 slice A-1): 84 -> 85 CLI keys (`governance-cost-report`;
# handler lives in `governance_cost.py`, the engine wires dispatch only);
# snapshot + architecture baseline regenerated in the same change.
# FEAT-037 (0.84.0 slice A-6): 85 -> 86 CLI keys (`check-entry-bootstrap-sync`;
# handler lives in `checks/projection.py`, thin bare-Name wrapper in the
# engine); snapshot regenerated via `contract_matrix/generator.py --regen`.
# FEAT-033 (0.84.0 slice A-2): 86 -> 87 CLI keys (`governance-bootstrap`;
# handler lives in `bootstrap_aggregate.py`, engine wires dispatch only);
# snapshot + architecture baseline regenerated in the same change.
# FEAT-039 (0.84.0 slice A-8): 87 -> 88 CLI keys (`check-injection-budget`;
# handler lives in `checks/injection_budget.py` — the engine wires dispatch and
# the Check 33 sub-report only — and the report rides inside check segment 33,
# so the segment face stays at 71); snapshot regenerated via
# `contract_matrix/generator.py --regen` in the same change.
# FEAT-055 (0.86.0 batch 2.0): 88 -> 95 CLI keys — the three governed writer
# modules join the dispatch face (engine wires dispatch only, governance_cost
# pattern; FEAT-047 P2-1 add_arguments caliber): `task-row-update`
# (task_row_update.py, FEAT-051), `locks-extend`/`locks-amend`/
# `evidence-append`/`decision-append` (governance_store.py, FEAT-046), and
# `baseline-register`/`baseline-evaluate` (baseline_metadata.py, FEAT-047).
# Snapshot + architecture baseline regenerated in the same change
# (`contract_matrix/generator.py --regen` + `archguard_ratchet.py --regen`).
FROZEN_CLI_KEYS = 95
FROZEN_SEGMENTS = 71

# FEAT-018 R6 frozen startup budget (``core/architecture-baseline.json`` r6):
# the acceptance ② comparison frame for "启动 import 集合不增".
# FEAT-032: 196 -> 197 — the engine imports the self-contained
# ``governance_cost`` module (stdlib-only at import time; zstandard is lazy,
# so the face grows by exactly this one module).
# FEAT-033: 197 -> 198 — the engine imports the self-contained
# ``bootstrap_aggregate`` module (import face = stdlib + the engine-free
# leaves resolve_entry / task_priority; grows the face by exactly this one
# module).
# FEAT-039: 198 -> 199 — the engine imports the self-contained
# ``checks.injection_budget`` leaf (stdlib-only: json/re/sys/pathlib) and
# re-exports its public surface; the ArchGuard R6 cold-import face grows by
# exactly this one module (baseline regenerated in the same change, see
# ``core/architecture-baseline.json`` r6).
# FEAT-055: 199 -> 205 — the engine imports the three self-contained
# governed writer modules (``task_row_update`` / ``governance_store`` /
# ``baseline_metadata``) plus exactly the three leaves their import-time
# faces pull in and the engine never had: the L0 ``contracts`` leaf (all
# three writers consume the m0-r1 frozen contract read-only), ``uuid``
# (contracts' operation-id generator) and ``_uuid`` (uuid's C companion
# module in the measured sys.modules face — git-archive dual-face diff,
# review-FEAT-055 F-1; ``threading`` was already in the HEAD face).
# Baseline regenerated in the same change, see
# ``core/architecture-baseline.json``.
FROZEN_ENGINE_IMPORT_COUNT = 205

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


def _segment_facts():
    """{segment: {"calls": set[str], "all_issues": bool}} by line attribution.

    One AST parse of the engine; every Call / ``all_issues`` AugAssign node is
    attributed to the ``# ── <id>. `` section that contains its line. Section
    scoping follows the FEAT-025 caliber (``_run_full_engine_checks`` body
    only): 30b prints no banner and 28u's section runs into the summary block,
    so sub-parsing the section text is unreliable while line attribution is
    exact.
    """
    source = _engine_source()
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith(_ENGINE_ENTRY))
    end = next(i for i in range(start + 5, len(lines))
               if lines[i].startswith("def "))
    marks = []
    for index in range(start, end):
        match = _SECTION_RE.match(lines[index])
        if match is not None:
            marks.append((index + 1, match.group(1)))
    facts = {}
    for position, (line_no, segment) in enumerate(marks):
        stop = marks[position + 1][0] if position + 1 < len(marks) else end + 1
        facts[segment] = {"range": (line_no, stop), "calls": set(),
                          "all_issues": False}
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", None)
        if line is None:
            continue
        for segment, slot in facts.items():
            low, high = slot["range"]
            if not low <= line < high:
                continue
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                slot["calls"].add(node.func.id)
            elif (isinstance(node, ast.AugAssign)
                  and isinstance(node.target, ast.Name)
                  and node.target.id == "all_issues"):
                slot["all_issues"] = True
            break
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


# ── ① command registry (82 keys) ────────────────────────────────────────────


class CommandRegistryTests(unittest.TestCase):

    def test_declares_the_frozen_key_count(self):
        self.assertEqual(len(reg.COMMAND_SPECS), FROZEN_CLI_KEYS)
        self.assertEqual(len(reg.command_keys()), FROZEN_CLI_KEYS)
        self.assertEqual(len(set(reg.command_keys())), FROZEN_CLI_KEYS)

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
            # FEAT-055 (0.86.0 batch 2.0): the BaselineMetadata provenance
            # writer's two dispatch keys; handlers live in
            # baseline_metadata.py, the engine wires dispatch only
            # (governance_cost pattern, FEAT-047 P2-1 add_arguments caliber).
            "baseline-evaluate", "baseline-register",
            "check-capability-registry",
            # FEAT-037 (0.84.0 slice A-6): entry-bootstrap guard handler lives
            # in checks/projection.py; the engine wires a thin wrapper only.
            "check-entry-bootstrap-sync",
            # FEAT-039 (0.84.0 slice A-8): injection-size budget handler lives
            # in checks/injection_budget.py; the engine wires dispatch + the
            # Check 33 sub-report only (this engine's LOC/print counts are
            # only-down under the ArchGuard ratchet). Sorted position follows
            # the key string, not the task age.
            "check-injection-budget",
            "check-manifest-consistency", "check-review-debt",
            # FEAT-055 (0.86.0 batch 2.0): the DEC-append writer of the
            # governance_store family (handlers in governance_store.py).
            "decision-append", "dsh-doctor",
            # FEAT-055 (0.86.0 batch 2.0): the EVD-append writer of the
            # governance_store family.
            "evidence-append",
            # FEAT-033 (0.84.0 slice A-2): read-only bootstrap aggregate
            # handler lives in bootstrap_aggregate.py; the engine wires
            # dispatch only (governance_cost pattern).
            "governance-bootstrap",
            # FEAT-032 (0.84.0 slice A-1): cost observability handler lives
            # in governance_cost.py; the engine wires dispatch only.
            "governance-cost-report",
            # FEAT-055 (0.86.0 batch 2.0): the lock-maintenance writers of
            # the governance_store family.
            "locks-amend", "locks-extend",
            # FEAT-055 (0.86.0 batch 2.0): the task-row state-flip writer
            # (B-1 termination surface; handler in task_row_update.py).
            "task-row-update",
        ])

    def test_declared_keys_resolve_to_callables(self):
        modules = {}
        for spec in reg.COMMAND_SPECS:
            handler = reg.load_handler(spec.key)
            self.assertTrue(callable(handler), spec.key)
            modules.setdefault(reg.loader_module(spec.handler), []).append(
                spec.key)
        self.assertGreaterEqual(len(modules), 3)


# ── ① check registry (70 segments) ──────────────────────────────────────────


class CheckRegistryTests(unittest.TestCase):

    def test_declares_the_frozen_segment_count(self):
        self.assertEqual(len(reg.CHECK_SPECS), FROZEN_SEGMENTS)
        self.assertEqual(len(reg.segment_ids()), FROZEN_SEGMENTS)
        self.assertEqual(len(set(reg.segment_ids())), FROZEN_SEGMENTS)

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
        self.assertLess(len(hosted), FROZEN_SEGMENTS)
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
                    aliases[bound] = (f"{node.module}.{alias.name}"
                                      if alias.asname else node.module)
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
            self.assertEqual(len(body), 1, f"{attr} is no longer a wrapper")
            call = body[0].value if isinstance(body[0], ast.Return) else None
            self.assertIsInstance(call, ast.Call)
            self.assertIsInstance(call.func, ast.Attribute)
            self.assertEqual(call.func.attr,
                             reg.loader_attr(reg.check_spec(check_id).loader))
            target = aliases.get(call.func.value.id)
            self.assertEqual(target,
                             reg.loader_module(reg.check_spec(check_id).loader))


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
        self.assertIn(str(FROZEN_CLI_KEYS), joined)
        self.assertIn(str(FROZEN_SEGMENTS), joined)

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
        self.assertEqual(len(report.declared_keys), FROZEN_CLI_KEYS)
        self.assertEqual(len(report.declared_segments), FROZEN_SEGMENTS)
        self.assertEqual(len(report.observed_keys), FROZEN_CLI_KEYS)
        self.assertEqual(len(report.observed_segments), FROZEN_SEGMENTS)

    def test_an_explicit_live_label_on_the_live_branch_is_accepted(self):
        """F-1 negative control: the honest label is not refused."""
        report = reg.verify_registration(source=reg.LIVE_SOURCE)
        self.assertEqual(report.source, reg.LIVE_SOURCE)
        self.assertTrue(report.ok, "\n".join(report.lines()))


# ── ② startup import set ────────────────────────────────────────────────────


class StartupImportTests(unittest.TestCase):
    """Acceptance ② — registry load and per-command load add no startup mass."""

    def test_engine_baseline_is_the_frozen_196_module_caliber(self):
        """F-4: the recorded r6 count is reproduced by an *executable* caliber.

        ``core/architecture-baseline.json`` labels its r6 block with the
        shorthand ``python -I -B -c 'import verify_workflow' (isolated)``,
        which cannot run as written: ``-I`` implies ``-P``, so the cwd never
        enters ``sys.path`` and the import dies with ``ModuleNotFoundError``.
        The executable caliber is the one both producers require
        (``perf_protocol.probe_sys_modules(infra_dir)`` /
        ``archguard_ratchet.measure_cold_import(infra_dir)``): the infra dir on
        ``sys.path`` first. That form runs here and must land exactly on the
        recorded count. The label string itself is baseline-owned — correcting
        it is registered on the archguard/baseline side, not edited here.
        """
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        budget = baseline["r6_startup_budget"]
        self.assertEqual(budget["import_count"], FROZEN_ENGINE_IMPORT_COUNT)
        self.assertIn("import verify_workflow", budget["probe"])
        self.assertEqual(_engine_startup_face()["count"],
                         budget["import_count"],
                         "the executable caliber (infra dir injected) does not "
                         "reproduce the recorded r6 count")

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

    def test_engines_own_startup_face_is_reachable_without_the_registry(self):
        """The registry is an additive seam: the engine does not import it."""
        source = _engine_source()
        self.assertNotIn("import registry", source)
        self.assertNotIn("from registry import", source)

    def test_the_engine_frozen_face_is_not_grown_by_the_registry(self):
        """② "启动 import 集合不增": the engine's own R6 face is untouched
        by the registry seam.

        Adding ``registry.py`` to the tree cannot grow the engine's startup
        import set, because the engine never imports the registry (module
        axis) and the live count stays inside the frozen budget.  FEAT-055
        deliberately moved ``contracts`` INTO the engine face: the three
        governed writers consume the m0-r1 frozen contract leaf at import
        time, so the negative control narrows to the registry's own modules
        (``registry`` / ``quickscan_registry`` stay out).
        """
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
