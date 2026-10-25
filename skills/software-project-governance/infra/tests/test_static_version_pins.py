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
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

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
        # FIX-411 (FIX-404 family): mkdtemp dirs (0o700) deny fixture
        # writes under the UAC-filtered DSH sandbox token — plain
        # default-mode mkdir instead; best-effort cleanup.
        root = Path(tempfile.gettempdir()) / (
            "fix361-" + uuid.uuid4().hex[:12])
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
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
        root = Path(tempfile.gettempdir()) / (
            "fix361-empty-" + uuid.uuid4().hex[:12])
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
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


class PinsLedgerWriterTests(unittest.TestCase):
    """FIX-462 — the pins register/re-anchor machine writer (pin_ledger).

    Mini-root harness: a REAL copy of checks/version.py (its own 55-entry
    ledger included) under a synthetic root whose SKILL.md frontmatter pins
    a synthetic active version (1.23.0 — never the repo's), so a fixture
    file carrying that token reproduces a live scan hit without touching
    the real tree. Precedent caliber: evidence-append / agent-locks-acquire
    (op-id receipt, effect-based idempotency, fail-closed atomicity).
    """

    _ACTIVE = "1.23.0"
    _TARGET_REL = "skills/software-project-governance/infra/tests/fixture_writer_target.py"
    _TARGET_BODY = '# fixture for the FIX-462 writer tests\n_TARGET_VERSION = "1.23.0"\n'

    def _mini_root(self):
        root = Path(tempfile.gettempdir()) / (
            "fix462-" + uuid.uuid4().hex[:12])
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        plugin = root / "skills" / "software-project-governance"
        (plugin / "infra" / "checks").mkdir(parents=True)
        (plugin / "infra" / "tests").mkdir(parents=True)
        shutil.copyfile(_INFRA_DIR / "checks" / "version.py",
                        plugin / "infra" / "checks" / "version.py")
        (plugin / "SKILL.md").write_text(
            "---\nname: software-project-governance\nversion: 1.23.0\n---\n\n"
            "# synthetic mini-root\n", encoding="utf-8")
        return root

    def _write_target(self, root, head=""):
        path = root / self._TARGET_REL
        path.write_text(head + self._TARGET_BODY, encoding="utf-8")
        return path

    def test_register_writes_row_with_provenance_and_receipt(self):
        import pin_ledger
        root = self._mini_root()
        self._write_target(root)
        receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE,
            "synthetic writer-test pin — scenario fixture row")
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["effect"], "written")
        self.assertRegex(receipt["operation_id"], r"^op-[0-9a-f]{32}$")
        self.assertTrue(all(receipt["post_checks"].values()))
        ledger_text = (root / pin_ledger.LEDGER_REL).read_text(encoding="utf-8")
        lines = ledger_text.splitlines()
        tuple_idx = next(i for i, l in enumerate(lines)
                         if "(2, \"{0}\",".format(self._ACTIVE) in l)
        self.assertRegex(lines[tuple_idx - 1], r"#\s*pins register op-[0-9a-f]{32}")
        issues, status = pin_ledger.exemption_face_issues(root)
        self.assertEqual((status, issues), ("PASS", []))

    def test_register_refusal_is_atomic_zero_write(self):
        import pin_ledger
        root = self._mini_root()
        self._write_target(root)
        ledger_path = root / pin_ledger.LEDGER_REL
        before = ledger_path.read_bytes()
        receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, "9.9.9",
            "token not on the line — must refuse")
        self.assertEqual(code, 2)
        self.assertEqual(receipt["code"], "refused")
        self.assertEqual(ledger_path.read_bytes(), before,
                         "refused write mutated the ledger (atomicity broken)")

    def test_register_is_effect_idempotent(self):
        import pin_ledger
        root = self._mini_root()
        self._write_target(root)
        ledger_path = root / pin_ledger.LEDGER_REL
        _receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE, "idempotency probe row")
        self.assertEqual(code, 0)
        snapshot = ledger_path.read_bytes()
        receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE, "idempotency probe row")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["effect"], "idempotent_noop")
        self.assertEqual(ledger_path.read_bytes(), snapshot)

    def test_reanchor_repairs_drift_and_is_idempotent_after(self):
        import pin_ledger
        root = self._mini_root()
        self._write_target(root)
        _receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE, "drift-probe row")
        self.assertEqual(code, 0)
        # Drift: two header lines land above the token (2 -> 4).
        self._write_target(root, head="# drifted header 1\n# drifted header 2\n")
        findings = pin_ledger._scan_hits(root)
        self.assertTrue(any("stale exemption" in f and ":2 " in f
                            for f in findings))
        receipt, code = pin_ledger.reanchor_exemption(
            root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["effect"], "written")
        self.assertTrue(all(receipt["post_checks"].values()))
        lines = (root / pin_ledger.LEDGER_REL).read_text(encoding="utf-8").splitlines()
        tuple_idx = next(i for i, l in enumerate(lines)
                         if "(4, \"{0}\",".format(self._ACTIVE) in l)
        self.assertRegex(lines[tuple_idx - 1], r"#\s*pins re-anchor op-[0-9a-f]{32}")
        # Post-repair scan: no stale row, no unexempted hit for the entry.
        findings = pin_ledger._scan_hits(root)
        self.assertFalse(any(self._TARGET_REL in f for f in findings))
        # Re-running the same re-anchor is an effect-level no-op.
        receipt, code = pin_ledger.reanchor_exemption(
            root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 0)
        self.assertEqual(receipt["effect"], "idempotent_noop")

    def test_hand_edit_without_provenance_warns_on_guard_face(self):
        import pin_ledger
        root = self._mini_root()
        self._write_target(root)
        _receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE, "face-probe row")
        self.assertEqual(code, 0)
        # Hand edit simulation: strip the machine provenance comment line.
        ledger_path = root / pin_ledger.LEDGER_REL
        lines = ledger_path.read_text(encoding="utf-8").splitlines(keepends=True)
        idx = next(i for i, l in enumerate(lines)
                   if "(2, \"{0}\",".format(self._ACTIVE) in l)
        del lines[idx - 1]
        ledger_path.write_text("".join(lines), encoding="utf-8")
        issues, status = pin_ledger.exemption_face_issues(root)
        self.assertEqual(status, "PASS")  # WARN-class, never a FAIL
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "pin_ledger_unattributed")
        self.assertIn(self._TARGET_REL, issues[0]["detail"])


