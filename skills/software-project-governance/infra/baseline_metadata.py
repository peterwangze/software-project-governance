"""FEAT-047 — BaselineMetadata provenance (version-plan-0.86.0 §2 批 1).

The institutional fix for Q-4/W-3 (FEAT-041 pilot-gate incident, EVD-1099/
1100): every numeric gate carries provenance, and an evaluation whose basis
is invalid is ``not_evaluable`` — never silently mapped to pass, never
conflated with a user failure. Sources consumed read-only:

  * arch round-2 §4 (门禁参数数据化): the seven provenance 要素; the
    PASS/FAIL/NOT_EVALUABLE vs BLOCK/ADVISORY axis split; deterministic
    contradictions are gate-configuration errors, not user failures;
  * contracts.py M0 faces (FEAT-049, consumed read-only):
    ``EVALUATION_RESULTS`` (pass/fail/not_evaluable) and
    ``CONTINUATION_POLICIES`` (block/advisory) are the two frozen axes;
  * version-plan-0.86.0 §3: the three-dimension acceptance caliber — a
    number without a trustworthy baseline is NOT_EVALUABLE, never claimed;
  * EVD-1104: the stock registration's measurement facts (injection-budget
    6,000 gate, baseline 4,216 / 5,694 / 5,966, measured 2026-09-19).

Provenance schema — the seven 要素 (arch round-2 §4) mapped onto the 14
required fields (``BaselineMetadata``):

    测量时间            -> measured_at
    测量器版本          -> instrument_version
    来源命令            -> measurement_command
    测量对象 commit/摘要 -> target_commit_digest
    范围/分子/分母/排除  -> scope + numerator + denominator + exclusions
    阈值依据            -> threshold_basis
    有效期失效条件      -> expiry_condition (+ optional max_age_days)

plus the identity and payload faces: ``gate_id`` (registry key), ``value``
(the measured number), ``unit``, and ``source_evd`` (evidence anchor).

Storage: ``.governance/baselines.json`` is the CLI's only write target.
Schema version 1; canonical sorted-key JSON, explicit UTF-8 (FIX-278
caliber), same-directory temp file + ``os.replace`` (atomic on Windows and
POSIX), write-after-read self-check against the same schema (DoD 3/4 — a
second schema definition is forbidden). A tampered caliber whose stored
``scope_digest`` no longer matches the derived fingerprint is refused, never
compared. Re-registering the same gate with different metadata is a
``BaselineConflict`` — this slice has no overwrite; retirement of a
superseded baseline is a deliberate future flow, not a silent clobber.
Single-writer constraint (P2-2, review-FEAT-047-CODE-R0): the register path
is safe for ONE writer at a time (Coordinator practice); the load→replace
window has no cross-process lock, so concurrent registers of different
gates could lose one side — multi-writer locking is the FEAT-046
governance_store lock face and lands with the batch-2.0 integration
(concurrency negative-controls ride that ticket).

Evaluation (``evaluate``) — fail-closed chain, each step a closed-vocabulary
diagnostic:

    1. gate configuration contradictions (deterministic): a non-finite
       threshold, or an upper-bound threshold BELOW the caliber's frozen
       floor (the EVD-1100 "85% 数学不可达" shape: ≤414 demanded, floor 720)
       -> ``gate_configuration_error`` — a gate defect, never a user failure,
       and never an automatic threshold adjustment; a floor supplied with a
       lower-bound gate is refused at the entrance (P2-3);
    2. baseline presence -> ``baseline_missing``;
    3. required-observation layering (P1-1): with a baseline present, the
       comparison-side caliber (``observed_unit``/``observed_scope_digest``)
       is REQUIRED — omitting either is a caller bug (``ContractViolation``),
       never a silent skip of the caliber match;
    4. expiry (评估基础失效 -> NOT_EVALUABLE): instrument version changed ->
       ``instrument_changed``; target digest changed -> ``target_changed``
       (the SHA-change event the stock row's expiry_condition names); a
       ``max_age_days``-based age past the measurement date ->
       ``baseline_expired``. When the expiry is EVENT-based
       (``max_age_days`` absent) a missing instrument/target observation is
       fail-visible: ``instrument_missing`` / ``target_missing`` -> NOT_
       EVALUABLE (degraded, never "check skipped");
    5. caliber match (新鲜但口径不同的数字同样不能比较): unit or scope
       fingerprint differs -> ``caliber_mismatch`` — never a pass;
    6. only a fresh, matching caliber reaches the threshold comparison ->
       ``pass`` / ``fail`` (``objective_missed``).

The continuation axis is orthogonal to the evaluation axis and derives from
``policy_class`` alone: release/safety/data_integrity gates are ``block``
(not_evaluable/fail waits for re-measurement or an explicitly authorized
waiver); trend/pilot gates are ``advisory`` with a re-measure action item.
A ``pass`` never blocks; a ``fail`` on an advisory gate still only advises.
Waiver mechanism: deliberately OUT of this ticket's scope (P3-1 合规留白) —
the ``action`` texts point at it, and arch round-2 §4 fixes its shape when
it lands: a waiver carries 范围/理由/授权/失效条件 (scope, reason, authorizer,
expiry) — four required elements, none optional, never an implicit pass.

Registry wiring (composition root): handlers ``cmd_baseline_register`` /
``cmd_baseline_evaluate`` follow the engine's ``cmd_*`` dispatch convention
(governance_cost / bootstrap_aggregate pattern: self-contained module, the
engine wires dispatch). This slice's frozen file face is this module + its
tests — the two ``LOADER_WHITELIST``/``_COMMANDS`` declaration lines and the
engine dispatch entries are the batch-1 integration point and are
deliberately NOT touched here (parallel-ticket file-face freeze, version-plan
§2: 批 1 文件面不相交). Until wired, invoke the self-contained CLI:

    python baseline_metadata.py baseline-register --gate <id> ... [--dry-run]
    python baseline_metadata.py baseline-evaluate --gate <id> --policy-class <pc> ...

Exit codes (pinned face): evaluate pass=0, fail=1, not_evaluable=2; both
subcommands exit 0 on success (registered/replay/dry-run) and 3 on any
usage/storage/contract error — a gate verdict must never be confusable with
a command crash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from contracts import (  # L0 — consumed read-only, never redefined
    CONTINUATION_POLICIES,
    EVALUATION_RESULTS,
    ContractViolation,
)

__all__ = [
    "ADVISORY_POLICY_CLASSES",
    "BASELINE_FIELDS",
    "BLOCKING_POLICY_CLASSES",
    "BaselineConflict",
    "BaselineMetadata",
    "BaselineMetadataError",
    "DIRECTIONS",
    "DIAGNOSTIC_KINDS",
    "Diagnostic",
    "EvaluationOutcome",
    "POLICY_CLASSES",
    "REGISTRY_FILENAME",
    "REGISTRY_SCHEMA_VERSION",
    "RegisterResult",
    "RegistrySchemaError",
    "caliber_digest",
    "cmd_baseline_evaluate",
    "cmd_baseline_register",
    "continuation_for",
    "evaluate",
    "load_registry",
    "main",
    "register",
]


# ── vocabulary (closed enums — unknown values fail closed) ──────────────────

REGISTRY_FILENAME = ".governance/baselines.json"
"""Default registry path (repo-root relative) — the CLI's only write target."""

