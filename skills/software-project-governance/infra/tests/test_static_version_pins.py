"""FIX-361 (DEC-213③) — static version pin scan: dedicated regression tests.

The scan lives in ``checks/version.py::scan_static_version_pins`` (appended to
``check_version_consistency`` as a WARN-only face). These tests anchor its
judgement semantics to the defect it rule-izes: the pre-fix literal pins that
FIX-352/353 had to dynamize by hand at the 0.84.0 release. The positive
shapes below embed the literal pre-fix lines recovered from git (commit
``7a865b7^``) and inject ``active_version="0.83.0"`` — the bump era the
release actually hit — so this file reproduces the original rot without
carrying a token equal to the current active version (the file stays clean
under its own scan by construction).

Machine judgements, each anchored to a live fact source:

  ① FIX-352 defect shape — an assertion argument string pinning the then
     active version is a hit (7a865b7^ test_entry_projection.py:450).
  ② FIX-353 defect shape — a module-level fixture head string pinning the
     then active version, plus its echo assertion, are hits (7a865b7^
     test_bootstrap_aggregate.py:54/333).
  ③ Derived/guarded post-fix shapes (read_active_version, @@ACTIVE_VERSION@@
     token, f-string derivation) produce no tokens and no findings.
  ④ Annotation faces (pure comment lines, docstrings) are skipped; multiline
     string CONTENT lines that start with ``#`` stay scanned (no comment
     blind spot for fixture markdown).
  ⑤ Exemption ledger — a (line, token, reason) row suppresses exactly its
     own hit; drifted rows surface as stale-exemption warnings.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_static_version_pins.py -q
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from checks import version as version_checks  # noqa: E402

#: The bump era the 0.84.0 release actually hit — injected, never assumed.
_PRE_FIX_ACTIVE = "0.83.0"

#: 7a865b7^ skills/.../infra/tests/test_entry_projection.py:450 — verbatim.
_FIX352_LINE = 'self.assertIn("@bootstrap-version: 0.83.0", updated)'

#: 7a865b7^ skills/.../infra/tests/test_bootstrap_aggregate.py:54 (fixture
#: head) and :333 (echo assertion) — verbatim shapes.
_FIX353_HEAD = "- **工作流版本**: 0.83.0"
_FIX353_ASSERT = 'self.assertEqual(project["workflow_version"], "0.83.0")'


class _ScanHarnessMixin:
    """Writes a synthetic tests dir under a temp root and scans it."""

    def _scan(self, files, active=_PRE_FIX_ACTIVE, exemptions=None):
        root = Path(tempfile.mkdtemp(prefix="fix361-"))
        tests_dir = root / "infra" / "tests"
        tests_dir.mkdir(parents=True)
        for name, content in files.items():
            path = tests_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return version_checks.scan_static_version_pins(
            root, active_version=active, tests_dir=tests_dir,
            exemptions=exemptions if exemptions is not None else {})

    _HIT_RE = re.compile(r"static-version-pin: (\S+:\d+) pins")

    def _hit_locations(self, findings):
        return {m.group(1) for f in findings
                for m in [self._HIT_RE.search(f)] if m}


class Fix352DefectShapeTests(_ScanHarnessMixin, unittest.TestCase):
    """① The assertion-literal pin that rotted at the 0.84.0 bump."""

    def test_assertion_literal_is_a_hit(self):
        findings = self._scan({"test_entry_like.py": _FIX352_LINE + "\n"})
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_entry_like.py:1"})

    def test_fstring_literal_is_a_hit(self):
        # Same defect, f-string clothing: the token still lands in the bytes.
        content = 'updated = f"@bootstrap-version: 0.83.0"\n'
        findings = self._scan({"test_f.py": content})
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_f.py:1"})

    def test_finding_names_file_line_and_derivation(self):
        findings = self._scan({"test_entry_like.py": _FIX352_LINE + "\n"})
        self.assertEqual(len(findings), 1)
        self.assertIn("infra/tests/test_entry_like.py:1", findings[0])
        self.assertIn("read_active_version", findings[0])
        self.assertIn("STATIC_PIN_EXEMPTIONS", findings[0])


class Fix353DefectShapeTests(_ScanHarnessMixin, unittest.TestCase):
    """② The fixture-head pin and its echo assertion (same release)."""

    _FILE = (
        '_TEMPLATE = """# 项目计划跟踪\n'
        + _FIX353_HEAD + '\n'
        '"""\n'
        "\n"
        "PLAN_TRACKER = _TEMPLATE\n"
        "\n"
        "def test_x(self):\n"
        "    " + _FIX353_ASSERT + "\n"
    )

    def test_fixture_head_and_echo_assertion_are_hits(self):
        findings = self._scan({"test_boot_like.py": self._FILE})
        # Head lives on line 2 inside the assigned fixture string; the echo
        # assertion on line 8. The FIX-353 rot was exactly this pair.
        self.assertEqual(
            self._hit_locations(findings),
            {"infra/tests/test_boot_like.py:2",
             "infra/tests/test_boot_like.py:8"})


