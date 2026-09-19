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

M0 governed-writer contract (FEAT-049, version-plan-0.86.0 §2 批 0). The five
frozen cross-ticket faces live at the bottom of this module:

    1. operation_id      form / global scope / retry-replay / same-ID
                         different-payload refusal
    2. task states       lifecycle + legal transitions (behavior-protocol.md
                         §4.6 closure machine), UNKNOWN vs NOT_EVALUABLE
    3. error codes       closed enum + retry/manual disposition classes
    4. schema version    field, compatibility window, refuse-on-unknown
    5. writer minimal    WriterRequest / WriterResult I/O shapes + the
                         effect-based idempotency declaration

M0 freezes the cross-ticket interface, not every internal detail (arch round-3
P1-1). The frozen revision is pinned by ``infra/fixtures/m0/manifest.json``
(fixture hashes + content hashes of the contract sources this section was
derived from); batch 1 tickets (FEAT-042R/FEAT-046/FEAT-047) consume that
revision read-only. A change goes through the contract-change flow — propose →
re-baseline M0 → identify affected tickets → re-run acceptance — never by
editing shared semantics inside an implementation ticket.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping as _Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
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
    "CONTINUATION_POLICIES",
    "CheckID",
    "CheckResult",
    "CheckSpec",
    "ClockPort",
    "CommandKey",
    "ContractViolation",
    "DELIVERY_VERDICTS",
    "ERROR_CODE_DISPOSITIONS",
    "ERROR_DISPOSITIONS",
    "EVALUATION_RESULTS",
    "EVIDENCE_REF_KINDS",
    "EXECUTION_RESULTS",
    "EvidenceRef",
    "FilesystemPort",
    "Finding",
    "GitPort",
    "GovernanceStore",
    "IDEMPOTENCY_MODEL",
    "INPUT_FINGERPRINT_PATTERN",
    "LogicalRecord",
    "OPERATION_ID_PATTERN",
    "OPERATION_REPLAY_DECISIONS",
    "RecordScope",
    "REFERENCE_VALIDATION_STATES",
    "RESULT_OK",
    "REVIEW_CIRCUIT_BREAKER_ROUNDS",
    "REVIEW_OUTCOMES",
    "RUNTIME_POSTURES",
    "SEVERITIES",
    "TASK_STATES",
    "TASK_TRANSITIONS",
    "SchemaVersionWindow",
    "WriterRequest",
    "WriterResult",
    "decide_operation_replay",
    "error_disposition",
    "legal_task_transitions",
    "legacy_issue_text",
    "new_operation_id",
    "require_error_code",
    "require_input_fingerprint",
    "require_operation_id",
    "require_schema_version",
    "require_task_transition",
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


# ── M0 governed-writer contract (FEAT-049 · version-plan-0.86.0 §2 批 0) ────
#
# Sources (pinned by infra/fixtures/m0/manifest.json — batch 2.0 re-run
# detects contract-source edits by re-hashing these spans):
#   * docs/planning/0.86.0-arch-consult-round3-external.md §P1-1 — the five
#     frozen faces and the change rule;
#   * docs/planning/0.86.0-arch-consult-round2-external.md §1/§4/§5 — the
#     five-step write flow, CAS + lock split, PASS/FAIL/NOT_EVALUABLE vs
#     BLOCK/ADVISORY separation, structured-result classes;
#   * references/behavior-protocol.md M7.4 step 4.6 — the review closure
#     state machine and the round≤3 circuit breaker (C3);
#   * docs/planning/version-plan-0.86.0.md §2/§3/§4 — delivery-verdict vs
#     runtime-posture separation, 旧 CLI 遇新 schema 拒写.
#
# Everything below is declarative or pure: zero I/O, zero internal imports,
# construction fail-closed via ``ContractViolation`` — the same discipline
# the FEAT-021 shapes above follow.


def _require_positive_int(where: str, value: Any) -> int:
    # bool is an int subclass — a boolean revision is always a bug.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail(f"{where}: expected a positive int, got {value!r} "
              f"({type(value).__name__})")
    return value


# ── Face 1: operation_id ────────────────────────────────────────────────────

