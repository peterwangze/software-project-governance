"""Test the packaged DSH host contract and its consumers.

Checks include schema/error classification, rejection of retired frozen
composition inputs, overlay tokens, host dependency coverage, deterministic
fixture emission and contract mutation probes. The executable boundary check
and its negative fixtures are covered in test_dsh_boundary.py.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]

for _path in (str(_INFRA_DIR), str(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import dsh_compat  # noqa: E402
import dsh_contract  # noqa: E402
import dsh_fixtures  # noqa: E402

TEMPLATE = _REPO_ROOT / "agent-presets" / "governance" / "overlay.cordis.yml"
AUDIT_REPORT = (
    _REPO_ROOT / "docs" / "requirements" / "dsh-host-dependency-inventory-0.81.0.md")
PATCH_FILE = _REPO_ROOT / "cordis.patch.yml"
LIB_INDEX = _REPO_ROOT / "lib" / "index.js"
LAUNCH_PY = _REPO_ROOT / "adapters" / "dsh" / "launch.py"
GUARD_PY = (_REPO_ROOT / "skills" / "software-project-governance" / "infra"
            / "dsh_compat.py")
REGISTRY_PY = (_REPO_ROOT / "skills" / "software-project-governance" / "infra"
               / "registry.py")
SHIMS_DIR = _REPO_ROOT / "adapters" / "dsh" / "skill-shims"

_AUDIT_ID_RE = re.compile(r"^D-\d{2,3}$")
_TEMPLATE_TOKEN_RE = re.compile(r"__[A-Za-z0-9_]+__")

_NECESSARY = "necessary"
_WEAKENABLE = "weakenable"
_ELIMINABLE = "eliminable"
_HISTORICAL = "historical"


def _read(pypath):
    return pypath.read_text(encoding="utf-8")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _contract():
    return dsh_contract.load_contract()


def _template_text():
    import dsh_fixtures
    return dsh_fixtures._template_text()


def _audit_marker_sets():
    """Re-derive AUDIT-153's per-row necessity classes from its §2 tables.

    Only the dependency-point tables of §2 count. Their rows carry a necessity
    marker in one of the first five cells; §4's coverage-matrix rows carry no
    such marker and are skipped. Two §2 rows are ragged in the report itself
    (``D-53`` lost a cell, ``D-99``'s evidence contains ``||``), so the marker
    is located instead of assuming a fixed column — the derivation therefore
    stays independent of the report's own summary arithmetic.
    """
    classes = {_NECESSARY: [], _WEAKENABLE: [], _ELIMINABLE: [], _HISTORICAL: []}
    markers = {"**必要": _NECESSARY, "**可弱化": _WEAKENABLE,
               "**可消除": _ELIMINABLE, "**不可消除": _HISTORICAL}
    for line in _read(AUDIT_REPORT).splitlines():
        if not line.startswith("| D-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not _AUDIT_ID_RE.match(cells[0]):
            continue
        marker = next((cell for cell in cells[1:6]
                       if cell.startswith(tuple(markers))), None)
        if marker is None:
            continue
        for prefix, key in markers.items():
            if marker.startswith(prefix):
                classes[key].append(cells[0])
                break
    return {key: sorted(value, key=lambda item: int(item[2:]))
            for key, value in classes.items()}


def _guard_test_refs():
    """Map ``test_<file>.py::<method>`` references to their file/method text."""
    refs = {}
    for path in sorted((_INFRA_DIR / "tests").glob("test_*.py")):
        text = _read(path)
        refs[path.name] = set(re.findall(r"def (test_\w+)", text))
    return refs


def _registered_check_tokens():
    """Text-level registry face: segment ids and CLI command keys."""
    text = _read(REGISTRY_PY)
    tokens = set(re.findall(r'"(\d\d[a-z])"', text))
    tokens.update(re.findall(r'\("(check-[a-z0-9-]+)"', text))
    tokens.update(re.findall(r'\("(dsh-doctor)"', text))
    return tokens


# ══════════════════════════════════════════════════════════════════════════
# K-2 — the outside-contract hard-coding scan (design §2.8, R0 BT-R-01)
# ══════════════════════════════════════════════════════════════════════════
#
# **What this scan is for.** K-3/K-4 and the renderer parity suite prove that
# the *output* is unchanged; they cannot prove that the consumers stopped
# holding their own copy of a host fact. R0 BT-R-04 names that gap explicitly:
#
#     "parity 只证输出等价，不证单一事实源" — parity proves output equivalence
#     only; the single-source-of-truth claim is K-2's job.
#
# So V2 lands this scan together with the consumer migration (R0 BT-R-01: the
# only judgment that can see "still hard-coded" must not wait for V8), and the
# mutation matrix below proves the other half (the consumers really read the
# contract). The two are complementary, and neither substitutes for the other.
#
# **What it is.** Pure text/regex over six declared consumer files plus the
# template — no import of `verify_workflow`, no dependency on any module that
# only exists in V8. For four classes of literal, every occurrence must be
# traceable to a declared contract value, or be allowlisted with a reason.
#
# **Scope note (deliberate, R1 N-2/N-4 territory).** The design lists the
# consumer set as `lib/index.js`, `launch.py`, `dsh_compat.py`, the template,
# the hooks, `adapter-manifest.json`, `package.json` and `cordis.patch.yml`.
# This scan covers the six files V2 actually migrates plus the three hooks
# (whose runtime is explicitly *not* migrated — §2.5 C-5 keeps them static, so
# scanning them is the only V2-available guard). The remaining three are
# declaration files whose literals are the *input* the contract mirrors, and
# their consistency is already judged by K-10/`check-manifest-consistency` and
# by `test_own_package_matches_package_json`; scanning them here would only
# re-assert the same facts with a second mechanism. Widening the set is V8's
# `check-dsh-boundary` step, and the widening itself must fail closed when a
# new literal appears.

#: Ratchet budget for the allowlist below.
#:
#: Design §10 O-9 budgets **3** entries for "the three `@deepseek-ai/cordis*`
#: oracle packages". This slice lands **0**: the oracle names are declared in
#: the contract (`host.apis` is a declaration, so the guard naming one is not a
#: second source of truth) and V2 removed the last quoted occurrence of them
#: from `dsh_compat.py` (they now survive only as prose, which this scan does
#: not judge). The three entries would therefore have been *unnecessary* —
#: `test_every_allowlist_entry_is_necessary` proves it by removing each one and
#: watching no violation appear — and an unnecessary exemption is exactly what
#: R0 BT-R-01 asks to be denied. Landing 0 against a budget of 3 spends none of
#: the ratchet, so the constraint "only down, never up" is untouched.
#:
#: R1 N-2 flags that the budget's *anchor* must live outside the contract (a
#: contract field could be raised in the same commit as the entry it should
#: reject). It lives here, in the judging test, together with the entries.
ALLOWLIST_BUDGET = 0

#: The scanned consumers, repo-relative. Kept explicit (not globbed) so adding
#: a consumer is a reviewable edit rather than a silent widening.
K2_CONSUMERS = (
    "lib/index.js",
    "adapters/dsh/launch.py",
    "skills/software-project-governance/infra/dsh_compat.py",
    "skills/software-project-governance/infra/verify_workflow.py",
    "agent-presets/governance/overlay.cordis.yml",
    "skills/software-project-governance/infra/hooks/pre-commit",
    "skills/software-project-governance/infra/hooks/commit-msg",
    "skills/software-project-governance/infra/hooks/post-commit",
)

#: The allowlist (K-11 shape: `literal` + `reason` + `since_slice`, plus the
#: file scope this scan needs — a literal is exempt where it is justified, not
#: everywhere). Empty at V2 (see the budget note above); every entry added must
#: be *necessary*, which `test_every_allowlist_entry_is_necessary` asserts by
#: removing it and requiring a violation to appear.
K2_ALLOWLIST = ()


def _declared_literal_sets(contract=None):
    """The literal sets K-2 accepts, derived from the contract itself.

    Deriving the accepted set from the contract is what makes the scan a
    single-source judgment: the contract cannot widen its own acceptance
    without the migration (and the reader) seeing the change. Oracle packages
    are included — `host.apis` is a declaration, so the guard naming one is not
    a second source of truth.
    """
    contract = _contract() if contract is None else contract
    host = contract["host"]
    packages = ({value for key, value in contract["own"]["native"].items()
                 if key.endswith("_row_name")}
                | {contract["own"]["package"]["name"]}
                | {"{0}/{1}".format(host["install"]["scope"],
                                    host["install"]["cli_package"])}
                | set(host["apis"]))
    # Directory-boundary prefixes: `@scope/pkg` also declares `@scope`, so a
    # reference to a path *inside* a declared package (`@scope/pkg/package.json`,
    # which the probe resolves) is not a second literal.
    for name in list(packages):
        parts = name.split("/")
        for index in range(1, len(parts)):
            packages.add("/".join(parts[:index]))
    return {
        "package": packages,
        "env": {host["env"]["home_var"], *host["install"]["env_overrides"].values()},
        "path": {host["home"]["user_preset_dir"], host["home"]["composition_file"]},
        "marker": {contract["own"]["preset"]["version_marker"],
                   contract["own"]["preset"]["skill_root_marker"]},
    }


#: The four detection patterns (module-level constants, so a test can assert
#: what each class does and does not catch).
#:
#: **Every class is judged inside a string literal, never on a raw line**
#: (CODE R0 F-04/F-05). A line-based path/marker judgment missed the most likely
#: shadow copy — `const d = ".agent-presets"` — because it only recognized the
#: bare token; judging quoted content catches it while still ignoring prose.
#: `_QUOTED_RE` accepts `'`, `"` and backticks (backticks are the native spelling
#: in `lib/index.js` and were the F-05 blind spot); the contents are *not*
#: interpreted, so a `` `__X__${y}` `` interpolation is judged by its literal
#: text only — the honest reading for a text scan.
#:
#: **What the path class can and cannot see** (recorded so the coverage face is
#: honest): it judges the two spellings the contract declares — the user preset
#: directory name and the composition file name. A *different* preset directory
#: or composition name is not a fixed literal, so no text scan can recognize it
#: without a list; that is what the mutation matrix covers (the consumer must
#: follow `own.preset.id`, whichever value it holds). V8's `check-dsh-boundary`
#: can extend the class by reading `own.preset.*` for more spellings.
#:
#: **Known residual blind spot** (registered, not hidden; the reviewer's F-06):
#: `os.getenv('X')`, `e = os.environ; e.get('X')` and `process['env']['X']` are
#: equivalent spellings the env class does not recognize. Tightening it into a
#: tokenizer is V8 work; the direct accessor forms are what this tree uses.
_PACKAGE_RE = re.compile(r"@[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_QUOTED_RE = re.compile(
    r"([\"'`])((?:\\.|(?!\1).)*)\1")
_ENV_REF_RE = re.compile(
    r"(?:os\.environ\.get|os\.environ\[|process\.env\[|process\.env\.)"
    r"\(?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)")
_PATH_RE = re.compile(r"\.agent-presets\b|agent\.cordis\.yml(?!\.template)")
_MARKER_RE = re.compile(r"\.dsh-bundle-version\b|\bskill-root\.txt\b")


def quoted_literals(text):
    """Every string literal in ``text``, for `'`, `"` and backtick quotes.

    Nothing is interpreted — a text scan compares the declared spelling, so the
    raw content is the right thing to judge. A backtick template with
    `${…}` interpolation therefore reports its literal text.
    """
    return [match.group(2) for match in _QUOTED_RE.finditer(text)]


def k2_scan(paths=K2_CONSUMERS, root=None, allowlist=K2_ALLOWLIST):
    """Every outside-contract host literal, as ``(file, line, class, literal)``.

    Detection is **literal-scoped, not prose-scoped**, and every class reads the
    contents of a string literal rather than a raw line: the path/marker classes
    match inside quoted strings (so `const d = ".agent-presets"` is caught —
    reviewing a raw line missed exactly that shape), and the env class reads
    environment accessor calls (the identifier there is the literal).

    **Known divergence from the product scanner** (FIX-322): the package class
    here keeps the historic inside-string ``findall`` — any package spelling
    inside a literal is extracted and judged — while the product scanner
    (``checks/dsh_boundary.py``) judges a quoted string as a whole: the literal
    must *be* the package reference (optionally with a `/`-prefixed subpath),
    which closes F-07 (REVIEW-FEAT-030-CODE-R0) and N-2
    (REVIEW-FEAT-030-CODE-R1). This oracle stays conservative on purpose so a
    contract-facing test that needs the literal-scoped shape keeps a working
    reference; a message sentence quoting a package name is judged prose only by
    the product scanner.

    ``paths`` is repo-relative (the negative tests pass their own), and the
    allowlist is a parameter so both the "entry missing" and the "entry out of
    scope" failures can be exercised without touching the real one.
    """
    root = _REPO_ROOT if root is None else Path(root)
    declared = _declared_literal_sets()
    allowed = {(entry["literal"], path)
               for entry in allowlist
               for path in entry["files"]}
    violations = []
    for relative in paths:
        text = _read(root / relative)
        for line_number, line in enumerate(text.splitlines(), start=1):
            def report(kind, literal):
                if (literal, relative) not in allowed:
                    violations.append((relative, line_number, kind, literal))

            for literal in quoted_literals(line):
                # package class (V2 oracle): any package spelling inside the
                # string — the conservative divergence from the product
                # scanner's whole-literal judgment (see k2_scan docstring).
                for package in _PACKAGE_RE.findall(literal):
                    if package in declared["package"]:
                        continue
                    report("package", package)
                # path / marker classes: matched INSIDE the literal, which is
                # what makes a quoted shadow copy visible (F-04).
                for kind, pattern, declared_key in (
                        ("path", _PATH_RE, "path"),
                        ("marker", _MARKER_RE, "marker")):
                    for match in pattern.finditer(literal):
                        if match.group(0) in declared[declared_key]:
                            continue
                        report(kind, match.group(0))
            # env class: only environment accessor calls, and only names shaped
            # like a host variable — `DSH_SCOPE` (our own symbol) is not one.
            for reference in _ENV_REF_RE.finditer(line):
                name = reference.group(1)
                if name in declared["env"] or not name.startswith("DSH"):
                    continue
                report("env", name)
    return violations


def k2_report(violations):
    """The design's failure line shape: `file:line [class] "literal"`."""
    return "\n".join(
        f'{relative}:{line} [{kind}] "{literal}"'
        for relative, line, kind, literal in violations)


class TestAccessorContract(unittest.TestCase):
    """K-1: load + minimal validation + the §2.5.1 exception classification."""

    def test_contract_path_resolves_under_the_package_root(self):
        path = dsh_contract.contract_path()
        self.assertTrue(path.is_file(), path)
        self.assertEqual(path.name, "host-contract.json")
        self.assertEqual(
            path, dsh_contract.contract_path(_REPO_ROOT))

    def test_load_returns_the_declared_namespaces(self):
        contract = _contract()
        self.assertEqual(contract["schema_version"], 2)
        for namespace in ("evidence", "host", "own", "coverage", "elimination",
                          "deprecations"):
            self.assertIn(namespace, contract)
            self.assertIsInstance(contract[namespace], dict, namespace)

    def test_supported_schema_versions_is_the_declared_closed_set(self):
        # FEAT-113 S0 (§8.2.1): v2 only — the in-package contract ships with
        # its code, so v1 raises ContractSchemaUnknown (no legal v1 scenario).
        self.assertEqual(dsh_contract.SUPPORTED_SCHEMA_VERSIONS, (2,))
        self.assertEqual(
            dsh_contract.CONTRACT_REL, "adapters/dsh/host-contract.json")

    def test_missing_contract_file_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(dsh_contract.ContractUnreadable) as caught:
                dsh_contract.load_contract(Path(tmp))
        message = str(caught.exception)
        self.assertIn("ContractUnreadable", message)
        self.assertIn("host-contract.json", message)

    def test_a_non_utf8_contract_is_unreadable_and_names_the_path(self):
        # §2.5.1 / R0 F-1: bytes that cannot be decoded are a *read* failure —
        # `ContractUnreadable` (a consumer may degrade it to NOT_RUN), never a
        # bare `UnicodeDecodeError` (which escapes the three-class vocabulary
        # entirely) and never `ContractMalformed` (a product defect: FAIL).
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / dsh_contract.CONTRACT_REL
            target.parent.mkdir(parents=True)
            good = dsh_contract.contract_path().read_bytes()
            target.write_bytes(good[:200] + b"\xff\xfe" + good[200:])
            with self.assertRaises(dsh_contract.ContractUnreadable) as caught:
                dsh_contract.load_contract(Path(tmp))
        message = str(caught.exception)
        self.assertIn("ContractUnreadable", message)
        self.assertIn("UnicodeDecodeError", message)
        self.assertIn(str(target), message, "the message must carry the path")
        self.assertNotIsInstance(caught.exception, dsh_contract.ContractMalformed)

    def test_malformed_json_is_malformed(self):
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw="{ not json")
        self.assertIn("ContractMalformed", str(caught.exception))
        self.assertIn("host-contract.json", str(caught.exception))

    def test_non_object_document_is_malformed(self):
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw=json.dumps([1, 2, 3]))
        self.assertIn("ContractMalformed", str(caught.exception))

    def test_unknown_schema_version_is_fail_closed(self):
        payload = json.loads(json.dumps(_contract()))
        payload["schema_version"] = 99
        with self.assertRaises(dsh_contract.ContractSchemaUnknown) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        message = str(caught.exception)
        self.assertIn("ContractSchemaUnknown", message)
        self.assertIn("99", message)
        self.assertIn("host-contract.json", message)

    def test_missing_required_field_is_malformed_and_names_the_field(self):
        for dotted in ("host.env.probe_side.no_fallback",
                       "host.env.write_side.blank_policy",
                       "own.render.tokens",
                       "evidence.audit.head"):
            payload = json.loads(json.dumps(_contract()))
            node = payload
            parts = dotted.split(".")
            for part in parts[:-1]:
                node = node[part]
            node.pop(parts[-1])
            with self.assertRaises(dsh_contract.ContractMalformed) as caught:
                dsh_contract.load_contract(raw=json.dumps(payload))
            message = str(caught.exception)
            self.assertIn(dotted, message, dotted)
            self.assertIn("host-contract.json", message)

    def test_foreign_overlay_row_is_malformed(self):
        payload = json.loads(json.dumps(_contract()))
        payload["own"]["overlay"]["rows"].append("tool-fs")
        with self.assertRaisesRegex(dsh_contract.ContractMalformed, "own.overlay.rows"):
            dsh_contract.load_contract(raw=json.dumps(payload))


    def test_duplicate_overlay_row_is_malformed(self):
        payload = json.loads(json.dumps(_contract()))
        payload["own"]["overlay"]["rows"] = ["persona", "persona"]
        with self.assertRaisesRegex(dsh_contract.ContractMalformed, "own.overlay.rows"):
            dsh_contract.load_contract(raw=json.dumps(payload))

    def test_get_resolves_documented_paths(self):
        contract = _contract()
        self.assertEqual(dsh_contract.get("host.install.scope", contract),
                         "@deepseek-ai")
        self.assertEqual(
            dsh_contract.get("own.native.persona_row_name", contract),
            "@deepseek-ai/dsh-persona")
        self.assertEqual(
            dsh_contract.get("own.overlay.rows", contract),
            ["persona", "skill-filesystem"])
        self.assertIsInstance(dsh_contract.get("coverage.entries", contract), list)

    def test_get_raises_for_an_undeclared_path(self):
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.get("host.no_such_field")
        self.assertIn("host.no_such_field", str(caught.exception))

    def test_get_returns_null_fields_instead_of_raising(self):
        # `compat_range` is present-but-unadjudicated in V1 (see the contract
        # note); "present with a null value" is not the same as "missing".
        self.assertTrue(dsh_contract.get("evidence.compat_range") is None)

    def test_reset_cache_forces_a_fresh_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / dsh_contract.CONTRACT_REL
            target.parent.mkdir(parents=True)
            payload = json.loads(json.dumps(_contract()))
            target.write_text(json.dumps(payload), encoding="utf-8")
            first = dsh_contract.load_contract(root)
            payload["host"]["install"]["scope"] = "@mutated"
            target.write_text(json.dumps(payload), encoding="utf-8")
            try:
                self.assertEqual(
                    dsh_contract.load_contract(root)["host"]["install"]["scope"],
                    "@deepseek-ai")
                dsh_contract.reset_cache()
                self.assertEqual(
                    dsh_contract.load_contract(root)["host"]["install"]["scope"],
                    "@mutated")
            finally:
                dsh_contract.reset_cache()

    def test_load_never_writes_the_contract_file(self):
        # Design §2.7: readers are read-only, an automatic refresh would make
        # the declaration un-auditable.
        before = _sha256(dsh_contract.contract_path().read_bytes())
        mtime_before = dsh_contract.contract_path().stat().st_mtime_ns
        dsh_contract.reset_cache()
        dsh_contract.load_contract()
        self.assertEqual(before, _sha256(dsh_contract.contract_path().read_bytes()))
        self.assertEqual(
            mtime_before, dsh_contract.contract_path().stat().st_mtime_ns)

    def test_accessor_is_stdlib_only_and_never_imports_the_registry(self):
        # ADR-018 §8 / R0 F-15: `registry → checks.dsh_boundary → dsh_contract
        # → registry` would be a cycle, so the accessor must not name it.
        source = _read(_INFRA_DIR / "dsh_contract.py")
        imports = set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)",
                                 source, re.MULTILINE))
        self.assertNotIn("registry", imports)
        self.assertNotIn("dsh_compat", imports)
        self.assertNotIn("dsh_doctor", imports)
        allowed = {"json", "os", "pathlib", "typing", "__future__"}
        self.assertTrue(imports <= allowed, sorted(imports - allowed))

    def test_accessor_never_probes_the_host_plane(self):
        # The accessor reads exactly one file: the contract. Field *names* that
        # mention host concepts (evidence.plane.node_modules) are data, not
        # behaviour, so the scan looks for probing constructs, not substrings.
        source = _read(_INFRA_DIR / "dsh_contract.py")
        for forbidden in ("os.environ", "getenv", "expanduser", "subprocess",
                          "shutil", "tempfile", "socket", "urllib", "socket.",
                          "Path.home", '"DSH_HOME"', "readdir", "rglob",
                          "glob("):
            self.assertNotIn(forbidden, source, forbidden)


