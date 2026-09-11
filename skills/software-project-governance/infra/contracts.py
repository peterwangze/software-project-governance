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

  1. ``to_legacy_dict`` renders ``issues`` as strings — the caliber of the
     **string element face**, not of every face. Element-type census:
     ``issues.append`` string 210 / dict 45 / other 17, and the dict face has
     live structured consumers — ``verify_workflow.py`` L14824-14838 branches
     on ``issue["type"]``/``issue["detail"]``, L22439 reads
     ``issue.get("type")``, ``checks/review_domain.py`` L213-221 emits 7-key
     dicts, and ``tests/test_verify_workflow.py`` L9364 pins ``issue["type"]``.
     A ``dict``-element slice MUST therefore decide its own element caliber and
     pin the element shape in a §8.1 class-3 golden sample: FEAT-020 froze only
     the ``list`` container ("element payloads are state-dependent",
     ``contract_matrix/generator.py``), so the differential gate alone passes
     silently while those consumers break. The string rendering is
     single-source (``legacy_issue_text``).
  2. SKIP disclosure reuses the FIX-270 key pair and WARN semantics — a skip is
     disclosed, never a mis-FAIL (``verify_workflow.py`` L7285-7297 builds
     ``{"pass", "skipped", "skip_reason"}``, L20613-20621 renders
     ``[SKIP] <label> — <reason>``). Placement is *not* verbatim: the engine
     reads the pair at the label block's own top level
     (``details[label].get("skipped")``), whereas the adapter emits the §3.7
     Result dict whose pair sits inside ``details`` — one nesting level deeper.
     The aggregation convention for a slice wiring ``CheckResult`` into that
     consumer is therefore explicit: promote the two keys to the label block
     (pinned by
     ``test_adapter_output_is_the_level_a_result_dict_not_a_label_block``).
     ``to_legacy_dict`` keeps ``pass`` as given (a skipped result must be
     ``passed=True``) and never adds a top-level key (§3.7: "不加必填键").
     The pair is adapter-owned: a recorded skip overwrites it in ``details``,
     and a caller-supplied pair with no recorded skip is refused (NF-1), so
     the ``details`` channel cannot re-introduce the FAIL-disclosed-as-SKIP
     face that the ``skipped`` field invariant already rejects.
  3. ``extra`` has no slot in the string rendering — the legacy per-issue slot
     is a string, so check-specific detail stays on the typed object (and
     belongs in ``CheckResult.details`` for the legacy face). Scoped: this is a
     property of the string element face; a dict-element slice decides its own
     payload mapping (see 1).
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

#: Loader is a *dotted path string*, never a file path (§9.1 controlled
#: whitelist): ``<module>`` or ``<module>.<attribute>`` — a check entry point
#: may be a module-level callable (as in the engine), so both forms are
#: admitted; at least one dotted segment, no separators, no ``.py`` suffix, no
#: root-level name. Consumers resolve it by importing the module prefix and
#: ``getattr``-ing the trailing attribute.
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


def _require_skip_consistent(
    where: str, passed: Any, skipped: Optional[str],
) -> None:
    """The FIX-270 WARN invariant: a disclosed skip is never a FAIL.

    Shared by construction (``CheckResult.__post_init__``) and by the legacy
    adapter (``to_legacy_dict``) — post-construction mutation is the design's
    escape hatch, so both entry points must reject a contradictory payload.
    """
    if skipped is not None and passed is not True:
        _fail(f"{where}: skipped={skipped!r} requires passed=True "
              f"(FIX-270 WARN semantics: an intentional skip is disclosed, "
              f"never a mis-FAIL) — drop skipped to record a failure")


#: The FIX-270 disclosure pair, written by ``to_legacy_dict`` itself. Reserved:
#: a caller-supplied pair in ``details`` is a claim the typed object cannot
#: back, so the adapter refuses it (NF-1) instead of forwarding a contradictory
#: legacy face.
_LEGACY_DISCLOSURE_KEYS: Tuple[str, ...] = ("skipped", "skip_reason")


def _require_no_reserved_disclosure_keys(
    where: str, details: Dict[str, Any], skipped: Optional[str],
) -> None:
    """Reserved-key enforcement on the ``details`` channel (NF-1).

    ``skipped`` set: the adapter overwrites both keys from the typed object
    (the pre-existing FIX-270 normalization caliber). ``skipped`` unset: a
    pair carried by ``details`` would be forwarded verbatim, so a FAIL
    (``passed=False`` + ``details["skipped"]=True``) could reach the engine's
    label-block reader and be disclosed as ``[SKIP]`` — a failure hidden
    behind a skip disclosure, the exact inversion of FIX-270's WARN semantics.
    Rejecting keeps the contract fail-closed and says nothing about the
    caller's other ``details`` entries, which stay free-form.
    """
    if skipped is not None:
        return
    carried = [key for key in _LEGACY_DISCLOSURE_KEYS if key in details]
    if carried:
        _fail(f"{where}: details carries the adapter-owned disclosure key(s) "
              f"{carried} while skipped is None — to_legacy_dict writes these "
              f"keys itself, and a stale pair on a passing/failing result "
              f"would be read as SKIP (FIX-270 WARN semantics inverted); set "
              f"CheckResult.skipped to disclose a skip, or drop the keys from "
              f"details")


