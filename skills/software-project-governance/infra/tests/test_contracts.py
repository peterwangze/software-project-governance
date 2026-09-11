"""FEAT-021 L0 contract-layer tests (AUDIT-150 REFACTOR-contract-layer).

TDD order (packet acceptance ④): this file was written and run RED (module
absent) BEFORE ``infra/contracts.py`` existed; the run is recorded in the
task evidence. Coverage of the new module: legal/illegal construction paths,
``to_legacy_dict`` round trip, dataclass immutability, port protocol shapes,
plus the R3 zero-I/O zero-internal-dependency caliber (AST-judged).

The legacy caliber facts asserted here are measured, not assumed:
  * ``issues`` element type census over the engine + checks/ + release/:
    string 210 / dict 45 / other 17 — the adapter renders the **string element
    face**; dict-element consumers keep their ``issue["type"]``/``["detail"]``
    payloads and are pinned by their own tests (``contracts.py`` caliber 1);
  * ``"details": None`` never occurs (0 dict literals); ``"pass": None``
    occurs exactly 3x (verify_workflow.py L17340/L17372 couldn't-run,
    checks/manifest.py L419 manifest-unreadable) — the tri-state gap is
    documented in the contract and covered by a negative test.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_contracts.py" -v
"""

import ast
import dataclasses
import json
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple, get_type_hints

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import contracts as c  # noqa: E402

CONTRACTS_PATH = _INFRA_DIR / "contracts.py"
SNAPSHOT_PATH = _INFRA_DIR / "contract_matrix" / "snapshots.json"
LEGACY_RESULT_KEYS = {"pass", "issues", "details"}
LEGACY_DISCLOSURE_KEYS = {"skipped", "skip_reason"}

# R3 caliber: the module may import stdlib only, and only what the contract
# needs. A new import is a deliberate contract-module change (add it here in
# the same reviewed change) — never an accident.
ALLOWED_IMPORTS = {
    "__future__", "collections", "dataclasses", "datetime", "re", "typing",
}
FORBIDDEN_CALL_NAMES = {
    "open", "print", "input", "eval", "exec", "compile", "__import__",
}
FORBIDDEN_CALL_ATTRS = {
    "read_text", "read_bytes", "write_text", "write_bytes", "glob", "rglob",
    "iterdir", "mkdir", "unlink", "system", "popen", "urlopen", "now",
    "utcnow",
}
ALLOWED_MODULE_BODY_NODES = (
    ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.Expr,
    ast.ClassDef, ast.FunctionDef,
)

# Test-local inverse of the legacy issue caliber (round-trip proof). The round
# trip holds only for the caliber's unambiguous subset: the message must not
# itself end in the ``" (...)"`` location-suffix form (see
# ``test_parenthesized_message_is_not_guaranteed_reversible``), so the messages
# used in the round-trip test intentionally contain no parentheses.
_LEGACY_ISSUE_RE = re.compile(
    r"^\[(?P<severity>[A-Z]+)\] (?P<check>check-[0-9]+[a-z]?): "
    r"(?P<message>.+?)(?: \((?P<file>[^()]+?)(?::(?P<line>\d+))?\))?$")


def _finding(**overrides):
    fields = {"severity": "WARN", "check": "check-28p", "message": "demo issue"}
    fields.update(overrides)
    return c.Finding(**fields)


def _result(**overrides):
    fields = {"check": "check-28p", "passed": True, "findings": []}
    fields.update(overrides)
    return c.CheckResult(**fields)


def _spec(**overrides):
    fields = {
        "check_id": "check-28p",
        "domain": "review",
        "loader": "checks.review_domain.run_review_checks",
        "input_deps": ("plan-tracker",),
        "severity_floor": "WARN",
        "modes": ("full", "quick"),
    }
    fields.update(overrides)
    return c.CheckSpec(**fields)


def _violation(testcase, callable_obj, *needles):
    """Assert ContractViolation with an explicit message (fail-closed caliber)."""
    with testcase.assertRaises(c.ContractViolation) as ctx:
        callable_obj()
    message = str(ctx.exception)
    for needle in needles:
        testcase.assertIn(needle, message,
                          f"{needle!r} missing from violation message")
    return message


def _annotation_nodes(tree):
    """Every annotation position of a module (args, returns, ann-assigns)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.annotation is not None:
            yield node.annotation
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                node.returns is not None:
            yield node.returns
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            yield node.annotation


def _type_expression_values(tree):
    """Assignment right-hand sides, where a PEP 604 *alias* hides.

    ``Alias = str | None`` is py39-grammar-legal but raises ``TypeError`` at
    import time on 3.9 — exactly the drift this guard exists to catch, and
    invisible to an annotation-only scan (F-10).
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            yield node.value


#: Names that make a ``|`` expression look like a type union rather than an
#: integer/bitwise flag combination.
_TYPE_LIKE_NAMES = {
    "str", "int", "bool", "float", "complex", "bytes", "bytearray", "list",
    "dict", "tuple", "set", "frozenset", "type", "object",
}


def _looks_like_type_union(value):
    """Heuristic: is this ``a | b`` expression a type union (PEP 604)?"""
    leaves = [node for node in ast.walk(value)
              if isinstance(node, (ast.Name, ast.Constant))]
    if len(leaves) < 2:
        return False
    has_anchor = False
    for leaf in leaves:
        if isinstance(leaf, ast.Constant):
            if leaf.value is not None:
                return False        # 1 | 2 — a value expression, not a type
            has_anchor = True
            continue
        if leaf.id in _TYPE_LIKE_NAMES:
            has_anchor = True
            continue
        if not leaf.id[:1].isupper():
            return False            # lowercase non-builtin => a variable
    return has_anchor


