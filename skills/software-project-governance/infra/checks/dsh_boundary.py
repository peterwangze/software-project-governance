"""Check 28w — the dsh dependency-boundary contract guard (K-1 … K-13).

FEAT-031 / 0.81.0 slice **V8**; design
``docs/requirements/dsh-compat-design-0.81.0.md`` §2.8 (the judgment list),
§2.9.4 (the wiring face) and §5 (the single diagnostic entry).

**What this check is.** The contract ``adapters/dsh/host-contract.json`` is the
single machine-readable statement of what this plugin consumes from the dsh
host. V2 migrated the consumers to read it; V3–V7 closed the individual
soundness gaps. This check is what makes the migration *judgeable*: it compares
the contract against the artifacts that must agree with it (the template, the
hooks, the patch, the version evidence, the coverage claims) and reports one
verdict.

**Why it is a module of its own.** Design §2.9.4 records the two structural
reasons: (a) ``registry.RegistryError`` is raised *at import time* when the
segment tables disagree, so the segment must be declared in
``quickscan_registry.py`` as well as ``registry.py``; (b) the engine is under a
frozen print budget, so the rendering lives here and the engine keeps only a
thin section that delegates.

**Purity (what this module may and may not do).** Every judgment is a pure
function of files under the package root: no child process is started, no
ambient environment variable is consulted, no directory outside the package is
walked, and nothing is written. That is what lets the whole check run under
``dsh-doctor --offline`` (design §5.1 / R1 N-3) and what keeps it usable in the
one situation it exists for — a broken renderer or a broken guard, which it
never imports.

**Import discipline.** ``registry`` is imported *inside* the functions that need
it (K-8's guard resolution, K-10's cleanup-scope equality). ``dsh_contract``
must not import ``registry`` (R0 F-15: that would close the cycle
``registry → checks.dsh_boundary → dsh_contract → registry``, invalidating
ADR-018 §8's "zero cycles" result); the reverse direction is safe precisely
because it is lazy and one-way, and it keeps ``dsh_boundary`` importable when
the registry itself is the broken component (K-10's whole point).

**The offline applicable domain (R1 N-3, now closed).** ``--offline`` is a
statement about *subprocess and host-plane probing*, not about reading files.
The two domains are therefore:

  * **file-level criteria** — K-1 … K-11 and K-13 — read only files inside the
    package (the contract, the template, the hooks, the patch, the manifest,
    the test tree, ``package.json``, ``cleanup.py``, the manifest declaration).
    They run unchanged under ``--offline``, and they are the reason ``--offline``
    can still FAIL.
  * **host-plane criteria** — the plane discovery, oracle-version and
    ``compat_range`` half of S3, the four hooks' *reachability* half of S7 —
    need a child process. They degrade to ``NOT_RUN`` under ``--offline``.

  K-12 (doctor ↔ boundary single verdict) is only *defined* for a run in which
  every stage actually ran; under ``--offline`` the doctor reports
  ``NOT_RUN`` for K-12 and renders the boundary exit code as evidence rather
  than as a comparison. Its comparison operand is therefore "all stages ran",
  which is exactly the domain in which the two verdicts are the same claim
  about the same repository state.

**Coverage strength and the ratchet (K-8 / K-11).** ``coverage.entries[]``
declares, per contract subject, how strong the guard is. K-8 makes the
declaration falsifiable — a ``strong`` claim must name a negative fixture, and
every ``guard`` reference must resolve to a test that exists or to a registered
check id. K-11 keeps the escape hatch (``allowlist``) from becoming
self-certification: entries carry ``literal`` + ``reason`` + ``since_slice``,
and the budget lives **outside** the contract so the contract cannot raise it in
the same commit that would need it raised (R1 N-2). DEC-192 ruled the budget to
**0** — zero exemptions, which is strictly stronger than the design's initial
budget of three.

Public surface:

  ``CRITERIA``            the K-ids in report order
  ``MIN_* / EXPECTED_*``  the frozen shapes K-1/K-3/K-10 compare against
  ``judge(repo_root=None)``  every criterion → a dict report
  ``verdict(report)``     PASS / FAIL / NOT_RUN for the report
  ``failed(report)``      the failing criteria only
  ``emit_check_section()``  render one ``Check 28w`` section, return issues
  ``main(argv)``          thin CLI (``--json``, ``--fail-on-issues``)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# The accessor is the contract's only reader (design §2.5.1) — never a second
# JSON parser, so the failure vocabulary of K-1 and of the consumers cannot
# drift apart.
import dsh_contract

__all__ = [
    "CRITERIA",
    "CheckUnavailable",
    "criterion_result",
    "check_dsh_boundary",
    "verdict",
    "failed",
    "emit_check_section",
    "main",
]

#: The frozen judgment list, in the order the design's §2.8 table lists it.
CRITERIA: Tuple[str, ...] = tuple(
    f"K-{index}" for index in range(1, 14))

#: K-12: the command key whose verdict must equal this check's exit code.
DOCTOR_COMMAND_KEY = "dsh-doctor"

#: K-1: the two `allowlist` keys V8 adds to the contract (design §2.1 / O-9).
CONTRACT_ALLOWLIST_PATH = "allowlist"
CONTRACT_ALLOWLIST_BUDGET_PATH = "allowlist_budget"

#: K-3 / §0.2 E-10: 16 top-level + 13 nested platform-independent rows. The
#: template must carry exactly this set, and so must `host.rows[]`.
EXPECTED_ROWS_TOP_LEVEL = 16
EXPECTED_ROWS_NESTED = 13
EXPECTED_ROW_TOTAL = EXPECTED_ROWS_TOP_LEVEL + EXPECTED_ROWS_NESTED

#: K-3: the four row keys K-6's patch reading and K-3's comparison share.
ROW_KEYS = ("package", "disabled_expr", "platform_conditional", "enabled_on",
            "config_keys", "config_declared", "group")

#: K-6: the four `own.patch.shape_invariants` spellings.
PATCH_INVARIANT_EXACTLY_ONE_INSERT = "exactly-one-insert-row"
PATCH_INVARIANT_NO_ID_UPDATE = "no-id-update"
PATCH_INVARIANT_NO_TRUST = "no-trust"
PATCH_INVARIANT_NO_JS = "no-!!js"

#: K-5: the fallback spelling of `host.env.write_side.fallback`. The contract
#: declares it as the prose form `<home>/.dsh` (it is a policy, not a path); the
#: hooks spell the same policy in shell. The mapping is declared here, once.
FALLBACK_PROSE = "<home>/.dsh"
FALLBACK_SHELL = "$HOME/.dsh"

#: K-7: the fields `adapter-manifest.json` must carry (design §2.4 D-60).
MANIFEST_REQUIRED_FIELDS = ("workflow_id", "entry_type", "support_status",
                            "trigger", "inputs", "outputs", "native_entry",
                            "runtime_e2e", "validation")

#: K-7: the pointer form the manifest may use instead of restating a date.
MANIFEST_EVIDENCE_POINTER_RE = re.compile(
    r"see\s+contract\s+evidence\.(verified_on|dsh_cli_version)", re.I)

#: K-8: the closed target vocabulary of §4.1.
COVERAGE_TARGETS = ("strong", "medium", "weak", "none")

#: K-2 / K-11: the classes of host literal the scan judges.
LITERAL_CLASSES = ("package", "env", "path", "marker")

_TEMPLATE_TOKEN_RE = re.compile(r"__[A-Za-z0-9_]+__")
_ROW_ID_RE = re.compile(r"^(\s*)- id: (\S+)\s*$")
_ROW_KEY_RE = re.compile(r"^(\s*)(name|disabled|config|group|isolate):\s*(.*)$")
_CONFIG_KEY_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
_TEST_REF_RE = re.compile(r"^test_[A-Za-z0-9_]+\.py::(test_[A-Za-z0-9_]+)$")
_SEGMENT_ID_RE = re.compile(r"^\d\d[a-z]?$")
_FIXTURE_ID_RE = re.compile(r"^FX-[A-Z0-9-]+$")
_AUDIT_ID_RE = re.compile(r"^D-\d{2,3}$")
_PLATFORM_EXPR_RE = re.compile(r"^!!js process\.platform\s*(===|!==)\s*'(\w+)'$")
_BASEURL_FORMS = ("file-url", "path", "url")


class CheckUnavailable(RuntimeError):
    """The check could not build a report at all (never a silent PASS).

    Raised only when the contract itself cannot be classified — an
    ``OSError``/``UnicodeDecodeError`` outside the accessor's own vocabulary.
    The engine's thin wrapper treats it as FAIL: a check that cannot state its
    judgment has not verified anything (C-6).
    """


# ── report primitives ───────────────────────────────────────────────────────


@dataclass
class Criterion:
    """One K-id's outcome (``PASS`` / ``FAIL`` / ``NOT_RUN`` + actionable text)."""

    ident: str
    verdict: str
    reason: str
    findings: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.ident,
            "verdict": self.verdict,
            "reason": self.reason,
            "findings": list(self.findings),
            "details": list(self.details),
        }


def criterion_result(ident, verdict, reason, *, findings=None, details=None):
    """Build one :class:`Criterion` (the one constructor the tests use too)."""
    return Criterion(
        ident=ident,
        verdict=verdict,
        reason=reason,
        findings=list(findings or ()),
        details=list(details or ()),
    )


def verdict(report: Dict[str, Any]) -> str:
    """The report-level verdict: FAIL if any criterion failed, else PASS/NOT_RUN.

    A criterion that did not run is *never* folded into PASS (design §4.6, the
    three-state policy): a run in which nothing was judged reports NOT_RUN. A
    *mixed* report is PASS at the top — the verified part is real — while every
    unverified criterion keeps its own ``[NOT_RUN]`` line, which is exactly the
    "disclose, never pretend" rule this check exists to enforce.
    """
    verdicts = [entry["verdict"] for entry in report.get("criteria", [])]
    if not verdicts:
        return "NOT_RUN"
    if "FAIL" in verdicts:
        return "FAIL"
    if all(item == "NOT_RUN" for item in verdicts):
        return "NOT_RUN"
    return "PASS"


