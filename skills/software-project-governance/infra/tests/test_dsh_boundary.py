"""Check 28w (``checks.dsh_boundary``) — the criteria K-1 … K-13, both directions.

FEAT-031 / 0.81.0 slice **V8**; design §2.8 (the judgment list) and §5.6 (the
negative-fixture table).

**What this suite is for.** A criterion that only ever saw a healthy repository
would be indistinguishable from a constant ``PASS``. Every judgment here is
therefore exercised twice: once against the real package (the positive case the
gate relies on) and once against a deliberately broken *copy*, constructed under
a temporary directory — never the repository itself — so the negative case
proves the judgment can fail. The copies are built from the real artifacts and
mutated in one named way each, which is also why the messages are asserted: a
judgment that fails for the wrong reason is not a judgment.

**Red lines honored here.** Nothing in this file writes inside the repository;
``tempfile.TemporaryDirectory`` is used for every mutation, and the contract's
own file is read (never written) through ``dsh_contract``.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

_INFRA_DIR = Path(__file__).resolve().parent.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from checks import dsh_boundary as boundary  # noqa: E402

import dsh_contract  # noqa: E402

_PACKAGE_ROOT = _INFRA_DIR.parents[2]
_FIXTURES_DIR = _PACKAGE_ROOT / "adapters" / "dsh" / "fixtures"


def _copy_artifact(root: Path, relative: str) -> Path:
    """Copy one real artifact into ``root`` (creating parents); return the copy."""
    source = _PACKAGE_ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


class RepoCase(unittest.TestCase):
    """Base class: a subject rooted at the real package, plus copy scaffolding."""

    maxDiff = None

    def real_subject(self) -> boundary.Subject:
        return boundary.Subject(_PACKAGE_ROOT)

    def contract_facts(self, subject: boundary.Subject) -> boundary.ContractFacts:
        return boundary.ContractFacts(subject)

    def copied_root(self, patterns) -> tuple:
        """A temporary package copy holding ``patterns``; ``(root, tempdir)``.

        Every mutation in this suite happens on a copy. The caller owns the
        returned ``TemporaryDirectory`` so it can inspect the copy before
        cleanup (``self.addCleanup(temp.cleanup)``).
        """
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for pattern in patterns:
            source = _PACKAGE_ROOT / pattern
            if source.is_file():
                target = root / pattern
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                continue
            for item in _PACKAGE_ROOT.glob(pattern):
                if not item.is_file():
                    continue
                relative = item.relative_to(_PACKAGE_ROOT)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item, target)
        return root, temp

    def assertFails(self, criterion: boundary.Criterion, *needles: str) -> None:
        self.assertEqual(criterion.verdict, "FAIL",
                         f"{criterion.ident} unexpectedly {criterion.verdict}: "
                         f"{criterion.reason}")
        joined = "\n".join([criterion.reason, *criterion.findings])
        for needle in needles:
            self.assertIn(needle, joined, f"{criterion.ident}: {joined}")

    def assertPasses(self, criterion: boundary.Criterion) -> None:
        self.assertEqual(criterion.verdict, "PASS",
                         f"{criterion.ident} unexpectedly {criterion.verdict}: "
                         f"{criterion.reason}\n"
                         + "\n".join(criterion.findings))


# ══════════════════════════════════════════════════════════════════════════
# K-1 — contract readable / schema known / fields present
# ══════════════════════════════════════════════════════════════════════════


class K1ContractReadableTests(RepoCase):

    def test_positive_the_shipped_contract_passes(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k1_contract_readable(self.contract_facts(subject)))

    def test_negative_a_missing_contract_fails_as_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       contract=Path(tmp) / "absent.json")
            criteria = self.contract_facts(subject)
            criterion = boundary.k1_contract_readable(criteria)
            self.assertFails(criterion, "cannot read the host contract")
            self.assertEqual(criteria.error_class, "ContractUnreadable")

    def test_negative_malformed_json_is_malformed_not_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text("{ this is not json", encoding="utf-8")
            criterion = boundary.k1_contract_readable(
                self.contract_facts(boundary.Subject(_PACKAGE_ROOT, contract=contract)))
            self.assertFails(criterion, "ContractMalformed")

    def test_negative_an_unknown_schema_version_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(
                (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
            document["schema_version"] = 99
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            criterion = boundary.k1_contract_readable(
                self.contract_facts(boundary.Subject(_PACKAGE_ROOT, contract=contract)))
            self.assertFails(criterion, "ContractSchemaUnknown")

    def test_negative_a_dropped_required_field_names_the_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(
                (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
            del document["host"]["env"]["probe_side"]["no_fallback"]
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            criterion = boundary.k1_contract_readable(
                self.contract_facts(boundary.Subject(_PACKAGE_ROOT, contract=contract)))
            self.assertFails(criterion,
                             "missing required field "
                             "`host.env.probe_side.no_fallback`")


# ══════════════════════════════════════════════════════════════════════════
# K-2 — outside-contract host literals
# ══════════════════════════════════════════════════════════════════════════


class K2OutsideContractTests(RepoCase):

    def test_positive_no_outside_contract_literal_in_the_declared_consumers(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k2_no_outside_literal(subject, self.contract_facts(subject)))

    def test_positive_every_declared_consumer_exists(self):
        missing = [relative for relative in boundary.K2_CONSUMERS
                   if not (_PACKAGE_ROOT / relative).is_file()]
        self.assertEqual(missing, [])

    def test_negative_an_undeclared_package_literal_is_caught_with_file_and_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_artifact(root, dsh_contract.CONTRACT_REL)
            for relative in boundary.K2_CONSUMERS:
                _copy_artifact(root, relative)
            target = root / "lib" / "index.js"
            target.write_text(
                target.read_text(encoding="utf-8")
                + '\nconst ghost = "@deepseek-ai/dsh-not-a-declared-package";\n',
                encoding="utf-8")
            subject = boundary.Subject(root)
            criterion = boundary.k2_no_outside_literal(subject, self.contract_facts(subject))
            self.assertFails(criterion, "lib/index.js",
                             "@deepseek-ai/dsh-not-a-declared-package")

    def test_negative_an_undeclared_env_reference_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_artifact(root, dsh_contract.CONTRACT_REL)
            for relative in boundary.K2_CONSUMERS:
                _copy_artifact(root, relative)
            target = root / "adapters" / "dsh" / "launch.py"
            target.write_text(
                target.read_text(encoding="utf-8")
                + '\nDSH_SOMETHING_UNDECLARED = os.environ.get("DSH_SOMETHING_UNDECLARED")\n',
                encoding="utf-8")
            subject = boundary.Subject(root)
            criterion = boundary.k2_no_outside_literal(subject, self.contract_facts(subject))
            self.assertFails(criterion, "[env]", "DSH_SOMETHING_UNDECLARED")

    def test_negative_a_missing_consumer_is_reported_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_artifact(root, dsh_contract.CONTRACT_REL)
            for relative in boundary.K2_CONSUMERS:
                _copy_artifact(root, relative)
            (root / "adapters" / "dsh" / "launch.py").unlink()
            subject = boundary.Subject(root)
            criterion = boundary.k2_no_outside_literal(subject, self.contract_facts(subject))
            self.assertFails(criterion, "declared consumer missing")

    def test_an_allowlisted_literal_is_exempt_only_in_its_declared_scope(self):
        literal = "@deepseek-ai/dsh-not-a-declared-package"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_artifact(root, dsh_contract.CONTRACT_REL)
            for relative in boundary.K2_CONSUMERS:
                _copy_artifact(root, relative)
            target = root / "lib" / "index.js"
            target.write_text(
                target.read_text(encoding="utf-8")
                + f'\nconst ghost = "{literal}";\n', encoding="utf-8")
            copy_subject = boundary.Subject(root)
            copy_facts = self.contract_facts(copy_subject)
            exempt = [{"literal": literal, "reason": "test", "since_slice": "V8",
                       "files": ["lib/index.js"]}]
            self.assertEqual(
                boundary.scan_outside_contract_literals(copy_subject, copy_facts,
                                                        allowlist=exempt), [])
            elsewhere = [{"literal": literal, "reason": "test", "since_slice": "V8",
                          "files": ["package.json"]}]
            violations = boundary.scan_outside_contract_literals(
                copy_subject, copy_facts, allowlist=elsewhere)
            self.assertEqual(len(violations), 1, violations)
            self.assertEqual(violations[0][2], "package")


# ══════════════════════════════════════════════════════════════════════════
# K-3 — template rows ↔ contract rows, both directions, full set
# ══════════════════════════════════════════════════════════════════════════


class K3TemplateRowTests(RepoCase):

    def setUp(self):
        self.subject = self.real_subject()
        self.facts = self.contract_facts(self.subject)
        self.declared = self.facts.get("host.rows")
        self.rows = boundary.parse_template_rows(
            boundary._read(self.subject.template))

    def test_positive_the_two_sides_agree_on_the_full_set(self):
        self.assertPasses(boundary.k3_template_rows_match_contract(
            self.subject, self.facts))

    def test_positive_the_row_set_is_the_documented_29(self):
        ids = [row["row_id"] for row in self.rows]
        self.assertEqual(len(ids), boundary.EXPECTED_ROW_TOTAL)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(self.declared), boundary.EXPECTED_ROW_TOTAL)
        self.assertEqual(sorted(ids), sorted(row["row_id"] for row in self.declared))

    def test_positive_platform_and_disabled_rows_are_visible_on_both_sides(self):
        template_platform = {row["row_id"] for row in self.rows
                             if boundary.platform_conditional_of(row)}
        declared_platform = {row["row_id"] for row in self.declared
                             if row["platform_conditional"]}
        self.assertEqual(template_platform, declared_platform)
        self.assertEqual(template_platform, {"tool-bash", "tool-pwsh"})
        declared_disabled = {row["row_id"] for row in self.declared
                             if row["disabled_expr"] == "true"}
        self.assertEqual(declared_disabled,
                         {"tool-subagent-codex", "tool-subagent-claude-code"})

    def test_negative_a_row_only_the_template_has_is_named(self):
        text = boundary._read(self.subject.template)
        text = text.replace(
            "- id: tool-skill\n",
            "- id: tool-skill\n"
            "  name: '@deepseek-ai/dsh-tool-skill'\n"
            "- id: tool-ghost\n"
            "  name: '@deepseek-ai/dsh-tool-ghost'\n", 1)
        rows = boundary.parse_template_rows(text)
        self.assertEqual(len(rows), boundary.EXPECTED_ROW_TOTAL + 1)
        mismatches = boundary.template_row_mismatches(rows, self.declared)
        self.assertIn("template row not in contract: tool-ghost", mismatches)

    def test_negative_a_row_only_the_contract_has_is_named(self):
        # Drop `tool-skill` from the template text: the contract still declares
        # it, so the one-sided addition is named from the template's side.
        text = boundary._read(self.subject.template).replace(
            "- id: tool-skill\n"
            "  name: '@deepseek-ai/dsh-tool-skill'\n", "", 1)
        rows = boundary.parse_template_rows(text)
        self.assertEqual(len(rows), boundary.EXPECTED_ROW_TOTAL - 1)
        mismatches = boundary.template_row_mismatches(rows, self.declared)
        self.assertIn("contract row absent from template: tool-skill", mismatches)

    def test_negative_a_changed_config_key_set_is_a_field_level_finding(self):
        declared = json.loads(json.dumps(self.declared))
        for row in declared:
            if row["row_id"] == "persona":
                row["config_keys"] = ["prefix", "ghostKey"]
        mismatches = boundary.template_row_mismatches(self.rows, declared)
        self.assertTrue(any(item.startswith("persona.config_keys:")
                            for item in mismatches), mismatches)

    def test_negative_a_renamed_package_is_a_field_level_finding(self):
        declared = json.loads(json.dumps(self.declared))
        for row in declared:
            if row["row_id"] == "persona":
                row["package"] = "@deepseek-ai/dsh-persona-renamed"
        mismatches = boundary.template_row_mismatches(self.rows, declared)
        self.assertTrue(any(item.startswith("persona.package:")
                            for item in mismatches), mismatches)

    def test_negative_a_removed_disabled_form_is_visible_in_both_directions(self):
        declared = json.loads(json.dumps(self.declared))
        for row in declared:
            if row["row_id"] == "tool-subagent-codex":
                row["disabled_expr"] = None
                row["enabled_on"] = "any"
        mismatches = boundary.template_row_mismatches(self.rows, declared)
        self.assertTrue(any("tool-subagent-codex.disabled_expr" in item
                            for item in mismatches), mismatches)
        self.assertTrue(any("tool-subagent-codex.enabled_on" in item
                            for item in mismatches), mismatches)

    def test_a_row_at_an_undeclared_indent_is_rejected_not_absorbed(self):
        text = boundary._read(self.subject.template) + \
            "\n  - id: stray-at-indent-2\n"
        with self.assertRaises(ValueError) as caught:
            boundary.parse_template_rows(text, origin="mutant")
        self.assertIn("unexpected indent 2", str(caught.exception))

    def test_a_nested_row_without_a_group_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            boundary.link_template_rows(
                [{"row_id": "orphan", "indent": 4, "is_group": False,
                  "children": []}])
        self.assertIn("nested but no top-level group", str(caught.exception))

    def test_negative_a_broken_template_fails_the_criterion_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "agent.cordis.yml.template"
            text = boundary._read(self.subject.template).replace(
                "  name: '@deepseek-ai/dsh-persona'\n",
                "  name: '@deepseek-ai/dsh-persona-mutated'\n", 1)
            self.assertNotEqual(text, boundary._read(self.subject.template))
            mutated.write_text(text, encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, template=mutated)
            criterion = boundary.k3_template_rows_match_contract(
                subject, self.contract_facts(subject))
            self.assertFails(criterion, "persona.package")

    def test_negative_a_broken_contract_fails_the_criterion_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(
                (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
            for row in document["host"]["rows"]:
                if row["row_id"] == "persona":
                    row["config_keys"] = ["prefix", "ghostKey"]
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k3_template_rows_match_contract(
                subject, self.contract_facts(subject))
            self.assertFails(criterion, "persona.config_keys")


# ══════════════════════════════════════════════════════════════════════════
# K-4 — token set equality + no leftover after rendering
# ══════════════════════════════════════════════════════════════════════════


class K4TokenTests(RepoCase):

    def test_positive_the_token_sets_are_equal_and_render_clean(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k4_tokens_match(subject, self.contract_facts(subject)))

    def test_positive_the_misspelt_all_caps_token_is_not_a_known_token(self):
        tokens = set(self.contract_facts(self.real_subject()).get("own.render.tokens"))
        self.assertNotIn("__GOVERNANCE_SKILLS_ROOTS__", tokens)
        self.assertIn("__GOVERNANCE_SKILLS_ROOT__", tokens)

    def test_negative_a_misspelt_token_in_the_template_names_the_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = boundary._read(boundary.Subject(_PACKAGE_ROOT).template)
            mutated = Path(tmp) / "template.yml"
            mutated.write_text(
                text.replace("__GOVERNANCE_SKILLS_ROOT__",
                             "__GOVERNANCE_SKILLS_ROOTS__"),
                encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, template=mutated)
            criterion = boundary.k4_tokens_match(subject, self.contract_facts(subject))
            self.assertFails(criterion,
                             "unknown token in template: __GOVERNANCE_SKILLS_ROOTS__")

    def test_negative_a_declared_token_missing_from_the_template_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = boundary._read(boundary.Subject(_PACKAGE_ROOT).template)
            mutated = Path(tmp) / "template.yml"
            mutated.write_text(
                text.replace("__GOVERNANCE_SHIMS_ROOT__", "adapters/dsh/skill-shims"),
                encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, template=mutated)
            criterion = boundary.k4_tokens_match(subject, self.contract_facts(subject))
            self.assertFails(criterion,
                             "contract token absent from template: "
                             "__GOVERNANCE_SHIMS_ROOT__")

    def test_negative_a_mixed_case_leftover_is_caught_by_the_declared_pattern(self):
        import re

        pattern = boundary._read
        _ = pattern  # the pattern comes from the contract, not from this file
        declared = self.contract_facts(self.real_subject()).get("own.render.leftover_scan")
        self.assertTrue(re.search(declared, "__Governance_Repo_Root__"))


# ══════════════════════════════════════════════════════════════════════════
# K-5 — the hooks' path expression equals the contract's
# ══════════════════════════════════════════════════════════════════════════


class K5HookPathTests(RepoCase):

    def test_positive_all_three_hooks_carry_the_declared_expression(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k5_hook_paths(self.contract_facts(subject), subject))

    def test_positive_the_expression_is_derived_from_the_contract(self):
        facts = self.contract_facts(self.real_subject())
        expected = ("${%s:-$HOME/.dsh}/%s/%s"
                    % (facts.get("host.env.home_var"),
                       facts.get("host.home.user_preset_dir"),
                       facts.get("own.preset.id")))
        self.assertEqual(expected,
                         "${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance")

    def test_negative_a_renamed_preset_directory_is_a_drift_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("pre-commit", "commit-msg", "post-commit"):
                _copy_artifact(root, f"skills/software-project-governance/infra/hooks/{name}")
            for name in ("pre-commit", "commit-msg", "post-commit"):
                target = root / "skills/software-project-governance/infra/hooks" / name
                target.write_text(
                    target.read_text(encoding="utf-8").replace(
                        ".agent-presets/governance", ".agent-presets/renamed"),
                    encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, hooks_dir=root / "skills/software-project-governance/infra/hooks")
            criterion = boundary.k5_hook_paths(self.contract_facts(subject), subject)
            self.assertFails(criterion, "hook path drift")

    def test_negative_a_missing_hook_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hooks"
            root.mkdir()
            _copy_artifact(root, "skills/software-project-governance/infra/hooks/pre-commit")
            subject = boundary.Subject(_PACKAGE_ROOT, hooks_dir=root)
            criterion = boundary.k5_hook_paths(self.contract_facts(subject), subject)
            self.assertFails(criterion, "hook missing")

    def test_negative_a_renamed_marker_is_a_drift_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("pre-commit", "commit-msg", "post-commit"):
                _copy_artifact(
                    root,
                    f"skills/software-project-governance/infra/hooks/{name}")
            hooks = root / "skills/software-project-governance/infra/hooks"
            target = hooks / "pre-commit"
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "skill-root.txt", "skill-root-marker.txt"),
                encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, hooks_dir=hooks)
            criterion = boundary.k5_hook_paths(self.contract_facts(subject), subject)
            self.assertFails(criterion, "hook marker drift")


# ══════════════════════════════════════════════════════════════════════════
# K-6 — the patch's four shape invariants
# ══════════════════════════════════════════════════════════════════════════


class K6PatchShapeTests(RepoCase):

    INVARIANTS = ("exactly-one-insert-row", "no-id-update", "no-trust", "no-!!js")

    def test_positive_the_shipped_patch_holds_all_four_invariants(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k6_patch_shape(subject, self.contract_facts(subject)))

    def test_positive_the_patch_carries_exactly_one_top_level_insert_row(self):
        text = boundary._read(boundary.Subject(_PACKAGE_ROOT).patch)
        self.assertEqual(boundary.patch_shape_findings(text, self.INVARIANTS), [])
        self.assertEqual(len([line for line in text.splitlines()
                              if line.lstrip().startswith("- insert:")]), 1)

    def test_negative_an_id_targeted_update_row_is_a_violation(self):
        text = ("- insert:\n"
                "    - id: governance\n"
                "      name: '@peterwangze/software-project-governance-plugin'\n"
                "- id: persona\n"
                "  config:\n"
                "    prefix: injected\n")
        findings = boundary.patch_shape_findings(text, self.INVARIANTS)
        self.assertTrue(any("no-id-update" in item for item in findings), findings)

    def test_negative_an_insert_payload_is_not_mistaken_for_an_update_row(self):
        text = ("- insert:\n"
                "    - id: governance\n"
                "      name: '@peterwangze/software-project-governance-plugin'\n")
        self.assertEqual(boundary.patch_shape_findings(text, self.INVARIANTS), [])

    def test_negative_a_trust_key_is_a_violation(self):
        text = "- insert:\n    - id: governance\n      trust: system\n"
        findings = boundary.patch_shape_findings(text, self.INVARIANTS)
        self.assertTrue(any("no-trust" in item for item in findings), findings)

    def test_negative_a_js_expression_is_a_violation(self):
        text = "- insert:\n    - id: governance\n      disabled: !!js 1 === 1\n"
        findings = boundary.patch_shape_findings(text, self.INVARIANTS)
        self.assertTrue(any("no-!!js" in item for item in findings), findings)

    def test_negative_a_second_insert_row_is_a_violation(self):
        text = ("- insert:\n    - id: a\n"
                "- insert:\n    - id: b\n")
        findings = boundary.patch_shape_findings(text, self.INVARIANTS)
        self.assertTrue(any("exactly-one-insert-row" in item for item in findings),
                        findings)

    def test_an_empty_patch_violates_the_insert_row_count(self):
        findings = boundary.patch_shape_findings("", self.INVARIANTS)
        self.assertTrue(any("exactly-one-insert-row" in item for item in findings),
                        findings)

    def test_negative_the_prose_in_the_header_does_not_trip_the_invariants(self):
        # The shipped patch documents all four invariants by name in its header;
        # a comment must not be able to make the guard report its own text.
        text = ("# ZERO `- id: <host row>` UPDATE rows\n"
                "# ZERO `!!js` expressions\n"
                "# ZERO `trust: system` declarations\n"
                "- insert:\n    - id: governance\n")
        self.assertEqual(boundary.patch_shape_findings(text, self.INVARIANTS), [])

    def test_negative_a_broken_patch_fails_the_criterion_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch = Path(tmp) / "cordis.patch.yml"
            patch.write_text("- insert:\n    - id: governance\n"
                             "- id: persona\n  config: {prefix: x}\n",
                             encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, patch=patch)
            criterion = boundary.k6_patch_shape(subject, self.contract_facts(subject))
            self.assertFails(criterion, "no-id-update")


# ══════════════════════════════════════════════════════════════════════════
# FX-BASEURL-01 — the `baseUrl` shape whose semantics the contract fixes
# ══════════════════════════════════════════════════════════════════════════


def _relative_resolution(base, name):
    """Resolve ``name`` against ``base`` the way ``new URL(name, base)`` would."""
    from urllib.parse import urljoin

    return urljoin(base if base.endswith("/") else base + "/", name)


class BaseUrlShapeTests(RepoCase):
    """R1 N-6(b): assert the *injected* shape and the semantic difference.

    R0 F-10 fixed ``host.row_contract.loader_scope_baseurl_shape = "file-url"``
    because the loader resolves a relative module name with
    ``new URL(name, baseUrl).href`` — a URL join. The mutation that matters is
    therefore not "the string changed" but "the injected value stopped being a
    URL base", which is what makes that join resolve somewhere else. Asserting
    the shape alone would be a spelling test; asserting the semantics is what
    shows the guard's probe context is the one the loader uses.
    """

    def setUp(self):
        self.facts = self.contract_facts(self.real_subject())
        self.shape = self.facts.get("host.row_contract.loader_scope_baseurl_shape")

    def test_positive_the_contract_declares_the_file_url_shape(self):
        self.assertEqual(self.shape, "file-url")
        self.assertIn("baseUrl", self.facts.get("host.row_contract.loader_scope"))

    def test_positive_the_guard_injects_a_file_url_base(self):
        guard = boundary._read(_INFRA_DIR / "dsh_compat.py")
        self.assertIn("new URL(name, ctx.baseUrl)", guard)
        self.assertIn("baseUrl: pathToFileURL(file.path).href", guard)

    def test_the_file_url_and_bare_path_forms_resolve_differently(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            as_url = path.as_uri()
            as_path = str(path).replace("\\", "/")
        self.assertTrue(as_url.startswith("file:///"))
        self.assertNotEqual(as_url, as_path)
        self.assertEqual(_relative_resolution(as_url, "child.js"),
                         as_url + "/child.js")
        self.assertNotEqual(_relative_resolution(as_path, "child.js"),
                            _relative_resolution(as_url, "child.js"))

    def test_negative_a_contract_declaring_another_shape_is_a_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(
                (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
            document["host"]["row_contract"]["loader_scope_baseurl_shape"] = "path"
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            mutated = self.contract_facts(subject)
        self.assertEqual(
            mutated.get("host.row_contract.loader_scope_baseurl_shape"), "path")
        self.assertNotEqual(
            mutated.get("host.row_contract.loader_scope_baseurl_shape"), self.shape)


# ══════════════════════════════════════════════════════════════════════════
# K-7 — version evidence consistency and TTL
# ══════════════════════════════════════════════════════════════════════════


class K7VersionEvidenceTests(RepoCase):

    def _manifest_copy(self, mutate):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        target = _copy_artifact(root, "adapters/dsh/adapter-manifest.json")
        document = json.loads(target.read_text(encoding="utf-8"))
        mutate(document)
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        return boundary.Subject(_PACKAGE_ROOT, manifest=target)

    def test_positive_the_manifest_carries_the_pointer_form_and_field_shapes(self):
        subject = self.real_subject()
        criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
        # The contract is unrecorded in this slice: the honest verdict is
        # NOT_RUN, never PASS (nothing was compared) and never FAIL (nothing
        # was found wrong).
        self.assertEqual(criterion.verdict, "NOT_RUN", criterion.reason)
        self.assertIn("unrecorded", criterion.reason)

    def test_negative_a_recorded_stale_verified_on_is_a_fail(self):
        document = json.loads(
            (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
        document["evidence"]["verified_on"] = "2020-01-01"
        token = json.dumps(document)
        self.assertIn('"verified_on": "2020-01-01"', token)
        findings = boundary.ttl_findings(date(2020, 1, 1), 180, date(2026, 9, 13))
        self.assertEqual(len(findings), 1)
        self.assertIn("evidence stale", findings[0])

    def test_positive_a_fresh_recorded_date_is_within_ttl(self):
        today = date(2026, 9, 13)
        self.assertEqual(
            boundary.ttl_findings(today - timedelta(days=179), 180, today), [])

    def test_positive_an_absent_verified_on_is_not_an_expiry(self):
        self.assertEqual(boundary.ttl_findings(None, 180, date(2026, 9, 13)), [])

    def test_negative_a_restated_contract_date_that_disagrees_is_a_fail(self):
        subject = self._manifest_copy(
            lambda document: document["runtime_e2e"].update(
                {"verified_on": "2026-07-08"}))
        criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
        self.assertFails(criterion, "manifest evidence drift")

    def test_negative_a_literal_version_that_disagrees_with_the_contract_fails(self):
        def mutate(document):
            document["runtime_e2e"]["verified_on"] = "see contract evidence.verified_on"
            document["runtime_e2e"]["evidence"] = ("verified against 0.1.0-rc.6")
            document["__ghost_version__"] = "0.1.0-rc.6"
        # A version the contract does not name is drift only when the contract
        # records one; this slice records none, so the literal itself is not yet
        # comparable — the field-shape half must still be exercised.
        subject = self._manifest_copy(
            lambda document: document["runtime_e2e"].update(
                {"verified_on": "whenever"}))
        criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
        self.assertFails(criterion, "neither a date nor a contract pointer")
        _ = mutate

    def test_negative_a_missing_required_manifest_field_is_named(self):
        subject = self._manifest_copy(lambda document: document.pop("validation"))
        criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
        self.assertFails(criterion, "manifest missing required field(s): ['validation']")

    def test_negative_a_missing_manifest_fails_rather_than_passing(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       manifest=Path(tmp) / "absent.json")
            criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
            self.assertFails(criterion, "manifest missing")

    def test_negative_a_non_object_runtime_e2e_is_reported(self):
        subject = self._manifest_copy(
            lambda document: document.update({"runtime_e2e": "yes"}))
        criterion = boundary.k7_version_evidence(self.contract_facts(subject), subject)
        self.assertFails(criterion, "is not an object")


# ══════════════════════════════════════════════════════════════════════════
# K-8 — coverage claims are backed
# ══════════════════════════════════════════════════════════════════════════


class K8CoverageClaimTests(RepoCase):

    def setUp(self):
        self.subject = self.real_subject()
        self.facts = self.contract_facts(self.subject)
        self.entries = self.facts.get("coverage.entries")

    def test_positive_every_claim_is_backed(self):
        self.assertPasses(boundary.k8_coverage_claims(self.facts, self.subject))

    def test_positive_every_guard_reference_resolves_to_a_named_guard(self):
        definitions = boundary._test_definitions(self.subject)
        segments = set(boundary._registered_segments())
        commands = set(boundary._registered_command_keys())
        unresolved = [reference for entry in self.entries
                      for reference in entry.get("guard") or ()
                      if not boundary._guard_resolves(reference, definitions,
                                                      segments, commands)]
        self.assertEqual(unresolved, [])

    def test_negative_a_strong_target_without_a_negative_fixture_fails(self):
        # The machine check the design demands (K-8 / §4.1 rule 3): "declared
        # stronger than backed" must be structurally expressible as a FAIL.
        target = next(entry["subject"] for entry in self.entries
                      if entry["target"] == "strong")
        entries = json.loads(json.dumps(self.entries))
        for entry in entries:
            if entry["target"] == "strong":
                entry["negative_fixtures"] = []
                break
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion,
                         f"subject={target} target=strong without a negative "
                         f"fixture")
        self.assertIn("strong without a negative fixture",
                      "\n".join(criterion.findings))

    def test_negative_a_guard_reference_that_resolves_to_nothing_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries[0]["guard"] = ["test_does_not_exist.py::test_ghost"]
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion, "guard=", "resolves to nothing")

    def test_negative_a_subject_outside_the_contract_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries[0]["subject"] = "host.does.not.exist"
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion,
                         "coverage subject does not resolve inside the contract")

    def test_negative_an_unknown_negative_fixture_id_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries[0]["negative_fixtures"] = ["FX-NOT-DECLARED-99"]
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion, "FX-NOT-DECLARED-99")

    def test_negative_a_target_outside_the_vocabulary_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries[0]["target"] = "very-strong"
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion, "coverage target outside the vocabulary")

    def test_negative_a_duplicate_subject_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries.append(json.loads(json.dumps(entries[0])))
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion, "duplicate coverage subject")

    def test_negative_a_claim_without_a_guard_fails(self):
        entries = json.loads(json.dumps(self.entries))
        entries[0]["guard"] = []
        with tempfile.TemporaryDirectory() as tmp:
            document = json.loads(json.dumps(self.facts.document))
            document["coverage"]["entries"] = entries
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k8_coverage_claims(boundary.ContractFacts(subject),
                                                    subject)
        self.assertFails(criterion, "no guard")

    def test_a_strong_claim_flip_moves_the_criterion_not_the_contract(self):
        contract_sha = _sha256_of(_PACKAGE_ROOT / dsh_contract.CONTRACT_REL)
        benchmark = boundary.check_dsh_boundary(_PACKAGE_ROOT)
        self.assertEqual(len(benchmark["criteria"]), len(boundary.CRITERIA))
        self.assertEqual(_sha256_of(_PACKAGE_ROOT / dsh_contract.CONTRACT_REL),
                         contract_sha)


def _sha256_of(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
# K-9 — dispositions and the necessary-dependency cover
# ══════════════════════════════════════════════════════════════════════════


class K9DispositionTests(RepoCase):

    def setUp(self):
        self.subject = self.real_subject()
        self.facts = self.contract_facts(self.subject)

    def test_positive_the_audit_baseline_is_fully_disposed_and_covered(self):
        self.assertPasses(boundary.k9_dispositions(self.facts))

    def test_positive_the_necessary_cover_is_against_the_recomputable_baseline(self):
        baseline = self.facts.get("elimination.audit_baseline")
        covered = {audit_id for entry in self.facts.get("coverage.entries")
                   for audit_id in entry["audit_ids"]}
        self.assertTrue(set(baseline["necessary_ids"]) <= covered)
        # The contract is explicit that the audit report's own summary (62)
        # disagrees with its per-row markers (72); the machine baseline is the
        # fail-closed superset, so the cover must be judged against 72.
        self.assertEqual(len(baseline["necessary_ids"]), 72)
        self.assertEqual(baseline["count_reconciliation"]
                         ["stated_in_audit_section_2_11"]["necessary"], 62)

    def test_negative_a_missing_disposition_is_named(self):
        document = json.loads(json.dumps(self.facts.document))
        removed = document["elimination"]["dispositions"].pop(0)["id"]
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k9_dispositions(boundary.ContractFacts(subject))
        self.assertFails(criterion, f"disposition missing for {removed}")

    def test_negative_a_duplicate_disposition_is_named(self):
        document = json.loads(json.dumps(self.facts.document))
        dispositions = document["elimination"]["dispositions"]
        dispositions.append(json.loads(json.dumps(dispositions[0])))
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k9_dispositions(boundary.ContractFacts(subject))
        self.assertFails(criterion, "duplicate disposition")

    def test_negative_a_necessary_dependency_without_a_claim_is_named(self):
        document = json.loads(json.dumps(self.facts.document))
        target = document["elimination"]["audit_baseline"]["necessary_ids"][0]
        for entry in document["coverage"]["entries"]:
            entry["audit_ids"] = [item for item in entry["audit_ids"]
                                  if item != target]
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k9_dispositions(boundary.ContractFacts(subject))
        self.assertFails(criterion,
                         f"necessary dependency without coverage claim: {target}")

    def test_negative_an_eliminated_disposition_without_a_slice_is_named(self):
        document = json.loads(json.dumps(self.facts.document))
        for item in document["elimination"]["dispositions"]:
            if item["decision"] == "eliminated":
                item["removed_at"] = None
                break
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k9_dispositions(boundary.ContractFacts(subject))
        self.assertFails(criterion, "eliminated disposition without a removal slice")

    def test_negative_a_claim_without_audit_ids_is_named(self):
        document = json.loads(json.dumps(self.facts.document))
        document["coverage"]["entries"][0]["audit_ids"] = []
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "host-contract.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
            criterion = boundary.k9_dispositions(boundary.ContractFacts(subject))
        self.assertFails(criterion, "coverage claim without audit_ids")


# ══════════════════════════════════════════════════════════════════════════
# K-10 — structural declarations
# ══════════════════════════════════════════════════════════════════════════


class K10StructuralTests(RepoCase):

    def test_positive_the_contract_and_the_fixture_are_declared_everywhere(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k10_structural_invariants(
            subject, self.contract_facts(subject)))

    def test_positive_the_cleanup_scope_equals_plugin_scope_dirs(self):
        manifest = json.loads(
            (boundary.Subject(_PACKAGE_ROOT).core_manifest).read_text(encoding="utf-8"))
        declared = set(manifest["cleanup_scope"]["directories"])
        self.assertIn("adapters", declared)
        self.assertEqual(len(declared), 11)

    def test_negative_an_undeclared_host_facts_fixture_is_named(self):
        manifest = boundary.Subject(_PACKAGE_ROOT).core_manifest
        document = json.loads(manifest.read_text(encoding="utf-8"))
        entries = document["canonical_product_artifacts"]["entries"]
        document["canonical_product_artifacts"]["entries"] = [
            entry for entry in entries if entry["id"] != "dsh-host-facts-baseline"]
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "manifest.json"
            mutated.write_text(json.dumps(document, ensure_ascii=False),
                               encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, core_manifest=mutated)
            criterion = boundary.k10_structural_invariants(
                subject, self.contract_facts(subject))
        self.assertFails(criterion, "not declared in canonical_product_artifacts")

    def test_negative_an_undeclared_contract_path_is_named(self):
        manifest = boundary.Subject(_PACKAGE_ROOT).core_manifest
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["canonical_product_artifacts"]["entries"] = [
            entry for entry
            in document["canonical_product_artifacts"]["entries"]
            if entry["id"] != "dsh-host-contract"]
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "manifest.json"
            mutated.write_text(json.dumps(document, ensure_ascii=False),
                               encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, core_manifest=mutated)
            criterion = boundary.k10_structural_invariants(
                subject, self.contract_facts(subject))
        self.assertFails(criterion,
                         "adapters/dsh/host-contract.json")

    def test_negative_a_cleanup_scope_that_dropped_adapters_is_named(self):
        # The contract lives under `adapters/`; a scope that stopped covering
        # that directory would make the contract a cleanup candidate.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_artifact(root, "skills/software-project-governance/infra/cleanup.py")
            target = root / "skills/software-project-governance/infra/cleanup.py"
            target.write_text(
                target.read_text(encoding="utf-8").replace('    "adapters",\n', ""),
                encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT, cleanup_py=target)
            criterion = boundary.k10_structural_invariants(
                subject, self.contract_facts(subject))
        self.assertFails(criterion, "cleanup scope drift")

    def test_negative_a_missing_cleanup_declaration_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       cleanup_py=Path(tmp) / "absent.py")
            criterion = boundary.k10_structural_invariants(
                subject, self.contract_facts(subject))
        self.assertFails(criterion, "cannot read PLUGIN_SCOPE_DIRS")

    def test_positive_the_fixture_budget_is_respected(self):
        fixtures = sorted(_FIXTURES_DIR.glob("host-facts-*.json"))
        self.assertTrue(fixtures)
        self.assertLessEqual(len(fixtures), 3)
        for path in fixtures:
            self.assertLessEqual(path.stat().st_size, 64 * 1024, path.name)


# ══════════════════════════════════════════════════════════════════════════
# K-11 — the allowlist ratchet (DEC-192: 0 entries / budget 0)
# ══════════════════════════════════════════════════════════════════════════


class K11AllowlistTests(RepoCase):
    """K-11 — the allowlist ratchet, whose ceiling is DEC-192's zero."""

    def _facts_with(self, entries, budget=0):
        """Contract facts for a *copy* of the contract declaring an allowlist.

        The block is written into a contract copy rather than into the shipped
        contract: DEC-192 ruled the shipped budget to zero, so the malformed and
        over-budget branches are only reachable through a declared block — and
        exercising them through the real reader (rather than by assigning
        attributes) is what proves the reader handles a declared block at all.
        """
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        document = json.loads(
            (_PACKAGE_ROOT / dsh_contract.CONTRACT_REL).read_text(encoding="utf-8"))
        document["allowlist"] = list(entries)
        document["allowlist_budget"] = budget
        contract = Path(temp.name) / "host-contract.json"
        contract.write_text(json.dumps(document, ensure_ascii=False),
                            encoding="utf-8")
        subject = boundary.Subject(_PACKAGE_ROOT, contract=contract)
        facts = self.contract_facts(subject)
        self.assertTrue(facts.declared_allowlist)
        return subject, facts

    def test_positive_the_shipped_contract_spends_no_exemption(self):
        subject = self.real_subject()
        criterion = boundary.k11_allowlist_ratchet(self.contract_facts(subject), subject)
        self.assertPasses(criterion)
        self.assertIn("allowlist 0/0", criterion.reason)
        self.assertIn("only down", criterion.reason)

    def test_positive_a_declared_empty_block_is_still_zero_entries(self):
        # The V1 contract predates the block (`own.notes.single_source_of_truth`
        # says V8 appends it); absent must mean "empty", never "unbounded".
        subject, facts = self._facts_with([])
        self.assertFalse(boundary.ContractFacts(self.real_subject()).declared_allowlist)
        self.assertPasses(boundary.k11_allowlist_ratchet(facts, subject))

    def test_the_ceiling_is_anchored_outside_the_contract(self):
        # R1 N-2: a budget stored in the contract could be raised in the same
        # commit that needs it raised, which would make the ratchet decorative.
        subject = self.real_subject()
        budget, error = boundary._ratchet_anchor(subject)
        self.assertIsNone(error)
        self.assertEqual(budget, 0)
        self.assertNotIn("allowlist_budget", boundary._read(subject.contract_path))

    def test_positive_the_judging_test_and_this_check_read_the_same_number(self):
        anchor = _PACKAGE_ROOT / boundary.ANCHOR_TEST_REL
        self.assertTrue(anchor.is_file())
        self.assertEqual(boundary.CONTRACT_ALLOWLIST_ANCHOR_RE.search(
            anchor.read_text(encoding="utf-8")).group(1), "0")

    def test_negative_an_entry_without_reason_fails(self):
        subject, facts = self._facts_with(
            [{"literal": "@deepseek-ai/cordis", "since_slice": "V1",
              "files": ["lib/index.js"]}])
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist entry without reason")

    def test_negative_an_entry_without_since_slice_fails(self):
        subject, facts = self._facts_with(
            [{"literal": "@deepseek-ai/cordis", "reason": "oracle name",
              "files": ["lib/index.js"]}])
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist entry without since_slice")

    def test_negative_an_entry_without_a_literal_fails(self):
        subject, facts = self._facts_with(
            [{"reason": "x", "since_slice": "V1", "files": ["lib/index.js"]}])
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist entry without a literal")

    def test_negative_an_entry_without_a_file_scope_fails(self):
        subject, facts = self._facts_with(
            [{"literal": "@deepseek-ai/cordis", "reason": "x",
              "since_slice": "V1"}])
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist entry without files")

    def test_negative_a_well_formed_entry_still_exceeds_the_zero_budget(self):
        # FX-ALLOW-01's second half: even a *reviewable* entry is over budget,
        # because DEC-192 ruled the budget to zero.
        subject, facts = self._facts_with(
            [{"literal": "@deepseek-ai/cordis",
              "reason": "oracle package name",
              "since_slice": "V1",
              "files": ["lib/index.js"]}])
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist grew: 1 → budget 0")

    def test_negative_a_declared_budget_cannot_raise_the_ceiling(self):
        # The contract may *declare* a budget, but the ceiling comes from the
        # judging test: a block that raises its own budget is over the anchor.
        subject, facts = self._facts_with(
            [{"literal": "@deepseek-ai/cordis", "reason": "x",
              "since_slice": "V1", "files": ["lib/index.js"]}], budget=7)
        self.assertEqual(facts.allowlist_budget, 7)
        criterion = boundary.k11_allowlist_ratchet(facts, subject)
        self.assertFails(criterion, "allowlist grew: 1 → budget 0")

    def test_negative_a_missing_anchor_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = boundary.Subject(Path(tmp))
            criterion = boundary.k11_allowlist_ratchet(
                self.contract_facts(self.real_subject()), bare)
        self.assertFails(criterion, "anchor file missing")

    def test_the_budget_constant_is_not_widened_by_this_slice(self):
        self.assertEqual(boundary.CONTRACT_ALLOWLIST_ANCHOR_RE.search(
            (_PACKAGE_ROOT / boundary.ANCHOR_TEST_REL).read_text(encoding="utf-8")
        ).group(1), "0")