#: Operation id form: ``op-`` + 32 lowercase hex chars (one ``uuid4().hex``).
#: The form is frozen here; the canonical generator is :func:`new_operation_id`
#: so every writer produces the same shape from a single source.
OPERATION_ID_PATTERN = r"op-[0-9a-f]{32}"

#: Input fingerprint form: SHA-256 hex of the writer's canonical normalized
#: input (the exact canonicalization is writer-owned and MUST be stable for
#: the writer's own inputs — the fingerprint only ever needs to be comparable
#: to fingerprints of the same writer's requests).
INPUT_FINGERPRINT_PATTERN = r"[0-9a-f]{64}"

_FULL_OPERATION_ID_RE = re.compile(r"^" + OPERATION_ID_PATTERN + r"$")
_FULL_INPUT_FINGERPRINT_RE = re.compile(
    r"^" + INPUT_FINGERPRINT_PATTERN + r"$")

#: What a writer does with a retried operation id (arch round-2 §1):
#: ``execute`` — id unseen, run the operation; ``replay`` — same id AND same
#: input fingerprint → return the original result, do not re-execute;
#: ``conflict`` — same id, different payload → refuse (never execute).
OPERATION_REPLAY_DECISIONS: Tuple[str, ...] = (
    "execute", "replay", "conflict")