class TestContractV2AdditiveKeys(unittest.TestCase):
    """FEAT-113 S0 — contract v2 (design §8.2.1): additive keys, zero deletions.

    S0 is deliberately one-directional: v2 only *adds* keys and marks two of
    the old ones deprecated via the `deprecations` sidecar. Every case here
    pins one half of that contract:

      * the new keys are present, readable through `get`, and carry exactly the
        §8.2.1 values (the table is normative);
      * a missing new key is `ContractMalformed` — v2 widens the required set,
        it does not widen acceptance;
      * `schema_version` 1 is `ContractSchemaUnknown` (the in-package contract
        ships with its code; there is no legal v1 scenario, §8.2.1 last row);
      * `host.rows` / `own.preset.template` stay REQUIRED **and** are recorded
        as deprecated — "required-but-deprecated" is a distinct state from
        "optional", so deleting either is still malformed (the timing block:
        弃用 ≠ 允许缺失).
    """

    def setUp(self):
        self.contract = _contract()

    # ── the new keys: present, readable, normative ─────────────────────────
    def test_own_overlay_declares_the_two_governance_rows(self):
        self.assertEqual(dsh_contract.get("own.overlay", self.contract), {
            "path": "agent-presets/governance/overlay.cordis.yml",
            "rows": ["persona", "skill-filesystem"],
            "persona_body_token": "__GOVERNANCE_PERSONA_BODY__",
            "persona_body_source": "agent-presets/governance/persona.md.template",
            "allow_js": False,
        })

    def test_own_native_base_preset_selector_reuses_the_declared_names(self):
        base_preset = dsh_contract.get("own.native.base_preset", self.contract)
        self.assertEqual(base_preset, {
            "patch_rel": "dsh/node_modules/@deepseek-ai/dsh-web-app/"
                         "presets/{id}.patch.yml",
            "row_selector": {
                "name": "@deepseek-ai/dsh-agent-preset",
                "config_id": "standard",
            },
            "rows_path": "config.plugins",
            "insert_selector": "- insert:",
        })
        # `<base_row_name>` / `<base_preset_id>` of §8.2.1 are the two
        # already-declared facts — the selector must not fork a second name.
        self.assertEqual(base_preset["row_selector"]["name"],
                         self.contract["own"]["native"]["base_row_name"])
        self.assertEqual(base_preset["row_selector"]["config_id"],
                         self.contract["own"]["native"]["base_preset_id_default"])

    def test_own_preset_render_provenance_declares_the_d5_fields(self):
        provenance = dsh_contract.get("own.preset.render_provenance",
                                      self.contract)
        self.assertEqual(provenance["filename"], "render-provenance.json")
        self.assertEqual(provenance["schema"], "dsh-preset-provenance/1")
        self.assertEqual(provenance["fields"], [
            "schema", "package_version", "rendered_at",
            "overlay", "persona", "plane", "base",
            "overlay_rows", "rows", "policy",
        ])
        self.assertEqual(provenance["absent_policy"], "warn-one-release")

    def test_own_render_persona_prefix_carries_the_eleven_rule_fields(self):
        # §6.2.2.1 field table, verbatim: the 5-step persona body derivation
        # (§6.2.2.1) must be declarative, so the Python/JS differential gate
        # can judge drift instead of a human re-reading two renderers.
        self.assertEqual(
            dsh_contract.get("own.render.persona_prefix", self.contract),
            {
                "mode": "base-prefix-then-body",
                "separator": "\n\n",
                "trailing": "\n",
                "empty_prefix": "body-only",
                "body_source": "agent-presets/governance/persona.md.template",
                "body_token": "__GOVERNANCE_REPO_ROOT__",
                "body_token_value": "posix_pkg_root",
                "body_crlf": "lf",
                "body_trim": True,
                "body_empty_policy": "refuse",
                "leftover_scan": "__[A-Za-z0-9_]+__",
            })

    def test_persona_prefix_reuses_not_forks_the_existing_facts(self):
        # The three "复用" clauses of §6.2.2.1: body_source == persona_source,
        # body_token == persona_repo_token, leftover_scan == the render scan.
        render = self.contract["own"]["render"]
        native = self.contract["own"]["native"]
        prefix = render["persona_prefix"]
        self.assertEqual(prefix["body_source"], native["persona_source"])
        self.assertEqual(prefix["body_token"], native["persona_repo_token"])
        self.assertEqual(prefix["leftover_scan"], render["leftover_scan"])

    def test_host_planes_declare_precedence_and_the_asar_face(self):
        planes = dsh_contract.get("host.planes", self.contract)
        self.assertEqual(planes["precedence"], [
            "env:DSH_INSTALL_DIR",
            "env:DSH_DESKTOP_APP_DIR",
            "process-ancestor",
            "env:DSH_HARNESS_NODE_MODULES",
            "home-profile",
            "path",
        ])
        self.assertEqual(planes["asar"], {
            "header": [
                "[0:4]==4",
                "[4:8]=payload_size",
                "[12:16]=json_size",
                "json starts at byte 16, trimmed to the last '}'",
            ],
            "content_base": "8+payload_size",
            "runner": {"flag": "ELECTRON_RUN_AS_NODE",
                       "module_flag": "--input-type=module"},
            "runtime_rel": "resources/runtime/versions.json",
            "unpacked_cannot_serve": True,
            "entry_count_cap": 200000,
        })
        self.assertEqual(planes["env"], {"desktop_app_dir": "DSH_DESKTOP_APP_DIR",
                                         "profile_dir": "DSH_PROFILE_DIR"})
        self.assertEqual(planes["process_probe"],
                         {"enabled_in": ["doctor", "boundary"],
                          "max_ancestors": 4})

    def test_host_home_discovery_declares_the_bounded_walk(self):
        self.assertEqual(dsh_contract.get("host.home.discovery",
                                          self.contract), {
            "roots": ["agent-presets", "adapters/dsh"],
            "suffixes": [".cordis.yml", ".cordis.yml.template"],
            "exclude_names": ["overlay.cordis.yml"],
            "bounds": {"max_depth": 24, "max_entries": 50000,
                       "max_seconds": 30},
            "follow_reparse": False,
        })

    def test_host_apis_loader_ctx_declares_the_probe_stub_face(self):
        self.assertEqual(dsh_contract.get("host.apis.loader_ctx",
                                          self.contract), {
            "members": ["baseUrl", "process", "console", "get", "has"],
            "unlisted_member": "throw",
            "stub_values": {"get": "undefined", "has": False},
            "evidence": "ctx_members_used ⊆ members",
        })

    # ── missing new key → malformed (v2 widens the required set) ───────────
    def test_a_missing_v2_key_is_malformed_and_names_the_block(self):
        # Drop whole blocks AND single leaves: the required-paths table must
        # catch both, naming an offending path under the dropped block.
        blocks = [
            ("own.overlay", lambda d: d["own"].pop("overlay")),
            ("own.preset.render_provenance",
             lambda d: d["own"]["preset"].pop("render_provenance")),
            ("own.render.persona_prefix",
             lambda d: d["own"]["render"].pop("persona_prefix")),
            ("host.planes", lambda d: d["host"].pop("planes")),
            ("host.home.discovery",
             lambda d: d["host"]["home"].pop("discovery")),
            ("host.apis.loader_ctx",
             lambda d: d["host"]["apis"].pop("loader_ctx")),
            ("own.native.base_preset",
             lambda d: d["own"]["native"].pop("base_preset")),
            ("deprecations", lambda d: d.pop("deprecations")),
        ]
        for prefix, mutate in blocks:
            with self.subTest(block=prefix):
                payload = json.loads(json.dumps(_contract()))
                mutate(payload)
                with self.assertRaises(
                        dsh_contract.ContractMalformed) as caught:
                    dsh_contract.load_contract(raw=json.dumps(payload))
                self.assertIn(prefix, str(caught.exception), prefix)
                self.assertIn("ContractMalformed", str(caught.exception))

    def test_a_missing_v2_leaf_is_malformed_and_names_the_leaf(self):
        leaves = (
            "own.overlay.path",
            "own.overlay.allow_js",
            "own.native.base_preset.row_selector.name",
            "own.preset.render_provenance.absent_policy",
            "own.render.persona_prefix.body_token",
            "host.planes.asar.runner.flag",
            "host.planes.process_probe.max_ancestors",
            "host.home.discovery.bounds.max_seconds",
            "host.home.discovery.follow_reparse",
            "host.apis.loader_ctx.unlisted_member",
        )
        for dotted in leaves:
            with self.subTest(leaf=dotted):
                payload = json.loads(json.dumps(_contract()))
                node = payload
                parts = dotted.split(".")
                for part in parts[:-1]:
                    node = node[part]
                node.pop(parts[-1])
                with self.assertRaises(
                        dsh_contract.ContractMalformed) as caught:
                    dsh_contract.load_contract(raw=json.dumps(payload))
                self.assertIn(dotted, str(caught.exception), dotted)

    def test_v2_sequence_shapes_are_validated_like_host_apis(self):
        # §8.2.1 constrains these as lists of declared names; the accessor's
        # nested-shape checks mirror the host.apis style (fail loud, name the
        # field) instead of accepting any JSON value at the declared path.
        for dotted, bad in (
            ("own.overlay.rows", "skill-filesystem"),
            ("host.planes.precedence", []),
            ("host.planes.precedence", [23]),
            ("host.home.discovery.roots", "agent-presets"),
            ("host.home.discovery.suffixes", [None]),
            ("host.apis.loader_ctx.members", "baseUrl"),
        ):
            with self.subTest(field=dotted, value=bad):
                payload = json.loads(json.dumps(_contract()))
                node = payload
                parts = dotted.split(".")
                for part in parts[:-1]:
                    node = node[part]
                node[parts[-1]] = bad
                with self.assertRaises(
                        dsh_contract.ContractMalformed) as caught:
                    dsh_contract.load_contract(raw=json.dumps(payload))
                self.assertIn(dotted, str(caught.exception), dotted)

    # ── schema 1 is gone ────────────────────────────────────────────────────
    def test_schema_version_1_is_now_contract_schema_unknown(self):
        # §8.2.1 last row: the in-package contract ships with its code, so a
        # v1 document is not an "older but legal" contract — it is unknown,
        # fail-closed, never parsed with v2 assumptions.
        payload = json.loads(json.dumps(_contract()))
        payload["schema_version"] = 1
        with self.assertRaises(dsh_contract.ContractSchemaUnknown) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        message = str(caught.exception)
        self.assertIn("ContractSchemaUnknown", message)
        self.assertIn("schema_version 1", message)
        self.assertIn("(supported: 2)", message)
        self.assertIn("host-contract.json", message)

    # ── deprecated ≠ optional ──────────────────────────────────────────────
    def test_retired_frozen_inputs_are_refused_even_if_empty(self):
        for path, key, value in (("host", "rows", []), ("own.preset", "template", "")):
            payload = json.loads(json.dumps(_contract()))
            dsh_contract.get(path, payload)[key] = value
            with self.assertRaisesRegex(dsh_contract.ContractMalformed, "retired frozen"):
                dsh_contract.load_contract(raw=json.dumps(payload))

    def test_is_deprecated_is_false_for_every_undeprecated_path(self):
        # The predicate must not degrade into "true for anything old": only
        # the sidecar decides, and today that is exactly the two S0 keys.
        for dotted in ("host.install.scope", "own.render.tokens",
                       "schema_version", "own.overlay.path"):
            self.assertFalse(dsh_contract.is_deprecated(dotted, self.contract),
                             dotted)
        self.assertEqual(
            sorted(self.contract["deprecations"]["entries"]),
            [])

    def test_deprecations_sidecar_entries_are_shape_checked(self):
        for dotted, bad, expected in (
            ("host.rows", {"deprecated_in": "2"}, "deprecated_in"),
            ("host.rows", {}, "deprecated_in"),
            ("own.preset.template", "2", "must be an object"),
        ):
            with self.subTest(entry=dotted, value=bad):
                payload = json.loads(json.dumps(_contract()))
                payload["deprecations"]["entries"][dotted] = bad
                with self.assertRaises(
                        dsh_contract.ContractMalformed) as caught:
                    dsh_contract.load_contract(raw=json.dumps(payload))
                self.assertIn(f"deprecations.entries[{dotted}]",
                              str(caught.exception))
                self.assertIn(expected, str(caught.exception))
        payload = json.loads(json.dumps(_contract()))
        payload["deprecations"]["entries"] = []
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        self.assertIn("deprecations.entries", str(caught.exception))