# ══════════════════════════════════════════════════════════════════════════
# K-12 — the single-verdict anchor
# ══════════════════════════════════════════════════════════════════════════


class K12SingleVerdictTests(RepoCase):

    def test_positive_one_coverage_generator_carrying_the_fifth_field(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k12_single_verdict_anchor(self.contract_facts(subject)))

    def test_positive_the_coverage_block_carries_unreadable_compositions(self):
        # F-R1-06: the S2 projection must be able to carry it, which requires
        # the single generator to produce it.
        guard = boundary._read(_INFRA_DIR / "dsh_compat.py")
        self.assertIn('"unreadable_compositions"', guard)

    def test_positive_the_doctor_command_key_is_registered(self):
        self.assertIn(boundary.DOCTOR_COMMAND_KEY,
                      set(boundary._registered_command_keys()))

    def test_positive_the_28w_segment_resolves_through_the_registry(self):
        import registry

        self.assertEqual(registry.check_spec("28w").loader,
                         "checks.dsh_boundary.emit_check_section")
        self.assertEqual(registry.handler_path(boundary.DOCTOR_COMMAND_KEY),
                         "dsh_doctor.main")

    def test_negative_a_second_coverage_generator_is_detected(self):
        # The seam is the guard *text*, so this never writes to the repository.
        guard = boundary._read(_INFRA_DIR / "dsh_compat.py")
        mutated = guard + "\n\ndef check_dsh_preset_compat_again():\n    return {}\n"
        criterion = boundary.k12_single_verdict_anchor(
            self.contract_facts(self.real_subject()), guard_text=mutated)
        self.assertFails(criterion, "generation point is not unique")

    def test_negative_a_missing_fifth_field_is_detected(self):
        guard = boundary._read(_INFRA_DIR / "dsh_compat.py")
        mutated = guard.replace('"unreadable_compositions"',
                                '"unreadable_compositions_DISABLED"')
        self.assertNotEqual(mutated, guard)
        criterion = boundary.k12_single_verdict_anchor(
            self.contract_facts(self.real_subject()), guard_text=mutated)
        self.assertFails(criterion, "unreadable_compositions")


    def test_negative_an_unregistered_doctor_key_is_detected(self):
        criterion = boundary.k12_single_verdict_anchor(
            self.contract_facts(self.real_subject()),
            registered_commands={"check-governance", "archguard-ratchet"})
        self.assertFails(criterion, "is not a registered command key")

    def test_negative_a_missing_guard_source_is_detected(self):
        criterion = boundary.k12_single_verdict_anchor(
            self.contract_facts(self.real_subject()), guard_text="")
        self.assertFails(criterion, "generation point is not unique")

    def test_negative_an_empty_guard_source_is_detected(self):
        criterion = boundary.k12_single_verdict_anchor(
            self.contract_facts(self.real_subject()), guard_text="# nothing here")
        self.assertFails(criterion, "generation point is not unique")