def require_operation_id(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if not _FULL_OPERATION_ID_RE.match(text):
        _fail(f"{where}: operation id {text!r} does not match "
              f"{OPERATION_ID_PATTERN!r} (frozen form: 'op-' + uuid4 hex, "
              f"e.g. generate via new_operation_id())")
    return text


def new_operation_id() -> str:
    """Canonical operation-id generator (single source for all writers).

    ``op-`` + ``uuid4().hex`` — the entropy comes from the stdlib RNG; L0
    stays free of I/O and of any ambient state.
    """
    return "op-" + uuid.uuid4().hex


def require_input_fingerprint(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if not _FULL_INPUT_FINGERPRINT_RE.match(text):
        _fail(f"{where}: input fingerprint {text!r} does not match "
              f"{INPUT_FINGERPRINT_PATTERN!r} (SHA-256 hex of the writer's "
              f"canonical normalized input)")
    return text


def decide_operation_replay(
    stored_fingerprint: Optional[str], request_fingerprint: Any,
) -> str:
    """Idempotency decision for a retried operation id (fail-closed).

    ``stored_fingerprint`` is the fingerprint recorded under this operation
    id (``None`` = id unseen). Same id + same fingerprint → ``replay`` (the
    original result MUST be returned, not re-executed — arch round-2 §1);
    same id + different fingerprint → ``conflict`` (refused; the caller must
    mint a new operation id, a stored result is never silently reused for a
    different payload). Malformed fingerprints are contract violations, not
    decisions.
    """
    request = require_input_fingerprint(
        "decide_operation_replay: request_fingerprint", request_fingerprint)
    if stored_fingerprint is not None:
        stored = require_input_fingerprint(
            "decide_operation_replay: stored_fingerprint",
            stored_fingerprint)
    else:
        stored = None
    if stored is None:
        return "execute"
    if stored == request:
        return "replay"
    return "conflict"


# ── Face 2: task states, legal transitions, and the semantic axes ──────────

#: Governed task lifecycle states (behavior-protocol.md M7.4 step 4.5/4.6
#: made executable; FEAT-049 task text: triaged→dev→review→approved→committed).
#: ``triaged`` = machine-recorded in change-triage; ``dev`` = 进行中; ``review``
#: = 待审查/审查中 (per-round detail is the review-round dimension, C6/C7);
#: ``approved`` = 已审查; ``completed`` = 已完成; ``committed`` = committed
#: with the task ID in the message (M7.4 step 5); ``blocked`` = escalation.
TASK_STATES: Tuple[str, ...] = (
    "triaged", "dev", "review", "approved", "completed", "committed",
    "blocked")

#: Legal transitions, frozen from behavior-protocol.md §4.6 (L516-531):
#: review→approved = T3 pass terminal; review→dev = T1 NEEDS_CHANGE rework;
#: review→blocked = T2 (round>3 circuit breaker) / T4 BLOCKED escalation;
#: blocked→dev = escalation resolved back to work; blocked→triaged = delivery
#: verdict C (撤回规划) — back to planning. ``committed`` is terminal.
TASK_TRANSITIONS = MappingProxyType({
    "triaged": ("dev", "blocked"),
    "dev": ("review", "blocked"),
    "review": ("approved", "dev", "blocked"),
    "approved": ("completed",),
    "completed": ("committed",),
    "committed": (),
    "blocked": ("dev", "triaged"),
})

#: Review verdicts (behavior-protocol.md C4: APPROVED and
#: APPROVED_WITH_NOTES-with-unresolved_blockers=0 are the only pass terminals).
REVIEW_OUTCOMES: Tuple[str, ...] = (
    "approved", "approved_with_notes", "needs_change", "blocked")

#: C3 circuit breaker: maximum re-review rounds; round > 3 still
#: NEEDS_CHANGE MUST escalate as BLOCKED (never a round-4 quiet approval).
REVIEW_CIRCUIT_BREAKER_ROUNDS = 3

#: Execution state of an external action (arch round-2 §2: 持久化清单
#: "外部动作结果不明标 UNKNOWN"). ``unknown`` = the action's RESULT is
#: unknown (e.g. push timeout) — recovery MUST check the actual world
#: state (effect-based: 查世界不信日志) before re-running it.
EXECUTION_RESULTS: Tuple[str, ...] = ("succeeded", "failed", "unknown")

#: Evaluation result of a gate/baseline (arch round-2 §4 Q-4 verbatim
#: triple). ``not_evaluable`` = the EVALUATION BASIS is invalid (baseline
#: expired / scope changed / measurer incompatible) — never silently mapped
#: to pass, never conflated with the execution-state ``unknown`` above.
EVALUATION_RESULTS: Tuple[str, ...] = ("pass", "fail", "not_evaluable")

#: Continuation policy — deliberately a SEPARATE axis from
#: ``EVALUATION_RESULTS`` (arch round-2 §4: 评估结果与继续策略分离;
#: e.g. not_evaluable + advisory for trend gates, not_evaluable + block for
#: release/safety/data-integrity gates).
CONTINUATION_POLICIES: Tuple[str, ...] = ("block", "advisory")

#: Delivery adjudication (arch round-3 P1-3, layer 1 — 互斥三选一):
#: delivered = full DoD passed; deferred = explicit move to a named later
#: milestone (never claim the original scope completed); withdrawn = back to
#: planning, no delivery promise.
DELIVERY_VERDICTS: Tuple[str, ...] = ("delivered", "deferred", "withdrawn")

#: Runtime posture (arch round-3 P1-3, layer 2 — composable with any
#: delivery verdict; a degraded posture is pre-defined and separately
#: accepted, never invented after a failure to rebrand the original goal).
RUNTIME_POSTURES: Tuple[str, ...] = (
    "enabled", "disabled", "read_only", "validated_fallback")


def legal_task_transitions(state: Any) -> Tuple[str, ...]:
    """Legal target states from ``state`` — unknown states fail closed."""
    text = _require_text("legal_task_transitions: state", state)
    if text not in TASK_STATES:
        _fail(f"legal_task_transitions: unknown task state {text!r} "
              f"(expected one of {TASK_STATES})")
    return TASK_TRANSITIONS[text]


def require_task_transition(current: Any, target: Any) -> str:
    """Fail-closed transition check — the only sanctioned state change path.

    Writers (batch 1: task-row-update) call this before persisting a task
    state change; an illegal or unknown pair raises ``ContractViolation``
    with both states named (error code ``illegal_transition``).
    """
    current_text = _require_text("require_task_transition: current", current)
    target_text = _require_text("require_task_transition: target", target)
    legal = legal_task_transitions(current_text)
    if target_text not in legal:
        _fail(f"require_task_transition: illegal transition "
              f"{current_text!r} -> {target_text!r} (legal targets from "
              f"{current_text!r}: {legal}; frozen table TASK_TRANSITIONS, "
              f"behavior-protocol.md §4.6)")
    return target_text


# ── Face 3: error codes — closed enum + disposition classes ────────────────

#: Result classes for a rejected/failed writer operation (arch round-2 §5
#: DoD item 5: 区分校验失败/冲突/可重试/需介入). ``validation`` = the input or
#: candidate state is illegal (fix the input, then retry as a NEW operation);
#: ``conflict`` = a concurrent/intent mismatch the caller must re-judge;
#: ``retryable`` = transient, the SAME operation may be retried;
#: ``manual`` = human intervention required (credential repair, projection
#: rebuild, recovery adjudication).
ERROR_DISPOSITIONS: Tuple[str, ...] = (
    "validation", "conflict", "retryable", "manual")

#: Closed error-code enum. Grounding per code: ``schema_violation`` /
#: ``cross_record_violation`` = 写前完整验证 (schema + 跨记录约束, arch
#: round-2 §5); ``illegal_transition`` = TASK_TRANSITIONS refusal;
#: ``schema_version_unsupported`` = 旧 CLI 遇新 schema 拒写 (version-plan
#: §2 M0 line); ``revision_conflict`` = CAS expected_revision mismatch
#: (arch round-2 §1 — return observed state, caller re-judges);
#: ``operation_id_conflict`` = same id, different payload; ``lock_contention``
#: = short-term store lock busy (retryable); ``manual_intervention`` = needs
#: a human (credential failure, projection-repair state).
ERROR_CODE_DISPOSITIONS = MappingProxyType({
    "schema_violation": "validation",
    "cross_record_violation": "validation",
    "illegal_transition": "validation",
    "schema_version_unsupported": "validation",
    "revision_conflict": "conflict",
    "operation_id_conflict": "conflict",
    "lock_contention": "retryable",
    "manual_intervention": "manual",
})

#: The success result code (outside the error enum — an error code class
#: would make ``code`` total over a closed set that includes success).
RESULT_OK = "ok"


def require_error_code(where: str, value: Any) -> str:
    text = _require_text(where, value)
    if text != RESULT_OK and text not in ERROR_CODE_DISPOSITIONS:
        _fail(f"{where}: unknown result code {text!r} (closed enum: "
              f"{RESULT_OK!r} + {sorted(ERROR_CODE_DISPOSITIONS)} — extend "
              f"ERROR_CODE_DISPOSITIONS deliberately, never emit ad-hoc "
              f"codes)")
    return text


def error_disposition(where: str, code: Any) -> str:
    """Disposition class of an error code — unknown codes fail closed."""
    text = _require_text(where, code)
    if text not in ERROR_CODE_DISPOSITIONS:
        _fail(f"{where}: unknown error code {text!r} (closed enum: "
              f"{sorted(ERROR_CODE_DISPOSITIONS)})")
    return ERROR_CODE_DISPOSITIONS[text]


# ── Face 4: schema version field, window, refuse-on-unknown ────────────────


def require_schema_version(where: str, value: Any) -> int:
    return _require_positive_int(where, value)


@dataclass(frozen=True)
class SchemaVersionWindow:
    """Compatibility window of one writer over one record family (face 4).

    ``minimum`` = oldest schema version this writer still writes;
    ``current`` = newest schema version this writer knows. ``supports`` is
    the frozen compatibility rule (version-plan §2 M0: 旧 CLI 遇新 schema
    拒写): anything below ``minimum`` and anything ABOVE ``current`` is
    refused — a writer never guesses at an unknown newer schema, never
    silently downgrades it, and never writes into a record it cannot fully
    interpret. Monotonic bump discipline: raising ``current`` is a
    deliberate contract change; ``minimum`` moves forward only when old
    versions are genuinely retired.
    """

    minimum: int
    current: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "minimum",
            _require_positive_int("SchemaVersionWindow.minimum", self.minimum))
        object.__setattr__(
            self, "current",
            _require_positive_int("SchemaVersionWindow.current", self.current))
        if self.current < self.minimum:
            _fail(f"SchemaVersionWindow: current {self.current} < minimum "
                  f"{self.minimum} — an empty/inverted version window is "
                  f"never valid")

    def supports(self, version: Any) -> bool:
        checked = require_schema_version(
            "SchemaVersionWindow.supports: version", version)
        return self.minimum <= checked <= self.current

    def require_supported(self, where: str, version: Any) -> int:
        checked = require_schema_version(
            f"{where}: schema_version", version)
        if not self.supports(checked):
            _fail(f"{where}: schema version {checked} outside supported "
                  f"window [{self.minimum}, {self.current}] — refuse to "
                  f"write (schema_version_unsupported); a newer-than-known "
                  f"schema MUST be rejected, never guessed or downgraded")
        return checked


# ── Face 5: writer minimal I/O + effect-based idempotency declaration ──────

#: Evidence reference kinds (arch round-2 §3 引用类型表, verbatim five).
EVIDENCE_REF_KINDS: Tuple[str, ...] = (
    "repo_file", "git_object", "governance_id", "url", "human_observation")

#: Reference resolvability (arch round-2 §3: reference_validation —
#: 可解析/不可解析/暂不可验证). Deliberately SEPARATE from any verdict: a
#: CLI reports resolvability only; whether evidence is SUFFICIENT is a
#: human/LLM verdict and never derivable from file existence.
REFERENCE_VALIDATION_STATES: Tuple[str, ...] = (
    "resolvable", "unresolvable", "not_yet_verifiable")

#: Idempotency model declaration (arch round-2 §2: 幂等必须 effect-based —
#: 查世界不信日志; resume checks actual world effects before re-running a
#: step; never trust an operation log alone to decide what already happened).
IDEMPOTENCY_MODEL = "effect_based"


@dataclass(frozen=True)
class EvidenceRef:
    """One typed evidence reference in a writer request (face 5 input).

    ``validation`` is a checker OUTPUT attached later (default ``None`` =
    not yet checked); a ``url`` ref defaults to syntax-only validation —
    never auto-fetched (arch round-2 §3/§规划缺失②: 外部 URL 默认不联网验证).
    """

    kind: str
    value: str
    validation: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "kind", _require_text("EvidenceRef.kind", self.kind))
        if self.kind not in EVIDENCE_REF_KINDS:
            _fail(f"EvidenceRef.kind: unknown evidence reference kind "
                  f"{self.kind!r} (closed enum {EVIDENCE_REF_KINDS} — arch "
                  f"round-2 §3 引用类型表)")
        object.__setattr__(
            self, "value", _require_text("EvidenceRef.value", self.value))
        if self.validation is not None:
            object.__setattr__(
                self, "validation",
                _require_text("EvidenceRef.validation", self.validation))
            if self.validation not in REFERENCE_VALIDATION_STATES:
                _fail(f"EvidenceRef.validation: unknown state "
                      f"{self.validation!r} (closed enum "
                      f"{REFERENCE_VALIDATION_STATES})")