class TestContractFields(unittest.TestCase):
    """K-1 field-table coverage (§2.4), including the recorded-sub-block rule."""

    def setUp(self):
        self.contract = _contract()

    def test_evidence_fields(self):
        evidence = self.contract["evidence"]
        audit = evidence["audit"]
        self.assertEqual(audit["id"], "AUDIT-153")
        anchor = _REPO_ROOT / audit["path"]
        self.assertTrue(anchor.is_file(), anchor)
        text = _read(anchor)
        self.assertIn(audit["head"], text)
        self.assertIn(audit["date"], text)
        self.assertIsInstance(evidence["verified_on_ttl_days"], int)
        self.assertGreater(evidence["verified_on_ttl_days"], 0)
        self.assertEqual(evidence["verified_on_ttl_days"], 180)
        for field in ("recorded_on", "verified_on", "dsh_cli_version",
                      "compat_range", "plane.source", "plane.node_modules"):
            dsh_contract.get(f"evidence.{field}", self.contract)

    def test_recorded_evidence_is_not_hand_filled(self):
        # Only `dsh-doctor --record-evidence` (V8) may write these; V1 ships
        # them unrecorded and says so.
        evidence = self.contract["evidence"]
        for field in ("recorded_on", "verified_on", "dsh_cli_version",
                      "compat_range"):
            self.assertIsNone(evidence[field], field)
        self.assertIsNone(evidence["plane"]["source"])
        self.assertIsNone(evidence["plane"]["node_modules"])
        recording = evidence["recording"]
        self.assertEqual(recording["source"], "recorded")
        self.assertIs(recording["recorded"], False)
        self.assertEqual(recording["writer"], "dsh-doctor --record-evidence")
        self.assertEqual(recording["slice"], "V8")
        self.assertEqual(evidence["oracle_packages"], {})

    def test_host_env_is_split_into_write_and_probe_side(self):
        env = self.contract["host"]["env"]
        self.assertEqual(env["home_var"], "DSH_HOME")
        write_side = env["write_side"]
        self.assertEqual(write_side["blank_policy"], "trimmed-empty-means-unset")
        self.assertEqual(write_side["trim_policy"],
                         "verbatim-then-platform-resolve")
        self.assertEqual(write_side["fallback"], "<home>/.dsh")
        self.assertEqual(write_side["tilde_expansion"], ["~", "~/", "~\\"])
        probe_side = env["probe_side"]
        self.assertIs(probe_side["require_explicit"], True)
        self.assertIs(probe_side["no_fallback"], True)
        self.assertNotIn("probe_side", write_side)
        # The fail-closed probe side is an existing safety property of the
        # guard (`dsh_compat._profile_planes`), not a write-side convention.
        guard_text = _read(GUARD_PY)
        self.assertIn("if not raw:\n        return []", guard_text)

    def test_host_install_and_plane_layout(self):
        install = self.contract["host"]["install"]
        self.assertEqual(install["scope"], "@deepseek-ai")
        self.assertEqual(install["cli_package"], "dsh")
        self.assertEqual(install["anchor_rel"], ["@deepseek-ai", "dsh",
                                                 "package.json"])
        self.assertEqual(install["profiles_dir_name"], "profiles")
        self.assertEqual(sorted(install["env_overrides"].values()),
                         ["DSH_HARNESS_NODE_MODULES", "DSH_INSTALL_DIR"])
        guard_text = _read(GUARD_PY)
        # V2: the guard declares the contract field per symbol instead of the
        # literal, so the anchor is the binding itself.
        bindings = (
            ("DSH_SCOPE", "host.install.scope"),
            ("DSH_PACKAGE", "host.install.cli_package"),
            ("INSTALL_ANCHOR_REL", "host.install.anchor_rel"),
            ("PROFILES_DIR_NAME", "host.install.profiles_dir_name"),
        )
        for symbol, contract_path in bindings:
            self.assertIn(f'"{symbol}": "{contract_path}"', guard_text, symbol)
        for key, token in install["env_overrides"].items():
            self.assertIn(f'"{key.upper()}_ENV"', guard_text, key)
            self.assertIn(f'"host.install.env_overrides.{key}"', guard_text, token)
        for shape in install["plane_layout"]:
            self.assertIn("DSH_HOME/profiles", shape)
            self.assertIn("node_modules", shape)

    def test_host_home_paths_match_the_guard(self):
        home = self.contract["host"]["home"]
        self.assertEqual(home["user_preset_dir"], ".agent-presets")
        self.assertEqual(home["composition_file"], "agent.cordis.yml")
        self.assertEqual(home["composition_globs"],
                         ["**/agent.cordis.yml", "**/*.cordis.yml.template"])
        guard_text = _read(GUARD_PY)
        self.assertIn('"COMPOSITION_FILENAMES": "host.home.composition_file"',
                      guard_text)
        self.assertIn('"COMPOSITION_GLOBS": "host.home.composition_globs"',
                      guard_text)

    def test_host_row_contract_is_anchored_in_the_guard(self):
        row_contract = self.contract["host"]["row_contract"]
        self.assertEqual(row_contract["builtin_prefix"], "cordis:")
        self.assertEqual(row_contract["builtin_group_name"], "cordis:group")
        self.assertEqual(row_contract["js_dialect_tag"], "!!js")
        self.assertEqual(row_contract["loader_scope"],
                         ["baseUrl", "process", "console"])
        self.assertEqual(row_contract["loader_scope_baseurl_shape"], "file-url")
        self.assertIs(row_contract["group_self_disabled_shortcircuit"], True)
        self.assertIs(row_contract["ancestor_disabled_inherited"], True)
        self.assertEqual(row_contract["ctx_logger"], "optional")
        guard_text = _read(GUARD_PY)
        self.assertIn("startsWith('cordis:')", guard_text)
        self.assertIn("baseUrl: pathToFileURL(file.path).href", guard_text)
        self.assertEqual(set(self.contract["host"]["apis"]["loader_ctx"]["members"]),
                         {"baseUrl", "process", "console", "get", "has"})
        # The declared field names are the template's own keys.
        for field in ("id_field", "name_field", "config_field"):
            self.assertIn(f"{row_contract[field]}:", _template_text())



    def test_host_skill_frontmatter_matches_every_shim(self):
        contract = self.contract["host"]["skill_frontmatter"]
        self.assertIs(contract["name_equals_filename"], True)
        self.assertIs(contract["description_required"], True)
        self.assertEqual(contract["fence"], "---")
        shims = sorted(SHIMS_DIR.glob("*.md"))
        self.assertEqual(len(shims), 9)
        for shim in shims:
            text = _read(shim)
            self.assertTrue(text.startswith(contract["fence"]), shim.name)
            self.assertIn(f"name: {shim.stem}", text, shim.name)
            self.assertRegex(text, r"(?m)^description:\s*\S", shim.name)

    def test_host_apis_match_the_oracle_package_set(self):
        apis = self.contract["host"]["apis"]
        guard_text = _read(GUARD_PY)
        # V2: `host.apis` is bound as one contract path and the probe script is
        # rendered from it, so the guard names no package and no symbol of its
        # own. The anchor is the binding plus the renderer that consumes it.
        self.assertIn('"ORACLE_PACKAGES": "host.apis"', guard_text)
        self.assertIn("def _render_probe_script()", guard_text)
        # Contract v2 (FEAT-113 §8.2.1) adds ONE structural sub-key — the
        # loader ctx stub face — which is not a package: the oracle set is
        # still exactly the four packages, and the guard skips the structural
        # key by deriving it from the loader-ctx binding (never a literal).
        packages = {name: entry for name, entry in apis.items()
                    if name != "loader_ctx"}
        for package, entry in packages.items():
            self.assertTrue(entry["role"], package)
            self.assertTrue(entry["exports"], package)
        self.assertEqual(len(packages), 4)
        self.assertEqual(len(apis), 5)
        self.assertIn('"LOADER_CTX_MEMBERS": "host.apis.loader_ctx.members"',
                      guard_text)
        self.assertNotIn('"loader_ctx"', guard_text,
                         "the structural key must be derived, not restated")
        # Every declared symbol must be reachable from a role the renderer
        # resolves (`load` → YAML, `entryListSchema` → dialect,
        # `evaluate`/`isJsExpr` → loader, `resolveConfig` → cordis), otherwise
        # `_render_probe_script()` raises instead of running a partial probe.
        symbols = {symbol for entry in packages.values()
                   for symbol in entry["exports"]}
        for required in ("load", "entryListSchema", "evaluate", "isJsExpr",
                         "resolveConfig"):
            self.assertIn(required, symbols)

    def test_host_cli_commands_are_anchored(self):
        cli = self.contract["host"]["cli"]
        self.assertEqual(cli["version_command"], "dsh --version")
        self.assertIn("dsh --profile", cli["dump_config_command"])
        self.assertIn("--dump-config", cli["dump_config_command"])
        self.assertIn("plugin", cli["plugin_command"])
        self.assertEqual(cli["probe_invocation"],
                         "node --input-type=module --eval <probe>")
        manifest = json.loads(_read(
            _REPO_ROOT / "adapters" / "dsh" / "adapter-manifest.json"))
        self.assertEqual(cli["version_command"],
                         manifest["runtime_e2e"]["version_command"])
        self.assertIn("dsh plugin --profile <name> add",
                      _read(PATCH_FILE))
        guard_text = _read(GUARD_PY)
        self.assertIn('"--input-type=module", "--eval"', guard_text)

    def test_host_notes_record_the_profile_declaration(self):
        notes = self.contract["host"]["notes"]
        self.assertEqual(notes["profile_declaration"],
                         "host-install-mechanism-not-ours")

    def test_own_package_matches_package_json(self):
        own = self.contract["own"]["package"]
        package = json.loads(_read(_REPO_ROOT / "package.json"))
        self.assertEqual(own["name"], package["name"])
        self.assertEqual(own["type"], package["type"])
        self.assertEqual(own["main"], package["main"])
        self.assertEqual(own["engines_node"], package["engines"]["node"])
        self.assertEqual(own["dsh_bundle_patch_key"], "dsh.bundle.patch")
        self.assertEqual(own["exports"], package["exports"])
        self.assertEqual(own["files"], package["files"])
        self.assertTrue(
            package["dsh"]["bundle"]["patch"].endswith(self.contract["own"]["patch"]["file"]))
        self.assertEqual(self.contract["own"]["patch"]["file"], "cordis.patch.yml")

    def test_own_preset_and_markers_match_both_renderers(self):
        preset = self.contract["own"]["preset"]
        self.assertEqual(preset["id"], "governance")
        self.assertEqual(preset["version_marker"], ".dsh-bundle-version")
        self.assertEqual(preset["skill_root_marker"], "skill-root.txt")
        self.assertTrue((_REPO_ROOT / self.contract["own"]["overlay"]["path"]).is_file())
        self.assertTrue((_REPO_ROOT / preset["metadata"]).is_file())
        # V2: the renderers no longer spell the values — they declare which
        # contract field supplies each one. The traceability assertion is
        # therefore "the declared symbol is bound to the declared contract
        # path", not "the literal appears in the file" (which is precisely the
        # hard coding K-2 now fails on).
        launch_text = _read(LAUNCH_PY)
        for symbol, contract_path in (
                ("PRESET_ID", "own.preset.id"),
                ("PRESET_MARKER", "own.preset.version_marker"),
                ("SKILL_ROOT_MARKER", "own.preset.skill_root_marker")):
            self.assertIn(f'"{symbol}": "{contract_path}"', launch_text, symbol)
        lib_text = _read(LIB_INDEX)
        for symbol, contract_path in (
                ("presetId", "own.preset.id"),
                ("versionMarker", "own.preset.version_marker"),
                ("skillRootMarker", "own.preset.skill_root_marker")):
            self.assertIn(f"{symbol}: '{contract_path}'", lib_text, symbol)

    def test_own_render_tokens_match_both_renderers(self):
        tokens = self.contract["own"]["render"]["tokens"]
        self.assertEqual(sorted(tokens), [
            "__GOVERNANCE_REPO_ROOT__", "__GOVERNANCE_SHIMS_ROOT__",
            "__GOVERNANCE_SKILLS_ROOT__"])
        self.assertEqual(tokens["__GOVERNANCE_SKILLS_ROOT__"], "skills")
        self.assertEqual(tokens["__GOVERNANCE_SHIMS_ROOT__"],
                         "adapters/dsh/skill-shims")
        self.assertEqual(tokens["__GOVERNANCE_REPO_ROOT__"], "")
        launch_text = _read(LAUNCH_PY)
        lib_text = _read(LIB_INDEX)
        for token, relative in tokens.items():
            self.assertIn(token, launch_text, token)
            self.assertIn(token, lib_text, token)
            if relative:
                self.assertIn(relative.split("/")[-1], launch_text, relative)

    def test_own_render_leftover_scan_and_newline_policy(self):
        render = self.contract["own"]["render"]
        self.assertEqual(render["newline_policy"], "lf")
        self.assertEqual(render["leftover_scan"], "__[A-Za-z0-9_]+__")
        shape = render["custom_skill_dirs_shape"]
        self.assertEqual(shape["entry_count"], 2)
        self.assertEqual(shape["key_indent"], 4)
        self.assertEqual(shape["item_indent"], 6)
        template = _template_text()
        block = template.split("customSkillDirs:")[1].split("\n")
        self.assertEqual(len(block[1]) - len(block[1].lstrip()),
                         shape["item_indent"])
        self.assertEqual(sum(1 for line in block[1:3] if line.strip().startswith("-")),
                         shape["entry_count"])

    def test_own_patch_shape_invariants_hold_in_the_shipped_patch(self):
        invariants = self.contract["own"]["patch"]["shape_invariants"]
        self.assertEqual(sorted(invariants),
                         ["exactly-one-insert-row", "insert-row-requires-id", "no-!!js", "no-id-update",
                          "no-trust"])
        lines = [line for line in _read(PATCH_FILE).split("\n")
                 if line.strip() and not line.lstrip().startswith("#")]
        top_level = [line for line in lines if line.startswith("- ")]
        self.assertEqual(len(top_level), 1)
        self.assertTrue(top_level[0].startswith("- insert:"))
        self.assertFalse([line for line in lines if line.startswith("- id:")])
        text = "\n".join(lines)
        self.assertNotIn("trust:", text)
        self.assertNotIn("!!js", text)

    def test_own_paths_exist_unless_declared_pending(self):
        paths = self.contract["own"]["paths"]
        pending = set(self.contract["own"]["paths_pending"])
        self.assertTrue(pending <= set(paths))
        for key, relative in paths.items():
            if key in pending:
                continue
            self.assertTrue((_REPO_ROOT / relative).exists(), f"{key}:{relative}")
        # Every declared path is also inside the published file whitelist (or
        # under a shipped directory) — §2.4 own.package.files 判据.
        files = self.contract["own"]["package"]["files"]
        for key, relative in paths.items():
            predicate = any(
                relative == item or relative.startswith(item) for item in files
                if item.endswith("/"))
            self.assertTrue(predicate, f"{key}:{relative} not shipped")

    def test_own_checks_section_titles_and_exit_codes(self):
        checks = self.contract["own"]["checks"]
        # V2: the title is bound to the contract (`own.checks.compat_section_title`)
        # rather than restated, so the assertion is that the binding exists and
        # that the guard module's exported title is the declared value.
        guard_text = _read(GUARD_PY)
        self.assertIn('"COMPAT_SECTION_TITLE": "own.checks.compat_section_title"',
                      guard_text)
        self.assertEqual(dsh_compat.CHECK_SECTION_TITLE,
                         checks["compat_section_title"])
        from checks.dsh_smoke import emit_health_result
        with contextlib.redirect_stdout(io.StringIO()) as output:
            emit_health_result({"verdict": "PASS", "reason": "fixture", "exit_code": 0,
                                "isolation": {"real_home_writes": 0}})
        self.assertIn(checks["smoke_section_title"], output.getvalue().splitlines()[1])
        self.assertEqual(checks["upgrade_regression_label"],
                         "dsh preset-session smoke (isolated upgrade regression)")
        exit_codes = checks["exit_codes"]
        self.assertEqual(exit_codes["smoke"], {"PASS": 0, "FAIL": 1,
                                               "REFUSED": 2})
        self.assertEqual(exit_codes["doctor"], {"NONE": 0, "FAIL": 1,
                                                "REFUSED": 2})
        launch_text = _read(LAUNCH_PY)
        for token, code in exit_codes["smoke"].items():
            self.assertIn(f"SMOKE_EXIT_{token} = {code}", launch_text, token)

    def test_own_adapter_manifest_required_fields_are_read_by_print_manifest(self):
        required = self.contract["own"]["adapter_manifest"]["required_fields"]
        launch_text = _read(LAUNCH_PY)
        for field in required:
            self.assertRegex(launch_text,
                             r"manifest\[[\"']" + re.escape(field) + r"[\"']\]",
                             field)
        manifest = json.loads(_read(
            _REPO_ROOT / "adapters" / "dsh" / "adapter-manifest.json"))
        for field in required:
            self.assertIn(field, manifest, field)

    def test_own_host_row_invariants_match_the_python_side(self):
        host_row = self.contract["own"]["host_row"]
        self.assertEqual(host_row["entry"], "lib/index.js")
        self.assertEqual(host_row["export_surface"],
                         ["apply", "ensurePreset", "name", "renderComposition"])
        self.assertIs(host_row["apply_never_throws"], True)
        self.assertIs(host_row["warn_only"], True)
        self.assertIs(host_row["top_level_io"], False)
        self.assertEqual(host_row["runtime_dependencies"], [])
        lib_text = _read(LIB_INDEX)
        for name in host_row["export_surface"]:
            self.assertRegex(lib_text, r"export (?:const|function) " + name + r"\b")
        self.assertIn("catch (error)", lib_text)
        self.assertIn("ctx?.logger?.warn", lib_text)
        self.assertIn("node:fs", lib_text)

    def test_elimination_baseline_is_the_audit_report_classification(self):
        derived = _audit_marker_sets()
        baseline = self.contract["elimination"]["audit_baseline"]
        self.assertEqual(baseline["total"], 100)
        for key, field in ((_NECESSARY, "necessary_ids"),
                           (_WEAKENABLE, "weakenable_ids"),
                           (_ELIMINABLE, "eliminable_ids"),
                           (_HISTORICAL, "historical_ids")):
            self.assertEqual(baseline[field], derived[key], field)
        union = set()
        for field in ("necessary_ids", "weakenable_ids", "eliminable_ids",
                      "historical_ids"):
            union.update(baseline[field])
        self.assertEqual(len(union), baseline["total"])
        reconciliation = baseline["count_reconciliation"]
        self.assertEqual(reconciliation["stated_in_audit_section_2_11"]
                         ["necessary"], 62)
        self.assertEqual(reconciliation["derived_from_section_2_markers"]
                         ["necessary"], len(derived[_NECESSARY]))