def _python39_problems(source):
    """3.10+-only constructs a py39 target (pyproject: ruff/mypy py39) rejects."""
    problems = []
    try:
        ast.parse(source, feature_version=(3, 9))
    except SyntaxError as exc:
        problems.append(f"py39 grammar rejects the source: {exc}")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if type(node).__name__ == "Match":
            problems.append(f"match statement (3.10+) at line {node.lineno}")
    for annotation in _annotation_nodes(tree):
        for node in ast.walk(annotation):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                problems.append(
                    f"PEP 604 union in annotation at line {node.lineno} — "
                    f"use typing.Optional/typing.Union (DEC-184 Q1)")
    for value in _type_expression_values(tree):
        for node in ast.walk(value):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) \
                    and _looks_like_type_union(node):
                problems.append(
                    f"PEP 604 union alias outside an annotation at line "
                    f"{node.lineno} — py39 rejects it at runtime; use "
                    f"typing.Optional/typing.Union (DEC-184 Q1)")
    return problems


class ModuleSurfaceTests(unittest.TestCase):
    """Exported shape: aliases, vocabulary, exception type."""

    def test_type_aliases_are_plain_str(self):
        self.assertIs(c.CheckID, str)
        self.assertIs(c.CommandKey, str)

    def test_all_exports_resolve_and_are_unique(self):
        self.assertTrue(c.__all__)
        self.assertEqual(len(c.__all__), len(set(c.__all__)))
        for name in c.__all__:
            self.assertTrue(hasattr(c, name), f"__all__ exports missing {name}")

    def test_severity_vocabulary_is_the_frozen_triple(self):
        self.assertEqual(c.SEVERITIES, ("BLOCKING", "WARN", "INFO"))

    def test_contract_violation_is_a_value_error(self):
        self.assertTrue(issubclass(c.ContractViolation, ValueError))

    def test_check_id_pattern_is_the_documented_form(self):
        self.assertEqual(c.CHECK_ID_PATTERN, r"check-[0-9]+[a-z]?")
        for segment in ("check-1", "check-40", "check-18i", "check-28u",
                        "check-30c"):
            self.assertRegex(segment, c.CHECK_ID_PATTERN)


class ZeroIoZeroDependencyTests(unittest.TestCase):
    """R3 caliber: stdlib only, zero internal imports, zero I/O (AST-judged)."""

    @classmethod
    def setUpClass(cls):
        cls.source = CONTRACTS_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_imports_are_the_allowlisted_stdlib_subset(self):
        found = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                found.add(node.module or "")
        roots = {name.split(".")[0] for name in found if name}
        self.assertTrue(
            roots <= ALLOWED_IMPORTS,
            f"unauthorized imports: {sorted(roots - ALLOWED_IMPORTS)}")
        self.assertNotIn("", found, "relative import smuggles an internal dep")
        self.assertEqual(
            roots & {"verify_workflow", "contract_matrix", "archguard_ratchet"},
            set(), "L0 must not import any in-repo module")

    def test_no_io_or_side_effect_calls(self):
        offenders = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALL_NAMES:
                offenders.append((node.lineno, func.id))
            elif isinstance(func, ast.Attribute) and \
                    func.attr in FORBIDDEN_CALL_ATTRS:
                offenders.append((node.lineno, f".{func.attr}"))
        self.assertEqual(offenders, [], "L0 must perform zero I/O")

    def test_module_body_has_no_import_time_side_effects(self):
        """Only declarations: no executed statement creates state or I/O."""
        offenders = [
            type(node).__name__ for node in self.tree.body
            if not isinstance(node, ALLOWED_MODULE_BODY_NODES)
        ]
        self.assertEqual(offenders, [],
                         "module body must be declarations only (§9.1)")

    def test_module_has_no_cli_entry_point(self):
        self.assertNotIn(
            "__main__", self.source,
            "L0 is a pure contract module — CLI/rendering belongs to L5")