REGISTRY_SCHEMA_VERSION = 1
"""Storage schema version; readers refuse any other version (M0 face 4:
旧读器遇新 schema 拒读 — never guess, never silently downgrade)."""

BASELINE_FIELDS = (
    "gate_id", "value", "unit", "measured_at", "measurement_command",
    "instrument_version", "target_commit_digest", "scope", "numerator",
    "denominator", "exclusions", "threshold_basis", "expiry_condition",
    "source_evd",
)
"""The 14 required provenance fields — the seven arch round-2 §4 要素 plus
identity (gate_id), payload (value, unit) and evidence anchor (source_evd)."""

POLICY_CLASSES = ("release", "safety", "data_integrity", "trend", "pilot")
"""Gate classes. The first three guard releases/safety/data integrity — a
non-pass verdict there blocks continuation; trend/pilot gates advise."""

BLOCKING_POLICY_CLASSES = ("release", "safety", "data_integrity")
ADVISORY_POLICY_CLASSES = ("trend", "pilot")

DIRECTIONS = ("upper", "lower")
"""Threshold semantics: ``upper`` = the observed value must not exceed the
threshold (budget/capital gates); ``lower`` = it must not fall below it."""

DIAGNOSTIC_KINDS = (
    "ok",
    "baseline_missing",
    "baseline_expired",
    "instrument_changed",
    "instrument_missing",
    "target_changed",
    "target_missing",
    "caliber_mismatch",
    "gate_configuration_error",
    "objective_missed",
)

_GATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{7,64}$")


class BaselineMetadataError(ValueError):
    """Baseline registry defect — fail-closed, never swallowed."""


class RegistrySchemaError(BaselineMetadataError):
    """The registry's schema version is unknown — refuse, never downgrade."""


class BaselineConflict(BaselineMetadataError):
    """Same gate_id, different metadata — retirement is a deliberate flow."""


def _finite_number(where: str, value: Any) -> float:
    # bool is an int subclass — a boolean measurement is always a bug; NaN
    # and infinities are not measurements either (DoD 0: untrusted input).
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise ContractViolation(
            f"{where}: expected a finite number, got {value!r} "
            f"({type(value).__name__})")
    return float(value)