class TestTokenAgreement(unittest.TestCase):
    """K-4: token set equality + no leftover token after rendering."""

    def setUp(self):
        self.tokens = _contract()["own"]["render"]["tokens"]
        self.template = _template_text()

    def test_template_token_set_equals_the_contract_token_set(self):
        found = set(_TEMPLATE_TOKEN_RE.findall(self.template))
        self.assertEqual(found, set(self.tokens), found ^ set(self.tokens))

    def test_every_declared_token_is_used_by_the_template(self):
        for token in self.tokens:
            self.assertIn(token, self.template, token)

    def test_rendered_template_leaves_no_token_behind(self):
        rendered = self.template
        for token, relative in self.tokens.items():
            value = "/pkg" if not relative else f"/pkg/{relative}"
            rendered = rendered.replace(token, value)
        left = _TEMPLATE_TOKEN_RE.findall(rendered)
        self.assertEqual(left, [])

    def test_leftover_scan_pattern_catches_a_misspelt_token(self):
        pattern = re.compile(_contract()["own"]["render"]["leftover_scan"])
        self.assertTrue(pattern.search("__GOVERNANCE_SKILLS_ROOTS__"))
        self.assertTrue(pattern.search("__Governance_Repo_Root__"))
        self.assertFalse(pattern.search("no token in here"))