class FindingTests(unittest.TestCase):
    """Check ID / severity / message / file / line / extra construction."""

    def test_valid_finding_defaults(self):
        finding = _finding()
        self.assertEqual(finding.severity, "WARN")
        self.assertEqual(finding.check, "check-28p")
        self.assertEqual(finding.message, "demo issue")
        self.assertIsNone(finding.file)
        self.assertIsNone(finding.line)
        self.assertEqual(finding.extra, {})

    def test_finding_is_frozen(self):
        finding = _finding()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            finding.message = "mutated"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            finding.extra = {"x": 1}

    def test_finding_equality_by_value_and_extra_participation(self):
        self.assertEqual(_finding(), _finding())
        self.assertNotEqual(_finding(), _finding(extra={"k": 1}))
        self.assertNotEqual(_finding(), _finding(severity="INFO"))

    def test_finding_is_unhashable_by_field_design(self):
        """Characterization: the dict-typed ``extra`` field makes hashing fail.

        Frozen value objects are usually hashable, but §3.6 declares
        ``extra: dict``; a dict field cannot be hashed. Findings are therefore
        compared by equality (``==``), never used as set/dict keys.
        """
        with self.assertRaises(TypeError):
            hash(_finding())

    def test_accepts_every_extension_segment_form(self):
        for segment in ("check-1", "check-40", "check-18i", "check-28u",
                        "check-30c"):
            self.assertEqual(_finding(check=segment).check, segment)

    def test_rejects_unknown_severity(self):
        _violation(self, lambda: _finding(severity="ERROR"),
                   "Finding.severity", "BLOCKING")

    def test_severity_is_case_sensitive(self):
        _violation(self, lambda: _finding(severity="warn"), "Finding.severity")

    def test_rejects_non_text_severity(self):
        _violation(self, lambda: _finding(severity=3), "Finding.severity")

    def test_rejects_malformed_check_ids(self):
        for bad in ("28p", "check-", "check-28P", "check-28pp", "check 28",
                    "Check-28p", "28"):
            _violation(self, lambda bad=bad: _finding(check=bad),
                       "Finding.check", r"check-[0-9]+[a-z]?")

    def test_rejects_blank_or_non_text_check(self):
        for bad in ("", "   "):
            _violation(self, lambda bad=bad: _finding(check=bad),
                       "Finding.check", "non-empty string")
        _violation(self, lambda: _finding(check=28), "Finding.check")

    def test_rejects_blank_message(self):
        for bad in ("", "   "):
            _violation(self, lambda bad=bad: _finding(message=bad),
                       "Finding.message")

    def test_rejects_non_text_message(self):
        _violation(self, lambda: _finding(message=None), "Finding.message")

    def test_accepts_file_and_line(self):
        finding = _finding(file="docs/a.md", line=42)
        self.assertEqual((finding.file, finding.line), ("docs/a.md", 42))

    def test_rejects_blank_or_non_text_file(self):
        for bad in ("", "   "):
            _violation(self, lambda bad=bad: _finding(file=bad), "Finding.file")
        _violation(self, lambda: _finding(file=Path("docs/a.md")),
                   "Finding.file")

    def test_file_relativeness_is_not_validated_by_l0(self):
        """Characterization (F-9): §3.6 calls ``file`` repo-root-relative, but
        L0 does not parse paths — nothing here forbids an absolute/escaping
        path. The declared gap is deliberate: parsers/renderers own path
        resolution, and adding a root concept to L0 would need repo knowledge
        this layer must not have.
        """
        for unvalidated in ("C:\\x\\y.md", "/abs/x.md", "../../escape.md"):
            self.assertEqual(_finding(file=unvalidated).file, unvalidated)

    def test_rejects_non_positive_line(self):
        for bad in (0, -1, 1.5, "12"):
            _violation(self, lambda bad=bad: _finding(line=bad),
                       "Finding.line", "1-based")

    def test_rejects_bool_line(self):
        _violation(self, lambda: _finding(line=True), "Finding.line", "bool")

    def test_rejects_non_mapping_extra(self):
        for bad in (["a"], "a", 3, ("a",)):
            _violation(self, lambda bad=bad: _finding(extra=bad),
                       "Finding.extra", "mapping")

    def test_extra_is_copied_not_aliased(self):
        source = {"expected_columns": 4}
        finding = _finding(extra=source)
        source["expected_columns"] = 99
        self.assertEqual(finding.extra, {"expected_columns": 4})
        self.assertIsNot(finding.extra, source)

    def test_extra_copy_is_top_level_only(self):
        """Characterization (F-7): the copy is ``dict(value)``, not deepcopy.

        The caller's container is not aliased, but nested mutable values are
        still shared — a frozen Finding does not deep-isolate its innards.
        Keep this pinned so no later slice reads "frozen" as "deeply isolated".
        """
        nested = {"expected": 4}
        source = {"columns": nested}
        finding = _finding(extra=source)
        self.assertIsNot(finding.extra, source)
        self.assertIs(finding.extra["columns"], nested)
        nested["expected"] = 99
        self.assertEqual(finding.extra["columns"]["expected"], 99)

    def test_extra_default_is_not_shared(self):
        first, second = _finding(), _finding()
        first.extra["injected"] = True  # mutating the copy is allowed
        self.assertEqual(second.extra, {})
        self.assertIsNot(first.extra, second.extra)

    def test_missing_required_fields_raise_type_error(self):
        with self.assertRaises(TypeError):
            c.Finding(severity="WARN", check="check-1")