def _non_empty_text(where: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(
            f"{where}: expected a non-empty string, got {value!r}")
    return value


def _parse_timestamp(where: str, value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractViolation(
            f"{where}: expected an ISO-8601 date or datetime, got "
            f"{value!r} ({exc})") from exc


def _as_naive(value: datetime) -> datetime:
    """Project an aware datetime to naive UTC so mixed comparisons cannot
    raise; naive inputs pass through untouched."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


# ── BaselineMetadata ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BaselineMetadata:
    """Provenance-carrying baseline of one numeric gate (七要素, §4 round-2).

    Construction is the fail-closed gate: every field is validated, and a
    metadata missing any of the 14 required fields is a ``ContractViolation``
    — a number without provenance is not registrable, which is exactly the
    W-3 failure mode this mechanism exists to prevent.
    """

    gate_id: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    measured_at: Optional[str] = None
    measurement_command: Optional[str] = None
    instrument_version: Optional[str] = None
    target_commit_digest: Optional[str] = None
    scope: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    exclusions: Optional[str] = None
    threshold_basis: Optional[str] = None
    expiry_condition: Optional[str] = None
    source_evd: Optional[str] = None
    max_age_days: Optional[float] = None

    def __post_init__(self) -> None:
        # Required fields default to None on purpose: a MISSING element and
        # an explicitly-None element take the same fail-closed validation
        # path (dataclass TypeError is never the disclosure channel).
        for field in BASELINE_FIELDS:
            value = getattr(self, field)
            if value is None:
                raise ContractViolation(
                    f"BaselineMetadata.{field}: required provenance element "
                    f"missing — a baseline without its seven elements is "
                    f"not registrable (arch round-2 §4)")
        object.__setattr__(
            self, "gate_id", _non_empty_text("BaselineMetadata.gate_id",
                                             self.gate_id))
        if not _GATE_ID_RE.match(self.gate_id):
            raise ContractViolation(
                f"BaselineMetadata.gate_id: {self.gate_id!r} does not match "
                f"^[A-Za-z0-9][A-Za-z0-9._:-]*$ (registry key form — no "
                f"whitespace, no path separators)")
        object.__setattr__(
            self, "value", _finite_number("BaselineMetadata.value", self.value))
        for field in ("unit", "measurement_command", "instrument_version",
                      "scope", "numerator", "denominator", "exclusions",
                      "threshold_basis", "expiry_condition", "source_evd"):
            object.__setattr__(
                self, field,
                _non_empty_text(f"BaselineMetadata.{field}", getattr(self,
                                                                     field)))
        object.__setattr__(
            self, "measured_at",
            _non_empty_text("BaselineMetadata.measured_at", self.measured_at))
        _parse_timestamp("BaselineMetadata.measured_at", self.measured_at)
        object.__setattr__(
            self, "target_commit_digest",
            _non_empty_text("BaselineMetadata.target_commit_digest",
                            self.target_commit_digest))
        if not _DIGEST_RE.match(self.target_commit_digest):
            raise ContractViolation(
                f"BaselineMetadata.target_commit_digest: "
                f"{self.target_commit_digest!r} is not a git digest form "
                f"(7..64 lowercase hex)")
        if self.max_age_days is not None:
            age = _finite_number("BaselineMetadata.max_age_days",
                                 self.max_age_days)
            if age <= 0:
                raise ContractViolation(
                    f"BaselineMetadata.max_age_days: expected a positive "
                    f"number of days, got {age}")
            object.__setattr__(self, "max_age_days", age)

    # ── storage face (single schema: readers rebuild through __init__) ────

    def to_storage_dict(self) -> Dict[str, Any]:
        """Canonical storage row: the 14 fields + max_age_days + the derived
        scope fingerprint. ``sort_keys`` at serialization keeps the JSON
        diff-stable (评审可读性契约)."""
        row: Dict[str, Any] = {field: getattr(self, field)
                               for field in BASELINE_FIELDS}
        row["max_age_days"] = self.max_age_days
        row["scope_digest"] = self.scope_digest()
        return row

    @classmethod
    def from_storage_row(cls, row: Any) -> "BaselineMetadata":
        """Rebuild from a stored row through the same constructor — the
        read path shares the write path's schema (DoD 4: no second schema)."""
        if not isinstance(row, dict):
            raise BaselineMetadataError(
                f"baseline row: expected a JSON object, got "
                f"{type(row).__name__}")
        known = set(BASELINE_FIELDS) | {"max_age_days", "scope_digest"}
        unknown = sorted(set(row) - known)
        if unknown:
            raise BaselineMetadataError(
                f"baseline row: unknown field(s) {unknown} — the registry "
                f"schema is stricter than hand edits (schema_version "
                f"{REGISTRY_SCHEMA_VERSION})")
        kwargs = {field: row.get(field) for field in BASELINE_FIELDS}
        kwargs["max_age_days"] = row.get("max_age_days")
        meta = cls(**kwargs)  # raises ContractViolation on any hole
        stored = row.get("scope_digest")
        if stored != meta.scope_digest():
            raise BaselineMetadataError(
                f"baseline {meta.gate_id!r}: stored scope_digest "
                f"{stored!r} != derived {meta.scope_digest()!r} — the "
                f"registry row was edited outside baseline-register "
                f"(write-after-read self-check refused)")
        return meta

    def scope_digest(self) -> str:
        """Fingerprint of the measurement caliber (unit + 分子/分母/排除).

        The comparison anchor for arch round-2 §4's 新鲜但口径不同 rule:
        an observation whose fingerprint differs is never comparable.
        """
        return caliber_digest(self.unit, self.numerator, self.denominator,
                              self.exclusions)


def caliber_digest(unit: str, numerator: str, denominator: str,
                   exclusions: str) -> str:
    """SHA-256 of the canonical caliber tuple — both registration and
    evaluation sides derive it through this single function."""
    payload = json.dumps(
        {"unit": unit, "numerator": numerator, "denominator": denominator,
         "exclusions": exclusions},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def continuation_for(policy_class: str) -> str:
    """The BLOCK/ADVISORY continuation axis for a gate class (arch round-2
    §4: 评估结果与继续策略分离 — orthogonal to the evaluation result)."""
    text = _non_empty_text("continuation_for: policy_class", policy_class)
    if text not in POLICY_CLASSES:
        raise ContractViolation(
            f"continuation_for: unknown policy class {text!r} (closed enum "
            f"{POLICY_CLASSES})")
    return "block" if text in BLOCKING_POLICY_CLASSES else "advisory"


# ── evaluation outcome ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Diagnostic:
    """One closed-vocabulary evaluation diagnostic."""

    kind: str
    message: str
    action: str

    def __post_init__(self) -> None:
        if self.kind not in DIAGNOSTIC_KINDS:
            raise ContractViolation(
                f"Diagnostic.kind: unknown kind {self.kind!r} (closed enum "
                f"{DIAGNOSTIC_KINDS})")
        object.__setattr__(
            self, "message", _non_empty_text("Diagnostic.message",
                                             self.message))
        object.__setattr__(
            self, "action", _non_empty_text("Diagnostic.action", self.action))

    def to_dict(self) -> Dict[str, str]:
        return {"kind": self.kind, "message": self.message,
                "action": self.action}


@dataclass(frozen=True)
class EvaluationOutcome:
    """The two frozen axes plus the diagnostic (arch round-2 §4).

    ``evaluation`` ∈ EVALUATION_RESULTS (pass/fail/not_evaluable);
    ``continuation`` ∈ CONTINUATION_POLICIES (block/advisory) — derived from
    ``policy_class`` alone, never from the evaluation result, so a trend
    gate's fail stays advisory and a release gate's pass still reports the
    blocking posture of its class.
    """

    gate_id: str
    policy_class: str
    evaluation: str
    continuation: str
    diagnostic: Diagnostic

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "gate_id", _non_empty_text("EvaluationOutcome.gate_id",
                                             self.gate_id))
        if self.evaluation not in EVALUATION_RESULTS:
            raise ContractViolation(
                f"EvaluationOutcome.evaluation: {self.evaluation!r} outside "
                f"the frozen axis {EVALUATION_RESULTS}")
        if self.continuation not in CONTINUATION_POLICIES:
            raise ContractViolation(
                f"EvaluationOutcome.continuation: {self.continuation!r} "
                f"outside the frozen axis {CONTINUATION_POLICIES}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "policy_class": self.policy_class,
            "evaluation": self.evaluation,
            "continuation": self.continuation,
            "diagnostic": self.diagnostic.to_dict(),
        }


# ── registry storage (the CLI's only write path) ────────────────────────────


def _canonical_registry_bytes(payload: Dict[str, Any]) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def _row_digest(row: Dict[str, Any]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_registry(registry_path) -> Dict[str, Any]:
    """Read the baseline registry (fail-closed on every defect).

    A missing file reads as an empty v1 registry (registration creates it);
    anything present must be valid UTF-8 JSON at schema version 1 with rows
    that rebuild through :meth:`BaselineMetadata.from_storage_row` — the
    same constructor the writer used, and a scope fingerprint re-derivation.
    """
    path = str(registry_path)
    if not os.path.exists(path):
        return {"schema_version": REGISTRY_SCHEMA_VERSION, "baselines": {}}
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BaselineMetadataError(
            f"{path}: not valid UTF-8 ({exc}) — registry files are written "
            f"UTF-8 only (FIX-278 caliber)") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BaselineMetadataError(
            f"{path}: not valid JSON ({exc}) — refusing a corrupted "
            f"registry, never tolerating it") from exc
    if not isinstance(payload, dict):
        raise BaselineMetadataError(
            f"{path}: expected a JSON object at the top level")
    version = payload.get("schema_version")
    if version != REGISTRY_SCHEMA_VERSION:
        raise RegistrySchemaError(
            f"{path}: schema_version {version!r} unsupported (this reader "
            f"knows version {REGISTRY_SCHEMA_VERSION} only) — refuse, never "
            f"guess (M0 face 4)")
    baselines = payload.get("baselines")
    if not isinstance(baselines, dict):
        raise BaselineMetadataError(
            f"{path}: 'baselines' must be an object keyed by gate_id")
    for gate_id, row in baselines.items():
        meta = BaselineMetadata.from_storage_row(row)  # raises on any defect
        if meta.gate_id != gate_id:
            raise BaselineMetadataError(
                f"{path}: row keyed {gate_id!r} carries gate_id "
                f"{meta.gate_id!r} — registry keys and rows must agree")
    return {"schema_version": REGISTRY_SCHEMA_VERSION, "baselines": baselines}


@dataclass(frozen=True)
class RegisterResult:
    """Structured registration result (DoD 5): ``registered`` wrote v1 of
    the row; ``replay`` found the identical row already present (effect-based
    idempotency — the file is untouched); ``dry_run`` previews without
    writing. Any first-time write path reports the row digest so callers can
    audit what exactly landed."""

    status: str
    gate_id: str
    registry_path: str
    row_digest: str
    dry_run: bool

    def __post_init__(self) -> None:
        if self.status not in ("registered", "replay"):
            raise ContractViolation(
                f"RegisterResult.status: {self.status!r} (expected "
                f"'registered' or 'replay')")
        object.__setattr__(
            self, "gate_id", _non_empty_text("RegisterResult.gate_id",
                                             self.gate_id))
        object.__setattr__(
            self, "registry_path",
            _non_empty_text("RegisterResult.registry_path",
                            self.registry_path))
        object.__setattr__(
            self, "row_digest",
            _non_empty_text("RegisterResult.row_digest", self.row_digest))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": "baseline-register",
            "status": self.status,
            "gate_id": self.gate_id,
            "registry": self.registry_path,
            "row_digest": self.row_digest,
            "dry_run": self.dry_run,
        }


def register(metadata: BaselineMetadata, registry_path, *,
             dry_run: bool = False) -> RegisterResult:
    """Register one baseline (write path; replay-idempotent, conflict-safe).

    Idempotency: the row's canonical digest is the replay key — registering
    the identical metadata twice writes the file exactly once and reports
    ``replay``. The same gate with different metadata is a
    :class:`BaselineConflict`: baselines carry provenance, and quietly
    overwriting provenance is the exact anti-pattern this ticket removes.
    Reliability (DoD 3/4): write-then-``os.replace`` atomic swap, explicit
    UTF-8, then a full re-read through :func:`load_registry` — the self-check
    parses the stored file with the same schema and refuses on any anomaly
    (it never "restores" the old file; recovery is a human decision).
    """
    if not isinstance(metadata, BaselineMetadata):
        raise ContractViolation(
            f"register: expected BaselineMetadata, got "
            f"{type(metadata).__name__}")
    path = str(registry_path)
    row = metadata.to_storage_dict()
    digest = _row_digest(row)
    if dry_run:
        return RegisterResult(status="registered", gate_id=metadata.gate_id,
                              registry_path=path, row_digest=digest,
                              dry_run=True)

    loaded = load_registry(path)
    existing = loaded["baselines"].get(metadata.gate_id)
    if existing is not None:
        existing_digest = _row_digest(existing)
        if existing_digest == digest:
            return RegisterResult(status="replay",
                                  gate_id=metadata.gate_id, registry_path=path,
                                  row_digest=digest, dry_run=False)
        raise BaselineConflict(
            f"{path}: gate {metadata.gate_id!r} is already registered with "
            f"different metadata (stored digest {existing_digest}, this "
            f"digest {digest}) — overwriting provenance is refused; retire "
            f"the old baseline deliberately, never silently")

    loaded["baselines"][metadata.gate_id] = row
    payload_bytes = _canonical_registry_bytes(loaded)
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb", dir=parent, prefix=".baselines-", suffix=".tmp",
        delete=False)
    try:
        with handle:
            handle.write(payload_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise

    # Write-after-read self-check (DoD 4): re-parse with the same schema.
    verified = load_registry(path)
    if _row_digest(verified["baselines"].get(metadata.gate_id, {})) != digest:
        raise BaselineMetadataError(
            f"{path}: write-after-read self-check failed for gate "
            f"{metadata.gate_id!r} — the stored row does not re-read as what "
            f"was written; inspect the registry manually (no auto-restore)")
    return RegisterResult(status="registered", gate_id=metadata.gate_id,
                          registry_path=path, row_digest=digest, dry_run=False)


# ── evaluation ──────────────────────────────────────────────────────────────


def evaluate(
    gate_id: str,
    observed_value: Any,
    *,
    policy_class: str,
    threshold: Any,
    direction: str,
    registry,
    observed_unit: Optional[str] = None,
    observed_scope_digest: Optional[str] = None,
    current_instrument_version: Optional[str] = None,
    current_target_digest: Optional[str] = None,
    floor_value: Any = None,
    now: Optional[datetime] = None,
) -> EvaluationOutcome:
    """Evaluate one observation against the registered baseline.

    Fail-closed chain (module docstring): gate-configuration contradictions
    first (they are the gate's own defect and must not be masked by baseline
    state), then baseline presence, expiry, caliber match, and only then the
    threshold comparison. Malformed caller inputs are ``ContractViolation``
    — caller bugs, not gate verdicts.

    Required-observation layering (P1-1, review-FEAT-047-CODE-R0 — two
    tiers, both fail-loud, neither silently skipped):

      * ``observed_unit`` / ``observed_scope_digest`` are REQUIRED the
        moment a baseline is present — omitting either is a
        ``ContractViolation`` (CLI exit 3). The caliber match is the core
        of the provenance mechanism (新鲜但口径不同同样不能比较), so an
        omitted caliber must never quietly bypass the comparison and let a
        drifted-caliber number pass as fresh (the W-3 shape this ticket
        exists to kill).
      * ``current_instrument_version`` / ``current_target_digest``: when
        the baseline's expiry is EVENT-based (``max_age_days`` absent —
        e.g. the stock row's "SKILL bump or surface SHA change"), these
        observations are what the expiry condition is checked against, so
        a missing one is fail-VISIBLE: ``not_evaluable`` with
        ``instrument_missing`` / ``target_missing`` — degraded to
        not-evaluable, never "check skipped". When the expiry is
        time-based (``max_age_days`` present) the event observations are
        optional: supplied → compared (``instrument_changed`` /
        ``target_changed``); absent → the TTL carries the expiry check.

    ``now`` is REQUIRED when the baseline carries ``max_age_days`` — a
    missing clock never silently skips the expiry check.
    """
    continuation = continuation_for(policy_class)  # closed enum, fails closed
    gate = _non_empty_text("evaluate: gate_id", gate_id)
    _finite_number("evaluate: observed_value", observed_value)
    if direction not in DIRECTIONS:
        raise ContractViolation(
            f"evaluate: unknown direction {direction!r} (closed enum "
            f"{DIRECTIONS})")
    if direction == "lower" and floor_value is not None:
        # P2-3: the frozen-floor contradiction check is defined for
        # upper-bound gates; a floor on a lower-bound gate is a caller bug —
        # refused at the entrance, never silently ignored.
        raise ContractViolation(
            f"evaluate: floor_value applies to upper-bound gates only "
            f"(got direction='lower' with floor_value={floor_value!r}) — "
            f"refuse rather than ignore")

    def axis_action(kind: str) -> Optional[str]:
        """Continuation-axis action for the evaluation-derived family.

        The axis splits exactly the diagnostics a non-pass verdict produces
        (expired / mismatched / missed): a blocking gate waits for
        re-measurement or an explicitly authorized waiver; an advisory gate
        records the miss and triggers a re-measurement action item.
        ``gate_configuration_error`` (fix the gate) and ``baseline_missing``
        (register first) own their repair actions; ``ok`` owns ``none``.
        """
        if kind in ("gate_configuration_error", "baseline_missing", "ok"):
            return None
        if continuation == "advisory":
            return ("re-measure (advisory gate: record the miss and trigger "
                    "a re-measurement action item)")
        return ("re-measure or obtain an explicitly authorized waiver "
                "before continuing")

    def outcome(evaluation: str, kind: str, message: str, action: str = None
                ) -> EvaluationOutcome:
        resolved = action if action is not None else axis_action(kind)
        if resolved is None:  # a supplied action is required for these kinds
            resolved = "none" if kind == "ok" else "resolve the diagnostic"
        return EvaluationOutcome(
            gate_id=gate, policy_class=policy_class, evaluation=evaluation,
            continuation=continuation,
            diagnostic=Diagnostic(kind=kind, message=message, action=resolved))

    # 1. deterministic gate-configuration contradictions (checked before any
    #    baseline state so the more fundamental defect is never masked).
    threshold_value: Optional[float] = None
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) \
            or not math.isfinite(threshold):
        return outcome(
            "not_evaluable", "gate_configuration_error",
            f"gate {gate!r}: threshold {threshold!r} is not a finite number "
            f"— the gate itself is misconfigured; this is not a user "
            f"failure and the threshold is never auto-adjusted",
            "fix the gate configuration (threshold must be a finite number)")
    threshold_value = float(threshold)
    floor: Optional[float] = None
    if floor_value is not None:
        if isinstance(floor_value, bool) \
                or not isinstance(floor_value, (int, float)) \
                or not math.isfinite(floor_value):
            return outcome(
                "not_evaluable", "gate_configuration_error",
                f"gate {gate!r}: floor_value {floor_value!r} is not a "
                f"finite number — the gate itself is misconfigured",
                "fix the gate configuration (floor_value must be finite or "
                "omitted)")
        floor = float(floor_value)
    if direction == "upper" and floor is not None and threshold_value < floor:
        # The EVD-1100 shape: the demanded budget sits below a value the
        # caliber's frozen floor makes unreachable — mathematically
        # impossible, so report the configuration, never a user failure.
        return outcome(
            "not_evaluable", "gate_configuration_error",
            f"gate {gate!r}: upper-bound threshold {threshold_value:g} is "
            f"below the caliber's frozen floor {floor:g} — mathematically "
            f"unreachable (EVD-1100 shape); this is a gate configuration "
            f"error, not a user failure",
            "fix the gate configuration (threshold vs frozen floor) or "
            "re-baseline the caliber")

    # 2. baseline presence.
    loaded = load_registry(registry)
    row = loaded["baselines"].get(gate)
    if row is None:
        return outcome(
            "not_evaluable", "baseline_missing",
            f"gate {gate!r}: no baseline registered in the registry — "
            f"without provenance the observation is not evaluable",
            "register the baseline first (baseline-register)")

    # 3. expiry — the evaluation basis invalidates (NOT_EVALUABLE family).
    meta = BaselineMetadata.from_storage_row(row)

    # P1-1 ①: comparison-side caliber observations are REQUIRED once a
    # baseline is present — an omitted unit/digest must never silently skip
    # the caliber match (step 4) and reach the threshold comparison.
    if observed_unit is None or observed_scope_digest is None:
        digest_state = "present" if observed_scope_digest else None
        raise ContractViolation(
            f"evaluate: observed_unit and observed_scope_digest are "
            f"required once baseline {gate!r} is registered (got "
            f"unit={observed_unit!r}, digest={digest_state}) — the caliber "
            f"match is the provenance core; omitting it must not silently "
            f"skip (derive the digest via caliber_digest)")

    event_based = meta.max_age_days is None
    if event_based and current_instrument_version is None:
        # P1-1 ②: an event-based expiry condition is checked against the
        # current instrument observation — a missing one degrades to
        # not_evaluable (fail-visible), never "check skipped".
        return outcome(
            "not_evaluable", "instrument_missing",
            f"gate {gate!r}: baseline expiry is event-based (no "
            f"max_age_days) and requires the current instrument version "
            f"observation — without it the expiry check cannot run and is "
            f"not silently skipped")
    if event_based and current_target_digest is None:
        return outcome(
            "not_evaluable", "target_missing",
            f"gate {gate!r}: baseline expiry is event-based (no "
            f"max_age_days) and requires the current target digest "
            f"observation — without it the expiry check cannot run and is "
            f"not silently skipped")
    if current_instrument_version is not None \
            and current_instrument_version != meta.instrument_version:
        return outcome(
            "not_evaluable", "instrument_changed",
            f"gate {gate!r}: instrument version changed "
            f"({meta.instrument_version!r} -> {current_instrument_version!r}) "
            f"— measurements from different instruments are not comparable")
    if current_target_digest is not None \
            and current_target_digest != meta.target_commit_digest:
        return outcome(
            "not_evaluable", "target_changed",
            f"gate {gate!r}: measured target changed "
            f"({meta.target_commit_digest!r} -> {current_target_digest!r}) — "
            f"the baseline was taken over different content")
    if meta.max_age_days is not None:
        if now is None:
            raise ContractViolation(
                f"evaluate: baseline {gate!r} carries max_age_days="
                f"{meta.max_age_days:g} but no 'now' was provided — the "
                f"expiry check never silently skips")
        measured = _as_naive(_parse_timestamp(
            "BaselineMetadata.measured_at", meta.measured_at))
        expires = measured + timedelta(days=meta.max_age_days)
        if _as_naive(now) > expires:
            return outcome(
                "not_evaluable", "baseline_expired",
                f"gate {gate!r}: baseline measured at {meta.measured_at} "
                f"expired after {meta.max_age_days:g}d (now "
                f"{_as_naive(now).isoformat()})")

    # 4. caliber match — fresh but different caliber is never a pass.
    if observed_unit is not None and observed_unit != meta.unit:
        return outcome(
            "not_evaluable", "caliber_mismatch",
            f"gate {gate!r}: observed unit {observed_unit!r} != baseline "
            f"unit {meta.unit!r} — numbers in different units are not "
            f"comparable even when both are fresh")
    if observed_scope_digest is not None \
            and observed_scope_digest != row["scope_digest"]:
        return outcome(
            "not_evaluable", "caliber_mismatch",
            f"gate {gate!r}: observation caliber fingerprint "
            f"{observed_scope_digest} != baseline scope_digest "
            f"{row['scope_digest']} — a fresh number measured over a "
            f"different caliber is not comparable")

    # 5. threshold comparison — only a fresh, matching caliber reaches here.
    if direction == "upper":
        passed = float(observed_value) <= threshold_value
    else:
        passed = float(observed_value) >= threshold_value
    if passed:
        return outcome("pass", "ok",
                       f"gate {gate!r}: observed {float(observed_value):g} "
                       f"within the {direction}-bound threshold "
                       f"{threshold_value:g} (baseline "
                       f"{float(meta.value):g} @ {meta.measured_at})")
    return outcome(
        "fail", "objective_missed",
        f"gate {gate!r}: observed {float(observed_value):g} violates the "
        f"{direction}-bound threshold {threshold_value:g} (baseline "
        f"{float(meta.value):g} @ {meta.measured_at})")


# ── CLI (self-contained until the batch-1 registry wiring lands) ────────────


def _add_register_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gate", required=True)
    parser.add_argument("--value", required=True, type=float)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--measured-at", required=True, dest="measured_at")
    parser.add_argument("--measurement-command", required=True,
                        dest="measurement_command")
    parser.add_argument("--instrument-version", required=True,
                        dest="instrument_version")
    parser.add_argument("--target-commit-digest", required=True,
                        dest="target_commit_digest")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--numerator", required=True)
    parser.add_argument("--denominator", required=True)
    parser.add_argument("--exclusions", required=True)
    parser.add_argument("--threshold-basis", required=True,
                        dest="threshold_basis")
    parser.add_argument("--expiry-condition", required=True,
                        dest="expiry_condition")
    parser.add_argument("--source-evd", required=True, dest="source_evd")
    parser.add_argument("--max-age-days", type=float, default=None,
                        dest="max_age_days")
    parser.add_argument("--registry", default=REGISTRY_FILENAME)
    parser.add_argument("--dry-run", action="store_true")


def _add_evaluate_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gate", required=True)
    parser.add_argument("--policy-class", required=True,
                        choices=list(POLICY_CLASSES))
    parser.add_argument("--observed-value", required=True, type=float,
                        dest="observed_value")
    parser.add_argument("--threshold", required=True, type=float)
    parser.add_argument("--direction", required=True, choices=list(DIRECTIONS))
    parser.add_argument("--observed-unit", default=None, dest="observed_unit")
    parser.add_argument("--observed-scope-digest", default=None,
                        dest="observed_scope_digest")
    parser.add_argument("--current-instrument-version", default=None,
                        dest="current_instrument_version")
    parser.add_argument("--current-target-digest", default=None,
                        dest="current_target_digest")
    parser.add_argument("--floor-value", type=float, default=None,
                        dest="floor_value")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 evaluation instant (default: now)")
    parser.add_argument("--registry", default=REGISTRY_FILENAME)


class _Parser(argparse.ArgumentParser):
    """Usage errors exit 3 — a CLI mistake must never wear a gate verdict's
    exit code (0/1/2 are reserved for pass/fail/not_evaluable)."""

    def error(self, message):  # pragma: no cover - argparse plumbing
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(3)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="baseline_metadata",
        description="BaselineMetadata provenance registry (FEAT-047): "
                    "numeric-gate baselines with seven provenance elements, "
                    "expiry/caliber-aware evaluation, and the "
                    "BLOCK/ADVISORY continuation axis.")
    subparsers = parser.add_subparsers(dest="command")
    register_parser = subparsers.add_parser(
        "baseline-register",
        help="register one gate baseline (dry-run previews without writing)")
    _add_register_options(register_parser)
    evaluate_parser = subparsers.add_parser(
        "baseline-evaluate",
        help="evaluate an observation against the registered baseline")
    _add_evaluate_options(evaluate_parser)
    return parser