class TestCoverageAndElimination(unittest.TestCase):
    """K-9 + the unit-level half of K-8: coverage claims and their closable refs."""

    def setUp(self):
        self.contract = _contract()
        self.entries = self.contract["coverage"]["entries"]
        self.dispositions = self.contract["elimination"]["dispositions"]
        self.baseline = self.contract["elimination"]["audit_baseline"]

    def test_dispositions_cover_every_audit_id_exactly_once(self):
        ids = [item["id"] for item in self.dispositions]
        self.assertEqual(len(ids), len(set(ids)), "duplicate disposition")
        covered = set(ids)
        expected = set()
        for field in ("necessary_ids", "weakenable_ids", "eliminable_ids",
                      "historical_ids"):
            expected.update(self.baseline[field])
        self.assertEqual(covered - expected, set())
        self.assertEqual(expected - covered, set())
        self.assertEqual(len(covered), self.baseline["total"])

    def test_disposition_classes_match_the_baseline(self):
        fields = {"necessary": "necessary_ids", "weakenable": "weakenable_ids",
                  "eliminable": "eliminable_ids", "historical": "historical_ids"}
        for item in self.dispositions:
            self.assertIn(item["class"], fields, item["id"])
            self.assertIn(item["id"], self.baseline[fields[item["class"]]],
                          item["id"])
            self.assertTrue(item["decision"], item["id"])
            self.assertTrue(item["evidence"], item["id"])

    def test_eliminated_dispositions_carry_a_removal_slice(self):
        for item in self.dispositions:
            self.assertIsInstance(item["slice"], list, item["id"])
            for token in item["slice"]:
                self.assertRegex(token, r"^V\d+$", item["id"])
            if item.get("removed_at") is not None:
                self.assertIn(item["removed_at"], item["slice"], item["id"])
            if item.get("weakened_at") is not None:
                self.assertIn(item["weakened_at"], item["slice"], item["id"])

    def test_every_necessary_dependency_has_a_coverage_claim(self):
        declared = set()
        for entry in self.entries:
            declared.update(entry["audit_ids"])
        missing = sorted(set(self.baseline["necessary_ids"]) - declared,
                         key=lambda item: int(item[2:]))
        self.assertEqual(missing, [], "necessary dependency without coverage claim")
        self.assertGreaterEqual(len(self.baseline["necessary_ids"]), 62)

    def test_coverage_union_covers_every_audit_id(self):
        declared = set()
        for entry in self.entries:
            declared.update(entry["audit_ids"])
        expected = set()
        for field in ("necessary_ids", "weakenable_ids", "eliminable_ids",
                      "historical_ids"):
            expected.update(self.baseline[field])
        self.assertEqual(expected - declared, set())
        self.assertEqual(len(declared), self.baseline["total"])

    def test_no_duplicate_subject_and_no_empty_audit_ids(self):
        subjects = [entry["subject"] for entry in self.entries]
        duplicates = sorted({item for item in subjects
                             if subjects.count(item) > 1})
        self.assertEqual(duplicates, [])
        for entry in self.entries:
            self.assertTrue(entry["audit_ids"], entry["subject"])
            self.assertEqual(len(entry["audit_ids"]),
                             len(set(entry["audit_ids"])), entry["subject"])

    def test_subjects_resolve_inside_the_contract(self):
        # K-8: the `subject` of every claim must be a real contract path. A
        # declared-but-null field (evidence.verified_on) still resolves — the
        # failure mode this catches is a path the contract does not declare.
        for entry in self.entries:
            resolved = dsh_contract.get(entry["subject"], self.contract)
            del resolved
            self.assertRegex(entry["subject"], r"^(evidence|host|own|coverage|"
                                               r"elimination)\.")

    def test_declared_but_unadjudicated_fields_still_resolve(self):
        self.assertIsNone(dsh_contract.get("evidence.verified_on", self.contract))
        self.assertIsNone(dsh_contract.get("evidence.compat_range", self.contract))

    def test_coverage_vocabulary_is_closed(self):
        ladder = {"strong", "medium", "weak", "none"}
        for entry in self.entries:
            self.assertIn(entry["target"], ladder, entry["subject"])
            self.assertIn(entry["necessity"],
                          {"necessary", "weakenable", "eliminable",
                           "historical"}, entry["subject"])
            self.assertIsInstance(entry["guard"], list)
            self.assertIsInstance(entry["negative_fixtures"], list)
            self.assertIsInstance(entry["requires"], list)

    def test_a_strong_target_carries_a_negative_fixture(self):
        for entry in self.entries:
            if entry["target"] == "strong":
                self.assertTrue(entry["negative_fixtures"], entry["subject"])

    def test_a_necessary_entry_is_never_unguarded(self):
        for entry in self.entries:
            if entry["necessity"] == "necessary":
                self.assertNotEqual(entry["target"], "none", entry["subject"])
                self.assertTrue(entry["guard"], entry["subject"])

    def test_guard_references_resolve_to_existing_tests_or_checks(self):
        tests = _guard_test_refs()
        checks = _registered_check_tokens()
        for entry in self.entries:
            for guard in entry["guard"]:
                if "::" in guard:
                    filename, method = guard.split("::", 1)
                    self.assertIn(filename, tests, guard)
                    self.assertIn(method, tests[filename], guard)
                else:
                    self.assertIn(guard, checks, guard)

    def test_negative_fixture_references_are_emittable_or_declared(self):
        for entry in self.entries:
            for fixture in entry["negative_fixtures"]:
                self.assertIn(
                    fixture, dsh_fixtures.known_fixture_ids(),
                    f"{fixture} ({entry['subject']}) is neither emittable nor "
                    f"declared deferred")

    def test_requires_vocabulary_is_closed(self):
        for entry in self.entries:
            for requirement in entry["requires"]:
                self.assertIn(requirement, {"node", "dsh-plane"},
                              entry["subject"])

    def test_overlay_coverage_subjects_resolve(self):
        contract = _contract()
        subjects = {entry["subject"] for entry in contract["coverage"]["entries"]}
        for key in ("own.overlay.rows", "host.row_contract.config_field"):
            self.assertIn(key, subjects)
            self.assertTrue(dsh_contract.get(key, contract))


