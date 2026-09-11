"""L0 core contract — pure types, zero I/O, zero in-repo dependencies.

FEAT-021 / AUDIT-150 §3.6 (REFACTOR-contract-layer). Design §3.6 names this
layer ``L0/contract.py``; the packet lands the module at ``infra/contracts.py``
(module path is a packet-scoped decision — the layer assignment is L0).

First-batch shapes (§3.6, implemented verbatim):

    CheckID / CommandKey        frozen-list type aliases
    Finding                     frozen value object (severity/check/message/
                                file/line/extra)
    CheckResult                 mutable aggregation object, exposed as the
                                legacy dict through ``to_legacy_dict()`` (§3.7)
    CheckSpec                   registration metadata (§9.1 light registry, R5)
    GovernanceStore / FilesystemPort / GitPort / ClockPort
                                the L0 ports L2 implements; L3/L4 see only the
                                interface (§3.2 layer table)

Layer discipline (machine-judged: ArchGuard R3, evolution §4.1):

  * stdlib only, no import of any in-repo module (L0 depends on nothing);
  * zero I/O — no ``open``/``print``/filesystem/network/clock call anywhere,
    and the module body is declarations only (an import never executes a
    check body nor instantiates a service, §9.1);
  * the module cannot be a cycle source: it has no outgoing internal edge, so
    admitting it to the ratchet's ``managed_modules`` (an archguard-side,
    out-of-packet slice) can only add a clean L0 node.

Construction is fail-closed (§3.7 step 2): every illegal field raises
``ContractViolation`` — a ``ValueError`` subclass — with a message naming the
field, the expected shape and the value observed. Nothing is coerced silently.

Caliber decisions, each backed by a measurement over the current engine
(``verify_workflow.py`` + ``checks/`` + ``release/``), not by assumption:

  1. ``to_legacy_dict`` renders ``issues`` as strings. Element-type census:
     ``issues.append`` string 210 / dict 45 / other 17 — the legacy caliber is
     a human-readable line. FEAT-020's frozen class-3 signature pins only the
     ``list`` container ("element payloads are state-dependent",
     ``contract_matrix/generator.py``), so the element format is L0-owned here
     and is a documented, single-source rendering (``legacy_issue_text``).
  2. SKIP disclosure reuses the FIX-270 mechanism verbatim: the legacy detail
     block carries ``{"skipped": True, "skip_reason": <str>}``
     (``verify_workflow.py`` L7285-7297 builds it, L20613-20621 discloses it as
     ``[SKIP] <label> — <reason>``), with WARN semantics — a skip is disclosed,
     never a mis-FAIL. ``to_legacy_dict`` therefore keeps ``pass`` as given
     (a skipped result must be ``passed=True``) and adds the two disclosure
     keys inside ``details``. No top-level key is ever added (§3.7: "不加必填
     键").
  3. ``extra`` is the single documented field loss of the adapter: the legacy
     per-issue slot is a string, so check-specific detail stays on the typed
     object (and belongs in ``CheckResult.details`` for the legacy face).
  4. Tri-state ``pass``: the engine still emits ``pass: None`` for
     "couldn't run" (``verify_workflow.py`` L17340/L17372, ``checks/
     manifest.py`` L419). §3.6 declares ``passed: bool``, so the contract
     rejects ``None`` with an explicit message instead of guessing. A slice
     migrating one of those three producers MUST either map it to
     ``passed=False`` + a BLOCKING finding, disclose it as
     ``passed=True`` + ``skipped=<reason>`` (WARN), or obtain a DEC to widen
     the type — the gap is deliberate and visible, never silent.

Deferred by design (do not extend here without a deliberate contract change):
``RecordScope``/``LogicalRecord`` are minimal structural placeholders for the
port signature — the full versioned record model lands with
REFACTOR-governance-record-model (§7.2: stable id / status / time / relations /
source location); the execution context (§3.2) is a later L0 batch.
"""

from __future__ import annotations

import re
from collections.abc import Mapping as _Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NoReturn,
    Optional,
    Protocol,
    Tuple,
)