class CheckResultTests(unittest.TestCase):
    """Construction validation + design-declared mutability."""

    def test_valid_result_defaults(self):
        result = _result()
        self.assertTrue(result.passed)
        self.assertEqual(result.findings, [])
        self.assertIsNone(result.skipped)
        self.assertEqual(result.details, {})

    def test_result_is_mutable_by_design(self):
        """§3.6 declares ``@dataclass`` (not frozen) for L4 aggregation."""
        result = _result()
        result.passed = False
        result.details["loop_runtime_claim_gate"] = {"pass": True}
        result.findings.append(_finding())
        self.assertFalse(result.passed)
        self.assertEqual(len(result.findings), 1)

    def test_rejects_bad_check_id(self):
        _violation(self, lambda: _result(check="28p"), "CheckResult.check")

    def test_rejects_non_bool_passed(self):
        for bad in (1, 0, "true", [], None):
            _violation(self, lambda bad=bad: _result(passed=bad),
                       "CheckResult.passed", "bool")

    def test_rejects_none_passed_with_tri_state_guidance(self):
        """Legacy ``pass: None`` (couldn't-run) has no §3.6 representation."""
        message = _violation(self, lambda: _result(passed=None),
                             "CheckResult.passed", "tri-state")
        self.assertIn("skipped", message)
        self.assertIn("BLOCKING", message)

    def test_accepts_findings_as_tuple_and_normalizes_to_list(self):
        result = _result(findings=(_finding(), _finding(message="second")))
        self.assertIsInstance(result.findings, list)
        self.assertEqual([f.message for f in result.findings],
                         ["demo issue", "second"])

    def test_rejects_string_findings(self):
        _violation(self, lambda: _result(findings="abc"),
                   "CheckResult.findings", "str")

    def test_rejects_non_finding_element(self):
        _violation(self, lambda: _result(findings=[{"severity": "WARN"}]),
                   "CheckResult.findings[0]", "Finding")

    def test_skip_disclosure_requires_passing_result(self):
        _violation(
            self,
            lambda: _result(passed=False, skipped="--skip-execution-gates"),
            "FIX-270", "passed=True")

    def test_skip_records_reason_and_keeps_warn_semantics(self):
        result = _result(skipped="BR-4 released-history query")
        self.assertEqual(result.skipped, "BR-4 released-history query")
        self.assertTrue(result.passed)

    def test_rejects_blank_or_non_text_skip(self):
        for bad in ("", "   ", 5):
            _violation(self, lambda bad=bad: _result(skipped=bad),
                       "CheckResult.skipped")

    def test_rejects_non_mapping_details(self):
        _violation(self, lambda: _result(details=["a"]),
                   "CheckResult.details", "mapping")

    def test_details_is_copied_not_aliased(self):
        source = {"records_checked": 3}
        result = _result(details=source)
        source["records_checked"] = 99
        self.assertEqual(result.details, {"records_checked": 3})
        self.assertIsNot(result.details, source)

    def test_details_default_is_not_shared(self):
        first, second = _result(), _result()
        first.details["injected"] = True
        self.assertEqual(second.details, {})

    def test_missing_required_fields_raise_type_error(self):
        with self.assertRaises(TypeError):
            c.CheckResult(check="check-1", passed=True)