class TestOutsideContractScan(unittest.TestCase):
    """K-2 (V2 form): no consumer holds a host fact of its own.

    Complies with K-11's allowlist constraints at unit scope: every entry
    carries `literal` + `reason` + `since_slice`, the entry count is under the
    frozen budget, and each entry is *necessary* (removing it must produce a
    violation). The budget's anchor lives in this file, not in the contract —
    R1 N-2: a contract-owned budget could be raised in the same commit as the
    entry it should reject.
    """

    def test_no_outside_contract_host_literal_in_any_consumer(self):
        violations = k2_scan()
        self.assertEqual(
            violations, [],
            "outside-contract host literal(s) found:\n" + k2_report(violations))

    def test_every_scanned_consumer_exists(self):
        # A renamed consumer must fail loudly instead of silently dropping out
        # of the scan (the failure mode that would let hard coding return).
        for relative in K2_CONSUMERS:
            self.assertTrue((_REPO_ROOT / relative).is_file(), relative)

    def test_allowlist_is_within_budget_and_well_formed(self):
        self.assertLessEqual(len(K2_ALLOWLIST), ALLOWLIST_BUDGET)
        for entry in K2_ALLOWLIST:
            self.assertTrue(entry["literal"], entry)
            self.assertTrue(entry["reason"].strip(), entry)
            self.assertTrue(entry["since_slice"], entry)
            self.assertTrue(entry["files"], entry)
            for relative in entry["files"]:
                self.assertIn(relative, K2_CONSUMERS, entry)

    def test_every_allowlist_entry_is_necessary(self):
        # An allowlist entry that suppresses nothing is a budget spent for free;
        # removing it must produce at least one violation.
        self.assertLessEqual(len(K2_ALLOWLIST), ALLOWLIST_BUDGET)
        for entry in K2_ALLOWLIST:
            without = tuple(item for item in K2_ALLOWLIST if item is not entry)
            violations = k2_scan(allowlist=without)
            matched = [item for item in violations
                       if item[3] == entry["literal"]
                       and item[0] in entry["files"]]
            self.assertTrue(
                matched,
                f"allowlist entry {entry['literal']!r} suppresses nothing — "
                f"drop it (budget {len(K2_ALLOWLIST)}/{ALLOWLIST_BUDGET})")

    def test_an_undeclared_package_name_in_a_consumer_is_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "lib" / "index.js"
            target.parent.mkdir(parents=True)
            target.write_text(
                "const pkg = '@deepseek-ai/dsh-totally-new'\n", encoding="utf-8")
            violations = k2_scan(paths=("lib/index.js",), root=root)
            self.assertEqual(len(violations), 1, violations)
            self.assertEqual(violations[0][0], "lib/index.js")
            self.assertEqual(violations[0][1], 1)
            self.assertEqual(violations[0][3], "@deepseek-ai/dsh-totally-new")
            self.assertIn("lib/index.js:1 [package]", k2_report(violations))

    def test_an_undeclared_env_var_is_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "adapters" / "dsh" / "launch.py"
            target.parent.mkdir(parents=True)
            target.write_text(
                'env = os.environ.get("DSH_SOMETHING_ELSE")\n'
                'other = os.environ.get("DSH_HOME")\n',
                encoding="utf-8")
            violations = k2_scan(paths=("adapters/dsh/launch.py",), root=root)
            found = {(kind, literal) for _f, _l, kind, literal in violations}
            self.assertIn(("env", "DSH_SOMETHING_ELSE"), found)
            # `DSH_HOME` IS declared, so reading it is not a violation — the
            # scan accepts declared values, it does not ban the names.
            self.assertNotIn(("env", "DSH_HOME"), found)

    def test_a_backtick_literal_is_scanned_like_any_other_string(self):
        # CODE R0 F-05: `_QUOTED_RE` used to accept only `'` and `"`, so the
        # backtick form — the native spelling in `lib/index.js` — was invisible
        # to the package class. Both backtick shapes are covered: a plain
        # template and the `String.raw` form.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "lib" / "index.js"
            target.parent.mkdir(parents=True)
            target.write_text(
                "const a = `@deepseek-ai/dsh-backtick-new`\n"
                "const b = String.raw`@deepseek-ai/dsh-raw-new`\n",
                encoding="utf-8")
            violations = k2_scan(paths=("lib/index.js",), root=root)
            self.assertEqual([item[3] for item in violations],
                             ["@deepseek-ai/dsh-backtick-new",
                              "@deepseek-ai/dsh-raw-new"], violations)
            self.assertIn("lib/index.js:2 [package]", k2_report(violations))

    def test_path_and_marker_classes_judge_quoted_literals_not_lines(self):
        # CODE R0 F-04: the path/marker classes used to match the RAW line, which
        # made a prose line that merely names a path fragment a FALSE POSITIVE —
        # it is not a literal at all. Judging the quoted content removes that
        # while keeping the declared/undeclared judgment inside literals.
        #
        # Note on what can be a violation: the classes recognize the spellings
        # the contract declares, so a quoted declared spelling is accepted. The
        # regression under test is therefore the direction that actually broke —
        # prose must not be judged — and the literal direction is covered by
        # `test_the_literal_classes_accept_only_declared_spellings` and by the
        # package class above.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "lib" / "index.js"
            target.parent.mkdir(parents=True)
            target.write_text(
                "// the .agent-presets root and .dsh-bundle-version marker\n"
                "/* a docstring naming .agent-presets/skill-root.txt too */\n"
                'const ok = ".agent-presets"\n'
                'const tpl = "agent.cordis.yml.template"\n',
                encoding="utf-8")
            self.assertEqual(k2_scan(paths=("lib/index.js",), root=root), [])
            # The same fragments without comments are literals, and a declared
            # literal is still accepted — proving the class reads the string,
            # not the line.
            target.write_text(
                'const a = ".agent-presets"\n'
                'const b = "agent.cordis.yml.template"\n',
                encoding="utf-8")
            self.assertEqual(k2_scan(paths=("lib/index.js",), root=root), [])

    def test_quoted_literals_reads_all_three_quote_styles(self):
        # The extraction primitive the path/marker/package classes share.
        self.assertEqual(
            quoted_literals("a('x') b(\"y\") c(`z`)"),
            ["x", "y", "z"])
        self.assertEqual(quoted_literals('no literals here'), [])

    def test_the_literal_classes_accept_only_declared_spellings(self):
        # The path/marker classes judge the spellings the contract declares, and
        # the boundary rule keeps `agent.cordis.yml.template` (the declared
        # render-source name, `own.preset.template`) out of the path class. An
        # unrelated name that merely *looks* like a marker is not a contract
        # literal at all — the scan is literal-based, not shape-based — while an
        # undeclared environment-variable read is a violation.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "adapters" / "dsh" / "launch.py"
            target.parent.mkdir(parents=True)
            target.write_text(
                'a = home / ".agent-presets"\n'
                'b = "agent.cordis.yml"\n'
                'c = ".dsh-bundle-version"\n'
                'd = "other-bundle-version"\n'
                'e = "agent-presets/governance/overlay.cordis.yml"\n',
                encoding="utf-8")
            self.assertEqual(k2_scan(paths=("adapters/dsh/launch.py",), root=root), [])
            target.write_text(
                'g = os.environ.get("DSH_ANOTHER_HOME")\n', encoding="utf-8")
            violations = k2_scan(paths=("adapters/dsh/launch.py",), root=root)
            self.assertEqual([item[3] for item in violations],
                             ["DSH_ANOTHER_HOME"], violations)
            self.assertIn("adapters/dsh/launch.py:1 [env]", k2_report(violations))

    def test_an_allowlist_entry_out_of_scope_is_still_a_violation(self):
        # The exemption is file-scoped: the same literal in another consumer
        # must fail. (This is what stops an allowlist entry from becoming a
        # repo-wide amnesty.) Exercised with a synthetic entry, because the
        # shipped allowlist is empty at V2.
        entry = {"literal": "@totally-new/pkg",
                 "reason": "synthetic (test-local)",
                 "since_slice": "V2",
                 "files": ("skills/software-project-governance/infra/dsh_compat.py",)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "adapters" / "dsh" / "launch.py"
            target.parent.mkdir(parents=True)
            target.write_text("const p = '@totally-new/pkg'\n", encoding="utf-8")
            declared_elsewhere = k2_scan(paths=("adapters/dsh/launch.py",), root=root,
                                         allowlist=(entry,))
            self.assertEqual([item[3] for item in declared_elsewhere],
                             ["@totally-new/pkg"], declared_elsewhere)
            # …and the same synthetic entry does cover its declared file.
            dsh_compat_rel = ("skills/software-project-governance/infra/"
                              "dsh_compat.py")
            in_scope = root / dsh_compat_rel
            in_scope.parent.mkdir(parents=True)
            in_scope.write_text("const p = '@totally-new/pkg'\n", encoding="utf-8")
            covered = k2_scan(paths=(dsh_compat_rel,), root=root,
                              allowlist=(entry,))
            self.assertEqual(covered, [])

    def test_a_marker_name_inside_a_longer_name_is_not_a_violation(self):
        # Boundary discipline: `agent.cordis.yml.template` contains
        # `agent.cordis.yml`, and the template's own file name must not be
        # reported as an undeclared composition-file literal.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "lib" / "index.js"
            target.parent.mkdir(parents=True)
            target.write_text(
                "// agent-presets/governance/overlay.cordis.yml\n",
                encoding="utf-8")
            self.assertEqual(k2_scan(paths=("lib/index.js",), root=root), [])


class TestConsumerContractReads(unittest.TestCase):
    """R0 BT-R-04: the per-field mutation matrix.

    The parity suite (`test_dsh_adapter.py::test_js_and_python_renderers_agree`)
    proves that the three render paths still produce the same bytes — **output
    equivalence only.** It cannot tell a consumer that *reads* the contract from
    one that kept a shadow copy of the same values, because both would render
    identically. So each field below is mutated, and the consumer must be
    observed *changing* because of it:

      * `own.render.tokens`            → `renderComposition` (JS) + `render_composition` (Py)
      * `own.preset.id`                → `ensurePreset` destination directory (JS)
      * `own.preset.version_marker`    → the marker file `ensurePreset` writes (JS)
      * `own.preset.skill_root_marker` → the marker file the launcher writes (Py)
      * `host.env.home_var`            → the variable `ensurePreset` reads (JS)
      * `host.home.user_preset_dir`    → the preset-root segment `ensurePreset` uses (JS)
      * `host.rows[]`                  → the template ↔ contract row judgment

    **Isolation (CODE R0 F-09).** The mutation is applied to a throwaway COPY of
    the repository (`%TEMP%/…`), never to the working tree. The reviewer's own
    session produced the empirical case for this: an in-place swap whose
    `finally` did not run left the real contract briefly rewritten and raced a
    concurrent task. A copy cannot do that — and the shipped contract's SHA-256
    is asserted unchanged before and after, in `setUp`/`tearDown`, so a leak is
    still detected if one ever happens.

    Both consumers locate the contract relative to their own file (`lib/index.js`
    via `import.meta.url`; `launch.py` via `__file__`), so pointing them at the
    copy is what makes them read the mutated contract.

    **JS-side mutation runs in a separate process**, deliberately: `lib/index.js`
    memoizes its contract view for the life of the process (J-3), and adding a
    `reset` export for tests would violate J-5 (no new exports). A fresh `node`
    process is therefore the only honest way to observe a re-read — and
    `test_dsh_adapter.py:1127` already establishes the `subprocess.run([node,…])`
    shape.
    """

    #: Files the copies do not need; keeping the copy small keeps the matrix fast.
    _COPY_IGNORE = shutil.ignore_patterns(
        ".git", "node_modules", "__pycache__", "*.pyc", ".governance",
        "docs", "commands", "agents", "skills")

    #: The two subtrees a consumer needs (its own module + the contract), plus
    #: the preset payload the JS row renders.
    _COPY_KEEP = ("lib", "adapters", "agent-presets")

    @classmethod
    def setUpClass(cls):
        cls.contract_path = dsh_contract.contract_path()
        cls.original_bytes = cls.contract_path.read_bytes()
        cls.original_sha = _sha256(cls.original_bytes)
        cls.original = json.loads(cls.original_bytes.decode("utf-8"))
        dsh_contract.reset_cache()

    def setUp(self):
        # The shipped contract must be pristine before every case; if an earlier
        # process (or a concurrent task) left it dirty, name that here instead of
        # cascading into a confusing mutation result.
        self.assertEqual(_sha256(self.contract_path.read_bytes()),
                         self.original_sha,
                         f"the shipped contract is not pristine: {self.contract_path}")
        self._temp_root = None

    def tearDown(self):
        if self._temp_root is not None:
            shutil.rmtree(self._temp_root, ignore_errors=True)
        # The copy is where mutations live, so the shipped file must still be
        # byte-identical at the end of every case (F-09's acceptance evidence).
        self.assertEqual(_sha256(self.contract_path.read_bytes()),
                         self.original_sha,
                         "a mutation test leaked into the shipped contract")

    # ── helpers ────────────────────────────────────────────────────────────
    def _mutated_repo(self, mutate):
        """A throwaway repo copy whose contract has ``mutate`` applied.

        Returns the copy's root. The copy carries only the subtrees the three
        consumers need (`lib/`, `adapters/`, `agent-presets/`) — enough for
        `lib/index.js` (`packageRoot()` = one level above `lib/`),
        `adapters/dsh/launch.py` (`ROOT` = two levels above the adapter dir) and
        `dsh_contract.contract_path()` (`parents[3]` for the repo root) to
        resolve inside the copy.
        """
        root = Path(tempfile.mkdtemp(prefix="feat030-mut-"))
        self._temp_root = root
        for name in self._COPY_KEEP:
            shutil.copytree(_REPO_ROOT / name, root / name)
        # `dsh_contract.contract_path()` is derived from the accessor's own
        # location, so the copy needs the infra directory too — the module file
        # itself is what `lib/index.js`/`launch.py` never import.
        infra_rel = Path("skills") / "software-project-governance" / "infra"
        (root / infra_rel).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_INFRA_DIR / "dsh_contract.py",
                        root / infra_rel / "dsh_contract.py")
        contract = root / dsh_contract.CONTRACT_REL
        mutated = json.loads(json.dumps(self.original))
        mutate(mutated)
        contract.write_bytes(
            json.dumps(mutated, ensure_ascii=False, indent=2).encode("utf-8"))
        return root

    def _node(self, root, script, env=None, argv=()):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (JS consumer cannot be exercised)")
        environment = os.environ.copy() if env is None else env
        result = subprocess.run(
            [node, "--input-type=module", "-e", script, *argv],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=environment, cwd=str(root),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _lib_uri(self, root):
        return (root / "lib" / "index.js").resolve().as_uri()

    def _assert_row_warns_and_writes_nothing(self, root, roots, *,
                                             code="HOST_NO_LOADER_TREE",
                                             extra_env=None):
        """DEC-366 ②: the inserted row never renders; it warns with a code.

        ``roots`` is every directory the row could conceivably have rendered
        into for this case (the declared home plus any mutated alternative). No
        `.agent-presets`/derived preset root may appear under ANY of them.
        """
        env = os.environ.copy()
        env["DSH_HOME"] = str(roots[0])
        env.update(extra_env or {})
        out = self._node(
            root,
            "import { apply } from "
            f"{json.dumps(self._lib_uri(root))};"
            "const warns = [];"
            "apply({ logger: { warn: (m) => warns.push(String(m)),"
            " info: () => {} } });"
            "process.stdout.write(JSON.stringify(warns));", env=env)
        warns = json.loads(out)
        self.assertTrue(warns, "a non-native outcome must be reported, not silent")
        self.assertTrue(any(code in warning for warning in warns), warns)
        for candidate in roots:
            candidate = Path(candidate)
            self.assertFalse(
                (candidate / ".agent-presets").exists(),
                f"the row rendered a preset directory under {candidate}")
        return warns

    def _pyprobe(self, root, script, env=None):
        """Run a Python snippet against the COPY's `launch.py`/accessor.

        Both directories go on `sys.path`: the copy's `infra/` (so `import launch`
        — which adds its own `INFRA_DIR` for the accessor — and a direct
        `import dsh_contract` resolve inside the copy) and the copy's
        `adapters/dsh/` (the launcher itself). The copy is the cwd, and `HOME` /
        `USERPROFILE` are redirected to it too, so nothing outside the copy can
        be reached by accident.
        """
        environment = os.environ.copy() if env is None else env
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(root / "skills" / "software-project-governance" / "infra"),
             str(root / "adapters" / "dsh"),
             environment.get("PYTHONPATH", "")])
        environment["HOME"] = str(root)
        environment["USERPROFILE"] = str(root)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=environment, cwd=str(root),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _assert_copy_restored(self, root):
        """Isolation predicate: the shipped contract is untouched, the copy holds
        the mutation.

        "Restored" here means the *shipped* file — the mutation lives only in the
        throwaway copy, so the shipped SHA-256 must equal the baseline that
        `setUp` checked, and the copy must still carry what was written into it.
        """
        self.assertEqual(_sha256(self.contract_path.read_bytes()), self.original_sha,
                         "the shipped contract changed during a mutation test")
        self.assertNotEqual(
            _sha256((root / dsh_contract.CONTRACT_REL).read_bytes()),
            self.original_sha,
            "the copy does not carry the mutation (nothing was under test)")

    # ── the matrix ─────────────────────────────────────────────────────────
    def test_mutation_own_render_tokens_is_read_by_the_js_renderer(self):
        def mutate(contract):
            # The declared set is REPLACED: the real token is no longer declared,
            # so a renderer that read the contract leaves it unresolved.
            contract["own"]["render"]["tokens"] = {
                "__MUTATED_SKILLS_ROOT__": "skills",
                "__GOVERNANCE_SHIMS_ROOT__": "adapters/dsh/skill-shims",
                "__GOVERNANCE_REPO_ROOT__": "",
            }
        root = self._mutated_repo(mutate)
        self.assertNotEqual(_sha256((root / dsh_contract.CONTRACT_REL).read_bytes()),
                            self.original_sha, "the copy was not mutated")
        script = (
            f"import {{ renderComposition }} from {json.dumps(self._lib_uri(root))};"
            "import { readFileSync } from 'node:fs';"
            "const t = readFileSync(process.argv[1], 'utf8');"
            "process.stdout.write(JSON.stringify("
            "renderComposition(t, process.argv[2])));"
        )
        payload = json.loads(self._node(
            root, script, argv=(str(root / "agent-presets" / "governance"
                                    / "overlay.cordis.yml"),
                                str(root).replace("\\", "/"))))
        # The template's real token is left in the text and reported: the
        # renderer followed the contract rather than a fixed three-token table.
        self.assertIn("__GOVERNANCE_SKILLS_ROOT__", payload["text"])
        self.assertIn("__GOVERNANCE_SKILLS_ROOT__", payload["leftovers"])
        self._assert_copy_restored(root)
        # …and with the copy's pristine contract the template leaves nothing.
        pristine = self._mutated_repo(lambda _contract: None)
        payload = json.loads(self._node(
            pristine,
            "import { renderComposition } from "
            f"{json.dumps(self._lib_uri(pristine))};"
            "import { readFileSync } from 'node:fs';"
            "process.stdout.write(JSON.stringify(renderComposition("
            "readFileSync(process.argv[1], 'utf8'), process.argv[2])));",
            argv=(str(pristine / "agent-presets" / "governance"
                      / "overlay.cordis.yml"),
                  str(pristine).replace("\\", "/"))))
        self.assertEqual(payload["leftovers"], [], payload)

    def test_mutation_own_render_tokens_is_read_by_the_python_renderer(self):
        def mutate(contract):
            contract["own"]["render"]["tokens"] = {
                "__MUTATED_SKILLS_ROOT__": "skills",
                "__GOVERNANCE_SHIMS_ROOT__": "adapters/dsh/skill-shims",
                "__GOVERNANCE_REPO_ROOT__": "",
            }
        root = self._mutated_repo(mutate)
        out = self._pyprobe(root, (
            "import json, launch\n"
            "print(json.dumps({'rendered': launch.render_overlay(),\n"
            "                  'tokens': sorted(launch._token_paths())}))\n"))
        payload = json.loads(out)
        # The Python renderer refuses to emit a composition with an unresolved
        # token — and the unresolved one is the token the mutated contract no
        # longer declares.
        self.assertEqual(payload["rendered"], "")
        self.assertEqual(payload["tokens"], ["__GOVERNANCE_REPO_ROOT__",
                                             "__GOVERNANCE_SHIMS_ROOT__",
                                             "__MUTATED_SKILLS_ROOT__"])
        self._assert_copy_restored(root)
        pristine = self._mutated_repo(lambda _contract: None)
        out = self._pyprobe(pristine, (
            "import launch\n"
            "print(len(launch.render_overlay()))\n"))
        self.assertGreater(int(out.strip()), 0, out)

    def test_mutation_own_preset_id_never_renders_a_legacy_preset(self):
        # DEC-366 ②: the row has no sync destination any more, so a mutated
        # preset id must not resurrect one. This test used to assert the other
        # direction (a destination appeared under the mutated id); the pinned
        # fact is now "no write, one warning naming the structured cause".
        def mutate(contract):
            contract["own"]["preset"]["id"] = "governance-mutated"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            self._assert_row_warns_and_writes_nothing(root, [td])
        self._assert_copy_restored(root)

    def test_mutation_own_preset_version_marker_never_names_a_marker_file(self):
        # DEC-366 ②: the version marker is another legacy-renderer input; with
        # the renderer out of the row path, mutating it must change nothing.
        def mutate(contract):
            contract["own"]["preset"]["version_marker"] = ".mutated-version"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            self._assert_row_warns_and_writes_nothing(root, [td])
            self.assertFalse((Path(td) / ".mutated-version").exists())
        self._assert_copy_restored(root)

    def test_mutation_own_skill_root_marker_names_the_launcher_marker_file(self):
        def mutate(contract):
            contract["own"]["preset"]["skill_root_marker"] = "mutated-root.txt"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as tmp:
            out = self._pyprobe(root, (
                "import json, launch\n"
                f"ok = launch.write_rendered_preset(__import__('pathlib')"
                f".Path({str(Path(tmp) / 'staging')!r}), derived={{'composition': '[]', 'provenance': {{}}}})\n"
                "import pathlib\n"
                "names = sorted(p.name for p in "
                f"pathlib.Path({str(Path(tmp) / 'staging')!r}).iterdir())\n"
                "print(json.dumps({'ok': ok, 'names': names}))\n"))
        payload = json.loads(out)
        self.assertTrue(payload["ok"], payload)
        self.assertIn("mutated-root.txt", payload["names"], payload)
        self.assertNotIn("skill-root.txt", payload["names"], payload)
        self._assert_copy_restored(root)

    def test_mutation_host_env_home_var_never_selects_a_render_home(self):
        # F-10's old shape proved the row READ the declared home variable by
        # letting it render there. DEC-366 ② removes the render, so the binding
        # is now proved negatively: with BOTH the declared and the original
        # variables pointed at distinct directories, neither may gain a preset.
        def mutate(contract):
            contract["host"]["env"]["home_var"] = "DSH_HOME_MUTATED"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "wrong-home"
            target = Path(td) / "right-home"
            self._assert_row_warns_and_writes_nothing(
                root, [other, target],
                extra_env={"DSH_HOME_MUTATED": str(target)})
            self.assertFalse(other.exists(),
                             "the row wrote through the un-mutated home variable")
        self._assert_copy_restored(root)

    def test_mutation_host_home_user_preset_dir_never_selects_a_render_root(self):
        # `host.home.user_preset_dir` named the preset root segment. The row no
        # longer renders, so neither the mutated nor the default root may appear.
        def mutate(contract):
            contract["host"]["home"]["user_preset_dir"] = ".mutated-presets"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            self._assert_row_warns_and_writes_nothing(root, [td])
            self.assertFalse((Path(td) / ".mutated-presets").exists(),
                             "the row wrote through the mutated preset root")
        self._assert_copy_restored(root)