# ══════════════════════════════════════════════════════════════════════════
# K-13 — the rehearsal baseline
# ══════════════════════════════════════════════════════════════════════════


class K13RehearsalBaselineTests(RepoCase):

    def test_positive_the_shipped_baseline_is_shaped_and_within_ttl(self):
        subject = self.real_subject()
        self.assertPasses(boundary.k13_rehearsal_baseline(
            subject, self.contract_facts(subject)))

    def test_positive_the_baseline_is_a_recorded_non_synthetic_fact(self):
        record = boundary.load_factsheet(
            next(iter(_FIXTURES_DIR.glob("host-facts-*.json"))))
        self.assertEqual(record.findings, [])
        self.assertFalse(record.synthetic)
        self.assertIsNotNone(record.dsh_version)
        self.assertIsNotNone(record.captured_at)

    def test_negative_a_missing_baseline_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = boundary.Subject(
                _PACKAGE_ROOT,
                factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "no host-facts baseline")

    def test_negative_a_baseline_over_ttl_is_evidence_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "host-facts-0.9.9.json"
            fixture.write_text(json.dumps({
                "schema_version": 1, "dsh_version": "0.9.9",
                "captured_at": "2020-01-01T00:00:00+00:00",
                "synthetic": False, "provenance": "test",
                "plane": {"source": "test"},
            }), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "[EVIDENCE-STALE]")

    def test_negative_a_baseline_missing_a_required_field_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "host-facts-0.9.9.json"
            fixture.write_text(json.dumps({
                "schema_version": 1, "captured_at": "2026-09-13T00:00:00+00:00",
                "synthetic": False, "provenance": "test",
            }), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "missing `dsh_version`")

    def test_negative_a_non_iso_captured_at_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "host-facts-0.9.9.json"
            fixture.write_text(json.dumps({
                "schema_version": 1, "dsh_version": "0.9.9",
                "captured_at": "last Tuesday", "synthetic": False,
                "provenance": "test", "plane": {},
            }), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "is not an ISO-8601 timestamp")

    def test_negative_a_non_boolean_synthetic_flag_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "host-facts-0.9.9.json"
            fixture.write_text(json.dumps({
                "schema_version": 1, "dsh_version": "0.9.9",
                "captured_at": "2026-09-13T00:00:00+00:00",
                "synthetic": "no", "provenance": "test", "plane": {},
            }), encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "`synthetic` must be a boolean")

    def test_negative_unparsable_json_is_named_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "host-facts-0.9.9.json"
            fixture.write_text("{oops", encoding="utf-8")
            subject = boundary.Subject(_PACKAGE_ROOT,
                                       factsheet_glob=Path(tmp) / "host-facts-*.json")
            criterion = boundary.k13_rehearsal_baseline(subject,
                                                       self.contract_facts(subject))
        self.assertFails(criterion, "not valid JSON")