class DerivedShapeNegativeTests(_ScanHarnessMixin, unittest.TestCase):
    """③ Post-fix derivation shapes carry no token and must stay silent."""

    def test_token_derivation_shape_not_flagged(self):
        content = (
            "_ACTIVE = _read_active_version()\n"
            'assert _ACTIVE, "fail-closed"\n'
            '_TOKEN = "@@ACTIVE_VERSION@@"\n'
            "PLAN_TRACKER = _TEMPLATE.replace(_TOKEN, _ACTIVE)\n"
            'self.assertIn("- **工作流版本**: %s" % _ACTIVE, updated)\n'
        )
        self.assertEqual(self._scan({"test_boot_like.py": content}), [])

    def test_fstring_derivation_shape_not_flagged(self):
        content = (
            "def _tpl_version():\n"
            "    return _read_header_version()\n"
            "\n"
            "self.assertIn(\n"
            '    f"@bootstrap-version: {_tpl_version()}", updated)\n'
        )
        self.assertEqual(self._scan({"test_entry_like.py": content}), [])


class NoiseControlTests(_ScanHarnessMixin, unittest.TestCase):
    """④ Annotation faces and non-active tokens never surface."""

    def test_synthetic_and_non_active_versions_not_flagged(self):
        content = (
            'skill_home = _make_skill_home(root, version="9.9.9")\n'
            'legacy = "0.1.0"\n'
            'ahead = "0.85.0"\n'
            'self.assertEqual(legacy, "0.1.0")\n'
        )
        self.assertEqual(self._scan({"test_synth.py": content}), [])

    def test_pure_comment_lines_not_flagged(self):
        content = (
            "# REL-080: fixture head 0.83.0 vs active mismatch historical note\n"
            "    # indented historical annotation with 0.83.0\n"
        )
        self.assertEqual(self._scan({"test_c.py": content}), [])

    def test_docstring_lines_not_flagged(self):
        content = (
            'def _doc():\n'
            '    """Calibration cross-check: 1,304 calls (0.83.0 slice A).\n'
            "\n"
            "    The pin 0.83.0 here is historical annotation, not a check.\n"
            '    """\n'
            "    return 0\n"
        )
        self.assertEqual(self._scan({"test_d.py": content}), [])

    def test_module_docstring_not_flagged(self):
        content = (
            '"""Module annotation mentioning 0.83.0 as history.\n'
            '"""\n'
            "x = 1\n"
        )
        self.assertEqual(self._scan({"test_md.py": content}), [])

    def test_multiline_string_hash_line_is_scanned(self):
        # String CONTENT starting with `#` is fixture markdown, not a comment:
        # skipping it would recreate the M-1 blind spot this check closes.
        content = (
            "_TEMPLATE = \"\"\"# 项目计划跟踪\n"
            "\n"
            "## 0.83.0 task 表\n"
            "\n"
            "| P0 | FEAT-101 | 已完成的任务 | — | 0.83.0 | tests | ✅ |\n"
            '"""\n'
        )
        findings = self._scan({"test_boot_like.py": content})
        self.assertEqual(
            self._hit_locations(findings),
            {"infra/tests/test_boot_like.py:3",
             "infra/tests/test_boot_like.py:5"})

    def test_token_boundaries(self):
        content = (
            'wider_prefix = "10.83.0"\n'
            'wider_middle = "0.830.0"\n'
            'wider_suffix = "0.83.05"\n'
            'prefixed = "v0.83.0"\n'
        )
        findings = self._scan({"test_b.py": content})
        # Only the standalone token in the v-prefixed pin is a pin; the rest
        # are different versions, not the active one.
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_b.py:4"})

    def test_inline_comment_after_code_still_scanned(self):
        content = 'x = pin("0.83.0")  # slice A calibration note\n'
        findings = self._scan({"test_ic.py": content})
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_ic.py:1"})