class LegacyAdapterTests(unittest.TestCase):
    """§3.7 class-3 compatibility face: ``to_legacy_dict``."""

    def test_key_set_is_exactly_pass_issues_details(self):
        for result in (_result(), _result(passed=False,
                                          findings=[_finding()]),
                       _result(skipped="reason")):
            self.assertEqual(set(result.to_legacy_dict()), LEGACY_RESULT_KEYS)

    def test_value_types_match_the_legacy_caliber(self):
        legacy = _result(passed=False, findings=[_finding()]).to_legacy_dict()
        self.assertIsInstance(legacy["pass"], bool)
        self.assertIsInstance(legacy["issues"], list)
        self.assertIsInstance(legacy["details"], dict)

    def test_pass_key_mirrors_passed(self):
        self.assertTrue(_result(passed=True).to_legacy_dict()["pass"])
        self.assertFalse(_result(passed=False).to_legacy_dict()["pass"])

    def test_empty_issues_boundary(self):
        self.assertEqual(_result(findings=[]).to_legacy_dict()["issues"], [])

    def test_issue_text_carries_severity_check_and_message(self):
        legacy = _result(findings=[
            _finding(severity="BLOCKING", check="check-12",
                     message="missing evidence")
        ]).to_legacy_dict()
        self.assertEqual(legacy["issues"],
                         ["[BLOCKING] check-12: missing evidence"])

    def test_issue_text_carries_source_location(self):
        self.assertEqual(
            c.legacy_issue_text(_finding(file="docs/a.md", line=42)),
            "[WARN] check-28p: demo issue (docs/a.md:42)")
        self.assertEqual(
            c.legacy_issue_text(_finding(file="docs/a.md")),
            "[WARN] check-28p: demo issue (docs/a.md)")

    def test_issue_order_follows_findings_order(self):
        legacy = _result(findings=[
            _finding(message="first"), _finding(message="second"),
            _finding(message="third"),
        ]).to_legacy_dict()
        self.assertEqual([text.split(": ", 1)[1] for text in legacy["issues"]],
                         ["first", "second", "third"])

    def test_issue_text_rejects_non_finding(self):
        _violation(self, lambda: c.legacy_issue_text("nope"),
                   "legacy_issue_text", "Finding")

    def test_skip_disclosure_uses_the_fix270_keys(self):
        legacy = _result(skipped="BR-4 released-history query").to_legacy_dict()
        self.assertTrue(legacy["pass"], "WARN semantics — skip must not FAIL")
        self.assertIs(legacy["details"]["skipped"], True)
        self.assertEqual(legacy["details"]["skip_reason"],
                         "BR-4 released-history query")

    def test_no_skip_keys_when_not_skipped(self):
        details = _result().to_legacy_dict()["details"]
        self.assertEqual(set(details) & LEGACY_DISCLOSURE_KEYS, set())

    def test_skip_disclosure_normalizes_stale_detail_keys(self):
        legacy = _result(
            skipped="fresh reason",
            details={"skipped": False, "skip_reason": "stale reason"},
        ).to_legacy_dict()
        self.assertIs(legacy["details"]["skipped"], True)
        self.assertEqual(legacy["details"]["skip_reason"], "fresh reason")

    def test_adapter_output_is_the_level_a_result_dict_not_a_label_block(self):
        """F-2: the two nesting levels of the FIX-270 skip pair are pinned.

        Level A (§3.7 Result dict, what the adapter emits): exactly
        ``pass``/``issues``/``details``, with the disclosure pair inside
        ``details``.

        Level B (the label block inside a domain result — what
        ``verify_workflow.py`` L20613-20621 reads): ``pass``/``skipped``/
        ``skip_reason`` at the block's *own* top level, exactly as
        L7285-7297 builds ``details["dsh_upgrade_regression"]``.

        The two levels are not interchangeable: handing the adapter dict to the
        engine loop as a label block loses the disclosure (first half of this
        test), so a slice wiring ``CheckResult`` into that consumer MUST promote
        the pair to the label-block level (documented convention, second half).
        Without this pin the placement rule lives nowhere.
        """
        result = _result(check="check-30c",
                         skipped="BR-4 released-history query")
        legacy = result.to_legacy_dict()

        # Level A: the adapter's own face — 3 keys, pair inside `details`.
        self.assertEqual(set(legacy), LEGACY_RESULT_KEYS)
        self.assertIs(legacy["details"]["skipped"], True)

        def engine_loop(domain_result):
            """``verify_workflow.py`` L20613-20621 caliber, verbatim."""
            disclosed = []
            for label, detail in domain_result["details"].items():
                if detail.get("skipped"):
                    disclosed.append((label, detail.get("skip_reason")))
            return disclosed

        # Trap: nesting the level-A dict as a label block hides the skip.
        trapped = {"pass": legacy["pass"], "issues": legacy["issues"],
                   "details": {"the_label": legacy}}
        self.assertEqual(engine_loop(trapped), [],
                         "level-A nesting cannot be read as a label block")

        # Convention: promote the pair to the label block's top level.
        label_block = {
            "pass": legacy["pass"],
            "issues": legacy["issues"],
            "skipped": "skipped" in legacy["details"],
            "skip_reason": legacy["details"].get("skip_reason"),
        }
        self.assertEqual(engine_loop({"details": {"the_label": label_block}}),
                         [("the_label", "BR-4 released-history query")])
        self.assertTrue(label_block["pass"],
                        "WARN semantics — a skip is disclosed, never a mis-FAIL")

    def test_details_copy_is_top_level_only(self):
        """Characterization (F-7): nested details values stay shared."""
        nested = {"records": 3}
        result = _result(details={"summary": nested})
        legacy = result.to_legacy_dict()
        self.assertIsNot(legacy["details"], result.details)
        self.assertIs(legacy["details"]["summary"], nested)

    def test_details_copy_isolates_every_call(self):
        result = _result(details={"records_checked": 3})
        first = result.to_legacy_dict()
        first["details"]["records_checked"] = 99
        self.assertEqual(result.details, {"records_checked": 3})
        second = result.to_legacy_dict()
        self.assertEqual(second["details"], {"records_checked": 3})
        self.assertIsNot(first["details"], second["details"])

    def test_adapter_is_deterministic(self):
        result = _result(findings=[_finding(), _finding(message="second")],
                         details={"records_invalid": 0})
        self.assertEqual(result.to_legacy_dict(), result.to_legacy_dict())

    def test_legacy_dict_is_json_serializable(self):
        legacy = _result(findings=[_finding(message="中文问题 (含括号)")],
                         details={"verdict": "PASS", "count": 0,
                                  "list": [1, 2], "flag": False}
                         ).to_legacy_dict()
        payload = json.dumps(legacy, ensure_ascii=False, sort_keys=True)
        self.assertEqual(json.loads(payload), legacy)

    def test_legacy_issue_text_round_trips_to_finding_fields(self):
        """Every field the caliber can carry survives the round trip.

        Premise (F-13): the round trip is guaranteed only for messages that do
        not themselves end in the ``" (...)"`` location-suffix form — the
        caliber is then unambiguous. The characterization test below pins what
        happens outside that subset.
        """
        findings = [
            _finding(severity="BLOCKING", check="check-1",
                     message="missing evidence", file="docs/a.md", line=42),
            _finding(severity="WARN", check="check-28u",
                     message="stale risk row", file=".governance/risk-log.md"),
            _finding(severity="INFO", check="check-30c",
                     message="no source location"),
        ]
        legacy = _result(findings=findings).to_legacy_dict()
        recovered = []
        for text in legacy["issues"]:
            match = _LEGACY_ISSUE_RE.match(text)
            self.assertIsNotNone(match, f"issue line not parseable: {text!r}")
            recovered.append({
                "severity": match.group("severity"),
                "check": match.group("check"),
                "message": match.group("message"),
                "file": match.group("file"),
                "line": int(match.group("line"))
                if match.group("line") else None,
            })
        self.assertEqual(recovered, [
            {"severity": f.severity, "check": f.check, "message": f.message,
             "file": f.file, "line": f.line}
            for f in findings
        ])

    def test_parenthesized_message_is_not_guaranteed_reversible(self):
        """Characterization (F-13): outside the premise, the caliber is lossy.

        ``legacy_issue_text`` has no escaping, so a message carrying the
        location-suffix form is re-read as a source location by any consumer
        (including this file's inverse regex). Pinned so no later slice reads
        the adapter as an arbitrary Finding ⇄ string bijection.
        """
        text = c.legacy_issue_text(_finding(message="over budget (columns=5)"))
        match = _LEGACY_ISSUE_RE.match(text)
        self.assertIsNotNone(match, f"issue line not parseable: {text!r}")
        self.assertEqual(match.group("file"), "columns=5")
        self.assertNotEqual(match.group("message"), "over budget (columns=5)")

    def test_extra_has_no_slot_in_the_legacy_issue_string(self):
        """``extra`` has no legacy slot *in the string element face*.

        Scoped claim (F-1): this says nothing about dict-element faces, which
        own their own payload mapping (see ``contracts.py`` caliber 1).
        """
        finding = _finding(extra={"expected_columns": 4})
        self.assertNotIn("expected_columns",
                         c.legacy_issue_text(finding))
        self.assertEqual(finding.extra, {"expected_columns": 4})

    def test_adapter_refuses_mutated_payload(self):
        """Boundary re-validation: hooks/CI consume this dict for exit codes."""
        result = _result()
        result.passed = None
        _violation(self, result.to_legacy_dict,
                   "to_legacy_dict", "tri-state")
        broken = _result()
        broken.findings = ["not a finding"]
        _violation(self, broken.to_legacy_dict,
                   "to_legacy_dict", "Finding")

    def test_adapter_refuses_mutated_skip_invariant(self):
        """F-3: post-construction mutation must not ship a contradictory dict.

        ``passed=False`` + a leftover ``skipped`` would serialize as
        ``pass=False`` with ``details["skipped"]=True`` — a skip disclosure
        attached to a FAIL, contradicting the FIX-270 WARN invariant.
        """
        contradicted = _result(skipped="was skipped")
        contradicted.passed = False
        _violation(self, contradicted.to_legacy_dict,
                   "to_legacy_dict", "skipped", "passed=True", "FIX-270")
        broken_skip = _result()
        broken_skip.skipped = 3
        _violation(self, broken_skip.to_legacy_dict,
                   "to_legacy_dict", "skipped")

    def test_adapter_revalidates_every_serialized_field(self):
        """F-3: the adapter's re-validation covers exactly what it serializes."""
        for mutate in (
            lambda r: setattr(r, "passed", "yes"),
            lambda r: setattr(r, "findings", "not a list"),
            lambda r: setattr(r, "skipped", "   "),
            lambda r: setattr(r, "details", ["not", "a", "mapping"]),
        ):
            mutated = _result()
            mutate(mutated)
            _violation(self, mutated.to_legacy_dict, "to_legacy_dict")

    def test_adapter_rejects_caller_supplied_disclosure_keys(self):
        """NF-1: the FIX-270 pair inside ``details`` is adapter-owned.

        F-3's attribute check does not cover the ``details`` channel: a
        caller-supplied pair survives the verbatim copy, so a FAIL
        (``passed=False``) carrying ``details["skipped"]=True`` would be
        promoted to a label block and read by the engine loop as ``[SKIP]`` —
        a failure silently disclosed as a skip. The adapter therefore refuses
        the reserved keys instead of passing a contradictory face through.
        """
        injected = _result(passed=False,
                           details={"skipped": True,
                                    "skip_reason": "injected"})
        _violation(self, injected.to_legacy_dict,
                   "to_legacy_dict", "adapter-owned", "skipped", "skip_reason")
        for stale in ({"skipped": False}, {"skip_reason": "stale reason"}):
            _violation(self, _result(details=stale).to_legacy_dict,
                       "to_legacy_dict", "adapter-owned")

    def test_recorded_skip_still_normalizes_stale_detail_keys(self):
        """The pre-existing caliber survives NF-1: a recorded skip owns the pair.

        Stale keys carried by ``details`` are overwritten from the typed object
        (never treated as caller-supplied disclosure), so the FIX-270
        normalization path keeps working.
        """
        stale = {"skipped": False, "skip_reason": "stale reason"}
        for result in (_result(skipped="fresh reason", details=dict(stale)),
                       _result(passed=True, skipped="fresh reason",
                               details=dict(stale))):
            legacy = result.to_legacy_dict()
            self.assertIs(legacy["details"]["skipped"], True)
            self.assertEqual(legacy["details"]["skip_reason"], "fresh reason")