class PinsWriterAmnestySyncTests(unittest.TestCase):
    """FIX-464 — a writer-touched row automatically leaves the delivery
    amnesty (the FIX-462 writer gap: the ledger moved but the frozen
    in-source set kept a GHOST row, failing the snapshot contract on the
    first real write).

    Harness: the FIX-462 mini-root PLUS a real copy of pin_ledger.py, with
    the fixture row pre-registered as a hand-written amnesty row (live
    ledger row without provenance + matching frozenset member) — the exact
    pre-writer state the delivery amnesty froze.  register/re-anchor must
    remove it from the set in the same transaction.
    """

    _ACTIVE = "1.23.0"
    _TARGET_REL = "skills/software-project-governance/infra/tests/fixture_writer_target.py"
    _TARGET_BODY = '# fixture for the FIX-464 amnesty-sync tests\n_TARGET_VERSION = "1.23.0"\n'

    def _mini_root_with_amnesty_row(self, ledger_row=True):
        import pin_ledger
        root = Path(tempfile.gettempdir()) / (
            "fix464-" + uuid.uuid4().hex[:12])
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        plugin = root / "skills" / "software-project-governance"
        (plugin / "infra" / "checks").mkdir(parents=True)
        (plugin / "infra" / "tests").mkdir(parents=True)
        shutil.copyfile(_INFRA_DIR / "checks" / "version.py",
                        plugin / "infra" / "checks" / "version.py")
        shutil.copyfile(_INFRA_DIR / "pin_ledger.py",
                        plugin / "infra" / "pin_ledger.py")
        (plugin / "SKILL.md").write_text(
            "---\nname: software-project-governance\nversion: 1.23.0\n---\n\n"
            "# synthetic mini-root\n", encoding="utf-8")
        (root / self._TARGET_REL).write_text(self._TARGET_BODY, encoding="utf-8")
        # Pre-writer state: the row is live (no provenance comment) AND a
        # delivery-amnesty member — hand-written, writer never touched it.
        # AST-anchored insert (writer discipline): the entry block lands
        # directly above the STATIC_PIN_EXEMPTIONS dict's closing brace.
        if ledger_row:
            ledger_path = root / pin_ledger.LEDGER_REL
            text = ledger_path.read_text(encoding="utf-8")
            parsed, perr = pin_ledger._parse_ledger(text)
            assert perr is None, perr
            _tree, dict_node = parsed
            lines = text.splitlines(keepends=True)
            insert_at = dict_node.end_lineno  # 1-based closing "}" line
            lines[insert_at - 1:insert_at - 1] = [
                '    "{0}": [\n'.format(self._TARGET_REL),
                '        (2, "{0}", "FIX-464 hand-written amnesty row probe"),\n'.format(
                    self._ACTIVE),
                "    ],\n",
            ]
            ledger_path.write_text("".join(lines), encoding="utf-8")
        self_path = root / pin_ledger.SELF_REL
        stext = self_path.read_text(encoding="utf-8")
        anchor = "DELIVERY_AMNESTY_ENTRIES = frozenset({\n"
        assert anchor in stext
        stext = stext.replace(
            anchor, anchor + '    ("{0}", 2, "{1}"),\n'.format(
                self._TARGET_REL, self._ACTIVE), 1)
        self_path.write_text(stext, encoding="utf-8")
        return root

    def _mini_amnesty(self, root):
        import pin_ledger
        module = pin_ledger._shadow_module(root / pin_ledger.SELF_REL)
        return module.DELIVERY_AMNESTY_ENTRIES

    def test_reanchor_moves_row_out_of_amnesty(self):
        import pin_ledger
        root = self._mini_root_with_amnesty_row()
        self_path = root / pin_ledger.SELF_REL
        before = self_path.read_bytes()
        ghost = (self._TARGET_REL, 2, self._ACTIVE)
        self.assertIn(ghost, self._mini_amnesty(root))
        # drift the token line 2 -> 4, then re-anchor
        (root / self._TARGET_REL).write_text(
            "# drift a\n# drift b\n" + self._TARGET_BODY, encoding="utf-8")
        receipt, code = pin_ledger.reanchor_exemption(
            root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["effect"], "written")
        self.assertEqual(receipt["amnesty_sync"], "written")
        amnesty = self._mini_amnesty(root)
        self.assertNotIn(ghost, amnesty, "ghost row survived the re-anchor")
        text = self_path.read_text(encoding="utf-8")
        self.assertRegex(text, r"#\s*pins re-anchor op-[0-9a-f]{32} \(FIX-464\)")
        # both-sided invariant on the mini root
        live, live_text = pin_ledger._live_entries(root)
        self.assertFalse(amnesty - live, "amnesty keeps ghost rows")
        for (rel, ln, tok) in (live - amnesty):
            idx = pin_ledger._ledger_entry_lineno(live_text, rel, ln, tok)
            lines = live_text.splitlines()
            self.assertTrue(idx >= 2 and pin_ledger._PROVENANCE_RE.search(
                lines[idx - 2]), "unattributed live row: {0}".format((rel, ln, tok)))
        self.assertNotEqual(self_path.read_bytes(), before)

    def test_reanchor_amnesty_sync_failure_restores_both_files(self):
        """A corrupted amnesty candidate (syntax sabotage injected into the
        frozenset) must leave BOTH the ledger and pin_ledger untouched."""
        import pin_ledger
        root = self._mini_root_with_amnesty_row()
        (root / self._TARGET_REL).write_text(
            "# drift a\n# drift b\n" + self._TARGET_BODY, encoding="utf-8")
        ledger_path = root / pin_ledger.LEDGER_REL
        self_path = root / pin_ledger.SELF_REL
        ledger_before = ledger_path.read_bytes()
        self_before = self_path.read_bytes()
        real_sync = pin_ledger._sync_amnesty_exit
        def sabotaging_sync(root_arg, rel, line, token, command, op_id):
            # land the ledger write, then make the amnesty candidate invalid
            self_path.write_text(
                self_path.read_text(encoding="utf-8").replace(
                    'DELIVERY_AMNESTY_ENTRIES = frozenset({',
                    'DELIVERY_AMNESTY_ENTRIES = frozenset({ this is not python'),
                encoding="utf-8")
            return real_sync(root_arg, rel, line, token, command, op_id)
        with unittest.mock.patch.object(
                pin_ledger, "_sync_amnesty_exit", sabotaging_sync):
            receipt, code = pin_ledger.reanchor_exemption(
                root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 2, receipt)
        self.assertIn("amnesty exit sync failed", receipt["detail"])
        self.assertEqual(ledger_path.read_bytes(), ledger_before,
                         "ledger not restored after a failed amnesty sync")
        # pin_ledger keeps a sabotage-shaped body but NEVER a FIX-464 exit
        # comment for the fixture row — the sync never swapped the file
        # (the copied module may carry real-tree FIX-464 comments for other
        # rows; the fixture-targeted one is the discriminator).
        self.assertNotRegex(
            self_path.read_text(encoding="utf-8"),
            r"#\s*pins re-anchor op-[0-9a-f]{32} \(FIX-464\).*fixture_writer_target")

    def test_register_moves_row_out_of_amnesty(self):
        import pin_ledger
        # register's real-life amnesty scenario: an amnesty ghost row for
        # an exemption the ledger no longer carries (or never carried) —
        # the writer re-registers the row and the ghost leaves the set.
        # No ledger row is pre-seeded (ledger_row=False), so register hits
        # a LIVE scan hit and takes the new-file-key branch.
        root = self._mini_root_with_amnesty_row(ledger_row=False)
        ghost = (self._TARGET_REL, 2, self._ACTIVE)
        self.assertIn(ghost, self._mini_amnesty(root))
        receipt, code = pin_ledger.register_exemption(
            root, self._TARGET_REL, 2, self._ACTIVE,
            "FIX-464 register amnesty-exit probe")
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["effect"], "written")
        self.assertEqual(receipt["amnesty_sync"], "written")
        self.assertNotIn(ghost, self._mini_amnesty(root))

    def test_reanchor_idempotent_noop_self_heals_amnesty(self):
        """The FIX-462 gap repair path: an already-anchored entry with a
        GHOST amnesty row heals on the noop branch (effect= idempotent_noop,
        amnesty_sync=written, zero ledger byte change)."""
        import pin_ledger
        root = self._mini_root_with_amnesty_row()
        ghost = (self._TARGET_REL, 2, self._ACTIVE)
        (root / self._TARGET_REL).write_text(
            "# drift a\n# drift b\n" + self._TARGET_BODY, encoding="utf-8")
        receipt, code = pin_ledger.reanchor_exemption(
            root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 0, receipt)
        self.assertNotIn(ghost, self._mini_amnesty(root))
        # reintroduce the ghost by hand (the drift being repaired), then
        # re-run the same command — noop on the ledger, sync on the amnesty
        self_path = root / pin_ledger.SELF_REL
        stext = self_path.read_text(encoding="utf-8")
        anchor = "DELIVERY_AMNESTY_ENTRIES = frozenset({\n"
        stext = stext.replace(
            anchor, anchor + '    ("{0}", 2, "{1}"),\n'.format(
                self._TARGET_REL, self._ACTIVE), 1)
        self_path.write_text(stext, encoding="utf-8")
        self.assertIn(ghost, self._mini_amnesty(root))
        ledger_path = root / pin_ledger.LEDGER_REL
        ledger_before = ledger_path.read_bytes()
        receipt, code = pin_ledger.reanchor_exemption(
            root, self._TARGET_REL, 2, 4)
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["effect"], "idempotent_noop")
        self.assertEqual(receipt["amnesty_sync"], "written")
        self.assertEqual(ledger_path.read_bytes(), ledger_before)
        self.assertNotIn(ghost, self._mini_amnesty(root))