def _emit(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse usage error (already exit 3)
        return int(exc.code or 0)
    if not getattr(args, "command", None):
        parser.print_usage(sys.stderr)
        return 3
    try:
        if args.command == "baseline-register":
            metadata = BaselineMetadata(
                gate_id=args.gate,
                value=args.value,
                unit=args.unit,
                measured_at=args.measured_at,
                measurement_command=args.measurement_command,
                instrument_version=args.instrument_version,
                target_commit_digest=args.target_commit_digest,
                scope=args.scope,
                numerator=args.numerator,
                denominator=args.denominator,
                exclusions=args.exclusions,
                threshold_basis=args.threshold_basis,
                expiry_condition=args.expiry_condition,
                source_evd=args.source_evd,
                max_age_days=args.max_age_days,
            )
            result = register(metadata, args.registry, dry_run=args.dry_run)
            payload = result.to_dict()
            if args.dry_run:
                payload["would_write"] = metadata.to_storage_dict()
            _emit(payload)
            return 0
        if args.command == "baseline-evaluate":
            # P0-1 (review-FEAT-047-CODE-R0): parse through the same
            # fail-closed wrapper as every other timestamp — a bare
            # ``fromisoformat`` ValueError would pierce the except face and
            # exit 1, wearing a FAIL verdict for what is a usage error.
            now = (_parse_timestamp("main: --now", args.now) if args.now
                   else datetime.now())
            outcome = evaluate(
                args.gate,
                args.observed_value,
                policy_class=args.policy_class,
                threshold=args.threshold,
                direction=args.direction,
                registry=args.registry,
                observed_unit=args.observed_unit,
                observed_scope_digest=args.observed_scope_digest,
                current_instrument_version=args.current_instrument_version,
                current_target_digest=args.current_target_digest,
                floor_value=args.floor_value,
                now=now,
            )
            _emit(outcome.to_dict())
            return {"pass": 0, "fail": 1, "not_evaluable": 2}[
                outcome.evaluation]
        return 3
    except (ContractViolation, BaselineMetadataError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        # Storage-face convergence (P0-1 same family): a registry the CLI
        # cannot read/write (permission, missing parent, disk) is a command
        # error (exit 3), never a gate verdict (0/1/2 are verdict codes).
        print(f"ERROR: storage failure: {exc}", file=sys.stderr)
        return 3


def cmd_baseline_register(args) -> int:
    """Registry-wiring face (engine ``cmd_*`` dispatch convention).

    Reads the same options the subcommand parser defines off the engine's
    Namespace; the batch-1 integration point adds the two dispatch keys and
    identical option names to the engine parser (self-contained module,
    engine wires dispatch — governance_cost pattern).
    """
    return main(["baseline-register"] + _namespace_to_argv(
        args, _register_option_map()))


def cmd_baseline_evaluate(args) -> int:
    return main(["baseline-evaluate"] + _namespace_to_argv(
        args, _evaluate_option_map()))


def _register_option_map() -> Dict[str, str]:
    return {
        "gate": "--gate", "value": "--value", "unit": "--unit",
        "measured_at": "--measured-at",
        "measurement_command": "--measurement-command",
        "instrument_version": "--instrument-version",
        "target_commit_digest": "--target-commit-digest",
        "scope": "--scope", "numerator": "--numerator",
        "denominator": "--denominator", "exclusions": "--exclusions",
        "threshold_basis": "--threshold-basis",
        "expiry_condition": "--expiry-condition", "source_evd": "--source-evd",
        "max_age_days": "--max-age-days", "registry": "--registry",
        "dry_run": "--dry-run",
    }


def _evaluate_option_map() -> Dict[str, str]:
    return {
        "gate": "--gate", "policy_class": "--policy-class",
        "observed_value": "--observed-value", "threshold": "--threshold",
        "direction": "--direction", "observed_unit": "--observed-unit",
        "observed_scope_digest": "--observed-scope-digest",
        "current_instrument_version": "--current-instrument-version",
        "current_target_digest": "--current-target-digest",
        "floor_value": "--floor-value", "now": "--now",
        "registry": "--registry",
    }


def _namespace_to_argv(args: Any, option_map: Dict[str, str]) -> list:
    """Rebuild an argv from an engine-side Namespace (None values dropped,
    booleans become flags)."""
    argv: list = []
    for attr, flag in option_map.items():
        value = getattr(args, attr, None)
        if value is None:
            continue
        if value is True:
            argv.append(flag)
        elif value is not False:
            argv.extend([flag, str(value)])
    return argv


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