# ── Finding ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Finding:
    """One issue raised by one check (§3.6).

    ``extra`` stays a ``dict`` field per the design (a check-specific payload
    preserved as-is for output compatibility); it is copied on construction,
    as a **top-level shallow copy** — ``dict(value)``, never ``deepcopy``: the
    caller's container is not aliased, but nested mutable values remain shared
    with the caller (pinned by ``test_extra_copy_is_top_level_only``), so
    "frozen" here means the attribute cannot be rebound, not that the object
    deep-isolates its innards. Consequence: the generated ``__hash__`` is
    unusable — findings are compared by equality.
    """

    severity: str
    check: CheckID
    message: str
    #: Repo-root-relative path per §3.6 — L0 does not validate relativeness
    #: (no root knowledge in this layer); parsers/renderers own resolution.
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
    every field it serializes — ``passed``/``findings``/``skipped``/``details``,
    the skip invariant, and the adapter-owned disclosure keys inside
    ``details`` — before handing data to hooks/CI consumers.
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
        _require_skip_consistent("CheckResult", self.passed, self.skipped)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Result dict compatibility face (§3.7 / §8.1 class 3).

        Key set is exactly ``pass`` / ``issues`` / ``details`` — unchanged
        spelling, no added or removed top-level key. ``details`` is a fresh
        **top-level shallow copy** per call: callers cannot corrupt the typed
        object's mapping, while nested values stay shared with it
        (``test_details_copy_is_top_level_only`` pins that caliber). A recorded
        skip is disclosed inside ``details`` with the FIX-270
        ``skipped``/``skip_reason`` pair — the level-A placement; the engine's
        label-block reader is one level shallower, see the module docstring
        caliber 2.

        Re-validation covers everything this method serializes: ``passed``,
        ``findings``, ``skipped`` and ``details`` are re-checked (and the skip
        invariant re-asserted) because post-construction mutation is the
        documented escape hatch and hooks/CI derive exit codes from this dict.
        The FIX-270 pair inside ``details`` is adapter-owned: a recorded skip
        overwrites it from the typed object, and a caller-supplied pair with no
        recorded skip is refused rather than forwarded (NF-1) — otherwise the
        ``details`` channel would keep producing the contradictory
        ``pass=False`` + ``details["skipped"]=True`` face the attribute-level
        invariant already rejects.
        """
        where = "CheckResult.to_legacy_dict"
        passed = _require_bool(f"{where}: passed", self.passed)
        findings = _require_findings(f"{where}: findings", self.findings)
        skipped = _require_optional_text(f"{where}: skipped", self.skipped)
        details = _require_mapping(f"{where}: details", self.details)
        _require_skip_consistent(where, passed, skipped)
        _require_no_reserved_disclosure_keys(where, details, skipped)
        legacy: Dict[str, Any] = {
            "pass": passed,
            "issues": [legacy_issue_text(finding) for finding in findings],
            "details": details,
        }
        if skipped is not None:
            details["skipped"] = True
            details["skip_reason"] = skipped
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

    Lightweight by design: a dotted path string — ``<module>`` or
    ``<module>.<attribute>``, i.e. also a module-level handler callable — never
    an imported callable, since importing the check body at registry load is
    forbidden (§9.1); R5 asserts the path resolves inside the controlled
    whitelist, resolving the module prefix by import and the trailing attribute
    by ``getattr``.
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
                              allow_empty=True))
        object.__setattr__(
            self, "severity_floor",
            _require_severity("CheckSpec.severity_floor", self.severity_floor))
        object.__setattr__(
            self, "modes",
            _require_sequence("CheckSpec.modes", self.modes,
                              allow_empty=False))
        for index, mode in enumerate(self.modes):
            if not _FULL_MODE_RE.match(mode):
                _fail(f"CheckSpec.modes[{index}]: expected {_MODE_PATTERN!r} "
                      f"(\"full\" | \"quick\" | \"domain:<name>\"), got "
                      f"{mode!r}")


def _require_loader(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if (text.endswith(".py") or "/" in text or "\\" in text or ":" in text
            or not _FULL_DOTTED_PATH_RE.match(text)):
        _fail(f"{where}: expected a dotted module/handler path (no file "
              f"extension, no path separators, no root-level name — §9.1 "
              f"whitelist loader; 'module' or 'module.attribute'), got "
              f"{text!r}")
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