class TestGuardContractFailureVerdicts(unittest.TestCase):
    """§2.5.1/§2.5 C-3 as executable acceptance (CODE R0 F-02/F-03).

    The `dsh_compat` guard consumes the contract too, and the design fixes what a
    contract failure must look like for it:

      * `ContractUnreadable` (the contract is not there) is an *environment*
        fact → `NOT_RUN`, never a gate issue;
      * `ContractMalformed` / `ContractSchemaUnknown` (the contract is there and
        wrong) is a **product defect** → `FAIL`, explicitly never downgraded to
        `NOT_RUN`.

    Both halves used to be unreachable: the guard read its declared facts at
    import time, so *any* contract defect aborted the import and the CLI exited
    with a traceback instead of a verdict (F-02). And a contract that could not
    supply the probe facts was reported as `NOT_RUN` — the same status as "no dsh
    installed" (F-03), which is exactly the conflation §2.5.1 forbids.

    Each case runs in a **fresh process against a throwaway COPY of the repo**:
    import-time behaviour is part of what is under test, and
    `dsh_contract.contract_path()` resolves from the accessor's own location, so
    a copy of the tree is the only way to point the guard at a different
    contract. The shipped contract is asserted unchanged before and after.
    """

    _COPY_FOR_GUARD = ("lib", "adapters", "agent-presets", "package.json")

    def setUp(self):
        self.contract_path = dsh_contract.contract_path()
        self.original_bytes = self.contract_path.read_bytes()
        self.original_sha = _sha256(self.original_bytes)
        self.original = json.loads(self.original_bytes.decode("utf-8"))
        dsh_contract.reset_cache()
        self._temp_root = None

    def tearDown(self):
        if self._temp_root is not None:
            shutil.rmtree(self._temp_root, ignore_errors=True)
        self.assertEqual(_sha256(self.contract_path.read_bytes()), self.original_sha,
                         "a guard scenario leaked into the shipped contract")

    def _guard_repo(self, contract_bytes=None, drop=False):
        """A repo copy carrying the accessor + the guard + a chosen contract."""
        root = Path(tempfile.mkdtemp(prefix="feat030-guard-"))
        self._temp_root = root
        for name in self._COPY_FOR_GUARD:
            source = _REPO_ROOT / name
            if source.is_dir():
                shutil.copytree(source, root / name)
            else:
                shutil.copyfile(source, root / name)
        infra_rel = Path("skills") / "software-project-governance" / "infra"
        (root / infra_rel).mkdir(parents=True, exist_ok=True)
        # FEAT-113 S2: `dsh_walk.py` rides along — the guard imports its
        # traversal sibling at import time, and this throwaway repo must carry
        # the pair the way the real tree does.
        for module in ("dsh_contract.py", "dsh_compat.py", "dsh_walk.py"):
            shutil.copyfile(_INFRA_DIR / module, root / infra_rel / module)
        target = root / dsh_contract.CONTRACT_REL
        if drop:
            target.unlink()
        elif contract_bytes is not None:
            target.write_bytes(contract_bytes)
        return root

    def _run_guard(self, root, *, without_host=False):
        """Import + run the guard in a fresh process; return the parsed outcome.

        The probe captures both the report and the CLI exit code, and it never
        lets a traceback decide the result: an escaping exception is reported as
        such, which is exactly the F-02 symptom.
        """
        script = (
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "sys.path.insert(0, sys.argv[2])\n"
            "out = {'import_ok': True}\n"
            "try:\n"
            "    import dsh_compat\n"
            "except BaseException as exc:\n"
            "    print(json.dumps({'import_ok': False,\n"
            "                      'error': type(exc).__name__ + ': ' + str(exc)}))\n"
            "    raise SystemExit(0)\n"
            "report = dsh_compat.check_dsh_preset_compat(root=sys.argv[3])\n"
            "out['verdict'] = report['verdict']\n"
            "out['reason'] = report['reason']\n"
            "out['issues'] = len(report['issues'])\n"
            "out['rows_checked'] = report['rows_checked']\n"
            "out['install'] = report['install']\n"
            "out['exit'] = dsh_compat.main(['--json', '--root', sys.argv[3]])\n"
            "print(json.dumps(out))\n")
        env = os.environ.copy()
        if without_host:
            env["PATH"] = ""
            env.pop("DSH_INSTALL_DIR", None)
            env.pop("DSH_HARNESS_NODE_MODULES", None)
            isolated_home = root / "empty-home"
            isolated_home.mkdir(exist_ok=True)
            env["DSH_HOME"] = str(isolated_home)
        env["PYTHONPATH"] = os.pathsep.join([
            str(root / "skills" / "software-project-governance" / "infra"),
            str(root / "adapters" / "dsh"),
        ])
        result = subprocess.run(
            [sys.executable, "-c", script,
             str(root / "adapters" / "dsh"),
             str(root / "skills" / "software-project-governance" / "infra"),
             str(root)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, cwd=str(root))
        self.assertNotIn("Traceback", result.stderr,
                         f"the guard escaped with a traceback:\n{result.stderr}")
        payload = [line for line in result.stdout.splitlines()
                   if line.startswith("{")]
        self.assertTrue(payload, f"no report on stdout: {result.stdout!r}")
        return json.loads(payload[-1])

    # ── F-02: the guard classifies instead of aborting ─────────────────────
    def test_unreadable_contract_degrades_to_not_run(self):
        root = self._guard_repo(drop=True)
        outcome = self._run_guard(root)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "NOT_RUN", outcome)
        self.assertIn("ContractUnreadable", outcome["reason"])
        self.assertEqual(outcome["issues"], 0, outcome)
        self.assertEqual(outcome["exit"], 0, outcome)

    def test_truncated_contract_is_fail_not_not_run(self):
        root = self._guard_repo(contract_bytes=b'{"schema_version": 1, "host":')
        outcome = self._run_guard(root)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "FAIL", outcome)
        self.assertIn("ContractMalformed", outcome["reason"])
        self.assertGreaterEqual(outcome["issues"], 1, outcome)

    def test_unknown_schema_version_is_fail_not_not_run(self):
        mutated = json.loads(json.dumps(self.original))
        mutated["schema_version"] = 99
        root = self._guard_repo(
            contract_bytes=json.dumps(mutated, ensure_ascii=False,
                                      indent=2).encode("utf-8"))
        outcome = self._run_guard(root)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "FAIL", outcome)
        self.assertIn("ContractSchemaUnknown", outcome["reason"])

    # ── F-03: a contract defect must not share the "no dsh" status ─────────
    def test_missing_apis_exports_is_a_fail_not_an_environment_gap(self):
        # `host.apis[...].exports` is not in the accessor's REQUIRED_PATHS, so a
        # contract that carries it malformed must be rejected before discovery
        # can return "no dsh installed". This is a local product defect.
        mutated = json.loads(json.dumps(self.original))
        mutated["host"]["apis"]["js-yaml"].pop("exports")
        root = self._guard_repo(
            contract_bytes=json.dumps(mutated, ensure_ascii=False,
                                      indent=2).encode("utf-8"))
        outcome = self._run_guard(root, without_host=True)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "FAIL", outcome)
        self.assertIn("host.apis[js-yaml].exports", outcome["reason"])
        self.assertIn("ContractMalformed", outcome["reason"])
        self.assertGreaterEqual(outcome["issues"], 1, outcome)
        self.assertNotIn("NOT_RUN", outcome["verdict"])

    def test_malformed_api_shapes_fail_without_host_or_compositions(self):
        package = "@deepseek-ai/cordis-plugin-loader"
        cases = [
            ("host.apis", None, "host.apis"),
            ("host.apis", [], "host.apis"),
            ("host.apis", {}, "host.apis"),
            ("host.apis", "packages", "host.apis"),
            ("entry", None, f"host.apis[{package}]"),
            ("entry", [], f"host.apis[{package}]"),
            ("entry", "loader", f"host.apis[{package}]"),
            ("exports", None, f"host.apis[{package}].exports"),
            ("exports", [], f"host.apis[{package}].exports"),
            ("exports", "evaluate", f"host.apis[{package}].exports"),
            ("exports", [None], f"host.apis[{package}].exports[0]"),
            ("exports", [23], f"host.apis[{package}].exports[0]"),
            ("exports", [""], f"host.apis[{package}].exports[0]"),
            ("exports", ["  "], f"host.apis[{package}].exports[0]"),
            ("exports", ["otherSymbol"], "host.apis"),
        ]
        for target, value, field in cases:
            with self.subTest(target=target, value=value):
                mutated = json.loads(json.dumps(self.original))
                if target == "host.apis":
                    mutated["host"]["apis"] = value
                elif target == "entry":
                    mutated["host"]["apis"][package] = value
                else:
                    mutated["host"]["apis"][package]["exports"] = value
                root = self._guard_repo(contract_bytes=json.dumps(mutated).encode("utf-8"))
                try:
                    # No discovered composition is another optional-tooling
                    # early return; local contract defects must precede it too.
                    shutil.rmtree(root / "agent-presets")
                    outcome = self._run_guard(root, without_host=True)
                    self.assertTrue(outcome["import_ok"], outcome)
                    self.assertEqual(outcome["verdict"], "FAIL", outcome)
                    self.assertIn("ContractMalformed", outcome["reason"])
                    self.assertIn(field, outcome["reason"])
                    self.assertGreaterEqual(outcome["issues"], 1, outcome)
                    self.assertEqual(outcome["rows_checked"], 0, outcome)
                    self.assertEqual(outcome["install"], {}, outcome)
                finally:
                    shutil.rmtree(root)

    def test_healthy_contract_without_host_is_not_run(self):
        root = self._guard_repo()
        composition = root / "agent-presets/governance/agent.cordis.yml"
        composition.write_text("- id: persona\n  name: '@deepseek-ai/dsh-persona'\n", encoding="utf-8")
        outcome = self._run_guard(root, without_host=True)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "NOT_RUN", outcome)
        self.assertIn("installed dsh not available", outcome["reason"])
        self.assertEqual(outcome["issues"], 0, outcome)
        self.assertEqual(outcome["rows_checked"], 0, outcome)
        self.assertEqual(outcome["exit"], 0, outcome)

    def test_a_healthy_contract_still_classifies_normally(self):
        # Control: the copy's pristine contract must not turn every run red.
        root = self._guard_repo()
        outcome = self._run_guard(root)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertIn(outcome["verdict"], ("PASS", "NOT_RUN"), outcome)

    def test_declared_symbols_still_resolve_for_outside_callers(self):
        # The lazy binding must not change the public surface: the names the
        # guard's own tests and the render layer use stay resolvable, and a typo
        # still raises instead of resolving to something else.
        import dsh_compat as guard

        self.assertEqual(guard.DSH_HOME_ENV, "DSH_HOME")
        self.assertEqual(guard.INSTALL_DIR_ENV, "DSH_INSTALL_DIR")
        self.assertEqual(guard.NODE_MODULES_ENV, "DSH_HARNESS_NODE_MODULES")
        self.assertEqual(guard.CLI_PACKAGE,
                         f"{guard.DSH_SCOPE}/{guard.DSH_PACKAGE}")
        self.assertEqual(guard.CHECK_SECTION_TITLE,
                         _contract()["own"]["checks"]["compat_section_title"])
        with self.assertRaises(AttributeError):
            guard.DSH_NOT_A_DECLARED_SYMBOL  # noqa: B018

    def test_render_composition_without_a_contract_reports_every_token(self):
        """`FX-JS-03` (design §5.6 / §2.6 J-3), as a direct-call regression.

        The P0 of the R0 review was precisely "this acceptance item had **no
        test**", so the fix ships with the regression that would have caught it.
        `renderComposition` is called **directly** — the shape
        `test_dsh_adapter.py::test_js_and_python_renderers_agree` uses — because
        the J-3 read point exists for exactly that caller (a scheduled-runner
        integration may render the template without going through `apply()`).

        The package under test carries only `lib/index.js` and `package.json`:
        no `adapters/dsh/host-contract.json`, so `contractBindings()` degrades to
        the empty view. The three assertions are the J-3 failure semantics:

          1. nothing throws (J-2: a throwing host row takes down the dsh boot);
          2. `leftovers` is exactly the template's token set — the renderer says
             "I substituted nothing", instead of returning an `undefined`
             leftover list that a caller reads as "nothing left to do";
          3. `apply()` also does not throw, and its warning is the actionable
             contract-unreadable remediation, not a degraded `TypeError`.
        """
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (JS consumer cannot be exercised)")
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "pkg"
            # The row imports `lib/dsh-native/`; copy the shipped tree so this
            # case fails on the contract, not on a missing module.
            shutil.copytree(_REPO_ROOT / "lib", pkg / "lib")
            (pkg / "package.json").write_text(
                '{"name":"fake","version":"9.9.9","type":"module",'
                '"main":"lib/index.js"}\n', encoding="utf-8")
            # Deliberately absent: pkg/adapters/dsh/host-contract.json
            self.assertFalse(
                (pkg / "adapters" / "dsh" / "host-contract.json").exists())

            script = (
                f"import {{ renderComposition, apply }} from "
                f"{json.dumps((pkg / 'lib' / 'index.js').as_uri())};"
                "import { readFileSync } from 'node:fs';"
                "const t = readFileSync(process.argv[1], 'utf8');"
                "const tokens = [...new Set(t.match(/__[A-Za-z0-9_]+__/g) || [])];"
                "let threw = false, rendered = null;"
                "try { rendered = renderComposition(t, process.argv[2]); }"
                "catch { threw = true; }"
                "const warns = [];"
                "let applyThrew = false;"
                "try { apply({ logger: { warn: (m) => warns.push(String(m)),"
                " info: () => {} } }); } catch { applyThrew = true; }"
                "process.stdout.write(JSON.stringify({"
                " threw, applyThrew, warns, tokens,"
                " leftovers: rendered && rendered.leftovers,"
                " text: rendered && rendered.text }));"
            )
            env = os.environ.copy()
            env["DSH_HOME"] = str(Path(td) / "home")
            result = subprocess.run(
                [node, "--input-type=module", "-e", script,
                 str(TEMPLATE), str(pkg).replace("\\", "/")],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env, cwd=str(_REPO_ROOT))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)

            # 1. neither entry point throws
            self.assertFalse(payload["threw"],
                             "renderComposition threw without a contract")
            self.assertFalse(payload["applyThrew"],
                             "apply() threw without a contract")
            # 2. leftovers is the template's token set — nothing was substituted
            self.assertEqual(payload["tokens"],
                             ["__GOVERNANCE_PERSONA_BODY__",
                              "__GOVERNANCE_SKILLS_ROOT__",
                              "__GOVERNANCE_SHIMS_ROOT__"])
            self.assertIsInstance(payload["leftovers"], list, payload)
            self.assertEqual(sorted(payload["leftovers"]),
                             sorted(payload["tokens"]),
                             "leftovers must cover every template token")
            self.assertNotEqual(payload["leftovers"], [])
            for token in payload["tokens"]:
                self.assertIn(token, payload["text"],
                              "an unreadable contract must substitute nothing")
            # 3. the warning is the actionable remediation, not a TypeError
            self.assertEqual(len(payload["warns"]), 1, payload["warns"])
            self.assertIn("contract unreadable", payload["warns"][0])
            self.assertIn("--sync", payload["warns"][0])
            self.assertNotIn("TypeError", payload["warns"][0])
            # 4. R1 P3: no contract means no render either. The row warns and
            # writes NOTHING — pinned here because the reviewer's probe was the
            # only evidence before (DEC-366 ②).
            self.assertFalse(
                (Path(td) / "home" / ".agent-presets").exists(),
                "a contract-less row must not render a preset directory")
        self.assertEqual(_sha256(self.contract_path.read_bytes()),
                         self.original_sha,
                         "the shipped contract changed during this case")


