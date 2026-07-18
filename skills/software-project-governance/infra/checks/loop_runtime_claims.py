"""Fail-closed semantic Loop-runtime capability claim scanner (FIX-197)."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import stat
import tokenize
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Optional


POLICY_RELATIVE_PATH = PurePosixPath("core/loop-runtime-claim-allowlist.json")
AUTHORITY_RELATIVE_PATH = PurePosixPath("core/loop-runtime-claim-authority.json")
SUPPORTED_EXTENSIONS = {".md": "markdown", ".py": "python", ".json": "json"}
SEMANTIC_ACCOUNTING_CONTRACT = "loop-semantic-accounting/v1"
SEMANTIC_REPORT_SCHEMA = "loop-semantic-claim-report/v1"
IDENTITY_ATTESTATION_PENDING = "IDENTITY_ATTESTATION_PENDING"
ROOT_ROLE_ORDER = {"product_root": 0, "plugin_home": 1, "host_root": 2}
HOT_PATHS = (
    ".governance/plan-tracker.md",
    ".governance/session-snapshot.md",
    ".governance/evidence-log.md",
    ".governance/risk-log.md",
)
NOTICE_RE = re.compile(r"<!--\s*loop-runtime-superseding:(\{.*?\})\s*-->")
TARGET_RE = re.compile(r"<!--\s*loop-runtime-target:(\{.*?\})\s*-->")
CLAUSE_SPLIT_RE = re.compile(r"(?<=[。！？.!?；;])\s+|(?<=。)|(?<=！)|(?<=？)|(?<=；)")
ADR_SNAPSHOT_PATH = "docs/architecture/ADR-011-loop-runtime-claim-correction.md"
ADR_DIGEST_RE = re.compile(r"(?m)^(inventory_sha256: )[0-9a-f]{64}$")

SUBJECT_PATTERNS = {
    "runtime_activation": re.compile(r"(?i)(?:loop[-_ ](?:engineering[-_ ])?runtime|loop\s*运行时|循环运行时|runtime[-_ ]activation)"),
    "migration_validity": re.compile(r"(?i)(?:loop(?: engineering)? migration|migration[-_ ]validity|迁移(?:产物|payload|结果))"),
    "persisted_back_edge": re.compile(r"(?i)(?:persist(?:ed|ent)?\s+back[- ]edge|持久化(?:回边|back[- ]edge))"),
    "flow_unit_loop_count": re.compile(r"(?i)(?:flow[-_ ]unit.{0,24}loop_count|per[- ]unit loop count)"),
    "tier_fuse": re.compile(r"(?i)(?:tier fuse|loop fuse|Middle fuse|Inner fuse|Outer fuse|setup fuse)"),
    "paro_transition": re.compile(r"(?i)(?:PARO(?: transition)?|Plan.Act.Observe.Reflect)"),
    "automatic_escalation": re.compile(r"(?i)(?:loop.{0,24}automatic escalation|automatic loop escalation|循环自动升级)"),
    "only_model": re.compile(r"(?i)(?:loop.{0,24}(?:only|唯一).{0,16}model|loop 是唯一模型|唯一循环模型)"),
    "classic_supersession": re.compile(r"(?i)(?:classic.{0,30}(?:deprecated|superseded|replaced)|经典.{0,20}(?:废弃|替代))"),
    "global_stage": re.compile(
        r"(?i)(?:no\s+global\s+stage|global\s+stage.{0,24}(?:removed|eliminated|disabled)|"
        r"(?:移除|取消|不再存在).{0,16}(?:单一当前阶段|全局阶段))"
    ),
    "criteria_completion": re.compile(
        r"(?i)(?:criteria?\s*(?:2\s*[-–]\s*8|2\s*/\s*3\s*/\s*4\s*/\s*5\s*/\s*6(?:\s*/\s*7(?:\s*/\s*8)?)?)|"
        r"标准\s*2\s*[-至]\s*8)"
    ),
    "risk_closure": re.compile(r"(?i)(?:RISK-(?:037|042).{0,24}(?:closed|closure|关闭)|(?:关闭|解决).{0,24}RISK-(?:037|042))"),
    "readiness": re.compile(
        r"(?i)(?:loop(?: engineering)?.{0,48}(?:1\.0\.0|production[- ]ready|正式版就绪)|"
        r"(?:1\.0\.0|production[- ]ready|正式版就绪).{0,48}loop(?: engineering)?)"
    ),
}
LOOP_POTENTIAL_RE = re.compile(
    r"(?i)(?:\bloop\b|循环).{0,48}(?:scheduler|orchestrat|dispatch|executor|调度|编排).{0,48}"
    r"(?:active|enabled|complete|implemented|operational|运行|已激活|已实现|已启用|已运行)"
)
UNKNOWN_LOOP_RELATION_RE = re.compile(
    r"(?ix)(?:\bloop(?:[-_ ]engineering)?\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,5}\s+"
    r"(?:is|are|becomes?|remains?|[:=])\s*(?:active|activated|enabled|complete|implemented|operational|ready|met|resolved|closed)|"
    r"\b[a-z][\w-]*(?:\s+[a-z][\w-]*){0,5}\s+(?:is|are|becomes?|remains?)\s+"
    r"(?:active|activated|enabled|complete|implemented|operational|ready|met|resolved|closed)\s+"
    r"(?:for|in)\s+loop\b|\bloop\s+[\w-]+.{0,24}(?:已|自动)(?:激活|启用|完成|实现|生效|执行))"
)
SUBJECT_HINT_TOKENS = (
    "loop", "runtime", "runtime_activation", "runtime activation", "loop migration", "migration_validity",
    "migration validity", "back-edge", "back edge", "loop_count", "tier fuse", "loop fuse", "middle fuse",
    "inner fuse", "outer fuse", "setup fuse", "paro",
    "classic", "global stage", "criteria", "criterion", "risk-037", "risk-042", "production-ready",
    "plan-act-observe-reflect", "循环", "循环运行时", "迁移产物", "迁移payload", "迁移结果", "持久化回边",
    "循环自动升级", "当前阶段", "全局阶段", "标准 2", "标准2", "正式版就绪",
)
SUBJECT_HINT_RE = re.compile(
    "|".join(re.escape(token) for token in sorted(SUBJECT_HINT_TOKENS, key=len, reverse=True))
)
STATE_FIELD_RE = re.compile(
    r"(?i)\b(?:state|status|mode|capability|readiness|activation)\b\s*[:=]"
)
ACCOUNTING_JSON_ENCODER = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))

REQUIRED_RULES = {
    "runtime_activation": "LRC-ACTIVE-RUNTIME", "migration_validity": "LRC-ACTIVE-MIGRATION",
    "persisted_back_edge": "LRC-ACTIVE-BACKEDGE", "flow_unit_loop_count": "LRC-ACTIVE-COUNT",
    "tier_fuse": "LRC-ACTIVE-FUSE", "paro_transition": "LRC-ACTIVE-PARO",
    "automatic_escalation": "LRC-ACTIVE-ESCALATION", "only_model": "LRC-ACTIVE-ONLY-MODEL",
    "classic_supersession": "LRC-ACTIVE-CLASSIC", "global_stage": "LRC-ACTIVE-GLOBAL-STAGE",
    "criteria_completion": "LRC-ACTIVE-CRITERIA", "risk_closure": "LRC-ACTIVE-RISK",
    "readiness": "LRC-ACTIVE-READINESS",
}
REQUIRED_HISTORICAL_IDS = {
    "LRC-HIST-CHANGELOG-001", "LRC-HIST-FEATURE-FLAGS-001", "LRC-HIST-RELEASE-CHECKLIST-001",
    "LRC-HIST-ROLLBACK-001", "LRC-HIST-ARCH-001", "LRC-HIST-BREAKDOWN-001", "LRC-HIST-SHITU-001",
}
REQUIRED_SOURCE_IDS = {"DEC-104", "EVD-707", "AUDIT-133"}
REQUIRED_POLICY_SHA256 = "d8aeeb210fae02c452ec1eac88d3b5bf627afe7717b2da8b1b46abb318440f3d"
REQUIRED_SOURCE_RECORDS = {
    "DEC-104": (".governance/decision-log.md", "| DEC-104 |", "7666ace742ebc8691356ea53b884163ffafc25dd8545d7e6b680786461f6db11"),
    "EVD-707": (".governance/evidence-log.md", "| EVD-707 |", "8aa48e272d6e627cdb64d5eb443215a584e5d0fc6cdfbb5fa329a93dfeb68e69"),
    "AUDIT-133": (".governance/plan-tracker.md", "| **P0** | AUDIT-133 |", "c3fbd2e490f8871a39e63a7c2db750ee71bd0d8f9550b83f4442344532c08adb"),
}
REQUIRED_PLANNED_TARGETS = {
    **{f"LRC-{name}-PLANNED-001": frozenset({
        "persisted_back_edge", "flow_unit_loop_count", "tier_fuse", "paro_transition", "automatic_escalation",
    }) for name in ("CODE", "DESIGN", "RELEASE", "REQUIREMENT", "RETRO", "TECH", "TEST", "MAPPING")},
    "LRC-ARCH-PLANNED-001": frozenset({
        "persisted_back_edge", "flow_unit_loop_count", "tier_fuse", "paro_transition", "automatic_escalation",
    }),
}
REQUIRED_PATHS = {
    *(f"product_root:skills/{name}-review/SKILL.md" for name in ("code", "design", "release", "requirement", "retro", "tech", "test")),
    "product_root:skills/software-project-governance/references/loop-role-mapping.md",
    "product_root:skills/software-project-governance/core/loop-runtime-claim-allowlist.json",
    "product_root:skills/software-project-governance/core/loop-runtime-claim-authority.json",
    "product_root:skills/software-project-governance/core/manifest.json",
    "product_root:skills/software-project-governance/infra/checks/loop_runtime_claims.py",
    "product_root:skills/software-project-governance/infra/verify_workflow.py",
    "product_root:skills/software-project-governance/infra/loop_migration.py",
    "product_root:skills/software-project-governance/infra/tests/test_loop_runtime_claims.py",
    "product_root:skills/software-project-governance/infra/tests/test_verify_workflow.py",
    "product_root:skills/software-project-governance/infra/TOOLS.md",
    "product_root:project/CHANGELOG.md",
    "product_root:docs/release/feature-flags-0.65.0.md",
    "product_root:docs/release/release-checklist-0.65.0.md",
    "product_root:docs/release/rollback-plan-0.65.0.md",
    "product_root:docs/requirements/loop-engineering-architecture-0.65.0-proposed.md",
    "product_root:docs/requirements/loop-engineering-implementation-breakdown-0.65.0.md",
    "product_root:docs/requirements/shitu-loop-engineering-validation-0.65.0.md",
    "product_root:docs/migration/loop-engineering-runtime-contract-migration-0.66.1.md",
    *(f"host_root:{path}" for path in HOT_PATHS),
}
AFFIRMATIVE_RE = re.compile(
    r"(?ix)(?:\bis\s+(?:active|enabled|complete|valid|implemented|met|operational|ready)\b|"
    r"\b(?:active|activated|enabled|complete|valid|implemented|operational|ready|"
    r"deprecated|superseded|replaced|removed|eliminated|disabled|production[- ]ready)\b|"
    r"(?:已|自动)(?:激活|启用|完成|实现|生效|执行|持久化|升级|关闭|替代)|"
    r"(?:flags?\s+flip\s+to\s+true|[:=]\s*true\b|[:=]\s*[\"']?(?:MET|valid|active|enabled)[\"']?))"
)
NEGATIVE_RE = re.compile(
    r"(?ix)(?:\b(?:no|not|never|isn't|is\s+not|does\s+not|do\s+not|cannot)\b|"
    r"未(?:激活|启用|完成|实现|生效|执行|持久化|证明)|"
    r"不(?:激活|启用|代表|等于|执行|关闭|声明|生效)|"
    r"NOT_MET|NOT_PROVEN|MET[-_ ]NARROW|PARTIAL|non[- ]closed|非\s*closed|experimental[_ -]scaffolding|planned_not_active|false)"
)


@dataclass(frozen=True)
class ClaimScanContext:
    product_root: Path
    plugin_home: Path
    host_root: Optional[Path] = None
    scan_mode: str = "product_release"

    def __post_init__(self):
        object.__setattr__(self, "product_root", Path(self.product_root))
        object.__setattr__(self, "plugin_home", Path(self.plugin_home))
        if self.host_root is not None:
            object.__setattr__(self, "host_root", Path(self.host_root))


@dataclass(frozen=True)
class ScanLimits:
    max_candidates: int = 1500
    max_candidate_bytes: int = 24 * 1024 * 1024
    max_file_bytes: int = 2 * 1024 * 1024
    max_semantic_units: int = 300000
    max_semantic_payload_bytes: int = 32 * 1024 * 1024


@dataclass(frozen=True)
class Candidate:
    root_owner: str
    normalized_path: str
    absolute_path: Path
    language: str
    raw: bytes
    raw_bytes: int
    sha256: str


@dataclass(frozen=True)
class CandidateInventory:
    files: tuple[Candidate, ...] = ()
    candidate_count: int = 0
    candidate_bytes: int = 0
    inventory_sha256: str = ""


@dataclass(frozen=True)
class Relation:
    subject: str
    predicate: str
    polarity: str
    temporal_scope: str
    subject_span: tuple[int, int]
    predicate_spans: tuple[tuple[int, int], ...]
    negator_spans: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class SemanticUnit:
    root_owner: str
    normalized_path: str
    language: str
    locator: str
    source_span: tuple[int, int, int, int]
    raw_text_sha256: str
    canonical_text: str
    unit_kind: str
    provenance: str
    subject: str
    predicate: str
    polarity: str
    temporal_scope: str
    extraction_state: str
    context_text: str = ""
    claim_id: str = ""
    relations: tuple[Relation, ...] = ()


@dataclass(frozen=True)
class Finding:
    code: str
    stage: str
    message: str
    root_owner: str = ""
    normalized_path: str = ""
    locator: Any = None
    authority_version: str = ""
    claim_id: str = ""
    classification: str = ""


@dataclass
class ClaimScanReport:
    verdict: str
    scan_mode: str = "product_release"
    inventory: CandidateInventory = field(default_factory=CandidateInventory)
    parsed_candidates: int = 0
    semantic_units: int = 0
    semantic_payload_bytes: int = 0
    findings: list[Finding] = field(default_factory=list)
    notices_verified: int = 0
    historical_matches: int = 0
    skipped_candidates: int = 0
    truncated_candidates: int = 0
    host_state: str = "INITIALIZED"
    state_totals: dict[str, int] = field(default_factory=dict)
    final_inventory_sha256: str = ""
    classification_ledger: list[dict[str, str]] = field(default_factory=list)
    semantic_accounting_contract: str = SEMANTIC_ACCOUNTING_CONTRACT
    semantic_accounting_by_path: dict[str, dict[str, Any]] = field(default_factory=dict)
    semantic_accounting_sha256: str = ""
    source_envelope_sha256: str = field(default_factory=lambda: hashlib.sha256(b"").hexdigest())
    policy_sha256: str = field(default_factory=lambda: hashlib.sha256(b"").hexdigest())
    authority_sha256: str = field(default_factory=lambda: hashlib.sha256(b"").hexdigest())

    def _semantic_verdict(self) -> str:
        if self.verdict == "PASS":
            return "NOT_APPLICABLE" if self.host_state == "UNINITIALIZED" else "PASS"
        if any(
            finding.code == "UNKNOWN"
            or finding.code.endswith("_UNKNOWN")
            or "UNAVAILABLE" in finding.code
            or finding.code in {"ROOT_RESOLUTION_ERROR", "AUTHORITY_SOURCE_ROOT_MISSING"}
            for finding in self.findings
        ):
            return "UNKNOWN"
        return "FAIL"

    @staticmethod
    def _report_locator(locator: Any) -> dict[str, Any] | None:
        if locator in (None, ""):
            return None
        if isinstance(locator, dict):
            return locator
        return {"semantic_locator": str(locator)}

    def as_s1_dict(self) -> dict[str, Any]:
        record_digest_input = [
            {
                "path": path,
                "record_sha256": summary.get("record_sha256", ""),
                "unit_count": summary.get("unit_count", 0),
                "payload_bytes": summary.get("payload_bytes", 0),
            }
            for path, summary in sorted(self.semantic_accounting_by_path.items())
        ]
        record_digest = _sha_text(json.dumps(
            record_digest_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ))
        return {
            "schema_version": SEMANTIC_REPORT_SCHEMA,
            "scan_mode": self.scan_mode,
            "semantic_verdict": self._semantic_verdict(),
            "source_envelope_sha256": self.source_envelope_sha256,
            "scanner_inventory_digest": self.inventory.inventory_sha256 or hashlib.sha256(b"").hexdigest(),
            "accounting_contract": SEMANTIC_ACCOUNTING_CONTRACT,
            "accounting": {
                "record_count": self.semantic_units,
                "payload_bytes": self.semantic_payload_bytes,
                "record_digest": record_digest,
                "aggregate_digest": self.semantic_accounting_sha256 or hashlib.sha256(b"").hexdigest(),
            },
            "controls": {
                "policy_sha256": self.policy_sha256,
                "authority_sha256": self.authority_sha256,
            },
            "findings": [{
                "code": finding.code,
                "root_owner": finding.root_owner,
                "path": finding.normalized_path,
                "locator": self._report_locator(finding.locator),
                "detail": f"{finding.claim_id}: {finding.message}" if finding.claim_id else finding.message,
            } for finding in self.findings],
        }

    def as_dict(self) -> dict[str, Any]:
        """Preserve the existing CLI JSON surface; S1 is emitted explicitly."""
        return {
            "verdict": self.verdict,
            "inventory": {
                "candidate_count": self.inventory.candidate_count,
                "candidate_bytes": self.inventory.candidate_bytes,
                "inventory_sha256": self.inventory.inventory_sha256,
                "final_inventory_sha256": self.final_inventory_sha256,
            },
            "parsed_candidates": self.parsed_candidates,
            "semantic_units": self.semantic_units,
            "semantic_payload_bytes": self.semantic_payload_bytes,
            "findings": [finding.__dict__ for finding in self.findings],
            "notices_verified": self.notices_verified,
            "historical_matches": self.historical_matches,
            "skipped_candidates": self.skipped_candidates,
            "truncated_candidates": self.truncated_candidates,
            "host_state": self.host_state,
            "state_totals": dict(sorted(self.state_totals.items())),
            "classification_ledger": self.classification_ledger,
            "semantic_accounting_contract": self.semantic_accounting_contract,
            "semantic_accounting_by_path": self.semantic_accounting_by_path,
            "semantic_accounting_sha256": self.semantic_accounting_sha256,
        }


def _canonical_text(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="strict")
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def _sha_text(text: str) -> str:
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def _canonical_content_digest(text: str, root_owner: str,
                              normalized_path: str) -> tuple[Optional[str], Optional[str]]:
    if root_owner == "product_root" and normalized_path == ADR_SNAPSHOT_PATH:
        matches = list(ADR_DIGEST_RE.finditer(text))
        if len(matches) != 1:
            return None, f"ADR inventory digest placeholder count must be 1, found {len(matches)}"
        text = ADR_DIGEST_RE.sub(r"\g<1>" + ("0" * 64), text, count=1)
    return _sha_text(text), None


def _content_digest(raw: bytes, root_owner: str, normalized_path: str) -> tuple[Optional[str], Optional[str]]:
    try:
        text = _canonical_text(raw)
    except UnicodeError as exc:
        return None, str(exc)
    return _canonical_content_digest(text, root_owner, normalized_path)


def _account_context(kind: str, *, index: int | None = None, level: int | None = None,
                     name: str | None = None, payload: str | None = None,
                     pointer: str | None = None) -> dict[str, Any]:
    return {
        "index": index,
        "kind": kind,
        "level": level,
        "name": name,
        "payload": payload,
        "pointer": pointer,
    }


def _source_locator(start_line: int, start_column: int,
                    end_line: int, end_column: int) -> dict[str, Any]:
    return {
        "end_column": end_column,
        "end_line": end_line,
        "pointer": None,
        "role": None,
        "start_column": start_column,
        "start_line": start_line,
        "type": "source_span",
    }


def _pointer_locator(pointer: str, role: str) -> dict[str, Any]:
    return {
        "end_column": None,
        "end_line": None,
        "pointer": pointer,
        "role": role,
        "start_column": None,
        "start_line": None,
        "type": "json_pointer",
    }


def _account_record(candidate: Candidate, ordinal: int, kind: str,
                    locator: dict[str, Any], context_chain: list[dict[str, Any]],
                    payload: str) -> dict[str, Any]:
    return {
        "context_chain": context_chain,
        "kind": kind,
        "language": candidate.language,
        "locator": locator,
        "normalized_path": candidate.normalized_path,
        "normalized_payload": unicodedata.normalize("NFC", payload.strip(" \t\n")),
        "ordinal": ordinal,
        "root_owner": candidate.root_owner,
    }


def _serialize_accounting_records(records: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (ACCOUNTING_JSON_ENCODER.encode(record) + "\n").encode("utf-8")
        for record in records
    )


def _split_markdown_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    first_pipe = body.find("|")
    last_pipe = body.rfind("|")
    protected_pipe = "\\|" in body
    if first_pipe >= 0 and first_pipe != last_pipe:
        for marker, closing in (("`", "`"), ('"', '"'), ("<", ">")):
            start = body.find(marker)
            end = body.rfind(closing)
            if start >= 0 and start < last_pipe and end > first_pipe:
                protected_pipe = True
                break
    if not protected_pipe:
        return [cell.strip(" \t") for cell in body.split("|")]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    code_delimiter = 0
    quoted = False
    angle_literal = False
    position = 0
    while position < len(body):
        character = body[position]
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "`":
            end = position
            while end < len(body) and body[end] == "`":
                end += 1
            run = end - position
            current.extend("`" * run)
            if code_delimiter == 0:
                code_delimiter = run
            elif code_delimiter == run:
                code_delimiter = 0
            position = end - 1
        elif character == '"' and code_delimiter == 0:
            current.append(character)
            quoted = not quoted
        elif character == "<" and code_delimiter == 0 and not quoted and position > 0 \
                and body[position - 1].isalnum() and ">" in body[position + 1:]:
            current.append(character)
            angle_literal = True
        elif character == ">" and angle_literal:
            current.append(character)
            angle_literal = False
        elif character == "|" and code_delimiter == 0 and not quoted and not angle_literal:
            cells.append("".join(current).strip(" \t"))
            current = []
        else:
            current.append(character)
        position += 1
    cells.append("".join(current).strip(" \t"))
    return cells


def _markdown_accounting(candidate: Candidate, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    records: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    list_ancestors: list[tuple[int, str]] = []
    index = 0

    def emit(kind: str, start: int, end: int, payload: str,
             context: list[dict[str, Any]], start_column: int = 0,
             end_column: int | None = None) -> None:
        normalized = unicodedata.normalize("NFC", payload.strip(" \t\n"))
        if not normalized:
            return
        records.append(_account_record(
            candidate, len(records), kind,
            _source_locator(start, start_column, end, len(lines[end]) if end_column is None else end_column),
            context, normalized,
        ))

    def heading_context() -> list[dict[str, Any]]:
        return [_account_context("md_heading", level=level, payload=payload) for level, payload in headings]

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        atx = re.match(r"^\s*(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", line)
        setext = index + 1 < len(lines) and bool(re.match(r"^\s*(?:=+|-+)\s*$", lines[index + 1]))
        if atx or setext:
            list_ancestors.clear()
            level = len(atx.group(1)) if atx else (1 if "=" in lines[index + 1] else 2)
            payload = atx.group(2) if atx else stripped
            while headings and headings[-1][0] >= level:
                headings.pop()
            emit("md_heading", index, index if atx else index + 1, payload, heading_context(),
                 0, len(line) if atx else len(lines[index + 1]))
            headings.append((level, unicodedata.normalize("NFC", payload.strip(" \t"))))
            index += 1 if atx else 2
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            list_ancestors.clear()
            if index > 0 and re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[index - 1]):
                index += 1
                continue
            delimiter = fence.group(1)
            end = index + 1
            while end < len(lines) and not re.match(rf"^\s*{re.escape(delimiter[0])}{{{len(delimiter)},}}\s*$", lines[end]):
                if lines[end].strip(" \t"):
                    emit("md_fence_line", end, end, lines[end], heading_context())
                end += 1
            if end >= len(lines):
                raise ValueError("ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: unterminated fence")
            index = end + 1
            continue
        if "<!--" in line:
            list_ancestors.clear()
            end = index
            body = line.split("<!--", 1)[1]
            while "-->" not in body:
                end += 1
                if end >= len(lines):
                    raise ValueError("ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: unterminated comment")
                body += "\n" + lines[end]
            emit("md_comment", index, end, body.split("-->", 1)[0], heading_context())
            index = end + 1
            continue
        governance_record = re.match(r"^\s*\|\s*((?:EVD|REVIEW|QA)-[^|]+)\s*\|", line)
        if governance_record:
            list_ancestors.clear()
            cells = _split_markdown_cells(line)
            record_context = heading_context() + [
                _account_context("governance_record", payload=governance_record.group(1).strip())
            ]
            for payload in cells:
                emit("md_governance_record_cell", index, index, payload, record_context)
            index += 1
            continue
        if index + 1 < len(lines) and "|" in line and re.match(
            r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]
        ):
            headers = _split_markdown_cells(line)
            normalized_headers = [header.casefold() for header in headers]
            if len(normalized_headers) != len(set(normalized_headers)):
                raise ValueError("ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: duplicate table header")
            list_ancestors.clear()
            for column, payload in enumerate(headers):
                emit("md_table_cell", index, index, payload, heading_context())
            row = index + 2
            while row < len(lines) and "|" in lines[row] and lines[row].strip():
                cells = _split_markdown_cells(lines[row])
                if len(cells) != len(headers):
                    raise ValueError("ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row")
                row_header = cells[0] if cells and cells[0] else None
                for column, payload in enumerate(cells):
                    context = heading_context() + [_account_context("md_table_header", index=column, payload=headers[column])]
                    if row_header and column:
                        context.append(_account_context("md_table_row_header", index=0, payload=row_header))
                    emit("md_table_cell", row, row, payload, context)
                row += 1
            index = row
            continue
        list_match = re.match(r"^(\s*)(?:[-*+] |\d+[.)] )(.*)$", line)
        if list_match:
            level = len(list_match.group(1).expandtabs(4))
            while list_ancestors and list_ancestors[-1][0] >= level:
                list_ancestors.pop()
            payload_lines = [list_match.group(2)]
            end = index
            while end + 1 < len(lines):
                continuation = lines[end + 1]
                if not continuation.strip():
                    break
                if re.match(r"^\s*(?:#{1,6}[ \t]+|`{3,}|~{3,}|<!--)", continuation):
                    break
                if re.match(r"^(\s*)(?:[-*+] |\d+[.)] )", continuation):
                    break
                indentation = len(continuation) - len(continuation.lstrip(" \t"))
                if indentation <= level:
                    break
                payload_lines.append(continuation.strip())
                end += 1
            payload = "\n".join(payload_lines)
            context = heading_context() + [
                _account_context("md_list_item", level=ancestor_level, payload=ancestor_payload)
                for ancestor_level, ancestor_payload in list_ancestors
            ]
            emit("md_list_item", index, end, payload, context, 0, len(lines[end]))
            list_ancestors.append((level, unicodedata.normalize("NFC", payload.strip(" \t\n"))))
            index = end + 1
            continue
        list_ancestors.clear()
        start = index
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(
            r"^\s*(?:#{1,6}[ \t]+|[-*+] |\d+[.)] |```|~~~|<!--)", lines[index]
        ):
            if index + 1 < len(lines) and re.match(r"^\s*(?:=+|-+)\s*$", lines[index + 1]):
                break
            paragraph.append(lines[index])
            index += 1
        emit("md_paragraph", start, start + len(paragraph) - 1, "\n".join(paragraph), heading_context())
    return records


class _JsonNumber(str):
    pass


def _json_accounting(candidate: Candidate, text: str) -> list[dict[str, Any]]:
    def checked_string(value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("ACCOUNTING_JSON_PARSE_ERROR: unpaired surrogate") from exc
        return value

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            checked_string(key)
            if key in result:
                raise ValueError("ACCOUNTING_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    data = json.loads(
        text,
        object_pairs_hook=pairs,
        parse_int=_JsonNumber,
        parse_float=_JsonNumber,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid constant {value}")),
    )
    records: list[dict[str, Any]] = []

    def escaped(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def emit(kind: str, pointer: str, role: str, payload: str, context: list[dict[str, Any]]) -> None:
        records.append(_account_record(
            candidate, len(records), kind, _pointer_locator(pointer, role), context, payload,
        ))

    def walk(value: Any, pointer: str, context: list[dict[str, Any]]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_pointer = f"{pointer}/{escaped(key)}"
                emit("json_key", child_pointer, "key", key, context)
                key_context = context + [_account_context("json_key", payload=key, pointer=child_pointer)]
                walk(child, child_pointer, key_context)
        elif isinstance(value, list):
            for item_index, child in enumerate(value):
                child_pointer = f"{pointer}/{item_index}"
                walk(child, child_pointer, context + [
                    _account_context("json_array_index", index=item_index, pointer=child_pointer)
                ])
        elif isinstance(value, str) and not isinstance(value, _JsonNumber):
            emit("json_string", pointer or "", "value", checked_string(value), context)
        elif isinstance(value, _JsonNumber):
            emit("json_number", pointer or "", "value", str(value), context)
        elif value is True or value is False:
            emit("json_boolean", pointer or "", "value", "true" if value else "false", context)
        elif value is None:
            emit("json_null", pointer or "", "value", "null", context)
        else:
            raise ValueError("unsupported JSON value")

    walk(data, "", [])
    return records


def _python_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _python_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def _python_accounting(candidate: Candidate, text: str,
                       parse_bundle: tuple[ast.AST, list[ast.AST], dict[ast.AST, ast.AST],
                                           list[tokenize.TokenInfo]] | None = None) -> list[dict[str, Any]]:
    tree, nodes, parents, tokens = parse_bundle or _python_parse_bundle(text, candidate.normalized_path)
    pending: list[tuple[tuple[int, int, int, int], str, list[dict[str, Any]], str]] = []
    container_cache: dict[ast.AST, tuple[dict[str, Any], ...]] = {}

    def container_chain(container: ast.AST) -> tuple[dict[str, Any], ...]:
        cached = container_cache.get(container)
        if cached is not None:
            return cached
        outer = parents.get(container)
        while outer is not None and not isinstance(
            outer, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            outer = parents.get(outer)
        prefix = container_chain(outer) if outer is not None else ()
        if isinstance(container, ast.ClassDef):
            context = _account_context("py_class", name=container.name)
        else:
            context = _account_context("py_function", name=container.name)
        cached = (*prefix, context)
        container_cache[container] = cached
        return cached

    def containers(node: ast.AST) -> list[dict[str, Any]]:
        current = parents.get(node)
        while current is not None and not isinstance(
            current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            current = parents.get(current)
        return list(container_chain(current)) if current is not None else []

    for node in nodes:
        if not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        if isinstance(node, ast.Constant) and not isinstance(node.value, str):
            continue
        if isinstance(parents.get(node), ast.JoinedStr):
            continue
        if not all(hasattr(node, name) for name in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
            raise ValueError("ACCOUNTING_PYTHON_SPAN_ERROR")
        context = containers(node)
        parent = parents.get(node)
        assignment = parent
        while assignment is not None and not isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Call)):
            assignment = parents.get(assignment)
        if isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            for target in targets:
                name = _python_name(target)
                if name:
                    context.append(_account_context("binding", name=name))
        call = parent
        while call is not None and not isinstance(call, ast.Call):
            call = parents.get(call)
        if isinstance(call, ast.Call):
            name = _python_name(call.func)
            if name:
                context.append(_account_context("call", name=name))
            call_child = node
            while parents.get(call_child) is not call and parents.get(call_child) is not None:
                call_child = parents[call_child]
            for argument_index, argument in enumerate(call.args):
                if argument is call_child:
                    context.append(_account_context("parameter_index", index=argument_index))
                    break
            else:
                for keyword in call.keywords:
                    if keyword.value is call_child:
                        context.append(_account_context("parameter_name", name=keyword.arg))
                        break
        if isinstance(node, ast.Constant):
            payload = node.value
        else:
            pieces: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    pieces.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    pieces.append("{EXPR}")
                    name = _python_name(value.value)
                    if name:
                        context.append(_account_context("formatted_binding", name=name))
            payload = "".join(pieces)
        span = (node.lineno - 1, node.col_offset, node.end_lineno - 1, node.end_col_offset)
        pending.append((span, "py_string", context, payload))
    for token in tokens:
        if token.type == tokenize.COMMENT:
            pending.append(((token.start[0] - 1, token.start[1], token.end[0] - 1, token.end[1]),
                            "py_comment", containers(tree), token.string[1:]))
    pending.sort(key=lambda item: item[0])
    return [
        _account_record(candidate, ordinal, kind, _source_locator(*span), context, payload)
        for ordinal, (span, kind, context, payload) in enumerate(pending)
        if payload.strip(" \t\n")
    ]


def _account_candidate(candidate: Candidate, *,
                       python_parse_bundle: tuple[ast.AST, list[ast.AST], dict[ast.AST, ast.AST],
                                                  list[tokenize.TokenInfo]] | None = None,
                       canonical_text: str | None = None
                       ) -> tuple[list[dict[str, Any]], Optional[Finding]]:
    try:
        text = canonical_text if canonical_text is not None else _canonical_text(candidate.raw)
        if candidate.language == "markdown":
            return _markdown_accounting(candidate, text), None
        if candidate.language == "json":
            return _json_accounting(candidate, text), None
        if candidate.language == "python":
            return _python_accounting(candidate, text, python_parse_bundle), None
        return [], _finding("ACCOUNTING_CONTRACT_MISMATCH", "accounting", "unknown language", candidate)
    except json.JSONDecodeError as exc:
        return [], _finding("ACCOUNTING_JSON_PARSE_ERROR", "accounting", str(exc), candidate)
    except (SyntaxError, tokenize.TokenError) as exc:
        return [], _finding("ACCOUNTING_PYTHON_PARSE_ERROR", "accounting", str(exc), candidate)
    except ValueError as exc:
        message = str(exc)
        code = message.split(":", 1)[0] if message.startswith("ACCOUNTING_") else "ACCOUNTING_SERIALIZATION_ERROR"
        return [], _finding(code, "accounting", message, candidate)


def _accounting_summary(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], str]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = f"{record['root_owner']}:{record['normalized_path']}"
        by_path.setdefault(key, []).append(record)
    summaries: dict[str, dict[str, Any]] = {}
    aggregate = bytearray()
    for key in sorted(by_path, key=lambda item: (item.split(":", 1)[0], item.split(":", 1)[1].encode("utf-8"))):
        serialized = _serialize_accounting_records(by_path[key])
        aggregate.extend(serialized)
        summaries[key] = {
            "unit_count": len(by_path[key]),
            "payload_bytes": sum(len(item["normalized_payload"].encode("utf-8")) for item in by_path[key]),
            "record_sha256": hashlib.sha256(serialized).hexdigest(),
        }
    return summaries, hashlib.sha256(bytes(aggregate)).hexdigest()


@dataclass
class AccountingAccumulator:
    by_path: dict[str, dict[str, Any]] = field(default_factory=dict)
    aggregate: Any = field(default_factory=hashlib.sha256)
    unit_count: int = 0
    payload_bytes: int = 0

    def add(self, candidate: Candidate, records: list[dict[str, Any]]) -> None:
        serialized = _serialize_accounting_records(records)
        key = f"{candidate.root_owner}:{candidate.normalized_path}"
        path_payload_bytes = sum(
            len(record["normalized_payload"].encode("utf-8")) for record in records
        )
        self.by_path[key] = {
            "unit_count": len(records),
            "payload_bytes": path_payload_bytes,
            "record_sha256": hashlib.sha256(serialized).hexdigest(),
        }
        self.aggregate.update(serialized)
        self.unit_count += len(records)
        self.payload_bytes += path_payload_bytes


def _semantic_units_from_accounting(candidate: Candidate,
                                    records: list[dict[str, Any]]) -> list[SemanticUnit]:
    units: list[SemanticUnit] = []
    context_hint_cache: dict[tuple[str, ...], bool] = {}
    for record in records:
        payload = record["normalized_payload"]
        context = tuple(
            str(item.get("payload") or item.get("name") or "")
            for item in record["context_chain"]
        )
        payload_hint = _has_claim_potential_hint(payload)
        if not payload_hint:
            context_hint = context_hint_cache.get(context)
            if context_hint is None:
                context_hint = any(_has_claim_potential_hint(item) for item in context if item)
                context_hint_cache[context] = context_hint
            if not context_hint or not (
                AFFIRMATIVE_RE.search(payload)
                or NEGATIVE_RE.search(payload)
                or STATE_FIELD_RE.search(payload)
            ):
                continue
        kind = record["kind"]
        if kind == "md_comment":
            provenance = "html_comment"
            unit_kind = "structured_assertion"
        elif kind == "md_table_cell":
            provenance = "markdown_table_cell"
            unit_kind = "prose"
        elif kind == "md_fence_line":
            provenance = "fence:accounted"
            unit_kind = "quoted_output"
        elif kind == "md_list_item":
            provenance = "list_item"
            unit_kind = "prose"
        elif kind == "md_heading":
            provenance = "heading:accounted"
            unit_kind = "prose"
        elif kind == "md_governance_record_cell":
            provenance = "governance_record_cell"
            unit_kind = "structured_assertion"
        else:
            provenance = "paragraph"
            unit_kind = "prose"
        locator = record["locator"]
        span = (
            int(locator["start_line"]) + 1,
            int(locator["start_column"]),
            int(locator["end_line"]) + 1,
            int(locator["end_column"]),
        )
        fragments = [payload] if kind in {"md_comment", "md_table_cell", "md_heading"} else _split_clauses(payload)
        for clause_index, fragment in enumerate(fragments, 1):
            if (len(fragments) == 1 and fragment == payload) or _contextual_claim_potential(fragment, context):
                units.append(_unit(
                    candidate, f"accounting:{record['ordinal']}:{clause_index}", span,
                    fragment, unit_kind, provenance, context=context,
                ))
    return units


def _python_semantic_units_from_accounting(candidate: Candidate,
                                           records: list[dict[str, Any]]) -> list[SemanticUnit]:
    units: list[SemanticUnit] = []
    for record in records:
        payload = record["normalized_payload"]
        context = tuple(
            str(item.get("payload") or item.get("name") or "")
            for item in record["context_chain"]
        )
        if not _contextual_claim_potential(payload, context):
            continue
        locator = record["locator"]
        span = (
            int(locator["start_line"]) + 1,
            int(locator["start_column"]),
            int(locator["end_line"]) + 1,
            int(locator["end_column"]),
        )
        context_text = "\n".join(context)
        test_context = any(item.startswith("test_") for item in context)
        proven_fixture = test_context and (
            any(
                re.search(
                    r"(?i)(?:^mutat(?:e|ion)|^corpus$|^variants?$|^samples?$|^mutations?$|^cases?$|"
                    r"write_(?:text|bytes)$|_scan$|scan_loop_runtime_claims$|_candidate$|_unit$|assert)",
                    item,
                )
                for item in context
            )
            or any(re.search(
                r"(?i)(?:reject|block|mutation|golden|historical|accounting|notice_classification)",
                item,
            ) for item in context if item.startswith("test_"))
        )
        if proven_fixture:
            provenance = "test_local_non_escaping"
        elif record["kind"] == "py_comment":
            provenance = "python_comment"
        elif re.search(r"\(\?[a-z]*[:)]|\\[AbBdDsSwWZ]|\[\^?", payload) or re.search(
            r"(?i)(?:regex|pattern|subject_patterns|affirmative_re|negative_re)", context_text
        ):
            provenance = "regex_source"
        elif re.search(
            r"(?i)(?:overclaim|claim_token|subject_hint|required_rules|noun_claim_terms|no_overclaim_boundary)",
            context_text,
        ):
            provenance = "claim_token_registry"
        elif context and context[-1].endswith(("Error", "Exception")):
            provenance = "diagnostic_message"
        else:
            provenance = "python_accounted"
        units.append(_unit(
            candidate, f"accounting:{record['ordinal']}:1", span, payload,
            "prose" if record["kind"] == "py_comment" else "data",
            provenance, context=context,
        ))
    return units


def _finding(code: str, stage: str, message: str, candidate: Candidate | None = None,
             locator: Any = None, authority_version: str = "", claim_id: str = "",
             classification: str = "") -> Finding:
    return Finding(code, stage, message,
                   candidate.root_owner if candidate else "",
                   candidate.normalized_path if candidate else "",
                   locator, authority_version, claim_id, classification)


def _safe_relative(value: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(value, str) or not value or "\\" in value:
        return None, "path must be a non-empty POSIX relative path"
    pure = PurePosixPath(value)
    if pure.is_absolute() or re.match(r"^[A-Za-z]:/", value) or any(part in {"", ".", ".."} for part in pure.parts):
        return None, "absolute, traversal and alias paths are forbidden"
    normalized = unicodedata.normalize("NFC", pure.as_posix())
    if normalized != value:
        return None, "path must already be NFC canonical"
    return normalized, None


def _safe_join_from_base(base: Path, rel: str,
                         segment_cache: Optional[dict[Path, Optional[str]]] = None) -> tuple[Optional[Path], Optional[str]]:
    path = base
    try:
        for part in PurePosixPath(rel).parts:
            path = path / part
            cached = segment_cache.get(path) if segment_cache is not None else None
            if segment_cache is not None and path in segment_cache:
                if cached:
                    return None, cached
                continue
            path_stat = path.lstat()
            attributes = getattr(path_stat, "st_file_attributes", 0)
            error = None
            if stat.S_ISLNK(path_stat.st_mode):
                error = "symlink path segment is forbidden"
            elif attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                error = "junction/reparse path segment is forbidden"
            if segment_cache is not None:
                segment_cache[path] = error
            if error:
                return None, error
        return path, None
    except (OSError, ValueError) as exc:
        if segment_cache is not None:
            segment_cache[path] = str(exc)
        return None, str(exc)


def _safe_join(root: Path, rel: str) -> tuple[Optional[Path], Optional[str]]:
    try:
        return _safe_join_from_base(root.resolve(strict=True), rel)
    except (OSError, ValueError) as exc:
        return None, str(exc)


def _load_json(root: Path, relative: PurePosixPath, kind: str) -> tuple[Optional[dict[str, Any]], list[Finding]]:
    rel, path_error = _safe_relative(relative.as_posix())
    if path_error:
        return None, [_finding(f"{kind.upper()}_PATH_INVALID", "authority", path_error)]
    path, error = _safe_join(root, rel)
    if error:
        return None, [_finding(f"{kind.upper()}_MISSING", "authority", error)]
    try:
        data = json.loads(_canonical_text(path.read_bytes()))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [_finding(f"{kind.upper()}_INVALID", "authority", str(exc))]
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        return None, [_finding(f"{kind.upper()}_SCHEMA", "authority", "schema_version must be 1.0")]
    return data, []


def _policy_digest(policy: dict[str, Any]) -> str:
    clone = dict(policy)
    return _sha_text(json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _validate_policy(policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    required_sets = ("required_paths", "historical_claims", "active_surface_rules")
    for key in required_sets:
        value = policy.get(key)
        if not isinstance(value, list) or not value:
            findings.append(_finding("POLICY_REQUIRED_SET_EMPTY", "policy", f"{key} must be a non-empty list"))
    if policy.get("notice_schema_version") != "1.0":
        findings.append(_finding("POLICY_SCHEMA", "policy", "notice_schema_version must be 1.0"))
    if _policy_digest(policy) != REQUIRED_POLICY_SHA256:
        findings.append(_finding("POLICY_CONTRACT_DIGEST_DRIFT", "policy", "policy differs from the code-owned 0.66.1 contract"))
    claim_ids: list[str] = []
    notice_ids: list[str] = []
    for entry in policy.get("historical_claims", []):
        if not isinstance(entry, dict):
            findings.append(_finding("POLICY_SCHEMA", "policy", "historical claim must be an object"))
            continue
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            findings.append(_finding("POLICY_CLAIM_ID_INVALID", "policy", "claim_id is required"))
        else:
            claim_ids.append(claim_id)
        notice_ids.append(entry.get("notice_id"))
        _, error = _safe_relative(entry.get("normalized_relative_path"))
        if error:
            findings.append(_finding("POLICY_PATH_INVALID", "policy", error))
        locator = entry.get("locator")
        if not isinstance(locator, dict) or locator.get("kind") not in {"line", "heading_block", "record", "fence"}:
            findings.append(_finding("LOCATOR_SCHEMA", "policy", "unsupported historical locator"))
        elif locator.get("kind") == "line":
            legacy_keys = frozenset({"kind", "line_number", "ordinal"})
            semantic_keys = frozenset({"kind", "selector_sha256", "ordinal"})
            locator_keys = frozenset(locator)
            if locator_keys not in {legacy_keys, semantic_keys}:
                findings.append(_finding("LOCATOR_SCHEMA", "policy", "line locator fields must be exact"))
            elif locator_keys == semantic_keys and (
                not re.fullmatch(r"[0-9a-f]{64}", str(locator.get("selector_sha256", "")))
                or locator.get("selector_sha256") != entry.get("locator_sha256")
                or locator.get("ordinal") != 1
            ):
                findings.append(_finding("LOCATOR_SCHEMA", "policy", "semantic line selector must bind locator digest and ordinal 1"))
        if not isinstance(entry.get("claim_payload"), str) or not entry.get("claim_payload"):
            findings.append(_finding("CLAIM_PAYLOAD_EMPTY", "policy", "claim_payload is required"))
        for key in ("locator_sha256", "claim_payload_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get(key, ""))):
                findings.append(_finding("POLICY_DIGEST_INVALID", "policy", f"{key} must be lowercase SHA-256"))
        if not isinstance(entry.get("occurrence_count"), int) or entry.get("occurrence_count") < 1:
            findings.append(_finding("CLAIM_OCCURRENCE_INVALID", "policy", "occurrence_count must be positive"))
        if entry.get("superseding_mode") not in {"same_file", "hot_evidence"}:
            findings.append(_finding("SUPERSEDING_MODE_INVALID", "policy", "invalid superseding_mode"))
    if len(claim_ids) != len(set(claim_ids)):
        findings.append(_finding("POLICY_DUPLICATE_CLAIM_ID", "policy", "claim ids must be unique"))
    if len(notice_ids) != len(set(notice_ids)):
        findings.append(_finding("POLICY_DUPLICATE_NOTICE_ID", "policy", "notice ids must be unique"))
    path_set = {
        f"{item.get('root_owner')}:{item.get('path')}"
        for item in policy.get("required_paths", []) if isinstance(item, dict)
    }
    if path_set != REQUIRED_PATHS:
        findings.append(_finding("POLICY_REQUIRED_PATH_SET_DRIFT", "policy", "required authority path set drift"))
    if set(claim_ids) != REQUIRED_HISTORICAL_IDS:
        findings.append(_finding("POLICY_HISTORICAL_SET_DRIFT", "policy", "historical claim set drift"))
    actual_rules = {
        rule.get("claim_class"): (rule.get("claim_id"), rule.get("status"))
        for rule in policy.get("active_surface_rules", []) if isinstance(rule, dict)
    }
    expected_rules = {claim_class: (claim_id, "forbidden_current") for claim_class, claim_id in REQUIRED_RULES.items()}
    if actual_rules != expected_rules:
        findings.append(_finding("ACTIVE_RULE_SET_DRIFT", "policy", "active rule id/class/mode set drift"))
    if any(rule.get("status") == "allowed_current" for rule in policy.get("active_surface_rules", []) if isinstance(rule, dict)):
        findings.append(_finding("ALLOWED_CURRENT_FORBIDDEN", "policy", "0.66.1 has no allowed current Loop capability rule"))
    if any(
        not isinstance(item, dict) or set(item) != {"root_owner", "path", "required"} or item.get("required") is not True
        for item in policy.get("required_paths", [])
    ):
        findings.append(_finding("POLICY_REQUIRED_PATH_SCHEMA_DRIFT", "policy", "required path records must be exact and required"))
    planned_targets = policy.get("planned_targets")
    actual_targets = {
        item.get("claim_id"): frozenset(item.get("claim_classes", []))
        for item in planned_targets or [] if isinstance(item, dict)
    }
    if not isinstance(planned_targets, list) or actual_targets != REQUIRED_PLANNED_TARGETS or any(
        set(item) != {"claim_id", "claim_classes"} for item in planned_targets if isinstance(item, dict)
    ):
        findings.append(_finding("PLANNED_TARGET_SET_DRIFT", "policy", "planned marker ownership set drift"))
    serialized = json.dumps(policy, ensure_ascii=False).lower()
    if any(token in serialized for token in ("accept-current", "accept_current", "refresh-current", "auto_update")):
        findings.append(_finding("POLICY_REFRESH_FORBIDDEN", "policy", "policy refresh controls are forbidden"))
    return findings


def _validate_authority(authority: dict[str, Any], policy: dict[str, Any]) -> list[Finding]:
    expected = {
        "effective_version": "0.66.1", "capability": "experimental_scaffolding",
        "runtime_activation": "NOT_MET", "migration_validity": "NOT_MET",
        "criteria_2_3_4_5_6": "PARTIAL", "criterion_7": "NOT_PROVEN",
        "criterion_8": "MET-NARROW", "authority_ids": ["AUDIT-133", "EVD-707", "DEC-104"],
        "open_risks": ["RISK-037", "RISK-042"],
        "identity_attestation": IDENTITY_ATTESTATION_PENDING,
    }
    findings = [_finding("AUTHORITY_DRIFT", "authority", f"{key} drift")
                for key, value in expected.items() if authority.get(key) != value]
    records = authority.get("source_records")
    if not isinstance(records, list) or not records:
        findings.append(_finding("AUTHORITY_SOURCE_RECORDS_EMPTY", "authority", "source_records must be non-empty"))
    if authority.get("policy_sha256") != _policy_digest(policy):
        findings.append(_finding("AUTHORITY_POLICY_DIGEST", "authority", "authority is not bound to policy digest"))
    record_ids = {record.get("record_id") for record in records or [] if isinstance(record, dict)}
    if record_ids != REQUIRED_SOURCE_IDS:
        findings.append(_finding("AUTHORITY_SOURCE_SET_DRIFT", "authority", "source record set drift"))
    actual_records = {
        record.get("record_id"): (record.get("path"), record.get("line_prefix"), record.get("sha256"))
        for record in records or [] if isinstance(record, dict)
    }
    if actual_records != REQUIRED_SOURCE_RECORDS or any(
        set(record) != {"record_id", "path", "line_prefix", "sha256"}
        for record in records or [] if isinstance(record, dict)
    ):
        findings.append(_finding("AUTHORITY_SOURCE_RECORD_DRIFT", "authority", "source record contract drift"))
    return findings


def _validate_source_records(context: ClaimScanContext, authority: dict[str, Any]) -> list[Finding]:
    if context.scan_mode != "product_release":
        return []
    if context.host_root is None:
        return [_finding("AUTHORITY_SOURCE_ROOT_MISSING", "authority", "product_release requires host_root")]
    findings: list[Finding] = []
    for record in authority.get("source_records", []):
        if not isinstance(record, dict):
            findings.append(_finding("AUTHORITY_SOURCE_SCHEMA", "authority", "source record must be object"))
            continue
        rel, error = _safe_relative(record.get("path"))
        if error:
            findings.append(_finding("AUTHORITY_SOURCE_PATH", "authority", error))
            continue
        path, error = _safe_join(context.host_root, rel)
        if error:
            findings.append(Finding("AUTHORITY_SOURCE_MISSING", "authority", error, "host_root", rel))
            continue
        try:
            lines = _canonical_text(path.read_bytes()).split("\n")
        except (OSError, UnicodeError) as exc:
            findings.append(Finding("AUTHORITY_SOURCE_INVALID", "authority", str(exc), "host_root", rel))
            continue
        prefix = record.get("line_prefix")
        if not isinstance(prefix, str) or not prefix:
            findings.append(Finding("AUTHORITY_SOURCE_SCHEMA", "authority", "line_prefix required", "host_root", rel))
            continue
        matches = [line for line in lines if line.startswith(prefix)]
        if len(matches) != 1:
            findings.append(Finding("AUTHORITY_SOURCE_OCCURRENCE", "authority", f"found {len(matches)}", "host_root", rel))
        elif _sha_text(matches[0]) != record.get("sha256"):
            findings.append(Finding("AUTHORITY_SOURCE_DIGEST", "authority", "source digest drift", "host_root", rel))
    return findings


def _owner_roots(context: ClaimScanContext) -> list[tuple[str, Path, tuple[str, ...]]]:
    roots = [("product_root", context.product_root, ("docs", "project", "skills"))]
    if context.host_root is not None and (context.host_root / ".governance").is_dir():
        roots.append(("host_root", context.host_root, HOT_PATHS))
    return roots


def _inventory_digest(candidates: Iterable[Candidate]) -> str:
    records = "".join(
        f"{c.root_owner}\x1f{c.normalized_path}\x1f{c.sha256}\x1f{c.raw_bytes}\n" for c in candidates
    )
    return hashlib.sha256(records.encode("utf-8")).hexdigest()


def _scanner_source_envelope_sha256(scan_mode: str, inventory: CandidateInventory,
                                    policy_sha256: str, authority_sha256: str) -> str:
    role_records: dict[str, list[dict[str, Any]]] = {role: [] for role in ROOT_ROLE_ORDER}
    for candidate in inventory.files:
        role_records[candidate.root_owner].append({
            "path": candidate.normalized_path,
            "raw_bytes": candidate.raw_bytes,
            "sha256": candidate.sha256,
        })
    bindings = []
    for role in sorted(ROOT_ROLE_ORDER, key=ROOT_ROLE_ORDER.get):
        records = role_records[role]
        if role == "plugin_home":
            records = [
                *records,
                {"path": POLICY_RELATIVE_PATH.as_posix(), "sha256": policy_sha256},
                {"path": AUTHORITY_RELATIVE_PATH.as_posix(), "sha256": authority_sha256},
            ]
        records_digest = _sha_text(json.dumps(
            records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ))
        bindings.append({"role": role, "records_digest": records_digest})
    envelope = {
        "schema_version": "loop-semantic-source-envelope/v1",
        "scan_mode": scan_mode,
        "bindings": bindings,
    }
    return _sha_text(json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ))


def _scandir_paths(root: Path, start: Path, owner: str, findings: list[Finding]) -> list[Path]:
    paths: list[Path] = []
    stack = [start]
    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            rel = unicodedata.normalize("NFC", directory.relative_to(root).as_posix())
            findings.append(Finding("PATH_SAFETY_ERROR", "enumerate", str(exc), owner, rel))
            continue
        for entry in entries:
            path = Path(entry.path)
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                rel = unicodedata.normalize("NFC", path.relative_to(root).as_posix())
                findings.append(Finding("PATH_SAFETY_ERROR", "enumerate", str(exc), owner, rel))
                continue
            rel = unicodedata.normalize("NFC", path.relative_to(root).as_posix())
            is_reparse = bool(
                getattr(entry_stat, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            )
            if entry.is_symlink() or stat.S_ISLNK(entry_stat.st_mode) or is_reparse:
                findings.append(Finding("PATH_REPARSE", "enumerate", "symlink/junction/reparse entry forbidden", owner, rel))
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif entry.is_file(follow_symlinks=False):
                paths.append(path)
    return paths


def enumerate_candidates(context: ClaimScanContext, limits: ScanLimits) -> tuple[CandidateInventory, list[Finding]]:
    findings: list[Finding] = []
    candidates: list[Candidate] = []
    seen: dict[tuple[str, str], str] = {}
    for owner, configured_root, inputs in _owner_roots(context):
        try:
            root = configured_root.resolve(strict=True)
        except OSError as exc:
            findings.append(_finding("ROOT_RESOLUTION_ERROR", "enumerate", f"{owner}: {exc}"))
            continue
        paths: list[Path] = []
        segment_cache: dict[Path, Optional[str]] = {}
        for item in inputs:
            rel, rel_error = _safe_relative(item)
            if rel_error or rel is None:
                findings.append(Finding("PATH_SAFETY_ERROR", "enumerate", rel_error or "invalid input", owner, item))
                continue
            path, path_error = _safe_join_from_base(root, rel, segment_cache)
            if path_error or path is None:
                if Path(root, *PurePosixPath(rel).parts).exists() or Path(root, *PurePosixPath(rel).parts).is_symlink():
                    findings.append(Finding("PATH_SAFETY_ERROR", "enumerate", path_error or "unsafe input", owner, rel))
                continue
            try:
                path_stat = path.lstat()
            except OSError:
                continue
            if stat.S_ISDIR(path_stat.st_mode):
                paths.extend(_scandir_paths(root, path, owner, findings))
            elif stat.S_ISREG(path_stat.st_mode):
                paths.append(path)
        for path in paths:
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                lexical_rel = unicodedata.normalize("NFC", path.relative_to(root).as_posix())
            except ValueError as exc:
                findings.append(Finding("PATH_ROOT_ESCAPE", "enumerate", str(exc), owner, str(path)))
                continue
            if not path.is_file():
                continue
            try:
                resolved, path_error = _safe_join_from_base(root, lexical_rel, segment_cache)
                if path_error or resolved is None:
                    raise OSError(path_error or "candidate path resolution failed")
                raw = resolved.read_bytes()
            except (OSError, ValueError) as exc:
                findings.append(Finding("PATH_SAFETY_ERROR", "enumerate", str(exc), owner, lexical_rel))
                continue
            key = (owner, lexical_rel.casefold())
            if key in seen and seen[key] != lexical_rel:
                findings.append(Finding("PATH_CASE_COLLISION", "enumerate", "case collision", owner, lexical_rel))
                continue
            seen[key] = lexical_rel
            digest, digest_error = _content_digest(raw, owner, lexical_rel)
            if digest_error or digest is None:
                findings.append(Finding("CONTENT_NORMALIZATION_ERROR", "enumerate", digest_error or "digest failed", owner, lexical_rel))
                continue
            candidates.append(Candidate(owner, lexical_rel, resolved, SUPPORTED_EXTENSIONS[path.suffix.lower()],
                                        raw, len(raw), digest))
    candidates.sort(key=lambda c: (ROOT_ROLE_ORDER.get(c.root_owner, 99), c.normalized_path.encode("utf-8")))
    inventory = CandidateInventory(tuple(candidates), len(candidates), sum(c.raw_bytes for c in candidates),
                                   _inventory_digest(candidates))
    if inventory.candidate_count > limits.max_candidates or inventory.candidate_bytes > limits.max_candidate_bytes:
        findings.append(_finding("CANDIDATE_BUDGET_EXCEEDED", "enumerate", "candidate budget exceeded"))
    for candidate in candidates:
        if candidate.raw_bytes > limits.max_file_bytes:
            findings.append(_finding("INPUT_TOO_LARGE", "enumerate", "per-file budget exceeded", candidate))
    return inventory, findings


SCOPED_NEGATIVE_RE = re.compile(
    r"(?ix)(?:\b(?:does\s+not|do\s+not|cannot|never).{0,120}(?:active|activate|valid|complete|implemented)|"
    r"\b(?:is\s+not|not|does\s+not|do\s+not|cannot|never)\s+"
    r"(?:(?:an?|the)\s+)?(?:activate|active|enable|enabled|complete|valid|implemented)|"
    r"不表示.{0,40}已激活|未证明.{0,120}(?:已|已经)(?:实现|接入|激活)|"
    r"不能作为.{0,60}(?:已实现|已激活|生效)|当前不生效|planned[-_ ]not[-_ ]active|"
    r"(?:\bno\b|does\s+not\s+(?:claim|declare)|do\s+not\s+(?:claim|declare)|not\s+claimed|is\s+not).{0,180}"
    r"(?:production[- ]ready|readiness|RISK-(?:037|042).{0,24}(?:closed|closure))|"
    r"(?:不声明|不构成|不是|不关闭|不沿用|不允许声明|未发现|避免声明|阻断|禁止).{0,180}"
    r"(?:production[- ]ready|正式版就绪|1\.0\.0|RISK-(?:037|042).{0,24}(?:关闭|closed|closure))|"
    r"RISK-(?:037|042).{0,40}(?:remains?\s+open|保持打开|继续打开)|"
    r"runtime_activation.{0,30}(?:false|NOT_MET)|migration_validity.{0,30}(?:NOT_MET|false)|"
    r"(?:阻断|拒绝|禁止).{0,120}(?:runtime[-_ ]activation|dynamic\s+mode|active|enabled|"
    r"production[- ]ready|readiness|risk[-_ ]closure)|"
    r"\bis\s+removed\s+or\s+bound\s+to\s+.{0,80}(?:planned[-_ ]not[-_ ]active|0\.68\.0))"
)


def _relations(text: str) -> tuple[Relation, ...]:
    semantic_text = text.replace("**", "  ")
    lowered = semantic_text.casefold()
    if not _has_claim_potential_hint(lowered):
        return ()
    subject_matches = [
        (subject, match) for subject, pattern in SUBJECT_PATTERNS.items()
        for match in pattern.finditer(semantic_text)
    ]
    domain_matches = list(re.finditer(
        r"(?i)(?:\bloop(?:[-_ ](?:engineering|runtime))?\b|loop\s*运行时|循环运行时|循环)",
        semantic_text,
    ))
    if not subject_matches and not domain_matches:
        return ()
    affirmative_spans, negative_spans = _predicate_spans(semantic_text)
    state_slots = list(re.finditer(
        r"(?i)\b(?:state|status|mode|capability|readiness|activation)\b\s*[:=]\s*[\"']?([\w-]+)",
        semantic_text,
    ))
    reviewed_state = re.compile(
        r"(?i)^(?:active|activated|enabled|complete|valid|implemented|operational|ready|met|"
        r"resolved|closed|superseded|replaced|removed|eliminated|disabled|false|not_met|"
        r"not_proven|partial|met-narrow|planned_not_active|experimental_scaffolding|proposed|"
        r"approved|approved_with_notes|blocked|ready_for_[a-z0-9_-]+|not_applicable|revised|plan|"
        r"active-classic-compatibility|schema-only-no-runtime-activation|unchanged)$"
    )
    unknown_slots = [slot for slot in state_slots if not reviewed_state.fullmatch(slot.group(1))]
    copular_patterns = (
        re.compile(
            r"\b(?P<subject>Loop(?:[-_ ]Engineering)?(?:\s+[A-Za-z][\w-]*){0,4})\s+"
            r"(?i:is|are|becomes?|remains?)\s+(?P<state>(?i:experimental[ -]scaffolding|"
            r"planned[ -]not[ -]active|[a-z][\w-]*))\b"
        ),
        re.compile(
            r"(?i)\b(?P<state>experimental[ -]scaffolding|planned[ -]not[ -]active|[a-z][\w-]*)\s+"
            r"(?:is|are|becomes?|remains?)\s+(?:the\s+)?"
            r"(?P<subject>Loop(?:[-_ ]Engineering)?(?:\s+[A-Za-z][\w-]*){0,4})\b"
        ),
    )
    unknown_copular: list[tuple[re.Match[str], str, tuple[int, int]]] = []
    for pattern in copular_patterns:
        for copular in pattern.finditer(semantic_text):
            state = copular.group("state")
            subject_phrase = copular.group("subject")
            normalized_state = re.sub(r"[ -]+", "_", state.casefold())
            suffix = semantic_text[copular.end("state"):copular.end("state") + 12]
            if (
                normalized_state in {"not", "no", "the", "a", "an"}
                or reviewed_state.fullmatch(normalized_state)
                or re.match(r"(?i)'s\s+job\b", suffix)
                or re.search(r"(?i)\b(?:guidance|documentation|document|wording|text|example|claim)\b", subject_phrase)
            ):
                continue
            unknown_copular.append((copular, normalized_state, copular.span("state")))
    unknown_relation = UNKNOWN_LOOP_RELATION_RE.search(semantic_text)
    if not subject_matches and len(domain_matches) > 1 and state_slots:
        slot = state_slots[0]
        return (Relation(
            "ambiguous_loop_domain", "ambiguous_domain_context", "unknown", "unspecified",
            domain_matches[0].span(), (slot.span(1),), tuple(negative_spans),
        ),)
    if not subject_matches and domain_matches and (unknown_relation or state_slots):
        first = domain_matches[0]
        subject_matches = [("unknown_loop_capability:" + _unknown_capability_phrase(semantic_text, first), first)]
    if not subject_matches and unknown_copular:
        copular, _state, _span = unknown_copular[0]
        subject_matches = [(
            "unknown_loop_capability:" + _unknown_capability_phrase(semantic_text, copular), copular
        )]
    if not subject_matches:
        return ()
    temporal = "historical" if re.search(r"(?i)(?:0\.65\.0|historical|历史|当时|was reported)", semantic_text) else "unspecified"
    relations: list[Relation] = []
    for subject, match in subject_matches:
        matching_unknown = next((item for item in unknown_copular if (
            item[0].start() <= match.start() <= item[0].end()
            or match.start() <= item[0].start() <= match.end() + 80
        )), None)
        if matching_unknown is not None:
            _copular, state, state_span = matching_unknown
            relations.append(Relation(
                subject, f"unknown_state:{state}", "unknown", temporal,
                match.span(), (state_span,), tuple(negative_spans),
            ))
            continue
        if unknown_slots:
            slot = unknown_slots[0]
            relations.append(Relation(
                subject, f"unknown_state:{slot.group(1)}", "unknown", temporal,
                match.span(), (slot.span(1),), tuple(negative_spans),
            ))
            continue
        subject_affirmative_spans = list(affirmative_spans)
        if subject == "risk_closure":
            subject_affirmative_spans = [
                item.span() for item in re.finditer(r"(?i)\b(?:closed|closure\s+achieved)\b|已关闭|关闭完成", text)
                if not semantic_text[max(0, item.start() - 5):item.start()].lower().endswith("fail-")
            ]
        elif subject == "criteria_completion":
            subject_affirmative_spans = [
                item.span() for item in re.finditer(
                    r"(?i)\b(?:is\s+)?(?:MET(?![-_ ]NARROW)|complete|satisfied)\b|已完成|已满足", text
                )
            ]
        structured_negative = bool(re.search(
            rf"(?i){re.escape(match.group(0))}.{{0,40}}(?:false|NOT_MET|NOT_PROVEN)", semantic_text
        ))
        clause_start = max((semantic_text.rfind(mark, 0, match.start()) for mark in ";；.!?！？"), default=-1) + 1
        clause_positions = [semantic_text.find(mark, match.end()) for mark in ";；.!?！？"]
        clause_end = min((position for position in clause_positions if position >= 0), default=len(semantic_text))
        nearby_affirmative = [
            span for span in subject_affirmative_spans
            if clause_start <= span[0] and span[1] <= clause_end and abs(span[0] - match.end()) <= 80
        ]
        unmasked_affirmative = [
            span for span in subject_affirmative_spans
            if not any(
                (negative[0] <= span[0] and span[1] <= negative[1])
                or (
                    negative[1] <= span[0]
                    and span[0] - negative[1] <= 60
                    and not re.search(r"(?i)\b(?:but|however|yet)\b|但是|但", semantic_text[negative[1]:span[0]])
                )
                for negative in negative_spans
            )
        ]
        unmasked_affirmative = [span for span in unmasked_affirmative if span in nearby_affirmative]
        if structured_negative:
            unmasked_affirmative = [span for span in unmasked_affirmative if span[0] < match.start()]
        if negative_spans and unmasked_affirmative:
            polarity = "ambiguous"
        elif unmasked_affirmative:
            polarity = "affirmative"
        elif negative_spans:
            polarity = "negative"
        else:
            polarity = "none"
        relations.append(Relation(
            subject, "capability_state", polarity, temporal, match.span(),
            tuple(nearby_affirmative), tuple(negative_spans),
        ))
    return tuple(relations)


def _unknown_capability_phrase(text: str, anchor: re.Match[str]) -> str:
    clause_start = max((text.rfind(mark, 0, anchor.start()) for mark in ";；.!?！？\n"), default=-1) + 1
    clause_positions = [text.find(mark, anchor.end()) for mark in ";；.!?！？\n"]
    clause_end = min((position for position in clause_positions if position >= 0), default=len(text))
    clause = re.sub(r"[`*_#]", " ", text[clause_start:clause_end])
    clause = re.sub(r"(?i)\b(?:is|are|was|were|becomes?|for|of|the|a|an)\b.*$", "", clause)
    phrase = re.sub(r"\s+", "_", clause.strip().casefold())[:80]
    return phrase or "unspecified"


def _predicate_spans(text: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    affirmative_spans = [match.span() for match in AFFIRMATIVE_RE.finditer(text)]
    negative_spans = [match.span() for match in SCOPED_NEGATIVE_RE.finditer(text)]
    if not negative_spans:
        negative_spans = [match.span() for match in NEGATIVE_RE.finditer(text)]
    return affirmative_spans, negative_spans


def _analyze_text(text: str) -> tuple[str, str, str, str, tuple[Relation, ...]]:
    relations = _relations(text)
    subjects = {relation.subject for relation in relations}
    polarities = {relation.polarity for relation in relations}
    subject = next(iter(subjects)) if len(subjects) == 1 else ("multiple" if subjects else "none")
    polarity = next(iter(polarities)) if len(polarities) == 1 else ("ambiguous" if polarities else "none")
    predicate = relations[0].predicate if len({relation.predicate for relation in relations}) == 1 else (
        "multiple" if relations else "mention"
    )
    temporal = relations[0].temporal_scope if relations else "unspecified"
    return subject, predicate, polarity, temporal, relations


def _unit(candidate: Candidate, locator: str, span: tuple[int, int, int, int], text: str,
          kind: str, provenance: str, state: str = "extracted",
          context: Iterable[str] = ()) -> SemanticUnit:
    canonical = unicodedata.normalize("NFC", text.strip())
    context_items = tuple(item for item in context if item)
    analysis_text = "\n".join([*context_items, canonical])
    subject, predicate, polarity, temporal, relations = _analyze_text(analysis_text)
    return SemanticUnit(candidate.root_owner, candidate.normalized_path, candidate.language,
                        locator, span, _sha_text(canonical), canonical, kind, provenance,
                        subject, predicate, polarity, temporal, state,
                        "\n".join(context_items), relations=relations)


def _split_clauses(text: str) -> list[str]:
    return [part.strip() for part in CLAUSE_SPLIT_RE.split(text) if part.strip()]


def _has_claim_potential_hint(value: str) -> bool:
    folded = value.casefold()
    return bool(
        SUBJECT_HINT_RE.search(folded)
        or "loop-runtime-target:" in folded
        or "loop-runtime-superseding:" in folded
    )


def _claim_potential_hint(text: str, context: Iterable[str] = ()) -> bool:
    return _has_claim_potential_hint(text) or any(
        _has_claim_potential_hint(item) for item in context if item
    )


def _contextual_claim_potential(text: str, context: tuple[str, ...]) -> bool:
    if _has_claim_potential_hint(text):
        return True
    if not any(_has_claim_potential_hint(item) for item in context if item):
        return False
    return bool(
        AFFIRMATIVE_RE.search(text)
        or NEGATIVE_RE.search(text)
        or STATE_FIELD_RE.search(text)
    )


def _markdown_units(candidate: Candidate, text: str) -> list[SemanticUnit]:
    units: list[SemanticUnit] = []
    lines = text.split("\n")
    fence: Optional[tuple[str, str, int, list[str]]] = None
    heading_stack: list[tuple[int, str]] = []

    def add(locator: str, span: tuple[int, int, int, int], payload: str,
            kind: str, provenance: str, state: str = "extracted") -> None:
        context = tuple(value for _, value in heading_stack)
        if _claim_potential_hint(payload, context):
            units.append(_unit(candidate, locator, span, payload, kind, provenance, state, context))
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        fence_match = re.match(r"^(```+|~~~+)\s*([^\s]*)", stripped)
        if fence is not None:
            delimiter, language, start, body = fence
            if stripped.startswith(delimiter[0] * len(delimiter)):
                content = "\n".join(body)
                state = "extracted" if language in {"python", "py", "json", "ndjson", "text", "", "markdown", "md", "html"} else (
                    "ambiguous" if any(pattern.search(content) for pattern in SUBJECT_PATTERNS.values()) else "extracted"
                )
                if state == "ambiguous":
                    add(f"fence:{start}:{number}", (start, 0, number, len(line)), content,
                        "quoted_output", f"fence:{language or 'unlabelled'}", state)
                else:
                    for offset, body_line in enumerate(body, start + 1):
                        for clause_index, clause in enumerate(_split_clauses(body_line), 1):
                            add(f"fence:{start}:{offset}:{clause_index}",
                                (offset, 0, offset, len(body_line)), clause,
                                "quoted_output", f"fence:{language or 'unlabelled'}")
                fence = None
            else:
                body.append(line)
            continue
        if fence_match:
            fence = (fence_match.group(1), fence_match.group(2).lower(), number, [])
            continue
        if not stripped:
            continue
        comment = re.fullmatch(r"<!--\s*(.*?)\s*-->", stripped)
        if comment:
            add(f"comment:{number}", (number, 0, number, len(line)), comment.group(1),
                "structured_assertion", "html_comment")
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = stripped.strip("|").split("|")
            for index, cell in enumerate(cells, 1):
                if cell.strip():
                    add(f"table:{number}:{index}:1", (number, 0, number, len(line)), cell,
                        "prose", "markdown_table_cell")
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            add(f"heading:{number}", (number, 0, number, len(line)), heading.group(2),
                "prose", f"heading:{level}")
            heading_stack.append((level, heading.group(2).strip()))
            continue
        body = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        list_item = body != stripped
        heading_context = heading_stack[-1][1].casefold() if heading_stack else ""
        provenance = "control_condition" if list_item and heading_context in {
            "triggers", "rollback triggers", "触发条件", "回滚触发条件",
        } else ("list_item" if list_item else "paragraph")
        for index, clause in enumerate(_split_clauses(body), 1):
            add(f"clause:{number}:{index}", (number, 0, number, len(line)), clause,
                "prose", provenance)
    if fence is not None:
        raise ValueError(f"unclosed Markdown fence at line {fence[2]}")
    return units


@dataclass
class PythonProvenanceIndex:
    doc_nodes: set[ast.Constant]
    nearest_function: dict[ast.AST, ast.AST | None]
    enclosing_test: dict[ast.AST, ast.AST | None]
    nearest_call: dict[ast.AST, ast.Call | None]
    nearest_assignment: dict[ast.AST, ast.AST | None]
    nearest_collection: dict[ast.AST, ast.AST | None]
    nearest_tuple: dict[ast.AST, ast.Tuple | None]
    regex_ancestors: set[ast.AST]
    safe_name_uses: dict[tuple[ast.AST, str], tuple[int, bool]]
    proven_fixture_tests: set[ast.AST]
    isolated_fixture_callbacks: set[ast.AST]
    operation_count: int


def _is_regex_compile(call: ast.Call | None) -> bool:
    return bool(
        call
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "compile"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "re"
    )


def _is_fixture_sink(call: ast.Call | None) -> bool:
    if call is None:
        return False
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in {
            "enumerate", "len", "str", "repr", "sorted", "scan_loop_runtime_claims",
            "_unit", "_historical_consumption", "_account_candidate",
        }
    if not isinstance(func, ast.Attribute):
        return False
    return (
        func.attr in {
            "write_text", "write_bytes", "dumps", "encode", "subTest", "sha256", "replace",
            "items", "values", "_scan", "_candidate", "_unit", "_historical_consumption",
            "_account_candidate",
        }
        or func.attr.startswith("assert")
    )


def _assignment_names(node: ast.AST | None) -> set[str]:
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return set()
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _build_python_provenance_index(nodes: list[ast.AST], parents: dict[ast.AST, ast.AST]) -> PythonProvenanceIndex:
    nearest_function: dict[ast.AST, ast.AST | None] = {}
    enclosing_test = nearest_function
    nearest_call: dict[ast.AST, ast.Call | None] = {}
    nearest_assignment: dict[ast.AST, ast.AST | None] = {}
    nearest_collection: dict[ast.AST, ast.AST | None] = {}
    nearest_tuple: dict[ast.AST, ast.Tuple | None] = {}
    nearest_escape: dict[ast.AST, ast.AST | None] = {}
    doc_nodes: set[ast.Constant] = set()
    operation_count = 0
    regex_ancestors: set[ast.AST] = set()
    for node in nodes:
        operation_count += 1
        parent = parents.get(node)
        inherited_function = nearest_function.get(parent)
        inherited_call = nearest_call.get(parent)
        inherited_assignment = nearest_assignment.get(parent)
        inherited_collection = nearest_collection.get(parent)
        inherited_tuple = nearest_tuple.get(parent)
        inherited_escape = nearest_escape.get(parent)
        is_function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        current_function = node if is_function else inherited_function
        current_call = node if isinstance(node, ast.Call) else inherited_call
        current_assignment = node if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) else inherited_assignment
        current_collection = node if isinstance(node, (ast.List, ast.Tuple)) else inherited_collection
        current_tuple = node if isinstance(node, ast.Tuple) else inherited_tuple
        current_escape = node if isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom)) else inherited_escape
        nearest_function[node] = current_function
        nearest_call[node] = current_call
        nearest_assignment[node] = current_assignment
        nearest_collection[node] = current_collection
        nearest_tuple[node] = current_tuple
        nearest_escape[node] = current_escape
        if isinstance(node, ast.Call) and _is_regex_compile(node):
            regex_ancestors.add(node)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc_nodes.add(first.value)
    name_uses: dict[tuple[ast.AST, str], list[Any]] = {}
    function_symbol_uses: dict[tuple[ast.AST | None, str], list[ast.Name]] = {}
    test_calls: dict[ast.AST, set[str]] = {}
    for node in nodes:
        operation_count += 1
        test_function = enclosing_test.get(node)
        if isinstance(node, ast.Call) and test_function is not None:
            call_name = _python_name(node.func) or ""
            test_calls.setdefault(test_function, set()).add(call_name.rsplit(".", 1)[-1])
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        function_symbol_uses.setdefault((nearest_function.get(node), node.id), []).append(node)
        if test_function is None or nearest_function.get(node) is not test_function:
            continue
        parent = parents.get(node)
        safe = nearest_escape.get(node) is None and (
            _is_fixture_sink(nearest_call.get(node))
            or (isinstance(parent, ast.For) and parent.iter is node)
        )
        record = name_uses.setdefault((test_function, node.id), [0, True])
        record[0] += 1
        record[1] = record[1] and safe
    safe_name_uses = {key: (value[0], value[1]) for key, value in name_uses.items()}
    proven_fixture_tests = {
        test for test, calls in test_calls.items()
        if any(name.startswith("assert") for name in calls)
        and any(name.startswith("check_") or name in {
            "_scan", "scan_loop_runtime_claims", "_write_registry", "_write_runtime",
            "_account_candidate", "_historical_consumption",
        } for name in calls)
    }
    unsafe_fixture_functions = {
        nearest_function.get(node) for node in nodes
        if isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal))
    }
    isolated_fixture_callbacks: set[ast.AST] = set()
    for function in nodes:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        outer = nearest_function.get(parents.get(function))
        if outer not in proven_fixture_tests:
            continue
        if function in unsafe_fixture_functions:
            continue
        uses = function_symbol_uses.get((outer, function.name), [])
        if len(uses) != 1:
            continue
        current: ast.AST | None = uses[0]
        keyword_name = ""
        call: ast.Call | None = None
        while current is not None and current is not outer:
            parent = parents.get(current)
            if isinstance(parent, ast.keyword) and parent.value is current:
                keyword_name = parent.arg or ""
            if isinstance(parent, ast.Call):
                call = parent
                break
            current = parent
        call_name = (_python_name(call.func) if call is not None else "") or ""
        if keyword_name in {"mutate", "manifest_mutate"} and call_name.rsplit(".", 1)[-1] in {
            "_write_registry", "_write_runtime",
        }:
            isolated_fixture_callbacks.add(function)
    return PythonProvenanceIndex(
        doc_nodes, nearest_function, enclosing_test, nearest_call, nearest_assignment,
        nearest_collection, nearest_tuple, regex_ancestors, safe_name_uses,
        proven_fixture_tests, isolated_fixture_callbacks, operation_count,
    )


def _build_python_claim_provenance_index(
    nodes: list[ast.AST], parents: dict[ast.AST, ast.AST]
) -> tuple[PythonProvenanceIndex, list[tuple[ast.Constant, list[tuple[int, str]], tuple[str, ...]]]]:
    nearest_function: dict[ast.AST, ast.AST | None] = {}
    operation_count = 0
    for node in nodes:
        operation_count += 1
        nearest_function[node] = (
            node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            else nearest_function.get(parents.get(node))
        )

    doc_nodes: set[ast.Constant] = set()
    nearest_call: dict[ast.AST, ast.Call | None] = {}
    nearest_assignment: dict[ast.AST, ast.AST | None] = {}
    nearest_collection: dict[ast.AST, ast.AST | None] = {}
    nearest_tuple: dict[ast.AST, ast.Tuple | None] = {}
    claim_nodes: list[tuple[ast.Constant, list[tuple[int, str]], tuple[str, ...]]] = []
    needed_name_uses: set[tuple[ast.AST, str]] = set()
    target_functions: set[ast.AST] = set()
    context_hint_cache: dict[tuple[str, ...], bool] = {}
    for node in nodes:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        operation_count += 1
        assignment: ast.AST | None = None
        call: ast.Call | None = None
        collection: ast.AST | None = None
        tuple_ancestor: ast.Tuple | None = None
        current = parents.get(node)
        while current is not None:
            operation_count += 1
            if assignment is None and isinstance(current, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                assignment = current
            if call is None and isinstance(current, ast.Call):
                call = current
            if collection is None and isinstance(current, (ast.List, ast.Tuple)):
                collection = current
            if tuple_ancestor is None and isinstance(current, ast.Tuple):
                tuple_ancestor = current
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
            current = parents.get(current)
        assigned_names = _assignment_names(assignment)
        function = nearest_function.get(node)
        semantic_context = [*assigned_names]
        if function is not None and hasattr(function, "name"):
            semantic_context.append(function.name)
        if call is not None:
            call_name = _python_name(call.func)
            if call_name:
                semantic_context.append(call_name)
        semantic_context_tuple = tuple(semantic_context)
        expression = parents.get(node)
        container = parents.get(expression) if isinstance(expression, ast.Expr) else None
        is_doc = bool(
            isinstance(expression, ast.Expr)
            and isinstance(container, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and container.body
            and container.body[0] is expression
        )
        clauses = _split_clauses(node.value) if is_doc else [node.value]
        context_hint = context_hint_cache.get(semantic_context_tuple)
        if context_hint is None:
            context_hint = any(
                _has_claim_potential_hint(item) for item in semantic_context_tuple if item
            )
            context_hint_cache[semantic_context_tuple] = context_hint
        relevant_clauses = []
        for clause_index, clause in enumerate(clauses, 1):
            if _has_claim_potential_hint(clause) or context_hint and (
                AFFIRMATIVE_RE.search(clause)
                or NEGATIVE_RE.search(clause)
                or STATE_FIELD_RE.search(clause)
            ):
                relevant_clauses.append((clause_index, clause))
        if not relevant_clauses:
            continue
        if is_doc:
            doc_nodes.add(node)
        nearest_call[node] = call
        nearest_assignment[node] = assignment
        nearest_collection[node] = collection
        nearest_tuple[node] = tuple_ancestor
        claim_nodes.append((node, relevant_clauses, semantic_context_tuple))
        if function is not None:
            target_functions.add(function)
            needed_name_uses.update((function, name) for name in assigned_names)

    outer_functions = {
        function: nearest_function.get(parents.get(function))
        for function in target_functions
    }
    functions_of_interest = target_functions | {
        outer for outer in outer_functions.values() if outer is not None
    }
    test_calls: dict[ast.AST, set[str]] = {}
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        function = nearest_function.get(node)
        if function not in functions_of_interest:
            continue
        operation_count += 1
        call_name = _python_name(node.func) or ""
        test_calls.setdefault(function, set()).add(call_name.rsplit(".", 1)[-1])
    proven_fixture_tests = {
        test for test, calls in test_calls.items()
        if any(name.startswith("assert") for name in calls)
        and any(name.startswith("check_") or name in {
            "_scan", "scan_loop_runtime_claims", "_write_registry", "_write_runtime",
            "_account_candidate", "_historical_consumption",
        } for name in calls)
    }

    name_uses: dict[tuple[ast.AST, str], list[Any]] = {}
    for node in nodes:
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        function = nearest_function.get(node)
        key = (function, node.id)
        if key not in needed_name_uses:
            continue
        operation_count += 1
        escape: ast.AST | None = None
        call: ast.Call | None = None
        current = parents.get(node)
        while current is not None and current is not function:
            operation_count += 1
            if escape is None and isinstance(current, (ast.Return, ast.Yield, ast.YieldFrom)):
                escape = current
            if call is None and isinstance(current, ast.Call):
                call = current
            current = parents.get(current)
        parent = parents.get(node)
        safe = escape is None and (
            _is_fixture_sink(call)
            or (isinstance(parent, ast.For) and parent.iter is node)
        )
        record = name_uses.setdefault(key, [0, True])
        record[0] += 1
        record[1] = record[1] and safe
    safe_name_uses = {key: (value[0], value[1]) for key, value in name_uses.items()}

    callback_candidates = {
        function for function, outer in outer_functions.items()
        if outer in proven_fixture_tests
    }
    unsafe_fixture_functions = {
        nearest_function.get(node) for node in nodes
        if isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal))
        and nearest_function.get(node) in callback_candidates
    }
    callback_use_keys = {
        (outer_functions[function], function.name): function
        for function in callback_candidates
        if function not in unsafe_fixture_functions
    }
    function_symbol_uses: dict[tuple[ast.AST | None, str], list[ast.Name]] = {}
    for node in nodes:
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        key = (nearest_function.get(node), node.id)
        if key in callback_use_keys:
            function_symbol_uses.setdefault(key, []).append(node)
    isolated_fixture_callbacks: set[ast.AST] = set()
    for key, function in callback_use_keys.items():
        uses = function_symbol_uses.get(key, [])
        if len(uses) != 1:
            continue
        outer = outer_functions[function]
        current: ast.AST | None = uses[0]
        keyword_name = ""
        call: ast.Call | None = None
        while current is not None and current is not outer:
            parent = parents.get(current)
            if isinstance(parent, ast.keyword) and parent.value is current:
                keyword_name = parent.arg or ""
            if isinstance(parent, ast.Call):
                call = parent
                break
            current = parent
        call_name = (_python_name(call.func) if call is not None else "") or ""
        if keyword_name in {"mutate", "manifest_mutate"} and call_name.rsplit(".", 1)[-1] in {
            "_write_registry", "_write_runtime",
        }:
            isolated_fixture_callbacks.add(function)

    return PythonProvenanceIndex(
        doc_nodes, nearest_function, nearest_function, nearest_call, nearest_assignment,
        nearest_collection, nearest_tuple, set(), safe_name_uses,
        proven_fixture_tests, isolated_fixture_callbacks, operation_count,
    ), claim_nodes


def _python_parse_bundle(text: str, normalized_path: str) -> tuple[
    ast.AST, list[ast.AST], dict[ast.AST, ast.AST], list[tokenize.TokenInfo]
]:
    tree = ast.parse(text, filename=normalized_path)
    tokens = [] if "#" not in text else [
        token for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type == tokenize.COMMENT
    ]
    nodes: list[ast.AST] = []
    parents: dict[ast.AST, ast.AST] = {}
    stack = [tree]
    while stack:
        parent = stack.pop()
        nodes.append(parent)
        children: list[ast.AST] = []
        for field_name in parent._fields:
            value = getattr(parent, field_name, None)
            if isinstance(value, ast.AST):
                children.append(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, ast.AST):
                        children.append(child)
        for child in children:
            parents[child] = parent
        for child in reversed(children):
            stack.append(child)
    return tree, nodes, parents, tokens


def _inside_blocking_assertion(node: ast.AST, function: ast.AST | None,
                               parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST | None = node
    while current is not None and current is not function:
        current = parents.get(current)
        if isinstance(current, (ast.Return, ast.Yield, ast.YieldFrom)):
            return False
        if isinstance(current, ast.Call):
            name = (_python_name(current.func) or "").rsplit(".", 1)[-1]
            if name.startswith("assert"):
                return True
    return False


def _python_units(candidate: Candidate, text: str,
                  parse_bundle: tuple[ast.AST, list[ast.AST], dict[ast.AST, ast.AST],
                                      list[tokenize.TokenInfo]] | None = None,
                  claim_potential_only: bool = False) -> list[SemanticUnit]:
    _tree, nodes, parents, tokens = parse_bundle or _python_parse_bundle(text, candidate.normalized_path)
    if claim_potential_only:
        index, claim_nodes = _build_python_claim_provenance_index(nodes, parents)
    else:
        index = _build_python_provenance_index(nodes, parents)
        claim_nodes = []
        for node in nodes:
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            assigned_names = _assignment_names(index.nearest_assignment.get(node))
            semantic_context = [*assigned_names]
            nearest_function = index.nearest_function.get(node)
            if nearest_function is not None and hasattr(nearest_function, "name"):
                semantic_context.append(nearest_function.name)
            direct_call = index.nearest_call.get(node)
            if isinstance(direct_call, ast.Call):
                call_name = _python_name(direct_call.func)
                if call_name:
                    semantic_context.append(call_name)
            clauses = _split_clauses(node.value) if node in index.doc_nodes else [node.value]
            claim_nodes.append((
                node,
                [(clause_index, clause) for clause_index, clause in enumerate(clauses, 1)],
                tuple(semantic_context),
            ))
    units: list[SemanticUnit] = []
    for node, relevant_clauses, semantic_context_tuple in claim_nodes:
        nearest_function = index.nearest_function.get(node)
        test_function = index.enclosing_test.get(node)
        assignment = index.nearest_assignment.get(node)
        assigned_names = _assignment_names(assignment)
        direct_call = index.nearest_call.get(node)
        provenance = "string_literal"
        kind = "prose"
        if node in index.doc_nodes:
            provenance = "docstring"
        else:
            tuple_ancestor = index.nearest_tuple.get(node)
            collection_ancestor = index.nearest_collection.get(node)
            if tuple_ancestor in index.regex_ancestors:
                kind, provenance = "data", "regex_source"
            if collection_ancestor is not None and re.fullmatch(
                r"(?i)(?:risk-(?:036|037|042) (?:closed|closure achieved)|1\.0\.0 production-ready(?: claim)?)",
                node.value,
            ):
                kind, provenance = "data", "claim_token_registry"
            if _is_regex_compile(direct_call):
                kind, provenance = "data", "regex_source"
            if (
                direct_call
                and isinstance(direct_call.func, ast.Name)
                and direct_call.func.id.endswith(("Error", "Exception"))
            ):
                kind, provenance = "data", "diagnostic_message"
            if test_function is not None and kind not in {"data", "fixture"}:
                direct_fixture = (
                    _is_fixture_sink(direct_call) or _inside_blocking_assertion(node, test_function, parents)
                ) and test_function in index.proven_fixture_tests
                named_fixture = bool(assigned_names) and all(
                    index.safe_name_uses.get((test_function, name), (0, False))[0] > 0
                    and index.safe_name_uses.get((test_function, name), (0, False))[1]
                    for name in assigned_names
                )
                if direct_fixture or (nearest_function is test_function and named_fixture):
                    kind, provenance = "fixture", "test_local_non_escaping"
                elif test_function in index.isolated_fixture_callbacks:
                    kind, provenance = "fixture", "test_local_non_escaping"
                else:
                    provenance = "test_assignment_escaping_or_ambiguous"
            elif test_function is None and kind not in {"data", "fixture"} and (
                assignment is not None or direct_call is not None
            ):
                provenance = "test_assignment_escaping_or_ambiguous"
        for clause_index, clause in relevant_clauses:
            units.append(_unit(candidate, f"ast:string:{node.lineno}:{node.col_offset}:{clause_index}",
                               (node.lineno, node.col_offset, getattr(node, "end_lineno", node.lineno),
                                getattr(node, "end_col_offset", node.col_offset)), clause, kind, provenance,
                               context=semantic_context_tuple))
    for token in tokens:
        if token.type == tokenize.COMMENT:
            if not claim_potential_only or _claim_potential_hint(token.string[1:]):
                units.append(_unit(candidate, f"comment:{token.start[0]}:{token.start[1]}",
                                   (token.start[0], token.start[1], token.end[0], token.end[1]),
                                   token.string[1:], "prose", "python_comment"))
    return units


def _json_units(candidate: Candidate, text: str) -> list[SemanticUnit]:
    data = json.loads(text)
    units: list[SemanticUnit] = []
    policy_schema = (
        candidate.root_owner == "product_root"
        and candidate.normalized_path == "skills/software-project-governance/core/loop-runtime-claim-allowlist.json"
        and isinstance(data, dict)
        and all(key in data for key in ("historical_claims", "active_surface_rules"))
    )
    authority_schema = (
        candidate.root_owner == "product_root"
        and candidate.normalized_path == "skills/software-project-governance/core/loop-runtime-claim-authority.json"
        and isinstance(data, dict)
        and all(key in data for key in ("authority_ids", "source_records"))
    )

    def walk(value: Any, pointer: str, parent_key: str = "", context: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, f"{pointer}/{escaped}", str(key), (*context, str(key)))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{pointer}/{index}", parent_key, (*context, str(index)))
        else:
            rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            state_field = parent_key.casefold() in {
                "state", "status", "mode", "capability", "readiness", "activation",
            }
            loop_context = any(_has_claim_potential_hint(item) for item in context[:-1])
            assertion = (
                parent_key in SUBJECT_PATTERNS
                or parent_key in {"runtime_activation", "migration_validity"}
                or (state_field and loop_context)
            )
            content = f"{parent_key}: {rendered}" if assertion else str(rendered)
            schema_role = (policy_schema and parent_key in {
                "claim_id", "notice_id", "normalized_relative_path", "claim_payload",
                "claim_payload_sha256", "locator_sha256", "claim_class", "status",
            }) or (authority_schema and parent_key in {
                "record_id", "path", "line_prefix", "sha256", "policy_sha256", "authority_ids",
                "effective_version", "capability", "runtime_activation", "migration_validity",
                "criteria_2_3_4_5_6", "criterion_7", "criterion_8", "open_risks",
            })
            if _claim_potential_hint(content, context):
                units.append(_unit(candidate, f"json:{pointer or '/'}", (1, 0, 1, 0), content,
                                   "data" if schema_role else ("structured_assertion" if assertion else "data"),
                                   ("json_schema_role" if schema_role else f"json_pointer:{pointer or '/'}"),
                                   context=context))
    walk(data, "")
    return units


def extract_semantic_units(candidate: Candidate, *,
                           python_parse_bundle: tuple[ast.AST, list[ast.AST], dict[ast.AST, ast.AST],
                                                      list[tokenize.TokenInfo]] | None = None,
                           claim_potential_only: bool = False,
                           canonical_text: str | None = None
                           ) -> tuple[list[SemanticUnit], Optional[Finding]]:
    try:
        text = canonical_text if canonical_text is not None else _canonical_text(candidate.raw)
        digest, digest_error = _canonical_content_digest(
            text, candidate.root_owner, candidate.normalized_path
        )
        if digest_error or digest != candidate.sha256:
            return [], _finding("CANDIDATE_SNAPSHOT_MISMATCH", "parse", "enumerated bytes changed", candidate)
        if candidate.language == "markdown":
            return _markdown_units(candidate, text), None
        if candidate.language == "python":
            return _python_units(candidate, text, python_parse_bundle, claim_potential_only), None
        return _json_units(candidate, text), None
    except UnicodeError as exc:
        return [], _finding("DECODE_ERROR", "parse", str(exc), candidate)
    except (SyntaxError, json.JSONDecodeError, ValueError) as exc:
        return [], _finding("PARSE_ERROR", "parse", str(exc), candidate)


def _resolve_locator(text: str, locator: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    kind = locator.get("kind")
    lines = text.split("\n")
    if kind == "line":
        selector_sha256 = locator.get("selector_sha256")
        if selector_sha256 is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", str(selector_sha256)) or locator.get("ordinal", 1) != 1:
                return None, "LOCATOR_SCHEMA: semantic line selector requires 64hex and ordinal 1"
            matches = [line for line in lines if _sha_text(line) == selector_sha256]
            if not matches:
                return None, "LOCATOR_UNRESOLVED: semantic line selector matched zero lines"
            if len(matches) != 1:
                return None, f"LOCATOR_AMBIGUOUS: semantic line selector matched {len(matches)} lines"
            return matches[0], None
        number = locator.get("line_number")
        if not isinstance(number, int) or number < 1 or number > len(lines):
            return None, "LOCATOR_UNRESOLVED: line locator unresolved"
        return lines[number - 1], None
    if kind == "heading_block":
        level, heading, ordinal = locator.get("heading_level"), locator.get("heading_text"), locator.get("ordinal", 1)
        matches = [i for i, line in enumerate(lines) if line == f"{'#' * level} {heading}"] if isinstance(level, int) else []
        if len(matches) < ordinal or ordinal < 1:
            return None, "LOCATOR_UNRESOLVED: heading locator unresolved"
        start = matches[ordinal - 1]
        end = len(lines)
        for i in range(start + 1, len(lines)):
            match = re.match(r"^(#{1,6})\s+", lines[i])
            if match and len(match.group(1)) <= level:
                end = i
                break
        return "\n".join(lines[start:end]), None
    if kind == "record":
        record_id, ordinal = locator.get("record_id"), locator.get("ordinal", 1)
        matches = [line for line in lines if line.startswith(f"| {record_id} |")]
        if len(matches) < ordinal or ordinal < 1:
            return None, "LOCATOR_UNRESOLVED: record locator unresolved"
        return matches[ordinal - 1], None
    if kind == "fence":
        language, ordinal = locator.get("language", ""), locator.get("ordinal", 1)
        pattern = re.compile(rf"^```{re.escape(language)}\s*$.*?^```\s*$", re.MULTILINE | re.DOTALL)
        matches = pattern.findall(text)
        if len(matches) < ordinal or ordinal < 1:
            return None, "LOCATOR_UNRESOLVED: fence locator unresolved"
        return matches[ordinal - 1], None
    return None, "LOCATOR_SCHEMA: unsupported locator"


def _validate_historical_and_notices(context: ClaimScanContext, policy: dict[str, Any],
                                     candidates: dict[tuple[str, str], Candidate]) -> tuple[set[tuple[str, str, str]], int, list[Finding]]:
    owned: set[tuple[str, str, str]] = set()
    findings: list[Finding] = []
    if context.scan_mode == "installed_host":
        return owned, 0, findings
    expected_notice_ids = {entry["notice_id"] for entry in policy.get("historical_claims", []) if isinstance(entry, dict)}
    seen_notices: dict[str, tuple[str, dict[str, Any]]] = {}
    for (owner, rel), candidate in candidates.items():
        if owner != "product_root" or candidate.language != "markdown":
            continue
        text = _canonical_text(candidate.raw)
        outside: list[str] = []
        fence_delimiter = ""
        for line in text.split("\n"):
            match = re.match(r"^\s*(```+|~~~+)", line)
            if match:
                if not fence_delimiter:
                    fence_delimiter = match.group(1)
                elif line.strip().startswith(fence_delimiter[0] * len(fence_delimiter)):
                    fence_delimiter = ""
                continue
            if not fence_delimiter:
                outside.append(line)
        for raw in NOTICE_RE.findall("\n".join(outside)):
            try:
                notice = json.loads(raw)
            except json.JSONDecodeError as exc:
                findings.append(_finding("NOTICE_INVALID", "policy", str(exc), candidate))
                continue
            notice_id = notice.get("notice_id")
            if notice_id in seen_notices:
                findings.append(_finding("NOTICE_DUPLICATE", "policy", f"duplicate notice {notice_id}", candidate))
            elif not isinstance(notice_id, str) or notice_id not in expected_notice_ids:
                findings.append(_finding("NOTICE_ORPHAN", "policy", f"orphan notice {notice_id}", candidate))
            else:
                seen_notices[notice_id] = (rel, notice)
    for entry in policy.get("historical_claims", []):
        rel = entry.get("normalized_relative_path")
        candidate = candidates.get(("product_root", rel))
        if candidate is None:
            findings.append(Finding("REQUIRED_PATH_MISSING", "policy", "historical path missing", "product_root", rel or ""))
            continue
        text = _canonical_text(candidate.raw)
        entity, error = _resolve_locator(text, entry.get("locator", {}))
        if error:
            code, _, detail = error.partition(":")
            findings.append(_finding(
                code if code.startswith("LOCATOR_") else "LOCATOR_UNRESOLVED",
                "policy", detail.strip() or error, candidate,
                locator=entry.get("locator"), claim_id=entry.get("claim_id", ""),
            ))
            continue
        if _sha_text(entity) != entry.get("locator_sha256"):
            findings.append(_finding(
                "LOCATOR_DIGEST_DRIFT", "policy", "locator digest drift", candidate,
                locator=entry.get("locator"), claim_id=entry.get("claim_id", ""),
            ))
        payload = unicodedata.normalize("NFC", entry.get("claim_payload", ""))
        if _sha_text(payload) != entry.get("claim_payload_sha256"):
            findings.append(_finding(
                "CLAIM_PAYLOAD_DIGEST_DRIFT", "policy", "policy payload digest drift", candidate,
                locator=entry.get("locator"), claim_id=entry.get("claim_id", ""),
            ))
        occurrence = entity.count(payload)
        if occurrence != entry.get("occurrence_count"):
            findings.append(_finding(
                "CLAIM_OCCURRENCE_DRIFT", "policy", f"expected {entry.get('occurrence_count')}, found {occurrence}", candidate,
                locator=entry.get("locator"), claim_id=entry.get("claim_id", ""),
            ))
        notice_tuple = seen_notices.get(entry.get("notice_id"))
        if not notice_tuple:
            findings.append(_finding("NOTICE_MISSING", "policy", "bound notice missing", candidate))
        else:
            notice_rel, notice = notice_tuple
            expected = {
                "schema_version": "1.0", "effective_version": "0.66.1",
                "authority_ids": ["AUDIT-133", "EVD-707", "DEC-104"],
                "open_risks": ["RISK-037", "RISK-042"],
                "classification": {
                    "runtime_activation": "NOT_MET", "migration_validity": "NOT_MET",
                    "criteria_2_3_4_5_6": "PARTIAL", "criterion_7": "NOT_PROVEN",
                    "criterion_8": "MET-NARROW", "capability": "experimental_scaffolding",
                },
            }
            exact_keys = {
                "schema_version", "notice_id", "effective_version", "supersedes_claim_ids",
                "authority_ids", "classification", "open_risks",
            }
            if notice_rel != rel or set(notice) != exact_keys or any(notice.get(key) != value for key, value in expected.items()):
                findings.append(_finding("NOTICE_BINDING_DRIFT", "policy", "notice/path/authority drift", candidate))
            if notice.get("notice_id") != entry.get("notice_id"):
                findings.append(_finding("NOTICE_BINDING_DRIFT", "policy", "notice id binding drift", candidate))
            supersedes = notice.get("supersedes_claim_ids")
            if supersedes != [entry.get("claim_id")]:
                findings.append(_finding("NOTICE_BINDING_DRIFT", "policy", "notice claim binding drift", candidate))
        locator_key = json.dumps(entry.get("locator"), sort_keys=True, separators=(",", ":"))
        owned.add((rel, locator_key, entry.get("claim_payload_sha256", "")))
    return owned, len(seen_notices), findings


def _validate_required_paths(context: ClaimScanContext, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    roots = {"product_root": context.product_root, "plugin_home": context.plugin_home, "host_root": context.host_root}
    seen: set[tuple[str, str]] = set()
    for item in policy.get("required_paths", []):
        if not isinstance(item, dict):
            findings.append(_finding("POLICY_SCHEMA", "policy", "required path must be object"))
            continue
        owner = item.get("root_owner")
        rel, error = _safe_relative(item.get("path"))
        if error or owner not in roots:
            findings.append(_finding("POLICY_PATH_INVALID", "policy", error or "unknown root owner"))
            continue
        key = (owner, rel)
        if key in seen:
            findings.append(_finding("POLICY_DUPLICATE_PATH", "policy", f"duplicate {key}"))
            continue
        seen.add(key)
        if context.scan_mode == "installed_host" and owner == "product_root" and rel.startswith(("docs/", "project/")):
            continue
        root = roots[owner]
        if owner == "host_root" and context.scan_mode == "installed_host" and (
            root is None or not (root / ".governance").is_dir()
        ):
            continue
        if root is None:
            findings.append(_finding("ROOT_RESOLUTION_ERROR", "policy", f"missing {owner}"))
            continue
        path, path_error = _safe_join(root, rel)
        if item.get("required", True) and path_error:
            findings.append(Finding("REQUIRED_PATH_MISSING", "policy", path_error, owner, rel))
    return findings


def _bind_planned_markers(units: list[SemanticUnit], policy: dict[str, Any]) -> tuple[dict[int, str], list[Finding]]:
    bindings: dict[int, str] = {}
    findings: list[Finding] = []
    by_path: dict[tuple[str, str], list[tuple[int, SemanticUnit]]] = {}
    target_contract = {
        item.get("claim_id"): frozenset(item.get("claim_classes", []))
        for item in policy.get("planned_targets", []) if isinstance(item, dict)
    }
    for index, unit in enumerate(units):
        by_path.setdefault((unit.root_owner, unit.normalized_path), []).append((index, unit))
    for path_units in by_path.values():
        for position, (index, unit) in enumerate(path_units):
            match = TARGET_RE.fullmatch(f"<!-- {unit.canonical_text} -->") if unit.provenance == "html_comment" else None
            if not match:
                continue
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                findings.append(Finding("PLANNED_MARKER_INVALID", "classify", "invalid marker JSON", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            if set(payload) != {"claim_id", "target_version", "status"} or payload.get("target_version") != "0.68.0" or payload.get("status") != "planned_not_active":
                findings.append(Finding("PLANNED_MARKER_INVALID", "classify", "marker schema/value invalid", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            allowed_subjects = target_contract.get(payload.get("claim_id"))
            if allowed_subjects is None:
                findings.append(Finding("PLANNED_MARKER_UNKNOWN_CLAIM", "classify", "marker claim id is not policy-owned", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            if position + 1 >= len(path_units):
                findings.append(Finding("PLANNED_MARKER_ORPHAN", "classify", "marker has no adjacent unit", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            next_index, next_unit = path_units[position + 1]
            if next_unit.source_span[0] > unit.source_span[2] + 2:
                findings.append(Finding("PLANNED_MARKER_NOT_ADJACENT", "classify", "marker is not adjacent", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            subjects = {relation.subject for relation in next_unit.relations}
            if not subjects or not subjects <= allowed_subjects:
                findings.append(Finding("PLANNED_MARKER_SUBJECT_MISMATCH", "classify", "marker ownership does not match adjacent claim class", unit.root_owner, unit.normalized_path, unit.locator))
                continue
            bindings[next_index] = payload["claim_id"]
    return bindings, findings


def _historical_unit_key(unit: SemanticUnit, entry: dict[str, Any]) -> bool:
    locator = entry.get("locator", {})
    if locator.get("kind") == "line" and "selector_sha256" not in locator:
        return unit.source_span[0] == locator.get("line_number") and unit.raw_text_sha256 == entry.get("claim_payload_sha256")
    return unit.raw_text_sha256 == entry.get("claim_payload_sha256")


def _historical_consumption(units: list[SemanticUnit], policy: dict[str, Any]) -> tuple[int, list[Finding]]:
    entries = [entry for entry in policy.get("historical_claims", []) if isinstance(entry, dict)]
    consumers: dict[str, list[int]] = {entry.get("claim_id", ""): [] for entry in entries}
    owners: dict[int, list[str]] = {}
    for unit_index, unit in enumerate(units):
        for entry in entries:
            if unit.normalized_path != entry.get("normalized_relative_path"):
                continue
            if not _historical_unit_key(unit, entry):
                continue
            claim_id = entry.get("claim_id", "")
            consumers.setdefault(claim_id, []).append(unit_index)
            owners.setdefault(unit_index, []).append(claim_id)
    findings: list[Finding] = []
    exact = 0
    for entry in entries:
        claim_id = entry.get("claim_id", "")
        matches = consumers.get(claim_id, [])
        if not matches:
            findings.append(Finding(
                "HISTORICAL_ENTRY_UNUSED", "history", "historical entry consumes zero semantic units",
                "product_root", entry.get("normalized_relative_path", ""), claim_id=claim_id,
            ))
        elif len(matches) > 1:
            findings.append(Finding(
                "HISTORICAL_ENTRY_MULTIPLE", "history", f"historical entry consumes {len(matches)} semantic units",
                "product_root", entry.get("normalized_relative_path", ""), claim_id=claim_id,
            ))
        elif len(owners.get(matches[0], [])) == 1:
            exact += 1
    for unit_index, claim_ids in owners.items():
        if len(claim_ids) > 1:
            unit = units[unit_index]
            findings.append(Finding(
                "HISTORICAL_UNIT_MULTI_OWNED", "history", f"semantic unit owned by {sorted(claim_ids)}",
                unit.root_owner, unit.normalized_path, unit.locator,
            ))
    return exact, findings


def _is_exact_accounting_fixture(unit: SemanticUnit) -> bool:
    if (
        unit.normalized_path != "docs/architecture/ADR-012-loop-runtime-claim-recovery-split.md"
        or not unit.provenance.startswith("fence:")
    ):
        return False
    try:
        record = json.loads(unit.canonical_text)
    except json.JSONDecodeError:
        return False
    exact_keys = {
        "context_chain", "kind", "language", "locator", "normalized_path",
        "normalized_payload", "ordinal", "root_owner",
    }
    authored = {
        ("golden/ACCT-V1-MD-01.md", 0, "md_heading", "Loop runtime"),
        ("golden/ACCT-V1-MD-01.md", 1, "md_list_item", "state: frobnicated"),
        ("golden/ACCT-V1-JSON-01.json", 0, "json_key", "loop_runtime"),
        ("golden/ACCT-V1-JSON-01.json", 1, "json_key", "state"),
        ("golden/ACCT-V1-JSON-01.json", 2, "json_string", "frobnicated"),
        ("golden/ACCT-V1-PY-01.py", 0, "py_string", "frobnicated"),
        ("golden/ACCT-V1-PY-01.py", 1, "py_string", "ready"),
    }
    return (
        isinstance(record, dict)
        and set(record) == exact_keys
        and (record.get("normalized_path"), record.get("ordinal"), record.get("kind"),
             record.get("normalized_payload")) in authored
        and record.get("root_owner") == "product_root"
        and isinstance(record.get("context_chain"), list)
        and isinstance(record.get("locator"), dict)
    )


def _has_direct_claim_relation(text: str) -> bool:
    if UNKNOWN_LOOP_RELATION_RE.search(text):
        return True
    if re.search(
        r"(?i)\b(?:state|status|mode|capability|readiness|activation)\b\s*[:=]\s*[\"']?[\w-]+",
        text,
    ) and re.search(r"(?i)\bloop\b|循环|runtime[-_ ]activation|migration[-_ ]validity", text):
        return True
    if re.search(
        r"(?i)(?:\bloop(?:[-_ ]engineering)?(?:\s+[a-z][\w-]*){0,4}\s+"
        r"(?:is|are|becomes?|remains?)\s+[a-z][\w-]*\b|"
        r"\b[a-z][\w-]*\s+(?:is|are|becomes?|remains?)\s+(?:the\s+)?"
        r"loop(?:[-_ ]engineering)?(?:\s+[a-z][\w-]*){0,4}\b)",
        text,
    ):
        return True
    predicates = [match.span() for match in AFFIRMATIVE_RE.finditer(text)]
    if not predicates:
        return False
    for pattern in SUBJECT_PATTERNS.values():
        for subject in pattern.finditer(text):
            if any(abs(predicate[0] - subject.end()) <= 80 or abs(subject.start() - predicate[1]) <= 80
                   for predicate in predicates):
                return True
    return False


def _is_contract_context_without_direct_claim(unit: SemanticUnit) -> bool:
    context = unit.context_text
    unquoted = re.sub(r"`[^`]*`|\"[^\"]*\"|'[^']*'", " ", unit.canonical_text)
    if not context or _has_direct_claim_relation(unquoted):
        return False
    return bool(re.search(
        r"(?i)(?:\bADR[- ]?\d*\b|architecture|design|contract|claim correction|claim recovery|"
        r"scanner|acceptance|interface|algorithm|rollback|non-goals?|decision drivers?|"
        r"设计|架构|契约|接口|验收|扫描器|回滚)",
        context,
    ))


def _is_reported_governance_fact(unit: SemanticUnit) -> bool:
    if unit.provenance != "governance_record_cell" or not re.search(
        r"(?:^|\n)(?:EVD|REVIEW|QA)-[A-Z0-9-]+(?:$|\n)", unit.context_text
    ):
        return False
    return bool(re.search(
        r"(?i)(?:\b(?:review|reviewer|tested|verified|confirmed|reported|found|reproduced|"
        r"covered|matched|pass|fail|blocker)s?\b|QA\s|复审|二审|审查|测试|验证|确认|发现|"
        r"复现|覆盖|匹配|结论|阻塞|缺陷)",
        unit.canonical_text,
    ))


def _classify(unit: SemanticUnit, policy: dict[str, Any], planned_claim_id: str = "") -> tuple[str, str]:
    if unit.extraction_state != "extracted":
        return "AMBIGUOUS_SEMANTIC_UNIT", ""
    for entry in policy.get("historical_claims", []):
        if unit.normalized_path == entry.get("normalized_relative_path") and _historical_unit_key(unit, entry):
            return "HISTORICAL_FACT", entry.get("claim_id", "")
    if unit.provenance == "html_comment" and (unit.canonical_text.startswith("loop-runtime-target:") or unit.canonical_text.startswith("loop-runtime-superseding:")):
        return "STRUCTURAL_DATA", ""
    if not unit.relations:
        return "STRUCTURAL_DATA", ""
    registry_context = bool(
        re.search(r"(?:SUBJECT_HINT_TOKENS|SUBJECT_PATTERNS|REQUIRED_RULES)", unit.context_text)
        and "\n" not in unit.canonical_text and len(unit.canonical_text) <= 96
    )
    if unit.provenance == "test_assignment_escaping_or_ambiguous" and not registry_context and any(
        relation.predicate.startswith("unknown_state:")
        or relation.polarity in {"affirmative", "ambiguous", "unknown"}
        for relation in unit.relations
    ):
        return "AMBIGUOUS_SEMANTIC_UNIT", ""
    if _is_exact_accounting_fixture(unit):
        return "STRUCTURAL_DATA", ""
    if _is_contract_context_without_direct_claim(unit):
        return "STRUCTURAL_DATA", ""
    if _is_reported_governance_fact(unit):
        return "STRUCTURAL_DATA", ""
    if unit.provenance == "json_schema_role":
        return "STRUCTURAL_DATA", ""
    if unit.provenance == "test_local_non_escaping":
        return "STRUCTURAL_DATA", ""
    if unit.provenance == "claim_token_registry" and re.search(
        r"(?i)(?:forbidden|overclaim|pattern|token|registry|check|guard|boundary|noun_claim|negat)", unit.context_text
    ):
        return "STRUCTURAL_DATA", ""
    if re.search(r"(?:SUBJECT_HINT_TOKENS|SUBJECT_PATTERNS|REQUIRED_RULES)", unit.context_text) \
            and "\n" not in unit.canonical_text and len(unit.canonical_text) <= 96:
        return "STRUCTURAL_DATA", ""
    if unit.provenance == "regex_source" and re.search(r"\\[AbBdDsSwWZ]|\(\?:|\[\^?", unit.canonical_text):
        return "STRUCTURAL_DATA", ""
    if re.fullmatch(r"LRC-[A-Z0-9-]+", unit.canonical_text):
        return "STRUCTURAL_DATA", ""
    if planned_claim_id:
        contradictory_after_negation = any(
            relation.negator_spans and relation.predicate_spans
            and max(span[0] for span in relation.predicate_spans) > max(span[1] for span in relation.negator_spans)
            for relation in unit.relations
        )
        if unit.relations and not contradictory_after_negation:
            return "PLANNED_NOT_ACTIVE", planned_claim_id
        return "AMBIGUOUS_SEMANTIC_UNIT", planned_claim_id
    if any(relation.predicate == "ambiguous_domain_context" for relation in unit.relations):
        return "AMBIGUOUS_DOMAIN_CONTEXT", ""
    relation_subjects = {relation.subject for relation in unit.relations}
    if len(relation_subjects) > 1 and any(
        relation.polarity in {"affirmative", "unknown", "ambiguous"} for relation in unit.relations
    ):
        return "AMBIGUOUS_SUBJECT_RELATION", ""
    if any(relation.predicate.startswith("unknown_state:") for relation in unit.relations):
        return "UNKNOWN_STATE_PREDICATE", ""
    polarities = {relation.polarity for relation in unit.relations}
    if "ambiguous" in polarities or ("affirmative" in polarities and "negative" in polarities):
        return "AMBIGUOUS_POLARITY", ""
    if polarities <= {"negative", "none"}:
        return "NEGATIVE_NONCLAIM", ""
    rules = {rule.get("claim_class"): rule for rule in policy.get("active_surface_rules", []) if isinstance(rule, dict)}
    affirmative_relations = [relation for relation in unit.relations if relation.polarity == "affirmative"]
    missing = [relation.subject for relation in affirmative_relations if relation.subject not in rules]
    if missing:
        return "UNCLASSIFIED_SURFACE", ""
    allowed = [rules[relation.subject] for relation in affirmative_relations]
    if allowed and all(rule.get("status") == "allowed_current" for rule in allowed):
        return "AFFIRMATIVE_CLASSIFIED", allowed[0].get("claim_id", "")
    return "UNSUPPORTED_AFFIRMATIVE", allowed[0].get("claim_id", "") if allowed else ""


def _recheck_inventory(context: ClaimScanContext, inventory: CandidateInventory,
                       limits: ScanLimits) -> tuple[str, list[Finding]]:
    current, findings = enumerate_candidates(context, limits)
    initial_map = {(item.root_owner, item.normalized_path): item for item in inventory.files}
    current_map = {(item.root_owner, item.normalized_path): item for item in current.files}
    if set(initial_map) != set(current_map):
        created = sorted(set(current_map) - set(initial_map))
        deleted = sorted(set(initial_map) - set(current_map))
        findings.append(_finding(
            "INVENTORY_PATH_SET_CHANGED", "aggregate",
            f"candidate path set changed; created={created[:5]}; deleted={deleted[:5]}",
        ))
    if current.candidate_count != inventory.candidate_count:
        findings.append(_finding("INVENTORY_COUNT_CHANGED", "aggregate", "candidate count changed after enumeration"))
    if current.candidate_bytes != inventory.candidate_bytes:
        findings.append(_finding("INVENTORY_RAW_BYTES_CHANGED", "aggregate", "raw candidate byte total changed"))
    for key in sorted(set(initial_map) & set(current_map)):
        before, after = initial_map[key], current_map[key]
        if before.sha256 != after.sha256:
            findings.append(_finding("INVENTORY_CONTENT_CHANGED", "aggregate", "canonical content digest changed", before))
        if before.raw_bytes != after.raw_bytes:
            findings.append(_finding("INVENTORY_FILE_BYTES_CHANGED", "aggregate", "candidate raw byte count changed", before))
    return current.inventory_sha256, findings


def scan_loop_runtime_claims(context: ClaimScanContext, *, limits: ScanLimits | None = None) -> ClaimScanReport:
    limits = limits or ScanLimits()
    report = ClaimScanReport("BLOCKED", scan_mode=context.scan_mode)
    if context.scan_mode not in {"product_release", "installed_host"}:
        report.findings.append(_finding("SCAN_MODE_INVALID", "context", context.scan_mode))
        return report
    if context.scan_mode == "installed_host" and (context.host_root is None or not (context.host_root / ".governance").is_dir()):
        report.host_state = "UNINITIALIZED"
    policy, policy_errors = _load_json(context.plugin_home, POLICY_RELATIVE_PATH, "policy")
    authority, authority_errors = _load_json(context.plugin_home, AUTHORITY_RELATIVE_PATH, "authority")
    report.findings.extend(policy_errors + authority_errors)
    if not policy or not authority:
        return report
    report.policy_sha256 = _policy_digest(policy)
    report.authority_sha256 = _sha_text(json.dumps(
        authority, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ))
    report.findings.extend(_validate_policy(policy))
    report.findings.extend(_validate_authority(authority, policy))
    report.findings.extend(_validate_source_records(context, authority))
    report.findings.extend(_validate_required_paths(context, policy))

    inventory, enumeration_errors = enumerate_candidates(context, limits)
    report.inventory = inventory
    report.source_envelope_sha256 = _scanner_source_envelope_sha256(
        context.scan_mode, inventory, report.policy_sha256, report.authority_sha256
    )
    report.findings.extend(enumeration_errors)
    if enumeration_errors:
        return report
    candidate_map = {(c.root_owner, c.normalized_path): c for c in inventory.files}
    _owned, notice_count, historical_errors = _validate_historical_and_notices(context, policy, candidate_map)
    report.notices_verified = notice_count
    report.findings.extend(historical_errors)

    units: list[SemanticUnit] = []
    accounting = AccountingAccumulator()
    for candidate in inventory.files:
        python_bundle = None
        python_text = None
        if candidate.language == "python":
            try:
                python_text = _canonical_text(candidate.raw)
                python_bundle = _python_parse_bundle(python_text, candidate.normalized_path)
            except (SyntaxError, tokenize.TokenError, UnicodeError):
                python_bundle = None
        accounted, accounting_error = _account_candidate(
            candidate, python_parse_bundle=python_bundle, canonical_text=python_text
        )
        if accounting_error:
            report.findings.append(accounting_error)
        else:
            try:
                accounting.add(candidate, accounted)
            except (UnicodeError, ValueError, TypeError) as exc:
                accounting_error = _finding(
                    "ACCOUNTING_SERIALIZATION_ERROR", "accounting", str(exc), candidate
                )
                report.findings.append(accounting_error)
                accounted = []
        if candidate.language == "markdown" and accounting_error is None:
            extracted, error = _semantic_units_from_accounting(candidate, accounted), None
        elif candidate.language == "python" and accounting_error is None:
            extracted, error = _python_units(
                candidate, python_text or "", python_bundle, claim_potential_only=True
            ), None
        else:
            extracted, error = extract_semantic_units(
                candidate, python_parse_bundle=python_bundle, claim_potential_only=True,
                canonical_text=python_text,
            )
        if error:
            report.findings.append(error)
            continue
        report.parsed_candidates += 1
        units.extend(extracted)
    report.semantic_units = accounting.unit_count
    report.semantic_payload_bytes = accounting.payload_bytes
    report.semantic_accounting_by_path = accounting.by_path
    report.semantic_accounting_sha256 = accounting.aggregate.hexdigest()
    if report.semantic_units > limits.max_semantic_units or accounting.payload_bytes > limits.max_semantic_payload_bytes:
        report.findings.append(_finding("SEMANTIC_BUDGET_EXCEEDED", "extract", "semantic budget exceeded"))
        return report
    bindings, binding_errors = _bind_planned_markers(units, policy)
    report.findings.extend(binding_errors)
    report.historical_matches, historical_consumption_errors = _historical_consumption(units, policy)
    report.findings.extend(historical_consumption_errors)
    implicit_structural = max(0, report.semantic_units - len(units))
    if implicit_structural:
        report.state_totals["STRUCTURAL_DATA"] = implicit_structural
    for index, unit in enumerate(units):
        state, claim_id = _classify(unit, policy, bindings.get(index, ""))
        report.state_totals[state] = report.state_totals.get(state, 0) + 1
        if unit.relations or state in {"HISTORICAL_FACT", "PLANNED_NOT_ACTIVE"}:
            report.classification_ledger.append({
                "path": unit.normalized_path, "locator": unit.locator,
                "state": state, "provenance": unit.provenance,
            })
        if state in {
            "UNCLASSIFIED_SURFACE", "UNSUPPORTED_AFFIRMATIVE", "AMBIGUOUS_SEMANTIC_UNIT",
            "UNKNOWN_STATE_PREDICATE", "AMBIGUOUS_POLARITY", "AMBIGUOUS_SUBJECT_RELATION",
            "AMBIGUOUS_DOMAIN_CONTEXT",
        }:
            report.findings.append(Finding(state, "classify", unit.canonical_text[:240], unit.root_owner,
                                           unit.normalized_path, unit.locator, authority.get("effective_version", ""),
                                           claim_id, state))
    final_digest, final_errors = _recheck_inventory(context, inventory, limits)
    report.final_inventory_sha256 = final_digest
    report.findings.extend(final_errors)
    if final_digest != inventory.inventory_sha256:
        report.findings.append(_finding("INVENTORY_DIGEST_DRIFT", "aggregate", "final candidate inventory differs"))
    report.verdict = "PASS" if not report.findings and report.parsed_candidates == inventory.candidate_count else "BLOCKED"
    return report


def scan_report_json(context: ClaimScanContext, *, limits: ScanLimits | None = None) -> str:
    return json.dumps(
        scan_loop_runtime_claims(context, limits=limits).as_s1_dict(),
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ) + "\n"