class PinsLedgerRealTreeContractTests(unittest.TestCase):
    """FIX-462 — the delivery amnesty snapshot covers every live row."""

    def test_real_tree_face_is_clean_amnesty_complete(self):
        import pin_ledger
        issues, status = pin_ledger.exemption_face_issues(_REPO_ROOT)
        self.assertEqual(status, "PASS")
        self.assertEqual(issues, [],
                         "delivery amnesty snapshot incomplete: every live "
                         "row must be either amnesty-covered or "
                         "provenance-attributed")

    def test_amnesty_snapshot_matches_live_ledger_exactly(self):
        """FIX-464 — the snapshot/live invariant, not literal equality.

        The FIX-462 literal-equality form (amnesty == live) was only
        satisfiable while the writer had never really written: the first
        machine write ADDS a provenance-attributed live row outside the
        amnesty (by design — machine rows never need amnesty cover), so
        equality was a latent contradiction.  The drift contract it
        actually wanted is the two-sided invariant:

          * no GHOST rows — amnesty ⊆ live (a row the writer moved/removed
            must leave the frozen set; enforced by _sync_amnesty_exit),
          * no unattributed rows — live − amnesty ⊆ rows carrying a pins
            provenance comment (face 6 semantics; hand edits surface here).
        """
        import pin_ledger
        live = {(rel, ln, tok)
                for rel, entries in version_checks.STATIC_PIN_EXEMPTIONS.items()
                for ln, tok, _reason in entries}
        amnesty = pin_ledger.DELIVERY_AMNESTY_ENTRIES
        ghosts = amnesty - live
        self.assertFalse(
            ghosts,
            "ghost amnesty rows (writer touched but never left the frozen "
            "set — the FIX-462 gap FIX-464 closes): {0}".format(sorted(ghosts)[:5]))
        ledger_text = (_REPO_ROOT / pin_ledger.LEDGER_REL).read_text(
            encoding="utf-8")
        ledger_lines = ledger_text.splitlines()
        unattributed = []
        for (rel, ln, tok) in (live - amnesty):
            idx = pin_ledger._ledger_entry_lineno(ledger_text, rel, ln, tok)
            if (idx is None or idx < 2
                    or not pin_ledger._PROVENANCE_RE.search(ledger_lines[idx - 2])):
                unattributed.append((rel, ln, tok))
        self.assertFalse(
            unattributed,
            "live rows outside the amnesty without a provenance comment "
            "(hand edit? use pins register/re-anchor): {0}".format(
                sorted(unattributed)[:5]))


if __name__ == "__main__":
    unittest.main()