class ExemptionLedgerTests(_ScanHarnessMixin, unittest.TestCase):
    """⑤ The (line, token, reason) ledger and its stale-row audit."""

    _FILE = (
        "_TEMPLATE = \"\"\"# plan\n"
        "- **工作流版本**: 0.83.0\n"
        '"""\n'
    )

    def test_registered_hit_is_suppressed(self):
        ledger = {"infra/tests/test_boot_like.py": [
            (2, _PRE_FIX_ACTIVE, "synthetic fixture head — scenario data")]}
        self.assertEqual(
            self._scan({"test_boot_like.py": self._FILE}, exemptions=ledger),
            [])

    def test_wrong_token_entry_does_not_suppress(self):
        ledger = {"infra/tests/test_boot_like.py": [
            (2, "0.82.0", "token mismatch — must not mask")]}
        findings = self._scan(
            {"test_boot_like.py": self._FILE}, exemptions=ledger)
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_boot_like.py:2"})

    def test_drifted_line_surfaces_as_stale_exemption(self):
        ledger = {"infra/tests/test_boot_like.py": [
            (9, _PRE_FIX_ACTIVE, "line 9 never carries the token")]}
        findings = self._scan(
            {"test_boot_like.py": self._FILE}, exemptions=ledger)
        self.assertTrue(any(
            "stale exemption" in f and "test_boot_like.py:9" in f
            for f in findings))

    def test_removed_token_surfaces_as_stale_exemption(self):
        ledger = {"infra/tests/test_boot_like.py": [
            (2, _PRE_FIX_ACTIVE, "token since dynamized")]}
        content = self._FILE.replace(_FIX353_HEAD, "- **工作流版本**: @@ACTIVE_VERSION@@")
        findings = self._scan(
            {"test_boot_like.py": content}, exemptions=ledger)
        self.assertTrue(any(
            "stale exemption" in f and "no longer carries the token" in f
            for f in findings))

    def test_missing_file_surfaces_as_stale_exemption(self):
        ledger = {"infra/tests/test_gone.py": [
            (1, _PRE_FIX_ACTIVE, "file since deleted")]}
        findings = self._scan({"test_boot_like.py": self._FILE},
                              exemptions=ledger)
        self.assertTrue(any(
            "stale exemption" in f and "target file missing" in f
            for f in findings))


class PostureContractTests(_ScanHarnessMixin, unittest.TestCase):
    """DEC-213③ posture: WARN-only disclosure, fail-open advisory faces."""

    def test_all_findings_are_warn_prefixed(self):
        findings = self._scan({
            "test_boot_like.py": ExemptionLedgerTests._FILE,
            "test_broken.py": "def broken(:\n",
        })
        self.assertTrue(findings)
        for f in findings:
            self.assertTrue(f.startswith("[WARN]"), f)

    def test_unparsable_file_warns_and_scan_continues(self):
        findings = self._scan({
            "test_broken.py": "def broken(:\n",
            "test_entry_like.py": _FIX352_LINE + "\n",
        })
        self.assertTrue(any("cannot parse" in f and "test_broken.py" in f
                            for f in findings))
        self.assertEqual(self._hit_locations(findings),
                         {"infra/tests/test_entry_like.py:1"})

    def test_missing_tests_dir_is_silent(self):
        root = Path(tempfile.mkdtemp(prefix="fix361-empty-"))
        self.assertEqual(
            version_checks.scan_static_version_pins(
                root, active_version=_PRE_FIX_ACTIVE,
                tests_dir=root / "nowhere", exemptions={}),
            [])

    def test_underivable_active_version_is_silent(self):
        # The source-version face FAILs upstream; the scan adds nothing.
        findings = self._scan({"test_entry_like.py": _FIX352_LINE + "\n"},
                              active="")
        self.assertEqual(findings, [])


class RealTreeContractTests(unittest.TestCase):
    """The live tree: ledger rows live, face WARN-only, wiring intact."""

    def test_ledger_rows_are_live_on_current_tree(self):
        for rel, entries in version_checks.STATIC_PIN_EXEMPTIONS.items():
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"ledger target missing: {rel}")
            lines = path.read_text(encoding="utf-8").splitlines()
            for lineno, token, reason in entries:
                self.assertTrue(reason.strip(), f"unreasoned exemption {rel}:{lineno}")
                self.assertTrue(
                    0 < lineno <= len(lines)
                    and token in version_checks._SEMVER_TOKEN_RE.findall(lines[lineno - 1]),
                    f"stale ledger row {rel}:{lineno} (token {token}) — re-audit")

    def test_real_tree_scan_is_warn_only_and_clean(self):
        findings = version_checks.scan_static_version_pins(_REPO_ROOT)
        for f in findings:
            self.assertTrue(f.startswith("[WARN]"), f)
        # Current tree is FIX-352/353-dynamized: every active-version mention
        # is either derived or ledger-exempted — no unexempted hits may stand.
        self.assertEqual(
            [f for f in findings if " pins " in f], [],
            "unexempted static version pin(s) on the current tree")

    def test_check_version_consistency_appends_static_pin_face(self):
        issues = version_checks.check_version_consistency(_REPO_ROOT)
        for line in issues:
            if "static-version-pin" in line:
                self.assertTrue(line.startswith("[WARN]"), line)


if __name__ == "__main__":
    unittest.main()
