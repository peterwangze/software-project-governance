"""Self-check unit tests for the V1 DSH host-dependency contract data layer.

FEAT-029 (0.81.0 slice V1) lands three new artifacts and one declaration:

  * ``adapters/dsh/host-contract.json`` — the single machine-readable source of
    the dsh host facts this plugin consumes (design
    ``docs/requirements/dsh-compat-design-0.81.0.md`` §2.4);
  * ``infra/dsh_contract.py`` — the stdlib-only accessor (§2.5.1: four APIs,
    three exception classes, no registry import — ADR-018 §8);
  * ``infra/tests/dsh_fixtures.py`` — the deterministic fixture emitter (§5.4);
  * ``core/manifest.json`` — the canonical-product-artifact declaration
    (§2.9.1).

This module is the **unit-level** form of the Check 28w judgments that land in
V8 (§2.8). Covered here, at unit scope:

  - **K-1** — the contract parses, ``schema_version`` is known, every field of
    the §2.4 field table exists (including the "present but may be empty"
    recorded sub-block, R0 F-5), and the three failure classes of §2.5.1
    (``ContractUnreadable`` / ``ContractMalformed`` / ``ContractSchemaUnknown``)
    classify unreadable / malformed / unknown-schema inputs. Every message
    names the contract path, the exception class and the offending field.
  - **K-3** — the composition template's rows and ``host.rows[]`` agree **in
    both directions over the full platform-independent set of 29 rows**: the
    template's row ids, package names, config keys, ``disabled:`` forms and
    group membership are re-derived from the template text here (independently
    of the JSON), so a row added on either side turns this red. The 23 enabled
    rows per platform (29 − 3 groups − 2 ``disabled: true`` − 1 short-circuited
    platform row) are recomputed too.
  - **K-4** — the template's ``__…__`` token set equals ``own.render.tokens``
    and a rendered template leaves no ``__[A-Za-z0-9_]+__`` behind.
  - **K-9** — ``elimination.dispositions[]`` covers every ``D-nn`` of
    AUDIT-153 exactly once, ``coverage.entries[].audit_ids`` covers the
    necessary-dependency set, no ``subject`` repeats, and every declared
    subject resolves inside the contract (the K-8 ``guard`` /
    ``negative_fixtures`` resolution rules are checked at unit level too).

Two invariants of this slice are asserted directly, because they are the
failure mode the design calls out:

  * **R0 F-5 — no hand-copied real-plane facts.** The recorded sub-block of
    every ``host.rows[]`` entry MUST still be empty and flagged
    ``source: recorded`` / ``recorded: false``. A hand-transcribed schema key
    set would turn this red; only ``dsh-doctor --record-evidence`` (V8) may
    fill it.
  * **R0 F-6 — the probe side stays fail-closed.** ``host.env.probe_side``
    declares ``require_explicit`` / ``no_fallback`` and the write side is a
    separate block; the two are never conflated into a "three implementations
    agree" claim.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_dsh_contract.py" -v
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

TEMPLATE = _REPO_ROOT / "agent-presets" / "governance" / "agent.cordis.yml.template"
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

# Design §0.2 E-10②: 16 top-level + 13 nested = the platform-independent set.
_EXPECTED_ROWS_TOP_LEVEL = 16
_EXPECTED_ROWS_NESTED = 13
_EXPECTED_ROW_TOTAL = _EXPECTED_ROWS_TOP_LEVEL + _EXPECTED_ROWS_NESTED
# Design §0.2 E-10②: 29 − 3 groups − 2 `disabled: true` − 1 short-circuited
# platform row = the 23 rows AUDIT-153 measured as `rows_enabled`.
_EXPECTED_ENABLED_PER_PLATFORM = 23
# Design §0.2 E-10③: 14 non-group rows with a config mapping + 3 groups.
_EXPECTED_CONFIG_DECLARED = 17

_AUDIT_ID_RE = re.compile(r"^D-\d{2,3}$")
_TEMPLATE_TOKEN_RE = re.compile(r"__[A-Za-z0-9_]+__")
_ROW_ID_RE = re.compile(r"^(\s*)- id: (\S+)\s*$")
_ROW_KEY_RE = re.compile(r"^(\s*)(name|disabled|config|group|isolate):\s*(.*)$")
_CONFIG_KEY_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

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
    return _read(TEMPLATE)


def _parse_template_rows(text=None):
    """Re-derive the row table from the template text, independently of JSON.

    Strict by construction: a row is a ``- id: <name>`` entry at indent 0 or 4
    (the two row depths of this composition) and its row keys must sit at
    ``row_indent + 2``. Anything that looks like a row but does not match this
    shape raises, so a template mutation cannot be silently absorbed.
    """
    text = _template_text() if text is None else text
    lines = text.split("\n")
    rows = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = _ROW_ID_RE.match(line)
        if not match:
            index += 1
            continue
        indent = len(match.group(1))
        if indent not in (0, 4):
            raise AssertionError(
                f"{TEMPLATE.name}:{index + 1}: row at unexpected indent {indent}")
        row = {
            "row_id": match.group(2),
            "indent": indent,
            "line": index + 1,
            "package": None,
            "disabled_expr": None,
            "config_declared": False,
            "config_keys": [],
            "group": None,
            "is_group": False,
            "children": [],
        }
        index += 1
        while index < len(lines):
            probe = lines[index]
            if not probe.strip():
                index += 1
                continue
            if _ROW_ID_RE.match(probe) or _ROW_ID_RE.match(probe.lstrip()):
                break
            key_match = _ROW_KEY_RE.match(probe)
            if not key_match or len(key_match.group(1)) != indent + 2:
                if len(probe) - len(probe.lstrip()) <= indent:
                    break
                index += 1
                continue
            key = key_match.group(2)
            value = key_match.group(3).strip()
            if key == "name":
                row["package"] = value.strip("'\"") if value else None
            elif key == "disabled":
                row["disabled_expr"] = value or None
            elif key == "group":
                row["is_group"] = value == "true"
            elif key == "config":
                row["config_declared"] = True
                index += 1
                while index < len(lines):
                    child = lines[index]
                    if not child.strip():
                        index += 1
                        continue
                    child_indent = len(child) - len(child.lstrip())
                    if child_indent <= indent + 2:
                        break
                    nested_row = _ROW_ID_RE.match(child)
                    if nested_row:
                        break
                    config_key = _CONFIG_KEY_RE.match(child)
                    if config_key and child_indent == indent + 4:
                        row["config_keys"].append(config_key.group(2))
                    index += 1
                continue
            index += 1
        rows.append(row)
    return rows


def _link_template_rows(rows):
    """Attach nested rows to their group and derive the effective `group`."""
    stack = None
    for row in rows:
        if row["indent"] == 0:
            stack = row if row["is_group"] else None
            row["group"] = None
        else:
            if stack is None:
                raise AssertionError(
                    f"row {row['row_id']} is nested but no top-level group "
                    f"precedes it")
            row["group"] = stack["row_id"]
            stack["children"].append(row["row_id"])
    return rows


def _enabled_on(row):
    """Derive the per-row enablement from the template's own disabled form."""
    if row["is_group"]:
        return None
    expr = row["disabled_expr"]
    if expr is None:
        return "any"
    if expr == "true":
        return "never"
    if expr == "!!js process.platform === 'win32'":
        return "posix"
    if expr == "!!js process.platform !== 'win32'":
        return "win32"
    raise AssertionError(f"row {row['row_id']}: unknown disabled form {expr!r}")