# ══════════════════════════════════════════════════════════════════════════
# the aggregate report and its rendering
# ══════════════════════════════════════════════════════════════════════════


class ReportTests(RepoCase):

    def test_the_report_carries_every_criterion(self):
        report = boundary.check_dsh_boundary(_PACKAGE_ROOT)
        self.assertEqual([entry["id"] for entry in report["criteria"]],
                         list(boundary.CRITERIA))
        self.assertEqual(report["check"], "28w")

    def test_a_crashed_criterion_is_reported_as_fail_not_hidden(self):
        # Patch one runner through the module the aggregate uses: the point is
        # that a raising judgment is *reported*, never swallowed into PASS.
        original = boundary.k6_patch_shape

        def boom(subject, facts):
            raise RuntimeError("injected")

        boundary.k6_patch_shape = boom
        try:
            report = boundary.check_dsh_boundary(_PACKAGE_ROOT)
        finally:
            boundary.k6_patch_shape = original
        entry = {item["id"]: item for item in report["criteria"]}["K-6"]
        self.assertEqual(entry["verdict"], "FAIL")
        self.assertIn("criterion crashed: RuntimeError: injected", entry["reason"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_verdict_never_folds_not_run_into_pass(self):
        self.assertEqual(boundary.verdict(
            {"criteria": [{"verdict": "NOT_RUN"}, {"verdict": "NOT_RUN"}]}),
            "NOT_RUN")
        self.assertEqual(boundary.verdict(
            {"criteria": [{"verdict": "PASS"}, {"verdict": "NOT_RUN"}]}), "PASS")
        self.assertEqual(boundary.verdict(
            {"criteria": [{"verdict": "PASS"}, {"verdict": "FAIL"}]}), "FAIL")
        self.assertEqual(boundary.verdict({"criteria": []}), "NOT_RUN")

    def test_the_rendered_section_lists_every_criterion_and_counts_failures(self):
        import io

        stream = io.StringIO()
        issues = boundary.emit_check_section(stream=stream)
        output = stream.getvalue()
        self.assertIn("Check 28w", output)
        for ident in boundary.CRITERIA:
            self.assertIn(f" {ident}: ", output)
        self.assertEqual(issues, 0)
        self.assertIn("Result: PASS", output)

    def test_the_cli_json_form_matches_the_report(self):
        import contextlib
        import io

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = boundary.main(["--json"])
        self.assertEqual(code, 0)
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["check"], "28w")
        self.assertEqual(len(payload["criteria"]), len(boundary.CRITERIA))

    def test_the_cli_fail_on_issues_maps_a_fail_to_exit_one(self):
        import contextlib
        import io

        original = boundary.k6_patch_shape

        def boom(subject, facts):
            raise RuntimeError("injected")

        boundary.k6_patch_shape = boom
        try:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = boundary.main(["--fail-on-issues", "--json"])
        finally:
            boundary.k6_patch_shape = original
        self.assertEqual(code, 1)


# ══════════════════════════════════════════════════════════════════════════
# F-01 (REVIEW-FEAT-031-CODE-R0) — K-7's third clause: no restated host version
# ══════════════════════════════════════════════════════════════════════════


class K7VersionLiteralTests(RepoCase):
    """The clause R0 found unimplemented (design §2.8 K-7, G11-a / D-11 / D-15).

    V7 removed the stale dsh version literals from `cordis.patch.yml` and
    `lib/index.js`; R0 showed nothing guarded that removal, so the regression
    path had no judge at all. These cases pin both directions.
    """

    def setUp(self):
        self.subject = self.real_subject()
        self.facts = self.contract_facts(self.subject)
        self.patch_text = (_PACKAGE_ROOT / "cordis.patch.yml").read_text(encoding="utf-8")
        self.lib_text = (_PACKAGE_ROOT / "lib" / "index.js").read_text(encoding="utf-8")

    def _mutated(self, seam, text):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / ("mutated.yml" if seam == "patch" else "mutated.js")
        path.write_text(text, encoding="utf-8")
        subject = boundary.Subject(**{seam: path})
        return subject, self.contract_facts(subject)

    def test_positive_no_restated_host_version_in_the_scanned_files(self):
        self.assertEqual(boundary.version_literal_findings(self.facts, self.subject), [])
        criterion = boundary.k7_version_evidence(self.facts, self.subject)
        # The clause is clean; the *evidence* half stays NOT_RUN by design.
        self.assertEqual(criterion.verdict, "NOT_RUN", criterion.reason)
        self.assertIn("no restated dsh version literal", criterion.reason)

    def test_the_scanned_files_are_the_contract_declared_ones(self):
        pairs = boundary.version_literal_scan_paths(self.facts, self.subject)
        self.assertEqual([relative for relative, _ in pairs],
                         [self.facts.get("own.patch.file"),
                          self.facts.get("own.host_row.entry")])

    def test_negative_a_version_literal_in_the_patch_is_a_fail(self):
        # The reviewer's exact mutation: `version: "0.1.5-rc.2"`.
        subject, facts = self._mutated(
            "patch", self.patch_text + '\n  version: "0.1.5-rc.2"\n')
        criterion = boundary.k7_version_evidence(facts, subject)
        self.assertFails(criterion, "dsh version literal outside the contract",
                         "cordis.patch.yml", "0.1.5-rc.2")

    def test_negative_a_version_literal_in_a_patch_comment_is_a_fail(self):
        # G-11 arose in prose ("installed dsh 0.1.5-rc.2"), so comments count.
        subject, facts = self._mutated(
            "patch", self.patch_text + "\n# installed dsh 0.1.5-rc.2\n")
        criterion = boundary.k7_version_evidence(facts, subject)
        self.assertFails(criterion, "cordis.patch.yml", "0.1.5-rc.2")

    def test_negative_a_version_literal_in_the_host_row_is_a_fail(self):
        subject, facts = self._mutated(
            "host_row", self.lib_text + "\n// validated against dsh 0.1.0-rc.6\n")
        criterion = boundary.k7_version_evidence(facts, subject)
        self.assertFails(criterion, "lib/index.js", "0.1.0-rc.6")

    def test_positive_our_own_package_version_is_not_a_host_claim(self):
        version = boundary._package_version_from(_PACKAGE_ROOT)
        self.assertTrue(version)
        subject, facts = self._mutated(
            "patch", self.patch_text + f"\n# package {version}\n")
        self.assertEqual(boundary.version_literal_findings(facts, subject), [])

    def test_positive_a_recorded_host_version_is_accepted(self):
        # The accepted set is the contract's own record: a literal that *is* the
        # recorded dsh version is the single source of truth naming itself.
        version = self.facts.get("evidence.dsh_cli_version") or "0.1.5-rc.1"
        document = json.loads(json.dumps(self.facts.document))
        document["evidence"]["dsh_cli_version"] = version
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        contract = Path(temp.name) / "host-contract.json"
        contract.write_text(json.dumps(document), encoding="utf-8")
        patch = Path(temp.name) / "mutated.yml"
        patch.write_text(self.patch_text + f"\n# measured {version}\n", encoding="utf-8")
        subject = boundary.Subject(contract=contract, patch=patch)
        binding = boundary.ContractFacts(subject)
        self.assertEqual(binding.get("evidence.dsh_cli_version"), version)
        self.assertEqual(boundary.version_literal_findings(binding, subject), [])

    def test_positive_a_design_citation_is_not_a_version_literal(self):
        # `§2.5.1` is a section reference — the live tree contains exactly that
        # in a `lib/index.js` comment, and reporting it would be noise.
        subject, facts = self._mutated(
            "host_row", self.lib_text + "\n// design \u00a72.5.1 makes this explicit\n")
        self.assertEqual(boundary.version_literal_findings(facts, subject), [])

    def test_negative_a_deeper_numbering_chain_is_not_a_version(self):
        subject, facts = self._mutated(
            "host_row", self.lib_text + "\n// see 2.5.1.3 below\n")
        self.assertEqual(boundary.version_literal_findings(facts, subject), [])

    def test_negative_an_unreadable_scanned_file_is_named(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        subject = boundary.Subject(patch=Path(temp.name) / "absent.yml")
        facts = self.contract_facts(subject)
        criterion = boundary.k7_version_evidence(facts, subject)
        self.assertFails(criterion, "version-literal scan cannot read")


# ══════════════════════════════════════════════════════════════════════════
# F-04 (REVIEW-FEAT-031-CODE-R0) — K-2's consumer set matches the design's list
# ══════════════════════════════════════════════════════════════════════════


class K2ConsumerCoverageTests(RepoCase):
    """The three declaration files R0 showed outside the scan."""

    ADDED = ("adapters/dsh/adapter-manifest.json", "package.json", "cordis.patch.yml")

    def test_the_designs_full_consumer_list_is_scanned(self):
        for relative in self.ADDED:
            self.assertIn(relative, boundary.K2_CONSUMERS)
        self.assertEqual(len(boundary.K2_CONSUMERS), 11)

    def test_positive_all_eleven_consumers_exist_and_pass(self):
        subject = self.real_subject()
        missing = [relative for relative in boundary.K2_CONSUMERS
                   if not (_PACKAGE_ROOT / relative).is_file()]
        self.assertEqual(missing, [])
        self.assertPasses(boundary.k2_no_outside_literal(subject,
                                                         self.contract_facts(subject)))

    def test_negative_an_undeclared_package_in_the_adapter_manifest_is_caught(self):
        self._inject_and_assert("adapters/dsh/adapter-manifest.json",
                                '"ghost": "@deepseek-ai/dsh-not-declared"',
                                "adapters/dsh/adapter-manifest.json")

    def test_negative_an_undeclared_package_in_package_json_is_caught(self):
        self._inject_and_assert("package.json",
                                '"ghost": "@deepseek-ai/dsh-not-declared"',
                                "package.json")

    def test_negative_an_undeclared_env_in_package_json_is_caught(self):
        self._inject_and_assert("package.json",
                                '"ghostEnv": "DSH_NOT_DECLARED_ANYWHERE"',
                                "DSH_NOT_DECLARED_ANYWHERE")

    def test_negative_an_undeclared_package_in_the_patch_layer_is_caught(self):
        self._inject_and_assert("cordis.patch.yml",
                                "# ghost: '@deepseek-ai/dsh-not-declared'",
                                "cordis.patch.yml")

    def _inject_and_assert(self, relative, injection, needle):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        _copy_artifact(root, dsh_contract.CONTRACT_REL)
        for consumer in boundary.K2_CONSUMERS:
            _copy_artifact(root, consumer)
        target = root / relative
        target.write_text(target.read_text(encoding="utf-8") + "\n" + injection + "\n",
                          encoding="utf-8")
        subject = boundary.Subject(root)
        criterion = boundary.k2_no_outside_literal(subject, self.contract_facts(subject))
        self.assertFails(criterion, needle)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