class CheckSpecTests(unittest.TestCase):
    """Registration metadata (R5 input shape)."""

    def test_valid_spec_fields_are_stored_as_tuples(self):
        spec = _spec(input_deps=["plan-tracker", "evidence-log"],
                     modes=["full", "quick"])
        self.assertEqual(spec.check_id, "check-28p")
        self.assertEqual(spec.domain, "review")
        self.assertEqual(spec.loader, "checks.review_domain.run_review_checks")
        self.assertEqual(spec.input_deps, ("plan-tracker", "evidence-log"))
        self.assertEqual(spec.severity_floor, "WARN")
        self.assertEqual(spec.modes, ("full", "quick"))

    def test_spec_is_frozen(self):
        spec = _spec()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            spec.loader = "checks.other"

    def test_rejects_malformed_check_ids(self):
        for bad in ("", "28p", "check-", "check-28P"):
            _violation(self, lambda bad=bad: _spec(check_id=bad),
                       "CheckSpec.check_id")

    def test_rejects_blank_or_non_text_domain(self):
        for bad in ("", "   ", 3):
            _violation(self, lambda bad=bad: _spec(domain=bad),
                       "CheckSpec.domain")

    def test_loader_accepts_module_and_handler_dotted_paths(self):
        """Caliber decision (F-4): ``<module>`` or ``<module>.<attribute>``.

        The engine's check entry points are module-level callables (e.g.
        ``run_review_checks``), so the loader is a dotted *handler* path: R5
        resolution imports the module prefix and ``getattr``s the trailing
        attribute. A root-level (single-segment) name stays rejected.
        """
        for good in ("checks.review_domain",
                     "checks.review_domain.run_review_checks",
                     "infra.checks.review_domain.run_review_checks"):
            self.assertEqual(_spec(loader=good).loader, good)

    def test_loader_rejects_paths_and_file_names(self):
        for bad in ("verify_workflow.py", "/abs/path.py", "C:\\x\\y.py",
                    "checks/review_domain.py", "", 3, "single"):
            _violation(self, lambda bad=bad: _spec(loader=bad),
                       "CheckSpec.loader")

    def test_input_deps_default_free_but_empty_allowed(self):
        self.assertEqual(_spec(input_deps=()).input_deps, ())

    def test_rejects_duplicate_input_deps(self):
        _violation(self, lambda: _spec(input_deps=("plan-tracker",
                                                   "plan-tracker")),
                   "CheckSpec.input_deps", "duplicate")

    def test_rejects_blank_or_non_text_input_deps(self):
        for bad in (("",), (3,), "plan-tracker", {"a": 1}):
            _violation(self, lambda bad=bad: _spec(input_deps=bad),
                       "CheckSpec.input_deps")

    def test_severity_floor_uses_the_finding_vocabulary(self):
        for good in c.SEVERITIES:
            self.assertEqual(_spec(severity_floor=good).severity_floor, good)
        for bad in ("WARNING", "warn", "", 3):
            _violation(self, lambda bad=bad: _spec(severity_floor=bad),
                       "CheckSpec.severity_floor")

    def test_modes_vocabulary(self):
        for good in ("full", "quick", "domain:review", "domain:ci_domain",
                     "domain:review-2"):
            self.assertEqual(_spec(modes=(good,)).modes, (good,))
        for bad in ("", "fast", "domain:", "domain", "FULL", "domain:a b"):
            _violation(self, lambda bad=bad: _spec(modes=(bad,)),
                       "CheckSpec.modes")

    def test_modes_must_be_non_empty_unique_sequence(self):
        for bad in ((), [], "full", ("full", "full")):
            _violation(self, lambda bad=bad: _spec(modes=bad),
                       "CheckSpec.modes")

    def test_missing_required_fields_raise_type_error(self):
        with self.assertRaises(TypeError):
            c.CheckSpec(check_id="check-1", domain="review",
                        loader="checks.x", input_deps=(),
                        severity_floor="WARN")