def _require_evidence_refs(
    where: str, value: Any,
) -> Tuple[EvidenceRef, ...]:
    # A str is itself a sequence — refusing it keeps a mistyped single ref
    # from exploding into per-character entries.
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        _fail(f"{where}: expected a list/tuple of EvidenceRef, got "
              f"{type(value).__name__}")
    refs: List[EvidenceRef] = []
    for index, item in enumerate(value):
        if not isinstance(item, EvidenceRef):
            _fail(f"{where}[{index}]: expected EvidenceRef, got "
                  f"{type(item).__name__}")
        refs.append(item)
    return tuple(refs)


@dataclass(frozen=True)
class WriterRequest:
    """Minimal governed-write input (face 5; arch round-2 §1 五步).

    The submitter provides exactly: which task, the CAS expectation, the
    intended target state, the idempotency identity, the payload
    fingerprint, and typed evidence references. Everything else — locking,
    re-validation, atomic replacement — is writer-internal detail M0
    deliberately does NOT freeze (arch round-3 P1-1: 跨票接口非内部细节).
    ``expected_revision`` is the optimistic-concurrency expectation; a
    mismatch is reported as ``revision_conflict`` with the observed
    revision, never auto-rebased.
    """

    task_id: str
    expected_revision: int
    target_state: str
    operation_id: str
    input_fingerprint: str
    evidence_refs: Tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "task_id", _require_text("WriterRequest.task_id",
                                           self.task_id))
        object.__setattr__(
            self, "expected_revision",
            _require_positive_int("WriterRequest.expected_revision",
                                  self.expected_revision))
        object.__setattr__(
            self, "target_state",
            _require_text("WriterRequest.target_state", self.target_state))
        if self.target_state not in TASK_STATES:
            _fail(f"WriterRequest.target_state: unknown task state "
                  f"{self.target_state!r} (closed enum {TASK_STATES})")
        object.__setattr__(
            self, "operation_id",
            require_operation_id("WriterRequest.operation_id",
                                 self.operation_id))
        object.__setattr__(
            self, "input_fingerprint",
            require_input_fingerprint("WriterRequest.input_fingerprint",
                                      self.input_fingerprint))
        object.__setattr__(
            self, "evidence_refs",
            _require_evidence_refs("WriterRequest.evidence_refs",
                                   self.evidence_refs))