class TestFixtureEmitter(unittest.TestCase):
    """§5.4/§7.3: the emitter is deterministic and self-describing."""

    def test_fixture_ids_are_unique_and_str_keys(self):
        ids = dsh_fixtures.emitted_fixture_ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("FX-NO-SCHEMA-01", ids)

    def test_emit_fixture_writes_the_documented_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = dsh_fixtures.emit_fixture("FX-NO-SCHEMA-01", Path(tmp))
            self.assertEqual(written.name, "FX-NO-SCHEMA-01.cordis.yml")
            self.assertTrue(written.is_file())

    def test_emit_fixture_is_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as first, \
                tempfile.TemporaryDirectory() as second:
            one = dsh_fixtures.emit_fixture("FX-NO-SCHEMA-01", Path(first))
            two = dsh_fixtures.emit_fixture("FX-NO-SCHEMA-01", Path(second))
            self.assertEqual(_sha256(one.read_bytes()),
                             _sha256(two.read_bytes()))

    def test_every_emitted_fixture_is_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as first, \
                tempfile.TemporaryDirectory() as second:
            for fixture in dsh_fixtures.emitted_fixture_ids():
                one = _sha256(
                    dsh_fixtures.emit_fixture(fixture, Path(first)).read_bytes())
                two = _sha256(
                    dsh_fixtures.emit_fixture(fixture, Path(second)).read_bytes())
                self.assertEqual(one, two, fixture)

    def test_cli_emit_fixture_matches_the_in_process_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(_HERE / "dsh_fixtures.py"),
                 "--emit-fixture", "FX-NO-SCHEMA-01", "--out", tmp],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            written = Path(tmp) / "FX-NO-SCHEMA-01.cordis.yml"
            self.assertTrue(written.is_file())
            with tempfile.TemporaryDirectory() as other:
                in_process = dsh_fixtures.emit_fixture(
                    "FX-NO-SCHEMA-01", Path(other))
                self.assertEqual(_sha256(written.read_bytes()),
                                 _sha256(in_process.read_bytes()))

    def test_cli_refuses_an_unknown_fixture_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(_HERE / "dsh_fixtures.py"),
                 "--emit-fixture", "FX-NOT-A-FIXTURE", "--out", tmp],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("FX-NOT-A-FIXTURE", completed.stderr
                          + completed.stdout)

    def test_cli_reports_the_owning_slice_for_a_deferred_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(_HERE / "dsh_fixtures.py"),
                 "--emit-fixture", "FX-REHEARSE-05", "--out", tmp],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("V8", completed.stdout + completed.stderr)

    def test_deferred_fixtures_declare_an_owning_slice(self):
        deferred = dsh_fixtures.deferred_fixture_ids()
        self.assertTrue(deferred)
        for fixture in deferred:
            reason = dsh_fixtures.deferred_reason(fixture)
            self.assertRegex(reason, r"V\d+")

    def test_emitting_creates_no_repository_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fixture in dsh_fixtures.emitted_fixture_ids():
                dsh_fixtures.emit_fixture(fixture, Path(tmp))
        fixtures_dir = _REPO_ROOT / "adapters" / "dsh" / "fixtures"
        self.assertFalse(
            list(fixtures_dir.glob("FX-*")) if fixtures_dir.exists() else [])

    def test_fixtures_are_generated_not_committed(self):
        tracked = subprocess.run(
            ["git", "ls-files", "adapters/dsh"], cwd=str(_REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace").stdout.split()
        self.assertFalse([item for item in tracked
                          if Path(item).name.startswith("FX-")], tracked)

    def test_no_schema_fixture_uses_a_zero_schema_module_of_its_own(self):
        # AUDIT-153 D-44 measured `@deepseek-ai/dsh-tool-ask-user` as a row
        # whose module exported no `Config`. dsh 0.2.1 gave that package a
        # `Config`, so anchoring the fixture to a host package made it test the
        # opposite premise (a schema that accepts the bogus key) without saying
        # so. The fixture now ships a local module that provably exports no
        # `Config`; the premise is a property of this repository, not of the
        # installed host version.
        with tempfile.TemporaryDirectory() as tmp:
            path = dsh_fixtures.emit_fixture("FX-NO-SCHEMA-01", Path(tmp))
            text = path.read_text(encoding="utf-8")
            companion = dsh_fixtures.NO_SCHEMA_FIXTURE_SOURCE
            module = path.parent / dsh_fixtures.NO_SCHEMA_MODULE[2:]
            emitted = module.read_text(encoding="utf-8")
        self.assertIn(dsh_fixtures.NO_SCHEMA_MODULE, text)
        self.assertNotIn("@deepseek-ai/", text)
        self.assertIn("totallyBogusKeyThatMustBeRejected", text)
        self.assertEqual(emitted, companion)
        self.assertNotIn("Config", emitted)
        self.assertIn("export function apply", emitted)


class TestFixturePayloads(unittest.TestCase):
    """§5.6: every emitted fixture must really carry its named mutation."""

    def _payload(self, fixture_id, encoding=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = dsh_fixtures.emit_fixture(fixture_id, Path(tmp))
            raw = path.read_bytes()
        return raw.decode(encoding) if encoding else raw

    def _text(self, fixture_id):
        return self._payload(fixture_id, "utf-8")

    def test_group_name_fixture_carries_the_typo(self):
        self.assertIn("name: cordis:gruop", self._text("FX-GROUP-01"))
        self.assertNotIn("name: cordis:group", self._text("FX-GROUP-01"))

    def test_group_without_children_declares_an_empty_child_sequence(self):
        text = self._text("FX-GROUP-02")
        self.assertIn("group: true", text)
        self.assertIn("config: []", text)

    def test_group_with_children_declares_a_child_row(self):
        text = self._text("FX-GROUP-03")
        self.assertIn("- id: tool-todo", text)

    def test_cr_fixture_carries_exactly_one_isolated_cr(self):
        raw = self._payload("FX-CR-01")
        self.assertEqual(raw.count(b"\r"), 1)
        self.assertEqual(raw.count(b"\r\n"), 0)

    def test_token_fixtures_carry_the_misspellings(self):
        all_caps = self._text("FX-TOKEN-01")
        self.assertIn("__GOVERNANCE_SKILLS_ROOTS__", all_caps)
        self.assertNotIn("__GOVERNANCE_SKILLS_ROOT__", all_caps)
        mixed = self._text("FX-TOKEN-02")
        self.assertIn("__Governance_Repo_Root__", mixed)
        self.assertNotIn("__GOVERNANCE_REPO_ROOT__", mixed)

    def test_custom_skill_dirs_fixture_puts_items_at_the_key_indent(self):
        text = self._text("FX-CSD-01")
        self.assertIn("    customSkillDirs:\n"
                      "    - '__GOVERNANCE_SKILLS_ROOT__'\n", text)

    def test_relative_skill_dir_fixture_has_a_literal_relative_entry(self):
        text = self._text("FX-CSD-02")
        self.assertIn("      - 'adapters/dsh/skill-shims'\n", text)

    def test_utf8_fixture_is_not_valid_utf8(self):
        raw = self._payload("FX-UTF8-01")
        self.assertIn(b"\xff", raw)
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")

    def test_patch_fixture_adds_an_id_targeted_update_row(self):
        text = self._text("FX-PATCH-01")
        self.assertIn("- id: persona", text)
        self.assertIn("- insert:", text)

    def test_unknown_fixture_id_raises_actionable_errors(self):
        with self.assertRaises(ValueError) as caught:
            dsh_fixtures.fixture_bytes("FX-NOT-A-FIXTURE")
        self.assertIn("FX-NOT-A-FIXTURE", str(caught.exception))
        with self.assertRaises(KeyError):
            dsh_fixtures.deferred_reason("FX-NOT-A-FIXTURE")

    def test_deferred_fixture_reports_its_owning_slice(self):
        with self.assertRaises(ValueError) as caught:
            dsh_fixtures.fixture_bytes("FX-REHEARSE-05")
        self.assertIn("V8", str(caught.exception))

    def test_cli_list_and_usage_paths(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(dsh_fixtures.main(["--list"]), 0)
        listing = buffer.getvalue()
        self.assertIn("FX-NO-SCHEMA-01", listing)
        self.assertIn("FX-REHEARSE-05", listing)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(dsh_fixtures.main([]), 2)


class TestManifestDeclaration(unittest.TestCase):
    """§2.9.1/K-10: the contract is declared as a canonical product artifact."""

    def setUp(self):
        self.manifest = json.loads(_read(
            _REPO_ROOT / "skills" / "software-project-governance" / "core"
            / "manifest.json"))

    def test_contract_is_a_canonical_product_artifact(self):
        entries = {entry["id"]: entry
                   for entry in self.manifest["canonical_product_artifacts"]
                   ["entries"]}
        self.assertIn("dsh-host-contract", entries)
        entry = entries["dsh-host-contract"]
        self.assertEqual(entry["path"], "adapters/dsh/host-contract.json")
        self.assertEqual(entry["type"], "file")
        self.assertIs(entry["required"], True)
        self.assertEqual(entry["artifact_role"], "host-dependency-contract")
        self.assertTrue(entry["validation_commands"])
        self.assertTrue(any("check-manifest-consistency" in command
                            for command in entry["validation_commands"]))

    def test_contract_has_an_explicit_product_file_entry(self):
        product_files = {item["path"] for item in self.manifest["product"]
                         ["entries"] if item["type"] == "file"}
        self.assertIn("adapters/dsh/host-contract.json", product_files)

    def test_cleanup_scope_is_unchanged_and_covers_the_contract(self):
        # C-8 zero change: `adapters` is already in the directory set, and
        # `cleanup.py` expands dir entries recursively (§2.9.2).
        # FEAT-101: the platform-set reduction dropped one plugin dir, so
        # the scope carries 10 directories (the C-8 era count was 11).
        directories = self.manifest["cleanup_scope"]["directories"]
        self.assertIn("adapters", directories)
        self.assertEqual(len(directories), 10)
        cleanup_text = _read(_REPO_ROOT / "skills"
                             / "software-project-governance" / "infra"
                             / "cleanup.py")
        self.assertIn('"adapters"', cleanup_text)

    def test_adapters_is_a_product_dir_entry_covering_the_contract(self):
        entries = self.manifest["product"]["entries"]
        self.assertIn({"path": "adapters/", "type": "dir"}, entries)


if __name__ == "__main__":
    unittest.main()
