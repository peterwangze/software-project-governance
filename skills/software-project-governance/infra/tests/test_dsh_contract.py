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
import io
import json
import re
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
        for token in install["env_overrides"].values():
            self.assertIn(f'"{token}"', guard_text, token)
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
        self.assertIn('COMPOSITION_FILENAMES = ("agent.cordis.yml",)',
                      guard_text.replace("'", '"'))
        for glob in home["composition_globs"]:
            self.assertIn(glob, guard_text, glob)

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
        for package, entry in apis.items():
            self.assertIn(package, guard_text, package)
            self.assertTrue(entry["role"], package)
            for symbol in entry["exports"]:
                self.assertIn(symbol, guard_text, f"{package}:{symbol}")
        self.assertEqual(len(apis), 4)

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
        launch_text = _read(LAUNCH_PY)
        lib_text = _read(LIB_INDEX)
        self.assertIn(f'PRESET_ID = "{preset["id"]}"', launch_text)
        self.assertIn(f"PRESET_MARKER = '{preset['version_marker']}'", lib_text)
        self.assertIn(f'SKILL_ROOT_MARKER = "{preset["skill_root_marker"]}"',
                      launch_text)

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
        self.assertEqual(checks["compat_section_title"],
                         _read(GUARD_PY).split(
                             'CHECK_SECTION_TITLE = "')[1].split('"')[0])
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