class PortProtocolTests(unittest.TestCase):
    """§3.6 ports — L2 implements, L3/L4 only see the interface."""

    def test_ports_are_declared_protocols(self):
        for protocol in (c.GovernanceStore, c.FilesystemPort, c.GitPort,
                         c.ClockPort, c.RecordScope, c.LogicalRecord):
            self.assertIs(getattr(protocol, "_is_protocol", False), True,
                          f"{protocol.__name__} must be a typing.Protocol")

    def test_protocols_cannot_be_instantiated(self):
        for protocol in (c.GovernanceStore, c.FilesystemPort, c.GitPort,
                         c.ClockPort):
            with self.assertRaises(TypeError):
                protocol()

    def test_declared_method_names_match_design(self):
        self.assertTrue(callable(c.GovernanceStore.read_records))
        self.assertTrue(callable(c.FilesystemPort.read_text))
        self.assertTrue(callable(c.FilesystemPort.list_files))
        for name in ("status", "show", "tag", "rev_parse"):
            self.assertTrue(callable(getattr(c.GitPort, name)),
                            f"GitPort.{name} missing (§3.6: status/show/tag/"
                            f"rev-parse)")
        self.assertTrue(callable(c.ClockPort.now))

    def test_type_hints_resolve_to_contract_types(self):
        """No hallucinated type names: every annotation resolves."""
        store_hints = get_type_hints(c.GovernanceStore.read_records)
        self.assertIs(store_hints["scope"], c.RecordScope)
        self.assertEqual(store_hints["return"],
                         Iterable[c.LogicalRecord])
        self.assertIs(get_type_hints(c.ClockPort.now)["return"], datetime)
        filesystem_hints = get_type_hints(c.FilesystemPort.read_text)
        self.assertIs(filesystem_hints["return"], str)
        self.assertEqual(get_type_hints(c.GitPort.tag)["return"],
                         Iterable[str])

    def test_record_model_placeholders_follow_the_record_model_fields(self):
        record_hints = get_type_hints(c.LogicalRecord)
        self.assertLessEqual(
            {"id", "status", "time", "relations", "source_path",
             "source_line"}, set(record_hints))
        self.assertEqual(get_type_hints(c.RecordScope)["sources"],
                         Tuple[str, ...])

    def test_ports_are_implementable_without_the_contract_changing(self):
        class _Store(c.GovernanceStore):
            def read_records(self, scope):
                return []

        class _Files(c.FilesystemPort):
            def read_text(self, path):
                return ""

            def list_files(self, root):
                return []

        class _Git(c.GitPort):
            def status(self):
                return ""

            def show(self, rev):
                return ""

            def tag(self):
                return []

            def rev_parse(self, rev):
                return "0" * 40

        class _Clock(c.ClockPort):
            def now(self):
                return datetime(2026, 9, 10, 0, 0, 0)

        self.assertEqual(list(_Store().read_records(None)), [])
        self.assertEqual(_Files().read_text("x"), "")
        self.assertEqual(_Git().rev_parse("HEAD"), "0" * 40)
        self.assertEqual(_Clock().now().year, 2026)