@dataclass(frozen=True)
class WriterResult:
    """Structured writer outcome (face 5 output; arch round-2 §1/§5).

    ``code`` is ``RESULT_OK`` or a closed error code; ``disposition``
    semantics: ``new_revision`` is present ONLY on success (the released
    new version per the five-step flow); ``observed_revision`` is REQUIRED
    on ``conflict`` codes (the caller re-judges against the current state —
    arch round-2 §1: CAS 冲突不自动换版本执行) and meaningless elsewhere;
    ``execution`` is the external-action state (``None`` = nothing was
    executed). ``validation``/``conflict``/``retryable`` rejections never
    execute anything; ``manual`` may follow an executed action (e.g. 源已提交
    投影待修复 — execution ``succeeded``; push timeout — execution
    ``unknown``: check the world before re-running, never blindly retry).
    """

    operation_id: str
    code: str
    new_revision: Optional[int] = None
    observed_revision: Optional[int] = None
    execution: Optional[str] = None
    detail: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "operation_id",
            require_operation_id("WriterResult.operation_id",
                                 self.operation_id))
        object.__setattr__(
            self, "code",
            require_error_code("WriterResult.code", self.code))
        if self.new_revision is not None:
            object.__setattr__(
                self, "new_revision",
                _require_positive_int("WriterResult.new_revision",
                                      self.new_revision))
        if self.observed_revision is not None:
            object.__setattr__(
                self, "observed_revision",
                _require_positive_int("WriterResult.observed_revision",
                                      self.observed_revision))
        if self.execution is not None:
            object.__setattr__(
                self, "execution",
                _require_text("WriterResult.execution", self.execution))
            if self.execution not in EXECUTION_RESULTS:
                _fail(f"WriterResult.execution: unknown execution state "
                      f"{self.execution!r} (closed enum {EXECUTION_RESULTS})")
        object.__setattr__(
            self, "detail",
            _require_optional_text("WriterResult.detail", self.detail))

        if self.code == RESULT_OK:
            if self.new_revision is None:
                _fail("WriterResult: code 'ok' requires new_revision (the "
                      "five-step flow returns 新版本+结果码)")
            if self.execution is None:
                _fail("WriterResult: code 'ok' requires execution (succeeded "
                      "— or unknown when an external action's result is "
                      "unresolved; effect-based recovery then checks the "
                      "world, never the log alone)")
            if self.execution == "failed":
                _fail("WriterResult: code 'ok' with execution 'failed' is "
                      "contradictory — report the failure code instead")
        else:
            disposition = ERROR_CODE_DISPOSITIONS[self.code]
            if self.new_revision is not None:
                _fail(f"WriterResult: error code {self.code!r} must not "
                      f"carry new_revision — a rejected/failed operation "
                      f"released no new version")
            if disposition in ("validation", "conflict", "retryable") \
                    and self.execution is not None:
                _fail(f"WriterResult: {disposition} code {self.code!r} "
                      f"executed nothing — execution must be None (a "
                      f"pre-execution rejection never ran an external "
                      f"action)")
            if disposition == "conflict":
                if self.observed_revision is None:
                    _fail(f"WriterResult: conflict code {self.code!r} "
                          f"requires observed_revision (CAS 冲突返回当前状态"
                          f"与冲突原因，由调用方重判 — arch round-2 §1)")
            elif self.observed_revision is not None:
                _fail(f"WriterResult: {disposition} code {self.code!r} must "
                      f"not carry observed_revision — it is the conflict "
                      f"channel only")