__all__ = [
    "CHECK_ID_PATTERN",
    "CheckID",
    "CheckResult",
    "CheckSpec",
    "ClockPort",
    "CommandKey",
    "ContractViolation",
    "FilesystemPort",
    "Finding",
    "GitPort",
    "GovernanceStore",
    "LogicalRecord",
    "RecordScope",
    "SEVERITIES",
    "legacy_issue_text",
]

# ── Frozen vocabulary and identifier forms (§3.5 / §3.6) ────────────────────

CheckID = str
CommandKey = str

#: Finding severity vocabulary — the engine's existing semantics (§3.5 sample A).
SEVERITIES: Tuple[str, ...] = ("BLOCKING", "WARN", "INFO")

#: Stable Check ID form: ``check-<segment>``, e.g. ``check-28p`` (§3.5 step 1).
#: Cross-checked against the FEAT-020 frozen 70-segment surface by the test
#: suite — an id form this pattern cannot express is a deliberate extension.
CHECK_ID_PATTERN = r"check-[0-9]+[a-z]?"

#: Execution modes a CheckSpec may declare (§3.6: "full" | "quick" |
#: "domain:<name>").
_MODE_PATTERN = r"(?:full|quick|domain:[A-Za-z0-9_-]+)"

#: Loader is a *module path string*, never a file path (§9.1 controlled
#: whitelist): at least one dotted segment, no separators, no ``.py`` suffix.
_DOTTED_PATH_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+"

_FULL_CHECK_ID_RE = re.compile(r"^" + CHECK_ID_PATTERN + r"$")
_FULL_MODE_RE = re.compile(r"^" + _MODE_PATTERN + r"$")
_FULL_DOTTED_PATH_RE = re.compile(r"^" + _DOTTED_PATH_PATTERN + r"$")


class ContractViolation(ValueError):
    """Illegal L0 contract construction — fail-closed (never coerced).

    Subclasses ``ValueError`` so callers that already guard value errors keep
    working, while the explicit type lets new code fail loudly.
    """


# ── Fail-closed field validation helpers ────────────────────────────────────


def _fail(message: str) -> NoReturn:
    raise ContractViolation(message)