class Python39CompatibilityTests(unittest.TestCase):
    """DEC-184 Q1 transition caliber: the module stays py39-parseable.

    pyproject pins the progressive checks to py39 (``[tool.ruff]
    target-version = "py39"``, ``[tool.mypy] python_version = "3.9"``), so the
    contract uses ``from __future__ import annotations`` + ``typing.Optional``
    instead of §3.6's PEP 604 pseudocode syntax (3.10+ at runtime). The
    pyproject tool pins themselves are outside this packet's file scope.
    """

    def test_module_is_py39_parseable_without_pep604_or_match(self):
        source = CONTRACTS_PATH.read_text(encoding="utf-8")
        self.assertEqual(_python39_problems(source), [])

    def test_checker_detects_pep604_union(self):
        """Negative control — the py39 check has teeth."""
        problems = _python39_problems(
            "def f(value: str | None) -> int:\n    return 0\n")
        self.assertTrue(any("PEP 604" in problem for problem in problems),
                        f"union annotation not flagged: {problems}")

    def test_checker_detects_match_statement(self):
        problems = _python39_problems(
            "def f(x):\n    match x:\n        case 1:\n            return 1\n")
        self.assertTrue(problems, "3.10+ match statement not flagged")

    def test_checker_detects_pep604_union_alias_outside_annotations(self):
        """F-10: ``Alias = str | None`` passes py39 grammar, fails at runtime."""
        problems = _python39_problems("Alias = str | None\n")
        self.assertTrue(any("PEP 604" in problem for problem in problems),
                        f"module-level union alias not flagged: {problems}")

    def test_checker_detects_pep604_union_alias_with_class_operands(self):
        problems = _python39_problems("Alias = Record | None\n")
        self.assertTrue(any("PEP 604" in problem for problem in problems),
                        f"alias with a class operand not flagged: {problems}")

    def test_type_union_heuristic_does_not_flag_plain_bitwise_values(self):
        """Negative-negative control: the widened scan must not over-reach."""
        self.assertEqual(_python39_problems("MASK = 1 | 2\n"), [])
        self.assertEqual(_python39_problems("combined = left | right\n"), [])


class FrozenContractCrossCheckTests(unittest.TestCase):
    """The L0 CheckID form must cover the FEAT-020 frozen segment surface."""

    def test_every_frozen_check_segment_maps_to_a_contract_check_id(self):
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        segments = snapshot["faces"]["check_segments"]["ids"]
        self.assertTrue(segments, "frozen segment list must not be empty")
        unmatched = [segment for segment in segments
                     if not re.fullmatch(c.CHECK_ID_PATTERN,
                                         f"check-{segment}")]
        self.assertEqual(
            unmatched, [],
            "FEAT-020 frozen segments that the L0 CheckID form cannot "
            "express — extend the pattern deliberately")

    def test_frozen_cli_keys_reconcile_with_the_frozen_face_counts(self):
        """F-11: reconciled counts instead of a vacuously-true isinstance.

        JSON object keys are always ``str``, so the previous assertion could
        never fail. This one reconciles the frozen face's three fields against
        each other and against the ``CommandKey`` alias: the key list must be
        complete (count match), unique, and decomposable into single-key
        handlers plus alias groups — a hand-edit or a lost key breaks it.
        """
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        face = snapshot["faces"]["cli_dispatch"]
        keys = face["keys"]
        self.assertTrue(keys, "frozen key list must not be empty")
        self.assertEqual(face["key_count"], len(keys))
        self.assertEqual(len(set(keys)), len(keys), "frozen keys must be unique")
        single_key_handlers = face["handler_count"] - len(face["alias_groups"])
        aliased_keys = sum(len(group) for group in face["alias_groups"].values())
        self.assertEqual(face["key_count"], single_key_handlers + aliased_keys)
        for key in keys:
            self.assertIsInstance(key, c.CommandKey)


class AdapterVsFrozenShapeTests(unittest.TestCase):
    """Class-3 differential caliber: the adapter emits the shape §3.7 froze."""

    def test_adapter_shape_signature_is_bool_list_dict(self):
        def signature(value):
            if isinstance(value, bool):
                return "bool"
            if isinstance(value, dict):
                return {"$dict": {str(k): signature(v)
                                  for k, v in value.items()}}
            if isinstance(value, list):
                return {"$seq": "list"}
            return type(value).__name__

        legacy = _result(passed=False, findings=[_finding()],
                         details={"count": 1}).to_legacy_dict()
        self.assertEqual(
            signature(legacy),
            {"$dict": {"pass": "bool", "issues": {"$seq": "list"},
                       "details": {"$dict": {"count": "int"}}}})

    def test_adapter_never_adds_top_level_keys(self):
        legacy = _result(skipped="reason",
                         details={"extra": "kept"}).to_legacy_dict()
        self.assertEqual(set(legacy), LEGACY_RESULT_KEYS)
        self.assertIn("extra", legacy["details"])


if __name__ == "__main__":
    unittest.main()