def failed(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The failing criteria only (the engine section and the exit code use it)."""
    return [entry for entry in report.get("criteria", [])
            if entry["verdict"] == "FAIL"]


# ── path resolution ─────────────────────────────────────────────────────────


def _default_root() -> Path:
    """Package root, derived from this file (never the process CWD)."""
    # <pkg>/skills/software-project-governance/infra/checks/dsh_boundary.py
    return Path(__file__).resolve().parents[4]


class Subject:
    """The file paths one judgment reads — all overridable for negative tests.

    Negative tests must be able to run a criterion against a mutated *copy*
    without writing anywhere near the repository (the task's red line). Rather
    than monkey-patching module globals, every criterion takes a :class:`Subject`
    and reads through it.
    """

    def __init__(self, root: Optional[Path] = None, **overrides: Optional[Path]):
        self.root = Path(root) if root is not None else _default_root()
        # Presence is what marks an override, never truthiness: the negative
        # tests pin paths that do not exist yet (`<tmp>/absent.json`), and a
        # truthiness check would silently fall back to the shipped artifact —
        # the mutation test would then judge the real file and pass.
        self.contract_path = (overrides["contract"] if "contract" in overrides
                              else dsh_contract.contract_path(self.root))
        self.template = overrides.get("template") or (
            self.root / "agent-presets" / "governance" / "agent.cordis.yml.template")
        self.manifest = overrides.get("manifest") or (
            self.root / "adapters" / "dsh" / "adapter-manifest.json")
        self.package_json = overrides.get("package_json") or (self.root / "package.json")
        self.patch = overrides.get("patch") or (self.root / "cordis.patch.yml")
        self.host_row = overrides.get("host_row") or (
            self.root / "lib" / "index.js")
        self.hooks_dir = overrides.get("hooks_dir") or (
            self.root / "skills" / "software-project-governance" / "infra" / "hooks")
        self.tests_dir = overrides.get("tests_dir") or (
            self.root / "skills" / "software-project-governance" / "infra" / "tests")
        self.cleanup_py = overrides.get("cleanup_py") or (
            self.root / "skills" / "software-project-governance" / "infra" / "cleanup.py")
        self.core_manifest = overrides.get("core_manifest") or (
            self.root / "skills" / "software-project-governance" / "core" / "manifest.json")
        self.factsheet_glob = (overrides["factsheet_glob"]
                               if "factsheet_glob" in overrides
                               else self.root / "adapters" / "dsh" / "fixtures"
                               / "host-facts-*.json")


def _read(path: Path) -> str:
    """Read one artifact as UTF-8 text; an unreadable file is an empty string.

    Callers turn "empty" into an explicit finding, so a missing artifact is a
    reported FAIL rather than an exception that would abort the whole check.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _rel(path: Path) -> str:
    try:
        return path.as_posix()
    except Exception:  # pragma: no cover - defensive
        return str(path)


# ── contract access ─────────────────────────────────────────────────────────


class ContractFacts:
    """The contract document plus the two V8 allowlist declarations.

    The document is read from **the subject's own path** and parsed through the
    accessor (``load_contract(raw=...)``), so the accessor stays the only
    reader and its failure vocabulary is the one K-1 reports. Reading by raw
    text is deliberate: the accessor's file cache is keyed by path, and a check
    that judged a *mutated copy* must never receive a document cached earlier
    for the same path (it would pass a mutation test for the wrong reason).

    The allowlist block is not part of the V1 document (``own.notes`` records
    that V8 appends it), so declaring it on the in-memory copy here is how
    K-11's "absent means empty, never unbounded" rule stays judgeable.
    """

    def __init__(self, subject: Subject):
        self.subject = subject
        self.raw: Optional[str] = None
        self.document: Dict[str, Any] = {}
        self.allowlist: List[Dict[str, Any]] = []
        self.allowlist_budget = 0
        self.error: Optional[str] = None
        self.error_class: Optional[str] = None
        path = subject.contract_path
        # Read the subject's file, then hand the *text* to the accessor: the
        # accessor stays the only parser and the only source of the three
        # failure classes (§2.5.1), while a mutated copy is judged as a copy —
        # never as whatever document the accessor's path-keyed cache happens to
        # hold (a mutation test that judged the shipped file would pass for the
        # wrong reason).
        try:
            with open(path, "rb") as handle:
                payload = handle.read()
        except OSError as error:
            self.error = (f"ContractUnreadable: cannot read the host contract: "
                          f"{type(error).__name__}: {error} ({path})")
            self.error_class = "ContractUnreadable"
            return
        try:
            self.raw = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            self.error = (f"ContractUnreadable: cannot read the host contract: "
                          f"UnicodeDecodeError: {error} ({path})")
            self.error_class = "ContractUnreadable"
            return
        try:
            document = dict(dsh_contract.load_contract(raw=self.raw))
        except dsh_contract.ContractError as error:
            self.error = str(error)
            self.error_class = type(error).__name__
            return
        document.setdefault(CONTRACT_ALLOWLIST_PATH, [])
        document.setdefault(CONTRACT_ALLOWLIST_BUDGET_PATH, 0)
        self.document = document
        self.allowlist = list(document.get(CONTRACT_ALLOWLIST_PATH) or [])
        self.allowlist_budget = int(document.get(CONTRACT_ALLOWLIST_BUDGET_PATH) or 0)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def declared_allowlist(self) -> bool:
        """Whether the contract file itself declares the allowlist block."""
        for key in (CONTRACT_ALLOWLIST_PATH, CONTRACT_ALLOWLIST_BUDGET_PATH):
            if f'"{key}"' in self.raw:
                return True
        return False

    def get(self, path: str) -> Any:
        """Dotted path lookup through the accessor (same failure vocabulary)."""
        return dsh_contract.get(path, self.document)


# ── K-1 … K-13 ──────────────────────────────────────────────────────────────


def k1_contract_readable(facts: ContractFacts) -> Criterion:
    """K-1 — the contract parses, has a known schema, and declares every field.

    Delegates to the accessor's validation (§2.5.1's three exception classes are
    the classification K-1 reuses, so the check and the consumers cannot drift).
    A ``ContractUnreadable`` is a FAIL here, not a degradation: what a consumer
    may downgrade to NOT_RUN, the gate that judges the contract must report.
    """
    if facts.ok:
        rows = facts.get("host.rows")
        entries = facts.get("coverage.entries")
        dispositions = facts.get("elimination.dispositions")
        return criterion_result(
            "K-1", "PASS",
            f"contract readable: schema_version {facts.get('schema_version')}, "
            f"{len(rows)} host row(s), {len(entries)} coverage claim(s), "
            f"{len(dispositions)} disposition(s)",
            details=[f"read {len(facts.raw)} byte(s) from "
                     f"{_rel(facts.subject.contract_path)}"])
    return criterion_result(
        "K-1", "FAIL",
        f"{facts.error_class}: {facts.error}",
        findings=[facts.error or "contract unreadable"])


def _declared_literal_sets(document: Dict[str, Any]) -> Dict[str, set]:
    """The literal sets K-2 accepts, derived from the contract alone.

    Same derivation as V2's text scan (``test_dsh_contract.py``): the accepted
    set *is* the contract, so the contract cannot widen its own acceptance
    without the reader seeing it.
    """
    host = document["host"]
    packages = ({row["package"] for row in host["rows"]}
                | {document["own"]["package"]["name"]}
                | {"{0}/{1}".format(host["install"]["scope"],
                                    host["install"]["cli_package"])}
                | set(host["apis"]))
    for name in list(packages):
        parts = name.split("/")
        for index in range(1, len(parts)):
            packages.add("/".join(parts[:index]))
    return {
        "package": packages,
        "env": {host["env"]["home_var"], *host["install"]["env_overrides"].values()},
        "path": {host["home"]["user_preset_dir"], host["home"]["composition_file"]},
        "marker": {document["own"]["preset"]["version_marker"],
                   document["own"]["preset"]["skill_root_marker"]},
    }


#: The declared consumer set (design §2.5 + §2.9.4). Repo-relative, explicit so
#: widening it is a reviewable edit rather than a silent scan of the tree.
#:
#: F-04 (REVIEW-FEAT-031-CODE-R0) closed the gap against the design's own list:
#: the three declaration files — `package.json`, the patch layer and the adapter
#: manifest — are consumers too. They are the *inputs* the contract mirrors, so
#: each of their literals must be one the contract declares; a literal the
#: contract does not know (a package the host no longer owns, a renamed bundle
#: key) is exactly the drift the scan exists to catch, and the reviewer showed
#: the narrower set let it through silently.
K2_CONSUMERS: Tuple[str, ...] = (
    "lib/index.js",
    "adapters/dsh/launch.py",
    "skills/software-project-governance/infra/dsh_compat.py",
    "skills/software-project-governance/infra/verify_workflow.py",
    "agent-presets/governance/agent.cordis.yml.template",
    "skills/software-project-governance/infra/hooks/pre-commit",
    "skills/software-project-governance/infra/hooks/commit-msg",
    "skills/software-project-governance/infra/hooks/post-commit",
    "adapters/dsh/adapter-manifest.json",
    "package.json",
    "cordis.patch.yml",
)

#: The package class judges a quoted string **as a whole**: the literal must
#: *be* a package reference — `@scope/name`, optionally followed by `/`-separated
#: subpath segments — not merely contain one (FIX-322, closing F-07 of
#: REVIEW-FEAT-030-CODE-R0 and N-2 of REVIEW-FEAT-030-CODE-R1, where
#: ``findall`` over the literal reported a package spelling inside a message).
#: A sentence mentioning a package is prose: an error message quoting a
#: package name is a message, not a host fact. This mirrors the whole-literal
#: rationale recorded on ``_ENV_NAME_LITERAL_RE`` below.
_PACKAGE_RE = re.compile(r"@[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_QUOTED_RE = re.compile(r"([\"'`])((?:\\.|(?!\1).)*)\1")
_ENV_REF_RE = re.compile(
    r"(?:os\.environ\.get|os\.environ\[|process\.env\[|process\.env\.)"
    r"\(?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)")
_PATH_RE = re.compile(r"\.agent-presets\b|agent\.cordis\.yml(?!\.template)")
_MARKER_RE = re.compile(r"\.dsh-bundle-version\b|\bskill-root\.txt\b")
#: A `DSH_…` name spelled as a whole string literal — how a *declaration* file
#: (package.json, the adapter manifest) names an env var, where no accessor call
#: exists to read. Whole-content matching is deliberate: a sentence mentioning
#: `DSH_HOME` is prose, a literal that *is* `DSH_HOME` is a declaration.
_ENV_NAME_LITERAL_RE = re.compile(r"^DSH[A-Z0-9_]*$")

#: The consumers where that spelling applies. In a **code** file the same
#: spelling is a module-level symbol — `dsh_compat.py` declares its own
#: `DSH_SCOPE` / `DSH_PACKAGE` / `DSH_HOME_ENV` constants, and flagging those
#: would report our symbols as host facts (the false positive the accessor-only
#: env class was written to avoid).
K2_DECLARATION_CONSUMERS: Tuple[str, ...] = (
    "adapters/dsh/adapter-manifest.json",
    "package.json",
    "cordis.patch.yml",
)


def quoted_literals(text: str) -> List[str]:
    """Every string literal in ``text`` (``'``, ``"`` and backticks)."""
    return [match.group(2) for match in _QUOTED_RE.finditer(text)]


def scan_outside_contract_literals(subject: Subject, facts: ContractFacts,
                                   paths: Sequence[str] = K2_CONSUMERS,
                                   allowlist: Optional[Sequence[Dict[str, Any]]] = None,
                                   ) -> List[Tuple[str, int, str, str]]:
    """Every outside-contract host literal, as ``(file, line, class, literal)``.

    Walks the declared consumer set, not the tree: a glob would silently widen
    the judged surface. An *absent* consumer is skipped here and reported by the
    K-2 entry itself, so "the file moved" and "the literal reappeared" stay
    distinguishable.
    """
    if not facts.ok:
        raise ValueError("the outside-contract scan needs a readable contract")
    declared = _declared_literal_sets(facts.document)
    entries = facts.allowlist if allowlist is None else allowlist
    allowed = {(entry.get("literal"), path)
               for entry in entries
               for path in (entry.get("files") or ())}
    violations: List[Tuple[str, int, str, str]] = []
    for relative in paths:
        text = _read(subject.root / relative)
        if not text:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            def report(kind: str, literal: str) -> None:
                if (literal, relative) not in allowed:
                    violations.append((relative, line_number, kind, literal))

            for literal in quoted_literals(line):
                # package class: whole-literal judgment (see _PACKAGE_RE) — the
                # literal must *be* a package reference. The match is anchored
                # at the literal start; a `/`-prefixed rest is a subpath and an
                # `@`-prefixed rest is a version tag of the same package — both
                # stay attributed to their package token (F-2,
                # REVIEW-FIX-320-322-CODE-R0).
                package_match = _PACKAGE_RE.match(literal)
                if package_match:
                    rest = literal[package_match.end():]
                    if (not rest or rest.startswith(("/", "@"))) \
                            and package_match.group(0) not in declared["package"]:
                        report("package", package_match.group(0))
                # env names in declaration files: a whole-literal `DSH_…`
                if (relative in K2_DECLARATION_CONSUMERS
                        and _ENV_NAME_LITERAL_RE.match(literal)
                        and literal not in declared["env"]):
                    report("env", literal)
                for kind, pattern, key in (("path", _PATH_RE, "path"),
                                           ("marker", _MARKER_RE, "marker")):
                    for match in pattern.finditer(literal):
                        if match.group(0) not in declared[key]:
                            report(kind, match.group(0))
            for reference in _ENV_REF_RE.finditer(line):
                name = reference.group(1)
                if name in declared["env"] or not name.startswith("DSH"):
                    continue
                report("env", name)
    return violations


def k2_no_outside_literal(subject: Subject, facts: ContractFacts) -> Criterion:
    """K-2 — no consumer holds a host fact of its own.

    V8 form: the V2 text scan widened to the declared consumer set, judged
    against the contract's allowlist (whose budget K-11 constrains).
    """
    if not facts.ok:
        return criterion_result("K-2", "FAIL",
                                "outside-contract scan needs a readable contract")
    missing = [relative for relative in K2_CONSUMERS
               if not (subject.root / relative).is_file()]
    violations = scan_outside_contract_literals(subject, facts)
    findings = [f"{relative}:{line} [{kind}] \"{literal}\""
                for relative, line, kind, literal in violations]
    if missing:
        findings.extend(f"declared consumer missing: {name}" for name in missing)
    if findings:
        return criterion_result(
            "K-2", "FAIL",
            f"{len(findings)} outside-contract host literal(s) or missing "
            f"consumer(s)", findings=findings)
    return criterion_result(
        "K-2", "PASS",
        f"outside-contract host literals: 0 ({len(K2_CONSUMERS)} declared "
        f"consumer(s) scanned)")


# ── template row derivation (K-3) ───────────────────────────────────────────


def parse_template_rows(text: str, origin: str = "<template>") -> List[Dict[str, Any]]:
    """Re-derive the row table from the template text, independently of JSON.

    Strict by construction (mirrors the V1 caliber): a row is a
    ``- id: <name>`` entry at indent 0 or 4 — the two depths this composition
    uses — and its row keys sit at ``row_indent + 2``. A row-looking line at any
    other indent raises, so a mutation cannot be silently absorbed.
    """
    lines = text.split("\n")
    rows: List[Dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = _ROW_ID_RE.match(lines[index])
        if not match:
            index += 1
            continue
        indent = len(match.group(1))
        if indent not in (0, 4):
            raise ValueError(
                f"{origin}:{index + 1}: row at unexpected indent {indent}")
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
                    if _ROW_ID_RE.match(child):
                        break
                    config_key = _CONFIG_KEY_RE.match(child)
                    if config_key and child_indent == indent + 4:
                        row["config_keys"].append(config_key.group(2))
                    index += 1
                continue
            index += 1
        rows.append(row)
    return link_template_rows(rows)


def link_template_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach nested rows to their group and derive the effective ``group``."""
    stack: Optional[Dict[str, Any]] = None
    for row in rows:
        if row["indent"] == 0:
            stack = row if row["is_group"] else None
            row["group"] = None
        else:
            if stack is None:
                raise ValueError(
                    f"row {row['row_id']} is nested but no top-level group "
                    f"precedes it")
            row["group"] = stack["row_id"]
            stack["children"].append(row["row_id"])
    return rows


def enabled_on_of(row: Dict[str, Any]) -> Optional[str]:
    """Derive the per-row enablement from the template's own disabled form."""
    if row["is_group"]:
        return None
    expr = row["disabled_expr"]
    if expr is None:
        return "any"
    if expr == "true":
        return "never"
    match = _PLATFORM_EXPR_RE.match(expr)
    if match:
        operator, platform = match.group(1), match.group(2)
        return "posix" if (platform == "win32") == (operator == "===") else "win32"
    raise ValueError(f"row {row['row_id']}: unknown disabled form {expr!r}")


def platform_conditional_of(row: Dict[str, Any]) -> bool:
    return (row["disabled_expr"] or "").startswith("!!js process.platform")


def template_row_mismatches(rows: Sequence[Dict[str, Any]],
                            declared: Sequence[Dict[str, Any]]) -> List[str]:
    """K-3's comparison as a value: how the two sides disagree.

    Order-independent by construction; the empty list means "they agree".
    """
    by_id = {row["row_id"]: row for row in declared}
    template_ids = [row["row_id"] for row in rows]
    mismatches: List[str] = []
    if len(template_ids) != len(set(template_ids)):
        mismatches.append(f"template row ids are not unique: {template_ids}")
    for missing in sorted(set(by_id) - set(template_ids)):
        mismatches.append(f"contract row absent from template: {missing}")
    for extra in sorted(set(template_ids) - set(by_id)):
        mismatches.append(f"template row not in contract: {extra}")
    for row in rows:
        declared_row = by_id.get(row["row_id"])
        if declared_row is None:
            continue
        derived = {
            "package": row["package"],
            "disabled_expr": row["disabled_expr"],
            "platform_conditional": platform_conditional_of(row),
            "enabled_on": enabled_on_of(row),
            "config_keys": row["config_keys"],
            "config_declared": row["config_declared"],
            "group": row["group"],
        }
        for key in ROW_KEYS:
            if declared_row.get(key) != derived[key]:
                mismatches.append(
                    f"{row['row_id']}.{key}: {declared_row.get(key)!r} != "
                    f"{derived[key]!r}")
    return mismatches


def k3_template_rows_match_contract(subject: Subject,
                                    facts: ContractFacts) -> Criterion:
    """K-3 — template rows ↔ ``host.rows[]``, both directions, full set."""
    if not facts.ok:
        return criterion_result("K-3", "FAIL",
                                "row comparison needs a readable contract")
    text = _read(subject.template)
    if not text:
        return criterion_result("K-3", "FAIL",
                                f"template missing: {_rel(subject.template)}")
    try:
        rows = parse_template_rows(text, origin=subject.template.name)
    except ValueError as error:
        return criterion_result("K-3", "FAIL", str(error), findings=[str(error)])
    declared = facts.get("host.rows")
    mismatches = template_row_mismatches(rows, declared)
    if mismatches:
        return criterion_result(
            "K-3", "FAIL", f"{len(mismatches)} row disagreement(s)",
            findings=mismatches)
    return criterion_result(
        "K-3", "PASS",
        f"template rows == contract host.rows[]: {len(rows)} row(s) "
        f"({EXPECTED_ROWS_TOP_LEVEL} top-level + {EXPECTED_ROWS_NESTED} nested)",
        details=[f"both sides declare rows, packages, disabled forms, config "
                 f"keys and group links identically"])


# ── K-4 ─────────────────────────────────────────────────────────────────────


def k4_tokens_match(subject: Subject, facts: ContractFacts) -> Criterion:
    """K-4 — token set equality, and no token left behind after rendering."""
    if not facts.ok:
        return criterion_result("K-4", "FAIL",
                                "token comparison needs a readable contract")
    text = _read(subject.template)
    if not text:
        return criterion_result("K-4", "FAIL",
                                f"template missing: {_rel(subject.template)}")
    tokens = facts.get("own.render.tokens")
    found = set(_TEMPLATE_TOKEN_RE.findall(text))
    findings: List[str] = []
    for extra in sorted(found - set(tokens)):
        findings.append(f"unknown token in template: {extra}")
    for missing in sorted(set(tokens) - found):
        findings.append(f"contract token absent from template: {missing}")
    rendered = text
    for token, relative in tokens.items():
        rendered = rendered.replace(token, "" if not relative else f"/pkg/{relative}")
    pattern = re.compile(facts.get("own.render.leftover_scan"))
    leftovers = sorted(set(pattern.findall(rendered)))
    for leftover in leftovers:
        findings.append(f"token left after rendering: {leftover}")
    if findings:
        return criterion_result("K-4", "FAIL",
                                f"{len(findings)} token disagreement(s)",
                                findings=findings)
    return criterion_result(
        "K-4", "PASS",
        f"template token set == contract token set ({len(tokens)} token(s)); "
        f"no `{facts.get('own.render.leftover_scan')}` residue after rendering")


# ── K-5 ─────────────────────────────────────────────────────────────────────


def _composition_file_expr(facts: ContractFacts) -> str:
    """The declared composition file name, derived from `own.preset.template`.

    Built from the template path rather than restated: the composition file is
    the template's name minus the render suffix, so a rename in the contract
    moves this derivation with it.
    """
    name = Path(facts.get("own.preset.template")).name
    return name[:-len(".template")] if name.endswith(".template") else name


def k5_hook_paths(facts: ContractFacts, subject: Subject) -> Criterion:
    """K-5 — the hooks' path expression equals the one the contract implies.

    The hooks are shell and keep their expression inline (design §2.5 C-5:
    giving them a parser would add the coupling the slice removes), so the guard
    is the static equality between the hook text and the expression derived from
    ``host.env.*`` + ``host.home.*`` + ``own.preset.*``. All three hooks share
    one preset-root expression; the composition file name is asserted
    separately, because the hooks reach the preset directory and then read the
    markers inside it.
    """
    if not facts.ok:
        return criterion_result("K-5", "FAIL",
                                "hook comparison needs a readable contract")
    preset_root = "/".join((facts.get("host.home.user_preset_dir"),
                            facts.get("own.preset.id")))
    fallback = facts.get("host.env.write_side.fallback")
    shell_fallback = FALLBACK_SHELL if fallback == FALLBACK_PROSE else fallback
    expected = ("${%s:-%s}/%s"
                % (facts.get("host.env.home_var"), shell_fallback, preset_root))
    marker = facts.get("own.preset.skill_root_marker")
    findings: List[str] = []
    for hook_name in ("pre-commit", "commit-msg", "post-commit"):
        path = subject.hooks_dir / hook_name
        text = _read(path)
        if not text:
            findings.append(f"hook missing: {_rel(path)}")
            continue
        if expected not in text:
            findings.append(
                f"hook path drift: {hook_name} does not contain the declared "
                f"expression {expected}")
        if marker not in text:
            findings.append(
                f"hook marker drift: {hook_name} does not read the declared "
                f"skill-root marker {marker}")
    if findings:
        return criterion_result("K-5", "FAIL",
                                f"{len(findings)} hook path disagreement(s)",
                                findings=findings)
    return criterion_result(
        "K-5", "PASS",
        f"hook path expression == declared expression ({expected}); all three "
        f"hooks read the declared marker `{marker}`")


# ── K-6 ─────────────────────────────────────────────────────────────────────


def patch_shape_findings(text: str, invariants: Sequence[str]) -> List[str]:
    """K-6's four shape invariants as a value (empty list = the patch holds).

    Two readings matter for the judgment to mean what the design says:

      * YAML comments are dropped first (replaced by an empty line, so line
        numbers survive). This patch documents the four invariants *by name* in
        its header; a guard a comment can trip would be reporting its own
        documentation;
      * an ``- id:`` line nested **inside** an ``insert:`` row is that row's
        payload, not an id-targeted UPDATE row. ``no-id-update`` is violated
        only by a *top-level* ``- id:`` entry, which would replace the targeted
        row's whole config (DEC-187 I-1).
    """
    text = re.sub(r"^[ \t]*#.*$", "", text, flags=re.M)
    lines = text.splitlines()
    inserts: List[str] = []
    id_rows: List[str] = []
    insert_indent: Optional[int] = None
    for line in lines:
        stripped = line.strip()
        if insert_indent is not None:
            if not stripped:
                continue
            if len(line) - len(line.lstrip()) > insert_indent:
                continue  # the insert row's own payload
            insert_indent = None
        if stripped.startswith("-") and "insert:" in stripped:
            inserts.append(line)
            insert_indent = len(line) - len(line.lstrip())
            continue
        if re.match(r"^\s*-\s*id:\s*\S+", line):
            id_rows.append(line)
    findings: List[str] = []
    if PATCH_INVARIANT_EXACTLY_ONE_INSERT in invariants and len(inserts) != 1:
        findings.append(
            f"{PATCH_INVARIANT_EXACTLY_ONE_INSERT}: found {len(inserts)} "
            f"insert row(s), expected exactly 1")
    if PATCH_INVARIANT_NO_ID_UPDATE in invariants and id_rows:
        findings.append(
            f"{PATCH_INVARIANT_NO_ID_UPDATE}: {len(id_rows)} id-targeted "
            f"UPDATE row(s) present (first: {id_rows[0].strip()})")
    if PATCH_INVARIANT_NO_TRUST in invariants and re.search(r"^\s*trust:", text, re.M):
        findings.append(f"{PATCH_INVARIANT_NO_TRUST}: a `trust:` key is present")
    if PATCH_INVARIANT_NO_JS in invariants and "!!js" in text:
        findings.append(f"{PATCH_INVARIANT_NO_JS}: an `!!js` expression is present")
    return findings


def k6_patch_shape(subject: Subject, facts: ContractFacts) -> Criterion:
    """K-6 — exactly one insert row, no id-targeted UPDATE, no trust, no `!!js`."""
    if not facts.ok:
        return criterion_result("K-6", "FAIL",
                                "patch judgment needs a readable contract")
    text = _read(subject.patch)
    if not text:
        return criterion_result("K-6", "FAIL",
                                f"patch missing: {_rel(subject.patch)}")
    invariants = facts.get("own.patch.shape_invariants")
    findings = patch_shape_findings(text, invariants)
    if findings:
        return criterion_result("K-6", "FAIL",
                                f"{len(findings)} patch invariant violation(s)",
                                findings=findings)
    return criterion_result(
        "K-6", "PASS",
        f"patch invariants hold: {', '.join(invariants)}")


# ── K-7 ─────────────────────────────────────────────────────────────────────


def _parse_date(value: Any) -> Optional[date]:
    """Parse an ISO date / datetime; anything else is not a date."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def ttl_findings(verified_on: Optional[date], ttl_days: Optional[int],
                 today: date) -> List[str]:
    """TTL judgment as a value: expired declarations, nothing else."""
    if verified_on is None or ttl_days is None:
        return []
    age = (today - verified_on).days
    if age > ttl_days:
        return [f"evidence stale: verified_on={verified_on.isoformat()} is "
                f"{age} day(s) old (ttl {ttl_days})"]
    return []


def _manifest_evidence_findings(manifest: Dict[str, Any],
                                facts: ContractFacts) -> List[str]:
    """The manifest half of K-7: fields present, evidence version == contract."""
    findings: List[str] = []
    missing = [name for name in MANIFEST_REQUIRED_FIELDS if name not in manifest]
    if missing:
        findings.append(f"manifest missing required field(s): {missing}")
    runtime = manifest.get("runtime_e2e")
    if not isinstance(runtime, dict):
        findings.append("manifest `runtime_e2e` is not an object")
        return findings
    declared_version = facts.get("evidence.dsh_cli_version")
    declared_verified = facts.get("evidence.verified_on")
    verified = runtime.get("verified_on")
    if isinstance(verified, str):
        if MANIFEST_EVIDENCE_POINTER_RE.search(verified):
            pass  # a pointer to the contract is the honest form
        elif _parse_date(verified) is None:
            findings.append(f"manifest evidence drift: `runtime_e2e.verified_on` "
                            f"{verified!r} is neither a date nor a contract pointer")
        elif declared_verified is None:
            findings.append(
                f"manifest evidence drift: `runtime_e2e.verified_on` states "
                f"{verified!r} but the contract records none")
        elif _parse_date(verified) != _parse_date(declared_verified):
            findings.append(
                f"manifest evidence drift: manifest {verified!r} vs contract "
                f"{declared_verified!r}")
    elif verified is not None:
        findings.append("manifest `runtime_e2e.verified_on` must be a string")
    version_text = json.dumps(manifest, ensure_ascii=False)
    if declared_version:
        if declared_version not in version_text:
            findings.append(
                f"manifest evidence drift: contract records dsh_cli_version "
                f"{declared_version!r}; the manifest does not name it")
    return findings


#: K-7's third clause (design §2.8): the two hand-maintained host-facing files
#: must not restate a dsh version. Two patterns cooperate:
#:
#:   * ``_VERSION_LITERAL_RE`` matches a dotted triple with an optional
#:     pre-release tag — the shape AUDIT-153 G-11/G-12 measured as stale
#:     (`0.1.5-rc.2`, `0.1.0-rc.6`);
#:   * ``_CITATION_PREFIX_RE`` recognises a **section reference** (`§2.5.1`), and
#:     ``_CITATION_SUFFIX_RE`` a deeper chain (`2.5.1.3`). Neither is a version,
#:     and reporting design citations as stale host versions would be noise:
#:     the judgment exists to catch a restated *host* fact, not to police prose.
_VERSION_LITERAL_RE = re.compile(r"\b\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\b")
_CITATION_PREFIX_RE = re.compile(r"\u00a7\s*$")
_CITATION_SUFFIX_RE = re.compile(r"^[.\d]")


def version_literal_scan_paths(facts: ContractFacts,
                               subject: Subject) -> List[Tuple[str, Path]]:
    """The files K-7's third clause scans, derived from the contract.

    ``own.patch.file`` (the patch layer) and ``own.host_row.entry`` (the host
    row) are the two files the design names; resolving them through the
    contract means a rename moves the scan with it.
    """
    seams = (("own.patch.file", subject.patch),
             ("own.host_row.entry", subject.host_row))
    pairs = []
    for key, path in seams:
        relative = facts.get(key)
        if isinstance(relative, str) and relative:
            pairs.append((relative, path))
    return pairs


def accepted_version_literals(facts: ContractFacts,
                              subject: Subject) -> set:
    """The version literals these files may legitimately contain.

    Only self-references and contract-declared facts qualify: our own package
    version, the recorded dsh version and the recorded oracle versions. A host
    version the contract does **not** record is by definition not traceable, so
    it fails rather than being tolerated — that is the whole point of the
    clause.
    """
    accepted = set()
    package_version = _package_version_from(subject.root)
    if package_version:
        accepted.add(package_version)
    recorded = facts.get("evidence.dsh_cli_version")
    if isinstance(recorded, str) and recorded:
        accepted.add(recorded)
    for value in (facts.get("evidence.oracle_packages") or {}).values():
        if isinstance(value, dict) and isinstance(value.get("version"), str):
            accepted.add(value["version"])
    return accepted


def _package_version_from(root: Path) -> Optional[str]:
    """Our own ``package.json`` version (a self-reference, not a host fact)."""
    try:
        document = json.loads(_read(root / "package.json"))
    except ValueError:
        return None
    version = document.get("version")
    return version if isinstance(version, str) and version else None


def version_literal_findings(facts: ContractFacts,
                             subject: Subject) -> List[str]:
    """K-7's third clause as a value: stale dsh version literals, ``file:line``.

    Every occurrence is reported (code *or* comment — a version claim in prose
    goes stale exactly like one in code, which is how G-11/G-12 arose), and the
    accepted set is the contract's own record.
    """
    accepted = accepted_version_literals(facts, subject)
    findings: List[str] = []
    for relative, path in version_literal_scan_paths(facts, subject):
        text = _read(path)
        if not text:
            findings.append(f"version-literal scan cannot read {relative}")
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in _VERSION_LITERAL_RE.finditer(line):
                literal = match.group(0)
                if literal in accepted:
                    continue
                if _CITATION_PREFIX_RE.search(line[:match.start()]):
                    continue  # `§2.5.1` — a section reference
                if _CITATION_SUFFIX_RE.match(line[match.end():]):
                    continue  # `2.5.1.3` — a deeper numbering chain
                findings.append(
                    f"dsh version literal outside the contract: "
                    f"{relative}:{line_number} {literal!r}")
    return findings


def k7_version_evidence(facts: ContractFacts, subject: Subject,
                        *, today: Optional[date] = None) -> Criterion:
    """K-7 — version evidence consistency and TTL, consumed (never recomputed).

    Three clauses (design §2.8): manifest ↔ contract evidence agreement, the TTL
    on a *recorded* date, and the ban on restated dsh version literals in
    ``cordis.patch.yml`` / ``lib/index.js``. The first two are ``NOT_RUN`` while
    the contract is unrecorded (V1 ships every recorded field ``null``; §2.4:
    "null = not recorded ⇒ the judgments that depend on it MUST be NOT_RUN,
    never treated as expired or as passing") — the third is judged regardless,
    because it is a statement about *our* files, not about the host plane.

    A *recorded* value that has aged out is a FAIL: a stale "runtime-verified"
    claim is exactly what C-20 forbids.
    """
    if not facts.ok:
        return criterion_result("K-7", "FAIL",
                                "evidence judgment needs a readable contract")
    today = today or datetime.now(timezone.utc).date()
    ttl = facts.get("evidence.verified_on_ttl_days")
    verified_on = _parse_date(facts.get("evidence.verified_on"))
    manifest_text = _read(subject.manifest)
    if not manifest_text:
        return criterion_result("K-7", "FAIL",
                                f"manifest missing: {_rel(subject.manifest)}")
    try:
        manifest = json.loads(manifest_text)
    except ValueError as error:
        return criterion_result("K-7", "FAIL",
                                f"manifest is not valid JSON: {error}",
                                findings=[str(error)])
    findings = _manifest_evidence_findings(manifest, facts)
    stale = ttl_findings(verified_on, ttl, today)
    findings.extend(stale)
    # The third clause is judged even while the evidence is unrecorded: it is a
    # statement about our own files, so the host plane's absence cannot excuse
    # it (and this is the clause whose absence let the reviewer's injected
    # version literal through unguarded).
    literals = version_literal_findings(facts, subject)
    findings.extend(literals)
    if findings:
        return criterion_result("K-7", "FAIL",
                                f"{len(findings)} evidence disagreement(s)",
                                findings=findings)
    if verified_on is None:
        return criterion_result(
            "K-7", "NOT_RUN",
            "no restated dsh version literal in `own.patch.file` / "
            "`own.host_row.entry`; the contract's own evidence is unrecorded "
            "(verified_on = null) so the TTL and version comparison are NOT "
            "RUN — recording is the maintainer's reviewed-commit step, see "
            "`dsh-doctor --record-evidence`")
    return criterion_result(
        "K-7", "PASS",
        f"manifest evidence == contract evidence (dsh_cli_version "
        f"{facts.get('evidence.dsh_cli_version')}, verified_on "
        f"{verified_on.isoformat()}, ttl {ttl} day(s), not expired); no "
        f"restated dsh version literal in the scanned files")


# ── K-8 ─────────────────────────────────────────────────────────────────────


def _test_definitions(subject: Subject) -> Dict[str, set]:
    """``{test_file.py: {test_name, ...}}`` for the whole test tree.

    Unanchored on purpose: test methods live inside ``unittest.TestCase``
    classes, so an indentation-sensitive pattern would find nothing and quietly
    turn every guard reference into "unbacked".
    """
    definitions: Dict[str, set] = {}
    if not subject.tests_dir.is_dir():
        return definitions
    for path in sorted(subject.tests_dir.rglob("test_*.py")):
        definitions[path.name] = set(
            re.findall(r"^\s*def (test_\w+)", _read(path), re.M))
    return definitions


def _registered_segments() -> set:
    """The registry's declared segments (lazy import: see the module docstring)."""
    import registry  # noqa: PLC0415 — deliberate, lazy, one-way

    return set(registry.segment_ids())


def _registered_command_keys() -> set:
    import registry  # noqa: PLC0415 — deliberate, lazy, one-way

    return set(registry.command_keys())


def _fixture_vocabulary() -> set:
    """The declared fixture ids (emittable + deferred), from the fixture module."""
    import importlib.util  # noqa: PLC0415 — lazy so the check works without it

    path = (Path(__file__).resolve().parents[1] / "tests" / "dsh_fixtures.py")
    if not path.is_file():
        return set()
    spec = importlib.util.spec_from_file_location("_spg_dsh_fixture_vocab", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # pragma: no cover - a broken fixture module is reported
        return set()
    try:
        return set(module.known_fixture_ids())
    except Exception:  # pragma: no cover
        return set()


def k8_coverage_claims(facts: ContractFacts, subject: Subject,
                       *, test_definitions: Optional[Dict[str, set]] = None,
                       segments: Optional[set] = None,
                       commands: Optional[set] = None,
                       fixture_ids: Optional[set] = None,
                       acknowledged: Optional[Sequence[str]] = None) -> Criterion:
    """K-8 — every coverage claim is provable, and ``strong`` needs a negative.

    Guard references must resolve to a test that exists in ``infra/tests/``, to
    a registered segment id, or to a registered command key; ``subject`` must
    resolve inside the contract; ``target == "strong"`` must name at least one
    fixture. Fixture *existence in the vocabulary* is required of every fixture
    reference — whether this slice can already emit its bytes is K-13's
    business, not K-8's, so the judgment keeps its edge: a reference to a
    fixture nobody has declared is still FAIL.
    """
    if not facts.ok:
        return criterion_result("K-8", "FAIL",
                                "coverage judgment needs a readable contract")
    definitions = (test_definitions if test_definitions is not None
                   else _test_definitions(subject))
    try:
        segment_ids = set(segments) if segments is not None else _registered_segments()
        command_keys = (set(commands) if commands is not None
                        else _registered_command_keys())
    except Exception as error:  # registry unimportable → the claim is unbacked
        return criterion_result(
            "K-8", "FAIL",
            f"cannot resolve guard references: the registry is unreadable "
            f"({type(error).__name__}: {error})",
            findings=[str(error)])
    fixtures = (set(fixture_ids) if fixture_ids is not None
                else _fixture_vocabulary())
    entries = facts.get("coverage.entries")
    findings: List[str] = []
    subjects: List[str] = []
    for entry in entries:
        subject_path = entry.get("subject", "")
        subjects.append(subject_path)
        target = entry.get("target")
        if target not in COVERAGE_TARGETS:
            findings.append(f"coverage target outside the vocabulary: "
                            f"subject={subject_path} target={target!r}")
        try:
            dsh_contract.get(subject_path, facts.document)
        except dsh_contract.ContractError:
            findings.append(f"coverage subject does not resolve inside the "
                            f"contract: subject={subject_path}")
        guards = list(entry.get("guard") or ())
        if not guards:
            findings.append(f"coverage claim unbacked (no guard): "
                            f"subject={subject_path}")
        for reference in guards:
            if not _guard_resolves(reference, definitions, segment_ids,
                                   command_keys):
                findings.append(f"coverage claim unbacked: subject={subject_path} "
                                f"guard={reference!r} resolves to nothing")
        if target == "strong" and not entry.get("negative_fixtures"):
            findings.append(f"coverage claim unbacked: subject={subject_path} "
                            f"target=strong without a negative fixture")
        if target == "none" and entry.get("necessity") == "necessary":
            findings.append(f"coverage claim unbacked: subject={subject_path} "
                            f"target=none for a necessary dependency")
        for fixture in entry.get("negative_fixtures") or ():
            if fixture not in fixtures:
                findings.append(f"coverage claim unbacked: subject={subject_path} "
                                f"negative fixture {fixture!r} is not declared "
                                f"in the fixture vocabulary")
            if not _FIXTURE_ID_RE.match(fixture):
                findings.append(f"negative fixture form: {fixture!r} is not an "
                                f"`FX-…` id")
    duplicates = sorted({name for name in subjects if subjects.count(name) > 1})
    for name in duplicates:
        findings.append(f"duplicate coverage subject: {name}")
    if findings:
        return criterion_result("K-8", "FAIL",
                                f"{len(findings)} unbacked coverage claim(s)",
                                findings=findings)
    strong = sum(1 for entry in entries if entry.get("target") == "strong")
    return criterion_result(
        "K-8", "PASS",
        f"{len(entries)} coverage claim(s) backed: {strong} strong claim(s) "
        f"each name a negative fixture; every guard reference resolves "
        f"({len(definitions)} test file(s), {len(segment_ids)} segment(s), "
        f"{len(command_keys)} command key(s))")


def _guard_resolves(reference: str, definitions: Dict[str, set],
                    segments: set, commands: Optional[set] = None) -> bool:
    """Whether one ``coverage.entries[].guard`` reference names a real guard.

    Three accepted spellings, all resolvable to something that exists:

      * a registered **command key** (``check-manifest-consistency``) — the
        judgment runs as its own CLI entry;
      * a **segment id** (``28v``) — the judgment runs inside the engine;
      * a **test id** (``test_x.py::test_y`` or an unambiguous bare name).

    A reference that resolves to nothing is the failure mode K-8 exists for:
    §4.1's fourth rule ("声明强于佐证在结构上不可表达").
    """
    if not isinstance(reference, str) or not reference:
        return False
    if commands is not None and reference in commands:
        return True
    if _SEGMENT_ID_RE.match(reference):
        return reference in segments
    match = _TEST_REF_RE.match(reference)
    if match:
        return match.group(1) in definitions.get(match.group(0).split("::")[0], set())
    owners = [name for name, tests in definitions.items() if reference in tests]
    return len(owners) == 1


# ── K-9 ─────────────────────────────────────────────────────────────────────


def k9_dispositions(facts: ContractFacts) -> Criterion:
    """K-9 — every audit id is disposed of once, and the necessary set is covered."""
    if not facts.ok:
        return criterion_result("K-9", "FAIL",
                                "disposition judgment needs a readable contract")
    entries = facts.get("coverage.entries")
    dispositions = facts.get("elimination.dispositions")
    baseline = facts.get("elimination.audit_baseline")
    findings: List[str] = []
    ids = [item.get("id") for item in dispositions]
    duplicates = sorted({name for name in ids if ids.count(name) > 1})
    for name in duplicates:
        findings.append(f"duplicate disposition: {name}")
    expected = set()
    class_field = {"necessary": "necessary_ids", "weakenable": "weakenable_ids",
                   "eliminable": "eliminable_ids", "historical": "historical_ids"}
    for field_name in class_field.values():
        expected.update(baseline[field_name])
    covered = set(ids)
    for missing in sorted(expected - covered):
        findings.append(f"disposition missing for {missing}")
    for extra in sorted(covered - expected):
        findings.append(f"disposition outside the audit baseline: {extra}")
    if len(covered) != baseline["total"]:
        findings.append(f"disposition count {len(covered)} != baseline total "
                        f"{baseline['total']}")
    for item in dispositions:
        ident = item.get("id")
        if not _AUDIT_ID_RE.match(str(ident)):
            findings.append(f"disposition id form: {ident!r} is not a `D-nn` id")
        if item.get("class") not in class_field:
            findings.append(f"disposition class outside the vocabulary: {ident} "
                            f"{item.get('class')!r}")
        if item.get("decision") == "eliminated" and not item.get("removed_at"):
            findings.append(f"eliminated disposition without a removal slice: {ident}")
        if (item.get("decision") in ("weakened", "deferred")
                and not item.get("weakened_at") and not item.get("slice")):
            findings.append(f"weakened/deferred disposition without a slice: {ident}")
    covered_ids = {audit_id for entry in entries
                   for audit_id in (entry.get("audit_ids") or ())}
    for missing in sorted(set(baseline["necessary_ids"]) - covered_ids):
        findings.append(f"necessary dependency without coverage claim: {missing}")
    for entry in entries:
        if not entry.get("audit_ids"):
            findings.append(f"coverage claim without audit_ids: "
                            f"subject={entry.get('subject')}")
    if findings:
        return criterion_result("K-9", "FAIL",
                                f"{len(findings)} disposition gap(s)",
                                findings=findings)
    return criterion_result(
        "K-9", "PASS",
        f"{len(dispositions)} disposition(s) cover the audit baseline exactly "
        f"once; the {len(baseline['necessary_ids'])} necessary dependency id(s) "
        f"are all covered by a claim")


# ── K-10 ────────────────────────────────────────────────────────────────────


def k10_structural_invariants(subject: Subject, facts: ContractFacts) -> Criterion:
    """K-10 — the contract and the fixture are declared product artifacts.

    Three declarations must agree: ``package.json``'s ``files`` (shipping),
    ``core/manifest.json``'s canonical entries (audit), and the cleanup scope's
    directory set (deletion safety). ``cleanup.py``'s ``PLUGIN_SCOPE_DIRS`` is
    read as text and compared with the manifest's ``cleanup_scope.directories``
    — the equality judgment the manifest check already owns, re-asserted here
    because the contract's placement depends on it (design §2.9.2).
    """
    if not facts.ok:
        return criterion_result("K-10", "FAIL",
                                "declaration judgment needs a readable contract")
    findings: List[str] = []
    files = facts.get("own.package.files")
    contract_rel = str(dsh_contract.CONTRACT_REL)
    if not any(entry.rstrip("/") + "/" == contract_rel[:len(entry.rstrip("/")) + 1]
               or entry == contract_rel for entry in files):
        if not any(contract_rel.startswith(entry.rstrip("/") + "/")
                   for entry in files if isinstance(entry, str)):
            findings.append(f"contract not covered by `files`: {contract_rel}")
    try:
        manifest = json.loads(_read(subject.core_manifest) or "{}")
    except ValueError as error:
        findings.append(f"core manifest is not valid JSON: {error}")
        manifest = {}
    entries = (manifest.get("canonical_product_artifacts") or {}).get("entries") or []
    paths = {entry.get("path") for entry in entries}
    if contract_rel not in paths:
        findings.append(f"contract not declared in canonical_product_artifacts: "
                        f"{contract_rel}")
    fixture_paths = sorted(
        path.relative_to(subject.root).as_posix()
        for path in subject.factsheet_glob.parent.glob(subject.factsheet_glob.name))
    for fixture in fixture_paths:
        if fixture not in paths:
            findings.append(f"host-facts fixture not declared in "
                            f"canonical_product_artifacts: {fixture}")
    if len(fixture_paths) > 3:
        findings.append(f"host-facts fixture budget exceeded: "
                        f"{len(fixture_paths)} files (design §5.4: ≤3)")
    for fixture in fixture_paths:
        size = (subject.root / fixture).stat().st_size if (subject.root / fixture).is_file() else 0
        if size > 64 * 1024:
            findings.append(f"host-facts fixture over the size budget: "
                            f"{fixture} is {size} byte(s) (design §5.4: ≤64 KiB)")
    manifest_dirs = set((manifest.get("cleanup_scope") or {}).get("directories") or [])
    cleanup_text = _read(subject.cleanup_py)
    # Comments are stripped before the assignment is located: the module
    # discusses `PLUGIN_SCOPE_DIRS` in prose, and a prose mention must not be
    # mistaken for the declaration (it would compare the manifest against a
    # sentence).
    cleanup_code = re.sub(r"^[ \t]*#.*$", "", cleanup_text, flags=re.M)
    plugin_scope = None
    match = re.search(r"^PLUGIN_SCOPE_DIRS\s*=\s*[\(\{]([^\)\}]*)[\)\}]",
                      cleanup_code, re.S | re.M)
    if match:
        plugin_scope = set(re.findall(r'"([A-Za-z0-9._-]+)"', match.group(1)))
    if not plugin_scope:
        findings.append(f"cannot read PLUGIN_SCOPE_DIRS from {_rel(subject.cleanup_py)}")
    elif manifest_dirs != plugin_scope:
        findings.append(
            f"cleanup scope drift: manifest {sorted(manifest_dirs)} != "
            f"PLUGIN_SCOPE_DIRS {sorted(plugin_scope)}")
    elif "adapters" not in plugin_scope:
        findings.append("`adapters` is not in the cleanup scope — the contract's "
                        "directory is not covered")
    if findings:
        return criterion_result("K-10", "FAIL",
                                f"{len(findings)} declaration gap(s)",
                                findings=findings)
    return criterion_result(
        "K-10", "PASS",
        f"contract in `files` + canonical_product_artifacts; "
        f"{len(fixture_paths)} host-facts fixture(s) declared; cleanup scope == "
        f"PLUGIN_SCOPE_DIRS ({len(manifest_dirs)} dir(s))")


# ── K-11 ────────────────────────────────────────────────────────────────────


#: K-11 — the two declarations the ratchet is tied to. Both live **outside** the
#: contract, because a budget stored in the same file as the entries it must
#: bound could be raised in the very commit that needs it raised (R1 N-2).
#: ``ALLOWLIST_BUDGET = 0`` is DEC-192's ruling — zero exemptions, strictly
#: stronger than the design's initial budget of three.
ANCHOR_TEST_REL = (
    "skills/software-project-governance/infra/tests/test_dsh_contract.py")
CONTRACT_ALLOWLIST_ANCHOR_RE = re.compile(
    r"^ALLOWLIST_BUDGET\s*=\s*(\d+)\s*$", re.M)
ANCHOR_ENTRIES_RE = re.compile(r"^K2_ALLOWLIST\s*=\s*(\S+)\s*$", re.M)


def _ratchet_anchor(subject: Subject) -> Tuple[Optional[int], Optional[str]]:
    """The ratchet ceiling from the judging test, or ``None`` + the reason.

    Reading the constant rather than restating it keeps one number in the tree:
    lowering the budget in the test immediately lowers it here, and raising it
    requires editing the file a reviewer already reads for the entries.
    """
    path = subject.root / ANCHOR_TEST_REL
    if not path.is_file():
        return None, f"anchor file missing: {ANCHOR_TEST_REL}"
    text = _read(path)
    budget = CONTRACT_ALLOWLIST_ANCHOR_RE.search(text)
    if budget is None:
        return None, f"`ALLOWLIST_BUDGET` not declared in {ANCHOR_TEST_REL}"
    entries = ANCHOR_ENTRIES_RE.search(text)
    if entries is None:
        return None, f"`K2_ALLOWLIST` not declared in {ANCHOR_TEST_REL}"
    return int(budget.group(1)), None


def k11_allowlist_ratchet(facts: ContractFacts, subject: Subject) -> Criterion:
    """K-11 — the exemption channel is constrained (R0 BT-R-01 / DEC-192).

    Every entry carries ``literal`` + ``reason`` + ``since_slice``; the count is
    within the ratchet ceiling; the ceiling only ever goes down. Two properties
    make this a *guard* rather than a formality:

      * the ceiling is read from the judging test (outside the contract), so the
        contract cannot widen its own exemption budget;
      * an undeclared block counts as **zero entries with a ceiling of zero**, so
        adding the block later cannot silently create headroom — it must first
        raise the ceiling in the other file.
    """
    if not facts.ok:
        return criterion_result("K-11", "FAIL",
                                "allowlist judgment needs a readable contract")
    findings: List[str] = []
    budget, anchor_error = _ratchet_anchor(subject)
    if anchor_error:
        findings.append(anchor_error)
        budget = 0
    entries = facts.allowlist
    if not facts.declared_allowlist:
        # V1's contract predates the block (`own.notes.single_source_of_truth`:
        # "本文件在 V2/V8 追加该块，V1 不含"). Absent means empty — never
        # "unbounded" — which is the whole point of anchoring the ceiling
        # elsewhere.
        entries = []
    if not isinstance(entries, list):
        findings.append(f"`{CONTRACT_ALLOWLIST_PATH}` must be a list")
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            findings.append(f"allowlist entry is not an object: {entry!r}")
            continue
        literal = entry.get("literal")
        if not isinstance(literal, str) or not literal:
            findings.append(f"allowlist entry without a literal: {entry!r}")
        for field_name in ("reason", "since_slice"):
            value = entry.get(field_name)
            if not isinstance(value, str) or not value.strip():
                findings.append(f"allowlist entry without {field_name}: "
                                f"{literal!r}")
        if not entry.get("files"):
            findings.append(f"allowlist entry without files (scope): "
                            f"{literal!r}")
    if len(entries) > budget:
        findings.append(f"allowlist grew: {len(entries)} → budget {budget} "
                        f"(only down, never up)")
    if findings:
        return criterion_result("K-11", "FAIL",
                                f"{len(findings)} allowlist violation(s)",
                                findings=findings)
    return criterion_result(
        "K-11", "PASS",
        f"allowlist {len(entries)}/{budget} (ratchet: only down); ceiling "
        f"anchored in {ANCHOR_TEST_REL} — outside the contract")


# ── K-13 ────────────────────────────────────────────────────────────────────


@dataclass
class Factsheet:
    """One ``host-facts-*.json`` record, validated but not interpreted."""

    path: Path
    document: Dict[str, Any]
    findings: List[str] = field(default_factory=list)

    @property
    def captured_at(self) -> Optional[datetime]:
        return _parse_timestamp(self.document.get("captured_at"))

    @property
    def dsh_version(self) -> Optional[str]:
        value = self.document.get("dsh_version")
        return value if isinstance(value, str) and value else None

    @property
    def synthetic(self) -> bool:
        return self.document.get("synthetic") is True


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp; a naive value is read as UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


FACTSHEET_REQUIRED_FIELDS = ("captured_at", "dsh_version", "synthetic",
                             "provenance", "plane")


def load_factsheet(path: Path) -> Factsheet:
    """Read + shape-check one ``host-facts`` record (never raises)."""
    document: Dict[str, Any] = {}
    findings: List[str] = []
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        findings.append(f"{Path(path).name}: cannot read ({type(error).__name__})")
    except ValueError as error:
        findings.append(f"{Path(path).name}: not valid JSON ({error})")
    if not isinstance(document, dict):
        findings.append(f"{Path(path).name}: the document must be an object")
        document = {}
    for name in FACTSHEET_REQUIRED_FIELDS:
        if name not in document:
            findings.append(f"{Path(path).name}: missing `{name}`")
    if document and _parse_timestamp(document.get("captured_at")) is None:
        findings.append(f"{Path(path).name}: `captured_at` is not an ISO-8601 "
                        f"timestamp")
    if document and not isinstance(document.get("synthetic"), bool):
        findings.append(f"{Path(path).name}: `synthetic` must be a boolean")
    if document and not isinstance(document.get("plane"), dict):
        findings.append(f"{Path(path).name}: `plane` must be an object")
    return Factsheet(path=Path(path), document=document, findings=findings)


def rehearsal_findings(baseline: Dict[str, Any], candidate: Dict[str, Any],
                       *, ttl_days: Optional[int] = None,
                       today: Optional[date] = None) -> List[str]:
    """K-13's preconditions as a value — the guard *before* any drift is read.

    Three rules, all of which exist because a rehearsal that cannot fail is
    worse than no rehearsal (design §5.5 honesty boundary 4 / R0 BT-R-03):

      * same version on both sides → FAIL ("rehearsal no-op"): a no-op replay
        would print "no drift" and be read as "the upgrade is safe";
      * ``candidate.captured_at`` must be **strictly** later than
        ``baseline.captured_at``;
      * either record past its TTL → ``[EVIDENCE-STALE]`` and FAIL (R1 N-6
        fixed the consequence: stale evidence is a FAIL, not an advisory).
    """
    findings: List[str] = []
    base = load_factsheet_from(baseline)
    cand = load_factsheet_from(candidate)
    today = today or datetime.now(timezone.utc).date()
    if base.dsh_version and cand.dsh_version and base.dsh_version == cand.dsh_version:
        findings.append(f"rehearsal no-op: baseline and candidate are both "
                        f"{base.dsh_version}")
    if base.captured_at is None or cand.captured_at is None:
        findings.append("rehearsal baseline/candidate time order: a "
                        "`captured_at` is missing or unparsable")
    elif cand.captured_at <= base.captured_at:
        findings.append(
            f"baseline/candidate time order: candidate "
            f"{cand.captured_at.isoformat()} is not strictly later than "
            f"baseline {base.captured_at.isoformat()}")
    for label, record in (("baseline", base), ("candidate", cand)):
        if record.captured_at is None or ttl_days is None:
            continue
        age = (today - record.captured_at.date()).days
        if age > ttl_days:
            findings.append(
                f"[EVIDENCE-STALE] {label} fixture is {age} day(s) old "
                f"(ttl {ttl_days}) — re-record it before reading the rehearsal")
    return findings


def load_factsheet_from(document: Dict[str, Any]) -> Factsheet:
    """Adapt an in-memory record to :class:`Factsheet` (the rehearsal seam)."""
    findings = [f"missing `{name}`" for name in FACTSHEET_REQUIRED_FIELDS
                if name not in document]
    return Factsheet(path=Path("<memory>"), document=dict(document),
                     findings=findings)


def k13_rehearsal_baseline(subject: Subject, facts: ContractFacts,
                           *, today: Optional[date] = None) -> Criterion:
    """K-13's repository half — the recorded baseline is present and in TTL.

    The no-op and time-order rules need two records, so they belong to the
    ``--rehearse`` entry point (they are executed against an in-memory
    candidate); what can be judged of the repository alone is that the baseline
    this CI will compare against exists, is shaped correctly, and has not aged
    past the TTL — the failure mode R-11 names ("a stale baseline manufactures
    false confidence").
    """
    paths = sorted(subject.factsheet_glob.parent.glob(subject.factsheet_glob.name))
    if not paths:
        return criterion_result(
            "K-13", "FAIL",
            f"no host-facts baseline under "
            f"{_rel(subject.factsheet_glob.parent)}", 
            findings=["run `dsh-doctor --record-evidence --out "
                      "adapters/dsh/fixtures/host-facts-<dsh-version>.json` "
                      "on a real plane"])
    if not facts.ok:
        return criterion_result("K-13", "FAIL",
                                "baseline TTL judgment needs a readable contract")
    ttl_days = facts.get("evidence.verified_on_ttl_days")
    today = today or datetime.now(timezone.utc).date()
    details: List[str] = []
    findings: List[str] = []
    for path in paths:
        record = load_factsheet(path)
        findings.extend(record.findings)
        if record.captured_at is None:
            continue
        age = (today - record.captured_at.date()).days
        state = "synthetic" if record.synthetic else "recorded"
        details.append(f"{path.name}: dsh {record.dsh_version}, {state}, "
                       f"captured {record.captured_at.date().isoformat()} "
                       f"({age} day(s) old)")
        if age > ttl_days:
            findings.append(f"[EVIDENCE-STALE] {path.name} is {age} day(s) old "
                            f"(ttl {ttl_days})")
    if findings:
        return criterion_result("K-13", "FAIL",
                                f"{len(findings)} baseline problem(s)",
                                findings=findings, details=details)
    return criterion_result(
        "K-13", "PASS",
        f"{len(paths)} host-facts baseline(s) present, shaped and within the "
        f"{ttl_days}-day TTL; no-op and time-order rules are enforced by "
        f"`dsh-doctor --rehearse`",
        details=details)


# ── the judgment ────────────────────────────────────────────────────────────


def check_dsh_boundary(repo_root: Optional[Path] = None,
                       *, subject: Optional[Subject] = None,
                       today: Optional[date] = None) -> Dict[str, Any]:
    """Run every criterion and return the report dict (design §2.8).

    The report shape the rendering and the doctor consume::

        {"check": "28w", "verdict": ..., "criteria": [{id, verdict, reason,
          findings, details}, ...], "issues": [finding, ...]}

    A criterion that raises is reported as FAIL with its own message: the
    boundary check must not be silent about a judgment it could not make (C-6),
    and the failure must name the criterion so the engine's line is actionable.
    """
    subject = subject or Subject(repo_root)
    facts = ContractFacts(subject)
    runners = (
        ("K-1", lambda: k1_contract_readable(facts)),
        ("K-2", lambda: k2_no_outside_literal(subject, facts)),
        ("K-3", lambda: k3_template_rows_match_contract(subject, facts)),
        ("K-4", lambda: k4_tokens_match(subject, facts)),
        ("K-5", lambda: k5_hook_paths(facts, subject)),
        ("K-6", lambda: k6_patch_shape(subject, facts)),
        ("K-7", lambda: k7_version_evidence(facts, subject, today=today)),
        ("K-8", lambda: k8_coverage_claims(facts, subject)),
        ("K-9", lambda: k9_dispositions(facts)),
        ("K-10", lambda: k10_structural_invariants(subject, facts)),
        ("K-11", lambda: k11_allowlist_ratchet(facts, subject)),
        ("K-12", lambda: k12_single_verdict_anchor(facts)),
        ("K-13", lambda: k13_rehearsal_baseline(subject, facts, today=today)),
    )
    criteria: List[Dict[str, Any]] = []
    for ident, runner in runners:
        try:
            criteria.append(runner().as_dict())
        except Exception as error:  # a crashed criterion is still reported
            criteria.append(criterion_result(
                ident, "FAIL",
                f"criterion crashed: {type(error).__name__}: {error}",
                findings=[f"{ident}: {type(error).__name__}: {error}"]).as_dict())
    report = {
        "check": "28w",
        "contract": _rel(subject.contract_path),
        "criteria": criteria,
        "issues": [finding for entry in criteria
                   if entry["verdict"] == "FAIL"
                   for finding in (entry["findings"] or [entry["reason"]])],
    }
    report["verdict"] = verdict(report)
    return report


def k12_single_verdict_anchor(facts: ContractFacts,
                              *, guard_text: Optional[str] = None,
                              registered_commands: Optional[set] = None) -> Criterion:
    """K-12's boundary half — the coverage block has a single generation point.

    The full K-12 judgment ("the doctor's verdict equals this check's exit code
    under one repository state") needs the doctor's report and therefore lives
    in ``dsh_doctor`` (which consumes *this* function's result rather than
    recomputing it — R0 BT-R-02). What the boundary check can assert on its own
    is the other half of the rule: ``coverage`` is produced by exactly one
    place, ``check_dsh_preset_compat()``, and no consumer may re-derive it.

    ``guard_text`` / ``registered_commands`` are the negative-test seams: the
    judgment must be exercisable against a mutated guard *source string*, so no
    test ever has to write to the repository to prove it can fail.
    """
    if not facts.ok:
        return criterion_result("K-12", "FAIL",
                                "single-verdict anchor needs a readable contract")
    if guard_text is None:
        guard_path = Path(__file__).resolve().parents[1] / "dsh_compat.py"
        guard_text = _read(guard_path)
        if not guard_text:
            return criterion_result(
                "K-12", "FAIL",
                f"coverage generator missing: {_rel(guard_path)}")
    generators = re.findall(r"^def (check_dsh_preset_compat\w*)", guard_text, re.M)
    if generators != ["check_dsh_preset_compat"]:
        return criterion_result(
            "K-12", "FAIL",
            f"coverage generation point is not unique: {generators}",
            findings=["the `coverage` block must have exactly one generator"])
    projections = re.findall(r'"unreadable_compositions"', guard_text)
    if not projections:
        return criterion_result(
            "K-12", "FAIL",
            "the coverage generator does not carry "
            "`unreadable_compositions` (F-R1-06)",
            findings=["unreadable compositions would vanish from every surface "
                      "that only reads `rows_unverified`"])
    try:
        registered = (set(registered_commands)
                      if registered_commands is not None
                      else _registered_command_keys())
    except Exception as error:
        return criterion_result(
            "K-12", "FAIL",
            f"cannot resolve the doctor's dispatch key: the registry is "
            f"unreadable ({type(error).__name__}: {error})",
            findings=[str(error)])
    if DOCTOR_COMMAND_KEY not in registered:
        return criterion_result(
            "K-12", "FAIL",
            f"`{DOCTOR_COMMAND_KEY}` is not a registered command key",
            findings=[f"the K-12 comparison needs the doctor command the "
                      f"registry declares ({sorted(registered)[:4]} …)"])
    return criterion_result(
        "K-12", "PASS",
        "coverage has a single generation point "
        "(`check_dsh_preset_compat`) carrying `unreadable_compositions`; the "
        f"doctor command key `{DOCTOR_COMMAND_KEY}` is registered, so the "
        "verdict comparison has a subject")


# ── rendering ───────────────────────────────────────────────────────────────

_STATUS_GLYPH = {"PASS": "[PASS]", "FAIL": "[FAIL]", "NOT_RUN": "[NOT_RUN]"}


def emit_check_section(stream=None, *, report: Optional[Dict[str, Any]] = None,
                       repo_root: Optional[Path] = None) -> int:
    """Render the engine's ``Check 28w`` section; return the FAIL count.

    The engine keeps a one-statement wrapper: orchestration output belongs to
    the check module (R4/C-15 — the monolith's print budget does not grow).
    """
    stream = sys.stdout if stream is None else stream
    report = check_dsh_boundary(repo_root) if report is None else report
    print("\n┌─ Check 28w: DSH Dependency Boundary (FEAT-031) ──────┐", file=stream)
    print(f"│  contract: {report['contract']}", file=stream)
    for entry in report["criteria"]:
        print(f"│  {_STATUS_GLYPH[entry['verdict']]} {entry['id']}: "
              f"{entry['reason']}", file=stream)
        for finding in entry["findings"][:6]:
            print(f"│    - {finding}", file=stream)
        hidden = len(entry["findings"]) - 6
        if hidden > 0:
            print(f"│    ... and {hidden} more", file=stream)
    print(f"│  Result: {report['verdict']} — "
          f"{len(failed(report))} failing criterion(a)", file=stream)
    print("└──────────────────────────────────────────────────────┘", file=stream)
    return len(failed(report))


# ── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Thin CLI: ``--json`` for machines, ``--fail-on-issues`` for gates."""
    parser = argparse.ArgumentParser(
        description="Check 28w — the dsh dependency-boundary contract guard.")
    parser.add_argument("--json", action="store_true",
                        help="emit the report as JSON")
    parser.add_argument("--fail-on-issues", action="store_true",
                        help="exit 1 when a criterion fails")
    parser.add_argument("--project-root", default=None,
                        help="package root to judge (default: derived from this file)")
    args = parser.parse_args(argv)

    try:
        report = check_dsh_boundary(args.project_root)
    except Exception as error:  # noqa: BLE001 — the CLI must not leak a stack
        print(f"Check 28w could not run: {type(error).__name__}: {error}",
              file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        emit_check_section(report=report)
    issues = len(failed(report))
    if issues and args.fail_on_issues:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    sys.exit(main())