def _platform_conditional(row):
    return (row["disabled_expr"] or "").startswith("!!js process.platform")


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
    "agent-presets/governance/agent.cordis.yml.template",
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
    packages = ({row["package"] for row in host["rows"]}
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


def _correct(a, b):
    """Like :func:`unittest.TestCase.assertEqual`, but returning the mismatch."""
    return "" if a == b else f"{a!r} != {b!r}"


def template_row_mismatches(contract=None, template_text=None):
    """K-3's comparison as a value: how the template's rows disagree with the
    contract's.

    Extracted so the idempotent tests and the mutation matrix share one
    implementation — the mutation test must observe *this* judgment changing
    when `host.rows[]` changes, otherwise it proves nothing about the reader.
    Order-independent by construction: the caller gets one message per
    disagreement, and the empty list means "the two sides agree".
    """
    contract = _contract() if contract is None else contract
    declared = contract["host"]["rows"]
    template_text = _template_text() if template_text is None else template_text

    # Both sides are values: the template rows are re-derived from the text
    # (independently of the JSON) and the contract rows come from the accessor,
    # so a mutation on either side shows up here and only here.
    rows = _link_template_rows(_parse_template_rows(template_text))
    by_id = {row["row_id"]: row for row in declared}
    template_ids = [row["row_id"] for row in rows]
    mismatch = []
    if len(template_ids) != len(set(template_ids)):
        mismatch.append(f"template row ids are not unique: {template_ids}")
    for missing in sorted(set(by_id) - set(template_ids)):
        mismatch.append(f"contract row absent from template: {missing}")
    for extra in sorted(set(template_ids) - set(by_id)):
        mismatch.append(f"template row not in contract: {extra}")
    for row in rows:
        declared_row = by_id.get(row["row_id"])
        if declared_row is None:
            continue
        for key, value in (
                ("package", row["package"]),
                ("disabled_expr", row["disabled_expr"]),
                ("platform_conditional", _platform_conditional(row)),
                ("enabled_on", _enabled_on(row)),
                ("config_keys", row["config_keys"]),
                ("config_declared", row["config_declared"]),
                ("group", row["group"]),
        ):
            message = _correct(declared_row[key], value)
            if message:
                mismatch.append(f"{row['row_id']}.{key}: {message}")
    return mismatch


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
        self.assertEqual(contract["schema_version"], 1)
        for namespace in ("evidence", "host", "own", "coverage", "elimination"):
            self.assertIn(namespace, contract)
            self.assertIsInstance(contract[namespace], dict, namespace)

    def test_supported_schema_versions_is_the_declared_closed_set(self):
        self.assertEqual(dsh_contract.SUPPORTED_SCHEMA_VERSIONS, (1,))
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

    def test_row_shape_violation_is_malformed_and_names_the_row(self):
        payload = json.loads(json.dumps(_contract()))
        payload["host"]["rows"][0].pop("config_declared")
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        message = str(caught.exception)
        self.assertIn("host.rows[persona].config_declared", message)

    def test_a_non_false_recorded_flag_is_malformed(self):
        # R0 F-2: `recorded.source` was value-checked while `recorded.recorded`
        # was only key-checked. V1 ships every row unrecorded, so the flag must
        # be *exactly* the JSON literal `false` on all 29 rows (design §2.4/
        # §2.7 + R0 F-5) — `null`, `0` and the string "false" are malformed,
        # not merely "not yet recorded".
        for mutated in (None, "false", 0, "False", True):
            payload = json.loads(json.dumps(_contract()))
            payload["host"]["rows"][0]["recorded"]["recorded"] = mutated
            with self.assertRaises(dsh_contract.ContractMalformed) as caught:
                dsh_contract.load_contract(raw=json.dumps(payload))
            self.assertIn("host.rows[persona].recorded.recorded",
                          str(caught.exception), repr(mutated))
        # The key check this replaces is not lost: an absent flag is not
        # `false` either.
        payload = json.loads(json.dumps(_contract()))
        del payload["host"]["rows"][0]["recorded"]["recorded"]
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        self.assertIn("host.rows[persona].recorded.recorded",
                      str(caught.exception))
        # Positive control: the shipped `source: "recorded"` + `false` loads.
        payload = json.loads(json.dumps(_contract()))
        loaded = dsh_contract.load_contract(raw=json.dumps(payload))
        self.assertIs(loaded["host"]["rows"][0]["recorded"]["recorded"], False)

    def test_duplicate_row_id_is_malformed(self):
        payload = json.loads(json.dumps(_contract()))
        payload["host"]["rows"].append(dict(payload["host"]["rows"][0]))
        with self.assertRaises(dsh_contract.ContractMalformed) as caught:
            dsh_contract.load_contract(raw=json.dumps(payload))
        self.assertIn("persona", str(caught.exception))

    def test_get_resolves_documented_paths(self):
        contract = _contract()
        self.assertEqual(dsh_contract.get("host.install.scope", contract),
                         "@deepseek-ai")
        self.assertEqual(
            dsh_contract.get("host.rows[persona].package", contract),
            "@deepseek-ai/dsh-persona")
        self.assertEqual(
            dsh_contract.get("host.rows[persona].config_keys", contract),
            ["prefix"])
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
        self.assertIn("{ baseUrl: pathToFileURL(file.path).href, process, console }",
                      guard_text)
        # The declared field names are the template's own keys.
        for field in ("id_field", "name_field", "config_field", "group_field",
                      "disabled_field"):
            self.assertIn(f"{row_contract[field]}:", _template_text())

    def test_host_rows_full_set_and_arithmetic(self):
        rows = self.contract["host"]["rows"]
        self.assertEqual(len(rows), _EXPECTED_ROW_TOTAL)
        self.assertEqual(sum(1 for row in rows if row["group"] is None),
                         _EXPECTED_ROWS_TOP_LEVEL)
        self.assertEqual(sum(1 for row in rows if row["group"] is not None),
                         _EXPECTED_ROWS_NESTED)
        groups = [row for row in rows
                  if row["package"] == self.contract["host"]["row_contract"]
                  ["builtin_group_name"]]
        self.assertEqual(len(groups), 3)
        self.assertEqual(sum(1 for row in rows if row["disabled_expr"] == "true"), 2)
        platform_rows = [row for row in rows if row["platform_conditional"]]
        self.assertEqual(len(platform_rows), 2)
        self.assertTrue(all(row["disabled_expr"].startswith("!!js ")
                            for row in platform_rows))
        self.assertEqual(
            sorted(row["enabled_on"] for row in platform_rows),
            ["posix", "win32"])
        self.assertEqual(sum(1 for row in rows if row["enabled_on"] == "any"),
                         _EXPECTED_ROW_TOTAL - 3 - 2 - 2)
        enabled = sum(1 for row in rows
                      if row["enabled_on"] in ("any", "win32", "posix")) - 1
        self.assertEqual(enabled, _EXPECTED_ENABLED_PER_PLATFORM)
        self.assertEqual(sum(1 for row in rows if row["config_declared"]),
                         _EXPECTED_CONFIG_DECLARED)

    def test_host_rows_recorded_subblock_is_empty_and_flagged(self):
        for row in self.contract["host"]["rows"]:
            recorded = row["recorded"]
            self.assertEqual(recorded["source"], "recorded", row["row_id"])
            self.assertIs(recorded["recorded"], False, row["row_id"])
            self.assertIsNone(recorded["schema_export"], row["row_id"])
            self.assertIsNone(recorded["probe_result"], row["row_id"])
            self.assertEqual(recorded["required_keys"], [], row["row_id"])
            self.assertEqual(recorded["accepted_keys"], [], row["row_id"])

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
        for package, entry in apis.items():
            self.assertTrue(entry["role"], package)
            self.assertTrue(entry["exports"], package)
        self.assertEqual(len(apis), 4)
        # Every declared symbol must be reachable from a role the renderer
        # resolves (`load` → YAML, `entryListSchema` → dialect,
        # `evaluate`/`isJsExpr` → loader, `resolveConfig` → cordis), otherwise
        # `_render_probe_script()` raises instead of running a partial probe.
        symbols = {symbol for entry in apis.values() for symbol in entry["exports"]}
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
        for key in ("rows_field_semantics", "rows_recorded_subblock"):
            self.assertTrue(notes[key], key)

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
        self.assertTrue((_REPO_ROOT / preset["template"]).is_file())
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
                         ["exactly-one-insert-row", "no-!!js", "no-id-update",
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
        self.assertIn(checks["smoke_section_title"],
                      _read(_REPO_ROOT / "skills" / "software-project-governance"
                            / "infra" / "verify_workflow.py"))
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


class TestTemplateContractAgreement(unittest.TestCase):
    """K-3: template rows ↔ `host.rows[]`, both directions, full set."""

    def setUp(self):
        self.contract = _contract()
        self.rows = _link_template_rows(_parse_template_rows())
        self.declared = self.contract["host"]["rows"]
        self.by_id = {row["row_id"]: row for row in self.declared}

    def test_template_row_ids_are_unique_and_total_29(self):
        ids = [row["row_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertEqual(len(ids), _EXPECTED_ROW_TOTAL)

    def test_template_row_set_equals_the_contract_row_set(self):
        template_ids = {row["row_id"] for row in self.rows}
        contract_ids = set(self.by_id)
        self.assertEqual(
            template_ids - contract_ids, set(),
            "template row not in contract")
        self.assertEqual(
            contract_ids - template_ids, set(),
            "contract row absent from template")

    def test_every_row_agrees_field_by_field(self):
        for row in self.rows:
            declared = self.by_id[row["row_id"]]
            self.assertEqual(declared["package"], row["package"], row["row_id"])
            self.assertEqual(declared["disabled_expr"], row["disabled_expr"],
                             row["row_id"])
            self.assertEqual(declared["platform_conditional"],
                             _platform_conditional(row), row["row_id"])
            self.assertEqual(declared["enabled_on"], _enabled_on(row),
                             row["row_id"])
            self.assertEqual(declared["config_keys"], row["config_keys"],
                             row["row_id"])
            self.assertEqual(declared["config_declared"],
                             row["config_declared"], row["row_id"])
            self.assertEqual(declared["group"], row["group"], row["row_id"])

    def test_group_children_are_attached_to_their_group(self):
        groups = [row for row in self.rows if row["is_group"]]
        self.assertEqual([row["row_id"] for row in groups],
                         ["planning", "compaction", "delegation"])
        counts = {row["row_id"]: len(row["children"]) for row in groups}
        self.assertEqual(sum(counts.values()), _EXPECTED_ROWS_NESTED)
        self.assertEqual(counts, {"planning": 1, "compaction": 3,
                                  "delegation": 9})

    def test_platform_and_disabled_rows_are_both_visible_in_the_contract(self):
        # A one-sided addition is exactly what K-3 has to catch: the platform
        # conditional rows and the `disabled: true` rows must be declared.
        declared_platform = {row["row_id"] for row in self.declared
                             if row["platform_conditional"]}
        declared_disabled = {row["row_id"] for row in self.declared
                             if row["disabled_expr"] == "true"}
        self.assertEqual(declared_platform, {"tool-bash", "tool-pwsh"})
        self.assertEqual(declared_disabled,
                         {"tool-subagent-codex", "tool-subagent-claude-code"})
        self.assertEqual(
            {row["row_id"] for row in self.rows if _platform_conditional(row)},
            declared_platform)


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

    def test_design_example_subject_path_resolves(self):
        # Design §2.4/§4.1 use `host.rows[persona].config_keys` as the canonical
        # subject spelling: `[<row id>]` indexes the row list by `row_id`.
        self.assertEqual(
            dsh_contract.get("host.rows[persona].config_keys"), ["prefix"])
        self.assertEqual(
            dsh_contract.get("host.rows[plan-mode].config_keys"), ["section"])


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
                'e = "agent-presets/governance/agent.cordis.yml.template"\n',
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
                "// agent-presets/governance/agent.cordis.yml.template\n",
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
                                    / "agent.cordis.yml.template"),
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
                      / "agent.cordis.yml.template"),
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
            "print(json.dumps({'rendered': launch.render_composition(),\n"
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
            "print(len(launch.render_composition()))\n"))
        self.assertGreater(int(out.strip()), 0, out)

    def test_mutation_own_preset_id_moves_the_js_sync_destination(self):
        def mutate(contract):
            contract["own"]["preset"]["id"] = "governance-mutated"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            out = self._node(
                root,
                "import { apply } from "
                f"{json.dumps(self._lib_uri(root))};"
                "const warns = [];"
                "apply({ logger: { warn: (m) => warns.push(String(m)),"
                " info: () => {} } });"
                "process.stdout.write(JSON.stringify(warns));", env=env)
            self.assertEqual(json.loads(out), [])
            self.assertTrue(
                (Path(td) / ".agent-presets" / "governance-mutated"
                 / "agent.cordis.yml").is_file(),
                "the mutated preset id did not reach ensurePreset()")
            self.assertFalse(
                (Path(td) / ".agent-presets" / "governance").exists(),
                "the un-mutated preset id was still used")
        self._assert_copy_restored(root)

    def test_mutation_own_preset_version_marker_names_the_js_marker_file(self):
        def mutate(contract):
            contract["own"]["preset"]["version_marker"] = ".mutated-version"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            self._node(
                root,
                "import { apply } from "
                f"{json.dumps(self._lib_uri(root))};"
                "const warns = [];"
                "apply({ logger: { warn: (m) => warns.push(String(m)),"
                " info: () => {} } });"
                "process.stdout.write(JSON.stringify(warns));", env=env)
            preset = Path(td) / ".agent-presets" / "governance"
            self.assertTrue((preset / ".mutated-version").is_file(),
                            sorted(item.name for item in preset.iterdir()))
            self.assertFalse((preset / ".dsh-bundle-version").exists())
        self._assert_copy_restored(root)

    def test_mutation_own_skill_root_marker_names_the_launcher_marker_file(self):
        def mutate(contract):
            contract["own"]["preset"]["skill_root_marker"] = "mutated-root.txt"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as tmp:
            out = self._pyprobe(root, (
                "import json, launch\n"
                f"ok = launch.write_rendered_preset(__import__('pathlib')"
                f".Path({str(Path(tmp) / 'staging')!r}))\n"
                "import pathlib\n"
                "names = sorted(p.name for p in "
                f"pathlib.Path({str(Path(tmp) / 'staging')!r}).iterdir())\n"
                "print(json.dumps({'ok': ok, 'names': names}))\n"))
        payload = json.loads(out)
        self.assertTrue(payload["ok"], payload)
        self.assertIn("mutated-root.txt", payload["names"], payload)
        self.assertNotIn("skill-root.txt", payload["names"], payload)
        self._assert_copy_restored(root)

    def test_mutation_host_env_home_var_is_read_by_the_js_row(self):
        # F-10: `host.env.home_var` has a binding in all three consumers; the JS
        # row is the one whose observable output changes when the *variable name*
        # changes (the home it resolves is named by that declaration).
        def mutate(contract):
            contract["host"]["env"]["home_var"] = "DSH_HOME_MUTATED"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            # The declared (mutated) variable is set; the original one is also
            # set to a DIFFERENT directory, so reading the wrong name is visible.
            other = Path(td) / "wrong-home"
            target = Path(td) / "right-home"
            env = os.environ.copy()
            env["DSH_HOME"] = str(other)
            env["DSH_HOME_MUTATED"] = str(target)
            out = self._node(
                root,
                "import { apply } from "
                f"{json.dumps(self._lib_uri(root))};"
                "const warns = [];"
                "apply({ logger: { warn: (m) => warns.push(String(m)),"
                " info: () => {} } });"
                "process.stdout.write(JSON.stringify(warns));", env=env)
            self.assertEqual(json.loads(out), [])
            self.assertTrue(
                (target / ".agent-presets" / "governance"
                 / "agent.cordis.yml").is_file(),
                "the mutated home variable was not the one read")
            self.assertFalse(other.exists(),
                             "the row read the un-mutated home variable")
        self._assert_copy_restored(root)

    def test_mutation_host_home_user_preset_dir_is_read_by_the_js_row(self):
        # F-10: `host.home.user_preset_dir` names the preset root segment; a
        # consumer that kept `.agent-presets` hard-coded would ignore it.
        def mutate(contract):
            contract["host"]["home"]["user_preset_dir"] = ".mutated-presets"
        root = self._mutated_repo(mutate)
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            out = self._node(
                root,
                "import { apply } from "
                f"{json.dumps(self._lib_uri(root))};"
                "const warns = [];"
                "apply({ logger: { warn: (m) => warns.push(String(m)),"
                " info: () => {} } });"
                "process.stdout.write(JSON.stringify(warns));", env=env)
            self.assertEqual(json.loads(out), [])
            self.assertTrue(
                (Path(td) / ".mutated-presets" / "governance"
                 / "agent.cordis.yml").is_file(),
                "the mutated user preset dir was not used")
            self.assertFalse((Path(td) / ".agent-presets").exists(),
                             "the un-mutated preset dir was still used")
        self._assert_copy_restored(root)

    def test_mutation_host_rows_flips_the_template_agreement_judgment(self):
        # The consumer of `host.rows[]` at V2 is the template cross-check
        # (design §2.8 K-3; the rule engine reads the composition, never the
        # contract). So the observable consumer output here IS that judgment:
        # with the real contract it is empty, and a one-row mutation must make
        # it non-empty.
        self.assertEqual(template_row_mismatches(), [])
        # The affected row is chosen from the declared set, not hard-coded.
        target = next(row for row in self.original["host"]["rows"]
                      if row["config_keys"] and row["config_declared"])

        def mutate(contract):
            for row in contract["host"]["rows"]:
                if row["row_id"] == target["row_id"]:
                    row["config_declared"] = False

        root = self._mutated_repo(mutate)
        out = self._pyprobe(root, (
            "import json, dsh_contract\n"
            "document = dsh_contract.load_contract()\n"
            "print(json.dumps([r['config_declared'] for r in "
            "document['host']['rows'] if r['row_id'] == "
            f"{target['row_id']!r}]))\n"))
        self.assertIn(False, json.loads(out),
                      "the copy's mutated row was not read")
        self._assert_copy_restored(root)
        # The judgment itself is contract-driven: feeding it the mutated
        # document (as the copy's accessor returns it) reports the mismatch.
        mutated = json.loads((root / dsh_contract.CONTRACT_REL).read_text("utf-8"))
        mismatches = template_row_mismatches(mutated)
        self.assertTrue(mismatches, target["row_id"])
        self.assertTrue(any(target["row_id"] in item for item in mismatches),
                        mismatches)

    def test_mutation_host_rows_removal_is_a_one_sided_row(self):
        dropped = self.original["host"]["rows"][0]["row_id"]

        def mutate(contract):
            contract["host"]["rows"] = [
                row for row in contract["host"]["rows"]
                if row["row_id"] != dropped]
        root = self._mutated_repo(mutate)
        mutated = json.loads((root / dsh_contract.CONTRACT_REL).read_text("utf-8"))
        mismatches = template_row_mismatches(mutated)
        self.assertIn(f"template row not in contract: {dropped}", mismatches)
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
        for module in ("dsh_contract.py", "dsh_compat.py"):
            shutil.copyfile(_INFRA_DIR / module, root / infra_rel / module)
        target = root / dsh_contract.CONTRACT_REL
        if drop:
            target.unlink()
        elif contract_bytes is not None:
            target.write_bytes(contract_bytes)
        return root

    def _run_guard(self, root):
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
            "out['reason'] = report['reason'][:200]\n"
            "out['issues'] = len(report['issues'])\n"
            "out['exit'] = dsh_compat.main(['--json', '--root', sys.argv[3]])\n"
            "print(json.dumps(out))\n")
        env = os.environ.copy()
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
        # contract that carries it malformed passes every earlier check and only
        # fails when the probe script is rendered. That failure is a contract
        # defect: FAIL, never the NOT_RUN that "no dsh installed" produces.
        mutated = json.loads(json.dumps(self.original))
        mutated["host"]["apis"]["js-yaml"].pop("exports")
        root = self._guard_repo(
            contract_bytes=json.dumps(mutated, ensure_ascii=False,
                                      indent=2).encode("utf-8"))
        outcome = self._run_guard(root)
        self.assertTrue(outcome["import_ok"], outcome)
        self.assertEqual(outcome["verdict"], "FAIL", outcome)
        self.assertIn("host.apis", outcome["reason"])
        self.assertNotIn("NOT_RUN", outcome["verdict"])

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
            (pkg / "lib").mkdir(parents=True)
            (pkg / "lib" / "index.js").write_text(
                _read(LIB_INDEX), encoding="utf-8")
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
                             ["__GOVERNANCE_REPO_ROOT__",
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

    def test_no_schema_fixture_uses_a_measured_zero_schema_row(self):
        # AUDIT-153 D-44 measured `@deepseek-ai/dsh-tool-ask-user` as a row
        # whose module exports no `Config`; the fixture must not invent one.
        with tempfile.TemporaryDirectory() as tmp:
            text = dsh_fixtures.emit_fixture(
                "FX-NO-SCHEMA-01", Path(tmp)).read_text(encoding="utf-8")
        self.assertIn("@deepseek-ai/dsh-tool-ask-user", text)
        self.assertIn("totallyBogusKeyThatMustBeRejected", text)


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
        # C-8 zero change: `adapters` is already in the 11-directory set, and
        # `cleanup.py` expands dir entries recursively (§2.9.2).
        directories = self.manifest["cleanup_scope"]["directories"]
        self.assertIn("adapters", directories)
        self.assertEqual(len(directories), 11)
        cleanup_text = _read(_REPO_ROOT / "skills"
                             / "software-project-governance" / "infra"
                             / "cleanup.py")
        self.assertIn('"adapters"', cleanup_text)

    def test_adapters_is_a_product_dir_entry_covering_the_contract(self):
        entries = self.manifest["product"]["entries"]
        self.assertIn({"path": "adapters/", "type": "dir"}, entries)


if __name__ == "__main__":
    unittest.main()