def _require_text(where: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: expected a non-empty string, got {value!r}")
    return value


def _require_optional_text(where: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    return _require_text(where, value)


def _require_severity(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if text not in SEVERITIES:
        _fail(f"{where}: expected one of {SEVERITIES}, got {text!r}")
    return text


def _require_check_id(where: str, value: Any) -> CheckID:
    text = _require_text(where, value)
    if not _FULL_CHECK_ID_RE.match(text):
        _fail(f"{where}: check id {text!r} does not match "
              f"{CHECK_ID_PATTERN!r} (frozen segment form, e.g. 'check-28p')")
    return text


def _require_line(where: str, value: Any) -> Optional[int]:
    if value is None:
        return None
    # bool is an int subclass — a boolean line number is always a bug.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail(f"{where}: expected a positive int (1-based) or None, got "
              f"{value!r} ({type(value).__name__})")
    return value


def _require_mapping(where: str, value: Any) -> Dict[str, Any]:
    if not isinstance(value, _Mapping):
        _fail(f"{where}: expected a mapping, got {type(value).__name__}")
    return dict(value)


def _require_bool(where: str, value: Any) -> bool:
    if not isinstance(value, bool):
        tri_state = ""
        if value is None:
            tri_state = (
                " — legacy tri-state ``pass: None`` (couldn't run: "
                "verify_workflow.py L17340/L17372, checks/manifest.py L419) "
                "has no representation in the §3.6 contract; use passed=False "
                "+ a BLOCKING finding, or passed=True + skipped=<reason> "
                "(FIX-270 WARN semantics), or obtain a DEC to widen the type")
        _fail(f"{where}: expected bool, got {value!r} "
              f"({type(value).__name__}){tri_state}")
    return value


def _require_sequence(
    where: str,
    value: Any,
    *,
    unique: bool,
    allow_empty: bool,
) -> Tuple[str, ...]:
    # A str is itself a sequence — accepting it would silently explode a
    # mistyped single value into per-character entries.
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        _fail(f"{where}: expected a list/tuple of strings, got "
              f"{type(value).__name__}")
    if not allow_empty and not value:
        _fail(f"{where}: expected at least one entry, got {value!r}")
    items: List[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _fail(f"{where}[{index}]: expected a non-empty string, got "
                  f"{item!r}")
        items.append(item)
    if unique:
        duplicates = sorted({item for item in items if items.count(item) > 1})
        if duplicates:
            _fail(f"{where}: duplicate entry {duplicates[0]!r} — declared "
                  f"entries must be unique for R5 registration diffing")
    return tuple(items)


def _require_findings(where: str, value: Any) -> List[Finding]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        _fail(f"{where}: expected a list/tuple of Finding, got "
              f"{type(value).__name__}")
    findings: List[Finding] = []
    for index, item in enumerate(value):
        if not isinstance(item, Finding):
            _fail(f"{where}[{index}]: expected Finding, got "
                  f"{type(item).__name__}")
        findings.append(item)
    return findings


# ── Finding ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Finding:
    """One issue raised by one check (§3.6).

    ``extra`` stays a ``dict`` field per the design (a check-specific payload
    preserved as-is for output compatibility); it is copied on construction, so
    a frozen Finding never aliases caller-owned mutable state. Consequence: the
    generated ``__hash__`` is unusable — findings are compared by equality.
    """

    severity: str
    check: CheckID
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "severity",
            _require_severity("Finding.severity", self.severity))
        object.__setattr__(
            self, "check", _require_check_id("Finding.check", self.check))
        object.__setattr__(
            self, "message", _require_text("Finding.message", self.message))
        object.__setattr__(
            self, "file",
            _require_optional_text("Finding.file", self.file))
        object.__setattr__(
            self, "line", _require_line("Finding.line", self.line))
        object.__setattr__(
            self, "extra", _require_mapping("Finding.extra", self.extra))


# ── CheckResult ─────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Strongly typed check outcome; the legacy dict face is the adapter (§3.7).

    Not frozen by design: L4 aggregation merges findings and derives the
    topline verdict, mirroring ``result["pass"] = not result["issues"]`` in the
    engine. Construction is the fail-closed gate; post-construction mutation is
    the design's deliberate escape hatch, and ``to_legacy_dict`` re-validates
    the two fields it serializes before handing data to hooks/CI consumers.
    """

    check: CheckID
    passed: bool
    findings: List[Finding]
    skipped: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.check = _require_check_id("CheckResult.check", self.check)
        self.passed = _require_bool("CheckResult.passed", self.passed)
        self.findings = _require_findings("CheckResult.findings",
                                          self.findings)
        self.skipped = _require_optional_text("CheckResult.skipped",
                                              self.skipped)
        self.details = _require_mapping("CheckResult.details", self.details)
        if self.skipped is not None and self.passed is not True:
            _fail(f"CheckResult: skipped={self.skipped!r} requires passed=True "
                  f"(FIX-270 WARN semantics: an intentional skip is disclosed, "
                  f"never a mis-FAIL) — drop skipped to record a failure")

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Result dict compatibility face (§3.7 / §8.1 class 3).

        Key set is exactly ``pass`` / ``issues`` / ``details`` — unchanged
        spelling, no added or removed top-level key. ``details`` is a fresh
        copy per call (callers cannot corrupt the typed object), and a recorded
        skip is disclosed inside it with the FIX-270 ``skipped``/``skip_reason``
        pair.
        """
        where = "CheckResult.to_legacy_dict"
        passed = _require_bool(f"{where}: passed", self.passed)
        findings = _require_findings(f"{where}: findings", self.findings)
        details = _require_mapping(f"{where}: details", self.details)
        legacy: Dict[str, Any] = {
            "pass": passed,
            "issues": [legacy_issue_text(finding) for finding in findings],
            "details": details,
        }
        if self.skipped is not None:
            details["skipped"] = True
            details["skip_reason"] = self.skipped
        return legacy


def legacy_issue_text(finding: Finding) -> str:
    """Render one Finding to the legacy issue-string caliber.

    Single source for the L0→legacy line form
    ``[<SEVERITY>] <check-id>: <message>[ (<file>[:<line>])]``. Severity is
    carried in the text because the legacy dict has no per-issue severity
    slot; ``extra`` has no legacy slot at all and stays on the typed object.
    """
    if not isinstance(finding, Finding):
        _fail(f"legacy_issue_text: expected Finding, got "
              f"{type(finding).__name__}")
    location = ""
    if finding.file is not None:
        location = (f" ({finding.file}:{finding.line})"
                    if finding.line is not None else f" ({finding.file})")
    return (f"[{finding.severity}] {finding.check}: "
            f"{finding.message}{location}")


# ── CheckSpec ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CheckSpec:
    """Registration metadata for one independently dispatchable check (§3.6).

    Lightweight by design: a module-path string, never an imported callable —
    importing the check body at registry load is forbidden (§9.1), and R5
    asserts the path resolves inside the controlled whitelist.
    """

    check_id: CheckID
    domain: str
    loader: str
    input_deps: Tuple[str, ...]
    severity_floor: str
    modes: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "check_id",
            _require_check_id("CheckSpec.check_id", self.check_id))
        object.__setattr__(
            self, "domain", _require_text("CheckSpec.domain", self.domain))
        object.__setattr__(
            self, "loader", _require_loader("CheckSpec.loader", self.loader))
        object.__setattr__(
            self, "input_deps",
            _require_sequence("CheckSpec.input_deps", self.input_deps,
                              unique=True, allow_empty=True))
        object.__setattr__(
            self, "severity_floor",
            _require_severity("CheckSpec.severity_floor", self.severity_floor))
        object.__setattr__(
            self, "modes",
            _require_sequence("CheckSpec.modes", self.modes,
                              unique=True, allow_empty=False))
        for index, mode in enumerate(self.modes):
            if not _FULL_MODE_RE.match(mode):
                _fail(f"CheckSpec.modes[{index}]: expected {_MODE_PATTERN!r} "
                      f"(\"full\" | \"quick\" | \"domain:<name>\"), got "
                      f"{mode!r}")


def _require_loader(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if (text.endswith(".py") or "/" in text or "\\" in text or ":" in text
            or not _FULL_DOTTED_PATH_RE.match(text)):
        _fail(f"{where}: expected a dotted module path (no file extension, no "
              f"path separators, no root-level name — §9.1 whitelist loader), "
              f"got {text!r}")
    return text


# ── Ports (L2 implements; L3/L4 only see the interface, §3.2) ───────────────


class RecordScope(Protocol):
    """Which L1 record sources a store read covers (§3.6 store comment).

    Minimal structural placeholder: the full versioned record model (schema,
    relations, tolerant-cycle typing) lands with
    REFACTOR-governance-record-model (§7.2).
    """

    sources: Tuple[str, ...]


class LogicalRecord(Protocol):
    """Structural view of one logical governance record (§7.2 field list)."""

    id: str
    status: str
    time: str
    relations: Tuple[str, ...]
    source_path: str
    source_line: Optional[int]


class GovernanceStore(Protocol):
    """Read access to plan-tracker / evidence / decision / risk + archive."""

    def read_records(self, scope: RecordScope) -> Iterable[LogicalRecord]:
        ...


class FilesystemPort(Protocol):
    """Read-only tree/file access; implementations MUST decode UTF-8
    (FIX-278 G4/F) so Windows checkouts cannot produce mojibake."""

    def read_text(self, path: str) -> str:
        ...

    def list_files(self, root: str) -> Iterable[str]:
        ...


class GitPort(Protocol):
    """Git read surface: status / show / tag / rev-parse (§3.6)."""

    def status(self) -> str:
        ...

    def show(self, rev: str) -> str:
        ...

    def tag(self) -> Iterable[str]:
        ...

    def rev_parse(self, rev: str) -> str:
        ...


class ClockPort(Protocol):
    """Injectable clock — deterministic tests, no ambient ``now()`` (§3.6).

    The implementation owns the zone policy; L0 only fixes the seam.
    """

    def now(self) -> datetime:
        ...
